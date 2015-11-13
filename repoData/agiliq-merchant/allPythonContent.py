__FILENAME__ = admin
from django.contrib import admin
import billing.models as billing_models

admin.site.register(billing_models.GCNewOrderNotification)
admin.site.register(billing_models.AuthorizeAIMResponse)
admin.site.register(billing_models.WorldPayResponse)
admin.site.register(billing_models.AmazonFPSResponse)


class PaylaneTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'customer_email', 'transaction_date', 'amount', 'success', 'error_code')
    list_filter = ('success',)
    ordering = ('-transaction_date',)
    search_fields = ['customer_name', 'customer_email']

admin.site.register(billing_models.PaylaneTransaction, PaylaneTransactionAdmin)

########NEW FILE########
__FILENAME__ = authorize_net_forms
from django import forms


class AuthorizeNetDPMForm(forms.Form):
    x_card_num = forms.CharField(max_length=16, label="Credit Card #")
    x_exp_date = forms.CharField(max_length=5, label="Exp Date (mm/yy)")
    x_card_code = forms.CharField(max_length=4, label="CVV")

    x_first_name = forms.CharField(max_length=50, label="First Name")
    x_last_name = forms.CharField(max_length=50, label="Last Name")

    x_address = forms.CharField(widget=forms.Textarea, max_length=60, label="Address")
    x_city = forms.CharField(max_length=40, label="City")
    x_state = forms.CharField(max_length=40, label="State")
    x_zip = forms.CharField(max_length=20, label="Zip")
    x_country = forms.CharField(max_length=60, label="Country")

    x_amount = forms.CharField(label="Amount (in USD)")

    x_login = forms.CharField(widget=forms.HiddenInput(), required=False)
    x_fp_sequence = forms.CharField(widget=forms.HiddenInput(), required=False)
    x_fp_timestamp = forms.CharField(widget=forms.HiddenInput())
    x_fp_hash = forms.CharField(widget=forms.HiddenInput())
    x_type = forms.CharField(widget=forms.HiddenInput())

    x_relay_response = forms.CharField(initial="TRUE", widget=forms.HiddenInput())

########NEW FILE########
__FILENAME__ = braintree_payments_forms
from django import forms
from django.conf import settings


class BraintreePaymentsForm(forms.Form):
    transaction__customer__first_name = forms.CharField(max_length=50, required=False)
    transaction__customer__last_name = forms.CharField(max_length=50, required=False)
    transaction__customer__company = forms.CharField(max_length=100, required=False)
    transaction__customer__email = forms.EmailField(required=False)
    transaction__customer__phone = forms.CharField(max_length=15, required=False)
    transaction__customer__fax = forms.CharField(max_length=15, required=False)
    transaction__customer__website = forms.URLField(required=False)
    transaction__credit_card__cardholder_name = forms.CharField(max_length=100)
    transaction__credit_card__number = forms.CharField()
    transaction__credit_card__cvv = forms.CharField(max_length=4)
    transaction__credit_card__expiration_date = forms.CharField(max_length=7)

    transaction__billing__first_name = forms.CharField(max_length=50, required=False)
    transaction__billing__last_name = forms.CharField(max_length=50, required=False)
    transaction__billing__company = forms.CharField(max_length=100, required=False)
    transaction__billing__street_address = forms.CharField(widget=forms.Textarea(), required=False)
    transaction__billing__extended_address = forms.CharField(widget=forms.Textarea(), required=False)
    transaction__billing__locality = forms.CharField(max_length=50, required=False)
    transaction__billing__region = forms.CharField(max_length=50, required=False)
    transaction__billing__postal_code = forms.CharField(max_length=10, required=False)
    transaction__billing__country_code_alpha2 = forms.CharField(max_length=2, required=False)
    transaction__billing__country_code_alpha3 = forms.CharField(max_length=3, required=False)
    transaction__billing__country_code_numeric = forms.IntegerField(required=False, min_value=0)
    transaction__billing__country_name = forms.CharField(max_length=50, required=False)

    transaction__shipping__first_name = forms.CharField(max_length=50, required=False)
    transaction__shipping__last_name = forms.CharField(max_length=50, required=False)
    transaction__shipping__company = forms.CharField(max_length=100, required=False)
    transaction__shipping__street_address = forms.CharField(widget=forms.Textarea(), required=False)
    transaction__shipping__extended_address = forms.CharField(widget=forms.Textarea(), required=False)
    transaction__shipping__locality = forms.CharField(max_length=50, required=False)
    transaction__shipping__region = forms.CharField(max_length=50, required=False)
    transaction__shipping__postal_code = forms.CharField(max_length=10, required=False)
    transaction__shipping__country_code_alpha2 = forms.CharField(max_length=2, required=False)
    transaction__shipping__country_code_alpha3 = forms.CharField(max_length=3, required=False)
    transaction__shipping__country_code_numeric = forms.IntegerField(required=False, min_value=0)
    transaction__shipping__country_name = forms.CharField(max_length=50, required=False)

    transaction__options__add_billing_address_to_payment_method = forms.BooleanField(required=False)
    transaction__options__store_shipping_address_in_vault = forms.BooleanField(required=False)
    transaction__options__store_in_vault_on_success = forms.BooleanField(required=False)
    transaction__options__submit_for_settlement = forms.BooleanField(required=False)

    transaction__type = forms.CharField(max_length=10)
    transaction__amount = forms.DecimalField(required=False)
    transaction__order_id = forms.CharField(max_length=50)
    transaction__customer__id = forms.CharField(max_length=50, required=False)
    transaction__credit_card__token = forms.CharField(max_length=50, required=False)
    transaction__payment_method_token = forms.CharField(max_length=50, required=False)

    tr_data = forms.CharField(widget=forms.HiddenInput())

########NEW FILE########
__FILENAME__ = common
from django import forms

from billing.utils.credit_card import CreditCard, CardNotSupported


class CreditCardFormBase(forms.Form):
    """
    Base class for a simple credit card form which provides some utilities like
    'get_credit_card' to return a CreditCard instance.

    If you pass the gateway as a keyword argument to the constructor,
    the gateway.validate_card method will be used in form validation.

    This class must be subclassed to provide the actual fields to be used.
    """

    def __init__(self, *args, **kwargs):
        self.gateway = kwargs.pop('gateway', None)
        super(CreditCardFormBase, self).__init__(*args, **kwargs)

    def get_credit_card(self):
        """
        Returns a CreditCard from the submitted (cleaned) data.

        If gateway was passed to the form constructor, the gateway.validate_card
        method will be called - which can throw CardNotSupported, and will also
        add the attribute 'card_type' which is the CreditCard subclass if it is
        successful.
        """
        card = CreditCard(**self.cleaned_data)
        if self.gateway is not None:
            self.gateway.validate_card(card)
        return card

    def clean(self):
        cleaned_data = super(CreditCardFormBase, self).clean()
        if self.errors:
            # Don't bother with further validation, it only confuses things
            # for the user to be presented with multiple error messages.
            return cleaned_data
        try:
            credit_card = self.get_credit_card()
            if not credit_card.is_valid():
                raise forms.ValidationError("Credit card details are invalid")
        except CardNotSupported:
            raise forms.ValidationError("This type of credit card is not supported. Please check the number.")
        return cleaned_data

########NEW FILE########
__FILENAME__ = eway_au_forms
from django import forms
from django.utils.translation import ugettext_lazy as _


class EwayAuForm(forms.Form):
    EWAY_ACCESSCODE = forms.CharField(widget=forms.HiddenInput())
    EWAY_CARDNAME = forms.CharField(label=_("Name"))
    EWAY_CARDNUMBER = forms.CharField(label=_("Credit card number"))
    EWAY_CARDMONTH = forms.CharField(label=_("Expiration month"))
    EWAY_CARDYEAR = forms.CharField(label=_("Expiration year"))
    EWAY_CARDCVN = forms.CharField(label=_("CVN"))

########NEW FILE########
__FILENAME__ = global_iris_forms
import datetime

from django import forms

from billing.forms.common import CreditCardFormBase

class CreditCardForm(CreditCardFormBase):

    cardholders_name = forms.CharField(label="Card holder's name", required=True)
    number = forms.CharField(required=True)
    month = forms.ChoiceField(label="Expiry month", choices=[])
    year = forms.ChoiceField(label="Expiry year", choices=[])
    verification_value = forms.CharField(label='CVV', required=True)

    def __init__(self, *args, **kwargs):
        super(CreditCardForm, self).__init__(*args, **kwargs)
        self.fields['year'].choices = self.get_year_choices()
        self.fields['month'].choices = self.get_month_choices()

    def get_year_choices(self):
        today = datetime.date.today()
        return [(y, y) for y in range(today.year, today.year + 21)]

    def get_month_choices(self):
        # Override if you want month names, for instance.
        return [(m, m) for m in range(1, 13)]


########NEW FILE########
__FILENAME__ = paylane_forms
# -*- coding: utf-8 -*-
# vim:tabstop=4:expandtab:sw=4:softtabstop=4
import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _
from billing.utils.credit_card import InvalidCard, Visa, MasterCard
from billing.utils.countries import COUNTRIES

curr_year = datetime.datetime.now().year
month_choices = ((ii, ii) for ii in range(1, 13))
year_choices = ((ii, ii) for ii in range(curr_year, curr_year + 7))


class PaylaneForm(forms.Form):
    name_on_card = forms.CharField(label=_("Name on card"), max_length=50)
    street_house = forms.CharField(label=_("Address"), max_length=46)
    city = forms.CharField(label=_("City"), max_length=40)
    state_address = forms.CharField(label=_("State"), max_length=40, required=False)
    zip_code = forms.CharField(label=_("Zip Code"), max_length=9)
    country_code = forms.ChoiceField(COUNTRIES, label=_("Country"))
    card_number = forms.RegexField(label=_("Card Number"), max_length=19, regex=r'[0-9]{13,19}$')
    card_code = forms.RegexField(label=_("Card Code"), max_length=4, regex=r'[0-9]{3,4}$')
    issue_number = forms.RegexField(label=_("Issue Number"), max_length=3, required=False, regex=r'[0-9]{1,3}$')
    expiration_month = forms.ChoiceField(label=_("Expiration date"), choices=month_choices)
    expiration_year = forms.ChoiceField(label=_("Expiration year"), choices=year_choices)

    def clean(self):
        cleaned_data = super(PaylaneForm, self).clean()

        if not self._errors:
            name = cleaned_data.get('name_on_card', '').split(' ', 1)
            first_name = name[0]
            last_name = ' '.join(name[1:])

            cc = Visa(first_name=first_name,
                    last_name=last_name,
                    month=cleaned_data.get('expiration_month'),
                    year=cleaned_data.get('expiration_year'),
                    number=cleaned_data.get('card_number'),
                    verification_value=cleaned_data.get('card_code'))

            if cc.is_expired():
                raise forms.ValidationError(_('This credit card has expired.'))

            if not cc.is_luhn_valid():
                raise forms.ValidationError(_('This credit card number isn\'t valid'))

            if not cc.is_valid():
                #this should never occur
                raise forms.ValidationError(_('Invalid credit card'))

            options = {
                    'customer': cleaned_data.get('name_on_card'),
                    'email': '',
                    'order_id': '',
                    'ip': '',
                    'description': '',
                    'merchant': '',
                    'billing_address': {
                            'name': cleaned_data.get('name_on_card'),
                            'company': '',
                            'address1': cleaned_data.get('street_house'),
                            'address2': '',
                            'city': cleaned_data.get('city'),
                            'state': '',
                            'country': cleaned_data.get('country_code'),
                            'zip': cleaned_data.get('zip_code'),
                            'phone': '',
                        },
                    'shipping_address': {}
                }

            cleaned_data['paylane'] = {
                    'credit_card': cc,
                    'options': options
                }

        return cleaned_data

########NEW FILE########
__FILENAME__ = paypal_forms
from django import forms
import re

from paypal.standard.forms import (PayPalPaymentsForm,
                                   PayPalEncryptedPaymentsForm)


INTEGER_FIELDS = ('amount_', 'item_number_', 'quantity_', 'tax_', 'shipping_',
                  'shipping2_', 'discount_amount_', 'discount_amount2_',
                  'discount_rate_', 'discount_rate2_', 'discount_num_',
                  'tax_rate_')
INTEGER_FIELD_RE = re.compile(r'|'.join(re.escape(f) for f in INTEGER_FIELDS))

CHAR_FIELDS = ('item_name_', 'on0_', 'on1_', 'os0_', 'os1_')
CHAR_FIELD_RE = re.compile(r'|'.join(re.escape(f) for f in CHAR_FIELDS))


class MultipleItemsMixin(object):
    """
    Use the initial data as a heuristic to create a form
    that accepts multiple items
    """

    def __init__(self, **kwargs):
        super(MultipleItemsMixin, self).__init__(**kwargs)
        has_multiple_items = False
        if 'initial' in kwargs:
            for k, v in kwargs['initial'].items():
                if INTEGER_FIELD_RE.match(k):
                    self.fields[k] = forms.IntegerField(
                        widget=forms.widgets.HiddenInput())
                    has_multiple_items = True
                elif CHAR_FIELD_RE.match(k):
                    has_multiple_items = True
                    self.fields[k] = forms.CharField(
                        widget=forms.widgets.HiddenInput())
        if has_multiple_items:
            self.fields['upload'] = forms.IntegerField(
                initial=1,
                widget=forms.widgets.HiddenInput())
            del self.fields['amount']
            del self.fields['item_name']
            self.initial['cmd'] = '_cart'


class MerchantPayPalPaymentsForm(MultipleItemsMixin, PayPalPaymentsForm):
    pass


class MerchantPayPalEncryptedPaymentsForm(MultipleItemsMixin, PayPalEncryptedPaymentsForm):
    pass

########NEW FILE########
__FILENAME__ = pin_forms
import re
from datetime import date
from django import forms
from billing import CreditCard
from billing.models.pin_models import PinCard

class CardNumberField(forms.CharField):
    """
    Field for entering card number, validates using mod 10
    """
    def clean(self, value):
        value = super(CardNumberField, self).clean(value)
        value = value.replace('-', '').replace(' ', '')
        if not verify_mod10(value):
            raise forms.ValidationError('The card number is not valid.')
        return value

def verify_mod10(ccnum):
    """
    Check a credit card number for validity using the mod10 algorithm.
    """
    ccnum = re.sub(r'[^0-9]', '', ccnum)
    double, sum = 0, 0
    for i in range(len(ccnum) - 1, -1, -1):
            for c in str((double + 1) * int(ccnum[i])): sum = sum + int(c)
            double = (double + 1) % 2
    return ((sum % 10) == 0)

class PinChargeForm(forms.ModelForm):
    number = CardNumberField()
    expiry_month = forms.IntegerField(min_value=1,
                            max_value=12,
                            widget=forms.NumberInput(attrs={'placeholder':'MM'}))
    expiry_year = forms.IntegerField(min_value=date.today().year,
                            max_value=date.today().year+20,
                            widget=forms.NumberInput(attrs={'placeholder':'YYYY'}))
    cvc = forms.IntegerField(min_value=0, max_value=9999)
    email = forms.EmailField()
    description = forms.CharField(max_length=255)

    user_fields = ('email', 'first_name', 'last_name')

    class Meta:
        model = PinCard
        exclude = []

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PinChargeForm, self).__init__(*args, **kwargs)
        # If we're supplying a valid user already, we can either leave the
        # fields in the template, pre-populated; or leave them out completely
        if user:
            for field in self.user_fields:
                self.fields[field].required = False
                value = getattr(user, field, None)
                if value:
                    self.fields[field].initial = value

    def get_credit_card(self):
        d = self.cleaned_data
        d['month'] = d['expiry_month']
        d['year'] = d['expiry_year']
        d['verification_value'] = d['cvc']
        card = CreditCard(**d)
        options = {
            'email': d['email'],
            'description': d['description'],
            'billing_address': {
                'address1': d['address_line1'],
                'address2': d.get('address_line2'),
                'city': d['address_city'],
                'zip': d['address_postcode'],
                'state': d['address_state'],
                'country': d['address_country'],
            }
        }
        return card, options

########NEW FILE########
__FILENAME__ = stripe_forms
from django import forms
import decimal
import datetime

curr_year = datetime.datetime.now().year
month_choices = ((ii, ii) for ii in range(1, 13))
year_choices = ((ii, ii) for ii in range(curr_year, curr_year + 7))


class StripeForm(forms.Form):
    # Small value to prevent non-zero values. Might need a relook
    amount = forms.DecimalField(min_value=decimal.Decimal('0.001'))
    credit_card_number = forms.CharField(max_length=16)
    credit_card_cvc = forms.CharField(max_length=4)
    credit_card_expiration_month = forms.CharField(max_length=2, widget=forms.Select(choices=month_choices))
    credit_card_expiration_year = forms.CharField(max_length=4, widget=forms.Select(choices=year_choices))

########NEW FILE########
__FILENAME__ = world_pay_forms
from django import forms
from hashlib import md5
from django.conf import settings


class WPHostedPaymentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(WPHostedPaymentForm, self).__init__(*args, **kwargs)
        if self.initial:
            self.initial["signatureFields"] = self.initial.get("signatureFields") or "instId:amount:cartId"
            signature_fields = self.initial["signatureFields"].split(":")
            hash_str = ""
            for field in signature_fields:
                hash_str += "%s" % self.initial[field]
                if not signature_fields.index(field) == len(signature_fields) - 1:
                    hash_str += ":"
            md5_hash = md5("%s:%s" % (settings.MERCHANT_SETTINGS["world_pay"]["MD5_SECRET_KEY"],
                                     hash_str)).hexdigest()
            self.initial["signature"] = self.initial.get("signature") or md5_hash

    # recurring(future pay) parameters
    futurePayType = forms.CharField(widget=forms.HiddenInput(), required=False)
    intervalUnit = forms.CharField(widget=forms.HiddenInput(), required=False)
    intervalMult = forms.CharField(widget=forms.HiddenInput(), required=False)
    option = forms.CharField(widget=forms.HiddenInput(), required=False)
    noOfPayments = forms.CharField(widget=forms.HiddenInput(), required=False)
    normalAmount = forms.CharField(widget=forms.HiddenInput(), required=False)
    startDelayUnit = forms.CharField(widget=forms.HiddenInput(), required=False)
    startDelayMult = forms.CharField(widget=forms.HiddenInput(), required=False)

    instId = forms.CharField(widget=forms.HiddenInput)
    cartId = forms.CharField(widget=forms.HiddenInput)
    amount = forms.DecimalField(widget=forms.HiddenInput)
    currency = forms.CharField(widget=forms.HiddenInput, initial="USD")
    desc = forms.CharField(widget=forms.HiddenInput)
    testMode = forms.CharField(widget=forms.HiddenInput)
    signatureFields = forms.CharField(widget=forms.HiddenInput)
    signature = forms.CharField(widget=forms.HiddenInput)

    #override Country field
    # country = CountryField(initial="AU")

########NEW FILE########
__FILENAME__ = gateway
from django.utils.importlib import import_module
from django.conf import settings
from .utils.credit_card import CardNotSupported

gateway_cache = {}


class GatewayModuleNotFound(Exception):
    pass


class GatewayNotConfigured(Exception):
    pass


class InvalidData(Exception):
    pass


class Gateway(object):
    """Sub-classes to inherit from this and implement the below methods"""

    # To indicate if the gateway is in test mode or not
    test_mode = getattr(settings, "MERCHANT_TEST_MODE", True)

    # The below are optional attributes to be implemented and used by subclases.
    #
    # Set to indicate the default currency for the gateway.
    default_currency = ""
    # Sequence of countries supported by the gateway in ISO 3166 alpha-2 format.
    # http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    supported_countries = []
    # Sequence of supported card types by the gateway. Members should be valid
    # subclasses of the Credit Card object.
    supported_cardtypes = []
    # Home page URL for the gateway. Used for information purposes only.
    homepage_url = ""
    # Name of the gateway.
    display_name = ""
    # Application name or some unique identifier for the gateway.
    application_id = ""

    def validate_card(self, credit_card):
        """Checks if the credit card is supported by the gateway
        and calls the `is_valid` method on it. Responsibility
        of the gateway author to use this method before every
        card transaction."""
        card_supported = None
        for card in self.supported_cardtypes:
            card_supported = card.regexp.match(credit_card.number)
            if card_supported:
                credit_card.card_type = card
                break
        if not card_supported:
            raise CardNotSupported("This credit card is not "
                                   "supported by the gateway.")
        # Gateways might provide some random number which
        # might not pass Luhn's test.
        if self.test_mode:
            return True
        return credit_card.is_valid()

    def purchase(self, money, credit_card, options=None):
        """One go authorize and capture transaction"""
        raise NotImplementedError

    def authorize(self, money, credit_card, options=None):
        """Authorization for a future capture transaction"""
        raise NotImplementedError

    def capture(self, money, authorization, options=None):
        """Capture funds from a previously authorized transaction"""
        raise NotImplementedError

    def void(self, identification, options=None):
        """Null/Blank/Delete a previous transaction"""
        raise NotImplementedError

    def credit(self, money, identification, options=None):
        """Refund a previously 'settled' transaction"""
        raise NotImplementedError

    def recurring(self, money, creditcard, options=None):
        """Setup a recurring transaction"""
        raise NotImplementedError

    def store(self, creditcard, options=None):
        """Store the credit card and user profile information
        on the gateway for future use"""
        raise NotImplementedError

    def unstore(self, identification, options=None):
        """Delete the previously stored credit card and user
        profile information on the gateway"""
        raise NotImplementedError


def get_gateway(gateway, *args, **kwargs):
    """
    Return a gateway instance specified by `gateway` name.
    This caches gateway classes in a module-level dictionnary to avoid hitting
    the filesystem every time we require a gateway.

    Should the list of available gateways change at runtime, one should then
    invalidate the cache, the simplest of ways would be to:

    >>> gateway_cache = {}
    """
    # Is the class in the cache?
    clazz = gateway_cache.get(gateway, None)
    if not clazz:
        # Let's actually load it (it's not in the cache)
        gateway_filename = "%s_gateway" % gateway
        gateway_module = None
        for app in settings.INSTALLED_APPS:
            try:
                gateway_module = import_module(".gateways.%s" % gateway_filename, package=app)
            except ImportError:
                pass
        if not gateway_module:
            raise GatewayModuleNotFound("Missing gateway: %s" % (gateway))
        gateway_class_name = "".join(gateway_filename.title().split("_"))
        try:
            clazz = getattr(gateway_module, gateway_class_name)
        except AttributeError:
            raise GatewayNotConfigured("Missing %s class in the gateway module." % gateway_class_name)
        gateway_cache[gateway] = clazz
    # We either hit the cache or load our class object, let's return an instance
    # of it.
    return clazz(*args, **kwargs)

########NEW FILE########
__FILENAME__ = authorize_net_gateway
import urllib
import urllib2
import datetime

from collections import namedtuple

from django.conf import settings
from django.template.loader import render_to_string

from billing.models import AuthorizeAIMResponse
from billing import Gateway, GatewayNotConfigured
from billing.signals import *
from billing.utils.credit_card import InvalidCard, Visa, \
    MasterCard, Discover, AmericanExpress
from billing.utils.xml_parser import parseString, nodeToDic

API_VERSION = '3.1'
DELIM_CHAR = ','
ENCAP_CHAR = '$'
APPROVED, DECLINED, ERROR, FRAUD_REVIEW = 1, 2, 3, 4
RESPONSE_CODE, RESPONSE_REASON_CODE, RESPONSE_REASON_TEXT = 0, 2, 3

MockAuthorizeAIMResponse = namedtuple(
    'AuthorizeAIMResponse', [
        'response_code',
        'response_reason_code',
        'response_reason_text'
    ]
)


def save_authorize_response(response):
    data = {}
    data['response_code'] = int(response[0])
    data['response_reason_code'] = response[2]
    data['response_reason_text'] = response[3]
    data['authorization_code'] = response[4]
    data['address_verification_response'] = response[5]
    data['transaction_id'] = response[6]
    data['invoice_number'] = response[7]
    data['description'] = response[8]
    data['amount'] = response[9]
    data['method'] = response[10]
    data['transaction_type'] = response[11]
    data['customer_id'] = response[12]

    data['first_name'] = response[13]
    data['last_name'] = response[14]
    data['company'] = response[15]
    data['address'] = response[16]
    data['city'] = response[17]
    data['state'] = response[18]
    data['zip_code'] = response[19]
    data['country'] = response[20]
    data['phone'] = response[21]
    data['fax'] = response[22]
    data['email'] = response[23]

    data['shipping_first_name'] = response[24]
    data['shipping_last_name'] = response[25]
    data['shipping_company'] = response[26]
    data['shipping_address'] = response[27]
    data['shipping_city'] = response[28]
    data['shipping_state'] = response[29]
    data['shipping_zip_code'] = response[30]
    data['shipping_country'] = response[31]
    data['card_code_response'] = response[38]
    return AuthorizeAIMResponse.objects.create(**data)


class AuthorizeNetGateway(Gateway):
    test_url = "https://test.authorize.net/gateway/transact.dll"
    live_url = "https://secure.authorize.net/gateway/transact.dll"

    arb_test_url = 'https://apitest.authorize.net/xml/v1/request.api'
    arb_live_url = 'https://api.authorize.net/xml/v1/request.api'

    supported_countries = ["US"]
    default_currency = "USD"

    supported_cardtypes = [Visa, MasterCard, AmericanExpress, Discover]
    homepage_url = "http://www.authorize.net/"
    display_name = "Authorize.Net"

    def __init__(self):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("authorize_net"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        authorize_net_settings = merchant_settings["authorize_net"]
        self.login = authorize_net_settings["LOGIN_ID"]
        self.password = authorize_net_settings["TRANSACTION_KEY"]

    def add_invoice(self, post, options):
        """add invoice details to the request parameters"""
        post['invoice_num'] = options.get('order_id', None)
        post['description'] = options.get('description', None)

    def add_creditcard(self, post, credit_card):
        """add credit card details to the request parameters"""
        post['card_num'] = credit_card.number
        post['card_code'] = credit_card.verification_value
        post['exp_date'] = credit_card.expire_date
        post['first_name'] = credit_card.first_name
        post['last_name'] = credit_card.last_name

    def add_address(self, post, options):
        """add billing/shipping address details to the request parameters"""
        if options.get('billing_address', None):
            address = options.get('billing_address')
            post['address'] = address.get('address1', '') + \
                               address.get('address2', '')
            post['company'] = address.get('company', '')
            post['phone'] = address.get('phone', '')
            post['zip'] = address.get('zip', '')
            post['city'] = address.get('city', '')
            post['country'] = address.get('country', '')
            post['state'] = address.get('state', '')

        if options.get('shipping_address', None):
            address = options.get('shipping_address')
            post['ship_to_first_name'] = address.get('name', '').split(" ")[0]
            post['ship_to_last_name'] = " ".join(address.get('name', '').split(" ")[1:])
            post['ship_to_address'] = address.get('address1', '') + \
                                         address.get('address2', '')
            post['ship_to_company'] = address.get('company', '')
            post['ship_to_phone'] = address.get('phone', '')
            post['ship_to_zip'] = address.get('zip', '')
            post['ship_to_city'] = address.get('city', '')
            post['ship_to_country'] = address.get('country', '')
            post['ship_to_state'] = address.get('state', '')

    def add_customer_data(self, post, options):
        """add customer details to the request parameters"""
        if 'email' in options:
            post['email'] = options['email']
            post['email_customer'] = bool(options.get('email_customer', True))

        if 'customer' in options:
            post['cust_id'] = options['customer']

        if 'ip' in options:
            post['customer_ip'] = options['ip']

    @property
    def service_url(self):
        if self.test_mode:
            return self.test_url
        return self.live_url

    def commit(self, action, money, parameters):
        if not action == 'VOID':
            parameters['amount'] = money

        parameters['test_request'] = self.test_mode
        url = self.service_url
        data = self.post_data(action, parameters)
        response = self.request(url, data)
        return response

    def post_data(self, action, parameters=None):
        """add API details, gateway response formating options
        to the request parameters"""
        if not parameters:
            parameters = {}
        post = {}

        post['version'] = API_VERSION
        post['login'] = self.login
        post['tran_key'] = self.password
        post['relay_response'] = "FALSE"
        post['type'] = action
        post['delim_data'] = "TRUE"
        post['delim_char'] = DELIM_CHAR
        post['encap_char'] = ENCAP_CHAR

        post.update(parameters)
        return urllib.urlencode(dict(('x_%s' % (k), v) for k, v in post.iteritems()))

    # this shoud be moved to a requests lib file
    def request(self, url, data, headers=None):
        """Make POST request to the payment gateway with the data and return
        gateway RESPONSE_CODE, RESPONSE_REASON_CODE, RESPONSE_REASON_TEXT"""
        if not headers:
            headers = {}
        conn = urllib2.Request(url=url, data=data, headers=headers)
        try:
            open_conn = urllib2.urlopen(conn)
            response = open_conn.read()
        except urllib2.URLError as e:
            return MockAuthorizeAIMResponse(5, '1', str(e))
        fields = response[1:-1].split('%s%s%s' % (ENCAP_CHAR, DELIM_CHAR, ENCAP_CHAR))
        return save_authorize_response(fields)

    def purchase(self, money, credit_card, options=None):
        """Using Authorize.net payment gateway, charge the given
        credit card for specified money"""
        if not options:
            options = {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        post = {}
        self.add_invoice(post, options)
        self.add_creditcard(post, credit_card)
        self.add_address(post, options)
        self.add_customer_data(post, options)

        response = self.commit("AUTH_CAPTURE", money, post)
        status = "SUCCESS"
        if response.response_code != 1:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=response)
        else:
            transaction_was_successful.send(sender=self,
                                            type="purchase",
                                            response=response)
        return {"status": status, "response": response}

    def authorize(self, money, credit_card, options=None):
        """Using Authorize.net payment gateway, authorize the
        credit card for specified money"""
        if not options:
            options = {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        post = {}
        self.add_invoice(post, options)
        self.add_creditcard(post, credit_card)
        self.add_address(post, options)
        self.add_customer_data(post, options)

        response = self.commit("AUTH_ONLY", money, post)
        status = "SUCCESS"
        if response.response_code != 1:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="authorization",
                                              response=response)
        else:
            transaction_was_successful.send(sender=self,
                                            type="authorization",
                                            response=response)
        return {"status": status, "response": response}

    def capture(self, money, authorization, options=None):
        """Using Authorize.net payment gateway, capture the
        authorize credit card"""
        if not options:
            options = {}
        post = {}
        post["trans_id"] = authorization
        post.update(options)

        response = self.commit("PRIOR_AUTH_CAPTURE", money, post)
        status = "SUCCESS"
        if response.response_code != 1:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="capture",
                                              response=response)
        else:
            transaction_was_successful.send(sender=self,
                                            type="capture",
                                            response=response)
        return {"status": status, "response": response}

    def void(self, identification, options=None):
        """Using Authorize.net payment gateway, void the
        specified transaction"""
        if not options:
            options = {}
        post = {}
        post["trans_id"] = identification
        post.update(options)

        # commit ignores the money argument for void, so we set it None
        response = self.commit("VOID", None, post)
        status = "SUCCESS"
        if response.response_code != 1:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="void",
                                              response=response)
        else:
            transaction_was_successful.send(sender=self,
                                            type="void",
                                            response=response)
        return {"status": status, "response": response}

    def credit(self, money, identification, options=None):
        """Using Authorize.net payment gateway, void the
        specified transaction"""
        if not options:
            options = {}
        post = {}
        post["trans_id"] = identification
        # Authorize.Net requuires the card or the last 4 digits be sent
        post["card_num"] = options["credit_card"]
        post.update(options)

        response = self.commit("CREDIT", money, post)
        status = "SUCCESS"
        if response.response_code != 1:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="credit",
                                              response=response)
        else:
            transaction_was_successful.send(sender=self,
                                            type="credit",
                                            response=response)
        return {"status": status, "response": response}

    def recurring(self, money, credit_card, options):
        if not options:
            options = {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")
        template_vars = {}
        template_vars['auth_login'] = self.login
        template_vars['auth_key'] = self.password
        template_vars['amount'] = money
        template_vars['card_number'] = credit_card.number
        template_vars['exp_date'] = credit_card.expire_date

        template_vars['start_date'] = options.get('start_date') or datetime.date.today().strftime("%Y-%m-%d")
        template_vars['total_occurrences'] = options.get('total_occurences', 9999)
        template_vars['interval_length'] = options.get('interval_length', 1)
        template_vars['interval_unit'] = options.get('interval_unit', 'months')
        template_vars['sub_name'] = options.get('sub_name', '')
        template_vars['first_name'] = credit_card.first_name
        template_vars['last_name'] = credit_card.last_name

        xml = render_to_string('billing/arb/arb_create_subscription.xml', template_vars)

        if self.test_mode:
            url = self.arb_test_url
        else:
            url = self.arb_live_url
        headers = {'content-type': 'text/xml'}

        conn = urllib2.Request(url=url, data=xml, headers=headers)
        try:
            open_conn = urllib2.urlopen(conn)
            xml_response = open_conn.read()
        except urllib2.URLError as e:
            return MockAuthorizeAIMResponse(5, '1', str(e))

        response = nodeToDic(parseString(xml_response))['ARBCreateSubscriptionResponse']
        # successful response
        # {u'ARBCreateSubscriptionResponse': {u'messages': {u'message': {u'code': u'I00001',
        #                                                               u'text': u'Successful.'},
        #                                                  u'resultCode': u'Ok'},
        #                                    u'subscriptionId': u'933728'}}

        status = "SUCCESS"
        if response['messages']['resultCode'].lower() != 'ok':
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=response)
        else:
            transaction_was_successful.send(sender=self,
                                            type="recurring",
                                            response=response)
        return {"status": status, "response": response}

    def store(self, creditcard, options=None):
        raise NotImplementedError

    def unstore(self, identification, options=None):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = beanstream_gateway
from beanstream.gateway import Beanstream
from beanstream.billing import CreditCard
from beanstream.process_transaction import Adjustment

from django.conf import settings

from billing import Gateway, GatewayNotConfigured
from billing.gateway import CardNotSupported
from billing.signals import transaction_was_successful, \
    transaction_was_unsuccessful
from billing.utils.credit_card import InvalidCard, Visa, \
    MasterCard, Discover, AmericanExpress

class BeanstreamGateway(Gateway):
    txnurl = "https://www.beanstream.com/scripts/process_transaction.asp"
    profileurl = "https://www.beanstream.com/scripts/payment_profile.asp"
    display_name = "Beanstream"

    # A list of all the valid parameters, and which ones are required.
    params = [
        ("requestType", True), # BACKEND Enter requestType=BACKEND for the recommended server to server integration method. Note that server to server typically cannot be used when hosting forms in the Beanstream Secure Webspace.
        ("merchant_id", True), # 9-digits Beanstream assigns one merchant ID number for each processing currency. Include the 9-digit Beanstream ID number here. Additional accounts may also have been issued for special services. Complete one full integration for each of the merchant IDs issued.
        ("trnOrderNumber", False), # but Recommended 30 alphanumeric (a/n) characters Include a unique order reference number if desired. If no number is passed, Beanstream will place the default transaction identification number (trnId) in this field. Custom order numbers will be used in duplicate transaction error checking. Order numbers are also required for Server to Server transaction queries. Integrators that wish to use the query function should pass custom values.
        ("trnAmount", True), # In the format 0.00. Max 2 decimal places. Max 9 digits total. This is the total dollar value of the purchase. This should represent the total of all taxes, shipping charges and other product/service costs as applicable.

        ("errorPage", True), # URL (encoded). Max 128 a/n characters. Not for use with server to server integrations. If a standard transaction request contains errors in billing or credit card information, the customer's browser will be re-directed to this page. Error messages will prompt the user to correct their data.
        ("approvedPage", False), # URL (encoded). Unlimited a/n characters. Beanstream provides default approved or declined transaction pages. For a seamless transaction flow, design unique pages and specify the approved transaction redirection URL here.
        ("declinedPage", False), # URL (encoded). Unlimited a/n characters. Specify the URL for your custom declined transaction notification page here.

        ("trnCardOwner", True), #* Max 64 a/n characters This field must contain the full name of the card holder exactly as it appears on their credit card.
        ("trnCardNumber", True), # Max 20 digits Capture the customer's credit card number.
        ("trnExpMonth", True), # 2 digits (January = 01) The card expiry month with January as 01 and December as 12.
        ("trnExpYear", True), # 2 digits (2011=11) Card expiry years must be entered as a number less than 50. In combination, trnExpYear and trnExpMonth must reflect a date in the future.
        ("trnCardCvd", False), # 4 digits Amex, 3 digits all other cards. Include the three or four-digit CVD number from the back of the customer's credit card. This information may be made mandatory using the "Require CVD" option in the Beanstream Order Settings module.
        ("ordName", True), #* Max 64 a/n characters. Capture the first and last name of the customer placing the order. This may be different from trnCardOwner.
        ("ordEmailAddress", True), # Max 64 a/n characters in the format a@b.com. The email address specified here will be used for sending automated email receipts.
        ("ordPhoneNumber", True), #* Min 7 a/n characters Max 32 a/n characters Collect a customer phone number for order follow-up.
        ("ordAddress1", True), #* Max 64 a/n characters Collect a unique street address for billing purposes.
        ("ordAddress2", False), # Max 64 a/n characters An optional variable is available for longer addresses.
        ("ordCity", True), #* Max 32 a/n characters The customer's billing city.
        ("ordProvince", True), #* 2 characters Province and state ID codes in this variable must match one of the available province and state codes.
        ("ordPostalCode", True), #* 16 a/n characters Indicates the customer's postal code for billing purposes.
        ("ordCountry", True), #* 2 characters Country codes must match one of the available ISO country codes.

        ("termURL", True), # URL (encoded) Specify the URL where the bank response codes will be collected after enters their VBV or SecureCode pin on the banking portal.
        ("vbvEnabled", False), # 1 digit When VBV service has been activated, Beanstream will attempt VBV authentication on all transactions. Use this variable to override our default settings and process VBV on selected transactions only. Pass vbvEnabled=1 to enable VBV authentication with an order. Pass vbvEnabled=0 to bypass VBV authentication on specific orders.
        ("scEnabled", False), # 1 digit When SecureCode service has been activated, Beanstream will attempt SC authentication on all transactions. Use this variable to override our default settings and process SC on selected transactions only. Pass scEnabled=1 to enable SC authentication with an order. Pass scEnabled=0 to bypass SC authentication on specific orders.

        ("SecureXID", True), # 20 digits Include the 3D secure transaction identifier as issued by the bank following VBV or SecureCode authentication.
        ("SecureECI", True), # 1 digit Provide the ECI status. 5=transaction authenticated. 6= authentication attempted but not completed.
        ("SecireCAVV", True), # 40 a/n characters Include the cardholder authentication verification value as issued by the bank.
    ]

    def __init__(self, *args, **kwargs):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("beanstream"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        beanstream_settings = merchant_settings["beanstream"]

        self.supported_cardtypes = [Visa, MasterCard, AmericanExpress, Discover]

        hash_validation = False
        if kwargs.get("hash_algorithm", beanstream_settings.get("HASH_ALGORITHM", None)):
            hash_validation = True

        self.beangw = Beanstream(
            hash_validation=hash_validation,
            require_billing_address=kwargs.get("require_billing_address", False),
            require_cvd=kwargs.get("require_cvd", False))

        merchant_id = kwargs.pop("merchant_id", beanstream_settings["MERCHANT_ID"])
        login_company = kwargs.pop("login_company", beanstream_settings["LOGIN_COMPANY"])
        login_user = kwargs.pop("login_user", beanstream_settings["LOGIN_USER"])
        login_password = kwargs.pop("login_password", beanstream_settings["LOGIN_PASSWORD"])
        kwargs["payment_profile_passcode"] = beanstream_settings.get("PAYMENT_PROFILE_PASSCODE", None)

        if hash_validation:
            if not kwargs.get("hash_algorithm"):
                kwargs["hash_algorithm"] = beanstream_settings["HASH_ALGORITHM"]
            if not kwargs.get("hashcode"):
                kwargs["hashcode"] = beanstream_settings["HASHCODE"]

        self.beangw.configure(
            merchant_id,
            login_company,
            login_user,
            login_password,
            **kwargs)

    def convert_cc(self, credit_card, validate=True):
        """Convert merchant.billing.utils.CreditCard to beanstream.billing.CreditCard"""
        card = CreditCard(
            credit_card.first_name + " " + credit_card.last_name,
            credit_card.number,
            credit_card.month, credit_card.year,
            credit_card.verification_value)
        if validate:
            self.validate_card(card)
        return card

    def _parse_resp(self, resp):
        status = "FAILURE"
        response = resp

        if resp.approved():
            status = "SUCCESS"

        return {"status": status, "response": response}

    def purchase(self, money, credit_card, options=None):
        """One go authorize and capture transaction"""
        options = options or {}
        txn = None
        order_number = options.get("order_number") if options else None

        if credit_card:
            card = self.convert_cc(credit_card)
            txn = self.beangw.purchase(money, card, None, order_number)
            billing_address = options.get("billing_address")
            if billing_address:
                txn.params.update({"ordName": billing_address["name"],
                                   "ordEmailAddress": billing_address["email"],
                                   "ordPhoneNumber": billing_address["phone"],
                                   "ordAddress1": billing_address["address1"],
                                   "ordAddress2": billing_address.get("address2", ""),
                                   "ordCity": billing_address["city"],
                                   "ordProvince": billing_address["state"],
                                   "ordCountry": billing_address["country"]})
        elif options.get("customer_code"):
            customer_code = options.get("customer_code", None)
            txn = self.beangw.purchase_with_payment_profile(money, customer_code, order_number)

        txn.validate()
        resp = self._parse_resp(txn.commit())
        if resp["status"] == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="purchase",
                                            response=resp["response"])
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=resp["response"])
        return resp

    def authorize(self, money, credit_card, options=None):
        """Authorization for a future capture transaction"""
        # TODO: Need to add check for trnAmount
        # For Beanstream Canada and TD Visa & MasterCard merchant accounts this value may be $0 or $1 or more.
        # For all other scenarios, this value must be $0.50 or greater.
        options = options or {}
        order_number = options.get("order_number") if options else None
        card = self.convert_cc(credit_card)
        txn = self.beangw.preauth(money, card, None, order_number)
        billing_address = options.get("billing_address")
        if billing_address:
            txn.params.update({"ordName": billing_address["name"],
                               "ordEmailAddress": billing_address["email"],
                               "ordPhoneNumber": billing_address["phone"],
                               "ordAddress1": billing_address["address1"],
                               "ordAddress2": billing_address.get("address2", ""),
                               "ordCity": billing_address["city"],
                               "ordProvince": billing_address["state"],
                               "ordCountry": billing_address["country"]})
        if options and "order_number" in options:
            txn.order_number = options.get("order_number");

        txn.validate()
        resp = self._parse_resp(txn.commit())
        if resp["status"] == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="authorize",
                                            response=resp["response"])
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="authorize",
                                              response=resp["response"])
        return resp

    def unauthorize(self, money, authorization, options=None):
        """Cancel a previously authorized transaction"""
        txn = Adjustment(self.beangw, Adjustment.PREAUTH_COMPLETION, authorization, money)

        resp = self._parse_resp(txn.commit())
        if resp["status"] == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="unauthorize",
                                            response=resp["response"])
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="unauthorize",
                                              response=resp["response"])
        return resp

    def capture(self, money, authorization, options=None):
        """Capture funds from a previously authorized transaction"""
        order_number = options.get("order_number") if options else None
        txn = self.beangw.preauth_completion(authorization, money, order_number)
        resp = self._parse_resp(txn.commit())
        if resp["status"] == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="capture",
                                            response=resp["response"])
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="capture",
                                              response=resp["response"])
        return resp

    def void(self, identification, options=None):
        """Null/Blank/Delete a previous transaction"""
        """Right now this only handles VOID_PURCHASE"""
        txn = self.beangw.void_purchase(identification["txnid"], identification["amount"])
        resp = self._parse_resp(txn.commit())
        if resp["status"] == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="void",
                                            response=resp["response"])
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="void",
                                              response=resp["response"])
        return resp

    def credit(self, money, identification, options=None):
        """Refund a previously 'settled' transaction"""
        order_number = options.get("order_number") if options else None
        txn = self.beangw.return_purchase(identification, money, order_number)
        resp = self._parse_resp(txn.commit())
        if resp["status"] == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="credit",
                                            response=resp["response"])
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="credit",
                                              response=resp["response"])
        return resp

    def recurring(self, money, creditcard, options=None):
        """Setup a recurring transaction"""
        card = self.convert_cc(creditcard)
        frequency_period = options['frequency_period']
        frequency_increment = options['frequency_increment']
        billing_address = options.get('billing_address', None) # must be a beanstream.billing.Address instance

        txn = self.beangw.create_recurring_billing_account(
            money, card, frequency_period, frequency_increment, billing_address)
        resp = self._parse_resp(txn.commit())
        if resp["status"] == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="recurring",
                                            response=resp["response"])
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=resp["response"])
        return resp

    def store(self, credit_card, options=None):
        """Store the credit card and user profile information
        on the gateway for future use"""
        card = self.convert_cc(credit_card)
        billing_address = options.get("billing_address")
        txn = self.beangw.create_payment_profile(card, billing_address)

        resp = txn.commit()

        status = "FAILURE"
        response = None
        if resp.approved() or resp.resp["responseCode"] == ["17"]:
            status = "SUCCESS"
        else:
            response = resp

        if status == "SUCCESS":
            transaction_was_successful.send(sender=self,
                                            type="recurring",
                                            response=response)
        else:
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=response)
        return {"status": status, "response": response}

    def unstore(self, identification, options=None):
        """Delete the previously stored credit card and user
        profile information on the gateway"""
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = bitcoin_gateway
import bitcoinrpc

from decimal import Decimal

from billing import Gateway, GatewayNotConfigured
from billing.signals import transaction_was_unsuccessful, \
    transaction_was_successful
from billing.utils.credit_card import CreditCard
from django.conf import settings
from django.utils import simplejson as json


class BitcoinGateway(Gateway):
    display_name = "Bitcoin"
    homepage_url = "http://bitcoin.org/"

    def __init__(self):
        test_mode = getattr(settings, "MERCHANT_TEST_MODE", True)
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("bitcoin"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        bitcoin_settings = merchant_settings["bitcoin"]

        self.rpcuser = bitcoin_settings["RPCUSER"]
        self.rpcpassword = bitcoin_settings["RPCPASSWORD"]
        self.host = bitcoin_settings.get("HOST", "127.0.0.1")
        self.port = bitcoin_settings.get("PORT", "8332")
        self.account = bitcoin_settings["ACCOUNT"]
        self.minconf = bitcoin_settings.get("MINCONF", 1)

        self.connection = bitcoinrpc.connect_to_remote(
                self.rpcuser,
                self.rpcpassword,
                self.host,
                self.port
        )

    def get_new_address(self):
        return self.connection.getnewaddress(self.account)

    def get_transactions(self):
        return self.connection.listtransactions(self.account)

    def get_transactions_by_address(self, address):
        all_txns = self.get_transactions()
        return filter(lambda txn: txn.address == address, all_txns)

    def get_txns_sum(self, txns):
        return sum(txn.amount for txn in txns)

    def purchase(self, money, address, options = None):
        options = options or {}
        money = Decimal(str(money))
        txns = self.get_transactions_by_address(address)
        received = self.get_txns_sum(txns)
        response = [txn.__dict__ for txn in txns]
        if received == money:
            transaction_was_successful.send(sender=self,
                                            type="purchase",
                                            response=response)
            return {'status': 'SUCCESS', 'response': response}
        transaction_was_unsuccessful.send(sender=self,
                                          type="purchase",
                                          response=response)
        return {'status': 'FAILURE', 'response': response}

########NEW FILE########
__FILENAME__ = braintree_payments_gateway
from billing import Gateway, GatewayNotConfigured
from billing.gateway import InvalidData
from billing.signals import *
from billing.utils.credit_card import InvalidCard, Visa, MasterCard, \
    AmericanExpress, Discover, CreditCard
from django.conf import settings
import braintree


class BraintreePaymentsGateway(Gateway):
    supported_cardtypes = [Visa, MasterCard, AmericanExpress, Discover]
    supported_countries = ["US"]
    default_currency = "USD"
    homepage_url = "http://www.braintreepayments.com/"
    display_name = "Braintree Payments"

    def __init__(self):
        test_mode = getattr(settings, "MERCHANT_TEST_MODE", True)
        if test_mode:
            env = braintree.Environment.Sandbox
        else:
            env = braintree.Environment.Production
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("braintree_payments"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        braintree_settings = merchant_settings['braintree_payments']
        braintree.Configuration.configure(
            env,
            braintree_settings['MERCHANT_ACCOUNT_ID'],
            braintree_settings['PUBLIC_KEY'],
            braintree_settings['PRIVATE_KEY']
            )

    def _cc_expiration_date(self, credit_card):
        return "%s/%s" % (credit_card.month, credit_card.year)

    def _cc_cardholder_name(self, credit_card):
        return "%s %s" % (credit_card.first_name, credit_card.last_name)

    def _build_request_hash(self, options):
        request_hash = {
                "order_id": options.get("order_id", ""),
                }
        if options.get("customer"):
            name = options["customer"].get("name", "")
            try:
                first_name, last_name = name.split(" ", 1)
            except ValueError:
                first_name = name
                last_name = ""
            request_hash.update({
                "customer": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": options["customer"].get("company", ""),
                    "phone": options["customer"].get("phone", ""),
                    "fax": options["customer"].get("fax", ""),
                    "website": options["customer"].get("website", ""),
                    "email": options["customer"].get("email", options.get("email", ""))
                    }
                })
        if options.get("billing_address"):
            name = options["billing_address"].get("name", "")
            try:
                first_name, last_name = name.split(" ", 1)
            except ValueError:
                first_name = name
                last_name = ""
            request_hash.update({
                "billing": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": options["billing_address"].get("company", ""),
                    "street_address": options["billing_address"].get("address1", ""),
                    "extended_address": options["billing_address"].get("address2", ""),
                    "locality": options["billing_address"].get("city", ""),
                    "region": options["billing_address"].get("state", ""),
                    "postal_code": options["billing_address"].get("zip", ""),
                    "country_code_alpha2": options["billing_address"].get("country", "")
                    }
                })
        if options.get("shipping_address"):
            name = options["shipping_address"].get("name", "")
            try:
                first_name, last_name = name.split(" ", 1)
            except ValueError:
                first_name = name
                last_name = ""
            request_hash.update({
                "shipping": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": options["shipping_address"].get("company", ""),
                    "street_address": options["shipping_address"].get("address1", ""),
                    "extended_address": options["shipping_address"].get("address2", ""),
                    "locality": options["shipping_address"].get("city", ""),
                    "region": options["shipping_address"].get("state", ""),
                    "postal_code": options["shipping_address"].get("zip", ""),
                    "country_code_alpha2": options["shipping_address"].get("country", "")
                    }
                })
        return request_hash

    def purchase(self, money, credit_card, options=None):
        if not options:
            options = {}
        if isinstance(credit_card, CreditCard) and not self.validate_card(credit_card):
             raise InvalidCard("Invalid Card")

        request_hash = self._build_request_hash(options)
        request_hash["amount"] = money

        if options.get("merchant_account_id"):
            request_hash["merchant_account_id"] = options.get("merchant_account_id")

        if isinstance(credit_card, CreditCard):
            request_hash["credit_card"] = {
                "number": credit_card.number,
                "expiration_date": self._cc_expiration_date(credit_card),
                "cardholder_name": self._cc_cardholder_name(credit_card),
                "cvv": credit_card.verification_value,
            }
        else:
            request_hash["payment_method_token"] = credit_card

        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        request_hash = self._build_request_hash(options)
        request_hash["amount"] = money
        request_hash["credit_card"] = {
            "number": credit_card.number,
            "expiration_date": self._cc_expiration_date(credit_card),
            "cardholder_name": self._cc_cardholder_name(credit_card),
            "cvv": credit_card.verification_value,
            }
        braintree_options = options.get("options", {})
        braintree_options.update({"submit_for_settlement": True})
        request_hash.update({
                "options": braintree_options
                })
        response = braintree.Transaction.sale(request_hash)
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="purchase",
                                            response=response)
        else:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=response)
        return {"status": status, "response": response}

    def authorize(self, money, credit_card, options=None):
        if not options:
            options = {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        request_hash = self._build_request_hash(options)
        request_hash["amount"] = money
        request_hash["credit_card"] = {
            "number": credit_card.number,
            "expiration_date": self._cc_expiration_date(credit_card),
            "cardholder_name": self._cc_cardholder_name(credit_card),
            "cvv": credit_card.verification_value,
            }
        braintree_options = options.get("options", {})
        if braintree_options:
            request_hash.update({
                    "options": braintree_options
                    })
        response = braintree.Transaction.sale(request_hash)
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="authorize",
                                            response=response)
        else:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="authorize",
                                              response=response)
        return {"status": status, "response": response}

    def capture(self, money, authorization, options=None):
        response = braintree.Transaction.submit_for_settlement(authorization, money)
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="capture",
                                            response=response)
        else:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="capture",
                                              response=response)
        return {"status": status, "response": response}

    def void(self, identification, options=None):
        response = braintree.Transaction.void(identification)
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="void",
                                            response=response)
        else:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="void",
                                              response=response)
        return {"status": status, "response": response}

    def credit(self, money, identification, options=None):
        response = braintree.Transaction.refund(identification, money)
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="credit",
                                            response=response)
        else:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="credit",
                                              response=response)
        return {"status": status, "response": response}

    def recurring(self, money, credit_card, options=None):
        resp = self.store(credit_card, options=options)
        if resp["status"] == "FAILURE":
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=resp)
            return resp
        payment_token = resp["response"].customer.credit_cards[0].token
        request_hash = options["recurring"]
        request_hash.update({
            "payment_method_token": payment_token,
            })
        response = braintree.Subscription.create(request_hash)
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="recurring",
                                            response=response)
        else:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=response)
        return {"status": status, "response": response}

    def store(self, credit_card, options=None):
        if not options:
            options = {}

        customer = options.get("customer", None)
        if not customer:
            raise InvalidData("Customer information needs to be passed.")

        try:
            first_name, last_name = customer["name"].split(" ", 1)
        except ValueError:
            first_name = customer["name"]
            last_name = ""

        search_resp = braintree.Customer.search(
            braintree.CustomerSearch.cardholder_name == credit_card.name,
            braintree.CustomerSearch.credit_card_number.starts_with(credit_card.number[:6]),
            braintree.CustomerSearch.credit_card_number.ends_with(credit_card.number[-4:]),
            braintree.CustomerSearch.credit_card_expiration_date == self._cc_expiration_date(credit_card)
            )

        customer_list = []
        for customer in search_resp.items:
            customer_list.append(customer)

        if len(customer_list) >= 1:
            # Take the first customer
            customer = customer_list[0]
        else:
            card_hash = {
                "number": credit_card.number,
                "expiration_date": self._cc_expiration_date(credit_card),
                "cardholder_name": self._cc_cardholder_name(credit_card),
                }

            if options.get("options"):
                card_hash["options"] = options["options"]

            request_hash = {
                "first_name": first_name,
                "last_name": last_name,
                "company": customer.get("company", ""),
                "email": customer.get("email", options.get("email", "")),
                "phone": customer.get("phone", ""),
                "credit_card": card_hash,
                }
            result = braintree.Customer.create(request_hash)
            if not result.is_success:
                transaction_was_unsuccessful.send(sender=self,
                                                  type="store",
                                                  response=result)
                return {"status": "FAILURE", "response": result}
            customer = result.customer

        request_hash = {}
        if options.get("billing_address"):
            name = options["billing_address"].get("name", "")
            try:
                first_name, last_name = name.split(" ", 1)
            except ValueError:
                first_name = name
                last_name = ""

            request_hash.update({
                "first_name": first_name,
                "last_name": last_name,
                "company":  options["billing_address"].get("company", ""),
                "street_address":  options["billing_address"].get("address1", ""),
                "extended_address":  options["billing_address"].get("address2", ""),
                "locality":  options["billing_address"].get("city", ""),
                "region":  options["billing_address"].get("state", ""),
                "postal_code":  options["billing_address"].get("zip", ""),
                "country_name":  options["billing_address"].get("country", "")
                })

        card_hash = {
            "number": credit_card.number,
            "expiration_date": self._cc_expiration_date(credit_card),
            "cardholder_name": self._cc_cardholder_name(credit_card),
            "options": {
                "update_existing_token": customer.credit_cards[0].token,
                }
            }
        if options.get("options"):
            card_hash["options"].update(options["options"])
        if request_hash:
            card_hash.update({"billing_address": request_hash})
        response = braintree.Customer.update(customer.id, {
                "credit_card": card_hash,
                })
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="store",
                                            response=response)
        else:
            for ii in response.errors.deep_errors:
                print ii.message
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="store",
                                              response=response)
        return {"status": status, "response": response}

    def unstore(self, identification, options=None):
        response = braintree.CreditCard.delete(identification)
        if response.is_success:
            status = "SUCCESS"
            transaction_was_successful.send(sender=self,
                                            type="unstore",
                                            response=response)
        else:
            status = "FAILURE"
            transaction_was_unsuccessful.send(sender=self,
                                              type="unstore",
                                              response=response)
        return {"status": status, "response": response}

########NEW FILE########
__FILENAME__ = chargebee_gateway
from billing import Gateway, GatewayNotConfigured
import requests
from requests.auth import HTTPBasicAuth
from billing.signals import transaction_was_unsuccessful, \
    transaction_was_successful
from billing.utils.credit_card import CreditCard
from django.conf import settings

class ChargebeeGateway(Gateway):
    display_name = "Chargebee"
    homepage_url = "https://chargebee.com/"

    def __init__(self):
        test_mode = getattr(settings, "MERCHANT_TEST_MODE", True)
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("chargebee"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        chargebee_settings = merchant_settings["chargebee"]
        self.chargebee_api_key = chargebee_settings["API_KEY"]
        chargebee_site = chargebee_settings["SITE"]
        self.chargebee_api_base_url = "https://%s.chargebee.com/api/v1" % chargebee_site

    def _chargebee_request(self, method, url, **kwargs):
        request_method = getattr(requests, method)
        uri = "%s%s" % (self.chargebee_api_base_url, url)
        if kwargs.pop("requires_auth", True) and not kwargs.get("auth"):
            kwargs["auth"] = HTTPBasicAuth(self.chargebee_api_key, '')
        return request_method(uri, **kwargs)

    def purchase(self, money, credit_card, options = None):
        """Create a plan that bills every decade or so 
        and charge the plan immediately"""
        options = options or {}
        resp = self.store(credit_card, options = options)
        subscription_id = resp["response"]["subscription"]["id"]
        resp = self._chargebee_request("post", "/invoices/charge", 
                                       data = {"subscription_id": subscription_id,
                                               "amount": money,
                                               "description": options.get("description")})
        if 200 <= resp.status_code < 300:
            transaction_was_successful.send(sender=self,
                                            type="purchase",
                                            response=resp.json())
            return {'status': 'SUCCESS', 'response': resp.json()}
        transaction_was_unsuccessful.send(sender=self,
                                          type="purchase",
                                          response=resp.json())
        return {'status': 'FAILURE', 'response': resp.json()}
            

    def authorize(self, money, credit_card, options = None):
        """This is a mirror to the store method. Create a plan 
        that bills every decade or so for a large authorized
        amount and charge that plan with the capture method"""
        return self.store(credit_card, options = options)

    def capture(self, money, authorization, options = None):
        options = options or {}
        resp = self._chargebee_request("post", "/invoices/charge",
                                       data = {"subscription_id": authorization,
                                               "amount": money,
                                               "description": options.get("description")})
        if 200 <= resp.status_code < 300:
            transaction_was_successful.send(sender=self,
                                            type="capture",
                                            response=resp.json())
            return {'status': 'SUCCESS', 'response': resp.json()}
        transaction_was_unsuccessful.send(sender=self,
                                          type="capture",
                                          response=resp.json())
        return {'status': 'FAILURE', 'response': resp.json()}

    def void(self, identification, options = None):
        return self.unstore(identification, options = options)

    def recurring(self, money, credit_card, options = None):
        return self.store(credit_card, options = options)

    def store(self, credit_card, options = None):
        options = options or {}
        if isinstance(credit_card, CreditCard):
            options.update({"card[first_name]": credit_card.first_name,
                            "card[last_name]": credit_card.last_name,
                            "card[number]": credit_card.number,
                            "card[expiry_year]": credit_card.year,
                            "card[expiry_month]": credit_card.month,
                            "card[cvv]": credit_card.verification_value})
        resp = self._chargebee_request('post', "/subscriptions", data = options)
        if 200 <= resp.status_code < 300:
            transaction_was_successful.send(sender=self,
                                            type="store",
                                            response=resp.json())
            return {'status': 'SUCCESS', 'response': resp.json()}
        transaction_was_unsuccessful.send(sender=self,
                                          type="store",
                                          response=resp.json())
        return {'status': 'FAILURE', 'response': resp.json()}

    def unstore(self, identification, options = None):
        options = options or {}
        resp = self._chargebee_request('post',
                                       "/subscriptions/%s/cancel" % identification,
                                       data = options)
        if 200 <= resp.status_code < 300:
            transaction_was_successful.send(sender=self,
                                            type="void",
                                            response=resp.json())
            return {'status': 'SUCCESS', 'response': resp.json()}
        transaction_was_unsuccessful.send(sender=self,
                                          type="void",
                                          response=resp.json())
        return {'status': 'FAILURE', 'response': resp.json()}

########NEW FILE########
__FILENAME__ = client
import requests
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, tostring
from suds.client import Client, WebFault

from billing.utils.xml_parser import nodeToDic


# Token Payments urls( Web Service ) : http://www.eway.com.au/developers/api/token
HOSTED_TEST_URL = "https://www.eway.com.au/gateway/ManagedPaymentService/test/managedCreditCardPayment.asmx?WSDL"
HOSTED_LIVE_URL = "https://www.eway.com.au/gateway/ManagedPaymentService/managedCreditCardPayment.asmx?WSDL"

# Recurring Payments urls( Web Service ) : http://www.eway.com.au/developers/api/recurring
REBILL_TEST_URL = "https://www.eway.com.au/gateway/rebill/test/manageRebill_test.asmx?WSDL"
REBILL_LIVE_URL = "https://www.eway.com.au/gateway/rebill/manageRebill.asmx?WSDL"

# Direct Payments urls( XML Based ) : http://www.eway.com.au/developers/api/token
DIRECT_PAYMENT_TEST_URL = "https://www.eway.com.au/gateway_cvn/xmltest/testpage.asp"
DIRECT_PAYMENT_LIVE_URL = "https://www.eway.com.au/gateway_cvn/xmlpayment.asp"


class DirectPaymentClient(object):
    """
        Wrapper for eway payment gateway's Direct Payment:
            eWay Link: http://www.eway.com.au/developers/api/direct-payments

    """
    def __init__(self, gateway_url=None):
        self.gateway_url = gateway_url

    def process_direct_payment(self, direct_payment_details=None, **kwargs):
        """
            Eway Direct Payment API Url : http://www.eway.com.au/developers/api/direct-payments#tab-1
            Input and Output format: https://gist.github.com/2552fcaa2799045a7884
        """
        if direct_payment_details:
            # Create XML to send
            payment_xml_root = Element("ewaygateway")
            for each_field in direct_payment_details:
                field = Element(each_field)
                field.text = str(direct_payment_details.get(each_field))
                payment_xml_root.append(field)
            # pretty string
            payment_xml_string = tostring(payment_xml_root)
            response = requests.post(self.gateway_url, data=payment_xml_string)
            response_xml = parseString(response.text)
            response_dict = nodeToDic(response_xml)

            return response_dict
        else:
            return self.process_direct_payment(**kwargs)


class RebillEwayClient(object):
    """
        Wrapper for eway payment gateway's managed and rebill webservices

        To create a empty object from the webservice types, call self.client.factory.create('type_name')

        Useful types are
            CustomerDetails: rebill customer
            RebillEventDetails: rebill event
            CreditCard: hosted customer
    """

    def __init__(self, customer_id=None, username=None, password=None, url=None):
        self.gateway_url = url
        self.customer_id = customer_id
        self.username = username
        self.password = password
        self.client = Client(self.gateway_url)
        self.set_eway_header()

    def set_eway_header(self):
        """
            creates eway header containing login credentials

            required for all api calls
        """
        eway_header = self.client.factory.create("eWAYHeader")
        eway_header.eWAYCustomerID = self.customer_id
        eway_header.Username = self.username
        eway_header.Password = self.password
        self.client.set_options(soapheaders=eway_header)

    def create_rebill_customer(self, rebill_customer=None, **kwargs):
        """
            eWay Urls : http://www.eway.com.au/developers/api/recurring
            Doc       : http://www.eway.com.au/docs/api-documentation/rebill-web-service.pdf?sfvrsn=2

            creates rebill customer with CustomerDetails type from the webservice

            also accepts keyword arguments if CustomerDetails object is not passed
            return CustomerDetails.RebillCustomerID and CustomerDetails.Result if successful
        """
        if rebill_customer:
            response = self.client.service.CreateRebillCustomer(
                rebill_customer.CustomerTitle,
                rebill_customer.CustomerFirstName,
                rebill_customer.CustomerLastName,
                rebill_customer.CustomerAddress,
                rebill_customer.CustomerSuburb,
                rebill_customer.CustomerState,
                rebill_customer.CustomerCompany,
                rebill_customer.CustomerPostCode,
                rebill_customer.CustomerCountry,
                rebill_customer.CustomerEmail,
                rebill_customer.CustomerFax,
                rebill_customer.CustomerPhone1,
                rebill_customer.CustomerPhone2,
                rebill_customer.CustomerRef,
                rebill_customer.CustomerJobDesc,
                rebill_customer.CustomerComments,
                rebill_customer.CustomerURL,
            )
            return response
        else:
            return self.client.service.CreateRebillCustomer(**kwargs)

    def update_rebill_customer(self, **kwargs):
        """
            same as create, takes CustomerDetails.RebillCustomerID
        """
        return self.client.service.UpdateRebillCustomer(**kwargs)

    def delete_rebill_customer(self, rebill_customer_id):
        """
            deletes a rebill customer based on id
        """
        return self.client.service.DeleteRebillCustomer(rebill_customer_id)

    def create_rebill_event(self, rebill_event=None, **kwargs):
        """
            eWay Urls : http://www.eway.com.au/developers/api/recurring
            Doc       : http://www.eway.com.au/docs/api-documentation/rebill-web-service.pdf?sfvrsn=2

            creates a rebill event based on RebillEventDetails object
            returns RebillEventDetails.RebillCustomerID and RebillEventDetails.RebillID if successful
        """
        if rebill_event:
            return self.client.service.CreateRebillEvent(
                rebill_event.RebillCustomerID,
                rebill_event.RebillInvRef,
                rebill_event.RebillInvDesc,
                rebill_event.RebillCCName,
                rebill_event.RebillCCNumber,
                rebill_event.RebillCCExpMonth,
                rebill_event.RebillCCExpYear,
                rebill_event.RebillInitAmt,
                rebill_event.RebillInitDate,
                rebill_event.RebillRecurAmt,
                rebill_event.RebillStartDate,
                rebill_event.RebillInterval,
                rebill_event.RebillIntervalType,
                rebill_event.RebillEndDate,
            )
        else:
            return self.client.service.CreateRebillEvent(**kwargs)

    def delete_rebill_event(self, rebill_customer_id=None, rebill_event_id=None, **kwargs):
        """
            eWay Urls : http://www.eway.com.au/developers/api/recurring
            Doc       : http://www.eway.com.au/docs/api-documentation/rebill-web-service.pdf?sfvrsn=2

            Deletes a rebill event based on RebillEventDetails object
            returns Result as Successful if successful
        """
        if rebill_customer_id and rebill_event_id:
            return self.client.service.DeleteRebillEvent(rebill_customer_id, rebill_event_id)
        else:
            return self.client.service.DeleteRebillEvent(**kwargs)

    def update_rebill_event(self, **kwargs):
        """
            same as create, takes RebillEventDetails.RebillCustomerID and RebillEventDetails.RebillID
        """
        return self.client.service.CreateRebillEvent(**kwargs)

    def query_next_transaction(self, RebillCustomerID, RebillID):
        return self.client.service.QueryNextTransaction(RebillCustomerID, RebillID)

    def query_rebill_customer(self, RebillCustomerID):
        return self.client.service.QueryRebillCustomer(RebillCustomerID)

    def query_rebill_event(self, RebillCustomerID, RebillID):
        return self.client.service.QueryRebillEvent(RebillCustomerID, RebillID)

    def query_transactions(self, RebillCustomerID, RebillID, startDate=None, endDate=None, status=None):
        try:
            return self.client.service.QueryTransactions(RebillCustomerID, RebillID, startDate, endDate, status)
        except WebFault as wf:
            return wf

    def create_hosted_customer(self, hosted_customer=None, **kwargs):
        """
            eWay Urls : http://www.eway.com.au/developers/api/token
            Doc       : http://www.eway.com.au/docs/api-documentation/token-payments-field-description.pdf?sfvrsn=2

            creates hosted customer based on CreditCard type details or kwargs

            returns id of newly created customer (112233445566 in test mode)
        """
        try:
            if hosted_customer:
                return self.client.service.CreateCustomer(
                    hosted_customer.Title,
                    hosted_customer.FirstName,
                    hosted_customer.LastName,
                    hosted_customer.Address,
                    hosted_customer.Suburb,
                    hosted_customer.State,
                    hosted_customer.Company,
                    hosted_customer.PostCode,
                    hosted_customer.Country,
                    hosted_customer.Email,
                    hosted_customer.Fax,
                    hosted_customer.Phone,
                    hosted_customer.Mobile,
                    hosted_customer.CustomerRef,
                    hosted_customer.JobDesc,
                    hosted_customer.Comments,
                    hosted_customer.URL,
                    hosted_customer.CCNumber,
                    hosted_customer.CCNameOnCard,
                    hosted_customer.CCExpiryMonth,
                    hosted_customer.CCExpiryYear,
                )
            else:
                return self.client.service.CreateCustomer(**kwargs)
        except WebFault as wf:
            print wf
            return wf

    def update_hosted_customer(self, **kwargs):
        """
            Update hosted customer based on kwargs

            returns True or False
        """
        try:
            return self.client.service.UpdateCustomer(**kwargs)
        except WebFault as wf:
            return wf

    def process_payment(self, managedCustomerID, amount, invoiceReference, invoiceDescription):
        """
            makes a transaction based on customer id and amount

            returns CCPaymentResponse type object with ewayTrxnStatus, ewayTrxnNumber, ewayAuthCode
        """
        try:
            return self.client.service.ProcessPayment(managedCustomerID, amount, invoiceReference, invoiceDescription)
        except WebFault as wf:
            return wf

    def query_customer(self, managedCustomerID):
        return self.client.service.QueryCustomer(managedCustomerID)

    def query_customer_by_reference(self, CustomerReference):
        """
            returns customer details based on reference

            not working with test data
        """
        return self.client.service.QueryCustomerByReference(CustomerReference)

    def query_payment(self, managedCustomerID):
        return self.client.service.QueryPayment(managedCustomerID)

########NEW FILE########
__FILENAME__ = tests
import unittest

from datetime import datetime, timedelta
from suds import WebFault

from client import RebillEwayClient, HOSTED_TEST_URL

# uncomment to enable debugging
#import logging
#logging.basicConfig(level=logging.DEBUG)
#logging.getLogger('suds.client').setLevel(logging.DEBUG)


class ClientTestCase(unittest.TestCase):
    def setUp(self):
        self.rebill_test = RebillEwayClient(test_mode=True, customer_id='87654321', username='test@eway.com.au', password='test123')
        self.rebill_customer = self.rebill_test.client.factory.create("CustomerDetails")
        self.rebill_event = self.rebill_test.client.factory.create("RebillEventDetails")
        self.hosted_test = RebillEwayClient(test_mode=True,
                                            customer_id='87654321',
                                            username='test@eway.com.au',
                                            password='test123',
                                            url=HOSTED_TEST_URL)
        self.hosted_customer = self.hosted_test.client.factory.create("CreditCard")

        self.rebill_init_date = datetime.today()
        self.rebill_start_date = datetime.today() + timedelta(days=1)
        self.rebill_end_date = datetime.today() + timedelta(days=31)

    def test_create_rebill_customer(self):
        self.rebill_customer.CustomerTitle = "Mr."
        self.rebill_customer.CustomerFirstName = "Joe"
        self.rebill_customer.CustomerLastName = "Bloggs"
        self.rebill_customer.CustomerAddress = "test street"
        self.rebill_customer.CustomerSuburb = "Sydney"
        self.rebill_customer.CustomerState = "NSW"
        self.rebill_customer.CustomerCompany = "Test Company"
        self.rebill_customer.CustomerPostCode = "2000"
        self.rebill_customer.CustomerCountry = "au"
        self.rebill_customer.CustomerEmail = "test@eway.com.au"
        self.rebill_customer.CustomerFax = "0267720000"
        self.rebill_customer.CustomerPhone1 = "0267720000"
        self.rebill_customer.CustomerPhone2 = "0404085992"
        self.rebill_customer.CustomerRef = "REF100"
        self.rebill_customer.CustomerJobDesc = "test"
        self.rebill_customer.CustomerComments = "Now!"
        self.rebill_customer.CustomerURL = "http://www.google.com.au"

        new_rebill_customer = self.rebill_test.create_rebill_customer(self.rebill_customer)
        print "create rebill customer", new_rebill_customer
        self.assertEqual(new_rebill_customer.Result, "Success")

    def test_create_rebill_customer_with_kwargs(self):
        new_rebill_customer_with_kwargs = self.rebill_test.create_rebill_customer(
                                                                           customerTitle="Mr.",
                                                                           customerFirstName="Joe",
                                                                           customerLastName="Bloggs",
                                                                           customerAddress="test street",
                                                                           customerSuburb="Sydney",
                                                                           customerState="NSW",
                                                                           customerCompany="Test Company",
                                                                           customerPostCode="2000",
                                                                           customerCountry="au",
                                                                           customerEmail="test@eway.com.au",
                                                                           customerFax="0267720000",
                                                                           customerPhone1="0267720000",
                                                                           customerPhone2="0404085992",
                                                                           customerRef="REF100",
                                                                           customerJobDesc="test",
                                                                           customerURL="http://www.google.com.au",
                                                                           customerComments="Now!",
                                                                           )
        print "create rebill customer with kwargs", new_rebill_customer_with_kwargs
        self.assertEqual(new_rebill_customer_with_kwargs.Result, "Success")

    def test_update_rebill_customer(self):
        updated_rebill_customer = self.rebill_test.update_rebill_customer(
                                                                               RebillCustomerID="17609",
                                                                               customerTitle="Mr.",
                                                                               customerFirstName="Joe",
                                                                               customerLastName="Bloggs",
                                                                               customerAddress="test street",
                                                                               customerSuburb="Sydney",
                                                                               customerState="NSW",
                                                                               customerCompany="Test Company",
                                                                               customerPostCode="2000",
                                                                               customerCountry="au",
                                                                               customerEmail="test@eway.com.au",
                                                                               customerFax="0267720000",
                                                                               customerPhone1="0267720000",
                                                                               customerPhone2="0404085992",
                                                                               customerRef="REF100",
                                                                               customerJobDesc="test",
                                                                               customerURL="http://www.google.com.au",
                                                                               customerComments="Now!",
                                                                               )
        print "update rebill customer", updated_rebill_customer
        self.assertEqual(updated_rebill_customer.Result, "Success")

    def test_delete_rebill_customer(self):
        deleted_rebill_customer = self.rebill_test.delete_rebill_customer("10292")
        print "delete rebill customer", deleted_rebill_customer
        self.assertEqual(deleted_rebill_customer.Result, "Success")

    def test_create_rebill_event(self):
        self.rebill_event.RebillCustomerID = "60001545"
        self.rebill_event.RebillID = ""
        self.rebill_event.RebillInvRef = "ref123"
        self.rebill_event.RebillInvDesc = "test event"
        self.rebill_event.RebillCCName = "test"
        self.rebill_event.RebillCCNumber = "4444333322221111"
        self.rebill_event.RebillCCExpMonth = "07"
        self.rebill_event.RebillCCExpYear = "20"
        self.rebill_event.RebillInitAmt = "100"
        self.rebill_event.RebillInitDate = self.rebill_init_date.strftime("%d/%m/%Y")
        self.rebill_event.RebillRecurAmt = "100"
        self.rebill_event.RebillStartDate = self.rebill_init_date.strftime("%d/%m/%Y")
        self.rebill_event.RebillInterval = "1"
        self.rebill_event.RebillIntervalType = "1"
        self.rebill_event.RebillEndDate = self.rebill_end_date.strftime("%d/%m/%Y")

        new_rebill_event = self.rebill_test.create_rebill_event(self.rebill_event)
        print "create rebill event", new_rebill_event
        self.assertEqual(new_rebill_event.Result, "Success")

    def test_create_rebill_event_with_kwargs(self):
        new_rebill_event_with_kwargs = self.rebill_test.create_rebill_event(
                                                                                 RebillCustomerID="60001545",
                                                                                 RebillInvRef="ref123",
                                                                                 RebillInvDes="test",
                                                                                 RebillCCName="test",
                                                                                 RebillCCNumber="4444333322221111",
                                                                                 RebillCCExpMonth="07",
                                                                                 RebillCCExpYear="20",
                                                                                 RebillInitAmt="100",
                                                                                 RebillInitDate=self.rebill_init_date.strftime("%d/%m/%Y"),
                                                                                 RebillRecurAmt="100",
                                                                                 RebillStartDate=self.rebill_start_date.strftime("%d/%m/%Y"),
                                                                                 RebillInterval="1",
                                                                                 RebillIntervalType="1",
                                                                                 RebillEndDate=self.rebill_end_date.strftime("%d/%m/%Y")
                                                                                 )
        print "create rebill event with kwargs", new_rebill_event_with_kwargs
        self.assertEqual(new_rebill_event_with_kwargs.Result, "Success")

    def test_update_rebill_event(self):
        updated_rebill_event = self.rebill_test.update_rebill_event(
                                                                         RebillCustomerID="60001545",
                                                                         RebillID="80001208",
                                                                         RebillInvRef="ref123",
                                                                         RebillInvDes="test",
                                                                         RebillCCName="test",
                                                                         RebillCCNumber="4444333322221111",
                                                                         RebillCCExpMonth="07",
                                                                         RebillCCExpYear="20",
                                                                         RebillInitAmt="100",
                                                                         RebillInitDate=self.rebill_init_date.strftime("%d/%m/%Y"),
                                                                         RebillRecurAmt="100",
                                                                         RebillStartDate=self.rebill_start_date.strftime("%d/%m/%Y"),
                                                                         RebillInterval="1",
                                                                         RebillIntervalType="1",
                                                                         RebillEndDate=self.rebill_end_date.strftime("%d/%m/%Y")
                                                                         )
        print "update rebill event", updated_rebill_event
        self.assertEqual(updated_rebill_event.Result, "Success")

    def test_delete_rebill_event(self):
        deleted_rebill_event = self.rebill_test.delete_rebill_event("10292", "80001208")
        print "delete rebill event", deleted_rebill_event
        self.assertEqual(deleted_rebill_event.Result, "Success")

    def test_query_next_transaction(self):
        query_next_transaction_result = self.rebill_test.query_next_transaction("60001545", "80001227")
        print "test_query_next_transaction", query_next_transaction_result
        self.assertFalse(query_next_transaction_result == None)

    def test_query_rebill_customer(self):
        query_rebill_customer_result = self.rebill_test.query_rebill_customer("60001545")
        print "test_query_rebill_customer", query_rebill_customer_result
        self.assertFalse(query_rebill_customer_result == None)

    def test_query_rebill_event(self):
        query_rebill_result = self.rebill_test.query_rebill_event("60001545", "80001227")
        print "test_query_rebill_event", query_rebill_result
        self.assertFalse(query_rebill_result == None)

    def test_query_transactions(self):
        query_transactions_result = self.rebill_test.query_transactions("60001545", "80001208")
        print "test_query_transactions", query_transactions_result
        self.assertFalse(query_transactions_result == None)

    def test_create_hosted_customer(self):
        self.hosted_customer.Title = "Mr."
        self.hosted_customer.FirstName = "Joe"
        self.hosted_customer.LastName = "Bloggs"
        self.hosted_customer.Address = "test street"
        self.hosted_customer.Suburb = "Sydney"
        self.hosted_customer.State = "NSW"
        self.hosted_customer.Company = "Test Company"
        self.hosted_customer.PostCode = "2000"
        self.hosted_customer.Country = "au"
        self.hosted_customer.Email = "test@eway.com.au"
        self.hosted_customer.Fax = "0267720000"
        self.hosted_customer.Phone = "0267720000"
        self.hosted_customer.Mobile = "0404085992"
        self.hosted_customer.CustomerRef = "REF100"
        self.hosted_customer.JobDesc = "test"
        self.hosted_customer.Comments = "Now!"
        self.hosted_customer.URL = "http://www.google.com.au"
        self.hosted_customer.CCNumber = "4444333322221111"
        self.hosted_customer.CCNameOnCard = "test"
        self.hosted_customer.CCExpiryMonth = "07"
        self.hosted_customer.CCExpiryYear = "12"

        new_hosted_customer_id = self.hosted_test.create_hosted_customer(self.hosted_customer)
        print "create new hosted customer", new_hosted_customer_id
        self.assertFalse(isinstance(new_hosted_customer_id, WebFault))

    def test_create_hosted_customer_with_kwargs(self):
        new_hosted_customer_id = self.hosted_test.create_hosted_customer(
                                                                          Title="Mr.",
                                                                          FirstName="Joe",
                                                                          LastName="Bloggs",
                                                                          Address="test street",
                                                                          Suburb="Sydney",
                                                                          State="NSW",
                                                                          Company="Test Company",
                                                                          PostCode="2000",
                                                                          Country="au",
                                                                          Email="test@eway.com.au",
                                                                          Fax="0267720000",
                                                                          Phone="0267720000",
                                                                          Mobile="0404085992",
                                                                          CustomerRef="REF100",
                                                                          JobDesc="test",
                                                                          Comments="Now!",
                                                                          URL="http://www.google.com.au",
                                                                          CCNumber="4444333322221111",
                                                                          CCNameOnCard="test",
                                                                          CCExpiryMonth="07",
                                                                          CCExpiryYear="12"
                                                                          )
        print "create new hosted customer with kwargs", new_hosted_customer_id
        self.assertFalse(isinstance(new_hosted_customer_id, WebFault))

    def test_update_hosted_customer(self):
        updated_hosted_customer = self.hosted_test.update_hosted_customer(
                                                                          managedCustomerID="9876543211000",
                                                                          Title="Mr.",
                                                                          FirstName="Joe",
                                                                          LastName="Bloggs",
                                                                          Address="test street",
                                                                          Suburb="Sydney",
                                                                          State="NSW",
                                                                          Company="Test Company",
                                                                          PostCode="2000",
                                                                          Country="au",
                                                                          Email="test@eway.com.au",
                                                                          Fax="0267720000",
                                                                          Phone="0267720000",
                                                                          Mobile="0404085992",
                                                                          CustomerRef="REF100",
                                                                          JobDesc="test",
                                                                          Comments="Now!",
                                                                          URL="http://www.google.com.au",
                                                                          CCNumber="4444333322221111",
                                                                          CCNameOnCard="test",
                                                                          CCExpiryMonth="07",
                                                                          CCExpiryYear="12"
                                                                          )
        print "update hosted customer", updated_hosted_customer
        self.assertTrue(updated_hosted_customer)

    def test_process_payment(self):
        payment_result = self.hosted_test.process_payment("9876543211000", "100", "test", "test")
        print "test_process_payment", payment_result
        self.assertFalse(isinstance(payment_result, WebFault))

    def test_query_customer(self):
        query_result = self.hosted_test.query_customer("9876543211000")
        print "test_query_customer", query_result
        self.assertFalse(query_result == None)

    def test_query_payment(self):
        query_payment_result = self.hosted_test.query_payment("9876543211000")
        print "test_query_payment", query_payment_result
        self.assertFalse(query_payment_result == None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = eway_gateway
from billing import CreditCard
from billing import Gateway, GatewayNotConfigured
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from billing.utils.credit_card import Visa, MasterCard, DinersClub, JCB, AmericanExpress, InvalidCard

from eway_api.client import RebillEwayClient, DirectPaymentClient
from eway_api.client import REBILL_TEST_URL, REBILL_LIVE_URL, HOSTED_TEST_URL, HOSTED_LIVE_URL, DIRECT_PAYMENT_TEST_URL, DIRECT_PAYMENT_LIVE_URL

from django.conf import settings


class EwayGateway(Gateway):
    default_currency = "AUD"
    supported_countries = ["AU"]
    supported_cardtypes = [Visa, MasterCard, AmericanExpress, DinersClub, JCB]
    homepage_url = "https://eway.com.au/"
    display_name = "eWay"

    def __init__(self):
        self.test_mode = getattr(settings, 'MERCHANT_TEST_MODE', True)
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("eway"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        eway_settings = merchant_settings["eway"]
        self.customer_id = eway_settings['CUSTOMER_ID']
        if self.test_mode:
            self.rebill_url = REBILL_TEST_URL
            self.hosted_url = HOSTED_TEST_URL
            self.direct_payment_url = DIRECT_PAYMENT_TEST_URL
        else:
            self.rebill_url = REBILL_LIVE_URL
            self.hosted_url = HOSTED_LIVE_URL
            self.direct_payment_url = DIRECT_PAYMENT_LIVE_URL

        self.eway_username = eway_settings['USERNAME']
        self.eway_password = eway_settings['PASSWORD']

    def add_creditcard(self, hosted_customer, credit_card):
        """
            add credit card details to the request parameters
        """
        hosted_customer.CCNumber = credit_card.number
        hosted_customer.CCNameOnCard = credit_card.name
        hosted_customer.CCExpiryMonth = '%02d' % (credit_card.month)
        hosted_customer.CCExpiryYear = str(credit_card.year)[-2:]
        hosted_customer.FirstName = credit_card.first_name
        hosted_customer.LastName = credit_card.last_name

    def add_address(self, hosted_customer, options=None):
        """
            add address details to the request parameters
        """
        if not options:
            options = {}
        address = options.get("billing_address", {})
        hosted_customer.Title = address.get("salutation", "Mr./Ms.")
        hosted_customer.Address = address.get("address1", '') + address.get("address2", "")
        hosted_customer.Suburb = address.get("city")
        hosted_customer.State = address.get("state")
        hosted_customer.Company = address.get("company")
        hosted_customer.PostCode = address.get("zip")
        hosted_customer.Country = address.get("country")
        hosted_customer.Email = address.get("email")
        hosted_customer.Fax = address.get("fax")
        hosted_customer.Phone = address.get("phone")
        hosted_customer.Mobile = address.get("mobile")
        hosted_customer.CustomerRef = address.get("customer_ref")
        hosted_customer.JobDesc = address.get("job_desc")
        hosted_customer.Comments = address.get("comments")
        hosted_customer.URL = address.get("url")

    def add_customer_details(self, credit_card, customer_detail, options=None):
        """
            add customer details to the request parameters
        """
        if not options:
            options = {}
        customer = options.get("customer_details", {})
        customer_detail.CustomerRef = customer.get("customer_ref")
        customer_detail.CustomerTitle = customer.get("customer_salutation", "")
        customer_detail.CustomerFirstName = credit_card.first_name
        customer_detail.CustomerLastName = credit_card.last_name
        customer_detail.CustomerCompany = customer.get("customer_company", "")
        customer_detail.CustomerJobDesc = customer.get("customer_job_desc", "")
        customer_detail.CustomerEmail = customer.get("customer_email")
        customer_detail.CustomerAddress = customer.get("customer_address1", "") + customer.get("customer_address2", "")
        customer_detail.CustomerSuburb = customer.get("customer_city", "")
        customer_detail.CustomerState = customer.get("customer_state", "")
        customer_detail.CustomerPostCode = customer.get("customer_zip", "")
        customer_detail.CustomerCountry = customer.get("customer_country", "")
        customer_detail.CustomerPhone1 = customer.get("customer_phone1", "")
        customer_detail.CustomerPhone2 = customer.get("customer_phone2", "")
        customer_detail.CustomerFax = customer.get("customer_fax", "")
        customer_detail.CustomerURL = customer.get("customer_url")
        customer_detail.CustomerComments = customer.get("customer_comments", "")

    def add_rebill_details(self, rebill_detail, rebile_customer_id, credit_card, rebill_profile):
        """
            add customer details to the request parameters
        """
        rebill_detail.RebillCustomerID = rebile_customer_id
        rebill_detail.RebillInvRef = rebill_profile.get("rebill_invRef")
        rebill_detail.RebillInvDesc = rebill_profile.get("rebill_invDesc")
        rebill_detail.RebillCCName = credit_card.name
        rebill_detail.RebillCCNumber = credit_card.number
        rebill_detail.RebillCCExpMonth = '%02d' % (credit_card.month)
        rebill_detail.RebillCCExpYear = str(credit_card.year)[-2:]
        rebill_detail.RebillInitAmt = rebill_profile.get("rebill_initAmt")
        rebill_detail.RebillInitDate = rebill_profile.get("rebill_initDate")
        rebill_detail.RebillRecurAmt = rebill_profile.get("rebill_recurAmt")
        rebill_detail.RebillStartDate = rebill_profile.get("rebill_startDate")
        rebill_detail.RebillInterval = rebill_profile.get("rebill_interval")
        rebill_detail.RebillIntervalType = rebill_profile.get("rebill_intervalType")
        rebill_detail.RebillEndDate = rebill_profile.get("rebill_endDate")

    def add_direct_payment_details(self, credit_card, customer_details, payment_details):
        direct_payment_details = {}
        direct_payment_details['ewayCustomerID'] = self.customer_id
        direct_payment_details['ewayCustomerFirstName'] = customer_details.get('customer_fname', '')
        direct_payment_details['ewayCustomerLastName'] = customer_details.get('customer_lname', '')
        direct_payment_details['ewayCustomerAddress'] = customer_details.get('customer_address', '')
        direct_payment_details['ewayCustomerEmail'] = customer_details.get('customer_email', '')
        direct_payment_details['ewayCustomerPostcode'] = customer_details.get('customer_postcode', None)
        direct_payment_details['ewayCardNumber'] = credit_card.number
        direct_payment_details['ewayCardHoldersName'] = credit_card.name
        direct_payment_details['ewayCardExpiryMonth'] = '%02d' % (credit_card.month)
        direct_payment_details['ewayCardExpiryYear'] = str(credit_card.year)[-2:]
        direct_payment_details['ewayCVN'] = credit_card.verification_value
        direct_payment_details['ewayOption1'] = '',
        direct_payment_details['ewayOption2'] = '',
        direct_payment_details['ewayOption3'] = '',
        direct_payment_details['ewayTrxnNumber'] = payment_details.get('transaction_number', '')
        direct_payment_details['ewayTotalAmount'] = payment_details['amount']
        direct_payment_details['ewayCustomerInvoiceRef'] = payment_details.get('inv_ref', '')
        direct_payment_details['ewayCustomerInvoiceDescription'] = payment_details.get('inv_desc', '')
        return direct_payment_details

    @property
    def service_url(self):
        if self.test_mode:
            return HOSTED_TEST_URL
        return HOSTED_LIVE_URL

    def purchase(self, money, credit_card, options=None):
        """
            Using Eway payment gateway , charge the given
            credit card for specified money
        """
        if not options:
            options = {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        client = RebillEwayClient(customer_id=self.customer_id,
                                  username=self.eway_username,
                                  password=self.eway_password,
                                  url=self.service_url,
                                  )
        hosted_customer = client.client.factory.create("CreditCard")

        self.add_creditcard(hosted_customer, credit_card)
        self.add_address(hosted_customer, options)
        customer_id = client.create_hosted_customer(hosted_customer)

        pymt_response = client.process_payment(
            customer_id,
            money,
            options.get("invoice", 'test'),
            options.get("description", 'test')
        )

        if not hasattr(pymt_response, "ewayTrxnStatus"):
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=pymt_response)
            return {"status": "FAILURE", "response": pymt_response}

        if pymt_response.ewayTrxnStatus == "False":
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=pymt_response)
            return {"status": "FAILURE", "response": pymt_response}

        transaction_was_successful.send(sender=self,
                                        type="purchase",
                                        response=pymt_response)
        return {"status": "SUCCESS", "response": pymt_response}

    def authorize(self, money, credit_card, options=None):
        raise NotImplementedError

    def capture(self, money, authorization, options=None):
        raise NotImplementedError

    def void(self, identification, options=None):
        raise NotImplementedError

    def credit(self, money, identification, options=None):
        raise NotImplementedError

    def direct_payment(self, credit_card_details, options=None):
        """
            Function that implement Direct Payment functionality provided by eWay.
                (Reference: http://www.eway.com.au/developers/api/direct-payments)

            Input Parameters:
                ( Please find the details here in this Gist: https://gist.github.com/08893221533daad49388 )
                credit_card   :    Customer Credit Card details
                options       :    Customer and Recurring Payment details

            Output Paramters:
                status: 'SUCCESS' or 'FAILURE'
                response : eWay Response in Dictionary format.
        """
        error_response = {}
        try:
            if (options and options.get('customer_details', False) and
                    options.get('payment_details', False)):
                customer_details = options.get('customer_details')
                payment_details = options.get('payment_details')
            else:
                error_response = {"reason": "Not enough information Available!"}
                raise

            """
                # Validate Entered credit card details.
            """
            credit_card = CreditCard(**credit_card_details)
            is_valid = self.validate_card(credit_card)
            if not is_valid:
                raise InvalidCard("Invalid Card")

            """
                # Create direct payment details
            """
            direct_payment_details = self.add_direct_payment_details(credit_card, customer_details, payment_details)

            """
                Process Direct Payment.
            """
            dpObj = DirectPaymentClient(self.direct_payment_url)
            response = dpObj.process_direct_payment(direct_payment_details)

            """
                Return value based on eWay Response
            """
            eway_response = response.get('ewayResponse', None)
            if eway_response and eway_response.get('ewayTrxnStatus', 'false').lower() == 'true':
                status = "SUCCESS"
            else:
                status = "FAILURE"

        except Exception as e:
            error_response['exception'] = e
            return {"status": "FAILURE", "response": error_response}

        return {"status": status, "response": response}

    def recurring(self, credit_card_details, options=None):
        """
            Recurring Payment Implementation using eWay recurring API (http://www.eway.com.au/developers/api/recurring)

            Input Parameters:
                ( Please find the details here in this Gist: https://gist.github.com/df67e02f7ffb39f415e6 )
                credit_card   :    Customer Credit Card details
                options       :    Customer and Recurring Payment details

            Output Dict:
                status: 'SUCCESS' or 'FAILURE'
                response : Response list of rebill event request in order of provided input
                           in options["customer_rebill_details"] list.
        """
        error_response = {}
        try:
            if not options:
                error_response = {"reason": "Not enough information Available!"}
                raise

            """
                # Validate Entered credit card details.
            """
            credit_card = CreditCard(**credit_card_details)
            if not self.validate_card(credit_card):
                raise InvalidCard("Invalid Card")

            rebillClient = RebillEwayClient(
                customer_id=self.customer_id,
                username=self.eway_username,
                password=self.eway_password,
                url=self.rebill_url,
            )
            # CustomerDetails : To create rebill Customer
            customer_detail = rebillClient.client.factory.create("CustomerDetails")
            self.add_customer_details(credit_card, customer_detail, options)
            """
                # Create Rebill customer and retrieve customer rebill ID.
            """
            rebill_customer_response = rebillClient.create_rebill_customer(customer_detail)

            # Handler error in create_rebill_customer response
            if rebill_customer_response.ErrorSeverity:
                transaction_was_unsuccessful.send(sender=self,
                                                  type="recurringCreateRebill",
                                                  response=rebill_customer_response)
                error_response = rebill_customer_response
                raise

            rebile_customer_id = rebill_customer_response.RebillCustomerID
            """
                For Each rebill profile
                # Create Rebill events using rebill customer ID and customer rebill details.
            """
            rebill_event_response_list = []
            for each_rebill_profile in options.get("customer_rebill_details", []):
                rebill_detail = rebillClient.client.factory.create("RebillEventDetails")
                self.add_rebill_details(rebill_detail, rebile_customer_id, credit_card, each_rebill_profile)

                rebill_event_response = rebillClient.create_rebill_event(rebill_detail)

                # Handler error in create_rebill_event response
                if rebill_event_response.ErrorSeverity:
                    transaction_was_unsuccessful.send(sender=self,
                                                      type="recurringRebillEvent",
                                                      response=rebill_event_response)
                    error_response = rebill_event_response
                    raise

                rebill_event_response_list.append(rebill_event_response)

            transaction_was_successful.send(sender=self,
                                            type="recurring",
                                            response=rebill_event_response_list)
        except Exception as e:
            error_response['exception'] = e
            return {"status": "Failure", "response": error_response}

        return {"status": "SUCCESS", "response": rebill_event_response_list}

    def recurring_cancel(self, rebill_customer_id, rebill_id):
        """
            Recurring Payment Cancelation (http://www.eway.com.au/developers/api/recurring)

            Input Parameters:
                - rebill_customer_id,
                - rebill_id  ( Output of recurring method)

            Output Dict:
                status : 'SUCCESS' or 'FAILURE'
                response : Rebill/Recurring Cancelation Response from eWay Web service.
        """
        rebillDeleteClient = RebillEwayClient(
            customer_id=self.customer_id,
            username=self.eway_username,
            password=self.eway_password,
            url=self.rebill_url,
        )

        """
            # Delete Rebill Event, using customer create rebill detail.
        """
        delete_rebill_response = rebillDeleteClient.delete_rebill_event(rebill_customer_id, rebill_id)

        # Handler error in delete_rebill_customer response
        if delete_rebill_response.ErrorSeverity:
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurringDeleteRebill",
                                              response=delete_rebill_response)
            return {"status": "FAILURE", "response": delete_rebill_response}

        transaction_was_successful.send(sender=self,
                                        type="recurring",
                                        response=delete_rebill_response)
        return {"status": "SUCCESS", "response": delete_rebill_response}

    def store(self, creditcard, options=None):
        raise NotImplementedError

    def unstore(self, identification, options=None):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = global_iris_gateway
from datetime import datetime
from decimal import Decimal
import sha
import string

from django.conf import settings
from django.template.loader import render_to_string
import lxml
import requests

from billing import Gateway
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from billing.utils.credit_card import Visa, MasterCard, AmericanExpress, InvalidCard


# See https://resourcecentre.globaliris.com/documents/pdf.html?id=43 for details

CARD_NAMES = {
    Visa: 'VISA',
    MasterCard: 'MC',
    AmericanExpress: 'AMEX',
    # Maestro and Switch are probably broken due to need for issue number to be passed.
    }


class Config(object):
    def __init__(self, config_dict):
        self.shared_secret = config_dict['SHARED_SECRET']
        self.merchant_id = config_dict['MERCHANT_ID']
        self.account = config_dict['ACCOUNT']


class GlobalIrisBase(object):

    default_currency = "GBP"
    supported_countries = ["GB"]
    supported_cardtypes = [Visa, MasterCard, AmericanExpress]
    homepage_url = "https://resourcecentre.globaliris.com/"

    def __init__(self, config=None, test_mode=None):
        if config is None:
            config = settings.MERCHANT_SETTINGS['global_iris']
        self.config = config

        if test_mode is None:
            test_mode = getattr(settings, 'MERCHANT_TEST_MODE', True)
        self.test_mode = test_mode

    def get_config(self, credit_card):
        setting_name_base = 'LIVE' if not self.test_mode else 'TEST'
        setting_names = ['%s_%s' % (setting_name_base, CARD_NAMES[credit_card.card_type]),
                         setting_name_base]

        for name in setting_names:
            try:
                config_dict = self.config[name]
            except KeyError:
                continue
            return Config(config_dict)

        raise KeyError("Couldn't find key %s in config %s" % (' or '.join(setting_names), self.config))

    def make_timestamp(self, dt):
        return dt.strftime('%Y%m%d%H%M%S')

    def standardize_data(self, data):
        config = self.get_config(data['card'])
        all_data = {
            'currency': self.default_currency,
            'merchant_id': config.merchant_id,
            'account': config.account,
            }

        all_data.update(data)
        if not 'timestamp' in all_data:
            all_data['timestamp'] = datetime.now()
        all_data['timestamp'] = self.make_timestamp(all_data['timestamp'])
        currency = all_data['currency']
        if currency in ['GBP', 'USD', 'EUR']:
            all_data['amount_normalized'] = int(all_data['amount'] * Decimal('100.00'))
        else:
            raise ValueError("Don't know how to normalise amounts in currency %s" % currency)
        card = all_data['card']
        card.month_normalized = "%02d" % int(card.month)
        year = int(card.year)
        card.year_normalized = "%02d" % (year if year < 100 else int(str(year)[-2:]))
        card.name_normalized = CARD_NAMES[card.card_type]

        def fix_address(address_dict):
            if 'post_code' in address_dict and 'street_address' in address_dict:
                address_dict['code'] = self.address_to_code(address_dict['street_address'],
                                                            address_dict['post_code'])

        if 'billing_address' in data:
            fix_address(data['billing_address'])
        if 'shipping_address' in data:
            fix_address(data['shipping_address'])

        all_data['sha1_hash'] = self.get_standard_signature(all_data, config)
        return all_data

    def address_to_code(self, street_address, post_code):
        """
        Returns a post 'code' in format required by RealAuth, from
        the street address and the post code.
        """
        # See https://resourcecentre.globaliris.com/documents/pdf.html?id=102, p27
        get_digits = lambda s: ''.join(c for c in s if c in string.digits)
        return "{0}|{1}".format(get_digits(post_code),
                                get_digits(street_address),
                                )

    def get_signature(self, data, config, signing_string):
        d = data.copy()
        d['merchant_id'] = config.merchant_id
        val1 = signing_string.format(**d)
        hash1 = sha.sha(val1).hexdigest()
        val2 = "{0}.{1}".format(hash1, config.shared_secret)
        hash2 = sha.sha(val2).hexdigest()
        return hash2

    def get_standard_signature(self, data, config):
        return self.get_signature(data, config, "{timestamp}.{merchant_id}.{order_id}.{amount_normalized}.{currency}.{card.number}")

    def do_request(self, xml):
        return requests.post(self.base_url, xml)


class GlobalIrisGateway(GlobalIrisBase, Gateway):

    display_name = "Global Iris"

    base_url = "https://remote.globaliris.com/RealAuth"

    def build_xml(self, data):
        all_data = self.standardize_data(data)
        return render_to_string("billing/global_iris_realauth_request.xml", all_data).encode('utf-8')

    def purchase(self, money, credit_card, options=None):
        if options is None or 'order_id' not in options:
            raise ValueError("Required parameter 'order_id' not found in options")

        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        data = {
            'amount': money,
            'card': credit_card,
            }
        data.update(options)
        xml = self.build_xml(data)
        return self.handle_response(self.do_request(xml), "purchase")

    def _failure(self, type, message, response, response_code=None):
        transaction_was_unsuccessful.send(self, type=type, response=response, response_code=response_code)
        retval = {"status": "FAILURE",
                  "message": message,
                  "response": response,
                  }
        if response_code is not None:
            retval['response_code'] = response_code
        return retval

    def _success(self, type, message, response, response_code=None, **kwargs):
        transaction_was_successful.send(self, type=type, response=response, response_code=response_code)
        retval = {"status": "SUCCESS",
                  "message": message,
                  "response": response,
                  "response_code": response_code,
                  }
        retval.update(kwargs)
        return retval

    def handle_response(self, response, type):
        if response.status_code != 200:
            return self._failure(type, response.reason, response)

        # Parse XML
        xml = lxml.etree.fromstring(response.content)
        response_code = xml.find('result').text
        message = xml.find('message').text
        if response_code == '00':
            kwargs = {}
            merge_xml_to_dict(xml, kwargs, ['avsaddressresponse', 'avspostcoderesponse', 'cvnresult'])
            cardissuer = xml.find('cardissuer')
            if cardissuer is not None:
                cardissuer_data = {}
                merge_xml_to_dict(cardissuer, cardissuer_data, ['bank', 'country', 'countrycode', 'region'])
                kwargs['cardissuer'] = cardissuer_data

            return self._success(type, message, response, response_code=response_code, **kwargs)

        else:
            return self._failure(type, message, response, response_code=response_code)


def merge_xml_to_dict(node, d, attrs):
    for n in attrs:
        elem = node.find(n)
        if elem is not None:
            d[n] = elem.text

########NEW FILE########
__FILENAME__ = paylane_gateway
# -*- coding: utf-8 -*-
# vim:tabstop=4:expandtab:sw=4:softtabstop=4

import datetime

from suds.client import Client
from suds.cache import ObjectCache
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from billing import Gateway, GatewayNotConfigured
from billing.models import PaylaneTransaction, PaylaneAuthorization
from billing.utils.credit_card import CreditCard, InvalidCard, Visa, MasterCard
from billing.utils.paylane import PaylaneError
from billing.signals import transaction_was_successful, transaction_was_unsuccessful


class PaylaneGateway(Gateway):
    """

    """
    default_currency = "EUR"
    supported_cardtypes = [Visa, MasterCard]
    supported_countries = ['PT']
    homepage_url = 'http://www.paylane.com/'
    display_name = 'Paylane'

    def __init__(self):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("paylane"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        paylane_settings = merchant_settings["paylane"]
        wsdl = paylane_settings.get('WSDL', 'https://direct.paylane.com/wsdl/production/Direct.wsdl')
        wsdl_cache = paylane_settings.get('SUDS_CACHE_DIR', '/tmp/suds')
        username = paylane_settings.get('USERNAME', '')
        password = paylane_settings.get('PASSWORD', '')

        self.client = Client(wsdl, username=username, password=password, cache=ObjectCache(location=wsdl_cache, days=15))

    def _validate(self, card):
        if not isinstance(card, CreditCard):
            raise InvalidCard('credit_card not an instance of CreditCard')

        if not self.validate_card(card):
            raise InvalidCard('Invalid Card')

        card.month = '%02d' % card.month

    def authorize(self, money, credit_card, options=None):
        """Authorization for a future capture transaction"""
        self._validate(credit_card)

        params = self.client.factory.create('ns0:multi_sale_params')
        params['payment_method'] = {}
        params['payment_method']['card_data'] = {}
        params['payment_method']['card_data']['card_number'] = credit_card.number
        params['payment_method']['card_data']['card_code'] = credit_card.verification_value
        params['payment_method']['card_data']['expiration_month'] = credit_card.month
        params['payment_method']['card_data']['expiration_year'] = credit_card.year
        params['payment_method']['card_data']['name_on_card'] = '%s %s' % (credit_card.first_name, credit_card.last_name)
        params['capture_later'] = True

        customer = options['customer']
        params['customer']['name'] = customer.name
        params['customer']['email'] = customer.email
        params['customer']['ip'] = customer.ip_address
        params['customer']['address']['street_house'] = customer.address.street_house
        params['customer']['address']['city'] = customer.address.city
        if customer.address.state:
            params['customer']['address']['state'] = customer.address.state
        params['customer']['address']['zip'] = customer.address.zip_code
        params['customer']['address']['country_code'] = customer.address.country_code

        params['amount'] = money
        params['currency_code'] = self.default_currency

        product = options['product']
        params['product'] = {}
        params['product']['description'] = product.description

        res = self.client.service.multiSale(params)

        transaction = PaylaneTransaction()
        transaction.amount = money
        transaction.customer_name = customer.name
        transaction.customer_email = customer.email
        transaction.product = product.description

        status = None
        response = None
        transaction.success = hasattr(res, 'OK')
        transaction.save()

        if hasattr(res, 'OK'):
            status = 'SUCCESS'
            authz = PaylaneAuthorization()
            authz.sale_authorization_id = res.OK.id_sale_authorization
            authz.transaction = transaction
            authz.first_authorization = True
            authz.save()

            response = {'transaction': transaction, 'authorization': authz}
            transaction_was_successful.send(sender=self, type='recurring', response=response)

        else:
            status = 'FAILURE'
            response = {'error': PaylaneError(getattr(res.ERROR, 'error_number'),
                                    getattr(res.ERROR, 'error_description'),
                                    getattr(res.ERROR, 'processor_error_number', ''),
                                    getattr(res.ERROR, 'processor_error_description', '')),
                        'transaction': transaction
                        }
            transaction_was_unsuccessful.send(sender=self, type='recurring', response=response)

        return {'status': status, 'response': response}

    def capture(self, money, authorization, options=None):
        """Capture all funds from a previously authorized transaction"""
        product = options['product']
        res = self.client.service.captureSale(id_sale_authorization=authorization.sale_authorization_id,
                    amount=money,
                    description=product)

        previous_transaction = authorization.transaction

        transaction = PaylaneTransaction()
        transaction.amount = previous_transaction.amount
        transaction.customer_name = previous_transaction.customer_name
        transaction.customer_email = previous_transaction.customer_email
        transaction.product = previous_transaction.product

        status = None
        response = None
        transaction.success = hasattr(res, 'OK')
        transaction.save()
        if hasattr(res, 'OK'):
            status = 'SUCCESS'
            authz = PaylaneAuthorization()
            authz.sale_authorization_id = authorization.sale_authorization_id
            authz.transaction = transaction
            authz.save()
            response = {'transaction': transaction, 'authorization': authz}
            transaction_was_successful.send(sender=self, type='bill_recurring', response=response)
        else:
            status = 'FAILURE'
            response = {'error': PaylaneError(getattr(res.ERROR, 'error_number'),
                                    getattr(res.ERROR, 'error_description'),
                                    getattr(res.ERROR, 'processor_error_number', ''),
                                    getattr(res.ERROR, 'processor_error_description', '')),
                        'transaction': transaction
                        }
            transaction_was_unsuccessful.send(sender=self, type='bill_recurring', response=response)

        return {'status': status, 'response': response}

    def purchase(self, money, credit_card, options=None):
        """One go authorize and capture transaction"""
        self._validate(credit_card)

        params = self.client.factory.create('ns0:multi_sale_params')
        params['payment_method'] = {}
        params['payment_method']['card_data'] = {}
        params['payment_method']['card_data']['card_number'] = credit_card.number
        params['payment_method']['card_data']['card_code'] = credit_card.verification_value
        params['payment_method']['card_data']['expiration_month'] = credit_card.month
        params['payment_method']['card_data']['expiration_year'] = credit_card.year
        params['payment_method']['card_data']['name_on_card'] = '%s %s' % (credit_card.first_name, credit_card.last_name)
        params['capture_later'] = False

        customer = options['customer']
        params['customer']['name'] = customer.name
        params['customer']['email'] = customer.email
        params['customer']['ip'] = customer.ip_address
        params['customer']['address']['street_house'] = customer.address.street_house
        params['customer']['address']['city'] = customer.address.city
        if customer.address.state:
            params['customer']['address']['state'] = customer.address.state
        params['customer']['address']['zip'] = customer.address.zip_code
        params['customer']['address']['country_code'] = customer.address.country_code

        params['amount'] = money
        params['currency_code'] = self.default_currency

        product = options['product']
        params['product'] = {}
        params['product']['description'] = product

        res = self.client.service.multiSale(params)

        transaction = PaylaneTransaction()
        transaction.amount = money
        transaction.customer_name = customer.name
        transaction.customer_email = customer.email
        transaction.product = product

        status = None
        response = None
        transaction.success = hasattr(res, 'OK')
        transaction.save()

        if hasattr(res, 'OK'):
            status = 'SUCCESS'
            response = {'transaction': transaction}
            transaction_was_successful.send(sender=self, type='purchase', response=response)
        else:
            status = 'FAILURE'
            response = {'error': PaylaneError(getattr(res.ERROR, 'error_number'),
                                    getattr(res.ERROR, 'error_description'),
                                    getattr(res.ERROR, 'processor_error_number', ''),
                                    getattr(res.ERROR, 'processor_error_description', '')),
                        'transaction': transaction
                        }
            transaction_was_unsuccessful.send(sender=self, type='purchase', response=response)

        return {'status': status, 'response': response}

    def recurring(self, money, credit_card, options=None):
        """Setup a recurring transaction"""
        return self.authorize(money, credit_card, options)

    def void(self, identification, options=None):
        """Null/Blank/Delete a previous transaction"""
        res = self.client.service.closeSaleAuthorization(id_sale_authorization=identification)
        if hasattr(res, 'OK'):
            return {'status': 'SUCCESS'}
        else:
            return {'status': 'FAILURE',
                    'response': {'error': PaylaneError(getattr(res.ERROR, 'error_number'),
                                            getattr(res.ERROR, 'error_description'),
                                            getattr(res.ERROR, 'processor_error_number', ''),
                                            getattr(res.ERROR, 'processor_error_description', '')),
                                }
                    }

    def bill_recurring(self, amount, authorization, description):
        """ Debit a recurring transaction payment, eg. monthly subscription.

            Use the result of recurring() as the paylane_recurring parameter.
            If this transaction is successful, use it's response as input for the
            next bill_recurring() call.
        """
        processing_date = datetime.datetime.today().strftime("%Y-%m-%d")
        res = self.client.service.resale(id_sale=authorization.sale_authorization_id, amount=amount, currency=self.default_currency,
                                        description=description, processing_date=processing_date, resale_by_authorization=authorization)

        previous_transaction = authorization.transaction

        transaction = PaylaneTransaction()
        transaction.amount = previous_transaction.amount
        transaction.customer_name = previous_transaction.customer_name
        transaction.customer_email = previous_transaction.customer_email
        transaction.product = previous_transaction.product

        status = None
        response = None
        transaction.success = hasattr(res, 'OK')
        transaction.save()
        if hasattr(res, 'OK'):
            status = 'SUCCESS'
            authz = PaylaneAuthorization()
            authz.sale_authorization_id = authorization.sale_authorization_id
            authz.transaction = transaction
            authz.save()
            response = {'transaction': transaction, 'authorization': authz}
            transaction_was_successful.send(sender=self, type='bill_recurring', response=response)
        else:
            status = 'FAILURE'
            response = {'error': PaylaneError(getattr(res.ERROR, 'error_number'),
                                    getattr(res.ERROR, 'error_description'),
                                    getattr(res.ERROR, 'processor_error_number', ''),
                                    getattr(res.ERROR, 'processor_error_description', '')),
                        'transaction': transaction
                        }
            transaction_was_unsuccessful.send(sender=self, type='bill_recurring', response=response)

        return {'status': status, 'response': response}

########NEW FILE########
__FILENAME__ = pay_pal_gateway
import datetime

from paypal.pro.helpers import PayPalWPP
from paypal.pro.exceptions import PayPalFailure

from django.conf import settings

from billing import Gateway
from billing.utils.credit_card import Visa, MasterCard, AmericanExpress, Discover
from billing.signals import *


class PayPalGateway(Gateway):
    default_currency = "USD"
    supported_countries = ["US"]
    supported_cardtypes = [Visa, MasterCard, AmericanExpress, Discover]
    homepage_url = "https://merchant.paypal.com/us/cgi-bin/?&cmd=_render-content&content_ID=merchant/wp_pro"
    display_name = "PayPal Website Payments Pro"

    def __init__(self):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("pay_pal"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        pay_pal_settings = merchant_settings["pay_pal"]

    @property
    def service_url(self):
        # Implemented in django-paypal
        raise NotImplementedError

    def purchase(self, money, credit_card, options=None):
        """Using PAYPAL DoDirectPayment, charge the given
        credit card for specified money"""
        if not options:
            options = {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        params = {}
        params['creditcardtype'] = credit_card.card_type.card_name
        params['acct'] = credit_card.number
        params['expdate'] = '%02d%04d' % (credit_card.month, credit_card.year)
        params['cvv2'] = credit_card.verification_value
        params['ipaddress'] = options['request'].META.get("REMOTE_ADDR", "")
        params['amt'] = money

        if options.get("email"):
            params['email'] = options["email"]

        address = options.get("billing_address", {})
        first_name = None
        last_name = None
        try:
            first_name, last_name = address.get("name", "").split(" ")
        except ValueError:
            pass
        params['firstname'] = first_name or credit_card.first_name
        params['lastname'] = last_name or credit_card.last_name
        params['street'] = address.get("address1", '')
        params['street2'] = address.get("address2", "")
        params['city'] = address.get("city", '')
        params['state'] = address.get("state", '')
        params['countrycode'] = address.get("country", '')
        params['zip'] = address.get("zip", '')
        params['phone'] = address.get("phone", "")

        shipping_address = options.get("shipping_address", None)
        if shipping_address:
            params['shiptoname'] = shipping_address["name"]
            params['shiptostreet'] = shipping_address["address1"]
            params['shiptostreet2'] = shipping_address.get("address2", "")
            params['shiptocity'] = shipping_address["city"]
            params['shiptostate'] = shipping_address["state"]
            params['shiptocountry'] = shipping_address["country"]
            params['shiptozip'] = shipping_address["zip"]
            params['shiptophonenum'] = shipping_address.get("phone", "")

        wpp = PayPalWPP(options['request'])
        try:
            response = wpp.doDirectPayment(params)
            transaction_was_successful.send(sender=self,
                                            type="purchase",
                                            response=response)
        except PayPalFailure, e:
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=e)
            # Slight skewness because of the way django-paypal
            # is implemented.
            return {"status": "FAILURE", "response": e}
        return {"status": response.ack.upper(), "response": response}

    def authorize(self, money, credit_card, options=None):
        if not options:
            options = {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")
        raise NotImplementedError

    def capture(self, money, authorization, options=None):
        raise NotImplementedError

    def void(self, identification, options=None):
        raise NotImplementedError

    def credit(self, money, identification, options=None):
        raise NotImplementedError

    def recurring(self, money, creditcard, options=None):
        if not options:
            options = {}
        params = {}
        params['profilestartdate'] = options.get('startdate') or datetime.datetime.now().strftime("%Y-%m-%dT00:00:00Z")
        params['startdate'] = options.get('startdate') or datetime.datetime.now().strftime("%m%Y")
        params['billingperiod'] = options.get('billingperiod') or 'Month'
        params['billingfrequency'] = options.get('billingfrequency') or '1'
        params['amt'] = money
        params['desc'] = 'description of the billing'

        params['creditcardtype'] = creditcard.card_type.card_name
        params['acct'] = creditcard.number
        params['expdate'] = '%02d%04d' % (creditcard.month, creditcard.year)
        params['firstname'] = creditcard.first_name
        params['lastname'] = creditcard.last_name

        wpp = PayPalWPP(options.get('request', {}))
        try:
            response = wpp.createRecurringPaymentsProfile(params, direct=True)
            transaction_was_successful.send(sender=self,
                                            type="purchase",
                                            response=response)
        except PayPalFailure, e:
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=e)
            # Slight skewness because of the way django-paypal
            # is implemented.
            return {"status": "FAILURE", "response": e}
        return {"status": response.ack.upper(), "response": response}

    def store(self, creditcard, options=None):
        raise NotImplementedError

    def unstore(self, identification, options=None):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = pin_gateway
try:
    import json
except ImportError:
    from django.utils import simplejson as json

import requests
from copy import copy
from django.conf import settings
from billing import CreditCard
from billing import Gateway, GatewayNotConfigured
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from billing.utils.credit_card import Visa, MasterCard, DinersClub, JCB, AmericanExpress, InvalidCard
from billing.models.pin_models import *

SSIG = {
    True:  ('SUCCESS', transaction_was_successful),
    False: ('FAILURE', transaction_was_unsuccessful),
}

class PinGateway(Gateway):
    default_currency = "AUD"
    supported_countries = ["AU"]
    supported_cardtypes = [Visa, MasterCard]
    homepage_url = "https://pin.net.au/"
    display_name = "Pin Payments"
    version = '1'
    endpoints = {
        'LIVE': 'api.pin.net.au',
        'TEST': 'test-api.pin.net.au',
    }

    def __init__(self):
        try:
            self.test_mode = settings.MERCHANT_TEST_MODE
            mode = 'TEST' if self.test_mode else 'LIVE'
            self.secret_key = settings.MERCHANT_SETTINGS["pin"]['SECRET']
            self.endpoint = self.endpoints[mode]
        except (AttributeError, KeyError):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)

    def _pin_request(self, method, url, data):
        request_method = getattr(requests, method)
        uri = "https://%s/%s%s" % (self.endpoint, self.version, url)
        auth = (self.secret_key, '')
        headers = {'content-type': 'application/json'}
        resp = request_method(uri, data=json.dumps(data), auth=auth, headers=headers)
        return resp.json()

    def _pin_response(self, resp, signal_type, obj=None):
        success = False
        if 'response' in resp:
            resp = resp['response']
            success = resp.get('success', False)
        status, signal = SSIG[success]
        signal.send(sender=self, type=signal_type, response=resp)
        return {'status': status, 'response': resp, 'obj': obj}

    def _pin_base(self, money, options):
        return {
            'amount': str(int(money*100)),
            'email': options.get('email', ''),
            'description': options.get('description', ''),
            'currency': options.get('currency', self.default_currency),
            'ip_address': options.get('ip', ''),
        }

    def _pin_card(self, credit_card, options=None):
        address = options['billing_address']
        return {
            "number": credit_card.number,
            "expiry_month": "%02d" % credit_card.month,
            "expiry_year": str(credit_card.year),
            "cvc": credit_card.verification_value,
            "name": '%s %s' % (credit_card.first_name, credit_card.last_name),
            "address_line1": address['address1'],
            "address_line2": address.get('address2', ''),
            "address_city": address['city'],
            "address_postcode": address['zip'],
            "address_state": address['state'],
            "address_country": address['country'],
        }

    def purchase(self, money, credit_card, options=None, commit=True):
        "Charge (without token)"
        data = self._pin_base(money, options)
        data['card'] = self._pin_card(credit_card, options)
        resp = self._pin_request('post', '/charges', data)
        charge = None
        if commit and 'response' in resp:
            response = copy(resp['response'])
            del response['card']['name']
            card = PinCard(**response['card'])
            card.first_name = credit_card.first_name
            card.last_name = credit_card.last_name
            card.save()
            charge = PinCharge(card=card)
            for key, value in response.items():
                if key != 'card':
                    setattr(charge, key, value)
            charge.save()
        return self._pin_response(resp, 'purchase', charge)

    def authorize(self, money, credit_card, options=None):
        "Card tokens"
        data = self._pin_card(credit_card, options)
        resp = self._pin_request('post', '/cards', data)
        # TODO: save model
        return self._pin_response(resp, 'authorize', obj=card)

    def capture(self, money, authorization, options=None):
        "Charge (with card/customer token)"
        # authorization is a card/customer token from authorize/store
        data = self._pin_base(money, options)
        if authorization.startswith('cus_'):
            data['customer_token'] = authorization
        elif authorization.startswith('card_'):
            data['card_token'] = authorization
        resp = self._pin_request('post', '/charges', data)
        # TODO: save model
        return self._pin_response(resp, 'capture')

    def void(self, identification, options=None):
        raise NotImplementedError

    def credit(self, money, identification, options=None):
        "Refunds"
        url = '/%s/refunds' % identification
        resp = self._pin_request('post', url, {})
        # TODO: save model
        return self._pin_response(resp, 'credit')

    def recurring(self, money, credit_card, options=None):
        raise NotImplementedError

    def store(self, credit_card, options=None):
        "Customers"
        data = {
            'email': options['email'],
            'card': self._pin_card(credit_card, options),
        }
        if "token" in options:
            url = '/%s/customers' % options['token']
        else:
            url = '/customers'
        resp = self._pin_request('post', url, data)
        # TODO: save model
        return self._pin_response(resp, 'store')

    def unstore(self, identification, options=None):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = stripe_gateway
from billing import Gateway, GatewayNotConfigured
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from billing.utils.credit_card import InvalidCard, Visa, MasterCard, \
     AmericanExpress, Discover, CreditCard
import stripe
from django.conf import settings


class StripeGateway(Gateway):
    supported_cardtypes = [Visa, MasterCard, AmericanExpress, Discover]
    supported_countries = ['US']
    default_currency = "USD"
    homepage_url = "https://stripe.com/"
    display_name = "Stripe"

    def __init__(self):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("stripe"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        stripe_settings = merchant_settings["stripe"]
        stripe.api_key = stripe_settings['API_KEY']
        self.stripe = stripe

    def purchase(self, amount, credit_card, options=None):
        card = credit_card
        if isinstance(credit_card, CreditCard):
            if not self.validate_card(credit_card):
                raise InvalidCard("Invalid Card")
            card = {
                'number': credit_card.number,
                'exp_month': credit_card.month,
                'exp_year': credit_card.year,
                'cvc': credit_card.verification_value
                }
        try:
            response = self.stripe.Charge.create(
                amount=int(amount * 100),
                currency=self.default_currency.lower(),
                card=card)
        except self.stripe.CardError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="purchase",
                                        response=response)
        return {'status': 'SUCCESS', 'response': response}

    def store(self, credit_card, options=None):
        card = credit_card
        if isinstance(credit_card, CreditCard):
            if not self.validate_card(credit_card):
                raise InvalidCard("Invalid Card")
            card = {
                'number': credit_card.number,
                'exp_month': credit_card.month,
                'exp_year': credit_card.year,
                'cvc': credit_card.verification_value
                }
        try:
            customer = self.stripe.Customer.create(card=card)
        except (self.stripe.CardError, self.stripe.InvalidRequestError), error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="store",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="store",
                                        response=customer)
        return {'status': 'SUCCESS', 'response': customer}

    def recurring(self, credit_card, options=None):
        card = credit_card
        if isinstance(credit_card, CreditCard):
            if not self.validate_card(credit_card):
                raise InvalidCard("Invalid Card")
            card = {
                'number': credit_card.number,
                'exp_month': credit_card.month,
                'exp_year': credit_card.year,
                'cvc': credit_card.verification_value
                }
        try:
            plan_id = options['plan_id']
            self.stripe.Plan.retrieve(options['plan_id'])
            try:
                response = self.stripe.Customer.create(
                    card=card,
                    plan=plan_id
                )
                transaction_was_successful.send(sender=self,
                                                type="recurring",
                                                response=response)
                return {"status": "SUCCESS", "response": response}
            except self.stripe.CardError, error:
                transaction_was_unsuccessful.send(sender=self,
                                                  type="recurring",
                                                  response=error)
                return {"status": "FAILURE", "response": error}
        except self.stripe.InvalidRequestError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=error)
            return {"status": "FAILURE", "response": error}
        except TypeError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=error)
            return {"status": "FAILURE", "response": "Missing Plan Id"}

    def unstore(self, identification, options=None):
        try:
            customer = self.stripe.Customer.retrieve(identification)
            response = customer.delete()
            transaction_was_successful.send(sender=self,
                                              type="unstore",
                                              response=response)
            return {"status": "SUCCESS", "response": response}
        except self.stripe.InvalidRequestError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="unstore",
                                              response=error)
            return {"status": "FAILURE", "response": error}

    def credit(self, identification, money=None, options=None):
        try:
            charge = self.stripe.Charge.retrieve(identification)
            response = charge.refund(amount=money)
            transaction_was_successful.send(sender=self,
                                            type="credit",
                                            response=response)
            return {"status": "SUCCESS", "response": response}
        except self.stripe.InvalidRequestError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="credit",
                                              response=error)
            return {"status": "FAILURE", "error": error}

    def authorize(self, money, credit_card, options=None):
        card = credit_card
        if isinstance(credit_card, CreditCard):
            if not self.validate_card(credit_card):
                raise InvalidCard("Invalid Card")
            card = {
                'number': credit_card.number,
                'exp_month': credit_card.month,
                'exp_year': credit_card.year,
                'cvc': credit_card.verification_value
                }
        try:
            token = self.stripe.Token.create(
                card=card,
                amount=int(money * 100),
            )
            transaction_was_successful.send(sender=self,
                                            type="authorize",
                                            response=token)
            return {'status': "SUCCESS", "response": token}
        except self.stripe.InvalidRequestError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="authorize",
                                              response=error)
            return {"status": "FAILURE", "response": error}

    def capture(self, money, authorization, options=None):
        try:
            response = self.stripe.Charge.create(
                amount=int(money * 100),
                card=authorization,
                currency=self.default_currency.lower()
            )
            transaction_was_successful.send(sender=self,
                                            type="capture",
                                            response=response)
            return {'status': "SUCCESS", "response": response}
        except self.stripe.InvalidRequestError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="capture",
                                              response=error)
            return {"status": "FAILURE", "response": error}

########NEW FILE########
__FILENAME__ = we_pay_gateway
from billing import Gateway, GatewayNotConfigured
from billing.utils.credit_card import InvalidCard, Visa, MasterCard, CreditCard
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from django.conf import settings
from wepay import WePay
from wepay.exceptions import WePayError


class WePayGateway(Gateway):
    display_name = "WePay"
    homepage_url = "https://www.wepay.com/"
    default_currency = "USD"
    supported_countries = ["US"]
    supported_cardtypes = [Visa, MasterCard]

    def __init__(self):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("we_pay"):
            raise GatewayNotConfigured("The '%s' gateway is not correctly "
                                       "configured." % self.display_name)
        super(WePayGateway, self).__init__()
        production = not self.test_mode
        self.we_pay = WePay(production)
        self.we_pay_settings = merchant_settings["we_pay"]

    def purchase(self, money, credit_card, options=None):
        options = options or {}
        params = {}
        params.update({
                'account_id': options.pop("account_id", self.we_pay_settings.get("ACCOUNT_ID", "")),
                'short_description': options.pop("description", ""),
                'amount': money,
                })
        if credit_card and not isinstance(credit_card, CreditCard):
            params["payment_method_id"] = credit_card
            params["payment_method_type"] = "credit_card"
        token = options.pop("access_token", self.we_pay_settings["ACCESS_TOKEN"])
        params.update(options)
        try:
            response = self.we_pay.call('/checkout/create', params, token=token)
        except WePayError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="purchase",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="purchase",
                                        response=response)
        return {'status': 'SUCCESS', 'response': response}

    def authorize(self, money, credit_card, options=None):
        options = options or {}
        resp = self.store(credit_card, options)
        if resp["status"] == "FAILURE":
            transaction_was_unsuccessful.send(sender=self,
                                              type="authorize",
                                              response=resp['response'])
            return resp
        token = options.pop("access_token", self.we_pay_settings["ACCESS_TOKEN"])
        try:
            resp = self.we_pay.call('/credit_card/authorize', {
                    'client_id': self.we_pay_settings["CLIENT_ID"],
                    'client_secret': self.we_pay_settings["CLIENT_SECRET"],
                    'credit_card_id': resp['response']['credit_card_id']
                    }, token=token)
        except WePayError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="authorize",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        params = {
            "auto_capture": False
            }
        params.update(options)
        response = self.purchase(money, resp["credit_card_id"], params)
        if response["status"] == "FAILURE":
            transaction_was_unsuccessful.send(sender=self,
                                              type="authorize",
                                              response=response["response"])
            return response
        transaction_was_successful.send(sender=self,
                                        type="authorize",
                                        response=response["response"])
        return response

    def capture(self, money, authorization, options=None):
        options = options or {}
        params = {
            'checkout_id': authorization,
            }
        token = options.pop("access_token", self.we_pay_settings["ACCESS_TOKEN"])
        try:
            response = self.we_pay.call('/checkout/capture', params, token=token)
        except WePayError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="capture",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="capture",
                                        response=response)
        return {'status': 'SUCCESS', 'response': response}

    def void(self, identification, options=None):
        options = options or {}
        params = {
            'checkout_id': identification,
            'cancel_reason': options.pop("description", "")
            }
        token = options.pop("access_token", self.we_pay_settings["ACCESS_TOKEN"])
        try:
            response = self.we_pay.call('/checkout/cancel', params, token=token)
        except WePayError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="void",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="void",
                                        response=response)
        return {'status': 'SUCCESS', 'response': response}

    def credit(self, money, identification, options=None):
        options = options or {}
        params = {
            'checkout_id': identification,
            'refund_reason': options.pop("description", ""),
            }
        if money:
            params.update({'amount': money})
        token = options.pop("access_token", self.we_pay_settings["ACCESS_TOKEN"])
        try:
            response = self.we_pay.call('/checkout/refund', params, token=token)
        except WePayError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="credit",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="credit",
                                        response=response)
        return {'status': 'SUCCESS', 'response': response}

    def recurring(self, money, credit_card, options=None):
        options = options or {}
        params = {
            'account_id': self.we_pay_settings.get("ACCOUNT_ID", ""),
            "short_description": options.pop("description", ""),
            "amount": money,
            }
        params.update(options)
        token = options.pop("access_token", self.we_pay_settings["ACCESS_TOKEN"])
        try:
            response = self.we_pay.call("/preapproval/create", params, token=token)
        except WePayError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="recurring",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="recurring",
                                        response=response)
        return {'status': 'SUCCESS', 'response': response}

    def store(self, credit_card, options=None):
        options = options or {}
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")
        token = options.pop("access_token", self.we_pay_settings["ACCESS_TOKEN"])
        try:
            response = self.we_pay.call('/credit_card/create', {
                    'client_id': self.we_pay_settings["CLIENT_ID"],
                    'user_name': credit_card.name,
                    'email': options.pop("customer")["email"],
                    'cc_number': credit_card.number,
                    'cvv': credit_card.verification_value,
                    'expiration_month': credit_card.month,
                    'expiration_year': credit_card.year,
                    'address': options.pop("billing_address")
                    }, token=token)
        except WePayError, error:
            transaction_was_unsuccessful.send(sender=self,
                                              type="store",
                                              response=error)
            return {'status': 'FAILURE', 'response': error}
        transaction_was_successful.send(sender=self,
                                        type="store",
                                        response=response)
        return {'status': 'SUCCESS', 'response': response}

########NEW FILE########
__FILENAME__ = integration
from django.utils.importlib import import_module
from django.conf import settings
from django.conf.urls import patterns


class IntegrationModuleNotFound(Exception):
    pass


class IntegrationNotConfigured(Exception):
    pass

integration_cache = {}


class Integration(object):
    """Base Integration class that needs to be subclassed by
    implementations"""
    # The mode of the gateway. Looks into the settings else
    # defaults to True
    test_mode = getattr(settings, "MERCHANT_TEST_MODE", True)

    # Name of the integration.
    display_name = 'Base Integration'

    # Template rendered by the templatetag 'billing'
    template = ''

    def __init__(self, options=None):
        if not options:
            options = {}
        # The form fields that will be rendered in the template
        self.fields = {}
        self.fields.update(options)

    def add_field(self, key, value):
        self.fields[key] = value

    def add_fields(self, params):
        for (key, val) in params.iteritems():
            self.add_field(key, val)

    @property
    def service_url(self):
        # Modified by subclasses
        raise NotImplementedError

    def get_urls(self):
        # Method must be subclassed
        urlpatterns = patterns('')
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls()


def get_integration(integration, *args, **kwargs):
    """Return a integration instance specified by `integration` name"""

    klass = integration_cache.get(integration, None)

    if not klass:
        integration_filename = "%s_integration" % integration
        integration_module = None
        for app in settings.INSTALLED_APPS:
            try:
                integration_module = import_module(".integrations.%s" % integration_filename, package=app)
                break
            except ImportError:
                pass
        if not integration_module:
            raise IntegrationModuleNotFound("Missing integration: %s" % (integration))
        integration_class_name = "".join(integration_filename.title().split("_"))
        try:
            klass = getattr(integration_module, integration_class_name)
        except AttributeError:
            raise IntegrationNotConfigured("Missing %s class in the integration module." % integration_class_name)
        integration_cache[integration] = klass
    return klass(*args, **kwargs)

########NEW FILE########
__FILENAME__ = amazon_fps_integration
from billing.integration import Integration, IntegrationNotConfigured
from django.conf import settings
from boto.fps.connection import FPSConnection
from django.conf.urls import patterns, url
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import (HttpResponseForbidden,
                         HttpResponseRedirect,
                         HttpResponse)
from billing.signals import (transaction_was_successful,
                             transaction_was_unsuccessful)
from django.core.urlresolvers import reverse
from billing.models import AmazonFPSResponse
import urlparse
import urllib
import time
import datetime

FPS_PROD_API_ENDPOINT = "fps.amazonaws.com"
FPS_SANDBOX_API_ENDPOINT = "fps.sandbox.amazonaws.com"

csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)


class AmazonFpsIntegration(Integration):
    """
    Fields required:
    transactionAmount: Amount to be charged/authorized
    paymentReason: Description of the transaction
    paymentPage: Page to direct the user on completion/failure of transaction
    """

    display_name = "Amazon Flexible Payment Service"
    template = "billing/amazon_fps.html"

    def __init__(self, options=None):
        if not options:
            options = {}
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("amazon_fps"):
            raise IntegrationNotConfigured("The '%s' integration is not correctly "
                                       "configured." % self.display_name)
        amazon_fps_settings = merchant_settings["amazon_fps"]
        self.aws_access_key = options.get("aws_access_key", None) or amazon_fps_settings['AWS_ACCESS_KEY']
        self.aws_secret_access_key = options.get("aws_secret_access_key", None) or amazon_fps_settings['AWS_SECRET_ACCESS_KEY']
        super(AmazonFpsIntegration, self).__init__(options=options)
        options.setdefault('host', self.service_url)
        self.fps_connection = FPSConnection(self.aws_access_key, self.aws_secret_access_key, **options)

    @property
    def service_url(self):
        if self.test_mode:
            return FPS_SANDBOX_API_ENDPOINT
        return FPS_PROD_API_ENDPOINT

    @property
    def link_url(self):
        tmp_fields = self.fields.copy()
        tmp_fields.pop("aws_access_key", None)
        tmp_fields.pop("aws_secret_access_key", None)
        tmp_fields.pop("paymentPage", None)
        return self.fps_connection.cbui_url(returnURL=tmp_fields.pop("returnURL"),
                                            paymentReason=tmp_fields.pop("paymentReason"),
                                            pipelineName=tmp_fields.pop("pipelineName"),
                                            transactionAmount=str(tmp_fields.pop("transactionAmount")),
                                            **tmp_fields)

    def purchase(self, amount, options=None):
        if not options:
            options = {}
        tmp_options = options.copy()
        permissible_options = ["SenderTokenId", "CallerReference",
            "SenderDescription", "CallerDescription", "TransactionTimeoutInMins"
            "TransactionAmount", "OverrideIPNURL", "DescriptorPolicy"]
        tmp_options['TransactionAmount'] = amount
        if 'tokenID' in options:
            tmp_options["SenderTokenId"] = options["tokenID"]
        if 'callerReference' in options:
            tmp_options['CallerReference'] = options["callerReference"]
        for key in options:
            if key not in permissible_options:
                tmp_options.pop(key)
        resp = self.fps_connection.pay(**tmp_options)
        return {"status": resp.PayResult.TransactionStatus, "response": resp.PayResult}

    def authorize(self, amount, options=None):
        """ 
        amount: the amount of money to authorize.
        options:
            Required:
                CallerReference
                SenderTokenId
                TransactionAmount

            Conditional:
                SenderDescription

            Optional:
                CallerDescription
                DescriptorPolicy
                OverrideIPNURL
                TransactionTimeoutInMins

            See: http://docs.aws.amazon.com/AmazonFPS/latest/FPSBasicGuide/Reserve.html
            for more info
        """
        if not options:
            options = {}
        options['TransactionAmount'] = amount
        resp = self.fps_connection.reserve(**options)
        return {"status": resp.ReserveResult.TransactionStatus, "response": resp.ReserveResult}

    def capture(self, amount, options=None):
        if not options:
            options = {}
        assert "ReserveTransactionId" in options, "Expecting 'ReserveTransactionId' in options"
        resp = self.fps_connection.settle(options["ReserveTransactionId"], amount)
        return {"status": resp.SettleResult.TransactionStatus, "response": resp.SettleResult}

    def credit(self, amount, options=None):
        if not options:
            options = {}
        assert "CallerReference" in options, "Expecting 'CallerReference' in options"
        assert "TransactionId" in options, "Expecting 'TransactionId' in options"
        resp = self.fps_connection.refund(options["CallerReference"],
                                          options["TransactionId"],
                                          refundAmount=amount,
                                          callerDescription=options.get("description", None))
        return {"status": resp.RefundResult.TransactionStatus, "response": resp.RefundResult}

    def void(self, identification, options=None):
        if not options:
            options = {}
        # Requires the TransactionID to be passed as 'identification'
        resp = self.fps_connection.cancel(identification,
                                          options.get("description", None))
        return {"status": resp.CancelResult.TransactionStatus, "response": resp.CancelResult}

    def get_urls(self):
        urlpatterns = patterns('',
           url(r'^fps-notify-handler/$', self.fps_ipn_handler, name="fps_ipn_handler"),
           url(r'^fps-return-url/$', self.fps_return_url, name="fps_return_url"),
                               )
        return urlpatterns

    @csrf_exempt_m
    @require_POST_m
    def fps_ipn_handler(self, request):
        uri = request.build_absolute_uri()
        parsed_url = urlparse.urlparse(uri)
        resp = self.fps_connection.verify_signature(UrlEndPoint="%s://%s%s" % (parsed_url.scheme,
                                                                  parsed_url.netloc,
                                                                  parsed_url.path),
                                                    HttpParameters=request.raw_post_data)
        if not resp.VerifySignatureResult.VerificationStatus == "Success":
            return HttpResponseForbidden()

        data = dict(map(lambda x: x.split("="), request.raw_post_data.split("&")))
        for (key, val) in data.iteritems():
            data[key] = urllib.unquote_plus(val)
        if AmazonFPSResponse.objects.filter(transactionId=data["transactionId"]).count():
            resp = AmazonFPSResponse.objects.get(transactionId=data["transactionId"])
        else:
            resp = AmazonFPSResponse()
        for (key, val) in data.iteritems():
            attr_exists = hasattr(resp, key)
            if attr_exists and not callable(getattr(resp, key, None)):
                if key == "transactionDate":
                    val = datetime.datetime(*time.localtime(float(val))[:6])
                setattr(resp, key, val)
        resp.save()
        if resp.statusCode == "Success":
            transaction_was_successful.send(sender=self.__class__,
                                            type=data["operation"],
                                            response=resp)
        else:
            if not "Pending" in resp.statusCode:
                transaction_was_unsuccessful.send(sender=self.__class__,
                                                  type=data["operation"],
                                                  response=resp)
        # Return a HttpResponse to prevent django from complaining
        return HttpResponse(resp.statusCode)

    def fps_return_url(self, request):
        uri = request.build_absolute_uri()
        parsed_url = urlparse.urlparse(uri)
        resp = self.fps_connection.verify_signature(UrlEndPoint="%s://%s%s" % (parsed_url.scheme,
                                                                  parsed_url.netloc,
                                                                  parsed_url.path),
                                                    HttpParameters=parsed_url.query)
        if not resp.VerifySignatureResult.VerificationStatus == "Success":
            return HttpResponseForbidden()

        return self.transaction(request)

    def transaction(self, request):
        """Has to be overridden by the subclasses"""
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = authorize_net_dpm_integration
from billing import Integration, IntegrationNotConfigured
from billing.forms.authorize_net_forms import AuthorizeNetDPMForm
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from django.conf import settings
from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.http import HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
import hashlib
import hmac
import urllib

csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)


class AuthorizeNetDpmIntegration(Integration):
    display_name = "Authorize.Net Direct Post Method"
    template = "billing/authorize_net_dpm.html"

    def __init__(self):
        super(AuthorizeNetDpmIntegration, self).__init__()
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("authorize_net"):
            raise IntegrationNotConfigured("The '%s' integration is not correctly "
                                           "configured." % self.display_name)
        self.authorize_net_settings = merchant_settings["authorize_net"]

    def form_class(self):
        return AuthorizeNetDPMForm

    def generate_form(self):
        transaction_key = self.authorize_net_settings["TRANSACTION_KEY"]
        login_id = self.authorize_net_settings["LOGIN_ID"]

        initial_data = self.fields
        x_fp_hash = hmac.new(transaction_key, "%s^%s^%s^%s^" % (login_id,
                                                               initial_data['x_fp_sequence'],
                                                               initial_data['x_fp_timestamp'],
                                                               initial_data['x_amount']),
                             hashlib.md5)
        initial_data.update({'x_login': login_id,
                             'x_fp_hash': x_fp_hash.hexdigest()})
        form = self.form_class()(initial=initial_data)
        return form

    @property
    def service_url(self):
        if self.test_mode:
            return "https://test.authorize.net/gateway/transact.dll"
        return "https://secure.authorize.net/gateway/transact.dll"

    def verify_response(self, request):
        data = request.POST.copy()
        md5_hash = self.authorize_net_settings["MD5_HASH"]
        login_id = self.authorize_net_settings["LOGIN_ID"]
        hash_str = "%s%s%s%s" % (md5_hash, login_id,
                                 data.get("x_trans_id", ""),
                                 data.get("x_amount", ""))
        return hashlib.md5(hash_str).hexdigest() == data.get("x_MD5_Hash").lower()

    @csrf_exempt_m
    @require_POST_m
    def authorizenet_notify_handler(self, request):
        response_from_authorize_net = self.verify_response(request)
        if not response_from_authorize_net:
            return HttpResponseForbidden()
        post_data = request.POST.copy()
        result = post_data["x_response_reason_text"]
        if request.POST['x_response_code'] == '1':
            transaction_was_successful.send(sender=self,
                                            type="sale",
                                            response=post_data)
            redirect_url = "%s?%s" % (request.build_absolute_uri(reverse("authorize_net_success_handler")),
                                     urllib.urlencode({"response": result,
                                                       "transaction_id": request.POST["x_trans_id"]}))
            return render_to_response("billing/authorize_net_relay_snippet.html",
                                      {"redirect_url": redirect_url})
        redirect_url = "%s?%s" % (request.build_absolute_uri(reverse("authorize_net_failure_handler")),
                                 urllib.urlencode({"response": result}))
        transaction_was_unsuccessful.send(sender=self,
                                          type="sale",
                                          response=post_data)
        return render_to_response("billing/authorize_net_relay_snippet.html",
                                  {"redirect_url": redirect_url})

    def authorize_net_success_handler(self, request):
        response = request.GET
        return render_to_response("billing/authorize_net_success.html",
                                  {"response": response},
                                  context_instance=RequestContext(request))

    def authorize_net_failure_handler(self, request):
        response = request.GET
        return render_to_response("billing/authorize_net_failure.html",
                                  {"response": response},
                                  context_instance=RequestContext(request))

    def get_urls(self):
        urlpatterns = patterns('',
           url('^authorize_net-notify-handler/$', self.authorizenet_notify_handler, name="authorize_net_notify_handler"),
           url('^authorize_net-sucess-handler/$', self.authorize_net_success_handler, name="authorize_net_success_handler"),
           url('^authorize_net-failure-handler/$', self.authorize_net_failure_handler, name="authorize_net_failure_handler"),)
        return urlpatterns

########NEW FILE########
__FILENAME__ = braintree_payments_integration
from billing import Integration, IntegrationNotConfigured
from django.conf import settings
from django.views.decorators.http import require_GET
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from django.conf.urls import patterns, url
import braintree
import urllib
from django.core.urlresolvers import reverse
from billing.forms.braintree_payments_forms import BraintreePaymentsForm
from django.shortcuts import render_to_response
from django.template import RequestContext


class BraintreePaymentsIntegration(Integration):
    display_name = "Braintree Transparent Redirect"
    template = "billing/braintree_payments.html"

    def __init__(self, options=None):
        if not options:
            options = {}
        super(BraintreePaymentsIntegration, self).__init__(options=options)

        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("braintree_payments"):
            raise IntegrationNotConfigured("The '%s' integration is not correctly "
                                       "configured." % self.display_name)
        braintree_payments_settings = merchant_settings["braintree_payments"]
        test_mode = getattr(settings, "MERCHANT_TEST_MODE", True)
        if test_mode:
            env = braintree.Environment.Sandbox
        else:
            env = braintree.Environment.Production
        braintree.Configuration.configure(
            env,
            braintree_payments_settings['MERCHANT_ACCOUNT_ID'],
            braintree_payments_settings['PUBLIC_KEY'],
            braintree_payments_settings['PRIVATE_KEY']
            )

    @property
    def service_url(self):
        return braintree.TransparentRedirect.url()

    def braintree_notify_handler(self, request):
        fpath = request.get_full_path()
        query_string = fpath.split("?", 1)[1]
        result = braintree.TransparentRedirect.confirm(query_string)
        if result.is_success:
            transaction_was_successful.send(sender=self,
                                            type="sale",
                                            response=result)
            return self.braintree_success_handler(request, result)
        transaction_was_unsuccessful.send(sender=self,
                                          type="sale",
                                          response=result)
        return self.braintree_failure_handler(request, result)

    def braintree_success_handler(self, request, response):
        return render_to_response("billing/braintree_success.html",
                                  {"response": response},
                                  context_instance=RequestContext(request))

    def braintree_failure_handler(self, request, response):
        return render_to_response("billing/braintree_failure.html",
                                  {"response": response},
                                  context_instance=RequestContext(request))

    def get_urls(self):
        urlpatterns = patterns('',
           url('^braintree-notify-handler/$', self.braintree_notify_handler, name="braintree_notify_handler"),)
        return urlpatterns

    def add_fields(self, params):
        for (key, val) in params.iteritems():
            if isinstance(val, dict):
                new_params = {}
                for k in val:
                    new_params["%s__%s" % (key, k)] = val[k]
                self.add_fields(new_params)
            else:
                self.add_field(key, val)

    def generate_tr_data(self):
        tr_data_dict = {"transaction": {}}
        tr_data_dict["transaction"]["type"] = self.fields["transaction__type"]
        tr_data_dict["transaction"]["order_id"] = self.fields["transaction__order_id"]
        if self.fields.get("transaction__customer_id"):
            tr_data_dict["transaction"]["customer_id"] = self.fields["transaction__customer__id"]
        if self.fields.get("transaction__customer__id"):
            tr_data_dict["transaction"]["customer"] = {"id": self.fields["transaction__customer__id"]}
        tr_data_dict["transaction"]["options"] = {"submit_for_settlement":
                                                  self.fields.get("transaction__options__submit_for_settlement", True)}
        if self.fields.get("transaction__payment_method_token"):
            tr_data_dict["transaction"]["payment_method_token"] = self.fields["transaction__payment_method_token"]
        if self.fields.get("transaction__credit_card__token"):
            tr_data_dict["transaction"]["credit_card"] = {"token": self.fields["transaction__credit_card__token"]}
        if self.fields.get("transaction__amount"):
            tr_data_dict["transaction"]["amount"] = self.fields["transaction__amount"]
        notification_url = "%s%s" % (self.fields["site"], reverse("braintree_notify_handler"))
        tr_data = braintree.Transaction.tr_data_for_sale(tr_data_dict, notification_url)
        return tr_data

    def form_class(self):
        return BraintreePaymentsForm

    def generate_form(self):
        initial_data = self.fields
        initial_data.update({"tr_data": self.generate_tr_data()})
        form = self.form_class()(initial=initial_data)
        return form

########NEW FILE########
__FILENAME__ = eway_au_integration
from billing import Integration, get_gateway, IntegrationNotConfigured
from billing.forms.eway_au_forms import EwayAuForm
from django.conf import settings
from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
import operator
from suds.client import Client


client = Client("https://au.ewaygateway.com/mh/soap.asmx?wsdl")
client.options.cache.setduration(days=7)


translation = {
    'SaveToken': 'save_token',
    'TokenCustomerID': 'token_customer_id',
    'Reference': 'reference',
    'Title': 'title',
    'FirstName': 'first_name',
    'LastName': 'last_name',
    'CompanyName': 'company',
    'JobDescription': 'job',
    'Street1': 'street',
    'City': 'city',
    'State': 'state',
    'PostalCode': 'postal_code',
    'Country': 'country',
    'Email': 'email',
    'Phone': 'phone',
    'Mobile': 'mobile',
    'Comments': 'comments',
    'Fax': 'fax',
    'Url': 'url',
    'CardNumber': 'card_number',
    'CardName': 'card_name',
    'CardExpiryMonth': 'card_expiry_month',
    'CardExpiryYear': 'card_expiry_year',
    'Option1': 'option_1',
    'Option2': 'option_2',
    'Option3': 'option_3',
    'BeagleScore': 'beagle_score',
    'ErrorMessage': 'error_message',
    'TransactionStatus': 'transaction_status',
    'TransactionID': 'transaction_id',
    'TotalAmount': 'total_amount',
    'InvoiceReference': 'invoice_reference',
    'InvoiceNumber': 'invoice_number',
    'ResponseCode': 'response_code',
    'ResponseMessage': 'response_message',
    'AuthorisationCode': 'authorisation_code',
    'AccessCode': 'access_code',
}
translation.update(dict(zip(translation.values(), translation.keys())))


def translate(original):
    """
    Translate between the eWAY SOAP naming convention (camel case), and
    Python's convention (lowercase separated with underscores).

    Takes and returns a dictionary.

    Untranslatable keys are not included in returned dict.
    """
    translated = {}
    for k, v in translation.items():
        try:
            value = original[k]
        except KeyError:
            continue
        translated[v] = value
    return translated


def attr_update(object_, dict_):
    for k, v in dict_.items():
        setattr(object_, k, v)


class EwayAuIntegration(Integration):
    display_name = "eWAY"
    service_url = "https://au.ewaygateway.com/mh/payment"
    template = "billing/eway.html"
    urls = ()

    def __init__(self, access_code=None):
        super(EwayAuIntegration, self).__init__()
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("eway"):
            raise IntegrationNotConfigured("The '%s' integration is not correctly "
                                           "configured." % self.display_name)
        eway_settings = merchant_settings["eway"]
        self.customer_id = eway_settings["CUSTOMER_ID"]
        self.username = eway_settings["USERNAME"]
        self.password = eway_settings["PASSWORD"]
        # Don't use X-Forwarded-For. It doesn't really matter if REMOTE_ADDR
        # isn't their *real* IP, we're only interested in what IP they're going
        # to use for their POST request to eWAY. If they're using a proxy to
        # connect to us, it's fair to assume they'll use the same proxy to
        # connect to eWAY.
        self.access_code = access_code

    def generate_form(self):
        initial_data = dict(EWAY_ACCESSCODE=self.access_code, **self.fields)
        return EwayAuForm(initial=initial_data)

    def request_access_code(self, payment, return_url, customer=None,
                            billing_country=None, ip_address=None):
        # enforce required fields
        assert self.customer_id
        assert self.username
        assert self.password
        assert payment['total_amount']
        assert return_url

        # Request a new access code.
        req = client.factory.create("CreateAccessCodeRequest")
        req.Authentication.CustomerID = self.customer_id
        req.Authentication.Username = self.username
        req.Authentication.Password = self.password
        attr_update(req.Payment, translate(payment))
        attr_update(req.Customer, translate(customer or {}))
        req.RedirectUrl = return_url
        if ip_address:
            req.IPAddress = ip_address
        if billing_country:
            req.BillingCountry = billing_country
        del req.ResponseMode

        # Handle the response
        response = client.service.CreateAccessCode(req)
        self.access_code = response.AccessCode

        # turn customer to dict
        customer_echo = dict(((k, getattr(response.Customer, k))
                              for k in dir(response.Customer)))
        return (self.access_code, translate(customer_echo))

    def check_transaction(self):
        if not self.access_code:
            raise ValueError("`access_code` must be specified")

        req = client.factory.create("GetAccessCodeResultRequest")
        req.Authentication.CustomerID = self.customer_id
        req.Authentication.Username = self.username
        req.Authentication.Password = self.password
        req.AccessCode = self.access_code

        response = client.service.GetAccessCodeResult(req)
        return translate(dict(((k, getattr(response, k)) for k in dir(response))))

########NEW FILE########
__FILENAME__ = global_iris_real_mpi_integration
import base64
import decimal
import json
import logging

from django.conf import settings
from django.core.signing import TimestampSigner
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
import lxml
import requests

from billing import Integration, get_gateway, IntegrationNotConfigured
from billing.gateways.global_iris_gateway import GlobalIrisBase
from billing.utils.credit_card import Visa, MasterCard, Maestro, CreditCard
from billing.utils.json import chain_custom_encoders, chain_custom_decoders
import billing.utils.credit_card

log = logging.getLogger(__name__)


def get_signer():
    return TimestampSigner(salt="billing.global_iris_real_mpi_integration")


class GlobalIrisRealMpiIntegration(GlobalIrisBase, Integration):
    display_name = "Global Iris RealMPI"

    base_url = "https://remote.globaliris.com/realmpi"

    def get_gateway(self):
        return get_gateway("global_iris")

    def __init__(self, config=None, test_mode=None):
        super(GlobalIrisRealMpiIntegration, self).__init__(config=config, test_mode=test_mode)
        self.gateway = self.get_gateway()

    def card_supported(self, card):
        return card.card_type in [Visa, MasterCard, Maestro]

    def send_3ds_verifyenrolled(self, data):
        return self.handle_3ds_verifyenrolled_response(self.do_request(self.build_3ds_verifyenrolled_xml(data)))

    def handle_3ds_verifyenrolled_response(self, response):
        if response.status_code != 200:
            return GlobalIris3dsError(response.reason, response)
        return GlobalIris3dsVerifyEnrolled(response.content)

    def build_3ds_verifyenrolled_xml(self, data):
        all_data = self.standardize_data(data)
        return render_to_string("billing/global_iris_real_mpi_3ds_verifyenrolled_request.xml", all_data).encode('utf-8')

    def encode_merchant_data(self, data_dict):
        # resourcecentre.globaliris.com talks about encrypting this data.
        # Encryption is not necessary here, since the data has been either
        # entered by the user, or relating to the users stuff, and we are sending
        # it only to services we trust (RealMPI and their bank). However, we do
        # need to ensure that there is no tampering (which encryption does not
        # guarantee), so we sign it.
        return base64.encodestring(get_signer().sign(json.dumps(data_dict,
                                                                default=json_encoder_func,
                                                                )))

    def decode_merchant_data(self, s):
        return json.loads(get_signer().unsign(base64.decodestring(s),
                                              max_age=10*60*60), # Shouldn't take more than 1 hour to fill in auth details!
                          object_hook=json_decoder_func)

    def redirect_to_acs_url(self, enrolled_response, term_url, merchant_data):
        return render_to_response("billing/global_iris_real_mpi_redirect_to_acs.html",
                                  {'enrolled_response': enrolled_response,
                                   'term_url': term_url,
                                   'merchant_data': self.encode_merchant_data(merchant_data),
                                   })

    def parse_3d_secure_request(self, request):
        """
        Extracts the PaRes and merchant data from the HTTP request that is sent
        to the website when the user returns from the 3D secure website.
        """
        return request.POST['PaRes'], self.decode_merchant_data(request.POST['MD'])

    def send_3ds_verifysig(self, pares, data):
        return self.handle_3ds_verifysig_response(self.do_request(self.build_3ds_verifysig_xml(pares, data)))

    def handle_3ds_verifysig_response(self, response):
        if response.status_code != 200:
            return GlobalIris3dsError(response.reason, response)
        return GlobalIris3dsVerifySig(response.content)

    def build_3ds_verifysig_xml(self, pares, data):
        all_data = self.standardize_data(data)
        all_data['pares'] = pares
        return render_to_string("billing/global_iris_real_mpi_3ds_verifysig_request.xml", all_data).encode('utf-8')


def encode_credit_card_as_json(obj):
    if isinstance(obj, CreditCard):
        card_type = getattr(obj, 'card_type', None)
        if card_type is not None:
            card_type = card_type.__name__

        return {'__credit_card__': True,
                'first_name': obj.first_name,
                'last_name': obj.last_name,
                'cardholders_name': obj.cardholders_name,
                'month': obj.month,
                'year': obj.year,
                'number': obj.number,
                'verification_value': obj.verification_value,
                'card_type': card_type,
                }
    raise TypeError("Unknown type %s" % obj.__class__)


def decode_credit_card_from_dict(dct):
    if '__credit_card__' in dct:
        d = dct.copy()
        d.pop('__credit_card__')
        d.pop('card_type')
        retval = CreditCard(**d)
        card_type = dct.get('card_type', None) # put there by Gateway.validate_card
        if card_type is not None:
            # Get the credit card class with this name
            retval.card_type = getattr(billing.utils.credit_card, card_type)
        return retval
    return dct


def encode_decimal_as_json(obj):
    if isinstance(obj, decimal.Decimal):
        return {'__decimal__': True,
                'value': str(obj),
                }
    return TypeError("Unknown type %s" % obj.__class__)


def decode_decimal_from_dict(dct):
    if '__decimal__' in dct:
        return decimal.Decimal(dct['value'])
    return dct


json_encoder_func = chain_custom_encoders([encode_credit_card_as_json, encode_decimal_as_json])
json_decoder_func = chain_custom_decoders([decode_credit_card_from_dict, decode_decimal_from_dict])


class GlobalIris3dsAttempt(object):
    pass


class GlobalIris3dsError(GlobalIris3dsAttempt):
    error = True

    def __init__(self, message, response):
        self.message = message
        self.response = response

    def __repr__(self):
        return "GlobalIris3dsError(%r, %r)" % (self.message, self.response)


class GlobalIris3dsResponse(GlobalIris3dsAttempt):
    error = False


class GlobalIris3dsVerifyEnrolled(GlobalIris3dsResponse):
    def __init__(self, xml_content):
        tree = lxml.etree.fromstring(xml_content)
        self.response_code = tree.find('result').text
        enrolled_node = tree.find('enrolled')
        self.enrolled = enrolled_node is not None and enrolled_node.text == "Y"
        self.message = tree.find('message').text
        if self.response_code in ["00", "110"]:
            self.url = tree.find('url').text
            self.pareq = tree.find('pareq').text
        else:
            self.error = True
            log.warning("3Ds verifyenrolled error", extra={'response_xml': xml_content})


    def proceed_with_auth(self, card):
        """
        Returns a tuple (bool, dict) indicating if you can
        proceed directly with authorisation.

        If the bool == True, you must pass the data in the dict as additional
        data to the gateway.purchase() method.
        """
        if self.error:
            return False, {}
        if not self.enrolled and (self.url is None or self.url == ""):
            eci = 6 if card.card_type is Visa else 1
            return True, {'mpi': {'eci': eci}}
        return False, {}


class GlobalIris3dsVerifySig(GlobalIris3dsResponse):
    def __init__(self, xml_content):
        tree = lxml.etree.fromstring(xml_content)
        self.response_code = tree.find('result').text
        self.message = tree.find('message').text
        if self.response_code == "00":
            threed = tree.find('threedsecure')
            self.status = threed.find('status').text
            if self.status in ["Y", "A"]:
                self.eci = threed.find('eci').text
                self.xid = threed.find('xid').text
                self.cavv = threed.find('cavv').text
        else:
            self.error = True
            log.warning("3Ds verifysig error", extra={'response_xml': xml_content})

    def proceed_with_auth(self, card):
        """
        Returns a tuple (bool, dict) indicating if you can
        proceed with authorisation.

        If the bool == True, you must pass the data in the dict as additional
        data to the gateway.purchase() method.
        """
        if self.error or self.status in ["N", "U"]:
            # Proceeding with status "U" is allowed, but risky
            return False, {}

        if self.status in ["Y", "A"]:
            mpi_data = {'eci': self.eci,
                        'xid': self.xid,
                        'cavv': self.cavv,
                        }
            return True, {'mpi': mpi_data}

        return False, {}

########NEW FILE########
__FILENAME__ = google_checkout_integration
from billing import Integration, IntegrationNotConfigured
from billing.models import GCNewOrderNotification
from django.conf import settings
from xml.dom import minidom
import hmac
import hashlib
import base64
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, QueryDict
from billing import signals
from django.conf.urls import patterns
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

SANDBOX_URL = 'https://sandbox.google.com/checkout/api/checkout/v2/checkout/Merchant/%s'
PROD_URL = 'https://checkout.google.com/api/checkout/v2/checkout/Merchant/%s'

BUTTON_SANDBOX_URL = 'https://sandbox.google.com/checkout/buttons/checkout.gif?merchant_id=%(merchant_id)s&w=%(width)s&h=%(height)s&style=white&variant=text&loc=en_US'
BUTTON_URL = 'https://checkout.google.com/buttons/checkout.gif?merchant_id=%(merchant_id)s&w=%(width)s&h=%(height)s&style=white&variant=text&loc=en_US'

csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)


class GoogleCheckoutIntegration(Integration):
    display_name = 'Google Checkout'
    template = "billing/google_checkout.html"

    def __init__(self, options=None):
        if not options:
            options = {}
        super(GoogleCheckoutIntegration, self).__init__(options=options)
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("google_checkout"):
            raise IntegrationNotConfigured("The '%s' integration is not correctly "
                                       "configured." % self.display_name)
        google_checkout_settings = merchant_settings["google_checkout"]
        self.merchant_id = google_checkout_settings['MERCHANT_ID']
        self.merchant_key = google_checkout_settings['MERCHANT_KEY']
        self._signature = None

    @property
    def service_url(self):
        if self.test_mode:
            return SANDBOX_URL % self.merchant_id
        return PROD_URL % self.merchant_id

    def button_image_url(self):
        params = {"merchant_id": self.merchant_id,
                  "width": self.button_width,
                  "height": self.button_height}
        if self.test_mode:
            return BUTTON_SANDBOX_URL % params
        return BUTTON_URL % params

    @property
    def button_width(self):
        return self.fields.get("button_width", 180)

    @property
    def button_height(self):
        return self.fields.get("button_height", 46)

    def _add_nodes(self, doc, parent_node, child_node_name,
                   child_subnode_name, child_node_values):
        """ Helper method that makes it easy to add a bunch of like child nodes
        to a parent node"""
        if child_node_values:
            for value in child_node_values:
                child_node = doc.createElement(unicode(child_node_name))
                child_sub_node = doc.createElement(unicode(child_subnode_name))
                child_node.appendChild(child_sub_node)
                child_sub_node.appendChild(doc.createTextNode(value))
                parent_node.appendChild(child_node)

    def _shipping_allowed_excluded(self, doc, parent_node, data):
        """ Build the nodes for the allowed-areas, excluded-areas
        for shipping-restrictions and address-filters """
        if not data:
            return
        states = data.get('us-state-area', None)
        zips = data.get('us-zip-area', None)
        country = data.get('us-country-area', None)
        world = data.get('world-area', False)
        postal = data.get('postal-area', None)

        self._add_nodes(doc, parent_node, 'us-state-area', 'state', states)
        self._add_nodes(doc, parent_node, 'us-zip-area', 'zip-pattern', zips)

        if country:
            us_country_area = doc.createElement('us-country-area')
            us_country_area.setAttribute('country-area', unicode(country))
            parent_node.appendChild(us_country_area)

        if world:
            parent_node.appendChild(doc.createElement('world-area'))

        if postal:
            for post in postal:
                p_country_code = post.get('country-code', None)
                p_pattern = post.get('postal-code-pattern', None)
                postal_area = doc.createElement('postal-area')
                if p_country_code:
                    c_code = doc.createElement('country-code')
                    c_code.appendChild(doc.createTextNode(unicode(p_country_code)))
                    postal_area.appendChild(c_code)
                if p_pattern:
                    for pp in p_pattern:
                        p_p = doc.createElement('postal-code-pattern')
                        p_p.appendChild(doc.createTextNode(unicode(pp)))
                        postal_area.appendChild(p_p)
                parent_node.appendChild(postal_area)


    def _shipping_restrictions_filters(self, doc, parent_node, data):
        """ process the shipping restriction and address-filter sections for
        the shipping method merchant-calculated-shipping and flat-rate-shipping
        """
        the_allowed_areas = data.get('allowed-areas', None)
        the_excluded_areas = data.get('excluded-areas', None)
        allow_us_po_box = data.get('allow-us-po-box', None)

        if allow_us_po_box is not None:
            allow_po_box = doc.createElement('allow-us-po-box')
            allow_po_box.appendChild(
                    doc.createTextNode(str(allow_us_po_box).lower()))
            parent_node.appendChild(allow_po_box)

        if the_allowed_areas:
            allowed_areas = doc.createElement('allowed-areas')
            parent_node.appendChild(allowed_areas)
            self._shipping_allowed_excluded(doc,
                                            allowed_areas,
                                            the_allowed_areas)

        if the_excluded_areas:
            excluded_areas = doc.createElement('excluded-areas')
            parent_node.appendChild(excluded_areas)
            self._shipping_allowed_excluded(doc,
                                            excluded_areas,
                                            the_excluded_areas)


    def _process_tax_rule(self, doc, parent_node, node_name, data, show_shipping_tax=True):
        """ process a tax rule default_tax_rule, and alternative_tax_rule"""
        tax_rule = doc.createElement(node_name)
        parent_node.appendChild(tax_rule)
        shipping_taxed = data.get('shipping-taxed', False)
        rate = data.get('rate', 0)
        tax_area = data.get('tax-area', {})
        zips = tax_area.get('us-zip-area', [])
        states = tax_area.get('us-state-area', [])
        postal = tax_area.get('postal-area', [])
        country = tax_area.get('us-country-area', None)
        word_area = tax_area.get('world-area', False)

        if shipping_taxed is not None and show_shipping_tax:
            shippingtaxed_node = doc.createElement('shipping-taxed')
            shippingtaxed_node.appendChild(
            doc.createTextNode(str(shipping_taxed).lower()))
            tax_rule.appendChild(shippingtaxed_node)

        rate_node = doc.createElement('rate')
        rate_node.appendChild(
        doc.createTextNode(str(rate)))
        tax_rule.appendChild(rate_node)

        # if there is more then one area then the tag switches from
        # tax-area to tax-areas.
        total_areas = len(zips) + len(states) + len(postal)
        if word_area:
            total_areas += 1
        if country is not None:
            total_areas += 1

        if total_areas == 1:
            tax_area_label = 'tax-area'
        else:
            tax_area_label = 'tax-areas'

        tax_area_node = doc.createElement(tax_area_label)
        tax_rule.appendChild(tax_area_node)

        self._add_nodes(doc, tax_area_node, 'us-state-area', 'state', states)
        self._add_nodes(doc, tax_area_node, 'us-zip-area', 'zip-pattern', zips)

        if country is not None:
            us_country_area = doc.createElement('us-country-area')
            us_country_area.setAttribute('country-area', unicode(country))
            tax_area_node.appendChild(us_country_area)

        if word_area:
            tax_area_node.appendChild(doc.createElement('world-area'))

        if postal:
            for post in postal:
                p_country_code = post.get('country-code', None)
                p_pattern = post.get('postal-code-pattern', None)
                postal_area = doc.createElement('postal-area')
                if p_country_code:
                    c_code = doc.createElement('country-code')
                    c_code.appendChild(doc.createTextNode(unicode(p_country_code)))
                    postal_area.appendChild(c_code)
                if p_pattern:
                    for pp in p_pattern:
                        p_p = doc.createElement('postal-code-pattern')
                        p_p.appendChild(doc.createTextNode(unicode(pp)))
                        postal_area.appendChild(p_p)
                tax_area_node.appendChild(postal_area)

    def _alt_tax_tables(self, doc, parent_node, data):
        """ Alternative Tax tables """
        alt_tax_tables = data.get('alternate-tax-tables', None)
        if not alt_tax_tables:
            return

        alt_tax_tables_node = doc.createElement('alternate-tax-tables')
        parent_node.appendChild(alt_tax_tables_node)

        for alt_tax_table in alt_tax_tables:
            alt_tax_table_node = doc.createElement('alternate-tax-table')
            alt_tax_table_node.setAttribute('name', unicode(alt_tax_table.get('name')))
            alt_tax_table_node.setAttribute('standalone', unicode(str(alt_tax_table.get('standalone', False)).lower()))
            alt_tax_tables_node.appendChild(alt_tax_table_node)

            # if there are no rules we still want to show the element <alternate-tax-rules/>
            alt_tax_rules = alt_tax_table.get('alternative-tax-rules', [])
            alt_tax_rules_node = doc.createElement('alternate-tax-rules')
            alt_tax_table_node.appendChild(alt_tax_rules_node)

            for tax_rule in alt_tax_rules:
                self._process_tax_rule(doc, alt_tax_rules_node, 'alternate-tax-rule', tax_rule, show_shipping_tax=False)

    def _default_tax_table(self, doc, parent_node, data):
        """ process default tax table """
        default_tax_table_node = doc.createElement('default-tax-table')
        parent_node.appendChild(default_tax_table_node)

        tax_rules_node = doc.createElement('tax-rules')
        default_tax_table_node.appendChild(tax_rules_node)

        default_tax_table = data.get('default-tax-table', None)
        if default_tax_table:
            tax_rules = default_tax_table.get('tax-rules', [])
            for tax_rule in tax_rules:
                self._process_tax_rule(doc, tax_rules_node, 'default-tax-rule', tax_rule)

    def _taxes(self, doc, parent_node, data):
        """ Process the taxes section """

        tax_tables = doc.createElement('tax-tables')
        parent_node.appendChild(tax_tables)

        self._default_tax_table(doc, tax_tables, data)
        self._alt_tax_tables(doc, tax_tables, data)

    def _process_item(self, doc, parent, item, item_tag_name="item"):
        it = doc.createElement(item_tag_name)
        parent.appendChild(it)
        it_name = doc.createElement("item-name")
        it_name.appendChild(doc.createTextNode(unicode(item["name"])))
        it.appendChild(it_name)
        it_descr = doc.createElement('item-description')
        it_descr.appendChild(doc.createTextNode(unicode(item["description"])))
        it.appendChild(it_descr)
        it_price = doc.createElement("unit-price")
        it_price.setAttribute("currency", unicode(item["currency"]))
        it_price.appendChild(doc.createTextNode(unicode(item["amount"])))
        it.appendChild(it_price)
        it_qty = doc.createElement("quantity")
        it_qty.appendChild(doc.createTextNode(unicode(item["quantity"])))
        it.appendChild(it_qty)
        it_unique_id = doc.createElement("merchant-item-id")
        it_unique_id.appendChild(doc.createTextNode(unicode(item["id"])))
        it.appendChild(it_unique_id)
        if 'private-item-data' in item:
            it_private = doc.createElement("merchant-private-item-data")
            it.appendChild(it_private)
            it_data = unicode(item.get('private-item-data', ""))
            it_private.appendChild(doc.createTextNode(it_data))
        if 'subscription' in item:
            subscription = item['subscription']
            it_subscription = doc.createElement("subscription")
            if "type" in subscription:
                it_subscription.setAttribute('type', unicode(subscription["type"]))
            if "period" in subscription:
                it_subscription.setAttribute('period', unicode(subscription["period"]))
            if "start-date" in subscription:
                it_subscription.setAttribute('start-date', unicode(subscription["start-date"]))
            if "no-charge-after" in subscription:
                it_subscription.setAttribute('no-charge-after', unicode(subscription["no-charge-after"]))
            it.appendChild(it_subscription)
            if "payments" in subscription:
                it_payments = doc.createElement("payments")
                it_subscription.appendChild(it_payments)
                payment_items = subscription["payments"]
                for payment in payment_items:
                    it_subscription_payment = doc.createElement("subscription-payment")
                    it_payments.appendChild(it_subscription_payment)
                    if 'times' in payment:
                        it_subscription_payment.setAttribute('times', unicode(payment["times"]))
                    maximum_charge = doc.createElement("maximum-charge")
                    maximum_charge.setAttribute("currency", unicode(payment["currency"]))
                    it_subscription_payment.appendChild(maximum_charge)
                    maximum_charge.appendChild(doc.createTextNode(unicode(payment["maximum-charge"])))
            if "recurrent-items" in subscription:
                recurrent_items = subscription["recurrent-items"]
                for recurrent_item in recurrent_items:
                    self._process_item(doc, it_subscription, recurrent_item, item_tag_name="recurrent-item")

        if "digital-content" in item:
            digital_content = item['digital-content']
            it_dc = doc.createElement("digital-content")
            it.appendChild(it_dc)
            if "display-disposition" in digital_content:
                dc_dd = doc.createElement('display-disposition')
                dc_dd.appendChild(doc.createTextNode(unicode(digital_content["display-disposition"])))
                it_dc.appendChild(dc_dd)
            if "description" in digital_content:
                dc_descr = doc.createElement('description')
                dc_descr.appendChild(doc.createTextNode(unicode(digital_content["description"])))
                it_dc.appendChild(dc_descr)
            if "email-delivery" in digital_content:
                dc_email = doc.createElement('email-delivery')
                dc_email.appendChild(doc.createTextNode(unicode(digital_content["email-delivery"])))
                it_dc.appendChild(dc_email)
            if "key" in digital_content:
                dc_key = doc.createElement('key')
                dc_key.appendChild(doc.createTextNode(unicode(digital_content["key"])))
                it_dc.appendChild(dc_key)
            if "url" in digital_content:
                dc_url = doc.createElement('url')
                dc_url.appendChild(doc.createTextNode(unicode(digital_content["url"])))
                it_dc.appendChild(dc_url)

        if 'tax-table-selector' in item:
            tax_table_selector_node = doc.createElement('tax-table-selector')
            it.appendChild(tax_table_selector_node)
            it_tax_table = unicode(item.get('tax-table-selector', ""))
            tax_table_selector_node.appendChild(doc.createTextNode(it_tax_table))

    def build_xml(self):
        """ Build up the Cart XML. Seperate method for easier unit testing """
        doc = minidom.Document()
        root = doc.createElement('checkout-shopping-cart')
        root.setAttribute('xmlns', 'http://checkout.google.com/schema/2')
        doc.appendChild(root)
        cart = doc.createElement('shopping-cart')
        root.appendChild(cart)
        items = doc.createElement('items')
        cart.appendChild(items)

        merchant_private_data = doc.createElement('merchant-private-data')
        cart.appendChild(merchant_private_data)
        private_data = unicode(self.fields.get("private_data", ""))
        merchant_private_data.appendChild(doc.createTextNode(private_data))

        ip_items = self.fields.get("items", [])
        for item in ip_items:
            self._process_item(doc, items, item)

        checkout_flow = doc.createElement('checkout-flow-support')
        root.appendChild(checkout_flow)
        merchant_checkout_flow = doc.createElement('merchant-checkout-flow-support')
        checkout_flow.appendChild(merchant_checkout_flow)
        return_url = doc.createElement('continue-shopping-url')
        return_url.appendChild(doc.createTextNode(self.fields["return_url"]))
        merchant_checkout_flow.appendChild(return_url)

        # supports: flat-rate-shipping, merchant-calculated-shipping, pickup
        # No support for carrier-calculated-shipping yet
        shipping = self.fields.get("shipping-methods", [])
        if shipping:
            shipping_methods = doc.createElement('shipping-methods')
            merchant_checkout_flow.appendChild(shipping_methods)

            for ship_method in shipping:
                # don't put dict.get() because we want these to fail if 
                # they aren't here because they are required.
                shipping_type = doc.createElement(unicode(ship_method["shipping_type"]))
                shipping_type.setAttribute('name', unicode(ship_method["name"]))
                shipping_methods.appendChild(shipping_type)

                shipping_price = doc.createElement('price')
                shipping_price.setAttribute('currency', unicode(ship_method["currency"]))
                shipping_type.appendChild(shipping_price)

                shipping_price_text = doc.createTextNode(unicode(ship_method["price"]))
                shipping_price.appendChild(shipping_price_text)

                restrictions = ship_method.get('shipping-restrictions', None)
                if restrictions:
                    shipping_restrictions = doc.createElement('shipping-restrictions')
                    shipping_type.appendChild(shipping_restrictions)
                    self._shipping_restrictions_filters(doc, 
                                                        shipping_restrictions,
                                                        restrictions)

                address_filters = ship_method.get('address-filters', None)
                if address_filters:
                    address_filters_node = doc.createElement('address-filters')
                    shipping_type.appendChild(address_filters_node)
                    self._shipping_restrictions_filters(doc, 
                                                        address_filters_node,
                                                        address_filters)

        # add support for taxes.
        # both default-tax-table and alternate-tax-tables is supported.
        taxes = self.fields.get("tax-tables", None)
        if taxes:
            self._taxes(doc, merchant_checkout_flow, taxes)

        return doc.toxml(encoding="utf-8")

    def generate_cart_xml(self):
        cart_xml = self.build_xml()
        hmac_signature = hmac.new(self.merchant_key, cart_xml, hashlib.sha1).digest()
        self._signature = base64.b64encode(hmac_signature)
        return base64.b64encode(cart_xml)

    def signature(self):
        if not self._signature:
            self.generate_cart_xml()
        return self._signature

    @csrf_exempt_m
    @require_POST_m
    def gc_notify_handler(self, request):
        #get the Authorization string from the Google POST header
        auth_string = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_string:
            #decode the Authorization string and remove Basic portion
            plain_string = base64.b64decode(auth_string.lstrip('Basic '))
            #split the decoded string at the ':'
            split_string = plain_string.split(':')
            merchant_id = split_string[0]
            merchant_key = split_string[1]
            if self.check_auth(merchant_id, merchant_key):
                data = self.parse_response(request.body)

                type = data.get('type', "")
                serial_number = data.get('serial-number', "").strip()

                if type == 'new-order-notification':
                    self.gc_new_order_notification(data)
                elif type == 'order-state-change-notification':
                    self.gc_order_state_change_notification(data)
                elif type == 'charge-amount-notification':
                    self.gc_charge_amount_notification(data)

                # Create Response
                doc = minidom.Document()
                notification_acknowledgment = doc.createElement("notification-acknowledgment")
                notification_acknowledgment.setAttribute("xmlns","http://checkout.google.com/schema/2")
                notification_acknowledgment.setAttribute("serial-number", serial_number)
                doc.appendChild(notification_acknowledgment)
                ack = doc.toxml(encoding="utf-8")

                return HttpResponse(content=ack, content_type="text/xml; charset=UTF-8")
            else:
                raise PermissionDenied
        else:
            raise PermissionDenied

    def gc_cart_items_blob(self, post_data):
        items = post_data.getlist('shopping-cart.items')
        cart_blob = ''
        for item in items:
            item_id = post_data.get('%s.merchant-item-id' % (item), '')
            item_name = post_data.get('%s.item-name' % (item), '')
            item_desc = post_data.get('%s.item-description' % (item), '')
            item_price = post_data.get('%s.unit-price' % (item), '')
            item_price_currency = post_data.get('%s.unit-price.currency' % (item), '')
            item_quantity = post_data.get('%s.quantity' % (item), '')
            item_private_data = post_data.get('%s.merchant-private-item-data' % (item), '')
            cart_blob += '%(item_id)s\t%(item_name)s\t%(item_desc)s\t%(item_price)s\t%(item_price_currency)s\t%(item_quantity)s\t%(item_private_data)s\n\n' % ({"item_id": item_id,
                                                                                                                             "item_name": item_name,
                                                                                                                             "item_desc": item_desc,
                                                                                                                             "item_price": item_price,
                                                                                                                             "item_price_currency": item_price_currency,
                                                                                                                             "item_quantity": item_quantity,
                                                                                                                             "item_private_data": item_private_data,
                                                                                                                             })
        return cart_blob

    def gc_new_order_notification(self, post_data):
        data = {}

        resp_fields = {
            "type": "notify_type",
            "serial-number": "serial_number",
            "google-order-number": "google_order_number",
            "buyer-id": "buyer_id",
            "buyer-shipping-address.contact-name": "shipping_contact_name",
            "buyer-shipping-address.address1": "shipping_address1",
            "buyer-shipping-address.address2": "shipping_address2",
            "buyer-shipping-address.city": "shipping_city",
            "buyer-shipping-address.postal-code": "shipping_postal_code",
            "buyer-shipping-address.region": "shipping_region",
            "buyer-shipping-address.country-code": "shipping_country_code",
            "buyer-shipping-address.email": "shipping_email",
            "buyer-shipping-address.company-name": "shipping_company_name",
            "buyer-shipping-address.fax": "shipping_fax",
            "buyer-shipping-address.phone": "shipping_phone",
            "buyer-billing-address.contact-name": "billing_contact_name",
            "buyer-billing-address.address1": "billing_address1",
            "buyer-billing-address.address2": "billing_address2",
            "buyer-billing-address.city": "billing_city",
            "buyer-billing-address.postal-code": "billing_postal_code",
            "buyer-billing-address.region": "billing_region",
            "buyer-billing-address.country-code": "billing_country_code",
            "buyer-billing-address.email": "billing_email",
            "buyer-billing-address.company-name": "billing_company_name",
            "buyer-billing-address.fax": "billing_fax",
            "buyer-billing-address.phone": "billing_phone",
            "buyer-marketing-preferences.email-allowed": "marketing_email_allowed",
            "order-adjustment.total-tax": "total_tax",
            "order-adjustment.total-tax.currency": "total_tax_currency",
            "order-adjustment.adjustment-total": "adjustment_total",
            "order-adjustment.adjustment-total.currency": "adjustment_total_currency",
            "order-total": "order_total",
            "order-total.currency": "order_total_currency",
            "financial-order-state": "financial_order_state",
            "fulfillment-order-state": "fulfillment_order_state",
            "timestamp": "timestamp",
            "shopping-cart.merchant-private-data": "private_data",
            }

        for (key, val) in resp_fields.iteritems():
            data[val] = post_data.get(key, '')

        data['num_cart_items'] = len(post_data.getlist('shopping-cart.items'))
        data['cart_items'] = self.gc_cart_items_blob(post_data)

        resp = GCNewOrderNotification.objects.create(**data)

    def gc_order_state_change_notification(self, post_data):
        order = GCNewOrderNotification.objects.get(google_order_number=post_data['google-order-number'])
        order.financial_order_state = post_data['new-financial-order-state']
        order.fulfillment_order_state = post_data['new-fulfillment-order-state']
        order.save()

    def gc_charge_amount_notification(self, post_data):
        order = GCNewOrderNotification.objects.get(google_order_number=post_data['google-order-number'])
        post_data['local_order'] = order
        signals.transaction_was_successful.send(sender=self.__class__,
                                                    type="purchase",
                                                    response=post_data)

    def get_urls(self):
        urlpatterns = patterns('',
           (r'^gc-notify-handler/$', self.gc_notify_handler),
                               )
        return urlpatterns

    def check_auth(self, merchant_id, merchant_key):
        "Check to ensure valid Google notification."
        if merchant_id == self.merchant_id and merchant_key == self.merchant_key:
            return True
        else: return False

    def parse_response(self, response):
        dom = minidom.parseString(response)
        response_type = dom.childNodes[0].localName #get the reaponse type
        #use this dictionary to determine which items will be taken from the reaponse
        result = QueryDict("", mutable=True)
        result['type'] = response_type
        # load root values
        result.update(self.load_child_nodes(dom.childNodes[0], is_root=True, ignore_nodes=["items"]))
        # load items
        items_arr = []
        items_node = dom.getElementsByTagName('items')
        if items_node:
            n = 0
            for item in items_node[0].childNodes:
                if item.localName:
                    # load root item values
                    item_name = 'item-%s' % n
                    for key, value in self.load_child_nodes(item, is_root=True, ignore_nodes=['subscription', 'digital-content']).items():
                        result['%s.%s' % (item_name, key)] = value
                    n += 1
                    items_arr.append(item_name)
            result.setlist('shopping-cart.items', items_arr)

        return result

    def load_child_nodes(self, node, load_attributes=True, load_complex_nodes=True, is_root=False, ignore_nodes=[]):
        result={}
        if node:
            if is_root:
                for key, value in node.attributes.items():
                    result[str(key)] = value
            for n in node.childNodes:
                if n.localName and n.localName not in ignore_nodes:
                    if load_attributes:
                        for key, value in n.attributes.items():
                            if is_root:
                                result['%s.%s' % (str(n.localName), str(key))] = value
                            else:
                                result['%s.%s.%s' % (str(node.localName), str(n.localName), str(key))] = value
                    if len(n.childNodes) > 1 and load_complex_nodes:
                        for key, value in self.load_child_nodes(n, ignore_nodes=ignore_nodes).items():
                            if is_root:
                                result[key] = value
                            else:
                                result['%s.%s' % (str(node.localName), str(key))] = value
                    elif n.firstChild:
                        if is_root:
                            result[str(n.localName)] = n.firstChild.data
                        else:
                            result['%s.%s' % (str(node.localName), str(n.localName))] = n.firstChild.data
                    else:
                        if is_root:
                            result[str(n.localName)] = ""
                        else:
                            result['%s.%s' % (str(node.localName), str(n.localName))] = ""
        return result

########NEW FILE########
__FILENAME__ = ogone_payments_integration
# -*- coding: utf-8 *-*
from billing import Integration, IntegrationNotConfigured
from django.conf import settings

from django.conf.urls import patterns, url
from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render_to_response

from django_ogone.ogone import Ogone
from django_ogone.status_codes import get_status_category, get_status_description, \
SUCCESS_STATUS, DECLINE_STATUS, EXCEPTION_STATUS, CANCEL_STATUS
from django_ogone.signals import ogone_payment_accepted, ogone_payment_failed, ogone_payment_cancelled

from billing.utils.utilities import Bunch


class OgonePaymentsIntegration(Integration):
    display_name = "Ogone Payments Integration"
    template = "billing/ogone_payments.html"

    def __init__(self, options=None):
        if not options:
            options = {}
        super(OgonePaymentsIntegration, self).__init__(options=options)
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("ogone_payments"):
            raise IntegrationNotConfigured("The '%s' integration is not correctly "
                                       "configured." % self.display_name)
        bunch = Bunch()
        bunch.update(merchant_settings["ogone_payments"])
        self.settings = bunch

    @property
    def service_url(self):
        return Ogone.get_action(production=self.settings.PRODUCTION)

    def ogone_notify_handler(self, request):
        response = Ogone(request=request, settings=self.settings)
        if response.is_valid():
            fpath = request.get_full_path()
            query_string = fpath.split("?", 1)[1]
            transaction_feedback = query_string.split('&')
            result = {}
            for item in transaction_feedback:
                k, v = item.split("=")
                result[k] = v

            # Default transaction feedback parameters
            status = result.get('STATUS', False)
            orderid = result.get('orderID', '')
            payid = result.get('PAYID', '')
            ncerror = result.get('NCERROR', '')

            amount = result.get('amount', '')
            currency = result.get('currency', '')

            if status and get_status_category(int(status)) == SUCCESS_STATUS:
                ogone_payment_accepted.send(sender=self, order_id=orderid, \
                    amount=amount, currency=currency, pay_id=payid, status=status, ncerror=ncerror)
                return self.ogone_success_handler(request, response=result, description=get_status_description(int(status)))

            if status and get_status_category(int(status)) == CANCEL_STATUS:
                ogone_payment_cancelled.send(sender=self, order_id=orderid, \
                    amount=amount, currency=currency, pay_id=payid, status=status, ncerror=ncerror)
                return self.ogone_cancel_handler(request, response=result, description=get_status_description(int(status)))

            if status and get_status_category(int(status)) == DECLINE_STATUS or EXCEPTION_STATUS:
                ogone_payment_failed.send(sender=self, order_id=orderid, \
                    amount=amount, currency=currency, pay_id=payid, status=status, ncerror=ncerror)
                return self.ogone_failure_handler(request, response=result, description=get_status_description(int(status)))
        else:
            return HttpResponse('signature validation failed!')

    def ogone_success_handler(self, request, response=None, description=''):
        return render_to_response("billing/ogone_success.html",
                                  {"response": response, "message": description},
                                  context_instance=RequestContext(request))

    def ogone_failure_handler(self, request, response=None, description=''):
        return render_to_response("billing/ogone_failure.html",
                                  {"response": response, "message": description},
                                  context_instance=RequestContext(request))

    def ogone_cancel_handler(self, request, response=None, description=''):
        return render_to_response("billing/ogone_cancel.html",
                                  {"response": response, "message": description},
                                  context_instance=RequestContext(request))

    def get_urls(self):
        urlpatterns = patterns('',
            url('^ogone_notify_handler/$', self.ogone_notify_handler, name="ogone_notify_handler"),
        )
        return urlpatterns

    def add_fields(self, params):
        for (key, val) in params.iteritems():
            if isinstance(val, dict):
                new_params = {}
                for k in val:
                    new_params["%s__%s" % (key, k)] = val[k]
                self.add_fields(new_params)
            else:
                self.add_field(key, val)

    def generate_form(self):
        form = Ogone.get_form(self.fields, settings=self.settings)
        return form

########NEW FILE########
__FILENAME__ = pay_pal_integration
from django.conf import settings
from django.conf.urls import patterns, include

from paypal.standard.conf import POSTBACK_ENDPOINT, SANDBOX_POSTBACK_ENDPOINT
from paypal.standard.ipn.signals import (payment_was_flagged,
                                         payment_was_successful)

from billing import Integration, IntegrationNotConfigured
from billing.forms.paypal_forms import (MerchantPayPalPaymentsForm,
                                        MerchantPayPalEncryptedPaymentsForm)
from billing.signals import (transaction_was_successful,
                             transaction_was_unsuccessful)


class PayPalIntegration(Integration):
    display_name = "PayPal IPN"
    template = "billing/paypal.html"

    def __init__(self):
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("pay_pal"):
            raise IntegrationNotConfigured("The '%s' integration is not \
                                    correctly configured." % self.display_name)
        pay_pal_settings = merchant_settings["pay_pal"]
        self.encrypted = False
        if pay_pal_settings.get("ENCRYPTED"):
            self.encrypted = True
        # Required Fields. Just a template for the user
        self.fields = {"business": pay_pal_settings['RECEIVER_EMAIL'],
                       "item_name": "",
                       "invoice": "",
                       "notify_url": "",
                       "return_url": "",
                       "cancel_return": "",
                       "amount": 0,
                       }

    @property
    def service_url(self):
        if self.test_mode:
            return SANDBOX_POSTBACK_ENDPOINT
        return POSTBACK_ENDPOINT

    def get_urls(self):
        urlpatterns = patterns('', (r'^', include('paypal.standard.ipn.urls')))
        return urlpatterns

    def form_class(self):
        if self.encrypted:
            return MerchantPayPalEncryptedPaymentsForm
        return MerchantPayPalPaymentsForm

    def generate_form(self):
        return self.form_class()(initial=self.fields)


def unsuccessful_txn_handler(sender, **kwargs):
    transaction_was_unsuccessful.send(sender=sender.__class__,
                                      type="purchase",
                                      response=sender)


def successful_txn_handler(sender, **kwargs):
    transaction_was_successful.send(sender=sender.__class__,
                                    type="purchase",
                                    response=sender)

payment_was_flagged.connect(unsuccessful_txn_handler)
payment_was_successful.connect(successful_txn_handler)

########NEW FILE########
__FILENAME__ = stripe_integration
from billing import Integration, get_gateway, IntegrationNotConfigured
from django.conf import settings
from django.conf.urls import patterns, url
from billing.forms.stripe_forms import StripeForm


class StripeIntegration(Integration):
    display_name = "Stripe"
    template = "billing/stripe.html"

    def __init__(self):
        super(StripeIntegration, self).__init__()
        merchant_settings = getattr(settings, "MERCHANT_SETTINGS")
        if not merchant_settings or not merchant_settings.get("stripe"):
            raise IntegrationNotConfigured("The '%s' integration is not correctly "
                                       "configured." % self.display_name)
        stripe_settings = merchant_settings["stripe"]
        self.gateway = get_gateway("stripe")
        self.publishable_key = stripe_settings['PUBLISHABLE_KEY']

    def form_class(self):
        return StripeForm

    def generate_form(self):
        initial_data = self.fields
        form = self.form_class()(initial=initial_data)
        return form

    def transaction(self, request):
        # Subclasses must override this
        raise NotImplementedError

    def get_urls(self):
        urlpatterns = patterns('',
           url('^stripe_token/$', self.transaction, name="stripe_transaction")
        )
        return urlpatterns

########NEW FILE########
__FILENAME__ = world_pay_integration
from billing.integration import Integration
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf.urls import patterns
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from django.http import HttpResponse
from billing.models.world_pay_models import WorldPayResponse
from django.utils.decorators import method_decorator
from billing.forms.world_pay_forms import WPHostedPaymentForm

RBS_HOSTED_URL_TEST = "https://select-test.worldpay.com/wcc/purchase"
RBS_HOSTED_URL_LIVE = "https://secure.worldpay.com/wcc/purchase"

# http://www.rbsworldpay.com/support/bg/index.php?page=development&sub=integration&c=WW

csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)


class WorldPayIntegration(Integration):
    """
    Fields required:
    instId: Installation ID provided by WorldPay
    cartId: Merchant specified unique id to identify user
    amount: Amount to be charged
    currency: ISO 3-character currency
    """
    display_name = "RBS World Pay"
    template = "billing/world_pay.html"

    def __init__(self, options=None):
        if not options:
            options = {}
        super(WorldPayIntegration, self).__init__(options=options)
        if self.test_mode:
            self.fields.update({"testMode": 100})

    def get_urls(self):
        urlpatterns = patterns('',
           (r'^rbs-notify-handler/$', self.notify_handler),
                               )
        return urlpatterns

    @property
    def service_url(self):
        if self.test_mode:
            return RBS_HOSTED_URL_TEST
        return RBS_HOSTED_URL_LIVE

    def form_class(self):
        return WPHostedPaymentForm

    def generate_form(self):
        return self.form_class()(initial=self.fields)

    @csrf_exempt_m
    @require_POST_m
    def notify_handler(self, request):
        post_data = request.POST.copy()
        data = {}

        resp_fields = {
            'instId': 'installation_id',
            'compName': 'company_name',
            'cartId': 'cart_id',
            'desc': 'description',
            'amount': 'amount',
            'currency': 'currency',
            'authMode': 'auth_mode',
            'testMode': 'test_mode',
            'transId': 'transaction_id',
            'transStatus': 'transaction_status',
            'transTime': 'transaction_time',
            'authAmount': 'auth_amount',
            'authCurrency': 'auth_currency',
            'authAmountString': 'auth_amount_string',
            'rawAuthMessage': 'raw_auth_message',
            'rawAuthCode': 'raw_auth_code',
            'name': 'name',
            'address': 'address',
            'postcode': 'post_code',
            'country': 'country_code',
            'countryString': 'country',
            'tel': 'phone',
            'fax': 'fax',
            'email': 'email',
            'futurePayId': 'future_pay_id',
            'cardType': 'card_type',
            'ipAddress': 'ip_address',
            }

        for (key, val) in resp_fields.iteritems():
            data[val] = post_data.get(key, '')

        try:
            resp = WorldPayResponse.objects.create(**data)
            # TODO: Make the type more generic
            transaction_was_successful.send(sender=self.__class__, type="purchase", response=resp)
            status = "SUCCESS"
        except:
            transaction_was_unsuccessful.send(sender=self.__class__, type="purchase", response=post_data)
            status = "FAILURE"

        return HttpResponse(status)

########NEW FILE########
__FILENAME__ = check_billing_settings
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

PAYPAL_STANDARD_IPN = ['PAYPAL_RECEIVER_EMAIL']
# PAYPAL_STANDARD_PDT = ['PAYPAL_IDENTITY_TOKEN']
PAYPAL_PRO = ['PAYPAL_TEST', 'PAYPAL_WPP_USER', 'PAYPAL_WPP_PASSWORD', 'PAYPAL_WPP_SIGNATURE']
AUTHORIZE = ['AUTHORIZE_LOGIN_ID', 'AUTHORIZE_TRANSACTION_KEY']
EWAY = ['EWAY_CUSTOMER_ID', 'EWAY_USERNAME', 'EWAY_PASSWORD']
GOOGLE_CHECKOUT = ['GOOGLE_CHECKOUT_MERCHANT_ID', 'GOOGLE_CHECKOUT_MERCHANT_KEY']

RBS_TEST = {'required': ['RBS_INSTALLTION_ID_TEST'], 'optional': ['RBS_MD5_SECRET_KEY']}
RBS_LIVE = {'required': ['RBS_INSTALLTION_ID_LIVE'], 'optional': ['RBS_MD5_SECRET_KEY']}

PAYMENT_GATEWAYS = {
    'authorize': AUTHORIZE,
    'eway': EWAY,
    'google_checkout': GOOGLE_CHECKOUT,
    'paypal_pro': PAYPAL_PRO,
    'paypal_ipn': PAYPAL_STANDARD_IPN,
    'rbs_test': RBS_TEST,
    'rbs_live': RBS_LIVE,
}


class Command(BaseCommand):
    help = 'Check for the required settings of billing app'
    args = PAYMENT_GATEWAYS.keys()

    def handle(self, *args, **kwargs):
        check_for_gateway = args or PAYMENT_GATEWAYS.keys()

        for gateway in check_for_gateway:
            if gateway not in PAYMENT_GATEWAYS:
                raise CommandError('Invalid payment gateway option %s, valid gateway options are %s' % (gateway, PAYMENT_GATEWAYS.keys()))
            required_settings = PAYMENT_GATEWAYS[gateway]

            if isinstance(required_settings, dict):
                if 'optional' in required_settings:
                    print '%s takes optional parameter %s' % (gateway, required_settings['optional'])
                required_settings = required_settings['required']

            for rs in required_settings:
                try:
                    getattr(settings, rs)
                except AttributeError:
                    # raising CommandError because the error message display is neat
                    raise CommandError('Missing parameter %s in settings for %s gateway' % (rs, gateway))
        return '0 errors'

########NEW FILE########
__FILENAME__ = amazon_fps_models
from django.db import models


class AmazonFPSResponse(models.Model):
    """ See This doc for a list of fields available, and what they mean.
    http://docs.aws.amazon.com/AmazonFPS/latest/FPSAPIReference/AWSFPSIPNDetails.html """
    buyerEmail = models.EmailField()
    buyerName = models.CharField(max_length=75)
    callerReference = models.CharField(max_length=100)
    notificationType = models.CharField(max_length=50)
    operation = models.CharField(max_length=20)
    paymentMethod = models.CharField(max_length=5)
    recipientEmail = models.EmailField()
    recipientName = models.CharField(max_length=75)
    statusCode = models.CharField(max_length=50)
    statusMessage = models.TextField()
    # Because currency is sent along
    transactionAmount = models.CharField(max_length=20)
    transactionDate = models.DateTimeField()
    transactionId = models.CharField(max_length=50, db_index=True)
    transactionStatus = models.CharField(max_length=50)

    customerEmail = models.EmailField(blank=True, null=True)
    customerName = models.CharField(max_length=75, blank=True, null=True)
    # Address fields
    addressFullName = models.CharField(max_length=100, blank=True, null=True)
    addressLine1 = models.CharField(max_length=100, blank=True, null=True)
    addressLine2 = models.CharField(max_length=100, blank=True, null=True)
    addressState = models.CharField(max_length=50, blank=True, null=True)
    addressZip = models.CharField(max_length=25, blank=True, null=True)
    addressCountry = models.CharField(max_length=25, blank=True, null=True)
    addressPhone = models.CharField(max_length=25, blank=True, null=True)

    def __unicode__(self):
        return "%s : %s" % (self.transactionId, self.statusCode)

    class Meta:
        app_label = __name__.split(".")[0]

########NEW FILE########
__FILENAME__ = authorize_models
from django.db import models

# Response Codes
# APPROVED, DECLINED, ERROR, FRAUD_REVIEW = 1, 2, 3, 4


class AuthorizeAIMResponse(models.Model):
    RESPONSE_CODES = [
        (1, 'Approved'),
        (2, 'Declined'),
        (3, 'Error'),
        (4, 'Held for Review'),
    ]
    ADDRESS_VERIFICATION_RESPONSE = [
        ('A', 'Address(Street) matches,ZIP does not'),
        ('B', 'Address information not provided for AVS check'),
        ('E', 'AVS error'),
        ('G', 'Non-U.S. Card Issuing Bank'),
        ('N', 'No match on Address(Street) or ZIP'),
        ('P', 'AVS not applicable for this transactions'),
        ('R', 'Retry-System unavailable or timed out'),
        ('S', 'Service not supported by issuer'),
        ('U', 'Address information is unavailable'),
        ('W', 'Nine digit Zip matches, Address(Street) does not'),
        ('X', 'Address(Street) and nine digit ZIP match'),
        ('Y', 'Address(Street) and five digit ZIP match'),
        ('Z', 'Five digit Zip matches, Address(Street) does not'),
    ]
    CARD_CODE_RESPONSES = [
        ('', ''),
        ('M', 'Match'),
        ('N', 'No Match'),
        ('P', 'Not Processed'),
        ('S', 'Should have been present'),
        ('U', 'Issuer unable to process request'),
    ]
    response_code = models.IntegerField(choices=RESPONSE_CODES)
    response_reason_code = models.IntegerField(blank=True)
    response_reason_text = models.TextField(blank=True)
    authorization_code = models.CharField(max_length=8)
    address_verification_response = models.CharField(max_length='8', choices=ADDRESS_VERIFICATION_RESPONSE)
    transaction_id = models.CharField(max_length=64)
    invoice_number = models.CharField(max_length=64, blank=True)
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    method = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(max_length=255, blank=True)
    customer_id = models.CharField(max_length=64, blank=True)

    first_name = models.CharField(max_length=64, blank=True)
    last_name = models.CharField(max_length=64, blank=True)
    company = models.CharField(max_length=64, blank=True)
    address = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=64, blank=True)
    zip_code = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    fax = models.CharField(max_length=64, blank=True)
    email = models.EmailField()

    shipping_first_name = models.CharField(max_length=64, blank=True)
    shipping_last_name = models.CharField(max_length=64, blank=True)
    shipping_company = models.CharField(max_length=64, blank=True)
    shipping_address = models.CharField(max_length=64, blank=True)
    shipping_city = models.CharField(max_length=64, blank=True)
    shipping_state = models.CharField(max_length=64, blank=True)
    shipping_zip_code = models.CharField(max_length=64, blank=True)
    shipping_country = models.CharField(max_length=64, blank=True)

    card_code_response = models.CharField(max_length='8', choices=CARD_CODE_RESPONSES, help_text=u'Card Code Verification response')

    class Meta:
        app_label = __name__.split(".")[0]

    def __unicode__(self):
        return "%s, $%s" % (self.get_response_code_display(), self.amount)

########NEW FILE########
__FILENAME__ = eway_models
from django.db import models


class EwayResponse(models.Model):
    pass

########NEW FILE########
__FILENAME__ = gc_models
from django.db import models


class GCNewOrderNotification(models.Model):
    notify_type = models.CharField(max_length=255, blank=True)
    serial_number = models.CharField(max_length=255)
    google_order_number = models.CharField(max_length=255)
    buyer_id = models.CharField(max_length=255)

    # Private merchant data
    private_data = models.CharField(max_length=255, blank=True)

    # Buyer Shipping Address details
    shipping_contact_name = models.CharField(max_length=255, blank=True)
    shipping_address1 = models.CharField(max_length=255, blank=True)
    shipping_address2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=255, blank=True)
    shipping_postal_code = models.CharField(max_length=255, blank=True)
    shipping_region = models.CharField(max_length=255, blank=True)
    shipping_country_code = models.CharField(max_length=255, blank=True)
    shipping_email = models.EmailField()
    shipping_company_name = models.CharField(max_length=255, blank=True)
    shipping_fax = models.CharField(max_length=255, blank=True)
    shipping_phone = models.CharField(max_length=255, blank=True)

    # Buyer Billing Address details
    billing_contact_name = models.CharField(max_length=255, blank=True)
    billing_address1 = models.CharField(max_length=255, blank=True)
    billing_address2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=255, blank=True)
    billing_postal_code = models.CharField(max_length=255, blank=True)
    billing_region = models.CharField(max_length=255, blank=True)
    billing_country_code = models.CharField(max_length=255, blank=True)
    billing_email = models.EmailField()
    billing_company_name = models.CharField(max_length=255, blank=True)
    billing_fax = models.CharField(max_length=255, blank=True)
    billing_phone = models.CharField(max_length=255, blank=True)

    # Buyer marketing preferences, bool marketing email allowed
    marketing_email_allowed = models.BooleanField(default=False)

    num_cart_items = models.IntegerField()
    cart_items = models.TextField()

    # Order Adjustment details
    total_tax = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    total_tax_currency = models.CharField(max_length=255, blank=True)
    adjustment_total = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    adjustment_total_currency = models.CharField(max_length=255, blank=True)

    order_total = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    order_total_currency = models.CharField(max_length=255, blank=True)

    financial_order_state = models.CharField(max_length=255, blank=True)
    fulfillment_order_state = models.CharField(max_length=255, blank=True)

    # u'timestamp': [u'2010-10-04T14:05:39.868Z'],
    # timestamp = models.DateTimeField(blank=True, null=True)
    timestamp = models.CharField(max_length=64, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = __name__.split(".")[0]

########NEW FILE########
__FILENAME__ = paylane_models
# -*- coding: utf-8 -*-
# vim:tabstop=4:expandtab:sw=4:softtabstop=4

from django.db import models


class PaylaneTransaction(models.Model):
    transaction_date = models.DateTimeField(auto_now_add=True)
    amount = models.FloatField()
    customer_name = models.CharField(max_length=200)
    customer_email = models.CharField(max_length=200)
    product = models.CharField(max_length=200)
    success = models.BooleanField(default=False)
    error_code = models.IntegerField(default=0)
    error_description = models.CharField(max_length=300, blank=True)
    acquirer_error = models.CharField(max_length=40, blank=True)
    acquirer_description = models.CharField(max_length=300, blank=True)

    def __unicode__(self):
        return u'Transaction for %s (%s)' % (self.customer_name, self.customer_email)

    class Meta:
        app_label = __name__.split(".")[0]


class PaylaneAuthorization(models.Model):
    sale_authorization_id = models.BigIntegerField(db_index=True)
    first_authorization = models.BooleanField(default=False)
    transaction = models.OneToOneField(PaylaneTransaction)

    def __unicode__(self):
        return u'Authorization: %s' % (self.sale_authorization_id)

    class Meta:
        app_label = __name__.split(".")[0]

########NEW FILE########
__FILENAME__ = pin_models
from django.db import models
from django.conf import settings

User = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class PinCard(models.Model):
    token = models.CharField(max_length=32, db_index=True, editable=False)
    display_number = models.CharField(max_length=20, editable=False)
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    scheme = models.CharField(max_length=20, editable=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    address_city = models.CharField(max_length=255)
    address_postcode = models.CharField(max_length=20)
    address_state = models.CharField(max_length=255)
    address_country = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, related_name='pin_cards', blank=True, null=True)

    def __unicode__(self):
        return 'Card %s' % self.display_number

    class Meta:
        app_label = __name__.split(".")[0]


class PinCustomer(models.Model):
    token = models.CharField(unique=True, max_length=32)
    card = models.ForeignKey("billing.PinCard", related_name='customers')
    email = models.EmailField()
    created_at = models.DateTimeField()
    user = models.OneToOneField(User, related_name='pin_customer', blank=True, null=True)

    def __unicode__(self):
        return 'Customer %s' % self.email

    class Meta:
        app_label = __name__.split(".")[0]


class PinCharge(models.Model):
    token = models.CharField(unique=True, max_length=32, editable=False)
    card = models.ForeignKey("billing.PinCard", related_name='charges', editable=False)
    customer = models.ForeignKey("billing.PinCustomer", related_name='customers', null=True, blank=True, editable=False)
    success = models.BooleanField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3)
    description = models.CharField(max_length=255)
    email = models.EmailField()
    ip_address = models.IPAddressField()
    created_at = models.DateTimeField()
    status_message = models.CharField(max_length=255)
    error_message = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, related_name='pin_charges', blank=True, null=True)

    def __unicode__(self):
        return 'Charge %s' % self.email

    class Meta:
        app_label = __name__.split(".")[0]


class PinRefund(models.Model):
    token = models.CharField(unique=True, max_length=32)
    charge = models.ForeignKey("billing.PinCharge", related_name='refunds')
    success = models.BooleanField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3)
    created_at = models.DateTimeField()
    status_message = models.CharField(max_length=255)
    error_message = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, related_name='pin_refunds', blank=True, null=True)

    def __unicode__(self):
        return 'Refund %s' % self.charge.email

    class Meta:
        app_label = __name__.split(".")[0]

########NEW FILE########
__FILENAME__ = world_pay_models
from django.db import models


class WorldPayResponse(models.Model):
    # merchant details
    installation_id = models.CharField(max_length=64)
    company_name = models.CharField(max_length=255, blank=True, null=True)

    # purchase details sent by merchant
    cart_id = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=64)

    # HTML string produced from the amount and currency
    # that were submitted to initiate the payment
    amount_string = models.CharField(max_length=64)
    auth_mode = models.CharField(max_length=64)
    test_mode = models.CharField(max_length=64)

    # transaction details
    transaction_id = models.CharField(max_length=64)
    transaction_status = models.CharField(max_length=64)
    transaction_time = models.CharField(max_length=64)
    auth_amount = models.DecimalField(max_digits=16, decimal_places=2)
    auth_currency = models.CharField(max_length=64)
    auth_amount_string = models.CharField(max_length=64)
    raw_auth_message = models.CharField(max_length=255)
    raw_auth_code = models.CharField(max_length=64)

    # billing address of the user
    name = models.CharField(max_length=255)
    address = models.TextField()
    post_code = models.CharField(max_length=64)
    country_code = models.CharField(max_length=64)
    country = models.CharField(max_length=64)
    phone = models.CharField(u'Phone number', max_length=64, blank=True)
    fax = models.CharField(u'Fax number', max_length=64, blank=True)
    email = models.EmailField()

    # future pay id, for recurring payments
    future_pay_id = models.CharField(max_length=64, blank=True)

    card_type = models.CharField(max_length=64, blank=True)
    ip_address = models.IPAddressField(blank=True, null=True)

    class Meta:
        app_label = __name__.split(".")[0]

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

transaction_started = Signal()

transaction_was_successful = Signal(providing_args=["type", "response"])
transaction_was_unsuccessful = Signal(providing_args=["type", "response"])

########NEW FILE########
__FILENAME__ = billing_tags
from django import template
from django.template.loader import render_to_string

register = template.Library()


class BillingIntegrationNode(template.Node):
    def __init__(self, integration):
        self.integration = template.Variable(integration)

    def render(self, context):
        int_obj = self.integration.resolve(context)
        form_str = render_to_string(
                int_obj.template, {
                    "integration": int_obj
                },
                context)
        return form_str

@register.tag
def render_integration(parser, token):
    try:
        tag, int_obj = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r was expecting a single argument" %token.split_contents()[0])
    return BillingIntegrationNode(int_obj)

########NEW FILE########
__FILENAME__ = jinja2_tags
from coffin.template import Library
from django.template.loader import render_to_string
from jinja2 import nodes
from jinja2.ext import Extension


register = Library()


class MerchantExtension(Extension):

    tags = set(['render_integration'])

    def parse(self, parser):
        stream = parser.stream
        lineno = stream.next().lineno

        obj = parser.parse_expression()
        call_node = self.call_method('render_integration', args=[obj])

        return nodes.Output([call_node]).set_lineno(lineno)

    @classmethod
    def render_integration(self, obj):
        form_str = render_to_string(obj.template, {'integration': obj})
        return form_str

register.tag(MerchantExtension)

########NEW FILE########
__FILENAME__ = amazon_fps_tests
from xml.dom import minidom
from urllib2 import urlparse

from django.conf import settings
from django.test import TestCase
from django.template import Template, Context
from django.utils.unittest.case import skipIf

from billing import get_integration


@skipIf(not settings.MERCHANT_SETTINGS.get("amazon_fps", None), "gateway not configured")
class AmazonFPSTestCase(TestCase):
    urls = "billing.tests.test_urls"

    def setUp(self):
        self.fps = get_integration("amazon_fps")
        self.fields = {
            "callerReference": "100",
            "paymentReason": "Digital Download",
            "pipelineName": "SingleUse",
            "transactionAmount": '30',
            "returnURL": "http://localhost/fps/fps-return-url/",
        }
        self.fps.add_fields(self.fields)

    def testLinkGen(self):
        tmpl = Template("{% load render_integration from billing_tags %}{% render_integration obj %}")
        html = tmpl.render(Context({"obj": self.fps}))
        # get the integration link url
        dom = minidom.parseString(html)
        url = dom.getElementsByTagName('a')[0].attributes['href'].value
        parsed = urlparse.urlparse(url)
        query_dict = dict(urlparse.parse_qsl(parsed.query))

        self.assertEquals(parsed.scheme, 'https')
        self.assertEquals(parsed.netloc, 'authorize.payments-sandbox.amazon.com')
        self.assertEquals(parsed.path, '/cobranded-ui/actions/start')

        self.assertDictContainsSubset(self.fields, query_dict)
        self.assertEquals(query_dict['callerKey'], settings.MERCHANT_SETTINGS['amazon_fps']['AWS_ACCESS_KEY'])

########NEW FILE########
__FILENAME__ = authorize_net_tests
import mock
import urllib2

from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_gateway, CreditCard
from billing.signals import *
from billing.models import AuthorizeAIMResponse
from billing.gateway import CardNotSupported
from billing.gateways.authorize_net_gateway import MockAuthorizeAIMResponse
from billing.utils.credit_card import Visa


@skipIf(not settings.MERCHANT_SETTINGS.get("authroize_net", None), "gateway not configured")
class AuthorizeNetAIMGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("authorize_net")
        self.merchant.test_mode = True
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2020,
                                      number="4222222222222",
                                      verification_value="100")

    def testCardSupported(self):
        self.credit_card.number = "5019222222222222"
        self.assertRaises(CardNotSupported,
                          lambda: self.merchant.purchase(1000, self.credit_card))

    def testCardValidated(self):
        self.merchant.test_mode = False
        self.credit_card.number = "4222222222222123"
        self.assertFalse(self.merchant.validate_card(self.credit_card))

    def testCardType(self):
        self.merchant.validate_card(self.credit_card)
        self.assertEquals(self.credit_card.card_type, Visa)

    def testPurchase(self):
        resp = self.merchant.purchase(1, self.credit_card)
        self.assertEquals(resp["status"], "SUCCESS")
        # In test mode, the transaction ID from Authorize.net is 0
        self.assertEquals(resp["response"].transaction_id, "0")
        self.assertTrue(isinstance(resp["response"], AuthorizeAIMResponse))

    def testPaymentSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_successful.connect(receive)

        resp = self.merchant.purchase(1, self.credit_card)
        self.assertEquals(received_signals, [transaction_was_successful])

    def testPaymentUnSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        resp = self.merchant.purchase(6, self.credit_card)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

    def testCreditCardExpired(self):
        resp = self.merchant.purchase(8, self.credit_card)
        self.assertNotEquals(resp["status"], "SUCCESS")

    def testPurchaseURLError(self):
        with mock.patch('billing.gateways.authorize_net_gateway.urllib2.urlopen') as mock_urlopen:
            error_text = "Something bad happened :("
            mock_urlopen.side_effect = urllib2.URLError(error_text)
            resp = self.merchant.purchase(1, self.credit_card)
            self.assertEquals(resp["status"], "FAILURE")
            self.assertEquals(resp["response"].response_code, 5)
            self.assertEquals(resp["response"].response_reason_code, '1')
            self.assertTrue(error_text in resp["response"].response_reason_text)
            self.assertTrue(isinstance(resp["response"], MockAuthorizeAIMResponse))

########NEW FILE########
__FILENAME__ = base_tests
from django.conf import settings
from django.test import TestCase
from django.template import Template, Context, TemplateSyntaxError
from django.utils.unittest.case import skipIf

from billing.utils.credit_card import CreditCard
from billing import get_gateway, GatewayNotConfigured, get_integration, IntegrationNotConfigured


class MerchantTestCase(TestCase):

    @skipIf(not settings.MERCHANT_SETTINGS.get("authorize_net", None), "gateway not configured")
    def testCorrectClassLoading(self):
        gateway = get_gateway("authorize_net")
        self.assertEquals(gateway.display_name, "Authorize.Net")

    def testSettingAttributes(self):
        self.assertTrue(getattr(settings, "MERCHANT_SETTINGS", None) != None)
        self.assertTrue(isinstance(settings.MERCHANT_SETTINGS, dict))

    def testRaiseExceptionNotConfigured(self):
        original_settings = settings.MERCHANT_SETTINGS
        settings.MERCHANT_SETTINGS = {
            "google_checkout": {
                "MERCHANT_ID": '',
                "MERCHANT_KEY": ''
                }
            }

        # Test if we can import any other gateway or integration
        self.assertRaises(IntegrationNotConfigured, lambda: get_integration("stripe"))
        self.assertRaises(GatewayNotConfigured, lambda: get_gateway("authorize_net"))
        settings.MERCHANT_SETTINGS = original_settings

    def testTemplateTagLoad(self):
        original_settings = settings.MERCHANT_SETTINGS
        settings.MERCHANT_SETTINGS = {
            "google_checkout": {
                "MERCHANT_ID": '',
                "MERCHANT_KEY": ''
                }
            }

        # Raises TemplateSyntaxError: Invalid Block Tag
        self.assertRaises(TemplateSyntaxError, lambda: Template("{% load render_integration from billing_tags %}{% stripe obj %}"))

        tmpl = Template("{% load render_integration from billing_tags %}{% render_integration obj %}")
        gc = get_integration("google_checkout")
        fields = {"items": [{
                    "name": "name of the item",
                    "description": "Item description",
                    "amount": 1,
                    "id": "999AXZ",
                    "currency": "USD",
                    "quantity": 1,
                    }],
                  "return_url": "http://127.0.0.1:8000/offsite/google-checkout/",
                  }
        gc.add_fields(fields)
        self.assertTrue(len(tmpl.render(Context({"obj": gc}))) > 0)

        settings.MERCHANT_SETTINGS = original_settings


class CreditCardTestCase(TestCase):
    def test_constructor(self):
        opts = dict(number='x', year=2000, month=1, verification_value='123')
        self.assertRaises(TypeError, lambda: CreditCard(**opts))
        self.assertRaises(TypeError, lambda: CreditCard(first_name='x', **opts))
        self.assertRaises(TypeError, lambda: CreditCard(last_name='y', **opts))
        c = CreditCard(first_name='x', last_name='y', **opts)
        self.assertEqual(c.cardholders_name, None)
        c2 = CreditCard(cardholders_name='z', **opts)
        self.assertEqual(c2.cardholders_name, 'z')

########NEW FILE########
__FILENAME__ = beanstream_tests
from datetime import date

from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_gateway, CreditCard
from billing.signals import *
from billing.gateway import CardNotSupported
from billing.utils.credit_card import Visa

from beanstream.billing import Address


@skipIf(not settings.MERCHANT_SETTINGS.get("beanstream", None), "gateway not configured")
class BeanstreamGatewayTestCase(TestCase):
    approved_cards = {'visa': {'number':      '4030000010001234', 'cvd': '123'},
                       '100_visa': {'number': '4504481742333', 'cvd': '123'},
                       'vbv_visa': {'nubmer': '4123450131003312', 'cvd': '123', 'vbv': '12345'},
                       'mc1': {'number': '5100000010001004', 'cvd': '123'},
                       'mc2': {'number': '5194930004875020', 'cvd': '123'},
                       'mc3': {'number': '5123450000002889', 'cvd': '123'},
                       '3d_mc': {'number': '5123450000000000', 'cvd': '123', 'passcode': '12345'},
                       'amex': {'number': '371100001000131', 'cvd': '1234'},
                       'discover': {'number': '6011500080009080', 'cvd': '123'},
                      }
    declined_cards = {'visa': {'number': '4003050500040005', 'cvd': '123'},
                       'mc': {'number': '5100000020002000', 'cvd': '123'},
                       'amex': {'number': '342400001000180', 'cvd': '1234'},
                       'discover': {'number': '6011000900901111', 'cvd': '123'},
                      }

    def setUp(self):
        self.merchant = get_gateway("beanstream")
        self.merchant.test_mode = True
        self.billing_address = Address(
            'John Doe',
            'john.doe@example.com',
            '555-555-5555',
            '123 Fake Street',
            '',
            'Fake City',
            'ON',
            'A1A1A1',
            'CA')

    def ccFactory(self, number, cvd):
        today = date.today()
        return CreditCard(first_name = "John",
                          last_name = "Doe",
                          month = str(today.month),
                          year = str(today.year + 1),
                          number = number,
                          verification_value = cvd)

    def testCardSupported(self):
        credit_card = self.ccFactory("5019222222222222", "100")
        self.assertRaises(CardNotSupported, self.merchant.purchase,
                          1000, credit_card)

    def testCardValidated(self):
        self.merchant.test_mode = False
        credit_card = self.ccFactory("4222222222222123", "100")
        self.assertFalse(self.merchant.validate_card(credit_card))

    def testCardType(self):
        credit_card = self.ccFactory("4222222222222", "100")
        self.merchant.validate_card(credit_card)
        self.assertEquals(credit_card.card_type, Visa)

    def testCreditCardExpired(self):
        credit_card = CreditCard(first_name="John",
                          last_name="Doe",
                          month=12, year=2011, # Use current date time to generate a date in the future
                          number = self.approved_cards["visa"]["number"],
                          verification_value = self.approved_cards["visa"]["cvd"])
        resp = self.merchant.purchase(8, credit_card)
        self.assertNotEquals(resp["status"], "SUCCESS")

    def testPurchase(self):
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        response = self.merchant.purchase('1.00', credit_card)
        self.assertEquals(response["status"], "FAILURE")
        self.assertTrue(len(response["response"].resp["errorFields"]) > 0)
        response = self.merchant.purchase('1.00', credit_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)
        declined_card = self.ccFactory("4003050500040005", 123)
        response = self.merchant.purchase('1.00', declined_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(response["status"], "FAILURE")
        self.assertEquals(response["response"].approved(), False)
        self.assertEquals(response["response"].resp["messageId"], ["7"])

    def testPaymentSuccessfulSignal(self):
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])

        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_successful.connect(receive)

        resp = self.merchant.purchase(10, credit_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(received_signals, [transaction_was_successful])

    def testPaymentUnSuccessfulSignal(self):
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        resp = self.merchant.purchase(10, credit_card)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

    def testPurchaseVoid(self):
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        response = self.merchant.purchase('1.00', credit_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)
        response = self.merchant.void({"txnid": txnid, "amount":'1.00'})
        self.assertEquals(response["status"], "SUCCESS")

    def testPurchaseReturn(self):
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        response = self.merchant.purchase('5.00', credit_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)
        response = self.merchant.credit('4.00', txnid)
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)

    def testAuthorize(self):
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        response = self.merchant.authorize('1.00', credit_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)

    def testAuthorizeComplete(self):
        ''' Preauth and complete '''
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        response = self.merchant.authorize('1.00', credit_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)
        response = self.merchant.capture('1.00', txnid)
        self.assertEquals(response["status"], "SUCCESS")

    def testAuthorizeCancel(self):
        ''' Preauth and cancel '''
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        response = self.merchant.authorize('1.00', credit_card, {"billing_address": {
                    "name": "Test user",
                    "email": "test@example.com",
                    "phone": "123456789",
                    "city": "Hyd",
                    "state": "AP",
                    "country": "IN",
                    "address1": "ABCD"}})
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)
        response = self.merchant.unauthorize('0.5', txnid)
        self.assertEquals(response["status"], "SUCCESS")

    def testCreateProfile(self):
        if not self.merchant.beangw.payment_profile_passcode:
            self.skipTest("beanstream - missing PAYMENT_PROFILE_PASSCODE")
        credit_card = self.ccFactory(self.approved_cards["visa"]["number"],
                                     self.approved_cards["visa"]["cvd"])
        response = self.merchant.store(credit_card, {"billing_address": self.billing_address})
        self.assertEquals(response["status"], "SUCCESS")

        customer_code = response["response"].resp.customer_code()
        self.assertIsNotNone(customer_code)

        response = self.merchant.purchase('1.00', None, {"customer_code": customer_code})
        self.assertEquals(response["status"], "SUCCESS")
        txnid = response["response"].resp["trnId"][0]
        self.assertIsNotNone(txnid)

########NEW FILE########
__FILENAME__ = bitcoin_tests
from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_gateway
from billing.signals import transaction_was_successful, transaction_was_unsuccessful


TEST_AMOUNT = 0.01


@skipIf(not settings.MERCHANT_SETTINGS.get("bitcoin", None), "gateway not configured")
class BitcoinGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("bitcoin")
        self.address = self.merchant.get_new_address()

    def testPurchase(self):
        self.merchant.connection.sendtoaddress(self.address, TEST_AMOUNT)
        resp = self.merchant.purchase(TEST_AMOUNT, self.address)
        self.assertEquals(resp['status'], 'SUCCESS')

    def testPaymentSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_successful.connect(receive)

        self.merchant.connection.sendtoaddress(self.address, TEST_AMOUNT)
        self.merchant.purchase(TEST_AMOUNT, self.address)
        self.assertEquals(received_signals, [transaction_was_successful])

    def testPaymentUnSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        self.merchant.purchase(0.001, self.address)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

########NEW FILE########
__FILENAME__ = braintree_payments_tests
import braintree

from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_gateway, CreditCard
from billing.signals import *
from billing.gateway import CardNotSupported, InvalidData
from billing.utils.credit_card import Visa


@skipIf(not settings.MERCHANT_SETTINGS.get("braintree_payments", None), "gateway not configured")
class BraintreePaymentsGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("braintree_payments")
        self.merchant.test_mode = True
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2020,
                                      number="4111111111111111",
                                      verification_value="100")

    def assertBraintreeResponseSuccess(self, resp, msg=None):
        if resp['status'] == "FAILURE":
            standardMsg = resp['response'].message
            self.fail(self._formatMessage(msg, standardMsg))
        else:
            self.assertEquals(resp['status'], "SUCCESS")

    def assertBraintreeResponseFailure(self, resp, msg=None):
        self.assertEquals(resp['status'], "FAILURE")

    def testCardSupported(self):
        self.credit_card.number = "5019222222222222"
        self.assertRaises(CardNotSupported,
                          lambda: self.merchant.purchase(1000, self.credit_card))

    def testCardType(self):
        self.merchant.validate_card(self.credit_card)
        self.assertEquals(self.credit_card.card_type, Visa)

    def testPurchase(self):
        resp = self.merchant.purchase(5, self.credit_card)
        self.assertBraintreeResponseSuccess(resp)

    def testFailedPurchase(self):
        resp = self.merchant.purchase(2001, self.credit_card)
        self.assertBraintreeResponseFailure(resp)

    def testDeclinedPurchase(self):
        resp = self.merchant.purchase(2900, self.credit_card)
        self.assertBraintreeResponseFailure(resp)

    def testPaymentSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_successful.connect(receive)

        resp = self.merchant.purchase(1, self.credit_card)
        self.assertEquals(received_signals, [transaction_was_successful])

    def testPaymentUnSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        resp = self.merchant.purchase(2000, self.credit_card)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

    def testCreditCardExpired(self):
        credit_card = CreditCard(first_name="Test", last_name="User",
                                 month=10, year=2011,
                                 number="4000111111111115",
                                 verification_value="100")
        resp = self.merchant.purchase(2004, credit_card)
        self.assertNotEquals(resp["status"], "SUCCESS")

    def testAuthorizeAndCapture(self):
        resp = self.merchant.authorize(100, self.credit_card)
        self.assertBraintreeResponseSuccess(resp)
        resp = self.merchant.capture(50, resp["response"].transaction.id)
        self.assertBraintreeResponseSuccess(resp)

    # Need a way to test this. Requires delaying the status to either
    # "settled" or "settling"
    # def testAuthorizeAndRefund(self):
    #     resp = self.merchant.purchase(100, self.credit_card)
    #     self.assertEquals(resp["status"], "SUCCESS")
    #     response = self.merchant.credit(50, resp["response"].transaction.id)
    #     self.assertEquals(response["status"], "SUCCESS")

    def testAuthorizeAndVoid(self):
        resp = self.merchant.authorize(105, self.credit_card)
        self.assertBraintreeResponseSuccess(resp)
        resp = self.merchant.void(resp["response"].transaction.id)
        self.assertBraintreeResponseSuccess(resp)

    def testStoreMissingCustomer(self):
        self.assertRaises(InvalidData,
                          lambda: self.merchant.store(self.credit_card, {}))

    def testStoreWithoutBillingAddress(self):
        options = {
            "customer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                },
            }
        resp = self.merchant.store(self.credit_card, options=options)
        self.assertBraintreeResponseSuccess(resp)
        self.assertEquals(resp["response"].customer.credit_cards[0].expiration_date,
                          "%s/%s" % (self.credit_card.month,
                                    self.credit_card.year))
        self.assertTrue(getattr(resp["response"].customer.credit_cards[0], "customer_id"))
        self.assertTrue(getattr(resp["response"].customer.credit_cards[0], "token"))

    def testStoreWithBillingAddress(self):
        options = {
            "customer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                },
            "billing_address": {
                "name": "Johnny Doe",
                "company": "",
                "email": "johnny.doe@example.com",
                "address1": "Street #1",
                "address2": "House #2",
                "city": "Timbuktu",
                "country": "United States of America",
                "zip": "110011"
                }
            }
        resp = self.merchant.store(self.credit_card, options=options)
        self.assertBraintreeResponseSuccess(resp)
        self.assertTrue(getattr(resp["response"].customer.credit_cards[0], "billing_address"))
        billing_address = resp["response"].customer.credit_cards[0].billing_address
        self.assertEquals(billing_address.country_code_alpha2, "US")
        self.assertEquals(billing_address.postal_code, "110011")
        self.assertEquals(billing_address.street_address, "Street #1")
        self.assertEquals(billing_address.extended_address, "House #2")
        self.assertEquals(billing_address.locality, "Timbuktu")

    def testUnstore(self):
        options = {
            "customer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                },
            }
        resp = self.merchant.store(self.credit_card, options=options)
        self.assertBraintreeResponseSuccess(resp)
        resp = self.merchant.unstore(resp["response"].customer.credit_cards[0].token)
        self.assertBraintreeResponseSuccess(resp)

    # The below tests require 'test_plan' to be created in the sandbox
    # console panel. This cannot be created by API at the moment
    def testRecurring1(self):
        options = {
            "customer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                },
            "recurring": {
                "plan_id": "test_plan"
                },
            }
        resp = self.merchant.recurring(10, self.credit_card, options=options)
        self.assertBraintreeResponseSuccess(resp)
        subscription = resp["response"].subscription
        self.assertEquals(subscription.status,
                          braintree.Subscription.Status.Active)

    def testRecurring2(self):
        options = {
            "customer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                },
            "recurring": {
                "plan_id": "test_plan",
                "price": 15
                },
            }
        resp = self.merchant.recurring(15, self.credit_card, options=options)
        self.assertBraintreeResponseSuccess(resp)
        subscription = resp["response"].subscription
        self.assertEquals(subscription.price, 15)

    def testRecurring3(self):
        options = {
            "customer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                },
            "recurring": {
                "plan_id": "test_plan",
                "trial_duration": 2,
                "trial_duration_unit": "month",
                "number_of_billing_cycles": 12,
                },
            }
        resp = self.merchant.recurring(20, self.credit_card, options=options)
        self.assertBraintreeResponseSuccess(resp)
        subscription = resp["response"].subscription
        self.assertEquals(subscription.number_of_billing_cycles, 12)

########NEW FILE########
__FILENAME__ = braintree_payments_tr_tests
"""
Braintree Payments Transparent Redirect Tests.
"""
from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_integration


@skipIf(not settings.MERCHANT_SETTINGS.get("braintree_payments", None), "gateway not configured")
class BraintreePaymentsIntegrationTestCase(TestCase):
    urls = "billing.tests.test_urls"

    def setUp(self):
        self.bp = get_integration("braintree_payments")
        fields = {
            "transaction": {
                "type": "sale",
                "amount": "10.00",
                "order_id": 1,
                "customer": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    },
                }
            }
        self.bp.add_fields(fields)

    def testFormFields(self):
        self.assertEquals(self.bp.fields, {"transaction__type": "sale",
                                           "transaction__amount": "10.00",
                                           "transaction__order_id": 1,
                                           "transaction__customer__first_name": "John",
                                           "transaction__customer__last_name": "Doe",
                                           "transaction__customer__email": "john.doe@example.com"})

    # Need to think about the tests below because they are dynamic because
    # of the hashes and the timestamps.
    # def testFormGen(self):
    #     tmpl = Template("{% load braintree_payments from braintree_payments_tags %}{% braintree_payments obj %}")
    #     form = tmpl.render(Context({"obj": self.bp}))
    #     print self.bp.generate_form()
    #     pregen_form = """""" %(settings.BRAINTREE_MERCHANT_ACCOUNT_ID)
    #     self.assertEquals(pregen_form, strip_spaces_between_tags(form).strip())

    # def testFormGen2(self):
    #     tmpl = Template("{% load braintree_payments from braintree_payments_tags %}{% braintree_payments obj %}")
    #     form = tmpl.render(Context({"obj": self.bp}))
    #     pregen_form = u"""%s""" %(settings.BRAINTREE_MERCHANT_ACCOUNT_ID)
    #     self.assertEquals(pregen_form, strip_spaces_between_tags(form).strip())

########NEW FILE########
__FILENAME__ = chargebee_tests
from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_gateway, CreditCard
from billing.signals import transaction_was_successful, \
    transaction_was_unsuccessful


@skipIf(not settings.MERCHANT_SETTINGS.get("chargebee", None), "gateway not configured")
class ChargebeeGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("chargebee")
        self.merchant.test_mode = True
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2020,
                                      number="4111111111111111",
                                      verification_value="100")

    def testPurchase(self):
        # Purchase is a custom plan created that charges $1000 every 10 years.
        resp = self.merchant.purchase(1, self.credit_card, options = {"plan_id": "purchase"})
        self.assertEquals(resp["status"], "FAILURE")
        resp = self.merchant.purchase(1, self.credit_card,
                                      options = {"plan_id": "purchase",
                                                 "description": "Quick Purchase"})
        self.assertEquals(resp["status"], "SUCCESS")

    def testAuthorizeAndCapture(self):
        resp = self.merchant.authorize(100, self.credit_card,
                                       options = {"plan_id": "purchase",
                                                  "description": "Authorize"})
        self.assertEquals(resp["status"], "SUCCESS")
        response = self.merchant.capture(50, resp["response"]["subscription"]["id"],
                                         options = {"description": "Capture"})
        self.assertEquals(response["status"], "SUCCESS")

    def testAuthorizeAndVoid(self):
        resp = self.merchant.authorize(100, self.credit_card,
                                       options = {"plan_id": "purchase",
                                                  "description": "Authorize"})
        self.assertEquals(resp["status"], "SUCCESS")
        response = self.merchant.void(resp["response"]["subscription"]["id"])
        self.assertEquals(response["status"], "SUCCESS")

    def testPaymentSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_successful.connect(receive)

        resp = self.merchant.store(self.credit_card, options={"plan_id": "professional"})
        self.assertEquals(received_signals, [transaction_was_successful])

    def testPaymentUnSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        resp = self.merchant.store(self.credit_card)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

    def testCreditCardExpired(self):
        credit_card = CreditCard(first_name="Test", last_name="User",
                                 month=10, year=2011,
                                 number="4000111111111115",
                                 verification_value="100")
        resp = self.merchant.store(credit_card)
        self.assertNotEquals(resp["status"], "SUCCESS")

    def testStoreWithoutCreditCard(self):
        options = {
            "customer[first_name]": "John",
            "customer[last_name]": "Doe",
            "customer[email]": "john.doe@example.com",
            "plan_id": "professional"
            }
        resp = self.merchant.store(None, options=options)
        self.assertEquals(resp["status"], "SUCCESS")
        self.assertTrue(resp["response"]["customer"]["object"], "customer")
        self.assertTrue(resp["response"]["customer"]["first_name"], "John")
        self.assertTrue(resp["response"]["customer"]["last_name"], "Doe")
        self.assertTrue(resp["response"]["customer"]["email"], "john.doe@example.com")
        self.assertTrue(resp["response"]["customer"]["card_status"], "no_card")
        self.assertIsNotNone(resp["response"]["customer"]["id"])
        self.assertTrue(resp["response"]["subscription"]["plan_id"], "professional")
        self.assertEquals(resp["response"]["subscription"]["status"], "in_trial")

    def testStoreWithCreditCard(self):
        options = {
            "customer[first_name]": "John",
            "customer[last_name]": "Doe",
            "customer[email]": "john.doe@example.com",
            "plan_id": "professional"
            }
        resp = self.merchant.store(self.credit_card, options=options)
        self.assertEquals(resp["status"], "SUCCESS")
        self.assertTrue(resp["response"]["customer"]["object"], "customer")
        self.assertTrue(resp["response"]["customer"]["first_name"], "John")
        self.assertTrue(resp["response"]["customer"]["last_name"], "Doe")
        self.assertTrue(resp["response"]["customer"]["email"], "john.doe@example.com")
        self.assertTrue(resp["response"]["customer"]["card_status"], "valid")
        self.assertIsNotNone(resp["response"]["customer"]["id"])
        self.assertTrue(resp["response"]["subscription"]["plan_id"], "professional")
        self.assertEquals(resp["response"]["subscription"]["status"], "in_trial")

    def testUnstore(self):
        resp = self.merchant.store(self.credit_card, options={"plan_id": "professional"})
        self.assertEquals(resp["status"], "SUCCESS")
        response = self.merchant.unstore(resp["response"]["customer"]["id"])
        self.assertEquals(response["status"], "SUCCESS")
        self.assertEquals(response["response"]["subscription"]["status"], "cancelled")
        response = self.merchant.unstore("abcdef")
        self.assertEquals(response["status"], "FAILURE")
        self.assertEquals(response["response"]["http_status_code"], 404)
        self.assertEquals(response["response"]["error_msg"], "abcdef not found")

########NEW FILE########
__FILENAME__ = eway_tests
from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_gateway, CreditCard
from billing.signals import *
from billing.models import EwayResponse
from billing.gateway import CardNotSupported
from billing.utils.credit_card import Visa

fake_options = {
    "email": "testuser@fakedomain.com",
    "billing_address": {
        "name": "PayPal User",
        "address1": "Street 1",
        "city": "Mountain View",
        "state": "CA",
        "country": "US",
        "zip": "94043",
        "fax": "1234567890",
        "email": "testuser@fakedomain.com",
        "phone": "1234567890",
        "mobile": "1234567890",
        "customer_ref": "Blah",
        "job_desc": "Job",
        "comments": "comments",
        "url": "http://google.com.au/",
    },
    "invoice": "1234",
    "description": "Blah Blah!",
    "customer_details": {
        "customer_fname": "TEST",
        "customer_lname": "USER",
        "customer_address": "#43, abc",
        "customer_email": "abc@test.Com",
        "customer_postcode": 560041,
    },
    "payment_details": {
        "amount": 100,  # In cents
        "transaction_number": 3234,
        "inv_ref": 'REF1234',
        "inv_desc": "Please Ship ASASP",
    }
}

@skipIf(not settings.MERCHANT_SETTINGS.get("eway", None), "gateway not configured")
class EWayGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("eway")
        self.merchant.test_mode = True
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2020,
                                      number="4444333322221111",
                                      verification_value="100")

    def testCardSupported(self):
        self.credit_card.number = "5019222222222222"
        self.assertRaises(CardNotSupported,
                          lambda: self.merchant.purchase(1000, self.credit_card))

    def testCardValidated(self):
        self.merchant.test_mode = False
        self.credit_card.number = "4222222222222123"
        self.assertFalse(self.merchant.validate_card(self.credit_card))

    def testCardType(self):
        self.merchant.validate_card(self.credit_card)
        self.assertEquals(self.credit_card.card_type, Visa)

    def testPurchase(self):
        resp = self.merchant.purchase(100, self.credit_card,
                                      options=fake_options)
        self.assertEquals(resp["status"], "SUCCESS")
        self.assertNotEquals(resp["response"].ewayTrxnStatus, True)
        self.assertEquals(resp["response"].ewayTrxnError,
                          "00,Transaction Approved(Test Gateway)")
        self.assertNotEquals(resp["response"].ewayTrxnNumber, "0")
        self.assertTrue(resp["response"].ewayReturnAmount, "100")

    def testFailure(self):
        resp = self.merchant.purchase(105, self.credit_card,
                                      options=fake_options)
        self.assertEquals(resp["status"], "FAILURE")
        self.assertEquals(resp["response"].ewayTrxnError,
                          "05,Do Not Honour(Test Gateway)")
        self.assertNotEquals(resp["response"].ewayTrxnNumber, "0")
        self.assertTrue(resp["response"].ewayReturnAmount, "100")

    def testDirectPayment(self):
        credit_card_details = {
            'first_name': 'test fname',
            'last_name': 'test lname',
            'verification_value': '123',
            'number': '4444333322221111',
            'month': '7',
            'card_type': 'visa',
            'year': '2017'
        }
        resp = self.merchant.direct_payment(credit_card_details,
                                            options=fake_options)
        self.assertEquals(resp["status"], "SUCCESS")
        eway_response = resp["response"]["ewayResponse"]
        self.assertEquals(eway_response['ewayTrxnStatus'], 'True')
        self.assertEquals(eway_response["ewayReturnAmount"], "100")

    def testPaymentSuccessfulSignal(self):
        # Since in the test mode, all transactions are
        # failures, we need to be checking for transaction_was_unsuccessful
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        resp = self.merchant.purchase(1, self.credit_card,
                                      options=fake_options)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

    def testPaymentUnSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        resp = self.merchant.purchase(6, self.credit_card,
                                      options=fake_options)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

    def testCreditCardExpired(self):
        resp = self.merchant.purchase(8, self.credit_card,
                                      options=fake_options)
        self.assertNotEquals(resp["status"], "SUCCESS")

########NEW FILE########
__FILENAME__ = global_iris_tests
# -*- coding: utf-8 -*-
import random
import sys
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing.tests.utils import BetterXMLCompareMixin
from billing.gateway import get_gateway
from billing.gateways.global_iris_gateway import GlobalIrisGateway, CARD_NAMES
from billing.integrations.global_iris_real_mpi_integration import GlobalIrisRealMpiIntegration
from billing.signals import transaction_was_unsuccessful, transaction_was_successful
from billing.utils.credit_card import CreditCard, CardNotSupported, Visa


class Dummy200Response(object):
    def __init__(self, content):
        self.status_code = 200
        self.content = content


class GlobalIrisTestBase(object):

    def mk_gateway(self):
        return GlobalIrisGateway(
            config={'TEST': dict(SHARED_SECRET="mysecret",
                                 MERCHANT_ID="thestore",
                                 ACCOUNT="theaccount")
                    },
            test_mode=True)

    def mk_integration(self):
        return GlobalIrisRealMpiIntegration(
            config={'TEST': dict(SHARED_SECRET="mysecret",
                                 MERCHANT_ID="thestore",
                                 ACCOUNT="theaccount")
                    },
            test_mode=True)

    def get_visa_card(self):
        return CreditCard(first_name='Mickey',
                          last_name='Mouse',
                          month=7,
                          year=2035,
                          number='4903034000057389',
                          verification_value='123',
                          )

    def get_amex_card(self):
        return CreditCard(first_name='Donald',
                          last_name='Duck',
                          month=8,
                          year=2035,
                          number='374101012180018',
                          verification_value='4567',
                          )

    def get_order_id(self):
        # Need unique IDs for orders
        return str(datetime.now()).replace(':', '_').replace(' ', '_').replace('.', '_') + str(random.randint(0, sys.maxint))


@skipIf(not settings.MERCHANT_SETTINGS.get("global_iris", None), "gateway not configured")
class GlobalIrisGatewayTestCase(BetterXMLCompareMixin, GlobalIrisTestBase, TestCase):

    def test_request_xml(self):
        gateway = self.mk_gateway()
        card = CreditCard(first_name='Mickey',
                          last_name='Mouse',
                          month=7,
                          year=2014,
                          number='4903034000057389',
                          verification_value='123',
                          )
        gateway.validate_card(card)
        data = {
                'timestamp': datetime(2001, 4, 27, 12, 45, 23),
                'order_id': '345',
                'amount': Decimal('20.00'),
                'card': card,
                'customer': '567',
                'billing_address': {
                    'street_address': "45 The Way",
                    'post_code': "ABC 123",
                    'country': 'GB',
                    },
                'product_id': '678',
                'customer_ip_address': '123.4.6.23',
                'varref': 'abc',
                }

        xml = gateway.build_xml(data)

        self.assertXMLEqual(u"""<?xml version="1.0" encoding="UTF-8" ?>
<request timestamp="20010427124523" type="auth">
  <merchantid>thestore</merchantid>
  <account>theaccount</account>
  <channel>ECOM</channel>
  <orderid>345</orderid>
  <amount currency="GBP">2000</amount>
  <card>
    <number>4903034000057389</number>
    <expdate>0714</expdate>
    <chname>Mickey Mouse</chname>
    <type>VISA</type>
    <cvn>
      <number>123</number>
      <presind>1</presind>
    </cvn>
  </card>
  <autosettle flag="1" />
  <tssinfo>
    <custnum>567</custnum>
    <prodid>678</prodid>
    <varref>abc</varref>
    <custipaddress>123.4.6.23</custipaddress>
    <address type="billing">
      <code>123|45</code>
      <country>GB</country>
    </address>
  </tssinfo>
  <sha1hash>eeaeaf2751a86edcf0d77e906b2daa08929e7cbe</sha1hash>
</request>""".encode('utf-8'), xml)

        # Test when we have MPI data (in the format returned
        # from GlobalIris3dsVerifySig.proceed_with_auth)
        mpi_data = {'mpi':{'eci': '5',
                           'xid': 'crqAeMwkEL9r4POdxpByWJ1/wYg=',
                           'cavv': 'AAABASY3QHgwUVdEBTdAAAAAAAA=',
                    }}
        data.update(mpi_data)

        xml2 = gateway.build_xml(data)

        self.assertXMLEqual(u"""<?xml version="1.0" encoding="UTF-8" ?>
<request timestamp="20010427124523" type="auth">
  <merchantid>thestore</merchantid>
  <account>theaccount</account>
  <channel>ECOM</channel>
  <orderid>345</orderid>
  <amount currency="GBP">2000</amount>
  <card>
    <number>4903034000057389</number>
    <expdate>0714</expdate>
    <chname>Mickey Mouse</chname>
    <type>VISA</type>
    <cvn>
      <number>123</number>
      <presind>1</presind>
    </cvn>
  </card>
  <autosettle flag="1" />
  <mpi>
    <eci>5</eci>
    <cavv>AAABASY3QHgwUVdEBTdAAAAAAAA=</cavv>
    <xid>crqAeMwkEL9r4POdxpByWJ1/wYg=</xid>
  </mpi>
  <tssinfo>
    <custnum>567</custnum>
    <prodid>678</prodid>
    <varref>abc</varref>
    <custipaddress>123.4.6.23</custipaddress>
    <address type="billing">
      <code>123|45</code>
      <country>GB</country>
    </address>
  </tssinfo>
  <sha1hash>eeaeaf2751a86edcf0d77e906b2daa08929e7cbe</sha1hash>
</request>""".encode('utf-8'), xml2)


    def test_signature(self):
        gateway = self.mk_gateway()
        card = CreditCard(number='5105105105105100',
                          first_name='x',
                          last_name='x',
                          year='1', month='1',
                          verification_value='123')
        gateway.validate_card(card)
        config = gateway.get_config(card)
        sig = gateway.get_standard_signature(
            {
                'timestamp':'20010403123245',
                'amount_normalized':'29900',
                'order_id': 'ORD453-11',
                'currency': 'GBP',
                'card': card,
                }, config)
        self.assertEqual(sig, "9e5b49f4df33b52efa646cce1629bcf8e488f7bb")

    def test_parse_fail_xml(self):
        gateway = self.mk_gateway()
        fail_resp = Dummy200Response('<?xml version="1.0" ?>\r\n<response timestamp="20140212143606">\r\n<result>504</result>\r\n<message>There is no such merchant id.</message>\r\n<orderid>1</orderid>\r\n</response>\r\n')
        retval = gateway.handle_response(fail_resp, "purchase")
        self.assertEqual(retval['status'], 'FAILURE')
        self.assertEqual(retval['message'], 'There is no such merchant id.')
        self.assertEqual(retval['response_code'], "504")
        self.assertEqual(retval['response'], fail_resp)

    def test_parse_success_xml(self):
        gateway = self.mk_gateway()
        success_resp = Dummy200Response('<?xml version="1.0" encoding="UTF-8"?>\r\n\r\n<response timestamp="20140327170816">\r\n  <merchantid>wolfandbadgertest</merchantid>\r\n  <account>internet</account>\r\n  <orderid>2014-03-27_17_08_15_871579556348273697313729</orderid>\r\n  <authcode>12345</authcode>\r\n  <result>00</result>\r\n  <cvnresult>U</cvnresult>\r\n  <avspostcoderesponse>U</avspostcoderesponse>\r\n  <avsaddressresponse>U</avsaddressresponse>\r\n  <batchid>169005</batchid>\r\n  <message>[ test system ] Authorised</message>\r\n  <pasref>13959400966589445</pasref>\r\n  <timetaken>0</timetaken>\r\n  <authtimetaken>0</authtimetaken>\r\n  <cardissuer>\r\n    <bank>AIB BANK</bank>\r\n    <country>IRELAND</country>\r\n    <countrycode>IE</countrycode>\r\n    <region>EUR</region>\r\n  </cardissuer>\r\n  <tss>\r\n    <result>89</result>\r\n    <check id="1001">9</check>\r\n    <check id="1002">9</check>\r\n    <check id="1004">9</check>\r\n    <check id="1005">9</check>\r\n    <check id="1006">9</check>\r\n    <check id="1007">9</check>\r\n    <check id="1008">9</check>\r\n    <check id="1009">9</check>\r\n    <check id="1200">9</check>\r\n    <check id="2001">9</check>\r\n    <check id="2003">0</check>\r\n    <check id="3100">9</check>\r\n    <check id="3101">9</check>\r\n    <check id="3200">9</check>\r\n    <check id="1010">9</check>\r\n    <check id="3202">0</check>\r\n    <check id="1011">9</check>\r\n  </tss>\r\n  <sha1hash>cfb5882353fea0a06919c0f86d9f037b99434026</sha1hash>\r\n</response>\r\n')
        retval = gateway.handle_response(success_resp, "purchase")
        self.assertEqual(retval['status'], 'SUCCESS')
        self.assertEqual(retval['response_code'], '00')
        self.assertEqual(retval['avsaddressresponse'], 'U')
        self.assertEqual(retval['avspostcoderesponse'], 'U')
        self.assertEqual(retval['cvnresult'], 'U')
        self.assertEqual(retval['cardissuer'], {'bank': 'AIB BANK',
                                                'country': 'IRELAND',
                                                'countrycode': 'IE',
                                                'region': 'EUR',
                                                })


    def test_config_for_card_type(self):
        """
        Test that the GateWay object can pick the correct config depending on the card type.
        """
        gateway = GlobalIrisGateway(config={
                'LIVE': dict(SHARED_SECRET="mysecret",
                             MERCHANT_ID="thestore",
                             ACCOUNT="theaccount"),
                'LIVE_AMEX': dict(SHARED_SECRET="mysecret2",
                                  MERCHANT_ID="thestore",
                                  ACCOUNT="theaccountamex"),
                }, test_mode=False)

        vc = self.get_visa_card()
        self.assertTrue(gateway.validate_card(vc)) # needed for side effects

        ac = self.get_amex_card()
        self.assertTrue(gateway.validate_card(ac))

        self.assertEqual("theaccount", gateway.get_config(vc).account)
        self.assertEqual("theaccountamex", gateway.get_config(ac).account)

    def test_purchase_fail(self):
        received_signals = []
        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))
        transaction_was_unsuccessful.connect(receive)

        gateway = get_gateway('global_iris')
        card = self.get_visa_card()
        gateway.validate_card(card)
        response = gateway.purchase(Decimal("45.00"), card, options={'order_id': 1})
        # Difficult to test success, because we need dummy card numbers etc.
        # But we can at least test we aren't getting exceptions.
        self.assertEqual(response['status'], 'FAILURE')

        self.assertEqual(received_signals, [transaction_was_unsuccessful])

    def _get_test_cards(self):
        cards = []
        card_dicts = settings.MERCHANT_SETTINGS['global_iris']['TEST_CARDS']
        for card_dict in card_dicts:
            card_type = card_dict['TYPE']
            d = dict(first_name= 'Test',
                     last_name= 'Test',
                     month=1,
                     year=datetime.now().year + 2,
                     number=card_dict['NUMBER'],
                     verification_value="1234" if card_type == "AMEX" else "123")
            card = CreditCard(**d)
            card.expected_response_code = card_dict['RESPONSE_CODE']
            cards.append(card)
        return cards

    @skipIf('TEST' not in settings.MERCHANT_SETTINGS.get('global_iris', {})
            or 'TEST_CARDS' not in settings.MERCHANT_SETTINGS.get('global_iris', {}),
            "gateway not configured")

    def test_purchase_with_test_cards(self):
        # This test requires valid test numbers
        gateway = GlobalIrisGateway()
        if not gateway.test_mode:
            self.fail("MERCHANT_TEST_MODE must be true for running tests")

        for card in self._get_test_cards():
            received_signals = []
            def success(sender, **kwargs):
                received_signals.append(kwargs.get("signal"))
            transaction_was_successful.connect(success)

            def fail(sender, **kwargs):
                received_signals.append(kwargs.get("signal"))
            transaction_was_unsuccessful.connect(fail)

            # Cards with invalid numbers will get caught by billing code, not by
            # the gateway itself.
            try:
                gateway.validate_card(card)
            except CardNotSupported:
                self.assertNotEqual(card.expected_response_code, "00")
                continue # skip the rest


            response = gateway.purchase(Decimal("45.00"), card,
                                        options={'order_id': self.get_order_id(),
                                                 })

            actual_rc = response['response_code']
            expected_rc = card.expected_response_code

            self.assertEqual(actual_rc, expected_rc,
                             "%s != %s - card %s, message: %s" % (actual_rc, expected_rc, card.number, response['message']))
            if card.expected_response_code == "00":
                self.assertEqual(response['status'], 'SUCCESS')
                self.assertEqual(received_signals, [transaction_was_successful])
            else:
                self.assertEqual(response['status'], 'FAILURE')
                self.assertEqual(received_signals, [transaction_was_unsuccessful])

    def test_address_to_code(self):
        gateway = GlobalIrisGateway()
        self.assertEqual(gateway.address_to_code("382, The Road", "WB1 A42"),
                         "142|382")



@skipIf(not settings.MERCHANT_SETTINGS.get("global_iris", None), "integration not configured")
class GlobalIrisRealMpiIntegrationTestCase(BetterXMLCompareMixin, GlobalIrisTestBase, TestCase):

    def test_3ds_verifyenrolled_xml(self):

        expected = """<?xml version="1.0" encoding="UTF-8" ?>
<request timestamp="20100625172305" type="3ds-verifyenrolled">
  <merchantid>thestore</merchantid>
  <account>theaccount</account>
  <orderid>1</orderid>
  <amount currency="GBP">2499</amount>
  <card>
    <number>4903034000057389</number>
    <expdate>0714</expdate>
    <chname>Mickey Mouse</chname>
    <type>VISA</type>
  </card>
  <sha1hash>272d8dde0bf34a0e744f696f2860a7894b687cf7</sha1hash>
</request>
"""
        integration = self.mk_integration()
        gateway = self.mk_gateway()
        card = CreditCard(first_name='Mickey',
                          last_name='Mouse',
                          month=7,
                          year=2014,
                          number='4903034000057389',
                          verification_value='123',
                          )
        gateway.validate_card(card)
        actual_xml = integration.build_3ds_verifyenrolled_xml(
            {'order_id': 1,
             'amount': Decimal('24.99'),
             'card': card,
             'timestamp': datetime(2010,6, 25, 17, 23, 05),
             })
        self.assertXMLEqual(actual_xml, expected)

    def test_parse_3ds_verifyenrolled_response(self):
        example_xml = """<?xml version="1.0" encoding="UTF-8" ?>
<response timestamp="20030625171810">
<merchantid>merchantid</merchantid>
<account>internet</account>
<orderid>orderid</orderid>
<authcode></authcode>
<result>00</result>
<message>Enrolled</message>
<pasref></pasref>
<timetaken>3</timetaken>
<authtimetaken>0</authtimetaken>
<pareq>eJxVUttygkAM/ZUdnitZFlBw4na02tE6bR0vD+0bLlHpFFDASv++u6i1zVNycju54H2dfrIvKsokz3qWY3OLUabyOMm2PWu1fGwF1r3E5a4gGi5IHQuS+ExlGW2JJXHPCjcuVyLYbIRQnrf2o3VMEY+57q05oIsibP+nA4SL02k7mELhKupqxVqF2WVxEgdBpMX6dwE4YJhSsVkKB3RH9ypGFyvNXpkrLW982HcancQzn7MopSkO2RnqmxJZYXQgKjyY1YV39Lt6O5XA4/Fp9xV1b4LcDqdbDcum8xKJ9oqTxFMAMKN5OxotFIXrJNY1otpMH0qYQwP43w08Pn0/W1Ql6+nj+cegonAOKpICs5d3hY+czpdJ+g6HKHBUoNEyk8OwzZaDXXE58R3JtG/as7DBH+IqhZFvpS3zLsBHqeq4VU7/OMTA7Cr45wo/0wNptWlV4Xb8Thftv3A30xs+7GYaokej3c415TxhgIJhUu54TLF2jt33f8ADVyvnA=</pareq>
<url>http://www.acs.com</url>
<enrolled>Y</enrolled>
<xid>7ba3b1e6e6b542489b73243aac050777</xid>
<sha1hash>9eda1f99191d4e994627ddf38550b9f47981f614</sha1hash>
</response>"""
        integration = self.mk_integration()
        retval = integration.handle_3ds_verifyenrolled_response(Dummy200Response(example_xml))
        self.assertEqual(retval.enrolled, True)
        self.assertEqual(retval.response_code, "00")
        self.assertEqual(retval.message, "Enrolled")
        self.assertEqual(retval.url, "http://www.acs.com")
        self.assertEqual(retval.pareq, "eJxVUttygkAM/ZUdnitZFlBw4na02tE6bR0vD+0bLlHpFFDASv++u6i1zVNycju54H2dfrIvKsokz3qWY3OLUabyOMm2PWu1fGwF1r3E5a4gGi5IHQuS+ExlGW2JJXHPCjcuVyLYbIRQnrf2o3VMEY+57q05oIsibP+nA4SL02k7mELhKupqxVqF2WVxEgdBpMX6dwE4YJhSsVkKB3RH9ypGFyvNXpkrLW982HcancQzn7MopSkO2RnqmxJZYXQgKjyY1YV39Lt6O5XA4/Fp9xV1b4LcDqdbDcum8xKJ9oqTxFMAMKN5OxotFIXrJNY1otpMH0qYQwP43w08Pn0/W1Ql6+nj+cegonAOKpICs5d3hY+czpdJ+g6HKHBUoNEyk8OwzZaDXXE58R3JtG/as7DBH+IqhZFvpS3zLsBHqeq4VU7/OMTA7Cr45wo/0wNptWlV4Xb8Thftv3A30xs+7GYaokej3c415TxhgIJhUu54TLF2jt33f8ADVyvnA=")

    def test_parse_3ds_verifyenrolled_response_not_enrolled(self):
        example_xml = """<?xml version="1.0" encoding="UTF-8" ?>
<response timestamp="20030625171810">
<merchantid>merchantid</merchantid>
<account>internet</account>
<orderid>orderid</orderid>
<authcode></authcode>
<result>110</result>
<message>Not Enrolled</message>
<pasref></pasref>
<timetaken>3</timetaken>
<authtimetaken>0</authtimetaken>
<pareq>eJxVUttygkAM/ZUdnitZFlBw4na02tE6bR0vD+0bLlHpFFDASv++u6i1
 zVNycju54H2dfrIvKsokz3qWY3OLUabyOMm2PWu1fGwF1r3E5a4gGi5IH
 QuS+ExlGW2JJXHPCjcuVyLYbIRQnrf2o3VMEY+57q05oIsibP+nA4SL02k
 7mELhKupqxVqF2WVxEgdBpMX6dwE4YJhSsVkKB3RH9ypGFyvNXpkrLW
 982HcancQzn7MopSkO2RnqmxJZYXQgKjyY1YV39Lt6O5XA4/Fp9xV1b4L
 cDqdbDcum8xKJ9oqTxFMAMKN5OxotFIXrJNY1otpMH0qYQwP43w08Pn0
 /W1Ql6+nj+cegonAOKpICs5d3hY+czpdJ+g6HKHBUoNEyk8OwzZaDXXE
 58R3JtG/as7DBH+IqhZFvpS3zLsBHqeq4VU7/OMTA7Cr45wo/0wNptWlV

4Xb8Thftv3A30xs+7GYaokej3c415TxhgIJhUu54TLF2jt33f8ADVyvnA=</pareq>
<url></url>
<enrolled>N</enrolled>
<xid>e9dafe706f7142469c45d4877aaf5984</xid>
<sha1hash>9eda1f99191d4e994627ddf38550b9f47981f614</sha1hash>
</response>
"""
        integration = self.mk_integration()
        retval = integration.handle_3ds_verifyenrolled_response(Dummy200Response(example_xml))
        self.assertEqual(retval.enrolled, False)
        self.assertEqual(retval.response_code, "110")
        self.assertEqual(retval.message, "Not Enrolled")
        self.assertEqual(retval.url, None)
        gateway = self.mk_gateway()
        card = self.get_visa_card()
        gateway.validate_card(card)
        proceed, extra = retval.proceed_with_auth(card)
        self.assertEqual(proceed, True),
        self.assertEqual(extra, {'mpi': {'eci': 6}})

    def test_send_3ds_verifyenrolled(self):
        integration = self.mk_integration()
        gateway = self.mk_gateway()
        card = self.get_visa_card()
        gateway.validate_card(card)
        response = integration.send_3ds_verifyenrolled({
                'order_id': 1,
                'amount': Decimal('24.99'),
                'card': card,
                })

        self.assertEqual(response.error, True)

    def test_encode(self):
        card = self.get_visa_card()
        integration = self.mk_integration()
        gateway = self.mk_gateway()
        gateway.validate_card(card) # Adds 'card_type'
        d = {'some_data': 1,
             'card': card,
             'amount': Decimal('12.34'),
             }
        encoded = integration.encode_merchant_data(d)
        decoded = integration.decode_merchant_data(encoded)
        self.assertEqual(decoded['some_data'], 1)
        self.assertEqual(decoded['card'].number, card.number)
        self.assertEqual(decoded['card'].card_type, Visa)
        self.assertEqual(decoded['amount'], d['amount'])

    def test_3ds_verifysig_xml(self):

        expected = """<?xml version="1.0" encoding="UTF-8" ?>
<request timestamp="20100625172305" type="3ds-verifysig">
  <merchantid>thestore</merchantid>
  <account>theaccount</account>
  <orderid>1</orderid>
  <amount currency="GBP">2499</amount>
  <card>
    <number>4903034000057389</number>
    <expdate>0714</expdate>
    <chname>Mickey Mouse</chname>
    <type>VISA</type>
  </card>
  <pares>xyz</pares>
  <sha1hash>272d8dde0bf34a0e744f696f2860a7894b687cf7</sha1hash>
</request>"""

        integration = self.mk_integration()
        gateway = self.mk_gateway()
        card = CreditCard(first_name='Mickey',
                          last_name='Mouse',
                          month=7,
                          year=2014,
                          number='4903034000057389',
                          verification_value='123',
                          )
        gateway.validate_card(card)
        actual_xml = integration.build_3ds_verifysig_xml('xyz',
                                                         {'order_id': 1,
                                                          'amount': Decimal('24.99'),
                                                          'card': card,
                                                          'timestamp': datetime(2010,6, 25, 17, 23, 05),
                                                          })
        self.assertXMLEqual(actual_xml, expected)

    def test_parse_3ds_verifysig_response_no_auth(self):
        example_xml = """<response timestamp="20100625171823">
<merchantid>merchantid</merchantid>
<account />
<orderid>orderid</orderid>
<result>00</result>
<message>Authentication Successful</message>
<threedsecure>
<status>N</status>
<eci />
<xid />
<cavv />
<algorithm />
</threedsecure>
<sha1hash>e5a7745da5dc32d234c3f52860132c482107e9ac</sha1hash>
</response>
"""
        integration = self.mk_integration()
        gateway = self.mk_gateway()
        card = self.get_visa_card()
        gateway.validate_card(card)
        retval = integration.handle_3ds_verifysig_response(Dummy200Response(example_xml))
        self.assertEqual(retval.response_code, "00")
        self.assertEqual(retval.message, "Authentication Successful")
        self.assertEqual(retval.status, "N")
        self.assertEqual(retval.proceed_with_auth(card)[0], False) # status is "N"

    def test_parse_3ds_verifysig_response_yes_auth(self):
        example_xml = """<response timestamp="20100625171823">
<merchantid>merchantid</merchantid>
<account />
<orderid>orderid</orderid>
<result>00</result>
<message>Authentication Successful</message>
<threedsecure>
<status>Y</status>
<eci>5</eci>
<xid>crqAeMwkEL9r4POdxpByWJ1/wYg=</xid>
<cavv>AAABASY3QHgwUVdEBTdAAAAAAAA=</cavv>
<algorithm />
</threedsecure>
<sha1hash>e5a7745da5dc32d234c3f52860132c482107e9ac</sha1hash>
</response>
"""
        integration = self.mk_integration()
        gateway = self.mk_gateway()
        card = self.get_visa_card()
        gateway.validate_card(card)
        retval = integration.handle_3ds_verifysig_response(Dummy200Response(example_xml))
        self.assertEqual(retval.response_code, "00")
        self.assertEqual(retval.message, "Authentication Successful")
        self.assertEqual(retval.status, "Y")
        proceed, data = retval.proceed_with_auth(card)
        self.assertTrue(proceed)
        self.assertEqual(data, {'mpi':{'eci': '5',
                                       'xid': 'crqAeMwkEL9r4POdxpByWJ1/wYg=',
                                       'cavv': 'AAABASY3QHgwUVdEBTdAAAAAAAA=',
                                       }})

    def test_send_3ds_verifysig(self):
        integration = self.mk_integration()
        gateway = self.mk_gateway()
        card = self.get_visa_card()
        gateway.validate_card(card)
        response = integration.send_3ds_verifysig('xyz', {
                'order_id': 1,
                'amount': Decimal('24.99'),
                'card': card,
                })

        self.assertEqual(response.error, True)

########NEW FILE########
__FILENAME__ = google_checkout_tests
from xml.dom.minidom import Document, parseString

from django.conf import settings
from django.test import TestCase
from django.template import Template, Context

from billing import get_integration
from django.utils.unittest.case import skipIf


@skipIf(not settings.MERCHANT_SETTINGS.get("google_checkout", None), "gateway not configured")
class GoogleCheckoutTestCase(TestCase):
    def setUp(self):
        self.gc = get_integration("google_checkout")
        target_url_name = "example.com/offsite/my_content/"
        target_url = 'http://' + target_url_name
        fields = {
            "items": [
                {
                    "name": "name of the item",
                    "description": "Item description",
                    "amount": 0.00,
                    "id": "999AXZ",
                    "currency": "USD",
                    "quantity": 1,
                    "subscription": {
                        "type": "merchant",                     # valid choices is ["merchant", "google"]
                        "period": "YEARLY",                     # valid choices is ["DAILY", "WEEKLY", "SEMI_MONTHLY", "MONTHLY", "EVERY_TWO_MONTHS"," QUARTERLY", "YEARLY"]
                        "payments": [
                            {
                                "maximum-charge": 9.99,         # Item amount must be "0.00"
                                "currency": "USD"
                            }
                        ]
                    },
                    "digital-content": {
                        "display-disposition": "OPTIMISTIC",    # valid choices is ['OPTIMISTIC', 'PESSIMISTIC']
                        "description": "Congratulations! Your subscription is being set up. Feel free to log onto &amp;lt;a href='%s'&amp;gt;%s&amp;lt;/a&amp;gt; and try it out!" % (target_url, target_url_name)
                    },
                },
            ],
            "return_url": "http://127.0.0.1:8000/offsite/google-checkout/",
            'private_data': "test@example.com",
         }
        self.gc.add_fields(fields)

    def testFormGen(self):
        tmpl = Template("{% load render_integration from billing_tags %}{% render_integration obj %}")
        form = tmpl.render(Context({"obj": self.gc}))

        dom = parseString(form)
        form_action_url = dom.getElementsByTagName('form')[0].attributes['action'].value
        input_image_src = dom.getElementsByTagName('input')[2].attributes['src'].value

        expected_form_action_url = "https://sandbox.google.com/checkout/api/checkout/v2/checkout/Merchant/%s" % settings.MERCHANT_SETTINGS['google_checkout']['MERCHANT_ID']
        expected_input_image_src = "https://sandbox.google.com/checkout/buttons/checkout.gif?merchant_id=%s&w=180&h=46&style=white&variant=text&loc=en_US" % settings.MERCHANT_SETTINGS['google_checkout']['MERCHANT_ID']

        self.assertEquals(form_action_url, expected_form_action_url)
        self.assertEquals(input_image_src, expected_input_image_src)


    def testBuildXML(self):
        xml = self.gc.build_xml()
        good_xml = """<?xml version="1.0" encoding="utf-8"?><checkout-shopping-cart xmlns="http://checkout.google.com/schema/2"><shopping-cart><items><item><item-name>name of the item</item-name><item-description>Item description</item-description><unit-price currency="USD">0.0</unit-price><quantity>1</quantity><merchant-item-id>999AXZ</merchant-item-id><subscription period="YEARLY" type="merchant"><payments><subscription-payment><maximum-charge currency="USD">9.99</maximum-charge></subscription-payment></payments></subscription><digital-content><display-disposition>OPTIMISTIC</display-disposition><description>Congratulations! Your subscription is being set up. Feel free to log onto &amp;amp;lt;a href=\'http://example.com/offsite/my_content/\'&amp;amp;gt;example.com/offsite/my_content/&amp;amp;lt;/a&amp;amp;gt; and try it out!</description></digital-content></item></items><merchant-private-data>test@example.com</merchant-private-data></shopping-cart><checkout-flow-support><merchant-checkout-flow-support><continue-shopping-url>http://127.0.0.1:8000/offsite/google-checkout/</continue-shopping-url></merchant-checkout-flow-support></checkout-flow-support></checkout-shopping-cart>"""
        self.assertEquals(xml, good_xml)

@skipIf(not settings.MERCHANT_SETTINGS.get("google_checkout", None), "gateway not configured")
class GoogleCheckoutShippingTestCase(TestCase):
    def setUp(self):
        self.gc = get_integration("google_checkout")
        self.maxDiff = None

    def testAddNodes(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        child_node_values = ['child1', 'child2', 'child3']
        self.gc._add_nodes(doc, parent_node, 'child_node','child_sub_node', child_node_values)
        xml1 = "<parent_node><child_node><child_sub_node>child1</child_sub_node></child_node>\
<child_node><child_sub_node>child2</child_sub_node></child_node>\
<child_node><child_sub_node>child3</child_sub_node></child_node></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testAddNodes_novalues(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        child_node_values = []
        self.gc._add_nodes(doc, parent_node, 'child_node','child_sub_node', child_node_values)
        xml1 = """<parent_node></parent_node>"""
        doc_good = parseString(xml1)
        self.assertEquals(doc.toprettyxml(), doc_good.toprettyxml())

    def testShippingExclude(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
            'us-state-area': ['AK','HI'],
            'us-zip-area': ['90210', '04005', '04092'],
            'us-country-area': 'CONTINENTAL_48',
            'world-area': True,
            'postal-area': [{
                'country-code': 'US',
                'postal-code-pattern': ['94043', '90211'],
                },
            ],
        }
        self.gc._shipping_allowed_excluded(doc, parent_node, data)
        xml1 = "<parent_node><us-state-area><state>AK</state></us-state-area>\
<us-state-area><state>HI</state></us-state-area>\
<us-zip-area><zip-pattern>90210</zip-pattern></us-zip-area>\
<us-zip-area><zip-pattern>04005</zip-pattern></us-zip-area>\
<us-zip-area><zip-pattern>04092</zip-pattern></us-zip-area>\
<us-country-area country-area='CONTINENTAL_48'/>\
<world-area/>\
<postal-area><country-code>US</country-code>\
<postal-code-pattern>94043</postal-code-pattern>\
<postal-code-pattern>90211</postal-code-pattern></postal-area>\
</parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testShippingRestrictions(self):
        """ Not a real data since you would never put the these values for
            exclude and include, but wanted to test everything on both sides
            should work the same for both allowed and excluded"""
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
            'allowed-areas': {
                'us-state-area': ['ME','NH'],
                'us-zip-area': ['04005', '04092'],
                'us-country-area': 'ALL',
                'world-area': True,
                'postal-area': [{
                    'country-code': 'US',
                    'postal-code-pattern': ['94043', '90211'],
                    },
                ],
            },
            'excluded-areas': {
                'us-state-area': ['AK','HI'],
                'us-zip-area': ['90210'],
                'us-country-area': 'CONTINENTAL_48',
                'world-area': False,
                'postal-area': [{
                    'country-code': 'US',
                    'postal-code-pattern': ['11111', '11112'],
                    },
                ],
            },
        }
        self.gc._shipping_restrictions_filters(doc, parent_node, data)
        xml1 = "<parent_node><allowed-areas><us-state-area>\
<state>ME</state></us-state-area>\
<us-state-area><state>NH</state></us-state-area>\
<us-zip-area><zip-pattern>04005</zip-pattern></us-zip-area>\
<us-zip-area><zip-pattern>04092</zip-pattern></us-zip-area>\
<us-country-area country-area='ALL'/>\
<world-area/>\
<postal-area><country-code>US</country-code>\
<postal-code-pattern>94043</postal-code-pattern>\
<postal-code-pattern>90211</postal-code-pattern></postal-area>\
</allowed-areas>\
<excluded-areas><us-state-area><state>AK</state></us-state-area>\
<us-state-area><state>HI</state></us-state-area>\
<us-zip-area><zip-pattern>90210</zip-pattern></us-zip-area>\
<us-country-area country-area='CONTINENTAL_48'/>\
<postal-area><country-code>US</country-code>\
<postal-code-pattern>11111</postal-code-pattern>\
<postal-code-pattern>11112</postal-code-pattern></postal-area>\
</excluded-areas></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testFullCartXML(self):
        fields = {"items": [{
            "name": "name of the item",
            "description": "Item description",
            "amount": 1,
            "id": "999AXZ",
            "currency": "USD",
            "quantity": 1,
            }],
        'shipping-methods': [
            {'shipping_type':'flat-rate-shipping',
             'name':"UPS Next Day Air",
             'currency':"USD",
             'price':20.00,
             'shipping-restrictions': {
                'allow-us-po-box': False,
                'excluded-areas': {
                        'us-state-area' : ['AK', 'HI']
                        }
                }
             },
            {'shipping_type':'flat-rate-shipping',
             'name':"UPS Ground",
             'currency':"USD",
             'price':15.00,
             'shipping-restrictions': {
                'allow-us-po-box': False,
                }
            },
        ],
       "return_url": "http://127.0.0.1:8000/offsite/google-checkout/",
       }
        self.gc.add_fields(fields)

        xml = self.gc.build_xml()
        good_xml = """<?xml version="1.0" encoding="utf-8"?><checkout-shopping-cart xmlns="http://checkout.google.com/schema/2"><shopping-cart><items><item><item-name>name of the item</item-name><item-description>Item description</item-description><unit-price currency="USD">1</unit-price><quantity>1</quantity><merchant-item-id>999AXZ</merchant-item-id></item></items><merchant-private-data></merchant-private-data></shopping-cart><checkout-flow-support><merchant-checkout-flow-support><continue-shopping-url>http://127.0.0.1:8000/offsite/google-checkout/</continue-shopping-url><shipping-methods><flat-rate-shipping name="UPS Next Day Air"><price currency="USD">20.0</price><shipping-restrictions><allow-us-po-box>false</allow-us-po-box><excluded-areas><us-state-area><state>AK</state></us-state-area><us-state-area><state>HI</state></us-state-area></excluded-areas></shipping-restrictions></flat-rate-shipping><flat-rate-shipping name="UPS Ground"><price currency="USD">15.0</price><shipping-restrictions><allow-us-po-box>false</allow-us-po-box></shipping-restrictions></flat-rate-shipping></shipping-methods></merchant-checkout-flow-support></checkout-flow-support></checkout-shopping-cart>"""
        self.assertEquals(xml, good_xml)


@skipIf(not settings.MERCHANT_SETTINGS.get("google_checkout", None), "gateway not configured")
class GoogleCheckoutTaxTestCase(TestCase):
    """ Test the tax code """

    def setUp(self):
        self.gc = get_integration("google_checkout")
        self.maxDiff = None

    def testTaxes1(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                    'tax-rules': [
                        {
                            'shipping-taxed': True,
                            'rate': 0.06,
                            'tax-area': {
                                'us-state-area': ['CT'],
                             }
                        }
                    ]
                }
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables><default-tax-table><tax-rules>\
<default-tax-rule><shipping-taxed>true</shipping-taxed><rate>0.06</rate>\
<tax-area><us-state-area><state>CT</state></us-state-area></tax-area>\
</default-tax-rule></tax-rules></default-tax-table></tax-tables>\
</parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testTaxes2(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                    'tax-rules': [
                            {
                                'shipping-taxed': True,
                                'rate': 0.06,
                                'tax-area': {
                                    'us-state-area': ['CT'],
                                 }
                            },
                            {
                                'rate': 0.05,
                                'tax-area': {
                                    'us-state-area': ['MD'],
                                 }
                            }
                        ]
                    }
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables><default-tax-table><tax-rules>\
<default-tax-rule><shipping-taxed>true</shipping-taxed><rate>0.06</rate>\
<tax-area><us-state-area><state>CT</state></us-state-area></tax-area>\
</default-tax-rule><default-tax-rule><shipping-taxed>false</shipping-taxed>\
<rate>0.05</rate><tax-area><us-state-area><state>MD</state></us-state-area>\
</tax-area></default-tax-rule></tax-rules></default-tax-table></tax-tables>\
</parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testTaxes3(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                        'tax-rules': [
                            {
                                'shipping-taxed': False,
                                'rate': 0.08375,
                                'tax-area': {
                                    'us-zip-area': ['100*'],
                                 }
                            },
                            {
                                'shipping-taxed': True,
                                'rate': 0.04,
                                'tax-area': {
                                    'us-state-area': ['NY'],
                                 }
                            }
                        ]
                    }
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables><default-tax-table>\
<tax-rules><default-tax-rule><shipping-taxed>false</shipping-taxed>\
<rate>0.08375</rate><tax-area><us-zip-area><zip-pattern>100*</zip-pattern>\
</us-zip-area></tax-area></default-tax-rule>\
<default-tax-rule><shipping-taxed>true</shipping-taxed>\
<rate>0.04</rate><tax-area><us-state-area><state>NY</state></us-state-area>\
</tax-area></default-tax-rule>\
</tax-rules></default-tax-table></tax-tables></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testTaxes4(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                        'tax-rules': [
                            {
                                'shipping-taxed': False,
                                'rate': 0.08375,
                                'tax-area': {
                                    'us-zip-area': ['100*', '040*'],
                                 }
                            },
                            {
                                'shipping-taxed': True,
                                'rate': 0.04,
                                'tax-area': {
                                    'us-state-area': ['NY', 'ME'],
                                 }
                            }
                        ]
                    }
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables><default-tax-table>\
<tax-rules><default-tax-rule><shipping-taxed>false</shipping-taxed>\
<rate>0.08375</rate><tax-areas><us-zip-area><zip-pattern>100*</zip-pattern>\
</us-zip-area><us-zip-area><zip-pattern>040*</zip-pattern>\
</us-zip-area></tax-areas></default-tax-rule>\
<default-tax-rule><shipping-taxed>true</shipping-taxed>\
<rate>0.04</rate><tax-areas><us-state-area><state>NY</state></us-state-area>\
<us-state-area><state>ME</state></us-state-area>\
</tax-areas></default-tax-rule>\
</tax-rules></default-tax-table></tax-tables></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testTaxes5(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                        'tax-rules': [
                            {
                                'shipping-taxed': True,
                                'rate': 0.06,
                                'tax-area': {
                                    'us-state-area': ['CT'],
                                 }
                            },
                            {
                                'rate': 0.05,
                                'tax-area': {
                                    'us-state-area': ['MD'],
                                 }
                            }
                        ]
                    },
                'alternate-tax-tables': [
                    {'name': 'bicycle_helmets',
                     'standalone': False,
                     'alternative-tax-rules': [
                        { 'rate': 0,
                          'tax-area': {
                            'us-state-area': ['CT'],
                          }
                        }
                      ]
                    }
                ]
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables>\
<default-tax-table><tax-rules><default-tax-rule>\
<shipping-taxed>true</shipping-taxed><rate>0.06</rate>\
<tax-area><us-state-area><state>CT</state></us-state-area>\
</tax-area></default-tax-rule><default-tax-rule>\
<shipping-taxed>false</shipping-taxed><rate>0.05</rate>\
<tax-area><us-state-area><state>MD</state></us-state-area>\
</tax-area></default-tax-rule></tax-rules></default-tax-table>\
<alternate-tax-tables><alternate-tax-table name='bicycle_helmets' standalone='false'>\
<alternate-tax-rules><alternate-tax-rule><rate>0</rate>\
<tax-area><us-state-area><state>CT</state></us-state-area></tax-area>\
</alternate-tax-rule></alternate-tax-rules></alternate-tax-table>\
</alternate-tax-tables></tax-tables></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testTaxes6(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                        'tax-rules': [
                            {
                                'shipping-taxed': True,
                                'rate': 0.06,
                                'tax-area': {
                                    'us-state-area': ['CT'],
                                 }
                            },
                            {
                                'rate': 0.05,
                                'tax-area': {
                                    'us-state-area': ['MD'],
                                 }
                            }
                        ]
                    },
                'alternate-tax-tables': [
                    {'name': 'tax_exempt',
                     'standalone': True,
                    }
                ]
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables>\
<default-tax-table><tax-rules><default-tax-rule>\
<shipping-taxed>true</shipping-taxed><rate>0.06</rate>\
<tax-area><us-state-area><state>CT</state></us-state-area>\
</tax-area></default-tax-rule><default-tax-rule>\
<shipping-taxed>false</shipping-taxed><rate>0.05</rate>\
<tax-area><us-state-area><state>MD</state></us-state-area>\
</tax-area></default-tax-rule></tax-rules></default-tax-table>\
<alternate-tax-tables><alternate-tax-table name='tax_exempt' standalone='true'>\
<alternate-tax-rules/></alternate-tax-table>\
</alternate-tax-tables></tax-tables></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testTaxes7(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                        'tax-rules': [
                            {
                                'shipping-taxed': True,
                                'rate': 0.175,
                                'tax-area': {
                                    'postal-area': [
                                        {'country-code': 'DE'},
                                        {'country-code': 'ES'},
                                        {'country-code': 'GB'},
                                    ],
                                 },
                            },
                        ]
                    },
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables>\
<default-tax-table><tax-rules><default-tax-rule>\
<shipping-taxed>true</shipping-taxed><rate>0.175</rate>\
<tax-areas><postal-area><country-code>DE</country-code>\
</postal-area><postal-area><country-code>ES</country-code>\
</postal-area><postal-area><country-code>GB</country-code>\
</postal-area></tax-areas></default-tax-rule></tax-rules>\
</default-tax-table></tax-tables></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())

    def testTaxes8(self):
        doc = Document()
        parent_node = doc.createElement('parent_node')
        doc.appendChild(parent_node)
        data = {
                'default-tax-table': {
                        'tax-rules': [
                            {
                                'shipping-taxed': True,
                                'rate': 0.175,
                                'tax-area': {
                                    'world-area': True,
                                 },
                            },
                        ]
                    },
                'alternate-tax-tables': [
                    {'name': 'reduced',
                     'standalone': True,
                     'alternative-tax-rules': [
                        { 'rate': 0.05,
                          'tax-area': {
                            'world-area': True,
                          }
                        },
                      ]
                     },
                    { 'name': 'tax_exempt',
                     'standalone': True,
                    }
                ]
        }
        self.gc._taxes(doc, parent_node, data)
        xml1 = "<parent_node><tax-tables>\
<default-tax-table><tax-rules>\
<default-tax-rule><shipping-taxed>true</shipping-taxed>\
<rate>0.175</rate><tax-area><world-area/></tax-area>\
</default-tax-rule></tax-rules></default-tax-table>\
<alternate-tax-tables><alternate-tax-table name='reduced' standalone='true'>\
<alternate-tax-rules><alternate-tax-rule><rate>0.05</rate><tax-area>\
<world-area/></tax-area></alternate-tax-rule></alternate-tax-rules>\
</alternate-tax-table><alternate-tax-table standalone='true' name='tax_exempt'>\
<alternate-tax-rules/></alternate-tax-table></alternate-tax-tables>\
</tax-tables></parent_node>"
        doc_good = parseString(xml1)
        self.assertEquals(doc.toxml(), doc_good.toxml())


    def testFullCartXML(self):
        fields = {"items": [{
            "name": "name of the item",
            "description": "Item description",
            "amount": 1,
            "id": "999AXZ",
            "currency": "USD",
            "quantity": 1,
            },
            {
            "name": "tax free item",
            "description": "Item description",
            "amount": 2,
            "id": "999AXZ",
            "currency": "USD",
            "quantity": 1,
            "tax-table-selector": 'tax_exempt',
            },
            ],
           'tax-tables': {
                'default-tax-table': {
                    'tax-rules': [
                        {
                            'shipping-taxed': False,
                            'rate': 0.08375,
                            'tax-area': {
                                'us-zip-area': ['100*'],
                             }
                        },
                        {
                            'shipping-taxed': True,
                            'rate': 0.04,
                            'tax-area': {
                                'us-state-area': ['NY'],
                             }
                        }
                    ]
                },
                'alternate-tax-tables': [
                    {
                     'name': 'tax_exempt',
                     'standalone': True,
                    }
                ]
           },
           "return_url": "http://127.0.0.1:8000/offsite/google-checkout/",
           }
        self.gc.add_fields(fields)

        xml = self.gc.build_xml()
        good_xml = """<?xml version="1.0" encoding="utf-8"?><checkout-shopping-cart xmlns="http://checkout.google.com/schema/2"><shopping-cart><items><item><item-name>name of the item</item-name><item-description>Item description</item-description><unit-price currency="USD">1</unit-price><quantity>1</quantity><merchant-item-id>999AXZ</merchant-item-id></item><item><item-name>tax free item</item-name><item-description>Item description</item-description><unit-price currency="USD">2</unit-price><quantity>1</quantity><merchant-item-id>999AXZ</merchant-item-id><tax-table-selector>tax_exempt</tax-table-selector></item></items><merchant-private-data></merchant-private-data></shopping-cart><checkout-flow-support><merchant-checkout-flow-support><continue-shopping-url>http://127.0.0.1:8000/offsite/google-checkout/</continue-shopping-url><tax-tables><default-tax-table><tax-rules><default-tax-rule><shipping-taxed>false</shipping-taxed><rate>0.08375</rate><tax-area><us-zip-area><zip-pattern>100*</zip-pattern></us-zip-area></tax-area></default-tax-rule><default-tax-rule><shipping-taxed>true</shipping-taxed><rate>0.04</rate><tax-area><us-state-area><state>NY</state></us-state-area></tax-area></default-tax-rule></tax-rules></default-tax-table><alternate-tax-tables><alternate-tax-table name="tax_exempt" standalone="true"><alternate-tax-rules/></alternate-tax-table></alternate-tax-tables></tax-tables></merchant-checkout-flow-support></checkout-flow-support></checkout-shopping-cart>"""
        self.assertEquals(xml, good_xml)

########NEW FILE########
__FILENAME__ = ogone_payments_tests
from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing import get_integration


@skipIf(not settings.MERCHANT_SETTINGS.get("ogone_payments", None), "gateway not configured")
class OgonePaymentsTestCase(TestCase):
    def setUp(self):
        self.op = get_integration("ogone_payments")
        self.data = {
            'orderID': 21,
            'ownerstate': u'',
            'cn': u'Venkata Ramana',
            'language': 'en_US',
            'ownertown': u'Hyderabad',
            'ownercty': u'IN',
            'exceptionurl': u'http://127.0.0.1:8000/offsite/ogone/failure/',
            'ownerzip': u'Postcode',
            'catalogurl': u'http://127.0.0.1:8000/',
            'currency': u'EUR',
            'amount': u'579',
            'declineurl': u'http://127.0.0.1:8000/offsite/ogone/failure/',
            'homeurl': u'http://127.0.0.1:8000/',
            'cancelurl': u'http://127.0.0.1:8000/offsite/ogone/failure/',
            'accepturl': u'http://127.0.0.1:8000/offsite/ogone/success/',
            'owneraddress': u'Near Madapur PS',
            'com': u'Order #21: Venkata Ramana',
            'email': u'ramana@agiliq.com'
        }
        self.op.add_fields(self.data)

    def testFormFields(self):
        self.assertEquals(self.op.fields, {
            'orderID': 21,
            'ownerstate': u'',
            'cn': u'Venkata Ramana',
            'language': 'en_US',
            'ownertown': u'Hyderabad',
            'ownercty': u'IN',
            'exceptionurl': u'http://127.0.0.1:8000/offsite/ogone/failure/',
            'ownerzip': u'Postcode',
            'catalogurl': u'http://127.0.0.1:8000/',
            'currency': u'EUR',
            'amount': u'579',
            'declineurl': u'http://127.0.0.1:8000/offsite/ogone/failure/',
            'homeurl': u'http://127.0.0.1:8000/',
            'cancelurl': u'http://127.0.0.1:8000/offsite/ogone/failure/',
            'accepturl': u'http://127.0.0.1:8000/offsite/ogone/success/',
            'owneraddress': u'Near Madapur PS',
            'com': u'Order #21: Venkata Ramana',
            'email': u'ramana@agiliq.com'
        })

########NEW FILE########
__FILENAME__ = paylane_tests
# -*- coding: utf-8 -*-
# vim:tabstop=4:expandtab:sw=4:softtabstop=4

from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf

from billing.gateway import CardNotSupported
from billing.utils.credit_card import Visa, CreditCard
from billing import get_gateway
from billing.signals import *
from billing.utils.paylane import *
from billing.models import PaylaneTransaction, PaylaneAuthorization

#This is needed because Paylane doesn't like too many requests in a very short time


THROTTLE_CONTROL_SECONDS = 60

# VISA test card numbers
# 4929966723331981 #
# 4916437826836305 #
# 4532830407731057
# 4539824967650347
# 4278255665174428
# 4556096020428973
# 4929242798450290
# 4024007124529719
# 4024007172509597
# 4556969412054203


@skipIf(not settings.MERCHANT_SETTINGS.get("paylane", None), "gateway not configured")
class PaylaneTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("paylane")
        self.merchant.test_mode = True
        address = PaylanePaymentCustomerAddress()
        address.street_house = 'Av. 24 de Julho, 1117'
        address.city = 'Lisbon'
        address.zip_code = '1700-000'
        address.country_code = 'PT'
        self.customer = PaylanePaymentCustomer(name='Celso Pinto', email='celso@modelo3.pt', ip_address='8.8.8.8', address=address)
        self.product = PaylanePaymentProduct(description='Paylane test payment')

    def tearDown(self):
        for authz in PaylaneAuthorization.objects.all():
            self.merchant.void(authz.sale_authorization_id)

    def testOneShotPurchaseOK(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4012888888881881', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = {}
        res = self.merchant.purchase(1.0, credit_card, options=options)
        self.assertEqual(res['status'], 'SUCCESS', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertFalse('authorization' in res['response'])

    def testOneShotPurchaseError(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4929966723331981', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = {}
        res = self.merchant.purchase(float(PaylaneError.ERR_CARD_EXPIRED), credit_card, options=options)
        self.assertEqual(res['status'], 'FAILURE', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertFalse('authorization' in res['response'])
        self.assertTrue('error' in res['response'])
        self.assertEqual(res['response']['error'].error_code, PaylaneError.ERR_CARD_EXPIRED)

    def testRecurringSetupOK(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4242424242424242', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.recurring(1.0, credit_card, options=options)
        self.assertEqual(res['status'], 'SUCCESS', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertTrue('authorization' in res['response'])
        self.assertTrue(res['response']['authorization'].sale_authorization_id > 0)

    def testRecurringSetupError(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4916437826836305', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.recurring(float(PaylaneError.ERR_CARD_EXPIRED), credit_card, options=options)
        self.assertEqual(res['status'], 'FAILURE', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertFalse('authorization' in res['response'])
        self.assertTrue('error' in res['response'])
        self.assertEqual(res['response']['error'].error_code, PaylaneError.ERR_CARD_EXPIRED)

    def testRecurringBillingOK(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4000111111111115', verification_value="100")
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.recurring(1.0, credit_card, options=options)
        self.assertEqual(res['status'], 'SUCCESS', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertTrue('authorization' in res['response'])
        self.assertTrue(res['response']['authorization'].sale_authorization_id > 0)

        bill1 = self.merchant.bill_recurring(12.0, res['response']['authorization'], 'OK recurring')
        self.assertEqual(bill1['status'], 'SUCCESS', unicode(bill1['response']))
        self.assertTrue('transaction' in bill1['response'])
        self.assertTrue('authorization' in bill1['response'])

    def testRecurringBillingFailWithChargeback(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4111111111111111', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.recurring(1.0, credit_card, options=options)
        self.assertEqual(res['status'], 'SUCCESS', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertTrue('authorization' in res['response'])
        self.assertTrue(res['response']['authorization'].sale_authorization_id > 0)

        bill1 = self.merchant.bill_recurring(12.0, res['response']['authorization'], 'OK recurring')
        self.assertEqual(bill1['status'], 'SUCCESS', unicode(bill1['response']))
        self.assertTrue('transaction' in bill1['response'])
        self.assertTrue('authorization' in bill1['response'])

        bill2 = self.merchant.bill_recurring(float(PaylaneError.ERR_RESALE_WITH_CHARGEBACK), bill1['response']['authorization'], 'Fail recurring')
        self.assertEqual(bill2['status'], 'FAILURE', unicode(bill2['response']))
        self.assertTrue('transaction' in bill2['response'])
        self.assertTrue('error' in bill2['response'])
        self.assertEqual(bill2['response']['error'].error_code, PaylaneError.ERR_RESALE_WITH_CHARGEBACK)

    def testAuthorizeOK(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4532830407731057', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.authorize(1.0, credit_card, options=options)
        self.assertEqual(res['status'], 'SUCCESS', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertTrue('authorization' in res['response'])
        self.assertTrue(res['response']['authorization'].sale_authorization_id > 0)

    def testAuthorizeError(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4539824967650347', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.authorize(float(PaylaneError.ERR_CARD_EXPIRED), credit_card, options=options)
        self.assertEqual(res['status'], 'FAILURE', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertFalse('authorization' in res['response'])
        self.assertTrue('error' in res['response'])
        self.assertEqual(res['response']['error'].error_code, PaylaneError.ERR_CARD_EXPIRED)

    def testCaptureOK(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4278255665174428', verification_value="100")
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.authorize(36.0, credit_card, options=options)
        self.assertEqual(res['status'], 'SUCCESS', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertTrue('authorization' in res['response'])
        self.assertTrue(res['response']['authorization'].sale_authorization_id > 0)

        bill1 = self.merchant.capture(36.0, res['response']['authorization'], options)
        self.assertEqual(bill1['status'], 'SUCCESS', unicode(bill1['response']))
        self.assertTrue('transaction' in bill1['response'])
        self.assertTrue('authorization' in bill1['response'])

    def testCaptureError(self):
        credit_card = Visa(first_name='Celso', last_name='Pinto', month=10, year=2020, number='4556096020428973', verification_value=435)
        options = {}
        options['customer'] = self.customer
        options['product'] = self.product
        res = self.merchant.authorize(1.0, credit_card, options=options)
        self.assertEqual(res['status'], 'SUCCESS', unicode(res['response']))
        self.assertTrue('transaction' in res['response'])
        self.assertTrue('authorization' in res['response'])
        self.assertTrue(res['response']['authorization'].sale_authorization_id > 0)

        bill2 = self.merchant.capture(float(PaylaneError.ERR_RESALE_WITH_CHARGEBACK), res['response']['authorization'], options)
        self.assertEqual(bill2['status'], 'FAILURE', unicode(bill2['response']))
        self.assertTrue('transaction' in bill2['response'])
        self.assertTrue('error' in bill2['response'])
        self.assertEqual(bill2['response']['error'].error_code, 443)

########NEW FILE########
__FILENAME__ = pay_pal_tests
import datetime
from urllib2 import urlparse
from xml.dom import minidom

from django.conf import settings
from django.test.client import RequestFactory
from django.template import Template, Context
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.unittest.case import skipIf

from paypal.pro.models import PayPalNVP

from billing import get_gateway, get_integration, CreditCard
from billing.signals import *
from billing.gateway import CardNotSupported
from billing.utils.credit_card import Visa

RF = RequestFactory()
request = RF.get("/", REMOTE_ADDR="192.168.1.1")
fake_options = {
    "request": request,
    "email": "testuser@fakedomain.com",
    "billing_address": {
        "name": "PayPal User",
        "address1": "Street 1",
        "city": "Mountain View",
        "state": "CA",
        "country": "US",
        "zip": "94043"
    },
}

@skipIf(not settings.MERCHANT_SETTINGS.get("pay_pal", None), "gateway not configured")
class PayPalGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("pay_pal")
        self.merchant.test_mode = True
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2017,
                                      number="4500775008976759",
                                      verification_value="000")

    def testCardSupported(self):
        self.credit_card.number = "5019222222222222"
        self.assertRaises(CardNotSupported,
                          lambda: self.merchant.purchase(1000,
                                                         self.credit_card))

    def testCardValidated(self):
        self.merchant.test_mode = False
        self.credit_card.number = "4222222222222123"
        self.assertFalse(self.merchant.validate_card(self.credit_card))

    def testCardType(self):
        self.merchant.validate_card(self.credit_card)
        self.assertEquals(self.credit_card.card_type, Visa)

    def testPurchase(self):
        resp = self.merchant.purchase(1, self.credit_card,
                                      options=fake_options)
        self.assertEquals(resp["status"], "SUCCESS")
        self.assertNotEquals(resp["response"].correlationid, "0")
        self.assertTrue(isinstance(resp["response"], PayPalNVP))

    def testPaymentSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_successful.connect(receive)

        resp = self.merchant.purchase(1, self.credit_card,
                                      options=fake_options)
        self.assertEquals(received_signals, [transaction_was_successful])

    def testPaymentUnSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        transaction_was_unsuccessful.connect(receive)

        resp = self.merchant.purchase(105.02, self.credit_card,
                                      options=fake_options)
        self.assertEquals(received_signals, [transaction_was_unsuccessful])

    def testCreditCardExpired(self):
        resp = self.merchant.purchase(105.02, self.credit_card,
                                      options=fake_options)
        self.assertNotEquals(resp["status"], "SUCCESS")


@skipIf(not settings.MERCHANT_SETTINGS.get("pay_pal", None), "gateway not configured")
class PayPalWebsiteStandardsTestCase(TestCase):
    urls = "billing.tests.test_urls"

    def setUp(self):
        self.today = datetime.datetime.today().strftime("%Y-%m-%d")
        self.pws = get_integration("pay_pal")
        self.pws.test_mode = True
        fields = {
            "cmd": "_xclick",
            'notify_url': 'http://localhost/paypal-ipn-handler/',
            'return_url': 'http://localhost/offsite/paypal/done/',
            'cancel_return': 'http://localhost/offsite/paypal/',
            'amount': '1',
            'item_name': "Test Item",
            'invoice': self.today,
        }
        self.pws.add_fields(fields)

    def assertFormIsCorrect(self, form, fields):
        dom = minidom.parseString(form)
        inputs = dom.getElementsByTagName('input')
        values_dict = {}
        for el in inputs:
            if (el.attributes['type'].value == 'hidden'
                    and el.hasAttribute('value')):
                values_dict[el.attributes['name'].value] = el.attributes['value'].value
        self.assertDictContainsSubset(values_dict, fields)

        form_action_url = dom.getElementsByTagName('form')[0].attributes['action'].value
        parsed = urlparse.urlparse(form_action_url)

        self.assertEquals(parsed.scheme, 'https')
        self.assertEquals(parsed.netloc, 'www.sandbox.paypal.com')
        self.assertEquals(parsed.path, '/cgi-bin/webscr')

    def testRenderForm(self):
        tmpl = Template("""
            {% load render_integration from billing_tags %}
            {% render_integration obj %}
        """)
        form = tmpl.render(Context({"obj": self.pws}))
        fields = self.pws.fields.copy()
        fields.update({
            'charset': 'utf-8',
            'currency_code': 'USD',
            'return': 'http://localhost/offsite/paypal/done/',
            'no_shipping': '1',
        })
        self.assertFormIsCorrect(form, fields)

    def testRenderFormMultipleItems(self):
        fields = self.pws.fields.copy()
        fields.update({
            'amount_1': '10',
            'item_name_1': 'Test Item 1',
            'amount_2': '20',
            'item_name_2': 'Test Item 2',
            'charset': 'utf-8',
            'currency_code': 'USD',
            'return': 'http://localhost/offsite/paypal/done/',
            'no_shipping': '1',
        })
        tmpl = Template("""
            {% load render_integration from billing_tags %}
            {% render_integration obj %}
        """)
        form = tmpl.render(Context({"obj": self.pws}))
        self.assertFormIsCorrect(form, fields)

    def testIPNURLSetup(self):
        self.assertEquals(reverse("paypal-ipn"), "/paypal-ipn-url/")

########NEW FILE########
__FILENAME__ = pin_tests
from django.conf import settings
from django.test import TestCase
from django.utils.unittest.case import skipIf
from billing import get_gateway, CreditCard

VISA_SUCCESS = '4200000000000000'
VISA_FAILURE = '4100000000000001'

OPTIONS = {
    "email": "test@test.com",
    "description": "Test transaction",
    "currency": "AUD",
    "ip": "0.0.0.0",
    "billing_address": {
        "address1": "392 Sussex St",
        "address2": "",
        "city": "Sydney",
        "zip": "2000",
        "state": "NSW",
        "country": "Australia",
    },
}


@skipIf(not settings.MERCHANT_SETTINGS.get("pin", None), "gateway not configured")
class PinGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("pin")
        self.merchant.test_mode = True
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2020,
                                      number=VISA_SUCCESS,
                                      verification_value="100")

    def testPurchaseSuccess(self):
        self.credit_card.number = VISA_SUCCESS
        resp = self.merchant.purchase(100, self.credit_card, options=OPTIONS)
        self.assertEquals(resp["status"], "SUCCESS")

    def testPurchaseFailure(self):
        self.credit_card.number = VISA_FAILURE
        resp = self.merchant.purchase(100.00, self.credit_card, options=OPTIONS)
        self.assertEquals(resp["status"], "FAILURE")

########NEW FILE########
__FILENAME__ = stripe_tests
from django.test import TestCase
from billing import get_gateway, CreditCard
from billing.gateway import CardNotSupported
from billing.utils.credit_card import Visa
from django.utils.unittest.case import skipIf
import stripe
from django.conf import settings

@skipIf(not settings.MERCHANT_SETTINGS.get("stripe", None), "gateway not configured")
class StripeGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("stripe")
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2020,
                                      number="4242424242424242",
                                      verification_value="100")
        stripe.api_key = self.merchant.stripe.api_key
        self.stripe = stripe

    def testCardSupported(self):
        self.credit_card.number = "5019222222222222"
        self.assertRaises(CardNotSupported,
                     lambda: self.merchant.purchase(1000, self.credit_card))

    def testCardType(self):
        self.credit_card.number = '4242424242424242'
        self.merchant.validate_card(self.credit_card)
        self.assertEquals(self.credit_card.card_type, Visa)

    def testPurchase(self):
        resp = self.merchant.purchase(1, self.credit_card)
        self.assertEquals(resp["status"], "SUCCESS")

    def testPurchaseDecimalAmount(self):
        resp = self.merchant.purchase(1.99, self.credit_card)
        self.assertEquals(resp["status"], "SUCCESS")

    def testStoreMissingCustomer(self):
        self.assertRaises(TypeError, self.merchant.store)

    def testStoreWithoutBillingAddress(self):
        resp = self.merchant.store(self.credit_card)
        self.assertEquals(resp["status"], "SUCCESS")
        self.assertEquals(resp["response"].active_card.exp_month, self.credit_card.month)
        self.assertEquals(resp["response"].active_card.exp_year, self.credit_card.year)
        self.assertTrue(getattr(resp["response"], "id"))
        self.assertTrue(getattr(resp["response"], "created"))

    def testUnstore(self):
        resp = self.merchant.store(self.credit_card)
        self.assertEquals(resp["status"], "SUCCESS")
        response = self.merchant.unstore(resp["response"].id)
        self.assertEquals(response["status"], "SUCCESS")

    def testRecurring1(self):
        plan_id = "test_plan"
        try:
            plan = self.stripe.Plan.retrieve(plan_id)
        except self.stripe.InvalidRequestError:
            response = self.stripe.Plan.create(
                amount=1000,
                interval='month',
                name="Test Plan",
                currency="usd",
                id=plan_id)
        options = {"plan_id": plan_id}
        resp = self.merchant.recurring(self.credit_card, options=options)
        self.assertEquals(resp["status"], "SUCCESS")
        subscription = resp["response"].subscription
        self.assertEquals(subscription.status, "active")

    def testCredit(self):
        resp = self.merchant.purchase(1, self.credit_card)
        self.assertEquals(resp["status"], "SUCCESS")
        identification = resp["response"].id
        resp = self.merchant.credit(identification=identification)
        self.assertEquals(resp["status"], "SUCCESS")

    def testAuthorizeAndCapture(self):
        resp = self.merchant.authorize(100, self.credit_card)
        self.assertEquals(resp["status"], "SUCCESS")
        response = self.merchant.capture(50, resp["response"].id)
        self.assertEquals(response["status"], "SUCCESS")

    def testPurchaseWithToken(self):
        # Somewhat similar to capture but testing for the
        # purpose of the stripe integration
        resp = self.merchant.authorize(1, self.credit_card)
        resp = self.merchant.purchase(1, resp["response"].id)
        self.assertEquals(resp["status"], "SUCCESS")

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls import *
from billing import get_integration

pay_pal = get_integration("pay_pal")
fps = get_integration("amazon_fps")
braintree = get_integration("braintree_payments")

urlpatterns = patterns('',
      ('^paypal-ipn-url/', include(pay_pal.urls)),
      ('^fps/', include(fps.urls)),
      ('^braintree/', include(braintree.urls)),
)

########NEW FILE########
__FILENAME__ = utils
import re

from django.test.utils import compare_xml
from lxml import etree


class BetterXMLCompareMixin(object):

    maxDiff = None

    def assertXMLEqual(self, expected, actual):
        if not compare_xml(actual, expected):
            self.assertMultiLineEqual(self.norm_whitespace(expected),
                                      self.norm_whitespace(actual))

    def norm_whitespace(self, v):
        v = re.sub(b"^ *", b"", v, flags=re.MULTILINE)
        v = re.sub(b"\n", b"", v)
        v = re.sub(b"\t", b"", v)
        return etree.tostring(etree.fromstring(v), pretty_print=True)


########NEW FILE########
__FILENAME__ = world_pay_tests
from urllib2 import urlparse
from xml.dom import minidom

from django.test import TestCase
from django.template import Template, Context
from django.conf import settings
from django.utils.unittest.case import skipIf

from billing import get_integration


@skipIf(not settings.MERCHANT_SETTINGS.get("world_pay", None), "WorldPay integration not configured")
class WorldPayTestCase(TestCase):
    def setUp(self):
        self.wp = get_integration("world_pay")
        fields = {
            "cartId": "TEST123",
            "amount": "1",
            "currency": "USD",
            "testMode": "100",
            "futurePayType": "regular",
            "option": "0",
            "noOfPayments": "12",
            "intervalUnit": "3",
            "intervalMult": "1",
            "normalAmount": "1",
            "startDelayUnit": "3",
            "startDelayMult": "1",
            "instId": "12345",
            "signatureFields": "instId:amount:cartId",
        }
        self.wp.add_fields(fields)

    def assertFormIsCorrect(self, form, fields):
        dom = minidom.parseString(form)
        inputs = dom.getElementsByTagName('input')
        values_dict = {}
        for el in inputs:
            if el.attributes['type'].value == 'hidden' and el.hasAttribute('value'):
                values_dict[el.attributes['name'].value] = el.attributes['value'].value
        self.assertDictContainsSubset(values_dict, fields)

        form_action_url = dom.getElementsByTagName('form')[0].attributes['action'].value
        parsed = urlparse.urlparse(form_action_url)

        self.assertEquals(parsed.scheme, 'https')
        self.assertEquals(parsed.netloc, 'select-test.worldpay.com')
        self.assertEquals(parsed.path, '/wcc/purchase')

    def testFormGen(self):
        # Since the secret key cannot be distributed
        settings.WORLDPAY_MD5_SECRET_KEY = "test"
        tmpl = Template("{% load render_integration from billing_tags %}{% render_integration obj %}")
        form = tmpl.render(Context({"obj": self.wp}))
        self.assertFormIsCorrect(form, self.wp.fields)

    def testFormGen2(self):
        # Since the secret key cannot be distributed
        settings.WORLDPAY_MD5_SECRET_KEY = "test"
        self.wp.add_field("signatureFields", "instId:amount:currency:cartId")
        self.wp.fields.pop("signature", None)
        tmpl = Template("{% load render_integration from billing_tags %}{% render_integration obj %}")
        form = tmpl.render(Context({"obj": self.wp}))
        self.assertFormIsCorrect(form, self.wp.fields)

########NEW FILE########
__FILENAME__ = countries
# -*- coding: utf-8 -*-
# vim:tabstop=4:expandtab:sw=4:softtabstop=4
from django.utils.translation import ugettext_lazy as _

# List taken from http://www.iso.org/iso/english_country_names_and_code_elements
COUNTRY_CODE = {
    "AFGHANISTAN": "AF",
    "ÅLAND ISLANDS": "AX",
    "ALBANIA": "AL",
    "ALGERIA": "DZ",
    "AMERICAN SAMOA": "AS",
    "ANDORRA": "AD",
    "ANGOLA": "AO",
    "ANGUILLA": "AI",
    "ANTARCTICA": "AQ",
    "ANTIGUA AND BARBUDA": "AG",
    "ARGENTINA": "AR",
    "ARMENIA": "AM",
    "ARUBA": "AW",
    "AUSTRALIA": "AU",
    "AUSTRIA": "AT",
    "AZERBAIJAN": "AZ",
    "BAHAMAS": "BS",
    "BAHRAIN": "BH",
    "BANGLADESH": "BD",
    "BARBADOS": "BB",
    "BELARUS": "BY",
    "BELGIUM": "BE",
    "BELIZE": "BZ",
    "BENIN": "BJ",
    "BERMUDA": "BM",
    "BHUTAN": "BT",
    "BOLIVIA, PLURINATIONAL STATE OF": "BO",
    "BOSNIA AND HERZEGOVINA": "BA",
    "BOTSWANA": "BW",
    "BOUVET ISLAND": "BV",
    "BRAZIL": "BR",
    "BRITISH INDIAN OCEAN TERRITORY": "IO",
    "BRUNEI DARUSSALAM": "BN",
    "BULGARIA": "BG",
    "BURKINA FASO": "BF",
    "BURUNDI": "BI",
    "CAMBODIA": "KH",
    "CAMEROON": "CM",
    "CANADA": "CA",
    "CAPE VERDE": "CV",
    "CAYMAN ISLANDS": "KY",
    "CENTRAL AFRICAN REPUBLIC": "CF",
    "CHAD": "TD",
    "CHILE": "CL",
    "CHINA": "CN",
    "CHRISTMAS ISLAND": "CX",
    "COCOS (KEELING) ISLANDS": "CC",
    "COLOMBIA": "CO",
    "COMOROS": "KM",
    "CONGO": "CG",
    "CONGO, THE DEMOCRATIC REPUBLIC OF THE": "CD",
    "COOK ISLANDS": "CK",
    "COSTA RICA": "CR",
    "CÔTE D'IVOIRE": "CI",
    "CROATIA": "HR",
    "CUBA": "CU",
    "CYPRUS": "CY",
    "CZECH REPUBLIC": "CZ",
    "DENMARK": "DK",
    "DJIBOUTI": "DJ",
    "DOMINICA": "DM",
    "DOMINICAN REPUBLIC": "DO",
    "ECUADOR": "EC",
    "EGYPT": "EG",
    "EL SALVADOR": "SV",
    "EQUATORIAL GUINEA": "GQ",
    "ERITREA": "ER",
    "ESTONIA": "EE",
    "ETHIOPIA": "ET",
    "FALKLAND ISLANDS (MALVINAS)": "FK",
    "FAROE ISLANDS": "FO",
    "FIJI": "FJ",
    "FINLAND": "FI",
    "FRANCE": "FR",
    "FRENCH GUIANA": "GF",
    "FRENCH POLYNESIA": "PF",
    "FRENCH SOUTHERN TERRITORIES": "TF",
    "GABON": "GA",
    "GAMBIA": "GM",
    "GEORGIA": "GE",
    "GERMANY": "DE",
    "GHANA": "GH",
    "GIBRALTAR": "GI",
    "GREECE": "GR",
    "GREENLAND": "GL",
    "GRENADA": "GD",
    "GUADELOUPE": "GP",
    "GUAM": "GU",
    "GUATEMALA": "GT",
    "GUERNSEY": "GG",
    "GUINEA": "GN",
    "GUINEA-BISSAU": "GW",
    "GUYANA": "GY",
    "HAITI": "HT",
    "HEARD ISLAND AND MCDONALD ISLANDS": "HM",
    "HOLY SEE (VATICAN CITY STATE)": "VA",
    "HONDURAS": "HN",
    "HONG KONG": "HK",
    "HUNGARY": "HU",
    "ICELAND": "IS",
    "INDIA": "IN",
    "INDONESIA": "ID",
    "IRAN, ISLAMIC REPUBLIC OF": "IR",
    "IRAQ": "IQ",
    "IRELAND": "IE",
    "ISLE OF MAN": "IM",
    "ISRAEL": "IL",
    "ITALY": "IT",
    "JAMAICA": "JM",
    "JAPAN": "JP",
    "JERSEY": "JE",
    "JORDAN": "JO",
    "KAZAKHSTAN": "KZ",
    "KENYA": "KE",
    "KIRIBATI": "KI",
    "KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF": "KP",
    "KOREA, REPUBLIC OF": "KR",
    "KUWAIT": "KW",
    "KYRGYZSTAN": "KG",
    "LAO PEOPLE'S DEMOCRATIC REPUBLIC": "LA",
    "LATVIA": "LV",
    "LEBANON": "LB",
    "LESOTHO": "LS",
    "LIBERIA": "LR",
    "LIBYAN ARAB JAMAHIRIYA": "LY",
    "LIECHTENSTEIN": "LI",
    "LITHUANIA": "LT",
    "LUXEMBOURG": "LU",
    "MACAO": "MO",
    "MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF": "MK",
    "MADAGASCAR": "MG",
    "MALAWI": "MW",
    "MALAYSIA": "MY",
    "MALDIVES": "MV",
    "MALI": "ML",
    "MALTA": "MT",
    "MARSHALL ISLANDS": "MH",
    "MARTINIQUE": "MQ",
    "MAURITANIA": "MR",
    "MAURITIUS": "MU",
    "MAYOTTE": "YT",
    "MEXICO": "MX",
    "MICRONESIA, FEDERATED STATES OF": "FM",
    "MOLDOVA, REPUBLIC OF": "MD",
    "MONACO": "MC",
    "MONGOLIA": "MN",
    "MONTENEGRO": "ME",
    "MONTSERRAT": "MS",
    "MOROCCO": "MA",
    "MOZAMBIQUE": "MZ",
    "MYANMAR": "MM",
    "NAMIBIA": "NA",
    "NAURU": "NR",
    "NEPAL": "NP",
    "NETHERLANDS": "NL",
    "NETHERLANDS ANTILLES": "AN",
    "NEW CALEDONIA": "NC",
    "NEW ZEALAND": "NZ",
    "NICARAGUA": "NI",
    "NIGER": "NE",
    "NIGERIA": "NG",
    "NIUE": "NU",
    "NORFOLK ISLAND": "NF",
    "NORTHERN MARIANA ISLANDS": "MP",
    "NORWAY": "NO",
    "OMAN": "OM",
    "PAKISTAN": "PK",
    "PALAU": "PW",
    "PALESTINIAN TERRITORY, OCCUPIED": "PS",
    "PANAMA": "PA",
    "PAPUA NEW GUINEA": "PG",
    "PARAGUAY": "PY",
    "PERU": "PE",
    "PHILIPPINES": "PH",
    "PITCAIRN": "PN",
    "POLAND": "PL",
    "PORTUGAL": "PT",
    "PUERTO RICO": "PR",
    "QATAR": "QA",
    "RÉUNION": "RE",
    "ROMANIA": "RO",
    "RUSSIAN FEDERATION": "RU",
    "RWANDA": "RW",
    "SAINT BARTHÉLEMY": "BL",
    "SAINT HELENA, ASCENSION AND TRISTAN DA CUNHA": "SH",
    "SAINT KITTS AND NEVIS": "KN",
    "SAINT LUCIA": "LC",
    "SAINT MARTIN": "MF",
    "SAINT PIERRE AND MIQUELON": "PM",
    "SAINT VINCENT AND THE GRENADINES": "VC",
    "SAMOA": "WS",
    "SAN MARINO": "SM",
    "SAO TOME AND PRINCIPE": "ST",
    "SAUDI ARABIA": "SA",
    "SENEGAL": "SN",
    "SERBIA": "RS",
    "SEYCHELLES": "SC",
    "SIERRA LEONE": "SL",
    "SINGAPORE": "SG",
    "SLOVAKIA": "SK",
    "SLOVENIA": "SI",
    "SOLOMON ISLANDS": "SB",
    "SOMALIA": "SO",
    "SOUTH AFRICA": "ZA",
    "SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS": "GS",
    "SPAIN": "ES",
    "SRI LANKA": "LK",
    "SUDAN": "SD",
    "SURINAME": "SR",
    "SVALBARD AND JAN MAYEN": "SJ",
    "SWAZILAND": "SZ",
    "SWEDEN": "SE",
    "SWITZERLAND": "CH",
    "SYRIAN ARAB REPUBLIC": "SY",
    "TAIWAN, PROVINCE OF CHINA": "TW",
    "TAJIKISTAN": "TJ",
    "TANZANIA, UNITED REPUBLIC OF": "TZ",
    "THAILAND": "TH",
    "TIMOR-LESTE": "TL",
    "TOGO": "TG",
    "TOKELAU": "TK",
    "TONGA": "TO",
    "TRINIDAD AND TOBAGO": "TT",
    "TUNISIA": "TN",
    "TURKEY": "TR",
    "TURKMENISTAN": "TM",
    "TURKS AND CAICOS ISLANDS": "TC",
    "TUVALU": "TV",
    "UGANDA": "UG",
    "UKRAINE": "UA",
    "UNITED ARAB EMIRATES": "AE",
    "UNITED KINGDOM": "GB",
    "UNITED STATES": "US",
    "UNITED STATES MINOR OUTLYING ISLANDS": "UM",
    "URUGUAY": "UY",
    "UZBEKISTAN": "UZ",
    "VANUATU": "VU",
    "VENEZUELA, BOLIVARIAN REPUBLIC OF": "VE",
    "VIET NAM": "VN",
    "VIRGIN ISLANDS, BRITISH": "VG",
    "VIRGIN ISLANDS, U.S": "VI",
    "WALLIS AND FUTUNA": "WF",
    "WESTERN SAHARA": "EH",
    "YEMEN": "YE",
    "ZAMBIA": "ZM",
    "ZIMBABWE": "ZW",
}

#List taken from https://bitbucket.org/smileychris/django-countries/
# Nicely titled (and translatable) country names.
COUNTRIES = (
    ('AF', _(u'Afghanistan')),
    ('AX', _(u'\xc5land Islands')),
    ('AL', _(u'Albania')),
    ('DZ', _(u'Algeria')),
    ('AS', _(u'American Samoa')),
    ('AD', _(u'Andorra')),
    ('AO', _(u'Angola')),
    ('AI', _(u'Anguilla')),
    ('AQ', _(u'Antarctica')),
    ('AG', _(u'Antigua and Barbuda')),
    ('AR', _(u'Argentina')),
    ('AM', _(u'Armenia')),
    ('AW', _(u'Aruba')),
    ('AU', _(u'Australia')),
    ('AT', _(u'Austria')),
    ('AZ', _(u'Azerbaijan')),
    ('BS', _(u'Bahamas')),
    ('BH', _(u'Bahrain')),
    ('BD', _(u'Bangladesh')),
    ('BB', _(u'Barbados')),
    ('BY', _(u'Belarus')),
    ('BE', _(u'Belgium')),
    ('BZ', _(u'Belize')),
    ('BJ', _(u'Benin')),
    ('BM', _(u'Bermuda')),
    ('BT', _(u'Bhutan')),
    ('BO', _(u'Bolivia, Plurinational State of')),
    ('BQ', _(u'Bonaire, Sint Eustatius and Saba')),
    ('BA', _(u'Bosnia and Herzegovina')),
    ('BW', _(u'Botswana')),
    ('BV', _(u'Bouvet Island')),
    ('BR', _(u'Brazil')),
    ('IO', _(u'British Indian Ocean Territory')),
    ('BN', _(u'Brunei Darussalam')),
    ('BG', _(u'Bulgaria')),
    ('BF', _(u'Burkina Faso')),
    ('BI', _(u'Burundi')),
    ('KH', _(u'Cambodia')),
    ('CM', _(u'Cameroon')),
    ('CA', _(u'Canada')),
    ('CV', _(u'Cape Verde')),
    ('KY', _(u'Cayman Islands')),
    ('CF', _(u'Central African Republic')),
    ('TD', _(u'Chad')),
    ('CL', _(u'Chile')),
    ('CN', _(u'China')),
    ('CX', _(u'Christmas Island')),
    ('CC', _(u'Cocos (Keeling) Islands')),
    ('CO', _(u'Colombia')),
    ('KM', _(u'Comoros')),
    ('CG', _(u'Congo')),
    ('CD', _(u'Congo, The Democratic Republic of the')),
    ('CK', _(u'Cook Islands')),
    ('CR', _(u'Costa Rica')),
    ('CI', _(u"C\xf4te D'ivoire")),
    ('HR', _(u'Croatia')),
    ('CU', _(u'Cuba')),
    ('CW', _(u'Cura\xe7ao')),
    ('CY', _(u'Cyprus')),
    ('CZ', _(u'Czech Republic')),
    ('DK', _(u'Denmark')),
    ('DJ', _(u'Djibouti')),
    ('DM', _(u'Dominica')),
    ('DO', _(u'Dominican Republic')),
    ('EC', _(u'Ecuador')),
    ('EG', _(u'Egypt')),
    ('SV', _(u'El Salvador')),
    ('GQ', _(u'Equatorial Guinea')),
    ('ER', _(u'Eritrea')),
    ('EE', _(u'Estonia')),
    ('ET', _(u'Ethiopia')),
    ('FK', _(u'Falkland Islands (Malvinas)')),
    ('FO', _(u'Faroe Islands')),
    ('FJ', _(u'Fiji')),
    ('FI', _(u'Finland')),
    ('FR', _(u'France')),
    ('GF', _(u'French Guiana')),
    ('PF', _(u'French Polynesia')),
    ('TF', _(u'French Southern Territories')),
    ('GA', _(u'Gabon')),
    ('GM', _(u'Gambia')),
    ('GE', _(u'Georgia')),
    ('DE', _(u'Germany')),
    ('GH', _(u'Ghana')),
    ('GI', _(u'Gibraltar')),
    ('GR', _(u'Greece')),
    ('GL', _(u'Greenland')),
    ('GD', _(u'Grenada')),
    ('GP', _(u'Guadeloupe')),
    ('GU', _(u'Guam')),
    ('GT', _(u'Guatemala')),
    ('GG', _(u'Guernsey')),
    ('GN', _(u'Guinea')),
    ('GW', _(u'Guinea-bissau')),
    ('GY', _(u'Guyana')),
    ('HT', _(u'Haiti')),
    ('HM', _(u'Heard Island and McDonald Islands')),
    ('VA', _(u'Holy See (Vatican City State)')),
    ('HN', _(u'Honduras')),
    ('HK', _(u'Hong Kong')),
    ('HU', _(u'Hungary')),
    ('IS', _(u'Iceland')),
    ('IN', _(u'India')),
    ('ID', _(u'Indonesia')),
    ('IR', _(u'Iran, Islamic Republic of')),
    ('IQ', _(u'Iraq')),
    ('IE', _(u'Ireland')),
    ('IM', _(u'Isle of Man')),
    ('IL', _(u'Israel')),
    ('IT', _(u'Italy')),
    ('JM', _(u'Jamaica')),
    ('JP', _(u'Japan')),
    ('JE', _(u'Jersey')),
    ('JO', _(u'Jordan')),
    ('KZ', _(u'Kazakhstan')),
    ('KE', _(u'Kenya')),
    ('KI', _(u'Kiribati')),
    ('KP', _(u"Korea, Democratic People's Republic of")),
    ('KR', _(u'Korea, Republic of')),
    ('KW', _(u'Kuwait')),
    ('KG', _(u'Kyrgyzstan')),
    ('LA', _(u"Lao People's Democratic Republic")),
    ('LV', _(u'Latvia')),
    ('LB', _(u'Lebanon')),
    ('LS', _(u'Lesotho')),
    ('LR', _(u'Liberia')),
    ('LY', _(u'Libyan Arab Jamahiriya')),
    ('LI', _(u'Liechtenstein')),
    ('LT', _(u'Lithuania')),
    ('LU', _(u'Luxembourg')),
    ('MO', _(u'Macao')),
    ('MK', _(u'Macedonia, The Former Yugoslav Republic of')),
    ('MG', _(u'Madagascar')),
    ('MW', _(u'Malawi')),
    ('MY', _(u'Malaysia')),
    ('MV', _(u'Maldives')),
    ('ML', _(u'Mali')),
    ('MT', _(u'Malta')),
    ('MH', _(u'Marshall Islands')),
    ('MQ', _(u'Martinique')),
    ('MR', _(u'Mauritania')),
    ('MU', _(u'Mauritius')),
    ('YT', _(u'Mayotte')),
    ('MX', _(u'Mexico')),
    ('FM', _(u'Micronesia, Federated States of')),
    ('MD', _(u'Moldova, Republic of')),
    ('MC', _(u'Monaco')),
    ('MN', _(u'Mongolia')),
    ('ME', _(u'Montenegro')),
    ('MS', _(u'Montserrat')),
    ('MA', _(u'Morocco')),
    ('MZ', _(u'Mozambique')),
    ('MM', _(u'Myanmar')),
    ('NA', _(u'Namibia')),
    ('NR', _(u'Nauru')),
    ('NP', _(u'Nepal')),
    ('NL', _(u'Netherlands')),
    ('NC', _(u'New Caledonia')),
    ('NZ', _(u'New Zealand')),
    ('NI', _(u'Nicaragua')),
    ('NE', _(u'Niger')),
    ('NG', _(u'Nigeria')),
    ('NU', _(u'Niue')),
    ('NF', _(u'Norfolk Island')),
    ('MP', _(u'Northern Mariana Islands')),
    ('NO', _(u'Norway')),
    ('OM', _(u'Oman')),
    ('PK', _(u'Pakistan')),
    ('PW', _(u'Palau')),
    ('PS', _(u'Palestinian Territory, Occupied')),
    ('PA', _(u'Panama')),
    ('PG', _(u'Papua New Guinea')),
    ('PY', _(u'Paraguay')),
    ('PE', _(u'Peru')),
    ('PH', _(u'Philippines')),
    ('PN', _(u'Pitcairn')),
    ('PL', _(u'Poland')),
    ('PT', _(u'Portugal')),
    ('PR', _(u'Puerto Rico')),
    ('QA', _(u'Qatar')),
    ('RE', _(u'R\xe9union')),
    ('RO', _(u'Romania')),
    ('RU', _(u'Russian Federation')),
    ('RW', _(u'Rwanda')),
    ('BL', _(u'Saint Barth\xe9lemy')),
    ('SH', _(u'Saint Helena, Ascension and Tristan Da Cunha')),
    ('KN', _(u'Saint Kitts and Nevis')),
    ('LC', _(u'Saint Lucia')),
    ('MF', _(u'Saint Martin (French Part)')),
    ('PM', _(u'Saint Pierre and Miquelon')),
    ('VC', _(u'Saint Vincent and the Grenadines')),
    ('WS', _(u'Samoa')),
    ('SM', _(u'San Marino')),
    ('ST', _(u'Sao Tome and Principe')),
    ('SA', _(u'Saudi Arabia')),
    ('SN', _(u'Senegal')),
    ('RS', _(u'Serbia')),
    ('SC', _(u'Seychelles')),
    ('SL', _(u'Sierra Leone')),
    ('SG', _(u'Singapore')),
    ('SX', _(u'Sint Maarten (Dutch Part)')),
    ('SK', _(u'Slovakia')),
    ('SI', _(u'Slovenia')),
    ('SB', _(u'Solomon Islands')),
    ('SO', _(u'Somalia')),
    ('ZA', _(u'South Africa')),
    ('GS', _(u'South Georgia and the South Sandwich Islands')),
    ('SS', _(u'South Sudan')),
    ('ES', _(u'Spain')),
    ('LK', _(u'Sri Lanka')),
    ('SD', _(u'Sudan')),
    ('SR', _(u'Suriname')),
    ('SJ', _(u'Svalbard and Jan Mayen')),
    ('SZ', _(u'Swaziland')),
    ('SE', _(u'Sweden')),
    ('CH', _(u'Switzerland')),
    ('SY', _(u'Syrian Arab Republic')),
    ('TW', _(u'Taiwan, Province of China')),
    ('TJ', _(u'Tajikistan')),
    ('TZ', _(u'Tanzania, United Republic of')),
    ('TH', _(u'Thailand')),
    ('TL', _(u'Timor-leste')),
    ('TG', _(u'Togo')),
    ('TK', _(u'Tokelau')),
    ('TO', _(u'Tonga')),
    ('TT', _(u'Trinidad and Tobago')),
    ('TN', _(u'Tunisia')),
    ('TR', _(u'Turkey')),
    ('TM', _(u'Turkmenistan')),
    ('TC', _(u'Turks and Caicos Islands')),
    ('TV', _(u'Tuvalu')),
    ('UG', _(u'Uganda')),
    ('UA', _(u'Ukraine')),
    ('AE', _(u'United Arab Emirates')),
    ('GB', _(u'United Kingdom')),
    ('US', _(u'United States')),
    ('UM', _(u'United States Minor Outlying Islands')),
    ('UY', _(u'Uruguay')),
    ('UZ', _(u'Uzbekistan')),
    ('VU', _(u'Vanuatu')),
    ('VE', _(u'Venezuela, Bolivarian Republic of')),
    ('VN', _(u'Viet Nam')),
    ('VG', _(u'Virgin Islands, British')),
    ('VI', _(u'Virgin Islands, U.S.')),
    ('WF', _(u'Wallis and Futuna')),
    ('EH', _(u'Western Sahara')),
    ('YE', _(u'Yemen')),
    ('ZM', _(u'Zambia')),
    ('ZW', _(u'Zimbabwe')),
)
########NEW FILE########
__FILENAME__ = credit_card
import calendar
import re
import datetime


class InvalidCard(Exception):
    pass


class CardNotSupported(Exception):
    pass


class CreditCard(object):
    # The regexp attribute should be overriden by the subclasses.
    # Attribute value should be a regexp instance
    regexp = None
    # Has to be set by the user after calling `validate_card`
    # method on the gateway
    card_type = None
    # Required mainly for PayPal. PayPal expects to be sent
    # the card type also with the requests.
    card_name = None

    def __init__(self, **kwargs):
        if ("first_name" not in kwargs
            or "last_name" not in kwargs) and "cardholders_name" not in kwargs:
            raise TypeError("You must provide cardholders_name or first_name and last_name")
        self.first_name = kwargs.get("first_name", None)
        self.last_name = kwargs.get("last_name", None)
        self.cardholders_name = kwargs.get("cardholders_name", None)
        self.month = int(kwargs["month"])
        self.year = int(kwargs["year"])
        self.number = kwargs["number"]
        self.verification_value = kwargs["verification_value"]

    def is_luhn_valid(self):
        """Checks the validity of card number by using Luhn Algorithm.
        Please see http://en.wikipedia.org/wiki/Luhn_algorithm for details."""
        try:
            num = [int(x) for x in str(self.number)]
        except ValueError:
            return False
        return not sum(num[::-2] + [sum(divmod(d * 2, 10)) for d in num[-2::-2]]) % 10

    def is_expired(self):
        """Check whether the credit card is expired or not"""
        return datetime.date.today() > datetime.date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])

    def valid_essential_attributes(self):
        """Validate that all the required attributes of card are given"""
        return (((self.first_name and
                  self.last_name) or
                 self.cardholders_name)
                and self.month
                and self.year
                and self.number
                and self.verification_value)

    def is_valid(self):
        """Check the validity of the card"""
        return self.is_luhn_valid() and \
               not self.is_expired() and \
               self.valid_essential_attributes()

    @property
    def expire_date(self):
        """Returns the expiry date of the card in MM-YYYY format"""
        return '%02d-%04d' % (self.month, self.year)

    @property
    def name(self):
        """Concat first name and last name of the card holder"""
        return '%s %s' % (self.first_name, self.last_name)


class Visa(CreditCard):
    card_name = "Visa"
    regexp = re.compile('^4\d{12}(\d{3})?$')


class MasterCard(CreditCard):
    card_name = "MasterCard"
    regexp = re.compile('^(5[1-5]\d{4}|677189)\d{10}$')


class Discover(CreditCard):
    card_name = "Discover"
    regexp = re.compile('^(6011|65\d{2})\d{12}$')


class AmericanExpress(CreditCard):
    card_name = "Amex"
    regexp = re.compile('^3[47]\d{13}$')


class DinersClub(CreditCard):
    card_name = "DinersClub"
    regexp = re.compile('^3(0[0-5]|[68]\d)\d{11}$')


class JCB(CreditCard):
    card_name = "JCB"
    regexp = re.compile('^35(28|29|[3-8]\d)\d{12}$')


class Switch(CreditCard):
    # Debit Card
    card_name = "Switch"
    regexp = re.compile('^6759\d{12}(\d{2,3})?$')


class Solo(CreditCard):
    # Debit Card
    card_name = "Solo"
    regexp = re.compile('^6767\d{12}(\d{2,3})?$')


class Dankort(CreditCard):
    # Debit cum Credit Card
    card_name = "Dankort"
    regexp = re.compile('^5019\d{12}$')


class Maestro(CreditCard):
    # Debit Card
    card_name = "Maestro"
    regexp = re.compile('^(5[06-8]|6\d)\d{10,17}$')


class Forbrugsforeningen(CreditCard):
    card_name = "Forbrugsforeningen"
    regexp = re.compile('^600722\d{10}$')


class Laser(CreditCard):
    # Debit Card
    card_name = "Laser"
    regexp = re.compile('^(6304|6706|6771|6709)\d{8}(\d{4}|\d{6,7})?$')

# A few helpful (probably) attributes
all_credit_cards = [Visa, MasterCard, Discover, AmericanExpress,
                    DinersClub, JCB]

all_debit_cards = [Switch, Solo, Dankort, Maestro,
                    Forbrugsforeningen, Laser]

all_cards = all_credit_cards + all_debit_cards

########NEW FILE########
__FILENAME__ = json


# Utilties for building functions to pass to json.loads and json.dumps
# for custom encoding/decoding.

def chain_custom_encoders(encoders):
    def combined_encoder(obj):
        for encoder in encoders:
            try:
                return encoder(obj)
            except TypeError:
                continue
        raise TypeError("Unknown type %s" % obj.__class__)
    return combined_encoder


def chain_custom_decoders(decoders):
    def combined_decoder(dct):
        for decoder in decoders:
            dct = decoder(dct)
            if not hasattr(dct, '__getitem__'):
                # Already changed
                return dct
        return dct
    return combined_decoder

########NEW FILE########
__FILENAME__ = paylane
# -*- coding: utf-8 -*-
# vim:tabstop=4:expandtab:sw=4:softtabstop=4
"""
Example usage:

from billing.utils.credit_card import Visa

product = PaylanePaymentProduct(description='Some description')
customer_address = PaylanePaymentCustomerAddress(street_house='',city='',state='',zip_code='',country_code='PT')
customer = PaylanePaymentCustomer(name='',email='',ip_address='127.0.0.1',address=customer_address)
pp = PaylanePayment(credit_card=Visa(),customer=customer,amount=0.01,product=product)
"""


class PaylanePaymentCustomerAddress(object):
    def __init__(self, street_house=None, city=None, state=None, zip_code=None, country_code=None):
        self.street_house = street_house
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.country_code = country_code


class PaylanePaymentCustomer(object):
    def __init__(self, name=None, email=None, ip_address=None, address=None):
        self.name = name
        self.email = email
        self.ip_address = ip_address
        self.address = address


class PaylanePaymentProduct(object):
    def __init__(self, description=None):
        self.description = description


class PaylanePayment(object):
    def __init__(self, credit_card=None, customer=None, amount=0.0, product=None):
        self.credit_card = credit_card
        self.customer = customer
        self.amount = amount
        self.product = product


class PaylaneError(object):
    ERR_INVALID_ACCOUNT_HOLDER_NAME = 312
    ERR_INVALID_CUSTOMER_NAME = 313
    ERR_INVALID_CUSTOMER_EMAIL = 314
    ERR_INVALID_CUSTOMER_ADDRESS = 315
    ERR_INVALID_CUSTOMER_CITY = 316
    ERR_INVALID_CUSTOMER_ZIP = 317
    ERR_INVALID_CUSTOMER_STATE = 318
    ERR_INVALID_CUSTOMER_COUNTRY = 319
    ERR_INVALID_AMOUNT = 320
    ERR_AMOUNT_TOO_LOW = 321
    ERR_INVALID_CURRENCY_CODE = 322
    ERR_INVALID_CUSTOMER_IP = 323
    ERR_INVALID_DESCRIPTION = 324
    ERR_INVALID_ACCOUNT_COUNTRY = 325
    ERR_INVALID_BANK_CODE = 326
    ERR_INVALID_ACCOUNT_NUMBER = 327
    ERR_UNKNOWN_PAYMENT_METHOD = 405
    ERR_TOO_MANY_PAYMENT_METHODS = 406
    ERR_CANNOT_CAPTURE_LATER = 407
    ERR_FEATURE_NOT_AVAILABLE = 408
    ERR_CANNOT_OVERRIDE_FEATURE = 409
    ERR_UNSUPPORTED_PAYMENT_METHOD = 410
    ERR_INVALID_CARD_NUMBER_FORMAT = 411
    ERR_INVALID_EXPIRATION_YEAR = 412
    ERR_INVALID_EXPIRATION_MONTH = 413
    ERR_EXPIRATION_YEAR_PAST = 414
    ERR_CARD_EXPIRED = 415
    ERR_INVALID_CARD_NAME = 417
    ERR_INVALID_CARDHOLDER_NAME = 418
    ERR_INVALID_CARDHOLDER_EMAIL = 419
    ERR_INVALID_CARDHOLDER_ADDRESS = 420
    ERR_INVALID_CARDHOLDER_CITY = 421
    ERR_INVALID_CARDHOLDER_ZIP = 422
    ERR_INVALID_CARDHOLDER_STATE = 423
    ERR_INVALID_CARDHOLDER_COUNTRY = 424
    ERR_INVALID_AMOUNT2 = 425
    ERR_AMOUNT_TOO_LOW2 = 426
    ERR_INVALID_CURRENCY_CODE2 = 427
    ERR_INVALID_CLIENT_IP = 428
    ERR_INVALID_DESCRIPTION2 = 429
    ERR_UNKNOWN_CARD_TYPE_NUMBER = 430
    ERR_INVALID_CARD_ISSUE_NUMBER = 431
    ERR_CANNOT_FRAUD_CHECK = 432
    ERR_INVALID_AVS_LEVEL = 433
    ERR_INVALID_SALE_ID = 441
    ERR_SALE_AUTHORIZATION_NOT_FOUND = 442
    ERR_CAPTURE_EXCEEDS_AUTHORIZATION_AMOUNT = 443
    ERR_TRANSACTION_LOCK = 401
    ERR_GATEWAY_PROBLEM = 402
    ERR_CARD_DECLINED = 403
    ERR_CURRENCY_NOT_ALLOWED = 404
    ERR_CARD_CODE_INVALID = 416
    ERR_CARD_CODE_MANDATORY = 470
    ERR_INVALID_SALE_ID = 471
    ERR_INVALID_RESALE_AMOUNT = 472
    ERR_RESALE_AMOUNT_TOO_LOW = 473
    ERR_INVALID_RESALE_CURRENCY = 474
    ERR_INVALID_RESALE_DESCRIPTION = 475
    ERR_SALE_ID_NOT_FOUND = 476
    ERR_RESALE_WITH_CHARGEBACK = 477
    ERR_CANNOT_RESALE_SALE = 478
    ERR_RESALE_CARD_EXPIRED = 479
    ERR_RESALE_WITH_REVERSAL = 480
    ERR_CANNOT_REFUND_SALE = 488
    ERR_INTERNAL_ERROR = 501
    ERR_GATEWAY_ERROR = 502
    ERR_METHOD_NOT_ALLOWED = 503
    ERR_INACTIVE_MERCHANT = 505
    ERR_FRAUD_DETECTED = 601
    ERR_BLACKLISTED_NUMBER = 611
    ERR_BLACKLISTED_COUNTRY = 612
    ERR_BLACKLISTED_CARD_NUMBER = 613
    ERR_BLACKLISTED_CUSTOMER_COUNTRY = 614
    ERR_BLACKLISTED_CUSTOMER_EMAIL = 615
    ERR_BLACKLISTED_CUSTOMER_IP = 616

    def __init__(self, error_code, description, acquirer_error=None, acquirer_description=None):
        self.FRAUD_ERRORS = [self.ERR_FRAUD_DETECTED, self.ERR_BLACKLISTED_NUMBER,
                            self.ERR_BLACKLISTED_COUNTRY, self.ERR_BLACKLISTED_CARD_NUMBER,
                            self.ERR_BLACKLISTED_CUSTOMER_COUNTRY,
                            self.ERR_BLACKLISTED_CUSTOMER_EMAIL,
                            self.ERR_BLACKLISTED_CUSTOMER_IP]
        self.error_code = error_code
        self.description = description
        self.acquirer_error = acquirer_error
        self.acquirer_description = acquirer_description

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'Error Code: %s (%s). Acquirer Error: %s (%s)' % (self.error_code,
            self.description,
            self.acquirer_error,
            self.acquirer_description)

    def __unicode__(self):
        return unicode(str(self))

    @property
    def is_customer_data_error(self):
        """True if error is related to the card/account data the customer provided."""
        return self.error_code in [
                self.ERR_INVALID_ACCOUNT_HOLDER_NAME,
                self.ERR_INVALID_CUSTOMER_NAME,
                self.ERR_INVALID_CUSTOMER_EMAIL,
                self.ERR_INVALID_CUSTOMER_ADDRESS,
                self.ERR_INVALID_CUSTOMER_CITY,
                self.ERR_INVALID_CUSTOMER_ZIP,
                self.ERR_INVALID_CUSTOMER_STATE,
                self.ERR_INVALID_CUSTOMER_COUNTRY,
                self.ERR_INVALID_ACCOUNT_COUNTRY,
                self.ERR_INVALID_BANK_CODE,
                self.ERR_INVALID_ACCOUNT_NUMBER,
                self.ERR_INVALID_CARD_NAME,
                self.ERR_INVALID_CARDHOLDER_NAME,
                self.ERR_INVALID_CARDHOLDER_EMAIL,
                self.ERR_INVALID_CARDHOLDER_ADDRESS,
                self.ERR_INVALID_CARDHOLDER_CITY,
                self.ERR_INVALID_CARDHOLDER_ZIP,
                self.ERR_INVALID_CARDHOLDER_STATE,
                self.ERR_INVALID_CARDHOLDER_COUNTRY,
            ]

    @property
    def is_card_data_error(self):
        """True if error is related to the card data the customer provided."""
        return self.error_code in [
                self.ERR_UNKNOWN_CARD_TYPE_NUMBER,
                self.ERR_INVALID_CARD_ISSUE_NUMBER,
            ]

    @property
    def was_card_declined(self):
        """True if this error is related to the card being declined for some reason."""
        return self.error_code in [
                self.ERR_CARD_DECLINED,
            ] or self.is_card_expired

    @property
    def is_card_expired(self):
        """True if this error is related to card expiration."""
        return self.error_code in [
                self.ERR_CARD_EXPIRED,
                self.ERR_RESALE_CARD_EXPIRED,
            ]

    @property
    def is_recurring_impossible(self):
        """Whether this error should nullify a recurring transaction."""
        return self.error_code in [
                self.ERR_CARD_DECLINED,
                self.ERR_CARD_CODE_INVALID,
                self.ERR_CARD_CODE_MANDATORY,
                self.ERR_INVALID_SALE_ID,
                self.ERR_INVALID_RESALE_AMOUNT,
                self.ERR_RESALE_AMOUNT_TOO_LOW,
                self.ERR_SALE_ID_NOT_FOUND,
                self.ERR_RESALE_WITH_CHARGEBACK,
                self.ERR_CANNOT_RESALE_SALE,
                self.ERR_RESALE_CARD_EXPIRED,
                self.ERR_RESALE_WITH_REVERSAL,
            ]

    @property
    def is_fatal(self):
        """Whether this is a fatal error that, in principle, cannot be retried."""
        return self.error_code == self.ERR_CANNOT_REFUND_SALE or self.error_code >= 500

    @property
    def is_fraud(self):
        """Whether this is a fraud fatal error."""
        return self.error_code in self.FRAUD_ERRORS

    @property
    def can_retry_later(self):
        """Whether this resale fatal error can disappear in the future."""
        return self.error_code in [
                self.ERR_INTERNAL_ERROR,
                self.ERR_GATEWAY_ERROR,
            ]

########NEW FILE########
__FILENAME__ = required


def require(d, *args):
    for arg in args:
        if arg not in d:
            raise TypeError('Missing required parameter: %s' % (arg))

########NEW FILE########
__FILENAME__ = utilities
class Bunch(dict):
    def __init__(self, **kw):
        dict.__init__(self, kw)
        self.__dict__ = self

########NEW FILE########
__FILENAME__ = xml_parser
from xml.dom.minidom import parseString


class NotTextNodeError:
    pass


def getTextFromNode(node):
    """
    scans through all children of node and gathers the
    text. if node has non-text child-nodes, then
    NotTextNodeError is raised.
    """
    t = ""
    for n in node.childNodes:
        if n.nodeType == n.TEXT_NODE:
            t += n.nodeValue
        else:
            raise NotTextNodeError
    return t


def nodeToDic(node):
    """
        nodeToDic() scans through the children of node and makes a
        dictionary from the content. Three cases are differentiated:

        - if the node contains no other nodes, it is a text-node
        and {nodeName:text} is merged into the dictionary.

        - if the node has the attribute "method" set to "true",
        then it's children will be appended to a list and this
        list is merged to the dictionary in the form: {nodeName:list}.

        - else, nodeToDic() will call itself recursively on
        the nodes children (merging {nodeName:nodeToDic()} to
        the dictionary).
    """
    dic = {}
    multlist = {}  # holds temporary lists where there are multiple children
    multiple = False
    for n in node.childNodes:
        if n.nodeType != n.ELEMENT_NODE:
            continue
        # find out if there are multiple records
        if len(node.getElementsByTagName(n.nodeName)) > 1:
            multiple = True
            # and set up the list to hold the values
            if not n.nodeName in multlist:
                multlist[n.nodeName] = []
        else:
            multiple = False
        try:
            # text node
            text = getTextFromNode(n)
        except NotTextNodeError:
            if multiple:
                # append to our list
                multlist[n.nodeName].append(nodeToDic(n))
                dic.update({n.nodeName: multlist[n.nodeName]})
                continue
            else:
                # 'normal' node
                dic.update({n.nodeName: nodeToDic(n)})
                continue
        # text node
        if multiple:
            multlist[n.nodeName].append(text)
            dic.update({n.nodeName: multlist[n.nodeName]})
        else:
            dic.update({n.nodeName: text})
    return dic


def readConfig(filename):
    dom = parseString(open(filename).read())
    return nodeToDic(dom)

if __name__ == "__main__":
    import sys
    import pprint
    pprint.pprint(readConfig(sys.argv[1]))

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Merchant Documentation documentation build configuration file, created by
# sphinx-quickstart on Mon Oct 18 21:09:11 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Merchant Documentation'
copyright = u'2012, Team Agiliq'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.09'
# The full version, including alpha/beta/rc tags.
release = '0.09a'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'MerchantDocumentationdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'MerchantDocumentation.tex', u'Merchant Documentation Documentation',
   u'Team Agiliq', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'merchantdocumentation', u'Merchant Documentation Documentation',
     [u'Team Agiliq'], 1)
]

########NEW FILE########
__FILENAME__ = encrypt
#!/usr/bin/env python

"""
Add merchant settings as encryped env vars to .travis.yml
"""

import os

from django.core.management import setup_environ

from example.settings import local
setup_environ(local)

from django.conf import settings

from formencode.variabledecode import variable_encode

env_dict = variable_encode(settings.MERCHANT_SETTINGS, prepend='MERCHANT', dict_char='__')
for k, v in env_dict.iteritems():
    print 'adding %s' % (k)
    os.system('travis encrypt %s="%s" --add env.global' % (k, v))

########NEW FILE########
__FILENAME__ = conf
import datetime
from django.conf import settings
from django.core.urlresolvers import reverse

from billing.utils.paylane import (
    PaylanePaymentCustomer,
    PaylanePaymentCustomerAddress
)
from utils import randomword

HOST = getattr(settings, "HOST", "http://127.0.0.1")

COMMON_INITIAL = {
    'first_name': 'John',
    'last_name': 'Doe',
    'month': '06',
    'year': '2020',
    'card_type': 'visa',
    'verification_value': '000'
}

GATEWAY_INITIAL = {
    'authorize_net': {
        'number': '4222222222222',
        'card_type': 'visa',
        'verification_value': '100'
    },
    'paypal': {
        'number': '4797503429879309',
        'verification_value': '037',
        'month': 1,
        'year': 2019,
        'card_type': 'visa'
    },
    'eway': {
        'number': '4444333322221111',
        'verification_value': '000'
    },
    'braintree_payments': {
        'number': '4111111111111111',
    },
    'stripe': {
        'number': '4242424242424242',
    },
    'paylane': {
        'number': '4111111111111111',
    },
    'beanstream': {
        'number': '4030000010001234',
        'card_type': 'visa',
        'verification_value': '123'
    },
    'chargebee': {
        'number': '4111111111111111',
    }
}

INTEGRATION_INITIAL = {
    'stripe': {
        'amount': 1,
        'credit_card_number': '4222222222222',
        'credit_card_cvc': '100',
        'credit_card_expiration_month': '01',
        'credit_card_expiration_year': '2020'
    },
    'authorize_net_dpm': {
        'x_amount': 1,
        'x_fp_sequence': datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
        'x_fp_timestamp': datetime.datetime.now().strftime('%s'),
        'x_recurring_bill': 'F',
        'x_card_num': '4007000000027',
        'x_exp_date': '01/20',
        'x_card_code': '100',
        'x_first_name': 'John',
        'x_last_name': 'Doe',
        'x_address': '100, Spooner Street, Springfield',
        'x_city': 'San Francisco',
        'x_state': 'California',
        'x_zip': '90210',
        'x_country': 'United States'
    },

    'paypal': {
        'amount_1': 1,
        'item_name_1': "Item 1",
        'amount_2': 2,
        'item_name_2': "Item 2",
        'invoice': datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
        'return_url': '{HOST}/invoice'.format(HOST=HOST),
        'cancel_return': '{HOST}/invoice'.format(HOST=HOST),
        'notify_url': '{HOST}/merchant/paypal/ipn'.format(HOST=HOST),
    },

    'google_checkout': {
        'items': [{
                    'amount': 1,
                    'name': 'name of the item',
                    'description': 'Item description',
                    'id': '999AXZ',
                    'currency': 'USD',
                    'quantity': 1,
                    "subscription": {
                    "type": "merchant",                     # valid choices is ["merchant", "google"]
                    "period": "YEARLY",                     # valid choices is ["DAILY", "WEEKLY", "SEMI_MONTHLY", "MONTHLY", "EVERY_TWO_MONTHS"," QUARTERLY", "YEARLY"]
                    "payments": [{
                            "maximum-charge": 9.99,         # Item amount must be "0.00"
                            "currency": "USD"
                    }]
                },
                "digital-content": {
                    "display-disposition": "OPTIMISTIC",    # valid choices is ['OPTIMISTIC', 'PESSIMISTIC']
                    "description": "Congratulations! Your subscription is being set up."
                },
        }],
        'return_url': '{HOST}/invoice'.format(HOST=HOST)
    },

    'amazon_fps': {
        "transactionAmount": "100",
        "pipelineName": "SingleUse",
        "paymentReason": "Merchant Test",
        "paymentPage": "{HOST}/integration/amazon_fps/".format(HOST=HOST),
        "returnURL": '{HOST}/invoice'.format(HOST=HOST)
    },

    'eway_au': {
        'EWAY_CARDNAME': 'John Doe',
        'EWAY_CARDNUMBER': '4444333322221111',
        'EWAY_CARDMONTH': '01',
        'EWAY_CARDYEAR': '2020',
        'EWAY_CARDCVN': '100',
    },

    "braintree_payments": {
        "transaction": {
            "order_id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "type": "sale",
            "options": {
                "submit_for_settlement": True
            },
        },
        "site": "{HOST}:8000".format(HOST=HOST)
    },

    "ogone_payments": {
        'orderID': randomword(6),
        'currency': u'INR',
        'amount': u'10000',  # Rs. 100.00
        'language': 'en_US',
        'exceptionurl': "{HOST}:8000/ogone_notify_handler".format(HOST=HOST),
        'declineurl': "{HOST}:8000/ogone_notify_handler".format(HOST=HOST),
        'cancelurl': "{HOST}:8000/ogone_notify_handler".format(HOST=HOST),
        'accepturl': "{HOST}:8000/ogone_notify_handler".format(HOST=HOST),
    }
}

for k, v in GATEWAY_INITIAL.iteritems():
    v.update(COMMON_INITIAL)

for k, v in INTEGRATION_INITIAL.iteritems():
    v.update(COMMON_INITIAL)

########NEW FILE########
__FILENAME__ = forms

import datetime

from django import forms

from billing import CreditCard

CARD_TYPES = [
    ('', ''),
    ('visa', 'Visa'),
    ('master', 'Master'),
    ('discover', 'Discover'),
    ('american_express', 'American Express'),
    ('diners_club', 'Diners Club'),
    # ('jcb', ''),
    # ('switch', ''),
    # ('solo', ''),
    # ('dankort', ''),
    ('maestro', 'Maestro'),
    # ('forbrugsforeningen', ''),
    # ('laser', 'Laser'),
    ]

today = datetime.date.today()
MONTH_CHOICES = [(m, datetime.date(today.year, m, 1).strftime('%b')) for m in range(1, 13)]
YEAR_CHOICES = [(y, y) for y in range(today.year, today.year + 21)]


class CreditCardForm(forms.Form):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    month = forms.ChoiceField(choices=MONTH_CHOICES)
    year = forms.ChoiceField(choices=YEAR_CHOICES)
    number = forms.CharField(required=False)
    card_type = forms.ChoiceField(choices=CARD_TYPES, required=False)
    verification_value = forms.CharField(label='CVV', required=False)

    def clean(self):
        data = self.cleaned_data
        credit_card = CreditCard(**data)
        if not credit_card.is_valid():
            raise forms.ValidationError('Credit card validation failed')
        return data

########NEW FILE########
__FILENAME__ = authorize_net_dpm_integration
from django import forms

from billing.forms.authorize_net_forms import AuthorizeNetDPMForm as BaseAuthorizeNetDPMForm
from billing.integrations.authorize_net_dpm_integration import AuthorizeNetDpmIntegration as BaseAuthorizeNetDpmIntegration


class AuthorizeNetDPMForm(BaseAuthorizeNetDPMForm):
    x_cust_id = forms.CharField(max_length=20, label="Customer ID", required=False)


class AuthorizeNetDpmIntegration(BaseAuthorizeNetDpmIntegration):

    def form_class(self):
        return AuthorizeNetDPMForm

########NEW FILE########
__FILENAME__ = fps_integration
from billing.integrations.amazon_fps_integration import AmazonFpsIntegration as Integration
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
import urlparse

class FpsIntegration(Integration):
    def transaction(self, request):
        """Ideally at this method, you will check the 
        caller reference against a user id or uniquely
        identifiable attribute (if you are already not 
        using it as the caller reference) and the type 
        of transaction (either pay, reserve etc). For
        the sake of the example, we assume all the users
        get charged $100"""
        request_url = request.build_absolute_uri()
        parsed_url = urlparse.urlparse(request_url)
        query = parsed_url.query
        dd = dict(map(lambda x: x.split("="), query.split("&")))
        resp = self.purchase(100, dd)
        return HttpResponseRedirect("%s?status=%s" %(reverse("app_offsite_amazon_fps"),
                                resp["status"]))

########NEW FILE########
__FILENAME__ = stripe_example_integration
from billing.integrations.stripe_integration import StripeIntegration
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

class StripeExampleIntegration(StripeIntegration):
    def transaction(self, request):
        resp = self.gateway.purchase(100, request.POST["stripeToken"])
        return HttpResponseRedirect("%s?status=%s" %(reverse("app_offsite_stripe"),
                                                     resp["status"]))

########NEW FILE########
__FILENAME__ = models
from django.db import models

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from billing import get_integration
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

google_checkout_obj = get_integration("google_checkout")
authorize_net_obj = get_integration("authorize_net_dpm")
pay_pal_obj = get_integration("pay_pal")
amazon_fps_obj = get_integration("fps")
fps_recur_obj = get_integration("fps")
world_pay_obj = get_integration("world_pay")
braintree_obj = get_integration("braintree_payments")
stripe_obj = get_integration("stripe_example")
ogone_obj = get_integration("ogone_payments")

urlpatterns = patterns('app.views',
    url(r'^$', 'index', name='app_index'),
    url(r'^authorize/$', 'authorize', name='app_authorize'),
    url(r'^paypal/$', 'paypal', name='app_paypal'),
    url(r'^eway/$', 'eway', name='app_eway'),
    url(r'^braintree/$', 'braintree', name='app_braintree'),
    url(r'^stripe/$', 'stripe', name='app_stripe'),
    url(r'^paylane/$', 'paylane', name='app_paylane'),
    url(r'^beanstream/$', 'beanstream', name='app_beanstream'),
    url(r'^chargebee/$', 'chargebee', name='app_chargebee'),
    url(r'^bitcoin/$', 'bitcoin', name='app_bitcoin'),
    url(r'^bitcoin/done/$', 'bitcoin_done', name='app_bitcoin_done'),
)

# offsite payments
urlpatterns += patterns('app.views',
    url(r'offsite/authorize_net/$', 'offsite_authorize_net', name='app_offsite_authorize_net'),
    url(r'offsite/paypal/$', 'offsite_paypal', name='app_offsite_paypal'),
    url(r'offsite/google-checkout/$', 'offsite_google_checkout', name='app_offsite_google_checkout'),
    url(r'offsite/world_pay/$', 'offsite_world_pay', name='app_offsite_world_pay'),
    url(r'offsite/amazon_fps/$', 'offsite_amazon_fps', name='app_offsite_amazon_fps'),
    url(r'offsite/braintree/$', 'offsite_braintree', name='app_offsite_braintree'),
    url(r'offsite/stripe/$', 'offsite_stripe', name='app_offsite_stripe'),
    url(r'offsite/eway/$', 'offsite_eway', name='app_offsite_eway'),

    # redirect handler
    url(r'offsite/eway/done/$', 'offsite_eway_done'),
    url(r'offsite/ogone/$', 'offsite_ogone', name='app_offsite_ogone'),
)

urlpatterns += patterns('',
    (r'^authorize_net-handler/', include(authorize_net_obj.urls)),
)

# paypal payment notification handler
urlpatterns += patterns('',
    (r'^paypal-ipn-handler/', include(pay_pal_obj.urls)),
)
urlpatterns += patterns('',
    (r'^', include(google_checkout_obj.urls)),
)

urlpatterns += patterns('',
    (r'^fps/', include(amazon_fps_obj.urls)),
)

urlpatterns += patterns('',
    (r'^braintree/', include(braintree_obj.urls)),
)

urlpatterns += patterns('',
    (r'^stripe/', include(stripe_obj.urls)),
)

urlpatterns += patterns('',
    url(r'offsite/paypal/done/$',
        csrf_exempt(TemplateView.as_view(template_name="app/payment_done.html")),
        name='app_offsite_paypal_done'),
    url(r'offsite/google-checkout/done/$',
        TemplateView.as_view(template_name="app/payment_done.html"),
        name='app_offsite_google_checkout_done'),
)

urlpatterns += patterns('app.views',
    url(r'^we_pay/$', 'we_pay', name="app_we_pay"),
    url(r'we_pay_redirect/$', 'we_pay_redirect', name="app_we_pay_redirect"),
    url(r'^we_pay_ipn/$', 'we_pay_ipn', name="app_we_pay_ipn"),
)

urlpatterns += patterns('',
    (r'^ogone/', include(ogone_obj.urls)),
)

########NEW FILE########
__FILENAME__ = utils
import random, string


def randomword(word_len):
	rstr = string.lowercase + string.digits
	return ''.join(random.sample(rstr, word_len))

########NEW FILE########
__FILENAME__ = views
import datetime

from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect  # , HttpResponse

from billing import CreditCard, get_gateway, get_integration
from billing.gateway import CardNotSupported

from app.forms import CreditCardForm
from app.urls import (authorize_net_obj, google_checkout_obj, world_pay_obj, pay_pal_obj,
                      amazon_fps_obj, fps_recur_obj, braintree_obj,
                      stripe_obj, ogone_obj)
from app.utils import randomword
from django.conf import settings
from django.contrib.sites.models import RequestSite
from billing.utils.paylane import PaylanePaymentCustomer, \
    PaylanePaymentCustomerAddress

from app.conf import GATEWAY_INITIAL, INTEGRATION_INITIAL

def render(request, template, template_vars={}):
    return render_to_response(template, template_vars, RequestContext(request))

def index(request, gateway=None):
    return authorize(request)

def authorize(request):
    amount = 1
    response = None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("authorize_net")
            try:
                merchant.validate_card(credit_card)
            except CardNotSupported:
                response = "Credit Card Not Supported"
            response = merchant.purchase(amount, credit_card)
            #response = merchant.recurring(amount, credit_card)
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['authorize_net'])
    return render(request, 'app/index.html', {'form': form,
                                              'amount': amount,
                                              'response': response,
                                              'title': 'Authorize'})


def paypal(request):
    amount = 1
    response = None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("pay_pal")
            try:
                merchant.validate_card(credit_card)
            except CardNotSupported:
                response = "Credit Card Not Supported"
            # response = merchant.purchase(amount, credit_card, options={'request': request})
            response = merchant.recurring(amount, credit_card, options={'request': request})
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['paypal'])
    return render(request, 'app/index.html', {'form': form,
                                              'amount': amount,
                                              'response': response,
                                              'title': 'Paypal'})


def eway(request):
    amount = 100
    response = None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("eway")
            try:
                merchant.validate_card(credit_card)
            except CardNotSupported:
                response = "Credit Card Not Supported"
            billing_address = {'salutation': 'Mr.',
                               'address1': 'test',
                               'address2': ' street',
                               'city': 'Sydney',
                               'state': 'NSW',
                               'company': 'Test Company',
                               'zip': '2000',
                               'country': 'au',
                               'email': 'test@example.com',
                               'fax': '0267720000',
                               'phone': '0267720000',
                               'mobile': '0404085992',
                               'customer_ref': 'REF100',
                               'job_desc': 'test',
                               'comments': 'any',
                               'url': 'http://www.google.com.au',
                               }
            response = merchant.purchase(amount, credit_card, options={'request': request, 'billing_address': billing_address})
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['eway'])
    return render(request, 'app/index.html', {'form': form,
                                              'amount': amount,
                                              'response': response,
                                              'title': 'Eway'})

def braintree(request):
    amount = 1
    response = None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("braintree_payments")
            try:
                merchant.validate_card(credit_card)
            except CardNotSupported:
                response = "Credit Card Not Supported"
            response = merchant.purchase(amount, credit_card)
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['braintree_payments'])

    return render(request, 'app/index.html', {'form': form,
                                              'amount': amount,
                                              'response': response,
                                              'title': 'Braintree Payments (S2S)'})
def stripe(request):
    amount = 1
    response= None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("stripe")
            response = merchant.purchase(amount,credit_card)
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['stripe'])
    return render(request, 'app/index.html',{'form': form,
                                             'amount':amount,
                                             'response':response,
                                             'title':'Stripe Payment'})


def paylane(request):
    amount = 1
    response= None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("paylane")
            customer = PaylanePaymentCustomer()
            customer.name = "%s %s" %(data['first_name'], data['last_name'])
            customer.email = "testuser@example.com"
            customer.ip_address = "127.0.0.1"
            options = {}
            address = PaylanePaymentCustomerAddress()
            address.street_house = 'Av. 24 de Julho, 1117'
            address.city = 'Lisbon'
            address.zip_code = '1700-000'
            address.country_code = 'PT'
            customer.address = address
            options['customer'] = customer
            options['product'] = {}
            response = merchant.purchase(amount, credit_card, options = options)
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['paylane'])
    return render(request, 'app/index.html', {'form': form,
                                              'amount':amount,
                                              'response':response,
                                              'title':'Paylane Gateway'})


def we_pay(request):
    wp = get_gateway("we_pay")
    form = None
    amount = 10
    response = wp.purchase(10, None, {
            "description": "Test Merchant Description",
            "type": "SERVICE",
            "redirect_uri": request.build_absolute_uri(reverse('app_we_pay_redirect'))
            })
    if response["status"] == "SUCCESS":
        return HttpResponseRedirect(response["response"]["checkout_uri"])
    return render(request, 'app/index.html', {'form': form,
                                              'amount':amount,
                                              'response':response,
                                              'title':'WePay Payment'})

def we_pay_redirect(request):
    checkout_id = request.GET.get("checkout_id", None)
    return render(request, 'app/we_pay_success.html', {"checkout_id": checkout_id})


def we_pay_ipn(request):
    # Just a dummy view for now.
    return render(request, 'app/index.html', {})


def beanstream(request):
    amount = 1
    response = None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("beanstream")
            response = merchant.purchase(amount, credit_card,
                                         {"billing_address": {
                        "name": "%s %s" % (data["first_name"], data["last_name"]),
                        # below are hardcoded just for the sake of the example
                        # you can make these optional by toggling the customer name
                        # and address in the account dashboard.
                        "email": "test@example.com",
                        "phone": "555-555-555-555",
                        "address1": "Addr1",
                        "address2": "Addr2",
                        "city": "Hyd",
                        "state": "AP",
                        "country": "IN"
                        }
                                          })
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['beanstream'])
    return render(request, 'app/index.html',{'form': form,
                                             'amount': amount,
                                             'response': response,
                                             'title': 'Beanstream'})

def chargebee(request):
    amount = 1
    response = None
    if request.method == 'POST':
        form = CreditCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            credit_card = CreditCard(**data)
            merchant = get_gateway("chargebee")
            response = merchant.purchase(amount, credit_card,
                                         {"plan_id": "professional",
                                          "description": "Quick Purchase"})
    else:
        form = CreditCardForm(initial=GATEWAY_INITIAL['chargebee'])
    return render(request, 'app/index.html',{'form': form,
                                             'amount': amount,
                                             'response': response,
                                             'title': 'Chargebee'})

def offsite_authorize_net(request):
    params = {
        'x_amount': 1,
        'x_fp_sequence': datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
        'x_fp_timestamp': datetime.datetime.now().strftime('%s'),
        'x_recurring_bill': 'F',
        'x_card_num': '4007000000027',
        'x_exp_date': '01/20',
        'x_card_code': '100',
        'x_first_name': 'John',
        'x_last_name': 'Doe',
        'x_address': '100, Spooner Street, Springfield',
        'x_city': 'San Francisco',
        'x_state': 'California',
        'x_zip': '90210',
        'x_country': 'United States'
    }
    authorize_net_obj.add_fields(params)
    template_vars = {"obj": authorize_net_obj, 'title': authorize_net_obj.display_name}
    return render(request, 'app/offsite_authorize_net.html', template_vars)


def offsite_paypal(request):
    invoice_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return_url = request.build_absolute_uri(reverse('app_offsite_paypal_done'))
    cancel_return = request.build_absolute_uri(request.META['PATH_INFO'])
    notify_url = request.build_absolute_uri(reverse('paypal-ipn'))

    paypal_params = {
        'amount_1': 1,
        'item_name_1': "Item 1",
        'amount_2': 2,
        'item_name_2': "Item 2",
        'invoice': invoice_id,
        'notify_url': notify_url,
        'return_url': return_url,
        'cancel_return': cancel_return,
    }
    pay_pal_obj.add_fields(paypal_params)
    template_vars = {"obj": pay_pal_obj, 'title': 'PayPal Offsite'}
    return render(request, 'app/offsite_paypal.html', template_vars)

def offsite_google_checkout(request):
    return_url = request.build_absolute_uri(reverse('app_offsite_google_checkout_done'))
    fields = {
            'items': [{
                'amount': 1,
                'name': 'name of the item',
                'description': 'Item description',
                'id': '999AXZ',
                'currency': 'USD',
                'quantity': 1,
                "subscription": {
                "type": "merchant",                     # valid choices is ["merchant", "google"]
                "period": "YEARLY",                     # valid choices is ["DAILY", "WEEKLY", "SEMI_MONTHLY", "MONTHLY", "EVERY_TWO_MONTHS"," QUARTERLY", "YEARLY"]
                "payments": [{
                        "maximum-charge": 9.99,         # Item amount must be "0.00"
                        "currency": "USD"
                }]
            },
            "digital-content": {
                "display-disposition": "OPTIMISTIC",    # valid choices is ['OPTIMISTIC', 'PESSIMISTIC']
                "description": "Congratulations! Your subscription is being set up. Continue: {return_url}".format(return_url=return_url)
            },
        }],
        'return_url': return_url
    }
    google_checkout_obj.add_fields(fields)
    template_vars = {'title': 'Google Checkout', "gc_obj": google_checkout_obj}

    return render(request, 'app/google_checkout.html', template_vars)

def offsite_world_pay(request):
    fields = {"instId": settings.MERCHANT_SETTINGS["world_pay"]["INSTALLATION_ID_TEST"],
              "cartId": "TEST123",
              "currency": "USD",
              "amount": 1,
              "desc": "Test Item",}
    world_pay_obj.add_fields(fields)
    template_vars = {'title': 'WorldPay', "wp_obj": world_pay_obj}
    return render(request, 'app/world_pay.html', template_vars)

def offsite_amazon_fps(request):
    url_scheme = "http"
    if request.is_secure():
        url_scheme = "https"
    fields = {"transactionAmount": "100",
              "pipelineName": "SingleUse",
              "paymentReason": "Merchant Test",
              "paymentPage": request.build_absolute_uri(),
              "returnURL": "%s://%s%s" % (url_scheme,
                                          RequestSite(request).domain,
                                          reverse("fps_return_url"))
              }
    # Save the fps.fields["callerReference"] in the db along with
    # the amount to be charged or use the user's unique id as
    # the callerReference so that the amount to be charged is known
    # Or save the callerReference in the session and send the user
    # to FPS and then use the session value when the user is back.
    amazon_fps_obj.add_fields(fields)
    fields.update({"transactionAmount": "100",
                   "pipelineName": "Recurring",
                   "recurringPeriod": "1 Hour",
                   })
    fps_recur_obj.add_fields(fields)
    template_vars = {'title': 'Amazon Flexible Payment Service',
                     "fps_recur_obj": fps_recur_obj,
                     "fps_obj": amazon_fps_obj}
    return render(request, 'app/amazon_fps.html', template_vars)

def offsite_braintree(request):
    fields = {"transaction": {
            "order_id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "type": "sale",
            "options": {
                "submit_for_settlement": True
                },
            },
            "site": "%s://%s" % ("https" if request.is_secure() else "http",
                                RequestSite(request).domain)
            }
    braintree_obj.add_fields(fields)
    template_vars = {'title': 'Braintree Payments Transparent Redirect',
                     "bp_obj": braintree_obj}
    return render(request, "app/braintree_tr.html", template_vars)

def offsite_stripe(request):
    status = request.GET.get("status")
    stripe_obj.add_field("amount", 100)
    template_vars = {'title': 'Stripe.js',
                     "stripe_obj": stripe_obj,
                     "status": status}
    return render(request, "app/stripe.html", template_vars)


def offsite_eway(request):
    return_url = request.build_absolute_uri(reverse(offsite_eway_done))
    eway_obj = get_integration("eway_au")
    customer = eway_obj.request_access_code(
            return_url=return_url, customer={},
            payment={"total_amount": 100})
    request.session["eway_access_code"] = eway_obj.access_code
    template_vars = {"title": "eWAY",
                     "eway_obj": eway_obj}
    return render(request, "app/eway.html", template_vars)


def offsite_eway_done(request):
    access_code = request.session["eway_access_code"]
    eway_obj = get_integration("eway_au", access_code=access_code)
    result = eway_obj.check_transaction()

    return render(request, "app/eway_done.html", {"result": result})


def bitcoin(request):
    amount = 0.01
    bitcoin_obj = get_gateway("bitcoin")
    address = request.session.get("bitcoin_address", None)
    if not address:
        address = bitcoin_obj.get_new_address()
        request.session["bitcoin_address"] = address
    return render(request, "app/bitcoin.html", {
        "title": "Bitcoin",
        "amount": amount,
        "address": address,
        "settings": settings
    })

def bitcoin_done(request):
    amount = 0.01
    bitcoin_obj = get_gateway("bitcoin")
    address = request.session.get("bitcoin_address", None)
    if not address:
        return HttpResponseRedirect(reverse("app_bitcoin"))
    result = bitcoin_obj.purchase(amount, address)
    if result['status'] == 'SUCCESS':
        del request.session["bitcoin_address"]
    return render(request, "app/bitcoin_done.html", {
        "title": "Bitcoin",
        "amount": amount,
        "address": address,
        "result": result
    })


def offsite_ogone(request):
    fields = {
        # Required
        # orderID needs to be unique per transaction.
        'orderID': randomword(6),
        'currency': u'INR',
        'amount': u'10000',  # 100.00
        'language': 'en_US',

        # Optional; Can be configured in Ogone Account:

        'exceptionurl': request.build_absolute_uri(reverse("ogone_notify_handler")),
        'declineurl': request.build_absolute_uri(reverse("ogone_notify_handler")),
        'cancelurl': request.build_absolute_uri(reverse("ogone_notify_handler")),
        'accepturl': request.build_absolute_uri(reverse("ogone_notify_handler")),

        # Optional fields which can be used for billing:

        # 'homeurl': u'http://127.0.0.1:8000/',
        # 'catalogurl': u'http://127.0.0.1:8000/',
        # 'ownerstate': u'',
        # 'cn': u'Venkata Ramana',
        # 'ownertown': u'Hyderabad',
        # 'ownercty': u'IN',
        # 'ownerzip': u'Postcode',
        # 'owneraddress': u'Near Madapur PS',
        # 'com': u'Order #21: Venkata Ramana',
        # 'email': u'ramana@agiliq.com'
    }
    ogone_obj.add_fields(fields)
    return render(request, "app/ogone.html", {"og_obj": ogone_obj})

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os

import settings


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.local")
    from django.core.management import execute_manager
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = common
# Django settings for example project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'wobwwik!&)qmyt2kf3(^jjc6gff)jbtuir+&2)ux7e#xozf5@m'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "templates",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'app',
    'billing',
    'stripe',
    'paypal.pro',
    'crispy_forms',
    'raven.contrib.django.raven_compat'
)

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(os.path.dirname(__file__), "static")
STATICFILES_FINDER = ("django.contrib.staticfiles.finders.FileSystemFinder",
                      "django.contrib.staticfiles.finders.AppDirectoriesFinder")
USE_TZ = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

ALLOWED_HOSTS = ['agiliq.com']

########NEW FILE########
__FILENAME__ = travis
import os
from common import *

from formencode.variabledecode import variable_decode

DEBUG = False


def get_merchant_settings():
    env_dict = dict(filter(lambda x: x[0].startswith('MERCHANT'), os.environ.items()))
    return variable_decode(env_dict, dict_char='__')['MERCHANT']

# MERCHANT SETTINGS
MERCHANT_TEST_MODE = True
MERCHANT_SETTINGS = get_merchant_settings()

# PAYPAL SETTINGS
if MERCHANT_SETTINGS.get("pay_pal"):
    PAYPAL_TEST = MERCHANT_TEST_MODE
    PAYPAL_WPP_USER = MERCHANT_SETTINGS["pay_pal"]["WPP_USER"]
    PAYPAL_WPP_PASSWORD = MERCHANT_SETTINGS["pay_pal"]["WPP_PASSWORD"]
    PAYPAL_WPP_SIGNATURE = MERCHANT_SETTINGS["pay_pal"]["WPP_SIGNATURE"]
    PAYPAL_RECEIVER_EMAIL = MERCHANT_SETTINGS["pay_pal"]["RECEIVER_EMAIL"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'merchant.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}
ADMIN_MEDIA_PREFIX = "/static/admin/"

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^example/', include('example.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    url(r'^', include('app.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for demo_project project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "demo_project.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.local")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = fabfile
from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm

env.hosts = ["merchant.agiliq.com"]
env.user = "agiliq"

def describe():
    print "This is a fab file to automate deployments for the merchant server."

def deploy():
    with cd("/home/agiliq/envs/merchant/src/merchant"):
        run("git pull")

    with prefix("workon merchant"):
        with cd("/home/agiliq/envs/merchant/src/merchant/example"):
            run("pip install -r requirements.txt")
            run("python manage.py validate")
            run("python manage.py syncdb")

    run('/home/agiliq/scripts/merchant_restart.sh')

########NEW FILE########
