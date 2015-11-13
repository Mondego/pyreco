__FILENAME__ = collectstatic
# -*- coding: utf-8 -*-

from __future__ import with_statement, unicode_literals
from optparse import make_option
import hashlib
import datetime

from django.conf import settings
from django.contrib.staticfiles.management.commands import collectstatic
from django.core.cache import get_cache
from django.core.files.storage import FileSystemStorage
from django.core.management.base import CommandError
from django.utils.encoding import smart_str

try:
    from django.utils.six.moves import input as _input
except ImportError:
    _input = raw_input

cache = get_cache(getattr(settings, "COLLECTFAST_CACHE", "default"))


class Command(collectstatic.Command):
    option_list = collectstatic.Command.option_list + (
        make_option(
            '--ignore-etag', action="store_true", dest="ignore_etag",
            default=False, help="Disable Collectfast."),
    )

    lookups = None
    cache_key_prefix = 'collectfast_asset_'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

        self.storage.preload_metadata = True

        if getattr(settings, 'AWS_PRELOAD_METADATA', False) is not True:
            self._pre_setup_log(
                "----> WARNING!\nCollectfast does not work properly without "
                "`AWS_PRELOAD_METADATA` set to `True`.\nOverriding "
                "`storage.preload_metadata` and continuing.")

    def set_options(self, **options):
        self.ignore_etag = options.pop('ignore_etag', False)
        if self.ignore_etag:
            self.collectfast_enabled = False
        else:
            self.collectfast_enabled = getattr(settings, "COLLECTFAST_ENABLED", True)
        super(Command, self).set_options(**options)

    def _pre_setup_log(self, message):
        print(message)

    def collect(self):
        """Override collect method to track time"""

        self.num_skipped_files = 0
        start = datetime.datetime.now()
        ret = super(Command, self).collect()
        self.collect_time = str(datetime.datetime.now() - start)
        return ret

    def get_cache_key(self, path):
        # Python 2/3 support for path hashing
        try:
            path_hash = hashlib.md5(path).hexdigest()
        except TypeError:
            path_hash = hashlib.md5(path.encode('utf-8')).hexdigest()
        return self.cache_key_prefix + path_hash

    def get_storage_lookup(self, path):
        return self.storage.bucket.lookup(path)

    def get_lookup(self, path):
        """Get lookup from local dict, cache or S3 — in that order"""

        if self.lookups is None:
            self.lookups = {}

        if path not in self.lookups:
            cache_key = self.get_cache_key(path)
            cached = cache.get(cache_key, False)

            if cached is False:
                self.lookups[path] = self.get_storage_lookup(path)
                cache.set(cache_key, self.lookups[path])
            else:
                self.lookups[path] = cached

        return self.lookups[path]

    def destroy_lookup(self, path):
        if self.lookups is not None and path in self.lookups:
            del self.lookups[path]
        cache.delete(self.get_cache_key(path))

    def get_file_hash(self, storage, path):
        contents = storage.open(path).read()
        file_hash = '"%s"' % hashlib.md5(contents).hexdigest()
        return file_hash

    def copy_file(self, path, prefixed_path, source_storage):
        """
        Attempt to generate an md5 hash of the local file and compare it with
        the S3 version's hash before copying the file.

        """
        if self.collectfast_enabled and not self.dry_run:
            normalized_path = self.storage._normalize_name(prefixed_path)
            try:
                storage_lookup = self.get_lookup(normalized_path)
                local_etag = self.get_file_hash(source_storage, path)

                # Compare hashes and skip copying if matching
                if (hasattr(storage_lookup, 'etag') and
                        storage_lookup.etag == local_etag):
                    self.log(
                        "Skipping '%s' based on matching file hashes" % path,
                        level=2)
                    self.num_skipped_files += 1
                    return False
                else:
                    self.log("Hashes did not match", level=2)
            except Exception as e:
                # Ignore errors and let super Command handle it
                self.stdout.write(smart_str(
                    "Ignored error in Collectfast:\n%s\n--> Continuing using "
                    "default collectstatic." % e.message))

            # Invalidate cached versions of lookup if copy is done
            self.destroy_lookup(normalized_path)

        return super(Command, self).copy_file(
            path, prefixed_path, source_storage)

    def delete_file(self, path, prefixed_path, source_storage):
        """Override delete_file to skip modified time and exists lookups"""
        if not self.collectfast_enabled:
            return super(Command, self).delete_file(
                    path, prefixed_path, source_storage)
        if self.dry_run:
            self.log("Pretending to delete '%s'" % path)
        else:
            self.log("Deleting '%s'" % path)
            self.storage.delete(prefixed_path)
        return True

    def handle_noargs(self, **options):
        self.set_options(**options)
        # Warn before doing anything more.
        if (isinstance(self.storage, FileSystemStorage) and
                self.storage.location):
            destination_path = self.storage.location
            destination_display = ':\n\n    %s' % destination_path
        else:
            destination_path = None
            destination_display = '.'

        if self.clear:
            clear_display = 'This will DELETE EXISTING FILES!'
        else:
            clear_display = 'This will overwrite existing files!'

        if self.interactive:
            confirm = _input("""
You have requested to collect static files at the destination
location as specified in your settings%s

%s
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """
% (destination_display, clear_display))
            if confirm != 'yes':
                raise CommandError("Collecting static files cancelled.")

        collected = self.collect()
        modified_count = len(collected['modified'])
        unmodified_count = len(collected['unmodified'])
        post_processed_count = len(collected['post_processed'])

        if self.verbosity >= 1:
            template = ("Collected static files in %(collect_time)s."
                        "\nSkipped %(num_skipped)i already synced files."
                        "\n%(modified_count)s %(identifier)s %(action)s"
                        "%(destination)s%(unmodified)s%(post_processed)s.\n")
            summary = template % {
                'modified_count': modified_count,
                'identifier': 'static file' + (modified_count != 1 and 's' or ''),
                'action': self.symlink and 'symlinked' or 'copied',
                'destination': (destination_path and " to '%s'"
                                % destination_path or ''),
                'unmodified': (collected['unmodified'] and ', %s unmodified'
                               % unmodified_count or ''),
                'post_processed': (collected['post_processed'] and
                                   ', %s post-processed'
                                   % post_processed_count or ''),
                'num_skipped': self.num_skipped_files,
                'collect_time': self.collect_time,
            }
            self.stdout.write(smart_str(summary))

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = test_command
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from unittest import TestCase
from mock import patch
from os.path import join

from django.core.files.storage import Storage, FileSystemStorage
from django.core.files.base import ContentFile
from django.conf import settings

from ..management.commands.collectstatic import Command, cache


class BotolikeStorage(Storage):
    location = None

    def _normalize_name(self, path):
        if self.location is not None:
            path = join(self.location, path)
        return path


class CollectfastTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.path = '.collectfast-test-file.txt'
        self.storage = FileSystemStorage(location='./')

    def get_command(self, *args, **kwargs):
        return Command(*args, **kwargs)

    def tearDown(self):
        self.storage.delete(self.path)


class TestCommand(CollectfastTestCase):
    @patch("collectfast.management.commands.collectstatic.collectstatic"
           ".Command.collect")
    def test_collect(self, mocked_super):
        command = self.get_command()
        command.collect()
        self.assertEqual(command.num_skipped_files, 0)
        self.assertIsInstance(command.collect_time, str)

    def test_get_cache_key(self):
        command = self.get_command()
        cache_key = command.get_cache_key('/some/random/path')
        prefix_len = len(command.cache_key_prefix)
        self.assertTrue(cache_key.startswith(command.cache_key_prefix))
        self.assertEqual(32 + prefix_len, len(cache_key))

    @patch("collectfast.management.commands.collectstatic.cache.get")
    @patch("collectfast.management.commands.collectstatic.Command"
           ".get_storage_lookup")
    def mock_get_lookup(self, path, cached_value, mocked_lookup, mocked_cache):
        mocked_lookup.return_value = 'a fresh lookup'
        mocked_cache.return_value = cached_value
        command = self.get_command()
        ret_val = command.get_lookup(path)
        return ret_val, mocked_lookup, mocked_cache

    def get_fresh_lookup(self, path):
        return self.mock_get_lookup(path, False)

    def get_cached_lookup(self, path):
        return self.mock_get_lookup(path, 'a cached lookup')

    def test_get_lookup(self):
        path = '/some/unique/path'
        cache_key = self.get_command().get_cache_key(path)

        # Assert storage lookup is hit and cache is populated
        ret_val, mocked_lookup, mocked_cache = self.get_fresh_lookup(path)
        mocked_lookup.assert_called_once_with(path)
        self.assertEqual(ret_val, 'a fresh lookup')
        self.assertEqual(cache.get(cache_key), 'a fresh lookup')

        # Assert storage is not hit, but cache is
        ret_val, mocked_lookup, mocked_cache = self.get_cached_lookup(path)
        self.assertEqual(mocked_lookup.call_count, 0)
        self.assertEqual(mocked_cache.call_count, 1)
        self.assertEqual(ret_val, 'a cached lookup')

    @patch("collectfast.management.commands.collectstatic.Command"
           ".get_storage_lookup")
    def test_destroy_lookup(self, mocked_lookup):
        mocked_lookup.return_value = 'a fake lookup'
        c = self.get_command()
        path = '/another/unique/path'
        cache_key = c.get_cache_key(path)
        c.get_lookup(path)
        self.assertEqual(cache.get(cache_key), mocked_lookup.return_value)
        self.assertEqual(c.lookups[path], mocked_lookup.return_value)

        c.destroy_lookup(path)
        self.assertEqual(cache.get(cache_key, 'empty'), 'empty')
        self.assertNotIn(path, c.lookups)


class TestGetFileHash(CollectfastTestCase):
    def test_get_file_hash(self):
        content = 'this is some content to be hashed'
        expected_hash = '"16e71fd2be8be2a3a8c0be7b9aab6c04"'
        c = self.get_command()

        self.storage.save(self.path, ContentFile(content))
        file_hash = c.get_file_hash(self.storage, self.path)
        self.assertEqual(file_hash, expected_hash)

        self.storage.delete(self.path)

        self.storage.save(self.path, ContentFile('some nonsense'))
        file_hash = c.get_file_hash(self.storage, self.path)
        self.assertNotEqual(file_hash, expected_hash)


class TestCopyFile(CollectfastTestCase):
    @patch("collectfast.management.commands.collectstatic.collectstatic.Command"
           ".copy_file")
    @patch("collectfast.management.commands.collectstatic.Command.get_lookup")
    def call_copy_file(self, mocked_lookup, mocked_copy_file_super, **kwargs):
        options = {
            "interactive": False,
            "post_process": False,
            "dry_run": False,
            "clear": False,
            "link": False,
            "ignore_patterns": [],
            "use_default_ignore_patterns": True}
        options.update(kwargs)
        path = options.pop('path', '/a/sweet/path')

        if 'lookup_hash' in options:
            class FakeLookup:
                etag = options.pop('lookup_hash')
            mocked_lookup.return_value = FakeLookup()

        c = self.get_command()
        c.storage = options.pop('storage', BotolikeStorage())
        c.set_options(**options)
        c.num_skipped_files = 0
        ret_val = c.copy_file(path, path, c.storage)
        return ret_val, mocked_copy_file_super, mocked_lookup

    def test_respect_flags(self):
        """`copy_file` respects --ignore_etag and --dry_run flags"""
        path = '/a/sweet/path'
        storage = BotolikeStorage()

        ret_val, super_mock, lookup_mock = self.call_copy_file(
            path=path, storage=storage, ignore_etag=True)
        self.assertEqual(lookup_mock.call_count, 0)

        ret_val, super_mock, lookup_mock = self.call_copy_file(
            path=path, storage=storage, dry_run=True)
        self.assertEqual(lookup_mock.call_count, 0)

    @patch("collectfast.management.commands.collectstatic.Command"
           ".get_file_hash")
    @patch("collectfast.management.commands.collectstatic.Command"
           ".destroy_lookup")
    def test_calls_super(self, mock_destroy_lookup, mock_get_file_hash):
        """`copy_file` properly calls super method"""
        path = '/a/sweet/path'
        storage = BotolikeStorage()

        ret_val, super_mock, lookup_mock = self.call_copy_file(
            path=path, storage=storage)
        super_mock.assert_called_once_with(path, path, storage)
        self.assertFalse(ret_val is False)
        mock_destroy_lookup.assert_called_once_with(path)

    @patch("collectfast.management.commands.collectstatic.Command"
           ".get_file_hash")
    def test_skips(self, mock_get_file_hash):
        """
        Returns False and increments self.num_skipped_files if matching
        hashes
        """
        # mock get_file_hash and lookup to return the same hashes
        mock_hash = 'thisisafakehash'
        mock_get_file_hash.return_value = mock_hash

        storage = BotolikeStorage()

        ret_val, super_mock, lookup_mock = self.call_copy_file(
            path=self.path, storage=storage, lookup_hash=mock_hash)
        self.assertFalse(ret_val)
        self.assertEqual(super_mock.call_count, 0)


class TestAwsPreloadMetadata(CollectfastTestCase):
    def setUp(self):
        super(TestAwsPreloadMetadata, self).setUp()
        settings.AWS_PRELOAD_METADATA = False

    def tearDown(self):
        super(TestAwsPreloadMetadata, self).tearDown()
        settings.AWS_PRELOAD_METADATA = True

    @patch(
        "collectfast.management.commands.collectstatic.Command._pre_setup_log")
    def test_always_true(self, _mock_log):
        c = self.get_command()
        self.assertTrue(c.storage.preload_metadata)

    @patch(
        "collectfast.management.commands.collectstatic.Command._pre_setup_log")
    def test_log(self, mock_log):
        self.get_command()
        mock_log.assert_called_once_with(
            "----> WARNING!\nCollectfast does not work properly without "
            "`AWS_PRELOAD_METADATA` set to `True`.\nOverriding "
            "`storage.preload_metadata` and continuing.")

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import os
import sys

from optparse import OptionParser

from django.conf import settings
from django.core.management import call_command


def main():
    parser = OptionParser()
    parser.add_option("--DATABASE_ENGINE", dest="DATABASE_ENGINE", default="sqlite3")
    parser.add_option("--DATABASE_NAME", dest="DATABASE_NAME", default="")
    parser.add_option("--DATABASE_USER", dest="DATABASE_USER", default="")
    parser.add_option("--DATABASE_PASSWORD", dest="DATABASE_PASSWORD", default="")
    parser.add_option("--TEST", dest="TEST_SUITE", default=None)

    options, args = parser.parse_args()

    # check for app in args
    app_path = 'collectfast'
    parent_dir, app_name = os.path.split(app_path)
    sys.path.insert(0, parent_dir)

    settings.configure(**{
        "DATABASES": {
            'default': {
                "ENGINE": 'django.db.backends.%s' % options.DATABASE_ENGINE,
                "NAME": options.DATABASE_NAME,
                "USER": options.DATABASE_USER,
                "PASSWORD": options.DATABASE_PASSWORD,
            }
        },
        "CACHES": {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'test-collectfast'
            }
        },
        "ROOT_URLCONF": app_name + ".urls",
        "TEMPLATE_LOADERS": (
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
            "django.template.loaders.eggs.Loader",
        ),
        "TEMPLATE_DIRS": (
            os.path.join(os.path.dirname(__file__),
                         "collectfast/templates"),
        ),
        "INSTALLED_APPS": (
            "django.contrib.auth",
            "django.contrib.contenttypes",
            app_name,
        ),
        "STATIC_URL": "/staticfiles/",
        "STATIC_ROOT": "./",

        "AWS_PRELOAD_METADATA": True,
    })

    if options.TEST_SUITE is not None:
        test_arg = "%s.%s" % (app_name, options.TEST_SUITE)
    else:
        test_arg = app_name

    call_command("test", test_arg)

if __name__ == "__main__":
    main()

########NEW FILE########
