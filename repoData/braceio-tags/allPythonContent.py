__FILENAME__ = generator
import os
import sys
import time
import posixpath
import threading

if sys.version > '3':
    import urllib.parse
    from http.server import HTTPServer
    from http.server import SimpleHTTPRequestHandler
else:
    import urllib
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

from . import tags
from . import utils
from . import templatelang

def build_file(filename, outfilename, root='.', create_dir=True):
    filepath = os.path.join(root, filename)
    with utils.open_file(filepath) as infile:
        try:
            if sys.version > '3':
                content = str(infile.read(), 'utf-8')
            else:
                content = unicode(infile.read(), 'utf-8')
            output = tags.render(content, filename=filename, rootdir=root)
        except templatelang.ParseBaseException as e:
            utils.print_parse_exception(e, filename)
            return

    with utils.open_file(outfilename, "w", create_dir=create_dir) as outfile:
        if sys.version > '3':
            outfile.write(output)
        else:
            outfile.write(output.encode('utf-8'))

            
def build_files(root='.', dest='_site', pattern='**/*.html', 
                exclude='_*/**', watch=False, force=False):
    try:
        os.stat(os.path.join(root, 'index.html'))
    except OSError:
        if not force:
            msg = "Oops, we can't find an index.html in the source folder.\n"+\
                  "If you want to build this folder anyway, use the --force\n"+\
                  "option."
            print(msg)
            sys.exit(1)

    print("Building site from '{0}' into '{1}'".format(root, dest))

    exclude = exclude or os.path.join(dest, '**')
    for filename in utils.walk_folder(root or '.'):
        included = utils.matches_pattern(pattern, filename)
        excluded = utils.matches_pattern(exclude, filename)
        destfile = os.path.join(dest, filename)
        if included and not excluded: 
            build_file(filename, destfile, root=root)
        elif not excluded:
            filepath = os.path.join(root, filename)
            destpath = os.path.join(dest, filename)
            utils.copy_file(filepath, destpath)

    if watch:
        observer = _watch(root=root,
                          dest=dest,
                          pattern=pattern,
                          exclude=exclude)
        if not observer:
            return
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


def _watch(root='.', dest='_site', pattern='**/*.html', exclude='_*/**'):

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        msg = "The build --watch feature requires watchdog. \n"\
            + "Please install it with 'easy_install watchdog'."
        print(msg)
        return None

    class handler(FileSystemEventHandler):
        def on_any_event(self, event):
            exclude_path = os.path.join(os.getcwd(), exclude)
            if not utils.matches_pattern(exclude_path, event.src_path):
                build_files(root=root,
                            dest=dest,
                            pattern=pattern,
                            exclude=exclude)

    observer = Observer()
    observer.schedule(handler(), root, recursive=True)
    observer.start()

    print("Watching '{0}' ...".format(root))

    return observer


def serve_files(root='.', dest='_site', pattern='**/*.html', 
                exclude='_*/**', watch=False, port=8000, force=False):

    # setup server

    class RequestHandler(SimpleHTTPRequestHandler):
        
        def translate_path(self, path):
            root = os.path.join(os.getcwd(), dest)

            # normalize path and prepend root directory
            path = path.split('?',1)[0]
            path = path.split('#',1)[0]
            if sys.version > '3':
                path = posixpath.normpath(urllib.parse.unquote(path))
            else:
                path = posixpath.normpath(urllib.unquote(path))
            words = path.split('/')
            words = [_f for _f in words if _f]
            
            path = root
            for word in words:
                drive, word = os.path.splitdrive(word)
                head, word = os.path.split(word)
                if word in (os.curdir, os.pardir):
                    continue
                path = os.path.join(path, word)

            return path

    class StoppableHTTPServer(HTTPServer):

        def serve_until_shutdown(self):
            self._stopped = False
            while not self._stopped:
                try:
                    httpd.handle_request()
                except:
                    self._stopped=True
                    self.server_close()


        def shutdown(self):
            self._stopped = True            
            self.server_close()

    server_address = ('', port)
    httpd = StoppableHTTPServer(server_address, RequestHandler)
    server_thread = threading.Thread(
        target=httpd.serve_until_shutdown)
    server_thread.daemon = True
    server_thread.start()

    print("HTTP server started on port {0}".format(server_address[1]))

    # build files

    build_files(root=root,
                dest=dest,
                pattern=pattern,
                exclude=exclude,
                force=force)

    # watch files while server running

    if watch:
        observer = _watch(root=root,
                          dest=dest,
                          pattern=pattern,
                          exclude=exclude)
        if not observer:
            return
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            httpd.shutdown()
        observer.join()

    else:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            httpd.shutdown()



NEW_INDEX_STR = """<!DOCTYPE html>
<html>
{% include _partials/header.html %}
<body>
  {% include _partials/nav.html %}
  <h1>Welcome!</h1>
</body>
</html>"""

NEW_ABOUT_STR = """<!DOCTYPE html>
<html>
{% include _partials/header.html %}
<body>
  {% include _partials/nav.html %}
  <h1>About!</h1>
</body>
</html>"""

NEW_HEADER_STR = """
<head>
  <title>My new site</title>
  <link rel="stylesheet" href="/css/style.css" />
</head>"""

NEW_NAV_STR = """
  <ul>
    <li>
      <a href="/"{% is index.html %} class="active"{% endis %}>
        home
      </a>
    </li>
    <li>
      <a href="/about.html"{% is about.html %} class="active"{% endis %}>
        about
      </a>
    </li>
  </ul>"""

NEW_STYLE_STR = """.active {font-weight:bold;}"""

NEW_SITE = {
    'index.html': NEW_INDEX_STR,
    'about.html': NEW_ABOUT_STR,
    '_partials/header.html': NEW_HEADER_STR,
    '_partials/nav.html': NEW_NAV_STR,
    'css/style.css': NEW_STYLE_STR
}

def new_site(root='.', force=False):
    try:
        os.stat(os.path.join(root, 'index.html'))
        if not force:
            msg = "Oops, there's already an index.html file in the source \n"+\
                  "folder. If you want to overwrite this folder with a new \n"+\
                  "site, use the --force option."
            print(msg)
            sys.exit(1)
    except OSError:
        pass

    print("Creating new site in '{0}'.".format(root))

    for fname, text in list(NEW_SITE.items()):
        fpath = os.path.join(root, fname)
        with utils.open_file(fpath, "w", create_dir=True) as afile:
            afile.write(text)

########NEW FILE########
__FILENAME__ = tags
import os

from .templatelang import TemplateLanguage

lang = TemplateLanguage(openseq='{%', closeseq='%}')

@lang.add_tag
def include(path, context={}):
    '''
    Renders the content of a file. File paths should be relative
    to the site's root folder. Ex: {% include nav.html %}
    '''
    fullpath = os.path.join(context.get('rootdir'), path)
    return open(fullpath).read()


@lang.add_tag_with_name('is')
def _is(path, body='', context={}):
    '''
    Renders the tag body if the path matches the current file. File paths 
    should be relative to the site's root folder. 
    Ex: {% is index.html %}Home!{% endis %}
    '''
    return body if path == context.get('filename') else ''


# ---- Add your custom tags here! -----

# Example:

# @lang.add_tag
# def print3x(style, body=u'', context={}):
#     ''' A tag that appends 3 copies of its body '''
#     result = body + body + body
#     if style == "bold":
#         result = u'<b>' + result + u'</b>'
#     return result

# Notes:

# - positional arguments define the tag's required arguments.
# - If you specify a `body` keyword argument, then the tag will require a body.
# - All tag functions must accept a `context` keyword argument. 

# You can also define tags that accept a variable argument list like so:

# @lang.add_tag
# def whatever(*args, **kwargs):
#     return str(len(args))


def render(content, filename='', rootdir='.'):
    ''' 
    Renders a content string containing template code into an output string. 
    Uses the tags specified above. Filename and rootdir are added to the 
    context passed to the tag functions.
    '''
    return lang.parse(content, filename=filename, rootdir=rootdir)

########NEW FILE########
__FILENAME__ = templatelang
from pyparsing import *
import inspect


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class TagErrorArguments(Exception):
    def __init__(self, tagname, nargs, args):
        params = (tagname, nargs, " ".join(args))
        errstr = "malformed tag '{0}' should have {1} argument(s), got '{2}'"
        self.msg = errstr.format(*params)

    def __str__(self):
        return self.msg


class TagErrorBody(Exception):
    def __init__(self, tagname, req_body, has_body):
        req = '' if req_body else "n't"
        has = 'does' if has_body else "doesn't"
        params = (tagname, req, has)
        errstr = "malformed tag '{0}' should{1} have a body, but {2}"
        self.msg = errstr.format(*params)

    def __str__(self):
        return self.msg


class TagErrorException(ParseBaseException):
    def __init__(self, parsestr, loc, exc, dev=False):
        if dev:
            import traceback
            msg = traceback.print_exc()
        else:
            msg = str(exc)
        super(TagErrorException, self).__init__(parsestr, loc=loc, msg=msg)


# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def debug_action(name=''):
    def _wrapped(parsestr, loc, tokens):
        print(name, ": ", parsestr[0:loc], '*', parsestr[loc:], "-->", tokens)
    return _wrapped


# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class TemplateLanguage(object):
    ''' A generic tag-based language supporting nested tags. 

    Each tag has a name, optional arguments, and an optional closing tag.

    Examples: 

    {% tagname arg1 arg2 %}

    {% tagname args %}
        tag body
    {% endtagname %}

    The action performed by each tag must be supplied in a tag definition,
    either passed to the __init__ method, or by using the add_tag 
    decorators.
    '''

    # decorators --------------------------------------------------------------

    def add_tag_with_name(self, name):
        ''' Adds a tag to the language. 

        The function for the decorator should 
        accept a list of positional args, the context keyword arg, and an
        optional body keyword arg.

        Example:

        @language.add_tag_with_name('mytag')
        def tagfn(arg1, arg2, body=u'', context={}):
            return "tag args: {0}, body: {1}".format([arg1, arg2], body])

        The positional args define the required arguments for the tag. 
        If the body keyword arg is present the tag must have a body and
        closing tag.

        Tag argument checking won't happen if the development flag is set.
        '''
        def _decorator(fn):
            posargs, varargs, varkwargs, defaults = inspect.getargspec(fn)
            req_body = "body" in posargs
            nargs = len(posargs)
            if "context" in posargs:
                nargs -= 1
            if req_body:
                nargs -= 1

            def _wrapper(*args, **kwargs):
                if not self._development:
                    if (varargs and len(args) < nargs) or len(args) != nargs:
                        raise TagErrorArguments(name, nargs, args)
                    has_body = 'body' in kwargs
                    if has_body != req_body:
                        raise TagErrorBody(name, req_body, has_body)
                return fn(*args, **kwargs)

            self._tags[name] = _wrapper

            return _wrapper
        return _decorator


    def add_tag(self, fn):
        ''' Shortcut for add_tag_with_name.

        Uses the function's name as the tag name.

        Example:

        @language.add_tag
        def mytag(body=u'', context={}):
            return "tag body: "+body
        '''
        return self.add_tag_with_name(fn.__name__)(fn)


    # language specification --------------------------------------------------

    def _mkopentag(self, name):
        tagname = CaselessKeyword(name)
        quote = quotedString.setParseAction(removeQuotes)
        arg = Optional(White()).suppress() + CharsNotIn(" \t\r\n")
        args = Group(ZeroOrMore(quote | arg))
        rawargs = SkipTo(self._tagclose)
        rawargs.setParseAction(lambda toks: args.parseString(toks[0]))
        return self._tagopen + tagname + rawargs + self._tagclose


    def _mkclosetag(self, name):
        tagname = CaselessKeyword("end"+name)
        return self._tagopen + tagname.suppress() + self._tagclose


    def _mktag(self, name, body):
        opentag = self._mkopentag(name)
        closetag = self._mkclosetag(name)
        tag = opentag + body + closetag | opentag
        return tag


    def _mkparser(self, tags):
        onechar = CharsNotIn('', exact=1)
        freetext = Combine(OneOrMore(~self._tagopen + ~self._tagclose + onechar))
        anytag = Forward()
        body = originalTextFor(ZeroOrMore(anytag | freetext))
        anytag << MatchFirst([self._mktag(key, body) for key in list(tags.keys())])
        return anytag


    def _mkparsefn(self, context):
        def _parsefn(parsestr, loc, tokens):
            name, parseresult = tokens[:2]
            args = parseresult.asList()
            try:
                fn = self._tags[name]
            except KeyError:
                # This should never be reached since the parser 
                # won't match a tag that's not in the list
                raise
            kwargs = {'context': context}
            if len(tokens) > 2:
                kwargs.update({'body': tokens[2]})
            try:
                processed = fn(*args, **kwargs)
            except ParseBaseException:
                raise
            except Exception as e:
                raise TagErrorException(parsestr, loc, e, self._development)
            return self.parse(processed, **context)
        return _parsefn


    # public methods ----------------------------------------------------------

    def __init__(self, tags=None, openseq='{%', closeseq='%}', development=False):
        ''' Creates a new template language instance.

        If the tag keyword argument isn't provided, tags should be created
        using the add_tag decorators. Otherwise, tags should be a dictionairy
        of name/function pairs.

        If the development flag is set, tag argument checking is disabled and
        errors will include a stack trace.
        '''
        self._tags = {}
        self._development = development
        self._openseq = openseq
        self._tagopen = Literal(openseq).suppress()
        self._tagclose = Literal(closeseq).suppress()

        if tags:
            for name, fn in tags.items():
                self.add_tag_with_name(name)(fn)
            self._parser = self._mkparser(self._tags)
        else:
            self._parser = None


    def parse(self, string, **context):
        ''' Parses a template string. 

        For each tag in the input string, calls the tag functions and replaces
        the tag with the function results. Keyword arguments provided to parse 
        will be added to the context passed to the tag functions.
        '''
        if self._openseq in string:
            if not self._parser:
                self._parser = self._mkparser(self._tags)
            parsefn = self._mkparsefn(context.copy())
            parser = self._parser.copy()
            parser.setParseAction(parsefn)
            return parser.transformString(string)
        else:
            return string


########NEW FILE########
__FILENAME__ = utils
import os
import fnmatch
import shutil


def print_parse_exception(exc, filename=None):
    msg = "Parse Error "
    if filename:
        msg += "while compiling {0}".format(filename)
    msg += ": " + exc.msg + "\n"
    msg += exc.line + "\n"
    msg += " "*(exc.column-1) + "^"
    print(msg)


def walk_folder(root='.'):
    for subdir, dirs, files in os.walk(root):
        reldir = subdir.lstrip(root).lstrip('/')
        for filename in files:
            yield os.path.join(reldir, filename)


def open_file(path, mode='rb', create_dir=False, create_mode=0o755):
    # Opens the given path. If create_dir is set, will
    # create all intermediate folders necessary to open
    try:
        newfile = open(path, mode)
    except IOError:
        # end here if not create_dir
        if not create_dir:
            raise
        newfile = None

    if not newfile:
        # may raise OSError
        filedir = os.path.split(path)[0]
        os.makedirs(filedir, create_mode)
        newfile = open(path, mode)

    return newfile


def copy_file(src, dst, create_dir=True, create_mode=0o755):
    try:
        shutil.copy2(src, dst)
    except IOError:
        if not create_dir:
            raise
        # may raise OSError
        filedir = os.path.split(dst)[0]
        os.makedirs(filedir, create_mode)
        shutil.copy2(src, dst)


def matches_pattern(pattern, filepath):

    def _is_match(pattern_list, token_list):
        if not pattern_list or not token_list:
            return False
        i, j = 0, 0
        while True:
            if pattern_list[j] == '**':
                if j+1 == len(pattern_list): return True
                if _is_match(pattern_list[j+1:], token_list[i:]):
                    return True
                else:
                    i+=1 
            elif fnmatch.fnmatch(token_list[i], pattern_list[j]):
                i+=1
                j+=1
            else:
                return False
            if i==len(token_list) and j==len(pattern_list):
                return True
            if i==len(token_list) or j==len(pattern_list):
                return False

    return _is_match(pattern.strip('/').split('/'), 
                     filepath.strip('/').split('/'))


########NEW FILE########
__FILENAME__ = test_generator
import unittest
import os
import shutil
from filecmp import dircmp
 
from tags.utils import *
from tags import generator


class TestTemplateLanguage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        wwwroot = os.path.dirname(os.path.realpath(__file__))+"/www"
        cls.cwd = os.getcwd()
        os.chdir(wwwroot)
        shutil.rmtree(os.path.join(wwwroot, "_site"), ignore_errors=True)


    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.cwd)


    def test_build_file(self):
        generator.build_file('index.html', "_site/index.html")
        self.assertEqual(dircmp('_gen_result_1', '_site').diff_files, [])


    def test_build_files(self):
        generator.build_files()
        self.assertEqual(dircmp('_gen_result_2', '_site').diff_files, [])


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_templatelang
import unittest
import os
import sys

from tags.templatelang import TemplateLanguage

def _testfile(name):
    root = os.path.dirname(os.path.realpath(__file__))
    return open(root+'/'+name)

class TestTemplateLanguage(unittest.TestCase):

    def setUp(self):

        def _test(*args, **kwargs):
            args = list(args)
            body = kwargs.pop('body','')
            if body:
                args.append(body)
            return ', '.join(args)

        self.lang = TemplateLanguage(tags={'t': _test}, development=True)

        self.unicodedata = []
        for line in _testfile("unicodedata.txt"):
            if sys.version > '3':
                test, result = str(line).split(' --> ')
            else:
                test, result = unicode(line, 'utf-8').split(' --> ')
            self.unicodedata.append({
                'test': test.strip(), 
                'result': result.strip()
            })


    def test_tags(self):
        result = self.lang.parse("hello {% t world %}")
        self.assertEqual(result, "hello world")
        result = self.lang.parse("hello {%t world%}")
        self.assertEqual(result, "hello world")
        result = self.lang.parse("hello {%t world yeah %}")
        self.assertEqual(result, "hello world, yeah")
        result = self.lang.parse("hello {%t 'big world' %}")
        self.assertEqual(result, "hello big world")
        result = self.lang.parse("hello {%t 'big world' uh... %}")
        self.assertEqual(result, "hello big world, uh...")
        result = self.lang.parse(self.unicodedata[0]['test'])
        self.assertEqual(result, self.unicodedata[0]['result'])


    def test_block_tag(self):
        result = self.lang.parse("hello {% t %}world{% endt %}")
        self.assertEqual(result, "hello world")
        result = self.lang.parse("hello {%t%}world{%endt%}")
        self.assertEqual(result, "hello world")
        result = self.lang.parse("hello {% t%}world{%endt %}")
        self.assertEqual(result, "hello world")
        result = self.lang.parse("hello {% t oh my %}world{%endt %}")
        self.assertEqual(result, "hello oh, my, world")
        result = self.lang.parse(self.unicodedata[1]['test'])
        self.assertEqual(result, self.unicodedata[1]['result'])


    def test_tag_list(self):
        result = self.lang.parse("{%t hello%} {%t world%}")
        self.assertEqual(result, "hello world")


    def test_block_list(self):
        result = self.lang.parse("{%t%}hello{%endt%} {%t%}world{%endt%}")
        self.assertEqual(result, "hello world")


    def test_invalid_tag(self):
        result = self.lang.parse("hello {% bad %}world{% endbad %}")
        self.assertEqual(result, "hello {% bad %}world{% endbad %}")
        result = self.lang.parse("hello {% tbad %}world{% endtbad %}")
        self.assertEqual(result, "hello {% tbad %}world{% endtbad %}")


    def test_nested_blocks(self):
        teststr = '{%t l1 %}hello {%t l2 %}world {%endt%}/l1{%endt%}'
        self.assertEqual(self.lang.parse(teststr), "l1, hello l2, world /l1")
        teststr = '{%t%}{%t%}hello {%endt%}{%t%}nested {%t%}world{%endt%}{%endt%}{%endt%}'
        self.assertEqual(self.lang.parse(teststr), "hello nested world")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
