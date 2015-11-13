__FILENAME__ = models

########NEW FILE########
__FILENAME__ = spurl
import re
from django.conf import settings
from django.utils.html import escape
from django.utils.encoding import smart_str
from urlobject import URLObject
from urlobject.query_string import QueryString
from django.template import StringOrigin, Lexer, Parser
from django.template.defaulttags import kwarg_re
from django.template import Template, Library, Node, TemplateSyntaxError


register = Library()

TRUE_RE = re.compile(r'^(true|on)$', flags=re.IGNORECASE)


def convert_to_boolean(string_or_boolean):
    if isinstance(string_or_boolean, bool):
        return string_or_boolean
    if isinstance(string_or_boolean, basestring):
        return bool(TRUE_RE.match(string_or_boolean))


class SpurlURLBuilder(object):

    def __init__(self, args, context, tags, filters):
        self.args = args
        self.context = context
        self.tags = tags
        self.filters = filters
        self.autoescape = self.context.autoescape
        self.url = URLObject()

    def build(self):
        for argument, value in self.args:
            self.handle_argument(argument, value)

        self.set_sensible_defaults()

        url = unicode(self.url)

        if self.autoescape:
            url = escape(url)

        return url

    def handle_argument(self, argument, value):
        argument = smart_str(argument, 'ascii')
        handler_name = 'handle_%s' % argument
        handler = getattr(self, handler_name, None)

        if handler is not None:
            value = value.resolve(self.context)
            handler(value)

    def handle_base(self, value):
        base = self.prepare_value(value)
        self.url = URLObject(base)

    def handle_secure(self, value):
        is_secure = convert_to_boolean(value)
        scheme = 'https' if is_secure else 'http'
        self.url = self.url.with_scheme(scheme)

    def handle_query(self, value):
        query = self.prepare_value(value)
        if isinstance(query, dict):
            query = QueryString().set_params(**query)
        self.url = self.url.with_query(QueryString(query))

    def handle_query_from(self, value):
        url = URLObject(value)
        self.url = self.url.with_query(url.query)

    def handle_add_query(self, value):
        query_to_add = self.prepare_value(value)
        if isinstance(query_to_add, basestring):
            query_to_add = QueryString(query_to_add).dict
        self.url = self.url.add_query_params(**query_to_add)

    def handle_add_query_from(self, value):
        url = URLObject(value)
        self.url = self.url.add_query_params(**url.query.dict)

    def handle_set_query(self, value):
        query_to_set = self.prepare_value(value)
        if isinstance(query_to_set, basestring):
            query_to_set = QueryString(query_to_set).dict
        self.url = self.url.set_query_params(**query_to_set)

    def handle_set_query_from(self, value):
        url = URLObject(value)
        self.url = self.url.set_query_params(**url.query.dict)

    def handle_remove_query_param(self, value):
        self.url = self.url.del_query_param(value)

    def handle_toggle_query(self, value):
        query_to_toggle = self.prepare_value(value)
        if isinstance(query_to_toggle, basestring):
            query_to_toggle = QueryString(query_to_toggle).dict
        current_query = self.url.query.dict
        for key, value in query_to_toggle.items():
            if isinstance(value, basestring):
                value = value.split(',')
            first, second = value
            if key in current_query and first in current_query[key]:
                self.url = self.url.set_query_param(key, second)
            else:
                self.url = self.url.set_query_param(key, first)

    def handle_scheme(self, value):
        self.url = self.url.with_scheme(value)

    def handle_scheme_from(self, value):
        url = URLObject(value)
        self.url = self.url.with_scheme(url.scheme)

    def handle_host(self, value):
        host = self.prepare_value(value)
        self.url = self.url.with_hostname(host)

    def handle_host_from(self, value):
        url = URLObject(value)
        self.url = self.url.with_hostname(url.hostname)

    def handle_path(self, value):
        path = self.prepare_value(value)
        self.url = self.url.with_path(path)

    def handle_path_from(self, value):
        url = URLObject(value)
        self.url = self.url.with_path(url.path)

    def handle_add_path(self, value):
        path_to_add = self.prepare_value(value)
        self.url = self.url.add_path(path_to_add)

    def handle_add_path_from(self, value):
        url = URLObject(value)
        path_to_add = url.path
        if path_to_add.startswith('/'):
            path_to_add = path_to_add[1:]
        self.url = self.url.add_path(path_to_add)

    def handle_fragment(self, value):
        fragment = self.prepare_value(value)
        self.url = self.url.with_fragment(fragment)

    def handle_fragment_from(self, value):
        url = URLObject(value)
        self.url = self.url.with_fragment(url.fragment)

    def handle_port(self, value):
        self.url = self.url.with_port(int(value))

    def handle_port_from(self, value):
        url = URLObject(value)
        self.url = self.url.with_port(url.port)

    def handle_autoescape(self, value):
        self.autoescape = convert_to_boolean(value)

    def set_sensible_defaults(self):
        if self.url.hostname and not self.url.scheme:
            self.url = self.url.with_scheme('http')

    def prepare_value(self, value):
        """Prepare a value by unescaping embedded template tags
        and rendering through Django's template system"""
        if isinstance(value, basestring):
            value = self.unescape_tags(value)
            value = self.render_template(value)
        return value

    def unescape_tags(self, template_string):
        """Spurl allows the use of templatetags inside templatetags, if
        the inner templatetags are escaped - {\% and %\}"""
        return template_string.replace('{\%', '{%').replace('%\}', '%}')

    def compile_string(self, template_string, origin):
        """Re-implementation of django.template.base.compile_string
        that takes into account the tags and filter of the parser
        that rendered the parent template"""
        if settings.TEMPLATE_DEBUG:
            from django.template.debug import DebugLexer, DebugParser
            lexer_class, parser_class = DebugLexer, DebugParser
        else:
            lexer_class, parser_class = Lexer, Parser
        lexer = lexer_class(template_string, origin)
        parser = parser_class(lexer.tokenize())

        # Attach the tags and filters from the parent parser
        parser.tags = self.tags
        parser.filters = self.filters

        return parser.parse()

    def render_template(self, template_string):
        """Used to render an "inner" template, ie one which
        is passed as an argument to spurl"""
        original_autoescape = self.context.autoescape
        self.context.autoescape = False

        template = Template('')
        if settings.TEMPLATE_DEBUG:
            origin = StringOrigin(template_string)
        else:
            origin = None

        template.nodelist = self.compile_string(template_string, origin)

        rendered = template.render(self.context)
        self.context.autoescape = original_autoescape
        return rendered


class SpurlNode(Node):

    def __init__(self, args, tags, filters, asvar=None):
        self.args = args
        self.asvar = asvar
        self.tags = tags
        self.filters = filters

    def render(self, context):
        builder = SpurlURLBuilder(self.args, context, self.tags, self.filters)
        url = builder.build()

        if self.asvar:
            context[self.asvar] = url
            return ''

        return url


@register.tag
def spurl(parser, token):
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'spurl' takes at least one argument")

    args = []
    asvar = None
    bits = bits[1:]

    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]

    for bit in bits:
        name, value = kwarg_re.match(bit).groups()
        if not (name and value):
            raise TemplateSyntaxError("Malformed arguments to spurl tag")
        args.append((name, parser.compile_filter(value)))
    return SpurlNode(args, parser.tags, parser.filters, asvar)

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse
from django.template import Template, Context, loader, TemplateSyntaxError
from .templatetags.spurl import convert_to_boolean
import nose

# This file acts as a urlconf
urlpatterns = patterns('',
    url('^test/$', lambda r: HttpResponse('ok'), name='test')
)

# bootstrap django
settings.configure(
    ROOT_URLCONF='spurl.tests',
    INSTALLED_APPS=['spurl.tests'],
)

# add spurl to builtin tags
loader.add_to_builtins('spurl.templatetags.spurl')

def render(template_string, dictionary=None, autoescape=False):
    """
    Render a template from the supplied string, with optional context data.

    This differs from Django's normal template system in that autoescaping
    is disabled by default. This is simply to make the tests below easier
    to read and write. You can re-enable the default behavior by passing True
    as the value of the autoescape parameter
    """
    context = Context(dictionary, autoescape=autoescape)
    return Template(template_string).render(context)

def test_convert_argument_value_to_boolean():
    assert convert_to_boolean(True) is True
    assert convert_to_boolean(False) is False
    assert convert_to_boolean("True") is True
    assert convert_to_boolean("true") is True
    assert convert_to_boolean("On") is True
    assert convert_to_boolean("on") is True
    assert convert_to_boolean("False") is False
    assert convert_to_boolean("false") is False
    assert convert_to_boolean("Off") is False
    assert convert_to_boolean("off") is False
    assert convert_to_boolean("randomstring") is False

@nose.tools.raises(TemplateSyntaxError)
def test_noargs_raises_exception():
    render("""{% spurl %}""")

@nose.tools.raises(TemplateSyntaxError)
def test_malformed_args_raises_exception():
    render("""{% spurl something %}""")

def test_passthrough():
    template = """{% spurl base="http://www.google.com" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com'

def test_url_in_variable():
    template = """{% spurl base=myurl %}"""
    data = {'myurl': 'http://www.google.com'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com'

def test_make_secure():
    template = """{% spurl base="http://www.google.com" secure="True" %}"""
    rendered = render(template)
    assert rendered == 'https://www.google.com'

def test_make_secure_with_variable():
    template = """{% spurl base=myurl secure=is_secure %}"""
    data = {'myurl': 'http://www.google.com', 'is_secure': True}
    rendered = render(template, data)
    assert rendered == 'https://www.google.com'

def test_make_insecure():
    template = """{% spurl base="https://www.google.com" secure="False" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com'

def test_make_insecure_with_variable():
    template = """{% spurl base=myurl secure=is_secure %}"""
    data = {'myurl': 'https://www.google.com', 'is_secure': False}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com'

def test_set_query_from_string():
    template = """{% spurl base="http://www.google.com" query="foo=bar&bar=foo" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com?foo=bar&bar=foo'

def test_set_query_from_string_with_variable():
    template = """{% spurl base=myurl query=myquery %}"""
    data = {'myurl': 'http://www.google.com', 'myquery': 'foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com?foo=bar&bar=foo'

def test_set_query_from_dict_with_variable():
    template = """{% spurl base=myurl query=myquery %}"""
    data = {'myurl': 'http://www.google.com', 'myquery': {'foo': 'bar', 'bar': 'foo'}}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com?foo=bar&bar=foo'

def test_set_query_from_template_variables():
    template = """{% spurl base=myurl query="foo={{ first_var }}&bar={{ second_var }}" %}"""
    data = {'myurl': 'http://www.google.com', 'first_var': 'bar', 'second_var': 'baz'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com?foo=bar&bar=baz'

def test_set_query_from_template_variables_not_double_escaped():
    template = """{% spurl base="http://www.google.com" query="{{ query }}" %}"""
    data = {'query': 'foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com?foo=bar&bar=foo'

def test_set_query_removes_existing_query():
    template = """{% spurl base="http://www.google.com?something=somethingelse" query="foo=bar&bar=foo" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com?foo=bar&bar=foo'

def test_query_from():
    template = """{% spurl base="http://www.google.com/" query_from=url %}"""
    data = {'url': 'http://example.com/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=bar&bar=foo'

def test_add_to_query_from_string():
    template = """{% spurl base="http://www.google.com?something=somethingelse" add_query="foo=bar&bar=foo" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com?something=somethingelse&foo=bar&bar=foo'

def test_add_to_query_from_dict_with_variable():
    template = """{% spurl base=myurl add_query=myquery %}"""
    data = {'myurl': 'http://www.google.com?something=somethingelse', 'myquery': {'foo': 'bar', 'bar': 'foo'}}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com?something=somethingelse&foo=bar&bar=foo'

def test_multiple_add_query():
    template = """{% spurl base="http://www.google.com/" add_query="foo=bar" add_query="bar=baz" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/?foo=bar&bar=baz'

def test_add_to_query_from_template_variables():
    template = """{% spurl base="http://www.google.com/?foo=bar" add_query="bar={{ var }}" %}"""
    data = {'var': 'baz'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=bar&bar=baz'

def test_add_query_from():
    template = """{% spurl base="http://www.google.com/?bla=bla&flub=flub" add_query_from=url %}"""
    data = {'url': 'http://example.com/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?bla=bla&flub=flub&foo=bar&bar=foo'

def test_set_query_param_from_string():
    template = """{% spurl base="http://www.google.com?something=somethingelse" set_query="something=foo&somethingelse=bar" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com?somethingelse=bar&something=foo'

def test_set_query_param_from_dict_with_variable():
    template = """{% spurl base=myurl set_query=myquery %}"""
    data = {'myurl': 'http://www.google.com?something=somethingelse', 'myquery': {'something': 'foo', 'somethingelse': 'bar'}}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com?somethingelse=bar&something=foo'

def test_toggle_query():
    template = """{% spurl base="http://www.google.com/?foo=bar" toggle_query="bar=first,second" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/?foo=bar&bar=first'

    template = """{% spurl base="http://www.google.com/?foo=bar&bar=first" toggle_query="bar=first,second" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/?foo=bar&bar=second'

    template = """{% spurl base="http://www.google.com/?foo=bar&bar=second" toggle_query="bar=first,second" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/?foo=bar&bar=first'

    template = """{% spurl base="http://www.google.com/?foo=bar&bar=first" toggle_query=to_toggle %}"""
    data = {'to_toggle': {'bar': ('first', 'second')}}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=bar&bar=second'

    template = """{% spurl base="http://www.google.com/?foo=bar&bar=second" toggle_query=to_toggle %}"""
    data = {'to_toggle': {'bar': ('first', 'second')}}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=bar&bar=first'

def test_multiple_set_query():
    template = """{% spurl base="http://www.google.com/?foo=test" set_query="foo=bar" set_query="bar=baz" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/?foo=bar&bar=baz'

def test_set_query_param_from_template_variables():
    template = """{% spurl base="http://www.google.com/?foo=bar" set_query="foo={{ var }}" %}"""
    data = {'var': 'baz'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=baz'

def test_empty_parameters_preserved():
    template = """{% spurl base="http://www.google.com/?foo=bar" set_query="bar={{ emptyvar }}" %}"""
    data = {} # does not contain and "emptyvar" key
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=bar&bar='

def test_none_values_are_removed_when_setting_query():
    template = """{% spurl base="http://www.google.com/?foo=bar" set_query="bar={{ nonevar|default_if_none:'' }}" %}"""
    data = {'nonevar': None}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=bar&bar='

def test_set_query_from():
    template = """{% spurl base="http://www.google.com/?bla=bla&foo=something" set_query_from=url %}"""
    data = {'url': 'http://example.com/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?bla=bla&foo=bar&bar=foo'

def test_none_values_are_removed_when_adding_query():
    template = """{% spurl base="http://www.google.com/?foo=bar" add_query="bar={{ nonevar|default_if_none:'' }}" %}"""
    data = {'nonevar': None}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?foo=bar&bar='

def test_remove_from_query():
    template = """{% spurl base="http://www.google.com/?foo=bar&bar=baz" remove_query_param="foo" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/?bar=baz'

def test_remove_multiple_params():
    template = """{% spurl base="http://www.google.com/?foo=bar&bar=baz" remove_query_param="foo" remove_query_param="bar" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/'

def test_remove_param_from_template_variable():
    template = """{% spurl base="http://www.google.com/?foo=bar&bar=baz" remove_query_param=foo remove_query_param=bar %}"""
    data = {'foo': 'foo', 'bar': 'bar'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/'

def test_override_scheme():
    template = """{% spurl base="http://google.com" scheme="ftp" %}"""
    rendered = render(template)
    assert rendered == 'ftp://google.com'

def test_scheme_from():
    template = """{% spurl base="http://www.google.com/?bla=bla&foo=bar" scheme_from=url %}"""
    data = {'url': 'https://example.com/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'https://www.google.com/?bla=bla&foo=bar'

def test_override_host():
    template = """{% spurl base="http://www.google.com/some/path/" host="www.example.com" %}"""
    rendered = render(template)
    assert rendered == 'http://www.example.com/some/path/'

def test_host_from():
    template = """{% spurl base="http://www.google.com/?bla=bla&foo=bar" host_from=url %}"""
    data = {'url': 'https://example.com/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://example.com/?bla=bla&foo=bar'

def test_override_path():
    template = """{% spurl base="http://www.google.com/some/path/" path="/another/different/one/" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/another/different/one/'

def test_path_from():
    template = """{% spurl base="http://www.google.com/original/?bla=bla&foo=bar" path_from=url %}"""
    data = {'url': 'https://example.com/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/some/path/?bla=bla&foo=bar'

def test_add_path():
    template = """{% spurl base="http://www.google.com/some/path/" add_path="another/" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/some/path/another/'

def test_multiple_add_path():
    template = """{% spurl base="http://www.google.com/" add_path="some" add_path="another/" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/some/another/'

def test_multiple_add_path_from_template_variables():
    """Usage example for building media urls"""
    template = """{% spurl base=STATIC_URL add_path="javascript" add_path="lib" add_path="jquery.js" %}"""
    data = {'STATIC_URL': 'http://cdn.example.com'}
    rendered = render(template, data)
    assert rendered == 'http://cdn.example.com/javascript/lib/jquery.js'

def test_add_path_from():
    template = """{% spurl base="http://www.google.com/original/?bla=bla&foo=bar" add_path_from=url %}"""
    data = {'url': 'https://example.com/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/original/some/path/?bla=bla&foo=bar'

def test_override_fragment():
    template = """{% spurl base="http://www.google.com/#somefragment" fragment="someotherfragment" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/#someotherfragment'

def test_fragment_from():
    template = """{% spurl base="http://www.google.com/?bla=bla&foo=bar#fragment" fragment_from=url %}"""
    data = {'url': 'https://example.com/some/path/?foo=bar&bar=foo#newfragment'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com/?bla=bla&foo=bar#newfragment'

def test_override_port():
    template = """{% spurl base="http://www.google.com:80" port="8080" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com:8080'

def test_port_from():
    template = """{% spurl base="http://www.google.com:8000/?bla=bla&foo=bar" port_from=url %}"""
    data = {'url': 'https://example.com:8888/some/path/?foo=bar&bar=foo'}
    rendered = render(template, data)
    assert rendered == 'http://www.google.com:8888/?bla=bla&foo=bar'

def test_build_complete_url():
    template = """{% spurl scheme="http" host="www.google.com" path="/some/path/" port="8080" fragment="somefragment" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com:8080/some/path/#somefragment'

def test_sensible_defaults():
    template = """{% spurl path="/some/path/" %}"""
    rendered = render(template)
    assert rendered == '/some/path/'

    template = """{% spurl path="/some/path/" host="www.google.com" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/some/path/'

def test_autoescaping():
    template = """{% spurl base="http://www.google.com" query="a=b" add_query="c=d" add_query="e=f" fragment="frag" %}"""
    rendered = render(template, autoescape=True) # Ordinarily, templates will be autoescaped by default
    assert rendered == 'http://www.google.com?a=b&amp;c=d&amp;e=f#frag'

def test_disable_autoescaping_with_parameter():
    template = """{% spurl base="http://www.google.com" query="a=b" add_query="c=d" autoescape="False" %}"""
    rendered = render(template, autoescape=True)
    assert rendered == 'http://www.google.com?a=b&c=d'

def test_url_as_template_variable():
    template = """{% spurl base="http://www.google.com" as foo %}The url is {{ foo }}"""
    rendered = render(template)
    assert rendered == 'The url is http://www.google.com'

def test_reversing_inside_spurl_tag():
    template = """{% load url from future %}{% spurl base="http://www.google.com/" path="{\% url 'test' %\}" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/test/'

    template = """{% load url from future %}{% spurl base="http://www.google.com/" query="next={\% url 'test' %\}" %}"""
    rendered = render(template)
    assert rendered == 'http://www.google.com/?next=/test/'

def test_xzibit():
    template = """Yo dawg, the URL is: {% spurl base="http://www.google.com/" query="foo={\% spurl base='http://another.com' secure='true' %\}" %}"""
    rendered = render(template)
    assert rendered == 'Yo dawg, the URL is: http://www.google.com/?foo=https://another.com'

########NEW FILE########
