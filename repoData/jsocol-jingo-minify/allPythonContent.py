__FILENAME__ = settings
import os

TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

MEDIA_ROOT = '/media'
MEDIA_URL = ''
STATIC_ROOT = path('static')
STATIC_URL = ''

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'jingo_minify',
    'django_nose',
    'minify',
)

MINIFY_BUNDLES = {
    'css': {
        'common': ['css/test.css'],
        'common_multi': ['css/test.css', 'css/test2.css'],
        'common_url': ['http://example.com/test.css'],
        'common_protocol_less_url': ['//example.com/test.css'],
        'common_bundle': ['css/test.css', 'http://example.com/test.css',
                          '//example.com/test.css',
                          'https://example.com/test.css'],
        'compiled': ['css/plain.css',
                     'css/less.less',
                     'css/sass.sass',
                     'css/scss.scss',
                     'css/stylus.styl']
    },
    'js': {
        'common': ['js/test.js'],
        'common_url': ['http://example.com/test.js'],
        'common_protocol_less_url': ['//example.com/test.js'],
        'common_bundle': ['js/test.js', 'http://example.com/test.js',
                          '//example.com/test.js',
                          'https://example.com/test.js'],
    },
}

LESS_PREPROCESS = True
LESS_BIN = '/usr/bin/lessc'

SASS_PREPROCESS = True
SASS_BIN = '/usr/bin/sass'

########NEW FILE########
__FILENAME__ = helpers
import os
import subprocess
import time

from django.conf import settings

import jinja2
from jingo import register

from .utils import get_media_url, get_path


try:
    from build import BUILD_ID_CSS, BUILD_ID_JS, BUILD_ID_IMG, BUNDLE_HASHES
except ImportError:
    BUILD_ID_CSS = BUILD_ID_JS = BUILD_ID_IMG = 'dev'
    BUNDLE_HASHES = {}


def is_external(url):
    """
    Determine if it is an external URL.
    """
    return url.startswith(('//', 'http://', 'https://'))


def _get_item_path(item):
    """
    Determine whether to return a relative path or a URL.
    """
    if is_external(item):
        return item
    return get_media_url() + item


def _get_mtime(item):
    """Get a last-changed timestamp for development."""
    if item.startswith(('//', 'http://', 'https://')):
        return int(time.time())
    return int(os.path.getmtime(get_path(item)))


def _build_html(items, wrapping):
    """
    Wrap `items` in wrapping.
    """
    return jinja2.Markup('\n'.join((wrapping % item for item in items)))


def get_js_urls(bundle, debug=None):
    """
    Fetch URLs for the JS files in the requested bundle.

    :param bundle:
        Name of the bundle to fetch.

    :param debug:
        If True, return URLs for individual files instead of the minified
        bundle.
    """
    if debug is None:
        debug = settings.TEMPLATE_DEBUG

    if debug:
        # Add timestamp to avoid caching.
        return [_get_item_path('%s?build=%s' % (item, _get_mtime(item))) for
                item in settings.MINIFY_BUNDLES['js'][bundle]]
    else:
        build_id = BUILD_ID_JS
        bundle_full = 'js:%s' % bundle
        if bundle_full in BUNDLE_HASHES:
            build_id = BUNDLE_HASHES[bundle_full]
        return (_get_item_path('js/%s-min.js?build=%s' % (bundle, build_id,)),)


def _get_compiled_css_url(item):
    """
    Compresses a preprocess file and returns its relative compressed URL.

    :param item:
        Name of the less/sass/stylus file to compress into css.
    """
    if ((item.endswith('.less') and
            getattr(settings, 'LESS_PREPROCESS', False)) or
            item.endswith(('.sass', '.scss', '.styl'))):
        compile_css(item)
        return item + '.css'
    return item


def get_css_urls(bundle, debug=None):
    """
    Fetch URLs for the CSS files in the requested bundle.

    :param bundle:
        Name of the bundle to fetch.

    :param debug:
        If True, return URLs for individual files instead of the minified
        bundle.
    """
    if debug is None:
        debug = settings.TEMPLATE_DEBUG

    if debug:
        items = []
        for item in settings.MINIFY_BUNDLES['css'][bundle]:
            if ((item.endswith('.less') and
                    getattr(settings, 'LESS_PREPROCESS', False)) or
                    item.endswith(('.sass', '.scss', '.styl'))):
                compile_css(item)
                items.append('%s.css' % item)
            else:
                items.append(item)
        # Add timestamp to avoid caching.
        return [_get_item_path('%s?build=%s' % (item, _get_mtime(item))) for
                item in items]
    else:
        build_id = BUILD_ID_CSS
        bundle_full = 'css:%s' % bundle
        if bundle_full in BUNDLE_HASHES:
            build_id = BUNDLE_HASHES[bundle_full]
        return (_get_item_path('css/%s-min.css?build=%s' %
                               (bundle, build_id)),)


@register.function
def js(bundle, debug=None, defer=False, async=False):
    """
    If we are in debug mode, just output a single script tag for each js file.
    If we are not in debug mode, return a script that points at bundle-min.js.
    """
    attrs = []
    urls = get_js_urls(bundle, debug)

    attrs.append('src="%s"')

    if defer:
        attrs.append('defer')

    if async:
        attrs.append('async')

    return _build_html(urls, '<script %s></script>' % ' '.join(attrs))


@register.function
def css(bundle, media=False, debug=None):
    """
    If we are in debug mode, just output a single script tag for each css file.
    If we are not in debug mode, return a script that points at bundle-min.css.
    """
    urls = get_css_urls(bundle, debug)
    if not media:
        media = getattr(settings, 'CSS_MEDIA_DEFAULT', 'screen,projection,tv')

    return _build_html(urls, '<link rel="stylesheet" media="%s" href="%%s" />'
                             % media)


@register.function
def inline_css(bundle, media=False, debug=None):
    """
    If we are in debug mode, just output a single style tag for each css file.
    If we are not in debug mode, return a style that contains bundle-min.css.
    Forces a regular css() call for external URLs (no inline allowed).
    """
    if debug is None:
        debug = getattr(settings, 'TEMPLATE_DEBUG', False)

    if debug:
        items = [_get_compiled_css_url(i)
                 for i in settings.MINIFY_BUNDLES['css'][bundle]]
    else:
        items = ['css/%s-min.css' % bundle]

    if not media:
        media = getattr(settings, 'CSS_MEDIA_DEFAULT', 'screen,projection,tv')

    contents = []
    for css in items:
        if is_external(css):
            return _build_html([css], '<link rel="stylesheet" media="%s" '
                                      'href="%%s" />' % media)
        with open(get_path(css), 'r') as f:
            contents.append(f.read())

    return _build_html(contents, '<style type="text/css" media="%s">%%s'
                                 '</style>' % media)


def ensure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as e:
        # If the directory already exists, that is fine. Otherwise re-raise.
        if e.errno != os.errno.EEXIST:
            raise


def compile_css(item):
    path_src = get_path(item)
    path_dst = get_path('%s.css' % item)

    updated_src = os.path.getmtime(get_path(item))
    updated_css = 0  # If the file doesn't exist, force a refresh.
    if os.path.exists(path_dst):
        updated_css = os.path.getmtime(path_dst)

    # Is the uncompiled version newer?  Then recompile!
    if not updated_css or updated_src > updated_css:
        ensure_path_exists(os.path.dirname(path_dst))
        if item.endswith('.less'):
            with open(path_dst, 'w') as output:
                subprocess.Popen([settings.LESS_BIN, path_src], stdout=output)
        elif item.endswith(('.sass', '.scss')):
            with open(path_dst, 'w') as output:
                subprocess.Popen([settings.SASS_BIN, path_src], stdout=output)
        elif item.endswith('.styl'):
            subprocess.call('%s --include-css --include %s < %s > %s' %
                            (settings.STYLUS_BIN, os.path.dirname(path_src),
                             path_src, path_dst), shell=True)


def build_ids(request):
    """A context processor for injecting the css/js build ids."""
    return {'BUILD_ID_CSS': BUILD_ID_CSS, 'BUILD_ID_JS': BUILD_ID_JS,
            'BUILD_ID_IMG': BUILD_ID_IMG}

########NEW FILE########
__FILENAME__ = compress_assets
import hashlib
from optparse import make_option
import os
import re
import shutil
import time
import urllib2
from subprocess import call, PIPE

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import git

from jingo_minify.utils import get_media_root


path = lambda *a: os.path.join(get_media_root(), *a)


class Command(BaseCommand):  # pragma: no cover
    help = ("Compresses css and js assets defined in settings.MINIFY_BUNDLES")
    option_list = BaseCommand.option_list + (
        make_option('-u', '--update-only', action='store_true',
                    dest='do_update_only', help='Updates the hash only'),
        make_option('-t', '--add-timestamp', action='store_true',
                    dest='add_timestamp', help='Add timestamp to hash'),
    )
    requires_model_validation = False
    do_update_only = False

    checked_hash = {}
    bundle_hashes = {}

    missing_files = 0
    minify_skipped = 0
    cmd_errors = False
    ext_media_path = os.path.join(get_media_root(), 'external')

    def update_hashes(self, update=False):
        def media_git_id(media_path):
            id = git.repo.Repo(path(media_path)).log('-1')[0].id_abbrev
            if update:
                # Adds a time based hash on to the build id.
                return '%s-%s' % (id, hex(int(time.time()))[2:])
            return id

        build_id_file = os.path.realpath(os.path.join(settings.ROOT,
                                                      'build.py'))
        with open(build_id_file, 'w') as f:
            f.write('BUILD_ID_CSS = "%s"\n' % media_git_id('css'))
            f.write('BUILD_ID_JS = "%s"\n' % media_git_id('js'))
            f.write('BUILD_ID_IMG = "%s"\n' % media_git_id('img'))
            f.write('BUNDLE_HASHES = %s\n' % self.bundle_hashes)

    def handle(self, **options):
        if options.get('do_update_only', False):
            self.update_hashes(update=True)
            return

        jar_path = (os.path.dirname(__file__), '..', '..', 'bin',
                'yuicompressor-2.4.7.jar')
        self.path_to_jar = os.path.realpath(os.path.join(*jar_path))

        self.v = '-v' if options.get('verbosity', False) == '2' else ''

        cachebust_imgs = getattr(settings, 'CACHEBUST_IMGS', False)
        if not cachebust_imgs:
            print "To turn on cache busting, use settings.CACHEBUST_IMGS"

        # This will loop through every bundle, and do the following:
        # - Concat all files into one
        # - Cache bust all images in CSS files
        # - Minify the concatted files

        for ftype, bundle in settings.MINIFY_BUNDLES.iteritems():
            for name, files in bundle.iteritems():
                # Set the paths to the files.
                concatted_file = path(ftype, '%s-all.%s' % (name, ftype,))
                compressed_file = path(ftype, '%s-min.%s' % (name, ftype,))

                files_all = []
                for fn in files:
                    processed = self._preprocess_file(fn)
                    # If the file can't be processed, we skip it.
                    if processed is not None:
                        files_all.append(processed)

                # Concat all the files.
                tmp_concatted = '%s.tmp' % concatted_file
                if len(files_all) == 0:
                    raise CommandError('No input files specified in ' +
                        'MINIFY_BUNDLES["%s"]["%s"] in settings.py!' %
                        (ftype, name))
                self._call("cat %s > %s" % (' '.join(files_all), tmp_concatted),
                     shell=True)

                # Cache bust individual images in the CSS.
                if cachebust_imgs and ftype == "css":
                    bundle_hash = self._cachebust(tmp_concatted, name)
                    self.bundle_hashes["%s:%s" % (ftype, name)] = bundle_hash

                # Compresses the concatenations.
                is_changed = self._is_changed(concatted_file)
                self._clean_tmp(concatted_file)
                if is_changed or not os.path.isfile(compressed_file):
                    self._minify(ftype, concatted_file, compressed_file)
                elif self.v:
                    print "File unchanged, skipping minification of %s" % (
                            concatted_file)
                else:
                    self.minify_skipped += 1

        # Write out the hashes
        self.update_hashes(options.get('add_timestamp', False))

        if not self.v and self.minify_skipped:
            print "Unchanged files skipped for minification: %s" % (
                    self.minify_skipped)
        if self.cmd_errors:
            raise CommandError('one or more minify commands exited with a '
                               'non-zero status. See output above for errors.')

    def _call(self, *args, **kw):
        exit = call(*args, **kw)
        if exit != 0:
            print '%s exited with a non-zero status.' % args
            self.cmd_errors = True
        return exit

    def _get_url_or_path(self, item):
        """
        Determine whether this is a URL or a relative path.
        """
        if item.startswith('//'):
            return 'http:%s' % item
        elif item.startswith(('http', 'https')):
            return item
        return None

    def _preprocess_file(self, filename):
        """Preprocess files and return new filenames."""
        url = self._get_url_or_path(filename)
        if url:
            # External files from URLs are placed into a subdirectory.
            if not os.path.exists(self.ext_media_path):
                os.makedirs(self.ext_media_path)

            filename = os.path.basename(url)
            if filename.endswith(('.js', '.css', '.less', '.styl')):
                fp = path(filename.lstrip('/'))
                file_path = '%s/%s' % (self.ext_media_path, filename)

                try:
                    req = urllib2.urlopen(url)
                    print ' - Fetching %s ...' % url
                except urllib2.HTTPError, e:
                    print ' - HTTP Error %s for %s, %s' % (url, filename,
                                                           str(e.code))
                    return None
                except urllib2.URLError, e:
                    print ' - Invalid URL %s for %s, %s' % (url, filename,
                                                            str(e.reason))
                    return None

                with open(file_path, 'w+') as fp:
                    try:
                        shutil.copyfileobj(req, fp)
                    except shutil.Error:
                        print ' - Could not copy file %s' % filename
                filename = os.path.join('external', filename)
            else:
                print ' - Not a valid remote file %s' % filename
                return None

        css_bin = ((filename.endswith('.less') and settings.LESS_BIN) or
                   (filename.endswith(('.sass', '.scss')) and settings.SASS_BIN))
        if css_bin:
            fp = path(filename.lstrip('/'))
            self._call('%s %s %s.css' % (css_bin, fp, fp),
                 shell=True, stdout=PIPE)
            filename = '%s.css' % filename
        elif filename.endswith('.styl'):
            fp = path(filename.lstrip('/'))
            self._call('%s --include-css --include %s < %s > %s.css' %
                       (settings.STYLUS_BIN, os.path.dirname(fp), fp, fp),
                       shell=True, stdout=PIPE)
            filename = '%s.css' % filename
        return path(filename.lstrip('/'))

    def _is_changed(self, concatted_file):
        """Check if the file has been changed."""
        tmp_concatted = '%s.tmp' % concatted_file
        if (os.path.exists(concatted_file) and
            os.path.getsize(concatted_file) == os.path.getsize(tmp_concatted)):
            orig_hash = self._file_hash(concatted_file)
            temp_hash = self._file_hash(tmp_concatted)
            return orig_hash != temp_hash
        return True  # Different filesize, so it was definitely changed

    def _clean_tmp(self, concatted_file):
        """Replace the old file with the temp file."""
        tmp_concatted = '%s.tmp' % concatted_file
        if os.path.exists(concatted_file):
            os.remove(concatted_file)
        os.rename(tmp_concatted, concatted_file)

    def _cachebust(self, css_file, bundle_name):
        """Cache bust images.  Return a new bundle hash."""
        print "Cache busting images in %s" % re.sub('.tmp$', '', css_file)

        css_content = ''
        with open(css_file, 'r') as css_in:
            css_content = css_in.read()

        parse = lambda url: self._cachebust_regex(url, css_file)
        css_parsed = re.sub('url\(([^)]*?)\)', parse, css_content)

        with open(css_file, 'w') as css_out:
            css_out.write(css_parsed)

        # Return bundle hash for cachebusting JS/CSS files.
        file_hash = hashlib.md5(css_parsed).hexdigest()[0:7]
        self.checked_hash[css_file] = file_hash

        if not self.v and self.missing_files:
           print " - Error finding %s images (-v2 for info)" % (
                   self.missing_files,)
           self.missing_files = 0

        return file_hash

    def _minify(self, ftype, file_in, file_out):
        """Run the proper minifier on the file."""
        if ftype == 'js' and hasattr(settings, 'UGLIFY_BIN'):
            o = {'method': 'UglifyJS', 'bin': settings.UGLIFY_BIN}
            self._call("%s %s -o %s %s -m" % (o['bin'], self.v, file_out, file_in),
                 shell=True, stdout=PIPE)
        elif ftype == 'css' and hasattr(settings, 'CLEANCSS_BIN'):
            o = {'method': 'clean-css', 'bin': settings.CLEANCSS_BIN}
            self._call("%s -o %s %s" % (o['bin'], file_out, file_in),
                 shell=True, stdout=PIPE)
        else:
            o = {'method': 'YUI Compressor', 'bin': settings.JAVA_BIN}
            variables = (o['bin'], self.path_to_jar, self.v, file_in, file_out)
            self._call("%s -jar %s %s %s -o %s" % variables,
                 shell=True, stdout=PIPE)

        print "Minifying %s (using %s)" % (file_in, o['method'])

    def _file_hash(self, url):
        """Open the file and get a hash of it."""
        if url in self.checked_hash:
            return self.checked_hash[url]

        file_hash = ""
        try:
            with open(url) as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[0:7]
        except IOError:
            self.missing_files += 1
            if self.v:
                print " - Could not find file %s" % url

        self.checked_hash[url] = file_hash
        return file_hash

    def _cachebust_regex(self, img, parent):
        """Run over the regex; img is the structural regex object."""
        url = img.group(1).strip('"\'')
        if url.startswith('data:') or url.startswith('http'):
            return "url(%s)" % url

        url = url.split('?')[0]
        full_url = os.path.join(settings.ROOT, os.path.dirname(parent),
                                url)

        return "url(%s?%s)" % (url, self._file_hash(full_url))

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.test.utils import override_settings

import jingo
from mock import ANY, call, patch
from nose.tools import eq_

from .utils import get_media_root, get_media_url

try:
    from build import BUILD_ID_CSS, BUILD_ID_JS
except:
    BUILD_ID_CSS = BUILD_ID_JS = 'dev'


def setup():
    jingo.load_helpers()


@patch('jingo_minify.helpers.time.time')
@patch('jingo_minify.helpers.os.path.getmtime')
def test_js_helper(getmtime, time):
    """
    Given the js() tag if we return the assets that make up that bundle
    as defined in settings.MINIFY_BUNDLES.

    If we're not in debug mode, we just return a minified url
    """
    getmtime.return_value = 1
    time.return_value = 1
    env = jingo.env

    t = env.from_string("{{ js('common', debug=True) }}")
    s = t.render()

    expected = "\n".join(['<script src="%s?build=1"></script>'
                         % (settings.STATIC_URL + j) for j in
                         settings.MINIFY_BUNDLES['js']['common']])

    eq_(s, expected)

    t = env.from_string("{{ js('common', debug=False) }}")
    s = t.render()

    eq_(s, '<script src="%sjs/common-min.js?build=%s"></script>' %
           (settings.STATIC_URL, BUILD_ID_JS))

    t = env.from_string("{{ js('common_url', debug=True) }}")
    s = t.render()

    eq_(s, '<script src="%s"></script>' %
           "http://example.com/test.js?build=1")

    t = env.from_string("{{ js('common_url', debug=False) }}")
    s = t.render()

    eq_(s, '<script src="%sjs/common_url-min.js?build=%s"></script>' %
           (settings.STATIC_URL, BUILD_ID_JS))

    t = env.from_string("{{ js('common_protocol_less_url', debug=True) }}")
    s = t.render()

    eq_(s, '<script src="%s"></script>' %
           "//example.com/test.js?build=1")

    t = env.from_string("{{ js('common_protocol_less_url', debug=False) }}")
    s = t.render()

    eq_(s, '<script src="%sjs/common_protocol_less_url-min.js?build=%s">'
           '</script>' % (settings.STATIC_URL, BUILD_ID_JS))

    t = env.from_string("{{ js('common_bundle', debug=True) }}")
    s = t.render()

    eq_(s, '<script src="js/test.js?build=1"></script>\n'
           '<script src="http://example.com/test.js?build=1"></script>\n'
           '<script src="//example.com/test.js?build=1"></script>\n'
           '<script src="https://example.com/test.js?build=1"></script>')

    t = env.from_string("{{ js('common_bundle', debug=False) }}")
    s = t.render()

    eq_(s, '<script src="%sjs/common_bundle-min.js?build=%s"></script>' %
           (settings.STATIC_URL, BUILD_ID_JS))


@patch('jingo_minify.helpers.time.time')
@patch('jingo_minify.helpers.os.path.getmtime')
def test_css_helper(getmtime, time):
    """
    Given the css() tag if we return the assets that make up that bundle
    as defined in settings.MINIFY_BUNDLES.

    If we're not in debug mode, we just return a minified url
    """
    getmtime.return_value = 1
    time.return_value = 1
    env = jingo.env

    t = env.from_string("{{ css('common', debug=True) }}")
    s = t.render()

    expected = "\n".join(
        ['<link rel="stylesheet" media="screen,projection,tv" '
        'href="%s?build=1" />' % (settings.STATIC_URL + j)
         for j in settings.MINIFY_BUNDLES['css']['common']])

    eq_(s, expected)

    t = env.from_string("{{ css('common', debug=False) }}")
    s = t.render()

    eq_(s,
        '<link rel="stylesheet" media="screen,projection,tv" '
        'href="%scss/common-min.css?build=%s" />'
        % (settings.STATIC_URL, BUILD_ID_CSS))

    t = env.from_string("{{ css('common_url', debug=True) }}")
    s = t.render()

    eq_(s, '<link rel="stylesheet" media="screen,projection,tv" '
           'href="http://example.com/test.css?build=1" />')

    t = env.from_string("{{ css('common_url', debug=False) }}")
    s = t.render()

    eq_(s,
        '<link rel="stylesheet" media="screen,projection,tv" '
        'href="%scss/common_url-min.css?build=%s" />'
        % (settings.STATIC_URL, BUILD_ID_CSS))

    t = env.from_string("{{ css('common_protocol_less_url', debug=True) }}")
    s = t.render()

    eq_(s, '<link rel="stylesheet" media="screen,projection,tv" '
           'href="//example.com/test.css?build=1" />')

    t = env.from_string("{{ css('common_protocol_less_url', debug=False) }}")
    s = t.render()

    eq_(s,
        '<link rel="stylesheet" media="screen,projection,tv" '
        'href="%scss/common_protocol_less_url-min.css?build=%s" />'
        % (settings.STATIC_URL, BUILD_ID_CSS))

    t = env.from_string("{{ css('common_bundle', debug=True) }}")
    s = t.render()

    eq_(s, '<link rel="stylesheet" media="screen,projection,tv" '
           'href="css/test.css?build=1" />\n'
           '<link rel="stylesheet" media="screen,projection,tv" '
           'href="http://example.com/test.css?build=1" />\n'
           '<link rel="stylesheet" media="screen,projection,tv" '
           'href="//example.com/test.css?build=1" />\n'
           '<link rel="stylesheet" media="screen,projection,tv" '
           'href="https://example.com/test.css?build=1" />')

    t = env.from_string("{{ css('common_bundle', debug=False) }}")
    s = t.render()

    eq_(s, '<link rel="stylesheet" media="screen,projection,tv" '
           'href="%scss/common_bundle-min.css?build=%s" />' %
           (settings.STATIC_URL, BUILD_ID_CSS))


def test_inline_css_helper():
    env = jingo.env
    t = env.from_string("{{ inline_css('common', debug=True) }}")
    s = t.render()

    eq_(s, '<style type="text/css" media="screen,projection,tv">'
           'body {\n    color: #999;\n}\n</style>')

    t = env.from_string("{{ inline_css('common', debug=False) }}")
    s = t.render()

    eq_(s, '<style type="text/css" media="screen,projection,tv">body'
           '{color:#999}</style>')


def test_inline_css_helper_multiple_files():
    env = jingo.env
    t = env.from_string("{{ inline_css('common_multi', debug=True) }}")
    s = t.render()

    eq_(s, '<style type="text/css" media="screen,projection,tv">body {\n    '
           'color: #999;\n}\n</style>\n<style type="text/css" media="screen,'
           'projection,tv">body {\n    color: #999;\n}\n</style>')

    t = env.from_string("{{ inline_css('common_multi', debug=False) }}")
    s = t.render()

    eq_(s, '<style type="text/css" media="screen,projection,tv">body{color:'
           '#999}\nmain{font-size:1em}\n</style>')


def test_inline_css_helper_external_url():
    env = jingo.env

    t = env.from_string("{{ inline_css('common_url', debug=True) }}")
    s = t.render()

    eq_(s, '<link rel="stylesheet" media="screen,projection,tv" '
           'href="http://example.com/test.css" />')

    t = env.from_string("{{ inline_css('common_url', debug=False) }}")
    s = t.render()

    eq_(s, '<style type="text/css" media="screen,projection,tv">'
        'body{color:#999}</style>')


@override_settings(STATIC_ROOT='static',
                   MEDIA_ROOT='media',
                   STATIC_URL='http://example.com/static',
                   MEDIA_URL='http://example.com/media')
def test_no_override():
    """No override uses STATIC versions."""
    eq_(get_media_root(), 'static')
    eq_(get_media_url(), 'http://example.com/static')


@override_settings(JINGO_MINIFY_USE_STATIC=False,
                   STATIC_ROOT='static',
                   MEDIA_ROOT='media',
                   STATIC_URL='http://example.com/static',
                   MEDIA_URL='http://example.com/media')
def test_static_override():
    """Overriding to False uses MEDIA versions."""
    eq_(get_media_root(), 'media')
    eq_(get_media_url(), 'http://example.com/media')


@override_settings(STATIC_ROOT='static',
                   MEDIA_ROOT='media',
                   STATIC_URL='http://example.com/static/',
                   MEDIA_URL='http://example.com/media/')
@patch('jingo_minify.helpers.time.time')
@patch('jingo_minify.helpers.os.path.getmtime')
def test_css(getmtime, time):
    getmtime.return_value = 1
    time.return_value = 1
    env = jingo.env

    t = env.from_string("{{ css('common', debug=True) }}")
    s = t.render()

    expected = "\n".join(
        ['<link rel="stylesheet" media="screen,projection,tv" '
         'href="%s?build=1" />' % (settings.STATIC_URL + j)
         for j in settings.MINIFY_BUNDLES['css']['common']])

    eq_(s, expected)


@override_settings(STATIC_ROOT='static',
                   MEDIA_ROOT='media',
                   LESS_PREPROCESS=True,
                   LESS_BIN='lessc-bin',
                   SASS_BIN='sass-bin',
                   STYLUS_BIN='stylus-bin')
@patch('jingo_minify.helpers.time.time')
@patch('jingo_minify.helpers.os.path.getmtime')
@patch('jingo_minify.helpers.subprocess')
@patch('__builtin__.open', spec=True)
def test_compiled_css(open_mock, subprocess_mock, getmtime_mock, time_mock):
    jingo.env.from_string("{{ css('compiled', debug=True) }}").render()

    eq_(subprocess_mock.Popen.mock_calls,
        [call(['lessc-bin', 'static/css/less.less'], stdout=ANY),
         call(['sass-bin', 'static/css/sass.sass'], stdout=ANY),
         call(['sass-bin', 'static/css/scss.scss'], stdout=ANY)])

    subprocess_mock.call.assert_called_with(
        'stylus-bin --include-css --include '
        'static/css < static/css/stylus.styl > static/css/stylus.styl.css',
        shell=True)


@override_settings(STATIC_ROOT='static',
                   MEDIA_ROOT='media',
                   STATIC_URL='http://example.com/static/',
                   MEDIA_URL='http://example.com/media/')
@patch('jingo_minify.helpers.time.time')
@patch('jingo_minify.helpers.os.path.getmtime')
def test_js(getmtime, time):
    getmtime.return_value = 1
    time.return_value = 1
    env = jingo.env

    t = env.from_string("{{ js('common', debug=True) }}")
    s = t.render()

    expected = "\n".join(
        ['<script src="%s?build=1"></script>' % (settings.STATIC_URL + j)
         for j in settings.MINIFY_BUNDLES['js']['common']])

    eq_(s, expected)

########NEW FILE########
__FILENAME__ = utils
import os

from django.conf import settings
from django.contrib.staticfiles.finders import find as static_finder


def get_media_root():
    """Return STATIC_ROOT or MEDIA_ROOT depending on JINGO_MINIFY_USE_STATIC.

    This allows projects using Django 1.4 to continue using the old
    ways, but projects using Django 1.4 to use the new ways.

    """
    if getattr(settings, 'JINGO_MINIFY_USE_STATIC', True):
        return settings.STATIC_ROOT
    return settings.MEDIA_ROOT


def get_media_url():
    """Return STATIC_URL or MEDIA_URL depending on JINGO_MINIFY_USE_STATIC.

    Allows projects using Django 1.4 to continue using the old ways
    but projects using Django 1.4 to use the new ways.

    """
    if getattr(settings, 'JINGO_MINIFY_USE_STATIC', True):
        return settings.STATIC_URL
    return settings.MEDIA_URL


def get_path(path):
    """Get a system path for a given file.

    This properly handles storing files in `project/app/static`, and any other
    location that Django's static files system supports.

    ``path`` should be relative to ``STATIC_ROOT``.

    """
    debug = getattr(settings, 'DEBUG', False)
    static = getattr(settings, 'JINGO_MINIFY_USE_STATIC', True)

    full_path = os.path.join(get_media_root(), path)

    if debug and static:
        found_path = static_finder(path)
        # If the path is not found by Django's static finder (like we are
        # trying to get an output path), it returns None, so fall back.
        if found_path is not None:
            full_path = found_path

    return full_path

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python

import os
import sys


# Set up the environment for our test project.
ROOT = os.path.abspath(os.path.dirname(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = 'minify.settings'
sys.path.insert(0, os.path.join(ROOT, 'examples'))

# This can't be imported until after we've fiddled with the
# environment.
from django.test.utils import setup_test_environment
setup_test_environment()

from django.core.management import call_command

# Run the equivalent of "django-admin.py test"
call_command('test')

########NEW FILE########
