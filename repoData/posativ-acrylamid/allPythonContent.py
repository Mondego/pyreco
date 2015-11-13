__FILENAME__ = fallback
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from itertools import chain
from acrylamid.utils import cached_property

Bundle = lambda *args, **kwargs: None


class Webassets(object):

    def __init__(self, conf, env):
        pass

    def excludes(self, directory):
        return []

    def compile(self, *args, **kwargs):
        return ""


class Mixin(object):

    @cached_property
    def modified(self):
        """Iterate template dependencies for modification."""

        for item in chain([self.path], self.loader.resolved[self.path]):
            if self.loader.modified[item]:
                return True

        return False

########NEW FILE########
__FILENAME__ = web
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import os

from os.path import join, isdir, dirname, getmtime, relpath
from itertools import chain

from acrylamid import core
from acrylamid.compat import map

from acrylamid.utils import cached_property
from acrylamid.helpers import event

from webassets.env import Environment, Resolver
from webassets.merge import FileHunk
from webassets.bundle import Bundle, has_placeholder
from webassets.updater import TimestampUpdater
from webassets.version import HashVersion


class Acrylresolver(Resolver):

    def __init__(self, conf, environment):
        super(Acrylresolver, self).__init__(environment)
        self.conf = conf

    def resolve_output_to_path(self, target, bundle):

        if not target.startswith(self.conf.output_dir):
            target = join(self.conf.output_dir, target)

        if not isdir(dirname(target)):
            os.makedirs(dirname(target))

        return target


class Acrylupdater(TimestampUpdater):
    """Keep incremental compilation even with ``depends``, which is currently
    not provided by webassets: https://github.com/miracle2k/webassets/pull/220.
    """
    id = 'acrylic'
    used, new = set(), set()

    def build_done(self, bundle, env):
        func = event.create if bundle in self.new else event.update
        func('webassets', bundle.resolve_output(env))
        return super(Acrylupdater, self).build_done(bundle, env)

    def needs_rebuild(self, bundle, env):

        if super(TimestampUpdater, self).needs_rebuild(bundle, env):
            return True

        try:
            dest = getmtime(bundle.resolve_output(env))
        except OSError:
            return self.new.add(bundle) or True

        src = [s[1] for s in bundle.resolve_contents(env)]
        deps = bundle.resolve_depends(env)

        for item in src + deps:
            self.used.add(item)

        if any(getmtime(deps) > dest for deps in src + deps):
            return True

        event.skip('assets', bundle.resolve_output(env))

        return False


class Acrylversion(HashVersion):
    """Hash based on the input (+ depends), not on the output."""

    id = 'acrylic'

    def determine_version(self, bundle, env, hunk=None):

        if not hunk and not has_placeholder(bundle.output):
            hunks = [FileHunk(bundle.resolve_output(env)), ]
        elif not hunk:
            src = sum(map(env.resolver.resolve_source, bundle.contents), [])
            hunks = [FileHunk(hunk) for hunk in src + bundle.resolve_depends(env)]
        else:
            hunks = [hunk, ]

        hasher = self.hasher()
        for hunk in hunks:
            hasher.update(hunk.data())
        return hasher.hexdigest()[:self.length]


class Webassets(object):

    def __init__(self, conf, env):
        self.conf = conf
        self.env = env

        self.environment = Environment(
            directory=conf.theme, url=env.path,
            updater='acrylic', versions='acrylic',
            cache=core.cache.cache_dir, load_path=[conf.theme])

        # fix output directory creation
        self.environment.resolver = Acrylresolver(conf, self.environment)

    def excludes(self, directory):
        """Return used assets relative to :param:`directory`."""
        return [relpath(p, directory) for p in self.environment.updater.used]

    def compile(self, *args, **kw):

        assert 'output' in kw
        kw.setdefault('debug', False)

        bundle = Bundle(*args, **kw)
        for url in bundle.urls(env=self.environment):
            yield url


class Mixin:

    @cached_property
    def modified(self):
        """Iterate template dependencies for modification and check web assets
        if a bundle needs to be rebuilt."""

        for item in chain([self.path], self.loader.resolved[self.path]):
            if self.loader.modified[item]:
                return True

        for args, kwargs in self.loader.assets[self.path]:
            kwargs.setdefault('debug', False)
            bundle = Bundle(*args, **kwargs)
            rv = self.environment.webassets.environment.updater.needs_rebuild(
                bundle, self.environment.webassets.environment)
            if rv:
                return True

        return False

########NEW FILE########
__FILENAME__ = colors
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import sys

from acrylamid import compat
from acrylamid.compat import text_type as str, string_types

if sys.platform == 'win32':
    import colorama
    colorama.init()


@compat.implements_to_string
class ANSIString(object):

    style = 0
    color = 30

    def __init__(self, obj, style=None, color=None):

        if isinstance(obj, ANSIString):
            if style is None:
                style = obj.style
            if color is None:
                color = obj.color
            obj = obj.obj
        elif not isinstance(obj, string_types):
            obj = str(obj)

        self.obj = obj
        if style:
            self.style = style
        if color:
            self.color = color

    def __str__(self):
        return '\033[%i;%im' % (self.style, self.color) + self.obj + '\033[0m'

    def __add__(self, other):
        return str.__add__(str(self), other)

    def __radd__(self, other):
        return other + str(self)

    def encode(self, encoding):
        return str(self).encode(encoding)


normal, bold, underline = [lambda obj, x=x: ANSIString(obj, style=x)
    for x in (0, 1, 4)]

black, red, green, yellow, blue, \
magenta, cyan, white = [lambda obj, y=y: ANSIString(obj, color=y)
    for y in range(30, 38)]

########NEW FILE########
__FILENAME__ = commands
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import print_function

import sys
import os
import time
import locale

from datetime import datetime
from itertools import chain
from collections import defaultdict
from os.path import getmtime

from distutils.version import LooseVersion

from acrylamid import log, compat
from acrylamid.compat import iteritems, iterkeys, string_types, text_type as str
from acrylamid.errors import AcrylamidException

from acrylamid import readers, filters, views, assets, refs, hooks, helpers, dist
from acrylamid.lib import lazy, history
from acrylamid.core import cache, load, Environment
from acrylamid.utils import hash, HashableList, import_object, OrderedDict as dict
from acrylamid.utils import total_seconds
from acrylamid.helpers import event

if compat.PY2K:
    from urlparse import urlsplit
else:
    from urllib.parse import urlsplit


def initialize(conf, env):
    """Initializes Jinja2 environment, prepares locale and configure
    some minor things. Filter and View are inited with conf and env,
    a data dict is returned.
    """
    # initialize cache, optional to cache_dir
    cache.init(conf.get('cache_dir'))

    env['version'] = type('Version', (str, ), dict(zip(
        ['major', 'minor'], LooseVersion(dist.version).version[:2])))(dist.version)

    # crawl through CHANGES.md and stop on breaking changes
    if history.breaks(env, cache.emptyrun):
        cache.shutdown()
        print("Detected version upgrade that might break your configuration. Run")
        print("Acrylamid a second time to get rid of this message and premature exit.")
        raise SystemExit

    # set up templating environment
    env.engine = import_object(conf['engine'])(conf['theme'], cache.cache_dir)
    env.engine.register('safeslug', helpers.safeslug)
    env.engine.register('tagify', lambda x: x)

    # try language set in LANG, if set correctly use it
    try:
        locale.setlocale(locale.LC_ALL, str(conf.get('lang', '')))
    except (locale.Error, TypeError):
        # try if LANG is an alias
        try:
            locale.setlocale(locale.LC_ALL, locale.locale_alias[str(conf.get('lang', '')).lower()])
        except (locale.Error, KeyError):
            # LANG is not an alias, so we use system's default
            try:
                locale.setlocale(locale.LC_ALL, '')
            except locale.Error:
                pass  # hope this makes Travis happy
            log.info('notice  your OS does not support %s, fallback to %s', conf.get('lang', ''),
                     locale.getlocale()[0])
    if locale.getlocale()[0] is not None:
        conf['lang'] = locale.getlocale()[0][:2]
    else:
        # getlocale() is (None, None) aka 'C'
        conf['lang'] = 'en'

    if 'www_root' not in conf:
        log.warn('no `www_root` specified, using localhost:8000')
        conf['www_root'] = 'http://localhost:8000/'

    # figure out timezone and set offset, more verbose for 2.6 compatibility
    td = (datetime.now() - datetime.utcnow())
    offset = round(total_seconds(td) / 3600.0)
    conf['tzinfo'] = readers.Timezone(offset)

    # determine http(s), host and path
    env['protocol'], env['netloc'], env['path'], x, y = urlsplit(conf['www_root'])

    # take off the trailing slash for www_root and path
    conf['www_root'] = conf['www_root'].rstrip('/')
    env['path'] = env['path'].rstrip('/')

    if env['path']:
        conf['output_dir'] = conf['output_dir'] + env['path']

    lazy.enable()
    filters.initialize(conf["filters_dir"][:], conf, env)
    lazy.disable()  # this has weird side effects with jinja2, so disabled after filters

    views.initialize(conf["views_dir"][:], conf, env)
    env.views = views.Views(view for view in views.get_views())

    entryfmt, pagefmt = '/:year/:slug/', '/:slug/'
    for view in views.get_views():
        if view.name == 'entry':
            entryfmt = view.path
        if view.name == 'page':
            pagefmt = view.path

    conf.setdefault('entry_permalink', entryfmt)
    conf.setdefault('page_permalink', pagefmt)

    # register webassets to theme engine, make webassets available as env.webassets
    assets.initialize(conf, env)

    return {'conf': conf, 'env': env}


def compile(conf, env):
    """The compilation process."""

    hooks.initialize(conf, env)
    hooks.run(conf, env, 'pre')

    if env.options.force:
        cache.clear(conf.get('cache_dir'))

    # time measurement
    ctime = time.time()

    # populate env and corrects some conf things
    data = initialize(conf, env)

    # load pages/entries and store them in env
    rv = dict(zip(['entrylist', 'pages', 'translations', 'drafts'],
        map(HashableList, readers.load(conf))))

    entrylist, pages = rv['entrylist'], rv['pages']
    translations, drafts = rv['translations'], rv['drafts']

    # load references
    refs.load(entrylist, pages, translations, drafts)

    data.update(rv)
    env.globals.update(rv)

    # here we store all found filter and their aliases
    ns = defaultdict(set)

    # [<class head_offset.Headoffset at 0x1014882c0>, <class html.HTML at 0x101488328>,...]
    aflist = filters.get_filters()

    # ... and get all configured views
    _views = views.get_views()

    # filters found in all entries, views and conf.py (skip translations, has no items)
    found = sum((x.filters for x in chain(entrylist, pages, drafts, _views, [conf])), [])

    for val in found:
        # first we for `no` and get the function name and arguments
        f = val[2:] if val.startswith('no') else val
        fname, fargs = f.split('+')[:1][0], f.split('+')[1:]

        try:
            # initialize the filter with its function name and arguments
            fx = aflist[fname](conf, env, val, *fargs)
            if val.startswith('no'):
                fx = filters.disable(fx)
        except ValueError:
            try:
                fx = aflist[val.split('+')[:1][0]](conf, env, val, *fargs)
            except ValueError:
                raise AcrylamidException('no such filter: %s' % val)

        ns[fx].add(val)

    # include actual used filters to trigger modified state
    env.filters = HashableList(iterkeys(ns))

    for entry in chain(entrylist, pages, drafts):
        for v in _views:

            # a list that sorts out conflicting and duplicated filters
            flst = filters.FilterList()

            # filters found in this specific entry plus views and conf.py
            found = entry.filters + v.filters + data['conf']['filters']

            for fn in found:
                fx, _ = next((k for k in iteritems(ns) if fn in k[1]))
                if fx not in flst:
                    flst.append(fx)

            # sort them ascending because we will pop within filters.add
            entry.filters.add(sorted(flst, key=lambda k: (-k.priority, k.name)),
                              context=v)

    # lets offer a last break to populate tags and such
    for v in _views:
        env = v.context(conf, env, data)

    # now teh real thing!
    for v in _views:

        for entry in chain(entrylist, pages, translations, drafts):
            entry.context = v

        for var in 'entrylist', 'pages', 'translations', 'drafts':
            data[var] = HashableList(filter(v.condition, locals()[var])) \
                if v.condition else locals()[var]

        tt = time.time()
        for buf, path in v.generate(conf, env, data):
            try:
                helpers.mkfile(buf, path, time.time()-tt, ns=v.name,
                    force=env.options.force, dryrun=env.options.dryrun)
            except UnicodeError:
                log.exception(path)
            finally:
                buf.close()
            tt = time.time()

    # copy modified/missing assets to output
    assets.compile(conf, env)

    # wait for unfinished hooks
    hooks.shutdown()

    # run post hooks (blocks)
    hooks.run(conf, env, 'post')

    # save conf/environment hash and new/changed/unchanged references
    helpers.memoize('Configuration', hash(conf))
    helpers.memoize('Environment', hash(env))
    refs.save()

    # remove abandoned cache files
    cache.shutdown()

    # print a short summary
    log.info('%i new, %i updated, %i skipped [%.2fs]', event.count('create'),
             event.count('update'), event.count('identical') + event.count('skip'),
             time.time() - ctime)


def autocompile(ws, conf, env):
    """Subcommand: autocompile -- automatically re-compiles when something in
    content-dir has changed and parallel serving files."""

    mtime = -1
    cmtime = getmtime('conf.py')

    # config content_extension originally defined as string, not a list
    exts = conf.get('content_extension',['.txt', '.rst', '.md'])
    if isinstance(exts, string_types):
        whitelist = (exts,)
    else:
        whitelist = tuple(exts)

    while True:

        ws.wait = True
        ntime = max(
            max(getmtime(e) for e in readers.filelist(
                conf['content_dir'], conf['content_ignore']) if e.endswith(whitelist)),
            max(getmtime(p) for p in chain(
                readers.filelist(conf['theme'], conf['theme_ignore']),
                readers.filelist(conf['static'], conf['static_ignore']))))

        if mtime != ntime:
            try:
                compile(conf, env)
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception:
                log.exception("uncaught exception during auto-compilation")
            else:
                conf = load(env.options.conf)
                env = Environment.new(env)
            event.reset()
            mtime = ntime
        ws.wait = False

        if cmtime != getmtime('conf.py'):
            log.info(' * Restarting due to change in conf.py')
            # Kill the webserver
            ws.shutdown()
            # Restart acrylamid
            os.execvp(sys.argv[0], sys.argv)

        time.sleep(1)


__all__ = ["compile", "autocompile"]

########NEW FILE########
__FILENAME__ = compat
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Armin Ronacher <armin.ronacher@active-4.com>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.
#
# http://lucumr.pocoo.org/2013/5/21/porting-to-python-3-redux/

import sys
PY2K = sys.version_info[0] == 2

if not PY2K:

    unichr = chr
    text_type = str
    string_types = (str, )
    implements_to_string = lambda x: x

    map, zip, filter = map, zip, filter

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

else:

    unichr = unichr
    text_type = unicode
    string_types = (str, unicode)

    from itertools import imap, izip, ifilter
    map, zip, filter = imap, izip, ifilter

    def implements_to_string(cls):

        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: x.__unicode__().encode('utf-8')
        return cls

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()


def metaclass(meta, *bases):

    class Meta(meta):

        __call__ = type.__call__
        __init__ = type.__init__

        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)

    return Meta('temporary_class', None, {})

########NEW FILE########
__FILENAME__ = core
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.
#
# This provide some basic functionality of Acrylamid: caching and re-validating.

import os
import io
import zlib
import types
import pickle
import shutil
import tempfile

from os.path import join, exists, getmtime, getsize, dirname, basename

from acrylamid import log, defaults
from acrylamid.errors import AcrylamidException
from acrylamid.compat import PY2K, iteritems, iterkeys

from acrylamid.utils import (
    classproperty, cached_property, Struct, hash, HashableList, find, execfile,
    lchop, force_unicode as u
)

if PY2K:
    import cPickle as pickle

__all__ = ['Memory', 'cache', 'Environment', 'Configuration']


class Memory(dict):
    """A callable dictionary object described at
    :func:`acrylamid.helpers.memoize`."""

    def __call__(self, key, value=None):
        if value is None:
            return self.get(key)

        rv = self.get(key)
        self[key] = value
        return rv != value


class cache(object):
    """A cache that stores all intermediates of an entry zlib-compressed on
    file system. Inspired from ``werkzeug.contrib.cache``, but heavily modified
    to fit our needs.

    Terminology: A cache object is a pickled dictionary into a single file. An
    intermediate (object) is a key/value pair that we store into a cache object.
    An intermediate is the content of an entry that is the same for a chain of
    filters used in different views.

    :class:`cache` is designed as global singleton and should not be constructed.

    .. attribute:: cache_dir

       Location where all cache objects are being stored, defaults to `.cache/`.

    The :class:`cache` does no longer maintain used/unused intermediates and cache
    objects due performance reasons (and an edge case described in #67)."""

    _fs_transaction_suffix = '.__ac_cache'
    cache_dir = '.cache/'
    mode = 0o600

    memoize = Memory()

    @classmethod
    def init(self, cache_dir=None):
        """Initialize cache object by creating the cache_dir if non-existent,
        read all available cache objects and restore memoized key/values.

        :param cache_dir: the directory where cache files are stored.
        :param mode: the file mode wanted for the cache files, default 0600
        """
        if cache_dir:
            self.cache_dir = cache_dir

        if not exists(self.cache_dir):
            try:
                os.mkdir(self.cache_dir, 0o700)
            except OSError:
                raise AcrylamidException("could not create directory '%s'" % self.cache_dir)

        # load memorized items
        try:
            with io.open(join(self.cache_dir, 'info'), 'rb') as fp:
                self.memoize.update(pickle.load(fp))
        except (IOError, pickle.PickleError):
            self.emptyrun = True
        else:
            self.emptyrun = False

    @classmethod
    def shutdown(self):
        """Write memoized key-value pairs to disk."""
        try:
            with io.open(join(self.cache_dir, 'info'), 'wb') as fp:
                pickle.dump(self.memoize, fp, pickle.HIGHEST_PROTOCOL)
        except (IOError, pickle.PickleError) as e:
            log.warn('%s: %s' % (e.__class__.__name__, e))

    @classmethod
    def remove(self, path):
        """Remove a cache object completely from disk and `objects`."""
        try:
            os.remove(join(self.cache_dir, path))
        except OSError as e:
            log.debug('OSError: %s' % e)

    @classmethod
    def clear(self, directory=None):
        """Wipe current cache objects and reset all stored informations.

        :param directory: directory to clean (defaults to `.cache/`"""

        if directory is not None:
            self.cache_dir = directory

        self.memoize = Memory()
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    @classmethod
    def get(self, path, key, default=None):
        """Restore value from obj[key] if mtime has not changed or return
        default.

        :param path: path of this cache object
        :param key: key of this value
        :param default: default return value
        """
        try:
            with io.open(join(self.cache_dir, path), 'rb') as fp:
                return zlib.decompress(pickle.load(fp)[key]).decode('utf-8')
        except KeyError:
            pass
        except (IOError, pickle.PickleError, zlib.error):
            self.remove(join(self.cache_dir, path))

        return default

    @classmethod
    def set(self, path, key, value):
        """Save a key, value pair into a blob using pickle and moderate zlib
        compression (level 6). We simply save a dictionary containing all
        different intermediates (from every view) of an entry.

        :param path: path of this cache object
        :param key: dictionary key where we store the value
        :param value: a string we compress with zlib and afterwards save
        """
        path = join(self.cache_dir, path)

        if exists(path):
            try:
                with io.open(path, 'rb') as fp:
                    rv = pickle.load(fp)
            except (pickle.PickleError, IOError):
                self.remove(path)
                rv = {}
            try:
                with io.open(path, 'wb') as fp:
                    rv[key] = zlib.compress(value.encode('utf-8'), 6)
                    pickle.dump(rv, fp, pickle.HIGHEST_PROTOCOL)
            except (IOError, pickle.PickleError) as e:
                log.warn('%s: %s' % (e.__class__.__name__, e))
        else:
            try:
                fd, tmp = tempfile.mkstemp(suffix=self._fs_transaction_suffix,
                                           dir=self.cache_dir)
                with io.open(fd, 'wb') as fp:
                    pickle.dump({key: zlib.compress(value.encode('utf-8'), 6)}, fp,
                                pickle.HIGHEST_PROTOCOL)
                os.rename(tmp, path)
                os.chmod(path, self.mode)
            except (IOError, OSError, pickle.PickleError, zlib.error) as e:
                log.warn('%s: %s' % (e.__class__.__name__, e))

        return value

    @classmethod
    def getmtime(self, path, default=0.0):
        """Get last modification timestamp from cache object but store it over
        the whole compilation process so we have the same value for different
        views.

        :param path: valid cache object
        :param default: default value if an :class:`OSError` occurs
        """
        try:
            return getmtime(join(self.cache_dir, path))
        except OSError:
            return default

    @classproperty
    @classmethod
    def size(self):
        """return size of all cacheobjects in bytes"""
        try:
            res = getsize(join(self.cache_dir, 'info'))
        except OSError:
            res = 0
        for (path, dirs, files) in os.walk(self.cache_dir):
            for file in files:
                filename = os.path.join(path, file)
                res += getsize(filename)
        return res


def load(path):
    """Load default configuration, prepare namespace and update configuration
    with `conf.py`'s uppercase values and normalizes ambiguous values.
    """
    conf = Configuration(defaults.conf)
    ns = dict([(k.upper(), v) for k, v in iteritems(defaults.conf)])

    os.chdir(dirname(find(basename(path), u(dirname(path) or os.getcwd()))))

    if PY2K:
        execfile(path, ns)
    else:
        exec(compile(open(path).read(), path, 'exec'), ns)

    conf.update(dict([(k.lower(), ns[k]) for k in ns if k.upper() == k]))

    # append trailing slash to *_dir and place certain values into an array
    return defaults.normalize(conf)


class Environment(Struct):
    """Use *only* for the environment container.  This class hides un-hashable
    keys from :class:`Struct` hash function.

    .. attribute:: modified

        Return whether the Environment has changed between two runs. This
        attribute must only be accessed after all modifications to the environment!
    """
    blacklist = set(['engine', 'translationsfor', 'options', 'archives', 'webassets'])

    @classmethod
    def new(self, env):
        return Environment({'author': env.author, 'url': env.url,
            'options': env.options, 'globals': Struct()})

    def keys(self):
        return sorted(list(set(super(Environment, self).keys()) - self.blacklist))

    def values(self):
        for key in self.keys():
            yield self[key]

    @cached_property
    def modified(self):
        return hash(self) != cache.memoize(self.__class__.__name__)


class Configuration(Environment):
    """Similar to :class:`Environment` but allows hashing of a literarily
    defined dictionary (that's the conf.py)."""

    blacklist = set(['if', 'hooks'])

    def fetch(self, ns):
        return Configuration((lchop(k, ns), v)
            for k, v in iteritems(self) if k.startswith(ns))

    def values(self):
        for key in self.keys():
            if isinstance(self[key], types.FunctionType):
                continue

            if isinstance(self[key], list):
                yield HashableList(self[key])
            elif isinstance(self[key], dict):
                yield Configuration(self[key])
            elif isinstance(self[key], type(None)):
                yield -1
            else:
                yield self[key]

########NEW FILE########
__FILENAME__ = defaults
# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import io
from os.path import join, dirname

from acrylamid import log, compat

copy = lambda path: io.open(join(dirname(__file__), path), 'rb')

__ = ['*.swp', ]

conf = {
    'sitename': 'A descriptive blog title',
    'author': 'Anonymous',
    'email': 'info@example.com',

    'date_format': '%d.%m.%Y, %H:%M',
    'encoding': 'utf-8',
    'permalink_format': '/:year/:slug/',

    # pagination
    'default_orphans': 0,

    # tag cloud
    'tag_cloud_max_items': 100,
    'tag_cloud_steps': 4,
    'tag_cloud_start_index': 0,
    'tag_cloud_shuffle': False,

    # filter & view configuration
    'filters_dir': [],
    'views_dir': [],

    'filters': ['markdown+codehilite(css_class=highlight)', 'hyphenate'],
    'views': {
    },

    # user dirs
    'output_dir': 'output/',
    'output_ignore': ['.git*', '.hg*', '.svn'],

    'content_dir': 'content/',
    'content_ignore': ['.git*', '.hg*', '.svn'] + __,
    'content_extension': ['.txt', '.rst', '.md'],

    'theme': 'layouts/',
    'theme_ignore': ['.git*', '.hg*', '.svn'] + __,

    'static': None,
    'static_ignore': ['.git*', '.hg*', '.svn'] + __,
    'static_filter': ['Template', 'XML'],

    'engine': 'acrylamid.templates.jinja2.Environment',
}


def normalize(conf):

    # metastyle has been removed
    if 'metastyle' in conf:
        log.info('notice  METASTYLE is no longer needed to determine the metadata format ' + \
                 'and can be removed.')

    # deprecated since 0.8
    if isinstance(conf['static'], list):
        conf['static'] = conf['static'][0]
        log.warn("multiple static directories has been deprecated, " + \
                 "Acrylamid continues with '%s'.", conf['static'])

    # deprecated since 0.8
    for fx in 'Jinja2', 'Mako':
        try:
            conf['static_filter'].remove(fx)
        except ValueError:
            pass
        else:
            log.warn("%s asset filter has been renamed to `Template` and is "
                     "included by default.", fx)


    for key in 'content_dir', 'theme', 'static', 'output_dir':
        if conf[key] is not None and not conf[key].endswith('/'):
            conf[key] += '/'

    for key in 'views_dir', 'filters_dir':
        if isinstance(conf[key], compat.string_types):
            conf[key] = [conf[key], ]

    return conf

########NEW FILE########
__FILENAME__ = errors
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.


class AcrylamidException(Exception):
    pass

########NEW FILE########
__FILENAME__ = acronyms
# -*- encoding: utf-8 -*-
#
# Copyright (c) 2010, 2011 Will Kahn-Greene
#
# Pyblosxom is distributed under the MIT license.  See the file
# LICENSE for distribution details.
#
# -- http://pyblosxom.bluesock.org/
#
# This is a port of PyBlosxom's acronyms plugin as Acrylamid
# filter. All credits go to Pyblosxom's and blosxom's authors.

import os
import io
import re

from acrylamid import log
from acrylamid.compat import iteritems, filter
from acrylamid.filters import Filter

from acrylamid.lib.html import HTMLParser, HTMLParseError


class Acrynomify(HTMLParser):

    def __init__(self, html, abbr, repl):
        self.abbr = abbr
        self.repl = repl

        HTMLParser.__init__(self, html)

    def handle_data(self, data):
        if any(filter(lambda i: i in self.stack, ['pre', 'code', 'math', 'script'])):
            pass
        else:
            data = self.abbr.sub(self.repl, data)
        self.result.append(data)


class Acronyms(Filter):

    match = [re.compile('^Acronyms?$', re.I), 'abbr', 'Abbr']
    version = 2

    # after Typography, so CAPS is around ABBR
    priority = 20.0

    @property
    def uses(self):
        try:
            return os.path.getmtime(self.conf['acronyms_file'])
        except KeyError:
            return ACRONYMS

    def init(self, conf, env):

        if conf.get('acronyms_file', None):
            with io.open(conf['acronyms_file'], 'r', encoding='utf-8') as fp:
                data = fp.readlines()
        else:
            global ACRONYMS
            data = ACRONYMS.split('\n')

        acronyms = {}
        for line in data:
            line = line.split("=", 1)
            firstpart = line[0].strip()

            secondpart = line[1].strip()
            secondpart = secondpart.replace("\"", "&quot;")

            if secondpart.startswith("abbr|"):
                secondpart = secondpart[5:]
            elif secondpart.startswith("acronym|"):
                secondpart = secondpart[8:]

            acronyms[re.compile(firstpart)] = secondpart

        self.acronyms = acronyms

    def transform(self, text, entry, *args):

        acros = self.acronyms
        if len(args) > 0:
            acros = dict(filter(lambda k: any(k[0] == v for v in args), iteritems(acros)))

        try:
            abbr = re.compile(r'\b(%s)\b' % '|'.join((pat.pattern for pat in acros)))
        except re.error as e:
            log.warn("acronyms: %s", e.args[0])

        def repl(match):

            abbr = match.group(0)
            desc = acros.get(abbr, None)

            if desc is None:
                for pat in acros:
                    if pat.match(abbr):
                        desc = acros.get(pat)
                        break
            return '<abbr title="%s">%s</abbr>' % (desc, abbr)

        try:
            return ''.join(Acrynomify(text, abbr, repl).result)
        except HTMLParseError:
            log.exception('could not acronymize ' + entry.filename)
            return text


ACRONYMS = r"""
ASCII=American Standard Code for Information Interchange
BGP=Border Gateway Protocol
BSD=Berkeley System Distribution
CGI=Common Gateway Interface
CLI=Command Line Interface
CLUE=Command Line User Environment
CSS=Cascading Stylesheets
CVS=Concurrent Versioning System
DSL=Digital Subscriber Line
EFF=Electronic Frontier Foundation
ELF=Executable and Linking Format
FAQ=Frequently asked question(s)
FFII=Foundation for a Free Information Infrastructure / F&ouml;rderverein f&uuml;r eine Freie Informationelle Infrastruktur
FIFO=First In, First Out
FLOSS=Free, Libre and Open Source Software
FOSS=Free and Open Source Software
FSF=Free Software Foundation
FSFE=Free Software Foundation Europe
GNOME=GNU Network Object Model Environment
GPL=GNU General Public License
GPRS=General Packet Radio Service
GSM=Global System for Mobile Communications
GUI=Graphical User Interface
HTML=Hypertext Markup Language
HTTP=Hypertext Transport Protocol
IMD[Bb]=Internet Movie Database
IRC=Internet Relay Chat
ISBN=International Standard Book Number
ISDN=Integrated Services Digital Network
ISO=International Organization for Standardization; also short for a image of an ISO9660 (CD-ROM) file system
ISSN=International Standard Serial Number
KDE=K-Desktop Environment; Kolorful Diskfilling Environment
KISS=Keep it simple, stupid
LIFO=Last In, First Out
LUG=Linux User Group
MCSE=Minesweeper Consultant and Solitaire Expert (User Friendly)
MMS=Multimedia Messaging Service
MMX=Multimedia Extension
MP3=MPEG (Moving Picture Experts Group) 1 Audio Layer 3
MPEG=Moving Picture Experts Group
MSIE=Microsoft Internet Explorer
NSFW=Not Safe For Work
OOP=Object-Oriented Programming
OS=Operating System; Open Source
OSI=Open Source Initiative; Open Systems Interconnection
OSS=Open Source Software
PHP[2345]?=Programmers Hate PHP ;-)
QA=Quality Assurance
RAM=Random Access Memory
ROM=Read Only Memory
SMD=Surface Mounted Devices
SMS=Short Message Service
SMTP=Simple Mail Transfer Protocol
SPF=Sender Policy Framework, formerly Sender Permitted From
SSI=Server-Side Includes
TLA=Three Letter Acronym
UI=User Interface
UMTS=Universal Mobile Telecommunications System
URI=Uniform Resource Indicator
URL=Uniform Resource Locator
USB=Universal Serial Bus
VM=Virtual Machine
VoIP=Voice over IP
WYSIWYG=What you see is what you get
XHTML=Extensible Hypertext Markup Language
XML=Extensible Markup Language
""".strip()

########NEW FILE########
__FILENAME__ = head_offset
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid.filters import Filter
from re import sub


class Headoffset(Filter):
    """This filter increases HTML headings by N whereas N is the suffix of
    this filter, e.g. `h2' increases headers by two."""

    version = 1

    def transform(self, text, entry, *args):

        def f(m):
            i = int(m.group(1))+1
            return ''.join(['<h%i' % i, m.group(2), '>', m.group(3), '</h%i>' % i])

        for i in range(int(self.name[1])):
            text = sub(r'<h([12345])([^>]*)>(.+)</h\1>', f, text)

        return text


for offset in range(1, 6):
    var = 'h%i' % offset
    globals()[var] = type(var, (Headoffset, ), {
        'match': [var],
        'conflicts': ['h%i' % i for i in set([1, 2, 3, 4, 5]) - set([offset])]
    })

########NEW FILE########
__FILENAME__ = html
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import re
from acrylamid.filters import Filter


class HTML(Filter):

    match = [re.compile('^(pass|plain|X?HTML)$', re.I)]
    version = 1

    conflicts = ['rst', 'md']
    priority = 70.0

    def transform(self, content, entry, *filters):
        return content

########NEW FILE########
__FILENAME__ = hyphenation
# -*- encoding: utf-8 -*-
#
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid import log, utils
from acrylamid.filters import Filter
from acrylamid.compat import filter, text_type as str

from acrylamid.lib.html import HTMLParser, HTMLParseError

import os
import io
import re

from os.path import join, dirname, basename


class HyphenPatternNotFound(Exception):
    pass


class Hyphenator:
    """ Hyphenation, using Frank Liang's algorithm.

    This module provides a single function to hyphenate words.  hyphenate_word takes
    a string (the word), and returns a list of parts that can be separated by hyphens.

    >>> hyphenate_word("hyphenation")
    ['hy', 'phen', 'ation']
    >>> hyphenate_word("supercalifragilisticexpialidocious")
    ['su', 'per', 'cal', 'ifrag', 'ilis', 'tic', 'ex', 'pi', 'ali', 'do', 'cious']
    >>> hyphenate_word("project")
    ['project']

    Ned Batchelder, July 2007.
    This Python code is in the public domain."""

    __version__ = '1.0.20070709'

    def __init__(self, chars, patterns, exceptions=''):
        self.chars = str('[.' + chars + ']')
        self.tree = {}
        for pattern in patterns.split():
            self._insert_pattern(pattern)

        self.exceptions = {}
        for ex in exceptions.split():
            # Convert the hyphenated pattern into a point array for use later.
            self.exceptions[ex.replace('-', '')] = [0] + [int(h == '-') for h in re.split(r"[a-z]", ex)]

    def _insert_pattern(self, pattern):
        # Convert the a pattern like 'a1bc3d4' into a string of chars 'abcd'
        # and a list of points [ 1, 0, 3, 4 ].
        chars = re.sub('[0-9]', '', pattern)
        points = [int(d or 0) for d in re.split(self.chars, pattern)]

        # Insert the pattern into the tree.  Each character finds a dict
        # another level down in the tree, and leaf nodes have the list of
        # points.
        t = self.tree
        for c in chars:
            if c not in t:
                t[c] = {}
            t = t[c]
        t[None] = points

    def hyphenate_word(self, word):
        """ Given a word, returns a list of pieces, broken at the possible
            hyphenation points.
        """
        # Short words aren't hyphenated.
        if len(word) <= 4:
            return [word]
        # If the word is an exception, get the stored points.
        if word.lower() in self.exceptions:
            points = self.exceptions[word.lower()]
        else:
            work = '.' + word.lower() + '.'
            points = [0] * (len(work) + 1)
            for i in range(len(work)):
                t = self.tree
                for c in work[i:]:
                    if c in t:
                        t = t[c]
                        if None in t:
                            p = t[None]
                            for j in range(len(p)):
                                points[i + j] = max(points[i + j], p[j])
                    else:
                        break
            # No hyphens in the first two chars or the last two.
            points[1] = points[2] = points[-2] = points[-3] = 0

        # Examine the points to build the pieces list.
        pieces = ['']
        for c, p in zip(word, points[2:]):
            pieces[-1] += c
            if p % 2:
                pieces.append('')
        return pieces


class Separator(HTMLParser):
    """helper class to apply Hyphenator to each word except in pre, code,
    math and em tags."""

    def __init__(self, html, hyphenationfunc, length=10):
        self.hyphenate = hyphenationfunc
        self.length = length

        HTMLParser.__init__(self, html)

    def handle_data(self, data):
        """Hyphenate words longer than 10 characters."""

        if any(filter(lambda i: i in self.stack, ['pre', 'code', 'math', 'script'])):
            pass
        else:
            split = [word for word in re.split(r"[.:,\s!?+=\(\)/-]+", data)
                     if len(word) > self.length]
            for word in split:
                hyphenated = '&shy;'.join(self.hyphenate(word))
                data = data.replace(word, hyphenated)

        self.result.append(data)


def build(lang):
    """build the Hyphenator from given language.  If you want add more, see
    http://tug.org/svn/texhyphen/trunk/hyph-utf8/tex/generic/hyph-utf8/patterns/txt/ ."""

    def gethyph(lang, directory='hyph/', prefix='hyph-'):

        for la in [prefix + lang, prefix + lang[:2]]:
            for p in os.listdir(directory):
                f = os.path.basename(p)
                if f.startswith(la):
                    return join(directory, p)
        else:
            raise HyphenPatternNotFound("no hyph-definition found for '%s'" % lang)

    dir = os.path.join(dirname(__file__), 'hyph/')
    fpath = gethyph(lang, dir).rsplit('.', 2)[0]
    try:
        with io.open(fpath + '.chr.txt', encoding='utf-8') as f:
            chars = ''.join([line[0] for line in f.readlines()])
        with io.open(fpath + '.pat.txt', encoding='utf-8') as f:
            patterns = f.read()
    except IOError:
        raise HyphenPatternNotFound('hyph/%s.chr.txt or hyph/%s.pat.txt missing' % (lang, lang))

    hyphenator = Hyphenator(chars, patterns, exceptions='')
    del patterns
    del chars
    log.debug("built Hyphenator from <%s>" % basename(fpath))
    return hyphenator.hyphenate_word


class Hyphenate(Filter):

    match = [re.compile('^(H|h)yph')]
    version = 2
    priority = 20.0

    @utils.cached_property
    def default(self):
        try:
            # build default hyphenate_word using conf's lang (if available)
            return build(self.conf['lang'].replace('_', '-'))
        except HyphenPatternNotFound as e:
            log.warn(e.args[0])
            return lambda x: [x]

    def init(self, conf, env):
        self.conf = conf

    def transform(self, content, entry, *args):
        if entry.lang != self.conf['lang']:
            try:
                hyphenate_word = build(entry.lang.replace('_', '-'))
            except HyphenPatternNotFound as e:
                log.warn(e.args[0])
                hyphenate_word = lambda x: [x]
        else:
            hyphenate_word = self.default

        try:
            length = int(args[0])
        except (ValueError, IndexError) as e:
            if e.__class__.__name__ == 'ValueError':
                log.warn('Hyphenate: invalid length argument %r', args[0])
            length = 10

        try:
            return ''.join(Separator(content, hyphenate_word, length=length).result)
        except HTMLParseError as e:
            log.exception('could not hyphenate ' + entry.filename)
            return content

########NEW FILE########
__FILENAME__ = intro
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Mark van Lent <mark@vlent.nl>. All rights reserved.
# License: BSD Style, 2 clauses.

from acrylamid import log, helpers
from acrylamid.filters import Filter
from acrylamid.lib.html import HTMLParser, HTMLParseError


class Introducer(HTMLParser):
    paragraph_list = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol', 'pre', 'p']
    """List of root elements, which may be treated as paragraphs"""

    def __init__(self, html, maxparagraphs, href, options):
        self.maxparagraphs = maxparagraphs
        self.paragraphs = 0
        self.options = options
        self.href = href

        super(Introducer, self).__init__(html)

    def handle_starttag(self, tag, attrs):
        if self.paragraphs < self.maxparagraphs:
            super(Introducer, self).handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self.paragraphs >= self.maxparagraphs:
            pass
        elif len(self.stack) < 1 or (self.stack[0] not in self.paragraph_list and self.stack[-1] not in self.paragraph_list):
            pass
        else:
            self.result.append(data)

    def handle_endtag(self, tag):
        if self.paragraphs < self.maxparagraphs:
            if tag in self.paragraph_list:
                self.paragraphs += 1
            super(Introducer, self).handle_endtag(tag)

            if self.paragraphs == self.maxparagraphs:
                for x in self.stack[:]:
                    self.result.append('</%s>' % self.stack.pop())
                if self.options['link'] != '':
                    self.result.append(self.options['link'] % self.href)

    def handle_startendtag(self, tag, attrs):
        if self.paragraphs < self.maxparagraphs and tag not in self.options['ignore']:
            super(Introducer, self).handle_startendtag(tag, attrs)

    def handle_entityref(self, name):
        if self.paragraphs < self.maxparagraphs:
            super(Introducer, self).handle_entityref(name)

    def handle_charref(self, char):
        if self.paragraphs < self.maxparagraphs:
            super(Introducer, self).handle_charref(char)

    def handle_comment(self, comment):
        if self.paragraphs < self.maxparagraphs:
            super(Introducer, self).handle_comment(comment)


class Introduction(Filter):

    match = ['intro', ]
    version = 2
    priority = 15.0

    defaults = {
        'ignore': ['img', 'video', 'audio'],
        'link': '<span>&#8230;<a href="%s" class="continue">continue</a>.</span>'
    }

    @property
    def uses(self):
        return self.env.path

    def transform(self, content, entry, *args):
        options = helpers.union(Introduction.defaults, self.conf.fetch('intro_'))

        try:
            options.update(entry.intro)
        except AttributeError:
            pass

        try:
            maxparagraphs = int(options.get('maxparagraphs') or args[0])
        except (IndexError, ValueError) as ex:
            if isinstance(ex, ValueError):
                log.warn('Introduction: invalid maxparagraphs argument %r',
                         options.get('maxparagraphs') or args[0])
            maxparagraphs = 1

        try:
            return ''.join(Introducer(
                content, maxparagraphs, self.env.path+entry.permalink, options).result)
        except HTMLParseError as e:
            log.exception('could not extract intro from ' + entry.filename)
            return content
        return content

########NEW FILE########
__FILENAME__ = jinja2-templating
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import io
import re
import types

from os.path import join, isfile

from acrylamid import log
from acrylamid.errors import AcrylamidException
from acrylamid.compat import PY2K, text_type as str

from acrylamid.filters import Filter
from acrylamid.helpers import system as defaultsystem

from jinja2 import Environment, TemplateError


class Jinja2(Filter):
    """Jinja2 filter that pre-processes in Markdown/reStructuredText
    written posts. XXX: and offers some jinja2 extensions."""

    match = ['Jinja2', 'jinja2']
    version = 1

    priority = 90.0

    def init(self, conf, env, *args):

        def system(cmd, stdin=None):
            try:
                return defaultsystem(cmd, stdin, shell=True).strip()
            except (OSError, AcrylamidException) as e:
                log.warn('%s: %s' % (e.__class__.__name__, e.args[0]))
                return e.args[0]

        self.conf = conf
        self.env = env

        # jinja2 is limited and can't import any module
        import time, datetime, os.path
        modules = [time, datetime, os.path]

        # check config for imports
        confimports = conf.get('jinja2_import')
        if confimports and isinstance(confimports, list):
            for modname in confimports:
                try:
                    modules.append(__import__(modname))
                except ImportError as e:
                    log.exception('Failed loading user defined Jinja2 import: '
                                  '%s (JINJA2_IMPORT = %s)' % (e, confimports))

        if PY2K:
            import urllib
            modules += [urllib]
        else:
            import urllib.request, urllib.parse, urllib.error
            modules += [urllib.request, urllib.parse, urllib.error]

        if isinstance(env.engine._jinja2, Environment):
            self.jinja2_env = env.engine._jinja2.overlay(cache_size=0)
        else:
            self.jinja2_env = Environment(cache_size=0)

        self.jinja2_env.filters['system'] = system
        self.jinja2_env.filters['split'] = str.split

        # swap out platform specific os.path name (posixpath , ntpath, riscospath)
        ospathmodname, os.path.__name__ = os.path.__name__, 'os.path'

        for mod in modules:
            for name in dir(mod):
                if name.startswith('_') or isinstance(getattr(mod, name), types.ModuleType):
                    continue

                self.jinja2_env.filters[mod.__name__ + '.' + name] = getattr(mod, name)

        # restore original os.path module name
        os.path.__name__ = ospathmodname

    @property
    def macros(self):
        """Import macros from ``THEME/macro.html`` into context of the
        post environment.  Very hackish, but it should work."""

        path = join(self.conf['theme'], 'macros.html')
        if not (isfile(path) and isinstance(self.env.engine._jinja2, Environment)):
            return ''

        with io.open(path, encoding='utf-8') as fp:
            text = fp.read()

        return "{%% from 'macros.html' import %s with context %%}\n" % ', '.join(
            re.findall('^\{% macro ([^\(]+)', text, re.MULTILINE))

    def transform(self, content, entry):

        try:
            tt = self.jinja2_env.from_string(self.macros + content)
            return tt.render(conf=self.conf, env=self.env, entry=entry)
        except (TemplateError, AcrylamidException) as e:
            log.warn('%s: %s in %r' % (e.__class__.__name__, e.args[0], entry.filename))
            return content

########NEW FILE########
__FILENAME__ = liquid
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import io
import re
import json
import pickle

from os.path import join
from functools import partial

from acrylamid import core, utils, lib
from acrylamid.compat import PY2K, iteritems, text_type as str

from acrylamid.core import cache
from acrylamid.utils import Struct
from acrylamid.filters import Filter

from acrylamid.lib import requests

if PY2K:
    from urllib import urlencode
    from urlparse import urlparse, parse_qs
    import cPickle as pickle
else:
    from urllib.parse import urlencode
    from urllib.parse import urlparse, parse_qs

__img_re = r'(?P<class>\S.*\s+)?(?P<src>(?:https?:\/\/|\/|\S+\/)\S+)(?:\s+(?P<width>\d+))?(?:\s+(?P<height>\d+))?(?P<title>\s+.+)?'
__img_re_title = r'(?:"|\')(?P<title>[^"\']+)?(?:"|\')\s+(?:"|\')(?P<alt>[^"\']+)?(?:"|\')'


def blockquote(header, body):
    """Mimic Octopress's blockquote plugin. See
    http://octopress.org/docs/plugins/blockquote/ for examples."""

    # TODO: use python-titlecase if available or use this implementation:
    #       https://github.com/imathis/octopress/blob/master/plugins/titlecase.rb

    def paragraphize(text):
        return '<p>' + text.strip().replace('\n\n', '</p><p>').replace('\n', '<br/>') + '</p>'

    by, source, title = None, None, None

    m = re.match(r'(\S.*)\s+(https?:\/\/)(\S+)\s+(.+)', header, flags=re.I)
    if m:
        by = m.group(1)
        source = m.group(2) + m.group(3)
        title = m.group(4)  # titlecase
    else:
        m = re.match(r'(\S.*)\s+(https?:\/\/)(\S+)', header, re.I)
        if m:
            by = m.group(1)
            source = m.group(2) + m.group(3)
        else:
            m = re.match(r'([^,]+),([^,]+)', header)
            if m:
                by = m.group(1)
                title = m.group(2)  # titlecase
            else:
                m = re.match(r'(.+)', header)
                if m:
                    by = m.group(1)

    quote = paragraphize(body)
    author = '<strong>%s</strong>' % (by.strip() or '')

    if source:
        url = re.match(r'https?:\/\/(.+)', source).group(1)
        parts = []
        for part in url.split('/'):
            if not part or len('/'.join(parts + [part])) >= 32:
                break
            parts.append(part)
        else:
            parts.append('&hellip;')

        href = '/'.join(parts)

    if source:
        cite = ' <cite><a href="%s">%s</a></cite>' % (source, (title or href))
    elif title:
        cite = ' <cite>%s</cite>' % title

    if not author:
        blockquote = quote
    elif cite:
        blockquote = quote + "<footer>%s</footer>" % (author + cite)
    else:
        blockquote = quote + "<footer>%s</footer>" % author

    return "<blockquote>%s</blockquote>" % blockquote


def img(header, body=None):
    """Alternate to Markdown's image tag. See
    http://octopress.org/docs/plugins/image-tag/ for usage."""

    attrs = re.match(__img_re, header).groupdict()
    m = re.match(__img_re_title, attrs['title'])

    if m:
        attrs['title'] = m.groupdict()['title']
        attrs['alt'] = m.groupdict()['alt']
    elif 'title' in attrs:
        attrs['alt'] = attrs['title'].replace('"', '&#34')

    if 'class' in attrs:
        attrs['class'] = attrs['class'].replace('"', '')

    if attrs:
        return '<img ' + ' '.join('%s="%s"' % (k, v) for k, v in iteritems(attrs) if v) + ' />'
    return ("Error processing input, expected syntax: "
            "{% img [class name(s)] [http[s]:/]/path/to/image [width [height]] "
            "[title text | \"title text\" [\"alt text\"]] %}")


def youtube(header, body=None):

    # TODO add options similar to rstx_youtube directive

    if header.startswith(('http://', 'https://')):
        header = parse_qs(urlparse(header).query)['v'][0]

    return '<div class="video">' + \
                '<iframe src="http://www.youtube.com/embed/%s"></iframe>' % header + \
           '</div>'


def pullquote(header, body):
    """Semantic pullquote using CSS only. Defaults to right alignment. See
    http://octopress.org/docs/plugins/pullquote/ for details."""

    # TODO support a markup language somehow

    align = 'left' if 'left' in header.lower() else 'right'
    m = re.search(r'{"\s*(.+?)\s*"}', body, re.MULTILINE | re.DOTALL)

    if m:
        return '<span class="pullquote-{0}" data-pullquote="{1}">{2}</span>'.format(
            align, m.group(1), re.sub(r'\{"\s*|\s*"\}', '', body))
    return "Surround your pullquote like this {\" text to be quoted \"}"


def tweet(header, body=None):
    """Easy embedding of Tweets. The Twitter oEmbed API is rate-limited,
    hence we are caching the response per configuration to `.cache/`."""

    oembed = 'https://api.twitter.com/1/statuses/oembed.json'
    args = list(map(str.strip, re.split(r'\s+', header)))

    params = Struct(url=args.pop(0))
    for arg in args:
        k, v = list(map(str.strip, arg.split('=')))
        if k and v:
            v = v.strip('\'')
        params[k] = v

    try:
        with io.open(join(core.cache.cache_dir, 'tweets'), 'rb') as fp:
            cache = pickle.load(fp)
    except (IOError, pickle.PickleError):
        cache = {}

    if params in cache:
        body = cache[params]
    else:
        try:
            body = json.loads(requests.get(oembed + '?' + urlencode(params)).read())['html']
        except (requests.HTTPError, requests.URLError):
            log.exception('unable to fetch tweet')
            body = "Tweet could not be fetched"
        except (ValueError, KeyError):
            log.exception('could not parse response')
            body = "Tweet could not be processed"
        else:
            cache[params] = body

    try:
        with io.open(join(core.cache.cache_dir, 'tweets'), 'wb') as fp:
            pickle.dump(cache, fp, pickle.HIGHEST_PROTOCOL)
    except (IOError, pickle.PickleError):
        log.exception('uncaught exception during pickle.dump')

    return "<div class='embed tweet'>%s</div>" % body


class Liquid(Filter):

    match = [re.compile('^(liquid|octopress)$', re.I)]
    priority = 80.0

    directives = {
        'blockquote': blockquote, 'pullquote': pullquote,
        'img': img, 'tweet': tweet,
        'youtube': youtube
    }

    def block(self, tag):
        return re.compile(''.join([
            r'{%% %s (.*?) ?%%}' % tag,
            '(?:',
                '\n(.+?)\n',
                r'{%% end%s %%}' % tag,
            ')?']), re.MULTILINE | re.DOTALL)

    def transform(self, text, entry, *args):

        for tag, func in iteritems(self.directives):
            text = re.sub(self.block(tag), lambda m: func(*m.groups()), text)

        return text

########NEW FILE########
__FILENAME__ = mako-templating
# -*- encoding: utf-8 -*-
#
# Copyright 2012 moschlar <mail@moritz-schlarb.de>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid import log
from acrylamid.filters import Filter
from acrylamid.helpers import system as defaultsystem
from acrylamid.errors import AcrylamidException
from acrylamid.compat import text_type as str

try:
    from mako.template import Template
    from mako.exceptions import MakoException
except ImportError:
    Template = None  # NOQA
    MakoException = None  # NOQA


class Mako(Filter):
    """Mako filter that pre-processes in Markdown/reStructuredText
    written posts. XXX: and offers some Mako extensions."""

    match = ['Mako', 'mako']
    version = 1

    priority = 90.0

    def init(self, conf, env, *args):

        if not Mako or not MakoException:
            raise ImportError('Mako: No module named mako')

        def system(cmd, stdin=None):
            try:
                return defaultsystem(cmd, stdin, shell=True).strip()
            except (OSError, AcrylamidException) as e:
                log.warn('%s: %s' % (e.__class__.__name__, e.args[0]))
                return e.args[0]

        self.conf = conf
        self.env = env
        self.filters = {'system': system, 'split': str.split}

    def transform(self, content, entry):

        try:
            tt = Template(content, cache_enabled=False, input_encoding='utf-8')
            return tt.render(conf=self.conf, env=self.env, entry=entry, **self.filters)
        except (MakoException, AcrylamidException) as e:
            log.warn('%s: %s in %r' % (e.__class__.__name__, e.args[0], entry.filename))
            return content

########NEW FILE########
__FILENAME__ = md
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import os
import imp
import markdown

from acrylamid.errors import AcrylamidException
from acrylamid.compat import string_types
from acrylamid.filters import Filter, discover


class Markdown(Filter):

    match = ['md', 'mkdown', 'markdown', 'Markdown']
    version = 2

    conflicts = ['rst', 'plain']
    priority = 70.0

    extensions = dict((x, x) for x in ['abbr', 'fenced_code', 'footnotes', 'headerid',
        'tables', 'codehilite', 'def_list', 'extra', 'smart_strong', 'nl2br',
        'sane_lists', 'wikilink', 'attr_list'])

    def init(self, conf, env):

        self.failed = []
        self.ignore = env.options.ignore

        markdown.Markdown  # raises ImportError eventually

        # -- discover markdown extensions --
        directories = conf['filters_dir'] + [os.path.dirname(__file__)]
        for filename in discover(directories, lambda path: path.startswith('mdx_')):
            modname, ext = os.path.splitext(os.path.basename(filename))
            fp, path, descr = imp.find_module(modname, directories)

            try:
                mod = imp.load_module(modname, fp, path, descr)
                mdx = mod.makeExtension()
                if isinstance(mod.match, string_types):
                    mod.match = [mod.match]
                for name in mod.match:
                    self.extensions[name] = mdx
            except (ImportError, Exception) as e:
                self.failed.append('%r %s: %s' % (filename, e.__class__.__name__, e))

    def __contains__(self, key):
        return True if key in self.extensions else False

    def transform(self, text, entry, *filters):

        val = []
        for f in filters:
            if f in self:
                val.append(f)
            else:
                x = f.split('(', 1)[:1][0]
                if x in self:
                    val.append(x)
                    self.extensions[x] = f
                elif not self.ignore:
                    raise AcrylamidException('Markdown: %s' % '\n'.join(self.failed))

        return markdown.Markdown(
            extensions=[self.extensions[m] for m in val],
            output_format='xhtml5'
        ).convert(text)

########NEW FILE########
__FILENAME__ = mdx_asciimathml
# -*- encoding: utf-8 -*-
#
# Copyright (c) 2010-2011, Gabriele Favalessa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import re
import markdown
import asciimathml

match = ['mathml', 'math', 'asciimathml', 'MathML', 'Math', 'AsciiMathML']
__author__ = 'Gabriele Favalessa'

RE = re.compile(r'^(.*)\$([^\$]*)\$(.*)$', re.M)  # $ a $


class ASCIIMathMLExtension(markdown.Extension):
    def __init__(self, configs):
        pass

    def extendMarkdown(self, md, md_globals):
        self.md = md
        md.inlinePatterns.add('', ASCIIMathMLPattern(RE), '_begin')

    def reset(self):
        pass


class ASCIIMathMLPattern(markdown.inlinepatterns.Pattern):
    def getCompiledRegExp(self):
        return RE

    def handleMatch(self, m):
        if markdown.version_info < (2, 1, 0):
            math = asciimathml.parse(m.group(2).strip(), markdown.etree.Element,
                       markdown.AtomicString)
        else:
            math = asciimathml.parse(m.group(2).strip(),
                       markdown.util.etree.Element, markdown.util.AtomicString)
        math.set('xmlns', 'http://www.w3.org/1998/Math/MathML')
        return math


def makeExtension(configs=None):
    return ASCIIMathMLExtension(configs=configs)

########NEW FILE########
__FILENAME__ = mdx_delins
# -*- encoding: utf-8 -*-
#
# - Copyright 2011, 2012 The Active Archives contributors
# - Copyright 2011, 2012 Alexandre Leray
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the <organization> nor the names of its contributors may
#    be used to endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE PYTHON MARKDOWN PROJECT ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL ANY CONTRIBUTORS TO THE PYTHON MARKDOWN PROJECT
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Del/Ins Extension for Python-Markdown
# =====================================
#
# Wraps the inline content with ins/del tags.
#
#
# Usage
# -----
#
# >>> import markdown
# >>> src = """This is ++added content++ and this is ~~deleted content~~"""
# >>> html = markdown.markdown(src, ['del_ins'])
# >>> print(html)
# <p>This is <ins>added content</ins> and this is <del>deleted content</del>
# </p>

import markdown
from markdown.inlinepatterns import SimpleTagPattern

match = ['delins']


class DelInsExtension(markdown.extensions.Extension):
    """Adds del_ins extension to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """Modifies inline patterns."""
        md.inlinePatterns.add('del', SimpleTagPattern(r"(\~\~)(.+?)(\~\~)", 'del'), '<not_strong')
        md.inlinePatterns.add('ins', SimpleTagPattern(r"(\+\+)(.+?)(\+\+)", 'ins'), '<not_strong')


def makeExtension(configs={}):
    return DelInsExtension(configs=dict(configs))

########NEW FILE########
__FILENAME__ = mdx_gist
# -*- encoding: utf-8 -*-
#
# Markdown Gist, similar to rstx_gist.py 
#

import re
import markdown

from acrylamid.lib.requests import get, HTTPError, URLError
from acrylamid import log

match = ['gist', 'gistraw']

GIST_RE = r'\[gist:\s*(?P<gistID>\d+)(?:\s*(?P<filename>.+?))?\]'
GISTRAW_RE = r'\[gistraw:\s*(?P<gistID>\d+)(?:\s*(?P<filename>.+?))?\]'

class GistExtension(markdown.Extension):
    """Add [gist:] and [gistraw:] to Pyton-Markdown Extensions"""

    def extendMarkdown(self, md, md_globals):
        self.md = md
        md.inlinePatterns.add('gist', GistPattern(GIST_RE), '_begin')
        md.inlinePatterns.add('gistraw', GistPattern(GISTRAW_RE), '_begin')

class GistPattern(markdown.inlinepatterns.Pattern):
    """Replace [gist: id filename] with embedded Gist script. Filename is optional
       [gistraw: id filename] will return the raw text wrapped in a <pre> block (no embedded javascript)
       Add filters: [Markdown+gist] to your Markdown metadata"""

    def get_raw_gist_with_filename(self, gistID, filename):
        url = "https://raw.github.com/gist/%s/%s" % (gistID, filename)
        try:
            return get(url).read()
        except (URLError, HTTPError) as e:
            log.exception('Failed to access URL %s : %s' % (url, e))
        return ''

    def get_raw_gist(self, gistID):
        url = "https://raw.github.com/gist/%s" % (gistID)
        try:
            return get(url).read()
        except (URLError, HTTPError) as e:
            log.exception('Failed to access URL %s : %s' % (url, e))
        return ''

    def handleMatch(self, m):

        if markdown.version_info < (2, 1, 0):
            mdutils = markdown
        else:
            mdutils = markdown.util

        gistID = m.group('gistID')
        gistFilename = m.group('filename')

        if gistFilename:
            embeddedJS = "https://gist.github.com/%s.js?file=%s" % (gistID, gistFilename)
            rawGist = (self.get_raw_gist_with_filename(gistID, gistFilename))
        else:
            embeddedJS = "https://gist.github.com/%s.js" % (gistID)
            rawGist = (self.get_raw_gist(gistID))

        if self.pattern == GIST_RE:
            el = mdutils.etree.Element('div')
            el.set('class', 'gist')
            script = mdutils.etree.SubElement(el, 'script')
            script.set('src', embeddedJS)
            
            # NoScript alternative in <pre> block
            noscript = mdutils.etree.SubElement(el, 'noscript')
            pre = mdutils.etree.SubElement(noscript, 'pre')
            pre.set('class', 'literal-block')
            pre.text = mdutils.AtomicString(rawGist)
        else:
            # No javascript, just output gist as <pre> wrapped text
            el = mdutils.etree.Element('pre')
            el.set('class', 'literal-block gist-raw')
            el.text = mdutils.AtomicString(rawGist)

        return el


def makeExtension(configs=None):
    return GistExtension(configs=configs)

########NEW FILE########
__FILENAME__ = mdx_subscript
# -*- encoding: utf-8 -*-
#
# Copyright (c) 2010, Shane Graber
#
# Subscript extension for Markdown.
#
# To subscript something, place a tilde symbol, '~', before and after the
# text that you would like in subscript: C~6~H~12~O~6~
# The numbers in this example will be subscripted. See below for more:
#
# Examples:
#
# >>> import markdown
# >>> md = markdown.Markdown(extensions=['subscript'])
# >>> md.convert('This is sugar: C~6~H~12~O~6~')
# u'<p>This is sugar: C<sub>6</sub>H<sub>12</sub>O<sub>6</sub></p>'
#
# Paragraph breaks will nullify subscripts across paragraphs. Line breaks
# within paragraphs will not.
#
# Modified to not subscript "~/Library. Foo bar, see ~/Music/".
#
# useful CSS rules:  sup, sub {
#                        vertical-align: baseline;
#                        position: relative;
#                        top: -0.4em;
#                    }
#                    sub { top: 0.4em; }

import markdown

match = ['subscript', 'sub']


class SubscriptPattern(markdown.inlinepatterns.Pattern):
    """Return a subscript Element: `C~6~H~12~O~6~'"""

    def handleMatch(self, m):

        text = m.group(3)

        if markdown.version_info < (2, 1, 0):
            el = markdown.etree.Element("sub")
            el.text = markdown.AtomicString(text)
        else:
            el = markdown.util.etree.Element("sub")
            el.text = markdown.util.AtomicString(text)

        return el


class SubscriptExtension(markdown.Extension):
    """Subscript Extension for Python-Markdown."""

    def extendMarkdown(self, md, md_globals):
        """Replace subscript with SubscriptPattern"""
        md.inlinePatterns['subscript'] = SubscriptPattern(r'(\~)([^\s\~]+)\2', md)


def makeExtension(configs=None):
    return SubscriptExtension(configs=configs)

########NEW FILE########
__FILENAME__ = mdx_superscript
# -*- encoding: utf-8 -*-
#
# Copyright (c) 2010, Shane Graber
#
# Superscipt extension for Markdown.
#
# To superscript something, place a carat symbol, '^', before and after the
# text that you would like in superscript: 6.02 x 10^23^
# The '23' in this example will be superscripted. See below.
#
# Examples:
#
# >>> import markdown
# >>> md = markdown.Markdown(extensions=['superscript'])
# >>> md.convert('This is a reference to a footnote^1^.')
# u'<p>This is a reference to a footnote<sup>1</sup>.</p>'
#
# >>> md.convert('This is scientific notation: 6.02 x 10^23^')
# u'<p>This is scientific notation: 6.02 x 10<sup>23</sup></p>'
#
# >>> md.convert('This is scientific notation: 6.02 x 10^23. Note lack of second carat.')
# u'<p>This is scientific notation: 6.02 x 10^23. Note lack of second carat.</p>'
#
# >>> md.convert('Scientific notation: 6.02 x 10^23. Add carat at end of sentence.^')
# u'<p>Scientific notation: 6.02 x 10<sup>23. Add a carat at the end of sentence.</sup>.</p>'
#
# Paragraph breaks will nullify superscripts across paragraphs. Line breaks
# within paragraphs will not.
#
# Modified to not superscript "HEAD^1. Also for HEAD^2".
#
# useful CSS rules:  sup, sub {
#                        vertical-align: baseline;
#                        position: relative;
#                        top: -0.4em;
#                    }
#                    sub { top: 0.4em; }

import markdown

match = ['superscript', 'sup']


class SuperscriptPattern(markdown.inlinepatterns.Pattern):
    """Return a superscript Element (`word^2^`)."""

    def handleMatch(self, m):

        text = m.group(3)

        if markdown.version_info < (2, 1, 0):
            el = markdown.etree.Element("sup")
            el.text = markdown.AtomicString(text)
        else:
            el = markdown.util.etree.Element("sup")
            el.text = markdown.util.AtomicString(text)

        return el


class SuperscriptExtension(markdown.Extension):
    """Superscript Extension for Python-Markdown."""

    def extendMarkdown(self, md, md_globals):
        """Replace superscript with SuperscriptPattern"""
        md.inlinePatterns['superscript'] = SuperscriptPattern(r'(\^)([^\s\^]+)\2', md)


def makeExtension(configs=None):
    return SuperscriptExtension(configs=configs)

########NEW FILE########
__FILENAME__ = metalogo
# -*- encoding: utf-8 -*-
#
# Copyright 2012 sebix <szebi@gmx.at>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.
# Idea by http://nitens.org/taraborelli/texlogo

from acrylamid.filters import Filter

LaTeX = """\
<span style="font-family: cmr10, LMRoman10-Regular, Times, serif; letter-spacing: 0.075em;">L
<span style="text-transform: uppercase; font-size: 70%; margin-left: -0.36em; vertical-align: 0.3em; line-height: 0; margin-right: -0.15em;">a</span>T
<span style="text-transform: uppercase; margin-left: -0.1667em; vertical-align: -0.5ex; line-height: 0; margin-right: -0.125em;">e
</span>X</span>
""".strip().replace('\n', '')

TeX = """\
<span style="font-family: cmr10, LMRoman10-Regular, Times, serif; letter-spacing: 0.075em;">T
<span style="text-transform: uppercase; margin-left: -0.1667em; vertical-align: -0.5ex; line-height: 0; margin-right: -0.125em;">e
</span>X</span>
""".strip().replace('\n', '')

XeTeX = u"""\
<span style="font-family: cmr10, LMRoman10-Regular, Times, serif; letter-spacing: 0.075em;">X
<span style="text-transform: uppercase; margin-left: -0.1367em; vertical-align: -0.5ex; line-height: 0; margin-right: -0.125em;">ǝ
</span>T
<span style="text-transform: uppercase; margin-left: -0.1667em; vertical-align: -0.5ex; line-height: 0; margin-right: -0.125em;">e
</span>X</span>
""".strip().replace('\n', '')


class Tex(Filter):

    match = ['metalogo']
    version = 3

    def transform(self, text, entry, *args):
        replacings = (('LaTeX', LaTeX),
                        ('XeTeX', XeTeX),
                        ('TeX', TeX))
        for k in replacings:
            text = text.replace(k[0], k[1])
        return text

########NEW FILE########
__FILENAME__ = pandoc
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid.filters import Filter
from acrylamid.helpers import system
from acrylamid.errors import AcrylamidException


class Pandoc(Filter):

    match = ['Pandoc', 'pandoc']
    version = 1

    conflicts = ['Markdown', 'reStructuredText', 'HTML']
    priority = 70.0

    def init(self, conf, env):
        self.ignore = env.options.ignore

    def transform(self, text, entry, *args):

        try:
            system(['which', 'pandoc'])
        except AcrylamidException:
            if self.ignore:
                return text
            raise AcrylamidException('Pandoc: pandoc not available')

        if len(args) == 0:
            raise AcrylamidException("pandoc filter takes one or more arguments")

        fmt, extras = args[0], args[1:]
        cmd = ['pandoc', '-f', fmt, '-t', 'HTML']
        cmd.extend(['--'+x for x in extras])

        try:
            return system(cmd, stdin=text)
        except OSError as e:
            raise AcrylamidException(e.msg)

########NEW FILE########
__FILENAME__ = pytextile
# -*- encoding: utf-8 -*-
#
# Copyright 2012 sebix <szebi@gmx.at>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid.filters import Filter

try:
    from textile import textile
except ImportError:
    textile = None  # NOQA


class PyTextile(Filter):

    match = ['Textile', 'textile', 'pytextile', 'PyTextile']
    version = 1

    conflicts = ['Markdown', 'reStructuredText', 'HTML', 'Pandoc']
    priority = 70.0

    def init(self, conf, env):

        if textile is None:
            raise ImportError('Textile: PyTextile not available')

    def transform(self, text, entry, *args):

        return textile(text)

########NEW FILE########
__FILENAME__ = python-discount
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid.filters import Filter

try:
    from discount import Markdown
except ImportError:
    Markdown = None  # NOQA


class Discount(Filter):

    match = ['discount', 'Discount']
    version = 1

    conflicts = ['Markdown', 'reStructuredText', 'HTML', 'Pandoc', 'typography']
    priority = 70.0

    def init(self, conf, env):

        if Markdown is None:
            raise ImportError("Discount: discount not available")

    def transform(self, text, entry, *args):

        mkd = Markdown(text.encode('utf-8'),
                       autolink=True, safelink=True, ignore_header=True)
        return mkd.get_html_content().decode('utf-8')

########NEW FILE########
__FILENAME__ = relative
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid import log
from acrylamid.filters import Filter
from acrylamid.helpers import joinurl
from acrylamid.lib.html import HTMLParser, HTMLParseError


class Href(HTMLParser):

    def __init__(self, html, func=lambda part: part):
        self.func = func
        super(Href, self).__init__(html)

    def apply(self, attrs):

        for i, (key, value) in enumerate(attrs):
            if key in ('href', 'src'):
                attrs[i] = (key, self.func(value))

        return attrs

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs = self.apply(attrs)
        super(Href, self).handle_starttag(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        if tag == 'img':
            attrs = self.apply(attrs)
        super(Href, self).handle_startendtag(tag, attrs)


class Relative(Filter):

    match = ['relative']
    version = 1
    priority = 15.0

    def transform(self, text, entry, *args):

        def relatively(part):

            if part.startswith('/') or part.find('://') == part.find('/') - 1:
                return part

            return joinurl(entry.permalink, part)

        try:
            return ''.join(Href(text, relatively).result)
        except HTMLParseError as e:
            log.warn('%s: %s in %s' % (e.__class__.__name__, e.msg, entry.filename))
            return text


class Absolute(Filter):

    match = ['absolute']
    version = 2
    priority = 15.0

    @property
    def uses(self):
        return self.conf.www_root

    def transform(self, text, entry, *args):

        def absolutify(part):

            if part.startswith('/'):
                return self.conf.www_root + part

            if part.find('://') == part.find('/') - 1:
                return part

            return self.conf.www_root + joinurl(entry.permalink, part)

        try:
            return ''.join(Href(text, absolutify).result)
        except HTMLParseError as e:
            log.warn('%s: %s in %s' % (e.__class__.__name__, e.msg, entry.filename))
            return text

########NEW FILE########
__FILENAME__ = rst
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import sys
import os
import imp
import traceback

from distutils.version import LooseVersion

from acrylamid import log
from acrylamid.filters import Filter, discover

try:
    from docutils.core import publish_parts, __version__ as version
    from docutils.parsers.rst import roles, directives
except ImportError:
    publish_parts = roles = directives = None  # NOQA


class Restructuredtext(Filter):

    match = ['restructuredtext', 'rst', 'rest', 'reST', 'reStructuredText']
    version = 2

    conflicts = ['markdown', 'plain']
    priority = 70.00

    def init(self, conf, env):

        self.extensions = {}
        self.ignore = env.options.ignore

        if not tuple(LooseVersion(version).version) > (0, 9):
            raise ImportError(u'docutils ≥ 0.9 required.')

        if not publish_parts or not directives:
            raise ImportError(u'reStructuredText: No module named docutils')

        # -- discover reStructuredText extensions --
        directories = conf['filters_dir'] + [os.path.dirname(__file__)]
        for filename in discover(directories, lambda path: path.startswith('rstx_')):
            modname, ext = os.path.splitext(os.path.basename(filename))
            fp, path, descr = imp.find_module(modname, directories)

            try:
                mod = imp.load_module(modname, fp, path, descr)
                mod.register(roles, directives)
            except (ImportError, Exception) as e:
                traceback.print_exc(file=sys.stdout)
                log.warn('%r %s: %s' % (filename, e.__class__.__name__, e))

    def transform(self, content, entry, *filters):

        settings = {
            'initial_header_level': 1,
            'doctitle_xform': 0,
            'syntax_highlight': 'short'
        }

        parts = publish_parts(content, writer_name='html', settings_overrides=settings)
        return parts['body']

########NEW FILE########
__FILENAME__ = rstx_gist
# -*- encoding: utf-8 -*-#
#
# License: This document has been placed in the public domain
# Author: Brian Hsu

from docutils.parsers.rst import Directive, directives
from docutils import nodes

from acrylamid.lib.requests import get, HTTPError, URLError
from acrylamid import log

class Gist(Directive):
    """`GitHub:Gist <https://gist.github.com/>`__ embedding (file is optional).

  .. code-block:: rst

      .. gist:: 4145152
         :file: transmission.rb
    """

    required_arguments = 1
    optional_arguments = 1
    option_spec = {'file': directives.unchanged}
    final_argument_whitespace = True
    has_content = False

    def get_raw_gist_with_filename(self, gistID, filename):
        url = "https://raw.github.com/gist/%s/%s" % (gistID, filename)
        try:
            return get(url).read()
        except (URLError, HTTPError) as e:
            log.exception('Failed to access URL %s : %s' % (url, e))
        return ''

    def get_raw_gist(self, gistID):
        url = "https://raw.github.com/gist/%s" % (gistID)
        try:
            return get(url).read()
        except (URLError, HTTPError) as e:
            log.exception('Failed to access URL %s : %s' % (url, e))
        return ''

    def run(self):

        gistID = self.arguments[0].strip()

        if 'file' in self.options:
            filename = self.options['file']
            rawGist = (self.get_raw_gist_with_filename(gistID, filename))
            embedHTML = '<script src="https://gist.github.com/%s.js?file=%s"></script>' % \
                (gistID, filename)
        else:
            rawGist = (self.get_raw_gist(gistID))
            embedHTML = '<script src="https://gist.github.com/%s.js"></script>' % gistID

        return [nodes.raw('', embedHTML, format='html'),
                nodes.raw('', '<noscript>', format='html'),
                nodes.literal_block('', rawGist),
                nodes.raw('', '</noscript>', format='html')]


def register(roles, directives):
    directives.register_directive('gist', Gist)

########NEW FILE########
__FILENAME__ = rstx_highlight
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from docutils import nodes
from docutils.parsers.rst import Directive
from xml.sax.saxutils import escape


class Highlight(Directive):
    """Wrap source code to be used with `Highlight.js`_:

    .. _highlight.js: http://softwaremaniacs.org/soft/highlight/en/

    .. code-block:: rst

        .. highlight-js:: python

            print("Hello, World!")
    """

    optional_arguments = 1
    has_content = True

    def run(self):
        lang = None
        if len(self.arguments) >= 1:
            lang = self.arguments[0]
        if lang:
            tmpl = '<pre><code class="%s">%%s</code></pre>' % lang
        else:
            tmpl = '<pre><code>%s</code></pre>'
        html = tmpl % escape('\n'.join(self.content))
        raw = nodes.raw('', html, format='html')
        return [raw]


def register(roles, directives):
    directives.register_directive('highlight-js', Highlight)

########NEW FILE########
__FILENAME__ = rstx_sourcecode
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from docutils.parsers.rst.directives import body

def register(roles, directives):
    for name in 'code-block', 'sourcecode', 'pygments':
        directives.register_directive(name, body.CodeBlock)

########NEW FILE########
__FILENAME__ = rstx_vimeo
# -*- encoding: utf-8 -*-
#
# Copyright 2012 the_metalgamer <the_metalgamer@hackerspace.lu>. All rights reserved.
# License: BSD Style, 2 clauses. see acrylamid/__init__.py

from docutils import nodes
from docutils.parsers.rst import Directive, directives

import re

color_pattern = re.compile("([a-f]|[A-F]|[0-9]){3}(([a-f]|[A-F]|[0-9]){3})")

match = ['vimeo']


def align(argument):
    return directives.choice(argument, ('left', 'center', 'right'))

def color(argument):
    match = color_pattern.match(argument)
    if match:
        return argument
    else:
        raise ValueError('argument must be an hexadecimal color number')


class Vimeo(Directive):
    """Vimeo directive for easy embedding (`:options:` are optional).

    .. code-block:: rst

        .. vimeo:: 6455561
           :align: center
           :height: 1280
           :width: 720
           :border: 1px
           :color: ffffff
           :nobyline:
           :noportrait:
           :nobyline:
           :notitle:
           :autoplay:
           :loop:
    """

    required_arguments = 1
    optional_arguments = 0
    option_spec = {
        'height': directives.length_or_unitless,
        'width': directives.length_or_unitless,
        'align': align,
        'border': directives.length_or_unitless,
        'color': color,
        'noportrait': directives.flag,
        'notitle': directives.flag,
        'nobyline': directives.flag,
        'autoplay': directives.flag,
        'loop': directives.flag,
    }
    has_content = False

    def run(self):

        alignments = {
            'left': '0',
            'center': '0 auto',
            'right': '0 0 0 auto',
        }

        self.options.setdefault('color', 'ffffff')

        uri = ("http://player.vimeo.com/video/" + self.arguments[0]
               + ( "?color=" + self.options['color'] + "&" ) \
               + ( "title=0&" if 'notitle' in self.options else "") \
               + ( "portrait=0&" if 'noportrait' in self.options else "") \
               + ( "byline=0&" if 'nobyline' in self.options else "") \
               + ( "autoplay=1&" if 'autoplay' in self.options else "") \
               + ( "loop=1" if 'loop' in self.options else "" )
                )
        self.options['uri'] = uri
        self.options['align'] = alignments[self.options.get('align', 'center')]
        self.options.setdefault('width', '500px')
        self.options.setdefault('height', '281px')
        self.options.setdefault('border', '0')

        VI_EMBED = """<iframe width="%(width)s" height="%(height)s" src="%(uri)s" \
                      frameborder="%(border)s" style="display: block; margin: %(align)s;" \
                      class="video" webkitAllowFullScreen mozallowfullscreen allowfullscreen></iframe>"""
        return [nodes.raw('', VI_EMBED % self.options, format='html')]

def register(roles, directives):
    directives.register_directive('vimeo', Vimeo)

########NEW FILE########
__FILENAME__ = rstx_youtube
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from docutils import nodes
from docutils.parsers.rst import Directive, directives


def align(argument):
    return directives.choice(argument, ('left', 'center', 'right'))


class YouTube(Directive):
    """YouTube directive for easy embedding (`:options:` are optional).

    .. code-block:: rst

        .. youtube:: ZPJlyRv_IGI
           :start: 34
           :align: center
           :height: 1280
           :width: 720
           :privacy:
           :ssl:
    """

    required_arguments = 1
    optional_arguments = 0
    option_spec = {
        'height': directives.length_or_unitless,
        'width': directives.length_or_percentage_or_unitless,
        'border': directives.length_or_unitless,
        'align': align,
        'start': int,
        'ssl': directives.flag,
        'privacy': directives.flag
    }
    has_content = False

    def run(self):

        alignments = {
            'left': '0',
            'center': '0 auto',
            'right': '0 0 0 auto',
        }

        uri = ('https://' if 'ssl' in self.options else 'http://') \
              + ('www.youtube-nocookie.com' if 'privacy' in
                  self.options else 'www.youtube.com') \
              + '/embed/' + self.arguments[0]
        self.options['uri'] = uri
        self.options['align'] = alignments[self.options.get('align', 'center')]
        self.options.setdefault('width', '680px')
        self.options.setdefault('height', '382px')
        self.options.setdefault('border', 0)
        self.options.setdefault('start', 0)

        YT_EMBED = """<iframe width="%(width)s" height="%(height)s" src="%(uri)s" \
                      frameborder="%(border)s" style="display: block; margin: %(align)s;" \
                      start="%(start)i" class="video" allowfullscreen></iframe>"""
        return [nodes.raw('', YT_EMBED % self.options, format='html')]


def register(roles, directives):
    for name in 'youtube', 'yt':
        directives.register_directive(name, YouTube)

########NEW FILE########
__FILENAME__ = strip
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid import log

from acrylamid.filters import Filter
from acrylamid.lib.html import HTMLParser, HTMLParseError


class Text(HTMLParser):
    """Strip tags and attributes from HTML.  By default it keeps everything
    between any HTML tags, but you can supply a list of ignored tags."""

    handle_comment = handle_startendtag = lambda *x, **z: None

    def __init__(self, html, args):

        self.ignored = args
        super(Text, self).__init__(html)

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        try:
            self.stack.pop()
        except IndexError:
            pass

        if tag in ('li', 'ul', 'p'):
            self.result.append('\n')

    def handle_data(self, data):
        if not any(tag for tag in self.ignored if tag in self.stack):
            super(Text, self).handle_data(data)

    def handle_entityref(self, name):
        if name == 'shy':
            return
        self.handle_data(self.unescape('&' + name + ';'))

    def handle_charref(self, char):
        self.handle_data(self.unescape('&#' + char + ';'))


class Strip(Filter):

    match = ['strip']
    version = 1
    priority = 0.0

    def transform(self, content, entry, *args):

        try:
            return ''.join(Text(content, args).result)
        except HTMLParseError:
            log.exception('could not strip ' + entry.filename)
            return content

########NEW FILE########
__FILENAME__ = summarize
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid import log, helpers
from acrylamid.filters import Filter

from acrylamid.lib.html import HTMLParser, HTMLParseError


class Summarizer(HTMLParser):

    def __init__(self, text, maxwords, href, options):
        self.href = href
        self.mode = options['mode']
        self.options = options

        self.words = 0
        self.maxwords = maxwords

        HTMLParser.__init__(self, text)

    def handle_starttag(self, tag, attrs):
        # Apply and stack each tag until we reach maxword.
        if self.words < self.maxwords:
            super(Summarizer, self).handle_starttag(tag, attrs)

    def handle_data(self, data):
        # append words
        if self.words >= self.maxwords:
            pass
        else:
            ws = data.count(' ')
            if ws + self.words < self.maxwords:
                self.result.append(data)
            else:
                words = data.split(' ')
                self.result.append(' '.join(words[:self.maxwords - self.words]) + ' ')
            self.words += ws

        if self.words >= self.maxwords and not self.stack:
            # weird markup, mostly from WordPress. Just append link and break
            if self.mode > -1:
                self.result.append(self.options['link'] % self.href)
                self.mode = -1

    def handle_endtag(self, tag):
        # If we are behind the word limit, append out link in various modes, else append tag
        if self.words < self.maxwords:
            self.result.append('</%s>' % self.stack.pop())

        elif self.stack:
            # this injects the link to the end of the current tag
            if self.mode == 0:
                self.result.append(self.options['link'] % self.href)
                self.mode = -1

            # now we append all stored tags
            for x in self.stack[:]:

                # this adds the link if it's not inside a given tag, prefered way
                if self.mode == 1:
                    if not any(filter(lambda t: t in ['code', 'pre', 'b', 'a', 'em'], self.stack)):
                        self.result.append(self.options['link'] % self.href)
                        self.mode = -1

                self.result.append('</%s>' % self.stack.pop())

            # this adds the link when the stack is empty
            if self.mode == 2:
                self.result.append(self.options['link'] % self.href)

    def handle_startendtag(self, tag, attrs):
        if self.words < self.maxwords and tag not in self.options['ignore']:
            super(Summarizer, self).handle_startendtag(tag, attrs)

    def handle_entityref(self, entity):
        if self.words < self.maxwords:
            super(Summarizer, self).handle_entityref(entity)

    def handle_charref(self, char):
        if self.words < self.maxwords:
            super(Summarizer, self).handle_charref(char)

    def handle_comment(self, comment, keywords=['excerpt', 'summary', 'break', 'more']):
        if self.words < self.maxwords and [word for word in keywords if word in comment.lower()]:
            self.words = self.maxwords


class Summarize(Filter):
    """Summarizes content up to `maxwords` (defaults to 100)."""

    match = ['summarize', 'sum']
    version = 3
    priority = 15.0

    defaults = {
        'mode': 1,
        'ignore': ['img', 'video', 'audio'],
        'link': '<span>&#8230;<a href="%s" class="continue">continue</a>.</span>'
    }

    @property
    def uses(self):
        return self.env.path

    def transform(self, content, entry, *args):
        options = helpers.union(Summarize.defaults, self.conf.fetch('summarize_'))

        try:
            options.update(entry.summarize)
        except AttributeError:
            pass

        try:
            maxwords = int(options.get('maxwords') or args[0])
        except (IndexError, ValueError) as ex:
            if isinstance(ex, ValueError):
                log.warn('Summarize: invalid maxwords argument %r',
                         options.get('maxwords') or args[0])
            maxwords = 100

        try:
            return ''.join(Summarizer(
                content, maxwords, self.env.path+entry.permalink, options).result)
        except HTMLParseError:
            log.exception('could not summarize ' + entry.filename)
            return content

########NEW FILE########
__FILENAME__ = typography
# -*- encoding: utf-8 -*-
#
# License: New BSD Style
#
# [typography.py][1] is a set of filters enhancing written text output. As the
# name says, it adds specific typography things documented in the definitions
# itself and [smartypants][2].
#
# The typography.py filter comes with two options: ``mode`` and ``default``.
# ``TYPOGRAPHY_MODE`` sets the `smartypants_attributes` as documented in [2].
# ``default`` (hard-coded) is a list of filters that will be always applied
# if *typopgraphy* is invoked + everything you specify in the additional arguments.
#
# typopgraphy.py offers a custom mode, "a", that don't educate dashes when written
# without space like *--bare* or *foo--* using mode "2".
#
# [1]: https://github.com/mintchaos/typogrify
# [2]: http://web.chad.org/projects/smartypants.py/

import re
import smartypants

from acrylamid.filters import Filter


class Typography(Filter):

    match = [re.compile('^(T|t)ypo(graphy)?$'), 'smartypants']
    version = 2

    priority = 25.0

    def init(self, conf, env):

        self.mode = conf.get("typography_mode", "2")  # -- en-dash, --- em-dash
        self.default = ['amp', 'widont', 'smartypants', 'caps']

        if self.mode == "a":
            smartypants.educateDashes = new_dashes
            smartypants.educateDashesOldSchool = new_dashes

            self.mode = "2"

        self.ignore = env.options.ignore
        self.filters = {'amp': amp, 'widont': widont, 'caps': caps,
                        'initial_quotes': initial_quotes, 'number_suffix': number_suffix,
                        'typo': typogrify, 'typogrify': typogrify, 'all': typogrify,
                        'smartypants': smartypants.smartyPants}

    def transform(self, content, entry, *args):

        if any(filter(lambda k: k in args, ['all', 'typo', 'typogrify'])):
            return typogrify(content)

        for x in ['amp', 'widont', 'smartypants', 'caps', 'initial_quotes', 'number_suffix']:
            if x in self.default + list(args):
                if x == 'smartypants':
                    content = self.filters[x](content, self.mode)
                else:
                    content = self.filters[x](content)

        return content


def new_dashes(str):
    # patching something-- to return something-- not something&#8212.
    str = re.sub(r"""(\s)--""", r"""\1&#8211;""", str)   # en (yes, backwards)
    str = re.sub(r"""(\s)---""", r"""\1&#8212;""", str)  # em (yes, backwards)
    return str


def amp(text, autoescape=None):
    """Wraps apersands in HTML with ``<span class="amp">`` so they can be
    styled with CSS. Apersands are also normalized to ``&amp;``. Requires
    ampersands to have whitespace or an ``&nbsp;`` on both sides.

    >>> amp('One & two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('One &amp; two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('One &#38; two')
    u'One <span class="amp">&amp;</span> two'

    >>> amp('One&nbsp;&amp;&nbsp;two')
    u'One&nbsp;<span class="amp">&amp;</span>&nbsp;two'

    It won't mess up & that are already wrapped, in entities or URLs

    >>> amp('One <span class="amp">&amp;</span> two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('&ldquo;this&rdquo; & <a href="/?that&amp;test">that</a>')
    u'&ldquo;this&rdquo; <span class="amp">&amp;</span> <a href="/?that&amp;test">that</a>'

    It should ignore standalone amps that are in attributes
    >>> amp('<link href="xyz.html" title="One & Two">xyz</link>')
    u'<link href="xyz.html" title="One & Two">xyz</link>'
    """

    # tag_pattern from http://haacked.com/archive/2004/10/25/usingregularexpressionstomatchhtml.aspx
    # it kinda sucks but it fixes the standalone amps in attributes bug
    tag_pattern = '</?\w+((\s+\w+(\s*=\s*(?:".*?"|\'.*?\'|[^\'">\s]+))?)+\s*|\s*)/?>'
    amp_finder = re.compile(r"(\s|&nbsp;)(&|&amp;|&\#38;)(\s|&nbsp;)")
    intra_tag_finder = re.compile(r'(?P<prefix>(%s)?)(?P<text>([^<]*))(?P<suffix>(%s)?)' % (tag_pattern, tag_pattern))

    def _amp_process(groups):
        prefix = groups.group('prefix') or ''
        text = amp_finder.sub(r"""\1<span class="amp">&amp;</span>\3""", groups.group('text'))
        suffix = groups.group('suffix') or ''
        return prefix + text + suffix
    return intra_tag_finder.sub(_amp_process, text)


def caps(text):
    """Wraps multiple capital letters in ``<span class="caps">``
    so they can be styled with CSS.

    >>> caps("A message from KU")
    u'A message from <span class="caps">KU</span>'

    Uses the smartypants tokenizer to not screw with HTML or with tags it shouldn't.

    >>> caps("<PRE>CAPS</pre> more CAPS")
    u'<PRE>CAPS</pre> more <span class="caps">CAPS</span>'

    >>> caps("A message from 2KU2 with digits")
    u'A message from <span class="caps">2KU2</span> with digits'

    >>> caps("Dotted caps followed by spaces should never include them in the wrap D.O.T.   like so.")
    u'Dotted caps followed by spaces should never include them in the wrap <span class="caps">D.O.T.</span>  like so.'

    All caps with with apostrophes in them shouldn't break. Only handles dump apostrophes though.
    >>> caps("JIMMY'S")
    u'<span class="caps">JIMMY\\'S</span>'

    >>> caps("<i>D.O.T.</i>HE34T<b>RFID</b>")
    u'<i><span class="caps">D.O.T.</span></i><span class="caps">HE34T</span><b><span class="caps">RFID</span></b>'
    """

    tokens = smartypants._tokenize(text)
    result = []
    in_skipped_tag = False

    cap_finder = re.compile(r"""(
                            (\b[A-Z\d]*        # Group 2: Any amount of caps and digits
                            [A-Z]\d*[A-Z]      # A cap string must at least include two caps (but they can have digits between them)
                            [A-Z\d']*\b)       # Any amount of caps and digits or dumb apostsrophes
                            | (\b[A-Z]+\.\s?   # OR: Group 3: Some caps, followed by a '.' and an optional space
                            (?:[A-Z]+\.\s?)+)  # Followed by the same thing at least once more
                            (?:\s|\b|$))
                            """, re.VERBOSE)

    def _cap_wrapper(matchobj):
        """This is necessary to keep dotted cap strings to pick up extra spaces"""
        if matchobj.group(2):
            return """<span class="caps">%s</span>""" % matchobj.group(2)
        else:
            if matchobj.group(3)[-1] == " ":
                caps = matchobj.group(3)[:-1]
                tail = ' '
            else:
                caps = matchobj.group(3)
                tail = ''
            return """<span class="caps">%s</span>%s""" % (caps, tail)

    tags_to_skip_regex = re.compile("<(/)?(?:pre|code|kbd|script|math)[^>]*>", re.IGNORECASE)

    for token in tokens:
        if token[0] == "tag":
            # Don't mess with tags.
            result.append(token[1])
            close_match = tags_to_skip_regex.match(token[1])
            if close_match and close_match.group(1) == None:
                in_skipped_tag = True
            else:
                in_skipped_tag = False
        else:
            if in_skipped_tag:
                result.append(token[1])
            else:
                result.append(cap_finder.sub(_cap_wrapper, token[1]))
    return "".join(result)


def number_suffix(text):
    """Wraps date suffix in <span class="ord">
    so they can be styled with CSS.

    >>> number_suffix("10th")
    u'10<span class="rod">th</span>'

    Uses the smartypants tokenizer to not screw with HTML or with tags it shouldn't.

    """

    suffix_finder = re.compile(r'(?P<number>[\d]+)(?P<ord>st|nd|rd|th)')

    def _suffix_process(groups):
        number = groups.group('number')
        suffix = groups.group('ord')

        return "%s<span class='ord'>%s</span>" % (number, suffix)
    return suffix_finder.sub(_suffix_process, text)


def initial_quotes(text):
    """Wraps initial quotes in ``class="dquo"`` for double quotes or
    ``class="quo"`` for single quotes. Works in these block tags ``(h1-h6, p, li, dt, dd)``
    and also accounts for potential opening inline elements ``a, em, strong, span, b, i``

    >>> initial_quotes('"With primes"')
    u'<span class="dquo">"</span>With primes"'
    >>> initial_quotes("'With single primes'")
    u'<span class="quo">\\'</span>With single primes\\''

    >>> initial_quotes('<a href="#">"With primes and a link"</a>')
    u'<a href="#"><span class="dquo">"</span>With primes and a link"</a>'

    >>> initial_quotes('&#8220;With smartypanted quotes&#8221;')
    u'<span class="dquo">&#8220;</span>With smartypanted quotes&#8221;'
    """

    quote_finder = re.compile(r"""((<(p|h[1-6]|li|dt|dd)[^>]*>|^)              # start with an opening p, h1-6, li, dd, dt or the start of the string
                                  \s*                                          # optional white space!
                                  (<(a|em|span|strong|i|b)[^>]*>\s*)*)         # optional opening inline tags, with more optional white space for each.
                                  (("|&ldquo;|&\#8220;)|('|&lsquo;|&\#8216;))  # Find me a quote! (only need to find the left quotes and the primes)
                                                                               # double quotes are in group 7, singles in group 8
                                  """, re.VERBOSE)

    def _quote_wrapper(matchobj):
        if matchobj.group(7):
            classname = "dquo"
            quote = matchobj.group(7)
        else:
            classname = "quo"
            quote = matchobj.group(8)
        return """%s<span class="%s">%s</span>""" % (matchobj.group(1), classname, quote)
    output = quote_finder.sub(_quote_wrapper, text)
    return output


def widont(text):
    """Replaces the space between the last two words in a string with ``&nbsp;``
    Works in these block tags ``(h1-h6, p, li, dd, dt)`` and also accounts for
    potential closing inline elements ``a, em, strong, span, b, i``

    >>> widont('A very simple test')
    u'A very simple&nbsp;test'

    Single word items shouldn't be changed
    >>> widont('Test')
    u'Test'
    >>> widont(' Test')
    u' Test'
    >>> widont('<ul><li>Test</p></li><ul>')
    u'<ul><li>Test</p></li><ul>'
    >>> widont('<ul><li> Test</p></li><ul>')
    u'<ul><li> Test</p></li><ul>'

    >>> widont('<p>In a couple of paragraphs</p><p>paragraph two</p>')
    u'<p>In a couple of&nbsp;paragraphs</p><p>paragraph&nbsp;two</p>'

    >>> widont('<h1><a href="#">In a link inside a heading</i> </a></h1>')
    u'<h1><a href="#">In a link inside a&nbsp;heading</i> </a></h1>'

    >>> widont('<h1><a href="#">In a link</a> followed by other text</h1>')
    u'<h1><a href="#">In a link</a> followed by other&nbsp;text</h1>'

    Empty HTMLs shouldn't error
    >>> widont('<h1><a href="#"></a></h1>')
    u'<h1><a href="#"></a></h1>'

    >>> widont('<div>Divs get no love!</div>')
    u'<div>Divs get no love!</div>'

    >>> widont('<pre>Neither do PREs</pre>')
    u'<pre>Neither do PREs</pre>'

    >>> widont('<div><p>But divs with paragraphs do!</p></div>')
    u'<div><p>But divs with paragraphs&nbsp;do!</p></div>'
    """

    widont_finder = re.compile(r"""((?:</?(?:a|em|span|strong|i|b)[^>]*>)|[^<>\s]) # must be proceeded by an approved inline opening or closing tag or a nontag/nonspace
                                   \s+                                             # the space to replace
                                   ([^<>\s]+                                       # must be flollowed by non-tag non-space characters
                                   \s*                                             # optional white space!
                                   (</(a|em|span|strong|i|b)>\s*)*                 # optional closing inline tags with optional white space after each
                                   ((</(p|h[1-6]|li|dt|dd)>)|$))                   # end with a closing p, h1-6, li or the end of the string
                                   """, re.VERBOSE)

    output = widont_finder.sub(r'\1&nbsp;\2', text)
    return output


def typogrify(content):
    """The super typography filter

    Applies the following filters: widont, smartypants, caps, amp, initial_quotes"""

    return number_suffix(
           initial_quotes(
           caps(
           smartypants.smartyPants(
           widont(
           amp(content)), "2"))))

########NEW FILE########
__FILENAME__ = helpers
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.
#
# This module contains helper objects and function for writing third-party code.

import sys
import os
import io
import re
import imp
import shutil
import itertools
import contextlib
import subprocess

from unicodedata import normalize
from collections import defaultdict
from os.path import join, dirname, isdir, isfile, commonprefix, normpath

from acrylamid import log, compat, __file__ as PATH
from acrylamid.errors import AcrylamidException

from acrylamid.core import cache
from acrylamid.utils import batch, hash, rchop

from acrylamid.compat import text_type as str, iteritems, PY2K

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None  # NOQA

__all__ = ['memoize', 'union', 'mkfile', 'hash', 'expand', 'joinurl',
           'safeslug', 'paginate', 'safe', 'system', 'event', 'rchop',
           'discover']

_slug_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')


def memoize(key, value=None):
    """Persistent memory for small values, set and get in a single function.
    If you set a value, it returns whether the new value is different to the
    previous.

    >>> memoize("Foo", 1)
    False
    >>> memoize("Foo", 1)
    True
    >>> memoize("Foo", 2)
    False
    >>> memoize("Foo")
    2

    :param key: get value saved to key, if key does not exist, return None.
    :param value: set key to value
    """
    return cache.memoize(key, value)


def union(first, *args, **kwargs):
    """Takes a list of dictionaries and performs union of each.  Can take additional
    key=values as parameters to overwrite or add key/value-pairs. No side-effects,"""

    new = first.__class__()
    for item in itertools.chain([first], args, [kwargs]):
        new.update(item)

    return new


def identical(obj, other, bs=4096):
    """Takes two file-like objects and return whether they are identical or not."""
    s, t = obj.tell(), other.tell()
    while True:
        a, b = obj.read(bs), other.read(bs)
        if not a or not b or a != b:
            break
    obj.seek(s), other.seek(t)
    return a == b


def mkfile(fileobj, path, ctime=0.0, ns=None, force=False, dryrun=False):
    """Creates entry in filesystem. Overwrite only if fileobj differs.

    :param fileobj: rendered html/xml as file-like object
    :param path: path to write to
    :param ctime: time needed to compile
    :param force: force overwrite, even nothing has changed (defaults to `False`)
    :param dryrun: don't write anything."""

    fileobj.seek(0)

    if isinstance(fileobj, io.TextIOBase):
        open = lambda path, mode: io.open(path, mode + 't', encoding='utf-8')
    else:
        open = lambda path, mode: io.open(path, mode + 'b')

    if isfile(path):
        with open(path, 'r') as other:
            if identical(fileobj, other):
                return event.identical(ns, path)
        if not dryrun:
            if hasattr(fileobj, 'name'):
                shutil.copy(fileobj.name, path)
            else:
                with open(path, 'w') as fp:
                    fp.write(fileobj.read())
        event.update(ns, path, ctime)
    else:
        if not dryrun:
            try:
                os.makedirs(dirname(path))
            except OSError:
                pass
        if not dryrun:
            if hasattr(fileobj, 'name'):
                shutil.copy(fileobj.name, path)
            else:
                with open(path, 'w') as fp:
                    fp.write(fileobj.read())
        event.create(ns, path, ctime)


def expand(url, obj, re=re.compile(r':(\w+)')):
    """Substitutes/expands URL parameters beginning with a colon.

    :param url: a URL with zero or more :key words
    :param obj: a dictionary where we get key from

    >>> expand('/:year/:slug/', {'year': 2012, 'slug': 'awesome title'})
    '/2011/awesome-title/'
    """
    if isinstance(obj, dict):
        return re.sub(lambda m: str(obj.get(m.group(1), m.group(1))), url)
    else:
        return re.sub(lambda m: str(getattr(obj, m.group(1), m.group(1))), url)


def joinurl(*args):
    """Joins multiple urls pieces to one single URL without loosing the root
    (first element). If the URL ends with a slash, Acrylamid automatically
    appends ``index.html``.

    >>> joinurl('/hello/', '/world/')
    '/hello/world/index.html'
    """
    rv = [str(mem) for mem in args]
    if rv[-1].endswith('/'):
        rv.append('index.html')
    return normpath('/'.join(rv))


def safeslug(slug):
    """Generates an ASCII-only slug.  Borrowed from
    http://flask.pocoo.org/snippets/5/"""

    result = []
    if unidecode:
        slug = u"" + unidecode(slug)
    for word in _slug_re.split(slug.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore').decode('utf-8').strip()
        if word:
            result.append(word)
    return u'-'.join(result)


def paginate(lst, ipp, salt="", orphans=0):
    """paginate(lst, ipp, func=lambda x: x, salt=None, orphans=0)

    Yields a triple ((next, current, previous), list of entries, has
    changed) of a paginated entrylist. It will first filter by the specified
    function, then split the ist into several sublists and check wether the
    list or an entry has changed.

    :param lst: the entrylist containing Entry instances.
    :param ipp: items per page
    :param salt: uses as additional identifier in memoize
    :param orphans: avoid N orphans on last page

    >>> for x, values, _, paginate(entryrange(20), 6, orphans=2):
    ...    print(x, values)
    (None, 0, 1), [entries 1..6]
    (0, 1, 2), [entries 7..12]
    (1, 2, None), [entries 12..20]"""

    # detect removed or newly added entries
    modified = cache.memoize('paginate-' + salt, hash(*lst))

    # slice into batches
    res = list(batch(lst, ipp))

    if len(res) >= 2 and len(res[-1]) <= orphans:
        res[-2].extend(res[-1])
        res.pop(-1)

    j = len(res)
    for i, entries in enumerate(res):

        i += 1
        next = None if i == 1 else i-1
        curr = i
        prev = None if i >= j else i+1

        yield (next, curr, prev), entries, modified or any(e.modified for e in entries)


def safe(string):
    """Safe string to fit in to the YAML standard (hopefully). Counterpart
    to :func:`acrylamid.readers.unsafe`."""

    if not string:
        return '""'

    if len(string) < 2:
        return string

    for char in ':%#*?{}[]':
        if char in string:
            if '"' in string:
                return '\'' + string + '\''
            else:
                return '\"' + string + '\"'

    for char, repl in ('\'"', '"\''):
        if string.startswith(char) and string.endswith(char):
            return repl + string + repl
    return string


@compat.implements_to_string
class Link(object):
    """Return a link struct, that contains title and optionally href. If only
    title is given, we use title as href too.  It provides a __unicode__ to
    be compatible with older templates (≤ 0.3.4).

    :param title: link title and href if no href is given
    :param href: href
    """

    def __init__(self, title, href=None):
        self.title = title
        self.href = href

    def __str__(self):
        return self.href

    def __add__(self, other):
        return str(self) + other

    def __radd__(self, other):
        return other + str(other)

link = Link


@contextlib.contextmanager
def chdir(directory):

    cwd = os.getcwd()

    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(cwd)


def system(cmd, stdin=None, **kwargs):
    """A simple front-end to python's horrible Popen-interface which lets you
    run a single shell command (only one, semicolon and && is not supported by
    os.execvp(). Does not catch OSError!

    :param cmd: command to run (a single string or a list of strings).
    :param stdin: optional string to pass to stdin.
    :param kwargs: is passed to :class:`subprocess.Popen`."""

    try:
        if stdin:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE, **kwargs)
            result, err = p.communicate(stdin.encode('utf-8'))
        else:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            result, err = p.communicate()

    except OSError as e:
        raise OSError(e.strerror)

    retcode = p.poll()
    if err or retcode != 0:
        if not err.strip():
            err = 'process exited with %i.' % retcode
        raise AcrylamidException(err.strip() if not PY2K else err.strip().decode('utf-8'))
    return result.strip().decode('utf-8')


class metaevent(type):
    """Add classmethod to each callable, track given methods and intercept
    methods with callbacks added to cls.callbacks"""

    def __new__(cls, name, bases, attrs):

        def intercept(func):
            """decorator which calls callback registered to this method."""
            name = func.func_name if compat.PY2K else func.__name__

            def dec(cls, ns, path, *args, **kwargs):
                for callback in  cls.callbacks[name]:
                    callback(ns, path)
                if name in cls.events:
                    attrs['counter'][name] += 1
                return func(cls, path, *args, **kwargs)
            dec.__doc__ = func.__doc__  # sphinx
            return dec

        for name, func in iteritems(attrs):
            if not name.startswith('_') and callable(func):
                if name in attrs['events']:
                    func = intercept(func)
                attrs[name] = classmethod(func)

        return type.__new__(cls, name, bases, attrs)


class event(compat.metaclass(metaevent, object)):
    """This helper class provides an easy mechanism to give user feedback of
    created, changed or deleted files.  As side-effect every it allows you to
    register your own functions to these events.

    Acrylamid has the following, fairly self-explanatory events: ``create``,
    ``update``, ``skip``, ``identical`` and ``remove``. A callback receives
    the current namespace and the path. The namespace might be None if not
    specified by the originator, but it is recommended to achieve a informal
    standard:

       * the views supply their lowercase name such as ``'entry'`` or
         ``'archive'`` as namespace.
       * asset generation uses the ``'assets'`` namespace.
       * the init, import and new task use their name as namespace.

    To make this clear, the following example just records all newly created
    items from the entry view:

    .. code-block:: python

        from acrylamid.hepers import event

        skipped = []

        def callback(ns, path):

            if ns == 'entry':
                skipped.add(path)

        event.register(callback, to=['create'])

    .. Note:: This class is a singleton and should not be initialized

    .. method:: count(event)

       :param event: count calls of this particular event
       :type event: string"""

    # intercept these event
    events = ('create', 'update', 'remove', 'skip', 'identical')

    callbacks = defaultdict(list)
    counter = defaultdict(int)

    def __init__(self):
        raise TypeError("You can't construct event.")

    def register(self, callback, to=[]):
        """Register a callback to a list of events. Everytime the event
        eventuates, your callback gets called with all arguments of this
        particular event handler.

        :param callback: a function
        :param to: a list of events when your function gets called"""

        for item in to:
            event.callbacks[item].append(callback)

    def count(self, event):
        return self.counter.get(event, 0)

    def reset(self):
        for key in self.counter:
            self.counter[key] = 0

    def create(self, path, ctime=None):
        if ctime:
            log.info("create  [%.2fs] %s", ctime, path)
        else:
            log.info("create  %s", path)

    def update(self, path, ctime=None):
        if ctime:
            log.info("update  [%.2fs] %s", ctime, path)
        else:
            log.info("update  %s", path)

    def skip(self, path):
        log.skip("skip  %s", path)

    def identical(self, path):
        log.skip("identical  %s", path)

    def remove(self, path):
        log.info("remove  %s", path)


def discover(directories, index, filterfunc=lambda filename: True):
    """Import and initialize modules from `directories` list.

    :param directories: list of directories
    :param index: index function"""

    def find(directories, filterfunc):
        """Discover and yield python modules (aka files that endswith .py) if
        `filterfunc` returns True for that filename."""

        for directory in directories:
            for root, dirs, files in os.walk(directory):
                for fname in files:
                    if fname.endswith('.py') and filterfunc(join(root, fname)):
                        yield join(root, fname)

    for filename in find(directories, filterfunc):
        modname, ext = os.path.splitext(os.path.basename(rchop(filename, os.sep + '__init__.py')))
        fp, path, descr = imp.find_module(modname, directories)

        prefix = commonprefix((PATH, filename))
        if prefix:
            modname = 'acrylamid.'
            modname += rchop(filename[len(prefix):].replace(os.sep, '.'), '.py')

        try:
            mod = sys.modules[modname]
        except KeyError:
            try:
                mod = imp.load_module(modname, fp, path, descr)
            except (ImportError, SyntaxError, ValueError) as e:
                log.exception('%r %s: %s', modname, e.__class__.__name__, e)
                continue

        index(mod)

########NEW FILE########
__FILENAME__ = hooks
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import os
import io
import re
import types
import shutil
import multiprocessing

from os.path import isfile, getmtime, isdir, dirname
from tempfile import mkstemp
from functools import partial

from acrylamid import log
from acrylamid.errors import AcrylamidException
from acrylamid.compat import string_types, iteritems

from acrylamid.helpers import event, system, discover
from acrylamid.lib.async import Threadpool

pool = None
tasks = {}


def modified(src, dest):
    return not isfile(dest) or getmtime(src) > getmtime(dest)


def execute(cmd, ns, src, dest=None):
    """Execute `cmd` such as `yui-compressor %1 -o %2` in-place.
    If `dest` is none, you don't have to supply %2."""

    assert '%1' in cmd
    cmd = cmd.replace('%1', src)

    if dest:
        assert '%2' in cmd
        cmd = cmd.replace('%2', dest)

        if not isdir(dirname(dest)):
            os.makedirs(dirname(dest))

    try:
        rv = system(cmd, shell=True)
    except (AcrylamidException, OSError):
        log.exception("uncaught exception during execution")
        return

    if dest is None:
        fd, path = mkstemp()
        with io.open(fd, 'w', encoding='utf-8') as fp:
            fp.write(rv)
        shutil.move(path, src)
        log.info('update  %s', src)
    else:
        log.info('create  %s', dest)


def simple(pool, pattern, normalize, action, ns, path):
    """
    :param pool: threadpool
    :param pattern: if pattern matches `path`, queue action
    :param action: task to run
    """
    if re.match(pattern, normalize(path), re.I):
        if isinstance(action, string_types):
            action = partial(execute, action)
        pool.add_task(action, ns, path)


def advanced(pool, pattern, force, normalize, action, translate, ns, path):
    """
    :param force: re-run task even when the source has not been modified
    :param pattern: a regular expression to match the original path
    :param func: function to run
    :param translate: path translation, e.g. /images/*.jpg -> /images/thumbs/*.jpg
    """
    if not re.match(pattern, normalize(path), re.I):
        return

    if force or modified(path, translate(path)):
        if isinstance(action, string_types):
            action = partial(execute, action)
        pool.add_task(action, ns, path, translate(path))
    else:
        log.skip('skip  %s', translate(path))


def pre(func):
    global tasks
    tasks.setdefault('pre', []).append(func)


def post(func):
    global tasks
    tasks.setdefault('post', []).append(func)


def run(conf, env, type):

    global tasks

    pool = Threadpool(multiprocessing.cpu_count())
    while tasks.get(type):
        pool.add_task(partial(tasks[type].pop(), conf, env))

    pool.wait_completion()


def initialize(conf, env):

    global pool

    hooks, blocks = conf.get('hooks', {}), not conf.get('hooks_mt', True)
    pool = Threadpool(1 if blocks else multiprocessing.cpu_count(), wait=blocks)

    force = env.options.force
    normalize = lambda path: path.replace(conf['output_dir'], '')

    for pattern, action in iteritems(hooks):
        if isinstance(action, (types.FunctionType, string_types)):
            event.register(
                callback=partial(simple, pool, pattern, normalize, action),
                to=['create', 'update'] if not force else event.events)
        else:
            event.register(
                callback=partial(advanced, pool, pattern, force, normalize, *action),
                to=event.events)

    discover([conf.get('HOOKS_DIR', 'hooks/')], lambda x: x)


def shutdown():

    global pool
    pool.wait_completion()

########NEW FILE########
__FILENAME__ = async
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# via http://code.activestate.com/recipes/577187-python-thread-pool/

"""
Asynchronous Tasks
~~~~~~~~~~~~~~~~~~

A simple thread pool implementation, that can be used for parallel I/O.

Example usage::

    >>> def takes(long=10):
    ...     sleep(long)
    ...
    >>> pool = Threadpool(5)
    >>> for x in range(10):
    ...     pool.add_task(takes, x)
    >>> pool.wait_completion()

You can't retrieve the return values, just wait until they finish."""

from threading import Thread
from acrylamid import log
from acrylamid.compat import PY2K, text_type as str

if PY2K:
    from Queue import Queue
else:
    from queue import Queue


class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""

    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception as e:
                log.exception('%s: %s' % (e.__class__.__name__, str(e)))
            self.tasks.task_done()


class Threadpool:
    """Initialize pool with number of workers, that run a function with
    given arguments and catch all exceptions."""

    def __init__(self, num_threads, wait=True):
        self.tasks = Queue(num_threads if wait else 0)
        self.wait = wait
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kargs), self.wait)

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.tasks.join()

########NEW FILE########
__FILENAME__ = history
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.
#
# give update information for Acrylamid

from __future__ import print_function

import io
import re

from os.path import join, dirname

from acrylamid.lib import __file__ as PATH
from acrylamid.colors import blue, red, bold, underline
from acrylamid.helpers import memoize


def changesfor(version):
    """return CHANGES for `version` and whether it *breaks*."""

    with io.open(join(dirname(PATH), 'CHANGES'), encoding='utf-8') as fp:

        rv = []
        section, paragraph, safe = False, False, True

        for line in (line.rstrip() for line in fp if line):

            if not line:
                continue

            m = re.match(r'^(\d\.\d) \(\d{4}-\d{2}-\d{2}\)$', line)

            if m:
                section = m.group(1) == version
                continue

            if section and line.startswith('### '):
                paragraph = 'changes' in line
                continue

            if section and paragraph:
                rv.append(line)
                if 'break' in line:
                    safe = False

    return not safe, '\n'.join(rv)


colorize = lambda text: \
    re.sub('`([^`]+)`', lambda m: bold(blue(m.group(1))).encode('utf-8'),
    re.sub('`([A-Z_*]+)`', lambda m: bold(m.group(1)).encode('utf-8'),
    re.sub('(#\d+)', lambda m: underline(m.group(1)).encode('utf-8'),
    re.sub('(breaks?)', lambda m: red(bold(m.group(1))).encode('utf-8'), text))))


def breaks(env, firstrun):
    """Return whether the new version may break current configuration and print
    all changes between the current and new version."""

    version = memoize('version') or (0, 4)
    if version >= (env.version.major, env.version.minor):
        return False

    memoize('version', (env.version.major, env.version.minor))

    if firstrun:
        return False

    broken = False

    for major in range(version[0], env.version.major or 1):
        for minor in range(version[1], env.version.minor):
            rv, hints = changesfor('%i.%i' % (major, minor + 1))
            broken = broken or rv

            if not hints:
                continue

            print()
            print((blue('Acrylamid') + ' %i.%s' % (major, minor+1) + u' – changes').encode('utf-8'), end="")

            if broken:
                print((u'– ' + red('may break something.')).encode('utf-8'))
            else:
                print()

            print()
            print(colorize(hints).encode('utf-8'))
            print()

    return broken

########NEW FILE########
__FILENAME__ = html
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

"""
Generic HTML tools
~~~~~~~~~~~~~~~~~~

A collection of tools that ease reading and writing HTML. Currently,
there's only a improved version of python's :class:`HTMLParser.HTMLParser`,
that returns the HTML untouched, so you can override specific calls to
add custom behavior.

This implementation is used :mod:`acrylamid.filters.acronyms`,
:mod:`acrylamid.filters.hyphenation` and more advanced in
:mod:`acrylamid.filters.summarize`. It is quite fast, but remains
an unintuitive way of working with HTML."""

import sys
import re

from cgi import escape
from acrylamid.compat import PY2K, unichr

if PY2K:
    from HTMLParser import HTMLParser as DefaultParser, HTMLParseError
    from htmlentitydefs import name2codepoint
else:
    from html.parser import HTMLParser as DefaultParser, HTMLParseError
    from html.entities import name2codepoint


def unescape(s):
    """&amp; -> & conversion"""
    return re.sub('&(%s);' % '|'.join(name2codepoint),
            lambda m: unichr(name2codepoint[m.group(1)]), s)


def format(attrs):
    res = []
    for key, value in attrs:
        if value is None:
            res.append(key)
        else:
            res.append('%s="%s"' % (key, escape(value, quote=True)))
    return ' '.join(res)


if sys.version_info < (3, 0):
    class WTFMixin(object, DefaultParser):
        pass
else:
    class WTFMixin(DefaultParser):
        pass


class HTMLParser(WTFMixin):
    """A more useful base HTMLParser that returns the actual HTML by
    default::

    >>> "<b>Foo</b>" == HTMLParser("<b>Foo</b>").result

    It is intended to use this class as base so you don't make
    the same mistakes I did before.

    .. attribute:: result

        This is the processed HTML."""

    def __init__(self, html):
        DefaultParser.__init__(self)
        self.result = []
        self.stack = []

        self.feed(html)

    def handle_starttag(self, tag, attrs):
        """Append tag to stack and write it to result."""

        self.stack.append(tag)
        self.result.append('<%s %s>' % (tag, format(attrs)) if attrs else '<%s>' % tag)

    def handle_data(self, data):
        """Everything that is *not* a tag shows up as data, but you can't expect
       that it is always a continous sentence or word."""

        self.result.append(data)

    def handle_endtag(self, tag):
        """Append ending tag to result and pop it from the stack too."""

        try:
            self.stack.pop()
        except IndexError:
            pass
        self.result.append('</%s>' % tag)

    def handle_startendtag(self, tag, attrs):
        """Something like ``"<br />"``"""
        self.result.append('<%s %s/>' % (tag, format(attrs)))

    def handle_entityref(self, name):
        """An escaped ampersand like ``"&#38;"``."""
        self.result.append('&' + name + ';')

    def handle_charref(self, char):
        """An escaped umlaut like ``"&auml;"``"""
        self.result.append('&#' + char + ';')

    def handle_comment(self, comment):
        """Preserve HTML comments."""
        self.result.append('<!--' + comment + '-->')

__all__ = ['HTMLParser', 'HTMLParseError', 'unescape']

########NEW FILE########
__FILENAME__ = httpd
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

"""
Internal Webserver
~~~~~~~~~~~~~~~~~~

Launch a dumb webserver as thread."""

import os
import time

from threading import Thread

from acrylamid.utils import force_unicode as u
from acrylamid.compat import PY2K
from acrylamid.helpers import joinurl

if PY2K:
    from SocketServer import TCPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler
else:
    from socketserver import TCPServer
    from http.server import SimpleHTTPRequestHandler


class ReuseAddressServer(TCPServer):
    """avoids socket.error: [Errno 48] Address already in use"""
    allow_reuse_address = True

    def serve_forever(self):
        """Handle one request at a time until doomsday."""
        while not self.kill_received:
            if not self.wait:
                self.handle_request()
            else:
                time.sleep(0.1)


class RequestHandler(SimpleHTTPRequestHandler):
    """This is a modified version of python's -m SimpleHTTPServer to
    serve on a specific sub directory of :func:`os.getcwd`."""

    www_root = '.'
    log_error = lambda x, *y: None

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        return joinurl(u(os.getcwd()), self.www_root, path[len(u(os.getcwd())):])

    def end_headers(self):
        self.send_header("Cache-Control", "max-age=0, must-revalidate")
        SimpleHTTPRequestHandler.end_headers(self)


class Webserver(Thread):
    """A single-threaded webserver to serve while generation.

    :param port: port to listen on
    :param root: serve this directory under /"""

    def __init__(self, port=8000, root='.', log_message=lambda x, *y: None):
        Thread.__init__(self)
        Handler = RequestHandler
        Handler.www_root = root
        Handler.log_message = log_message

        self.httpd = ReuseAddressServer(("", port), Handler)
        self.httpd.wait = False
        self.httpd.kill_received = False

    def setwait(self, value):
        self.httpd.wait = value
    wait = property(lambda self: self.httpd.wait, setwait)

    def run(self):
        self.httpd.serve_forever()
        self.join(1)

    def shutdown(self):
        """"Sets kill_recieved and closes the server socket."""
        self.httpd.kill_received = True
        self.httpd.socket.close()

########NEW FILE########
__FILENAME__ = lazy
# -*- encoding: utf-8 -*-
#
# demandimport.py - global demand-loading of modules for Mercurial
#
# Copyright 2006, 2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.


"""
Lazy Import
~~~~~~~~~~~

Two switches that enable/disable automatic demandloading of modules. Imports
of the following forms will be demand-loaded::

  import a, b.c
  import a.b as c
  from a import b,c # a will be loaded immediately

These imports will not be delayed::

  from a import *
  b = __import__(a)

This is dark magic, currently only used for lazy import in filters as there have been
mysterious exceptions in the jinja2 templating engine when enabled for views as well."""

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

_origimport = __import__


class _demandmod(object):
    """module demand-loader and proxy"""

    def __init__(self, name, globals, locals):
        if '.' in name:
            head, rest = name.split('.', 1)
            after = [rest]
        else:
            head = name
            after = []
        object.__setattr__(self, "_data", (head, globals, locals, after))
        object.__setattr__(self, "_module", None)

    def _extend(self, name):
        """add to the list of submodules to load"""
        self._data[3].append(name)

    def _load(self):
        if not self._module:
            head, globals, locals, after = self._data
            mod = _origimport(head, globals, locals)

            # load submodules
            def subload(mod, p):
                h, t = p, None
                if '.' in p:
                    h, t = p.split('.', 1)
                if not hasattr(mod, h):
                    setattr(mod, h, _demandmod(p, mod.__dict__, mod.__dict__))
                elif t:
                    subload(getattr(mod, h), t)

            for x in after:
                subload(mod, x)

            # are we in the locals dictionary still?
            if locals and locals.get(head) == self:
                locals[head] = mod
            object.__setattr__(self, "_module", mod)

    def __repr__(self):
        if self._module:
            return "<proxied module '%s'>" % self._data[0]
        return "<unloaded module '%s'>" % self._data[0]

    def __call__(self, *args, **kwargs):
        raise TypeError("%s object is not callable" % repr(self))

    def __getattribute__(self, attr):
        if attr in ('_data', '_extend', '_load', '_module'):
            return object.__getattribute__(self, attr)
        self._load()
        return getattr(self._module, attr)

    def __setattr__(self, attr, val):
        self._load()
        setattr(self._module, attr, val)


def _demandimport(name, globals=None, locals=None, fromlist=None, level=None):
    if not locals or fromlist == ('*',):
        # these cases we can't really delay
        return _origimport(name, globals, locals, fromlist)
    elif not fromlist:
        # import a [as b]
        if '.' in name:  # a.b
            base, rest = name.split('.', 1)
            # email.__init__ loading email.mime
            if globals and globals.get('__name__', None) == base:
                return _origimport(name, globals, locals, fromlist)
            # if a is already demand-loaded, add b to its submodule list
            if base in locals:
                if isinstance(locals[base], _demandmod):
                    locals[base]._extend(rest)
                return locals[base]
        return _demandmod(name, globals, locals)
    else:
        if level is not None:
            # from . import b,c,d or from .a import b,c,d
            return _origimport(name, globals, locals, fromlist, level)
        # from a import b,c,d
        mod = _origimport(name, globals, locals)
        # recurse down the module chain
        for comp in name.split('.')[1:]:
            if not hasattr(mod, comp):
                setattr(mod, comp, _demandmod(comp, mod.__dict__, mod.__dict__))
            mod = getattr(mod, comp)
        for x in fromlist:
            # set requested submodules for demand load
            if not(hasattr(mod, x)):
                setattr(mod, x, _demandmod(x, mod.__dict__, locals))
        return mod


def enable():
    "Enable global demand-loading of modules."
    builtins.__import__ = _demandimport


def disable():
    "Disable global demand-loading of modules."
    builtins.__import__ = _origimport


__all__ = ["enable", "disable"]

########NEW FILE########
__FILENAME__ = requests
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

"""
Requests
~~~~~~~~

A simple wrapper around urllib2.

.. function:: head(url, **hdrs)

    Sends a HEAD request to given url but does not catch any exception.

    :param url: url to send the request to
    :param hdrs: a key-value pair that is send within the HTTP header

.. function:: get(url, **hdrs)

    Same like :func:`head` but for GET."""

try:
    from urllib2 import Request, urlopen, HTTPError, URLError
except ImportError:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError


def proto(method, url, **hdrs):

    headers = {'User-Agent': "Mozilla/5.0 Gecko/20120427 Firefox/15.0"}
    headers.update(hdrs)

    req = Request(url, headers=headers)
    req.get_method = lambda : method

    return urlopen(req, timeout=10)


head = lambda url, **hdrs: proto('HEAD', url, **hdrs)
get = lambda url, **hdrs: proto('GET', url, **hdrs)


__all__ = ['head', 'get', 'HTTPError', 'URLError']

########NEW FILE########
__FILENAME__ = log
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import print_function

import sys
import logging
import warnings
from logging import INFO, WARN, DEBUG
from acrylamid.colors import bold, red, green, yellow, black

SKIP = 15
logger = fatal = critical = warn = info = skip = debug = error = exception = None


class TerminalHandler(logging.StreamHandler):
    """A handler that logs everything >= logging.WARN to stderr and everything
    below to stdout."""

    def __init__(self):
        logging.StreamHandler.__init__(self)
        self.stream = None  # reset it; we are not going to use it anyway

    def emit(self, record):
        if record.levelno >= logging.WARN:
            self.__emit(record, sys.stderr)
        else:
            self.__emit(record, sys.stdout)

    def __emit(self, record, strm):
        self.stream = strm
        logging.StreamHandler.emit(self, record)


class ANSIFormatter(logging.Formatter):
    """Implements basic colored output using ANSI escape codes.  Currently acrylamid
    uses nanoc's color and information scheme: skip, create, identical, update,
    re-initialized, removed.

    If log level is greater than logging.WARN the level name is printed red underlined.
    """

    def __init__(self, fmt='[%(levelname)s] %(name)s: %(message)s'):
        logging.Formatter.__init__(self, fmt)

    def format(self, record):

        keywords = {'create': green, 'update': yellow, 'skip': black, 'identical': black,
            're-initialized': yellow, 'remove': black, 'notice': black, 'execute': black}

        if record.levelno in (SKIP, INFO):
            for item in keywords:
                if record.msg.startswith(item):
                    record.msg = record.msg.replace(item, ' '*2 + \
                                    keywords[item](bold(item.rjust(9))))
        elif record.levelno >= logging.WARN:
            record.levelname = record.levelname.replace('WARNING', 'WARN')
            record.msg = ''.join([' '*2, u"" + red(bold(record.levelname.lower().rjust(9))),
                                  '  ', record.msg])

        return logging.Formatter.format(self, record)


class SkipHandler(logging.Logger):
    """Adds ``skip`` as new log item, which has a value of 15

    via <https://github.com/Ismael/big-brother-bot/blob/master/b3/output.py>"""
    def __init__(self, name, level=logging.NOTSET):
        logging.Logger.__init__(self, name, level)

    def skip(self, msg, *args, **kwargs):
        self.log(15, msg, *args, **kwargs)


def init(name, level, colors=True):

    global logger, critical, fatal, warn, info, skip, debug, error, exception

    logging.setLoggerClass(SkipHandler)
    logger = logging.getLogger(name)

    handler = TerminalHandler()
    if colors:
        handler.setFormatter(ANSIFormatter('%(message)s'))

    logger.addHandler(handler)
    logger.setLevel(level)

    error = logger.error
    fatal = logger.fatal
    critical = logger.critical
    warn = logger.warn
    info = logger.info
    skip = logger.skip
    debug = logger.debug
    exception = logger.exception

    warnings.resetwarnings()
    warnings.showwarning = showwarning if level == DEBUG else lambda *x: None


def setLevel(level):
    global logger
    logger.setLevel(level)


def level():
    global logger
    return logger.level


def showwarning(msg, cat, path, lineno):
    print(path + ':%i' % lineno)
    print('%s: %s' % (cat().__class__.__name__, msg))


__all__ = ['fatal', 'warn', 'info', 'skip', 'debug', 'error',
           'WARN', 'INFO', 'SKIP', 'DEBUG', 'setLevel', 'level']

########NEW FILE########
__FILENAME__ = readers
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import unicode_literals

import os
import io
import re
import sys
import abc
import shlex
import codecs
import traceback
import glob

BOM_UTF8 = codecs.BOM_UTF8.decode('utf8')

from os.path import join, getmtime, relpath, splitext, dirname, isfile, normpath
from fnmatch import fnmatch
from datetime import datetime, tzinfo, timedelta

from acrylamid import log, compat
from acrylamid.errors import AcrylamidException
from acrylamid.compat import iteritems, string_types, text_type as str

from acrylamid.utils import (cached_property, Metadata, rchop, lchop,
                             HashableList, force_unicode as u)
from acrylamid.core import cache
from acrylamid.filters import FilterTree
from acrylamid.helpers import safeslug, expand, hash

try:
    import yaml
except ImportError:
    yaml = None  # NOQA
else:
    yaml.Loader.add_constructor(u'tag:yaml.org,2002:timestamp', lambda x, y: y.value)


def load(conf):
    """Load and parse textfiles from content directory and optionally filter by an
    ignore pattern. Filenames ending with a known whitelist of extensions are processed.

    This function is *not* exception-tolerant. If Acrylamid could not handle a file
    it will raise an exception.

    It returns a tuple containing the list of entries sorted by date reverse (newest
    comes first) and other pages (unsorted).

    :param conf: configuration with CONTENT_DIR, CONTENT_EXTENSION and CONTENT_IGNORE set"""

    # list of Entry-objects reverse sorted by date.
    entries, pages, trans, drafts = [], [], [], []

    # config content_extension originally defined as string, not a list
    exts = conf.get('content_extension',['.txt', '.rst', '.md'])
    if isinstance(exts, string_types):
        whitelist = (exts,)
    else:
        whitelist = tuple(exts)

    # collect and skip over malformed entries
    for path in filelist(conf['content_dir'], conf['content_ignore']):
        if path.endswith(whitelist):
            try:
                entry = Entry(path, conf)
                if entry.draft:
                    drafts.append(entry)
                elif entry.type == 'entry':
                    entries.append(entry)
                else:
                    pages.append(entry)
            except AcrylamidException as e:
                log.exception('failed to parse file %s (%s)' % (path, e))
            except:
                log.fatal('uncaught exception for ' + path)
                raise

    # sort by date, reverse
    return sorted(entries, key=lambda k: k.date, reverse=True), pages, trans, drafts


def ignored(cwd, path, patterns, directory):
    """Test wether a path is excluded by the user. The ignore syntax is
    similar to Git: a path with a leading slash means absolute position
    (relative to output root), path with trailing slash marks a directory
    and everything else is just relative fnmatch.

    :param cwd: current directory (root from :py:func:`os.walk`)
    :param path: current path
    :param patterns: a list of patterns
    :param directory: destination directory
    """

    for pattern in patterns:
        if pattern.startswith('/'):
            if fnmatch(join(cwd, path), join(directory, pattern[1:])):
                return True
        elif fnmatch(path, pattern):
            return True
    else:
        return False


def filelist(directory, patterns=[]):
    """Gathers all files in directory but excludes file by patterns. Note, that
    this generator won't raise any (IOError, OSError).  If directory is `None`
    yield nothing."""

    if directory is None:
        raise StopIteration

    for root, dirs, files in os.walk(directory):
        for path in files:
            if not ignored(root, path, patterns, directory):
                yield os.path.join(root, path)

        # don't visit excluded dirs
        for dir in dirs[:]:
            if ignored(root, dir+'/', patterns, directory):
                dirs.remove(dir)

def relfilelist(directory, patterns=[], excludes=[]):
    """Gathers identical files like filelist but with relative paths."""

    for path in filelist(directory, patterns):
        path = relpath(path, directory)
        if path not in excludes:
            yield (path, directory)

class Date(datetime):
    """A :class:`datetime.datetime` object that returns unicode on ``strftime``."""

    def strftime(self, fmt):
        return u(datetime.strftime(self, fmt))


class Timezone(tzinfo):
    """A dummy tzinfo object that gives :class:`datetime.datetime` more
    UTC awareness."""

    def __init__(self, offset=0):
        self.offset = offset

    def __hash__(self):
        return self.offset

    def utcoffset(self, dt):
        return timedelta(hours=self.offset)

    def dst(self, dt):
        return timedelta()


class Reader(compat.metaclass(abc.ABCMeta, object)):
    """This class represents a single entry. Every property from this class is
    available during templating including custom key-value pairs from the
    header. The formal structure is first a YAML with some key/value pairs and
    then the actual content. For example::

        ---
        title: My Title
        date: 12.04.2012, 14:12
        tags: [some, values]

        custom: key example
        image: /path/to/my/image.png
        ---

        Here we start!

    Where you can access the image path via ``entry.image``.

    For convenience Acrylamid maps "filter" and "tag" automatically to "filters"
    and "tags" and also converts a single string into an array containing only
    one string.

    :param filename: valid path to an entry
    :param conf: acrylamid configuration

    .. attribute:: lang

       Language used in this article. This is important for the hyphenation pattern."""

    def __init__(self, conf, meta):

        self.props = Metadata((k, v) for k, v in iteritems(conf)
            if k in ['author', 'lang', 'email', 'date_format',
                     'entry_permalink', 'page_permalink'])

        self.props.update(meta)
        self.type = meta.get('type', 'entry')

        # redirect singular -> plural
        for key, to in [('tag', 'tags'), ('filter', 'filters'), ('template', 'layout')]:
            if key in self.props:
                self.props.redirect(key, to)

        self.filters = self.props.get('filters', [])
        self.hashvalue = hash(self.filename, self.title, self.date.ctime())

    @abc.abstractmethod
    def __hash__(self):
        return

    @abc.abstractproperty
    def source(self):
        return

    @abc.abstractproperty
    def modified(self):
        return

    @abc.abstractproperty
    def lastmodified(self):
        return

    def getfilters(self):
        return self._filters
    def setfilters(self, filters):
        if isinstance(filters, string_types):
            filters = [filters]
        self._filters = FilterTree(filters)
    filters = property(getfilters, setfilters)

    def gettype(self):
        """="Type of this entry. Can be either ``'entry'`` or ``'page'``"""
        return self._type
    def settype(self, value):
        if value not in ('entry', 'page'):
            raise ValueError("item type must be 'entry' or 'page'")
        self._type = value
    type = property(gettype, settype, doc=gettype.__doc__)

    def hasproperty(self, prop):
        """Test whether BaseEntry has prop in `self.props`."""
        return prop in self.props

    @property
    def date(self):
        return datetime.now()

    def __iter__(self):
        for key in self.props:
            yield key

        for key in (attr for attr in dir(self) if not attr.startswith('_')):
            yield key

    def __contains__(self, other):
        return other in self.props or other in self.__dict__

    def __getattr__(self, attr):
        try:
            return self.props[attr]
        except KeyError:
            raise AttributeError(attr)

    __getitem__ = lambda self, attr: getattr(self, attr)


class FileReader(Reader):

    def __init__(self, path, conf):

        self.filename = path
        self.tzinfo = conf.get('tzinfo', None)
        self.defaultcopywildcard = conf.get('copy_wildcard', '_[0-9]*.*')

        with io.open(path, 'r', encoding='utf-8', errors='replace') as fp:

            peak = lchop(fp.read(512), BOM_UTF8)
            fp.seek(0)

            if peak.startswith('---\n'):
                i, meta = yamlstyle(fp)
            elif isrest(peak):
                i, meta = reststyle(fp)
            elif peak.startswith('% '):
                i, meta = pandocstyle(fp)
            else:
                i, meta = markdownstyle(fp)

        meta['title'] = str(meta['title'])  # YAML can convert 42 to an int
        meta['category'] = lchop(dirname(path) + '/', conf['content_dir']).split('/')

        jekyll = r'(?:(.+?)/)?(\d{4}-\d{2}-\d{2})-(.+)'
        m = re.match('^' + conf['content_dir'] + jekyll + '$', splitext(path)[0])

        if m:
            meta.setdefault('date', m.group(2))
            meta.setdefault('slug', m.group(3))

            if m.group(1) is not None:
                meta['category'] = m.group(1).split('/')

        self.offset = i
        Reader.__init__(self, conf, meta)

        path, ext = os.path.splitext(path)
        self.path = lchop(path, conf['content_dir'])
        self.extension = ext[1:]

    def __repr__(self):
        return "<FileReader f'%s'>" % repr(self.filename)[2:-1]

    @property
    def lastmodified(self):
        return getmtime(self.filename)

    @property
    def source(self):
        """Returns the actual, unmodified content."""
        with io.open(self.filename, 'r', encoding='utf-8') as f:
            return lchop(''.join(f.readlines()[self.offset:]).strip('\n'), BOM_UTF8)

    def __hash__(self):
        return self.hashvalue

    @property
    def cachefilename(self):
        return hex(self.hashvalue)[2:]

    @property
    def date(self):
        "Fallback to last modification timestamp if date is unset."
        return Date.fromtimestamp(getmtime(self.filename)).replace(tzinfo=self.tzinfo)

    def getresources(self, wildcards):
        """Generate a list of resources files based on the wildcard(s) passed in."""
        reslist = []
        if isinstance(wildcards, list):
            for term in wildcards:
                # exclude missing and non file types
                reslist.extend([normpath(f) for f in glob.glob(
                    join(dirname(self.filename), term)) if isfile(f)])
        elif wildcards is None:
            # use default wildcard appended to entry filename
            reslist = [normpath(f) for f in glob.glob(
                splitext(self.filename)[0] + self.defaultcopywildcard) if isfile(f)]
        else:
            # provided wildcard appended to input directory
            reslist = [normpath(f) for f in glob.glob(
                join(dirname(self.filename), wildcards)) if isfile(f)]
        return reslist


class MetadataMixin(object):

    @cached_property
    def slug(self):
        """ascii safe entry title"""
        slug = self.props.get('slug', None)
        if not slug:
            slug = safeslug(self.title)
        return slug

    @cached_property
    def permalink(self):
        """Actual permanent link, depends on entry's property and ``permalink_format``.
        If you set permalink in the YAML header, we use this as permalink otherwise
        the URL without trailing *index.html.*"""

        try:
            return self.props['permalink']
        except KeyError:
            return expand(rchop(self.props['%s_permalink' % self.type], 'index.html'), self)

    @cached_property
    def date(self):
        """Parse date value and return :class:`datetime.datetime` object.
        You can set a ``DATE_FORMAT`` in your :doc:`conf.py` otherwise
        Acrylamid tries several format strings and throws an exception if
        no pattern works."""

        # alternate formats from pelican.utils, thank you!
        # https://github.com/ametaireau/pelican/blob/master/pelican/utils.py
        formats = ['%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M',
                   '%Y-%m-%d', '%Y/%m/%d',
                   '%d-%m-%Y', '%Y-%d-%m',  # Weird ones
                   '%d/%m/%Y', '%d.%m.%Y',
                   '%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S']

        if 'date' not in self.props:
            if self.type == 'entry':
                log.warn("using mtime from %r" % self.filename)
            return super(MetadataMixin, self).date  # Date.fromtimestamp(self.mtime)

        string = re.sub(' +', ' ', self.props['date'])
        formats.insert(0, self.props['date_format'])

        for date_format in formats:
            try:
                return Date.strptime(string, date_format).replace(tzinfo=self.tzinfo)
            except ValueError:
                pass
        else:
            raise AcrylamidException("%r is not a valid date" % string)

    @cached_property
    def resources(self):
        """List of resource file paths that were copied with the entry from
        the copy: wildcard"""

        res = []
        if self.hasproperty('copy'):
            res = HashableList(self.getresources(self.props.get('copy')))
        return res

    @property
    def year(self):
        """entry's year as an integer"""
        return self.date.year

    @property
    def imonth(self):
        """entry's month as an integer"""
        return self.date.month

    @property
    def month(self):
        """entry's month as zero padded string"""
        return '%02d' % self.imonth

    @property
    def iday(self):
        """entry's day as an integer"""
        return self.date.day

    @property
    def day(self):
        """entry's day as zero padded string"""
        return '%02d' % self.iday

    @property
    def ihour(self):
        """entry's hour as an integer"""
        return self.date.hour

    @property
    def hour(self):
        """entry's hour as zero padded string"""
        return '%02d' % self.ihour

    @property
    def iminute(self):
        """entry's minute as an integer"""
        return self.date.minute

    @property
    def minute(self):
        """entry's minute as zero padded string"""
        return '%02d' % self.iminute

    @property
    def tags(self):
        """Tags applied to this entry, if any.  If you set a single string it
        is converted to an array containing this string."""

        fx = self.props.get('tags', [])
        if isinstance(fx, string_types):
            return [fx]
        return fx

    @property
    def draft(self):
        """If set to True, the entry will not appear in articles, index, feed and tag view."""
        return True if self.props.get('draft', False) else False

    @property
    def description(self):
        """first 50 characters from the source"""
        try:
            return self.props['description']
        except KeyError:
            return self.source[:50].strip() + u'...'


class ContentMixin(object):
    """Lazy evaluation and content caching + filtering."""

    @property
    def content(self):
        """Returns the processed content.  This one of the core functions of
        acrylamid: it compiles incrementally the filter chain using a tree
        representation and saves final output or intermediates to cache, so
        we can rapidly re-compile the whole content.

        The cache is rather dumb: Acrylamid can not determine wether it differs
        only in a single character. Thus, to minimize the overhead the cache
        object is zlib-compressed."""

        # previous value
        pv = None

        # this is our cache filename
        path = self.cachefilename

        # remove *all* intermediates when entry has been modified
        if cache.getmtime(path) > 0.0 and self.modified:
            cache.remove(path)

        if self.hasproperty('copy'):
            res = self.resources
            if res:
                # use ascii record separator between paths, ignore empty list
                cache.set(path, 'resources', '\x1e'.join(res))

        # growing dependencies of the filter chain
        deps = []

        for fxs in self.filters.iter(context=self.context):

            # extend dependencies
            deps.extend(fxs)

            # key where we save this filter chain
            key = hash(*deps)

            try:
                rv = cache.get(path, key)
                if rv is None:
                    res = self.source if pv is None else pv
                    for f in fxs:
                        res = f.transform(res, self, *f.args)
                    pv = cache.set(path, key, res)
                else:
                    pv = rv
            except (IndexError, AttributeError):
                # jinja2 will ignore these Exceptions, better to catch them before
                traceback.print_exc(file=sys.stdout)

        return pv

    @cached_property
    def modified(self):
        changed = self.lastmodified > cache.getmtime(self.cachefilename)
        # skip resource check if changed is true
        if not changed and self.hasproperty('copy'):
            # using ascii record separator between paths, ignore empty list
            pv = cache.get(self.cachefilename, 'resources')
            if pv:
                return self.resources != pv.split('\x1e')
            else:
                # flag as modified if resource list is not empty and cache is
                return (not self.resources) == False
        return changed


class Entry(ContentMixin, MetadataMixin, FileReader):
    pass


def unsafe(string):
    """Try to remove YAML string escape characters safely from `string`.

    Title: "AttributeError: get\_id" when creating an object

    Should retain the quotations around AttributeError. Single backslashes
    are removed if not preceded by another backslash."""

    if len(string) < 2:
        return string

    string = re.sub(r'\\\\', r'\\', re.sub(r'([^\\]|^)\\([^\\])', r'\1\2', string))

    for char in "'", '"':
        if string == 2*char:
            return ''
        try:
            if string.startswith(char) and string.endswith(char):
                return string[1:-1]
        except IndexError:
            continue
    else:
        return string


def distinguish(value):
    """Convert :param value: to None, Int, Float, Bool, a List or String.
    """
    if not isinstance(value, string_types):
        return value

    if not isinstance(value, string_types):
        value = str(value)

    if value in ['None', 'none', '~', 'null']:
        return None
    elif re.match(r'^-?\d+$', value):
        return int(value)
    elif re.match(r'^-?\d+.\d+$', value):
        return float(value)
    elif value in ['True', 'true', 'on']:
        return True
    elif value in ['False', 'false', 'off']:
        return False
    elif len(value) >= 2 and value[0] == '[' and value[-1] == ']':
        tokenizer = shlex.shlex((value[1:-1]).encode('utf-8'), posix=True)
        tokenizer.whitespace = ','.encode('utf-8')
        tokenizer.whitespace_split = True
        tokens = [unsafe(val.decode('utf-8').strip()) for val in list(tokenizer)]
        return [val for val in tokens if val]
    else:
        return unsafe(value)


def markdownstyle(fileobj):
    """Parse Markdown Metadata without converting the source code. Mostly copy&paste
    from the 'meta' extension but slighty modified to fit to Acrylamid: we try to parse
    a value into a python value (via :func:`distinguish`)."""

    # -- from markdown.extensions.meta
    meta_re = re.compile(r'^[ ]{0,3}(?P<key>[A-Za-z0-9._-]+):\s*(?P<value>.*)')
    meta_more_re = re.compile(r'^[ ]{4,}(?P<value>.*)')

    i = 0
    meta, key = {}, None

    while True:
        line = fileobj.readline(); i += 1

        if line.strip() == '':
            break  # blank line - done

        m1 = meta_re.match(line)
        if m1:
            key = m1.group('key').lower().strip()
            value = distinguish(m1.group('value').strip())
            meta.setdefault(key, []).append(value)
        else:
            m2 = meta_more_re.match(line)
            if m2 and key:
                # Add another line to existing key
                meta[key].append(m2.group('value').strip())
            else:
                break  # no meta data - done

    if not meta:
        raise AcrylamidException("no meta information in %r found" % fileobj.name)

    for key, values in iteritems(meta):
        if len(values) == 1:
            meta[key] = values[0]

    return i, meta


def isrest(peak):
    """Determine whether the first 512 bytes are written in reST."""

    try:
        a, b = re.match('^(.+?)\n((?:-|=|#)+)', peak).groups()
    except (ValueError, AttributeError):
        return False
    return len(b) >= len(a)


def reststyle(fileobj):
    """Parse metadata from reStructuredText document when the first two lines are
    valid reStructuredText headlines followed by metadata fields.

    -- http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#field-lists"""

    import docutils
    from docutils.core import publish_doctree

    title = fileobj.readline().strip('\n')
    dash = fileobj.readline().strip('\n')

    if not title or not dash:
        raise AcrylamidException('No title given in %r' % fileobj.name)

    if len(dash) < len(title) or dash.count(dash[0]) < len(dash):
        raise AcrylamidException('title line does not match second line %r' % fileobj.name)

    i = 2
    meta = []

    while True:
        line = fileobj.readline(); i += 1

        if not line.strip() and i == 3:
            continue
        elif not line.strip():
            break  # blank line - done
        else:
            meta.append(line)

    document = publish_doctree(''.join(meta))
    meta = dict(title=title)

    for docinfo in document.traverse(docutils.nodes.docinfo):
        for element in docinfo.children:
            if element.tagname == 'field':  # custom fields
                name_elem, body_elem = element.children
                name = name_elem.astext()
                value = body_elem.astext()
            else:  # standard fields (e.g. filters)
                name = element.tagname
                value = element.astext()
            name = name.lower()

            if '\n\n' in value:
                value = value.split('\n\n')  # Y U NO DETECT UR LISTS?
            elif '\n' in value:
                value = value.replace('\n', ' ')  # linebreaks in wrapped sentences

            meta[name] = distinguish(value.split('\n\n') if '\n\n' in value else value)

    return i, meta


def pandocstyle(fileobj):
    """A function to parse the so called 'Title block' out of Pandoc-formatted documents.
    Provides very simple parsing so that Acrylamid won't choke on plain Pandoc documents.

    See http://johnmacfarlane.net/pandoc/README.html#title-block

    Currently not implemented:
     - Formatting within title blocks
     - Man-page writer title block extensions
    """

    meta_pan_re = re.compile(r'^[ ]{0,3}%+\s*(?P<value>.*)')
    meta_pan_more_re = re.compile(r'^\s*(?P<value>.*)')
    meta_pan_authsplit = re.compile(r';+\s*')

    i, j = 0, 0
    meta, key = {}, None
    poss_keys = ['title', 'author', 'date']

    while True:
        line = fileobj.readline(); i += 1

        if line.strip() == '':
            break  # blank line - done

        if j + 1 > len(poss_keys):
            raise AcrylamidException(
                "%r has too many items in the Pandoc title block."  % fileobj.name)

        m1 = meta_pan_re.match(line)
        if m1:
            key = poss_keys[j]; j += 1
            valstrip = m1.group('value').strip()
            if not valstrip:
                continue
            value = distinguish(m1.group('value').strip())
            if key == 'author':
                value = value.strip(';')
                value = meta_pan_authsplit.split(value)
            meta.setdefault(key, []).append(value)
        else:
            m2 = meta_pan_more_re.match(line)
            if m2 and key:
                # Add another line to existing key
                value = m2.group('value').strip()
                if key == 'author':
                    value = value.strip(';')
                    value = meta_pan_authsplit.split(value)
                meta[key].append(value)
            else:
                break  # no meta data - done

    if 'title' not in meta:
         raise AcrylamidException('No title given in %r' % fileobj.name)

    if len(meta['title']) > 1:
        meta['title'] = ' '.join(meta['title'])

    if 'author' in meta:
        meta['author'] = sum(meta['author'], [])
    else:
        log.warn('%s does not have an Author in the Pandoc title block.' % fileobj.name)

    for key, values in iteritems(meta):
        if len(values) == 1:
            meta[key] = values[0]

    return i, meta


def yamlstyle(fileobj):
    """Open and read content and return metadata and the position where the
    actual content begins.

    If ``pyyaml`` is available we use this parser but we provide a dumb
    fallback parser that can handle simple assigments in YAML.

    :param fileobj: fileobj, utf-8 encoded
    """

    head = []
    i = 0

    while True:
        line = fileobj.readline(); i += 1
        if i == 1 and not line.startswith('---'):
            raise AcrylamidException("no meta information in %r found" % fileobj.name)
        elif i > 1 and not line.startswith('---'):
            head.append(line)
        elif i > 1 and line.startswith('---') or not line:
            break

    if yaml:
        try:
            return i, yaml.load(''.join(head))
        except yaml.YAMLError as e:
            raise AcrylamidException('YAMLError: %s' % str(e))
    else:
        props = {}
        for j, line in enumerate(head):
            if line[0] == '#' or not line.strip():
                continue
            try:
                key, value = [x.strip() for x in line.split(':', 1)]
            except ValueError:
                raise AcrylamidException('%s:%i ValueError: %s\n%s' %
                    (fileobj.name, j, line.strip('\n'),
                    ("Either your YAML is malformed or our naïve parser is to dumb \n"
                     "to read it. Revalidate your YAML or install PyYAML parser with \n"
                     "> easy_install -U pyyaml")))
            props[key] = distinguish(value)

    if 'title' not in props:
        raise AcrylamidException('No title given in %r' % fileobj.name)

    return i, props

########NEW FILE########
__FILENAME__ = refs
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from functools import partial
from itertools import chain
from collections import defaultdict

from acrylamid.core import cache
from acrylamid.utils import hash
from acrylamid.compat import map

__orig_refs = None
__seen_refs = None
__entry_map = None


def load(*entries):
    """Initialize references, load previous state."""
    global __orig_refs, __seen_refs, __entry_map

    __seen_refs = defaultdict(set)
    __orig_refs = cache.memoize('references') or defaultdict(set)
    __entry_map = dict((hash(entry), entry) for entry in chain(*entries))


def save():
    """Save new references state to disk."""
    global __seen_refs
    cache.memoize('references', __seen_refs)


def modified(key, references):
    """Check whether an entry hash `key` has modified `references`. This
    function takes the return values from :func:`refernces`."""

    global __orig_refs, __entry_map

    if not references:
        return False

    if __orig_refs[key] != __seen_refs[key]:
        return True

    try:
        return any(__entry_map[ref].modified for ref in references)
    except KeyError:
        return True


def references(entry):
    """Return hash for entry and the referenced entries' hashes."""
    global __seen_refs
    return hash(entry), __seen_refs.get(hash(entry), set())


def track(func):
    """A syntactic-sugar decorator to automatically track yielded
    references from an entry. See :class:`Translation` in
    :mod:`acrylamid.views.entry` for an example."""

    def dec(entry, item):
        append(entry, item)
        return item

    return lambda entry, **kw: map(partial(dec, entry), func(entry, **kw))


def append(entry, *references):
    """Appenf `references` to `entry`."""
    global __seen_refs

    for ref in references:
        __seen_refs[hash(entry)].add(hash(ref))

########NEW FILE########
__FILENAME__ = check
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import print_function

import sys
import io
import re
import time
import random
import collections

from xml.sax.saxutils import unescape

from acrylamid import readers, helpers, compat
from acrylamid.tasks import task, argument
from acrylamid.colors import green, yellow, red, blue, white

from acrylamid.lib.async import Threadpool
from acrylamid.lib.requests import get, head, HTTPError, URLError

if compat.PY2K:
    from urllib import quote
else:
    from urllib.parse import quote

arguments = [
    argument("action", nargs="?", choices=["W3C", "links"], default="W3C",
        help="check action (default: W3C compatibility)"),
    argument("-r", "--random", dest="random", action="store_true", default=False,
        help="random order"),
    argument("-s", type=float, default=0.2, dest="sleep",
        help="seconds between requests (default 0.2)"),
    argument("-w", action="store_true", default=False, dest="warn",
        help="show W3C warnings"),
    argument("-j", "--jobs", dest="jobs", type=int, default=10, help="N parallel requests"),
]


def w3c(paths, conf, warn=False, sleep=0.2):
    """Validate HTML by using the validator.w3.org API.

    :param paths: a list of HTML files we map to our actual domain
    :param conf: configuration
    :param warn: don't handle warnings as success when set
    :param sleep: sleep between requests (be nice to their API)"""

    for path in paths:
        url = path[len(conf['output_dir'])-1:]

        resp = head("http://validator.w3.org/check?uri=" + \
            helpers.joinurl(conf['www_root'], quote(url)))

        print(helpers.rchop(url, 'index.html'), end=' ')

        if resp.code != 200:
            print(red('not 200 Ok!'))
            continue

        headers = resp.info()
        if headers['x-w3c-validator-status'] == "Abort":
            print(red("Abort"))
        elif headers['x-w3c-validator-status'] == 'Valid':
            if int(headers['x-w3c-validator-warnings']) == 0:
                print(green('Ok'))
            else:
                if warn:
                    print(yellow(headers['x-w3c-validator-warnings'] + ' warns'))
                else:
                    print(green('Ok'))
        else:
            res = headers['x-w3c-validator-errors'] + ' errors, ' + \
                  headers['x-w3c-validator-warnings'] + ' warns'
            print(red(res))

        time.sleep(sleep)


def validate(paths, jobs):
    """Validates a list of urls using up to N threads.

    :param paths: a list of HTML files where we search for a-href's
    :param jobs: numbers of threads used to send I/O requests"""

    ahref = re.compile(r'<a [^>]*href="([^"]+)"[^>]*>.*?</a>')
    visited, urls = set(), collections.defaultdict(list)

    def check(url, path):
        """A HEAD request to URL.  If HEAD is not allowed, we try GET."""

        try:
            get(url, timeout=10)
        except HTTPError as e:
            if e.code == 405:
                try:
                    get(url, path, 'GET', True)
                except URLError as e:
                    print('  ' + yellow(e.reason), url)
                    print(white('  -- ' + path))
            else:
                print('  ' + red(e.code), url)
                print(white('  -- ' + path))
        except URLError as e:
            print('  ' + yellow(e.reason), url)
            print(white('  -- ' + path))

    # -- validation
    for path in paths:

        with io.open(path, 'r', encoding='utf-8') as fp:
            data = fp.read()

        for match in ahref.finditer(data):
            a = match.group(1)
            if a.startswith(('http://', 'https://')):
                if a not in visited:
                    visited.add(a)
                    urls[path].append(a)

    print()
    print("Trying", blue(len(visited)), "links...")
    print()

    pool = Threadpool(jobs)
    for path in urls:
        for url in urls[path]:
            pool.add_task(check, *[unescape(url), path])

    try:
        pool.wait_completion()
    except KeyboardInterrupt:
        sys.exit(1)


@task('check', arguments, "run W3C or validate links")
def run(conf, env, options):
    """Subcommand: check -- run W3C over generated output and check destination
    of linked items"""

    paths = [path for path in readers.filelist(conf['output_dir']) if path.endswith('.html')]

    if options.random:
        random.shuffle(paths)

    if options.action == 'W3C':
        w3c(paths, conf, warn=options.warn, sleep=options.sleep)
    else:
        validate(paths, options.jobs)

########NEW FILE########
__FILENAME__ = deploy
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import print_function

import sys
import os
import argparse
import subprocess

from acrylamid import log
from acrylamid.tasks import argument, task
from acrylamid.errors import AcrylamidException
from acrylamid.compat import iterkeys, iteritems, string_types, PY2K

arguments = [
    argument("task", nargs="?"),
    argument("args", nargs=argparse.REMAINDER),
    argument("--list", dest="list", action="store_true", default=False,
        help="list available tasks")
]


@task(['deploy', 'dp'], arguments, help="run task")
def run(conf, env, options):
    """Subcommand: deploy -- run the shell command specified in
    DEPLOYMENT[task] using Popen. Each string value from :doc:`conf.py` is
    added to the execution environment. Every argument after ``acrylamid
    deploy task ARG1 ARG2`` is appended to cmd."""

    if options.list:
        for task in iterkeys(conf.get('deployment', {})):
            print(task)
        sys.exit(0)

    task, args = options.task or 'default', options.args
    cmd = conf.get('deployment', {}).get(task, None)

    if not cmd:
        raise AcrylamidException('no tasks named %r in conf.py' % task)

    # apply ARG1 ARG2 ... and -v --long-args to the command, e.g.:
    # $> acrylamid deploy task arg1 -b --foo
    cmd += ' ' + ' '.join(args)

    enc = sys.getfilesystemencoding()
    env = os.environ
    env.update(dict([(k.upper(), v.encode(enc, 'replace') if PY2K else v)
        for k, v in iteritems(conf) if isinstance(v, string_types)]))

    log.info('execute  %s', cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    while True:
        output = p.stdout.read(1)
        if output == b'' and p.poll() != None:
            break
        if output != b'':
            sys.stdout.write(output.decode(enc))
            sys.stdout.flush()

########NEW FILE########
__FILENAME__ = imprt
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import print_function

import os
import io
import re
import sys
import shutil
import tempfile
import getpass

from base64 import b64encode
from datetime import datetime

from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

from email.utils import parsedate_tz, mktime_tz
from os.path import join, dirname, isfile

from acrylamid import log, commands
from acrylamid.tasks import task, argument
from acrylamid.errors import AcrylamidException
from acrylamid.compat import PY2K, iteritems, map, filter

from acrylamid.readers import Entry
from acrylamid.helpers import event, safe, system
from acrylamid.lib.html import unescape

if PY2K:
    from urllib2 import urlopen, Request, HTTPError
    from urlparse import urlsplit
else:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
    from urllib.parse import urlsplit

try:
    input = raw_input
except NameError:
    pass

arguments = [
    argument("src", metavar="FILE|URL"),
    argument("-f", "--force", dest="force", action="store_true",
        help="overwrite existing entries", default=False),
    argument("-m", dest="fmt", default="Markdown",
        help="reconvert HTML to FMT"),
    argument("-k", "--keep-links", dest="keep", action="store_true",
        help="keep permanent links", default=False),
    argument("-p", "--pandoc", dest="pandoc", action="store_true",
        help="use pandoc first", default=False),
    argument("-a", dest="args", nargs="+", action="store", metavar="ARG",
        type=str, help="add argument to header section", default=[]),
]

if sys.version_info < (2, 7):
    setattr(ElementTree, 'ParseError', ExpatError)

# no joke
USED_WORDPRESS = False


class InputError(Exception):
    pass


def convert(data, fmt='markdown', pandoc=False):
    """Reconversion of HTML to Markdown or reStructuredText.  Defaults to Markdown,
    but can be in fact every format pandoc supports. If pandoc is not available, try
    some specific conversion tools like html2text and html2rest.

    :param html: raw content to convert to
    :param html: format to reconvert to"""

    if fmt in ('Markdown', 'markdown', 'mkdown', 'md', 'mkd'):
        cmds = ['html2text']
        fmt = 'markdown'
    elif fmt in ('rst', 'restructuredtext', 'rest', 'reStructuredText'):
        cmds = ['html2rest']
        fmt = 'rst'
    else:
        cmds = []

    p = ['pandoc', '--normalize', '-f', 'html', '-t', fmt, '--strict', '--no-wrap', '--parse-raw']
    cmds.insert(0, p) if pandoc or fmt == 'rst' else cmds.append(p)

    if fmt == 'html':
        return data, 'html'

    #  - item.find(foo).text returns None if no CDATA
    #  - pandoc waits for input if a zero-length string is given
    if data is None or data is '':
        return '', fmt

    for cmd in cmds:
        try:
            return system(cmd, stdin=data), fmt.lower()
        except AcrylamidException as e:
            log.warn(e.args[0])
        except OSError:
            pass
    else:
        return data, 'html'


def rss(xml):

    if 'xmlns:wp' in xml:
        raise InputError('WordPress dump')

    def parse_date_time(stamp):
        ts = parsedate_tz(stamp)
        ts = mktime_tz(ts)
        return datetime.fromtimestamp(ts)

    def generate(item):

        entry = {}
        for k, v in iteritems({'title': 'title', 'date': 'pubDate',
                               'link': 'link', 'content': 'description'}):
            try:
                entry[k] = item.find(v).text if k != 'content' \
                                             else unescape(item.find(v).text)
            except (AttributeError, TypeError):
                pass

        if any(filter(lambda k: k not in entry, ['title', 'date', 'link', 'content'])):
            raise AcrylamidException('invalid RSS 2.0 feed: provide at least title, ' \
                                     + 'link, content and pubDate!')

        return {'title': entry['title'],
               'content': entry['content'],
               'date': parse_date_time(entry['date']),
               'link': entry['link'],
               'tags': [cat.text for cat in item.findall('category')]}

    try:
        tree = ElementTree.fromstring(xml.encode('utf-8'))
    except ElementTree.ParseError:
        raise InputError('no well-formed XML')
    if tree.tag != 'rss' or tree.attrib.get('version') != '2.0':
        raise InputError('no RSS 2.0 feed')

    defaults = {'author': None}
    channel = tree.getchildren()[0]

    for k, v in iteritems({'title': 'sitename', 'link': 'www_root',
                           'language': 'lang', 'author': 'author'}):
        try:
            defaults[v] = channel.find(k).text
        except AttributeError:
            pass

    return defaults, list(map(generate, channel.findall('item')))

    try:
        tree = ElementTree.fromstring(xml.encode('utf-8'))
    except ElementTree.ParseError:
        raise InputError('no well-formed XML')
    if tree.tag != 'rss' or tree.attrib.get('version') != '2.0':
        raise InputError('no RSS 2.0 feed')

    defaults = {'author': None}
    channel = tree.getchildren()[0]

    for k, v in iteritems({'title': 'sitename', 'link': 'www_root',
                           'language': 'lang', 'author': 'author'}):
        try:
            defaults[v] = channel.find(k).text
        except AttributeError:
            pass

    return defaults, list(map(generate, channel.findall('item')))


def atom(xml):

    def parse_date_time(stamp):
        ts = parsedate_tz(stamp)
        ts = mktime_tz(ts)
        return datetime.fromtimestamp(ts)

    def generate(item):

        entry = {}

        try:
            entry['title'] = item.find(ns + 'title').text
            entry['date'] = item.find(ns + 'updated').text
            entry['link'] = item.find(ns + 'link').text
            entry['content'] = item.find(ns + 'content').text
        except (AttributeError, TypeError):
            raise AcrylamidException('invalid Atom feed: provide at least title, '
                                     + 'link, content and updated!')

        if item.find(ns + 'content').get('type', 'text') == 'html':
            entry['content'] = unescape(entry['content'])

        return {'title': entry['title'],
               'content': entry['content'],
               'date': datetime.strptime(entry['date'], "%Y-%m-%dT%H:%M:%SZ"),
               'link': entry['link'],
               'tags': [x.get('term') for x in item.findall(ns + 'category')]}

    try:
        tree = ElementTree.fromstring(xml.encode('utf-8'))
    except ElementTree.ParseError:
        raise InputError('no well-formed XML')

    if not tree.tag.endswith('/2005/Atom}feed'):
        raise InputError('no Atom feed')

    ns = '{http://www.w3.org/2005/Atom}'  # etree Y U have stupid namespace handling?
    defaults = {}

    defaults['sitename'] = tree.find(ns + 'title').text
    defaults['author'] = tree.find(ns + 'author').find(ns + 'name').text

    www_root = [a for a in tree.findall(ns + 'link')
        if a.attrib.get('rel', 'alternate') == 'alternate']
    if www_root:
         defaults['www_root'] = www_root[0].attrib.get('href')

    return defaults, list(map(generate, tree.findall(ns + 'entry')))


def wordpress(xml):
    """WordPress to Acrylamid, inspired by the Astraeus project."""

    if 'xmlns:wp' not in xml:
        raise InputError('not a WP dump')

    global USED_WORDPRESS
    USED_WORDPRESS = True

    def generate(item):

        entry = {
            'title': item.find('title').text,
            'link': item.find('link').text,

            'content': (item.find('%sencoded' % cons).text or '').replace('\n', '<br />\n'),
            'description': item.find('%sencoded' % excerptns).text or '',
            'date': datetime.strptime(item.find('%spost_date' % wpns).text,
                "%Y-%m-%d %H:%M:%S"),

            'author': item.find('%screator' % dcns).text,
            'tags': [tag.text for tag in item.findall('category')]
        }

        # attachment, nav_menu_item, page, post
        entry['type'] = item.find('%spost_type' % wpns).text

        if entry['type'] == 'post':
            entry['type'] = 'entry'

        if item.find('%sstatus' % wpns).text != 'publish':
            entry['draft'] = True

        return entry

    try:
        tree = ElementTree.fromstring(xml.encode('utf-8'))
    except ElementTree.ParseError:
        raise InputError('no well-formed XML')

    # wordpress name spaces
    dcns = '{http://purl.org/dc/elements/1.1/}'
    cons = '{http://purl.org/rss/1.0/modules/content/}'

    defaults = {
        'title': tree.find('channel/title').text,
        'www_root': tree.find('channel/link').text
    }

    for version in range(1, 10):
        wpns = '{http://wordpress.org/export/1.%i/}' % version
        excerptns = '{http://wordpress.org/export/1.%i/excerpt/}' % version
        if tree.find('channel/%swxr_version' % wpns) is None:
            continue
        entries = list(map(generate, tree.findall('channel/item')))
        return defaults, [entry for entry in entries if entry['type'] in ('page', 'entry')]


def fetch(url, auth=None):
    """Fetch URL, optional with HTTP Basic Authentication."""

    if not (url.startswith('http://') or url.startswith('https://')):
        try:
            with io.open(url, 'r', encoding='utf-8', errors='replace') as fp:
                return u''.join(fp.readlines())
        except OSError as e:
            raise AcrylamidException(e.args[0])

    req = Request(url)
    if auth:
        req.add_header('Authorization', 'Basic ' + b64encode(auth))

    try:
        r = urlopen(req)
    except HTTPError as e:
        raise AcrylamidException(e.msg)

    if r.getcode() == 401:
        user = input('Username: ')
        passwd = getpass.getpass()
        fetch(url, user + ':' + passwd)
    elif r.getcode() == 200:
        try:
            enc = re.search('charset=(.+);?', r.headers.get('Content-Type', '')).group(1)
        except AttributeError:
            enc = 'utf-8'
        return u'' + r.read().decode(enc)

    raise AcrylamidException('invalid status code %i, aborting.' % r.getcode())


def parse(content):

    for method in (atom, rss, wordpress):
        try:
            return method(content)
        except InputError:
            pass
    else:
        raise AcrylamidException('unable to parse source')


def build(conf, env, defaults, items, options):

    def create(defaults, item):

        global USED_WORDPRESS
        fd, tmp = tempfile.mkstemp(suffix='.txt')

        with io.open(fd, 'w', encoding='utf-8') as f:
            f.write(u'---\n')
            f.write(u'title: %s\n' % safe(item['title']))
            if item.get('author') != defaults.get('author'):
                f.write(u'author: %s\n' % (item.get('author') or defaults.get('author')))
            f.write(u'date: %s\n' % item['date'].strftime(conf['date_format']))
            #f.write(u'filter: %s\n' % item['filter'])
            if 'draft' in item:
                f.write(u'draft: %s\n' % item['draft'])
            if 'tags' in item:
                f.write(u'tags: [%s]\n' % ', '.join(item['tags']))
            if item.get('description'):
                f.write(u'description: %s\n' % item['description'])
            if 'permalink' in item:
                f.write(u'permalink: %s\n' % item['permalink'])
            if item.get('type', 'entry') != 'entry':
                f.write(u'type: %s\n' % item['type'])
            for arg in options.args:
                f.write(arg.strip() + u'\n')
            f.write(u'---\n\n')

            # this are fixes for WordPress because they don't save HTML but a
            # stupid mixed-in form of HTML making it very difficult to get either HTML
            # or reStructuredText/Markdown
            if USED_WORDPRESS and item['filter'] == 'markdown':
                item['content'] = item['content'].replace("\n ", "  \n")
            elif USED_WORDPRESS and item['filter'] == 'rst':
                item['content'] = item['content'].replace('\n ', '\n\n')
            f.write(item['content']+u'\n')

        entry = Entry(tmp, conf)
        p = join(conf['content_dir'], dirname(entry.permalink)[1:])

        try:
            os.makedirs(p.rsplit('/', 1)[0])
        except OSError:
            pass

        filepath = p + '.txt'
        if isfile(filepath) and not options.force:
            raise AcrylamidException('Entry already exists %r' % filepath)
        shutil.move(tmp, filepath)
        event.create('import', filepath)

    for item in items:

        if options.keep:
            m = urlsplit(item['link'])
            if m.path != '/':
                item['permalink'] = m.path

        item['content'], item['filter'] = convert(item.get('content', ''),
            options.fmt, options.pandoc)

        create(defaults, item)

    print("\nImport was successful. Edit your conf.py with these new settings:")
    for key, value in iteritems(defaults):
        if value is None:
            continue
        print("    %s = '%s'" % (key.upper(), value))


@task("import", arguments, "import content from URL or FILE")
def run(conf, env, options):
    """Subcommand: import -- import entries and settings from an existing RSS/Atom
    feed or WordPress dump.  ``acrylamid import http://example.com/feed/`` or any
    local FILE is fine.

    By default we use ``html2text`` (if available) to re-convert to Markdown, with
    ``-m rst`` you can also re-convert to reST if you have ``html2rest`` installed.
    As fallback there we have ``pandoc`` but you can use pandoc as first choice with
    the ``-p`` flag.

    If you don't like any reconversion, simply use ``-m html``. This command supports
    the force flag to override already existing files. Use with care!"""

    # we need the actual defaults values for permalink format
    commands.initialize(conf, env)

    content = fetch(options.src, auth=options.__dict__.get('auth', None))
    defaults, items = parse(content)
    build(conf, env, defaults, items, options)

########NEW FILE########
__FILENAME__ = info
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import print_function

import os
import datetime
import argparse

from math import ceil
from time import localtime, strftime
from os.path import join, getmtime, isfile

from acrylamid import readers, commands
from acrylamid.compat import iteritems, PY2K

from acrylamid.core import cache
from acrylamid.utils import batch, force_unicode as u
from acrylamid.tasks import task, argument
from acrylamid.colors import white, blue, green, normal
from acrylamid.views.tag import fetch

if PY2K:
    from itertools import izip_longest as izip
else:
    from itertools import zip_longest as izip


class Gitlike(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):

        namespace.max = 10 * namespace.max + int(option_string.strip('-'))


option = lambda i: argument('-%i' % i, action=Gitlike, help=argparse.SUPPRESS,
    nargs=0, dest="max", default=0)
arguments = [
    argument("type", nargs="?", type=str, choices=["summary", "tags"],
        default="summary", help="info about given type (default: summary)"),
    argument("--coverage", type=int, default=None, dest="coverage",
        metavar="N", help="discover posts with uncommon tags")
] + [option(i) for i in range(10)]


def ago(date, now=datetime.datetime.now()):

    delta = now - date

    secs = delta.seconds
    days = delta.days

    if days == 0:
        if secs < 10:
            return "just now"
        if secs < 60:
            return str(secs) + " seconds ago"
        if secs < 120:
            return  "a minute ago"
        if secs < 3600:
            return str(secs//60) + " minutes ago"
        if secs < 7200:
            return "an hour ago"
        if secs < 86400:
            return str(secs//3600) + " hours ago"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return str(days) + " days ago"
    if days < 31:
        return str(days//7) + " weeks ago"
    if days < 365:
        return str(days//30) + " months ago"

    return str(days//365) + " years ago"


def do_summary(conf, env, options):

    limit = options.max if options.max > 0 else 5
    entrylist, pages, translations, drafts = readers.load(conf)

    entrylist = sorted(entrylist + translations + drafts,
        key=lambda k: k.date, reverse=True)

    print()
    print('Acrylamid', blue(env['version']) + ',', end=' ')
    print('cache size:', blue('%0.2f' % (cache.size / 1024.0**2)) + ' mb')
    print()

    for entry in entrylist[:limit]:
        print('  ', green(ago(entry.date.replace(tzinfo=None)).ljust(13)), end=' ')
        print(white(entry.title) if entry.draft else normal(entry.title))

    print()
    print('%s published,' % blue(len([e for e in entrylist if not e.draft])), end=' ')
    print('%s drafted articles' % blue(len([e for e in entrylist if e.draft])))

    if not isfile(join(conf.get('cache_dir', '.cache/'), 'info')):
        return

    time = localtime(getmtime(join(conf.get('cache_dir', '.cache/'), 'info')))
    print('last compilation at %s' % blue(u(strftime(u'%d. %B %Y, %H:%M', time))))


# This function was written by Alex Martelli
# -- http://stackoverflow.com/questions/1396820/
def colprint(table, totwidth):
    """Print the table in terminal taking care of wrapping/alignment

    - `table`:    A table of strings. Elements must not be `None`
    """
    if not table:
        return
    numcols = max(len(row) for row in table)
    # ensure all rows have >= numcols columns, maybe empty
    padded = [row+numcols*('',) for row in table]
    # compute col widths, including separating space (except for last one)
    widths = [1 + max(len(x) for x in column) for column in zip(*padded)]
    widths[-1] -= 1
    # drop or truncate columns from the right in order to fit
    while sum(widths) > totwidth:
        mustlose = sum(widths) - totwidth
        if widths[-1] <= mustlose:
            del widths[-1]
        else:
            widths[-1] -= mustlose
            break
    # and finally, the output phase!
    for row in padded:
        s = ''.join(['%*s' % (-w, i[:w])
                     for w, i in zip(widths, row)])
        print(s.encode('utf-8'))

def do_tags(conf, env, options):

    limit = options.max if options.max > 0 else 100
    entrylist = readers.load(conf)[0]

    if options.coverage:
        for tag, entries in sorted(iteritems(fetch(entrylist))):
            if len(entries) <= options.coverage:
                print(blue(tag).encode('utf-8'), end=' ')
                print(', '.join(e.filename.encode('utf-8') for e in entries))
        return

    tags = ['%i %s' % (len(value), key) for key, value in
        sorted(iteritems(fetch(entrylist)), key=lambda k: len(k[1]), reverse=True)]

    colprint(
        list(izip(*list(batch(tags[:limit], ceil(len(tags)/4.0))), fillvalue='')),
        os.popen('stty size', 'r').read().split()[1]
    )


@task('info', arguments=arguments, help="short summary")
def run(conf, env, options):
    """Subcommand: info -- a short overview of a blog."""

    commands.initialize(conf, env)

    if options.type == "summary":
        do_summary(conf, env, options)
    elif options.type == "tags":
        do_tags(conf, env, options)

########NEW FILE########
__FILENAME__ = new
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import sys
import io
import os
import tempfile
import subprocess
import shutil
import shlex

from os.path import join, dirname, isfile, splitext
from datetime import datetime

from acrylamid import log, readers, commands
from acrylamid.errors import AcrylamidException
from acrylamid.compat import string_types

from acrylamid.tasks import task, argument
from acrylamid.utils import force_unicode as u
from acrylamid.helpers import safe, event

try:
    input = raw_input
except NameError:
    pass

yaml, rst, md = \
    lambda title, date: u"---\ntitle: %s\ndate: %s\n---\n\n" % (safe(title), date), \
    lambda title, date: u"%s\n" % title + "="*len(title) + '\n\n' + ":date: %s\n\n" % date, \
    lambda title, date: u"Title: %s\nDate: %s\n\n" % (title, date)

formats = {'.md': md, '.mkdown': md, '.rst': rst, '.rest': rst}


@task('new', [argument("title", nargs="*", default=None)], help="create a new entry")
def run(conf, env, options):
    """Subcommand: new -- create a new blog entry the easy way.  Either run
    ``acrylamid new My fresh new Entry`` or interactively via ``acrylamid new``
    and the file will be created using the preferred permalink format."""

    # we need the actual default values
    commands.initialize(conf, env)

    # config content_extension originally defined as string, not a list
    extlist = conf.get('content_extension',['.txt'])
    if isinstance(extlist, string_types):
        ext = extlist
    else:
        ext = extlist[0]

    fd, tmp = tempfile.mkstemp(suffix=ext, dir='.cache/')

    editor = os.getenv('VISUAL') if os.getenv('VISUAL') else os.getenv('EDITOR')
    tt = formats.get(ext, yaml)

    if options.title:
        title = u(' '.join(options.title))
    else:
        title = u(input("Entry's title: "))

    with io.open(fd, 'w', encoding='utf-8') as f:
        f.write(tt(title, datetime.now().strftime(conf['date_format'])))

    entry = readers.Entry(tmp, conf)
    p = join(conf['content_dir'], splitext(entry.permalink.strip('/'))[0])

    try:
        os.makedirs(p.rsplit('/', 1)[0])
    except OSError:
        pass

    filepath = p + ext
    if isfile(filepath):
        raise AcrylamidException('Entry already exists %r' % filepath)
    shutil.move(tmp, filepath)
    event.create('new', filepath)

    if datetime.now().hour == 23 and datetime.now().minute > 45:
        log.info("notice  don't forget to update entry.date-day after mignight!")

    if log.level() >= log.WARN:
        return

    try:
        if editor:
            retcode = subprocess.call(shlex.split(editor) + [filepath])
        elif sys.platform == 'darwin':
            retcode = subprocess.call(['open', filepath])
        else:
            retcode = subprocess.call(['xdg-open', filepath])
    except OSError:
        raise AcrylamidException('Could not launch an editor')

    # XXX process detaches... m(
    if retcode < 0:
        raise AcrylamidException('Child was terminated by signal %i' % -retcode)

    if os.stat(filepath)[6] == 0:
        raise AcrylamidException('File is empty!')

########NEW FILE########
__FILENAME__ = ping
# -*- encoding: utf-8 -*-
#
# Copyrights:
#    - PingBack: Иван Сагалаев (Ivan Sagalaew) <maniac@softwaremaniacs.org>
#    - Other: Martin Zimmermann <info@posativ.org>
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import print_function

import sys
import re
import os
import json

from textwrap import wrap

from acrylamid.tasks import task, argument
from acrylamid.errors import AcrylamidException
from acrylamid.compat import PY2K
from acrylamid.colors import blue, green, bold

from acrylamid import readers, commands, helpers, log
from acrylamid.tasks.info import option
from acrylamid.lib.requests import head, URLError, HTTPError
from acrylamid.lib.async import Threadpool

if PY2K:
    from urlparse import urlparse
    import xmlrpclib as xmlrpc
    setattr(xmlrpc, 'client', xmlrpc)
else:
    from urllib.parse import urlparse
    import xmlrpc.client

try:
    import twitter
except ImportError:
    twitter = None  # NOQA

arguments = [
    argument("service", nargs="?", type=str, choices=["twitter", "back"],
        default="back", help="ping service (default: back)"),

    argument("-a", "--all", dest="all", action="store_true", default=False,
        help="ping all entries (default: only the newest)"),
    argument("-p", dest="file", type=str, default=None, help="ping specific article"),

    argument("-n", "--dry-run", dest="dryrun", action='store_true',
             help="show what would have been pingbacked", default=False),
    argument("-j", "--jobs", dest="jobs", type=int, default=10, help="N parallel requests"),
] + [option(i) for i in range(10)]


def pingback(src, dest, dryrun=False):
    """Makes a pingback request to dest on behalf of src, i.e. effectively
    saying to dest that "the page at src is linking to you"."""

    def search_link(content):
        match = re.search(b'<link rel="pingback" href="([^"]+)" ?/?>', content)
        return match and match.group(1)

    try:
        r = head(dest)
    except (URLError, HTTPError) as e:
        return

    try:
        server_url = r.info().get('X-Pingback', '') or search_link(r.read(512 * 1024))
        if server_url:

            print("Pingback", blue(urlparse(server_url).netloc), end='')
            print("from", green(''.join(urlparse(src)[1:3])) + ".")

            if not dryrun:
                server = xmlrpc.client.ServerProxy(server_url)
                server.pingback.ping(src, dest)

    except xmlrpc.client.ProtocolError as e:
        raise AcrylamidException(e.args[0])


def tweet(entry, conf, dryrun=False):
    """Send a tweet with the title, link and tags from an entry. The first time you
    need to authorize Acrylamid but than it works without any interaction."""

    key = "6k00FRe6w4SZfqEzzzyZVA"
    secret = "fzRfQcqQX4gcZziyLeoI5wSbnFb7GGj2oEh10hnjPUo"

    creds = os.path.expanduser('~/.twitter_oauth')
    if not os.path.exists(creds):
        twitter.oauth_dance("Acrylamid", key, secret, creds)

    oauth_token, oauth_token_secret = twitter.read_token_file(creds)
    t = twitter.Twitter(auth=twitter.OAuth(oauth_token, oauth_token_secret, key, secret))

    tweet = u"New Blog Entry: {0} {1} {2}".format(entry.title,
        helpers.joinurl(conf['www_root'], entry.permalink),
        ' '.join([u'#' + helpers.safeslug(tag) for tag in entry.tags]))

    print('     ', bold(blue("tweet ")), end='')
    print('\n'.join(wrap(tweet.encode('utf8'), subsequent_indent=' '*13)))

    if not dryrun:
        try:
            t.statuses.update(status=tweet.encode('utf8'))
        except twitter.api.TwitterError as e:
            try:
                log.warn("%s" % json.loads(e.response_data)['error'])
            except (ValueError, TypeError):
                log.warn("Twitter: something went wrong...")


@task('ping', arguments, "notify resources")
def run(conf, env, options):
    """Subcommand: ping -- notify external resources via Pingback etc."""

    commands.initialize(conf, env)
    entrylist = [entry for entry in readers.load(conf)[0] if not entry.draft]

    if options.file:
        try:
            entrylist = [filter(lambda e: e.filename == options.file, entrylist)[0]]
        except IndexError:
            raise AcrylamidException("no such post!")

    if options.service == 'twitter':

        if twitter is None:
            raise AcrylamidException("'twitter' egg not found")

        for entry in entrylist if options.all else entrylist[:options.max or 1]:
            tweet(entry, conf, options.dryrun)

        return

    # XXX we should search for actual hrefs not random grepping, but this
    # requires access to the cache at non-runtime which is unfortunately
    # not possible yet.

    patterns = [
        r'(?<=\n)\[.*?\]:\s?(https?://.+)$',  # referenced markdown
        r'\[[^\]]+\]\((https?://[^\)]+)\)',  # inline markdown
        r'(?<=\n)\.\.\s+[^:]+:\s+(https?://.+)$',  # referenced docutils
        r'`[^<]+ <(https?://[^>]+)>`_',  # inline docutils
    ]

    pool = Threadpool(options.jobs)
    ping = lambda src, dest: pingback(helpers.joinurl(conf['www_root'], src), dest, options.dryrun)

    for entry in entrylist if options.all else entrylist[:options.max or 1]:

        for href in sum([re.findall(pat, entry.source, re.M) for pat in patterns], []):
            pool.add_task(ping, *[entry.permalink, href])

        try:
            pool.wait_completion()
        except KeyboardInterrupt:
            sys.exit(1)

########NEW FILE########
__FILENAME__ = jinja2
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import absolute_import

from io import StringIO
from os.path import getmtime
from collections import defaultdict

from jinja2 import Environment as J2Environemnt, FileSystemBytecodeCache
from jinja2 import FileSystemLoader, meta, nodes

from acrylamid.templates import AbstractEnvironment, AbstractTemplate

try:
    from acrylamid.assets.web import Mixin
except ImportError:
    from acrylamid.assets.fallback import Mixin


def unast(node):

    if isinstance(node, nodes.Const):
        return node.value
    elif isinstance(node, nodes.List):
        return [unast(item) for item in node.items]
    raise NotImplementedError(node)


def find_assets(ast):
    """Finds the {% for url in compile("foo.scss") %} syntax and yields
    the *args and **kwargs for Bundle(*args, **kwargs)."""

    for node in ast.find_all((nodes.Call, )):
        if isinstance(node.node, nodes.Name) and node.node.name == 'compile':
            yield [x.value for x in node.args], \
                dict((x.key, unast(x.value)) for x in node.kwargs)


class ExtendedFileSystemLoader(FileSystemLoader):

    def __init__(self, layoutdir):
        # remember already resolved templates -> modified state
        # TODO don't assume macros.html never changes
        self.modified = {'macros.html': False}

        # requested template -> parents as flat list
        self.resolved = defaultdict(set)

        # assets in the form of theme/base.html -> (*args, **kwargs)
        self.assets = defaultdict(list)

        super(ExtendedFileSystemLoader, self).__init__(layoutdir)

    def load(self, environment, name, globals=None):

        bcc = environment.bytecode_cache

        if globals is None:
            globals = {}

        deps = [name, ]
        while len(deps) > 0:

            child = deps.pop()
            if child in self.modified:
                continue

            source, filename, uptodate = self.get_source(environment, child)
            bucket = bcc.get_bucket(environment, child, filename, source)

            try:
                modified = getmtime(filename) > getmtime(bcc._get_cache_filename(bucket))
            except OSError:
                modified = True

            self.modified[child] = modified

            if modified:
                # updating cached template if timestamp has changed
                code = environment.compile(source, child, filename)
                bucket.code = code
                bcc.set_bucket(bucket)

            ast = environment.parse(source)
            for parent in meta.find_referenced_templates(ast):
                self.resolved[child].add(parent)
                deps.append(parent)

            for args, kwargs in find_assets(ast):
                self.assets[name].append((args, kwargs))

        source, filename, uptodate = self.get_source(environment, name)
        code = bcc.get_bucket(environment, name, filename, source).code

        if code is None:
            code = environment.compile(source, name, filename)

        tt = environment.template_class.from_code(environment, code,
                                                      globals, uptodate)
        return tt


class Environment(AbstractEnvironment):

    extension = ['.html', '.j2']
    loader = None

    def __init__(self, layoutdir, cachedir):

        self.templates = {}
        self.loader = ExtendedFileSystemLoader(layoutdir)

        self._jinja2 = J2Environemnt(
            loader=self.loader, bytecode_cache=FileSystemBytecodeCache(cachedir))

        # jinja2 is stupid and can't import any module during runtime
        import time, datetime, urllib

        for module in (time, datetime, urllib):
            self._jinja2.globals[module.__name__] = module

            for name in dir(module):
                if name.startswith('_'):
                    continue
                obj = getattr(module, name)
                if hasattr(obj, '__class__') and callable(obj):
                    self._jinja2.filters[module.__name__ + '.' + name] = obj

    def register(self, name, func):
        self._jinja2.globals[name] = func
        self._jinja2.filters[name] = func

    def fromfile(self, env, path):
        return self.templates.setdefault(path,
            Template(env, path, self._jinja2.get_template(path)))

    def extend(self, path):
        self.loader.searchpath.append(path)


class Template(AbstractTemplate, Mixin):

    def render(self, **kw):
        buf = StringIO()
        self.template.stream(**kw).dump(buf)
        return buf

########NEW FILE########
__FILENAME__ = mako
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Moritz Schlarb <mail@moritz-schlarb.de>. All rights reserved.
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from __future__ import absolute_import

import os
import io
import re
import ast
import posixpath

from os.path import getmtime, isfile
from itertools import chain
from collections import defaultdict

from acrylamid.templates import AbstractEnvironment, AbstractTemplate
from mako.lookup import TemplateLookup
from mako import exceptions, runtime

try:
    from acrylamid.assets.web import Mixin
except ImportError:
    from acrylamid.assets.fallback import Mixin


class CallVisitor(ast.NodeVisitor):

    def __init__(self, callback):
        self.callback = callback
        super(CallVisitor, self).__init__()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.callback(node)


def unast(node):
    if isinstance(node, ast.Str):
        return node.s
    elif isinstance(node, ast.List):
        return [unast(item) for item in node.elts]
    raise NotImplementedError(node)


def find_assets(tt):
    """
    Parse AST from Mako template and yield *args, **kwargs from any
    `compile` call.
    """
    rv = []

    def collect(node):
        if node.func.id != "compile":
            return

        args = list(unast(x) for x in node.args)
        kwargs = dict((x.arg, unast(x.value)) for x in node.keywords)

        rv.append((args, kwargs))

    CallVisitor(collect).visit(ast.parse(tt.code))

    for args, kwargs in rv:
        yield args, kwargs


class ExtendedLookup(TemplateLookup):
    """
    Custom Mako template lookup that records dependencies, mtime and referenced
    web assets.
    """

    inherits = re.compile(r'<%inherit file="([^"]+)" />')
    includes = re.compile(r'<%namespace file="([^"]+)" import="[^"]+" />')

    def __init__(self, *args, **kwargs):
        # remember already resolved templates -> modified state
        # TODO don't assume macros.html never changes
        self.modified = {'macros.html': False}

        # requested template -> parents as flat list
        self.resolved = defaultdict(set)

        # assets in the form of theme/base.html -> (*args, **kwargs)
        self.assets = defaultdict(list)
        
        super(ExtendedLookup, self).__init__(*args, **kwargs)

    def get_template(self, uri):
        """This is stolen and truncated from mako.lookup:TemplateLookup."""

        u = re.sub(r'^/+', '', uri)
        for dir in self.directories:
            filename = posixpath.normpath(posixpath.join(dir, u))
            if os.path.isfile(filename):
                return self._load(filename, uri)
        else:
            raise exceptions.TopLevelLookupException(
                                "Cant locate template for uri %r" % uri)

    def _load(self, filename, uri):

        deps = [uri, ]
        while len(deps) > 0:

            child = deps.pop()
            if child in self.modified:
                continue

            for directory in self.directories:
                filename = posixpath.normpath(posixpath.join(directory, child))
                if isfile(filename):
                    break

            p = self.modulename_callable(filename, child)

            try:
                modified = getmtime(filename) > getmtime(p)
            except OSError:
                modified = True

            self.modified[child] = modified

            with io.open(filename, encoding='utf-8') as fp:
                source = fp.read()

            parents = chain(self.inherits.finditer(source), self.includes.finditer(source))
            for match in parents:
                self.resolved[child].add(match.group(1))
                deps.append(match.group(1))

            # TODO: definitely an ugly way (= side effect) to get the byte code
            tt = super(ExtendedLookup, self)._load(filename, child)
            for args, kwargs in find_assets(tt):
                self.assets[uri].append((args, kwargs))

        # already cached due side effect above
        return self._collection[uri]


class Environment(AbstractEnvironment):

    extension = ['.html', '.mako']

    def __init__(self, layoutdir, cachedir):
        self._mako = ExtendedLookup(
            directories=[layoutdir],
            module_directory=cachedir,
            # similar to mako.template.Template.__init__ but with
            # leading cache_ for the acrylamid cache
            modulename_callable=lambda filename, uri:\
                os.path.join(os.path.abspath(cachedir), 'cache_' +
                    os.path.normpath(uri.lstrip('/')) + '.py'),
            input_encoding='utf-8')

        self.filters = {}

    def register(self, name, func):
        self.filters[name] = func

    def fromfile(self, env, path):
        return Template(env, path, self._mako.get_template(path))

    def extend(self, path):
        self._mako.directories.append(path)

    @property
    def loader(self):
        return self._mako


class Template(AbstractTemplate, Mixin):

    def render(self, **kw):
        # we inject the filter functions as top-level objects into the template,
        # that's probably the only way that works with Mako
        kw.update(self.engine.filters)
        buf = io.StringIO()
        ctx = runtime.Context(buf, **kw)
        self.template.render_context(ctx)
        return buf
        # For debugging template compilation:
        # TODO: Integrate this with acrylamid somehow
        #from mako import exceptions as mako_exceptions
        #try:
        #    return self.template.render(**kw)
        #except:
        #    print mako_exceptions.text_error_template().render()
        #    return unicode(mako_exceptions.html_error_template().render())

########NEW FILE########
__FILENAME__ = utils
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.
#
# Utilities that do not depend on any further Acrylamid object

from __future__ import unicode_literals

import sys
import os
import io
import zlib
import locale
import functools
import itertools

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

try:
    import magic
except ImportError as e:
    if e.args[0].find('libmagic') > -1:
        raise
    magic = None

from acrylamid.compat import PY2K, string_types, map, filter, iteritems


def hash(*objs, **kw):

    # start with 0?
    rv = kw.get('start', 0)

    for obj in objs:
        if isinstance(obj, string_types):
            rv = zlib.crc32(obj.encode('utf-8'), rv)
        else:
            if isinstance(obj, tuple):
                hv = hash(*obj, start=rv)
            else:
                hv = obj.__hash__()

            rv = zlib.crc32(repr(hv).encode('utf-8'), rv)

    return rv & 0xffffffff


def rchop(original_string, substring):
    """Return the given string after chopping of a substring from the end.

    :param original_string: the original string
    :param substring: the substring to chop from the end
    """
    if original_string.endswith(substring):
        return original_string[:-len(substring)]
    return original_string


def lchop(string, prefix):
    """Return the given string after chopping the prefix from the begin.

    :param string: the original string
    :oaram prefix: prefix to chop of
    """

    if string.startswith(prefix):
        return string[len(prefix):]
    return string


if sys.version_info[0] == 2:
    def force_unicode(string):  # This function can be removed with Python 3

        if isinstance(string, unicode):
            return string

        try:
            return string.decode('utf-8')
        except UnicodeDecodeError:
            return string.decode(locale.getpreferredencoding())
else:
    force_unicode = lambda x: x


def total_seconds(td):  # timedelta.total_seconds, required for 2.6
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6


class cached_property(object):
    """A property that is only computed once per instance and then replaces
    itself with an ordinary attribute. Deleting the attribute resets the
    property.

    Copyright (c) 2012, Marcel Hellkamp. License: MIT."""

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class classproperty(property):
    # via http://stackoverflow.com/a/1383402
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class memoized(object):
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated)."""

    def __init__(self, func):
        self.func = func
        self.cache = {}
        self.__doc__ = func.__doc__

    def __call__(self, *args):
        try:
            return self.cache[args]
        except KeyError:
            value = self.func(*args)
            self.cache[args] = value
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)

    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)


def find(fname, directory):
    """Find `fname` in `directory`, if not found try the parent folder until
    we find `fname` (as full path) or raise an :class:`IOError`."""

    directory = directory.rstrip('/')

    while directory:
        try:
            return os.path.join(directory, next(filter(
                lambda p: p == fname, os.listdir(directory))))
        except (OSError, StopIteration):
            directory = directory.rsplit('/', 1)[0]
    else:
        raise IOError


def execfile(path, ns):
    """Python 2 and 3 compatible way to execute a file into a namespace."""
    with io.open(path, 'rb') as fp:
        exec(fp.read(), ns)


def batch(iterable, count):
    """batch a list to N items per slice"""
    result = []
    for item in iterable:
        if len(result) == count:
            yield result
            result = []
        result.append(item)
    if result:
        yield result


def groupby(iterable, keyfunc=lambda x: x):
    """:func:`itertools.groupby` wrapper for :func:`neighborhood`."""
    for k, g in itertools.groupby(iterable, keyfunc):
        yield k, list(g)


def neighborhood(iterable, prev=None):
    """yield previous and next values while iterating"""
    iterator = iter(iterable)
    item = next(iterator)
    for new in iterator:
        yield (prev, item, new)
        prev, item = item, new
    yield (prev, item, None)


class Metadata(dict):
    """A nested :class:`dict` used for post metadata."""

    def __init__(self, dikt={}):
        super(Metadata, self).__init__(self)
        self.update(dict(dikt))


    def __setitem__(self, key, value):
        try:
            key, other = key.split('.', 1)
            self.setdefault(key, Metadata())[other] = value
        except ValueError:
            super(Metadata, self).__setitem__(key, value)

    def __getattr__(self, attr):
        return self[attr]

    def update(self, dikt):
        for key, value in iteritems(dikt):
            self[key] = value

    def redirect(self, old, new):

        self[new] = self[old]
        del self[old]


def import_object(name):
    if '.' not in name:
        return __import__(name)

    parts = name.split('.')
    obj = __import__('.'.join(parts[:-1]), None, None, [parts[-1]], 0)
    return getattr(obj, parts[-1])


class Struct(OrderedDict):
    """A dictionary that provides attribute-style access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super(Struct, self).__setattr__(key, value)
        else:
            self[key] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash(*itertools.chain(self.keys(), self.values()))


class HashableList(list):

    def __hash__(self):
        return hash(*self)

########NEW FILE########
__FILENAME__ = archive
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from os.path import isfile

from acrylamid.utils import neighborhood, groupby
from acrylamid.views import View
from acrylamid.helpers import union, joinurl, event, expand, memoize, hash, link
from acrylamid.readers import Date


class Day(object):

    def __init__(self, name, items=[]):
        self.name = name
        self.items = items

    @property
    def abbr(self):
        return Date(2001, 1, self.name).strftime('%a')

    @property
    def full(self):
        return Date(2001, 1, self.name).strftime('%A')

    def __str__(self):
        return '%02i' % self.name


class Month(Day):

    yields = Day
    keyfunc = lambda self, d: d.iday

    def __iter__(self):
        for k, group in groupby(self.items, self.keyfunc):
            yield self.yields(k, list(group))

    def __len__(self):
        return len(self.items)

    @property
    def abbr(self):
        return Date(2001, self.name, 1).strftime('%b')

    @property
    def full(self):
        return Date(2001, self.name, 1).strftime('%B')


class Year(Month):

    yields = Month
    keyfunc = lambda self, m: m.imonth


class Archive(View):
    """A view that lists all posts per year/month/day -- usually found in
    WordPress blogs. Configuration syntax:

    .. code-block:: python

        '/:year/': {'view': 'archive'},
        '/:year/:month/': {'view': 'archive'},
        '/:year/:month/:day/': {'view': 'archive'}

    During templating you can access the current archive year/month/day via
    ``env.archive`` which basically holds the year, month and day, although
    the latter two may be ``None`` in case of a route without month or day.
    To determine the current archive name, you can use the following snippet:

    .. code-block:: html+jinja

        {% set archivesname = env.archive.year
                            ~ (('/' ~ env.archive.month) if env.archive.month else '')
                            ~ (('/' ~ env.archive.day) if env.archive.day else '')  %}


    Rendering a list of entries is the same like in other views:

    .. code-block:: html+jinja

        {% for entry in env.entrylist %}
        <a href="{{ entry.permalink }}">{{ entry.title | e }}</a>
        {% endfor %}

    To link to the archive pages, you can either link the entry date as there
    is at least one entry in that timerange: the entry itself. But you can also
    generate a complete archive listing as you may know from WordPress. This
    does only includes years, months and/or days where you have at least a
    single post.

    .. code-block:: html+jinja

        {% for year in env.globals.entrylist | archivesfor %}
        <h2>{{ year ~ ' (' ~ year | count ~ ')' }}</h2>
        <ul>
            {% for month in year %}
            <li>
                <a href="{{ env.path ~ '/' ~ year ~ '/' ~ month ~ '/'  }}">{{ month.full }}</a>
                ({{  month | count }})
            </li>
            {% endfor %}
        </ul>
        {% endfor %}

    This generates a listing that shows the amount of postings during the
    period. You can also iterate over each month to get to the days.
    :class:`Year`, :class:`Month` and :class:`Day` objects always evaluate to
    a zero-padded date unit such as 2012 (year) or 01 (January). In addition,
    Month and Day objects have ``full`` and ``abbr`` attributes to access the
    fullname or abbreviation in your current location.

    You can retrieve the posts from the :class:`Year`, :class:`Month` and
    :class:`Day` via the ``.items`` attribute.

    .. code-block:: html+jinja

        {% for year in env.globals.entrylist | archivesfor %}
            <h2>{{ year ~ ' (' ~ year | count ~ ')' }}</h2>
            {% for entry in year.items %}
                <a href="{{ entry.permalink }}">{{ entry.title }}</a>
            {% endfor %}
        {% endfor %}
    """

    priority = 80.0

    def init(self, conf, env, template='listing.html'):
        self.template = template

    def context(self, conf, env, data):

        env.engine.register('archivesfor', lambda entrylist:
            [Year(k, list(group)) for k, group in groupby(entrylist, lambda e: e.year)])

        return env

    def generate(self, conf, env, data):

        tt = env.engine.fromfile(env, self.template)
        keyfunc = lambda k: ( )

        if '/:year' in self.path:
            keyfunc = lambda k: (k.year, )
        if '/:month' in self.path:
            keyfunc = lambda k: (k.year, k.imonth)
        if '/:day' in self.path:
            keyfunc = lambda k: (k.year, k.imonth, k.iday)

        for next, curr, prev in neighborhood(groupby(data['entrylist'], keyfunc)):

            salt, group = '-'.join(str(i) for i in curr[0]), list(curr[1])
            modified = memoize('archive-' + salt, hash(*group)) or any(e.modified for e in group)

            if prev:
                prev = link(u'/'.join('%02i' % i for i in prev[0]), expand(self.path, prev[1][0]))
            if next:
                next = link(u'/'.join('%02i' % i for i in next[0]), expand(self.path, next[1][0]))

            route = expand(self.path, group[0])
            path = joinurl(conf['output_dir'], route)

            # an object storing year, zero-padded month and day as attributes (may be None)
            key = type('Archive', (object, ), dict(zip(('year', 'month', 'day'),
                map(lambda x: '%02i' % x if x else None, keyfunc(group[0]))
            )))()

            if isfile(path) and not (modified or tt.modified or env.modified or conf.modified):
                event.skip('archive', path)
                continue

            html = tt.render(conf=conf, env=union(env, entrylist=group,
                type='archive', prev=prev, curr=link(route), next=next,
                num_entries=len(group), route=route, archive=key))

            yield html, path

########NEW FILE########
__FILENAME__ = articles
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid.views import View
from acrylamid.helpers import union, joinurl, event

from os.path import exists


class Articles(View):
    """Generates an overview of all articles using *layouts/articles.html* as
    default jinja2 template (`Example <http://blog.posativ.org/articles/>`_).

    To enable Articles view, add:

    .. code-block:: python

        '/articles/' : {
            'view': 'articles',
            'template': 'articles.html'  # default
        }

    to your :doc:`conf.py` where */articles/* is the default URL for this view.

    We filter articles that are drafts and add them to the *articles*
    dictionary using ``(entry.year, entry.imonth)`` as key. During templating
    we sort all keys by value, hence we get a listing of years > months > entries.

    Variables available during Templating:

    - *articles* containing the articles
    - *num_entries* count of articles
    - *conf*, *env*"""

    priority = 80.0

    def init(self, conf, env, template='articles.html'):
        self.template = template

    def generate(self, conf, env, data):

        entrylist = data['entrylist']

        tt = env.engine.fromfile(env, self.template)
        path = joinurl(conf['output_dir'], self.path, 'index.html')

        if exists(path) and not (conf.modified or env.modified or tt.modified):
            event.skip('article', path)
            raise StopIteration

        articles = {}
        for entry in entrylist:
            articles.setdefault((entry.year, entry.imonth), []).append(entry)

        html = tt.render(conf=conf, articles=articles, env=union(env,
                         num_entries=len(entrylist), route=self.path))
        yield html, path

########NEW FILE########
__FILENAME__ = category
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from itertools import chain

from acrylamid.views.index import Index, Paginator
from acrylamid.compat import itervalues, iteritems
from acrylamid.helpers import expand, safeslug


def fetch(tree):
    """fetch all posts from the tree"""

    for item in tree[1]:
        yield item

    for subtree in itervalues(tree[0]):
        for item in fetch(subtree):
            yield item


def recurse(category, tree):

    yield category, sorted(list(fetch(tree)), key=lambda k: k.date, reverse=True)

    for subtree in iteritems(tree[0]):
        for item in recurse(category + '/' + safeslug(subtree[0]), subtree[1]):
            yield item


class Top(object):
    """Top-level category node without a category at all.  Iterable and yields
    sub categories that are also iterable up to the very last sub category."""

    def __init__(self, tree, route):
        self.tree = tree
        self.route = route
        self.parent = []

    def __iter__(self):
        for category, subtree in sorted(iteritems(self.tree[0]), key=lambda k: k[0]):
            yield Subcategory(self.parent + [category], category, subtree, self.route)

    def __bool__(self):
        return len(self) > 0

    @property
    def items(self):
        return list(fetch(self.tree))

    @property
    def href(self):
        return expand(self.route, {'name': ''})


class Subcategory(Top):

    def __init__(self, parent, category, tree, route):
        self.parent = parent
        self.title = category
        self.tree = tree
        self.route = route

    def __str__(self):
        return self.title

    @property
    def href(self):
        return expand(self.route, {'name': '/'.join(map(safeslug, self.parent))})


class Category(Index):

    export = ['prev', 'curr', 'next', 'items_per_page', 'category', 'entrylist']
    template = 'main.html'

    def context(self, conf, env, data):

        self.tree = ({}, [])

        for entry in data['entrylist']:
            node = self.tree

            for i, category in enumerate(entry.category):

                if i < len(entry.category) - 1:
                    if category in node:
                        node = node[category]
                    else:
                        node = node[0].setdefault(category, ({}, []))
                else:
                    node[0].setdefault(category, ({}, []))[1].append(entry)

        class Link:

            def __init__(self, title, href):
                self.title = title
                self.href = href if href.endswith('/') else href + '/'

        def categorize(category):
            for i, name in enumerate(category):
                rv = '/'.join(category[:i] + [name])
                yield Link(rv, expand(self.path, {'name': rv}))

        env.engine.register('categorize', categorize)
        env.categories = Top(self.tree, self.path)
        return env

    def generate(self, conf,env, data):

        iterator = chain(*map(lambda args: recurse(*args), iteritems(self.tree[0])))

        for category, entrylist in iterator:
            data['entrylist'] = entrylist
            for res in Paginator.generate(self, conf, env, data,
                                          category=category, name=category):
                yield res

########NEW FILE########
__FILENAME__ = entry
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import os
import abc
import io

from os.path import isfile, dirname, basename, getmtime, join
from collections import defaultdict

from acrylamid import refs, log
from acrylamid.errors import AcrylamidException
from acrylamid.compat import metaclass, filter
from acrylamid.helpers import expand, union, joinurl, event, link, mkfile

from acrylamid.refs import modified, references
from acrylamid.views import View


class Base(metaclass(abc.ABCMeta, View)):

    priority = 75.0

    @abc.abstractproperty
    def type(self):
        return None

    def init(self, conf, env, template='main.html'):
        self.template = template

    def next(self, entrylist, i):
        return None

    def prev(self, entrylist, i):
        return None

    def generate(self, conf, env, data):

        pathes, entrylist = set(), data[self.type]
        unmodified = not env.modified and not conf.modified

        for i, entry in enumerate(entrylist):

            if entry.hasproperty('permalink'):
                path = joinurl(conf['output_dir'], entry.permalink)
            else:
                path = joinurl(conf['output_dir'], expand(self.path, entry))

            if isfile(path) and path in pathes:
                try:
                    os.remove(path)
                finally:
                    other = [e.filename for e in entrylist
                        if e is not entry and e.permalink == entry.permalink][0]
                    log.error("title collision %s caused by %s and %s",
                              entry.permalink, entry.filename, other)
                    raise SystemExit

            pathes.add(path)
            next, prev = self.next(entrylist, i), self.prev(entrylist, i)

            # per-entry template
            tt = env.engine.fromfile(env, entry.props.get('layout', self.template))

            if all([isfile(path), unmodified, not tt.modified, not entry.modified,
            not modified(*references(entry))]):
                event.skip(self.name, path)
            else:
                html = tt.render(conf=conf, entry=entry, env=union(env,
                                 entrylist=[entry], type=self.__class__.__name__.lower(),
                                 prev=prev, next=next, route=expand(self.path, entry)))
                yield html, path

            # check if any resources need to be moved
            if entry.hasproperty('copy'):
                for res_src in entry.resources:
                    res_dest = join(dirname(path), basename(res_src))
                    # Note, presence of res_src check in FileReader.getresources
                    if isfile(res_dest) and getmtime(res_dest) > getmtime(res_src):
                        event.skip(self.name, res_dest)
                        continue
                    try:
                        fp = io.open(res_src, 'rb')
                        # use mkfile rather than yield so different ns can be specified (and filtered by sitemap)
                        mkfile(fp, res_dest, ns='resource', force=env.options.force, dryrun=env.options.dryrun)
                    except IOError as e:
                        log.warn("Failed to copy resource '%s' whilst processing '%s' (%s)" % (res_src, entry.filename, e.strerror))


class Entry(Base):

    @property
    def type(self):
        return 'entrylist'

    def next(self, entrylist, i):

        if i == 0:
            return None

        refs.append(entrylist[i], entrylist[i - 1])
        return link(entrylist[i-1].title, entrylist[i-1].permalink)

    def prev(self, entrylist, i):

        if i == len(entrylist) - 1:
            return None

        refs.append(entrylist[i], entrylist[i + 1])
        return link(entrylist[i+1].title, entrylist[i+1].permalink)


class Page(Base):

    @property
    def type(self):
        return 'pages'


class Translation(Base):

    @property
    def type(self):
        return 'translations'

    def context(self, conf, env, data):

        translations = defaultdict(list)
        for entry in data['entrylist'][:]:

            if entry.hasproperty('identifier'):
                translations[entry.identifier].append(entry)

                if entry.lang != conf.lang:
                    entry.props['entry_permalink'] = self.path

                    # remove from original entrylist
                    data['entrylist'].remove(entry)
                    data['translations'].append(entry)

        @refs.track
        def translationsfor(entry):

            try:
                entries = translations[entry.identifier]
            except (KeyError, AttributeError):
                raise StopIteration

            for translation in entries:
                if translation != entry:
                    yield translation

        env.translationsfor = translationsfor

        return env


class Draft(Base):
    """Create an drafted post that is not linked by the articles overview or
    regular posts."""

    @property
    def type(self):
        return 'drafts'

########NEW FILE########
__FILENAME__ = feeds
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from os.path import isfile
from datetime import datetime, timedelta
from wsgiref.handlers import format_date_time

from acrylamid.utils import HashableList, total_seconds
from acrylamid.views import View, tag
from acrylamid.compat import text_type as str
from acrylamid.helpers import joinurl, event, expand, union
from acrylamid.readers import Timezone

epoch = datetime.utcfromtimestamp(0).replace(tzinfo=Timezone(0))


def utc(dt, fmt='%Y-%m-%dT%H:%M:%SZ'):
    """return date pre-formated as UTC timestamp.
    """
    return (dt - (dt.utcoffset() or timedelta())).strftime(fmt)


class Feed(View):
    """Atom and RSS feed generation.  The feeds module provides several classes
    to generate feeds:

      - RSS -- RSS feed for all entries
      - Atom  -- same for Atom
      - RSSPerTag -- RSS feed for all entries for a given tag
      - AtomPerTag -- same for Atom

    All feed views have a ``num_entries`` argument that defaults to 25 and
    limits the list of posts to the 25 latest ones. In addition RSSPerTag and
    AtomPerTag expand ``:name`` to the current tag in your route.

    Examples:

    .. code-block:: python

        # per tag Atom feed
        '/tag/:name/feed/': {'filters': ..., 'view': 'atompertag'}

        # full Atom feed
        '/atom/full/': {'filters': ..., 'view': 'atom', 'num_entries': 1000}
    """

    priority = 25.0

    def init(self, conf, env):
        self.filters.append('absolute')
        self.route = self.path

    def context(self, conf, env, data):
        env.engine.register('utc', utc)
        return env

    def generate(self, conf, env, data):
        entrylist = data['entrylist']
        entrylist = list(entrylist)[0:self.num_entries]
        tt = env.engine.fromfile(env, '%s.xml' % self.type)

        path = joinurl(conf['output_dir'], self.route)
        modified = any(entry.modified for entry in entrylist)

        if isfile(path) and not (conf.modified or env.modified or tt.modified or modified):
            event.skip(self.name, path)
            raise StopIteration

        updated = entrylist[0].date if entrylist \
            else datetime.utcnow().replace(tzinfo=conf.tzinfo)
        html = tt.render(conf=conf, env=union(env, route=self.route,
                         updated=updated, entrylist=entrylist))
        yield html, path


class FeedPerTag(tag.Tag, Feed):

    def context(self, conf, env, data):
        self.populate_tags(data)

        return env

    def generate(self, conf, env, data):

        for tag in self.tags:

            entrylist = HashableList(entry for entry in self.tags[tag])
            new_data = data
            new_data['entrylist'] = entrylist
            self.route = expand(self.path, {'name': tag})
            for html, path in Feed.generate(self, conf, env, new_data):
                yield html, path


class Atom(Feed):

    def init(self, conf, env, num_entries=25):
        super(Atom, self).init(conf, env)

        self.num_entries = num_entries
        self.type = 'atom'


class RSS(Feed):

    def init(self, conf, env, num_entries=25):
        super(RSS, self).init(conf, env)

        self.num_entries = num_entries
        env.engine.register(
            'rfc822', lambda dt: str(format_date_time(total_seconds(dt - epoch))))
        self.type = 'rss'


class AtomPerTag(FeedPerTag):

    def init(self, conf, env, num_entries=25):
        super(AtomPerTag, self).init(conf, env)

        self.num_entries = num_entries
        self.type = 'atom'


class RssPerTag(FeedPerTag):

    def init(self, conf, env, num_entries=25):
        super(RssPerTag, self).init(conf, env)

        self.num_entries = num_entries
        env.engine.register(
            'rfc822', lambda dt: str(format_date_time(total_seconds(dt - epoch))))
        self.type = 'rss'

########NEW FILE########
__FILENAME__ = index
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

from acrylamid.views import View, Paginator


class Index(View, Paginator):
    """Creates nicely paged listing of your posts. First page renders to ``route``
    (defaults to */*) with a recent list of your (e.g. summarized) articles. Other
    pages enumerate to the variable ``pagination`` (*/page/:num/* per default).

    .. code-block:: python

        '/' : {
            'view': 'index',
            'template': 'main.html',
            'pagination': '/page/:num/',
            'items_per_page': 10
        }
    """

    export = ['prev', 'curr', 'next', 'items_per_page', 'entrylist']
    template = 'main.html'

    def init(self, *args, **kwargs):
        View.init(self, *args, **kwargs)
        Paginator.init(self, *args, **kwargs)
        self.filters.append('relative')

########NEW FILE########
__FILENAME__ = sitemap
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import io

from time import strftime, gmtime
from os.path import getmtime, exists, splitext, basename
from xml.sax.saxutils import escape

from acrylamid.views import View
from acrylamid.compat import PY2K
from acrylamid.helpers import event, joinurl, rchop

if PY2K:
    from urlparse import urljoin
else:
    from urllib.parse import urljoin


class Map(io.StringIO):
    """A simple Sitemap generator."""

    def __init__(self, *args, **kw):

        io.StringIO.__init__(self)
        self.write(u"<?xml version='1.0' encoding='UTF-8'?>\n")
        self.write(u'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n')
        self.write(u'        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n')

    def add(self, url, lastmod, changefreq='never', priority=0.5, images=None):

        self.write(u'  <url>\n')
        self.write(u'    <loc>%s</loc>\n' % escape(url))
        self.write(u'    <lastmod>%s</lastmod>\n' % strftime('%Y-%m-%d', gmtime(lastmod)))
        if changefreq:
            self.write(u'    <changefreq>%s</changefreq>\n' % changefreq)
        if priority != 0.5:
            self.write(u'    <priority>%.1f</priority>\n' % priority)
        for img in images or []:
            self.write(u'    <image:image>\n')
            self.write(u'        <image:loc>%s</image:loc>\n' %  escape(urljoin(url, basename(img))))
            self.write(u'    </image:image>\n')

        self.write(u'  </url>\n')

    def finish(self):
        self.write(u'</urlset>')


class Sitemap(View):

    priority = 0.0
    scores = {'page': (1.0, 'never'), 'entry': (1.0, 'never')}

    def init(self, conf, env):

        def track(ns, path):
            if ns != 'resource':
                self.files.add((ns, path))
            elif self.resext and splitext(path)[1] in self.resext:
                self.files.add((ns, path))

        def changed(ns, path):
            if not self.modified:
                self.modified = True

        self.files = set([])
        self.modified = False

        # use extension to check if resource should be tracked (keep image, video and other resources separate)
        self.resext = conf.get('sitemap_resource_ext', [])
        self.imgext = conf.get('sitemap_image_ext', [])
        # video resources require more attributes (image, description)
        # see http://support.google.com/webmasters/bin/answer.py?hl=en&answer=183668
        #self.vidext = conf.get('sitemap_video_ext', [])

        # track output files
        event.register(track, to=['create', 'update', 'skip', 'identical'])
        event.register(changed, to=['create', 'update'])

    def context(self, conf, env, data):
        """If resources are included in sitemap, create a map for each entry and its
        resources, so they can be include in <url>"""

        if self.imgext:
            self.mapping = dict([(entry.permalink, entry.resources)
                for entry in data['entrylist']])

        return env

    def generate(self, conf, env, data):
        """In this step, we filter drafted entries (they should not be included into the
        Sitemap) and write the pre-defined priorities to the map."""

        path = joinurl(conf['output_dir'], self.path)
        sm = Map()

        if exists(path) and not self.modified and not conf.modified:
            event.skip('sitemap', path)
            raise StopIteration

        for ns, fname in self.files:

            if ns == 'draft':
                continue

            permalink = '/' + fname.replace(conf['output_dir'], '')
            permalink = rchop(permalink, 'index.html')
            url = conf['www_root'] + permalink
            priority, changefreq = self.scores.get(ns, (0.5, 'weekly'))
            if self.imgext:
                images = [x for x in self.mapping.get(permalink, []) if splitext(x)[1].lower() in self.imgext]
                sm.add(url, getmtime(fname), changefreq, priority, images)
            else:
                sm.add(url, getmtime(fname), changefreq, priority)
        sm.finish()
        yield sm, path

########NEW FILE########
__FILENAME__ = tag
# -*- encoding: utf-8 -*-
#
# Copyright 2012 Martin Zimmermann <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses -- see LICENSE.

import math
import random

from collections import defaultdict

from acrylamid.compat import iteritems
from acrylamid.helpers import expand, safeslug, hash
from acrylamid.views.index import Index, Paginator


def fetch(entrylist):
    """Fetch tags from list of entries and map tags to most common tag name
    """
    tags = defaultdict(list)
    tmap = defaultdict(int)

    for e in entrylist:
        for tag in e.tags:
            tags[tag.lower()].append(e)
            tmap[tag] += 1

    # map tags to the most counted tag name
    for name in list(tags.keys()):
        key = max([(tmap[key], key) for key in tmap
                   if key.lower() == name])[1]
        rv = tags.pop(key.lower())
        tags[key] = rv

    return tags


class Tagcloud(object):
    """Tagcloud helper class similar (almost identical) to pelican's tagcloud helper object.
    Takes a bunch of tags and produces a logarithm-based partition and returns a iterable
    object yielding a Tag-object with two attributes: name and step where step is the
    calculated step size (== font size) and reaches from 0 to steps-1.

    :param tags: a dictionary of tags, e.g. {'name', [list of entries]}
    :param steps: maximum steps
    :param max_items: maximum items shown in tagcloud
    :param start: start index of steps resulting in start to steps+start-1 steps."""

    def __init__(self, tags, steps=4, max_items=100, start=0, shuffle=False):

        lst = sorted([(k, len(v)) for k, v in iteritems(tags)],
            key=lambda x: x[0])[:max_items]
        # stolen from pelican/generators.py:286
        max_count = max(lst, key=lambda k: k[1])[1] if lst else None
        self.lst = [(tag, count, 
                        int(math.floor(steps - (steps - 1) * math.log(count)
                            / (math.log(max_count) or 1)))+start-1)
                    for tag, count in lst]

        if shuffle:
            random.shuffle(self.lst)

        self.tags = tags

    def __iter__(self):
        for tag, count, step in self.lst:
            yield type('Tag', (), {'name': tag, 'step': step, 'count': count})

    def __hash__(self):
        return hash(*self.lst)

    def __getitem__(self, tag):
        return self.tags[tag.name]


class Tag(Index):
    """Same behaviour like Index except ``route`` that defaults to */tag/:name/* and
    ``pagination`` that defaults to */tag/:name/:num/* where :name is the current
    tag identifier.

    To create a tag cloud head over to :doc:`conf.py`.
    """

    export = ['prev', 'curr', 'next', 'items_per_page', 'tag', 'entrylist']
    template = 'main.html'

    def populate_tags(self, request):

        tags = fetch(request['entrylist'])
        self.tags = tags
        return tags

    def context(self, conf, env, request):

        class Link:

            def __init__(self, title, href):
                self.title = title
                self.href = href

        def tagify(tags):
            href = lambda t: expand(self.path, {'name': safeslug(t)})
            return [Link(t, href(t)) for t in tags] if isinstance(tags, (list, tuple)) \
                else Link(tags, href(tags))

        tags = self.populate_tags(request)
        env.engine.register('tagify', tagify)
        env.tag_cloud = Tagcloud(tags, conf['tag_cloud_steps'],
                                       conf['tag_cloud_max_items'],
                                       conf['tag_cloud_start_index'],
                                       conf['tag_cloud_shuffle'])

        return env

    def generate(self, conf, env, data):
        """Creates paged listing by tag."""

        for tag in self.tags:

            data['entrylist'] = [entry for entry in self.tags[tag]]
            for res in Paginator.generate(self, conf, env, data, tag=tag, name=safeslug(tag)):
                yield res

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import sys
import os
import datetime
import pkg_resources

from distutils.version import LooseVersion

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('_themes'))

# -- General configuration -----------------------------------------------------

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.blockdiag', 'sphinx.ext.mathjax']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

# ADJUST IT TO FIT YOUR NEEDS!1
# blockdiag_fontpath = '/usr/share/fonts/truetype/ipafont/ipagp.ttf'
blockdiag_fontpath = '/Users/ich/Library/Fonts/DejaVuSans-Bold.ttf'

# General information about the project.
project = u'Acrylamid'
copyright = u'%i, Martin Zimmermann' % datetime.date.today().year

release = pkg_resources.get_distribution("acrylamid").version  # 0.6, 0.6.1, 0.7 or 0.7.1
version = '%i.%i' % tuple(LooseVersion(release).version[:2])  # 0.6 or 0.7

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

exclude_patterns = ['_build']

html_theme = 'werkzeug'
html_theme_path = ['_themes']
html_static_path = ['_static']

htmlhelp_basename = 'acrylamiddoc'

# -- Options for LaTeX output --------------------------------------------------

latex_documents = [
  ('index', 'acrylamid.tex', u'Acrylamid Documentation',
   u'Martin Zimmermann', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'acrylamid', u'Acrylamid Documentation',
     [u'Martin Zimmermann'], 1)
]

# -- http://stackoverflow.com/questions/7825263/including-docstring-in-sphinx-documentation --
from sphinx.ext import autodoc

class SimpleDocumenter(autodoc.ClassDocumenter):
    objtype = "simple"

    #do not indent the content
    content_indent = ""

    #do not add a header to the docstring
    def add_directive_header(self, sig):
        pass

def setup(app):
    app.add_autodocumenter(SimpleDocumenter)

########NEW FILE########
__FILENAME__ = werkzeug_theme_support
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class WerkzeugStyle(Style):
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
        Name.Decorator:            "#1B5C66",        # class: 'nd' - to be revised
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
__FILENAME__ = search
#!/usr/bin/env python

from __future__ import unicode_literals

import sys
import os
import io
import json


def find(node):

    if len(node) == 2:
        yield node[1]

    for key in node[0]:
        find(node[0][key])


def search(needle, haystack):

    if needle[0] not in haystack:
        return False

    node = haystack[needle[0]]
    needle = needle[1:]
    i, j = 0, 0

    while j < len(needle):

        if needle[i:j+1] in node[0]:
            node = node[0][needle[i:j+1]]
            i = j + 1

        j += 1

    if i != j:
        return False

    if len(node) == 2:
        print 'exact match:', node[1]

    rest = []
    for key in node[0]:
        rest.append(list(find(node[0][key])))
    print 'partial match:', sum(sum(rest, []), [])


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print 'usage: %s /path/to/[a-z].js keyword' % sys.argv[0]
        sys.exit(1)

    with io.open(sys.argv[1]) as fp:
        tree = {os.path.basename(sys.argv[1])[0]: json.load(fp)}

    search(sys.argv[2].decode('utf-8'), tree)

########NEW FILE########
__FILENAME__ = content
# -*- coding: utf-8 -*-

import os
import attest

from os.path import join, isfile

from acrylamid import core, log, utils, helpers
from acrylamid.compat import iteritems
from acrylamid.commands import compile
from acrylamid.defaults import conf

# supress warnings
log.init('acrylamid', 40)
options = type('Options', (object, ), {
    'ignore': False, 'force': False, 'dryrun': False, 'parser': 'compile'})


def entry(**kw):

    L = [('title', 'Hänsel and Gretel!'),
         ('date', '12.02.2012 15:46')]

    res = ['---']

    for k, v in L:
        if k not in kw:
            res.append('%s: %s' % (k, v))
    for k, v in iteritems(kw):
        res.append('%s: %s' % (k, v))

    res.append('---')
    res.append('')
    res.append('# Test')
    res.append('')
    res.append('This is supercalifragilisticexpialidocious.')

    return '\n'.join(res)


class SingleEntry(attest.TestBase):

    @classmethod
    def __context__(self):
        with attest.tempdir() as path:

            self.path = path
            os.chdir(self.path)
            os.mkdir('content/')
            os.mkdir('layouts/')

            with open('layouts/main.html', 'w') as fp:
                fp.write('{{ env.entrylist[0].content }}\n')

            self.conf = core.Configuration(conf)
            self.env = core.Environment({'options': options, 'globals': utils.Struct()})

            self.conf['filters'] = ['HTML']
            self.conf['views'] = {'/:year/:slug/': {'view': 'entry'}}
            yield

    def exists_at_permalink(self):
        with open('content/bla.txt', 'w') as fp:
            fp.write(entry())

        compile(self.conf, self.env)
        assert isfile(join('output/', '2012', 'haensel-and-gretel', 'index.html'))

    @attest.test
    def renders_custom_permalink(self):
        with open('content/bla.txt', 'w') as fp:
            fp.write(entry(permalink='/about/me.asp'))

        compile(self.conf, self.env)
        assert isfile(join('output/', 'about', 'me.asp'))

    @attest.test
    def appends_index(self):
        with open('content/bla.txt', 'w') as fp:
            fp.write(entry(permalink='/about/me/'))

        compile(self.conf, self.env)
        assert isfile(join('output/', 'about', 'me', 'index.html'))

    @attest.test
    def plaintext(self):
        with open('content/bla.txt', 'w') as fp:
            fp.write(entry(permalink='/'))

        compile(self.conf, self.env)

        expected = '# Test\n\nThis is supercalifragilisticexpialidocious.'
        assert open('output/index.html').read() == expected

    @attest.test
    def markdown(self):
        with open('content/bla.txt', 'w') as fp:
            fp.write(entry(permalink='/', filter='[Markdown]'))

        compile(self.conf, self.env)

        expected = '<h1>Test</h1>\n<p>This is supercalifragilisticexpialidocious.</p>'
        assert open('output/index.html').read() == expected

    @attest.test
    def fullchain(self):
        with open('content/bla.txt', 'w') as fp:
            fp.write(entry(permalink='/', filter='[Markdown, h1, hyphenate]', lang='en'))

        compile(self.conf, self.env)

        expected = ('<h2>Test</h2>\n<p>This is su&shy;per&shy;cal&shy;ifrag&shy;'
                    'ilis&shy;tic&shy;ex&shy;pi&shy;ali&shy;do&shy;cious.</p>')
        assert open('output/index.html').read() == expected


class MultipleEntries(attest.TestBase):

    @classmethod
    def __context__(self):
        with attest.tempdir() as path:
            self.path = path

            os.chdir(self.path)
            os.mkdir('content/')
            os.mkdir('layouts/')

            with open('layouts/main.html', 'w') as fp:
                fp.write('{{ env.entrylist[0].content }}\n')

            with open('layouts/atom.xml', 'w') as fp:
                fp.write("{% for entry in env.entrylist %}\n{{ entry.content ~ '\n' }}\n{% endfor %}")

            self.conf = core.Configuration(conf)
            self.env = core.Environment({'options': options, 'globals': utils.Struct()})

            self.conf['filters'] = ['Markdown', 'h1']
            self.conf['views'] = {'/:year/:slug/': {'view': 'entry'},
                                  '/atom.xml': {'view': 'Atom', 'filters': ['h2', 'summarize+2']}}
            yield

    @attest.test
    def markdown(self):
        with open('content/foo.txt', 'w') as fp:
            fp.write(entry(title='Foo'))
        with open('content/bar.txt', 'w') as fp:
            fp.write(entry(title='Bar'))

        compile(self.conf, self.env)

        expected = '<h2>Test</h2>\n<p>This is supercalifragilisticexpialidocious.</p>'
        assert open('output/2012/foo/index.html').read() == expected
        assert open('output/2012/bar/index.html').read() == expected

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

import attest
from acrylamid.core import cache


class Cache(attest.TestBase):

    def __context__(self):
        with attest.tempdir() as path:
            self.path = path
            cache.init(self.path)

        yield

    @attest.test
    def persistence(self):

        cache.init(self.path)
        cache.set('foo', 'bar', "Hello World!")
        cache.set('foo', 'baz', "spam")
        assert cache.get('foo', 'bar') == "Hello World!"
        assert cache.get('foo', 'baz') == "spam"

        cache.shutdown()
        cache.init(self.path)
        assert cache.get('foo', 'bar') == "Hello World!"
        assert cache.get('foo', 'baz') == "spam"

    @attest.test
    def remove(self):

        cache.init(self.path)
        cache.set('foo', 'bar', 'baz')
        cache.remove('foo')
        cache.remove('invalid')

        assert cache.get('foo', 'bar') == None
        assert cache.get('invalid', 'bla') == None

    @attest.test
    def clear(self):

        cache.init(self.path)
        cache.set('foo', 'bar', 'baz')
        cache.set('spam', 'bar', 'baz')

        cache.clear()
        assert cache.get('foo', 'bar') == None
        assert cache.get('spam', 'bar') == None

########NEW FILE########
__FILENAME__ = entry
# -*- coding: utf-8 -*-

import tempfile
import attest

from datetime import datetime

from acrylamid import log
from acrylamid.errors import AcrylamidException
from acrylamid.compat import iteritems

from acrylamid.readers import Entry
from acrylamid.defaults import conf

log.init('acrylamid', level=40)
conf['entry_permalink'] = '/:year/:slug/'

def create(path, **kwargs):

    with open(path, 'w') as fp:
        fp.write('---\n')
        for k, v in iteritems(kwargs):
            fp.write('%s: %s\n' % (k, v))
        fp.write('---\n')


class TestEntry(attest.TestBase):

    def __context__(self):
        fd, self.path = tempfile.mkstemp(suffix='.txt')
        yield

    @attest.test
    def dates(self):

        create(self.path, date='13.02.2011, 15:36', title='bla')
        date = Entry(self.path, conf).date.replace(tzinfo=None)

        assert date.year == 2011
        assert date.month == 2
        assert date.day == 13
        assert date == datetime(year=2011, month=2, day=13, hour=15, minute=36)

    @attest.test
    def alternate_dates(self):

        create(self.path, date='1.2.2034', title='bla')
        date = Entry(self.path, conf).date.replace(tzinfo=None)

        assert date.year == 2034
        assert date.month == 2
        assert date.day == 1
        assert date == datetime(year=2034, month=2, day=1)

    @attest.test
    def invalid_dates(self):

        create(self.path, date='unparsable', title='bla')
        with attest.raises(AcrylamidException):
            Entry(self.path, conf).date

    @attest.test
    def permalink(self):

        create(self.path, title='foo')
        entry = Entry(self.path, conf)

        assert entry.permalink == '/2013/foo/'

        create(self.path, title='foo', permalink='/hello/world/')
        entry = Entry(self.path, conf)

        assert entry.permalink == '/hello/world/'

        create(self.path, title='foo', permalink_format='/:year/:slug/index.html')
        entry = Entry(self.path, conf)

        assert entry.permalink == '/2013/foo/'

    @attest.test
    def tags(self):

        create(self.path, title='foo', tags='Foo')
        assert Entry(self.path, conf).tags == ['Foo']

        create(self.path, title='foo', tags='[Foo, Bar]')
        assert Entry(self.path, conf).tags == ['Foo', 'Bar']

    @attest.test
    def deprecated_keys(self):

        create(self.path, title='foo', tag=[], filter=[])
        entry = Entry(self.path, conf)

        assert 'tags' in entry
        assert 'filters' in entry

    @attest.test
    def custom_values(self):

        create(self.path, title='foo', image='/img/test.png')
        entry = Entry(self.path, conf)

        assert 'image' in entry
        assert entry.image == '/img/test.png'

    @attest.test
    def fallbacks(self):

        create(self.path, title='Bla')
        entry = Entry(self.path, conf)

        assert entry.draft == False
        assert entry.email == 'info@example.com'
        assert entry.author == 'Anonymous'
        assert entry.extension == 'txt'
        assert entry.year == datetime.now().year
        assert entry.imonth == datetime.now().month
        assert entry.iday == datetime.now().day

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-

import re
import attest

from acrylamid.core import Configuration
from acrylamid.filters import FilterList, FilterTree
from acrylamid.filters import Filter, disable


def build(name, **kw):
    return type(name, (Filter, ), kw)(Configuration({}), {}, name)


class TestFilterlist(attest.TestBase):

    @attest.test
    def plain_strings(self):

        f1 = build('F1', match=['foo', 'bar'], conflicts=['spam'])
        f2 = build('F2', match=['spam'])
        f3 = build('F3', match=['bla'])

        x = FilterList([f1])

        assert f1 in x
        assert f2 in x
        assert f3 not in x

    @attest.test
    def regex_strings(self):

        f1 = build('F1', match=['foo', 'bar'], conflicts=['spam'])
        f2 = build('F2', match=[re.compile('^spam$')])
        f3 = build('F3', match=['bla'])

        x = FilterList([f1])

        assert f1 in x
        assert f2 in x
        assert f3 not in x

    @attest.test
    def conflicts(self):

        f1 = build('F1', match=['foo', 'bar'], conflicts=['spam'])
        f4 = build('F4', match=['baz'], conflicts=['foo'])

        x = FilterList([f1])

        assert f1 in x
        assert f4 in x

    @attest.test
    def access_by_name(self):

        f3 = build('F3', match=[re.compile('^sp', re.I)])
        x = FilterList([f3])

        assert x['sp'] == f3
        assert x['spam'] == f3
        assert x['sPaMmEr'] == f3

    @attest.test
    def disable(self):

        f1 = build('F1', match=['Foo'], conflicts=['Bar'])
        f2 = disable(f1)

        assert hash(f1) != hash(f2)
        assert f1.match != f2.match

        assert f1.name == f2.name
        assert f1.conflicts == f2.conflicts


class TestFilterTree(attest.TestBase):

    @attest.test
    def path(self):

        t = FilterTree()
        t.add([1, 3, 4, 7], 'foo')
        assert t.path('foo') == [1, 3, 4, 7]

    @attest.test
    def works(self):

        t = FilterTree()

        t.add([1, 2, 5], 'foo')
        t.add([1, 2, 3, 5], 'bar')
        t.add([7, ], 'baz')

        assert list(t.iter('foo')) == [[1, 2], [5, ]]
        assert list(t.iter('bar')) == [[1, 2], [3, 5]]
        assert list(t.iter('baz')) == [[7, ], ]

    @attest.test
    def edge_cases(self):

        t = FilterTree()

        t.add([1, 2], 'foo')
        t.add([1, 2], 'bar')
        t.add([2, ], 'baz')

        assert list(t.iter('foo')) == [[1, 2], ]
        assert list(t.iter('bar')) == [[1, 2], ]
        assert list(t.iter('baz')) == [[2, ], ]

########NEW FILE########
__FILENAME__ = filters_builtin
# -*- coding: utf-8 -*-

from acrylamid import log, utils, core
from acrylamid.filters import initialize, get_filters

import attest

tt = attest.Tests()

log.init('foo', 35)

conf = core.Configuration({'lang': 'en', 'theme': ''})
env = utils.Struct({'path': '', 'engine': None, 'options': type('X', (), {'ignore': False})})
initialize([], conf, env)

# now we have filters in path
from acrylamid.filters.hyphenation import build


class Entry(object):

    permalink = '/foo/'

    def __init__(self, lang='en'):
        self.lang = lang


class Hyphenation(attest.TestBase):

    @attest.test
    def hyphenate(self):

        hyph = get_filters()['Hyphenate'](conf, env, 'Hyphenate')

        hyph.transform('Airplane', Entry('en')) == 'Airplane'
        hyph.transform('supercalifragilisticexpialidocious', Entry('en')) == \
                         '&shy;'.join(['su', 'per', 'cal', 'ifrag', 'ilis', 'tic', 'ex',
                                       'pi', 'ali', 'do', 'cious'])

        hyph = get_filters()['Hyphenate'](conf, env, 'Hyphenate')

        assert hyph.transform('Flugzeug', Entry('de'), '8') == 'Flugzeug'
        assert hyph.transform('Flugzeug', Entry('de'), '7') == 'Flug&shy;zeug'

        # test unsupported
        assert hyph.transform('Flugzeug', Entry('foo'), '8') == 'Flugzeug'

    @attest.test
    def build_pattern(self):

        # short term
        build('en')

        hyphenate = build('en_US')
        assert hyphenate('Airplane') == ['Air', 'plane']


@tt.test
def jinja2():

    jinja2 = get_filters()['Jinja2'](conf, env, 'Jinja2')

    assert jinja2.transform('{{ entry.lang }}', Entry('de')) == 'de'
    assert jinja2.transform("{{ 'which which' | system }}", None) == '/usr/bin/which'


@tt.test
def mako():

    mako = get_filters()['Mako'](conf, env, 'Mako')

    e = Entry('de')
    e.filename = '1'

    assert mako.transform('${entry.lang}', Entry('de')) == 'de'
    assert mako.transform("${ 'which which' | system }", e) == '/usr/bin/which'


@tt.test
def acronyms():

    acronyms = get_filters()['Acronyms'](conf, env, 'Acronyms')
    abbr = lambda abbr, expl: '<abbr title="%s">%s</abbr>' % (expl, abbr)

    examples = [
        ('CGI', abbr('CGI', 'Common Gateway Interface')),
        ('IMDB', abbr('IMDB', 'Internet Movie Database')),
        ('IMDb', abbr('IMDb', 'Internet Movie Database')),
        ('PHP5', abbr('PHP5', 'Programmers Hate PHP ;-)')),
        ('TEST', 'TEST')
    ]

    for test, result in examples:
        assert acronyms.transform(test, None) == result


@tt.test
def headoffset():

    h1 = get_filters()['h1'](conf, env, 'h1')
    examples = [
        ('<h1>Hello</h1>', '<h2>Hello</h2>'), ('<h2>World</h2>', '<h3>World</h3>'),
        ('<h1 class="foo bar">spam</h1>', '<h2 class="foo bar">spam</h2>'),
        ('<h1 class="foo" id="baz">spam</h1>', '<h2 class="foo" id="baz">spam</h2>'),
    ]

    for test, result in examples:
        assert h1.transform(test, None) == result

    h5 = get_filters()['h5'](conf, env, 'h5')
    assert h5.transform('<h3>eggs</h3>', '<h6>eggs</h6>')


@tt.test
def summarize():

    summarize = get_filters()['summarize'](conf, env, 'summarize')
    examples = [('Hello World', 'Hello World'),
                # a real world example
                ('<p>Hello World, you have to click this link because</p>',
                 '<p>Hello World, you have to <span>&#8230;<a href="/foo/" '+ \
                 'class="continue">continue</a>.</span></p>'),
                ('<p>Hel&shy;lo Wor&shy;ld, you have to click this link because</p>',
                # now with HTML entities
                 '<p>Hel&shy;lo Wor&shy;ld, you have to <span>&#8230;<a href="/foo/" '+ \
                 'class="continue">continue</a>.</span></p>'),
                ('Hello<br />', 'Hello<br />'),
                ('<p>Hello World, you have<br /> to <br /> click<br /> this<br /> link...</p>',
                 '<p>Hello World, you have<br /> to <span>&#8230;<a href="/foo/" '+ \
                 'class="continue">continue</a>.</span></p>'),
                ('Hello World, you have to click this link because',
                 'Hello World, you have to <span>&#8230;<a href="/foo/" '+ \
                 'class="continue">continue</a>.</span>')]

    for text, result in examples:
        assert summarize.transform(text, Entry(), '5') == result

    conf['summarize_mode'] = 0
    summarize = get_filters()['summarize'](conf, env, 'summarize')

    assert summarize.transform((
        '<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod '
        'tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam</p>'
        '\n'
        '<p>Here it breaks ...</p>'),
        Entry(), '20') == (
        '<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod '
        'tempor incididunt ut labore et dolore magna aliqua. Ut '
        '<span>&#8230;<a href="/foo/" class="continue">continue</a>.</span></p>')



@tt.test
def intro():

    intro = get_filters()['intro'](conf, env, 'intro')
    examples = [('Hello World', ''),
                ('<p>First</p>', '<p>First</p><span>&#8230;<a href="/foo/" class="continue">continue</a>.</span>'),
                ('<p>First</p><p>Second</p>', '<p>First</p><span>&#8230;<a href="/foo/" class="continue">continue</a>.</span>')]

    for text, result in examples:
        assert intro.transform(text, Entry(), '1') == result


@tt.test
def strip():

    strip = get_filters()['strip'](conf, env, 'strip')
    examples = [
        ('<em>Foo</em>', 'Foo'), ('<a href="#">Bar</a>', 'Bar'),
        ('<video src="#" />', '')]

    for text, result in examples:
        assert strip.transform(text, Entry()) == result

    assert strip.transform('<pre>...</pre>', Entry(), 'pre') == ''
    assert strip.transform('<pre>&lt;</pre>', Entry(), 'pre') == ''


@tt.test
def liquid():

    liquid = get_filters()['liquid'](conf, env, 'liquid')

    # liquid block recognition
    text = '\n'.join([
        "{% tag %}", "", "Foo Bar.", "", "{% endtag %}"
    ])

    rv = liquid.block("tag").match(text)
    assert rv.group(1) == ""
    assert rv.group(2) == "\nFoo Bar.\n"

    # multiple, not nested blocks
    text = '\n'.join([
        "{% block %}", "", "Foo Bar.", "", "{% endblock %}",
        "",
        "{% block %}", "", "Baz.", "", "{% endblock %}"
    ])

    rv = tuple(liquid.block("block").finditer(text))
    assert len(rv) == 2

    x, y = rv
    assert x.group(2).strip() == "Foo Bar."
    assert y.group(2).strip() == "Baz."

    # self-closing block
    text = '{% block a few args %}'
    rv = liquid.block("block").match(text)

    assert rv is not None
    assert rv.group(1) == 'a few args'
    assert rv.group(2) is None

    # blockquote
    examples = [
        ('{% blockquote Author, Source http://example.org/ Title %}\nFoo Bar\n{% endblockquote %}',
         '<blockquote><p>Foo Bar</p><footer><strong>Author, Source</strong> <cite><a href="http://example.org/">Title</a></cite></footer></blockquote>'),
    ]

    for text, result in examples:
        assert liquid.transform(text, Entry()) == result

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

import attest

from acrylamid import helpers, refs
from acrylamid import AcrylamidException


class Helpers(attest.TestBase):

    @attest.test
    def safeslug(self):

        examples = (('This is a Test', 'this-is-a-test'),
                    ('this is a test', 'this-is-a-test'),
                    ('This is another-- test', 'this-is-another-test'),
                    ('A real example: Hello World in C++ -- "a new approach*"!',
                     'a-real-example-hello-world-in-c++-a-new-approach'))

        for value, expected in examples:
            assert helpers.safeslug(value) == expected

        examples = ((u'Hänsel und Gretel', 'haensel-und-gretel'),
                    (u'fácil € ☺', 'facil-eu'),
                    (u'русский', 'russkii'))

        for value, expected in examples:
            assert helpers.safeslug(value) == expected

    @attest.test
    def joinurl(self):

        examples = ((['hello', 'world'], 'hello/world'),
                    (['/hello', 'world'], '/hello/world'),
                    (['hello', '/world'], 'hello/world'),
                    (['/hello', '/world'], '/hello/world'),
                    (['/hello/', '/world/'], '/hello/world/index.html'),
                    (['/bar/', '/'], '/bar/index.html'))

        for value, expected in examples:
            assert helpers.joinurl(*value) == expected

    @attest.test
    def expand(self):

        assert helpers.expand('/:foo/:bar/', {'foo': 1, 'bar': 2}) == '/1/2/'
        assert helpers.expand('/:foo/:spam/', {'foo': 1, 'bar': 2}) == '/1/spam/'
        assert helpers.expand('/:foo/', {'bar': 2}) == '/foo/'

        assert helpers.expand('/:slug.html', {'slug': 'foo'}) == '/foo.html'
        assert helpers.expand('/:slug.:slug.html', {'slug': 'foo'}) == '/foo.foo.html'

    @attest.test
    def paginate(self):

        X = type('X', (str, ), {'modified': True}); refs.load()

        res = ['1', 'asd', 'asd123', 'egg', 'spam', 'ham', '3.14', '42']
        res = [X(val) for val in res]

        # default stuff
        assert list(helpers.paginate(res, 4)) == \
            [((None, 1, 2), res[:4], True), ((1, 2, None), res[4:], True)]
        assert list(helpers.paginate(res, 7)) == \
            [((None, 1, 2), res[:7], True), ((1, 2, None), res[7:], True)]

        # with orphans
        assert list(helpers.paginate(res, 7, orphans=1)) == \
            [((None, 1, None), res, True)]
        assert list(helpers.paginate(res, 6, orphans=1)) == \
            [((None, 1, 2), res[:6], True), ((1, 2, None), res[6:], True)]

        # a real world example which has previously failed
        res = [X(_) for _ in range(20)]
        assert list(helpers.paginate(res, 10)) == \
            [((None, 1, 2), res[:10], True), ((1, 2, None), res[10:], True)]

        res = [X(_) for _ in range(21)]
        assert list(helpers.paginate(res, 10)) == \
            [((None, 1, 2), res[:10], True), ((1, 2, 3), res[10:20], True),
             ((2, 3, None), res[20:], True)]

        # edge cases
        assert list(helpers.paginate([], 2)) == []
        assert list(helpers.paginate([], 2, orphans=7)) == []
        assert list(helpers.paginate([X('1'), X('2'), X('3')], 3, orphans=1)) == \
            [((None, 1, None), [X('1'), X('2'), X('3')], True)]

    @attest.test
    def safe(self):

        assert helpers.safe('"') == '"'
        assert helpers.safe('') == '""'

        assert helpers.safe('*Foo') == '"*Foo"'
        assert helpers.safe('{"Foo') == '\'{"Foo\''

        assert helpers.safe('"Foo" Bar') == '"Foo" Bar'
        assert helpers.safe("'bout \" and '") == "\"'bout \" and '\""

        assert helpers.safe('Hello World') == 'Hello World'
        assert helpers.safe('Hello: World') == '"Hello: World"'
        assert helpers.safe('Hello\'s World') == 'Hello\'s World'
        assert helpers.safe('Hello "World"') == 'Hello "World"'

        assert helpers.safe('[foo][bar] Baz') == '"[foo][bar] Baz"'

    @attest.test
    def system(self):

        examples = ((['echo', 'ham'], None, 'ham'),
                    ('cat', 'foo', 'foo'),
            )
        for cmd, stdin, expected in examples:
            assert helpers.system(cmd, stdin) == expected

        with attest.raises(AcrylamidException):
            helpers.system('false')

        with attest.raises(OSError):
            helpers.system('foo', None)

########NEW FILE########
__FILENAME__ = imprt
# -*- encoding: utf-8 -*-

import io
import attest
from os.path import join, dirname

from acrylamid import log, tasks, helpers

log.init('acrylamid', 20)
tasks.task = lambda x,y,z: lambda x: x

from acrylamid.tasks import imprt

read = lambda path: io.open(join(dirname(__file__), 'samples', path), encoding='utf-8').read()
wordpress = read('thethreedevelopers.wordpress.2012-04-11.xml')
rss = read('blog.posativ.org.xml')
atom = read('vlent.nl.xml')


class Import(attest.TestBase):

    @attest.test
    def unescape(self):

        assert imprt.unescape('&lt;p&gt;Foo&lt;/p&gt;') == '<p>Foo</p>'
        assert imprt.unescape('Some Text/') == 'Some Text/'

    @attest.test
    def conversion(self):

        md = 'Hello _[World](http://example.com/)!_'
        rst = 'Hello *`World <http://example.com/>`_!*'
        html = '<p>Hello <em><a href="http://example.com/">World</a>!</em></p>'

        try:
            import html2text
        except ImportError:
            return

        try:
            import html2rest
        except ImportError:
            try:
                helpers.system(['which', 'pandoc'])
            except:
                return
        else:
            return

        assert imprt.convert(html, fmt='Markdown') == (md, 'markdown')
        assert imprt.convert(html, fmt='reStructuredText') == (rst, 'rst')
        assert imprt.convert(html, fmt='HTML') == (html, 'html')

        assert imprt.convert('', fmt='Markdown') == ('', 'markdown')
        assert imprt.convert(None, fmt='Markdown') == ('', 'markdown')


class RSS(attest.TestBase):

    @attest.test
    def recognition(self):

        examples = [
            'baz',
            '<?xml version="1.0" encoding="utf-8"?>' \
            + '<rss version="1.0" xmlns:atom="http://www.w3.org/2005/Atom">' \
            + '</rss>',
            wordpress, atom
        ]

        for value in examples:
            with attest.raises(imprt.InputError):
                imprt.rss(value)

        imprt.rss(rss)

    @attest.test
    def defaults(self):

        defaults, items = imprt.rss(rss)

        assert defaults['sitename'] == 'mecker. mecker. mecker.'
        assert defaults['www_root'] == 'http://blog.posativ.org/'

        assert len(items) == 1

    @attest.test
    def first_entry(self):

        defaults, items = imprt.rss(rss)
        entry = items[0]

        for key in 'title', 'content', 'link', 'date', 'tags':
            assert key in entry

        assert len(entry['tags']) == 2


class Atom(attest.TestBase):

    @attest.test
    def recognition(self):

        examples = [
            'bar',
            '<?xml version="1.0" encoding="utf-8"?>' \
            + '<feed xmlns="http://invalid.org/" xml:lang="de">' \
            + '</feed>',
            wordpress, rss
        ]

        for value in examples:
            with attest.raises(imprt.InputError):
                imprt.atom(value)

        imprt.atom(atom)

    @attest.test
    def defaults(self):

        defaults, items = imprt.atom(atom)

        assert defaults['sitename'] == "Mark van Lent's weblog"
        assert defaults['author'] == 'Mark van Lent'
        assert defaults['www_root'] == 'http://www.vlent.nl/weblog/'

        assert len(items) == 1

    @attest.test
    def first_entry(self):

        defaults, items = imprt.atom(atom)
        entry = items[0]

        for key in 'title', 'content', 'link', 'date', 'tags':
            assert key in entry

        assert len(entry['tags']) == 2


class WordPress(attest.TestBase):

    @attest.test
    def recognition(self):

        examples = [
            'bar', rss, atom
        ]

        for value in examples:
            with attest.raises(imprt.InputError):
                imprt.wordpress(value)

    @attest.test
    def defaults(self):

        defaults, items = imprt.wordpress(wordpress)
        entry = items[0]

        for key in 'title', 'link', 'content', 'date', 'author', 'tags':
            assert key in entry

        assert len(entry['tags']) == 1

    @attest.test
    def additional_metadata(self):

        defaults, items = imprt.wordpress(wordpress)

        assert 'type' in items[1]
        assert items[1]['type'] == 'page'

        assert 'draft' in items[2]
        assert items[2]['draft']

########NEW FILE########
__FILENAME__ = lib
# -*- coding: utf-8 -*-

from attest import test, TestBase

from acrylamid.lib.html import HTMLParser
f = lambda x: ''.join(HTMLParser(x).result)


class TestHTMLParser(TestBase):

    @test
    def starttag(self):

        examples = [
            '<p></p>',
            '<p id="foo"></p>',
            '<script src="/js/foo.js" type="text/javascript"></script>',
            '<iframe allowfullscreen></iframe>',
        ]

        for ex in examples:
            assert f(ex) == ex

    @test
    def data(self):
        assert f('<p>Data!1</p>') == '<p>Data!1</p>'

    @test
    def endtag(self):

        examples = [
            '<p></p></p>',
            '</p>'*3,
        ]

        for ex in examples:
            assert f(ex) == ex

    @test
    def startendtag(self):

        for ex in ['<br />',  '<link id="foo" attr="bar"/>']:
            assert f(ex) == ex

    @test
    def entityrefs(self):

        assert f('<span>&amp;</span>') == '<span>&amp;</span>'
        assert f('<span>&foo;</span>') == '<span>&foo;</span>'

    @test
    def charrefs(self):

        assert f('<span>&#1234;</span>') == '<span>&#1234;</span>'

########NEW FILE########
__FILENAME__ = readers
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io
import attest

tt = attest.Tests()
from acrylamid.readers import reststyle, markdownstyle, distinguish, ignored
from acrylamid.readers import pandocstyle


@tt.test
def rest():

    header = ["Header",
    "======",
    "",
    ":date: 2001-08-16",
    ":version: 1",
    ":draft: True",
    ":authors: foo, bar",
    ":indentation: Since the field marker may be quite long, the second",
    "   and subsequent lines of the field body do not have to line up",
    "   with the first line, but they must be indented relative to the",
    "   field name marker, and they must line up with each other.",
    ":parameter i: integer",
    "",
    "Hello *World*."]

    i, meta = reststyle(io.StringIO('\n'.join(header)))
    assert i == len(header) - 1

    assert 'foo' in meta['authors']
    assert meta['version'] == 1
    assert meta['date'] == '2001-08-16'
    assert 'second and subsequent' in meta['indentation']
    assert meta['draft'] is True


@tt.test
def mkdown():

    header = ["Title:   My Document",
    "Summary: A brief description of my document.",
    "Authors: Waylan Limberg",
    "         John Doe",
    "Date:    October 2, 2007",
    "blank-value: ",
    "base_url: http://example.com",
    "",
    "This is the first paragraph of the document."]

    i, meta = markdownstyle(io.StringIO('\n'.join(header)))
    assert i == len(header) - 1

    assert 'John Doe' in meta['authors']
    assert meta['date'] == 'October 2, 2007'
    assert meta['blank-value'] == ""


@tt.test
def pandoc():

    header = ["% title",
    "% Author; Another",
    "% June 15, 2006",
    "",
    "Here comes the regular text"]

    i, meta = pandocstyle(io.StringIO('\n'.join(header)))
    assert i == len(header) - 1

    assert 'Another' in meta['author']
    assert meta['date'] == 'June 15, 2006'


@tt.test
def quotes():

    assert distinguish('"') == '"'
    assert distinguish('""') == ''

    assert distinguish('Foo"') == 'Foo"'
    assert distinguish('"Foo') == '"Foo'

    assert distinguish('"Foo" Bar') == '"Foo" Bar'
    assert distinguish('"Foo Bar"') == 'Foo Bar'

    assert distinguish("\"'bout \" and '\"") == "'bout \" and '"

    # quote commas, so they are not recognized as a new part
    assert distinguish('["X+ext(foo, bar=123)", other]') == ["X+ext(foo, bar=123)", "other"]
    assert distinguish('["a,b,c,d", a, b, c]') == ['a,b,c,d', 'a', 'b', 'c']

    # shlex tokenizer should not split on "+" and " "
    assert distinguish("[X+Y]") == ["X+Y"]
    assert distinguish("[foo bar, baz]") == ["foo bar", "baz"]
    assert distinguish("[Foo, ]") == ["Foo"]

    # non-ascii
    assert distinguish('["Föhn", "Bär"]') == ["Föhn", "Bär"]
    assert distinguish('[Bla, Calléjon]') == ["Bla", "Calléjon"]
    assert distinguish('[да, нет]') == ["да", "нет"]


@tt.test
def types():

    for val in ['None', 'none', '~', 'null']:
        assert distinguish(val) == None

    for val in ['3.14', '42.0', '-0.01']:
        assert distinguish(val) == float(val)

    for val in ['1', '2', '-1', '9000']:
        assert distinguish(val) == int(val)

    assert distinguish('test') == 'test'
    assert distinguish('') == ''


@tt.test
def backslash():

    assert distinguish('\\_bar') == '_bar'
    assert distinguish('foo\\_') == 'foo_'
    assert distinguish('foo\\\\bar') == 'foo\\bar'


@tt.test
def ignore():

    assert ignored('/path/', 'foo', ['foo', 'fo*', '/foo'], '/path/')
    assert ignored('/path/', 'dir/', ['dir', 'dir/'], '/path/')
    assert not ignored('/path/to/', 'baz/', ['/baz/', '/baz'], '/path/')

    assert ignored('/', '.git/info/refs', ['.git*'], '/')
    assert ignored('/', '.gitignore', ['.git*'], '/')

    assert ignored('/', '.DS_Store', ['.DS_Store'], '/')

########NEW FILE########
__FILENAME__ = search
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import attest

tt = attest.Tests()
from acrylamid.views import search


@tt.test
def commonprefix():

    for a, b, i in  ('foo', 'faa', 1), ('test', 'test', 4), ('', 'spam', 0), ('a', 'b', 0):
        assert search.commonprefix(a, b) == (i, b)


@tt.test
def basics():

    tree = {}
    for word in 'javascript', 'java', 'java-vm':
        search.insert(tree, word, 1)

    assert 'j' in tree
    assert 'ava' in tree['j'][0]
    assert 'script' in tree['j'][0]['ava'][0]
    assert '-vm' in tree['j'][0]['ava'][0]

    assert len(tree['j'][0]['ava']) == 2  # Java found!
    assert len(tree['j'][0]['ava'][0]['script']) == 2  # JavaScript found!
    assert len(tree['j'][0]['ava'][0]['-vm']) == 2  # Java-VM found!


@tt.test
def split():

    tree = {}
    for word in 'a', 'aa', 'aaa', 'aaaa', 'ab':
        search.insert(tree, word, 1)

    assert 'a' in tree
    assert 'a' in tree['a'][0]
    assert 'a' in tree['a'][0]['a'][0]
    assert 'a' in tree['a'][0]['a'][0]['a'][0]
    assert 'b' in tree['a'][0]

    assert len(tree['a']) == 1  # search word must be longer than three chars ;)
    assert len(tree['a'][0]['a']) == 2
    assert len(tree['a'][0]['b']) == 2
    assert len(tree['a'][0]['a'][0]['a']) == 2
    assert len(tree['a'][0]['a'][0]['a'][0]['a']) == 2


@tt.test
def advanced():

    def find(node, i):
        if len(node) == 2 and node[1] == i:
            yield i

        for key in node[0]:
            yield find(node[0][key], i)

    tree = {}
    words = 'eines', 'erwachte', 'er', 'einem', 'ein', 'erhalten', 'es', \
            'etwas', 'eine', 'einer', 'entgegenhob'

    for i, word in enumerate(words):
        search.insert(tree, word, i)

    for i in range(len(word)):
        assert len(list(find((tree, -1), i))) == 1

if __name__ == '__main__':

    tt.run()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

from acrylamid.utils import Metadata, neighborhood

import attest
tt = attest.Tests()


class TestMetadata(attest.TestBase):

    @attest.test
    def works(self):

        dct = Metadata()
        dct['hello.world'] = 1

        assert dct['hello']['world'] == 1
        assert dct.hello.world == 1

        try:
            dct.foo
            dct.foo.bar
        except KeyError:
            assert True
        else:
            assert False

        dct['hello.foreigner'] = 2

        assert dct['hello']['world'] == 1
        assert dct.hello.world == 1

        assert dct.hello.foreigner == 2

    @attest.test
    def redirects(self):

        dct = Metadata()
        alist = [1, 2, 3]

        dct['foo'] = alist
        dct.redirect('foo', 'baz')

        assert 'foo' not in dct
        assert 'baz' in dct
        assert dct['baz'] == alist


    @attest.test
    def update(self):

        dct = Metadata()
        dct.update({'hello.world': 1})

        assert 'hello' in dct
        assert dct.hello.world == 1

    @attest.test
    def init(self):
        assert Metadata({'hello.world': 1}).hello.world == 1


@tt.test
def neighbors():

    assert list(neighborhood([1, 2, 3])) == \
        [(None, 1, 2), (1, 2, 3), (2, 3, None)]

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

import attest
from acrylamid.views import tag


class Tag(attest.TestBase):

    @attest.test
    def cloud(self):

        tags = {'foo': range(1), 'bar': range(2)}
        cloud = tag.Tagcloud(tags, steps=4, max_items=100, start=0)
        lst = [(t.name, t.step) for t in cloud]

        assert ('foo', 3) in lst
        assert ('bar', 0) in lst

        tags = {'foo': range(1), 'bar': range(2), 'baz': range(4), 'spam': range(8)}
        cloud = tag.Tagcloud(tags, steps=4, max_items=4, start=0)
        lst = [(t.name, t.step) for t in cloud]

        assert ('foo', 3) in lst
        assert ('bar', 2) in lst
        assert ('baz', 1) in lst
        assert ('spam', 0) in lst

########NEW FILE########
