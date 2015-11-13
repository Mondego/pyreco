__FILENAME__ = context
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django template preprocessor.
Author: Jonathan Slenders, City Live
"""
from template_preprocessor.core.lexer import CompileException
import os

from template_preprocessor.core.utils import compile_external_javascript_files, compile_external_css_files


class GettextEntry(object):
    def __init__(self, path, line, column, text):
        self.path = path
        self.line = line
        self.column = column
        self.text = text

    def __unicode__(self):
        return "%s (line %s, column %s)" % (node.path, node.line, node.column)



class Context(object):
    """
    Preprocess context. Contains the compile settings, error logging,
    remembers dependencies, etc...
    """
    def __init__(self, path, loader=None, extra_options=None, insert_debug_symbols=False):
        self.loader = loader
        self.insert_debug_symbols = insert_debug_symbols

        # Remember stuff
        self.warnings = []
        self.media_dependencies = []
        self.gettext_entries = []

        # template_dependencies: will contains all other templates which are
        # needed for compilation of this template.
        self.template_dependencies = []

        # Only direct dependencies (first level {% include %} and {% extends %})
        self.include_dependencies = []
        self.extends_dependencies = []

        # Process options
        self.options = Options()
        for o in extra_options or []:
            self.options.change(o)

    def compile_media_callback(self, compress_tag, media_files):
        """
        Callback for the media compiler. Override for different output.
        """
        print 'Compiling media files from "%s" (line %s, column %s)' % \
                        (compress_tag.path, compress_tag.line, compress_tag.column)
        print ', '.join(media_files)

    def compile_media_progress_callback(self, compress_tag, media_file, current, total, file_size):
        """
        Print progress of compiling media files.
        """
        print ' (%s / %s): %s  (%s bytes)' % (current, total, media_file, file_size)

    def raise_warning(self, node, message):
        """
        Log warnings: this will not raise an exception. So, preprocessing
        for the current template will go on. But it's possible to retreive a
        list of all the warnings at the end.
        """
        self.warnings.append(PreprocessWarning(node, message))

    def load(self, template):
        if self.loader:
            self.template_dependencies.append(template)
            return self.loader(template)
        else:
            raise Exception('Preprocess context does not support template loading')

    def remember_gettext(self, node, text):
        self.gettext_entries.append(GettextEntry(node.path, node.line, node.column, text))

    def remember_include(self, template):
        self.include_dependencies.append(template)

    def remember_extends(self, template):
        self.extends_dependencies.append(template)

    # What to do with media files

    def compile_js_files(self, compress_tag, media_files):
        return compile_external_javascript_files(media_files, self, compress_tag)

    def compile_css_files(self, compress_tag, media_files):
        return compile_external_css_files(media_files, self, compress_tag)



class PreprocessWarning(Warning):
    def __init__(self, node, message):
        self.node = node
        self.message = message



class Options(object):
    """
    What options are used for compiling the current template.
    """
    def __init__(self):
        # Default settings
        self.execute_preprocessable_tags = True
        self.merge_all_load_tags = True
        self.preprocess_ifdebug = True # Should probably always be True
        self.preprocess_macros = True
        self.preprocess_translations = True
        self.preprocess_urls = True
        self.preprocess_variables = True
        self.remove_block_tags = True # Should propably not be disabled
        self.remove_some_tags = True # As we lack a better settings name
        self.whitespace_compression = True

        # HTML processor settings
        self.is_html = True

        self.compile_css = True
        self.compile_javascript = True
        self.compile_remote_css = False
        self.compile_remote_javascript = False
        self.merge_internal_css = False
        self.merge_internal_javascript = False # Not always recommended...
        self.remove_empty_class_attributes = False
        self.pack_external_javascript = False
        self.pack_external_css = False
        self.validate_html = True
        self.disallow_orphan_blocks = False # An error will be raised when a block has been defined, which is not present in the parent.
        self.disallow_block_level_elements_in_inline_level_elements = False

    def change(self, value, node=None):
        """
        Change an option. Called when the template contains a {% ! ... %} option tag.
        """
        actions = {
            'compile-css': ('compile_css', True),
            'compile-javascript': ('compile_javascript', True),
            'disallow-orphan-blocks': ('disallow_orphan_blocks', True),
            'html': ('is_html', True), # Enable HTML extensions
            'html-remove-empty-class-attributes': ('remove_empty_class_attributes', True),
            'merge-internal-css': ('merge_internal_css', True),
            'merge-internal-javascript': ('merge_internal_javascript', True),
            'no-disallow-orphan-blocks': ('disallow_orphan_blocks', False),
            'no-html': ('is_html', False), # Disable all HTML specific options
            'no-i18n-preprocessing': ('preprocess_translations', False),
            'no-macro-preprocessing': ('preprocess_macros', False),
            'no-pack-external-css': ('pack_external_css', False),
            'no-pack-external-javascript': ('pack_external_javascript', False),
            'no-validate-html': ('validate_html', False),
            'no-whitespace-compression': ('whitespace_compression', False),
            'pack-external-css': ('pack_external_css', True),
            'pack-external-javascript': ('pack_external_javascript', True),
            'validate-html': ('validate_html', True),
            'whitespace-compression': ('whitespace_compression', True),
            'no-block-level-elements-in-inline-level-elements': ('disallow_block_level_elements_in_inline_level_elements', True),
        }

        if value in actions:
            setattr(self, actions[value][0], actions[value][1])
        else:
            if node:
                raise CompileException(node, 'No such template preprocessor option: %s' % value)
            else:
                raise CompileException('No such template preprocessor option: %s (in settings.py)' % value)


########NEW FILE########
__FILENAME__ = css_processor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django template preprocessor.
Author: Jonathan Slenders, City Live
"""


"""
CSS parser for the template preprocessor.
-----------------------------------------------

Similar to the javascript preprocessor. This
will precompile the CSS in the parse tree.
"""

from django.conf import settings

from template_preprocessor.core.django_processor import DjangoContent, DjangoContainer
from template_preprocessor.core.lexer import State, StartToken, Push, Record, Shift, StopToken, Pop, CompileException, Token, Error
from template_preprocessor.core.lexer_engine import tokenize
from template_preprocessor.core.html_processor import HtmlNode, HtmlContent
import string
import os

__CSS_STATES = {
    'root' : State(
            # Operators for which it's allowed to remove the surrounding whitespace
            # Note that the dot (.) and hash (#) operators are not among these. Removing whitespace before them
            # can cause their meaning to change.
            State.Transition(r'\s*[{}():;,]\s*', (StartToken('css-operator'), Record(), Shift(), StopToken(), )),

            # Strings
            State.Transition(r'"', (Push('double-quoted-string'), StartToken('css-double-quoted-string-open'), Record(), Shift(), )),
            State.Transition(r"'", (Push('single-quoted-string'), StartToken('css-single-quoted-string-open'), Record(), Shift(), )),

            # Comments
            State.Transition(r'/\*', (Push('multiline-comment'), Shift(), )),
            State.Transition(r'//', (Push('singleline-comment'), Shift(), )),

            # Skip over comment signs. (not part of the actual css, and automatically inserted later on before and after
            # the css.)
            State.Transition(r'(<!--|-->)', (Shift(), )),

            # URLs like in url(...)
            State.Transition(r'url\(', (Shift(), StartToken('css-url'), Push('css-url'), )),


            # 'Words' (multiple of these should always be separated by whitespace.)
            State.Transition('([^\s{}();:,"\']|/(!?[/*]))+', (Record(), Shift(), )),

            # Whitespace which can be minified to a single space, but shouldn't be removed completely.
            State.Transition(r'\s+', (StartToken('css-whitespace'), Record(), Shift(), StopToken() )),

            State.Transition(r'.|\s', (Error('Error in parser #1'),)),
            ),
    'double-quoted-string': State(
            State.Transition(r'"', (Record(), Pop(), Shift(), StopToken(), )),
            State.Transition(r'\\.', (Record(), Shift(), )),
            State.Transition(r'[^"\\]+', (Record(), Shift(), )),
            State.Transition(r'.|\s', (Error('Error in parser #2'),)),
            ),
    'single-quoted-string': State(
            State.Transition(r"'", (Record(), Pop(), Shift(), StopToken(), )),
            State.Transition(r'\\.', (Record(), Shift() )),
            State.Transition(r"[^'\\]+", (Record(), Shift(), )),
            State.Transition(r'.|\s', (Error('Error in parser #3'),)),
            ),
    'multiline-comment': State(
            State.Transition(r'\*/', (Shift(), Pop(), )), # End comment
            State.Transition(r'(\*(?!/)|[^\*])+', (Shift(), )), # star, not followed by slash, or non star characters
            State.Transition(r'.|\s', (Error('Error in parser #4'),)),
            ),

    'css-url': State(
            # Strings inside urls (don't record the quotes, just place the content into the 'css-url' node)
            State.Transition(r'"', (Push('css-url-double-quoted'), Shift(), )),
            State.Transition(r"'", (Push('css-url-single-quoted'), Shift(), )),
            State.Transition("[^'\"\\)]+", (Record(), Shift())),

            State.Transition(r'\)', (Shift(), Pop(), StopToken(), )), # End url(...)
            State.Transition(r'.|\s', (Error('Error in parser #5'),)),
            ),
    'css-url-double-quoted': State(
            State.Transition(r'"', (Shift(), Pop(), )),
            State.Transition(r'\\.', (Record(), Shift() )),
            State.Transition(r'[^"\\]', (Record(), Shift())),
            ),
    'css-url-single-quoted': State(
            State.Transition(r"'", (Shift(), Pop(), )),
            State.Transition(r'\\.', (Record(), Shift() )),
            State.Transition(r"[^'\\]", (Record(), Shift())),
            ),

            # Single line comment (however, not allowed by the CSS specs.)
    'singleline-comment': State(
            State.Transition(r'\n', (Shift(), Pop(), )), # End of line is end of comment
            State.Transition(r'[^\n]+', (Shift(), )),
            State.Transition(r'.|\s', (Error('Error in parser #6'),)),
            ),
}


class CssNode(HtmlContent):
    pass

class CssOperator(HtmlContent):
    pass

class CssDoubleQuotedString(HtmlContent):
    pass

class CssWhitespace(HtmlContent):
    pass

class CssUrl(HtmlContent):
    def init_extension(self):
        self.url = self._unescape(self.output_as_string(True))

    def _unescape(self, url):
        import re
        return re.sub(r'\\(.)', r'\1', url)

    def _escape(self, url):
        import re
        return re.sub(r"'", r'\\\1', url)

    def output(self, handler):
        handler("url('")
        handler(self._escape(self.url))
        handler("')")


__CSS_EXTENSION_MAPPINGS = {
        'css-operator': CssOperator,
        'css-double-quoted-string': CssDoubleQuotedString,
        'css-whitespace': CssWhitespace,
        'css-url': CssUrl,
}


def _add_css_parser_extensions(css_node):
    """
    Patch nodes in the parse tree, to get the CSS parser functionality.
    """
    for node in css_node.all_children:
        if isinstance(node, Token):
            # Patch the js scope class
            if node.name in __CSS_EXTENSION_MAPPINGS:
                node.__class__ = __CSS_EXTENSION_MAPPINGS[node.name]
                if hasattr(node, 'init_extension'):
                    node.init_extension()

            _add_css_parser_extensions(node)


def _rewrite_urls(css_node, base_url):
    """
    Rewrite url(../img/img.png) to an absolute url, by
    joining it with its own public path.
    """
    def is_absolute_url(url):
        # An URL is absolute when it contains a protocol definition
        # like http:// or when it starts with a slash.
        return '://' in url or url[0] == '/'

    directory = os.path.dirname(base_url)

    for url_node in css_node.child_nodes_of_class(CssUrl):
        if not is_absolute_url(url_node.url):
            url_node.url = os.path.normpath(os.path.join(directory, url_node.url))

    # Replace urls starting with /static and /media with the real static and
    # media urls. We cannot use settings.MEDIA_URL/STATIC_URL in external css
    # files, and therefore we simply write /media or /static.
    from template_preprocessor.core.utils import real_url
    for url_node in css_node.child_nodes_of_class(CssUrl):
        url_node.url = real_url(url_node.url)


def _compress_css_whitespace(css_node):
    """
    Remove all whitepace in the css code where possible.
    """
    for c in css_node.all_children:
        if isinstance(c, CssOperator):
            # Around operators, we can delete all whitespace.
            c.children = [ c.output_as_string().strip()  ]

        if isinstance(c, CssWhitespace):
            # Whitespace tokens to be kept. (but minified into one character.)
            c.children = [ u' ' ]

        if isinstance(c, Token):
            _compress_css_whitespace(c)


def compile_css(css_node, context):
    """
    Compile the css nodes to more compact code.
    - Remove comments
    - Remove whitespace where possible.
    """
    #_remove_multiline_js_comments(js_node)
    tokenize(css_node, __CSS_STATES, HtmlNode, DjangoContainer)
    _add_css_parser_extensions(css_node)

    # Remove meaningless whitespace in javascript code.
    _compress_css_whitespace(css_node)


def compile_css_string(css_string, context, path='', url=None):
    """
    Compile CSS code
    """
    # First, create a tree to begin with
    tree = Token(name='root', line=1, column=1, path=path)
    tree.children = [ css_string ]

    # Tokenize
    tokenize(tree, __CSS_STATES, Token)
    _add_css_parser_extensions(tree)

    # Rewrite url() in external css files
    if url:
        _rewrite_urls(tree, url)

    # Compile
    _compress_css_whitespace(tree)

    # Output
    return u''.join([o for o in tree.output_as_string() ])

########NEW FILE########
__FILENAME__ = django_processor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django template preprocessor.
Author: Jonathan Slenders, City Live
"""

"""
Django parser for a template preprocessor.
------------------------------------------------------------------
Parses django template tags.
This parser will call the html/css/js parser if required.
"""

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.utils.translation import ugettext as _, ungettext

from template_preprocessor.core.lexer import Token, State, StartToken, Shift, StopToken, Push, Pop, Error, Record, CompileException
from template_preprocessor.core.preprocessable_template_tags import get_preprocessable_tags, NotPreprocessable
from template_preprocessor.core.lexer_engine import nest_block_level_elements, tokenize
import re
from copy import deepcopy



__DJANGO_STATES = {
    'root' : State(
            # Start of django tag
            State.Transition(r'\{#', (StartToken('django-comment'), Shift(), Push('django-comment'))),
            State.Transition(r'\{%\s*comment\s*%\}', (StartToken('django-multiline-comment'), Shift(), Push('django-multiline-comment'))),
            State.Transition(r'\{%\s*verbatim\s*%\}', (StartToken('django-verbatim'), Shift(), Push('django-verbatim'))),
            State.Transition(r'\{%\s*', (StartToken('django-tag'), Shift(), Push('django-tag'))),
            State.Transition(r'\{{\s*', (StartToken('django-variable'), Shift(), Push('django-variable'))),

            # Content
            State.Transition(r'([^{]|%|{(?![%#{]))+', (StartToken('content'), Record(), Shift(), StopToken())),

            State.Transition(r'.|\s', (Error('Error in parser'),)),
        ),
    # {# .... #}
    'django-comment': State(
            State.Transition(r'#\}', (StopToken(), Shift(), Pop())),
            State.Transition(r'[^\n#]+', (Record(), Shift())),
            State.Transition(r'\n', (Error('No newlines allowed in django single line comment'), )),
            State.Transition(r'#(?!\})', (Record(), Shift())),

            State.Transition(r'.|\s', (Error('Error in parser: comment'),)),
        ),
    'django-multiline-comment': State(
            State.Transition(r'\{%\s*endcomment\s*%\}', (StopToken(), Shift(), Pop())), # {% endcomment %}
                    # Nested single line comments are allowed
            State.Transition(r'\{#', (StartToken('django-comment'), Shift(), Push('django-comment'))),
            State.Transition(r'[^{]+', (Record(), Shift(), )), # Everything except '{'
            State.Transition(r'\{(?!%\s*endcomment\s*%\}|#)', (Record(), Shift(), )), # '{' if not followed by '%endcomment%}'
        ),
    # {% tagname ... %}
    'django-tag': State(
            #State.Transition(r'([a-zA-Z0-9_\-\.|=:\[\]<>(),]+|"[^"]*"|\'[^\']*\')+', # Whole token as one
            State.Transition(r'([^\'"\s%}]+|"[^"]*"|\'[^\']*\')+', # Whole token as one
                                        (StartToken('django-tag-element'), Record(), Shift(), StopToken() )),
            State.Transition(r'\s*%\}', (StopToken(), Shift(), Pop())),
            State.Transition(r'\s+', (Shift(), )), # Skip whitespace

            State.Transition(r'.|\s', (Error('Error in parser: django-tag'),)),
        ),
    # {{ variable }}
    'django-variable': State(
            #State.Transition(r'([a-zA-Z0-9_\-\.|=:\[\]<>(),]+|"[^"]*"|\'[^\']*\')+',
            State.Transition(r'([^\'"\s%}]+|"[^"]*"|\'[^\']*\')+',
                                        (StartToken('django-variable-part'), Record(), Shift(), StopToken() )),
            State.Transition(r'\s*\}\}', (StopToken(), Shift(), Pop())),
            State.Transition(r'\s+', (Shift(), )),

            State.Transition(r'.|\s', (Error('Error in parser: django-variable'),)),
        ),

    # {% verbatim %} ... {% endverbatim %}
    'django-verbatim': State(
            State.Transition(r'\{%\s*endverbatim\s*%\}', (Shift(), StopToken(), Pop())), # {% endverbatim %}
            State.Transition(r'[^{]+', (Record(), Shift(), )), # Everything except '{'
            State.Transition(r'\{(?!%\s*endverbatim\s*%\})', (Record(), Shift(), )), # '{' if not followed by '%endverbatim%}'
        ),
    }



class DjangoContainer(Token):
    """
    Any node which can contain both other Django nodes and DjangoContent.
    """
    pass

class DjangoContent(Token):
    """
    Any literal string to output. (html, javascript, ...)
    """
    pass


# ====================================[ Parser classes ]=====================================


class DjangoRootNode(DjangoContainer):
    """
    Root node of the parse tree.
    """
    pass


class DjangoComment(Token):
    """
    {# ... #}
    """
    def output(self, handler):
        # Don't output anything. :)
        pass


class DjangoMultilineComment(Token):
    """
    {% comment %} ... {% endcomment %}
    """
    def output(self, handler):
        # Don't output anything.
        pass


class DjangoVerbatim(Token):
    """
    {% verbatim %} ... {% endverbatim %}
    """
    # This tag is transparent, things that look like template tags, variables
    # and other stuff inside this tag is not interpreted in any way, but send to the
    # output straight away.
    #
    # A {% load verbatim %} may be required in order to get the Django
    # template engine support it. See this template tag:
    # https://gist.github.com/629508
    #
    # Verbatim is still an open discussion:
    # http://groups.google.com/group/django-developers/browse_thread/thread/eda0e9187adcbe36/abfb48648c80a9c7?lnk=gst&q=verbatim#abfb48648c80a9c7

    def output(self, handler):
        handler('{% verbatim %}')
        map(handler, self.children)
        handler('{% endverbatim %}')


class DjangoTag(Token):
    @property
    def tagname(self):
        """
        return the tagname in: {% tagname option option|filter ... %}
        """
        # This is the first django-tag-element child
        for c in self.children:
            if c.name == 'django-tag-element':
                return c.output_as_string()

    @property
    def args(self):
        iterator = (c for c in self.children if c.name == 'django-tag-element')
        iterator.next() # Skip first tag-element
        return list(i.output_as_string() for i in iterator)

    def output(self, handler):
        handler(u'{%')
        for c in self.children:
            handler(c)
            handler(u' ')
        handler(u'%}')


class DjangoVariable(Token):
    def init_extension(self):
        self.__varname = Token.output_as_string(self, True)

    @property
    def varname(self):
        return self.__varname

    def output(self, handler):
        handler(u'{{')
        handler(self.__varname)
        handler(u'}}')


class DjangoPreprocessorConfigTag(Token):
    """
    {% ! config-option-1 cofig-option-2 %}
    """
    def process_params(self, params):
        self.preprocessor_options = [ p.output_as_string() for p in params[1:] ]

    def output(self, handler):
        # Should output nothing.
        pass

class DjangoRawOutput(Token):
    """
    {% !raw %} ... {% !endraw %}
    This section contains code which should not be validated or interpreted
    (Because is would cause trigger a false-positive "invalid HTML" or similar.)
    """
    # Note that this class does not inherit from DjangoContainer, this makes
    # sure that the html processor won't enter this class.
    def process_params(self, params):
        pass

    def output(self, handler):
        # Do not output the '{% !raw %}'-tags
        map(handler, self.children)


class DjangoExtendsTag(Token):
    """
    {% extends varname_or_template %}
    """
    def process_params(self, params):
        param = params[1].output_as_string()

        if param[0] == '"' and param[-1] == '"':
            self.template_name = param[1:-1]
            self.template_name_is_variable = False
        elif param[0] == "'" and param[-1] == "'":
            self.template_name = param[1:-1]
            self.template_name_is_variable = False
        else:
            raise CompileException(self, 'Preprocessor does not support variable {% extends %} nodes')

            self.template_name = param
            self.template_name_is_variable = True

    def output(self, handler):
        if self.template_name_is_variable:
            handler(u'{%extends '); handler(self.template_name); handler(u'%}')
        else:
            handler(u'{%extends "'); handler(self.template_name); handler(u'"%}')


class DjangoIncludeTag(Token):
    """
    {% include varname_or_template %}

    Support for with-parameters:
    {% include "name_snippet.html" with person="Jane" greeting="Hello" %}
    """
    def process_params(self, params):
        include_param = params[1].output_as_string()

        # Include path
        if include_param[0] in ('"', "'") and include_param[-1] in ('"', "'"):
            self.template_name = include_param[1:-1]
            self.template_name_is_variable = False
        else:
            self.template_name = include_param
            self.template_name_is_variable = True

        # With parameters
        if len(params) > 2 and params[2].output_as_string() == 'with':
            self.with_params = params[3:]
        else:
            self.with_params = []

    def output(self, handler):
        if self.with_params:
            handler('{%with')
            for c in self.with_params:
                handler(' ')
                handler(c)
            handler('%}')

        if self.template_name_is_variable:
            handler(u'{%include '); handler(self.template_name); handler(u'%}')
        else:
            handler(u'{%include "'); handler(self.template_name); handler(u'"%}')

        if self.with_params:
            handler('{%endwith%}')

class DjangoDecorateTag(DjangoContainer):
    """
    {% decorate "template.html" %}
        things to place in '{{ content }}' of template.html
    {% enddecorate %}
    """
    def process_params(self, params):
        param = params[1].output_as_string()

        # Template name should not be variable
        if param[0] in ('"', "'") and param[-1] in ('"', "'"):
            self.template_name = param[1:-1]
        else:
            raise CompileException(self, 'Do not use variable template names in {% decorate %}')

    def output(self, handler):
        handler(u'{%decorate "%s" %}' % self.template_name);
        handler(self.children)
        handler(u'{%enddecorate%}')


class NoLiteraleException(Exception):
    def __init__(self):
        Exception.__init__(self, 'Not a variable')

def _variable_to_literal(variable):
    """
    if the string 'variable' represents a variable, return it
    without the surrounding quotes, otherwise raise exception.
    """
    if variable[0] in ('"', "'") and variable[-1] in ('"', "'"):
        return variable[1:-1]
    else:
        raise NoLiteraleException()


class DjangoUrlTag(DjangoTag):
    """
    {% url name param1 param2 param3=value %}
    """
    def process_params(self, params):
        self.url_params = params[1:]
        self._preprocess = None

    def original_output(self, handler):
        handler(u'{%url ')
        for c in self.url_params:
            handler(c)
            handler(u' ')
        handler(u'%}')

    def output(self, handler):
        if self._preprocess:
            handler(self._preprocess)
        else:
            self.original_output(handler)

    def preprocess(self, value):
        self._preprocess = value


class DjangoTransTag(Token):
    """
    {% trans "text" %}
    """
    def process_params(self, params):
        self.__string_is_variable = False
        param = params[1].output_as_string()

        # TODO: check whether it's allowed to have variables in {% trans %},
        #       if not: cleanup code,  if allowed: support behavior in all
        #       parts of this code.
        if param[0] in ('"', "'") and param[-1] in ('"', "'"):
            self.__string = param[1:-1]
            self.__string_is_variable = False
        else:
            self.__string = param
            self.__string_is_variable = True

    @property
    def is_variable(self):
        return self.__string_is_variable

    @property
    def string(self):
        return '' if self.__string_is_variable else self.__string

    def output(self, handler):
        if self.__string_is_variable:
            handler(u'{%trans '); handler(self.__string); handler(u'%}')
        else:
            handler(u'{%trans "'); handler(self.__string); handler(u'"%}')

    @property
    def translation_info(self):
        """
        Return an object which is compatible with {% blocktrans %}-info.
        (Only to be used when this string is not a variable, so not for {% trans var %} )
        """
        class TransInfo(object):
            def __init__(self, trans):
                self.has_plural = False
                self.plural_string = u''
                self.string = trans.string
                self.variables = set()
                self.plural_variables = set()
        return TransInfo(self)

class DjangoBlocktransTag(Token):
    """
    Contains:
    {% blocktrans %} children {% endblocktrans %}
    """
    def process_params(self, params):
        # Skip django-tag-element
        self.params = params[1:]

    @property
    def is_variable(self):
        # Consider this a dynamic string (which shouldn't be translated at compile time)
        # if it has variable nodes inside. Same for {% plural %} inside the blocktrans.
        return self.has_child_nodes_of_class((DjangoVariable, DjangoPluralTag))

#    @property
#    def string(self):
#        return '' if self.is_variable else self.output_as_string(True)

    @property
    def translation_info(self):
        """
        Return an {% blocktrans %}-info object which contains:
        - the string to be translated.
        - the string to be translated (in case of plural)
        - the variables to be used
        - the variables to be used (in case of plural)
        """
        convert_var = lambda v: '%%(%s)s' % v

        class BlocktransInfo(object):
            def __init__(self, blocktrans):
                # Build translatable string
                plural = False # get true when we find a plural translation
                string = []
                variables = []
                plural_string = []
                plural_variables = []

                for n in blocktrans.children:
                    if isinstance(n, DjangoPluralTag):
                        if not (len(blocktrans.params) and blocktrans.params[0].output_as_string() == 'count'):
                            raise CompileException(blocktrans,
                                    '{% plural %} tags can only appear inside {% blocktrans COUNT ... %}')
                        plural = True
                    elif isinstance(n, DjangoVariable):
                        (plural_string if plural else string).append(convert_var(n.varname))
                        (plural_variables if plural else variables).append(n.varname)
                    elif isinstance(n, DjangoContent):
                        (plural_string if plural else string).append(n.output_as_string())
                    else:
                        raise CompileException(n, 'Unexpected token in {% blocktrans %}: ' + n.output_as_string())

                # Return information
                self.has_plural = plural
                self.string = u''.join(string)
                self.plural_string = ''.join(plural_string)
                self.variables = set(variables)
                self.plural_variables = set(plural_variables)

        return BlocktransInfo(self)

    def output(self, handler):
        # Blocktrans output
        handler(u'{%blocktrans ');
        for p in self.params:
            p.output(handler)
            handler(u' ')
        handler(u'%}')
        Token.output(self, handler)
        handler(u'{%endblocktrans%}')


class DjangoPluralTag(Token):
    """
    {% plural %} tag. should only appear inside {% blocktrans %} for separating
    the singular and plural form.
    """
    def process_params(self, params):
        pass

    def output(self, handler):
        handler(u'{%plural%}')


class DjangoLoadTag(Token):
    """
    {% load module1 module2 ... %}
    """
    def process_params(self, params):
        self.modules = [ p.output_as_string() for p in params[1:] ]

    def output(self, handler):
        handler(u'{% load ')
        handler(u' '.join(self.modules))
        handler(u'%}')


class DjangoMacroTag(DjangoContainer): # TODO: not standard Django -> should be removed
    def process_params(self, params):
        assert len(params) == 2
        name = params[1].output_as_string()
        assert name[0] in ('"', "'") and name[0] == name[-1]
        self.macro_name = name[1:-1]

    def output(self, handler):
        handler(u'{%macro "'); handler(self.macro_name); handler(u'"%}')
        Token.output(self, handler)
        handler(u'{%endmacro%}')



class DjangoCallMacroTag(Token): # TODO: not standard Django -> should be removed
    def process_params(self, params):
        assert len(params) == 2
        name = params[1].output_as_string()
        assert name[0] in ('"', "'") and name[0] == name[-1]
        self.macro_name = name[1:-1]

    def output(self, handler):
        handler(u'{%callmacro "')
        handler(self.macro_name)
        handler(u'"%}')


class DjangoCompressTag(DjangoContainer):
    """
    {% compress %} ... {% endcompress %}
    """
    def process_params(self, params):
        pass

    def output(self, handler):
        # Don't output the template tags.
        # (these are hints to the preprocessor only.)
        Token.output(self, handler)


class DjangoIfTag(DjangoContainer):
    """
    {% if condition %}...{% else %}...{% endif %}
    """
    def process_params(self, params):
        self._params = params

    def output(self, handler):
        handler(u'{%if ');
        handler(' '.join(p.output_as_string() for p in self._params[1:]))
        handler(u'%}')

        map(handler, self.children)

        # Render {% else %} if this node had an else-block
        # NOTE: nest_block_level_elements will place the second part into
        # children2
        if hasattr(self, 'children2'):
            handler(u'{%else%}')
            map(handler, self.children2)

        handler(u'{%endif%}')


class DjangoIfEqualTag(DjangoContainer):
    """
    {% ifequal a b %}...{% else %}...{% endifequal %}
    """
    def process_params(self, params):
        self._params = params
        if not len(self._params) == 3:
            raise CompileException(self, '{% ifequal %} needs exactly two parameters')

    def output(self, handler):
        handler(u'{%ifequal ');
        handler(' '.join(p.output_as_string() for p in self._params[1:]))
        handler(u'%}')

        map(handler, self.children)

        # Render {% else %} if this node had an else-block
        if hasattr(self, 'children2'):
            handler(u'{%else%}')
            map(handler, self.children2)

        handler(u'{%endifequal%}')


class DjangoBlockTag(DjangoContainer):
    """
    Contains:
    {% block %} children {% endblock %}
    Note: this class should not inherit from DjangoTag, because it's .children are different...  XXX
    """
    def process_params(self, params):
        self.block_name = params[1].output_as_string()

    def output(self, handler):
        handler(u'{%block '); handler(self.block_name); handler(u'%}')
        Token.output(self, handler)
        handler(u'{%endblock%}')


# ====================================[ Parser extensions ]=====================================


# Mapping for turning the lex tree into a Django parse tree
_PARSER_MAPPING_DICT = {
    'content': DjangoContent,
    'django-tag': DjangoTag,
    'django-variable': DjangoVariable,
    'django-comment': DjangoComment,
    'django-multiline-comment': DjangoMultilineComment,
    'django-verbatim': DjangoVerbatim,
}

def _add_parser_extensions(tree):
    """
    Turn the lex tree into a parse tree.
    Actually, nothing more than replacing the parser classes, as
    a wrapper around the lex tree.
    """
    tree.__class__ = DjangoRootNode

    def _add_parser_extensions2(node):
        if isinstance(node, Token):
            if node.name in _PARSER_MAPPING_DICT:
                node.__class__ = _PARSER_MAPPING_DICT[node.name]
                if hasattr(node, 'init_extension'):
                    node.init_extension()

            map(_add_parser_extensions2, node.all_children)

    _add_parser_extensions2(tree)


# Mapping for replacing the *inline* DjangoTag nodes into more specific nodes
_DJANGO_INLINE_ELEMENTS = {
    'extends': DjangoExtendsTag,
    'trans': DjangoTransTag,
    'plural': DjangoPluralTag,
    'include': DjangoIncludeTag,
    'url': DjangoUrlTag,
    'load': DjangoLoadTag,
    'callmacro': DjangoCallMacroTag,
    '!': DjangoPreprocessorConfigTag,
}

def _process_inline_tags(tree):
    """
    Replace DjangoTag elements by more specific elements.
    """
    for c in tree.all_children:
        if isinstance(c, DjangoTag) and c.tagname in _DJANGO_INLINE_ELEMENTS:
            # Patch class
            c.__class__ = _DJANGO_INLINE_ELEMENTS[c.tagname]

            # In-line tags don't have childnodes, but process what we had
            # as 'children' as parameters.
            c.process_params(list(c.get_childnodes_with_name('django-tag-element')))
            #c.children = [] # TODO: for Jonathan -- we want to keep this tags API compatible with the DjangoTag object, so keep children

        elif isinstance(c, DjangoTag):
            _process_inline_tags(c)


# Mapping for replacing the *block* DjangoTag nodes into more specific nodes
__DJANGO_BLOCK_ELEMENTS = {
    'block': ('endblock', DjangoBlockTag),
    'blocktrans': ('endblocktrans', DjangoBlocktransTag),
    'macro': ('endmacro', DjangoMacroTag),
    'decorate': ('enddecorate', DjangoDecorateTag),
    'compress': ('endcompress', DjangoCompressTag),
    '!raw': ('!endraw', DjangoRawOutput),

    'if': ('else', 'endif', DjangoIfTag),
    'ifequal': ('else', 'endifequal', DjangoIfEqualTag),
}



# ====================================[ Check parser settings in template {% ! ... %} ]================


def _update_preprocess_settings(tree, context):
    """
    Look for parser configuration tags in the template tree.
    Return a dictionary of the compile options to use.
    """
    for c in tree.child_nodes_of_class(DjangoPreprocessorConfigTag):
        for o in c.preprocessor_options:
            context.options.change(o, c)


# ====================================[ 'Patched' class definitions ]=====================================


class DjangoPreprocessedInclude(DjangoContainer):
    def init(self, children, with_params=None):
        self.children = children
        self.with_params = with_params

    def output(self, handler):
        if self.with_params:
            handler('{%with')
            for c in self.with_params:
                handler(' ')
                handler(c)
            handler('%}')

        DjangoContainer.output(self, handler)

        if self.with_params:
            handler('{%endwith%}')


class DjangoPreprocessedCallMacro(DjangoContainer):
    def init(self, children):
        self.children = children

class DjangoPreprocessedVariable(DjangoContent):
    def init(self, var_value):
        self.children = var_value

class DjangoTranslated(DjangoContent):
    def init(self, translated_text, translation_info):
        self.translation_info = translation_info
        self.children = [ translated_text ]



# ====================================[ Parse tree manipulations ]=====================================

def apply_method_on_parse_tree(tree, class_, method, *args, **kwargs):
    for c in tree.all_children:
        if isinstance(c, class_):
            getattr(c, method)(*args, **kwargs)

        if isinstance(c, Token):
            apply_method_on_parse_tree(c, class_, method, *args, **kwargs)


def _find_first_level_dependencies(tree, context):
    for node in tree.child_nodes_of_class((DjangoIncludeTag, DjangoExtendsTag)):
        if isinstance(node, DjangoExtendsTag):
            context.remember_extends(node.template_name)

        elif isinstance(node, DjangoIncludeTag):
            context.remember_include(node.template_name)


def _process_extends(tree, context):
    """
    {% extends ... %}
    When this tree extends another template. Load the base template,
    compile it, merge the trees, and return a new tree.
    """
    extends_tag = None

    try:
        base_tree = None

        for c in tree.all_children:
            if isinstance(c, DjangoExtendsTag) and not c.template_name_is_variable:
                extends_tag = c
                base_tree = context.load(c.template_name)
                break

        if base_tree:
            base_tree_blocks = list(base_tree.child_nodes_of_class(DjangoBlockTag))
            tree_blocks = list(tree.child_nodes_of_class(DjangoBlockTag))

            # Retreive list of block tags in the outer scope of the child template.
            # These are the blocks which at least have to exist in the parent.
            outer_tree_blocks = filter(lambda b: isinstance(b, DjangoBlockTag), tree.children)

            # For every {% block %} in the base tree
            for base_block in base_tree_blocks:
                # Look for a block with the same name in the current tree
                for block in tree_blocks[:]:
                    if block.block_name == base_block.block_name:
                        # Replace {{ block.super }} variable by the parent's
                        # block node's children.
                        block_dot_super = base_block.children

                        for v in block.child_nodes_of_class(DjangoVariable):
                            if v.varname == 'block.super':
                                # Found a {{ block.super }} declaration, deep copy
                                # parent nodes in here
                                v.__class__ = DjangoPreprocessedVariable
                                v.init(deepcopy(block_dot_super[:]))

                        # Replace all nodes in the base tree block, with this nodes
                        base_block.children = block.children

                        # Remove block from list
                        if block in outer_tree_blocks:
                            outer_tree_blocks.remove(block)

            # We shouldn't have any blocks left (if so, they don't have a match in the parent)
            if outer_tree_blocks:
                warning = 'Found {%% block %s %%} which has not been found in the parent' % outer_tree_blocks[0].block_name
                if context.options.disallow_orphan_blocks:
                    raise CompileException(outer_tree_blocks[0], warning)
                else:
                    context.raise_warning(outer_tree_blocks[0], warning)

            # Move every {% load %} and {% ! ... %} to the base tree
            for l in tree.child_nodes_of_class((DjangoLoadTag, DjangoPreprocessorConfigTag)):
                base_tree.children.insert(0, l)

            return base_tree

        else:
            return tree

    except TemplateDoesNotExist, e:
        # It is required that the base template exists.
        raise CompileException(extends_tag, 'Base template {%% extends "%s" %%} not found' %
                    (extends_tag.template_name if extends_tag else "..."))


def _preprocess_includes(tree, context):
    """
    Look for all the {% include ... %} tags and replace it by their include.
    """
    include_blocks = list(tree.child_nodes_of_class(DjangoIncludeTag))

    for block in include_blocks:
        if not block.template_name_is_variable:
            try:
                # Parse include
                include_tree = context.load(block.template_name)

                # Move tree from included file into {% include %}
                block.__class__ = DjangoPreprocessedInclude
                block.init([ include_tree ], block.with_params)

                block.path = include_tree.path
                block.line = include_tree.line
                block.column = include_tree.column

            except TemplateDoesNotExist, e:
                raise CompileException(block, 'Template in {%% include %%} tag not found (%s)' % block.template_name)


def _preprocess_decorate_tags(tree, context):
    """
    Replace {% decorate "template.html" %}...{% enddecorate %} by the include,
    and fill in {{ content }}
    """
    class DjangoPreprocessedDecorate(DjangoContent):
        def init(self, children):
            self.children = children

    for decorate_block in list(tree.child_nodes_of_class(DjangoDecorateTag)):
        # Content nodes
        content = decorate_block.children

        # Replace content
        try:
            include_tree = context.load(decorate_block.template_name)

            for content_var in include_tree.child_nodes_of_class(DjangoVariable):
                if content_var.varname == 'decorator.content':
                    content_var.__class__ = DjangoPreprocessedVariable
                    content_var.init(content)

            # Move tree
            decorate_block.__class__ = DjangoPreprocessedDecorate
            decorate_block.init([ include_tree ])

        except TemplateDoesNotExist, e:
            raise CompileException(decorate_block, 'Template in {% decorate %} tag not found (%s)' % decorate_block.template_name)


def _group_all_loads(tree):
    """
    Look for all {% load %} tags, and group them to one, on top.
    """
    all_modules = set()
    first_load_tag = None
    to_remove = []

    # Collect all {% load %} nodes.
    for load_tag in tree.child_nodes_of_class(DjangoLoadTag):
        # Keeps tags like {% load ssi from future %} as they are.
        # Concatenating these is invalid.
        if not ('from' in load_tag.output_as_string()  and 'future' in load_tag.output_as_string()):
            to_remove.append(load_tag)
            # First tag
            if not first_load_tag:
                first_load_tag = load_tag

            for l in load_tag.modules:
                all_modules.add(l)

    # Remove all {% load %} nodes except {% load ... from future %}
    tree.remove_child_nodes(to_remove)

    # Place all {% load %} in the first node of the tree
    if first_load_tag:
        first_load_tag.modules = list(all_modules)
        tree.children.insert(0, first_load_tag)

        # But {% extends %} really needs to be placed before everything else
        # NOTE: (Actually not necessary, because we don't support variable extends.)
        extends_tags = list(tree.child_nodes_of_class(DjangoExtendsTag))
        tree.remove_child_nodes_of_class(DjangoExtendsTag)

        for e in extends_tags:
            tree.children.insert(0, e)

def _preprocess_urls(tree):
    """
    Replace URLs without variables by their resolved value.
    """
    # Do 'reverse' import at this point. To be sure we use the
    # latest version. Other Django plug-ins like localeurl tend
    # to monkey patch this code.
    from django.core.urlresolvers import NoReverseMatch
    from django.core.urlresolvers import reverse

    def parse_url_params(urltag):
        if not urltag.url_params:
            raise CompileException(urltag, 'Attribute missing for {% url %} tag.')

        # Parse url parameters
        name = urltag.url_params[0].output_as_string()
        args = []
        kwargs = { }
        for k in urltag.url_params[1:]:
            k = k.output_as_string()
            if '=' in k:
                k,v = k.split('=', 1)
                kwargs[str(k)] = _variable_to_literal(v)
            else:
                args.append(_variable_to_literal(k))

        return name, args, kwargs

    for urltag in tree.child_nodes_of_class(DjangoUrlTag):
        try:
            name, args, kwargs = parse_url_params(urltag)
            if not 'as' in args:
                result = reverse(name, args=args, kwargs=kwargs)
                urltag.preprocess(result)
        except NoReverseMatch, e:
            pass
        except NoLiteraleException, e:
            # Got some variable, can't prerender url
            pass


def _preprocess_variables(tree, values_dict):
    """
    Replace known variables, like {{ MEDIA_URL }} by their value.
    """
    for var in tree.child_nodes_of_class(DjangoVariable):
        if var.varname in values_dict:
            value = values_dict[var.varname]
            var.__class__ = DjangoPreprocessedVariable
            var.init([value])

                # TODO: escape
                #       -> for now we don't escape because
                #          we are unsure of the autoescaping state.
                #          and 'resolve' is only be used for variables
                #          like MEDIA_URL which are safe in HTML.

def _preprocess_trans_tags(tree):
    """
    Replace {% trans %} and {% blocktrans %} if they don't depend on variables.
    """
    convert_var = lambda v: '%%(%s)s' % v

    def process_blocktrans(trans):
        # Return True when this {% blocktrans %} contains assignments
        # like {% blocktrans with key=value and key2=value2 %} or
        # {% blocktrans with value as key and value2 as key2 %}
        #
        # TODO: adjust this method to be able to preprocess these as well.
        #       ({% with %} syntax is not completely compatible between Django
        #       1.2 and 1.3. Django 1.2 does not support with statements with
        #       multiple parameters.
        if isinstance(trans, DjangoBlocktransTag):
            params = ' '.join(map(lambda t: t.output_as_string(), trans.params))
            return not 'and' in params and not '=' in params
        else:
            return True


    for trans in tree.child_nodes_of_class((DjangoTransTag, DjangoBlocktransTag)):
        # Process {% blocktrans %}
        if isinstance(trans, DjangoBlocktransTag) and process_blocktrans(trans):
            translation_info = trans.translation_info

            # Translate strings
            string = _(translation_info.string or ' ') # or ' ', because we don't want to translate the empty string which returns PO meta info.
            if translation_info.has_plural:
                plural_string = ungettext(translation_info.string, translation_info.plural_string, 2)

            # Replace %(variable)s in translated strings by {{ variable }}
            for v in translation_info.variables:
                if convert_var(v) in string:
                    string = string.replace(convert_var(v), '{{%s}}' % v)
                #else:
                #    raise CompileException(trans,
                #            'Could not find variable "%s" in {%% blocktrans %%} "%s" after translating.' % (v, string))

            if translation_info.has_plural:
                for v in translation_info.plural_variables:
                    if convert_var(v) in plural_string:
                        plural_string = plural_string.replace(convert_var(v), '{{%s}}' % v)
                #    else:
                #        raise CompileException(trans,
                #                'Could not find variable "%s" in {%% blocktrans %%} "%s" after translating.' % (v, plural_string))

            # Wrap in {% if test %} for plural checking and in {% with test for passing parameters %}
            if translation_info.has_plural:
                # {% blocktrans count /expression/ as /variable/ and ... %}
                output = (
                    '{%with ' + ' '.join(map(lambda t: t.output_as_string(), trans.params[1:])) + '%}' +
                    '{%if ' + trans.params[3].output_as_string() + ' > 1%}' + plural_string + '{%else%}' + string + '{%endif%}' +
                    '{%endwith%}')
            else:
                if len(trans.params):
                    # {% blocktrans with /expression/ as /variable/ and ... %}
                    output = '{%' + ' '.join(map(lambda t: t.output_as_string(), trans.params)) + '%}' + string + '{%endwith%}'
                else:
                    # {% blocktrans %}
                    output = string

            # Replace {% blocktrans %} by its translated output.
            trans.__class__ = DjangoTranslated
            trans.init(output, translation_info)

        # Process {% trans "..." %}
        elif isinstance(trans, DjangoTransTag):
            if not trans.is_variable:
                output = _(trans.string or ' ')
                translation_info = trans.translation_info
                trans.__class__ = DjangoTranslated
                trans.init(output, translation_info)


def _preprocess_macros(tree):
    """
    Replace every {% callmacro "name" %} by the content of {% macro "name" %} ... {% endmacro %}
    NOTE: this will not work with recursive macro calls.
    """
    macros = { }
    for m in tree.child_nodes_of_class(DjangoMacroTag):
        macros[m.macro_name] = m

    for call in tree.child_nodes_of_class(DjangoCallMacroTag):
        if call.macro_name in macros:
            # Replace the call node by a deep-copy of the macro childnodes
            call.__class__ = DjangoPreprocessedCallMacro
            call.init(deepcopy(macros[call.macro_name].children[:]))

    # Remove all macro nodes
    tree.remove_child_nodes_of_class(DjangoMacroTag)


def _execute_preprocessable_tags(tree):
    preprocessable_tags = get_preprocessable_tags()

    for c in tree.all_children:
        if isinstance(c, DjangoTag) and c.tagname in preprocessable_tags:
            params = [ p.output_as_string() for p in c.get_childnodes_with_name('django-tag-element') ]
            try:
                c.children = [ preprocessable_tags[c.tagname](*params) ]
                c.__class__ = DjangoContent
            except NotPreprocessable:
                pass

        elif isinstance(c, DjangoContainer):
            _execute_preprocessable_tags(c)


def remember_gettext_entries(tree, context):
    """
    Look far all the {% trans %} and {% blocktrans %} tags in the tree,
    and copy the translatable strings into the context.
    """
    # {% trans %}
    for node in tree.child_nodes_of_class(DjangoTransTag):
        context.remember_gettext(node, node.string)

    # {% blocktrans %}
    for node in tree.child_nodes_of_class(DjangoBlocktransTag):
        info = node.translation_info

        context.remember_gettext(node, info.string)

        if info.has_plural:
            context.remember_gettext(node, info.plural_string)



from template_preprocessor.core.html_processor import compile_html


def parse(source_code, path, context, main_template=False):
    """
    Parse the code.
    - source_code: string
    - path: for attaching meta information to the tree.
    - context: preprocess context (holding the settings/dependecies/warnings, ...)
    - main_template: False for includes/extended templates. True for the
                     original path that was called.
    """
    # To start, create the root node of a tree.
    tree = Token(name='root', line=1, column=1, path=path)
    tree.children = [ source_code ]

    # Lex Django tags
    tokenize(tree, __DJANGO_STATES, Token)

    # Phase I: add parser extensions
    _add_parser_extensions(tree)

    # Phase II: process inline tags
    _process_inline_tags(tree)

    # Phase III: create recursive structure for block level tags.
    nest_block_level_elements(tree, __DJANGO_BLOCK_ELEMENTS, DjangoTag, lambda c: c.tagname)

    # === Actions ===

    if main_template:
        _find_first_level_dependencies(tree, context)

    # Extend parent template and process includes
    tree = _process_extends(tree, context) # NOTE: this returns a new tree!
    _preprocess_includes(tree, context)
    _preprocess_decorate_tags(tree, context)

    # Following actions only need to be applied if this is the 'main' tree.
    # It does not make sense to apply it on every include, and then again
    # on the complete tree.
    if main_template:

        _update_preprocess_settings(tree, context)
        options = context.options

        # Remember translations in context (form PO-file generation)
        remember_gettext_entries(tree, context)

        # Do translations
        if options.preprocess_translations:
            _preprocess_trans_tags(tree)

        # Reverse URLS
        if options.preprocess_urls:
            _preprocess_urls(tree)

        # Do variable lookups
        if options.preprocess_variables:
            sites_enabled = 'django.contrib.sites' in settings.INSTALLED_APPS

            _preprocess_variables(tree,
                        {
                            'MEDIA_URL': getattr(settings, 'MEDIA_URL', ''),
                            'STATIC_URL': getattr(settings, 'STATIC_URL', ''),
                        })
            if sites_enabled:
                from django.contrib.sites.models import Site
                try:
                    # Don't preprocess anything when we don't have a Site
                    # instance yet.
                    site = Site.objects.get_current()
                    _preprocess_variables(tree,
                            {
                                'SITE_DOMAIN': site.domain,
                                'SITE_NAME': site.name,
                                'SITE_URL': 'http://%s' % site.domain,
                            })
                except Site.DoesNotExist, e:
                    pass

        # Don't output {% block %} tags in the compiled file.
        if options.remove_block_tags:
            tree.collapse_nodes_of_class(DjangoBlockTag)

        # Preprocess {% callmacro %} tags
        if options.preprocess_macros:
            _preprocess_macros(tree)

        # Group all {% load %} statements
        if options.merge_all_load_tags:
            _group_all_loads(tree)

        # Preprocessable tags
        if options.execute_preprocessable_tags:
            _execute_preprocessable_tags(tree)

        # HTML compiler
        if options.is_html:
            compile_html(tree, context)
    return tree

########NEW FILE########
__FILENAME__ = html_processor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django template preprocessor.
Author: Jonathan Slenders, City Live
"""

"""
HTML parser for the template preprocessor.
-----------------------------------------------

Parses HTML in de parse tree. (between django template tags.)
"""

from template_preprocessor.core.django_processor import *
from template_preprocessor.core.lexer import State, StartToken, Push, Record, Shift, StopToken, Pop, CompileException, Token, Error
from template_preprocessor.core.lexer_engine import tokenize, nest_block_level_elements
from template_preprocessor.core.utils import check_external_file_existance, is_remote_url

from copy import deepcopy
from django.utils.translation import ugettext as _, ungettext

import codecs
import os
import string


# HTML 4 tags
__HTML4_BLOCK_LEVEL_ELEMENTS = ('html', 'head', 'body', 'meta', 'script', 'noscript', 'p', 'div', 'ul', 'ol', 'dl', 'dt', 'dd', 'li', 'table', 'td', 'tr', 'th', 'thead', 'tfoot', 'tbody', 'br', 'link', 'title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'form', 'object', 'base', 'iframe', 'fieldset', 'code', 'blockquote', 'legend', 'pre', 'embed')
__HTML4_INLINE_LEVEL_ELEMENTS = ('address', 'span', 'a', 'b', 'i', 'em', 'del', 'ins', 'strong', 'select', 'label', 'q', 'sub', 'sup', 'small', 'sub', 'sup', 'option', 'abbr', 'img', 'input', 'hr', 'param', 'button', 'caption', 'style', 'textarea', 'colgroup', 'col', 'samp', 'kbd', 'map', 'optgroup', 'strike', 'var', 'wbr', 'dfn')

# HTML 5 tags
__HTML5_BLOCK_LEVEL_ELEMENTS = ( 'article', 'aside', 'canvas', 'figcaption', 'figure', 'footer', 'header', 'hgroup', 'output', 'progress', 'section', 'video', )
__HTML5_INLINE_LEVEL_ELEMENTS = ('audio', 'details', 'command', 'datalist', 'mark', 'meter', 'nav', 'source', 'summary', 'time', 'samp', 'cite' )

# All HTML tags
__HTML_BLOCK_LEVEL_ELEMENTS = __HTML4_BLOCK_LEVEL_ELEMENTS + __HTML5_BLOCK_LEVEL_ELEMENTS
__HTML_INLINE_LEVEL_ELEMENTS = __HTML4_INLINE_LEVEL_ELEMENTS + __HTML5_INLINE_LEVEL_ELEMENTS


# Following tags are also listed as block elements, but this list can only contain inline-elements.
__HTML_INLINE_BLOCK_ELEMENTS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img', 'object', 'button')


        # HTML tags consisting of separate open and close tag.
__ALL_HTML_TAGS = __HTML_BLOCK_LEVEL_ELEMENTS + __HTML_INLINE_LEVEL_ELEMENTS

__DEPRECATED_HTML_TAGS = ('i', 'b', 'u', 'tt', 'strike', )

__HTML_ATTRIBUTES = {
    # Valid for every HTML tag
    '_': ('accesskey', 'id', 'class', 'contenteditable', 'contextmenu', 'dir', 'draggable', 'dropzone',
        'hidden', 'spellcheck', 'style', 'tabindex', 'lang', 'xmlns', 'title', 'xml:lang',

        # HTML 5
        'itemscope', 'itemtype', 'itemprop', 'role',
        
        # ARIA support
        # see: http://www.w3.org/TR/wai-aria/states_and_properties
        'aria-atomic', 'aria-busy', 'aria-controls', 'aria-describedby', 'aria-disabled', 
        'aria-dropeffect', 'aria-flowto', 'aria-grabbed', 'aria-haspopup', 'aria-hidden', 
        'aria-invalid', 'aria-label', 'aria-labelledby', 'aria-live', 'aria-owns', 'aria-relevant',

        # Event attributes
        'onclick', 'ondblclick', 'onmousedown', 'onmousemove', 'onmouseout', 'onmouseover', 'onmouseup',
        'onkeydown', 'onkeypress', 'onkeyup',
        ),

    # Attributes for specific HTML tags

    'a': ('href', 'hreflang', 'media', 'type', 'target', 'rel', 'name', 'share_url', 'onblur', 'onfocus'), # share_url is not valid, but used in the facebook share snipped.
    'audio': ('autoplay', 'controls', 'loop', 'preload', 'src'),
    'canvas': ('height', 'width'),
    'font': ('face', 'size', ),
    'form': ('action', 'method', 'enctype', 'name', 'onblur', 'onfocus', ),
    'html': ('xmlns', 'lang', 'dir', 'itemscope', 'itemtype',),
    'body': ('onLoad', ),
    'img': ('src', 'alt', 'height', 'width', ),
    'input': ('type', 'name', 'value', 'maxlength', 'checked', 'disabled', 'src', 'size', 'readonly', 'autocomplete', 'placeholder', 'onblur', 'onfocus', 'onchange', 'onselect', ),
    'select': ('name', 'value', 'size', 'disabled', 'onblur', 'onfocus', 'onchange', ),
    'textarea': ('name', 'rows', 'cols', 'readonly', 'placeholder', 'onblur', 'onfocus', 'onchange', 'onselect', ),
    'link': ('type', 'rel', 'href', 'media', 'charset', 'sizes', ),
    'meta': ('content', 'http-equiv', 'name', 'property', 'charset', 'itemprop', ),
    'script': ('type', 'src', 'language', 'charset', ),
    'style': ('type', 'media', ),
    'td': ('colspan', 'rowspan', 'width', 'height', ),
    'th': ('colspan', 'rowspan', 'width', 'height', 'scope', ),
    'button': ('value', 'type', 'name', 'onblur', 'onfocus', ),
    'label': ('for', 'onblur', 'onfocus', ),
    'option': ('value', 'selected', ),
    'base': ('href', ),
    'object': ('data', 'type', 'width', 'height', 'quality', ),
    'iframe': ('src', 'srcdoc', 'name', 'height', 'width', 'marginwidth', 'marginheight', 'scrolling', 'sandbox', 'seamless', 'frameborder', 'allowTransparency', 'webkitAllowFullScreen', 'allowFullScreen', 'mozallowfullscreen', 'frameBorder', ),
    'param': ('name', 'value', ),
    'table': ('cellpadding', 'cellspacing', 'summary', 'width', ),
    'p': ('align', ), # Deprecated
    'embed': ('src', 'allowscriptaccess', 'allowScriptAccess', 'height', 'width', 'allowfullscreen', 'type', ),
    'video': ('audio', 'autoplay', 'controls', 'height', 'loop', 'poster', 'preload', 'src', 'width'),
}

# TODO: check whether forms have {% csrf_token %}
# TODO: check whether all attributes are valid.

def xml_escape(s):
    # XML escape
    s = unicode(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')#.replace("'", '&#39;')

    # Escape braces, to make sure Django tags will not be rendered in here.
    s = unicode(s).replace('}', '&#x7d;').replace('{', '&#x7b;')

    return s



__HTML_STATES = {
    'root' : State(
            # conditional comments
            State.Transition(r'<!(--)?\[if', (StartToken('html-start-conditional-comment'), Record(), Shift(), Push('conditional-comment'), )),
            State.Transition(r'<!(--)?(<!)?\[endif\](--)?>', (StartToken('html-end-conditional-comment'), Record(), Shift(), StopToken(), )),
            State.Transition(r'<!\[CDATA\[', (StartToken('html-cdata'), Shift(), Push('cdata'), )),

            # XML doctype
            State.Transition(r'<!DOCTYPE', (StartToken('html-doctype'), Record(), Shift(), Push('doctype'), )),

            # HTML comments
            State.Transition(r'<!--', (StartToken('html-comment'), Shift(), Push('comment'), )),

            # HTML tags
            State.Transition(r'</(?=\w)', (StartToken('html-end-tag'), Shift(), Push('tag'), )),
            State.Transition(r'<(?=\w)', (StartToken('html-tag'), Shift(), Push('tag'), )),

            State.Transition(r'&', (StartToken('html-entity'), Record(), Shift(), Push('entity'), )),

            # Content
            State.Transition(r'([^<>\s&])+', (StartToken('html-content'), Record(), Shift(), StopToken(), )),

            # Whitespace
            State.Transition(r'\s+', (StartToken('html-whitespace'), Record(), Shift(), StopToken(), )),

            State.Transition(r'.|\s', (Error('Parse error in HTML document'), )),
            ),
    'conditional-comment': State(
            State.Transition(r'[\s\w()!|&]+', (Record(), Shift(), )),
            State.Transition(r'\](--)?>(\s*<!-->)?', (Record(), Shift(), Pop(), StopToken(), )),
            State.Transition(r'.|\s', (Error('Parse error in Conditional Comment'), )),
            ),
    'comment': State(
            # End of comment
            State.Transition(r'-->', (Shift(), Pop(), StopToken(), )),

            # Comment content
            State.Transition(r'([^-]|-(?!->))+', (Record(), Shift(), )),

            State.Transition(r'.|\s', (Error('Parse error in HTML comment'), )),
            ),
    'cdata': State(
            # End of CDATA block
            State.Transition(r'\]\]>', (Shift(), Pop(), StopToken() )),

            # CDATA content
            State.Transition(r'([^\]]|\](?!\]>))+', (Record(), Shift(), )),

            State.Transition(r'.|\s', (Error('Parse error in CDATA tag'), )),
            ),
    'doctype': State(
            State.Transition(r'[^>\s]+', (Record(), Shift(), )),
            State.Transition(r'\s+', (Record(' '), Shift(), )),
            State.Transition(r'>', (Record(), StopToken(), Shift(), Pop(), )),

            State.Transition(r'.|\s', (Error('Parse error in doctype tag'), )),
            ),
    'tag': State(
            # At the start of an html tag
            State.Transition('[^\s/>]+', (StartToken('html-tag-name'), Record(), Shift(), StopToken(), Pop(), Push('tag2'), )),

            State.Transition(r'.|\s', (Error('Parse error in HTML tag'), )),
            ),
    'tag2': State( # Inside the html tag
            # HTML tag attribute
            State.Transition(r'[\w:_-]+=', (StartToken('html-tag-attribute'),
                                            StartToken('html-tag-attribute-key'), Record(), Shift(), StopToken(),
                                            StartToken('html-tag-attribute-value'), Push('attribute-value'), )),

            # HTML tag attribute (oldstyle without = sign
            State.Transition(r'[\w:_-]+(?!=)', (StartToken('html-tag-attribute'), StartToken('html-tag-attribute-key'),
                                                    Record(), Shift(), StopToken(), StopToken(), )),

            # End of html tag
            State.Transition(r'\s*/>', (StartToken('html-tag-end-sign'), StopToken(), Shift(), Pop(), StopToken(), )),
            State.Transition(r'\s*>', (Shift(), Pop(), StopToken(), )),

            # Whitespace
            State.Transition(r'\s+', (Shift(), StartToken('html-tag-whitespace'), Record(' '), StopToken(), )),

            State.Transition(r'.|\s', (Error('Parse error in HTML tag'), )),
            ),
    'entity': State(
            State.Transition(r';', (Record(), Shift(), Pop(), StopToken() )),
            State.Transition(r'[#a-zA-Z0-9]+', (Record(), Shift(), )),
            State.Transition(r'.|\s', (Error('Parse error in HTML entity'), )),
            ),
    'attribute-value': State(
            # Strings or word characters
            State.Transition(r"'", (Record(), Shift(), Push('attribute-string'), )),
            State.Transition(r'"', (Record(), Shift(), Push('attribute-string2'), )),
            State.Transition(r'\w+', (Record(), Shift(), )),

            # Anything else? Pop back to the tag
            State.Transition(r'\s|.', (Pop(), StopToken(), StopToken() )),
            ),

    'attribute-string': State( # Double quoted
                    # NOTE: We could also use the regex r'"[^"]*"', but that won't work
                    #       We need a separate state for the strings, because the string itself could
                    #       contain a django tag, and it works this way in lexer.
            State.Transition(r"'", (Record(), Shift(), Pop(), Pop(), StopToken(), StopToken(), )),
            State.Transition(r'&', (StartToken('html-entity'), Record(), Shift(), Push('entity'), )),
            State.Transition(r"[^'&]+", (Record(), Shift(), )),
            ),
    'attribute-string2': State( # Single quoted
            State.Transition(r'"', (Record(), Shift(), Pop(), Pop(), StopToken(), StopToken(), )),
            State.Transition(r'&', (StartToken('html-entity'), Record(), Shift(), Push('entity'), )),
            State.Transition(r'[^"&]+', (Record(), Shift(), )),
            ),
    }


# ==================================[  HTML Parser Extensions ]================================

class HtmlNode(DjangoContent):
    """
    base class
    """
    pass

class HtmlDocType(HtmlNode):
    pass

class HtmlEntity(HtmlNode):
    pass

class HtmlConditionalComment(HtmlNode):
    """
    Contains:
    <!--[if ...]> children <![endif ...]-->
    """
    def process_params(self, params):
        self.__start = u''.join(params)

    def output(self, handler):
        handler(self.__start)
        Token.output(self, handler)
        handler(u'<![endif]-->')


class HtmlContent(HtmlNode):
    pass

class HtmlWhiteSpace(HtmlContent):
    def compress(self):
        self.children = [u' ']

class HtmlComment(HtmlNode):
    def init_extension(self):
        self.__show_comment_signs = True

    def remove_comment_signs(self):
        self.__show_comment_signs = False

    def output(self, handler):
        if self.__show_comment_signs: handler('<!--')
        Token.output(self, handler)
        if self.__show_comment_signs: handler('-->')

class HtmlCDATA(HtmlNode):
    def init_extension(self):
        self.__show_cdata_signs = True

    def remove_cdata_signs(self):
        self.__show_cdata_signs = False

    def output(self, handler):
        if self.__show_cdata_signs: handler('<![CDATA[')
        Token.output(self, handler)
        if self.__show_cdata_signs: handler(']]>')


class HtmlTag(HtmlNode):
    @property
    def html_attributes(self):
        attributes = {}

        for a in self.child_nodes_of_class(HtmlTagAttribute):
            attributes[a.attribute_name] = a.attribute_value

        return attributes

    def get_html_attribute_value_as_string(self, name):
        """
        Return attribute value. *Fuzzy* because it will render possible template tags
        in the string, and strip double quotes.
        """
        attrs = self.html_attributes
        if name in attrs:
            result = attrs[name].output_as_string()
            return result.strip('"\'')
        return None

    def is_inline(self):
        return self.html_tagname in __HTML_INLINE_LEVEL_ELEMENTS

    @property
    def is_closing_html_tag(self):
        """
        True when we have the slash, like in "<img src=...  />"
        """
        for c in self.children:
            if isinstance(c, HtmlTagEndSign):
                return True
        return False

    @property
    def html_tagname(self):
        """
        For <img src="..." />, return 'img'
        """
        for c in self.children:
            if c.name == 'html-tag-name':
                return c.output_as_string()

    def set_html_attribute(self, name, attribute_value):
        """
        Replace attribute and add double quotes.
        """
        # Delete attributes having this name
        for a in self.child_nodes_of_class(HtmlTagAttribute):
            if a.attribute_name == name:
                self.remove_child_nodes([ a ])

        # Set attribute
        self.add_attribute(name, '"%s"' % xml_escape(attribute_value))


    def add_attribute(self, name, attribute_value):
        """
        Add a new attribute to this html tag.
        """
        # First, create a whitespace, to insert before the attribute
        ws = HtmlTagWhitespace()
        ws.children = [ ' ' ]

        # Attribute name
        n= HtmlTagAttributeName()
        n.children = [ name, '=' ]

        # Attribute
        a = HtmlTagAttribute()
        a.children = [n, attribute_value]

        # If we have a slash at the end, insert the attribute before the slash
        if isinstance(self.children[-1], HtmlTagEndSign):
            self.children.insert(-1, ws)
            self.children.insert(-1, a)
        else:
            self.children.append(ws)
            self.children.append(a)

    def output(self, handler):
        handler('<')
        Token.output(self, handler)
        handler('>')

    def remove_whitespace_in_html_tag(self):
        """
        Remove all whitespace that can removed between
        attributes. (To be called after removing attributes.)
        """
        i = -1

        while isinstance(self.children[i], HtmlTagEndSign):
            i -= 1

        while self.children and isinstance(self.children[i], HtmlTagWhitespace):
            self.children.remove(self.children[i])


class HtmlTagName(HtmlNode):
    pass


class HtmlEndTag(HtmlNode):
    @property
    def html_tagname(self):
        for c in self.children:
            if c.name == 'html-tag-name':
                return c.output_as_string()

    @property
    def is_closing_html_tag(self):
        return False

    def output(self, handler):
        handler('</')
        Token.output(self, handler)
        handler('>')

class HtmlTagEndSign(HtmlNode):
    def output(self, handler):
        """
        This is the '/' in <span />
        """
        handler('/')
        # yield ' /' # Do we need a space before the closing slash?

class HtmlTagAttribute(HtmlNode):
    @property
    def attribute_name(self):
        """
        Return attribute name
        (Result is a string)
        """
        key = self.child_nodes_of_class(HtmlTagAttributeName).next()
        key = key.output_as_string()
        return key.rstrip('=')

    @property
    def attribute_value(self):
        """
        Return attribute value, or None if none was given (value can be optional (HTML5))
        (result is nodes or None)
        """
        try:
            return self.child_nodes_of_class(HtmlTagAttributeValue).next()
        except StopIteration:
            return None


class HtmlTagPair(HtmlNode):
    """
    Container for the opening HTML tag, the matching closing HTML
    and all the content. (e.g. <p> + ... + </p>)
    This is overriden for every possible HTML tag.
    """
    pass


class HtmlTagWhitespace(HtmlNode):
    pass

class HtmlTagAttributeName(HtmlNode):
    pass


class HtmlTagAttributeValue(HtmlNode):
    def init_extension(self):
        self.__double_quotes = False

    def output(self, handler):
        if self.__double_quotes:
            handler('"')

        Token.output(self, handler)

        if self.__double_quotes:
            handler('"')


class HtmlScriptNode(HtmlNode):
    """
    <script type="text/javascript" src="..."> ... </script>
    """
    html_tagname = 'script'
    def process_params(self, params):
        # Create dictionary of key/value pairs for this script node
        self.__attrs = { }
        for p in params:
            if isinstance(p, HtmlTagAttribute):
                key = p.child_nodes_of_class(HtmlTagAttributeName).next()
                val = p.child_nodes_of_class(HtmlTagAttributeValue).next()

                key = key.output_as_string()
                val = val.output_as_string()

                self.__attrs[key] = val

        self.is_external = ('src=' in self.__attrs)

    def _get_script_source(self):
        """
        Return a string containing the value of the 'src' property without quotes.
        ** Note that this property is a little *fuzzy*!
           It can return a django tag like '{{ varname }}', but as a string.
        """
        if self.is_external:
            return self.__attrs['src='].strip('"\'')

    def _set_script_source(self, value):
        self.__attrs['src='] = '"%s"' % xml_escape(value)

    script_source = property(_get_script_source, _set_script_source)

    def output(self, handler):
        handler('<script ')
        handler(u' '.join([ u'%s%s' % (a, self.__attrs[a]) for a in self.__attrs.keys() ]))
        handler('>')

        if not self.is_external:
            handler('//<![CDATA[\n')

        Token.output(self, handler)

        if not self.is_external:
            handler(u'//]]>\n')

        handler(u'</script>')


class HtmlStyleNode(HtmlNode):
    """
    <style type="text/css"> ... </style>
    """
    html_tagname = 'style'

    def process_params(self, params):
        self.is_external = False # Always False

    def output(self, handler):
        handler(u'<style type="text/css"><!--')
        Token.output(self, handler)
        handler(u'--></style>')


class HtmlPreNode(HtmlNode):
    """
    <pre> ... </pre>
    """
    html_tagname = 'pre'

    def process_params(self, params):
        self.__open_tag = HtmlTag()
        self.__open_tag.children = params

    def output(self, handler):
        self.__open_tag.output(handler)
        Token.output(self, handler)
        handler('</pre>')


class HtmlTextareaNode(HtmlNode):
    """
    <textarea> ... </textarea>
    """
    html_tagname = 'textarea'

    def process_params(self, params):
        self.__open_tag = HtmlTag()
        self.__open_tag.children = params

    def output(self, handler):
        self.__open_tag.output(handler)
        Token.output(self, handler)
        handler('</textarea>')



__HTML_EXTENSION_MAPPINGS = {
        'html-doctype': HtmlDocType,
        'html-entity': HtmlEntity,
        'html-cdata': HtmlCDATA,
        'html-comment': HtmlComment,
        'html-tag': HtmlTag,
        'html-tag-name': HtmlTagName,
        'html-end-tag': HtmlEndTag,
        'html-tag-end-sign': HtmlTagEndSign,
        'html-tag-attribute': HtmlTagAttribute,
        'html-tag-whitespace': HtmlTagWhitespace,
        'html-tag-attribute-key': HtmlTagAttributeName,
        'html-tag-attribute-value': HtmlTagAttributeValue,
        'html-content': HtmlContent,
        'html-whitespace': HtmlWhiteSpace,
}


def _add_html_parser_extensions(tree):
    """
    Patch (some) nodes in the parse tree, to get the HTML parser functionality.
    """
    for node in tree.all_children:
        if isinstance(node, Token):
            if node.name in __HTML_EXTENSION_MAPPINGS:
                node.__class__ = __HTML_EXTENSION_MAPPINGS[node.name]
                if hasattr(node, 'init_extension'):
                    node.init_extension()

            _add_html_parser_extensions(node)


def _nest_elements(tree):
    """
    Example:
    Replace (<script>, content, </script>) nodes by a single node, moving the
    child nodes to the script's content.
    """
    block_elements1 = {
        'html-start-conditional-comment': ('html-end-conditional-comment', HtmlConditionalComment),
    }
    nest_block_level_elements(tree, block_elements1, Token, lambda c: c.name)

    # Read as: move the content between:
        # element of this class, with this html_tagname, and
        # element of the other class, with the other html_tagname,
    # to a new parse node of the latter class.
    block_elements2 = {
        (False, HtmlTag, 'script'): ((False, HtmlEndTag, 'script'),  HtmlScriptNode),
        (False, HtmlTag, 'style'): ((False, HtmlEndTag, 'style'),  HtmlStyleNode),
        (False, HtmlTag, 'pre'): ((False, HtmlEndTag, 'pre'),  HtmlPreNode),
        (False, HtmlTag, 'textarea'): ((False, HtmlEndTag, 'textarea'),  HtmlTextareaNode),
    }

    nest_block_level_elements(tree, block_elements2, (HtmlTag, HtmlEndTag),
            lambda c: (c.is_closing_html_tag, c.__class__, c.html_tagname) )


# ==================================[  HTML Tree manipulations ]================================


def _merge_content_nodes(tree, context):
    """
    Concatenate whitespace and content nodes.
    e.g. when the we have "<p>...{% trans "</p>" %}" these nodes will be
         concatenated into one single node. (A preprocessed translation is a
         HtmlContent node)
    The usage in the example above is abuse, but in case of {% url %} and
    {% trans %} blocks inside javascript code, we want them all to be
    concatenated in order to make it possible to check the syntax of the
    result.
    e.g. "alert('{% trans "some weird characters in here: ',! " %}');"

    When insert_debug_symbols is on, only apply concatenation inside CSS and
    Javascript nodes. We want to keep the {% trans %} nodes in <body/> for
    adding line/column number annotations later on.
    """
    def apply(tree):
        for children in tree.children_lists:
            last_child = None

            for c in children[:]:
                if isinstance(c, HtmlContent):
                    # Second content node (following another content node)
                    if last_child:
                        for i in c.children:
                            last_child.children.append(i)
                        children.remove(c)
                    # Every first content node
                    else:
                        last_child = c
                        last_child.__class__ = HtmlContent
                else:
                    last_child = None

            # Apply recursively
            for c in children:
                if isinstance(c, Token):
                    _merge_content_nodes(c, context)

    # Concatenate nodes
    if context.insert_debug_symbols:
        # In debug mode: only inside script/style nodes
        map(apply, tree.child_nodes_of_class((HtmlStyleNode, HtmlScriptNode)))
    else:
        apply(tree)


def _remove_whitespace_around_html_block_level_tags(tree):
    for children in tree.children_lists:
        whitespace_elements = []
        after_block_level_element = False

        for c in children[:]:
            # If we find a block level element
            if (isinstance(c, HtmlTag) or isinstance(c, HtmlEndTag)) and c.html_tagname in __HTML_BLOCK_LEVEL_ELEMENTS:
                after_block_level_element = True

                # remove all whitespace before
                for w in whitespace_elements:
                    children.remove(w)
                whitespace_elements = []

                # Also, *inside* the block level element, remove whitespace at the
                # beginning and before the end
                while c.children and isinstance(c.children[0], HtmlWhiteSpace):
                    del c.children[0]
                while c.children and isinstance(c.children[-1], HtmlWhiteSpace):
                    del c.children[-1]

            # If we find a whitespace
            elif isinstance(c, HtmlWhiteSpace):
                if after_block_level_element:
                    # Remove whitespace after.
                    children.remove(c)
                else:
                    whitespace_elements.append(c)

            # Something else: reset state
            else:
                whitespace_elements = []
                after_block_level_element = False

            # Recursively
            if isinstance(c, Token):
                _remove_whitespace_around_html_block_level_tags(c)


def _compress_whitespace(tree):
    # Don't compress in the following tags
    dont_enter = [ HtmlScriptNode, HtmlStyleNode, HtmlPreNode, HtmlTextareaNode ]

    for c in tree.all_children:
        if isinstance(c, HtmlWhiteSpace):
            c.compress()
        elif isinstance(c, Token) and not any([ isinstance(c, t) for t in dont_enter ]):
            _compress_whitespace(c)


def _remove_empty_class_attributes(tree):
    """
    For all the HTML tags which have empty class="" attributes,
    remove the attribute.
    """
    # For every HTML tag
    for tag in tree.child_nodes_of_class(HtmlTag):
        for a in tag.child_nodes_of_class(HtmlTagAttribute):
            if a.attribute_name == 'class' and a.attribute_value.output_as_string() in ('', '""', "''"):
                tag.children.remove(a)


def _turn_comments_to_content_in_js_and_css(tree):
    for c in tree.child_nodes_of_class((HtmlStyleNode, HtmlScriptNode)):
        for c2 in c.child_nodes_of_class((HtmlCDATA, HtmlComment)):
            c2.__class__ = HtmlContent


def _remove_comments(tree):
    tree.remove_child_nodes_of_class(HtmlComment)


def _merge_nodes_of_type(tree, type_, dont_enter):
    """
    Merge nodes of this type into one node.
    """
    # Find all internal js nodes
    js_nodes = [ j for j in tree.child_nodes_of_class(type_, dont_enter=dont_enter) if not j.is_external ]

    if js_nodes:
        first = js_nodes[0]

        # Move all js code from the following js nodes in the first one.
        for js in js_nodes[1:]:
            # Move js content
            first.children = first.children + js.children
            js.children = []

        # Remove all empty javascript nodes
        tree.remove_child_nodes(js_nodes[1:])


# ==================================[  HTML validation ]================================

def _validate_html_tags(tree):
    """
    Check whether all HTML tags exist.
    """
    for tag in tree.child_nodes_of_class(HtmlTag):
        if tag.html_tagname not in __ALL_HTML_TAGS:
            # Ignore html tags in other namespaces:
            # (Like e.g. <x:tagname />, <fb:like .../>)
            if not ':' in tag.html_tagname:
                raise CompileException(tag, 'Unknown HTML tag: <%s>' % tag.html_tagname)


def _validate_html_attributes(tree):
    """
    Check whether HTML tags have invalid or double attributes.
    """
    for tag in tree.child_nodes_of_class(HtmlTag):
        # Ignore tags from other namespaces.
        if not ':' in tag.html_tagname:
            # Check for double attributes
            attr_list=[]

            if not tag.has_child_nodes_of_class((DjangoTag, DjangoContainer)):
                # TODO XXX:  {% if ... %} ... {% endif %} are not yet groupped in an DjangoIfNode, which means
                # that the content of the if-block is still a child of the parent. For now, we simply
                # don't check in these cases.
                for a in tag.child_nodes_of_class(HtmlTagAttribute, dont_enter=(DjangoTag, DjangoContainer)):
                    if a.attribute_name in attr_list:
                        raise CompileException(tag, 'Attribute "%s" defined more than once for <%s> tag' %
                                        (a.attribute_name, tag.html_tagname))
                    attr_list.append(a.attribute_name)

            # Check for invalid attributes
            for a in tag.html_attributes:
                if ':' in a or a.startswith('data-'):
                    # Don't validate tagnames from other namespaces, or HTML5 data- attributes
                    continue

                elif a in __HTML_ATTRIBUTES['_']:
                    continue

                elif tag.html_tagname in __HTML_ATTRIBUTES and a in __HTML_ATTRIBUTES[tag.html_tagname]:
                    continue

                else:
                    raise CompileException(tag, 'Invalid HTML attribute "%s" for <%s> tag' % (a, tag.html_tagname))


def _ensure_type_in_scripts(tree):
    """
    <script> should have type="text/javascript"
    """
    for tag in tree.child_nodes_of_class(HtmlTag):
        if tag.html_tagname == 'script':
            type_ = tag.html_attributes.get('type', None)

            if not bool(type_) or not type_.output_as_string() == u'"text/javascript"':
                raise CompileException(tag, '<script> should have type="text/javascript"')


def _ensure_type_in_css(tree):
    """
    <style> should have type="text/css"
    """
    for tag in tree.child_nodes_of_class(HtmlTag):
        if tag.html_tagname == 'style':
            type_ = tag.html_attributes.get('type', None)

            if not bool(type_) or not type_.output_as_string() == u'"text/css"':
                raise CompileException(tag, '<style> should have type="text/css"')


def _ensure_href_in_hyperlinks(tree):
    """
    Throw error if no href found in hyperlinks.
    """
    for tag in tree.child_nodes_of_class(HtmlTag):
        if tag.html_tagname == 'a':
            href = tag.html_attributes.get('href', None)
            if href:
                attr = href.output_as_string()
                if attr in ('', '""', "''"):
                    raise CompileException(tag, 'Empty href-attribute not allowed for hyperlink')

                # Disallow javascript: links
                if any([ attr.startswith(x) for x in ('javascript:', '"javascript:', "'javascript:")]):
                    raise CompileException(tag, 'Javascript hyperlinks not allowed.')

            else:
                raise CompileException(tag, 'href-attribute required for hyperlink')


def _ensure_alt_attribute(tree):
    """
    For every image, check if alt attribute exists missing.
    """
    for tag in tree.child_nodes_of_class(HtmlTag):
        if tag.html_tagname == 'img':
            if not tag.html_attributes.get('alt', None):
                raise CompileException(tag, 'alt-attribute required for image')


def _nest_all_elements(tree):
    """
    Manipulate the parse tree by combining all opening and closing html nodes,
    to reflect the nesting of HTML nodes in the tree.
    So where '<p>' and '</p>' where two independent siblings in the source three,
    they become one now, and everything in between is considered a child of this tag.
    """
    # NOTE: this does not yet combile unknown tags, like <fb:like/>,
    #       maybe it's better to replace this code by a more dynamic approach.
    #       Or we can ignore them, like we do know, because we're not unsure
    #       how to thread them.
    def _create_html_tag_node(name):
        class tag_node(HtmlTagPair):
            html_tagname = ''
            def process_params(self, params):
                # Create new node for the opening html tag
                self._open_tag = HtmlTag(name='html-tag')
                self._open_tag.children = params

                # Copy line/column number information
                self._open_tag.line = self.line
                self._open_tag.column = self.column
                self._open_tag.path = self.path

            @property
            def open_tag(self):
                return self._open_tag

            def register_end_node(self, end_node):
                """ Called by 'nest_block_level_elements' for registering the end node """
                self._end_tag = end_node

            def output(self, handler):
                handler(self._open_tag)
                Token.output(self, handler)
                handler(self._end_tag)

        tag_node.__name__ = name
        tag_node.html_tagname = name
        return tag_node

    # Parse all other HTML tags, (useful for validation, it checks whether
    # every opening tag has a closing match. It doesn't hurt, but also doesn't
    # make much sense to enable this in a production environment.)
    block_elements2 = { }

    for t in __ALL_HTML_TAGS:
        block_elements2[(False, HtmlTag, t)] = ((False, HtmlEndTag, t), _create_html_tag_node(t))

    nest_block_level_elements(tree, block_elements2, (HtmlTag, HtmlEndTag),
            lambda c: (c.is_closing_html_tag, c.__class__, c.html_tagname) )


def _check_no_block_level_html_in_inline_html(tree, options):
    """
    Check whether no block level HTML elements, like <div> are nested inside
    in-line HTML elements, like <span>. Raise CompileException otherwise.
    """
    def check(node, inline_tag=None):
        for c in node.all_children:
            if isinstance(c, HtmlNode) and hasattr(c.__class__, 'html_tagname'):
                if inline_tag and c.__class__.html_tagname in __HTML_BLOCK_LEVEL_ELEMENTS:
                    raise CompileException(c, 'Improper nesting of HTML tags. Block level <%s> node should not appear inside inline <%s> node.' % (c.__class__.html_tagname, inline_tag))

                if c.__class__.html_tagname in __HTML4_INLINE_LEVEL_ELEMENTS:
                    check(c, c.__class__.html_tagname)
                elif c.__class__.html_tagname in __HTML_INLINE_BLOCK_ELEMENTS:
                    # This are block level tags, but can only contain inline level elements,
                    # therefor, consider as in-line from now on.
                    check(c, c.__class__.html_tagname)
                else:
                    check(c, inline_tag)
            elif isinstance(c, DjangoContainer):
                check(c, inline_tag)

    check(tree)


def _check_for_unmatched_closing_html_tags(tree):
    for tag in tree.child_nodes_of_class(HtmlEndTag):
        # NOTE: end tags may still exist for unknown namespaces because the
        #       current implementation does not yet combile unknown start and
        #       end tags.
        if not ':' in tag.html_tagname:
            raise CompileException(tag, 'Unmatched closing </%s> tag' % tag.html_tagname)


# ==================================[  Advanced script/css manipulations ]================================


from django.conf import settings
from django.core.urlresolvers import reverse
from template_preprocessor.core.css_processor import compile_css
from template_preprocessor.core.js_processor import compile_javascript

MEDIA_URL = settings.MEDIA_URL
STATIC_URL = getattr(settings, 'STATIC_URL', '')



def _merge_internal_javascript(tree):
    """
    Group all internal javascript code in the first javascript block.
    NOTE: but don't move scripts which appear in a conditional comment.
    """
    _merge_nodes_of_type(tree, HtmlScriptNode, dont_enter=HtmlConditionalComment)


def _merge_internal_css(tree):
    """
    Group all internal CSS code in the first CSS block.
    """
    _merge_nodes_of_type(tree, HtmlStyleNode, dont_enter=HtmlConditionalComment)


def _pack_external_javascript(tree, context):
    """
    Pack external javascript code. (between {% compress %} and {% endcompress %})
    """
    # For each {% compress %}
    for compress_tag in tree.child_nodes_of_class(DjangoCompressTag):
        # Respect the order of the scripts
        scripts_in_pack = []

        # Find each external <script /> starting with the MEDIA_URL or STATIC_URL
        for script in compress_tag.child_nodes_of_class(HtmlScriptNode):
            if script.is_external:
                source = script.script_source
                if ((MEDIA_URL and source.startswith(MEDIA_URL)) or
                        (STATIC_URL and source.startswith(STATIC_URL)) or
                        is_remote_url(source)):
                    # Add to list
                    scripts_in_pack.append(source)
                    check_external_file_existance(script, source)


        if scripts_in_pack:
            # Remember which media files were linked to this cache,
            # and compile the media files.
            new_script_url = context.compile_js_files(compress_tag, scripts_in_pack)

            # Replace the first external script's url by this one.
            # Remove all other external script files
            first = True
            for script in list(compress_tag.child_nodes_of_class(HtmlScriptNode)):
                # ! Note that we made a list of the child_nodes_of_class iterator,
                #   this is required because we are removing childs from the list here.
                if script.is_external:
                    source = script.script_source
                    if ((MEDIA_URL and source.startswith(MEDIA_URL)) or
                                (STATIC_URL and source.startswith(STATIC_URL)) or
                                is_remote_url(source)):
                        if first:
                            # Replace source
                            script.script_source = new_script_url
                            first = False
                        else:
                            compress_tag.remove_child_nodes([script])


def _pack_external_css(tree, context):
    """
    Pack external CSS code. (between {% compress %} and {% endcompress %})
    Replaces <link type="text/css" rel="stylesheet" media="..." />

    This will bundle all stylesheet in the first link tag. So it's better
    to use multiple {% compress %} tags if you have several values for media.
    """
    def is_external_css_tag(tag):
        return tag.html_tagname == 'link' and \
                tag.get_html_attribute_value_as_string('type') == 'text/css' and \
                tag.get_html_attribute_value_as_string('rel') == 'stylesheet'

    # For each {% compress %}
    for compress_tag in tree.child_nodes_of_class(DjangoCompressTag):
        # Respect the order of the links
        css_in_pack = []

        # Find each external <link type="text/css" /> starting with the MEDIA_URL
        for tag in compress_tag.child_nodes_of_class(HtmlTag):
            if is_external_css_tag(tag):
                source = tag.get_html_attribute_value_as_string('href')
                if ((MEDIA_URL and source.startswith(MEDIA_URL)) or
                        (STATIC_URL and source.startswith(STATIC_URL)) or
                        is_remote_url(source)):
                    # Add to list
                    css_in_pack.append( { 'tag': tag, 'source': source } )
                    check_external_file_existance(tag, source)

        # Group CSS only when they have the same 'media' attribute value
        while css_in_pack:
            # Place first css include in current pack
            first_tag = css_in_pack[0]['tag']
            media = first_tag.get_html_attribute_value_as_string('media')

            css_in_current_pack = [ css_in_pack[0]['source'] ]
            del css_in_pack[0]

            # Following css includes with same media attribute
            while css_in_pack and css_in_pack[0]['tag'].get_html_attribute_value_as_string('media') == media:
                # Remove this tag from the HTML tree (not needed anymore)
                compress_tag.remove_child_nodes([ css_in_pack[0]['tag'] ])

                # Remember source
                css_in_current_pack.append(css_in_pack[0]['source'])
                del css_in_pack[0]

            # Remember which media files were linked to this cache,
            # and compile the media files.
            new_css_url = context.compile_css_files(compress_tag, css_in_current_pack)

            # Update URL for first external CSS node
            first_tag.set_html_attribute('href', new_css_url)


# ==================================[  Debug extensions ]================================

class Trace(Token):
    def __init__(self, original_node):
        Token.__init__(self, line=original_node.line, column=original_node.column, path=original_node.path)
        self.original_node = original_node

class BeforeDjangoTranslatedTrace(Trace): pass
class AfterDjangoTranslatedTrace(Trace): pass

def _insert_debug_trace_nodes(tree, context):
    """
    If we need debug symbols. We have to insert a few traces.
    DjangoTranslated is concidered content
    during the HTML parsing and will disappear.
    We add a trace before and after this nodes. if they still match after
    HTML parsing (which should unless in bad cases like "<p>{%trans "</p>" %}")
    then we can insert debug symbols.
    """
    def insert_trace(cls, before_class, after_class):
        for trans in tree.child_nodes_of_class(cls):
            trans_copy = deepcopy(trans)

            trans.children.insert(0, before_class(trans_copy))
            trans.children.append(after_class(trans_copy))

    insert_trace(DjangoTranslated, BeforeDjangoTranslatedTrace, AfterDjangoTranslatedTrace)
#    insert_trace(DjangoPreprocessedUrl, BeforeDjangoPreprocessedUrlTrace, AfterDjangoPreprocessedUrlTrace)


def _insert_debug_symbols(tree, context):
    """
    Insert useful debugging information into the template.
    """
    import json

    # Find head/body nodes
    body_node = None
    head_node = None

    for tag in tree.child_nodes_of_class(HtmlTagPair):
        if tag.html_tagname == 'body':
            body_node = tag

        if tag.html_tagname == 'head':
            head_node = tag

    # Give every node a debug reference
    tag_references = { }

    def create_references():
        ref_counter = [0]
        for tag in tree.child_nodes_of_class((HtmlTagPair, HtmlTag)):
                tag_references[tag] = ref_counter[0]
                ref_counter[0] += 1
    create_references()

    def apply_tag_refences():
        for tag, ref_counter in tag_references.items():
            if isinstance(tag, HtmlTagPair):
                tag.open_tag.set_html_attribute('d:r', ref_counter)
            else:
                tag.set_html_attribute('d:r', ref_counter)

    # Add template source of this node as an attribute of it's own node.
    # Only for block nodes inside <body/>
    if body_node:
        # The parent node would contain the source of every child node as
        # well, but we do not want to send the same source 100times to the browser.
        # Therefor we add hooks for every tag, and replace it by pointers.
        apply_source_list = [] # (tag, source)

        for tag in [body_node] + list(body_node.child_nodes_of_class((HtmlTagPair, HtmlTag))):
            def create_capture():
                capture_output = []

                def capture(part):
                    if ((isinstance(part, HtmlTagPair) or isinstance(part, HtmlTag)) and part in tag_references):
                            capture_output.append({ 'include': tag_references[part] })

                    elif isinstance(part, basestring):
                        capture_output.append(part)

                    elif part.name in ('django-tag', 'html-tag-attribute-key', 'html-tag-attribute-value',
                                    'html-tag', 'html-end-tag'):
                        capt, o = create_capture()

                        # For {% url %}, be sure to use the original output
                        # method (ignore preprocessing)
                        if isinstance(part, DjangoUrlTag):
                            part.original_output(capt)
                        else:
                            part.output(capt)

                        capture_output.append({ 'type': part.name, 'content': o })
                    else:
                        part.output(capture)
                return capture, capture_output

            capt, o = create_capture()
            tag.output(capt)

            if isinstance(tag, HtmlTag):
                o = [{ 'type': 'html-tag', 'content': o }]

            apply_source_list.append((tag, json.dumps(o)))

        for tag, source in apply_source_list:
            if isinstance(tag, HtmlTagPair):
                tag.open_tag.set_html_attribute('d:s', source)
            else:
                tag.set_html_attribute('d:s', source)

    # For every HTML node, add the following attributes:
    #  d:t="template.html"
    #  d:l="line_number"
    #  d:c="column_number"
    def add_template_info(tag):
        tag.set_html_attribute('d:t', tag.path)
        tag.set_html_attribute('d:l', tag.line)
        tag.set_html_attribute('d:c', tag.column)

    for tag in tree.child_nodes_of_class(HtmlTag):
        add_template_info(tag)

    for tag in tree.child_nodes_of_class(HtmlTagPair):
        add_template_info(tag.open_tag)

    # Surround every {% trans %} block which does not appear into Javascript or Css
    # by <e:tr d:l="..." d:c="..." d:s="original_string..." ...></e:tr>
    # and <e:etr></e:etr>
    # ** Note that we don't place the string itself in a html tag, but instead
    # use two pairs of HTML tags. This is because otherwise, this could
    # destroy the CSS layout. It is up to the Javascript to detect the text
    # node in between and attach eventhandlers to these.
    def insert_trans_tags(tree):
        last_trace = None

        for node in tree.all_children:
            if isinstance(node, BeforeDjangoTranslatedTrace):
                original_node = node.original_node
                node.children = ['<d:tr d:l="%s" d:c="%s" d:t="%s" d:s="%s" d:tr="%s"></d:tr>' %
                                    tuple(map(xml_escape, (
                                        original_node.line,
                                        original_node.column,
                                        original_node.path,
                                        original_node.translation_info.string,
                                        _(original_node.translation_info.string),
                                        )))]

            elif isinstance(node, AfterDjangoTranslatedTrace):
                node.children = ['<d:etr></d:etr>']

            # Recursively find matching traces in
            elif isinstance(node, Token) and not any(isinstance(node, c)
                                    for c in (Trace, HtmlScriptNode, HtmlStyleNode, HtmlTag)):
                insert_trans_tags(node)

    if body_node:
        insert_trans_tags(body_node)

    # Apply tag references as attributes now. (The output could be polluted if we did this earlier)
    apply_tag_refences()


# ==================================[  HTML Parser ]================================


def compile_html_string(html_string, path=''):
    """
    Compile a html string
    """
    # First, create a tree to begin with
    tree = Token(name='root', line=1, column=1, path=path)
    tree.children = [ html_string ]

    # Tokenize
    tokenize(tree, __HTML_STATES, Token)

    from template_preprocessor.core.context import Context
    context = Context(path)
    _process_html_tree(tree, context)

    # Output
    return tree.output_as_string()


def compile_html(tree, context):
    """
    Compile the html in content nodes
    """
    # If we need debug symbols. We have to insert a few traces.
    if context.insert_debug_symbols:
        _insert_debug_trace_nodes(tree, context)

    # Parse HTML code in parse tree (Note that we don't enter DjangoRawTag)
    tokenize(tree, __HTML_STATES, DjangoContent, DjangoContainer)
    _process_html_tree(tree, context)


def _process_html_tree(tree, context):
    options = context.options

    # Add HTML parser extensions
    _add_html_parser_extensions(tree)

    # All kind of HTML validation checks
    if options.validate_html:
        # Methods to execute before nesting everything
        _validate_html_tags(tree)

        # TODO: following three checks are not necsesary in HTML5,
        #       -> create a HTML5 option instead.
        #_ensure_type_in_scripts(tree)
        #_ensure_type_in_css(tree)
        #_ensure_href_in_hyperlinks(tree)

        _validate_html_attributes(tree)
        _ensure_alt_attribute(tree)
        # TODO: check for deprecated HTML tags also

    # Remove empty class="" parameter
    if options.remove_empty_class_attributes:
        _remove_empty_class_attributes(tree)
        apply_method_on_parse_tree(tree, HtmlTag, 'remove_whitespace_in_html_tag')

    _nest_elements(tree)

    # All kind of HTML validation checks, part II
    if options.validate_html:
        # Nest all elements
        _nest_all_elements(tree)

        # Validate nesting.
        if options.disallow_block_level_elements_in_inline_level_elements:
            _check_no_block_level_html_in_inline_html(tree, options)

        _check_for_unmatched_closing_html_tags(tree)

    # Turn comments into content, when they appear inside JS/CSS and remove all other comments
    _turn_comments_to_content_in_js_and_css(tree)
    _remove_comments(tree)

    # Merge all internal javascript code
    if options.merge_internal_javascript:
        _merge_internal_javascript(tree)

    # Merge all internal CSS code
    if options.merge_internal_css:
        _merge_internal_css(tree)

    # Whitespace compression
    # To be dore before merging content nodes.
    if options.whitespace_compression:
        _compress_whitespace(tree)
        _remove_whitespace_around_html_block_level_tags(tree)

    # Merge whitespace and other content.
    # Need to be done before JS or CSS compiling.
    _merge_content_nodes(tree, context)

    # Pack external Javascript
    if options.pack_external_javascript:
        _pack_external_javascript(tree, context)

    # Pack external CSS
    if options.pack_external_css:
        _pack_external_css(tree, context)

    # Compile javascript
    if options.compile_javascript:
        for js_node in tree.child_nodes_of_class(HtmlScriptNode):
            if not js_node.is_external:
                #print 'compiling'
                #print js_node._print()
                compile_javascript(js_node, context)

    # Compile CSS
    if options.compile_css:
        # Document-level CSS
        for css_node in tree.child_nodes_of_class(HtmlStyleNode):
            compile_css(css_node, context)

        # In-line CSS.
            # TODO: this would work, if attribute_value didn't contain the attribute quotes.
        '''
        for attr in tree.child_nodes_of_class(HtmlTagAttribute):
            if attr.attribute_name == 'style':
                att.attribute_value = compile_css(attr.attribute_value)
        '''


    ## TODO: remove emty CSS nodes <style type="text/css"><!-- --></style>

    # Insert DEBUG symbols (for bringing line/column numbers to web client)
    if context.insert_debug_symbols:
        _insert_debug_symbols(tree, context)

########NEW FILE########
__FILENAME__ = js_processor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django template preprocessor.
Author: Jonathan Slenders, City Live
"""


"""
Javascript parser for the template preprocessor.
-----------------------------------------------

Compile the javascript code inside the parse tree
of django template nodes.
"""


# =========================[ Javascript Lexer ]===========================

from template_preprocessor.core.django_processor import DjangoContent, DjangoContainer, DjangoTag
from template_preprocessor.core.lexer import State, StartToken, Push, Record, Shift, StopToken, Pop, CompileException, Token, Error
from template_preprocessor.core.lexer_engine import tokenize
from template_preprocessor.core.html_processor import HtmlContent
import string
from django.utils.translation import ugettext as _
import gettext

__JS_KEYWORDS = 'break|catch|const|continue|debugger|default|delete|do|else|enum|false|finally|for|function|gcase|if|new|null|return|switch|this|throw|true|try|typeof|var|void|while|with'.split('|')


__JS_STATES = {
    'root' : State(
            State.Transition(r'\s*\{\s*', (StartToken('js-scope'), Shift(), )),
            State.Transition(r'\s*\}\s*', (StopToken('js-scope'), Shift(), )),
            State.Transition(r'/\*', (Push('multiline-comment'), Shift(), )),
            State.Transition(r'//', (Push('singleline-comment'), Shift(), )),
            State.Transition(r'"', (Push('double-quoted-string'), StartToken('js-double-quoted-string'), Shift(), )),
            State.Transition(r"'", (Push('single-quoted-string'), StartToken('js-single-quoted-string'), Shift(), )),

            State.Transition(r'(break|catch|const|continue|debugger|default|delete|do|else|enum|false|finally|for|function|case|if|new|null|return|switch|this|throw|true|try|typeof|var|void|while|with)(?![a-zA-Z0-9_$])',
                                    (StartToken('js-keyword'), Record(), Shift(), StopToken())),

                # Whitespaces are recorded in the operator. (They can be removed later on by a simple trim operator.)
            State.Transition(r'\s*(in|instanceof)\b\s*', (StartToken('js-operator'), Record(), Shift(), StopToken(), )), # in-operator
            State.Transition(r'\s*([;,=?:|^&=!<>*%~\.+-])\s*', (StartToken('js-operator'), Record(), Shift(), StopToken(), )),

                # Place ( ... ) and [ ... ] in separate nodes.
                # After closing parentheses/square brakets. Go 'after-varname' (because the context is the same.)
            State.Transition(r'\s*(\()\s*', (StartToken('js-parentheses'), Shift(), )),
            State.Transition(r'\s*(\))\s*', (StopToken('js-parentheses'), Shift(), Push('after-varname'), )),
            State.Transition(r'\s*(\[)\s*', (StartToken('js-square-brackets'), Shift(), )),
            State.Transition(r'\s*(\])\s*', (StopToken('js-square-brackets'), Shift(), Push('after-varname'), )),

                # Varnames and numbers
            State.Transition(r'[a-zA-Z_$][a-zA-Z_$0-9]*', (StartToken('js-varname'), Record(), Shift(), StopToken(), Push('after-varname') )),
            State.Transition(r'[0-9.]+', (StartToken('js-number'), Record(), Shift(), StopToken(), Push('after-varname') )),

                # Required whitespace here (to be replaced with at least a space.)
            State.Transition(r'\s+', (StartToken('js-whitespace'), Record(), Shift(), StopToken() )), # Skip whitespace.

                # A slash in here means we are at the start of a regex block.
            State.Transition(r'\s*/(?![/*])', (StartToken('js-regex-object'), Record(), Shift(), Push('regex-object') )),

            State.Transition(r'.|\s', (Error('Error in parser #1'),)),
            ),
    'double-quoted-string': State(
            State.Transition(r'"', (Pop(), Shift(), StopToken(), )),
                        # Records quotes without their escape characters
            State.Transition(r"\\'", (Record("'"), Shift(), )),
            State.Transition(r'\\"', (Record('"'), Shift(), )),
                        # For other escapes, also save the slash
            State.Transition(r'\\(.|\n|\r)', (Record(), Shift(), )),
            State.Transition(r'[^"\\]+', (Record(), Shift(), )),
            State.Transition(r'.|\s', (Error('Error in parser #2'),)),
            ),
    'single-quoted-string': State(
            State.Transition(r"'", (Pop(), Shift(), StopToken(), )),
            State.Transition(r"\\'", (Record("'"), Shift(), )),
            State.Transition(r'\\"', (Record('"'), Shift(), )),
            State.Transition(r'\\(.|\n|\r)', (Record(), Shift(), )),
            State.Transition(r"[^'\\]+", (Record(), Shift(), )),
            State.Transition(r'.|\s', (Error('Error in parser #3'),)),
            ),

    'multiline-comment': State(
            State.Transition(r'\*/', (Shift(), Pop(), )), # End comment
            State.Transition(r'(\*(?!/)|[^\*])+', (Shift(), )), # star, not followed by slash, or non star characters
            State.Transition(r'(\*(?!/))+', (Shift(), )), # star, not followed by slash
            State.Transition(r'.|\s', (Error('Error in parser #4'),)),
            ),

    'singleline-comment': State(
            State.Transition(r'\n', (Shift(), Pop(), )), # End of line is end of comment
            State.Transition(r'[^\n]+', (Shift(), )),
            State.Transition(r'.|\s', (Error('Error in parser #5'),)),
            ),

    'after-varname': State(
            # A slash after a varname means we have a division operator.
            State.Transition(r'\s*/(?![/*])\s*', (StartToken('js-operator'), Record(), Shift(), StopToken(), )),

            State.Transition(r'/\*', (Push('multiline-comment'), Shift(), )),
            State.Transition(r'//[^\n]*', (Shift(), )), # Single line comment

            # None of the previous matches? Pop and get again in the root state
            State.Transition(r'.|\s', (Pop(), )),
            State.Transition(r'.|\s', (Error('Error in parser #6'),)),
            ),

    'regex-object': State(
            State.Transition(r'\\.', (Record(), Shift() )),
            State.Transition(r'[^/\\]+', (Record(), Shift(), )),
            State.Transition(r'/[a-z]*', (Record(), Shift(), StopToken(), Pop() )), # End of regex object
            State.Transition(r'.|\s', (Error('Error in parser #7'),)),
            ),
   }


# =========================[ I18n ]===========================

from django.utils.translation import get_language
translations = {}

def translate_js(text):
    # Get current language
    lang = get_language()

    # Load dictionary file
    if lang not in translations:
        try:
            translations[lang] = gettext.translation('djangojs', 'locale', [ lang ]).ugettext
        except IOError as e:
            # Fall back to identical translations, when no translation file
            # has been found.
            print e
            translations[lang] = lambda t:t


    return translations[lang](text)


# =========================[ Javascript Parser ]===========================

class JavascriptNode(HtmlContent):
    pass


class JavascriptScope(JavascriptNode):
    """
    Contains:
    Something between { curly brackets } in javascript.
    """
    def init_extension(self):
        self.symbol_table = { }

    def output(self, handler):
        handler(u'{')
        Token.output(self, handler)
        handler(u'}')


class JavascriptParentheses(JavascriptNode):
    """
    Contains:
    Something between ( parentheses ) in javascript.
    """
    def output(self, handler):
        handler(u'(')
        Token.output(self, handler)
        handler(u')')

    @property
    def contains_django_tags(self):
        return any(self.child_nodes_of_class(DjangoTag))


class JavascriptSquareBrackets(JavascriptNode):
    """
    Contains:
    Something between ( parentheses ) in javascript.
    """
    def output(self, handler):
        handler(u'[')
        Token.output(self, handler)
        handler(u']')


class JavascriptWhiteSpace(JavascriptNode):
    pass


class JavascriptOperator(JavascriptNode):
    """
    Javascript operator.
    """
    @property
    def operator(self):
        return self.output_as_string().strip()

    @property
    def is_comma(self):
        return self.operator == ','

    @property
    def is_semicolon(self):
        return self.operator == ';'

    @property
    def is_colon(self):
        return self.operator == ':'


class JavascriptKeyword(JavascriptNode):
    """
    Any javascript keyword: like 'function' or 'var'...
    """
    @property
    def keyword(self):
        return self.output_as_string()


class JavascriptVariable(JavascriptNode):
    """
    Any javascript variable:
    """
    def init_extension(self):
        self.__varname = None
        self.__link_to = None

    def link_to_variable(self, variable):
        if variable != self:
            self.__link_to = variable

    def has_been_linked(self):
        return bool(self.__link_to)

    @property
    def varname(self):
        return self.output_as_string()

    @varname.setter
    def varname(self, varname):
        self.__varname = varname

    def output(self, handler):
        # Yield this node's content, or if the variable name
        # has been changed, use the modified name.
        if self.__varname:
            handler(self.__varname)

        elif self.__link_to:
            self.__link_to.output(handler)

        else:
            Token.output(self, handler)


class JavascriptString(JavascriptNode):
    @property
    def value(self):
        """
        String value. Has still escaped special characters,
        but no escapes for quotes.

        WARNING: Don't call this method when the string contains django tags,
                 the output may be invalid.
        """
        return self.output_as_string(use_original_output_method=True)

    @property
    def contains_django_tags(self):
        return any(self.child_nodes_of_class(DjangoTag))

    def output(self, handler):
        raise Exception("Don't call output on abstract base class")


class JavascriptDoubleQuotedString(JavascriptString):
    def output(self, handler):
        handler(u'"')

        for c in self.children:
            if isinstance(c, basestring):
                handler(c.replace(u'"', ur'\"'))
            else:
                handler(c)

        handler(u'"')


class JavascriptSingleQuotedString(JavascriptString):
    def output(self, handler):
        handler(u"'")

        for c in self.children:
            if isinstance(c, basestring):
                handler(c.replace(u"'", ur"\'"))
            else:
                handler(c)

        handler(u"'")


class JavascriptRegexObject(JavascriptNode):
    pass

class JavascriptNumber(JavascriptNode):
    pass

__JS_EXTENSION_MAPPINGS = {
        'js-scope': JavascriptScope,
        'js-parentheses': JavascriptParentheses,
        'js-square-brackets': JavascriptSquareBrackets,
        'js-varname': JavascriptVariable,
        'js-keyword': JavascriptKeyword,
        'js-whitespace': JavascriptWhiteSpace,
        'js-operator': JavascriptOperator,
        'js-double-quoted-string': JavascriptDoubleQuotedString,
        'js-single-quoted-string': JavascriptSingleQuotedString,
        'js-regex-object': JavascriptRegexObject,
        'js-number': JavascriptNumber,
}


def _add_javascript_parser_extensions(js_node):
    """
    Patch (some) nodes in the parse tree, to get the JS parser functionality.
    """
    for c in js_node.all_children:
        if isinstance(c, Token):
            # Patch the js scope class
            if c.name in __JS_EXTENSION_MAPPINGS:
                c.__class__ = __JS_EXTENSION_MAPPINGS[c.name]
                if hasattr(c, 'init_extension'):
                    c.init_extension()

            _add_javascript_parser_extensions(c)


# =========================[ Javascript processor ]===========================


def _compress_javascript_whitespace(js_node, root_node=True):
    """
    Remove all whitepace in javascript code where possible.
    """
    for c in js_node.all_children:
        if isinstance(c, Token):
            # Whitespcae tokens are required to be kept. e.g. between 'var' and the actual varname.
            if isinstance(c, JavascriptWhiteSpace):
                c.children = [u' ']

            # Around operators, we can delete all whitespace.
            if isinstance(c, JavascriptOperator):
                if c.operator == 'in':
                    c.children = [ ' in ' ] # Don't trim whitespaces around the 'in' operator
                elif c.operator == 'instanceof':
                    c.children = [ ' instanceof ' ] # Don't trim whitespaces around the 'in' operator
                else:
                    c.children = [ c.operator ]

            _compress_javascript_whitespace(c, root_node=False)

    # In the root node, we can remove all leading and trailing whitespace
    if len(js_node.children):
        for i in (0, -1):
            if isinstance(js_node.children[i], JavascriptWhiteSpace):
               js_node.children[i].children = [ u'' ]


def _minify_variable_names(js_node):
    """
    Look for all variables in the javascript code, and
    replace it with a name, as short as possible.
    """
    global_variable_names = []

    def add_var_to_scope(scope, var):
        """
        Add variable "var" to this scope.
        """
        if var.varname in scope.symbol_table:
            # Another variable with the same name was already declared into
            # this scope. Link to each other. They can, and should remain the
            # same name.
            # E.g. as in:    "function(a) { var a; }"
            var.link_to_variable(scope.symbol_table[var.varname])
        else:
            # Save variable into this scope
            scope.symbol_table[var.varname] = var

    # Walk through all the JavascriptScope elements in the tree.
    # Detect variable declaration (variables preceded by a 'function' or 'var'
    # keyword.  Save in the scope that it declares a variable with that name.
    # (do this recursively for every javascript scope.)
    def find_variables(js_node, scope, in_root_node=True):
        next_is_variable = False
        for children in js_node.children_lists:
            for index, c in enumerate(children):
                # Look for 'function' and 'var'
                if isinstance(c, JavascriptKeyword) and c.keyword in ('function', 'var') and not in_root_node:
                    next_is_variable = True

                    # NOTE: the `in_root_node` check is required because "var
                    # varname" should not be renamed, if it's been declared in the
                    # global scope. We only want to rename variables in private
                    # nested scopes.

                    if c.keyword == 'function':
                        find_variables_in_function_parameter_list(children[index:])

                elif isinstance(c, JavascriptVariable) and next_is_variable:
                    add_var_to_scope(scope, c)
                    next_is_variable = False

                elif isinstance(c, JavascriptScope):
                    find_variables(c, c, False)
                    next_is_variable = False

                elif isinstance(c, JavascriptWhiteSpace):
                    pass

                elif isinstance(c, JavascriptParentheses) or isinstance(c, JavascriptSquareBrackets):
                    find_variables(c, scope, in_root_node)
                    next_is_variable = False

                elif isinstance(c, Token):
                    find_variables(c, scope, in_root_node)
                    next_is_variable = False

                else:
                    next_is_variable = False


    # Detect variable declarations in function parameters
    # In the following example are 'varname1' and 'varname2' variable declarations
    # in the scope between the curly brackets.
    # function(varname1, varname2, ...)  {   ... }
    def find_variables_in_function_parameter_list(nodelist):
        # The `nodelist` parameter is the nodelist of the parent parsenode, starting with the 'function' keyword
        assert isinstance(nodelist[0], JavascriptKeyword) and nodelist[0].keyword == 'function'
        i = 1

        while isinstance(nodelist[i], JavascriptWhiteSpace):
            i += 1

        # Skip function name (and optional whitespace after function name)
        if isinstance(nodelist[i], JavascriptVariable):
            i += 1
            while isinstance(nodelist[i], JavascriptWhiteSpace):
                i += 1

        # Enter function parameter list
        if isinstance(nodelist[i], JavascriptParentheses):
            # Remember function parameters
            variables = []
            need_comma = False # comma is the param separator
            for n in nodelist[i].children:
                if isinstance(n, JavascriptWhiteSpace):
                    pass
                elif isinstance(n, JavascriptVariable):
                    variables.append(n)
                    need_comma = True
                elif isinstance(n, JavascriptOperator) and n.is_comma and need_comma:
                    need_comma = False
                else:
                    raise CompileException(n, 'Unexpected token in function parameter list')

            # Skip whitespace after parameter list
            i += 1
            while isinstance(nodelist[i], JavascriptWhiteSpace):
                i += 1

            # Following should be a '{', and bind found variables to scope
            if isinstance(nodelist[i], JavascriptScope):
                for v in variables:
                    add_var_to_scope(nodelist[i], v)
            else:
                raise CompileException(nodelist[i], 'Expected "{" after function definition')
        else:
            raise CompileException(nodelist[i], 'Expected "(" after function keyword')

    find_variables(js_node, js_node)


    # Walk again through the tree. For all the variables: look in the parent
    # scopes where is has been defined. If it's never been defined, add it to
    # the global variable names. (names that we should avoid other variables to
    # be renamed to.) If it has been defined in a parent scope, link it to that
    # variable in that scope.
    def find_free_variables(js_node, parent_scopes):
        skip_next_var = False

        for children in js_node.children_lists:
            for index, c in enumerate(children):
                # Variables after a dot operator shouldn't be renamed.
                if isinstance(c, JavascriptOperator):
                    skip_next_var = (c.operator == '.')

                elif isinstance(c, JavascriptVariable):
                    # Test whether this is not the key of a dictionary,
                    # if so, we shouldn't rename it.
                    try:
                        if index + 1 < len(children):
                            n = children[index+1]
                            if isinstance(n, JavascriptOperator) and n.is_colon:
                                skip_next_var = True

                        # Except for varname in this case:    (1 == 2 ? varname : 3 )
                        if index > 0:
                            n = children[index-1]
                            if isinstance(n, JavascriptOperator) and n.operator == '?':
                                skip_next_var = False
                    except IndexError, e:
                        pass

                    # If we have to link this var (not after a dot, not before a colon)
                    if not skip_next_var:
                        # Link variable to definition symbol table
                        varname = c.varname
                        linked = False
                        for s in parent_scopes:
                            if varname in s.symbol_table:
                                c.link_to_variable(s.symbol_table[varname])
                                linked = True
                                break

                        if not linked:
                            global_variable_names.append(varname)

                elif isinstance(c, JavascriptScope):
                    find_free_variables(c, [c] + parent_scopes)

                elif isinstance(c, Token):
                    find_free_variables(c, parent_scopes)

    find_free_variables(js_node, [ ])

    # Following is a helper method for generating variable names
    def generate_varname(avoid_names):
        avoid_names += __JS_KEYWORDS
        def output(c):
            return u''.join([ string.lowercase[i] for i in c ])

        c = [0] # Numeral representation of character array
        while output(c) in avoid_names:
            c[0] += 1

            # Overflow dectection
            for i in range(0, len(c)):
                if c[i] == 26: # Overflow
                    c[i] = 0
                    try:
                        c[i+1] += 1
                    except IndexError:
                        c.append(0)

        return output(c)

    # Now, rename all the local variables. Start from the outer scope, and move to the
    # inner scopes. Use the first free variable name. Pass each time to the inner scopes,
    # which variables that shouldn't be used. (However, they can be redeclared again, if they
    # are not needed in the inner scope.)
    def rename_variables(js_node, avoid_names):
        if hasattr(js_node, 'symbol_table'):
            for s in js_node.symbol_table:
                new_name = generate_varname(avoid_names)
                avoid_names = avoid_names + [ new_name ]
                js_node.symbol_table[s].varname = new_name

        for c in js_node.all_children:
            if isinstance(c, Token):
                rename_variables(c, avoid_names[:])

    rename_variables(js_node, global_variable_names[:])


def fix_whitespace_bug(js_node):
    """
    Fixes the following case in js code:
        <script type="text/javascript"> if {  {% if test %} ... {% endif %} } </script>
    The lexer above would remove the space between the first '{' and '{%'. This collision
    would make Django think it's the start of a variable.
    """
    # For every scope (starting with '{')
    for scope in js_node.child_nodes_of_class(JavascriptScope):
        # Look if the first child inside this scope also renders to a '{'
        if scope.children and scope.children[0].output_as_string()[0:1] == '{':
            # If so, insert a whitespace token in between.
            space = Token(name='required-whitespace')
            space.children = [' ']
            scope.children.insert(0, space)


def _validate_javascript(js_node):
    """
    Check for missing semicolons in javascript code.

    Note that this is some very fuzzy code. It works, but won't find all the errors,
    It should be replaced sometime by a real javascript parser.
    """
    # Check whether no comma appears at the end of any scope.
    # e.g.    var x = { y: z, } // causes problems in IE6 and IE7
    for scope in js_node.child_nodes_of_class(JavascriptScope):
        if scope.children:
            last_child = scope.children[-1]
            if isinstance(last_child, JavascriptOperator) and last_child.is_comma:
                raise CompileException(last_child,
                            'Please remove colon at the end of Javascript object (not supported by IE6 and IE7)')

    # Check whether no semi-colons are missing. Javascript has optional
    # semicolons and uses an insertion mechanism, but it's very bad to rely on
    # this. If semicolons are missing, we consider the code invalid.  Every
    # statement should end with a semi colon, except: for, function, if,
    # switch, try and while (See JSlint.com)
    for scope in [js_node] + list(js_node.child_nodes_of_class(JavascriptScope)):
        i = [0] # Variable by referece

        def next():
            i[0] += 1

        def has_node():
            return i[0] < len(scope.children)

        def current_node():
            return scope.children[i[0]]

        def get_last_non_whitespace_token():
            if i[0] > 0:
                j = i[0] - 1
                while j > 0 and isinstance(scope.children[j], JavascriptWhiteSpace):
                        j -= 1
                if j:
                    return scope.children[j]

        def found_missing():
            raise CompileException(current_node(), 'Missing semicolon detected. Please check your Javascript code.')

        semi_colon_required = False

        while has_node():
            c = current_node()

            if isinstance(c, JavascriptKeyword) and c.keyword in ('for', 'if', 'switch', 'function', 'try', 'catch', 'while'):
                if (semi_colon_required):
                    found_missing()

                semi_colon_required = False

                if c.keyword == 'function':
                    # One *exception*: When this is an function-assignment, a
                    # semi-colon IS required after this statement.
                    last_token = get_last_non_whitespace_token()
                    if isinstance(last_token, JavascriptOperator) and last_token.operator == '=':
                        semi_colon_required = True

                    # Skip keyword
                    next()

                    # and optional also function name
                    while isinstance(current_node(), JavascriptWhiteSpace):
                        next()
                    if isinstance(current_node(), JavascriptVariable):
                        next()
                else:
                    # Skip keyword
                    next()

                # Skip whitespace
                while isinstance(current_node(), JavascriptWhiteSpace):
                    next()

                # Skip over the  '(...)' parameter list
                # Some blocks, like try {}  don't have parameters.
                if isinstance(current_node(), JavascriptParentheses):
                    next()

                # Skip whitespace
                #  In case of "do { ...} while(1)", this may be the end of the
                #  scope. Therefore we check has_node
                while has_node() and isinstance(current_node(), JavascriptWhiteSpace):
                    next()

                # Skip scope { ... }
                if has_node() and isinstance(current_node(), JavascriptScope):
                    next()

                i[0] -= 1

            elif isinstance(c, JavascriptKeyword) and c.keyword == 'var':
                # The previous token, before the 'var' keyword should be semi-colon
                last_token = get_last_non_whitespace_token()
                if last_token:
                    if isinstance(last_token, JavascriptOperator) and last_token.operator == ';':
                        #  x = y; var ...
                        pass
                    elif isinstance(last_token, JavascriptOperator) and last_token.operator == ':':
                        #  case 'x': var ...
                        pass
                    elif isinstance(last_token, JavascriptScope) or isinstance(last_token, DjangoTag):
                        #  for (...) { ... } var ...
                        pass
                    elif isinstance(last_token, JavascriptParentheses):
                        #  if (...) var ...
                        pass
                    else:
                        found_missing()

            elif isinstance(c, JavascriptOperator):
                # Colons, semicolons, ...
                # No semicolon required before or after
                semi_colon_required = False

            elif isinstance(c, JavascriptParentheses) or isinstance(c, JavascriptSquareBrackets):
                semi_colon_required = True

            elif isinstance(c, JavascriptScope):
                semi_colon_required = False

            elif isinstance(c, JavascriptKeyword) and c.keyword == 'return':
                # Semicolon required before return in:  x=y; return y
                if (semi_colon_required):
                    found_missing()

                # No semicolon required after return in: return y
                semi_colon_required = False

            elif isinstance(c, JavascriptVariable):
                if (semi_colon_required):
                    found_missing()

                semi_colon_required = True

            elif isinstance(c, JavascriptWhiteSpace):
                # Skip whitespace
                pass

            next()


def _process_gettext(js_node, context, validate_only=False):
    """
    Validate whether gettext(...) function in javascript get a string as
    parameter. (Or concatenation of several strings)
    """
    for scope in js_node.child_nodes_of_class((JavascriptScope, JavascriptSquareBrackets, JavascriptParentheses)):
        nodes = scope.children
        for i, c in enumerate(nodes):
            # Is this a gettext method?
            if isinstance(nodes[i], JavascriptVariable) and nodes[i].varname == 'gettext':
                try:
                    gettext = nodes[i]

                    # Skip whitespace
                    i += 1
                    while isinstance(nodes[i], JavascriptWhiteSpace):
                        i += 1

                    # When gettext is followed by '()', this is a call to gettext, otherwise, gettext is used
                    # as a variable.
                    if isinstance(nodes[i], JavascriptParentheses) and not nodes[i].contains_django_tags:
                        parentheses = nodes[i]

                        # Read content of gettext call.
                        body = []
                        for node in parentheses.children:
                            if isinstance(node, JavascriptOperator) and node.operator == '+':
                                # Skip concatenation operator
                                pass
                            elif isinstance(node, JavascriptString):
                                body.append(node.value)
                            else:
                                raise CompileException(node, 'Unexpected token inside gettext(...)')

                        body = u''.join(body)

                        # Remember gettext entry
                        context.remember_gettext(gettext, body)

                        if not validate_only:
                            # Translate content
                            translation = translate_js(body)

                            # Replace gettext(...) call by its translation (in double quotes.)
                            gettext.__class__ = JavascriptDoubleQuotedString
                            gettext.children = [ translation.replace(u'"', ur'\"') ]
                            nodes.remove(parentheses)
                except IndexError, i:
                    # i got out of the nodes array
                    pass


def compile_javascript(js_node, context):
    """
    Compile the javascript nodes to more compact code.
    - Remove comments
    - Rename private variables.
    - Remove whitespace.

    js_node is a node in the parse tree. Note that it may contain
    template tag nodes, and that we should also parse through the block
    nodes.
    """
    # Tokenize and compile
    tokenize(js_node, __JS_STATES, HtmlContent, DjangoContainer)
    _compile(js_node, context)


def compile_javascript_string(js_string, context, path=''):
    """
    Compile JS code (can be used for external javascript files)
    """
    # First, create a tree to begin with
    tree = Token(name='root', line=1, column=1, path=path)
    tree.children = [ js_string ]

    # Tokenize
    tokenize(tree, __JS_STATES, Token)

    # Compile
    _compile(tree, context)

    # Output
    return tree.output_as_string()


def _compile(js_node, context):
    # Javascript parser extensions (required for proper output)
    _add_javascript_parser_extensions(js_node)

    # Validate javascript
    _validate_javascript(js_node)

    # Remove meaningless whitespace in javascript code.
    _compress_javascript_whitespace(js_node)

    # Preprocess gettext
    _process_gettext(js_node, context)

    # Minify variable names
    _minify_variable_names(js_node)

    fix_whitespace_bug(js_node)



########NEW FILE########
__FILENAME__ = lexer
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django template preprocessor.
Author: Jonathan Slenders, City Live
"""

"""
Tokenizer for a template preprocessor.
------------------------------------------------------------------
This file contains only the classes used for defining the grammar of each
language. The actual engine can be found in lexer_engine.py

The Token class is the base class for any node in the parse tree.
"""

__author__ = 'Jonathan Slenders, City Live'
__all__ = ('Token', 'State', 'Push', 'Pop', 'Record', 'Shift', 'StartToken', 'StopToken', 'Error', )

import re
from itertools import chain


class CompileException(Exception):
    def __init__(self, *args):
        """
        Call:
        CompileException(message)
        CompileException(token, message)
        CompileException(line, column, path, message)
        """
        if isinstance(args[0], basestring):
            self.line, self.column, self.path, self.message = 0, 0, '', args[0]

        elif isinstance(args[0], Token):
            if args[0]:
                # TODO: eleminate call like CompileException(None, message)
                self.path = args[0].path
                self.line = args[0].line
                self.column = args[0].column
                self.message = args[1]
            else:
                self.path = self.line = self.column = '?'
        else:
            self.line, self.column, self.path, self.message = args


        Exception.__init__(self,
            u'In: %s\nLine %s, column %s: %s' % (self.path, self.line, self.column, self.message))


class Token(object):
    """
    Token in the parse tree
    """
    def __init__(self, name='unknown-node', line=0, column=0, path=''):
        self.name = name
        self.line = line
        self.path = path
        self.column = column
        self.children = [] # nest_block_level_elements can also create a .children2, .children3 ...
        self.params = [] # 2nd child list, used by the parser

    def append(self, child):
        self.children.append(child)

    @property
    def children_lists(self):
        """
        Yield all the children child lists.
        e.g. "{% if %} ... {% else %} ... {% endif %}" has two child lists.
        """
        yield self.children

        try:
            yield self.children2
            yield self.children3
            yield self.children4
        except AttributeError:
            pass

        # Alternatively, we could write the following as well, but
        # the above is slightly faster.

        # i = 2
        # while hasattr(self, 'children%i' % i):
        #     yield getattr(self, 'children%i' % i)
        #     i += 1

    @property
    def all_children(self):
        return chain(* self.children_lists)

    def get_childnodes_with_name(self, name):
        for children in self.children_lists:
            for c in children:
                if c.name == name:
                    yield c

    def _print(self, prefix=''):
        """
        For debugging: print the output to a unix terminal for a colored parse tree.
        """
        result = []

        result.append('\033[34m')
        result.append ("%s(%s,%s) %s {\n" % (self.name, str(self.line), str(self.column), self.__class__.__name__))
        result.append('\033[0m')

        children_result = []
        for t in self.children:
            if isinstance(t, basestring):
                children_result.append('str(%s)\n' % t)
            else:
                children_result.append("%s\n" % t._print())
        result.append(''.join(['\t%s\n' % s for s in ''.join(children_result).split('\n')]))

        result.append('\033[34m')
        result.append("}\n")
        result.append('\033[0m')
        return ''.join(result)

    def output(self, handler):
        """
        Method for generating the output.
        This calls the output handler for every child of this node.
        To be overriden in the parse tree. (an override can output additional information.)
        """
        for children in self.children_lists:
            map(handler, children)

    def _output(self, handler):
        """
        Original output method.
        """
        for children in self.children_lists:
            map(handler, children)

    def output_as_string(self, use_original_output_method=False):
        """
        Return a unicode string of this node
        """
        o = []
        if use_original_output_method:
            def capture(s):
                if isinstance(s, basestring):
                    o.append(s)
                else:
                    s._output(capture)
            self._output(capture)
        else:
            def capture(s):
                if isinstance(s, basestring):
                    o.append(s)
                else:
                    s.output(capture)
            self.output(capture)

        return u''.join(o)

    def output_params(self, handler):
        map(handler, self.params)

    def __unicode__(self):
        """ Just for debugging the parser """
        return self._print()

    # **** [ Token manipulation ] ****

    def child_nodes_of_class(self, classes, dont_enter=None):
        """
        Iterate through all nodes of this class type.
        `classes` and `dont_enter` should be a single Class, or a tuple of classes.
        (I think it's a depth-first implementation.)
        `dont_enter` parameter can receive a list of node classes to
        be excluded for searching.
        """
                    # TODO: this is a hard limit to 3 child nodes, (better for performance but not optimal)
        for c in chain(self.children, getattr(self, 'children2', []), getattr(self, 'children3', [])):
            if isinstance(c, classes):
                yield c

            if isinstance(c, Token):
                if not dont_enter:
                    for i in c.child_nodes_of_class(classes):
                        yield i

                elif not isinstance(c, dont_enter):
                    for i in c.child_nodes_of_class(classes, dont_enter):
                        yield i

    def has_child_nodes_of_class(self, classes, dont_enter=None):
        """
        Return True when at least one childnode of this class is found.
        """
        iterator = self.child_nodes_of_class(classes, dont_enter)
        try:
            iterator.next()
            return True
        except StopIteration:
            return False


    def remove_child_nodes_of_class(self, class_):
        """
        Iterate recursively through the parse tree,
        and remove nodes of this class.
        """
        for children in self.children_lists:
            for c in children:
                if isinstance(c, class_):
                    children.remove(c)

                elif isinstance(c, Token):
                    c.remove_child_nodes_of_class(class_)

    def remove_child_nodes(self, nodes):
        """
        Removed these nodes from the tree.
        """
        for children in self.children_lists:
            # Remove nodes from this children
            for c in nodes:
                if c in children:
                    children.remove(c)

            # Recursively remove children from child tokens.
            for c in children:
                if isinstance(c, Token):
                    c.remove_child_nodes(nodes)

    def collapse_nodes_of_class(self, class_):
        """
        Replace nodes of this class by their children.
        """
        for children in self.children_lists:
            new_nodes = []
            for c in children:
                if isinstance(c, Token):
                    c.collapse_nodes_of_class(class_)

                if isinstance(c, class_):
                    new_nodes += c.children
                else:
                    new_nodes.append(c)

            children.__init__(new_nodes)


class State(object):
    """
    Parse state. Contains a list of regex we my find in the current
    context. Each parse state consists of an ordered list of transitions.
    """
    class Transition(object):
        def __init__(self, regex_match, action_list):
            """
            Parse state transition. Consits of a regex
            and an action list that should be executed whet
            this regex has been found.
            """
            self.regex_match = regex_match
            self.compiled_regex = re.compile(regex_match)
            self.action_list = action_list

    def __init__(self, *transitions):
        self.__transitions = transitions

    def transitions(self):
        """ Transition iterator """
        for t in self.__transitions:
            yield t.compiled_regex, t.action_list


###
# Following classes are 'action' classes for the tokenizer
# Used for defining the grammar of a language
###

class ParseAction(object):
    """ Abstract base class, does nothing. """
    pass

class Push(ParseAction):
    """
    Push this state to the state tack. Parsing
    shall continue by examining this state.
    """
    def __init__(self, state_name):
        self.state_name = state_name

class Pop(ParseAction):
    """
    Pop from the state stack.
    """
    pass

class Record(ParseAction):
    """
    Record the matched text into the current
    token.
    """
    def __init__(self, value=None):
        self.value = value

class Shift(ParseAction):
    """
    Shift the parse pointer after the match.
    """
    pass

class StartToken(ParseAction):
    """
    Push this token to the parse stack. New
    tokens or records shall be inserted as
    child of this one.
    """
    def __init__(self, state_name):
        self.state_name = state_name

class StopToken(ParseAction):
    """
    Pop the current token from the parse stack.
    """
    def __init__(self, state_name=None):
        self.state_name = state_name

class Error(ParseAction):
    """
    Raises an error. We don't expect this match here.
    """
    def __init__(self, message):
        self.message = message


########NEW FILE########
__FILENAME__ = lexer_engine
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django template preprocessor.
Author: Jonathan Slenders, City Live
"""


"""
Tokenizer for a template preprocessor.
------------------------------------------------------------------

This tokenizer is designed to parse a language inside a parse tree.
- It is used to parse django templates. (starting with a parse tree with only a single
  root node containg the full template code as a single string.)
- The parser is called from the html_processor, to turn the django tree into a
  html tree by parsing HTML nodes.
- The parser is called from the css_processor and the js_processor, to parse
  the css and js nodes in the HTML tree.

So, the result of this tokenizer is a tree, but it can contain tokens of
different languages.


        By the way: DON'T CHANGE ANYTHING IN THIS FILE, unless you're absolutely sure.
"""

from template_preprocessor.core.lexer import State, StartToken, Push, Record, Shift, StopToken, Pop, CompileException, Token, Error

import codecs

# Pseudo code:
#
# for every childlist in tree:
#    - emtpy list.
#    - tokenize list
#    - add new tokens to this list


def tokenize(tree, states, classes_to_replace_by_parsed_content, classes_to_enter=None):
    """
    Tokenize javascript or css code within the
    django parse tree.
    `classes_to_replace_by_parsed_content` should be a single class or tuple of classes
    `classes_to_enter` should be a single class or tuple of classes.
    """
    classes_to_enter = classes_to_enter or []

    def _tokenize(node, nodelist, state_stack, token_stack, root=False):
        """
        node:        The current parse node that we are lexing. We are lexing
                     tokens in a parse tree of another language, and this node
                     is the parse node of the other language where we are now.

        state_stack: The current state in our lexing 'grammar'

        token_stack: The output token to where we are moving nodes right now.
                     This is a stack of childnodes lists

        root:        True when this is the main call.
        """
        # Copy input nodes to new list, and clear nodelist
        input_nodes = nodelist[:]
        nodelist.__init__()

        # Position   TODO: this information is only right for the first children-list, not
        #                  for the others!!!
        line =  node.line
        column = node.column
        path = node.path

        # As long as we have input nodes
        while input_nodes:
            # Pop input node
            current_input_node = input_nodes[0]
            del input_nodes[0]

            if isinstance(current_input_node, basestring):
                # Tokenize content
                string = current_input_node

                # When the string starts with a BOM_UTF8 character, remove it.
                string = string.lstrip(unicode(codecs.BOM_UTF8, 'utf8'))

                # We want the regex to be able to match as much as possible,
                # So, if several basestring nodes, are following each other,
                # concatenate as one.
                while input_nodes and isinstance(input_nodes[0], basestring):
                    # Pop another input node
                    string += input_nodes[0]
                    del input_nodes[0]

                # Parse position
                position = 0

                while position < len(string):
                    for compiled_regex, action_list in states[ state_stack[-1] ].transitions():
                        match = compiled_regex.match(string[position:])

                        #print state_stack, string[position:position+10]

                        if match:
                            (start, count) = match.span()

                            # Read content
                            content = string[position : position + count]

                            # Execute actions for this match
                            for action in action_list:
                                if isinstance(action, Record):
                                    if action.value:
                                        token_stack[-1].append(action.value)
                                    else:
                                        token_stack[-1].append(content)

                                elif isinstance(action, Shift):
                                    position += count
                                    count = 0

                                    # Update row/column
                                    f = content.find('\n')
                                    while f >= 0:
                                        line += 1
                                        column = 1
                                        content = content[f+1:]
                                        f = content.find('\n')
                                    column += len(content)

                                elif isinstance(action, Push):
                                    state_stack.append(action.state_name)

                                elif isinstance(action, Pop):
                                    del state_stack[-1]

                                elif isinstance(action, StartToken):
                                    token = Token(action.state_name, line, column, path)
                                    token_stack[-1].append(token)
                                    token_stack.append(token.children)

                                elif isinstance(action, StopToken):
# TODO: check following constraint!
# token_stack[-1] is a childnode list now instead of a node. it does no longer
# have an attribute name!

#                                    if action.state_name and token_stack[-1].name != action.state_name:
#                                        raise CompileException(line, column, path, 'Token mismatch')

                                    del token_stack[-1]

                                elif isinstance(action, Error):
                                    raise CompileException(line, column, path, action.message +
                                                "; near: '%s'" % string[max(0,position-20):position+20])

                            break # Out of for

            # Not a DjangoContent node? Copy in current position.
            else:
                # Recursively tokenize in this node (continue with states, token will be replaced by parsed content)
                if isinstance(current_input_node, classes_to_replace_by_parsed_content):
                    for l in current_input_node.children_lists:
                        _tokenize(current_input_node, l, state_stack, token_stack)

                # Recursively tokenize in this node (start parsing again in nested node)
                elif isinstance(current_input_node, classes_to_enter):
                    for l in current_input_node.children_lists:
                        _tokenize(current_input_node, l, state_stack, [ l ], True)
                    token_stack[-1].append(current_input_node)

                # Any other class, copy in current token
                else:
                    token_stack[-1].append(current_input_node)

        if root and token_stack != [ nodelist ]:
            top = token_stack[-1]
            raise CompileException(top.line, top.column, top.path, '%s not terminated' % top.name)

    _tokenize(tree, tree.children, ['root'], [ tree.children ], True)


def nest_block_level_elements(tree, mappings, _classes=Token, check=None):
    """
    Replace consecutive nodes like  (BeginBlock, Content, Endblock) by
    a recursive structure:  (Block with nested Content).

    Or also supported:  (BeginBlock, Content, ElseBlock Content EndBlock)
        After execution, the first content will be found in node.children,
        The second in node.children2

    `_classes` should be a single Class or tuple of classes.
    """
    check = check or (lambda c: c.name)

    def get_moving_to_list():
        """
        Normally, we are moving childnodes to the .children
        list, but when we have several child_node_lists because
        of the existance of 'else'-nodes, we may move to another
        list. This method returns the list instace we are currently
        moving to.
        """
        node = moving_to_node[-1]
        index = str(moving_to_index[-1] + 1) if moving_to_index[-1] else ''

        if not hasattr(node, 'children%s' % index):
            setattr(node, 'children%s' % index, [])

        return getattr(node, 'children%s' % index)

    for nodelist in tree.children_lists:
        # Push/Pop stacks
        moving_to_node = []
        moving_to_index = []
        tags_stack = [] # Stack of lists (top of the list contains a list of
                    # check_values for possible {% else... %} or {% end... %}-nodes.

        for c in nodelist[:]:
            # The 'tags' are only concidered tags if they are of one of these classes
            is_given_class = isinstance(c, _classes)

            # And if it's a tag, this check_value is the once which could
            # match a value of the mapping.
            check_value = check(c) if is_given_class else None

            # Found the start of a block-level tag
            if is_given_class and check_value in mappings:
                m = mappings[check(c)]
                (end, class_) = (m[:-1], m[-1])

                # Patch class
                c.__class__ = class_

                # Are we moving nodes
                if moving_to_node:
                    get_moving_to_list().append(c)
                    nodelist.remove(c)

                # Start moving all following nodes as a child node of this one
                moving_to_node.append(c)
                moving_to_index.append(0)
                tags_stack.append(end)

                # This node will create a side-tree containing the 'parameters'.
                c.process_params(c.children[:])
                c.children = []

            # End of this block-level tag
            elif moving_to_node and is_given_class and check_value == tags_stack[-1][-1]:
                nodelist.remove(c)

                # Some node classes like to receive a notification of the matching
                # end node.
                if hasattr(moving_to_node[-1], 'register_end_node'):
                    moving_to_node[-1].register_end_node(c)

                # Block-level tag created, apply recursively
                # No, we shouldn't!!! Child nodes of this tag are already processed
                #nest_block_level_elements(moving_to_node[-1])

                # Continue
                del moving_to_node[-1]
                del moving_to_index[-1]
                del tags_stack[-1]

            # Any 'else'-node within
            elif moving_to_node and is_given_class and check_value in tags_stack[-1][:-1]:
                nodelist.remove(c)

                # Move the tags list
                position = tags_stack[-1].index(check_value)
                tags_stack[-1] = tags_stack[-1][position+1:]

                # Children attribute ++
                moving_to_index[-1] += position+1

            # Are we moving nodes
            elif moving_to_node:
                get_moving_to_list().append(c)
                nodelist.remove(c)

                # Apply recursively
                nest_block_level_elements(c, mappings, _classes, check)

            elif isinstance(c, Token):
                # Apply recursively
                nest_block_level_elements(c, mappings, _classes, check)

    if moving_to_node:
        raise CompileException(moving_to_node[-1].line, moving_to_node[-1].column, moving_to_node[-1].path, '%s tag not terminated' % moving_to_node[-1].__class__.__name__)


########NEW FILE########
__FILENAME__ = preprocessable_template_tags

from django.conf import settings
from django.utils.translation import ugettext as _

import re

__doc__ = """
Extensions to the preprocessor, if certain tags are possible to be preprocessed,
you can add these in your application as follows:

from template_preprocessor import preproces_tag

@preprocess_tag
def now(*args):
    if len(args) == 2 and args[1] in (u'"Y"', u"'Y'"):
        import datetime
        return unicode(datetime.datetime.now().year)
    else:
        raise NotPreprocessable()

"""


class NotPreprocessable(Exception):
    """
    Raise this exception when a template tag which has been registered as being
    preprocessable, can not be preprocessed with the current arguments.
    """
    pass


# === Discover preprocessable tags

__preprocessabel_tags = { }

def preprocess_tag(func_or_name):
    """
    > @preprocess_tag
    > def my_template_tag(*args):
    >     return '<p>.....</p>'

    > @preprocess_tag('my_template_tag')
    > def func(*args):
    >     return '<p>.....</p>'
    """
    if isinstance(func_or_name, basestring):
        def decorator(func):
            __preprocessabel_tags[func_or_name] = func
            return func
        return decorator
    else:
        __preprocessabel_tags[func_or_name.__name__] = func_or_name
        return func_or_name


def discover_template_tags():
    for a in settings.INSTALLED_APPS:
        try:
            __import__('%s.preprocessable_template_tags' % a)
        except ImportError, e:
            pass



_discovered = False

def get_preprocessable_tags():
    global _discovered

    if not _discovered:
        discover_template_tags()
        _discovered = True

    return __preprocessabel_tags



# ==== Build-in preprocessable tags ====


@preprocess_tag('google_analytics')
def _google_analytics(*args):
    if len(args) != 1: raise NotPreprocessable()

    return re.compile('\s\s+').sub(' ',  '''
    <script type="text/javascript">
        var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
        document.write(unescape("%%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%%3E%%3C/script%%3E"));
    </script>
    <script type="text/javascript">
        try {
            var pageTracker = _gat._getTracker("%s");
            pageTracker._trackPageview();
        } catch(err) {}
    </script>
    ''' % getattr(settings, 'URCHIN_ID', None))


@preprocess_tag('now')
def _now(*args):
    """
    The output of the following template tag will probably not change between
    reboots of the django server.
    {% now "Y" %}
    """
    if len(args) == 2 and args[1] in (u'"Y"', u"'Y'"):
        import datetime
        return unicode(datetime.datetime.now().year)
    else:
        raise NotPreprocessable()


########NEW FILE########
__FILENAME__ = utils

import os
import codecs
import urllib2
from hashlib import md5

from django.conf import settings
from django.utils import translation
from template_preprocessor.core.lexer import CompileException

MEDIA_ROOT = getattr(settings, 'MEDIA_ROOT', '')
MEDIA_URL = getattr(settings, 'MEDIA_URL', '')
MEDIA_CACHE_DIR = settings.MEDIA_CACHE_DIR
MEDIA_CACHE_URL = settings.MEDIA_CACHE_URL
STATIC_ROOT = getattr(settings, 'STATIC_ROOT', '')
STATIC_URL = getattr(settings, 'STATIC_URL', None)


try:
    from django.contrib.staticfiles.finders import find
except ImportError:
    # fall back to django-staticfiles
    try:
        from staticfiles.finders import find
    except ImportError:
        def find(url):
            return os.path.join(STATIC_ROOT, url)


# =======[ Utilities for media/static files ]======

def is_remote_url(url):
    return any(url.startswith(prefix) for prefix in ('http://', 'https://'))


def get_media_source_from_url(url):
    """
    For a given media/static URL, return the matching full path in the media/static directory
    """
    # Media
    if MEDIA_URL and url.startswith(MEDIA_URL):
        return os.path.join(MEDIA_ROOT, url[len(MEDIA_URL):].lstrip('/'))

    elif MEDIA_URL and url.startswith('/media/'):
        return os.path.join(MEDIA_ROOT, url[len('/media/'):].lstrip('/'))

    # Static
    elif STATIC_URL and url.startswith(STATIC_URL):
        return find(url[len(STATIC_URL):].lstrip('/'))

    elif STATIC_URL and url.startswith('/static/'):
        return find(url[len('/static/'):].lstrip('/'))

    # External URLs
    elif is_remote_url(url):
        return url

    else:
        raise Exception('Invalid media/static url given: %s' % url)


def read_media(url):
    if is_remote_url(url):
        try:
            f = urllib2.urlopen(url)

            if f.code == 200:
                return f.read().decode('utf-8')
            else:
                raise CompileException(None, 'External media not found: %s' % url)

        except urllib2.URLError, e:
            raise CompileException(None, 'Opening %s failed: %s' % (url, e.message))
    else:
        path = get_media_source_from_url(url)
        if path:
            return codecs.open(path, 'r', 'utf-8').read()
        else:
            raise CompileException(None, 'External media file %s does not exist' % url)


def simplify_media_url(url):
    """
    For a given media/static URL, replace the settings.MEDIA/STATIC_URL prefix
    by simply /media or /static.
    """
    if MEDIA_URL and url.startswith(MEDIA_URL):
        return '/media/' + url[len(MEDIA_URL):]
    elif STATIC_URL and url.startswith(STATIC_URL):
        return '/static/' + url[len(STATIC_URL):]
    else:
        return url


def real_url(url):
    if url.startswith('/static/'):
        return STATIC_URL + url[len('/static/'):]

    elif url.startswith('/media/'):
        return MEDIA_URL + url[len('/media/'):]

    else:
        return url


def check_external_file_existance(node, url):
    """
    Check whether we have a matching file in our media/static directory for this URL.
    Raise exception if we don't.
    """
    exception = CompileException(node, 'Missing external media file (%s)' % url)

    if is_remote_url(url):
        if urllib2.urlopen(url).code != 200:
            raise exception
    else:
        complete_path = get_media_source_from_url(url)

        if not complete_path or not os.path.exists(complete_path):
            if MEDIA_URL and url.startswith(MEDIA_URL):
                raise exception

            elif STATIC_URL and url.startswith(STATIC_URL):
                raise exception


def _create_directory_if_not_exists(directory):
    """
    Create a directory (for cache, ...) if this one does not yet exist.
    """
    if not os.path.exists(directory):
        #os.mkdir(directory)
        os.makedirs(directory)


def need_to_be_recompiled(source_files, output_file):
    """
    Returns True when one of the source files in newer then the output_file
    """
    return (
        # Output does not exists
        not os.path.exists(output_file) or

        # Any local input file has been changed after generation of the output file
        # (We don't check the modification date of external javascript files.)
        any(not is_remote_url(s) and os.path.getmtime(s) > os.path.getmtime(output_file) for s in map(get_media_source_from_url, source_files))
    )


def create_media_output_path(media_files, extension, lang):
    assert extension in ('js', 'css')

    name = '%s.%s' % (os.path.join(lang, md5(''.join(media_files)).hexdigest()), extension)
    return os.path.join(MEDIA_CACHE_DIR, name)


# =======[ Compiler for external media/static files ]======


def compile_external_javascript_files(media_files, context, compress_tag=None):
    """
    Make sure that these external javascripts are compiled. (don't compile when not required.)
    Return output path.
    """
    from template_preprocessor.core.js_processor import compile_javascript_string

    # Create a hash for this scriptnames
    name = os.path.join(translation.get_language(), md5(''.join(media_files)).hexdigest()) + '.js'
    compiled_path = os.path.join(MEDIA_CACHE_DIR, name)

    if need_to_be_recompiled(media_files, compiled_path):
        # Trigger callback, used for printing "compiling media..." feedback
        context.compile_media_callback(compress_tag, map(simplify_media_url, media_files))
        progress = [0] # by reference

        def compile_part(media_file):
            progress[0] += 1
            media_content = read_media(media_file)

            context.compile_media_progress_callback(compress_tag, simplify_media_url(media_file),
                        progress[0], len(media_files), len(media_content))

            if not is_remote_url(media_file) or context.options.compile_remote_javascript:
                return compile_javascript_string(media_content, context, media_file)
            else:
                return media_content

        # Concatenate and compile all scripts
        source = u'\n'.join(compile_part(p) for p in media_files)

        # Store in media dir
        _create_directory_if_not_exists(os.path.split(compiled_path)[0])
        codecs.open(compiled_path, 'w', 'utf-8').write(source)

        # Store meta information
        open(compiled_path + '-c-meta', 'w').write('\n'.join(map(simplify_media_url, media_files)))

    return os.path.join(MEDIA_CACHE_URL, name)


def compile_external_css_files(media_files, context, compress_tag=None):
    """
    Make sure that these external css are compiled. (don't compile when not required.)
    Return output path.
    """
    from template_preprocessor.core.css_processor import compile_css_string

    # Create a hash for this scriptnames
    name = os.path.join(translation.get_language(), md5(''.join(media_files)).hexdigest()) + '.css'
    compiled_path = os.path.join(MEDIA_CACHE_DIR, name)

    if need_to_be_recompiled(media_files, compiled_path):
        # Trigger callback, used for printing "compiling media..." feedback
        context.compile_media_callback(compress_tag, map(simplify_media_url, media_files))
        progress = [0] # by reference

        def compile_part(media_file):
            progress[0] += 1
            media_content = read_media(media_file)

            context.compile_media_progress_callback(compress_tag, simplify_media_url(media_file),
                        progress[0], len(media_files), len(media_content))

            if not is_remote_url(media_file) or context.options.compile_remote_css:
                return compile_css_string(media_content, context, get_media_source_from_url(media_file), media_file)
            else:
                return media_content

        # concatenate and compile all css files
        source = u'\n'.join(compile_part(p) for p in media_files)

        # Store in media dir
        _create_directory_if_not_exists(os.path.split(compiled_path)[0])
        codecs.open(compiled_path, 'w', 'utf-8').write(source)

        # Store meta information
        open(compiled_path + '-c-meta', 'w').write('\n'.join(map(simplify_media_url, media_files)))

    return os.path.join(MEDIA_CACHE_URL, name)

########NEW FILE########
__FILENAME__ = compile_templates
"""
Author: Jonathan Slenders, City Live
"""
import os
import codecs
from optparse import make_option
import termcolor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist

from template_preprocessor.core import compile
from template_preprocessor.core.lexer import CompileException

from template_preprocessor.utils import language, template_iterator, load_template_source, get_template_path
from template_preprocessor.utils import get_options_for_path, execute_precompile_command
from template_preprocessor.core.utils import need_to_be_recompiled, create_media_output_path
from template_preprocessor.core.context import Context


class Command(BaseCommand):
    help = "Preprocess all the templates form all known applications."
    option_list = BaseCommand.option_list + (
        make_option('--language', action='append', dest='languages', help='Give the languages'),
        make_option('--all', action='store_true', dest='all_templates', help='Compile all templates (instead of only the changed)'),
        make_option('--single-template', action='append', dest='single_template', help='Compile only this template'),
        make_option('--boring', action='store_true', dest='boring', help='No colors in output'),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
                        help='Tell Django to NOT prompt the user for input of any kind.'),
        make_option('--insert-debug-symbols', action='store_true', dest='insert_debug_symbols', default=False,
                        help='Insert debug symbols in template output')
    )


    def __init__(self, *args, **kwargs):
        class NiceContext(Context):
            """
            Same as the real context class, but override some methods in order to gain
            nice colored output.
            """
            def __init__(s, *args, **kwargs):
                kwargs['insert_debug_symbols'] = self.insert_debug_symbols
                Context.__init__(s, *args, **kwargs)

            def compile_media_callback(s, compress_tag, media_files):
                """
                When the compiler notifies us that compiling of this file begins.
                """
                if compress_tag:
                    print self.colored('Compiling media files from', 'yellow'),
                    print self.colored(' "%s" ' % compress_tag.path, 'green'),
                    print self.colored(' (line %s, column %s)" ' % (compress_tag.line, compress_tag.column), 'yellow')
                else:
                    print self.colored('Compiling media files', 'yellow')

                for m in media_files:
                    print self.colored('   * %s' % m, 'green')

            def compile_media_progress_callback(s, compress_tag, media_file, current, total, file_size):
                """
                Print progress of compiling media files.
                """
                print self.colored('       (%s / %s):' % (current, total), 'yellow'),
                print self.colored(' %s (%s bytes)' % (media_file, file_size), 'green')
        self.NiceContext = NiceContext

        BaseCommand.__init__(self, *args, **kwargs)


    def print_error(self, text):
        self._errors.append(text)
        print self.colored(text, 'white', 'on_red').encode('utf-8')


    def colored(self, text, *args, **kwargs):
        if self.boring:
            return text
        else:
            return termcolor.colored(text, *args, **kwargs)



    def handle(self, *args, **options):
        self.real_handle(*args, **options)
        return


        import os, sys
        import StringIO
        import hotshot, hotshot.stats
        f = '/tmp/django-profile'
        prof = hotshot.Profile(f)
        prof.runcall(self.real_handle, *args, **options)

        prof.close()
        stats = hotshot.stats.load(f)
        #stats.strip_dirs()
        stats.sort_stats('time')
        stats.print_stats(1.0)
        os.remove(f)





    def real_handle(self, *args, **options):
        all_templates = options['all_templates']
        single_template = options['single_template']
        interactive = options['interactive']
        self.insert_debug_symbols = options['insert_debug_symbols']

        # Default verbosity
        self.verbosity = int(options.get('verbosity', 1))

        # Colors?
        self.boring = bool(options.get('boring'))

        # All languages by default
        languages = [l[0] for l in settings.LANGUAGES]
        if options['languages'] is None:
            options['languages'] = languages


        self._errors = []
        if languages.sort() != options['languages'].sort():
            print self.colored('Warning: all template languages are deleted while we won\'t generate them again.',
                                    'white', 'on_red')

        # Delete previously compiled templates and media files
        # (This is to be sure that no template loaders were configured to
        # load files from this cache.)
        if all_templates:
            if not interactive or raw_input('\nDelete all files in template cache directory: %s? [y/N] ' %
                                settings.TEMPLATE_CACHE_DIR).lower() in ('y', 'yes'):
                for root, dirs, files in os.walk(settings.TEMPLATE_CACHE_DIR):
                    for f in files:
                        if not f[0] == '.': # Skip hidden files
                            path = os.path.join(root, f)
                            if self.verbosity >= 1:
                                print ('Deleting old template: %s' % path)
                            os.remove(path)

            if not interactive or raw_input('\nDelete all files in media cache directory %s? [y/N] ' %
                                settings.MEDIA_CACHE_DIR).lower() in ('y', 'yes'):
                for root, dirs, files in os.walk(settings.MEDIA_CACHE_DIR):
                    for f in files:
                        if not f[0] == '.': # Skip hidden files
                            path = os.path.join(root, f)
                            if self.verbosity >= 1:
                                print ('Deleting old media file: %s' % path)
                            os.remove(path)

        # Build compile queue
        queue = self._build_compile_queue(options['languages'], all_templates, single_template)

        # Precompile command
        execute_precompile_command()

        # Compile queue
        for i in range(0, len(queue)):
            lang = queue[i][0]
            with language(lang):
                if self.verbosity >= 2:
                    print self.colored('%i / %i |' % (i+1, len(queue)), 'yellow'),
                    print self.colored('(%s)' % lang, 'yellow'),
                    print self.colored(queue[i][1], 'green')

                self._compile_template(*queue[i])

        # Show all errors once again.
        print u'\n*** %i Files processed, %i compile errors ***' % (len(queue), len(self._errors))

        # Build media compile queue
        media_queue = self._build_compile_media_queue(options['languages'])

        # Compile media queue
        self._errors = []
        for i in range(0, len(media_queue)):
            lang = media_queue[i][0]
            with language(lang):
                if self.verbosity >= 2:
                    print self.colored('%i / %i |' % (i+1, len(media_queue)), 'yellow'),
                    print self.colored('(%s)' % lang, 'yellow'),
                    print self.colored(','.join(media_queue[i][1]), 'green')
                self._compile_media(*media_queue[i])

        # Show all errors once again.
        print u'\n*** %i Media files processed, %i compile errors ***' % (len(media_queue), len(self._errors))

        # Ring bell :)
        print '\x07'

    def _build_compile_queue(self, languages, all_templates=True, single_template=None):
        """
        Build a list of all the templates to be compiled.
        """
        # Create compile queue
        queue = set() # Use a set, avoid duplication of records.

        if self.verbosity >= 2:
            print 'Building queue'

        for lang in languages:
            # Now compile all templates to the cache directory
            for dir, t in template_iterator():
                input_path = os.path.normpath(os.path.join(dir, t))
                output_path = self._make_output_path(lang, t)

                # Compile this template if:
                if (
                        # We are compiling *everything*
                        all_templates or

                        # Or this is the only template that we want to compile
                        (single_template and t in single_template) or

                        # Or we are compiling changed files
                        (not single_template and (

                            # Compiled file does not exist
                            not os.path.exists(output_path) or

                            # Compiled file has been marked for recompilation
                            os.path.exists(output_path + '-c-recompile') or

                            # Compiled file is outdated
                            os.path.getmtime(output_path) < os.path.getmtime(input_path))

                        )):

                    queue.add( (lang, t, input_path, output_path) )

                    # When this file has to be compiled, and other files depend
                    # on this template also compile the other templates.
                    if os.path.exists(output_path + '-c-used-by'):
                        for t2 in open(output_path + '-c-used-by', 'r').read().split('\n'):
                            if t2:
                                try:
                                    queue.add( (lang, t2, get_template_path(t2), self._make_output_path(lang, t2)) )
                                except TemplateDoesNotExist, e:
                                    pass # Reference to non-existing template

        # Return ordered queue
        queue = list(queue)
        queue.sort()
        return queue


    def _build_compile_media_queue(self, languages):
        from template_preprocessor.core.utils import compile_external_css_files, compile_external_javascript_files

        queue = []
        for root, dirs, files in os.walk(settings.MEDIA_CACHE_DIR):
            for f in files:
                if f.endswith('-c-meta'):
                    input_files = open(os.path.join(root, f), 'r').read().split('\n')
                    output_file = f[:-len('-c-meta')]
                    lang = os.path.split(root)[-1]

                    if output_file.endswith('.js'):
                        extension = 'js'
                        compiler = compile_external_javascript_files
                    elif output_file.endswith('.css'):
                        extension = 'css'
                        compiler = compile_external_css_files
                    else:
                        extension = None

                    if extension and need_to_be_recompiled(input_files, create_media_output_path(input_files, extension, lang)):
                        queue.append((lang, input_files, compiler))

        queue.sort()
        return queue


    def _compile_media(self, lang, input_urls, compiler):
        context = self.NiceContext('External media: ' + ','.join(input_urls))
        compiler(input_urls, context)


    def _make_output_path(self, language, template):
        return os.path.normpath(os.path.join(settings.TEMPLATE_CACHE_DIR, language, template))


    def _save_template_dependencies(self, lang, template, dependency_list):
        """
        Store template dependencies into meta files.  (So that we now which
        templates need to be recompiled when one of the others has been
        changed.)
        """
        # Reverse dependencies
        for t in dependency_list:
            output_path = self._make_output_path(lang, t) + '-c-used-by'
            self._create_dir(os.path.split(output_path)[0])

            # Append current template to this list if it doesn't appear yet
            deps = open(output_path, 'r').read().split('\n') if os.path.exists(output_path) else []

            if not template in deps:
                open(output_path, 'a').write(template + '\n')

        # Dependencies
        output_path = self._make_output_path(lang, template) + '-c-depends-on'
        open(output_path, 'w').write('\n'.join(dependency_list) + '\n')

    def _save_first_level_template_dependencies(self, lang, template, include_list, extends_list):
        """
        First level dependencies (used for generating dependecy graphs)
        (This doesn't contain the indirect dependencies.)
        """
        # {% include "..." %}
        output_path = self._make_output_path(lang, template) + '-c-includes'
        open(output_path, 'w').write('\n'.join(include_list) + '\n')

        # {% extends "..." %}
        output_path = self._make_output_path(lang, template) + '-c-extends'
        open(output_path, 'w').write('\n'.join(extends_list) + '\n')

    def _compile_template(self, lang, template, input_path, output_path, no_html=False):
        try:
            # Create output directory
            self._create_dir(os.path.split(output_path)[0])

            try:
                # Open input file
                code = codecs.open(input_path, 'r', 'utf-8').read()
            except UnicodeDecodeError, e:
                raise CompileException(0, 0, input_path, str(e))
            except IOError, e:
                raise CompileException(0, 0, input_path, str(e))

            # Compile
            if no_html:
                output, context = compile(code, path=input_path, loader=load_template_source,
                            options=get_options_for_path(input_path) + ['no-html'],
                            context_class=self.NiceContext)
            else:
                output, context = compile(code, path=input_path, loader=load_template_source,
                            options=get_options_for_path(input_path),
                            context_class=self.NiceContext)

            # store dependencies
            self._save_template_dependencies(lang, template, context.template_dependencies)
            self._save_first_level_template_dependencies(lang, template, context.include_dependencies,
                                                                context.extends_dependencies)

            # Open output file
            codecs.open(output_path, 'w', 'utf-8').write(output)

            # Delete -c-recompile file (mark for recompilation) if one such exist.
            if os.path.exists(output_path + '-c-recompile'):
                os.remove(output_path + '-c-recompile')

            return True

        except CompileException, e:
            # Try again without html
            if not no_html:
                # Print the error
                self.print_error(u'ERROR:  %s' % unicode(e))

                print u'Trying again with option "no-html"... ',
                if self._compile_template(lang, template, input_path, output_path, no_html=True):
                    print 'Succeeded'
                else:
                    print 'Failed again'

                # Create recompile mark
                open(output_path + '-c-recompile', 'w').close()

        except TemplateDoesNotExist, e:
            if self.verbosity >= 2:
                print u'WARNING: Template does not exist:  %s' % unicode(e)

    def _create_dir(self, newdir):
        if not os.path.isdir(newdir):
            os.makedirs(newdir)


########NEW FILE########
__FILENAME__ = compile_templates_to_code
"""
Author: Jonathan Slenders, City Live
"""
import os
import codecs
from optparse import make_option
import termcolor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist

from template_preprocessor.core import compile_to_parse_tree
from template_preprocessor.render_engine.render import compile_tree
from template_preprocessor.core.lexer import CompileException

from template_preprocessor.utils import language, template_iterator, load_template_source

WARNING="""
            WARNING: experimental compiler, not ready for production!
"""


class Command(BaseCommand):
    help = "Compile all the templates to fast python code."

    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', dest='all_templates', help='Compile all templates (instead of only the changed)'),
        make_option('--language', action='append', dest='languages', help='Give the languages'),
    )


    def print_error(self, text):
        self._errors.append(text)
        print termcolor.colored(text, 'white', 'on_red')

    def handle(self, *args, **options):
        all_templates = options['all_templates']

        print WARNING

        # Default verbosity
        self.verbosity = int(options.get('verbosity', 1))

        # All languages by default
        languages = [l[0] for l in settings.LANGUAGES]
        if options['languages'] is None:
            options['languages'] = languages

        self._errors = []

        cache_dir = os.path.join(settings.TEMPLATE_CACHE_DIR, 'compiled_to_code')

        # Delete previously compiled templates
        # (This is to be sure that no template loaders were configured to
        # load files from this cache.)
        if all_templates:
            for root, dirs, files in os.walk(cache_dir):
                for f in files:
                    path = os.path.join(root, f)
                    if self.verbosity >= 1:
                        print ('Deleting old code: %s' % path)
                    os.remove(path)

        # Create compile queue
        queue = set()

        if self.verbosity >= 2:
            print 'Building queue'

        for lang in options['languages']:
            # Now compile all templates to the cache directory
            for dir, t in template_iterator():
                input_path = os.path.join(dir, t)
                output_path = os.path.join(cache_dir, lang, t)
                if (
                        all_templates or
                        not os.path.exists(output_path) or
                        os.path.getmtime(output_path) < os.path.getmtime(input_path)):
                    queue.add( (lang, input_path, output_path) )

        queue = list(queue)
        queue.sort()

        for i in range(0, len(queue)):
            lang = queue[i][0]
            with language(lang):
                if self.verbosity >= 2:
                    print termcolor.colored('%i / %i |' % (i, len(queue)), 'yellow'),
                    print termcolor.colored('(%s)' % lang, 'yellow'),
                    print termcolor.colored(queue[i][1], 'green')

                self._compile_template(*queue[i])

        # Show all errors once again.
        print u'\n*** %i Files processed, %i compile errors ***' % (len(queue), len(self._errors))

    def _compile_template(self, lang, input_path, output_path):
        try:
            # Open input file
            code = codecs.open(input_path, 'r', 'utf-8').read()

            # Compile
            output = compile_to_parse_tree(code, loader=load_template_source, path=input_path)
            output2 = compile_tree(output)

            # Open output file
            self._create_dir(os.path.split(output_path)[0])
            codecs.open(output_path, 'w', 'utf-8').write(output2)

        except CompileException, e:
            self.print_error(u'ERROR:  %s' % unicode(e))

        except TemplateDoesNotExist, e:
            if self.verbosity >= 2:
                print u'WARNING: Template does not exist:  %s' % unicode(e)

    def _create_dir(self, newdir):
        if not os.path.isdir(newdir):
            os.makedirs(newdir)


########NEW FILE########
__FILENAME__ = make_template_dependency_graph
"""
Generate a graph of all the templates.

- Dotted arrows represent includes
- Solid arrows represent inheritance.

"""


from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.html import escape
from optparse import make_option
from yapgvb import Graph
import datetime
import time
import math
import os

from django.contrib.auth.models import User
from django.db.models import Q
from template_preprocessor.utils import template_iterator, get_template_path
from django.conf import settings


class Command(BaseCommand):
    help = "Make dependency graph"
    option_list = BaseCommand.option_list + (
        make_option('--directory', action='append', dest='directory', help='Template directory (all templates if none is given)'),
        make_option('--exclude', action='append', dest='exclude_directory', help='Exclude template directory'),
    )

    def handle(self, *args, **options):
        directory = (options.get('directory', ['']) or [''])[0]
        exclude_directory = (options.get('exclude_directory', []) or [])

        g = Graph('Template dependencies', True)

        g.layout('neato')
        g.landscape = True
        g.rotate = 90
        g.label = str(datetime.datetime.now())
        #g.scale = 0.7
        #g.overlap = 'prism'
        #g.overlap = False
        g.overlap = 'scale'
        g.ranksep = 1.8
        g.overlap = 'compress'
        g.ratio = 1. / math.sqrt(2)
        g.sep = 0.1
        g.mindist = 0.1

        nodes = set()
        edges = [ ]
        nodes_in_edges = set()

        # Retreive all nodes/edges
        for dir, t in template_iterator():
            if t.startswith(directory) and not any([ t.startswith(x) for x in exclude_directory ]):
                nodes.add(t)

                # {% include "..." %}
                includes = self._make_output_path(t) + '-c-includes'

                if os.path.exists(includes):
                    for t2 in open(includes, 'r').read().split('\n'):
                        if t2:
                            nodes.add(t2)
                            edges.append( (t, t2, False) )

                            nodes_in_edges.add(t)
                            nodes_in_edges.add(t2)

                # {% extends "..." %}
                extends = self._make_output_path(t) + '-c-extends'

                if os.path.exists(extends):
                    for t2 in open(extends, 'r').read().split('\n'):
                        if t2:
                            nodes.add(t2)
                            edges.append( (t, t2, True) )

                            nodes_in_edges.add(t)
                            nodes_in_edges.add(t2)

        # Remove orphan nodes
        for n in list(nodes):
            if not n in nodes_in_edges:
                nodes.remove(n)

        # Create graphvis nodes
        nodes2 = { }
        for t in nodes:
            node = self._create_node(t, g, nodes2)

        # Create graphvis edges
        for t1, t2, is_extends in edges:
            print 'from ', t1, ' to ', t2
            node_a = self._create_node(t1, g, nodes2)
            node_b = self._create_node(t2, g, nodes2)
            edge = g.add_edge(node_a, node_b)
            edge.color = 'black'
            edge.arrowhead = 'normal'
            edge.arrowsize = 1.1
            if is_extends:
                edge.style = 'solid'
            else:
                edge.style = 'dotted'

        #g.layout('neato')
        g.layout('twopi')
        g.render(settings.ROOT + 'template_dependency_graph.pdf', 'pdf', None)
        g.render(settings.ROOT + 'template_dependency_graph.jpg', 'jpg', None)


    def _create_node(self, template, graph, nodes):
        """
        Create node for subscription, if one exists for this subscription in
        `nodes`, return the existing.
        """
        if template not in nodes:
            node = graph.add_node(template.replace('/', '/\n').encode('utf-8'))
            node.shape = 'rect'
            node.label = template.replace('/', '/\n').encode('utf-8')
            node.fontsize = 11
            node.fixedsize = False
            node.width = 1.0
            node.height = 0.8
            node.fontcolor = 'black'


            node.style = 'filled'
            node.fillcolor = 'white'
            node.fontcolor = 'black'

            nodes[template] = node

        return nodes[template]

    def _make_output_path(self, template):
        return os.path.join(settings.TEMPLATE_CACHE_DIR, 'en', template)


########NEW FILE########
__FILENAME__ = open_in_editor_server
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import os
import sys


class Command(BaseCommand):
    help = "Server for opening Django templates in your code editor. (Used by the chromium extension)"

    """
    The Chromium extension for browsing the Django Template Source code runs
    in a sandbox, and is not able to execute native commands. The extension
    can however do HTTP requests to this server on 'localhost' which can in
    turn execute the system command for opening the editor.
    """
    def handle(self, addrport='', *args, **options):
        import django
        from django.core.servers.basehttp import run, AdminMediaHandler, WSGIServerException
        from django.core.handlers.wsgi import WSGIHandler

        if args:
            raise CommandError('Usage is runserver %s' % self.args)
        if not addrport:
            addr = ''
            port = 8900
        else:
            try:
                addr, port = addrport.split(':')
            except ValueError:
                addr, port = '', addrport
        if not addr:
            addr = '127.0.0.1'

        # Patch the settings
        def patch_settings():
            # We only need the INSTALLED_APPS from this application, but have
            # our own url patterns and don't need any other middleware.
            from django.conf import settings
            settings.ROOT_URLCONF = 'template_preprocessor.tools.open_in_editor_api.urls'
            settings.MIDDLEWARE_CLASSES = []
        patch_settings()

        # Run the server
        def _run():
            from django.conf import settings
            from django.utils import translation

            print 'Open-in-editor server started'

            try:
                run(addr, int(port), WSGIHandler())
            except WSGIServerException, e:
                # Use helpful error messages instead of ugly tracebacks.
                ERRORS = {
                    13: "You don't have permission to access that port.",
                    98: "That port is already in use.",
                    99: "That IP address can't be assigned-to.",
                }
                try:
                    error_text = ERRORS[e.args[0].args[0]]
                except (AttributeError, KeyError):
                    error_text = str(e)
                sys.stderr.write(self.style.ERROR("Error: %s" % error_text) + '\n')
                # Need to use an OS exit because sys.exit doesn't work in a thread
                os._exit(1)
            except KeyboardInterrupt:
                if shutdown_message:
                    print shutdown_message
                sys.exit(0)
        _run()

########NEW FILE########
__FILENAME__ = print_not_translated_strings
"""
Author: Jonathan Slenders, City Live
"""
import codecs
import os
import string
from optparse import make_option
import termcolor

from django.core.management.base import BaseCommand
from django.template import TemplateDoesNotExist

from template_preprocessor.core import compile_to_parse_tree
from template_preprocessor.core.lexer import CompileException

from template_preprocessor.utils import template_iterator, load_template_source
from template_preprocessor.utils import get_options_for_path


class Command(BaseCommand):
    help = "Print an overview of all the strings in the templates which lack {% trans %} blocks around them."

    option_list = BaseCommand.option_list + (
        make_option('--single-template', action='append', dest='single_template', help='Compile only this template'),
        make_option('--boring', action='store_true', dest='boring', help='No colors in output'),
    )

    def print_error(self, text):
        self._errors.append(text)
        print self.colored(text, 'white', 'on_red').encode('utf-8')


    def colored(self, text, *args, **kwargs):
        if self.boring:
            return text
        else:
            return termcolor.colored(text, *args, **kwargs)


    def handle(self, *args, **options):
        single_template = options['single_template']

        # Default verbosity
        self.verbosity = int(options.get('verbosity', 1))

        # Colors?
        self.boring = bool(options.get('boring'))

        self._errors = []

        # Build compile queue
        queue = self._build_compile_queue(single_template)

        # Compile queue
        for i in range(0, len(queue)):
                if self.verbosity >= 2:
                    print self.colored('%i / %i |' % (i+1, len(queue)), 'yellow'),
                    print self.colored(queue[i][1], 'green')

                self._compile_template(*queue[i])

        # Ring bell :)
        print '\x07'

    def _build_compile_queue(self, single_template=None):
        """
        Build a list of all the templates to be compiled.
        """
        # Create compile queue
        queue = set() # Use a set, avoid duplication of records.

        if self.verbosity >= 2:
            print 'Building queue'

        # Now compile all templates to the cache directory
        for dir, t in template_iterator():
            input_path = os.path.normpath(os.path.join(dir, t))

            # Compile this template if:
            if (
                    # We are compiling *everything*
                    not single_template or

                    # Or this is the only template that we want to compile
                    (single_template and t in single_template)):

                queue.add( (t, input_path) )

        # Return ordered queue
        queue = list(queue)
        queue.sort()
        return queue


    def _compile_template(self, template, input_path):
        try:
            try:
                # Open input file
                code = codecs.open(input_path, 'r', 'utf-8').read()
            except UnicodeDecodeError, e:
                raise CompileException(0, 0, input_path, str(e))
            except IOError, e:
                raise CompileException(0, 0, input_path, str(e))

            # Get options for this template
            options=get_options_for_path(input_path)
            options.append('no-i18n-preprocessing')

            # Compile
            tree, context = compile_to_parse_tree(code, path=input_path, loader=load_template_source,
                        options=options)

            # Now find all nodes, which contain text, but not in trans blocks.
            from template_preprocessor.core.html_processor import HtmlContent, HtmlStyleNode, HtmlScriptNode

            def contains_alpha(s):
                # Return True when string contains at least a letter.
                for i in s:
                    if i in string.ascii_letters:
                        return True
                return False

            for node in tree.child_nodes_of_class(HtmlContent, dont_enter=(HtmlStyleNode, HtmlScriptNode)):
                content = node.output_as_string()

                s = content.strip()
                if s and contains_alpha(s):
                    print self.colored(node.path, 'yellow'), '  ',
                    print self.colored(' %s:%s' % (node.line, node.column), 'red')
                    print s.encode('utf-8')

        except CompileException, e:
                # Print the error
                self.print_error(u'ERROR:  %s' % unicode(e))

        except TemplateDoesNotExist, e:
            if self.verbosity >= 2:
                print u'WARNING: Template does not exist:  %s' % unicode(e)

########NEW FILE########
__FILENAME__ = spellcheck_templates
"""
Author: Jonathan Slenders, City Live
"""
import os
import codecs
from optparse import make_option
import termcolor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist

from template_preprocessor.core import compile
from template_preprocessor.core import compile_to_parse_tree
from template_preprocessor.core.lexer import CompileException

from template_preprocessor.utils import language, template_iterator, load_template_source
from template_preprocessor.core.django_processor import parse, DjangoTransTag, DjangoBlocktransTag


IGNORE_WORDS = [

]


class Command(BaseCommand):
    help = "Spellcheck all templates."

    def found_spelling_errors(self, tag, word):
        if not word in self._errors:
            self._errors[word] = 1
        else:
            self._errors[word] += 1

        print '     ', termcolor.colored(word.strip().encode('utf-8'), 'white', 'on_red'),
        print '(%s, Line %s, column %s)' % (tag.path, tag.line, tag.column)


    def handle(self, *args, **options):
        self._errors = []

        # Default verbosity
        self.verbosity = int(options.get('verbosity', 1))

        # Now compile all templates to the cache directory
        for dir, t in template_iterator():
            input_path = os.path.join(dir, t)
            self._spellcheck(input_path)

        # Show all errors once again.
        print u'\n*** %i spelling errors ***' % len(self._errors)

        # Ring bell :)
        print '\x07'

    def _spellcheck(self, input_path):
        # Now compile all templates to the cache directory
            try:
                print termcolor.colored(input_path, 'green')

                # Open input file
                code = codecs.open(input_path, 'r', 'utf-8').read()

                # Compile
                tree = compile_to_parse_tree(code, loader=load_template_source, path=input_path)

                # For every text node
                for tag in tree.child_nodes_of_class([DjangoTransTag, DjangoBlocktransTag, ]):
                    if isinstance(tag, DjangoTransTag):
                        self._check_sentence(f, tag, tag.string)

                    if isinstance(tag, DjangoBlocktransTag):
                        for t in tag.children:
                            if isinstance(t, basestring):
                                self._check_sentence(f, tag, t)

            except CompileException, e:
                self.print_warning(u'Warning:  %s' % unicode(e))

            except TemplateDoesNotExist, e:
                self.print_warning(u'Template does not exist: %s' % unicode(e))

    def _check_sentence(self, path, tag, sentence):
        import subprocess
        p = subprocess.Popen(['aspell', '-l', 'en', 'list'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        p.stdin.write(sentence.encode('utf-8'))
        output = p.communicate()[0]
        for o in output.split():
            o = o.strip()
            if not (o in IGNORE_WORDS or o.lower() in IGNORE_WORDS):
                self.found_spelling_errors(tag, o)


########NEW FILE########
__FILENAME__ = template_preprocessor_makemessages
"""
Author: Jonathan Slenders, City Live
"""
import os
import sys
import codecs
from optparse import make_option
import termcolor

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist

from template_preprocessor.core import compile
from template_preprocessor.core.lexer import CompileException

from template_preprocessor.utils import language, template_iterator, load_template_source, get_template_path
from template_preprocessor.utils import get_options_for_path



class Command(BaseCommand):
    help = "Print all strings found in the templates and javascript gettext(...)"


    def handle(self, *args, **options):
        # Default verbosity
        self.verbosity = int(options.get('verbosity', 1))

        self.strings = { } # Maps msgid -> list of paths

        # Build queue
        queue = set()
        print 'Building queue'

        # Build list of all templates
        for dir, t in template_iterator():
            input_path = os.path.join(dir, t)
            queue.add( (t, input_path) )

        queue = list(queue)
        queue.sort()

        # Process queue
        for i in range(0, len(queue)):
            if self.verbosity >= 2:
                sys.stderr.write(termcolor.colored('%i / %i |' % (i, len(queue)), 'yellow'))
                sys.stderr.write(termcolor.colored(queue[i][1], 'green'))
            self.process_template(*queue[i])

        # Output string to stdout
        for s in self.strings:
            for l in self.strings[s]:
                print l
            print 'msgid "%s"' % s.replace('"', r'\"')
            print 'msgstr ""'
            print


    def process_template(self, template, input_path):
        # TODO: when HTML processing fails, the 'context' attribute is not
        #       retreived and no translations are failed.  so, translate again
        #       without html. (But we need to process html, in order to find
        #       gettext() in javascript.)

        try:
            try:
                # Open input file
                code = codecs.open(input_path, 'r', 'utf-8').read()
            except UnicodeDecodeError, e:
                raise CompileException(0, 0, input_path, str(e))

            # Compile
            output, context = compile(code, path=input_path, loader=load_template_source,
                        options=get_options_for_path(input_path))

            for entry in context.gettext_entries:
                line = '#: %s:%s:%s' % (entry.path, entry.line, entry.column)

                if not entry.text in self.strings:
                    self.strings[entry.text] = set()

                self.strings[entry.text].add(line)

                if self.verbosity >= 2:
                    sys.stderr.write(line + '\n')
                    sys.stderr.write('msgid "%s"\n\n' % entry.text.replace('"', r'\"'))

        except CompileException, e:
            sys.stderr.write(termcolor.colored('Warning: failed to process %s: \n%s\n' % (input_path, e),
                                    'white', 'on_red'))

        except TemplateDoesNotExist, e:
            pass

########NEW FILE########
__FILENAME__ = validate_html_in_model
"""
Author: Jonathan Slenders, City Live

Management command for validating HTML in model instances.
It will use the HTML parser/validator from the template proprocessor.
"""
import os
import termcolor

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import LabelCommand

from template_preprocessor.core import compile
from template_preprocessor.core.lexer import CompileException
from template_preprocessor.core.html_processor import compile_html_string

from template_preprocessor.utils import language


class Command(LabelCommand):
    """
    ./manage.py validate_html_in_model app_label.model.field

    Examples:
    ./manage.py validate_html_in_model blog.entry.body
    ./manage.py validate_html_in_model faq.faqtranslation.question faq.faqtranslation.answer
    ./manage.py validate_html_in_model flatpages.flatpage.content
    """
    help = 'Validate HTML in models.'
    args = 'app_label model field'

    def print_error(self, text):
        self._errors.append(text)
        print termcolor.colored(text, 'white', 'on_red')

    def handle_label(self, label, **options):
        self._errors = []

        args = label.split('.')
        if not len(args) == 3:
            print 'Not enough items (app_label.model.field)'
            print self.__doc__
            return

        app_label, model, field = args
        class_ = ContentType.objects.get(app_label=app_label, model=model).model_class()

        total = 0
        succes = 0

        for lang in ('en', 'fr', 'nl'):
            with language(lang):
                for i in class_.objects.all():
                    total += 1
                    print termcolor.colored('(%s) %s %i' % (lang, unicode(i), i.id), 'green')
                    try:
                        # TODO: maybe pass preprocessor options somehow.
                        #       at the moment, the default settings are working.
                        compile_html_string(getattr(i, field), path='%s (%i)' % (unicode(i), i.id) )
                        succes += 1

                    except CompileException, e:
                        self.print_error(unicode(e))

        # Show all errors once again.
        print u'\n*** %s Compile Errors ***' % len(self._errors)
        for e in self._errors:
            print termcolor.colored(e)
            print

        print ' %i / %i succeeded' % (succes, total)

        # Ring bell :)
        print '\x07'

########NEW FILE########
__FILENAME__ = render
# Author: Jonathan Slenders, City Live

#
#  !!!! THIS IS AN *EXPERIMENTAL* COMPILED RENDER ENGINE FOR DJANGO TEMPLATES
#  !!!!      -- NOT READY FOR PRODUCTION --
#


# Only some ideas and pseudo code for implementing a faster template rendering
# engine. The idea is to totally replace Django's engine, by writing a new
# rendering engine compatible with Django's 'Template'-object.

# It should be a two-step rendering engine
# 1. Preprocess template to a the new, more compact version which is still
#    compatible with Django. (with the preprocessor as we now do.) 2.
# 2. Generate Python code from each Template. (Template tags are not
#    compatible, because they literrally plug into the current Django parser,
#    but template filters are reusable.) Call 'compile' on the generated code,
#    wrap in into a Template-compatible object and return from the template loader.



# Some tricks we are going to use:
# 1. Compiled code will use local variables where possible. Following translations will be made:
#         {{ a }}   ->    a
#         {{ a.b }}   ->    a.b
#         {{ a.0.c }}   ->    a[0].c
#         {{ a.get_profile.c }}   ->  a.get_profile.c  # proxy of get_profile will call itself when resolving c.
#
#    Accessing local variables should be extremely fast in python, if a
#    variable does not exist in the locals(), python will automatically look
#    into the globals. But if we run this code through an eval() call, it is
#    possible to pass our own Global class which will transparantly redirect
#    lookups to the context if they were not yet assigned by generated code.
#    http://stackoverflow.com/questions/3055228/how-to-override-built-in-getattr-in-python
#
#

# 2. Generated code will output by using 'print', not yield. We will replace
#    sys.stdout for capturing render output and ''.join -it afterwards. To
#    restore: sys.stdout=sys.__stdout__
#    -> UPDATE: it's difficult to replace stdout. it would cause difficult template
#    tag implementations, when using tags like {% filter escape %}i[Madi, it would cause
#    several levels of wrapped-stdouts. -> now using a custom _write function.


# Very interesting documentation:
# http://docs.python.org/reference/executionmodel.html


from template_preprocessor.core.django_processor import DjangoTag, DjangoContent, DjangoVariable, DjangoPreprocessorConfigTag, DjangoTransTag, DjangoBlocktransTag, DjangoComment, DjangoMultilineComment, DjangoUrlTag, DjangoLoadTag, DjangoCompressTag, DjangoRawOutput
from template_preprocessor.core.html_processor import HtmlNode
from django.utils.translation import ugettext as _

from template_preprocessor.core.lexer import Token, State, StartToken, Shift, StopToken, Push, Pop, Error, Record, CompileException
from template_preprocessor.core.lexer_engine import tokenize

from template_preprocessor.core.lexer import CompileException

import sys

def _escape_python_string(string):
    return string.replace('"', r'\"')



# States for django variables

        # Grammar rules:
        # [ digits | quoted_string | varname ]
        # ( "." [ digits | quoted_string | varname ]) *
        # ( "|" filter_name ":" ? quoted_string "?" ) *


_DJANGO_VARIABLE_STATES = {
    'root' : State(
            State.Transition(r'_\(', (StartToken('trans'), Shift(), )),
            State.Transition(r'\)', (StopToken('trans'), Shift(), )),

            # Start of variable
            State.Transition(r'[0-9]+', (StartToken('digits'), Record(), Shift(), StopToken(), )),
            State.Transition(r'[a-zA-Z][0-9a-zA-Z_]*', (StartToken('name'), Record(), Shift(), StopToken(), )),
            State.Transition(r'"[^"]*"', (StartToken('string'), Record(), Shift(), StopToken(), )),
            State.Transition(r"'[^']*'", (StartToken('string'), Record(), Shift(), StopToken(), )),
            State.Transition(r'\.', (StartToken('dot'), Record(), Shift(), StopToken(), )),
            State.Transition(r'\|', (StartToken('pipe'), Record(), Shift(), StopToken(), )),
            State.Transition(r':', (StartToken('filter-option'), Record(), Shift(), StopToken() )),

            State.Transition(r'.|\s', (Error('Not a valid variable'),)),
            ),
}



# ==================================[ Code generator ]===================================


class CodeGenerator(object):
    """
    Object where the python output code will we placed into. It contains some
    utilities for tracking which variables in Python are already in use.
    """
    def __init__(self):
        self._code = [] # Lines of code, terminating \n not required after each line.
        self._tmp_print_code = [] # Needed to group print consecutive statements
        self._indent_level = 0

        # Push/pop stack of variable scopes.
        self._scopes = [ set() ]

        self._tag = None

    def tag_proxy(self, tag):
        """
        Return interface to this code generator, where every call is supposed to
        be executed on this tag (=parse token).
        (This does avoid the need of having to pass the tag to all the template
        tag implementations, and makes 'register_variable' aware of the current
        tag, so that proper exeptions with line numbers can be thrown.)
        """
        class CodeGeneratorProxy(object):
            def __getattr__(s, attr):
                self._tag = tag
                return getattr(self, attr)

            @property
            def current_tag(self):
                return self._tag
        return CodeGeneratorProxy()

    def write(self, line, _flush=True):
        if _flush:
            self._flush_print_cache()
        self._code.append('\t'*self._indent_level + line)

    def _flush_print_cache(self):
        if self._tmp_print_code:
            self.write('_w(u"""%s""")' % _escape_python_string(''.join(self._tmp_print_code)), False)
            self._tmp_print_code = []

    def write_print(self, text):
        if text:
            self._tmp_print_code.append(text)

    def indent(self):
        """
        Indent source code written in here. (Nested in current indentation level.)
        Usage: with generator.indent():
        """
        class Indenter(object):
            def __enter__(s):
                self._flush_print_cache()
                self._indent_level += 1

            def __exit__(s, type, value, traceback):
                self._flush_print_cache()
                self._indent_level -= 1
        return Indenter()

    def write_indented(self, lines):
        with self.indent():
            for l in lines:
                self.write(l)

    def register_variable(self, var):
        #if self.variable_in_current_scope(var):
        if var in self._scopes[-1]:
            raise CompileException(self._tag, 'Variable "%s" already defined in current scope' % var)
        else:
            self._scopes[-1].add(var)


    def scope(self):
        """
        Enter a new scope. (Nested in current scope.)
        Usage: with generator.scope():
        """
        class ScopeCreater(object):
            def __enter__(s):
                self._scopes.append(set())

            def __exit__(s, type, value, traceback):
                self._scopes.pop()
        return ScopeCreater()

    def variable_in_current_scope(self, variable):
        """
        True when this variable name has been defined in the current or one of the
        parent scopes.
        """
        return any(map(lambda scope: variable in scope, self._scopes))

    def convert_variable(self, name):
        """
        Convert a template variable to a Python variable.
        """
        # 88 -> 88
        # a.1.b -> a[1].b
        # 8.a   -> CompileException
        # "..." -> "..."
        # var|filter:"..."|filter2:value  -> _filters['filter2'](_filters['filter'](var))

        # Parse the variable
        tree = Token(name='root', line=1, column=1, path='django variable')
        tree.children = [ name ]
        tokenize(tree, _DJANGO_VARIABLE_STATES, [Token])

        #print tree._print()

        def handle_filter(subject, children):
            filter_name = None
            filter_option = None
            in_filter_option = False

            def result():
                assert filter_name

                if filter_name in _native_filters:
                    return _native_filters[filter_name](self, subject, filter_option)

                elif filter_option:
                    return '_f["%s"](%s, %s)' % (filter_name, subject, filter_option)

                else:
                    return '_f["%s"](%s)' % (filter_name, subject)

            for i in range(0,len(children)):
                part = children[i].output_as_string()
                c = children[i]

                if c.name == 'digits':
                    if not filter_option and in_filter_option:
                        filter_option = part
                    else:
                        raise CompileException(self._tag, 'Invalid variable')

                elif c.name == 'name':
                    if not filter_option and in_filter_option:
                        filter_option = part

                    elif not filter_name:
                        filter_name = part
                    else:
                        raise CompileException(self._tag, 'Invalid variable')

                elif c.name == 'string':
                    if not filter_option and in_filter_option:
                        filter_option = part
                    else:
                        raise CompileException(self._tag, 'Invalid variable')

                elif c.name == 'trans':
                    if not filter_option and in_filter_option:
                        filter_option = '_(%s)' % c.output_as_string()
                    else:
                        raise CompileException(self._tag, 'Invalid variable')

                if c.name == 'filter-option' and filter_name:
                    # Entered the colon ':'
                    in_filter_option = True

                elif c.name == 'pipe':
                    # | is the start of a following filter
                    return handle_filter(result(), children[i+1:])

            return result()

        def handle_var(children):
            out = []
            for i in range(0,len(children)):
                part = children[i].output_as_string()
                c = children[i]

                if c.name == 'digits':
                    # First digits are literals, following digits are indexers
                    out.append('[%s]' % part if out else part)

                elif c.name == 'dot':
                    #out.append('.') # assume last is not a dot
                    pass

                elif c.name == 'string':
                    out.append(part)

                elif c.name == 'name':
                    if out:
                        out.append('.%s' % part)
                    else:
                        if not self.variable_in_current_scope(part):
                            # If variable is not found in current or one of the parents'
                            # scopes, then prefix variable with "_c."
                            out.append('_c.%s' % part)
                        else:
                            out.append(part)

                elif c.name == 'trans':
                    if out:
                        raise CompileException(self._tag, 'Invalid variable')
                    else:
                        out.append('_(%s)' % handle_var(c.children))

                elif c.name == 'pipe':
                    # | is the start of a filter
                    return handle_filter(''.join(out), children[i+1:])
            return ''.join(out)

        return handle_var(tree.children)

    def get_code(self):
        self._flush_print_cache()
        return '\n'.join(self._code)

# ==================================[ Registration of template tags and filters ]===================================

# Dictionary for registering tags { tagname -> handler }
__tags = { }

class Tag(object):
    def __init__(self, tagname, optional=False):
        self.tagname = tagname
        self.is_optional = optional

def optional(tagname):
    """ Make a tagname optional.  """
    return Tag(tagname, optional=True)


def register_native_template_tag(start_tag, *other_tags):
    def turn_into_tag_object(tag):
        return Tag(tag) if isinstance(tag, basestring) else tag

    def decorator(func):
        __tags[start_tag] = func
        func.tags = map(turn_into_tag_object, other_tags)
    return decorator


_filters = { }
_native_filters = { }


def register_template_filter(name):
    def decorator(func):
        _filters[name] = func
    return decorator


def register_native_template_filter(name):
    def decorator(func):
        _native_filters[name] = func
    return decorator

# ==================================[ Compiler main loop ]===================================

def compile_tree(tree):
    """
    Turn parse tree into executable template code.
    """
    # We create some kind of tree hierarchy. The outer frames have to be
    # rendered before the inner frames.  This is opposed to Django's
    # parser/render engine, but we need this, because inner tags have to know
    # whether variabels are local scoped (from a parent frame), or come
    # directly from the context dictionary.

    generator = CodeGenerator()

    class TagFrameContent(object):
        def __init__(self, tagname):
            self.tagname = tagname
            self.content = []
            self.generator = None

        def render(self):
            for c in self.content:
                if isinstance(c, basestring):
                    generator.write_print(c)
                elif isinstance(c, Frame):
                    c.render()

        def render_indented(self):
            with generator.indent():
                self.render()

        @property
        def django_tags(self):
            """ Retreive the DjangoTag objects in this content frame """
            for c in self.content:
                if isinstance(c, TagFrame):
                    yield c.django_tag

        @property
        def django_variables(self):
            """ Retreive the DjangoVariable objects in this content frame """
            for c in self.content:
                if isinstance(c, VariableFrame):
                    yield c.django_variable

    class Frame(object): pass

    class TagFrame(Frame):
        """
        A frame is a series of matching template tags (like 'if'-'else'-'endif')
        with their content.
        """
        def __init__(self, django_tag, start_tag, other_tags, args=None):
            self.django_tag = django_tag # tag object
            self.start_tag = start_tag
            self.other_tags = other_tags # list of Tag
            self.args = args or []       # Tag args parameters
            self.handler = None  # Tag handler
            self.frame_content = [ ] # List of TagFrameContent

        @property
        def following_tagnames(self):
            """ Next optional tags, or first following required tag """
            for t in self.other_tags:
                if t.is_optional:
                    yield t.tagname
                else:
                    yield t.tagname
                    return

        def start_content_block(self, tagname):
            removed_tag = False
            while not removed_tag and len(self.other_tags):
                if self.other_tags[0].tagname == tagname:
                    removed_tag = True
                self.other_tags = self.other_tags[1:]

            content = TagFrameContent(tagname)
            self.frame_content.append(content)

        def append_content(self, content):
            if not self.frame_content:
                 self.frame_content.append(TagFrameContent(self.start_tag))
            self.frame_content[-1].content.append(content)

        def render(self):
            if self.handler:
                self.handler(generator.tag_proxy(self.django_tag), self.args, *self.frame_content)
            else:
                for c in self.frame_content:
                    c.render()

    class VariableFrame(Frame):
        def __init__(self, django_variable):
            self.django_variable = django_variable

        def render(self):
            generator.write('_w(%s)' %
                    generator.tag_proxy(self.django_variable).convert_variable(self.django_variable.varname))

    class BlocktransFrame(Frame):
        def __init__(self, tag):
            self.tag = tag

        def render(self):
            handle_blocktrans(generator.tag_proxy(self.tag), self.tag)

    def run():
        # Push/pop stack for the Django tags.
        stack = [ TagFrame(None, 'document', [ Tag('enddocument') ]) ]

        def top():
            return stack[-1] if stack else None

        def _compile(n):
            if isinstance(n, DjangoTag):
                if n.tagname in __tags:
                    # Opening of {% tag %}
                    other_tags = __tags[n.tagname].tags
                    frame = TagFrame(n, n.tagname, other_tags, n.args)
                    frame.handler = __tags[n.tagname]

                    if other_tags:
                        stack.append(frame)
                    else:
                        top().append_content(frame)

                elif stack and n.tagname == top().other_tags[-1].tagname:
                    # Close tag for this frame
                    frame = stack.pop()
                    top().append_content(frame)

                elif stack and n.tagname in top().following_tagnames:
                    # Transition to following content block (e.g. from 'if' to 'else')
                    top().start_content_block(n.tagname)

                else:
                    raise CompileException(n, 'Unknown template tag %s' % n.tagname)

            elif isinstance(n, DjangoVariable):
                top().append_content(VariableFrame(n))

            elif isinstance(n, basestring):
                top().append_content(n)

            elif isinstance(n, DjangoTransTag):
                top().append_content(_(n.string))

            elif isinstance(n, DjangoBlocktransTag):
                # Create blocktrans frame
                top().append_content(BlocktransFrame(n))

            elif any([ isinstance(n, k) for k in (DjangoPreprocessorConfigTag, DjangoComment, DjangoMultilineComment, DjangoLoadTag, DjangoCompressTag) ]):
                pass

            elif any([ isinstance(n, k) for k in (DjangoContent, HtmlNode, DjangoRawOutput) ]):
                # Recursively build output frames
                n.output(_compile)

            else:
                raise CompileException(n, 'Unknown django tag %s' % n.name)

        tree.output(_compile)

        stack[0].render()

        return generator.get_code()
    return run()


def handle_blocktrans(generator, tag):
    """
    Handle {% blocktrans with value as name ...%} ... {% endblocktrans %}
    """
    # TODO: {% plural %} support

    variables = []
    string = []

    for c in tag.children:
        if isinstance(c, DjangoVariable):
            variables.append(c.varname)
            string.append('%%(%s)s' % c.varname)
        elif isinstance(c, basestring):
            string.append(c)  # TODO: escape %
        else:
            string.append(c.output_as_string())  # TODO: escape %

    # TODO: wrap in 'with' block


    if variables:
        generator.write('_w(_("""%s""") %% { %s })' % (
                                ''.join(string).replace('"', r'\"'),
                                ','.join(['"%s":%s' % (v, generator.convert_variable(v)) for v in variables ])
                                ))
    else:
        generator.write('_w(_("""%s"""))' % ''.join(string))

    """
    def __(b, c):
        _w("%(b)s ... %(c)s" % { 'b': b, 'c': c })
    __(_c.a,_c.d)

    # {% blocktrans with a as b and d as c %}{{ b }} ... {{ c }}{% endblocktrans %}
    """



def register_template_tag(tagname, *other_tags):
    """
    Register runtime-evaluated template tag.
    """
    def decorator(func):
        @register_native_template_tag(tagname, *other_tags)
        def native_implementation(generator, args, *content):
            i = 0
            for c in content:
                generator.write('def __%s():' % i)
                c.render_indented()
                i += 1
            generator.write('_call_tag(%s, %s, %s)' %
                (unicode(args), ','.join(map(lambda i: '__%s' % i, range(0, len(content))))))

            """
            def __c1():
                ...
            def __c2():
                ...
            def __c3():
                ...
            _call_tag('tag_handler', args, __c1, __c2, __c3)
            """

        # TODO: store binding between func and native implementation somewhere.
        # _call_tag('tag_handler') -> func
        # TODO: pass context or loookup method

    return decorator





# ==================================[ Code execution environment ]===================================

class OutputCapture(list):
    """
    Simple interface for capturing the output, and stacking
    several levels of capturing on top of each other.

    We inherit directly from list, for performance reasons.
    It faster than having a member object of type list, and
    doing a lookup every time.
    """
    def __init__(self):
        self.sink_array = []
        self.level = 0

        # Redirect stdout to capture interface
        # (for parts of code doing print or sys.stdout.write
        class StdOut(object):
            def write(s, c):
                self.append(c)

        self._old_stdout = sys.stdout
        sys.stdout = StdOut()

    def capture(self):
        # Copy current list to stack
        self.sink_array.append(list(self))

        # Create new sink
        list.__init__(self) # Empty capture list

        self.level += 1

    def __call__(self, c):
        self.append(c)

    def end_capture(self):
        if self.level:
            # Join last capture
            result = u''.join(map(unicode,self))
            self.level -= 1

            # Pop previous capture
            list.__init__(self)
            self.extend(self.sink_array.pop())

            return result
        else:
            raise Exception("'end_capture' called without any previous call of 'capture'")

    def end_all_captures(self):
        # Restore stdout
        sys.stdout = self._old_stdout

        # Return captured content
        out = ''
        while self.level:
            out = self.end_capture()
        return out


class ContextProxy(object):
    """
    Proxy for a Django template Context, this will handle the various attribute lookup
    we can do in a template. (A template author does not have to know whether something is
    an attribute or index or callable, we decide at runtime what to do.)
    """
    def __init__(self, context=''):
        self._context = context or '' # Print an empty string, rather than 'None'

    def __str__(self):
        return str(self._context)

    def __unicode__(self):
        return unicode(self._context)

    def __add__(self, other):
        """ Implement + operator """
        if isinstance(other, ContextProxy):
            other = other._context
        return ContextProxy(self._context + other)

    def __sub__(self, other):
        """ Implement - operator """
        if isinstance(other, ContextProxy):
            other = other._context
        return ContextProxy(self._context - other)

    def __iter__(self):
        try:
            return self._context.__iter__()
        except AttributeError:
            # Dummy iterator
            return [].__iter__()

    def __nonzero__(self):
        return bool(self._context)

    def __len__(self):
        return len(self._context)

    def __call__(self, *args, **kwargs):
        try:
            return ContextProxy(self._context(*args, **kwargs))
        except TypeError:
            return ContextProxy()

    def __getattr__(self, name):
        # Similar to django.template.Variable._resolve_lookup(context)
        # But minor differences: `var.0' is in our case compiled to var[0]
        # Do we can a quick list index lookup, before dictionary lookup of the string "0".
        c = self._context

        try:
            attr = c[name]
            if callable(attr): attr = attr()
            return ContextProxy(attr)
        except (IndexError, ValueError, TypeError, KeyError, AttributeError):
            try:
                attr = getattr(c, name)
                if callable(attr): attr = attr()
                return ContextProxy(attr)
            except (TypeError, AttributeError):
                try:
                    attr = c[str(name)]
                    if callable(attr): attr = attr()
                    return ContextProxy(attr)
                except (KeyError, AttributeError, TypeError):
                    return ContextProxy()

    def __getitem__(self, name):
        c = self._context

        try:
            attr = c[name]
            if callable(attr): attr = attr()
            return ContextProxy(attr) # Print an empty string, rather than 'None'
        except (IndexError, ValueError, TypeError, KeyError):
            try:
                attr = c[str(name)]
                if callable(attr): attr = attr()
                return ContextProxy(attr)
            except (KeyError, AttributeError, TypeError):
                return ContextProxy()




class Template(object):
    """
    Create a Template-compatible object.
    (The API is compatible with django.template.Template, but it wraps around the faster
    template compiled as python code.)
    """
    def __init__(self, compiled_template_code, filename):
        from __builtin__ import compile
        self._code = compiled_template_code
        self.compiled_template_code = compile(compiled_template_code, 'Python compiled template: %s' % filename, 'exec')

    def render(self, context):
        a = self._code
        capture_interface = OutputCapture()
        capture_interface.capture()
        from django.core.urlresolvers import reverse

        our_globals = {
            'capture_interface': capture_interface, # Rendered code may call the capture interface.
            '_w': capture_interface,
            '_c': ContextProxy(context),
            '_f': _filters,
            '_p': ContextProxy,
            '_for': ForLoop,
            '_cycle': Cycle,
            'reverse':  reverse,
            '_': _,
            'sys': sys,
        }

        exec (self.compiled_template_code, our_globals, our_globals)

        # Return output
        return capture_interface.end_all_captures()



# ================================[ TEMPLATE TAG IMPLEMENTATIONS ]================================



@register_template_tag('has_permission', 'end_haspermission')
def has_permission(args):
    name = params[0]
    if lookup('request.user').has_permission(name): # TODO: receive context or lookup method
        content()


@register_native_template_tag('url')
def url(generator, args):
    """
    Native implementation of {% url %}
    """
    # Case 1: assign to varname
    if len(args) >= 2 and args[-2] == 'as':
        varname = args[-1]
        args = args[:-2]

        prefix = '%s = ' % varname
        suffix = ''
        generator.register_variable(varname)

    # Case 2: print url
    else:
        prefix = '_w('
        suffix = ')'

    def split_args_and_kwargs(params):
        args = []
        kwargs = { }
        for k in params:
            if '=' in k:
                k,v = k.split('=', 1)
                kwargs[unicode(k)] = generator.convert_variable(v)
            else:
                args.append(generator.convert_variable(k))

        return args, kwargs


    name = args[0]
    args, kwargs = split_args_and_kwargs(args[1:])

    generator.write('%s reverse("%s", args=%s, kwargs={%s})%s' %
            (
            prefix,
            unicode(name),
            '[%s]' % ','.join(args),
            ','.join(['"%s":%s' % (unicode(k), v) for k,v in kwargs.iteritems() ]),
            suffix
            ))


@register_native_template_tag('with', 'endwith')
def with_(generator, args, content):
    """
    {% with a as b and c as d %} ... {% endwith %}
    """
    pairs = { } # key -> value

    value = None
    passed_as = False

    for k in args:
        if k == 'and':
            pass
        elif k == 'as':
            passed_as = True
        else:
            if passed_as and value:
                # Remember pair
                pairs[k] = value
                value = None
                passed_as = False
            elif not value:
                value = k
            else:
                raise 'invalid syntax'#TODO

    with generator.scope():
        for name in pairs.keys():
            generator.register_variable(name);

        generator.write('def __(%s):' % ','.join(pairs.keys()))
        content.render_indented()
        generator.write('__(%s)' % ','.join(map(generator.convert_variable, pairs.values())))

    """
    def __(b):
        ...
    __(_c.a)
    """


@register_native_template_tag('filter', 'endfilter')
def filter(generator, args, content):
    """
    Native implementation of {% filter ... %} ... {% endfilter %}
    """
    filter_name, = args

    generator.write('_start_capture()')
    generator.write('def __():')
    content.render_indented()
    generator.write('__():')
    generator.write("print _filters['%s'](_stop_capture())," % filter_name)


    """
    _start_capture() # Push stdout stack
    def __():
        ...
    __()
    print _filters['escape'] (_stop_capture) # Pop stdout stack, call filter, and print
    """


@register_native_template_tag('if', optional('else'), 'endif')
def if_(generator, args, content, else_content=None):
    """
    Native implementation of the 'if' template tag.
    """
    operators = ('==', '!=', '<', '>', '<=', '>=', 'and', 'or', 'not', 'in')

    params = map(lambda p: p if p in operators else generator.convert_variable(p), args)

    generator.write('if %s:' % ' '.join(params))
    content.render_indented()

    if else_content:
        generator.write('else:')
        else_content.render_indented()


    """
    if condition:
        ...
    else:
        ...
    """


@register_native_template_tag('pyif', optional('else'), 'endpyif')
def pyif_(generator, args, content, else_content=None):
    """
    {% pyif ... %}
    """
    # It is pretty tricky to do a decent convertion of the variable names in this case,
    # therefor, we execute the pyif test in an eval, and pass everything we 'think' that
    # could be a variable into a new context. There is certainly a better implementation,
    # but this should work, and pyif is not recommended anyway.

    def find_variables():
        import re
        variable_re = re.compile(r'[a-zA-Z][a-zA-Z0-9_]*')

        vars = set()
        for a in args:
            for x in variable_re.findall(a):
                if not x in ('and', 'or', 'not', 'in'):
                    vars.add(x)
        return vars

    def process_condition():
        import re
        part_re = re.compile(
            '(' +
                # Django variable name with filter or strings
                r'([a-zA-Z0-9_\.\|:]+|"[^"]*"|\'[^\']*\')+'

            + '|' +
                # Operators
                r'([<>=()\[\]]+)'
            ')'
        )
        operator_re = re.compile(r'([<>=()\[\]]+|and|or|not|in)')

        o = []
        for a in args:
            y = part_re.findall(a)
            for x in part_re.findall(a):
                if isinstance(x,tuple): x = x[0]
                if operator_re.match(x):
                    o.append(x)
                else:
                    o.append(generator.convert_variable(x))
        return ' '.join(o)

    generator.write('if (%s):' % process_condition())
    content.render_indented()

    if else_content:
        generator.write('else:')
        else_content.render_indented()


@register_native_template_tag('ifequal', optional('else'), 'endifequal')
def ifequal(generator, args, content, else_content=None):
    """
    {% ifequal %}
    """
    a, b = args

    generator.write('if %s == %s:' % (generator.convert_variable(a), generator.convert_variable(b)))
    content.render_indented()

    if else_content:
        generator.write('else:')
        else_content.render_indented()


    """
    if a == b:
        ...
    else:
        ...
    """

@register_native_template_tag('ifnotequal', optional('else'), 'endifnotequal')
def ifnotequal(generator, args, content, else_content=None):
    """
    {% ifnotequal %}
    """
    a, b = args

    generator.write('if %s != %s:' % (generator.convert_variable(a), generator.convert_variable(b)))
    content.render_indented()

    if else_content:
        generator.write('else:')
        else_content.render_indented()


@register_native_template_tag('for', optional('empty'), 'endfor')
def for_(generator, args, content, empty_content=None):
    """
    {% for item in iterator %}
        {{ forloop.counter }}
        {{ forloop.counter0 }}
        {{ forloop.revcounter0 }}
        {{ forloop.first }}
        {{ forloop.last }}
        {{ forloop.parentloop }}
        {% ifchanged var.name %}... {% endifchanged %}

        {% if forloop.first %} ... {% endif %}

        {% cycle "a" "b" %}
    {% empty %}
    {% endfor %}

    {% for x in a b c %}
        ...
    {% endfor %}
    """
    if len(args) > 3:
        var, in_ = args[0:2]
        iterator = args[3:]
    else:
        var, in_, iterator = args

    # === Implementation decision ===

    # We have two implementations of the forloop

    # 1. The Quick forloop. Where the forloop variable is not accessed anywhere
    #    inside the forloop. And where no empty statement is used.

    # 2. The slower, more advanced forloop. Which exposes a forloop object,
    #    exposes all the forloop properties, and allows usage of {% ifchanged %}
    quick_forloop = True

    if empty_content:
        quick_forloop = False

    for t in content.django_tags:
        if t.tagname in ('cycle', 'ifchanged'):
            quick_forloop = False

    for v in content.django_variables:
        if 'forloop' in v.varname:
            quick_forloop = False

            # TODO: chooose complex implementation when using {% if forloop.first %} somewhere.


    # === implementations ===

    if quick_forloop:
        with generator.scope():
            generator.register_variable(var);

            generator.write('def __():')
            with generator.indent():
                generator.write('for %s in %s:' % (var, generator.convert_variable(iterator)))
                with generator.indent():
                    generator.write('%s=_p(%s)' % (var, var))
                    content.render()
            generator.write('__()')

    else:
        # Forloop body
        with generator.scope():
            generator.register_variable(var);
            generator.register_variable('forloop');

            generator.write('def __(forloop, %s):' % var)
            content.render_indented()

        # Empty content body
        if empty_content:
            generator.write('def __e():')
            empty_content.render_indented()

        # Forloop initialisation
        generator.write('_for(%s, __, %s, %s)' % (
                                generator.convert_variable(iterator),
                                ('__e' if empty_content else 'None'),
                                'None' # TODO: pass parentloop, if we have one.
                            ))

    """
    # Quick implementation
    def __():
        for item in iterator:
            print ...
    __()

    # Advanced
    def __():
        for __(forloop):
            ...(content)...
        def __e(forloop, item):
            ...(empty)...
        --()
        _for(iterator, __, __e, forloop)
    __()
    """


class ForLoop(object):
    def __init__(self, iterator, body, empty_body, parent=None):
        self._iterator = iter(iterator)
        self._first = True
        self._last = False
        self._parent = parent
        self._counter = 0
        self._if_changed_storage = { }

        try:
            # Read first item
            current = self._iterator.next()

            # Read next item
            try:
                next_ = self._iterator.next()
            except StopIteration, e:
                self._last = True

            while True:
                # Call forloop body
                body(self, ContextProxy(current))

                # Go to next
                if self._last:
                    return
                else:
                    # Update current
                    self._counter += 1
                    current = next_

                    # Update next (not DRY, but it would cause too much function
                    # calling overhead otherwise...)
                    try:
                        next_ = self._iterator.next()
                    except StopIteration, e:
                        self._last = True

        except StopIteration, e:
            if empty_body:
                empty_body()

    @property
    def _ifchanged(self, varname, new_value):
        """
        In-forloop storage for checking wether this value has been changed,
        compared to last call. Called by {% ifchanged varname %} template tag.
        """
        self._if_changed_storage = { }
        prev_value = self._if_changed_storage.get(varname, None)
        changed = prev_value != new_value
        self._if_changed_storage[varname] = new_value
        return changed

    @property
    def first(self):
        return self._first

    @property
    def last(self):
        raise self._last

    @property
    def counter(self):
        return self._counter + 1

    @property
    def counter0(self):
        return self._counter

    @property
    def revcounter0(self):
        raise Exception('{{ forloop.revcounter0 }} not yet implemented')

    @property
    def parentloop(self):
        return self._parent or ContextProxy()

    def __getattr__(self):
        """
        For any undefined property, return this dummy proxy.
        """
        return ContextProxy()

class Cycle(object):
    def __init__(self, *args):
        self._args = args
        self._len = len(args)
        self._display_counter = 0

    @property
    def next(self):
        sys.stdout.write(self._args[self._display_counter % self._len ])
        self._display_counter += 1


@register_native_template_tag('cycle')
def cycle(generator, args):
    """ {% cycle v1 v2 v3 as varname %} """ # Not required to be nested inside a forloop, assigned to iterator
    """ {% cycle varname %} """ # Iterator ++; and output
    """ {% cycle v1 v2 v3 %} """ # cycle inside forloop.
    if 'as' in args:
        args, as_, varname = args[:-2], args[-2], args[-1]
        generator.register_variable(varname)
        generator.write('%s = _cycle(%s)' % (varname, ','.join(map(generator.convert_variable, args))))

    elif len(args) == 1:
        varname, = args

        if not generator.variable_in_current_scope(varname):
            raise CompileException(generator.current_tag, 'Variable %s has not been defined by a {% cycle %} declaration' % varname)

        generator.write('%s.next' % generator.convert_variable(varname))

    else:
        # How it works: {% for %} should detect wether some {% cycle %} nodes are nested inside
        if not generator.variable_in_current_scope('forloop'):
            raise CompileException(generator.current_tag, '{% cycle %} can only appear inside a {% for %} loop')

        args = map(generator.convert_variable, args)
        generator.write('sys.stdout.write([ %s ][ forloop.counter %% %i ])' % (','.join(args), len(args)))


    """
    varname = _cycle(v1, v2, v3)
    varname.next
    varname = [ v1, v2, v3 ] [ forloop.counter % 3 ]
    """


@register_native_template_tag('csrf_token')
def csrf_token(generator, args):
    """ {% csrf_token %} """
    # The django implementation checks if _c.csrf_token return 'NOTPROVIDED', and if so, it doesn't print
    # the hidden field. We don't place this if test in the generated code.
    generator.write_print('<div style="display:none"><input type="hidden" name="csrfmiddlewaretoken" value="')
    generator.write('sys.stdout.write(_c.csrf_token)')
    generator.write_print('" /></div>')


@register_native_template_tag('widthratio')
def widthratio(generator, args):
    """
    {% widthratio this_value max_value 100 %}
    """
    a, b, c = map(generator.convert_variable, args)
    generator.write('_w(int(%s / %s * %s))' % (a, b, c))


@register_native_template_tag('now')
def now_(generator, args):
    """
    {% now 'Y' format %}
    """
    format_, = map(generator.convert_variable, args)

    generator.write('def __():')
    with generator.indent():
        generator.write('from datetime import datetime')
        generator.write('from django.utils.dateformat import DateFormat')
        generator.write('sys.stdout.write(DateFormat(datetime.now()).format(%s))' % generator.convert_variable(format_))
    generator.write('__()')


@register_native_template_tag('call')
def call_template_tag(generator, args):
    """
    {% call func p1 p2 %}
    {% call result = func p1 p2 %}
    """
    if '=' in args:
        result = args[0]
        assert args[1] == '='
        func = generator.convert_variable(args[2])
        p = map(generator.convert_variable, args[3:])

        generator.register_variable(result)
        generator.write('%s = %s(%s)' % (result, func, ','.join(p)))
    else:
        func = generator.convert_variable(args[0])
        p = map(generator.convert_variable, args[1:])

        generator.write('sys.stdout.write(%s(%s))' % (func, ','.join(p)))


@register_native_template_tag('get_pingback_url')
def get_pingback_url(generator, args, *content):
    pass # TODO: and move to mvno platform

@register_native_template_tag('get_flattext')
def get_flattext(generator, args, *content):
    pass # TODO: and move to mvno platform

@register_native_template_tag('blog_latest_items')
def get_flattext(generator, args, *content):
    pass # TODO: and move to mvno platform

@register_native_template_tag('get_trackback_rdf_for')
def get_trackback_rdf_for(generator, args, *content):
    pass # TODO: and move to mvno platform

@register_native_template_tag('paginate', 'endpaginate')
def paginate(generator, args, paginated_content):
    pass # TODO: and move to mvno platform



@register_native_template_filter('add')
def add(generator, subject, arg):
    """ {{ var|add:"var" }} """ # TODO: arg should be converted to variables before calling filter
    return '(%s + %s)' % (subject, generator.convert_variable(arg))


@register_native_template_filter('default')
def default(generator, subject, arg):
    """ {{ var|default:"var" }} """
    return '(%s or %s)' % (subject, generator.convert_variable(arg))


@register_native_template_filter('empty')
def empty(generator, subject, arg):
    """ {{ var|empty:_("N/A) }} """
    #  TODO Same to |default filter???
    return '(%s or %s)' % (subject, generator.convert_variable(arg))



@register_native_template_filter('default_if_none')
def default_if_none(generator, subject, arg):
    """ {{ var|default_if_none:"var" }} """
        # TODO: may not be the best way, subject can be a complex object, and this causes it to be resolved twice.
    return '(%s if %s is None else %s)' % (subject, subject, generator.convert_variable(arg))

@register_native_template_filter('cut')
def cut(generator, subject, arg):
    """ {{ var|cut:" " }} """
    return 'unicode(%s).replace(%s, '')' % (subject, generator.convert_variable(arg))

@register_native_template_filter('replace')
def cut(generator, subject, arg):
    """ {{ var|replace:"a|b" }} """
    a, b = arg.strip('"').strip("'").split('|')
    return 'unicode(%s).replace("%s", "%s")' % (subject, a, b)

@register_native_template_filter('slice')
def slice(generator, subject, arg):
    """ {{ var|slice:":2"}} """
    a,b = arg.strip('"').strip("'").split(':')
    return '(%s[%s:%s])' % (subject,
            (int(a) if a else ''),
            (int(b) if b else ''))


@register_native_template_filter('divisibleby')
def divisibleby(generator, subject, arg):
    """ {{ var|divisibleby:3 }} """
    return '(%s %% %s == 0)' % (subject, generator.convert_variable(arg))


@register_native_template_filter('first')
def first(generator, subject, arg):
    """ {{ var|first }} """
    return '(%s[0])' % (subject)


@register_native_template_filter('join')
def join(generator, subject, arg):
    """ {{ var|join }} """
    return '(%s.join(%s))' % (generator.convert_variable(arg), subject)

@register_native_template_filter('safe')
def safe(generator, subject, arg):
    """ {{ var|safe }} """
    return subject # TODO

@register_native_template_filter('length')
def length(generator, subject, arg):
    """ {{ var|length}} """
    return 'len(%s)' % subject

@register_native_template_filter('pluralize')
def pluralize(generator, subject, arg):
    """ {{ var|pluralize }} """ # appends 's'
    """ {{ var|pluralize:"suffix" }} """
    """ {{ var|pluralize:"single,plural" }} """
    return subject # TODO

@register_native_template_filter('date')
def date(generator, subject, arg):
    """ {{ var|date:format }} """
    return subject # TODO

@register_native_template_filter('truncate_chars')
def truncate_chars(generator, subject, arg):
    """ {{ var|truncate_chars:2}} """
    return '%s[:%s]' % (subject, int(arg))

@register_native_template_filter('floatformat')
def floatformat(generator, subject, arg):
    """ {{ var|floatformat:"-3" }} """
    return subject # TODO


@register_native_template_filter('prettify_phonenumber')
def prettify_phonenumber(generator, subject, arg):
    """ {{ var|safe }} """
    return subject # TODO

@register_native_template_filter('dictsort')
def dictsort(generator, subject, arg):
    """ {{ var|dictsort:"key"}} """
    return 'sorted(%s, key=(lambda i: getattr(i, %s)))' % (subject, generator.convert_variable(arg))

@register_native_template_filter('dictsortreversed')
def dictsortreversed(generator, subject, arg):
    """ {{ var|dictsort:"key"}} """
    return 'sorted(%s, key=(lambda i: getattr(i, %s)), reverse=True)' % (subject, generator.convert_variable(arg))

#=================

@register_template_filter('capfirst')
def capfirst(subject):
    """ {{ value|capfirst }} """
    return subject[0].upper() + subject[1:]


@register_template_filter('striptags')
def striptags(subject):
    """Strips all [X]HTML tags."""
    from django.utils.html import strip_tags
    return strip_tags(subject)
    # TODO make safe string


# All django filters can be wrapped as non-native filters...

########NEW FILE########
__FILENAME__ = experimental_compiled
"""
Wrapper for loading the optimized, compiled templates. For Django 1.2
"""


from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist
from django.template.loader import BaseLoader, get_template_from_string, find_template_loader, make_origin
from django.utils import translation
from hashlib import sha1 as sha_constructor
from django.utils.importlib import import_module
from django.template import StringOrigin
from template_preprocessor.render_engine.render import compile_tree, Template
from template_preprocessor.core import compile_to_parse_tree

from template_preprocessor.core import compile

import os
import codecs



"""
Use this loader to experiment with running the to-python-compiled templates.
Implementation is probably like 75% finished.
"""


class Loader(BaseLoader):
    is_usable = True
    __cache_dir = settings.TEMPLATE_CACHE_DIR

    def __init__(self, loaders):
        self.template_cache = {}
        self._loaders = loaders
        self._cached_loaders = []

    @property
    def loaders(self):
        # Resolve loaders on demand to avoid circular imports
        if not self._cached_loaders:
            for loader in self._loaders:
                self._cached_loaders.append(find_template_loader(loader))
        return self._cached_loaders

    def find_template(self, name, dirs=None):
        for loader in self.loaders:
            try:
                template, display_name = loader.load_template_source(name, dirs)
                return (template, make_origin(display_name, loader.load_template_source, name, dirs))
            except TemplateDoesNotExist:
                pass
            except NotImplementedError, e:
                raise Exception('Template loader %s does not implement load_template_source. Be sure not to nest '
                            'loaders which return only Template objects into the template preprocessor. (We need '
                            'a loader which returns a template string.)' % unicode(loader))
        raise TemplateDoesNotExist(name)

    def load_template(self, template_name, template_dirs=None):
        lang = translation.get_language() or 'en'
        key = '%s-%s' % (lang, template_name)

        if key not in self.template_cache:
            # Path in the cache directory
            output_path = os.path.join(self.__cache_dir, 'cache', lang, template_name)

            # Load template
            if os.path.exists(output_path):
                # Prefer precompiled version
                template = codecs.open(output_path, 'r', 'utf-8').read()
                origin = StringOrigin(template)
            else:
                template, origin = self.find_template(template_name, template_dirs)

            # Compile template
            output = compile_to_parse_tree(template, loader = lambda path: self.find_template(path)[0], path=template_name)

            # Compile to python
            output2 = compile_tree(output)
            template = Template(output2, template_name)

            # Turn into Template object
            #template = get_template_from_string(template, origin, template_name)

            # Save in cache
            self.template_cache[key] = template

        # Return result
        return self.template_cache[key], None

    def reset(self):
        "Empty the template cache."
        self.template_cache.clear()

########NEW FILE########
__FILENAME__ = template_preprocessor
"""
Author: Jonathan Slenders, City Live

Following tag is a dummy tag. If the preprocessor is not used,
the tag should not output anything. If the preprocessor is enabled,
the tag is used to determine which optimizations are enabled.
"""
from django import template
from django.utils.safestring import mark_safe
from django.template import Library, Node, resolve_variable

register = template.Library()

class DummyTag(Node):
    """
    Dummy tag to make sure these preprocessor tags
    don't output anything if the preprocessor has been disabled.
    """
    def __init__(self):
        pass

    def render(self, context):
        return u''


@register.tag(name="!")
def preprocessor_option(parser, token):
    """
    # usage: {% ! no-whitespace-compression no-js-minify %}
    """
    return DummyTag()


@register.tag(name='compress')
def pack(parser, token):
    """
    # usage: {% compress %} ... {% endcompress %}
    Contains CSS or javascript files which are to be packed together.
    """
    return DummyTag()


@register.tag(name='endcompress')
def pack(parser, token):
    return DummyTag()


@register.tag(name='!raw')
def pack(parser, token):
    """
    # usage: {% !raw %} ... {% !endraw %}
    Contains a block which should not be html-validated.
    """
    return DummyTag()


@register.tag(name='!endraw')
def pack(parser, token):
    return DummyTag()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *


from template_preprocessor.tools.open_in_editor_api.views import open_in_editor


urlpatterns = patterns('',
    url(r'^$', open_in_editor)
)


########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from template_preprocessor.utils import get_template_path

import subprocess
import time


def open_in_editor(request):
    from django.conf import settings

    template = request.REQUEST['template']
    line = request.REQUEST.get('line', 0)
    column = request.REQUEST.get('column', 0)

    # Get template path
    path = get_template_path(template)
    print 'opening template: ' + path

    # Call command for opening this file
    if hasattr(settings, 'TEMPLATE_PREPROCESSOR_OPEN_IN_EDITOR_COMMAND'):
        settings.TEMPLATE_PREPROCESSOR_OPEN_IN_EDITOR_COMMAND(path, line, column)
    else:
        # By default, open this file in GVim, in a new tab.
        subprocess.Popen(["/usr/bin/gvim"])
        #subprocess.Popen(["/usr/bin/gvim", "--remote-tab", path ])
        time.sleep(0.4)
        subprocess.Popen(["/usr/bin/gvim", "--remote-send", "<ESC>:tabe %s<ENTER>" % path ])
        subprocess.Popen(["/usr/bin/gvim", "--remote-send", "<ESC>:%s<ENTER>%s|" % (line, column)])

    return HttpResponse('[{ "result": "ok" }]', mimetype="application/javascript")

########NEW FILE########
__FILENAME__ = utils
from django.utils import translation
from django.conf import settings
from django.template import TemplateDoesNotExist

import os
import codecs

EXCLUDED_APPS = [ 'debug_toolbar', 'django_extensions' ]

def language(lang):
    """
    Execute the content of this block in the language of the user.
    To be used as follows:

    with language(lang):
       some_thing_in_this_language()

    """
    class with_block(object):
        def __enter__(self):
            self._old_language = translation.get_language()
            translation.activate(lang)

        def __exit__(self, *args):
            translation.activate(self._old_language)

    return with_block()


def _get_path_form_app(app):
    m = __import__(app)
    if '.' in app:
        parts = app.split('.')
        for p in parts[1:]:
            m = getattr(m, p)
    return m.__path__[0]


def template_iterator():
    """
    Iterate through all templates of all installed apps.
    (Except EXCLUDED_APPS)
    """
    visited_templates = []
    def walk(directory):
        for root, dirs, files in os.walk(directory):
            for f in files:
                if not os.path.normpath(os.path.join(root, f)).startswith(settings.TEMPLATE_CACHE_DIR):
                    if f.endswith('.html'):
                        yield os.path.relpath(os.path.join(root, f), directory)


    for dir in settings.TEMPLATE_DIRS:
        for f in walk(dir):
            if f in visited_templates:
                continue
            visited_templates.append(f)
            yield dir, f

    for app in settings.INSTALLED_APPS:
        if app not in EXCLUDED_APPS:
            dir = os.path.join(_get_path_form_app(app), 'templates')
            for f in walk(dir):
                if f in visited_templates:
                    continue
                visited_templates.append(f)
                yield dir, f

def get_template_path(template):
    """
    Turn template path into absolute path
    """
    for dir in settings.TEMPLATE_DIRS:
        p = os.path.join(dir, template)
        if os.path.exists(p):
            return p

    for app in settings.INSTALLED_APPS:
        p = os.path.join(_get_path_form_app(app), 'templates', template)
        if os.path.exists(p):
            return p

    raise TemplateDoesNotExist, template


def load_template_source(template):
    """
    Get template source code.
    """
    path = get_template_path(template)
    return codecs.open(path, 'r', 'utf-8').read()


def get_options_for_path(path):
    """
    return a list of default settings for this template.
    (find app, and return settings for the matching app.)
    """
    result = get_options_for_everyone()
    for app in settings.INSTALLED_APPS:
        dir = os.path.normpath(os.path.join(_get_path_form_app(app), 'templates')).lower()
        if os.path.normpath(path).lower().startswith(dir):
            result += get_options_for_app(app)

        # NOTE: somehow, we get lowercase paths from the template origin in
        # Windows, so convert both paths to lowercase before comparing.

    # Disable all HTML extensions if the template name does not end with .html
    # (Can still be overriden in the templates.)
    if path and not path.endswith('.html'):
        result = list(result) + ['no-html']

    return result

def get_options_for_everyone():
    """
    return a list of default settings valid for all applications.

    -- settings.py --
    TEMPLATE_PREPROCESSOR_OPTIONS = {
            # Default
            '*', ('html',),
    }
    """
    # Read settings.py
    options = getattr(settings, 'TEMPLATE_PREPROCESSOR_OPTIONS', { })
    result = []

    # Possible fallback: '*'
    if '*' in options:
        result += list(options['*'])

    return result


def get_options_for_app(app):
    """
    return a list of default settings for this application.
    (e.g. Some applications, like the django admin are not HTML compliant with
    this validator.)

    -- settings.py --
    TEMPLATE_PREPROCESSOR_OPTIONS = {
            # Default
            '*', ('html',),
            ('django.contrib.admin', 'django.contrib.admindocs', 'debug_toolbar'): ('no-html',),
    }
    """
    # Read settings.py
    options = getattr(settings, 'TEMPLATE_PREPROCESSOR_OPTIONS', { })
    result = []

    # Look for any configuration entry which contains this appname
    for k, v in options.iteritems():
        if app == k or app in k:
            if isinstance(v, tuple):
                result += list(v)
            else:
                raise Exception('Configuration error in settings.TEMPLATE_PREPROCESSOR_OPTIONS')

    return result


def execute_precompile_command():
    """
    Execute precompile command before compiling templates.
    For instance, for compiling CSCC files to CSS first.

    -- settings.py --
    TEMPLATE_PREPROCESSOR_PRECOMPILE_COMMAND = 'cd %s; compass compile -c config.rb -q' % ('....path...'))
    """
    command = getattr(settings, 'TEMPLATE_PREPROCESSOR_PRECOMPILE_COMMAND', None)

    if command:
        import os
        os.system(command)

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

from django.conf import settings

from template_preprocessor.core import compile
from template_preprocessor.template.loaders import _Base as BaseLoader
from template_preprocessor.core.context import Context


class HelperLoader(BaseLoader):

    options = ()
    context_class = Context

    def __init__(self, loaders=settings.TEMPLATE_LOADERS):
        super(HelperLoader, self).__init__(loaders=loaders)

    def compile_template(self, original_source, template_dirs=None):
        template_source, context = compile(
            original_source,
            loader = lambda path: self.find_template(path)[0],
            options=self.options,
            context_class=self.context_class
        )

        return template_source


def compile_source(source):
    return HelperLoader().compile_template(source)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test_project.sqlite',
    },
}

TIME_ZONE = 'America/Chicago'

PROJECT_DIR = os.path.dirname(__file__) + '/'

LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True

LANGUAGES = (
    ('en', 'EN'),
    ('fr', 'FR'),
    ('nl', 'NL'),
)

MEDIA_ROOT = PROJECT_DIR + 'media/'
MEDIA_URL = '/media/'
STATIC_ROOT = PROJECT_DIR + 'static/'
STATIC_URL = '/static/'


# Template preprocessor settings
TEMPLATE_CACHE_DIR = PROJECT_DIR + 'templates/cache/'
MEDIA_CACHE_DIR = MEDIA_ROOT + 'cache/'
MEDIA_CACHE_URL = MEDIA_URL + 'cache/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


SECRET_KEY = '7wq0^b4+mx39f%ly5ty#4nk9pwdkh%63u1!_h-x@%!hos3f9%b'


TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'template_preprocessor',
    'testapp',
    'otherapp',
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = test_include
# -*- coding: utf-8 -*-

from unittest import TestCase
from template_preprocessor.core.lexer import CompileException

from test_project.helpers import compile_source

class TestTemplateInclude(TestCase):

    def test_should_include_template_markup(self):
        compiled = compile_source('{% include "include/include_template.html" %}').strip()
        self.assertEqual(compiled, 'include template')

    def test_include_a_dynamic_variable_should_not_include_template_markup(self):
        compiled = compile_source('{% include dynamic_template %}').strip()
        self.assertEqual(compiled, '{%include dynamic_template%}')

    def test_should_raise_a_compileException_when_template_doesnt_exists(self):
        self.assertRaises(CompileException, compile_source, '{% include "include/notfound_template.html" %}')

########NEW FILE########
__FILENAME__ = test_inheritance
# -*- coding: utf-8 -*-

from unittest import TestCase
from template_preprocessor.core.lexer import CompileException

from test_project.helpers import compile_source


class TestSimpleTemplateInheritance(TestCase):
    
    def test_should_expand_one_level_inheritance(self):
        compiled = compile_source('{% extends "inheritance/base.html" %}').strip()
        self.assertEqual(compiled, 'BASE TEMPLATE')

    def test_should_expand_two_level_inheritance(self):
        compiled = compile_source('{% extends "inheritance/level-one.html" %}').strip()
        self.assertEqual(compiled, 'BASE TEMPLATE')

    def test_should_expand_app_template_inheriting_from_template_dirs(self):
        compiled = compile_source('{% extends "inheritance/inherit-from-template-dirs.html" %}').strip()
        self.assertEqual(compiled, 'BASE TEMPLATE')


class TestSimpleTemplateInheritanceWithBlocks(TestCase):
    
    def test_should_expand_block_from_base_template(self):
        template = '{% extends "blocks/base.html" %}'
        compiled = compile_source(template).strip()
        self.assertEqual(compiled, 'BASE BLOCK')

    def test_should_keep_overriden_block(self):
        template = '{% extends "blocks/base.html" %}{% block base_block %}OVERRIDEN{% endblock %}'
        compiled = compile_source(template).strip()
        self.assertEqual(compiled, 'OVERRIDEN')

    def test_should_keep_overriden_block_plus_super(self):
        template = '''
            {% extends "blocks/base.html" %}
            {% block base_block %}{{ block.super }} + OVERRIDEN{% endblock %}
        '''
        compiled = compile_source(template).strip()
        self.assertEqual(compiled, 'BASE BLOCK + OVERRIDEN')

    def test_extends_template_with_dynamic_variable_should_return_an_exception(self):
        template = '{% extends dynamic_template %}'
        self.assertRaises(CompileException, compile_source, template)


########NEW FILE########
__FILENAME__ = test_load
# -*- coding: utf-8 -*-

from unittest import TestCase
from template_preprocessor.core import compile
from template_preprocessor.core.context import Context

class TestTemplateLoad(TestCase):

	def test_load_url_from_future(self):
		compiled, context = compile('{% load url from future %}')
		compiled = compiled.strip()
		self.assertEqual(compiled, '{% load url from future%}')

########NEW FILE########
__FILENAME__ = test_template_iterator

import os
from django.utils.unittest import TestCase
from django.conf import settings
from template_preprocessor.utils import template_iterator


class TemplateIteratorTestCase(TestCase):

    def setUp(self):
        self.template_paths = {}
        self.app_template_dir = os.path.join(settings.PROJECT_DIR, 'testapp')
        for dir, template_path in template_iterator():
            if template_path not in self.template_paths:
                self.template_paths[template_path] = [dir]
            else:
                self.template_paths[template_path].append(template_path)
        self.app_template_name = 'app-template.html'
        self.project_template_name = 'project-template.html'

    def test_prefer_templatedirs_than_app_templates(self):
        self.assertListEqual([settings.TEMPLATE_DIRS[0]],
                             self.template_paths[self.project_template_name])

    def test_use_the_app_order_returning_the_first_template_app(self):
        self.assertListEqual([os.path.join(self.app_template_dir, 'templates')],
                             self.template_paths[self.app_template_name])

    def test_must_return_one_entry_from_both_project_and_app_which_have_the_same_template(self):
        self.assertEqual(1,
                         len(self.template_paths[self.project_template_name]))

    def test_must_return_one_entry_when_two_apps_have_the_same_template(self):
        self.assertEqual(1,
                         len(self.template_paths[self.app_template_name]))

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns

urlpatterns = patterns('',)

########NEW FILE########
