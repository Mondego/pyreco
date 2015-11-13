__FILENAME__ = exceptions
# coding=utf-8
"""
Various PayPal API related exceptions.
"""

class PayPalError(Exception):
    """
    Used to denote some kind of generic error. This does not include errors
    returned from PayPal API responses. Those are handled by the more
    specific exception classes below.
    """
    def __init__(self, message, error_code=None):
        self.response = message
        self.error_code = error_code

    def __str__(self):
        if self.error_code:
            return "%s (Error Code: %s)" % (repr(self.message), self.error_code)
        else:
            return repr(self.message)


class PayPalConfigError(PayPalError):
    """
    Raised when a configuration problem arises.
    """
    pass


class PayPalAPIResponseError(PayPalError):
    """
    Raised when there is an error coming back with a PayPal NVP API response.
    
    Pipe the error message from the API to the exception, along with
    the error code.
    """
    def __init__(self, response):
        self.response = response
        self.error_code = int(response.L_ERRORCODE0)
        self.message = response.L_LONGMESSAGE0
        self.short_message = response.L_SHORTMESSAGE0
        self.correlation_id = response.CORRELATIONID
########NEW FILE########
__FILENAME__ = interface
# coding=utf-8
"""
The end developer will do most of their work with the PayPalInterface class found
in this module. Configuration, querying, and manipulation can all be done
with it.
"""

import types
import socket
import urllib
import urllib2
from urlparse import urlsplit, urlunsplit

from settings import PayPalConfig
from response import PayPalResponse
from exceptions import PayPalError, PayPalAPIResponseError
   
class PayPalInterface(object):
    """
    The end developers will do 95% of their work through this class. API
    queries, configuration, etc, all go through here. See the __init__ method
    for config related details.
    """
    def __init__(self , config=None, **kwargs):
        """
        Constructor, which passes all config directives to the config class
        via kwargs. For example:
        
            paypal = PayPalInterface(API_USERNAME='somevalue')
            
        Optionally, you may pass a 'config' kwarg to provide your own
        PayPalConfig object.
        """
        if config:
            # User provided their own PayPalConfig object.
            self.config = config
        else:
            # Take the kwargs and stuff them in a new PayPalConfig object.
            self.config = PayPalConfig(**kwargs)
        
    def _encode_utf8(self, **kwargs):
        """
        UTF8 encodes all of the NVP values.
        """
        unencoded_pairs = kwargs
        for i in unencoded_pairs.keys():
            if isinstance(unencoded_pairs[i], types.UnicodeType):
                unencoded_pairs[i] = unencoded_pairs[i].encode('utf-8')
        return unencoded_pairs
    
    def _check_required(self, requires, **kwargs):
        """
        Checks kwargs for the values specified in 'requires', which is a tuple
        of strings. These strings are the NVP names of the required values.
        """
        for req in requires:
            # PayPal api is never mixed-case.
            if req.lower() not in kwargs and req.upper() not in kwargs:
                raise PayPalError('missing required : %s' % req)
        
    def _call(self, method, **kwargs):
        """
        Wrapper method for executing all API commands over HTTP. This method is
        further used to implement wrapper methods listed here:
    
        https://www.x.com/docs/DOC-1374
    
        ``method`` must be a supported NVP method listed at the above address.
    
        ``kwargs`` will be a hash of
        """
        socket.setdefaulttimeout(self.config.HTTP_TIMEOUT)
    
        url_values = {
            'METHOD': method,
            'VERSION': self.config.API_VERSION
        }
    
        headers = {}
        if(self.config.API_AUTHENTICATION_MODE == "3TOKEN"):
            # headers['X-PAYPAL-SECURITY-USERID'] = API_USERNAME
            # headers['X-PAYPAL-SECURITY-PASSWORD'] = API_PASSWORD
            # headers['X-PAYPAL-SECURITY-SIGNATURE'] = API_SIGNATURE
            url_values['USER'] = self.config.API_USERNAME
            url_values['PWD'] = self.config.API_PASSWORD
            url_values['SIGNATURE'] = self.config.API_SIGNATURE
        elif(self.config.API_AUTHENTICATION_MODE == "UNIPAY"):
            # headers['X-PAYPAL-SECURITY-SUBJECT'] = SUBJECT
            url_values['SUBJECT'] = self.config.SUBJECT
        # headers['X-PAYPAL-REQUEST-DATA-FORMAT'] = 'NV'
        # headers['X-PAYPAL-RESPONSE-DATA-FORMAT'] = 'NV'
        # print(headers)

        for k,v in kwargs.iteritems():
            url_values[k.upper()] = v
        
        # When in DEBUG level 2 or greater, print out the NVP pairs.
        if self.config.DEBUG_LEVEL >= 2:
            k = url_values.keys()
            k.sort()
            for i in k:
               print " %-20s : %s" % (i , url_values[i])

        u2 = self._encode_utf8(**url_values)

        data = urllib.urlencode(u2)
        req = urllib2.Request(self.config.API_ENDPOINT, data, headers)
        response = PayPalResponse(urllib2.urlopen(req).read(), self.config)

        if self.config.DEBUG_LEVEL >= 1:
            print " %-20s : %s" % ("ENDPOINT", self.config.API_ENDPOINT)
    
        if not response.success:
            if self.config.DEBUG_LEVEL >= 1:
                print response
            raise PayPalAPIResponseError(response)

        return response

    def address_verify(self, email, street, zip):
        """Shortcut for the AddressVerify method.
    
        ``email``::
            Email address of a PayPal member to verify.
            Maximum string length: 255 single-byte characters
            Input mask: ?@?.??
        ``street``::
            First line of the billing or shipping postal address to verify.
    
            To pass verification, the value of Street must match the first three
            single-byte characters of a postal address on file for the PayPal member.
    
            Maximum string length: 35 single-byte characters.
            Alphanumeric plus - , . ‘ # \
            Whitespace and case of input value are ignored.
        ``zip``::
            Postal code to verify.
    
            To pass verification, the value of Zip mustmatch the first five
            single-byte characters of the postal code of the verified postal
            address for the verified PayPal member.
    
            Maximumstring length: 16 single-byte characters.
            Whitespace and case of input value are ignored.
        """
        args = locals()
        del args['self']
        return self._call('AddressVerify', **args)

    def do_authorization(self, transactionid, amt):
        """Shortcut for the DoAuthorization method.
    
        Use the TRANSACTIONID from DoExpressCheckoutPayment for the
        ``transactionid``. The latest version of the API does not support the
        creation of an Order from `DoDirectPayment`.
    
        The `amt` should be the same as passed to `DoExpressCheckoutPayment`.
    
        Flow for a payment involving a `DoAuthorization` call::
    
             1. One or many calls to `SetExpressCheckout` with pertinent order
                details, returns `TOKEN`
             1. `DoExpressCheckoutPayment` with `TOKEN`, `PAYMENTACTION` set to
                Order, `AMT` set to the amount of the transaction, returns
                `TRANSACTIONID`
             1. `DoAuthorization` with `TRANSACTIONID` and `AMT` set to the
                amount of the transaction.
             1. `DoCapture` with the `AUTHORIZATIONID` (the `TRANSACTIONID`
                returned by `DoAuthorization`)
    
        """
        args = locals()
        del args['self']
        return self._call('DoAuthorization', **args)

    def do_capture(self, authorizationid, amt, completetype='Complete', **kwargs):
        """Shortcut for the DoCapture method.
    
        Use the TRANSACTIONID from DoAuthorization, DoDirectPayment or
        DoExpressCheckoutPayment for the ``authorizationid``.
    
        The `amt` should be the same as the authorized transaction.
        """
        kwargs.update(locals())
        del kwargs['self']
        return self._call('DoCapture', **kwargs)

    def do_direct_payment(self, paymentaction="Sale", **kwargs):
        """Shortcut for the DoDirectPayment method.
    
        ``paymentaction`` could be 'Authorization' or 'Sale'
    
        To issue a Sale immediately::
    
            charge = {
                'amt': '10.00',
                'creditcardtype': 'Visa',
                'acct': '4812177017895760',
                'expdate': '012010',
                'cvv2': '962',
                'firstname': 'John',
                'lastname': 'Doe',
                'street': '1 Main St',
                'city': 'San Jose',
                'state': 'CA',
                'zip': '95131',
                'countrycode': 'US',
                'currencycode': 'USD',
            }
            direct_payment("Sale", **charge)
    
        Or, since "Sale" is the default:
    
            direct_payment(**charge)
    
        To issue an Authorization, simply pass "Authorization" instead of "Sale".
    
        You may also explicitly set ``paymentaction`` as a keyword argument:
    
            ...
            direct_payment(paymentaction="Sale", **charge)
        """
        kwargs.update(locals())
        del kwargs['self']
        return self._call('DoDirectPayment', **kwargs)

    def do_void(self, authorizationid, note=''):
        """Shortcut for the DoVoid method.
    
        Use the TRANSACTIONID from DoAuthorization, DoDirectPayment or
        DoExpressCheckoutPayment for the ``authorizationid``.
        """
        args = locals()
        del args['self']
        return self._call('DoVoid', **args)

    def get_express_checkout_details(self, token):
        """Shortcut for the GetExpressCheckoutDetails method.
        """
        return self._call('GetExpressCheckoutDetails', token=token)
        
    def get_transaction_details(self, transactionid):
        """Shortcut for the GetTransactionDetails method.
    
        Use the TRANSACTIONID from DoAuthorization, DoDirectPayment or
        DoExpressCheckoutPayment for the ``transactionid``.
        """
        args = locals()
        del args['self']
        return self._call('GetTransactionDetails', **args)

    def set_express_checkout_legacy(self, amt, returnurl, cancelurl, token='', 
                                    **kwargs ):
        """Shortcut for the SetExpressCheckout method.
        """
        kwargs.update(locals())
        del kwargs['self']
        return self._call('SetExpressCheckout', **kwargs)

    def set_express_checkout(self, token='', **kwargs):
        """Shortcut for the SetExpressCheckout method.
            JV did not like the original method. found it limiting.
        """
        kwargs.update(locals())
        del kwargs['self']
        self._check_required(('amt',), **kwargs)
        return self._call('SetExpressCheckout', **kwargs)

    def do_express_checkout_payment(self, token, **kwargs):
        """Shortcut for the DoExpressCheckoutPayment method.
        
            Required
                *METHOD
                *TOKEN
                PAYMENTACTION
                PAYERID
                AMT
                
            Optional
                RETURNFMFDETAILS
                GIFTMESSAGE
                GIFTRECEIPTENABLE
                GIFTWRAPNAME
                GIFTWRAPAMOUNT
                BUYERMARKETINGEMAIL
                SURVEYQUESTION
                SURVEYCHOICESELECTED
                CURRENCYCODE
                ITEMAMT
                SHIPPINGAMT
                INSURANCEAMT
                HANDLINGAMT
                TAXAMT

            Optional + USEFUL
                INVNUM - invoice number
                
        """
        kwargs.update(locals())
        del kwargs['self']
        self._check_required(('paymentaction', 'payerid'), **kwargs)
        return self._call('DoExpressCheckoutPayment', **kwargs)
        
    def generate_express_checkout_redirect_url(self, token):
        """Submit token, get redirect url for client."""
        url_vars = (self.config.PAYPAL_URL_BASE, token)
        return "%s?cmd=_express-checkout&token=%s" % url_vars
    
    def generate_cart_upload_redirect_url(self, **kwargs):
        """https://www.sandbox.paypal.com/webscr 
            ?cmd=_cart
            &upload=1
        """
        required_vals = ('business', 'item_name_1', 'amount_1', 'quantity_1')
        self._check_required(required_vals, **kwargs)
        url = "%s?cmd=_cart&upload=1" % self.config.PAYPAL_URL_BASE
        additional = self._encode_utf8(**kwargs)
        additional = urllib.urlencode(additional)
        return url + "&" + additional

########NEW FILE########
__FILENAME__ = response
# coding=utf-8
"""
PayPalResponse parsing and processing.
"""

from urlparse import parse_qs

import exceptions 

class PayPalResponse(object):
    """
    Parse and prepare the reponse from PayPal's API. Acts as somewhat of a
    glorified dictionary for API responses.
    
    NOTE: Don't access self.raw directly. Just do something like
    PayPalResponse.someattr, going through PayPalResponse.__getattr__().
    """
    def __init__(self, query_string, config):
        """
        query_string is the response from the API, in NVP format. This is
        parseable by urlparse.parse_qs(), which sticks it into the self.raw
        dict for retrieval by the user.
        """
        # A dict of NVP values. Don't access this directly, use
        # PayPalResponse.attribname instead. See self.__getattr__().
        self.raw = parse_qs(query_string)
        self.config = config

    def __str__(self):
        return str(self.raw)

    def __getattr__(self, key):
        """
        Handles the retrieval of attributes that don't exist on the object
        already. This is used to get API response values.
        """
        # PayPal response names are always uppercase.
        key = key.upper()
        try:
            value = self.raw[key]
            if len(value) == 1:
                return value[0]
            return value
        except KeyError:
            if self.config.KEY_ERROR:
                raise AttributeError(self)
            else:
                return None
                
    def success(self):
        """
        Checks for the presence of errors in the response. Returns True if
        all is well, False otherwise.
        """
        return self.ack.upper() in (self.config.ACK_SUCCESS, 
                                    self.config.ACK_SUCCESS_WITH_WARNING)
    success = property(success)
########NEW FILE########
__FILENAME__ = settings
# coding=utf-8
"""
This module contains config objects needed by paypal.interface.PayPalInterface.
Most of this is transparent to the end developer, as the PayPalConfig object
is instantiated by the PayPalInterface object.
"""

from exceptions import PayPalConfigError, PayPalError

class PayPalConfig(object):
    """
    The PayPalConfig object is used to allow the developer to perform API
    queries with any number of different accounts or configurations. This
    is done by instantiating paypal.interface.PayPalInterface, passing config
    directives as keyword args.
    """
    # Used to validate correct values for certain config directives.
    _valid_= {
        'API_ENVIRONMENT' : ['sandbox','production'],
        'API_AUTHENTICATION_MODE' : ['3TOKEN','CERTIFICATE'],
    }

    # Various API servers.
    _API_ENDPOINTS= {
        # In most cases, you want 3-Token. There's also Certificate-based
        # authentication, which uses different servers, but that's not
        # implemented.
        '3TOKEN': {
            'sandbox' : 'https://api-3t.sandbox.paypal.com/nvp',
            'production' : 'https://api-3t.paypal.com/nvp',
        }
    }

    _PAYPAL_URL_BASE= {
        'sandbox' : 'https://www.sandbox.paypal.com/webscr',
        'production' : 'https://www.paypal.com/webscr',
    }

    API_VERSION = "60.0"

    # Defaults. Used in the absence of user-specified values.
    API_ENVIRONMENT = 'sandbox'
    API_AUTHENTICATION_MODE = '3TOKEN'

    # 3TOKEN credentials
    API_USERNAME = None
    API_PASSWORD = None
    API_SIGNATURE = None

    # API Endpoints are just API server addresses.
    API_ENDPOINT = None
    PAYPAL_URL_BASE = None
    
    # UNIPAY credentials
    UNIPAY_SUBJECT = None
    
    ACK_SUCCESS = "SUCCESS"
    ACK_SUCCESS_WITH_WARNING = "SUCCESSWITHWARNING"
    
    # 0 being no debugging, 1 being some, 2 being lots.
    DEBUG_LEVEL = 0

    # In seconds. Depending on your setup, this may need to be higher.
    HTTP_TIMEOUT = 15
    
    RESPONSE_KEYERROR = "AttributeError"
    
    # When True, return an AttributeError when the user tries to get an
    # attribute on the response that does not exist. If False or None,
    # return None for non-existant attribs.
    KEY_ERROR = True

    def __init__(self, **kwargs):
        """
        PayPalConfig constructor. **kwargs catches all of the user-specified
        config directives at time of instantiation. It is fine to set these
        values post-instantiation, too.
        
        Some basic validation for a few values is performed below, and defaults
        are applied for certain directives in the absence of
        user-provided values.
        """
        if 'API_ENVIRONMENT' not in kwargs:
            kwargs['API_ENVIRONMENT']= self.API_ENVIRONMENT
        # Make sure the environment is one of the acceptable values.
        if kwargs['API_ENVIRONMENT'] not in self._valid_['API_ENVIRONMENT']:
            raise PayPalConfigError('Invalid API_ENVIRONMENT')
        self.API_ENVIRONMENT = kwargs['API_ENVIRONMENT']

        if 'API_AUTHENTICATION_MODE' not in kwargs:
            kwargs['API_AUTHENTICATION_MODE']= self.API_AUTHENTICATION_MODE
        # Make sure the auth mode is one of the known/implemented methods.
        if kwargs['API_AUTHENTICATION_MODE'] not in self._valid_['API_AUTHENTICATION_MODE']:
            raise PayPalConfigError("Not a supported auth mode. Use one of: %s" % \
                           ", ".join(self._valid_['API_AUTHENTICATION_MODE']))
        
        # Set the API endpoints, which is a cheesy way of saying API servers.
        self.API_ENDPOINT= self._API_ENDPOINTS[self.API_AUTHENTICATION_MODE][self.API_ENVIRONMENT]
        self.PAYPAL_URL_BASE= self._PAYPAL_URL_BASE[self.API_ENVIRONMENT]        
        
        # set the 3TOKEN required fields
        if self.API_AUTHENTICATION_MODE == '3TOKEN':
            for arg in ('API_USERNAME','API_PASSWORD','API_SIGNATURE'):
                if arg not in kwargs:
                    raise PayPalConfigError('Missing in PayPalConfig: %s ' % arg)
                setattr(self, arg, kwargs[arg])
                
        for arg in ('HTTP_TIMEOUT' , 'DEBUG_LEVEL' , 'RESPONSE_KEYERROR'):
            if arg in kwargs:
                setattr(self, arg, kwargs[arg])
########NEW FILE########
__FILENAME__ = api_details_blank
"""
This file contains your PayPal test account credentials. If you are just
getting started, you'll want to copy api_details_blank.py to api_details.py,
and substitute the placeholders below with your PayPal test account details.
"""
from paypal import PayPalConfig

# Enter your test account's API details here. You'll need the 3-token
# credentials, not the certificate stuff.
CONFIG = PayPalConfig(API_USERNAME = "xxx_xxx_apix.xxx.com",
                      API_PASSWORD = "xxxxxxxxxx",
                      API_SIGNATURE = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                      DEBUG_LEVEL=0)

"""
The following values may be found by visiting https://developer.paypal.com/,
clicking on the 'Test Accounts' navbar link in the sandbox, and looking at
the accounts listed there. You'll need a business and a personal account
created to run these tests.
"""
# The email address of your personal test account. This is typically the
# customer for these tests.
EMAIL_PERSONAL = 'custX_xxxxxxxxxx_per@xxxxxxxx.com'
# If you view the details of your personal account, you'll see credit card
# details. Enter the credit card number from there.
VISA_ACCOUNT_NO = 'xxxxxxxxxxxxxxxx'
# And the expiration date in the form of MMYYYY. Note that there are no slashes,
# and single-digit month numbers have a leading 0 (IE: 03 for march).
VISA_EXPIRATION = 'mmyyyy'
########NEW FILE########
__FILENAME__ = interface_factory
"""
This module creates PayPalInterface objects for each of the unit test
modules to use. We create a new one for each unittest module to reduce any
chance of tainting tests by all of them using the same interface. IE: Values
getting modified.

See get_interface_obj() below, as well as the README in this tests directory.
"""
import sys
import os

# The unit tests import this module, so we'll do the path modification to use
# this paypal project instead of any potential globally installed ones.
project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not project_root_dir in sys.path:
    sys.path.insert(0, project_root_dir)

from paypal import PayPalInterface

try:
    import api_details
except ImportError:
    print """
    ERROR: No api_details.py file exists in your paypal/tests directory. Please 
    copy api_details_blank.py to api_details.py and modify the values to your 
    own API developer _test_ credentials.
    
    If you don't already have test credentials, please visit:
    
        https://developer.paypal.com
    
    """
    sys.exit(1)

def get_interface_obj():
    """
    Use this function to get a PayPalInterface object with your test API
    credentials (as specified in api_details.py). Create new interfaces for
    each unit test module to avoid potential variable pollution. 
    """
    return PayPalInterface(config=api_details.CONFIG)

########NEW FILE########
__FILENAME__ = runner
#!/usr/bin/env python
"""
Execute this module to run all of the unit tests for paypal-python. If you
haven't already, read README and act accordingly or all of these tests
will fail.
"""
import os
import sys
# Prepare the path to use the included paypal module instead of the system
# one (if applicable).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
import t_direct_payment
import t_express_checkout

# A list of the modules under the tests package that should be ran.
test_modules = [t_direct_payment, t_express_checkout]

# Fire off all of the tests.
for mod in test_modules:
    suite = unittest.TestLoader().loadTestsFromModule(mod)
    unittest.TextTestRunner(verbosity=1).run(suite)
########NEW FILE########
__FILENAME__ = t_direct_payment
# coding=utf-8

import unittest
from paypal import PayPalAPIResponseError
import interface_factory
import api_details

interface = interface_factory.get_interface_obj()

class TestDirectPayment(unittest.TestCase):
    def setUp(self):
        self.credit_card = {
            'amt': '10.00',
            'creditcardtype': 'Visa',
            'acct': api_details.VISA_ACCOUNT_NO,
            'expdate': api_details.VISA_EXPIRATION,
            'cvv2': '123',
            'firstname': 'John',
            'lastname': 'Doe',
            'street': '1313 Mockingbird Lane',
            'city': 'Beverly Hills',
            'state': 'CA',
            'zip': '90110',
            'countrycode': 'US',
            'currencycode': 'USD',
        }

    def test_sale(self):
        sale = interface.do_direct_payment('Sale', **self.credit_card)
        self.assertTrue(sale.success)

        details = interface.get_transaction_details(sale.TRANSACTIONID)
        self.assertTrue(details.success)
        self.assertEqual(details.PAYMENTSTATUS.upper(), 'COMPLETED')
        self.assertEqual(details.REASONCODE.upper(), 'NONE')
        
    def test_exception_handling(self):
        """
        Make sure response exception handling is working as intended by
        forcing some bad values.
        """
        new_details = self.credit_card
        # Set an invalid credit card number.
        new_details['acct'] = '123'
        # Make sure this raises an exception.
        self.assertRaises(PayPalAPIResponseError, interface.do_direct_payment, 
                          'Sale', **new_details)

    def test_abbreviated_sale(self):
        sale = interface.do_direct_payment(**self.credit_card)
        self.assertTrue(sale.success)

        details = interface.get_transaction_details(sale.TRANSACTIONID)
        self.assertTrue(details.success)
        self.assertEqual(details.PAYMENTSTATUS.upper(), 'COMPLETED')
        self.assertEqual(details.REASONCODE.upper(), 'NONE')

    def test_authorize_and_delayed_capture(self):
        # authorize payment
        auth = interface.do_direct_payment('Authorization', **self.credit_card)
        self.assertTrue(auth.success)
        self.assertEqual(auth.AMT, self.credit_card['amt'])

        # capture payment
        captured = interface.do_capture(auth.TRANSACTIONID, auth.AMT)
        self.assertTrue(captured.success)
        self.assertEqual(auth.TRANSACTIONID, captured.PARENTTRANSACTIONID)
        self.assertEqual(captured.PAYMENTSTATUS.upper(), 'COMPLETED')
        self.assertEqual(captured.REASONCODE.upper(), 'NONE')

    def test_authorize_and_void(self):
        # authorize payment
        auth = interface.do_direct_payment('Authorization', **self.credit_card)
        self.assertTrue(auth.success)
        self.assertEqual(auth.AMT, self.credit_card['amt'])

        # void payment
        note = 'Voided the authorization.'
        void = interface.do_void(auth.TRANSACTIONID, note)
        self.assertTrue(void.success)
        self.assertEqual(auth.TRANSACTIONID, void.AUTHORIZATIONID)

        details = interface.get_transaction_details(auth.TRANSACTIONID)
        self.assertTrue(details.success)
        self.assertEqual(details.PAYMENTSTATUS.upper(), 'VOIDED')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = t_express_checkout
# coding=utf-8

import unittest
import interface_factory
import api_details

interface = interface_factory.get_interface_obj()

# TODO: implement the paypal account log-in as web-based? somehow implement with a bare-bones python web client so it's programmable?
class TestExpressCheckout(unittest.TestCase):
    def setUp(self):
        self.returnurl = 'http://www.paypal.com'
        self.cancelurl = 'http://www.ebay.com'

    def test_sale(self):
        pass

    def test_authorize_and_delayed_capture(self):
        """
        Tests a four-step checkout process involving the following flow::

            One or more calls to `SetExpressCheckout`.
            --- User goes to PayPal, logs in, and confirms shipping, taxes,
                and total amount. ---
            A call to `GetExpressCheckoutDetails`.
            A call to `DoExpressCheckoutPayment`.
            A call to `DoAuthorization`.
            A call to `DoCapture`.
        """
        setexp = interface.set_express_checkout(amt='10.00', returnurl=self.returnurl, \
                     cancelurl=self.cancelurl, paymentaction='Order', \
                     email=api_details.EMAIL_PERSONAL)
        self.assertTrue(setexp.success)
        # print(setexp)
        # getexp = get_express_checkout_details(token=setexp.token)
        # print(getexp)

    def test_authorize_and_void(self):
        """
        Tests a four-step checkout process involving the following flow::

            One or more calls to `SetExpressCheckout`.
            --- User goes to PayPal, logs in, and confirms shipping, taxes,
                and total amount. ---
            A call to `GetExpressCheckoutDetails`.
            A call to `DoExpressCheckoutPayment`.
            A call to `DoAuthorization`.
            A call to `DoVoid`.
        """
        pass

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
