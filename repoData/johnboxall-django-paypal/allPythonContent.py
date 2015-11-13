__FILENAME__ = admin
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from string import split as L
from django.contrib import admin
from paypal.pro.models import PayPalNVP


class PayPalNVPAdmin(admin.ModelAdmin):
    list_display = L("user method flag flag_code created_at")
admin.site.register(PayPalNVP, PayPalNVPAdmin)

########NEW FILE########
__FILENAME__ = creditcard
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapted from:
    - http://www.djangosnippets.org/snippets/764/
    - http://www.satchmoproject.com/trac/browser/satchmo/trunk/satchmo/apps/satchmo_utils/views.py
    - http://tinyurl.com/shoppify-credit-cards
"""
import re


# Well known card regular expressions.
CARDS = {
    'Visa': re.compile(r"^4\d{12}(\d{3})?$"),
    'Mastercard': re.compile(r"(5[1-5]\d{4}|677189)\d{10}$"),
    'Dinersclub': re.compile(r"^3(0[0-5]|[68]\d)\d{11}"),
    'Amex': re.compile("^3[47]\d{13}$"),
    'Discover': re.compile("^(6011|65\d{2})\d{12}$"),
}

# Well known test numbers
TEST_NUMBERS = [
    "378282246310005", "371449635398431", "378734493671000", "30569309025904",
    "38520000023237", "6011111111111117", "6011000990139424", "555555555554444",
    "5105105105105100", "4111111111111111", "4012888888881881", "4222222222222"
]

def verify_credit_card(number):
    """Returns the card type for given card number or None if invalid."""
    return CreditCard(number).verify()

class CreditCard(object):
    def __init__(self, number):
        self.number = number
	
    def is_number(self):
        """True if there is at least one digit in number."""
        self.number = re.sub(r'[^\d]', '', self.number)
        return self.number.isdigit()

    def is_mod10(self):
        """Returns True if number is valid according to mod10."""
        double = 0
        total = 0
        for i in range(len(self.number) - 1, -1, -1):
            for c in str((double + 1) * int(self.number[i])):
                total = total + int(c)
            double = (double + 1) % 2
        return (total % 10) == 0

    def is_test(self):
        """Returns True if number is a test card number."""
        return self.number in TEST_NUMBERS

    def get_type(self):
        """Return the type if it matches one of the cards."""
        for card, pattern in CARDS.iteritems():
            if pattern.match(self.number):
                return card
        return None

    def verify(self):
        """Returns the card type if valid else None."""
        if self.is_number() and not self.is_test() and self.is_mod10():
            return self.get_type()
        return None
########NEW FILE########
__FILENAME__ = fields
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from calendar import monthrange
from datetime import date

from django.db import models
from django import forms
from django.utils.translation import ugettext as _

from paypal.pro.creditcard import verify_credit_card


class CreditCardField(forms.CharField):
    """Form field for checking out a credit card."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 20)
        super(CreditCardField, self).__init__(*args, **kwargs)
        
    def clean(self, value):
        """Raises a ValidationError if the card is not valid and stashes card type."""
        self.card_type = verify_credit_card(value)
        if self.card_type is None:
            raise forms.ValidationError("Invalid credit card number.")
        return value


# Credit Card Expiry Fields from:
# http://www.djangosnippets.org/snippets/907/
class CreditCardExpiryWidget(forms.MultiWidget):
    """MultiWidget for representing credit card expiry date."""
    def decompress(self, value):
        if value:
            return [value.month, value.year]
        else:
            return [None, None]

    def format_output(self, rendered_widgets):
        html = u' / '.join(rendered_widgets)
        return u'<span style="white-space: nowrap">%s</span>' % html

class CreditCardExpiryField(forms.MultiValueField):
    EXP_MONTH = [(x, x) for x in xrange(1, 13)]
    EXP_YEAR = [(x, x) for x in xrange(date.today().year, date.today().year + 15)]

    default_error_messages = {
        'invalid_month': u'Enter a valid month.',
        'invalid_year': u'Enter a valid year.',
    }

    def __init__(self, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        
        fields = (
            forms.ChoiceField(choices=self.EXP_MONTH, error_messages={'invalid': errors['invalid_month']}),
            forms.ChoiceField(choices=self.EXP_YEAR, error_messages={'invalid': errors['invalid_year']}),
        )
        
        super(CreditCardExpiryField, self).__init__(fields, *args, **kwargs)
        self.widget = CreditCardExpiryWidget(widgets=[fields[0].widget, fields[1].widget])

    def clean(self, value):
        exp = super(CreditCardExpiryField, self).clean(value)
        if date.today() > exp:
            raise forms.ValidationError("The expiration date you entered is in the past.")
        return exp

    def compress(self, data_list):
        if data_list:
            if data_list[1] in forms.fields.EMPTY_VALUES:
                error = self.error_messages['invalid_year']
                raise forms.ValidationError(error)
            if data_list[0] in forms.fields.EMPTY_VALUES:
                error = self.error_messages['invalid_month']
                raise forms.ValidationError(error)
            year = int(data_list[1])
            month = int(data_list[0])
            # find last day of the month
            day = monthrange(year, month)[1]
            return date(year, month, day)
        return None


class CreditCardCVV2Field(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 4)
        super(CreditCardCVV2Field, self).__init__(*args, **kwargs)
        

# Country Field from:
# http://www.djangosnippets.org/snippets/494/
# http://xml.coverpages.org/country3166.html
COUNTRIES = (
    ('US', _('United States of America')),
    ('CA', _('Canada')),
    ('AD', _('Andorra')),
    ('AE', _('United Arab Emirates')),
    ('AF', _('Afghanistan')),
    ('AG', _('Antigua & Barbuda')),
    ('AI', _('Anguilla')),
    ('AL', _('Albania')),
    ('AM', _('Armenia')),
    ('AN', _('Netherlands Antilles')),
    ('AO', _('Angola')),
    ('AQ', _('Antarctica')),
    ('AR', _('Argentina')),
    ('AS', _('American Samoa')),
    ('AT', _('Austria')),
    ('AU', _('Australia')),
    ('AW', _('Aruba')),
    ('AZ', _('Azerbaijan')),
    ('BA', _('Bosnia and Herzegovina')),
    ('BB', _('Barbados')),
    ('BD', _('Bangladesh')),
    ('BE', _('Belgium')),
    ('BF', _('Burkina Faso')),
    ('BG', _('Bulgaria')),
    ('BH', _('Bahrain')),
    ('BI', _('Burundi')),
    ('BJ', _('Benin')),
    ('BM', _('Bermuda')),
    ('BN', _('Brunei Darussalam')),
    ('BO', _('Bolivia')),
    ('BR', _('Brazil')),
    ('BS', _('Bahama')),
    ('BT', _('Bhutan')),
    ('BV', _('Bouvet Island')),
    ('BW', _('Botswana')),
    ('BY', _('Belarus')),
    ('BZ', _('Belize')),
    ('CC', _('Cocos (Keeling) Islands')),
    ('CF', _('Central African Republic')),
    ('CG', _('Congo')),
    ('CH', _('Switzerland')),
    ('CI', _('Ivory Coast')),
    ('CK', _('Cook Iislands')),
    ('CL', _('Chile')),
    ('CM', _('Cameroon')),
    ('CN', _('China')),
    ('CO', _('Colombia')),
    ('CR', _('Costa Rica')),
    ('CU', _('Cuba')),
    ('CV', _('Cape Verde')),
    ('CX', _('Christmas Island')),
    ('CY', _('Cyprus')),
    ('CZ', _('Czech Republic')),
    ('DE', _('Germany')),
    ('DJ', _('Djibouti')),
    ('DK', _('Denmark')),
    ('DM', _('Dominica')),
    ('DO', _('Dominican Republic')),
    ('DZ', _('Algeria')),
    ('EC', _('Ecuador')),
    ('EE', _('Estonia')),
    ('EG', _('Egypt')),
    ('EH', _('Western Sahara')),
    ('ER', _('Eritrea')),
    ('ES', _('Spain')),
    ('ET', _('Ethiopia')),
    ('FI', _('Finland')),
    ('FJ', _('Fiji')),
    ('FK', _('Falkland Islands (Malvinas)')),
    ('FM', _('Micronesia')),
    ('FO', _('Faroe Islands')),
    ('FR', _('France')),
    ('FX', _('France, Metropolitan')),
    ('GA', _('Gabon')),
    ('GB', _('United Kingdom (Great Britain)')),
    ('GD', _('Grenada')),
    ('GE', _('Georgia')),
    ('GF', _('French Guiana')),
    ('GH', _('Ghana')),
    ('GI', _('Gibraltar')),
    ('GL', _('Greenland')),
    ('GM', _('Gambia')),
    ('GN', _('Guinea')),
    ('GP', _('Guadeloupe')),
    ('GQ', _('Equatorial Guinea')),
    ('GR', _('Greece')),
    ('GS', _('South Georgia and the South Sandwich Islands')),
    ('GT', _('Guatemala')),
    ('GU', _('Guam')),
    ('GW', _('Guinea-Bissau')),
    ('GY', _('Guyana')),
    ('HK', _('Hong Kong')),
    ('HM', _('Heard & McDonald Islands')),
    ('HN', _('Honduras')),
    ('HR', _('Croatia')),
    ('HT', _('Haiti')),
    ('HU', _('Hungary')),
    ('ID', _('Indonesia')),
    ('IE', _('Ireland')),
    ('IL', _('Israel')),
    ('IN', _('India')),
    ('IO', _('British Indian Ocean Territory')),
    ('IQ', _('Iraq')),
    ('IR', _('Islamic Republic of Iran')),
    ('IS', _('Iceland')),
    ('IT', _('Italy')),
    ('JM', _('Jamaica')),
    ('JO', _('Jordan')),
    ('JP', _('Japan')),
    ('KE', _('Kenya')),
    ('KG', _('Kyrgyzstan')),
    ('KH', _('Cambodia')),
    ('KI', _('Kiribati')),
    ('KM', _('Comoros')),
    ('KN', _('St. Kitts and Nevis')),
    ('KP', _('Korea, Democratic People\'s Republic of')),
    ('KR', _('Korea, Republic of')),
    ('KW', _('Kuwait')),
    ('KY', _('Cayman Islands')),
    ('KZ', _('Kazakhstan')),
    ('LA', _('Lao People\'s Democratic Republic')),
    ('LB', _('Lebanon')),
    ('LC', _('Saint Lucia')),
    ('LI', _('Liechtenstein')),
    ('LK', _('Sri Lanka')),
    ('LR', _('Liberia')),
    ('LS', _('Lesotho')),
    ('LT', _('Lithuania')),
    ('LU', _('Luxembourg')),
    ('LV', _('Latvia')),
    ('LY', _('Libyan Arab Jamahiriya')),
    ('MA', _('Morocco')),
    ('MC', _('Monaco')),
    ('MD', _('Moldova, Republic of')),
    ('MG', _('Madagascar')),
    ('MH', _('Marshall Islands')),
    ('ML', _('Mali')),
    ('MN', _('Mongolia')),
    ('MM', _('Myanmar')),
    ('MO', _('Macau')),
    ('MP', _('Northern Mariana Islands')),
    ('MQ', _('Martinique')),
    ('MR', _('Mauritania')),
    ('MS', _('Monserrat')),
    ('MT', _('Malta')),
    ('MU', _('Mauritius')),
    ('MV', _('Maldives')),
    ('MW', _('Malawi')),
    ('MX', _('Mexico')),
    ('MY', _('Malaysia')),
    ('MZ', _('Mozambique')),
    ('NA', _('Namibia')),
    ('NC', _('New Caledonia')),
    ('NE', _('Niger')),
    ('NF', _('Norfolk Island')),
    ('NG', _('Nigeria')),
    ('NI', _('Nicaragua')),
    ('NL', _('Netherlands')),
    ('NO', _('Norway')),
    ('NP', _('Nepal')),
    ('NR', _('Nauru')),
    ('NU', _('Niue')),
    ('NZ', _('New Zealand')),
    ('OM', _('Oman')),
    ('PA', _('Panama')),
    ('PE', _('Peru')),
    ('PF', _('French Polynesia')),
    ('PG', _('Papua New Guinea')),
    ('PH', _('Philippines')),
    ('PK', _('Pakistan')),
    ('PL', _('Poland')),
    ('PM', _('St. Pierre & Miquelon')),
    ('PN', _('Pitcairn')),
    ('PR', _('Puerto Rico')),
    ('PT', _('Portugal')),
    ('PW', _('Palau')),
    ('PY', _('Paraguay')),
    ('QA', _('Qatar')),
    ('RE', _('Reunion')),
    ('RO', _('Romania')),
    ('RU', _('Russian Federation')),
    ('RW', _('Rwanda')),
    ('SA', _('Saudi Arabia')),
    ('SB', _('Solomon Islands')),
    ('SC', _('Seychelles')),
    ('SD', _('Sudan')),
    ('SE', _('Sweden')),
    ('SG', _('Singapore')),
    ('SH', _('St. Helena')),
    ('SI', _('Slovenia')),
    ('SJ', _('Svalbard & Jan Mayen Islands')),
    ('SK', _('Slovakia')),
    ('SL', _('Sierra Leone')),
    ('SM', _('San Marino')),
    ('SN', _('Senegal')),
    ('SO', _('Somalia')),
    ('SR', _('Suriname')),
    ('ST', _('Sao Tome & Principe')),
    ('SV', _('El Salvador')),
    ('SY', _('Syrian Arab Republic')),
    ('SZ', _('Swaziland')),
    ('TC', _('Turks & Caicos Islands')),
    ('TD', _('Chad')),
    ('TF', _('French Southern Territories')),
    ('TG', _('Togo')),
    ('TH', _('Thailand')),
    ('TJ', _('Tajikistan')),
    ('TK', _('Tokelau')),
    ('TM', _('Turkmenistan')),
    ('TN', _('Tunisia')),
    ('TO', _('Tonga')),
    ('TP', _('East Timor')),
    ('TR', _('Turkey')),
    ('TT', _('Trinidad & Tobago')),
    ('TV', _('Tuvalu')),
    ('TW', _('Taiwan, Province of China')),
    ('TZ', _('Tanzania, United Republic of')),
    ('UA', _('Ukraine')),
    ('UG', _('Uganda')),
    ('UM', _('United States Minor Outlying Islands')),
    ('UY', _('Uruguay')),
    ('UZ', _('Uzbekistan')),
    ('VA', _('Vatican City State (Holy See)')),
    ('VC', _('St. Vincent & the Grenadines')),
    ('VE', _('Venezuela')),
    ('VG', _('British Virgin Islands')),
    ('VI', _('United States Virgin Islands')),
    ('VN', _('Viet Nam')),
    ('VU', _('Vanuatu')),
    ('WF', _('Wallis & Futuna Islands')),
    ('WS', _('Samoa')),
    ('YE', _('Yemen')),
    ('YT', _('Mayotte')),
    ('YU', _('Yugoslavia')),
    ('ZA', _('South Africa')),
    ('ZM', _('Zambia')),
    ('ZR', _('Zaire')),
    ('ZW', _('Zimbabwe')),
    ('ZZ', _('Unknown or unspecified country')),
)

class CountryField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('choices', COUNTRIES)
        super(CountryField, self).__init__(*args, **kwargs)
########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms

from paypal.pro.fields import CreditCardField, CreditCardExpiryField, CreditCardCVV2Field, CountryField


class PaymentForm(forms.Form):
    """Form used to process direct payments."""
    firstname = forms.CharField(255, label="First Name")
    lastname = forms.CharField(255, label="Last Name")
    street = forms.CharField(255, label="Street Address")
    city = forms.CharField(255, label="City")
    state = forms.CharField(255, label="State")
    countrycode = CountryField(label="Country", initial="US")
    zip = forms.CharField(32, label="Postal / Zip Code")
    acct = CreditCardField(label="Credit Card Number")
    expdate = CreditCardExpiryField(label="Expiration Date")
    cvv2 = CreditCardCVV2Field(label="Card Security Code")

    def process(self, request, item):
        """Process a PayPal direct payment."""
        from paypal.pro.helpers import PayPalWPP
        wpp = PayPalWPP(request) 
        params = self.cleaned_data
        params['creditcardtype'] = self.fields['acct'].card_type
        params['expdate'] = self.cleaned_data['expdate'].strftime("%m%Y")
        params['ipaddress'] = request.META.get("REMOTE_ADDR", "")
        params.update(item)
 
        # Create single payment:
        if 'billingperiod' not in params:
            response = wpp.doDirectPayment(params)

        # Create recurring payment:
        else:
            response = wpp.createRecurringPaymentsProfile(params, direct=True)
 
        return response


class ConfirmForm(forms.Form):
    """Hidden form used by ExpressPay flow to keep track of payer information."""
    token = forms.CharField(max_length=255, widget=forms.HiddenInput())
    PayerID = forms.CharField(max_length=255, widget=forms.HiddenInput())
########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import pprint
import time
import urllib
import urllib2

from django.conf import settings
from django.forms.models import fields_for_model
from django.utils.datastructures import MergeDict
from django.utils.http import urlencode

from paypal.pro.models import PayPalNVP, L


TEST = settings.PAYPAL_TEST
USER = settings.PAYPAL_WPP_USER 
PASSWORD = settings.PAYPAL_WPP_PASSWORD
SIGNATURE = settings.PAYPAL_WPP_SIGNATURE
VERSION = 54.0
BASE_PARAMS = dict(USER=USER , PWD=PASSWORD, SIGNATURE=SIGNATURE, VERSION=VERSION)
ENDPOINT = "https://api-3t.paypal.com/nvp"
SANDBOX_ENDPOINT = "https://api-3t.sandbox.paypal.com/nvp"
NVP_FIELDS = fields_for_model(PayPalNVP).keys()


def paypal_time(time_obj=None):
    """Returns a time suitable for PayPal time fields."""
    if time_obj is None:
        time_obj = time.gmtime()
    return time.strftime(PayPalNVP.TIMESTAMP_FORMAT, time_obj)
    
def paypaltime2datetime(s):
    """Convert a PayPal time string to a DateTime."""
    return datetime.datetime(*(time.strptime(s, PayPalNVP.TIMESTAMP_FORMAT)[:6]))


class PayPalError(TypeError):
    """Error thrown when something be wrong."""
    

class PayPalWPP(object):
    """
    Wrapper class for the PayPal Website Payments Pro.
    
    Website Payments Pro Integration Guide:
    https://cms.paypal.com/cms_content/US/en_US/files/developer/PP_WPP_IntegrationGuide.pdf

    Name-Value Pair API Developer Guide and Reference:
    https://cms.paypal.com/cms_content/US/en_US/files/developer/PP_NVPAPI_DeveloperGuide.pdf
    """
    def __init__(self, request, params=BASE_PARAMS):
        """Required - USER / PWD / SIGNATURE / VERSION"""
        self.request = request
        if TEST:
            self.endpoint = SANDBOX_ENDPOINT
        else:
            self.endpoint = ENDPOINT
        self.signature_values = params
        self.signature = urlencode(self.signature_values) + "&"

    def doDirectPayment(self, params):
        """Call PayPal DoDirectPayment method."""
        defaults = {"method": "DoDirectPayment", "paymentaction": "Sale"}
        required = L("creditcardtype acct expdate cvv2 ipaddress firstname lastname street city state countrycode zip amt")
        nvp_obj = self._fetch(params, required, defaults)
        # @@@ Could check cvv2match / avscode are both 'X' or '0'
        # qd = django.http.QueryDict(nvp_obj.response)
        # if qd.get('cvv2match') not in ['X', '0']:
        #   nvp_obj.set_flag("Invalid cvv2match: %s" % qd.get('cvv2match')
        # if qd.get('avscode') not in ['X', '0']:
        #   nvp_obj.set_flag("Invalid avscode: %s" % qd.get('avscode')
        return not nvp_obj.flag

    def setExpressCheckout(self, params):
        """
        Initiates an Express Checkout transaction.
        Optionally, the SetExpressCheckout API operation can set up billing agreements for
        reference transactions and recurring payments.
        Returns a NVP instance - check for token and payerid to continue!
        """
        if self._is_recurring(params):
            params = self._recurring_setExpressCheckout_adapter(params)

        defaults = {"method": "SetExpressCheckout", "noshipping": 1}
        required = L("returnurl cancelurl amt")
        return self._fetch(params, required, defaults)

    def doExpressCheckoutPayment(self, params):
        """
        Check the dude out:
        """
        defaults = {"method": "DoExpressCheckoutPayment", "paymentaction": "Sale"}
        required =L("returnurl cancelurl amt token payerid")
        nvp_obj = self._fetch(params, required, defaults)
        return not nvp_obj.flag
        
    def createRecurringPaymentsProfile(self, params, direct=False):
        """
        Set direct to True to indicate that this is being called as a directPayment.
        Returns True PayPal successfully creates the profile otherwise False.
        """
        defaults = {"method": "CreateRecurringPaymentsProfile"}
        required = L("profilestartdate billingperiod billingfrequency amt")

        # Direct payments require CC data
        if direct:
            required + L("creditcardtype acct expdate firstname lastname")
        else:
            required + L("token payerid")

        nvp_obj = self._fetch(params, required, defaults)
        
        # Flag if profile_type != ActiveProfile
        return not nvp_obj.flag

    def getExpressCheckoutDetails(self, params):
        raise NotImplementedError

    def setCustomerBillingAgreement(self, params):
        raise DeprecationWarning

    def getTransactionDetails(self, params):
        raise NotImplementedError

    def massPay(self, params):
        raise NotImplementedError

    def getRecurringPaymentsProfileDetails(self, params):
        raise NotImplementedError

    def updateRecurringPaymentsProfile(self, params):
        raise NotImplementedError
    
    def billOutstandingAmount(self, params):
        raise NotImplementedError
        
    def manangeRecurringPaymentsProfileStatus(self, params):
        raise NotImplementedError
        
    def refundTransaction(self, params):
        raise NotImplementedError

    def _is_recurring(self, params):
        """Returns True if the item passed is a recurring transaction."""
        return 'billingfrequency' in params

    def _recurring_setExpressCheckout_adapter(self, params):
        """
        The recurring payment interface to SEC is different than the recurring payment
        interface to ECP. This adapts a normal call to look like a SEC call.
        """
        params['l_billingtype0'] = "RecurringPayments"
        params['l_billingagreementdescription0'] = params['desc']

        REMOVE = L("billingfrequency billingperiod profilestartdate desc")
        for k in params.keys():
            if k in REMOVE:
                del params[k]
                
        return params

    def _fetch(self, params, required, defaults):
        """Make the NVP request and store the response."""
        defaults.update(params)
        pp_params = self._check_and_update_params(required, defaults)        
        pp_string = self.signature + urlencode(pp_params)
        response = self._request(pp_string)
        response_params = self._parse_response(response)
        
        if settings.DEBUG:
            print 'PayPal Request:'
            pprint.pprint(defaults)
            print '\nPayPal Response:'
            pprint.pprint(response_params)

        # Gather all NVP parameters to pass to a new instance.
        nvp_params = {}
        for k, v in MergeDict(defaults, response_params).items():
            if k in NVP_FIELDS:
                nvp_params[k] = v    

        # PayPal timestamp has to be formatted.
        if 'timestamp' in nvp_params:
            nvp_params['timestamp'] = paypaltime2datetime(nvp_params['timestamp'])

        nvp_obj = PayPalNVP(**nvp_params)
        nvp_obj.init(self.request, params, response_params)
        nvp_obj.save()
        return nvp_obj
        
    def _request(self, data):
        """Moved out to make testing easier."""
        return urllib2.urlopen(self.endpoint, data).read()

    def _check_and_update_params(self, required, params):
        """
        Ensure all required parameters were passed to the API call and format
        them correctly.
        """
        for r in required:
            if r not in params:
                raise PayPalError("Missing required param: %s" % r)    

        # Upper case all the parameters for PayPal.
        return (dict((k.upper(), v) for k, v in params.iteritems()))

    def _parse_response(self, response):
        """Turn the PayPal response into a dict"""
        response_tokens = {}
        for kv in response.split('&'):
            key, value = kv.split("=")
            response_tokens[key.lower()] = urllib.unquote(value)
        return response_tokens
########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from string import split as L
from django.db import models
from django.utils.http import urlencode
from django.forms.models import model_to_dict
from django.contrib.auth.models import User


class PayPalNVP(models.Model):
    """Record of a NVP interaction with PayPal."""
    TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # 2009-02-03T17:47:41Z
    RESTRICTED_FIELDS = L("expdate cvv2 acct")
    ADMIN_FIELDS = L("id user flag flag_code flag_info query response created_at updated_at ")
    ITEM_FIELDS = L("amt custom invnum")
    DIRECT_FIELDS = L("firstname lastname street city state countrycode zip")

    # Response fields
    method = models.CharField(max_length=64, blank=True)
    ack = models.CharField(max_length=32, blank=True)    
    profilestatus = models.CharField(max_length=32, blank=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    profileid = models.CharField(max_length=32, blank=True)  # I-E596DFUSD882
    profilereference = models.CharField(max_length=128, blank=True)  # PROFILEREFERENCE
    correlationid = models.CharField(max_length=32, blank=True) # 25b380cda7a21
    token = models.CharField(max_length=64, blank=True)
    payerid = models.CharField(max_length=64, blank=True)
    
    # Transaction Fields
    firstname = models.CharField("First Name", max_length=255, blank=True)
    lastname = models.CharField("Last Name", max_length=255, blank=True)
    street = models.CharField("Street Address", max_length=255, blank=True)
    city = models.CharField("City", max_length=255, blank=True)
    state = models.CharField("State", max_length=255, blank=True)
    countrycode = models.CharField("Country", max_length=2,blank=True)
    zip = models.CharField("Postal / Zip Code", max_length=32, blank=True)
    
    # Custom fields
    invnum = models.CharField(max_length=255, blank=True)
    custom = models.CharField(max_length=255, blank=True) 
    
    # Admin fields
    user = models.ForeignKey(User, blank=True, null=True)
    flag = models.BooleanField(default=False, blank=True)
    flag_code = models.CharField(max_length=32, blank=True)
    flag_info = models.TextField(blank=True)    
    ipaddress = models.IPAddressField(blank=True)
    query = models.TextField(blank=True)
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    class Meta:
        db_table = "paypal_nvp"
        verbose_name = "PayPal NVP"
    
    def init(self, request, paypal_request, paypal_response):
        """Initialize a PayPalNVP instance from a HttpRequest."""
        self.ipaddress = request.META.get('REMOTE_ADDR', '')
        if hasattr(request, "user") and request.user.is_authenticated():
            self.user = request.user

        # No storing credit card info.
        query_data = dict((k,v) for k, v in paypal_request.iteritems() if k not in self.RESTRICTED_FIELDS)
        self.query = urlencode(query_data)
        self.response = urlencode(paypal_response)

        # Was there a flag on the play?        
        ack = paypal_response.get('ack', False)
        if ack != "Success":
            if ack == "SuccessWithWarning":
                self.flag_info = paypal_response.get('l_longmessage0', '')
            else:
                self.set_flag(paypal_response.get('l_longmessage0', ''), paypal_response.get('l_errorcode', ''))

    def set_flag(self, info, code=None):
        """Flag this instance for investigation."""
        self.flag = True
        self.flag_info += info
        if code is not None:
            self.flag_code = code

    def process(self, request, item):
        """Do a direct payment."""
        from paypal.pro.helpers import PayPalWPP
        wpp = PayPalWPP(request)

        # Change the model information into a dict that PayPal can understand.        
        params = model_to_dict(self, exclude=self.ADMIN_FIELDS)
        params['acct'] = self.acct
        params['creditcardtype'] = self.creditcardtype
        params['expdate'] = self.expdate
        params['cvv2'] = self.cvv2
        params.update(item)      

        # Create recurring payment:
        if 'billingperiod' in params:
            return wpp.createRecurringPaymentsProfile(params, direct=True)
        # Create single payment:
        else:
            return wpp.doDirectPayment(params)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

"""
These signals are different from IPN signals in that they are sent the second
the payment is failed or succeeds and come with the `item` object passed to
PayPalPro rather than an IPN object.

### SENDER is the item? is that right???

"""

# Sent when a payment is successfully processed.
payment_was_successful = Signal() #providing_args=["item"])

# Sent when a payment is flagged.
payment_was_flagged = Signal() #providing_args=["item"])

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.forms import ValidationError
from django.http import QueryDict
from django.test import TestCase
from django.test.client import Client

from paypal.pro.fields import CreditCardField
from paypal.pro.helpers import PayPalWPP, PayPalError


class RequestFactory(Client):
    # Used to generate request objects.
    def request(self, **request):
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)

RF = RequestFactory()
REQUEST = RF.get("/pay/", REMOTE_ADDR="127.0.0.1:8000")


class DummyPayPalWPP(PayPalWPP):
    pass
#     """Dummy class for testing PayPalWPP."""
#     responses = {
#         # @@@ Need some reals data here.
#         "DoDirectPayment": """ack=Success&timestamp=2009-03-12T23%3A52%3A33Z&l_severitycode0=Error&l_shortmessage0=Security+error&l_longmessage0=Security+header+is+not+valid&version=54.0&build=854529&l_errorcode0=&correlationid=""",
#     }
# 
#     def _request(self, data):
#         return self.responses["DoDirectPayment"]


class CreditCardFieldTest(TestCase):
    def testCreditCardField(self):
        field = CreditCardField()
        field.clean('4797503429879309')
        self.assertEquals(field.card_type, "Visa")
        self.assertRaises(ValidationError, CreditCardField().clean, '1234567890123455')

        
class PayPalWPPTest(TestCase):
    def setUp(self):
    
        # Avoding blasting real requests at PayPal.
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
            
        self.item = {
            'amt': '9.95',
            'inv': 'inv',
            'custom': 'custom',
            'next': 'http://www.example.com/next/',
            'returnurl': 'http://www.example.com/pay/',
            'cancelurl': 'http://www.example.com/cancel/'
        }                    
        self.wpp = DummyPayPalWPP(REQUEST)
        
    def tearDown(self):
        settings.DEBUG = self.old_debug

    def test_doDirectPayment_missing_params(self):
        data = {'firstname': 'Chewbacca'}
        self.assertRaises(PayPalError, self.wpp.doDirectPayment, data)

    def test_doDirectPayment_valid(self):
        data = {
            'firstname': 'Brave',
            'lastname': 'Star',
            'street': '1 Main St',
            'city': u'San Jos\xe9',
            'state': 'CA',
            'countrycode': 'US',
            'zip': '95131',
            'expdate': '012019',
            'cvv2': '037',
            'acct': '4797503429879309',
            'creditcardtype': 'visa',
            'ipaddress': '10.0.1.199',}
        data.update(self.item)
        self.assertTrue(self.wpp.doDirectPayment(data))
        
    def test_doDirectPayment_invalid(self):
        data = {
            'firstname': 'Epic',
            'lastname': 'Fail',
            'street': '100 Georgia St',
            'city': 'Vancouver',
            'state': 'BC',
            'countrycode': 'CA',
            'zip': 'V6V 1V1',
            'expdate': '012019',
            'cvv2': '999',
            'acct': '1234567890',
            'creditcardtype': 'visa',
            'ipaddress': '10.0.1.199',}
        data.update(self.item)
        self.assertFalse(self.wpp.doDirectPayment(data))

    def test_setExpressCheckout(self):
        # We'll have to stub out tests for doExpressCheckoutPayment and friends
        # because they're behind paypal's doors.
        nvp_obj = self.wpp.setExpressCheckout(self.item)
        self.assertTrue(nvp_obj.ack == "Success")


### DoExpressCheckoutPayment
# PayPal Request:
# {'amt': '10.00',
#  'cancelurl': u'http://xxx.xxx.xxx.xxx/deploy/480/upgrade/?upgrade=cname',
#  'custom': u'website_id=480&cname=1',
#  'inv': u'website-480-cname',
#  'method': 'DoExpressCheckoutPayment',
#  'next': u'http://xxx.xxx.xxx.xxx/deploy/480/upgrade/?upgrade=cname',
#  'payerid': u'BN5JZ2V7MLEV4',
#  'paymentaction': 'Sale',
#  'returnurl': u'http://xxx.xxx.xxx.xxx/deploy/480/upgrade/?upgrade=cname',
#  'token': u'EC-6HW17184NE0084127'}
# 
# PayPal Response:
# {'ack': 'Success',
#  'amt': '10.00',
#  'build': '848077',
#  'correlationid': '375f4773c3d34',
#  'currencycode': 'USD',
#  'feeamt': '0.59',
#  'ordertime': '2009-03-04T20:56:08Z',
#  'paymentstatus': 'Completed',
#  'paymenttype': 'instant',
#  'pendingreason': 'None',
#  'reasoncode': 'None',
#  'taxamt': '0.00',
#  'timestamp': '2009-03-04T20:56:09Z',
#  'token': 'EC-6HW17184NE0084127',
#  'transactionid': '3TG42202A7335864V',
#  'transactiontype': 'expresscheckout',
#  'version': '54.0'}
########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.utils.http import urlencode

from paypal.pro.forms import PaymentForm, ConfirmForm
from paypal.pro.models import PayPalNVP
from paypal.pro.helpers import PayPalWPP, TEST
from paypal.pro.signals import payment_was_successful, payment_was_flagged


# PayPal Edit IPN URL:
# https://www.sandbox.paypal.com/us/cgi-bin/webscr?cmd=_profile-ipn-notify
EXPRESS_ENDPOINT = "https://www.paypal.com/webscr?cmd=_express-checkout&%s"
SANDBOX_EXPRESS_ENDPOINT = "https://www.sandbox.paypal.com/webscr?cmd=_express-checkout&%s"


class PayPalPro(object):
    """
    This class-based view takes care of PayPal WebsitePaymentsPro (WPP).
    PayPalPro has two separate flows - DirectPayment and ExpressPayFlow. In 
    DirectPayment the user buys on your site. In ExpressPayFlow the user is
    direct to PayPal to confirm their purchase. PayPalPro implements both 
    flows. To it create an instance using the these parameters:

    item: a dictionary that holds information about the item being purchased.
    
    For single item purchase (pay once):
    
        Required Keys:
            * amt: Float amount of the item.
        
        Optional Keys:
            * custom: You can set this to help you identify a transaction.
            * invnum: Unique ID that identifies this transaction.
    
    For recurring billing:
    
        Required Keys:
          * amt: Float amount for each billing cycle.
          * billingperiod: String unit of measure for the billing cycle (Day|Week|SemiMonth|Month|Year)
          * billingfrequency: Integer number of periods that make up a cycle.
          * profilestartdate: The date to begin billing. "2008-08-05T17:00:00Z" UTC/GMT
          * desc: Description of what you're billing for.
          
        Optional Keys:
          * trialbillingperiod: String unit of measure for trial cycle (Day|Week|SemiMonth|Month|Year)
          * trialbillingfrequency: Integer # of periods in a cycle.
          * trialamt: Float amount to bill for the trial period.
          * trialtotalbillingcycles: Integer # of cycles for the trial payment period.
          * failedinitamtaction: set to continue on failure (ContinueOnFailure / CancelOnFailure)
          * maxfailedpayments: number of payments before profile is suspended.
          * autobilloutamt: automatically bill outstanding amount.
          * subscribername: Full name of the person who paid.
          * profilereference: Unique reference or invoice number.
          * taxamt: How much tax.
          * initamt: Initial non-recurring payment due upon creation.
          * currencycode: defaults to USD
          * + a bunch of shipping fields
        
    payment_form_cls: form class that will be used to display the payment form.
    It should inherit from `paypal.pro.forms.PaymentForm` if you're adding more.
    
    payment_template: template used to ask the dude for monies. To comply with
    PayPal standards it must include a link to PayPal Express Checkout.
    
    confirm_form_cls: form class that will be used to display the confirmation form.
    It should inherit from `paypal.pro.forms.ConfirmForm`. It is only used in the Express flow.
    
    success_url / fail_url: URLs to be redirected to when the payment successful or fails.
    """
    errors = {
        "processing": "There was an error processing your payment. Check your information and try again.",
        "form": "Please correct the errors below and try again.",
        "paypal": "There was a problem contacting PayPal. Please try again later."
    }
    
    def __init__(self, item=None, payment_form_cls=PaymentForm,
                 payment_template="pro/payment.html", confirm_form_cls=ConfirmForm, 
                 confirm_template="pro/confirm.html", success_url="?success", 
                 fail_url=None, context=None, form_context_name="form"):
        self.item = item
        self.payment_form_cls = payment_form_cls
        self.payment_template = payment_template
        self.confirm_form_cls = confirm_form_cls
        self.confirm_template = confirm_template
        self.success_url = success_url
        self.fail_url = fail_url
        self.context = context or {}
        self.form_context_name = form_context_name

    def __call__(self, request):
        """Return the appropriate response for the state of the transaction."""
        self.request = request
        if request.method == "GET":
            if self.should_redirect_to_express():
                return self.redirect_to_express()
            elif self.should_render_confirm_form():
                return self.render_confirm_form()
            elif self.should_render_payment_form():
                return self.render_payment_form() 
        else:
            if self.should_validate_confirm_form():
                return self.validate_confirm_form()
            elif self.should_validate_payment_form():
                return self.validate_payment_form()
        
        # Default to the rendering the payment form.
        return self.render_payment_form()

    def is_recurring(self):
        return self.item is not None and 'billingperiod' in self.item

    def should_redirect_to_express(self):
        return 'express' in self.request.GET
        
    def should_render_confirm_form(self):
        return 'token' in self.request.GET and 'PayerID' in self.request.GET
        
    def should_render_payment_form(self):
        return True

    def should_validate_confirm_form(self):
        return 'token' in self.request.POST and 'PayerID' in self.request.POST  
        
    def should_validate_payment_form(self):
        return True

    def render_payment_form(self):
        """Display the DirectPayment for entering payment information."""
        self.context[self.form_context_name] = self.payment_form_cls()
        return render_to_response(self.payment_template, self.context, RequestContext(self.request))

    def validate_payment_form(self):
        """Try to validate and then process the DirectPayment form."""
        form = self.payment_form_cls(self.request.POST)        
        if form.is_valid():
            success = form.process(self.request, self.item)
            if success:
                payment_was_successful.send(sender=self.item)
                return HttpResponseRedirect(self.success_url)
            else:
                self.context['errors'] = self.errors['processing']

        self.context[self.form_context_name] = form
        self.context.setdefault("errors", self.errors['form'])
        return render_to_response(self.payment_template, self.context, RequestContext(self.request))

    def get_endpoint(self):
        if TEST:
            return SANDBOX_EXPRESS_ENDPOINT
        else:
            return EXPRESS_ENDPOINT

    def redirect_to_express(self):
        """
        First step of ExpressCheckout. Redirect the request to PayPal using the 
        data returned from setExpressCheckout.
        """
        wpp = PayPalWPP(self.request)
        nvp_obj = wpp.setExpressCheckout(self.item)
        if not nvp_obj.flag:
            pp_params = dict(token=nvp_obj.token, AMT=self.item['amt'], 
                             RETURNURL=self.item['returnurl'], 
                             CANCELURL=self.item['cancelurl'])
            pp_url = self.get_endpoint() % urlencode(pp_params)
            return HttpResponseRedirect(pp_url)
        else:
            self.context['errors'] = self.errors['paypal']
            return self.render_payment_form()

    def render_confirm_form(self):
        """
        Second step of ExpressCheckout. Display an order confirmation form which
        contains hidden fields with the token / PayerID from PayPal.
        """
        initial = dict(token=self.request.GET['token'], PayerID=self.request.GET['PayerID'])
        self.context[self.form_context_name] = self.confirm_form_cls(initial=initial)
        return render_to_response(self.confirm_template, self.context, RequestContext(self.request))

    def validate_confirm_form(self):
        """
        Third and final step of ExpressCheckout. Request has pressed the confirmation but
        and we can send the final confirmation to PayPal using the data from the POST'ed form.
        """
        wpp = PayPalWPP(self.request)
        pp_data = dict(token=self.request.POST['token'], payerid=self.request.POST['PayerID'])
        self.item.update(pp_data)
        
        # @@@ This check and call could be moved into PayPalWPP.
        if self.is_recurring():
            success = wpp.createRecurringPaymentsProfile(self.item)
        else:
            success = wpp.doExpressCheckoutPayment(self.item)

        if success:
            payment_was_successful.send(sender=self.item)
            return HttpResponseRedirect(self.success_url)
        else:
            self.context['errors'] = self.errors['processing']
            return self.render_payment_form()

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings

class PayPalSettingsError(Exception):
    """Raised when settings be bad."""
    

TEST = getattr(settings, "PAYPAL_TEST", True)


RECEIVER_EMAIL = settings.PAYPAL_RECEIVER_EMAIL


# API Endpoints.
POSTBACK_ENDPOINT = "https://www.paypal.com/cgi-bin/webscr"
SANDBOX_POSTBACK_ENDPOINT = "https://www.sandbox.paypal.com/cgi-bin/webscr"

# Images
IMAGE = getattr(settings, "PAYPAL_IMAGE", "http://images.paypal.com/images/x-click-but01.gif")
SUBSCRIPTION_IMAGE = "https://www.paypal.com/en_US/i/btn/btn_subscribeCC_LG.gif"
SANDBOX_IMAGE = getattr(settings, "PAYPAL_SANDBOX_IMAGE", "https://www.sandbox.paypal.com/en_US/i/btn/btn_buynowCC_LG.gif")
SUBSCRIPTION_SANDBOX_IMAGE = "https://www.sandbox.paypal.com/en_US/i/btn/btn_subscribeCC_LG.gif"
########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from paypal.standard.conf import *
from paypal.standard.widgets import ValueHiddenInput, ReservedValueHiddenInput
from paypal.standard.conf import (POSTBACK_ENDPOINT, SANDBOX_POSTBACK_ENDPOINT, 
    RECEIVER_EMAIL)


# 20:18:05 Jan 30, 2009 PST - PST timezone support is not included out of the box.
# PAYPAL_DATE_FORMAT = ("%H:%M:%S %b. %d, %Y PST", "%H:%M:%S %b %d, %Y PST",)
# PayPal dates have been spotted in the wild with these formats, beware!
PAYPAL_DATE_FORMAT = ("%H:%M:%S %b. %d, %Y PST",
                      "%H:%M:%S %b. %d, %Y PDT",
                      "%H:%M:%S %b %d, %Y PST",
                      "%H:%M:%S %b %d, %Y PDT",)

class PayPalPaymentsForm(forms.Form):
    """
    Creates a PayPal Payments Standard "Buy It Now" button, configured for a
    selling a single item with no shipping.
    
    For a full overview of all the fields you can set (there is a lot!) see:
    http://tinyurl.com/pps-integration
    
    Usage:
    >>> f = PayPalPaymentsForm(initial={'item_name':'Widget 001', ...})
    >>> f.render()
    u'<form action="https://www.paypal.com/cgi-bin/webscr" method="post"> ...'
    
    """    
    CMD_CHOICES = (
        ("_xclick", "Buy now or Donations"), 
        ("_cart", "Shopping cart"), 
        ("_xclick-subscriptions", "Subscribe")
    )
    SHIPPING_CHOICES = ((1, "No shipping"), (0, "Shipping"))
    NO_NOTE_CHOICES = ((1, "No Note"), (0, "Include Note"))
    RECURRING_PAYMENT_CHOICES = (
        (1, "Subscription Payments Recur"), 
        (0, "Subscription payments do not recur")
    )
    REATTEMPT_ON_FAIL_CHOICES = (
        (1, "reattempt billing on Failure"), 
        (0, "Do Not reattempt on failure")
    )
        
    # Where the money goes.
    business = forms.CharField(widget=ValueHiddenInput(), initial=RECEIVER_EMAIL)
    
    # Item information.
    amount = forms.IntegerField(widget=ValueHiddenInput())
    item_name = forms.CharField(widget=ValueHiddenInput())
    item_number = forms.CharField(widget=ValueHiddenInput())
    quantity = forms.CharField(widget=ValueHiddenInput())
    
    # Subscription Related.
    a1 = forms.CharField(widget=ValueHiddenInput())  # Trial 1 Price
    p1 = forms.CharField(widget=ValueHiddenInput())  # Trial 1 Duration
    t1 = forms.CharField(widget=ValueHiddenInput())  # Trial 1 unit of Duration, default to Month
    a2 = forms.CharField(widget=ValueHiddenInput())  # Trial 2 Price
    p2 = forms.CharField(widget=ValueHiddenInput())  # Trial 2 Duration
    t2 = forms.CharField(widget=ValueHiddenInput())  # Trial 2 unit of Duration, default to Month    
    a3 = forms.CharField(widget=ValueHiddenInput())  # Subscription Price
    p3 = forms.CharField(widget=ValueHiddenInput())  # Subscription Duration
    t3 = forms.CharField(widget=ValueHiddenInput())  # Subscription unit of Duration, default to Month
    src = forms.CharField(widget=ValueHiddenInput()) # Is billing recurring? default to yes
    sra = forms.CharField(widget=ValueHiddenInput()) # Reattempt billing on failed cc transaction
    no_note = forms.CharField(widget=ValueHiddenInput())    
    # Can be either 1 or 2. 1 = modify or allow new subscription creation, 2 = modify only
    modify = forms.IntegerField(widget=ValueHiddenInput()) # Are we modifying an existing subscription?
    
    # Localization / PayPal Setup
    lc = forms.CharField(widget=ValueHiddenInput())
    page_style = forms.CharField(widget=ValueHiddenInput())
    cbt = forms.CharField(widget=ValueHiddenInput())
    
    # IPN control.
    notify_url = forms.CharField(widget=ValueHiddenInput())
    cancel_return = forms.CharField(widget=ValueHiddenInput())
    return_url = forms.CharField(widget=ReservedValueHiddenInput(attrs={"name":"return"}))
    custom = forms.CharField(widget=ValueHiddenInput())
    invoice = forms.CharField(widget=ValueHiddenInput())
    
    # Default fields.
    cmd = forms.ChoiceField(widget=forms.HiddenInput(), initial=CMD_CHOICES[0][0])
    charset = forms.CharField(widget=forms.HiddenInput(), initial="utf-8")
    currency_code = forms.CharField(widget=forms.HiddenInput(), initial="USD")
    no_shipping = forms.ChoiceField(widget=forms.HiddenInput(), choices=SHIPPING_CHOICES, 
        initial=SHIPPING_CHOICES[0][0])

    def __init__(self, button_type="buy", *args, **kwargs):
        super(PayPalPaymentsForm, self).__init__(*args, **kwargs)
        self.button_type = button_type

    def render(self):
        return mark_safe(u"""<form action="%s" method="post">
    %s
    <input type="image" src="%s" border="0" name="submit" alt="Buy it Now" />
</form>""" % (POSTBACK_ENDPOINT, self.as_p(), self.get_image()))
        
        
    def sandbox(self):
        return mark_safe(u"""<form action="%s" method="post">
    %s
    <input type="image" src="%s" border="0" name="submit" alt="Buy it Now" />
</form>""" % (SANDBOX_POSTBACK_ENDPOINT, self.as_p(), self.get_image()))
        
    def get_image(self):
        return {
            (True, True): SUBSCRIPTION_SANDBOX_IMAGE,
            (True, False): SANDBOX_IMAGE,
            (False, True): SUBSCRIPTION_IMAGE,
            (False, False): IMAGE
        }[TEST, self.is_subscription()]

    def is_transaction(self):
        return self.button_type == "buy"

    def is_subscription(self):
        return self.button_type == "subscribe"


class PayPalEncryptedPaymentsForm(PayPalPaymentsForm):
    """
    Creates a PayPal Encrypted Payments "Buy It Now" button.
    Requires the M2Crypto package.

    Based on example at:
    http://blog.mauveweb.co.uk/2007/10/10/paypal-with-django/
    
    """
    def _encrypt(self):
        """Use your key thing to encrypt things."""
        from M2Crypto import BIO, SMIME, X509
        # @@@ Could we move this to conf.py?
        CERT = settings.PAYPAL_PRIVATE_CERT
        PUB_CERT = settings.PAYPAL_PUBLIC_CERT
        PAYPAL_CERT = settings.PAYPAL_CERT
        CERT_ID = settings.PAYPAL_CERT_ID

        # Iterate through the fields and pull out the ones that have a value.
        plaintext = 'cert_id=%s\n' % CERT_ID
        for name, field in self.fields.iteritems():
            value = None
            if name in self.initial:
                value = self.initial[name]
            elif field.initial is not None:
                value = field.initial
            if value is not None:
                # @@@ Make this less hackish and put it in the widget.
                if name == "return_url":
                    name = "return"
                plaintext += u'%s=%s\n' % (name, value)
        plaintext = plaintext.encode('utf-8')
        
    	# Begin crypto weirdness.
    	s = SMIME.SMIME()	
    	s.load_key_bio(BIO.openfile(CERT), BIO.openfile(PUB_CERT))
    	p7 = s.sign(BIO.MemoryBuffer(plaintext), flags=SMIME.PKCS7_BINARY)
    	x509 = X509.load_cert_bio(BIO.openfile(settings.PAYPAL_CERT))
    	sk = X509.X509_Stack()
    	sk.push(x509)
    	s.set_x509_stack(sk)
    	s.set_cipher(SMIME.Cipher('des_ede3_cbc'))
    	tmp = BIO.MemoryBuffer()
    	p7.write_der(tmp)
    	p7 = s.encrypt(tmp, flags=SMIME.PKCS7_BINARY)
    	out = BIO.MemoryBuffer()
    	p7.write(out)	
    	return out.read()
    	
    def as_p(self):
        return mark_safe(u"""
<input type="hidden" name="cmd" value="_s-xclick" />
<input type="hidden" name="encrypted" value="%s" />            
        """ % self._encrypt())


class PayPalSharedSecretEncryptedPaymentsForm(PayPalEncryptedPaymentsForm):
    """
    Creates a PayPal Encrypted Payments "Buy It Now" button with a Shared Secret.
    Shared secrets should only be used when your IPN endpoint is on HTTPS.
    
    Adds a secret to the notify_url based on the contents of the form.

    """
    def __init__(self, *args, **kwargs):
        "Make the secret from the form initial data and slip it into the form."
        from paypal.standard.helpers import make_secret
        super(PayPalSharedSecretEncryptedPaymentsForm, self).__init__(self, *args, **kwargs)
        # @@@ Attach the secret parameter in a way that is safe for other query params.
        secret_param = "?secret=%s" % make_secret(self)
        # Initial data used in form construction overrides defaults
        if 'notify_url' in self.initial:
            self.initial['notify_url'] += secret_param
        else:
            self.fields['notify_url'].initial += secret_param


class PayPalStandardBaseForm(forms.ModelForm):
    """Form used to receive and record PayPal IPN/PDT."""
    # PayPal dates have non-standard formats.
    time_created = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    payment_date = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    next_payment_date = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    subscr_date = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    subscr_effective = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf import settings


def duplicate_txn_id(ipn_obj):
    """Returns True if a record with this transaction id exists."""
    return ipn_obj._default_manager.filter(txn_id=ipn_obj.txn_id).count() > 0
    
def make_secret(form_instance, secret_fields=None):
    """
    Returns a secret for use in a EWP form or an IPN verification based on a
    selection of variables in params. Should only be used with SSL.
    
    """
    # @@@ Moved here as temporary fix to avoid dependancy on auth.models.
    from django.contrib.auth.models import get_hexdigest
    # @@@ amount is mc_gross on the IPN - where should mapping logic go?
    # @@@ amount / mc_gross is not nessecarily returned as it was sent - how to use it? 10.00 vs. 10.0
    # @@@ the secret should be based on the invoice or custom fields as well - otherwise its always the same.
    
    # Build the secret with fields availible in both PaymentForm and the IPN. Order matters.
    if secret_fields is None:
        secret_fields = ['business', 'item_name']

    data = ""
    for name in secret_fields:
        if hasattr(form_instance, 'cleaned_data'):
            if name in form_instance.cleaned_data:
                data += unicode(form_instance.cleaned_data[name])
        else:
            # Initial data passed into the constructor overrides defaults.
            if name in form_instance.initial:
                data += unicode(form_instance.initial[name])
            elif name in form_instance.fields and form_instance.fields[name].initial is not None:
                data += unicode(form_instance.fields[name].initial)

    secret = get_hexdigest('sha1', settings.SECRET_KEY, data)
    return secret

def check_secret(form_instance, secret):
    """
    Returns true if received `secret` matches expected secret for form_instance.
    Used to verify IPN.
    
    """
    # @@@ add invoice & custom
    # secret_fields = ['business', 'item_name']
    return make_secret(form_instance) == secret
########NEW FILE########
__FILENAME__ = admin
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.contrib import admin
from paypal.standard.ipn.models import PayPalIPN


class PayPalIPNAdmin(admin.ModelAdmin):
    date_hierarchy = 'payment_date'
    fieldsets = (
        (None, {
            "fields": [
                "flag", "txn_id", "txn_type", "payment_status", "payment_date",
                "transaction_entity", "reason_code", "pending_reason", 
                "mc_gross", "mc_fee", "auth_status", "auth_amount", "auth_exp", 
                "auth_id"
            ]
        }),
        ("Address", {
            "description": "The address of the Buyer.",
            'classes': ('collapse',),
            "fields": [
                "address_city", "address_country", "address_country_code",
                "address_name", "address_state", "address_status", 
                "address_street", "address_zip"
            ]
        }),
        ("Buyer", {
            "description": "The information about the Buyer.",
            'classes': ('collapse',),
            "fields": [
                "first_name", "last_name", "payer_business_name", "payer_email",
                "payer_id", "payer_status", "contact_phone", "residence_country"
            ]
        }),
        ("Seller", {
            "description": "The information about the Seller.",
            'classes': ('collapse',),
            "fields": [
                "business", "item_name", "item_number", "quantity", 
                "receiver_email", "receiver_id", "custom", "invoice", "memo"
            ]
        }),
        ("Recurring", {
            "description": "Information about recurring Payments.",
            "classes": ("collapse",),
            "fields": [
                "profile_status", "initial_payment_amount", "amount_per_cycle", 
                "outstanding_balance", "period_type", "product_name", 
                "product_type", "recurring_payment_id", "receipt_id", 
                "next_payment_date"
            ]
        }),
        ("Admin", {
            "description": "Additional Info.",
            "classes": ('collapse',),
            "fields": [
                "test_ipn", "ipaddress", "query", "response", "flag_code", 
                "flag_info"
            ]
        }),
    )
    list_display = [
        "__unicode__", "flag", "flag_info", "invoice", "custom", 
        "payment_status", "created_at"
    ]
    search_fields = ["txn_id", "recurring_payment_id"]


admin.site.register(PayPalIPN, PayPalIPNAdmin)
########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from paypal.standard.forms import PayPalStandardBaseForm 
from paypal.standard.ipn.models import PayPalIPN


class PayPalIPNForm(PayPalStandardBaseForm):
    """
    Form used to receive and record PayPal IPN notifications.
    
    PayPal IPN test tool:
    https://developer.paypal.com/us/cgi-bin/devscr?cmd=_tools-session
    """
    class Meta:
        model = PayPalIPN


########NEW FILE########
__FILENAME__ = 0001_first_migration
# -*- coding: utf-8 -*-
from django.db import models
from south.db import db
from paypal.standard.ipn.models import *


class Migration:    
    def forwards(self, orm):
        # Adding model 'PayPalIPN'
        db.create_table('paypal_ipn', (
            ('id', models.AutoField(primary_key=True)),
            ('business', models.CharField(max_length=127, blank=True)),
            ('charset', models.CharField(max_length=32, blank=True)),
            ('custom', models.CharField(max_length=255, blank=True)),
            ('notify_version', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('parent_txn_id', models.CharField("Parent Transaction ID", max_length=19, blank=True)),
            ('receiver_email', models.EmailField(max_length=127, blank=True)),
            ('receiver_id', models.CharField(max_length=127, blank=True)),
            ('residence_country', models.CharField(max_length=2, blank=True)),
            ('test_ipn', models.BooleanField(default=False, blank=True)),
            ('txn_id', models.CharField("Transaction ID", max_length=19, blank=True)),
            ('txn_type', models.CharField("Transaction Type", max_length=128, blank=True)),
            ('verify_sign', models.CharField(max_length=255, blank=True)),
            ('address_country', models.CharField(max_length=64, blank=True)),
            ('address_city', models.CharField(max_length=40, blank=True)),
            ('address_country_code', models.CharField(max_length=64, blank=True)),
            ('address_name', models.CharField(max_length=128, blank=True)),
            ('address_state', models.CharField(max_length=40, blank=True)),
            ('address_status', models.CharField(max_length=11, blank=True)),
            ('address_street', models.CharField(max_length=200, blank=True)),
            ('address_zip', models.CharField(max_length=20, blank=True)),
            ('contact_phone', models.CharField(max_length=20, blank=True)),
            ('first_name', models.CharField(max_length=64, blank=True)),
            ('last_name', models.CharField(max_length=64, blank=True)),
            ('payer_business_name', models.CharField(max_length=127, blank=True)),
            ('payer_email', models.CharField(max_length=127, blank=True)),
            ('payer_id', models.CharField(max_length=13, blank=True)),
            ('auth_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('auth_exp', models.CharField(max_length=28, blank=True)),
            ('auth_id', models.CharField(max_length=19, blank=True)),
            ('auth_status', models.CharField(max_length=9, blank=True)),
            ('exchange_rate', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=16, blank=True)),
            ('invoice', models.CharField(max_length=127, blank=True)),
            ('item_name', models.CharField(max_length=127, blank=True)),
            ('item_number', models.CharField(max_length=127, blank=True)),
            ('mc_currency', models.CharField(default='USD', max_length=32, blank=True)),
            ('mc_fee', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_gross', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_handling', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_shipping', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('memo', models.CharField(max_length=255, blank=True)),
            ('num_cart_items', models.IntegerField(default=0, null=True, blank=True)),
            ('option_name1', models.CharField(max_length=64, blank=True)),
            ('option_name2', models.CharField(max_length=64, blank=True)),
            ('payer_status', models.CharField(max_length=10, blank=True)),
            ('payment_date', models.DateTimeField(null=True, blank=True)),
            ('payment_gross', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('payment_status', models.CharField(max_length=9, blank=True)),
            ('payment_type', models.CharField(max_length=7, blank=True)),
            ('pending_reason', models.CharField(max_length=14, blank=True)),
            ('protection_eligibility', models.CharField(max_length=32, blank=True)),
            ('quantity', models.IntegerField(default=1, null=True, blank=True)),
            ('reason_code', models.CharField(max_length=15, blank=True)),
            ('remaining_settle', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('settle_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('settle_currency', models.CharField(max_length=32, blank=True)),
            ('shipping', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('shipping_method', models.CharField(max_length=255, blank=True)),
            ('tax', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('transaction_entity', models.CharField(max_length=7, blank=True)),
            ('auction_buyer_id', models.CharField(max_length=64, blank=True)),
            ('auction_closing_date', models.DateTimeField(null=True, blank=True)),
            ('auction_multi_item', models.IntegerField(default=0, null=True, blank=True)),
            ('for_auction', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount_per_cycle', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('initial_payment_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('next_payment_date', models.DateTimeField(null=True, blank=True)),
            ('outstanding_balance', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('payment_cycle', models.CharField(max_length=32, blank=True)),
            ('period_type', models.CharField(max_length=32, blank=True)),
            ('product_name', models.CharField(max_length=128, blank=True)),
            ('product_type', models.CharField(max_length=128, blank=True)),
            ('profile_status', models.CharField(max_length=32, blank=True)),
            ('recurring_payment_id', models.CharField(max_length=128, blank=True)),
            ('rp_invoice_id', models.CharField(max_length=127, blank=True)),
            ('time_created', models.DateTimeField(null=True, blank=True)),
            ('amount1', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount2', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount3', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_amount1', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_amount2', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_amount3', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('password', models.CharField(max_length=24, blank=True)),
            ('period1', models.CharField(max_length=32, blank=True)),
            ('period2', models.CharField(max_length=32, blank=True)),
            ('period3', models.CharField(max_length=32, blank=True)),
            ('reattempt', models.CharField(max_length=1, blank=True)),
            ('recur_times', models.IntegerField(default=0, null=True, blank=True)),
            ('recurring', models.CharField(max_length=1, blank=True)),
            ('retry_at', models.DateTimeField(null=True, blank=True)),
            ('subscr_date', models.DateTimeField(null=True, blank=True)),
            ('subscr_effective', models.DateTimeField(null=True, blank=True)),
            ('subscr_id', models.CharField(max_length=19, blank=True)),
            ('username', models.CharField(max_length=64, blank=True)),
            ('case_creation_date', models.DateTimeField(null=True, blank=True)),
            ('case_id', models.CharField(max_length=14, blank=True)),
            ('case_type', models.CharField(max_length=24, blank=True)),
            ('receipt_id', models.CharField(max_length=64, blank=True)),
            ('currency_code', models.CharField(default='USD', max_length=32, blank=True)),
            ('handling_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('transaction_subject', models.CharField(max_length=255, blank=True)),
            ('ipaddress', models.IPAddressField(blank=True)),
            ('flag', models.BooleanField(default=False, blank=True)),
            ('flag_code', models.CharField(max_length=16, blank=True)),
            ('flag_info', models.TextField(blank=True)),
            ('query', models.TextField(blank=True)),
            ('response', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('from_view', models.CharField(max_length=6, null=True, blank=True)),
        ))
        db.send_create_signal('ipn', ['PayPalIPN'])
    
    def backwards(self, orm):        
        # Deleting model 'PayPalIPN'
        db.delete_table('paypal_ipn')

        
    models = {
        'ipn.paypalipn': {
            'Meta': {'db_table': '"paypal_ipn"'},
            'address_city': ('models.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_country': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_country_code': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_name': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'address_state': ('models.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_status': ('models.CharField', [], {'max_length': '11', 'blank': 'True'}),
            'address_street': ('models.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'address_zip': ('models.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount1': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount2': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount3': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount_per_cycle': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auction_buyer_id': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'auction_closing_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'auction_multi_item': ('models.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'auth_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auth_exp': ('models.CharField', [], {'max_length': '28', 'blank': 'True'}),
            'auth_id': ('models.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'auth_status': ('models.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'business': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'case_creation_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'case_id': ('models.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'case_type': ('models.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'charset': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'contact_phone': ('models.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'created_at': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'currency_code': ('models.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'custom': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'exchange_rate': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '16', 'blank': 'True'}),
            'first_name': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'flag': ('models.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'flag_code': ('models.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'flag_info': ('models.TextField', [], {'blank': 'True'}),
            'for_auction': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'from_view': ('models.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'handling_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'initial_payment_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'invoice': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'ipaddress': ('models.IPAddressField', [], {'blank': 'True'}),
            'item_name': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'item_number': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'last_name': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'mc_amount1': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount2': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount3': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_currency': ('models.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'mc_fee': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_gross': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_handling': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_shipping': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'memo': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'next_payment_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'notify_version': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'num_cart_items': ('models.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'option_name1': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'option_name2': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'outstanding_balance': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'parent_txn_id': ('models.CharField', ['"Parent Transaction ID"'], {'max_length': '19', 'blank': 'True'}),
            'password': ('models.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'payer_business_name': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_email': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_id': ('models.CharField', [], {'max_length': '13', 'blank': 'True'}),
            'payer_status': ('models.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'payment_cycle': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'payment_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'payment_gross': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'payment_status': ('models.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'payment_type': ('models.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'pending_reason': ('models.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'period1': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period2': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period3': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period_type': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'product_name': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'product_type': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'profile_status': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'protection_eligibility': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'quantity': ('models.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'query': ('models.TextField', [], {'blank': 'True'}),
            'reason_code': ('models.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'reattempt': ('models.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'receipt_id': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'receiver_email': ('models.EmailField', [], {'max_length': '127', 'blank': 'True'}),
            'receiver_id': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'recur_times': ('models.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'recurring': ('models.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'recurring_payment_id': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'remaining_settle': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'residence_country': ('models.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'response': ('models.TextField', [], {'blank': 'True'}),
            'retry_at': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rp_invoice_id': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'settle_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'settle_currency': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'shipping': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'shipping_method': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'subscr_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_effective': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_id': ('models.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'tax': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'test_ipn': ('models.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'time_created': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'transaction_entity': ('models.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'transaction_subject': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'txn_id': ('models.CharField', ['"Transaction ID"'], {'max_length': '19', 'blank': 'True'}),
            'txn_type': ('models.CharField', ['"Transaction Type"'], {'max_length': '128', 'blank': 'True'}),
            'updated_at': ('models.DateTimeField', [], {'auto_now': 'True'}),
            'username': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'verify_sign': ('models.CharField', [], {'max_length': '255', 'blank': 'True'})
        }
    }
    
    complete_apps = ['ipn']
########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib2
from paypal.standard.models import PayPalStandardBase
from paypal.standard.ipn.signals import *


class PayPalIPN(PayPalStandardBase):
    """Logs PayPal IPN interactions."""
    format = u"<IPN: %s %s>"

    class Meta:
        db_table = "paypal_ipn"
        verbose_name = "PayPal IPN"

    def _postback(self):
        """Perform PayPal Postback validation."""
        return urllib2.urlopen(self.get_endpoint(), "cmd=_notify-validate&%s" % self.query).read()
    
    def _verify_postback(self):
        if self.response != "VERIFIED":
            self.set_flag("Invalid postback. (%s)" % self.response)
            
    def send_signals(self):
        """Shout for the world to hear whether a txn was successful."""
        # Transaction signals:
        if self.is_transaction():
            if self.flag:
                payment_was_flagged.send(sender=self)
            else:
                payment_was_successful.send(sender=self)
        # Subscription signals:
        else:
            if self.is_subscription_cancellation():
                subscription_cancel.send(sender=self)
            elif self.is_subscription_signup():
                subscription_signup.send(sender=self)
            elif self.is_subscription_end_of_term():
                subscription_eot.send(sender=self)
            elif self.is_subscription_modified():
                subscription_modify.send(sender=self)            
########NEW FILE########
__FILENAME__ = signals
"""
Note that sometimes you will get duplicate signals emitted, depending on configuration of your systems. 
If you do encounter this, you will need to add the "dispatch_uid" to your connect handlers:
http://code.djangoproject.com/wiki/Signals#Helppost_saveseemstobeemittedtwiceforeachsave

"""
from django.dispatch import Signal

# Sent when a payment is successfully processed.
payment_was_successful = Signal()

# Sent when a payment is flagged.
payment_was_flagged = Signal()

# Sent when a subscription was cancelled.
subscription_cancel = Signal()

# Sent when a subscription expires.
subscription_eot = Signal()

# Sent when a subscription was modified.
subscription_modify = Signal()

# Sent when a subscription is created.
subscription_signup = Signal()
########NEW FILE########
__FILENAME__ = test_ipn
from django.conf import settings
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import Client

from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.ipn.signals import (payment_was_successful, 
    payment_was_flagged)


IPN_POST_PARAMS = {
    "protection_eligibility": "Ineligible",
    "last_name": "User",
    "txn_id": "51403485VH153354B",
    "receiver_email": settings.PAYPAL_RECEIVER_EMAIL,
    "payment_status": "Completed",
    "payment_gross": "10.00",
    "tax": "0.00",
    "residence_country": "US",
    "invoice": "0004",
    "payer_status": "verified",
    "txn_type": "express_checkout",
    "handling_amount": "0.00",
    "payment_date": "23:04:06 Feb 02, 2009 PST",
    "first_name": "Test",
    "item_name": "",
    "charset": "windows-1252",
    "custom": "website_id=13&user_id=21",
    "notify_version": "2.6",
    "transaction_subject": "",
    "test_ipn": "1",
    "item_number": "",
    "receiver_id": "258DLEHY2BDK6",
    "payer_id": "BN5JZ2V7MLEV4",
    "verify_sign": "An5ns1Kso7MWUdW4ErQKJJJ4qi4-AqdZy6dD.sGO3sDhTf1wAbuO2IZ7",
    "payment_fee": "0.59",
    "mc_fee": "0.59",
    "mc_currency": "USD",
    "shipping": "0.00",
    "payer_email": "bishan_1233269544_per@gmail.com",
    "payment_type": "instant",
    "mc_gross": "10.00",
    "quantity": "1",
}


class IPNTest(TestCase):    
    urls = 'paypal.standard.ipn.tests.test_urls'

    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True

        # Monkey patch over PayPalIPN to make it get a VERFIED response.
        self.old_postback = PayPalIPN._postback
        PayPalIPN._postback = lambda self: "VERIFIED"
        
    def tearDown(self):
        settings.DEBUG = self.old_debug
        PayPalIPN._postback = self.old_postback

    def assertGotSignal(self, signal, flagged):
        # Check the signal was sent. These get lost if they don't reference self.
        self.got_signal = False
        self.signal_obj = None
        
        def handle_signal(sender, **kwargs):
            self.got_signal = True
            self.signal_obj = sender
        signal.connect(handle_signal)
        
        response = self.client.post("/ipn/", IPN_POST_PARAMS)
        self.assertEqual(response.status_code, 200)
        ipns = PayPalIPN.objects.all()
        self.assertEqual(len(ipns), 1)        
        ipn_obj = ipns[0]        
        self.assertEqual(ipn_obj.flag, flagged)
        
        self.assertTrue(self.got_signal)
        self.assertEqual(self.signal_obj, ipn_obj)
        
    def test_correct_ipn(self):
        self.assertGotSignal(payment_was_successful, False)

    def test_failed_ipn(self):
        PayPalIPN._postback = lambda self: "INVALID"
        self.assertGotSignal(payment_was_flagged, True)

    def assertFlagged(self, updates, flag_info):
        params = IPN_POST_PARAMS.copy()
        params.update(updates)
        response = self.client.post("/ipn/", params)
        self.assertEqual(response.status_code, 200)
        ipn_obj = PayPalIPN.objects.all()[0]
        self.assertEqual(ipn_obj.flag, True)
        self.assertEqual(ipn_obj.flag_info, flag_info)

    def test_incorrect_receiver_email(self):
        update = {"receiver_email": "incorrect_email@someotherbusiness.com"}
        flag_info = "Invalid receiver_email. (incorrect_email@someotherbusiness.com)"
        self.assertFlagged(update, flag_info)

    def test_invalid_payment_status(self):
        update = {"payment_status": "Failed"}
        flag_info = "Invalid payment_status. (Failed)"
        self.assertFlagged(update, flag_info)

    def test_duplicate_txn_id(self):       
        self.client.post("/ipn/", IPN_POST_PARAMS)
        self.client.post("/ipn/", IPN_POST_PARAMS)
        self.assertEqual(len(PayPalIPN.objects.all()), 2)
        ipn_obj = PayPalIPN.objects.order_by('-created_at')[1]
        self.assertEqual(ipn_obj.flag, True)
        self.assertEqual(ipn_obj.flag_info, "Duplicate txn_id. (51403485VH153354B)")
########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import *

urlpatterns = patterns('paypal.standard.ipn.views',
    (r'^ipn/$', 'ipn'),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('paypal.standard.ipn.views',            
    url(r'^$', 'ipn', name="paypal-ipn"),
)
########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from paypal.standard.ipn.forms import PayPalIPNForm
from paypal.standard.ipn.models import PayPalIPN


@require_POST
def ipn(request, item_check_callable=None):
    """
    PayPal IPN endpoint (notify_url).
    Used by both PayPal Payments Pro and Payments Standard to confirm transactions.
    http://tinyurl.com/d9vu9d
    
    PayPal IPN Simulator:
    https://developer.paypal.com/cgi-bin/devscr?cmd=_ipn-link-session
    """
    flag = None
    ipn_obj = None
    form = PayPalIPNForm(request.POST)
    if form.is_valid():
        try:
            ipn_obj = form.save(commit=False)
        except Exception, e:
            flag = "Exception while processing. (%s)" % e
    else:
        flag = "Invalid form. (%s)" % form.errors

    if ipn_obj is None:
        ipn_obj = PayPalIPN()    

    ipn_obj.initialize(request)

    if flag is not None:
        ipn_obj.set_flag(flag)
    else:
        # Secrets should only be used over SSL.
        if request.is_secure() and 'secret' in request.GET:
            ipn_obj.verify_secret(form, request.GET['secret'])
        else:
            ipn_obj.verify(item_check_callable)

    ipn_obj.save()
    return HttpResponse("OKAY")
########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from paypal.standard.helpers import duplicate_txn_id, check_secret
from paypal.standard.conf import RECEIVER_EMAIL, POSTBACK_ENDPOINT, SANDBOX_POSTBACK_ENDPOINT


class PayPalStandardBase(models.Model):
    """Meta class for common variables shared by IPN and PDT: http://tinyurl.com/cuq6sj"""
    # @@@ Might want to add all these one distant day.
    # FLAG_CODE_CHOICES = (
    # PAYMENT_STATUS_CHOICES = "Canceled_ Reversal Completed Denied Expired Failed Pending Processed Refunded Reversed Voided".split()
    # AUTH_STATUS_CHOICES = "Completed Pending Voided".split()
    # ADDRESS_STATUS_CHOICES = "confirmed unconfirmed".split()
    # PAYER_STATUS_CHOICES = "verified / unverified".split()
    # PAYMENT_TYPE_CHOICES =  "echeck / instant.split()
    # PENDING_REASON = "address authorization echeck intl multi-currency unilateral upgrade verify other".split()
    # REASON_CODE = "chargeback guarantee buyer_complaint refund other".split()
    # TRANSACTION_ENTITY_CHOICES = "auth reauth order payment".split()
    
    # Transaction and Notification-Related Variables
    business = models.CharField(max_length=127, blank=True, help_text="Email where the money was sent.")
    charset=models.CharField(max_length=32, blank=True)
    custom = models.CharField(max_length=255, blank=True)
    notify_version = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    parent_txn_id = models.CharField("Parent Transaction ID", max_length=19, blank=True)
    receiver_email = models.EmailField(max_length=127, blank=True)
    receiver_id = models.CharField(max_length=127, blank=True)  # 258DLEHY2BDK6
    residence_country = models.CharField(max_length=2, blank=True)
    test_ipn = models.BooleanField(default=False, blank=True)
    txn_id = models.CharField("Transaction ID", max_length=19, blank=True, help_text="PayPal transaction ID.")
    txn_type = models.CharField("Transaction Type", max_length=128, blank=True, help_text="PayPal transaction type.")
    verify_sign = models.CharField(max_length=255, blank=True)    
    
    # Buyer Information Variables
    address_country = models.CharField(max_length=64, blank=True)
    address_city = models.CharField(max_length=40, blank=True)
    address_country_code = models.CharField(max_length=64, blank=True, help_text="ISO 3166")
    address_name = models.CharField(max_length=128, blank=True)
    address_state = models.CharField(max_length=40, blank=True)
    address_status = models.CharField(max_length=11, blank=True)
    address_street = models.CharField(max_length=200, blank=True)
    address_zip = models.CharField(max_length=20, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=64, blank=True)
    last_name = models.CharField(max_length=64, blank=True)
    payer_business_name = models.CharField(max_length=127, blank=True)
    payer_email = models.CharField(max_length=127, blank=True)
    payer_id = models.CharField(max_length=13, blank=True)
    
    # Payment Information Variables
    auth_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    auth_exp = models.CharField(max_length=28, blank=True)
    auth_id = models.CharField(max_length=19, blank=True)
    auth_status = models.CharField(max_length=9, blank=True) 
    exchange_rate = models.DecimalField(max_digits=64, decimal_places=16, default=0, blank=True, null=True)
    invoice = models.CharField(max_length=127, blank=True)
    item_name = models.CharField(max_length=127, blank=True)
    item_number = models.CharField(max_length=127, blank=True)
    mc_currency = models.CharField(max_length=32, default="USD", blank=True)
    mc_fee = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_gross = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_handling = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_shipping = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    memo = models.CharField(max_length=255, blank=True)
    num_cart_items = models.IntegerField(blank=True, default=0, null=True)
    option_name1 = models.CharField(max_length=64, blank=True)
    option_name2 = models.CharField(max_length=64, blank=True)
    payer_status = models.CharField(max_length=10, blank=True)
    payment_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    payment_gross = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    payment_status = models.CharField(max_length=9, blank=True)
    payment_type = models.CharField(max_length=7, blank=True)
    pending_reason = models.CharField(max_length=14, blank=True)
    protection_eligibility=models.CharField(max_length=32, blank=True)
    quantity = models.IntegerField(blank=True, default=1, null=True)
    reason_code = models.CharField(max_length=15, blank=True)
    remaining_settle = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    settle_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    settle_currency = models.CharField(max_length=32, blank=True)
    shipping = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    shipping_method = models.CharField(max_length=255, blank=True)
    tax = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    transaction_entity = models.CharField(max_length=7, blank=True)
    
    # Auction Variables
    auction_buyer_id = models.CharField(max_length=64, blank=True)
    auction_closing_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    auction_multi_item = models.IntegerField(blank=True, default=0, null=True)
    for_auction = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
        
    # Recurring Payments Variables
    amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    amount_per_cycle = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    initial_payment_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    next_payment_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    outstanding_balance = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    payment_cycle= models.CharField(max_length=32, blank=True) #Monthly
    period_type = models.CharField(max_length=32, blank=True)
    product_name = models.CharField(max_length=128, blank=True)
    product_type= models.CharField(max_length=128, blank=True)    
    profile_status = models.CharField(max_length=32, blank=True)
    recurring_payment_id = models.CharField(max_length=128, blank=True)  # I-FA4XVST722B9
    rp_invoice_id= models.CharField(max_length=127, blank=True)  # 1335-7816-2936-1451
    time_created = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    
    # Subscription Variables
    amount1 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    amount2 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    amount3 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_amount1 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_amount2 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    mc_amount3 = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    password = models.CharField(max_length=24, blank=True)
    period1 = models.CharField(max_length=32, blank=True)
    period2 = models.CharField(max_length=32, blank=True)
    period3 = models.CharField(max_length=32, blank=True)
    reattempt = models.CharField(max_length=1, blank=True)
    recur_times = models.IntegerField(blank=True, default=0, null=True)
    recurring = models.CharField(max_length=1, blank=True)
    retry_at = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    subscr_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    subscr_effective = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    subscr_id = models.CharField(max_length=19, blank=True)
    username = models.CharField(max_length=64, blank=True)
    
    # Dispute Resolution Variables
    case_creation_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    case_id = models.CharField(max_length=14, blank=True)
    case_type = models.CharField(max_length=24, blank=True)
    
    # Variables not categorized
    receipt_id= models.CharField(max_length=64, blank=True)  # 1335-7816-2936-1451 
    currency_code = models.CharField(max_length=32, default="USD", blank=True)
    handling_amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    transaction_subject = models.CharField(max_length=255, blank=True)

    # @@@ Mass Pay Variables (Not Implemented, needs a separate model, for each transaction x)
    # fraud_managment_pending_filters_x = models.CharField(max_length=255, blank=True) 
    # option_selection1_x = models.CharField(max_length=200, blank=True) 
    # option_selection2_x = models.CharField(max_length=200, blank=True) 
    # masspay_txn_id_x = models.CharField(max_length=19, blank=True)
    # mc_currency_x = models.CharField(max_length=32, default="USD", blank=True)
    # mc_fee_x = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    # mc_gross_x = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    # mc_handlingx = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    # payment_date = models.DateTimeField(blank=True, null=True, help_text="HH:MM:SS DD Mmm YY, YYYY PST")
    # payment_status = models.CharField(max_length=9, blank=True)
    # reason_code = models.CharField(max_length=15, blank=True)
    # receiver_email_x = models.EmailField(max_length=127, blank=True)
    # status_x = models.CharField(max_length=9, blank=True)
    # unique_id_x = models.CharField(max_length=13, blank=True)

    # Non-PayPal Variables - full IPN/PDT query and time fields.    
    ipaddress = models.IPAddressField(blank=True)
    flag = models.BooleanField(default=False, blank=True)
    flag_code = models.CharField(max_length=16, blank=True)
    flag_info = models.TextField(blank=True)
    query = models.TextField(blank=True)  # What we sent to PayPal.
    response = models.TextField(blank=True)  # What we got back.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

    def __unicode__(self):
        if self.is_transaction():
            return self.format % ("Transaction", self.txn_id)
        else:
            return self.format % ("Recurring", self.recurring_payment_id)
        
    def is_transaction(self):
        return len(self.txn_id) > 0

    def is_recurring(self):
        return len(self.recurring_payment_id) > 0
    
    def is_subscription_cancellation(self):
        return self.txn_type == "subscr_cancel"
    
    def is_subscription_end_of_term(self):
        return self.txn_type == "subscr_eot"
    
    def is_subscription_modified(self):
        return self.txn_type == "subscr_modify"
    
    def is_subscription_signup(self):
        return self.txn_type == "subscr_signup"
    
    def set_flag(self, info, code=None):
        """Sets a flag on the transaction and also sets a reason."""
        self.flag = True
        self.flag_info += info
        if code is not None:
            self.flag_code = code
        
    def verify(self, item_check_callable=None):
        """
        Verifies an IPN and a PDT.
        Checks for obvious signs of weirdness in the payment and flags appropriately.
        
        Provide a callable that takes an instance of this class as a parameter and returns
        a tuple (False, None) if the item is valid. Should return (True, "reason") if the
        item isn't valid. Strange but backward compatible :) This function should check 
        that `mc_gross`, `mc_currency` `item_name` and `item_number` are all correct.

        """
        self.response = self._postback()
        self._verify_postback()  
        if not self.flag:
            if self.is_transaction():
                if self.payment_status != "Completed":
                    self.set_flag("Invalid payment_status. (%s)" % self.payment_status)
                if duplicate_txn_id(self):
                    self.set_flag("Duplicate txn_id. (%s)" % self.txn_id)
                if self.receiver_email != RECEIVER_EMAIL:
                    self.set_flag("Invalid receiver_email. (%s)" % self.receiver_email)
                if callable(item_check_callable):
                    flag, reason = item_check_callable(self)
                    if flag:
                        self.set_flag(reason)
            else:
                # @@@ Run a different series of checks on recurring payments.
                pass
        
        self.save()
        self.send_signals()

    def verify_secret(self, form_instance, secret):
        """Verifies an IPN payment over SSL using EWP."""
        if not check_secret(form_instance, secret):
            self.set_flag("Invalid secret. (%s)") % secret
        self.save()
        self.send_signals()

    def get_endpoint(self):
        """Set Sandbox endpoint if the test variable is present."""
        if self.test_ipn:
            return SANDBOX_POSTBACK_ENDPOINT
        else:
            return POSTBACK_ENDPOINT

    def initialize(self, request):
        """Store the data we'll need to make the postback from the request object."""
        self.query = getattr(request, request.method).urlencode()
        self.ipaddress = request.META.get('REMOTE_ADDR', '')

    def send_signals(self):
        """After a transaction is completed use this to send success/fail signals"""
        raise NotImplementedError
        
    def _postback(self):
        """Perform postback to PayPal and store the response in self.response."""
        raise NotImplementedError
        
    def _verify_postback(self):
        """Check self.response is valid andcall self.set_flag if there is an error."""
        raise NotImplementedError
########NEW FILE########
__FILENAME__ = admin
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from string import split as L
from django.contrib import admin
from paypal.standard.pdt.models import PayPalPDT


# ToDo: How similiar is this to PayPalIPNAdmin? Could we just inherit off one common admin model?
class PayPalPDTAdmin(admin.ModelAdmin):
    date_hierarchy = 'payment_date'
    fieldsets = (
        (None, {
            "fields": L("flag txn_id txn_type payment_status payment_date transaction_entity reason_code pending_reason mc_gross mc_fee auth_status auth_amount auth_exp auth_id")
        }),
        ("Address", {
            "description": "The address of the Buyer.",
            'classes': ('collapse',),
            "fields": L("address_city address_country address_country_code address_name address_state address_status address_street address_zip")
        }),
        ("Buyer", {
            "description": "The information about the Buyer.",
            'classes': ('collapse',),
            "fields": L("first_name last_name payer_business_name payer_email payer_id payer_status contact_phone residence_country")
        }),
        ("Seller", {
            "description": "The information about the Seller.",
            'classes': ('collapse',),
            "fields": L("business item_name item_number quantity receiver_email receiver_id custom invoice memo")
        }),
        ("Subscriber", {
            "description": "The information about the Subscription.",
            'classes': ('collapse',),
            "fields": L("subscr_id subscr_date subscr_effective")
        }),
        ("Recurring", {
            "description": "Information about recurring Payments.",
            "classes": ("collapse",),
            "fields": L("profile_status initial_payment_amount  amount_per_cycle outstanding_balance period_type product_name product_type recurring_payment_id receipt_id next_payment_date")
        }),
        ("Admin", {
            "description": "Additional Info.",
            "classes": ('collapse',),
            "fields": L("test_ipn ipaddress query flag_code flag_info")
        }),
    )
    list_display = L("__unicode__ flag invoice custom payment_status created_at")
    search_fields = L("txn_id recurring_payment_id")
admin.site.register(PayPalPDT, PayPalPDTAdmin)
########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from paypal.standard.forms import PayPalStandardBaseForm
from paypal.standard.pdt.models import PayPalPDT


class PayPalPDTForm(PayPalStandardBaseForm):
    class Meta:
        model = PayPalPDT
########NEW FILE########
__FILENAME__ = 0001_first_migration
# -*- coding: utf-8 -*-

from south.db import db
from django.db import models
from paypal.standard.pdt.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'PayPalPDT'
        db.create_table('paypal_pdt', (
            ('id', models.AutoField(primary_key=True)),
            ('business', models.CharField(max_length=127, blank=True)),
            ('charset', models.CharField(max_length=32, blank=True)),
            ('custom', models.CharField(max_length=255, blank=True)),
            ('notify_version', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('parent_txn_id', models.CharField("Parent Transaction ID", max_length=19, blank=True)),
            ('receiver_email', models.EmailField(max_length=127, blank=True)),
            ('receiver_id', models.CharField(max_length=127, blank=True)),
            ('residence_country', models.CharField(max_length=2, blank=True)),
            ('test_ipn', models.BooleanField(default=False, blank=True)),
            ('txn_id', models.CharField("Transaction ID", max_length=19, blank=True)),
            ('txn_type', models.CharField("Transaction Type", max_length=128, blank=True)),
            ('verify_sign', models.CharField(max_length=255, blank=True)),
            ('address_country', models.CharField(max_length=64, blank=True)),
            ('address_city', models.CharField(max_length=40, blank=True)),
            ('address_country_code', models.CharField(max_length=64, blank=True)),
            ('address_name', models.CharField(max_length=128, blank=True)),
            ('address_state', models.CharField(max_length=40, blank=True)),
            ('address_status', models.CharField(max_length=11, blank=True)),
            ('address_street', models.CharField(max_length=200, blank=True)),
            ('address_zip', models.CharField(max_length=20, blank=True)),
            ('contact_phone', models.CharField(max_length=20, blank=True)),
            ('first_name', models.CharField(max_length=64, blank=True)),
            ('last_name', models.CharField(max_length=64, blank=True)),
            ('payer_business_name', models.CharField(max_length=127, blank=True)),
            ('payer_email', models.CharField(max_length=127, blank=True)),
            ('payer_id', models.CharField(max_length=13, blank=True)),
            ('auth_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('auth_exp', models.CharField(max_length=28, blank=True)),
            ('auth_id', models.CharField(max_length=19, blank=True)),
            ('auth_status', models.CharField(max_length=9, blank=True)),
            ('exchange_rate', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=16, blank=True)),
            ('invoice', models.CharField(max_length=127, blank=True)),
            ('item_name', models.CharField(max_length=127, blank=True)),
            ('item_number', models.CharField(max_length=127, blank=True)),
            ('mc_currency', models.CharField(default='USD', max_length=32, blank=True)),
            ('mc_fee', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_gross', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_handling', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_shipping', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('memo', models.CharField(max_length=255, blank=True)),
            ('num_cart_items', models.IntegerField(default=0, null=True, blank=True)),
            ('option_name1', models.CharField(max_length=64, blank=True)),
            ('option_name2', models.CharField(max_length=64, blank=True)),
            ('payer_status', models.CharField(max_length=10, blank=True)),
            ('payment_date', models.DateTimeField(null=True, blank=True)),
            ('payment_gross', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('payment_status', models.CharField(max_length=9, blank=True)),
            ('payment_type', models.CharField(max_length=7, blank=True)),
            ('pending_reason', models.CharField(max_length=14, blank=True)),
            ('protection_eligibility', models.CharField(max_length=32, blank=True)),
            ('quantity', models.IntegerField(default=1, null=True, blank=True)),
            ('reason_code', models.CharField(max_length=15, blank=True)),
            ('remaining_settle', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('settle_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('settle_currency', models.CharField(max_length=32, blank=True)),
            ('shipping', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('shipping_method', models.CharField(max_length=255, blank=True)),
            ('tax', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('transaction_entity', models.CharField(max_length=7, blank=True)),
            ('auction_buyer_id', models.CharField(max_length=64, blank=True)),
            ('auction_closing_date', models.DateTimeField(null=True, blank=True)),
            ('auction_multi_item', models.IntegerField(default=0, null=True, blank=True)),
            ('for_auction', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount_per_cycle', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('initial_payment_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('next_payment_date', models.DateTimeField(null=True, blank=True)),
            ('outstanding_balance', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('payment_cycle', models.CharField(max_length=32, blank=True)),
            ('period_type', models.CharField(max_length=32, blank=True)),
            ('product_name', models.CharField(max_length=128, blank=True)),
            ('product_type', models.CharField(max_length=128, blank=True)),
            ('profile_status', models.CharField(max_length=32, blank=True)),
            ('recurring_payment_id', models.CharField(max_length=128, blank=True)),
            ('rp_invoice_id', models.CharField(max_length=127, blank=True)),
            ('time_created', models.DateTimeField(null=True, blank=True)),
            ('amount1', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount2', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('amount3', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_amount1', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_amount2', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('mc_amount3', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('password', models.CharField(max_length=24, blank=True)),
            ('period1', models.CharField(max_length=32, blank=True)),
            ('period2', models.CharField(max_length=32, blank=True)),
            ('period3', models.CharField(max_length=32, blank=True)),
            ('reattempt', models.CharField(max_length=1, blank=True)),
            ('recur_times', models.IntegerField(default=0, null=True, blank=True)),
            ('recurring', models.CharField(max_length=1, blank=True)),
            ('retry_at', models.DateTimeField(null=True, blank=True)),
            ('subscr_date', models.DateTimeField(null=True, blank=True)),
            ('subscr_effective', models.DateTimeField(null=True, blank=True)),
            ('subscr_id', models.CharField(max_length=19, blank=True)),
            ('username', models.CharField(max_length=64, blank=True)),
            ('case_creation_date', models.DateTimeField(null=True, blank=True)),
            ('case_id', models.CharField(max_length=14, blank=True)),
            ('case_type', models.CharField(max_length=24, blank=True)),
            ('receipt_id', models.CharField(max_length=64, blank=True)),
            ('currency_code', models.CharField(default='USD', max_length=32, blank=True)),
            ('handling_amount', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('transaction_subject', models.CharField(max_length=255, blank=True)),
            ('ipaddress', models.IPAddressField(blank=True)),
            ('flag', models.BooleanField(default=False, blank=True)),
            ('flag_code', models.CharField(max_length=16, blank=True)),
            ('flag_info', models.TextField(blank=True)),
            ('query', models.TextField(blank=True)),
            ('response', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('from_view', models.CharField(max_length=6, null=True, blank=True)),
            ('amt', models.DecimalField(default=0, null=True, max_digits=64, decimal_places=2, blank=True)),
            ('cm', models.CharField(max_length=255, blank=True)),
            ('sig', models.CharField(max_length=255, blank=True)),
            ('tx', models.CharField(max_length=255, blank=True)),
            ('st', models.CharField(max_length=32, blank=True)),
        ))
        db.send_create_signal('pdt', ['PayPalPDT'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'PayPalPDT'
        db.delete_table('paypal_pdt')
        
    
    
    models = {
        'pdt.paypalpdt': {
            'Meta': {'db_table': '"paypal_pdt"'},
            'address_city': ('models.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_country': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_country_code': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_name': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'address_state': ('models.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_status': ('models.CharField', [], {'max_length': '11', 'blank': 'True'}),
            'address_street': ('models.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'address_zip': ('models.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount1': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount2': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount3': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount_per_cycle': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amt': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auction_buyer_id': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'auction_closing_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'auction_multi_item': ('models.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'auth_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auth_exp': ('models.CharField', [], {'max_length': '28', 'blank': 'True'}),
            'auth_id': ('models.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'auth_status': ('models.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'business': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'case_creation_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'case_id': ('models.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'case_type': ('models.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'charset': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'cm': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'contact_phone': ('models.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'created_at': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'currency_code': ('models.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'custom': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'exchange_rate': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '16', 'blank': 'True'}),
            'first_name': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'flag': ('models.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'flag_code': ('models.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'flag_info': ('models.TextField', [], {'blank': 'True'}),
            'for_auction': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'from_view': ('models.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'handling_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'initial_payment_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'invoice': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'ipaddress': ('models.IPAddressField', [], {'blank': 'True'}),
            'item_name': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'item_number': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'last_name': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'mc_amount1': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount2': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount3': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_currency': ('models.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'mc_fee': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_gross': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_handling': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_shipping': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'memo': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'next_payment_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'notify_version': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'num_cart_items': ('models.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'option_name1': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'option_name2': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'outstanding_balance': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'parent_txn_id': ('models.CharField', ['"Parent Transaction ID"'], {'max_length': '19', 'blank': 'True'}),
            'password': ('models.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'payer_business_name': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_email': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_id': ('models.CharField', [], {'max_length': '13', 'blank': 'True'}),
            'payer_status': ('models.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'payment_cycle': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'payment_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'payment_gross': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'payment_status': ('models.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'payment_type': ('models.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'pending_reason': ('models.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'period1': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period2': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period3': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period_type': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'product_name': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'product_type': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'profile_status': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'protection_eligibility': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'quantity': ('models.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'query': ('models.TextField', [], {'blank': 'True'}),
            'reason_code': ('models.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'reattempt': ('models.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'receipt_id': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'receiver_email': ('models.EmailField', [], {'max_length': '127', 'blank': 'True'}),
            'receiver_id': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'recur_times': ('models.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'recurring': ('models.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'recurring_payment_id': ('models.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'remaining_settle': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'residence_country': ('models.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'response': ('models.TextField', [], {'blank': 'True'}),
            'retry_at': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rp_invoice_id': ('models.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'settle_amount': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'settle_currency': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'shipping': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'shipping_method': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'sig': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'st': ('models.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'subscr_date': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_effective': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_id': ('models.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'tax': ('models.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'test_ipn': ('models.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'time_created': ('models.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'transaction_entity': ('models.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'transaction_subject': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'tx': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'txn_id': ('models.CharField', ['"Transaction ID"'], {'max_length': '19', 'blank': 'True'}),
            'txn_type': ('models.CharField', ['"Transaction Type"'], {'max_length': '128', 'blank': 'True'}),
            'updated_at': ('models.DateTimeField', [], {'auto_now': 'True'}),
            'username': ('models.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'verify_sign': ('models.CharField', [], {'max_length': '255', 'blank': 'True'})
        }
    }
    
    complete_apps = ['pdt']

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from urllib import unquote_plus
import urllib2
from django.db import models
from django.conf import settings
from django.http import QueryDict
from django.utils.http import urlencode
from paypal.standard.models import PayPalStandardBase
from paypal.standard.conf import POSTBACK_ENDPOINT, SANDBOX_POSTBACK_ENDPOINT
from paypal.standard.pdt.signals import pdt_successful, pdt_failed

# ### Todo: Move this logic to conf.py:
# if paypal.standard.pdt is in installed apps
# ... then check for this setting in conf.py
class PayPalSettingsError(Exception):
    """Raised when settings are incorrect."""

try:
    IDENTITY_TOKEN = settings.PAYPAL_IDENTITY_TOKEN
except:
    raise PayPalSettingsError("You must set PAYPAL_IDENTITY_TOKEN in settings.py. Get this token by enabling PDT in your PayPal account.")


class PayPalPDT(PayPalStandardBase):
    format = u"<PDT: %s %s>"

    amt = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True)
    cm = models.CharField(max_length=255, blank=True)
    sig = models.CharField(max_length=255, blank=True)
    tx = models.CharField(max_length=255, blank=True)
    st = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table = "paypal_pdt"
        verbose_name = "PayPal PDT"

    def _postback(self):
        """
        Perform PayPal PDT Postback validation.
        Sends the transaction ID and business token to PayPal which responses with
        SUCCESS or FAILED.
        
        """
        postback_dict = dict(cmd="_notify-synch", at=IDENTITY_TOKEN, tx=self.tx)
        postback_params = urlencode(postback_dict)
        return urllib2.urlopen(self.get_endpoint(), postback_params).read()
    
    def get_endpoint(self):
        """Use the sandbox when in DEBUG mode as we don't have a test_ipn variable in pdt."""
        if settings.DEBUG:
            return SANDBOX_POSTBACK_ENDPOINT
        else:
            return POSTBACK_ENDPOINT
    
    def _verify_postback(self):
        # ### Now we don't really care what result was, just whether a flag was set or not.
        from paypal.standard.pdt.forms import PayPalPDTForm
        result = False
        response_list = self.response.split('\n')
        response_dict = {}
        for i, line in enumerate(response_list):
            unquoted_line = unquote_plus(line).strip()        
            if i == 0:
                self.st = unquoted_line
                if self.st == "SUCCESS":
                    result = True
            else:
                if self.st != "SUCCESS":
                    self.set_flag(line)
                    break
                try:                        
                    if not unquoted_line.startswith(' -'):
                        k, v = unquoted_line.split('=')                        
                        response_dict[k.strip()] = v.strip()
                except ValueError, e:
                    pass

        qd = QueryDict('', mutable=True)
        qd.update(response_dict)
        qd.update(dict(ipaddress=self.ipaddress, st=self.st, flag_info=self.flag_info))
        pdt_form = PayPalPDTForm(qd, instance=self)
        pdt_form.save(commit=False)
        
    def send_signals(self):
        # Send the PDT signals...
        if self.flag:
            pdt_failed.send(sender=self)
        else:
            pdt_successful.send(sender=self)
########NEW FILE########
__FILENAME__ = signals
"""
Note that sometimes you will get duplicate signals emitted, depending on configuration of your systems. 
If you do encounter this, you will need to add the "dispatch_uid" to your connect handlers:
http://code.djangoproject.com/wiki/Signals#Helppost_saveseemstobeemittedtwiceforeachsave

"""
from django.dispatch import Signal

# Sent when a payment is successfully processed.
pdt_successful = Signal()

# Sent when a payment is flagged.
pdt_failed = Signal()

# # Sent when a subscription was cancelled.
# subscription_cancel = Signal()
# 
# # Sent when a subscription expires.
# subscription_eot = Signal()
# 
# # Sent when a subscription was modified.
# subscription_modify = Signal()
# 
# # Sent when a subscription ends.
# subscription_signup = Signal()
########NEW FILE########
__FILENAME__ = test_pdt
"""
run this with ./manage.py test website
see http://www.djangoproject.com/documentation/testing/ for details
"""
import os
from django.conf import settings
from django.shortcuts import render_to_response
from django.test import TestCase
from paypal.standard.pdt.forms import PayPalPDTForm
from paypal.standard.pdt.models import PayPalPDT
from paypal.standard.pdt.signals import pdt_successful, pdt_failed


class DummyPayPalPDT(object):
    
    def __init__(self, update_context_dict={}):
        self.context_dict = {'st': 'SUCCESS', 'custom':'cb736658-3aad-4694-956f-d0aeade80194',
                             'txn_id':'1ED550410S3402306', 'mc_gross': '225.00', 
                             'business': settings.PAYPAL_RECEIVER_EMAIL, 'error': 'Error code: 1234'}
        
        self.context_dict.update(update_context_dict)
        
    def update_with_get_params(self, get_params):
        if get_params.has_key('tx'):
            self.context_dict['txn_id'] = get_params.get('tx')
        if get_params.has_key('amt'):
            self.context_dict['mc_gross'] = get_params.get('amt')
        if get_params.has_key('cm'):
            self.context_dict['custom'] = get_params.get('cm')
            
    def _postback(self, test=True):
        """Perform a Fake PayPal PDT Postback request."""
        # @@@ would be cool if this could live in the test templates dir...
        return render_to_response("pdt/test_pdt_response.html", self.context_dict).content

class PDTTest(TestCase):
    urls = "paypal.standard.pdt.tests.test_urls"
    template_dirs = [os.path.join(os.path.dirname(__file__), 'templates'),]

    def setUp(self):
        # set up some dummy PDT get parameters
        self.get_params = {"tx":"4WJ86550014687441", "st":"Completed", "amt":"225.00", "cc":"EUR",
                      "cm":"a3e192b8-8fea-4a86-b2e8-d5bf502e36be", "item_number":"",
                      "sig":"blahblahblah"}
        
        # monkey patch the PayPalPDT._postback function
        self.dpppdt = DummyPayPalPDT()
        self.dpppdt.update_with_get_params(self.get_params)
        PayPalPDT._postback = self.dpppdt._postback

    def test_verify_postback(self):
        dpppdt = DummyPayPalPDT()
        paypal_response = dpppdt._postback()
        assert('SUCCESS' in paypal_response)
        self.assertEqual(len(PayPalPDT.objects.all()), 0)
        pdt_obj = PayPalPDT()
        pdt_obj.ipaddress = '127.0.0.1'
        pdt_obj.response = paypal_response
        pdt_obj._verify_postback()
        self.assertEqual(len(PayPalPDT.objects.all()), 0)
        self.assertEqual(pdt_obj.txn_id, '1ED550410S3402306')
        
    def test_pdt(self):        
        self.assertEqual(len(PayPalPDT.objects.all()), 0)        
        self.dpppdt.update_with_get_params(self.get_params)
        paypal_response = self.client.get("/pdt/", self.get_params)        
        self.assertContains(paypal_response, 'Transaction complete', status_code=200)
        self.assertEqual(len(PayPalPDT.objects.all()), 1)

    def test_pdt_signals(self):
        self.successful_pdt_fired = False        
        self.failed_pdt_fired = False
        
        def successful_pdt(sender, **kwargs):
            self.successful_pdt_fired = True
        pdt_successful.connect(successful_pdt)
            
        def failed_pdt(sender, **kwargs):
            self.failed_pdt_fired = True 
        pdt_failed.connect(failed_pdt)
        
        self.assertEqual(len(PayPalPDT.objects.all()), 0)        
        paypal_response = self.client.get("/pdt/", self.get_params)
        self.assertContains(paypal_response, 'Transaction complete', status_code=200)        
        self.assertEqual(len(PayPalPDT.objects.all()), 1)
        self.assertTrue(self.successful_pdt_fired)
        self.assertFalse(self.failed_pdt_fired)        
        pdt_obj = PayPalPDT.objects.all()[0]
        self.assertEqual(pdt_obj.flag, False)
        
    def test_double_pdt_get(self):
        self.assertEqual(len(PayPalPDT.objects.all()), 0)            
        paypal_response = self.client.get("/pdt/", self.get_params)
        self.assertContains(paypal_response, 'Transaction complete', status_code=200)
        self.assertEqual(len(PayPalPDT.objects.all()), 1)
        pdt_obj = PayPalPDT.objects.all()[0]        
        self.assertEqual(pdt_obj.flag, False)        
        paypal_response = self.client.get("/pdt/", self.get_params)
        self.assertContains(paypal_response, 'Transaction complete', status_code=200)
        self.assertEqual(len(PayPalPDT.objects.all()), 1) # we don't create a new pdt        
        pdt_obj = PayPalPDT.objects.all()[0]
        self.assertEqual(pdt_obj.flag, False)

    def test_no_txn_id_in_pdt(self):
        self.dpppdt.context_dict.pop('txn_id')
        self.get_params={}
        paypal_response = self.client.get("/pdt/", self.get_params)
        self.assertContains(paypal_response, 'Transaction Failed', status_code=200)
        self.assertEqual(len(PayPalPDT.objects.all()), 0)
        
    def test_custom_passthrough(self):
        self.assertEqual(len(PayPalPDT.objects.all()), 0)        
        self.dpppdt.update_with_get_params(self.get_params)
        paypal_response = self.client.get("/pdt/", self.get_params)
        self.assertContains(paypal_response, 'Transaction complete', status_code=200)
        self.assertEqual(len(PayPalPDT.objects.all()), 1)
        pdt_obj = PayPalPDT.objects.all()[0]
        self.assertEqual(pdt_obj.custom, self.get_params['cm'] )
########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import *

urlpatterns = patterns('paypal.standard.pdt.views',
    (r'^pdt/$', 'pdt'),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('paypal.standard.pdt.views',
    url(r'^$', 'pdt', name="paypal-pdt"),
)
########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.decorators.http import require_GET
from paypal.standard.pdt.models import PayPalPDT
from paypal.standard.pdt.forms import PayPalPDTForm
 
 
@require_GET
def pdt(request, item_check_callable=None, template="pdt/pdt.html", context=None):
    """Payment data transfer implementation: http://tinyurl.com/c9jjmw"""
    context = context or {}
    pdt_obj = None
    txn_id = request.GET.get('tx')
    failed = False
    if txn_id is not None:
        # If an existing transaction with the id tx exists: use it
        try:
            pdt_obj = PayPalPDT.objects.get(txn_id=txn_id)
        except PayPalPDT.DoesNotExist:
            # This is a new transaction so we continue processing PDT request
            pass
        
        if pdt_obj is None:
            form = PayPalPDTForm(request.GET)
            if form.is_valid():
                try:
                    pdt_obj = form.save(commit=False)
                except Exception, e:
                    error = repr(e)
                    failed = True
            else:
                error = form.errors
                failed = True
            
            if failed:
                pdt_obj = PayPalPDT()
                pdt_obj.set_flag("Invalid form. %s" % error)
            
            pdt_obj.initialize(request)
        
            if not failed:
                # The PDT object gets saved during verify
                pdt_obj.verify(item_check_callable)
    else:
        pass # we ignore any PDT requests that don't have a transaction id
 
    context.update({"failed":failed, "pdt_obj":pdt_obj})
    return render_to_response(template, context, RequestContext(request))
########NEW FILE########
__FILENAME__ = widgets
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms
from django.forms.util import flatatt
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode


class ValueHiddenInput(forms.HiddenInput):
    """
    Widget that renders only if it has a value.
    Used to remove unused fields from PayPal buttons.
    """
    def render(self, name, value, attrs=None):
        if value is None:
            return u''
        else:
            return super(ValueHiddenInput, self).render(name, value, attrs)

class ReservedValueHiddenInput(ValueHiddenInput):
    """
    Overrides the default name attribute of the form.
    Used for the PayPal `return` field.
    """
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type)
        if value != '':
            final_attrs['value'] = force_unicode(value)
        return mark_safe(u'<input%s />' % flatatt(final_attrs))
########NEW FILE########
