__FILENAME__ = bootstrap
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
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser()
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=False,
                   help="Use Disribute rather than Setuptools.")

parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
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

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse(requirement)).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse(requirement)).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = settings
import os

DIRNAME = os.path.dirname(__file__)

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/tmp/postal.db', # Or path to database file if using sqlite3.
        'USER': '', # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '', # Set to empty string for default. Not used with sqlite3.
    }
}

SITE_ID = 1

MEDIA_ROOT = DIRNAME + "/media"
MEDIA_URL = '/site_media/'

TEMPLATE_DIRS = (
    os.path.join(DIRNAME, "templates"),
)

INSTALLED_APPS = ['django.contrib.admin',
                  'django.contrib.auth',
                  'django.contrib.contenttypes',
                  'django.contrib.sessions',
                  'django.contrib.sites',
                  'django_countries',
                  'postal', ]
ROOT_URLCONF = 'postal_project.urls'

SECRET_KEY = "abc123"

POSTAL_ADDRESS_L10N = True
########NEW FILE########
__FILENAME__ = urls
import os

from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns("",
    (r'^admin/(.*)', include(admin.site.urls)),
    (r'^postal/', include('postal.urls')),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': os.path.join(settings.DIRNAME, "media"), 'show_indexes': True }),
    url(r'^$', 'postal_project.views.test_postal', name="postal-home"),
    url(r'^json$', 'postal_project.views.test_postal_json', name="postal-home"),

)

########NEW FILE########
__FILENAME__ = views
from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from postal.library import country_map
from postal.forms import PostalAddressForm


def test_postal(request):
    countries = []
    for k,v in country_map.items():
        countries.append(k)
    
    result = ""
    if request.method == "POST":
        form = PostalAddressForm(request.POST, prefix=request.POST.get('prefix', ''))
        if form.is_valid():
            for k,v in form.cleaned_data.items():
                result = result + k + " -> " + v + "<br/>"
        context = RequestContext(request, locals())
        return render_to_response('postal/test.html', context)
    else:
        form = PostalAddressForm() # An unbound form
        
    context = RequestContext(request, locals())    
    return render_to_response('postal/test.html', context)

def test_postal_json(request):
    countries = []
    for k,v in country_map.items():
        countries.append(k)
    
    result = ""
    if request.method == "POST":
        form = PostalAddressForm(request.POST, prefix=request.POST.get('prefix', ''))
        if form.is_valid():
            for k,v in form.cleaned_data.items():
                result = result + k + " -> " + v + "<br/>"
        context = RequestContext(request, locals())
        return render_to_response('postal/test.html', context)
    else:
        form = PostalAddressForm() # An unbound form
        
    context = RequestContext(request, locals())    
    return render_to_response('postal/test_json.html', context)
########NEW FILE########
__FILENAME__ = handlers
from piston.handler import BaseHandler
from postal.library import form_factory

class PostalHandler(BaseHandler):
    allowed_methods = ('GET',)      
    def read(self, request):        
        iso_code=request.GET.get('country', '')
        json = {}
        form_class = form_factory(country_code=iso_code)
        form_obj = form_class()
        for k,v in form_obj.fields.items():
            if k not in json.keys():
                json[k] = {}
            json[k]['label'] = unicode(v.label)
            json[k]['widget'] =  v.widget.render(k,"", attrs={'id': 'id_' + k})
        return json
       

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from piston.resource import Resource
from postal.api.handlers import PostalHandler

postal_handler = Resource(PostalHandler)

urlpatterns = patterns('',
   url(r'^country/$', postal_handler, name="postal-api-country"),   
)

########NEW FILE########
__FILENAME__ = forms
""" http://www.bitboost.com/ref/international-address-formats.html """
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.ar.forms import ARProvinceSelect, ARPostalCodeField

from postal.forms import PostalAddressForm

class ARPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=50)
    line2 = forms.CharField(label=_(u"Number"), max_length=50)
    city = forms.CharField(label=_(u"City"), max_length=50)
    state = forms.CharField(label=_(u"Province"), widget=ARProvinceSelect)
    code = ARPostalCodeField(label=_(u"Zip Code"))

    def __init__(self, *args, **kwargs):
        super(ARPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields['country'].initial = "AR"

########NEW FILE########
__FILENAME__ = forms
""" http://www.bitboost.com/ref/international-address-formats.html """
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.co.forms import CODepartmentSelect

from postal.forms import PostalAddressForm

class COPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    line2 = forms.CharField(label=_(u"Number"), max_length=100)
    state = forms.CharField(label=_(u"Department"), max_length=50, widget=CODepartmentSelect)

    def __init__(self, *args, **kwargs):
        super(COPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields['country'].initial = "CO"
        self.fields['code'].initial= '000000'
        self.fields['code'].widget = forms.HiddenInput()

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.cz.forms import CZPostalCodeField

from postal.forms import PostalAddressForm


class CZPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    city = forms.CharField(label=_(u"City"), max_length=100)
    code = CZPostalCodeField(label=_(u"Zip Code"))

    def __init__(self, *args, **kwargs):
        super(CZPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields.pop('line2')
        self.fields.pop('state')
        self.fields['country'].initial = "CZ"

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.de.forms import DEZipCodeField

from postal.forms import PostalAddressForm

class DEPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    city = forms.CharField(label=_(u"City"), max_length=100)
    code = DEZipCodeField(label=_(u"Zip Code"))

    def __init__(self, *args, **kwargs):
        super(DEPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields.pop('line2')
        self.fields.pop('state')
        self.fields['country'].initial = "DE"
        self.fields.keyOrder = ['line1', 'code', 'city', 'country']

########NEW FILE########
__FILENAME__ = forms
""" from http://www.bitboost.com/ref/international-address-formats.html#Great-Britain"""
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.gb.forms import GBPostcodeField, GBCountySelect

from postal.forms import PostalAddressForm

class GBPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    line2 = forms.CharField(label=_(u"Area"), required=False, max_length=100)
    city = forms.CharField(label=_(u"Town"), max_length=100)
    state = forms.CharField(label=_(u"County"), widget=GBCountySelect, max_length=100)
    code = GBPostcodeField(label=_(u"Postcode"))

    def __init__(self, *args, **kwargs):
        super(GBPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields['country'].initial = "GB"
########NEW FILE########
__FILENAME__ = forms
""" from http://homepages.iol.ie/~discover/mail.htm"""
from django import forms
from django.utils.translation import ugettext_lazy as _
from postal.forms import PostalAddressForm
from localflavor.ie.forms import IECountySelect


class IEPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    line2 = forms.CharField(label=_(u"Area"), max_length=100, required=False)
    city = forms.CharField(label=_(u"Town/City"), max_length=100)
    state = forms.CharField(label=_(u"County"), widget=IECountySelect(), max_length=100)

    class Meta:
        exclude = ('code',)

    def __init__(self, *args, **kwargs):
        super(IEPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields.pop('code')
        self.fields['country'].initial = "IE"

########NEW FILE########
__FILENAME__ = forms
""" http://www.bitboost.com/ref/international-address-formats.html """
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.mx.forms import MXStateSelect, MXZipCodeField

from postal.forms import PostalAddressForm

class MXPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    line2 = forms.CharField(label=_(u"Number"), max_length=100)
    city = forms.CharField(label=_(u"City"), max_length=100)
    state = forms.CharField(label=_(u"State"), widget=MXStateSelect)
    code = MXZipCodeField(label=_(u"Zip Code"))

    def __init__(self, *args, **kwargs):
        super(MXPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields['country'].initial = "MX"

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.nl.forms import NLZipCodeField

from postal.forms import PostalAddressForm

class NLPostalAddressForm(PostalAddressForm):    
    line1 = forms.CharField(label=_(u"Street"), required=False, max_length=100)
    line2 = forms.CharField(label=_(u"Area"), required=False, max_length=100)
    city = forms.CharField(label=_(u"Town/City"), required=False, max_length=100)
    code = NLZipCodeField(label=_(u"Zip Code"))
    
    
    class Meta:
        exclude = ('state',)
    
    def __init__(self, *args, **kwargs):
        super(NLPostalAddressForm, self).__init__(*args, **kwargs)
        # we have to manually pop the inherited line5
        self.fields.pop('state')
        self.fields['country'].initial = "NL"

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.pl.forms import PLPostalCodeField

from postal.forms import PostalAddressForm

class PLPostalAddressForm(PostalAddressForm):    
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    city = forms.CharField(label=_(u"City"), max_length=100)
    code = PLPostalCodeField(label=_(u"Zip code"))

    def __init__(self, *args, **kwargs):
        super(PLPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields.pop('line2')
        self.fields.pop('state')
        self.fields['country'].initial = "PL"

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.ru.forms import RUCountySelect, RURegionSelect, RUPostalCodeField, RUPostalCodeField

from postal.forms import PostalAddressForm

class RUPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=100)
    line2 = forms.CharField(label=_(u"Area"), required=False, max_length=100, widget=RURegionSelect)
    city = forms.CharField(label=_(u"City"), max_length=100)
    state = forms.CharField(label=_(u"County"), required=False, max_length=100, widget=RUCountySelect)
    code = RUPostalCodeField(label=_(u"Postal code"), required=False)

    def __init__(self, *args, **kwargs):
        super(RUPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields['country'].initial = "RU"

########NEW FILE########
__FILENAME__ = forms
""" http://www.bitboost.com/ref/international-address-formats.html """
from django import forms
from django.utils.translation import ugettext_lazy as _
from localflavor.us.forms import USStateField, USStateSelect, USZipCodeField

from postal.forms import PostalAddressForm

class USPostalAddressForm(PostalAddressForm):
    line1 = forms.CharField(label=_(u"Street"), max_length=50)
    line2 = forms.CharField(label=_(u"Area"), required=False, max_length=100)
    city = forms.CharField(label=_(u"City"), max_length=50)
    state = USStateField(label=_(u"US State"), widget=USStateSelect)
    code = USZipCodeField(label=_(u"Zip Code"))

    def __init__(self, *args, **kwargs):
        super(USPostalAddressForm, self).__init__(*args, **kwargs)
        self.fields['country'].initial = "US"

########NEW FILE########
__FILENAME__ = library
from django import forms
from postal import settings as postal_settings
from postal.forms import PostalAddressForm
from postal.forms.ar.forms import ARPostalAddressForm
from postal.forms.co.forms import COPostalAddressForm
from postal.forms.cz.forms import CZPostalAddressForm
from postal.forms.de.forms import DEPostalAddressForm
from postal.forms.gb.forms import GBPostalAddressForm
from postal.forms.ie.forms import IEPostalAddressForm
from postal.forms.mx.forms import MXPostalAddressForm
from postal.forms.nl.forms import NLPostalAddressForm
from postal.forms.pl.forms import PLPostalAddressForm
from postal.forms.ru.forms import RUPostalAddressForm
from postal.forms.us.forms import USPostalAddressForm

# TODO: Auto-import these forms
country_map = {
    "co": COPostalAddressForm,
    "cz": CZPostalAddressForm,
    "de": DEPostalAddressForm,
    "gb": GBPostalAddressForm,
    "ie": IEPostalAddressForm,
    "mx": MXPostalAddressForm,
    "nl": NLPostalAddressForm,
    "pl": PLPostalAddressForm,
    "ru": RUPostalAddressForm,
    "us": USPostalAddressForm,
    "ar": ARPostalAddressForm,
}


def form_factory(country_code=None):
    if country_code is not None:
        if postal_settings.POSTAL_ADDRESS_L10N:
            return country_map.get(country_code.lower(), PostalAddressForm)

    return PostalAddressForm

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

POSTAL_ADDRESS_L10N = getattr(settings, 'POSTAL_ADDRESS_L10N', True)

# each address line is a tuple of format (field_label, required)
POSTAL_ADDRESS_LINE1 = getattr(settings, "POSTAL_ADDRESS_LINE1", (_(u"Street"), False))
POSTAL_ADDRESS_LINE2 = getattr(settings, "POSTAL_ADDRESS_LINE2", (_(u"Area"), False))
POSTAL_ADDRESS_CITY = getattr(settings, "POSTAL_ADDRESS_CITY", (_(u"City"), False))
POSTAL_ADDRESS_STATE = getattr(settings, "POSTAL_ADDRESS_STATE", (_(u"State"), False))
POSTAL_ADDRESS_CODE = getattr(settings, "POSTAL_ADDRESS_CODE", (_(u"Zip code"), False))
########NEW FILE########
__FILENAME__ = postal_tags
from django import template
from django.core.urlresolvers import reverse

register = template.Library()

@register.inclusion_tag('postal/monitor_country_change.html')
def monitor_country_change():
    return {
        'postal_url': reverse('changed_country'),
    }

########NEW FILE########
__FILENAME__ = test_l10n
from django.test import TestCase
from django.utils.translation import ugettext
from django import forms

from postal.library import form_factory
import postal.settings
import postal.forms


class PostalTests(TestCase):
    def test_environment(self):
        """Just make sure everything is set up correctly."""
        self.assert_(True)

    def test_get_ar_address(self):
        """
        Tests that we get the correct widget for Argentina
        """
        form_class = form_factory("ar")
        self.assertNotEqual(form_class, None)

        # only use required fields
        test_data = {
            'line1': 'Maipu',
            'line2': '270',
            'city': 'Ciudad de Buenos Aires',
            'state': 'B',
            'code': 'C1006ACT',
        }
        form = form_class(data=test_data)

        self.assertEqual(form.fields['line1'].label.lower(), "street")
        self.assertEqual(form.fields['line2'].label.lower(), "number")
        self.assertEqual(form.fields['city'].label.lower(), "city")
        self.assertEqual(form.fields['code'].label.lower(), "zip code")

    def test_get_de_address(self):
        """
        Tests that we get the correct widget for Germny
        """
        german_form_class = form_factory("de")
        self.assertNotEqual(german_form_class, None)

        # only use required fields
        test_data = {'code': '12345',}
        form = german_form_class(data=test_data)

        self.assertEqual(form.fields['line1'].label.lower(), "street")
        self.assertEqual(form.fields.has_key('line2'), False)
        self.assertEqual(form.fields['city'].label.lower(), "city")
        self.assertEqual(form.fields['code'].label.lower(), "zip code")

    def test_get_mx_address(self):
        """
        Tests that we get the correct widget for Mexico
        """
        mx_form_class = form_factory("mx")
        self.assertNotEqual(mx_form_class, None)

        # only use required fields
        test_data = {
            'line1': 'Avenida Reforma',
            'line2': '1110',
            'line3': 'Centro',
            'city': 'Puebla',
            'state': 'Puebla',
            'code': '12345'
        }
        form = mx_form_class(data=test_data)

        self.assertEqual(form.fields['line1'].label.lower(), 'street')
        self.assertEqual(form.fields['line2'].label.lower(), 'number')
        self.assertEqual(form.fields['city'].label.lower(), 'city')
        self.assertEqual(form.fields['state'].label.lower(), 'state')
        self.assertEqual(form.fields['code'].label.lower(), 'zip code')

        from localflavor.mx.forms import MXStateSelect, MXZipCodeField
        self.assertIsInstance(form.fields['state'].widget, MXStateSelect)
        self.assertIsInstance(form.fields['code'], MXZipCodeField)

    def test_get_co_address(self):
        """
        Tests that we get the correct widget for Colombia
        """
        co_form_class = form_factory("co")
        self.assertNotEqual(co_form_class, None)
        test_data = {
            'line1': 'Diagonal 25 G',
            'line2': '#95 a 55',
            'state': 'Bogota D.C.',
        }
        form = co_form_class(data=test_data)
        self.assertEqual(form.fields['line1'].label.lower(), "street")
        self.assertEqual(form.fields['line2'].label.lower(), "number")
        self.assertEqual(form.fields['city'].label.lower(), "city")
        self.assertEqual(form.fields['state'].label.lower(), "department")
        self.assertIsInstance(form.fields['code'].widget, forms.HiddenInput)

    def test_get_ie_address(self):
        """
        Tests that we get the correct widget for Ireland
        """
        irish_form_class = form_factory("ie")
        self.assertNotEqual(irish_form_class, None)

        # only use required fields
        test_data = {'line1': 'street', 'city': 'Tullamore',
                     'state': 'offaly',  }
        form = irish_form_class(data=test_data)

        self.assertEqual(form.fields['line1'].label.lower(), "street")
        self.assertEqual(form.fields['line2'].label.lower(), "area")
        self.assertEqual(form.fields['city'].label.lower(), "town/city")
        self.assertEqual(form.fields['state'].label.lower(), "county")

    def test_incorrect_country_code(self):
        """
        Tests that we don't throw an exception for an incorrect country code
        """
        no_country_form_class = form_factory("xx")
        self.assertNotEqual(no_country_form_class, None)

        form = no_country_form_class()

        self.assertEqual(form.fields['line1'].label.lower(), "street")
        self.assertEqual(form.fields['line2'].label.lower(), "area")
        self.assertEqual(form.fields['city'].label.lower(), "city")
        self.assertEqual(form.fields['state'].label.lower(), "state")
        self.assertEqual(form.fields['code'].label.lower(), "zip code")

    def test_set_default_address(self):
        # change line1 label and make it required
        postal.settings.POSTAL_ADDRESS_LINE1 = ('Crazy address label', True)
        # we have to reload the postal form for the setting above to take effect
        reload(postal.forms)
        form = postal.forms.PostalAddressForm(data={})
        self.assertEqual('Crazy address label' in form.as_p(), True)
        self.assertEqual('Company name' in form.as_p(), False)

        # create a blank form
        form = postal.forms.PostalAddressForm(data={})

        # Our form is invalid as line1 is now required
        self.assertEqual(form.is_valid(), False)

        form = postal.forms.PostalAddressForm(data={'line1': 'my street', 'country': 'DE'})
        self.assertEqual(form.is_valid(), True)

    def test_4_line_address(self):
        netherlands_form_class = form_factory("nl")
        self.assertNotEqual(netherlands_form_class, None)
        test_data = {'code': '1234AB'}
        form = netherlands_form_class(data=test_data)
        self.assertEqual(form.fields['line1'].label.lower(), "street")
        self.assertEqual(form.fields['line2'].label.lower(), "area")
        self.assertEqual(form.fields['city'].label.lower(), "town/city")
        self.assertEqual(form.fields.get('state'), None)
        self.assertEqual(form.fields['code'].label.lower(), "zip code")

    def test_no_localisation(self):
        postal.settings.POSTAL_ADDRESS_L10N = False
        postal.settings.POSTAL_ADDRESS_LINE1 = ('a', False)
        postal.settings.POSTAL_ADDRESS_LINE2 = ('b', False)
        postal.settings.POSTAL_ADDRESS_CITY = ('c', False)
        postal.settings.POSTAL_ADDRESS_STATE = ('d', False)
        postal.settings.POSTAL_ADDRESS_CODE = ('e', False)
        reload(postal.forms)
        reload(postal.library)

        noloc_form_class = form_factory("nl")
        self.assertNotEqual(noloc_form_class, None)
        test_data = {'code': '1234AB'}
        form = noloc_form_class(data=test_data)

        self.assertEqual(form.fields['line1'].label, "a")
        self.assertEqual(form.fields['line2'].label, "b")
        self.assertEqual(form.fields['city'].label, "c")
        self.assertEqual(form.fields['state'].label, 'd')
        self.assertEqual(form.fields['code'].label, "e")






########NEW FILE########
__FILENAME__ = test_widgets
from django.test import TestCase
from django.utils.translation import ugettext
from django import forms
from postal.library import form_factory
from postal import settings as postal_settings


class PostalWidgetsTests(TestCase):
    def test_environment(self):
        """Just make sure everything is set up correctly."""
        self.assert_(True)

    def test_ar_widgets(self):
        """
        Tests that we get the correct widget for Argentina
        """
        # enable L10N
        postal_settings.POSTAL_ADDRESS_L10N = True

        form_class = form_factory("ar")
        self.assertNotEqual(form_class, None)

        # only use required fields
        test_data = {
            'line1': 'Maipu',
            'line2': '270',
            'city': 'Ciudad de Buenos Aires',
            'state': 'B',
            'code': 'C1006ACT',
        }
        form = form_class(data=test_data)

        from localflavor.ar.forms import ARProvinceSelect, ARPostalCodeField
        self.assertIsInstance(form.fields['state'].widget, ARProvinceSelect)
        self.assertIsInstance(form.fields['code'], ARPostalCodeField)
        self.assertEqual(form.fields['country'].initial, 'AR')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns("",
            (r'^api/', include('postal.api.urls')),
            url(r'^update_postal_address/$', 'postal.views.changed_country', name="changed_country"),
        )
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson

from postal.library import form_factory

def address_inline(request, prefix="", country_code=None, template_name="postal/form.html"):
    """ Displays postal address with localized fields """
    
    country_prefix = "country"
    prefix = request.POST.get('prefix', prefix)
    
    if prefix:
        country_prefix = prefix + '-country'
    
    country_code = request.POST.get(country_prefix, country_code)
    form_class = form_factory(country_code=country_code)
    
    if request.method == "POST":
        data = {}
        for (key, val) in request.POST.items():
            if val is not None and len(val) > 0:
                data[key] = val
        data.update({country_prefix: country_code})
        
        form = form_class(prefix=prefix, initial=data)
    else:
        form = form_class(prefix=prefix)
        
    return render_to_string(template_name, RequestContext(request, {
        "form": form,
        "prefix": prefix,
    }))


def changed_country(request):
    result = simplejson.dumps({
        "postal_address": address_inline(request),
    })
    return HttpResponse(result)
########NEW FILE########
