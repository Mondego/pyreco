__FILENAME__ = authorize_net
"""authorize_net.py - Authorize.Net example"""

try:
    from paython import api, gateways, CreditCard
except ImportError:
    # adding paython to the path
    # to run this without installing the library
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

    # trying again
    from paython import api, gateways, CreditCard

api = gateways.AuthorizeNet(username='test',
                            password='test',
                            test=True)

mycard = {
    'first_name': 'auston',
    'last_name': 'bunsen',
    'number': '4111111111111111',
    'exp_mo': '12',
    'exp_yr': '2012'
}

cc_obj = CreditCard(**mycard)

billing = {
    'address': '7519 NW 88th Terrace',
    'city': 'Tamarac',
    'state': 'FL',
    'zipcode': '33321',
    'phone': '9546703289',
    'email': 'auston@gmail.com'
}

api.auth('0.22', cc_obj, billing)
api.void('2155779779')

########NEW FILE########
__FILENAME__ = firstdata
"""firstdata.py - Firstdata legacy example"""

try:
    from paython import api, gateways, CreditCard
except ImportError:
    # adding paython to the path
    # to run this without installing the library
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

    # trying again
    from paython import api, gateways, CreditCard

pem = '/Path/to/your/yourkey.pem'

api = gateways.FirstDataLegacy(username='1329411',
                               key_file=pem,
                               cert_file=pem,
                               debug=True,
                               test=True)

mycard = {
    'full_name': 'auston bunsen',
    'number': '5555555555554444',
    'cvv': '904',
    'exp_mo': '12',
    'exp_yr': '2012'
}

cc_obj = CreditCard(**mycard)

billing = {
    'address': '7519 NW 88th Terrace',
    'city': 'Tamarac',
    'state': 'FL',
    'zipcode': '33321',
    'country': 'US',
    'phone': '9547212241',
    'email': 'auston@gmail.com'
}

api.auth('0.01', cc_obj, billing)

########NEW FILE########
__FILENAME__ = innovative_gw
"""innovative_gw.py - Innovative GW example"""

try:
    from paython import api, gateways, CreditCard
except ImportError:
    # adding paython to the path
    # to run this without installing the library
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

    # trying again
    from paython import api, gateways, CreditCard

api = gateways.InnovativeGW(username='test',
                            password='test',
                            debug=True)

mycard = {
    'full_name': 'auston bunsen',
    'number': '4111111111111111',
    'cvv': '771',
    'exp_mo': '12',
    'exp_yr': '2012'
}

cc_obj = CreditCard(**mycard)

billing = {
    'address': '7519 NW 88th Terrace',
    'city': 'Tamarac',
    'state': 'FL',
    'zipcode': '33321',
    'country': 'US',
    'phone': '9546703289',
    'email': 'auston@gmail.com'
}

api.auth('1.22', cc_obj, billing)

########NEW FILE########
__FILENAME__ = plugnpay
"""plugnpay.py - PlugnPay.com example"""

try:
    from paython import gateways, CreditCard
except ImportError:
    # adding paython to the path
    # to run this without installing the library
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

    # trying again
    from paython import gateways, CreditCard

# enter your `email` to receive gateway notifications
api = gateways.PlugnPay(username='pnpdemo', password='', email='')

mycard = {
    'first_name': 'auston',
    'last_name': 'bunsen',
    'number': '41111111111111',
    'exp_mo': '12',
    'exp_yr': '2012'
}

cc_obj = CreditCard(**mycard)

billing = {
    'address': '7519 NW 88th Terrace',
    'city': 'Tamarac',
    'state': 'FL',
    'zipcode': '33321',
    'country' : 'US',
    'phone': '3053333333',
    'email': 'manuel@140.am'
}

print '-----------------------------'

trans = api.capture('1.0', cc_obj, billing)
print trans

########NEW FILE########
__FILENAME__ = samurai_ex
from paython import api, gateways, CreditCard

api = gateways.Samurai(
	merchant_key='202fc9c52312295d8ab93048', 
	password='f5b06686bc8d0625560f7a6d', 
	processor='df52fa67def1a3e85a0affce'
)

mycard = {
    'first_name': 'John',
    'last_name': 'Doe',
    'number': '4111111111111111',
    'exp_mo': '12',
    'exp_yr': '2012',
    'cvv':'111',
    'strict': True
}

cc_obj = CreditCard(**mycard)

billing = {
    'address': '1000 1st Av',
    'city': 'Chicago',
    'state': 'IL',
    'zipcode': '10101',
    'phone': '9546703289',
    'email': 'auston@gmail.com'
}

authorization = api.auth('1.00', cc_obj, billing)
print authorization
print api.void(authorization['alt_trans_id'])
########NEW FILE########
__FILENAME__ = stripe_ex
from paython import api, gateways, CreditCard

api = gateways.Stripe(username="vtUQeOtUnYr7PGCLQ96Ul4zqpDUO4sOE")#, debug=True)

mycard = {
    'first_name': 'auston',
    'last_name': 'bunsen',
    'number': '4242424242424242',
    'exp_mo': '12',
    'exp_yr': '2012'
}

cc_obj = CreditCard(**mycard)

billing = {
    'address': '7519 NW 88th Terrace',
    'city': 'Tamarac',
    'state': 'FL',
    'zipcode': '33321',
    'phone': '9546703289',
    'email': 'auston@gmail.com'
}

api.capture('0.22', cc_obj, billing)
ex = api.capture('10.22', cc_obj, billing)
api.credit('5.55', ex['trans_id'])
api.void('2155779779')
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.localflavor.us.forms import USStateField, USZipCodeField, USStateSelect

from paython.lib.utils import is_valid_cc, is_valid_cvv, is_valid_exp

class CustomerInformation(forms.Form):
    """
    Store the customer information, typically first name and last name.
    """
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)

class CreditCardForm(forms.Form):
    """
    Form for validating credit card numbers.
    """
    number = forms.CharField(max_length=19)
    exp_month = forms.CharField(max_length=2)
    exp_year = forms.CharField(max_length=4)
    security_code = forms.CharField(max_length=4)

    def clean(self):
        """Validates the form"""
        super(CreditCardForm, self).clean()

        cleaned_data = self.cleaned_data

        number = cleaned_data.get('number')
        security_code = cleaned_data.get('security_code')
        exp_month = cleaned_data.get('exp_month')
        exp_year = cleaned_data.get('exp_year')

        if not self.is_valid():
            raise forms.ValidationError("There was a problem processing your payment")

        if not is_valid_cc(number):
            raise forms.ValidationError("Invalid credit card number")

        if not is_valid_cvv(security_code):
            raise forms.ValidationError("Invalid security code")

        if not is_valid_exp(exp_month, exp_year):
            raise forms.ValidationError("Invalid expiracy date")

        return cleaned_data

class ZipCodeForm(forms.Form):
    """
    Sometimes we just need the zipcode
    """
    zipcode = USZipCodeField()

class CityStateZipCode(forms.Form):
    """
    And sometimes we need the City and State with the zipcode
    """
    city = forms.CharField(max_length=255)
    state = USStateField(widget=USStateSelect)
    zipcode = USZipCodeField()

class AddressForm(forms.Form):
    """
    Address form for new signup
    """
    address1 = forms.CharField(max_length=255)
    address2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=255)
    state = USStateField(widget=USStateSelect)
    zipcode = USZipCodeField()

########NEW FILE########
__FILENAME__ = exceptions
class DataValidationError(Exception):
    """ Errors when data is corrupt, malformed or just plain wrong """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class MissingDataError(Exception):
    """ Errors when data is missing in developer API call """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class GatewayError(Exception):
    """ Errors returned from API Gateway """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class RequestError(Exception):
    """ Errors during the API Request """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class MissingTranslationError(Exception):
    """ Errors with trying to find a translation"""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

########NEW FILE########
__FILENAME__ = authorize_net
import time
import logging

from paython.exceptions import MissingDataError
from paython.lib.api import GetGateway

logger = logging.getLogger(__name__)

class AuthorizeNet(GetGateway):
    """TODO needs docstring"""
    VERSION = '3.1'
    DELIMITER = ';'
    LIVE_TEST = 'live_test'

    # This is how we determine whether or not we allow 'test' as an init param
    API_URI = {
        'live' : 'https://secure.authorize.net/gateway/transact.dll',
        'test' : 'https://test.authorize.net/gateway/transact.dll'
    }

    # This is how we translate the common Paython fields to Gateway specific fields
    REQUEST_FIELDS = {
        #contact
        'full_name' : None,
        'first_name': 'x_first_name',
        'last_name': 'x_last_name',
        'email': 'x_email',
        'phone': 'x_phone',
        #billing
        'address': 'x_address',
        'address2': None,
        'city': 'x_city',
        'state': 'x_state',
        'zipcode': 'x_zip',
        'country': 'x_country',
        'ip': 'x_customer_ip',
        'invoice_num': 'x_invoice_num',
        #card
        'number': 'x_card_num',
        'exp_date': 'x_exp_date',
        'exp_month': None,
        'exp_year': None,
        'verification_value': 'x_card_code',
        'card_type': None,
        #shipping
        'ship_full_name': None,
        'ship_first_name': 'x_ship_to_first_name',
        'ship_last_name': 'x_ship_to_last_name',
        'ship_to_co': 'x_ship_to_company',
        'ship_address': 'x_ship_to_address',
        'ship_address2': None,
        'ship_city': 'x_ship_to_city',
        'ship_state': 'x_ship_to_state',
        'ship_zipcode': 'x_ship_to_zip',
        'ship_country': 'x_ship_to_country',
        #transaction
        'amount': 'x_amount',
        'trans_type': 'x_type',
        'trans_id': 'x_trans_id',
        'alt_trans_id': None,
        'split_tender_id':'x_split_tender_id',
        'is_partial':'x_allow_partial_auth',
    }

    # Response Code: 1 = Approved, 2 = Declined, 3 = Error, 4 = Held for Review
    # AVS Responses: A = Address (Street) matches, ZIP does not,  P = AVS not applicable for this transaction,
    # AVS Responses (cont'd): W = Nine digit ZIP matches, Address (Street) does not, X = Address (Street) and nine digit ZIP match,
    # AVS Responses (cont'd): Y = Address (Street) and five digit ZIP match, Z = Five digit ZIP matches, Address (Street) does not
    # response index keys to map the value to its proper dictionary key
    RESPONSE_KEYS = {
        '0':'response_code',
        '1':'response_sub_code',
        '2':'response_reason_code',
        '3':'response_text',
        '4':'auth_code',
        '5':'avs_response',
        '6':'trans_id',
        '7':'invoice_number',
        '8': 'description',
        '9':'amount',
        '10':'method',
        '11':'trans_type',
        '12':'alt_trans_id',
        '13':'first_name',
        '14':'last_name',
        '15':'company',
        '16':'address',
        '17':'city',
        '18':'state',
        '19':'zip_code',
        '20':'country',
        '21':'phone',
        '22':'fax',
        '23':'email_address',
        '24':'ship_to_first_name',
        '25':'ship_to_last_name',
        '26':'ship_to_company',
        '27':'ship_to_address',
        '28':'ship_to_city',
        '29':'ship_to_state',
        '30':'ship_to_zip_code',
        '31':'ship_to_country',
        '32':'tax',
        '33':'duty',
        '34':'freight',
        '35':'tax_exempt',
        '36':'purchase_order_number',
        '37':'MD5_hash',
        '38':'cvv_response',
        '39':'cavv_response',
        '40':'account_number',
        '41':'card_type',
        '42':'split_tender_id',
        '43':'amount',
        '44':'balance_on_card',
        '53':'split_tender_id',
        '54':'requested_amount',
        '55':'balance_on_card',
        #'n/a':'alt_trans_id2', <-- third way of id'ing a transaction
    }

    debug = False
    test = False

    def __init__(self, username='test', password='testpassword', debug=False, test=False, delim=None):
        """
        setting up object so we can run 4 different ways (live, debug, test & debug+test)
        There are two different test modes:
        - test=True: regular test mode where the authentication and verification
          is done on the authorize.net staging server.
          For this you need to use the credentials of your test account.
        - test="live_test": the transaction is processed on the live authorize.net
          server but is not submitted to financial institutions for authorization.
          For this you need to use the credentials of the live authorize.net
          account.

        For further details please see:
        http://developer.authorize.net/guides/AIM/wwhelp/wwhimpl/common/html/wwhelp.htm#context=AIM&file=5_TestTrans.html
        """
        super(AuthorizeNet, self).set('x_login', username)
        super(AuthorizeNet, self).set('x_tran_key', password)

        # passing fields to bubble up to Base Class
        super(AuthorizeNet, self).__init__(translations=self.REQUEST_FIELDS, debug=debug)

        if debug:
            self.debug = True

        if test:
            if test != self.LIVE_TEST:
                self.test = True
                test_string = 'regular'
            else:
                test_string = 'live'
                super(AuthorizeNet, self).set('x_test_request', 'TRUE')
            debug_string = " paython.gateways.authorize_net.__init__() -- You're in %s test mode (& debug, obviously) " % test_string
            logger.debug(debug_string.center(80, '='))
        else:
            self.test = False

        if delim:
            self.DELIMITER = delim

    def charge_setup(self):
        """
        standard setup, used for charges
        """
        super(AuthorizeNet, self).set('x_delim_data', 'TRUE')
        super(AuthorizeNet, self).set('x_delim_char', self.DELIMITER)
        super(AuthorizeNet, self).set('x_version', self.VERSION)
        debug_string = " paython.gateways.authorize_net.charge_setup() Just set up for a charge "
        logger.debug(debug_string.center(80, '='))

    def auth(self, amount, credit_card=None, billing_info=None, shipping_info=None, is_partial=False, split_id=None, invoice_num=None):
        """
        Sends charge for authorization based on amount
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_type'], 'AUTH_ONLY')
        if invoice_num is not None:
            super(AuthorizeNet, self).set(self.REQUEST_FIELDS['invoice_num'], invoice_num)

        # support for partial auths
        if is_partial:
            super(AuthorizeNet, self).set(self.REQUEST_FIELDS['is_partial'], 'true')
            super(AuthorizeNet, self).set(self.REQUEST_FIELDS['split_tender_id'], split_id)

        # validating or building up request
        if not credit_card:
            debug_string = "paython.gateways.authorize_net.auth()  -- No CreditCard object present. You passed in %s " % (credit_card)
            logger.debug(debug_string)

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            super(AuthorizeNet, self).use_credit_card(credit_card)

        if billing_info:
            super(AuthorizeNet, self).set_billing_info(**billing_info)

        if shipping_info:
            super(AuthorizeNet, self).set_shipping_info(**shipping_info)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def settle(self, amount, trans_id, split_id=None):
        """
        Sends prior authorization to be settled based on amount & trans_id PRIOR_AUTH_CAPTURE
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_type'], 'PRIOR_AUTH_CAPTURE')
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)

        if split_id: # settles the entire split
            super(AuthorizeNet, self).set(self.REQUEST_FIELDS['split_tender_id'], split_id)
            super(AuthorizeNet, self).unset(self.REQUEST_FIELDS['trans_id'])

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def capture(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends transaction for capture (same day settlement) based on amount.
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_type'], 'AUTH_CAPTURE')

        # validating or building up request
        if not credit_card:
            debug_string = "paython.gateways.authorize_net.capture()  -- No CreditCard object present. You passed in %s " % (credit_card)
            logger.debug(debug_string)

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            super(AuthorizeNet, self).use_credit_card(credit_card)

        if billing_info:
            super(AuthorizeNet, self).set_billing_info(**billing_info)

        if shipping_info:
            super(AuthorizeNet, self).set_shipping_info(**shipping_info)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def void(self, trans_id, split_id=None):
        """
        Sends a transaction to be voided (in full)
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_type'], 'VOID')
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)

        if split_id: # voids an entire split (alternatively, a trans_id just kills that particular txn)
            super(AuthorizeNet, self).set(self.REQUEST_FIELDS['split_tender_id'], split_id)
            super(AuthorizeNet, self).unset(self.REQUEST_FIELDS['trans_id'])

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def credit(self, amount, trans_id, credit_card, split_id=None):
        """
        Sends a transaction to be refunded (partially or fully)
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_type'], 'CREDIT')
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(AuthorizeNet, self).set(self.REQUEST_FIELDS['number'], credit_card.number)

        if amount: #check to see if we should send an amount
            super(AuthorizeNet, self).set(self.REQUEST_FIELDS['amount'], amount)

        if split_id: # voids an entire split (alternatively, a trans_id just kills that particular txn)
            super(AuthorizeNet, self).set(self.REQUEST_FIELDS['split_tender_id'], split_id)
            super(AuthorizeNet, self).unset(self.REQUEST_FIELDS['trans_id'])

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def request(self):
        """
        Makes a request using lib.api.GetGateway.make_request() & move some debugging away from other methods.
        """
        # decide which url to use (test|live)
        if self.test == self.LIVE_TEST or not self.test:
            url = self.API_URI['live']
        else:
            url = self.API_URI['test'] # here just in case we want to granularly change endpoint

        debug_string = " paython.gateways.authorize_net.request() -- Attempting request to: "
        logger.debug(debug_string.center(80, '='))
        debug_string = "%s with params: %s" % (url, super(AuthorizeNet, self).query_string())
        logger.debug(debug_string)
        logger.debug('as dict: %s' % self.REQUEST_DICT)

        # make the request
        start = time.time() # timing it
        response = super(AuthorizeNet, self).make_request(url)
        end = time.time() # done timing it
        response_time = '%0.2f' % (end - start)

        debug_string = " paython.gateways.authorize_net.request()  -- Request completed in %ss " % response_time
        logger.debug(debug_string.center(80, '='))

        return response, response_time

    def parse(self, response, response_time):
        """
        On Specific Gateway due differences in response from gateway
        """
        debug_string = " paython.gateways.authorize_net.parse() -- Raw response: "
        logger.debug(debug_string.center(80, '='))
        logger.debug("\n %s" % response)

        #splitting up response into a list so we can map it to Paython generic response
        response = response.split(self.DELIMITER)
        approved = True if response[0] == '1' else False

        debug_string = " paython.gateways.authorize_net.parse() -- Response as list: "
        logger.debug(debug_string.center(80, '='))
        logger.debug('\n%s' % response)

        return super(AuthorizeNet, self).standardize(response, self.RESPONSE_KEYS, response_time, approved)

########NEW FILE########
__FILENAME__ = core
"""core.py - Paython's core libraries"""

import logging

from paython.exceptions import DataValidationError, MissingTranslationError
from paython.lib.utils import is_valid_email

logger = logging.getLogger(__name__)

class Gateway(object):
    """base gateway class"""
    REQUEST_FIELDS = {}
    RESPONSE_FIELDS = {}
    debug = False

    def __init__(self, set_method, translations, debug):
        """core gateway class"""
        self.set = set_method
        self.REQUEST_FIELDS = translations
        self.debug = debug

    def use_credit_card(self, credit_card):
        """
        Set up credit card info use (if necessary for transaction)
        """
        if hasattr(credit_card, '_exp_yr_style'): # here for gateways that like 2 digit expiration years
            credit_card.exp_year = credit_card.exp_year[-2:]

        for key, value in credit_card.__dict__.items():
            if not key.startswith('_'):
                try:
                    self.set(self.REQUEST_FIELDS[key], value)
                except KeyError:
                    pass # it is okay to fail (on exp_month & exp_year)

    def set_billing_info(self, address=None, address2=None, city=None, state=None, zipcode=None, country=None, phone=None, email=None, ip=None, first_name=None, last_name=None):
        """
        Set billing info, as necessary, no required keys. Validates email as well formed.
        """
        if address:
            self.set(self.REQUEST_FIELDS['address'], address)

        if address2:
            self.set(self.REQUEST_FIELDS['address2'], address2)

        if city:
            self.set(self.REQUEST_FIELDS['city'], city)

        if state:
            self.set(self.REQUEST_FIELDS['state'], state)

        if zipcode:
            self.set(self.REQUEST_FIELDS['zipcode'], zipcode)

        if country:
            self.set(self.REQUEST_FIELDS['country'], country)

        if phone:
            self.set(self.REQUEST_FIELDS['phone'], phone)

        if ip:
            self.set(self.REQUEST_FIELDS['ip'], ip)

        if first_name:
            self.set(self.REQUEST_FIELDS['first_name'], first_name)

        if last_name:
            self.set(self.REQUEST_FIELDS['last_name'], last_name)

        if email:
            if is_valid_email(email):
                self.set(self.REQUEST_FIELDS['email'], email)
            else:
                raise DataValidationError('The email submitted does not pass regex validation')

    def set_shipping_info(self, ship_first_name, ship_last_name, ship_address, ship_city, ship_state, ship_zipcode, ship_country=None, ship_to_co=None, ship_phone=None, ship_email=None):
        """
        Adds shipping info, is standard on all gateways. Does not always use same all provided fields.
        """
        # setting all shipping variables
        self.set(self.REQUEST_FIELDS['ship_first_name'], ship_first_name)
        self.set(self.REQUEST_FIELDS['ship_last_name'], ship_last_name)
        self.set(self.REQUEST_FIELDS['ship_address'], ship_address)
        self.set(self.REQUEST_FIELDS['ship_city'], ship_city)
        self.set(self.REQUEST_FIELDS['ship_state'], ship_state)
        self.set(self.REQUEST_FIELDS['ship_zipcode'], ship_zipcode)

        # now optional ones
        optionals = ['ship_to_co', 'ship_phone', 'ship_email', 'ship_country'] # using list of strings for reasons spec'd below

        #in line comments on this one
        for optional_var in optionals:
            exec '%s = %s' % (optional_var, optional_var) # re-assign each option param to itself
            if eval(optional_var): # see if it was passed into the method
                if optional_var not in self.REQUEST_FIELDS: # make sure we have a translation in the request fields dictionary
                    # & keep the string so we have a meaningful exception
                    raise MissingTranslationError('Gateway doesn\'t support the \"%s\" field for shipping' % optional_var)

                # set it on the gateway level if we are able to get this far
                self.set(self.REQUEST_FIELDS['ship_to_co'], ship_to_co)

    def standardize(self, spec_response, field_mapping, response_time, approved):
        """
        Translates gateway specific response into Paython generic response.
        Expects list or dictionary for spec_repsonse & dictionary for field_mapping.
        """
        # manual settings
        self.RESPONSE_FIELDS['response_time'] = response_time
        self.RESPONSE_FIELDS['approved'] = approved

        if isinstance(spec_response, list): # list settings
            i = 0
            debug_string = 'paython.gateways.core.standardize() -- spec_response: '
            logger.debug(debug_string.center(80, '='))
            logger.debug('\n%s' % spec_response)
            debug_string = 'paython.gateways.core.standardize() -- field_mapping: '
            logger.debug(debug_string.center(80, '='))
            logger.debug('\n%s' % field_mapping)

            for item in spec_response:
                iteration_key = str(i) #stringifying because the field_mapping keys are strings
                if iteration_key in field_mapping:
                    self.RESPONSE_FIELDS[field_mapping[iteration_key]] = item
                i += 1
        else: # dict settings
            for key, value in spec_response.items():
                try:
                    self.RESPONSE_FIELDS[field_mapping[key]] = value
                except KeyError:
                    pass #its okay to fail if we dont have a translation

        #send it back!
        return self.RESPONSE_FIELDS

########NEW FILE########
__FILENAME__ = firstdata_legacy
import re
import time
import urlparse
import logging

from paython.exceptions import DataValidationError, MissingDataError
from paython.lib.api import XMLGateway

logger = logging.getLogger(__name__)

class FirstDataLegacy(XMLGateway):
    """First data legacy support"""

    # This is how we determine whether or not we allow 'test' as an init param
    API_URI = {
        'live' : 'https://secure.linkpt.net/LSGSXML'
    }

    # This is how we translate the common Paython fields to Gateway specific fields
    # it goes like this: 'paython_key' ==> 'gateway_specific_parameter'
    REQUEST_FIELDS = {
        #contact
        'full_name': 'order/billing/name',
        'first_name': None,
        'last_name': None,
        'email': 'order/billing/email',
        'phone': 'order/billing/phone',
        #billing
        'address': 'order/billing/address1',
        'address2': 'order/billing/address2',
        'city': 'order/billing/city',
        'state': 'order/billing/state', 
        'zipcode': 'order/billing/zip',
        'country': 'order/billing/country',
        'ip': 'order/transactiondetails/ip',
        #card
        'number': 'order/creditcard/cardnumber',
        'exp_date': None,
        'exp_month': 'order/creditcard/cardexpmonth',
        'exp_year': 'order/creditcard/cardexpyear',
        'verification_value': 'order/creditcard/cvmvalue',
        'card_type': None,
        #shipping
        'ship_full_name': 'order/shipping/name',
        'ship_first_name': None,
        'ship_last_name': None,
        'ship_to_co': None,
        'ship_address': 'order/shipping/address1',
        'ship_address2': 'order/shipping/address2',
        'ship_city': 'order/shipping/city',
        'ship_state': 'order/shipping/state',
        'ship_zipcode': 'order/shipping/zip',
        'ship_country': 'order/shipping/country',
        #transation
        'amount': 'order/payment/chargetotal',
        'trans_type': 'order/orderoptions/ordertype',
        'trans_id': 'order/transactiondetails/oid',
        'alt_trans_id': None,
    }

    # Response Code: 1 = Approved, 2 = Declined, 3 = Error, 4 = Held for Review
    # AVS Responses: A = Address (Street) matches, ZIP does not,  P = AVS not applicable for this transaction,
    # AVS Responses (cont'd): W = Nine digit ZIP matches, Address (Street) does not, X = Address (Street) and nine digit ZIP match, 
    # AVS Responses (cont'd): Y = Address (Street) and five digit ZIP match, Z = Five digit ZIP matches, Address (Street) does not
    # AVS Responses (cont'd): N = Neither the street address nor the postal code matches. R = Retry, System unavailable (maybe due to timeout)
    # AVS Responses (cont'd): S = Service not supported. U = Address information unavailable. E = Data not available/error invalid. 
    # AVS Responses (cont'd): G = Non-US card issuer that does not participate in AVS
    # response index keys to map the value to its proper dictionary key
    # it goes like this: 'gateway_specific_parameter' ==> 'paython_key'
    RESPONSE_KEYS = {
        'r_message':'response_text',
        'r_authresponse':'auth_code',
        'r_avs':'avs_response', 
        'r_ordernum':'trans_id',
        'r_ref':'alt_trans_id',
        #'fulltotal':'amount', <-- amount of transaction
        #'trantype':'trans_type', <-- type of transaction
        #'ordernumber':'alt_trans_id2', <-- third way of id'ing a transaction
        #'38':'cvv_response', <-- way of finding out if verification_value is invalid
        #'2':'response_reason_code', <-- mostly for reporting
        #'0':'response_code', <-- mostly for reporting
    }

    debug = False
    test = False
    cvv_present = False

    def __init__(self, username='Test123', key_file='../keys/yourkey.pem', cert_file='../keys/yourkey.pem', debug=False, test=False):
        """
        Setting up object so we can run 4 different ways (live, debug, test & debug+test) - no password because gateway does not use it
        """
        # passing fields to bubble up to Base Class
        ssl_config = {'port':'1129', 'key_file':key_file, 'cert_file':cert_file}
        # there is only a live environment, with test credentials & we only need the host for now
        url = urlparse.urlparse(self.API_URI['live']).netloc.split(':')[0]
        # initing the XML gateway
        super(FirstDataLegacy, self).__init__(url, translations=self.REQUEST_FIELDS, debug=debug, special_params=ssl_config)

        #setting some creds
        super(FirstDataLegacy, self).set('order/merchantinfo/configfile', username)

        if debug:
            self.debug = True

        if test:
            self.test = True
            debug_string = " paython.gateways.firstdata_legacy.__init__() -- You're in test mode (& debug, obviously) "
            logger.debug(debug_string.center(80, '='))

    def charge_setup(self):
        """
        standard setup, used for charges
        """
        if self.cvv_present:
            super(FirstDataLegacy, self).set('order/creditcard/cvmindicator', 'provided')
        
        if self.test: # will almost always return nice
            super(FirstDataLegacy, self).set('order/orderoptions/result', 'Good')
        else:
            super(FirstDataLegacy, self).set('order/orderoptions/result', 'Live')
        
        debug_string = " paython.gateways.firstdata_legacy.charge_setup() Just set up for a charge "
        logger.debug(debug_string.center(80, '='))

    def auth(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends charge for authorization based on amount
        """
        #check for cvv
        self.cvv_present = True if credit_card.verification_value else False
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_type'], 'Preauth')
        #special treatment to make peoples lives easier (extracting addrnum from address)
        try:
            matches = re.match('\d+', billing_info['address'])
        except KeyError:
            raise DataValidationError('Unable to find a billing address to extract a number from for gateway')

        if matches:
            super(FirstDataLegacy, self).set('order/billing/addrnum', matches.group()) #hardcoded because of uniqueness to gateway
        else:
            raise DataValidationError('Unable to find a number at the start of provided billing address')

        # validating or building up request
        if not credit_card:
            debug_string = "paython.gateways.firstdata_legacy.auth()  -- No CreditCard object present. You passed in %s " % (credit_card)
            logger.debug(debug_string)

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            credit_card._exp_yr_style = True
            super(FirstDataLegacy, self).use_credit_card(credit_card)

        if billing_info:
            super(FirstDataLegacy, self).set_billing_info(**billing_info)

        if shipping_info:
            super(FirstDataLegacy, self).set_shipping_info(**shipping_info)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def settle(self, amount, trans_id):
        """
        Sends prior authorization to be settled based on amount & trans_id PRIOR_AUTH_CAPTURE
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_type'], 'Postauth')
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def capture(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends transaction for capture (same day settlement) based on amount.
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_type'], 'Sale')

        #special treatment to make peoples lives easier (extracting addrnum from address)
        matches = re.match('\d+', billing_info['address'])
        if matches:
            super(FirstDataLegacy, self).set('order/billing/addrnum', matches.group()) #hardcoded because of uniqueness to gateway
        else:
            raise DataValidationError('Unable to find a number at the start of provided billing address')

        # validating or building up request
        if not credit_card:
            logger.debug("paython.gateways.firstdata_legacy.capture()  -- No CreditCard object present. You passed in %s " % (credit_card))

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            credit_card._exp_yr_style = True
            super(FirstDataLegacy, self).use_credit_card(credit_card)

        if billing_info:
            super(FirstDataLegacy, self).set_billing_info(**billing_info)

        if shipping_info:
            super(FirstDataLegacy, self).set_shipping_info(**shipping_info)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def void(self, trans_id):
        """
        Send a SALE (only works for sales) transaction to be voided (in full) that was initially sent for capture the same day
        This is so wierd!
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_type'], 'Void')
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def credit(self, amount, trans_id, credit_card):
        """
        Sends a transaction to be refunded (partially or fully)
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_type'], 'Credit')
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['number'], credit_card.number)

        if amount: #check to see if we should send an amount
            super(FirstDataLegacy, self).set(self.REQUEST_FIELDS['amount'], amount)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def request(self):
        """
        Makes a request using lib.api.XMLGateway.make_request() & move some debugging away from other methods.
        """
        #getting the uri to POST xml to
        uri = urlparse.urlparse(self.API_URI['live']).path

        debug_string = " paython.gateways.firstdata_legacy.request() -- Attempting request to: "
        logger.debug(debug_string.center(80, '='))
        logger.debug("\n %s with params: %s" %
                     (self.API_URI['live'],
                      super(FirstDataLegacy, self).request_xml()))

        # make the request
        start = time.time() # timing it
        response = super(FirstDataLegacy, self).make_request(uri)
        end = time.time() # done timing it
        response_time = '%0.2f' % (end-start)

        debug_string = " paython.gateways.firstdata_legacy.request()  -- Request completed in %ss " % response_time
        logger.debug(debug_string.center(80, '='))

        return response, response_time

    def parse(self, response, response_time):
        """
        On Specific Gateway due differences in response from gateway
        """
        debug_string = " paython.gateways.firstdata_legacy.parse() -- Raw response: "
        logger.debug(debug_string.center(80, '='))
        logger.debug("\n %s" % response)

        response = response['response']
        approved = True if response['r_approved'] == 'APPROVED' else False

        debug_string = " paython.gateways.firstdata_legacy.parse() -- Response as dict: "
        logger.debug(debug_string.center(80, '='))
        logger.debug('\n%s' % response)

        return super(FirstDataLegacy, self).standardize(response, self.RESPONSE_KEYS, response_time, approved)

########NEW FILE########
__FILENAME__ = innovative_gw
import time
import urlparse
import logging

from paython.exceptions import MissingDataError
from paython.lib.api import PostGateway

logger = logging.getLogger(__name__)

class InnovativeGW(PostGateway):
    """TODO needs docstring"""
    VERSION = 'WebCharge_v5.06'

    # This is how we determine whether or not we allow 'test' as an init param
    API_URI = {
        'live': 'https://transactions.innovativegateway.com/servlet/com.gateway.aai.Aai'
    }

    # This is how we translate the common Paython fields to Gateway specific fields
    # it goes like this: 'paython_key' ==> 'gateway_specific_parameter'
    REQUEST_FIELDS = {
        #contact
        'full_name': 'ccname',
        'first_name': None,
        'last_name': None,
        'email': 'email',
        'phone': 'bphone',
        #billing
        'address': 'baddress',
        'address2': 'baddress1',
        'city': 'bcity',
        'state': 'bstate',
        'zipcode': 'bzip',
        'country': 'bcountry',
        'ip': None,
        #card
        'number': 'ccnumber',
        'exp_date': None,
        'exp_month': 'month',
        'exp_year': 'year',
        'verification_value': 'ccidentifier1',
        'card_type': 'cardtype',
        #shipping
        'ship_full_name': None,
        'ship_first_name': None,
        'ship_last_name': None,
        'ship_to_co': None,
        'ship_address': 'saddress1',
        'ship_address2': 'saddress',
        'ship_city': 'scity',
        'ship_state': 'sstate',
        'ship_zipcode': 'szip',
        'ship_country': 'scountry',
        #transation
        'amount': 'fulltotal',
        'trans_type': 'trantype',
        'trans_id': 'trans_id',
        'alt_trans_id': 'reference',
    }

    # Response Code: 1 = Approved, 2 = Declined, 3 = Error, 4 = Held for Review
    # AVS Responses: A = Address (Street) matches, ZIP does not,  P = AVS not applicable for this transaction,
    # AVS Responses (cont'd): W = Nine digit ZIP matches, Address (Street) does not, X = Address (Street) and nine digit ZIP match,
    # AVS Responses (cont'd): Y = Address (Street) and five digit ZIP match, Z = Five digit ZIP matches, Address (Street) does not
    # AVS Responses (cont'd): N = Neither the street address nor the postal code matches. R = Retry, System unavailable (maybe due to timeout)
    # AVS Responses (cont'd): S = Service not supported. U = Address information unavailable. E = Data not available/error invalid.
    # AVS Responses (cont'd): G = Non-US card issuer that does not participate in AVS
    # response index keys to map the value to its proper dictionary key
    # it goes like this: 'gateway_specific_parameter' ==> 'paython_key'
    RESPONSE_KEYS = {
        'error':'response_text',
        'messageid':'auth_code',
        'avs':'avs_response',
        'anatransid':'trans_id',
        'fulltotal':'amount',
        'trantype':'trans_type',
        'approval':'alt_trans_id', # aka "reference" in intuit land
        'ordernumber':'alt_trans_id2',
        'fulltotal':'amount',
        #'38':'cvv_response', <-- way of finding out if verification_value is invalid
        #'2':'response_reason_code', <-- mostly for reporting
        #'0':'response_code', <-- mostly for reporting
    }

    debug = False
    test = False

    def __init__(self, username='gatewaytest', password='GateTest2002', debug=False):
        """
        setting up object so we can run 3 different ways (live, debug, live+debug no test endpoint available)
        """
        super(InnovativeGW, self).set('username', username)
        super(InnovativeGW, self).set('pw', password)

        # passing fields to bubble up to Base Class
        super(InnovativeGW, self).__init__(translations=self.REQUEST_FIELDS, debug=debug)

        if debug:
            self.debug = True

    def charge_setup(self):
        """
        standard setup, used for charges
        """
        super(InnovativeGW, self).set('target_app', self.VERSION)
        super(InnovativeGW, self).set('response_mode', 'simple')
        super(InnovativeGW, self).set('response_fmt', 'url_encoded')
        super(InnovativeGW, self).set('upg_auth', 'zxcvlkjh')

        debug_string = " paython.gateways.innovative_gw.charge_setup() Just set up for a charge "
        logger.debug(debug_string.center(80, '='))

    def auth(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends charge for authorization based on amount
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_type'], 'preauth')

        # validating or building up request
        if not credit_card:
            logger.debug("paython.gateways.innovative_gw.auth()  -- No CreditCard object present. You passed in %s " % (credit_card))

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            super(InnovativeGW, self).use_credit_card(credit_card)

        if billing_info:
            super(InnovativeGW, self).set_billing_info(**billing_info)

        if shipping_info:
            super(InnovativeGW, self).set_shipping_info(**shipping_info)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def settle(self, amount, trans_id, ref):
        """
        Sends prior authorization to be settled based on amount & trans_id PRIOR_AUTH_CAPTURE
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_type'], 'postauth')
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['alt_trans_id'], ref)
        super(InnovativeGW, self).set('authamount', amount) #hardcoded because of uniqueness to gateway

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def capture(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends transaction for capture (same day settlement) based on amount.
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_type'], 'sale')

        # validating or building up request
        if not credit_card:
            logger.debug("paython.gateways.innovative_gw.capture()  -- No CreditCard object present. You passed in %s " % (credit_card))

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            super(InnovativeGW, self).use_credit_card(credit_card)

        if billing_info:
            super(InnovativeGW, self).set_billing_info(**billing_info)

        if shipping_info:
            super(InnovativeGW, self).set_shipping_info(**shipping_info)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def void(self, trans_id, ref, ordernumber):
        """
        Sends a transaction to be voided (in full)
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_type'], 'void')
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['alt_trans_id'], ref)
        super(InnovativeGW, self).set('ordernumber', ordernumber) #hardcoded because of uniqueness to gateway

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def credit(self, amount, trans_id, ref, ordernumber):
        """
        Sends a transaction to be refunded (partially or fully)
        """
        #set up transaction
        self.charge_setup() # considering turning this into a decorator?

        #setting transaction data
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_type'], 'credit')
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(InnovativeGW, self).set(self.REQUEST_FIELDS['alt_trans_id'], ref)
        super(InnovativeGW, self).set('ordernumber', ordernumber) #hardcoded because of uniqueness to gateway

        if amount: #check to see if we should send an amount
            super(InnovativeGW, self).set(self.REQUEST_FIELDS['amount'], amount)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def request(self):
        """
        Makes a request using lib.api.GetGateway.make_request() & move some debugging away from other methods.
        """
        # there is only a live environment, with test credentials
        url = self.API_URI['live']

        debug_string = " paython.gateways.innovative_gw.request() -- Attempting request to: "
        logger.debug(debug_string.center(80, '='))
        logger.debug("\n %s with params: %s" %
                     (url, super(InnovativeGW, self).params()))

        # make the request
        start = time.time() # timing it
        response = super(InnovativeGW, self).make_request(url)
        end = time.time() # done timing it
        response_time = '%0.2f' % (end - start)

        debug_string = " paython.gateways.innovative_gw.request()  -- Request completed in %ss " % response_time
        logger.debug(debug_string.center(80, '='))

        return response, response_time

    def parse(self, response, response_time):
        """
        On Specific Gateway due differences in response from gateway
        """
        debug_string = " paython.gateways.innovative_gw.parse() -- Raw response: "
        logger.debug(debug_string.center(80, '='))
        logger.debug("\n %s" % response)

        new_response = urlparse.parse_qsl(response)
        response = dict(new_response)
        if 'approval' in response:
            approved = True
        else:
            approved = False
            response['approval'] = 'decline' # there because we have a translation key called "approval" - open to ideas here...

        debug_string = " paython.gateways.innovative_gw.parse() -- Response as dict: "
        logger.debug(debug_string.center(80, '='))
        logger.debug('\n%s' % response)

        return super(InnovativeGW, self).standardize(response, self.RESPONSE_KEYS, response_time, approved)

########NEW FILE########
__FILENAME__ = plugnpay
import time
import urllib
import logging

from paython.exceptions import MissingDataError
from paython.lib.api import PostGateway

logger = logging.getLogger(__name__)


class PlugnPay(PostGateway):
    """ plugnpay.com Payment Gatway Interface

    Based on the basic Remote Client Integration Specification Rev. 04.22.2011

    - @auth : Credit Card Authorization
    - @reauth : Used to settle a transaction at a lower dollar amount
    - @capture : Credit Card Authorization + Automatically marks transaction for settlement
    - @settle : Settle a specific transaction
    - @void : Cancels the most recent transaction operation (auth, postauth, or return) of the given orderID
    - @return_transaction : Return funds back to a prior authorization
    - @return_credit : Credits funds, using card info file from a previous transaction
    - @credit : Credits funds to card info provided
    - @query : Ability to query system for credit card transaction information
    """

    API_URI = 'https://pay1.plugnpay.com/payment/pnpremote.cgi'

    DELIMITER = '&'

    # This is how we translate the common Paython fields to Gateway specific fields
    REQUEST_FIELDS = {
        #contact
        'full_name': 'card-name',
        'first_name': None,
        'last_name': None,
        'email': 'email',
        'phone': 'phone',
        'fax': 'fax',
        #billing
        'address': 'card-address1',
        'address2': 'card-address2',
        'city': 'card-city',
        'state': 'card-state',
        'province': 'card-prov',
        'zipcode': 'card-zip',
        'country': 'card-country',
        'ip': None,
        #card
        'number': 'card-number',
        'exp_date': 'card-exp',
        'exp_month': None,
        'exp_year': None,
        'verification_value': 'card-cvv',
        'card_type': None,
        #shipping
        'ship_full_name': 'shipname',
        'ship_first_name': None,
        'ship_last_name': None,
        'ship_to_co': None,
        'ship_address': 'address1',
        'ship_address2': 'address2',
        'ship_city': 'city',
        'ship_state': 'state',
        'ship_province': 'province',
        'ship_zipcode': 'zip',
        'ship_country': 'country',
        #transation
        'amount': 'card-amount',
        'trans_mode': 'mode',
        'trans_type': 'authtype',
        'trans_id': 'orderID',
        'alt_trans_id': None,
    }

    # AVS response codes by credit card
    # https://pay1.plugnpay.com/admin/doc_replace.cgi?doc=AVS_Specifications.htm
    AVS_RESPONSE_KEYS = {}

    # Visa
    AVS_RESPONSE_KEYS['VISA'] = {
        'A': 'Address matches, ZIP code does not',
        'B': 'Street address match for international transaction; postal code not verified',
        'C': 'Street & postal code not verified for international transaction',
        'D': 'Street & Postal codes match for international transaction',
        'E': 'Transaction is ineligible for address verification',
        'F': 'Street address & postal codes match for international transaction. (UK Only)',
        'G': 'AVS not performed because the international issuer does not support AVS',
        'I': 'Address information not verified for international transaction',
        'M': 'Street address & postal codes match for international transaction',
        'N': 'Neither the ZIP nor the address matches',
        'P': 'Postal codes match for international transaction; street address not verified',
        'S': 'AVS not supported at this time',
        'R': "Issuer's authorization system is unavailable, try again later",
        'U': 'Unable to perform address verification because either address information is unavailable or the Issuer does not support AVS',
        'W': 'Nine-digit zip match, address does not',
        'X': 'Exact match (nine-digit zip and address)',
        'Y': 'Address & 5-digit or 9-digit ZIP match',
        'Z': 'Either 5-digit or 9-digit ZIP matches, address does not',
        '0': 'No AVS response returned from issuing bank'
    }

    # Mastercard
    AVS_RESPONSE_KEYS['MSTR'] = {
        'A': 'Address matches, ZIP code does not',
        'B': 'Street address match for international transaction; postal code not verified',
        'C': 'Street & postal code not verified for international transaction',
        'D': 'Street & Postal codes match for international transaction',
        'E': 'Address verification not allowed for card typ',
        'F': 'Street address & postal codes match for international transaction. (UK Only',
        'G': 'International Address information unavailable.',
        'I': 'Address information not verified for international transaction',
        'M': 'Street address & postal codes match for international transaction',
        'N': 'Neither the ZIP nor the address matches',
        'P': 'Postal codes match for international transaction; street address not verified',
        'S': 'AVS not supported at this time',
        'R': 'Retry, system unable to process',
        'U': 'No data from issuer/BankNet switch',
        'W': '9-digit ZIP code matches, but address does not',
        'X': 'Exact, all digits match, 9-digit ZIP code',
        'Y': 'Exact, all digits match, 5-digit ZIP code',
        'Z': '5-digit ZIP code matches, but address does not',
        '0': 'No AVS response returned from issuing bank'
    }

    # American Express
    AVS_RESPONSE_KEYS['AMEX'] = {
        'A': 'Address only is correc',
        'B': 'Street address match for international transaction; postal code not verified',
        'C': 'Street & postal code not verified for international transaction',
        'D': 'Street & Postal codes match for international transaction',
        'E': 'Address verification not allowed for card typ',
        'F': 'Street address & postal codes match for international transaction. (UK Only',
        'G': 'International Address information unavailable.',
        'I': 'Address information not verified for international transaction',
        'M': 'Street address & postal codes match for international transaction',
        'N': 'Neither the ZIP nor the address matche',
        'P': 'Street address match for international transaction; postal code not verified',
        'R': "Issuer's authorization system is unavailable, try again late",
        'S': 'AVS not supported at this tim',
        'U': 'The necessary information is not available, account number is neither U.S. nor Canadia',
        'W': 'Nine-digit zip match, address does not.',
        'X': 'Exact match (nine-digit zip and address).',
        'Y': 'Yes, address and ZIP code are both correct',
        'Z': 'ZIP code only is correc',
        '0': 'No AVS response returned from issuing bank',
    }

    # Discover
    AVS_RESPONSE_KEYS['SWTCH'] = {
        'A': 'Address matches, ZIP code does not',
        'B': 'Street address match for international transaction; postal code not verified',
        'C': 'Street & postal code not verified for international transaction',
        'D': 'Street & Postal codes match for international transaction',
        'E': 'Transaction is ineligible for address verificatio',
        'F': 'Street address & postal codes match for international transaction. (UK Only',
        'G': 'AVS not performed because the international issuer does not support AVS',
        'I': 'Address information not verified for international transaction',
        'M': 'Street address & postal codes match for international transaction',
        'N': 'Neither the ZIP nor the address matche',
        'P': 'Postal codes match for international transaction; street address not verified',
        'S': 'AVS not supported at this tim',
        'R': "Issuer's authorization system is unavailable, try again late",
        'U': 'Unable to perform address verification because either address information is unavailable or the Issuer does not support AV',
        'W': 'Nine-digit zip match, address does not.',
        'X': 'Exact match (nine-digit zip and address).',
        'Y': 'Address & 5-digit or 9-digit ZIP matc',
        'Z': 'Either 5-digit or 9-digit ZIP matches, address does no',
        '0': 'No AVS response returned from issuing bank'
    }

    STATUS_RESPONSE_KEYS = {

        # Payment Gateway Response Codes
        'P01': 'AVS Mismatch Failure',
        'P02': 'CVV2 Mismatch Failure',
        'P03': 'Sorry, the transaction failed Cybersource Fraud Test and was voided.',
        'P21': 'Transaction may not be marked',
        'P22': 'orderID was not marked successfully.',
        'P30': 'Test Tran. Bad Card',
        'P35': 'Test Tran. Problem',
        'P40': 'Username already exists',
        'P41': 'Username is blank',
        'P50': 'Fraud Screen Failure',
        'P51': 'Missing PIN Code',
        'P52': 'Invalid Bank Acct. No.',
        'P53': 'Invalid Bank Routing No.',
        'P54': 'Invalid/Missing Check No.',
        'P55': 'Invalid Credit Card No.',
        'P56': 'Invalid CVV2/CVC2 No.',
        'P57': 'Expired. CC Exp. Date',
        'P58': 'Missing Data',
        'P59': 'Missing Email Address',
        'P60': 'Zip Code does not match Billing State.',
        'P61': 'Invalid Billing Zip Code',
        'P62': 'Zip Code does not match Shipping State.',
        'P63': 'Invalid Shipping Zip Code',
        'P64': 'Invalid Credit Card CVV2/CVC2 Format.',
        'P65': 'Maximum number of attempts has been exceeded.',
        'P66': 'Credit Card number has been flagged and can not be used to access this service.',
        'P67': 'IP Address is on Blocked List.',
        'P68': 'Billing country does not match ipaddress country.',
        'P69': 'US based ipaddresses are currently blocked.',
        'P70': 'Credit Cards issued from this country are currently not being accepted.',
        'P71': 'Credit Cards issued from this bank are currently not being accepted.',
        'P72': 'Daily volume exceeded.',
        'P73': 'Too many transactions within allotted time.',
        'P74': 'Sales for this phone number are currently not being accepted.',
        'P75': 'Email Address is on Blocked List.',
        'P76': 'Duplicate Transaction error.',
        'P91': 'Missing/incorrect password',
        'P92': 'Account not configured for mobil administration',
        'P93': 'IP Not registered to username.',
        'P94': 'Mode not permitted for this account.',
        'P95': 'Currently Blank',
        'P96': 'Currently Blank',
        'P97': 'Processor not responding',
        'P98': 'Missing merchant/publisher name',
        'P99': 'Currently Blank',
        'P100': 'Discount exceeds available gift certificate balance.',
        'P101': 'Gift certificate discount does not match order.',

        # VisaNet / Vital Response Codes
        '00': 'Approved',
        '01': 'Refer to issuer',
        '02': 'Refer to issuer',
        '28': 'File is temporarily unavailable',
        '91': 'Issuer or switch is unavailable',
        '04': 'Pick up card',
        '07': 'Pick up card',
        '41': 'Pick up card - lost',
        '43': 'Pick up card - stolen',
        'EA': 'Verification error',
        '79': 'Already reversed at switch',
        '13': 'Invalid amount',
        '83': 'Can not verify PIN',
        '86': 'Can not verify PIN',
        '14': 'Invalid card number',
        '82': 'Cashback limit exceeded',
        'N3': 'Cashback service not available',
        'EB': 'Verification error',
        'EC': 'Verification error',
        '80': 'Invalid date',
        '05': 'Do not honor',
        '51': 'Insufficient funds',
        'N4': 'Exceeds issuer withdrawal limit',
        '61': 'Exceeds withdrawal limit',
        '62': 'Invalid service code, restricted',
        '65': 'Activity limit exceeded',
        '93': 'Violation, cannot complete',
        '81': 'Cryptographic error',
        '06': 'General error',
        '54': 'Expired card',
        '92': 'Destination not found',
        '12': 'Invalid transaction',
        '78': 'No account',
        '21': 'unable to back out transaction',
        '76': 'Unable to locate, no match',
        '77': 'Inconsistent date, rev. or repeat',
        '52': 'No checking account',
        '39': 'No credit account',
        '53': 'No savings account',
        '15': 'No such issuer',
        '75': 'PIN tries exceeded',
        '19': 'Re-enter transaction',
        '63': 'Security violation',
        '57': 'Trans. not permitted-Card',
        '58': 'Trans. not permitted-Terminal',
        '96': 'System malfunction',
        '03': 'Invalid merchant ID',
        '55': 'Incorrect PIN',
        'N7': 'CVV2 Value supplied is invalid',
        'xx': 'Undefined response',
        'CV': 'Card type verification error',
        'R1': 'Stop recurring',

        # Mercury Response Codes
        '001': 'Refer to Issuer',
        '002': 'Refer to Issuer',
        '003': 'Invalid to Merchant ID',
        '004': 'Pick up card',
        '005': 'Authorization declined',
        '006': 'Reversal was successful',
        '007': 'CVV failure',
        '008': 'Approved with positive ID',
        '012': 'Invalid transaction code',
        '013': 'Invalid amount',
        '014': 'Invalid account or Amex CID failure',
        '019': 'Please retry',
        '054': 'Invalid expiration date',
        '055': 'Incorrect PIN',
        '058': 'Merchant not setup for transaction code used',
        '075': 'Maximum PIN number entry attempts exceeded',
        '094': 'Transaction entered is a duplicate',
        '998': 'Invalid account number or security code',
        '0C1': 'System unavailable',
        '0N1': 'The account number for a void or adjustment does not match stored value',
        '0N2': 'The amount entered for a void or adjustment transaction does not match stored value',
        '0N3': 'The item number entered for a void or adjustment transaction is incorrect',
        '0N4': 'An adjustment or item review was attempted on a transaction previously voided or reversed',
        '0N5': 'Terminal has not been balanced within time specified in the mercury Payments Merchant master file',
        '0N6': 'Terminal has not been balanced within time specified in the master file, but merchant is setup to perform extra transactions before balancing',
        '0N7': 'Override transaction is attempted on a non-duplicated transaction',
        '0N8': 'Format of the transaction is incorrect',
        '0NA': 'Reversal transaction is attempted on a transaction that is not in the open batch on the host',
        '0NC': 'Approved but not captured (applies only to credit card transactions)',
        '0NE': 'Approved but this EDC merchant is not setup to capture this card type',
        '0NF': 'Acquiring Bank ID entered is incorrect',
        '0P0': 'Transaction not supported by EFT Network or card issuer',
        '0P1': 'Approved debit card transaction',
        '0P2': 'mercury Payments Gateway is down',
        '0P3': 'mercury Payments Gateway link timed out',
        '0P4': 'mercury Payments Gateway cannot contact EFT network or EFT Group ID is incorrect',
        '0P5': 'Merchant is not setup for debit on mercury Payments merchant master file',
        '0P6': 'Debit card not on issuer file',
        '0P7': 'EFT network cannot contact issuer',
        '0P8': 'Card is not eligible for POS',
        '0P9': 'Type of account entered cannot be accessed',
        '0PA': 'No sharing arrangement for this card',
        '0PB': 'mercury Payments Gateway financial institutio ID not setup',
        '0S0': 'Match on SCAN file. Routing/transit number on the negative file',
        '0S1': 'The license or ID number entered during a check authorization transaction is incorrect',
        '0S2': 'State code entered is incorrect',
        '0T1': 'EDC application down, try later',
        '0T2': 'Debit application down, try later',
        '0T3': 'SCAN application is down, try later',
        '121': 'Exceeds withdrawal amount limit',
        '123': 'Exceeds withdrawal frequency limit',
    }

    SIMPLE_STATUS_RESPONSE_KEYS = {
        'A': 'Approved',
        'C': 'Call Auth Center',
        'D': 'Declined',
        'P': 'Pick up card',
        'X': 'Expired',
        'E': 'Other Error'
    }

    RESPONSE_KEYS = {
        'sresp': 'response_code',
        'sresp-msg': 'response_text',
        'resp-code-msg': 'response_reason',
        'resp-code': 'response_reason_code',
        'auth-code': 'auth_code',
        'avs-code': 'avs_response',
        'avs-code-msg': 'avs_response_text',
        'orderID': 'trans_id',
        'card-amount': 'amount',
        'authtype': 'trans_type',
        'merchfraudlev': 'fraud_level',
        'alt_trans_id': 'ref_number',  # refnumber
        'MErrMsg': 'error_message',  # not sure what M means
        'FinalStatus': 'final_status'
    }

    debug = False

    def __init__(self, username='pnpdemo', password='', email='', dontsndmail=True, debug=True):

        # mandatory fields for every request
        super(PlugnPay, self).set('publisher-name', username)
        if password: # optional gateway password
            super(PlugnPay, self).set('publisher-password', password)

        if email: # publisher email to send alerts/notifiation to
            super(PlugnPay, self).set('publisher-email', email)

        # don't send transaction confirmation email to customer
        if dontsndmail:
            super(PlugnPay, self).set('dontsndmail', 'yes')

        if debug:
            self.debug = True

        debug_string = " paython.gateways.plugnpay.__init__() -- You're in debug mode"
        logger.debug(debug_string.center(80, '='))

    def auth(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends charge for authorization only based on amount
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_type'], 'authonly')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'auth')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)

        # validating or building up request
        if not credit_card:
            debug_string = "paython.gateways.plugnpay.auth()  -- No CreditCard object present. You passed in %s " % (credit_card)
            logger.debug(debug_string)

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            super(PlugnPay, self).use_credit_card(credit_card)

        if billing_info:
            super(PlugnPay, self).set_billing_info(**billing_info)

        if shipping_info:
            super(PlugnPay, self).set_shipping_info(**shipping_info)

        response, response_time = self.request()
        return self.parse(response, response_time)

    def reauth(self, amount, trans_id):
        """
        Used to settle a transaction at a lower dollar amount.
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'reauth')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)

        response, response_time = self.request()
        return self.parse(response, response_time)

    def capture(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends transaction for auth + capture (same day settlement) based on amount.
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_type'], 'authpostauth')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'auth')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)

        # validating or building up request
        if not credit_card:
            debug_string = "paython.gateways.plugnpay.capture()  -- No CreditCard object present. You passed in %s " % (credit_card)
            logger.debug(debug_string)

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            super(PlugnPay, self).use_credit_card(credit_card)

        if billing_info:
            super(PlugnPay, self).set_billing_info(**billing_info)

        if shipping_info:
            super(PlugnPay, self).set_shipping_info(**shipping_info)

        response, response_time = self.request()
        return self.parse(response, response_time)

    def settle(self, amount, trans_id):
        """
        Sends prior authorization to be settled based on amount & trans_id
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'mark')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)

        response, response_time = self.request()
        return self.parse(response, response_time)

    def void(self, amount, trans_id):
        """
        Sends a transaction to be voided
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'void')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(PlugnPay, self).set('txn-type', 'auth')

        response, response_time = self.request()
        return self.parse(response, response_time)

    def return_transaction(self, amount, trans_id):
        """
        Return funds back to a prior authorization.

        - This cannot be used on transactions over 6 months old
        - This type of return is limited to one use per orderID.
        - Amount returned cannot exceed that of the original auth.
        - Use this mode when returning funds back to the same transaction.
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'return')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)
        super(PlugnPay, self).set('txn-type', 'auth')

        response, response_time = self.request()
        return self.parse(response, response_time)

    def return_credit(self, amount, trans_id):
        """
        Credits funds, using card info file from a previous transaction.

        - This type of return is NOT linked to the previous transaction's records; instead a new orderID will be associated to each return submitted.
        - This cannot be used on transactions over 6 months old
        - This type of return can be issued for any amount & can be used as often as needed.
        - Use this mode when amount returned exceeds that of the original auth &/or when you want to issue the return to a card already on file.
        - Use this mode when issuing additional returns on a particular transaction. (i.e. use 'return' mode for 1st return, then use 'returnprev' for 2nd, 3rd, 4th, Nth return)
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'returnprev')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)

        response, response_time = self.request()
        return self.parse(response, response_time)

    def credit(self, amount, credit_card, trans_id=None):
        """
        Credits funds to card info provided

        The optionally submitted `trans_id` overwrites the NEW Credit Transaction.
        If not submitted one will be generated using a date/time string

        - Credits are not associated with any prior authorization; a new orderID will be associated to each credit submitted.
        - Credits can issued for any amount & can be used as often as needed.
        - Use this mode for returning funds on transactions over 6 months old.
        - Use this mode when returning funds to a different card, then what was originally used by the customer.
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'newreturn')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)
        super(PlugnPay, self).set(self.REQUEST_FIELDS['amount'], amount)

        super(PlugnPay, self).use_credit_card(credit_card)

        response, response_time = self.request()
        return self.parse(response, response_time)

    def query(self, trans_id):
        """
        Ability to query system for credit card transaction information
        """

        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_mode'], 'query_trans')
        super(PlugnPay, self).set(self.REQUEST_FIELDS['trans_id'], trans_id)

        response, response_time = self.request()
        return self.parse(response, response_time)

    def request(self):
        """
        Makes a request using lib.api.GetGateway.make_request() & move some debugging away from other methods.
        """

        debug_string = " paython.gateways.plugnpay.request() -- Attempting request to: "
        logger.debug(debug_string.center(80, '='))
        debug_string = "\n %s with params: %s" % (self.API_URI, super(PlugnPay, self).params())
        logger.debug(debug_string)

        # make the request
        start = time.time() # timing it
        response = super(PlugnPay, self).make_request(self.API_URI)
        end = time.time() # done timing it
        response_time = '%0.2f' % (end - start)

        debug_string = " paython.gateways.plugnpay.request()  -- Request completed in %ss " % response_time
        logger.debug(debug_string.center(80, '='))

        return response, response_time

    def parse(self, raw_response, response_time):
        """
        On Specific Gateway due differences in response from gateway

        Populates the `response` dict with additional human-readable fields:
        `avs-code-msg`  : AVS code description
        `sresp-msg`     : Simplified Response Code Message (Approved, Declined etc)
        `resp-code-msg` : Gateway Response Code Message
        """

        debug_string = " paython.gateways.plugnpay.parse() -- Raw response: "
        logger.debug(debug_string.center(80, '='))
        debug_string = "\n %s" % raw_response
        logger.debug(debug_string)

        #splitting up response into a list so we can map it to Paython generic response
        raw_response = raw_response.split(self.DELIMITER)

        # map key/value keys to `response` dict
        response = {}
        for field in raw_response:
            t = field.split('=')
            response[urllib.unquote(t[0])] = urllib.unquote(t[1]).strip('|').strip()

        # map AVS code to string based on `card-type`
        if response.has_key('avs-code'):
            if (response.get('card-type') in self.AVS_RESPONSE_KEYS and
                response['avs-code'] in self.AVS_RESPONSE_KEYS[response['card-type']]
            ):
                response['avs-code-msg'] = self.AVS_RESPONSE_KEYS[response['card-type']][response['avs-code']]
            elif response['avs-code'] in self.AVS_RESPONSE_KEYS['VISA']:  # default to VISA AVS description
                response['avs-code-msg'] = self.AVS_RESPONSE_KEYS['VISA'][response['avs-code']]

        # simple response code description
        if response.get('sresp') in self.SIMPLE_STATUS_RESPONSE_KEYS:
            response['sresp-msg'] = self.SIMPLE_STATUS_RESPONSE_KEYS[response['sresp']]

        # exact response code description by Merchant Processors
        if response.has_key('resp-code') and response['resp-code'] in self.STATUS_RESPONSE_KEYS:
            response['resp-code-msg'] = self.STATUS_RESPONSE_KEYS[response['resp-code']]

        # parse Transaction status
        # FinalStatus is The Right Way to parse the transaction status
        # valid FinalStatus values:
        # success
        # badcard = transaction declined
        # problem = transaction could not be processed at this time
        # fraud = authorization flagged as fraudulent
        # Unapproved values have an accompanying MErrMsg field saying why
        approved = response['FinalStatus'] == 'success'

        debug_string = " paython.gateways.plugnpay.parse() -- Response as list: "
        logger.debug(debug_string.center(80, '='))
        debug_string = '\n%s' % response
        logger.debug(debug_string)

        return super(PlugnPay, self).standardize(response, self.RESPONSE_KEYS, response_time, approved)


########NEW FILE########
__FILENAME__ = samurai_ff
import time
import logging

from paython.gateways.core import Gateway
from paython.exceptions import *

logger = logging.getLogger(__name__)

try:
    import samurai.config as config
    from samurai.payment_method import PaymentMethod
    from samurai.processor import Processor
    from samurai.transaction import Transaction
except ImportError:
    raise Exception('Samurai library not found, please install requirements.txt')

class Samurai(Gateway):
    """TODO needs docstring"""
    VERSION = 'v1'

    REQUEST_FIELDS = {
        'first_name':'first_name',
        'last_name':'last_name',
        'address':'address_1',
        'city':'city',
        'state':'state',
        'zipcode':'zip'
    }

    RESPONSE_KEYS = {
        'transaction_token':'trans_id',
        'transaction_type':'trans_type',
        'reference_id':'alt_trans_id',
        'amount':'amount'
    }

    def __init__(self, merchant_key=None, password=None, processor=None, debug=False):
        """
        setting up object so we can run 2 different ways (live & debug)

        we have username and api_key because other gateways use "username"
        and we want to make it simple to change out gateways ;)
        """
        config.merchant_key = merchant_key
        config.merchant_password = password
        config.processor_token = processor

        # passing fields to bubble up to Base Class
        super(Samurai, self).__init__(set_method=self.set, translations=self.REQUEST_FIELDS, debug=debug)

        if debug:
            self.debug = True
        debug_string = " paython.gateways.samurai_ff.__init__() -- You're in debug mode"
        logger.debug(debug_string.center(80, '='))

    def set(self, key, value):
        """
        Does not serve a purpose other than to let us inherit
        from core.Gateway with no problems
        """
        pass

    def translate(self, info):
        """
        Translates the data for billing_info
        """
        new_dict = dict()
        for k, v in info.items():
            try:
                new_dict[self.REQUEST_FIELDS[k]] = v
            except KeyError:
                pass
        return new_dict

    def charge_setup(self, card, billing_info):
        """
        standard setup, used for charges
        """
        billing_info = self.translate(billing_info)

        # use the card + extra data- send it to samurai for storage and tokenization
        card._exp_yr_style = True
        super(Samurai, self).use_credit_card(card)
        pm = PaymentMethod.create(
                    card.number,
                    card.verification_value,
                    card.exp_month, card.exp_year, **billing_info)

        debug_string = " paython.gateways.samurai_ff.charge_setup() -- response on setting pm"
        logger.debug(debug_string.center(80, '='))
        logger.debug(dir(pm))

        if pm.errors:
            raise DataValidationError('Invalid Card Data: %s' % pm.errors[pm.error_messages[0]['context']][0])

        return pm.payment_method_token

    def auth(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        # set up the card for charging, obviously
        card_token = self.charge_setup(credit_card, billing_info)
        # start the timer
        start = time.time()
        # send it over for processing
        response = Processor.authorize(card_token, amount)
        # measure time
        end = time.time() # done timing it
        response_time = '%0.2f' % (end-start)
        # return parsed response
        return self.parse(response, response_time)

    def settle(self, amount, trans_id):
        txn = Transaction.find(trans_id)
        if txn.errors:
            raise GatewayError('Problem fetching transaction: %s' % txn.errors[txn.error_messages[0]['context']][0])
        else:
            # start the timer
            start = time.time()
            response = txn.capture(amount)
            # measure time
            end = time.time() # done timing it
            response_time = '%0.2f' % (end-start)
            # return parsed response
            return self.parse(response, response_time)
            
    def capture(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        # set up the card for charging, obviously
        card_token = self.charge_setup(credit_card, billing_info)
        # start the timer
        start = time.time()
        # send it over for processing
        response = Processor.purchase(card_token, amount)
        # measure time
        end = time.time() # done timing it
        response_time = '%0.2f' % (end-start)
        # return parsed response
        return self.parse(response, response_time)

    def void(self, trans_id):
        txn = Transaction.find(trans_id)
        if txn.errors:
            raise GatewayError('Problem fetching transaction: %s' % txn.errors[txn.error_messages[0]['context']][0])
        else:
            # start the timer
            start = time.time()
            response = txn.void()
            # measure time
            end = time.time() # done timing it
            response_time = '%0.2f' % (end-start)
            # return parsed response
            return self.parse(response, response_time)

    def credit(self, amount, trans_id):
        txn = Transaction.find(trans_id)
        if txn.errors:
            raise GatewayError('Problem fetching transaction: %s' % txn.errors[txn.error_messages[0]['context']][0])
        else:
            # start the timer
            start = time.time()
            response = txn.reverse(amount)
            # measure time
            end = time.time() # done timing it
            response_time = '%0.2f' % (end-start)
            # return parsed response
            return self.parse(response, response_time)

    def parse(self, response, response_time):
        """
        Make sure we translate the stuff not in self.RESPONSE_KEYS, like:
        cvv_response
        avs_response
        response_text
        """
        resp = response.__dict__
        rd = super(Samurai, self).standardize(resp, self.RESPONSE_KEYS, response_time, resp['success'])
        
        # now try to update the other stuff
        if response.errors:
            rd['response_text'] = resp['errors'][resp['error_messages'][0]['context']][0]
            rd['cvv_response'] = resp['processor_response'].get('cvv_result_code')
            rd['avs_response'] = resp['processor_response'].get('avs_result_code')

        return rd

########NEW FILE########
__FILENAME__ = stripe_com
import time
import logging

try:
    import stripe
except ImportError:
    raise Exception('Stripe library not found, please install requirements.txt')

logger = logging.getLogger(__name__)

class Stripe(object):
    """TODO needs docstring"""
    VERSION = 'v1'

    RESPONSE_KEYS = {
        'id':'trans_id',
        'amount':'amount',
        'cvv_response':'cvc_check',
        'avs_response':'address_line1_check',
    }
    debug = False
    test = False
    stripe_api = stripe

    def __init__(self, username=None, api_key=None, debug=False):
        """
        setting up object so we can run 2 different ways (live & debug)

        we have username and api_key because other gateways use "username"
        and we want to make it simple to change out gateways ;)
        """
        self.stripe_api.api_key = username or api_key

        if debug:
            self.debug = True
        debug_string = " paython.gateways.stripe.__init__() -- You're in debug mode"
        logger.debug(debug_string.center(80, '='))

    def auth(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Not implemented because stripe does not support authorizations:
        https://answers.stripe.com/questions/can-i-authorize-transactions-first-then-charge-the-customer-after-service-is-comp
        """
        raise NotImplementedError('Stripe does not support auth or settlement. Try capture().')

    def settle(self, amount, trans_id):
        """
        Not implemented because stripe does not support auth/settle:
        https://answers.stripe.com/questions/can-i-authorize-transactions-first-then-charge-the-customer-after-service-is-comp
        """
        raise NotImplementedError('Stripe does not support auth or settlement. Try capture().')

    def capture(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        debug_string = " paython.gateways.stripe.parse() -- Sending charge "
        logger.debug(debug_string.center(80, '='))

        amount = int(float(amount)*100) # then change the amount to how stripe likes it

        start = time.time() # timing it
        try:
            response = self.stripe_api.Charge.create(
                amount=amount,
                currency="usd",
                card={
                    "name":credit_card.full_name,
                    "number": credit_card.number,
                    "exp_month": credit_card.exp_month,
                    "exp_year": credit_card.exp_year,
                    "cvc": credit_card.verification_value if credit_card.verification_value else None,
                    "address_line1":billing_info.get('address'),
                    "address_line2":billing_info.get('address2'),
                    "address_zip":billing_info.get('zipcode'),
                    "address_state":billing_info.get('state')
                },
            )
        except stripe.InvalidRequestError, e:
            response = {'failure_message':'Invalid Request: %s' % e}
            end = time.time() # done timing it
            response_time = '%0.2f' % (end-start)
        except stripe.CardError, e:
            response = {'failure_message':'Card Error: %s' % e}
            end = time.time() # done timing it
            response_time = '%0.2f' % (end-start)
        else:
            end = time.time() # done timing it
            response_time = '%0.2f' % (end-start)

        return self.parse(response, response_time)

    def void(self, trans_id):
        """
        Not implemented because Stripe does not support transaction voiding
        """
        raise NotImplementedError('Stripe does not support transaction voiding. Try credit().')

    def credit(self, amount, trans_id):
        debug_string = " paython.gateways.stripe.parse() -- Sending credit "
        logger.debug(debug_string.center(80, '='))

        amount = int(float(amount) * 100)
        start = time.time() # timing it
        try:
            ch = self.stripe_api.Charge.retrieve(trans_id)
            response = ch.refund(amount=amount)
        except Exception, e:
            response = {'failure_message':'Unable to refund: %s' % e}
            end = time.time() # done timing it
            response_time = '%0.2f' % (end - start)
        else:
            end = time.time() # done timing it
            response_time = '%0.2f' % (end - start)

        return self.parse(response, response_time)

    def parse(self, response, response_time):
        """
        turn the response into a dict and attach these things:
        response_text
        response_time
        trans_type
        approved
        cvv_response
        avs_response

        before returning the dict
        """
        if hasattr(response, 'to_dict'):
            response = response.to_dict()

        debug_string = " paython.gateways.stripe.parse() -- Dict response: "
        logger.debug(debug_string.center(80, '='))
        logger.debug("\n %s" % response)

        new_response = {}

        # alright now lets stuff some info in here
        new_response['response_time'] = response_time
        # determining success
        new_response['response_text'] = response['failure_message'] or 'success'
        new_response['approved'] = True if not response['failure_message'] else False
        # trans type ;)
        new_response['trans_type'] = 'credit' if response.get('amount_refunded') > 0 else 'capture'

        for key in self.RESPONSE_KEYS.keys():
            if response.get(key):
                if key == 'amount':
                    response[key] = '%.2f' % (float(response[key])/float(100))

                new_response[self.RESPONSE_KEYS[key]] = response[key]
        return new_response

########NEW FILE########
__FILENAME__ = usaepay
import time
import urlparse
import logging

from paython.exceptions import MissingDataError
from paython.lib.api import PostGateway

logger = logging.getLogger(__name__)

class USAePay(PostGateway):
    """ usaepay.com Payment Gatway Interface

    Based on the CGI Transaction Gateway API v2.17.1

    The method names used should be consistent with the Authorize.net terms,
    which are not always the same as those used by USAePay.

    - @auth : Credit Card Authorization
    - @capture : Credit Card Authorization + Automatically marks transaction for settlement
    - @settle : Settle a specific transaction
    - @adjust : Adjust the amount of a previous transaction
    - @void : Cancels the most recent transaction operation (auth, postauth, or return) of the given orderID
    - @credit : Credits funds to card info provided
    - @open_credit : Refund to card provided, not linked to previous transaction
    """

    # This is how we translate the common Paython fields to Gateway specific fields
    REQUEST_FIELDS = {
        #contact
        'full_name' : 'UMname',
        'first_name': None,
        'last_name': None,
        'email': 'UMcustemail',
        'phone': 'UMbillphone',
        #billing
        'address': 'UMbillstreet',
        'address2': 'UMbillstreet2',
        'city': 'UMbillcity',
        'state': 'UMbillstate',
        'zipcode': 'UMbillzip',
        'country': 'UMbillcountry',
        'ip': 'UMip',
        #card
        'number': 'UMcard',
        'exp_date': 'UMexpir',
        'exp_month': None,
        'exp_year': None,
        'verification_value': 'UMcvv2',
        'card_type': None,
        #shipping
        'ship_full_name': None,
        'ship_first_name': 'UMshipfname',
        'ship_last_name': 'UMshiplname',
        'ship_to_co': 'UMshipcompany',
        'ship_address': 'UMshipstreet',
        'ship_address2': 'UMshipstreet2',
        'ship_city': 'UMshipcity',
        'ship_state': 'UMshipstate',
        'ship_zipcode': 'UMshipzip',
        'ship_country': 'UMshipcountry',
        #transation
        'amount': 'UMamount',
        'trans_type': 'UMcommand',
        'trans_id': 'UMrefNum',
        'alt_trans_id': None,
    }

    # Response Code: 1 = Approved, 2 = Declined, 3 = Error, 4 = Held for Review
    # AVS Responses: A = Address (Street) matches, ZIP does not,  P = AVS not applicable for this transaction,
    # AVS Responses (cont'd): W = Nine digit ZIP matches, Address (Street) does not, X = Address (Street) and nine digit ZIP match,
    # AVS Responses (cont'd): Y = Address (Street) and five digit ZIP match, Z = Five digit ZIP matches, Address (Street) does not
    # response index keys to map the value to its proper dictionary key
    RESPONSE_KEYS = {
        'UMresult' :         'response_code',
        'UMerror' :          'response_text',
        'UMauthCode' :       'auth_code',
        'UMavsResult' :      'avs_response',
        'UMrefNum' :         'trans_id',
        'UMauthAmount' :     'amount',
        'UMcvv2ResultCode' : 'cvv_response',
        'UMavsResult' :      'avs_response_text',
        #'n/a' :              'response_reason_code',
        #'n/a' :              'trans_type',
        #'n/a' :              'alt_trans_id',
        #'n/a' :              'response_reason',
        #'n/a' :              'fraud_level',
    }

    def __init__(self, username='test', password='testpassword', debug=False, test=False):
        """
        setting up object so we can run 4 different ways (live, debug, test & debug+test)
        """
        # passing fields to bubble up to Base Class
        super(USAePay, self).__init__(translations=self.REQUEST_FIELDS, debug=debug)

        self.set('UMkey', username)
        #self.set('UM', password)

        self.API_URI = {
                        False : 'https://www.usaepay.com/gate',
                        True :  'https://sandbox.usaepay.com/gate'
                       }

        self.test = test
        if test:
            debug_string = self._get_debug_str_base() + ".__init__() -- You're in test mode (& debug, obviously) "
            logger.debug(debug_string.center(80, '='))

    def _get_debug_str_base(self):
        return ' ' + __name__ + '.' + self.__class__.__name__

    def charge_setup(self):
        """
        standard setup, used for charges
        """
        #self.set('x_delim_data', 'TRUE')
        #self.set('x_delim_char', self.DELIMITER)
        #self.set('x_version', self.VERSION)
        debug_string = self._get_debug_str_base() + '.charge_setup() Just set up for a charge '
        logger.debug(debug_string.center(80, '='))

    def auth(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends charge for authorization based on amount
        """
        #set up transaction
        self.charge_setup()

        #setting transaction data
        self.set(self.REQUEST_FIELDS['amount'], amount)
        self.set(self.REQUEST_FIELDS['trans_type'], 'cc:authonly')

        # validating or building up request
        if not credit_card:
            debug_string = self._get_debug_str_base() + '.auth()  -- No CreditCard object present. You passed in %s ' % (credit_card)
            logger.debug(debug_string)

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            self.use_credit_card(credit_card)

        if billing_info:
            self.set_billing_info(**billing_info)

        if shipping_info:
            self.set_shipping_info(**shipping_info)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def settle(self, amount, trans_id):
        """
        Sends prior authorization to be settled based on amount & trans_id
        """
        #set up transaction
        self.charge_setup() 

        #setting transaction data
        self.set(self.REQUEST_FIELDS['trans_type'], 'cc:capture')
        self.set(self.REQUEST_FIELDS['amount'], amount)
        self.set(self.REQUEST_FIELDS['trans_id'], trans_id)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def adjust(self, amount, trans_id):
        """
        Adjust an existing (unsettled) sale.  Adjust the amount up or down, etc.
        """
        #set up transaction
        self.charge_setup() 

        #setting transaction data
        self.set(self.REQUEST_FIELDS['trans_type'], 'cc:adjust')
        self.set(self.REQUEST_FIELDS['amount'], amount)
        self.set(self.REQUEST_FIELDS['trans_id'], trans_id)

        # send transaction to gateway!
        response, response_time = self.request()
        return self.parse(response, response_time)

    def capture(self, amount, credit_card=None, billing_info=None, shipping_info=None):
        """
        Sends transaction for capture (same day settlement) based on amount.
        """
        #set up transaction
        self.charge_setup()

        #setting transaction data
        self.set(self.REQUEST_FIELDS['amount'], amount)
        self.set(self.REQUEST_FIELDS['trans_type'], 'cc:sale')

        # validating or building up request
        if not credit_card:
            debug_string = self._get_debug_str_base() + 'capture()  -- No CreditCard object present. You passed in ' + str(credit_card)
            logger.debug(debug_string)

            raise MissingDataError('You did not pass a CreditCard object into the auth method')
        else:
            self.use_credit_card(credit_card)

        if billing_info:
            self.set_billing_info(**billing_info)

        if shipping_info:
            self.set_shipping_info(**shipping_info)

        # send transaction to gateway
        response, response_time = self.request()
        return self.parse(response, response_time)

    def void(self, trans_id):
        """
        Sends a transaction to be voided (in full)
        """
        #set up transaction
        self.charge_setup()

        #setting transaction data
        self.set(self.REQUEST_FIELDS['trans_type'], 'void')
        self.set(self.REQUEST_FIELDS['trans_id'], trans_id)

        # send transaction to gateway
        response, response_time = self.request()
        return self.parse(response, response_time)

    def credit(self, amount, trans_id, credit_card):
        """
        Sends a transaction to be refunded (partially or fully)
        """
        #set up transaction
        self.charge_setup()

        #setting transaction data
        self.set(self.REQUEST_FIELDS['trans_type'], 'refund')
        self.set(self.REQUEST_FIELDS['trans_id'], trans_id)
        self.set(self.REQUEST_FIELDS['number'], credit_card.number)

        if amount: #check to see if we should send an amount
            self.set(self.REQUEST_FIELDS['amount'], amount)

        # send transaction to gateway
        response, response_time = self.request()
        return self.parse(response, response_time)

    def open_credit(self, amount, credit_card):
        """
        Refund money to a credit card, not linked to a previous transaction
        """
        #set up transaction
        self.charge_setup()

        #setting transaction data
        self.set(self.REQUEST_FIELDS['trans_type'], 'cc:credit')
        self.set(self.REQUEST_FIELDS['number'], credit_card.number)

        if amount: #check to see if we should send an amount
            self.set(self.REQUEST_FIELDS['amount'], amount)

        # send transaction to gateway
        response, response_time = self.request()
        return self.parse(response, response_time)

    def request(self):
        """
        Makes a request using lib.api.GetGateway.make_request() & move some debugging away from other methods.
        """
        # decide which url to use (test|live)
        url = self.API_URI[self.test]

        debug_string = self._get_debug_str_base() + '.request() -- Attempting request to: '
        logger.debug(debug_string.center(80, '='))
        logger.debug("\n %s with params: %s" % (url, self.params()))

        # make the request
        start = time.time() # timing it
        response = self.make_request(url)
        end = time.time() # done timing it
        response_time = '%0.2f' % (end-start)

        debug_string = self._get_debug_str_base() + '.request()  -- Request completed in ' + response_time + 's '
        logger.debug(debug_string.center(80, '='))

        return response, response_time

    def parse(self, response, response_time):
        """
        On Specific Gateway due differences in response from gateway
        """
        debug_string = self._get_debug_str_base() + '.parse() -- Raw response: '
        logger.debug(debug_string.center(80, '='))
        logger.debug('\n ' + str(response))

        #splitting up response into a list so we can map it to Paython generic response
        new_response = urlparse.parse_qsl(response)
        response = dict(new_response)
        approved = (response['UMresult'] == 'A')

        debug_string = self._get_debug_str_base() + '.parse() -- Response as list: '
        logger.debug(debug_string.center(80, '='))
        logger.debug('\n' + str(response))

        return self.standardize(response, self.RESPONSE_KEYS, response_time, approved)

########NEW FILE########
__FILENAME__ = api
import httplib
import urllib
import xml.dom.minidom

from utils import parse_xml
from paython.gateways.core import Gateway
from paython.exceptions import RequestError, GatewayError, DataValidationError

class XMLGateway(Gateway):
    def __init__(self, host, translations, debug=False, special_params={}):
        """ initalize API call session

        host: hostname (apigateway.tld)
        auth: accept a tuple with (username,password)
        debug: True/False
        """
        self.doc = xml.dom.minidom.Document()
        self.api_host = host
        self.debug = debug
        self.parse_xml = parse_xml
        self.special_ssl = special_params
        super(XMLGateway, self).__init__(set_method=self.set, translations=translations, debug=debug)

    def set(self, path, child=False, attribute=False):
        """ Accepts a forward slash seperated path of XML elements to traverse and create if non existent.
        Optional child and target node attributes can be set. If the `child` attribute is a tuple
        it will create X child nodes by reading each tuple as (name, text, 'attribute:value') where value
        and attributes are optional for each tuple.

        - path: forward slash seperated API element path as string (example: "Order/Authentication/Username")
        - child: tuple of child node data or string to create a text node
        - attribute: sets the target XML attributes (string format: "Key:Value")
        """
        try:
            xml_path = path.split('/')
        except AttributeError:
            return # because if it's None, then don't worry

        xml_doc = self.doc

        # traverse full XML element path string `path`
        for element_name in xml_path:
            # get existing XML element by `element_name`
            element = self.doc.getElementsByTagName(element_name)
            if element: element = element[0]

            # create element if non existing or target element
            if not element or element_name == xml_path[-1:][0]:
                element = self.doc.createElement(element_name)
                xml_doc.appendChild(element)

            xml_doc = element

        if child:
            # create child elements from an tuple with optional text node or attributes
            # format: ((name1, text, 'attribute:value'), (name2, text2))
            if isinstance(child, tuple):
                for obj in child:
                    child = self.doc.createElement(obj[0])
                    if len(obj) >= 2:
                        element = self.doc.createTextNode(str(obj[1]))
                        child.appendChild(element)
                    if len(obj) == 3:
                        a = obj[2].split(':')
                        child.setAttribute(a[0], a[1])
                    xml_doc.appendChild(child)
            # create a single text child node
            else:
                element = self.doc.createTextNode(str(child))
                xml_doc.appendChild(element)

        # target element attributes
        if attribute:
            #checking to see if we have a list of attributes
            if '|' in attribute:
                attributes = attribute.split('|')
            else:
                #if not just put this into a list so we have the same data type no matter what
                attributes = [attribute]

            # adding attributes for each item
            for attribute in attributes:
                attribute = attribute.split(':')
                xml_doc.setAttribute(attribute[0], attribute[1])

    def request_xml(self):
        """
        Stringifies request xml for debugging
        """
        return self.doc.toprettyxml()

    def make_request(self, api_uri):
        """ 
        Submits the API request as XML formated string via HTTP POST and parse gateway response.
        This needs to be run after adding some data via 'set'
        """
        request_body = self.doc.toxml('utf-8')

        # checking to see if we have any special params
        if self.special_ssl:
            kwargs = self.special_ssl
            api = httplib.HTTPSConnection(self.api_host, **kwargs)
        else:
            api = httplib.HTTPSConnection(self.api_host)

        api.connect()
        api.putrequest('POST', api_uri, skip_host=True)
        api.putheader('Host', self.api_host)
        api.putheader('Content-type', 'text/xml; charset="utf-8"')
        api.putheader("Content-length", str(len(request_body)))
        api.putheader('User-Agent', 'yourdomain.net')
        api.endheaders()
        api.send(request_body)

        resp = api.getresponse()
        resp_data = resp.read()

        # parse API call response
        if not resp.status == 200:
            raise RequestError('Gateway returned %i status' % resp.status)

        # parse XML response and return as dict
        try:
            resp_dict = self.parse_xml(resp_data)
        except:
            try:
                resp_dict = self.parse_xml('<?xml version="1.0"?><response>%s</response>' % resp_data)
            except:
                raise RequestError('Could not parse XML into JSON')

        return resp_dict

class SOAPGateway(object):
    pass

class GetGateway(Gateway):
    REQUEST_DICT = {}
    debug = False

    def __init__(self, translations, debug):
        """core GETgateway class"""
        super(GetGateway, self).__init__(set_method=self.set, translations=translations, debug=debug)
        self.debug = debug

    def set(self, key, value):
        """
        Setups request dict for Get
        """
        self.REQUEST_DICT[key] = value

    def unset(self, key):
        """
        Sets up request dict for Get
        """
        try:
            del self.REQUEST_DICT[key]
        except KeyError:
            raise DataValidationError('The key being unset is non-existent in the request dictionary.')

    def query_string(self):
        """
        Build the query string to use later (in get)
        """
        request_query = '?%s' % urllib.urlencode(self.REQUEST_DICT)
        return request_query

    def make_request(self, uri):
        """
        GETs url with params - simple enough... string uri, string params
        """
        try:
            params = self.query_string()
            request = urllib.urlopen('%s%s' % (uri, params))

            return request.read()
        except:
            raise GatewayError('Error making request to gateway')

class PostGateway(Gateway):
    REQUEST_DICT = {}
    debug = False

    def __init__(self, translations, debug):
        """core POSTgateway class"""
        super(PostGateway, self).__init__(set_method=self.set, translations=translations, debug=debug)
        self.debug = debug

    def set(self, key, value):
        """
        Setups request dict for Post
        """
        self.REQUEST_DICT[key] = value

    def params(self):
        """
        returns arguments that are going to be sent to the POST (here for debugging)
        """
        return urllib.urlencode(self.REQUEST_DICT)

    def make_request(self, uri):
        """
        POSTs to url with params (self.REQUEST_DICT) - simple enough... string uri, dict params
        """
        try:
            request = urllib.urlopen(uri, self.params())
            return request.read()
        except:
            raise GatewayError('Error making request to gateway')

########NEW FILE########
__FILENAME__ = cc
from paython.exceptions import DataValidationError

from paython.lib.utils import get_card_type, get_card_exp, is_valid_exp, is_valid_cc, is_valid_cvv

class CreditCard(object):
    """
    generic CreditCard object
    """
    def __init__(self, number, exp_mo, exp_yr, first_name=None, last_name=None, full_name=None, cvv=None, cc_type=None, strict=False):
        """
        sets credit card info
        """
        if full_name:
            self.full_name = full_name
        else:
            self.first_name = first_name
            self.last_name = last_name
            self.full_name = "{0.first_name} {0.last_name}".format(self)

        #everything else
        self.number = number
        self.exp_month = exp_mo
        self.exp_year = exp_yr
        self.exp_date = get_card_exp(self.exp_month, self.exp_year)
        self.card_type = get_card_type(self.number)

        self.verification_value = cvv if cvv else None

        self.strict = strict

    def __repr__(self):
        """
        string repr for debugging
        """
        if hasattr(self, '_exp_yr_style') and self._exp_yr_style:
            return u'<CreditCard -- {0.full_name}, {0.card_type}, {0.safe_num}, expires: {0.exp_date} --extra: {_exp_yr_style}>'.format(self, _exp_yr_style=self.exp_year[2:])
        else:
            return u'<CreditCard -- {0.full_name}, {0.card_type}, {0.safe_num}, expires: {0.exp_date}>'.format(self)

    @property
    def safe_num(self):
        """
        outputs the card number with *'s, only exposing last four digits of card number
        """
        card_length = len(self.number)
        stars = '*' * (card_length - 4)
        return '{0}{1}'.format(stars, self.number[-4:])

    def is_valid(self):
        """
        boolean to see if a card is valid
        """
        try:
            self.validate()
        except DataValidationError:
            return False
        else:
            return True

    def validate(self):
        """
        validates expiration date & card number using util functions
        """
        if not is_valid_cc(self.number):
            raise DataValidationError('The credit card number provided does not pass luhn validation')

        if not is_valid_exp(self.exp_month, self.exp_year):
            raise DataValidationError('The credit card expiration provided is not in the future')

        if self.strict:
            if not is_valid_cvv(self.verification_value):
                raise DataValidationError('The credit card cvv is not valid')

        return True

########NEW FILE########
__FILENAME__ = utils
import re
import calendar
import xml

from datetime import datetime
from suds.sax.text import Text as sudTypeText # for the 'parse_soap()' string type

from paython.exceptions import GatewayError

CARD_TYPES = {
    'visa': r'4\d{12}(\d{3})?$',
    'amex': r'37\d{13}$',
    'mc': r'5[1-5]\d{14}$',
    'discover': r'6011\d{12}',
    'diners': r'(30[0-5]\d{11}|(36|38)\d{12})$'
}

def parse_xml(element):
    """
    Parse an XML API Response xml.dom.minidom.Document. Returns the result as dict or string
    depending on amount of child elements. Returns None in case of empty elements
    """
    if not isinstance(element, xml.dom.minidom.Node):
        try:
            element = xml.dom.minidom.parseString(element)
        except xml.parsers.expat.ExpatError as e:
            raise GatewayError("Error parsing XML: {0}".format(e))

    # return DOM element with single text element as string
    if len(element.childNodes) == 1:
        child = element.childNodes[0]
        if child.nodeName == '#text':
            return child.nodeValue.strip()

    # parse the child elements and return as dict
    root = {}

    for e in element.childNodes:
        t = {}

        if e.nodeName == '#text':
            if not e.nodeValue.strip(): continue

        if e.attributes:
            t['attribute'] = {}
            for attribute in e.attributes.values():
                t['attribute'][attribute.nodeName] = attribute.childNodes[0].nodeValue

        if e.childNodes:
            if t.has_key('attribute'):
                t['meta'] = parse_xml(e)
            else:
                if len(e.childNodes) == 1:
                    if e.firstChild.nodeType == xml.dom.Node.CDATA_SECTION_NODE:
                        t = e.firstChild.wholeText
                    else:
                        t = parse_xml(e)
                else:
                    t = parse_xml(e)

        if not t:
            t = e.nodeValue

        if root.has_key(e.nodeName):
            if not isinstance(root[e.nodeName], list):
                tmp = []
                tmp.append(root[e.nodeName])
            tmp.append(t)
            t = tmp

        root[e.nodeName] = t

    return root

def is_valid_cc(cc):
    """
    Uses Luhn Algorithm for credit card number validation. http://en.wikipedia.org/wiki/Luhn_algorithm
    """
    try:
        num = map(int, cc)
    except ValueError:
        return False
    else:
        return not sum(num[::-2] + map(lambda d: sum(divmod(d * 2, 10)), num[-2::-2])) % 10

def is_valid_exp(month, year):
    """
    Uses datetime to compare string of card expiration to the time right now
    """
    month = int(month)
    year = int(year)

    exp_date_obj = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, 59)
    return datetime.now() < exp_date_obj

def is_valid_cvv(cc_cvv):
    """
    Simple regex for card validator length & type.
    """
    return re.match(r'^[\d+]{3,4}$', cc_cvv)

def get_card_type(cc):
    """
    Gets card type by using card number
    """
    for k, v in CARD_TYPES.items():
        if re.match(v, cc):
            return k

def get_card_exp(month, year):
    """
    Gets the expiration date by concatenating strings
    """
    return "{0}/{1}".format(month, year)

def is_valid_email(email):
    """
    Based on "The Perfect E-Mail Regex" : http://fightingforalostcause.net/misc/2006/compare-email-regex.php
    """
    pat = '^([\w\!\#$\%\&\'\*\+\-\/\=\?\^\`{\|\}\~]+\.)*[\w\!\#$\%\&\'\*\+\-\/\=\?\^\`{\|\}\~]+@((((([a-z0-9]{1}[a-z0-9\-]{0,62}[a-z0-9]{1})|[a-z])\.)+[a-z]{2,6})|(\d{1,3}\.){3}\d{1,3}(\:\d{1,5})?)$'
    return re.search(pat, email, re.IGNORECASE)

def transform_keys():
    raise NotImplemented

########NEW FILE########
__FILENAME__ = test_credit_card
from datetime import datetime
from dateutil.relativedelta import relativedelta

from paython.lib.cc import CreditCard
from paython.exceptions import DataValidationError

from nose.tools import assert_equals, assert_false, assert_true, with_setup, raises

# Initialize globals here so that pyflakes doesn't freak out about them.
TEST_CARDS = {}
NEXT_YEAR = None
LAST_YEAR = None

def setup():
    """setting up the test"""

    global TEST_CARDS
    global NEXT_YEAR
    global LAST_YEAR

    TEST_CARDS = {
            'visa': "4111111111111111",
            'amex': "378282246310005",
            'mc': "5555555555554444",
            'discover': "6011111111111117",
            'diners': "30569309025904"
    }

    # We are using relative delta so that tests will always pass
    # no matter what the date is. This fixed three failing tests
    # that were hard-wired to 2012.
    NEXT_YEAR = datetime.now().date() + relativedelta(years=1)
    LAST_YEAR = NEXT_YEAR - relativedelta(years=2)


def teardown():
    """teardowning the test"""
    pass

@with_setup(setup, teardown)
@raises(DataValidationError)
def test_invalid():
    """test if a credit card number is luhn invalid"""
    credit_card = CreditCard(
            number = "411111111111111a", # invalid credit card
            exp_mo = NEXT_YEAR.strftime('%m'),
            exp_yr = NEXT_YEAR.strftime('%Y'),
            first_name = "John",
            last_name = "Doe",
            cvv = "123",
            strict = False
    )

    # safe check for luhn valid
    assert_false(credit_card.is_valid())

    # checking if the exception fires
    credit_card.validate()

@with_setup(setup, teardown)
@raises(DataValidationError)
def test_expired_credit_card():
    """test if a credit card number is expired"""
    credit_card = CreditCard(
            number = "4111111111111111",
            exp_mo = LAST_YEAR.strftime('%m'),
            exp_yr = LAST_YEAR.strftime('%Y'),
            first_name = "John",
            last_name = "Doe",
            cvv = "123",
            strict = False
    )

    # safe check for luhn valid
    assert_false(credit_card.is_valid())

    # checking if the exception fires
    credit_card.validate()

@with_setup(setup, teardown)
@raises(DataValidationError)
def test_invalid_cvv():
    """test if a credit card number has an invalid cvv"""
    credit_card = CreditCard(
            number = "4111111111111111",
            exp_mo = NEXT_YEAR.strftime('%m'),
            exp_yr = NEXT_YEAR.strftime('%Y'),
            first_name = "John",
            last_name = "Doe",
            cvv = "1", # invalid cvv
            strict = True
    )

    # safe check for luhn valid
    assert_false(credit_card.is_valid())

    # checking if the exception fires
    credit_card.validate()

@with_setup(setup, teardown)
def test_valid():
    """test if a credit card number is luhn valid"""
    for test_cc_type, test_cc_num in TEST_CARDS.items():
        # create a credit card object
        credit_card = CreditCard(
                number = test_cc_num, # valid credit card
                exp_mo = NEXT_YEAR.strftime('%m'),
                exp_yr = NEXT_YEAR.strftime('%Y'),
                first_name = "John",
                last_name = "Doe",
                cvv = "123",
                strict = False
        )

        # safe check
        assert_true(credit_card.is_valid())

        # check the type
        assert_equals(test_cc_type, credit_card.card_type)

@with_setup(setup, teardown)
def test_to_string():
    """test if a credit card outputs the right to str value"""
    credit_card = CreditCard(
            number = '4111111111111111',
            exp_mo = NEXT_YEAR.strftime('%m'),
            exp_yr = NEXT_YEAR.strftime('%Y'),
            first_name = 'John',
            last_name = 'Doe',
            cvv = '911',
            strict = False
    )

    # safe check
    assert_true(credit_card.is_valid())

    # checking if our str() method (or repr()) is ok
    final_str = '<CreditCard -- John Doe, visa, ************1111, expires: %s/%s>' % (NEXT_YEAR.strftime('%m'), NEXT_YEAR.strftime('%Y'))
    assert_equals(str(credit_card), final_str)

@with_setup(setup, teardown)
def test_full_name():
    """testing full_name support"""
    credit_card = CreditCard(
            number = '4111111111111111',
            exp_mo = NEXT_YEAR.strftime('%m'),
            exp_yr = NEXT_YEAR.strftime('%Y'),
            full_name = 'John Doe',
            cvv = '911',
            strict = False
    )

    # safe check
    assert_true(credit_card.is_valid())

    # checking if our str() method (or repr()) is ok
    final_str = '<CreditCard -- John Doe, visa, ************1111, expires: %s/%s>' % (NEXT_YEAR.strftime('%m'), NEXT_YEAR.strftime('%Y'))
    assert_equals(str(credit_card), final_str)

@with_setup(setup, teardown)
def test_exp_styled():
    """testing support for 2 digits expiracy year"""
    credit_card = CreditCard(
            number = '4111111111111111',
            exp_mo = NEXT_YEAR.strftime('%m'),
            exp_yr = NEXT_YEAR.strftime('%Y'),
            full_name = 'John Doe',
            cvv = '911',
            strict = False
    )

    credit_card._exp_yr_style = True

    # safe check
    assert_true(credit_card.is_valid())

    # checking if our str() method (or repr()) is ok
    final_str = '<CreditCard -- John Doe, visa, ************1111, expires: %s/%s --extra: %s>' % (NEXT_YEAR.strftime('%m'), NEXT_YEAR.strftime('%Y'), NEXT_YEAR.strftime('%y'))
    assert_equals(str(credit_card), final_str)

########NEW FILE########
__FILENAME__ = test_example
from nose.tools import assert_equals, with_setup

def setup():
    """setting up the test"""
    # TODO here we add the useful global vars
    global global_var
    global_var = "is this a global?"

def teardown():
    """teardowning the test"""
    # TODO add something to do when exiting
    pass

@with_setup(setup, teardown)
def test():
    """testing Authorize.Net"""
    # TODO write the actual test
    #assert_equals(False, "we're fucked, but the global var we set == {0}".format(global_var))
    pass

########NEW FILE########
__FILENAME__ = test_exceptions
"""test_exceptions.py: testing exceptions just raising them and testing them"""
from paython.exceptions import DataValidationError, MissingDataError, GatewayError, RequestError

from nose.tools import assert_equals, raises

@raises(DataValidationError)
def test_data_validation_error():
    """Testing DataValidationError"""
    try:
        raise DataValidationError("Your data is incorrect fool!")
    except DataValidationError as error:
        assert_equals("'Your data is incorrect fool!'", str(error))

    raise DataValidationError("Your data is incorrect fool!")

@raises(MissingDataError)
def test_missing_data_error():
    """Testing MissingDataError"""
    try:
        raise MissingDataError("Your data is incomplete fool!")
    except MissingDataError as error:
        assert_equals("'Your data is incomplete fool!'", str(error))

    raise MissingDataError("Your data is incomplete fool!")

@raises(GatewayError)
def test_gateway_error():
    """Testing GatewayError"""
    try:
        raise GatewayError("Your gateway sucks fool!")
    except GatewayError as error:
        assert_equals("'Your gateway sucks fool!'", str(error))

    raise GatewayError("Your gateway sucks fool!")

@raises(RequestError)
def test_request_error():
    """Testing RequestError"""
    try:
        raise RequestError("Your request is wrong fool!")
    except RequestError as error:
        assert_equals("'Your request is wrong fool!'", str(error))

    raise RequestError("Your request is wrong fool!")

########NEW FILE########
__FILENAME__ = test_utils
from paython.exceptions import GatewayError
from paython.lib.utils import parse_xml, is_valid_email

from nose.tools import assert_equals, raises

@raises(GatewayError)
def test_parse_xml():
    """Testing our parse xml util"""
    result = parse_xml("<lol test=\"woot\">waaa<inside>heh</inside></lol>")
    expected = {u'lol': {'attribute': {u'test': u'woot'},
                      'meta': {'#text': u'waaa', u'inside': u'heh'}}}

    assert_equals(result, expected)

    parse_xml("<lol>testing invalid xml<lol>")


def test_cdata_parse_xml():
    """testing when we pass cdata to the xml"""
    result = parse_xml("<lol><inside><![CDATA[???]]></inside></lol>")
    expected = {u'lol': {u'inside': u'???'}}

    assert_equals(result, expected)

def test_multiple_child_nodes():
    """testing multiple child nodes"""
    result = parse_xml("<lol><first>text 1</first><second>text 2</second></lol>")
    expected = {u'lol': {u'first': u'text 1', u'second': u'text 2'}}

    assert_equals(result, expected)

def test_append_to_root():
    """testing append to root entity"""
    result = parse_xml("<lol><first>text 1</first><first>text 2</first></lol>")
    expected = {u'lol': {u'first': [u'text 1', u'text 2']}}

    assert_equals(result, expected)

def test_valid_email():
    """testing our email validation"""
    assert_equals(is_valid_email("lol@lol.com") is None, False)

########NEW FILE########
