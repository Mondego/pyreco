__FILENAME__ = bootstrap
#!/usr/bin/env python
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if is_jython:
    import subprocess
    
    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd', 
           quote(tmpeggs), 'zc.buildout'], 
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('setuptools')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout',
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('setuptools')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout')
import zc.buildout.buildout
zc.buildout.buildout.main(sys.argv[1:] + ['bootstrap'])
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = baseconv
"""
Convert numbers from base 10 integers to base X strings and back again.

Original: http://www.djangosnippets.org/snippets/1431/

Sample usage:

>>> base20 = BaseConverter('0123456789abcdefghij')
>>> base20.from_decimal(1234)
'31e'
>>> base20.to_decimal('31e')
1234
"""

class BaseConverter(object):
    decimal_digits = "0123456789"
    
    def __init__(self, digits):
        self.digits = digits
    
    def from_decimal(self, i):
        return self.convert(i, self.decimal_digits, self.digits)
    
    def to_decimal(self, s):
        return int(self.convert(s, self.digits, self.decimal_digits))
    
    def convert(number, fromdigits, todigits):
        # Based on http://code.activestate.com/recipes/111286/
        if str(number)[0] == '-':
            number = str(number)[1:]
            neg = 1
        else:
            neg = 0

        # make an integer out of the number
        x = 0
        for digit in str(number):
           x = x * len(fromdigits) + fromdigits.index(digit)
    
        # create the result in base 'len(todigits)'
        if x == 0:
            res = todigits[0]
        else:
            res = ""
            while x > 0:
                digit = x % len(todigits)
                res = todigits[digit] + res
                x = int(x / len(todigits))
            if neg:
                res = '-' + res
        return res
    convert = staticmethod(convert)

bin = BaseConverter('01')
hexconv = BaseConverter('0123456789ABCDEF')
base62 = BaseConverter(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz'
)
########NEW FILE########
__FILENAME__ = models
# This file intentionally left blank.
########NEW FILE########
__FILENAME__ = shorturl
import urlparse
from django import template
from django.conf import settings
from django.core import urlresolvers
from django.utils.safestring import mark_safe
from shorturls.baseconv import base62

class ShortURL(template.Node):
    @classmethod
    def parse(cls, parser, token):
        parts = token.split_contents()
        if len(parts) != 2:
            raise template.TemplateSyntaxError("%s takes exactly one argument" % parts[0])
        return cls(template.Variable(parts[1]))
        
    def __init__(self, obj):
        self.obj = obj
        
    def render(self, context):
        try:
            obj = self.obj.resolve(context)
        except template.VariableDoesNotExist:
            return ''
            
        try:
            prefix = self.get_prefix(obj)
        except (AttributeError, KeyError):
            return ''
        
        tinyid = base62.from_decimal(obj.pk)
                
        if hasattr(settings, 'SHORT_BASE_URL') and settings.SHORT_BASE_URL:
            return urlparse.urljoin(settings.SHORT_BASE_URL, prefix+tinyid)
        
        try:
            return urlresolvers.reverse('shorturls.views.redirect', kwargs = {
                'prefix': prefix,
                'tiny': tinyid
            })
        except urlresolvers.NoReverseMatch:
            return ''
            
    def get_prefix(self, model):
        if not hasattr(self.__class__, '_prefixmap'):
            self.__class__._prefixmap = dict((m,p) for p,m in settings.SHORTEN_MODELS.items())
        key = '%s.%s' % (model._meta.app_label, model.__class__.__name__.lower())
        return self.__class__._prefixmap[key]
        
class RevCanonical(ShortURL):
    def render(self, context):
        url = super(RevCanonical, self).render(context)
        if url:
            return mark_safe('<link rev="canonical" href="%s">' % url)
        else:
            return ''

register = template.Library()
register.tag('shorturl', ShortURL.parse)
register.tag('revcanonical', RevCanonical.parse)
########NEW FILE########
__FILENAME__ = models
"""
A handful of test modules to test out resolving redirects.
"""

from django.db import models

class Animal(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'shorturls'

    def __unicode__(self):
        return self.name
        
    def get_absolute_url(self):
        return '/animal/%s/' % self.id
        
class Vegetable(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'shorturls'

    def __unicode__(self):
        return self.name
        
    def get_absolute_url(self):
        return 'http://example.net/veggies/%s' % self.id
    
class Mineral(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'shorturls'

    def __unicode__(self):
        return self.name
########NEW FILE########
__FILENAME__ = test_baseconv
import unittest
from shorturls import baseconv

class BaseConvTests(unittest.TestCase):
    
    def _test_converter(self, converter):
        nums = [-10 ** 10, 10 ** 10] + range(-100, 100)
        for before in nums:
            after = converter.to_decimal(converter.from_decimal(before))
            self.assertEqual(before, after)
            
    def test_bin(self):
        self._test_converter(baseconv.bin)
        
    def test_hex(self):
        self._test_converter(baseconv.hexconv)
        
    def test_base62(self):
        self._test_converter(baseconv.base62)
########NEW FILE########
__FILENAME__ = test_templatetag
from django import template
from django.conf import settings
from django.test import TestCase
from shorturls.tests.models import Animal, Vegetable, Mineral

class RedirectViewTestCase(TestCase):
    urls = 'shorturls.urls'
    fixtures = ['shorturls-test-data.json']

    def setUp(self):
        self.old_shorten = getattr(settings, 'SHORTEN_MODELS', None)
        self.old_base = getattr(settings, 'SHORT_BASE_URL', None)
        settings.SHORT_BASE_URL = None
        settings.SHORTEN_MODELS = {
            'A': 'shorturls.animal',
            'V': 'shorturls.vegetable',
        }
        
    def tearDown(self):
        if self.old_shorten is not None:
            settings.SHORTEN_MODELS = self.old_shorten
        if self.old_base is not None:
            settings.SHORT_BASE_URL = self.old_base

    def render(self, t, **c):
        return template.Template('{% load shorturl %}'+t).render(c)
        
    def test_shorturl(self):
        r = self.render('{% shorturl a %}', a=Animal.objects.get(id=12345))
        self.assertEqual(r, '/ADNH')
        
    def test_bad_context(self):
        r = self.render('{% shorturl a %}')
        self.assertEqual(r, '')

    def test_no_prefix(self):
        r = self.render('{% shorturl m %}', m=Mineral.objects.all()[0])
        self.assertEqual(r, '')
        
    def test_short_base_url(self):
        settings.SHORT_BASE_URL = 'http://example.com/'
        r = self.render('{% shorturl a %}', a=Animal.objects.get(id=12345))
        self.assertEqual(r, 'http://example.com/ADNH')
        
    def test_revcanonical(self):
        r = self.render('{% revcanonical a %}', a=Animal.objects.get(id=12345))
        self.assertEqual(r, '<link rev="canonical" href="/ADNH">')
        
########NEW FILE########
__FILENAME__ = test_views
from django.conf import settings
from django.http import Http404
from django.test import TestCase
from shorturls.baseconv import base62

class RedirectViewTestCase(TestCase):
    urls = 'shorturls.urls'
    fixtures = ['shorturls-test-data.json']
    
    def setUp(self):
        self.old_shorten = getattr(settings, 'SHORTEN_MODELS', None)
        self.old_base = getattr(settings, 'SHORTEN_FULL_BASE_URL', None)
        settings.SHORTEN_MODELS = {
            'A': 'shorturls.animal',
            'V': 'shorturls.vegetable',
            'M': 'shorturls.mineral',
            'bad': 'not.amodel',
            'bad2': 'not.even.valid',
        }
        settings.SHORTEN_FULL_BASE_URL = 'http://example.com'
        
    def tearDown(self):
        if self.old_shorten is not None:
            settings.SHORTEN_MODELS = self.old_shorten
        if self.old_base is not None:
            settings.SHORTEN_FULL_BASE_URL = self.old_base
    
    def test_redirect(self):
        """
        Test the basic operation of a working redirect.
        """
        response = self.client.get('/A%s' % enc(12345))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'http://example.com/animal/12345/')
        
    def test_redirect_from_request(self):
        """
        Test a relative redirect when the Sites app isn't installed.
        """
        settings.SHORTEN_FULL_BASE_URL = None
        response = self.client.get('/A%s' % enc(54321), HTTP_HOST='example.org')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'http://example.org/animal/54321/')
        
    def test_redirect_complete_url(self):
        """
        Test a redirect when the object returns a complete URL.
        """
        response = self.client.get('/V%s' % enc(785))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'http://example.net/veggies/785')
        
    def test_bad_short_urls(self):
        self.assertEqual(404, self.client.get('/badabcd').status_code)
        self.assertEqual(404, self.client.get('/bad2abcd').status_code)
        self.assertEqual(404, self.client.get('/Vssssss').status_code)

    def test_model_without_get_absolute_url(self):
        self.assertEqual(404, self.client.get('/M%s' % enc(10101)).status_code)
        
def enc(id):
    return base62.from_decimal(id)

########NEW FILE########
__FILENAME__ = testsettings
import os

DEBUG = TEMPLATE_DEBUG = True
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/shorturls.db'
INSTALLED_APPS = ['shorturls']
ROOT_URLCONF = ['shorturls.urls']
TEMPLATE_DIRS = os.path.join(os.path.dirname(__file__), 'tests', 'templates')
########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('', 
    url(
        regex = '^(?P<prefix>%s)(?P<tiny>\w+)$' % '|'.join(settings.SHORTEN_MODELS.keys()),
        view  = 'shorturls.views.redirect',
    ),
)
########NEW FILE########
__FILENAME__ = views
import urlparse
from django.conf import settings
from django.contrib.sites.models import Site, RequestSite
from django.db import models
from django.http import HttpResponsePermanentRedirect, Http404
from django.shortcuts import get_object_or_404
from shorturls.baseconv import base62

def redirect(request, prefix, tiny):
    """
    Redirect to a given object from a short URL.
    """
    # Resolve the prefix and encoded ID into a model object and decoded ID.
    # Many things here could go wrong -- bad prefix, bad value in 
    # SHORTEN_MODELS, no such model, bad encoding -- so just return a 404 if
    # any of that stuff goes wrong.
    try:
        app_label, model_name = settings.SHORTEN_MODELS[prefix].split('.')
        model = models.get_model(app_label, model_name)
        if not model: raise ValueError
        id = base62.to_decimal(tiny)
    except (AttributeError, ValueError, KeyError):
        raise Http404('Bad prefix, model, SHORTEN_MODELS, or encoded ID.')
    
    # Try to look up the object. If it's not a valid object, or if it doesn't
    # have an absolute url, bail again.
    obj = get_object_or_404(model, pk=id)
    try:
        url = obj.get_absolute_url()
    except AttributeError:
        raise Http404("'%s' models don't have a get_absolute_url() method." % model.__name__)
    
    # We might have to translate the URL -- the badly-named get_absolute_url
    # actually returns a domain-relative URL -- into a fully qualified one.
    
    # If we got a fully-qualified URL, sweet.
    if urlparse.urlsplit(url)[0]:
        return HttpResponsePermanentRedirect(url)
    
    # Otherwise, we need to make a full URL by prepending a base URL.
    # First, look for an explicit setting.
    if hasattr(settings, 'SHORTEN_FULL_BASE_URL') and settings.SHORTEN_FULL_BASE_URL:
        base = settings.SHORTEN_FULL_BASE_URL
        
    # Next, if the sites app is enabled, redirect to the current site.
    elif Site._meta.installed:
        base = 'http://%s/' % Site.objects.get_current().domain
        
    # Finally, fall back on the current request.
    else:
        base = 'http://%s/' % RequestSite(request).domain
        
    return HttpResponsePermanentRedirect(urlparse.urljoin(base, url))
########NEW FILE########
