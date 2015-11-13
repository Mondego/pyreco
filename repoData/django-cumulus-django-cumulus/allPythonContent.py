__FILENAME__ = context_processors
from urlparse import urlparse

from django.conf import settings

from cumulus.storage import SwiftclientStorage, SwiftclientStaticStorage


def _is_ssl_uri(uri):
    return urlparse(uri).scheme == "https"


def _get_container_urls(swiftclient_storage):
    cdn_url = swiftclient_storage.container.cdn_uri
    ssl_url = swiftclient_storage.container.cdn_ssl_uri

    return cdn_url, ssl_url


def cdn_url(request):
    """
    A context processor that exposes the full CDN URL in templates.
    """
    cdn_url, ssl_url = _get_container_urls(SwiftclientStorage())
    static_url = settings.STATIC_URL

    return {
        "CDN_URL": cdn_url + static_url,
        "CDN_SSL_URL": ssl_url + static_url,
    }


def static_cdn_url(request):
    """
    A context processor that exposes the full static CDN URL
    as static URL in templates.
    """
    cdn_url, ssl_url = _get_container_urls(SwiftclientStaticStorage())
    static_url = settings.STATIC_URL

    return {
        "STATIC_URL": cdn_url + static_url,
        "STATIC_SSL_URL": ssl_url + static_url,
        "LOCAL_STATIC_URL": static_url,
    }

########NEW FILE########
__FILENAME__ = collectstatic
import hashlib

from django.contrib.staticfiles.management.commands import collectstatic

from cumulus.storage import SwiftclientStorage


class Command(collectstatic.Command):

    def delete_file(self, path, prefixed_path, source_storage):
        """
        Checks if the target file should be deleted if it already exists
        """
        if isinstance(self.storage, SwiftclientStorage):
            if self.storage.exists(prefixed_path):
                try:
                    etag = self.storage._get_cloud_obj(prefixed_path).etag
                    digest = "{0}".format(hashlib.md5(source_storage.open(path).read()).hexdigest())
                    print etag, digest
                    if etag == digest:
                        self.log(u"Skipping '{0}' (not modified based on file hash)".format(path))
                        return False
                except:
                    raise
        return super(Command, self).delete_file(path, prefixed_path, source_storage)

########NEW FILE########
__FILENAME__ = container_create
import optparse
import pyrax
import swiftclient

from django.core.management.base import BaseCommand, CommandError

from cumulus.settings import CUMULUS


def cdn_enabled_for_container(container):
    """pyrax.cf_wrapper.CFClient assumes cdn_connection.

    Currently the pyrax swift client wrapper assumes that if
    you're using pyrax, you're using the CDN support that's
    only available with the rackspace openstack.
    This can be removed once the following pull-request lands
    (or is otherwise resolved):
        https://github.com/rackspace/pyrax/pull/254
    """
    try:
        return container.cdn_enabled
    except AttributeError:
        return False


class Command(BaseCommand):
    help = "Create a container."
    args = "[container_name]"

    option_list = BaseCommand.option_list + (
        optparse.make_option("-p", "--private", action="store_true", default=False,
                             dest="private", help="Make a private container."),)

    def connect(self):
        """
        Connects using the swiftclient api.
        """
        self.conn = swiftclient.Connection(authurl=CUMULUS["AUTH_URL"],
                                           user=CUMULUS["USERNAME"],
                                           key=CUMULUS["API_KEY"],
                                           snet=CUMULUS["SERVICENET"],
                                           auth_version=CUMULUS["AUTH_VERSION"],
                                           tenant_name=CUMULUS["AUTH_TENANT_NAME"])

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Pass one and only one [container_name] as an argument")
        self.connect()
        container_name = args[0]
        print("Creating container: {0}".format(container_name))
        self.conn.put_container(container_name)
        if not options.get("private"):
            print("Publish container: {0}".format(container_name))
            headers = {"X-Container-Read": ".r:*"}
            self.conn.post_container(container_name, headers=headers)
            if CUMULUS["USE_PYRAX"]:
                if CUMULUS["PYRAX_IDENTITY_TYPE"]:
                    pyrax.set_setting("identity_type", CUMULUS["PYRAX_IDENTITY_TYPE"])
                pyrax.set_credentials(CUMULUS["USERNAME"], CUMULUS["API_KEY"])
                public = not CUMULUS["SERVICENET"]
                connection = pyrax.connect_to_cloudfiles(region=CUMULUS["REGION"],
                                                         public=public)
                container = connection.get_container(container_name)
                if cdn_enabled_for_container(container):
                    container.make_public(ttl=CUMULUS["TTL"])

########NEW FILE########
__FILENAME__ = container_delete
import datetime
import multiprocessing
import optparse
import swiftclient

from django.core.management.base import BaseCommand, CommandError

from cumulus.settings import CUMULUS


class Command(BaseCommand):
    help = "Delete a container."
    args = "[container_name]"

    option_list = BaseCommand.option_list + (
        optparse.make_option("-y", "--yes", action="store_true", default=False,
                             dest="is_yes", help="Assume Yes to confirmation question"),)

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Pass one and only one [container_name] as an argument")
        container_name = args[0]
        if not options.get("is_yes"):
            is_ok = raw_input("Permanently delete container {0}? [y|N] ".format(
                container_name))
            if not is_ok == "y":
                raise CommandError("Aborted")

        conn = swiftclient.Connection(authurl=CUMULUS["AUTH_URL"],
                                      user=CUMULUS["USERNAME"],
                                      key=CUMULUS["API_KEY"],
                                      snet=CUMULUS["SERVICENET"],
                                      auth_version=CUMULUS["AUTH_VERSION"],
                                      tenant_name=CUMULUS["AUTH_TENANT_NAME"])

        print("Connecting")
        container = conn.get_container(container_name)

        print("Deleting objects from container {0}".format(container_name))
        # divide the objects to delete equally into one list per processor
        cloud_objs = [cloud_obj["name"] for cloud_obj in container[1]]
        nbr_chunks = multiprocessing.cpu_count()
        chunk_size = len(cloud_objs) / nbr_chunks
        if len(cloud_objs) % nbr_chunks != 0:
            chunk_size += 1
        chunks = [[container_name, cloud_objs[x * chunk_size:(x + 1) * chunk_size]]
                  for x in range(nbr_chunks)]
        # create a Pool which will create Python processes
        p = multiprocessing.Pool()
        start_time = datetime.datetime.now()
        # send out the work chunks to the Pool
        po = p.map_async(delete_cloud_objects, chunks)
        # we get a list of lists back, one per chunk, so we have to
        # flatten them back together
        # po.get() will block until results are ready and then
        # return a list of lists of results: [[cloud_obj], [cloud_obj]]
        results = po.get()
        output = []
        for res in results:
            output += res
        if output != cloud_objs:
            print("Deletion failure")
        conn.delete_container(container_name)
        print(datetime.datetime.now() - start_time)
        print("Deletion complete")


def delete_cloud_objects(chunk):
    """Deletes cloud objects. Runs in a separate process."""
    container_name, cloud_objs = chunk
    conn = swiftclient.Connection(authurl=CUMULUS["AUTH_URL"],
                                  user=CUMULUS["USERNAME"],
                                  key=CUMULUS["API_KEY"],
                                  snet=CUMULUS["SERVICENET"],
                                  auth_version=CUMULUS["AUTH_VERSION"],
                                  tenant_name=CUMULUS["AUTH_TENANT_NAME"])
    filter(None, cloud_objs)
    deleted = []
    for cloud_obj in cloud_objs:
        conn.delete_object(container=container_name,
                           obj=cloud_obj)
        deleted.append(cloud_obj)
    return deleted

########NEW FILE########
__FILENAME__ = container_info
import optparse
import pyrax
import swiftclient

from django.core.management.base import BaseCommand

from cumulus.settings import CUMULUS


class Command(BaseCommand):
    help = "Display info for containers"
    args = "[container_name container_name ...]"

    option_list = BaseCommand.option_list + (
        optparse.make_option("-n", "--name", action="store_true", dest="name", default=False),
        optparse.make_option("-c", "--count", action="store_true", dest="count", default=False),
        optparse.make_option("-s", "--size", action="store_true", dest="size", default=False),
        optparse.make_option("-u", "--uri", action="store_true", dest="uri", default=False)
    )

    def connect(self):
        """
        Connect using the swiftclient api and the cloudfiles api.
        """
        self.conn = swiftclient.Connection(authurl=CUMULUS["AUTH_URL"],
                                           user=CUMULUS["USERNAME"],
                                           key=CUMULUS["API_KEY"],
                                           snet=CUMULUS["SERVICENET"],
                                           auth_version=CUMULUS["AUTH_VERSION"],
                                           tenant_name=CUMULUS["AUTH_TENANT_NAME"])

    def handle(self, *args, **options):
        self.connect()
        account = self.conn.get_account()
        if args:
            container_names = args
        else:
            container_names = [c["name"] for c in account[1]]
        containers = {}
        for container_name in container_names:
            containers[container_name] = self.conn.head_container(container_name)

        if not containers:
            print("No containers found.")
            return

        if not args:
            print("{0}, {1}, {2}\n".format(
                account[0]["x-account-container-count"],
                account[0]["x-account-object-count"],
                account[0]["x-account-bytes-used"],
            ))

        opts = ["name", "count", "size", "uri"]
        for container_name, values in containers.iteritems():
            info = {
                "name": container_name,
                "count": values["x-container-object-count"],
                "size": values["x-container-bytes-used"],
                "uri": "{}/{}".format(self.conn.url, container_name),
            }
            if CUMULUS["USE_PYRAX"]:
                if CUMULUS["PYRAX_IDENTITY_TYPE"]:
                    pyrax.set_setting("identity_type", CUMULUS["PYRAX_IDENTITY_TYPE"])
                pyrax.set_credentials(CUMULUS["USERNAME"], CUMULUS["API_KEY"])
                public = not CUMULUS["SERVICENET"]
                connection = pyrax.connect_to_cloudfiles(region=CUMULUS["REGION"],
                                                         public=public)
                if connection.cdn_connection is not None:
                    metadata = connection.get_container_cdn_metadata(container_name)
                    if "x-cdn-enabled" not in metadata or metadata["x-cdn-enabled"] == "False":
                        uri = "NOT PUBLIC"
                    else:
                        uri = metadata["x-cdn-uri"]
                    info['uri'] = uri

            output = [str(info[o]) for o in opts if options.get(o)]
            if not output:
                output = [str(info[o]) for o in opts]
            print(", ".join(output))

########NEW FILE########
__FILENAME__ = container_list
import swiftclient

from django.core.management.base import BaseCommand, CommandError

from cumulus.settings import CUMULUS


class Command(BaseCommand):
    help = ("List all the items in a container to stdout.\n\n"
            "We recommend you run it like this:\n"
            "    ./manage.py container_list <container> | pv --line-mode > <container>.list\n\n"
            "pv is Pipe Viewer: http://www.ivarch.com/programs/pv.shtml")
    args = "[container_name]"

    def connect(self):
        """
        Connects using the swiftclient api.
        """
        self.conn = swiftclient.Connection(authurl=CUMULUS["AUTH_URL"],
                                           user=CUMULUS["USERNAME"],
                                           key=CUMULUS["API_KEY"],
                                           snet=CUMULUS["SERVICENET"],
                                           auth_version=CUMULUS["AUTH_VERSION"],
                                           tenant_name=CUMULUS["AUTH_TENANT_NAME"])

    def handle(self, *args, **options):
        """
        Lists all the items in a container to stdout.
        """
        if len(args) == 0:
            self.connect()
            self.list_all_containers()
        elif len(args) == 1:
            self.connect()
            self.container = self.conn.get_container(args[0])
            for cloudfile in self.container[1]:
                print(cloudfile["name"])
        else:
            raise CommandError("Pass one and only one [container_name] as an argument")

    def list_all_containers(self):
        """
        Prints a list of all containers.
        """
        print("...Listing containers...")

        containers = self.conn.get_account()[1]
        if containers:
            print("Please specify one of the following containers:")
            for container in containers:
                print(container["name"])
        else:
            print("No containers were found for this account.")

########NEW FILE########
__FILENAME__ = syncmedia
import datetime
import fnmatch
import mimetypes
import optparse
import os
import pyrax
import re
import swiftclient

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError, NoArgsCommand


from cumulus.settings import CUMULUS
from cumulus.storage import get_gzipped_contents


class Command(NoArgsCommand):
    help = "Synchronizes media to cloud files."
    option_list = NoArgsCommand.option_list + (
        optparse.make_option("-i", "--include", action="append", default=[],
                             dest="includes", metavar="PATTERN",
                             help="Include file or directories matching this glob-style "
                                  "pattern. Use multiple times to include more."),
        optparse.make_option("-e", "--exclude", action="append", default=[],
                             dest="excludes", metavar="PATTERN",
                             help="Exclude files or directories matching this glob-style "
                                  "pattern. Use multiple times to exclude more."),
        optparse.make_option("-w", "--wipe",
                             action="store_true", dest="wipe", default=False,
                             help="Wipes out entire contents of container first."),
        optparse.make_option("-t", "--test-run",
                             action="store_true", dest="test_run", default=False,
                             help="Performs a test run of the sync."),
        optparse.make_option("-q", "--quiet",
                             action="store_true", dest="test_run", default=False,
                             help="Do not display any output."),
        optparse.make_option("-c", "--container",
                             dest="container", help="Override CONTAINER."),
    )

    def set_options(self, options):
        """
        Sets instance variables based on an options dict
        """
        # COMMAND LINE OPTIONS
        self.wipe = options.get("wipe")
        self.test_run = options.get("test_run")
        self.quiet = options.get("test_run")
        self.container_name = options.get("container")
        self.verbosity = int(options.get("verbosity"))
        if self.test_run:
            self.verbosity = 2
        cli_includes = options.get("includes")
        cli_excludes = options.get("excludes")

        # CUMULUS CONNECTION AND SETTINGS FROM SETTINGS.PY
        if not self.container_name:
            self.container_name = CUMULUS["CONTAINER"]
        settings_includes = CUMULUS["INCLUDE_LIST"]
        settings_excludes = CUMULUS["EXCLUDE_LIST"]

        # PATH SETTINGS
        self.static_root = os.path.abspath(settings.MEDIA_ROOT)
        self.static_url = settings.MEDIA_URL
        if not self.static_root.endswith("/"):
            self.static_root = self.static_root + "/"
        if self.static_url.startswith("/"):
            self.static_url = self.static_url[1:]

        # SYNCSTATIC VARS
        # combine includes and excludes from the cli and django settings file
        self.includes = list(set(cli_includes + settings_includes))
        self.excludes = list(set(cli_excludes + settings_excludes))
        # transform glob patterns to regular expressions
        self.local_filenames = []
        self.create_count = 0
        self.upload_count = 0
        self.update_count = 0
        self.skip_count = 0
        self.delete_count = 0

    def connect_container(self):
        """
        Connects to a container using the swiftclient api.

        The container will be created and/or made public using the
        pyrax api if not already so.
        """
        self.conn = swiftclient.Connection(authurl=CUMULUS["AUTH_URL"],
                                           user=CUMULUS["USERNAME"],
                                           key=CUMULUS["API_KEY"],
                                           snet=CUMULUS["SERVICENET"],
                                           auth_version=CUMULUS["AUTH_VERSION"],
                                           tenant_name=CUMULUS["AUTH_TENANT_NAME"])
        try:
            self.conn.head_container(self.container_name)
        except swiftclient.client.ClientException as exception:
            if exception.msg == "Container HEAD failed":
                call_command("container_create", self.container_name)
            else:
                raise

        if CUMULUS["USE_PYRAX"]:
            if CUMULUS["PYRAX_IDENTITY_TYPE"]:
                pyrax.set_setting("identity_type", CUMULUS["PYRAX_IDENTITY_TYPE"])
            public = not CUMULUS["SERVICENET"]
            pyrax.set_credentials(CUMULUS["USERNAME"], CUMULUS["API_KEY"])
            connection = pyrax.connect_to_cloudfiles(region=CUMULUS["REGION"],
                                                     public=public)
            container = connection.get_container(self.container_name)
            if not container.cdn_enabled:
                container.make_public(ttl=CUMULUS["TTL"])
        else:
            headers = {"X-Container-Read": ".r:*"}
            self.conn.post_container(self.container_name, headers=headers)

        self.container = self.conn.get_container(self.container_name, full_listing=True)

    def handle_noargs(self, *args, **options):
        # setup
        self.set_options(options)
        self.connect_container()

        # wipe first
        if self.wipe:
            self.wipe_container()

        # match local files
        abspaths = self.match_local(self.static_root, self.includes, self.excludes)
        relpaths = []
        for path in abspaths:
            filename = path.split(self.static_root)[1]
            if filename.startswith("/"):
                filename = filename[1:]
            relpaths.append(filename)
        if not relpaths:
            raise CommandError("The MEDIA_ROOT directory is empty "
                               "or all files have been ignored.")
        for path in abspaths:
            if not os.path.isfile(path):
                raise CommandError("Unsupported filetype: {0}.".format(path))

        # match cloud objects
        cloud_objs = self.match_cloud(self.includes, self.excludes)

        remote_objects = {
            obj['name']: datetime.datetime.strptime(obj['last_modified'],
                                "%Y-%m-%dT%H:%M:%S.%f") for obj in self.container[1]
        }

        # sync
        self.upload_files(abspaths, relpaths, remote_objects)
        self.delete_extra_files(relpaths, cloud_objs)

        if not self.quiet or self.verbosity > 1:
            self.print_tally()

    def match_cloud(self, includes, excludes):
        """
        Returns the cloud objects that match the include and exclude patterns.
        """
        cloud_objs = [cloud_obj["name"] for cloud_obj in self.container[1]]
        includes_pattern = r"|".join([fnmatch.translate(x) for x in includes])
        excludes_pattern = r"|".join([fnmatch.translate(x) for x in excludes]) or r"$."
        excludes = [o for o in cloud_objs if re.match(excludes_pattern, o)]
        includes = [o for o in cloud_objs if re.match(includes_pattern, o)]
        return [o for o in includes if o not in excludes]

    def match_local(self, prefix, includes, excludes):
        """
        Filters os.walk() with include and exclude patterns.
        See: http://stackoverflow.com/a/5141829/93559
        """
        includes_pattern = r"|".join([fnmatch.translate(x) for x in includes])
        excludes_pattern = r"|".join([fnmatch.translate(x) for x in excludes]) or r"$."
        matches = []
        for root, dirs, files in os.walk(prefix, topdown=True):
            # exclude dirs
            dirs[:] = [os.path.join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.match(excludes_pattern,
                                                       d.split(root)[1])]
            # exclude/include files
            files = [os.path.join(root, f) for f in files]
            files = [os.path.join(root, f) for f in files
                     if not re.match(excludes_pattern, f)]
            files = [os.path.join(root, f) for f in files
                     if re.match(includes_pattern, f.split(prefix)[1])]
            for fname in files:
                matches.append(fname)
        return matches

    def upload_files(self, abspaths, relpaths, remote_objects):
        """
        Determines files to be uploaded and call ``upload_file`` on each.
        """
        for relpath in relpaths:
            abspath = [p for p in abspaths if p.endswith(relpath)][0]
            cloud_datetime = remote_objects[relpath] if relpath in remote_objects else None
            local_datetime = datetime.datetime.utcfromtimestamp(os.stat(abspath).st_mtime)

            if cloud_datetime and local_datetime < cloud_datetime:
                self.skip_count += 1
                if not self.quiet:
                    print("Skipped {0}: not modified.".format(relpath))
                continue
            if relpath in remote_objects:
                self.update_count += 1
            else:
                self.create_count += 1
            self.upload_file(abspath, relpath)

    def upload_file(self, abspath, cloud_filename):
        """
        Uploads a file to the container.
        """
        if not self.test_run:
            headers = None
            contents = open(abspath, "rb")
            size = os.stat(abspath).st_size

            mime_type, encoding = mimetypes.guess_type(abspath)
            if mime_type in CUMULUS.get("GZIP_CONTENT_TYPES", []):
                headers = {"Content-Encoding": "gzip"}
                contents = get_gzipped_contents(contents)
                size = contents.size

            self.conn.put_object(container=self.container_name,
                                 obj=cloud_filename,
                                 contents=contents,
                                 content_length=size,
                                 etag=None,
                                 content_type=mime_type,
                                 headers=headers)
            # TODO syncheaders
            #from cumulus.storage import sync_headers
            #sync_headers(cloud_obj)
        self.upload_count += 1
        if not self.quiet or self.verbosity > 1:
            print("Uploaded: {0}".format(cloud_filename))

    def delete_extra_files(self, relpaths, cloud_objs):
        """
        Deletes any objects from the container that do not exist locally.
        """
        for cloud_obj in cloud_objs:
            if cloud_obj not in relpaths:
                if not self.test_run:
                    self.delete_cloud_obj(cloud_obj)
                self.delete_count += 1
                if not self.quiet or self.verbosity > 1:
                    print("Deleted: {0}".format(cloud_obj))

    def delete_cloud_obj(self, cloud_obj):
        """
        Deletes an object from the container.
        """
        self.conn.delete_object(container=self.container_name,
                                obj=cloud_obj)

    def wipe_container(self):
        """
        Completely wipes out the contents of the container.
        """
        if self.test_run:
            print("Wipe would delete {0} objects.".format(len(self.container[1])))
        else:
            if not self.quiet or self.verbosity > 1:
                print("Deleting {0} objects...".format(len(self.container[1])))
            for cloud_obj in self.container[1]:
                self.conn.delete_object(self.container_name, cloud_obj["name"])

    def print_tally(self):
        """
        Prints the final tally to stdout.
        """
        self.update_count = self.upload_count - self.create_count
        if self.test_run:
            print("Test run complete with the following results:")
        print("Skipped {0}. Created {1}. Updated {2}. Deleted {3}.".format(
            self.skip_count, self.create_count, self.update_count, self.delete_count))

########NEW FILE########
__FILENAME__ = syncstatic
import datetime
import fnmatch
import mimetypes
import optparse
import os
import pyrax
import re
import swiftclient

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError, NoArgsCommand


from cumulus.settings import CUMULUS
from cumulus.storage import get_headers, get_content_type, get_gzipped_contents


class Command(NoArgsCommand):
    help = "Synchronizes static media to cloud files."
    option_list = NoArgsCommand.option_list + (
        optparse.make_option("-i", "--include", action="append", default=[],
                             dest="includes", metavar="PATTERN",
                             help="Include file or directories matching this glob-style "
                                  "pattern. Use multiple times to include more."),
        optparse.make_option("-e", "--exclude", action="append", default=[],
                             dest="excludes", metavar="PATTERN",
                             help="Exclude files or directories matching this glob-style "
                                  "pattern. Use multiple times to exclude more."),
        optparse.make_option("-w", "--wipe",
                             action="store_true", dest="wipe", default=False,
                             help="Wipes out entire contents of container first."),
        optparse.make_option("-t", "--test-run",
                             action="store_true", dest="test_run", default=False,
                             help="Performs a test run of the sync."),
        optparse.make_option("-q", "--quiet",
                             action="store_true", dest="test_run", default=False,
                             help="Do not display any output."),
        optparse.make_option("-c", "--container",
                             dest="container", help="Override STATIC_CONTAINER."),
    )

    def set_options(self, options):
        """
        Sets instance variables based on an options dict
        """
        # COMMAND LINE OPTIONS
        self.wipe = options.get("wipe")
        self.test_run = options.get("test_run")
        self.quiet = options.get("test_run")
        self.container_name = options.get("container")
        self.verbosity = int(options.get("verbosity"))
        if self.test_run:
            self.verbosity = 2
        cli_includes = options.get("includes")
        cli_excludes = options.get("excludes")

        # CUMULUS CONNECTION AND SETTINGS FROM SETTINGS.PY
        if not self.container_name:
            self.container_name = CUMULUS["STATIC_CONTAINER"]
        settings_includes = CUMULUS["INCLUDE_LIST"]
        settings_excludes = CUMULUS["EXCLUDE_LIST"]

        # PATH SETTINGS
        self.static_root = os.path.abspath(settings.STATIC_ROOT)
        self.static_url = settings.STATIC_URL
        if not self.static_root.endswith("/"):
            self.static_root = self.static_root + "/"
        if self.static_url.startswith("/"):
            self.static_url = self.static_url[1:]

        # SYNCSTATIC VARS
        # combine includes and excludes from the cli and django settings file
        self.includes = list(set(cli_includes + settings_includes))
        self.excludes = list(set(cli_excludes + settings_excludes))
        # transform glob patterns to regular expressions
        self.local_filenames = []
        self.create_count = 0
        self.upload_count = 0
        self.update_count = 0
        self.skip_count = 0
        self.delete_count = 0

    def connect_container(self):
        """
        Connects to a container using the swiftclient api.

        The container will be created and/or made public using the
        pyrax api if not already so.
        """
        self.conn = swiftclient.Connection(authurl=CUMULUS["AUTH_URL"],
                                           user=CUMULUS["USERNAME"],
                                           key=CUMULUS["API_KEY"],
                                           snet=CUMULUS["SERVICENET"],
                                           auth_version=CUMULUS["AUTH_VERSION"],
                                           tenant_name=CUMULUS["AUTH_TENANT_NAME"])
        try:
            self.conn.head_container(self.container_name)
        except swiftclient.client.ClientException as exception:
            if exception.msg == "Container HEAD failed":
                call_command("container_create", self.container_name)
            else:
                raise

        if CUMULUS["USE_PYRAX"]:
            if CUMULUS["PYRAX_IDENTITY_TYPE"]:
                pyrax.set_setting("identity_type", CUMULUS["PYRAX_IDENTITY_TYPE"])
            public = not CUMULUS["SERVICENET"]
            pyrax.set_credentials(CUMULUS["USERNAME"], CUMULUS["API_KEY"])
            connection = pyrax.connect_to_cloudfiles(region=CUMULUS["REGION"],
                                                     public=public)
            container = connection.get_container(self.container_name)
            if not container.cdn_enabled:
                container.make_public(ttl=CUMULUS["TTL"])
        else:
            headers = {"X-Container-Read": ".r:*"}
            self.conn.post_container(self.container_name, headers=headers)

        self.container = self.conn.get_container(self.container_name, full_listing=True)

    def handle_noargs(self, *args, **options):
        # setup
        self.set_options(options)
        self.connect_container()

        # wipe first
        if self.wipe:
            self.wipe_container()

        # match local files
        abspaths = self.match_local(self.static_root, self.includes, self.excludes)
        relpaths = []
        for path in abspaths:
            filename = path.split(self.static_root)[1]
            if filename.startswith("/"):
                filename = filename[1:]
            relpaths.append(filename)
        if not relpaths:
            raise CommandError("The STATIC_ROOT directory is empty "
                               "or all files have been ignored.")
        for path in abspaths:
            if not os.path.isfile(path):
                raise CommandError("Unsupported filetype: {0}.".format(path))

        # match cloud objects
        cloud_objs = self.match_cloud(self.includes, self.excludes)

        remote_objects = {
            obj['name']: datetime.datetime.strptime(obj['last_modified'],
                                "%Y-%m-%dT%H:%M:%S.%f") for obj in self.container[1]
        }

        # sync
        self.upload_files(abspaths, relpaths, remote_objects)
        self.delete_extra_files(relpaths, cloud_objs)

        if not self.quiet or self.verbosity > 1:
            self.print_tally()

    def match_cloud(self, includes, excludes):
        """
        Returns the cloud objects that match the include and exclude patterns.
        """
        cloud_objs = [cloud_obj["name"] for cloud_obj in self.container[1]]
        includes_pattern = r"|".join([fnmatch.translate(x) for x in includes])
        excludes_pattern = r"|".join([fnmatch.translate(x) for x in excludes]) or r"$."
        excludes = [o for o in cloud_objs if re.match(excludes_pattern, o)]
        includes = [o for o in cloud_objs if re.match(includes_pattern, o)]
        return [o for o in includes if o not in excludes]

    def match_local(self, prefix, includes, excludes):
        """
        Filters os.walk() with include and exclude patterns.
        See: http://stackoverflow.com/a/5141829/93559
        """
        includes_pattern = r"|".join([fnmatch.translate(x) for x in includes])
        excludes_pattern = r"|".join([fnmatch.translate(x) for x in excludes]) or r"$."
        matches = []
        for root, dirs, files in os.walk(prefix, topdown=True):
            # exclude dirs
            dirs[:] = [os.path.join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.match(excludes_pattern,
                                                       d.split(root)[1])]
            # exclude/include files
            files = [os.path.join(root, f) for f in files]
            files = [os.path.join(root, f) for f in files
                     if not re.match(excludes_pattern, f)]
            files = [os.path.join(root, f) for f in files
                     if re.match(includes_pattern, f.split(prefix)[1])]
            for fname in files:
                matches.append(fname)
        return matches

    def upload_files(self, abspaths, relpaths, remote_objects):
        """
        Determines files to be uploaded and call ``upload_file`` on each.
        """
        for relpath in relpaths:
            abspath = [p for p in abspaths if p.endswith(relpath)][0]
            cloud_datetime = remote_objects[relpath] if relpath in remote_objects else None
            local_datetime = datetime.datetime.utcfromtimestamp(os.stat(abspath).st_mtime)

            if cloud_datetime and local_datetime < cloud_datetime:
                self.skip_count += 1
                if not self.quiet:
                    print("Skipped {0}: not modified.".format(relpath))
                continue
            if relpath in remote_objects:
                self.update_count += 1
            else:
                self.create_count += 1
            self.upload_file(abspath, relpath)

    def upload_file(self, abspath, cloud_filename):
        """
        Uploads a file to the container.
        """
        if not self.test_run:
            content = open(abspath, "rb")
            content_type = get_content_type(cloud_filename, content)
            headers = get_headers(cloud_filename, content_type)

            if headers.get("Content-Encoding") == "gzip":
                content = get_gzipped_contents(content)
                size = content.size
            else:
                size = os.stat(abspath).st_size

            self.conn.put_object(
                container=self.container_name,
                obj=cloud_filename,
                contents=content,
                content_length=size,
                etag=None,
                content_type=content_type,
                headers=headers)

            # TODO syncheaders
            #from cumulus.storage import sync_headers
            #sync_headers(cloud_obj)
        self.upload_count += 1
        if not self.quiet or self.verbosity > 1:
            print("Uploaded: {0}".format(cloud_filename))

    def delete_extra_files(self, relpaths, cloud_objs):
        """
        Deletes any objects from the container that do not exist locally.
        """
        for cloud_obj in cloud_objs:
            if cloud_obj not in relpaths:
                if not self.test_run:
                    self.delete_cloud_obj(cloud_obj)
                self.delete_count += 1
                if not self.quiet or self.verbosity > 1:
                    print("Deleted: {0}".format(cloud_obj))

    def delete_cloud_obj(self, cloud_obj):
        """
        Deletes an object from the container.
        """
        self.conn.delete_object(container=self.container_name,
                                obj=cloud_obj)

    def wipe_container(self):
        """
        Completely wipes out the contents of the container.
        """
        if self.test_run:
            print("Wipe would delete {0} objects.".format(len(self.container[1])))
        else:
            if not self.quiet or self.verbosity > 1:
                print("Deleting {0} objects...".format(len(self.container[1])))
            for cloud_obj in self.container[1]:
                self.conn.delete_object(self.container_name, cloud_obj["name"])

    def print_tally(self):
        """
        Prints the final tally to stdout.
        """
        self.update_count = self.upload_count - self.create_count
        if self.test_run:
            print("Test run complete with the following results:")
        print("Skipped {0}. Created {1}. Updated {2}. Deleted {3}.".format(
            self.skip_count, self.create_count, self.update_count, self.delete_count))

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
from pyrax.cf_wrapper.client import CFClient

from django.conf import settings


CUMULUS = {
    "API_KEY": None,
    "AUTH_URL": "us_authurl",
    "AUTH_VERSION": "1.0",
    "AUTH_TENANT_NAME": None,
    "AUTH_TENANT_ID": None,
    "REGION": "DFW",
    "CNAMES": None,
    "CONTAINER": None,
    "CONTAINER_URI": None,
    "CONTAINER_SSL_URI": None,
    "SERVICENET": False,
    "TIMEOUT": 5,
    "TTL": CFClient.default_cdn_ttl,  # 86400s (24h), pyrax default
    "USE_SSL": False,
    "USERNAME": None,
    "STATIC_CONTAINER": None,
    "STATIC_CONTAINER_URI": None,
    "STATIC_CONTAINER_SSL_URI": None,
    "INCLUDE_LIST": [],
    "EXCLUDE_LIST": [],
    "HEADERS": {},
    "GZIP_CONTENT_TYPES": [],
    "USE_PYRAX": True,
    "PYRAX_IDENTITY_TYPE": None,
    "FILE_TTL": CFClient.default_cdn_ttl
}

if hasattr(settings, "CUMULUS"):
    CUMULUS.update(settings.CUMULUS)

# set the full rackspace auth_url
if CUMULUS["AUTH_URL"] == "us_authurl":
    CUMULUS["AUTH_URL"] = "https://auth.api.rackspacecloud.com/v1.0"
elif CUMULUS["AUTH_URL"] == "uk_authurl":
    CUMULUS["AUTH_URL"] = "https://lon.auth.api.rackspacecloud.com/v1.0"

########NEW FILE########
__FILENAME__ = storage
import mimetypes
import pyrax
import re
import swiftclient
from gzip import GzipFile

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core.files.base import File, ContentFile
from django.core.files.storage import Storage

from cumulus.settings import CUMULUS


HEADER_PATTERNS = tuple((re.compile(p), h) for p, h in CUMULUS.get("HEADERS", {}))


def get_content_type(name, content):
    """
    Checks if the content_type is already set.
    Otherwise uses the mimetypes library to guess.
    """
    if hasattr(content, "content_type"):
        content_type = content.content_type
    else:
        mime_type, encoding = mimetypes.guess_type(name)
        content_type = mime_type
    return content_type


def get_headers(name, content_type):
    headers = {"Content-Type": content_type}
    # gzip the file if its of the right content type
    if content_type in CUMULUS.get("GZIP_CONTENT_TYPES", []):
        headers["Content-Encoding"] = "gzip"
    if CUMULUS["HEADERS"]:
        for pattern, pattern_headers in HEADER_PATTERNS:
            if pattern.match(name):
                headers.update(pattern_headers.copy())
    return headers


def sync_headers(cloud_obj, headers={}, header_patterns=HEADER_PATTERNS):
    """
    Overwrites the given cloud_obj's headers with the ones given as ``headers`
    and adds additional headers as defined in the HEADERS setting depending on
    the cloud_obj's file name.
    """
    # don't set headers on directories
    content_type = getattr(cloud_obj, "content_type", None)
    if content_type == "application/directory":
        return
    matched_headers = {}
    for pattern, pattern_headers in header_patterns:
        if pattern.match(cloud_obj.name):
            matched_headers.update(pattern_headers.copy())
    # preserve headers already set
    matched_headers.update(cloud_obj.headers)
    # explicitly set headers overwrite matches and already set headers
    matched_headers.update(headers)
    if matched_headers != cloud_obj.headers:
        cloud_obj.headers = matched_headers
        cloud_obj.sync_metadata()


def get_gzipped_contents(input_file):
    """
    Returns a gzipped version of a previously opened file's buffer.
    """
    zbuf = StringIO()
    zfile = GzipFile(mode="wb", compresslevel=6, fileobj=zbuf)
    zfile.write(input_file.read())
    zfile.close()
    return ContentFile(zbuf.getvalue())


class SwiftclientStorage(Storage):
    """
    Custom storage for Swiftclient.
    """
    default_quick_listdir = True
    api_key = CUMULUS["API_KEY"]
    auth_url = CUMULUS["AUTH_URL"]
    region = CUMULUS["REGION"]
    connection_kwargs = {}
    container_name = CUMULUS["CONTAINER"]
    container_uri = CUMULUS["CONTAINER_URI"]
    container_ssl_uri = CUMULUS["CONTAINER_SSL_URI"]
    use_snet = CUMULUS["SERVICENET"]
    username = CUMULUS["USERNAME"]
    ttl = CUMULUS["TTL"]
    use_ssl = CUMULUS["USE_SSL"]
    use_pyrax = CUMULUS["USE_PYRAX"]

    def __init__(self, username=None, api_key=None, container=None,
                 connection_kwargs=None, container_uri=None):
        """
        Initializes the settings for the connection and container.
        """
        if username is not None:
            self.username = username
        if api_key is not None:
            self.api_key = api_key
        if container is not None:
            self.container_name = container
        if connection_kwargs is not None:
            self.connection_kwargs = connection_kwargs
        # connect
        if CUMULUS["USE_PYRAX"]:
            if CUMULUS["PYRAX_IDENTITY_TYPE"]:
                pyrax.set_setting("identity_type", CUMULUS["PYRAX_IDENTITY_TYPE"])
            if CUMULUS["AUTH_URL"]:
                pyrax.set_setting("auth_endpoint", CUMULUS["AUTH_URL"])
            if CUMULUS["AUTH_TENANT_ID"]:
                pyrax.set_setting("tenant_id", CUMULUS["AUTH_TENANT_ID"])

            pyrax.set_credentials(self.username, self.api_key)

    def __getstate__(self):
        """
        Return a picklable representation of the storage.
        """
        return {
            "username": self.username,
            "api_key": self.api_key,
            "container_name": self.container_name,
            "use_snet": self.use_snet,
            "connection_kwargs": self.connection_kwargs
        }

    def _get_connection(self):
        if not hasattr(self, "_connection"):
            if CUMULUS["USE_PYRAX"]:
                public = not self.use_snet  # invert
                self._connection = pyrax.connect_to_cloudfiles(region=self.region,
                                                               public=public)
            else:
                self._connection = swiftclient.Connection(
                    authurl=CUMULUS["AUTH_URL"],
                    user=CUMULUS["USERNAME"],
                    key=CUMULUS["API_KEY"],
                    snet=CUMULUS["SERVICENET"],
                    auth_version=CUMULUS["AUTH_VERSION"],
                    tenant_name=CUMULUS["AUTH_TENANT_NAME"],
                )
        return self._connection

    def _set_connection(self, value):
        self._connection = value

    connection = property(_get_connection, _set_connection)

    def _get_container(self):
        """
        Gets or creates the container.
        """
        if not hasattr(self, "_container"):
            if CUMULUS["USE_PYRAX"]:
                self._container = self.connection.create_container(self.container_name)
            else:
                self._container = None
        return self._container

    def _set_container(self, container):
        """
        Sets the container (and, if needed, the configured TTL on it), making
        the container publicly available.
        """
        if CUMULUS["USE_PYRAX"]:
            if container.cdn_ttl != self.ttl or not container.cdn_enabled:
                container.make_public(ttl=self.ttl)
            if hasattr(self, "_container_public_uri"):
                delattr(self, "_container_public_uri")
        self._container = container

    container = property(_get_container, _set_container)

    def _get_container_url(self):
        if self.use_ssl and self.container_ssl_uri:
            self._container_public_uri = self.container_ssl_uri
        elif self.use_ssl:
            self._container_public_uri = self.container.cdn_ssl_uri
        elif self.container_uri:
            self._container_public_uri = self.container_uri
        else:
            self._container_public_uri = self.container.cdn_uri
        if CUMULUS["CNAMES"] and self._container_public_uri in CUMULUS["CNAMES"]:
            self._container_public_uri = CUMULUS["CNAMES"][self._container_public_uri]
        return self._container_public_uri

    container_url = property(_get_container_url)

    def _get_object(self, name):
        """
        Helper function to retrieve the requested Object.
        """
        try:
            return self.container.get_object(name)
        except pyrax.exceptions.NoSuchObject, swiftclient.exceptions.ClientException:
            return None

    def _open(self, name, mode="rb"):
        """
        Returns the SwiftclientStorageFile.
        """
        return SwiftclientStorageFile(storage=self, name=name)

    def _save(self, name, content):
        """
        Uses the Swiftclient service to write ``content`` to a remote
        file (called ``name``).
        """
        content_type = get_content_type(name, content.file)
        headers = get_headers(name, content_type)

        if CUMULUS["USE_PYRAX"]:
            if headers.get("Content-Encoding") == "gzip":
                content = get_gzipped_contents(content)
            self.connection.store_object(container=self.container_name,
                                         obj_name=name,
                                         data=content.read(),
                                         content_type=content_type,
                                         content_encoding=headers.get("Content-Encoding", None),
                                         ttl=CUMULUS["FILE_TTL"],
                                         etag=None)
            # set headers/object metadata
            self.connection.set_object_metadata(container=self.container_name,
                                                obj=name,
                                                metadata=headers,
                                                prefix='')
        else:
            # TODO gzipped content when using swift client
            self.connection.put_object(self.container_name, name,
                                       content, headers=headers)

        return name

    def delete(self, name):
        """
        Deletes the specified file from the storage system.

        Deleting a model doesn't delete associated files: bit.ly/12s6Oox
        """
        try:
            self.connection.delete_object(self.container_name, name)
        except pyrax.exceptions.ClientException as exc:
            if exc.http_status == 404:
                pass
            else:
                raise

    def exists(self, name):
        """
        Returns True if a file referenced by the given name already
        exists in the storage system, or False if the name is
        available for a new file.
        """
        return bool(self._get_object(name))

    def size(self, name):
        """
        Returns the total size, in bytes, of the file specified by name.
        """
        return self._get_object(name).total_bytes

    def url(self, name):
        """
        Returns an absolute URL where the content of each file can be
        accessed directly by a web browser.
        """
        return "{0}/{1}".format(self.container_url, name)

    def listdir(self, path):
        """
        Lists the contents of the specified path, returning a 2-tuple;
        the first being an empty list of directories (not available
        for quick-listing), the second being a list of filenames.

        If the list of directories is required, use the full_listdir method.
        """
        files = []
        if path and not path.endswith("/"):
            path = "{0}/".format(path)
        path_len = len(path)
        for name in [x["name"] for x in
                     self.connection.get_container(self.container_name, full_listing=True)[1]]:
            files.append(name[path_len:])
        return ([], files)

    def full_listdir(self, path):
        """
        Lists the contents of the specified path, returning a 2-tuple
        of lists; the first item being directories, the second item
        being files.
        """
        dirs = set()
        files = []
        if path and not path.endswith("/"):
            path = "{0}/".format(path)
        path_len = len(path)
        for name in [x["name"] for x in
                     self.connection.get_container(self.container_name, full_listing=True)[1]]:
            name = name[path_len:]
            slash = name[1:-1].find("/") + 1
            if slash:
                dirs.add(name[:slash])
            elif name:
                files.append(name)
        dirs = list(dirs)
        dirs.sort()
        return (dirs, files)


class SwiftclientStaticStorage(SwiftclientStorage):
    """
    Subclasses SwiftclientStorage to automatically set the container
    to the one specified in CUMULUS["STATIC_CONTAINER"]. This provides
    the ability to specify a separate storage backend for Django's
    collectstatic command.

    To use, make sure CUMULUS["STATIC_CONTAINER"] is set to something other
    than CUMULUS["CONTAINER"]. Then, tell Django's staticfiles app by setting
    STATICFILES_STORAGE = "cumulus.storage.SwiftclientStaticStorage".
    """
    container_name = CUMULUS["STATIC_CONTAINER"]
    container_uri = CUMULUS["STATIC_CONTAINER_URI"]
    container_ssl_uri = CUMULUS["STATIC_CONTAINER_SSL_URI"]


class SwiftclientStorageFile(File):
    closed = False

    def __init__(self, storage, name, *args, **kwargs):
        self._storage = storage
        self._pos = 0
        self._chunks = None
        super(SwiftclientStorageFile, self).__init__(file=None, name=name,
                                                     *args, **kwargs)

    def _get_pos(self):
        return self._pos

    def _get_size(self):
        if not hasattr(self, "_size"):
            self._size = self._storage.size(self.name)
        return self._size

    def _set_size(self, size):
        self._size = size

    size = property(_get_size, _set_size)

    def _get_file(self):
        if not hasattr(self, "_file"):
            self._file = self._storage._get_object(self.name)
            self._file.tell = self._get_pos
        return self._file

    def _set_file(self, value):
        if value is None:
            if hasattr(self, "_file"):
                del self._file
        else:
            self._file = value

    file = property(_get_file, _set_file)

    def read(self, chunk_size=None):
        """
        Reads specified chunk_size or the whole file if chunk_size is None.

        If reading the whole file and the content-encoding is gzip, also
        gunzip the read content.

        If chunk_size is provided, the same chunk_size will be used in all
        further read() calls until the file is reopened or seek() is called.
        """
        if self._pos >= self._get_size() or chunk_size == 0:
            return ""

        if chunk_size is None and self._chunks is None:
            meta, data = self.file.get(include_meta=True)
            if meta.get("content-encoding", None) == "gzip":
                zbuf = StringIO(data)
                zfile = GzipFile(mode="rb", fileobj=zbuf)
                data = zfile.read()
        else:
            if self._chunks is None:
                # When reading by chunks, we're supposed to read the whole file
                # before calling get() again.
                self._chunks = self.file.get(chunk_size=chunk_size)

            try:
                data = self._chunks.next()
            except StopIteration:
                data = ""

        self._pos += len(data)
        return data

    def chunks(self, chunk_size=None):
        """
        Returns an iterator of file where each chunk has chunk_size.
        """
        if not chunk_size:
            chunk_size = self.DEFAULT_CHUNK_SIZE
        return self.file.get(chunk_size=chunk_size)

    def open(self, *args, **kwargs):
        """
        Opens the cloud file object.
        """
        self._pos = 0
        self._chunks = None

    def close(self, *args, **kwargs):
        self._pos = 0
        self._chunks = None

    @property
    def closed(self):
        return not hasattr(self, "_file")

    def seek(self, pos):
        self._pos = pos
        self._chunks = None


class ThreadSafeSwiftclientStorage(SwiftclientStorage):
    """
    Extends SwiftclientStorage to make it mostly thread safe.

    As long as you do not pass container or cloud objects between
    threads, you will be thread safe.

    Uses one connection/container per thread.
    """
    def __init__(self, *args, **kwargs):
        super(ThreadSafeSwiftclientStorage, self).__init__(*args, **kwargs)

        import threading
        self.local_cache = threading.local()

    def _get_connection(self):
        if not hasattr(self.local_cache, "connection"):
            public = not self.use_snet  # invert
            connection = pyrax.connect_to_cloudfiles(region=self.region,
                                                     public=public)
            self.local_cache.connection = connection

        return self.local_cache.connection

    connection = property(_get_connection, SwiftclientStorage._set_connection)

    def _get_container(self):
        if not hasattr(self.local_cache, "container"):
            container = self.connection.create_container(self.container_name)
            self.local_cache.container = container

        return self.local_cache.container

    container = property(_get_container, SwiftclientStorage._set_container)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from cumulus.storage import SwiftclientStorage

openstack_storage = SwiftclientStorage()


class Thing(models.Model):
    "A dummy model to use for tests."
    image = models.ImageField(storage=openstack_storage,
                              upload_to="cumulus-tests",
                              blank=True)
    document = models.FileField(storage=openstack_storage, upload_to="cumulus-tests")
    custom = models.FileField(storage=openstack_storage, upload_to="cumulus-tests")

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-cumulus documentation build configuration file, created by
# sphinx-quickstart on Tue Feb  9 09:08:23 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-cumulus'
copyright = u'2010, Rich Leland'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0.5'
# The full version, including alpha/beta/rc tags.
release = '1.0.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = ['_theme']

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
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-cumulusdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'django-cumulus.tex', u'django-cumulus Documentation',
     u'Rich Leland', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import imp
try:
    imp.find_module("settings")  # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write(
        "Error: Can't find the file 'settings.py' in the directory containing"
        "{0}. It appears you've customized things.\nYou'll have to run"
        "django-admin.py, passing it your settings module.\n".format(__file__))
    sys.exit(1)

from django.core.management import execute_manager

import settings


if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from photos.models import Photo


admin.site.register(Photo)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Photo(models.Model):
    title = models.CharField(max_length=50)
    image = models.ImageField(upload_to='photos')

    def __unicode__(self):
        return self.title

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = common
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',              # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '!gz7b74mfu7^mj0yj&dxc&^$o7tf%^0&i07y7s#zv73x($g%pa'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'cumulus',

    'photos',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

DEFAULT_FILE_STORAGE = 'cumulus.storage.SwiftclientStorage'
#STATICFILES_STORAGE = 'cumulus.storage.SwiftclientStaticStorage'

# these are the default cumulus settings
CUMULUS = {
    "API_KEY": os.environ.get("CUMULUS_API_KEY", None),
    'AUTH_URL': 'us_authurl',
    'REGION': 'DFW',
    'CNAMES': None,
    'CONTAINER': 'cumulus-content-tests',
    'CONTAINER_URI': None,
    'CONTAINER_SSL_URI': None,
    'STATIC_CONTAINER': 'cumulus-static-tests',
    'SERVICENET': False,
    'TIMEOUT': 5,
    'TTL': 600,
    'USE_SSL': False,
    "USERNAME": os.environ.get("CUMULUS_USERNAME", None),
    'INCLUDE_LIST': [],
    'EXCLUDE_LIST': [],
    'HEADERS': {},
    'GZIP_CONTENT_TYPES': [],
    'USE_PYRAX': True,
}

try:
    from local_settings import *  # noqa
except:
    pass

########NEW FILE########
__FILENAME__ = legacy
from common import *  # noqa

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',

    'cumulus',
    'cumulus.tests',

    'photos',
)

########NEW FILE########
__FILENAME__ = test
from common import *  # noqa

INSTALLED_APPS += (
    'cumulus.tests',
)

########NEW FILE########
__FILENAME__ = urls
from django.contrib import admin
from django.conf.urls.defaults import patterns, include, url

admin.autodiscover()


urlpatterns = patterns(
    "",

    url(r"^admin/", include(admin.site.urls)),
)

########NEW FILE########
