__FILENAME__ = compat
# -*- coding: utf-8 -*-

"""
pythoncompat, from python-requests.

Copyright (c) 2012 Kenneth Reitz.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""


import sys

# -------
# Pythons
# -------

# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)

#: Python 3.0.x
is_py30 = (is_py3 and _ver[1] == 0)

#: Python 3.1.x
is_py31 = (is_py3 and _ver[1] == 1)

#: Python 3.2.x
is_py32 = (is_py3 and _ver[1] == 2)

#: Python 3.3.x
is_py33 = (is_py3 and _ver[1] == 3)

#: Python 3.4.x
is_py34 = (is_py3 and _ver[1] == 4)

#: Python 2.7.x
is_py27 = (is_py2 and _ver[1] == 7)

#: Python 2.6.x
is_py26 = (is_py2 and _ver[1] == 6)

#: Python 2.5.x
is_py25 = (is_py2 and _ver[1] == 5)

#: Python 2.4.x
is_py24 = (is_py2 and _ver[1] == 4)   # I'm assuming this is not by choice.


# ---------
# Platforms
# ---------


# Syntax sugar.
_ver = sys.version.lower()

is_pypy = ('pypy' in _ver)
is_jython = ('jython' in _ver)
is_ironpython = ('iron' in _ver)

# Assume CPython, if nothing else.
is_cpython = not any((is_pypy, is_jython, is_ironpython))

# Windows-based system.
is_windows = 'win32' in str(sys.platform).lower()

# Standard Linux 2+ system.
is_linux = ('linux' in str(sys.platform).lower())
is_osx = ('darwin' in str(sys.platform).lower())
is_hpux = ('hpux' in str(sys.platform).lower())   # Complete guess.
is_solaris = ('solar==' in str(sys.platform).lower())   # Complete guess.


# ---------
# Specifics
# ---------


if is_py2:
    #noinspection PyUnresolvedReferences,PyCompatibility
    from urllib import quote, unquote, urlencode
    #noinspection PyUnresolvedReferences,PyCompatibility
    from urlparse import urlparse, urlunparse, urljoin, urlsplit
    #noinspection PyUnresolvedReferences,PyCompatibility
    from urllib2 import parse_http_list
    #noinspection PyUnresolvedReferences,PyCompatibility
    import cookielib
    #noinspection PyUnresolvedReferences,PyCompatibility
    from Cookie import Morsel
    #noinspection PyUnresolvedReferences,PyCompatibility
    from StringIO import StringIO

    bytes = str
    #noinspection PyUnresolvedReferences,PyCompatibility
    str = unicode
    #noinspection PyUnresolvedReferences,PyCompatibility,PyUnboundLocalVariable
    basestring = basestring
elif is_py3:
    #noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import urlparse, urlunparse, urljoin, urlsplit, urlencode, quote, unquote
    #noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.request import parse_http_list
    #noinspection PyUnresolvedReferences,PyCompatibility
    from http import cookiejar as cookielib
    #noinspection PyUnresolvedReferences,PyCompatibility
    from http.cookies import Morsel
    #noinspection PyUnresolvedReferences,PyCompatibility
    from io import StringIO

    str = str
    bytes = bytes
    basestring = (str, bytes)

########NEW FILE########
__FILENAME__ = countries
"""
Country Code List: ISO 3166-1993 (E)

http://xml.coverpages.org/country3166.html

A tuple of tuples of country codes and their full names. There are a few helper
functions provided if you'd rather not use the dict directly. Examples provided
in the test_countries.py unit tests.
"""

COUNTRY_TUPLES = (
    ('US', 'United States of America'),
    ('CA', 'Canada'),
    ('AD', 'Andorra'),
    ('AE', 'United Arab Emirates'),
    ('AF', 'Afghanistan'),
    ('AG', 'Antigua & Barbuda'),
    ('AI', 'Anguilla'),
    ('AL', 'Albania'),
    ('AM', 'Armenia'),
    ('AN', 'Netherlands Antilles'),
    ('AO', 'Angola'),
    ('AQ', 'Antarctica'),
    ('AR', 'Argentina'),
    ('AS', 'American Samoa'),
    ('AT', 'Austria'),
    ('AU', 'Australia'),
    ('AW', 'Aruba'),
    ('AZ', 'Azerbaijan'),
    ('BA', 'Bosnia and Herzegovina'),
    ('BB', 'Barbados'),
    ('BD', 'Bangladesh'),
    ('BE', 'Belgium'),
    ('BF', 'Burkina Faso'),
    ('BG', 'Bulgaria'),
    ('BH', 'Bahrain'),
    ('BI', 'Burundi'),
    ('BJ', 'Benin'),
    ('BM', 'Bermuda'),
    ('BN', 'Brunei Darussalam'),
    ('BO', 'Bolivia'),
    ('BR', 'Brazil'),
    ('BS', 'Bahama'),
    ('BT', 'Bhutan'),
    ('BV', 'Bouvet Island'),
    ('BW', 'Botswana'),
    ('BY', 'Belarus'),
    ('BZ', 'Belize'),
    ('CC', 'Cocos (Keeling) Islands'),
    ('CF', 'Central African Republic'),
    ('CG', 'Congo'),
    ('CH', 'Switzerland'),
    ('CI', 'Ivory Coast'),
    ('CK', 'Cook Iislands'),
    ('CL', 'Chile'),
    ('CM', 'Cameroon'),
    ('CN', 'China'),
    ('CO', 'Colombia'),
    ('CR', 'Costa Rica'),
    ('CU', 'Cuba'),
    ('CV', 'Cape Verde'),
    ('CX', 'Christmas Island'),
    ('CY', 'Cyprus'),
    ('CZ', 'Czech Republic'),
    ('DE', 'Germany'),
    ('DJ', 'Djibouti'),
    ('DK', 'Denmark'),
    ('DM', 'Dominica'),
    ('DO', 'Dominican Republic'),
    ('DZ', 'Algeria'),
    ('EC', 'Ecuador'),
    ('EE', 'Estonia'),
    ('EG', 'Egypt'),
    ('EH', 'Western Sahara'),
    ('ER', 'Eritrea'),
    ('ES', 'Spain'),
    ('ET', 'Ethiopia'),
    ('FI', 'Finland'),
    ('FJ', 'Fiji'),
    ('FK', 'Falkland Islands (Malvinas)'),
    ('FM', 'Micronesia'),
    ('FO', 'Faroe Islands'),
    ('FR', 'France'),
    ('FX', 'France, Metropolitan'),
    ('GA', 'Gabon'),
    ('GB', 'United Kingdom (Great Britain)'),
    ('GD', 'Grenada'),
    ('GE', 'Georgia'),
    ('GF', 'French Guiana'),
    ('GH', 'Ghana'),
    ('GI', 'Gibraltar'),
    ('GL', 'Greenland'),
    ('GM', 'Gambia'),
    ('GN', 'Guinea'),
    ('GP', 'Guadeloupe'),
    ('GQ', 'Equatorial Guinea'),
    ('GR', 'Greece'),
    ('GS', 'South Georgia and the South Sandwich Islands'),
    ('GT', 'Guatemala'),
    ('GU', 'Guam'),
    ('GW', 'Guinea-Bissau'),
    ('GY', 'Guyana'),
    ('HK', 'Hong Kong'),
    ('HM', 'Heard & McDonald Islands'),
    ('HN', 'Honduras'),
    ('HR', 'Croatia'),
    ('HT', 'Haiti'),
    ('HU', 'Hungary'),
    ('ID', 'Indonesia'),
    ('IE', 'Ireland'),
    ('IL', 'Israel'),
    ('IN', 'India'),
    ('IO', 'British Indian Ocean Territory'),
    ('IQ', 'Iraq'),
    ('IR', 'Islamic Republic of Iran'),
    ('IS', 'Iceland'),
    ('IT', 'Italy'),
    ('JM', 'Jamaica'),
    ('JO', 'Jordan'),
    ('JP', 'Japan'),
    ('KE', 'Kenya'),
    ('KG', 'Kyrgyzstan'),
    ('KH', 'Cambodia'),
    ('KI', 'Kiribati'),
    ('KM', 'Comoros'),
    ('KN', 'St. Kitts and Nevis'),
    ('KP', 'Korea, Democratic People\'s Republic of'),
    ('KR', 'Korea, Republic of'),
    ('KW', 'Kuwait'),
    ('KY', 'Cayman Islands'),
    ('KZ', 'Kazakhstan'),
    ('LA', 'Lao People\'s Democratic Republic'),
    ('LB', 'Lebanon'),
    ('LC', 'Saint Lucia'),
    ('LI', 'Liechtenstein'),
    ('LK', 'Sri Lanka'),
    ('LR', 'Liberia'),
    ('LS', 'Lesotho'),
    ('LT', 'Lithuania'),
    ('LU', 'Luxembourg'),
    ('LV', 'Latvia'),
    ('LY', 'Libyan Arab Jamahiriya'),
    ('MA', 'Morocco'),
    ('MC', 'Monaco'),
    ('MD', 'Moldova, Republic of'),
    ('MG', 'Madagascar'),
    ('MH', 'Marshall Islands'),
    ('ML', 'Mali'),
    ('MN', 'Mongolia'),
    ('MM', 'Myanmar'),
    ('MO', 'Macau'),
    ('MP', 'Northern Mariana Islands'),
    ('MQ', 'Martinique'),
    ('MR', 'Mauritania'),
    ('MS', 'Monserrat'),
    ('MT', 'Malta'),
    ('MU', 'Mauritius'),
    ('MV', 'Maldives'),
    ('MW', 'Malawi'),
    ('MX', 'Mexico'),
    ('MY', 'Malaysia'),
    ('MZ', 'Mozambique'),
    ('NA', 'Namibia'),
    ('NC', 'New Caledonia'),
    ('NE', 'Niger'),
    ('NF', 'Norfolk Island'),
    ('NG', 'Nigeria'),
    ('NI', 'Nicaragua'),
    ('NL', 'Netherlands'),
    ('NO', 'Norway'),
    ('NP', 'Nepal'),
    ('NR', 'Nauru'),
    ('NU', 'Niue'),
    ('NZ', 'New Zealand'),
    ('OM', 'Oman'),
    ('PA', 'Panama'),
    ('PE', 'Peru'),
    ('PF', 'French Polynesia'),
    ('PG', 'Papua New Guinea'),
    ('PH', 'Philippines'),
    ('PK', 'Pakistan'),
    ('PL', 'Poland'),
    ('PM', 'St. Pierre & Miquelon'),
    ('PN', 'Pitcairn'),
    ('PR', 'Puerto Rico'),
    ('PT', 'Portugal'),
    ('PW', 'Palau'),
    ('PY', 'Paraguay'),
    ('QA', 'Qatar'),
    ('RE', 'Reunion'),
    ('RO', 'Romania'),
    ('RU', 'Russian Federation'),
    ('RW', 'Rwanda'),
    ('SA', 'Saudi Arabia'),
    ('SB', 'Solomon Islands'),
    ('SC', 'Seychelles'),
    ('SD', 'Sudan'),
    ('SE', 'Sweden'),
    ('SG', 'Singapore'),
    ('SH', 'St. Helena'),
    ('SI', 'Slovenia'),
    ('SJ', 'Svalbard & Jan Mayen Islands'),
    ('SK', 'Slovakia'),
    ('SL', 'Sierra Leone'),
    ('SM', 'San Marino'),
    ('SN', 'Senegal'),
    ('SO', 'Somalia'),
    ('SR', 'Suriname'),
    ('ST', 'Sao Tome & Principe'),
    ('SV', 'El Salvador'),
    ('SY', 'Syrian Arab Republic'),
    ('SZ', 'Swaziland'),
    ('TC', 'Turks & Caicos Islands'),
    ('TD', 'Chad'),
    ('TF', 'French Southern Territories'),
    ('TG', 'Togo'),
    ('TH', 'Thailand'),
    ('TJ', 'Tajikistan'),
    ('TK', 'Tokelau'),
    ('TM', 'Turkmenistan'),
    ('TN', 'Tunisia'),
    ('TO', 'Tonga'),
    ('TP', 'East Timor'),
    ('TR', 'Turkey'),
    ('TT', 'Trinidad & Tobago'),
    ('TV', 'Tuvalu'),
    ('TW', 'Taiwan, Province of China'),
    ('TZ', 'Tanzania, United Republic of'),
    ('UA', 'Ukraine'),
    ('UG', 'Uganda'),
    ('UM', 'United States Minor Outlying Islands'),
    ('UY', 'Uruguay'),
    ('UZ', 'Uzbekistan'),
    ('VA', 'Vatican City State (Holy See)'),
    ('VC', 'St. Vincent & the Grenadines'),
    ('VE', 'Venezuela'),
    ('VG', 'British Virgin Islands'),
    ('VI', 'United States Virgin Islands'),
    ('VN', 'Viet Nam'),
    ('VU', 'Vanuatu'),
    ('WF', 'Wallis & Futuna Islands'),
    ('WS', 'Samoa'),
    ('YE', 'Yemen'),
    ('YT', 'Mayotte'),
    ('YU', 'Yugoslavia'),
    ('ZA', 'South Africa'),
    ('ZM', 'Zambia'),
    ('ZR', 'Zaire'),
    ('ZW', 'Zimbabwe'),
    ('ZZ', 'Unknown or unspecified country'),
)


def is_valid_country_abbrev(abbrev, case_sensitive=False):
    """
    Given a country code abbreviation, check to see if it matches the
    country table.

    abbrev: (str) Country code to evaluate.
    case_sensitive: (bool) When True, enforce case sensitivity.

    Returns True if valid, False if not.
    """
    if case_sensitive:
        country_code = abbrev
    else:
        country_code = abbrev.upper()

    for code, full_name in COUNTRY_TUPLES:
        if country_code == code:
            return True

    return False


def get_name_from_abbrev(abbrev, case_sensitive=False):
    """
    Given a country code abbreviation, get the full name from the table.

    abbrev: (str) Country code to retrieve the full name of.
    case_sensitive: (bool) When True, enforce case sensitivity.
    """
    if case_sensitive:
        country_code = abbrev
    else:
        country_code = abbrev.upper()

    for code, full_name in COUNTRY_TUPLES:
        if country_code == code:
            return full_name

    raise KeyError('No country with that country code.')

########NEW FILE########
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
        Exception.__init__(self, message, error_code)
        self.message = message
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
        self.error_code = int(getattr(response, 'L_ERRORCODE0', -1))
        self.message = getattr(response, 'L_LONGMESSAGE0', None)
        self.short_message = getattr(response, 'L_SHORTMESSAGE0', None)
        self.correlation_id = getattr(response, 'CORRELATIONID', None)

        super(PayPalAPIResponseError, self).__init__(self.message, self.error_code)

########NEW FILE########
__FILENAME__ = interface
# coding=utf-8
"""
The end developer will do most of their work with the PayPalInterface class found
in this module. Configuration, querying, and manipulation can all be done
with it.
"""

import types
import logging
from pprint import pformat

import requests

from paypal.settings import PayPalConfig
from paypal.response import PayPalResponse
from paypal.response_list import PayPalResponseList
from paypal.exceptions import PayPalError, PayPalAPIResponseError
from paypal.compat import is_py3

if is_py3:
    #noinspection PyUnresolvedReferences
    from urllib.parse import urlencode
else:
    from urllib import urlencode

logger = logging.getLogger('paypal.interface')


class PayPalInterface(object):

    __credentials = ['USER', 'PWD', 'SIGNATURE', 'SUBJECT']

    """
    The end developers will do 95% of their work through this class. API
    queries, configuration, etc, all go through here. See the __init__ method
    for config related details.
    """
    def __init__(self, config=None, **kwargs):
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
        if is_py3:
            # This is only valid for Python 2. In Python 3, unicode is
            # everywhere (yay).
            return kwargs

        unencoded_pairs = kwargs
        for i in unencoded_pairs.keys():
            #noinspection PyUnresolvedReferences
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

    def _sanitize_locals(self, data):
        """
        Remove the 'self' key in locals()
        It's more explicit to do it in one function
        """
        if 'self' in data:
            data = data.copy()
            del data['self']

        return data

    def _call(self, method, **kwargs):
        """
        Wrapper method for executing all API commands over HTTP. This method is
        further used to implement wrapper methods listed here:

        https://www.x.com/docs/DOC-1374

        ``method`` must be a supported NVP method listed at the above address.

        ``kwargs`` will be a hash of
        """
        # This dict holds the key/value pairs to pass to the PayPal API.
        url_values = {
            'METHOD': method,
            'VERSION': self.config.API_VERSION,
        }

        if self.config.API_AUTHENTICATION_MODE == "3TOKEN":
            url_values['USER'] = self.config.API_USERNAME
            url_values['PWD'] = self.config.API_PASSWORD
            url_values['SIGNATURE'] = self.config.API_SIGNATURE
        elif self.config.API_AUTHENTICATION_MODE == "UNIPAY":
            url_values['SUBJECT'] = self.config.UNIPAY_SUBJECT

        # All values passed to PayPal API must be uppercase.
        for key, value in kwargs.items():
            url_values[key.upper()] = value

        # This shows all of the key/val pairs we're sending to PayPal.
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('PayPal NVP Query Key/Vals:\n%s' % pformat(url_values))

        req = requests.post(
            self.config.API_ENDPOINT,
            data=url_values,
            timeout=self.config.HTTP_TIMEOUT,
            verify=self.config.API_CA_CERTS,
        )

        # Call paypal API
        response = PayPalResponse(req.text, self.config)

        logger.debug('PayPal NVP API Endpoint: %s' % self.config.API_ENDPOINT)

        if not response.success:
            logger.error('A PayPal API error was encountered.')
            url_values_no_credentials = dict((p, 'X' * len(v) if p in \
                self.__credentials else v) for (p, v) in url_values.items())
            logger.error('PayPal NVP Query Key/Vals (credentials removed):' \
                '\n%s' % pformat(url_values_no_credentials))
            logger.error('PayPal NVP Query Response')
            logger.error(response)
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
        args = self._sanitize_locals(locals())
        return self._call('AddressVerify', **args)

    def create_recurring_payments_profile(self, **kwargs):
        """Shortcut for the CreateRecurringPaymentsProfile method.
        Currently, this method only supports the Direct Payment flavor.

        It requires standard credit card information and a few additional
        parameters related to the billing. e.g.:

            profile_info = {
                # Credit card information
                'creditcardtype': 'Visa',
                'acct': '4812177017895760',
                'expdate': '102015',
                'cvv2': '123',
                'firstname': 'John',
                'lastname': 'Doe',
                'street': '1313 Mockingbird Lane',
                'city': 'Beverly Hills',
                'state': 'CA',
                'zip': '90110',
                'countrycode': 'US',
                'currencycode': 'USD',
                # Recurring payment information
                'profilestartdate': '2010-10-25T0:0:0',
                'billingperiod': 'Month',
                'billingfrequency': '6',
                'amt': '10.00',
                'desc': '6 months of our product.'
            }
            response = create_recurring_payments_profile(**profile_info)

            The above NVPs compose the bare-minimum request for creating a
            profile. For the complete list of parameters, visit this URI:
            https://www.x.com/docs/DOC-1168
        """
        return self._call('CreateRecurringPaymentsProfile', **kwargs)

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
        args = self._sanitize_locals(locals())
        return self._call('DoAuthorization', **args)

    def do_capture(self, authorizationid, amt, completetype='Complete', **kwargs):
        """Shortcut for the DoCapture method.

        Use the TRANSACTIONID from DoAuthorization, DoDirectPayment or
        DoExpressCheckoutPayment for the ``authorizationid``.

        The `amt` should be the same as the authorized transaction.
        """
        kwargs.update(self._sanitize_locals(locals()))
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
        kwargs.update(self._sanitize_locals(locals()))
        return self._call('DoDirectPayment', **kwargs)

    def do_void(self, **kwargs):
        """Shortcut for the DoVoid method.

        Use the TRANSACTIONID from DoAuthorization, DoDirectPayment or
        DoExpressCheckoutPayment for the ``AUTHORIZATIONID``.

        Required Kwargs
        ---------------
        * AUTHORIZATIONID
        """
        return self._call('DoVoid', **kwargs)

    def get_express_checkout_details(self, **kwargs):
        """Shortcut for the GetExpressCheckoutDetails method.

        Required Kwargs
        ---------------
        * TOKEN
        """
        return self._call('GetExpressCheckoutDetails', **kwargs)

    def get_transaction_details(self, **kwargs):
        """Shortcut for the GetTransactionDetails method.

        Use the TRANSACTIONID from DoAuthorization, DoDirectPayment or
        DoExpressCheckoutPayment for the ``transactionid``.

        Required Kwargs
        ---------------

        * TRANSACTIONID
        """
        return self._call('GetTransactionDetails', **kwargs)

    def transaction_search(self, **kwargs):
        """Shortcut for the TransactionSearch method.
        Returns a PayPalResponseList object, which merges the L_ syntax list
        to a list of dictionaries with properly named keys.

        Note that the API will limit returned transactions to 100.

        Required Kwargs
        ---------------
        * STARTDATE
        
        Optional Kwargs
        ---------------
        STATUS = one of ['Pending','Processing','Success','Denied','Reversed']

        """
        plain = self._call('TransactionSearch', **kwargs)
        return PayPalResponseList(plain.raw, self.config)

    def set_express_checkout(self, **kwargs):
        """Start an Express checkout.

        You'll want to use this in conjunction with
        :meth:`generate_express_checkout_redirect_url` to create a payment,
        then figure out where to redirect the user to for them to
        authorize the payment on PayPal's website.

        Required Kwargs
        ---------------

        * PAYMENTREQUEST_0_AMT
        * PAYMENTREQUEST_0_PAYMENTACTION
        * RETURNURL
        * CANCELURL
        """
        return self._call('SetExpressCheckout', **kwargs)

    def refund_transaction(self, transactionid=None, payerid=None, **kwargs):
        """Shortcut for RefundTransaction method.
           Note new API supports passing a PayerID instead of a transaction id, exactly one must be provided.
           Optional:
               INVOICEID
               REFUNDTYPE
               AMT
               CURRENCYCODE
               NOTE
               RETRYUNTIL
               REFUNDSOURCE
               MERCHANTSTOREDETAILS
               REFUNDADVICE
               REFUNDITEMDETAILS
               MSGSUBID

           MERCHANSTOREDETAILS has two fields:
               STOREID
               TERMINALID
           """
        #this line seems like a complete waste of time... kwargs should not be populated
        if (transactionid is None) and (payerid is None):
            raise PayPalError('RefundTransaction requires either a transactionid or a payerid')
        if (transactionid is not None) and (payerid is not None):
            raise PayPalError('RefundTransaction requires only one of transactionid %s and payerid %s' % (transactionid, payerid))
        if transactionid is not None:
            kwargs['TRANSACTIONID'] = transactionid
        else:
            kwargs['PAYERID'] = payerid

        return self._call('RefundTransaction', **kwargs)

    def do_express_checkout_payment(self, **kwargs):
        """Finishes an Express checkout.

        TOKEN is the token that was returned earlier by
        :meth:`set_express_checkout`. This identifies the transaction.

        Required
        --------
        * TOKEN
        * PAYMENTACTION
        * PAYERID
        * AMT

        """
        return self._call('DoExpressCheckoutPayment', **kwargs)

    def generate_express_checkout_redirect_url(self, token):
        """Returns the URL to redirect the user to for the Express checkout.

        Express Checkouts must be verified by the customer by redirecting them
        to the PayPal website. Use the token returned in the response from
        :meth:`set_express_checkout` with this function to figure out where
        to redirect the user to.

        :param str token: The unique token identifying this transaction.
        :rtype: str
        :returns: The URL to redirect the user to for approval.
        """
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
        additional = urlencode(additional)
        return url + "&" + additional

    def get_recurring_payments_profile_details(self, profileid):
        """Shortcut for the GetRecurringPaymentsProfile method.

        This returns details for a recurring payment plan. The ``profileid`` is
        a value included in the response retrieved by the function
        ``create_recurring_payments_profile``. The profile details include the
        data provided when the profile was created as well as default values
        for ignored fields and some pertinent stastics.

        e.g.:
            response = create_recurring_payments_profile(**profile_info)
            profileid = response.PROFILEID
            details = get_recurring_payments_profile(profileid)

        The response from PayPal is somewhat self-explanatory, but for a
        description of each field, visit the following URI:
        https://www.x.com/docs/DOC-1194
        """
        args = self._sanitize_locals(locals())
        return self._call('GetRecurringPaymentsProfileDetails', **args)

    def manage_recurring_payments_profile_status(self, profileid, action, note=None):
        """Shortcut to the ManageRecurringPaymentsProfileStatus method.

        ``profileid`` is the same profile id used for getting profile details.
        ``action`` should be either 'Cancel', 'Suspend', or 'Reactivate'.
        ``note`` is optional and is visible to the user. It contains the reason for the change in status.
        """
        args = self._sanitize_locals(locals())
        if not note:
            del args['note']
        return self._call('ManageRecurringPaymentsProfileStatus', **args)

    def update_recurring_payments_profile(self, profileid, **kwargs):
        """Shortcut to the UpdateRecurringPaymentsProfile method.

        ``profileid`` is the same profile id used for getting profile details.

        The keyed arguments are data in the payment profile which you wish to
        change. The profileid does not change. Anything else will take the new
        value. Most of, though not all of, the fields available are shared
        with creating a profile, but for the complete list of parameters, you
        can visit the following URI:
        https://www.x.com/docs/DOC-1212
        """
        kwargs.update(self._sanitize_locals(locals()))
        return self._call('UpdateRecurringPaymentsProfile', **kwargs)

    def bm_create_button(self, **kwargs):
        """Shortcut to the BMButtonSearch method.

        See the docs for details on arguments:
        https://cms.paypal.com/mx/cgi-bin/?cmd=_render-content&content_ID=developer/e_howto_api_nvp_BMCreateButton

        The L_BUTTONVARn fields are especially important, so make sure to
        read those and act accordingly. See unit tests for some examples.
        """
        kwargs.update(self._sanitize_locals(locals()))
        return self._call('BMCreateButton', **kwargs)

########NEW FILE########
__FILENAME__ = response
# coding=utf-8
"""
PayPalResponse parsing and processing.
"""

import logging
from pprint import pformat

from paypal.compat import is_py3

if is_py3:
    #noinspection PyUnresolvedReferences
    from urllib.parse import parse_qs
else:
    # Python 2.6 and up (but not 3.0) have urlparse.parse_qs, which is copied
    # from Python 2.5's cgi.parse_qs.
    from urlparse import parse_qs

logger = logging.getLogger('paypal.response')


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
        parseable by urlparse.parse_qs(), which sticks it into the
        :attr:`raw` dict for retrieval by the user.

        :param str query_string: The raw response from the API server.
        :param PayPalConfig config: The config object that was used to send
            the query that caused this response.
        """
        # A dict of NVP values. Don't access this directly, use
        # PayPalResponse.attribname instead. See self.__getattr__().
        self.raw = parse_qs(query_string)
        self.config = config
        logger.debug("PayPal NVP API Response:\n%s" % self.__str__())

    def __str__(self):
        """
        Returns a string representation of the PayPalResponse object, in
        'pretty-print' format.

        :rtype: str
        :returns: A 'pretty' string representation of the response dict.
        """
        return pformat(self.raw)

    def __getattr__(self, key):
        """
        Handles the retrieval of attributes that don't exist on the object
        already. This is used to get API response values. Handles some
        convenience stuff like discarding case and checking the cgi/urlparsed
        response value dict (self.raw).

        :param str key: The response attribute to get a value for.
        :rtype: str
        :returns: The requested value from the API server's response.
        """
        # PayPal response names are always uppercase.
        key = key.upper()
        try:
            value = self.raw[key]
            if len(value) == 1:
                # For some reason, PayPal returns lists for all of the values.
                # I'm not positive as to why, so we'll just take the first
                # of each one. Hasn't failed us so far.
                return value[0]
            return value
        except KeyError:
            # The requested value wasn't returned in the response.
            raise AttributeError(self)

    def __getitem__(self, key):
        """
        Another (dict-style) means of accessing response data.

        :param str key: The response key to get a value for.
        :rtype: str
        :returns: The requested value from the API server's response.
        """
        # PayPal response names are always uppercase.
        key = key.upper()
        value = self.raw[key]
        if len(value) == 1:
            # For some reason, PayPal returns lists for all of the values.
            # I'm not positive as to why, so we'll just take the first
            # of each one. Hasn't failed us so far.
            return value[0]
        return value
        
    def items(self):
        items_list = []
        for key in self.raw.keys():
            items_list.append((key, self.__getitem__(key)))
        return items_list
        
    def iteritems(self):
        for key in self.raw.keys():
            yield (key, self.__getitem__(key))

    def success(self):
        """
        Checks for the presence of errors in the response. Returns ``True`` if
        all is well, ``False`` otherwise.

        :rtype: bool
        :returns ``True`` if PayPal says our query was successful.
        """
        return self.ack.upper() in (self.config.ACK_SUCCESS,
                                    self.config.ACK_SUCCESS_WITH_WARNING)
    success = property(success)

########NEW FILE########
__FILENAME__ = response_list
# coding=utf-8
"""
PayPal response parsing of list syntax.
"""

import logging
import re

from response import PayPalResponse
from exceptions import PayPalAPIResponseError

logger = logging.getLogger('paypal.response')

class PayPalResponseList(PayPalResponse):
    """
    Subclass of PayPalResponse, parses L_style list items and
    stores them in a dictionary keyed by numeric index.

    NOTE: Don't access self.raw directly. Just do something like
    PayPalResponse.someattr, going through PayPalResponse.__getattr__().
    """
    def __init__(self, raw, config):
        self.raw = raw
        self.config = config

        L_regex = re.compile("L_([a-zA-Z]+)([0-9]{0,2})")
        # name-value pair list syntax documented at
        #  https://developer.paypal.com/docs/classic/api/NVPAPIOverview/#id084E30EC030
        # api returns max 100 items, so only two digits required

        self.list_items_dict = {}

        for key in self.raw.keys():
            match = L_regex.match(key)
            if match:
                index = match.group(2)
                d_key = match.group(1)

                if type(self.raw[key]) == type(list()) and len(self.raw[key]) == 1:
                    d_val = self.raw[key][0]
                else:
                    d_val = self.raw[key]
            
                #skip error codes
                if d_key in ['ERRORCODE','SHORTMESSAGE','LONGMESSAGE','SEVERITYCODE']:
                    continue

                if index in self.list_items_dict:
                    #dict for index exists, update
                    self.list_items_dict[index][d_key] = d_val
                else:
                    #create new dict 
                    self.list_items_dict[index] = {d_key: d_val}

        #log ResponseErrors from warning keys
        if self.raw['ACK'][0].upper() == self.config.ACK_SUCCESS_WITH_WARNING:
            self.errors = [PayPalAPIResponseError(self)]
            logger.error(self.errors)

    def items(self):
        #convert dict like {'1':{},'2':{}, ...} to list
        return list(self.list_items_dict.values())
        
    def iteritems(self):
         for key in self.list_items_dict.keys():
            yield (key, self.list_items_dict[key])

########NEW FILE########
__FILENAME__ = settings
# coding=utf-8
"""
This module contains config objects needed by paypal.interface.PayPalInterface.
Most of this is transparent to the end developer, as the PayPalConfig object
is instantiated by the PayPalInterface object.
"""

import logging
import os
from pprint import pformat

from paypal.compat import basestring
from paypal.exceptions import PayPalConfigError

logger = logging.getLogger('paypal.settings')


class PayPalConfig(object):
    """
    The PayPalConfig object is used to allow the developer to perform API
    queries with any number of different accounts or configurations. This
    is done by instantiating paypal.interface.PayPalInterface, passing config
    directives as keyword args.
    """
    # Used to validate correct values for certain config directives.
    _valid_ = {
        'API_ENVIRONMENT': ['SANDBOX', 'PRODUCTION'],
        'API_AUTHENTICATION_MODE': ['3TOKEN', 'CERTIFICATE'],
    }

    # Various API servers.
    _API_ENDPOINTS = {
        # In most cases, you want 3-Token. There's also Certificate-based
        # authentication, which uses different servers, but that's not
        # implemented.
        '3TOKEN': {
            'SANDBOX': 'https://api-3t.sandbox.paypal.com/nvp',
            'PRODUCTION': 'https://api-3t.paypal.com/nvp',
        }
    }

    _PAYPAL_URL_BASE = {
        'SANDBOX': 'https://www.sandbox.paypal.com/webscr',
        'PRODUCTION': 'https://www.paypal.com/webscr',
    }

    API_VERSION = '98.0'

    # Defaults. Used in the absence of user-specified values.
    API_ENVIRONMENT = 'SANDBOX'
    API_AUTHENTICATION_MODE = '3TOKEN'

    # 3TOKEN credentials
    API_USERNAME = None
    API_PASSWORD = None
    API_SIGNATURE = None

    # API Endpoints are just API server addresses.
    API_ENDPOINT = None
    PAYPAL_URL_BASE = None

    # API Endpoint CA certificate chain. If this is True, do a simple SSL
    # certificate check on the endpoint. If it's a full path, verify against
    # a private cert.
    # e.g. '/etc/ssl/certs/Verisign_Class_3_Public_Primary_Certification_Authority.pem'
    API_CA_CERTS = True

    # UNIPAY credentials
    UNIPAY_SUBJECT = None

    ACK_SUCCESS = "SUCCESS"
    ACK_SUCCESS_WITH_WARNING = "SUCCESSWITHWARNING"

    # In seconds. Depending on your setup, this may need to be higher.
    HTTP_TIMEOUT = 15.0

    def __init__(self, **kwargs):
        """
        PayPalConfig constructor. **kwargs catches all of the user-specified
        config directives at time of instantiation. It is fine to set these
        values post-instantiation, too.

        Some basic validation for a few values is performed below, and defaults
        are applied for certain directives in the absence of
        user-provided values.
        """
        if kwargs.get('API_ENVIRONMENT'):
            api_environment = kwargs['API_ENVIRONMENT'].upper()
            # Make sure the environment is one of the acceptable values.
            if api_environment not in self._valid_['API_ENVIRONMENT']:
                raise PayPalConfigError('Invalid API_ENVIRONMENT')
            else:
                self.API_ENVIRONMENT = api_environment

        if kwargs.get('API_AUTHENTICATION_MODE'):
            auth_mode = kwargs['API_AUTHENTICATION_MODE'].upper()
            # Make sure the auth mode is one of the known/implemented methods.
            if auth_mode not in self._valid_['API_AUTHENTICATION_MODE']:
                choices = ", ".join(self._valid_['API_AUTHENTICATION_MODE'])
                raise PayPalConfigError(
                    "Not a supported auth mode. Use one of: %s" % choices
                )
            else:
                self.API_AUTHENTICATION_MODE = auth_mode

        # Set the API endpoints, which is a cheesy way of saying API servers.
        self.API_ENDPOINT = self._API_ENDPOINTS[self.API_AUTHENTICATION_MODE][self.API_ENVIRONMENT]
        self.PAYPAL_URL_BASE = self._PAYPAL_URL_BASE[self.API_ENVIRONMENT]

        # Set the CA_CERTS location. This can either be a None, a bool, or a
        # string path.
        if kwargs.get('API_CA_CERTS'):
            self.API_CA_CERTS = kwargs['API_CA_CERTS']

            if isinstance(self.API_CA_CERTS, basestring) and not os.path.exists(self.API_CA_CERTS):
                # A CA Cert path was specified, but it's invalid.
                raise PayPalConfigError('Invalid API_CA_CERTS')

        # set the 3TOKEN required fields
        if self.API_AUTHENTICATION_MODE == '3TOKEN':
            for arg in ('API_USERNAME', 'API_PASSWORD', 'API_SIGNATURE'):
                if arg not in kwargs:
                    raise PayPalConfigError('Missing in PayPalConfig: %s ' % arg)
                setattr(self, arg, kwargs[arg])

        for arg in ['HTTP_TIMEOUT']:
            if arg in kwargs:
                setattr(self, arg, kwargs[arg])

        logger.debug(
            'PayPalConfig object instantiated with kwargs: %s' % pformat(kwargs)
        )

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
CONFIG = PayPalConfig(API_USERNAME="xxx_xxx_apix.xxx.com",
                      API_PASSWORD="xxxxxxxxxx",
                      API_SIGNATURE="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                      DEBUG_LEVEL=0)

# The following values may be found by visiting https://developer.paypal.com/,
# clicking on the 'Applications' -> 'Sandbox accounts' link in the sandbox,
# and looking at the accounts listed there.
# You'll need a business and a personal account created to run these tests.

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
    from tests import api_details
except ImportError:
    print("""
    ERROR: No api_details.py file exists in your paypal/tests directory. Please
    copy api_details_blank.py to api_details.py and modify the values to your
    own API developer _test_ credentials.

    If you don't already have test credentials, please visit:

        https://developer.paypal.com

    """)
    sys.exit(1)


def get_interface_obj():
    """
    Use this function to get a PayPalInterface object with your test API
    credentials (as specified in api_details.py). Create new interfaces for
    each unit test module to avoid potential variable pollution.
    """
    return PayPalInterface(config=api_details.CONFIG)

########NEW FILE########
__FILENAME__ = test_buttons
# coding=utf-8

import unittest
from . import interface_factory

interface = interface_factory.get_interface_obj()


class ButtonTests(unittest.TestCase):
    """
    These test the BM button API available in Payments Standard and up. This
    is the cheapest and most direct route towards accepting payments.
    """

    def test_create_button(self):
        """
        Tests the creation of a simple button. This particular one is not
        stored on the PayPal account.
        """
        button_params = {
            'BUTTONCODE': 'ENCRYPTED',
            'BUTTONTYPE': 'BUYNOW',
            'BUTTONSUBTYPE': 'SERVICES',
            'BUYNOWTEXT': 'PAYNOW',
            'L_BUTTONVAR0': 'notify_url=http://test.com',
            'L_BUTTONVAR1': 'amount=5.00',
            'L_BUTTONVAR2': 'item_name=Testing',
            'L_BUTTONVAR3': 'item_number=12345',
        }
        response = interface.bm_create_button(**button_params)
        self.assertEqual(response.ACK, 'Success')

########NEW FILE########
__FILENAME__ = test_countries
# coding=utf-8

import unittest
from paypal import countries


class TestCountries(unittest.TestCase):

    def test_is_valid_country_abbrev(self):
        self.assertEqual(True, countries.is_valid_country_abbrev('US'))
        self.assertEqual(True, countries.is_valid_country_abbrev('us'))
        self.assertEqual(False, countries.is_valid_country_abbrev('us',
                                                                  case_sensitive=True))

    def test_get_name_from_abbrev(self):
        us_fullval = 'United States of America'
        self.assertEqual(us_fullval, countries.get_name_from_abbrev('US'))
        self.assertEqual(us_fullval, countries.get_name_from_abbrev('us'))
        self.assertRaises(KeyError, countries.get_name_from_abbrev, 'us',
                          case_sensitive=True)

########NEW FILE########
__FILENAME__ = test_direct_payment
# coding=utf-8

import unittest
from paypal import PayPalAPIResponseError
from . import interface_factory
from . import api_details

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

        details = interface.get_transaction_details(TRANSACTIONID=sale.TRANSACTIONID)
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

        details = interface.get_transaction_details(TRANSACTIONID=sale.TRANSACTIONID)
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
        void = interface.do_void(AUTHORIZATIONID=auth.TRANSACTIONID, NOTE=note)
        self.assertTrue(void.success)
        self.assertEqual(auth.TRANSACTIONID, void.AUTHORIZATIONID)

        details = interface.get_transaction_details(TRANSACTIONID=auth.TRANSACTIONID)
        self.assertTrue(details.success)
        self.assertEqual(details.PAYMENTSTATUS.upper(), 'VOIDED')

########NEW FILE########
__FILENAME__ = test_express_checkout
# coding=utf-8

import unittest
from . import interface_factory
from . import api_details

interface = interface_factory.get_interface_obj()


class TestExpressCheckout(unittest.TestCase):

    def setUp(self):
        self.returnurl = 'http://www.paypal.com'
        self.cancelurl = 'http://www.ebay.com'

    def test_sale(self):
        """
        Tests the first part of a sale. At this point, this is a partial unit
        test. The user has to login to PayPal and approve the transaction,
        which is not something we have tackled in the unit test yet. So we'll
        just test the set/get_express_checkout methods.

        A call to `SetExpressCheckoutDetails`.
        A call to `DoExpressCheckoutPayment`.
        A call to `GetExpressCheckoutDetails`.
        """
        setexp_response = interface.set_express_checkout(
            amt='10.00',
            returnurl=self.returnurl, cancelurl=self.cancelurl,
            paymentaction='Order',
            email=api_details.EMAIL_PERSONAL
        )

        self.assertTrue(setexp_response)
        token = setexp_response.token

        getexp_response = interface.get_express_checkout_details(token=token)

        # Redirect your client to this URL for approval.
        redir_url = interface.generate_express_checkout_redirect_url(token)
        # Once they have approved your transaction at PayPal, they'll get
        # directed to the returnurl value you defined in set_express_checkout()
        # above. This view should then call do_express_checkout_payment() with
        # paymentaction = 'Sale'. This will finalize and bill.

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
        pass

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

########NEW FILE########
