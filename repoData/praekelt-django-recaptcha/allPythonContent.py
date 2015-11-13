__FILENAME__ = client
import django
if django.VERSION[1] >= 5:
    import json
else:
    from django.utils import simplejson as json

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import get_language

from captcha._compat import want_bytes, urlencode, Request, urlopen, PY2

DEFAULT_API_SSL_SERVER = "https://www.google.com/recaptcha/api"
DEFAULT_API_SERVER = "http://www.google.com/recaptcha/api"
DEFAULT_VERIFY_SERVER = "www.google.com"
DEFAULT_WIDGET_TEMPLATE = 'captcha/widget.html'
DEFAULT_WIDGET_TEMPLATE_AJAX = 'captcha/widget_ajax.html'

API_SSL_SERVER = getattr(settings, "CAPTCHA_API_SSL_SERVER",
                         DEFAULT_API_SSL_SERVER)
API_SERVER = getattr(settings, "CAPTCHA_API_SERVER", DEFAULT_API_SERVER)
VERIFY_SERVER = getattr(settings, "CAPTCHA_VERIFY_SERVER",
                        DEFAULT_VERIFY_SERVER)

if getattr(settings, "CAPTCHA_AJAX", False):
    WIDGET_TEMPLATE = getattr(settings, "CAPTCHA_WIDGET_TEMPLATE",
                              DEFAULT_WIDGET_TEMPLATE_AJAX)
else:
    WIDGET_TEMPLATE = getattr(settings, "CAPTCHA_WIDGET_TEMPLATE",
                              DEFAULT_WIDGET_TEMPLATE)


RECAPTCHA_SUPPORTED_LANUAGES = ('en', 'nl', 'fr', 'de', 'pt', 'ru', 'es', 'tr')


class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code


def displayhtml(public_key,
                attrs,
                use_ssl=False,
                error=None):
    """Gets the HTML to display for reCAPTCHA

    public_key -- The public api key
    use_ssl -- Should the request be sent over ssl?
    error -- An error message to display (from RecaptchaResponse.error_code)"""

    error_param = ''
    if error:
        error_param = '&error=%s' % error

    if use_ssl:
        server = API_SSL_SERVER
    else:
        server = API_SERVER

    if not 'lang' in attrs:
        attrs['lang'] = get_language()[:2]

    return render_to_string(
        WIDGET_TEMPLATE,
        {'api_server': server,
         'public_key': public_key,
         'error_param': error_param,
         'lang': attrs['lang'],
         'options': mark_safe(json.dumps(attrs, indent=2))
         })


def submit(recaptcha_challenge_field,
           recaptcha_response_field,
           private_key,
           remoteip,
           use_ssl=False):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    recaptcha_challenge_field -- The value of recaptcha_challenge_field
    from the form
    recaptcha_response_field -- The value of recaptcha_response_field
    from the form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's ip address
    """

    if not (recaptcha_response_field and recaptcha_challenge_field and
            len(recaptcha_response_field) and len(recaptcha_challenge_field)):
        return RecaptchaResponse(
            is_valid=False,
            error_code='incorrect-captcha-sol'
        )

    params = urlencode({
        'privatekey': want_bytes(private_key),
        'remoteip':  want_bytes(remoteip),
        'challenge':  want_bytes(recaptcha_challenge_field),
        'response':  want_bytes(recaptcha_response_field),
    })

    if not PY2:
        params = params.encode('utf-8')

    if use_ssl:
        verify_url = 'https://%s/recaptcha/api/verify' % VERIFY_SERVER
    else:
        verify_url = 'http://%s/recaptcha/api/verify' % VERIFY_SERVER

    req = Request(
        url=verify_url,
        data=params,
        headers={
            'Content-type': 'application/x-www-form-urlencoded',
            'User-agent': 'reCAPTCHA Python'
        }
    )

    httpresp = urlopen(req)

    return_values = httpresp.read().splitlines()
    httpresp.close()

    return_code = return_values[0]
    if not PY2:
        return_code = return_code.decode('utf-8')

    if (return_code == "true"):
        return RecaptchaResponse(is_valid=True)
    else:
        return RecaptchaResponse(is_valid=False, error_code=return_values[1])

########NEW FILE########
__FILENAME__ = fields
import os
import sys

from django import forms
from django.conf import settings
try:
    from django.utils.encoding import smart_unicode
except ImportError:
    from django.utils.encoding import smart_text as smart_unicode

from django.utils.translation import ugettext_lazy as _

from captcha import client
from captcha.widgets import ReCaptcha


class ReCaptchaField(forms.CharField):
    default_error_messages = {
        'captcha_invalid': _('Incorrect, please try again.')
    }

    def __init__(self, public_key=None, private_key=None, use_ssl=None, \
            attrs={}, *args, **kwargs):
        """
        ReCaptchaField can accepts attributes which is a dictionary of
        attributes to be passed ot the ReCaptcha widget class. The widget will
        loop over any options added and create the RecaptchaOptions
        JavaScript variables as specified in
        https://code.google.com/apis/recaptcha/docs/customization.html
        """
        public_key = public_key if public_key else settings.\
                RECAPTCHA_PUBLIC_KEY
        self.private_key = private_key if private_key else \
                settings.RECAPTCHA_PRIVATE_KEY
        self.use_ssl = use_ssl if use_ssl != None else getattr(settings, \
                'RECAPTCHA_USE_SSL', False)

        self.widget = ReCaptcha(public_key=public_key, use_ssl=self.use_ssl, \
                attrs=attrs)
        self.required = True
        super(ReCaptchaField, self).__init__(*args, **kwargs)

    def get_remote_ip(self):
        f = sys._getframe()
        while f:
            if 'request' in f.f_locals:
                request = f.f_locals['request']
                if request:
                    remote_ip = request.META.get('REMOTE_ADDR', '')
                    forwarded_ip = request.META.get('HTTP_X_FORWARDED_FOR', '')
                    ip = remote_ip if not forwarded_ip else forwarded_ip
                    return ip
            f = f.f_back

    def clean(self, values):
        super(ReCaptchaField, self).clean(values[1])
        recaptcha_challenge_value = smart_unicode(values[0])
        recaptcha_response_value = smart_unicode(values[1])

        if os.environ.get('RECAPTCHA_TESTING', None) == 'True' and \
                recaptcha_response_value == 'PASSED':
            return values[0]

        check_captcha = client.submit(recaptcha_challenge_value, \
                recaptcha_response_value, private_key=self.private_key, \
                remoteip=self.get_remote_ip(), use_ssl=self.use_ssl)
        if not check_captcha.is_valid:
            raise forms.util.ValidationError(
                self.error_messages['captcha_invalid']
            )
        return values[0]

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
import os
import unittest

from captcha import fields
from django.forms import Form


class TestForm(Form):
    captcha = fields.ReCaptchaField(attrs={'theme': 'white'})

class TestCase(unittest.TestCase):

    def setUp(self):
        os.environ['RECAPTCHA_TESTING'] = 'True'

    def test_envvar_enabled(self):
        form_params = {'recaptcha_response_field': 'PASSED'}
        form = TestForm(form_params)
        self.assertTrue(form.is_valid())

    def test_envvar_disabled(self):
        os.environ['RECAPTCHA_TESTING'] = 'False'
        form_params = {'recaptcha_response_field': 'PASSED'}
        form = TestForm(form_params)
        self.assertFalse(form.is_valid())

    def tearDown(self):
        del os.environ['RECAPTCHA_TESTING']

########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe

from captcha import client


class ReCaptcha(forms.widgets.Widget):
    recaptcha_challenge_name = 'recaptcha_challenge_field'
    recaptcha_response_name = 'recaptcha_response_field'

    def __init__(self, public_key=None, use_ssl=None, attrs={}, *args, \
            **kwargs):
        self.public_key = public_key if public_key else \
                settings.RECAPTCHA_PUBLIC_KEY
        self.use_ssl = use_ssl if use_ssl != None else getattr(settings, \
                'RECAPTCHA_USE_SSL', False)
        self.js_attrs = attrs
        super(ReCaptcha, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        return mark_safe(u'%s' % client.displayhtml(self.public_key, \
                self.js_attrs, use_ssl=self.use_ssl))

    def value_from_datadict(self, data, files, name):
        return [data.get(self.recaptcha_challenge_name, None),
            data.get(self.recaptcha_response_name, None)]

########NEW FILE########
__FILENAME__ = _compat
import sys

PY2 = sys.version_info[0] == 2
if PY2:
    text_type = unicode
    from urllib2 import Request, urlopen
    from urllib import urlencode
else:
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    text_type = str


def want_bytes(s, encoding='utf-8', errors='strict'):
    if isinstance(s, text_type):
        s = s.encode(encoding, errors)
    return s

########NEW FILE########
__FILENAME__ = test_settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.sqlite',
    }
}

INSTALLED_APPS = [
    'captcha',
]

RECAPTCHA_PRIVATE_KEY = 'privkey'
RECAPTCHA_PUBLIC_KEY = 'pubkey'

########NEW FILE########
