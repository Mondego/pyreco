__FILENAME__ = bucket
from boto.s3.bucket import Bucket as boto_Bucket
from boto.s3.key import Key as boto_Key

import mimicdb
from mimicdb.s3.key import Key


class Bucket(boto_Bucket):
    def __init__(self, *args, **kwargs):
        """
        Sets the base class for key objects created in the bucket to the MimicDB
        class.
        """
        kwargs['key_class'] = Key
        super(Bucket, self).__init__(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        """
        __iter__ can not be forced to check S3, so it returns an iterable of
        keys from MimicDB.
        """
        return self.list()

    def get_key(self, *args, **kwargs):
        """
        Checks if a key exists in the bucket set. Returns None if not. Uses
        the headers hack to pass 'force' to internal method: _get_key_internal()
        """
        if kwargs.pop('force', None):
            headers = kwargs.get('headers', {})
            headers['force'] = 'True'
            kwargs['headers'] = headers

        return super(Bucket, self).get_key(*args, **kwargs)

    def _get_key_internal(self, *args, **kwargs):
        """
        Internal method for checking if a key exists in the bucket set. Returns
        None if not. If 'force' is in the headers, it checks S3 for the key.
        """
        if 'force' in kwargs.get('headers', args[1] if len(args) > 1 else {}) or kwargs.pop('force', None):
            return super(Bucket, self)._get_key_internal(*args, **kwargs)

        key = None

        if mimicdb.redis.sismember(self.name, args[0]):
            key = Key(self)

        return key, None

    def delete_keys(self, *args, **kwargs):
        """
        Remove each key or key name in an iterable from the bucket set.
        """
        ikeys = iter(kwargs.get('keys', args[0] if args else []))

        while True:
            try:
                key = ikeys.next()
            except StopIteration:
                break

            if isinstance(key, basestring):
                mimicdb.redis.srem(self.name, key)
            elif isinstance(key, boto_Key) or isinstance(key, Key):
                mimicdb.redis.srem(self.name, key.name)

        return super(Bucket, self).delete_keys(*args, **kwargs)

    def _delete_key_internal(self, *args, **kwargs):
        """
        Remove key name from bucket set before deleting it.
        """
        key = kwargs.get('key_name', args[0] if args else None)

        if key:
            mimicdb.redis.srem(self.name, key)

        return super(Bucket, self)._delete_key_internal(*args, **kwargs)

    def list(self, *args, **kwargs):
        """
        Returns an iterable of keys in the bucket set. If 'force' is passed,
        it passes it to the internal function using the headers hack.

        """
        if kwargs.pop('force', None):
            headers = kwargs.get('headers', {})
            headers['force'] = 'True'
            kwargs['headers'] = headers

            for key in super(Bucket, self).list(*args, **kwargs):
                yield key

        else:
            prefix = kwargs.get('prefix', args[0] if args else '')

            for key in mimicdb.redis.smembers(self.name):
                if key.startswith(prefix):
                    yield Key(self, key)

    def _get_all(self, *args, **kwargs):
        """
        Internal method for listing keys in a bucket set. If 'force' is in the
        headers, it retrieves the list of keys from S3.

        """
        if 'force' in kwargs.get('headers', args[2] if len(args) > 2 else {}) or kwargs.pop('force', None):
            headers = kwargs.get('headers', {})

            if headers == dict():
                kwargs.pop('headers', None)
            else:
                kwargs['headers'] = headers

            return super(Bucket, self)._get_all(*args, **kwargs)

        prefix = kwargs.get('prefix', '')

        return list(self.list(prefix=prefix))


    def sync(self):
        """
        Syncs the bucket with S3. The bucket set is wiped before being re-populated.
        """
        mimicdb.redis.sadd('mimicdb', self.name)

        for key in mimicdb.redis.smembers(self.name):
            mimicdb.redis.delete('%(bucket)s:%(key)s:size' % dict(bucket=self.name, key=key))

        mimicdb.redis.delete(self.name)

        for key in self.list(force=True):
            mimicdb.redis.sadd(self.name, key.name)
            mimicdb.redis.set((key.base + ':size') % dict(bucket=self.name, key=key.name), key.size)

########NEW FILE########
__FILENAME__ = connection
from boto.s3.connection import S3Connection as boto_S3Connection
from boto.exception import S3ResponseError

import mimicdb
from mimicdb.s3.bucket import Bucket


class S3Connection(boto_S3Connection):
    def __init__(self, *args, **kwargs):
        """
        Sets the base class for bucket objects created in the connection to the
        MimicDB class.
        """
        kwargs['bucket_class'] = Bucket
        super(S3Connection, self).__init__(*args, **kwargs)


    def get_all_buckets(self, *args, **kwargs):
        """
        Retrieve buckets from the 'mimicdb' set. Passing 'force' checks S3 for
        the list of buckets.
        """
        if kwargs.pop('force', None):
            buckets = super(S3Connection, self).get_all_buckets(*args, **kwargs)

            for bucket in buckets:
                mimicdb.redis.sadd('mimicdb', bucket.name)

            return buckets

        return [Bucket(self, bucket) for bucket in mimicdb.redis.smembers('mimicdb')]


    def get_bucket(self, *args, **kwargs):
        """
        Retrieves a bucket from the 'mimicdb' set if it exists. Simulates an
        S3ResponseError if the bucket does not exist (and validate is passed).
        """
        if kwargs.pop('force', None):
            bucket = super(S3Connection, self).get_bucket(*args, **kwargs)

            mimicdb.redis.sadd('mimicdb', bucket.name)

            return bucket

        name = kwargs.get('bucket_name', args[0] if args else None)
        validate = kwargs.get('validate', args[0] if args else True)

        if not name:
            raise ValueError

        if mimicdb.redis.sismember('mimicdb', name):
            return Bucket(name)
        else:
            if validate:
                raise S3ResponseError(404, 'NoSuchBucket')


    def create_bucket(self, *args, **kwargs):
        """
        Add the bucket name to the mimicdb set.
        """
        bucket = kwargs.get('bucket_name', args[0] if args else None)

        if bucket:
            mimicdb.redis.sadd('mimicdb', bucket)

        return super(S3Connection, self).create_bucket(*args, **kwargs)


    def delete_bucket(self, *args, **kwargs):
        """
        Deletes the bucket on S3 before removing it from the mimicdb set.
        If the delete fails (usually because the bucket is not empty), it does
        not remove the bucket from the set.
        """
        super(S3Connection, self).delete_bucket(*args, **kwargs)

        bucket = kwargs.get('bucket_name', args[0] if args else None)

        if bucket:
            mimicdb.redis.srem('mimicdb', bucket)


    def sync(self, bucket=None):
        """
        Syncs either a bucket or the entire connection.

        Bucket names are stored in a set named 'mimicdb'.
        Key names are stored in a set with the same name as the bucket.

        Key metadata is in the format 'bucket:key:size'.

        Syncing overrides the MimicDB functionality and forces API calls to S3.

        Calling sync() populates the database with the current state of S3.
        When syncing the entire connection, the mimicdb set and all bucket sets
        are wiped before being re-populated. When syncing a bucket, the bucket set
        is wiped before it is re-populated.
        """
        if bucket:
            bucket = self.get_bucket(bucket)

            mimicdb.redis.sadd('mimicdb', bucket.name)

            for key in mimicdb.redis.smembers(bucket.name):
                mimicdb.redis.delete('%(bucket)s:%(key)s:size' % dict(bucket=bucket, key=key))

            mimicdb.redis.delete(bucket.name)

            for key in bucket.list(force=True):
                mimicdb.redis.sadd(bucket.name, key.name)
                mimicdb.redis.set((key.base + ':size') % dict(bucket=bucket.name, key=key.name), key.size)

        else:
            for bucket in mimicdb.redis.smembers('mimicdb'):
                for key in mimicdb.redis.smembers(bucket):
                    mimicdb.redis.delete('%(bucket)s:%(key)s:size' % dict(bucket=bucket, key=key))

                mimicdb.redis.delete(bucket)

            mimicdb.redis.delete('mimicdb')

            buckets = self.get_all_buckets(force=True)

            for bucket in buckets:
                mimicdb.redis.sadd('mimicdb', bucket.name)

                for key in bucket.list(force=True):
                    mimicdb.redis.sadd(bucket.name, key.name)
                    mimicdb.redis.set((key.base + ':size') % dict(bucket=bucket.name, key=key.name), key.size)

########NEW FILE########
__FILENAME__ = key
from boto.s3.key import Key as boto_Key

import mimicdb


class Key(boto_Key):
    def __init__(self, *args, **kwargs):
        """
        Adds an attribute 'base' for key metadata. Stores the key in the bucket
        if the key name is already set, otherwise nothing is stored.
        """
        self.base = '%(bucket)s:%(key)s'
        self.bucket = kwargs.get('bucket', args[0] if args else None)
        self.name = kwargs.get('name', args[1] if len(args) > 1 else None)

        if self.name and self.bucket:
            mimicdb.redis.sadd(self.bucket.name, self.name)

        super(Key, self).__init__(*args, **kwargs)


    def _get_key(self):
        return super(Key, self).name


    def _set_key(self, *args, **kwargs):
        value = kwargs.get('value', args[0])

        mimicdb.redis.sadd(self.bucket.name, value)

        return super(Key, self)._set_key(*args, **kwargs)


    key = property(_get_key, _set_key)


    def _send_file_internal(self, *args, **kwargs):
        """
        Saves the file size when the key contents are set using:
         - set_contents_from_file
         - set_contents_from_filename
         - set_contents_from_string
        """
        key_size = super(Key, self)._send_file_internal(*args, **kwargs)
        mimicdb.redis.set((self.base + ':size') % dict(bucket=self.bucket.name, key=self.name), key_size)
        return key_size

########NEW FILE########
