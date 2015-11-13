__FILENAME__ = render
# coding: utf-8

"""
This module provides command-line access to pystache.

Run this script using the -h option for command-line help.

"""


try:
    import json
except:
    # The json module is new in Python 2.6, whereas simplejson is
    # compatible with earlier versions.
    try:
        import simplejson as json
    except ImportError:
        # Raise an error with a type different from ImportError as a hack around
        # this issue:
        #   http://bugs.python.org/issue7559
        from sys import exc_info
        ex_type, ex_value, tb = exc_info()
        new_ex = Exception("%s: %s" % (ex_type.__name__, ex_value))
        raise new_ex.__class__, new_ex, tb

# The optparse module is deprecated in Python 2.7 in favor of argparse.
# However, argparse is not available in Python 2.6 and earlier.
from optparse import OptionParser
import sys

# We use absolute imports here to allow use of this script from its
# location in source control (e.g. for development purposes).
# Otherwise, the following error occurs:
#
#   ValueError: Attempted relative import in non-package
#
from pystache.common import TemplateNotFoundError
from pystache.renderer import Renderer


USAGE = """\
%prog [-h] template context

Render a mustache template with the given context.

positional arguments:
  template    A filename or template string.
  context     A filename or JSON string."""


def parse_args(sys_argv, usage):
    """
    Return an OptionParser for the script.

    """
    args = sys_argv[1:]

    parser = OptionParser(usage=usage)
    options, args = parser.parse_args(args)

    template, context = args

    return template, context


# TODO: verify whether the setup() method's entry_points argument
# supports passing arguments to main:
#
#     http://packages.python.org/distribute/setuptools.html#automatic-script-creation
#
def main(sys_argv=sys.argv):
    template, context = parse_args(sys_argv, USAGE)

    if template.endswith('.mustache'):
        template = template[:-9]

    renderer = Renderer()

    try:
        template = renderer.load_template(template)
    except TemplateNotFoundError:
        pass

    try:
        context = json.load(open(context))
    except IOError:
        context = json.loads(context)

    rendered = renderer.render(template, context)
    print rendered


if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = test
# coding: utf-8

"""
This module provides a command to test pystache (unit tests, doctests, etc).

"""

import sys

from pystache.tests.main import main as run_tests


def main(sys_argv=sys.argv):
    run_tests(sys_argv=sys_argv)


if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = common
# coding: utf-8

"""
Exposes functionality needed throughout the project.

"""

from sys import version_info

def _get_string_types():
    # TODO: come up with a better solution for this.  One of the issues here
    #   is that in Python 3 there is no common base class for unicode strings
    #   and byte strings, and 2to3 seems to convert all of "str", "unicode",
    #   and "basestring" to Python 3's "str".
    if version_info < (3, ):
         return basestring
    # The latter evaluates to "bytes" in Python 3 -- even after conversion by 2to3.
    return (unicode, type(u"a".encode('utf-8')))


_STRING_TYPES = _get_string_types()


def is_string(obj):
    """
    Return whether the given object is a byte string or unicode string.

    This function is provided for compatibility with both Python 2 and 3
    when using 2to3.

    """
    return isinstance(obj, _STRING_TYPES)


# This function was designed to be portable across Python versions -- both
# with older versions and with Python 3 after applying 2to3.
def read(path):
    """
    Return the contents of a text file as a byte string.

    """
    # Opening in binary mode is necessary for compatibility across Python
    # 2 and 3.  In both Python 2 and 3, open() defaults to opening files in
    # text mode.  However, in Python 2, open() returns file objects whose
    # read() method returns byte strings (strings of type `str` in Python 2),
    # whereas in Python 3, the file object returns unicode strings (strings
    # of type `str` in Python 3).
    f = open(path, 'rb')
    # We avoid use of the with keyword for Python 2.4 support.
    try:
        return f.read()
    finally:
        f.close()


class MissingTags(object):

    """Contains the valid values for Renderer.missing_tags."""

    ignore = 'ignore'
    strict = 'strict'


class PystacheError(Exception):
    """Base class for Pystache exceptions."""
    pass


class TemplateNotFoundError(PystacheError):
    """An exception raised when a template is not found."""
    pass

########NEW FILE########
__FILENAME__ = context
# coding: utf-8

"""
Exposes a ContextStack class.

The Mustache spec makes a special distinction between two types of context
stack elements: hashes and objects.  For the purposes of interpreting the
spec, we define these categories mutually exclusively as follows:

 (1) Hash: an item whose type is a subclass of dict.

 (2) Object: an item that is neither a hash nor an instance of a
     built-in type.

"""

from pystache.common import PystacheError


# This equals '__builtin__' in Python 2 and 'builtins' in Python 3.
_BUILTIN_MODULE = type(0).__module__


# We use this private global variable as a return value to represent a key
# not being found on lookup.  This lets us distinguish between the case
# of a key's value being None with the case of a key not being found --
# without having to rely on exceptions (e.g. KeyError) for flow control.
#
# TODO: eliminate the need for a private global variable, e.g. by using the
#   preferred Python approach of "easier to ask for forgiveness than permission":
#     http://docs.python.org/glossary.html#term-eafp
class NotFound(object):
    pass
_NOT_FOUND = NotFound()


def _get_value(context, key):
    """
    Retrieve a key's value from a context item.

    Returns _NOT_FOUND if the key does not exist.

    The ContextStack.get() docstring documents this function's intended behavior.

    """
    if isinstance(context, dict):
        # Then we consider the argument a "hash" for the purposes of the spec.
        #
        # We do a membership test to avoid using exceptions for flow control
        # (e.g. catching KeyError).
        if key in context:
            return context[key]
    elif type(context).__module__ != _BUILTIN_MODULE:
        # Then we consider the argument an "object" for the purposes of
        # the spec.
        #
        # The elif test above lets us avoid treating instances of built-in
        # types like integers and strings as objects (cf. issue #81).
        # Instances of user-defined classes on the other hand, for example,
        # are considered objects by the test above.
        try:
            attr = getattr(context, key)
        except AttributeError:
            # TODO: distinguish the case of the attribute not existing from
            #   an AttributeError being raised by the call to the attribute.
            #   See the following issue for implementation ideas:
            #     http://bugs.python.org/issue7559
            pass
        else:
            # TODO: consider using EAFP here instead.
            #   http://docs.python.org/glossary.html#term-eafp
            if callable(attr):
                return attr()
            return attr

    return _NOT_FOUND


class KeyNotFoundError(PystacheError):

    """
    An exception raised when a key is not found in a context stack.

    """

    def __init__(self, key, details):
        self.key = key
        self.details = details

    def __str__(self):
        return "Key %s not found: %s" % (repr(self.key), self.details)


class ContextStack(object):

    """
    Provides dictionary-like access to a stack of zero or more items.

    Instances of this class are meant to act as the rendering context
    when rendering Mustache templates in accordance with mustache(5)
    and the Mustache spec.

    Instances encapsulate a private stack of hashes, objects, and built-in
    type instances.  Querying the stack for the value of a key queries
    the items in the stack in order from last-added objects to first
    (last in, first out).

    Caution: this class does not currently support recursive nesting in
    that items in the stack cannot themselves be ContextStack instances.

    See the docstrings of the methods of this class for more details.

    """

    # We reserve keyword arguments for future options (e.g. a "strict=True"
    # option for enabling a strict mode).
    def __init__(self, *items):
        """
        Construct an instance, and initialize the private stack.

        The *items arguments are the items with which to populate the
        initial stack.  Items in the argument list are added to the
        stack in order so that, in particular, items at the end of
        the argument list are queried first when querying the stack.

        Caution: items should not themselves be ContextStack instances, as
        recursive nesting does not behave as one might expect.

        """
        self._stack = list(items)

    def __repr__(self):
        """
        Return a string representation of the instance.

        For example--

        >>> context = ContextStack({'alpha': 'abc'}, {'numeric': 123})
        >>> repr(context)
        "ContextStack({'alpha': 'abc'}, {'numeric': 123})"

        """
        return "%s%s" % (self.__class__.__name__, tuple(self._stack))

    @staticmethod
    def create(*context, **kwargs):
        """
        Build a ContextStack instance from a sequence of context-like items.

        This factory-style method is more general than the ContextStack class's
        constructor in that, unlike the constructor, the argument list
        can itself contain ContextStack instances.

        Here is an example illustrating various aspects of this method:

        >>> obj1 = {'animal': 'cat', 'vegetable': 'carrot', 'mineral': 'copper'}
        >>> obj2 = ContextStack({'vegetable': 'spinach', 'mineral': 'silver'})
        >>>
        >>> context = ContextStack.create(obj1, None, obj2, mineral='gold')
        >>>
        >>> context.get('animal')
        'cat'
        >>> context.get('vegetable')
        'spinach'
        >>> context.get('mineral')
        'gold'

        Arguments:

          *context: zero or more dictionaries, ContextStack instances, or objects
            with which to populate the initial context stack.  None
            arguments will be skipped.  Items in the *context list are
            added to the stack in order so that later items in the argument
            list take precedence over earlier items.  This behavior is the
            same as the constructor's.

          **kwargs: additional key-value data to add to the context stack.
            As these arguments appear after all items in the *context list,
            in the case of key conflicts these values take precedence over
            all items in the *context list.  This behavior is the same as
            the constructor's.

        """
        items = context

        context = ContextStack()

        for item in items:
            if item is None:
                continue
            if isinstance(item, ContextStack):
                context._stack.extend(item._stack)
            else:
                context.push(item)

        if kwargs:
            context.push(kwargs)

        return context

    # TODO: add more unit tests for this.
    # TODO: update the docstring for dotted names.
    def get(self, name):
        """
        Resolve a dotted name against the current context stack.

        This function follows the rules outlined in the section of the
        spec regarding tag interpolation.  This function returns the value
        as is and does not coerce the return value to a string.

        Arguments:

          name: a dotted or non-dotted name.

          default: the value to return if name resolution fails at any point.
            Defaults to the empty string per the Mustache spec.

        This method queries items in the stack in order from last-added
        objects to first (last in, first out).  The value returned is
        the value of the key in the first item that contains the key.
        If the key is not found in any item in the stack, then the default
        value is returned.  The default value defaults to None.

        In accordance with the spec, this method queries items in the
        stack for a key differently depending on whether the item is a
        hash, object, or neither (as defined in the module docstring):

        (1) Hash: if the item is a hash, then the key's value is the
            dictionary value of the key.  If the dictionary doesn't contain
            the key, then the key is considered not found.

        (2) Object: if the item is an an object, then the method looks for
            an attribute with the same name as the key.  If an attribute
            with that name exists, the value of the attribute is returned.
            If the attribute is callable, however (i.e. if the attribute
            is a method), then the attribute is called with no arguments
            and that value is returned.  If there is no attribute with
            the same name as the key, then the key is considered not found.

        (3) Neither: if the item is neither a hash nor an object, then
            the key is considered not found.

        *Caution*:

          Callables are handled differently depending on whether they are
          dictionary values, as in (1) above, or attributes, as in (2).
          The former are returned as-is, while the latter are first
          called and that value returned.

          Here is an example to illustrate:

          >>> def greet():
          ...     return "Hi Bob!"
          >>>
          >>> class Greeter(object):
          ...     greet = None
          >>>
          >>> dct = {'greet': greet}
          >>> obj = Greeter()
          >>> obj.greet = greet
          >>>
          >>> dct['greet'] is obj.greet
          True
          >>> ContextStack(dct).get('greet')  #doctest: +ELLIPSIS
          <function greet at 0x...>
          >>> ContextStack(obj).get('greet')
          'Hi Bob!'

          TODO: explain the rationale for this difference in treatment.

        """
        if name == '.':
            try:
                return self.top()
            except IndexError:
                raise KeyNotFoundError(".", "empty context stack")

        parts = name.split('.')

        try:
            result = self._get_simple(parts[0])
        except KeyNotFoundError:
            raise KeyNotFoundError(name, "first part")

        for part in parts[1:]:
            # The full context stack is not used to resolve the remaining parts.
            # From the spec--
            #
            #   5) If any name parts were retained in step 1, each should be
            #   resolved against a context stack containing only the result
            #   from the former resolution.  If any part fails resolution, the
            #   result should be considered falsey, and should interpolate as
            #   the empty string.
            #
            # TODO: make sure we have a test case for the above point.
            result = _get_value(result, part)
            # TODO: consider using EAFP here instead.
            #   http://docs.python.org/glossary.html#term-eafp
            if result is _NOT_FOUND:
                raise KeyNotFoundError(name, "missing %s" % repr(part))

        return result

    def _get_simple(self, name):
        """
        Query the stack for a non-dotted name.

        """
        for item in reversed(self._stack):
            result = _get_value(item, name)
            if result is not _NOT_FOUND:
                return result

        raise KeyNotFoundError(name, "part missing")

    def push(self, item):
        """
        Push an item onto the stack.

        """
        self._stack.append(item)

    def pop(self):
        """
        Pop an item off of the stack, and return it.

        """
        return self._stack.pop()

    def top(self):
        """
        Return the item last added to the stack.

        """
        return self._stack[-1]

    def copy(self):
        """
        Return a copy of this instance.

        """
        return ContextStack(*self._stack)

########NEW FILE########
__FILENAME__ = defaults
# coding: utf-8

"""
This module provides a central location for defining default behavior.

Throughout the package, these defaults take effect only when the user
does not otherwise specify a value.

"""

try:
    # Python 3.2 adds html.escape() and deprecates cgi.escape().
    from html import escape
except ImportError:
    from cgi import escape

import os
import sys

from pystache.common import MissingTags


# How to handle encoding errors when decoding strings from str to unicode.
#
# This value is passed as the "errors" argument to Python's built-in
# unicode() function:
#
#   http://docs.python.org/library/functions.html#unicode
#
DECODE_ERRORS = 'strict'

# The name of the encoding to use when converting to unicode any strings of
# type str encountered during the rendering process.
STRING_ENCODING = sys.getdefaultencoding()

# The name of the encoding to use when converting file contents to unicode.
# This default takes precedence over the STRING_ENCODING default for
# strings that arise from files.
FILE_ENCODING = sys.getdefaultencoding()

# The delimiters to start with when parsing.
DELIMITERS = (u'{{', u'}}')

# How to handle missing tags when rendering a template.
MISSING_TAGS = MissingTags.ignore

# The starting list of directories in which to search for templates when
# loading a template by file name.
SEARCH_DIRS = [os.curdir]  # i.e. ['.']

# The escape function to apply to strings that require escaping when
# rendering templates (e.g. for tags enclosed in double braces).
# Only unicode strings will be passed to this function.
#
# The quote=True argument causes double but not single quotes to be escaped
# in Python 3.1 and earlier, and both double and single quotes to be
# escaped in Python 3.2 and later:
#
#   http://docs.python.org/library/cgi.html#cgi.escape
#   http://docs.python.org/dev/library/html.html#html.escape
#
TAG_ESCAPE = lambda u: escape(u, quote=True)

# The default template extension, without the leading dot.
TEMPLATE_EXTENSION = 'mustache'

########NEW FILE########
__FILENAME__ = init
# encoding: utf-8

"""
This module contains the initialization logic called by __init__.py.

"""

from pystache.parser import parse
from pystache.renderer import Renderer
from pystache.template_spec import TemplateSpec


def render(template, context=None, **kwargs):
    """
    Return the given template string rendered using the given context.

    """
    renderer = Renderer()
    return renderer.render(template, context, **kwargs)

########NEW FILE########
__FILENAME__ = loader
# coding: utf-8

"""
This module provides a Loader class for locating and reading templates.

"""

import os
import sys

from pystache import common
from pystache import defaults
from pystache.locator import Locator


# We make a function so that the current defaults take effect.
# TODO: revisit whether this is necessary.

def _make_to_unicode():
    def to_unicode(s, encoding=None):
        """
        Raises a TypeError exception if the given string is already unicode.

        """
        if encoding is None:
            encoding = defaults.STRING_ENCODING
        return unicode(s, encoding, defaults.DECODE_ERRORS)
    return to_unicode


class Loader(object):

    """
    Loads the template associated to a name or user-defined object.

    All load_*() methods return the template as a unicode string.

    """

    def __init__(self, file_encoding=None, extension=None, to_unicode=None,
                 search_dirs=None):
        """
        Construct a template loader instance.

        Arguments:

          extension: the template file extension, without the leading dot.
            Pass False for no extension (e.g. to use extensionless template
            files).  Defaults to the package default.

          file_encoding: the name of the encoding to use when converting file
            contents to unicode.  Defaults to the package default.

          search_dirs: the list of directories in which to search when loading
            a template by name or file name.  Defaults to the package default.

          to_unicode: the function to use when converting strings of type
            str to unicode.  The function should have the signature:

              to_unicode(s, encoding=None)

            It should accept a string of type str and an optional encoding
            name and return a string of type unicode.  Defaults to calling
            Python's built-in function unicode() using the package string
            encoding and decode errors defaults.

        """
        if extension is None:
            extension = defaults.TEMPLATE_EXTENSION

        if file_encoding is None:
            file_encoding = defaults.FILE_ENCODING

        if search_dirs is None:
            search_dirs = defaults.SEARCH_DIRS

        if to_unicode is None:
            to_unicode = _make_to_unicode()

        self.extension = extension
        self.file_encoding = file_encoding
        # TODO: unit test setting this attribute.
        self.search_dirs = search_dirs
        self.to_unicode = to_unicode

    def _make_locator(self):
        return Locator(extension=self.extension)

    def unicode(self, s, encoding=None):
        """
        Convert a string to unicode using the given encoding, and return it.

        This function uses the underlying to_unicode attribute.

        Arguments:

          s: a basestring instance to convert to unicode.  Unlike Python's
            built-in unicode() function, it is okay to pass unicode strings
            to this function.  (Passing a unicode string to Python's unicode()
            with the encoding argument throws the error, "TypeError: decoding
            Unicode is not supported.")

          encoding: the encoding to pass to the to_unicode attribute.
            Defaults to None.

        """
        if isinstance(s, unicode):
            return unicode(s)

        return self.to_unicode(s, encoding)

    def read(self, path, encoding=None):
        """
        Read the template at the given path, and return it as a unicode string.

        """
        b = common.read(path)

        if encoding is None:
            encoding = self.file_encoding

        return self.unicode(b, encoding)

    def load_file(self, file_name):
        """
        Find and return the template with the given file name.

        Arguments:

          file_name: the file name of the template.

        """
        locator = self._make_locator()

        path = locator.find_file(file_name, self.search_dirs)

        return self.read(path)

    def load_name(self, name):
        """
        Find and return the template with the given template name.

        Arguments:

          name: the name of the template.

        """
        locator = self._make_locator()

        path = locator.find_name(name, self.search_dirs)

        return self.read(path)

    # TODO: unit-test this method.
    def load_object(self, obj):
        """
        Find and return the template associated to the given object.

        Arguments:

          obj: an instance of a user-defined class.

          search_dirs: the list of directories in which to search.

        """
        locator = self._make_locator()

        path = locator.find_object(obj, self.search_dirs)

        return self.read(path)

########NEW FILE########
__FILENAME__ = locator
# coding: utf-8

"""
This module provides a Locator class for finding template files.

"""

import os
import re
import sys

from pystache.common import TemplateNotFoundError
from pystache import defaults


class Locator(object):

    def __init__(self, extension=None):
        """
        Construct a template locator.

        Arguments:

          extension: the template file extension, without the leading dot.
            Pass False for no extension (e.g. to use extensionless template
            files).  Defaults to the package default.

        """
        if extension is None:
            extension = defaults.TEMPLATE_EXTENSION

        self.template_extension = extension

    def get_object_directory(self, obj):
        """
        Return the directory containing an object's defining class.

        Returns None if there is no such directory, for example if the
        class was defined in an interactive Python session, or in a
        doctest that appears in a text file (rather than a Python file).

        """
        if not hasattr(obj, '__module__'):
            return None

        module = sys.modules[obj.__module__]

        if not hasattr(module, '__file__'):
            # TODO: add a unit test for this case.
            return None

        path = module.__file__

        return os.path.dirname(path)

    def make_template_name(self, obj):
        """
        Return the canonical template name for an object instance.

        This method converts Python-style class names (PEP 8's recommended
        CamelCase, aka CapWords) to lower_case_with_underscords.  Here
        is an example with code:

        >>> class HelloWorld(object):
        ...     pass
        >>> hi = HelloWorld()
        >>>
        >>> locator = Locator()
        >>> locator.make_template_name(hi)
        'hello_world'

        """
        template_name = obj.__class__.__name__

        def repl(match):
            return '_' + match.group(0).lower()

        return re.sub('[A-Z]', repl, template_name)[1:]

    def make_file_name(self, template_name, template_extension=None):
        """
        Generate and return the file name for the given template name.

        Arguments:

          template_extension: defaults to the instance's extension.

        """
        file_name = template_name

        if template_extension is None:
            template_extension = self.template_extension

        if template_extension is not False:
            file_name += os.path.extsep + template_extension

        return file_name

    def _find_path(self, search_dirs, file_name):
        """
        Search for the given file, and return the path.

        Returns None if the file is not found.

        """
        for dir_path in search_dirs:
            file_path = os.path.join(dir_path, file_name)
            if os.path.exists(file_path):
                return file_path

        return None

    def _find_path_required(self, search_dirs, file_name):
        """
        Return the path to a template with the given file name.

        """
        path = self._find_path(search_dirs, file_name)

        if path is None:
            raise TemplateNotFoundError('File %s not found in dirs: %s' %
                                        (repr(file_name), repr(search_dirs)))

        return path

    def find_file(self, file_name, search_dirs):
        """
        Return the path to a template with the given file name.

        Arguments:

          file_name: the file name of the template.

          search_dirs: the list of directories in which to search.

        """
        return self._find_path_required(search_dirs, file_name)

    def find_name(self, template_name, search_dirs):
        """
        Return the path to a template with the given name.

        Arguments:

          template_name: the name of the template.

          search_dirs: the list of directories in which to search.

        """
        file_name = self.make_file_name(template_name)

        return self._find_path_required(search_dirs, file_name)

    def find_object(self, obj, search_dirs, file_name=None):
        """
        Return the path to a template associated with the given object.

        """
        if file_name is None:
            # TODO: should we define a make_file_name() method?
            template_name = self.make_template_name(obj)
            file_name = self.make_file_name(template_name)

        dir_path = self.get_object_directory(obj)

        if dir_path is not None:
            search_dirs = [dir_path] + search_dirs

        path = self._find_path_required(search_dirs, file_name)

        return path

########NEW FILE########
__FILENAME__ = parsed
# coding: utf-8

"""
Exposes a class that represents a parsed (or compiled) template.

"""


class ParsedTemplate(object):

    """
    Represents a parsed or compiled template.

    An instance wraps a list of unicode strings and node objects.  A node
    object must have a `render(engine, stack)` method that accepts a
    RenderEngine instance and a ContextStack instance and returns a unicode
    string.

    """

    def __init__(self):
        self._parse_tree = []

    def __repr__(self):
        return repr(self._parse_tree)

    def add(self, node):
        """
        Arguments:

          node: a unicode string or node object instance.  See the class
            docstring for information.

        """
        self._parse_tree.append(node)

    def render(self, engine, context):
        """
        Returns: a string of type unicode.

        """
        # We avoid use of the ternary operator for Python 2.4 support.
        def get_unicode(node):
            if type(node) is unicode:
                return node
            return node.render(engine, context)
        parts = map(get_unicode, self._parse_tree)
        s = ''.join(parts)

        return unicode(s)

########NEW FILE########
__FILENAME__ = parser
# coding: utf-8

"""
Exposes a parse() function to parse template strings.

"""

import re

from pystache import defaults
from pystache.parsed import ParsedTemplate


END_OF_LINE_CHARACTERS = [u'\r', u'\n']
NON_BLANK_RE = re.compile(ur'^(.)', re.M)


# TODO: add some unit tests for this.
# TODO: add a test case that checks for spurious spaces.
# TODO: add test cases for delimiters.
def parse(template, delimiters=None):
    """
    Parse a unicode template string and return a ParsedTemplate instance.

    Arguments:

      template: a unicode template string.

      delimiters: a 2-tuple of delimiters.  Defaults to the package default.

    Examples:

    >>> parsed = parse(u"Hey {{#who}}{{name}}!{{/who}}")
    >>> print str(parsed).replace('u', '')  # This is a hack to get the test to pass both in Python 2 and 3.
    ['Hey ', _SectionNode(key='who', index_begin=12, index_end=21, parsed=[_EscapeNode(key='name'), '!'])]

    """
    if type(template) is not unicode:
        raise Exception("Template is not unicode: %s" % type(template))
    parser = _Parser(delimiters)
    return parser.parse(template)


def _compile_template_re(delimiters):
    """
    Return a regular expresssion object (re.RegexObject) instance.

    """
    # The possible tag type characters following the opening tag,
    # excluding "=" and "{".
    tag_types = "!>&/#^"

    # TODO: are we following this in the spec?
    #
    #   The tag's content MUST be a non-whitespace character sequence
    #   NOT containing the current closing delimiter.
    #
    tag = r"""
        (?P<whitespace>[\ \t]*)
        %(otag)s \s*
        (?:
          (?P<change>=) \s* (?P<delims>.+?)   \s* = |
          (?P<raw>{)    \s* (?P<raw_name>.+?) \s* } |
          (?P<tag>[%(tag_types)s]?)  \s* (?P<tag_key>[\s\S]+?)
        )
        \s* %(ctag)s
    """ % {'tag_types': tag_types, 'otag': re.escape(delimiters[0]), 'ctag': re.escape(delimiters[1])}

    return re.compile(tag, re.VERBOSE)


class ParsingError(Exception):

    pass


## Node types

def _format(obj, exclude=None):
    if exclude is None:
        exclude = []
    exclude.append('key')
    attrs = obj.__dict__
    names = list(set(attrs.keys()) - set(exclude))
    names.sort()
    names.insert(0, 'key')
    args = ["%s=%s" % (name, repr(attrs[name])) for name in names]
    return "%s(%s)" % (obj.__class__.__name__, ", ".join(args))


class _CommentNode(object):

    def __repr__(self):
        return _format(self)

    def render(self, engine, context):
        return u''


class _ChangeNode(object):

    def __init__(self, delimiters):
        self.delimiters = delimiters

    def __repr__(self):
        return _format(self)

    def render(self, engine, context):
        return u''


class _EscapeNode(object):

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return _format(self)

    def render(self, engine, context):
        s = engine.fetch_string(context, self.key)
        return engine.escape(s)


class _LiteralNode(object):

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return _format(self)

    def render(self, engine, context):
        s = engine.fetch_string(context, self.key)
        return engine.literal(s)


class _PartialNode(object):

    def __init__(self, key, indent):
        self.key = key
        self.indent = indent

    def __repr__(self):
        return _format(self)

    def render(self, engine, context):
        template = engine.resolve_partial(self.key)
        # Indent before rendering.
        template = re.sub(NON_BLANK_RE, self.indent + ur'\1', template)

        return engine.render(template, context)


class _InvertedNode(object):

    def __init__(self, key, parsed_section):
        self.key = key
        self.parsed_section = parsed_section

    def __repr__(self):
        return _format(self)

    def render(self, engine, context):
        # TODO: is there a bug because we are not using the same
        #   logic as in fetch_string()?
        data = engine.resolve_context(context, self.key)
        # Note that lambdas are considered truthy for inverted sections
        # per the spec.
        if data:
            return u''
        return self.parsed_section.render(engine, context)


class _SectionNode(object):

    # TODO: the template_ and parsed_template_ arguments don't both seem
    # to be necessary.  Can we remove one of them?  For example, if
    # callable(data) is True, then the initial parsed_template isn't used.
    def __init__(self, key, parsed, delimiters, template, index_begin, index_end):
        self.delimiters = delimiters
        self.key = key
        self.parsed = parsed
        self.template = template
        self.index_begin = index_begin
        self.index_end = index_end

    def __repr__(self):
        return _format(self, exclude=['delimiters', 'template'])

    def render(self, engine, context):
        values = engine.fetch_section_data(context, self.key)

        parts = []
        for val in values:
            if callable(val):
                # Lambdas special case section rendering and bypass pushing
                # the data value onto the context stack.  From the spec--
                #
                #   When used as the data value for a Section tag, the
                #   lambda MUST be treatable as an arity 1 function, and
                #   invoked as such (passing a String containing the
                #   unprocessed section contents).  The returned value
                #   MUST be rendered against the current delimiters, then
                #   interpolated in place of the section.
                #
                #  Also see--
                #
                #   https://github.com/defunkt/pystache/issues/113
                #
                # TODO: should we check the arity?
                val = val(self.template[self.index_begin:self.index_end])
                val = engine._render_value(val, context, delimiters=self.delimiters)
                parts.append(val)
                continue

            context.push(val)
            parts.append(self.parsed.render(engine, context))
            context.pop()

        return unicode(''.join(parts))


class _Parser(object):

    _delimiters = None
    _template_re = None

    def __init__(self, delimiters=None):
        if delimiters is None:
            delimiters = defaults.DELIMITERS

        self._delimiters = delimiters

    def _compile_delimiters(self):
        self._template_re = _compile_template_re(self._delimiters)

    def _change_delimiters(self, delimiters):
        self._delimiters = delimiters
        self._compile_delimiters()

    def parse(self, template):
        """
        Parse a template string starting at some index.

        This method uses the current tag delimiter.

        Arguments:

          template: a unicode string that is the template to parse.

          index: the index at which to start parsing.

        Returns:

          a ParsedTemplate instance.

        """
        self._compile_delimiters()

        start_index = 0
        content_end_index, parsed_section, section_key = None, None, None
        parsed_template = ParsedTemplate()

        states = []

        while True:
            match = self._template_re.search(template, start_index)

            if match is None:
                break

            match_index = match.start()
            end_index = match.end()

            matches = match.groupdict()

            # Normalize the matches dictionary.
            if matches['change'] is not None:
                matches.update(tag='=', tag_key=matches['delims'])
            elif matches['raw'] is not None:
                matches.update(tag='&', tag_key=matches['raw_name'])

            tag_type = matches['tag']
            tag_key = matches['tag_key']
            leading_whitespace = matches['whitespace']

            # Standalone (non-interpolation) tags consume the entire line,
            # both leading whitespace and trailing newline.
            did_tag_begin_line = match_index == 0 or template[match_index - 1] in END_OF_LINE_CHARACTERS
            did_tag_end_line = end_index == len(template) or template[end_index] in END_OF_LINE_CHARACTERS
            is_tag_interpolating = tag_type in ['', '&']

            if did_tag_begin_line and did_tag_end_line and not is_tag_interpolating:
                if end_index < len(template):
                    end_index += template[end_index] == '\r' and 1 or 0
                if end_index < len(template):
                    end_index += template[end_index] == '\n' and 1 or 0
            elif leading_whitespace:
                match_index += len(leading_whitespace)
                leading_whitespace = ''

            # Avoid adding spurious empty strings to the parse tree.
            if start_index != match_index:
                parsed_template.add(template[start_index:match_index])

            start_index = end_index

            if tag_type in ('#', '^'):
                # Cache current state.
                state = (tag_type, end_index, section_key, parsed_template)
                states.append(state)

                # Initialize new state
                section_key, parsed_template = tag_key, ParsedTemplate()
                continue

            if tag_type == '/':
                if tag_key != section_key:
                    raise ParsingError("Section end tag mismatch: %s != %s" % (tag_key, section_key))

                # Restore previous state with newly found section data.
                parsed_section = parsed_template

                (tag_type, section_start_index, section_key, parsed_template) = states.pop()
                node = self._make_section_node(template, tag_type, tag_key, parsed_section,
                                               section_start_index, match_index)

            else:
                node = self._make_interpolation_node(tag_type, tag_key, leading_whitespace)

            parsed_template.add(node)

        # Avoid adding spurious empty strings to the parse tree.
        if start_index != len(template):
            parsed_template.add(template[start_index:])

        return parsed_template

    def _make_interpolation_node(self, tag_type, tag_key, leading_whitespace):
        """
        Create and return a non-section node for the parse tree.

        """
        # TODO: switch to using a dictionary instead of a bunch of ifs and elifs.
        if tag_type == '!':
            return _CommentNode()

        if tag_type == '=':
            delimiters = tag_key.split()
            self._change_delimiters(delimiters)
            return _ChangeNode(delimiters)

        if tag_type == '':
            return _EscapeNode(tag_key)

        if tag_type == '&':
            return _LiteralNode(tag_key)

        if tag_type == '>':
            return _PartialNode(tag_key, leading_whitespace)

        raise Exception("Invalid symbol for interpolation tag: %s" % repr(tag_type))

    def _make_section_node(self, template, tag_type, tag_key, parsed_section,
                           section_start_index, section_end_index):
        """
        Create and return a section node for the parse tree.

        """
        if tag_type == '#':
            return _SectionNode(tag_key, parsed_section, self._delimiters,
                               template, section_start_index, section_end_index)

        if tag_type == '^':
            return _InvertedNode(tag_key, parsed_section)

        raise Exception("Invalid symbol for section tag: %s" % repr(tag_type))

########NEW FILE########
__FILENAME__ = renderengine
# coding: utf-8

"""
Defines a class responsible for rendering logic.

"""

import re

from pystache.common import is_string
from pystache.parser import parse


def context_get(stack, name):
    """
    Find and return a name from a ContextStack instance.

    """
    return stack.get(name)


class RenderEngine(object):

    """
    Provides a render() method.

    This class is meant only for internal use.

    As a rule, the code in this class operates on unicode strings where
    possible rather than, say, strings of type str or markupsafe.Markup.
    This means that strings obtained from "external" sources like partials
    and variable tag values are immediately converted to unicode (or
    escaped and converted to unicode) before being operated on further.
    This makes maintaining, reasoning about, and testing the correctness
    of the code much simpler.  In particular, it keeps the implementation
    of this class independent of the API details of one (or possibly more)
    unicode subclasses (e.g. markupsafe.Markup).

    """

    # TODO: it would probably be better for the constructor to accept
    #   and set as an attribute a single RenderResolver instance
    #   that encapsulates the customizable aspects of converting
    #   strings and resolving partials and names from context.
    def __init__(self, literal=None, escape=None, resolve_context=None,
                 resolve_partial=None, to_str=None):
        """
        Arguments:

          literal: the function used to convert unescaped variable tag
            values to unicode, e.g. the value corresponding to a tag
            "{{{name}}}".  The function should accept a string of type
            str or unicode (or a subclass) and return a string of type
            unicode (but not a proper subclass of unicode).
                This class will only pass basestring instances to this
            function.  For example, it will call str() on integer variable
            values prior to passing them to this function.

          escape: the function used to escape and convert variable tag
            values to unicode, e.g. the value corresponding to a tag
            "{{name}}".  The function should obey the same properties
            described above for the "literal" function argument.
                This function should take care to convert any str
            arguments to unicode just as the literal function should, as
            this class will not pass tag values to literal prior to passing
            them to this function.  This allows for more flexibility,
            for example using a custom escape function that handles
            incoming strings of type markupsafe.Markup differently
            from plain unicode strings.

          resolve_context: the function to call to resolve a name against
            a context stack.  The function should accept two positional
            arguments: a ContextStack instance and a name to resolve.

          resolve_partial: the function to call when loading a partial.
            The function should accept a template name string and return a
            template string of type unicode (not a subclass).

          to_str: a function that accepts an object and returns a string (e.g.
            the built-in function str).  This function is used for string
            coercion whenever a string is required (e.g. for converting None
            or 0 to a string).

        """
        self.escape = escape
        self.literal = literal
        self.resolve_context = resolve_context
        self.resolve_partial = resolve_partial
        self.to_str = to_str

    # TODO: Rename context to stack throughout this module.

    # From the spec:
    #
    #   When used as the data value for an Interpolation tag, the lambda
    #   MUST be treatable as an arity 0 function, and invoked as such.
    #   The returned value MUST be rendered against the default delimiters,
    #   then interpolated in place of the lambda.
    #
    def fetch_string(self, context, name):
        """
        Get a value from the given context as a basestring instance.

        """
        val = self.resolve_context(context, name)

        if callable(val):
            # Return because _render_value() is already a string.
            return self._render_value(val(), context)

        if not is_string(val):
            return self.to_str(val)

        return val

    def fetch_section_data(self, context, name):
        """
        Fetch the value of a section as a list.

        """
        data = self.resolve_context(context, name)

        # From the spec:
        #
        #   If the data is not of a list type, it is coerced into a list
        #   as follows: if the data is truthy (e.g. `!!data == true`),
        #   use a single-element list containing the data, otherwise use
        #   an empty list.
        #
        if not data:
            data = []
        else:
            # The least brittle way to determine whether something
            # supports iteration is by trying to call iter() on it:
            #
            #   http://docs.python.org/library/functions.html#iter
            #
            # It is not sufficient, for example, to check whether the item
            # implements __iter__ () (the iteration protocol).  There is
            # also __getitem__() (the sequence protocol).  In Python 2,
            # strings do not implement __iter__(), but in Python 3 they do.
            try:
                iter(data)
            except TypeError:
                # Then the value does not support iteration.
                data = [data]
            else:
                if is_string(data) or isinstance(data, dict):
                    # Do not treat strings and dicts (which are iterable) as lists.
                    data = [data]
                # Otherwise, treat the value as a list.

        return data

    def _render_value(self, val, context, delimiters=None):
        """
        Render an arbitrary value.

        """
        if not is_string(val):
            # In case the template is an integer, for example.
            val = self.to_str(val)
        if type(val) is not unicode:
            val = self.literal(val)
        return self.render(val, context, delimiters)

    def render(self, template, context_stack, delimiters=None):
        """
        Render a unicode template string, and return as unicode.

        Arguments:

          template: a template string of type unicode (but not a proper
            subclass of unicode).

          context_stack: a ContextStack instance.

        """
        parsed_template = parse(template, delimiters)

        return parsed_template.render(self, context_stack)

########NEW FILE########
__FILENAME__ = renderer
# coding: utf-8

"""
This module provides a Renderer class to render templates.

"""

import sys

from pystache import defaults
from pystache.common import TemplateNotFoundError, MissingTags, is_string
from pystache.context import ContextStack, KeyNotFoundError
from pystache.loader import Loader
from pystache.parsed import ParsedTemplate
from pystache.renderengine import context_get, RenderEngine
from pystache.specloader import SpecLoader
from pystache.template_spec import TemplateSpec


class Renderer(object):

    """
    A class for rendering mustache templates.

    This class supports several rendering options which are described in
    the constructor's docstring.  Other behavior can be customized by
    subclassing this class.

    For example, one can pass a string-string dictionary to the constructor
    to bypass loading partials from the file system:

    >>> partials = {'partial': 'Hello, {{thing}}!'}
    >>> renderer = Renderer(partials=partials)
    >>> # We apply print to make the test work in Python 3 after 2to3.
    >>> print renderer.render('{{>partial}}', {'thing': 'world'})
    Hello, world!

    To customize string coercion (e.g. to render False values as ''), one can
    subclass this class.  For example:

        class MyRenderer(Renderer):
            def str_coerce(self, val):
                if not val:
                    return ''
                else:
                    return str(val)

    """

    def __init__(self, file_encoding=None, string_encoding=None,
                 decode_errors=None, search_dirs=None, file_extension=None,
                 escape=None, partials=None, missing_tags=None):
        """
        Construct an instance.

        Arguments:

          file_encoding: the name of the encoding to use by default when
            reading template files.  All templates are converted to unicode
            prior to parsing.  Defaults to the package default.

          string_encoding: the name of the encoding to use when converting
            to unicode any byte strings (type str in Python 2) encountered
            during the rendering process.  This name will be passed as the
            encoding argument to the built-in function unicode().
            Defaults to the package default.

          decode_errors: the string to pass as the errors argument to the
            built-in function unicode() when converting byte strings to
            unicode.  Defaults to the package default.

          search_dirs: the list of directories in which to search when
            loading a template by name or file name.  If given a string,
            the method interprets the string as a single directory.
            Defaults to the package default.

          file_extension: the template file extension.  Pass False for no
            extension (i.e. to use extensionless template files).
            Defaults to the package default.

          partials: an object (e.g. a dictionary) for custom partial loading
            during the rendering process.
                The object should have a get() method that accepts a string
            and returns the corresponding template as a string, preferably
            as a unicode string.  If there is no template with that name,
            the get() method should either return None (as dict.get() does)
            or raise an exception.
                If this argument is None, the rendering process will use
            the normal procedure of locating and reading templates from
            the file system -- using relevant instance attributes like
            search_dirs, file_encoding, etc.

          escape: the function used to escape variable tag values when
            rendering a template.  The function should accept a unicode
            string (or subclass of unicode) and return an escaped string
            that is again unicode (or a subclass of unicode).
                This function need not handle strings of type `str` because
            this class will only pass it unicode strings.  The constructor
            assigns this function to the constructed instance's escape()
            method.
                To disable escaping entirely, one can pass `lambda u: u`
            as the escape function, for example.  One may also wish to
            consider using markupsafe's escape function: markupsafe.escape().
            This argument defaults to the package default.

          missing_tags: a string specifying how to handle missing tags.
            If 'strict', an error is raised on a missing tag.  If 'ignore',
            the value of the tag is the empty string.  Defaults to the
            package default.

        """
        if decode_errors is None:
            decode_errors = defaults.DECODE_ERRORS

        if escape is None:
            escape = defaults.TAG_ESCAPE

        if file_encoding is None:
            file_encoding = defaults.FILE_ENCODING

        if file_extension is None:
            file_extension = defaults.TEMPLATE_EXTENSION

        if missing_tags is None:
            missing_tags = defaults.MISSING_TAGS

        if search_dirs is None:
            search_dirs = defaults.SEARCH_DIRS

        if string_encoding is None:
            string_encoding = defaults.STRING_ENCODING

        if isinstance(search_dirs, basestring):
            search_dirs = [search_dirs]

        self._context = None
        self.decode_errors = decode_errors
        self.escape = escape
        self.file_encoding = file_encoding
        self.file_extension = file_extension
        self.missing_tags = missing_tags
        self.partials = partials
        self.search_dirs = search_dirs
        self.string_encoding = string_encoding

    # This is an experimental way of giving views access to the current context.
    # TODO: consider another approach of not giving access via a property,
    #   but instead letting the caller pass the initial context to the
    #   main render() method by reference.  This approach would probably
    #   be less likely to be misused.
    @property
    def context(self):
        """
        Return the current rendering context [experimental].

        """
        return self._context

    # We could not choose str() as the name because 2to3 renames the unicode()
    # method of this class to str().
    def str_coerce(self, val):
        """
        Coerce a non-string value to a string.

        This method is called whenever a non-string is encountered during the
        rendering process when a string is needed (e.g. if a context value
        for string interpolation is not a string).  To customize string
        coercion, you can override this method.

        """
        return str(val)

    def _to_unicode_soft(self, s):
        """
        Convert a basestring to unicode, preserving any unicode subclass.

        """
        # We type-check to avoid "TypeError: decoding Unicode is not supported".
        # We avoid the Python ternary operator for Python 2.4 support.
        if isinstance(s, unicode):
            return s
        return self.unicode(s)

    def _to_unicode_hard(self, s):
        """
        Convert a basestring to a string with type unicode (not subclass).

        """
        return unicode(self._to_unicode_soft(s))

    def _escape_to_unicode(self, s):
        """
        Convert a basestring to unicode (preserving any unicode subclass), and escape it.

        Returns a unicode string (not subclass).

        """
        return unicode(self.escape(self._to_unicode_soft(s)))

    def unicode(self, b, encoding=None):
        """
        Convert a byte string to unicode, using string_encoding and decode_errors.

        Arguments:

          b: a byte string.

          encoding: the name of an encoding.  Defaults to the string_encoding
            attribute for this instance.

        Raises:

          TypeError: Because this method calls Python's built-in unicode()
            function, this method raises the following exception if the
            given string is already unicode:

              TypeError: decoding Unicode is not supported

        """
        if encoding is None:
            encoding = self.string_encoding

        # TODO: Wrap UnicodeDecodeErrors with a message about setting
        # the string_encoding and decode_errors attributes.
        return unicode(b, encoding, self.decode_errors)

    def _make_loader(self):
        """
        Create a Loader instance using current attributes.

        """
        return Loader(file_encoding=self.file_encoding, extension=self.file_extension,
                      to_unicode=self.unicode, search_dirs=self.search_dirs)

    def _make_load_template(self):
        """
        Return a function that loads a template by name.

        """
        loader = self._make_loader()

        def load_template(template_name):
            return loader.load_name(template_name)

        return load_template

    def _make_load_partial(self):
        """
        Return a function that loads a partial by name.

        """
        if self.partials is None:
            return self._make_load_template()

        # Otherwise, create a function from the custom partial loader.
        partials = self.partials

        def load_partial(name):
            # TODO: consider using EAFP here instead.
            #     http://docs.python.org/glossary.html#term-eafp
            #   This would mean requiring that the custom partial loader
            #   raise a KeyError on name not found.
            template = partials.get(name)
            if template is None:
                raise TemplateNotFoundError("Name %s not found in partials: %s" %
                                            (repr(name), type(partials)))

            # RenderEngine requires that the return value be unicode.
            return self._to_unicode_hard(template)

        return load_partial

    def _is_missing_tags_strict(self):
        """
        Return whether missing_tags is set to strict.

        """
        val = self.missing_tags

        if val == MissingTags.strict:
            return True
        elif val == MissingTags.ignore:
            return False

        raise Exception("Unsupported 'missing_tags' value: %s" % repr(val))

    def _make_resolve_partial(self):
        """
        Return the resolve_partial function to pass to RenderEngine.__init__().

        """
        load_partial = self._make_load_partial()

        if self._is_missing_tags_strict():
            return load_partial
        # Otherwise, ignore missing tags.

        def resolve_partial(name):
            try:
                return load_partial(name)
            except TemplateNotFoundError:
                return u''

        return resolve_partial

    def _make_resolve_context(self):
        """
        Return the resolve_context function to pass to RenderEngine.__init__().

        """
        if self._is_missing_tags_strict():
            return context_get
        # Otherwise, ignore missing tags.

        def resolve_context(stack, name):
            try:
                return context_get(stack, name)
            except KeyNotFoundError:
                return u''

        return resolve_context

    def _make_render_engine(self):
        """
        Return a RenderEngine instance for rendering.

        """
        resolve_context = self._make_resolve_context()
        resolve_partial = self._make_resolve_partial()

        engine = RenderEngine(literal=self._to_unicode_hard,
                              escape=self._escape_to_unicode,
                              resolve_context=resolve_context,
                              resolve_partial=resolve_partial,
                              to_str=self.str_coerce)
        return engine

    # TODO: add unit tests for this method.
    def load_template(self, template_name):
        """
        Load a template by name from the file system.

        """
        load_template = self._make_load_template()
        return load_template(template_name)

    def _render_object(self, obj, *context, **kwargs):
        """
        Render the template associated with the given object.

        """
        loader = self._make_loader()

        # TODO: consider an approach that does not require using an if
        #   block here.  For example, perhaps this class's loader can be
        #   a SpecLoader in all cases, and the SpecLoader instance can
        #   check the object's type.  Or perhaps Loader and SpecLoader
        #   can be refactored to implement the same interface.
        if isinstance(obj, TemplateSpec):
            loader = SpecLoader(loader)
            template = loader.load(obj)
        else:
            template = loader.load_object(obj)

        context = [obj] + list(context)

        return self._render_string(template, *context, **kwargs)

    def render_name(self, template_name, *context, **kwargs):
        """
        Render the template with the given name using the given context.

        See the render() docstring for more information.

        """
        loader = self._make_loader()
        template = loader.load_name(template_name)
        return self._render_string(template, *context, **kwargs)

    def render_path(self, template_path, *context, **kwargs):
        """
        Render the template at the given path using the given context.

        Read the render() docstring for more information.

        """
        loader = self._make_loader()
        template = loader.read(template_path)

        return self._render_string(template, *context, **kwargs)

    def _render_string(self, template, *context, **kwargs):
        """
        Render the given template string using the given context.

        """
        # RenderEngine.render() requires that the template string be unicode.
        template = self._to_unicode_hard(template)

        render_func = lambda engine, stack: engine.render(template, stack)

        return self._render_final(render_func, *context, **kwargs)

    # All calls to render() should end here because it prepares the
    # context stack correctly.
    def _render_final(self, render_func, *context, **kwargs):
        """
        Arguments:

          render_func: a function that accepts a RenderEngine and ContextStack
            instance and returns a template rendering as a unicode string.

        """
        stack = ContextStack.create(*context, **kwargs)
        self._context = stack

        engine = self._make_render_engine()

        return render_func(engine, stack)

    def render(self, template, *context, **kwargs):
        """
        Render the given template string, view template, or parsed template.

        Returns a unicode string.

        Prior to rendering, this method will convert a template that is a
        byte string (type str in Python 2) to unicode using the string_encoding
        and decode_errors attributes.  See the constructor docstring for
        more information.

        Arguments:

          template: a template string that is unicode or a byte string,
            a ParsedTemplate instance, or another object instance.  In the
            final case, the function first looks for the template associated
            to the object by calling this class's get_associated_template()
            method.  The rendering process also uses the passed object as
            the first element of the context stack when rendering.

          *context: zero or more dictionaries, ContextStack instances, or objects
            with which to populate the initial context stack.  None
            arguments are skipped.  Items in the *context list are added to
            the context stack in order so that later items in the argument
            list take precedence over earlier items.

          **kwargs: additional key-value data to add to the context stack.
            As these arguments appear after all items in the *context list,
            in the case of key conflicts these values take precedence over
            all items in the *context list.

        """
        if is_string(template):
            return self._render_string(template, *context, **kwargs)
        if isinstance(template, ParsedTemplate):
            render_func = lambda engine, stack: template.render(engine, stack)
            return self._render_final(render_func, *context, **kwargs)
        # Otherwise, we assume the template is an object.

        return self._render_object(template, *context, **kwargs)

########NEW FILE########
__FILENAME__ = specloader
# coding: utf-8

"""
This module supports customized (aka special or specified) template loading.

"""

import os.path

from pystache.loader import Loader


# TODO: add test cases for this class.
class SpecLoader(object):

    """
    Supports loading custom-specified templates (from TemplateSpec instances).

    """

    def __init__(self, loader=None):
        if loader is None:
            loader = Loader()

        self.loader = loader

    def _find_relative(self, spec):
        """
        Return the path to the template as a relative (dir, file_name) pair.

        The directory returned is relative to the directory containing the
        class definition of the given object.  The method returns None for
        this directory if the directory is unknown without first searching
        the search directories.

        """
        if spec.template_rel_path is not None:
            return os.path.split(spec.template_rel_path)
        # Otherwise, determine the file name separately.

        locator = self.loader._make_locator()

        # We do not use the ternary operator for Python 2.4 support.
        if spec.template_name is not None:
            template_name = spec.template_name
        else:
            template_name = locator.make_template_name(spec)

        file_name = locator.make_file_name(template_name, spec.template_extension)

        return (spec.template_rel_directory, file_name)

    def _find(self, spec):
        """
        Find and return the path to the template associated to the instance.

        """
        if spec.template_path is not None:
            return spec.template_path

        dir_path, file_name = self._find_relative(spec)

        locator = self.loader._make_locator()

        if dir_path is None:
            # Then we need to search for the path.
            path = locator.find_object(spec, self.loader.search_dirs, file_name=file_name)
        else:
            obj_dir = locator.get_object_directory(spec)
            path = os.path.join(obj_dir, dir_path, file_name)

        return path

    def load(self, spec):
        """
        Find and return the template associated to a TemplateSpec instance.

        Returns the template as a unicode string.

        Arguments:

          spec: a TemplateSpec instance.

        """
        if spec.template is not None:
            return self.loader.unicode(spec.template, spec.template_encoding)

        path = self._find(spec)

        return self.loader.read(path, spec.template_encoding)

########NEW FILE########
__FILENAME__ = template_spec
# coding: utf-8

"""
Provides a class to customize template information on a per-view basis.

To customize template properties for a particular view, create that view
from a class that subclasses TemplateSpec.  The "spec" in TemplateSpec
stands for "special" or "specified" template information.

"""

class TemplateSpec(object):

    """
    A mixin or interface for specifying custom template information.

    The "spec" in TemplateSpec can be taken to mean that the template
    information is either "specified" or "special."

    A view should subclass this class only if customized template loading
    is needed.  The following attributes allow one to customize/override
    template information on a per view basis.  A None value means to use
    default behavior for that value and perform no customization.  All
    attributes are initialized to None.

    Attributes:

      template: the template as a string.

      template_encoding: the encoding used by the template.

      template_extension: the template file extension.  Defaults to "mustache".
        Pass False for no extension (i.e. extensionless template files).

      template_name: the name of the template.

      template_path: absolute path to the template.

      template_rel_directory: the directory containing the template file,
        relative to the directory containing the module defining the class.

      template_rel_path: the path to the template file, relative to the
        directory containing the module defining the class.

    """

    template = None
    template_encoding = None
    template_extension = None
    template_name = None
    template_path = None
    template_rel_directory = None
    template_rel_path = None

########NEW FILE########
__FILENAME__ = benchmark
#!/usr/bin/env python
# coding: utf-8

"""
A rudimentary backward- and forward-compatible script to benchmark pystache.

Usage:

tests/benchmark.py 10000

"""

import sys
from timeit import Timer

import pystache

# TODO: make the example realistic.

examples = [
    # Test case: 1
    ("""{{#person}}Hi {{name}}{{/person}}""",
    {"person": {"name": "Jon"}},
    "Hi Jon"),

    # Test case: 2
    ("""\
<div class="comments">
<h3>{{header}}</h3>
<ul>
{{#comments}}<li class="comment">
<h5>{{name}}</h5><p>{{body}}</p>
</li>{{/comments}}
</ul>
</div>""",
    {'header': "My Post Comments",
     'comments': [
         {'name': "Joe", 'body': "Thanks for this post!"},
         {'name': "Sam", 'body': "Thanks for this post!"},
         {'name': "Heather", 'body': "Thanks for this post!"},
         {'name': "Kathy", 'body': "Thanks for this post!"},
         {'name': "George", 'body': "Thanks for this post!"}]},
    """\
<div class="comments">
<h3>My Post Comments</h3>
<ul>
<li class="comment">
<h5>Joe</h5><p>Thanks for this post!</p>
</li><li class="comment">
<h5>Sam</h5><p>Thanks for this post!</p>
</li><li class="comment">
<h5>Heather</h5><p>Thanks for this post!</p>
</li><li class="comment">
<h5>Kathy</h5><p>Thanks for this post!</p>
</li><li class="comment">
<h5>George</h5><p>Thanks for this post!</p>
</li>
</ul>
</div>"""),
]


def make_test_function(example):

    template, context, expected = example

    def test():
        actual = pystache.render(template, context)
        if actual != expected:
            raise Exception("Benchmark mismatch: \n%s\n*** != ***\n%s" % (expected, actual))

    return test


def main(sys_argv):
    args = sys_argv[1:]
    count = int(args[0])

    print "Benchmarking: %sx" % count
    print

    for example in examples:

        test = make_test_function(example)

        t = Timer(test,)
        print min(t.repeat(repeat=3, number=count))

    print "Done"


if __name__ == '__main__':
    main(sys.argv)


########NEW FILE########
__FILENAME__ = common
# coding: utf-8

"""
Provides test-related code that can be used by all tests.

"""

import os

import pystache
from pystache import defaults
from pystache.tests import examples

# Save a reference to the original function to avoid recursion.
_DEFAULT_TAG_ESCAPE = defaults.TAG_ESCAPE
_TESTS_DIR = os.path.dirname(pystache.tests.__file__)

DATA_DIR = os.path.join(_TESTS_DIR, 'data')  # i.e. 'pystache/tests/data'.
EXAMPLES_DIR = os.path.dirname(examples.__file__)
PACKAGE_DIR = os.path.dirname(pystache.__file__)
PROJECT_DIR = os.path.join(PACKAGE_DIR, '..')
# TEXT_DOCTEST_PATHS: the paths to text files (i.e. non-module files)
# containing doctests.  The paths should be relative to the project directory.
TEXT_DOCTEST_PATHS = ['README.md']

UNITTEST_FILE_PREFIX = "test_"


def get_spec_test_dir(project_dir):
    return os.path.join(project_dir, 'ext', 'spec', 'specs')


def html_escape(u):
    """
    An html escape function that behaves the same in both Python 2 and 3.

    This function is needed because single quotes are escaped in Python 3
    (to '&#x27;'), but not in Python 2.

    The global defaults.TAG_ESCAPE can be set to this function in the
    setUp() and tearDown() of unittest test cases, for example, for
    consistent test results.

    """
    u = _DEFAULT_TAG_ESCAPE(u)
    return u.replace("'", '&#x27;')


def get_data_path(file_name=None):
    """Return the path to a file in the test data directory."""
    if file_name is None:
        file_name = ""
    return os.path.join(DATA_DIR, file_name)


# Functions related to get_module_names().

def _find_files(root_dir, should_include):
    """
    Return a list of paths to all modules below the given directory.

    Arguments:

      should_include: a function that accepts a file path and returns True or False.

    """
    paths = []  # Return value.

    is_module = lambda path: path.endswith(".py")

    # os.walk() is new in Python 2.3
    #   http://docs.python.org/library/os.html#os.walk
    for dir_path, dir_names, file_names in os.walk(root_dir):
        new_paths = [os.path.join(dir_path, file_name) for file_name in file_names]
        new_paths = filter(is_module, new_paths)
        new_paths = filter(should_include, new_paths)
        paths.extend(new_paths)

    return paths


def _make_module_names(package_dir, paths):
    """
    Return a list of fully-qualified module names given a list of module paths.

    """
    package_dir = os.path.abspath(package_dir)
    package_name = os.path.split(package_dir)[1]

    prefix_length = len(package_dir)

    module_names = []
    for path in paths:
        path = os.path.abspath(path)  # for example <path_to_package>/subpackage/module.py
        rel_path = path[prefix_length:]  # for example /subpackage/module.py
        rel_path = os.path.splitext(rel_path)[0]  # for example /subpackage/module

        parts = []
        while True:
            (rel_path, tail) = os.path.split(rel_path)
            if not tail:
                break
            parts.insert(0, tail)
        # We now have, for example, ['subpackage', 'module'].
        parts.insert(0, package_name)
        module = ".".join(parts)
        module_names.append(module)

    return module_names


def get_module_names(package_dir=None, should_include=None):
    """
    Return a list of fully-qualified module names in the given package.

    """
    if package_dir is None:
        package_dir = PACKAGE_DIR

    if should_include is None:
        should_include = lambda path: True

    paths = _find_files(package_dir, should_include)
    names = _make_module_names(package_dir, paths)
    names.sort()

    return names


class AssertStringMixin:

    """A unittest.TestCase mixin to check string equality."""

    def assertString(self, actual, expected, format=None):
        """
        Assert that the given strings are equal and have the same type.

        Arguments:

          format: a format string containing a single conversion specifier %s.
            Defaults to "%s".

        """
        if format is None:
            format = "%s"

        # Show both friendly and literal versions.
        details = """String mismatch: %%s

        Expected: \"""%s\"""
        Actual:   \"""%s\"""

        Expected: %s
        Actual:   %s""" % (expected, actual, repr(expected), repr(actual))

        def make_message(reason):
            description = details % reason
            return format % description

        self.assertEqual(actual, expected, make_message("different characters"))

        reason = "types different: %s != %s (actual)" % (repr(type(expected)), repr(type(actual)))
        self.assertEqual(type(expected), type(actual), make_message(reason))


class AssertIsMixin:

    """A unittest.TestCase mixin adding assertIs()."""

    # unittest.assertIs() is not available until Python 2.7:
    #   http://docs.python.org/library/unittest.html#unittest.TestCase.assertIsNone
    def assertIs(self, first, second):
        self.assertTrue(first is second, msg="%s is not %s" % (repr(first), repr(second)))


class AssertExceptionMixin:

    """A unittest.TestCase mixin adding assertException()."""

    # unittest.assertRaisesRegexp() is not available until Python 2.7:
    #   http://docs.python.org/library/unittest.html#unittest.TestCase.assertRaisesRegexp
    def assertException(self, exception_type, msg, callable, *args, **kwds):
        try:
            callable(*args, **kwds)
            raise Exception("Expected exception: %s: %s" % (exception_type, repr(msg)))
        except exception_type, err:
            self.assertEqual(str(err), msg)


class SetupDefaults(object):

    """
    Mix this class in to a unittest.TestCase for standard defaults.

    This class allows for consistent test results across Python 2/3.

    """

    def setup_defaults(self):
        self.original_decode_errors = defaults.DECODE_ERRORS
        self.original_file_encoding = defaults.FILE_ENCODING
        self.original_string_encoding = defaults.STRING_ENCODING

        defaults.DECODE_ERRORS = 'strict'
        defaults.FILE_ENCODING = 'ascii'
        defaults.STRING_ENCODING = 'ascii'

    def teardown_defaults(self):
        defaults.DECODE_ERRORS = self.original_decode_errors
        defaults.FILE_ENCODING = self.original_file_encoding
        defaults.STRING_ENCODING = self.original_string_encoding


class Attachable(object):
    """
    A class that attaches all constructor named parameters as attributes.

    For example--

    >>> obj = Attachable(foo=42, size="of the universe")
    >>> repr(obj)
    "Attachable(foo=42, size='of the universe')"
    >>> obj.foo
    42
    >>> obj.size
    'of the universe'

    """
    def __init__(self, **kwargs):
        self.__args__ = kwargs
        for arg, value in kwargs.iteritems():
            setattr(self, arg, value)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join("%s=%s" % (k, repr(v))
                                     for k, v in self.__args__.iteritems()))

########NEW FILE########
__FILENAME__ = views
# coding: utf-8

"""
TODO: add a docstring.

"""

from pystache import TemplateSpec

class SayHello(object):

    def to(self):
        return "World"


class SampleView(TemplateSpec):
    pass


class NonAscii(TemplateSpec):
    pass

########NEW FILE########
__FILENAME__ = doctesting
# coding: utf-8

"""
Exposes a get_doctests() function for the project's test harness.

"""

import doctest
import os
import pkgutil
import sys
import traceback

if sys.version_info >= (3,):
    # Then pull in modules needed for 2to3 conversion.  The modules
    # below are not necessarily available in older versions of Python.
    from lib2to3.main import main as lib2to3main  # new in Python 2.6?
    from shutil import copyfile

from pystache.tests.common import TEXT_DOCTEST_PATHS
from pystache.tests.common import get_module_names


# This module follows the guidance documented here:
#
#   http://docs.python.org/library/doctest.html#unittest-api
#

def get_doctests(text_file_dir):
    """
    Return a list of TestSuite instances for all doctests in the project.

    Arguments:

      text_file_dir: the directory in which to search for all text files
        (i.e. non-module files) containing doctests.

    """
    # Since module_relative is False in our calls to DocFileSuite below,
    # paths should be OS-specific.  See the following for more info--
    #
    #   http://docs.python.org/library/doctest.html#doctest.DocFileSuite
    #
    paths = [os.path.normpath(os.path.join(text_file_dir, path)) for path in TEXT_DOCTEST_PATHS]

    if sys.version_info >= (3,):
        # Skip the README doctests in Python 3 for now because examples
        # rendering to unicode do not give consistent results
        # (e.g. 'foo' vs u'foo').
        # paths = _convert_paths(paths)
        paths = []

    suites = []

    for path in paths:
        suite = doctest.DocFileSuite(path, module_relative=False)
        suites.append(suite)

    modules = get_module_names()
    for module in modules:
        suite = doctest.DocTestSuite(module)
        suites.append(suite)

    return suites


def _convert_2to3(path):
    """
    Convert the given file, and return the path to the converted files.

    """
    base, ext = os.path.splitext(path)
    # For example, "README.temp2to3.rst".
    new_path = "%s.temp2to3%s" % (base, ext)

    copyfile(path, new_path)

    args = ['--doctests_only', '--no-diffs', '--write', '--nobackups', new_path]
    lib2to3main("lib2to3.fixes", args=args)

    return new_path


def _convert_paths(paths):
    """
    Convert the given files, and return the paths to the converted files.

    """
    new_paths = []
    for path in paths:
        new_path = _convert_2to3(path)
        new_paths.append(new_path)

    return new_paths

########NEW FILE########
__FILENAME__ = comments

"""
TODO: add a docstring.

"""

class Comments(object):

    def title(self):
        return "A Comedy of Errors"

########NEW FILE########
__FILENAME__ = complex

"""
TODO: add a docstring.

"""

class Complex(object):

    def header(self):
        return "Colors"

    def item(self):
        items = []
        items.append({ 'name': 'red', 'current': True, 'url': '#Red' })
        items.append({ 'name': 'green', 'link': True, 'url': '#Green' })
        items.append({ 'name': 'blue', 'link': True, 'url': '#Blue' })
        return items

    def list(self):
        return not self.empty()

    def empty(self):
        return len(self.item()) == 0

    def empty_list(self):
        return [];

########NEW FILE########
__FILENAME__ = delimiters

"""
TODO: add a docstring.

"""

class Delimiters(object):

    def first(self):
        return "It worked the first time."

    def second(self):
        return "And it worked the second time."

    def third(self):
        return "Then, surprisingly, it worked the third time."

########NEW FILE########
__FILENAME__ = double_section

"""
TODO: add a docstring.

"""

class DoubleSection(object):

    def t(self):
        return True

    def two(self):
        return "second"

########NEW FILE########
__FILENAME__ = escaped

"""
TODO: add a docstring.

"""

class Escaped(object):

    def title(self):
        return "Bear > Shark"

########NEW FILE########
__FILENAME__ = inverted

"""
TODO: add a docstring.

"""

from pystache import TemplateSpec

class Inverted(object):

    def t(self):
        return True

    def f(self):
        return False

    def two(self):
        return 'two'

    def empty_list(self):
        return []

    def populated_list(self):
        return ['some_value']

class InvertedLists(Inverted, TemplateSpec):
    template_name = 'inverted'

    def t(self):
        return [0, 1, 2]

    def f(self):
        return []

########NEW FILE########
__FILENAME__ = lambdas

"""
TODO: add a docstring.

"""

from pystache import TemplateSpec

def rot(s, n=13):
    r = ""
    for c in s:
        cc = c
        if cc.isalpha():
            cc = cc.lower()
            o = ord(cc)
            ro = (o+n) % 122
            if ro == 0: ro = 122
            if ro < 97: ro += 96
            cc = chr(ro)
        r = ''.join((r,cc))
    return r

def replace(subject, this='foo', with_this='bar'):
    return subject.replace(this, with_this)


# This class subclasses TemplateSpec because at least one unit test
# sets the template attribute.
class Lambdas(TemplateSpec):

    def replace_foo_with_bar(self, text=None):
        return replace

    def rot13(self, text=None):
        return rot

    def sort(self, text=None):
        return lambda text: ''.join(sorted(text))

########NEW FILE########
__FILENAME__ = nested_context

"""
TODO: add a docstring.

"""

from pystache import TemplateSpec

class NestedContext(TemplateSpec):

    def __init__(self, renderer):
        self.renderer = renderer

    def _context_get(self, key):
        return self.renderer.context.get(key)

    def outer_thing(self):
        return "two"

    def foo(self):
        return {'thing1': 'one', 'thing2': 'foo'}

    def derp(self):
        return [{'inner': 'car'}]

    def herp(self):
        return [{'outer': 'car'}]

    def nested_context_in_view(self):
        if self._context_get('outer') == self._context_get('inner'):
            return 'it works!'
        return ''

########NEW FILE########
__FILENAME__ = partials_with_lambdas

"""
TODO: add a docstring.

"""

from pystache.tests.examples.lambdas import rot

class PartialsWithLambdas(object):

    def rot(self):
        return rot

########NEW FILE########
__FILENAME__ = readme

"""
TODO: add a docstring.

"""

class SayHello(object):
    def to(self):
        return "Pizza"

########NEW FILE########
__FILENAME__ = simple

"""
TODO: add a docstring.

"""

from pystache import TemplateSpec

class Simple(TemplateSpec):

    def thing(self):
        return "pizza"

    def blank(self):
        return ''

########NEW FILE########
__FILENAME__ = template_partial

"""
TODO: add a docstring.

"""

from pystache import TemplateSpec

class TemplatePartial(TemplateSpec):

    def __init__(self, renderer):
        self.renderer = renderer

    def _context_get(self, key):
        return self.renderer.context.get(key)

    def title(self):
        return "Welcome"

    def title_bars(self):
        return '-' * len(self.title())

    def looping(self):
        return [{'item': 'one'}, {'item': 'two'}, {'item': 'three'}]

    def thing(self):
        return self._context_get('prop')

########NEW FILE########
__FILENAME__ = unescaped

"""
TODO: add a docstring.

"""

class Unescaped(object):

    def title(self):
        return "Bear > Shark"

########NEW FILE########
__FILENAME__ = unicode_input

"""
TODO: add a docstring.

"""

from pystache import TemplateSpec

class UnicodeInput(TemplateSpec):

    template_encoding = 'utf8'

    def age(self):
        return 156

########NEW FILE########
__FILENAME__ = unicode_output
# encoding: utf-8

"""
TODO: add a docstring.

"""

class UnicodeOutput(object):

    def name(self):
        return u'Henri Poincaré'

########NEW FILE########
__FILENAME__ = main
# coding: utf-8

"""
Exposes a main() function that runs all tests in the project.

This module is for our test console script.

"""

import os
import sys
import unittest
from unittest import TestCase, TestProgram

import pystache
from pystache.tests.common import PACKAGE_DIR, PROJECT_DIR, UNITTEST_FILE_PREFIX
from pystache.tests.common import get_module_names, get_spec_test_dir
from pystache.tests.doctesting import get_doctests
from pystache.tests.spectesting import get_spec_tests


# If this command option is present, then the spec test and doctest directories
# will be inserted if not provided.
FROM_SOURCE_OPTION = "--from-source"


def make_extra_tests(text_doctest_dir, spec_test_dir):
    tests = []

    if text_doctest_dir is not None:
        doctest_suites = get_doctests(text_doctest_dir)
        tests.extend(doctest_suites)

    if spec_test_dir is not None:
        spec_testcases = get_spec_tests(spec_test_dir)
        tests.extend(spec_testcases)

    return unittest.TestSuite(tests)


def make_test_program_class(extra_tests):
    """
    Return a subclass of unittest.TestProgram.

    """
    # The function unittest.main() is an alias for unittest.TestProgram's
    # constructor.  TestProgram's constructor does the following:
    #
    # 1. calls self.parseArgs(argv),
    # 2. which in turn calls self.createTests().
    # 3. then the constructor calls self.runTests().
    #
    # The createTests() method sets the self.test attribute by calling one
    # of self.testLoader's "loadTests" methods.  Each loadTest method returns
    # a unittest.TestSuite instance.  Thus, self.test is set to a TestSuite
    # instance prior to calling runTests().
    class PystacheTestProgram(TestProgram):

        """
        Instantiating an instance of this class runs all tests.

        """

        def createTests(self):
            """
            Load tests and set self.test to a unittest.TestSuite instance

            Compare--

              http://docs.python.org/library/unittest.html#unittest.TestSuite

            """
            super(PystacheTestProgram, self).createTests()
            self.test.addTests(extra_tests)

    return PystacheTestProgram


# Do not include "test" in this function's name to avoid it getting
# picked up by nosetests.
def main(sys_argv):
    """
    Run all tests in the project.

    Arguments:

      sys_argv: a reference to sys.argv.

    """
    # TODO: use logging module
    print "pystache: running tests: argv: %s" % repr(sys_argv)

    should_source_exist = False
    spec_test_dir = None
    project_dir = None

    if len(sys_argv) > 1 and sys_argv[1] == FROM_SOURCE_OPTION:
        # This usually means the test_pystache.py convenience script
        # in the source directory was run.
        should_source_exist = True
        sys_argv.pop(1)

    try:
        # TODO: use optparse command options instead.
        project_dir = sys_argv[1]
        sys_argv.pop(1)
    except IndexError:
        if should_source_exist:
            project_dir = PROJECT_DIR

    try:
        # TODO: use optparse command options instead.
        spec_test_dir = sys_argv[1]
        sys_argv.pop(1)
    except IndexError:
        if project_dir is not None:
            # Then auto-detect the spec test directory.
            _spec_test_dir = get_spec_test_dir(project_dir)
            if not os.path.exists(_spec_test_dir):
                # Then the user is probably using a downloaded sdist rather
                # than a repository clone (since the sdist does not include
                # the spec test directory).
                print("pystache: skipping spec tests: spec test directory "
                      "not found")
            else:
                spec_test_dir = _spec_test_dir

    if len(sys_argv) <= 1 or sys_argv[-1].startswith("-"):
        # Then no explicit module or test names were provided, so
        # auto-detect all unit tests.
        module_names = _discover_test_modules(PACKAGE_DIR)
        sys_argv.extend(module_names)
        if project_dir is not None:
            # Add the current module for unit tests contained here (e.g.
            # to include SetupTests).
            sys_argv.append(__name__)

    SetupTests.project_dir = project_dir

    extra_tests = make_extra_tests(project_dir, spec_test_dir)
    test_program_class = make_test_program_class(extra_tests)

    # We pass None for the module because we do not want the unittest
    # module to resolve module names relative to a given module.
    # (This would require importing all of the unittest modules from
    # this module.)  See the loadTestsFromName() method of the
    # unittest.TestLoader class for more details on this parameter.
    test_program_class(argv=sys_argv, module=None)
    # No need to return since unitttest.main() exits.


def _discover_test_modules(package_dir):
    """
    Discover and return a sorted list of the names of unit-test modules.

    """
    def is_unittest_module(path):
        file_name = os.path.basename(path)
        return file_name.startswith(UNITTEST_FILE_PREFIX)

    names = get_module_names(package_dir=package_dir, should_include=is_unittest_module)

    # This is a sanity check to ensure that the unit-test discovery
    # methods are working.
    if len(names) < 1:
        raise Exception("No unit-test modules found--\n  in %s" % package_dir)

    return names


class SetupTests(TestCase):

    """Tests about setup.py."""

    project_dir = None

    def test_version(self):
        """
        Test that setup.py's version matches the package's version.

        """
        original_path = list(sys.path)

        sys.path.insert(0, self.project_dir)

        try:
            from setup import VERSION
            self.assertEqual(VERSION, pystache.__version__)
        finally:
            sys.path = original_path

########NEW FILE########
__FILENAME__ = spectesting
# coding: utf-8

"""
Exposes a get_spec_tests() function for the project's test harness.

Creates a unittest.TestCase for the tests defined in the mustache spec.

"""

# TODO: this module can be cleaned up somewhat.
# TODO: move all of this code to pystache/tests/spectesting.py and
#   have it expose a get_spec_tests(spec_test_dir) function.

FILE_ENCODING = 'utf-8'  # the encoding of the spec test files.

yaml = None

try:
    # We try yaml first since it is more convenient when adding and modifying
    # test cases by hand (since the YAML is human-readable and is the master
    # from which the JSON format is generated).
    import yaml
except ImportError:
    try:
        import json
    except:
        # The module json is not available prior to Python 2.6, whereas
        # simplejson is.  The simplejson package dropped support for Python 2.4
        # in simplejson v2.1.0, so Python 2.4 requires a simplejson install
        # older than the most recent version.
        try:
            import simplejson as json
        except ImportError:
            # Raise an error with a type different from ImportError as a hack around
            # this issue:
            #   http://bugs.python.org/issue7559
            from sys import exc_info
            ex_type, ex_value, tb = exc_info()
            new_ex = Exception("%s: %s" % (ex_type.__name__, ex_value))
            raise new_ex.__class__, new_ex, tb
    file_extension = 'json'
    parser = json
else:
    file_extension = 'yml'
    parser = yaml


import codecs
import glob
import os.path
import unittest

import pystache
from pystache import common
from pystache.renderer import Renderer
from pystache.tests.common import AssertStringMixin


def get_spec_tests(spec_test_dir):
    """
    Return a list of unittest.TestCase instances.

    """
    # TODO: use logging module instead.
    print "pystache: spec tests: using %s" % _get_parser_info()

    cases = []

    # Make this absolute for easier diagnosis in case of error.
    spec_test_dir = os.path.abspath(spec_test_dir)
    spec_paths = glob.glob(os.path.join(spec_test_dir, '*.%s' % file_extension))

    for path in spec_paths:
        new_cases = _read_spec_tests(path)
        cases.extend(new_cases)

    # Store this as a value so that CheckSpecTestsFound is not checking
    # a reference to cases that contains itself.
    spec_test_count = len(cases)

    # This test case lets us alert the user that spec tests are missing.
    class CheckSpecTestsFound(unittest.TestCase):

        def runTest(self):
            if spec_test_count > 0:
                return
            raise Exception("Spec tests not found--\n  in %s\n"
                " Consult the README file on how to add the Mustache spec tests." % repr(spec_test_dir))

    case = CheckSpecTestsFound()
    cases.append(case)

    return cases


def _get_parser_info():
    return "%s (version %s)" % (parser.__name__, parser.__version__)


def _read_spec_tests(path):
    """
    Return a list of unittest.TestCase instances.

    """
    b = common.read(path)
    u = unicode(b, encoding=FILE_ENCODING)
    spec_data = parse(u)
    tests = spec_data['tests']

    cases = []
    for data in tests:
        case = _deserialize_spec_test(data, path)
        cases.append(case)

    return cases


# TODO: simplify the implementation of this function.
def _convert_children(node):
    """
    Recursively convert to functions all "code strings" below the node.

    This function is needed only for the json format.

    """
    if not isinstance(node, (list, dict)):
        # Then there is nothing to iterate over and recurse.
        return

    if isinstance(node, list):
        for child in node:
            _convert_children(child)
        return
    # Otherwise, node is a dict, so attempt the conversion.

    for key in node.keys():
        val = node[key]

        if not isinstance(val, dict) or val.get('__tag__') != 'code':
            _convert_children(val)
            continue
        # Otherwise, we are at a "leaf" node.

        val = eval(val['python'])
        node[key] = val
        continue


def _deserialize_spec_test(data, file_path):
    """
    Return a unittest.TestCase instance representing a spec test.

    Arguments:

      data: the dictionary of attributes for a single test.

    """
    context = data['data']
    description = data['desc']
    # PyYAML seems to leave ASCII strings as byte strings.
    expected = unicode(data['expected'])
    # TODO: switch to using dict.get().
    partials = data.has_key('partials') and data['partials'] or {}
    template = data['template']
    test_name = data['name']

    _convert_children(context)

    test_case = _make_spec_test(expected, template, context, partials, description, test_name, file_path)

    return test_case


def _make_spec_test(expected, template, context, partials, description, test_name, file_path):
    """
    Return a unittest.TestCase instance representing a spec test.

    """
    file_name  = os.path.basename(file_path)
    test_method_name = "Mustache spec (%s): %s" % (file_name, repr(test_name))

    # We subclass SpecTestBase in order to control the test method name (for
    # the purposes of improved reporting).
    class SpecTest(SpecTestBase):
        pass

    def run_test(self):
        self._runTest()

    # TODO: should we restore this logic somewhere?
    # If we don't convert unicode to str, we get the following error:
    #   "TypeError: __name__ must be set to a string object"
    # test.__name__ = str(name)
    setattr(SpecTest, test_method_name, run_test)
    case = SpecTest(test_method_name)

    case._context = context
    case._description = description
    case._expected = expected
    case._file_path = file_path
    case._partials = partials
    case._template = template
    case._test_name = test_name

    return case


def parse(u):
    """
    Parse the contents of a spec test file, and return a dict.

    Arguments:

      u: a unicode string.

    """
    # TODO: find a cleaner mechanism for choosing between the two.
    if yaml is None:
        # Then use json.

        # The only way to get the simplejson module to return unicode strings
        # is to pass it unicode.  See, for example--
        #
        #   http://code.google.com/p/simplejson/issues/detail?id=40
        #
        # and the documentation of simplejson.loads():
        #
        #   "If s is a str then decoded JSON strings that contain only ASCII
        #    characters may be parsed as str for performance and memory reasons.
        #    If your code expects only unicode the appropriate solution is
        #    decode s to unicode prior to calling loads."
        #
        return json.loads(u)
    # Otherwise, yaml.

    def code_constructor(loader, node):
        value = loader.construct_mapping(node)
        return eval(value['python'], {})

    yaml.add_constructor(u'!code', code_constructor)
    return yaml.load(u)


class SpecTestBase(unittest.TestCase, AssertStringMixin):

    def _runTest(self):
        context = self._context
        description = self._description
        expected = self._expected
        file_path = self._file_path
        partials = self._partials
        template = self._template
        test_name = self._test_name

        renderer = Renderer(partials=partials)
        actual = renderer.render(template, context)

        # We need to escape the strings that occur in our format string because
        # they can contain % symbols, for example (in delimiters.yml)--
        #
        #   "template: '{{=<% %>=}}(<%text%>)'"
        #
        def escape(s):
            return s.replace("%", "%%")

        parser_info = _get_parser_info()
        subs = [repr(test_name), description, os.path.abspath(file_path),
                template, repr(context), parser_info]
        subs = tuple([escape(sub) for sub in subs])
        # We include the parsing module version info to help with troubleshooting
        # yaml/json/simplejson issues.
        message = """%s: %s

  File: %s

  Template: \"""%s\"""

  Context: %s

  %%s

  [using %s]
  """ % subs

        self.assertString(actual, expected, format=message)

########NEW FILE########
__FILENAME__ = test_commands
# coding: utf-8

"""
Unit tests of commands.py.

"""

import sys
import unittest

from pystache.commands.render import main


ORIGINAL_STDOUT = sys.stdout


class MockStdout(object):

    def __init__(self):
        self.output = ""

    def write(self, str):
        self.output += str


class CommandsTestCase(unittest.TestCase):

    def setUp(self):
        sys.stdout = MockStdout()

    def callScript(self, template, context):
        argv = ['pystache', template, context]
        main(argv)
        return sys.stdout.output

    def testMainSimple(self):
        """
        Test a simple command-line case.

        """
        actual = self.callScript("Hi {{thing}}", '{"thing": "world"}')
        self.assertEqual(actual, u"Hi world\n")

    def tearDown(self):
        sys.stdout = ORIGINAL_STDOUT

########NEW FILE########
__FILENAME__ = test_context
# coding: utf-8

"""
Unit tests of context.py.

"""

from datetime import datetime
import unittest

from pystache.context import _NOT_FOUND, _get_value, KeyNotFoundError, ContextStack
from pystache.tests.common import AssertIsMixin, AssertStringMixin, AssertExceptionMixin, Attachable

class SimpleObject(object):

    """A sample class that does not define __getitem__()."""

    def __init__(self):
        self.foo = "bar"

    def foo_callable(self):
        return "called..."


class DictLike(object):

    """A sample class that implements __getitem__() and __contains__()."""

    def __init__(self):
        self._dict = {'foo': 'bar'}
        self.fuzz = 'buzz'

    def __contains__(self, key):
        return key in self._dict

    def __getitem__(self, key):
        return self._dict[key]


class GetValueTestCase(unittest.TestCase, AssertIsMixin):

    """Test context._get_value()."""

    def assertNotFound(self, item, key):
        """
        Assert that a call to _get_value() returns _NOT_FOUND.

        """
        self.assertIs(_get_value(item, key), _NOT_FOUND)

    ### Case: the item is a dictionary.

    def test_dictionary__key_present(self):
        """
        Test getting a key from a dictionary.

        """
        item = {"foo": "bar"}
        self.assertEqual(_get_value(item, "foo"), "bar")

    def test_dictionary__callable_not_called(self):
        """
        Test that callable values are returned as-is (and in particular not called).

        """
        def foo_callable(self):
            return "bar"

        item = {"foo": foo_callable}
        self.assertNotEqual(_get_value(item, "foo"), "bar")
        self.assertTrue(_get_value(item, "foo") is foo_callable)

    def test_dictionary__key_missing(self):
        """
        Test getting a missing key from a dictionary.

        """
        item = {}
        self.assertNotFound(item, "missing")

    def test_dictionary__attributes_not_checked(self):
        """
        Test that dictionary attributes are not checked.

        """
        item = {1: 2, 3: 4}
        # I was not able to find a "public" attribute of dict that is
        # the same across Python 2/3.
        attr_name = "__len__"
        self.assertEqual(getattr(item, attr_name)(), 2)
        self.assertNotFound(item, attr_name)

    def test_dictionary__dict_subclass(self):
        """
        Test that subclasses of dict are treated as dictionaries.

        """
        class DictSubclass(dict): pass

        item = DictSubclass()
        item["foo"] = "bar"

        self.assertEqual(_get_value(item, "foo"), "bar")

    ### Case: the item is an object.

    def test_object__attribute_present(self):
        """
        Test getting an attribute from an object.

        """
        item = SimpleObject()
        self.assertEqual(_get_value(item, "foo"), "bar")

    def test_object__attribute_missing(self):
        """
        Test getting a missing attribute from an object.

        """
        item = SimpleObject()
        self.assertNotFound(item, "missing")

    def test_object__attribute_is_callable(self):
        """
        Test getting a callable attribute from an object.

        """
        item = SimpleObject()
        self.assertEqual(_get_value(item, "foo_callable"), "called...")

    def test_object__non_built_in_type(self):
        """
        Test getting an attribute from an instance of a type that isn't built-in.

        """
        item = datetime(2012, 1, 2)
        self.assertEqual(_get_value(item, "day"), 2)

    def test_object__dict_like(self):
        """
        Test getting a key from a dict-like object (an object that implements '__getitem__').

        """
        item = DictLike()
        self.assertEqual(item["foo"], "bar")
        self.assertNotFound(item, "foo")

    def test_object__property__raising_exception(self):
        """
        Test getting a property that raises an exception.

        """
        class Foo(object):

            @property
            def bar(self):
                return 1

            @property
            def baz(self):
                raise ValueError("test")

        foo = Foo()
        self.assertEqual(_get_value(foo, 'bar'), 1)
        self.assertNotFound(foo, 'missing')
        self.assertRaises(ValueError, _get_value, foo, 'baz')

    ### Case: the item is an instance of a built-in type.

    def test_built_in_type__integer(self):
        """
        Test getting from an integer.

        """
        class MyInt(int): pass

        cust_int = MyInt(10)
        pure_int = 10

        # We have to use a built-in method like __neg__ because "public"
        # attributes like "real" were not added to Python until Python 2.6,
        # when the numeric type hierarchy was added:
        #
        #   http://docs.python.org/library/numbers.html
        #
        self.assertEqual(cust_int.__neg__(), -10)
        self.assertEqual(pure_int.__neg__(), -10)

        self.assertEqual(_get_value(cust_int, '__neg__'), -10)
        self.assertNotFound(pure_int, '__neg__')

    def test_built_in_type__string(self):
        """
        Test getting from a string.

        """
        class MyStr(str): pass

        item1 = MyStr('abc')
        item2 = 'abc'

        self.assertEqual(item1.upper(), 'ABC')
        self.assertEqual(item2.upper(), 'ABC')

        self.assertEqual(_get_value(item1, 'upper'), 'ABC')
        self.assertNotFound(item2, 'upper')

    def test_built_in_type__list(self):
        """
        Test getting from a list.

        """
        class MyList(list): pass

        item1 = MyList([1, 2, 3])
        item2 = [1, 2, 3]

        self.assertEqual(item1.pop(), 3)
        self.assertEqual(item2.pop(), 3)

        self.assertEqual(_get_value(item1, 'pop'), 2)
        self.assertNotFound(item2, 'pop')


class ContextStackTestCase(unittest.TestCase, AssertIsMixin, AssertStringMixin,
                           AssertExceptionMixin):

    """
    Test the ContextStack class.

    """

    def test_init__no_elements(self):
        """
        Check that passing nothing to __init__() raises no exception.

        """
        context = ContextStack()

    def test_init__many_elements(self):
        """
        Check that passing more than two items to __init__() raises no exception.

        """
        context = ContextStack({}, {}, {})

    def test__repr(self):
        context = ContextStack()
        self.assertEqual(repr(context), 'ContextStack()')

        context = ContextStack({'foo': 'bar'})
        self.assertEqual(repr(context), "ContextStack({'foo': 'bar'},)")

        context = ContextStack({'foo': 'bar'}, {'abc': 123})
        self.assertEqual(repr(context), "ContextStack({'foo': 'bar'}, {'abc': 123})")

    def test__str(self):
        context = ContextStack()
        self.assertEqual(str(context), 'ContextStack()')

        context = ContextStack({'foo': 'bar'})
        self.assertEqual(str(context), "ContextStack({'foo': 'bar'},)")

        context = ContextStack({'foo': 'bar'}, {'abc': 123})
        self.assertEqual(str(context), "ContextStack({'foo': 'bar'}, {'abc': 123})")

    ## Test the static create() method.

    def test_create__dictionary(self):
        """
        Test passing a dictionary.

        """
        context = ContextStack.create({'foo': 'bar'})
        self.assertEqual(context.get('foo'), 'bar')

    def test_create__none(self):
        """
        Test passing None.

        """
        context = ContextStack.create({'foo': 'bar'}, None)
        self.assertEqual(context.get('foo'), 'bar')

    def test_create__object(self):
        """
        Test passing an object.

        """
        class Foo(object):
            foo = 'bar'
        context = ContextStack.create(Foo())
        self.assertEqual(context.get('foo'), 'bar')

    def test_create__context(self):
        """
        Test passing a ContextStack instance.

        """
        obj = ContextStack({'foo': 'bar'})
        context = ContextStack.create(obj)
        self.assertEqual(context.get('foo'), 'bar')

    def test_create__kwarg(self):
        """
        Test passing a keyword argument.

        """
        context = ContextStack.create(foo='bar')
        self.assertEqual(context.get('foo'), 'bar')

    def test_create__precedence_positional(self):
        """
        Test precedence of positional arguments.

        """
        context = ContextStack.create({'foo': 'bar'}, {'foo': 'buzz'})
        self.assertEqual(context.get('foo'), 'buzz')

    def test_create__precedence_keyword(self):
        """
        Test precedence of keyword arguments.

        """
        context = ContextStack.create({'foo': 'bar'}, foo='buzz')
        self.assertEqual(context.get('foo'), 'buzz')

    ## Test the get() method.

    def test_get__single_dot(self):
        """
        Test getting a single dot (".").

        """
        context = ContextStack("a", "b")
        self.assertEqual(context.get("."), "b")

    def test_get__single_dot__missing(self):
        """
        Test getting a single dot (".") with an empty context stack.

        """
        context = ContextStack()
        self.assertException(KeyNotFoundError, "Key '.' not found: empty context stack", context.get, ".")

    def test_get__key_present(self):
        """
        Test getting a key.

        """
        context = ContextStack({"foo": "bar"})
        self.assertEqual(context.get("foo"), "bar")

    def test_get__key_missing(self):
        """
        Test getting a missing key.

        """
        context = ContextStack()
        self.assertException(KeyNotFoundError, "Key 'foo' not found: first part", context.get, "foo")

    def test_get__precedence(self):
        """
        Test that get() respects the order of precedence (later items first).

        """
        context = ContextStack({"foo": "bar"}, {"foo": "buzz"})
        self.assertEqual(context.get("foo"), "buzz")

    def test_get__fallback(self):
        """
        Check that first-added stack items are queried on context misses.

        """
        context = ContextStack({"fuzz": "buzz"}, {"foo": "bar"})
        self.assertEqual(context.get("fuzz"), "buzz")

    def test_push(self):
        """
        Test push().

        """
        key = "foo"
        context = ContextStack({key: "bar"})
        self.assertEqual(context.get(key), "bar")

        context.push({key: "buzz"})
        self.assertEqual(context.get(key), "buzz")

    def test_pop(self):
        """
        Test pop().

        """
        key = "foo"
        context = ContextStack({key: "bar"}, {key: "buzz"})
        self.assertEqual(context.get(key), "buzz")

        item = context.pop()
        self.assertEqual(item, {"foo": "buzz"})
        self.assertEqual(context.get(key), "bar")

    def test_top(self):
        key = "foo"
        context = ContextStack({key: "bar"}, {key: "buzz"})
        self.assertEqual(context.get(key), "buzz")

        top = context.top()
        self.assertEqual(top, {"foo": "buzz"})
        # Make sure calling top() didn't remove the item from the stack.
        self.assertEqual(context.get(key), "buzz")

    def test_copy(self):
        key = "foo"
        original = ContextStack({key: "bar"}, {key: "buzz"})
        self.assertEqual(original.get(key), "buzz")

        new = original.copy()
        # Confirm that the copy behaves the same.
        self.assertEqual(new.get(key), "buzz")
        # Change the copy, and confirm it is changed.
        new.pop()
        self.assertEqual(new.get(key), "bar")
        # Confirm the original is unchanged.
        self.assertEqual(original.get(key), "buzz")

    def test_dot_notation__dict(self):
        name = "foo.bar"
        stack = ContextStack({"foo": {"bar": "baz"}})
        self.assertEqual(stack.get(name), "baz")

        # Works all the way down
        name = "a.b.c.d.e.f.g"
        stack = ContextStack({"a": {"b": {"c": {"d": {"e": {"f": {"g": "w00t!"}}}}}}})
        self.assertEqual(stack.get(name), "w00t!")

    def test_dot_notation__user_object(self):
        name = "foo.bar"
        stack = ContextStack({"foo": Attachable(bar="baz")})
        self.assertEqual(stack.get(name), "baz")

        # Works on multiple levels, too
        name = "a.b.c.d.e.f.g"
        A = Attachable
        stack = ContextStack({"a": A(b=A(c=A(d=A(e=A(f=A(g="w00t!"))))))})
        self.assertEqual(stack.get(name), "w00t!")

    def test_dot_notation__mixed_dict_and_obj(self):
        name = "foo.bar.baz.bak"
        stack = ContextStack({"foo": Attachable(bar={"baz": Attachable(bak=42)})})
        self.assertEqual(stack.get(name), 42)

    def test_dot_notation__missing_attr_or_key(self):
        name = "foo.bar.baz.bak"
        stack = ContextStack({"foo": {"bar": {}}})
        self.assertException(KeyNotFoundError, "Key 'foo.bar.baz.bak' not found: missing 'baz'", stack.get, name)

        stack = ContextStack({"foo": Attachable(bar=Attachable())})
        self.assertException(KeyNotFoundError, "Key 'foo.bar.baz.bak' not found: missing 'baz'", stack.get, name)

    def test_dot_notation__missing_part_terminates_search(self):
        """
        Test that dotted name resolution terminates on a later part not found.

        Check that if a later dotted name part is not found in the result from
        the former resolution, then name resolution terminates rather than
        starting the search over with the next element of the context stack.
        From the spec (interpolation section)--

          5) If any name parts were retained in step 1, each should be resolved
          against a context stack containing only the result from the former
          resolution.  If any part fails resolution, the result should be considered
          falsey, and should interpolate as the empty string.

        This test case is equivalent to the test case in the following pull
        request:

          https://github.com/mustache/spec/pull/48

        """
        stack = ContextStack({'a': {'b': 'A.B'}}, {'a': 'A'})
        self.assertEqual(stack.get('a'), 'A')
        self.assertException(KeyNotFoundError, "Key 'a.b' not found: missing 'b'", stack.get, "a.b")
        stack.pop()
        self.assertEqual(stack.get('a.b'), 'A.B')

    def test_dot_notation__autocall(self):
        name = "foo.bar.baz"

        # When any element in the path is callable, it should be automatically invoked
        stack = ContextStack({"foo": Attachable(bar=Attachable(baz=lambda: "Called!"))})
        self.assertEqual(stack.get(name), "Called!")

        class Foo(object):
            def bar(self):
                return Attachable(baz='Baz')

        stack = ContextStack({"foo": Foo()})
        self.assertEqual(stack.get(name), "Baz")

########NEW FILE########
__FILENAME__ = test_defaults
# coding: utf-8

"""
Unit tests for defaults.py.

"""

import unittest

import pystache

from pystache.tests.common import AssertStringMixin


# TODO: make sure each default has at least one test.
class DefaultsConfigurableTestCase(unittest.TestCase, AssertStringMixin):

    """Tests that the user can change the defaults at runtime."""

    # TODO: switch to using a context manager after 2.4 is deprecated.
    def setUp(self):
        """Save the defaults."""
        defaults = [
            'DECODE_ERRORS', 'DELIMITERS',
            'FILE_ENCODING', 'MISSING_TAGS',
            'SEARCH_DIRS', 'STRING_ENCODING',
            'TAG_ESCAPE', 'TEMPLATE_EXTENSION'
        ]
        self.saved = {}
        for e in defaults:
            self.saved[e] = getattr(pystache.defaults, e)

    def tearDown(self):
        for key, value in self.saved.items():
            setattr(pystache.defaults, key, value)

    def test_tag_escape(self):
        """Test that changes to defaults.TAG_ESCAPE take effect."""
        template = u"{{foo}}"
        context = {'foo': '<'}
        actual = pystache.render(template, context)
        self.assertString(actual, u"&lt;")

        pystache.defaults.TAG_ESCAPE = lambda u: u
        actual = pystache.render(template, context)
        self.assertString(actual, u"<")

    def test_delimiters(self):
        """Test that changes to defaults.DELIMITERS take effect."""
        template = u"[[foo]]{{foo}}"
        context = {'foo': 'FOO'}
        actual = pystache.render(template, context)
        self.assertString(actual, u"[[foo]]FOO")

        pystache.defaults.DELIMITERS = ('[[', ']]')
        actual = pystache.render(template, context)
        self.assertString(actual, u"FOO{{foo}}")

    def test_missing_tags(self):
        """Test that changes to defaults.MISSING_TAGS take effect."""
        template = u"{{foo}}"
        context = {}
        actual = pystache.render(template, context)
        self.assertString(actual, u"")

        pystache.defaults.MISSING_TAGS = 'strict'
        self.assertRaises(pystache.context.KeyNotFoundError,
                          pystache.render, template, context)

########NEW FILE########
__FILENAME__ = test_examples
# encoding: utf-8

"""
TODO: add a docstring.

"""

import unittest

from examples.comments import Comments
from examples.double_section import DoubleSection
from examples.escaped import Escaped
from examples.unescaped import Unescaped
from examples.template_partial import TemplatePartial
from examples.delimiters import Delimiters
from examples.unicode_output import UnicodeOutput
from examples.unicode_input import UnicodeInput
from examples.nested_context import NestedContext
from pystache import Renderer
from pystache.tests.common import EXAMPLES_DIR
from pystache.tests.common import AssertStringMixin


class TestView(unittest.TestCase, AssertStringMixin):

    def _assert(self, obj, expected):
        renderer = Renderer()
        actual = renderer.render(obj)
        self.assertString(actual, expected)

    def test_comments(self):
        self._assert(Comments(), u"<h1>A Comedy of Errors</h1>")

    def test_double_section(self):
        self._assert(DoubleSection(), u"* first\n* second\n* third")

    def test_unicode_output(self):
        renderer = Renderer()
        actual = renderer.render(UnicodeOutput())
        self.assertString(actual, u'<p>Name: Henri Poincaré</p>')

    def test_unicode_input(self):
        renderer = Renderer()
        actual = renderer.render(UnicodeInput())
        self.assertString(actual, u'abcdé')

    def test_escaping(self):
        self._assert(Escaped(), u"<h1>Bear &gt; Shark</h1>")

    def test_literal(self):
        renderer = Renderer()
        actual = renderer.render(Unescaped())
        self.assertString(actual, u"<h1>Bear > Shark</h1>")

    def test_template_partial(self):
        renderer = Renderer(search_dirs=EXAMPLES_DIR)
        actual = renderer.render(TemplatePartial(renderer=renderer))

        self.assertString(actual, u"""<h1>Welcome</h1>
Again, Welcome!""")

    def test_template_partial_extension(self):
        renderer = Renderer(search_dirs=EXAMPLES_DIR, file_extension='txt')

        view = TemplatePartial(renderer=renderer)

        actual = renderer.render(view)
        self.assertString(actual, u"""Welcome
-------

## Again, Welcome! ##""")

    def test_delimiters(self):
        renderer = Renderer()
        actual = renderer.render(Delimiters())
        self.assertString(actual, u"""\
* It worked the first time.
* And it worked the second time.
* Then, surprisingly, it worked the third time.
""")

    def test_nested_context(self):
        renderer = Renderer()
        actual = renderer.render(NestedContext(renderer))
        self.assertString(actual, u"one and foo and two")

    def test_nested_context_is_available_in_view(self):
        renderer = Renderer()

        view = NestedContext(renderer)
        view.template = '{{#herp}}{{#derp}}{{nested_context_in_view}}{{/derp}}{{/herp}}'

        actual = renderer.render(view)
        self.assertString(actual, u'it works!')

    def test_partial_in_partial_has_access_to_grand_parent_context(self):
        renderer = Renderer(search_dirs=EXAMPLES_DIR)

        view = TemplatePartial(renderer=renderer)
        view.template = '''{{>partial_in_partial}}'''

        actual = renderer.render(view, {'prop': 'derp'})
        self.assertEqual(actual, 'Hi derp!')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_loader
# encoding: utf-8

"""
Unit tests of loader.py.

"""

import os
import sys
import unittest

from pystache.tests.common import AssertStringMixin, DATA_DIR, SetupDefaults
from pystache import defaults
from pystache.loader import Loader


# We use the same directory as the locator tests for now.
LOADER_DATA_DIR = os.path.join(DATA_DIR, 'locator')


class LoaderTests(unittest.TestCase, AssertStringMixin, SetupDefaults):

    def setUp(self):
        self.setup_defaults()

    def tearDown(self):
        self.teardown_defaults()

    def test_init__extension(self):
        loader = Loader(extension='foo')
        self.assertEqual(loader.extension, 'foo')

    def test_init__extension__default(self):
        # Test the default value.
        loader = Loader()
        self.assertEqual(loader.extension, 'mustache')

    def test_init__file_encoding(self):
        loader = Loader(file_encoding='bar')
        self.assertEqual(loader.file_encoding, 'bar')

    def test_init__file_encoding__default(self):
        file_encoding = defaults.FILE_ENCODING
        try:
            defaults.FILE_ENCODING = 'foo'
            loader = Loader()
            self.assertEqual(loader.file_encoding, 'foo')
        finally:
            defaults.FILE_ENCODING = file_encoding

    def test_init__to_unicode(self):
        to_unicode = lambda x: x
        loader = Loader(to_unicode=to_unicode)
        self.assertEqual(loader.to_unicode, to_unicode)

    def test_init__to_unicode__default(self):
        loader = Loader()
        self.assertRaises(TypeError, loader.to_unicode, u"abc")

        decode_errors = defaults.DECODE_ERRORS
        string_encoding = defaults.STRING_ENCODING

        nonascii = u'abcdé'.encode('utf-8')

        loader = Loader()
        self.assertRaises(UnicodeDecodeError, loader.to_unicode, nonascii)

        defaults.DECODE_ERRORS = 'ignore'
        loader = Loader()
        self.assertString(loader.to_unicode(nonascii), u'abcd')

        defaults.STRING_ENCODING = 'utf-8'
        loader = Loader()
        self.assertString(loader.to_unicode(nonascii), u'abcdé')


    def _get_path(self, filename):
        return os.path.join(DATA_DIR, filename)

    def test_unicode__basic__input_str(self):
        """
        Test unicode(): default arguments with str input.

        """
        loader = Loader()
        actual = loader.unicode("foo")

        self.assertString(actual, u"foo")

    def test_unicode__basic__input_unicode(self):
        """
        Test unicode(): default arguments with unicode input.

        """
        loader = Loader()
        actual = loader.unicode(u"foo")

        self.assertString(actual, u"foo")

    def test_unicode__basic__input_unicode_subclass(self):
        """
        Test unicode(): default arguments with unicode-subclass input.

        """
        class UnicodeSubclass(unicode):
            pass

        s = UnicodeSubclass(u"foo")

        loader = Loader()
        actual = loader.unicode(s)

        self.assertString(actual, u"foo")

    def test_unicode__to_unicode__attribute(self):
        """
        Test unicode(): encoding attribute.

        """
        loader = Loader()

        non_ascii = u'abcdé'.encode('utf-8')
        self.assertRaises(UnicodeDecodeError, loader.unicode, non_ascii)

        def to_unicode(s, encoding=None):
            if encoding is None:
                encoding = 'utf-8'
            return unicode(s, encoding)

        loader.to_unicode = to_unicode
        self.assertString(loader.unicode(non_ascii), u"abcdé")

    def test_unicode__encoding_argument(self):
        """
        Test unicode(): encoding argument.

        """
        loader = Loader()

        non_ascii = u'abcdé'.encode('utf-8')

        self.assertRaises(UnicodeDecodeError, loader.unicode, non_ascii)

        actual = loader.unicode(non_ascii, encoding='utf-8')
        self.assertString(actual, u'abcdé')

    # TODO: check the read() unit tests.
    def test_read(self):
        """
        Test read().

        """
        loader = Loader()
        path = self._get_path('ascii.mustache')
        actual = loader.read(path)
        self.assertString(actual, u'ascii: abc')

    def test_read__file_encoding__attribute(self):
        """
        Test read(): file_encoding attribute respected.

        """
        loader = Loader()
        path = self._get_path('non_ascii.mustache')

        self.assertRaises(UnicodeDecodeError, loader.read, path)

        loader.file_encoding = 'utf-8'
        actual = loader.read(path)
        self.assertString(actual, u'non-ascii: é')

    def test_read__encoding__argument(self):
        """
        Test read(): encoding argument respected.

        """
        loader = Loader()
        path = self._get_path('non_ascii.mustache')

        self.assertRaises(UnicodeDecodeError, loader.read, path)

        actual = loader.read(path, encoding='utf-8')
        self.assertString(actual, u'non-ascii: é')

    def test_read__to_unicode__attribute(self):
        """
        Test read(): to_unicode attribute respected.

        """
        loader = Loader()
        path = self._get_path('non_ascii.mustache')

        self.assertRaises(UnicodeDecodeError, loader.read, path)

        #loader.decode_errors = 'ignore'
        #actual = loader.read(path)
        #self.assertString(actual, u'non-ascii: ')

    def test_load_file(self):
        loader = Loader(search_dirs=[DATA_DIR, LOADER_DATA_DIR])
        template = loader.load_file('template.txt')
        self.assertEqual(template, 'Test template file\n')

    def test_load_name(self):
        loader = Loader(search_dirs=[DATA_DIR, LOADER_DATA_DIR],
                        extension='txt')
        template = loader.load_name('template')
        self.assertEqual(template, 'Test template file\n')


########NEW FILE########
__FILENAME__ = test_locator
# encoding: utf-8

"""
Unit tests for locator.py.

"""

from datetime import datetime
import os
import sys
import unittest

# TODO: remove this alias.
from pystache.common import TemplateNotFoundError
from pystache.loader import Loader as Reader
from pystache.locator import Locator

from pystache.tests.common import DATA_DIR, EXAMPLES_DIR, AssertExceptionMixin
from pystache.tests.data.views import SayHello


LOCATOR_DATA_DIR = os.path.join(DATA_DIR, 'locator')


class LocatorTests(unittest.TestCase, AssertExceptionMixin):

    def _locator(self):
        return Locator(search_dirs=DATA_DIR)

    def test_init__extension(self):
        # Test the default value.
        locator = Locator()
        self.assertEqual(locator.template_extension, 'mustache')

        locator = Locator(extension='txt')
        self.assertEqual(locator.template_extension, 'txt')

        locator = Locator(extension=False)
        self.assertTrue(locator.template_extension is False)

    def _assert_paths(self, actual, expected):
        """
        Assert that two paths are the same.

        """
        self.assertEqual(actual, expected)

    def test_get_object_directory(self):
        locator = Locator()

        obj = SayHello()
        actual = locator.get_object_directory(obj)

        self._assert_paths(actual, DATA_DIR)

    def test_get_object_directory__not_hasattr_module(self):
        locator = Locator()

        # Previously, we used a genuine object -- a datetime instance --
        # because datetime instances did not have the __module__ attribute
        # in CPython.  See, for example--
        #
        #   http://bugs.python.org/issue15223
        #
        # However, since datetime instances do have the __module__ attribute
        # in PyPy, we needed to switch to something else once we added
        # support for PyPi.  This was so that our test runs would pass
        # in all systems.
        obj = "abc"
        self.assertFalse(hasattr(obj, '__module__'))
        self.assertEqual(locator.get_object_directory(obj), None)

        self.assertFalse(hasattr(None, '__module__'))
        self.assertEqual(locator.get_object_directory(None), None)

    def test_make_file_name(self):
        locator = Locator()

        locator.template_extension = 'bar'
        self.assertEqual(locator.make_file_name('foo'), 'foo.bar')

        locator.template_extension = False
        self.assertEqual(locator.make_file_name('foo'), 'foo')

        locator.template_extension = ''
        self.assertEqual(locator.make_file_name('foo'), 'foo.')

    def test_make_file_name__template_extension_argument(self):
        locator = Locator()

        self.assertEqual(locator.make_file_name('foo', template_extension='bar'), 'foo.bar')

    def test_find_file(self):
        locator = Locator()
        path = locator.find_file('template.txt', [LOCATOR_DATA_DIR])

        expected_path = os.path.join(LOCATOR_DATA_DIR, 'template.txt')
        self.assertEqual(path, expected_path)

    def test_find_name(self):
        locator = Locator()
        path = locator.find_name(search_dirs=[EXAMPLES_DIR], template_name='simple')

        self.assertEqual(os.path.basename(path), 'simple.mustache')

    def test_find_name__using_list_of_paths(self):
        locator = Locator()
        path = locator.find_name(search_dirs=[EXAMPLES_DIR, 'doesnt_exist'], template_name='simple')

        self.assertTrue(path)

    def test_find_name__precedence(self):
        """
        Test the order in which find_name() searches directories.

        """
        locator = Locator()

        dir1 = DATA_DIR
        dir2 = LOCATOR_DATA_DIR

        self.assertTrue(locator.find_name(search_dirs=[dir1], template_name='duplicate'))
        self.assertTrue(locator.find_name(search_dirs=[dir2], template_name='duplicate'))

        path = locator.find_name(search_dirs=[dir2, dir1], template_name='duplicate')
        dirpath = os.path.dirname(path)
        dirname = os.path.split(dirpath)[-1]

        self.assertEqual(dirname, 'locator')

    def test_find_name__non_existent_template_fails(self):
        locator = Locator()

        self.assertException(TemplateNotFoundError, "File 'doesnt_exist.mustache' not found in dirs: []",
                             locator.find_name, search_dirs=[], template_name='doesnt_exist')

    def test_find_object(self):
        locator = Locator()

        obj = SayHello()

        actual = locator.find_object(search_dirs=[], obj=obj, file_name='sample_view.mustache')
        expected = os.path.join(DATA_DIR, 'sample_view.mustache')

        self._assert_paths(actual, expected)

    def test_find_object__none_file_name(self):
        locator = Locator()

        obj = SayHello()

        actual = locator.find_object(search_dirs=[], obj=obj)
        expected = os.path.join(DATA_DIR, 'say_hello.mustache')

        self.assertEqual(actual, expected)

    def test_find_object__none_object_directory(self):
        locator = Locator()

        obj = None
        self.assertEqual(None, locator.get_object_directory(obj))

        actual = locator.find_object(search_dirs=[DATA_DIR], obj=obj, file_name='say_hello.mustache')
        expected = os.path.join(DATA_DIR, 'say_hello.mustache')

        self.assertEqual(actual, expected)

    def test_make_template_name(self):
        """
        Test make_template_name().

        """
        locator = Locator()

        class FooBar(object):
            pass
        foo = FooBar()

        self.assertEqual(locator.make_template_name(foo), 'foo_bar')

########NEW FILE########
__FILENAME__ = test_parser
# coding: utf-8

"""
Unit tests of parser.py.

"""

import unittest

from pystache.defaults import DELIMITERS
from pystache.parser import _compile_template_re as make_re


class RegularExpressionTestCase(unittest.TestCase):

    """Tests the regular expression returned by _compile_template_re()."""

    def test_re(self):
        """
        Test getting a key from a dictionary.

        """
        re = make_re(DELIMITERS)
        match = re.search("b  {{test}}")

        self.assertEqual(match.start(), 1)


########NEW FILE########
__FILENAME__ = test_pystache
# encoding: utf-8

import unittest

import pystache
from pystache import defaults
from pystache import renderer
from pystache.tests.common import html_escape


class PystacheTests(unittest.TestCase):


    def setUp(self):
        self.original_escape = defaults.TAG_ESCAPE
        defaults.TAG_ESCAPE = html_escape

    def tearDown(self):
        defaults.TAG_ESCAPE = self.original_escape

    def _assert_rendered(self, expected, template, context):
        actual = pystache.render(template, context)
        self.assertEqual(actual, expected)

    def test_basic(self):
        ret = pystache.render("Hi {{thing}}!", { 'thing': 'world' })
        self.assertEqual(ret, "Hi world!")

    def test_kwargs(self):
        ret = pystache.render("Hi {{thing}}!", thing='world')
        self.assertEqual(ret, "Hi world!")

    def test_less_basic(self):
        template = "It's a nice day for {{beverage}}, right {{person}}?"
        context = { 'beverage': 'soda', 'person': 'Bob' }
        self._assert_rendered("It's a nice day for soda, right Bob?", template, context)

    def test_even_less_basic(self):
        template = "I think {{name}} wants a {{thing}}, right {{name}}?"
        context = { 'name': 'Jon', 'thing': 'racecar' }
        self._assert_rendered("I think Jon wants a racecar, right Jon?", template, context)

    def test_ignores_misses(self):
        template = "I think {{name}} wants a {{thing}}, right {{name}}?"
        context = { 'name': 'Jon' }
        self._assert_rendered("I think Jon wants a , right Jon?", template, context)

    def test_render_zero(self):
        template = 'My value is {{value}}.'
        context = { 'value': 0 }
        self._assert_rendered('My value is 0.', template, context)

    def test_comments(self):
        template = "What {{! the }} what?"
        actual = pystache.render(template)
        self.assertEqual("What  what?", actual)

    def test_false_sections_are_hidden(self):
        template = "Ready {{#set}}set {{/set}}go!"
        context = { 'set': False }
        self._assert_rendered("Ready go!", template, context)

    def test_true_sections_are_shown(self):
        template = "Ready {{#set}}set{{/set}} go!"
        context = { 'set': True }
        self._assert_rendered("Ready set go!", template, context)

    non_strings_expected = """(123 & [&#x27;something&#x27;])(chris & 0.9)"""

    def test_non_strings(self):
        template = "{{#stats}}({{key}} & {{value}}){{/stats}}"
        stats = []
        stats.append({'key': 123, 'value': ['something']})
        stats.append({'key': u"chris", 'value': 0.900})
        context = { 'stats': stats }
        self._assert_rendered(self.non_strings_expected, template, context)

    def test_unicode(self):
        template = 'Name: {{name}}; Age: {{age}}'
        context = {'name': u'Henri Poincaré', 'age': 156 }
        self._assert_rendered(u'Name: Henri Poincaré; Age: 156', template, context)

    def test_sections(self):
        template = """<ul>{{#users}}<li>{{name}}</li>{{/users}}</ul>"""

        context = { 'users': [ {'name': 'Chris'}, {'name': 'Tom'}, {'name': 'PJ'} ] }
        expected = """<ul><li>Chris</li><li>Tom</li><li>PJ</li></ul>"""
        self._assert_rendered(expected, template, context)

    def test_implicit_iterator(self):
        template = """<ul>{{#users}}<li>{{.}}</li>{{/users}}</ul>"""
        context = { 'users': [ 'Chris', 'Tom','PJ' ] }
        expected = """<ul><li>Chris</li><li>Tom</li><li>PJ</li></ul>"""
        self._assert_rendered(expected, template, context)

    # The spec says that sections should not alter surrounding whitespace.
    def test_surrounding_whitepace_not_altered(self):
        template = "first{{#spacing}} second {{/spacing}}third"
        context = {"spacing": True}
        self._assert_rendered("first second third", template, context)

    def test__section__non_false_value(self):
        """
        Test when a section value is a (non-list) "non-false value".

        From mustache(5):

            When the value [of a section key] is non-false but not a list, it
            will be used as the context for a single rendering of the block.

        """
        template = """{{#person}}Hi {{name}}{{/person}}"""
        context = {"person": {"name": "Jon"}}
        self._assert_rendered("Hi Jon", template, context)

    def test_later_list_section_with_escapable_character(self):
        """
        This is a simple test case intended to cover issue #53.

        The test case failed with markupsafe enabled, as follows:

        AssertionError: Markup(u'foo &lt;') != 'foo <'

        """
        template = """{{#s1}}foo{{/s1}} {{#s2}}<{{/s2}}"""
        context = {'s1': True, 's2': [True]}
        self._assert_rendered("foo <", template, context)

########NEW FILE########
__FILENAME__ = test_renderengine
# coding: utf-8

"""
Unit tests of renderengine.py.

"""

import sys
import unittest

from pystache.context import ContextStack, KeyNotFoundError
from pystache import defaults
from pystache.parser import ParsingError
from pystache.renderer import Renderer
from pystache.renderengine import context_get, RenderEngine
from pystache.tests.common import AssertStringMixin, AssertExceptionMixin, Attachable


def _get_unicode_char():
    if sys.version_info < (3, ):
        return 'u'
    return ''

_UNICODE_CHAR = _get_unicode_char()


def mock_literal(s):
    """
    For use as the literal keyword argument to the RenderEngine constructor.

    Arguments:

      s: a byte string or unicode string.

    """
    if isinstance(s, unicode):
        # Strip off unicode super classes, if present.
        u = unicode(s)
    else:
        u = unicode(s, encoding='ascii')

    # We apply upper() to make sure we are actually using our custom
    # function in the tests
    return u.upper()



class RenderEngineTestCase(unittest.TestCase):

    """Test the RenderEngine class."""

    def test_init(self):
        """
        Test that __init__() stores all of the arguments correctly.

        """
        # In real-life, these arguments would be functions
        engine = RenderEngine(resolve_partial="foo", literal="literal",
                              escape="escape", to_str="str")

        self.assertEqual(engine.escape, "escape")
        self.assertEqual(engine.literal, "literal")
        self.assertEqual(engine.resolve_partial, "foo")
        self.assertEqual(engine.to_str, "str")


class RenderTests(unittest.TestCase, AssertStringMixin, AssertExceptionMixin):

    """
    Tests RenderEngine.render().

    Explicit spec-test-like tests best go in this class since the
    RenderEngine class contains all parsing logic.  This way, the unit tests
    will be more focused and fail "closer to the code".

    """

    def _engine(self):
        """
        Create and return a default RenderEngine for testing.

        """
        renderer = Renderer(string_encoding='utf-8', missing_tags='strict')
        engine = renderer._make_render_engine()

        return engine

    def _assert_render(self, expected, template, *context, **kwargs):
        """
        Test rendering the given template using the given context.

        """
        partials = kwargs.get('partials')
        engine = kwargs.get('engine', self._engine())

        if partials is not None:
            engine.resolve_partial = lambda key: unicode(partials[key])

        context = ContextStack(*context)

        # RenderEngine.render() only accepts unicode template strings.
        actual = engine.render(unicode(template), context)

        self.assertString(actual=actual, expected=expected)

    def test_render(self):
        self._assert_render(u'Hi Mom', 'Hi {{person}}', {'person': 'Mom'})

    def test__resolve_partial(self):
        """
        Test that render() uses the load_template attribute.

        """
        engine = self._engine()
        partials = {'partial': u"{{person}}"}
        engine.resolve_partial = lambda key: partials[key]

        self._assert_render(u'Hi Mom', 'Hi {{>partial}}', {'person': 'Mom'}, engine=engine)

    def test__literal(self):
        """
        Test that render() uses the literal attribute.

        """
        engine = self._engine()
        engine.literal = lambda s: s.upper()

        self._assert_render(u'BAR', '{{{foo}}}', {'foo': 'bar'}, engine=engine)

    def test_literal__sigil(self):
        template = "<h1>{{& thing}}</h1>"
        context = {'thing': 'Bear > Giraffe'}

        expected = u"<h1>Bear > Giraffe</h1>"

        self._assert_render(expected, template, context)

    def test__escape(self):
        """
        Test that render() uses the escape attribute.

        """
        engine = self._engine()
        engine.escape = lambda s: "**" + s

        self._assert_render(u'**bar', '{{foo}}', {'foo': 'bar'}, engine=engine)

    def test__escape_does_not_call_literal(self):
        """
        Test that render() does not call literal before or after calling escape.

        """
        engine = self._engine()
        engine.literal = lambda s: s.upper()  # a test version
        engine.escape = lambda s: "**" + s

        template = 'literal: {{{foo}}} escaped: {{foo}}'
        context = {'foo': 'bar'}

        self._assert_render(u'literal: BAR escaped: **bar', template, context, engine=engine)

    def test__escape_preserves_unicode_subclasses(self):
        """
        Test that render() preserves unicode subclasses when passing to escape.

        This is useful, for example, if one wants to respect whether a
        variable value is markupsafe.Markup when escaping.

        """
        class MyUnicode(unicode):
            pass

        def escape(s):
            if type(s) is MyUnicode:
                return "**" + s
            else:
                return s + "**"

        engine = self._engine()
        engine.escape = escape

        template = '{{foo1}} {{foo2}}'
        context = {'foo1': MyUnicode('bar'), 'foo2': 'bar'}

        self._assert_render(u'**bar bar**', template, context, engine=engine)

    # Custom to_str for testing purposes.
    def _to_str(self, val):
        if not val:
            return ''
        else:
            return str(val)

    def test_to_str(self):
        """Test the to_str attribute."""
        engine = self._engine()
        template = '{{value}}'
        context = {'value': None}

        self._assert_render(u'None', template, context, engine=engine)
        engine.to_str = self._to_str
        self._assert_render(u'', template, context, engine=engine)

    def test_to_str__lambda(self):
        """Test the to_str attribute for a lambda."""
        engine = self._engine()
        template = '{{value}}'
        context = {'value': lambda: None}

        self._assert_render(u'None', template, context, engine=engine)
        engine.to_str = self._to_str
        self._assert_render(u'', template, context, engine=engine)

    def test_to_str__section_list(self):
        """Test the to_str attribute for a section list."""
        engine = self._engine()
        template = '{{#list}}{{.}}{{/list}}'
        context = {'list': [None, None]}

        self._assert_render(u'NoneNone', template, context, engine=engine)
        engine.to_str = self._to_str
        self._assert_render(u'', template, context, engine=engine)

    def test_to_str__section_lambda(self):
        # TODO: add a test for a "method with an arity of 1".
        pass

    def test__non_basestring__literal_and_escaped(self):
        """
        Test a context value that is not a basestring instance.

        """
        engine = self._engine()
        engine.escape = mock_literal
        engine.literal = mock_literal

        self.assertRaises(TypeError, engine.literal, 100)

        template = '{{text}} {{int}} {{{int}}}'
        context = {'int': 100, 'text': 'foo'}

        self._assert_render(u'FOO 100 100', template, context, engine=engine)

    def test_tag__output_not_interpolated(self):
        """
        Context values should not be treated as templates (issue #44).

        """
        template = '{{template}}: {{planet}}'
        context = {'template': '{{planet}}', 'planet': 'Earth'}
        self._assert_render(u'{{planet}}: Earth', template, context)

    def test_tag__output_not_interpolated__section(self):
        """
        Context values should not be treated as templates (issue #44).

        """
        template = '{{test}}'
        context = {'test': '{{#hello}}'}
        self._assert_render(u'{{#hello}}', template, context)

    ## Test interpolation with "falsey" values
    #
    # In these test cases, we test the part of the spec that says that
    # "data should be coerced into a string (and escaped, if appropriate)
    # before interpolation."  We test this for data that is "falsey."

    def test_interpolation__falsey__zero(self):
        template = '{{.}}'
        context = 0
        self._assert_render(u'0', template, context)

    def test_interpolation__falsey__none(self):
        template = '{{.}}'
        context = None
        self._assert_render(u'None', template, context)

    def test_interpolation__falsey__zero(self):
        template = '{{.}}'
        context = False
        self._assert_render(u'False', template, context)

    # Built-in types:
    #
    #   Confirm that we not treat instances of built-in types as objects,
    #   for example by calling a method on a built-in type instance when it
    #   has a method whose name matches the current key.
    #
    #   Each test case puts an instance of a built-in type on top of the
    #   context stack before interpolating a tag whose key matches an
    #   attribute (method or property) of the instance.
    #

    def _assert_builtin_attr(self, item, attr_name, expected_attr):
        self.assertTrue(hasattr(item, attr_name))
        actual = getattr(item, attr_name)
        if callable(actual):
            actual = actual()
        self.assertEqual(actual, expected_attr)

    def _assert_builtin_type(self, item, attr_name, expected_attr, expected_template):
        self._assert_builtin_attr(item, attr_name, expected_attr)

        template = '{{#section}}{{%s}}{{/section}}' % attr_name
        context = {'section': item, attr_name: expected_template}
        self._assert_render(expected_template, template, context)

    def test_interpolation__built_in_type__string(self):
        """
        Check tag interpolation with a built-in type: string.

        """
        self._assert_builtin_type('abc', 'upper', 'ABC', u'xyz')

    def test_interpolation__built_in_type__integer(self):
        """
        Check tag interpolation with a built-in type: integer.

        """
        # Since public attributes weren't added to integers until Python 2.6
        # (for example the "real" attribute of the numeric type hierarchy)--
        #
        #   http://docs.python.org/library/numbers.html
        #
        # we need to resort to built-in attributes (double-underscored) on
        # the integer type.
        self._assert_builtin_type(15, '__neg__', -15, u'999')

    def test_interpolation__built_in_type__list(self):
        """
        Check tag interpolation with a built-in type: list.

        """
        item = [[1, 2, 3]]
        attr_name = 'pop'
        # Make a copy to prevent changes to item[0].
        self._assert_builtin_attr(list(item[0]), attr_name, 3)

        template = '{{#section}}{{%s}}{{/section}}' % attr_name
        context = {'section': item, attr_name: 7}
        self._assert_render(u'7', template, context)

    # This test is also important for testing 2to3.
    def test_interpolation__nonascii_nonunicode(self):
        """
        Test a tag whose value is a non-ascii, non-unicode string.

        """
        template = '{{nonascii}}'
        context = {'nonascii': u'abcdé'.encode('utf-8')}
        self._assert_render(u'abcdé', template, context)

    def test_implicit_iterator__literal(self):
        """
        Test an implicit iterator in a literal tag.

        """
        template = """{{#test}}{{{.}}}{{/test}}"""
        context = {'test': ['<', '>']}

        self._assert_render(u'<>', template, context)

    def test_implicit_iterator__escaped(self):
        """
        Test an implicit iterator in a normal tag.

        """
        template = """{{#test}}{{.}}{{/test}}"""
        context = {'test': ['<', '>']}

        self._assert_render(u'&lt;&gt;', template, context)

    def test_literal__in_section(self):
        """
        Check that literals work in sections.

        """
        template = '{{#test}}1 {{{less_than}}} 2{{/test}}'
        context = {'test': {'less_than': '<'}}

        self._assert_render(u'1 < 2', template, context)

    def test_literal__in_partial(self):
        """
        Check that literals work in partials.

        """
        template = '{{>partial}}'
        partials = {'partial': '1 {{{less_than}}} 2'}
        context = {'less_than': '<'}

        self._assert_render(u'1 < 2', template, context, partials=partials)

    def test_partial(self):
        partials = {'partial': "{{person}}"}
        self._assert_render(u'Hi Mom', 'Hi {{>partial}}', {'person': 'Mom'}, partials=partials)

    def test_partial__context_values(self):
        """
        Test that escape and literal work on context values in partials.

        """
        engine = self._engine()

        template = '{{>partial}}'
        partials = {'partial': 'unescaped: {{{foo}}} escaped: {{foo}}'}
        context = {'foo': '<'}

        self._assert_render(u'unescaped: < escaped: &lt;', template, context, engine=engine, partials=partials)

    ## Test cases related specifically to lambdas.

    # This test is also important for testing 2to3.
    def test_section__nonascii_nonunicode(self):
        """
        Test a section whose value is a non-ascii, non-unicode string.

        """
        template = '{{#nonascii}}{{.}}{{/nonascii}}'
        context = {'nonascii': u'abcdé'.encode('utf-8')}
        self._assert_render(u'abcdé', template, context)

    # This test is also important for testing 2to3.
    def test_lambda__returning_nonascii_nonunicode(self):
        """
        Test a lambda tag value returning a non-ascii, non-unicode string.

        """
        template = '{{lambda}}'
        context = {'lambda': lambda: u'abcdé'.encode('utf-8')}
        self._assert_render(u'abcdé', template, context)

    ## Test cases related specifically to sections.

    def test_section__end_tag_with_no_start_tag(self):
        """
        Check what happens if there is an end tag with no start tag.

        """
        template = '{{/section}}'
        try:
            self._assert_render(None, template)
        except ParsingError, err:
            self.assertEqual(str(err), "Section end tag mismatch: section != None")

    def test_section__end_tag_mismatch(self):
        """
        Check what happens if the end tag doesn't match.

        """
        template = '{{#section_start}}{{/section_end}}'
        try:
            self._assert_render(None, template)
        except ParsingError, err:
            self.assertEqual(str(err), "Section end tag mismatch: section_end != section_start")

    def test_section__context_values(self):
        """
        Test that escape and literal work on context values in sections.

        """
        engine = self._engine()

        template = '{{#test}}unescaped: {{{foo}}} escaped: {{foo}}{{/test}}'
        context = {'test': {'foo': '<'}}

        self._assert_render(u'unescaped: < escaped: &lt;', template, context, engine=engine)

    def test_section__context_precedence(self):
        """
        Check that items higher in the context stack take precedence.

        """
        template = '{{entree}} : {{#vegetarian}}{{entree}}{{/vegetarian}}'
        context = {'entree': 'chicken', 'vegetarian': {'entree': 'beans and rice'}}
        self._assert_render(u'chicken : beans and rice', template, context)

    def test_section__list_referencing_outer_context(self):
        """
        Check that list items can access the parent context.

        For sections whose value is a list, check that items in the list
        have access to the values inherited from the parent context
        when rendering.

        """
        context = {
            "greeting": "Hi",
            "list": [{"name": "Al"}, {"name": "Bob"}],
        }

        template = "{{#list}}{{greeting}} {{name}}, {{/list}}"

        self._assert_render(u"Hi Al, Hi Bob, ", template, context)

    def test_section__output_not_interpolated(self):
        """
        Check that rendered section output is not interpolated.

        """
        template = '{{#section}}{{template}}{{/section}}: {{planet}}'
        context = {'section': True, 'template': '{{planet}}', 'planet': 'Earth'}
        self._assert_render(u'{{planet}}: Earth', template, context)

    # TODO: have this test case added to the spec.
    def test_section__string_values_not_lists(self):
        """
        Check that string section values are not interpreted as lists.

        """
        template = '{{#section}}foo{{/section}}'
        context = {'section': '123'}
        # If strings were interpreted as lists, this would give "foofoofoo".
        self._assert_render(u'foo', template, context)

    def test_section__nested_truthy(self):
        """
        Check that "nested truthy" sections get rendered.

        Test case for issue #24: https://github.com/defunkt/pystache/issues/24

        This test is copied from the spec.  We explicitly include it to
        prevent regressions for those who don't pull down the spec tests.

        """
        template = '| A {{#bool}}B {{#bool}}C{{/bool}} D{{/bool}} E |'
        context = {'bool': True}
        self._assert_render(u'| A B C D E |', template, context)

    def test_section__nested_with_same_keys(self):
        """
        Check a doubly-nested section with the same context key.

        Test case for issue #36: https://github.com/defunkt/pystache/issues/36

        """
        # Start with an easier, working case.
        template = '{{#x}}{{#z}}{{y}}{{/z}}{{/x}}'
        context = {'x': {'z': {'y': 1}}}
        self._assert_render(u'1', template, context)

        template = '{{#x}}{{#x}}{{y}}{{/x}}{{/x}}'
        context = {'x': {'x': {'y': 1}}}
        self._assert_render(u'1', template, context)

    def test_section__lambda(self):
        template = '{{#test}}Mom{{/test}}'
        context = {'test': (lambda text: 'Hi %s' % text)}
        self._assert_render(u'Hi Mom', template, context)

    # This test is also important for testing 2to3.
    def test_section__lambda__returning_nonascii_nonunicode(self):
        """
        Test a lambda section value returning a non-ascii, non-unicode string.

        """
        template = '{{#lambda}}{{/lambda}}'
        context = {'lambda': lambda text: u'abcdé'.encode('utf-8')}
        self._assert_render(u'abcdé', template, context)

    def test_section__lambda__returning_nonstring(self):
        """
        Test a lambda section value returning a non-string.

        """
        template = '{{#lambda}}foo{{/lambda}}'
        context = {'lambda': lambda text: len(text)}
        self._assert_render(u'3', template, context)

    def test_section__iterable(self):
        """
        Check that objects supporting iteration (aside from dicts) behave like lists.

        """
        template = '{{#iterable}}{{.}}{{/iterable}}'

        context = {'iterable': (i for i in range(3))}  # type 'generator'
        self._assert_render(u'012', template, context)

        context = {'iterable': xrange(4)}  # type 'xrange'
        self._assert_render(u'0123', template, context)

        d = {'foo': 0, 'bar': 0}
        # We don't know what order of keys we'll be given, but from the
        # Python documentation:
        #  "If items(), keys(), values(), iteritems(), iterkeys(), and
        #   itervalues() are called with no intervening modifications to
        #   the dictionary, the lists will directly correspond."
        expected = u''.join(d.keys())
        context = {'iterable': d.iterkeys()}  # type 'dictionary-keyiterator'
        self._assert_render(expected, template, context)

    def test_section__lambda__tag_in_output(self):
        """
        Check that callable output is treated as a template string (issue #46).

        The spec says--

            When used as the data value for a Section tag, the lambda MUST
            be treatable as an arity 1 function, and invoked as such (passing
            a String containing the unprocessed section contents).  The
            returned value MUST be rendered against the current delimiters,
            then interpolated in place of the section.

        """
        template = '{{#test}}Hi {{person}}{{/test}}'
        context = {'person': 'Mom', 'test': (lambda text: text + " :)")}
        self._assert_render(u'Hi Mom :)', template, context)

    def test_section__lambda__list(self):
        """
        Check that lists of lambdas are processed correctly for sections.

        This test case is equivalent to a test submitted to the Mustache spec here:

          https://github.com/mustache/spec/pull/47 .

        """
        template = '<{{#lambdas}}foo{{/lambdas}}>'
        context = {'foo': 'bar',
                   'lambdas': [lambda text: "~{{%s}}~" % text,
                               lambda text: "#{{%s}}#" % text]}

        self._assert_render(u'<~bar~#bar#>', template, context)

    def test_section__lambda__mixed_list(self):
        """
        Test a mixed list of lambdas and non-lambdas as a section value.

        This test case is equivalent to a test submitted to the Mustache spec here:

          https://github.com/mustache/spec/pull/47 .

        """
        template = '<{{#lambdas}}foo{{/lambdas}}>'
        context = {'foo': 'bar',
                   'lambdas': [lambda text: "~{{%s}}~" % text, 1]}

        self._assert_render(u'<~bar~foo>', template, context)

    def test_section__lambda__not_on_context_stack(self):
        """
        Check that section lambdas are not pushed onto the context stack.

        Even though the sections spec says that section data values should be
        pushed onto the context stack prior to rendering, this does not apply
        to lambdas.  Lambdas obey their own special case.

        This test case is equivalent to a test submitted to the Mustache spec here:

          https://github.com/mustache/spec/pull/47 .

        """
        context = {'foo': 'bar', 'lambda': (lambda text: "{{.}}")}
        template = '{{#foo}}{{#lambda}}blah{{/lambda}}{{/foo}}'
        self._assert_render(u'bar', template, context)

    def test_section__lambda__no_reinterpolation(self):
        """
        Check that section lambda return values are not re-interpolated.

        This test is a sanity check that the rendered lambda return value
        is not re-interpolated as could be construed by reading the
        section part of the Mustache spec.

        This test case is equivalent to a test submitted to the Mustache spec here:

          https://github.com/mustache/spec/pull/47 .

        """
        template = '{{#planet}}{{#lambda}}dot{{/lambda}}{{/planet}}'
        context = {'planet': 'Earth', 'dot': '~{{.}}~', 'lambda': (lambda text: "#{{%s}}#" % text)}
        self._assert_render(u'#~{{.}}~#', template, context)

    def test_comment__multiline(self):
        """
        Check that multiline comments are permitted.

        """
        self._assert_render(u'foobar', 'foo{{! baz }}bar')
        self._assert_render(u'foobar', 'foo{{! \nbaz }}bar')

    def test_custom_delimiters__sections(self):
        """
        Check that custom delimiters can be used to start a section.

        Test case for issue #20: https://github.com/defunkt/pystache/issues/20

        """
        template = '{{=[[ ]]=}}[[#foo]]bar[[/foo]]'
        context = {'foo': True}
        self._assert_render(u'bar', template, context)

    def test_custom_delimiters__not_retroactive(self):
        """
        Check that changing custom delimiters back is not "retroactive."

        Test case for issue #35: https://github.com/defunkt/pystache/issues/35

        """
        expected = u' {{foo}} '
        self._assert_render(expected, '{{=$ $=}} {{foo}} ')
        self._assert_render(expected, '{{=$ $=}} {{foo}} $={{ }}=$')  # was yielding u'  '.

    def test_dot_notation(self):
        """
        Test simple dot notation cases.

        Check that we can use dot notation when the variable is a dict,
        user-defined object, or combination of both.

        """
        template = 'Hello, {{person.name}}. I see you are {{person.details.age}}.'
        person = Attachable(name='Biggles', details={'age': 42})
        context = {'person': person}
        self._assert_render(u'Hello, Biggles. I see you are 42.', template, context)

    def test_dot_notation__multiple_levels(self):
        """
        Test dot notation with multiple levels.

        """
        template = """Hello, Mr. {{person.name.lastname}}.
        I see you're back from {{person.travels.last.country.city}}."""
        expected = u"""Hello, Mr. Pither.
        I see you're back from Cornwall."""
        context = {'person': {'name': {'firstname': 'unknown', 'lastname': 'Pither'},
                            'travels': {'last': {'country': {'city': 'Cornwall'}}},
                            'details': {'public': 'likes cycling'}}}
        self._assert_render(expected, template, context)

        # It should also work with user-defined objects
        context = {'person': Attachable(name={'firstname': 'unknown', 'lastname': 'Pither'},
                                        travels=Attachable(last=Attachable(country=Attachable(city='Cornwall'))),
                                        details=Attachable())}
        self._assert_render(expected, template, context)

    def test_dot_notation__missing_part_terminates_search(self):
        """
        Test that dotted name resolution terminates on a later part not found.

        Check that if a later dotted name part is not found in the result from
        the former resolution, then name resolution terminates rather than
        starting the search over with the next element of the context stack.
        From the spec (interpolation section)--

          5) If any name parts were retained in step 1, each should be resolved
          against a context stack containing only the result from the former
          resolution.  If any part fails resolution, the result should be considered
          falsey, and should interpolate as the empty string.

        This test case is equivalent to the test case in the following pull
        request:

          https://github.com/mustache/spec/pull/48

        """
        context = {'a': {'b': 'A.B'}, 'c': {'a': 'A'} }

        template = '{{a.b}}'
        self._assert_render(u'A.B', template, context)

        template = '{{#c}}{{a}}{{/c}}'
        self._assert_render(u'A', template, context)

        template = '{{#c}}{{a.b}}{{/c}}'
        self.assertException(KeyNotFoundError, "Key %(unicode)s'a.b' not found: missing %(unicode)s'b'" %
                             {'unicode': _UNICODE_CHAR},
                             self._assert_render, 'A.B :: (A :: )', template, context)

########NEW FILE########
__FILENAME__ = test_renderer
# coding: utf-8

"""
Unit tests of template.py.

"""

import codecs
import os
import sys
import unittest

from examples.simple import Simple
from pystache import Renderer
from pystache import TemplateSpec
from pystache.common import TemplateNotFoundError
from pystache.context import ContextStack, KeyNotFoundError
from pystache.loader import Loader

from pystache.tests.common import get_data_path, AssertStringMixin, AssertExceptionMixin
from pystache.tests.data.views import SayHello


def _make_renderer():
    """
    Return a default Renderer instance for testing purposes.

    """
    renderer = Renderer(string_encoding='ascii', file_encoding='ascii')
    return renderer


def mock_unicode(b, encoding=None):
    if encoding is None:
        encoding = 'ascii'
    u = unicode(b, encoding=encoding)
    return u.upper()


class RendererInitTestCase(unittest.TestCase):

    """
    Tests the Renderer.__init__() method.

    """

    def test_partials__default(self):
        """
        Test the default value.

        """
        renderer = Renderer()
        self.assertTrue(renderer.partials is None)

    def test_partials(self):
        """
        Test that the attribute is set correctly.

        """
        renderer = Renderer(partials={'foo': 'bar'})
        self.assertEqual(renderer.partials, {'foo': 'bar'})

    def test_escape__default(self):
        escape = Renderer().escape

        self.assertEqual(escape(">"), "&gt;")
        self.assertEqual(escape('"'), "&quot;")
        # Single quotes are escaped only in Python 3.2 and later.
        if sys.version_info < (3, 2):
            expected = "'"
        else:
            expected = '&#x27;'
        self.assertEqual(escape("'"), expected)

    def test_escape(self):
        escape = lambda s: "**" + s
        renderer = Renderer(escape=escape)
        self.assertEqual(renderer.escape("bar"), "**bar")

    def test_decode_errors__default(self):
        """
        Check the default value.

        """
        renderer = Renderer()
        self.assertEqual(renderer.decode_errors, 'strict')

    def test_decode_errors(self):
        """
        Check that the constructor sets the attribute correctly.

        """
        renderer = Renderer(decode_errors="foo")
        self.assertEqual(renderer.decode_errors, "foo")

    def test_file_encoding__default(self):
        """
        Check the file_encoding default.

        """
        renderer = Renderer()
        self.assertEqual(renderer.file_encoding, renderer.string_encoding)

    def test_file_encoding(self):
        """
        Check that the file_encoding attribute is set correctly.

        """
        renderer = Renderer(file_encoding='foo')
        self.assertEqual(renderer.file_encoding, 'foo')

    def test_file_extension__default(self):
        """
        Check the file_extension default.

        """
        renderer = Renderer()
        self.assertEqual(renderer.file_extension, 'mustache')

    def test_file_extension(self):
        """
        Check that the file_encoding attribute is set correctly.

        """
        renderer = Renderer(file_extension='foo')
        self.assertEqual(renderer.file_extension, 'foo')

    def test_missing_tags(self):
        """
        Check that the missing_tags attribute is set correctly.

        """
        renderer = Renderer(missing_tags='foo')
        self.assertEqual(renderer.missing_tags, 'foo')

    def test_missing_tags__default(self):
        """
        Check the missing_tags default.

        """
        renderer = Renderer()
        self.assertEqual(renderer.missing_tags, 'ignore')

    def test_search_dirs__default(self):
        """
        Check the search_dirs default.

        """
        renderer = Renderer()
        self.assertEqual(renderer.search_dirs, [os.curdir])

    def test_search_dirs__string(self):
        """
        Check that the search_dirs attribute is set correctly when a string.

        """
        renderer = Renderer(search_dirs='foo')
        self.assertEqual(renderer.search_dirs, ['foo'])

    def test_search_dirs__list(self):
        """
        Check that the search_dirs attribute is set correctly when a list.

        """
        renderer = Renderer(search_dirs=['foo'])
        self.assertEqual(renderer.search_dirs, ['foo'])

    def test_string_encoding__default(self):
        """
        Check the default value.

        """
        renderer = Renderer()
        self.assertEqual(renderer.string_encoding, sys.getdefaultencoding())

    def test_string_encoding(self):
        """
        Check that the constructor sets the attribute correctly.

        """
        renderer = Renderer(string_encoding="foo")
        self.assertEqual(renderer.string_encoding, "foo")


class RendererTests(unittest.TestCase, AssertStringMixin):

    """Test the Renderer class."""

    def _renderer(self):
        return Renderer()

    ## Test Renderer.unicode().

    def test_unicode__string_encoding(self):
        """
        Test that the string_encoding attribute is respected.

        """
        renderer = self._renderer()
        b = u"é".encode('utf-8')

        renderer.string_encoding = "ascii"
        self.assertRaises(UnicodeDecodeError, renderer.unicode, b)

        renderer.string_encoding = "utf-8"
        self.assertEqual(renderer.unicode(b), u"é")

    def test_unicode__decode_errors(self):
        """
        Test that the decode_errors attribute is respected.

        """
        renderer = self._renderer()
        renderer.string_encoding = "ascii"
        b = u"déf".encode('utf-8')

        renderer.decode_errors = "ignore"
        self.assertEqual(renderer.unicode(b), "df")

        renderer.decode_errors = "replace"
        # U+FFFD is the official Unicode replacement character.
        self.assertEqual(renderer.unicode(b), u'd\ufffd\ufffdf')

    ## Test the _make_loader() method.

    def test__make_loader__return_type(self):
        """
        Test that _make_loader() returns a Loader.

        """
        renderer = self._renderer()
        loader = renderer._make_loader()

        self.assertEqual(type(loader), Loader)

    def test__make_loader__attributes(self):
        """
        Test that _make_loader() sets all attributes correctly..

        """
        unicode_ = lambda x: x

        renderer = self._renderer()
        renderer.file_encoding = 'enc'
        renderer.file_extension = 'ext'
        renderer.unicode = unicode_

        loader = renderer._make_loader()

        self.assertEqual(loader.extension, 'ext')
        self.assertEqual(loader.file_encoding, 'enc')
        self.assertEqual(loader.to_unicode, unicode_)

    ## Test the render() method.

    def test_render__return_type(self):
        """
        Check that render() returns a string of type unicode.

        """
        renderer = self._renderer()
        rendered = renderer.render('foo')
        self.assertEqual(type(rendered), unicode)

    def test_render__unicode(self):
        renderer = self._renderer()
        actual = renderer.render(u'foo')
        self.assertEqual(actual, u'foo')

    def test_render__str(self):
        renderer = self._renderer()
        actual = renderer.render('foo')
        self.assertEqual(actual, 'foo')

    def test_render__non_ascii_character(self):
        renderer = self._renderer()
        actual = renderer.render(u'Poincaré')
        self.assertEqual(actual, u'Poincaré')

    def test_render__context(self):
        """
        Test render(): passing a context.

        """
        renderer = self._renderer()
        self.assertEqual(renderer.render('Hi {{person}}', {'person': 'Mom'}), 'Hi Mom')

    def test_render__context_and_kwargs(self):
        """
        Test render(): passing a context and **kwargs.

        """
        renderer = self._renderer()
        template = 'Hi {{person1}} and {{person2}}'
        self.assertEqual(renderer.render(template, {'person1': 'Mom'}, person2='Dad'), 'Hi Mom and Dad')

    def test_render__kwargs_and_no_context(self):
        """
        Test render(): passing **kwargs and no context.

        """
        renderer = self._renderer()
        self.assertEqual(renderer.render('Hi {{person}}', person='Mom'), 'Hi Mom')

    def test_render__context_and_kwargs__precedence(self):
        """
        Test render(): **kwargs takes precedence over context.

        """
        renderer = self._renderer()
        self.assertEqual(renderer.render('Hi {{person}}', {'person': 'Mom'}, person='Dad'), 'Hi Dad')

    def test_render__kwargs_does_not_modify_context(self):
        """
        Test render(): passing **kwargs does not modify the passed context.

        """
        context = {}
        renderer = self._renderer()
        renderer.render('Hi {{person}}', context=context, foo="bar")
        self.assertEqual(context, {})

    def test_render__nonascii_template(self):
        """
        Test passing a non-unicode template with non-ascii characters.

        """
        renderer = _make_renderer()
        template = u"déf".encode("utf-8")

        # Check that decode_errors and string_encoding are both respected.
        renderer.decode_errors = 'ignore'
        renderer.string_encoding = 'ascii'
        self.assertEqual(renderer.render(template), "df")

        renderer.string_encoding = 'utf_8'
        self.assertEqual(renderer.render(template), u"déf")

    def test_make_resolve_partial(self):
        """
        Test the _make_resolve_partial() method.

        """
        renderer = Renderer()
        renderer.partials = {'foo': 'bar'}
        resolve_partial = renderer._make_resolve_partial()

        actual = resolve_partial('foo')
        self.assertEqual(actual, 'bar')
        self.assertEqual(type(actual), unicode, "RenderEngine requires that "
            "resolve_partial return unicode strings.")

    def test_make_resolve_partial__unicode(self):
        """
        Test _make_resolve_partial(): that resolve_partial doesn't "double-decode" Unicode.

        """
        renderer = Renderer()

        renderer.partials = {'partial': 'foo'}
        resolve_partial = renderer._make_resolve_partial()
        self.assertEqual(resolve_partial("partial"), "foo")

        # Now with a value that is already unicode.
        renderer.partials = {'partial': u'foo'}
        resolve_partial = renderer._make_resolve_partial()
        # If the next line failed, we would get the following error:
        #   TypeError: decoding Unicode is not supported
        self.assertEqual(resolve_partial("partial"), "foo")

    def test_render_name(self):
        """Test the render_name() method."""
        data_dir = get_data_path()
        renderer = Renderer(search_dirs=data_dir)
        actual = renderer.render_name("say_hello", to='foo')
        self.assertString(actual, u"Hello, foo")

    def test_render_path(self):
        """
        Test the render_path() method.

        """
        renderer = Renderer()
        path = get_data_path('say_hello.mustache')
        actual = renderer.render_path(path, to='foo')
        self.assertEqual(actual, "Hello, foo")

    def test_render__object(self):
        """
        Test rendering an object instance.

        """
        renderer = Renderer()

        say_hello = SayHello()
        actual = renderer.render(say_hello)
        self.assertEqual('Hello, World', actual)

        actual = renderer.render(say_hello, to='Mars')
        self.assertEqual('Hello, Mars', actual)

    def test_render__template_spec(self):
        """
        Test rendering a TemplateSpec instance.

        """
        renderer = Renderer()

        class Spec(TemplateSpec):
            template = "hello, {{to}}"
            to = 'world'

        spec = Spec()
        actual = renderer.render(spec)
        self.assertString(actual, u'hello, world')

    def test_render__view(self):
        """
        Test rendering a View instance.

        """
        renderer = Renderer()

        view = Simple()
        actual = renderer.render(view)
        self.assertEqual('Hi pizza!', actual)

    def test_custom_string_coercion_via_assignment(self):
        """
        Test that string coercion can be customized via attribute assignment.

        """
        renderer = self._renderer()
        def to_str(val):
            if not val:
                return ''
            else:
                return str(val)

        self.assertEqual(renderer.render('{{value}}', value=None), 'None')
        renderer.str_coerce = to_str
        self.assertEqual(renderer.render('{{value}}', value=None), '')

    def test_custom_string_coercion_via_subclassing(self):
        """
        Test that string coercion can be customized via subclassing.

        """
        class MyRenderer(Renderer):
            def str_coerce(self, val):
                if not val:
                    return ''
                else:
                    return str(val)
        renderer1 = Renderer()
        renderer2 = MyRenderer()

        self.assertEqual(renderer1.render('{{value}}', value=None), 'None')
        self.assertEqual(renderer2.render('{{value}}', value=None), '')


# By testing that Renderer.render() constructs the right RenderEngine,
# we no longer need to exercise all rendering code paths through
# the Renderer.  It suffices to test rendering paths through the
# RenderEngine for the same amount of code coverage.
class Renderer_MakeRenderEngineTests(unittest.TestCase, AssertStringMixin, AssertExceptionMixin):

    """
    Check the RenderEngine returned by Renderer._make_render_engine().

    """

    def _make_renderer(self):
        """
        Return a default Renderer instance for testing purposes.

        """
        return _make_renderer()

    ## Test the engine's resolve_partial attribute.

    def test__resolve_partial__returns_unicode(self):
        """
        Check that resolve_partial returns unicode (and not a subclass).

        """
        class MyUnicode(unicode):
            pass

        renderer = Renderer()
        renderer.string_encoding = 'ascii'
        renderer.partials = {'str': 'foo', 'subclass': MyUnicode('abc')}

        engine = renderer._make_render_engine()

        actual = engine.resolve_partial('str')
        self.assertEqual(actual, "foo")
        self.assertEqual(type(actual), unicode)

        # Check that unicode subclasses are not preserved.
        actual = engine.resolve_partial('subclass')
        self.assertEqual(actual, "abc")
        self.assertEqual(type(actual), unicode)

    def test__resolve_partial__not_found(self):
        """
        Check that resolve_partial returns the empty string when a template is not found.

        """
        renderer = Renderer()

        engine = renderer._make_render_engine()
        resolve_partial = engine.resolve_partial

        self.assertString(resolve_partial('foo'), u'')

    def test__resolve_partial__not_found__missing_tags_strict(self):
        """
        Check that resolve_partial provides a nice message when a template is not found.

        """
        renderer = Renderer()
        renderer.missing_tags = 'strict'

        engine = renderer._make_render_engine()
        resolve_partial = engine.resolve_partial

        self.assertException(TemplateNotFoundError, "File 'foo.mustache' not found in dirs: ['.']",
                             resolve_partial, "foo")

    def test__resolve_partial__not_found__partials_dict(self):
        """
        Check that resolve_partial returns the empty string when a template is not found.

        """
        renderer = Renderer()
        renderer.partials = {}

        engine = renderer._make_render_engine()
        resolve_partial = engine.resolve_partial

        self.assertString(resolve_partial('foo'), u'')

    def test__resolve_partial__not_found__partials_dict__missing_tags_strict(self):
        """
        Check that resolve_partial provides a nice message when a template is not found.

        """
        renderer = Renderer()
        renderer.missing_tags = 'strict'
        renderer.partials = {}

        engine = renderer._make_render_engine()
        resolve_partial = engine.resolve_partial

       # Include dict directly since str(dict) is different in Python 2 and 3:
       #   <type 'dict'> versus <class 'dict'>, respectively.
        self.assertException(TemplateNotFoundError, "Name 'foo' not found in partials: %s" % dict,
                             resolve_partial, "foo")

    ## Test the engine's literal attribute.

    def test__literal__uses_renderer_unicode(self):
        """
        Test that literal uses the renderer's unicode function.

        """
        renderer = self._make_renderer()
        renderer.unicode = mock_unicode

        engine = renderer._make_render_engine()
        literal = engine.literal

        b = u"foo".encode("ascii")
        self.assertEqual(literal(b), "FOO")

    def test__literal__handles_unicode(self):
        """
        Test that literal doesn't try to "double decode" unicode.

        """
        renderer = Renderer()
        renderer.string_encoding = 'ascii'

        engine = renderer._make_render_engine()
        literal = engine.literal

        self.assertEqual(literal(u"foo"), "foo")

    def test__literal__returns_unicode(self):
        """
        Test that literal returns unicode (and not a subclass).

        """
        renderer = Renderer()
        renderer.string_encoding = 'ascii'

        engine = renderer._make_render_engine()
        literal = engine.literal

        self.assertEqual(type(literal("foo")), unicode)

        class MyUnicode(unicode):
            pass

        s = MyUnicode("abc")

        self.assertEqual(type(s), MyUnicode)
        self.assertTrue(isinstance(s, unicode))
        self.assertEqual(type(literal(s)), unicode)

    ## Test the engine's escape attribute.

    def test__escape__uses_renderer_escape(self):
        """
        Test that escape uses the renderer's escape function.

        """
        renderer = Renderer()
        renderer.escape = lambda s: "**" + s

        engine = renderer._make_render_engine()
        escape = engine.escape

        self.assertEqual(escape("foo"), "**foo")

    def test__escape__uses_renderer_unicode(self):
        """
        Test that escape uses the renderer's unicode function.

        """
        renderer = Renderer()
        renderer.unicode = mock_unicode

        engine = renderer._make_render_engine()
        escape = engine.escape

        b = u"foo".encode('ascii')
        self.assertEqual(escape(b), "FOO")

    def test__escape__has_access_to_original_unicode_subclass(self):
        """
        Test that escape receives strings with the unicode subclass intact.

        """
        renderer = Renderer()
        renderer.escape = lambda s: unicode(type(s).__name__)

        engine = renderer._make_render_engine()
        escape = engine.escape

        class MyUnicode(unicode):
            pass

        self.assertEqual(escape(u"foo".encode('ascii')), unicode.__name__)
        self.assertEqual(escape(u"foo"), unicode.__name__)
        self.assertEqual(escape(MyUnicode("foo")), MyUnicode.__name__)

    def test__escape__returns_unicode(self):
        """
        Test that literal returns unicode (and not a subclass).

        """
        renderer = Renderer()
        renderer.string_encoding = 'ascii'

        engine = renderer._make_render_engine()
        escape = engine.escape

        self.assertEqual(type(escape("foo")), unicode)

        # Check that literal doesn't preserve unicode subclasses.
        class MyUnicode(unicode):
            pass

        s = MyUnicode("abc")

        self.assertEqual(type(s), MyUnicode)
        self.assertTrue(isinstance(s, unicode))
        self.assertEqual(type(escape(s)), unicode)

    ## Test the missing_tags attribute.

    def test__missing_tags__unknown_value(self):
        """
        Check missing_tags attribute: setting an unknown value.

        """
        renderer = Renderer()
        renderer.missing_tags = 'foo'

        self.assertException(Exception, "Unsupported 'missing_tags' value: 'foo'",
                             renderer._make_render_engine)

    ## Test the engine's resolve_context attribute.

    def test__resolve_context(self):
        """
        Check resolve_context(): default arguments.

        """
        renderer = Renderer()

        engine = renderer._make_render_engine()

        stack = ContextStack({'foo': 'bar'})

        self.assertEqual('bar', engine.resolve_context(stack, 'foo'))
        self.assertString(u'', engine.resolve_context(stack, 'missing'))

    def test__resolve_context__missing_tags_strict(self):
        """
        Check resolve_context(): missing_tags 'strict'.

        """
        renderer = Renderer()
        renderer.missing_tags = 'strict'

        engine = renderer._make_render_engine()

        stack = ContextStack({'foo': 'bar'})

        self.assertEqual('bar', engine.resolve_context(stack, 'foo'))
        self.assertException(KeyNotFoundError, "Key 'missing' not found: first part",
                             engine.resolve_context, stack, 'missing')

########NEW FILE########
__FILENAME__ = test_simple
import unittest

import pystache
from pystache import Renderer
from examples.nested_context import NestedContext
from examples.complex import Complex
from examples.lambdas import Lambdas
from examples.template_partial import TemplatePartial
from examples.simple import Simple

from pystache.tests.common import EXAMPLES_DIR
from pystache.tests.common import AssertStringMixin


class TestSimple(unittest.TestCase, AssertStringMixin):

    def test_nested_context(self):
        renderer = Renderer()
        view = NestedContext(renderer)
        view.template = '{{#foo}}{{thing1}} and {{thing2}} and {{outer_thing}}{{/foo}}{{^foo}}Not foo!{{/foo}}'

        actual = renderer.render(view)
        self.assertString(actual, u"one and foo and two")

    def test_looping_and_negation_context(self):
        template = '{{#item}}{{header}}: {{name}} {{/item}}{{^item}} Shouldnt see me{{/item}}'
        context = Complex()

        renderer = Renderer()
        actual = renderer.render(template, context)
        self.assertEqual(actual, "Colors: red Colors: green Colors: blue ")

    def test_empty_context(self):
        template = '{{#empty_list}}Shouldnt see me {{/empty_list}}{{^empty_list}}Should see me{{/empty_list}}'
        self.assertEqual(pystache.Renderer().render(template), "Should see me")

    def test_callables(self):
        view = Lambdas()
        view.template = '{{#replace_foo_with_bar}}foo != bar. oh, it does!{{/replace_foo_with_bar}}'

        renderer = Renderer()
        actual = renderer.render(view)
        self.assertString(actual, u'bar != bar. oh, it does!')

    def test_rendering_partial(self):
        renderer = Renderer(search_dirs=EXAMPLES_DIR)

        view = TemplatePartial(renderer=renderer)
        view.template = '{{>inner_partial}}'

        actual = renderer.render(view)
        self.assertString(actual, u'Again, Welcome!')

        view.template = '{{#looping}}{{>inner_partial}} {{/looping}}'
        actual = renderer.render(view)
        self.assertString(actual, u"Again, Welcome! Again, Welcome! Again, Welcome! ")

    def test_non_existent_value_renders_blank(self):
        view = Simple()
        template = '{{not_set}} {{blank}}'
        self.assertEqual(pystache.Renderer().render(template), ' ')


    def test_template_partial_extension(self):
        """
        Side note:

        From the spec--

            Partial tags SHOULD be treated as standalone when appropriate.

        In particular, this means that trailing newlines should be removed.

        """
        renderer = Renderer(search_dirs=EXAMPLES_DIR, file_extension='txt')

        view = TemplatePartial(renderer=renderer)

        actual = renderer.render(view)
        self.assertString(actual, u"""Welcome
-------

## Again, Welcome! ##""")

########NEW FILE########
__FILENAME__ = test_specloader
# coding: utf-8

"""
Unit tests for template_spec.py.

"""

import os.path
import sys
import unittest

import examples
from examples.simple import Simple
from examples.complex import Complex
from examples.lambdas import Lambdas
from examples.inverted import Inverted, InvertedLists
from pystache import Renderer
from pystache import TemplateSpec
from pystache.common import TemplateNotFoundError
from pystache.locator import Locator
from pystache.loader import Loader
from pystache.specloader import SpecLoader
from pystache.tests.common import DATA_DIR, EXAMPLES_DIR
from pystache.tests.common import AssertIsMixin, AssertStringMixin
from pystache.tests.data.views import SampleView
from pystache.tests.data.views import NonAscii


class Thing(object):
    pass


class AssertPathsMixin:

    """A unittest.TestCase mixin to check path equality."""

    def assertPaths(self, actual, expected):
        self.assertEqual(actual, expected)


class ViewTestCase(unittest.TestCase, AssertStringMixin):

    def test_template_rel_directory(self):
        """
        Test that View.template_rel_directory is respected.

        """
        class Tagless(TemplateSpec):
            pass

        view = Tagless()
        renderer = Renderer()

        self.assertRaises(TemplateNotFoundError, renderer.render, view)

        # TODO: change this test to remove the following brittle line.
        view.template_rel_directory = "examples"
        actual = renderer.render(view)
        self.assertEqual(actual, "No tags...")

    def test_template_path_for_partials(self):
        """
        Test that View.template_rel_path is respected for partials.

        """
        spec = TemplateSpec()
        spec.template = "Partial: {{>tagless}}"

        renderer1 = Renderer()
        renderer2 = Renderer(search_dirs=EXAMPLES_DIR)

        actual = renderer1.render(spec)
        self.assertString(actual, u"Partial: ")

        actual = renderer2.render(spec)
        self.assertEqual(actual, "Partial: No tags...")

    def test_basic_method_calls(self):
        renderer = Renderer()
        actual = renderer.render(Simple())

        self.assertString(actual, u"Hi pizza!")

    def test_non_callable_attributes(self):
        view = Simple()
        view.thing = 'Chris'

        renderer = Renderer()
        actual = renderer.render(view)
        self.assertEqual(actual, "Hi Chris!")

    def test_complex(self):
        renderer = Renderer()
        actual = renderer.render(Complex())
        self.assertString(actual, u"""\
<h1>Colors</h1>
<ul>
<li><strong>red</strong></li>
<li><a href="#Green">green</a></li>
<li><a href="#Blue">blue</a></li>
</ul>""")

    def test_higher_order_replace(self):
        renderer = Renderer()
        actual = renderer.render(Lambdas())
        self.assertEqual(actual, 'bar != bar. oh, it does!')

    def test_higher_order_rot13(self):
        view = Lambdas()
        view.template = '{{#rot13}}abcdefghijklm{{/rot13}}'

        renderer = Renderer()
        actual = renderer.render(view)
        self.assertString(actual, u'nopqrstuvwxyz')

    def test_higher_order_lambda(self):
        view = Lambdas()
        view.template = '{{#sort}}zyxwvutsrqponmlkjihgfedcba{{/sort}}'

        renderer = Renderer()
        actual = renderer.render(view)
        self.assertString(actual, u'abcdefghijklmnopqrstuvwxyz')

    def test_partials_with_lambda(self):
        view = Lambdas()
        view.template = '{{>partial_with_lambda}}'

        renderer = Renderer(search_dirs=EXAMPLES_DIR)
        actual = renderer.render(view)
        self.assertEqual(actual, u'nopqrstuvwxyz')

    def test_hierarchical_partials_with_lambdas(self):
        view = Lambdas()
        view.template = '{{>partial_with_partial_and_lambda}}'

        renderer = Renderer(search_dirs=EXAMPLES_DIR)
        actual = renderer.render(view)
        self.assertString(actual, u'nopqrstuvwxyznopqrstuvwxyz')

    def test_inverted(self):
        renderer = Renderer()
        actual = renderer.render(Inverted())
        self.assertString(actual, u"""one, two, three, empty list""")

    def test_accessing_properties_on_parent_object_from_child_objects(self):
        parent = Thing()
        parent.this = 'derp'
        parent.children = [Thing()]
        view = Simple()
        view.template = "{{#parent}}{{#children}}{{this}}{{/children}}{{/parent}}"

        renderer = Renderer()
        actual = renderer.render(view, {'parent': parent})

        self.assertString(actual, u'derp')

    def test_inverted_lists(self):
        renderer = Renderer()
        actual = renderer.render(InvertedLists())
        self.assertString(actual, u"""one, two, three, empty list""")


def _make_specloader():
    """
    Return a default SpecLoader instance for testing purposes.

    """
    # Python 2 and 3 have different default encodings.  Thus, to have
    # consistent test results across both versions, we need to specify
    # the string and file encodings explicitly rather than relying on
    # the defaults.
    def to_unicode(s, encoding=None):
        """
        Raises a TypeError exception if the given string is already unicode.

        """
        if encoding is None:
            encoding = 'ascii'
        return unicode(s, encoding, 'strict')

    loader = Loader(file_encoding='ascii', to_unicode=to_unicode)
    return SpecLoader(loader=loader)


class SpecLoaderTests(unittest.TestCase, AssertIsMixin, AssertStringMixin,
                      AssertPathsMixin):

    """
    Tests template_spec.SpecLoader.

    """

    def _make_specloader(self):
        return _make_specloader()

    def test_init__defaults(self):
        spec_loader = SpecLoader()

        # Check the loader attribute.
        loader = spec_loader.loader
        self.assertEqual(loader.extension, 'mustache')
        self.assertEqual(loader.file_encoding, sys.getdefaultencoding())
        # TODO: finish testing the other Loader attributes.
        to_unicode = loader.to_unicode

    def test_init__loader(self):
        loader = Loader()
        custom = SpecLoader(loader=loader)

        self.assertIs(custom.loader, loader)

    # TODO: rename to something like _assert_load().
    def _assert_template(self, loader, custom, expected):
        self.assertString(loader.load(custom), expected)

    def test_load__template__type_str(self):
        """
        Test the template attribute: str string.

        """
        custom = TemplateSpec()
        custom.template = "abc"

        spec_loader = self._make_specloader()
        self._assert_template(spec_loader, custom, u"abc")

    def test_load__template__type_unicode(self):
        """
        Test the template attribute: unicode string.

        """
        custom = TemplateSpec()
        custom.template = u"abc"

        spec_loader = self._make_specloader()
        self._assert_template(spec_loader, custom, u"abc")

    def test_load__template__unicode_non_ascii(self):
        """
        Test the template attribute: non-ascii unicode string.

        """
        custom = TemplateSpec()
        custom.template = u"é"

        spec_loader = self._make_specloader()
        self._assert_template(spec_loader, custom, u"é")

    def test_load__template__with_template_encoding(self):
        """
        Test the template attribute: with template encoding attribute.

        """
        custom = TemplateSpec()
        custom.template = u'é'.encode('utf-8')

        spec_loader = self._make_specloader()

        self.assertRaises(UnicodeDecodeError, self._assert_template, spec_loader, custom, u'é')

        custom.template_encoding = 'utf-8'
        self._assert_template(spec_loader, custom, u'é')

    # TODO: make this test complete.
    def test_load__template__correct_loader(self):
        """
        Test that reader.unicode() is called correctly.

        This test tests that the correct reader is called with the correct
        arguments.  This is a catch-all test to supplement the other
        test cases.  It tests SpecLoader.load() independent of reader.unicode()
        being implemented correctly (and tested).

        """
        class MockLoader(Loader):

            def __init__(self):
                self.s = None
                self.encoding = None

            # Overrides the existing method.
            def unicode(self, s, encoding=None):
                self.s = s
                self.encoding = encoding
                return u"foo"

        loader = MockLoader()
        custom_loader = SpecLoader()
        custom_loader.loader = loader

        view = TemplateSpec()
        view.template = "template-foo"
        view.template_encoding = "encoding-foo"

        # Check that our unicode() above was called.
        self._assert_template(custom_loader, view, u'foo')
        self.assertEqual(loader.s, "template-foo")
        self.assertEqual(loader.encoding, "encoding-foo")

    def test_find__template_path(self):
        """Test _find() with TemplateSpec.template_path."""
        loader = self._make_specloader()
        custom = TemplateSpec()
        custom.template_path = "path/foo"
        actual = loader._find(custom)
        self.assertPaths(actual, "path/foo")


# TODO: migrate these tests into the SpecLoaderTests class.
# TODO: rename the get_template() tests to test load().
# TODO: condense, reorganize, and rename the tests so that it is
#   clear whether we have full test coverage (e.g. organized by
#   TemplateSpec attributes or something).
class TemplateSpecTests(unittest.TestCase, AssertPathsMixin):

    def _make_loader(self):
        return _make_specloader()

    def _assert_template_location(self, view, expected):
        loader = self._make_loader()
        actual = loader._find_relative(view)
        self.assertEqual(actual, expected)

    def test_find_relative(self):
        """
        Test _find_relative(): default behavior (no attributes set).

        """
        view = SampleView()
        self._assert_template_location(view, (None, 'sample_view.mustache'))

    def test_find_relative__template_rel_path__file_name_only(self):
        """
        Test _find_relative(): template_rel_path attribute.

        """
        view = SampleView()
        view.template_rel_path = 'template.txt'
        self._assert_template_location(view, ('', 'template.txt'))

    def test_find_relative__template_rel_path__file_name_with_directory(self):
        """
        Test _find_relative(): template_rel_path attribute.

        """
        view = SampleView()
        view.template_rel_path = 'foo/bar/template.txt'
        self._assert_template_location(view, ('foo/bar', 'template.txt'))

    def test_find_relative__template_rel_directory(self):
        """
        Test _find_relative(): template_rel_directory attribute.

        """
        view = SampleView()
        view.template_rel_directory = 'foo'

        self._assert_template_location(view, ('foo', 'sample_view.mustache'))

    def test_find_relative__template_name(self):
        """
        Test _find_relative(): template_name attribute.

        """
        view = SampleView()
        view.template_name = 'new_name'
        self._assert_template_location(view, (None, 'new_name.mustache'))

    def test_find_relative__template_extension(self):
        """
        Test _find_relative(): template_extension attribute.

        """
        view = SampleView()
        view.template_extension = 'txt'
        self._assert_template_location(view, (None, 'sample_view.txt'))

    def test_find__with_directory(self):
        """
        Test _find() with a view that has a directory specified.

        """
        loader = self._make_loader()

        view = SampleView()
        view.template_rel_path = os.path.join('foo', 'bar.txt')
        self.assertTrue(loader._find_relative(view)[0] is not None)

        actual = loader._find(view)
        expected = os.path.join(DATA_DIR, 'foo', 'bar.txt')

        self.assertPaths(actual, expected)

    def test_find__without_directory(self):
        """
        Test _find() with a view that doesn't have a directory specified.

        """
        loader = self._make_loader()

        view = SampleView()
        self.assertTrue(loader._find_relative(view)[0] is None)

        actual = loader._find(view)
        expected = os.path.join(DATA_DIR, 'sample_view.mustache')

        self.assertPaths(actual, expected)

    def _assert_get_template(self, custom, expected):
        loader = self._make_loader()
        actual = loader.load(custom)

        self.assertEqual(type(actual), unicode)
        self.assertEqual(actual, expected)

    def test_get_template(self):
        """
        Test get_template(): default behavior (no attributes set).

        """
        view = SampleView()

        self._assert_get_template(view, u"ascii: abc")

    def test_get_template__template_encoding(self):
        """
        Test get_template(): template_encoding attribute.

        """
        view = NonAscii()

        self.assertRaises(UnicodeDecodeError, self._assert_get_template, view, 'foo')

        view.template_encoding = 'utf-8'
        self._assert_get_template(view, u"non-ascii: é")

########NEW FILE########
__FILENAME__ = test_pystache
#!/usr/bin/env python
# coding: utf-8

"""
Runs project tests.

This script is a substitute for running--

    python -m pystache.commands.test

It is useful in Python 2.4 because the -m flag does not accept subpackages
in Python 2.4:

  http://docs.python.org/using/cmdline.html#cmdoption-m

"""

import sys

from pystache.commands import test
from pystache.tests.main import FROM_SOURCE_OPTION


def main(sys_argv=sys.argv):
    sys.argv.insert(1, FROM_SOURCE_OPTION)
    test.main()


if __name__=='__main__':
    main()

########NEW FILE########
