__FILENAME__ = AAA
import os
import sys

try:  # ST3
    from .Lib.sublime_lib.path import get_package_name

    PLUGIN_NAME = get_package_name()
    path = os.path.dirname(__file__)
    libpath = os.path.join(path, "Lib")
except ValueError:  # ST2
    # For some reason the import does only work when RELOADING the plugin, not
    # when ST is loading it initially.

    # from lib.sublime_lib.path import get_package_name, get_package_path
    path = os.path.normpath(os.getcwdu())
    PLUGIN_NAME = os.path.basename(path)
    libpath = os.path.join(path, "Lib")


def add(path):
    if not path in sys.path:
        sys.path.append(path)
        print("[%s] Added %s to sys.path." % (PLUGIN_NAME, path))

# Make sublime_lib (and more) available for all packages.
add(libpath)
# Differentiate between Python 2 and Python 3 packages (split by folder)
add(os.path.join(libpath, "_py%d" % sys.version_info[0]))

########NEW FILE########
__FILENAME__ = build_sys_dev
import sublime_plugin

from sublime_lib.path import root_at_packages, get_package_name

PLUGIN_NAME = get_package_name()

BUILD_SYSTEM_SYNTAX = "Packages/%s/Syntax Definitions/Sublime Text Build System.tmLanguage" % PLUGIN_NAME


# Adding "2" to avoid name clash with shipped command.
class NewBuildSystem2Command(sublime_plugin.WindowCommand):
    def run(self):
        v = self.window.new_file()
        v.settings().set('default_dir', root_at_packages('User'))
        v.set_syntax_file(BUILD_SYSTEM_SYNTAX)
        v.set_name('untitled.sublime-build')

        template = """{\n\t"cmd": ["${0:make}"]\n}"""
        v.run_command("insert_snippet", {"contents": template})

########NEW FILE########
__FILENAME__ = commands_file_dev
import sublime_plugin

from sublime_lib.path import root_at_packages, get_package_name


tpl = """[
    { "caption": "${1:My Caption for the Comand Palette}", "command": "${2:my_command}" }$0
]"""

PLUGIN_NAME = get_package_name()

SYNTAX_DEF = "Packages/%s/Syntax Definitions/Sublime Commands.tmLanguage" % PLUGIN_NAME


class NewCommandsFileCommand(sublime_plugin.WindowCommand):
    def run(self):
        v = self.window.new_file()
        v.run_command('insert_snippet', {'contents': tpl})
        v.settings().set('default_dir', root_at_packages('User'))
        v.set_syntax_file(SYNTAX_DEF)

########NEW FILE########
__FILENAME__ = completions_dev
import sublime_plugin

from sublime_lib.path import root_at_packages, get_package_name

PLUGIN_NAME = get_package_name()

COMPLETIONS_SYNTAX_DEF = "Packages/%s/Syntax Definitions/Sublime Completions.tmLanguage" % PLUGIN_NAME
TPL = """{
    "scope": "source.${1:off}",

    "completions": [
        { "trigger": "${2:some_trigger}", "contents": "${3:Hint: Use f, ff and fff plus Tab inside here.}" }$0
    ]
}"""


class NewCompletionsCommand(sublime_plugin.WindowCommand):
    def run(self):
        v = self.window.new_file()
        v.run_command('insert_snippet', {"contents": TPL})
        v.settings().set('syntax', COMPLETIONS_SYNTAX_DEF)
        v.settings().set('default_dir', root_at_packages('User'))

########NEW FILE########
__FILENAME__ = dumpers
import datetime

import json
import yaml
import plistlib

from sublime_lib.view import OutputPanel


class DumperProto(object):
    """Prototype class for data dumpers of different types.

        Classes derived from this class (and in this file) will be appended
        to the module's ``get`` variable (a dict) with ``self.ext`` as their key.

        Variables to be defined:

            name (str)
                The dumpers name, e.g. "JSON" or "Property List".

            ext (str)
                The default file extension.

            output_panel_name (str; optional)
                If this is specified it will be used as the output panel's
                reference name.
                Defaults to ``"aaa_package_dev"``.

            default_params (dict; optional)
                Just a dict of the default params for self.write().

            allowed_params (set/tuple; optional)
                A collection of strings defining the allowed parameters for
                self.write(). Other keys in the kwargs dict will be removed.


        Methods to be implemented:

            write(self, data, params, *args, **kwargs)
                This is called when the actual parsing should happen.

                Data to write is defined in ``data``.
                The parsed data should be returned.
                To output problems, use ``self.output.write_line(str)``.
                The default self.dump function will catch excetions raised
                and print them via ``str()`` to the output.

                Parameters to the dumping functions are in ``params`` dict,
                which have been validated before, according to the class
                variables (see above).
                *args, **kwargs parameters are passed from
                ``load(self, *args, **kwargs)``. If you want to specify or
                process any options or optional parsing, use these.

            validate_data(self, data, *args, **kwargs) (optional)

                Called by self.dump. Please read the documentation for
                _validate_data in order to understand how this function works.

        Methods you can override/implement
        (please read their documentation/code to understand their purposes):

            _validate_data(self, data, funcs)

            validate_params(self, params)

            dump(self, *args, **kwargs)
    """
    name = ""
    ext  = ""
    output_panel_name = "aaa_package_dev"
    default_params = {}
    allowed_params = ()

    def __init__(self, window, view, new_file_path, output=None, file_path=None, *args, **kwargs):
        """Guess what this does.
        """
        self.window = window
        self.view = view
        self.file_path = file_path or view.file_name()
        self.new_file_path = new_file_path

        if isinstance(output, OutputPanel):
            self.output = output
        elif window:
            self.output = OutputPanel(window, self.output_panel_name)

    def validate_data(self, data, *args, **kwargs):
        """To be implemented (optional).

            Must return the validated data object.

            Example:
                return self._validate_data(data, [
                    ((lambda x: isinstance(x, float), int),
                     (lambda x: isinstance(x, datetime.datetime), str),
                     (lambda x: x is None, False))
                ]
        """
        pass

    def _validate_data(self, data, funcs):
        """Check for incompatible data recursively.

        ``funcs`` is supposed to be a set, or just iterable two times and
        represents two functions, one to test whether the data is invalid
        and one to validate it. Both functions accept one parameter:
        the object to test.
        The validation value can be a function (is callable) or be a value.
        In the latter case the value will always be used instead of the
        previous object.

        Example:
            funcs = ((lambda x: isinstance(x, float), int),
                     (lambda x: isinstance(x, datetime.datetime), str),
                     (lambda x: x is None, False))
        """
        checked = []

        def check_recursive(obj):
            # won't and shouldn't work for immutable types
            # I mean, why would you even reference objects inside themselves?
            if obj in checked:
                return obj
            checked.append(obj)

            for is_invalid, validate in funcs:
                if is_invalid(obj):
                    if callable(validate):
                        obj = validate(obj)
                    else:
                        obj = validate

            if isinstance(obj, dict):  # dicts are fine
                for key in obj:
                    obj[key] = check_recursive(obj[key])

            if isinstance(obj, list):  # lists are too
                for i in range(len(obj)):
                    obj[i] = check_recursive(obj[i])

            if isinstance(obj, tuple):  # tuples are immutable ...
                return tuple([check_recursive(sub_obj) for sub_obj in obj])

            if isinstance(obj, set):  # sets ...
                for val in obj:
                    new_val = check_recursive(val)
                    if new_val != val:  # a set's components are hashable, no need to "is"
                        obj.remove(val)
                        obj.add(new_val)

            return obj

        return check_recursive(data)

    def validate_params(self, params):
        """Validate the parameters according to self.default_params and
        self.allowed_params.
        """
        new_params = self.default_params.copy()
        new_params.update(params)
        for key in new_params.keys():
            if key not in self.allowed_params:
                del new_params[key]
        return new_params

    def dump(self, data, *args, **kwargs):
        """Wraps the ``self.write`` function.

        This function is called by the handler directly.
        """
        self.output.write_line("Writing %s... (%s)" % (self.name, self.new_file_path))
        self.output.show()
        data = self.validate_data(data)
        params = self.validate_params(kwargs)
        try:
            self.write(data, params, *args, **kwargs)
        except Exception as e:
            self.output.write_line("Error writing %s: %s" % (self.name, e))
        else:
            return True

    def write(self, data, *args, **kwargs):
        """To be implemented."""
        pass


class JSONDumper(DumperProto):
    name = "JSON"
    ext  = "json"
    default_params = dict(
        skipkeys=True,
        check_circular=False,  # there won't be references here, hopefully
        indent=4
    )
    allowed_params = (
        'skipkeys',
        'ensure_ascii',
        'check_circular',
        'allow_nan',
        'sort_keys',
        'indent',
        'separators',
        'encoding'
    )

    def validate_data(self, data):
        return self._validate_data(data, (
            # TOTEST: sets
            (lambda x: isinstance(x, plistlib.Data), lambda x: x.data),  # plist
            (lambda x: isinstance(x, datetime.date), str),  # yaml
            (lambda x: isinstance(x, datetime.datetime), str)  # plist and yaml
        ))

    def write(self, data, params, *args, **kwargs):
        """Parameters:

            skipkeys (bool)
                Default: True

                Dict keys that are not of a basic type (str, unicode, int,
                long, float, bool, None) will be skipped instead of raising a
                TypeError.

            ensure_ascii (bool)
                Default: True

                If False, then some chunks may be unicode instances, subject to
                normal Python str to unicode coercion rules.

            check_circular (bool)
                Default: False

                If False, the circular reference check for container types will
                be skipped and a circular reference will result in an
                OverflowError (or worse).
                Since we are working with file data here this is likely not
                going to happen.

            allow_nan (bool)
                Default: True

                If False, it will be a ValueError to serialize out of range
                float values (nan, inf, -inf) in strict compliance of the JSON
                specification, instead of using the JavaScript equivalents
                (NaN, Infinity, -Infinity).

            sort_keys (bool)
                Default: True

                The output of dictionaries will be sorted by key.

            indent (int)
                Default: 4

                If a non-negative integer, then JSON array elements and object
                members will be pretty-printed with that indent level. An
                indent level of 0 will only insert newlines. None (the default)
                selects the most compact representation.

            separators (tuple, iterable)
                Default: (', ', ': ')

                (item_separator, dict_separator) tuple. (',', ':') is the most
                compact JSON representation.

            encoding (str)
                Default: UTF-8

                Character encoding for str instances, default is UTF-8.
        """
        with open(self.new_file_path, "w") as f:
            json.dump(data, f, **params)


class PlistDumper(DumperProto):
    name = "Property List"
    ext  = "plist"

    def validate_data(self, data):
        return self._validate_data(data, (
            # TOTEST: sets
            # yaml; lost of "precision" when converting to datetime.datetime
            (lambda x: isinstance(x, datetime.date), str),
            (lambda x: x is None, False)
        ))

    def write(self, data, params, *args, **kwargs):
        plistlib.writePlist(data, self.new_file_path)


class YAMLDumper(DumperProto):
    name = "YAML"
    ext  = "yaml"
    default_params = dict(Dumper=yaml.SafeDumper)
    allowed_params = (
        'default_style',
        'default_flow_style',
        'canonical',
        'indent',
        'width',
        'allow_unicode',
        'line_break',
        'encoding',
        'explicit_start',
        'explicit_end',
        'version',
        'tags',
        'Dumper'
    )

    def validate_data(self, data):
        return self._validate_data(data, (
            (lambda x: isinstance(x, plistlib.Data), lambda x: x.data),  # plist
        ))

    def write(self, data, params, *args, **kwargs):
        """Parameters:

            default_style (str)
                Default: None
                Accepted: None, '', '\'', '"', '|', '>'.

                Indicates the style of the scalar.

            default_flow_style (bool)
                Default: True

                Indicates if a collection is block or flow.

            canonical (bool)
                Default: None (-> False)

                Export tag type to the output file.

            indent (int)
                Default: 2
                Accepted: 1 < x < 10

            width (int)
                Default: 80
                Accepted: > indent*2

            allow_unicode (bool)
                Default: None (-> False)

            line_break (str)
                Default: "\n"
                Accepted: u'\r', u'\n', u'\r\n'

            encoding (str)
                Default: 'utf-8'

            explicit_start (bool)
                Default: None (-> False)

                Explicit '---' at the start.

            explicit_end (bool)
                Default: None (-> False)

                Excplicit '...' at the end.

            version (tuple)
                Default: Newest

                Version of the YAML parser: tuple(major, minor).
                Supports only major version 1.

            tags (str?)
                Default: None

                ???

            ===========================

            Dumper (supposedly derived from yaml.BaseDumper)
                You should know what you are doing when passing this.
        """
        with open(self.new_file_path, "w") as f:
            yaml.dump(data, f, **params)


# Add the internal plistlib dict wrapper to the safe dumper
yaml.SafeDumper.add_representer(
    plistlib._InternalDict,
    yaml.SafeDumper.represent_dict
)


###############################################################################


# Collect all the dumpers and assign them to `get`
get = dict()
for type_name in dir():
    try:
        t = globals()[type_name]
        if t.__bases__:
            if issubclass(t, DumperProto) and not t is DumperProto:
                get[t.ext] = t

    except AttributeError:
        pass

########NEW FILE########
__FILENAME__ = loaders
import re
import os

import json
import yaml
import plistlib

import sublime

from sublime_lib import ST2
from sublime_lib.view import OutputPanel, coorded_substr, base_scope, get_text
from sublime_lib.path import file_path_tuple

###############################################################################

re_js_comments_str = r"""
    (                               # Capture code
        (?:
            "(?:\\.|[^"\\])*"           # String literal
            |
            '(?:\\.|[^'\\])*'           # String literal
            |
            (?:[^/\n"']|/[^/*\n"'])+    # Any code besides newlines or string literals (essentially no comments)
            |
            \n                          # Newline
        )+                          # Repeat
    )|
    (/\* (?:[^*]|\*[^/])* \*/)      # Multi-line comment
    |
    (?://(.*)$)                     # Comment
"""
re_js_comments = re.compile(re_js_comments_str, re.VERBOSE + re.MULTILINE)


def strip_js_comments(string):
    """Originally obtained from Stackoverflow this function strips JavaScript
    (and JSON) comments from a string while considering those encapsulated by strings.

        Source: http://stackoverflow.com/questions/2136363/matching-one-line-javascript-comments-with-re
    """
    parts = re_js_comments.findall(string)
    # Stripping the whitespaces is, of course, optional, but the columns are fucked up anyway
    # with the comments being removed and it doesn't break things.
    return ''.join(x[0].strip(' ') for x in parts)

###############################################################################


# Define the prototype loader class and the loaders for the separate data types
class LoaderProto(object):
    """Prototype class for data loaders of different types.

        Classes derived from this class (and in this file) will be appended
        to the module's ``get`` variable (a dict) with ``self.ext`` as their key.

        Variables to define:

            name (str)
                The loaders name, e.g. "JSON" or "Property List".

            ext (str)
                The default file extension. Used to construct ``self.ext_regex``.

            comment (str; optional)
                The line comment string for the file type. Used to construct
                ``self.opt_regex``.

            scope (str; optional)
                If the view's base scope equals this the file will be considered
                "valid" and then parsed.

            file_regex (str; optional)
                Regex to be applied to your output string in ``parse()``.

                This is used to determine the problem's position in the file and
                lets the user browse the errors with F4 and Shift+F4.
                Define up to three groups:
                    1: file path
                    2: line number
                    3: column

                For reference, see the "result_file_regex" key in a view's
                settings() or compare to build systems.

            output_panel_name (str; optional)
                If this is specified it will be used as the output panel's
                reference name.

                Defaults to ``"aaa_package_dev"``.

            ext_regex (str; optional)
                This regex will be used by get_ext_appendix() to determine the
                extension's appendix. The appendix should be found in group 1.

                Defaults to ``r'(?i)\.%s(?:-([^\.]+))?$' % self.ext``.

            opt_regex (str; optional)
                A regex to search for an option dict in a line. Used by
                ``self.get_options()`` and ``cls.load_options(view)``.
                Content should be found in group 1.

                Defaults to ``r'^\s*%s\s+\[PackageDev\]\s+(.+)$' % cls.comment``.


        Methods to implement:

            parse(self, *args, **kwargs)
                This is called when the actual parsing should happen.

                The file to be read from is defined in ``self.file_path``.
                The parsed data should be returned.
                To output problems, use ``self.output.write_line(str)`` and use a
                string matched by ``self.file_regex`` if possible.

                *args, **kwargs parameters are passed from
                ``load(self, *args, **kwargs)``. If you want to specify any options
                or optional parsing, use these.

        Methods you can override/implement
        (please read their documentation/code to understand their purposes):

            @classmethod
            _pre_init_(cls)

            @classmethod
            get_ext_appendix(cls, file_name)

            @classmethod
            get_new_file_ext(cls, view, file_name=None)

            new_file_ext(self)

            @classmethod
            load_options(self, view)

            get_options(self)

            @classmethod
            file_is_valid(cls, view, file_name=None)

            is_valid(self)

            load(self, *args, **kwargs)
    """
    name    = ""
    ext     = ""
    comment = ""
    scope   = None
    file_regex = ""
    output_panel_name = "aaa_package_dev"

    def __init__(self, window, view, file_path=None, output=None, *args, **kwargs):
        """Mirror the parameters to ``self``, do "init" stuff.
        """
        super(LoaderProto, self).__init__()  # object.__init__ takes no parameters

        self.window = window or view.window() or sublime.active_window()
        self.view = view
        self.file_path = file_path or view.file_name()

        path = os.path.split(self.file_path)[0]
        if isinstance(output, OutputPanel):
            output.set_path(path, self.file_regex)
            self.output = output
        else:
            self.output = OutputPanel(self.window, self.output_panel_name, file_regex=self.file_regex, path=path)

    @classmethod
    def _pre_init_(cls):
        """Assign attributes that depend on other attributes defined by subclasses.
        """
        if not hasattr(cls, 'ext_regex'):
            cls.ext_regex = r'(?i)\.%s(?:-([^\.]+))?$' % cls.ext

        if not hasattr(cls, 'opt_regex'):
            # Will result in an exception when running cls.load_options but will be caught.
            cls.opt_regex = cls.comment and r'^\s*%s\s+\[PackageDev\]\s+(.+)$' % cls.comment or ""

    @classmethod
    def get_ext_appendix(cls, file_name):
        """Returns the appendix part of a file_name in style ".json-Appendix",
        "json" being ``self.ext`` respectively, or ``None``.
        """
        if file_name:
            ret = re.search(cls.ext_regex, file_name)
            if ret and ret.group(1):
                return ret.group(1)
        return None

    @classmethod
    def get_new_file_ext(cls, view, file_path=None):
        """Returns a tuple in style (str(ext), bool(prepend_ext)).

        The first part is the extension string, which may be ``None``.
        The second part is a boolean value that indicates whether the dumper
        (or the handler) should use the value of the first part as appendix
        and prepend the actual "new" file type.

        See also get_ext_appendix().
        """
        file_path = file_path or view and view.file_name()
        if not file_path:
            return (None, False)

        appendix = cls.get_ext_appendix(file_path)
        if appendix:
            return ('.' + appendix, False)

        ext = os.path.splitext(file_path)[1]
        if not ext == '.' + cls.ext and cls.file_is_valid(view, file_path):
            return (ext, True)

        return (None, False)

    def new_file_ext(self):
        """Instance method wrapper for ``cls.get_new_file_ext``.
        """
        return self.__class__.get_new_file_ext(self.view, self.file_path)

    @classmethod
    def load_options(self, view):
        """Search for a line comment in the first few lines which starts with
        ``"[PackageDev]"`` and parse the following things using ``yaml.safe_load``
        after wrapping them in "{}".
        """
        # Don't bother reading the file to load its options.
        if not view:
            return None

        # Search for options in the first 3 lines (compatible with xml)
        for i in range(3):
            try:
                line = coorded_substr(view, (i, 0), (i, -1))
                optstr = re.search(self.opt_regex, line)
                # Just parse the string with yaml; wrapped in {}
                # Yeah, I'm lazy like that, but see, I even put "safe_" in front of it
                return yaml.safe_load('{%s}' % optstr.group(1))
            except:
                continue

        return None

    def get_options(self):
        """Instance method wrapper for ``cls.load_options``.
        """
        return self.__class__.load_options(self.view)

    @classmethod
    def file_is_valid(cls, view, file_path=None):
        """Returns a boolean whether ``file_path`` is a valid file for
        this loader.
        """
        file_path = file_path or view and view.file_name()
        if not file_path:
            return None

        return (cls.get_ext_appendix(file_path) is not None
                or file_path_tuple(file_path).ext == '.' + cls.ext
                or (cls.scope is not None and view
                    and base_scope(view) == cls.scope))

    def is_valid(self):
        """Instance method wrapper for ``cls.file_is_valid``.
        """
        return self.__class__.file_is_valid(self.view, self.file_path)

    def load(self, *args, **kwargs):
        """Wraps ``self.parse(*args, **kwargs)`` and calls some other functions
        similar for almost every loader.

        This function is called by the handler directly.
        """
        if not self.is_valid():
            raise NotImplementedError("Not a %s file." % self.name)

        self.output.write_line("Parsing %s... (%s)" % (self.name, self.file_path))

        return self.parse(*args, **kwargs)

    def parse(self, *args, **kwargs):
        """To be implemented. Should return the parsed data from
        ``self.file_path`` as a Python object.
        """
        pass


class JSONLoader(LoaderProto):
    name    = "JSON"
    ext     = "json"
    comment = "//"
    scope   = "source.json"
    debug_base = 'Error parsing ' + name + ' "%s": %s'
    file_regex = debug_base % (r'(.*?)', r'.+? line (\d+) column (\d+)')

    def parse(self, *args, **kwargs):
        text = get_text(self.view)
        try:
            text = strip_js_comments(text)
            data = json.loads(text)
        except ValueError as e:
            self.output.write_line(self.debug_base % (self.file_path, str(e)))
        else:
            return data


class PlistLoader(LoaderProto):
    name = "Property List"
    ext  = "plist"
    debug_base = 'Error parsing ' + name + ' "%s": %s, line %s, column %s'
    file_regex = re.escape(debug_base).replace(r'\%', '%') % (r'(.*?)', r'.*?', r'(\d+)', r'(\d+)')
    opt_regex = r'^\s*<!--\s+\[PackageDev\]\s+(.+)-->'
    DOCTYPE = "<!DOCTYPE plist"

    @classmethod
    def file_is_valid(cls, view, file_path=None):
        file_path = file_path or view and view.file_name()
        if not file_path:
            return None

        if (cls.get_ext_appendix(file_path) is not None
                or os.path.splitext(file_path)[1] == '.' + cls.ext):
            return True

        # Plists have no scope (syntax definition) since they are XML.
        # Instead, check for the DOCTYPE in the first three lines.
        if view:
            for i in range(3):  # This would be a really terrible one-liner
                text = coorded_substr(view, (i, 0), (i, len(cls.DOCTYPE)))
                if text == cls.DOCTYPE:
                    return True
        return False

    def parse(self, *args, **kwargs):
        # Note: I hate Plist and XML. And it doesn't help a bit that parsing
        # plist files is a REAL PITA.
        text = get_text(self.view)

        # Parsing will fail if `<?xml version="1.0" encoding="UTF-8"?>` encoding is in the first
        # line, so strip it.
        # XXX: Find a better way to fix this misbehaviour of xml stuff in Python
        #      (I mean, plistliv even "writes" that line)
        if text.startswith('<?xml version="1.0" encoding="UTF-8"?>'):
            text = text[38:]

        # See https://github.com/SublimeText/AAAPackageDev/issues/34
        if ST2 and isinstance(text, unicode):
            text = text.encode('utf-8')

        try:
            from xml.parsers.expat import ExpatError, ErrorString
        except ImportError:
            # xml.parsers.expat is not available on certain Linux dists, use plist_parser then.
            # See https://github.com/SublimeText/AAAPackageDev/issues/19
            import plist_parser
            print("[AAAPackageDev] Using plist_parser")

            try:
                data = plist_parser.parse_string(text)
            except plist_parser.PropertyListParseError as e:
                self.output.write_line(self.debug_base % (self.file_path, str(e), 0, 0))
            else:
                return data
        else:
            try:
                # This will try `from xml.parsers.expat import ParserCreate`
                # but since it is already tried above it should succeed.
                if ST2:
                    data = plistlib.readPlistFromString(text)
                else:
                    data = plistlib.readPlistFromBytes(text.encode('utf-8'))
            except ExpatError as e:
                self.output.write_line(self.debug_base
                                       % (self.file_path,
                                          ErrorString(e.code),
                                          e.lineno,
                                          e.offset)
                                       )
            except BaseException as e:
                # Whatever could happen here ...
                self.output.write_line(self.debug_base % (self.file_path, str(e), 0, 0))
            else:
                return data


class YAMLLoader(LoaderProto):
    name    = "YAML"
    ext     = "yaml"
    comment = "#"
    scope   = "source.yaml"
    debug_base = "Error parsing YAML: %s"
    file_regex = r'^ +in "(.*?)", line (\d+), column (\d+)'

    def parse(self, *args, **kwargs):
        text = get_text(self.view)
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            out = self.debug_base % str(e).replace("<unicode string>", self.file_path)
            self.output.write_line(out)
        except IOError as e:
            self.output.write_line('Error opening "%s": %s' % (self.file_path, str(e)))
        else:
            return data


###############################################################################


# Collect all the loaders and assign them to `get`
get = dict()
for type_name in dir():
    try:
        t = globals()[type_name]
        if t.__bases__:
            if issubclass(t, LoaderProto) and not t is LoaderProto:
                t._pre_init_()
                get[t.ext] = t

    except AttributeError:
        pass

########NEW FILE########
__FILENAME__ = strip_js_comments
import re

reexpr = r"""
    (                               # Capture code
        (?:
            "(?:\\.|[^"\\])*"           # String literal
            |
            '(?:\\.|[^'\\])*'           # String literal
            |
            (?:[^/\n"']|/[^/*\n"'])+    # Any code besides newlines or string literals (essentially no comments)
            |
            \n                          # Newline
        )+                          # Repeat
    )|
    (/\*  (?:[^*]|\*[^/])*   \*/)   # Multi-line comment
    |
    (?://(.*)$)                     # Comment
"""
rx = re.compile(reexpr, re.VERBOSE + re.MULTILINE)

# This regex matches with three different subgroups. One for code and two for comment contents. Below is a example of how to extract those.

code = r"""// this is a comment
var x = 2 * 4 // and this is a comment too
var url = "http://www.google.com/" // and "this" too
url += 'but // this is not a comment' // however this one is
url += 'this "is not a comment' + " and ' neither is this //" // only this

bar = 'http://no.comments.com/' // these // are // comments
bar = 'text // string \' no // more //\\' // comments
bar = 'http://no.comments.com/' /*
multiline */
bar = /var/ // comment

/* comment 1 */
bar = open() /* comment 2 */
bar = open() /* comment 2b */// another comment
bar = open( /* comment 3 */ file) // another comment
"""

parts = rx.findall(code)
print('*' * 80, '\nCode:\n\n',                  ''.join(x[0].strip(' ') for x in parts))
print('*' * 80, '\nMulti line comments:\n\n', '\n'.join(x[1] for x in parts if x[1].strip()))
print('*' * 80, '\nOne line comments:\n\n',   '\n'.join(x[2] for x in parts if x[2].strip()))

########NEW FILE########
__FILENAME__ = file_conversion
import os
import time

import sublime

from sublime_lib import WindowAndTextCommand
from sublime_lib.path import file_path_tuple
from sublime_lib.view import OutputPanel

try:  # ST3
    from .fileconv import dumpers, loaders
except ValueError:  # ST2
    from fileconv import dumpers, loaders


# build command
class ConvertFileCommand(WindowAndTextCommand):
    """Convert a file (view's buffer) of type ``source_format`` to type
    ``target_format``.

        Supports the following parsers/loaders:
            'json'
            'plist'
            'yaml'

        Supports the following writers/dumpers:
            'json'
            'plist'
            'yaml'

        The different dumpers try to validate the data passed.
        This works best for json -> anything because json only defines
        strings, numbers, lists and objects (dicts, arrays, hash tables).
    """
    # {name:, kwargs:}
    # name is for the quick panel; others are arguments used when running the command again
    target_list = [dict(name=fmt.name,
                        kwargs={"target_format": fmt.ext})
                   for fmt in dumpers.get.values()]
    for i, itm in enumerate(target_list):
        if itm['name'] == "YAML":
            # Hardcode YAML block style, who knows if anyone can use this
            target_list.insert(
                i + 1,
                dict(name="YAML (Block Style)",
                     kwargs={"target_format": "yaml", "default_flow_style": False})
            )

    def run(self, edit=None, source_format=None, target_format=None, ext=None,
            open_new_file=False, rearrange_yaml_syntax_def=False, _output=None, *args, **kwargs):
        """Available parameters:

            edit (sublime.Edit) = None
                The edit parameter from TextCommand. Unused.

            source_format (str) = None
                The source format. Any of "yaml", "plist" or "json".
                If `None`, attempt to automatically detect the format by extension, used syntax
                highlight or (with plist) the actual contents.

            target_format (str) = None
                The target format. Any of "yaml", "plist" or "json".
                If `None`, attempt to find an option set in the file to parse.
                If unable to find an option, ask the user directly with all available format options.

            ext (str) = None
                The extension of the file to convert to, without leading dot. If `None`, the extension
                will be automatically determined by a special algorythm using "appendixes".

                Here are a few examples:
                    ".YAML-ppplist" yaml  -> plist ".ppplist"
                    ".json"         json  -> yaml  ".yaml"
                    ".tmplist"      plist -> json  ".JSON-tmplist"
                    ".yaml"         json  -> plist ".JSON-yaml" (yes, doesn't make much sense)

            open_new_file (bool) = False
                Open the (newly) created file in a new buffer.

            rearrange_yaml_syntax_def (bool) = False
                Interesting for language definitions, will automatically run
                "rearrange_yaml_syntax_def" command on it, if the target format is "yaml".
                Overrides "open_new_file" parameter.

            _output (OutputPanel) = None
                For internal use only.

            *args
                Forwarded to pretty much every relevant call but does not have any effect.
                You can't pass *args in commands anyway.

            **kwargs
                Will be forwarded to both the loading function and the dumping function, after stripping
                unsopported entries. Only do this if you know what you're doing.

                Functions in question:
                    yaml.dump
                    json.dump
                    plist.writePlist (does not support any parameters)

                A more detailed description of each supported parameter for the respective dumper can be
                found in `fileconv/dumpers.py`.
        """
        # TODO: Ditch *args, can't be passed in commands anyway

        # Check the environment (view, args, ...)
        if self.view.is_scratch():
            return

        if self.view.is_dirty():
            # While it works without saving you should always save your files
            return self.status("Please save the file.")

        file_path = self.view.file_name()
        if not file_path or not os.path.exists(file_path):
            # REVIEW: It is not really necessary for the file to exist, technically
            return self.status("File does not exist.", file_path)

        if source_format and target_format == source_format:
            return self.status("Target and source file format are identical. (%s)" % target_format)

        if source_format and not source_format in loaders.get:
            return self.status("%s for '%s' not supported/implemented." % ("Loader", source_format))

        if target_format and not target_format in dumpers.get:
            return self.status("%s for '%s' not supported/implemented." % ("Dumper", target_format))

        # Now the actual "building" starts (collecting remaining parameters)
        output = _output or OutputPanel(self.window, "package_dev")
        output.show()

        # Auto-detect the file type if it's not specified
        if not source_format:
            output.write("Input type not specified, auto-detecting...")
            for Loader in loaders.get.values():
                if Loader.file_is_valid(self.view):
                    source_format = Loader.ext
                    output.write_line(' %s\n' % Loader.name)
                    break

            if not source_format:
                return output.write_line("\nUnable to detect file type.")
            elif target_format == source_format:
                return output.write_line("File already is %s." % loaders.get[source_format].name)

        # Load inline options
        Loader = loaders.get[source_format]
        opts = Loader.load_options(self.view)

        # Function to determine the new file extension depending on the target format
        def get_new_ext(target_format):
            if ext:
                return '.' + ext
            if opts and 'ext' in opts:
                return '.' + opts['ext']
            else:
                new_ext, prepend_target_format = Loader.get_new_file_ext(self.view)
                if prepend_target_format:
                    new_ext = ".%s-%s" % (target_format.upper(), new_ext[1:])

            return (new_ext or '.' + target_format)

        path_tuple = file_path_tuple(file_path)  # This is the latest point possible

        if not target_format:
            output.write("No target format specified, searching in file...")

            # No information about a target format; ask for it
            if not opts or not 'target_format' in opts:
                output.write(" Could not detect target format.\n"
                             "Please select or define a target format...")

                # Show overlay with all dumping options except for the current type
                # Save stripped-down `items` for later
                options, items = [], []
                for itm in self.target_list:
                    # To not clash with function-local "target_format"
                    target_format_ = itm['kwargs']['target_format']
                    if target_format_ != source_format:
                        options.append(["Convert to: %s" % itm['name'],
                                        path_tuple.base_name + get_new_ext(target_format_)])
                        items.append(itm)

                def on_select(index):
                    target = items[index]
                    output.write_line(' %s\n' % target['name'])

                    kwargs.update(target['kwargs'])
                    kwargs.update(dict(source_format=source_format, _output=output))
                    self.run(*args, **kwargs)

                # Forward all params to the new command call
                self.window.show_quick_panel(options, on_select)
                return

            target_format = opts['target_format']
            # Validate the shit again, but this time print to output panel
            if source_format is not None and target_format == source_format:
                return output.write_line("\nTarget and source file format are identical. (%s)" % target_format)

            if not target_format in dumpers.get:
                return output.write_line("\n%s for '%s' not supported/implemented." % ("Dumper", target_format))

            output.write_line(' %s\n' % dumpers.get[target_format].name)

        start_time = time.time()

        # Okay, THIS is where the building really starts
        # Note: loader or dumper errors are not caught in order to receive a nice traceback in the console
        loader = Loader(self.window, self.view, output=output)

        data = None
        try:
            data = loader.load(*args, **kwargs)
        except NotImplementedError as e:
            # use NotImplementedError to make the handler report the message as it pleases
            output.write_line(str(e))
            self.status(str(e), file_path)

        if data:
            # Determine new file name
            new_file_path = path_tuple.no_ext + get_new_ext(target_format)

            # Init the Dumper
            dumper = dumpers.get[target_format](self.window, self.view, new_file_path, output=output)
            if dumper.dump(data, *args, **kwargs):
                self.status("File conversion successful. (%s -> %s)" % (source_format, target_format))

        # Finish
        output.write("[Finished in %.3fs]" % (time.time() - start_time))
        output.finish()

        if open_new_file or rearrange_yaml_syntax_def:
            new_view = self.window.open_file(new_file_path)

            if rearrange_yaml_syntax_def:
                # For some reason, ST would still indicate the new buffer having "usaved changes"
                # even though there aren't any (calling "save" command here).
                new_view.run_command("rearrange_yaml_syntax_def", {"save": True})

    def status(self, msg, file_path=None):
        sublime.status_message(msg)
        print("[PackageDev] " + msg + (" (%s)" % file_path if file_path is not None else ""))

########NEW FILE########
__FILENAME__ = ordereddict_yaml
# Defines (Safe)Loaders and a SafeDumper for YAML supporting ordered
# dictionaries. Also adds a representer to the default Dumper.

import yaml

from yaml.loader import SafeLoader, Loader
from yaml.dumper import SafeDumper
from yaml.constructor import ConstructorError

try:  # ST2
    from ordereddict import OrderedDict
except ImportError:  # ST3
    from collections import OrderedDict


__all__ = ['OrderedDictLoader', 'OrderedDictSafeLoader', 'OrderedDictSafeDumper']


class BaseOrderedDictLoader(object):
    # http://stackoverflow.com/questions/5121931

    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise ConstructorError(None, None, 'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()

        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError('while constructing a mapping', node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value

        return mapping


class OrderedDictLoader(BaseOrderedDictLoader, Loader):
    """A YAML loader that loads mappings into ordered dictionaries.
    """
    pass


class OrderedDictSafeLoader(BaseOrderedDictLoader, SafeLoader):
    """A YAML (safe) loader that loads mappings into ordered dictionaries.
    """
    pass


def add_ordereddict_constructor(cls):
    cls.add_constructor(
        u'tag:yaml.org,2002:map',
        cls.construct_yaml_map
    )
    cls.add_constructor(
        u'tag:yaml.org,2002:omap',
        cls.construct_yaml_map
    )

add_ordereddict_constructor(OrderedDictLoader)
add_ordereddict_constructor(OrderedDictSafeLoader)


class OrderedDictSafeDumper(SafeDumper):
    """A YAML (safe) dumper that dumps OrderedDicts according to
    their order.
    """

    def represent_ordereddict(self, data):
        # Bypass the sorting in represent_mapping
        return self.represent_mapping(u'tag:yaml.org,2002:map', list(data.items()))

OrderedDictSafeDumper.add_representer(
    OrderedDict,
    OrderedDictSafeDumper.represent_ordereddict
)

# Add representer to the default dumper
yaml.add_representer(
    OrderedDict,
    OrderedDictSafeDumper.represent_ordereddict
)

########NEW FILE########
__FILENAME__ = plist_parser
#!/usr/bin/env python
"""A `Property Lists`_ is a data representation used in Apple's Mac OS X as
a convenient way to store standard object types, such as string, number,
boolean, and container object.

This file contains a class ``XmlPropertyListParser`` for parse
a property list file and get back a python native data structure.

    :copyright: 2008 by Takanori Ishikawa <takanori.ishikawa@gmail.com>
    :license: MIT (See LICENSE file for more details)

.. _Property Lists: http://developer.apple.com/documentation/Cocoa/Conceptual/PropertyLists/
"""

import re
import sys


if sys.version_info >= (3,):
    # Some forwards compatability
    basestring = str


class PropertyListParseError(Exception):
    """Raised when parsing a property list is failed."""
    pass


class XmlPropertyListParser(object):
    """The ``XmlPropertyListParser`` class provides methods that
    convert `Property Lists`_ objects from xml format.
    Property list objects include ``string``, ``unicode``,
    ``list``, ``dict``, ``datetime``, and ``int`` or ``float``.

        :copyright: 2008 by Takanori Ishikawa <takanori.ishikawa@gmail.com>
        :license: MIT License

    .. _Property List: http://developer.apple.com/documentation/Cocoa/Conceptual/PropertyLists/
    """

    def _assert(self, test, message):
        if not test:
            raise PropertyListParseError(message)

    # ------------------------------------------------
    # SAX2: ContentHandler
    # ------------------------------------------------
    def setDocumentLocator(self, locator):
        pass

    def startPrefixMapping(self, prefix, uri):
        pass

    def endPrefixMapping(self, prefix):
        pass

    def startElementNS(self, name, qname, attrs):
        pass

    def endElementNS(self, name, qname):
        pass

    def ignorableWhitespace(self, whitespace):
        pass

    def processingInstruction(self, target, data):
        pass

    def skippedEntity(self, name):
        pass

    def startDocument(self):
        self.__stack = []
        self.__plist = self.__key = self.__characters = None
        # For reducing runtime type checking,
        # the parser caches top level object type.
        self.__in_dict = False

    def endDocument(self):
        self._assert(self.__plist is not None, "A top level element must be <plist>.")
        self._assert(
            len(self.__stack) is 0,
            "multiple objects at top level.")

    def startElement(self, name, attributes):
        if name in XmlPropertyListParser.START_CALLBACKS:
            XmlPropertyListParser.START_CALLBACKS[name](self, name, attributes)
        if name in XmlPropertyListParser.PARSE_CALLBACKS:
            self.__characters = []

    def endElement(self, name):
        if name in XmlPropertyListParser.END_CALLBACKS:
            XmlPropertyListParser.END_CALLBACKS[name](self, name)
        if name in XmlPropertyListParser.PARSE_CALLBACKS:
            # Creates character string from buffered characters.
            content = ''.join(self.__characters)
            # For compatibility with ``xml.etree`` and ``plistlib``,
            # convert text string to ascii, if possible
            try:
                content = content.encode('ascii')
            except (UnicodeError, AttributeError):
                pass
            XmlPropertyListParser.PARSE_CALLBACKS[name](self, name, content)
            self.__characters = None

    def characters(self, content):
        if self.__characters is not None:
            self.__characters.append(content)

    # ------------------------------------------------
    # XmlPropertyListParser private
    # ------------------------------------------------
    def _push_value(self, value):
        if not self.__stack:
            self._assert(self.__plist is None, "Multiple objects at top level")
            self.__plist = value
        else:
            top = self.__stack[-1]
            #assert isinstance(top, (dict, list))
            if self.__in_dict:
                k = self.__key
                if k is None:
                    raise PropertyListParseError("Missing key for dictionary.")
                top[k] = value
                self.__key = None
            else:
                top.append(value)

    def _push_stack(self, value):
        self.__stack.append(value)
        self.__in_dict = isinstance(value, dict)

    def _pop_stack(self):
        self.__stack.pop()
        self.__in_dict = self.__stack and isinstance(self.__stack[-1], dict)

    def _start_plist(self, name, attrs):
        self._assert(not self.__stack and self.__plist is None, "<plist> more than once.")
        self._assert(attrs.get('version', '1.0') == '1.0',
                     "version 1.0 is only supported, but was '%s'." % attrs.get('version'))

    def _start_array(self, name, attrs):
        v = list()
        self._push_value(v)
        self._push_stack(v)

    def _start_dict(self, name, attrs):
        v = dict()
        self._push_value(v)
        self._push_stack(v)

    def _end_array(self, name):
        self._pop_stack()

    def _end_dict(self, name):
        if self.__key is not None:
            raise PropertyListParseError("Missing value for key '%s'" % self.__key)
        self._pop_stack()

    def _start_true(self, name, attrs):
        self._push_value(True)

    def _start_false(self, name, attrs):
        self._push_value(False)

    def _parse_key(self, name, content):
        if not self.__in_dict:
            raise PropertyListParseError("<key> element must be in <dict> element.")
        self.__key = content

    def _parse_string(self, name, content):
        self._push_value(content)

    def _parse_data(self, name, content):
        import base64
        self._push_value(base64.b64decode(content))

    # http://www.apple.com/DTDs/PropertyList-1.0.dtd says:
    #
    # Contents should conform to a subset of ISO 8601
    # (in particular, YYYY '-' MM '-' DD 'T' HH ':' MM ':' SS 'Z'.
    # Smaller units may be omitted with a loss of precision)
    DATETIME_PATTERN = re.compile(r"(?P<year>\d\d\d\d)(?:-(?P<month>\d\d)(?:-(?P<day>\d\d)(?:T(?P<hour>\d\d)(?::(?P<minute>\d\d)(?::(?P<second>\d\d))?)?)?)?)?Z$")

    def _parse_date(self, name, content):
        import datetime

        units = ('year', 'month', 'day', 'hour', 'minute', 'second', )
        pattern = XmlPropertyListParser.DATETIME_PATTERN
        match = pattern.match(content)
        if not match:
            raise PropertyListParseError("Failed to parse datetime '%s'" % content)

        groups, components = match.groupdict(), []
        for key in units:
            value = groups[key]
            if value is None:
                break
            components.append(int(value))
        while len(components) < 3:
            components.append(1)

        d = datetime.datetime(*components)
        self._push_value(d)

    def _parse_real(self, name, content):
        self._push_value(float(content))

    def _parse_integer(self, name, content):
        self._push_value(int(content))

    START_CALLBACKS = {
        'plist': _start_plist,
        'array': _start_array,
        'dict': _start_dict,
        'true': _start_true,
        'false': _start_false,
    }

    END_CALLBACKS = {
        'array': _end_array,
        'dict': _end_dict,
    }

    PARSE_CALLBACKS = {
        'key': _parse_key,
        'string': _parse_string,
        'data': _parse_data,
        'date': _parse_date,
        'real': _parse_real,
        'integer': _parse_integer,
    }

    # ------------------------------------------------
    # XmlPropertyListParser
    # ------------------------------------------------
    def _to_stream(self, io_or_string):
        if isinstance(io_or_string, basestring):
            # Creates a string stream for in-memory contents.
            from cStringIO import StringIO
            return StringIO(io_or_string)
        elif hasattr(io_or_string, 'read') and callable(getattr(io_or_string, 'read')):
            return io_or_string
        else:
            raise TypeError('Can\'t convert %s to file-like-object' % type(io_or_string))

    def _parse_using_etree(self, xml_input):
        from xml.etree.cElementTree import iterparse

        parser = iterparse(self._to_stream(xml_input), events=('start', 'end'))
        self.startDocument()
        try:
            for action, element in parser:
                name = element.tag
                if action == 'start':
                    if name in XmlPropertyListParser.START_CALLBACKS:
                        XmlPropertyListParser.START_CALLBACKS[name](self, element.tag, element.attrib)
                elif action == 'end':
                    if name in XmlPropertyListParser.END_CALLBACKS:
                        XmlPropertyListParser.END_CALLBACKS[name](self, name)
                    if name in XmlPropertyListParser.PARSE_CALLBACKS:
                        XmlPropertyListParser.PARSE_CALLBACKS[name](self, name, element.text or "")
                    element.clear()
        except SyntaxError as e:
            raise PropertyListParseError(e)

        self.endDocument()
        return self.__plist

    def _parse_using_sax_parser(self, xml_input):
        from xml.sax import make_parser, xmlreader, SAXParseException
        source = xmlreader.InputSource()
        source.setByteStream(self._to_stream(xml_input))
        reader = make_parser()
        reader.setContentHandler(self)
        try:
            reader.parse(source)
        except SAXParseException as e:
            raise PropertyListParseError(e)

        return self.__plist

    def parse(self, xml_input):
        """Parse the property list (`.plist`, `.xml, for example) ``xml_input``,
        which can be either a string or a file-like object.

        >>> parser = XmlPropertyListParser()
        >>> parser.parse(r'<plist version="1.0">'
        ...              r'<dict><key>Python</key><string>.py</string></dict>'
        ...              r'</plist>')
        {'Python': '.py'}
        """
        try:
            return self._parse_using_etree(xml_input)
        except ImportError:
            # No xml.etree.ccElementTree found.
            return self._parse_using_sax_parser(xml_input)


def parse_string(io_or_string):
    """Parse a string (or a stream) and return the resulting object.
    """
    return XmlPropertyListParser().parse(io_or_string)


def parse_file(file_path):
    """Parse the specified file and return the resulting object.
    """
    with open(file_path) as f:
        return XmlPropertyListParser().parse(f)

########NEW FILE########
__FILENAME__ = constants
KEY_UP                  = "up"
KEY_DOWN                = "down"
KEY_RIGHT               = "right"
KEY_LEFT                = "left"
KEY_INSERT              = "insert"
KEY_HOME                = "home"
KEY_END                 = "end"
KEY_PAGEUP              = "pageup"
KEY_PAGEDOWN            = "pagedown"
KEY_BACKSPACE           = "backspace"
KEY_DELETE              = "delete"
KEY_TAB                 = "tab"
KEY_ENTER               = "enter"
KEY_PAUSE               = "pause"
KEY_ESCAPE              = "escape"
KEY_SPACE               = "space"
KEY_KEYPAD0             = "keypad0"
KEY_KEYPAD1             = "keypad1"
KEY_KEYPAD2             = "keypad2"
KEY_KEYPAD3             = "keypad3"
KEY_KEYPAD4             = "keypad4"
KEY_KEYPAD5             = "keypad5"
KEY_KEYPAD6             = "keypad6"
KEY_KEYPAD7             = "keypad7"
KEY_KEYPAD8             = "keypad8"
KEY_KEYPAD9             = "keypad9"
KEY_KEYPAD_PERIOD       = "keypad_period"
KEY_KEYPAD_DIVIDE       = "keypad_divide"
KEY_KEYPAD_MULTIPLY     = "keypad_multiply"
KEY_KEYPAD_MINUS        = "keypad_minus"
KEY_KEYPAD_PLUS         = "keypad_plus"
KEY_KEYPAD_ENTER        = "keypad_enter"
KEY_CLEAR               = "clear"
KEY_F1                  = "f1"
KEY_F2                  = "f2"
KEY_F3                  = "f3"
KEY_F4                  = "f4"
KEY_F5                  = "f5"
KEY_F6                  = "f6"
KEY_F7                  = "f7"
KEY_F8                  = "f8"
KEY_F9                  = "f9"
KEY_F10                 = "f10"
KEY_F11                 = "f11"
KEY_F12                 = "f12"
KEY_F13                 = "f13"
KEY_F14                 = "f14"
KEY_F15                 = "f15"
KEY_F16                 = "f16"
KEY_F17                 = "f17"
KEY_F18                 = "f18"
KEY_F19                 = "f19"
KEY_F20                 = "f20"
KEY_SYSREQ              = "sysreq"
KEY_BREAK               = "break"
KEY_CONTEXT_MENU        = "context_menu"
KEY_BROWSER_BACK        = "browser_back"
KEY_BROWSER_FORWARD     = "browser_forward"
KEY_BROWSER_REFRESH     = "browser_refresh"
KEY_BROWSER_STOP        = "browser_stop"
KEY_BROWSER_SEARCH      = "browser_search"
KEY_BROWSER_FAVORITES   = "browser_favorites"
KEY_BROWSER_HOME        = "browser_home"

########NEW FILE########
__FILENAME__ = edit
# edit.py, courtesy of @lunixbochs (https://github.com/lunixbochs)
# and slightly modified
"""Abstraction for edit objects in ST2 and ST3

All methods on "edit" create an edit step. When leaving the `with` block, all
the steps are executed one by one.

Be careful: All other code in the with block is still executed! If a method on
edit depends on something you do based on a previous method on edit, you
should use the second method. However, using `edit.callback` or pass a
function as an argument you can circumvent that if it's only small things. The
function will be called with the parameters `view` and `edit` when processing
the edit group.

Usage 1:
    with Edit(view) as edit:
        edit.insert(0, "text")
        edit.replace(reg, "replacement")
        edit.erase(lambda v,e: sublime.Region(0, v.size()))
        # OR
        # edit.callback(lambda v,e: v.erase(e, sublime.Region(0, v.size())))

Usage 2:
    def do_ed(view, edit):
        edit.erase()
        view.insert(edit, 0, "text")
        view.sel().clear()
        view.sel().add(sublime.Region(0, 4))
        edit.replace(reg, "replacement")

    Edit.call(do_ed)

Available methods:
    Note: Any of these parameters can be a function which will be called with
    `view` and `edit` when processing the edit group.

    insert(point, string)
        view.insert(edit, point, string)

    erase(region)
        view.erase(edit, region)

    replace(region, string)
        view.replace(edit, region, string)

    callback(func)
        func(view, edit)

"""

import inspect
import sublime
import sublime_plugin

from . import ST2

try:
    sublime.edit_storage
except AttributeError:
    sublime.edit_storage = {}


def run_callback(func, *args, **kwargs):
    spec = inspect.getfullargspec(func)
    if spec.args or spec.varargs:
        func(*args, **kwargs)
    else:
        func()


class EditStep:
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = args

    def run(self, view, edit):
        if self.cmd == 'callback':
            return run_callback(self.args[0], view, edit)

        funcs = {
            'insert':  view.insert,
            'erase':   view.erase,
            'replace': view.replace,
        }
        func = funcs.get(self.cmd)
        if func:
            args = self.resolve_args(view, edit)
            func(edit, *args)

    def resolve_args(self, view, edit):
        args = []
        for arg in self.args:
            if callable(arg):
                arg = arg(view, edit)
            args.append(arg)
        return args


class Edit:
    def __init__(self, view, func=None):
        self.view = view
        self.steps = []

    def __nonzero__(self):
        return bool(self.steps)

    __bool__ = __nonzero__  # Python 3 equivalent

    def step(self, cmd, *args):
        step = EditStep(cmd, *args)
        self.steps.append(step)

    def insert(self, point, string):
        self.step('insert', point, string)

    def erase(self, region):
        self.step('erase', region)

    def replace(self, region, string):
        self.step('replace', region, string)

    @classmethod
    def call(cls, view, func):
        if not (func and callable(func)):
            return

        with cls(view) as edit:
            edit.callback(func)

    def callback(self, func):
        self.step('callback', func)

    def run(self, view, edit):
        for step in self.steps:
            step.run(view, edit)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        view = self.view
        if ST2:
            edit = view.begin_edit()
            self.run(view, edit)
            view.end_edit(edit)
        else:
            key = str(hash(tuple(self.steps)))
            sublime.edit_storage[key] = self
            view.run_command('sl_apply_edit', {'key': key})


if not ST2:
    # Changed command name to not clash with other variations of this file
    class SlApplyEdit(sublime_plugin.TextCommand):
        def run(self, edit, key):
            sublime.edit_storage.pop(key).run(self.view, edit)

    # Make command known to sublime_command despite not being loaded by it
    sublime_plugin.text_command_classes.append(SlApplyEdit)

    # Make the command unloadable
    plugins = [SlApplyEdit]

########NEW FILE########
__FILENAME__ = path
import os
import re
import inspect
from collections import namedtuple

import sublime

__all__ = [
    "FTYPE_EXT_KEYMAP",
    "FTYPE_EXT_COMPLETIONS",
    "FTYPE_EXT_SNIPPET",
    "FTYPE_EXT_BUILD",
    "FTYPE_EXT_SETTINGS",
    "FTYPE_EXT_TMPREFERENCES",
    "FTYPE_EXT_TMLANGUAGE",
    "root_at_packages",
    "data_path",
    "root_at_data",
    "file_path_tuple",
    "get_module_path",
    "get_package_name"
]


FTYPE_EXT_KEYMAP        = ".sublime-keymap"
FTYPE_EXT_COMPLETIONS   = ".sublime-completions"
FTYPE_EXT_SNIPPET       = ".sublime-snippet"
FTYPE_EXT_BUILD         = ".sublime-build"
FTYPE_EXT_SETTINGS      = ".sublime-settings"
FTYPE_EXT_TMPREFERENCES = ".tmPreferences"
FTYPE_EXT_TMLANGUAGE    = ".tmLanguage"


def root_at_packages(*leafs):
    """Combines leafs with path to Sublime's Packages folder.
    """
    # If we really need to, we dan extract the packages path from sys.path (ST3)
    return os.path.join(sublime.packages_path(), *leafs)


def data_path():
    """Extract Sublime Text's data path from the packages path.
    Requires the API to finish loading on ST3.
    """
    return os.path.split(sublime.packages_path())[0]


def root_at_data(*leafs):
    """Combines leafs with Sublime's ``Data`` folder.
    """
    data = os.path.join(os.path.dirname(sublime.packages_path()))
    return os.path.join(data, *leafs)


FilePath = namedtuple("FilePath", "file_path path file_name base_name ext no_ext")


def file_path_tuple(file_path):
    """Creates a named tuple with the following attributes:
    file_path, path, file_name, base_name, ext, no_ext
    """
    path, file_name = os.path.split(file_path)
    base_name, ext = os.path.splitext(file_name)
    return FilePath(
        file_path,
        path,
        file_name,
        base_name,
        ext,
        no_ext=os.path.join(path, base_name)
    )


def get_module_path(_file_=None):
    """Returns a tuple with the normalized module path plus a boolean.

    * _file_ (optional)
        The value of `__file__` in your module.
        If omitted, `get_caller_frame()` will be used instead which usually works.

    Returns: (normalized_module_path, archived)
        `normalized_module_path`
            What you usually refer to when using Sublime API, without `.sublime-package`
        `archived`
            True, when in an archive
    """
    if _file_ is None:
        _file_ = get_caller_frame().f_globals['__file__']

    dir_name = os.path.dirname(os.path.abspath(_file_))
    # Check if we are in an archived package
    if int(sublime.version()) < 3000 or not dir_name.endswith(".sublime-package"):
        return dir_name, False

    # We are in a .sublime-package and need to normalize the path
    virtual_path = re.sub(r"(?:Installed )?Packages([\\/][^\\/]+)\.sublime-package(?=[\\/]|$)",
                          r"Packages\1", dir_name)
    return virtual_path, True


def get_package_path(_file_=None):
    """Returns the path to the current Sublime Text package.
    Parameters are the same as for `get_module_path`.
    """
    if _file_ is None:
        _file_ = get_caller_frame().f_globals['__file__']

    mpath = get_module_path(_file_)[0]

    # There probably is a better way for this, but it works
    while not os.path.dirname(mpath).endswith('Packages'):
        if len(mpath) <= 3:
            return None
        # We're not in a top-level plugin.
        # If this was ST2 we could easily use sublime.packages_path(), but ...
        mpath = os.path.dirname(mpath)

    return mpath


def get_package_name(_file_=None):
    """`return os.path.split(get_package_path(_file_))[1]`
    """
    if _file_ is None:
        _file_ = get_caller_frame().f_globals['__file__']

    return os.path.split(get_package_path(_file_))[1]


def get_caller_frame(i=1):
    """Utilizes the inspect module to get the caller's frame.
    You can adjust `i` to find the i-th caller, default is 1.
    """
    # We can't use inspect.stack()[1 + i][1] for the file name because ST sets
    # that to a different value when inside a zip archive.
    return inspect.stack()[1 + i][0]

########NEW FILE########
__FILENAME__ = output_panel
from sublime import Region, Window, version

from ._view import ViewSettings, unset_read_only, append, clear, get_text

if int(version()) > 3000:
    basestring = str


class OutputPanel(object):
    """This class represents an output panel (which are used for e.g. build systems).
    Please not that the panel's contents will be cleared on __init__.

    OutputPanel(window, panel_name, file_regex=None, line_regex=None, path=None, read_only=True)
        * window
            The window. This is usually `self.window` or
            `self.view.window()`, depending on the type of your command.

        * panel_name
            The panel's name, passed to `window.get_output_panel()`.

        * file_regex
            Important for Build Systems. The user can browse the errors you
            writewith F4 and Shift+F4 keys. The error's location is
            determined with 3 capturing groups:
            the file name, the line number and the column.
            The last two are optional.

            Example:
                r"Error in file "(.*?)", line (\d+), column (\d+)"

        * line_regex
            Same style as `file_regex` except that it misses the first
            group for the file name.

            If `file_regex` doesn't match on the current line, but
            `line_regex` exists, and it does match on the current line,
            then walk backwards through the buffer until  a line matching
            file regex is found, and use these two matches
            to determine the file and line to go to; column is optional.

        * path
            This is only needed if you specify the file_regex param and
            will be used as the root dir for relative filenames when
            determining error locations.

        * read_only
            A boolean whether the output panel should be read only.
            You usually want this to be true.
            Can be modified with `self.view.set_read_only()` when needed.

    Useful attributes:

        view
            The view handle of the output panel. Can be passed to
            `Edit(output.view)` to group modifications for example.

    Defines the following methods:

        set_path(path=None, file_regex=None, line_regex=None)
            Used to update `path`, `file_regex` and `line_regex` if
            they are not `None`, see the constructor for information
            about these parameters.

            The file_regex is updated automatically because it might happen
            that the same panel_name is used multiple times.
            If `file_regex` is omitted or `None` it will be reset to
            the latest regex specified (when creating the instance or from
            the last call of  set_regex/path).
            The same applies to `line_regex`.

        set_regex(file_regex=None, line_regex=None)
            Subset of set_path. Read there for further information.

        write(text)
            Will just write appending `text` to the output panel.

        write_line(text)
            Same as write() but inserts a newline at the end.

        clear()
            Erases all text in the output panel.

        show()
        hide()
            Show or hide the output panel.

        finish()
            Call this when you are done with updating the panel.
            Required if you want the next_result command (F4) to work.
    """
    def __init__(self, window, panel_name, file_regex=None, line_regex=None, path=None, read_only=True):
        if not isinstance(window, Window):
            raise ValueError("window parameter is invalid")
        if not isinstance(panel_name, basestring):
            raise ValueError("panel_name must be a string")

        self.window = window
        self.panel_name = panel_name
        self.view = window.get_output_panel(panel_name)
        self.view.set_read_only(read_only)
        self.settings = ViewSettings(self.view)

        self.set_path(path, file_regex, line_regex)

    def set_path(self, path=None, file_regex=None, line_regex=None):
        """Update the view's result_base_dir pattern.
        Only overrides the previous settings if parameters are not None.
        """
        if path is not None:
            self.settings.result_base_dir = path
        # Also always update the file_regex
        self.set_regex(file_regex, line_regex)

    def set_regex(self, file_regex=None, line_regex=None):
        """Update the view's result_(file|line)_regex patterns.
        Only overrides the previous settings if parameters are not None.
        """
        if file_regex is not None:
            self.file_regex = file_regex
        if hasattr(self, 'file_regex'):
            self.settings.result_file_regex = self.file_regex

        if line_regex is not None:
            self.line_regex = line_regex
        if hasattr(self, 'line_regex'):
            self.settings.result_line_regex = self.line_regex

        # Call get_output_panel again after assigning the above settings, so that "next_result" and
        # "prev_result" work. However, it will also clear the view so read it before and re-write
        # its contents afterwards.
        contents = get_text(self.view)
        self.view = self.window.get_output_panel(self.panel_name)
        self.write(contents)

    def write(self, text):
        """Appends `text` to the output panel.
        Alias for `sublime_lib.view.append(self.view, text)` + `with unset_read_only:`.
        """
        with unset_read_only(self.view):
            append(self.view, text)

    def write_line(self, text):
        """Appends `text` to the output panel and starts a new line.
        """
        self.write(text + "\n")

    def clear(self):
        """Clears the output panel.
        Alias for `sublime_lib.view.clear(self.view)`.
        """
        with unset_read_only(self.view):
            clear(self.view)

    def show(self):
        """Makes the output panel visible.
        """
        self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})

    def hide(self):
        """Makes the output panel invisible.
        """
        self.window.run_command("hide_panel", {"panel": "output.%s" % self.panel_name})

    def finish(self):
        """Things that are required to use the output panel properly.

        Set the selection to the start, so that next_result will work as
        expected.
        """
        self.view.sel().clear()
        self.view.sel().add(Region(0))

########NEW FILE########
__FILENAME__ = _view
from contextlib import contextmanager

from sublime import Region, View

from .. import Settings
from ..edit import Edit

__all__ = ['ViewSettings', 'unset_read_only', 'append', 'clear', 'has_sels',
           'has_file_ext', 'base_scope', 'rowcount', 'rowwidth',
           'relative_point', 'coorded_region', 'coorded_substr', 'get_text',
           'get_viewport_point', 'get_viewport_coords', 'set_viewport',
           'extract_selector']


# TODO remove
class ViewSettings(Settings):
    """Helper class for accessing settings' values from views.

    Derived from sublime_lib.Settings. Please also read the documentation
    there.

    ViewSettings(view, none_erases=False)

        * view (sublime.View)
            Forwarding ``view.settings()``.

        * none_erases (bool, optional)
            Iff ``True`` a setting's key will be erased when setting it to
            ``None``. This only has a meaning when the key you erase is defined
            in a parent Settings collection which would be retrieved in that
            case.
    """
    def __init__(self, view, none_erases=False):
        if not isinstance(view, View):
            raise ValueError("Invalid view")
        settings = view.settings()
        if not settings:
            raise ValueError("Could not resolve view.settings()")
        super(ViewSettings, self).__init__(settings, none_erases)


@contextmanager
def unset_read_only(view):
    """Context manager to make sure a view writable if it is read-only.
    If the view is not read-only it will just leave it untouched.

    Yields a boolean indicating whether the view was read-only before or
    not. This has limited use.

    Examples:
        ...
        with unset_read_only(view):
            ...
        ...
    """
    read_only_before = view.is_read_only()
    if read_only_before:
        view.set_read_only(False)

    yield read_only_before

    if read_only_before:
        view.set_read_only(True)


def append(view, text, scroll=False):
    """Appends text to `view`. Won't work if the view is read-only.

    The `scroll_always` parameter may be one of these values:

        True:  Always scroll to the end of the view.
        False: Scroll only if the selecton is already at the end.
        None:  Don't scroll.
    """
    size = view.size()
    scroll = scroll or (scroll is not None and len(view.sel()) == 1 and
                        view.sel()[0] == Region(size))

    with Edit(view) as edit:
        edit.insert(size, text)

    if scroll:
        view.show(view.size())


def clear(view, edit=None):
    """Removes all the text in ``view``. Won't work if the view is read-only.
    """
    with Edit(view) as edit:
        edit.erase(Region(0, view.size()))


def has_sels(view):
    """Returns `True` if `view` has one selection or more.
    """
    return len(view.sel()) > 0


def has_file_ext(view, ext):
    """Returns `True` if `view` has file extension `ext`.
    `ext` may be specified with or without leading ".".
    """
    if not view.file_name() or not ext.strip().replace('.', ''):
        return False

    if not ext.startswith('.'):
        ext = '.' + ext

    return view.file_name().endswith(ext)


def base_scope(view):
    """Returns the view's base scope.
    """
    return view.scope_name(0).split(' ', 1)[0]


def rowcount(view):
    """Returns the 1-based number of rows in ``view``.
    """
    return view.rowcol(view.size())[0] + 1


def rowwidth(view, row):
    """Returns the 1-based number of characters of ``row`` in ``view``.
    """
    return view.rowcol(view.line(view.text_point(row, 0)).end())[1] + 1


def relative_point(view, row=0, col=0, p=None):
    """Returns a point (int) to the given coordinates.

    Supports relative (negative) parameters and checks if they are in the
    bounds (other than `View.text_point()`).

    If p (indexable -> `p[0]`, `len(p) == 2`; preferrably a tuple) is
    specified, row and col parameters are overridden.
    """
    if p is not None:
        if len(p) != 2:
            raise TypeError("Coordinates have 2 dimensions, not %d" % len(p))
        (row, col) = p

    # shortcut
    if row == -1 and col == -1:
        return view.size()

    # calc absolute coords and check if coords are in the bounds
    rowc = rowcount(view)
    if row < 0:
        row = max(rowc + row, 0)
    else:
        row = min(row, rowc - 1)

    roww = rowwidth(view, row)
    if col < 0:
        col = max(roww + col, 0)
    else:
        col = min(col, roww - 1)

    return view.text_point(row, col)


def coorded_region(view, reg1=None, reg2=None, rel=None):
    """Turn two coordinate pairs into a region.

    The pairs are checked for boundaries by `relative_point`.

    You may also supply a `rel` parameter which will determine the
    Region's end point relative to `reg1`, as a pair. The pairs are
    supposed to be indexable and have a length of 2. Tuples are preferred.

    Defaults to the whole buffer (`reg1=(0, 0), reg2=(-1, -1)`).

    Examples:
    coorded_region(view, (20, 0), (22, -1))    # normal usage
    coorded_region(view, (20, 0), rel=(2, -1)) # relative, works because 0-1=-1
    coorded_region(view, (22, 6), rel=(2, 15)) # relative, ~ more than 3 lines,
                                               # if line 25 is long enough

    """
    reg1 = reg1 or (0, 0)
    if rel:
        reg2 = (reg1[0] + rel[0], reg1[1] + rel[1])
    else:
        reg2 = reg2 or (-1, -1)

    p1 = relative_point(view, p=reg1)
    p2 = relative_point(view, p=reg2)
    return Region(p1, p2)


def coorded_substr(view, reg1=None, reg2=None, rel=None):
    """Returns the string of two coordinate pairs forming a region.

    The pairs are supporsed to be indexable and have a length of 2.
    Tuples are preferred.

    Defaults to the whole buffer.

        For examples, see `coorded_region`.
    """
    return view.substr(coorded_region(view, reg1, reg2))


def get_text(view):
    """Returns the whole string of a buffer. Alias for `coorded_substr(view)`.
    """
    return coorded_substr(view)


def get_viewport_point(view):
    """Returns the text point of the current viewport.
    """
    return view.layout_to_text(view.viewport_position())


def get_viewport_coords(view):
    """Returns the text coordinates of the current viewport.
    """
    return view.rowcol(get_viewport_point(view))


def set_viewport(view, row, col=None):
    """Sets the current viewport from either a text point or relative coords.

        set_viewport(view, 892)      # point
        set_viewport(view, 2, 27)    # coords1
        set_viewport(view, (2, 27))  # coords2
    """
    if col is None:
        pos = row

    if type(row) == tuple:
        pos = relative_point(view, p=row)
    else:
        pos = relative_point(view, row, col)

    view.set_viewport_position(view.text_to_layout(pos))


def extract_selector(view, selector, point):
    """Works similar to view.extract_scope except that you may define the
    selector (scope) on your own and it does not use the point's scope by
    default.

    Example:
        extract_selector(view, "source string", view.sel()[0].begin())

    Returns the Region for the out-most "source string" which contains the
    beginning of the first selection.
    """
    regs = view.find_by_selector(selector)
    for reg in regs:
        if reg.contains(point):
            return reg
    return None

########NEW FILE########
__FILENAME__ = ordereddict
# https://code.activestate.com/recipes/576693/

# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.

try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass

__all__ = ['OrderedDict']


class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self) == len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)

########NEW FILE########
__FILENAME__ = composer

__all__ = ['Composer', 'ComposerError']

from error import MarkedYAMLError
from events import *
from nodes import *

class ComposerError(MarkedYAMLError):
    pass

class Composer(object):

    def __init__(self):
        self.anchors = {}

    def check_node(self):
        # Drop the STREAM-START event.
        if self.check_event(StreamStartEvent):
            self.get_event()

        # If there are more documents available?
        return not self.check_event(StreamEndEvent)

    def get_node(self):
        # Get the root node of the next document.
        if not self.check_event(StreamEndEvent):
            return self.compose_document()

    def get_single_node(self):
        # Drop the STREAM-START event.
        self.get_event()

        # Compose a document if the stream is not empty.
        document = None
        if not self.check_event(StreamEndEvent):
            document = self.compose_document()

        # Ensure that the stream contains no more documents.
        if not self.check_event(StreamEndEvent):
            event = self.get_event()
            raise ComposerError("expected a single document in the stream",
                    document.start_mark, "but found another document",
                    event.start_mark)

        # Drop the STREAM-END event.
        self.get_event()

        return document

    def compose_document(self):
        # Drop the DOCUMENT-START event.
        self.get_event()

        # Compose the root node.
        node = self.compose_node(None, None)

        # Drop the DOCUMENT-END event.
        self.get_event()

        self.anchors = {}
        return node

    def compose_node(self, parent, index):
        if self.check_event(AliasEvent):
            event = self.get_event()
            anchor = event.anchor
            if anchor not in self.anchors:
                raise ComposerError(None, None, "found undefined alias %r"
                        % anchor.encode('utf-8'), event.start_mark)
            return self.anchors[anchor]
        event = self.peek_event()
        anchor = event.anchor
        if anchor is not None:
            if anchor in self.anchors:
                raise ComposerError("found duplicate anchor %r; first occurence"
                        % anchor.encode('utf-8'), self.anchors[anchor].start_mark,
                        "second occurence", event.start_mark)
        self.descend_resolver(parent, index)
        if self.check_event(ScalarEvent):
            node = self.compose_scalar_node(anchor)
        elif self.check_event(SequenceStartEvent):
            node = self.compose_sequence_node(anchor)
        elif self.check_event(MappingStartEvent):
            node = self.compose_mapping_node(anchor)
        self.ascend_resolver()
        return node

    def compose_scalar_node(self, anchor):
        event = self.get_event()
        tag = event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(ScalarNode, event.value, event.implicit)
        node = ScalarNode(tag, event.value,
                event.start_mark, event.end_mark, style=event.style)
        if anchor is not None:
            self.anchors[anchor] = node
        return node

    def compose_sequence_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(SequenceNode, None, start_event.implicit)
        node = SequenceNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        index = 0
        while not self.check_event(SequenceEndEvent):
            node.value.append(self.compose_node(node, index))
            index += 1
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node

    def compose_mapping_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(MappingNode, None, start_event.implicit)
        node = MappingNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        while not self.check_event(MappingEndEvent):
            #key_event = self.peek_event()
            item_key = self.compose_node(node, None)
            #if item_key in node.value:
            #    raise ComposerError("while composing a mapping", start_event.start_mark,
            #            "found duplicate key", key_event.start_mark)
            item_value = self.compose_node(node, item_key)
            #node.value[item_key] = item_value
            node.value.append((item_key, item_value))
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node


########NEW FILE########
__FILENAME__ = constructor

__all__ = ['BaseConstructor', 'SafeConstructor', 'Constructor',
    'ConstructorError']

from error import *
from nodes import *

import datetime

import binascii, re, sys, types

class ConstructorError(MarkedYAMLError):
    pass

class BaseConstructor(object):

    yaml_constructors = {}
    yaml_multi_constructors = {}

    def __init__(self):
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.state_generators = []
        self.deep_construct = False

    def check_data(self):
        # If there are more documents available?
        return self.check_node()

    def get_data(self):
        # Construct and return the next document.
        if self.check_node():
            return self.construct_document(self.get_node())

    def get_single_data(self):
        # Ensure that the stream contains a single document and construct it.
        node = self.get_single_node()
        if node is not None:
            return self.construct_document(node)
        return None

    def construct_document(self, node):
        data = self.construct_object(node)
        while self.state_generators:
            state_generators = self.state_generators
            self.state_generators = []
            for generator in state_generators:
                for dummy in generator:
                    pass
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.deep_construct = False
        return data

    def construct_object(self, node, deep=False):
        if node in self.constructed_objects:
            return self.constructed_objects[node]
        if deep:
            old_deep = self.deep_construct
            self.deep_construct = True
        if node in self.recursive_objects:
            raise ConstructorError(None, None,
                    "found unconstructable recursive node", node.start_mark)
        self.recursive_objects[node] = None
        constructor = None
        tag_suffix = None
        if node.tag in self.yaml_constructors:
            constructor = self.yaml_constructors[node.tag]
        else:
            for tag_prefix in self.yaml_multi_constructors:
                if node.tag.startswith(tag_prefix):
                    tag_suffix = node.tag[len(tag_prefix):]
                    constructor = self.yaml_multi_constructors[tag_prefix]
                    break
            else:
                if None in self.yaml_multi_constructors:
                    tag_suffix = node.tag
                    constructor = self.yaml_multi_constructors[None]
                elif None in self.yaml_constructors:
                    constructor = self.yaml_constructors[None]
                elif isinstance(node, ScalarNode):
                    constructor = self.__class__.construct_scalar
                elif isinstance(node, SequenceNode):
                    constructor = self.__class__.construct_sequence
                elif isinstance(node, MappingNode):
                    constructor = self.__class__.construct_mapping
        if tag_suffix is None:
            data = constructor(self, node)
        else:
            data = constructor(self, tag_suffix, node)
        if isinstance(data, types.GeneratorType):
            generator = data
            data = generator.next()
            if self.deep_construct:
                for dummy in generator:
                    pass
            else:
                self.state_generators.append(generator)
        self.constructed_objects[node] = data
        del self.recursive_objects[node]
        if deep:
            self.deep_construct = old_deep
        return data

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            raise ConstructorError(None, None,
                    "expected a scalar node, but found %s" % node.id,
                    node.start_mark)
        return node.value

    def construct_sequence(self, node, deep=False):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None,
                    "expected a sequence node, but found %s" % node.id,
                    node.start_mark)
        return [self.construct_object(child, deep=deep)
                for child in node.value]

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                        "found unacceptable key (%s)" % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

    def construct_pairs(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        pairs = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            pairs.append((key, value))
        return pairs

    def add_constructor(cls, tag, constructor):
        if not 'yaml_constructors' in cls.__dict__:
            cls.yaml_constructors = cls.yaml_constructors.copy()
        cls.yaml_constructors[tag] = constructor
    add_constructor = classmethod(add_constructor)

    def add_multi_constructor(cls, tag_prefix, multi_constructor):
        if not 'yaml_multi_constructors' in cls.__dict__:
            cls.yaml_multi_constructors = cls.yaml_multi_constructors.copy()
        cls.yaml_multi_constructors[tag_prefix] = multi_constructor
    add_multi_constructor = classmethod(add_multi_constructor)

class SafeConstructor(BaseConstructor):

    def construct_scalar(self, node):
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if key_node.tag == u'tag:yaml.org,2002:value':
                    return self.construct_scalar(value_node)
        return BaseConstructor.construct_scalar(self, node)

    def flatten_mapping(self, node):
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == u'tag:yaml.org,2002:merge':
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError("while constructing a mapping",
                                    node.start_mark,
                                    "expected a mapping for merging, but found %s"
                                    % subnode.id, subnode.start_mark)
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "expected a mapping or list of mappings for merging, but found %s"
                            % value_node.id, value_node.start_mark)
            elif key_node.tag == u'tag:yaml.org,2002:value':
                key_node.tag = u'tag:yaml.org,2002:str'
                index += 1
            else:
                index += 1
        if merge:
            node.value = merge + node.value

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        return BaseConstructor.construct_mapping(self, node, deep=deep)

    def construct_yaml_null(self, node):
        self.construct_scalar(node)
        return None

    bool_values = {
        u'yes':     True,
        u'no':      False,
        u'true':    True,
        u'false':   False,
        u'on':      True,
        u'off':     False,
    }

    def construct_yaml_bool(self, node):
        value = self.construct_scalar(node)
        return self.bool_values[value.lower()]

    def construct_yaml_int(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value[0] == '0':
            return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

    inf_value = 1e300
    while inf_value != inf_value*inf_value:
        inf_value *= inf_value
    nan_value = -inf_value/inf_value   # Trying to make a quiet NaN (like C99).

    def construct_yaml_float(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '').lower()
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '.inf':
            return sign*self.inf_value
        elif value == '.nan':
            return self.nan_value
        elif ':' in value:
            digits = [float(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0.0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*float(value)

    def construct_yaml_binary(self, node):
        value = self.construct_scalar(node)
        try:
            return str(value).decode('base64')
        except (binascii.Error, UnicodeEncodeError), exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark) 

    timestamp_regexp = re.compile(
            ur'''^(?P<year>[0-9][0-9][0-9][0-9])
                -(?P<month>[0-9][0-9]?)
                -(?P<day>[0-9][0-9]?)
                (?:(?:[Tt]|[ \t]+)
                (?P<hour>[0-9][0-9]?)
                :(?P<minute>[0-9][0-9])
                :(?P<second>[0-9][0-9])
                (?:\.(?P<fraction>[0-9]*))?
                (?:[ \t]*(?P<tz>Z|(?P<tz_sign>[-+])(?P<tz_hour>[0-9][0-9]?)
                (?::(?P<tz_minute>[0-9][0-9]))?))?)?$''', re.X)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        year = int(values['year'])
        month = int(values['month'])
        day = int(values['day'])
        if not values['hour']:
            return datetime.date(year, month, day)
        hour = int(values['hour'])
        minute = int(values['minute'])
        second = int(values['second'])
        fraction = 0
        if values['fraction']:
            fraction = values['fraction'][:6]
            while len(fraction) < 6:
                fraction += '0'
            fraction = int(fraction)
        delta = None
        if values['tz_sign']:
            tz_hour = int(values['tz_hour'])
            tz_minute = int(values['tz_minute'] or 0)
            delta = datetime.timedelta(hours=tz_hour, minutes=tz_minute)
            if values['tz_sign'] == '-':
                delta = -delta
        data = datetime.datetime(year, month, day, hour, minute, second, fraction)
        if delta:
            data -= delta
        return data

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        omap = []
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap.append((key, value))

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = []
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing pairs", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = set()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        value = self.construct_scalar(node)
        try:
            return value.encode('ascii')
        except UnicodeEncodeError:
            return value

    def construct_yaml_seq(self, node):
        data = []
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = {}
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = cls.__new__(cls)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)

    def construct_undefined(self, node):
        raise ConstructorError(None, None,
                "could not determine a constructor for the tag %r" % node.tag.encode('utf-8'),
                node.start_mark)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:null',
        SafeConstructor.construct_yaml_null)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:bool',
        SafeConstructor.construct_yaml_bool)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:int',
        SafeConstructor.construct_yaml_int)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:float',
        SafeConstructor.construct_yaml_float)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:binary',
        SafeConstructor.construct_yaml_binary)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:timestamp',
        SafeConstructor.construct_yaml_timestamp)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:omap',
        SafeConstructor.construct_yaml_omap)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:pairs',
        SafeConstructor.construct_yaml_pairs)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:set',
        SafeConstructor.construct_yaml_set)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:str',
        SafeConstructor.construct_yaml_str)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:seq',
        SafeConstructor.construct_yaml_seq)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:map',
        SafeConstructor.construct_yaml_map)

SafeConstructor.add_constructor(None,
        SafeConstructor.construct_undefined)

class Constructor(SafeConstructor):

    def construct_python_str(self, node):
        return self.construct_scalar(node).encode('utf-8')

    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

    def construct_python_long(self, node):
        return long(self.construct_yaml_int(node))

    def construct_python_complex(self, node):
       return complex(self.construct_scalar(node))

    def construct_python_tuple(self, node):
        return tuple(self.construct_sequence(node))

    def find_python_module(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python module", mark,
                    "expected non-empty name appended to the tag", mark)
        try:
            __import__(name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python module", mark,
                    "cannot find module %r (%s)" % (name.encode('utf-8'), exc), mark)
        return sys.modules[name]

    def find_python_name(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python object", mark,
                    "expected non-empty name appended to the tag", mark)
        if u'.' in name:
            module_name, object_name = name.rsplit('.', 1)
        else:
            module_name = '__builtin__'
            object_name = name
        try:
            __import__(module_name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find module %r (%s)" % (module_name.encode('utf-8'), exc), mark)
        module = sys.modules[module_name]
        if not hasattr(module, object_name):
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find %r in the module %r" % (object_name.encode('utf-8'),
                        module.__name__), mark)
        return getattr(module, object_name)

    def construct_python_name(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python name", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_name(suffix, node.start_mark)

    def construct_python_module(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python module", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_module(suffix, node.start_mark)

    class classobj: pass

    def make_python_instance(self, suffix, node,
            args=None, kwds=None, newobj=False):
        if not args:
            args = []
        if not kwds:
            kwds = {}
        cls = self.find_python_name(suffix, node.start_mark)
        if newobj and isinstance(cls, type(self.classobj))  \
                and not args and not kwds:
            instance = self.classobj()
            instance.__class__ = cls
            return instance
        elif newobj and isinstance(cls, type):
            return cls.__new__(cls, *args, **kwds)
        else:
            return cls(*args, **kwds)

    def set_python_instance_state(self, instance, state):
        if hasattr(instance, '__setstate__'):
            instance.__setstate__(state)
        else:
            slotstate = {}
            if isinstance(state, tuple) and len(state) == 2:
                state, slotstate = state
            if hasattr(instance, '__dict__'):
                instance.__dict__.update(state)
            elif state:
                slotstate.update(state)
            for key, value in slotstate.items():
                setattr(object, key, value)

    def construct_python_object(self, suffix, node):
        # Format:
        #   !!python/object:module.name { ... state ... }
        instance = self.make_python_instance(suffix, node, newobj=True)
        yield instance
        deep = hasattr(instance, '__setstate__')
        state = self.construct_mapping(node, deep=deep)
        self.set_python_instance_state(instance, state)

    def construct_python_object_apply(self, suffix, node, newobj=False):
        # Format:
        #   !!python/object/apply       # (or !!python/object/new)
        #   args: [ ... arguments ... ]
        #   kwds: { ... keywords ... }
        #   state: ... state ...
        #   listitems: [ ... listitems ... ]
        #   dictitems: { ... dictitems ... }
        # or short format:
        #   !!python/object/apply [ ... arguments ... ]
        # The difference between !!python/object/apply and !!python/object/new
        # is how an object is created, check make_python_instance for details.
        if isinstance(node, SequenceNode):
            args = self.construct_sequence(node, deep=True)
            kwds = {}
            state = {}
            listitems = []
            dictitems = {}
        else:
            value = self.construct_mapping(node, deep=True)
            args = value.get('args', [])
            kwds = value.get('kwds', {})
            state = value.get('state', {})
            listitems = value.get('listitems', [])
            dictitems = value.get('dictitems', {})
        instance = self.make_python_instance(suffix, node, args, kwds, newobj)
        if state:
            self.set_python_instance_state(instance, state)
        if listitems:
            instance.extend(listitems)
        if dictitems:
            for key in dictitems:
                instance[key] = dictitems[key]
        return instance

    def construct_python_object_new(self, suffix, node):
        return self.construct_python_object_apply(suffix, node, newobj=True)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/none',
    Constructor.construct_yaml_null)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/bool',
    Constructor.construct_yaml_bool)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/str',
    Constructor.construct_python_str)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/unicode',
    Constructor.construct_python_unicode)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/int',
    Constructor.construct_yaml_int)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/long',
    Constructor.construct_python_long)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/float',
    Constructor.construct_yaml_float)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/complex',
    Constructor.construct_python_complex)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/list',
    Constructor.construct_yaml_seq)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/tuple',
    Constructor.construct_python_tuple)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/dict',
    Constructor.construct_yaml_map)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/name:',
    Constructor.construct_python_name)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/module:',
    Constructor.construct_python_module)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object:',
    Constructor.construct_python_object)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/apply:',
    Constructor.construct_python_object_apply)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/new:',
    Constructor.construct_python_object_new)


########NEW FILE########
__FILENAME__ = cyaml

__all__ = ['CBaseLoader', 'CSafeLoader', 'CLoader',
        'CBaseDumper', 'CSafeDumper', 'CDumper']

from _yaml import CParser, CEmitter

from constructor import *

from serializer import *
from representer import *

from resolver import *

class CBaseLoader(CParser, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class CSafeLoader(CParser, SafeConstructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class CLoader(CParser, Constructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        Constructor.__init__(self)
        Resolver.__init__(self)

class CBaseDumper(CEmitter, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CSafeDumper(CEmitter, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CDumper(CEmitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = dumper

__all__ = ['BaseDumper', 'SafeDumper', 'Dumper']

from emitter import *
from serializer import *
from representer import *
from resolver import *

class BaseDumper(Emitter, Serializer, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class SafeDumper(Emitter, Serializer, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class Dumper(Emitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = emitter

# Emitter expects events obeying the following grammar:
# stream ::= STREAM-START document* STREAM-END
# document ::= DOCUMENT-START node DOCUMENT-END
# node ::= SCALAR | sequence | mapping
# sequence ::= SEQUENCE-START node* SEQUENCE-END
# mapping ::= MAPPING-START (node node)* MAPPING-END

__all__ = ['Emitter', 'EmitterError']

from error import YAMLError
from events import *

class EmitterError(YAMLError):
    pass

class ScalarAnalysis(object):
    def __init__(self, scalar, empty, multiline,
            allow_flow_plain, allow_block_plain,
            allow_single_quoted, allow_double_quoted,
            allow_block):
        self.scalar = scalar
        self.empty = empty
        self.multiline = multiline
        self.allow_flow_plain = allow_flow_plain
        self.allow_block_plain = allow_block_plain
        self.allow_single_quoted = allow_single_quoted
        self.allow_double_quoted = allow_double_quoted
        self.allow_block = allow_block

class Emitter(object):

    DEFAULT_TAG_PREFIXES = {
        u'!' : u'!',
        u'tag:yaml.org,2002:' : u'!!',
    }

    def __init__(self, stream, canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None):

        # The stream should have the methods `write` and possibly `flush`.
        self.stream = stream

        # Encoding can be overriden by STREAM-START.
        self.encoding = None

        # Emitter is a state machine with a stack of states to handle nested
        # structures.
        self.states = []
        self.state = self.expect_stream_start

        # Current event and the event queue.
        self.events = []
        self.event = None

        # The current indentation level and the stack of previous indents.
        self.indents = []
        self.indent = None

        # Flow level.
        self.flow_level = 0

        # Contexts.
        self.root_context = False
        self.sequence_context = False
        self.mapping_context = False
        self.simple_key_context = False

        # Characteristics of the last emitted character:
        #  - current position.
        #  - is it a whitespace?
        #  - is it an indention character
        #    (indentation space, '-', '?', or ':')?
        self.line = 0
        self.column = 0
        self.whitespace = True
        self.indention = True

        # Whether the document requires an explicit document indicator
        self.open_ended = False

        # Formatting details.
        self.canonical = canonical
        self.allow_unicode = allow_unicode
        self.best_indent = 2
        if indent and 1 < indent < 10:
            self.best_indent = indent
        self.best_width = 80
        if width and width > self.best_indent*2:
            self.best_width = width
        self.best_line_break = u'\n'
        if line_break in [u'\r', u'\n', u'\r\n']:
            self.best_line_break = line_break

        # Tag prefixes.
        self.tag_prefixes = None

        # Prepared anchor and tag.
        self.prepared_anchor = None
        self.prepared_tag = None

        # Scalar analysis and style.
        self.analysis = None
        self.style = None

    def dispose(self):
        # Reset the state attributes (to clear self-references)
        self.states = []
        self.state = None

    def emit(self, event):
        self.events.append(event)
        while not self.need_more_events():
            self.event = self.events.pop(0)
            self.state()
            self.event = None

    # In some cases, we wait for a few next events before emitting.

    def need_more_events(self):
        if not self.events:
            return True
        event = self.events[0]
        if isinstance(event, DocumentStartEvent):
            return self.need_events(1)
        elif isinstance(event, SequenceStartEvent):
            return self.need_events(2)
        elif isinstance(event, MappingStartEvent):
            return self.need_events(3)
        else:
            return False

    def need_events(self, count):
        level = 0
        for event in self.events[1:]:
            if isinstance(event, (DocumentStartEvent, CollectionStartEvent)):
                level += 1
            elif isinstance(event, (DocumentEndEvent, CollectionEndEvent)):
                level -= 1
            elif isinstance(event, StreamEndEvent):
                level = -1
            if level < 0:
                return False
        return (len(self.events) < count+1)

    def increase_indent(self, flow=False, indentless=False):
        self.indents.append(self.indent)
        if self.indent is None:
            if flow:
                self.indent = self.best_indent
            else:
                self.indent = 0
        elif not indentless:
            self.indent += self.best_indent

    # States.

    # Stream handlers.

    def expect_stream_start(self):
        if isinstance(self.event, StreamStartEvent):
            if self.event.encoding and not getattr(self.stream, 'encoding', None):
                self.encoding = self.event.encoding
            self.write_stream_start()
            self.state = self.expect_first_document_start
        else:
            raise EmitterError("expected StreamStartEvent, but got %s"
                    % self.event)

    def expect_nothing(self):
        raise EmitterError("expected nothing, but got %s" % self.event)

    # Document handlers.

    def expect_first_document_start(self):
        return self.expect_document_start(first=True)

    def expect_document_start(self, first=False):
        if isinstance(self.event, DocumentStartEvent):
            if (self.event.version or self.event.tags) and self.open_ended:
                self.write_indicator(u'...', True)
                self.write_indent()
            if self.event.version:
                version_text = self.prepare_version(self.event.version)
                self.write_version_directive(version_text)
            self.tag_prefixes = self.DEFAULT_TAG_PREFIXES.copy()
            if self.event.tags:
                handles = self.event.tags.keys()
                handles.sort()
                for handle in handles:
                    prefix = self.event.tags[handle]
                    self.tag_prefixes[prefix] = handle
                    handle_text = self.prepare_tag_handle(handle)
                    prefix_text = self.prepare_tag_prefix(prefix)
                    self.write_tag_directive(handle_text, prefix_text)
            implicit = (first and not self.event.explicit and not self.canonical
                    and not self.event.version and not self.event.tags
                    and not self.check_empty_document())
            if not implicit:
                self.write_indent()
                self.write_indicator(u'---', True)
                if self.canonical:
                    self.write_indent()
            self.state = self.expect_document_root
        elif isinstance(self.event, StreamEndEvent):
            if self.open_ended:
                self.write_indicator(u'...', True)
                self.write_indent()
            self.write_stream_end()
            self.state = self.expect_nothing
        else:
            raise EmitterError("expected DocumentStartEvent, but got %s"
                    % self.event)

    def expect_document_end(self):
        if isinstance(self.event, DocumentEndEvent):
            self.write_indent()
            if self.event.explicit:
                self.write_indicator(u'...', True)
                self.write_indent()
            self.flush_stream()
            self.state = self.expect_document_start
        else:
            raise EmitterError("expected DocumentEndEvent, but got %s"
                    % self.event)

    def expect_document_root(self):
        self.states.append(self.expect_document_end)
        self.expect_node(root=True)

    # Node handlers.

    def expect_node(self, root=False, sequence=False, mapping=False,
            simple_key=False):
        self.root_context = root
        self.sequence_context = sequence
        self.mapping_context = mapping
        self.simple_key_context = simple_key
        if isinstance(self.event, AliasEvent):
            self.expect_alias()
        elif isinstance(self.event, (ScalarEvent, CollectionStartEvent)):
            self.process_anchor(u'&')
            self.process_tag()
            if isinstance(self.event, ScalarEvent):
                self.expect_scalar()
            elif isinstance(self.event, SequenceStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_sequence():
                    self.expect_flow_sequence()
                else:
                    self.expect_block_sequence()
            elif isinstance(self.event, MappingStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_mapping():
                    self.expect_flow_mapping()
                else:
                    self.expect_block_mapping()
        else:
            raise EmitterError("expected NodeEvent, but got %s" % self.event)

    def expect_alias(self):
        if self.event.anchor is None:
            raise EmitterError("anchor is not specified for alias")
        self.process_anchor(u'*')
        self.state = self.states.pop()

    def expect_scalar(self):
        self.increase_indent(flow=True)
        self.process_scalar()
        self.indent = self.indents.pop()
        self.state = self.states.pop()

    # Flow sequence handlers.

    def expect_flow_sequence(self):
        self.write_indicator(u'[', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_sequence_item

    def expect_first_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(u']', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    def expect_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(u',', False)
                self.write_indent()
            self.write_indicator(u']', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(u',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    # Flow mapping handlers.

    def expect_flow_mapping(self):
        self.write_indicator(u'{', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_mapping_key

    def expect_first_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(u'}', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(u',', False)
                self.write_indent()
            self.write_indicator(u'}', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(u',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_simple_value(self):
        self.write_indicator(u':', False)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    def expect_flow_mapping_value(self):
        if self.canonical or self.column > self.best_width:
            self.write_indent()
        self.write_indicator(u':', True)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    # Block sequence handlers.

    def expect_block_sequence(self):
        indentless = (self.mapping_context and not self.indention)
        self.increase_indent(flow=False, indentless=indentless)
        self.state = self.expect_first_block_sequence_item

    def expect_first_block_sequence_item(self):
        return self.expect_block_sequence_item(first=True)

    def expect_block_sequence_item(self, first=False):
        if not first and isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            self.write_indicator(u'-', True, indention=True)
            self.states.append(self.expect_block_sequence_item)
            self.expect_node(sequence=True)

    # Block mapping handlers.

    def expect_block_mapping(self):
        self.increase_indent(flow=False)
        self.state = self.expect_first_block_mapping_key

    def expect_first_block_mapping_key(self):
        return self.expect_block_mapping_key(first=True)

    def expect_block_mapping_key(self, first=False):
        if not first and isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            if self.check_simple_key():
                self.states.append(self.expect_block_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True, indention=True)
                self.states.append(self.expect_block_mapping_value)
                self.expect_node(mapping=True)

    def expect_block_mapping_simple_value(self):
        self.write_indicator(u':', False)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    def expect_block_mapping_value(self):
        self.write_indent()
        self.write_indicator(u':', True, indention=True)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    # Checkers.

    def check_empty_sequence(self):
        return (isinstance(self.event, SequenceStartEvent) and self.events
                and isinstance(self.events[0], SequenceEndEvent))

    def check_empty_mapping(self):
        return (isinstance(self.event, MappingStartEvent) and self.events
                and isinstance(self.events[0], MappingEndEvent))

    def check_empty_document(self):
        if not isinstance(self.event, DocumentStartEvent) or not self.events:
            return False
        event = self.events[0]
        return (isinstance(event, ScalarEvent) and event.anchor is None
                and event.tag is None and event.implicit and event.value == u'')

    def check_simple_key(self):
        length = 0
        if isinstance(self.event, NodeEvent) and self.event.anchor is not None:
            if self.prepared_anchor is None:
                self.prepared_anchor = self.prepare_anchor(self.event.anchor)
            length += len(self.prepared_anchor)
        if isinstance(self.event, (ScalarEvent, CollectionStartEvent))  \
                and self.event.tag is not None:
            if self.prepared_tag is None:
                self.prepared_tag = self.prepare_tag(self.event.tag)
            length += len(self.prepared_tag)
        if isinstance(self.event, ScalarEvent):
            if self.analysis is None:
                self.analysis = self.analyze_scalar(self.event.value)
            length += len(self.analysis.scalar)
        return (length < 128 and (isinstance(self.event, AliasEvent)
            or (isinstance(self.event, ScalarEvent)
                    and not self.analysis.empty and not self.analysis.multiline)
            or self.check_empty_sequence() or self.check_empty_mapping()))

    # Anchor, Tag, and Scalar processors.

    def process_anchor(self, indicator):
        if self.event.anchor is None:
            self.prepared_anchor = None
            return
        if self.prepared_anchor is None:
            self.prepared_anchor = self.prepare_anchor(self.event.anchor)
        if self.prepared_anchor:
            self.write_indicator(indicator+self.prepared_anchor, True)
        self.prepared_anchor = None

    def process_tag(self):
        tag = self.event.tag
        if isinstance(self.event, ScalarEvent):
            if self.style is None:
                self.style = self.choose_scalar_style()
            if ((not self.canonical or tag is None) and
                ((self.style == '' and self.event.implicit[0])
                        or (self.style != '' and self.event.implicit[1]))):
                self.prepared_tag = None
                return
            if self.event.implicit[0] and tag is None:
                tag = u'!'
                self.prepared_tag = None
        else:
            if (not self.canonical or tag is None) and self.event.implicit:
                self.prepared_tag = None
                return
        if tag is None:
            raise EmitterError("tag is not specified")
        if self.prepared_tag is None:
            self.prepared_tag = self.prepare_tag(tag)
        if self.prepared_tag:
            self.write_indicator(self.prepared_tag, True)
        self.prepared_tag = None

    def choose_scalar_style(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.event.style == '"' or self.canonical:
            return '"'
        if not self.event.style and self.event.implicit[0]:
            if (not (self.simple_key_context and
                    (self.analysis.empty or self.analysis.multiline))
                and (self.flow_level and self.analysis.allow_flow_plain
                    or (not self.flow_level and self.analysis.allow_block_plain))):
                return ''
        if self.event.style and self.event.style in '|>':
            if (not self.flow_level and not self.simple_key_context
                    and self.analysis.allow_block):
                return self.event.style
        if not self.event.style or self.event.style == '\'':
            if (self.analysis.allow_single_quoted and
                    not (self.simple_key_context and self.analysis.multiline)):
                return '\''
        return '"'

    def process_scalar(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.style is None:
            self.style = self.choose_scalar_style()
        split = (not self.simple_key_context)
        #if self.analysis.multiline and split    \
        #        and (not self.style or self.style in '\'\"'):
        #    self.write_indent()
        if self.style == '"':
            self.write_double_quoted(self.analysis.scalar, split)
        elif self.style == '\'':
            self.write_single_quoted(self.analysis.scalar, split)
        elif self.style == '>':
            self.write_folded(self.analysis.scalar)
        elif self.style == '|':
            self.write_literal(self.analysis.scalar)
        else:
            self.write_plain(self.analysis.scalar, split)
        self.analysis = None
        self.style = None

    # Analyzers.

    def prepare_version(self, version):
        major, minor = version
        if major != 1:
            raise EmitterError("unsupported YAML version: %d.%d" % (major, minor))
        return u'%d.%d' % (major, minor)

    def prepare_tag_handle(self, handle):
        if not handle:
            raise EmitterError("tag handle must not be empty")
        if handle[0] != u'!' or handle[-1] != u'!':
            raise EmitterError("tag handle must start and end with '!': %r"
                    % (handle.encode('utf-8')))
        for ch in handle[1:-1]:
            if not (u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'  \
                    or ch in u'-_'):
                raise EmitterError("invalid character %r in the tag handle: %r"
                        % (ch.encode('utf-8'), handle.encode('utf-8')))
        return handle

    def prepare_tag_prefix(self, prefix):
        if not prefix:
            raise EmitterError("tag prefix must not be empty")
        chunks = []
        start = end = 0
        if prefix[0] == u'!':
            end = 1
        while end < len(prefix):
            ch = prefix[end]
            if u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'   \
                    or ch in u'-;/?!:@&=+$,_.~*\'()[]':
                end += 1
            else:
                if start < end:
                    chunks.append(prefix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append(u'%%%02X' % ord(ch))
        if start < end:
            chunks.append(prefix[start:end])
        return u''.join(chunks)

    def prepare_tag(self, tag):
        if not tag:
            raise EmitterError("tag must not be empty")
        if tag == u'!':
            return tag
        handle = None
        suffix = tag
        prefixes = self.tag_prefixes.keys()
        prefixes.sort()
        for prefix in prefixes:
            if tag.startswith(prefix)   \
                    and (prefix == u'!' or len(prefix) < len(tag)):
                handle = self.tag_prefixes[prefix]
                suffix = tag[len(prefix):]
        chunks = []
        start = end = 0
        while end < len(suffix):
            ch = suffix[end]
            if u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'   \
                    or ch in u'-;/?:@&=+$,_.~*\'()[]'   \
                    or (ch == u'!' and handle != u'!'):
                end += 1
            else:
                if start < end:
                    chunks.append(suffix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append(u'%%%02X' % ord(ch))
        if start < end:
            chunks.append(suffix[start:end])
        suffix_text = u''.join(chunks)
        if handle:
            return u'%s%s' % (handle, suffix_text)
        else:
            return u'!<%s>' % suffix_text

    def prepare_anchor(self, anchor):
        if not anchor:
            raise EmitterError("anchor must not be empty")
        for ch in anchor:
            if not (u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'  \
                    or ch in u'-_'):
                raise EmitterError("invalid character %r in the anchor: %r"
                        % (ch.encode('utf-8'), anchor.encode('utf-8')))
        return anchor

    def analyze_scalar(self, scalar):

        # Empty scalar is a special case.
        if not scalar:
            return ScalarAnalysis(scalar=scalar, empty=True, multiline=False,
                    allow_flow_plain=False, allow_block_plain=True,
                    allow_single_quoted=True, allow_double_quoted=True,
                    allow_block=False)

        # Indicators and special characters.
        block_indicators = False
        flow_indicators = False
        line_breaks = False
        special_characters = False

        # Important whitespace combinations.
        leading_space = False
        leading_break = False
        trailing_space = False
        trailing_break = False
        break_space = False
        space_break = False

        # Check document indicators.
        if scalar.startswith(u'---') or scalar.startswith(u'...'):
            block_indicators = True
            flow_indicators = True

        # First character or preceded by a whitespace.
        preceeded_by_whitespace = True

        # Last character or followed by a whitespace.
        followed_by_whitespace = (len(scalar) == 1 or
                scalar[1] in u'\0 \t\r\n\x85\u2028\u2029')

        # The previous character is a space.
        previous_space = False

        # The previous character is a break.
        previous_break = False

        index = 0
        while index < len(scalar):
            ch = scalar[index]

            # Check for indicators.
            if index == 0:
                # Leading indicators are special characters.
                if ch in u'#,[]{}&*!|>\'\"%@`': 
                    flow_indicators = True
                    block_indicators = True
                if ch in u'?:':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == u'-' and followed_by_whitespace:
                    flow_indicators = True
                    block_indicators = True
            else:
                # Some indicators cannot appear within a scalar as well.
                if ch in u',?[]{}':
                    flow_indicators = True
                if ch == u':':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == u'#' and preceeded_by_whitespace:
                    flow_indicators = True
                    block_indicators = True

            # Check for line breaks, special, and unicode characters.
            if ch in u'\n\x85\u2028\u2029':
                line_breaks = True
            if not (ch == u'\n' or u'\x20' <= ch <= u'\x7E'):
                if (ch == u'\x85' or u'\xA0' <= ch <= u'\uD7FF'
                        or u'\uE000' <= ch <= u'\uFFFD') and ch != u'\uFEFF':
                    unicode_characters = True
                    if not self.allow_unicode:
                        special_characters = True
                else:
                    special_characters = True

            # Detect important whitespace combinations.
            if ch == u' ':
                if index == 0:
                    leading_space = True
                if index == len(scalar)-1:
                    trailing_space = True
                if previous_break:
                    break_space = True
                previous_space = True
                previous_break = False
            elif ch in u'\n\x85\u2028\u2029':
                if index == 0:
                    leading_break = True
                if index == len(scalar)-1:
                    trailing_break = True
                if previous_space:
                    space_break = True
                previous_space = False
                previous_break = True
            else:
                previous_space = False
                previous_break = False

            # Prepare for the next character.
            index += 1
            preceeded_by_whitespace = (ch in u'\0 \t\r\n\x85\u2028\u2029')
            followed_by_whitespace = (index+1 >= len(scalar) or
                    scalar[index+1] in u'\0 \t\r\n\x85\u2028\u2029')

        # Let's decide what styles are allowed.
        allow_flow_plain = True
        allow_block_plain = True
        allow_single_quoted = True
        allow_double_quoted = True
        allow_block = True

        # Leading and trailing whitespaces are bad for plain scalars.
        if (leading_space or leading_break
                or trailing_space or trailing_break):
            allow_flow_plain = allow_block_plain = False

        # We do not permit trailing spaces for block scalars.
        if trailing_space:
            allow_block = False

        # Spaces at the beginning of a new line are only acceptable for block
        # scalars.
        if break_space:
            allow_flow_plain = allow_block_plain = allow_single_quoted = False

        # Spaces followed by breaks, as well as special character are only
        # allowed for double quoted scalars.
        if space_break or special_characters:
            allow_flow_plain = allow_block_plain =  \
            allow_single_quoted = allow_block = False

        # Although the plain scalar writer supports breaks, we never emit
        # multiline plain scalars.
        if line_breaks:
            allow_flow_plain = allow_block_plain = False

        # Flow indicators are forbidden for flow plain scalars.
        if flow_indicators:
            allow_flow_plain = False

        # Block indicators are forbidden for block plain scalars.
        if block_indicators:
            allow_block_plain = False

        return ScalarAnalysis(scalar=scalar,
                empty=False, multiline=line_breaks,
                allow_flow_plain=allow_flow_plain,
                allow_block_plain=allow_block_plain,
                allow_single_quoted=allow_single_quoted,
                allow_double_quoted=allow_double_quoted,
                allow_block=allow_block)

    # Writers.

    def flush_stream(self):
        if hasattr(self.stream, 'flush'):
            self.stream.flush()

    def write_stream_start(self):
        # Write BOM if needed.
        if self.encoding and self.encoding.startswith('utf-16'):
            self.stream.write(u'\uFEFF'.encode(self.encoding))

    def write_stream_end(self):
        self.flush_stream()

    def write_indicator(self, indicator, need_whitespace,
            whitespace=False, indention=False):
        if self.whitespace or not need_whitespace:
            data = indicator
        else:
            data = u' '+indicator
        self.whitespace = whitespace
        self.indention = self.indention and indention
        self.column += len(data)
        self.open_ended = False
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_indent(self):
        indent = self.indent or 0
        if not self.indention or self.column > indent   \
                or (self.column == indent and not self.whitespace):
            self.write_line_break()
        if self.column < indent:
            self.whitespace = True
            data = u' '*(indent-self.column)
            self.column = indent
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)

    def write_line_break(self, data=None):
        if data is None:
            data = self.best_line_break
        self.whitespace = True
        self.indention = True
        self.line += 1
        self.column = 0
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_version_directive(self, version_text):
        data = u'%%YAML %s' % version_text
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    def write_tag_directive(self, handle_text, prefix_text):
        data = u'%%TAG %s %s' % (handle_text, prefix_text)
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    # Scalar streams.

    def write_single_quoted(self, text, split=True):
        self.write_indicator(u'\'', True)
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch is None or ch != u' ':
                    if start+1 == end and self.column > self.best_width and split   \
                            and start != 0 and end != len(text):
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    if text[start] == u'\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029' or ch == u'\'':
                    if start < end:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                        start = end
            if ch == u'\'':
                data = u'\'\''
                self.column += 2
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                start = end + 1
            if ch is not None:
                spaces = (ch == u' ')
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1
        self.write_indicator(u'\'', False)

    ESCAPE_REPLACEMENTS = {
        u'\0':      u'0',
        u'\x07':    u'a',
        u'\x08':    u'b',
        u'\x09':    u't',
        u'\x0A':    u'n',
        u'\x0B':    u'v',
        u'\x0C':    u'f',
        u'\x0D':    u'r',
        u'\x1B':    u'e',
        u'\"':      u'\"',
        u'\\':      u'\\',
        u'\x85':    u'N',
        u'\xA0':    u'_',
        u'\u2028':  u'L',
        u'\u2029':  u'P',
    }

    def write_double_quoted(self, text, split=True):
        self.write_indicator(u'"', True)
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if ch is None or ch in u'"\\\x85\u2028\u2029\uFEFF' \
                    or not (u'\x20' <= ch <= u'\x7E'
                        or (self.allow_unicode
                            and (u'\xA0' <= ch <= u'\uD7FF'
                                or u'\uE000' <= ch <= u'\uFFFD'))):
                if start < end:
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
                if ch is not None:
                    if ch in self.ESCAPE_REPLACEMENTS:
                        data = u'\\'+self.ESCAPE_REPLACEMENTS[ch]
                    elif ch <= u'\xFF':
                        data = u'\\x%02X' % ord(ch)
                    elif ch <= u'\uFFFF':
                        data = u'\\u%04X' % ord(ch)
                    else:
                        data = u'\\U%08X' % ord(ch)
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end+1
            if 0 < end < len(text)-1 and (ch == u' ' or start >= end)   \
                    and self.column+(end-start) > self.best_width and split:
                data = text[start:end]+u'\\'
                if start < end:
                    start = end
                self.column += len(data)
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                self.write_indent()
                self.whitespace = False
                self.indention = False
                if text[start] == u' ':
                    data = u'\\'
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
            end += 1
        self.write_indicator(u'"', False)

    def determine_block_hints(self, text):
        hints = u''
        if text:
            if text[0] in u' \n\x85\u2028\u2029':
                hints += unicode(self.best_indent)
            if text[-1] not in u'\n\x85\u2028\u2029':
                hints += u'-'
            elif len(text) == 1 or text[-2] in u'\n\x85\u2028\u2029':
                hints += u'+'
        return hints

    def write_folded(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator(u'>'+hints, True)
        if hints[-1:] == u'+':
            self.open_ended = True
        self.write_line_break()
        leading_space = True
        spaces = False
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    if not leading_space and ch is not None and ch != u' '  \
                            and text[start] == u'\n':
                        self.write_line_break()
                    leading_space = (ch == u' ')
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            elif spaces:
                if ch != u' ':
                    if start+1 == end and self.column > self.best_width:
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in u'\n\x85\u2028\u2029')
                spaces = (ch == u' ')
            end += 1

    def write_literal(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator(u'|'+hints, True)
        if hints[-1:] == u'+':
            self.open_ended = True
        self.write_line_break()
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            else:
                if ch is None or ch in u'\n\x85\u2028\u2029':
                    data = text[start:end]
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1

    def write_plain(self, text, split=True):
        if self.root_context:
            self.open_ended = True
        if not text:
            return
        if not self.whitespace:
            data = u' '
            self.column += len(data)
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)
        self.whitespace = False
        self.indention = False
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch != u' ':
                    if start+1 == end and self.column > self.best_width and split:
                        self.write_indent()
                        self.whitespace = False
                        self.indention = False
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch not in u'\n\x85\u2028\u2029':
                    if text[start] == u'\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    self.whitespace = False
                    self.indention = False
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
            if ch is not None:
                spaces = (ch == u' ')
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1


########NEW FILE########
__FILENAME__ = error

__all__ = ['Mark', 'YAMLError', 'MarkedYAMLError']

class Mark(object):

    def __init__(self, name, index, line, column, buffer, pointer):
        self.name = name
        self.index = index
        self.line = line
        self.column = column
        self.buffer = buffer
        self.pointer = pointer

    def get_snippet(self, indent=4, max_length=75):
        if self.buffer is None:
            return None
        head = ''
        start = self.pointer
        while start > 0 and self.buffer[start-1] not in u'\0\r\n\x85\u2028\u2029':
            start -= 1
            if self.pointer-start > max_length/2-1:
                head = ' ... '
                start += 5
                break
        tail = ''
        end = self.pointer
        while end < len(self.buffer) and self.buffer[end] not in u'\0\r\n\x85\u2028\u2029':
            end += 1
            if end-self.pointer > max_length/2-1:
                tail = ' ... '
                end -= 5
                break
        snippet = self.buffer[start:end].encode('utf-8')
        return ' '*indent + head + snippet + tail + '\n'  \
                + ' '*(indent+self.pointer-start+len(head)) + '^'

    def __str__(self):
        snippet = self.get_snippet()
        where = "  in \"%s\", line %d, column %d"   \
                % (self.name, self.line+1, self.column+1)
        if snippet is not None:
            where += ":\n"+snippet
        return where

class YAMLError(Exception):
    pass

class MarkedYAMLError(YAMLError):

    def __init__(self, context=None, context_mark=None,
            problem=None, problem_mark=None, note=None):
        self.context = context
        self.context_mark = context_mark
        self.problem = problem
        self.problem_mark = problem_mark
        self.note = note

    def __str__(self):
        lines = []
        if self.context is not None:
            lines.append(self.context)
        if self.context_mark is not None  \
            and (self.problem is None or self.problem_mark is None
                    or self.context_mark.name != self.problem_mark.name
                    or self.context_mark.line != self.problem_mark.line
                    or self.context_mark.column != self.problem_mark.column):
            lines.append(str(self.context_mark))
        if self.problem is not None:
            lines.append(self.problem)
        if self.problem_mark is not None:
            lines.append(str(self.problem_mark))
        if self.note is not None:
            lines.append(self.note)
        return '\n'.join(lines)


########NEW FILE########
__FILENAME__ = events

# Abstract classes.

class Event(object):
    def __init__(self, start_mark=None, end_mark=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in ['anchor', 'tag', 'implicit', 'value']
                if hasattr(self, key)]
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

class NodeEvent(Event):
    def __init__(self, anchor, start_mark=None, end_mark=None):
        self.anchor = anchor
        self.start_mark = start_mark
        self.end_mark = end_mark

class CollectionStartEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, start_mark=None, end_mark=None,
            flow_style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class CollectionEndEvent(Event):
    pass

# Implementations.

class StreamStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None, encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndEvent(Event):
    pass

class DocumentStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None, version=None, tags=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit
        self.version = version
        self.tags = tags

class DocumentEndEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit

class AliasEvent(NodeEvent):
    pass

class ScalarEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, value,
            start_mark=None, end_mark=None, style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class SequenceStartEvent(CollectionStartEvent):
    pass

class SequenceEndEvent(CollectionEndEvent):
    pass

class MappingStartEvent(CollectionStartEvent):
    pass

class MappingEndEvent(CollectionEndEvent):
    pass


########NEW FILE########
__FILENAME__ = loader

__all__ = ['BaseLoader', 'SafeLoader', 'Loader']

from reader import *
from scanner import *
from parser import *
from composer import *
from constructor import *
from resolver import *

class BaseLoader(Reader, Scanner, Parser, Composer, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class SafeLoader(Reader, Scanner, Parser, Composer, SafeConstructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        Constructor.__init__(self)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = nodes

class Node(object):
    def __init__(self, tag, value, start_mark, end_mark):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        value = self.value
        #if isinstance(value, list):
        #    if len(value) == 0:
        #        value = '<empty>'
        #    elif len(value) == 1:
        #        value = '<1 item>'
        #    else:
        #        value = '<%d items>' % len(value)
        #else:
        #    if len(value) > 75:
        #        value = repr(value[:70]+u' ... ')
        #    else:
        #        value = repr(value)
        value = repr(value)
        return '%s(tag=%r, value=%s)' % (self.__class__.__name__, self.tag, value)

class ScalarNode(Node):
    id = 'scalar'
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class CollectionNode(Node):
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, flow_style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class SequenceNode(CollectionNode):
    id = 'sequence'

class MappingNode(CollectionNode):
    id = 'mapping'


########NEW FILE########
__FILENAME__ = parser

# The following YAML grammar is LL(1) and is parsed by a recursive descent
# parser.
#
# stream            ::= STREAM-START implicit_document? explicit_document* STREAM-END
# implicit_document ::= block_node DOCUMENT-END*
# explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*
# block_node_or_indentless_sequence ::=
#                       ALIAS
#                       | properties (block_content | indentless_block_sequence)?
#                       | block_content
#                       | indentless_block_sequence
# block_node        ::= ALIAS
#                       | properties block_content?
#                       | block_content
# flow_node         ::= ALIAS
#                       | properties flow_content?
#                       | flow_content
# properties        ::= TAG ANCHOR? | ANCHOR TAG?
# block_content     ::= block_collection | flow_collection | SCALAR
# flow_content      ::= flow_collection | SCALAR
# block_collection  ::= block_sequence | block_mapping
# flow_collection   ::= flow_sequence | flow_mapping
# block_sequence    ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END
# indentless_sequence   ::= (BLOCK-ENTRY block_node?)+
# block_mapping     ::= BLOCK-MAPPING_START
#                       ((KEY block_node_or_indentless_sequence?)?
#                       (VALUE block_node_or_indentless_sequence?)?)*
#                       BLOCK-END
# flow_sequence     ::= FLOW-SEQUENCE-START
#                       (flow_sequence_entry FLOW-ENTRY)*
#                       flow_sequence_entry?
#                       FLOW-SEQUENCE-END
# flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
# flow_mapping      ::= FLOW-MAPPING-START
#                       (flow_mapping_entry FLOW-ENTRY)*
#                       flow_mapping_entry?
#                       FLOW-MAPPING-END
# flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?
#
# FIRST sets:
#
# stream: { STREAM-START }
# explicit_document: { DIRECTIVE DOCUMENT-START }
# implicit_document: FIRST(block_node)
# block_node: { ALIAS TAG ANCHOR SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_node: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_content: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# flow_content: { FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# block_collection: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_sequence: { BLOCK-SEQUENCE-START }
# block_mapping: { BLOCK-MAPPING-START }
# block_node_or_indentless_sequence: { ALIAS ANCHOR TAG SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START BLOCK-ENTRY }
# indentless_sequence: { ENTRY }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_sequence: { FLOW-SEQUENCE-START }
# flow_mapping: { FLOW-MAPPING-START }
# flow_sequence_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }
# flow_mapping_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }

__all__ = ['Parser', 'ParserError']

from error import MarkedYAMLError
from tokens import *
from events import *
from scanner import *

class ParserError(MarkedYAMLError):
    pass

class Parser(object):
    # Since writing a recursive-descendant parser is a straightforward task, we
    # do not give many comments here.

    DEFAULT_TAGS = {
        u'!':   u'!',
        u'!!':  u'tag:yaml.org,2002:',
    }

    def __init__(self):
        self.current_event = None
        self.yaml_version = None
        self.tag_handles = {}
        self.states = []
        self.marks = []
        self.state = self.parse_stream_start

    def dispose(self):
        # Reset the state attributes (to clear self-references)
        self.states = []
        self.state = None

    def check_event(self, *choices):
        # Check the type of the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        if self.current_event is not None:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.current_event, choice):
                    return True
        return False

    def peek_event(self):
        # Get the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        return self.current_event

    def get_event(self):
        # Get the next event and proceed further.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        value = self.current_event
        self.current_event = None
        return value

    # stream    ::= STREAM-START implicit_document? explicit_document* STREAM-END
    # implicit_document ::= block_node DOCUMENT-END*
    # explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*

    def parse_stream_start(self):

        # Parse the stream start.
        token = self.get_token()
        event = StreamStartEvent(token.start_mark, token.end_mark,
                encoding=token.encoding)

        # Prepare the next state.
        self.state = self.parse_implicit_document_start

        return event

    def parse_implicit_document_start(self):

        # Parse an implicit document.
        if not self.check_token(DirectiveToken, DocumentStartToken,
                StreamEndToken):
            self.tag_handles = self.DEFAULT_TAGS
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=False)

            # Prepare the next state.
            self.states.append(self.parse_document_end)
            self.state = self.parse_block_node

            return event

        else:
            return self.parse_document_start()

    def parse_document_start(self):

        # Parse any extra document end indicators.
        while self.check_token(DocumentEndToken):
            self.get_token()

        # Parse an explicit document.
        if not self.check_token(StreamEndToken):
            token = self.peek_token()
            start_mark = token.start_mark
            version, tags = self.process_directives()
            if not self.check_token(DocumentStartToken):
                raise ParserError(None, None,
                        "expected '<document start>', but found %r"
                        % self.peek_token().id,
                        self.peek_token().start_mark)
            token = self.get_token()
            end_mark = token.end_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=True, version=version, tags=tags)
            self.states.append(self.parse_document_end)
            self.state = self.parse_document_content
        else:
            # Parse the end of the stream.
            token = self.get_token()
            event = StreamEndEvent(token.start_mark, token.end_mark)
            assert not self.states
            assert not self.marks
            self.state = None
        return event

    def parse_document_end(self):

        # Parse the document end.
        token = self.peek_token()
        start_mark = end_mark = token.start_mark
        explicit = False
        if self.check_token(DocumentEndToken):
            token = self.get_token()
            end_mark = token.end_mark
            explicit = True
        event = DocumentEndEvent(start_mark, end_mark,
                explicit=explicit)

        # Prepare the next state.
        self.state = self.parse_document_start

        return event

    def parse_document_content(self):
        if self.check_token(DirectiveToken,
                DocumentStartToken, DocumentEndToken, StreamEndToken):
            event = self.process_empty_scalar(self.peek_token().start_mark)
            self.state = self.states.pop()
            return event
        else:
            return self.parse_block_node()

    def process_directives(self):
        self.yaml_version = None
        self.tag_handles = {}
        while self.check_token(DirectiveToken):
            token = self.get_token()
            if token.name == u'YAML':
                if self.yaml_version is not None:
                    raise ParserError(None, None,
                            "found duplicate YAML directive", token.start_mark)
                major, minor = token.value
                if major != 1:
                    raise ParserError(None, None,
                            "found incompatible YAML document (version 1.* is required)",
                            token.start_mark)
                self.yaml_version = token.value
            elif token.name == u'TAG':
                handle, prefix = token.value
                if handle in self.tag_handles:
                    raise ParserError(None, None,
                            "duplicate tag handle %r" % handle.encode('utf-8'),
                            token.start_mark)
                self.tag_handles[handle] = prefix
        if self.tag_handles:
            value = self.yaml_version, self.tag_handles.copy()
        else:
            value = self.yaml_version, None
        for key in self.DEFAULT_TAGS:
            if key not in self.tag_handles:
                self.tag_handles[key] = self.DEFAULT_TAGS[key]
        return value

    # block_node_or_indentless_sequence ::= ALIAS
    #               | properties (block_content | indentless_block_sequence)?
    #               | block_content
    #               | indentless_block_sequence
    # block_node    ::= ALIAS
    #                   | properties block_content?
    #                   | block_content
    # flow_node     ::= ALIAS
    #                   | properties flow_content?
    #                   | flow_content
    # properties    ::= TAG ANCHOR? | ANCHOR TAG?
    # block_content     ::= block_collection | flow_collection | SCALAR
    # flow_content      ::= flow_collection | SCALAR
    # block_collection  ::= block_sequence | block_mapping
    # flow_collection   ::= flow_sequence | flow_mapping

    def parse_block_node(self):
        return self.parse_node(block=True)

    def parse_flow_node(self):
        return self.parse_node()

    def parse_block_node_or_indentless_sequence(self):
        return self.parse_node(block=True, indentless_sequence=True)

    def parse_node(self, block=False, indentless_sequence=False):
        if self.check_token(AliasToken):
            token = self.get_token()
            event = AliasEvent(token.value, token.start_mark, token.end_mark)
            self.state = self.states.pop()
        else:
            anchor = None
            tag = None
            start_mark = end_mark = tag_mark = None
            if self.check_token(AnchorToken):
                token = self.get_token()
                start_mark = token.start_mark
                end_mark = token.end_mark
                anchor = token.value
                if self.check_token(TagToken):
                    token = self.get_token()
                    tag_mark = token.start_mark
                    end_mark = token.end_mark
                    tag = token.value
            elif self.check_token(TagToken):
                token = self.get_token()
                start_mark = tag_mark = token.start_mark
                end_mark = token.end_mark
                tag = token.value
                if self.check_token(AnchorToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    anchor = token.value
            if tag is not None:
                handle, suffix = tag
                if handle is not None:
                    if handle not in self.tag_handles:
                        raise ParserError("while parsing a node", start_mark,
                                "found undefined tag handle %r" % handle.encode('utf-8'),
                                tag_mark)
                    tag = self.tag_handles[handle]+suffix
                else:
                    tag = suffix
            #if tag == u'!':
            #    raise ParserError("while parsing a node", start_mark,
            #            "found non-specific tag '!'", tag_mark,
            #            "Please check 'http://pyyaml.org/wiki/YAMLNonSpecificTag' and share your opinion.")
            if start_mark is None:
                start_mark = end_mark = self.peek_token().start_mark
            event = None
            implicit = (tag is None or tag == u'!')
            if indentless_sequence and self.check_token(BlockEntryToken):
                end_mark = self.peek_token().end_mark
                event = SequenceStartEvent(anchor, tag, implicit,
                        start_mark, end_mark)
                self.state = self.parse_indentless_sequence_entry
            else:
                if self.check_token(ScalarToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    if (token.plain and tag is None) or tag == u'!':
                        implicit = (True, False)
                    elif tag is None:
                        implicit = (False, True)
                    else:
                        implicit = (False, False)
                    event = ScalarEvent(anchor, tag, implicit, token.value,
                            start_mark, end_mark, style=token.style)
                    self.state = self.states.pop()
                elif self.check_token(FlowSequenceStartToken):
                    end_mark = self.peek_token().end_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_sequence_first_entry
                elif self.check_token(FlowMappingStartToken):
                    end_mark = self.peek_token().end_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_mapping_first_key
                elif block and self.check_token(BlockSequenceStartToken):
                    end_mark = self.peek_token().start_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_sequence_first_entry
                elif block and self.check_token(BlockMappingStartToken):
                    end_mark = self.peek_token().start_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_mapping_first_key
                elif anchor is not None or tag is not None:
                    # Empty scalars are allowed even if a tag or an anchor is
                    # specified.
                    event = ScalarEvent(anchor, tag, (implicit, False), u'',
                            start_mark, end_mark)
                    self.state = self.states.pop()
                else:
                    if block:
                        node = 'block'
                    else:
                        node = 'flow'
                    token = self.peek_token()
                    raise ParserError("while parsing a %s node" % node, start_mark,
                            "expected the node content, but found %r" % token.id,
                            token.start_mark)
        return event

    # block_sequence ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END

    def parse_block_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_sequence_entry()

    def parse_block_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken, BlockEndToken):
                self.states.append(self.parse_block_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_block_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block collection", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    # indentless_sequence ::= (BLOCK-ENTRY block_node?)+

    def parse_indentless_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken,
                    KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_indentless_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_indentless_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        token = self.peek_token()
        event = SequenceEndEvent(token.start_mark, token.start_mark)
        self.state = self.states.pop()
        return event

    # block_mapping     ::= BLOCK-MAPPING_START
    #                       ((KEY block_node_or_indentless_sequence?)?
    #                       (VALUE block_node_or_indentless_sequence?)?)*
    #                       BLOCK-END

    def parse_block_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_mapping_key()

    def parse_block_mapping_key(self):
        if self.check_token(KeyToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_value)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_value
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block mapping", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_block_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_key)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_block_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    # flow_sequence     ::= FLOW-SEQUENCE-START
    #                       (flow_sequence_entry FLOW-ENTRY)*
    #                       flow_sequence_entry?
    #                       FLOW-SEQUENCE-END
    # flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
    #
    # Note that while production rules for both flow_sequence_entry and
    # flow_mapping_entry are equal, their interpretations are different.
    # For `flow_sequence_entry`, the part `KEY flow_node? (VALUE flow_node?)?`
    # generate an inline mapping (set syntax).

    def parse_flow_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_sequence_entry(first=True)

    def parse_flow_sequence_entry(self, first=False):
        if not self.check_token(FlowSequenceEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow sequence", self.marks[-1],
                            "expected ',' or ']', but got %r" % token.id, token.start_mark)
            
            if self.check_token(KeyToken):
                token = self.peek_token()
                event = MappingStartEvent(None, None, True,
                        token.start_mark, token.end_mark,
                        flow_style=True)
                self.state = self.parse_flow_sequence_entry_mapping_key
                return event
            elif not self.check_token(FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry)
                return self.parse_flow_node()
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_sequence_entry_mapping_key(self):
        token = self.get_token()
        if not self.check_token(ValueToken,
                FlowEntryToken, FlowSequenceEndToken):
            self.states.append(self.parse_flow_sequence_entry_mapping_value)
            return self.parse_flow_node()
        else:
            self.state = self.parse_flow_sequence_entry_mapping_value
            return self.process_empty_scalar(token.end_mark)

    def parse_flow_sequence_entry_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry_mapping_end)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_sequence_entry_mapping_end
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_sequence_entry_mapping_end
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_sequence_entry_mapping_end(self):
        self.state = self.parse_flow_sequence_entry
        token = self.peek_token()
        return MappingEndEvent(token.start_mark, token.start_mark)

    # flow_mapping  ::= FLOW-MAPPING-START
    #                   (flow_mapping_entry FLOW-ENTRY)*
    #                   flow_mapping_entry?
    #                   FLOW-MAPPING-END
    # flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?

    def parse_flow_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_mapping_key(first=True)

    def parse_flow_mapping_key(self, first=False):
        if not self.check_token(FlowMappingEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow mapping", self.marks[-1],
                            "expected ',' or '}', but got %r" % token.id, token.start_mark)
            if self.check_token(KeyToken):
                token = self.get_token()
                if not self.check_token(ValueToken,
                        FlowEntryToken, FlowMappingEndToken):
                    self.states.append(self.parse_flow_mapping_value)
                    return self.parse_flow_node()
                else:
                    self.state = self.parse_flow_mapping_value
                    return self.process_empty_scalar(token.end_mark)
            elif not self.check_token(FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_empty_value)
                return self.parse_flow_node()
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_key)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_mapping_empty_value(self):
        self.state = self.parse_flow_mapping_key
        return self.process_empty_scalar(self.peek_token().start_mark)

    def process_empty_scalar(self, mark):
        return ScalarEvent(None, None, (True, False), u'', mark, mark)


########NEW FILE########
__FILENAME__ = reader
# This module contains abstractions for the input stream. You don't have to
# looks further, there are no pretty code.
#
# We define two classes here.
#
#   Mark(source, line, column)
# It's just a record and its only use is producing nice error messages.
# Parser does not use it for any other purposes.
#
#   Reader(source, data)
# Reader determines the encoding of `data` and converts it to unicode.
# Reader provides the following methods and attributes:
#   reader.peek(length=1) - return the next `length` characters
#   reader.forward(length=1) - move the current position to `length` characters.
#   reader.index - the number of the current character.
#   reader.line, stream.column - the line and the column of the current character.

__all__ = ['Reader', 'ReaderError']

from error import YAMLError, Mark

import codecs, re

class ReaderError(YAMLError):

    def __init__(self, name, position, character, encoding, reason):
        self.name = name
        self.character = character
        self.position = position
        self.encoding = encoding
        self.reason = reason

    def __str__(self):
        if isinstance(self.character, str):
            return "'%s' codec can't decode byte #x%02x: %s\n"  \
                    "  in \"%s\", position %d"    \
                    % (self.encoding, ord(self.character), self.reason,
                            self.name, self.position)
        else:
            return "unacceptable character #x%04x: %s\n"    \
                    "  in \"%s\", position %d"    \
                    % (self.character, self.reason,
                            self.name, self.position)

class Reader(object):
    # Reader:
    # - determines the data encoding and converts it to unicode,
    # - checks if characters are in allowed range,
    # - adds '\0' to the end.

    # Reader accepts
    #  - a `str` object,
    #  - a `unicode` object,
    #  - a file-like object with its `read` method returning `str`,
    #  - a file-like object with its `read` method returning `unicode`.

    # Yeah, it's ugly and slow.

    def __init__(self, stream):
        self.name = None
        self.stream = None
        self.stream_pointer = 0
        self.eof = True
        self.buffer = u''
        self.pointer = 0
        self.raw_buffer = None
        self.raw_decode = None
        self.encoding = None
        self.index = 0
        self.line = 0
        self.column = 0
        if isinstance(stream, unicode):
            self.name = "<unicode string>"
            self.check_printable(stream)
            self.buffer = stream+u'\0'
        elif isinstance(stream, str):
            self.name = "<string>"
            self.raw_buffer = stream
            self.determine_encoding()
        else:
            self.stream = stream
            self.name = getattr(stream, 'name', "<file>")
            self.eof = False
            self.raw_buffer = ''
            self.determine_encoding()

    def peek(self, index=0):
        try:
            return self.buffer[self.pointer+index]
        except IndexError:
            self.update(index+1)
            return self.buffer[self.pointer+index]

    def prefix(self, length=1):
        if self.pointer+length >= len(self.buffer):
            self.update(length)
        return self.buffer[self.pointer:self.pointer+length]

    def forward(self, length=1):
        if self.pointer+length+1 >= len(self.buffer):
            self.update(length+1)
        while length:
            ch = self.buffer[self.pointer]
            self.pointer += 1
            self.index += 1
            if ch in u'\n\x85\u2028\u2029'  \
                    or (ch == u'\r' and self.buffer[self.pointer] != u'\n'):
                self.line += 1
                self.column = 0
            elif ch != u'\uFEFF':
                self.column += 1
            length -= 1

    def get_mark(self):
        if self.stream is None:
            return Mark(self.name, self.index, self.line, self.column,
                    self.buffer, self.pointer)
        else:
            return Mark(self.name, self.index, self.line, self.column,
                    None, None)

    def determine_encoding(self):
        while not self.eof and len(self.raw_buffer) < 2:
            self.update_raw()
        if not isinstance(self.raw_buffer, unicode):
            if self.raw_buffer.startswith(codecs.BOM_UTF16_LE):
                self.raw_decode = codecs.utf_16_le_decode
                self.encoding = 'utf-16-le'
            elif self.raw_buffer.startswith(codecs.BOM_UTF16_BE):
                self.raw_decode = codecs.utf_16_be_decode
                self.encoding = 'utf-16-be'
            else:
                self.raw_decode = codecs.utf_8_decode
                self.encoding = 'utf-8'
        self.update(1)

    NON_PRINTABLE = re.compile(u'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD]')
    def check_printable(self, data):
        match = self.NON_PRINTABLE.search(data)
        if match:
            character = match.group()
            position = self.index+(len(self.buffer)-self.pointer)+match.start()
            raise ReaderError(self.name, position, ord(character),
                    'unicode', "special characters are not allowed")

    def update(self, length):
        if self.raw_buffer is None:
            return
        self.buffer = self.buffer[self.pointer:]
        self.pointer = 0
        while len(self.buffer) < length:
            if not self.eof:
                self.update_raw()
            if self.raw_decode is not None:
                try:
                    data, converted = self.raw_decode(self.raw_buffer,
                            'strict', self.eof)
                except UnicodeDecodeError, exc:
                    character = exc.object[exc.start]
                    if self.stream is not None:
                        position = self.stream_pointer-len(self.raw_buffer)+exc.start
                    else:
                        position = exc.start
                    raise ReaderError(self.name, position, character,
                            exc.encoding, exc.reason)
            else:
                data = self.raw_buffer
                converted = len(data)
            self.check_printable(data)
            self.buffer += data
            self.raw_buffer = self.raw_buffer[converted:]
            if self.eof:
                self.buffer += u'\0'
                self.raw_buffer = None
                break

    def update_raw(self, size=1024):
        data = self.stream.read(size)
        if data:
            self.raw_buffer += data
            self.stream_pointer += len(data)
        else:
            self.eof = True

#try:
#    import psyco
#    psyco.bind(Reader)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = representer

__all__ = ['BaseRepresenter', 'SafeRepresenter', 'Representer',
    'RepresenterError']

from error import *
from nodes import *

import datetime

import sys, copy_reg, types

class RepresenterError(YAMLError):
    pass

class BaseRepresenter(object):

    yaml_representers = {}
    yaml_multi_representers = {}

    def __init__(self, default_style=None, default_flow_style=None):
        self.default_style = default_style
        self.default_flow_style = default_flow_style
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def represent(self, data):
        node = self.represent_data(data)
        self.serialize(node)
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def get_classobj_bases(self, cls):
        bases = [cls]
        for base in cls.__bases__:
            bases.extend(self.get_classobj_bases(base))
        return bases

    def represent_data(self, data):
        if self.ignore_aliases(data):
            self.alias_key = None
        else:
            self.alias_key = id(data)
        if self.alias_key is not None:
            if self.alias_key in self.represented_objects:
                node = self.represented_objects[self.alias_key]
                #if node is None:
                #    raise RepresenterError("recursive objects are not allowed: %r" % data)
                return node
            #self.represented_objects[alias_key] = None
            self.object_keeper.append(data)
        data_types = type(data).__mro__
        if type(data) is types.InstanceType:
            data_types = self.get_classobj_bases(data.__class__)+list(data_types)
        if data_types[0] in self.yaml_representers:
            node = self.yaml_representers[data_types[0]](self, data)
        else:
            for data_type in data_types:
                if data_type in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[data_type](self, data)
                    break
            else:
                if None in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[None](self, data)
                elif None in self.yaml_representers:
                    node = self.yaml_representers[None](self, data)
                else:
                    node = ScalarNode(None, unicode(data))
        #if alias_key is not None:
        #    self.represented_objects[alias_key] = node
        return node

    def add_representer(cls, data_type, representer):
        if not 'yaml_representers' in cls.__dict__:
            cls.yaml_representers = cls.yaml_representers.copy()
        cls.yaml_representers[data_type] = representer
    add_representer = classmethod(add_representer)

    def add_multi_representer(cls, data_type, representer):
        if not 'yaml_multi_representers' in cls.__dict__:
            cls.yaml_multi_representers = cls.yaml_multi_representers.copy()
        cls.yaml_multi_representers[data_type] = representer
    add_multi_representer = classmethod(add_multi_representer)

    def represent_scalar(self, tag, value, style=None):
        if style is None:
            style = self.default_style
        node = ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node

    def represent_sequence(self, tag, sequence, flow_style=None):
        value = []
        node = SequenceNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        for item in sequence:
            node_item = self.represent_data(item)
            if not (isinstance(node_item, ScalarNode) and not node_item.style):
                best_style = False
            value.append(node_item)
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = mapping.items()
            mapping.sort()
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def ignore_aliases(self, data):
        return False

class SafeRepresenter(BaseRepresenter):

    def ignore_aliases(self, data):
        if data in [None, ()]:
            return True
        if isinstance(data, (str, unicode, bool, int, float)):
            return True

    def represent_none(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:null',
                u'null')

    def represent_str(self, data):
        tag = None
        style = None
        try:
            data = unicode(data, 'ascii')
            tag = u'tag:yaml.org,2002:str'
        except UnicodeDecodeError:
            try:
                data = unicode(data, 'utf-8')
                tag = u'tag:yaml.org,2002:str'
            except UnicodeDecodeError:
                data = data.encode('base64')
                tag = u'tag:yaml.org,2002:binary'
                style = '|'
        return self.represent_scalar(tag, data, style=style)

    def represent_unicode(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:str', data)

    def represent_bool(self, data):
        if data:
            value = u'true'
        else:
            value = u'false'
        return self.represent_scalar(u'tag:yaml.org,2002:bool', value)

    def represent_int(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:int', unicode(data))

    def represent_long(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:int', unicode(data))

    inf_value = 1e300
    while repr(inf_value) != repr(inf_value*inf_value):
        inf_value *= inf_value

    def represent_float(self, data):
        if data != data or (data == 0.0 and data == 1.0):
            value = u'.nan'
        elif data == self.inf_value:
            value = u'.inf'
        elif data == -self.inf_value:
            value = u'-.inf'
        else:
            value = unicode(repr(data)).lower()
            # Note that in some cases `repr(data)` represents a float number
            # without the decimal parts.  For instance:
            #   >>> repr(1e17)
            #   '1e17'
            # Unfortunately, this is not a valid float representation according
            # to the definition of the `!!float` tag.  We fix this by adding
            # '.0' before the 'e' symbol.
            if u'.' not in value and u'e' in value:
                value = value.replace(u'e', u'.0e', 1)
        return self.represent_scalar(u'tag:yaml.org,2002:float', value)

    def represent_list(self, data):
        #pairs = (len(data) > 0 and isinstance(data, list))
        #if pairs:
        #    for item in data:
        #        if not isinstance(item, tuple) or len(item) != 2:
        #            pairs = False
        #            break
        #if not pairs:
            return self.represent_sequence(u'tag:yaml.org,2002:seq', data)
        #value = []
        #for item_key, item_value in data:
        #    value.append(self.represent_mapping(u'tag:yaml.org,2002:map',
        #        [(item_key, item_value)]))
        #return SequenceNode(u'tag:yaml.org,2002:pairs', value)

    def represent_dict(self, data):
        return self.represent_mapping(u'tag:yaml.org,2002:map', data)

    def represent_set(self, data):
        value = {}
        for key in data:
            value[key] = None
        return self.represent_mapping(u'tag:yaml.org,2002:set', value)

    def represent_date(self, data):
        value = unicode(data.isoformat())
        return self.represent_scalar(u'tag:yaml.org,2002:timestamp', value)

    def represent_datetime(self, data):
        value = unicode(data.isoformat(' '))
        return self.represent_scalar(u'tag:yaml.org,2002:timestamp', value)

    def represent_yaml_object(self, tag, data, cls, flow_style=None):
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__.copy()
        return self.represent_mapping(tag, state, flow_style=flow_style)

    def represent_undefined(self, data):
        raise RepresenterError("cannot represent an object: %s" % data)

SafeRepresenter.add_representer(type(None),
        SafeRepresenter.represent_none)

SafeRepresenter.add_representer(str,
        SafeRepresenter.represent_str)

SafeRepresenter.add_representer(unicode,
        SafeRepresenter.represent_unicode)

SafeRepresenter.add_representer(bool,
        SafeRepresenter.represent_bool)

SafeRepresenter.add_representer(int,
        SafeRepresenter.represent_int)

SafeRepresenter.add_representer(long,
        SafeRepresenter.represent_long)

SafeRepresenter.add_representer(float,
        SafeRepresenter.represent_float)

SafeRepresenter.add_representer(list,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(tuple,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(dict,
        SafeRepresenter.represent_dict)

SafeRepresenter.add_representer(set,
        SafeRepresenter.represent_set)

SafeRepresenter.add_representer(datetime.date,
        SafeRepresenter.represent_date)

SafeRepresenter.add_representer(datetime.datetime,
        SafeRepresenter.represent_datetime)

SafeRepresenter.add_representer(None,
        SafeRepresenter.represent_undefined)

class Representer(SafeRepresenter):

    def represent_str(self, data):
        tag = None
        style = None
        try:
            data = unicode(data, 'ascii')
            tag = u'tag:yaml.org,2002:str'
        except UnicodeDecodeError:
            try:
                data = unicode(data, 'utf-8')
                tag = u'tag:yaml.org,2002:python/str'
            except UnicodeDecodeError:
                data = data.encode('base64')
                tag = u'tag:yaml.org,2002:binary'
                style = '|'
        return self.represent_scalar(tag, data, style=style)

    def represent_unicode(self, data):
        tag = None
        try:
            data.encode('ascii')
            tag = u'tag:yaml.org,2002:python/unicode'
        except UnicodeEncodeError:
            tag = u'tag:yaml.org,2002:str'
        return self.represent_scalar(tag, data)

    def represent_long(self, data):
        tag = u'tag:yaml.org,2002:int'
        if int(data) is not data:
            tag = u'tag:yaml.org,2002:python/long'
        return self.represent_scalar(tag, unicode(data))

    def represent_complex(self, data):
        if data.imag == 0.0:
            data = u'%r' % data.real
        elif data.real == 0.0:
            data = u'%rj' % data.imag
        elif data.imag > 0:
            data = u'%r+%rj' % (data.real, data.imag)
        else:
            data = u'%r%rj' % (data.real, data.imag)
        return self.represent_scalar(u'tag:yaml.org,2002:python/complex', data)

    def represent_tuple(self, data):
        return self.represent_sequence(u'tag:yaml.org,2002:python/tuple', data)

    def represent_name(self, data):
        name = u'%s.%s' % (data.__module__, data.__name__)
        return self.represent_scalar(u'tag:yaml.org,2002:python/name:'+name, u'')

    def represent_module(self, data):
        return self.represent_scalar(
                u'tag:yaml.org,2002:python/module:'+data.__name__, u'')

    def represent_instance(self, data):
        # For instances of classic classes, we use __getinitargs__ and
        # __getstate__ to serialize the data.

        # If data.__getinitargs__ exists, the object must be reconstructed by
        # calling cls(**args), where args is a tuple returned by
        # __getinitargs__. Otherwise, the cls.__init__ method should never be
        # called and the class instance is created by instantiating a trivial
        # class and assigning to the instance's __class__ variable.

        # If data.__getstate__ exists, it returns the state of the object.
        # Otherwise, the state of the object is data.__dict__.

        # We produce either a !!python/object or !!python/object/new node.
        # If data.__getinitargs__ does not exist and state is a dictionary, we
        # produce a !!python/object node . Otherwise we produce a
        # !!python/object/new node.

        cls = data.__class__
        class_name = u'%s.%s' % (cls.__module__, cls.__name__)
        args = None
        state = None
        if hasattr(data, '__getinitargs__'):
            args = list(data.__getinitargs__())
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__
        if args is None and isinstance(state, dict):
            return self.represent_mapping(
                    u'tag:yaml.org,2002:python/object:'+class_name, state)
        if isinstance(state, dict) and not state:
            return self.represent_sequence(
                    u'tag:yaml.org,2002:python/object/new:'+class_name, args)
        value = {}
        if args:
            value['args'] = args
        value['state'] = state
        return self.represent_mapping(
                u'tag:yaml.org,2002:python/object/new:'+class_name, value)

    def represent_object(self, data):
        # We use __reduce__ API to save the data. data.__reduce__ returns
        # a tuple of length 2-5:
        #   (function, args, state, listitems, dictitems)

        # For reconstructing, we calls function(*args), then set its state,
        # listitems, and dictitems if they are not None.

        # A special case is when function.__name__ == '__newobj__'. In this
        # case we create the object with args[0].__new__(*args).

        # Another special case is when __reduce__ returns a string - we don't
        # support it.

        # We produce a !!python/object, !!python/object/new or
        # !!python/object/apply node.

        cls = type(data)
        if cls in copy_reg.dispatch_table:
            reduce = copy_reg.dispatch_table[cls](data)
        elif hasattr(data, '__reduce_ex__'):
            reduce = data.__reduce_ex__(2)
        elif hasattr(data, '__reduce__'):
            reduce = data.__reduce__()
        else:
            raise RepresenterError("cannot represent object: %r" % data)
        reduce = (list(reduce)+[None]*5)[:5]
        function, args, state, listitems, dictitems = reduce
        args = list(args)
        if state is None:
            state = {}
        if listitems is not None:
            listitems = list(listitems)
        if dictitems is not None:
            dictitems = dict(dictitems)
        if function.__name__ == '__newobj__':
            function = args[0]
            args = args[1:]
            tag = u'tag:yaml.org,2002:python/object/new:'
            newobj = True
        else:
            tag = u'tag:yaml.org,2002:python/object/apply:'
            newobj = False
        function_name = u'%s.%s' % (function.__module__, function.__name__)
        if not args and not listitems and not dictitems \
                and isinstance(state, dict) and newobj:
            return self.represent_mapping(
                    u'tag:yaml.org,2002:python/object:'+function_name, state)
        if not listitems and not dictitems  \
                and isinstance(state, dict) and not state:
            return self.represent_sequence(tag+function_name, args)
        value = {}
        if args:
            value['args'] = args
        if state or not isinstance(state, dict):
            value['state'] = state
        if listitems:
            value['listitems'] = listitems
        if dictitems:
            value['dictitems'] = dictitems
        return self.represent_mapping(tag+function_name, value)

Representer.add_representer(str,
        Representer.represent_str)

Representer.add_representer(unicode,
        Representer.represent_unicode)

Representer.add_representer(long,
        Representer.represent_long)

Representer.add_representer(complex,
        Representer.represent_complex)

Representer.add_representer(tuple,
        Representer.represent_tuple)

Representer.add_representer(type,
        Representer.represent_name)

Representer.add_representer(types.ClassType,
        Representer.represent_name)

Representer.add_representer(types.FunctionType,
        Representer.represent_name)

Representer.add_representer(types.BuiltinFunctionType,
        Representer.represent_name)

Representer.add_representer(types.ModuleType,
        Representer.represent_module)

Representer.add_multi_representer(types.InstanceType,
        Representer.represent_instance)

Representer.add_multi_representer(object,
        Representer.represent_object)


########NEW FILE########
__FILENAME__ = resolver

__all__ = ['BaseResolver', 'Resolver']

from error import *
from nodes import *

import re

class ResolverError(YAMLError):
    pass

class BaseResolver(object):

    DEFAULT_SCALAR_TAG = u'tag:yaml.org,2002:str'
    DEFAULT_SEQUENCE_TAG = u'tag:yaml.org,2002:seq'
    DEFAULT_MAPPING_TAG = u'tag:yaml.org,2002:map'

    yaml_implicit_resolvers = {}
    yaml_path_resolvers = {}

    def __init__(self):
        self.resolver_exact_paths = []
        self.resolver_prefix_paths = []

    def add_implicit_resolver(cls, tag, regexp, first):
        if not 'yaml_implicit_resolvers' in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()
        if first is None:
            first = [None]
        for ch in first:
            cls.yaml_implicit_resolvers.setdefault(ch, []).append((tag, regexp))
    add_implicit_resolver = classmethod(add_implicit_resolver)

    def add_path_resolver(cls, tag, path, kind=None):
        # Note: `add_path_resolver` is experimental.  The API could be changed.
        # `new_path` is a pattern that is matched against the path from the
        # root to the node that is being considered.  `node_path` elements are
        # tuples `(node_check, index_check)`.  `node_check` is a node class:
        # `ScalarNode`, `SequenceNode`, `MappingNode` or `None`.  `None`
        # matches any kind of a node.  `index_check` could be `None`, a boolean
        # value, a string value, or a number.  `None` and `False` match against
        # any _value_ of sequence and mapping nodes.  `True` matches against
        # any _key_ of a mapping node.  A string `index_check` matches against
        # a mapping value that corresponds to a scalar key which content is
        # equal to the `index_check` value.  An integer `index_check` matches
        # against a sequence value with the index equal to `index_check`.
        if not 'yaml_path_resolvers' in cls.__dict__:
            cls.yaml_path_resolvers = cls.yaml_path_resolvers.copy()
        new_path = []
        for element in path:
            if isinstance(element, (list, tuple)):
                if len(element) == 2:
                    node_check, index_check = element
                elif len(element) == 1:
                    node_check = element[0]
                    index_check = True
                else:
                    raise ResolverError("Invalid path element: %s" % element)
            else:
                node_check = None
                index_check = element
            if node_check is str:
                node_check = ScalarNode
            elif node_check is list:
                node_check = SequenceNode
            elif node_check is dict:
                node_check = MappingNode
            elif node_check not in [ScalarNode, SequenceNode, MappingNode]  \
                    and not isinstance(node_check, basestring)  \
                    and node_check is not None:
                raise ResolverError("Invalid node checker: %s" % node_check)
            if not isinstance(index_check, (basestring, int))   \
                    and index_check is not None:
                raise ResolverError("Invalid index checker: %s" % index_check)
            new_path.append((node_check, index_check))
        if kind is str:
            kind = ScalarNode
        elif kind is list:
            kind = SequenceNode
        elif kind is dict:
            kind = MappingNode
        elif kind not in [ScalarNode, SequenceNode, MappingNode]    \
                and kind is not None:
            raise ResolverError("Invalid node kind: %s" % kind)
        cls.yaml_path_resolvers[tuple(new_path), kind] = tag
    add_path_resolver = classmethod(add_path_resolver)

    def descend_resolver(self, current_node, current_index):
        if not self.yaml_path_resolvers:
            return
        exact_paths = {}
        prefix_paths = []
        if current_node:
            depth = len(self.resolver_prefix_paths)
            for path, kind in self.resolver_prefix_paths[-1]:
                if self.check_resolver_prefix(depth, path, kind,
                        current_node, current_index):
                    if len(path) > depth:
                        prefix_paths.append((path, kind))
                    else:
                        exact_paths[kind] = self.yaml_path_resolvers[path, kind]
        else:
            for path, kind in self.yaml_path_resolvers:
                if not path:
                    exact_paths[kind] = self.yaml_path_resolvers[path, kind]
                else:
                    prefix_paths.append((path, kind))
        self.resolver_exact_paths.append(exact_paths)
        self.resolver_prefix_paths.append(prefix_paths)

    def ascend_resolver(self):
        if not self.yaml_path_resolvers:
            return
        self.resolver_exact_paths.pop()
        self.resolver_prefix_paths.pop()

    def check_resolver_prefix(self, depth, path, kind,
            current_node, current_index):
        node_check, index_check = path[depth-1]
        if isinstance(node_check, basestring):
            if current_node.tag != node_check:
                return
        elif node_check is not None:
            if not isinstance(current_node, node_check):
                return
        if index_check is True and current_index is not None:
            return
        if (index_check is False or index_check is None)    \
                and current_index is None:
            return
        if isinstance(index_check, basestring):
            if not (isinstance(current_index, ScalarNode)
                    and index_check == current_index.value):
                return
        elif isinstance(index_check, int) and not isinstance(index_check, bool):
            if index_check != current_index:
                return
        return True

    def resolve(self, kind, value, implicit):
        if kind is ScalarNode and implicit[0]:
            if value == u'':
                resolvers = self.yaml_implicit_resolvers.get(u'', [])
            else:
                resolvers = self.yaml_implicit_resolvers.get(value[0], [])
            resolvers += self.yaml_implicit_resolvers.get(None, [])
            for tag, regexp in resolvers:
                if regexp.match(value):
                    return tag
            implicit = implicit[1]
        if self.yaml_path_resolvers:
            exact_paths = self.resolver_exact_paths[-1]
            if kind in exact_paths:
                return exact_paths[kind]
            if None in exact_paths:
                return exact_paths[None]
        if kind is ScalarNode:
            return self.DEFAULT_SCALAR_TAG
        elif kind is SequenceNode:
            return self.DEFAULT_SEQUENCE_TAG
        elif kind is MappingNode:
            return self.DEFAULT_MAPPING_TAG

class Resolver(BaseResolver):
    pass

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:bool',
        re.compile(ur'''^(?:yes|Yes|YES|no|No|NO
                    |true|True|TRUE|false|False|FALSE
                    |on|On|ON|off|Off|OFF)$''', re.X),
        list(u'yYnNtTfFoO'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:float',
        re.compile(ur'''^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
                    |\.[0-9_]+(?:[eE][-+][0-9]+)?
                    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$''', re.X),
        list(u'-+0123456789.'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:int',
        re.compile(ur'''^(?:[-+]?0b[0-1_]+
                    |[-+]?0[0-7_]+
                    |[-+]?(?:0|[1-9][0-9_]*)
                    |[-+]?0x[0-9a-fA-F_]+
                    |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$''', re.X),
        list(u'-+0123456789'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:merge',
        re.compile(ur'^(?:<<)$'),
        [u'<'])

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:null',
        re.compile(ur'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
        [u'~', u'n', u'N', u''])

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:timestamp',
        re.compile(ur'''^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
                    |[0-9][0-9][0-9][0-9] -[0-9][0-9]? -[0-9][0-9]?
                     (?:[Tt]|[ \t]+)[0-9][0-9]?
                     :[0-9][0-9] :[0-9][0-9] (?:\.[0-9]*)?
                     (?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$''', re.X),
        list(u'0123456789'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:value',
        re.compile(ur'^(?:=)$'),
        [u'='])

# The following resolver is only for documentation purposes. It cannot work
# because plain scalars cannot start with '!', '&', or '*'.
Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:yaml',
        re.compile(ur'^(?:!|&|\*)$'),
        list(u'!&*'))


########NEW FILE########
__FILENAME__ = scanner

# Scanner produces tokens of the following types:
# STREAM-START
# STREAM-END
# DIRECTIVE(name, value)
# DOCUMENT-START
# DOCUMENT-END
# BLOCK-SEQUENCE-START
# BLOCK-MAPPING-START
# BLOCK-END
# FLOW-SEQUENCE-START
# FLOW-MAPPING-START
# FLOW-SEQUENCE-END
# FLOW-MAPPING-END
# BLOCK-ENTRY
# FLOW-ENTRY
# KEY
# VALUE
# ALIAS(value)
# ANCHOR(value)
# TAG(value)
# SCALAR(value, plain, style)
#
# Read comments in the Scanner code for more details.
#

__all__ = ['Scanner', 'ScannerError']

from error import MarkedYAMLError
from tokens import *

class ScannerError(MarkedYAMLError):
    pass

class SimpleKey(object):
    # See below simple keys treatment.

    def __init__(self, token_number, required, index, line, column, mark):
        self.token_number = token_number
        self.required = required
        self.index = index
        self.line = line
        self.column = column
        self.mark = mark

class Scanner(object):

    def __init__(self):
        """Initialize the scanner."""
        # It is assumed that Scanner and Reader will have a common descendant.
        # Reader do the dirty work of checking for BOM and converting the
        # input data to Unicode. It also adds NUL to the end.
        #
        # Reader supports the following methods
        #   self.peek(i=0)       # peek the next i-th character
        #   self.prefix(l=1)     # peek the next l characters
        #   self.forward(l=1)    # read the next l characters and move the pointer.

        # Had we reached the end of the stream?
        self.done = False

        # The number of unclosed '{' and '['. `flow_level == 0` means block
        # context.
        self.flow_level = 0

        # List of processed tokens that are not yet emitted.
        self.tokens = []

        # Add the STREAM-START token.
        self.fetch_stream_start()

        # Number of tokens that were emitted through the `get_token` method.
        self.tokens_taken = 0

        # The current indentation level.
        self.indent = -1

        # Past indentation levels.
        self.indents = []

        # Variables related to simple keys treatment.

        # A simple key is a key that is not denoted by the '?' indicator.
        # Example of simple keys:
        #   ---
        #   block simple key: value
        #   ? not a simple key:
        #   : { flow simple key: value }
        # We emit the KEY token before all keys, so when we find a potential
        # simple key, we try to locate the corresponding ':' indicator.
        # Simple keys should be limited to a single line and 1024 characters.

        # Can a simple key start at the current position? A simple key may
        # start:
        # - at the beginning of the line, not counting indentation spaces
        #       (in block context),
        # - after '{', '[', ',' (in the flow context),
        # - after '?', ':', '-' (in the block context).
        # In the block context, this flag also signifies if a block collection
        # may start at the current position.
        self.allow_simple_key = True

        # Keep track of possible simple keys. This is a dictionary. The key
        # is `flow_level`; there can be no more that one possible simple key
        # for each level. The value is a SimpleKey record:
        #   (token_number, required, index, line, column, mark)
        # A simple key may start with ALIAS, ANCHOR, TAG, SCALAR(flow),
        # '[', or '{' tokens.
        self.possible_simple_keys = {}

    # Public methods.

    def check_token(self, *choices):
        # Check if the next token is one of the given types.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.tokens[0], choice):
                    return True
        return False

    def peek_token(self):
        # Return the next token, but do not delete if from the queue.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            return self.tokens[0]

    def get_token(self):
        # Return the next token.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            self.tokens_taken += 1
            return self.tokens.pop(0)

    # Private methods.

    def need_more_tokens(self):
        if self.done:
            return False
        if not self.tokens:
            return True
        # The current token may be a potential simple key, so we
        # need to look further.
        self.stale_possible_simple_keys()
        if self.next_possible_simple_key() == self.tokens_taken:
            return True

    def fetch_more_tokens(self):

        # Eat whitespaces and comments until we reach the next token.
        self.scan_to_next_token()

        # Remove obsolete possible simple keys.
        self.stale_possible_simple_keys()

        # Compare the current indentation and column. It may add some tokens
        # and decrease the current indentation level.
        self.unwind_indent(self.column)

        # Peek the next character.
        ch = self.peek()

        # Is it the end of stream?
        if ch == u'\0':
            return self.fetch_stream_end()

        # Is it a directive?
        if ch == u'%' and self.check_directive():
            return self.fetch_directive()

        # Is it the document start?
        if ch == u'-' and self.check_document_start():
            return self.fetch_document_start()

        # Is it the document end?
        if ch == u'.' and self.check_document_end():
            return self.fetch_document_end()

        # TODO: support for BOM within a stream.
        #if ch == u'\uFEFF':
        #    return self.fetch_bom()    <-- issue BOMToken

        # Note: the order of the following checks is NOT significant.

        # Is it the flow sequence start indicator?
        if ch == u'[':
            return self.fetch_flow_sequence_start()

        # Is it the flow mapping start indicator?
        if ch == u'{':
            return self.fetch_flow_mapping_start()

        # Is it the flow sequence end indicator?
        if ch == u']':
            return self.fetch_flow_sequence_end()

        # Is it the flow mapping end indicator?
        if ch == u'}':
            return self.fetch_flow_mapping_end()

        # Is it the flow entry indicator?
        if ch == u',':
            return self.fetch_flow_entry()

        # Is it the block entry indicator?
        if ch == u'-' and self.check_block_entry():
            return self.fetch_block_entry()

        # Is it the key indicator?
        if ch == u'?' and self.check_key():
            return self.fetch_key()

        # Is it the value indicator?
        if ch == u':' and self.check_value():
            return self.fetch_value()

        # Is it an alias?
        if ch == u'*':
            return self.fetch_alias()

        # Is it an anchor?
        if ch == u'&':
            return self.fetch_anchor()

        # Is it a tag?
        if ch == u'!':
            return self.fetch_tag()

        # Is it a literal scalar?
        if ch == u'|' and not self.flow_level:
            return self.fetch_literal()

        # Is it a folded scalar?
        if ch == u'>' and not self.flow_level:
            return self.fetch_folded()

        # Is it a single quoted scalar?
        if ch == u'\'':
            return self.fetch_single()

        # Is it a double quoted scalar?
        if ch == u'\"':
            return self.fetch_double()

        # It must be a plain scalar then.
        if self.check_plain():
            return self.fetch_plain()

        # No? It's an error. Let's produce a nice error message.
        raise ScannerError("while scanning for the next token", None,
                "found character %r that cannot start any token"
                % ch.encode('utf-8'), self.get_mark())

    # Simple keys treatment.

    def next_possible_simple_key(self):
        # Return the number of the nearest possible simple key. Actually we
        # don't need to loop through the whole dictionary. We may replace it
        # with the following code:
        #   if not self.possible_simple_keys:
        #       return None
        #   return self.possible_simple_keys[
        #           min(self.possible_simple_keys.keys())].token_number
        min_token_number = None
        for level in self.possible_simple_keys:
            key = self.possible_simple_keys[level]
            if min_token_number is None or key.token_number < min_token_number:
                min_token_number = key.token_number
        return min_token_number

    def stale_possible_simple_keys(self):
        # Remove entries that are no longer possible simple keys. According to
        # the YAML specification, simple keys
        # - should be limited to a single line,
        # - should be no longer than 1024 characters.
        # Disabling this procedure will allow simple keys of any length and
        # height (may cause problems if indentation is broken though).
        for level in self.possible_simple_keys.keys():
            key = self.possible_simple_keys[level]
            if key.line != self.line  \
                    or self.index-key.index > 1024:
                if key.required:
                    raise ScannerError("while scanning a simple key", key.mark,
                            "could not found expected ':'", self.get_mark())
                del self.possible_simple_keys[level]

    def save_possible_simple_key(self):
        # The next token may start a simple key. We check if it's possible
        # and save its position. This function is called for
        #   ALIAS, ANCHOR, TAG, SCALAR(flow), '[', and '{'.

        # Check if a simple key is required at the current position.
        required = not self.flow_level and self.indent == self.column

        # A simple key is required only if it is the first token in the current
        # line. Therefore it is always allowed.
        assert self.allow_simple_key or not required

        # The next token might be a simple key. Let's save it's number and
        # position.
        if self.allow_simple_key:
            self.remove_possible_simple_key()
            token_number = self.tokens_taken+len(self.tokens)
            key = SimpleKey(token_number, required,
                    self.index, self.line, self.column, self.get_mark())
            self.possible_simple_keys[self.flow_level] = key

    def remove_possible_simple_key(self):
        # Remove the saved possible key position at the current flow level.
        if self.flow_level in self.possible_simple_keys:
            key = self.possible_simple_keys[self.flow_level]
            
            if key.required:
                raise ScannerError("while scanning a simple key", key.mark,
                        "could not found expected ':'", self.get_mark())

            del self.possible_simple_keys[self.flow_level]

    # Indentation functions.

    def unwind_indent(self, column):

        ## In flow context, tokens should respect indentation.
        ## Actually the condition should be `self.indent >= column` according to
        ## the spec. But this condition will prohibit intuitively correct
        ## constructions such as
        ## key : {
        ## }
        #if self.flow_level and self.indent > column:
        #    raise ScannerError(None, None,
        #            "invalid intendation or unclosed '[' or '{'",
        #            self.get_mark())

        # In the flow context, indentation is ignored. We make the scanner less
        # restrictive then specification requires.
        if self.flow_level:
            return

        # In block context, we may need to issue the BLOCK-END tokens.
        while self.indent > column:
            mark = self.get_mark()
            self.indent = self.indents.pop()
            self.tokens.append(BlockEndToken(mark, mark))

    def add_indent(self, column):
        # Check if we need to increase indentation.
        if self.indent < column:
            self.indents.append(self.indent)
            self.indent = column
            return True
        return False

    # Fetchers.

    def fetch_stream_start(self):
        # We always add STREAM-START as the first token and STREAM-END as the
        # last token.

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-START.
        self.tokens.append(StreamStartToken(mark, mark,
            encoding=self.encoding))
        

    def fetch_stream_end(self):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False
        self.possible_simple_keys = {}

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-END.
        self.tokens.append(StreamEndToken(mark, mark))

        # The steam is finished.
        self.done = True

    def fetch_directive(self):
        
        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Scan and add DIRECTIVE.
        self.tokens.append(self.scan_directive())

    def fetch_document_start(self):
        self.fetch_document_indicator(DocumentStartToken)

    def fetch_document_end(self):
        self.fetch_document_indicator(DocumentEndToken)

    def fetch_document_indicator(self, TokenClass):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys. Note that there could not be a block collection
        # after '---'.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Add DOCUMENT-START or DOCUMENT-END.
        start_mark = self.get_mark()
        self.forward(3)
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_start(self):
        self.fetch_flow_collection_start(FlowSequenceStartToken)

    def fetch_flow_mapping_start(self):
        self.fetch_flow_collection_start(FlowMappingStartToken)

    def fetch_flow_collection_start(self, TokenClass):

        # '[' and '{' may start a simple key.
        self.save_possible_simple_key()

        # Increase the flow level.
        self.flow_level += 1

        # Simple keys are allowed after '[' and '{'.
        self.allow_simple_key = True

        # Add FLOW-SEQUENCE-START or FLOW-MAPPING-START.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_end(self):
        self.fetch_flow_collection_end(FlowSequenceEndToken)

    def fetch_flow_mapping_end(self):
        self.fetch_flow_collection_end(FlowMappingEndToken)

    def fetch_flow_collection_end(self, TokenClass):

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Decrease the flow level.
        self.flow_level -= 1

        # No simple keys after ']' or '}'.
        self.allow_simple_key = False

        # Add FLOW-SEQUENCE-END or FLOW-MAPPING-END.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_entry(self):

        # Simple keys are allowed after ','.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add FLOW-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(FlowEntryToken(start_mark, end_mark))

    def fetch_block_entry(self):

        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a new entry?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "sequence entries are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-SEQUENCE-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockSequenceStartToken(mark, mark))

        # It's an error for the block entry to occur in the flow context,
        # but we let the parser detect this.
        else:
            pass

        # Simple keys are allowed after '-'.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add BLOCK-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(BlockEntryToken(start_mark, end_mark))

    def fetch_key(self):
        
        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a key (not nessesary a simple)?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "mapping keys are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-MAPPING-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockMappingStartToken(mark, mark))

        # Simple keys are allowed after '?' in the block context.
        self.allow_simple_key = not self.flow_level

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add KEY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(KeyToken(start_mark, end_mark))

    def fetch_value(self):

        # Do we determine a simple key?
        if self.flow_level in self.possible_simple_keys:

            # Add KEY.
            key = self.possible_simple_keys[self.flow_level]
            del self.possible_simple_keys[self.flow_level]
            self.tokens.insert(key.token_number-self.tokens_taken,
                    KeyToken(key.mark, key.mark))

            # If this key starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.
            if not self.flow_level:
                if self.add_indent(key.column):
                    self.tokens.insert(key.token_number-self.tokens_taken,
                            BlockMappingStartToken(key.mark, key.mark))

            # There cannot be two simple keys one after another.
            self.allow_simple_key = False

        # It must be a part of a complex key.
        else:
            
            # Block context needs additional checks.
            # (Do we really need them? They will be catched by the parser
            # anyway.)
            if not self.flow_level:

                # We are allowed to start a complex value if and only if
                # we can start a simple key.
                if not self.allow_simple_key:
                    raise ScannerError(None, None,
                            "mapping values are not allowed here",
                            self.get_mark())

            # If this value starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.  It will be detected as an error later by
            # the parser.
            if not self.flow_level:
                if self.add_indent(self.column):
                    mark = self.get_mark()
                    self.tokens.append(BlockMappingStartToken(mark, mark))

            # Simple keys are allowed after ':' in the block context.
            self.allow_simple_key = not self.flow_level

            # Reset possible simple key on the current level.
            self.remove_possible_simple_key()

        # Add VALUE.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(ValueToken(start_mark, end_mark))

    def fetch_alias(self):

        # ALIAS could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after ALIAS.
        self.allow_simple_key = False

        # Scan and add ALIAS.
        self.tokens.append(self.scan_anchor(AliasToken))

    def fetch_anchor(self):

        # ANCHOR could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after ANCHOR.
        self.allow_simple_key = False

        # Scan and add ANCHOR.
        self.tokens.append(self.scan_anchor(AnchorToken))

    def fetch_tag(self):

        # TAG could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after TAG.
        self.allow_simple_key = False

        # Scan and add TAG.
        self.tokens.append(self.scan_tag())

    def fetch_literal(self):
        self.fetch_block_scalar(style='|')

    def fetch_folded(self):
        self.fetch_block_scalar(style='>')

    def fetch_block_scalar(self, style):

        # A simple key may follow a block scalar.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Scan and add SCALAR.
        self.tokens.append(self.scan_block_scalar(style))

    def fetch_single(self):
        self.fetch_flow_scalar(style='\'')

    def fetch_double(self):
        self.fetch_flow_scalar(style='"')

    def fetch_flow_scalar(self, style):

        # A flow scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after flow scalars.
        self.allow_simple_key = False

        # Scan and add SCALAR.
        self.tokens.append(self.scan_flow_scalar(style))

    def fetch_plain(self):

        # A plain scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after plain scalars. But note that `scan_plain` will
        # change this flag if the scan is finished at the beginning of the
        # line.
        self.allow_simple_key = False

        # Scan and add SCALAR. May change `allow_simple_key`.
        self.tokens.append(self.scan_plain())

    # Checkers.

    def check_directive(self):

        # DIRECTIVE:        ^ '%' ...
        # The '%' indicator is already checked.
        if self.column == 0:
            return True

    def check_document_start(self):

        # DOCUMENT-START:   ^ '---' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == u'---'  \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_document_end(self):

        # DOCUMENT-END:     ^ '...' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == u'...'  \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_block_entry(self):

        # BLOCK-ENTRY:      '-' (' '|'\n')
        return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_key(self):

        # KEY(flow context):    '?'
        if self.flow_level:
            return True

        # KEY(block context):   '?' (' '|'\n')
        else:
            return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_value(self):

        # VALUE(flow context):  ':'
        if self.flow_level:
            return True

        # VALUE(block context): ':' (' '|'\n')
        else:
            return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_plain(self):

        # A plain scalar may start with any non-space character except:
        #   '-', '?', ':', ',', '[', ']', '{', '}',
        #   '#', '&', '*', '!', '|', '>', '\'', '\"',
        #   '%', '@', '`'.
        #
        # It may also start with
        #   '-', '?', ':'
        # if it is followed by a non-space character.
        #
        # Note that we limit the last rule to the block context (except the
        # '-' character) because we want the flow context to be space
        # independent.
        ch = self.peek()
        return ch not in u'\0 \t\r\n\x85\u2028\u2029-?:,[]{}#&*!|>\'\"%@`'  \
                or (self.peek(1) not in u'\0 \t\r\n\x85\u2028\u2029'
                        and (ch == u'-' or (not self.flow_level and ch in u'?:')))

    # Scanners.

    def scan_to_next_token(self):
        # We ignore spaces, line breaks and comments.
        # If we find a line break in the block context, we set the flag
        # `allow_simple_key` on.
        # The byte order mark is stripped if it's the first character in the
        # stream. We do not yet support BOM inside the stream as the
        # specification requires. Any such mark will be considered as a part
        # of the document.
        #
        # TODO: We need to make tab handling rules more sane. A good rule is
        #   Tabs cannot precede tokens
        #   BLOCK-SEQUENCE-START, BLOCK-MAPPING-START, BLOCK-END,
        #   KEY(block), VALUE(block), BLOCK-ENTRY
        # So the checking code is
        #   if <TAB>:
        #       self.allow_simple_keys = False
        # We also need to add the check for `allow_simple_keys == True` to
        # `unwind_indent` before issuing BLOCK-END.
        # Scanners for block, flow, and plain scalars need to be modified.

        if self.index == 0 and self.peek() == u'\uFEFF':
            self.forward()
        found = False
        while not found:
            while self.peek() == u' ':
                self.forward()
            if self.peek() == u'#':
                while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                    self.forward()
            if self.scan_line_break():
                if not self.flow_level:
                    self.allow_simple_key = True
            else:
                found = True

    def scan_directive(self):
        # See the specification for details.
        start_mark = self.get_mark()
        self.forward()
        name = self.scan_directive_name(start_mark)
        value = None
        if name == u'YAML':
            value = self.scan_yaml_directive_value(start_mark)
            end_mark = self.get_mark()
        elif name == u'TAG':
            value = self.scan_tag_directive_value(start_mark)
            end_mark = self.get_mark()
        else:
            end_mark = self.get_mark()
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        self.scan_directive_ignored_line(start_mark)
        return DirectiveToken(name, value, start_mark, end_mark)

    def scan_directive_name(self, start_mark):
        # See the specification for details.
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                or ch in u'-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        return value

    def scan_yaml_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        major = self.scan_yaml_directive_number(start_mark)
        if self.peek() != '.':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or '.', but found %r"
                    % self.peek().encode('utf-8'),
                    self.get_mark())
        self.forward()
        minor = self.scan_yaml_directive_number(start_mark)
        if self.peek() not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or ' ', but found %r"
                    % self.peek().encode('utf-8'),
                    self.get_mark())
        return (major, minor)

    def scan_yaml_directive_number(self, start_mark):
        # See the specification for details.
        ch = self.peek()
        if not (u'0' <= ch <= u'9'):
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit, but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        length = 0
        while u'0' <= self.peek(length) <= u'9':
            length += 1
        value = int(self.prefix(length))
        self.forward(length)
        return value

    def scan_tag_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        handle = self.scan_tag_directive_handle(start_mark)
        while self.peek() == u' ':
            self.forward()
        prefix = self.scan_tag_directive_prefix(start_mark)
        return (handle, prefix)

    def scan_tag_directive_handle(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_handle('directive', start_mark)
        ch = self.peek()
        if ch != u' ':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return value

    def scan_tag_directive_prefix(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_uri('directive', start_mark)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return value

    def scan_directive_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        if self.peek() == u'#':
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in u'\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        self.scan_line_break()

    def scan_anchor(self, TokenClass):
        # The specification does not restrict characters for anchors and
        # aliases. This may lead to problems, for instance, the document:
        #   [ *alias, value ]
        # can be interpteted in two ways, as
        #   [ "value" ]
        # and
        #   [ *alias , "value" ]
        # Therefore we restrict aliases to numbers and ASCII letters.
        start_mark = self.get_mark()
        indicator = self.peek()
        if indicator == u'*':
            name = 'alias'
        else:
            name = 'anchor'
        self.forward()
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                or ch in u'-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in u'\0 \t\r\n\x85\u2028\u2029?:,]}%@`':
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        end_mark = self.get_mark()
        return TokenClass(value, start_mark, end_mark)

    def scan_tag(self):
        # See the specification for details.
        start_mark = self.get_mark()
        ch = self.peek(1)
        if ch == u'<':
            handle = None
            self.forward(2)
            suffix = self.scan_tag_uri('tag', start_mark)
            if self.peek() != u'>':
                raise ScannerError("while parsing a tag", start_mark,
                        "expected '>', but found %r" % self.peek().encode('utf-8'),
                        self.get_mark())
            self.forward()
        elif ch in u'\0 \t\r\n\x85\u2028\u2029':
            handle = None
            suffix = u'!'
            self.forward()
        else:
            length = 1
            use_handle = False
            while ch not in u'\0 \r\n\x85\u2028\u2029':
                if ch == u'!':
                    use_handle = True
                    break
                length += 1
                ch = self.peek(length)
            handle = u'!'
            if use_handle:
                handle = self.scan_tag_handle('tag', start_mark)
            else:
                handle = u'!'
                self.forward()
            suffix = self.scan_tag_uri('tag', start_mark)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a tag", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        value = (handle, suffix)
        end_mark = self.get_mark()
        return TagToken(value, start_mark, end_mark)

    def scan_block_scalar(self, style):
        # See the specification for details.

        if style == '>':
            folded = True
        else:
            folded = False

        chunks = []
        start_mark = self.get_mark()

        # Scan the header.
        self.forward()
        chomping, increment = self.scan_block_scalar_indicators(start_mark)
        self.scan_block_scalar_ignored_line(start_mark)

        # Determine the indentation level and go to the first non-empty line.
        min_indent = self.indent+1
        if min_indent < 1:
            min_indent = 1
        if increment is None:
            breaks, max_indent, end_mark = self.scan_block_scalar_indentation()
            indent = max(min_indent, max_indent)
        else:
            indent = min_indent+increment-1
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
        line_break = u''

        # Scan the inner part of the block scalar.
        while self.column == indent and self.peek() != u'\0':
            chunks.extend(breaks)
            leading_non_space = self.peek() not in u' \t'
            length = 0
            while self.peek(length) not in u'\0\r\n\x85\u2028\u2029':
                length += 1
            chunks.append(self.prefix(length))
            self.forward(length)
            line_break = self.scan_line_break()
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
            if self.column == indent and self.peek() != u'\0':

                # Unfortunately, folding rules are ambiguous.
                #
                # This is the folding according to the specification:
                
                if folded and line_break == u'\n'   \
                        and leading_non_space and self.peek() not in u' \t':
                    if not breaks:
                        chunks.append(u' ')
                else:
                    chunks.append(line_break)
                
                # This is Clark Evans's interpretation (also in the spec
                # examples):
                #
                #if folded and line_break == u'\n':
                #    if not breaks:
                #        if self.peek() not in ' \t':
                #            chunks.append(u' ')
                #        else:
                #            chunks.append(line_break)
                #else:
                #    chunks.append(line_break)
            else:
                break

        # Chomp the tail.
        if chomping is not False:
            chunks.append(line_break)
        if chomping is True:
            chunks.extend(breaks)

        # We are done.
        return ScalarToken(u''.join(chunks), False, start_mark, end_mark,
                style)

    def scan_block_scalar_indicators(self, start_mark):
        # See the specification for details.
        chomping = None
        increment = None
        ch = self.peek()
        if ch in u'+-':
            if ch == '+':
                chomping = True
            else:
                chomping = False
            self.forward()
            ch = self.peek()
            if ch in u'0123456789':
                increment = int(ch)
                if increment == 0:
                    raise ScannerError("while scanning a block scalar", start_mark,
                            "expected indentation indicator in the range 1-9, but found 0",
                            self.get_mark())
                self.forward()
        elif ch in u'0123456789':
            increment = int(ch)
            if increment == 0:
                raise ScannerError("while scanning a block scalar", start_mark,
                        "expected indentation indicator in the range 1-9, but found 0",
                        self.get_mark())
            self.forward()
            ch = self.peek()
            if ch in u'+-':
                if ch == '+':
                    chomping = True
                else:
                    chomping = False
                self.forward()
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected chomping or indentation indicators, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        return chomping, increment

    def scan_block_scalar_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        if self.peek() == u'#':
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in u'\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        self.scan_line_break()

    def scan_block_scalar_indentation(self):
        # See the specification for details.
        chunks = []
        max_indent = 0
        end_mark = self.get_mark()
        while self.peek() in u' \r\n\x85\u2028\u2029':
            if self.peek() != u' ':
                chunks.append(self.scan_line_break())
                end_mark = self.get_mark()
            else:
                self.forward()
                if self.column > max_indent:
                    max_indent = self.column
        return chunks, max_indent, end_mark

    def scan_block_scalar_breaks(self, indent):
        # See the specification for details.
        chunks = []
        end_mark = self.get_mark()
        while self.column < indent and self.peek() == u' ':
            self.forward()
        while self.peek() in u'\r\n\x85\u2028\u2029':
            chunks.append(self.scan_line_break())
            end_mark = self.get_mark()
            while self.column < indent and self.peek() == u' ':
                self.forward()
        return chunks, end_mark

    def scan_flow_scalar(self, style):
        # See the specification for details.
        # Note that we loose indentation rules for quoted scalars. Quoted
        # scalars don't need to adhere indentation because " and ' clearly
        # mark the beginning and the end of them. Therefore we are less
        # restrictive then the specification requires. We only need to check
        # that document separators are not included in scalars.
        if style == '"':
            double = True
        else:
            double = False
        chunks = []
        start_mark = self.get_mark()
        quote = self.peek()
        self.forward()
        chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        while self.peek() != quote:
            chunks.extend(self.scan_flow_scalar_spaces(double, start_mark))
            chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        self.forward()
        end_mark = self.get_mark()
        return ScalarToken(u''.join(chunks), False, start_mark, end_mark,
                style)

    ESCAPE_REPLACEMENTS = {
        u'0':   u'\0',
        u'a':   u'\x07',
        u'b':   u'\x08',
        u't':   u'\x09',
        u'\t':  u'\x09',
        u'n':   u'\x0A',
        u'v':   u'\x0B',
        u'f':   u'\x0C',
        u'r':   u'\x0D',
        u'e':   u'\x1B',
        u' ':   u'\x20',
        u'\"':  u'\"',
        u'\\':  u'\\',
        u'N':   u'\x85',
        u'_':   u'\xA0',
        u'L':   u'\u2028',
        u'P':   u'\u2029',
    }

    ESCAPE_CODES = {
        u'x':   2,
        u'u':   4,
        u'U':   8,
    }

    def scan_flow_scalar_non_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            length = 0
            while self.peek(length) not in u'\'\"\\\0 \t\r\n\x85\u2028\u2029':
                length += 1
            if length:
                chunks.append(self.prefix(length))
                self.forward(length)
            ch = self.peek()
            if not double and ch == u'\'' and self.peek(1) == u'\'':
                chunks.append(u'\'')
                self.forward(2)
            elif (double and ch == u'\'') or (not double and ch in u'\"\\'):
                chunks.append(ch)
                self.forward()
            elif double and ch == u'\\':
                self.forward()
                ch = self.peek()
                if ch in self.ESCAPE_REPLACEMENTS:
                    chunks.append(self.ESCAPE_REPLACEMENTS[ch])
                    self.forward()
                elif ch in self.ESCAPE_CODES:
                    length = self.ESCAPE_CODES[ch]
                    self.forward()
                    for k in range(length):
                        if self.peek(k) not in u'0123456789ABCDEFabcdef':
                            raise ScannerError("while scanning a double-quoted scalar", start_mark,
                                    "expected escape sequence of %d hexdecimal numbers, but found %r" %
                                        (length, self.peek(k).encode('utf-8')), self.get_mark())
                    code = int(self.prefix(length), 16)
                    chunks.append(unichr(code))
                    self.forward(length)
                elif ch in u'\r\n\x85\u2028\u2029':
                    self.scan_line_break()
                    chunks.extend(self.scan_flow_scalar_breaks(double, start_mark))
                else:
                    raise ScannerError("while scanning a double-quoted scalar", start_mark,
                            "found unknown escape character %r" % ch.encode('utf-8'), self.get_mark())
            else:
                return chunks

    def scan_flow_scalar_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        length = 0
        while self.peek(length) in u' \t':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch == u'\0':
            raise ScannerError("while scanning a quoted scalar", start_mark,
                    "found unexpected end of stream", self.get_mark())
        elif ch in u'\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            breaks = self.scan_flow_scalar_breaks(double, start_mark)
            if line_break != u'\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(u' ')
            chunks.extend(breaks)
        else:
            chunks.append(whitespaces)
        return chunks

    def scan_flow_scalar_breaks(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            # Instead of checking indentation, we check for document
            # separators.
            prefix = self.prefix(3)
            if (prefix == u'---' or prefix == u'...')   \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                raise ScannerError("while scanning a quoted scalar", start_mark,
                        "found unexpected document separator", self.get_mark())
            while self.peek() in u' \t':
                self.forward()
            if self.peek() in u'\r\n\x85\u2028\u2029':
                chunks.append(self.scan_line_break())
            else:
                return chunks

    def scan_plain(self):
        # See the specification for details.
        # We add an additional restriction for the flow context:
        #   plain scalars in the flow context cannot contain ',', ':' and '?'.
        # We also keep track of the `allow_simple_key` flag here.
        # Indentation rules are loosed for the flow context.
        chunks = []
        start_mark = self.get_mark()
        end_mark = start_mark
        indent = self.indent+1
        # We allow zero indentation for scalars, but then we need to check for
        # document separators at the beginning of the line.
        #if indent == 0:
        #    indent = 1
        spaces = []
        while True:
            length = 0
            if self.peek() == u'#':
                break
            while True:
                ch = self.peek(length)
                if ch in u'\0 \t\r\n\x85\u2028\u2029'   \
                        or (not self.flow_level and ch == u':' and
                                self.peek(length+1) in u'\0 \t\r\n\x85\u2028\u2029') \
                        or (self.flow_level and ch in u',:?[]{}'):
                    break
                length += 1
            # It's not clear what we should do with ':' in the flow context.
            if (self.flow_level and ch == u':'
                    and self.peek(length+1) not in u'\0 \t\r\n\x85\u2028\u2029,[]{}'):
                self.forward(length)
                raise ScannerError("while scanning a plain scalar", start_mark,
                    "found unexpected ':'", self.get_mark(),
                    "Please check http://pyyaml.org/wiki/YAMLColonInFlowContext for details.")
            if length == 0:
                break
            self.allow_simple_key = False
            chunks.extend(spaces)
            chunks.append(self.prefix(length))
            self.forward(length)
            end_mark = self.get_mark()
            spaces = self.scan_plain_spaces(indent, start_mark)
            if not spaces or self.peek() == u'#' \
                    or (not self.flow_level and self.column < indent):
                break
        return ScalarToken(u''.join(chunks), True, start_mark, end_mark)

    def scan_plain_spaces(self, indent, start_mark):
        # See the specification for details.
        # The specification is really confusing about tabs in plain scalars.
        # We just forbid them completely. Do not use tabs in YAML!
        chunks = []
        length = 0
        while self.peek(length) in u' ':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch in u'\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            self.allow_simple_key = True
            prefix = self.prefix(3)
            if (prefix == u'---' or prefix == u'...')   \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return
            breaks = []
            while self.peek() in u' \r\n\x85\u2028\u2029':
                if self.peek() == ' ':
                    self.forward()
                else:
                    breaks.append(self.scan_line_break())
                    prefix = self.prefix(3)
                    if (prefix == u'---' or prefix == u'...')   \
                            and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                        return
            if line_break != u'\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(u' ')
            chunks.extend(breaks)
        elif whitespaces:
            chunks.append(whitespaces)
        return chunks

    def scan_tag_handle(self, name, start_mark):
        # See the specification for details.
        # For some strange reasons, the specification does not allow '_' in
        # tag handles. I have allowed it anyway.
        ch = self.peek()
        if ch != u'!':
            raise ScannerError("while scanning a %s" % name, start_mark,
                    "expected '!', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        length = 1
        ch = self.peek(length)
        if ch != u' ':
            while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                    or ch in u'-_':
                length += 1
                ch = self.peek(length)
            if ch != u'!':
                self.forward(length)
                raise ScannerError("while scanning a %s" % name, start_mark,
                        "expected '!', but found %r" % ch.encode('utf-8'),
                        self.get_mark())
            length += 1
        value = self.prefix(length)
        self.forward(length)
        return value

    def scan_tag_uri(self, name, start_mark):
        # See the specification for details.
        # Note: we do not check if URI is well-formed.
        chunks = []
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= u'Z' or u'a' <= ch <= u'z'    \
                or ch in u'-;/?:@&=+$,_.!~*\'()[]%':
            if ch == u'%':
                chunks.append(self.prefix(length))
                self.forward(length)
                length = 0
                chunks.append(self.scan_uri_escapes(name, start_mark))
            else:
                length += 1
            ch = self.peek(length)
        if length:
            chunks.append(self.prefix(length))
            self.forward(length)
            length = 0
        if not chunks:
            raise ScannerError("while parsing a %s" % name, start_mark,
                    "expected URI, but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return u''.join(chunks)

    def scan_uri_escapes(self, name, start_mark):
        # See the specification for details.
        bytes = []
        mark = self.get_mark()
        while self.peek() == u'%':
            self.forward()
            for k in range(2):
                if self.peek(k) not in u'0123456789ABCDEFabcdef':
                    raise ScannerError("while scanning a %s" % name, start_mark,
                            "expected URI escape sequence of 2 hexdecimal numbers, but found %r" %
                                (self.peek(k).encode('utf-8')), self.get_mark())
            bytes.append(chr(int(self.prefix(2), 16)))
            self.forward(2)
        try:
            value = unicode(''.join(bytes), 'utf-8')
        except UnicodeDecodeError, exc:
            raise ScannerError("while scanning a %s" % name, start_mark, str(exc), mark)
        return value

    def scan_line_break(self):
        # Transforms:
        #   '\r\n'      :   '\n'
        #   '\r'        :   '\n'
        #   '\n'        :   '\n'
        #   '\x85'      :   '\n'
        #   '\u2028'    :   '\u2028'
        #   '\u2029     :   '\u2029'
        #   default     :   ''
        ch = self.peek()
        if ch in u'\r\n\x85':
            if self.prefix(2) == u'\r\n':
                self.forward(2)
            else:
                self.forward()
            return u'\n'
        elif ch in u'\u2028\u2029':
            self.forward()
            return ch
        return u''

#try:
#    import psyco
#    psyco.bind(Scanner)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = serializer

__all__ = ['Serializer', 'SerializerError']

from error import YAMLError
from events import *
from nodes import *

class SerializerError(YAMLError):
    pass

class Serializer(object):

    ANCHOR_TEMPLATE = u'id%03d'

    def __init__(self, encoding=None,
            explicit_start=None, explicit_end=None, version=None, tags=None):
        self.use_encoding = encoding
        self.use_explicit_start = explicit_start
        self.use_explicit_end = explicit_end
        self.use_version = version
        self.use_tags = tags
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_anchor_id = 0
        self.closed = None

    def open(self):
        if self.closed is None:
            self.emit(StreamStartEvent(encoding=self.use_encoding))
            self.closed = False
        elif self.closed:
            raise SerializerError("serializer is closed")
        else:
            raise SerializerError("serializer is already opened")

    def close(self):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif not self.closed:
            self.emit(StreamEndEvent())
            self.closed = True

    #def __del__(self):
    #    self.close()

    def serialize(self, node):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif self.closed:
            raise SerializerError("serializer is closed")
        self.emit(DocumentStartEvent(explicit=self.use_explicit_start,
            version=self.use_version, tags=self.use_tags))
        self.anchor_node(node)
        self.serialize_node(node, None, None)
        self.emit(DocumentEndEvent(explicit=self.use_explicit_end))
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_anchor_id = 0

    def anchor_node(self, node):
        if node in self.anchors:
            if self.anchors[node] is None:
                self.anchors[node] = self.generate_anchor(node)
        else:
            self.anchors[node] = None
            if isinstance(node, SequenceNode):
                for item in node.value:
                    self.anchor_node(item)
            elif isinstance(node, MappingNode):
                for key, value in node.value:
                    self.anchor_node(key)
                    self.anchor_node(value)

    def generate_anchor(self, node):
        self.last_anchor_id += 1
        return self.ANCHOR_TEMPLATE % self.last_anchor_id

    def serialize_node(self, node, parent, index):
        alias = self.anchors[node]
        if node in self.serialized_nodes:
            self.emit(AliasEvent(alias))
        else:
            self.serialized_nodes[node] = True
            self.descend_resolver(parent, index)
            if isinstance(node, ScalarNode):
                detected_tag = self.resolve(ScalarNode, node.value, (True, False))
                default_tag = self.resolve(ScalarNode, node.value, (False, True))
                implicit = (node.tag == detected_tag), (node.tag == default_tag)
                self.emit(ScalarEvent(alias, node.tag, implicit, node.value,
                    style=node.style))
            elif isinstance(node, SequenceNode):
                implicit = (node.tag
                            == self.resolve(SequenceNode, node.value, True))
                self.emit(SequenceStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                index = 0
                for item in node.value:
                    self.serialize_node(item, node, index)
                    index += 1
                self.emit(SequenceEndEvent())
            elif isinstance(node, MappingNode):
                implicit = (node.tag
                            == self.resolve(MappingNode, node.value, True))
                self.emit(MappingStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                for key, value in node.value:
                    self.serialize_node(key, node, None)
                    self.serialize_node(value, node, key)
                self.emit(MappingEndEvent())
            self.ascend_resolver()


########NEW FILE########
__FILENAME__ = tokens

class Token(object):
    def __init__(self, start_mark, end_mark):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in self.__dict__
                if not key.endswith('_mark')]
        attributes.sort()
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

#class BOMToken(Token):
#    id = '<byte order mark>'

class DirectiveToken(Token):
    id = '<directive>'
    def __init__(self, name, value, start_mark, end_mark):
        self.name = name
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class DocumentStartToken(Token):
    id = '<document start>'

class DocumentEndToken(Token):
    id = '<document end>'

class StreamStartToken(Token):
    id = '<stream start>'
    def __init__(self, start_mark=None, end_mark=None,
            encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndToken(Token):
    id = '<stream end>'

class BlockSequenceStartToken(Token):
    id = '<block sequence start>'

class BlockMappingStartToken(Token):
    id = '<block mapping start>'

class BlockEndToken(Token):
    id = '<block end>'

class FlowSequenceStartToken(Token):
    id = '['

class FlowMappingStartToken(Token):
    id = '{'

class FlowSequenceEndToken(Token):
    id = ']'

class FlowMappingEndToken(Token):
    id = '}'

class KeyToken(Token):
    id = '?'

class ValueToken(Token):
    id = ':'

class BlockEntryToken(Token):
    id = '-'

class FlowEntryToken(Token):
    id = ','

class AliasToken(Token):
    id = '<alias>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class AnchorToken(Token):
    id = '<anchor>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class TagToken(Token):
    id = '<tag>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class ScalarToken(Token):
    id = '<scalar>'
    def __init__(self, value, plain, start_mark, end_mark, style=None):
        self.value = value
        self.plain = plain
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style


########NEW FILE########
__FILENAME__ = composer

__all__ = ['Composer', 'ComposerError']

from .error import MarkedYAMLError
from .events import *
from .nodes import *

class ComposerError(MarkedYAMLError):
    pass

class Composer:

    def __init__(self):
        self.anchors = {}

    def check_node(self):
        # Drop the STREAM-START event.
        if self.check_event(StreamStartEvent):
            self.get_event()

        # If there are more documents available?
        return not self.check_event(StreamEndEvent)

    def get_node(self):
        # Get the root node of the next document.
        if not self.check_event(StreamEndEvent):
            return self.compose_document()

    def get_single_node(self):
        # Drop the STREAM-START event.
        self.get_event()

        # Compose a document if the stream is not empty.
        document = None
        if not self.check_event(StreamEndEvent):
            document = self.compose_document()

        # Ensure that the stream contains no more documents.
        if not self.check_event(StreamEndEvent):
            event = self.get_event()
            raise ComposerError("expected a single document in the stream",
                    document.start_mark, "but found another document",
                    event.start_mark)

        # Drop the STREAM-END event.
        self.get_event()

        return document

    def compose_document(self):
        # Drop the DOCUMENT-START event.
        self.get_event()

        # Compose the root node.
        node = self.compose_node(None, None)

        # Drop the DOCUMENT-END event.
        self.get_event()

        self.anchors = {}
        return node

    def compose_node(self, parent, index):
        if self.check_event(AliasEvent):
            event = self.get_event()
            anchor = event.anchor
            if anchor not in self.anchors:
                raise ComposerError(None, None, "found undefined alias %r"
                        % anchor, event.start_mark)
            return self.anchors[anchor]
        event = self.peek_event()
        anchor = event.anchor
        if anchor is not None:
            if anchor in self.anchors:
                raise ComposerError("found duplicate anchor %r; first occurence"
                        % anchor, self.anchors[anchor].start_mark,
                        "second occurence", event.start_mark)
        self.descend_resolver(parent, index)
        if self.check_event(ScalarEvent):
            node = self.compose_scalar_node(anchor)
        elif self.check_event(SequenceStartEvent):
            node = self.compose_sequence_node(anchor)
        elif self.check_event(MappingStartEvent):
            node = self.compose_mapping_node(anchor)
        self.ascend_resolver()
        return node

    def compose_scalar_node(self, anchor):
        event = self.get_event()
        tag = event.tag
        if tag is None or tag == '!':
            tag = self.resolve(ScalarNode, event.value, event.implicit)
        node = ScalarNode(tag, event.value,
                event.start_mark, event.end_mark, style=event.style)
        if anchor is not None:
            self.anchors[anchor] = node
        return node

    def compose_sequence_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == '!':
            tag = self.resolve(SequenceNode, None, start_event.implicit)
        node = SequenceNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        index = 0
        while not self.check_event(SequenceEndEvent):
            node.value.append(self.compose_node(node, index))
            index += 1
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node

    def compose_mapping_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == '!':
            tag = self.resolve(MappingNode, None, start_event.implicit)
        node = MappingNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        while not self.check_event(MappingEndEvent):
            #key_event = self.peek_event()
            item_key = self.compose_node(node, None)
            #if item_key in node.value:
            #    raise ComposerError("while composing a mapping", start_event.start_mark,
            #            "found duplicate key", key_event.start_mark)
            item_value = self.compose_node(node, item_key)
            #node.value[item_key] = item_value
            node.value.append((item_key, item_value))
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node


########NEW FILE########
__FILENAME__ = constructor

__all__ = ['BaseConstructor', 'SafeConstructor', 'Constructor',
    'ConstructorError']

from .error import *
from .nodes import *

import collections, datetime, base64, binascii, re, sys, types

class ConstructorError(MarkedYAMLError):
    pass

class BaseConstructor:

    yaml_constructors = {}
    yaml_multi_constructors = {}

    def __init__(self):
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.state_generators = []
        self.deep_construct = False

    def check_data(self):
        # If there are more documents available?
        return self.check_node()

    def get_data(self):
        # Construct and return the next document.
        if self.check_node():
            return self.construct_document(self.get_node())

    def get_single_data(self):
        # Ensure that the stream contains a single document and construct it.
        node = self.get_single_node()
        if node is not None:
            return self.construct_document(node)
        return None

    def construct_document(self, node):
        data = self.construct_object(node)
        while self.state_generators:
            state_generators = self.state_generators
            self.state_generators = []
            for generator in state_generators:
                for dummy in generator:
                    pass
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.deep_construct = False
        return data

    def construct_object(self, node, deep=False):
        if node in self.constructed_objects:
            return self.constructed_objects[node]
        if deep:
            old_deep = self.deep_construct
            self.deep_construct = True
        if node in self.recursive_objects:
            raise ConstructorError(None, None,
                    "found unconstructable recursive node", node.start_mark)
        self.recursive_objects[node] = None
        constructor = None
        tag_suffix = None
        if node.tag in self.yaml_constructors:
            constructor = self.yaml_constructors[node.tag]
        else:
            for tag_prefix in self.yaml_multi_constructors:
                if node.tag.startswith(tag_prefix):
                    tag_suffix = node.tag[len(tag_prefix):]
                    constructor = self.yaml_multi_constructors[tag_prefix]
                    break
            else:
                if None in self.yaml_multi_constructors:
                    tag_suffix = node.tag
                    constructor = self.yaml_multi_constructors[None]
                elif None in self.yaml_constructors:
                    constructor = self.yaml_constructors[None]
                elif isinstance(node, ScalarNode):
                    constructor = self.__class__.construct_scalar
                elif isinstance(node, SequenceNode):
                    constructor = self.__class__.construct_sequence
                elif isinstance(node, MappingNode):
                    constructor = self.__class__.construct_mapping
        if tag_suffix is None:
            data = constructor(self, node)
        else:
            data = constructor(self, tag_suffix, node)
        if isinstance(data, types.GeneratorType):
            generator = data
            data = next(generator)
            if self.deep_construct:
                for dummy in generator:
                    pass
            else:
                self.state_generators.append(generator)
        self.constructed_objects[node] = data
        del self.recursive_objects[node]
        if deep:
            self.deep_construct = old_deep
        return data

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            raise ConstructorError(None, None,
                    "expected a scalar node, but found %s" % node.id,
                    node.start_mark)
        return node.value

    def construct_sequence(self, node, deep=False):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None,
                    "expected a sequence node, but found %s" % node.id,
                    node.start_mark)
        return [self.construct_object(child, deep=deep)
                for child in node.value]

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, collections.Hashable):
                raise ConstructorError("while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

    def construct_pairs(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        pairs = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            pairs.append((key, value))
        return pairs

    @classmethod
    def add_constructor(cls, tag, constructor):
        if not 'yaml_constructors' in cls.__dict__:
            cls.yaml_constructors = cls.yaml_constructors.copy()
        cls.yaml_constructors[tag] = constructor

    @classmethod
    def add_multi_constructor(cls, tag_prefix, multi_constructor):
        if not 'yaml_multi_constructors' in cls.__dict__:
            cls.yaml_multi_constructors = cls.yaml_multi_constructors.copy()
        cls.yaml_multi_constructors[tag_prefix] = multi_constructor

class SafeConstructor(BaseConstructor):

    def construct_scalar(self, node):
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if key_node.tag == 'tag:yaml.org,2002:value':
                    return self.construct_scalar(value_node)
        return super().construct_scalar(node)

    def flatten_mapping(self, node):
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == 'tag:yaml.org,2002:merge':
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError("while constructing a mapping",
                                    node.start_mark,
                                    "expected a mapping for merging, but found %s"
                                    % subnode.id, subnode.start_mark)
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "expected a mapping or list of mappings for merging, but found %s"
                            % value_node.id, value_node.start_mark)
            elif key_node.tag == 'tag:yaml.org,2002:value':
                key_node.tag = 'tag:yaml.org,2002:str'
                index += 1
            else:
                index += 1
        if merge:
            node.value = merge + node.value

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        return super().construct_mapping(node, deep=deep)

    def construct_yaml_null(self, node):
        self.construct_scalar(node)
        return None

    bool_values = {
        'yes':      True,
        'no':       False,
        'true':     True,
        'false':    False,
        'on':       True,
        'off':      False,
    }

    def construct_yaml_bool(self, node):
        value = self.construct_scalar(node)
        return self.bool_values[value.lower()]

    def construct_yaml_int(self, node):
        value = self.construct_scalar(node)
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value[0] == '0':
            return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

    inf_value = 1e300
    while inf_value != inf_value*inf_value:
        inf_value *= inf_value
    nan_value = -inf_value/inf_value   # Trying to make a quiet NaN (like C99).

    def construct_yaml_float(self, node):
        value = self.construct_scalar(node)
        value = value.replace('_', '').lower()
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '.inf':
            return sign*self.inf_value
        elif value == '.nan':
            return self.nan_value
        elif ':' in value:
            digits = [float(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0.0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*float(value)

    def construct_yaml_binary(self, node):
        try:
            value = self.construct_scalar(node).encode('ascii')
        except UnicodeEncodeError as exc:
            raise ConstructorError(None, None,
                    "failed to convert base64 data into ascii: %s" % exc,
                    node.start_mark)
        try:
            if hasattr(base64, 'decodebytes'):
                return base64.decodebytes(value)
            else:
                return base64.decodestring(value)
        except binascii.Error as exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark)

    timestamp_regexp = re.compile(
            r'''^(?P<year>[0-9][0-9][0-9][0-9])
                -(?P<month>[0-9][0-9]?)
                -(?P<day>[0-9][0-9]?)
                (?:(?:[Tt]|[ \t]+)
                (?P<hour>[0-9][0-9]?)
                :(?P<minute>[0-9][0-9])
                :(?P<second>[0-9][0-9])
                (?:\.(?P<fraction>[0-9]*))?
                (?:[ \t]*(?P<tz>Z|(?P<tz_sign>[-+])(?P<tz_hour>[0-9][0-9]?)
                (?::(?P<tz_minute>[0-9][0-9]))?))?)?$''', re.X)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        year = int(values['year'])
        month = int(values['month'])
        day = int(values['day'])
        if not values['hour']:
            return datetime.date(year, month, day)
        hour = int(values['hour'])
        minute = int(values['minute'])
        second = int(values['second'])
        fraction = 0
        if values['fraction']:
            fraction = values['fraction'][:6]
            while len(fraction) < 6:
                fraction += '0'
            fraction = int(fraction)
        delta = None
        if values['tz_sign']:
            tz_hour = int(values['tz_hour'])
            tz_minute = int(values['tz_minute'] or 0)
            delta = datetime.timedelta(hours=tz_hour, minutes=tz_minute)
            if values['tz_sign'] == '-':
                delta = -delta
        data = datetime.datetime(year, month, day, hour, minute, second, fraction)
        if delta:
            data -= delta
        return data

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        omap = []
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap.append((key, value))

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = []
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing pairs", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = set()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        return self.construct_scalar(node)

    def construct_yaml_seq(self, node):
        data = []
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = {}
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = cls.__new__(cls)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)

    def construct_undefined(self, node):
        raise ConstructorError(None, None,
                "could not determine a constructor for the tag %r" % node.tag,
                node.start_mark)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:null',
        SafeConstructor.construct_yaml_null)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:bool',
        SafeConstructor.construct_yaml_bool)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:int',
        SafeConstructor.construct_yaml_int)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:float',
        SafeConstructor.construct_yaml_float)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:binary',
        SafeConstructor.construct_yaml_binary)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:timestamp',
        SafeConstructor.construct_yaml_timestamp)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:omap',
        SafeConstructor.construct_yaml_omap)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:pairs',
        SafeConstructor.construct_yaml_pairs)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:set',
        SafeConstructor.construct_yaml_set)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:str',
        SafeConstructor.construct_yaml_str)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:seq',
        SafeConstructor.construct_yaml_seq)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:map',
        SafeConstructor.construct_yaml_map)

SafeConstructor.add_constructor(None,
        SafeConstructor.construct_undefined)

class Constructor(SafeConstructor):

    def construct_python_str(self, node):
        return self.construct_scalar(node)

    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

    def construct_python_bytes(self, node):
        try:
            value = self.construct_scalar(node).encode('ascii')
        except UnicodeEncodeError as exc:
            raise ConstructorError(None, None,
                    "failed to convert base64 data into ascii: %s" % exc,
                    node.start_mark)
        try:
            if hasattr(base64, 'decodebytes'):
                return base64.decodebytes(value)
            else:
                return base64.decodestring(value)
        except binascii.Error as exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark)

    def construct_python_long(self, node):
        return self.construct_yaml_int(node)

    def construct_python_complex(self, node):
       return complex(self.construct_scalar(node))

    def construct_python_tuple(self, node):
        return tuple(self.construct_sequence(node))

    def find_python_module(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python module", mark,
                    "expected non-empty name appended to the tag", mark)
        try:
            __import__(name)
        except ImportError as exc:
            raise ConstructorError("while constructing a Python module", mark,
                    "cannot find module %r (%s)" % (name, exc), mark)
        return sys.modules[name]

    def find_python_name(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python object", mark,
                    "expected non-empty name appended to the tag", mark)
        if '.' in name:
            module_name, object_name = name.rsplit('.', 1)
        else:
            module_name = 'builtins'
            object_name = name
        try:
            __import__(module_name)
        except ImportError as exc:
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find module %r (%s)" % (module_name, exc), mark)
        module = sys.modules[module_name]
        if not hasattr(module, object_name):
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find %r in the module %r"
                    % (object_name, module.__name__), mark)
        return getattr(module, object_name)

    def construct_python_name(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python name", node.start_mark,
                    "expected the empty value, but found %r" % value, node.start_mark)
        return self.find_python_name(suffix, node.start_mark)

    def construct_python_module(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python module", node.start_mark,
                    "expected the empty value, but found %r" % value, node.start_mark)
        return self.find_python_module(suffix, node.start_mark)

    def make_python_instance(self, suffix, node,
            args=None, kwds=None, newobj=False):
        if not args:
            args = []
        if not kwds:
            kwds = {}
        cls = self.find_python_name(suffix, node.start_mark)
        if newobj and isinstance(cls, type):
            return cls.__new__(cls, *args, **kwds)
        else:
            return cls(*args, **kwds)

    def set_python_instance_state(self, instance, state):
        if hasattr(instance, '__setstate__'):
            instance.__setstate__(state)
        else:
            slotstate = {}
            if isinstance(state, tuple) and len(state) == 2:
                state, slotstate = state
            if hasattr(instance, '__dict__'):
                instance.__dict__.update(state)
            elif state:
                slotstate.update(state)
            for key, value in slotstate.items():
                setattr(object, key, value)

    def construct_python_object(self, suffix, node):
        # Format:
        #   !!python/object:module.name { ... state ... }
        instance = self.make_python_instance(suffix, node, newobj=True)
        yield instance
        deep = hasattr(instance, '__setstate__')
        state = self.construct_mapping(node, deep=deep)
        self.set_python_instance_state(instance, state)

    def construct_python_object_apply(self, suffix, node, newobj=False):
        # Format:
        #   !!python/object/apply       # (or !!python/object/new)
        #   args: [ ... arguments ... ]
        #   kwds: { ... keywords ... }
        #   state: ... state ...
        #   listitems: [ ... listitems ... ]
        #   dictitems: { ... dictitems ... }
        # or short format:
        #   !!python/object/apply [ ... arguments ... ]
        # The difference between !!python/object/apply and !!python/object/new
        # is how an object is created, check make_python_instance for details.
        if isinstance(node, SequenceNode):
            args = self.construct_sequence(node, deep=True)
            kwds = {}
            state = {}
            listitems = []
            dictitems = {}
        else:
            value = self.construct_mapping(node, deep=True)
            args = value.get('args', [])
            kwds = value.get('kwds', {})
            state = value.get('state', {})
            listitems = value.get('listitems', [])
            dictitems = value.get('dictitems', {})
        instance = self.make_python_instance(suffix, node, args, kwds, newobj)
        if state:
            self.set_python_instance_state(instance, state)
        if listitems:
            instance.extend(listitems)
        if dictitems:
            for key in dictitems:
                instance[key] = dictitems[key]
        return instance

    def construct_python_object_new(self, suffix, node):
        return self.construct_python_object_apply(suffix, node, newobj=True)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/none',
    Constructor.construct_yaml_null)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/bool',
    Constructor.construct_yaml_bool)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/str',
    Constructor.construct_python_str)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/unicode',
    Constructor.construct_python_unicode)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/bytes',
    Constructor.construct_python_bytes)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/int',
    Constructor.construct_yaml_int)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/long',
    Constructor.construct_python_long)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/float',
    Constructor.construct_yaml_float)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/complex',
    Constructor.construct_python_complex)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/list',
    Constructor.construct_yaml_seq)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/tuple',
    Constructor.construct_python_tuple)

Constructor.add_constructor(
    'tag:yaml.org,2002:python/dict',
    Constructor.construct_yaml_map)

Constructor.add_multi_constructor(
    'tag:yaml.org,2002:python/name:',
    Constructor.construct_python_name)

Constructor.add_multi_constructor(
    'tag:yaml.org,2002:python/module:',
    Constructor.construct_python_module)

Constructor.add_multi_constructor(
    'tag:yaml.org,2002:python/object:',
    Constructor.construct_python_object)

Constructor.add_multi_constructor(
    'tag:yaml.org,2002:python/object/apply:',
    Constructor.construct_python_object_apply)

Constructor.add_multi_constructor(
    'tag:yaml.org,2002:python/object/new:',
    Constructor.construct_python_object_new)


########NEW FILE########
__FILENAME__ = cyaml

__all__ = ['CBaseLoader', 'CSafeLoader', 'CLoader',
        'CBaseDumper', 'CSafeDumper', 'CDumper']

from _yaml import CParser, CEmitter

from .constructor import *

from .serializer import *
from .representer import *

from .resolver import *

class CBaseLoader(CParser, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class CSafeLoader(CParser, SafeConstructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class CLoader(CParser, Constructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        Constructor.__init__(self)
        Resolver.__init__(self)

class CBaseDumper(CEmitter, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CSafeDumper(CEmitter, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CDumper(CEmitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width, encoding=encoding,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = dumper

__all__ = ['BaseDumper', 'SafeDumper', 'Dumper']

from .emitter import *
from .serializer import *
from .representer import *
from .resolver import *

class BaseDumper(Emitter, Serializer, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class SafeDumper(Emitter, Serializer, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class Dumper(Emitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = emitter

# Emitter expects events obeying the following grammar:
# stream ::= STREAM-START document* STREAM-END
# document ::= DOCUMENT-START node DOCUMENT-END
# node ::= SCALAR | sequence | mapping
# sequence ::= SEQUENCE-START node* SEQUENCE-END
# mapping ::= MAPPING-START (node node)* MAPPING-END

__all__ = ['Emitter', 'EmitterError']

from .error import YAMLError
from .events import *

class EmitterError(YAMLError):
    pass

class ScalarAnalysis:
    def __init__(self, scalar, empty, multiline,
            allow_flow_plain, allow_block_plain,
            allow_single_quoted, allow_double_quoted,
            allow_block):
        self.scalar = scalar
        self.empty = empty
        self.multiline = multiline
        self.allow_flow_plain = allow_flow_plain
        self.allow_block_plain = allow_block_plain
        self.allow_single_quoted = allow_single_quoted
        self.allow_double_quoted = allow_double_quoted
        self.allow_block = allow_block

class Emitter:

    DEFAULT_TAG_PREFIXES = {
        '!' : '!',
        'tag:yaml.org,2002:' : '!!',
    }

    def __init__(self, stream, canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None):

        # The stream should have the methods `write` and possibly `flush`.
        self.stream = stream

        # Encoding can be overriden by STREAM-START.
        self.encoding = None

        # Emitter is a state machine with a stack of states to handle nested
        # structures.
        self.states = []
        self.state = self.expect_stream_start

        # Current event and the event queue.
        self.events = []
        self.event = None

        # The current indentation level and the stack of previous indents.
        self.indents = []
        self.indent = None

        # Flow level.
        self.flow_level = 0

        # Contexts.
        self.root_context = False
        self.sequence_context = False
        self.mapping_context = False
        self.simple_key_context = False

        # Characteristics of the last emitted character:
        #  - current position.
        #  - is it a whitespace?
        #  - is it an indention character
        #    (indentation space, '-', '?', or ':')?
        self.line = 0
        self.column = 0
        self.whitespace = True
        self.indention = True

        # Whether the document requires an explicit document indicator
        self.open_ended = False

        # Formatting details.
        self.canonical = canonical
        self.allow_unicode = allow_unicode
        self.best_indent = 2
        if indent and 1 < indent < 10:
            self.best_indent = indent
        self.best_width = 80
        if width and width > self.best_indent*2:
            self.best_width = width
        self.best_line_break = '\n'
        if line_break in ['\r', '\n', '\r\n']:
            self.best_line_break = line_break

        # Tag prefixes.
        self.tag_prefixes = None

        # Prepared anchor and tag.
        self.prepared_anchor = None
        self.prepared_tag = None

        # Scalar analysis and style.
        self.analysis = None
        self.style = None

    def dispose(self):
        # Reset the state attributes (to clear self-references)
        self.states = []
        self.state = None

    def emit(self, event):
        self.events.append(event)
        while not self.need_more_events():
            self.event = self.events.pop(0)
            self.state()
            self.event = None

    # In some cases, we wait for a few next events before emitting.

    def need_more_events(self):
        if not self.events:
            return True
        event = self.events[0]
        if isinstance(event, DocumentStartEvent):
            return self.need_events(1)
        elif isinstance(event, SequenceStartEvent):
            return self.need_events(2)
        elif isinstance(event, MappingStartEvent):
            return self.need_events(3)
        else:
            return False

    def need_events(self, count):
        level = 0
        for event in self.events[1:]:
            if isinstance(event, (DocumentStartEvent, CollectionStartEvent)):
                level += 1
            elif isinstance(event, (DocumentEndEvent, CollectionEndEvent)):
                level -= 1
            elif isinstance(event, StreamEndEvent):
                level = -1
            if level < 0:
                return False
        return (len(self.events) < count+1)

    def increase_indent(self, flow=False, indentless=False):
        self.indents.append(self.indent)
        if self.indent is None:
            if flow:
                self.indent = self.best_indent
            else:
                self.indent = 0
        elif not indentless:
            self.indent += self.best_indent

    # States.

    # Stream handlers.

    def expect_stream_start(self):
        if isinstance(self.event, StreamStartEvent):
            if self.event.encoding and not hasattr(self.stream, 'encoding'):
                self.encoding = self.event.encoding
            self.write_stream_start()
            self.state = self.expect_first_document_start
        else:
            raise EmitterError("expected StreamStartEvent, but got %s"
                    % self.event)

    def expect_nothing(self):
        raise EmitterError("expected nothing, but got %s" % self.event)

    # Document handlers.

    def expect_first_document_start(self):
        return self.expect_document_start(first=True)

    def expect_document_start(self, first=False):
        if isinstance(self.event, DocumentStartEvent):
            if (self.event.version or self.event.tags) and self.open_ended:
                self.write_indicator('...', True)
                self.write_indent()
            if self.event.version:
                version_text = self.prepare_version(self.event.version)
                self.write_version_directive(version_text)
            self.tag_prefixes = self.DEFAULT_TAG_PREFIXES.copy()
            if self.event.tags:
                handles = sorted(self.event.tags.keys())
                for handle in handles:
                    prefix = self.event.tags[handle]
                    self.tag_prefixes[prefix] = handle
                    handle_text = self.prepare_tag_handle(handle)
                    prefix_text = self.prepare_tag_prefix(prefix)
                    self.write_tag_directive(handle_text, prefix_text)
            implicit = (first and not self.event.explicit and not self.canonical
                    and not self.event.version and not self.event.tags
                    and not self.check_empty_document())
            if not implicit:
                self.write_indent()
                self.write_indicator('---', True)
                if self.canonical:
                    self.write_indent()
            self.state = self.expect_document_root
        elif isinstance(self.event, StreamEndEvent):
            if self.open_ended:
                self.write_indicator('...', True)
                self.write_indent()
            self.write_stream_end()
            self.state = self.expect_nothing
        else:
            raise EmitterError("expected DocumentStartEvent, but got %s"
                    % self.event)

    def expect_document_end(self):
        if isinstance(self.event, DocumentEndEvent):
            self.write_indent()
            if self.event.explicit:
                self.write_indicator('...', True)
                self.write_indent()
            self.flush_stream()
            self.state = self.expect_document_start
        else:
            raise EmitterError("expected DocumentEndEvent, but got %s"
                    % self.event)

    def expect_document_root(self):
        self.states.append(self.expect_document_end)
        self.expect_node(root=True)

    # Node handlers.

    def expect_node(self, root=False, sequence=False, mapping=False,
            simple_key=False):
        self.root_context = root
        self.sequence_context = sequence
        self.mapping_context = mapping
        self.simple_key_context = simple_key
        if isinstance(self.event, AliasEvent):
            self.expect_alias()
        elif isinstance(self.event, (ScalarEvent, CollectionStartEvent)):
            self.process_anchor('&')
            self.process_tag()
            if isinstance(self.event, ScalarEvent):
                self.expect_scalar()
            elif isinstance(self.event, SequenceStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_sequence():
                    self.expect_flow_sequence()
                else:
                    self.expect_block_sequence()
            elif isinstance(self.event, MappingStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_mapping():
                    self.expect_flow_mapping()
                else:
                    self.expect_block_mapping()
        else:
            raise EmitterError("expected NodeEvent, but got %s" % self.event)

    def expect_alias(self):
        if self.event.anchor is None:
            raise EmitterError("anchor is not specified for alias")
        self.process_anchor('*')
        self.state = self.states.pop()

    def expect_scalar(self):
        self.increase_indent(flow=True)
        self.process_scalar()
        self.indent = self.indents.pop()
        self.state = self.states.pop()

    # Flow sequence handlers.

    def expect_flow_sequence(self):
        self.write_indicator('[', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_sequence_item

    def expect_first_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(']', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    def expect_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(',', False)
                self.write_indent()
            self.write_indicator(']', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    # Flow mapping handlers.

    def expect_flow_mapping(self):
        self.write_indicator('{', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_mapping_key

    def expect_first_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator('}', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator('?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(',', False)
                self.write_indent()
            self.write_indicator('}', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator('?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_simple_value(self):
        self.write_indicator(':', False)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    def expect_flow_mapping_value(self):
        if self.canonical or self.column > self.best_width:
            self.write_indent()
        self.write_indicator(':', True)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    # Block sequence handlers.

    def expect_block_sequence(self):
        indentless = (self.mapping_context and not self.indention)
        self.increase_indent(flow=False, indentless=indentless)
        self.state = self.expect_first_block_sequence_item

    def expect_first_block_sequence_item(self):
        return self.expect_block_sequence_item(first=True)

    def expect_block_sequence_item(self, first=False):
        if not first and isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            self.write_indicator('-', True, indention=True)
            self.states.append(self.expect_block_sequence_item)
            self.expect_node(sequence=True)

    # Block mapping handlers.

    def expect_block_mapping(self):
        self.increase_indent(flow=False)
        self.state = self.expect_first_block_mapping_key

    def expect_first_block_mapping_key(self):
        return self.expect_block_mapping_key(first=True)

    def expect_block_mapping_key(self, first=False):
        if not first and isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            if self.check_simple_key():
                self.states.append(self.expect_block_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator('?', True, indention=True)
                self.states.append(self.expect_block_mapping_value)
                self.expect_node(mapping=True)

    def expect_block_mapping_simple_value(self):
        self.write_indicator(':', False)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    def expect_block_mapping_value(self):
        self.write_indent()
        self.write_indicator(':', True, indention=True)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    # Checkers.

    def check_empty_sequence(self):
        return (isinstance(self.event, SequenceStartEvent) and self.events
                and isinstance(self.events[0], SequenceEndEvent))

    def check_empty_mapping(self):
        return (isinstance(self.event, MappingStartEvent) and self.events
                and isinstance(self.events[0], MappingEndEvent))

    def check_empty_document(self):
        if not isinstance(self.event, DocumentStartEvent) or not self.events:
            return False
        event = self.events[0]
        return (isinstance(event, ScalarEvent) and event.anchor is None
                and event.tag is None and event.implicit and event.value == '')

    def check_simple_key(self):
        length = 0
        if isinstance(self.event, NodeEvent) and self.event.anchor is not None:
            if self.prepared_anchor is None:
                self.prepared_anchor = self.prepare_anchor(self.event.anchor)
            length += len(self.prepared_anchor)
        if isinstance(self.event, (ScalarEvent, CollectionStartEvent))  \
                and self.event.tag is not None:
            if self.prepared_tag is None:
                self.prepared_tag = self.prepare_tag(self.event.tag)
            length += len(self.prepared_tag)
        if isinstance(self.event, ScalarEvent):
            if self.analysis is None:
                self.analysis = self.analyze_scalar(self.event.value)
            length += len(self.analysis.scalar)
        return (length < 128 and (isinstance(self.event, AliasEvent)
            or (isinstance(self.event, ScalarEvent)
                    and not self.analysis.empty and not self.analysis.multiline)
            or self.check_empty_sequence() or self.check_empty_mapping()))

    # Anchor, Tag, and Scalar processors.

    def process_anchor(self, indicator):
        if self.event.anchor is None:
            self.prepared_anchor = None
            return
        if self.prepared_anchor is None:
            self.prepared_anchor = self.prepare_anchor(self.event.anchor)
        if self.prepared_anchor:
            self.write_indicator(indicator+self.prepared_anchor, True)
        self.prepared_anchor = None

    def process_tag(self):
        tag = self.event.tag
        if isinstance(self.event, ScalarEvent):
            if self.style is None:
                self.style = self.choose_scalar_style()
            if ((not self.canonical or tag is None) and
                ((self.style == '' and self.event.implicit[0])
                        or (self.style != '' and self.event.implicit[1]))):
                self.prepared_tag = None
                return
            if self.event.implicit[0] and tag is None:
                tag = '!'
                self.prepared_tag = None
        else:
            if (not self.canonical or tag is None) and self.event.implicit:
                self.prepared_tag = None
                return
        if tag is None:
            raise EmitterError("tag is not specified")
        if self.prepared_tag is None:
            self.prepared_tag = self.prepare_tag(tag)
        if self.prepared_tag:
            self.write_indicator(self.prepared_tag, True)
        self.prepared_tag = None

    def choose_scalar_style(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.event.style == '"' or self.canonical:
            return '"'
        if not self.event.style and self.event.implicit[0]:
            if (not (self.simple_key_context and
                    (self.analysis.empty or self.analysis.multiline))
                and (self.flow_level and self.analysis.allow_flow_plain
                    or (not self.flow_level and self.analysis.allow_block_plain))):
                return ''
        if self.event.style and self.event.style in '|>':
            if (not self.flow_level and not self.simple_key_context
                    and self.analysis.allow_block):
                return self.event.style
        if not self.event.style or self.event.style == '\'':
            if (self.analysis.allow_single_quoted and
                    not (self.simple_key_context and self.analysis.multiline)):
                return '\''
        return '"'

    def process_scalar(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.style is None:
            self.style = self.choose_scalar_style()
        split = (not self.simple_key_context)
        #if self.analysis.multiline and split    \
        #        and (not self.style or self.style in '\'\"'):
        #    self.write_indent()
        if self.style == '"':
            self.write_double_quoted(self.analysis.scalar, split)
        elif self.style == '\'':
            self.write_single_quoted(self.analysis.scalar, split)
        elif self.style == '>':
            self.write_folded(self.analysis.scalar)
        elif self.style == '|':
            self.write_literal(self.analysis.scalar)
        else:
            self.write_plain(self.analysis.scalar, split)
        self.analysis = None
        self.style = None

    # Analyzers.

    def prepare_version(self, version):
        major, minor = version
        if major != 1:
            raise EmitterError("unsupported YAML version: %d.%d" % (major, minor))
        return '%d.%d' % (major, minor)

    def prepare_tag_handle(self, handle):
        if not handle:
            raise EmitterError("tag handle must not be empty")
        if handle[0] != '!' or handle[-1] != '!':
            raise EmitterError("tag handle must start and end with '!': %r" % handle)
        for ch in handle[1:-1]:
            if not ('0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'    \
                    or ch in '-_'):
                raise EmitterError("invalid character %r in the tag handle: %r"
                        % (ch, handle))
        return handle

    def prepare_tag_prefix(self, prefix):
        if not prefix:
            raise EmitterError("tag prefix must not be empty")
        chunks = []
        start = end = 0
        if prefix[0] == '!':
            end = 1
        while end < len(prefix):
            ch = prefix[end]
            if '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z' \
                    or ch in '-;/?!:@&=+$,_.~*\'()[]':
                end += 1
            else:
                if start < end:
                    chunks.append(prefix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append('%%%02X' % ord(ch))
        if start < end:
            chunks.append(prefix[start:end])
        return ''.join(chunks)

    def prepare_tag(self, tag):
        if not tag:
            raise EmitterError("tag must not be empty")
        if tag == '!':
            return tag
        handle = None
        suffix = tag
        prefixes = sorted(self.tag_prefixes.keys())
        for prefix in prefixes:
            if tag.startswith(prefix)   \
                    and (prefix == '!' or len(prefix) < len(tag)):
                handle = self.tag_prefixes[prefix]
                suffix = tag[len(prefix):]
        chunks = []
        start = end = 0
        while end < len(suffix):
            ch = suffix[end]
            if '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z' \
                    or ch in '-;/?:@&=+$,_.~*\'()[]'   \
                    or (ch == '!' and handle != '!'):
                end += 1
            else:
                if start < end:
                    chunks.append(suffix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append('%%%02X' % ord(ch))
        if start < end:
            chunks.append(suffix[start:end])
        suffix_text = ''.join(chunks)
        if handle:
            return '%s%s' % (handle, suffix_text)
        else:
            return '!<%s>' % suffix_text

    def prepare_anchor(self, anchor):
        if not anchor:
            raise EmitterError("anchor must not be empty")
        for ch in anchor:
            if not ('0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'    \
                    or ch in '-_'):
                raise EmitterError("invalid character %r in the anchor: %r"
                        % (ch, anchor))
        return anchor

    def analyze_scalar(self, scalar):

        # Empty scalar is a special case.
        if not scalar:
            return ScalarAnalysis(scalar=scalar, empty=True, multiline=False,
                    allow_flow_plain=False, allow_block_plain=True,
                    allow_single_quoted=True, allow_double_quoted=True,
                    allow_block=False)

        # Indicators and special characters.
        block_indicators = False
        flow_indicators = False
        line_breaks = False
        special_characters = False

        # Important whitespace combinations.
        leading_space = False
        leading_break = False
        trailing_space = False
        trailing_break = False
        break_space = False
        space_break = False

        # Check document indicators.
        if scalar.startswith('---') or scalar.startswith('...'):
            block_indicators = True
            flow_indicators = True

        # First character or preceded by a whitespace.
        preceeded_by_whitespace = True

        # Last character or followed by a whitespace.
        followed_by_whitespace = (len(scalar) == 1 or
                scalar[1] in '\0 \t\r\n\x85\u2028\u2029')

        # The previous character is a space.
        previous_space = False

        # The previous character is a break.
        previous_break = False

        index = 0
        while index < len(scalar):
            ch = scalar[index]

            # Check for indicators.
            if index == 0:
                # Leading indicators are special characters.
                if ch in '#,[]{}&*!|>\'\"%@`': 
                    flow_indicators = True
                    block_indicators = True
                if ch in '?:':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == '-' and followed_by_whitespace:
                    flow_indicators = True
                    block_indicators = True
            else:
                # Some indicators cannot appear within a scalar as well.
                if ch in ',?[]{}':
                    flow_indicators = True
                if ch == ':':
                    flow_indicators = True
                    if followed_by_whitespace:
                        block_indicators = True
                if ch == '#' and preceeded_by_whitespace:
                    flow_indicators = True
                    block_indicators = True

            # Check for line breaks, special, and unicode characters.
            if ch in '\n\x85\u2028\u2029':
                line_breaks = True
            if not (ch == '\n' or '\x20' <= ch <= '\x7E'):
                if (ch == '\x85' or '\xA0' <= ch <= '\uD7FF'
                        or '\uE000' <= ch <= '\uFFFD') and ch != '\uFEFF':
                    unicode_characters = True
                    if not self.allow_unicode:
                        special_characters = True
                else:
                    special_characters = True

            # Detect important whitespace combinations.
            if ch == ' ':
                if index == 0:
                    leading_space = True
                if index == len(scalar)-1:
                    trailing_space = True
                if previous_break:
                    break_space = True
                previous_space = True
                previous_break = False
            elif ch in '\n\x85\u2028\u2029':
                if index == 0:
                    leading_break = True
                if index == len(scalar)-1:
                    trailing_break = True
                if previous_space:
                    space_break = True
                previous_space = False
                previous_break = True
            else:
                previous_space = False
                previous_break = False

            # Prepare for the next character.
            index += 1
            preceeded_by_whitespace = (ch in '\0 \t\r\n\x85\u2028\u2029')
            followed_by_whitespace = (index+1 >= len(scalar) or
                    scalar[index+1] in '\0 \t\r\n\x85\u2028\u2029')

        # Let's decide what styles are allowed.
        allow_flow_plain = True
        allow_block_plain = True
        allow_single_quoted = True
        allow_double_quoted = True
        allow_block = True

        # Leading and trailing whitespaces are bad for plain scalars.
        if (leading_space or leading_break
                or trailing_space or trailing_break):
            allow_flow_plain = allow_block_plain = False

        # We do not permit trailing spaces for block scalars.
        if trailing_space:
            allow_block = False

        # Spaces at the beginning of a new line are only acceptable for block
        # scalars.
        if break_space:
            allow_flow_plain = allow_block_plain = allow_single_quoted = False

        # Spaces followed by breaks, as well as special character are only
        # allowed for double quoted scalars.
        if space_break or special_characters:
            allow_flow_plain = allow_block_plain =  \
            allow_single_quoted = allow_block = False

        # Although the plain scalar writer supports breaks, we never emit
        # multiline plain scalars.
        if line_breaks:
            allow_flow_plain = allow_block_plain = False

        # Flow indicators are forbidden for flow plain scalars.
        if flow_indicators:
            allow_flow_plain = False

        # Block indicators are forbidden for block plain scalars.
        if block_indicators:
            allow_block_plain = False

        return ScalarAnalysis(scalar=scalar,
                empty=False, multiline=line_breaks,
                allow_flow_plain=allow_flow_plain,
                allow_block_plain=allow_block_plain,
                allow_single_quoted=allow_single_quoted,
                allow_double_quoted=allow_double_quoted,
                allow_block=allow_block)

    # Writers.

    def flush_stream(self):
        if hasattr(self.stream, 'flush'):
            self.stream.flush()

    def write_stream_start(self):
        # Write BOM if needed.
        if self.encoding and self.encoding.startswith('utf-16'):
            self.stream.write('\uFEFF'.encode(self.encoding))

    def write_stream_end(self):
        self.flush_stream()

    def write_indicator(self, indicator, need_whitespace,
            whitespace=False, indention=False):
        if self.whitespace or not need_whitespace:
            data = indicator
        else:
            data = ' '+indicator
        self.whitespace = whitespace
        self.indention = self.indention and indention
        self.column += len(data)
        self.open_ended = False
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_indent(self):
        indent = self.indent or 0
        if not self.indention or self.column > indent   \
                or (self.column == indent and not self.whitespace):
            self.write_line_break()
        if self.column < indent:
            self.whitespace = True
            data = ' '*(indent-self.column)
            self.column = indent
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)

    def write_line_break(self, data=None):
        if data is None:
            data = self.best_line_break
        self.whitespace = True
        self.indention = True
        self.line += 1
        self.column = 0
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_version_directive(self, version_text):
        data = '%%YAML %s' % version_text
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    def write_tag_directive(self, handle_text, prefix_text):
        data = '%%TAG %s %s' % (handle_text, prefix_text)
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    # Scalar streams.

    def write_single_quoted(self, text, split=True):
        self.write_indicator('\'', True)
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch is None or ch != ' ':
                    if start+1 == end and self.column > self.best_width and split   \
                            and start != 0 and end != len(text):
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch is None or ch not in '\n\x85\u2028\u2029':
                    if text[start] == '\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    start = end
            else:
                if ch is None or ch in ' \n\x85\u2028\u2029' or ch == '\'':
                    if start < end:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                        start = end
            if ch == '\'':
                data = '\'\''
                self.column += 2
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                start = end + 1
            if ch is not None:
                spaces = (ch == ' ')
                breaks = (ch in '\n\x85\u2028\u2029')
            end += 1
        self.write_indicator('\'', False)

    ESCAPE_REPLACEMENTS = {
        '\0':       '0',
        '\x07':     'a',
        '\x08':     'b',
        '\x09':     't',
        '\x0A':     'n',
        '\x0B':     'v',
        '\x0C':     'f',
        '\x0D':     'r',
        '\x1B':     'e',
        '\"':       '\"',
        '\\':       '\\',
        '\x85':     'N',
        '\xA0':     '_',
        '\u2028':   'L',
        '\u2029':   'P',
    }

    def write_double_quoted(self, text, split=True):
        self.write_indicator('"', True)
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if ch is None or ch in '"\\\x85\u2028\u2029\uFEFF' \
                    or not ('\x20' <= ch <= '\x7E'
                        or (self.allow_unicode
                            and ('\xA0' <= ch <= '\uD7FF'
                                or '\uE000' <= ch <= '\uFFFD'))):
                if start < end:
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
                if ch is not None:
                    if ch in self.ESCAPE_REPLACEMENTS:
                        data = '\\'+self.ESCAPE_REPLACEMENTS[ch]
                    elif ch <= '\xFF':
                        data = '\\x%02X' % ord(ch)
                    elif ch <= '\uFFFF':
                        data = '\\u%04X' % ord(ch)
                    else:
                        data = '\\U%08X' % ord(ch)
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end+1
            if 0 < end < len(text)-1 and (ch == ' ' or start >= end)    \
                    and self.column+(end-start) > self.best_width and split:
                data = text[start:end]+'\\'
                if start < end:
                    start = end
                self.column += len(data)
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                self.write_indent()
                self.whitespace = False
                self.indention = False
                if text[start] == ' ':
                    data = '\\'
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
            end += 1
        self.write_indicator('"', False)

    def determine_block_hints(self, text):
        hints = ''
        if text:
            if text[0] in ' \n\x85\u2028\u2029':
                hints += str(self.best_indent)
            if text[-1] not in '\n\x85\u2028\u2029':
                hints += '-'
            elif len(text) == 1 or text[-2] in '\n\x85\u2028\u2029':
                hints += '+'
        return hints

    def write_folded(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator('>'+hints, True)
        if hints[-1:] == '+':
            self.open_ended = True
        self.write_line_break()
        leading_space = True
        spaces = False
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in '\n\x85\u2028\u2029':
                    if not leading_space and ch is not None and ch != ' '   \
                            and text[start] == '\n':
                        self.write_line_break()
                    leading_space = (ch == ' ')
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            elif spaces:
                if ch != ' ':
                    if start+1 == end and self.column > self.best_width:
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            else:
                if ch is None or ch in ' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in '\n\x85\u2028\u2029')
                spaces = (ch == ' ')
            end += 1

    def write_literal(self, text):
        hints = self.determine_block_hints(text)
        self.write_indicator('|'+hints, True)
        if hints[-1:] == '+':
            self.open_ended = True
        self.write_line_break()
        breaks = True
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in '\n\x85\u2028\u2029':
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            else:
                if ch is None or ch in '\n\x85\u2028\u2029':
                    data = text[start:end]
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in '\n\x85\u2028\u2029')
            end += 1

    def write_plain(self, text, split=True):
        if self.root_context:
            self.open_ended = True
        if not text:
            return
        if not self.whitespace:
            data = ' '
            self.column += len(data)
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)
        self.whitespace = False
        self.indention = False
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch != ' ':
                    if start+1 == end and self.column > self.best_width and split:
                        self.write_indent()
                        self.whitespace = False
                        self.indention = False
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch not in '\n\x85\u2028\u2029':
                    if text[start] == '\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == '\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    self.whitespace = False
                    self.indention = False
                    start = end
            else:
                if ch is None or ch in ' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
            if ch is not None:
                spaces = (ch == ' ')
                breaks = (ch in '\n\x85\u2028\u2029')
            end += 1


########NEW FILE########
__FILENAME__ = error

__all__ = ['Mark', 'YAMLError', 'MarkedYAMLError']

class Mark:

    def __init__(self, name, index, line, column, buffer, pointer):
        self.name = name
        self.index = index
        self.line = line
        self.column = column
        self.buffer = buffer
        self.pointer = pointer

    def get_snippet(self, indent=4, max_length=75):
        if self.buffer is None:
            return None
        head = ''
        start = self.pointer
        while start > 0 and self.buffer[start-1] not in '\0\r\n\x85\u2028\u2029':
            start -= 1
            if self.pointer-start > max_length/2-1:
                head = ' ... '
                start += 5
                break
        tail = ''
        end = self.pointer
        while end < len(self.buffer) and self.buffer[end] not in '\0\r\n\x85\u2028\u2029':
            end += 1
            if end-self.pointer > max_length/2-1:
                tail = ' ... '
                end -= 5
                break
        snippet = self.buffer[start:end]
        return ' '*indent + head + snippet + tail + '\n'  \
                + ' '*(indent+self.pointer-start+len(head)) + '^'

    def __str__(self):
        snippet = self.get_snippet()
        where = "  in \"%s\", line %d, column %d"   \
                % (self.name, self.line+1, self.column+1)
        if snippet is not None:
            where += ":\n"+snippet
        return where

class YAMLError(Exception):
    pass

class MarkedYAMLError(YAMLError):

    def __init__(self, context=None, context_mark=None,
            problem=None, problem_mark=None, note=None):
        self.context = context
        self.context_mark = context_mark
        self.problem = problem
        self.problem_mark = problem_mark
        self.note = note

    def __str__(self):
        lines = []
        if self.context is not None:
            lines.append(self.context)
        if self.context_mark is not None  \
            and (self.problem is None or self.problem_mark is None
                    or self.context_mark.name != self.problem_mark.name
                    or self.context_mark.line != self.problem_mark.line
                    or self.context_mark.column != self.problem_mark.column):
            lines.append(str(self.context_mark))
        if self.problem is not None:
            lines.append(self.problem)
        if self.problem_mark is not None:
            lines.append(str(self.problem_mark))
        if self.note is not None:
            lines.append(self.note)
        return '\n'.join(lines)


########NEW FILE########
__FILENAME__ = events

# Abstract classes.

class Event(object):
    def __init__(self, start_mark=None, end_mark=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in ['anchor', 'tag', 'implicit', 'value']
                if hasattr(self, key)]
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

class NodeEvent(Event):
    def __init__(self, anchor, start_mark=None, end_mark=None):
        self.anchor = anchor
        self.start_mark = start_mark
        self.end_mark = end_mark

class CollectionStartEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, start_mark=None, end_mark=None,
            flow_style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class CollectionEndEvent(Event):
    pass

# Implementations.

class StreamStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None, encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndEvent(Event):
    pass

class DocumentStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None, version=None, tags=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit
        self.version = version
        self.tags = tags

class DocumentEndEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit

class AliasEvent(NodeEvent):
    pass

class ScalarEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, value,
            start_mark=None, end_mark=None, style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class SequenceStartEvent(CollectionStartEvent):
    pass

class SequenceEndEvent(CollectionEndEvent):
    pass

class MappingStartEvent(CollectionStartEvent):
    pass

class MappingEndEvent(CollectionEndEvent):
    pass


########NEW FILE########
__FILENAME__ = loader

__all__ = ['BaseLoader', 'SafeLoader', 'Loader']

from .reader import *
from .scanner import *
from .parser import *
from .composer import *
from .constructor import *
from .resolver import *

class BaseLoader(Reader, Scanner, Parser, Composer, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class SafeLoader(Reader, Scanner, Parser, Composer, SafeConstructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        Constructor.__init__(self)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = nodes

class Node(object):
    def __init__(self, tag, value, start_mark, end_mark):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        value = self.value
        #if isinstance(value, list):
        #    if len(value) == 0:
        #        value = '<empty>'
        #    elif len(value) == 1:
        #        value = '<1 item>'
        #    else:
        #        value = '<%d items>' % len(value)
        #else:
        #    if len(value) > 75:
        #        value = repr(value[:70]+u' ... ')
        #    else:
        #        value = repr(value)
        value = repr(value)
        return '%s(tag=%r, value=%s)' % (self.__class__.__name__, self.tag, value)

class ScalarNode(Node):
    id = 'scalar'
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class CollectionNode(Node):
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, flow_style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class SequenceNode(CollectionNode):
    id = 'sequence'

class MappingNode(CollectionNode):
    id = 'mapping'


########NEW FILE########
__FILENAME__ = parser

# The following YAML grammar is LL(1) and is parsed by a recursive descent
# parser.
#
# stream            ::= STREAM-START implicit_document? explicit_document* STREAM-END
# implicit_document ::= block_node DOCUMENT-END*
# explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*
# block_node_or_indentless_sequence ::=
#                       ALIAS
#                       | properties (block_content | indentless_block_sequence)?
#                       | block_content
#                       | indentless_block_sequence
# block_node        ::= ALIAS
#                       | properties block_content?
#                       | block_content
# flow_node         ::= ALIAS
#                       | properties flow_content?
#                       | flow_content
# properties        ::= TAG ANCHOR? | ANCHOR TAG?
# block_content     ::= block_collection | flow_collection | SCALAR
# flow_content      ::= flow_collection | SCALAR
# block_collection  ::= block_sequence | block_mapping
# flow_collection   ::= flow_sequence | flow_mapping
# block_sequence    ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END
# indentless_sequence   ::= (BLOCK-ENTRY block_node?)+
# block_mapping     ::= BLOCK-MAPPING_START
#                       ((KEY block_node_or_indentless_sequence?)?
#                       (VALUE block_node_or_indentless_sequence?)?)*
#                       BLOCK-END
# flow_sequence     ::= FLOW-SEQUENCE-START
#                       (flow_sequence_entry FLOW-ENTRY)*
#                       flow_sequence_entry?
#                       FLOW-SEQUENCE-END
# flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
# flow_mapping      ::= FLOW-MAPPING-START
#                       (flow_mapping_entry FLOW-ENTRY)*
#                       flow_mapping_entry?
#                       FLOW-MAPPING-END
# flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?
#
# FIRST sets:
#
# stream: { STREAM-START }
# explicit_document: { DIRECTIVE DOCUMENT-START }
# implicit_document: FIRST(block_node)
# block_node: { ALIAS TAG ANCHOR SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_node: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_content: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# flow_content: { FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# block_collection: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_sequence: { BLOCK-SEQUENCE-START }
# block_mapping: { BLOCK-MAPPING-START }
# block_node_or_indentless_sequence: { ALIAS ANCHOR TAG SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START BLOCK-ENTRY }
# indentless_sequence: { ENTRY }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_sequence: { FLOW-SEQUENCE-START }
# flow_mapping: { FLOW-MAPPING-START }
# flow_sequence_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }
# flow_mapping_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }

__all__ = ['Parser', 'ParserError']

from .error import MarkedYAMLError
from .tokens import *
from .events import *
from .scanner import *

class ParserError(MarkedYAMLError):
    pass

class Parser:
    # Since writing a recursive-descendant parser is a straightforward task, we
    # do not give many comments here.

    DEFAULT_TAGS = {
        '!':   '!',
        '!!':  'tag:yaml.org,2002:',
    }

    def __init__(self):
        self.current_event = None
        self.yaml_version = None
        self.tag_handles = {}
        self.states = []
        self.marks = []
        self.state = self.parse_stream_start

    def dispose(self):
        # Reset the state attributes (to clear self-references)
        self.states = []
        self.state = None

    def check_event(self, *choices):
        # Check the type of the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        if self.current_event is not None:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.current_event, choice):
                    return True
        return False

    def peek_event(self):
        # Get the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        return self.current_event

    def get_event(self):
        # Get the next event and proceed further.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        value = self.current_event
        self.current_event = None
        return value

    # stream    ::= STREAM-START implicit_document? explicit_document* STREAM-END
    # implicit_document ::= block_node DOCUMENT-END*
    # explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*

    def parse_stream_start(self):

        # Parse the stream start.
        token = self.get_token()
        event = StreamStartEvent(token.start_mark, token.end_mark,
                encoding=token.encoding)

        # Prepare the next state.
        self.state = self.parse_implicit_document_start

        return event

    def parse_implicit_document_start(self):

        # Parse an implicit document.
        if not self.check_token(DirectiveToken, DocumentStartToken,
                StreamEndToken):
            self.tag_handles = self.DEFAULT_TAGS
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=False)

            # Prepare the next state.
            self.states.append(self.parse_document_end)
            self.state = self.parse_block_node

            return event

        else:
            return self.parse_document_start()

    def parse_document_start(self):

        # Parse any extra document end indicators.
        while self.check_token(DocumentEndToken):
            self.get_token()

        # Parse an explicit document.
        if not self.check_token(StreamEndToken):
            token = self.peek_token()
            start_mark = token.start_mark
            version, tags = self.process_directives()
            if not self.check_token(DocumentStartToken):
                raise ParserError(None, None,
                        "expected '<document start>', but found %r"
                        % self.peek_token().id,
                        self.peek_token().start_mark)
            token = self.get_token()
            end_mark = token.end_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=True, version=version, tags=tags)
            self.states.append(self.parse_document_end)
            self.state = self.parse_document_content
        else:
            # Parse the end of the stream.
            token = self.get_token()
            event = StreamEndEvent(token.start_mark, token.end_mark)
            assert not self.states
            assert not self.marks
            self.state = None
        return event

    def parse_document_end(self):

        # Parse the document end.
        token = self.peek_token()
        start_mark = end_mark = token.start_mark
        explicit = False
        if self.check_token(DocumentEndToken):
            token = self.get_token()
            end_mark = token.end_mark
            explicit = True
        event = DocumentEndEvent(start_mark, end_mark,
                explicit=explicit)

        # Prepare the next state.
        self.state = self.parse_document_start

        return event

    def parse_document_content(self):
        if self.check_token(DirectiveToken,
                DocumentStartToken, DocumentEndToken, StreamEndToken):
            event = self.process_empty_scalar(self.peek_token().start_mark)
            self.state = self.states.pop()
            return event
        else:
            return self.parse_block_node()

    def process_directives(self):
        self.yaml_version = None
        self.tag_handles = {}
        while self.check_token(DirectiveToken):
            token = self.get_token()
            if token.name == 'YAML':
                if self.yaml_version is not None:
                    raise ParserError(None, None,
                            "found duplicate YAML directive", token.start_mark)
                major, minor = token.value
                if major != 1:
                    raise ParserError(None, None,
                            "found incompatible YAML document (version 1.* is required)",
                            token.start_mark)
                self.yaml_version = token.value
            elif token.name == 'TAG':
                handle, prefix = token.value
                if handle in self.tag_handles:
                    raise ParserError(None, None,
                            "duplicate tag handle %r" % handle,
                            token.start_mark)
                self.tag_handles[handle] = prefix
        if self.tag_handles:
            value = self.yaml_version, self.tag_handles.copy()
        else:
            value = self.yaml_version, None
        for key in self.DEFAULT_TAGS:
            if key not in self.tag_handles:
                self.tag_handles[key] = self.DEFAULT_TAGS[key]
        return value

    # block_node_or_indentless_sequence ::= ALIAS
    #               | properties (block_content | indentless_block_sequence)?
    #               | block_content
    #               | indentless_block_sequence
    # block_node    ::= ALIAS
    #                   | properties block_content?
    #                   | block_content
    # flow_node     ::= ALIAS
    #                   | properties flow_content?
    #                   | flow_content
    # properties    ::= TAG ANCHOR? | ANCHOR TAG?
    # block_content     ::= block_collection | flow_collection | SCALAR
    # flow_content      ::= flow_collection | SCALAR
    # block_collection  ::= block_sequence | block_mapping
    # flow_collection   ::= flow_sequence | flow_mapping

    def parse_block_node(self):
        return self.parse_node(block=True)

    def parse_flow_node(self):
        return self.parse_node()

    def parse_block_node_or_indentless_sequence(self):
        return self.parse_node(block=True, indentless_sequence=True)

    def parse_node(self, block=False, indentless_sequence=False):
        if self.check_token(AliasToken):
            token = self.get_token()
            event = AliasEvent(token.value, token.start_mark, token.end_mark)
            self.state = self.states.pop()
        else:
            anchor = None
            tag = None
            start_mark = end_mark = tag_mark = None
            if self.check_token(AnchorToken):
                token = self.get_token()
                start_mark = token.start_mark
                end_mark = token.end_mark
                anchor = token.value
                if self.check_token(TagToken):
                    token = self.get_token()
                    tag_mark = token.start_mark
                    end_mark = token.end_mark
                    tag = token.value
            elif self.check_token(TagToken):
                token = self.get_token()
                start_mark = tag_mark = token.start_mark
                end_mark = token.end_mark
                tag = token.value
                if self.check_token(AnchorToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    anchor = token.value
            if tag is not None:
                handle, suffix = tag
                if handle is not None:
                    if handle not in self.tag_handles:
                        raise ParserError("while parsing a node", start_mark,
                                "found undefined tag handle %r" % handle,
                                tag_mark)
                    tag = self.tag_handles[handle]+suffix
                else:
                    tag = suffix
            #if tag == '!':
            #    raise ParserError("while parsing a node", start_mark,
            #            "found non-specific tag '!'", tag_mark,
            #            "Please check 'http://pyyaml.org/wiki/YAMLNonSpecificTag' and share your opinion.")
            if start_mark is None:
                start_mark = end_mark = self.peek_token().start_mark
            event = None
            implicit = (tag is None or tag == '!')
            if indentless_sequence and self.check_token(BlockEntryToken):
                end_mark = self.peek_token().end_mark
                event = SequenceStartEvent(anchor, tag, implicit,
                        start_mark, end_mark)
                self.state = self.parse_indentless_sequence_entry
            else:
                if self.check_token(ScalarToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    if (token.plain and tag is None) or tag == '!':
                        implicit = (True, False)
                    elif tag is None:
                        implicit = (False, True)
                    else:
                        implicit = (False, False)
                    event = ScalarEvent(anchor, tag, implicit, token.value,
                            start_mark, end_mark, style=token.style)
                    self.state = self.states.pop()
                elif self.check_token(FlowSequenceStartToken):
                    end_mark = self.peek_token().end_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_sequence_first_entry
                elif self.check_token(FlowMappingStartToken):
                    end_mark = self.peek_token().end_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_mapping_first_key
                elif block and self.check_token(BlockSequenceStartToken):
                    end_mark = self.peek_token().start_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_sequence_first_entry
                elif block and self.check_token(BlockMappingStartToken):
                    end_mark = self.peek_token().start_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_mapping_first_key
                elif anchor is not None or tag is not None:
                    # Empty scalars are allowed even if a tag or an anchor is
                    # specified.
                    event = ScalarEvent(anchor, tag, (implicit, False), '',
                            start_mark, end_mark)
                    self.state = self.states.pop()
                else:
                    if block:
                        node = 'block'
                    else:
                        node = 'flow'
                    token = self.peek_token()
                    raise ParserError("while parsing a %s node" % node, start_mark,
                            "expected the node content, but found %r" % token.id,
                            token.start_mark)
        return event

    # block_sequence ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END

    def parse_block_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_sequence_entry()

    def parse_block_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken, BlockEndToken):
                self.states.append(self.parse_block_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_block_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block collection", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    # indentless_sequence ::= (BLOCK-ENTRY block_node?)+

    def parse_indentless_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken,
                    KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_indentless_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_indentless_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        token = self.peek_token()
        event = SequenceEndEvent(token.start_mark, token.start_mark)
        self.state = self.states.pop()
        return event

    # block_mapping     ::= BLOCK-MAPPING_START
    #                       ((KEY block_node_or_indentless_sequence?)?
    #                       (VALUE block_node_or_indentless_sequence?)?)*
    #                       BLOCK-END

    def parse_block_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_mapping_key()

    def parse_block_mapping_key(self):
        if self.check_token(KeyToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_value)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_value
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block mapping", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_block_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_key)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_block_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    # flow_sequence     ::= FLOW-SEQUENCE-START
    #                       (flow_sequence_entry FLOW-ENTRY)*
    #                       flow_sequence_entry?
    #                       FLOW-SEQUENCE-END
    # flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
    #
    # Note that while production rules for both flow_sequence_entry and
    # flow_mapping_entry are equal, their interpretations are different.
    # For `flow_sequence_entry`, the part `KEY flow_node? (VALUE flow_node?)?`
    # generate an inline mapping (set syntax).

    def parse_flow_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_sequence_entry(first=True)

    def parse_flow_sequence_entry(self, first=False):
        if not self.check_token(FlowSequenceEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow sequence", self.marks[-1],
                            "expected ',' or ']', but got %r" % token.id, token.start_mark)
            
            if self.check_token(KeyToken):
                token = self.peek_token()
                event = MappingStartEvent(None, None, True,
                        token.start_mark, token.end_mark,
                        flow_style=True)
                self.state = self.parse_flow_sequence_entry_mapping_key
                return event
            elif not self.check_token(FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry)
                return self.parse_flow_node()
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_sequence_entry_mapping_key(self):
        token = self.get_token()
        if not self.check_token(ValueToken,
                FlowEntryToken, FlowSequenceEndToken):
            self.states.append(self.parse_flow_sequence_entry_mapping_value)
            return self.parse_flow_node()
        else:
            self.state = self.parse_flow_sequence_entry_mapping_value
            return self.process_empty_scalar(token.end_mark)

    def parse_flow_sequence_entry_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry_mapping_end)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_sequence_entry_mapping_end
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_sequence_entry_mapping_end
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_sequence_entry_mapping_end(self):
        self.state = self.parse_flow_sequence_entry
        token = self.peek_token()
        return MappingEndEvent(token.start_mark, token.start_mark)

    # flow_mapping  ::= FLOW-MAPPING-START
    #                   (flow_mapping_entry FLOW-ENTRY)*
    #                   flow_mapping_entry?
    #                   FLOW-MAPPING-END
    # flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?

    def parse_flow_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_mapping_key(first=True)

    def parse_flow_mapping_key(self, first=False):
        if not self.check_token(FlowMappingEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow mapping", self.marks[-1],
                            "expected ',' or '}', but got %r" % token.id, token.start_mark)
            if self.check_token(KeyToken):
                token = self.get_token()
                if not self.check_token(ValueToken,
                        FlowEntryToken, FlowMappingEndToken):
                    self.states.append(self.parse_flow_mapping_value)
                    return self.parse_flow_node()
                else:
                    self.state = self.parse_flow_mapping_value
                    return self.process_empty_scalar(token.end_mark)
            elif not self.check_token(FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_empty_value)
                return self.parse_flow_node()
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_key)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_mapping_empty_value(self):
        self.state = self.parse_flow_mapping_key
        return self.process_empty_scalar(self.peek_token().start_mark)

    def process_empty_scalar(self, mark):
        return ScalarEvent(None, None, (True, False), '', mark, mark)


########NEW FILE########
__FILENAME__ = reader
# This module contains abstractions for the input stream. You don't have to
# looks further, there are no pretty code.
#
# We define two classes here.
#
#   Mark(source, line, column)
# It's just a record and its only use is producing nice error messages.
# Parser does not use it for any other purposes.
#
#   Reader(source, data)
# Reader determines the encoding of `data` and converts it to unicode.
# Reader provides the following methods and attributes:
#   reader.peek(length=1) - return the next `length` characters
#   reader.forward(length=1) - move the current position to `length` characters.
#   reader.index - the number of the current character.
#   reader.line, stream.column - the line and the column of the current character.

__all__ = ['Reader', 'ReaderError']

from .error import YAMLError, Mark

import codecs, re

class ReaderError(YAMLError):

    def __init__(self, name, position, character, encoding, reason):
        self.name = name
        self.character = character
        self.position = position
        self.encoding = encoding
        self.reason = reason

    def __str__(self):
        if isinstance(self.character, bytes):
            return "'%s' codec can't decode byte #x%02x: %s\n"  \
                    "  in \"%s\", position %d"    \
                    % (self.encoding, ord(self.character), self.reason,
                            self.name, self.position)
        else:
            return "unacceptable character #x%04x: %s\n"    \
                    "  in \"%s\", position %d"    \
                    % (self.character, self.reason,
                            self.name, self.position)

class Reader(object):
    # Reader:
    # - determines the data encoding and converts it to a unicode string,
    # - checks if characters are in allowed range,
    # - adds '\0' to the end.

    # Reader accepts
    #  - a `bytes` object,
    #  - a `str` object,
    #  - a file-like object with its `read` method returning `str`,
    #  - a file-like object with its `read` method returning `unicode`.

    # Yeah, it's ugly and slow.

    def __init__(self, stream):
        self.name = None
        self.stream = None
        self.stream_pointer = 0
        self.eof = True
        self.buffer = ''
        self.pointer = 0
        self.raw_buffer = None
        self.raw_decode = None
        self.encoding = None
        self.index = 0
        self.line = 0
        self.column = 0
        if isinstance(stream, str):
            self.name = "<unicode string>"
            self.check_printable(stream)
            self.buffer = stream+'\0'
        elif isinstance(stream, bytes):
            self.name = "<byte string>"
            self.raw_buffer = stream
            self.determine_encoding()
        else:
            self.stream = stream
            self.name = getattr(stream, 'name', "<file>")
            self.eof = False
            self.raw_buffer = None
            self.determine_encoding()

    def peek(self, index=0):
        try:
            return self.buffer[self.pointer+index]
        except IndexError:
            self.update(index+1)
            return self.buffer[self.pointer+index]

    def prefix(self, length=1):
        if self.pointer+length >= len(self.buffer):
            self.update(length)
        return self.buffer[self.pointer:self.pointer+length]

    def forward(self, length=1):
        if self.pointer+length+1 >= len(self.buffer):
            self.update(length+1)
        while length:
            ch = self.buffer[self.pointer]
            self.pointer += 1
            self.index += 1
            if ch in '\n\x85\u2028\u2029'  \
                    or (ch == '\r' and self.buffer[self.pointer] != '\n'):
                self.line += 1
                self.column = 0
            elif ch != '\uFEFF':
                self.column += 1
            length -= 1

    def get_mark(self):
        if self.stream is None:
            return Mark(self.name, self.index, self.line, self.column,
                    self.buffer, self.pointer)
        else:
            return Mark(self.name, self.index, self.line, self.column,
                    None, None)

    def determine_encoding(self):
        while not self.eof and (self.raw_buffer is None or len(self.raw_buffer) < 2):
            self.update_raw()
        if isinstance(self.raw_buffer, bytes):
            if self.raw_buffer.startswith(codecs.BOM_UTF16_LE):
                self.raw_decode = codecs.utf_16_le_decode
                self.encoding = 'utf-16-le'
            elif self.raw_buffer.startswith(codecs.BOM_UTF16_BE):
                self.raw_decode = codecs.utf_16_be_decode
                self.encoding = 'utf-16-be'
            else:
                self.raw_decode = codecs.utf_8_decode
                self.encoding = 'utf-8'
        self.update(1)

    NON_PRINTABLE = re.compile('[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD]')
    def check_printable(self, data):
        match = self.NON_PRINTABLE.search(data)
        if match:
            character = match.group()
            position = self.index+(len(self.buffer)-self.pointer)+match.start()
            raise ReaderError(self.name, position, ord(character),
                    'unicode', "special characters are not allowed")

    def update(self, length):
        if self.raw_buffer is None:
            return
        self.buffer = self.buffer[self.pointer:]
        self.pointer = 0
        while len(self.buffer) < length:
            if not self.eof:
                self.update_raw()
            if self.raw_decode is not None:
                try:
                    data, converted = self.raw_decode(self.raw_buffer,
                            'strict', self.eof)
                except UnicodeDecodeError as exc:
                    character = self.raw_buffer[exc.start]
                    if self.stream is not None:
                        position = self.stream_pointer-len(self.raw_buffer)+exc.start
                    else:
                        position = exc.start
                    raise ReaderError(self.name, position, character,
                            exc.encoding, exc.reason)
            else:
                data = self.raw_buffer
                converted = len(data)
            self.check_printable(data)
            self.buffer += data
            self.raw_buffer = self.raw_buffer[converted:]
            if self.eof:
                self.buffer += '\0'
                self.raw_buffer = None
                break

    def update_raw(self, size=4096):
        data = self.stream.read(size)
        if self.raw_buffer is None:
            self.raw_buffer = data
        else:
            self.raw_buffer += data
        self.stream_pointer += len(data)
        if not data:
            self.eof = True

#try:
#    import psyco
#    psyco.bind(Reader)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = representer

__all__ = ['BaseRepresenter', 'SafeRepresenter', 'Representer',
    'RepresenterError']

from .error import *
from .nodes import *

import datetime, sys, copyreg, types, base64

class RepresenterError(YAMLError):
    pass

class BaseRepresenter:

    yaml_representers = {}
    yaml_multi_representers = {}

    def __init__(self, default_style=None, default_flow_style=None):
        self.default_style = default_style
        self.default_flow_style = default_flow_style
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def represent(self, data):
        node = self.represent_data(data)
        self.serialize(node)
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def represent_data(self, data):
        if self.ignore_aliases(data):
            self.alias_key = None
        else:
            self.alias_key = id(data)
        if self.alias_key is not None:
            if self.alias_key in self.represented_objects:
                node = self.represented_objects[self.alias_key]
                #if node is None:
                #    raise RepresenterError("recursive objects are not allowed: %r" % data)
                return node
            #self.represented_objects[alias_key] = None
            self.object_keeper.append(data)
        data_types = type(data).__mro__
        if data_types[0] in self.yaml_representers:
            node = self.yaml_representers[data_types[0]](self, data)
        else:
            for data_type in data_types:
                if data_type in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[data_type](self, data)
                    break
            else:
                if None in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[None](self, data)
                elif None in self.yaml_representers:
                    node = self.yaml_representers[None](self, data)
                else:
                    node = ScalarNode(None, str(data))
        #if alias_key is not None:
        #    self.represented_objects[alias_key] = node
        return node

    @classmethod
    def add_representer(cls, data_type, representer):
        if not 'yaml_representers' in cls.__dict__:
            cls.yaml_representers = cls.yaml_representers.copy()
        cls.yaml_representers[data_type] = representer

    @classmethod
    def add_multi_representer(cls, data_type, representer):
        if not 'yaml_multi_representers' in cls.__dict__:
            cls.yaml_multi_representers = cls.yaml_multi_representers.copy()
        cls.yaml_multi_representers[data_type] = representer

    def represent_scalar(self, tag, value, style=None):
        if style is None:
            style = self.default_style
        node = ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node

    def represent_sequence(self, tag, sequence, flow_style=None):
        value = []
        node = SequenceNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        for item in sequence:
            node_item = self.represent_data(item)
            if not (isinstance(node_item, ScalarNode) and not node_item.style):
                best_style = False
            value.append(node_item)
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = list(mapping.items())
            try:
                mapping = sorted(mapping)
            except TypeError:
                pass
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def ignore_aliases(self, data):
        return False

class SafeRepresenter(BaseRepresenter):

    def ignore_aliases(self, data):
        if data in [None, ()]:
            return True
        if isinstance(data, (str, bytes, bool, int, float)):
            return True

    def represent_none(self, data):
        return self.represent_scalar('tag:yaml.org,2002:null', 'null')

    def represent_str(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', data)

    def represent_binary(self, data):
        if hasattr(base64, 'encodebytes'):
            data = base64.encodebytes(data).decode('ascii')
        else:
            data = base64.encodestring(data).decode('ascii')
        return self.represent_scalar('tag:yaml.org,2002:binary', data, style='|')

    def represent_bool(self, data):
        if data:
            value = 'true'
        else:
            value = 'false'
        return self.represent_scalar('tag:yaml.org,2002:bool', value)

    def represent_int(self, data):
        return self.represent_scalar('tag:yaml.org,2002:int', str(data))

    inf_value = 1e300
    while repr(inf_value) != repr(inf_value*inf_value):
        inf_value *= inf_value

    def represent_float(self, data):
        if data != data or (data == 0.0 and data == 1.0):
            value = '.nan'
        elif data == self.inf_value:
            value = '.inf'
        elif data == -self.inf_value:
            value = '-.inf'
        else:
            value = repr(data).lower()
            # Note that in some cases `repr(data)` represents a float number
            # without the decimal parts.  For instance:
            #   >>> repr(1e17)
            #   '1e17'
            # Unfortunately, this is not a valid float representation according
            # to the definition of the `!!float` tag.  We fix this by adding
            # '.0' before the 'e' symbol.
            if '.' not in value and 'e' in value:
                value = value.replace('e', '.0e', 1)
        return self.represent_scalar('tag:yaml.org,2002:float', value)

    def represent_list(self, data):
        #pairs = (len(data) > 0 and isinstance(data, list))
        #if pairs:
        #    for item in data:
        #        if not isinstance(item, tuple) or len(item) != 2:
        #            pairs = False
        #            break
        #if not pairs:
            return self.represent_sequence('tag:yaml.org,2002:seq', data)
        #value = []
        #for item_key, item_value in data:
        #    value.append(self.represent_mapping(u'tag:yaml.org,2002:map',
        #        [(item_key, item_value)]))
        #return SequenceNode(u'tag:yaml.org,2002:pairs', value)

    def represent_dict(self, data):
        return self.represent_mapping('tag:yaml.org,2002:map', data)

    def represent_set(self, data):
        value = {}
        for key in data:
            value[key] = None
        return self.represent_mapping('tag:yaml.org,2002:set', value)

    def represent_date(self, data):
        value = data.isoformat()
        return self.represent_scalar('tag:yaml.org,2002:timestamp', value)

    def represent_datetime(self, data):
        value = data.isoformat(' ')
        return self.represent_scalar('tag:yaml.org,2002:timestamp', value)

    def represent_yaml_object(self, tag, data, cls, flow_style=None):
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__.copy()
        return self.represent_mapping(tag, state, flow_style=flow_style)

    def represent_undefined(self, data):
        raise RepresenterError("cannot represent an object: %s" % data)

SafeRepresenter.add_representer(type(None),
        SafeRepresenter.represent_none)

SafeRepresenter.add_representer(str,
        SafeRepresenter.represent_str)

SafeRepresenter.add_representer(bytes,
        SafeRepresenter.represent_binary)

SafeRepresenter.add_representer(bool,
        SafeRepresenter.represent_bool)

SafeRepresenter.add_representer(int,
        SafeRepresenter.represent_int)

SafeRepresenter.add_representer(float,
        SafeRepresenter.represent_float)

SafeRepresenter.add_representer(list,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(tuple,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(dict,
        SafeRepresenter.represent_dict)

SafeRepresenter.add_representer(set,
        SafeRepresenter.represent_set)

SafeRepresenter.add_representer(datetime.date,
        SafeRepresenter.represent_date)

SafeRepresenter.add_representer(datetime.datetime,
        SafeRepresenter.represent_datetime)

SafeRepresenter.add_representer(None,
        SafeRepresenter.represent_undefined)

class Representer(SafeRepresenter):

    def represent_complex(self, data):
        if data.imag == 0.0:
            data = '%r' % data.real
        elif data.real == 0.0:
            data = '%rj' % data.imag
        elif data.imag > 0:
            data = '%r+%rj' % (data.real, data.imag)
        else:
            data = '%r%rj' % (data.real, data.imag)
        return self.represent_scalar('tag:yaml.org,2002:python/complex', data)

    def represent_tuple(self, data):
        return self.represent_sequence('tag:yaml.org,2002:python/tuple', data)

    def represent_name(self, data):
        name = '%s.%s' % (data.__module__, data.__name__)
        return self.represent_scalar('tag:yaml.org,2002:python/name:'+name, '')

    def represent_module(self, data):
        return self.represent_scalar(
                'tag:yaml.org,2002:python/module:'+data.__name__, '')

    def represent_object(self, data):
        # We use __reduce__ API to save the data. data.__reduce__ returns
        # a tuple of length 2-5:
        #   (function, args, state, listitems, dictitems)

        # For reconstructing, we calls function(*args), then set its state,
        # listitems, and dictitems if they are not None.

        # A special case is when function.__name__ == '__newobj__'. In this
        # case we create the object with args[0].__new__(*args).

        # Another special case is when __reduce__ returns a string - we don't
        # support it.

        # We produce a !!python/object, !!python/object/new or
        # !!python/object/apply node.

        cls = type(data)
        if cls in copyreg.dispatch_table:
            reduce = copyreg.dispatch_table[cls](data)
        elif hasattr(data, '__reduce_ex__'):
            reduce = data.__reduce_ex__(2)
        elif hasattr(data, '__reduce__'):
            reduce = data.__reduce__()
        else:
            raise RepresenterError("cannot represent object: %r" % data)
        reduce = (list(reduce)+[None]*5)[:5]
        function, args, state, listitems, dictitems = reduce
        args = list(args)
        if state is None:
            state = {}
        if listitems is not None:
            listitems = list(listitems)
        if dictitems is not None:
            dictitems = dict(dictitems)
        if function.__name__ == '__newobj__':
            function = args[0]
            args = args[1:]
            tag = 'tag:yaml.org,2002:python/object/new:'
            newobj = True
        else:
            tag = 'tag:yaml.org,2002:python/object/apply:'
            newobj = False
        function_name = '%s.%s' % (function.__module__, function.__name__)
        if not args and not listitems and not dictitems \
                and isinstance(state, dict) and newobj:
            return self.represent_mapping(
                    'tag:yaml.org,2002:python/object:'+function_name, state)
        if not listitems and not dictitems  \
                and isinstance(state, dict) and not state:
            return self.represent_sequence(tag+function_name, args)
        value = {}
        if args:
            value['args'] = args
        if state or not isinstance(state, dict):
            value['state'] = state
        if listitems:
            value['listitems'] = listitems
        if dictitems:
            value['dictitems'] = dictitems
        return self.represent_mapping(tag+function_name, value)

Representer.add_representer(complex,
        Representer.represent_complex)

Representer.add_representer(tuple,
        Representer.represent_tuple)

Representer.add_representer(type,
        Representer.represent_name)

Representer.add_representer(types.FunctionType,
        Representer.represent_name)

Representer.add_representer(types.BuiltinFunctionType,
        Representer.represent_name)

Representer.add_representer(types.ModuleType,
        Representer.represent_module)

Representer.add_multi_representer(object,
        Representer.represent_object)


########NEW FILE########
__FILENAME__ = resolver

__all__ = ['BaseResolver', 'Resolver']

from .error import *
from .nodes import *

import re

class ResolverError(YAMLError):
    pass

class BaseResolver:

    DEFAULT_SCALAR_TAG = 'tag:yaml.org,2002:str'
    DEFAULT_SEQUENCE_TAG = 'tag:yaml.org,2002:seq'
    DEFAULT_MAPPING_TAG = 'tag:yaml.org,2002:map'

    yaml_implicit_resolvers = {}
    yaml_path_resolvers = {}

    def __init__(self):
        self.resolver_exact_paths = []
        self.resolver_prefix_paths = []

    @classmethod
    def add_implicit_resolver(cls, tag, regexp, first):
        if not 'yaml_implicit_resolvers' in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()
        if first is None:
            first = [None]
        for ch in first:
            cls.yaml_implicit_resolvers.setdefault(ch, []).append((tag, regexp))

    @classmethod
    def add_path_resolver(cls, tag, path, kind=None):
        # Note: `add_path_resolver` is experimental.  The API could be changed.
        # `new_path` is a pattern that is matched against the path from the
        # root to the node that is being considered.  `node_path` elements are
        # tuples `(node_check, index_check)`.  `node_check` is a node class:
        # `ScalarNode`, `SequenceNode`, `MappingNode` or `None`.  `None`
        # matches any kind of a node.  `index_check` could be `None`, a boolean
        # value, a string value, or a number.  `None` and `False` match against
        # any _value_ of sequence and mapping nodes.  `True` matches against
        # any _key_ of a mapping node.  A string `index_check` matches against
        # a mapping value that corresponds to a scalar key which content is
        # equal to the `index_check` value.  An integer `index_check` matches
        # against a sequence value with the index equal to `index_check`.
        if not 'yaml_path_resolvers' in cls.__dict__:
            cls.yaml_path_resolvers = cls.yaml_path_resolvers.copy()
        new_path = []
        for element in path:
            if isinstance(element, (list, tuple)):
                if len(element) == 2:
                    node_check, index_check = element
                elif len(element) == 1:
                    node_check = element[0]
                    index_check = True
                else:
                    raise ResolverError("Invalid path element: %s" % element)
            else:
                node_check = None
                index_check = element
            if node_check is str:
                node_check = ScalarNode
            elif node_check is list:
                node_check = SequenceNode
            elif node_check is dict:
                node_check = MappingNode
            elif node_check not in [ScalarNode, SequenceNode, MappingNode]  \
                    and not isinstance(node_check, str) \
                    and node_check is not None:
                raise ResolverError("Invalid node checker: %s" % node_check)
            if not isinstance(index_check, (str, int))  \
                    and index_check is not None:
                raise ResolverError("Invalid index checker: %s" % index_check)
            new_path.append((node_check, index_check))
        if kind is str:
            kind = ScalarNode
        elif kind is list:
            kind = SequenceNode
        elif kind is dict:
            kind = MappingNode
        elif kind not in [ScalarNode, SequenceNode, MappingNode]    \
                and kind is not None:
            raise ResolverError("Invalid node kind: %s" % kind)
        cls.yaml_path_resolvers[tuple(new_path), kind] = tag

    def descend_resolver(self, current_node, current_index):
        if not self.yaml_path_resolvers:
            return
        exact_paths = {}
        prefix_paths = []
        if current_node:
            depth = len(self.resolver_prefix_paths)
            for path, kind in self.resolver_prefix_paths[-1]:
                if self.check_resolver_prefix(depth, path, kind,
                        current_node, current_index):
                    if len(path) > depth:
                        prefix_paths.append((path, kind))
                    else:
                        exact_paths[kind] = self.yaml_path_resolvers[path, kind]
        else:
            for path, kind in self.yaml_path_resolvers:
                if not path:
                    exact_paths[kind] = self.yaml_path_resolvers[path, kind]
                else:
                    prefix_paths.append((path, kind))
        self.resolver_exact_paths.append(exact_paths)
        self.resolver_prefix_paths.append(prefix_paths)

    def ascend_resolver(self):
        if not self.yaml_path_resolvers:
            return
        self.resolver_exact_paths.pop()
        self.resolver_prefix_paths.pop()

    def check_resolver_prefix(self, depth, path, kind,
            current_node, current_index):
        node_check, index_check = path[depth-1]
        if isinstance(node_check, str):
            if current_node.tag != node_check:
                return
        elif node_check is not None:
            if not isinstance(current_node, node_check):
                return
        if index_check is True and current_index is not None:
            return
        if (index_check is False or index_check is None)    \
                and current_index is None:
            return
        if isinstance(index_check, str):
            if not (isinstance(current_index, ScalarNode)
                    and index_check == current_index.value):
                return
        elif isinstance(index_check, int) and not isinstance(index_check, bool):
            if index_check != current_index:
                return
        return True

    def resolve(self, kind, value, implicit):
        if kind is ScalarNode and implicit[0]:
            if value == '':
                resolvers = self.yaml_implicit_resolvers.get('', [])
            else:
                resolvers = self.yaml_implicit_resolvers.get(value[0], [])
            resolvers += self.yaml_implicit_resolvers.get(None, [])
            for tag, regexp in resolvers:
                if regexp.match(value):
                    return tag
            implicit = implicit[1]
        if self.yaml_path_resolvers:
            exact_paths = self.resolver_exact_paths[-1]
            if kind in exact_paths:
                return exact_paths[kind]
            if None in exact_paths:
                return exact_paths[None]
        if kind is ScalarNode:
            return self.DEFAULT_SCALAR_TAG
        elif kind is SequenceNode:
            return self.DEFAULT_SEQUENCE_TAG
        elif kind is MappingNode:
            return self.DEFAULT_MAPPING_TAG

class Resolver(BaseResolver):
    pass

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:bool',
        re.compile(r'''^(?:yes|Yes|YES|no|No|NO
                    |true|True|TRUE|false|False|FALSE
                    |on|On|ON|off|Off|OFF)$''', re.X),
        list('yYnNtTfFoO'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:float',
        re.compile(r'''^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
                    |\.[0-9_]+(?:[eE][-+][0-9]+)?
                    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$''', re.X),
        list('-+0123456789.'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:int',
        re.compile(r'''^(?:[-+]?0b[0-1_]+
                    |[-+]?0[0-7_]+
                    |[-+]?(?:0|[1-9][0-9_]*)
                    |[-+]?0x[0-9a-fA-F_]+
                    |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$''', re.X),
        list('-+0123456789'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:merge',
        re.compile(r'^(?:<<)$'),
        ['<'])

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:null',
        re.compile(r'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
        ['~', 'n', 'N', ''])

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:timestamp',
        re.compile(r'''^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
                    |[0-9][0-9][0-9][0-9] -[0-9][0-9]? -[0-9][0-9]?
                     (?:[Tt]|[ \t]+)[0-9][0-9]?
                     :[0-9][0-9] :[0-9][0-9] (?:\.[0-9]*)?
                     (?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$''', re.X),
        list('0123456789'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:value',
        re.compile(r'^(?:=)$'),
        ['='])

# The following resolver is only for documentation purposes. It cannot work
# because plain scalars cannot start with '!', '&', or '*'.
Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:yaml',
        re.compile(r'^(?:!|&|\*)$'),
        list('!&*'))


########NEW FILE########
__FILENAME__ = scanner

# Scanner produces tokens of the following types:
# STREAM-START
# STREAM-END
# DIRECTIVE(name, value)
# DOCUMENT-START
# DOCUMENT-END
# BLOCK-SEQUENCE-START
# BLOCK-MAPPING-START
# BLOCK-END
# FLOW-SEQUENCE-START
# FLOW-MAPPING-START
# FLOW-SEQUENCE-END
# FLOW-MAPPING-END
# BLOCK-ENTRY
# FLOW-ENTRY
# KEY
# VALUE
# ALIAS(value)
# ANCHOR(value)
# TAG(value)
# SCALAR(value, plain, style)
#
# Read comments in the Scanner code for more details.
#

__all__ = ['Scanner', 'ScannerError']

from .error import MarkedYAMLError
from .tokens import *

class ScannerError(MarkedYAMLError):
    pass

class SimpleKey:
    # See below simple keys treatment.

    def __init__(self, token_number, required, index, line, column, mark):
        self.token_number = token_number
        self.required = required
        self.index = index
        self.line = line
        self.column = column
        self.mark = mark

class Scanner:

    def __init__(self):
        """Initialize the scanner."""
        # It is assumed that Scanner and Reader will have a common descendant.
        # Reader do the dirty work of checking for BOM and converting the
        # input data to Unicode. It also adds NUL to the end.
        #
        # Reader supports the following methods
        #   self.peek(i=0)       # peek the next i-th character
        #   self.prefix(l=1)     # peek the next l characters
        #   self.forward(l=1)    # read the next l characters and move the pointer.

        # Had we reached the end of the stream?
        self.done = False

        # The number of unclosed '{' and '['. `flow_level == 0` means block
        # context.
        self.flow_level = 0

        # List of processed tokens that are not yet emitted.
        self.tokens = []

        # Add the STREAM-START token.
        self.fetch_stream_start()

        # Number of tokens that were emitted through the `get_token` method.
        self.tokens_taken = 0

        # The current indentation level.
        self.indent = -1

        # Past indentation levels.
        self.indents = []

        # Variables related to simple keys treatment.

        # A simple key is a key that is not denoted by the '?' indicator.
        # Example of simple keys:
        #   ---
        #   block simple key: value
        #   ? not a simple key:
        #   : { flow simple key: value }
        # We emit the KEY token before all keys, so when we find a potential
        # simple key, we try to locate the corresponding ':' indicator.
        # Simple keys should be limited to a single line and 1024 characters.

        # Can a simple key start at the current position? A simple key may
        # start:
        # - at the beginning of the line, not counting indentation spaces
        #       (in block context),
        # - after '{', '[', ',' (in the flow context),
        # - after '?', ':', '-' (in the block context).
        # In the block context, this flag also signifies if a block collection
        # may start at the current position.
        self.allow_simple_key = True

        # Keep track of possible simple keys. This is a dictionary. The key
        # is `flow_level`; there can be no more that one possible simple key
        # for each level. The value is a SimpleKey record:
        #   (token_number, required, index, line, column, mark)
        # A simple key may start with ALIAS, ANCHOR, TAG, SCALAR(flow),
        # '[', or '{' tokens.
        self.possible_simple_keys = {}

    # Public methods.

    def check_token(self, *choices):
        # Check if the next token is one of the given types.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.tokens[0], choice):
                    return True
        return False

    def peek_token(self):
        # Return the next token, but do not delete if from the queue.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            return self.tokens[0]

    def get_token(self):
        # Return the next token.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            self.tokens_taken += 1
            return self.tokens.pop(0)

    # Private methods.

    def need_more_tokens(self):
        if self.done:
            return False
        if not self.tokens:
            return True
        # The current token may be a potential simple key, so we
        # need to look further.
        self.stale_possible_simple_keys()
        if self.next_possible_simple_key() == self.tokens_taken:
            return True

    def fetch_more_tokens(self):

        # Eat whitespaces and comments until we reach the next token.
        self.scan_to_next_token()

        # Remove obsolete possible simple keys.
        self.stale_possible_simple_keys()

        # Compare the current indentation and column. It may add some tokens
        # and decrease the current indentation level.
        self.unwind_indent(self.column)

        # Peek the next character.
        ch = self.peek()

        # Is it the end of stream?
        if ch == '\0':
            return self.fetch_stream_end()

        # Is it a directive?
        if ch == '%' and self.check_directive():
            return self.fetch_directive()

        # Is it the document start?
        if ch == '-' and self.check_document_start():
            return self.fetch_document_start()

        # Is it the document end?
        if ch == '.' and self.check_document_end():
            return self.fetch_document_end()

        # TODO: support for BOM within a stream.
        #if ch == '\uFEFF':
        #    return self.fetch_bom()    <-- issue BOMToken

        # Note: the order of the following checks is NOT significant.

        # Is it the flow sequence start indicator?
        if ch == '[':
            return self.fetch_flow_sequence_start()

        # Is it the flow mapping start indicator?
        if ch == '{':
            return self.fetch_flow_mapping_start()

        # Is it the flow sequence end indicator?
        if ch == ']':
            return self.fetch_flow_sequence_end()

        # Is it the flow mapping end indicator?
        if ch == '}':
            return self.fetch_flow_mapping_end()

        # Is it the flow entry indicator?
        if ch == ',':
            return self.fetch_flow_entry()

        # Is it the block entry indicator?
        if ch == '-' and self.check_block_entry():
            return self.fetch_block_entry()

        # Is it the key indicator?
        if ch == '?' and self.check_key():
            return self.fetch_key()

        # Is it the value indicator?
        if ch == ':' and self.check_value():
            return self.fetch_value()

        # Is it an alias?
        if ch == '*':
            return self.fetch_alias()

        # Is it an anchor?
        if ch == '&':
            return self.fetch_anchor()

        # Is it a tag?
        if ch == '!':
            return self.fetch_tag()

        # Is it a literal scalar?
        if ch == '|' and not self.flow_level:
            return self.fetch_literal()

        # Is it a folded scalar?
        if ch == '>' and not self.flow_level:
            return self.fetch_folded()

        # Is it a single quoted scalar?
        if ch == '\'':
            return self.fetch_single()

        # Is it a double quoted scalar?
        if ch == '\"':
            return self.fetch_double()

        # It must be a plain scalar then.
        if self.check_plain():
            return self.fetch_plain()

        # No? It's an error. Let's produce a nice error message.
        raise ScannerError("while scanning for the next token", None,
                "found character %r that cannot start any token" % ch,
                self.get_mark())

    # Simple keys treatment.

    def next_possible_simple_key(self):
        # Return the number of the nearest possible simple key. Actually we
        # don't need to loop through the whole dictionary. We may replace it
        # with the following code:
        #   if not self.possible_simple_keys:
        #       return None
        #   return self.possible_simple_keys[
        #           min(self.possible_simple_keys.keys())].token_number
        min_token_number = None
        for level in self.possible_simple_keys:
            key = self.possible_simple_keys[level]
            if min_token_number is None or key.token_number < min_token_number:
                min_token_number = key.token_number
        return min_token_number

    def stale_possible_simple_keys(self):
        # Remove entries that are no longer possible simple keys. According to
        # the YAML specification, simple keys
        # - should be limited to a single line,
        # - should be no longer than 1024 characters.
        # Disabling this procedure will allow simple keys of any length and
        # height (may cause problems if indentation is broken though).
        for level in list(self.possible_simple_keys):
            key = self.possible_simple_keys[level]
            if key.line != self.line  \
                    or self.index-key.index > 1024:
                if key.required:
                    raise ScannerError("while scanning a simple key", key.mark,
                            "could not found expected ':'", self.get_mark())
                del self.possible_simple_keys[level]

    def save_possible_simple_key(self):
        # The next token may start a simple key. We check if it's possible
        # and save its position. This function is called for
        #   ALIAS, ANCHOR, TAG, SCALAR(flow), '[', and '{'.

        # Check if a simple key is required at the current position.
        required = not self.flow_level and self.indent == self.column

        # A simple key is required only if it is the first token in the current
        # line. Therefore it is always allowed.
        assert self.allow_simple_key or not required

        # The next token might be a simple key. Let's save it's number and
        # position.
        if self.allow_simple_key:
            self.remove_possible_simple_key()
            token_number = self.tokens_taken+len(self.tokens)
            key = SimpleKey(token_number, required,
                    self.index, self.line, self.column, self.get_mark())
            self.possible_simple_keys[self.flow_level] = key

    def remove_possible_simple_key(self):
        # Remove the saved possible key position at the current flow level.
        if self.flow_level in self.possible_simple_keys:
            key = self.possible_simple_keys[self.flow_level]
            
            if key.required:
                raise ScannerError("while scanning a simple key", key.mark,
                        "could not found expected ':'", self.get_mark())

            del self.possible_simple_keys[self.flow_level]

    # Indentation functions.

    def unwind_indent(self, column):

        ## In flow context, tokens should respect indentation.
        ## Actually the condition should be `self.indent >= column` according to
        ## the spec. But this condition will prohibit intuitively correct
        ## constructions such as
        ## key : {
        ## }
        #if self.flow_level and self.indent > column:
        #    raise ScannerError(None, None,
        #            "invalid intendation or unclosed '[' or '{'",
        #            self.get_mark())

        # In the flow context, indentation is ignored. We make the scanner less
        # restrictive then specification requires.
        if self.flow_level:
            return

        # In block context, we may need to issue the BLOCK-END tokens.
        while self.indent > column:
            mark = self.get_mark()
            self.indent = self.indents.pop()
            self.tokens.append(BlockEndToken(mark, mark))

    def add_indent(self, column):
        # Check if we need to increase indentation.
        if self.indent < column:
            self.indents.append(self.indent)
            self.indent = column
            return True
        return False

    # Fetchers.

    def fetch_stream_start(self):
        # We always add STREAM-START as the first token and STREAM-END as the
        # last token.

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-START.
        self.tokens.append(StreamStartToken(mark, mark,
            encoding=self.encoding))
        

    def fetch_stream_end(self):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False
        self.possible_simple_keys = {}

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-END.
        self.tokens.append(StreamEndToken(mark, mark))

        # The steam is finished.
        self.done = True

    def fetch_directive(self):
        
        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Scan and add DIRECTIVE.
        self.tokens.append(self.scan_directive())

    def fetch_document_start(self):
        self.fetch_document_indicator(DocumentStartToken)

    def fetch_document_end(self):
        self.fetch_document_indicator(DocumentEndToken)

    def fetch_document_indicator(self, TokenClass):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys. Note that there could not be a block collection
        # after '---'.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Add DOCUMENT-START or DOCUMENT-END.
        start_mark = self.get_mark()
        self.forward(3)
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_start(self):
        self.fetch_flow_collection_start(FlowSequenceStartToken)

    def fetch_flow_mapping_start(self):
        self.fetch_flow_collection_start(FlowMappingStartToken)

    def fetch_flow_collection_start(self, TokenClass):

        # '[' and '{' may start a simple key.
        self.save_possible_simple_key()

        # Increase the flow level.
        self.flow_level += 1

        # Simple keys are allowed after '[' and '{'.
        self.allow_simple_key = True

        # Add FLOW-SEQUENCE-START or FLOW-MAPPING-START.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_end(self):
        self.fetch_flow_collection_end(FlowSequenceEndToken)

    def fetch_flow_mapping_end(self):
        self.fetch_flow_collection_end(FlowMappingEndToken)

    def fetch_flow_collection_end(self, TokenClass):

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Decrease the flow level.
        self.flow_level -= 1

        # No simple keys after ']' or '}'.
        self.allow_simple_key = False

        # Add FLOW-SEQUENCE-END or FLOW-MAPPING-END.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_entry(self):

        # Simple keys are allowed after ','.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add FLOW-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(FlowEntryToken(start_mark, end_mark))

    def fetch_block_entry(self):

        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a new entry?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "sequence entries are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-SEQUENCE-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockSequenceStartToken(mark, mark))

        # It's an error for the block entry to occur in the flow context,
        # but we let the parser detect this.
        else:
            pass

        # Simple keys are allowed after '-'.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add BLOCK-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(BlockEntryToken(start_mark, end_mark))

    def fetch_key(self):
        
        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a key (not nessesary a simple)?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "mapping keys are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-MAPPING-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockMappingStartToken(mark, mark))

        # Simple keys are allowed after '?' in the block context.
        self.allow_simple_key = not self.flow_level

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add KEY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(KeyToken(start_mark, end_mark))

    def fetch_value(self):

        # Do we determine a simple key?
        if self.flow_level in self.possible_simple_keys:

            # Add KEY.
            key = self.possible_simple_keys[self.flow_level]
            del self.possible_simple_keys[self.flow_level]
            self.tokens.insert(key.token_number-self.tokens_taken,
                    KeyToken(key.mark, key.mark))

            # If this key starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.
            if not self.flow_level:
                if self.add_indent(key.column):
                    self.tokens.insert(key.token_number-self.tokens_taken,
                            BlockMappingStartToken(key.mark, key.mark))

            # There cannot be two simple keys one after another.
            self.allow_simple_key = False

        # It must be a part of a complex key.
        else:
            
            # Block context needs additional checks.
            # (Do we really need them? They will be catched by the parser
            # anyway.)
            if not self.flow_level:

                # We are allowed to start a complex value if and only if
                # we can start a simple key.
                if not self.allow_simple_key:
                    raise ScannerError(None, None,
                            "mapping values are not allowed here",
                            self.get_mark())

            # If this value starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.  It will be detected as an error later by
            # the parser.
            if not self.flow_level:
                if self.add_indent(self.column):
                    mark = self.get_mark()
                    self.tokens.append(BlockMappingStartToken(mark, mark))

            # Simple keys are allowed after ':' in the block context.
            self.allow_simple_key = not self.flow_level

            # Reset possible simple key on the current level.
            self.remove_possible_simple_key()

        # Add VALUE.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(ValueToken(start_mark, end_mark))

    def fetch_alias(self):

        # ALIAS could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after ALIAS.
        self.allow_simple_key = False

        # Scan and add ALIAS.
        self.tokens.append(self.scan_anchor(AliasToken))

    def fetch_anchor(self):

        # ANCHOR could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after ANCHOR.
        self.allow_simple_key = False

        # Scan and add ANCHOR.
        self.tokens.append(self.scan_anchor(AnchorToken))

    def fetch_tag(self):

        # TAG could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after TAG.
        self.allow_simple_key = False

        # Scan and add TAG.
        self.tokens.append(self.scan_tag())

    def fetch_literal(self):
        self.fetch_block_scalar(style='|')

    def fetch_folded(self):
        self.fetch_block_scalar(style='>')

    def fetch_block_scalar(self, style):

        # A simple key may follow a block scalar.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Scan and add SCALAR.
        self.tokens.append(self.scan_block_scalar(style))

    def fetch_single(self):
        self.fetch_flow_scalar(style='\'')

    def fetch_double(self):
        self.fetch_flow_scalar(style='"')

    def fetch_flow_scalar(self, style):

        # A flow scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after flow scalars.
        self.allow_simple_key = False

        # Scan and add SCALAR.
        self.tokens.append(self.scan_flow_scalar(style))

    def fetch_plain(self):

        # A plain scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after plain scalars. But note that `scan_plain` will
        # change this flag if the scan is finished at the beginning of the
        # line.
        self.allow_simple_key = False

        # Scan and add SCALAR. May change `allow_simple_key`.
        self.tokens.append(self.scan_plain())

    # Checkers.

    def check_directive(self):

        # DIRECTIVE:        ^ '%' ...
        # The '%' indicator is already checked.
        if self.column == 0:
            return True

    def check_document_start(self):

        # DOCUMENT-START:   ^ '---' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == '---'  \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_document_end(self):

        # DOCUMENT-END:     ^ '...' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == '...'  \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_block_entry(self):

        # BLOCK-ENTRY:      '-' (' '|'\n')
        return self.peek(1) in '\0 \t\r\n\x85\u2028\u2029'

    def check_key(self):

        # KEY(flow context):    '?'
        if self.flow_level:
            return True

        # KEY(block context):   '?' (' '|'\n')
        else:
            return self.peek(1) in '\0 \t\r\n\x85\u2028\u2029'

    def check_value(self):

        # VALUE(flow context):  ':'
        if self.flow_level:
            return True

        # VALUE(block context): ':' (' '|'\n')
        else:
            return self.peek(1) in '\0 \t\r\n\x85\u2028\u2029'

    def check_plain(self):

        # A plain scalar may start with any non-space character except:
        #   '-', '?', ':', ',', '[', ']', '{', '}',
        #   '#', '&', '*', '!', '|', '>', '\'', '\"',
        #   '%', '@', '`'.
        #
        # It may also start with
        #   '-', '?', ':'
        # if it is followed by a non-space character.
        #
        # Note that we limit the last rule to the block context (except the
        # '-' character) because we want the flow context to be space
        # independent.
        ch = self.peek()
        return ch not in '\0 \t\r\n\x85\u2028\u2029-?:,[]{}#&*!|>\'\"%@`'  \
                or (self.peek(1) not in '\0 \t\r\n\x85\u2028\u2029'
                        and (ch == '-' or (not self.flow_level and ch in '?:')))

    # Scanners.

    def scan_to_next_token(self):
        # We ignore spaces, line breaks and comments.
        # If we find a line break in the block context, we set the flag
        # `allow_simple_key` on.
        # The byte order mark is stripped if it's the first character in the
        # stream. We do not yet support BOM inside the stream as the
        # specification requires. Any such mark will be considered as a part
        # of the document.
        #
        # TODO: We need to make tab handling rules more sane. A good rule is
        #   Tabs cannot precede tokens
        #   BLOCK-SEQUENCE-START, BLOCK-MAPPING-START, BLOCK-END,
        #   KEY(block), VALUE(block), BLOCK-ENTRY
        # So the checking code is
        #   if <TAB>:
        #       self.allow_simple_keys = False
        # We also need to add the check for `allow_simple_keys == True` to
        # `unwind_indent` before issuing BLOCK-END.
        # Scanners for block, flow, and plain scalars need to be modified.

        if self.index == 0 and self.peek() == '\uFEFF':
            self.forward()
        found = False
        while not found:
            while self.peek() == ' ':
                self.forward()
            if self.peek() == '#':
                while self.peek() not in '\0\r\n\x85\u2028\u2029':
                    self.forward()
            if self.scan_line_break():
                if not self.flow_level:
                    self.allow_simple_key = True
            else:
                found = True

    def scan_directive(self):
        # See the specification for details.
        start_mark = self.get_mark()
        self.forward()
        name = self.scan_directive_name(start_mark)
        value = None
        if name == 'YAML':
            value = self.scan_yaml_directive_value(start_mark)
            end_mark = self.get_mark()
        elif name == 'TAG':
            value = self.scan_tag_directive_value(start_mark)
            end_mark = self.get_mark()
        else:
            end_mark = self.get_mark()
            while self.peek() not in '\0\r\n\x85\u2028\u2029':
                self.forward()
        self.scan_directive_ignored_line(start_mark)
        return DirectiveToken(name, value, start_mark, end_mark)

    def scan_directive_name(self, start_mark):
        # See the specification for details.
        length = 0
        ch = self.peek(length)
        while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                or ch in '-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        return value

    def scan_yaml_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        major = self.scan_yaml_directive_number(start_mark)
        if self.peek() != '.':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or '.', but found %r" % self.peek(),
                    self.get_mark())
        self.forward()
        minor = self.scan_yaml_directive_number(start_mark)
        if self.peek() not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or ' ', but found %r" % self.peek(),
                    self.get_mark())
        return (major, minor)

    def scan_yaml_directive_number(self, start_mark):
        # See the specification for details.
        ch = self.peek()
        if not ('0' <= ch <= '9'):
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit, but found %r" % ch, self.get_mark())
        length = 0
        while '0' <= self.peek(length) <= '9':
            length += 1
        value = int(self.prefix(length))
        self.forward(length)
        return value

    def scan_tag_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        handle = self.scan_tag_directive_handle(start_mark)
        while self.peek() == ' ':
            self.forward()
        prefix = self.scan_tag_directive_prefix(start_mark)
        return (handle, prefix)

    def scan_tag_directive_handle(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_handle('directive', start_mark)
        ch = self.peek()
        if ch != ' ':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch, self.get_mark())
        return value

    def scan_tag_directive_prefix(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_uri('directive', start_mark)
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch, self.get_mark())
        return value

    def scan_directive_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        if self.peek() == '#':
            while self.peek() not in '\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in '\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch, self.get_mark())
        self.scan_line_break()

    def scan_anchor(self, TokenClass):
        # The specification does not restrict characters for anchors and
        # aliases. This may lead to problems, for instance, the document:
        #   [ *alias, value ]
        # can be interpteted in two ways, as
        #   [ "value" ]
        # and
        #   [ *alias , "value" ]
        # Therefore we restrict aliases to numbers and ASCII letters.
        start_mark = self.get_mark()
        indicator = self.peek()
        if indicator == '*':
            name = 'alias'
        else:
            name = 'anchor'
        self.forward()
        length = 0
        ch = self.peek(length)
        while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                or ch in '-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in '\0 \t\r\n\x85\u2028\u2029?:,]}%@`':
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        end_mark = self.get_mark()
        return TokenClass(value, start_mark, end_mark)

    def scan_tag(self):
        # See the specification for details.
        start_mark = self.get_mark()
        ch = self.peek(1)
        if ch == '<':
            handle = None
            self.forward(2)
            suffix = self.scan_tag_uri('tag', start_mark)
            if self.peek() != '>':
                raise ScannerError("while parsing a tag", start_mark,
                        "expected '>', but found %r" % self.peek(),
                        self.get_mark())
            self.forward()
        elif ch in '\0 \t\r\n\x85\u2028\u2029':
            handle = None
            suffix = '!'
            self.forward()
        else:
            length = 1
            use_handle = False
            while ch not in '\0 \r\n\x85\u2028\u2029':
                if ch == '!':
                    use_handle = True
                    break
                length += 1
                ch = self.peek(length)
            handle = '!'
            if use_handle:
                handle = self.scan_tag_handle('tag', start_mark)
            else:
                handle = '!'
                self.forward()
            suffix = self.scan_tag_uri('tag', start_mark)
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a tag", start_mark,
                    "expected ' ', but found %r" % ch, self.get_mark())
        value = (handle, suffix)
        end_mark = self.get_mark()
        return TagToken(value, start_mark, end_mark)

    def scan_block_scalar(self, style):
        # See the specification for details.

        if style == '>':
            folded = True
        else:
            folded = False

        chunks = []
        start_mark = self.get_mark()

        # Scan the header.
        self.forward()
        chomping, increment = self.scan_block_scalar_indicators(start_mark)
        self.scan_block_scalar_ignored_line(start_mark)

        # Determine the indentation level and go to the first non-empty line.
        min_indent = self.indent+1
        if min_indent < 1:
            min_indent = 1
        if increment is None:
            breaks, max_indent, end_mark = self.scan_block_scalar_indentation()
            indent = max(min_indent, max_indent)
        else:
            indent = min_indent+increment-1
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
        line_break = ''

        # Scan the inner part of the block scalar.
        while self.column == indent and self.peek() != '\0':
            chunks.extend(breaks)
            leading_non_space = self.peek() not in ' \t'
            length = 0
            while self.peek(length) not in '\0\r\n\x85\u2028\u2029':
                length += 1
            chunks.append(self.prefix(length))
            self.forward(length)
            line_break = self.scan_line_break()
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
            if self.column == indent and self.peek() != '\0':

                # Unfortunately, folding rules are ambiguous.
                #
                # This is the folding according to the specification:
                
                if folded and line_break == '\n'    \
                        and leading_non_space and self.peek() not in ' \t':
                    if not breaks:
                        chunks.append(' ')
                else:
                    chunks.append(line_break)
                
                # This is Clark Evans's interpretation (also in the spec
                # examples):
                #
                #if folded and line_break == '\n':
                #    if not breaks:
                #        if self.peek() not in ' \t':
                #            chunks.append(' ')
                #        else:
                #            chunks.append(line_break)
                #else:
                #    chunks.append(line_break)
            else:
                break

        # Chomp the tail.
        if chomping is not False:
            chunks.append(line_break)
        if chomping is True:
            chunks.extend(breaks)

        # We are done.
        return ScalarToken(''.join(chunks), False, start_mark, end_mark,
                style)

    def scan_block_scalar_indicators(self, start_mark):
        # See the specification for details.
        chomping = None
        increment = None
        ch = self.peek()
        if ch in '+-':
            if ch == '+':
                chomping = True
            else:
                chomping = False
            self.forward()
            ch = self.peek()
            if ch in '0123456789':
                increment = int(ch)
                if increment == 0:
                    raise ScannerError("while scanning a block scalar", start_mark,
                            "expected indentation indicator in the range 1-9, but found 0",
                            self.get_mark())
                self.forward()
        elif ch in '0123456789':
            increment = int(ch)
            if increment == 0:
                raise ScannerError("while scanning a block scalar", start_mark,
                        "expected indentation indicator in the range 1-9, but found 0",
                        self.get_mark())
            self.forward()
            ch = self.peek()
            if ch in '+-':
                if ch == '+':
                    chomping = True
                else:
                    chomping = False
                self.forward()
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected chomping or indentation indicators, but found %r"
                    % ch, self.get_mark())
        return chomping, increment

    def scan_block_scalar_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        if self.peek() == '#':
            while self.peek() not in '\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in '\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected a comment or a line break, but found %r" % ch,
                    self.get_mark())
        self.scan_line_break()

    def scan_block_scalar_indentation(self):
        # See the specification for details.
        chunks = []
        max_indent = 0
        end_mark = self.get_mark()
        while self.peek() in ' \r\n\x85\u2028\u2029':
            if self.peek() != ' ':
                chunks.append(self.scan_line_break())
                end_mark = self.get_mark()
            else:
                self.forward()
                if self.column > max_indent:
                    max_indent = self.column
        return chunks, max_indent, end_mark

    def scan_block_scalar_breaks(self, indent):
        # See the specification for details.
        chunks = []
        end_mark = self.get_mark()
        while self.column < indent and self.peek() == ' ':
            self.forward()
        while self.peek() in '\r\n\x85\u2028\u2029':
            chunks.append(self.scan_line_break())
            end_mark = self.get_mark()
            while self.column < indent and self.peek() == ' ':
                self.forward()
        return chunks, end_mark

    def scan_flow_scalar(self, style):
        # See the specification for details.
        # Note that we loose indentation rules for quoted scalars. Quoted
        # scalars don't need to adhere indentation because " and ' clearly
        # mark the beginning and the end of them. Therefore we are less
        # restrictive then the specification requires. We only need to check
        # that document separators are not included in scalars.
        if style == '"':
            double = True
        else:
            double = False
        chunks = []
        start_mark = self.get_mark()
        quote = self.peek()
        self.forward()
        chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        while self.peek() != quote:
            chunks.extend(self.scan_flow_scalar_spaces(double, start_mark))
            chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        self.forward()
        end_mark = self.get_mark()
        return ScalarToken(''.join(chunks), False, start_mark, end_mark,
                style)

    ESCAPE_REPLACEMENTS = {
        '0':    '\0',
        'a':    '\x07',
        'b':    '\x08',
        't':    '\x09',
        '\t':   '\x09',
        'n':    '\x0A',
        'v':    '\x0B',
        'f':    '\x0C',
        'r':    '\x0D',
        'e':    '\x1B',
        ' ':    '\x20',
        '\"':   '\"',
        '\\':   '\\',
        'N':    '\x85',
        '_':    '\xA0',
        'L':    '\u2028',
        'P':    '\u2029',
    }

    ESCAPE_CODES = {
        'x':    2,
        'u':    4,
        'U':    8,
    }

    def scan_flow_scalar_non_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            length = 0
            while self.peek(length) not in '\'\"\\\0 \t\r\n\x85\u2028\u2029':
                length += 1
            if length:
                chunks.append(self.prefix(length))
                self.forward(length)
            ch = self.peek()
            if not double and ch == '\'' and self.peek(1) == '\'':
                chunks.append('\'')
                self.forward(2)
            elif (double and ch == '\'') or (not double and ch in '\"\\'):
                chunks.append(ch)
                self.forward()
            elif double and ch == '\\':
                self.forward()
                ch = self.peek()
                if ch in self.ESCAPE_REPLACEMENTS:
                    chunks.append(self.ESCAPE_REPLACEMENTS[ch])
                    self.forward()
                elif ch in self.ESCAPE_CODES:
                    length = self.ESCAPE_CODES[ch]
                    self.forward()
                    for k in range(length):
                        if self.peek(k) not in '0123456789ABCDEFabcdef':
                            raise ScannerError("while scanning a double-quoted scalar", start_mark,
                                    "expected escape sequence of %d hexdecimal numbers, but found %r" %
                                        (length, self.peek(k)), self.get_mark())
                    code = int(self.prefix(length), 16)
                    chunks.append(chr(code))
                    self.forward(length)
                elif ch in '\r\n\x85\u2028\u2029':
                    self.scan_line_break()
                    chunks.extend(self.scan_flow_scalar_breaks(double, start_mark))
                else:
                    raise ScannerError("while scanning a double-quoted scalar", start_mark,
                            "found unknown escape character %r" % ch, self.get_mark())
            else:
                return chunks

    def scan_flow_scalar_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        length = 0
        while self.peek(length) in ' \t':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch == '\0':
            raise ScannerError("while scanning a quoted scalar", start_mark,
                    "found unexpected end of stream", self.get_mark())
        elif ch in '\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            breaks = self.scan_flow_scalar_breaks(double, start_mark)
            if line_break != '\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(' ')
            chunks.extend(breaks)
        else:
            chunks.append(whitespaces)
        return chunks

    def scan_flow_scalar_breaks(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            # Instead of checking indentation, we check for document
            # separators.
            prefix = self.prefix(3)
            if (prefix == '---' or prefix == '...')   \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                raise ScannerError("while scanning a quoted scalar", start_mark,
                        "found unexpected document separator", self.get_mark())
            while self.peek() in ' \t':
                self.forward()
            if self.peek() in '\r\n\x85\u2028\u2029':
                chunks.append(self.scan_line_break())
            else:
                return chunks

    def scan_plain(self):
        # See the specification for details.
        # We add an additional restriction for the flow context:
        #   plain scalars in the flow context cannot contain ',', ':' and '?'.
        # We also keep track of the `allow_simple_key` flag here.
        # Indentation rules are loosed for the flow context.
        chunks = []
        start_mark = self.get_mark()
        end_mark = start_mark
        indent = self.indent+1
        # We allow zero indentation for scalars, but then we need to check for
        # document separators at the beginning of the line.
        #if indent == 0:
        #    indent = 1
        spaces = []
        while True:
            length = 0
            if self.peek() == '#':
                break
            while True:
                ch = self.peek(length)
                if ch in '\0 \t\r\n\x85\u2028\u2029'    \
                        or (not self.flow_level and ch == ':' and
                                self.peek(length+1) in '\0 \t\r\n\x85\u2028\u2029') \
                        or (self.flow_level and ch in ',:?[]{}'):
                    break
                length += 1
            # It's not clear what we should do with ':' in the flow context.
            if (self.flow_level and ch == ':'
                    and self.peek(length+1) not in '\0 \t\r\n\x85\u2028\u2029,[]{}'):
                self.forward(length)
                raise ScannerError("while scanning a plain scalar", start_mark,
                    "found unexpected ':'", self.get_mark(),
                    "Please check http://pyyaml.org/wiki/YAMLColonInFlowContext for details.")
            if length == 0:
                break
            self.allow_simple_key = False
            chunks.extend(spaces)
            chunks.append(self.prefix(length))
            self.forward(length)
            end_mark = self.get_mark()
            spaces = self.scan_plain_spaces(indent, start_mark)
            if not spaces or self.peek() == '#' \
                    or (not self.flow_level and self.column < indent):
                break
        return ScalarToken(''.join(chunks), True, start_mark, end_mark)

    def scan_plain_spaces(self, indent, start_mark):
        # See the specification for details.
        # The specification is really confusing about tabs in plain scalars.
        # We just forbid them completely. Do not use tabs in YAML!
        chunks = []
        length = 0
        while self.peek(length) in ' ':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch in '\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            self.allow_simple_key = True
            prefix = self.prefix(3)
            if (prefix == '---' or prefix == '...')   \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                return
            breaks = []
            while self.peek() in ' \r\n\x85\u2028\u2029':
                if self.peek() == ' ':
                    self.forward()
                else:
                    breaks.append(self.scan_line_break())
                    prefix = self.prefix(3)
                    if (prefix == '---' or prefix == '...')   \
                            and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                        return
            if line_break != '\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(' ')
            chunks.extend(breaks)
        elif whitespaces:
            chunks.append(whitespaces)
        return chunks

    def scan_tag_handle(self, name, start_mark):
        # See the specification for details.
        # For some strange reasons, the specification does not allow '_' in
        # tag handles. I have allowed it anyway.
        ch = self.peek()
        if ch != '!':
            raise ScannerError("while scanning a %s" % name, start_mark,
                    "expected '!', but found %r" % ch, self.get_mark())
        length = 1
        ch = self.peek(length)
        if ch != ' ':
            while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                    or ch in '-_':
                length += 1
                ch = self.peek(length)
            if ch != '!':
                self.forward(length)
                raise ScannerError("while scanning a %s" % name, start_mark,
                        "expected '!', but found %r" % ch, self.get_mark())
            length += 1
        value = self.prefix(length)
        self.forward(length)
        return value

    def scan_tag_uri(self, name, start_mark):
        # See the specification for details.
        # Note: we do not check if URI is well-formed.
        chunks = []
        length = 0
        ch = self.peek(length)
        while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                or ch in '-;/?:@&=+$,_.!~*\'()[]%':
            if ch == '%':
                chunks.append(self.prefix(length))
                self.forward(length)
                length = 0
                chunks.append(self.scan_uri_escapes(name, start_mark))
            else:
                length += 1
            ch = self.peek(length)
        if length:
            chunks.append(self.prefix(length))
            self.forward(length)
            length = 0
        if not chunks:
            raise ScannerError("while parsing a %s" % name, start_mark,
                    "expected URI, but found %r" % ch, self.get_mark())
        return ''.join(chunks)

    def scan_uri_escapes(self, name, start_mark):
        # See the specification for details.
        codes = []
        mark = self.get_mark()
        while self.peek() == '%':
            self.forward()
            for k in range(2):
                if self.peek(k) not in '0123456789ABCDEFabcdef':
                    raise ScannerError("while scanning a %s" % name, start_mark,
                            "expected URI escape sequence of 2 hexdecimal numbers, but found %r"
                            % self.peek(k), self.get_mark())
            codes.append(int(self.prefix(2), 16))
            self.forward(2)
        try:
            value = bytes(codes).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ScannerError("while scanning a %s" % name, start_mark, str(exc), mark)
        return value

    def scan_line_break(self):
        # Transforms:
        #   '\r\n'      :   '\n'
        #   '\r'        :   '\n'
        #   '\n'        :   '\n'
        #   '\x85'      :   '\n'
        #   '\u2028'    :   '\u2028'
        #   '\u2029     :   '\u2029'
        #   default     :   ''
        ch = self.peek()
        if ch in '\r\n\x85':
            if self.prefix(2) == '\r\n':
                self.forward(2)
            else:
                self.forward()
            return '\n'
        elif ch in '\u2028\u2029':
            self.forward()
            return ch
        return ''

#try:
#    import psyco
#    psyco.bind(Scanner)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = serializer

__all__ = ['Serializer', 'SerializerError']

from .error import YAMLError
from .events import *
from .nodes import *

class SerializerError(YAMLError):
    pass

class Serializer:

    ANCHOR_TEMPLATE = 'id%03d'

    def __init__(self, encoding=None,
            explicit_start=None, explicit_end=None, version=None, tags=None):
        self.use_encoding = encoding
        self.use_explicit_start = explicit_start
        self.use_explicit_end = explicit_end
        self.use_version = version
        self.use_tags = tags
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_anchor_id = 0
        self.closed = None

    def open(self):
        if self.closed is None:
            self.emit(StreamStartEvent(encoding=self.use_encoding))
            self.closed = False
        elif self.closed:
            raise SerializerError("serializer is closed")
        else:
            raise SerializerError("serializer is already opened")

    def close(self):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif not self.closed:
            self.emit(StreamEndEvent())
            self.closed = True

    #def __del__(self):
    #    self.close()

    def serialize(self, node):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif self.closed:
            raise SerializerError("serializer is closed")
        self.emit(DocumentStartEvent(explicit=self.use_explicit_start,
            version=self.use_version, tags=self.use_tags))
        self.anchor_node(node)
        self.serialize_node(node, None, None)
        self.emit(DocumentEndEvent(explicit=self.use_explicit_end))
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_anchor_id = 0

    def anchor_node(self, node):
        if node in self.anchors:
            if self.anchors[node] is None:
                self.anchors[node] = self.generate_anchor(node)
        else:
            self.anchors[node] = None
            if isinstance(node, SequenceNode):
                for item in node.value:
                    self.anchor_node(item)
            elif isinstance(node, MappingNode):
                for key, value in node.value:
                    self.anchor_node(key)
                    self.anchor_node(value)

    def generate_anchor(self, node):
        self.last_anchor_id += 1
        return self.ANCHOR_TEMPLATE % self.last_anchor_id

    def serialize_node(self, node, parent, index):
        alias = self.anchors[node]
        if node in self.serialized_nodes:
            self.emit(AliasEvent(alias))
        else:
            self.serialized_nodes[node] = True
            self.descend_resolver(parent, index)
            if isinstance(node, ScalarNode):
                detected_tag = self.resolve(ScalarNode, node.value, (True, False))
                default_tag = self.resolve(ScalarNode, node.value, (False, True))
                implicit = (node.tag == detected_tag), (node.tag == default_tag)
                self.emit(ScalarEvent(alias, node.tag, implicit, node.value,
                    style=node.style))
            elif isinstance(node, SequenceNode):
                implicit = (node.tag
                            == self.resolve(SequenceNode, node.value, True))
                self.emit(SequenceStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                index = 0
                for item in node.value:
                    self.serialize_node(item, node, index)
                    index += 1
                self.emit(SequenceEndEvent())
            elif isinstance(node, MappingNode):
                implicit = (node.tag
                            == self.resolve(MappingNode, node.value, True))
                self.emit(MappingStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                for key, value in node.value:
                    self.serialize_node(key, node, None)
                    self.serialize_node(value, node, key)
                self.emit(MappingEndEvent())
            self.ascend_resolver()


########NEW FILE########
__FILENAME__ = tokens

class Token(object):
    def __init__(self, start_mark, end_mark):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in self.__dict__
                if not key.endswith('_mark')]
        attributes.sort()
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

#class BOMToken(Token):
#    id = '<byte order mark>'

class DirectiveToken(Token):
    id = '<directive>'
    def __init__(self, name, value, start_mark, end_mark):
        self.name = name
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class DocumentStartToken(Token):
    id = '<document start>'

class DocumentEndToken(Token):
    id = '<document end>'

class StreamStartToken(Token):
    id = '<stream start>'
    def __init__(self, start_mark=None, end_mark=None,
            encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndToken(Token):
    id = '<stream end>'

class BlockSequenceStartToken(Token):
    id = '<block sequence start>'

class BlockMappingStartToken(Token):
    id = '<block mapping start>'

class BlockEndToken(Token):
    id = '<block end>'

class FlowSequenceStartToken(Token):
    id = '['

class FlowMappingStartToken(Token):
    id = '{'

class FlowSequenceEndToken(Token):
    id = ']'

class FlowMappingEndToken(Token):
    id = '}'

class KeyToken(Token):
    id = '?'

class ValueToken(Token):
    id = ':'

class BlockEntryToken(Token):
    id = '-'

class FlowEntryToken(Token):
    id = ','

class AliasToken(Token):
    id = '<alias>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class AnchorToken(Token):
    id = '<anchor>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class TagToken(Token):
    id = '<tag>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class ScalarToken(Token):
    id = '<scalar>'
    def __init__(self, value, plain, start_mark, end_mark, style=None):
        self.value = value
        self.plain = plain
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style


########NEW FILE########
__FILENAME__ = package_dev
import sublime
import sublime_plugin

import os

from sublime_lib.path import root_at_packages, get_package_name

PLUGIN_NAME = get_package_name()


DEBUG = 1

status = sublime.status_message
error = sublime.error_message
join_path = os.path.join
path_exists = os.path.exists

DEFAULT_DIRS = (
    "Snippets",
    "Support",
    "Docs",
    "Macros",
    "bin",
    "data"
)

# name, default template
DEFAULT_FILES = [
    ("LICENSE.txt", None),
    ("README.rst",             "data/README.rst"),
    (".hgignore",              "data/hgignore.txt"),
    (".gitignore",             "data/gitignore.txt"),
    ("bin/MakeRelease.ps1",    "data/MakeRelease.ps1"),
    ("bin/CleanUp.ps1",        "data/CleanUp.ps1"),
    ("data/html_template.txt", "data/html_template.txt"),
    ("data/main.css",          "data/main.css"),
    ("setup.py",               "data/setup.py")
]
for i, (name, path) in enumerate(DEFAULT_FILES):
    if path is not None:
        DEFAULT_FILES[i] = (
            os.path.join(*name.split("/")),
            root_at_packages(PLUGIN_NAME, os.path.join(*path.split("/")))
        )


class NewPackageCommand(sublime_plugin.WindowCommand):

    def on_done(self, pkg_name):
        pam = PackageManager()
        if pam.exists(pkg_name):
            error("  NewPackage -- Error\n\n"
                  "  Package '" + pkg_name + "' already exists.\n"
                  "  You cannot overwrite an existing package."
                  )
            return

        pam.create_new(pkg_name)

    def run(self):
        self.window.show_input_panel("New Package Name", '', self.on_done)


class DeletePackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        pam = PackageManager()
        pam.browse()


class PackageManager(object):

    def is_installed(self, name):
        raise NotImplemented

    def exists(self, name):
        return path_exists(root_at_packages(name))

    def browse(self):
        # Let user choose.
        sublime.active_window().run_command(
            "open_dir",
            {"dir": sublime.packages_path()}
        )

    def create_new(self, name):
        print("[NewPackage] Creating new package...")
        print(root_at_packages(name))

        if self.dry_run:
            msg = "[NewPackage] ** Nothing done. This was a test. **"
            print(msg)
            status(msg)
            return

        # Create top folder, default folders, default files.
        map(os.makedirs, [root_at_packages(name, d) for d in DEFAULT_DIRS])

        for fname, template in DEFAULT_FILES:
            with open(root_at_packages(name, fname), 'w') as fh:
                if template:
                    try:
                        content = ("".join(open(template, 'r').readlines())
                                   % {"package_name": name})
                    except:
                        pass
                    finally:
                        content = "".join(open(template, 'r').readlines())

                    fh.write(content)

        msg = "[NewPackage] Created new package '%s'." % name
        print(msg)
        status(msg)

    def __init__(self, dry_run=False):
        self.dry_run = dry_run

########NEW FILE########
__FILENAME__ = scope_data
# https://manual.macromates.com/en/language_grammars#naming_conventions
import sys

if sys.version_info[0] > 2:
    basestring = str

__all__ = ["COMPILED_NODES", "COMPILED_HEADS"]

DATA = """
    comment
        line
            double-slash
            double-dash
            number-sign
            percentage
        block
            documentation

    constant
        numeric
        character
            escape
        language
        other

    entity
        name
            function
            type
            tag
            section
        other
            inherited-class
            attribute-name

    invalid
        illegal
        deprecated

    keyword
        control
        operator
        other

    markup
        underline
            link
        bold
        heading
        italic
        list
            numbered
            unnumbered
        quote
        raw
        other

    meta

    storage
        type
        modifier

    string
        quoted
            single
            double
            triple
            other
        unquoted
        interpolated
        regexp
        other

    support
        function
        class
        type
        constant
        variable
        other

    variable
        parameter
        language
        other
"""


class NodeList(list):
    """
    Methods:
        * find(name)
        * fine_all(name)
        * to_completion()
    """
    def find(self, name):
        for node in self:
            if node == name:
                return node
        return None

    def find_all(self, name):
        res = NodeList()
        for node in self:
            if node == name:
                res.append(node)
        return res

    def to_completion(self):
        # return zip(self, self)
        return [(n.name, n.name) for n in self]


COMPILED_NODES = NodeList()
COMPILED_HEADS = NodeList()


class ScopeNode(object):
    """
    Attributes:
        * name
        * parent
        * children
        * level | unused
    Methods:
        * add_child(child)
        * tree()
    """

    def __init__(self, name, parent=None, children=None):
        self.name = name
        self.parent = parent
        self.children = children or NodeList()
        self.level = parent and parent.level + 1 or 1

    def add_child(self, child):
        self.children.append(child)

    def tree(self):
        if self.parent:
            return self.name + '.' + self.parent.tree()
        else:
            return self.name

    def __eq__(self, other):
        if isinstance(other, basestring):
            return str(self) == other

    def __str__(self):
        return self.name

    def __repr__(self):
        ret = self.name
        if self.children:
            ret += " {%s}" % ' '.join(repr(child) for child in self.children)
        return ret


#######################################

# parse the DATA string
lines = DATA.split("\n")

# some variables
indent = " " * 4
indent_level = 0
indents = {}

# process lines
# Note: expects sane indentation (such as only indent by 1 `indent` at a time)
for line in lines:
    if line.isspace() or not len(line):
        # skip blank lines
        continue
    if line.startswith(indent * (indent_level + 1)):
        # indent increased
        indent_level += 1
    if not line.startswith(indent * indent_level):
        # indent decreased
        for level in range(indent_level - 1, 0, -1):
            if line.startswith(indent * level):
                indent_level = level
                break

    parent = indents[indent_level - 1] if indent_level - 1 in indents else None
    node = ScopeNode(line.strip(), parent)
    indents[indent_level] = node

    if parent:
        parent.add_child(node)
    else:
        COMPILED_HEADS.append(node)

    COMPILED_NODES.append(node)

########NEW FILE########
__FILENAME__ = settings_dev
import sublime_plugin

from sublime_lib.path import root_at_packages, get_package_name


PLUGIN_NAME = get_package_name()

SETTINGS_SYNTAX = "Packages/%s/Syntax Definitions/Sublime Settings.tmLanguage" % PLUGIN_NAME
TPL = """{$0}"""


class NewSettingsCommand(sublime_plugin.WindowCommand):
    def run(self):
        v = self.window.new_file()
        v.settings().set('default_dir', root_at_packages('User'))
        v.settings().set('syntax', SETTINGS_SYNTAX)
        v.run_command('insert_snippet', {'contents': TPL})

########NEW FILE########
__FILENAME__ = snippet_dev
from xml.etree import ElementTree as ET

import sublime
import sublime_plugin

from sublime_lib.view import has_file_ext, get_text, clear
from sublime_lib.path import root_at_packages, get_package_name


PLUGIN_NAME = get_package_name()

RAW_SNIPPETS_SYNTAX = "Packages/%s/Syntax Definitions/Sublime Snippet (Raw).tmLanguage" % PLUGIN_NAME


TPL = """<snippet>
    <content><![CDATA[$1]]></content>
    <tabTrigger>${2:tab_trigger}</tabTrigger>
    <scope>${3:source.name}</scope>
</snippet>"""


class NewRawSnippetCommand(sublime_plugin.WindowCommand):
    def run(self):
        v = self.window.new_file()
        v.settings().set('default_dir', root_at_packages('User'))
        v.settings().set('syntax', RAW_SNIPPETS_SYNTAX)
        v.set_scratch(True)


class GenerateSnippetFromRawSnippetCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.match_selector(0, 'source.sublimesnippetraw')

    def run(self, edit):
        content = get_text(self.view)
        clear(self.view)
        self.view.run_command('insert_snippet', {'contents': TPL})
        self.view.settings().set('syntax', 'Packages/XML/XML.tmLanguage')
        # Insert existing contents into CDATA section. We rely on the fact
        # that Sublime will place the first selection in the first field of
        # the newly inserted snippet.
        self.view.insert(edit, self.view.sel()[0].begin(), content)


class NewRawSnippetFromSnippetCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return has_file_ext(self.view, 'sublime-snippet')

    def run(self, edit):
        snippet = get_text(self.view)
        contents = ET.fromstring(snippet).findtext(".//content")
        v = self.view.window().new_file()
        v.insert(edit, 0, contents)
        v.settings().set('syntax', RAW_SNIPPETS_SYNTAX)


class CopyAndInsertRawSnippetCommand(sublime_plugin.TextCommand):
    """Inserts the raw snippet contents into the first selection of
    the previous view in the stack.

    Allows a workflow where you're creating snippets for a .sublime-completions
    file, for example, and you don't want to store them as .sublime-snippet
    files.
    """
    def is_enabled(self):
        return self.view.match_selector(0, 'source.sublimesnippetraw')

    def run(self, edit):
        snip = get_text(self.view)
        self.view.window().run_command('close')
        target = sublime.active_window().active_view()
        target.replace(edit, target.sel()[0], snip)

########NEW FILE########
__FILENAME__ = sublime_inspect
import os

import sublime
import sublime_plugin

from sublime_lib.edit import Edit


class SublimeInspectCommand(sublime_plugin.WindowCommand):
    def on_done(self, s):
        rep = Report(s)
        rep.show()

    def run(self):
        self.window.show_input_panel("Search String:", '', self.on_done, None, None)


class Report(object):
    def __init__(self, s):
        self.s = s

    def collect_info(self):
        try:
            atts = dir(eval(self.s, {"sublime": sublime, "sublime_plugin": sublime_plugin}))
        except NameError as e:
            atts = e

        self.data = atts

    def show(self):
        self.collect_info()
        v = sublime.active_window().new_file()
        with Edit(v) as edit:
            edit.insert(0, '\n'.join(self.data))
        v.set_scratch(True)
        v.set_name("SublimeInspect - Report")


class OpenSublimeSessionCommand(sublime_plugin.WindowCommand):
    def run(self):
        session_file = os.path.join(sublime.packages_path(), "..", "Settings", "Session.sublime_session")
        self.window.open_file(session_file)

########NEW FILE########
__FILENAME__ = syntax_def_dev
import uuid
import re
import time
import yaml

import sublime
import sublime_plugin

from sublime_lib.path import root_at_packages, get_package_name
from sublime_lib.view import OutputPanel, base_scope, get_viewport_coords, set_viewport, extract_selector

from ordereddict_yaml import OrderedDictSafeDumper

try:  # ST2
    from ordereddict import OrderedDict
    from fileconv import dumpers, loaders
    from scope_data import COMPILED_HEADS
except ImportError:  # ST3
    from collections import OrderedDict
    from .fileconv import dumpers, loaders
    from .scope_data import COMPILED_HEADS

PLUGIN_NAME = get_package_name()

# Must be forward slashes (no os.path.join)!
BASE_SYNTAX_LANGUAGE = "Packages/%s/Syntax Definitions/Sublime Text Syntax Def (%%s).tmLanguage" % PLUGIN_NAME


# Technically ST does not use uuids at all, but we'll just leave it in
boilerplates = dict(
    json="""// [PackageDev] target_format: plist, ext: tmLanguage
    { "name": "${1:Syntax Name}",
  "scopeName": "source.${2:syntax_name}",
  "fileTypes": ["$3"],
  "uuid": "%s",

  "patterns": [
    $0
  ]
}""",
    yaml="""# [PackageDev] target_format: plist, ext: tmLanguage
---
name: ${1:Syntax Name}
scopeName: source.${2:syntax_name}
fileTypes: [$3]
uuid: %s

patterns:
- $0
...""",
    plist="""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>name</key>
    <string>${1:Syntax Name}</string>
    <key>scopeName</key>
    <string>source.${2:syntax_name}</string>
    <key>fileTypes</key>
    <array>
        <string>$3</string>
    </array>
    <key>uuid</key>
    <string>%s</string>

    <key>patterns</key>
    <array>
        $0
    </array>
</dict>
</plist>"""
)


# XXX: make this one command with args or something - 6 should definitely not be needed
class NewSyntaxDefCommand(object):
    """Creates a new syntax definition file for Sublime Text with some
    boilerplate text.
    """
    typ = ""

    def run(self):
        target = self.window.new_file()
        target.run_command('new_%s_syntax_def_to_buffer' % self.typ)


class NewJsonSyntaxDefCommand(NewSyntaxDefCommand, sublime_plugin.WindowCommand):
    typ = "json"


class NewYamlSyntaxDefCommand(NewSyntaxDefCommand, sublime_plugin.WindowCommand):
    typ = "yaml"


class NewPlistSyntaxDefCommand(NewSyntaxDefCommand, sublime_plugin.WindowCommand):
    typ = "plist"


class NewSyntaxDefToBufferCommand(object):
    """Inserts boilerplate text for syntax defs into current view.
    """
    typ = ""
    lang = None

    def is_enabled(self):
        # Don't mess up a non-empty buffer.
        return self.view.size() == 0

    def run(self, edit):
        ext = "%stmLanguage" % ('%s-' % self.typ.upper() if self.typ != 'plist' else '')

        s = self.view.settings()
        s.set('default_dir', root_at_packages('User'))
        s.set('default_extension', ext)
        s.set('syntax', self.lang or BASE_SYNTAX_LANGUAGE % self.typ.upper())

        self.view.run_command('insert_snippet', {'contents': boilerplates[self.typ] % uuid.uuid4()})


class NewJsonSyntaxDefToBufferCommand(NewSyntaxDefToBufferCommand, sublime_plugin.TextCommand):
    typ = "json"


class NewYamlSyntaxDefToBufferCommand(NewSyntaxDefToBufferCommand, sublime_plugin.TextCommand):
    typ = "yaml"


class NewPlistSyntaxDefToBufferCommand(NewSyntaxDefToBufferCommand, sublime_plugin.TextCommand):
    typ = "plist"
    lang = "Packages/XML/XML.tmLanguage"


###############################################################################


class YAMLLanguageDevDumper(OrderedDictSafeDumper):
    def represent_scalar(self, tag, value, style=None):
        if tag == u'tag:yaml.org,2002:str':
            # Block style for multiline strings
            if any(c in value for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029"):
                style = '|'

            # Use " to denote strings if the string contains ' but not ";
            # but try to do this only when necessary as non-quoted strings are always better
            elif ("'" in value and not '"' in value
                  and (value[0] in "[]{#'}@"
                       or any(s in value for s in (" '", ' #', ', ', ': ')))):
                style = '"'

        return super(YAMLLanguageDevDumper, self).represent_scalar(tag, value, style)

    def represent_mapping(self, tag, mapping, flow_style=False):
        # Default to block style; revert back to flow if len = 1 and only has "name" key
        if len(mapping) == 1:
            if hasattr(mapping, 'items'):
                flow_style = ('name' in mapping)
            else:
                flow_style = (mapping[0][0] == 'name')

        return super(YAMLLanguageDevDumper, self).represent_mapping(tag, mapping, flow_style)


class YAMLOrderedTextDumper(dumpers.YAMLDumper):
    default_params = dict(Dumper=OrderedDictSafeDumper)

    def __init__(self, window=None, output=None):
        if isinstance(output, OutputPanel):
            self.output = output
        elif window:
            self.output = OutputPanel(window, self.output_panel_name)

    def sort_keys(self, data, sort_order, sort_numeric):
        def do_sort(obj):
            od = OrderedDict()
            # The usual order
            if sort_order:
                for key in sort_order:
                    if key in obj:
                        od[key] = obj[key]
                        del obj[key]
            # The number order
            if sort_numeric:
                nums = []
                for key in obj:
                    if key.isdigit():
                        nums.append(int(key))
                nums.sort()
                for num in nums:
                    key = str(num)
                    od[key] = obj[key]
                    del obj[key]
            # The remaining stuff (in alphabetical order)
            keys = sorted(obj.keys())
            for key in keys:
                od[key] = obj[key]
                del obj[key]

            assert len(obj) == 0
            return od

        return self._validate_data(data, (
            (lambda x: isinstance(x, dict), do_sort),
        ))

    def dump(self, data, sort=True, sort_order=None, sort_numeric=True, *args, **kwargs):
        self.output.write_line("Sorting %s..." % self.name)
        self.output.show()
        if sort:
            data = self.sort_keys(data, sort_order, sort_numeric)
        params = self.validate_params(kwargs)

        self.output.write_line("Dumping %s..." % self.name)
        try:
            return yaml.dump(data, **params)
        except Exception as e:
            self.output.write_line("Error dumping %s: %s" % (self.name, e))


class RearrangeYamlSyntaxDefCommand(sublime_plugin.TextCommand):
    """Parses YAML and sorts all the dict keys reasonably.
    Does not write to the file, only to the buffer.
    """
    default_order = """comment
        name scopeName contentName fileTypes uuid
        begin beginCaptures end endCaptures match captures include
        patterns repository""".split()

    def is_visible(self):
        return base_scope(self.view) in ('source.yaml', 'source.yaml-tmlanguage')

    def run(self, edit, sort=True, sort_numeric=True, sort_order=None, remove_single_line_maps=True,
            insert_newlines=True, save=False, **kwargs):
        """Available parameters:

            sort (bool) = True
                Whether the list should be sorted at all. If this is not
                ``True`` the dicts' keys' order is likely not going to equal
                the input.

            sort_numeric (bool) = True
                A language definition's captures are assigned to a numeric key
                which is in fact a string. If you want to bypass the string
                sorting and instead sort by the strings number value, you will
                want this to be ``True``.

            sort_order (list)
                When this is passed it will be used instead of the default.
                The first element in the list will be the first key to be
                written for ALL dictionaries.
                Set to ``False`` to skip this step.

                The default order is:
                comment, name, scopeName, fileTypes, uuid, begin,
                beginCaptures, end, endCaptures, match, captures, include,
                patterns, repository

            remove_single_line_maps (bool) = True
                This will in fact turn the "- {include: '#something'}" lines
                into "- include: '#something'".
                Also splits mappings like "- {name: anything, match: .*}" to
                multiple lines.

                Be careful though because this is just a
                simple regexp that's safe for *usual* syntax definitions.

            insert_newlines (bool) = True
                Add newlines where appropriate to make the whole data appear
                better organized.

                Essentially add a new line:
                - before global "patterns" key
                - before global "repository" key
                - before every repository key except for the first

            save (bool) = False
                Save the view after processing is done.

            **kwargs
                Forwarded to yaml.dump (if they are valid).
        """
        # Check the environment (view, args, ...)
        if self.view.is_scratch():
            return
        if self.view.is_loading():
            # The view has not yet loaded, recall the command in this case until ST is done
            kwargs.update(dict(
                sort=sort,
                sort_numeric=sort_numeric,
                sort_order=sort_order,
                remove_single_line_maps=remove_single_line_maps,
                insert_newlines=insert_newlines,
                save=save
            ))
            sublime.set_timeout(
                lambda: self.view.run_command("rearrange_yaml_syntax_def", kwargs),
                20
            )
            return

        # Collect parameters
        file_path = self.view.file_name()
        if sort_order is None:
            sort_order = self.default_order
        vp = get_viewport_coords(self.view)

        output = OutputPanel(self.view.window() or sublime.active_window(), "aaa_package_dev")
        output.show()

        self.start_time = time.time()

        # Init the Loader
        loader = loaders.YAMLLoader(None, self.view, file_path=file_path, output=output)

        data = None
        try:
            data = loader.load()
        except NotImplementedError as e:
            # Use NotImplementedError to make the handler report the message as it pleases
            output.write_line(str(e))
            self.status(str(e), file_path)

        if not data:
            output.write_line("No contents in file.")
            return self.finish(output)

        # Dump
        dumper = YAMLOrderedTextDumper(output=output)
        if remove_single_line_maps:
            kwargs["Dumper"] = YAMLLanguageDevDumper
        text = dumper.dump(data, sort, sort_order, sort_numeric, **kwargs)
        if not text:
            self.status("Error re-dumping the data.")
            return

        # Replace the whole buffer (with default options)
        self.view.replace(
            edit,
            sublime.Region(0, self.view.size()),
            "# [PackageDev] target_format: plist, ext: tmLanguage\n"
            + text
        )

        # Insert the new lines using the syntax definition (which has hopefully been set)
        if insert_newlines:
            find = self.view.find_by_selector

            def select(l, only_first=True, not_first=True):
                # 'only_first' has priority
                if not l:
                    return l  # empty
                elif only_first:
                    return l[:1]
                elif not_first:
                    return l[1:]
                return l

            def filter_pattern_regs(reg):
                # Only use those keys where the region starts at column 0 and begins with '-'
                # because these are apparently the first keys of a 1-scope list
                beg = reg.begin()
                return self.view.rowcol(beg)[1] == 0 and self.view.substr(beg) == '-'

            regs = (
                select(find('meta.patterns - meta.repository-block'))
                + select(find('meta.repository-block'))
                + select(find('meta.repository-block meta.repository-key'), False)
                + select(list(filter(filter_pattern_regs, find('meta'))), False)
            )

            # Iterate in reverse order to not clash the regions because we will be modifying the source
            regs.sort()
            regs.reverse()
            for reg in regs:
                self.view.insert(edit, reg.begin(), '\n')

        if save:
            self.view.run_command("save")
            output.write_line("File saved")

        # Finish
        set_viewport(self.view, vp)
        self.finish(output)

    def finish(self, output):
        output.write("[Finished in %.3fs]" % (time.time() - self.start_time))
        output.finish()

    def status(self, msg, file_path=None):
        sublime.status_message(msg)
        print("[PackageDev] " + msg + (" (%s)" % file_path if file_path is not None else ""))


###############################################################################


class SyntaxDefCompletions(sublime_plugin.EventListener):
    def __init__(self):
        base_keys = "match,end,begin,name,contentName,comment,scopeName,include".split(',')
        dict_keys = "repository,captures,beginCaptures,endCaptures".split(',')
        list_keys = "fileTypes,patterns".split(',')

        completions = [
            ("include\tinclude: '#...'", "include: '#$0'"),
            ('include\tinclude: $self',  "include: \$self")
        ]
        for ex in ((("{0}\t{0}:".format(s), "%s: "    % s) for s in base_keys),
                   (("{0}\t{0}:".format(s), "%s:\n  " % s) for s in dict_keys),
                   (("{0}\t{0}:".format(s), "%s:\n- " % s) for s in list_keys)):
            completions.extend(ex)

        self.base_completions = completions

    def on_query_completions(self, view, prefix, locations):
        # We can't work with multiple selections here
        if len(locations) > 1:
            return []

        loc = locations[0]
        # Do not bother if not in yaml-tmlanguage scope and within or at the end of a comment
        if (not view.match_selector(loc, "source.yaml-tmlanguage - comment")
                or view.match_selector(loc - 1, "comment")):
            return []

        inhibit = lambda ret: (ret, sublime.INHIBIT_WORD_COMPLETIONS)

        # Extend numerics into `'123': {name: $0}`, as used in captures,
        # but only if they are not in a string scope
        word = view.substr(view.word(loc))
        if word.isdigit() and not view.match_selector(loc, "string"):
            return inhibit([(word, "'%s': {name: $0}" % word)])

        # Provide a selection of naming convention from TextMate + the base scope appendix
        if (view.match_selector(loc, "meta.name meta.value string")
                or view.match_selector(loc - 1, "meta.name meta.value string")
                or view.match_selector(loc - 2, "meta.name keyword.control.definition")):
            reg = extract_selector(view, "meta.name meta.value string", loc)
            if reg:
                # Tokenize the current selector (only to the cursor)
                text = view.substr(reg)
                pos = loc - reg.begin()
                scope = re.search(r"[\w\-_.]+$", text[:pos])
                tokens = scope and scope.group(0).split(".") or ""

                if len(tokens) > 1:
                    del tokens[-1]  # The last token is either incomplete or empty

                    # Browse the nodes and their children
                    nodes = COMPILED_HEADS
                    for i, token in enumerate(tokens):
                        node = nodes.find(token)
                        if not node:
                            sublime.status_message("[PackageDev] Warning: `%s` not found in scope naming conventions"
                                                   % '.'.join(tokens[:i + 1]))
                            break
                        nodes = node.children
                        if not nodes:
                            break

                    if nodes and node:
                        return inhibit(nodes.to_completion())
                    else:
                        sublime.status_message("[PackageDev] No nodes available in scope naming conventions after `%s`"
                                               % '.'.join(tokens))
                        # Search for the base scope appendix/suffix
                        regs = view.find_by_selector("meta.scope-name meta.value string")
                        if not regs:
                            sublime.status_message("[PackageDev] Warning: Could not find base scope")
                            return []

                        base_scope = view.substr(regs[0]).strip("\"'")
                        base_suffix = base_scope.split('.')[-1]
                        # Only useful when the base scope suffix is not already the last one
                        # In this case it is even useful to inhibit other completions completely
                        if tokens[-1] == base_suffix:
                            return inhibit([])

                        return inhibit([(base_suffix,) * 2])

            # Just return all the head nodes
            return inhibit(COMPILED_HEADS.to_completion())

        # Check if triggered by a "."
        if view.substr(loc - 1) == ".":
            # Due to "." being set as a trigger this should not be computed after the block above
            return []

        # Auto-completion for include values using the repository keys
        if view.match_selector(loc, "meta.include meta.value string, variable.other.include"):
            # Search for the whole include string which contains the current location
            reg = extract_selector(view, "meta.include meta.value string", loc)
            include_text = view.substr(reg)

            if not reg or (not include_text.startswith("'#") and not include_text.startswith('"#')):
                return []

            variables = [view.substr(r) for r in view.find_by_selector("variable.other.repository-key")]
            sublime.status_message("[PackageDev] Found %d local repository keys to be used in includes" % len(variables))
            return inhibit(zip(variables, variables))

        # Do not bother if the syntax def already matched the current position, except in the main repository
        scope = view.scope_name(loc).strip()
        if (view.match_selector(loc, "meta") and not scope.endswith("meta.repository-block.yaml-tmlanguage")):
            return []

        # Otherwise, use the default completions + generated uuid
        completions = [
            ('uuid\tuuid: ...', "uuid: %s" % uuid.uuid4())
        ]

        return inhibit(self.base_completions + completions)

########NEW FILE########
__FILENAME__ = sublime

########NEW FILE########
__FILENAME__ = sublime_plugin

########NEW FILE########
__FILENAME__ = test_path
import sys
import os

import mock

import sublime

import sublime_lib.path as su_path


def test_root_at_packages():
    sublime.packages_path = mock.Mock()
    sublime.packages_path.return_value = "XXX"
    expected = os.path.join("XXX", "ZZZ")
    assert su_path.root_at_packages("ZZZ") == expected


def test_root_at_data():
    sublime.packages_path = mock.Mock()
    sublime.packages_path.return_value = "XXX\\YYY"
    expected = os.path.join("XXX", "ZZZ")
    assert su_path.root_at_data("ZZZ") == expected

########NEW FILE########
__FILENAME__ = test_sels
import sys
import os

import mock

import sublime
########NEW FILE########
__FILENAME__ = test_view
import sys
import os

import mock

import sublime

import sublime_lib.view as su_lib_view


def test_append():
    view = mock.Mock()

    edit = object()
    view.begin_edit.return_value = edit
    view.size.return_value = 100
    su_lib_view.append(view, "new text")
    assert view.insert.call_args == ((edit, 100, "new text"),)


def test_in_one_edit():
    view = mock.Mock()

    edit = object()
    view.begin_edit.return_value = edit
    with su_lib_view.in_one_edit(view) as x:
        assert x is edit
    assert view.end_edit.call_args == ((edit,),)


def test_has_file_ext():
    view = mock.Mock()

    view.file_name.return_value = "foo.bar"
    assert su_lib_view.has_file_ext(view, "bar")

    view.file_name.return_value = 'foo.'
    assert not su_lib_view.has_file_ext(view, ".")

    view.file_name.return_value = ''
    assert not su_lib_view.has_file_ext(view, ".")

    view.file_name.return_value = ''
    assert not su_lib_view.has_file_ext(view, '')    

    view.file_name.return_value = 'foo'
    assert not su_lib_view.has_file_ext(view, '')

    view.file_name.return_value = 'foo'
    assert not su_lib_view.has_file_ext(view, 'foo')

    view.file_name.return_value = None
    assert not su_lib_view.has_file_ext(view, None)

    view.file_name.return_value = None
    assert not su_lib_view.has_file_ext(view, '.any')


def test_has_sels():
    view = mock.Mock()
    view.sel.return_value = range(1)

    assert su_lib_view.has_sels(view)
########NEW FILE########
