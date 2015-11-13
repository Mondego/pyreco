__FILENAME__ = utils
import re

try:
    from hashlib import md5
except ImportError:
    import md5


from django.db.models.manager import Manager
from django.utils.encoding import smart_str


def clean_cache_key(key):
    '''Replace spaces with '-' and hash if length is greater than 250.'''

    #logic below borrowed from http://richwklein.com/2009/08/04/improving-django-cache-part-ii/ 
    cache_key = re.sub(r'\s+', '-', key)
    cache_key = smart_str(cache_key)

    if len(cache_key) > 250:
        m = md5()
        m.update(cache_key)
        cache_key = cache_key[:200] + '-' + m.hexdigest()

    return cache_key

def create_cache_key(klass, field=None, field_value=None):
    '''
    Helper to generate standard cache keys.

    Concepts borrowed from mmalone's django-caching:
    http://github.com/mmalone/django-caching/blob/ef7dd47e9beff39496e6a28ae129bae1b5f9ed71/app/managers.py

    Required Arguments
    ------------------
        'klass'
            Model or Manager

        'field'
            string, the specific Model field name used to create a more
            specific cache key. If you specify a field, it is used for the
            lookup to grab the value.

         'field_value'
            value, unique value used to generate a distinct key. Often
            this will be the ID, slug, name, etc.

            *Note: could be optimized/restricted to pk lookup only

    Returns
    -------
        'key'
            The key name.

    Example
    --------
        >> from blog.models import Post
        >> slug_val = 'test-foo'
        >> mykey = create_cache_key(Post, 'slug', slug_val)
        >> obj = cache.get(mykey)
    '''

    key_model = "%s.%s.%s:%s"
    key = ''

    if field and field_value:
        if isinstance(klass, Manager):
            key = key_model % (klass.model._meta.app_label, klass.model._meta.module_name, field, field_value)
        else:
            key = key_model % (klass._meta.app_label, klass._meta.module_name, field, field_value)

    if not key:
        raise Exception('Cache key cannot be empty.')

    return clean_cache_key(key)
########NEW FILE########
__FILENAME__ = awesome
import re
from django.conf import settings
from django.utils.encoding import smart_str

_END_BODY_RE = re.compile(r'<body([^<]*)>', re.IGNORECASE)
AWESOMENESS = '<div id="awesome" style="position: fixed; bottom: 10px; right: 15px; width: 200px; height: 60px; z-index: 9000;"><a href="http://djangopony.com/" class="ponybadge" border="0" title="Magic! Ponies! Django! Whee!"><img src="http://media.djangopony.com/img/small/badge.png" width="210" height="65" alt="ponybadge"></a></div>'

class AwesomeMiddleware(object):
    """
    Middleware that makes your django application awesome.

    Implement
    ---------
    Add to your middleware:

    'sugar.middleware.awesome.AwesomeMiddleware',

    """

    def __init__(self):
        self.is_awesome = True

        #yes, you can override with your own awesomeness.
        self.awesomeness = getattr(settings, 'AWESOMENESS', AWESOMENESS)

    def __process_awesome_response(self, request, response):
        """
        Handles rendering the awesome.

        Private access because not everyone method can be this awesome.

        """
        response.content = _END_BODY_RE.sub(smart_str('<body\\1>' + self.awesomeness), response.content)
        return response

    def process_response(self, request, response):
        """
        The out-of-the-box "process_response" method isn't awesome enough,
        so we hand it off to the private _process_awesome_response method which
        is obviously much more awesome than "process_response"

        """
        return self.__process_awesome_response(request, response)
########NEW FILE########
__FILENAME__ = debugging
from django.views.debug import technical_500_response
import sys
from django.conf import settings

class UserBasedExceptionMiddleware(object):
    """
    Source: http://ericholscher.com/blog/2008/nov/15/debugging-django-production-environments/

    Introduction
    ------------
    This is a pretty simple middleware that is crazy useful. When you throw this
    inside of your site, it will give you a normal Django error page if
    you're a superuser, or if your IP is in INTERNAL_IPS.

    Implement
    ---------
    Add to your middleware:

    'sugar.middleware.debugging.UserBasedExceptionMiddleware',

    """

    def process_exception(self, request, exception):
        if request.user.is_superuser or request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS:
            return technical_500_response(request, *sys.exc_info())
########NEW FILE########
__FILENAME__ = in_list
'''
From http://www.djangosnippets.org/snippets/177/#c196 by mikeivanov
'''
from django import template
register = template.Library()

@register.filter
def in_list(value,arg):
    '''
    Usage
    {% if value|in_list:list %}
    {% endif %}
    '''
    return value in arg

########NEW FILE########
__FILENAME__ = media
from django.template import Library, Node
from django.template.loader import render_to_string
from django.contrib.sites.models import Site    
from django.conf import settings
import os, urlparse
     
register = Library()
     
def _absolute_url(url):
    if url.startswith('http://') or url.startswith('https://'):
        return url
    domain = Site.objects.get_current().domain
    return 'http://%s%s' % (domain, url)

@register.simple_tag
def media(filename, flags=''):
    """
     Autor: http://softwaremaniacs.org/blog/2009/03/22/media-tag/
    
    {% load media %}
    <link rel="stylesheet" href="{% media "css/style.css" %}">
    
    {% media "css/style.css" %}                <!-- ...style.css?123456789 -->
    {% media "css/style.css" "no-timestamp" %} <!-- ...style.css -->
    {% media "images/edit.png" "timestamp" %}  <!-- ...edit.png?123456789 -->
    {% media "images/edit.png" "absolute" %} <!-- http://example.com/media/edit.png -->
    """
    flags = set(f.strip() for f in flags.split(','))
    url = urlparse.urljoin(settings.MEDIA_URL, filename)
    if 'absolute' in flags:
        url = _absolute_url(url)
    if (filename.endswith('.css') or filename.endswith('.js')) and 'no-timestamp' not in flags or \
       'timestamp' in flags:
        fullname = os.path.join(settings.MEDIA_ROOT, filename)
        if os.path.exists(fullname):
            url += '?%d' % os.path.getmtime(fullname)
    return url
########NEW FILE########
__FILENAME__ = pdb_debug
"""
Source: http://www.djangosnippets.org/snippets/1550/ 

Notes
=====
This allows you to set up a breakpoint anywhere in your template code, 
by simply writing {% pdb_debug %}.

You can then access your context variables using context.get(..) at the pdb 
prompt. Optionally, install the ipdb package for colors, completion, and more (easy_install ipdb).

"""

from django.template import Library, Node

register = Library()

try:
    import ipdb as pdb
except ImportError:   
    import pdb

class PdbNode(Node):
    def render(self, context):
        pdb.set_trace()
        return ''

@register.tag
def pdb_debug(parser, token):
    return PdbNode()

########NEW FILE########
__FILENAME__ = pygment_tags
import re 
import pygments 
from django import template 
from pygments import lexers 
from pygments import formatters 
from BeautifulSoup import BeautifulSoup 
 
register = template.Library() 
regex = re.compile(r'<code(.*?)>(.*?)</code>', re.DOTALL) 
 
@register.filter(name='pygmentize') 
def pygmentize(value): 
    '''
    Finds all <code class="python"></code> blocks in a text block and replaces it with 
    pygments-highlighted html semantics. It relies that you provide the format of the 
    input as class attribute.

    Inspiration:  http://www.djangosnippets.org/snippets/25/
    Updated by: Samualy Clay

    Example
    -------
    
    {% post.body|pygmentize %}

    '''
    last_end = 0 
    to_return = '' 
    found = 0 
    for match_obj in regex.finditer(value): 
        code_class = match_obj.group(1) 
        code_string = match_obj.group(2) 
        if code_class.find('class'): 
            language = re.split(r'"|\'', code_class)[1] 
            lexer = lexers.get_lexer_by_name(language) 
        else: 
            try: 
                lexer = lexers.guess_lexer(str(code)) 
            except ValueError: 
                lexer = lexers.PythonLexer() 
        pygmented_string = pygments.highlight(code_string, lexer, formatters.HtmlFormatter()) 
        to_return = to_return + value[last_end:match_obj.start(0)] + pygmented_string 
        last_end = match_obj.end(2) 
        found = found + 1 
    to_return = to_return + value[last_end:] 
    return to_return
########NEW FILE########
__FILENAME__ = querystring_tags
"""
Query String manipulation filters
"""

from django import template
from django.http import QueryDict
from django.utils.translation import ugettext as _

register = template.Library()


class QueryStringAlterer(template.Node):
    """
    Query String alteration template tag

    Receives a query string (either text or a QueryDict such as request.GET)
    and a list of changes to apply. The result will be returned as text query
    string, allowing use like this::

        <a href="?{% qs_alter request.GET type=object.type %}">{{ label }}</a>

    There are two available alterations:

        Assignment:

            name=var

        Deletion - removes the named parameter:

            delete:name

    Examples:

    Query string provided as QueryDict::

        {% qs_alter request.GET foo=bar %}
        {% qs_alter request.GET foo=bar baaz=quux %}
        {% qs_alter request.GET foo=bar baaz=quux delete:corge %}

    Query string provided as string::

        {% qs_alter "foo=baaz" foo=bar %}">
    """

    def __init__(self, base_qs, *args):
        self.base_qs = template.Variable(base_qs)
        self.args = args

    def render(self, context):
        base_qs = self.base_qs.resolve(context)

        if isinstance(base_qs, QueryDict):
            qs = base_qs.copy()
        else:
            qs = QueryDict(base_qs, mutable=True)

        for arg in self.args:
            if arg.startswith("delete:"):
                v = arg[7:]
                if v in qs:
                    del qs[v]
            else:
                k, v = arg.split("=", 2)
                qs[k] = template.Variable(v).resolve(context)

        return qs.urlencode()

    @classmethod
    def qs_alter_tag(cls, parser, token):
        try:
            bits = token.split_contents()
        except ValueError:
            raise template.TemplateSyntaxError(
                _('qs_alter requires at least two arguments: the initial query string and at least one alteration')
            )

        return QueryStringAlterer(bits[1], *bits[2:])

register.tag('qs_alter', QueryStringAlterer.qs_alter_tag)
########NEW FILE########
__FILENAME__ = smart_if
"""
Source: http://www.djangosnippets.org/snippets/1350/

A smarter {% if %} tag for django templates.

While retaining current Django functionality, it also handles equality,
greater than and less than operators. Some common case examples::

    {% if articles|length >= 5 %}...{% endif %}
    {% if "ifnotequal tag" != "beautiful" %}...{% endif %}
"""

import unittest
from django import template

register = template.Library()


#==============================================================================
# Calculation objects
#==============================================================================

class BaseCalc(object):
    def __init__(self, var1, var2=None, negate=False):
        self.var1 = var1
        self.var2 = var2
        self.negate = negate

    def resolve(self, context):
        try:
            var1, var2 = self.resolve_vars(context)
            outcome = self.calculate(var1, var2)
        except:
            outcome = False
        if self.negate:
            return not outcome
        return outcome

    def resolve_vars(self, context):
        var2 = self.var2 and self.var2.resolve(context)
        return self.var1.resolve(context), var2

    def calculate(self, var1, var2):
        raise NotImplementedError()


class Or(BaseCalc):
    def calculate(self, var1, var2):
        return var1 or var2


class And(BaseCalc):
    def calculate(self, var1, var2):
        return var1 and var2


class Equals(BaseCalc):
    def calculate(self, var1, var2):
        return var1 == var2


class Greater(BaseCalc):
    def calculate(self, var1, var2):
        return var1 > var2


class GreaterOrEqual(BaseCalc):
    def calculate(self, var1, var2):
        return var1 >= var2


class In(BaseCalc):
    def calculate(self, var1, var2):
        return var1 in var2


#==============================================================================
# Tests
#==============================================================================

class TestVar(object):
    """
    A basic self-resolvable object similar to a Django template variable. Used
    to assist with tests.
    """
    def __init__(self, value):
        self.value = value

    def resolve(self, context):
        return self.value


class SmartIfTests(unittest.TestCase):
    def setUp(self):
        self.true = TestVar(True)
        self.false = TestVar(False)
        self.high = TestVar(9000)
        self.low = TestVar(1)

    def assertCalc(self, calc, context=None):
        """
        Test a calculation is True, also checking the inverse "negate" case.
        """
        context = context or {}
        self.assert_(calc.resolve(context))
        calc.negate = not calc.negate
        self.assertFalse(calc.resolve(context))

    def assertCalcFalse(self, calc, context=None):
        """
        Test a calculation is False, also checking the inverse "negate" case.
        """
        context = context or {}
        self.assertFalse(calc.resolve(context))
        calc.negate = not calc.negate
        self.assert_(calc.resolve(context))

    def test_or(self):
        self.assertCalc(Or(self.true))
        self.assertCalcFalse(Or(self.false))
        self.assertCalc(Or(self.true, self.true))
        self.assertCalc(Or(self.true, self.false))
        self.assertCalc(Or(self.false, self.true))
        self.assertCalcFalse(Or(self.false, self.false))

    def test_and(self):
        self.assertCalc(And(self.true, self.true))
        self.assertCalcFalse(And(self.true, self.false))
        self.assertCalcFalse(And(self.false, self.true))
        self.assertCalcFalse(And(self.false, self.false))

    def test_equals(self):
        self.assertCalc(Equals(self.low, self.low))
        self.assertCalcFalse(Equals(self.low, self.high))

    def test_greater(self):
        self.assertCalc(Greater(self.high, self.low))
        self.assertCalcFalse(Greater(self.low, self.low))
        self.assertCalcFalse(Greater(self.low, self.high))

    def test_greater_or_equal(self):
        self.assertCalc(GreaterOrEqual(self.high, self.low))
        self.assertCalc(GreaterOrEqual(self.low, self.low))
        self.assertCalcFalse(GreaterOrEqual(self.low, self.high))

    def test_in(self):
        list_ = TestVar([1,2,3])
        invalid_list = TestVar(None)
        self.assertCalc(In(self.low, list_))
        self.assertCalcFalse(In(self.low, invalid_list))

    def test_parse_bits(self):
        var = IfParser([True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([False]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([False, 'or', True]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([False, 'and', True]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser(['not', False, 'and', 'not', False]).parse()
        self.assert_(var.resolve({}))

        var = IfParser(['not', 'not', True]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, '=', 1]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, 'not', '=', 1]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([1, 'not', 'not', '=', 1]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, '!=', 1]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([3, '>', 2]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([1, '<', 2]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([2, 'not', 'in', [2, 3]]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([1, 'or', 1, '=', 2]).parse()
        self.assert_(var.resolve({}))

    def test_boolean(self):
        var = IfParser([True, 'and', True, 'and', True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([False, 'or', False, 'or', True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([True, 'and', False, 'or', True]).parse()
        self.assert_(var.resolve({}))
        var = IfParser([False, 'or', True, 'and', True]).parse()
        self.assert_(var.resolve({}))

        var = IfParser([True, 'and', True, 'and', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'or', False, 'or', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'or', True, 'and', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'and', True, 'or', False]).parse()
        self.assertFalse(var.resolve({}))

    def test_invalid(self):
        self.assertRaises(ValueError, IfParser(['not']).parse)
        self.assertRaises(ValueError, IfParser(['==']).parse)
        self.assertRaises(ValueError, IfParser([1, 'in']).parse)
        self.assertRaises(ValueError, IfParser([1, '>', 'in']).parse)
        self.assertRaises(ValueError, IfParser([1, '==', 'not', 'not']).parse)
        self.assertRaises(ValueError, IfParser([1, 2]).parse)


OPERATORS = {
    '=': (Equals, True),
    '==': (Equals, True),
    '!=': (Equals, False),
    '>': (Greater, True),
    '>=': (GreaterOrEqual, True),
    '<=': (Greater, False),
    '<': (GreaterOrEqual, False),
    'or': (Or, True),
    'and': (And, True),
    'in': (In, True),
}
BOOL_OPERATORS = ('or', 'and')


class IfParser(object):
    error_class = ValueError

    def __init__(self, tokens):
        self.tokens = tokens

    def _get_tokens(self):
        return self._tokens

    def _set_tokens(self, tokens):
        self._tokens = tokens
        self.len = len(tokens)
        self.pos = 0

    tokens = property(_get_tokens, _set_tokens)

    def parse(self):
        if self.at_end():
            raise self.error_class('No variables provided.')
        var1 = self.get_bool_var()
        while not self.at_end():
            op, negate = self.get_operator()
            var2 = self.get_bool_var()
            var1 = op(var1, var2, negate=negate)
        return var1

    def get_token(self, eof_message=None, lookahead=False):
        negate = True
        token = None
        pos = self.pos
        while token is None or token == 'not':
            if pos >= self.len:
                if eof_message is None:
                    raise self.error_class()
                raise self.error_class(eof_message)
            token = self.tokens[pos]
            negate = not negate
            pos += 1
        if not lookahead:
            self.pos = pos
        return token, negate

    def at_end(self):
        return self.pos >= self.len

    def create_var(self, value):
        return TestVar(value)

    def get_bool_var(self):
        """
        Returns either a variable by itself or a non-boolean operation (such as
        ``x == 0`` or ``x < 0``).

        This is needed to keep correct precedence for boolean operations (i.e.
        ``x or x == 0`` should be ``x or (x == 0)``, not ``(x or x) == 0``).
        """
        var = self.get_var()
        if not self.at_end():
            op_token = self.get_token(lookahead=True)[0]
            if isinstance(op_token, basestring) and (op_token not in
                                                     BOOL_OPERATORS):
                op, negate = self.get_operator()
                return op(var, self.get_var(), negate=negate)
        return var

    def get_var(self):
        token, negate = self.get_token('Reached end of statement, still '
                                       'expecting a variable.')
        if isinstance(token, basestring) and token in OPERATORS:
            raise self.error_class('Expected variable, got operator (%s).' %
                                   token)
        var = self.create_var(token)
        if negate:
            return Or(var, negate=True)
        return var

    def get_operator(self):
        token, negate = self.get_token('Reached end of statement, still '
                                       'expecting an operator.')
        if not isinstance(token, basestring) or token not in OPERATORS:
            raise self.error_class('%s is not a valid operator.' % token)
        if self.at_end():
            raise self.error_class('No variable provided after "%s".' % token)
        op, true = OPERATORS[token]
        if not true:
            negate = not negate
        return op, negate


#==============================================================================
# Actual templatetag code.
#==============================================================================

class TemplateIfParser(IfParser):
    error_class = template.TemplateSyntaxError

    def __init__(self, parser, *args, **kwargs):
        self.template_parser = parser
        return super(TemplateIfParser, self).__init__(*args, **kwargs)

    def create_var(self, value):
        return self.template_parser.compile_filter(value)


class SmartIfNode(template.Node):
    def __init__(self, var, nodelist_true, nodelist_false=None):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.var = var

    def render(self, context):
        if self.var.resolve(context):
            return self.nodelist_true.render(context)
        if self.nodelist_false:
            return self.nodelist_false.render(context)
        return ''

    def __repr__(self):
        return "<Smart If node>"

    def __iter__(self):
        for node in self.nodelist_true:
            yield node
        if self.nodelist_false:
            for node in self.nodelist_false:
                yield node

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_true.get_nodes_by_type(nodetype))
        if self.nodelist_false:
            nodes.extend(self.nodelist_false.get_nodes_by_type(nodetype))
        return nodes


@register.tag('if')
def smart_if(parser, token):
    """
    A smarter {% if %} tag for django templates.

    While retaining current Django functionality, it also handles equality,
    greater than and less than operators. Some common case examples::

        {% if articles|length >= 5 %}...{% endif %}
        {% if "ifnotequal tag" != "beautiful" %}...{% endif %}

    Arguments and operators _must_ have a space between them, so
    ``{% if 1>2 %}`` is not a valid smart if tag.

    All supported operators are: ``or``, ``and``, ``in``, ``=`` (or ``==``),
    ``!=``, ``>``, ``>=``, ``<`` and ``<=``.
    """
    bits = token.split_contents()[1:]
    var = TemplateIfParser(parser, bits).parse()
    nodelist_true = parser.parse(('else', 'endif'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endif',))
        parser.delete_first_token()
    else:
        nodelist_false = None
    return SmartIfNode(var, nodelist_true, nodelist_false)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sugar_pagination
from django.core.paginator import Paginator
from django import template

register = template.Library()

class PaginatorNode(template.Node):
    """
    templatetag for paginating any iterable template variable (queryset, list, etc.)

    Assume that the query string provided has a key "page" containing the current page

    Usage:

        {% paginate list_of_documents request.GET %}
            <ul class="children">
            {% for doc in page.object_list %}
                <li>
                    <h2><a href="{{ doc.get_absolute_url }}">{{ doc.title }}</a></h2>
                    {{ doc.summary }}
                </li>
            {% endfor %}
            </ul>
        {% endpaginate %}
    """

    def __init__(self, nodelist, objects=None, query_string=None, page_size=10):
        self.nodelist = nodelist
        self.objects = template.Variable(objects)
        self.query_string = template.Variable(query_string)
        self.page_size = page_size

    def render(self, context):
        ctx = template.Context(context)

        objects = self.objects.resolve(ctx)
        query_string = self.query_string.resolve(ctx)

        paginator = Paginator(objects, self.page_size)

        page = 1
        if 'page' in query_string:
            try:
                page = int(query_string['page'])
            except ValueError:
                pass

        page = min(page, paginator.num_pages)

        ctx.update({
            "paginator":    paginator,
            "page_number":  page,
            "page":         paginator.page(page)
        })

        return self.nodelist.render(ctx)


    @classmethod
    def paginate_tag(cls, parser, token):
        args = token.contents.split()

        if not len(args) >= 3:
            raise template.TemplateSyntaxError, "%r tag must be called like this: {% paginate queryset_or_iterable query_string [page_size] %}" % args[0]

        nodelist = parser.parse(('endpaginate',))

        parser.delete_first_token()

        kwargs = {
            "objects": args[1],
            "query_string": args[2],
        }

        if len(args) > 3:
            kwargs['page_size'] = int(args[3])

        return PaginatorNode(nodelist, **kwargs)

register.tag("paginate", PaginatorNode.paginate_tag)
########NEW FILE########
__FILENAME__ = sugar_template_utils
from django import template

register = template.Library()

class RenderInlineNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        source = self.nodelist.render(context)
        t = template.Template(source)
        return t.render(context)

@register.tag
def render_inline(parser, token):
    """
    Renders its contents to a string using the current context, allowing you
    to process template variables embedded in things like model content,
    django-flatblocks, etc.

    Usage:

    {% render_inline %}
    Foo

    Bar

    {{ something_with_embedded_django_template }}

    Baaz

    {% end_render_inline %}

    """

    nodelist = parser.parse(('end_render_inline',))

    parser.delete_first_token()

    return RenderInlineNode(nodelist)
########NEW FILE########
__FILENAME__ = text_tags
import re

from django import template
from django.utils import text

register = template.Library()


@register.filter
def truncchar(value, arg):
    '''
    Truncate after a certain number of characters.

    Source: http://www.djangosnippets.org/snippets/194/

    Notes
    -----
    Super stripped down filter to truncate after a certain number of letters.

    Example
    -------

    {{ long_blurb|truncchar:20 }}

    The above will display 20 characters of the long blurb followed by "..."

    '''

    if len(value) < arg:
        return value
    else:
        return value[:arg] + '...'


@register.filter
def re_sub(string, args):
    """
    Provide a full regular expression replace on strings in templates

    Usage:

    {{ my_variable|re_sub:"/(foo|bar)/baaz/" }}
    """
    old = args.split(args[0])[1]
    new = args.split(args[0])[2]

    return re.sub(old, new, string)


@register.filter
def replace(string, args):
    """
    Provide a standard Python string replace in templates

    Usage:

    {{ my_variable|replace:"/foo/bar/" }}
    """
    old = args.split(args[0])[1]
    new = args.split(args[0])[2]

    return string.replace(old, new)


@register.filter
def truncatehtml(string, length):
    """
    Truncate the text to a certain length, honoring html.
    
    Usage:
    
    {{ my_variable|truncatehtml:250 }}
    
    """
    
    return text.truncate_html_words(string, length)

truncatehtml.is_safe = True
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from sugar.templatetags.pygment_tags import pygmentize

class PygmentTagsTestCase(TestCase):
    
    def testNone(self):
        text = u'This is a test'
        self.assertEqual(text, pygmentize(text))
    
    def testDefault(self):
        text = u'<code>a = 6</code>'
        self.assertNotEqual(text, pygmentize(text))
        
    def testElement(self):
        text = u'<pre>a = 6</pre>'
        self.assertNotEqual(text, pygmentize(text, 'pre'))
        self.assertEqual(text, pygmentize(text, 'pre:foo'))
        
    def testElementClass(self):
        text = u'<pre class="foo">a = 6</pre>'
        self.assertEqual(text, pygmentize(text, 'pre'))
        self.assertNotEqual(text, pygmentize(text, 'pre:foo'))
########NEW FILE########
__FILENAME__ = decorators
# -*- mode: python; coding: utf-8; -*-
from django.shortcuts import render_to_response
from django.template import RequestContext

from sugar.views.json import JsonResponse

def render_to(template):
    """
    Decorator for Django views that sends returned dict to render_to_response
    function with given template and RequestContext as context instance.

    If view doesn't return dict then decorator simply returns output.
    Additionally view can return two-tuple, which must contain dict as first
    element and string with template name as second. This string will
    override template name, given as parameter

    Parameters:

     - template: template name to use

    Examples::
      from sugar.views.decorators import render_to, ajax_request
      
      @render_to('some/tmpl.html')
      def view(request):
          if smth:
              return {'context': 'dict'}
          else:
              return {'context': 'dict'}, 'other/tmpl.html'

    (c) 2006-2009 Alexander Solovyov, new BSD License
    """
    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                return render_to_response(output[1], output[0],
                                          RequestContext(request))
            elif isinstance(output, dict):
                return render_to_response(template, output,
                                          RequestContext(request))
            return output
        wrapper.__name__ = func.__name__
        wrapper.__module__ = func.__module__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return renderer
    
def ajax_request(func):
    """
    Checks request.method is POST. Return error in JSON in other case.

    If view returned dict, returns JsonResponse with this dict as content.
    Examples::
    
    from sugar.views.decorators import render_to, ajax_request
    from sugar.views.helpers import get_object_or_404_ajax
    
    @ajax_request
    def comment_edit(request, object_id):
        comment = get_object_or_404_ajax(CommentNode, pk=object_id)
        if request.user != comment.user:
            return {'error': {'type': 403, 'message': 'Access denied'}}
        if 'get_body' in request.POST:
            return {'body': comment.body}
        elif 'body' in request.POST:
            comment.body = request.POST['body']
            comment.save()
            return {'body_html': comment.body_html}
        else:
            return {'error': {'type': 400, 'message': 'Bad request'}}
    
    
    """
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST':
            response = func(request, *args, **kwargs)
        else:
            response = {'error': {'type': 405,
                                  'message': 'Accepts only POST request'}}
        if isinstance(response, dict):
            resp = JsonResponse(response)
            if 'error' in response:
                resp.status_code = response['error'].get('type', 500)
            return resp
        return response
    wrapper.__name__ = func.__name__
    wrapper.__module__ = func.__module__
    wrapper.__doc__ = func.__doc__
    return wrapper
########NEW FILE########
__FILENAME__ = exceptions
# -*- mode: python; coding: utf-8; -*-

""" Custom exceptions """

class AjaxException(Exception):
    """Base class for AJAX exceptions"""
    pass

class Ajax404(AjaxException):
    """Object not found"""
    pass

class AjaxDataException(AjaxException):
    """
    Use it to push json data to response
    """

    def __init__(self, data, *args, **kwargs):
        self.data = data
        Exception.__init__(self, *args, **kwargs)

class RedirectException(Exception):
    def __init__(self, redirect_uri, *args, **kwargs):
        self.redirect_uri = redirect_uri
        self.notice_message = kwargs.pop('notice_message', None)
        self.error_message = kwargs.pop('error_message', None)
        Exception.__init__(self, *args, **kwargs)
########NEW FILE########
__FILENAME__ = helpers
# -*- mode: python; coding: utf-8; -*-

from urlparse import urlsplit, urlunsplit

from django.core.urlresolvers import reverse as _reverse
from django.shortcuts import _get_queryset, get_object_or_404
from django.http import Http404
from django.contrib.sites.models import Site

from sugar.views.exceptions import Ajax404

def reverse(view_name, *args, **kwargs):
    return _reverse(view_name, args=args, kwargs=kwargs)


def absolutize_uri(request, local_url):
    request_url = urlsplit(request.build_absolute_uri(local_url))
    absolute_url = urlunsplit(request_url[:1] + (Site.objects.get_current().domain,) + request_url[2:])
    return absolute_url


def get_object_or_404_ajax(*args, **kwargs):
    try:
        return get_object_or_404(*args, **kwargs)
    except Http404, e:
        raise Ajax404, e


def get_object_or_none(klass, *args, **kwargs):
    """
    Uses get() to return an object or None if the object does not exist.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Note: Like with get(), an MultipleObjectsReturned will be raised if more than one
    object is found.
    """
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None

########NEW FILE########
__FILENAME__ = json
# -*- mode: python; coding: utf-8; -*-

from django.http import HttpResponse
from django.utils import simplejson


class JsonResponse(HttpResponse):
    """
    HttpResponse descendant, which return response with ``application/json`` mimetype.
    """
    def __init__(self, data):
        super(JsonResponse, self).__init__(content=simplejson.dumps(data), mimetype='application/json')

def as_json(errors):
    return dict((k, map(unicode, v)) for k, v in errors.items())

def ajax_request(func):
    """
    Checks request.method is POST. Return error in JSON in other case.

    If view returned dict, returns JsonResponse with this dict as content.
    """
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST':
            response = func(request, *args, **kwargs)
        else:
            response = {'error': {'type': 405,
                                  'message': 'Accepts only POST request'}}
        if isinstance(response, dict):
            resp = JsonResponse(response)
            if 'error' in response:
                resp.status_code = response['error'].get('type', 500)
            return resp
        return response
    wrapper.__name__ = func.__name__
    wrapper.__module__ = func.__module__
    wrapper.__doc__ = func.__doc__
    return wrapper
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings
from sugar.widgets.admin_image.widget import AdminImageWidget

class AdminImageForm(forms.ModelForm):
    '''
    Basic form to handle wiring up the AdminImageWidget to your
    model that has a 'file' field. This assumes your models
    has a file field. If it doesn't then don't use this form
    but create your own.
    
    '''
    
    file = forms.FileField(widget=AdminImageWidget, required=True)
########NEW FILE########
__FILENAME__ = widget
###########
# Thanks to baumer1122 for his AdminImageWidget snippet: http://www.djangosnippets.org/snippets/934/
###########
  
from django.contrib.admin.widgets import AdminFileWidget
from django import forms
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.conf import settings
from PIL import Image
import os

try:
    from sorl.thumbnail.main import DjangoThumbnail
    def thumbnail(image_path):
        t = DjangoThumbnail(relative_source=image_path, requested_size=(80,80))
        return u'<img src="%s" alt="%s" />' % (t.absolute_url, image_path)
except ImportError:
    def thumbnail(image_path):
        absolute_url = os.path.join(settings.MEDIA_ROOT, image_path)
        return u'<img src="%s" alt="%s" />' % (absolute_url, image_path)

class AdminImageWidget(AdminFileWidget):
    """
    A FileField Widget that displays an image instead of a file path
    if the current file is an image.
    
    Example
    -------
    Below is an example on how to implement in your app using the provided code.
            
        from sugar.wigets.admin_image.forms import AdminImageForm
        
        class PhotoAdmin(admin.ModelAdmin):
            form = AdminImageForm
            prepopulated_fields = {'slug': ('title',)}
            
        admin.site.register(Photo, PhotoAdmin)
        
    """
    
    def render(self, name, value, attrs=None):
        output = []
        file_name = str(value)
        if file_name:
            file_path = '%s%s' % (settings.MEDIA_URL, file_name)
            try:            # is image
                Image.open(os.path.join(settings.MEDIA_ROOT, file_name))
                output.append('<a target="_blank" href="%s">%s</a><br />%s <a target="_blank" href="%s">%s</a><br />%s ' % \
                    (file_path, thumbnail(file_name), _('Currently:'), file_path, file_name, _('Change:')))
            except IOError: # not image
                output.append('%s <a target="_blank" href="%s">%s</a> <br />%s ' % \
                    (_('Currently:'), file_path, file_name, _('Change:')))
            
        output.append(super(AdminFileWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))

########NEW FILE########
