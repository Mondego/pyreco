__FILENAME__ = ext
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
import itertools
import functools

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateNotFound

from .template import CHART_HTML
from .options import Options


class ChartExtension(Extension):
    tags = set(['line_chart', 'pie_chart', 'column_chart',
                'bar_chart', 'area_chart'])

    id = itertools.count()
    _library = None

    def __init__(self, environment):
        super(ChartExtension, self).__init__(environment)

        environment.extend(
            options=dict(height='300px'),
        )

        for tag in self.tags:
            setattr(self, tag + '_support',
                    functools.partial(self._chart_support, tag))

    def parse(self, parser):
        # parse chart name
        chart_tag = parser.stream.next()

        args = [parser.parse_expression()]

        # parse 'with' statement
        if parser.stream.current.type != 'block_end':
            token = parser.stream.next()
            if token.value != 'with':
                parser.fail("expected 'with' statement", token.lineno)

        # parse options
        while parser.stream.current.type != 'block_end':
            lineno = parser.stream.current.lineno

            target = parser.parse_assign_target()
            parser.stream.expect('assign')
            expr = parser.parse_expression()

            args.append(nodes.Assign(target, expr, lineno=lineno))

        support_func = chart_tag.value + '_support'

        return nodes.CallBlock(self.call_method(support_func, args),
                               [], [], []).set_lineno(chart_tag.lineno)

    def _chart_support(self, name, data, caller, **kwargs):
        "template chart support function"
        id = 'chart-%s' % self.id.next()
        name = self._chart_class_name(name)
        options = dict(self.environment.options)
        options.update(name=name, id=id)

        # jinja2 prepends 'l_' to keys
        kwargs = dict((k[2:], v) for (k, v) in kwargs.items())

        if self._library is None:
            self._library = self.load_library()
        id = kwargs.get('id', '')
        library = self._library.get(id, {})

        # apply options from a tag
        library.update(kwargs.get('library', {}))
        # apply options from chartkick.json
        kwargs.update(library=library)

        options.update(kwargs)
        return CHART_HTML.format(data=data, options=json.dumps(kwargs),
                                 **options)

    def _chart_class_name(self, tag_name):
        "converts chart tag name to javascript class name"
        return ''.join(map(str.title, tag_name.split('_')))

    def load_library(self):
        "loads configuration options"
        try:
            filename = self.environment.get_template('chartkick.json').filename
        except TemplateNotFound:
            return {}
        else:
            options = Options()
            options.load(filename)
            return options


charts = ChartExtension

########NEW FILE########
__FILENAME__ = options
from __future__ import absolute_import

import json
import logging


class Options(dict):
    def __init__(self, *args, **kwargs) :
        dict.__init__(self, *args, **kwargs)

    def load(self, filename):
        with open(filename) as jsonfile:
            options = json.loads(jsonfile.read())
            self.clear()
            for option in options:
                id = option.get('id', None)
                if id is None:
                    logging.warning("Missing chart 'id' in %s" % option)
                    continue
                self.update({id: option})

########NEW FILE########
__FILENAME__ = template
from __future__ import absolute_import


CHART_HTML = """
<div id="{id}" style="height: {height}; text-align: center; color: #999;
                      line-height: {height}; font-size: 14px;
                      font-family: Lucida Grande, Lucida Sans Unicode,
                      Verdana, Arial, Helvetica, sans-serif;">
    Loading...
</div>
<script>
//<![CDATA[
new Chartkick.{name}(document.getElementById("{id}"), {data}, {options});
//]]>
</script>
"""

########NEW FILE########
__FILENAME__ = chartkick
from __future__ import absolute_import

import os
import ast
import json
import functools
import itertools

from django import template
from django.template.loaders.filesystem import Loader

from ..template import CHART_HTML
from ..options import Options


register = template.Library()


class ChartNode(template.Node):
    id = itertools.count()
    _library = None

    def __init__(self, name, variable, options=None):
        self.name = name
        self.variable = template.Variable(variable)
        self.options = options or {}

        for name, value in self.options.items():
            try:
                self.options[name] = ast.literal_eval(value)
            except ValueError:
                self.options[name] = template.Variable(value)
            except SyntaxError as e:
                raise template.TemplateSyntaxError(e)

    def render(self, context):
        for name, value in self.options.items():
            if isinstance(value, template.Variable):
                self.options[name] = value.resolve(context)

        options = dict(id='chart-%s' % self.id.next(), height='300px')
        id = self.options.get('id', None) or options['id']

        # apply options from chartkick.json
        options.update(library=self.library(id))
        # apply options from a tag
        options.update(self.options)

        data = json.dumps(self.variable.resolve(context))
        return CHART_HTML.format(name=self.name, data=data,
                                 options=json.dumps(options), **options)

    @classmethod
    def library(cls, chart_id):
        if cls._library is None:
            loader = Loader()
            for filename in loader.get_template_sources('chartkick.json'):
                if os.path.exists(filename):
                    oprtions = Options()
                    oprtions.load(filename)
                    cls._library = oprtions
                    break
            else:
                cls._library = Options()

        return cls._library.get(chart_id, {})


def chart(name, parser, token):
    args = token.split_contents()

    if len(args) < 2:
        raise template.TemplateSyntaxError(
                '%r statement requires at least one argument' %
                token.split_contents()[0])

    options = None
    if len(args) > 2:
        if args[2] != 'with':
            raise template.TemplateSyntaxError("Expected 'with' statement")

        try:
            options = parse_options(' '.join(args[3:]))
        except ValueError:
            raise template.TemplateSyntaxError('Invalid options')

    return ChartNode(name=name, variable=args[1], options=options)


def parse_options(source):
    """parses chart tag options"""
    options = {}
    tokens = [t.strip() for t in source.split('=')]

    name = tokens[0]
    for token in tokens[1:-1]:
        value, next_name = token.rsplit(' ', 1)
        options[name.strip()] = value
        name = next_name
    options[name.strip()] = tokens[-1].strip()
    return options


register.tag('line_chart', functools.partial(chart, 'LineChart'))
register.tag('pie_chart', functools.partial(chart, 'PieChart'))
register.tag('column_chart', functools.partial(chart, 'ColumnChart'))
register.tag('bar_chart', functools.partial(chart, 'BarChart'))
register.tag('area_chart', functools.partial(chart, 'AreaChart'))

########NEW FILE########
__FILENAME__ = settings
DEBUG = True
TEMPLATE_DEBUG = DEBUG

STATIC_ROOT = ''
STATIC_URL = '/static/'

import chartkick
STATICFILES_DIRS = (
    chartkick.js(),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = '5ry^!i1c6y*$396rb@^ibm1m%eg-aaw8mf0qurk%+a3-r5woo)'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'charts.urls'

WSGI_APPLICATION = 'charts.wsgi.application'

TEMPLATE_DIRS = (
    'charts',
)

INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'chartkick',
)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'charts.views.charts', name='charts'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render


def charts(request):
    exchange = {'2001-01-31': 1.064, '2002-01-31': 1.1305,
                '2003-01-31': 0.9417, '2004-01-31': 0.7937,
                '2005-01-31': 0.7609, '2006-01-31': 0.827,
                '2007-01-31': 0.7692, '2008-01-31': 0.6801,
                '2009-01-31': 0.7491, '2010-01-31': 0.7002,
                '2011-01-31': 0.7489, '2012-01-31': 0.7755,
                '2013-01-31': 0.7531,
                }

    browser_stats = [['Chrome', 52.9], ['Firefox', 27.7], ['Opera', 1.6],
                     ['Internet Explorer', 12.6], ['Safari', 4]]

    temperature = [{u'data': {  '2012-00-01 00:00:00 -0700': 7,
                                '2012-01-01 00:00:00 -0700': 6.9,
                                '2012-02-01 00:00:00 -0700': 9.5,
                                '2012-03-01 00:00:00 -0700': 14.5,
                                '2012-04-01 00:00:00 -0700': 18.2,
                                '2012-05-01 00:00:00 -0700': 21.5,
                                '2012-06-01 00:00:00 -0700': 25.2,
                                '2012-07-01 00:00:00 -0700': 26.5,
                                '2012-08-01 00:00:00 -0700': 23.3,
                                '2012-09-01 00:00:00 -0700': 18.3,
                                '2012-10-01 00:00:00 -0700': 13.9,
                                '2012-11-01 00:00:00 -0700': 9.6},
                    u'name': u'Tokyo'},
                    {u'data': { '2012-00-01 00:00:00 -0700': -0.2,
                                '2012-01-01 00:00:00 -0700': 0.8,
                                '2012-02-01 00:00:00 -0700': 5.7,
                                '2012-03-01 00:00:00 -0700': 11.3,
                                '2012-04-01 00:00:00 -0700': 17,
                                '2012-05-01 00:00:00 -0700': 22,
                                '2012-06-01 00:00:00 -0700': 24.8,
                                '2012-07-01 00:00:00 -0700': 24.1,
                                '2012-08-01 00:00:00 -0700': 20.1,
                                '2012-09-01 00:00:00 -0700': 14.1,
                                '2012-10-01 00:00:00 -0700': 8.6,
                                '2012-11-01 00:00:00 -0700': 2.5},
                    u'name': u'New York'},
                    {u'data': { '2012-00-01 00:00:00 -0700': -0.9,
                                '2012-01-01 00:00:00 -0700': 0.6,
                                '2012-02-01 00:00:00 -0700': 3.5,
                                '2012-03-01 00:00:00 -0700': 8.4,
                                '2012-04-01 00:00:00 -0700': 13.5,
                                '2012-05-01 00:00:00 -0700': 17,
                                '2012-06-01 00:00:00 -0700': 18.6,
                                '2012-07-01 00:00:00 -0700': 17.9,
                                '2012-08-01 00:00:00 -0700': 14.3,
                                '2012-09-01 00:00:00 -0700': 9,
                                '2012-10-01 00:00:00 -0700': 3.9,
                                '2012-11-01 00:00:00 -0700': 1},
                    u'name': u'Berlin'},
                    {u'data': { '2012-00-01 00:00:00 -0700': 3.9,
                                '2012-01-01 00:00:00 -0700': 4.2,
                                '2012-02-01 00:00:00 -0700': 5.7,
                                '2012-03-01 00:00:00 -0700': 8.5,
                                '2012-04-01 00:00:00 -0700': 11.9,
                                '2012-05-01 00:00:00 -0700': 15.2,
                                '2012-06-01 00:00:00 -0700': 17,
                                '2012-07-01 00:00:00 -0700': 16.6,
                                '2012-08-01 00:00:00 -0700': 14.2,
                                '2012-09-01 00:00:00 -0700': 10.3,
                                '2012-10-01 00:00:00 -0700': 6.6,
                                '2012-11-01 00:00:00 -0700': 4.8},
                    u'name': u'London'}]

    sizes = [['X-Small', 5], ['Small', 27], ['Medium', 10],
             ['Large', 14], ['X-Large', 10]]

    areas = {'2013-07-27 07:08:00 UTC': 4, '2013-07-27 07:09:00 UTC': 3,
             '2013-07-27 07:10:00 UTC': 2, '2013-07-27 07:04:00 UTC': 2,
             '2013-07-27 07:02:00 UTC': 3, '2013-07-27 07:00:00 UTC': 2,
             '2013-07-27 07:06:00 UTC': 1, '2013-07-27 07:01:00 UTC': 5,
             '2013-07-27 07:05:00 UTC': 5, '2013-07-27 07:03:00 UTC': 3,
             '2013-07-27 07:07:00 UTC': 3}

    return render(request, 'charts.html', locals())

########NEW FILE########
__FILENAME__ = wsgi
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "charts.settings")


from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "charts.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = tests
import re
import unittest

from django.template import Template, Context
from django.template import TemplateSyntaxError as DjangoTemplateSyntaxError
from django.conf import settings

from jinja2 import TemplateSyntaxError as Jinja2TemplateSyntaxError
from jinja2 import Environment
from jinja2 import FileSystemLoader

import chartkick

# python 2.6 support
if not hasattr(unittest.TestCase, 'assertIn'):
    import unittest2 as unittest


settings.configure()
settings.INSTALLED_APPS = ('chartkick',)
settings.STATICFILES_DIRS = (chartkick.js(),)
settings.STATIC_URL = ''


class TestsBase(object):

    TemplateSyntaxError = None

    def render(self, template, context=None):
        raise NotImplementedError

    def test_missing_vaiable(self):
        self.assertRaises(self.TemplateSyntaxError,
                          self.render, '{% line_chart %}')

    def test_empty(self):
        chart = self.render('{% line_chart data %}', dict(data={}))
        self.assertIn('Chartkick.LineChart', chart)
        self.assertIn('id', chart)
        self.assertIn('height', chart)

    def test_line_chart(self):
        chart = self.render('{% line_chart data %}', dict(data={}))
        self.assertIn('Chartkick.LineChart', chart)
        self.assertNotIn('Chartkick.PieChart', chart)
        self.assertNotIn('Chartkick.ColumnChart', chart)
        self.assertNotIn('Chartkick.BarChart', chart)
        self.assertNotIn('Chartkick.AreaChart', chart)

    def test_pie_chart(self):
        chart = self.render('{% pie_chart data %}', dict(data={}))
        self.assertNotIn('Chartkick.LineChart', chart)
        self.assertIn('Chartkick.PieChart', chart)
        self.assertNotIn('Chartkick.ColumnChart', chart)
        self.assertNotIn('Chartkick.BarChart', chart)
        self.assertNotIn('Chartkick.AreaChart', chart)

    def test_column_chart(self):
        chart = self.render('{% column_chart data %}', dict(data={}))
        self.assertNotIn('Chartkick.LineChart', chart)
        self.assertNotIn('Chartkick.PieChart', chart)
        self.assertIn('Chartkick.ColumnChart', chart)
        self.assertNotIn('Chartkick.BarChart', chart)
        self.assertNotIn('Chartkick.AreaChart', chart)

    def test_bar_chart(self):
        chart = self.render('{% bar_chart data %}', dict(data={}))
        self.assertNotIn('Chartkick.LineChart', chart)
        self.assertNotIn('Chartkick.PieChart', chart)
        self.assertNotIn('Chartkick.ColumnChart', chart)
        self.assertIn('Chartkick.BarChart', chart)
        self.assertNotIn('Chartkick.AreaChart', chart)

    def test_area_chart(self):
        chart = self.render('{% area_chart data %}', dict(data={}))
        self.assertNotIn('Chartkick.LineChart', chart)
        self.assertNotIn('Chartkick.PieChart', chart)
        self.assertNotIn('Chartkick.ColumnChart', chart)
        self.assertNotIn('Chartkick.BarChart', chart)
        self.assertIn('Chartkick.AreaChart', chart)

    def test_all_charts(self):
        template = """{% line_chart data %}
                      {% pie_chart data %}
                      {% column_chart data %}
                      {% bar_chart data %}
                      {% area_chart data %}"""
        chart = self.render(template, dict(data={}))

        self.assertIn('Chartkick.LineChart', chart)
        self.assertIn('Chartkick.PieChart', chart)
        self.assertIn('Chartkick.ColumnChart', chart)
        self.assertIn('Chartkick.BarChart', chart)
        self.assertIn('Chartkick.AreaChart', chart)

    @unittest.skip('Embedded data is not implemented yet')
    def test_data_embeded(self):
        chart = self.render('{% line_chart {"foo":35,"bar":12} %}')
        self.assertIn('foo', chart)
        self.assertIn('bar', chart)

    def test_data_context(self):
        chart = self.render('{% line_chart foo %}', dict(foo='bar'))
        self.assertNotIn('foo', chart)
        self.assertIn('bar', chart)

    def test_missing_with(self):
        self.assertRaises(self.TemplateSyntaxError,
                          self.render, '{% line_chart data x=y %}')

    def test_options_embeded(self):
        chart = self.render('{% line_chart foo with library={"title": "eltit"} %}',
                            dict(foo='bar'))
        self.assertNotIn('foo', chart)
        self.assertIn('bar', chart)
        self.assertIn('library', chart)
        self.assertIn('title', chart)
        self.assertIn('eltit', chart)

    def test_options_context(self):
        chart = self.render('{% line_chart "" with foo=bar %}',
                            dict(bar=123))
        self.assertNotIn('data', chart)
        self.assertIn('foo', chart)
        self.assertNotIn('bar', chart)
        self.assertIn('123', chart)

    def test_spaces(self):
        templates = ('{%line_chart data %}', '{%  line_chart data %}',
                     '{% line_chart  data  %}', '{%  line_chart data%}',
                     '{%  line_chart  data  with  x="foo  bar" %}',
                     '{%  line_chart  data with  x=1%}')

        for template in templates:
            chart = self.render(template, dict(data='foo'))
            self.assertIn('Chartkick.LineChart', chart)
            self.assertNotIn('data', chart)
            self.assertIn('foo', chart)

    def test_id(self):
        chart1 = self.render('{% line_chart "" with id=123 %}')
        chart2 = self.render('{% line_chart "" %}{% line_chart "" %}')
        ids = re.findall('id=\"(.*?)\"', chart2)

        self.assertIn('123', chart1)
        self.assertIn('id', chart1)
        self.assertNotEqual(ids[0], ids[1])

    def test_invalid_options(self):
        self.assertRaises(self.TemplateSyntaxError, self.render,
                '{% line_chart "" with library= %}')
        self.assertRaises(self.TemplateSyntaxError, self.render,
                '{% line_chart "" with library={"title":"test" %}')
        self.assertRaises(self.TemplateSyntaxError, self.render,
                '{% line_chart "" with library="title":"test" %}')
        self.assertRaises(self.TemplateSyntaxError, self.render,
                '{% line_chart "" with library={"title: "test"} %}')
        self.assertRaises(self.TemplateSyntaxError, self.render,
                '{% line_chart "" with library={"title": "test} %}')
        self.assertRaises(self.TemplateSyntaxError, self.render,
                '{% line_chart "" with library={"title": } %}')


class DjangoTests(unittest.TestCase, TestsBase):

    TemplateSyntaxError = DjangoTemplateSyntaxError

    def render(self, template, context=None):
        context = context or {}
        template = '{% load chartkick %}' + template
        t = Template(template)
        c = Context(context)
        return t.render(c)


class Jinja2Tests(unittest.TestCase, TestsBase):

    TemplateSyntaxError = Jinja2TemplateSyntaxError

    def render(self, template, context=None):
        context = context or {}
        env = Environment(extensions=['chartkick.ext.charts'])
        env.loader = FileSystemLoader('.')
        return env.from_string(template).render(context)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
