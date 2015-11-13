__FILENAME__ = cache
'''
filecache -- http://code.google.com/p/filecache/

filecache is a decorator which saves the return value of functions even
after the interpreter dies. For example this is useful on functions that download
and parse webpages. All you need to do is specify how long
the return values should be cached (use seconds, like time.sleep).

USAGE:

    from filecache import filecache
    
    @filecache(24 * 60 * 60)
    def time_consuming_function(args):
        # etc
    
    @filecache(filecache.YEAR)
    def another_function(args):
        # etc


NOTE: All arguments of the decorated function and the return value need to be
    picklable for this to work.

NOTE: The cache isn't automatically cleaned, it is only overwritten. If your
    function can receive many different arguments that rarely repeat, your
    cache may forever grow. One day I might add a feature that once in every
    100 calls scans the db for outdated stuff and erases.

NOTE: This is less useful on methods of a class because the instance (self)
    is cached, and if the instance isn't the same, the cache isn't used. This
    makes sense because class methods are affected by changes in whatever
    is attached to self.

Tested on python 2.7 and 3.1

License: BSD, do what you wish with this. Could be awesome to hear if you found
it useful and/or you have suggestions. ubershmekel at gmail


A trick to invalidate a single value:

    @filecache.filecache
    def somefunc(x, y, z):
        return x * y * z
        
    del somefunc._db[filecache._args_key(somefunc, (1,2,3), {})]
    # or just iterate of somefunc._db (it's a shelve, like a dict) to find the right key.


'''

import collections as _collections
import datetime as _datetime
import functools as _functools
import inspect as _inspect
import os as _os
import pickle as _pickle
import shelve as _shelve
import sys as _sys
import time as _time
import traceback as _traceback
import types

_retval = _collections.namedtuple('_retval', 'timesig data')
_SRC_DIR = _os.path.dirname(_os.path.abspath(__file__))

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY
YEAR = 365 * DAY
FOREVER = None

OPEN_DBS = dict()

def _get_cache_name(function):
    """
    returns a name for the module's cache db.
    """
    module_name = _inspect.getfile(function)
    cache_name = module_name
    
    # fix for '<string>' or '<stdin>' in exec or interpreter usage.
    cache_name = cache_name.replace('<', '_lt_')
    cache_name = cache_name.replace('>', '_gt_')
    
    cache_name += '.cache'
    return cache_name


def _log_error(error_str):
    try:
        error_log_fname = _os.path.join(_SRC_DIR, 'filecache.err.log')
        if _os.path.isfile(error_log_fname):
            fhand = open(error_log_fname, 'a')
        else:
            fhand = open(error_log_fname, 'w')
        fhand.write('[%s] %s\r\n' % (_datetime.datetime.now().isoformat(), error_str))
        fhand.close()
    except Exception:
        pass

def _args_key(function, args, kwargs):
    arguments = (args, kwargs)
    # Check if you have a valid, cached answer, and return it.
    # Sadly this is python version dependant
    if _sys.version_info[0] == 2:
        arguments_pickle = _pickle.dumps(arguments)
    else:
        # NOTE: protocol=0 so it's ascii, this is crucial for py3k
        #       because shelve only works with proper strings.
        #       Otherwise, we'd get an exception because
        #       function.__name__ is str but dumps returns bytes.
        arguments_pickle = _pickle.dumps(arguments, protocol=0).decode('ascii')
        
    key = function.__name__ + arguments_pickle
    return key

def filecache(seconds_of_validity=None, fail_silently=False):
    '''
    filecache is called and the decorator should be returned.
    '''
    def filecache_decorator(function):
        @_functools.wraps(function)
        def function_with_cache(*args, **kwargs):
            try:
                key = _args_key(function, args, kwargs)
                
                if key in function._db:
                    rv = function._db[key]
                    if seconds_of_validity is None or _time.time() - rv.timesig < seconds_of_validity:
                        return rv.data
            except Exception:
                # in any case of failure, don't let filecache break the program
                error_str = _traceback.format_exc()
                _log_error(error_str)
                if not fail_silently:
                    raise
            
            retval = function(*args, **kwargs)

            # store in cache
            # NOTE: no need to _db.sync() because there was no mutation
            # NOTE: it's importatnt to do _db.sync() because otherwise the cache doesn't survive Ctrl-Break!
            try:
                function._db[key] = _retval(_time.time(), retval)
                function._db.sync()
            except Exception:
                # in any case of failure, don't let filecache break the program
                error_str = _traceback.format_exc()
                _log_error(error_str)
                if not fail_silently:
                    raise
            
            return retval

        # make sure cache is loaded
        if not hasattr(function, '_db'):
            cache_name = _get_cache_name(function)
            if cache_name in OPEN_DBS:
                function._db = OPEN_DBS[cache_name]
            else:
                function._db = _shelve.open(cache_name)
                OPEN_DBS[cache_name] = function._db
            
            function_with_cache._db = function._db
        
        return function_with_cache

    if type(seconds_of_validity) == types.FunctionType:
        # support for when people use '@filecache.filecache' instead of '@filecache.filecache()'
        func = seconds_of_validity
        return filecache_decorator(func)
    
    return filecache_decorator



########NEW FILE########
__FILENAME__ = clean

# special thanks to Mike Johnson, author of Jep,
# a Java-Python bridge and also the most coherent
# example of setuptools extension code I've seen:
#
# https://github.com/mrj0/jep/tree/master/commands

from __future__ import print_function

import shutil
from os.path import join
from distutils.command.clean import clean

class really_clean(clean):
    
    def run(self):
        build_cathostel = join(self.build_base, 'cathostel')
        build_coffeecup = join(self.build_base, 'coffeecup')
        build_starbucks = join(self.build_base, 'starbucks')
        build_uglies = join(self.build_base, 'disgusting')
        
        print('removing', build_cathostel)
        shutil.rmtree(build_cathostel, ignore_errors=True)
        
        print('removing', build_coffeecup)
        shutil.rmtree(build_coffeecup, ignore_errors=True)
        
        print('removing', build_starbucks)
        shutil.rmtree(build_starbucks, ignore_errors=True)
        
        print('removing', build_uglies)
        shutil.rmtree(build_uglies, ignore_errors=True)
        
        # below this was stuff that was here before --
        
        print('removing', self.build_base)
        shutil.rmtree(self.build_base, ignore_errors=True)
        
        print('removing', self.build_lib)
        shutil.rmtree(self.build_lib, ignore_errors=True)
        
        print('removing', self.build_scripts)
        shutil.rmtree(self.build_scripts, ignore_errors=True)
        
        print('removing', self.build_temp)
        shutil.rmtree(self.build_temp, ignore_errors=True)
        
        print('removing', self.bdist_base)
        shutil.rmtree(self.bdist_base, ignore_errors=True)
########NEW FILE########
__FILENAME__ = coffeescript

from __future__ import print_function, with_statement

from distutils.cmd import Command
from distutils.spawn import spawn
from os import environ, makedirs
from os.path import isdir, join, exists, abspath, basename

from xwhich import xwhich

JAVASCRIPT_LIB_DLCACHE_DIR = join('build', 'starbucks')
COFFEESCRIPT_BUILD_OUT_DIR = join('build', 'coffeecup')
UGLIFICATION_BUILD_MID_DIR = join('build', 'cathostel')
UGLIFICATION_BUILD_OUT_DIR = join('build', 'disgusting')

def javascript_lib_dlcache_dir():
    global JAVASCRIPT_LIB_DLCACHE_DIR
    return JAVASCRIPT_LIB_DLCACHE_DIR

def coffeescript_build_out_dir():
    global COFFEESCRIPT_BUILD_OUT_DIR
    return COFFEESCRIPT_BUILD_OUT_DIR

def uglification_build_mezzo_dir():
    global UGLIFICATION_BUILD_MID_DIR
    return UGLIFICATION_BUILD_MID_DIR

def uglification_build_out_dir():
    global UGLIFICATION_BUILD_OUT_DIR
    return UGLIFICATION_BUILD_OUT_DIR

def js_download_storage():
    from downloads import URLRetrievalStorage
    return URLRetrievalStorage(
        location=javascript_lib_dlcache_dir(),
        base_url="file://%s" % abspath(javascript_lib_dlcache_dir()))

def coffeescript_node_lib_cmds():
    return [join(pth, 'coffee-script', 'bin') \
        for pth in environ.get('NODE_PATH', '').split(':') \
        if bool(len(pth)) and isdir(pth)]

def uglification_node_lib_cmds():
    return [join(pth, 'uglify-js', 'bin') \
        for pth in environ.get('NODE_PATH', '').split(':') \
        if bool(len(pth)) and isdir(pth)]

def coffeescript_cmd():
    return xwhich('coffee',
        also_look=coffeescript_node_lib_cmds())

def uglification_cmd():
    return xwhich('uglifyjs',
        also_look=uglification_node_lib_cmds())

class build_coffeescript(Command):
    """ Distutils command for CoffeScript compilation.
    Based largely on the fine build-system architecture
    of Jep. See also:
    
        https://github.com/mrj0/jep/blob/master/commands/java.py
    
    ... for the orig. """
    
    outdir = None
    user_options = [
        ('coffee=', 'C',
            'use coffeescript command (default: {0})'.format(
                coffeescript_cmd()))]
    description = 'Compile CoffeScript source to JavaScript'
    
    def initialize_options(self):
        build_coffeescript.outdir = coffeescript_build_out_dir()
        if not exists(build_coffeescript.outdir):
            makedirs(build_coffeescript.outdir)
        self.cs_files = []
        self.coffee = coffeescript_cmd()
    
    def finalize_options(self):
        self.cs_files = self.distribution.cs_files
    
    def demitasse(self, js_file):
        spawn([self.coffee,
            '--nodejs', '--no-deprecation',
            '-o', build_coffeescript.outdir,
            '-c', js_file])
    
    def run(self):
        print('')
        for js_file in list(self.cs_files):
            self.demitasse(js_file)



class download_js_libs(Command):
    outdir = None
    user_options = []
    description = 'Fetch JavaScript library files'
    
    def initialize_options(self):
        download_js_libs.outdir = javascript_lib_dlcache_dir()
        if not exists(download_js_libs.outdir):
            makedirs(download_js_libs.outdir)
        self.js_libs = []
        self.js_storage = None
    
    def finalize_options(self):
        self.js_libs = self.distribution.js_libs
        self.js_storage = js_download_storage()
    
    def run(self):
        print('')
        i = 1
        
        for js_lib in list(self.js_libs):
            
            if not self.js_storage.downloaded(js_lib):
                
                print("retrieving %s" % js_lib)
                js_dl = self.js_storage.download(js_lib,
                    content_type='application/javascript')
                
                self.js_storage.safely_move(
                    js_dl,
                    "%s-%s" % (i, js_dl.name),
                    clobber=True)
                i += 1
            
            else:
                print("already downloaded %s" % js_lib)
                print("up-to-date copy in %s" % self.js_storage.downloaded(js_lib))


class uglify(Command):

    outdir = None
    user_options = [
        ('uglifyjs=', 'U',
            'use uglifyjs command (default: {0})'.format(uglification_cmd())),
        ('pedantic', 'P',
            'emit uglifyjs debug-level trace messages during the uglification.')]
    description = 'Uglification: concatenate generated and library JavaScript, '
    description += 'and compress the remainder'
    
    def initialize_options(self):
        uglify.indir = coffeescript_build_out_dir()
        uglify.mezzodir = uglification_build_mezzo_dir()
        uglify.outdir = uglification_build_out_dir()
        
        if not exists(uglify.mezzodir):
            makedirs(uglify.mezzodir)
        if not exists(uglify.outdir):
            makedirs(uglify.outdir)
        
        uglify.reeturn = """
        
        """
        self.pretty_files = []
        self.pretty_store = None
        self.pretty_libs = []
        self.catty_files = []
        self.uglifier = None

    def finalize_options(self):
        
        # `pretty_files` -- not yet uglified -- are created by the `build_coffeescript` extension.
        # They are JavaScript source analogues produced by the `coffee` compilation command;
        # they have the same name as their pre-translation counterparts save for their `.js` suffix.
        self.pretty_files = map(
            lambda pn: join(uglify.indir, pn),
            map(basename,
                map(lambda fn: fn.replace('.coffee', '.js'),
                    self.distribution.cs_files)))
        
        # `pretty_libs` are also fresh-faced and young, free of the repugnant morphological grotesqueries
        # contemporary JavaScript must endure -- as served straight from the internets by `download_js_libs`.
        # PROTIP: Don't use precompressed libraries... we want 'em ugly of course, but double-stuffing
        # JS code all willy-nilly will yield assuredly disgusting shit of like an Octomom-porn magnatude.
        self.pretty_store = js_download_storage()
        self.pretty_libs = map(self.pretty_store.path,
            filter(lambda fn: fn.endswith('.js'),
                self.pretty_store.listdir('')[-1]))
        
        # catty_files are just what the name implies: the `pretty_files` content, concattylated [sic]
        # with the libraries. At the moment this process works like so: each of the libraries whose URLs
        # you've enumerated in the iterable you passed to your `setup()` call, via the `js_libs` kwarg,
        # are combined -- *in order* as specified; JavaScript code emitted from CoffeeScript compilation
        # is added at the end. The order-preservation is for safety's sake, as are the line breaks that
        # get stuck in between each con-cat-tylated [sic] code block... Overkill, really, to take such
        # precations, I mean, it's 2012. Right? So there's no real valid reason why, like, any of that
        # should matter, cuz all your code is properly encapsulated, e.g. with anonymous function wraps
        # and nary a whiff of let's call it global SCOPE-TAINT.* But what do I know, maybe you're siccing
        # these build extensions on some crazy legacy codebase full of w3schools.com copypasta, or some
        # shit like that. I've had the displeasure of both contributing to and extricating myself from
        # a variety of such projects, in my years of computering, so I am totally happy to help out any
        # users of this project who find themselves in a vexing mire of illegibly paleolithic JavaScript.
        # Erm. So, anyway. The upshot is that the `catty_files` are simple intermediates; hence this is
        # a list of dangling lexical references to not-yet-existent files, the names of which are based on
        # the source filenames of the CoffeeScript from which they originated.
        self.catty_files = map(
            lambda pn: join(uglify.mezzodir, pn),
            map(basename,
                map(lambda fn: fn.replace('.coffee', '.libs.js'),
                    self.distribution.cs_files)))
        
        # `ugly_files` are the `uglify` command's final output -- since the files do not exist yet,
        # at this point in the build's arc we will populate this list with the output filenames only
        # (versus filesystem-absolute pathnames, which is what is in the others).
        self.ugly_files = map(basename,
            map(lambda fn: fn.replace('.coffee', '.libs.min.js'),
                self.distribution.cs_files))
        
        # `uglifier` is a string, containing the command we'll use when invoking UglifyJS,
        # during the actual JavaScript-uglification process.
        self.uglifier = uglification_cmd()

    def run(self):
        print('')
        
        print("prepending libraries to generated code")
        print("\t- %1s post-CoffeeScript JS files" % len(self.pretty_files))
        print("\t- %1s downloaded JS libraries" % len(self.pretty_libs))
        
        print('')
        
        # Concatinate the libraries first while prepending that amalgamated datum
        # onto each post-CoffeeScript block of generated JS.
        for pretty, catty in zip(
            list(self.pretty_files),
            list(self.catty_files)):
            
            pretties = list(self.pretty_libs)
            pretties.append(pretty)
            catastrophe = self.catinate(pretties)
            
            self.cathole(catastrophe,
                catty, clobber=True)
            print("\t> %10sb wrote to %s" % (len(catastrophe), catty))
        
        print('')
        
        print('uglifying concatenated modules...')
        
        for catter, gross in zip(
            list(self.catty_files),
            list(self.ugly_files)):
            self.grossitate(catter, gross)

    def cathole(self, do_what, where_exactly, clobber=True):
        """ A cathole is where you shit when you're in the woods; relatedly,
        the `uglify.cathole()` method dumps to a file -- Dude. I mean, I never
        said I'm like fucking Shakespeare or whatevs. Ok. """
        if exists(where_exactly) and not clobber:
            raise IOError("*** can't concatinate into %s: file already exists")
        
        if not bool(do_what) or len(do_what) < 10:
            raise ValueError("*** can't write <10b into %s: not enough data")
        
        with open(where_exactly, 'wb') as cat:
            cat.write(do_what)
            cat.flush()
        return

    def catinate(self, *js_files):
        global reeturn
        catout = ""
        for catin in list(*js_files):
            with open(catin, 'rb') as cat:
                catout += cat.read()
            catout += uglify.reeturn
        return catout

    def grossitate(self, in_file, out_filename):
        ''' cat %s | /usr/local/bin/uglifyjs > %s '''
        
        spawn([self.uglifier,
            '--verbose', '--no-copyright',
            '--unsafe', '--lift-vars',
            '-o', join(uglify.outdir, out_filename),
            '-c', in_file])




# * Not to be confused with TAINT-SCOPE, the verenable OTC topical relief for anytime use, whenever
#   the gum disease gingivitis gets all up underneath your balls and/or labia and brushing alone
#   isn't enough. Don't be that guy who mixes them up. You know that guy -- the guy talking about
#   "taint scope" at code review. Nobody eats with that guy or offers him meaningful eye contact.


########NEW FILE########
__FILENAME__ = dist
from distutils.dist import Distribution

class SQDistribution(Distribution):
    def __init__(self, attrs=None):
        self.js_package = None
        self.cs_files = None
        self.js_outdirs = None
        self.js_libs = None
        Distribution.__init__(self, attrs)

########NEW FILE########
__FILENAME__ = downloads

from __future__ import print_function
import sys

try:
    from django.conf import settings
except ImportError:
    print("build_js can't run without Django",
        file=sys.stderr)
else:
    if not settings.configured:
        print("build_js running with default Django settings",
            file=sys.stdout)
        settings.configure(**dict())
    else:
        print("build_js running with settings from an existing Django config",
            file=sys.stdout)

import mimetypes
from os.path import dirname
from urlobject import URLObject as URL

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.core.files.move import file_move_safe
from django.utils._os import safe_join

class URLRequestFile(SimpleUploadedFile):
    
    DEFAULT_TYPE = 'text/plain'
    
    def __init__(self, url, filename, **kwargs):
        """ A URLRequestFile is created with a URL and a filename.
        The data from the URL is immediately fetched when one constructs
        a new URLRequestFile object -- exceptions are thrown in
        the event of failure. """
        import requests
        
        self._source_url = url
        
        try:
            request = requests.get(url)
        except (
            requests.exceptions.TooManyRedirects,
            requests.exceptions.ConnectionError,
            requests.exceptions.SSLError,
            requests.exceptions.Timeout), err:
            print("*** Couldn't save %s to a file" % url,
                file=sys.stderr)
            print("*** (%s)" % err,
                file=sys.stderr)
            content = ''
        else:
            content = request.ok and request.content or ''
        
        content_type = request.ok and \
            request.headers.get('content-type') or \
            kwargs.pop('content_type',
                URLRequestFile.DEFAULT_TYPE)
        
        self._source_content_type = content_type
        self._source_encoding = request.ok and request.encoding or None
        
        super(URLRequestFile, self).__init__(
            filename, content, content_type)
        self.charset = self._source_encoding
    
    @property
    def source_url(self):
        return getattr(self, '_source_url', None)
    
    @property
    def source_content_type(self):
        return getattr(self, '_source_content_type', None)
    
    @property
    def source_encoding(self):
        return getattr(self, '_source_encoding', None)
    
    @property
    def source_charset(self):
        return self.source_encoding


class URLRetrievalStorage(FileSystemStorage):
    
    DEFAULT_EXT = '_noext.txt'
    MINIMUM_BYTE_SIZE = 10
    
    def _extension(self, mime_type=DEFAULT_EXT):
        """ Get the common-law file extension for a given MIME type."""
        exts = mimetypes.guess_all_extensions(mime_type)
        if '.jpe' in exts:
            exts.remove('.jpe') # WHO USES THAT.
        ext = bool(exts) and \
            exts[0] or \
            URLRetrievalStorage.DEFAULT_EXT
        return ext
    
    def download(self, urlstr, **kwargs):
        """ Call url_rs.download('URL') to save that URL's contents
        into a new file within the storages' filesystem.
        Optionally setting the 'clobber' keyword to False will raise
        an exception before overwriting existing data.
        Any other keyword args are passed wholesale to URLRequestFile's
        constructor when the new file is saved locally. """
        import requests
        import socket
        
        url = URL(urlstr)
        clobber = bool(kwargs.pop('clobber', True))
        
        try:
            headstat = requests.head(url)
        except (
            requests.exceptions.TooManyRedirects,
            requests.exceptions.ConnectionError,
            requests.exceptions.SSLError,
            requests.exceptions.Timeout,
            socket.gaierror,
            socket.herror,
            socket.sslerror,
            socket.timeout), err:
            print("*** HTTP HEAD failed for %s" % url,
                file=sys.stderr)
            print("--- (%s)" % err,
                file=sys.stderr)
            return None
        
        ct = kwargs.pop('content_type',
            headstat.headers.get('content-type',
                URLRequestFile.DEFAULT_TYPE))
        if ';' in ct:
            ct = ct.split(';')[0]
        
        ext = self._extension(ct)
        fn = "%s%s" % (url.hash, ext)
        ff = URLRequestFile(url, fn, **kwargs)
        
        if self.exists(fn) and not clobber:
            raise IOError(
                "*** Can't overwrite existing file %s (clobber=%s)" % (fn, clobber))
        
        if ff.size < URLRetrievalStorage.MINIMUM_BYTE_SIZE:
            raise ValueError(
                "*** Bailing -- download's size smaller than MINIMUM_BYTE_SIZE: %sb" %
                    URLRequestFile.MINIMUM_BYTE_SIZE)
        
        self.save(fn, ff)
        return ff
    
    def downloaded(self, urlstr, path=None):
        """ We say that a remote file has been 'downloaded' to a local directory
        if we can spot the SHA1 of its URL inside exactly one local filename. """
        
        path = self.path(path or '')
        oneornone = filter(
            lambda fn: fn.find(URL(urlstr).hash) > -1,
            self.listdir(path)[-1])
        
        if len(oneornone) is 1:
            one = oneornone[0]
            return bool(self.size(one)) and self.path(one) or None
        return None
    
    def local_content_type(self, urlstr, path=None):
        """ Guess an existant local file's mimetype from its
        corresponding remote URL... it sounds circuitous I know. """
        if self.exists(self.downloaded(urlstr, path)):
            return mimetypes.guess_type(urlstr)
    
    def safely_rename(self, url_request_file, new_name, clobber=False):
        """ Pass a URLRequestFile, with a new filename, to move or rename. """
        new_path = safe_join(
            dirname(self.path(url_request_file.name)),
            new_name)
        
        file_move_safe(
            self.path(url_request_file.name),
            new_path,
            allow_overwrite=clobber)
        
        url_request_file.name = new_name
    
    safely_move = safely_rename


if __name__ == "__main__":
    from pprint import pformat
    import tempfile
    td = tempfile.mkdtemp()
    fs = URLRetrievalStorage(
        location=td, base_url='http://owls.com/discount')
    
    stuff_to_grab = (
        'http://objectsinspaceandtime.com/',
        'http://objectsinspaceandtime.com/index.html',
        'http://objectsinspaceandtime.com/css/fn_typography.css',
        'http://scs.viceland.com/int/v17n11/htdocs/bright-lights-591/it-s-over.jpg',
        'http://yo-dogggggg.com/i-dont-exist')
    
    print('> directory:', td)
    print('> storage:', fs)
    print('')
    
    for thing in stuff_to_grab:
        print('-' * 133)
        print('')
        
        print('\t +++ URL: %s' % thing)
        
        ff = fs.download(thing)
        success = bool(fs.downloaded(thing))
        
        print('\t +++ success: %s' % str(success))
        
        if success:
            print('\t +++ local content/type (guess): %s' % fs.local_content_type(thing)[0])
            if ff is not None:
                print('\t +++ file object: %s' % ff)
                print('\t +++ path:', fs.path(ff.name))
                print('\t +++ FS url:', fs.url(ff.name))
                print('\t +++ orig URL:', ff.source_url)
                print('')
                print(pformat(ff.__dict__,
                    indent=8))
        
        print('')
    
    print('-' * 133)
    print('')
    
    yieldem = fs.listdir('')[-1]
    
    print('> fs.listdir(\'\')[-1] yields %s files:' % len(yieldem))
    print('')
    print(pformat(yieldem,
        indent=8))
    
    print('')
    print('')

########NEW FILE########
__FILENAME__ = settings

# blank Django settings file (irritatingly necessary to use its file API)
########NEW FILE########
__FILENAME__ = netloc
import urlparse


class Netloc(unicode):

    """
    A netloc string (``username:password@hostname:port``).

    Contains methods for accessing and (non-destructively) modifying those four
    components of the netloc. All methods return new instances.
    """

    def __repr__(self):
        return 'Netloc(%r)' % (unicode(self),)

    @classmethod
    def __unsplit(cls, username, password, hostname, port):
        """Put together a :class:`Netloc` from its constituent parts."""
        auth_string = u''
        if username:
            auth_string = username
            if password:
                auth_string += u':' + password
            auth_string += '@'
        port_string = u''
        if port is not None:
            port_string = u':%d' % port
        return cls(auth_string + hostname + port_string)

    @property
    def username(self):
        """The username portion of this netloc, or ``None``."""
        return self.__urlsplit.username

    def with_username(self, username):
        """Replace or add a username to this netloc."""
        return self.__replace(username=username)

    def without_username(self):
        """Remove any username (and password) from this netloc."""
        return self.without_password().with_username('')

    @property
    def password(self):
        """The password portion of this netloc, or ``None``."""
        return self.__urlsplit.password

    def with_password(self, password):

        """
        Replace or add a password to this netloc.

        Raises a ``ValueError`` if you attempt to add a password to a netloc
        with no username.
        """

        if password and not self.username:
            raise ValueError("Can't set a password on a netloc with no username")
        return self.__replace(password=password)

    def without_password(self):
        """Remove any password from this netloc."""
        return self.with_password('')

    @property
    def auth(self):
        """The username and password of this netloc as a 2-tuple."""
        return (self.username, self.password)

    def with_auth(self, username, *password):
        """Replace or add a username and password in one method call."""
        netloc = self.without_auth()
        if password:
            return netloc.with_username(username).with_password(*password)
        return netloc.with_username(username)

    def without_auth(self):
        return self.without_password().without_username()

    @property
    def hostname(self):
        """The hostname portion of this netloc."""
        return self.__urlsplit.hostname

    def with_hostname(self, hostname):
        """Replace the hostname on this netloc."""
        return self.__replace(hostname=hostname)

    @property
    def port(self):
        """The port number on this netloc (as an ``int``), or ``None``."""
        return self.__urlsplit.port

    def with_port(self, port):
        """Replace or add a port number to this netloc."""
        return self.__replace(port=port)

    def without_port(self):
        """Remove any port number from this netloc."""
        return self.__replace(port=None)

    @property
    def __urlsplit(self):
        return urlparse.SplitResult('', self, '', '', '')

    def __replace(self, **params):
        """Replace any number of components on this netloc."""
        unsplit_args = {'username': self.username,
                        'password': self.password,
                        'hostname': self.hostname,
                        'port': self.port}
        unsplit_args.update(params)
        return self.__unsplit(**unsplit_args)

########NEW FILE########
__FILENAME__ = path
# -*- coding: utf-8 -*-

import posixpath
import urllib
import urlparse


class Root(object):

    """A descriptor which always returns the root path."""

    def __get__(self, instance, cls):
        return cls('/')


class URLPath(unicode):

    root = Root()

    def __repr__(self):
        return 'URLPath(%r)' % (unicode(self),)

    @classmethod
    def join_segments(cls, segments, absolute=True):
        """Create a :class:`URLPath` from an iterable of segments."""
        path = cls('/')
        for segment in segments:
            path = path.add_segment(segment)
        return path

    @property
    def segments(self):
        """
        Split this path into (decoded) segments.

            >>> URLPath(u'/a/b/c').segments
            (u'a', u'b', u'c')

        Non-leaf nodes will have a trailing empty string, and percent encodes
        will be decoded:

            >>> URLPath(u'/a%20b/c%20d/').segments
            (u'a b', u'c d', u'')
        """
        segments = tuple(map(path_decode, self.split('/')))
        if segments[0] == u'':
            return segments[1:]
        return segments

    @property
    def parent(self):
        """
        The parent of this node.

            >>> URLPath(u'/a/b/c').parent
            URLPath(u'/a/b/')
            >>> URLPath(u'/foo/bar/').parent
            URLPath(u'/foo/')
        """
        if self.is_leaf:
            return self.relative('.')
        return self.relative('..')

    @property
    def is_leaf(self):
        """
        Is this path a leaf node?

            >>> URLPath(u'/a/b/c').is_leaf
            True
            >>> URLPath(u'/a/b/').is_leaf
            False
        """
        return self and self.segments[-1] != u''

    @property
    def is_relative(self):
        """
        Is this path relative?

            >>> URLPath(u'a/b/c').is_relative
            True
            >>> URLPath(u'/a/b/c').is_relative
            False
        """
        return self[0] != u'/'

    @property
    def is_absolute(self):
        """
        Is this path absolute?

            >>> URLPath(u'a/b/c').is_absolute
            False
            >>> URLPath(u'/a/b/c').is_absolute
            True
        """
        return self[0] == u'/'

    def relative(self, rel_path):
        """
        Resolve a relative path against this one.

            >>> URLPath(u'/a/b/c').relative('.')
            URLPath(u'/a/b/')
            >>> URLPath(u'/a/b/c').relative('d')
            URLPath(u'/a/b/d')
            >>> URLPath(u'/a/b/c').relative('../d')
            URLPath(u'/a/d')
        """
        return type(self)(urlparse.urljoin(self, rel_path))

    def add_segment(self, segment):
        u"""
        Add a segment to this path.

            >>> URLPath(u'/a/b/').add_segment('c')
            URLPath(u'/a/b/c')

        Non-ASCII and reserved characters (including slashes) will be encoded:

            >>> URLPath(u'/a/b/').add_segment(u'dé/f')
            URLPath(u'/a/b/d%C3%A9%2Ff')
        """
        return type(self)(posixpath.join(self, path_encode(segment)))

    def add(self, path):
        u"""
        Add a partial path to this one.

        The only difference between this and :meth:`add_segment` is that slash
        characters will not be encoded, making it suitable for adding more than
        one path segment at a time:

            >>> URLPath(u'/a/b/').add(u'dé/f/g')
            URLPath(u'/a/b/d%C3%A9/f/g')
        """
        return type(self)(posixpath.join(self, path_encode(path, safe='/')))


def path_encode(string, safe=''):
    return urllib.quote(string.encode('utf-8'), safe=safe)

def path_decode(string):
    return urllib.unquote(string).decode('utf-8')

########NEW FILE########
__FILENAME__ = ports
"""Default port numbers for the URI schemes supported by urlparse."""

DEFAULT_PORTS = {
    'ftp': 21,
    'gopher': 70,
    'hdl': 2641,
    'http': 80,
    'https': 443,
    'imap': 143,
    'mms': 651,
    'news': 2009,
    'nntp': 119,
    'prospero': 191,
    'rsync': 873,
    'rtsp': 554,
    'rtspu': 554,
    'sftp': 115,
    'shttp': 80,
    'sip': 5060,
    'sips': 5061,
    'snews': 2009,
    'svn': 3690,
    'svn+ssh': 22,
    'telnet': 23,
}

########NEW FILE########
__FILENAME__ = query_string
import collections
import re
import urllib
import urlparse


class QueryString(unicode):

    def __repr__(self):
        return 'QueryString(%r)' % (unicode(self),)

    @property
    def list(self):
        result = []
        if not self:
            # Empty string => empty list.
            return result

        name_value_pairs = re.split(r'[\&\;]', self)
        for name_value_pair in name_value_pairs:
            # Split the pair string into a naive, encoded (name, value) pair.
            name_value = name_value_pair.split('=', 1)
            # 'param=' => ('param', None)
            if len(name_value) == 1:
                name, value = name_value + [None]
            # 'param=value' => ('param', 'value')
            # 'param=' => ('param', '')
            else:
                name, value = name_value

            name = qs_decode(name)
            if value is not None:
                value = qs_decode(value)

            result.append((name, value))
        return result

    @property
    def dict(self):
        return dict(self.list)

    @property
    def multi_dict(self):
        result = collections.defaultdict(list)
        for name, value in self.list:
            result[name].append(value)
        return dict(result)

    def add_param(self, name, value):
        if value is None:
            parameter = qs_encode(name)
        else:
            parameter = qs_encode(name) + '=' + qs_encode(value)
        if self:
            return type(self)(self + '&' + parameter)
        return type(self)(parameter)

    def add_params(self, *args, **kwargs):
        params_list = get_params_list(*args, **kwargs)
        new = self
        for name, value in params_list:
            new = new.add_param(name, value)
        return new

    def del_param(self, name):
        params = [(n, v) for n, v in self.list if n != name]
        qs = type(self)('')
        for param in params:
            qs = qs.add_param(*param)
        return qs

    def set_param(self, name, value):
        return self.del_param(name).add_param(name, value)

    def set_params(self, *args, **kwargs):
        params_list = get_params_list(*args, **kwargs)
        new = self
        for name, value in params_list:
            new = new.set_param(name, value)
        return new

    def del_params(self, params):
        deleted = set(params)
        params = [(name, value) for name, value in self.list
                  if name not in deleted]
        qs = type(self)('')
        for param in params:
            qs = qs.add_param(*param)
        return qs


qs_encode = lambda s: urllib.quote(s.encode('utf-8'))
qs_decode = lambda s: urllib.unquote(str(s).replace('+', ' ')).decode('utf-8')


def get_params_list(*args, **kwargs):
    """Turn dict-like arguments into an ordered list of pairs."""
    params = []
    if args:
        if len(args) > 1:
            raise TypeError("Expected at most 1 arguments, got 2")
        arg = args[0]
        if hasattr(arg, 'items'):
            params.extend(arg.items())
        else:
            params.extend(list(arg))
    if kwargs:
        params.extend(kwargs.items())
    return params

########NEW FILE########
__FILENAME__ = urlobject

import urlparse
import hashlib
import mimetypes

from netloc import Netloc
from path import URLPath, path_encode, path_decode
from ports import DEFAULT_PORTS
from query_string import QueryString


class URLObject(unicode):

    """
    A URL.

    This class contains properties and methods for accessing and modifying the
    constituent components of a URL. :class:`URLObject` instances are
    immutable, as they derive from the built-in ``unicode``, and therefore all
    methods return *new* objects; you need to consider this when using
    :class:`URLObject` in your own code.
    """

    def __repr__(self):
        return 'URLObject(%r)' % (unicode(self),)

    @property
    def hash(self):
        return hashlib.sha1(self).hexdigest()
    
    @property
    def content_type(self):
        return mimetype.guess_type(self)

    @property
    def scheme(self):
        return urlparse.urlsplit(self).scheme
    def with_scheme(self, scheme):
        return self.__replace(scheme=scheme)

    @property
    def netloc(self):
        return Netloc(urlparse.urlsplit(self).netloc)
    def with_netloc(self, netloc):
        return self.__replace(netloc=netloc)

    @property
    def username(self):
        return self.netloc.username
    def with_username(self, username):
        return self.with_netloc(self.netloc.with_username(username))
    def without_username(self):
        return self.with_netloc(self.netloc.without_username())

    @property
    def password(self):
        return self.netloc.password
    def with_password(self, password):
        return self.with_netloc(self.netloc.with_password(password))
    def without_password(self):
        return self.with_netloc(self.netloc.without_password())

    @property
    def hostname(self):
        return self.netloc.hostname
    def with_hostname(self, hostname):
        return self.with_netloc(self.netloc.with_hostname(hostname))

    @property
    def port(self):
        return self.netloc.port
    def with_port(self, port):
        return self.with_netloc(self.netloc.with_port(port))
    def without_port(self):
        return self.with_netloc(self.netloc.without_port())

    @property
    def auth(self):
        return self.netloc.auth
    def with_auth(self, *auth):
        return self.with_netloc(self.netloc.with_auth(*auth))
    def without_auth(self):
        return self.with_netloc(self.netloc.without_auth())

    @property
    def default_port(self):
        """
        The destination port number for this URL.

        If no port number is explicitly given in the URL, this will return the
        default port number for the scheme if one is known, or ``None``. The
        mapping of schemes to default ports is defined in
        :const:`urlobject.ports.DEFAULT_PORTS`.
        """
        port = urlparse.urlsplit(self).port
        if port is not None:
            return port
        return DEFAULT_PORTS.get(self.scheme)

    @property
    def path(self):
        return URLPath(urlparse.urlsplit(self).path)
    def with_path(self, path):
        return self.__replace(path=path)

    @property
    def root(self):
        return self.with_path('/')

    @property
    def parent(self):
        return self.with_path(self.path.parent)

    @property
    def is_leaf(self):
        return self.path.is_leaf

    def add_path_segment(self, segment):
        return self.with_path(self.path.add_segment(segment))

    def add_path(self, partial_path):
        return self.with_path(self.path.add(partial_path))

    @property
    def query(self):
        return QueryString(urlparse.urlsplit(self).query)
    def with_query(self, query):
        return self.__replace(query=query)
    def without_query(self):
        return self.__replace(query='')

    @property
    def query_list(self):
        return self.query.list

    @property
    def query_dict(self):
        return self.query.dict

    @property
    def query_multi_dict(self):
        return self.query.multi_dict

    def add_query_param(self, name, value):
        return self.with_query(self.query.add_param(name, value))
    def add_query_params(self, *args, **kwargs):
        return self.with_query(self.query.add_params(*args, **kwargs))

    def set_query_param(self, name, value):
        return self.with_query(self.query.set_param(name, value))
    def set_query_params(self, *args, **kwargs):
        return self.with_query(self.query.set_params(*args, **kwargs))

    def del_query_param(self, name):
        return self.with_query(self.query.del_param(name))
    def del_query_params(self, params):
        return self.with_query(self.query.del_params(params))

    @property
    def fragment(self):
        return path_decode(urlparse.urlsplit(self).fragment)
    def with_fragment(self, fragment):
        return self.__replace(fragment=path_encode(fragment))
    def without_fragment(self):
        return self.__replace(fragment='')

    def relative(self, other):
        """Resolve another URL relative to this one."""
        # Relative URL resolution involves cascading through the properties
        # from left to right, replacing
        other = type(self)(other)
        if other.scheme:
            return other
        elif other.netloc:
            return other.with_scheme(self.scheme)
        elif other.path:
            return other.with_scheme(self.scheme).with_netloc(self.netloc) \
                    .with_path(self.path.relative(other.path))
        elif other.query:
            return other.with_scheme(self.scheme).with_netloc(self.netloc) \
                    .with_path(self.path)
        elif other.fragment:
            return other.with_scheme(self.scheme).with_netloc(self.netloc) \
                    .with_path(self.path).with_query(self.query)
        # Empty string just removes fragment; it's treated as a path meaning
        # 'the current location'.
        return self.without_fragment()

    def __replace(self, **replace):
        """Replace a field in the ``urlparse.SplitResult`` for this URL."""
        return type(self)(urlparse.urlunsplit(
            urlparse.urlsplit(self)._replace(**replace)))


if not hasattr(urlparse, 'ResultMixin'):
    def _replace(split_result, **replace):
        return urlparse.SplitResult(
            **dict((attr, replace.get(attr, getattr(split_result, attr)))
                for attr in ('scheme', 'netloc', 'path', 'query', 'fragment')))
    urlparse.BaseResult._replace = _replace
    del _replace

########NEW FILE########
__FILENAME__ = xwhich

from os import environ, access, pathsep, X_OK
from os.path import exists, isdir, split, join

is_exe = lambda fpth: exists(fpth) and access(fpth, X_OK)

def xwhich(program, also_look=[]):
    """ UNIX `which` analogue. Derived from:
        https://github.com/amoffat/pbs/blob/master/pbs.py#L95) """
    fpath, fname = split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        paths = environ["PATH"].split(pathsep)
        try:
            paths += list(also_look)
        except (TypeError, ValueError):
            pass
        for path in paths:
            exe_file = join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def which(program):
    return xwhich(program)


if __name__ == '__main__':
    programs_to_try = (
        'python',
        'ls',
        'wget',
        'curl',
        'coffee',
        'lessc',
        'yo-dogg',
    )
    
    ali = [join(pth,
        'coffee-script', 'bin') for pth in environ['NODE_PATH'].split(':') if bool(
            len(pth)) and isdir(pth)]
    
    for p in programs_to_try:
        print "\t %20s --> %s" % (("which('%s')" % p), xwhich(p, also_look=ali))
    
            
########NEW FILE########
__FILENAME__ = admin
import os
from django.contrib import admin
from signalqueue.utils import SQ_ROOT

admin.site.index_template = os.path.join(SQ_ROOT, 'templates/admin/index_with_queues.html')
admin.site.app_index_template = os.path.join(SQ_ROOT, 'templates/admin/app_index.html')

import signalqueue.models
admin.site.register(signalqueue.models.EnqueuedSignal)

########NEW FILE########
__FILENAME__ = dispatcher
#!/usr/bin/env python
# encoding: utf-8
"""
dispatch.py

Created by FI$H 2000 on 2011-09-09.
Copyright (c) 2011 Objects In Space And Time, LLC. All rights reserved.

"""
from django.dispatch import Signal

class AsyncSignal(Signal):
    
    regkey = None
    name = None
    runmode = None
    
    queue_name = None
    mapping = None
    
    def __init__(self, providing_args=None, queue_name='default'):
        from signalqueue import mappings
        
        self.queue_name = queue_name
        self.mapping = mappings.MapperToPedigreeIndex()
        just_the_args = []
        
        if isinstance(providing_args, dict):
            for providing_arg, MappingCls in providing_args.items():
                just_the_args.append(providing_arg)
            self.mapping.update(providing_args)
        
        else: # list, iterable, whatev.
            just_the_args.extend(providing_args)
        
        super(AsyncSignal, self).__init__(providing_args=just_the_args)
    
    def send_now(self, sender, **named):
        return super(AsyncSignal, self).send(sender=sender, **named)
    
    def enqueue(self, sender, **named):
        from signalqueue import SQ_RUNMODES as runmodes
        if self.runmode == runmodes['SQ_SYNC']:
            from signalqueue import SignalDispatchError
            raise SignalDispatchError("WTF: enqueue() called in SQ_SYNC mode")
        
        from signalqueue.worker import queues
        return queues[self.queue_name].enqueue(self, sender=sender, **named)
    
    def send(self, sender, **named):
        from signalqueue import SQ_RUNMODES as runmodes
        from signalqueue.worker import queues
        from signalqueue.utils import logg
        
        self.runmode = int(named.pop('runmode', queues._runmode))
        
        #logg.debug("--- send() called, runmode = %s" % self.runmode)
        
        if self.runmode:
            
            if self.runmode == runmodes['SQ_ASYNC_REQUEST']:
                # it's a web request -- enqueue it
                return self.enqueue(sender, **named)
            
            elif self.runmode == runmodes['SQ_ASYNC_DAEMON']:
                # signal sent in daemon mode -- enqueue it
                return self.enqueue(sender, **named)
            
            elif self.runmode == runmodes['SQ_ASYNC_MGMT']:
                # signal sent in command mode -- fire away
                return self.send_now(sender, **named)
            
            elif self.runmode == runmodes['SQ_SYNC']:
                # fire normally
                return self.send_now(sender, **named)
            
            else:
                # unknown runmode value -- fire normally
                logg.info(
                    "*** send() called with an unknown runmode: '%s' -- firing sync signal." % self.runmode)
                return self.send_now(sender, **named)
        else:
            # fire normally
            logg.info("*** send() called and no runmode configured -- firing sync signal.")
            return self.send_now(sender, **named)

    
########NEW FILE########
__FILENAME__ = dequeue
#!/usr/bin/env python
# encoding: utf-8
import sys, os
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
#from pprint import pformat
from optparse import make_option

from . import echo_banner

class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
        make_option('--queuename', '-n', dest='queue_name', default='default',
            help="Name of queue, as specified in settings.py (defaults to 'default')",
        ),
    )
    
    help = ('Flushes a signal queue, executing all enqueued signals.')
    requires_model_validation = True
    can_import_settings = True
    
    def handle(self, *args, **options):
        import signalqueue
        signalqueue.autodiscover()
        echo_banner()
        try:
            return self.flush_signal_queue(args, options)
        except ImproperlyConfigured, err:
            self.echo("*** ERROR in configuration: %s" % err)
            self.echo("*** Check the signalqueue-related options in your settings.py.")
    
    def echo(self, *args, **kwargs):
        """ Print in color to stdout. """
        text = " ".join([str(item) for item in args])
        DEBUG = False
        
        if DEBUG:
            color = kwargs.get("color",32)
            self.stdout.write("\033[0;%dm%s\033[0;m" % (color, text))
        
        else:
            print text
    
    def flush_signal_queue(self, apps, options):
        """
        Flushes the named signal queue, executing all enqueued signals.
        
        """
        from django.conf import settings
        from signalqueue import SQ_RUNMODES as runmodes
        from signalqueue.worker import backends
        
        queue_name = options.get('queue_name')
        queues = backends.ConnectionHandler(settings.SQ_QUEUES, runmodes['SQ_ASYNC_MGMT'])
        
        if not queue_name in queues:
            self.echo("\n--- No definition found for a queue named '%s'" % (queue_name,), color=16)
            self.echo("\n--- Your defined queues have these names: '%s'" % ("', '".join(queues.keys()),), color=16)
            self.echo("\n>>> Exiting ...\n\n", color=16)
            sys.exit(2)
        
        queue = queues[queue_name]
        
        try:
            queue_available = queue.ping()
        except:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (queue.__class__.__name__, queue_name), color=16)
            self.echo("\n--- Is the server running?", color=16)
            self.echo("\n>>> Exiting ...\n\n", color=16)
            sys.exit(2)
        
        if not queue_available:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (queue.__class__.__name__, queue_name), color=16)
            self.echo("\n--- Is the server running?", color=16)
            self.echo("\n>>> Exiting ...\n\n", color=16)
            sys.exit(2)
        
        self.echo("\n>>> Flushing signal queue '%s' -- %s enqueued signals total" % (
            queue.queue_name, queue.count()), color=31)
        
        from django.db.models.loading import cache
        if queue.count() > 0:
            for signalblip in queue:
                #self.echo("\n>>> Signal: ", color=31)
                #self.echo("\n%s" % pformat(signalblip), color=31)
                
                sender_dict = signalblip.get('sender')
                sender = cache.get_model(str(sender_dict['app_label']), str(sender_dict['modl_name']))
                signal = signalblip.get('signal')
                
                self.echo(">>> Processing signal sent by %s.%s: %s.%s" % (
                    sender._meta.app_label, sender.__name__, signal.keys()[0], signal.values()[0]), color=31)
                
                queue.dequeue(queued_signal=signalblip)
        
        self.echo(">>> Done flushing signal queue '%s' -- %s enqueued signals remaining" % (
            queue.queue_name, queue.count()), color=31)
        self.echo("\n")


########NEW FILE########
__FILENAME__ = dumpqueue
#!/usr/bin/env python
# encoding: utf-8
import sys, os
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
#from pprint import pformat
from optparse import make_option

from . import echo_banner

class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
        make_option('--queuename', '-n', dest='queue_name', default='default',
            help="Name of queue, as specified in settings.py (defaults to 'default')",
        ),
        make_option('--indent', '-t', dest='indent', default='0',
            help="Levels to indent the output.",
        ),
    )
    
    help = ('Dumps the contents of a signal queue to a serialized format.')
    requires_model_validation = True
    can_import_settings = True
    
    def handle(self, *args, **options):
        echo_banner()
        try:
            return self.dump_queue(args, options)
        except ImproperlyConfigured, err:
            self.echo("*** ERROR in configuration: %s" % err)
            self.echo("*** Check the signalqueue-related options in your settings.py.")
    
    def echo(self, *args, **kwargs):
        """ Print in color to stdout. """
        text = " ".join([str(item) for item in args])
        DEBUG = False
        
        if DEBUG:
            color = kwargs.get("color",32)
            self.stdout.write("\033[0;%dm%s\033[0;m" % (color, text))
        
        else:
            print text
    
    def dump_queue(self, apps, options):
        from django.conf import settings
        from signalqueue import SQ_RUNMODES as runmodes
        from signalqueue.worker import backends
        import json as library_json
        
        queue_name = options.get('queue_name')
        indent = int(options.get('indent'))
        queues = backends.ConnectionHandler(settings.SQ_QUEUES, runmodes['SQ_ASYNC_MGMT'])
        
        if not queue_name in queues:
            self.echo("\n--- No definition found for a queue named '%s'" % queue_name,
                color=16)
            self.echo("\n--- Your defined queues have these names: '%s'" % (
                "', '".join(queues.keys()),),
                color=16)
            self.echo("\n>>> Exiting ...\n\n",
                color=16)
            sys.exit(2)
        
        queue = queues[queue_name]
        
        try:
            queue_available = queue.ping()
        except:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (
                queue.__class__.__name__, queue_name),
                color=16)
            self.echo("\n--- Is the server running?",
                color=16)
            self.echo("\n>>> Exiting ...\n\n",
                color=16)
            sys.exit(2)
        
        if not queue_available:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (
                queue.__class__.__name__, queue_name),
                color=16)
            self.echo("\n--- Is the server running?",
                color=16)
            self.echo("\n>>> Exiting ...\n\n",
                color=16)
            sys.exit(2)
        
        queue_json = repr(queue)
        
        if indent > 0:
            queue_out = library_json.loads(queue_json)
            print library_json.dumps(queue_out, indent=indent)
        else:
            print queue_json
########NEW FILE########
__FILENAME__ = purgequeue
#!/usr/bin/env python
# encoding: utf-8
import sys
from django.core.management.base import BaseCommand
from django.core.exceptions import ImproperlyConfigured
#from pprint import pformat
from optparse import make_option

from . import echo_banner

class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
        make_option('--queuename', '-n', dest='queue_name', default='default',
            help="Name of queue, as specified in settings.py (defaults to 'default')",
        ),
    )
    
    help = ('Purges everything from a queue, deleting all signals.')
    requires_model_validation = True
    can_import_settings = True
    
    def handle(self, *args, **options):
        import signalqueue
        signalqueue.autodiscover()
        echo_banner()
        try:
            return self.purge_signal_queue(args, options)
        except ImproperlyConfigured, err:
            self.echo("*** ERROR in configuration: %s" % err)
            self.echo("*** Check the signalqueue-related options in your settings.py.")
    
    def echo(self, *args, **kwargs):
        """ Print in color to stdout. """
        text = " ".join([str(item) for item in args])
        DEBUG = False
        
        if DEBUG:
            color = kwargs.get("color",32)
            self.stdout.write("\033[0;%dm%s\033[0;m" % (color, text))
        
        else:
            print text
    
    def purge_signal_queue(self, apps, options):
        """ Purges all signals from the queue. """
        from django.conf import settings
        from signalqueue import SQ_RUNMODES as runmodes
        from signalqueue.worker import backends
        
        queue_name = options.get('queue_name')
        queues = backends.ConnectionHandler(settings.SQ_QUEUES, runmodes['SQ_ASYNC_MGMT'])
        
        if not queue_name in queues:
            self.echo("\n--- No definition found for a queue named '%s'" % (queue_name,), color=16)
            self.echo("\n--- Your defined queues have these names: '%s'" % ("', '".join(queues.keys()),), color=16)
            self.echo("\n>>> Exiting ...\n\n", color=16)
            sys.exit(2)
        
        queue = queues[queue_name]
        
        try:
            queue_available = queue.ping()
        except:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (queue.__class__.__name__, queue_name), color=16)
            self.echo("\n--- Is the server running?", color=16)
            self.echo("\n>>> Exiting ...\n\n", color=16)
            sys.exit(2)
        
        if not queue_available:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (queue.__class__.__name__, queue_name), color=16)
            self.echo("\n--- Is the server running?", color=16)
            self.echo("\n>>> Exiting ...\n\n", color=16)
            sys.exit(2)
        
        self.echo("\n>>> Purging signals in queue '%s' -- %s enqueued signals total" % (
            queue.queue_name, queue.count()), color=31)
        
        from django.db.models.loading import cache
        if queue.count() > 0:
            for signalblip in queue:
                #self.echo("\n>>> Signal: ", color=31)
                #self.echo("\n%s" % pformat(signalblip), color=31)
                
                sender_dict = signalblip.get('sender')
                sender = cache.get_model(str(sender_dict['app_label']), str(sender_dict['modl_name']))
                signal = signalblip.get('signal')
                
                self.echo(">>> Purging signal sent by %s.%s: %s.%s" % (
                    sender._meta.app_label, sender.__name__, signal.keys()[0], signal.values()[0]), color=31)
        
        self.echo(">>> Done purging signals in queue '%s' -- %s enqueued signals remaining" % (
            queue.queue_name, queue.count()), color=31)
        self.echo("\n")


########NEW FILE########
__FILENAME__ = runqueueserver
#!/usr/bin/env python
# encoding: utf-8
import sys, os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
from optparse import make_option

from . import echo_banner


class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
        make_option('--queuename', '-n', dest='queue_name',
            default='default',
            help="Name of the queue as defined in settings.py",
        ),
        make_option('--halt-when-exhausted', '-H', action='store_true', dest='halt_when_exhausted',
            default=False,
            help="Halt the queue worker once the queue has been exhausted",
        ),
        make_option('--no-exit', '-N', action='store_false', dest='exit',
            default=True,
            help="Don't call sys.exit() when halting",
        ),
        make_option('--disable-exception-logging', '-x', action='store_false', dest='log_exceptions',
            default=True,
            help="Disable the Sentry exception log.",
        ),
    )
    
    help = ('Runs the Tornado-based queue worker.')
    args = '[optional port number, or ipaddr:port]'
    can_import_settings = True
    exit_when_halting = True
    
    def echo(self, *args, **kwargs):
        """ Print in color to stdout. """
        text = " ".join([str(item) for item in args])
        
        if settings.DEBUG:
            color = kwargs.get("color", 32)
            self.stdout.write("\033[0;%dm%s\033[0;m" % (color, text))
        else:
            print text
    
    def exit(self, status=2):
        """ Exit when complete. """
        self.echo("+++ Exiting ...\n", color=16)
        if self.exit_when_halting:
            sys.exit(status)

    def run_worker(self, args, options):
        """ Runs the Tornado-based queue worker. """
        import tornado.options
        from tornado.httpserver import HTTPServer
        from tornado.ioloop import IOLoop
        from signalqueue.worker.vortex import Application
        from signalqueue.worker import backends
        import signalqueue
        
        queue_name = options.get('queue_name')
        queues = backends.ConnectionHandler(settings.SQ_QUEUES, signalqueue.SQ_RUNMODES['SQ_ASYNC_MGMT'])
        queue = queues[queue_name]
        
        try:
            queue_available = queue.ping()
        except:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (queue.__class__.__name__, queue_name), color=16)
            self.echo("\n--- Is the server running?", color=16)
            self.exit(2)
        
        if not queue_available:
            self.echo("\n--- Can't ping the backend for %s named '%s'" % (queue.__class__.__name__, queue_name), color=16)
            self.echo("\n--- Is the server running?", color=16)
            self.exit(2)
        
        http_server = HTTPServer(Application(queue_name=queue_name,
            halt_when_exhausted=options.get('halt_when_exhausted', False),
            log_exceptions=options.get('log_exceptions', True),
        ))
        
        http_server.listen(int(options.get('port')), address=options.get('addr'))
        
        try:
            IOLoop.instance().start()
        
        except KeyboardInterrupt:
            self.echo("Shutting down signal queue worker ...", color=31)
    
    def handle(self, addrport='', *args, **options):
        """ Handle command-line options. """
        echo_banner()
        
        if args:
            raise CommandError('Usage: %s %s' % (__file__, self.args))
        
        self.exit_when_halting = options.get('exit', True)
        
        if not addrport:
            addr = ''
            port = str(settings.SQ_WORKER_PORT) or '8088'
        else:
            try:
                addr, port = addrport.split(':')
            except ValueError:
                addr, port = '', addrport
        
        if not addr:
            addr = '127.0.0.1'
        
        if not port.isdigit():
            raise CommandError("%r is not a valid port number." % port)
        
        self.quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'
        options.update({
            'addr': addr,
            'port': port,
        })
        
        self.echo("Validating models...")
        self.validate(display_num_errors=True)
        
        self.echo(("\nDjango version %(version)s, using settings %(settings)r\n"
            "Tornado worker for queue \"%(queue_name)s\" binding to http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n" ) % {
                "version": self.get_version(),
                "settings": settings.SETTINGS_MODULE,
                "queue_name": options.get('queue_name'),
                "addr": addr,
                "port": port,
                "quit_command": self.quit_command,
            })
        
        try:
            self.run_worker(args, options)
        
        except ImproperlyConfigured, err:
            self.echo("*** ERROR in configuration: %s" % err, color=31)
            self.echo("*** Check the signalqueue options in your settings.py.", color=31)
        
        finally:
            self.exit(0)

########NEW FILE########
__FILENAME__ = mappings

from __future__ import print_function
from collections import defaultdict

def who_calls():
    try:
        import sys
        return sys._getframe(1).f_code.co_name
    except (ValueError, AttributeError):
        return "I was never given a name."

by_priority = defaultdict(lambda: set())

class Mappers(type):
    def __new__(cls, name, bases, attrs):
        global by_priority
        outcls = super(Mappers, cls).__new__(cls, name, bases, attrs)
        if name is not 'Mapper':
            by_priority[attrs.get('PRIORITY', "normal")].add(outcls)
        return outcls

class Mapper(object):
    
    __metaclass__ = Mappers
    
    PRIORITY = "normal"
    
    """ Maybe I will make these singletons.
        Then, when they're all singly alone,
        I can get dressed up like global state
        and jump out in front of them like, 
                                            
                    !*** BOO ***!           
                                            
        which they never expect that shit, haha,
        nerd alert. """
    
    @classmethod
    def demap(cls, signal_arg):
        ''' serialize an argument. '''
        
        who = who_calls()
        raise NotImplementedError(
            '%s subclasses need to define %s()' % (
                cls.__name__, who))
    
    @classmethod
    def remap(cls, intermediate): # unserialize
        ''' un-serialize an argument from a provided
            intermediate representation. '''
        
        who = who_calls()
        raise NotImplementedError(
            '%s subclasses need to define %s()' % (
                cls.__name__, who))
    
    @classmethod
    def can_demap(cls, test_value):
        try:
            cls.demap(test_value)
        except NotImplementedError, exc:
            import sys
            raise NotImplementedError, exc, sys.exc_info()[2]
        except Exception:
            return False
        return True
    
    @classmethod
    def can_remap(cls, test_value):
        try:
            cls.remap(test_value)
        except NotImplementedError, exc:
            import sys
            raise NotImplementedError, exc, sys.exc_info()[2]
        except Exception:
            return False
        return True


class LiteralValueMapper(Mapper):
    """ Python primitive types e.g. bool, int, str;
        also list, dict & friends -- once it exists,
        this mapper class will be using Base64-encoded,
        compressed JSON as its intermediate form. """
    
    DEMAP_TYPES = (
        bool, int, long, float,
        str, unicode,
        list, dict)
    PRIORITY = "penultimate"
    
    @classmethod
    def json(cls):
        if not hasattr(cls, '_json'):
            from signalqueue.utils import json
            cls._json = json
        return cls._json
    
    @classmethod
    def base64(cls):
        if not hasattr(cls, '_base64'):
            import base64
            cls._base64 = base64
        return cls._base64
    
    @classmethod
    def demap(cls, signal_arg):
        return cls.base64().encodestring(
            cls.json().dumps(
                signal_arg))
    
    @classmethod
    def remap(cls, intermediate):
        return cls.json().loads(
            cls.base64().decodestring(
                intermediate))
    
    @classmethod
    def can_demap(cls, test_value):
        if type(test_value) not in cls.DEMAP_TYPES:
            return False
        try:
            ir = cls.demap(test_value)
            rt = cls.remap(ir)
        except Exception:
            return False
        return (repr(test_value) == repr(rt))
    
    @classmethod
    def can_remap(cls, test_value):
        try:
            rt = cls.remap(test_value)
        except Exception:
            return False
        return (type(rt) in cls.DEMAP_TYPES)

class PickleMapper(Mapper):
    """ Miscellaneous other objects -- see the `pickle`
        module documentation for details about what can
        be pickled. """
    
    PICKLE_PROTOCOL = 1
    PRIORITY = "ultimate"
    
    @classmethod
    def brine(cls):
        if not hasattr(cls, '_brine'):
            try:
                import cPickle
            except ImportError:
                import pickle
                cls._brine = pickle
            else:
                cls._brine = cPickle
        return cls._brine
    
    @classmethod
    def demap(cls, signal_arg):
        return cls.brine().dumps(signal_arg,
            cls.PICKLE_PROTOCOL)
    
    @classmethod
    def remap(cls, intermediate):
        return cls.brine().loads(str(intermediate))
    
    @classmethod
    def can_demap(cls, test_value):
        try:
            cls.demap(test_value)
        except Exception:
            return False
        return True
    
    @classmethod
    def can_remap(cls, test_value):
        try:
            cls.remap(str(test_value))
        except Exception:
            return False
        return True

class ModelIDMapper(Mapper):
    
    """ Django model instances, as in properly-saved
        instances of non-abstract django.db.models.Model
        subclasses -- they have valid `pk` properties
        and suchlike.
        
        This mapper 'passes by reference', using an intermediate
        serial form consisting of a JSONified dict,* containing
        three values: the instance object's `pk` and its parent
        classes' `app_label` and `model_name` property. These
        are the data with which the object can be reconstituted
        with `django.db.models.loading.cache.get_model()`. """
    
    @classmethod
    def demap(cls, signal_arg):
        return {
            'app_label': signal_arg._meta.app_label,
            'modl_name': signal_arg.__class__.__name__.lower(),
            'obj_id': signal_arg.pk }
    
    @classmethod
    def remap(cls, intermediate):
        from django.db.models.loading import cache
        pk = intermediate.get('obj_id')
        ModCls = cache.get_model(
            intermediate.get('app_label'),
            intermediate.get('modl_name'))
        if ModCls:
            if pk is not -1:
                try:
                    return ModCls.objects.get(pk=pk)
                except ModCls.DoesNotExist:
                    return None
        return None
    
    @classmethod
    def can_demap(cls, test_value):
        return hasattr(test_value, '_meta') and \
            hasattr(test_value, '__class__') and \
            hasattr(test_value, 'pk')
    
    @classmethod
    def can_remap(cls, test_value):
        return ('obj_id' in test_value) and \
            ('app_label' in test_value) and \
            ('modl_name' in test_value)

ModelInstanceMapper = ModelIDMapper # 'legacy support'

class ModelValueMapper(Mapper):
    """ Django model instances, as in properly-saved
        instances of non-abstract django.db.models.Model
        subclasses -- they have valid `pk` properties
        and suchlike.
        
        This mapper uses the analagous corrolary to its
        sibling `ModelIDMapper` in that it 'passes by value'.
        The model instances' ID is actually ignored, and the 
        object __dict__ is filtered and then JSONated, using
        whatever `django.core.serializers.serialize` employs.
        
        """
    
    @classmethod
    def flattener(cls):
        if not hasattr(cls, '_flattener'):
            from django.core import serializers
            PyFlattener = serializers.get_serializer('python')
            cls._flattener = PyFlattener()
        return cls._flattener
    
    @classmethod
    def expander(cls, expandees):
        if not hasattr(cls, '_expander'):
            from django.core import serializers
            cls._expander = staticmethod(
                serializers.get_deserializer('python'))
        return cls._expander(expandees)
    
    @classmethod
    def model_from_identifier(cls, model_identifier):
        from django.db.models import get_model
        try:
            return get_model(*model_identifier.split('.'))
        except (TypeError, AttributeError, ValueError):
            return None
    
    @classmethod
    def demap(cls, signal_arg):
        return cls.flattener().serialize([signal_arg])[0]
    
    @classmethod
    def remap(cls, intermediate):
        return list(cls.expander([intermediate]))[0].object
    
    @classmethod
    def can_demap(cls, test_value):
        return hasattr(test_value, '_meta') and \
            hasattr(test_value, '__class__')
    
    @classmethod
    def can_remap(cls, test_value):
        has_atts = ('model' in test_value) and \
            ('fields' in test_value)
        if not has_atts:
            return False
        ModlCls = cls.model_from_identifier(
            test_value['model'])
        return (ModlCls is not None)


signature = lambda thing: "%s.%s" % (
    type(thing) in __import__('__builtin__').__dict__.values() \
        and '__builtin__' \
        or thing.__module__, \
    thing.__class__.__name__)

signature.__doc__ = """
    signature(x): return a string with the qualified module path of x.__class__
    
    examples:
    
    >>> signature(lambda: None)
    '__main__.function'
    >>> def yodogg(): pass
    ... 
    >>> 
    >>> signature(yodogg)
    '__main__.function'
    
    >>> sig(models.Model)
    'django.db.models.base.ModelBase'
    >>> sig(models)
    Traceback (most recent call last):
      File "<input>", line 1, in <module>
      File "<input>", line 1, in <lambda>
    AttributeError: 'module' object has no attribute '__module__'
    
    >>> sig(fish)
    'django.contrib.auth.models.User'
    
    >>> sig(dict)
    '__builtin__.type'
    
    >>> sig(defaultdict)
    '__builtin__.type'
    >>> from django.core.files.storage import FileSystemStorage
    >>> fs = FileSystemStorage()
    >>> fs
    <django.core.files.storage.FileSystemStorage object at 0x1031b4590>
    >>> sig(fs)
    'django.core.files.storage.FileSystemStorage'
    >>> sig(FileSystemStorage)
    '__builtin__.type'
    
"""

class MapperToPedigreeIndex(defaultdict):
    
    pedigrees = {
        
        # here's why I might do singletons (despite my
        # idiotic joke I was serious):
        
        'django.db.models.Model':               ModelIDMapper,
        'django.db.models.ModelBase':           ModelValueMapper,
        
        # this dict won't necessarily have this type
        # of thing in here literally, btdubs.
        # etc, etc... it's a heiarchy.
    }
    pedigrees.update(dict(
        [(signature(T()), LiteralValueMapper) \
            for T in LiteralValueMapper.DEMAP_TYPES]))
    
    def _demap_tests(self):
        global by_priority
        order = ()
        for priority in ('normal', 'penultimate', 'ultimate'):
            order += tuple(sorted(tuple(by_priority[priority])))
        return order
    
    demap_tests = property(_demap_tests)
    remap_tests = property(_demap_tests)
    
    # the above sequence dictates the order in which 
    # the mapping classes will be applied to an argument
    # when checking it.
    
    def demapper_for_value(self, value):
        ''' Mapper.can_demap() implementations should NOT
            fuck with, in-place or otherwise, the values
            they are passed to examine. '''
        for TestCls in self.demap_tests:
            try:
                if TestCls.can_demap(value):
                    return (TestCls, value)
            except Exception:
                continue
        return (self[None], value)
    
    def remapper_for_serial(self, serial):
        ''' Generally the sequential order is less important
            on this end -- a proper value serial is valid for
            exactly 1 deserializer, like by definition.
            long as one doesn't list mappers whose inter-
            mediate structures have much formal overlap...
            As a valid Base64-ed bzipped minified JSON blob
            is highly unlikely to also be (say) a reasonable
            pickle value, the order won't matter, as long
            as the can_demap()/can_remap() functions in play
            are responsible w/r/t the data they are passed. '''
        for TestCls in self.remap_tests:
            try:
                if TestCls.can_remap(serial):
                    return (TestCls, serial)
            except Exception:
                continue
        return (self[None], serial)
    
    def demap(self, value):
        MapCls, val = self.demapper_for_value(value)
        return MapCls.demap(val)
    
    def remap(self, value):
        MapCls, val = self.remapper_for_serial(value)
        return MapCls.remap(val)
    
    # The way to do this is:
    #       MOST SPECIFIC -> LEAST SPECIFIC.
    # ... The pickle mapper [2] takes most anything
    # in Python i.e. generator sequences and other
    # things that don't have a one-to-one JSONish
    # lexical analogue. Before pickling everything,
    # the LiteralValueMapper will make exceptions
    # for JSONerizable values [1]; before that, any
    # Django model objects, who are disproportionately
    # frequent commuters in the signal traffic of
    # most apps, have already been sieved out
    # by the ModelIDMapper [0].
    #
    # N.B. ModelValueMapper isn't used by default --
    # it's a nuanced, subtle, upscale sort of mapper
    # and it's not applied willy-nilly to objects.
    #
    # Also the map_test_order tuple might benefit from
    # being built on-the-fly (allowing 3rd parties
    # to do their own mapping, either by subclassing
    # or delegation or someshit, I don't know.)
    
    def __init__(self, *args, **kwargs):
        self_update = kwargs.pop('self_update', True)
        super(MapperToPedigreeIndex, self).__init__(*args, **kwargs)
        if self_update:
            self.update(self.pedigrees)
    
    def __missing__(self, key):
        return self.demap_tests[-1]
    
    def for_object(self, obj):
        return self[signature(obj)]
    
    def update_for_type(self, betyped, fortype):
        try:
            handcock = signature(betyped)
        except AttributeError:
            print('*** signatures of object instances are currently supported --')
            print('*** but not class types or other higher-order structures.')
            return
        
        if len(handcock) < 3:
            print('*** instance signature "%s" is too short.' % handcock)
            return
        
        self.update({ handcock: fortype, })
        return handcock
    
    def update_for(self, betyped):
        """ use this on objects that are as type-ishly consistent
            with those you'll be flinging down the signal's chute
            as you can find. """
        
        mapper, _ = self.demapper_for_value(betyped)
        if mapper is not None:
            return self.update_for_type(betyped, mapper)
        return


########NEW FILE########
__FILENAME__ = models

from django.db import models
from datetime import datetime
from delegate import DelegateManager, delegate
from signalqueue.worker.base import QueueBase
#from signalqueue.utils import logg


class SignalQuerySet(models.query.QuerySet):
    """
    SignalQuerySet is a QuerySet that works as a signalqueue backend.
    
    The actual QueueBase override methods are implemented here and delegated to
    SignalManager, which is a DelegateManager subclass with the QueueBase
    implementation "mixed in".
    
    Since you can't nakedly instantiate managers outside of a model
    class, we use a proxy class to hand off SignalQuerySet's delegated
    manager to the queue config stuff. See the working implementation in
    signalqueue.worker.backends.DatabaseQueueProxy for details.
    
    """
    @delegate
    def queued(self, enqueued=True):
        return self.filter(queue_name=self.queue_name, enqueued=enqueued).order_by("createdate")
    
    @delegate
    def ping(self):
        return True
    
    @delegate
    def push(self, value):
        self.get_or_create(queue_name=self.queue_name, value=value, enqueued=True)
    
    @delegate
    def pop(self):
        """ Dequeued signals are marked as such (but not deleted) by default. """
        out = self.queued()[0]
        out.enqueued = False
        out.save()
        return str(out.value)
    
    def count(self, enqueued=True):
        """ This override can't be delegated as the super() call isn't portable. """
        return super(self.__class__, self.all().queued(enqueued=enqueued)).count()
    
    @delegate
    def clear(self):
        self.queued().update(enqueued=False)
    
    @delegate
    def values(self, floor=0, ceil=-1):
        if floor < 1:
            floor = 0
        if ceil < 1:
            ceil = self.count()
        
        out = self.queued()[floor:ceil]
        return [str(value[0]) for value in out.values_list('value')]
    
    @delegate
    def __repr__(self):
        return "[%s]" % ",".join([str(value[0]) for value in self.values_list('value')])
    
    @delegate
    def __str__(self):
        return repr(self)
    
    def __unicode__(self):
        import json as library_json
        return u"%s" % library_json.dumps(library_json.loads(repr(self)), indent=4)

class SignalManager(DelegateManager, QueueBase):
    __queryset__ = SignalQuerySet
    
    def __init__(self, *args, **kwargs):
        self.runmode = kwargs.get('runmode', 4)
        QueueBase.__init__(self, *args, **kwargs)
        DelegateManager.__init__(self, *args, **kwargs)
    
    def count(self, enqueued=True):
        return self.queued(enqueued=enqueued).count()
    
    def _get_queue_name(self):
        if self._queue_name:
            return self._queue_name
        return None
    
    def _set_queue_name(self, queue_name):
        self._queue_name = queue_name
        self.__queryset__.queue_name = queue_name
    
    queue_name = property(_get_queue_name, _set_queue_name)

class EnqueuedSignal(models.Model):
    class Meta:
        abstract = False
        verbose_name = "Enqueued Signal"
        verbose_name_plural = "Enqueued Signals"
    
    objects = SignalManager()
    keys = set(
        ('signal', 'sender', 'enqueue_runmode'))
    
    createdate = models.DateTimeField("Created on",
        default=datetime.now,
        blank=True,
        null=True,
        editable=False)
    
    enqueued = models.BooleanField("Enqueued",
        default=True,
        editable=True)
    
    queue_name = models.CharField(verbose_name="Queue Name",
        max_length=255, db_index=True,
        default="default",
        unique=False,
        blank=True,
        null=False)
    
    value = models.TextField(verbose_name="Serialized Signal Value",
        editable=False,
        unique=True, db_index=True,
        blank=True,
        null=True)
    
    def _get_struct(self):
        if self.value:
            from signalqueue.utils import json, ADict
            return ADict(
                json.loads(self.value))
        return ADict()
    
    def _set_struct(self, newstruct):
        if self.keys.issuperset(newstruct.keys()):
            from signalqueue.utils import json
            self.value = json.dumps(newstruct)
    
    struct = property(_get_struct, _set_struct)
    
    def __repr__(self):
        if self.value:
            return str(self.value)
        return "{'instance':null}"
    
    def __str__(self):
        return repr(self)
    
    def __unicode__(self):
        if self.value:
            import json as library_json
            return u"%s" % library_json.dumps(
                library_json.loads(repr(self)),
                indent=4)
        return u"{'instance':null}"

########NEW FILE########
__FILENAME__ = test_async
from ..settings import *

SQ_RUNMODE = 'SQ_ASYNC_REQUEST'

########NEW FILE########
__FILENAME__ = test_sync
from ..settings import *

SQ_RUNMODE = 'SQ_SYNC'

########NEW FILE########
__FILENAME__ = urlconf
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import signalqueue
signalqueue.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = signals

from signalqueue import mappings
from signalqueue.dispatcher import AsyncSignal

test_signal = AsyncSignal(providing_args={

    'instance':             mappings.ModelInstanceMapper,
    'signal_label':         mappings.LiteralValueMapper,

})
########NEW FILE########
__FILENAME__ = signalqueue_status

import os
from django.conf import settings
from django import template
from signalqueue.worker import queues

register = template.Library()

# get the URL for a static asset (css, js, et cetera.)
static = lambda pth: os.path.join(settings.STATIC_URL, 'signalqueue', pth)
sockio = lambda pth: os.path.join(settings.STATIC_URL, 'socket.io-client', pth)

@register.simple_tag
def queue_length(queue_name):
    if queue_name in queues:
        try:
            return queues[queue_name].count()
        except:
            return -1
    return -1

@register.simple_tag
def queue_classname(queue_name):
    return str(queues[queue_name].__class__.__name__)

@register.simple_tag
def sock_status_url():
    import socket
    return "ws://%s:%s/sock/status" % (socket.gethostname().lower(), settings.SQ_WORKER_PORT)

@register.inclusion_tag('admin/sidebar_queue_module.html', takes_context=True)
def sidebar_queue_module(context):
    qs = dict(queues.items())
    default = qs.pop('default')
    return dict(
        default=default, queues=qs,
        queue_javascript=static('js/jquery.signalqueue.js'),
        socketio_javascript=sockio('socket.io.js'),
        socketio_swf=sockio('WebSocketMain.swf'))




########NEW FILE########
__FILENAME__ = testrunner
#!/usr/bin/env python
# encoding: utf-8
"""
Run this file to test `signalqueue` -- 
You'll want to have `nose` and `django-nose` installed.

"""
def main():
    rp = None
    from signalqueue import settings as signalqueue_settings
    
    logging_format = '--logging-format="%(asctime)s %(levelname)-8s %(name)s:%(lineno)03d:%(funcName)s %(message)s"'
    signalqueue_settings.__dict__.update({
        "NOSE_ARGS": [
            '--rednose', '--nocapture', '--nologcapture', '-v',
            logging_format] })
    
    from django.conf import settings
    settings.configure(**signalqueue_settings.__dict__)
    import logging.config
    logging.config.dictConfig(settings.LOGGING)
    
    import subprocess, os
    redis_dir = '/tmp/redis/'
    if not os.path.isdir(redis_dir):
        try:
            os.makedirs(redis_dir) # make redis as happy as possible
        except OSError:
            print "- Can't create Redis data dir %s" % redis_dir
    
    rp = subprocess.Popen([
        'redis-server',
        "%s" % os.path.join(
            signalqueue_settings.approot,
            'settings', 'redis-compatible.conf'),
        ])
    
    from django.core.management import call_command
    call_command('test', 'signalqueue.tests',
        interactive=False, traceback=True, verbosity=2)
    
    if rp is not None:
        print "Shutting down Redis test process (pid = %s)" % rp.pid
        rp.kill()
    
    tempdata = settings.tempdata
    print "Deleting test data (%s)" % tempdata
    os.rmdir(tempdata)
    
    import sys
    sys.exit(0)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = tests

from django.conf import settings
from django.test import TestCase
#from django.test.utils import override_settings as override
from tornado.testing import AsyncHTTPTestCase
from unittest import skipUnless

from django.db import models
#from django.core.serializers import serialize
from signalqueue import dispatcher, mappings

additional_signal = dispatcher.AsyncSignal(
    providing_args=['instance',],
    queue_name='db',
)
test_sync_method_signal = dispatcher.AsyncSignal(
    providing_args=['instance',],
    queue_name='db',
)
test_sync_function_signal = dispatcher.AsyncSignal(
    providing_args=['instance',],
    queue_name='db',
)

signal_with_object_argument_old = dispatcher.AsyncSignal(
    providing_args=dict(
        instance=mappings.ModelIDMapper,
        obj=mappings.PickleMapper),
)
signal_with_object_argument_default = dispatcher.AsyncSignal(
    providing_args=['instance','obj'],
)
signal_with_object_argument_listqueue = dispatcher.AsyncSignal(
    providing_args=['instance','obj'],
    queue_name='listqueue',
)
signal_with_object_argument_db = dispatcher.AsyncSignal(
    providing_args=['instance','obj'],
    queue_name='db',
)
signal_with_object_argument_celery = dispatcher.AsyncSignal(
    providing_args=['instance','obj'],
    queue_name='celery',
)

class TestObject(object):
    def __init__(self, v):
        self.v = v

class TestModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255,
        blank=False, null=False, unique=False,
        default="Test Model Instance.")
    
    def save(self, signal=None, force_insert=False, force_update=False):
        super(TestModel, self).save(force_insert, force_update)
        if signal is not None:
            signal.send(sender=self, instance=self, signal_label="save")
    
    def save_now(self, signal=None, force_insert=False, force_update=False):
        super(TestModel, self).save(force_insert, force_update)
        if signal is not None:
            signal.send_now(sender=self, instance=self, signal_label="save_now")
    
    def callback(self, sender=None, **kwargs):
        msg =  "********** MODEL CALLBACK: %s sent %s\n" % (sender, kwargs.items())
        raise TestException(msg)

class TestException(Exception):
    def __eq__(self, other):
        return type(self) == type(other)
    def __repr__(self):
        return "<TestException (%s)>" % self.__hash__()

def callback(sender, **kwargs):
    msg = "********** CALLBACK: %s" % kwargs.items()
    raise TestException(msg)

def callback_no_exception(sender, **kwargs):
    msg = "********** NOEXEPT: %s" % kwargs.items()
    print msg
    return kwargs.get('obj', None)


class LiteralValueMapperTests(TestCase):
    
    fixtures = ['TESTMODEL-DUMP.json', 'TESTMODEL-ENQUEUED-SIGNALS.json']
    
    def setUp(self):
        from signalqueue.worker import queues
        self.mapper = mappings.LiteralValueMapper()
        self.mapees = [str(v) for v in queues['db'].values()]
    
    def test_map_remap(self):
        for test_instance in self.mapees:
            mapped = self.mapper.demap(test_instance)
            remapped = self.mapper.remap(mapped)
            self.assertEqual(test_instance, remapped)

class ModelIDMapperTests(TestCase):
    
    fixtures = ['TESTMODEL-DUMP.json', 'TESTMODEL-ENQUEUED-SIGNALS.json']
    
    def setUp(self):
        self.mapper = mappings.ModelIDMapper()
    
    def test_map_remap(self):
        for test_instance in TestModel.objects.all():
            mapped = self.mapper.demap(test_instance)
            remapped = self.mapper.remap(mapped)
            self.assertEqual(test_instance, remapped)

class ModelValueMapperTests(TestCase):

    fixtures = ['TESTMODEL-DUMP.json', 'TESTMODEL-ENQUEUED-SIGNALS.json']

    def setUp(self):
        self.mapper = mappings.ModelValueMapper()

    def test_map_remap(self):
        for test_instance in TestModel.objects.all():
            mapped = self.mapper.demap(test_instance)
            remapped = self.mapper.remap(mapped)
            self.assertEqual(test_instance, remapped)

class PickleMapperTests(TestCase):
    
    fixtures = ['TESTMODEL-DUMP.json']
    
    def setUp(self):
        self.dqsettings = dict(
            SQ_ADDITIONAL_SIGNALS=['signalqueue.tests'],
            SQ_RUNMODE='SQ_ASYNC_REQUEST')
        self.mapper = mappings.PickleMapper()
        
    def test_map_remap(self):
        for test_instance in TestModel.objects.all():
            mapped = self.mapper.demap(test_instance)
            remapped = self.mapper.remap(mapped)
            self.assertEqual(test_instance, remapped)
        
    def test_signal_with_pickle_mapped_argument(self):
        with self.settings(**self.dqsettings):
            import signalqueue
            signalqueue.autodiscover()
            from signalqueue.worker import queues
            
            #for queue in [q for q in queues.all() if q.queue_name is not 'celery']:
            
            for queue in queues.all():
                
                print "*** Testing queue: %s" % queue.queue_name
                #queue.clear()
                
                from signalqueue import SQ_DMV
                for regsig in SQ_DMV['signalqueue.tests']:
                    if regsig.name == "signal_with_object_argument_%s" % queue.queue_name:
                        signal_with_object_argument = regsig
                        break
                
                signal_with_object_argument.queue_name = str(queue.queue_name)
                signal_with_object_argument.connect(callback_no_exception)
                
                instances = TestModel.objects.all().iterator()
                testobj = TestObject('yo dogg')
                testexc = TestException()
                
                testobjects = [testobj, testexc]
                
                for testobject in testobjects:
                    sigstruct_send = signal_with_object_argument.send(
                        sender=instances.next(), instance=instances.next(), obj=testobject)
                    
                    print "*** Queue %s: %s values, runmode is %s" % (
                        signal_with_object_argument.queue_name, queue.count(), queue.runmode)
                    sigstruct_dequeue, result_list = queue.dequeue()
                    
                    #from pprint import pformat
                    #print pformat(sigstruct_send, indent=4)
                    #print pformat(sigstruct_dequeue, indent=4)
                    
                    self.assertEqual(sigstruct_send, sigstruct_dequeue)
                    
                    # result_list is a list of tuples, each containing a reference
                    # to a callback function at [0] and that callback's return at [1]
                    # ... this is per what the Django signal send() implementation returns.
                    if result_list is not None:
                        resultobject = dict(result_list)[callback_no_exception]
                        print "*** resultobject (%s) = %s" % (
                            type(resultobject), resultobject)
                        
                        #self.assertEqual(
                        #    resultobject, testobject)
                        #self.assertEqual(
                        #    type(resultobject), type(testobject))
                        
                    else:
                        print "*** queue.dequeue() returned None"

class WorkerTornadoTests(TestCase, AsyncHTTPTestCase):
    
    fixtures = ['TESTMODEL-DUMP.json', 'TESTMODEL-ENQUEUED-SIGNALS.json']
    
    def __init__(self, *args, **kwargs):
        TestCase.__init__(self, *args, **kwargs)
        AsyncHTTPTestCase.__init__(self, *args, **kwargs)
    
    def setUp(self):
        TestCase.setUp(self)
        AsyncHTTPTestCase.setUp(self)
    
    def tearDown(self):
        TestCase.tearDown(self)
        AsyncHTTPTestCase.tearDown(self)
    
    def get_app(self):
        from signalqueue.worker.vortex import Application
        return Application(queue_name="db")
    
    def test_worker_status_url_with_queue_parameter_content(self):
        from signalqueue.worker import queues
        for queue_name in queues.keys():
            #if queue_name is not 'celery':
            cnt = queues[queue_name].count() or 0
            self.http_client.fetch(self.get_url('/status?queue=%s' % queue_name), self.stop)
            response = self.wait()
            self.assertTrue(queue_name in response.body)
            self.assertTrue("enqueued" in response.body)
            
            #phrase = "%s enqueued signals" % cnt
            #print "##########################################"
            #print phrase
            #print "##########################################"
            #print response.body
            #print "##########################################"
            #phrase = "enqueued signals"
            #self.assertTrue(phrase in response.body)
    
    def test_worker_status_url_content(self):
        from signalqueue.worker import queues
        queue = queues['db']
        cnt = queue.count() or 0
        
        self.http_client.fetch(self.get_url('/status'), self.stop)
        response = self.wait()
        self.assertTrue("db" in response.body)
        self.assertTrue("enqueued" in response.body)
        
        phrase = "%s enqueued signals" % cnt
        self.assertTrue(phrase in response.body)
    
    def test_worker_status_timeout(self):
        dqsettings = dict(
            SQ_ADDITIONAL_SIGNALS=['signalqueue.tests'],
            SQ_RUNMODE='SQ_ASYNC_REQUEST')
        
        with self.settings(**dqsettings):
            import signalqueue
            signalqueue.autodiscover()
            from signalqueue.worker import queues
            queue = queues['db']
            
            oldcount = queue.count()
            
            yodogg = queue.retrieve()
            queue.dequeue(queued_signal=yodogg)
            
            print "Sleeping for 0.5 seconds..."
            import time
            time.sleep(0.5)
            
            cnt = queue.count() or 0
            self.http_client.fetch(self.get_url('/status'), self.stop)
            response = self.wait(timeout=10)
            phrase = "%s enqueued signals" % cnt
            #print "##########################################"
            #print phrase
            #print "##########################################"
            #print response.body
            #print "##########################################"
            #self.assertTrue(phrase in response.body)
            
            newcount = queue.count()
            self.assertTrue(int(oldcount) > int(newcount))
    
    def _test_worker_dequeue_from_tornado_periodic_callback(self):
        from signalqueue import signals
        signals.test_signal.connect(callback)
        
        import signalqueue
        signalqueue.autodiscover()
        
        from django.core.management import call_command
        call_command('runqueueserver', '9920',
            queue_name='db', halt_when_exhausted=True, exit=False)
        
        from signalqueue.models import WorkerExceptionLog
        self.assertTrue(WorkerExceptionLog.objects.totalcount() > 10)
    
    def test_worker_application(self):
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertTrue("YO DOGG" in response.body)


class DequeueManagementCommandTests(TestCase):
    
    fixtures = ['TESTMODEL-DUMP.json', 'TESTMODEL-ENQUEUED-SIGNALS.json']
    
    def setUp(self):
        self.dqsettings = dict(
            SQ_ADDITIONAL_SIGNALS=['signalqueue.tests'],
            SQ_RUNMODE='SQ_ASYNC_REQUEST')
        with self.settings(**self.dqsettings):
            import signalqueue
            signalqueue.autodiscover()
            from signalqueue.worker import queues
            self.queue = queues['db']
    
    def test_dequeue_management_command(self):
        with self.settings(**self.dqsettings):
            test_sync_function_signal.disconnect(callback)
            test_sync_function_signal.connect(callback_no_exception)
            
            from django.core.management import call_command
            call_command('dequeue',
                queue_name='db', verbosity=2)


class DjangoAdminQueueWidgetTests(TestCase):
    """ DjangoAdminQueueWidgetTests.setUp() creates a superuser for admin testing.
        See also http://www.djangosnippets.org/snippets/1875/ """
    
    def setUp(self):
        from django.contrib.auth import models as auth_models
        self.testuser = 'yodogg'
        self.testpass = 'iheardyoulikeunittests'
        
        try:
            self.user = auth_models.User.objects.get(username=self.testuser)
        except auth_models.User.DoesNotExist:
            assert auth_models.User.objects.create_superuser(self.testuser,
                '%s@%s.com' % (self.testuser, self.testuser), self.testpass)
            self.user = auth_models.User.objects.get(username=self.testuser)
        else:
            print 'Test user %s already exists.' % self.testuser
        
        from django.test.client import Client
        self.client = Client()
        
        import os
        self.testroot = os.path.dirname(os.path.abspath(__file__))
    
    @skipUnless(hasattr(settings, 'ROOT_URLCONF'),
        "needs specific ROOT_URLCONF from django-signalqueue testing")
    def test_admin_queue_status_widget_contains_queue_names(self):
        from signalqueue.worker import queues
        post_out = self.client.post('/admin/', dict(
            username=self.user.username, password=self.testpass,
            this_is_the_login_form='1', next='/admin/'))
        admin_root_page = self.client.get('/admin/')
        for queue_name in queues.keys():
            self.assertContains(admin_root_page, queue_name.capitalize())
            self.assertTrue(queue_name.capitalize() in admin_root_page.content)
        self.client.get('/admin/logout/')
        print post_out # pyflakes don't crack
    
    @skipUnless(hasattr(settings, 'ROOT_URLCONF'),
        "needs specific ROOT_URLCONF from django-signalqueue testing")
    def test_admin_widget_sidebar_uses_queue_module_template(self):
        post_out = self.client.post('/admin/', dict(
            username=self.user.username, password=self.testpass,
            this_is_the_login_form='1', next='/admin/'))
        admin_root_page = self.client.get('/admin/')
        import os
        self.assertTemplateUsed(admin_root_page,
            os.path.join(self.testroot,
            'templates/admin/index_with_queues.html'))
        self.client.get('/admin/logout/')
        print post_out # pyflakes don't crack
    
    @skipUnless(hasattr(settings, 'ROOT_URLCONF'),
        "needs specific ROOT_URLCONF from django-signalqueue testing")
    def test_get_admin_root_page(self):
        #post_out = self.client.post('/admin/', dict(
        #    username=self.user.username, password=self.testpass,
        #    this_is_the_login_form='1', next='/admin/'))
        admin_root_page = self.client.get('/admin/')
        self.assertEquals(admin_root_page.status_code, 200)
        #self.client.get('/admin/logout/')
        #print post_out # pyflakes don't crack
    
    @skipUnless(hasattr(settings, 'ROOT_URLCONF'),
        "needs specific ROOT_URLCONF from django-signalqueue testing")
    def test_testuser_admin_login_via_client(self):
        self.assertTrue(self.client.login(username=self.testuser,
        password=self.testpass))
        self.assertEquals(self.client.logout(), None)
    
    @skipUnless(hasattr(settings, 'ROOT_URLCONF'),
        "needs specific ROOT_URLCONF from django-signalqueue testing")
    def test_testuser_admin_login(self):
        self.assertEquals(self.user.username, 'yodogg')
        post_out = self.client.post('/admin/', dict(
            username=self.user.username, password=self.testpass,
            this_is_the_login_form='1', next='/admin/'))
        # you get a redirect when you log in correctly
        self.assertEquals(post_out.status_code, 302)

class DequeueFromDatabaseTests(TestCase):
    
    fixtures = ['TESTMODEL-DUMP.json', 'TESTMODEL-ENQUEUED-SIGNALS.json']
    
    def setUp(self):
        self.dqsettings = dict(
            SQ_ADDITIONAL_SIGNALS=['signalqueue.tests'],
            SQ_RUNMODE='SQ_ASYNC_REQUEST')
        with self.settings(**self.dqsettings):
            import signalqueue
            signalqueue.autodiscover()
            from signalqueue.worker import queues
            self.queue = queues['db']
    
    def test_dequeue(self):
        with self.settings(**self.dqsettings):
            test_sync_function_signal.connect(callback)
            for enqd in self.queue:
                with self.assertRaises(TestException):
                    self.queue.dequeue(enqd)


class DatabaseQueuedVersusSyncSignalTests(TestCase):
    def setUp(self):
        import signalqueue, uuid
        with self.settings(SQ_ADDITIONAL_SIGNALS=['signalqueue.tests']):
            signalqueue.autodiscover()
        
        from signalqueue.worker import queues
        self.queue = queues['db']
        self.name = "Yo dogg: %s" % str(uuid.uuid4().hex)
    
    def test_NOW_sync_method_callback(self):
        t = TestModel(name=self.name)
        test_sync_method_signal.connect(t.callback)
        with self.assertRaises(TestException):
            t.save_now(test_sync_method_signal)
    
    def test_NOW_sync_function_callback(self):
        t = TestModel(name=self.name)
        test_sync_function_signal.connect(callback)
        with self.assertRaises(TestException):
            t.save_now(test_sync_function_signal)
    
    def test_method_callback(self):
        t = TestModel(name=self.name)
        test_sync_method_signal.connect(t.callback)
        
        if getattr(settings, 'SQ_ASYNC', True):
            t.save(test_sync_method_signal)
            with self.assertRaises(TestException):
                enqueued_signal = self.queue.dequeue()
                print enqueued_signal # pyflakes don't crack
        
        else:
            with self.assertRaises(TestException):
                t.save(test_sync_method_signal)
    
    def test_function_callback(self):
        t = TestModel(name=self.name)
        test_sync_function_signal.connect(callback)
        
        if getattr(settings, 'SQ_ASYNC', True):
            t.save(test_sync_function_signal)
            with self.assertRaises(TestException):
                enqueued_signal = self.queue.dequeue()
                print enqueued_signal # pyflakes don't crack
            
        else:
            with self.assertRaises(TestException):
                t.save(test_sync_function_signal)


class RegistryTests(TestCase):
    def setUp(self):
        pass
    
    def test_register_function(self):
        import signalqueue
        signalqueue.register(additional_signal,
            'additional_signal', 'signalqueue.tests')
        signalqueue.register(additional_signal,
            'yo_dogg', 'i-heard-you-like-signal-registration-keys')
        
        self.assertTrue(
            additional_signal in signalqueue.SQ_DMV['signalqueue.tests'])
        self.assertTrue(
            additional_signal in signalqueue.SQ_DMV['i-heard-you-like-signal-registration-keys'])
    
    def test_additional_signals(self):
        #from signalqueue import signals
        
        with self.settings(SQ_ADDITIONAL_SIGNALS=['signalqueue.tests']):
            import signalqueue
            signalqueue.autodiscover()
            '''
            for k, v in signalqueue.SQ_DMV.items():
                print "%25s:" % k
                for val in v:
                    print "%25s %20s: %s" % ("", val.__class__.__name__, val.name) '''
            self.assertTrue(additional_signal in signalqueue.SQ_DMV['signalqueue.tests'])
    
    def test_autodiscover(self):
        import signalqueue
        from signalqueue import signals
        
        signalqueue.autodiscover()
        
        for sig in [s for s in signals.__dict__.values() if isinstance(s, dispatcher.AsyncSignal)]:
            self.assertTrue(sig in signalqueue.SQ_DMV['signalqueue.signals'])



########NEW FILE########
__FILENAME__ = utils

from __future__ import print_function

#import os, sys, traceback
import setproctitle
import sys
import os

# Root directory of this package
SQ_ROOT = os.path.dirname(os.path.abspath(__file__))

# Similar arrangement that affords us some kind of reasonable
# implementation of import_module
def simple_import_module(name, package=None):
    """
    Dumb version of import_module.
    Based on a function from dajaxice.utils of a similar name. """
    __import__(name)
    return sys.modules[name]

try:
    from importlib import import_module
except:
    try:
        from django.utils.importlib import import_module
    except:
        import_module = simple_import_module


class FakeLogger(object):
    """ Completely unacceptable fake-logger class, for last-resort use. """
    def log(self, level, msg):
        print("signalqueue.utils.FakeLogger: %s" % msg)
    
    def logg(self, msg):
        self.log(0, msg)
    
    def __init__(self, *args, **kwargs):
        super(FakeLogger, self).__init__(*args, **kwargs)
        for fname in ('critical', 'debug', 'error', 'exception', 'info', 'warning'):
            setattr(self, fname, self.logg)


# HAAAAAX
logger_name = "signalqueue > MODULE"
if 'runqueueserver' in setproctitle.getproctitle():
    logger_name = "signalqueue > WORKER"

try:
    from jogging import logging as logg
except ImportError:
    try:
        import logging
    except ImportError:
        print("WTF: You have no logging facilities available whatsoever.")
        print("I'm initializing a fake logger class. Love, django-signalqueue.")
        # set up fake logger
        logg = FakeLogger()
    else:
        logg = logging.getLogger(logger_name)
        logg.setLevel(logging.DEBUG)

from contextlib import contextmanager

@contextmanager
def log_exceptions(exc_type=Exception, **kwargs):
    try:
        from raven.contrib.django.models import client as raven_client
    except ImportError:
        raven_client = None
    try:
        yield
    except exc_type, exc:
        if raven_client is not None:
            raven_client.captureException(sys.exc_info())
        print(exc)


class ADict(dict):
    """
    ADict -- Convenience class for dictionary key access via attributes.
    
    The 'A' in 'ADict' is for 'Access' -- you can also use adict.key as well as adict[key]
    to access hash values. """
    
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
    
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(name)
    
    def __setattr__(self, name, value):
        self[name] = value
    
    def __delattr__(self, name):
        del self[name]


# To consistently use the fastest serializer possible, use:
#   from signalqueue.utils import json
# ... so if you need to swap a library, do it here.
try:
    import ujson as json
except ImportError:
    logg.info("--- Loading czjson in leu of ujson")
    try:
        import czjson as json
    except ImportError:
        logg.info("--- Loading yajl in leu of czjson")
        try:
            import yajl as json
            assert hasattr(json, 'loads')
            assert hasattr(json, 'dumps')
        except (ImportError, AssertionError):
            logg.info("--- Loading simplejson in leu of yajl")
            try:
                import simplejson as json
            except ImportError:
                logg.info("--- Loading stdlib json module in leu of simplejson")
                import json

########NEW FILE########
__FILENAME__ = backends
#!/usr/bin/env python
# encoding: utf-8
"""
backends.py

Driver classes -- each allows the queue workers to talk to a different backend server.

Created by FI$H 2000 on 2011-06-29.
Copyright (c) 2011 OST, LLC. All rights reserved.

"""

from django.core.exceptions import ImproperlyConfigured
from signalqueue.utils import import_module, logg
from signalqueue.worker.base import QueueBase

class RedisQueue(QueueBase):
    
    def __init__(self, *args, **kwargs):
        """
        The RedisQueue is the default queue backend. The QueueBase methods are mapped to 
        a Redis list; the redis-py module is required:
        
            https://github.com/andymccurdy/redis-py
        
        Redis is simple and fast, out of the box. The hiredis C library and python wrappers
        can be dropped into your install, to make it faster:
        
            https://github.com/pietern/hiredis-py
        
        To configure Redis, we pass the queue OPTIONS dict off wholesale to the python
        redis constructor -- Simply stick any Redis kwarg options you need into the OPTIONS
        setting. All the redis options can be furthermore specified in the RedisQueue constructor
        as a queue_options dict to override settings.py.
        
        """
        super(RedisQueue, self).__init__(*args, **kwargs)
        
        try:
            import redis
        except ImportError:
            raise IOError("WTF: Can't import redis python module.")
        else:
            try:
                import hiredis
            except ImportError:
                logg.warn("can't import the `hiredis` package")
                logg.warn("consider installing `hiredis` for native-speed access to a Redis queue")
                logg.warn("you can see the difference even when running the tests --")
                logg.warn("-- it's a good move, trust me on that")
            
            self.r = redis.Redis(**self.queue_options)
            self.exceptions = (
                redis.exceptions.ConnectionError,
                redis.exceptions.DataError,
                redis.exceptions.InvalidResponse)
            
            try:
                self.r.ping()
            except self.exceptions, err:
                logg.error("connection to Redis server failed: %s" % err)
                self.r = None
    
    def ping(self):
        if self.r is not None:
            try:
                return self.r.ping()
            except (self.ConnectionError, AttributeError), err:
                logg.error("no Redis connection available: %s" % err)
                return False
        return False
    
    def push(self, value):
        self.r.lpush(self.queue_name, value)
    
    def pop(self):
        return self.r.lpop(self.queue_name)
    
    def count(self):
        return self.r.llen(self.queue_name)
    
    def clear(self):
        self.r.delete(self.queue_name)
    
    def values(self, floor=0, ceil=-1):
        return list(self.r.lrange(self.queue_name, floor, ceil))

class RedisSetQueue(RedisQueue):
    """
    RedisSetQueue uses a Redis set. Use this queue backend if you want to ensure signals aren't
    dequeued and sent more than once.
    
    I'll be honest here -- I did not originally intend to write any of this configgy stuff or
    provide multiple backend implementations or any of that. I just wanted to write a queue for
    signals, man. That was it. In fact I didn't even set out to write •that• -- I was just going
    to put the constructors for the non-standard signals I was thinking about using in
    the 'signals.py' file, cuz they did that by convention at the last place I worked, so I was
    like hey why not. The notion of having async signal invocation occurred to me, so I took
    a stab at an implementation.
    
    Srsly I was going for casual friday for realsies, with KewGarden's API. The queue implementation
    was like two extra lines (aside from the serialization crapola) and it worked just fine, you had
    your redis instance, and you used it, erm.
    
    BUT SO. I ended up piling most everything else on because I thought: well, this is open source,
    and I obvi want to contribute my own brick in the GPL wall in the fine tradition of Stallman
    and/or de Raadt -- I am a de Raadt guy myself but either way -- and also maybe potential
    employers might look at this and be like "Hmm, this man has written some interesting codes.
    Let's give him money so he'll do an fascinatingly engaging yet flexible project for us."
    
    Anything is possible, right? Hence we have confguration dicts, multiple extensible backend
    implementations, inline documentation, management commands with help/usage text, sensible
    defaults with responsibly legible and double-entendre-free variable names... the works. 
    But the deal is: it's actually helpful. Like to me, the implementor. For example look:
    here's my iterative enhancement to the Redis queue in which we swap datastructures and
    see what happens. Not for my health; I wrote the list version first and then decided I wanted
    unque values to curtail signal throughput -- it's not like I sat around with such a fantastic
    void of things to do with my time that I needed to write multiple backends for my queue thingy
    in order to fill the days and nights with meaning. 
    
    Anyway that is the docstring for RedisSetQueue, which I hope you find informative.
    
    """
    def __init__(self, *args, **kwargs):
        super(RedisSetQueue, self).__init__(*args, **kwargs)
    
    def push(self, value):
        self.r.sadd(self.queue_name, value)
    
    def pop(self):
        return self.r.spop(self.queue_name)
    
    def count(self):
        return self.r.scard(self.queue_name)
    
    def clear(self):
        while self.r.spop(self.queue_name): pass
    
    def values(self, **kwargs):
        return list(self.r.smembers(self.queue_name))

class DatabaseQueueProxy(QueueBase):
    """
    The DatabaseQueueProxy doesn't directly instantiate; instead, this proxy object
    will set up a model manager you specify in your settings as a queue backend.
    This allows you to use a standard database-backed model to run a queue.
    
    A working implementation of such a model manager is available in signalqueue/models.py.
    To use it, sync the EnqueuedSignal model to your database and configure the queue like so:
    
        SQ_QUEUES = {
            'default': {
                'NAME': 'signalqueue_database_queue',
                'ENGINE': 'signalqueue.worker.backends.DatabaseQueueProxy',
                'OPTIONS': dict(app_label='signalqueue', modl_name='EnqueuedSignal'),
            },
        }
    
    This is useful for:
    
        * Debugging -- the queue can be easily inspected via the admin interface;
          dequeued objects aren't deleted by default (the 'enqueued' boolean field
          is set to False when instances are dequeued).
        * Less moving parts -- useful if you don't want to set up another service
          (e.g. Redis) to start working with queued signals.
        * Fallback functionality -- you can add logic to set up a database queue
          if the queue backend you want to use is somehow unavailable, to keep from
          losing signals e.g. while scaling Amazon AMIs or transitioning your
          servers to new hosts.
    
    """
    def __new__(cls, *args, **kwargs):
        
        if 'app_label' in kwargs['queue_options']:
            if 'modl_name' in kwargs['queue_options']:
                
                from django.db.models.loading import cache
                mgr_attr = kwargs['queue_options'].get('manager', "objects")
                
                ModlCls = cache.get_model(
                    app_label=kwargs['queue_options'].get('app_label'),
                    model_name=kwargs['queue_options'].get('modl_name'))
                
                if ModlCls is not None:
                    mgr_instance = getattr(ModlCls, mgr_attr)
                    mgr_instance.runmode = kwargs.pop('runmode', None)
                    mgr_instance.queue_name = kwargs.pop('queue_name')
                    mgr_instance.queue_options = {}
                    mgr_instance.queue_options.update(kwargs.pop('queue_options', {}))
                    return mgr_instance
                
                else:
                    return QueueBase()
            
            else:
                raise ImproperlyConfigured(
                    "DatabaseQueueProxy's queue configuration requires the name of a model class to be specified in in 'modl_name'.")
        
        else:
            raise ImproperlyConfigured(
                "DatabaseQueueProxy's queue configuration requires an app specified in 'app_label', in which the definition for a model named 'modl_name' can be found.")

"""
Class-loading functions.

ConnectionHandler, import_class() and load_backend() are based on original implementations
from the django-haystack app:

    https://github.com/toastdriven/django-haystack/blob/master/haystack/utils/loading.py
    https://github.com/toastdriven/django-haystack/

See the Haystack source for more on these.

"""
def import_class(path):
    path_bits = path.split('.') # Cut off the class name at the end.
    class_name = path_bits.pop()
    module_path = '.'.join(path_bits)
    module_itself = import_module(module_path)
    if not hasattr(module_itself, class_name):
        raise ImportError(
            "The Python module '%s' has no '%s' class." % (module_path, class_name))
    return getattr(module_itself, class_name)

def load_backend(full_backend_path):
    path_bits = full_backend_path.split('.')
    if len(path_bits) < 2:
        raise ImproperlyConfigured(
            "The provided backend '%s' is not a complete Python path to a QueueBase subclass." % full_backend_path)
    return import_class(full_backend_path)

class ConnectionHandler(object):
    def __init__(self, connections_info, runmode):
        #logg.debug(
        #    "Initializing a ConnectionHandler with %s queues running in mode %s" % (
        #        len(connections_info), runmode))
        self.connections_info = connections_info
        self._connections = {}
        self._runmode = runmode
        self._index = None
    
    def _get_runmode(self):
        return self._runmode
    def _set_runmode(self, mde):
        for key in self._connections.keys():
            if hasattr(self._connections[key], 'runmode'):
                self._connections[key].runmode = mde
        self._runmode = mde
    
    runmode = property(_get_runmode, _set_runmode)
    
    def ensure_defaults(self, alias):
        try:
            conn = self.connections_info[alias]
        except KeyError:
            raise ImproperlyConfigured(
                "The key '%s' isn't an available connection in (%s)." % (alias, ','.join(self.connections_info.keys())))
        
        default_engine = 'signalqueue.worker.backends.RedisSetQueue'
        
        if not conn.get('ENGINE'):
            logg.warn(
                "connection '%s' doesn't specify an ENGINE, using the default engine: '%s'" %
                    default_engine)
            # default to using the Redis set backend
            conn['ENGINE'] = default_engine
    
    def __getitem__(self, key):
        if key in self._connections:
            return self._connections[key]
        
        self.ensure_defaults(key)
        
        ConnectionClass = load_backend(self.connections_info[key]['ENGINE'])
        self._connections[key] = ConnectionClass(
            runmode=self._runmode,
            queue_name=str(key),
            queue_interval=self.connections_info[key].get('INTERVAL', None),
            queue_options=self.connections_info[key].get('OPTIONS', {}))
        
        self._connections[key].runmode = self._runmode
        
        return self._connections[key]
    
    def __setitem__(self, key, val):
        if not isinstance(val, QueueBase):
            raise ValueError(
                "Can't add instance of non-QueueBase descent '%s' to the ConnectionHandler." % val)
        if not val.runmode == self._runmode:
            raise AttributeError(
                "Queue backend '%s' was instantiated with runmode %s but the ConnectionHandler is in runmode %s" % (val.runmode, self._runmode))
        self._connections[key] = val
    
    def get(self, key, default=None):
        try:
            return self[key]
        except:
            if default is None:
                raise
            return default
    
    def all(self):
        return [self[alias] for alias in self.connections_info]
    
    def keys(self):
        return self.connections_info.keys()
    
    def items(self):
        return [(qn, self[qn]) for qn in self.keys()]
    
    def values(self):
        return self.all()
    
    def __iter__(self):
        return (self[alias] for alias in self.connections_info)
    
    def __len__(self):
        return len(self.keys())
    
    def __contains__(self, item):
        return item in dict(self.items())
    
    



########NEW FILE########
__FILENAME__ = base

import signalqueue
from signalqueue.utils import json, logg
from signalqueue import SQ_RUNMODES as runmodes

class QueueBase(object):
    """
    Base class for a signalqueue backend.
    
    Implementors of backend interfaces will want to override these methods:
    
        * ping(self)            # returns a boolean
        * push(self, value)
        * pop(self)             # returns a serialized signal value
        * count(self)           # returns an integer
        * clear(self)
        * values(self)          # returns a list of serialized signal values
    
    If your implementation has those methods implemented and working,
    your queue should run.
    
    Only reimplement enqueue(), retrieve(), and dequeue() if you know what
    you are doing and have some debugging time on your hands.
    
    The JSON structure of a serialized signal value looks like this:
    
        {
            "instance": {
                "modl_name": "testmodel",
                "obj_id": 1,
                "app_label": "signalqueue"
            },
            "signal": {
                "signalqueue.tests": "test_sync_function_signal"
            },
            "sender": {
                "modl_name": "testmodel",
                "app_label": "signalqueue"
            },
            "enqueue_runmode": 4
        }
    
    """
    runmode = None
    queue_name = None
    queue_interval = None
    queue_options = {}
    
    def __init__(self, *args, **kwargs):
        """
        It's a good idea to call super() first in your overrides,
        to take care of params and whatnot like these.
        
        """
        self.runmode = kwargs.pop('runmode', None)
        self.queue_name = kwargs.pop('queue_name', "default")
        self.queue_interval = kwargs.pop('queue_interval', None)
        self.queue_options = {}
        self.queue_options.update(kwargs.pop('queue_options', {}))
        super(QueueBase, self).__init__()
    
    def ping(self):
        raise NotImplementedError(
            "WTF: %s needs a Queue.ping() implementaton" %
                self.__class__.__name__)
    
    def push(self, value):
        raise NotImplementedError(
            "WTF: %s backend needs a Queue.push() implementaton" %
                self.__class__.__name__)
    
    def pop(self):
        raise NotImplementedError(
            "WTF: %s backend needs a Queue.pop() implementaton" %
                self.__class__.__name__)
    
    def count(self):
        return NotImplementedError(
            "WTF: %s backend needs a Queue.count() implementaton" %
                self.__class__.__name__)
    
    def clear(self):
        raise NotImplementedError(
            "WTF: %s backend needs a Queue.flush() implementaton" %
                self.__class__.__name__)
    
    def values(self, **kwargs):
        raise NotImplementedError(
            "WTF: %s backend needs a Queue.values() implementaton" %
                self.__class__.__name__)
    
    def enqueue(self, signal, sender=None, **kwargs):
        """ Serialize the parameters of a signal call, encode
            the serialized structure, and push the encoded
            string onto the queue. """
        
        if signal.regkey is not None:
            if self.ping():
                queue_json = {
                    'signal': { signal.regkey: signal.name },
                    #'sender': None,
                    'enqueue_runmode': self.runmode }
                
                if sender is not None:
                    queue_json.update({
                        'sender': dict(
                            app_label=sender._meta.app_label,
                            modl_name=sender._meta.object_name.lower()) })
                
                for k, v in kwargs.items():
                    queue_json.update({ k: signal.mapping.demap(v), })
                
                #print queue_json
                self.push(json.dumps(queue_json))
                return queue_json
        else:
            raise signalqueue.SignalRegistryError("Signal has no regkey value.")
    
    def retrieve(self):
        """ Pop the queue, decode the popped signal without deserializing,
            returning the serialized data. """
        
        if self.count() > 0:
            out = self.pop()
            if out is not None:
                return json.loads(out)
        return None
    
    def dequeue(self, queued_signal=None):
        """ Deserialize and execute a signal, either from the queue or as per the contents
        of the queued_signal kwarg.
        
        If queued_signal contains a serialized signal call datastructure,* dequeue()
        will deserialize and execute that serialized signal without popping the queue.
        If queued_signal is None, it will call retrieve() to pop the queue for the next
        signal, which it will execute if one is returned successfully.
        
        * See the QueueBase docstring for an example. """
        
        from django.db.models.loading import cache
        
        if queued_signal is None:
            queued_signal = self.retrieve()
        
        if queued_signal is not None:
            #logg.debug("Dequeueing signal: %s" % queued_signal)
            pass
        else:
            return (None, None)
        
        signal_dict = queued_signal.get('signal')
        sender_dict = queued_signal.get('sender')
        regkey, name = signal_dict.items()[0]
        sender = None
        
        # specifying a sender is optional.
        if sender_dict is not None:
            try:
                sender = cache.get_model(
                    str(sender_dict['app_label']),
                    str(sender_dict['modl_name']))
            except (KeyError, AttributeError), err:
                logg.info("*** Error deserializing sender_dict: %s" % err)
                sender = None
        
        enqueue_runmode = queued_signal.get('enqueue_runmode', runmodes['SQ_ASYNC_REQUEST'])
        
        kwargs = {
            'dequeue_runmode': self.runmode,
            'enqueue_runmode': enqueue_runmode,
        }
        
        thesignal = None
        if regkey in signalqueue.SQ_DMV:
            for signal in signalqueue.SQ_DMV[regkey]:
                if signal.name == name:
                    thesignal = signal
                    break
        else:
            raise signalqueue.SignalRegistryError(
                "Signal '%s' not amongst the registered: %s)." % (
                    regkey, ', '.join(signalqueue.SQ_DMV.keys())))
        
        if thesignal is not None:
            for k, v in queued_signal.items():
                if k not in ('signal', 'sender', 'enqueue_runmode', 'dequeue_runmode'):
                    kwargs.update({ k: thesignal.mapping.remap(v), })
            
            # result_list is a list of tuples, each containing a reference
            # to a callback function at [0] and that callback's return at [1]
            # ... this is per what the Django signal send() implementation returns;
            # AsyncSignal.send_now() returns whatever it gets from Signal.send().
            result_list = self.dispatch(thesignal, sender=sender, **kwargs)
            return (queued_signal, result_list)
        
        else:
            raise signalqueue.SignalRegistryError(
                "No registered signals named '%s'." % name)
    
    def dispatch(self, signal, sender, **kwargs):
        return signal.send_now(sender=sender, **kwargs)
    
    def next(self):
        """
        Retrieve and return a signal from the queue without executing it.
        
        This allows one to iterate through a queue with access to the signal data,
        and control over the dequeue execution -- exceptions can be caught, signals
        can be conditionally dealt with, and so on, as per your needs.
        
        This example script dequeues and executes all of the signals in one queue.
        If a signal's execution raises a specific type of error, its call data is requeued
        into a secondary backup queue (which the backup queue's contents can be used however
        it may most please you -- e.g. dequeued into an amenable execution environment;
        inspected as a blacklist by the signal-sending code to prevent known-bad calls;
        analytically aggregated into pie charts in real-time and displayed distractingly
        across the phalanx of giant flatscreens festooning the walls of the conference room
        you stand in when subjecting yourself and your big pitch to both the harsh whim
        of the venture capitalists whom you manage to coax into your office for meetings
        and the simultaneously indolent and obsequious Skype interview questions from 
        B-list TechCrunch blog writers in search of blurbs they can grind into filler
        for their daily link-baiting top-ten-reasons-why contribution to the ceaseless 
        maelstrom that is the zeitgeist of online technology news; et cetera ad nauseum):
        
        
            from myapp.logs import logging
            from myapp.exceptions import MyDequeueError
            from signalqueue import SignalRegistryError
            import math, signalqueue.worker
            myqueue = signalqueue.worker.queues['myqueue']
            backupqueue = signalqueue.worker.queues['backup']
            
            tries = 0
            wins = 0
            do_overs = 0
            perc = lambda num, tot: int(math.floor((float(num)/float(tot))*100))
            logging.info("Dequeueing %s signals from queue '%s'..." % (tries, myqueue.queue_name))
            
            for next_signal in myqueue:
                tries += 1
                try:
                    result, spent_signal = myqueue.dequeue(queued_signal=next_signal)
                except MyDequeueError, err:
                    # execution went awry but not catastrophically so -- reassign it to the backup queue
                    logging.warn("Error %s dequeueing signal: %s" % (repr(err), str(next_signal)))
                    logging.warn("Requeueing to backup queue: %s" % str(backupqueue.queue_name))
                    backupqueue.push(next_signal)
                    do_overs += 1
                except (SignalRegistryError, AttributeError), err:
                    # either this signal isn't registered or is somehow otherwise wack -- don't requeue it
                    logging.error("Fatal error %s dequeueing signal: %s" % (repr(err), str(next_signal)))
                else:
                    logging.info("Successful result %s from dequeued signal: %s " % (result, repr(spent_signal)))
                    wins += 1
            
            logging.info("Successfully dequeued %s signals (%s%% of %s total) from queue '%s'" %
                wins, perc(wins, tries), tries, myqueue.queue_name)
            logging.info("Requeued %s signals (%s%% of %s total) into queue '%s'" %
                do_overs, perc(do_overs, tries), tries, backupqueue.queue_name)
        
        """
        if not self.count() > 0:
            raise StopIteration
        return self.retrieve()
    
    def __iter__(self):
        return self
    
    def __getitem__(self, idx):
        """ Syntax sugar: myqueue[i] gives you the same value as myqueue.values()[i] """
        return self.values().__getitem__(idx)
    
    def __setitem__(self, idx, val):
        raise NotImplementedError(
            "OMG: Queue backend doesn't define __setitem__() -- items at specific indexes cannot be explicitly set.")
    
    def __delitem__(self, idx, val):
        raise NotImplementedError(
            "OMG: Queue backend doesn't define __delitem__() -- items at specific indexes cannot be explicitly removed.")
    
    def __repr__(self):
        """ Returns a JSON-stringified array, containing all enqueued signals. """
        return "[%s]" % ",".join([str(value) for value in self.values()])
    
    def __str__(self):
        """ Returns a JSON-stringified array, containing all enqueued signals. """
        return repr(self)
    
    def __unicode__(self):
        """ Returns a JSON-stringified array, containing all enqueued signals,
            properly pretty-printed. """
        import json as library_json
        return u"%s" % library_json.dumps(library_json.loads(repr(self)), indent=4)

########NEW FILE########
__FILENAME__ = celeryqueue

from celery import Task
from celery.registry import tasks
from kombu import Connection
import kombu.exceptions

import signalqueue
from signalqueue.worker.base import QueueBase
#from signalqueue.utils import logg

def taskmaster(sig):
    class CelerySignalTask(Task):
        name = "%s:%s" % (sig.regkey, sig.name)
        store_errors_even_if_ignored = True
        ignore_result = False
        track_started = True
        acks_late = True
        
        def __init__(self):
            self.signal_regkey = sig.regkey
            self.signal_name = sig.name
        
        @property
        def signal(self):
            for registered_signal in signalqueue.SQ_DMV[self.signal_regkey]:
                if registered_signal.name == self.signal_name:
                    return registered_signal
            return None
        
        def run(self, sender=None, **kwargs):
            self.signal.send_now(sender=sender, **kwargs)
        
    return CelerySignalTask

class CeleryQueue(QueueBase):
    """ At some point this will adapt `django-signalqueue` for use
        with popular `(dj)celery` platform (but not today).
        
        When this class is done, I will discuss it here. """
    
    def __init__(self, *args, **kwargs):
        super(CeleryQueue, self).__init__(*args, **kwargs)
        
        self.celery_queue_name = self.queue_options.pop('celery_queue_name', 'inactive')
        self.serializer = self.queue_options.pop('serializer', 'json')
        self.compression = self.queue_options.pop('compression', None)
        self.kc = Connection(**self.queue_options)
        self.kc.connect()
        
        self.qc = self.kc.SimpleQueue(name=self.celery_queue_name)
    
    def ping(self):
        return self.kc.connected and not self.qc.channel.closed
    
    def push(self, value):
        self.qc.put(value,
            compression=self.compression, serializer=None)
    
    def pop(self):
        virtual_message = self.qc.get(block=False, timeout=1)
        return virtual_message.payload
    
    def count(self):
        try:
            return self.qc.qsize()
        except kombu.exceptions.StdChannelError:
            self.qc.queue.declare()
            return 0
    
    def clear(self):
        self.qc.clear()
    
    def values(self, **kwargs):
        return []
    
    def __getitem__(self, idx):
        #return self.values().__getitem__(idx)
        return ''
    
    def dispatch(self, signal, sender=None, **kwargs):
        task_name = "%s:%s" % (signal.regkey, signal.name)
        try:
            result = tasks[task_name].delay(sender=sender, **kwargs)
        except tasks.NotRegistered:
            pass
        else:
            return result
    

########NEW FILE########
__FILENAME__ = poolqueue
#!/usr/bin/env python
# encoding: utf-8
"""
poolqueue.py

Internal 'pooling' of signal-dispatcher instances
that the tornado worker can safely deal with.

Created by FI$H 2000 on 2011-07-05.
Copyright (c) 2011 OST, LLC. All rights reserved.

"""
from tornado.ioloop import PeriodicCallback

class PoolQueue(object):
    
    def __init__(self, *args, **kwargs):
        super(PoolQueue, self).__init__()
        
        import signalqueue
        signalqueue.autodiscover()
        
        from django.conf import settings as django_settings
        from signalqueue.utils import logg
        from signalqueue.worker import backends
        from signalqueue import SQ_RUNMODES as runmodes
        
        self.active = kwargs.get('active', True)
        self.halt = kwargs.get('halt', False)
        self.logx = kwargs.get('log_exceptions', True)
        
        self.interval = 1
        self.queue_name = kwargs.get('queue_name', "default")
        
        self.runmode = runmodes['SQ_ASYNC_MGMT']
        self.queues = backends.ConnectionHandler(django_settings.SQ_QUEUES, self.runmode)
        self.signalqueue = self.queues[self.queue_name]
        self.signalqueue.runmode = self.runmode
        self.logg = logg
        
        # use interval from the config if it exists
        interval = kwargs.get('interval', self.signalqueue.queue_interval)
        if interval is not None:
            self.interval = interval
        
        if self.interval > 0:
            
            if self.logx:
                if self.halt:
                    self.shark = PeriodicCallback(self.joe_flacco, self.interval*10)
                else:
                    self.shark = PeriodicCallback(self.ray_rice, self.interval*10)
            
            else:
                if self.halt:
                    self.shark = PeriodicCallback(self.cueball_scratch, self.interval*10)
                else:
                    self.shark = PeriodicCallback(self.cueball, self.interval*10)
        
        if self.active:
            self.shark.start()
    
    def stop(self):
        self.active = False
        self.shark.stop()
    
    def rerack(self):
        self.active = True
        self.shark.start()
    
    """ Non-logging cues """
    
    def cueball(self):
        try:
            self.signalqueue.dequeue()
        except Exception, err:
            self.logg.info("--- Exception during dequeue: %s" % err)
    
    def cueball_scratch(self):
        try:
            self.signalqueue.dequeue()
        except Exception, err:
            self.logg.info("--- Exception during dequeue: %s" % err)
        if self.signalqueue.count() < 1:
            self.logg.info("Queue exhausted, exiting...")
            raise KeyboardInterrupt
    
    """ Logging cues (using the Raven client for Sentry) """
    
    def ray_rice(self):
        from signalqueue.utils import log_exceptions
        with log_exceptions():
            self.signalqueue.dequeue()
    
    def joe_flacco(self):
        from signalqueue.utils import log_exceptions
        with log_exceptions():
            self.signalqueue.dequeue()
        if self.signalqueue.count() < 1:
            self.logg.info("Queue exhausted, exiting...")
            raise KeyboardInterrupt
    
########NEW FILE########
__FILENAME__ = supercell
from os import path as op

import tornado
import tornado.web
import tornado.httpserver
import tornadio2
import tornadio2.router
import tornadio2.server
import tornadio2.conn

#ROOT = op.normpath(op.dirname(__file__))
from signalqueue.templatetags.signalqueue_status import sockio

class IndexHandler(tornado.web.RequestHandler):
    "" "Regular HTTP handler to serve the chatroom page """
    def get(self):
        self.render('index.html')


class SocketIOHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(sockio('socket.io.js'))


class ChatConnection(tornadio2.conn.SocketConnection):
    clients = set()
    
    def on_open(self, info):
        #self.send("Welcome from the server.")
        self.clients.add(self)
    
    def on_message(self, message):
        # Pong message back
        for p in self.clients:
            p.send(message)
    
    def on_close(self):
        if self in self.clients:
            self.clients.remove(self)


# Create tornadio server
ChatRouter = tornadio2.router.TornadioRouter(ChatConnection)


# Create socket application
sock_app = tornado.web.Application(
    ChatRouter.urls,
    flash_policy_port=843,
    flash_policy_file=sockio('flashpolicy.xml'),
    socket_io_port=8002,
)

# Create HTTP application
http_app = tornado.web.Application([
    (r"/", IndexHandler),
    (r"/socket.io.js", SocketIOHandler)
])

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    # Create http server on port 8001
    http_server = tornado.httpserver.HTTPServer(http_app)
    http_server.listen(8001)

    # Create tornadio server on port 8002, but don't start it yet
    tornadio2.server.SocketServer(sock_app, auto_start=False)

    # Start both servers
    tornado.ioloop.IOLoop.instance().start()
########NEW FILE########
__FILENAME__ = vortex
#!/usr/bin/env python
# encoding: utf-8
"""
vortex.py

The name 'tornado' was taken, you see.

Created by FI$H 2000 on 2011-07-05.
Copyright (c) 2011 OST, LLC. All rights reserved.
"""

import sys, hashlib, curses, logging

from django.conf import settings
from django.template import Context, loader
import tornado.options
import tornado.web
import tornado.websocket
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.options import define
from tornado.log import LogFormatter
from signalqueue.utils import json
from signalqueue.worker import queues
from signalqueue.worker.poolqueue import PoolQueue

define('port', default=settings.SQ_WORKER_PORT, help='Queue server HTTP port', type=int)

class Application(tornado.web.Application):
    def __init__(self, **kwargs):
        from django.conf import settings as django_settings
        
        nm = kwargs.get('queue_name', "default")
        self.queue_name = nm
        
        handlers = [
            (r'/socket.io/1/', MainHandler),
            (r'/', MainHandler),
            (r'/status', QueueServerStatusHandler),
            (r'/sock/status', QueueStatusSock),
        ]
        
        settings = dict(
            static_path=django_settings.MEDIA_ROOT,
            xsrf_cookies=True,
            cookie_secret=hashlib.sha1(django_settings.SECRET_KEY).hexdigest(),
            logging='info',
            queue_name=nm,
        )
        
        tornado.web.Application.__init__(self, handlers, **settings)
        self.queues = {}
        if nm is not None:
            self.queues.update({
                nm: PoolQueue(queue_name=nm, active=True,
                    halt=kwargs.get('halt_when_exhausted', False),
                    log_exceptions=kwargs.get('log_exceptions', True),
                ),
            })


class BaseQueueConnector(object):
    
    def queue(self, queue_name=None):
        if queue_name is None:
            queue_name = self.application.queue_name
        if queue_name not in queues.keys():
            raise IndexError("No queue named %s is defined" % queue_name)
        
        if not queue_name in self.application.queues:
            self.application.queues[queue_name] = PoolQueue(queue_name=queue_name, active=False)
        
        return self.application.queues[queue_name]
    
    @property
    def defaultqueue(self):
        return self.queue('default')
    
    def clientlist_get(self):
        if not hasattr(self.application, 'clientlist'):
            self.application.clientlist = []
        return self.application.clientlist
    def clientlist_set(self, val):
        self.application.clientlist = val
    def clientlist_del(self):
        del self.application.clientlist
    
    clientlist = property(clientlist_get, clientlist_set, clientlist_del)
    

class QueueStatusSock(tornado.websocket.WebSocketHandler, BaseQueueConnector):
    def open(self):
        self.clientlist.append(self)
    
    def on_message(self, inmess):
        mess = json.loads(str(inmess))
        nm = mess.get('status', "default")
        self.write_message({
            nm: self.queue(nm).signalqueue.count(),
        })
    
    def on_close(self):
        if self in self.clientlist:
            self.clientlist.remove(self)

class BaseHandler(tornado.web.RequestHandler, BaseQueueConnector):
    pass

class MainHandler(BaseHandler):
    def get(self):
        self.write("YO DOGG!")

class QueueServerStatusHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(QueueServerStatusHandler, self).__init__(*args, **kwargs)
        self.template = loader.get_template('status.html')
    
    def get(self):
        nm = self.get_argument('queue', self.application.queue_name)
        queue = self.queue(nm).signalqueue
        self.write(
            self.template.render(Context({
                'queue_name': nm,
                'items': [json.loads(morsel) for morsel in queue.values()],
                'count': queue.count(),
            }))
        )



def main():
    logg = logging.getLogger("signalqueue")
    # Set up color if we are in a tty and curses is installed
    
    color = False
    if curses and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                color = True
        except:
            pass
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter(color=color))
    logg.addHandler(channel)
    
    logg.info("YO DOGG.")
    from django.conf import settings
    
    try:
        tornado.options.parse_command_line()
        http_server = HTTPServer(Application())
        http_server.listen(settings.SQ_WORKER_PORT)
        IOLoop.instance().start()
        
    except KeyboardInterrupt:
        print 'NOOOOOOOOOOOO DOGGGGG!!!'


if __name__ == '__main__':
    main()
    



########NEW FILE########
