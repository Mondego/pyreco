__FILENAME__ = cache
from less.settings import LESS_MTIME_DELAY
from django.core.cache import cache
from django.utils.encoding import smart_str
from hashlib import md5
import os.path
import socket


def get_hexdigest(plaintext, length=None):
    digest = md5(smart_str(plaintext)).hexdigest()
    if length:
        return digest[:length]
    return digest


def get_cache_key(key):
    return ("django_less.%s.%s" % (socket.gethostname(), key))


def get_mtime_cachekey(filename):
    return get_cache_key("mtime.%s" % get_hexdigest(filename))


def get_mtime(filename):
    if LESS_MTIME_DELAY:
        key = get_mtime_cachekey(filename)
        mtime = cache.get(key)
        if mtime is None:
            mtime = os.path.getmtime(filename)
            cache.set(key, mtime, LESS_MTIME_DELAY)
        return mtime
    return os.path.getmtime(filename)


def get_hashed_mtime(filename, length=12):
    try:
        filename = os.path.realpath(filename)
        mtime = str(int(get_mtime(filename)))
    except OSError:
        return None
    return get_hexdigest(mtime, length)

########NEW FILE########
__FILENAME__ = devmode
from less.utils import compile_less, logger
from less.settings import LESS_DEVMODE_WATCH_DIRS, LESS_OUTPUT_DIR, LESS_DEVMODE_EXCLUDE
from django.conf import settings
import os
import re
import sys
import time
import threading


try:
    STATIC_ROOT = settings.STATIC_ROOT
except AttributeError:
    STATIC_ROOT = settings.MEDIA_ROOT


WATCHED_FILES = {}
LESS_IMPORT_RE = re.compile(r"""@import\s+['"](.+?\.less)['"]\s*;""")


def daemon():

    while True:
        to_be_compiled = set()
        for watched_dir in LESS_DEVMODE_WATCH_DIRS:
            for root, dirs, files in os.walk(watched_dir):
                for filename in filter(lambda f: f.endswith(".less"), files):
                    filename = os.path.join(root, filename)
                    f = os.path.relpath(filename, STATIC_ROOT)
                    if f in LESS_DEVMODE_EXCLUDE:
                        continue
                    mtime = os.path.getmtime(filename)

                    if f not in WATCHED_FILES:
                        WATCHED_FILES[f] = [None, set()]

                    if WATCHED_FILES[f][0] != mtime:
                        WATCHED_FILES[f][0] = mtime
                        # Look for @import statements to update dependecies
                        for line in open(filename):
                            for imported in LESS_IMPORT_RE.findall(line):
                                imported = os.path.relpath(os.path.join(os.path.dirname(filename), imported), STATIC_ROOT)
                                if imported not in WATCHED_FILES:
                                    WATCHED_FILES[imported] = [None, set([f])]
                                else:
                                    WATCHED_FILES[imported][1].add(f)

                        to_be_compiled.add(f)
                        importers = WATCHED_FILES[f][1]
                        while importers:
                            for importer in importers:
                                to_be_compiled.add(importer)
                            importers = WATCHED_FILES[importer][1]

        for less_path in to_be_compiled:
            full_path = os.path.join(STATIC_ROOT, less_path)
            base_filename = os.path.split(less_path)[-1][:-5]
            output_directory = os.path.join(STATIC_ROOT, LESS_OUTPUT_DIR, os.path.dirname(less_path))
            output_path = os.path.join(output_directory, "%s.css" % base_filename)
            if isinstance(full_path, unicode):
                filesystem_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()
                full_path = full_path.encode(filesystem_encoding)

            compile_less(full_path, output_path, less_path)
            logger.debug("Compiled: %s" % less_path)

        time.sleep(1)


def start_daemon():
    thread = threading.Thread(target=daemon)
    thread.daemon = True
    thread.start()

########NEW FILE########
__FILENAME__ = finders
from less.storage import LessFileStorage
from django.contrib.staticfiles.finders import BaseStorageFinder


class LessFinder(BaseStorageFinder):
    """
    A staticfiles finder that looks in LESS_ROOT
    for compiled files, to be used during development
    with staticfiles development file server or during
    deployment.
    """
    storage = LessFileStorage

    def list(self, ignore_patterns):
        return []

########NEW FILE########
__FILENAME__ = models
from less.settings import LESS_DEVMODE


if LESS_DEVMODE:
    # Run the devmode daemon if it's enabled.
    # We start it here because this file is auto imported by Django when
    # devserver is started.
    from less.devmode import start_daemon
    start_daemon()

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings


LESS_EXECUTABLE = getattr(settings, "LESS_EXECUTABLE", "lessc")
LESS_USE_CACHE = getattr(settings, "LESS_USE_CACHE", True)
LESS_CACHE_TIMEOUT = getattr(settings, "LESS_CACHE_TIMEOUT", 60 * 60 * 24 * 30) # 30 days
LESS_MTIME_DELAY = getattr(settings, "LESS_MTIME_DELAY", 10) # 10 seconds
LESS_ROOT = getattr(settings, "LESS_ROOT", getattr(settings, "STATIC_ROOT", getattr(settings, "MEDIA_ROOT")))
LESS_OUTPUT_DIR = getattr(settings, "LESS_OUTPUT_DIR", "LESS_CACHE")
LESS_OPTIONS = getattr(settings, "LESS_OPTIONS", [])
LESS_DEVMODE = getattr(settings, "LESS_DEVMODE", False)
LESS_DEVMODE_WATCH_DIRS = getattr(settings, "LESS_DEVMODE_WATCH_DIRS", [settings.STATIC_ROOT])
LESS_DEVMODE_EXCLUDE = getattr(settings, "LESS_DEVMODE_EXCLUDE", ())

########NEW FILE########
__FILENAME__ = storage
from django.core.files.storage import FileSystemStorage
from less.settings import LESS_ROOT


class LessFileStorage(FileSystemStorage):
    """
    Standard file system storage for files handled by django-less.

    The default for ``location`` is ``LESS_ROOT``
    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = LESS_ROOT
        super(LessFileStorage, self).__init__(location, base_url,
                                                *args, **kwargs)

########NEW FILE########
__FILENAME__ = less
from tempfile import NamedTemporaryFile
from ..cache import get_cache_key, get_hexdigest, get_hashed_mtime
from ..utils import compile_less
from ..settings import LESS_EXECUTABLE, LESS_USE_CACHE,\
    LESS_CACHE_TIMEOUT, LESS_ROOT, LESS_OUTPUT_DIR, LESS_DEVMODE,\
    LESS_DEVMODE_WATCH_DIRS
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.template.base import Library, Node, TemplateSyntaxError
import logging
import subprocess
import os
import sys


STATIC_ROOT = getattr(settings, "STATIC_ROOT", getattr(settings, "MEDIA_ROOT"))


logger = logging.getLogger("less")


register = Library()


class InlineLessNode(Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def compile(self, source):
        source_file = NamedTemporaryFile(delete=False)
        source_file.write(source)
        source_file.close()
        args = [LESS_EXECUTABLE, source_file.name]

        popen_kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if os.name == "nt":
            popen_kwargs["shell"] = True

        p = subprocess.Popen(args, **popen_kwargs)
        out, errors = p.communicate()
        os.remove(source_file.name)
        if out:
            return out.decode(settings.FILE_CHARSET)
        elif errors:
            return errors.decode(settings.FILE_CHARSET)

        return u""

    def render(self, context):
        output = self.nodelist.render(context)

        if LESS_USE_CACHE:
            cache_key = get_cache_key(get_hexdigest(output))
            cached = cache.get(cache_key, None)
            if cached is not None:
                return cached
            output = self.compile(output)
            cache.set(cache_key, output, LESS_CACHE_TIMEOUT)
            return output
        else:
            return self.compile(output)


@register.tag(name="inlineless")
def do_inlineless(parser, token):
    nodelist = parser.parse(("endinlineless",))
    parser.delete_first_token()
    return InlineLessNode(nodelist)


def less_paths(path):

    full_path = os.path.join(STATIC_ROOT, path)

    if settings.DEBUG and not os.path.exists(full_path):
        # while developing it is more confortable
        # searching for the less files rather then
        # doing collectstatics all the time
        full_path = finders.find(path)

        if full_path is None:
            raise TemplateSyntaxError("Can't find staticfile named: {}".format(path))

    file_name = os.path.split(path)[-1]
    output_dir = os.path.join(LESS_ROOT, LESS_OUTPUT_DIR, os.path.dirname(path))

    return full_path, file_name, output_dir


@register.simple_tag
def less(path):

    logger.info("processing file %s" % path)

    full_path, file_name, output_dir = less_paths(path)
    base_file_name = os.path.splitext(file_name)[0]

    if LESS_DEVMODE and any(map(lambda watched_dir: full_path.startswith(watched_dir), LESS_DEVMODE_WATCH_DIRS)):
        return os.path.join(os.path.dirname(path), "%s.css" % base_file_name)

    hashed_mtime = get_hashed_mtime(full_path)
    output_file = "%s-%s.css" % (base_file_name, hashed_mtime)
    output_path = os.path.join(output_dir, output_file)

    encoded_full_path = full_path
    if isinstance(full_path, unicode):
        filesystem_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()
        encoded_full_path = full_path.encode(filesystem_encoding)

    if not os.path.exists(output_path):
        compile_less(encoded_full_path, output_path, path)

        # Remove old files
        compiled_filename = os.path.split(output_path)[-1]
        for filename in os.listdir(output_dir):
            if filename.startswith(base_file_name) and filename != compiled_filename:
                os.remove(os.path.join(output_dir, filename))

    return os.path.join(LESS_OUTPUT_DIR, os.path.dirname(path), output_file)

########NEW FILE########
__FILENAME__ = django_settings
from django.conf.global_settings import *
import os

DEBUG = True

STATIC_ROOT = MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'static')
STATIC_URL = MEDIA_URL = "/static/"

STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__), 'staticfiles_dir'),
    ("prefix", os.path.join(os.path.dirname(__file__), 'staticfiles_dir_with_prefix')),
)

INSTALLED_APPS = (
    "less",
)

LESS_MTIME_DELAY = 2
LESS_OUTPUT_DIR = "LESS_CACHE"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        'less': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}

SECRET_KEY = "secret"

########NEW FILE########
__FILENAME__ = tests
# coding: utf-8
from unittest import main, TestCase
from django.http import HttpRequest
from django.template.base import Template
from django.template.context import RequestContext
from less import LessException
import os
import re
import time
import shutil


os.environ["DJANGO_SETTINGS_MODULE"] = "less.tests.django_settings"


class LessTestCase(TestCase):

    def setUp(self):
        from django.conf import settings as django_settings

        self.django_settings = django_settings

        output_dir = os.path.join(self.django_settings.MEDIA_ROOT,
                                  self.django_settings.LESS_OUTPUT_DIR)

        # Remove the output directory if it exists to start from scratch
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

    def _get_request_context(self):
        return RequestContext(HttpRequest())

    def test_inline_less(self):
        template = Template("""
        {% load less %}
        {% inlineless %}
            @the-border: 1px;
            #bordered {
                border: @the-border * 2;
            }
        {% endinlineless %}
        """)
        rendered = """#bordered {
  border: 2px;
}"""
        self.assertEqual(template.render(self._get_request_context()).strip(), rendered)

    def test_external_less(self):

        template = Template("""
        {% load less %}
        {% less "styles/test.less" %}
        """)
        compiled_filename_re = re.compile(r"LESS_CACHE/styles/test-[a-f0-9]{12}.css")
        compiled_filename = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename)))

        compiled_path = os.path.join(self.django_settings.MEDIA_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read().strip()
        compiled = """#header h1 {
  background-image: url('/static/images/header.png');
}"""
        self.assertEquals(compiled_content, compiled)

        # Change the modification time
        source_path = os.path.join(self.django_settings.MEDIA_ROOT, "styles/test.less")
        os.utime(source_path, None)

        # The modification time is cached so the compiled file is not updated
        compiled_filename_2 = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename_2)))
        self.assertEquals(compiled_filename, compiled_filename_2)

        # Wait to invalidate the cached modification time
        time.sleep(self.django_settings.LESS_MTIME_DELAY)

        # Now the file is re-compiled
        compiled_filename_3 = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename_3)))
        self.assertNotEquals(compiled_filename, compiled_filename_3)

        # Check that we have only one compiled file, old files should be removed

        compiled_file_dir = os.path.dirname(os.path.join(self.django_settings.MEDIA_ROOT,
                                                         compiled_filename_3))
        self.assertEquals(len(os.listdir(compiled_file_dir)), 1)

    def test_lookup_in_staticfiles_dirs(self):

        template = Template("""
        {% load less %}
        {% less "another_test.less" %}
        """)
        compiled_filename_re = re.compile(r"LESS_CACHE/another_test-[a-f0-9]{12}.css")
        compiled_filename = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename)))

        compiled_path = os.path.join(self.django_settings.STATIC_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read().strip()
        compiled = """#header-from-staticfiles-dir h1 {
  color: red;
}"""
        self.assertEquals(compiled_content, compiled)

        template = Template("""
        {% load less %}
        {% less "prefix/another_test.less" %}
        """)
        compiled_filename_re = re.compile(r"LESS_CACHE/prefix/another_test-[a-f0-9]{12}.css")
        compiled_filename = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename)))

        compiled_path = os.path.join(self.django_settings.STATIC_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read().strip()
        compiled = """#header-from-staticfiles-dir-with-prefix h1 {
  color: red;
}"""
        self.assertEquals(compiled_content, compiled)

    def test_non_ascii_content(self):

        template = Template("""
        {% load less %}
        {% less "styles/non-ascii.less" %}
        """)
        compiled_filename = template.render(self._get_request_context()).strip()
        compiled_path = os.path.join(self.django_settings.STATIC_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read().strip()
        compiled = """.external_link:first-child:before {
  content: "Zobacz także:";
  background: url('/static/styles/картинка.png');
}"""
        self.assertEquals(compiled_content, compiled)

    def test_imports(self):

        template = Template("""
        {% load less %}
        {% less "styles/import.less" %}
        """)
        compiled_filename = template.render(self._get_request_context()).strip()
        compiled_path = os.path.join(self.django_settings.STATIC_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read().strip()
        compiled = """h1 {
  color: red;
}"""
        self.assertEquals(compiled_content, compiled)

    def test_less_exception(self):
        template = Template("""
        {% load less %}
        {% less "styles/invalid.less" %}
        """)

        self.assertRaises(
            LessException,
            lambda: template.render(self._get_request_context())
        )


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = utils
from less import LessException
from less.settings import LESS_EXECUTABLE, LESS_ROOT, LESS_OUTPUT_DIR, \
        LESS_OPTIONS
from django.conf import settings
import logging
import urlparse
import re
import os
import subprocess


logger = logging.getLogger("less")


STATIC_URL = getattr(settings, "STATIC_URL", getattr(settings, "MEDIA_URL"))


class URLConverter(object):

    URL_PATTERN = re.compile(r'url\(([^\)]+)\)')

    def __init__(self, content, source_path):
        self.content = content
        self.source_dir = os.path.dirname(source_path)
        if not self.source_dir.endswith('/'):
            self.source_dir = self.source_dir + '/'

    def convert_url(self, matchobj):
        url = matchobj.group(1)
        url = url.strip(' \'"')
        if url.startswith(('http://', 'https://', '/', 'data:')):
            return "url('%s')" % url
        return "url('%s')" % urlparse.urljoin(self.source_dir, url)

    def convert(self):
        return self.URL_PATTERN.sub(self.convert_url, self.content)


def compile_less(input, output, less_path):

    less_root = os.path.join(LESS_ROOT, LESS_OUTPUT_DIR)
    if not os.path.exists(less_root):
        os.makedirs(less_root)

    args = [LESS_EXECUTABLE] + LESS_OPTIONS + [input]
    popen_kwargs = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if os.name == "nt":
        popen_kwargs["shell"] = True
    p = subprocess.Popen(args, **popen_kwargs)
    out, errors = p.communicate()

    if errors:
        logger.error(errors)
        raise LessException(errors)

    output_directory = os.path.dirname(output)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    compiled_css = URLConverter(
        out.decode(settings.FILE_CHARSET),
        os.path.join(STATIC_URL, less_path)
    ).convert()
    compiled_file = open(output, "w+")
    compiled_file.write(compiled_css.encode(settings.FILE_CHARSET))
    compiled_file.close()

########NEW FILE########
