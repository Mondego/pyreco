__FILENAME__ = base
import re
import operator
import ast

VAR_FRAGMENT = 0
OPEN_BLOCK_FRAGMENT = 1
CLOSE_BLOCK_FRAGMENT = 2
TEXT_FRAGMENT = 3

VAR_TOKEN_START = '{{'
VAR_TOKEN_END = '}}'
BLOCK_TOKEN_START = '{%'
BLOCK_TOKEN_END = '%}'

TOK_REGEX = re.compile(r"(%s.*?%s|%s.*?%s)" % (
    VAR_TOKEN_START,
    VAR_TOKEN_END,
    BLOCK_TOKEN_START,
    BLOCK_TOKEN_END
))

WHITESPACE = re.compile('\s+')

operator_lookup_table = {
    '<': operator.lt,
    '>': operator.gt,
    '==': operator.eq,
    '!=': operator.ne,
    '<=': operator.le,
    '>=': operator.ge
}


class TemplateError(Exception):
    pass


class TemplateContextError(TemplateError):

    def __init__(self, context_var):
        self.context_var = context_var

    def __str__(self):
        return "cannot resolve '%s'" % self.context_var


class TemplateSyntaxError(TemplateError):

    def __init__(self, error_syntax):
        self.error_syntax = error_syntax

    def __str__(self):
        return "'%s' seems like invalid syntax" % self.error_syntax


def eval_expression(expr):
    try:
        return 'literal', ast.literal_eval(expr)
    except ValueError, SyntaxError:
        return 'name', expr


def resolve(name, context):
    if name.startswith('..'):
        context = context.get('..', {})
        name = name[2:]
    try:
        for tok in name.split('.'):
            context = context[tok]
        return context
    except KeyError:
        raise TemplateContextError(name)


class _Fragment(object):
    def __init__(self, raw_text):
        self.raw = raw_text
        self.clean = self.clean_fragment()

    def clean_fragment(self):
        if self.raw[:2] in (VAR_TOKEN_START, BLOCK_TOKEN_START):
            return self.raw.strip()[2:-2].strip()
        return self.raw

    @property
    def type(self):
        raw_start = self.raw[:2]
        if raw_start == VAR_TOKEN_START:
            return VAR_FRAGMENT
        elif raw_start == BLOCK_TOKEN_START:
            return CLOSE_BLOCK_FRAGMENT if self.clean[:3] == 'end' else OPEN_BLOCK_FRAGMENT
        else:
            return TEXT_FRAGMENT


class _Node(object):
    creates_scope = False

    def __init__(self, fragment=None):
        self.children = []
        self.process_fragment(fragment)

    def process_fragment(self, fragment):
        pass

    def enter_scope(self):
        pass

    def render(self, context):
        pass

    def exit_scope(self):
        pass

    def render_children(self, context, children=None):
        if children is None:
            children = self.children
        def render_child(child):
            child_html = child.render(context)
            return '' if not child_html else str(child_html)
        return ''.join(map(render_child, children))


class _ScopableNode(_Node):
    creates_scope = True

class _Root(_Node):
    def render(self, context):
        return self.render_children(context)


class _Variable(_Node):
    def process_fragment(self, fragment):
        self.name = fragment

    def render(self, context):
        return resolve(self.name, context)


class _Each(_ScopableNode):
    def process_fragment(self, fragment):
        try:
            _, it = WHITESPACE.split(fragment, 1)
            self.it = eval_expression(it)
        except ValueError:
            raise TemplateSyntaxError(fragment)

    def render(self, context):
        items = self.it[1] if self.it[0] == 'literal' else resolve(self.it[1], context)
        def render_item(item):
            return self.render_children({'..': context, 'it': item})
        return ''.join(map(render_item, items))


class _If(_ScopableNode):
    def process_fragment(self, fragment):
        bits = fragment.split()[1:]
        if len(bits) not in (1, 3):
            raise TemplateSyntaxError(fragment)
        self.lhs = eval_expression(bits[0])
        if len(bits) == 3:
            self.op = bits[1]
            self.rhs = eval_expression(bits[2])

    def render(self, context):
        lhs = self.resolve_side(self.lhs, context)
        if hasattr(self, 'op'):
            op = operator_lookup_table.get(self.op)
            if op is None:
                raise TemplateSyntaxError(self.op)
            rhs = self.resolve_side(self.rhs, context)
            exec_if_branch = op(lhs, rhs)
        else:
            exec_if_branch = operator.truth(lhs)
        if_branch, else_branch = self.split_children()
        return self.render_children(context,
            self.if_branch if exec_if_branch else self.else_branch)

    def resolve_side(self, side, context):
        return side[1] if side[0] == 'literal' else resolve(side[1], context)

    def exit_scope(self):
        self.if_branch, self.else_branch = self.split_children()

    def split_children(self):
        if_branch, else_branch = [], []
        curr = if_branch
        for child in self.children:
            if isinstance(child, _Else):
                curr = else_branch
                continue
            curr.append(child)
        return if_branch, else_branch


class _Else(_Node):
    def render(self, context):
        pass


class _Call(_Node):
    def process_fragment(self, fragment):
        try:
            bits = WHITESPACE.split(fragment)
            self.callable = bits[1]
            self.args, self.kwargs = self._parse_params(bits[2:])
        except ValueError, IndexError:
            raise TemplateSyntaxError(fragment)

    def _parse_params(self, params):
        args, kwargs = [], {}
        for param in params:
            if '=' in param:
                name, value = param.split('=')
                kwargs[name] = eval_expression(value)
            else:
                args.append(eval_expression(param))
        return args, kwargs

    def render(self, context):
        resolved_args, resolved_kwargs = [], {}
        for kind, value in self.args:
            if kind == 'name':
                value = resolve(value, context)
            resolved_args.append(value)
        for key, (kind, value) in self.kwargs.iteritems():
            if kind == 'name':
                value = resolve(value, context)
            resolved_kwargs[key] = value
        resolved_callable = resolve(self.callable, context)
        if hasattr(resolved_callable, '__call__'):
            return resolved_callable(*resolved_args, **resolved_kwargs)
        else:
            raise TemplateError("'%s' is not a callable" % self.callable)


class _Text(_Node):
    def process_fragment(self, fragment):
        self.text = fragment

    def render(self, context):
        return self.text


class Compiler(object):
    def __init__(self, template_string):
        self.template_string = template_string

    def each_fragment(self):
        for fragment in TOK_REGEX.split(self.template_string):
            if fragment:
                yield _Fragment(fragment)

    def compile(self):
        root = _Root()
        scope_stack = [root]
        for fragment in self.each_fragment():
            if not scope_stack:
                raise TemplateError('nesting issues')
            parent_scope = scope_stack[-1]
            if fragment.type == CLOSE_BLOCK_FRAGMENT:
                parent_scope.exit_scope()
                scope_stack.pop()
                continue
            new_node = self.create_node(fragment)
            if new_node:
                parent_scope.children.append(new_node)
                if new_node.creates_scope:
                    scope_stack.append(new_node)
                    new_node.enter_scope()
        return root

    def create_node(self, fragment):
        node_class = None
        if fragment.type == TEXT_FRAGMENT:
            node_class = _Text
        elif fragment.type == VAR_FRAGMENT:
            node_class = _Variable
        elif fragment.type == OPEN_BLOCK_FRAGMENT:
            cmd = fragment.clean.split()[0]
            if cmd == 'each':
                node_class = _Each
            elif cmd == 'if':
                node_class = _If
            elif cmd == 'else':
                node_class = _Else
            elif cmd == 'call':
                node_class = _Call
        if node_class is None:
            raise TemplateSyntaxError(fragment)
        return node_class(fragment.clean)


class Template(object):
    def __init__(self, contents):
        self.contents = contents
        self.root = Compiler(contents).compile()

    def render(self, **kwargs):
        return self.root.render(kwargs)

########NEW FILE########
__FILENAME__ = benchmarks
import os
import timeit
from jinja2 import Environment, FileSystemLoader, Template as JinjaTemplate
from django.conf import settings
from django.template import Context, Template as DjangoTemplate
from django.template.loaders.filesystem import Loader as DjangoDefaultLoader
from django.template.loaders.cached import Loader as DjangoCachedLoader
from base import Template as MicroTemplate


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
context = {
    'title': 'MY TODOS',
    'todos': [
        dict(title='grocery shopping', description='do all the shopping', done=True, followers=[]),
        dict(title='pay bills', description='pay all the bills', done=False, followers=['alex']),
        dict(title='go clubbing', description='get drunk', done=False, followers=['alex', 'mike', 'paul']),
    ]
}

settings.configure(TEMPLATE_DIRS=[template_dir])

def read_html(engine):
    html_file_path = os.path.join(template_dir, "%s.html" % engine)
    with open(html_file_path) as html_file:
        html = html_file.read()
    return html


microtemplates_html = read_html('microtemplates')
django_html = read_html('django')
django_default_loader = DjangoDefaultLoader()
django_cached_loader = DjangoCachedLoader(['django.template.loaders.filesystem.Loader'])
jinja2_html = read_html('jinja2')
jinja2_env = Environment(loader=FileSystemLoader(template_dir))


def benchmark_microtemplates():
    MicroTemplate(microtemplates_html).render(**context)


def benchmark_django():
    DjangoTemplate(django_html).render(Context(context))


def benchmark_django_default_loader():
    template, _ = django_default_loader.load_template('django.html')
    template.render(Context(context))


def benchmark_django_cached_loader():
    template, _ = django_cached_loader.load_template('django.html')
    template.render(Context(context))


def benchmark_jinja2():
    JinjaTemplate(jinja2_html).render(**context)


def benchmark_jinja2_env():
    jinja2_env.get_template('jinja2.html').render(**context)


if __name__ == '__main__':
    number = 10000
    engines = ('microtemplates', 'django', 'django_default_loader', 'django_cached_loader', 'jinja2', 'jinja2_env')
    setup = "from __main__ import %s" % ', '.join(map(lambda t: 'benchmark_' + t, engines))
    for engine in engines:
        t = timeit.Timer("benchmark_%s()" % engine, setup=setup)
        time = t.timeit(number=number) / number
        print "%s => run %s times, took %.2f ms" % (engine, number, 1000 * time)

########NEW FILE########
__FILENAME__ = tests
import unittest
from .base import Template


class EachTests(unittest.TestCase):

    def test_each_iterable_in_context(self):
        rendered = Template('{% each items %}<div>{{it}}</div>{% end %}').render(items=['alex', 'maria'])
        self.assertEquals(rendered, '<div>alex</div><div>maria</div>')

    def test_each_iterable_as_literal_list(self):
        rendered = Template('{% each [1, 2, 3] %}<div>{{it}}</div>{% end %}').render()
        self.assertEquals(rendered, '<div>1</div><div>2</div><div>3</div>')

    def test_each_parent_context(self):
        rendered = Template('{% each [1, 2, 3] %}<div>{{..name}}-{{it}}</div>{% end %}').render(name='jon doe')
        self.assertEquals(rendered, '<div>jon doe-1</div><div>jon doe-2</div><div>jon doe-3</div>')

    def test_each_space_issues(self):
        rendered = Template('{% each [1,2, 3]%}<div>{{it}}</div>{%end%}').render()
        self.assertEquals(rendered, '<div>1</div><div>2</div><div>3</div>')

    def test_each_no_tags_inside(self):
        rendered = Template('{% each [1,2,3] %}<br>{% end %}').render()
        self.assertEquals(rendered, '<br><br><br>')

    def test_nested_objects(self):
        context = {'lines': [{'name': 'l1'}], 'name': 'p1'}
        rendered = Template('<h1>{{name}}</h1>{% each lines %}<span class="{{..name}}-{{it.name}}">{{it.name}}</span>{% end %}').render(**context)
        self.assertEquals(rendered, '<h1>p1</h1><span class="p1-l1">l1</span>')

    def test_nested_tag(self):
        rendered = Template('{% each items %}{% if it %}yes{% end %}{% end %}').render(items=['', None, '2'])
        self.assertEquals(rendered, 'yes')


class IfTests(unittest.TestCase):

    def test_simple_if_is_true(self):
        rendered = Template('{% if num > 5 %}<div>more than 5</div>{% end %}').render(num=6)
        self.assertEquals(rendered, '<div>more than 5</div>')

    def test_simple_if_is_false(self):
        rendered = Template('{% if num > 5 %}<div>more than 5</div>{% end %}').render(num=4)
        self.assertEquals(rendered, '')

    def test_if_else_if_branch(self):
        rendered = Template('{% if num > 5 %}<div>more than 5</div>{% else %}<div>less than 5</div>{% end %}').render(num=6)
        self.assertEquals(rendered, '<div>more than 5</div>')

    def test_if_else_else_branch(self):
        rendered = Template('{% if num > 5 %}<div>more than 5</div>{% else %}<div>less or equal to 5</div>{% end %}').render(num=4)
        self.assertEquals(rendered, '<div>less or equal to 5</div>')

    def test_nested_if(self):
        tmpl = '{% if num > 5 %}{% each [1, 2] %}{{it}}{% end %}{% else %}{% each [3, 4] %}{{it}}{% end %}{% end %}'
        rendered = Template(tmpl).render(num=6)
        self.assertEquals(rendered, '12')
        rendered = Template(tmpl).render(num=4)
        self.assertEquals(rendered, '34')

    def test_truthy_thingy(self):
        rendered = Template('{% if items %}we have items{% end %}').render(items=[])
        self.assertEquals(rendered, '')
        rendered = Template('{% if items %}we have items{% end %}').render(items=None)
        self.assertEquals(rendered, '')
        rendered = Template('{% if items %}we have items{% end %}').render(items='')
        self.assertEquals(rendered, '')
        rendered = Template('{% if items %}we have items{% end %}').render(items=[1])
        self.assertEquals(rendered, 'we have items')


def pow(m=2, e=2):
    return m ** e


class CallTests(unittest.TestCase):

    def test_no_args(self):
        rendered = Template('{% call pow %}').render(pow=pow)
        self.assertEquals(rendered, '4')

    def test_positional_args(self):
        rendered = Template('{% call pow 3 %}').render(pow=pow)
        self.assertEquals(rendered, '9')
        rendered = Template('{% call pow 2 3 %}').render(pow=pow)
        self.assertEquals(rendered, '8')

    def test_keyword_args(self):
        rendered = Template('{% call pow 2 e=5 %}').render(pow=pow)
        self.assertEquals(rendered, '32')
        rendered = Template('{% call pow e=4 %}').render(pow=pow)
        self.assertEquals(rendered, '16')
        rendered = Template('{% call pow m=3 e=4 %}').render(pow=pow)
        self.assertEquals(rendered, '81')


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
