__FILENAME__ = models

########NEW FILE########
__FILENAME__ = node
from django.template import Node


class SugarNode(Node):
    def __init__(self, pieces, function):
        self.pieces = pieces
        self.function = function

    def render(self, context):
        args = []
        kwargs = {}
        for part, name, value in self.pieces:
            value = part.resolve(context, value)
            if name is None:
                args.append(value)
            else:
                kwargs[name] = value

        return self.function(context, *args, **kwargs)

########NEW FILE########
__FILENAME__ = parser
from collections import deque
from copy import copy

from django.db.models.loading import cache
from django.template import TemplateSyntaxError

from templatetag_sugar.node import SugarNode


class Parser(object):
    def __init__(self, syntax, function):
        self.syntax = syntax
        self.function = function

    def __call__(self, parser, token):
        # we're going to be doing pop(0) a bit, so a deque is way more
        # efficient
        bits = deque(token.split_contents())
        # pop the name of the tag off
        tag_name = bits.popleft()
        pieces = []
        error = False
        for part in self.syntax:
            try:
                result = part.parse(parser, bits)
            except TemplateSyntaxError:
                error = True
                break
            if result is None:
                continue
            pieces.extend(result)
        if bits or error:
            raise TemplateSyntaxError(
                "%s has the following syntax: {%% %s %s %%}" % (
                    tag_name,
                    tag_name,
                    " ".join(part.syntax() for part in self.syntax),
                )
            )
        return SugarNode(pieces, self.function)


class Parsable(object):
    def resolve(self, context, value):
        return value


class NamedParsable(Parsable):
    def __init__(self, name=None):
        self.name = name

    def syntax(self):
        if self.name:
            return "<%s>" % self.name
        return "<arg>"


class Constant(Parsable):
    def __init__(self, text):
        self.text = text

    def syntax(self):
        return self.text

    def parse(self, parser, bits):
        if not bits:
            raise TemplateSyntaxError
        if bits[0] == self.text:
            bits.popleft()
            return None
        raise TemplateSyntaxError


class Variable(NamedParsable):
    def parse(self, parser, bits):
        bit = bits.popleft()
        val = parser.compile_filter(bit)
        return [(self, self.name, val)]

    def resolve(self, context, value):
        return value.resolve(context)


class Name(NamedParsable):
    def parse(self, parser, bits):
        bit = bits.popleft()
        return [(self, self.name, bit)]


class Optional(Parsable):
    def __init__(self, parts):
        self.parts = parts

    def syntax(self):
        return "[%s]" % (" ".join(part.syntax() for part in self.parts))

    def parse(self, parser, bits):
        result = []
        # we make a copy so that if part way through the optional part it
        # doesn't match no changes are made
        bits_copy = copy(bits)
        for part in self.parts:
            try:
                val = part.parse(parser, bits_copy)
                if val is None:
                    continue
                result.extend(val)
            except (TemplateSyntaxError, IndexError):
                return None
        # however many bits we popped off our copy pop off the real one
        diff = len(bits) - len(bits_copy)
        for _ in range(diff):
            bits.popleft()
        return result


class Model(NamedParsable):
    def parse(self, parser, bits):
        bit = bits.popleft()
        app, model = bit.split(".")
        return [(self, self.name, cache.get_model(app, model))]

########NEW FILE########
__FILENAME__ = register
from templatetag_sugar.parser import Parser


def tag(register, syntax, name=None):
    def inner(func):
        register.tag(name or func.__name__, Parser(syntax, func))
        return func
    return inner

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title

########NEW FILE########
__FILENAME__ = settings
SECRET_KEY = b"a"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

INSTALLED_APPS = [
    "templatetag_sugar",
    "templatetag_sugar.tests",
]

########NEW FILE########
__FILENAME__ = test_tags
import sys

from django import template

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Name, Variable, Constant, Optional, Model

register = template.Library()


@tag(
    register,
    [Constant("for"), Variable(), Optional([Constant("as"), Name()])]
)
def test_tag_1(context, val, asvar=None):
    if asvar:
        context[asvar] = val
        return ""
    else:
        return val


@tag(register, [Model(), Variable(), Optional([Constant("as"), Name()])])
def test_tag_2(context, model, limit, asvar=None):
    objs = model._default_manager.all()[:limit]
    if asvar:
        context[asvar] = objs
        return ""
    if sys.version_info[0] == 2:
        return unicode(objs)
    else:
        return str(objs)


@tag(register, [Variable()])
def test_tag_3(context, val):
    return val


@tag(
    register,
    [
        Optional([Constant("width"), Variable('width')]),
        Optional([Constant("height"), Variable('height')])
    ]
)
def test_tag_4(context, width=None, height=None):
    return "%s, %s" % (width, height)

########NEW FILE########
__FILENAME__ = tests
from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from templatetag_sugar.tests.models import Book


class SugarTestCase(TestCase):
    def assert_renders(self, tmpl, context, value):
        tmpl = Template(tmpl)
        self.assertEqual(tmpl.render(context), value)

    def assert_syntax_error(self, tmpl, error):
        try:
            Template(tmpl)
        except TemplateSyntaxError as e:
            self.assertTrue(
                str(e).endswith(error),
                "%s didn't end with %s" % (str(e), error)
            )
        else:
            self.fail("Didn't raise")

    def test_basic(self):
        self.assert_renders(
            """{% load test_tags %}{% test_tag_1 for "alex" %}""",
            Context(),
            "alex"
        )

        c = Context()
        self.assert_renders(
            """{% load test_tags %}{% test_tag_1 for "brian" as name %}""",
            c,
            ""
        )
        self.assertEqual(c["name"], "brian")

        self.assert_renders(
            """{% load test_tags %}{% test_tag_1 for variable %}""",
            Context({"variable": [1, 2, 3]}),
            "[1, 2, 3]",
        )

    def test_model(self):
        Book.objects.create(title="Pro Django")
        self.assert_renders(
            """{% load test_tags %}{% test_tag_2 tests.Book 2 %}""",
            Context(),
            "[<Book: Pro Django>]"
        )

    def test_errors(self):
        self.assert_syntax_error(
            """{% load test_tags %}{% test_tag_1 for "jesse" as %}""",
            "test_tag_1 has the following syntax: {% test_tag_1 for <arg> [as "
            "<arg>] %}"
        )

        self.assert_syntax_error(
            """{% load test_tags %}{% test_tag_4 width %}""",
            "test_tag_4 has the following syntax: {% test_tag_4 [width <width>"
            "] [height <height>] %}"
        )

    def test_variable_as_string(self):
        self.assert_renders(
            """{% load test_tags %}{% test_tag_3 "xela alex" %}""",
            Context(),
            "xela alex",
        )

    def test_optional(self):
        self.assert_renders(
            """{% load test_tags %}{% test_tag_4 width 100 height 200 %}""",
            Context(),
            "100, 200",
        )

        self.assert_renders(
            """{% load test_tags %}{% test_tag_4 width 100 %}""",
            Context(),
            "100, None"
        )

        self.assert_renders(
            """{% load test_tags %}{% test_tag_4 height 100 %}""",
            Context(),
            "None, 100",
        )

        self.assert_syntax_error(
            """{% load test_tags %}{% test_tag_1 %}""",
            "test_tag_1 has the following syntax: {% test_tag_1 for <arg> [as "
            "<arg>] %}"
        )

########NEW FILE########
