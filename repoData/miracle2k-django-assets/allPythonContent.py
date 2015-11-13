__FILENAME__ = env
import imp
import threading
from django.conf import settings
from webassets.env import (
    BaseEnvironment, ConfigStorage, Resolver, url_prefix_join)
from webassets.exceptions import ImminentDeprecationWarning
try:
    from django.contrib.staticfiles import finders
except ImportError:
    # Support pre-1.3 versions.
    finders = None

from django_assets.glob import Globber, has_magic


__all__ = ('register',)



class DjangoConfigStorage(ConfigStorage):

    _mapping = {
        'debug': 'ASSETS_DEBUG',
        'cache': 'ASSETS_CACHE',
        'updater': 'ASSETS_UPDATER',
        'auto_build': 'ASSETS_AUTO_BUILD',
        'url_expire': 'ASSETS_URL_EXPIRE',
        'versions': 'ASSETS_VERSIONS',
        'manifest': 'ASSETS_MANIFEST',
        'load_path': 'ASSETS_LOAD_PATH',
        'url_mapping': 'ASSETS_URL_MAPPING',
    }

    def _transform_key(self, key):
        # STATIC_* are the new Django 1.3 settings,
        # MEDIA_* was used in earlier versions.

        if key.lower() == 'directory':
            if hasattr(settings, 'ASSETS_ROOT'):
                return 'ASSETS_ROOT'
            if getattr(settings, 'STATIC_ROOT', None):
                # Is None by default
                return 'STATIC_ROOT'
            return 'MEDIA_ROOT'

        if key.lower() == 'url':
            if hasattr(settings, 'ASSETS_URL'):
                return 'ASSETS_URL'
            if getattr(settings, 'STATIC_URL', None):
                # Is '' by default
                return 'STATIC_URL'
            return 'MEDIA_URL'

        return self._mapping.get(key.lower(), key.upper())

    def __contains__(self, key):
        return hasattr(settings, self._transform_key(key))

    def __getitem__(self, key):
        if self.__contains__(key):
            value = self._get_deprecated(key)
            if value is not None:
                return value
            return getattr(settings, self._transform_key(key))
        else:
            raise KeyError("Django settings doesn't define %s" %
                           self._transform_key(key))

    def __setitem__(self, key, value):
        if not self._set_deprecated(key, value):
            setattr(settings, self._transform_key(key), value)

    def __delitem__(self, key):
        # This isn't possible to implement in Django without relying
        # on internals of the settings object, so just set to None.
        self.__setitem__(key, None)


class StorageGlobber(Globber):
    """Globber that works with a Django storage."""

    def __init__(self, storage):
        self.storage = storage

    def isdir(self, path):
        # No API for this, though we could a) check if this is a filesystem
        # storage, then do a shortcut, otherwise b) use listdir() and see
        # if we are in the directory set.
        # However, this is only used for the "sdf/" syntax, so by returning
        # False we disable this syntax and cause it no match nothing.
        return False

    def islink(self, path):
        # No API for this, just act like we don't know about links.
        return False

    def listdir(self, path):
        directories, files = self.storage.listdir(path)
        return directories + files

    def exists(self, path):
        try:
            return self.storage.exists(path)
        except NotImplementedError:
            return False


class DjangoResolver(Resolver):
    """Adds support for staticfiles resolving."""

    @property
    def use_staticfiles(self):
        return settings.DEBUG and \
            'django.contrib.staticfiles' in settings.INSTALLED_APPS

    def glob_staticfiles(self, item):
        # The staticfiles finder system can't do globs, but we can
        # access the storages behind the finders, and glob those.

        for finder in finders.get_finders():
            # Builtin finders use either one of those attributes,
            # though this does seem to be informal; custom finders
            # may well use neither. Nothing we can do about that.
            if hasattr(finder, 'storages'):
                storages = finder.storages.values()
            elif hasattr(finder, 'storage'):
                storages = [finder.storage]
            else:
                continue

            for storage in storages:
                globber = StorageGlobber(storage)
                for file in globber.glob(item):
                    yield storage.path(file)

    def search_for_source(self, ctx, item):
        if not self.use_staticfiles:
            return Resolver.search_for_source(self, ctx, item)

        # Use the staticfiles finders to determine the absolute path
        if finders:
            if has_magic(item):
                return list(self.glob_staticfiles(item))
            else:
                f = finders.find(item)
                if f is not None:
                    return f

        raise IOError(
            "'%s' not found (using staticfiles finders)" % item)

    def resolve_source_to_url(self, ctx, filepath, item):
        if not self.use_staticfiles:
            return Resolver.resolve_source_to_url(self, ctx, filepath, item)

        # With staticfiles enabled, searching the url mappings, as the
        # parent implementation does, will not help. Instead, we can
        # assume that the url is the root url + the original relative
        # item that was specified (and searched for using the finders).
        return url_prefix_join(ctx.url, item)


class DjangoEnvironment(BaseEnvironment):
    """For Django, we need to redirect all the configuration values this
    object holds to Django's own settings object.
    """

    config_storage_class = DjangoConfigStorage
    resolver_class = DjangoResolver


# Django has a global state, a global configuration, and so we need a
# global instance of a asset environment.
env = None
env_lock = threading.RLock()

def get_env():
    # While the first request is within autoload(), a second thread can come
    # in and without the lock, would use a not-fully-loaded environment.
    with env_lock:
        global env
        if env is None:
            env = DjangoEnvironment()

            # Load application's ``assets``  modules. We need to do this in
            # a delayed fashion, since the main django_assets module imports
            # this, and the application ``assets`` modules we load will import
            # ``django_assets``, thus giving us a classic circular dependency
            # issue.
            autoload()
        return env

def reset():
    global env
    env = None

# The user needn't know about the env though, we can expose the
# relevant functionality directly. This is also for backwards-compatibility
# with times where ``django-assets`` was a standalone library.
def register(*a, **kw):
    return get_env().register(*a, **kw)


# Finally, we'd like to autoload the ``assets`` module of each Django.
try:
    from django.utils.importlib import import_module
except ImportError:
    # django-1.0 compatibility
    import warnings
    warnings.warn('django-assets may not be compatible with Django versions '
                  'earlier than 1.1', ImminentDeprecationWarning)
    def import_module(app):
        return __import__(app, {}, {}, [app.split('.')[-1]]).__path__


_ASSETS_LOADED = False

def autoload():
    """Find assets by looking for an ``assets`` module within each
    installed application, similar to how, e.g., the admin autodiscover
    process works. This is were this code has been adapted from, too.

    Only runs once.
    """
    global _ASSETS_LOADED
    if _ASSETS_LOADED:
        return False

    # Import this locally, so that we don't have a global Django
    # dependency.
    from django.conf import settings

    for app in settings.INSTALLED_APPS:
        # For each app, we need to look for an assets.py inside that
        # app's package. We can't use os.path here -- recall that
        # modules may be imported different ways (think zip files) --
        # so we need to get the app's __path__ and look for
        # admin.py on that path.
        #if options.get('verbosity') > 1:
        #    print "\t%s..." % app,

        # Step 1: find out the app's __path__ Import errors here will
        # (and should) bubble up, but a missing __path__ (which is
        # legal, but weird) fails silently -- apps that do weird things
        # with __path__ might need to roll their own registration.
        try:
            app_path = import_module(app).__path__
        except AttributeError:
            #if options.get('verbosity') > 1:
            #    print "cannot inspect app"
            continue

        # Step 2: use imp.find_module to find the app's assets.py.
        # For some reason imp.find_module raises ImportError if the
        # app can't be found but doesn't actually try to import the
        # module. So skip this app if its assetse.py doesn't exist
        try:
            imp.find_module('assets', app_path)
        except ImportError:
            #if options.get('verbosity') > 1:
            #    print "no assets module"
            continue

        # Step 3: import the app's assets file. If this has errors we
        # want them to bubble up.
        import_module("%s.assets" % app)
        #if options.get('verbosity') > 1:
        #    print "assets module loaded"

    # Load additional modules.
    for module in getattr(settings, 'ASSETS_MODULES', []):
        import_module("%s" % module)

    _ASSETS_LOADED = True

########NEW FILE########
__FILENAME__ = filter
"""Django specific filters.

For those to be registered automatically, make sure the main
django_assets namespace imports this file.
"""
from django.template import Template, Context

from webassets import six
from webassets.filter import Filter, register_filter


class TemplateFilter(Filter):
    """
    Will compile all source files as Django templates.
    """
    name = 'template'
    max_debug_level = None

    def __init__(self, context=None):
        super(TemplateFilter, self).__init__()
        self.context = context

    def input(self, _in, out, source_path, output_path, **kw):
        t = Template(_in.read(), origin='django-assets', name=source_path)
        rendered = t.render(Context(self.context if self.context else {}))

        if not six.PY3:
            rendered = rendered.encode('utf-8')
        out.write(rendered)


register_filter(TemplateFilter)

########NEW FILE########
__FILENAME__ = finders
from django.conf import settings
from django.contrib import staticfiles
from django.core.files.storage import FileSystemStorage
from django_assets.env import get_env
from webassets.exceptions import BundleError

try:
    # Django 1.4
    from django.contrib.staticfiles.utils import matches_patterns
except ImportError:
    # Django 1.3
    from django.contrib.staticfiles.utils import is_ignored as matches_patterns


class AssetsFileStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        super(AssetsFileStorage, self).__init__(
            location or get_env().directory,
            base_url or get_env().url,
            *args, **kwargs)


class AssetsFinder(staticfiles.finders.BaseStorageFinder):
    """A staticfiles finder that will serve from ASSETS_ROOT (which
    defaults to STATIC_ROOT).

    This is required when using the django.contrib.staticfiles app
    in development, because the Django devserver will not serve files
    from STATIC_ROOT (or ASSETS_ROOT) by default - which is were the
    merged assets are written.
    """

    # Make this finder search ``Environment.directory``.
    storage = AssetsFileStorage

    def list(self, ignore_patterns):
        # While ``StaticFileStorage`` itself is smart enough not to stumble
        # over this finder returning the full contents of STATIC_ROOT via
        # ``AssetsFileStorage``, ``CachedAssetsFileStorage`` is not. It would
        # create hashed versions of already hashed files.
        #
        # Since the development ``serve`` view will not use this ``list()``
        # method, but the ``collectstatic`` command does, we can customize
        # it to deal with ``CachedAssetsFileStorage``.
        #
        # We restrict the files returned to known bundle output files. Those
        # will then be post-processed by ``CachedAssetsFileStorage`` and
        # properly hashed and rewritten.
        #
        # See also this discussion:
        #    https://github.com/miracle2k/webassets/issues/114

        env = get_env()
        if env.directory == getattr(settings, 'STATIC_ROOT'):
            for bundle in env:
                try:
                    output = bundle.resolve_output(env)
                except BundleError:
                    # We don't have a version for this bundle
                    continue

                if not matches_patterns(output, ignore_patterns) and \
                 self.storage.exists(output):
                    yield output, self.storage
        else:
            # When ASSETS_ROOT is a separate directory independent of
            # STATIC_ROOT, we're good just letting all files be collected.
            for output in super(AssetsFinder, self).list(ignore_patterns):
                yield output

########NEW FILE########
__FILENAME__ = glob
"""Copied from python-glob2, made to work in a single file, to avoid
having a dependency.
"""


"""Filename matching with shell patterns.

fnmatch(FILENAME, PATTERN) matches according to the local convention.
fnmatchcase(FILENAME, PATTERN) always takes case in account.

The functions operate by translating the pattern into a regular
expression.  They cache the compiled regular expressions for speed.

The function translate(PATTERN) returns a regular expression
corresponding to PATTERN.  (It does not compile it.)
"""

import re
from webassets import six

__all__ = ["filter", "fnmatch", "fnmatchcase", "translate"]

_cache = {}
_MAXCACHE = 100

def _purge():
    """Clear the pattern cache"""
    _cache.clear()

def fnmatch(name, pat):
    """Test whether FILENAME matches PATTERN.

    Patterns are Unix shell style:

    *       matches everything
    ?       matches any single character
    [seq]   matches any character in seq
    [!seq]  matches any char not in seq

    An initial period in FILENAME is not special.
    Both FILENAME and PATTERN are first case-normalized
    if the operating system requires it.
    If you don't want this, use fnmatchcase(FILENAME, PATTERN).
    """

    import os
    name = os.path.normcase(name)
    pat = os.path.normcase(pat)
    return fnmatchcase(name, pat)

def fnmatch_filter(names, pat):
    """Return the subset of the list NAMES that match PAT"""
    import os,posixpath
    result=[]
    pat=os.path.normcase(pat)
    if not pat in _cache:
        res = translate(pat)
        if len(_cache) >= _MAXCACHE:
            _cache.clear()
        _cache[pat] = re.compile(res)
    match=_cache[pat].match
    if os.path is posixpath:
        # normcase on posix is NOP. Optimize it away from the loop.
        for name in names:
            m = match(name)
            if m:
                result.append((name, m.groups()))
    else:
        for name in names:
            m = match(os.path.normcase(name))
            if m:
                result.append((name, m.groups()))
    return result

def fnmatchcase(name, pat):
    """Test whether FILENAME matches PATTERN, including case.

    This is a version of fnmatch() which doesn't case-normalize
    its arguments.
    """

    if not pat in _cache:
        res = translate(pat)
        if len(_cache) >= _MAXCACHE:
            _cache.clear()
        _cache[pat] = re.compile(res)
    return _cache[pat].match(name) is not None

def translate(pat):
    """Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.
    """

    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            res = res + '(.*)'
        elif c == '?':
            res = res + '(.)'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\','\\\\')
                i = j+1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s([%s])' % (res, stuff)
        else:
            res = res + re.escape(c)
    return res + '\Z(?ms)'


"""Filename globbing utility."""

import sys
import os
import re


class Globber(object):

    listdir = staticmethod(os.listdir)
    isdir = staticmethod(os.path.isdir)
    islink = staticmethod(os.path.islink)
    exists = staticmethod(os.path.lexists)

    def walk(self, top, followlinks=False):
        """A simplified version of os.walk (code copied) that uses
        ``self.listdir``, and the other local filesystem methods.

        Because we don't care about file/directory distinctions, only
        a single list is returned.
        """
        try:
            names = self.listdir(top)
        except os.error:
            return

        items = []
        for name in names:
            items.append(name)

        yield top, items

        for name in items:
            new_path = os.path.join(top, name)
            if followlinks or not self.islink(new_path):
                for x in self.walk(new_path, followlinks):
                    yield x

    def glob(self, pathname, with_matches=False):
        """Return a list of paths matching a pathname pattern.

        The pattern may contain simple shell-style wildcards a la fnmatch.

        """
        return list(self.iglob(pathname, with_matches))

    def iglob(self, pathname, with_matches=False):
        """Return an iterator which yields the paths matching a pathname
        pattern.

        The pattern may contain simple shell-style wildcards a la fnmatch.

        If ``with_matches`` is True, then for each matching path
        a 2-tuple will be returned; the second element if the tuple
        will be a list of the parts of the path that matched the individual
        wildcards.
        """
        result = self._iglob(pathname)
        if with_matches:
            return result
        return map(lambda s: s[0], result)

    def _iglob(self, pathname, rootcall=True):
        """Internal implementation that backs :meth:`iglob`.

        ``rootcall`` is required to differentiate between the user's call to
        iglob(), and subsequent recursive calls, for the purposes of resolving
        certain special cases of ** wildcards. Specifically, "**" is supposed
        to include the current directory for purposes of globbing, but the
        directory itself should never be returned. So if ** is the lastmost
        part of the ``pathname`` given the user to the root call, we want to
        ignore the current directory. For this, we need to know which the root
        call is.
        """

        # Short-circuit if no glob magic
        if not has_magic(pathname):
            if self.exists(pathname):
                yield pathname, ()
            return

        # If no directory part is left, assume the working directory
        dirname, basename = os.path.split(pathname)

        # If the directory is globbed, recurse to resolve.
        # If at this point there is no directory part left, we simply
        # continue with dirname="", which will search the current dir.
        if dirname and has_magic(dirname):
            # Note that this may return files, which will be ignored
            # later when we try to use them as directories.
            # Prefiltering them here would only require more IO ops.
            dirs = self._iglob(dirname, rootcall=False)
        else:
            dirs = [(dirname, ())]

        # Resolve ``basename`` expr for every directory found
        for dirname, dir_groups in dirs:
            for name, groups in self.resolve_pattern(
                dirname, basename, not rootcall):
                yield os.path.join(dirname, name), dir_groups + groups

    def resolve_pattern(self, dirname, pattern, globstar_with_root):
        """Apply ``pattern`` (contains no path elements) to the
        literal directory`` in dirname``.

        If pattern=='', this will filter for directories. This is
        a special case that happens when the user's glob expression ends
        with a slash (in which case we only want directories). It simpler
        and faster to filter here than in :meth:`_iglob`.
        """

        if isinstance(pattern, six.text_type) and not isinstance(dirname, six.text_type):
            dirname = six.u(dirname, sys.getfilesystemencoding() or
                                       sys.getdefaultencoding())

        # If no magic, short-circuit, only check for existence
        if not has_magic(pattern):
            if pattern == '':
                if self.isdir(dirname):
                    return [(pattern, ())]
            else:
                if self.exists(os.path.join(dirname, pattern)):
                    return [(pattern, ())]
            return []

        if not dirname:
            dirname = os.curdir

        try:
            if pattern == '**':
                # Include the current directory in **, if asked; by adding
                # an empty string as opposed to '.', be spare ourselves
                # having to deal with os.path.normpath() later.
                names = [''] if globstar_with_root else []
                for top, entries in self.walk(dirname):
                    _mkabs = lambda s: os.path.join(top[len(dirname)+1:], s)
                    names.extend(map(_mkabs, entries))
                    # Reset pattern so that fnmatch(), which does not understand
                # ** specifically, will only return a single group match.
                pattern = '*'
            else:
                names = self.listdir(dirname)
        except os.error:
            return []

        if pattern[0] != '.':
            # Remove hidden files by default, but take care to ensure
            # that the empty string we may have added earlier remains.
            # Do not filter out the '' that we might have added earlier
            names = filter(lambda x: not x or x[0] != '.', names)
        return fnmatch_filter(names, pattern)


default_globber = Globber()
glob = default_globber.glob
iglob = default_globber.iglob
del default_globber


magic_check = re.compile('[*?[]')

def has_magic(s):
    return magic_check.search(s) is not None

########NEW FILE########
__FILENAME__ = loaders
from django.conf import settings
from django import template
from webassets.loaders import GlobLoader, LoaderError

try:
    set
except NameError:
    from sets import Set as set

from django_assets.templatetags.assets import AssetsNode as AssetsNodeOriginal
try:
    from django.templatetags.assets import AssetsNode as AssetsNodeMapped
except ImportError:
    # Since Django #12295, custom templatetags are no longer mapped into
    # the Django namespace. Support both versions.
    AssetsNodeMapped = None
AssetsNodeClasses = tuple(
    filter(lambda c: bool(c), (AssetsNodeOriginal, AssetsNodeMapped))
)


__all__ = ('DjangoLoader', 'get_django_template_dirs',)


def _shortpath(abspath):
    """Make an absolute path relative to the project's settings module,
    which would usually be the project directory.
    """
    b = os.path.dirname(os.path.normpath(sys.modules[settings.SETTINGS_MODULE].__file__))
    p = os.path.normpath(abspath)
    return p[len(os.path.commonprefix([b, p])):]


def uniq(seq):
    """Remove duplicate items, preserve order.

    http://www.peterbe.com/plog/uniqifiers-benchmark
    """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if x not in seen and not seen_add(x)]


FILESYSTEM_LOADERS = [
    'django.template.loaders.filesystem.load_template_source', # <= 1.1
    'django.template.loaders.filesystem.Loader',                 # > 1.2
]
APPDIR_LOADERS = [
    'django.template.loaders.app_directories.load_template_source', # <= 1.1
    'django.template.loaders.app_directories.Loader'            # > 1.2
]
def get_django_template_dirs(loader_list=None):
    """Build a list of template directories based on configured loaders.
    """
    if not loader_list:
        loader_list = settings.TEMPLATE_LOADERS

    template_dirs = []
    for loader in loader_list:
        if loader in FILESYSTEM_LOADERS:
            template_dirs.extend(settings.TEMPLATE_DIRS)
        if loader in APPDIR_LOADERS:
            from django.template.loaders.app_directories import app_template_dirs
            template_dirs.extend(app_template_dirs)
        if isinstance(loader, (list, tuple)) and len(loader) >= 2:
            # The cached loader uses the tuple syntax, but simply search all
            # tuples for nested loaders; thus possibly support custom ones too.
            template_dirs.extend(get_django_template_dirs(loader[1]))

    return uniq(template_dirs)


class DjangoLoader(GlobLoader):
    """Parse all the templates of the current Django project, try to find
    bundles in active use.
    """

    def load_bundles(self):
        bundles = []
        for template_dir in get_django_template_dirs():
            for filename in self.glob_files((template_dir, '*.html'), True):
                bundles.extend(self.with_file(filename, self._parse) or [])
        return bundles

    def _parse(self, filename, contents):
        # parse the template for asset nodes
        try:
            t = template.Template(contents)
        except template.TemplateSyntaxError as e:
            raise LoaderError('Django parser failed: %s' % e)
        else:
            result = []
            def _recurse_node(node):
                # depending on whether the template tag is added to
                # builtins, or loaded via {% load %}, it will be
                # available in a different module
                if node is not None and \
                   isinstance(node, AssetsNodeClasses):
                    # try to resolve this node's data; if we fail,
                    # then it depends on view data and we cannot
                    # manually rebuild it.
                    try:
                        bundle = node.resolve()
                    except template.VariableDoesNotExist:
                        raise LoaderError('skipping bundle %s, depends on runtime data' % node.output)
                    else:
                        result.append(bundle)
                # see Django #7430
                for subnode in hasattr(node, 'nodelist') \
                    and node.nodelist\
                    or []:
                        _recurse_node(subnode)
            for node in t:  # don't move into _recurse_node, ``Template`` has a .nodelist attribute
                _recurse_node(node)
            return result

########NEW FILE########
__FILENAME__ = assets
"""Manage assets.

Usage:

    ./manage.py assets build

        Build all known assets; this requires tracking to be enabled: Only
        assets that have previously been built and tracked are
        considered "known".

    ./manage.py assets build --parse-templates

        Try to find as many of the project's templates (hopefully all), and
        check them for the use of assets. Build all the assets discovered in
        this way. If tracking is enabled, the tracking database will be
        replaced by the newly found assets.

    ./manage.py assets watch

        Like ``build``, but continues to watch for changes, and builds assets
        right away. Useful for cases where building takes some time.
"""

import sys
from os import path
import logging
from optparse import make_option
from django.conf import settings
from django.core.management import LaxOptionParser
from django.core.management.base import BaseCommand, CommandError

from webassets.script import (CommandError as AssetCommandError,
                              GenericArgparseImplementation)
from django_assets.env import get_env, autoload
from django_assets.loaders import get_django_template_dirs, DjangoLoader


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--parse-templates', action='store_true',
            help='Search project templates to find bundles. You need '
                 'this if you directly define your bundles in templates.'),
    )
    help = 'Manage assets.'
    args = 'subcommand'
    requires_model_validation = False

    def create_parser(self, prog_name, subcommand):
        # Overwrite parser creation with a LaxOptionParser that will
        # ignore arguments it doesn't know, allowing us to pass those
        # along to the webassets command.
        # Hooking into run_from_argv() would be another thing to try
        # if this turns out to be problematic.
        return LaxOptionParser(prog=prog_name,
            usage=self.usage(subcommand),
            version=self.get_version(),
            option_list=self.option_list)

    def handle(self, *args, **options):
        # Due to the use of LaxOptionParser ``args`` now contains all
        # unparsed options, and ``options`` those that the Django command
        # has declared.

        # Create log
        log = logging.getLogger('django-assets')
        log.setLevel({0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}[int(options.get('verbosity', 1))])
        log.addHandler(logging.StreamHandler())

        # If the user requested it, search for bundles defined in templates
        if options.get('parse_templates'):
            log.info('Searching templates...')
            # Note that we exclude container bundles. By their very nature,
            # they are guaranteed to have been created by solely referencing
            # other bundles which are already registered.
            get_env().add(*[b for b in self.load_from_templates()
                            if not b.is_container])

        if len(get_env()) == 0:
            raise CommandError('No asset bundles were found. '
                'If you are defining assets directly within your '
                'templates, you want to use the --parse-templates '
                'option.')

        prog = "%s assets" % path.basename(sys.argv[0])
        impl = GenericArgparseImplementation(
            env=get_env(), log=log, no_global_options=True, prog=prog)
        try:
            # The webassets script runner may either return None on success (so
            # map that to zero) or a return code on build failure (so raise
            # a Django CommandError exception when that happens)
            retval = impl.run_with_argv(args) or 0
            if retval != 0:
                raise CommandError('The webassets build script exited with '
                                   'a non-zero exit code (%d).' % retval)
        except AssetCommandError as e:
            raise CommandError(e)

    def load_from_templates(self):
        # Using the Django loader
        bundles = DjangoLoader().load_bundles()

        # Using the Jinja loader, if available
        try:
            import jinja2
        except ImportError:
            pass
        else:
            from webassets.ext.jinja2 import Jinja2Loader, AssetsExtension

            jinja2_envs = []
            # Prepare a Jinja2 environment we can later use for parsing.
            # If not specified by the user, put in there at least our own
            # extension, which we will need most definitely to achieve anything.
            _jinja2_extensions = getattr(settings, 'ASSETS_JINJA2_EXTENSIONS', False)
            if not _jinja2_extensions:
                _jinja2_extensions = [AssetsExtension.identifier]
            jinja2_envs.append(jinja2.Environment(extensions=_jinja2_extensions))

            try:
                from coffin.common import get_env as get_coffin_env
            except ImportError:
                pass
            else:
                jinja2_envs.append(get_coffin_env())

            bundles.extend(Jinja2Loader(get_env(),
                                        get_django_template_dirs(),
                                        jinja2_envs).load_bundles())

        return bundles

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = pytest_plugin
import pytest
import django_assets.env

@pytest.fixture(autouse=True)
def set_django_assets_env():
    print "Set django assets environment"
    django_assets.env.get_env() # initialise django-assets settings

########NEW FILE########
__FILENAME__ = settings
"""Unfortunately, Sphinx's autodoc module does not allow us to extract
the docstrings from the various environment config properties and
displaying them under a custom title. Instead, it will always put the
docstrings under a "Environment.foo" header.

This module is a hack to work around the issue while avoiding to duplicate
the actual docstrings.
"""

from webassets import Environment

class docwrap(object):
    def __init__(self, object, append=None):
        self.__doc__ = object.__doc__ if object else ''
        if append:
            # Add to the docstring, maintaining the proper indentation
            # so that the reST will be formatted correctly.
            try:
                last_line = self.__doc__.splitlines()[-1]
                indent = last_line[-len(last_line.lstrip()):]
                append = "\n".join(map(lambda s: indent+s, append.splitlines()))
            except IndexError:
                pass
            self.__doc__ += append


ASSETS_DEBUG = Environment.debug
ASSETS_CACHE = Environment.cache
ASSETS_AUTO_BUILD = Environment.auto_build
ASSETS_URL_EXPIRE = Environment.url_expire
ASSETS_MANIFEST = Environment.manifest
ASSETS_VERSIONS = Environment.versions
ASSETS_URL = docwrap(Environment.url, """\n\nBy default, ``STATIC_URL``
will be used for this, or the older ``MEDIA_URL`` setting.""")
ASSETS_ROOT = docwrap(Environment.directory, """\n\nBy default,
``STATIC_ROOT`` will be used for this, or the older ``MEDIA_ROOT``
setting.""")

########NEW FILE########
__FILENAME__ = assets
import tokenize
import warnings

from django import template
from django_assets import Bundle
from django_assets.env import get_env
from webassets.exceptions import ImminentDeprecationWarning


def parse_debug_value(value):
    """Django templates do not know what a boolean is, and anyway we need to
    support the 'merge' option."""
    if isinstance(value, bool):
        return value
    try:
        from webassets.env import parse_debug_value
        return parse_debug_value(value)
    except ValueError:
        raise template.TemplateSyntaxError(
            '"debug" argument must be one of the strings '
            '"true", "false" or "merge", not "%s"' % value)


class AssetsNode(template.Node):

    # For testing, to inject a mock bundle
    BundleClass = Bundle

    def __init__(self, filters, output, debug, files, childnodes):
        self.childnodes = childnodes
        self.output = output
        self.files = files
        self.filters = filters
        self.debug = debug

    def resolve(self, context={}):
        """We allow variables to be used for all arguments; this function
        resolves all data against a given context;

        This is a separate method as the management command must have
        the ability to check if the tag can be resolved without a context.
        """
        def resolve_var(x):
            if x is None:
                return None
            else:
                try:
                    return template.Variable(x).resolve(context)
                except template.VariableDoesNotExist:
                    # Django seems to hide those; we don't want to expose
                    # them either, I guess.
                    raise
        def resolve_bundle(name):
            # If a bundle with that name exists, use it. Otherwise,
            # assume a filename is meant.
            try:
                return get_env()[name]
            except KeyError:
                return name

        return self.BundleClass(
            *[resolve_bundle(resolve_var(f)) for f in self.files],
            **{'output': resolve_var(self.output),
            'filters': resolve_var(self.filters),
            'debug': parse_debug_value(resolve_var(self.debug))})

    def render(self, context):
        bundle = self.resolve(context)

        result = u""
        for url in bundle.urls(env=get_env()):
            context.update({'ASSET_URL': url, 'EXTRA': bundle.extra})
            try:
                result += self.childnodes.render(context)
            finally:
                context.pop()
        return result


def assets(parser, token):
    filters = None
    output = None
    debug = None
    files = []

    # parse the arguments
    args = token.split_contents()[1:]
    for arg in args:
        # Handle separating comma; for backwards-compatibility
        # reasons, this is currently optional, but is enforced by
        # the Jinja extension already.
        if arg[-1] == ',':
            arg = arg[:-1]
            if not arg:
                continue

        # determine if keyword or positional argument
        arg = arg.split('=', 1)
        if len(arg) == 1:
            name = None
            value = arg[0]
        else:
            name, value = arg

        # handle known keyword arguments
        if name == 'output':
            output = value
        elif name == 'debug':
            debug = value
        elif name == 'filters':
            filters = value
        elif name == 'filter':
            filters = value
            warnings.warn('The "filter" option of the {% assets %} '
                          'template tag has been renamed to '
                          '"filters" for consistency reasons.',
                            ImminentDeprecationWarning)
        # positional arguments are source files
        elif name is None:
            files.append(value)
        else:
            raise template.TemplateSyntaxError('Unsupported keyword argument "%s"'%name)

    # capture until closing tag
    childnodes = parser.parse(("endassets",))
    parser.delete_first_token()
    return AssetsNode(filters, output, debug, files, childnodes)



# If Coffin is installed, expose the Jinja2 extension
try:
    from coffin.template import Library as CoffinLibrary
except ImportError:
    register = template.Library()
else:
    register = CoffinLibrary()
    from webassets.ext.jinja2 import AssetsExtension
    from django_assets.env import get_env
    register.tag(AssetsExtension, environment={'assets_environment': get_env()})

# expose the default Django tag
register.tag('assets', assets)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-assets documentation build configuration file, created by
# sphinx-quickstart on Sun Jul  8 16:07:16 2012.
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
#sys.path.append(os.path.abspath('.'))

# make sure we are documenting the local version with autodoc
sys.path.insert(0, os.path.abspath('..'))
import django_assets

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'sphinx.ext.extlinks']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-assets'
copyright = u'2012, Michael Elsdörfer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, django_assets.__version__))
# The full version, including alpha/beta/rc tags.
release = version

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinxdoc'

html_style = 'theme_customize.css'

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
#html_sidebars = {}

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
htmlhelp_basename = 'django-assetsdoc'


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
  ('index', 'django-assets.tex', u'django-assets Documentation',
   u'Michael Elsdörfer', 'manual'),
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
    ('index', 'django-assets', u'django-assets Documentation',
     [u'Michael Elsdörfer'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-assets', u'django-assets Documentation',
   u'Michael Elsdörfer', 'django-assets', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


WEBASSETS_DOC_URL = 'http://elsdoerfer.name/docs/webassets/'

intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
    'webassets': (WEBASSETS_DOC_URL, None),
}

extlinks = {'webassets': (WEBASSETS_DOC_URL+'%s.html', None)}


def setup(app):
    from sphinx.ext import autodoc
    class MyDataDocumenter(autodoc.DataDocumenter):
        # To fetch the docstrings for the settings, Sphinx needs some help.
        # Without this, it would insert ugly signatures like:
        # my_module.SETTING = <property object at 0x193d368>
        priority = 20
        def add_directive_header(self, sig):
            autodoc.ModuleLevelDocumenter.add_directive_header(self, sig)

    app.add_autodocumenter(MyDataDocumenter)

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import run, put, env

env.hosts = ['elsdoerfer.com:2211']

def publish_docs():
    target = '/var/www/elsdoerfer/files/docs/django-assets'
    run('rm -rf %s' % target)
    run('mkdir %s' % target)
    put('build/sphinx/html/*', '%s' % target)

########NEW FILE########
__FILENAME__ = helpers
from __future__ import with_statement
import re

from webassets.test import TempDirHelper, TempEnvironmentHelper


__all__ = ('TempDirHelper', 'TempEnvironmentHelper', 'noop',
           'assert_raises_regexp', 'check_warnings')


# Define a noop filter; occasionally in tests we need to define
# a filter to be able to test a certain piece of functionality,.
noop = lambda _in, out: out.write(_in.read())


try:
    from nose.tools import assert_raises_regexp
except ImportError:
    # Python < 2.7
    def assert_raises_regexp(expected, regexp, callable, *a, **kw):
        try:
            callable(*a, **kw)
        except expected as e:
            if isinstance(regexp, basestring):
                regexp = re.compile(regexp)
            if not regexp.search(str(e.message)):
                raise self.failureException('"%s" does not match "%s"' %
                         (regexp.pattern, str(e.message)))
        else:
            if hasattr(expected,'__name__'): excName = expected.__name__
            else: excName = str(expected)
            raise AssertionError("%s not raised" % excName)


try:
    from test.test_support import check_warnings
except ImportError:
    # Python < 2.6
    import contextlib

    @contextlib.contextmanager
    def check_warnings(*filters, **kwargs):
        # We cannot reasonably support this, we'd have to copy to much code.
        # (or write our own). Since this is only testing warnings output,
        # we might slide by ignoring it.
        yield

########NEW FILE########
__FILENAME__ = test_django
# coding: utf-8
from __future__ import with_statement

from nose import SkipTest
from nose.tools import assert_raises

from django.conf import settings
from django.template import Template, Context
from django_assets.loaders import DjangoLoader
from django_assets import Bundle, register as django_env_register
from django_assets.env import get_env
from django_assets.env import reset as django_env_reset
from tests.helpers import (
    TempDirHelper,
    TempEnvironmentHelper as BaseTempEnvironmentHelper, assert_raises_regexp)
from webassets.filter import get_filter
from webassets.exceptions import BundleError, ImminentDeprecationWarning

from tests.helpers import check_warnings

try:
    from django.templatetags.assets import AssetsNode
except ImportError:
    # Since #12295, Django no longer maps the tags.
    from django_assets.templatetags.assets import AssetsNode


class TempEnvironmentHelper(BaseTempEnvironmentHelper):
    """Base-class for tests which will:

    - Reset the Django settings after each test.
    - Reset the django-assets environment after each test.
    - Initialize MEDIA_ROOT to point to a temporary directory.
    """

    def setup(self):
        TempDirHelper.setup(self)

        # Reset the webassets environment.
        django_env_reset()
        self.env = get_env()

        # Use a temporary directory as MEDIA_ROOT
        settings.MEDIA_ROOT = self.create_directories('media')[0]
        settings.STATIC_ROOT = None

        # Some other settings without which we are likely to run
        # into errors being raised as part of validation.
        setattr(settings, 'DATABASES', {})
        settings.DATABASES['default'] = {'ENGINE': ''}

        # Unless we explicitly test it, we don't want to use the cache during
        # testing.
        self.env.cache = False
        self.env.manifest = False

        # Setup a temporary settings object
        # TODO: This should be used (from 1.4), but the tests need
        # to run on 1.3 as well.
        # from django.test.utils import override_settings
        # self.override_settings = override_settings()
        # self.override_settings.enable()

    def teardown(self):
        #self.override_settings.disable()
        pass


def delsetting(name):
    """Helper to delete a Django setting from the settings
    object.

    Required because the Django 1.1. LazyObject does not implement
    __delattr__.
    """
    if '__delattr__' in settings.__class__.__dict__:
        delattr(settings, name)
    else:
        delattr(settings._wrapped, name)


class TestConfig(object):
    """The environment configuration is backed by the Django settings
    object.
    """

    def test_default_options(self):
        """The builtin options have different names within the Django
        settings, to make it obvious they belong to django-assets.
        """

        settings.ASSETS_URL_EXPIRE = True
        assert get_env().config['url_expire'] == settings.ASSETS_URL_EXPIRE

        settings.ASSETS_ROOT = 'FOO_ASSETS'
        settings.STATIC_ROOT = 'FOO_STATIC'
        settings.MEDIA_ROOT = 'FOO_MEDIA'
        # Pointing to ASSETS_ROOT
        assert get_env().directory.endswith('FOO_ASSETS')
        get_env().directory = 'BAR'
        assert settings.ASSETS_ROOT == 'BAR'
        # Pointing to STATIC_ROOT
        delsetting('ASSETS_ROOT')
        assert get_env().directory.endswith('FOO_STATIC')
        get_env().directory = 'BAR'
        assert settings.STATIC_ROOT == 'BAR'
        # Pointing to MEDIA_ROOT; Note we only
        # set STATIC_ROOT to None rather than deleting
        # it, a scenario that may occur in the wild.
        settings.STATIC_ROOT = None
        assert get_env().directory.endswith('FOO_MEDIA')
        get_env().directory = 'BAR'
        assert settings.MEDIA_ROOT == 'BAR'

    def test_custom_options(self):
        settings.FOO = 42
        assert get_env().config['foo'] == 42
        # Also, we are caseless.
        assert get_env().config['foO'] == 42

class TestTemplateTag():

    def setup(self):
        test_instance = self
        class MockBundle(Bundle):
            urls_to_fake = ['foo']
            def __init__(self, *a, **kw):
                Bundle.__init__(self, *a, **kw)
                self.env = get_env()
                # Kind of hacky, but gives us access to the last Bundle
                # instance used by our Django template tag.
                test_instance.the_bundle = self
            def urls(self, *a, **kw):
                return self.urls_to_fake
        # Inject our mock bundle class
        self._old_bundle_class = AssetsNode.BundleClass
        AssetsNode.BundleClass = self.BundleClass = MockBundle

        # Reset the Django asset environment, init it with some
        # dummy bundles.
        django_env_reset()
        self.foo_bundle = Bundle()
        self.bar_bundle = Bundle()
        django_env_register('foo_bundle', self.foo_bundle)
        django_env_register('bar_bundle', self.bar_bundle)

    def teardown(self):
        AssetsNode.BundleClass = self._old_bundle_class
        del self._old_bundle_class

    def render_template(self, args, ctx={}):
        return Template('{% load assets %}{% assets '+args+' %}{{ ASSET_URL }};{% endassets %}').render(Context(ctx))

    def test_reference_bundles(self):
        self.render_template('"foo_bundle", "bar_bundle"')
        assert self.the_bundle.contents == (self.foo_bundle, self.bar_bundle)

    def test_reference_files(self):
        self.render_template('"file1", "file2", "file3"')
        assert self.the_bundle.contents == ('file1', 'file2', 'file3',)

    def test_reference_mixed(self):
        self.render_template('"foo_bundle", "file2", "file3"')
        assert self.the_bundle.contents == (self.foo_bundle, 'file2', 'file3',)

    def test_with_vars(self):
        self.render_template('var1 var2', {'var1': self.foo_bundle, 'var2': 'a_file'})
        assert self.the_bundle.contents == (self.foo_bundle, 'a_file',)

    def test_debug_option(self):
        self.render_template('"file", debug="true"')
        assert self.the_bundle.debug == True
        self.render_template('"file", debug="false"')
        assert self.the_bundle.debug == False
        self.render_template('"file", debug="merge"')
        assert self.the_bundle.debug == "merge"

    def test_with_no_commas(self):
        """Using commas is optional.
        """
        self.render_template('"file1" "file2" "file3"')

    def test_output_urls(self):
        """Ensure the tag correcly spits out the urls the bundle returns.
        """
        self.BundleClass.urls_to_fake = ['foo', 'bar']
        assert self.render_template('"file1" "file2" "file3"') == 'foo;bar;'


class TestLoader(TempDirHelper):

    default_files = {
        'template.html': """
            {% load assets %}
            <h1>Test</h1>
            {% if foo %}
                {% assets "A" "B" "C" output="output.html" %}
                    {{ ASSET_URL }}
                {% endassets %}
            {% endif %}
            """
    }

    def setup(self):
        TempDirHelper.setup(self)

        self.loader = DjangoLoader()
        settings.TEMPLATE_LOADERS = [
            'django.template.loaders.filesystem.Loader',
        ]
        settings.TEMPLATE_DIRS = [self.tempdir]

    def test(self):
        bundles = self.loader.load_bundles()
        assert len(bundles) == 1
        assert bundles[0].output == "output.html"

    def test_cached_loader(self):
        settings.TEMPLATE_LOADERS = (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                )),
            )
        bundles = self.loader.load_bundles()
        assert len(bundles) == 1
        assert bundles[0].output == "output.html"


class TestStaticFiles(TempEnvironmentHelper):
    """Test integration with django.contrib.staticfiles.
    """

    def setup(self):
        try:
            import django.contrib.staticfiles
        except ImportError:
            raise SkipTest()

        TempEnvironmentHelper.setup(self)

        # Configure a staticfiles-using project.
        settings.STATIC_ROOT = settings.MEDIA_ROOT   # /media via baseclass
        settings.MEDIA_ROOT = self.path('needs_to_differ_from_static_root')
        settings.STATIC_URL = '/media/'
        settings.INSTALLED_APPS += ('django.contrib.staticfiles',)
        settings.STATICFILES_DIRS = tuple(self.create_directories('foo', 'bar'))
        settings.STATICFILES_FINDERS += ('django_assets.finders.AssetsFinder',)
        self.create_files({'foo/file1': 'foo', 'bar/file2': 'bar'})
        settings.DEBUG = True

        # Reset the finders cache after each run, since our
        # STATICFILES_DIRS change every time.
        from django.contrib.staticfiles import finders
        finders._finders.clear()

    def test_build(self):
        """Finders are used to find source files.
        """
        self.mkbundle('file1', 'file2', output="out").build()
        assert self.get("media/out") == "foo\nbar"

    def test_build_nodebug(self):
        """If debug is disabled, the finders are not used.
        """
        settings.DEBUG = False
        bundle = self.mkbundle('file1', 'file2', output="out")
        assert_raises(BundleError, bundle.build)

        # After creating the files in the static root directory,
        # it works (we only look there in production).
        from django.core.management import call_command
        call_command("collectstatic", interactive=False)

        bundle.build()
        assert self.get("media/out") == "foo\nbar"

    def test_find_with_glob(self):
        """Globs can be used across staticdirs."""
        self.mkbundle('file?', output="out").build()
        assert self.get("media/out") == "foo\nbar"

    def test_find_with_recursive_glob(self):
        """Recursive globs."""
        self.create_files({'foo/subdir/foundit.js': '42'})
        self.mkbundle('**/*.js', output="out").build()
        assert self.get("media/out") == "42"

    def test_missing_file(self):
        """An error is raised if a source file is missing.
        """
        bundle = self.mkbundle('xyz', output="out")
        assert_raises_regexp(
            BundleError, 'using staticfiles finders', bundle.build)

    def test_serve_built_files(self):
        """The files we write to STATIC_ROOT are served in debug mode
        using "django_assets.finders.AssetsFinder".
        """
        self.mkbundle('file1', 'file2', output="out").build()
        # I tried using the test client for this, but it would
        # need to be setup using StaticFilesHandler, which is
        # incompatible with the test client.
        from django_assets.finders import AssetsFinder
        assert AssetsFinder().find('out') == self.path("media/out")

    def test_css_rewrite(self):
        """Test that the cssrewrite filter can deal with staticfiles.
        """
        # file1 is in ./foo, file2 is in ./bar, the output will be
        # STATIC_ROOT = ./media
        self.create_files(
                {'foo/css': 'h1{background: url("file1"), url("file2")}'})
        self.mkbundle('css', filters='cssrewrite', output="out").build()
        # The urls are NOT rewritte to foo/file1, but because all three
        # directories are essentially mapped into the same url space, they
        # remain as is.
        assert self.get('media/out') == \
                '''h1{background: url("file1"), url("file2")}'''


class TestFilter(TempEnvironmentHelper):

    def test_template(self):
        self.create_files({'media/foo.html': '{{ num|filesizeformat }}'})
        self.mkbundle('foo.html', output="out",
                      filters=get_filter('template', context={'num': 23232323})).build()
        assert self.get('media/out') == '22.2 MB'

########NEW FILE########
