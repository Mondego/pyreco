__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from django.conf import settings

JS_VAR_NAME = getattr(settings, 'JS_REVERSE_JS_VAR_NAME', 'Urls')
########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}
SECRET_KEY = 'wtf'
ROOT_URLCONF = None
USE_TZ = True
INSTALLED_APPS = (
    'django_js_reverse',
)
ALLOWED_HOSTS = ['testserver']
########NEW FILE########
__FILENAME__ = test_urls
#-*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include


pattern_ns_1 = patterns('',
                        url(r'^ns1_1/$', 'foo', name='ns1_1'),
                        url(r'^ns1_2/$', 'foo', name='ns1_2'))

pattern_ns_2 = patterns('',
                        url(r'^ns2_1/$', 'foo', name='ns2_1'),
                        url(r'^ns2_2/$', 'foo', name='ns2_2'))

pattern_ns = patterns('',
                      url(r'^ns1/$', include(pattern_ns_1,  namespace='ns1')),
                      url(r'^ns2/$', include(pattern_ns_2,  namespace='ns2')))

urlpatterns = patterns('',
                       url(r'^jsreverse/$', 'django_js_reverse.views.urls_js', name='js_reverse'),

                       # test urls
                       url(r'^test_no_url_args/$', 'foo',
                           name='test_no_url_args'),
                       url(r'^test_one_url_args/(?P<arg_one>[-\w]+)/$', 'foo',
                           name='test_one_url_args'),
                       url(r'^test_two_url_args/(?P<arg_one>[-\w]+)-(?P<arg_two>[-\w]+)/$', 'foo',
                           name='test_two_url_args'),
                       url(r'^test_unicode_url_name/$', 'foo',
                           name=u'test_unicode_url_name'),
                       # test namespace
                       url(r'^ns/$', include(pattern_ns_2,  namespace='ns2'))
)
########NEW FILE########
__FILENAME__ = unit_tests
#!/usr/bin/env python
#-*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.test.client import Client
from django.utils import unittest
from django.test import TestCase
from django.test.utils import override_settings


class JSReverseViewTestCase(TestCase):
    client = None
    urls = 'django_js_reverse.tests.test_urls'

    def setUp(self):
        self.client = Client()

    def test_view_no_url_args(self):
        response = self.client.post('/jsreverse/')
        self.assertContains(response, "'test_no_url_args', ['test_no_url_args/', []]")

    def test_view_one_url_arg(self):
        response = self.client.post('/jsreverse/')
        self.assertContains(response, "'test_one_url_args', ['test_one_url_args/%(arg_one)s/', ['arg_one']]")

    def test_view_two_url_args(self):
        response = self.client.post('/jsreverse/')
        self.assertContains(
            response, "test_two_url_args', ['test_two_url_args/%(arg_one)s\\u002D%(arg_two)s/', ['arg_one','arg_two']]")

    def test_unicode_url_name(self):
        response = self.client.post('/jsreverse/')
        self.assertContains(response, "'test_unicode_url_name', ['test_unicode_url_name/', []]")

    @override_settings(JS_REVERSE_JS_VAR_NAME='Foo')
    def _test_js_var_name_changed_valid(self):
        # This test overrides JS_REVERSE_JS_VAR_NAME permanent, so it's disabled by default.
        # Needs to by tested as single test case
        response = self.client.post('/jsreverse/')
        self.assertContains(response, 'this.Foo = (function () {')

    @override_settings(JS_REVERSE_JS_VAR_NAME='1test')
    def _test_js_var_name_changed_invalid(self):
        # This test overrides JS_REVERSE_JS_VAR_NAME permanent, so it's disabled by default.
        # Needs to by tested as single test case
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/jsreverse/')


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..') + os.sep)
    unittest.main()
########NEW FILE########
__FILENAME__ = views
#-*- coding: utf-8 -*-
import re
import sys
if sys.version < '3':
    text_type = unicode
else:
    text_type = str

from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core import urlresolvers
from .settings import JS_VAR_NAME


def urls_js(request):
    if not re.match(r'^[$A-Z_][\dA-Z_$]*$', JS_VAR_NAME.upper()):
        raise ImproperlyConfigured(
            'JS_REVERSE_JS_VAR_NAME setting "%s" is not a valid javascript identifier.' % (JS_VAR_NAME))

    url_patterns = list(urlresolvers.get_resolver(None).reverse_dict.items())
    url_list = [(url_name, url_pattern[0][0]) for url_name, url_pattern in url_patterns if
                (isinstance(url_name, str) or isinstance(url_name, text_type))]

    return render_to_response('django_js_reverse/urls_js.tpl',
                              {
                                  'urls': url_list,
                                  'url_prefix': urlresolvers.get_script_prefix(),
                                  'js_var_name': JS_VAR_NAME
                              },
                              context_instance=RequestContext(request), mimetype='application/javascript')

########NEW FILE########
