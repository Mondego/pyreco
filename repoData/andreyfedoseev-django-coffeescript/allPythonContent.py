__FILENAME__ = cache
from coffeescript.settings import COFFEESCRIPT_MTIME_DELAY
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
    return ("django_coffescript.%s.%s" % (socket.gethostname(), key))


def get_mtime_cachekey(filename):
    return get_cache_key("mtime.%s" % get_hexdigest(filename))


def get_mtime(filename):
    if COFFEESCRIPT_MTIME_DELAY:
        key = get_mtime_cachekey(filename)
        mtime = cache.get(key)
        if mtime is None:
            mtime = os.path.getmtime(filename)
            cache.set(key, mtime, COFFEESCRIPT_MTIME_DELAY)
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
__FILENAME__ = finders
from coffeescript.storage import CoffeescriptFileStorage
from django.contrib.staticfiles.finders import BaseStorageFinder


class CoffeescriptFinder(BaseStorageFinder):
    """
    A staticfiles finder that looks in COFFEESCRIPT_ROOT
    for compiled files, to be used during development
    with staticfiles development file server or during
    deployment.
    """
    storage = CoffeescriptFileStorage

    def list(self, ignore_patterns):
        return []

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
import os


POSIX_COMPATIBLE = True if os.name == 'posix' else False
COFFEESCRIPT_EXECUTABLE = getattr(settings, "COFFEESCRIPT_EXECUTABLE", "coffee")
COFFEESCRIPT_USE_CACHE = getattr(settings, "COFFEESCRIPT_USE_CACHE", True)
COFFEESCRIPT_CACHE_TIMEOUT = getattr(settings, "COFFEESCRIPT_CACHE_TIMEOUT", 60 * 60 * 24 * 30) # 30 days
COFFEESCRIPT_MTIME_DELAY = getattr(settings, "COFFEESCRIPT_MTIME_DELAY", 10) # 10 seconds
COFFEESCRIPT_ROOT = getattr(settings, "COFFEESCRIPT_ROOT", getattr(settings, "STATIC_ROOT", getattr(settings, "MEDIA_ROOT")))
COFFEESCRIPT_OUTPUT_DIR = getattr(settings, "COFFEESCRIPT_OUTPUT_DIR", "COFFEESCRIPT_CACHE")

########NEW FILE########
__FILENAME__ = storage
from django.core.files.storage import FileSystemStorage
from coffeescript.settings import COFFEESCRIPT_ROOT


class CoffeescriptFileStorage(FileSystemStorage):
    """
    Standard file system storage for files handled by django-coffeescript.

    The default for ``location`` is ``COFFEESCRIPT_ROOT``
    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = COFFEESCRIPT_ROOT
        super(CoffeescriptFileStorage, self).__init__(location, base_url,
                                                *args, **kwargs)

########NEW FILE########
__FILENAME__ = coffeescript
from ..cache import get_cache_key, get_hexdigest, get_hashed_mtime
from django.contrib.staticfiles import finders
from ..settings import COFFEESCRIPT_EXECUTABLE, COFFEESCRIPT_USE_CACHE,\
    COFFEESCRIPT_CACHE_TIMEOUT, COFFEESCRIPT_ROOT, COFFEESCRIPT_OUTPUT_DIR,\
    POSIX_COMPATIBLE
from django.conf import settings
from django.core.cache import cache
from django.template.base import Library, Node, TemplateSyntaxError
import logging
import shlex
import subprocess
import os


STATIC_ROOT = getattr(settings, "STATIC_ROOT", getattr(settings, "MEDIA_ROOT"))


logger = logging.getLogger("coffeescript")


register = Library()


class InlineCoffeescriptNode(Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def compile(self, source):
        args = shlex.split(
            "%s -c -s -p" % COFFEESCRIPT_EXECUTABLE, posix=POSIX_COMPATIBLE
        )

        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        out, errors = p.communicate(source.encode("utf-8"))
        if out:
            return out.decode("utf-8")
        elif errors:
            return errors.decode("utf-8")

        return u""

    def render(self, context):
        output = self.nodelist.render(context)

        if COFFEESCRIPT_USE_CACHE:
            cache_key = get_cache_key(get_hexdigest(output))
            cached = cache.get(cache_key, None)
            if cached is not None:
                return cached
            output = self.compile(output)
            cache.set(cache_key, output, COFFEESCRIPT_CACHE_TIMEOUT)
            return output
        else:
            return self.compile(output)


@register.tag(name="inlinecoffeescript")
def do_inlinecoffeescript(parser, token):
    nodelist = parser.parse(("endinlinecoffeescript",))
    parser.delete_first_token()
    return InlineCoffeescriptNode(nodelist)


def coffeescript_paths(path):

    full_path = os.path.join(STATIC_ROOT, path)

    if settings.DEBUG and not os.path.exists(full_path):
        # while developing it is more confortable
        # searching for the coffeescript files rather then
        # doing collectstatics all the time
        full_path = finders.find(path)

        if full_path is None:
            raise TemplateSyntaxError("Can't find staticfile named: {}".format(path))

    file_name = os.path.split(path)[-1]
    output_dir = os.path.join(COFFEESCRIPT_ROOT, COFFEESCRIPT_OUTPUT_DIR, os.path.dirname(path))

    return full_path, file_name, output_dir


@register.simple_tag
def coffeescript(path):
    logger.info("processing file %s" % path)

    full_path, file_name, output_dir = coffeescript_paths(path)

    hashed_mtime = get_hashed_mtime(full_path)

    base_file_name = file_name.replace(".coffee","")

    output_file = "%s-%s.js" % (base_file_name, hashed_mtime)
    output_path = os.path.join(output_dir, output_file)

    if not os.path.exists(output_path):
        source_file = open(full_path)
        source = source_file.read()
        source_file.close()

        args = shlex.split(
            "%s -c -s -p" % COFFEESCRIPT_EXECUTABLE,
             posix=POSIX_COMPATIBLE
        )
        p = subprocess.Popen(args, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, errors = p.communicate(source)

        if errors:
            logger.error(errors)
            return path

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        compiled_file = open(output_path, "w+")
        compiled_file.write(out)
        compiled_file.close()

        # Remove old files
        compiled_filename = os.path.split(output_path)[-1]
        for filename in os.listdir(output_dir):
            if filename.startswith(base_file_name) and filename != compiled_filename:
                os.remove(os.path.join(output_dir, filename))

    return os.path.join(COFFEESCRIPT_OUTPUT_DIR, os.path.dirname(path), output_file)

########NEW FILE########
__FILENAME__ = django_settings
from django.conf.global_settings import *
import os

DEBUG = True

STATIC_ROOT = MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'static')

STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__), 'staticfiles_dir'),
    ("prefix", os.path.join(os.path.dirname(__file__), 'staticfiles_dir_with_prefix')),
)

INSTALLED_APPS = (
    "coffeescript",
)
COFFEESCRIPT_MTIME_DELAY = 2
COFFEESCRIPT_OUTPUT_DIR = "COFFEESCRIPT_CACHE"

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
        'coffeescript': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}

########NEW FILE########
__FILENAME__ = tests
from unittest import main, TestCase
from django.http import HttpRequest
from django.template.base import Template
from django.template.context import RequestContext
import os
import re
import time
import shutil


os.environ["DJANGO_SETTINGS_MODULE"] = "coffeescript.tests.django_settings"


class CoffeeScriptTestCase(TestCase):

    def setUp(self):
        from django.conf import settings as django_settings
        self.django_settings = django_settings

        output_dir = os.path.join(self.django_settings.STATIC_ROOT,
                                  self.django_settings.COFFEESCRIPT_OUTPUT_DIR)

        # Remove the output directory if it exists to start from scratch
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

    def _get_request_context(self):
        return RequestContext(HttpRequest())

    def _clean_javascript(self, js):
        """ Remove comments and all blank lines. """
        return "\n".join(line for line in js.split("\n") if line.strip() and not line.startswith("//"))

    def test_inline_coffeescript(self):
        template = Template("""
        {% load coffeescript %}
        {% inlinecoffeescript %}
          console.log "Hello, World"
        {% endinlinecoffeescript %}
        """)
        rendered = """(function() {
  console.log("Hello, World");
}).call(this);"""
        self.assertEqual(
            self._clean_javascript(template.render(self._get_request_context()).strip()),
            self._clean_javascript(rendered)
        )

    def test_external_coffeescript(self):

        template = Template("""
        {% load coffeescript %}
        {% coffeescript "scripts/test.coffee" %}
        """)
        compiled_filename_re = re.compile(r"COFFEESCRIPT_CACHE/scripts/test-[a-f0-9]{12}.js")
        compiled_filename = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename)))

        compiled_path = os.path.join(self.django_settings.STATIC_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read()
        compiled = """(function() {
  console.log("Hello, World!");
}).call(this);
"""
        self.assertEquals(
            self._clean_javascript(compiled_content),
            self._clean_javascript(compiled)
        )

        # Change the modification time
        source_path = os.path.join(self.django_settings.STATIC_ROOT, "scripts/test.coffee")
        os.utime(source_path, None)

        # The modification time is cached so the compiled file is not updated
        compiled_filename_2 = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename_2)))
        self.assertEquals(compiled_filename, compiled_filename_2)

        # Wait to invalidate the cached modification time
        time.sleep(self.django_settings.COFFEESCRIPT_MTIME_DELAY)

        # Now the file is re-compiled
        compiled_filename_3 = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename_3)))
        self.assertNotEquals(compiled_filename, compiled_filename_3)

        # Check that we have only one compiled file, old files should be removed

        compiled_file_dir = os.path.dirname(os.path.join(self.django_settings.STATIC_ROOT,
                                                         compiled_filename_3))
        self.assertEquals(len(os.listdir(compiled_file_dir)), 1)

    def test_lookup_in_staticfiles_dirs(self):
        template = Template("""
        {% load coffeescript %}
        {% coffeescript "another_test.coffee" %}
        """)
        compiled_filename_re = re.compile(r"COFFEESCRIPT_CACHE/another_test-[a-f0-9]{12}.js")
        compiled_filename = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename)))

        compiled_path = os.path.join(self.django_settings.STATIC_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read()
        compiled = """(function() {
  console.log("Hello, World from STATICFILES_DIRS!");
}).call(this);
"""
        self.assertEquals(
            self._clean_javascript(compiled_content),
            self._clean_javascript(compiled)
        )


        template = Template("""
        {% load coffeescript %}
        {% coffeescript "prefix/another_test.coffee" %}
        """)
        compiled_filename_re = re.compile(r"COFFEESCRIPT_CACHE/prefix/another_test-[a-f0-9]{12}.js")
        compiled_filename = template.render(self._get_request_context()).strip()
        self.assertTrue(bool(compiled_filename_re.match(compiled_filename)))

        compiled_path = os.path.join(self.django_settings.STATIC_ROOT, compiled_filename)
        compiled_content = open(compiled_path).read()
        compiled = """(function() {
  console.log("Hello, World from STATICFILES_DIRS with prefix!");
}).call(this);
"""
        self.assertEquals(
            self._clean_javascript(compiled_content),
            self._clean_javascript(compiled)
        )

if __name__ == '__main__':
    main()

########NEW FILE########
