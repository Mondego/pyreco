__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from wal_e.cmd import external_program_check
from wal_e.pipeline import PV_BIN


def runtests(args=None):
    import pytest

    external_program_check([PV_BIN])

    if args is None:
        args = []

    sys.exit(pytest.main(args))


if __name__ == '__main__':
    runtests(sys.argv)

########NEW FILE########
__FILENAME__ = blackbox
import os
import pytest
import s3_integration_help
import sys

from wal_e import cmd

_PREFIX_VARS = ['WALE_S3_PREFIX', 'WALE_WABS_PREFIX', 'WALE_SWIFT_PREFIX']

_AWS_CRED_ENV_VARS = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                      'AWS_SECURITY_TOKEN']


class AwsTestConfig(object):
    name = 'aws'

    def __init__(self, request):
        self.env_vars = {}
        self.monkeypatch = request.getfuncargvalue('monkeypatch')

        for name in _AWS_CRED_ENV_VARS:
            maybe_value = os.getenv(name)
            self.env_vars[name] = maybe_value

    def patch(self, test_name, default_test_bucket):
        # Scrub WAL-E prefixes left around in the user's environment to
        # prevent unexpected results.
        for name in _PREFIX_VARS:
            self.monkeypatch.delenv(name, raising=False)

        # Set other credentials.
        for name, value in self.env_vars.iteritems():
            if value is None:
                self.monkeypatch.delenv(name, raising=False)
            else:
                self.monkeypatch.setenv(name, value)

        self.monkeypatch.setenv('WALE_S3_PREFIX', 's3://{0}/{1}'
                                .format(default_test_bucket, test_name))

    def main(self, *args):
        self.monkeypatch.setattr(sys, 'argv', ['wal-e'] + list(args))
        return cmd.main()


class AwsInstanceProfileTestConfig(object):
    name = 'aws+instance-profile'

    def __init__(self, request):
        self.request = request
        self.monkeypatch = request.getfuncargvalue('monkeypatch')

    def patch(self, test_name, default_test_bucket):
        # Get STS-vended credentials to stand in for Instance Profile
        # credentials before scrubbing the environment of AWS
        # environment variables.
        c = s3_integration_help.sts_conn()
        policy = s3_integration_help.make_policy(default_test_bucket,
                                                 test_name)
        fed = c.get_federation_token(default_test_bucket, policy=policy)

        # Scrub AWS environment-variable based cred to make sure the
        # instance profile path is used.
        for name in _AWS_CRED_ENV_VARS:
            self.monkeypatch.delenv(name, raising=False)

        self.monkeypatch.setenv('WALE_S3_PREFIX', 's3://{0}/{1}'
                                .format(default_test_bucket, test_name))

        # Patch boto.utils.get_instance_metadata to return a ginned up
        # credential.
        m = {
            "Code": "Success",
            "LastUpdated": "3014-01-11T02:13:53Z",
            "Type": "AWS-HMAC",
            "AccessKeyId": fed.credentials.access_key,
            "SecretAccessKey": fed.credentials.secret_key,
            "Token": fed.credentials.session_token,
            "Expiration": "3014-01-11T08:16:59Z"
        }

        from boto import provider
        self.monkeypatch.setattr(provider.Provider,
                            '_credentials_need_refresh',
                            lambda self: False)

        # Different versions of boto require slightly different return
        # formats.
        import test_aws_instance_profiles
        if test_aws_instance_profiles.boto_flat_metadata():
            m = {'irrelevant': m}
        else:
            m = {'iam': {'security-credentials': {'irrelevant': m}}}
        from boto import utils

        self.monkeypatch.setattr(utils, 'get_instance_metadata',
                            lambda *args, **kwargs: m)

    def main(self, *args):
        self.monkeypatch.setattr(
            sys, 'argv', ['wal-e', '--aws-instance-profile'] + list(args))
        return cmd.main()


def _make_fixture_param_and_ids():
    ret = {
        'params': [],
        'ids': [],
    }

    def _add_config(c):
        ret['params'].append(c)
        ret['ids'].append(c.name)

    if not s3_integration_help.no_real_s3_credentials():
        _add_config(AwsTestConfig)
        _add_config(AwsInstanceProfileTestConfig)

    return ret


@pytest.fixture(**_make_fixture_param_and_ids())
def config(request, monkeypatch, default_test_bucket):
    config = request.param(request)
    config.patch(request.node.name, default_test_bucket)
    return config


class NoopPgBackupStatements(object):
    @classmethod
    def run_start_backup(cls):
        name = '0' * 8 * 3
        offset = '0' * 8
        return {'file_name': name,
                'file_offset': offset,
                'pg_xlogfile_name_offset':
                'START-BACKUP-FAKE-XLOGPOS'}

    @classmethod
    def run_stop_backup(cls):
        name = '1' * 8 * 3
        offset = '1' * 8
        return {'file_name': name,
                'file_offset': offset,
                'pg_xlogfile_name_offset':
                'STOP-BACKUP-FAKE-XLOGPOS'}

    @classmethod
    def pg_version(cls):
        return {'version': 'FAKE-PG-VERSION'}


@pytest.fixture
def noop_pg_backup_statements(monkeypatch):
    import wal_e.operator.backup

    monkeypatch.setattr(wal_e.operator.backup, 'PgBackupStatements',
                        NoopPgBackupStatements)

    # psql binary test will fail if local pg env isn't set up
    monkeypatch.setattr(wal_e.cmd, 'external_program_check',
                        lambda *args, **kwargs: None)


@pytest.fixture
def small_push_dir(tmpdir):
    """Create a small pg data directory-alike"""
    contents = 'abcdefghijlmnopqrstuvwxyz\n' * 10000
    push_dir = tmpdir.join('push-from').ensure(dir=True)
    push_dir.join('arbitrary-file').write(contents)

    # Construct a symlink a non-existent path.  This provoked a crash
    # at one time.
    push_dir.join('pg_xlog').mksymlinkto('/tmp/wal-e-test-must-not-exist')

    # Holy crap, the tar segmentation code relies on the directory
    # containing files without a common prefix...the first character
    # of two files must be distinct!
    push_dir.join('holy-smokes').ensure()

    return push_dir

########NEW FILE########
__FILENAME__ = pipe_performance
#!/usr/bin/env python
#
# Simplistic command line utility to measure pipe throughput and CPU
# usage.
#
# This was written to probe performance in pipe buffering.  It is not
# comprehensive but rather a starting point to be hacked up to
# evaluate changes pipeline performance.

import gevent
import signal
import time
import traceback

from wal_e import pipeline
from wal_e import piper

ONE_MB_IN_BYTES = 2 ** 20
PATTERN = 'abcdefghijklmnopqrstuvwxyz\n'
OVER_TEN_MEGS = PATTERN * ((ONE_MB_IN_BYTES / len(PATTERN) + 1))


def debug(sig, frame):
    # Adapted from
    # "showing-the-stack-trace-from-a-running-python-application".
    d = {'_frame': frame}
    d.update(frame.f_globals)
    d.update(frame.f_locals)

    message = "SIGUSR1 recieved: .\nTraceback:\n"
    message += ''.join(traceback.format_stack(frame))
    print message


def listen():
    signal.signal(signal.SIGUSR1, debug)  # Register handler


def consume(f):
    while f.read(ONE_MB_IN_BYTES):
        gevent.sleep()


def produce(f):
    while True:
        f.write(OVER_TEN_MEGS)

    f.flush()
    f.close()


def churn_at_rate_limit(rate_limit, bench_seconds):
    commands = [pipeline.PipeViewerRateLimitFilter(
        rate_limit, piper.PIPE, piper.PIPE)]
    pl = pipeline.Pipeline(commands, piper.PIPE, piper.PIPE)

    gevent.spawn(consume, pl.stdout)
    gevent.spawn(produce, pl.stdin)
    gevent.sleep(bench_seconds)


def main():
    bench_seconds = 10.0

    listen()

    cpu_start = time.clock()
    churn_at_rate_limit(ONE_MB_IN_BYTES * 1000, bench_seconds)
    cpu_finish = time.clock()

    print 'cpu use:', 100 * ((cpu_finish - cpu_start) / float(bench_seconds))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = s3_integration_help
import boto
import json
import os
import pytest

from boto import sts
from boto.s3.connection import Location
from wal_e.blobstore import s3
from wal_e.blobstore.s3 import calling_format


def no_real_s3_credentials():
    """Helps skip integration tests without live credentials.

    Phrased in the negative to make it read better with 'skipif'.
    """
    if os.getenv('WALE_S3_INTEGRATION_TESTS') != 'TRUE':
        return True

    for e_var in ('AWS_ACCESS_KEY_ID',
                  'AWS_SECRET_ACCESS_KEY'):
        if os.getenv(e_var) is None:
            return True

    return False


def prepare_s3_default_test_bucket():
    # Check credentials are present: this procedure should not be
    # called otherwise.
    if no_real_s3_credentials():
        assert False

    bucket_name = 'waletdefwuy' + os.getenv('AWS_ACCESS_KEY_ID').lower()

    creds = s3.Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                           os.getenv('AWS_SECRET_ACCESS_KEY'),
                           os.getenv('AWS_SECURITY_TOKEN'))

    cinfo = calling_format.from_store_name(bucket_name)
    conn = cinfo.connect(creds)

    def _clean():
        bucket = conn.get_bucket(bucket_name)
        bucket.delete_keys(key.name for key in bucket.list())

    try:
        conn.create_bucket(bucket_name, location=Location.USWest)
    except boto.exception.S3CreateError, e:
        if e.status == 409:
            # Conflict: bucket already present.  Re-use it, but
            # clean it out first.
            _clean()
        else:
            raise
    else:
        # Success
        _clean()

    return bucket_name


@pytest.fixture(scope='session')
def default_test_bucket():
    if not no_real_s3_credentials():
        return prepare_s3_default_test_bucket()


def boto_supports_certs():
    return tuple(int(x) for x in boto.__version__.split('.')) >= (2, 6, 0)


def make_policy(bucket_name, prefix, allow_get_location=False):
    """Produces a S3 IAM text for selective access of data.

    Only a prefix can be listed, gotten, or written to when a
    credential is subject to this policy text.
    """
    bucket_arn = "arn:aws:s3:::" + bucket_name
    prefix_arn = "arn:aws:s3:::{0}/{1}/*".format(bucket_name, prefix)

    structure = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:ListBucket"],
                "Effect": "Allow",
                "Resource": [bucket_arn],
                "Condition": {"StringLike": {"s3:prefix": [prefix + '/*']}},
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject"],
                "Resource": [prefix_arn]
            }]}

    if allow_get_location:
        structure["Statement"].append(
            {"Action": ["s3:GetBucketLocation"],
             "Effect": "Allow",
             "Resource": [bucket_arn]})

    return json.dumps(structure, indent=2)


@pytest.fixture
def sts_conn():
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    return sts.connect_to_region(
        'us-east-1',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key)


def _delete_keys(bucket, keys):
    for name in keys:
        while True:
            try:
                k = boto.s3.connection.Key(bucket, name)
                bucket.delete_key(k)
            except boto.exception.S3ResponseError, e:
                if e.status == 404:
                    # Key is already not present.  Continue the
                    # deletion iteration.
                    break

                raise
            else:
                break


def apathetic_bucket_delete(bucket_name, keys, *args, **kwargs):
    conn = boto.s3.connection.S3Connection(*args, **kwargs)
    bucket = conn.lookup(bucket_name)

    if bucket:
        # Delete key names passed by the test code.
        _delete_keys(conn.lookup(bucket_name), keys)

    try:
        conn.delete_bucket(bucket_name)
    except boto.exception.S3ResponseError, e:
        if e.status == 404:
            # If the bucket is already non-existent, then the bucket
            # need not be destroyed from a prior test run.
            pass
        else:
            raise

    return conn


def insistent_bucket_delete(conn, bucket_name, keys):
    bucket = conn.lookup(bucket_name)

    if bucket:
        # Delete key names passed by the test code.
        _delete_keys(bucket, keys)

    while True:
        try:
            conn.delete_bucket(bucket_name)
        except boto.exception.S3ResponseError, e:
            if e.status == 404:
                # Create not yet visible, but it just happened above:
                # keep trying.  Potential consistency.
                continue
            else:
                raise

        break


def insistent_bucket_create(conn, bucket_name, *args, **kwargs):
    while True:
        try:
            bucket = conn.create_bucket(bucket_name, *args, **kwargs)
        except boto.exception.S3CreateError, e:
            if e.status == 409:
                # Conflict; bucket already created -- probably means
                # the prior delete did not process just yet.
                continue

            raise

        return bucket


class FreshBucket(object):

    def __init__(self, bucket_name, keys=[], *args, **kwargs):
        self.bucket_name = bucket_name
        self.keys = keys
        self.conn_args = args
        self.conn_kwargs = kwargs
        self.created_bucket = False

    def __enter__(self):
        # Prefer using certs, when possible.
        if boto_supports_certs():
            self.conn_kwargs.setdefault('validate_certs', True)

        # Clean up a dangling bucket from a previous test run, if
        # necessary.
        self.conn = apathetic_bucket_delete(self.bucket_name,
                                            self.keys,
                                            *self.conn_args,
                                            **self.conn_kwargs)

        return self

    def create(self, *args, **kwargs):
        bucket = insistent_bucket_create(self.conn, self.bucket_name,
                                         *args, **kwargs)
        self.created_bucket = True

        return bucket

    def __exit__(self, typ, value, traceback):
        if not self.created_bucket:
            return False

        insistent_bucket_delete(self.conn, self.bucket_name, self.keys)

        return False

########NEW FILE########
__FILENAME__ = stage_pgxlog
import pytest


class PgXlog(object):
    """Test utility for staging a pg_xlog directory."""

    def __init__(self, cluster):
        self.cluster = cluster

        self.pg_xlog = cluster.join('pg_xlog')
        self.pg_xlog.ensure(dir=True)

        self.status = self.pg_xlog.join('archive_status')
        self.status.ensure(dir=True)

    def touch(self, name, status):
        assert status in ('.ready', '.done')

        self.pg_xlog.join(name).ensure(file=True)
        self.status.join(name + status).ensure(file=True)

    def seg(self, name):
        return self.pg_xlog.join(name)

    def assert_exists(self, name, status):
        assert status in ('.ready', '.done')

        assert self.pg_xlog.join(name).check(exists=1)
        assert self.status.join(name + status).check(exists=1)


@pytest.fixture()
def pg_xlog(tmpdir, monkeypatch):
    """Set up xlog utility functions and change directories."""
    monkeypatch.chdir(tmpdir)

    return PgXlog(tmpdir)

########NEW FILE########
__FILENAME__ = test_aws_instance_profiles
import pytest

import boto
import boto.provider
from boto import utils

from wal_e.blobstore.s3 import s3_credentials

META_DATA_CREDENTIALS = {
    "Code": "Success",
    "LastUpdated": "2014-01-11T02:13:53Z",
    "Type": "AWS-HMAC",
    "AccessKeyId": None,
    "SecretAccessKey": None,
    "Token": None,
    "Expiration": "2014-01-11T08:16:59Z"
}


def boto_flat_metadata():
    return tuple(int(x) for x in boto.__version__.split('.')) >= (2, 9, 0)


@pytest.fixture()
def metadata(monkeypatch):
    m = dict(**META_DATA_CREDENTIALS)
    m['AccessKeyId'] = 'foo'
    m['SecretAccessKey'] = 'bar'
    m['Token'] = 'baz'
    monkeypatch.setattr(boto.provider.Provider,
                        '_credentials_need_refresh',
                        lambda self: False)
    if boto_flat_metadata():
        m = {'irrelevant': m}
    else:
        m = {'iam': {'security-credentials': {'irrelevant': m}}}
    monkeypatch.setattr(utils, 'get_instance_metadata',
                        lambda *args, **kwargs: m)


def test_profile_provider(metadata):
    ipp = s3_credentials.InstanceProfileCredentials()
    assert ipp.get_access_key() == 'foo'
    assert ipp.get_secret_key() == 'bar'
    assert ipp.get_security_token() == 'baz'

########NEW FILE########
__FILENAME__ = test_aws_sts
import pytest

from boto import exception
from boto.s3 import connection
from cStringIO import StringIO
from wal_e.blobstore.s3 import Credentials
from wal_e.blobstore.s3 import calling_format
from wal_e.blobstore.s3 import uri_put_file
from wal_e.storage import StorageLayout
from wal_e.worker.s3 import BackupList

from s3_integration_help import (
    FreshBucket,
    make_policy,
    no_real_s3_credentials,
    sts_conn,
)

# quiet pyflakes
assert no_real_s3_credentials
assert sts_conn


@pytest.mark.skipif("no_real_s3_credentials()")
def test_simple_federation_token(sts_conn):
    sts_conn.get_federation_token(
        'hello',
        policy=make_policy('hello', 'goodbye'))


@pytest.mark.skipif("no_real_s3_credentials()")
def test_policy(sts_conn):
    """Sanity checks for the intended ACLs of the policy"""

    # Use periods to force OrdinaryCallingFormat when using
    # calling_format.from_store_name.
    bn = 'wal-e.sts.list.test'
    h = 's3-us-west-1.amazonaws.com'
    cf = connection.OrdinaryCallingFormat()

    fed = sts_conn.get_federation_token('wal-e-test-list-bucket',
                                        policy=make_policy(bn, 'test-prefix'))
    test_payload = 'wal-e test'

    keys = ['test-prefix/hello', 'test-prefix/world',
            'not-in-prefix/goodbye', 'not-in-prefix/world']
    creds = Credentials(fed.credentials.access_key,
                        fed.credentials.secret_key,
                        fed.credentials.session_token)

    with FreshBucket(bn, keys=keys, calling_format=cf, host=h) as fb:
        # Superuser creds, for testing keys not in the prefix.
        bucket_superset_creds = fb.create(location='us-west-1')

        cinfo = calling_format.from_store_name(bn)
        conn = cinfo.connect(creds)
        conn.host = h

        # Bucket using the token, subject to the policy.
        bucket = conn.get_bucket(bn, validate=False)

        for name in keys:
            if name.startswith('test-prefix/'):
                # Test the PUT privilege.
                k = connection.Key(bucket)
            else:
                # Not in the prefix, so PUT will not work.
                k = connection.Key(bucket_superset_creds)

            k.key = name
            k.set_contents_from_string(test_payload)

        # Test listing keys within the prefix.
        prefix_fetched_keys = list(bucket.list(prefix='test-prefix/'))
        assert len(prefix_fetched_keys) == 2

        # Test the GET privilege.
        for key in prefix_fetched_keys:
            assert key.get_contents_as_string() == 'wal-e test'

        # Try a bogus listing outside the valid prefix.
        with pytest.raises(exception.S3ResponseError) as e:
            list(bucket.list(prefix=''))

        assert e.value.status == 403

        # Test the rejection of PUT outside of prefix.
        k = connection.Key(bucket)
        k.key = 'not-in-prefix/world'

        with pytest.raises(exception.S3ResponseError) as e:
            k.set_contents_from_string(test_payload)

        assert e.value.status == 403


@pytest.mark.skipif("no_real_s3_credentials()")
def test_uri_put_file(sts_conn):
    bn = 'wal-e.sts.uri.put.file'
    cf = connection.OrdinaryCallingFormat()
    policy_text = make_policy(bn, 'test-prefix', allow_get_location=True)
    fed = sts_conn.get_federation_token('wal-e-test-uri-put-file',
                                        policy=policy_text)

    key_path = 'test-prefix/test-key'

    creds = Credentials(fed.credentials.access_key,
                        fed.credentials.secret_key,
                        fed.credentials.session_token)

    with FreshBucket(bn, keys=[key_path], calling_format=cf,
                     host='s3-us-west-1.amazonaws.com') as fb:
        fb.create(location='us-west-1')
        uri_put_file(creds, 's3://' + bn + '/' + key_path,
                     StringIO('test-content'))
        k = connection.Key(fb.conn.get_bucket(bn, validate=False))
        k.name = key_path
        assert k.get_contents_as_string() == 'test-content'


@pytest.mark.skipif("no_real_s3_credentials()")
def test_backup_list(sts_conn):
    """Test BackupList's compatibility with a test policy."""
    bn = 'wal-e.sts.backup.list'
    h = 's3-us-west-1.amazonaws.com'
    cf = connection.OrdinaryCallingFormat()
    fed = sts_conn.get_federation_token('wal-e-test-backup-list',
                                        policy=make_policy(bn, 'test-prefix'))
    layout = StorageLayout('s3://{0}/test-prefix'.format(bn))
    creds = Credentials(fed.credentials.access_key,
                        fed.credentials.secret_key,
                        fed.credentials.session_token)

    with FreshBucket(bn, calling_format=cf, host=h) as fb:
        fb.create(location='us-west-1')

        cinfo = calling_format.from_store_name(bn)
        conn = cinfo.connect(creds)
        conn.host = h

        backups = list(BackupList(conn, layout, True))
        assert not backups

########NEW FILE########
__FILENAME__ = test_blackbox
import pytest

from blackbox import config
from blackbox import noop_pg_backup_statements
from blackbox import small_push_dir
from s3_integration_help import default_test_bucket
from stage_pgxlog import pg_xlog

# Quiet pyflakes about pytest fixtures.
assert config
assert noop_pg_backup_statements
assert small_push_dir
assert default_test_bucket
assert pg_xlog


def test_wal_push_fetch(pg_xlog, tmpdir, config):
    contents = 'abcdefghijlmnopqrstuvwxyz\n' * 10000
    seg_name = '00000001' * 3
    pg_xlog.touch(seg_name, '.ready')
    pg_xlog.seg(seg_name).write(contents)
    config.main('wal-push', 'pg_xlog/' + seg_name)

    # Recall file and check for equality.
    download_file = tmpdir.join('TEST-DOWNLOADED')
    config.main('wal-fetch', seg_name, unicode(download_file))
    assert download_file.read() == contents


def test_wal_fetch_non_existent(tmpdir, config):
    # Recall file and check for equality.
    download_file = tmpdir.join('TEST-DOWNLOADED')

    with pytest.raises(SystemExit) as e:
        config.main('wal-fetch', 'irrelevant', unicode(download_file))

    assert e.value.code == 1


def test_backup_push_fetch(tmpdir, small_push_dir, monkeypatch, config,
                           noop_pg_backup_statements):
    import wal_e.tar_partition

    # check that _fsync_files() is called with the right
    # arguments. There's a separate unit test in test_tar_hacks.py
    # that it actually fsyncs the right files.
    fsynced_files = []
    monkeypatch.setattr(wal_e.tar_partition, '_fsync_files',
                        lambda filenames: fsynced_files.extend(filenames))

    config.main('backup-push', unicode(small_push_dir))

    fetch_dir = tmpdir.join('fetch-to').ensure(dir=True)
    config.main('backup-fetch', unicode(fetch_dir), 'LATEST')

    assert fetch_dir.join('arbitrary-file').read() == \
        small_push_dir.join('arbitrary-file').read()

    for filename in fetch_dir.listdir():
        if filename.check(link=0):
            assert unicode(filename) in fsynced_files
        elif filename.check(link=1):
            assert unicode(filename) not in fsynced_files


def test_delete_everything(config, small_push_dir, noop_pg_backup_statements):
    config.main('backup-push', unicode(small_push_dir))
    config.main('delete', '--confirm', 'everything')

########NEW FILE########
__FILENAME__ = test_bytedeque
import pytest

from wal_e import pipebuf


@pytest.fixture
def bd():
    return pipebuf.ByteDeque()


def test_empty(bd):
    assert bd.byteSz == 0

    bd.get(0)

    with pytest.raises(AssertionError):
        bd.get(1)

    with pytest.raises(ValueError):
        bd.get(-1)


def test_defragment(bd):
    bd.add('1')
    bd.add('2')

    assert bd.get(2) == bytearray('12')


def test_refragment(bd):
    byts = bytes('1234')
    bd.add(byts)
    assert bd.byteSz == len(byts)

    for ordinal, byt in enumerate(byts):
        assert bd.get(1) == byt
        assert bd.byteSz == len(byts) - ordinal - 1

    assert bd.byteSz == 0


def test_exact_fragment(bd):
    byts = bytes('1234')
    bd.add(byts)
    assert bd.get(len(byts)) == byts
    assert bd.byteSz == 0

########NEW FILE########
__FILENAME__ = test_channel_shim
import gevent

from gevent import queue
from wal_e import channel


def test_channel_shim():
    v = tuple(int(x) for x in gevent.__version__.split('.'))

    if v >= (0, 13, 0) and v < (1, 0, 0):
        assert isinstance(channel.Channel(), queue.Queue)
    elif v >= (1, 0, 0):
        assert isinstance(channel.Channel(), queue.Channel)
    else:
        assert False, 'Unexpected version ' + gevent.__version__

########NEW FILE########
__FILENAME__ = test_cmdline_version
import errno
import pytest

from os import path

from wal_e import subprocess


def test_version_print():
    # Load up the contents of the VERSION file out-of-band
    from wal_e import cmd
    place = path.join(path.dirname(cmd.__file__), 'VERSION')
    with open(place) as f:
        expected = f.read()

    # Try loading it via command line invocation
    try:
        proc = subprocess.Popen(['wal-e', 'version'], stdout=subprocess.PIPE)
    except EnvironmentError, e:
        if e.errno == errno.ENOENT:
            pytest.skip('wal-e must be in $PATH to test version output')
    result = proc.communicate()[0]

    # Make sure the two versions match and the command exits
    # successfully.
    assert proc.returncode == 0
    assert result == expected

########NEW FILE########
__FILENAME__ = test_exceptions
# Test exception construction
#
# Flush out simple typo crashes and problems with occasional changes
# in the exception base classes.
from wal_e.tar_partition import TarMemberTooBigError


def test_tar_member_too_big_error():
    # Must not raise an exception.
    a = TarMemberTooBigError("file.dat", 100, 150)
    assert a.msg == 'Attempted to archive a file that is too large.'
    hint = ('There is a file in the postgres database directory that '
            'is larger than 100 bytes. If no such file exists, please '
            'report this as a bug. In particular, check file.dat, '
            'which appears to be 150 bytes.')
    assert a.hint == hint

########NEW FILE########
__FILENAME__ = test_log_help
import re

from wal_e import log_help


def sanitize_log(log):
    return re.sub(r'time=[0-9T:\-\.]+ pid=\d+',
                  'time=2012-01-01T00.1234-00 pid=1234',
                  log)


def test_nonexisting_socket(tmpdir, monkeypatch):
    # Must not raise an exception, silently failing is preferred for
    # now.
    monkeypatch.setattr(log_help, 'HANDLERS', [])
    log_help.configure(syslog_address=tmpdir.join('bogus'))


def test_format_structured_info():
    zero = {}, 'time=2012-01-01T00.1234-00 pid=1234'

    one = ({'hello': 'world'},
           u'time=2012-01-01T00.1234-00 pid=1234 hello=world')

    many = ({'hello': 'world', 'goodbye': 'world'},
            u'time=2012-01-01T00.1234-00 pid=1234 goodbye=world hello=world')

    for d, expect in [zero, one, many]:
        result = log_help.WalELogger._fmt_structured(d)
        assert sanitize_log(result) == expect


def test_fmt_logline_simple():
    out = log_help.WalELogger.fmt_logline(
        'The message', 'The detail', 'The hint', {'structured-data': 'yes'})
    out = sanitize_log(out)

    assert out == """MSG: The message
DETAIL: The detail
HINT: The hint
STRUCTURED: time=2012-01-01T00.1234-00 pid=1234 structured-data=yes"""

    # Try without structured data
    out = log_help.WalELogger.fmt_logline(
        'The message', 'The detail', 'The hint')
    out = sanitize_log(out)

    assert out == """MSG: The message
DETAIL: The detail
HINT: The hint
STRUCTURED: time=2012-01-01T00.1234-00 pid=1234"""

########NEW FILE########
__FILENAME__ = test_pipeline_sanity
import pytest

from wal_e import pipeline


def create_bogus_payload(dirname):
    payload = 'abcd' * 1048576
    payload_file = dirname.join('payload')
    payload_file.write(payload)
    return payload, payload_file


def test_rate_limit(tmpdir):
    payload, payload_file = create_bogus_payload(tmpdir)

    pl = pipeline.PipeViewerRateLimitFilter(1048576 * 100,
                                           stdin=payload_file.open())
    pl.start()
    round_trip = pl.stdout.read()
    pl.finish()
    assert round_trip == payload


def test_upload_download_pipeline(tmpdir, rate_limit):
    payload, payload_file = create_bogus_payload(tmpdir)

    # Upload section
    test_upload = tmpdir.join('upload')
    with open(unicode(test_upload), 'w') as upload:
        with open(unicode(payload_file)) as inp:
            with pipeline.get_upload_pipeline(
                    inp, upload, rate_limit=rate_limit):
                pass

    with open(unicode(test_upload)) as completed:
        round_trip = completed.read()

    # Download section
    test_download = tmpdir.join('download')
    with open(unicode(test_upload)) as upload:
        with open(unicode(test_download), 'w') as download:
            with pipeline.get_download_pipeline(upload, download):
                pass

    with open(unicode(test_download)) as completed:
        round_trip = completed.read()

    assert round_trip == payload


def test_close_process_when_normal():
    """Process leaks must not occur in successful cases"""
    with pipeline.get_cat_pipeline(pipeline.PIPE, pipeline.PIPE) as pl:
        assert len(pl.commands) == 1
        assert pl.commands[0]._process.poll() is None

    # Failure means a failure to terminate the process.
    pipeline_wait(pl)


def test_close_process_when_exception():
    """Process leaks must not occur when an exception is raised"""
    exc = Exception('boom')

    with pytest.raises(Exception) as e:
        with pipeline.get_cat_pipeline(pipeline.PIPE, pipeline.PIPE) as pl:
            assert len(pl.commands) == 1
            assert pl.commands[0]._process.poll() is None
            raise exc

    assert e.value is exc

    # Failure means a failure to terminate the process.
    pipeline_wait(pl)


def test_close_process_when_aborted():
    """Process leaks must not occur when the pipeline is aborted"""
    with pipeline.get_cat_pipeline(pipeline.PIPE, pipeline.PIPE) as pl:
        assert len(pl.commands) == 1
        assert pl.commands[0]._process.poll() is None
        pl.abort()

    # Failure means a failure to terminate the process.
    pipeline_wait(pl)


def pipeline_wait(pl):
    for command in pl.commands:
        # Failure means a failure to terminate the process.
        command.wait()


def pytest_generate_tests(metafunc):
    # Test both with and without rate limiting if there is rate_limit
    # parameter.
    if "rate_limit" in metafunc.funcargnames:
        metafunc.parametrize("rate_limit", [None, int(2 ** 25)])

########NEW FILE########
__FILENAME__ = test_piper_low_mem
import errno
import os

import gevent
import pytest

from wal_e import piper
from wal_e import subprocess


def invoke_program():
    with open(os.devnull, 'w') as devnull:
        piper.popen_sp(['python', '--version'],
                       stdout=devnull, stderr=devnull)


def test_normal():
    invoke_program()


class OomTimes(object):
    def __init__(self, real, n):
        self.real = real
        self.n = n

    def __call__(self, *args, **kwargs):
        if self.n == 0:
            self.real(*args, **kwargs)
        else:
            self.n -= 1
            e = OSError('faked oom')
            e.errno = errno.ENOMEM
            raise e


def pytest_generate_tests(metafunc):
    if "oomtimes" in metafunc.funcargnames:
        # Test OOM being delivered a varying number of times.
        scenarios = [OomTimes(subprocess.Popen, n) for n in [0, 1, 2, 10]]
        metafunc.parametrize("oomtimes", scenarios)


def test_low_mem(oomtimes, gevent_fastsleep, monkeypatch):
    monkeypatch.setattr(subprocess, 'Popen', oomtimes)
    invoke_program()


def test_advanced_shim(oomtimes, monkeypatch):
    monkeypatch.setattr(subprocess, 'Popen', oomtimes)

    old_n = oomtimes.n

    def reset():
        oomtimes.n = old_n

    def invoke(max_tries):
        with open(os.devnull, 'w') as devnull:
            popen = piper.PopenShim(sleep_time=0, max_tries=max_tries)
            popen(['python', '--version'],
                  stdout=devnull, stderr=devnull)

    if oomtimes.n >= 1:
        with pytest.raises(OSError) as e:
            invoke(oomtimes.n - 1)

        assert e.value.errno == errno.ENOMEM
    else:
        invoke(oomtimes.n - 1)

    reset()

    invoke(oomtimes.n)
    reset()

    invoke(oomtimes.n + 1)
    reset()


@pytest.fixture()
def gevent_fastsleep(monkeypatch):
    """Stub out gevent.sleep to only yield briefly.

    In production one may want to wait a bit having no work to do to
    avoid spinning, but during testing this adds quite a bit of time.
    """
    old_sleep = gevent.sleep

    def fast_sleep(tm):
        # Ignore time passed and just yield.
        old_sleep(0.1)

    monkeypatch.setattr(gevent, 'sleep', fast_sleep)


def test_fast_sleep(gevent_fastsleep):
    """Annoy someone who causes fast-sleep test patching to regress.

    Someone could break the test-only monkey-patching of gevent.sleep
    without noticing and costing quite a bit of aggravation aggregated
    over time waiting in tests, added bit by bit.

    To avoid that, add this incredibly huge/annoying delay that can
    only be avoided by monkey-patch to catch the regression.
    """
    gevent.sleep(300)

########NEW FILE########
__FILENAME__ = test_s3_calling_format
import boto
import inspect
import os
import pytest

from boto.s3 import connection
from s3_integration_help import (
    FreshBucket,
    no_real_s3_credentials,
)
from wal_e.blobstore.s3 import Credentials
from wal_e.blobstore.s3 import calling_format
from wal_e.blobstore.s3.calling_format import (
    _is_mostly_subdomain_compatible,
    _is_ipv4_like,
)

SUBDOMAIN_BOGUS = [
    '1.2.3.4',
    'myawsbucket.',
    'myawsbucket-.',
    'my.-awsbucket',
    '.myawsbucket',
    'myawsbucket-',
    '-myawsbucket',
    'my_awsbucket',
    'my..examplebucket',

    # Too short.
    'sh',

    # Too long.
    'long' * 30,
]

SUBDOMAIN_OK = [
    'myawsbucket',
    'my-aws-bucket',
    'myawsbucket.1',
    'my.aws.bucket'
]

# Contrivance to quiet down pyflakes, since pytest does some
# string-evaluation magic in test collection.
no_real_s3_credentials = no_real_s3_credentials


def test_subdomain_detect():
    """Exercise subdomain compatible/incompatible bucket names."""
    for bn in SUBDOMAIN_OK:
        assert _is_mostly_subdomain_compatible(bn) is True

    for bn in SUBDOMAIN_BOGUS:
        assert _is_mostly_subdomain_compatible(bn) is False


def test_us_standard_default_for_bogus():
    """Test degradation to us-standard for all weird bucket names.

    Such bucket names are not supported outside of us-standard by
    WAL-E.
    """
    for bn in SUBDOMAIN_BOGUS:
        cinfo = calling_format.from_store_name(bn)
        assert cinfo.region == 'us-standard'


def test_cert_validation_sensitivity():
    """Test degradation of dotted bucket names to OrdinaryCallingFormat

    Although legal bucket names with SubdomainCallingFormat, these
    kinds of bucket names run afoul certification validation, and so
    they are forced to fall back to OrdinaryCallingFormat.
    """
    for bn in SUBDOMAIN_OK:
        if '.' not in bn:
            cinfo = calling_format.from_store_name(bn)
            assert (cinfo.calling_format ==
                    boto.s3.connection.SubdomainCallingFormat)
        else:
            assert '.' in bn

            cinfo = calling_format.from_store_name(bn)
            assert (cinfo.calling_format == connection.OrdinaryCallingFormat)
            assert cinfo.region is None
            assert cinfo.ordinary_endpoint is None


@pytest.mark.skipif("no_real_s3_credentials()")
def test_real_get_location():
    """Exercise a case where a get location call is needed.

    In cases where a bucket has offensive characters -- like dots --
    that would otherwise break TLS, test sniffing the right endpoint
    so it can be used to address the bucket.
    """
    creds = Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                        os.getenv('AWS_SECRET_ACCESS_KEY'))

    bucket_name = 'wal-e-test-us-west-1.get.location'

    cinfo = calling_format.from_store_name(bucket_name)

    with FreshBucket(bucket_name,
                     host='s3-us-west-1.amazonaws.com',
                     calling_format=connection.OrdinaryCallingFormat()) as fb:
        fb.create(location='us-west-1')
        conn = cinfo.connect(creds)

        assert cinfo.region == 'us-west-1'
        assert cinfo.calling_format is connection.OrdinaryCallingFormat
        assert conn.host == 's3-us-west-1.amazonaws.com'


@pytest.mark.skipif("no_real_s3_credentials()")
def test_classic_get_location():
    """Exercise get location on a s3-classic bucket."""
    creds = Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                        os.getenv('AWS_SECRET_ACCESS_KEY'))

    bucket_name = 'wal-e-test.classic.get.location'

    cinfo = calling_format.from_store_name(bucket_name)

    with FreshBucket(bucket_name,
                     host='s3.amazonaws.com',
                     calling_format=connection.OrdinaryCallingFormat()) as fb:
        fb.create()
        conn = cinfo.connect(creds)

        assert cinfo.region == 'us-standard'
        assert cinfo.calling_format is connection.OrdinaryCallingFormat
        assert conn.host == 's3.amazonaws.com'


@pytest.mark.skipif("no_real_s3_credentials()")
def test_subdomain_compatible():
    """Exercise a case where connecting is region-oblivious."""
    creds = Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                        os.getenv('AWS_SECRET_ACCESS_KEY'))

    bucket_name = 'wal-e-test-us-west-1-no-dots'

    cinfo = calling_format.from_store_name(bucket_name)

    with FreshBucket(bucket_name,
                     host='s3-us-west-1.amazonaws.com',
                     calling_format=connection.OrdinaryCallingFormat()) as fb:
        fb.create(location='us-west-1')
        conn = cinfo.connect(creds)

        assert cinfo.region is None
        assert cinfo.calling_format is connection.SubdomainCallingFormat
        assert isinstance(conn.calling_format,
                          connection.SubdomainCallingFormat)


def test_ipv4_detect():
    """IPv4 lookalikes are not valid SubdomainCallingFormat names

    Even though they otherwise follow the bucket naming rules,
    IPv4-alike names are called out as specifically banned.
    """
    assert _is_ipv4_like('1.1.1.1') is True

    # Out-of IPv4 numerical range is irrelevant to the rules.
    assert _is_ipv4_like('1.1.1.256') is True
    assert _is_ipv4_like('-1.1.1.1') is True

    assert _is_ipv4_like('1.1.1.hello') is False
    assert _is_ipv4_like('hello') is False
    assert _is_ipv4_like('-1.1.1') is False
    assert _is_ipv4_like('-1.1.1.') is False


@pytest.mark.skipif("no_real_s3_credentials()")
def test_get_location_errors(monkeypatch):
    """Simulate situations where get_location fails

    Exercise both the case where IAM refuses the privilege to get the
    bucket location and where some other S3ResponseError is raised
    instead.
    """
    bucket_name = 'wal-e.test.403.get.location'

    def just_403(self):
        raise boto.exception.S3ResponseError(status=403,
                                             reason=None, body=None)

    def unhandled_404(self):
        raise boto.exception.S3ResponseError(status=404,
                                             reason=None, body=None)

    creds = Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                        os.getenv('AWS_SECRET_ACCESS_KEY'))

    with FreshBucket(bucket_name,
                     calling_format=connection.OrdinaryCallingFormat()):
        cinfo = calling_format.from_store_name(bucket_name)

        # Provoke a 403 when trying to get the bucket location.
        monkeypatch.setattr(boto.s3.bucket.Bucket, 'get_location', just_403)
        cinfo.connect(creds)

        assert cinfo.region == 'us-standard'
        assert cinfo.calling_format is connection.OrdinaryCallingFormat

        cinfo = calling_format.from_store_name(bucket_name)

        # Provoke an unhandled S3ResponseError, in this case 404 not
        # found.
        monkeypatch.setattr(boto.s3.bucket.Bucket, 'get_location',
                            unhandled_404)

        with pytest.raises(boto.exception.S3ResponseError) as e:
            cinfo.connect(creds)

        assert e.value.status == 404


def test_str_repr_call_info():
    """Ensure CallingInfo renders sensibly.

    Try a few cases sensitive to the bucket name.
    """
    if boto.__version__ <= '2.2.0':
        pytest.skip('Class name output is unstable on older boto versions')

    cinfo = calling_format.from_store_name('hello-world')
    assert repr(cinfo) == str(cinfo)
    assert repr(cinfo) == (
        "CallingInfo(hello-world, "
        "<class 'boto.s3.connection.SubdomainCallingFormat'>, "
        "None, None)"
    )

    cinfo = calling_format.from_store_name('hello.world')
    assert repr(cinfo) == str(cinfo)
    assert repr(cinfo) == (
        "CallingInfo(hello.world, "
        "<class 'boto.s3.connection.OrdinaryCallingFormat'>, "
        "None, None)"
    )

    cinfo = calling_format.from_store_name('Hello-World')
    assert repr(cinfo) == str(cinfo)
    assert repr(cinfo) == (
        "CallingInfo(Hello-World, "
        "<class 'boto.s3.connection.OrdinaryCallingFormat'>, "
        "'us-standard', 's3.amazonaws.com')"
    )


@pytest.mark.skipif("no_real_s3_credentials()")
@pytest.mark.skipif("sys.version_info < (2, 7)")
def test_cipher_suites():
    # Imported for its side effects of setting up ssl cipher suites
    # and gevent.
    from wal_e import cmd

    # Quiet pyflakes.
    assert cmd

    creds = Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                        os.getenv('AWS_SECRET_ACCESS_KEY'))
    cinfo = calling_format.from_store_name('irrelevant')
    conn = cinfo.connect(creds)

    # Warm up the pool and the connection in it; new_http_connection
    # seems to be a more natural choice, but leaves the '.sock'
    # attribute null.
    conn.get_all_buckets()

    # Set up 'port' keyword argument for newer Botos that require it.
    spec = inspect.getargspec(conn._pool.get_http_connection)
    kw = {'host': 's3.amazonaws.com',
          'is_secure': True}
    if 'port' in spec.args:
        kw['port'] = 443

    htcon = conn._pool.get_http_connection(**kw)

    chosen_cipher_suite = htcon.sock.cipher()[0].split('-')

    # Test for the expected cipher suite.
    #
    # This can change or vary on different platforms somewhat
    # harmlessly, but do the simple thing and insist on an exact match
    # for now.
    assert chosen_cipher_suite == ['AES256', 'SHA']

########NEW FILE########
__FILENAME__ = test_s3_deleter
import gevent
import pytest

from gevent import coros

from boto.s3 import bucket
from boto.s3 import key

from wal_e import exception
from wal_e.worker.s3 import s3_deleter


class BucketDeleteKeysCollector(object):
    """A callable to stand-in for bucket.delete_keys

    Used to test that given keys are bulk-deleted.

    Also can inject an exception.
    """
    def __init__(self):
        self.deleted_keys = []
        self.aborted_keys = []
        self.exc = None

        # Protect exc, since some paths test it and then use it, which
        # can run afoul race conditions.
        self._exc_protect = coros.RLock()

    def inject(self, exc):
        self._exc_protect.acquire()
        self.exc = exc
        self._exc_protect.release()

    def __call__(self, keys):
        self._exc_protect.acquire()

        try:
            if self.exc:
                self.aborted_keys.extend(keys)

                # Prevent starvation/livelock with a polling process
                # by yielding.
                gevent.sleep(0.1)

                raise self.exc
        finally:
            self._exc_protect.release()

        self.deleted_keys.extend(keys)


@pytest.fixture
def collect(monkeypatch):
    """Instead of performing bulk delete, collect key names deleted.

    This is to test invariants, as to ensure deleted keys are passed
    to boto properly.
    """

    collect = BucketDeleteKeysCollector()
    monkeypatch.setattr(bucket.Bucket, 'delete_keys', collect)

    return collect


@pytest.fixture
def b():
    return bucket.Bucket(name='test-bucket-name')


@pytest.fixture(autouse=True)
def never_use_single_delete(monkeypatch):
    """Detect any mistaken uses of single-key deletion.

    Older wal-e versions used one-at-a-time deletions.  This is just
    to help ensure that use of this API (through the nominal boto
    symbol) is detected.
    """
    def die():
        assert False

    monkeypatch.setattr(key.Key, 'delete', die)
    monkeypatch.setattr(bucket.Bucket, 'delete_key', die)


@pytest.fixture(autouse=True)
def gevent_fastsleep(monkeypatch):
    """Stub out gevent.sleep to only yield briefly.

    In production one may want to wait a bit having no work to do to
    avoid spinning, but during testing this adds quite a bit of time.
    """
    old_sleep = gevent.sleep

    def fast_sleep(tm):
        # Ignore time passed and just yield.
        old_sleep(0.1)

    monkeypatch.setattr(gevent, 'sleep', fast_sleep)


def test_fast_sleep():
    """Annoy someone who causes fast-sleep test patching to regress.

    Someone could break the test-only monkey-patching of gevent.sleep
    without noticing and costing quite a bit of aggravation aggregated
    over time waiting in tests, added bit by bit.

    To avoid that, add this incredibly huge/annoying delay that can
    only be avoided by monkey-patch to catch the regression.
    """
    gevent.sleep(300)


def test_construction():
    """The constructor basically works."""
    s3_deleter.Deleter()


def test_close_error():
    """Ensure that attempts to use a closed Deleter results in an error."""

    d = s3_deleter.Deleter()
    d.close()

    with pytest.raises(exception.UserCritical):
        d.delete('no value should work')


def test_processes_one_deletion(b, collect):
    # Mock up a key and bucket
    key_name = 'test-key-name'
    k = key.Key(bucket=b, name=key_name)

    d = s3_deleter.Deleter()
    d.delete(k)
    d.close()

    assert collect.deleted_keys == [key_name]


def test_processes_many_deletions(b, collect):
    # Generate a target list of keys in a stable order
    target = sorted(['test-key-' + str(x) for x in range(20001)])

    # Construct boto S3 Keys from the generated names and delete them
    # all.
    keys = [key.Key(bucket=b, name=key_name) for key_name in target]
    d = s3_deleter.Deleter()

    for k in keys:
        d.delete(k)

    d.close()

    # Sort the deleted key names to obtain another stable order and
    # then ensure that everything was passed for deletion
    # successfully.
    assert sorted(collect.deleted_keys) == target


def test_retry_on_normal_error(b, collect):
    """Ensure retries are processed for most errors."""
    key_name = 'test-key-name'
    k = key.Key(bucket=b, name=key_name)

    collect.inject(Exception('Normal error'))
    d = s3_deleter.Deleter()
    d.delete(k)

    # Since delete_keys will fail over and over again, aborted_keys
    # should grow quickly.
    while len(collect.aborted_keys) < 2:
        gevent.sleep(0.1)

    # Since delete_keys has been failing repeatedly, no keys should be
    # successfully deleted.
    assert not collect.deleted_keys

    # Turn off fault injection and flush/synchronize with close().
    collect.inject(None)
    d.close()

    # The one enqueued job should have been processed.n
    assert collect.deleted_keys == [key_name]


def test_no_retry_on_keyboadinterrupt(b, collect):
    """Ensure that KeyboardInterrupts are forwarded."""
    key_name = 'test-key-name'
    k = key.Key(bucket=b, name=key_name)

    # If vanilla KeyboardInterrupt is used, then sending SIGINT to the
    # test can cause it to pass improperly, so use a subtype instead.
    class MarkedKeyboardInterrupt(KeyboardInterrupt):
        pass

    collect.inject(MarkedKeyboardInterrupt('SIGINT, probably'))
    d = s3_deleter.Deleter()

    with pytest.raises(MarkedKeyboardInterrupt):
        d.delete(k)

        # Exactly when coroutines are scheduled is non-deterministic,
        # so spin while yielding to provoke the
        # MarkedKeyboardInterrupt being processed within the
        # pytest.raises context manager.
        while True:
            gevent.sleep(0.1)

    # Only one key should have been aborted, since the purpose is to
    # *not* retry when processing KeyboardInterrupt.
    assert collect.aborted_keys == [key_name]

    # Turn off fault injection and flush/synchronize with close().
    collect.inject(None)
    d.close()

    # Since there is no retrying, no keys should be deleted.
    assert not collect.deleted_keys

########NEW FILE########
__FILENAME__ = test_s3_worker
import os
import pytest

from wal_e import storage
from wal_e.blobstore.s3 import Credentials
from wal_e.blobstore.s3 import do_lzop_get
from wal_e.worker.s3 import BackupList

from boto.s3.connection import (
    OrdinaryCallingFormat,
    SubdomainCallingFormat,
)
from s3_integration_help import (
    boto_supports_certs,
    FreshBucket,
    no_real_s3_credentials,
)

# Contrivance to quiet down pyflakes, since pytest does some
# string-evaluation magic in test collection.
no_real_s3_credentials = no_real_s3_credentials
boto_supports_certs = boto_supports_certs


@pytest.mark.skipif("no_real_s3_credentials()")
def test_301_redirect():
    """Integration test for bucket naming issues this test."""
    import boto.s3.connection

    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    bucket_name = 'wal-e-test-301-redirect' + aws_access_key.lower()

    with pytest.raises(boto.exception.S3ResponseError) as e:
        # Just initiating the bucket manipulation API calls is enough
        # to provoke a 301 redirect.
        with FreshBucket(bucket_name,
                         calling_format=OrdinaryCallingFormat()) as fb:
            fb.create(location='us-west-1')

    assert e.value.status == 301


@pytest.mark.skipif("no_real_s3_credentials()")
@pytest.mark.skipif("not boto_supports_certs()")
def test_get_bucket_vs_certs():
    """Integration test for bucket naming issues."""
    import boto.s3.connection

    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')

    # Add dots to try to trip up TLS certificate validation.
    bucket_name = 'wal-e.test.dots.' + aws_access_key.lower()

    with pytest.raises(boto.https_connection.InvalidCertificateException):
        with FreshBucket(bucket_name, calling_format=SubdomainCallingFormat()):
            pass


@pytest.mark.skipif("no_real_s3_credentials()")
def test_empty_latest_listing():
    """Test listing a 'backup-list LATEST' on an empty prefix."""

    bucket_name = 'wal-e-test-empty-listing'
    layout = storage.StorageLayout('s3://{0}/test-prefix'
                                   .format(bucket_name))

    with FreshBucket(bucket_name, host='s3.amazonaws.com',
                     calling_format=OrdinaryCallingFormat()) as fb:
        fb.create()
        bl = BackupList(fb.conn, layout, False)
        found = list(bl.find_all('LATEST'))
        assert len(found) == 0


@pytest.mark.skipif("no_real_s3_credentials()")
def test_404_termination(tmpdir):
    bucket_name = 'wal-e-test-404-termination'
    creds = Credentials(os.getenv('AWS_ACCESS_KEY_ID'),
                        os.getenv('AWS_SECRET_ACCESS_KEY'))

    with FreshBucket(bucket_name, host='s3.amazonaws.com',
                     calling_format=OrdinaryCallingFormat()) as fb:
        fb.create()

        target = unicode(tmpdir.join('target'))
        ret = do_lzop_get(creds, 's3://' + bucket_name + '/not-exist.lzo',
                          target, False)
        assert ret is False

########NEW FILE########
__FILENAME__ = test_tar_hacks
import os
import tarfile

from wal_e import tar_partition


def test_fsync_tar_members(monkeypatch, tmpdir):
    """Test that _fsync_files() syncs all files and directories

    Syncing directories is a platform specific feature, so it is
    optional.

    There is a separate test in test_blackbox that tar_file_extract()
    actually calls _fsync_files and passes it the expected list of
    files.

    """
    dira = tmpdir.join('dira').ensure(dir=True)
    dirb = tmpdir.join('dirb').ensure(dir=True)
    foo = dira.join('foo').ensure()
    bar = dirb.join('bar').ensure()
    baz = dirb.join('baz').ensure()

    # Monkeypatch around open, close, and fsync to capture which
    # filenames the file descriptors being fsynced actually correspond
    # to. Only bother to remember filenames in the tmpdir.

    # fd => filename for the tmpdir files currently open.
    open_descriptors = {}
    # Set of filenames that fsyncs have been called on.
    synced_filenames = set()
    # Filter on prefix of this path.
    tmproot = unicode(tmpdir)

    real_open = os.open
    real_close = os.close
    real_fsync = os.fsync

    def fake_open(filename, flags, mode=0777):
        fd = real_open(filename, flags, mode)
        if filename.startswith(tmproot):
            open_descriptors[fd] = filename
        return fd

    def fake_close(fd):
        if fd in open_descriptors:
            del open_descriptors[fd]
        real_close(fd)
        return

    def fake_fsync(fd):
        if fd in open_descriptors:
            synced_filenames.add(open_descriptors[fd])
        real_fsync(fd)
        return

    monkeypatch.setattr(os, 'open', fake_open)
    monkeypatch.setattr(os, 'close', fake_close)
    monkeypatch.setattr(os, 'fsync', fake_fsync)

    filenames = [unicode(filename) for filename in [foo, bar, baz]]
    tar_partition._fsync_files(filenames)

    for filename in filenames:
        assert filename in synced_filenames

    # Not every OS allows you to open directories, if not, don't try
    # to open it to fsync.
    if hasattr(os, 'O_DIRECTORY'):
        assert unicode(dira) in synced_filenames
        assert unicode(dirb) in synced_filenames


def test_creation_upper_dir(tmpdir, monkeypatch):
    """Check for upper-directory creation in untarring

    This affected the special "cat" based extraction works when no
    upper level directory is present.  Using that path depends on
    PIPE_BUF_BYTES, so test that integration via monkey-patching it to
    a small value.

    """
    from wal_e import pipebuf

    # Set up a directory with a file inside.
    adir = tmpdir.join('adir').ensure(dir=True)
    some_file = adir.join('afile')
    some_file.write('1234567890')

    tar_path = unicode(tmpdir.join('foo.tar'))

    # Add the file to a test tar, *but not the directory*.
    tar = tarfile.open(name=tar_path, mode='w')
    tar.add(unicode(some_file))
    tar.close()

    # Replace cat_extract with a version that does the same, but
    # ensures that it is called by the test.
    original_cat_extract = tar_partition.cat_extract

    class CheckCatExtract(object):
        def __init__(self):
            self.called = False

        def __call__(self, *args, **kwargs):
            self.called = True
            return original_cat_extract(*args, **kwargs)

    check = CheckCatExtract()
    monkeypatch.setattr(tar_partition, 'cat_extract', check)
    monkeypatch.setattr(pipebuf, 'PIPE_BUF_BYTES', 1)

    dest_dir = tmpdir.join('dest')
    dest_dir.ensure(dir=True)
    with open(tar_path) as f:
        tar_partition.TarPartition.tarfile_extract(f, unicode(dest_dir))

    # Make sure the test exercised cat_extraction.
    assert check.called

########NEW FILE########
__FILENAME__ = test_tar_upload_pool
import pytest

from wal_e import exception
from wal_e import worker


class FakeTarPartition(object):
    """Implements enough protocol to test concurrency semantics."""
    def __init__(self, num_members, explosive=False):
        self._explosive = explosive
        self.num_members = num_members

    def __len__(self):
        return self.num_members


class FakeUploader(object):
    """A no-op uploader that makes affordance for fault injection."""

    def __call__(self, tpart):
        if tpart._explosive:
            raise tpart._explosive

        return tpart


class Explosion(Exception):
    """Marker type of injected faults."""
    pass


def make_pool(max_concurrency, max_members):
    """Set up a pool with a FakeUploader"""
    return worker.TarUploadPool(FakeUploader(),
                                max_concurrency, max_members)


def test_simple():
    """Simple case of uploading one partition."""
    pool = make_pool(1, 1)
    pool.put(FakeTarPartition(1))
    pool.join()


def test_not_enough_resources():
    """Detect if a too-large segment can never complete."""
    pool = make_pool(1, 1)

    with pytest.raises(exception.UserCritical):
        pool.put(FakeTarPartition(2))

    pool.join()


def test_simple_concurrency():
    """Try a pool that cannot execute all submitted jobs at once."""
    pool = make_pool(1, 1)

    for i in xrange(3):
        pool.put(FakeTarPartition(1))

    pool.join()


def test_fault_midstream():
    """Test if a previous upload fault is detected in calling .put.

    This case is seen while pipelining many uploads in excess of the
    maximum concurrency.

    NB: This test is critical as to prevent failed uploads from
    failing to notify a caller that the entire backup is incomplete.
    """
    pool = make_pool(1, 1)

    # Set up upload doomed to fail.
    tpart = FakeTarPartition(1, explosive=Explosion('Boom'))
    pool.put(tpart)

    # Try to receive the error through adding another upload.
    tpart = FakeTarPartition(1)
    with pytest.raises(Explosion):
        pool.put(tpart)


def test_fault_join():
    """Test if a fault is detected when .join is used.

    This case is seen at the end of a series of uploads.

    NB: This test is critical as to prevent failed uploads from
    failing to notify a caller that the entire backup is incomplete.
    """
    pool = make_pool(1, 1)

    # Set up upload doomed to fail.
    tpart = FakeTarPartition(1, explosive=Explosion('Boom'))
    pool.put(tpart)

    # Try to receive the error while finishing up.
    with pytest.raises(Explosion):
        pool.join()


def test_put_after_join():
    """New jobs cannot be submitted after a .join

    This is mostly a re-check to detect programming errors.
    """
    pool = make_pool(1, 1)

    pool.join()

    with pytest.raises(exception.UserCritical):
        pool.put(FakeTarPartition(1))


def test_pool_concurrent_success():
    pool = make_pool(4, 4)

    for i in xrange(30):
        pool.put(FakeTarPartition(1))

    pool.join()


def test_pool_concurrent_failure():
    pool = make_pool(4, 4)

    parts = [FakeTarPartition(1) for i in xrange(30)]

    exc = Explosion('boom')
    parts[27]._explosive = exc

    with pytest.raises(Explosion) as e:
        for part in parts:
            pool.put(part)

        pool.join()

    assert e.value is exc

########NEW FILE########
__FILENAME__ = test_wabs_deleter
import gevent
import pytest
from collections import namedtuple

from azure.storage import BlobService
from gevent import coros

from wal_e import exception
from wal_e.worker.wabs import wabs_deleter

B = namedtuple('Blob', ['name'])


class ContainerDeleteKeysCollector(object):
    """A callable to stand-in for bucket.delete_keys

    Used to test that given keys are bulk-deleted.

    Also can inject an exception.
    """
    def __init__(self):
        self.deleted_keys = []
        self.aborted_keys = []
        self.exc = None

        # Protect exc, since some paths test it and then use it, which
        # can run afoul race conditions.
        self._exc_protect = coros.RLock()

    def inject(self, exc):
        self._exc_protect.acquire()
        self.exc = exc
        self._exc_protect.release()

    def __call__(self, container, key):
        self._exc_protect.acquire()

        try:
            if self.exc:
                self.aborted_keys.append(key)

                # Prevent starvation/livelock with a polling process
                # by yielding.
                gevent.sleep(0.1)

                raise self.exc
        finally:
            self._exc_protect.release()

        self.deleted_keys.append(key)


@pytest.fixture
def collect(monkeypatch):
    """Instead of performing bulk delete, collect key names deleted.

    This is to test invariants, as to ensure deleted keys are passed
    to boto properly.
    """

    collect = ContainerDeleteKeysCollector()
    monkeypatch.setattr(BlobService, 'delete_blob', collect)

    return collect


@pytest.fixture(autouse=True)
def gevent_fastsleep(monkeypatch):
    """Stub out gevent.sleep to only yield briefly.

    In production one may want to wait a bit having no work to do to
    avoid spinning, but during testing this adds quite a bit of time.
    """
    old_sleep = gevent.sleep

    def fast_sleep(tm):
        # Ignore time passed and just yield.
        old_sleep(0.1)

    monkeypatch.setattr(gevent, 'sleep', fast_sleep)


def test_fast_sleep():
    """Annoy someone who causes fast-sleep test patching to regress.

    Someone could break the test-only monkey-patching of gevent.sleep
    without noticing and costing quite a bit of aggravation aggregated
    over time waiting in tests, added bit by bit.

    To avoid that, add this incredibly huge/annoying delay that can
    only be avoided by monkey-patch to catch the regression.
    """
    gevent.sleep(300)


def test_construction():
    """The constructor basically works."""
    wabs_deleter.Deleter('test', 'ing')


def test_close_error():
    """Ensure that attempts to use a closed Deleter results in an error."""

    d = wabs_deleter.Deleter(BlobService('test', 'ing'), 'test-container')
    d.close()

    with pytest.raises(exception.UserCritical):
        d.delete('no value should work')


def test_processes_one_deletion(collect):
    key_name = 'test-key-name'
    b = B(name=key_name)

    d = wabs_deleter.Deleter(BlobService('test', 'ing'), 'test-container')
    d.delete(b)
    d.close()

    assert collect.deleted_keys == [key_name]


def test_processes_many_deletions(collect):
    # Generate a target list of keys in a stable order
    target = sorted(['test-key-' + str(x) for x in range(20001)])

    # Construct boto S3 Keys from the generated names and delete them
    # all.
    blobs = [B(name=key_name) for key_name in target]
    d = wabs_deleter.Deleter(BlobService('test', 'ing'), 'test-container')

    for b in blobs:
        d.delete(b)

    d.close()

    # Sort the deleted key names to obtain another stable order and
    # then ensure that everything was passed for deletion
    # successfully.
    assert sorted(collect.deleted_keys) == target


def test_retry_on_normal_error(collect):
    """Ensure retries are processed for most errors."""
    key_name = 'test-key-name'
    b = B(name=key_name)

    collect.inject(Exception('Normal error'))
    d = wabs_deleter.Deleter(BlobService('test', 'ing'), 'test-container')
    d.delete(b)

    # Since delete_keys will fail over and over again, aborted_keys
    # should grow quickly.
    while len(collect.aborted_keys) < 2:
        gevent.sleep(0.1)

    # Since delete_keys has been failing repeatedly, no keys should be
    # successfully deleted.
    assert not collect.deleted_keys

    # Turn off fault injection and flush/synchronize with close().
    collect.inject(None)
    d.close()

    # The one enqueued job should have been processed.n
    assert collect.deleted_keys == [key_name]


def test_no_retry_on_keyboadinterrupt(collect):
    """Ensure that KeyboardInterrupts are forwarded."""
    key_name = 'test-key-name'
    b = B(name=key_name)

    # If vanilla KeyboardInterrupt is used, then sending SIGINT to the
    # test can cause it to pass improperly, so use a subtype instead.
    class MarkedKeyboardInterrupt(KeyboardInterrupt):
        pass

    collect.inject(MarkedKeyboardInterrupt('SIGINT, probably'))
    d = wabs_deleter.Deleter(BlobService('test', 'ing'), 'test-container')

    with pytest.raises(MarkedKeyboardInterrupt):
        d.delete(b)

        # Exactly when coroutines are scheduled is non-deterministic,
        # so spin while yielding to provoke the
        # MarkedKeyboardInterrupt being processed within the
        # pytest.raises context manager.
        while True:
            gevent.sleep(0.1)

    # Only one key should have been aborted, since the purpose is to
    # *not* retry when processing KeyboardInterrupt.
    assert collect.aborted_keys == [key_name]

    # Turn off fault injection and flush/synchronize with close().
    collect.inject(None)
    d.close()

    # Since there is no retrying, no keys should be deleted.
    assert not collect.deleted_keys

########NEW FILE########
__FILENAME__ = test_wabs_worker
import pytest

from wal_e.worker.wabs import BackupList
from wal_e import storage

from wabs_integration_help import (
    FreshContainer,
    no_real_wabs_credentials,
)

# Contrivance to quiet down pyflakes, since pytest does some
# string-evaluation magic in test collection.
no_real_wabs_credentials = no_real_wabs_credentials


@pytest.mark.skipif("no_real_wabs_credentials()")
def test_empty_latest_listing():
    """Test listing a 'backup-list LATEST' on an empty prefix."""
    container_name = 'wal-e-test-empty-listing'
    layout = storage.StorageLayout('wabs://{0}/test-prefix'
                                   .format(container_name))

    with FreshContainer(container_name) as fb:
        fb.create()
        bl = BackupList(fb.conn, layout, False)
        found = list(bl.find_all('LATEST'))
        assert len(found) == 0

########NEW FILE########
__FILENAME__ = test_wal_segment
import pytest

from stage_pgxlog import pg_xlog
from wal_e import worker
from wal_e import exception

# Quiet pyflakes about pytest fixtures.
assert pg_xlog


def make_segment(num, **kwargs):
    return worker.WalSegment('pg_xlog/' + str(num) * 8 * 3, **kwargs)


def test_simple_create():
    """Check __init__."""
    make_segment(1)


def test_mark_done_invariant():
    """Check explicit segments cannot be .mark_done'd."""
    seg = make_segment(1, explicit=True)

    with pytest.raises(exception.UserCritical):
        seg.mark_done()


def test_mark_done(pg_xlog):
    """Check non-explicit segments can be .mark_done'd."""
    seg = make_segment(1, explicit=False)

    pg_xlog.touch(seg.name, '.ready')
    seg.mark_done()


def test_mark_done_problem(pg_xlog, monkeypatch):
    """Check that mark_done fails loudly if status file is missing.

    While in normal operation, WAL-E does not expect races against
    other processes manipulating .ready files.  But, just in case that
    should occur, WAL-E is designed to crash, exercised here.
    """
    seg = make_segment(1, explicit=False)

    with pytest.raises(exception.UserCritical):
        seg.mark_done()


def test_simple_search(pg_xlog):
    """Must find a .ready file"""
    name = '1' * 8 * 3
    pg_xlog.touch(name, '.ready')

    segs = worker.WalSegment.from_ready_archive_status('pg_xlog')
    assert segs.next().path == 'pg_xlog/' + name

    with pytest.raises(StopIteration):
        segs.next()


def test_multi_search(pg_xlog):
    """Test finding a few ready files.

    Also throw in some random junk to make sure they are filtered out
    from processing correctly.
    """
    for i in xrange(3):
        ready = str(i) * 8 * 3
        pg_xlog.touch(ready, '.ready')

    # Throw in a complete segment that should be ignored.
    complete_segment_name = 'F' * 8 * 3
    pg_xlog.touch(complete_segment_name, '.done')

    # Throw in a history-file-alike that also should not be found,
    # even if it's ready.
    ready_history_file_name = ('F' * 8) + '.history'
    pg_xlog.touch(ready_history_file_name, '.ready')

    segs = worker.WalSegment.from_ready_archive_status(str(pg_xlog.pg_xlog))

    for i, seg in enumerate(segs):
        assert seg.name == str(i) * 8 * 3

    assert i == 2

    # Make sure nothing interesting happened to ignored files.
    pg_xlog.assert_exists(complete_segment_name, '.done')
    pg_xlog.assert_exists(ready_history_file_name, '.ready')

########NEW FILE########
__FILENAME__ = test_wal_transfer
import gevent
import pytest

from wal_e import worker
from wal_e.exception import UserCritical


class Explosion(Exception):
    """Marker type for fault injection."""
    pass


class FakeWalSegment(object):
    def __init__(self, seg_path, explicit=False,
                 upload_explosive=False,
                 mark_done_explosive=False):
        self.explicit = explicit
        self._upload_explosive = upload_explosive
        self._mark_done_explosive = mark_done_explosive

        self._marked = False
        self._uploaded = False

    def mark_done(self):
        if self._mark_done_explosive:
            raise self._mark_done_explosive

        self._marked = True


class FakeWalUploader(object):
    def __call__(self, segment):
        if segment._upload_explosive:
            raise segment._upload_explosive

        segment._uploaded = True
        return segment


def failed(seg):
    """Returns true if a segment could be a failed upload.

    Or in progress, the two are not distinguished.
    """
    return seg._marked is False and seg._uploaded is False


def success(seg):
    """Returns true if a segment has been successfully uploaded.

    Checks that mark_done was not called if this is an 'explicit' wal
    segment from Postgres.
    """
    if seg.explicit:
        assert seg._marked is False

    return seg._uploaded


def indeterminate(seg):
    """Returns true as long as the segment is internally consistent.

    Checks invariants of mark_done, depending on whether the segment
    has been uploaded.  This is useful in cases with tests with
    failures and concurrent execution, and calls out the state of the
    segment in any case to the reader.
    """
    if seg._uploaded:
        if seg.explicit:
            assert seg._marked is False
        else:
            assert seg._marked is True
    else:
        assert seg._marked is False

    return True


def prepare_multi_upload_segments():
    """Prepare a handful of fake segments for upload."""
    # The first segment is special, being explicitly passed by
    # Postgres.
    yield FakeWalSegment('0' * 8 * 3, explicit=True)

    # Additional segments are non-explicit, which means they will have
    # their metadata manipulated by wal-e rather than relying on the
    # Postgres archiver.
    for i in xrange(1, 5):
        yield FakeWalSegment(str(i) * 8 * 3, explicit=False)


def test_simple_upload():
    """Model a case where there is no concurrency while uploading."""
    group = worker.WalTransferGroup(FakeWalUploader())
    seg = FakeWalSegment('1' * 8 * 3, explicit=True)
    group.start(seg)
    group.join()

    assert success(seg)


def test_multi_upload():
    """Model a case with upload concurrency."""
    group = worker.WalTransferGroup(FakeWalUploader())
    segments = list(prepare_multi_upload_segments())

    # "Start" fake uploads
    for seg in segments:
        group.start(seg)

    group.join()

    # Check invariants on the non-explicit segments.
    for seg in segments:
        assert success(seg)


def test_simple_fail():
    """Model a simple failure in the non-concurrent case."""
    group = worker.WalTransferGroup(FakeWalUploader())

    exp = Explosion('fail')
    seg = FakeWalSegment('1' * 8 * 3, explicit=True, upload_explosive=exp)

    group.start(seg)

    with pytest.raises(Explosion) as e:
        group.join()

    assert e.value is exp
    assert failed(seg)


def test_multi_explicit_fail():
    """Model a failure of the explicit segment under concurrency."""
    group = worker.WalTransferGroup(FakeWalUploader())
    segments = list(prepare_multi_upload_segments())

    exp = Explosion('fail')
    segments[0]._upload_explosive = exp

    for seg in segments:
        group.start(seg)

    with pytest.raises(Explosion) as e:
        group.join()

    assert e.value is exp
    assert failed(segments[0])

    for seg in segments[1:]:
        assert success(seg)


def test_multi_pipeline_fail():
    """Model a failure of the pipelined segments under concurrency."""
    group = worker.WalTransferGroup(FakeWalUploader())
    segments = list(prepare_multi_upload_segments())

    exp = Explosion('fail')
    fail_idx = 2
    segments[fail_idx]._upload_explosive = exp

    for seg in segments:
        group.start(seg)

    with pytest.raises(Explosion) as e:
        group.join()

    assert e.value is exp

    for i, seg in enumerate(segments):
        if i == fail_idx:
            assert failed(seg)
        else:
            # Given race conditions in conjunction with exceptions --
            # which will abort waiting for other greenlets to finish
            # -- one can't know very much about the final state of
            # segment.
            assert indeterminate(seg)


def test_finally_execution():
    """When one segment fails ensure parallel segments clean up."""
    segBad = FakeWalSegment('1' * 8 * 3)
    segOK = FakeWalSegment('2' * 8 * 3)

    class CleanupCheckingUploader(object):
        def __init__(self):
            self.cleaned_up = False

        def __call__(self, segment):
            if segment is segOK:
                try:
                    while True:
                        gevent.sleep(0.1)
                finally:
                    self.cleaned_up = True

            elif segment is segBad:
                raise Explosion('fail')

            else:
                assert False, 'Expect only two segments'

            segment._uploaded = True
            return segment

    uploader = CleanupCheckingUploader()
    group = worker.WalTransferGroup(uploader)
    group.start(segOK)
    group.start(segBad)

    with pytest.raises(Explosion):
        group.join()

    assert uploader.cleaned_up is True


def test_start_after_join():
    """Break an invariant by adding transfers after .join."""
    group = worker.WalTransferGroup(FakeWalUploader())
    group.join()
    seg = FakeWalSegment('arbitrary')

    with pytest.raises(UserCritical):
        group.start(seg)


def test_mark_done_fault():
    """Exercise exception handling from .mark_done()"""
    group = worker.WalTransferGroup(FakeWalUploader())

    exp = Explosion('boom')
    seg = FakeWalSegment('arbitrary', mark_done_explosive=exp)
    group.start(seg)

    with pytest.raises(Explosion) as e:
        group.join()

    assert e.value is exp

########NEW FILE########
__FILENAME__ = wabs_integration_help
from azure.storage import BlobService
import os


def no_real_wabs_credentials():
    """Helps skip integration tests without live credentials.

    Phrased in the negative to make it read better with 'skipif'.
    """
    if os.getenv('WALE_WABS_INTEGRATION_TESTS') != 'TRUE':
        return True

    for e_var in ('WABS_ACCOUNT_NAME', 'WABS_ACCESS_KEY'):
        if os.getenv(e_var) is None:
            return True

    return False


def apathetic_container_delete(container_name, *args, **kwargs):
    conn = BlobService(*args, **kwargs)
    conn.delete_container(container_name)

    return conn


def insistent_container_delete(conn, container_name):
    while True:
        success = conn.delete_container(container_name)
        if not success:
            continue

        break


def insistent_container_create(conn, container_name, *args, **kwargs):
    while True:
        success = conn.create_container(container_name)
        if not success:
            continue

        break

    return success


class FreshContainer(object):

    def __init__(self, container_name, *args, **kwargs):
        self.container_name = container_name
        self.conn_args = args or [os.environ.get('WABS_ACCOUNT_NAME'),
                                  os.environ.get('WABS_ACCESS_KEY')]
        self.conn_kwargs = kwargs
        self.created_container = False

    def __enter__(self):
        # Clean up a dangling container from a previous test run, if
        # necessary.
        self.conn = apathetic_container_delete(self.container_name,
                                               *self.conn_args,
                                               **self.conn_kwargs)

        return self

    def create(self, *args, **kwargs):
        container = insistent_container_create(self.conn, self.container_name,
                                               *args, **kwargs)
        self.created_container = True

        return container

    def __exit__(self, typ, value, traceback):
        if not self.created_container:
            return False

        insistent_container_delete(self.conn, self.container_name)

        return False

########NEW FILE########
__FILENAME__ = calling_format
import boto

from boto import s3
from boto.s3 import connection
from wal_e import log_help

logger = log_help.WalELogger(__name__)

_S3_REGIONS = {
    # A map like this is actually defined in boto.s3 in newer versions of boto
    # but we reproduce it here for the folks (notably, Ubuntu 12.04) on older
    # versions.
    'ap-northeast-1': 's3-ap-northeast-1.amazonaws.com',
    'ap-southeast-1': 's3-ap-southeast-1.amazonaws.com',
    'ap-southeast-2': 's3-ap-southeast-2.amazonaws.com',
    'eu-west-1': 's3-eu-west-1.amazonaws.com',
    'sa-east-1': 's3-sa-east-1.amazonaws.com',
    'us-standard': 's3.amazonaws.com',
    'us-west-1': 's3-us-west-1.amazonaws.com',
    'us-west-2': 's3-us-west-2.amazonaws.com',
}

try:
    # Override the hard-coded region map with boto's mappings if
    # available.
    from boto.s3 import regions
    _S3_REGIONS.update(dict((r.name, r.endpoint) for r in regions()))
except ImportError:
    pass


def _is_ipv4_like(s):
    """Find if a string superficially looks like an IPv4 address.

    AWS documentation plays it fast and loose with this; in other
    regions, it seems like even non-valid IPv4 addresses (in
    particular, ones that possess decimal numbers out of range for
    IPv4) are rejected.
    """
    parts = s.split('.')

    if len(parts) != 4:
        return False

    for part in parts:
        try:
            int(part)
        except ValueError:
            return False

    return True


def _is_mostly_subdomain_compatible(bucket_name):
    """Returns True if SubdomainCallingFormat can be used...mostly

    This checks to make sure that putting aside certificate validation
    issues that a bucket_name is able to use the
    SubdomainCallingFormat.
    """
    return (bucket_name.lower() == bucket_name and
            len(bucket_name) >= 3 and
            len(bucket_name) <= 63 and
            '_' not in bucket_name and
            '..' not in bucket_name and
            '-.' not in bucket_name and
            '.-' not in bucket_name and
            not bucket_name.startswith('-') and
            not bucket_name.endswith('-') and
            not bucket_name.startswith('.') and
            not bucket_name.endswith('.') and
            not _is_ipv4_like(bucket_name))


def _connect_secureish(*args, **kwargs):
    """Connect using the safest available options.

    This turns on encryption (works in all supported boto versions)
    and certificate validation (in the subset of supported boto
    versions that can handle certificate validation, namely, those
    after 2.6.0).

    Versions below 2.6 don't support the validate_certs option to
    S3Connection, and enable it via configuration option just seems to
    cause an error.
    """
    if tuple(int(x) for x in boto.__version__.split('.')) >= (2, 6, 0):
        kwargs['validate_certs'] = True

    kwargs['is_secure'] = True

    return connection.S3Connection(*args, **kwargs)


class CallingInfo(object):
    """Encapsulate information used to produce a S3Connection."""

    def __init__(self, bucket_name=None, calling_format=None, region=None,
                 ordinary_endpoint=None):
        self.bucket_name = bucket_name
        self.calling_format = calling_format
        self.region = region
        self.ordinary_endpoint = ordinary_endpoint

    def __repr__(self):
        return ('CallingInfo({bucket_name}, {calling_format!r}, {region!r}, '
                '{ordinary_endpoint!r})'.format(**self.__dict__))

    def __str__(self):
        return repr(self)

    def connect(self, creds):
        """Return a boto S3Connection set up with great care.

        This includes TLS settings, calling format selection, and
        region detection.

        The credentials are applied by the caller because in many
        cases (instance-profile IAM) it is possible for those
        credentials to fluctuate rapidly.  By comparison, region
        fluctuations of a bucket name are not nearly so likely versus
        the gains of not looking up a bucket's region over and over.
        """
        def _conn_help(*args, **kwargs):
            return _connect_secureish(
                *args,
                provider=creds,
                calling_format=self.calling_format(),
                **kwargs)

        # Check if subdomain format compatible; no need to go through
        # any region detection mumbo-jumbo of any kind.
        if self.calling_format is connection.SubdomainCallingFormat:
            return _conn_help()

        # Check if OrdinaryCallingFormat compatible, but also see if
        # the endpoint has already been set, in which case only
        # setting the host= flag is necessary.
        assert self.calling_format is connection.OrdinaryCallingFormat
        if self.ordinary_endpoint is not None:
            return _conn_help(host=self.ordinary_endpoint)

        # By this point, this is an OrdinaryCallingFormat bucket that
        # has never had its region detected in this CallingInfo
        # instance.  So, detect its region (this can happen without
        # knowing the right regional endpoint) and store it to speed
        # future calls.
        assert self.calling_format is connection.OrdinaryCallingFormat
        assert self.region is None
        assert self.ordinary_endpoint is None

        conn = _conn_help()

        bucket = s3.bucket.Bucket(connection=conn,
                                  name=self.bucket_name)

        try:
            loc = bucket.get_location()
        except boto.exception.S3ResponseError, e:
            if e.status == 403:
                # A 403 can be caused by IAM keys that do not permit
                # GetBucketLocation.  To not change behavior for
                # environments that do not have GetBucketLocation
                # allowed, fall back to the default endpoint,
                # preserving behavior for those using us-standard.
                logger.warning(msg='cannot detect location of bucket',
                               detail=('The specified bucket name was: ' +
                                       repr(self.bucket_name)),
                               hint=('Permit the GetLocation permission for '
                                     'the provided AWS credentials.  '
                                     'Or, use a bucket name that follows the '
                                     'preferred bucket naming guidelines '
                                     'and has no dots in it.'))

                self.region = 'us-standard'
                self.ordinary_endpoint = _S3_REGIONS[self.region]
            else:
                raise
        else:
            # An empty, successful get location returns an empty
            # string to mean S3-Classic/US-Standard.
            if loc == '':
                loc = 'us-standard'

            self.region = loc
            self.ordinary_endpoint = _S3_REGIONS[loc]

        # Region/endpoint information completed: connect.
        assert self.ordinary_endpoint is not None
        return _conn_help(host=self.ordinary_endpoint)


def from_store_name(bucket_name):
    """Construct a CallingInfo value from a bucket name.

    This is useful to encapsulate the ugliness of setting up S3
    connections, especially with regions and TLS certificates are
    involved.
    """
    mostly_ok = _is_mostly_subdomain_compatible(bucket_name)

    if not mostly_ok:
        return CallingInfo(
            bucket_name=bucket_name,
            region='us-standard',
            calling_format=connection.OrdinaryCallingFormat,
            ordinary_endpoint=_S3_REGIONS['us-standard'])
    else:
        if '.' in bucket_name:
            # The bucket_name might have been DNS compatible, but once
            # dots are involved TLS certificate validations will
            # certainly fail even if that's the case.
            return CallingInfo(
                bucket_name=bucket_name,
                calling_format=connection.OrdinaryCallingFormat,
                region=None,
                ordinary_endpoint=None)
        else:
            # If the bucket follows naming rules and has no dots in
            # the name, SubdomainCallingFormat can be used, with TLS,
            # world-wide, and WAL-E can be region-oblivious.
            return CallingInfo(
                bucket_name=bucket_name,
                calling_format=connection.SubdomainCallingFormat,
                region=None,
                ordinary_endpoint=None)

    assert False

########NEW FILE########
__FILENAME__ = s3_credentials
from boto import provider
from functools import partial
from wal_e.exception import UserException


class InstanceProfileProvider(provider.Provider):
    """Override boto Provider to control use of the AWS metadata store

    In particular, prevent boto from looking in a series of places for
    keys outside off WAL-E's control (e.g. boto.cfg, environment
    variables, and so on).  As-is that precedence and detection code
    is in one big ream, and so a method override and some internal
    symbols are used to excise most of that cleverness.

    Also take this opportunity to inject a WAL-E-friendly exception to
    help the user with missing keys.

    """

    def get_credentials(self, access_key=None, secret_key=None,
                        security_token=None, profile_name=None):
        if self.MetadataServiceSupport[self.name]:
            self._populate_keys_from_metadata_server()

        if not self._secret_key:
            raise UserException('Could not retrieve secret key from instance '
                                'profile.',
                                hint='Check that your instance has an IAM '
                                'profile or set --aws-access-key-id')


Credentials = partial(provider.Provider, "aws")
InstanceProfileCredentials = partial(InstanceProfileProvider, 'aws')

########NEW FILE########
__FILENAME__ = s3_util
from urlparse import urlparse
import socket
import traceback
import gevent

import boto

from . import calling_format
from wal_e import log_help
from wal_e.pipeline import get_download_pipeline
from wal_e.piper import PIPE
from wal_e.retries import retry, retry_with_count

logger = log_help.WalELogger(__name__)

# Set a timeout for boto HTTP operations should no timeout be set.
# Yes, in the case the user *wanted* no timeouts, this would set one.
# If that becomes a problem, someone should post a bug, although I am
# having a hard time imagining why that behavior could ever be useful.
if not boto.config.has_option('Boto', 'http_socket_timeout'):
    if not boto.config.has_section('Boto'):
        boto.config.add_section('Boto')

    boto.config.set('Boto', 'http_socket_timeout', '5')


def _uri_to_key(creds, uri, conn=None):
    assert uri.startswith('s3://')
    url_tup = urlparse(uri)
    bucket_name = url_tup.netloc
    cinfo = calling_format.from_store_name(bucket_name)
    if conn is None:
        conn = cinfo.connect(creds)
    bucket = boto.s3.bucket.Bucket(connection=conn, name=bucket_name)
    return boto.s3.key.Key(bucket=bucket, name=url_tup.path)


def uri_put_file(creds, uri, fp, content_encoding=None, conn=None):
    # Per Boto 2.2.2, which will only read from the current file
    # position to the end.  This manifests as successfully uploaded
    # *empty* keys in S3 instead of the intended data because of how
    # tempfiles are used (create, fill, submit to boto).
    #
    # It is presumed it is the caller's responsibility to rewind the
    # file position, and since the whole program was written with this
    # in mind, assert it as a precondition for using this procedure.
    assert fp.tell() == 0

    k = _uri_to_key(creds, uri, conn=conn)

    if content_encoding is not None:
        k.content_type = content_encoding

    k.set_contents_from_file(fp, encrypt_key=True)
    return k


def uri_get_file(creds, uri, conn=None):
    k = _uri_to_key(creds, uri, conn=conn)
    return k.get_contents_as_string()


def do_lzop_get(creds, url, path, decrypt):
    """
    Get and decompress a S3 URL

    This streams the content directly to lzop; the compressed version
    is never stored on disk.

    """
    assert url.endswith('.lzo'), 'Expect an lzop-compressed file'

    def log_wal_fetch_failures_on_error(exc_tup, exc_processor_cxt):
        def standard_detail_message(prefix=''):
            return (prefix + '  There have been {n} attempts to fetch wal '
                    'file {url} so far.'.format(n=exc_processor_cxt, url=url))
        typ, value, tb = exc_tup
        del exc_tup

        # Screen for certain kinds of known-errors to retry from
        if issubclass(typ, socket.error):
            socketmsg = value[1] if isinstance(value, tuple) else value

            logger.info(
                msg='Retrying fetch because of a socket error',
                detail=standard_detail_message(
                    "The socket error's message is '{0}'."
                    .format(socketmsg)))
        elif (issubclass(typ, boto.exception.S3ResponseError) and
              value.error_code == 'RequestTimeTooSkewed'):
            logger.info(msg='Retrying fetch because of a Request Skew time',
                        detail=standard_detail_message())
        else:
            # For all otherwise untreated exceptions, report them as a
            # warning and retry anyway -- all exceptions that can be
            # justified should be treated and have error messages
            # listed.
            logger.warning(
                msg='retrying WAL file fetch from unexpected exception',
                detail=standard_detail_message(
                    'The exception type is {etype} and its value is '
                    '{evalue} and its traceback is {etraceback}'
                    .format(etype=typ, evalue=value,
                            etraceback=''.join(traceback.format_tb(tb)))))

        # Help Python GC by resolving possible cycles
        del tb

    @retry(retry_with_count(log_wal_fetch_failures_on_error))
    def download():
        with open(path, 'wb') as decomp_out:
            key = _uri_to_key(creds, url)
            with get_download_pipeline(PIPE, decomp_out, decrypt) as pl:
                g = gevent.spawn(write_and_return_error, key, pl.stdin)

                try:
                    # Raise any exceptions from write_and_return_error
                    exc = g.get()
                    if exc is not None:
                        raise exc
                except boto.exception.S3ResponseError, e:
                    if e.status == 404:
                        # Do not retry if the key not present, this
                        # can happen under normal situations.
                        pl.abort()
                        logger.warning(
                            msg=('could no longer locate object while '
                                 'performing wal restore'),
                            detail=('The absolute URI that could not be '
                                    'located is {url}.'.format(url=url)),
                            hint=('This can be normal when Postgres is trying '
                                  'to detect what timelines are available '
                                  'during restoration.'))
                        return False
                    else:
                        raise

            logger.info(
                msg='completed download and decompression',
                detail='Downloaded and decompressed "{url}" to "{path}"'
                .format(url=url, path=path))
        return True

    return download()


def write_and_return_error(key, stream):
    try:
        key.get_contents_to_file(stream)
        stream.flush()
    except Exception, e:
        return e
    finally:
        stream.close()

########NEW FILE########
__FILENAME__ = calling_format
import swiftclient


def connect(creds):
    """
    Construct a connection value from a container
    """
    return swiftclient.Connection(
        authurl=creds.authurl,
        user=creds.user,
        key=creds.password,
        auth_version="2",
        tenant_name=creds.tenant_name,
        os_options={
            "region_name": creds.region,
            "endpoint_type": creds.endpoint_type
        }
    )

########NEW FILE########
__FILENAME__ = credentials
class Credentials(object):
    def __init__(self, authurl, user, password, tenant_name, region,
            endpoint_type):
        self.authurl = authurl
        self.user = user
        self.password = password
        self.tenant_name = tenant_name
        self.region = region
        self.endpoint_type = endpoint_type

########NEW FILE########
__FILENAME__ = utils
import socket
import traceback
from urlparse import urlparse

import gevent

from swiftclient.exceptions import ClientException

from wal_e import log_help
from wal_e.blobstore.swift import calling_format
from wal_e.pipeline import get_download_pipeline
from wal_e.piper import PIPE
from wal_e.retries import retry, retry_with_count


logger = log_help.WalELogger(__name__)


class SwiftKey(object):
    def __init__(self, name, size, last_modified=None):
        self.name = name
        self.size = size
        self.last_modified = last_modified


def uri_put_file(creds, uri, fp, content_encoding=None):
    assert fp.tell() == 0
    assert uri.startswith('swift://')

    url_tup = urlparse(uri)

    container_name = url_tup.netloc
    conn = calling_format.connect(creds)

    conn.put_object(
        container_name, url_tup.path, fp, content_type=content_encoding
    )
    # Swiftclient doesn't return us the total file size, we see how much of the
    # file swiftclient read in order to determine the file size.
    return SwiftKey(url_tup.path, size=fp.tell())


def do_lzop_get(creds, uri, path, decrypt):
    """
    Get and decompress a Swift URL

    This streams the content directly to lzop; the compressed version
    is never stored on disk.

    """
    assert uri.endswith('.lzo'), 'Expect an lzop-compressed file'

    def log_wal_fetch_failures_on_error(exc_tup, exc_processor_cxt):
        def standard_detail_message(prefix=''):
            return (prefix + '  There have been {n} attempts to fetch wal '
                    'file {uri} so far.'.format(n=exc_processor_cxt, uri=uri))
        typ, value, tb = exc_tup
        del exc_tup

        # Screen for certain kinds of known-errors to retry from
        if issubclass(typ, socket.error):
            socketmsg = value[1] if isinstance(value, tuple) else value

            logger.info(
                msg='Retrying fetch because of a socket error',
                detail=standard_detail_message(
                    "The socket error's message is '{0}'."
                    .format(socketmsg)))
        else:
            # For all otherwise untreated exceptions, report them as a
            # warning and retry anyway -- all exceptions that can be
            # justified should be treated and have error messages
            # listed.
            logger.warning(
                msg='retrying WAL file fetch from unexpected exception',
                detail=standard_detail_message(
                    'The exception type is {etype} and its value is '
                    '{evalue} and its traceback is {etraceback}'
                    .format(etype=typ, evalue=value,
                            etraceback=''.join(traceback.format_tb(tb)))))

        # Help Python GC by resolving possible cycles
        del tb

    @retry(retry_with_count(log_wal_fetch_failures_on_error))
    def download():
        with open(path, 'wb') as decomp_out:
            with get_download_pipeline(PIPE, decomp_out, decrypt) as pl:

                conn = calling_format.connect(creds)

                g = gevent.spawn(write_and_return_error, uri, conn, pl.stdin)

                # Raise any exceptions from write_and_return_error
                try:
                    exc = g.get()
                    if exc is not None:
                        raise exc
                except ClientException as e:
                    if e.http_status == 404:
                        # Do not retry if the key not present, this
                        # can happen under normal situations.
                        pl.abort()
                        logger.warning(
                            msg=('could no longer locate object while '
                                 'performing wal restore'),
                            detail=('The absolute URI that could not be '
                                    'located is {uri}.'.format(uri=uri)),
                            hint=('This can be normal when Postgres is trying '
                                  'to detect what timelines are available '
                                  'during restoration.'))
                        return False
                    else:
                        raise

            logger.info(
                msg='completed download and decompression',
                detail='Downloaded and decompressed "{uri}" to "{path}"'
                .format(uri=uri, path=path))
        return True

    return download()


def uri_get_file(creds, uri, conn=None, resp_chunk_size=None):
    assert uri.startswith('swift://')
    url_tup = urlparse(uri)
    container_name = url_tup.netloc
    object_name = url_tup.path

    if conn is None:
        conn = calling_format.connect(creds)
    _, content = conn.get_object(
        container_name, object_name, resp_chunk_size=resp_chunk_size
    )
    return content


def write_and_return_error(uri, conn, stream):
    try:
        response = uri_get_file(None, uri, conn, resp_chunk_size=8192)
        for chunk in response:
            stream.write(chunk)
        stream.flush()
    except Exception, e:
        return e
    finally:
        stream.close()

########NEW FILE########
__FILENAME__ = calling_format
from azure.storage.blobservice import BlobService
from wal_e import log_help

logger = log_help.WalELogger(__name__)


# WABS connection requirements are not quite this same as those of
# S3 and so this class is overkill. Implementing for the sake of
# consistency only
class CallingInfo(object):
    """Encapsulate information used to produce a WABS connection.
    """

    def __init__(self, account_name):
        self.account_name = account_name

    def __repr__(self):
        return ('CallingInfo({account_name})'.format(**self.__dict__))

    def __str__(self):
        return repr(self)

    def connect(self, creds):
        """Return an azure BlobService instance.
        """
        return BlobService(account_name=creds.account_name,
                           account_key=creds.account_key,
                           protocol='https')


def from_store_name(container_name):
    """Construct a CallingInfo value from a target container name.
    """
    return CallingInfo(container_name)

########NEW FILE########
__FILENAME__ = wabs_credentials
class Credentials(object):
    def __init__(self, account_name, account_key):
        self.account_name = account_name
        self.account_key = account_key

########NEW FILE########
__FILENAME__ = wabs_util
import base64
import collections
import errno
import gevent
import os
import socket
import sys
import traceback

from azure import WindowsAzureMissingResourceError
from azure.storage import BlobService

from . import calling_format
from hashlib import md5
from urlparse import urlparse
from wal_e import log_help
from wal_e.pipeline import get_download_pipeline
from wal_e.piper import PIPE
from wal_e.retries import retry, retry_with_count

assert calling_format

logger = log_help.WalELogger(__name__)

_Key = collections.namedtuple('_Key', ['size'])
WABS_CHUNK_SIZE = 4 * 1024 * 1024


def uri_put_file(creds, uri, fp, content_encoding=None):
    assert fp.tell() == 0
    assert uri.startswith('wabs://')

    def log_upload_failures_on_error(exc_tup, exc_processor_cxt):
        def standard_detail_message(prefix=''):
            return (prefix + '  There have been {n} attempts to upload  '
                    'file {url} so far.'.format(n=exc_processor_cxt, url=uri))
        typ, value, tb = exc_tup
        del exc_tup

        # Screen for certain kinds of known-errors to retry from
        if issubclass(typ, socket.error):
            socketmsg = value[1] if isinstance(value, tuple) else value

            logger.info(
                msg='Retrying upload because of a socket error',
                detail=standard_detail_message(
                    "The socket error's message is '{0}'."
                    .format(socketmsg)))
        else:
            # For all otherwise untreated exceptions, report them as a
            # warning and retry anyway -- all exceptions that can be
            # justified should be treated and have error messages
            # listed.
            logger.warning(
                msg='retrying file upload from unexpected exception',
                detail=standard_detail_message(
                    'The exception type is {etype} and its value is '
                    '{evalue} and its traceback is {etraceback}'
                    .format(etype=typ, evalue=value,
                            etraceback=''.join(traceback.format_tb(tb)))))

        # Help Python GC by resolving possible cycles
        del tb

    # Because we're uploading in chunks, catch rate limiting and
    # connection errors which occur for each individual chunk instead of
    # failing the whole file and restarting.
    @retry(retry_with_count(log_upload_failures_on_error))
    def upload_chunk(chunk, block_id):
        check_sum = base64.encodestring(md5(chunk).digest()).strip('\n')
        conn.put_block(url_tup.netloc, url_tup.path, chunk,
                       block_id, content_md5=check_sum)

    url_tup = urlparse(uri)
    kwargs = dict(x_ms_blob_type='BlockBlob')
    if content_encoding is not None:
        kwargs['x_ms_blob_content_encoding'] = content_encoding

    conn = BlobService(creds.account_name, creds.account_key, protocol='https')
    conn.put_blob(url_tup.netloc, url_tup.path, '', **kwargs)

    # WABS requires large files to be uploaded in 4MB chunks
    block_ids = []
    length, index = 0, 0
    pool_size = os.getenv('WABS_UPLOAD_POOL_SIZE', 5)
    p = gevent.pool.Pool(size=pool_size)
    while True:
        data = fp.read(WABS_CHUNK_SIZE)
        if data:
            length += len(data)
            block_id = base64.b64encode(str(index))
            p.wait_available()
            p.spawn(upload_chunk, data, block_id)
            block_ids.append(block_id)
            index += 1
        else:
            p.join()
            break

    conn.put_block_list(url_tup.netloc, url_tup.path, block_ids)

    # To maintain consistency with the S3 version of this function we must
    # return an object with a certain set of attributes.  Currently, that set
    # of attributes consists of only 'size'
    return _Key(size=len(data))


def uri_get_file(creds, uri, conn=None):
    assert uri.startswith('wabs://')
    url_tup = urlparse(uri)

    if conn is None:
        conn = BlobService(creds.account_name, creds.account_key,
                           protocol='https')

    # Determin the size of the target blob
    props = conn.get_blob_properties(url_tup.netloc, url_tup.path)
    blob_size = int(props['content-length'])

    ret_size = 0
    data = ''
    # WABS requires large files to be downloaded in 4MB chunks
    while ret_size < blob_size:
        ms_range = 'bytes={}-{}'.format(ret_size,
                                        ret_size + WABS_CHUNK_SIZE - 1)
        while True:
            # Because we're downloading in chunks, catch rate limiting and
            # connection errors here instead of letting them bubble up to the
            # @retry decorator so that we don't have to start downloading the
            # whole file over again.
            try:
                part = conn.get_blob(url_tup.netloc,
                                     url_tup.path,
                                     x_ms_range=ms_range)
            except EnvironmentError as e:
                if e.errno in (errno.EBUSY, errno.ECONNRESET):
                    logger.warning(
                        msg="retrying after encountering exception",
                        detail=("Exception traceback:\n{0}".format(
                            traceback.format_exception(*sys.exc_info()))),
                        hint="")
                    gevent.sleep(30)
                else:
                    raise
            else:
                break
        length = len(part)
        ret_size += length
        data += part
        if length > 0 and length < WABS_CHUNK_SIZE:
            break
        elif length == 0:
            break

    return data


def do_lzop_get(creds, url, path, decrypt):
    """
    Get and decompress a S3 URL

    This streams the content directly to lzop; the compressed version
    is never stored on disk.

    """
    assert url.endswith('.lzo'), 'Expect an lzop-compressed file'
    assert url.startswith('wabs://')

    conn = BlobService(creds.account_name, creds.account_key, protocol='https')

    def log_wal_fetch_failures_on_error(exc_tup, exc_processor_cxt):
        def standard_detail_message(prefix=''):
            return (prefix + '  There have been {n} attempts to fetch wal '
                    'file {url} so far.'.format(n=exc_processor_cxt, url=url))
        typ, value, tb = exc_tup
        del exc_tup

        # Screen for certain kinds of known-errors to retry from
        if issubclass(typ, socket.error):
            socketmsg = value[1] if isinstance(value, tuple) else value

            logger.info(
                msg='Retrying fetch because of a socket error',
                detail=standard_detail_message(
                    "The socket error's message is '{0}'."
                    .format(socketmsg)))
        else:
            # For all otherwise untreated exceptions, report them as a
            # warning and retry anyway -- all exceptions that can be
            # justified should be treated and have error messages
            # listed.
            logger.warning(
                msg='retrying WAL file fetch from unexpected exception',
                detail=standard_detail_message(
                    'The exception type is {etype} and its value is '
                    '{evalue} and its traceback is {etraceback}'
                    .format(etype=typ, evalue=value,
                            etraceback=''.join(traceback.format_tb(tb)))))

        # Help Python GC by resolving possible cycles
        del tb

    @retry(retry_with_count(log_wal_fetch_failures_on_error))
    def download():
        with open(path, 'wb') as decomp_out:
            with get_download_pipeline(PIPE, decomp_out, decrypt) as pl:
                g = gevent.spawn(write_and_return_error, url, conn, pl.stdin)

                try:
                    # Raise any exceptions guarded by
                    # write_and_return_error.
                    exc = g.get()
                    if exc is not None:
                        raise exc
                except WindowsAzureMissingResourceError:
                    # Short circuit any re-try attempts under certain race
                    # conditions.
                    pl.abort()
                    logger.warning(
                        msg=('could no longer locate object while '
                             'performing wal restore'),
                        detail=('The absolute URI that could not be '
                                'located is {url}.'.format(url=url)),
                        hint=('This can be normal when Postgres is trying '
                              'to detect what timelines are available '
                              'during restoration.'))
                    return False

            logger.info(
                msg='completed download and decompression',
                detail='Downloaded and decompressed "{url}" to "{path}"'
                .format(url=url, path=path))
        return True

    return download()


def write_and_return_error(url, conn, stream):
    try:
        data = uri_get_file(None, url, conn=conn)
        stream.write(data)
        stream.flush()
    except Exception, e:
        return e
    finally:
        stream.close()

########NEW FILE########
__FILENAME__ = channel
"""Gevent 1.0 changed the semantics of gevent.queue.Queue(0)

This module is a shim to paper over that.  The meaning was reportedly
changed to mean "unlimited" rather than "no queue buffer".  That means
Queue(0) suddenly joins Queue() and Queue(None), while the old
Queue(0) behavior has been moved to a new construct, "Channel".

"""
import functools

from gevent import queue

if hasattr(queue, 'Channel'):
    Channel = queue.Channel
else:
    Channel = functools.partial(queue.Queue, maxsize=0)

########NEW FILE########
__FILENAME__ = cmd
#!/usr/bin/env python
"""WAL-E is a program to assist in performing PostgreSQL continuous
archiving on S3 or Windows Azure Blob Service (WABS): it handles pushing
and fetching of WAL segments and base backups of the PostgreSQL data directory.

"""
import sys


def gevent_monkey(*args, **kwargs):
    import gevent.monkey
    gevent.monkey.patch_socket(dns=True, aggressive=True)
    gevent.monkey.patch_ssl()
    gevent.monkey.patch_time()

# Monkey-patch procedures early.  If it doesn't work with gevent,
# sadly it cannot be used (easily) in WAL-E.
gevent_monkey()

# Instate a cipher suite that bans a series of weak and slow ciphers.
# Both RC4 (weak) 3DES (slow) have been seen in use.
#
# Only Python 2.7+ possesses the 'ciphers' keyword to wrap_socket.
if sys.version_info >= (2, 7):
    def getresponse_monkey():
        import httplib
        original = httplib.HTTPConnection.getresponse

        def monkey(*args, **kwargs):
            kwargs['buffering'] = True
            return original(*args, **kwargs)

        httplib.HTTPConnection.getresponse = monkey

    getresponse_monkey()

    def ssl_monkey():
        import ssl

        original = ssl.wrap_socket

        def wrap_socket_monkey(*args, **kwargs):
            # Set up an OpenSSL cipher string.
            #
            # Rationale behind each part:
            #
            # * HIGH: only use the most secure class of ciphers and
            #   key lengths, generally being 128 bits and larger.
            #
            # * !aNULL: exclude cipher suites that contain anonymous
            #   key exchange, making man in the middle attacks much
            #   more tractable.
            #
            # * !SSLv2: exclude any SSLv2 cipher suite, as this
            #   category has security weaknesses.  There is only one
            #   OpenSSL cipher suite that is in the "HIGH" category
            #   but uses SSLv2 protocols: DES_192_EDE3_CBC_WITH_MD5
            #   (see s2_lib.c)
            #
            #   Technically redundant given "!3DES", but the intent in
            #   listing it here is more apparent.
            #
            # * !RC4: exclude because it's a weak block cipher.
            #
            # * !3DES: exclude because it's very CPU intensive and
            #   most peers support another reputable block cipher.
            #
            # * !MD5: although it doesn't seem use of known flaws in
            #   MD5 is able to compromise an SSL session, the wide
            #   deployment of SHA-family functions means the
            #   compatibility benefits of allowing it are slim to
            #   none, so disable it until someone produces material
            #   complaint.
            kwargs['ciphers'] = 'HIGH:!aNULL:!SSLv2:!RC4:!3DES:!MD5'
            return original(*args, **kwargs)

        ssl.wrap_socket = wrap_socket_monkey

    ssl_monkey()

import argparse
import logging
import os
import re
import textwrap
import traceback

from wal_e import log_help

from wal_e import subprocess
from wal_e.exception import UserCritical
from wal_e.exception import UserException
from wal_e import storage
from wal_e.piper import popen_sp
from wal_e.worker.pg import PSQL_BIN, psql_csv_run
from wal_e.pipeline import LZOP_BIN, PV_BIN, GPG_BIN
from wal_e.worker.pg import CONFIG_BIN, PgControlDataParser

log_help.configure(
    format='%(name)-12s %(levelname)-8s %(message)s')

logger = log_help.WalELogger('wal_e.main')


def external_program_check(
    to_check=frozenset([PSQL_BIN, LZOP_BIN, PV_BIN])):
    """
    Validates the existence and basic working-ness of other programs

    Implemented because it is easy to get confusing error output when
    one does not install a dependency because of the fork-worker model
    that is both necessary for throughput and makes more obscure the
    cause of failures.  This is intended to be a time and frustration
    saving measure.  This problem has confused The Author in practice
    when switching rapidly between machines.

    """

    could_not_run = []
    error_msgs = []

    def psql_err_handler(popen):
        assert popen.returncode != 0
        error_msgs.append(textwrap.fill(
                'Could not get a connection to the database: '
                'note that superuser access is required'))

        # Bogus error message that is re-caught and re-raised
        raise EnvironmentError('INTERNAL: Had problems running psql '
                               'from external_program_check')

    with open(os.devnull, 'w') as nullf:
        for program in to_check:
            try:
                if program is PSQL_BIN:
                    psql_csv_run('SELECT 1', error_handler=psql_err_handler)
                else:
                    if program is PV_BIN:
                        extra_args = ['--quiet']
                    else:
                        extra_args = []

                    proc = popen_sp([program] + extra_args,
                                    stdout=nullf, stderr=nullf,
                                    stdin=subprocess.PIPE)

                    # Close stdin for processes that default to
                    # reading from the pipe; the programs WAL-E uses
                    # of this kind will terminate in this case.
                    proc.stdin.close()
                    proc.wait()
            except EnvironmentError:
                could_not_run.append(program)

    if could_not_run:
        error_msgs.append(
            'Could not run the following programs, are they installed? ' +
            ', '.join(could_not_run))

    if error_msgs:
        raise UserException(
            'could not run one or more external programs WAL-E depends upon',
            '\n'.join(error_msgs))

    return None


def extract_segment(text_with_extractable_segment):
    from wal_e.storage import BASE_BACKUP_REGEXP
    from wal_e.storage.base import SegmentNumber

    match = re.match(BASE_BACKUP_REGEXP, text_with_extractable_segment)
    if match is None:
        return None
    else:
        groupdict = match.groupdict()
        return SegmentNumber(log=groupdict['log'], seg=groupdict['seg'])


def build_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)

    aws_group = parser.add_mutually_exclusive_group()
    aws_group.add_argument('-k', '--aws-access-key-id',
                           help='public AWS access key. Can also be defined '
                           'in an environment variable. If both are defined, '
                           'the one defined in the programs arguments takes '
                           'precedence.')

    aws_group.add_argument('--aws-instance-profile', action='store_true',
                           help='Use the IAM Instance Profile associated '
                           'with this instance to authenticate with the S3 '
                           'API.')

    parser.add_argument('-a', '--wabs-account-name',
                        help='Account name of Windows Azure Blob Service '
                        'account. Can also be defined in an environment'
                        'variable. If both are defined, the one defined'
                        'in the programs arguments takes precedence.')

    parser.add_argument('--s3-prefix',
                        help='S3 prefix to run all commands against.  '
                        'Can also be defined via environment variable '
                        'WALE_S3_PREFIX.')

    parser.add_argument('--wabs-prefix',
                        help='Storage prefix to run all commands against.  '
                        'Can also be defined via environment variable '
                        'WALE_WABS_PREFIX.')

    parser.add_argument(
        '--gpg-key-id',
        help='GPG key ID to encrypt to. (Also needed when decrypting.)  '
        'Can also be defined via environment variable '
        'WALE_GPG_KEY_ID')

    parser.add_argument(
        '--terse', action='store_true',
        help='Only log messages as or more severe than a warning.')

    subparsers = parser.add_subparsers(title='subcommands',
                                       dest='subcommand')

    # Common arguments for backup-fetch and backup-push
    backup_fetchpush_parent = argparse.ArgumentParser(add_help=False)
    backup_fetchpush_parent.add_argument('PG_CLUSTER_DIRECTORY',
                                         help="Postgres cluster path, "
                                         "such as '/var/lib/database'")
    backup_fetchpush_parent.add_argument(
        '--pool-size', '-p', type=int, default=4,
        help='Set the maximum number of concurrent transfers')

    # operator to print the wal-e version
    subparsers.add_parser('version', help='print the wal-e version')

    # Common arguments for backup-list and backup-fetch
    #
    # NB: This does not include the --detail options because some
    # other commands use backup listing functionality in a way where
    # --detail is never required.
    backup_list_nodetail_parent = argparse.ArgumentParser(add_help=False)

    # Common arguments between wal-push and wal-fetch
    wal_fetchpush_parent = argparse.ArgumentParser(add_help=False)
    wal_fetchpush_parent.add_argument('WAL_SEGMENT',
                                      help='Path to a WAL segment to upload')

    backup_fetch_parser = subparsers.add_parser(
        'backup-fetch', help='fetch a hot backup from S3 or WABS',
        parents=[backup_fetchpush_parent, backup_list_nodetail_parent])
    backup_list_parser = subparsers.add_parser(
        'backup-list', parents=[backup_list_nodetail_parent],
        help='list backups in S3 or WABS')
    backup_push_parser = subparsers.add_parser(
        'backup-push', help='pushing a fresh hot backup to S3 or WABS',
        parents=[backup_fetchpush_parent])
    backup_push_parser.add_argument(
        '--cluster-read-rate-limit',
        help='Rate limit reading the PostgreSQL cluster directory to a '
        'tunable number of bytes per second', dest='rate_limit',
        metavar='BYTES_PER_SECOND',
        type=int, default=None)
    backup_push_parser.add_argument(
        '--while-offline',
        help=('Backup a Postgres cluster that is in a stopped state '
              '(for example, a replica that you stop and restart '
              'when taking a backup)'),
        dest='while_offline',
        action='store_true',
        default=False)

    # wal-push operator section
    wal_push_parser = subparsers.add_parser(
        'wal-push', help='push a WAL file to S3 or WABS',
        parents=[wal_fetchpush_parent])

    wal_push_parser.add_argument(
        '--pool-size', '-p', type=int, default=8,
        help='Set the maximum number of concurrent transfers')

    # backup-fetch operator section
    backup_fetch_parser.add_argument('BACKUP_NAME',
                                     help='the name of the backup to fetch')
    backup_fetch_parser.add_argument(
        '--blind-restore',
        help='Restore from backup without verification of tablespace symlinks',
        dest='blind_restore',
        action='store_true',
        default=False)

    backup_fetch_parser.add_argument(
        '--restore-spec',
        help=('Specification for the directory structure of the database '
              'restoration (optional, see README for more information).'),
        type=str,
        default=None)

    # backup-list operator section
    backup_list_parser.add_argument(
        'QUERY', nargs='?', default=None,
        help='a string qualifying backups to list')
    backup_list_parser.add_argument(
        '--detail', default=False, action='store_true',
        help='show more detailed information about every backup')

    # wal-fetch operator section
    wal_fetch_parser = subparsers.add_parser(
        'wal-fetch', help='fetch a WAL file from S3 or WABS',
        parents=[wal_fetchpush_parent])
    wal_fetch_parser.add_argument('WAL_DESTINATION',
                                  help='Path to download the WAL segment to')

    # delete subparser section
    delete_parser = subparsers.add_parser(
        'delete', help='operators to destroy specified data in S3 or WABS')
    delete_parser.add_argument('--dry-run', '-n', action='store_true',
                               help=('Only print what would be deleted, '
                                     'do not actually delete anything'))
    delete_parser.add_argument('--confirm', action='store_true',
                               help=('Actually delete data.  '
                                     'By default, a dry run is performed.  '
                                     'Overridden by --dry-run.'))
    delete_subparsers = delete_parser.add_subparsers(
        title='delete subcommands',
        description=('All operators that may delete data are contained '
                     'in this subcommand.'),
        dest='delete_subcommand')

    # delete 'before' operator
    delete_before_parser = delete_subparsers.add_parser(
        'before', help=('Delete all backups and WAL segments strictly before '
                        'the given base backup name or WAL segment number.  '
                        'The passed backup is *not* deleted.'))
    delete_before_parser.add_argument(
        'BEFORE_SEGMENT_EXCLUSIVE',
        help='A WAL segment number or base backup name')

    # delete 'retain' operator
    delete_retain_parser = delete_subparsers.add_parser(
        'retain', help=('Delete backups and WAL segments older than the '
                        'NUM_TO_RETAIN oldest base backup. This will leave '
                        'NUM_TO_RETAIN working backups in place.'))
    delete_retain_parser.add_argument(
        'NUM_TO_RETAIN', type=int,
        help='The number of base backups to retain')

    # delete old versions operator
    delete_subparsers.add_parser(
        'old-versions',
        help=('Delete all old versions of WAL-E backup files.  One probably '
              'wants to ensure that they take a new backup with the new '
              'format first.  '
              'This is useful after a WAL-E major release upgrade.'))

    # delete *everything* operator
    delete_subparsers.add_parser(
        'everything',
        help=('Delete all data in the current WAL-E context.  '
              'Typically this is only appropriate when decommissioning an '
              'entire WAL-E archive.'))
    return parser


def _config_hint_generate(optname, both_env_and_param):
    """Generate HINT language for missing configuration"""
    env = optname.replace('-', '_').upper()

    if both_env_and_param:
        option = '--' + optname.lower()
        return ('Pass "{0}" or set the environment variable "{1}".'
                .format(option, env))
    else:
        return 'Set the environment variable {0}.'.format(env)


def s3_explicit_creds(args):
    access_key = args.aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
    if access_key is None:
        raise UserException(
            msg='AWS Access Key credential is required but not provided',
            hint=(_config_hint_generate('aws-access-key-id', True)))

    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    if secret_key is None:
        raise UserException(
            msg='AWS Secret Key credential is required but not provided',
            hint=_config_hint_generate('aws-secret-access-key', False))

    security_token = os.getenv('AWS_SECURITY_TOKEN')

    from wal_e.blobstore import s3

    return s3.Credentials(access_key, secret_key, security_token)


def s3_instance_profile(args):
    from wal_e.blobstore import s3

    assert args.aws_instance_profile
    return s3.InstanceProfileCredentials()


def configure_backup_cxt(args):
    # Try to find some WAL-E prefix to store data in.
    prefix = (args.s3_prefix or args.wabs_prefix
              or os.getenv('WALE_S3_PREFIX') or os.getenv('WALE_WABS_PREFIX')
              or os.getenv('WALE_SWIFT_PREFIX'))

    if prefix is None:
        raise UserException(
            msg='no storage prefix defined',
            hint=(
                'Either set one of the --wabs-prefix or --s3-prefix options or'
                ' define one of the WALE_WABS_PREFIX, WALE_S3_PREFIX, or '
                'WALE_SWIFT_PREFIX environment variables.'
            )
        )

    store = storage.StorageLayout(prefix)

    # GPG can be optionally layered atop of every backend, so a common
    # code path suffices.
    gpg_key_id = args.gpg_key_id or os.getenv('WALE_GPG_KEY_ID')
    if gpg_key_id is not None:
        external_program_check([GPG_BIN])

    # Enumeration of reading in configuration for all supported
    # backend data stores, yielding value adhering to the
    # 'operator.Backup' protocol.
    if store.is_s3:
        if args.aws_instance_profile:
            creds = s3_instance_profile(args)
        else:
            creds = s3_explicit_creds(args)

        from wal_e.operator import s3_operator

        return s3_operator.S3Backup(store, creds, gpg_key_id)
    elif store.is_wabs:
        account_name = args.wabs_account_name or os.getenv('WABS_ACCOUNT_NAME')
        if account_name is None:
            raise UserException(
                msg='WABS account name is undefined',
                hint=_config_hint_generate('wabs-account-name', True))

        access_key = os.getenv('WABS_ACCESS_KEY')
        if access_key is None:
            raise UserException(
                msg='WABS access key credential is required but not provided',
                hint=_config_hint_generate('wabs-access-key', False))

        from wal_e.blobstore import wabs
        from wal_e.operator.wabs_operator import WABSBackup

        creds = wabs.Credentials(account_name, access_key)

        return WABSBackup(store, creds, gpg_key_id)
    elif store.is_swift:
        from wal_e.blobstore import swift
        from wal_e.operator.swift_operator import SwiftBackup

        creds = swift.Credentials(
            os.getenv('SWIFT_AUTHURL'),
            os.getenv('SWIFT_USER'),
            os.getenv('SWIFT_PASSWORD'),
            os.getenv('SWIFT_TENANT'),
            os.getenv('SWIFT_REGION'),
            os.getenv('SWIFT_ENDPOINT_TYPE', 'publicURL'),
        )
        return SwiftBackup(store, creds, gpg_key_id)
    else:
        raise UserCritical(
            msg='no unsupported blob stores should get here',
            hint='Report a bug.')


def monkeypatch_tarfile_copyfileobj():
    """Monkey-patch tarfile.copyfileobj to exploit large buffers"""
    import tarfile
    from wal_e import copyfileobj

    tarfile.copyfileobj = copyfileobj.copyfileobj


def render_subcommand(args):
    """Render a subcommand for human-centric viewing"""
    if args.subcommand == 'delete':
        return 'delete ' + args.delete_subcommand
    else:
        return args.subcommand


def main():
    parser = build_parser()
    args = parser.parse_args()
    subcommand = args.subcommand

    # Adjust logging level if terse output is set.
    if args.terse:
        log_help.set_level(logging.WARNING)

    # Handle version printing specially, because it doesn't need
    # credentials.
    if subcommand == 'version':
        import pkgutil

        print pkgutil.get_data('wal_e', 'VERSION').strip()
        sys.exit(0)

    # Print a start-up message right away.
    #
    # Otherwise, it is hard to tell when and how WAL-E started in logs
    # because often emits status output too late.
    logger.info(msg='starting WAL-E',
                detail=('The subcommand is "{0}".'
                        .format(render_subcommand(args))))

    try:
        backup_cxt = configure_backup_cxt(args)

        if subcommand == 'backup-fetch':
            monkeypatch_tarfile_copyfileobj()

            external_program_check([LZOP_BIN])
            backup_cxt.database_fetch(
                args.PG_CLUSTER_DIRECTORY,
                args.BACKUP_NAME,
                blind_restore=args.blind_restore,
                restore_spec=args.restore_spec,
                pool_size=args.pool_size)
        elif subcommand == 'backup-list':
            backup_cxt.backup_list(query=args.QUERY, detail=args.detail)
        elif subcommand == 'backup-push':
            monkeypatch_tarfile_copyfileobj()

            if args.while_offline:
                # we need to query pg_config first for the
                # pg_controldata's bin location
                external_program_check([CONFIG_BIN])
                parser = PgControlDataParser(args.PG_CLUSTER_DIRECTORY)
                controldata_bin = parser.controldata_bin()
                external_programs = [
                    LZOP_BIN,
                    PV_BIN,
                    controldata_bin]
            else:
                external_programs = [LZOP_BIN, PSQL_BIN, PV_BIN]

            external_program_check(external_programs)
            rate_limit = args.rate_limit

            while_offline = args.while_offline
            backup_cxt.database_backup(
                args.PG_CLUSTER_DIRECTORY,
                rate_limit=rate_limit,
                while_offline=while_offline,
                pool_size=args.pool_size)
        elif subcommand == 'wal-fetch':
            external_program_check([LZOP_BIN])
            res = backup_cxt.wal_restore(args.WAL_SEGMENT,
                                         args.WAL_DESTINATION)
            if not res:
                sys.exit(1)
        elif subcommand == 'wal-push':
            external_program_check([LZOP_BIN])
            backup_cxt.wal_archive(args.WAL_SEGMENT,
                                   concurrency=args.pool_size)
        elif subcommand == 'delete':
            # Set up pruning precedence, optimizing for *not* deleting data
            #
            # Canonicalize the passed arguments into the value
            # "is_dry_run_really"
            if args.dry_run is False and args.confirm is True:
                # Actually delete data *only* if there are *no* --dry-runs
                # present and --confirm is present.
                logger.info(msg='deleting data in the store')
                is_dry_run_really = False
            else:
                logger.info(msg='performing dry run of data deletion')
                is_dry_run_really = True

                import boto.s3.key
                import boto.s3.bucket

                # This is not necessary, but "just in case" to find bugs.
                def just_error(*args, **kwargs):
                    assert False, ('About to delete something in '
                                   'dry-run mode.  Please report a bug.')

                boto.s3.key.Key.delete = just_error
                boto.s3.bucket.Bucket.delete_keys = just_error

            # Handle the subcommands and route them to the right
            # implementations.
            if args.delete_subcommand == 'old-versions':
                backup_cxt.delete_old_versions(is_dry_run_really)
            elif args.delete_subcommand == 'everything':
                backup_cxt.delete_all(is_dry_run_really)
            elif args.delete_subcommand == 'retain':
                backup_cxt.delete_with_retention(is_dry_run_really,
                                                 args.NUM_TO_RETAIN)
            elif args.delete_subcommand == 'before':
                segment_info = extract_segment(args.BEFORE_SEGMENT_EXCLUSIVE)
                assert segment_info is not None
                backup_cxt.delete_before(is_dry_run_really, segment_info)
            else:
                assert False, 'Should be rejected by argument parsing.'
        else:
            logger.error(msg='subcommand not implemented',
                         detail=('The submitted subcommand was {0}.'
                                 .format(subcommand)),
                         hint='Check for typos or consult wal-e --help.')
            sys.exit(127)

        # Report on all encountered exceptions, and raise the last one
        # to take advantage of the final catch-all reporting and exit
        # code management.
        if backup_cxt.exceptions:
            for exc in backup_cxt.exceptions[:-1]:
                if isinstance(exc, UserException):
                    logger.log(level=exc.severity,
                               msg=exc.msg, detail=exc.detail, hint=exc.hint)
                else:
                    logger.error(msg=exc)

            raise backup_cxt.exceptions[-1]

    except UserException, e:
        logger.log(level=e.severity,
                   msg=e.msg, detail=e.detail, hint=e.hint)
        sys.exit(1)
    except Exception, e:
        logger.critical(
            msg='An unprocessed exception has avoided all error handling',
            detail=''.join(traceback.format_exception(*sys.exc_info())))
        sys.exit(2)

########NEW FILE########
__FILENAME__ = copyfileobj
import shutil

from wal_e import pipebuf


def copyfileobj(src, dst, length=None):
    """Copy length bytes from fileobj src to fileobj dst.
       If length is None, copy the entire content.
    """
    BUFSIZE = pipebuf.PIPE_BUF_BYTES

    if length == 0:
        return
    if length is None:
        shutil.copyfileobj(src, dst, BUFSIZE)
        return

    blocks, remainder = divmod(length, BUFSIZE)
    for b in xrange(blocks):
        buf = src.read(BUFSIZE)
        if len(buf) < BUFSIZE:
            raise IOError("end of file reached")
        dst.write(buf)

    if remainder != 0:
        buf = src.read(remainder)
        if len(buf) < remainder:
            raise IOError("end of file reached")
        dst.write(buf)
    return

########NEW FILE########
__FILENAME__ = exception
from logging import ERROR, CRITICAL
from logging import getLevelName
from wal_e.log_help import WalELogger


class UserException(Exception):
    """
    Superclass intended for user-visible errors

    Instead of stacktraces, these will be prettyprinted.  The
    suggested error message guidelines are the same as for the
    PostgreSQL project:

    http://developer.postgresql.org/pgdocs/postgres/error-style-guide.html

    If it is necessary to trap these exceptions, use a subclass.

    >>> raise UserException(msg='foo', detail='bar')
    Traceback (most recent call last):
        ...
    UserException: ERROR: MSG: foo
    DETAIL: bar
    STRUCTURED: time=... pid=...
    >>> raise UserException(msg='foo', detail='bar', hint='hello')
    Traceback (most recent call last):
        ...
    UserException: ERROR: MSG: foo
    DETAIL: bar
    HINT: hello
    STRUCTURED: time=... pid=...
    """

    def __init__(self, msg=None, detail=None, hint=None):
        # msg uses a keyword argument with a default to make the
        # multiprocessing module happy, as it seems to set them after
        # the fact.  Realistically, one should *always* be setting msg
        # when used in normal code though.
        self.msg = msg
        self.detail = detail
        self.hint = hint
        self.severity = ERROR

    def __str__(self):
        return "{0}: {1}".format(getLevelName(self.severity),
                WalELogger.fmt_logline(self.msg, self.detail, self.hint))


class UserCritical(UserException):
    """
    For errors more severe than the norm.

    "DETAIL" may be much more verbose, and there is likely no hint.

    """

    def __init__(self, *args, **kwargs):
        UserException.__init__(self, *args, **kwargs)
        self.severity = CRITICAL

########NEW FILE########
__FILENAME__ = log_help
"""
A module to assist with using the Python logging module

"""
import datetime
import errno
import logging
import logging.handlers
import os

from os import path


# Global logging handlers created by configure.
HANDLERS = []


class IndentFormatter(logging.Formatter):

    def format(self, record, *args, **kwargs):
        """
        Format a message in the log

        Act like the normal format, but indent anything that is a
        newline within the message.

        """
        return logging.Formatter.format(
            self, record, *args, **kwargs).replace('\n', '\n' + ' ' * 8)


def configure(*args, **kwargs):
    """
    Configure logging.

    Borrowed from logging.basicConfig

    Uses the IndentFormatter instead of the regular Formatter

    Also, opts the caller into Syslog output, unless syslog could not
    be opened for some reason or another, in which case a warning will
    be printed to the other log handlers.

    """
    # Configuration must only happen once: no mechanism for avoiding
    # duplication of handlers exists.
    assert len(HANDLERS) == 0

    # Add stderr output.
    HANDLERS.append(logging.StreamHandler())

    def terrible_log_output(s):
        import sys

        print >>sys.stderr, s

    places = [
        # Linux
        '/dev/log',

        # FreeBSD
        '/var/run/log',

        # Macintosh
        '/var/run/syslog',
    ]

    default_syslog_address = places[0]
    for p in places:
        if path.exists(p):
            default_syslog_address = p
            break

    syslog_address = kwargs.setdefault('syslog_address',
                                       default_syslog_address)

    try:
        # Add syslog output.
        HANDLERS.append(logging.handlers.SysLogHandler(syslog_address))
    except EnvironmentError, e:
        if e.errno in [errno.ENOENT, errno.EACCES, errno.ECONNREFUSED]:
            message = ('wal-e: Could not set up syslog, '
                       'continuing anyway.  '
                       'Reason: {0}').format(errno.errorcode[e.errno])

            terrible_log_output(message)

    fs = kwargs.get("format", logging.BASIC_FORMAT)
    dfs = kwargs.get("datefmt", None)
    fmt = IndentFormatter(fs, dfs)

    for handler in HANDLERS:
        handler.setFormatter(fmt)
        logging.root.addHandler(handler)

    # Default to INFO level logging.
    set_level(kwargs.get('level', logging.INFO))


def set_level(level):
    """Adjust the logging level of WAL-E"""
    for handler in HANDLERS:
        handler.setLevel(level)

    logging.root.setLevel(level)


class WalELogger(object):
    def __init__(self, *args, **kwargs):
        self._logger = logging.getLogger(*args, **kwargs)

    @staticmethod
    def _fmt_structured(d):
        """Formats '{k1:v1, k2:v2}' => 'time=... pid=... k1=v1 k2=v2'

        Output is lexically sorted, *except* the time and pid always
        come first, to assist with human scanning of the data.
        """
        timeEntry = datetime.datetime.utcnow().strftime(
            "time=%Y-%m-%dT%H:%M:%S.%f-00")
        pidEntry = "pid=" + str(os.getpid())

        rest = sorted('='.join([unicode(k), unicode(v)])
                      for (k, v) in d.items())

        return ' '.join([timeEntry, pidEntry] + rest)

    @staticmethod
    def fmt_logline(msg, detail=None, hint=None, structured=None):
        msg_parts = ['MSG: ' + msg]

        if detail is not None:
            msg_parts.append('DETAIL: ' + detail)
        if hint is not None:
            msg_parts.append('HINT: ' + hint)

        # Initialize a fresh dictionary if structured is not passed,
        # because keyword arguments are not re-evaluated when calling
        # the function and it's okay for callees to mutate their
        # passed dictionary.
        if structured is None:
            structured = {}

        msg_parts.append('STRUCTURED: ' +
                         WalELogger._fmt_structured(structured))

        return '\n'.join(msg_parts)

    def log(self, level, msg, *args, **kwargs):
        detail = kwargs.pop('detail', None)
        hint = kwargs.pop('hint', None)
        structured = kwargs.pop('structured', None)

        self._logger.log(
            level,
            self.fmt_logline(msg, detail, hint, structured),
            *args, **kwargs)

    # Boilerplate convenience shims to different logging levels.  One
    # could abuse dynamism to generate these bindings in a loop, but
    # one day I hope to run with PyPy and tricks like that tend to
    # lobotomize an optimizer something fierce.

    def debug(self, *args, **kwargs):
        self.log(logging.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        self.log(logging.INFO, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self.log(logging.WARNING, *args, **kwargs)

    def error(self, *args, **kwargs):
        self.log(logging.ERROR, *args, **kwargs)

    def critical(self, *args, **kwargs):
        self.log(logging.CRITICAL, *args, **kwargs)

    # End convenience shims

########NEW FILE########
__FILENAME__ = backup
import sys
import os
import json
import functools
import gevent
import gevent.pool
import itertools

from cStringIO import StringIO
from wal_e import log_help
from wal_e import storage
from wal_e import tar_partition
from wal_e.exception import UserException, UserCritical
from wal_e.worker import (WalSegment,
                          WalUploader,
                          PgBackupStatements,
                          PgControlDataParser,
                          PartitionUploader,
                          TarUploadPool,
                          WalTransferGroup,
                          uri_put_file,
                          do_lzop_get)


# File mode on directories created during restore process
DEFAULT_DIR_MODE = 0700
# Provides guidence in object names as to the version of the file
# structure.
FILE_STRUCTURE_VERSION = storage.CURRENT_VERSION
logger = log_help.WalELogger(__name__)


class Backup(object):

    def __init__(self, layout, creds, gpg_key_id):
        self.layout = layout
        self.creds = creds
        self.gpg_key_id = gpg_key_id
        self.exceptions = []

    def new_connection(self):
        return self.cinfo.connect(self.creds)

    def backup_list(self, query, detail):
        """
        Lists base backups and basic information about them

        """
        import csv
        from wal_e.storage.base import BackupInfo
        bl = self._backup_list(detail)

        # If there is no query, return an exhaustive list, otherwise
        # find a backup instad.
        if query is None:
            bl_iter = bl
        else:
            bl_iter = bl.find_all(query)

        # TODO: support switchable formats for difference needs.
        w_csv = csv.writer(sys.stdout, dialect='excel-tab')
        w_csv.writerow(BackupInfo._fields)

        for bi in bl_iter:
            w_csv.writerow([getattr(bi, k) for k in BackupInfo._fields])

        sys.stdout.flush()

    def database_fetch(self, pg_cluster_dir, backup_name,
                       blind_restore, restore_spec, pool_size):
        if os.path.exists(os.path.join(pg_cluster_dir, 'postmaster.pid')):
            hint = ('Shut down postgres. If there is a stale lockfile, '
                    'then remove it after being very sure postgres is not '
                    'running.')
            raise UserException(
                msg='attempting to overwrite a live data directory',
                detail='Found a postmaster.pid lockfile, and aborting',
                hint=hint)

        bl = self._backup_list(False)
        backups = list(bl.find_all(backup_name))

        assert len(backups) <= 1
        if len(backups) == 0:
            raise UserException(
                msg='no backups found for fetching',
                detail=('No backup matching the query {0} '
                        'was able to be located.'.format(backup_name)))
        elif len(backups) > 1:
            raise UserException(
                msg='more than one backup found for fetching',
                detail=('More than one backup matching the query {0} was able '
                        'to be located.'.format(backup_name)),
                hint='To list qualifying backups, '
                'try "wal-e backup-list QUERY".')

        # There must be exactly one qualifying backup at this point.
        assert len(backups) == 1
        assert backups[0] is not None

        backup_info = backups[0]
        backup_info.load_detail(self.new_connection())
        self.layout.basebackup_tar_partition_directory(backup_info)

        if restore_spec is not None:
            if restore_spec != 'SOURCE':
                if not os.path.isfile(restore_spec):
                    raise UserException(
                        msg='Restore specification does not exist',
                        detail='File not found: %s'.format(restore_spec),
                        hint=('Provide valid json-formatted restoration '
                              'specification, or pseudo-name "SOURCE" to '
                              'restore using the specification from the '
                              'backup progenitor.'))
                with open(restore_spec, 'r') as fs:
                    spec = json.load(fs)
                backup_info.spec.update(spec)
            if 'base_prefix' not in spec or not spec['base_prefix']:
                backup_info.spec['base_prefix'] = pg_cluster_dir
            self._build_restore_paths(backup_info.spec)
        else:
            # If the user hasn't passed in a restoration specification
            # use pg_cluster_dir as the resore prefix
            backup_info.spec['base_prefix'] = pg_cluster_dir

        if not blind_restore:
            self._verify_restore_paths(backup_info.spec)

        connections = []
        for i in xrange(pool_size):
            connections.append(self.new_connection())

        partition_iter = self.worker.TarPartitionLister(
            connections[0], self.layout, backup_info)

        assert len(connections) == pool_size
        fetchers = []
        for i in xrange(pool_size):
            fetchers.append(self.worker.BackupFetcher(
                connections[i], self.layout, backup_info,
                backup_info.spec['base_prefix'],
                (self.gpg_key_id is not None)))
        assert len(fetchers) == pool_size

        p = gevent.pool.Pool(size=pool_size)
        fetcher_cycle = itertools.cycle(fetchers)
        for part_name in partition_iter:
            p.spawn(
                self._exception_gather_guard(
                    fetcher_cycle.next().fetch_partition),
                part_name)

        p.join(raise_error=True)

    def database_backup(self, data_directory, *args, **kwargs):
        """Uploads a PostgreSQL file cluster to S3 or Windows Azure Blob
        Service

        Mechanism: just wraps _upload_pg_cluster_dir with
        start/stop backup actions with exception handling.

        In particular there is a 'finally' block to stop the backup in
        most situations.
        """
        upload_good = False
        backup_stop_good = False
        while_offline = False
        start_backup_info = None
        if 'while_offline' in kwargs:
            while_offline = kwargs.pop('while_offline')

        try:
            if not while_offline:
                start_backup_info = PgBackupStatements.run_start_backup()
                version = PgBackupStatements.pg_version()['version']
            else:
                if os.path.exists(os.path.join(data_directory,
                                               'postmaster.pid')):
                    hint = ('Shut down postgres.  '
                            'If there is a stale lockfile, '
                            'then remove it after being very sure postgres '
                            'is not running.')
                    raise UserException(
                        msg='while_offline set, but pg looks to be running',
                        detail='Found a postmaster.pid lockfile, and aborting',
                        hint=hint)

                ctrl_data = PgControlDataParser(data_directory)
                start_backup_info = ctrl_data.last_xlog_file_name_and_offset()
                version = ctrl_data.pg_version()

            ret_tuple = self._upload_pg_cluster_dir(
                start_backup_info, data_directory, version=version, *args,
                **kwargs)
            spec, uploaded_to, expanded_size_bytes = ret_tuple
            upload_good = True
        finally:
            if not upload_good:
                logger.warning(
                    'blocking on sending WAL segments',
                    detail=('The backup was not completed successfully, '
                            'but we have to wait anyway.  '
                            'See README: TODO about pg_cancel_backup'))

            if not while_offline:
                stop_backup_info = PgBackupStatements.run_stop_backup()
            else:
                stop_backup_info = start_backup_info
            backup_stop_good = True

        # XXX: Ugly, this is more of a 'worker' task because it might
        # involve retries and error messages, something that is not
        # treated by the "operator" category of modules.  So
        # basically, if this small upload fails, the whole upload
        # fails!
        if upload_good and backup_stop_good:
            # Try to write a sentinel file to the cluster backup
            # directory that indicates that the base backup upload has
            # definitely run its course and also communicates what WAL
            # segments are needed to get to consistency.
            sentinel_content = StringIO()
            json.dump(
                {'wal_segment_backup_stop':
                     stop_backup_info['file_name'],
                 'wal_segment_offset_backup_stop':
                     stop_backup_info['file_offset'],
                 'expanded_size_bytes': expanded_size_bytes,
                 'spec': spec},
                sentinel_content)

            # XXX: should use the storage operators.
            #
            # XXX: distinguish sentinels by *PREFIX* not suffix,
            # which makes searching harder. (For the next version
            # bump).
            sentinel_content.seek(0)

            uri_put_file(self.creds,
                         uploaded_to + '_backup_stop_sentinel.json',
                         sentinel_content, content_encoding='application/json')
        else:
            # NB: Other exceptions should be raised before this that
            # have more informative results, it is intended that this
            # exception never will get raised.
            raise UserCritical('could not complete backup process')

    def wal_archive(self, wal_path, concurrency=1):
        """
        Uploads a WAL file to S3 or Windows Azure Blob Service

        This code is intended to typically be called from Postgres's
        archive_command feature.
        """

        # Upload the segment expressly indicated.  It's special
        # relative to other uploads when parallel wal-push is enabled,
        # in that it's not desirable to tweak its .ready/.done files
        # in archive_status.
        xlog_dir = os.path.dirname(wal_path)
        segment = WalSegment(wal_path, explicit=True)
        uploader = WalUploader(self.layout, self.creds, self.gpg_key_id)
        group = WalTransferGroup(uploader)
        group.start(segment)

        # Upload any additional wal segments up to the specified
        # concurrency by scanning the Postgres archive_status
        # directory.
        started = 1
        seg_stream = WalSegment.from_ready_archive_status(xlog_dir)
        while started < concurrency:
            try:
                other_segment = seg_stream.next()
            except StopIteration:
                break

            if other_segment.path != wal_path:
                group.start(other_segment)
                started += 1

        # Wait for uploads to finish.
        group.join()

    def wal_restore(self, wal_name, wal_destination):
        """
        Downloads a WAL file from S3 or Windows Azure Blob Service

        This code is intended to typically be called from Postgres's
        restore_command feature.

        NB: Postgres doesn't guarantee that wal_name ==
        basename(wal_path), so both are required.

        """
        # TODO :: Move arbitray path construction to StorageLayout Object
        url = '{0}/wal_{1}/{2}.lzo'.format(
            self.layout.prefix.rstrip('/'), FILE_STRUCTURE_VERSION, wal_name)

        logger.info(
            msg='begin wal restore',
            structured={'action': 'wal-fetch',
                        'key': url,
                        'seg': wal_name,
                        'prefix': self.layout.path_prefix,
                        'state': 'begin'})

        ret = do_lzop_get(self.creds, url, wal_destination,
                          self.gpg_key_id is not None)

        logger.info(
            msg='complete wal restore',
            structured={'action': 'wal-fetch',
                        'key': url,
                        'seg': wal_name,
                        'prefix': self.layout.path_prefix,
                        'state': 'complete'})

        return ret

    def delete_old_versions(self, dry_run):
        assert storage.CURRENT_VERSION not in storage.OBSOLETE_VERSIONS

        for obsolete_version in storage.OBSOLETE_VERSIONS:
            self.delete_all(dry_run, self.layout)

    def delete_all(self, dry_run):
        conn = self.new_connection()
        delete_cxt = self.worker.DeleteFromContext(conn, self.layout, dry_run)
        delete_cxt.delete_everything()

    def delete_before(self, dry_run, segment_info):
        conn = self.new_connection()
        delete_cxt = self.worker.DeleteFromContext(conn, self.layout, dry_run)
        delete_cxt.delete_before(segment_info)

    def delete_with_retention(self, dry_run, num_to_retain):
        conn = self.new_connection()
        delete_cxt = self.worker.DeleteFromContext(conn, self.layout, dry_run)
        delete_cxt.delete_with_retention(num_to_retain)

    def _backup_list(self, detail):
        conn = self.new_connection()
        bl = self.worker.BackupList(conn, self.layout, detail)
        return bl

    def _upload_pg_cluster_dir(self, start_backup_info, pg_cluster_dir,
                               version, pool_size, rate_limit=None):
        """
        Upload to url_prefix from pg_cluster_dir

        This function ignores the directory pg_xlog, which contains WAL
        files and are not generally part of a base backup.

        Note that this is also lzo compresses the files: thus, the number
        of pooled processes involves doing a full sequential scan of the
        uncompressed Postgres heap file that is pipelined into lzo. Once
        lzo is completely finished (necessary to have access to the file
        size) the file is sent to S3 or WABS.

        TODO: Investigate an optimization to decouple the compression and
        upload steps to make sure that the most efficient possible use of
        pipelining of network and disk resources occurs.  Right now it
        possible to bounce back and forth between bottlenecking on reading
        from the database block device and subsequently the S3/WABS sending
        steps should the processes be at the same stage of the upload
        pipeline: this can have a very negative impact on being able to
        make full use of system resources.

        Furthermore, it desirable to overflowing the page cache: having
        separate tunables for number of simultanious compression jobs
        (which occupy /tmp space and page cache) and number of uploads
        (which affect upload throughput) would help.

        """
        spec, parts = tar_partition.partition(pg_cluster_dir)

        # TODO :: Move arbitray path construction to StorageLayout Object
        backup_prefix = '{0}/basebackups_{1}/base_{file_name}_{file_offset}'\
                .format(self.layout.prefix.rstrip('/'), FILE_STRUCTURE_VERSION,
                        **start_backup_info)

        if rate_limit is None:
            per_process_limit = None
        else:
            per_process_limit = int(rate_limit / pool_size)

        # Reject tiny per-process rate limits.  They should be
        # rejected more nicely elsewhere.
        assert per_process_limit > 0 or per_process_limit is None

        total_size = 0

        # Make an attempt to upload extended version metadata
        extended_version_url = backup_prefix + '/extended_version.txt'
        logger.info(
            msg='start upload postgres version metadata',
            detail=('Uploading to {extended_version_url}.'
                    .format(extended_version_url=extended_version_url)))
        uri_put_file(self.creds,
                     extended_version_url, StringIO(version),
                     content_encoding='text/plain')

        logger.info(msg='postgres version metadata upload complete')

        uploader = PartitionUploader(self.creds, backup_prefix,
                                     per_process_limit, self.gpg_key_id)

        pool = TarUploadPool(uploader, pool_size)

        # Enqueue uploads for parallel execution
        for tpart in parts:
            total_size += tpart.total_member_size

            # 'put' can raise an exception for a just-failed upload,
            # aborting the process.
            pool.put(tpart)

        # Wait for remaining parts to upload.  An exception can be
        # raised to signal failure of the upload.
        pool.join()

        return spec, backup_prefix, total_size

    def _exception_gather_guard(self, fn):
        """
        A higher order function to trap UserExceptions and then log them.

        This is to present nicer output to the user when failures are
        occuring in another thread of execution that may not end up at
        the catch-all try/except in main().
        """

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except UserException, e:
                self.exceptions.append(e)

        return wrapper

    def _build_restore_paths(self, restore_spec):
        path_prefix = restore_spec['base_prefix']
        tblspc_prefix = os.path.join(path_prefix, 'pg_tblspc')

        if not os.path.isdir(path_prefix):
            os.mkdir(path_prefix, DEFAULT_DIR_MODE)
            os.mkdir(tblspc_prefix, DEFAULT_DIR_MODE)

        for tblspc in restore_spec['tablespaces']:
            dest = os.path.join(path_prefix,
                                restore_spec[tblspc]['link'])
            source = restore_spec[tblspc]['loc']
            if not os.path.isdir(source):
                os.mkdir(source, DEFAULT_DIR_MODE)
            os.symlink(source, dest)

    def _verify_restore_paths(self, restore_spec):
        path_prefix = restore_spec['base_prefix']
        bad_links = []
        if 'tablespaces' not in restore_spec:
            return
        for tblspc in restore_spec['tablespaces']:
            tblspc_link = os.path.join(path_prefix, 'pg_tblspc', tblspc)
            valid = os.path.islink(tblspc_link) and os.path.isdir(tblspc_link)
            if not valid:
                bad_links.append(tblspc)

        if bad_links:
            raise UserException(
                msg='Symlinks for some tablespaces not found or created.',
                detail=('Symlinks for the following tablespaces were not '
                        'found: {spaces}'.format(spaces=', '.join(bad_links))),
                hint=('Ensure all required symlinks are created prior to '
                      'running backup-fetch, or use --blind-restore to '
                      'ignore symlinking. Alternatively supply a restore '
                      'spec to have WAL-E create tablespace symlinks for you'))

########NEW FILE########
__FILENAME__ = s3_operator
from urlparse import urlparse

from wal_e.blobstore import s3
from wal_e.operator.backup import Backup


class S3Backup(Backup):
    """
    A performs S3 uploads to of PostgreSQL WAL files and clusters

    """

    def __init__(self, layout, creds, gpg_key_id):
        super(S3Backup, self).__init__(layout, creds, gpg_key_id)

        # Create a CallingInfo that will figure out region and calling
        # format issues and cache some of the determinations, if
        # necessary.
        url_tup = urlparse(layout.prefix)
        bucket_name = url_tup.netloc
        self.cinfo = s3.calling_format.from_store_name(bucket_name)
        from wal_e.worker.s3 import s3_worker
        self.worker = s3_worker

########NEW FILE########
__FILENAME__ = swift_operator
from wal_e.blobstore.swift import calling_format
from wal_e.operator.backup import Backup
from wal_e.worker.swift import swift_worker


class SwiftBackup(Backup):
    """
    Aerforms OpenStack Swift uploads of PostgreSQL WAL files and clusters
    """

    def __init__(self, layout, creds, gpg_key_id):
        super(SwiftBackup, self).__init__(layout, creds, gpg_key_id)
        self.cinfo = calling_format
        self.worker = swift_worker

########NEW FILE########
__FILENAME__ = wabs_operator
from urlparse import urlparse

from wal_e.blobstore import wabs
from wal_e.operator.backup import Backup


class WABSBackup(Backup):
    """
    A performs Windows Azure Blob Service uploads to of PostgreSQL WAL files
    and clusters

    """
    def __init__(self, layout, creds, gpg_key_id):
        super(WABSBackup, self).__init__(layout, creds, gpg_key_id)
        url_tup = urlparse(layout.prefix)
        container_name = url_tup.netloc
        self.cinfo = wabs.calling_format.from_store_name(container_name)
        from wal_e.worker.wabs import wabs_worker
        self.worker = wabs_worker

########NEW FILE########
__FILENAME__ = pipebuf
# Detailed handling of pipe buffering
#
# This module attempts to reduce the number of system calls to
# non-blocking pipes.  It does this by careful control over buffering
# and nonblocking pipe operations.

import collections
import errno
import fcntl
import gevent
import gevent.socket
import os

PIPE_BUF_BYTES = None
OS_PIPE_SZ = None


def _configure_buffer_sizes():
    """Set up module globals controlling buffer sizes"""
    global PIPE_BUF_BYTES
    global OS_PIPE_SZ

    PIPE_BUF_BYTES = 65536
    OS_PIPE_SZ = None

    # Teach the 'fcntl' module about 'F_SETPIPE_SZ', which is a Linux-ism,
    # but a good one that can drastically reduce the number of syscalls
    # when dealing with high-throughput pipes.
    if not hasattr(fcntl, 'F_SETPIPE_SZ'):
        import platform

        if platform.system() == 'Linux':
            fcntl.F_SETPIPE_SZ = 1031

    # If Linux procfs (or something that looks like it) exposes its
    # maximum F_SETPIPE_SZ, adjust the default buffer sizes.
    try:
        with open('/proc/sys/fs/pipe-max-size', 'r') as f:
            # Figure out OS pipe size, but in case it is unusually large
            # or small restrain it to sensible values.
            OS_PIPE_SZ = min(int(f.read()), 1024 * 1024)
            PIPE_BUF_BYTES = max(OS_PIPE_SZ, PIPE_BUF_BYTES)
    except:
        pass


_configure_buffer_sizes()


def set_buf_size(fd):
    """Set up os pipe buffer size, if applicable"""
    if OS_PIPE_SZ and hasattr(fcntl, 'F_SETPIPE_SZ'):
        fcntl.fcntl(fd, fcntl.F_SETPIPE_SZ, OS_PIPE_SZ)


def _setup_fd(fd):
    """Common set-up code for initializing a (pipe) file descriptor"""

    # Make the file nonblocking (but don't lose its previous flags)
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    set_buf_size(fd)


class ByteDeque(object):
    """Data structure for delayed defragmentation of submitted bytes"""
    def __init__(self):
        self._dq = collections.deque()
        self.byteSz = 0

    def add(self, b):
        self._dq.append(b)
        self.byteSz += len(b)

    def get(self, n):
        assert n <= self.byteSz, 'caller responsibility to ensure enough bytes'

        if (n == self.byteSz and len(self._dq) == 1 and
            isinstance(self._dq[0], bytes)):
            # Fast-path: if the deque has one element of the right
            # size *and* type (fragmentation can result in 'buffer'
            # objects pushed back on the deque) return it and avoid a
            # copy.
            self.byteSz = 0
            return self._dq.popleft()

        out = bytearray(n)
        remaining = n
        while remaining > 0:
            part = self._dq.popleft()
            delta = remaining - len(part)
            offset = n - remaining

            if delta == 0:
                out[offset:] = part
                remaining = 0
            elif delta > 0:
                out[offset:] = part
                remaining = delta
            elif delta < 0:
                cleave = len(part) + delta
                out[offset:] = buffer(part, 0, cleave)
                self._dq.appendleft(buffer(part, cleave))
                remaining = 0
            else:
                assert False

        self.byteSz -= n

        assert len(out) == n
        return bytes(out)

    def get_all(self):
        return self.get(self.byteSz)


class NonBlockBufferedReader(object):
    """A buffered pipe reader that adheres to the Python file protocol"""

    def __init__(self, fp):
        self._fp = fp
        self._fd = fp.fileno()
        self._bd = ByteDeque()
        self.got_eof = False

        _setup_fd(self._fd)

    def _read_chunk(self, sz):
        chunk = None
        try:
            chunk = os.read(self._fd, sz)
            self._bd.add(chunk)
        except EnvironmentError, e:
            if e.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                assert chunk is None
                gevent.socket.wait_read(self._fd)
            else:
                raise

        self.got_eof = (chunk == '')

    def read(self, size=None):
        # Handle case of "read all".
        if size is None:

            # Read everything.
            while not self.got_eof:
                self._read_chunk(PIPE_BUF_BYTES)

            # Defragment and return the contents.
            return self._bd.get_all()
        elif size > 0:
            while True:
                if self._bd.byteSz >= size:
                    # Enough bytes already buffered.
                    return self._bd.get(size)
                elif self._bd.byteSz <= size and self.got_eof:
                    # Not enough bytes buffered, but the stream is
                    # over, so return what has been gotten.
                    return self._bd.get_all()
                else:
                    # Not enough bytes buffered and stream is still
                    # open: read more bytes.
                    assert not self.got_eof

                    if size == PIPE_BUF_BYTES:
                        # Many PIPE_BUF_BYTES reads are done in WAL-E
                        # to move around data in bulk.
                        #
                        # Use that as a hint that another
                        # PIPE_BUF_BYTES-sized .read() will occur
                        # soon.  The goal is to trigger the
                        # less-copy-intensive fast-path in the
                        # ByteDeque frequently.
                        #
                        # To do that, attempt to align the read
                        # syscalls to the kernel with Python reads,
                        # even if that means issuing a shorter read
                        # than usual.
                        to_read = PIPE_BUF_BYTES - self._bd.byteSz
                        self._read_chunk(to_read)
                    else:
                        self._read_chunk(PIPE_BUF_BYTES)
        else:
            assert False

    def close(self):
        # Invalidate state.
        self._fd = -1
        del self._bd

        # Delegate close to self._fp -- it'll try to do it during its
        # destructor which is why delegation is used rather than
        # manipulation of the fd directly.
        self._fp.close()
        del self._fp

    def fileno(self):
        return self._fd

    @property
    def closed(self):
        return self._fd == -1


class NonBlockBufferedWriter(object):
    """A buffered pipe writer that adheres to the Python file protocol"""

    def __init__(self, fp):
        self._fp = fp
        self._fd = fp.fileno()
        self._bd = ByteDeque()

        _setup_fd(self._fd)

    def _partial_flush(self, max_retain):
        byts = self._bd.get_all()
        cursor = buffer(byts)

        flushed = False
        while len(cursor) > max_retain:
            try:
                n = os.write(self._fd, cursor)
                flushed = True
                cursor = buffer(cursor, n)
            except EnvironmentError, e:
                if e.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    gevent.socket.wait_write(self._fd)
                else:
                    raise

        assert self._bd.byteSz == 0
        if len(cursor) > 0:
            self._bd.add(cursor)

        return flushed

    def write(self, data):
        self._bd.add(data)

        flushed = True
        while flushed and self._bd.byteSz > PIPE_BUF_BYTES:
            # Flush down to a small amount of buffered bytes as to
            # avoid memory-copy intensive defragmentations.
            #
            # The tradeoff being made here is the price of a syscall
            # (where larger buffers are better) vs. the price of
            # copying some memory.
            flushed = self._partial_flush(65535)

    def flush(self):
        while self._bd.byteSz > 0:
            self._partial_flush(0)

    def fileno(self):
        return self._fd

    def close(self):
        # Invalidate state.
        self._fd = -1
        del self._bd

        # Delegate close to self._fp -- it'll try to do it during its
        # destructor which is why delegation is used rather than
        # manipulation of the fd directly.
        self._fp.close()
        del self._fp

    @property
    def closed(self):
        return self._fd == -1

########NEW FILE########
__FILENAME__ = pipeline
"""Primitives to manage and construct pipelines for
compression/encryption.
"""

from gevent import sleep
from wal_e import pipebuf

from wal_e.exception import UserCritical
from wal_e.piper import popen_sp, PIPE

PV_BIN = 'pv'
GPG_BIN = 'gpg'
LZOP_BIN = 'lzop'
CAT_BIN = 'cat'


def get_upload_pipeline(in_fd, out_fd, rate_limit=None,
                        gpg_key=None):
    """ Create a UNIX pipeline to process a file for uploading.
        (Compress, and optionally encrypt) """
    commands = []
    if rate_limit is not None:
        commands.append(PipeViewerRateLimitFilter(rate_limit))
    commands.append(LZOCompressionFilter())

    if gpg_key is not None:
        commands.append(GPGEncryptionFilter(gpg_key))

    return Pipeline(commands, in_fd, out_fd)


def get_download_pipeline(in_fd, out_fd, gpg=False):
    """ Create a pipeline to process a file after downloading.
        (Optionally decrypt, then decompress) """
    commands = []
    if gpg:
        commands.append(GPGDecryptionFilter())
    commands.append(LZODecompressionFilter())

    return Pipeline(commands, in_fd, out_fd)


def get_cat_pipeline(in_fd, out_fd):
    return Pipeline([CatFilter()], in_fd, out_fd)


class Pipeline(object):
    """ Represent a pipeline of commands.
        stdin and stdout are wrapped to be non-blocking. """

    def __init__(self, commands, in_fd, out_fd):
        self.commands = commands
        self.in_fd = in_fd
        self.out_fd = out_fd
        self._abort = False

    def abort(self):
        self._abort = True

    def __enter__(self):
        # Teach the first command to take input specially
        self.commands[0].stdinSet = self.in_fd
        last_command = self.commands[0]

        # Connect all interior commands to one another via stdin/stdout
        for command in self.commands[1:]:
            last_command.start()

            # Set large kernel buffering between pipeline
            # participants.
            pipebuf.set_buf_size(last_command.stdout.fileno())

            command.stdinSet = last_command.stdout
            last_command = command

        # Teach the last command to spill output to out_fd rather than to
        # its default, which is typically stdout.
        assert last_command is self.commands[-1]
        last_command.stdoutSet = self.out_fd
        last_command.start()

        stdin = self.commands[0].stdin
        if stdin is not None:
            self.stdin = pipebuf.NonBlockBufferedWriter(stdin)
        else:
            self.stdin = None

        stdout = self.commands[-1].stdout
        if stdout is not None:
            self.stdout = pipebuf.NonBlockBufferedReader(stdout)
        else:
            self.stdout = None

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if self.stdin is not None and not self.stdin.closed:
                self.stdin.flush()
                self.stdin.close()

            if exc_type is not None or self._abort:
                for command in self.commands:
                    command.wait()
            else:
                for command in self.commands:
                    command.finish()
        except:
            if exc_type:
                # Re-raise inner exception rather than complaints during
                # pipeline shutdown.
                raise exc_type, exc_value, traceback
            else:
                raise


class PipelineCommand(object):
    """A pipeline command

    Stdin and stdout are *blocking*, as tools that want to use
    non-blocking pipes will set that on their own.

    If one needs a gevent-compatible stdin/out, wrap it in
    NonBlockPipeFileWrap.
    """
    def __init__(self, command, stdin=PIPE, stdout=PIPE):
        self._command = command
        self._stdin = stdin
        self._stdout = stdout

        self._process = None

    def start(self):
        if self._process is not None:
            raise UserCritical(
                'BUG: Tried to .start on a PipelineCommand twice')

        self._process = popen_sp(self._command,
                                 stdin=self._stdin, stdout=self._stdout,
                                 close_fds=True)

    @property
    def stdin(self):
        return self._process.stdin

    @stdin.setter
    def stdinSet(self, value):
        # Use the grotesque name 'stdinSet' to suppress pyflakes.
        if self._process is not None:
            raise UserCritical(
                'BUG: Trying to set stdin on PipelineCommand '
                'after it has already been .start-ed')

        self._stdin = value

    @property
    def stdout(self):
        return self._process.stdout

    @stdout.setter
    def stdoutSet(self, value):
        # Use the grotesque name 'stdoutSet' to suppress pyflakes.
        if self._process is not None:
            raise UserCritical(
                'BUG: Trying to set stdout on PipelineCommand '
                'after it has already been .start-ed')

        self._stdout = value

    @property
    def returncode(self):
        if self._process is None:
            return None
        else:
            return self._process.returncode

    def wait(self):
        while True:
            if self._process.poll() is not None:
                break
            else:
                sleep(0.1)

        return self._process.wait()

    def finish(self):
        retcode = self.wait()

        if self.stdout is not None:
            self.stdout.close()

        if retcode != 0:
            raise UserCritical(
                msg='pipeline process did not exit gracefully',
                detail='"{0}" had terminated with the exit status {1}.'
                .format(" ".join(self._command), retcode))


class PipeViewerRateLimitFilter(PipelineCommand):
    """ Limit the rate of transfer through a pipe using pv """
    def __init__(self, rate_limit, stdin=PIPE, stdout=PIPE):
        PipelineCommand.__init__(
            self,
            [PV_BIN, '--rate-limit=' + unicode(rate_limit)], stdin, stdout)


class CatFilter(PipelineCommand):
    """Run bytes through 'cat'

    'cat' can be used to have quasi-asynchronous I/O that still allows
    for cooperative concurrency.

    """
    def __init__(self, stdin=PIPE, stdout=PIPE):
        PipelineCommand.__init__(self, [CAT_BIN], stdin, stdout)


class LZOCompressionFilter(PipelineCommand):
    """ Compress using LZO. """
    def __init__(self, stdin=PIPE, stdout=PIPE):
        PipelineCommand.__init__(
            self, [LZOP_BIN, '--stdout'], stdin, stdout)


class LZODecompressionFilter(PipelineCommand):
    """ Decompress using LZO. """
    def __init__(self, stdin=PIPE, stdout=PIPE):
        PipelineCommand.__init__(
                self, [LZOP_BIN, '-d', '--stdout', '-'], stdin, stdout)


class GPGEncryptionFilter(PipelineCommand):
    """ Encrypt using GPG, using the provided public key ID. """
    def __init__(self, key, stdin=PIPE, stdout=PIPE):
        PipelineCommand.__init__(
                self, [GPG_BIN, '-e', '-z', '0', '-r', key], stdin, stdout)


class GPGDecryptionFilter(PipelineCommand):
    """Decrypt using GPG.

    The private key must exist, and either be unpassworded, or the password
    should be present in the gpg agent.
    """
    def __init__(self, stdin=PIPE, stdout=PIPE):
        PipelineCommand.__init__(
                self, [GPG_BIN, '-d', '-q', '--batch'], stdin, stdout)

########NEW FILE########
__FILENAME__ = piper
#!/usr/bin/env python
"""
Utilities for handling subprocesses.

Mostly necessary only because of http://bugs.python.org/issue1652.

"""
import copy
import errno
import gevent
import gevent.socket
import signal

from wal_e import pipebuf
from wal_e import subprocess
from wal_e.subprocess import PIPE

# This is not used in this module, but is imported by dependent
# modules, so do this to quiet pyflakes.
assert PIPE


def subprocess_setup(f=None):
    """
    SIGPIPE reset for subprocess workaround

    Python installs a SIGPIPE handler by default. This is usually not
    what non-Python subprocesses expect.

    Calls an optional "f" first in case other code wants a preexec_fn,
    then restores SIGPIPE to what most Unix processes expect.

    http://bugs.python.org/issue1652

    """

    def wrapper(*args, **kwargs):
        if f is not None:
            f(*args, **kwargs)

        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    return wrapper


class PopenShim(object):
    def __init__(self, sleep_time=1, max_tries=None):
        self.sleep_time = sleep_time
        self.max_tries = max_tries

    def __call__(self, *args, **kwargs):
        """
        Same as subprocess.Popen, but restores SIGPIPE

        This bug is documented (See subprocess_setup) but did not make
        it to standard library.  Could also be resolved by using the
        python-subprocess32 backport and using it appropriately (See
        'restore_signals' keyword argument to Popen)
        """

        kwargs['preexec_fn'] = subprocess_setup(kwargs.get('preexec_fn'))

        # Call Popen, but be persistent in the face of ENOMEM.
        #
        # The utility of this is that on systems with overcommit off,
        # the momentary spike in committed virtual memory from fork()
        # can be large, but is cleared soon thereafter because
        # 'subprocess' uses an 'exec' system call.  Without retrying,
        # the the backup process would lose all its progress
        # immediately with no recourse, which is undesirable.
        #
        # Because the ENOMEM error happens on fork() before any
        # meaningful work can be done, one thinks this retry would be
        # safe, and without side effects.  Because fork is being
        # called through 'subprocess' and not directly here, this
        # program has to rely on the semantics of the exceptions
        # raised from 'subprocess' to avoid retries in unrelated
        # scenarios, which could be dangerous.
        tries = 0

        while True:
            try:
                proc = subprocess.Popen(*args, **kwargs)
            except OSError, e:
                if e.errno == errno.ENOMEM:
                    should_retry = (self.max_tries is not None and
                                    tries >= self.max_tries)

                    if should_retry:
                        raise

                    gevent.sleep(self.sleep_time)
                    tries += 1
                    continue

                raise
            else:
                break

        return proc

popen_sp = PopenShim()


def popen_nonblock(*args, **kwargs):
    """
    Create a process in the same way as popen_sp, but patch the file
    descriptors so they can be accessed from Python/gevent
    in a non-blocking manner.
    """

    proc = popen_sp(*args, **kwargs)

    if proc.stdin:
        proc.stdin = pipebuf.NonBlockBufferedWriter(proc.stdin)

    if proc.stdout:
        proc.stdout = pipebuf.NonBlockBufferedReader(proc.stdout)

    if proc.stderr:
        proc.stderr = pipebuf.NonBlockBufferedReader(proc.stderr)

    return proc


def pipe(*args):
    """
    Takes as parameters several dicts, each with the same
    parameters passed to popen.

    Runs the various processes in a pipeline, connecting
    the stdout of every process except the last with the
    stdin of the next process.

    Adapted from http://www.enricozini.org/2009/debian/python-pipes/

    """
    if len(args) < 2:
        raise ValueError("pipe needs at least 2 processes")

    # Set stdout=PIPE in every subprocess except the last
    for i in args[:-1]:
        i["stdout"] = subprocess.PIPE

    # Runs all subprocesses connecting stdins and stdouts to create the
    # pipeline. Closes stdouts to avoid deadlocks.
    popens = [popen_sp(**args[0])]
    for i in range(1, len(args)):
        args[i]["stdin"] = popens[i - 1].stdout
        popens.append(popen_sp(**args[i]))
        popens[i - 1].stdout.close()

    # Returns the array of subprocesses just created
    return popens


def pipe_wait(popens):
    """
    Given an array of Popen objects returned by the
    pipe method, wait for all processes to terminate
    and return the array with their return values.

    Taken from http://www.enricozini.org/2009/debian/python-pipes/

    """
    # Avoid mutating the passed copy
    popens = copy.copy(popens)
    results = [0] * len(popens)
    while popens:
        last = popens.pop(-1)
        results[len(popens)] = last.wait()
    return results

########NEW FILE########
__FILENAME__ = retries
import functools
import sys
import traceback

import gevent

from wal_e import log_help

logger = log_help.WalELogger(__name__)


def generic_exception_processor(exc_tup, **kwargs):
    logger.warning(
        msg='retrying after encountering exception',
        detail=('Exception information dump: \n{0}'
                .format(''.join(traceback.format_exception(*exc_tup)))),
        hint=('A better error message should be written to '
              'handle this exception.  Please report this output and, '
              'if possible, the situation under which it arises.'))
    del exc_tup


def retry(exception_processor=generic_exception_processor):
    """
    Generic retry decorator

    Tries to call the decorated function.  Should no exception be
    raised, the value is simply returned, otherwise, call an
    exception_processor function with the exception (type, value,
    traceback) tuple (with the intention that it could raise the
    exception without losing the traceback) and the exception
    processor's optionally usable context value (exc_processor_cxt).

    It's recommended to delete all references to the traceback passed
    to the exception_processor to speed up garbage collector via the
    'del' operator.

    This context value is passed to and returned from every invocation
    of the exception processor.  This can be used to more conveniently
    (vs. an object with __call__ defined) implement exception
    processors that have some state, such as the 'number of attempts'.
    The first invocation will pass None.

    :param f: A function to be retried.
    :type f: function

    :param exception_processor: A function to process raised
                                exceptions.
    :type exception_processor: function

    """

    def yield_new_function_from(f):
        def shim(*args, **kwargs):
            exc_processor_cxt = None

            while True:
                # Avoid livelocks while spinning on retry by yielding.
                gevent.sleep(0.1)

                try:
                    return f(*args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except:
                    exception_info_tuple = None

                    try:
                        exception_info_tuple = sys.exc_info()
                        exc_processor_cxt = exception_processor(
                            exception_info_tuple,
                            exc_processor_cxt=exc_processor_cxt)
                    finally:
                        # Although cycles are harmless long-term, help the
                        # garbage collector.
                        del exception_info_tuple
        return functools.wraps(f)(shim)
    return yield_new_function_from


def retry_with_count(side_effect_func):
    def retry_with_count_internal(exc_tup, exc_processor_cxt):
        """
        An exception processor that counts how many times it has retried

        :param exc_processor_cxt: The context counting how many times
                                  retries have been attempted.

        :type exception_cxt: integer

        :param side_effect_func: A function to perform side effects in
                                 response to the exception, such as
                                 logging.

        :type side_effect_func: function
        """
        def increment_context(exc_processor_cxt):
            return ((exc_processor_cxt is None and 1) or
                    exc_processor_cxt + 1)

        if exc_processor_cxt is None:
            exc_processor_cxt = increment_context(exc_processor_cxt)

        side_effect_func(exc_tup, exc_processor_cxt)

        return increment_context(exc_processor_cxt)

    return retry_with_count_internal

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
"""
Blob Storage Abstraction

This module is used to define and provide accessors to the logical
structure and metadata for an S3 or Windows Azure Blob Storage
backed WAL-E prefix.

"""
import collections

import wal_e.exception

from urlparse import urlparse


CURRENT_VERSION = '005'

SEGMENT_REGEXP = (r'(?P<filename>(?P<tli>[0-9A-F]{8,8})(?P<log>[0-9A-F]{8,8})'
                  '(?P<seg>[0-9A-F]{8,8}))')

SEGMENT_READY_REGEXP = SEGMENT_REGEXP + r'\.ready'

BASE_BACKUP_REGEXP = (r'base_' + SEGMENT_REGEXP + r'_(?P<offset>[0-9A-F]{8})')

COMPLETE_BASE_BACKUP_REGEXP = (
    r'base_' + SEGMENT_REGEXP +
    r'_(?P<offset>[0-9A-F]{8})_backup_stop_sentinel\.json')

VOLUME_REGEXP = (r'part_(\d+)\.tar\.lzo')


# A representation of a log number and segment, naive of timeline.
# This number always increases, even when diverging into two
# timelines, so it's useful for conservative garbage collection.
class SegmentNumber(collections.namedtuple('SegmentNumber',
                                           ['log', 'seg'])):

    @property
    def as_an_integer(self):
        assert len(self.log) == 8
        assert len(self.seg) == 8
        return int(self.log + self.seg, 16)

OBSOLETE_VERSIONS = frozenset(('004', '003', '002', '001', '000'))

SUPPORTED_STORE_SCHEMES = ('s3', 'wabs', 'swift')


# Exhaustively enumerates all possible metadata about a backup.  These
# may not always all be filled depending what access method is used to
# get information, in which case the unfilled items should be given a
# None value.  If an item was intended to be fetch, but could not be
# after some number of retries and timeouts, the field should be
# filled with the string 'timeout'.
class BackupInfo(object):
    _fields = ['name',
               'last_modified',
               'expanded_size_bytes',
               'wal_segment_backup_start',
               'wal_segment_offset_backup_start',
               'wal_segment_backup_stop',
               'wal_segment_offset_backup_stop']

    def __init__(self, **kwargs):
        for field in self._fields:
            setattr(self, field, kwargs.get(field, None))

        self.layout = kwargs['layout']
        self.spec = kwargs.get('spec', {})
        self._details_loaded = False

    def load_detail(self, conn):
        raise NotImplementedError()


class StorageLayout(object):
    """
    Encapsulates and defines S3 or Windows Azure Blob Service URL
    path manipulations for WAL-E

    S3:

    Without a trailing slash
    >>> sl = StorageLayout('s3://foo/bar')
    >>> sl.is_s3
    True
    >>> sl.basebackups()
    'bar/basebackups_005/'
    >>> sl.wal_directory()
    'bar/wal_005/'
    >>> sl.store_name()
    'foo'

    With a trailing slash
    >>> sl = StorageLayout('s3://foo/bar/')
    >>> sl.is_s3
    True
    >>> sl.basebackups()
    'bar/basebackups_005/'
    >>> sl.wal_directory()
    'bar/wal_005/'
    >>> sl.store_name()
    'foo'

    WABS:

    Without a trailing slash
    >>> sl = StorageLayout('wabs://foo/bar')
    >>> sl.is_s3
    False
    >>> sl.basebackups()
    'bar/basebackups_005/'
    >>> sl.wal_directory()
    'bar/wal_005/'
    >>> sl.store_name()
    'foo'

    With a trailing slash
    >>> sl = StorageLayout('wabs://foo/bar/')
    >>> sl.is_s3
    False
    >>> sl.basebackups()
    'bar/basebackups_005/'
    >>> sl.wal_directory()
    'bar/wal_005/'
    >>> sl.store_name()
    'foo'

    Swift:

    Without a trailing slash
    >>> sl = StorageLayout('swift://foo/bar')
    >>> sl.is_swift
    True
    >>> sl.basebackups()
    'bar/basebackups_005/'
    >>> sl.wal_directory()
    'bar/wal_005/'
    >>> sl.store_name()
    'foo'

    """

    def __init__(self, prefix, version=CURRENT_VERSION):
        self.VERSION = version

        url_tup = urlparse(prefix)

        if url_tup.scheme not in SUPPORTED_STORE_SCHEMES:
            raise wal_e.exception.UserException(
                msg='bad S3, Windows Azure Blob Storage, or OpenStack Swift '
                    'URL scheme passed',
                detail=('The scheme {0} was passed when "s3", "wabs", or '
                        '"swift" was expected.'.format(url_tup.scheme)))

        for scheme in SUPPORTED_STORE_SCHEMES:
            setattr(self, 'is_%s' % scheme, scheme == url_tup.scheme)

        self._url_tup = url_tup

        # S3 api requests absolutely cannot contain a leading slash.
        api_path_prefix = url_tup.path.lstrip('/')

        # Also canonicalize a trailing slash onto the prefix, should
        # none already exist. This only applies if we actually have a
        # prefix, i.e., our objects are not being created in the bucket's
        # root.
        if api_path_prefix and api_path_prefix[-1] != '/':
            self._api_path_prefix = api_path_prefix + '/'
            self._api_prefix = prefix + '/'
        else:
            self._api_path_prefix = api_path_prefix
            self._api_prefix = prefix

    @property
    def scheme(self):
        return self._url_tup.scheme

    @property
    def prefix(self):
        return self._api_prefix

    @property
    def path_prefix(self):
        return self._api_path_prefix

    def _error_on_unexpected_version(self):
        if self.VERSION != CURRENT_VERSION:
            raise ValueError('Backwards compatibility of this '
                             'operator is not implemented')

    def basebackups(self):
        return self._api_path_prefix + 'basebackups_' + self.VERSION + '/'

    def basebackup_directory(self, backup_info):
        self._error_on_unexpected_version()
        return (self.basebackups() +
                'base_{0}_{1}/'.format(
                backup_info.wal_segment_backup_start,
                backup_info.wal_segment_offset_backup_start))

    def basebackup_sentinel(self, backup_info):
        self._error_on_unexpected_version()
        basebackup = self.basebackup_directory(backup_info)
        # need to strip the trailing slash on the base backup dir
        # to correctly point to the sentinel
        return (basebackup.rstrip('/') + '_backup_stop_sentinel.json')

    def basebackup_tar_partition_directory(self, backup_info):
        self._error_on_unexpected_version()
        return (self.basebackup_directory(backup_info) +
                'tar_partitions/')

    def basebackup_tar_partition(self, backup_info, part_name):
        self._error_on_unexpected_version()
        return (self.basebackup_tar_partition_directory(backup_info) +
                part_name)

    def wal_directory(self):
        return self._api_path_prefix + 'wal_' + self.VERSION + '/'

    def wal_path(self, wal_file_name):
        self._error_on_unexpected_version()
        return self.wal_directory() + wal_file_name

    def store_name(self):
        """Return either the bucket name (S3) or the account name (Azure).
        """
        return self._url_tup.netloc

    def key_name(self, key):
        return key.name.lstrip('/')

    def key_last_modified(self, key):
        if hasattr(key, 'last_modified'):
            return key.last_modified
        return key.properties.last_modified


def get_backup_info(layout, **kwargs):
    kwargs['layout'] = layout
    if layout.is_s3:
        from wal_e.storage.s3_storage import S3BackupInfo
        bi = S3BackupInfo(**kwargs)
    elif layout.is_wabs:
        from wal_e.storage.wabs_storage import WABSBackupInfo
        bi = WABSBackupInfo(**kwargs)
    elif layout.is_swift:
        from wal_e.storage.swift_storage import SwiftBackupInfo
        bi = SwiftBackupInfo(**kwargs)
    return bi

########NEW FILE########
__FILENAME__ = s3_storage
import json

from wal_e.blobstore import s3
from wal_e.storage.base import BackupInfo


class S3BackupInfo(BackupInfo):

    def load_detail(self, conn):
        if self._details_loaded:
            return

        uri = "{scheme}://{bucket}/{path}".format(
            scheme=self.layout.scheme,
            bucket=self.layout.store_name(),
            path=self.layout.basebackup_sentinel(self))

        data = json.loads(s3.uri_get_file(None, uri, conn=conn))
        for k, v in data.items():
            setattr(self, k, v)

        self._details_loaded = True

########NEW FILE########
__FILENAME__ = swift_storage
import json

from wal_e.blobstore import swift
from wal_e.storage.base import BackupInfo


class SwiftBackupInfo(BackupInfo):
    def load_detail(self, conn):
        if self._details_loaded:
            return

        uri = "{scheme}://{bucket}/{path}".format(
            scheme=self.layout.scheme,
            bucket=self.layout.store_name(),
            path=self.layout.basebackup_sentinel(self))

        data = json.loads(swift.uri_get_file(None, uri, conn=conn))
        for k, v in data.items():
            setattr(self, k, v)

        self._details_loaded = True

########NEW FILE########
__FILENAME__ = wabs_storage
import json

from wal_e.storage.base import BackupInfo


class WABSBackupInfo(BackupInfo):

    def load_detail(self, conn):
        if self._details_loaded:
            return
        uri = "{scheme}://{bucket}/{path}".format(
            scheme=self.layout.scheme,
            bucket=self.layout.store_name(),
            path=self.layout.basebackup_sentinel(self))
        from wal_e.blobstore import wabs
        data = wabs.uri_get_file(None, uri, conn=conn)
        data = json.loads(data)
        for (k, v) in data.items():
            setattr(self, k, v)
        self._details_loaded = True

########NEW FILE########
__FILENAME__ = subprocess
# subprocess - Subprocesses with accessible I/O streams
#
# For more information about this module, see PEP 324.
#
# This module should remain compatible with Python 2.2, see PEP 291.
#
# Copyright (c) 2003-2005 by Peter Astrand <astrand@lysator.liu.se>
#
# Licensed to PSF under a Contributor Agreement.
# See http://www.python.org/2.4/license for licensing details.

r"""subprocess - Subprocesses with accessible I/O streams

This module allows you to spawn processes, connect to their
input/output/error pipes, and obtain their return codes.  This module
intends to replace several other, older modules and functions, like:

os.system
os.spawn*
os.popen*
popen2.*
commands.*

Information about how the subprocess module can be used to replace these
modules and functions can be found below.



Using the subprocess module
===========================
This module defines one class called Popen:

class Popen(args, bufsize=0, executable=None,
            stdin=None, stdout=None, stderr=None,
            preexec_fn=None, close_fds=False, shell=False,
            cwd=None, env=None, universal_newlines=False,
            startupinfo=None, creationflags=0):


Arguments are:

args should be a string, or a sequence of program arguments.  The
program to execute is normally the first item in the args sequence or
string, but can be explicitly set by using the executable argument.

On UNIX, with shell=False (default): In this case, the Popen class
uses os.execvp() to execute the child program.  args should normally
be a sequence.  A string will be treated as a sequence with the string
as the only item (the program to execute).

On UNIX, with shell=True: If args is a string, it specifies the
command string to execute through the shell.  If args is a sequence,
the first item specifies the command string, and any additional items
will be treated as additional shell arguments.

On Windows: the Popen class uses CreateProcess() to execute the child
program, which operates on strings.  If args is a sequence, it will be
converted to a string using the list2cmdline method.  Please note that
not all MS Windows applications interpret the command line the same
way: The list2cmdline is designed for applications using the same
rules as the MS C runtime.

bufsize, if given, has the same meaning as the corresponding argument
to the built-in open() function: 0 means unbuffered, 1 means line
buffered, any other positive value means use a buffer of
(approximately) that size.  A negative bufsize means to use the system
default, which usually means fully buffered.  The default value for
bufsize is 0 (unbuffered).

stdin, stdout and stderr specify the executed programs' standard
input, standard output and standard error file handles, respectively.
Valid values are PIPE, an existing file descriptor (a positive
integer), an existing file object, and None.  PIPE indicates that a
new pipe to the child should be created.  With None, no redirection
will occur; the child's file handles will be inherited from the
parent.  Additionally, stderr can be STDOUT, which indicates that the
stderr data from the applications should be captured into the same
file handle as for stdout.

If preexec_fn is set to a callable object, this object will be called
in the child process just before the child is executed.

If close_fds is true, all file descriptors except 0, 1 and 2 will be
closed before the child process is executed.

if shell is true, the specified command will be executed through the
shell.

If cwd is not None, the current directory will be changed to cwd
before the child is executed.

If env is not None, it defines the environment variables for the new
process.

If universal_newlines is true, the file objects stdout and stderr are
opened as a text files, but lines may be terminated by any of '\n',
the Unix end-of-line convention, '\r', the Macintosh convention or
'\r\n', the Windows convention.  All of these external representations
are seen as '\n' by the Python program.  Note: This feature is only
available if Python is built with universal newline support (the
default).  Also, the newlines attribute of the file objects stdout,
stdin and stderr are not updated by the communicate() method.

The startupinfo and creationflags, if given, will be passed to the
underlying CreateProcess() function.  They can specify things such as
appearance of the main window and priority for the new process.
(Windows only)


This module also defines some shortcut functions:

call(*popenargs, **kwargs):
    Run command with arguments.  Wait for command to complete, then
    return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])

check_call(*popenargs, **kwargs):
    Run command with arguments.  Wait for command to complete.  If the
    exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    check_call(["ls", "-l"])

check_output(*popenargs, **kwargs):
    Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    output = check_output(["ls", "-l", "/dev/null"])


Exceptions
----------
Exceptions raised in the child process, before the new program has
started to execute, will be re-raised in the parent.  Additionally,
the exception object will have one extra attribute called
'child_traceback', which is a string containing traceback information
from the childs point of view.

The most common exception raised is OSError.  This occurs, for
example, when trying to execute a non-existent file.  Applications
should prepare for OSErrors.

A ValueError will be raised if Popen is called with invalid arguments.

check_call() and check_output() will raise CalledProcessError, if the
called process returns a non-zero return code.


Security
--------
Unlike some other popen functions, this implementation will never call
/bin/sh implicitly.  This means that all characters, including shell
metacharacters, can safely be passed to child processes.


Popen objects
=============
Instances of the Popen class have the following methods:

poll()
    Check if child process has terminated.  Returns returncode
    attribute.

wait()
    Wait for child process to terminate.  Returns returncode attribute.

communicate(input=None)
    Interact with process: Send data to stdin.  Read data from stdout
    and stderr, until end-of-file is reached.  Wait for process to
    terminate.  The optional input argument should be a string to be
    sent to the child process, or None, if no data should be sent to
    the child.

    communicate() returns a tuple (stdout, stderr).

    Note: The data read is buffered in memory, so do not use this
    method if the data size is large or unlimited.

The following attributes are also available:

stdin
    If the stdin argument is PIPE, this attribute is a file object
    that provides input to the child process.  Otherwise, it is None.

stdout
    If the stdout argument is PIPE, this attribute is a file object
    that provides output from the child process.  Otherwise, it is
    None.

stderr
    If the stderr argument is PIPE, this attribute is file object that
    provides error output from the child process.  Otherwise, it is
    None.

pid
    The process ID of the child process.

returncode
    The child return code.  A None value indicates that the process
    hasn't terminated yet.  A negative value -N indicates that the
    child was terminated by signal N (UNIX only).


Replacing older functions with the subprocess module
====================================================
In this section, "a ==> b" means that b can be used as a replacement
for a.

Note: All functions in this section fail (more or less) silently if
the executed program cannot be found; this module raises an OSError
exception.

In the following examples, we assume that the subprocess module is
imported with "from subprocess import *".


Replacing /bin/sh shell backquote
---------------------------------
output=`mycmd myarg`
==>
output = Popen(["mycmd", "myarg"], stdout=PIPE).communicate()[0]


Replacing shell pipe line
-------------------------
output=`dmesg | grep hda`
==>
p1 = Popen(["dmesg"], stdout=PIPE)
p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
output = p2.communicate()[0]


Replacing os.system()
---------------------
sts = os.system("mycmd" + " myarg")
==>
p = Popen("mycmd" + " myarg", shell=True)
pid, sts = os.waitpid(p.pid, 0)

Note:

* Calling the program through the shell is usually not required.

* It's easier to look at the returncode attribute than the
  exitstatus.

A more real-world example would look like this:

try:
    retcode = call("mycmd" + " myarg", shell=True)
    if retcode < 0:
        print >>sys.stderr, "Child was terminated by signal", -retcode
    else:
        print >>sys.stderr, "Child returned", retcode
except OSError, e:
    print >>sys.stderr, "Execution failed:", e


Replacing os.spawn*
-------------------
P_NOWAIT example:

pid = os.spawnlp(os.P_NOWAIT, "/bin/mycmd", "mycmd", "myarg")
==>
pid = Popen(["/bin/mycmd", "myarg"]).pid


P_WAIT example:

retcode = os.spawnlp(os.P_WAIT, "/bin/mycmd", "mycmd", "myarg")
==>
retcode = call(["/bin/mycmd", "myarg"])


Vector example:

os.spawnvp(os.P_NOWAIT, path, args)
==>
Popen([path] + args[1:])


Environment example:

os.spawnlpe(os.P_NOWAIT, "/bin/mycmd", "mycmd", "myarg", env)
==>
Popen(["/bin/mycmd", "myarg"], env={"PATH": "/usr/bin"})


Replacing os.popen*
-------------------
pipe = os.popen("cmd", mode='r', bufsize)
==>
pipe = Popen("cmd", shell=True, bufsize=bufsize, stdout=PIPE).stdout

pipe = os.popen("cmd", mode='w', bufsize)
==>
pipe = Popen("cmd", shell=True, bufsize=bufsize, stdin=PIPE).stdin


(child_stdin, child_stdout) = os.popen2("cmd", mode, bufsize)
==>
p = Popen("cmd", shell=True, bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, close_fds=True)
(child_stdin, child_stdout) = (p.stdin, p.stdout)


(child_stdin,
 child_stdout,
 child_stderr) = os.popen3("cmd", mode, bufsize)
==>
p = Popen("cmd", shell=True, bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
(child_stdin,
 child_stdout,
 child_stderr) = (p.stdin, p.stdout, p.stderr)


(child_stdin, child_stdout_and_stderr) = os.popen4("cmd", mode,
                                                   bufsize)
==>
p = Popen("cmd", shell=True, bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
(child_stdin, child_stdout_and_stderr) = (p.stdin, p.stdout)

On Unix, os.popen2, os.popen3 and os.popen4 also accept a sequence as
the command to execute, in which case arguments will be passed
directly to the program without shell intervention.  This usage can be
replaced as follows:

(child_stdin, child_stdout) = os.popen2(["/bin/ls", "-l"], mode,
                                        bufsize)
==>
p = Popen(["/bin/ls", "-l"], bufsize=bufsize, stdin=PIPE, stdout=PIPE)
(child_stdin, child_stdout) = (p.stdin, p.stdout)

Return code handling translates as follows:

pipe = os.popen("cmd", 'w')
...
rc = pipe.close()
if rc is not None and rc % 256:
    print "There were some errors"
==>
process = Popen("cmd", 'w', shell=True, stdin=PIPE)
...
process.stdin.close()
if process.wait() != 0:
    print "There were some errors"


Replacing popen2.*
------------------
(child_stdout, child_stdin) = popen2.popen2("somestring", bufsize, mode)
==>
p = Popen(["somestring"], shell=True, bufsize=bufsize
          stdin=PIPE, stdout=PIPE, close_fds=True)
(child_stdout, child_stdin) = (p.stdout, p.stdin)

On Unix, popen2 also accepts a sequence as the command to execute, in
which case arguments will be passed directly to the program without
shell intervention.  This usage can be replaced as follows:

(child_stdout, child_stdin) = popen2.popen2(["mycmd", "myarg"], bufsize,
                                            mode)
==>
p = Popen(["mycmd", "myarg"], bufsize=bufsize,
          stdin=PIPE, stdout=PIPE, close_fds=True)
(child_stdout, child_stdin) = (p.stdout, p.stdin)

The popen2.Popen3 and popen2.Popen4 basically works as subprocess.Popen,
except that:

* subprocess.Popen raises an exception if the execution fails
* the capturestderr argument is replaced with the stderr argument.
* stdin=PIPE and stdout=PIPE must be specified.
* popen2 closes all filedescriptors by default, but you have to specify
  close_fds=True with subprocess.Popen.
"""

import sys
mswindows = (sys.platform == "win32")

import os
import types
import traceback
import gc
import signal
import errno

# Exception classes used by this module.
class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() or
    check_output() returns a non-zero exit status.
    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)


if mswindows:
    import threading
    import msvcrt
    import _subprocess
    class STARTUPINFO:
        dwFlags = 0
        hStdInput = None
        hStdOutput = None
        hStdError = None
        wShowWindow = 0
    class pywintypes:
        error = IOError
else:
    import select
    _has_poll = hasattr(select, 'poll')
    import fcntl
    import pickle

    # When select or poll has indicated that the file is writable,
    # we can write up to _PIPE_BUF bytes without risk of blocking.
    # POSIX defines PIPE_BUF as >= 512.
    _PIPE_BUF = getattr(select, 'PIPE_BUF', 512)


__all__ = ["Popen", "PIPE", "STDOUT", "call", "check_call",
           "check_output", "CalledProcessError"]

if mswindows:
    from _subprocess import (CREATE_NEW_CONSOLE, CREATE_NEW_PROCESS_GROUP,
                             STD_INPUT_HANDLE, STD_OUTPUT_HANDLE,
                             STD_ERROR_HANDLE, SW_HIDE,
                             STARTF_USESTDHANDLES, STARTF_USESHOWWINDOW)

    __all__.extend(["CREATE_NEW_CONSOLE", "CREATE_NEW_PROCESS_GROUP",
                    "STD_INPUT_HANDLE", "STD_OUTPUT_HANDLE",
                    "STD_ERROR_HANDLE", "SW_HIDE",
                    "STARTF_USESTDHANDLES", "STARTF_USESHOWWINDOW"])
try:
    MAXFD = os.sysconf("SC_OPEN_MAX")
except:
    MAXFD = 256

_active = []

def _cleanup():
    for inst in _active[:]:
        res = inst._internal_poll(_deadstate=sys.maxint)
        if res is not None:
            try:
                _active.remove(inst)
            except ValueError:
                # This can happen if two threads create a new Popen instance.
                # It's harmless that it was already removed, so ignore.
                pass

PIPE = -1
STDOUT = -2


def _eintr_retry_call(func, *args):
    while True:
        try:
            return func(*args)
        except (OSError, IOError) as e:
            if e.errno == errno.EINTR:
                continue
            raise


# XXX This function is only used by multiprocessing and the test suite,
# but it's here so that it can be imported when Python is compiled without
# threads.

def _args_from_interpreter_flags():
    """Return a list of command-line arguments reproducing the current
    settings in sys.flags and sys.warnoptions."""
    flag_opt_map = {
        'debug': 'd',
        # 'inspect': 'i',
        # 'interactive': 'i',
        'optimize': 'O',
        'dont_write_bytecode': 'B',
        'no_user_site': 's',
        'no_site': 'S',
        'ignore_environment': 'E',
        'verbose': 'v',
        'bytes_warning': 'b',
        'hash_randomization': 'R',
        'py3k_warning': '3',
    }
    args = []
    for flag, opt in flag_opt_map.items():
        v = getattr(sys.flags, flag)
        if v > 0:
            args.append('-' + opt * v)
    for opt in sys.warnoptions:
        args.append('-W' + opt)
    return args


def call(*popenargs, **kwargs):
    """Run command with arguments.  Wait for command to complete, then
    return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])
    """
    return Popen(*popenargs, **kwargs).wait()


def check_call(*popenargs, **kwargs):
    """Run command with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    check_call(["ls", "-l"])
    """
    retcode = call(*popenargs, **kwargs)
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd)
    return 0


def check_output(*popenargs, **kwargs):
    r"""Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    'crw-rw-rw- ...'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    'ls: ...'
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = Popen(stdout=PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, output=output)
    return output


def list2cmdline(seq):
    """
    Translate a sequence of arguments into a command line
    string, using the same rules as the MS C runtime:

    1) Arguments are delimited by white space, which is either a
       space or a tab.

    2) A string surrounded by double quotation marks is
       interpreted as a single argument, regardless of white space
       contained within.  A quoted string can be embedded in an
       argument.

    3) A double quotation mark preceded by a backslash is
       interpreted as a literal double quotation mark.

    4) Backslashes are interpreted literally, unless they
       immediately precede a double quotation mark.

    5) If backslashes immediately precede a double quotation mark,
       every pair of backslashes is interpreted as a literal
       backslash.  If the number of backslashes is odd, the last
       backslash escapes the next double quotation mark as
       described in rule 3.
    """

    # See
    # http://msdn.microsoft.com/en-us/library/17w5ykft.aspx
    # or search http://msdn.microsoft.com for
    # "Parsing C++ Command-Line Arguments"
    result = []
    needquote = False
    for arg in seq:
        bs_buf = []

        # Add a space to separate this argument from the others
        if result:
            result.append(' ')

        needquote = (" " in arg) or ("\t" in arg) or not arg
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backslashes.
                result.append('\\' * len(bs_buf)*2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backslashes, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')

    return ''.join(result)


class Popen(object):
    def __init__(self, args, bufsize=0, executable=None,
                 stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False,
                 cwd=None, env=None, universal_newlines=False,
                 startupinfo=None, creationflags=0):
        """Create new Popen instance."""
        _cleanup()

        self._child_created = False
        if not isinstance(bufsize, (int, long)):
            raise TypeError("bufsize must be an integer")

        if mswindows:
            if preexec_fn is not None:
                raise ValueError("preexec_fn is not supported on Windows "
                                 "platforms")
            if close_fds and (stdin is not None or stdout is not None or
                              stderr is not None):
                raise ValueError("close_fds is not supported on Windows "
                                 "platforms if you redirect stdin/stdout/stderr")
        else:
            # POSIX
            if startupinfo is not None:
                raise ValueError("startupinfo is only supported on Windows "
                                 "platforms")
            if creationflags != 0:
                raise ValueError("creationflags is only supported on Windows "
                                 "platforms")

        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.pid = None
        self.returncode = None
        self.universal_newlines = universal_newlines

        # Input and output objects. The general principle is like
        # this:
        #
        # Parent                   Child
        # ------                   -----
        # p2cwrite   ---stdin--->  p2cread
        # c2pread    <--stdout---  c2pwrite
        # errread    <--stderr---  errwrite
        #
        # On POSIX, the child objects are file descriptors.  On
        # Windows, these are Windows file handles.  The parent objects
        # are file descriptors on both platforms.  The parent objects
        # are None when not using PIPEs. The child objects are None
        # when not redirecting.

        (p2cread, p2cwrite,
         c2pread, c2pwrite,
         errread, errwrite) = self._get_handles(stdin, stdout, stderr)

        try:
            self._execute_child(args, executable, preexec_fn, close_fds,
                                cwd, env, universal_newlines,
                                startupinfo, creationflags, shell,
                                p2cread, p2cwrite,
                                c2pread, c2pwrite,
                                errread, errwrite)
        except Exception:
            # Preserve original exception in case os.close raises.
            exc_type, exc_value, exc_trace = sys.exc_info()

            to_close = []
            # Only close the pipes we created.
            if stdin == PIPE:
                to_close.extend((p2cread, p2cwrite))
            if stdout == PIPE:
                to_close.extend((c2pread, c2pwrite))
            if stderr == PIPE:
                to_close.extend((errread, errwrite))

            for fd in to_close:
                try:
                    os.close(fd)
                except EnvironmentError:
                    pass

            raise exc_type, exc_value, exc_trace

        if mswindows:
            if p2cwrite is not None:
                p2cwrite = msvcrt.open_osfhandle(p2cwrite.Detach(), 0)
            if c2pread is not None:
                c2pread = msvcrt.open_osfhandle(c2pread.Detach(), 0)
            if errread is not None:
                errread = msvcrt.open_osfhandle(errread.Detach(), 0)

        if p2cwrite is not None:
            self.stdin = os.fdopen(p2cwrite, 'wb', bufsize)
        if c2pread is not None:
            if universal_newlines:
                self.stdout = os.fdopen(c2pread, 'rU', bufsize)
            else:
                self.stdout = os.fdopen(c2pread, 'rb', bufsize)
        if errread is not None:
            if universal_newlines:
                self.stderr = os.fdopen(errread, 'rU', bufsize)
            else:
                self.stderr = os.fdopen(errread, 'rb', bufsize)


    def _translate_newlines(self, data):
        data = data.replace("\r\n", "\n")
        data = data.replace("\r", "\n")
        return data


    def __del__(self, _maxint=sys.maxint, _active=_active):
        # If __init__ hasn't had a chance to execute (e.g. if it
        # was passed an undeclared keyword argument), we don't
        # have a _child_created attribute at all.
        if not getattr(self, '_child_created', False):
            # We didn't get to successfully create a child process.
            return
        # In case the child hasn't been waited on, check if it's done.
        self._internal_poll(_deadstate=_maxint)
        if self.returncode is None and _active is not None:
            # Child is still running, keep us alive until we can wait on it.
            _active.append(self)


    def communicate(self, input=None):
        """Interact with process: Send data to stdin.  Read data from
        stdout and stderr, until end-of-file is reached.  Wait for
        process to terminate.  The optional input argument should be a
        string to be sent to the child process, or None, if no data
        should be sent to the child.

        communicate() returns a tuple (stdout, stderr)."""

        # Optimization: If we are only using one pipe, or no pipe at
        # all, using select() or threads is unnecessary.
        if [self.stdin, self.stdout, self.stderr].count(None) >= 2:
            stdout = None
            stderr = None
            if self.stdin:
                if input:
                    try:
                        self.stdin.write(input)
                    except IOError as e:
                        if e.errno != errno.EPIPE and e.errno != errno.EINVAL:
                            raise
                self.stdin.close()
            elif self.stdout:
                stdout = _eintr_retry_call(self.stdout.read)
                self.stdout.close()
            elif self.stderr:
                stderr = _eintr_retry_call(self.stderr.read)
                self.stderr.close()
            self.wait()
            return (stdout, stderr)

        return self._communicate(input)


    def poll(self):
        return self._internal_poll()


    if mswindows:
        #
        # Windows methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            if stdin is None and stdout is None and stderr is None:
                return (None, None, None, None, None, None)

            p2cread, p2cwrite = None, None
            c2pread, c2pwrite = None, None
            errread, errwrite = None, None

            if stdin is None:
                p2cread = _subprocess.GetStdHandle(_subprocess.STD_INPUT_HANDLE)
                if p2cread is None:
                    p2cread, _ = _subprocess.CreatePipe(None, 0)
            elif stdin == PIPE:
                p2cread, p2cwrite = _subprocess.CreatePipe(None, 0)
            elif isinstance(stdin, int):
                p2cread = msvcrt.get_osfhandle(stdin)
            else:
                # Assuming file-like object
                p2cread = msvcrt.get_osfhandle(stdin.fileno())
            p2cread = self._make_inheritable(p2cread)

            if stdout is None:
                c2pwrite = _subprocess.GetStdHandle(_subprocess.STD_OUTPUT_HANDLE)
                if c2pwrite is None:
                    _, c2pwrite = _subprocess.CreatePipe(None, 0)
            elif stdout == PIPE:
                c2pread, c2pwrite = _subprocess.CreatePipe(None, 0)
            elif isinstance(stdout, int):
                c2pwrite = msvcrt.get_osfhandle(stdout)
            else:
                # Assuming file-like object
                c2pwrite = msvcrt.get_osfhandle(stdout.fileno())
            c2pwrite = self._make_inheritable(c2pwrite)

            if stderr is None:
                errwrite = _subprocess.GetStdHandle(_subprocess.STD_ERROR_HANDLE)
                if errwrite is None:
                    _, errwrite = _subprocess.CreatePipe(None, 0)
            elif stderr == PIPE:
                errread, errwrite = _subprocess.CreatePipe(None, 0)
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif isinstance(stderr, int):
                errwrite = msvcrt.get_osfhandle(stderr)
            else:
                # Assuming file-like object
                errwrite = msvcrt.get_osfhandle(stderr.fileno())
            errwrite = self._make_inheritable(errwrite)

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)


        def _make_inheritable(self, handle):
            """Return a duplicate of handle, which is inheritable"""
            return _subprocess.DuplicateHandle(_subprocess.GetCurrentProcess(),
                                handle, _subprocess.GetCurrentProcess(), 0, 1,
                                _subprocess.DUPLICATE_SAME_ACCESS)


        def _find_w9xpopen(self):
            """Find and return absolut path to w9xpopen.exe"""
            w9xpopen = os.path.join(
                            os.path.dirname(_subprocess.GetModuleFileName(0)),
                                    "w9xpopen.exe")
            if not os.path.exists(w9xpopen):
                # Eeek - file-not-found - possibly an embedding
                # situation - see if we can locate it in sys.exec_prefix
                w9xpopen = os.path.join(os.path.dirname(sys.exec_prefix),
                                        "w9xpopen.exe")
                if not os.path.exists(w9xpopen):
                    raise RuntimeError("Cannot locate w9xpopen.exe, which is "
                                       "needed for Popen to work with your "
                                       "shell or platform.")
            return w9xpopen


        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Execute program (MS Windows version)"""

            if not isinstance(args, types.StringTypes):
                args = list2cmdline(args)

            # Process startup details
            if startupinfo is None:
                startupinfo = STARTUPINFO()
            if None not in (p2cread, c2pwrite, errwrite):
                startupinfo.dwFlags |= _subprocess.STARTF_USESTDHANDLES
                startupinfo.hStdInput = p2cread
                startupinfo.hStdOutput = c2pwrite
                startupinfo.hStdError = errwrite

            if shell:
                startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = _subprocess.SW_HIDE
                comspec = os.environ.get("COMSPEC", "cmd.exe")
                args = '{} /c "{}"'.format (comspec, args)
                if (_subprocess.GetVersion() >= 0x80000000 or
                        os.path.basename(comspec).lower() == "command.com"):
                    # Win9x, or using command.com on NT. We need to
                    # use the w9xpopen intermediate program. For more
                    # information, see KB Q150956
                    # (http://web.archive.org/web/20011105084002/http://support.microsoft.com/support/kb/articles/Q150/9/56.asp)
                    w9xpopen = self._find_w9xpopen()
                    args = '"%s" %s' % (w9xpopen, args)
                    # Not passing CREATE_NEW_CONSOLE has been known to
                    # cause random failures on win9x.  Specifically a
                    # dialog: "Your program accessed mem currently in
                    # use at xxx" and a hopeful warning about the
                    # stability of your system.  Cost is Ctrl+C wont
                    # kill children.
                    creationflags |= _subprocess.CREATE_NEW_CONSOLE

            # Start the process
            try:
                hp, ht, pid, tid = _subprocess.CreateProcess(executable, args,
                                         # no special security
                                         None, None,
                                         int(not close_fds),
                                         creationflags,
                                         env,
                                         cwd,
                                         startupinfo)
            except pywintypes.error, e:
                # Translate pywintypes.error to WindowsError, which is
                # a subclass of OSError.  FIXME: We should really
                # translate errno using _sys_errlist (or similar), but
                # how can this be done from Python?
                raise WindowsError(*e.args)
            finally:
                # Child is launched. Close the parent's copy of those pipe
                # handles that only the child should have open.  You need
                # to make sure that no handles to the write end of the
                # output pipe are maintained in this process or else the
                # pipe will not close when the child process exits and the
                # ReadFile will hang.
                if p2cread is not None:
                    p2cread.Close()
                if c2pwrite is not None:
                    c2pwrite.Close()
                if errwrite is not None:
                    errwrite.Close()

            # Retain the process handle, but close the thread handle
            self._child_created = True
            self._handle = hp
            self.pid = pid
            ht.Close()

        def _internal_poll(self, _deadstate=None,
                _WaitForSingleObject=_subprocess.WaitForSingleObject,
                _WAIT_OBJECT_0=_subprocess.WAIT_OBJECT_0,
                _GetExitCodeProcess=_subprocess.GetExitCodeProcess):
            """Check if child process has terminated.  Returns returncode
            attribute.

            This method is called by __del__, so it can only refer to objects
            in its local scope.

            """
            if self.returncode is None:
                if _WaitForSingleObject(self._handle, 0) == _WAIT_OBJECT_0:
                    self.returncode = _GetExitCodeProcess(self._handle)
            return self.returncode


        def wait(self):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            if self.returncode is None:
                _subprocess.WaitForSingleObject(self._handle,
                                                _subprocess.INFINITE)
                self.returncode = _subprocess.GetExitCodeProcess(self._handle)
            return self.returncode


        def _readerthread(self, fh, buffer):
            buffer.append(fh.read())


        def _communicate(self, input):
            stdout = None # Return
            stderr = None # Return

            if self.stdout:
                stdout = []
                stdout_thread = threading.Thread(target=self._readerthread,
                                                 args=(self.stdout, stdout))
                stdout_thread.setDaemon(True)
                stdout_thread.start()
            if self.stderr:
                stderr = []
                stderr_thread = threading.Thread(target=self._readerthread,
                                                 args=(self.stderr, stderr))
                stderr_thread.setDaemon(True)
                stderr_thread.start()

            if self.stdin:
                if input is not None:
                    try:
                        self.stdin.write(input)
                    except IOError as e:
                        if e.errno != errno.EPIPE:
                            raise
                self.stdin.close()

            if self.stdout:
                stdout_thread.join()
            if self.stderr:
                stderr_thread.join()

            # All data exchanged.  Translate lists into strings.
            if stdout is not None:
                stdout = stdout[0]
            if stderr is not None:
                stderr = stderr[0]

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(file, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)

        def send_signal(self, sig):
            """Send a signal to the process
            """
            if sig == signal.SIGTERM:
                self.terminate()
            elif sig == signal.CTRL_C_EVENT:
                os.kill(self.pid, signal.CTRL_C_EVENT)
            elif sig == signal.CTRL_BREAK_EVENT:
                os.kill(self.pid, signal.CTRL_BREAK_EVENT)
            else:
                raise ValueError("Unsupported signal: {}".format(sig))

        def terminate(self):
            """Terminates the process
            """
            try:
                _subprocess.TerminateProcess(self._handle, 1)
            except OSError as e:
                # ERROR_ACCESS_DENIED (winerror 5) is received when the
                # process already died.
                if e.winerror != 5:
                    raise
                rc = _subprocess.GetExitCodeProcess(self._handle)
                if rc == _subprocess.STILL_ACTIVE:
                    raise
                self.returncode = rc

        kill = terminate

    else:
        #
        # POSIX methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            p2cread, p2cwrite = None, None
            c2pread, c2pwrite = None, None
            errread, errwrite = None, None

            if stdin is None:
                pass
            elif stdin == PIPE:
                p2cread, p2cwrite = self.pipe_cloexec()
            elif isinstance(stdin, int):
                p2cread = stdin
            else:
                # Assuming file-like object
                p2cread = stdin.fileno()

            if stdout is None:
                pass
            elif stdout == PIPE:
                c2pread, c2pwrite = self.pipe_cloexec()
            elif isinstance(stdout, int):
                c2pwrite = stdout
            else:
                # Assuming file-like object
                c2pwrite = stdout.fileno()

            if stderr is None:
                pass
            elif stderr == PIPE:
                errread, errwrite = self.pipe_cloexec()
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif isinstance(stderr, int):
                errwrite = stderr
            else:
                # Assuming file-like object
                errwrite = stderr.fileno()

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)


        def _set_cloexec_flag(self, fd, cloexec=True):
            try:
                cloexec_flag = fcntl.FD_CLOEXEC
            except AttributeError:
                cloexec_flag = 1

            old = fcntl.fcntl(fd, fcntl.F_GETFD)
            if cloexec:
                fcntl.fcntl(fd, fcntl.F_SETFD, old | cloexec_flag)
            else:
                fcntl.fcntl(fd, fcntl.F_SETFD, old & ~cloexec_flag)


        def pipe_cloexec(self):
            """Create a pipe with FDs set CLOEXEC."""
            # Pipes' FDs are set CLOEXEC by default because we don't want them
            # to be inherited by other subprocesses: the CLOEXEC flag is removed
            # from the child's FDs by _dup2(), between fork() and exec().
            # This is not atomic: we would need the pipe2() syscall for that.
            r, w = os.pipe()
            self._set_cloexec_flag(r)
            self._set_cloexec_flag(w)
            return r, w


        def _close_fds(self, but):
            if hasattr(os, 'closerange'):
                os.closerange(3, but)
                os.closerange(but + 1, MAXFD)
            else:
                for i in xrange(3, MAXFD):
                    if i == but:
                        continue
                    try:
                        os.close(i)
                    except:
                        pass


        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Execute program (POSIX version)"""

            if isinstance(args, types.StringTypes):
                args = [args]
            else:
                args = list(args)

            if shell:
                args = ["/bin/sh", "-c"] + args
                if executable:
                    args[0] = executable

            if executable is None:
                executable = args[0]

            # For transferring possible exec failure from child to parent
            # The first char specifies the exception type: 0 means
            # OSError, 1 means some other error.
            errpipe_read, errpipe_write = self.pipe_cloexec()
            try:
                try:
                    gc_was_enabled = gc.isenabled()
                    # Disable gc to avoid bug where gc -> file_dealloc ->
                    # write to stderr -> hang.  http://bugs.python.org/issue1336
                    gc.disable()
                    try:
                        self.pid = os.fork()
                    except:
                        if gc_was_enabled:
                            gc.enable()
                        raise
                    self._child_created = True
                    if self.pid == 0:
                        # Child
                        try:
                            # Close parent's pipe ends
                            if p2cwrite is not None:
                                os.close(p2cwrite)
                            if c2pread is not None:
                                os.close(c2pread)
                            if errread is not None:
                                os.close(errread)
                            os.close(errpipe_read)

                            # When duping fds, if there arises a situation
                            # where one of the fds is either 0, 1 or 2, it
                            # is possible that it is overwritten (#12607).
                            if c2pwrite == 0:
                                c2pwrite = os.dup(c2pwrite)
                            if errwrite == 0 or errwrite == 1:
                                errwrite = os.dup(errwrite)

                            # Dup fds for child
                            def _dup2(a, b):
                                # dup2() removes the CLOEXEC flag but
                                # we must do it ourselves if dup2()
                                # would be a no-op (issue #10806).
                                if a == b:
                                    self._set_cloexec_flag(a, False)
                                elif a is not None:
                                    os.dup2(a, b)
                            _dup2(p2cread, 0)
                            _dup2(c2pwrite, 1)
                            _dup2(errwrite, 2)

                            # Close pipe fds.  Make sure we don't close the
                            # same fd more than once, or standard fds.
                            closed = set([None])
                            for fd in [p2cread, c2pwrite, errwrite]:
                                if fd not in closed and fd > 2:
                                    os.close(fd)
                                    closed.add(fd)

                            # Close all other fds, if asked for
                            if close_fds:
                                self._close_fds(but=errpipe_write)

                            if cwd is not None:
                                os.chdir(cwd)

                            if preexec_fn:
                                preexec_fn()

                            if env is None:
                                os.execvp(executable, args)
                            else:
                                os.execvpe(executable, args, env)

                        except:
                            exc_type, exc_value, tb = sys.exc_info()
                            # Save the traceback and attach it to the exception object
                            exc_lines = traceback.format_exception(exc_type,
                                                                   exc_value,
                                                                   tb)
                            exc_value.child_traceback = ''.join(exc_lines)
                            os.write(errpipe_write, pickle.dumps(exc_value))

                        # This exitcode won't be reported to applications, so it
                        # really doesn't matter what we return.
                        os._exit(255)

                    # Parent
                    if gc_was_enabled:
                        gc.enable()
                finally:
                    # be sure the FD is closed no matter what
                    os.close(errpipe_write)

                if p2cread is not None and p2cwrite is not None:
                    os.close(p2cread)
                if c2pwrite is not None and c2pread is not None:
                    os.close(c2pwrite)
                if errwrite is not None and errread is not None:
                    os.close(errwrite)

                # Wait for exec to fail or succeed; possibly raising exception
                # Exception limited to 1M
                data = _eintr_retry_call(os.read, errpipe_read, 1048576)
            finally:
                # be sure the FD is closed no matter what
                os.close(errpipe_read)

            if data != "":
                try:
                    _eintr_retry_call(os.waitpid, self.pid, 0)
                except OSError as e:
                    if e.errno != errno.ECHILD:
                        raise
                child_exception = pickle.loads(data)
                raise child_exception


        def _handle_exitstatus(self, sts, _WIFSIGNALED=os.WIFSIGNALED,
                _WTERMSIG=os.WTERMSIG, _WIFEXITED=os.WIFEXITED,
                _WEXITSTATUS=os.WEXITSTATUS):
            # This method is called (indirectly) by __del__, so it cannot
            # refer to anything outside of its local scope."""
            if _WIFSIGNALED(sts):
                self.returncode = -_WTERMSIG(sts)
            elif _WIFEXITED(sts):
                self.returncode = _WEXITSTATUS(sts)
            else:
                # Should never happen
                raise RuntimeError("Unknown child exit status!")


        def _internal_poll(self, _deadstate=None, _waitpid=os.waitpid,
                _WNOHANG=os.WNOHANG, _os_error=os.error, _ECHILD=errno.ECHILD):
            """Check if child process has terminated.  Returns returncode
            attribute.

            This method is called by __del__, so it cannot reference anything
            outside of the local scope (nor can any methods it calls).

            """
            if self.returncode is None:
                try:
                    pid, sts = _waitpid(self.pid, _WNOHANG)
                    if pid == self.pid:
                        self._handle_exitstatus(sts)
                except _os_error as e:
                    if _deadstate is not None:
                        self.returncode = _deadstate
                    if e.errno == _ECHILD:
                        # This happens if SIGCLD is set to be ignored or
                        # waiting for child processes has otherwise been
                        # disabled for our process.  This child is dead, we
                        # can't get the status.
                        # http://bugs.python.org/issue15756
                        self.returncode = 0
            return self.returncode


        def wait(self):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            while self.returncode is None:
                try:
                    pid, sts = _eintr_retry_call(os.waitpid, self.pid, 0)
                except OSError as e:
                    if e.errno != errno.ECHILD:
                        raise
                    # This happens if SIGCLD is set to be ignored or waiting
                    # for child processes has otherwise been disabled for our
                    # process.  This child is dead, we can't get the status.
                    pid = self.pid
                    sts = 0
                # Check the pid and loop as waitpid has been known to return
                # 0 even without WNOHANG in odd situations.  issue14396.
                if pid == self.pid:
                    self._handle_exitstatus(sts)
            return self.returncode


        def _communicate(self, input):
            if self.stdin:
                # Flush stdio buffer.  This might block, if the user has
                # been writing to .stdin in an uncontrolled fashion.
                self.stdin.flush()
                if not input:
                    self.stdin.close()

            if _has_poll:
                stdout, stderr = self._communicate_with_poll(input)
            else:
                stdout, stderr = self._communicate_with_select(input)

            # All data exchanged.  Translate lists into strings.
            if stdout is not None:
                stdout = ''.join(stdout)
            if stderr is not None:
                stderr = ''.join(stderr)

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(file, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)


        def _communicate_with_poll(self, input):
            stdout = None # Return
            stderr = None # Return
            fd2file = {}
            fd2output = {}

            poller = select.poll()
            def register_and_append(file_obj, eventmask):
                poller.register(file_obj.fileno(), eventmask)
                fd2file[file_obj.fileno()] = file_obj

            def close_unregister_and_remove(fd):
                poller.unregister(fd)
                fd2file[fd].close()
                fd2file.pop(fd)

            if self.stdin and input:
                register_and_append(self.stdin, select.POLLOUT)

            select_POLLIN_POLLPRI = select.POLLIN | select.POLLPRI
            if self.stdout:
                register_and_append(self.stdout, select_POLLIN_POLLPRI)
                fd2output[self.stdout.fileno()] = stdout = []
            if self.stderr:
                register_and_append(self.stderr, select_POLLIN_POLLPRI)
                fd2output[self.stderr.fileno()] = stderr = []

            input_offset = 0
            while fd2file:
                try:
                    ready = poller.poll()
                except select.error, e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise

                for fd, mode in ready:
                    if mode & select.POLLOUT:
                        chunk = input[input_offset : input_offset + _PIPE_BUF]
                        try:
                            input_offset += os.write(fd, chunk)
                        except OSError as e:
                            if e.errno == errno.EPIPE:
                                close_unregister_and_remove(fd)
                            else:
                                raise
                        else:
                            if input_offset >= len(input):
                                close_unregister_and_remove(fd)
                    elif mode & select_POLLIN_POLLPRI:
                        data = os.read(fd, 4096)
                        if not data:
                            close_unregister_and_remove(fd)
                        fd2output[fd].append(data)
                    else:
                        # Ignore hang up or errors.
                        close_unregister_and_remove(fd)

            return (stdout, stderr)


        def _communicate_with_select(self, input):
            read_set = []
            write_set = []
            stdout = None # Return
            stderr = None # Return

            if self.stdin and input:
                write_set.append(self.stdin)
            if self.stdout:
                read_set.append(self.stdout)
                stdout = []
            if self.stderr:
                read_set.append(self.stderr)
                stderr = []

            input_offset = 0
            while read_set or write_set:
                try:
                    rlist, wlist, xlist = select.select(read_set, write_set, [])
                except select.error, e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise

                if self.stdin in wlist:
                    chunk = input[input_offset : input_offset + _PIPE_BUF]
                    try:
                        bytes_written = os.write(self.stdin.fileno(), chunk)
                    except OSError as e:
                        if e.errno == errno.EPIPE:
                            self.stdin.close()
                            write_set.remove(self.stdin)
                        else:
                            raise
                    else:
                        input_offset += bytes_written
                        if input_offset >= len(input):
                            self.stdin.close()
                            write_set.remove(self.stdin)

                if self.stdout in rlist:
                    data = os.read(self.stdout.fileno(), 1024)
                    if data == "":
                        self.stdout.close()
                        read_set.remove(self.stdout)
                    stdout.append(data)

                if self.stderr in rlist:
                    data = os.read(self.stderr.fileno(), 1024)
                    if data == "":
                        self.stderr.close()
                        read_set.remove(self.stderr)
                    stderr.append(data)

            return (stdout, stderr)


        def send_signal(self, sig):
            """Send a signal to the process
            """
            os.kill(self.pid, sig)

        def terminate(self):
            """Terminate the process with SIGTERM
            """
            self.send_signal(signal.SIGTERM)

        def kill(self):
            """Kill the process with SIGKILL
            """
            self.send_signal(signal.SIGKILL)


def _demo_posix():
    #
    # Example 1: Simple redirection: Get process list
    #
    plist = Popen(["ps"], stdout=PIPE).communicate()[0]
    print "Process list:"
    print plist

    #
    # Example 2: Change uid before executing child
    #
    if os.getuid() == 0:
        p = Popen(["id"], preexec_fn=lambda: os.setuid(100))
        p.wait()

    #
    # Example 3: Connecting several subprocesses
    #
    print "Looking for 'hda'..."
    p1 = Popen(["dmesg"], stdout=PIPE)
    p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
    print repr(p2.communicate()[0])

    #
    # Example 4: Catch execution error
    #
    print
    print "Trying a weird file..."
    try:
        print Popen(["/this/path/does/not/exist"]).communicate()
    except OSError, e:
        if e.errno == errno.ENOENT:
            print "The file didn't exist.  I thought so..."
            print "Child traceback:"
            print e.child_traceback
        else:
            print "Error", e.errno
    else:
        print >>sys.stderr, "Gosh.  No error."


def _demo_windows():
    #
    # Example 1: Connecting several subprocesses
    #
    print "Looking for 'PROMPT' in set output..."
    p1 = Popen("set", stdout=PIPE, shell=True)
    p2 = Popen('find "PROMPT"', stdin=p1.stdout, stdout=PIPE)
    print repr(p2.communicate()[0])

    #
    # Example 2: Simple execution of program
    #
    print "Executing calc..."
    p = Popen("calc")
    p.wait()


if __name__ == "__main__":
    if mswindows:
        _demo_windows()
    else:
        _demo_posix()

########NEW FILE########
__FILENAME__ = tar_partition
#!/usr/bin/env python
"""
Converting a file tree into partitioned, space-controlled TAR files.

This module attempts to address the following problems:

* Storing individual small files can be very time consuming because of
  per-file overhead.

* It is desirable to maintain UNIX metadata on a file, and that's not
  always possible without boxing the file in another format, such as
  TAR.

* Because multiple connections can allow for better throughput,
  partitioned TAR files can be parallelized for download while being
  pipelined for extraction and decompression, all to the same base
  tree.

* Ensuring that partitions are of a predictable size: the size to be
  added is bounded, as sizes must be passed up-front.  It is assumed
  that if the dataset is "hot" that supplementary write-ahead-logs
  should exist to bring the data to a consistent state.

* Representation of empty directories and symbolic links.

* Avoiding volumes with "too many" individual members to avoid
  consuming too much memory with metadata.

The *approximate* maximum size of a volume is tunable.  If any archive
members are too large, a TarMemberTooBig exception is raised: in this
case, it is necessary to raise the partition size.  The volume size
does *not* include Tar metadata overhead, and this is why one cannot
rely on an exact maximum (without More Programming).

Why not GNU Tar with its multi-volume functionality: it's relatively
difficult to limit the size of an archive member (a problem for fast
growing files that are also being WAL-logged), and GNU Tar uses
interactive prompts to ask for the right tar file to continue the next
extraction.  This coupling between tarfiles makes the extraction
process considerably more complicated.

"""
import collections
import errno
import os
import tarfile

from wal_e import log_help
from wal_e import copyfileobj
from wal_e import pipebuf
from wal_e import pipeline
from wal_e.exception import UserException

logger = log_help.WalELogger(__name__)

PG_CONF = ('postgresql.conf',
           'pg_hba.conf',
           'recovery.conf',
           'pg_ident.conf')


class StreamPadFileObj(object):
    """
    Layer on a file to provide a precise stream byte length

    This file-like-object accepts an underlying file-like-object and a
    target size.  Once the target size is reached, no more bytes will
    be returned.  Furthermore, if the underlying stream runs out of
    bytes, '\0' will be returned until the target size is reached.

    """

    # Try to save space via __slots__ optimization: many of these can
    # be created on systems with many small files that are packed into
    # a tar partition, and memory blows up when instantiating the
    # tarfile instance full of these.
    __slots__ = ('underlying_fp', 'target_size', 'pos')

    def __init__(self, underlying_fp, target_size):
        self.underlying_fp = underlying_fp
        self.target_size = target_size
        self.pos = 0

    def read(self, size):
        max_readable = min(self.target_size - self.pos, size)
        ret = self.underlying_fp.read(max_readable)
        lenret = len(ret)
        self.pos += lenret
        return ret + '\0' * (max_readable - lenret)

    def close(self):
        return self.underlying_fp.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class TarMemberTooBigError(UserException):
    def __init__(self, member_name, limited_to, requested, *args, **kwargs):
        self.member_name = member_name
        self.max_size = limited_to
        self.requested = requested

        msg = 'Attempted to archive a file that is too large.'
        hint = ('There is a file in the postgres database directory that '
                'is larger than %d bytes. If no such file exists, please '
                'report this as a bug. In particular, check %s, which appears '
                'to be %d bytes.') % (limited_to, member_name, requested)
        UserException.__init__(self, msg=msg, hint=hint, *args, **kwargs)


class TarBadRootError(Exception):
    def __init__(self, root, *args, **kwargs):
        self.root = root
        Exception.__init__(self, *args, **kwargs)


class TarBadPathError(Exception):
    """
    Raised when a root directory does not contain all file paths.

    """

    def __init__(self, root, offensive_path, *args, **kwargs):
        self.root = root
        self.offensive_path = offensive_path

        Exception.__init__(self, *args, **kwargs)

ExtendedTarInfo = collections.namedtuple('ExtendedTarInfo',
                                         'submitted_path tarinfo')

# 1.5 GiB is 1610612736 bytes, and Postgres allocates 1 GiB files as a
# nominal maximum.  This must be greater than that.
PARTITION_MAX_SZ = 1610612736

# Maximum number of members in a TarPartition segment.
#
# This is to restrain memory consumption when segmenting the
# partitions.  Some workloads can produce many tiny files, so it's
# important to try to choose some happy medium between avoiding
# excessive bloat in the number of partitions and making the wal-e
# process effectively un-fork()-able for performing any useful work.
#
# 262144 is 256 KiB.
PARTITION_MAX_MEMBERS = int(PARTITION_MAX_SZ / 262144)


def _fsync_files(filenames):
    """Call fsync() a list of file names

    The filenames should be absolute paths already.

    """
    touched_directories = set()

    mode = os.O_RDONLY

    # Windows
    if hasattr(os, 'O_BINARY'):
        mode |= os.O_BINARY

    for filename in filenames:
        fd = os.open(filename, mode)
        os.fsync(fd)
        os.close(fd)
        touched_directories.add(os.path.dirname(filename))

    # Some OSes also require us to fsync the directory where we've
    # created files or subdirectories.
    if hasattr(os, 'O_DIRECTORY'):
        for dirname in touched_directories:
            fd = os.open(dirname, os.O_RDONLY | os.O_DIRECTORY)
            os.fsync(fd)
            os.close(fd)


def cat_extract(tar, member, targetpath):
    """Extract a regular file member using cat for async-like I/O

    Mostly adapted from tarfile.py.

    """
    assert member.isreg()

    # Fetch the TarInfo object for the given name and build the
    # destination pathname, replacing forward slashes to platform
    # specific separators.
    targetpath = targetpath.rstrip("/")
    targetpath = targetpath.replace("/", os.sep)

    # Create all upper directories.
    upperdirs = os.path.dirname(targetpath)
    if upperdirs and not os.path.exists(upperdirs):
        try:
            # Create directories that are not part of the archive with
            # default permissions.
            os.makedirs(upperdirs)
        except EnvironmentError as e:
            if e.errno == errno.EEXIST:
                # Ignore an error caused by the race of
                # the directory being created between the
                # check for the path and the creation.
                pass
            else:
                raise

    with open(targetpath, 'wb') as dest:
        with pipeline.get_cat_pipeline(pipeline.PIPE, dest) as pl:
            fp = tar.extractfile(member)
            copyfileobj.copyfileobj(fp, pl.stdin)

    tar.chown(member, targetpath)
    tar.chmod(member, targetpath)
    tar.utime(member, targetpath)


class TarPartition(list):

    def __init__(self, name, *args, **kwargs):
        self.name = name
        list.__init__(self, *args, **kwargs)

    @staticmethod
    def _padded_tar_add(tar, et_info):
        try:
            with open(et_info.submitted_path, 'rb') as raw_file:
                with StreamPadFileObj(raw_file,
                                      et_info.tarinfo.size) as f:
                    tar.addfile(et_info.tarinfo, f)

        except EnvironmentError, e:
            if (e.errno == errno.ENOENT and
                e.filename == et_info.submitted_path):
                # log a NOTICE/INFO that the file was unlinked.
                # Ostensibly harmless (such unlinks should be replayed
                # in the WAL) but good to know.
                logger.debug(
                    msg='tar member additions skipping an unlinked file',
                    detail='Skipping {0}.'.format(et_info.submitted_path))
            else:
                raise

    @staticmethod
    def tarfile_extract(fileobj, dest_path):
        """Extract a tarfile described by a file object to a specified path.

        Args:
            fileobj (file): File object wrapping the target tarfile.
            dest_path (str): Path to extract the contents of the tarfile to.
        """
        # Though this method doesn't fit cleanly into the TarPartition object,
        # tarballs are only ever extracted for partitions so the logic jives
        # for the most part.
        tar = tarfile.open(mode='r|', fileobj=fileobj,
                           bufsize=pipebuf.PIPE_BUF_BYTES)

        # canonicalize dest_path so the prefix check below works
        dest_path = os.path.realpath(dest_path)

        # list of files that need fsyncing
        extracted_files = []

        # Iterate through each member of the tarfile individually. We must
        # approach it this way because we are dealing with a pipe and the
        # getmembers() method will consume it before we extract any data.
        for member in tar:
            assert not member.name.startswith('/')
            relpath = os.path.join(dest_path, member.name)

            if member.isreg() and member.size >= pipebuf.PIPE_BUF_BYTES:
                cat_extract(tar, member, relpath)
            else:
                tar.extract(member, path=dest_path)

            if member.issym():
                # It does not appear possible to fsync a symlink, or
                # so it seems, as there is no portable way to open()
                # one to get a fd to run fsync on.
                pass
            else:
                filename = os.path.realpath(relpath)
                extracted_files.append(filename)

            # avoid accumulating an unbounded list of strings which
            # could be quite large for a large database
            if len(extracted_files) > 1000:
                _fsync_files(extracted_files)
                del extracted_files[:]
        tar.close()
        _fsync_files(extracted_files)

    def tarfile_write(self, fileobj):
        tar = None
        try:
            tar = tarfile.open(fileobj=fileobj, mode='w|',
                               bufsize=pipebuf.PIPE_BUF_BYTES)

            for et_info in self:
                # Treat files specially because they may grow, shrink,
                # or may be unlinked in the meanwhile.
                if et_info.tarinfo.isfile():
                    self._padded_tar_add(tar, et_info)
                else:
                    tar.addfile(et_info.tarinfo)
        finally:
            if tar is not None:
                tar.close()

    @property
    def total_member_size(self):
        """
        Compute the sum of the size of expanded TAR member

        Expressed in bytes.

        """
        return sum(et_info.tarinfo.size for et_info in self)

    def format_manifest(self):
        parts = []
        for tpart in self:
            for et_info in tpart:
                tarinfo = et_info.tarinfo
                parts.append('\t'.join([tarinfo.name, tarinfo.size]))

        return '\n'.join(parts)


def _segmentation_guts(root, file_paths, max_partition_size):
    """Segment a series of file paths into TarPartition values

    These TarPartitions are disjoint and roughly below the prescribed
    size.
    """
    # Canonicalize root to include the trailing slash, since root is
    # intended to be a directory anyway.
    if not root.endswith(os.path.sep):
        root += os.path.sep
    # Ensure that the root path is a directory before continuing.
    if not os.path.isdir(root):
        raise TarBadRootError(root=root)

    bogus_tar = None

    try:
        # Create a bogus TarFile as a contrivance to be able to run
        # gettarinfo and produce such instances.  Some of the settings
        # on the TarFile are important, like whether to de-reference
        # symlinks.
        bogus_tar = tarfile.TarFile(os.devnull, 'w', dereference=False)

        # Bookkeeping for segmentation of tar members into partitions.
        partition_number = 0
        partition_bytes = 0
        partition_members = 0
        partition = TarPartition(partition_number)

        for file_path in file_paths:

            # Ensure tar members exist within a shared root before
            # continuing.
            if not file_path.startswith(root):
                raise TarBadPathError(root=root, offensive_path=file_path)

            # Create an ExtendedTarInfo to represent the tarfile.
            try:
                et_info = ExtendedTarInfo(
                    tarinfo=bogus_tar.gettarinfo(
                        file_path, arcname=file_path[len(root):]),
                    submitted_path=file_path)

            except EnvironmentError, e:
                if (e.errno == errno.ENOENT and
                    e.filename == file_path):
                    # log a NOTICE/INFO that the file was unlinked.
                    # Ostensibly harmless (such unlinks should be replayed
                    # in the WAL) but good to know.
                    logger.debug(
                        msg='tar member additions skipping an unlinked file',
                        detail='Skipping {0}.'.format(et_info.submitted_path))
                else:
                    raise

            # Ensure tar members are within an expected size before
            # continuing.
            if et_info.tarinfo.size > max_partition_size:
                raise TarMemberTooBigError(
                    et_info.tarinfo.name, max_partition_size,
                    et_info.tarinfo.size)

            if (partition_bytes + et_info.tarinfo.size >= max_partition_size
                or partition_members >= PARTITION_MAX_MEMBERS):
                # Partition is full and cannot accept another member,
                # so yield the complete one to the caller.
                yield partition

                # Prepare a fresh partition to accrue additional file
                # paths into.
                partition_number += 1
                partition_bytes = et_info.tarinfo.size
                partition_members = 1
                partition = TarPartition(
                    partition_number, [et_info])
            else:
                # Partition is able to accept this member, so just add
                # it and increment the size counters.
                partition_bytes += et_info.tarinfo.size
                partition_members += 1
                partition.append(et_info)

                # Partition size overflow must not to be possible
                # here.
                assert partition_bytes < max_partition_size

    finally:
        if bogus_tar is not None:
            bogus_tar.close()

    # Flush out the final partition should it be non-empty.
    if partition:
        yield partition


def partition(pg_cluster_dir):
    def raise_walk_error(e):
        raise e
    if not pg_cluster_dir.endswith(os.path.sep):
        pg_cluster_dir += os.path.sep

    # Accumulates a list of archived files while walking the file
    # system.
    matches = []
    # Maintain a manifest of archived files. Tra
    spec = {'base_prefix': pg_cluster_dir,
            'tablespaces': []}

    walker = os.walk(pg_cluster_dir, onerror=raise_walk_error)
    for root, dirnames, filenames in walker:
        is_cluster_toplevel = (os.path.abspath(root) ==
                               os.path.abspath(pg_cluster_dir))
        # Do not capture any WAL files, although we do want to
        # capture the WAL directory or symlink
        if is_cluster_toplevel and 'pg_xlog' in dirnames:
            if 'pg_xlog' in dirnames:
                dirnames.remove('pg_xlog')
                matches.append(os.path.join(root, 'pg_xlog'))

        # Do not capture any TEMP Space files, although we do want to
        # capture the directory name or symlink
        if 'pgsql_tmp' in dirnames:
                dirnames.remove('pgsql_tmp')
                matches.append(os.path.join(root, 'pgsql_tmp'))
        if 'pg_stat_tmp' in dirnames:
                dirnames.remove('pg_stat_tmp')
                matches.append(os.path.join(root, 'pg_stat_tmp'))

        for filename in filenames:
            if is_cluster_toplevel and filename in ('postmaster.pid',
                                                    'postmaster.opts'):
                # Do not include the postmaster pid file or the
                # configuration file in the backup.
                pass
            elif is_cluster_toplevel and filename in PG_CONF:
                # Do not include config files in the backup
                pass
            else:
                matches.append(os.path.join(root, filename))

        # Special case for empty directories
        if not filenames:
            matches.append(root)

        # Special case for tablespaces
        if root == os.path.join(pg_cluster_dir, 'pg_tblspc'):
            for tablespace in dirnames:
                ts_path = os.path.join(root, tablespace)
                ts_name = os.path.basename(ts_path)

                if os.path.islink(ts_path) and os.path.isdir(ts_path):
                    ts_loc = os.readlink(ts_path)
                    ts_walker = os.walk(ts_path)
                    if not ts_loc.endswith(os.path.sep):
                        ts_loc += os.path.sep

                    if ts_name not in spec['tablespaces']:
                        spec['tablespaces'].append(ts_name)
                        link_start = len(spec['base_prefix'])
                        spec[ts_name] = {
                            'loc': ts_loc,
                            # Link path is relative to base_prefix
                            'link': ts_path[link_start:]
                        }

                    for ts_root, ts_dirnames, ts_filenames in ts_walker:
                        if 'pgsql_tmp' in ts_dirnames:
                            ts_dirnames.remove('pgsql_tmp')
                            matches.append(os.path.join(ts_root, 'pgsql_tmp'))

                        for ts_filename in ts_filenames:
                            matches.append(os.path.join(ts_root, ts_filename))

                        # pick up the empty directories, make sure ts_root
                        # isn't duplicated
                        if not ts_filenames and ts_root not in matches:
                            matches.append(ts_root)

                    # The symlink for this tablespace is now in the match list,
                    # remove it.
                    if ts_path in matches:
                        matches.remove(ts_path)

    # Absolute upload paths are used for telling lzop what to compress. We
    # must evaluate tablespace storage dirs separately from core file to handle
    # the case where a common prefix does not exist between the two.
    local_abspaths = [os.path.abspath(match) for match in matches]
    # Common local prefix is the prefix removed from the path all tar members.
    # Core files first
    local_prefix = os.path.commonprefix(local_abspaths)
    if not local_prefix.endswith(os.path.sep):
        local_prefix += os.path.sep

    parts = _segmentation_guts(
        local_prefix, matches, PARTITION_MAX_SZ)

    return spec, parts

########NEW FILE########
__FILENAME__ = base
import gevent
import re

from gevent import queue
from wal_e import exception
from wal_e import log_help
from wal_e import storage

logger = log_help.WalELogger(__name__)

generic_weird_key_hint_message = ('This means an unexpected key was found in '
                                  'a WAL-E prefix.  It can be harmless, or '
                                  'the result a bug or misconfiguration.')


class _Deleter(object):
    def __init__(self):
        # Allow enqueuing of several API calls worth of work, which
        # right now allow 1000 key deletions per job.
        self.PAGINATION_MAX = 1000
        self._q = queue.JoinableQueue(self.PAGINATION_MAX * 10)
        self._worker = gevent.spawn(self._work)
        self._parent_greenlet = gevent.getcurrent()
        self.closing = False

    def close(self):
        self.closing = True
        self._q.join()
        self._worker.kill(block=True)

    def delete(self, key):
        if self.closing:
            raise exception.UserCritical(
                msg='attempt to delete while closing Deleter detected',
                hint='This should be reported as a bug.')

        self._q.put(key)

    def _work(self):
        try:
            while True:
                # If _cut_batch has an error, it is responsible for
                # invoking task_done() the appropriate number of
                # times.
                page = self._cut_batch()

                # If nothing was enqueued, yield and wait around a bit
                # before looking for work again.
                if not page:
                    gevent.sleep(1)
                    continue

                # However, in event of success, the jobs are not
                # considered done until the _delete_batch returns
                # successfully.  In event an exception is raised, it
                # will be propagated to the Greenlet that created the
                # Deleter, but the tasks are marked done nonetheless.
                try:
                    self._delete_batch(page)
                finally:
                    for i in xrange(len(page)):
                        self._q.task_done()
        except KeyboardInterrupt, e:
            # Absorb-and-forward the exception instead of using
            # gevent's link_exception operator, because in gevent <
            # 1.0 there is no way to turn off the alarming stack
            # traces emitted when an exception propagates to the top
            # of a greenlet, linked or no.
            #
            # Normally, gevent.kill is ill-advised because it results
            # in asynchronous exceptions being raised in that
            # greenlet, but given that KeyboardInterrupt is nominally
            # asynchronously raised by receiving SIGINT to begin with,
            # there nothing obvious being lost from using kill() in
            # this case.
            gevent.kill(self._parent_greenlet, e)

    def _cut_batch(self):
        # Attempt to obtain as much work as possible, up to the
        # maximum able to be processed by S3 at one time,
        # PAGINATION_MAX.
        page = []

        try:
            for i in xrange(self.PAGINATION_MAX):
                page.append(self._q.get_nowait())
        except queue.Empty:
            pass
        except:
            # In event everything goes sideways while dequeuing,
            # carefully un-lock the queue.
            for i in xrange(len(page)):
                self._q.task_done()
            raise

        return page


class _BackupList(object):

    def __init__(self, conn, layout, detail):
        self.conn = conn
        self.layout = layout
        self.detail = detail

    def find_all(self, query):
        """A procedure to assist in finding or detailing specific backups

        Currently supports:

        * a backup name (base_number_number)

        * the psuedo-name LATEST, which finds the backup with the most
          recent modification date

        """

        match = re.match(storage.BASE_BACKUP_REGEXP, query)

        if match is not None:
            for backup in iter(self):
                if backup.name == query:
                    yield backup
        elif query == 'LATEST':
            all_backups = list(iter(self))

            if not all_backups:
                return

            assert len(all_backups) > 0

            all_backups.sort(key=lambda bi: bi.last_modified)
            yield all_backups[-1]
        else:
            raise exception.UserException(
                msg='invalid backup query submitted',
                detail='The submitted query operator was "{0}."'
                .format(query))

    def _backup_list(self):
        raise NotImplementedError()

    def __iter__(self):

        # Try to identify the sentinel file.  This is sort of a drag, the
        # storage format should be changed to put them in their own leaf
        # directory.
        #
        # TODO: change storage format
        sentinel_depth = self.layout.basebackups().count('/')
        matcher = re.compile(storage.COMPLETE_BASE_BACKUP_REGEXP).match

        for key in self._backup_list(self.layout.basebackups()):
            key_name = self.layout.key_name(key)
            # Use key depth vs. base and regexp matching to find
            # sentinel files.
            key_depth = key_name.count('/')

            if key_depth == sentinel_depth:
                backup_sentinel_name = key_name.rsplit('/', 1)[-1]
                match = matcher(backup_sentinel_name)
                if match:
                    # TODO: It's necessary to use the name of the file to
                    # get the beginning wal segment information, whereas
                    # the ending information is encoded into the file
                    # itself.  Perhaps later on it should all be encoded
                    # into the name when the sentinel files are broken out
                    # into their own directory, so that S3 listing gets
                    # all commonly useful information without doing a
                    # request-per.
                    groups = match.groupdict()

                    info = storage.get_backup_info(
                        self.layout,
                        name='base_{filename}_{offset}'.format(**groups),
                        last_modified=self.layout.key_last_modified(key),
                        wal_segment_backup_start=groups['filename'],
                        wal_segment_offset_backup_start=groups['offset'])

                    if self.detail:
                        try:
                            # This costs one web request
                            info.load_detail(self.conn)
                        except gevent.Timeout:
                            pass

                    yield info


class _DeleteFromContext(object):

    def __init__(self, conn, layout, dry_run):
        self.conn = conn
        self.dry_run = dry_run
        self.layout = layout
        self.deleter = None  # Must be set by subclass

        assert self.dry_run in (True, False)

    def _container_name(self, key):
        pass

    def _maybe_delete_key(self, key, type_of_thing):
        key_name = self.layout.key_name(key)
        url = '{scheme}://{bucket}/{name}'.format(
            scheme=self.layout.scheme, bucket=self._container_name(key),
            name=key_name)
        log_message = dict(
            msg='deleting {0}'.format(type_of_thing),
            detail='The key being deleted is {url}.'.format(url=url))

        if self.dry_run is False:
            logger.info(**log_message)
            self.deleter.delete(key)
        elif self.dry_run is True:
            log_message['hint'] = ('This is only a dry run -- no actual data '
                                   'is being deleted')
            logger.info(**log_message)
        else:
            assert False

    def _groupdict_to_segment_number(self, d):
        return storage.base.SegmentNumber(log=d['log'], seg=d['seg'])

    def _delete_if_before(self, delete_horizon_segment_number,
                            scanned_segment_number, key, type_of_thing):
        if scanned_segment_number.as_an_integer < \
            delete_horizon_segment_number.as_an_integer:
            self._maybe_delete_key(key, type_of_thing)

    def _delete_base_backups_before(self, segment_info):
        base_backup_sentinel_depth = self.layout.basebackups().count('/') + 1
        version_depth = base_backup_sentinel_depth + 1
        volume_backup_depth = version_depth + 1

        # The base-backup sweep, deleting bulk data and metadata, but
        # not any wal files.
        for key in self._backup_list(prefix=self.layout.basebackups()):
            key_name = self.layout.key_name(key)
            url = '{scheme}://{bucket}/{name}'.format(
                scheme=self.layout.scheme, bucket=self._container_name(key),
                name=key_name)
            key_parts = key_name.split('/')
            key_depth = len(key_parts)

            if key_depth not in (base_backup_sentinel_depth, version_depth,
                                 volume_backup_depth):
                # Check depth (in terms of number of
                # slashes/delimiters in the key); if there exists a
                # key with an unexpected depth relative to the
                # context, complain a little bit and move on.
                logger.warning(
                    msg="skipping non-qualifying key in 'delete before'",
                    detail=(
                        'The unexpected key is "{0}", and it appears to be '
                        'at an unexpected depth.'.format(url)),
                    hint=generic_weird_key_hint_message)
            elif key_depth == base_backup_sentinel_depth:
                # This is a key at the base-backup-sentinel file
                # depth, so check to see if it matches the known form.
                match = re.match(storage.COMPLETE_BASE_BACKUP_REGEXP,
                                 key_parts[-1])
                if match is None:
                    # This key was at the level for a base backup
                    # sentinel, but doesn't match the known pattern.
                    # Complain about this, and move on.
                    logger.warning(
                        msg="skipping non-qualifying key in 'delete before'",
                        detail=('The unexpected key is "{0}", and it appears '
                                'not to match the base-backup sentinel '
                                'pattern.'.format(url)),
                        hint=generic_weird_key_hint_message)
                else:
                    # This branch actually might delete some data: the
                    # key is at the right level, and matches the right
                    # form.  The last check is to make sure it's in
                    # the range of things to delete, and if that is
                    # the case, attempt deletion.
                    assert match is not None
                    scanned_sn = \
                        self._groupdict_to_segment_number(match.groupdict())
                    self._delete_if_before(segment_info, scanned_sn, key,
                                        'a base backup sentinel file')
            elif key_depth == version_depth:
                match = re.match(
                    storage.BASE_BACKUP_REGEXP, key_parts[-2])

                if match is None or key_parts[-1] != 'extended_version.txt':
                    logger.warning(
                        msg="skipping non-qualifying key in 'delete before'",
                        detail=('The unexpected key is "{0}", and it appears '
                                'not to match the extended-version backup '
                                'pattern.'.format(url)),
                        hint=generic_weird_key_hint_message)
                else:
                    assert match is not None
                    scanned_sn = \
                        self._groupdict_to_segment_number(match.groupdict())
                    self._delete_if_before(segment_info, scanned_sn, key,
                                        'a extended version metadata file')
            elif key_depth == volume_backup_depth:
                # This has the depth of a base-backup volume, so try
                # to match the expected pattern and delete it if the
                # pattern matches and the base backup part qualifies
                # properly.
                assert len(key_parts) >= 2, ('must be a logical result of the '
                                             's3 storage layout')

                match = re.match(
                    storage.BASE_BACKUP_REGEXP, key_parts[-3])

                if match is None or key_parts[-2] != 'tar_partitions':
                    logger.warning(
                        msg="skipping non-qualifying key in 'delete before'",
                        detail=(
                            'The unexpected key is "{0}", and it appears '
                            'not to match the base-backup partition pattern.'
                            .format(url)),
                        hint=generic_weird_key_hint_message)
                else:
                    assert match is not None
                    scanned_sn = \
                        self._groupdict_to_segment_number(match.groupdict())
                    self._delete_if_before(segment_info, scanned_sn, key,
                                        'a base backup volume')
            else:
                assert False

    def _delete_wals_before(self, segment_info):
        """
        Delete all WAL files before segment_info.

        Doesn't delete any base-backup data.
        """
        wal_key_depth = self.layout.wal_directory().count('/') + 1
        for key in self._backup_list(prefix=self.layout.wal_directory()):
            key_name = self.layout.key_name(key)
            bucket = self._container_name(key)
            url = '{scm}://{bucket}/{name}'.format(scm=self.layout.scheme,
                                                   bucket=bucket,
                                                   name=key_name)
            key_parts = key_name.split('/')
            key_depth = len(key_parts)
            if key_depth != wal_key_depth:
                logger.warning(
                    msg="skipping non-qualifying key in 'delete before'",
                    detail=(
                        'The unexpected key is "{0}", and it appears to be '
                        'at an unexpected depth.'.format(url)),
                    hint=generic_weird_key_hint_message)
            elif key_depth == wal_key_depth:
                segment_match = (re.match(storage.SEGMENT_REGEXP + r'\.lzo',
                                          key_parts[-1]))
                label_match = (re.match(storage.SEGMENT_REGEXP +
                                        r'\.[A-F0-9]{8,8}.backup.lzo',
                                        key_parts[-1]))
                history_match = re.match(r'[A-F0-9]{8,8}\.history',
                                         key_parts[-1])

                all_matches = [segment_match, label_match, history_match]

                non_matches = len(list(m for m in all_matches if m is None))

                # These patterns are intended to be mutually
                # exclusive, so either one should match or none should
                # match.
                assert non_matches in (len(all_matches) - 1, len(all_matches))
                if non_matches == len(all_matches):
                    logger.warning(
                        msg="skipping non-qualifying key in 'delete before'",
                        detail=('The unexpected key is "{0}", and it appears '
                                'not to match the WAL file naming pattern.'
                                .format(url)),
                        hint=generic_weird_key_hint_message)
                elif segment_match is not None:
                    scanned_sn = self._groupdict_to_segment_number(
                        segment_match.groupdict())
                    self._delete_if_before(segment_info, scanned_sn, key,
                                        'a wal file')
                elif label_match is not None:
                    scanned_sn = self._groupdict_to_segment_number(
                        label_match.groupdict())
                    self._delete_if_before(segment_info, scanned_sn, key,
                                        'a backup history file')
                elif history_match is not None:
                    # History (timeline) files do not have any actual
                    # WAL position information, so they are never
                    # deleted.
                    pass
                else:
                    assert False
            else:
                assert False

    def delete_everything(self):
        """Delete everything in a storage layout

        Named provocatively for a reason: can (and in fact intended
        to) cause irrecoverable loss of data.  This can be used to:

        * Completely obliterate data from old WAL-E versions
          (i.e. layout.VERSION is an obsolete version)

        * Completely obliterate all backups (from a decommissioned
          database, for example)

        """
        for k in self._backup_list(prefix=self.layout.basebackups()):
            self._maybe_delete_key(k, 'part of a base backup')

        for k in self._backup_list(prefix=self.layout.wal_directory()):
            self._maybe_delete_key(k, 'part of wal logs')

        if self.deleter:
            self.deleter.close()

    def delete_before(self, segment_info):
        """
        Delete all base backups and WAL before a given segment

        This is the most commonly-used deletion operator; to delete
        old backups and WAL.

        """

        # This will delete all base backup data before segment_info.
        self._delete_base_backups_before(segment_info)

        # This will delete all WAL segments before segment_info.
        self._delete_wals_before(segment_info)

        if self.deleter:
            self.deleter.close()

    def delete_with_retention(self, num_to_retain):
        """
        Retain the num_to_retain most recent backups and delete all data
        before them.

        """
        base_backup_sentinel_depth = self.layout.basebackups().count('/') + 1

        # Sweep over base backup files, collecting sentinel files from
        # completed backups.
        completed_basebackups = []
        for key in self._backup_list(prefix=self.layout.basebackups()):

            key_name = self.layout.key_name(key)
            key_parts = key_name.split('/')
            key_depth = len(key_parts)
            url = '{scheme}://{bucket}/{name}'.format(
                scheme=self.layout.scheme,
                bucket=self._container_name(key),
                name=key_name)

            if key_depth == base_backup_sentinel_depth:
                # This is a key at the depth of a base-backup-sentinel file.
                # Check to see if it matches the known form.
                match = re.match(storage.COMPLETE_BASE_BACKUP_REGEXP,
                                 key_parts[-1])

                # If this isn't a base-backup-sentinel file, just ignore it.
                if match is None:
                    continue

                # This key corresponds to a base-backup-sentinel file and
                # represents a completed backup. Grab its segment number.
                scanned_sn = \
                    self._groupdict_to_segment_number(match.groupdict())
                completed_basebackups.append(dict(
                    scanned_sn=scanned_sn,
                    url=url))

        # Sort the base backups from newest to oldest.
        basebackups = sorted(
                        completed_basebackups,
                        key=lambda backup: backup['scanned_sn'].as_an_integer,
                        reverse=True)
        last_retained = None
        if len(basebackups) <= num_to_retain:
            detail = None
            if len(basebackups) == 0:
                msg = 'Not deleting any data.'
                detail = 'No existing base backups.'
            elif len(basebackups) == 1:
                last_retained = basebackups[-1]
                msg = 'Retaining existing base backup.'
            else:
                last_retained = basebackups[-1]
                msg = "Retaining all %d base backups." % len(basebackups)
        else:
            last_retained = basebackups[num_to_retain - 1]
            num_deleting = len(basebackups) - num_to_retain
            msg = "Deleting %d oldest base backups." % num_deleting
            detail = "Found %d total base backups." % len(basebackups)
        log_message = dict(msg=msg)
        if detail is not None:
            log_message['detail'] = detail
        if last_retained is not None:
            log_message['hint'] = \
                "Deleting keys older than %s." % last_retained['url']
        logger.info(**log_message)

        # This will delete all base backup and WAL data before
        # last_retained['scanned_sn'].
        if last_retained is not None:
            self._delete_base_backups_before(last_retained['scanned_sn'])
            self._delete_wals_before(last_retained['scanned_sn'])

        if self.deleter:
            self.deleter.close()

########NEW FILE########
__FILENAME__ = pg_controldata_worker
from subprocess import PIPE
import os
from wal_e.piper import popen_sp

CONTROLDATA_BIN = 'pg_controldata'
CONFIG_BIN = 'pg_config'


class PgControlDataParser(object):
    """
    When we're backing up a PG cluster that is not
    running, we can't query it for information like
    the current restartpoint's WAL index,
    the current PG version, etc.

    Fortunately, we can use pg_controldata, which
    provides this information and doesn't require
    a running PG process
    """

    def __init__(self, data_directory):
        self.data_directory = data_directory
        pg_config_proc = popen_sp([CONFIG_BIN],
                             stdout=PIPE)
        output = pg_config_proc.communicate()[0]
        for line in output.split('\n'):
            parts = line.split('=')
            if len(parts) != 2:
                continue
            key, val = map(lambda x: x.strip(), parts)
            if key == 'BINDIR':
                self._controldata_bin = os.path.join(val, CONTROLDATA_BIN)
            elif key == 'VERSION':
                self._pg_version = val

    def _read_controldata(self):
        controldata_proc = popen_sp(
            [self._controldata_bin, self.data_directory], stdout=PIPE)
        stdout = controldata_proc.communicate()[0]
        controldata = {}
        for line in stdout.split('\n'):
            split_values = line.split(':')
            if len(split_values) == 2:
                key, val = split_values
                controldata[key.strip()] = val.strip()
        return controldata

    def controldata_bin(self):
        return self._controldata_bin

    def pg_version(self):
        return self._pg_version

    def last_xlog_file_name_and_offset(self):
        controldata = self._read_controldata()
        last_checkpoint_offset = \
            controldata["Latest checkpoint's REDO location"]
        current_timeline = controldata["Latest checkpoint's TimeLineID"]
        x, offset = last_checkpoint_offset.split('/')
        timeline = current_timeline.zfill(8)
        wal = x.zfill(8)
        offset = offset[0:2].zfill(8)
        return {
            'file_name': ''.join([timeline, wal, offset]),
            'file_offset': offset.zfill(8)}

########NEW FILE########
__FILENAME__ = psql_worker
import csv
import datetime

from subprocess import PIPE

from wal_e.piper import popen_nonblock
from wal_e.exception import UserException

PSQL_BIN = 'psql'


class UTC(datetime.tzinfo):
    """
    UTC timezone

    Adapted from a Python example

    """

    ZERO = datetime.timedelta(0)
    HOUR = datetime.timedelta(hours=1)

    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO


def psql_csv_run(sql_command, error_handler=None):
    """
    Runs psql and returns a CSVReader object from the query

    This CSVReader includes header names as the first record in all
    situations.  The output is fully buffered into Python.

    """
    csv_query = ('COPY ({query}) TO STDOUT WITH CSV HEADER;'
                 .format(query=sql_command))

    psql_proc = popen_nonblock([PSQL_BIN, '-d', 'postgres', '--no-password',
                                '-c', csv_query],
                               stdout=PIPE)
    stdout = psql_proc.communicate()[0]

    if psql_proc.returncode != 0:
        if error_handler is not None:
            error_handler(psql_proc)
        else:
            assert error_handler is None
            raise UserException(
                'could not csv-execute a query successfully via psql',
                'Query was "{query}".'.format(sql_command),
                'You may have to set some libpq environment '
                'variables if you are sure the server is running.')

    # Previous code must raise any desired exceptions for non-zero
    # exit codes
    assert psql_proc.returncode == 0

    # Fake enough iterator interface to get a CSV Reader object
    # that works.
    return csv.reader(iter(stdout.strip().split('\n')))


class PgBackupStatements(object):
    """
    Contains operators to start and stop a backup on a Postgres server

    Relies on PsqlHelp for underlying mechanism.

    """

    @staticmethod
    def _dict_transform(csv_reader):
        rows = list(csv_reader)
        assert len(rows) == 2, 'Expect header row and data row'
        return dict(zip(*rows))

    @classmethod
    def run_start_backup(cls):
        """
        Connects to a server and attempts to start a hot backup

        Yields the WAL information in a dictionary for bookkeeping and
        recording.

        """
        def handler(popen):
            assert popen.returncode != 0
            raise UserException('Could not start hot backup')

        # The difficulty of getting a timezone-stamped, UTC,
        # ISO-formatted datetime is downright embarrassing.
        #
        # See http://bugs.python.org/issue5094
        label = 'freeze_start_' + (datetime.datetime.utcnow()
                                   .replace(tzinfo=UTC()).isoformat())

        return cls._dict_transform(psql_csv_run(
                "SELECT file_name, "
                "  lpad(file_offset::text, 8, '0') AS file_offset "
                "FROM pg_xlogfile_name_offset("
                "  pg_start_backup('{0}'))".format(label),
                error_handler=handler))

    @classmethod
    def run_stop_backup(cls):
        """
        Stop a hot backup, if it was running, or error

        Return the last WAL file name and position that is required to
        gain consistency on the captured heap.

        """
        def handler(popen):
            assert popen.returncode != 0
            raise UserException('Could not stop hot backup')

        return cls._dict_transform(psql_csv_run(
                "SELECT file_name, "
                "  lpad(file_offset::text, 8, '0') AS file_offset "
                "FROM pg_xlogfile_name_offset("
                "  pg_stop_backup())", error_handler=handler))

    @classmethod
    def pg_version(cls):
        """
        Get a very informative version string from Postgres

        Includes minor version, major version, and architecture, among
        other details.

        """
        return cls._dict_transform(psql_csv_run('SELECT * FROM version()'))

########NEW FILE########
__FILENAME__ = wal_transfer
import gevent
import os
import re
import traceback

from os import path
from wal_e import channel
from wal_e import storage
from wal_e.exception import UserCritical


class WalSegment(object):
    def __init__(self, seg_path, explicit=False):
        self.path = seg_path
        self.explicit = explicit
        self.name = path.basename(self.path)

    def mark_done(self):
        """Mark the archive status of this segment as 'done'.

        This is most useful when performing out-of-band parallel
        uploads of segments, so that Postgres doesn't try to go and
        upload them again.

        This amounts to messing with an internal bookkeeping mechanism
        of Postgres, but that mechanism is not changing too fast over
        the last five years and seems simple enough.
        """

        # Recheck that this is not an segment explicitly passed from Postgres
        if self.explicit:
            raise UserCritical(
                msg='unexpected attempt to modify wal metadata detected',
                detail=('Segments explicitly passed from postgres should not '
                        'engage in archiver metadata manipulation: {0}'
                        .format(self.path)),
                hint='report a bug')

        # Attempt a rename of archiver metadata, wrapping unexpected
        # raised exceptions into a UserCritical.
        try:
            status_dir = path.join(path.dirname(self.path),
                                   'archive_status')

            ready_metadata = path.join(status_dir, self.name + '.ready')
            done_metadata = path.join(status_dir, self.name + '.done')

            os.rename(ready_metadata, done_metadata)
        except:
            raise UserCritical(
                msg='problem moving .ready archive status to .done',
                detail='Traceback is: {0}'.format(traceback.format_exc()),
                hint='report a bug')

    @staticmethod
    def from_ready_archive_status(xlog_dir):
        status_dir = path.join(xlog_dir, 'archive_status')
        statuses = os.listdir(status_dir)

        # Try to send earliest segments first.
        statuses.sort()

        for status in statuses:
            # Only bother with segments, not history files and such;
            # it seems like special treatment of such quantities is
            # more likely to change than that of the WAL segments,
            # which are bulky and situated in a particular place for
            # crash recovery.
            match = re.match(storage.SEGMENT_READY_REGEXP, status)

            if match:
                seg_name = match.groupdict()['filename']
                seg_path = path.join(xlog_dir, seg_name)

                yield WalSegment(seg_path, explicit=False)


class WalTransferGroup(object):
    """Concurrency and metadata manipulation for parallel transfers.

    It so happens that it looks like WAL segment uploads and downloads
    can be neatly done with one mechanism, so do so here.
    """

    def __init__(self, transferer):
        # Injected transfer mechanism
        self.transferer = transferer

        # Synchronization and tasks
        self.wait_change = channel.Channel()
        self.expect = 0
        self.closed = False

        # Maintain a list of running greenlets for gevent.killall.
        #
        # Abrupt termination of WAL-E (e.g. calling exit, as seen with
        # a propagated error) will not result in clean-ups
        # (e.g. 'finally' clauses) being run, so it's necessary to
        # retain the greenlets, inject asynchronous exceptions, and
        # then wait on termination.
        self.greenlets = set([])

    def join(self):
        """Wait for transfer to exit, raising errors as necessary."""
        self.closed = True

        while self.expect > 0:
            val = self.wait_change.get()
            self.expect -= 1

            if val is not None:
                # Kill all the running greenlets, waiting for them to
                # clean up and exit.
                #
                # As a fail-safe against indefinite blocking of
                # gevent.killall, time out after a liberal amount of
                # time.  This is not expected to ever occur except for
                # bugs and very dire situations, so do not take pains
                # to convert it into a UserException or anything.
                gevent.killall(list(self.greenlets), block=True, timeout=60)
                raise val

    def start(self, segment):
        """Begin transfer for an indicated wal segment."""

        if self.closed:
            raise UserCritical(msg='attempt to transfer wal after closing',
                               hint='report a bug')

        g = gevent.Greenlet(self.transferer, segment)
        g.link(self._complete_execution)
        self.greenlets.add(g)

        # Increment .expect before starting the greenlet, or else a
        # very unlucky .join could be fooled as to when pool is
        # complete.
        self.expect += 1

        g.start()

    def _complete_execution(self, g):
        """Forward any raised exceptions across a channel."""

        # Triggered via completion callback.
        #
        # Runs in its own greenlet, so take care to forward the
        # exception, if any, to fail the entire transfer in event of
        # trouble.
        assert g.ready()
        self.greenlets.remove(g)

        placed = UserCritical(msg='placeholder bogus exception',
                              hint='report a bug')

        if g.successful():
            try:
                segment = g.get()

                if not segment.explicit:
                    segment.mark_done()
            except BaseException as e:
                # Absorb and forward exceptions across the channel.
                placed = e
            else:
                placed = None
        else:
            placed = g.exception

        self.wait_change.put(placed)

########NEW FILE########
__FILENAME__ = s3_deleter
from wal_e import exception
from wal_e import retries
from wal_e.worker.base import _Deleter


class Deleter(_Deleter):

    @retries.retry()
    def _delete_batch(self, page):
        # Check that all keys are in the same bucket; this code is not
        # designed to deal with fast deletion of keys from multiple
        # buckets at the same time, and not checking this could result
        # in deleting similarly named keys from the wrong bucket.
        #
        # In wal-e's use, homogeneity of the bucket retaining the keys
        # is presumed to be always the case.
        bucket_name = page[0].bucket.name
        for key in page:
            if key.bucket.name != bucket_name:
                raise exception.UserCritical(
                    msg='submitted keys are not part of the same bucket',
                    detail=('The clashing bucket names are {0} and {1}.'
                            .format(key.bucket.name, bucket_name)),
                    hint='This should be reported as a bug.')

        bucket = page[0].bucket
        bucket.delete_keys([key.name for key in page])

########NEW FILE########
__FILENAME__ = s3_worker
"""
WAL-E AWS S3 workers

These are functions that are amenable to be called from other modules,
with the intention that they are used in gevent greenlets.

"""
import gevent
import re

from wal_e import log_help
from wal_e import storage
from wal_e.blobstore import s3
from wal_e.pipeline import get_download_pipeline
from wal_e.piper import PIPE
from wal_e.retries import retry
from wal_e.tar_partition import TarPartition
from wal_e.worker.base import _BackupList, _DeleteFromContext
from wal_e.worker.base import generic_weird_key_hint_message
from wal_e.worker.s3.s3_deleter import Deleter

logger = log_help.WalELogger(__name__)


def get_bucket(conn, name):
    return conn.get_bucket(name, validate=False)


class TarPartitionLister(object):
    def __init__(self, s3_conn, layout, backup_info):
        self.s3_conn = s3_conn
        self.layout = layout
        self.backup_info = backup_info

    def __iter__(self):
        prefix = self.layout.basebackup_tar_partition_directory(
            self.backup_info)

        bucket = get_bucket(self.s3_conn, self.layout.store_name())
        for key in bucket.list(prefix=prefix):
            url = 's3://{bucket}/{name}'.format(bucket=key.bucket.name,
                                                name=key.name)
            key_last_part = key.name.rsplit('/', 1)[-1]
            match = re.match(storage.VOLUME_REGEXP, key_last_part)
            if match is None:
                logger.warning(
                    msg='unexpected key found in tar volume directory',
                    detail=('The unexpected key is stored at "{0}".'
                            .format(url)),
                    hint=generic_weird_key_hint_message)
            else:
                yield key_last_part


class BackupFetcher(object):
    def __init__(self, s3_conn, layout, backup_info, local_root, decrypt):
        self.s3_conn = s3_conn
        self.layout = layout
        self.local_root = local_root
        self.backup_info = backup_info
        self.bucket = get_bucket(self.s3_conn, self.layout.store_name())
        self.decrypt = decrypt

    @retry()
    def fetch_partition(self, partition_name):
        part_abs_name = self.layout.basebackup_tar_partition(
            self.backup_info, partition_name)

        logger.info(
            msg='beginning partition download',
            detail='The partition being downloaded is {0}.'
            .format(partition_name),
            hint='The absolute S3 key is {0}.'.format(part_abs_name))

        key = self.bucket.get_key(part_abs_name)
        with get_download_pipeline(PIPE, PIPE, self.decrypt) as pl:
            g = gevent.spawn(s3.write_and_return_error, key, pl.stdin)
            TarPartition.tarfile_extract(pl.stdout, self.local_root)

            # Raise any exceptions guarded by write_and_return_error.
            exc = g.get()
            if exc is not None:
                raise exc


class BackupList(_BackupList):

    def _backup_detail(self, key):
        return key.get_contents_as_string()

    def _backup_list(self, prefix):
        bucket = get_bucket(self.conn, self.layout.store_name())
        return bucket.list(prefix=prefix)


class DeleteFromContext(_DeleteFromContext):

    def __init__(self, s3_conn, layout, dry_run):
        super(DeleteFromContext, self).__init__(s3_conn, layout, dry_run)

        if not dry_run:
            self.deleter = Deleter()
        else:
            self.deleter = None

    def _container_name(self, key):
        return key.bucket.name

    def _backup_list(self, prefix):
        bucket = get_bucket(self.conn, self.layout.store_name())
        return bucket.list(prefix=prefix)

########NEW FILE########
__FILENAME__ = swift_deleter
from wal_e import retries
from wal_e.worker.base import _Deleter


class Deleter(_Deleter):
    def __init__(self, swift_conn, container):
        super(Deleter, self).__init__()
        self.swift_conn = swift_conn
        self.container = container

    @retries.retry()
    def _delete_batch(self, page):
        # swiftclient doesn't expose mass-delete yet (the raw API supports it
        # when a particular middleware is installed), so we delete one at a
        # time.
        for blob in page:
            self.swift_conn.delete_object(self.container, blob.name)

########NEW FILE########
__FILENAME__ = swift_worker
import re

import gevent

from wal_e import log_help, storage
from wal_e.blobstore import swift
from wal_e.pipeline import get_download_pipeline
from wal_e.piper import PIPE
from wal_e.retries import retry
from wal_e.tar_partition import TarPartition
from wal_e.worker.base import (
    _BackupList, _DeleteFromContext, generic_weird_key_hint_message
)
from wal_e.worker.swift.swift_deleter import Deleter


logger = log_help.WalELogger(__name__)


class TarPartitionLister(object):
    def __init__(self, swift_conn, layout, backup_info):
        self.swift_conn = swift_conn
        self.layout = layout
        self.backup_info = backup_info

    def __iter__(self):
        prefix = self.layout.basebackup_tar_partition_directory(
            self.backup_info)

        _, object_list = self.swift_conn.get_container(
            self.layout.store_name(), prefix='/' + prefix
        )
        for obj in object_list:
            url = 'swift://{container}/{name}'.format(
                container=self.layout.store_name(), name=obj['name'])
            name_last_part = obj['name'].rsplit('/', 1)[-1]
            match = re.match(storage.VOLUME_REGEXP, name_last_part)
            if match is None:
                logger.warning(
                    msg='unexpected key found in tar volume directory',
                    detail=('The unexpected key is stored at "{0}".'
                            .format(url)),
                    hint=generic_weird_key_hint_message)
            else:
                yield name_last_part


class BackupFetcher(object):
    def __init__(self, swift_conn, layout, backup_info, local_root, decrypt):
        self.swift_conn = swift_conn
        self.layout = layout
        self.local_root = local_root
        self.backup_info = backup_info
        self.decrypt = decrypt

    @retry()
    def fetch_partition(self, partition_name):
        part_abs_name = self.layout.basebackup_tar_partition(
            self.backup_info, partition_name)

        logger.info(
            msg='beginning partition download',
            detail=('The partition being downloaded is {0}.'
                    .format(partition_name)),
            hint='The absolute Swift object name is {0}.'
            .format(part_abs_name))

        url = 'swift://{ctr}/{path}'.format(ctr=self.layout.store_name(),
                                            path=part_abs_name)
        with get_download_pipeline(PIPE, PIPE, self.decrypt) as pl:
            g = gevent.spawn(swift.write_and_return_error,
                             url, self.swift_conn, pl.stdin)
            TarPartition.tarfile_extract(pl.stdout, self.local_root)

            # Raise any exceptions guarded by write_and_return_error.
            exc = g.get()
            if exc is not None:
                raise exc


class BackupList(_BackupList):

    def _backup_detail(self, blob):
        return self.conn.get_object(self.layout.store_name(), blob['name'])

    def _backup_list(self, prefix):
        _, object_list = self.conn.get_container(self.layout.store_name(),
                                                 prefix='/' + prefix)
        return [
            swift.SwiftKey(obj['name'], obj['bytes'], obj['last_modified'])
            for obj in object_list
        ]


class DeleteFromContext(_DeleteFromContext):

    def __init__(self, wabs_conn, layout, dry_run):
        super(DeleteFromContext, self).__init__(wabs_conn, layout, dry_run)

        if not dry_run:
            self.deleter = Deleter(self.conn, self.layout.store_name())
        else:
            self.deleter = None

    def _container_name(self, key):
        return self.layout.store_name()

    def _backup_list(self, prefix):
        _, object_list = self.conn.get_container(self.layout.store_name(),
                                                 prefix='/' + prefix)
        return [
            swift.SwiftKey(obj['name'], obj['bytes'], obj['last_modified'])
            for obj in object_list
        ]

########NEW FILE########
__FILENAME__ = upload
import socket
import tempfile
import time

import boto.exception

from wal_e import log_help
from wal_e import pipebuf
from wal_e import pipeline
from wal_e import storage
from wal_e.blobstore import get_blobstore
from wal_e.piper import PIPE
from wal_e.retries import retry, retry_with_count
from wal_e.worker.worker_util import do_lzop_put, format_kib_per_second

logger = log_help.WalELogger(__name__)


class WalUploader(object):
    def __init__(self, layout, creds, gpg_key_id):
        self.layout = layout
        self.creds = creds
        self.gpg_key_id = gpg_key_id
        self.blobstore = get_blobstore(layout)

    def __call__(self, segment):
        # TODO :: Move arbitray path construction to StorageLayout Object
        url = '{0}/wal_{1}/{2}.lzo'.format(self.layout.prefix.rstrip('/'),
                                           storage.CURRENT_VERSION,
                                           segment.name)

        logger.info(msg='begin archiving a file',
                    detail=('Uploading "{wal_path}" to "{url}".'
                            .format(wal_path=segment.path, url=url)),
                    structured={'action': 'push-wal',
                                'key': url,
                                'seg': segment.name,
                                'prefix': self.layout.path_prefix,
                                'state': 'begin'})

        # Upload and record the rate at which it happened.
        kib_per_second = do_lzop_put(self.creds, url, segment.path,
                                     self.gpg_key_id)

        logger.info(msg='completed archiving to a file ',
                    detail=('Archiving to "{url}" complete at '
                            '{kib_per_second}KiB/s. '
                            .format(url=url, kib_per_second=kib_per_second)),
                    structured={'action': 'push-wal',
                                'key': url,
                                'rate': kib_per_second,
                                'seg': segment.name,
                                'prefix': self.layout.path_prefix,
                                'state': 'complete'})

        return segment


class PartitionUploader(object):
    def __init__(self, creds, backup_prefix, rate_limit, gpg_key):
        self.creds = creds
        self.backup_prefix = backup_prefix
        self.rate_limit = rate_limit
        self.gpg_key = gpg_key
        self.blobstore = get_blobstore(storage.StorageLayout(backup_prefix))

    def __call__(self, tpart):
        """
        Synchronous version of the upload wrapper

        """
        logger.info(msg='beginning volume compression',
                    detail='Building volume {name}.'.format(name=tpart.name))

        with tempfile.NamedTemporaryFile(
                mode='r+b', bufsize=pipebuf.PIPE_BUF_BYTES) as tf:
            with pipeline.get_upload_pipeline(PIPE, tf,
                                              rate_limit=self.rate_limit,
                                              gpg_key=self.gpg_key) as pl:
                tpart.tarfile_write(pl.stdin)

            tf.flush()

            # TODO :: Move arbitray path construction to StorageLayout Object
            url = '{0}/tar_partitions/part_{number:08d}.tar.lzo'.format(
                self.backup_prefix.rstrip('/'), number=tpart.name)

            logger.info(msg='begin uploading a base backup volume',
                        detail='Uploading to "{url}".'.format(url=url))

            def log_volume_failures_on_error(exc_tup, exc_processor_cxt):
                def standard_detail_message(prefix=''):
                    return (prefix +
                            '  There have been {n} attempts to send the '
                            'volume {name} so far.'.format(n=exc_processor_cxt,
                                                           name=tpart.name))

                typ, value, tb = exc_tup
                del exc_tup

                # Screen for certain kinds of known-errors to retry from
                if issubclass(typ, socket.error):
                    socketmsg = value[1] if isinstance(value, tuple) else value

                    logger.info(
                        msg='Retrying send because of a socket error',
                        detail=standard_detail_message(
                            "The socket error's message is '{0}'."
                            .format(socketmsg)))
                elif (issubclass(typ, boto.exception.S3ResponseError) and
                      value.error_code == 'RequestTimeTooSkewed'):
                    logger.info(
                        msg='Retrying send because of a Request Skew time',
                        detail=standard_detail_message())

                else:
                    # This type of error is unrecognized as a retry-able
                    # condition, so propagate it, original stacktrace and
                    # all.
                    raise typ, value, tb

            @retry(retry_with_count(log_volume_failures_on_error))
            def put_file_helper():
                tf.seek(0)
                return self.blobstore.uri_put_file(self.creds, url, tf)

            # Actually do work, retrying if necessary, and timing how long
            # it takes.
            clock_start = time.time()
            k = put_file_helper()
            clock_finish = time.time()

            kib_per_second = format_kib_per_second(clock_start, clock_finish,
                                                   k.size)
            logger.info(
                msg='finish uploading a base backup volume',
                detail=('Uploading to "{url}" complete at '
                        '{kib_per_second}KiB/s. '
                        .format(url=url, kib_per_second=kib_per_second)))

        return tpart

########NEW FILE########
__FILENAME__ = upload_pool
import gc
import gevent

from wal_e import channel
from wal_e import tar_partition
from wal_e.exception import UserCritical


class TarUploadPool(object):
    def __init__(self, uploader, max_concurrency,
                 max_members=tar_partition.PARTITION_MAX_MEMBERS):
        # Injected upload mechanism
        self.uploader = uploader

        # Concurrency maximums
        self.max_members = max_members
        self.max_concurrency = max_concurrency

        # Current concurrency burden
        self.member_burden = 0

        # Synchronization and tasks
        self.wait_change = channel.Channel()
        self.closed = False

        # Used for both synchronization and measurement.
        self.concurrency_burden = 0

    def _start(self, tpart):
        """Start upload and accout for resource consumption."""
        g = gevent.Greenlet(self.uploader, tpart)
        g.link(self._finish)

        # Account for concurrency_burden before starting the greenlet
        # to avoid racing against .join.
        self.concurrency_burden += 1

        self.member_burden += len(tpart)

        g.start()

    def _finish(self, g):
        """Called on completion of an upload greenlet.

        Takes care to forward Exceptions or, if there is no error, the
        finished TarPartition value across a channel.
        """
        assert g.ready()

        if g.successful():
            finished_tpart = g.get()
            self.wait_change.put(finished_tpart)
        else:
            self.wait_change.put(g.exception)

    def _wait(self):
        """Block until an upload finishes

        Raise an exception if that tar volume failed with an error.
        """
        val = self.wait_change.get()

        if isinstance(val, Exception):
            # Don't other uncharging, because execution is going to stop
            raise val
        else:
            # Uncharge for resources.
            self.member_burden -= len(val)
            self.concurrency_burden -= 1

    def put(self, tpart):
        """Upload a tar volume

        Blocks if there is too much work outstanding already, and
        raise errors of previously submitted greenlets that die
        unexpectedly.
        """
        if self.closed:
            raise UserCritical(msg='attempt to upload tar after closing',
                               hint='report a bug')

        while True:
            too_many = (
                self.concurrency_burden + 1 > self.max_concurrency
                or self.member_burden + len(tpart) > self.max_members
            )

            if too_many:
                # If there are not enough resources to start an upload
                # even with zero uploads in progress, then something
                # has gone wrong: the user should not be given enough
                # rope to hang themselves in this way.
                if self.concurrency_burden == 0:
                    raise UserCritical(
                        msg=('not enough resources in pool to '
                             'support an upload'),
                        hint='report a bug')

                # _wait blocks until an upload finishes and clears its
                # used resources, after which another attempt to
                # evaluate scheduling resources for another upload
                # might be worth evaluating.
                #
                # Alternatively, an error was encountered in a
                # previous upload in which case it'll be raised here
                # and cause the process to regard the upload as a
                # failure.
                self._wait()
                gc.collect()
            else:
                # Enough resources available: commence upload
                self._start(tpart)
                return

    def join(self):
        """Wait for uploads to exit, raising errors as necessary."""
        self.closed = True

        while self.concurrency_burden > 0:
            self._wait()

########NEW FILE########
__FILENAME__ = wabs_deleter
from wal_e import retries
from wal_e.worker.base import _Deleter


class Deleter(_Deleter):

    def __init__(self, wabs_conn, container):
        super(Deleter, self).__init__()
        self.wabs_conn = wabs_conn
        self.container = container

    @retries.retry()
    def _delete_batch(self, page):
        # Azure Blob Service has no concept of mass-delete, so we must nuke
        # each blob one-by-one...
        for blob in page:
            self.wabs_conn.delete_blob(self.container, blob.name)

########NEW FILE########
__FILENAME__ = wabs_worker
"""
WAL-E Windows Azure Blob Service workers

These are functions that are amenable to be called from other modules,
with the intention that they are used in gevent greenlets.

"""
import gevent
import re

from wal_e import log_help
from wal_e import storage
from wal_e.blobstore import wabs
from wal_e.pipeline import get_download_pipeline
from wal_e.piper import PIPE
from wal_e.retries import retry
from wal_e.tar_partition import TarPartition
from wal_e.worker.base import _BackupList, _DeleteFromContext
from wal_e.worker.base import generic_weird_key_hint_message
from wal_e.worker.wabs.wabs_deleter import Deleter

logger = log_help.WalELogger(__name__)


class TarPartitionLister(object):
    def __init__(self, wabs_conn, layout, backup_info):
        self.wabs_conn = wabs_conn
        self.layout = layout
        self.backup_info = backup_info

    def __iter__(self):
        prefix = self.layout.basebackup_tar_partition_directory(
            self.backup_info)

        blob_list = self.wabs_conn.list_blobs(self.layout.store_name(),
                                              prefix='/' + prefix)
        for blob in blob_list.blobs:
            url = 'wabs://{container}/{name}'.format(
                container=self.layout.store_name(), name=blob.name)
            name_last_part = blob.name.rsplit('/', 1)[-1]
            match = re.match(storage.VOLUME_REGEXP, name_last_part)
            if match is None:
                logger.warning(
                    msg='unexpected key found in tar volume directory',
                    detail=('The unexpected key is stored at "{0}".'
                            .format(url)),
                    hint=generic_weird_key_hint_message)
            else:
                yield name_last_part


class BackupFetcher(object):
    def __init__(self, wabs_conn, layout, backup_info, local_root, decrypt):
        self.wabs_conn = wabs_conn
        self.layout = layout
        self.local_root = local_root
        self.backup_info = backup_info
        self.decrypt = decrypt

    @retry()
    def fetch_partition(self, partition_name):
        part_abs_name = self.layout.basebackup_tar_partition(
            self.backup_info, partition_name)

        logger.info(
            msg='beginning partition download',
            detail=('The partition being downloaded is {0}.'
                    .format(partition_name)),
            hint='The absolute S3 key is {0}.'.format(part_abs_name))

        url = 'wabs://{ctr}/{path}'.format(ctr=self.layout.store_name(),
                                           path=part_abs_name)
        with get_download_pipeline(PIPE, PIPE, self.decrypt) as pl:
            g = gevent.spawn(wabs.write_and_return_error,
                             url, self.wabs_conn, pl.stdin)
            TarPartition.tarfile_extract(pl.stdout, self.local_root)

            # Raise any exceptions from self._write_and_close
            exc = g.get()
            if exc is not None:
                raise exc


class BackupList(_BackupList):

    def _backup_detail(self, blob):
        return self.conn.get_blob(self.layout.store_name(), blob.name)

    def _backup_list(self, prefix):
        blob_list = self.conn.list_blobs(self.layout.store_name(),
                                         prefix='/' + prefix)
        return blob_list.blobs


class DeleteFromContext(_DeleteFromContext):

    def __init__(self, wabs_conn, layout, dry_run):
        super(DeleteFromContext, self).__init__(wabs_conn, layout, dry_run)

        if not dry_run:
            self.deleter = Deleter(self.conn, self.layout.store_name())
        else:
            self.deleter = None

    def _container_name(self, key):
        return self.layout.store_name()

    def _backup_list(self, prefix):
        blob_list = self.conn.list_blobs(self.layout.store_name(),
                                         prefix='/' + prefix)
        return blob_list.blobs

########NEW FILE########
__FILENAME__ = worker_util
import tempfile
import time

from wal_e import pipebuf
from wal_e import storage
from wal_e.blobstore import get_blobstore
from wal_e import pipeline


def uri_put_file(creds, uri, fp, content_encoding=None):
    blobstore = get_blobstore(storage.StorageLayout(uri))
    return blobstore.uri_put_file(creds, uri, fp,
                                  content_encoding=content_encoding)


def do_lzop_put(creds, url, local_path, gpg_key):
    """
    Compress and upload a given local path.

    :type url: string
    :param url: A (s3|wabs)://bucket/key style URL that is the destination

    :type local_path: string
    :param local_path: a path to a file to be compressed

    """
    assert url.endswith('.lzo')
    blobstore = get_blobstore(storage.StorageLayout(url))

    with tempfile.NamedTemporaryFile(
            mode='r+b', bufsize=pipebuf.PIPE_BUF_BYTES) as tf:
        with pipeline.get_upload_pipeline(
                open(local_path, 'r'), tf, gpg_key=gpg_key):
            pass

        tf.flush()

        clock_start = time.time()
        tf.seek(0)
        k = blobstore.uri_put_file(creds, url, tf)
        clock_finish = time.time()

        kib_per_second = format_kib_per_second(
            clock_start, clock_finish, k.size)

        return kib_per_second


def do_lzop_get(creds, url, path, decrypt):
    """
    Get and decompress an S3 or WABS URL

    This streams the content directly to lzop; the compressed version
    is never stored on disk.

    """
    blobstore = get_blobstore(storage.StorageLayout(url))
    return blobstore.do_lzop_get(creds, url, path, decrypt)


def format_kib_per_second(start, finish, amount_in_bytes):
    try:
        return '{0:02g}'.format((amount_in_bytes / 1024) / (finish - start))
    except ZeroDivisionError:
        return 'NaN'

########NEW FILE########
