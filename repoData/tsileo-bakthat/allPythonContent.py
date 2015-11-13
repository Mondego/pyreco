__FILENAME__ = backends
# -*- encoding: utf-8 -*-
import tempfile
import os
import logging
import shelve
import json
import socket
import httplib

import boto
from boto.s3.key import Key
import math
from boto.glacier.exceptions import UnexpectedHTTPResponseError
from boto.exception import S3ResponseError

from bakthat.conf import config, DEFAULT_LOCATION, CONFIG_FILE
from bakthat.models import Inventory, Jobs

log = logging.getLogger(__name__)


class glacier_shelve(object):
    """Context manager for shelve.

    Deprecated, here for backward compatibility.

    """

    def __enter__(self):
        self.shelve = shelve.open(os.path.expanduser("~/.bakthat.db"))

        return self.shelve

    def __exit__(self, exc_type, exc_value, traceback):
        self.shelve.close()


class BakthatBackend(object):
    """Handle Configuration for Backends.

    The profile is only useful when no conf is None.

    :type conf: dict
    :param conf: Custom configuration

    :type profile: str
    :param profile: Profile name

    """
    def __init__(self, conf={}, profile="default"):
        self.conf = conf
        if not conf:
            self.conf = config.get(profile)
            if not self.conf:
                log.error("No {0} profile defined in {1}.".format(profile, CONFIG_FILE))
            if not "access_key" in self.conf or not "secret_key" in self.conf:
                log.error("Missing access_key/secret_key in {0} profile ({1}).".format(profile, CONFIG_FILE))


class RotationConfig(BakthatBackend):
    """Hold backups rotation configuration."""
    def __init__(self, conf={}, profile="default"):
        BakthatBackend.__init__(self, conf, profile)
        self.conf = self.conf.get("rotation", {})


class S3Backend(BakthatBackend):
    """Backend to handle S3 upload/download."""
    def __init__(self, conf={}, profile="default"):
        BakthatBackend.__init__(self, conf, profile)

        con = boto.connect_s3(self.conf["access_key"], self.conf["secret_key"])

        region_name = self.conf["region_name"]
        if region_name == DEFAULT_LOCATION:
            region_name = ""

        try:
            self.bucket = con.get_bucket(self.conf["s3_bucket"])
        except S3ResponseError, e:
            if e.code == "NoSuchBucket":
                self.bucket = con.create_bucket(self.conf["s3_bucket"], location=region_name)
            else:
                raise e

        self.container = self.conf["s3_bucket"]
        self.container_key = "s3_bucket"

    def download(self, keyname):
        k = Key(self.bucket)
        k.key = keyname

        encrypted_out = tempfile.TemporaryFile()
        k.get_contents_to_file(encrypted_out)
        encrypted_out.seek(0)

        return encrypted_out

    def cb(self, complete, total):
        """Upload callback to log upload percentage."""
        percent = int(complete * 100.0 / total)
        log.info("Upload completion: {0}%".format(percent))

    def upload(self, keyname, filename, **kwargs):
        k = Key(self.bucket)
        k.key = keyname
        upload_kwargs = {"reduced_redundancy": kwargs.get("s3_reduced_redundancy", False)}
        if kwargs.get("cb", True):
            upload_kwargs = dict(cb=self.cb, num_cb=10)
        k.set_contents_from_filename(filename, **upload_kwargs)
        k.set_acl("private")

    def ls(self):
        return [key.name for key in self.bucket.get_all_keys()]

    def delete(self, keyname):
        k = Key(self.bucket)
        k.key = keyname
        self.bucket.delete_key(k)


class GlacierBackend(BakthatBackend):
    """Backend to handle Glacier upload/download."""
    def __init__(self, conf={}, profile="default"):
        BakthatBackend.__init__(self, conf, profile)

        con = boto.connect_glacier(aws_access_key_id=self.conf["access_key"], aws_secret_access_key=self.conf["secret_key"], region_name=self.conf["region_name"])

        self.vault = con.create_vault(self.conf["glacier_vault"])
        self.backup_key = "bakthat_glacier_inventory"
        self.container = self.conf["glacier_vault"]
        self.container_key = "glacier_vault"

    def load_archives(self):
        return []

    def backup_inventory(self):
        """Backup the local inventory from shelve as a json string to S3."""
        if config.get("aws", "s3_bucket"):
            archives = self.load_archives()

            s3_bucket = S3Backend(self.conf).bucket
            k = Key(s3_bucket)
            k.key = self.backup_key

            k.set_contents_from_string(json.dumps(archives))

            k.set_acl("private")

    def load_archives_from_s3(self):
        """Fetch latest inventory backup from S3."""
        s3_bucket = S3Backend(self.conf).bucket
        try:
            k = Key(s3_bucket)
            k.key = self.backup_key

            return json.loads(k.get_contents_as_string())
        except S3ResponseError, exc:
            log.error(exc)
            return {}

#    def restore_inventory(self):
#        """Restore inventory from S3 to DumpTruck."""
#        if config.get("aws", "s3_bucket"):
#            loaded_archives = self.load_archives_from_s3()

#            # TODO faire le restore
#        else:
#            raise Exception("You must set s3_bucket in order to backup/restore inventory to/from S3.")

    def restore_inventory(self):
        """Restore inventory from S3 to local shelve."""
        if config.get("aws", "s3_bucket"):
            loaded_archives = self.load_archives_from_s3()

            with glacier_shelve() as d:
                archives = {}
                for a in loaded_archives:
                    print a
                    archives[a["filename"]] = a["archive_id"]
                d["archives"] = archives
        else:
            raise Exception("You must set s3_bucket in order to backup/restore inventory to/from S3.")

    def upload(self, keyname, filename, **kwargs):
        archive_id = self.vault.concurrent_create_archive_from_file(filename, keyname)
        Inventory.create(filename=keyname, archive_id=archive_id)

        #self.backup_inventory()

    def get_job_id(self, filename):
        """Get the job_id corresponding to the filename.

        :type filename: str
        :param filename: Stored filename.

        """
        return Jobs.get_job_id(filename)

    def delete_job(self, filename):
        """Delete the job entry for the filename.

        :type filename: str
        :param filename: Stored filename.

        """
        job = Jobs.get(Jobs.filename == filename)
        job.delete_instance()

    def download(self, keyname, job_check=False):
        """Initiate a Job, check its status, and download the archive if it's completed."""
        archive_id = Inventory.get_archive_id(keyname)
        if not archive_id:
            log.error("{0} not found !")
            # check if the file exist on S3 ?
            return

        job = None

        job_id = Jobs.get_job_id(keyname)
        log.debug("Job: {0}".format(job_id))

        if job_id:
            try:
                job = self.vault.get_job(job_id)
            except UnexpectedHTTPResponseError:  # Return a 404 if the job is no more available
                self.delete_job(keyname)

        if not job:
            job = self.vault.retrieve_archive(archive_id)
            job_id = job.id
            Jobs.update_job_id(keyname, job_id)

        log.info("Job {action}: {status_code} ({creation_date}/{completion_date})".format(**job.__dict__))

        if job.completed:
            log.info("Downloading...")
            encrypted_out = tempfile.TemporaryFile()

            # Boto related, download the file in chunk
            chunk_size = 4 * 1024 * 1024
            num_chunks = int(math.ceil(job.archive_size / float(chunk_size)))
            job._download_to_fileob(encrypted_out, num_chunks, chunk_size, True, (socket.error, httplib.IncompleteRead))

            encrypted_out.seek(0)
            return encrypted_out
        else:
            log.info("Not completed yet")
            if job_check:
                return job
            return

    def retrieve_inventory(self, jobid):
        """Initiate a job to retrieve Galcier inventory or output inventory."""
        if jobid is None:
            return self.vault.retrieve_inventory(sns_topic=None, description="Bakthat inventory job")
        else:
            return self.vault.get_job(jobid)

    def retrieve_archive(self, archive_id, jobid):
        """Initiate a job to retrieve Galcier archive or download archive."""
        if jobid is None:
            return self.vault.retrieve_archive(archive_id, sns_topic=None, description='Retrieval job')
        else:
            return self.vault.get_job(jobid)

    def ls(self):
        return [ivt.filename for ivt in Inventory.select()]

    def delete(self, keyname):
        archive_id = Inventory.get_archive_id(keyname)
        if archive_id:
            self.vault.delete_archive(archive_id)
            archive_data = Inventory.get(Inventory.filename == keyname)
            archive_data.delete_instance()

            #self.backup_inventory()

    def upgrade_from_shelve(self):
        try:
            with glacier_shelve() as d:
                archives = d["archives"]
                if "archives" in d:
                    for key, archive_id in archives.items():
                        #print {"filename": key, "archive_id": archive_id}
                        Inventory.create(**{"filename": key, "archive_id": archive_id})
                        del archives[key]
                d["archives"] = archives
        except Exception, exc:
            log.exception(exc)

class SwiftBackend(BakthatBackend):
    """Backend to handle OpenStack Swift upload/download."""
    def __init__(self, conf={}, profile="default"):
        BakthatBackend.__init__(self, conf, profile)

        from swiftclient import Connection, ClientException

        self.con = Connection(self.conf["auth_url"], self.conf["access_key"], 
                              self.conf["secret_key"],
                              auth_version=self.conf["auth_version"],
                              insecure=True)

        region_name = self.conf["region_name"]
        if region_name == DEFAULT_LOCATION:
            region_name = ""

        try:
            self.con.head_container(self.conf["s3_bucket"])
        except ClientException, e:
            self.con.put_container(self.conf["s3_bucket"])

        self.container = self.conf["s3_bucket"]
        self.container_key = "s3_bucket"

    def download(self, keyname):
        headers, data = self.con.get_object(self.container, keyname,
                                            resp_chunk_size=65535)

        encrypted_out = tempfile.TemporaryFile()
        for chunk in data:
            encrypted_out.write(chunk)
        encrypted_out.seek(0)

        return encrypted_out

    def cb(self, complete, total):
        """Upload callback to log upload percentage."""
        """Swift client does not support callbak"""
        percent = int(complete * 100.0 / total)
        log.info("Upload completion: {0}%".format(percent))

    def upload(self, keyname, filename, **kwargs):
        fp = open(filename, "rb")
        self.con.put_object(self.container, keyname, fp)

    def ls(self):
        headers, objects = self.con.get_container(self.conf["s3_bucket"])
        return [key['name'] for key in objects]

    def delete(self, keyname):
        self.con.delete_object(self.container, keyname)

########NEW FILE########
__FILENAME__ = conf
# -*- encoding: utf-8 -*-
import yaml
import os
import logging

from events import Events

log = logging.getLogger(__name__)

CONFIG_FILE = os.path.expanduser("~/.bakthat.yml")
PLUGINS_DIR = os.path.expanduser("~/.bakthat_plugins")
DATABASE = os.path.expanduser("~/.bakthat.sqlite")

DEFAULT_LOCATION = "us-east-1"
DEFAULT_DESTINATION = "s3"

EXCLUDE_FILES = [".bakthatexclude", ".gitignore"]


def load_config(config_file=CONFIG_FILE):
    """ Try to load a yaml config file. """
    config = {}
    if os.path.isfile(config_file):
        log.debug("Try loading config file: {0}".format(config_file))
        config = yaml.load(open(config_file))
        if config:
            log.debug("Config loaded")
    return config

# Read default config file
config = load_config()
events = Events()

########NEW FILE########
__FILENAME__ = helper
# -*- encoding: utf-8 -*-
import logging
import tempfile
import sh
import os
import shutil
import time
import hashlib
import json
from StringIO import StringIO
from gzip import GzipFile

from beefish import encrypt, decrypt
from boto.s3.key import Key

import bakthat
from bakthat.conf import DEFAULT_DESTINATION
from bakthat.backends import S3Backend
from bakthat.models import Backups

log = logging.getLogger(__name__)


class KeyValue(S3Backend):
    """A Key Value store to store/retrieve object/string on S3.

    Data is gzipped and json encoded before uploading,
    compression can be disabled.
    """
    def __init__(self, conf={}, profile="default"):
        S3Backend.__init__(self, conf, profile)
        self.profile = profile

    def set_key(self, keyname, value, **kwargs):
        """Store a string as keyname in S3.

        :type keyname: str
        :param keyname: Key name

        :type value: str
        :param value: Value to save, will be json encoded.

        :type value: bool
        :keyword compress: Compress content with gzip,
            True by default
        """
        k = Key(self.bucket)
        k.key = keyname

        backup_date = int(time.time())
        backup = dict(filename=keyname,
                      stored_filename=keyname,
                      backup_date=backup_date,
                      last_updated=backup_date,
                      backend="s3",
                      is_deleted=False,
                      tags="",
                      metadata={"KeyValue": True,
                                "is_enc": False,
                                "is_gzipped": False})

        fileobj = StringIO(json.dumps(value))

        if kwargs.get("compress", True):
            backup["metadata"]["is_gzipped"] = True
            out = StringIO()
            f = GzipFile(fileobj=out, mode="w")
            f.write(fileobj.getvalue())
            f.close()
            fileobj = StringIO(out.getvalue())

        password = kwargs.get("password")
        if password:
            backup["metadata"]["is_enc"] = True
            out = StringIO()
            encrypt(fileobj, out, password)
            fileobj = out
        # Creating the object on S3
        k.set_contents_from_string(fileobj.getvalue())
        k.set_acl("private")
        backup["size"] = k.size

        access_key = self.conf.get("access_key")
        container_key = self.conf.get(self.container_key)
        backup["backend_hash"] = hashlib.sha512(access_key + container_key).hexdigest()
        Backups.upsert(**backup)

    def get_key(self, keyname, **kwargs):
        """Return the object stored under keyname.

        :type keyname: str
        :param keyname: Key name

        :type default: str
        :keyword default: Default value if key name does not exist, None by default

        :rtype: str
        :return: The key content as string, or default value.
        """
        k = Key(self.bucket)
        k.key = keyname
        if k.exists():
            backup = Backups.get(Backups.stored_filename % keyname, Backups.backend == "s3")
            fileobj = StringIO(k.get_contents_as_string())

            if backup.is_encrypted():
                out = StringIO()
                decrypt(fileobj, out, kwargs.get("password"))
                fileobj = out
                fileobj.seek(0)

            if backup.is_gzipped():
                f = GzipFile(fileobj=fileobj, mode="r")
                out = f.read()
                f.close()
                fileobj = StringIO(out)
            return json.loads(fileobj.getvalue())
        return kwargs.get("default")

    def delete_key(self, keyname):
        """Delete the given key.

        :type keyname: str
        :param keyname: Key name
        """
        k = Key(self.bucket)
        k.key = keyname
        if k.exists():
            k.delete()
        backup = Backups.match_filename(keyname, "s3", profile=self.profile)
        if backup:
            backup.set_deleted()
            return True

    def get_key_url(self, keyname, expires_in, method="GET"):
        """Generate a URL for the keyname object.

        Be careful, the response is JSON encoded.

        :type keyname: str
        :param keyname: Key name

        :type expires_in: int
        :param expires_in: Number of the second before the expiration of the link

        :type method: str
        :param method: HTTP method for access

        :rtype str:
        :return: The URL to download the content of the given keyname
        """
        k = Key(self.bucket)
        k.key = keyname
        if k.exists:
            return k.generate_url(expires_in, method)


class BakHelper:
    """Helper that makes building scripts with bakthat better faster stronger.

    Designed to be used as a context manager.

    :type backup_name: str
    :param backup_name: Backup name
        also the prefix for the created temporary directory.

    :type destination: str
    :keyword destination: Destination (glacier|s3)

    :type password: str
    :keyword password: Password (Empty string to disable encryption, disabled by default)

    :type profile: str
    :keyword profile: Profile name, only valid if no custom conf is provided

    :type conf: dict
    :keyword conf: Override profiles configuration

    :type tags: list
    :param tags: List of tags
    """
    def __init__(self, backup_name, **kwargs):
        self.backup_name = backup_name
        self.dir_prefix = "{0}_".format(backup_name)
        self.destination = kwargs.get("destination", DEFAULT_DESTINATION)
        self.password = kwargs.get("password", "")
        self.profile = kwargs.get("profile", "default")
        self.conf = kwargs.get("conf", {})
        self.tags = kwargs.get("tags", [])
        # Key for bakmanager.io hook
        self.key = kwargs.get("key", None)
        self.syncer = None

    def __enter__(self):
        """Save the old current working directory,
            create a temporary directory,
            and make it the new current working directory.
        """
        self.old_cwd = os.getcwd()
        self.tmpd = tempfile.mkdtemp(prefix=self.dir_prefix)
        sh.cd(self.tmpd)
        log.info("New current working directory: {0}.".format(self.tmpd))
        return self

    def __exit__(self, type, value, traceback):
        """Reseting the current working directory,
            and run synchronization if enabled.
        """
        sh.cd(self.old_cwd)
        log.info("Back to {0}".format(self.old_cwd))
        shutil.rmtree(self.tmpd)
        if self.syncer:
            log.debug("auto sync")
            self.sync()

    def sync(self):
        """Shortcut for calling BakSyncer."""
        if self.syncer:
            try:
                return self.syncer.sync()
            except Exception, exc:
                log.exception(exc)

    def enable_sync(self, api_url, auth=None):
        """Enable synchronization with :class:`bakthat.sync.BakSyncer` (optional).

        :type api_url: str
        :param api_url: Base API URL.

        :type auth: tuple
        :param auth: Optional, tuple/list (username, password) for API authentication.
        """
        log.debug("Enabling BakSyncer to {0}".format(api_url))
        from bakthat.sync import BakSyncer
        self.syncer = BakSyncer(api_url, auth)

    def backup(self, filename=None, **kwargs):
        """Perform backup.

        :type filename: str
        :param filename: File/directory to backup.

        :type password: str
        :keyword password: Override already set password.

        :type destination: str
        :keyword destination: Override already set destination.

        :type tags: list
        :keyword tags: Tags list

        :type profile: str
        :keyword profile: Profile name

        :type conf: dict
        :keyword conf: Override profiles configuration

        :rtype: dict
        :return: A dict containing the following keys: stored_filename, size, metadata and filename.
        """
        if filename is None:
            filename = self.tmpd

        return bakthat.backup(filename,
                              destination=kwargs.get("destination", self.destination),
                              password=kwargs.get("password", self.password),
                              tags=kwargs.get("tags", self.tags),
                              profile=kwargs.get("profile", self.profile),
                              conf=kwargs.get("conf", self.conf),
                              key=kwargs.get("key", self.key),
                              custom_filename=self.backup_name)

    def restore(self, filename, **kwargs):
        """Restore backup in the current working directory.

        :type filename: str
        :param filename: File/directory to backup.

        :type password: str
        :keyword password: Override already set password.

        :type destination: str
        :keyword destination: Override already set destination.

        :type profile: str
        :keyword profile: Profile name

        :type conf: dict
        :keyword conf: Override profiles configuration

        :rtype: bool
        :return: True if successful.
        """
        return bakthat.restore(filename,
                               destination=kwargs.get("destination", self.destination),
                               password=kwargs.get("password", self.password),
                               profile=kwargs.get("profile", self.profile),
                               conf=kwargs.get("conf", self.conf))

    def delete_older_than(self, filename=None, interval=None, **kwargs):
        """Delete backups older than the given interval string.

        :type filename: str
        :param filename: File/directory name.

        :type interval: str
        :param interval: Interval string like 1M, 1W, 1M3W4h2s...
            (s => seconds, m => minutes, h => hours, D => days, W => weeks, M => months, Y => Years).

        :type destination: str
        :keyword destination: Override already set destination.

        :type profile: str
        :keyword profile: Profile name

        :type conf: dict
        :keyword conf: Override profiles configuration

        :rtype: list
        :return: A list containing the deleted keys (S3) or archives (Glacier).
        """
        if filename is None:
            filename = self.tmpd

        return bakthat.delete_older_than(filename, interval,
                                         destination=kwargs.get("destination", self.destination),
                                         profile=kwargs.get("profile", self.profile),
                                         conf=kwargs.get("conf", self.conf))

    def rotate(self, filename=None, **kwargs):
        """Rotate backup using grandfather-father-son rotation scheme.

        :type filename: str
        :param filename: File/directory name.

        :type destination: str
        :keyword destination: Override already set destination.

        :type profile: str
        :keyword profile: Profile name

        :type conf: dict
        :keyword conf: Override profiles configuration

        :rtype: list
        :return: A list containing the deleted keys (S3) or archives (Glacier).
        """
        if filename is None:
            filename = self.backup_name

        return bakthat.rotate_backups(filename,
                                      destination=kwargs.pop("destination", self.destination),
                                      profile=kwargs.get("profile", self.profile),
                                      conf=kwargs.get("conf", self.conf))

########NEW FILE########
__FILENAME__ = models
import peewee
from datetime import datetime
from bakthat.conf import config, load_config, DATABASE
import hashlib
import json
import sqlite3
import os
import requests
import logging

log = logging.getLogger(__name__)

database = peewee.SqliteDatabase(DATABASE)


class JsonField(peewee.CharField):
    """Custom JSON field."""
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        try:
            return json.loads(value)
        except:
            return value


class BaseModel(peewee.Model):
    class Meta:
        database = database


class SyncedModel(peewee.Model):
    class Meta:
        database = database


class History(BaseModel):
    """History for sync."""
    data = JsonField()
    ts = peewee.IntegerField(index=True)
    action = peewee.CharField(index=True)
    model = peewee.CharField(index=True)
    pk = peewee.CharField(index=True)

    class Meta:
        db_table = 'history'


class Backups(SyncedModel):
    """Backups Model."""
    backend = peewee.CharField(index=True)
    backend_hash = peewee.CharField(index=True, null=True)
    backup_date = peewee.IntegerField(index=True)
    filename = peewee.TextField(index=True)
    is_deleted = peewee.BooleanField()
    last_updated = peewee.IntegerField()
    metadata = JsonField()
    size = peewee.IntegerField()
    stored_filename = peewee.TextField(index=True, unique=True)
    tags = peewee.CharField()

    def __repr__(self):
        return "<Backup: {0}>".format(self._data.get("stored_filename"))

    @classmethod
    def match_filename(cls, filename, destination, **kwargs):
        conf = config
        if kwargs.get("config"):
            conf = load_config(kwargs.get("config"))

        profile = conf.get(kwargs.get("profile", "default"))

        s3_key = hashlib.sha512(profile.get("access_key") +
                                profile.get("s3_bucket")).hexdigest()
        glacier_key = hashlib.sha512(profile.get("access_key") +
                                     profile.get("glacier_vault")).hexdigest()

        try:
            fquery = "{0}*".format(filename)
            query = Backups.select().where(Backups.filename % fquery |
                                           Backups.stored_filename % fquery,
                                           Backups.backend == destination,
                                           Backups.backend_hash << [s3_key, glacier_key])
            query = query.order_by(Backups.backup_date.desc())
            return query.get()
        except Backups.DoesNotExist:
            return

    @classmethod
    def search(cls, query="", destination="", **kwargs):
        conf = config
        if kwargs.get("config"):
            conf = load_config(kwargs.get("config"))

        if not destination:
            destination = ["s3", "glacier"]
        if isinstance(destination, (str, unicode)):
            destination = [destination]

        query = "*{0}*".format(query)
        wheres = []

        if kwargs.get("profile"):
            profile = conf.get(kwargs.get("profile"))

            s3_key = hashlib.sha512(profile.get("access_key") +
                                    profile.get("s3_bucket")).hexdigest()
            glacier_key = hashlib.sha512(profile.get("access_key") +
                                         profile.get("glacier_vault")).hexdigest()

            wheres.append(Backups.backend_hash << [s3_key, glacier_key])

        wheres.append(Backups.filename % query |
                      Backups.stored_filename % query)
        wheres.append(Backups.backend << destination)
        wheres.append(Backups.is_deleted == False)

        older_than = kwargs.get("older_than")
        if older_than:
            wheres.append(Backups.backup_date < older_than)

        backup_date = kwargs.get("backup_date")
        if backup_date:
            wheres.append(Backups.backup_date == backup_date)

        last_updated_gt = kwargs.get("last_updated_gt")
        if last_updated_gt:
            wheres.append(Backups.last_updated >= last_updated_gt)

        tags = kwargs.get("tags", [])
        if tags:
            if isinstance(tags, (str, unicode)):
                tags = tags.split()
            tags_query = ["Backups.tags % '*{0}*'".format(tag) for tag in tags]
            tags_query = eval("({0})".format(" and ".join(tags_query)))
            wheres.append(tags_query)

        return Backups.select().where(*wheres).order_by(Backups.last_updated.desc())

    def set_deleted(self):
        self.is_deleted = True
        self.last_updated = int(datetime.utcnow().strftime("%s"))
        self.save()

    def is_encrypted(self):
        return self.stored_filename.endswith(".enc") or self.metadata.get("is_enc")

    def is_gzipped(self):
        return self.metadata.get("is_gzipped")

    @classmethod
    def upsert(cls, **backup):
        q = Backups.select()
        q = q.where(Backups.stored_filename == backup.get("stored_filename"))
        if q.count():
            del backup["stored_filename"]
            Backups.update(**backup).where(Backups.stored_filename == backup.get("stored_filename")).execute()
        else:
            Backups.create(**backup)

    class Meta:
        db_table = 'backups'

    class Sync:
        pk = 'stored_filename'


class Config(BaseModel):
    """key => value config store."""
    key = peewee.CharField(index=True, unique=True)
    value = JsonField()

    @classmethod
    def get_key(self, key, default=None):
        try:
            return Config.get(Config.key == key).value
        except Config.DoesNotExist:
            return default

    @classmethod
    def set_key(self, key, value=None):
        q = Config.select().where(Config.key == key)
        if q.count():
            Config.update(value=value).where(Config.key == key).execute()
        else:
            Config.create(key=key, value=value)

    class Meta:
        db_table = 'config'


class Inventory(SyncedModel):
    """Filename => archive_id mapping for glacier archives."""
    archive_id = peewee.CharField(index=True, unique=True)
    filename = peewee.CharField(index=True)

    @classmethod
    def get_archive_id(self, filename):
        return Inventory.get(Inventory.filename == filename).archive_id

    class Meta:
        db_table = 'inventory'

    class Sync:
        pk = 'filename'


class Jobs(SyncedModel):
    """filename => job_id mapping for glacier archives."""
    filename = peewee.CharField(index=True)
    job_id = peewee.CharField()

    @classmethod
    def get_job_id(cls, filename):
        """Try to retrieve the job id for a filename.

        :type filename: str
        :param filename: Filename

        :rtype: str
        :return: Job Id for the given filename
        """
        try:
            return Jobs.get(Jobs.filename == filename).job_id
        except Jobs.DoesNotExist:
            return

    @classmethod
    def update_job_id(cls, filename, job_id):
        """Update job_id for the given filename.

        :type filename: str
        :param filename: Filename

        :type job_id: str
        :param job_id: New job_id

        :return: None
        """
        q = Jobs.select().where(Jobs.filename == filename)
        if q.count():
            Jobs.update(job_id=job_id).where(Jobs.filename == filename).execute()
        else:
            Jobs.create(filename=filename, job_id=job_id)

    class Meta:
        db_table = 'jobs'


for table in [Backups, Jobs, Inventory, Config, History]:
    if not table.table_exists():
        table.create_table()


def backup_sqlite(filename):
    """Backup bakthat SQLite database to file."""
    con = sqlite3.connect(DATABASE)
    with open(filename, 'w') as f:
        for line in con.iterdump():
            f.write("{0}\n".format(line))


def restore_sqlite(filename):
    """Restore a dump into bakthat SQLite database."""
    con = sqlite3.connect(DATABASE)
    con.executescript(open(filename).read())


def switch_from_dt_to_peewee():
    if os.path.isfile(os.path.expanduser("~/.bakthat.dt")):
        import dumptruck
        import time
        dt = dumptruck.DumpTruck(dbname=os.path.expanduser("~/.bakthat.dt"), vars_table="config")
        for backup in dt.dump("backups"):
            try:
                backup["tags"] = " ".join(backup.get("tags", []))
                Backups.upsert(**backup)
                time.sleep(0.1)
            except Exception, exc:
                print exc
        for ivt in dt.dump("inventory"):
            try:
                Inventory.create(filename=ivt["filename"],
                                 archive_id=ivt["archive_id"])
            except Exception, exc:
                print exc
        os.remove(os.path.expanduser("~/.bakthat.dt"))

switch_from_dt_to_peewee()

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-
import importlib
import os
import sys
import logging
import atexit

from bakthat.conf import PLUGINS_DIR, events

log = logging.getLogger(__name__)
plugin_setup = False


def setup_plugins(conf=None):
    """ Add the plugin dir to the PYTHON_PATH,
    and activate them."""
    global plugin_setup
    if not plugin_setup:
        log.debug("Setting up plugins")
        plugins_dir = conf.get("plugins_dir", PLUGINS_DIR)

        if os.path.isdir(plugins_dir):
            log.debug("Adding {0} to plugins dir".format(plugins_dir))
            sys.path.append(plugins_dir)

        for plugin in conf.get("plugins", []):
            p = load_class(plugin)
            if issubclass(p, Plugin):
                load_plugin(p, conf)
            else:
                raise Exception("Plugin must be a bakthat.plugin.Plugin subclass!")
        plugin_setup = True


def load_class(full_class_string):
    """ Dynamically load a class from a string. """
    class_data = full_class_string.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]

    module = importlib.import_module(module_path)
    return getattr(module, class_str)


def load_plugin(plugin, conf):
    p = plugin(conf)
    log.debug("Activating {0}".format(p))
    p.activate()

    def deactivate_plugin():
        try:
            p.deactivate()
        except NotImplementedError:
            pass
    atexit.register(deactivate_plugin)


class Plugin(object):
    """ Abstract plugin class.
    Plugin should implement activate, and optionnaly deactivate.
    """
    def __init__(self, conf):
        self.conf = conf
        self.events = events
        self.log = log

    def __getattr__(self, attr):
        if attr in ["before_backup",
                    "on_backup",
                    "before_restore",
                    "on_restore",
                    "before_delete",
                    "on_delete",
                    "before_delete_older_than",
                    "on_delete_older_than",
                    "before_rotate_backups",
                    "on_rotate_backups"]:
            return getattr(self.events, attr)
        else:
            raise Exception("Event {0} does not exist!".format(attr))

    def __repr__(self):
        return "<Plugin bakthat: {0}>".format(self.__class__.__name__)

    def __str__(self):
        return self.__repr__()

    def activate(self):
        raise NotImplementedError("Plugin should implement this!")

    def deactivate(self):
        raise NotImplementedError("Plugin may implement this!")

########NEW FILE########
__FILENAME__ = sync
# -*- encoding: utf-8 -*-
import logging
import socket
from bakthat.models import Backups, Config
from bakthat.conf import config
import requests
import json

log = logging.getLogger(__name__)


def bakmanager_periodic_backups(conf):
    """Fetch periodic backups info from bakmanager.io API."""
    if conf.get("bakmanager_token"):
        bakmanager_backups_endpoint = conf.get("bakmanager_api", "https://bakmanager.io/api/keys/")
        r = requests.get(bakmanager_backups_endpoint, auth=(conf.get("bakmanager_token"), ""))
        r.raise_for_status()
        for key in r.json().get("_items", []):
            latest_date = key.get("latest", {}).get("date_human")
            line = "{key:20} status: {status:5} interval: {interval_human:6} total: {total_size_human:10}".format(**key)
            line += " latest: {0} ".format(latest_date)
            log.info(line)
    else:
        log.error("No bakmanager_token setting for the current profile.")


def bakmanager_hook(conf, backup_data, key=None):
    """First version of a hook for monitoring periodic backups with BakManager
    (https://bakmanager.io).

    :type conf: dict
    :param conf: Current profile config

    :type backup_data: dict
    :param backup_data: Backup data (size)

    :type key: str
    :param key: Periodic backup identifier
    """
    try:
        if conf.get("bakmanager_token"):
            bakmanager_backups_endpoint = conf.get("bakmanager_api", "https://bakmanager.io/api/backups/")
            bak_backup = {"key": key, "host": socket.gethostname(), "size": backup_data["size"]}
            bak_payload = {"backup":  json.dumps(bak_backup)}
            r = requests.post(bakmanager_backups_endpoint, bak_payload, auth=(conf.get("bakmanager_token"), ""))
            r.raise_for_status()
        else:
            log.error("No bakmanager_token setting for the current profile.")
    except Exception, exc:
        log.error("Error while submitting periodic backup to BakManager.")
        log.exception(exc)


class BakSyncer():
    """Helper to synchronize change on a backup set via a REST API.

    No sensitive information is transmitted except (you should be using https):
    - API user/password
    - a hash (hashlib.sha512) of your access_key concatened with
        your s3_bucket or glacier_vault, to be able to sync multiple
        client with the same configuration stored as metadata for each bakckupyy.

    :type conf: dict
    :param conf: Config (url, username, password)
    """
    def __init__(self, conf=None):
        conf = {} if conf is None else conf
        sync_conf = dict(url=config.get("sync", {}).get("url"),
                         username=config.get("sync", {}).get("username"),
                         password=config.get("sync", {}).get("password"))
        sync_conf.update(conf)

        self.sync_auth = (sync_conf["username"], sync_conf["password"])
        self.api_url = sync_conf["url"]

        self.request_kwargs = dict(auth=self.sync_auth)

        self.request_kwargs["headers"] = {'content-type': 'application/json', 'bakthat-client': socket.gethostname()}

        self.get_resource = lambda x: self.api_url + "/{0}".format(x)

    def register(self):
        """Register/create the current host on the remote server if not already registered."""
        if not Config.get_key("client_id"):
            r_kwargs = self.request_kwargs.copy()
            r = requests.post(self.get_resource("clients"), **r_kwargs)
            if r.status_code == 200:
                client = r.json()
                if client:
                    Config.set_key("client_id", client["_id"])
            else:
                log.error("An error occured during sync: {0}".format(r.text))
        else:
            log.debug("Already registered ({0})".format(Config.get_key("client_id")))

    def sync(self):
        """Draft for implementing bakthat clients (hosts) backups data synchronization.

        Synchronize Bakthat sqlite database via a HTTP POST request.

        Backups are never really deleted from sqlite database, we just update the is_deleted key.

        It sends the last server sync timestamp along with data updated since last sync.
        Then the server return backups that have been updated on the server since last sync.

        On both sides, backups are either created if they don't exists or updated if the incoming version is newer.
        """
        log.debug("Start syncing")

        self.register()

        last_sync_ts = Config.get_key("sync_ts", 0)
        to_insert_in_mongo = [b._data for b in Backups.search(last_updated_gt=last_sync_ts)]
        data = dict(sync_ts=last_sync_ts, new=to_insert_in_mongo)
        r_kwargs = self.request_kwargs.copy()
        log.debug("Initial payload: {0}".format(data))
        r_kwargs.update({"data": json.dumps(data)})
        r = requests.post(self.get_resource("backups/sync"), **r_kwargs)
        if r.status_code != 200:
            log.error("An error occured during sync: {0}".format(r.text))
            return

        log.debug("Sync result: {0}".format(r.json()))
        to_insert_in_bakthat = r.json().get("updated", [])
        sync_ts = r.json().get("sync_ts")
        for newbackup in to_insert_in_bakthat:
            log.debug("Upsert {0}".format(newbackup))
            Backups.upsert(**newbackup)

        Config.set_key("sync_ts", sync_ts)

        log.debug("Sync succcesful")

    def reset_sync(self):
        log.debug("reset sync")
        Config.set_key("sync_ts", 0)
        Config.set_key("client_id", None)

    def sync_auto(self):
        """Trigger sync if autosync is enabled."""
        if config.get("sync", {}).get("auto", False):
            self.sync()

########NEW FILE########
__FILENAME__ = utils
# -*- encoding: utf-8 -*-
import logging
from datetime import timedelta
import re

log = logging.getLogger(__name__)


def _timedelta_total_seconds(td):
    """Python 2.6 backward compatibility function for timedelta.total_seconds.

    :type td: timedelta object
    :param td: timedelta object

    :rtype: float
    :return: The total number of seconds for the given timedelta object.

    """
    if hasattr(timedelta, "total_seconds"):
        return getattr(td, "total_seconds")()

    # Python 2.6 backward compatibility
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)


def _interval_string_to_seconds(interval_string):
    """Convert internal string like 1M, 1Y3M, 3W to seconds.

    :type interval_string: str
    :param interval_string: Interval string like 1M, 1W, 1M3W4h2s...
        (s => seconds, m => minutes, h => hours, D => days, W => weeks, M => months, Y => Years).

    :rtype: int
    :return: The conversion in seconds of interval_string.

    """
    interval_exc = "Bad interval format for {0}".format(interval_string)
    interval_dict = {"s": 1, "m": 60, "h": 3600, "D": 86400,
                     "W": 7*86400, "M": 30*86400, "Y": 365*86400}

    interval_regex = re.compile("^(?P<num>[0-9]+)(?P<ext>[smhDWMY])")
    seconds = 0

    while interval_string:
        match = interval_regex.match(interval_string)
        if match:
            num, ext = int(match.group("num")), match.group("ext")
            if num > 0 and ext in interval_dict:
                seconds += num * interval_dict[ext]
                interval_string = interval_string[match.end():]
            else:
                raise Exception(interval_exc)
        else:
            raise Exception(interval_exc)
    return seconds

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bakthat documentation build configuration file, created by
# sphinx-quickstart on Fri Mar  1 10:32:38 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bakthat'
copyright = u'2013, Thomas Sileo'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6.0'
# The full version, including alpha/beta/rc tags.
release = '0.6.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'kr'
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index': ['sidebarintro.html', 'localtoc.html', 'searchbox.html', 'sidebarend.html'],
    '**': ['sidebarintro.html', 'localtoc.html', 'relations.html'
                 , 'searchbox.html', 'sidebarend.html'],
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Bakthatdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Bakthat.tex', u'Bakthat Documentation',
   u'Thomas Sileo', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bakthat', u'Bakthat Documentation',
     [u'Thomas Sileo'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Bakthat', u'Bakthat Documentation',
   u'Thomas Sileo', 'Bakthat', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
__FILENAME__ = test_plugin
import time

from bakthat.plugin import Plugin


class TestPlugin(Plugin):
    """ A basic plugin implementation. """
    def activate(self):
        self.start = {}
        self.stop = {}
        self.before_backup += self.before_backup_callback
        self.on_backup += self.on_backup_callback

    def before_backup_callback(self, session_id):
        self.start[session_id] = time.time()
        self.log.info("before_backup {0}".format(session_id))

    def on_backup_callback(self, session_id, backup):
        self.stop[session_id] = time.time()
        self.log.info("on_backup {0} {1}".format(session_id, backup))
        self.log.info("Job duration: {0}s".format(self.stop[session_id] - self.start[session_id]))

########NEW FILE########
__FILENAME__ = test_plugin2
from bakthat.plugin import Plugin
from bakthat.models import Backups


class MyBackups(Backups):
    @classmethod
    def my_custom_method(self):
        return True


class ChangeModelPlugin(Plugin):
    """ A basic plugin implementation. """
    def activate(self):
        global Backups
        self.log.info("Replace Backups")
        Backups = MyBackups

########NEW FILE########
__FILENAME__ = test_bakthat
# -*- encoding: utf-8 -*-
import bakthat
import tempfile
import hashlib
import os
import time
import unittest
import logging

log = logging.getLogger()

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.addFilter(bakthat.BakthatFilter())
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log.addHandler(handler)
log.setLevel(logging.DEBUG)


class BakthatTestCase(unittest.TestCase):

    def setUp(self):
        self.test_file = tempfile.NamedTemporaryFile()
        self.test_file.write("Bakthat Test File")
        self.test_file.seek(0)
        self.test_filename = self.test_file.name.split("/")[-1]
        self.test_hash = hashlib.sha1(self.test_file.read()).hexdigest()
        self.password = "bakthat_encrypted_test"

    def test_internals(self):
        with self.assertRaises(Exception):
            bakthat._interval_string_to_seconds("1z")

        self.assertEqual(bakthat._interval_string_to_seconds("2D1h"), 86400 * 2 + 3600)
        self.assertEqual(bakthat._interval_string_to_seconds("3M"), 3*30*86400)

    def test_keyvalue_helper(self):
        from bakthat.helper import KeyValue
        kv = KeyValue()
        test_string = "Bakthat Test str"
        test_key = "bakthat-unittest"
        test_key_enc = "bakthat-unittest-testenc"
        test_key2 = "itshouldfail"
        test_password = "bakthat-password"
        kv.set_key(test_key, test_string)
        kv.set_key(test_key_enc, test_string, password=test_password)
        self.assertEqual(test_string, kv.get_key(test_key))
        self.assertEqual(test_string, kv.get_key(test_key_enc, password=test_password))
        #from urllib2 import urlopen, HTTPError
        #test_url = kv.get_key_url(test_key, 10)
        #self.assertEqual(json.loads(urlopen(test_url).read()), test_string)
        #time.sleep(30)
        #with self.assertRaises(HTTPError):
        #    urlopen(test_url).read()
        kv.delete_key(test_key_enc)
        kv.delete_key(test_key)
        self.assertEqual(kv.get_key(test_key), None)
        self.assertEqual(kv.get_key(test_key2), None)


    def test_s3_backup_restore(self):
        backup_data = bakthat.backup(self.test_file.name, "s3", password="")
        log.info(backup_data)

        #self.assertEqual(bakthat.match_filename(self.test_filename, "s3")[0]["filename"],
        #                 self.test_filename)

        bakthat.restore(self.test_filename, "s3")

        restored_hash = hashlib.sha1(open(self.test_filename).read()).hexdigest()

        self.assertEqual(self.test_hash, restored_hash)

        os.remove(self.test_filename)

        bakthat.delete(self.test_filename, "s3")

        #self.assertEqual(bakthat.match_filename(self.test_filename), [])

    def test_s3_delete_older_than(self):
        backup_res = bakthat.backup(self.test_file.name, "s3", password="")

        #self.assertEqual(bakthat.match_filename(self.test_filename, "s3")[0]["filename"],
        #                 self.test_filename)

        bakthat.restore(self.test_filename, "s3")

        restored_hash = hashlib.sha1(open(self.test_filename).read()).hexdigest()

        self.assertEqual(self.test_hash, restored_hash)

        os.remove(self.test_filename)

        test_deleted = bakthat.delete_older_than(self.test_filename, "1Y", destination="s3")

        self.assertEqual(test_deleted, [])

        time.sleep(10)

        test_deleted = bakthat.delete_older_than(self.test_filename, "9s", destination="s3")

        key_deleted = test_deleted[0]

        self.assertEqual(key_deleted.stored_filename, backup_res.stored_filename)

        #self.assertEqual(bakthat.match_filename(self.test_filename), [])

    def test_s3_encrypted_backup_restore(self):
        bakthat.backup(self.test_file.name, "s3", password=self.password)

        #self.assertEqual(bakthat.match_filename(self.test_filename, "s3")[0]["filename"],
        #                 self.test_filename)

        # Check if stored file is encrypted
        #self.assertTrue(bakthat.match_filename(self.test_filename, "s3")[0]["is_enc"])

        bakthat.restore(self.test_filename, "s3", password=self.password)

        restored_hash = hashlib.sha1(open(self.test_filename).read()).hexdigest()

        self.assertEqual(self.test_hash, restored_hash)

        os.remove(self.test_filename)

        bakthat.delete(self.test_filename, "s3")

        #self.assertEqual(bakthat.match_filename(self.test_filename), [])

    def test_glacier_backup_restore(self):
        if raw_input("Test glacier upload/download ? It can take up to 4 hours ! (y/N): ").lower() == "y":

            # Backup dummy file
            bakthat.backup(self.test_file.name, "glacier", password="")

            # Check that file is showing up in bakthat ls
            #self.assertEqual(bakthat.match_filename(self.test_filename, "glacier")[0]["filename"],
            #                self.test_filename)
            # TODO replace by a Backups.search

            # We initialize glacier backend
            # to check that the file appear in both local and remote (S3) inventory
            #glacier_backend = GlacierBackend(None)

            #archives = glacier_backend.load_archives()
            #archives_s3 = glacier_backend.load_archives_from_s3()

            # Check that local and remote custom inventory are equal
            #self.assertEqual(archives, archives_s3)

            # Next we check that the file is stored in both inventories
            #inventory_key_name = bakthat.match_filename(self.test_filename, "glacier")[0]["key"]

            #self.assertTrue(inventory_key_name in [a.get("filename") for a in archives])
            #self.assertTrue(inventory_key_name in [a.get("filename") for a in archives_s3])

            # Restore backup
            job = bakthat.restore(self.test_filename, "glacier", job_check=True)

            # Check that a job is initiated
            self.assertEqual(job.__dict__["action"], "ArchiveRetrieval")
            self.assertEqual(job.__dict__["status_code"], "InProgress")

            while 1:
                # Check every ten minutes if the job is done
                result = bakthat.restore(self.test_filename, "glacier")

                # If job is done, we can download the file
                if result:
                    restored_hash = hashlib.sha1(open(self.test_filename).read()).hexdigest()

                    # Check if the hash of the restored file is equal to inital file hash
                    self.assertEqual(self.test_hash, restored_hash)

                    os.remove(self.test_filename)

                    # Now, we can delete the restored file
                    bakthat.delete(self.test_filename, "glacier")

                    # Check that the file is deleted
                    #self.assertEqual(bakthat.match_filename(self.test_filename, "glacier"), [])
                    # TODO Backups.search

                    #archives = glacier_backend.load_archives()
                    #archives_s3 = glacier_backend.load_archives_from_s3()

                    # Check if the file has been removed from both archives
                    #self.assertEqual(archives, archives_s3)
                    #self.assertTrue(inventory_key_name not in archives)
                    #self.assertTrue(inventory_key_name not in archives_s3)

                    break
                else:
                    time.sleep(600)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_bakthat_swift
# -*- encoding: utf-8 -*-
import bakthat
import tempfile
import hashlib
import os
import time
import unittest
import logging

log = logging.getLogger()

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.addFilter(bakthat.BakthatFilter())
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log.addHandler(handler)
log.setLevel(logging.DEBUG)


class BakthatSwiftBackendTestCase(unittest.TestCase):
    """This test cases use profile test_swift """

    def setUp(self):
        self.test_file = tempfile.NamedTemporaryFile()
        self.test_file.write("Bakthat Test File")
        self.test_file.seek(0)
        self.test_filename = self.test_file.name.split("/")[-1]
        self.test_hash = hashlib.sha1(self.test_file.read()).hexdigest()
        self.password = "bakthat_encrypted_test"
        self.test_profile = "test_swift"

    def test_swift_backup_restore(self):
        backup_data = bakthat.backup(self.test_file.name, "swift", password="",
                                     profile=self.test_profile)
        log.info(backup_data)

        #self.assertEqual(bakthat.match_filename(self.test_filename, "swift",
        #                                        profile=self.test_profile
        #                                        )[0]["filename"],
        #                 self.test_filename)

        bakthat.restore(self.test_filename, "swift", profile=self.test_profile)

        restored_hash = hashlib.sha1(
            open(self.test_filename).read()).hexdigest()

        self.assertEqual(self.test_hash, restored_hash)

        os.remove(self.test_filename)

        bakthat.delete(backup_data["stored_filename"], "swift", profile=self.test_profile)

        #self.assertEqual(bakthat.match_filename(self.test_filename, "swift",
        #                                        profile=self.test_profile), [])

    def test_swift_delete_older_than(self):
        backup_res = bakthat.backup(self.test_file.name, "swift", password="",
                                    profile=self.test_profile)

        #self.assertEqual(bakthat.match_filename(self.test_filename, "swift",
        #                                        profile=self.test_profile
        #                                        )[0]["filename"],
        #                 self.test_filename)

        bakthat.restore(self.test_filename, "swift",
                        profile=self.test_profile)

        restored_hash = hashlib.sha1(
            open(self.test_filename).read()).hexdigest()

        self.assertEqual(self.test_hash, restored_hash)

        os.remove(self.test_filename)

        test_deleted = bakthat.delete_older_than(self.test_filename, "1Y",
                                                 "swift",
                                                 profile=self.test_profile)

        self.assertEqual(test_deleted, [])

        time.sleep(10)

        test_deleted = bakthat.delete_older_than(self.test_filename, "9s",
                                                 "swift",
                                                 profile=self.test_profile)

        key_deleted = test_deleted[0]

        self.assertEqual(key_deleted, backup_res["stored_filename"])

        #self.assertEqual(bakthat.match_filename(self.test_filename,
        #                                        "swift",
        #                                        profile=self.test_profile),
        #                 [])

    def test_swift_encrypted_backup_restore(self):
        backup_data = bakthat.backup(self.test_file.name, "swift", password=self.password,
                                     profile=self.test_profile)

        #self.assertEqual(bakthat.match_filename(self.test_filename, "swift",
        #                                        profile=self.test_profile)
        #                 [0]["filename"], self.test_filename)

        # Check if stored file is encrypted
        #self.assertTrue(bakthat.match_filename(self.test_filename, "swift",
        #                                       profile=self.test_profile)
        #                [0]["is_enc"])

        bakthat.restore(self.test_filename, "swift", password=self.password,
                        profile=self.test_profile)

        restored_hash = hashlib.sha1(
            open(self.test_filename).read()).hexdigest()

        self.assertEqual(self.test_hash, restored_hash)

        os.remove(self.test_filename)

        bakthat.delete(backup_data["stored_filename"], "swift",
                       profile=self.test_profile)

        #self.assertEqual(bakthat.match_filename(self.test_filename,
        #                                        "swift",
        #                                        profile=self.test_profile),
        #                 [])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
