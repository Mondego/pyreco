__FILENAME__ = base
class DineroObject(object):
    def __getattr__(self, attr):
        if attr == '__setstate__':
            raise AttributeError
        try:
            return self.data[attr]
        except KeyError as e:
            raise AttributeError(e)

    def to_dict(self):
        return vars(self)

########NEW FILE########
__FILENAME__ = card
from dinero.log import log
from dinero import get_gateway
from dinero.base import DineroObject


class CreditCard(DineroObject):
    """
    A representation of a credit card to be stored in the gateway.
    """

    def __init__(self, gateway_name, customer_id, **kwargs):
        self.gateway_name = gateway_name
        self.customer_id = customer_id
        self.data = kwargs

    @log
    def save(self):
        """
        Save changes to a card to the gateway.
        """
        gateway = get_gateway(self.gateway_name)
        gateway.update_card(self)

    @log
    def delete(self):
        """
        Delete a card from the gateway.
        """
        gateway = get_gateway(self.gateway_name)
        gateway.delete_card(self)
        return True

    def __setattr__(self, attr, val):
        if attr in ['customer_id', 'data', 'gateway_name']:
            self.__dict__[attr] = val
        else:
            self.data[attr] = val

    @classmethod
    def from_dict(cls, dict):
        return cls(dict['gateway_name'],
                   dict['customer_id'],
                   **dict['data']
                   )

    def __repr__(self):
        return "CreditCard(({customer_id!r}, **{data!r})".format(**self.to_dict())

########NEW FILE########
__FILENAME__ = configure


def fancy_import(import_name):
    """
    This takes a fully qualified object name, like
    'dinero.gateways.AuthorizeNet', and turns it into the
    dinero.gateways.AuthorizeNet object.
    """
    import_path, import_me = import_name.rsplit('.', 1)
    imported = __import__(import_path, globals(), locals(), [import_me], -1)
    return getattr(imported, import_me)


_configured_gateways = {}


def configure(options):
    """
    Takes a dictionary of name -> gateway configuration pairs.
    configure({
        'auth.net': { # the name for this gateway
            'default': True, # register as the default gateway
            'type': 'dinero.gateways.AuthorizeNet' # the gateway path
            # ... gateway-specific configuration
        }})

    `settings.py` is a great place to put this call in a Django project.
    """
    for name, conf in options.iteritems():
        _configured_gateways[name] = fancy_import(conf['type'])(conf)
        _configured_gateways[name].name = name
        is_default = conf.get('default', False)
        if is_default:
            for gateway in _configured_gateways.itervalues():
                gateway.default = False
        _configured_gateways[name].default = is_default


def get_gateway(gateway_name=None):
    """
    Returns a configured gateway.  If no gateway name is provided, it returns
    the config marked as 'default'.
    """
    if gateway_name is None:
        return get_default_gateway()
    return _configured_gateways[gateway_name]


def get_default_gateway():
    """
    Returns the default gateway name.  If no gateway is found, a KeyError is thrown.

    Why KeyError?  That is the same error that would be thrown if _configured_gateways
    was accessed with a gateway name that doesn't exist.
    """
    for gateway in _configured_gateways.itervalues():
        if gateway.default:
            return gateway
    raise KeyError("Could not find a gateway configuration that is assigned as 'default'")


def set_default_gateway(name):
    """
    Set a default gateway that has already been configured.
    """
    for gateway in _configured_gateways.itervalues():
        gateway.default = False
    _configured_gateways[name].default = True

########NEW FILE########
__FILENAME__ = customer
from dinero import get_gateway
from dinero.exceptions import InvalidCustomerException
from dinero.log import log
from dinero.card import CreditCard
from dinero.base import DineroObject


class Customer(DineroObject):
    """
    A :class:`Customer` object stores information about your customers.
    """

    @classmethod
    @log
    def create(cls, gateway_name=None, **kwargs):
        """
        Creates and stores a customer object.  When you first create a
        customer, you are required to also pass in arguments for a credit card. ::

            Customer.create(
                email='bill@example.com',

                # required for credit card
                number='4111111111111111',
                cvv='900',
                month='12',
                year='2015',
                address='123 Elm St.',
                zip='12345',
            )

        This method also accepts ``gateway_name``.
        """
        gateway = get_gateway(gateway_name)
        resp = gateway.create_customer(kwargs)
        return cls(gateway_name=gateway.name, **resp)

    @classmethod
    @log
    def retrieve(cls, customer_id, gateway_name=None):
        """
        Fetches a customer object from the gateway.  This optionally accepts a
        ``gateway_name`` parameter.
        """
        gateway = get_gateway(gateway_name)
        resp, cards = gateway.retrieve_customer(customer_id)
        # resp must have customer_id in it
        customer = cls(gateway_name=gateway.name, **resp)
        for card in cards:
            customer.cards.append(CreditCard(
                gateway_name=gateway.name,
                **card
                ))
        return customer

    def __init__(self, gateway_name, customer_id, **kwargs):
        self.gateway_name = gateway_name
        self.customer_id = customer_id
        self.data = kwargs
        self.data['cards'] = []

    def update(self, options):
        for key, value in options.iteritems():
            setattr(self, key, value)

    @log
    def save(self):
        """
        Saves changes to a customer object.
        """
        if not self.customer_id:
            raise InvalidCustomerException("Cannot save a customer that doesn't have a customer_id")
        gateway = get_gateway(self.gateway_name)
        gateway.update_customer(self.customer_id, self.data)
        return True

    @log
    def delete(self):
        """
        Deletes a customer object from the gateway.
        """
        if not self.customer_id:
            raise InvalidCustomerException("Cannot delete a customer that doesn't have a customer_id")
        gateway = get_gateway(self.gateway_name)
        gateway.delete_customer(self.customer_id)
        self.customer_id = None
        return True

    @log
    def add_card(self, gateway_name=None, **options):
        """
        The first credit card is added when you call :meth:`create`, but you
        can add more cards using this method. ::

            customer.add_card(
                number='4222222222222',
                cvv='900',
                month='12'
                year='2015'
                address='123 Elm St',
                zip='12345',
            )
        """
        if not self.customer_id:
            raise InvalidCustomerException("Cannot add a card to a customer that doesn't have a customer_id")
        gateway = get_gateway(gateway_name)
        resp = gateway.add_card_to_customer(self, options)
        card = CreditCard(gateway_name=self.gateway_name, **resp)
        self.cards.append(card)
        return card

    def __setattr__(self, attr, val):
        if attr in ['gateway_name', 'customer_id', 'data']:
            self.__dict__[attr] = val
        else:
            self.data[attr] = val

    @classmethod
    def from_dict(cls, dict):
        return cls(dict['gateway_name'],
                   dict['customer_id'],
                   **dict['data']
                   )

    def __repr__(self):
        return "Customer({gateway_name!r}, {customer_id!r}, **{data!r})".format(**self.to_dict())

########NEW FILE########
__FILENAME__ = exceptions
class DineroException(Exception):
    pass

class GatewayException(DineroException):
    """
    Exceptions resulting from malformed requests to the gateway.  For example,
    if you do not have the correct login credentials, or if your request has
    malformed data.
    """
    pass

class PaymentException(DineroException):
    """
    This is how errors are reported when submitting a transaction.
    PaymentException has an `errors` property that stores a list of
    `PaymentError` instances, one for each error that occured. The `in`
    operator is overrided to provide a subclass-like interface, so if `a` is an
    instance of `Foo`, `Foo in PaymentException([a])` will be True.
    """

    def __init__(self, errors=None):
        self.errors = errors or []

    def has(self, error):
        return any(isinstance(i, error) for i in self.errors)

    def __contains__(self, key):
        return self.has(key)

    def __repr__(self):
        return "PaymentException(%r)" % (self.errors,)


class PaymentError(DineroException):
    """
    These exceptions are never actually raised, they always belong to a
    PaymentException.
    """
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.args[0])

class VerificationError(PaymentError):
    pass

class CVVError(VerificationError):
    pass

class AVSError(VerificationError):
    pass

class InvalidCardError(PaymentError):
    pass

class InvalidAmountError(PaymentError):
    pass

class ExpiryError(PaymentError):
    pass

class CardDeclinedError(PaymentError):
    pass

class DuplicateTransactionError(PaymentError):
    pass

class RefundError(PaymentError):
    pass

class InvalidTransactionError(PaymentError):
    pass


##|
##|  CUSTOMER
##|
class CustomerError(DineroException):
    pass


class InvalidCustomerException(CustomerError):
    pass


class DuplicateCustomerError(CustomerError):
    def __init__(self, *args, **kwargs):
        if 'customer_id' in kwargs:
            self.customer_id = kwargs.pop('customer_id')
        else:
            self.customer_id = None
        super(DuplicateCustomerError, self).__init__(*args, **kwargs)


class DuplicateCardError(CustomerError):
    pass


class CustomerNotFoundError(CustomerError):
    pass

########NEW FILE########
__FILENAME__ = authorizenet_gateway
from __future__ import division
import re
import requests
from lxml import etree

from dinero.ordereddict import OrderedDict
from dinero.exceptions import *
from dinero.gateways.base import Gateway

from datetime import date

# resonseCodes
# 1 = Approved
# 2 = Declined
# 3 = Error
# 4 = Held for Review
SUCCESSFUL_RESPONSES = ['1']

# CVV RESPONSES
# M = Match
# N = No Match
# P = Not Processed
# S = Should have been present
# U = Issuer unable to process request
CVV_SUCCESSFUL_RESPONSES = ['M']

# AVS RESPONSES
# A = Address (Street) matches, ZIP does not
# B = Address information not provided for AVS check
# E = AVS error
# G = Non.S. Card Issuing Bank
# N = No Match on Address (Street) or ZIP
# P = AVS not applicable for this transaction
# R = Retry System unavailable or timed out
# S = Service not supported by issuer
# U = Address information is unavailable
# W = Nine digit ZIP matches, Address (Street) does not
# X = Address (Street) and nine digit ZIP match
# Y = Address (Street) and five digit ZIP match
# Z = Five digit ZIP matches, Address (Street) does not
AVS_SUCCESSFUL_RESPONSES = [
    'X',  # Address (Street) and nine digit ZIP match
    'Y',  # Address (Street) and five digit ZIP match
]

AVS_ZIP_SUCCESSFUL_RESPONSES = [
    'W',  # Nine digit ZIP matches, Address (Street) does not
    'X',  # Address (Street) and nine digit ZIP match
    'Y',  # Address (Street) and five digit ZIP match
    'Z',  # Five digit ZIP matches, Address (Street) does not
]

AVS_ADDRESS_SUCCESSFUL_RESPONSES = [
    'A',  # Address (Street) matches, ZIP does not
    'X',  # Address (Street) and nine digit ZIP match
    'Y',  # Address (Street) and five digit ZIP match
]


def xml_post(url, obj):
    resp = requests.post(
            url,
            data=etree.tostring(obj),
            headers={'content-type': 'application/xml'},
            verify=True,
            )

    content = resp.content
    if isinstance(content, unicode) and content[0] == u'\ufeff':
        # authorize.net puts a BOM in utf-8. Shame.
        content = content[1:]
    content = str(content)
    return etree.XML(content)


def prepare_number(number):
    return re.sub('[^0-9Xx]', '', number)


def handle_value(root, key, value):
    if value is not None:
        sub = etree.SubElement(root, key)

        if isinstance(value, dict):
            _dict_to_xml(sub, value)
        elif isinstance(value, unicode):
            sub.text = value
        elif value:
            sub.text = str(value)


def _dict_to_xml(root, dictionary, ns=None):
    if isinstance(root, basestring):
        if ns is None:
            nsmap = None
        else:
            nsmap = {None: ns}
        root = etree.Element(root, nsmap=nsmap)

    for key, value in dictionary.iteritems():
        if isinstance(value, list):
            for item in value:
                handle_value(root, key, item)
        else:
            handle_value(root, key, value)

    return root


def get_tag(elem):
    return elem.tag.partition('}')[2] or elem.tag


def xml_to_dict(parent):
    ret = OrderedDict()

    parent_tag = get_tag(parent)
    if parent_tag in ('messages', 'errors'):
        ret[parent_tag[:-1]] = []

    if parent_tag == 'profile':
        ret['paymentProfiles'] = []

    for child in parent:
        tag = get_tag(child)

        if len(child):
            child_value = xml_to_dict(child)
        else:
            child_value = child.text and child.text.strip() or ''

        if tag in ret and isinstance(ret[tag], list):
            x = ret[tag]
            del(ret[tag])
            ret[tag] = x

            ret[tag].append(child_value)
        else:
            ret[tag] = child_value

    return ret


def dotted_get(dict, key):
    searches = key.split('.')
    while searches:
        try:
            dict = dict[searches.pop(0)]
        except KeyError:
            return None
    return dict

def get_first_of(dict, possibilities, default=None):
    for i in possibilities:
        if i in dict:
            return dict[i]

    return default


RESPONSE_CODE_EXCEPTION_MAP = {
        '8':  [ExpiryError],
        '6':  [InvalidCardError],
        '37': [InvalidCardError],
        '5':  [InvalidAmountError],
        '27': [AVSError],
        '65': [CVVError],
        '45': [AVSError, CVVError],
        '2':  [CardDeclinedError],
        '11': [DuplicateTransactionError],
        '54': [RefundError],
        '33': [InvalidTransactionError],
        '44': [CVVError],
        }

INVALID_AUTHENTICATION_ERROR_CODE = 'E00007'


def payment_exception_factory(errors):
    exceptions = []
    for code, message in errors:
        try:
            # instantiate all the classes in RESPONSE_CODE_EXCEPTION_MAP[code]
            exceptions.extend(exception_class(message) for exception_class in RESPONSE_CODE_EXCEPTION_MAP[code])
        except KeyError:
            raise DineroException("I don't recognize this error: {0!r}. Better call the programmers.".format(errors))
    return exceptions


class AuthorizeNet(Gateway):
    ns = 'AnetApi/xml/v1/schema/AnetApiSchema.xsd'
    live_url = 'https://api.authorize.net/xml/v1/request.api'
    test_url = 'https://apitest.authorize.net/xml/v1/request.api'

    def __init__(self, options):
        self.login_id = options['login_id']
        self.transaction_key = options['transaction_key']

    _url = None

    @property
    def url(self):
        if not self._url:
            # Auto-discover if this is a real account or a developer account.  Tries
            # to access both end points and see which one works.
            self._url = self.test_url
            try:
                # 0 is an invalid transaction ID.  This should raise an
                # InvalidTransactionError.
                self._void('0')
            except PaymentException as e:
                if InvalidTransactionError not in e:
                    raise
            except GatewayException as e:
                error_code = e.args[0][0][0]
                if error_code == INVALID_AUTHENTICATION_ERROR_CODE:
                    self._url = self.live_url
                    try:
                        self._void('0')
                    except PaymentException as e:
                        if InvalidTransactionError not in e:
                            raise
                else:
                    raise
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    def build_xml(self, root_name, root):
        root.insert(0, 'merchantAuthentication', OrderedDict([
                ('name', self.login_id),
                ('transactionKey', self.transaction_key),
                ]))

        return _dict_to_xml(root_name, root, self.ns)

    def check_for_error(self, resp):
        if resp['messages']['resultCode'] == 'Error':
            if 'transactionResponse' in resp:
                raise PaymentException(payment_exception_factory([(errors['errorCode'], errors['errorText'])
                                                                  for errors in resp['transactionResponse']['errors']['error']]))
            else:
                raise GatewayException([(message['code'], message['text'])
                                        for message in resp['messages']['message']])

        # Sometimes Authorize.net is confused and returns errors even though it
        # says that the request was Successful!
        try:
            raise PaymentException(payment_exception_factory([(errors['errorCode'], errors['errorText'])
                                                              for errors in resp['transactionResponse']['errors']['error']]))
        except KeyError:
            pass

    ##|
    ##|  XML BUILDERS
    ##|
    def _transaction_xml(self, price, options):
        if options.get('settle', True):
            txn_type = 'authCaptureTransaction'
        else:
            txn_type = 'authOnlyTransaction'

        transaction_xml = OrderedDict([
                ('transactionType', txn_type),
                ('amount', price),
            ])
        payment = self._payment_xml(options)
        if payment:
            transaction_xml['payment'] = payment
        if options.get('invoice_number'):
            transaction_xml['order'] = OrderedDict([
                ('invoiceNumber', options['invoice_number']),
            ])
        # customer node causes fail if it is present, but empty.
        customer_xml = self._simple_customer_xml(options)
        if customer_xml:
            transaction_xml['customer'] = customer_xml
        billto = self._billto_xml(options)
        if billto:
            transaction_xml['billTo'] = billto
        transaction_xml['transactionSettings'] = OrderedDict([
                    ('setting', [
                        OrderedDict([
                            ('settingName', 'duplicateWindow'),
                            ('settingValue', 0),
                            ]),
                        OrderedDict([
                            ('settingName', 'testRequest'),
                            ('settingValue', 'false'),
                            ]),
                        ],)
                    ])

        xml = self.build_xml('createTransactionRequest', OrderedDict([
            ('transactionRequest', transaction_xml,),
            ]))
        return xml

    def _payment_xml(self, options):
        year = str(options.get('year', '0'))
        if year != 'XXXX' and int(year) < 100:
            century = date.today().year // 100
            year = str(century) + str(year).zfill(2)

        # zeropad the month
        expiry = str(year) + '-' + str(options.get('month', '0')).zfill(2)
        if expiry == 'XXXX-XX':
            expiry = 'XXXX'

        payment_xml = OrderedDict([
            ('creditCard', OrderedDict([
                ('cardNumber', prepare_number(options['number'])),
                ('expirationDate', expiry),
                ('cardCode', options.get('cvv')),
                ])),
            ])
        if any(val != None for val in payment_xml.values()):
            return payment_xml
        return None

    def _billto_xml(self, options):
        billto_xml = OrderedDict([
            ('firstName', options.get('first_name')),
            ('lastName', options.get('last_name')),
            ('company', options.get('company')),
            ('address', options.get('address')),
            ('city', options.get('city')),
            ('state', options.get('state')),
            ('zip', options.get('zip')),
            ('country', options.get('country')),
            ('phoneNumber', options.get('phone')),
            ('faxNumber', options.get('fax')),
            ])
        if any(val != None for val in billto_xml.values()):
            return billto_xml
        return None

    def _simple_customer_xml(self, options):
        if not ('customer_id' in options or 'email' in options):
            return None
        return OrderedDict([
                ('id', options.get('customer_id')),
                ('email', options.get('email')),
                ])

    def _create_customer_xml(self, options):
        # include <billTo> and <payment> fields only if
        # the necessary data was included

        # build <billTo> entry?
        billto_fields = [
            'first_name',
            'last_name',
            'company',
            'address',
            'city',
            'state',
            'zip',
            'country',
            'phone',
            'fax',
            ]
        if any(field in options for field in billto_fields):
            billto = ('billTo', self._billto_xml(options))
        else:
            billto = None

        # build <payment> entry?
        if 'number' in options:
            payment = ('payment', self._payment_xml(options))
        else:
            payment = None

        if billto or payment:
            stuff = []
            if billto:
                stuff.append(billto)
            if payment:
                stuff.append(payment)
            payment_profiles = ('paymentProfiles', OrderedDict(stuff))
        else:
            payment_profiles = None

        stuff = [('email', options['email'])]
        if payment_profiles:
            stuff.append(payment_profiles)
        root = OrderedDict([
            ('profile', OrderedDict(stuff)),
            ])
        return self.build_xml('createCustomerProfileRequest', root)

    def _update_customer_xml(self, customer_id, options):
        stuff = [('email', options['email']), ('customerProfileId', customer_id)]

        root = OrderedDict([
            ('profile', OrderedDict(stuff)),
            ])
        return self.build_xml('updateCustomerProfileRequest', root)

    def _charge_customer_xml(self, customer_id, card_id, price, options):
        if options.get('settle', True):
            txn_type = 'profileTransAuthCapture'
        else:
            txn_type = 'profileTransAuthOnly'

        return self.build_xml('createCustomerProfileTransactionRequest', OrderedDict([
                ('transaction', OrderedDict([
                    (txn_type, OrderedDict([
                        ('amount', price),
                        ('customerProfileId', customer_id),
                        ('customerPaymentProfileId', card_id),
                        ('cardCode', options.get('cvv')),
                    ])),
                ]))
            ]))

    def _resp_to_transaction_dict(self, resp, price):
        ret = {
                'price': price,
                'transaction_id': resp['transId'],
                'avs_successful': get_first_of(resp, ['avsResultCode', 'AVSResponse']) in AVS_SUCCESSFUL_RESPONSES,
                'cvv_successful': get_first_of(resp, ['cvvResultCode', 'cardCodeResponse']) in CVV_SUCCESSFUL_RESPONSES,
                'avs_zip_successful': get_first_of(resp, ['avsResultCode', 'AVSResponse']) in AVS_ZIP_SUCCESSFUL_RESPONSES,
                'avs_address_successful': get_first_of(resp, ['avsResultCode', 'AVSResponse']) in AVS_ADDRESS_SUCCESSFUL_RESPONSES,
                'auth_code': resp.get('authCode'),
                'status': resp.get('transactionStatus'),
                }

        try:
            ret['account_number'] = resp['accountNumber']
            ret['card_type'] = resp['accountType']
        except KeyError:
            ret['account_number'] = resp['payment']['creditCard']['cardNumber']
            ret['card_type'] = resp['payment']['creditCard']['cardType']

        try:
            customer = resp['customer']
            if customer:
                ret['customer_id'] = customer.get('id')
                if ret['customer_id'] and re.match('^[0-9]+$', ret['customer_id']):
                    ret['customer_id'] = int(ret['customer_id'])
                ret['email'] = customer.get('email')
        except KeyError:
            pass

        ret['last_4'] = ret['account_number'][-4:]

        try:
            ret['messages'] = [(message['code'], message['description'])
                               for message in resp['messages']['message']]
        except KeyError:
            pass

        return ret

    RESPONSE_CODE = 0
    AUTH_CODE = 4
    TRANSACTION_ID = 6
    ACCOUNT_NUMBER = 50
    ACCOUNT_TYPE = 51

    def _resp_to_transaction_dict_direct_response(self, direct_resp, price):
        resp_list = direct_resp.split(',')
        ret = {
                'price': price,
                'response_code': resp_list[self.RESPONSE_CODE],
                'auth_code': resp_list[self.AUTH_CODE],
                'transaction_id': resp_list[self.TRANSACTION_ID],
                'account_number': resp_list[self.ACCOUNT_NUMBER],
                'card_type': resp_list[self.ACCOUNT_TYPE],
                'last_4': resp_list[self.ACCOUNT_NUMBER][-4:],
                }
        return ret

    def charge(self, price, options):
        if 'customer' in options:
            return self.charge_customer(options['customer'], price, options)
        if 'cc' in options:
            return self.charge_card(options['cc'], price, options)

        xml = self._transaction_xml(price, options)

        resp = xml_to_dict(xml_post(self.url, xml))
        self.check_for_error(resp)

        return self._resp_to_transaction_dict(resp['transactionResponse'], price)

    def retrieve(self, transaction_id):
        xml = self.build_xml('getTransactionDetailsRequest', OrderedDict([
            ('transId', transaction_id),
            ]))

        resp = xml_to_dict(xml_post(self.url, xml))
        self.check_for_error(resp)

        return self._resp_to_transaction_dict(resp['transaction'], resp['transaction']['authAmount'])

    def void(self, transaction):
        return self._void(transaction.transaction_id)

    def _void(self, transaction_id):
        xml = self.build_xml('createTransactionRequest', OrderedDict([
            ('transactionRequest', OrderedDict([
                ('transactionType', 'voidTransaction'),
                ('refTransId', transaction_id),
            ])),
        ]))

        resp = xml_to_dict(xml_post(self.url, xml))
        self.check_for_error(resp)

        return True

    def refund(self, transaction, amount):
        xml = self.build_xml('createTransactionRequest', OrderedDict([
            ('transactionRequest', OrderedDict([
                ('transactionType', 'refundTransaction'),
                ('amount', amount),
                ('payment', self._payment_xml({
                    'number': transaction.data['account_number'],
                    'year': 'XXXX',
                    'month': 'XX'
                })),
                ('refTransId', transaction.transaction_id),
                ])),
            ]))

        resp = xml_to_dict(xml_post(self.url, xml))
        self.check_for_error(resp)

        return True

    def create_customer(self, options):
        if 'email' not in options:
            raise InvalidCustomerException('"email" is a required field in Customer.create')

        xml = self._create_customer_xml(options)
        resp = xml_to_dict(xml_post(self.url, xml))
        try:
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            if error_code == 'E00039':  # Duplicate Record
                e.customer_id = None

                customer_match = re.search(r'^A duplicate record with ID (.*) already exists.$', e.message[0][1])
                if customer_match:
                    e.customer_id = customer_match.group(1)
                raise DuplicateCustomerError(e, customer_id=e.customer_id)
            elif error_code == 'E00013':  # Expiration Date is invalid
                raise InvalidCardError(e)
            raise

        # make a copy of options
        profile = {}
        profile.update(options)
        # and add information from the createCustomerProfileRequest response
        profile['customer_id'] = resp['customerProfileId']
        # authorize.net only:
        profile['card_id'] = None
        try:
            if resp['customerPaymentProfileIdList'] and resp['customerPaymentProfileIdList']['numericString']:
                profile['card_id'] = resp['customerPaymentProfileIdList']['numericString']
        except KeyError:
            pass

        return profile

    def _update_customer_payment(self, customer_id, options):
        # update <billTo> and <payment> fields only if
        # the necessary data was included

        # update <billTo> entry?
        billto_fields = [
            'first_name',
            'last_name',
            'company',
            'address',
            'city',
            'state',
            'zip',
            'country',
            'phone',
            'fax',
            ]
        if any(field in options for field in billto_fields):
            billto = ('billTo', self._billto_xml(options))
        else:
            billto = None

        # update <payment> entry?
        if 'number' in options:
            payment = ('payment', self._payment_xml(options))
        else:
            payment = None

        if billto or payment:
            if 'card_id' in options:
                card_id = options['card_id']
            else:
                customer = self.retrieve_customer(customer_id)
                card_id = customer.card_id

            merge = None
            if card_id:
                try:
                    profile = self._get_customer_payment_profile(customer_id, card_id)
                    # TODO: test this, sorry
                    merge = self._dict_to_payment_profile(profile['paymentProfile'])
                    merge.update(options)
                    options = merge
                except CustomerNotFoundError:
                    pass

            stuff = []
            # refresh billto and payment if merge came back with anything
            if merge:
                billto = ('billTo', self._billto_xml(options))

            if billto:
                stuff.append(billto)

            if merge:
                payment = ('payment', self._payment_xml(options))

            if payment:
                stuff.append(payment)

            if card_id:
                stuff.append(('customerPaymentProfileId', card_id))

                root = OrderedDict([
                    ('customerProfileId', customer_id),
                    ('paymentProfile', OrderedDict(stuff)),
                    ])
                xml = self.build_xml('updateCustomerPaymentProfileRequest', root)
                resp = xml_to_dict(xml_post(self.url, xml))
            else:
                root = OrderedDict([
                    ('customerProfileId', customer_id),
                    ('paymentProfile', OrderedDict(stuff)),
                    ])
                xml = self.build_xml('createCustomerPaymentProfileRequest', root)
                resp = xml_to_dict(xml_post(self.url, xml))

            try:
                self.check_for_error(resp)
            except GatewayException as e:
                error_code = e.args[0][0][0]
                if error_code == 'E00039':  # Duplicate Record
                    raise DuplicateCustomerError(e)
                elif error_code == 'E00013':  # Expiration Date is invalid
                    raise InvalidCardError(e)
                raise

    def add_card_to_customer(self, customer, options):
        root = OrderedDict([
            ('customerProfileId', customer.customer_id),
            ('paymentProfile', OrderedDict([
                ('billTo', self._billto_xml(options)),
                ('payment', self._payment_xml(options)),
                ])),
            ('validationMode', 'liveMode'),
            ])
        xml = self.build_xml('createCustomerPaymentProfileRequest', root)
        resp = xml_to_dict(xml_post(self.url, xml))
        try:
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            if error_code == 'E00039':  # Duplicate Record
                raise DuplicateCardError(e)
            elif error_code == 'E00013':  # Expiration Date is invalid
                raise InvalidCardError(e)
            raise
        card = self._dict_to_payment_profile(root['paymentProfile'])
        card.update({
            'customer_id': customer.customer_id,
            'card_id': resp['customerPaymentProfileId'],
        })
        return card

    def update_customer(self, customer_id, options):
        try:
            xml = self._update_customer_xml(customer_id, options)
            resp = xml_to_dict(xml_post(self.url, xml))
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            if error_code == 'E00040':  # NotFound
                raise CustomerNotFoundError(e)
            raise
        else:
            self._update_customer_payment(customer_id, options)

        return True

    def retrieve_customer(self, customer_id):
        xml = self.build_xml('getCustomerProfileRequest', OrderedDict([
            ('customerProfileId', customer_id),
            ]))

        resp = xml_to_dict(xml_post(self.url, xml))
        try:
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            if error_code == 'E00040':  # NotFound
                raise CustomerNotFoundError(e)
            raise

        return self._dict_to_customer(resp['profile'])

    def delete_customer(self, customer_id):
        xml = self.build_xml('deleteCustomerProfileRequest', OrderedDict([
            ('customerProfileId', customer_id),
            ]))
        resp = xml_to_dict(xml_post(self.url, xml))
        try:
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            if error_code == 'E00040':  # NotFound
                raise CustomerNotFoundError(e)
            raise

        return True

    def charge_customer(self, customer, price, options):
        customer_id = customer.customer_id

        try:
            card_id = customer.card_id
        except AttributeError:
            customer = self.retrieve_customer(customer_id)
            card_id = customer.card_id

        return self._charge_customer(customer_id, card_id, price, options)

    def _charge_customer(self, customer_id, card_id, price, options):
        xml = self._charge_customer_xml(customer_id, card_id, price, options)
        resp = xml_to_dict(xml_post(self.url, xml))
        try:
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            if error_code == 'E00040':  # NotFound
                raise CustomerNotFoundError(e)
            raise

        return self._resp_to_transaction_dict_direct_response(resp['directResponse'], price)

    def update_card(self, card):
        xml = self.build_xml('updateCustomerPaymentProfileRequest', OrderedDict([
            ('customerProfileId', card.customer_id),
            ('paymentProfile', OrderedDict([
                ('billTo', self._billto_xml(card.data)),
                ('payment', self._payment_xml(card.data)),
                ('customerPaymentProfileId', card.card_id),
            ])),
            ('validationMode', 'liveMode'),
        ]))
        resp = xml_to_dict(xml_post(self.url, xml))
        try:
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            raise

    def charge_card(self, card, price, options):
        return self._charge_customer(card.customer_id, card.card_id, price, options)

    def _get_customer_payment_profile(self, customer_id, card_id):
        xml = self.build_xml('getCustomerPaymentProfileRequest', OrderedDict([
            ('customerProfileId', customer_id),
            ('customerPaymentProfileId', card_id),
            ]))
        resp = xml_to_dict(xml_post(self.url, xml))
        try:
            self.check_for_error(resp)
        except GatewayException as e:
            error_code = e.args[0][0][0]
            if error_code == 'E00040':  # NotFound
                raise CustomerNotFoundError(e)
            raise

        return resp

    def _dict_to_customer(self, resp):
        ret = {
                'customer_id': resp['customerProfileId'],
                'email': resp['email'],
            }

        # more than one paymentProfile?
        if isinstance(resp.get('paymentProfiles'), list):
            try:
                resp['paymentProfile'] = resp['paymentProfiles'][0]
            except IndexError:
                resp['paymentProfile'] = {}
        else:
            resp['paymentProfile'] = resp['paymentProfiles']

        # more than one creditCard?
        try:
            if isinstance(resp['paymentProfile']['profile']['creditCard'], list):
                resp['paymentProfile']['profile']['creditCard'] = resp['paymentProfile']['profile']['creditCard'][0]
        except KeyError:
            pass

        gets = {
            'first_name': 'paymentProfile.billTo.firstName',
            'last_name': 'paymentProfile.billTo.lastName',
            'company': 'paymentProfile.billTo.company',
            'phone': 'paymentProfile.billTo.phoneNumber',
            'fax': 'paymentProfile.billTo.faxNumber',
            'address': 'paymentProfile.billTo.address',
            'state': 'paymentProfile.billTo.state',
            'city': 'paymentProfile.billTo.city',
            'zip': 'paymentProfile.billTo.zip',
            'country': 'paymentProfile.billTo.country',
            'last_4': 'paymentProfile.payment.creditCard.cardNumber',

            # auth.net specific
            'number': 'paymentProfile.payment.creditCard.cardNumber',
            'expiration_date': 'paymentProfile.payment.creditCard.expirationDate',
            'card_id': 'paymentProfile.customerPaymentProfileId',
            }
        for key, kvp in gets.iteritems():
            v = dotted_get(resp, kvp)
            if v:
                ret[key] = v

        if 'expiration_date' in ret:
            # in the form "XXXX" or "YYYY-MM"
            if '-' in ret['expiration_date']:
                ret['year'], ret['month'] = ret['expiration_date'].split('-', 1)
            else:
                ret['year'], ret['month'] = ('XXXX', 'XX')

        if 'last_4' in ret:
            # in the form "XXXX1234"
            ret['last_4'] = ret['last_4'][-4:]
            # now it's in the form "1234"

        try:
            ret['messages'] = [(message['code'], message['description'])
                               for message in resp['messages']['message']]
        except KeyError:
            pass

        cards = []
        profile_list = resp['paymentProfiles']
        if isinstance(profile_list, dict):
            profile_list = [profile_list]
        for profile_dict in profile_list:
            card = self._dict_to_payment_profile(profile_dict)
            card['customer_id'] = ret['customer_id']
            cards.append(card)

        return ret, cards

    def _dict_to_payment_profile(self, resp):
        ret = {}

        try:
            if isinstance(resp['profile']['creditCard'], list):
                resp['profile']['creditCard'] = resp['profile']['creditCard'][0]
        except KeyError:
            pass

        gets = {
            'card_id': 'customerPaymentProfileId',

            'first_name': 'billTo.firstName',
            'last_name': 'billTo.lastName',
            'company': 'billTo.company',
            'phone': 'billTo.phoneNumber',
            'fax': 'billTo.faxNumber',
            'address': 'billTo.address',
            'state': 'billTo.state',
            'city': 'billTo.city',
            'zip': 'billTo.zip',
            'country': 'billTo.country',
            'last_4': 'payment.creditCard.cardNumber',

            # these must be sent to auth.net in updateCustomerPaymentProfileRequest
            'number': 'payment.creditCard.cardNumber',
            'expiration_date': 'payment.creditCard.expirationDate',
        }

        for key, kvp in gets.iteritems():
            v = dotted_get(resp, kvp)
            if v:
                ret[key] = v

        if 'last_4' in ret:
            # in the form "XXXX1234"
            ret['last_4'] = ret['last_4'][-4:]
            # now it's in the form "1234"

        if 'expiration_date' in ret:
            # in the form "XXXX" or "YYYY-MM"
            if '-' in ret['expiration_date']:
                ret['year'], ret['month'] = ret['expiration_date'].split('-', 1)
            else:
                ret['year'], ret['month'] = ('XXXX', 'XX')

        try:
            ret['messages'] = [(message['code'], message['description'])
                               for message in resp['messages']['message']]
        except KeyError:
            pass

        return ret

    def settle(self, transaction, amount):
        xml = self.build_xml('createTransactionRequest', OrderedDict([
            ('transactionRequest', OrderedDict([
                ('transactionType', 'priorAuthCaptureTransaction'),
                ('amount', amount),
                ('refTransId', transaction.transaction_id),
                ])),
            ]))

        resp = xml_to_dict(xml_post(self.url, xml))
        transaction.auth_code = resp['transactionResponse']['authCode']
        return transaction

    def delete_card(self, card):
        xml = self.build_xml('deleteCustomerPaymentProfileRequest', OrderedDict([
            ('customerProfileId', card.customer_id),
            ('customerPaymentProfileId', card.card_id),
            ]))

        resp = xml_to_dict(xml_post(self.url, xml))
        self.check_for_error(resp)

########NEW FILE########
__FILENAME__ = base
class Gateway(object):
    """
    Implemented payment gateways should implement this interface.
    """

    def charge(self, price, options):
        raise NotImplementedError

    def void(self, transaction):
        raise NotImplementedError

    def refund(self, transaction, amount):
        raise NotImplementedError

    def retrieve(self, transaction_id):
        raise NotImplementedError

    def create_customer(self, options):
        raise NotImplementedError

    def update_customer(self, customer_id):
        raise NotImplementedError

    def delete_customer(self, customer_id):
        raise NotImplementedError

    def settle(self, transaction, amount):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = braintree_gateway
import re
import braintree
from braintree.exceptions import (
    NotFoundError,
    AuthenticationError as BraintreeAuthenticationError,
    )

from dinero.exceptions import *
from dinero.gateways.base import Gateway


# CVV RESPONSES
# M = Match
# N = Does not Match
# U = Not Verified
# I = Not Provided
# A = Not Applicable
CVV_SUCCESSFUL_RESPONSES = ['M']

# AVS POSTAL CODE RESPONSE CODE
# M = Matches
# N = Does not Match
# U = Not Verified
# I = Not Provided
# A = Not Applicable
AVS_ZIP_SUCCESSFUL_RESPONSES = ['M'],

# AVS STREET ADDRESS CODE RESPONSE CODE
# M = Matches
# N = Does not Match
# U = Not Verified
# I = Not Provided
# A = Not Applicable
AVS_ADDRESS_SUCCESSFUL_RESPONSES = ['M']


CREDITCARD_ERRORS = {
    '91701': [GatewayException],  # Cannot provide both a billing address and a billing address ID.
    '91702': [GatewayException],  # Billing address ID is invalid.
    '91704': [GatewayException],  # Customer ID is required.
    '91705': [GatewayException],  # Customer ID is invalid.
    '91708': [InvalidCardError],  # Cannot provide expiration_date if you are also providing expiration_month and expiration_year.
    '91718': [GatewayException],  # Token is invalid.
    '91719': [GatewayException],  # Credit card token is taken.
    '91720': [GatewayException],  # Credit card token is too long.
    '91721': [GatewayException],  # Token is not an allowed token.
    '91722': [GatewayException],  # Payment method token is required.
    '81723': [InvalidCardError],  # Cardholder name is too long.
    '81703': [InvalidCardError],  # Credit card type is not accepted by this merchant account.
    '81718': [GatewayException],  # Credit card number cannot be updated to an unsupported card type when it is associated to subscriptions.
    '81706': [InvalidCardError],  # CVV is required.
    '81707': [InvalidCardError],  # CVV must be 3 or 4 digits.
    '81709': [InvalidCardError],  # Expiration date is required.
    '81710': [InvalidCardError],  # Expiration date is invalid.
    '81711': [InvalidCardError],  # Expiration date year is invalid.
    '81712': [InvalidCardError],  # Expiration month is invalid.
    '81713': [InvalidCardError],  # Expiration year is invalid.
    '81714': [InvalidCardError],  # Credit card number is required.
    '81715': [InvalidTransactionError],  # Credit card number is invalid.
    '81716': [InvalidCardError],  # Credit card number must be 12-19 digits.
    '81717': [InvalidCardError],  # Credit card number is not an accepted test number.
    '91723': [GatewayException],  # Update Existing Token is invalid.
}

CUSTOMER_ERRORS = {
    '91602': [GatewayException],  # Custom field is invalid.
    '91609': [GatewayException],  # Customer ID has already been taken.
    '91610': [GatewayException],  # Customer ID is invalid.
    '91611': [GatewayException],  # Customer ID is not an allowed ID.
    '91612': [GatewayException],  # Customer ID is too long.
    '91613': [GatewayException],  # Id is required
    '81601': [GatewayException],  # Company is too long.
    '81603': [GatewayException],  # Custom field is too long.
    '81604': [GatewayException],  # Email is an invalid format.
    '81605': [GatewayException],  # Email is too long.
    '81606': [GatewayException],  # Email is required if sending a receipt.
    '81607': [GatewayException],  # Fax is too long.
    '81608': [GatewayException],  # First name is too long.
    '81613': [GatewayException],  # Last name is too long.
    '81614': [GatewayException],  # Phone is too long.
    '81615': [GatewayException],  # Website is too long.
    '81616': [GatewayException],  # Website is an invalid format.
}

ADDRESS_ERRORS = {
    '81801': [GatewayException],  # Address must have at least one field fill in.
    '81802': [GatewayException],  # Company is too long.
    '81804': [GatewayException],  # Extended address is too long.
    '81805': [GatewayException],  # First name is too long.
    '81806': [GatewayException],  # Last name is too long.
    '81807': [GatewayException],  # Locality is too long.
    '81813': [GatewayException],  # Postal code can only contain letters, numbers, spaces, and hyphens.
    '81808': [GatewayException],  # Postal code is required.
    '81809': [GatewayException],  # Postal code may contain no more than 9 letter or number characters.
    '81810': [GatewayException],  # Region is too long.
    '81811': [GatewayException],  # Street address is required.
    '81812': [GatewayException],  # Street address is too long.
    '91803': [GatewayException],  # Country name is not an accepted country.
    '91815': [GatewayException],  # Inconsistent country
    '91816': [GatewayException],  # Country code alpha-3 is not accepted
    '91817': [GatewayException],  # Country code numeric is not accepted
    '91814': [GatewayException],  # Country code alpha-2 is not accepted
    '91818': [GatewayException],  # Too many addresses per customer
}

TRANSACTION_ERRORS = {
    '81501': [InvalidAmountError],  # Amount cannot be negative.
    '81502': [InvalidAmountError],  # Amount is required.
    '81503': [InvalidAmountError],  # Amount is an invalid format.
    '81528': [InvalidAmountError],  # Amount is too large.
    '81509': [InvalidTransactionError],  # Credit card type is not accepted by this merchant account.
    '81527': [InvalidTransactionError],  # Custom field is too long.
    '91501': [InvalidTransactionError],  # Order ID is too long.
    '91530': [InvalidTransactionError],  # Cannot provide a billing address unless also providing a credit card.
    '91504': [RefundError],              # Transaction can only be voided if status is authorized or submitted_for_settlement.
    '91505': [RefundError],              # Cannot refund credit
    '91506': [RefundError],              # Cannot refund a transaction unless it is settled.
    '91507': [RefundError],              # Cannot submit for settlement unless status is authorized.
    '91508': [InvalidTransactionError],  # Need a customer_id, payment_method_token, credit_card, or subscription_id.
    '91526': [InvalidTransactionError],  # Custom field is invalid
    '91510': [InvalidTransactionError],  # Customer ID is invalid.
    '91511': [InvalidTransactionError],  # Customer does not have any credit cards.
    '91512': [InvalidTransactionError],  # Transaction has already been refunded.
    '91513': [InvalidTransactionError],  # Merchant account ID is invalid.
    '91514': [InvalidTransactionError],  # Merchant account is suspended.
    '91515': [InvalidTransactionError],  # Cannot provide both payment_method_token and credit_card attributes.
    '91516': [InvalidTransactionError],  # Cannot provide both payment_method_token and customer_id unless the payment_method belongs to the customer.
    '91527': [InvalidTransactionError],  # Cannot provide both payment_method_token and subscription_id unless the payment method belongs to the subscription.
    '91517': [InvalidTransactionError],  # Credit card type is not accepted by this merchant account.
    '91518': [InvalidTransactionError],  # Payment method token is invalid.
    '91519': [InvalidTransactionError],  # Processor authorization code cannot be set unless for a voice authorization.
    '91521': [InvalidTransactionError],  # Refund amount cannot be more than the authorized amount.
    '91538': [InvalidTransactionError],  # Cannot refund transaction with suspended merchant account.
    '91522': [InvalidTransactionError],  # Settlement amount cannot be more than the authorized amount.
    '91529': [InvalidTransactionError],  # Cannot provide both subscription_id and customer_id unless the subscription belongs to the customer.
    '91528': [InvalidTransactionError],  # Subscription ID is invalid.
    '91523': [InvalidTransactionError],  # Transaction type is invalid.
    '91524': [InvalidTransactionError],  # Transaction type is required.
    '91525': [InvalidTransactionError],  # Vault is disabled.
    '91531': [InvalidTransactionError],  # Subscription status must be past due
    '91547': [InvalidTransactionError],  # Merchant Account does not support refunds
    '81531': [InvalidAmountError],  # Amount must be greater than zero
    '81534': [InvalidAmountError],  # Tax amount cannot be negative.
    '81535': [InvalidAmountError],  # Tax amount is an invalid format.
    '81536': [InvalidAmountError],  # Tax amount is too large.
    '91537': [InvalidTransactionError],  # Purchase order number is too long.
    '91539': [InvalidTransactionError],  # Voice Authorization is not allowed for this card type
    '91540': [InvalidTransactionError],  # Transaction cannot be cloned if payment method is stored in vault
    '91541': [InvalidTransactionError],  # Cannot clone voice authorization transactions
    '91542': [InvalidTransactionError],  # Unsuccessful transaction cannot be cloned.
    '91543': [InvalidTransactionError],  # Credits cannot be cloned.
    '91544': [InvalidTransactionError],  # Cannot clone transaction without submit_for_settlement flag.
    '91545': [InvalidTransactionError],  # Voice Authorizations are not supported for this processor
    '91546': [InvalidTransactionError],  # Credits are not supported by this processor
    '91548': [InvalidTransactionError],  # Purchase order number is invalid
}

VALIDATION_ERRORS = {}  # all the dictionaries
VALIDATION_ERRORS.update(CREDITCARD_ERRORS)
VALIDATION_ERRORS.update(CUSTOMER_ERRORS)
VALIDATION_ERRORS.update(ADDRESS_ERRORS)
VALIDATION_ERRORS.update(TRANSACTION_ERRORS)

GATEWAY_REJECTION_REASONS = {
    'avs':         [AVSError],
    'avs_and_cvv': [AVSError, CVVError],
    'cvv':         [CVVError],
    'duplicate':   [DuplicateTransactionError],
}

PROCESSOR_RESPONSE_ERRORS = {
    '2000': [CardDeclinedError],          # Do Not Honor
    '2001': [CardDeclinedError],          # Insufficient Funds
    '2002': [CardDeclinedError],          # Limit Exceeded
    '2003': [CardDeclinedError],          # Cardholder's Activity Limit Exceeded
    '2004': [ExpiryError],                # Expired Card
    '2005': [InvalidCardError],           # Invalid Credit Card Number
    '2006': [ExpiryError],                # Invalid Expiration Date
    '2007': [InvalidCardError],           # No Account
    '2008': [InvalidCardError],           # Card Account Length Error
    '2009': [InvalidTransactionError],    # No Such Issuer
    '2010': [CVVError],                   # Card Issuer Declined CVV
    '2011': [CardDeclinedError],          # Voice Authorization Required
    '2012': [CardDeclinedError],          # Voice Authorization Required - Possible Lost Card
    '2013': [CardDeclinedError],          # Voice Authorization Required - Possible Stolen Card
    '2014': [CardDeclinedError],          # Voice Authorization Required - Fraud Suspected
    '2015': [CardDeclinedError],          # Transaction Not Allowed
    '2016': [DuplicateTransactionError],  # Duplicate Transaction
    '2017': [CardDeclinedError],          # Cardholder Stopped Billing
    '2018': [CardDeclinedError],          # Cardholder Stopped All Billing
    '2019': [InvalidTransactionError],    # Invalid Transaction
    '2020': [CardDeclinedError],          # Violation
    '2021': [CardDeclinedError],          # Security Violation
    '2022': [CardDeclinedError],          # Declined - Updated Cardholder Available
    '2023': [InvalidTransactionError],    # Processor Does Not Support This Feature
    '2024': [InvalidTransactionError],    # Card Type Not Enabled
    '2025': [InvalidTransactionError],    # Set Up Error - Merchant
    '2026': [InvalidTransactionError],    # Invalid Merchant ID
    '2027': [InvalidTransactionError],    # Set Up Error - Amount
    '2028': [InvalidTransactionError],    # Set Up Error - Hierarchy
    '2029': [InvalidTransactionError],    # Set Up Error - Card
    '2030': [InvalidTransactionError],    # Set Up Error - Terminal
    '2031': [InvalidTransactionError],    # Encryption Error
    '2032': [InvalidTransactionError],    # Surcharge Not Permitted
    '2033': [InvalidTransactionError],    # Inconsistent Data
    '2034': [InvalidTransactionError],    # No Action Taken
    '2035': [CardDeclinedError],          # Partial Approval For Amount In Group III Version
    '2036': [RefundError],                # Authorization could not be found to reverse
    '2037': [RefundError],                # Already Reversed
    '2038': [CardDeclinedError],          # Processor Declined
    '2039': [InvalidTransactionError],    # Invalid Authorization Code
    '2040': [InvalidTransactionError],    # Invalid Store
    '2041': [CardDeclinedError],          # Declined - Call For Approval
    '2043': [CardDeclinedError],          # Error - Do Not Retry, Call Issuer
    '2044': [CardDeclinedError],          # Declined - Call Issuer
    '2045': [CardDeclinedError],          # Invalid Merchant Number
    '2046': [CardDeclinedError],          # Declined
    '2047': [CardDeclinedError],          # Call Issuer. Pick Up Card.
    '2048': [InvalidAmountError],         # Invalid Amount
    '2049': [InvalidTransactionError],    # Invalid SKU Number
    '2050': [InvalidTransactionError],    # Invalid Credit Plan
    '2051': [InvalidTransactionError],    # Credit Card Number does not match method of payment
    '2052': [InvalidTransactionError],    # Invalid Level III Purchase
    '2053': [CardDeclinedError],          # Card reported as lost or stolen
    '2054': [RefundError],                # Reversal amount does not match authorization amount
    '2055': [InvalidTransactionError],    # Invalid Transaction Division Number
    '2056': [InvalidTransactionError],    # Transaction amount exceeds the transaction division limit
    '2057': [CardDeclinedError],          # Issuer or Cardholder has put a restriction on the card
    '2058': [CardDeclinedError],          # Merchant not MasterCard SecureCode enabled.
    '2059': [AVSError],                   # Address Verification Failed
    '2060': [AVSError, CVVError],         # Address Verification and Card Security Code Failed
}


def _convert_amount(price):
    if isinstance(price, str):
        amount = price
        price = float(price)
    else:
        amount = '%.2f' % float(price)
    return amount, price


def check_for_transaction_errors(result):
    if not result.is_success:
        if result.transaction:
            if result.transaction.gateway_rejection_reason:
                raise PaymentException([
                    # instantiate an exception for every class in GATEWAY_REJECTION_REASONS[result.transaction.gateway_rejection_reason]
                    error_class(result.transaction.processor_response_text) for error_class in GATEWAY_REJECTION_REASONS[result.transaction.gateway_rejection_reason]
                    ])
            if result.transaction.processor_response_code in PROCESSOR_RESPONSE_ERRORS:
                raise PaymentException([
                    # instantiate an exception for every class in PROCESSOR_RESPONSE_ERRORS[result.transaction.processor_response_code]
                    error_class(result.transaction.processor_response_text) for error_class in PROCESSOR_RESPONSE_ERRORS[result.transaction.processor_response_code]
                    ])
            raise PaymentException(result.transaction.processor_response_text)

        check_for_errors(result)


def check_for_errors(result):
    if not result.is_success:
        error_codes = {}
        for error in result.errors.deep_errors:
            if error.code in VALIDATION_ERRORS:
                error_codes[error.code] = [
                    # instantiate an exception for every class in VALIDATION_ERRORS[error.code]
                    error_class(error.message) for error_class in VALIDATION_ERRORS[error.code]
                    ]
            else:
                error_codes[error.code] = [GatewayException(error.message)]
        flattened_errors = []
        for errors in error_codes.values():
            flattened_errors.extend(errors)
        if not flattened_errors:
            PaymentException([result.message])
        raise PaymentException(flattened_errors)


class Braintree(Gateway):
    def __init__(self, options):
        environment = braintree.Environment.Sandbox  # TODO: autodetect live vs. test

        braintree.Configuration.configure(
                environment,
                options['merchant_id'],
                options['public_key'],
                options['private_key'],
                )

        # Auto-discover if this is a real account or a developer account.  Tries
        # to access both end points and see which one works.
        try:
            self.retrieve('0')
        except BraintreeAuthenticationError:
            environment = braintree.Environment.Production  # TODO: autodetect live vs. test

            braintree.Configuration.configure(
                    environment,
                    options['merchant_id'],
                    options['public_key'],
                    options['private_key'],
                    )
        except PaymentException:
            pass

    def charge(self, price, options):
        amount, price = _convert_amount(price)

        submit = {
            'amount': amount,
            'options': {
                'submit_for_settlement': True,
            },
        }

        if 'customer' in options:
            submit['customer_id'] = options['customer'].customer_id
            if 'credit_card_token' in options:
                submit['payment_method_token'] = options['credit_card_token']
        else:
            credit_card = {
                'number': str(options['number']),
                'expiration_month': str(options['month']).zfill(2),
                'expiration_year': str(options['year']),
            }
            if options.get('cvv'):
                credit_card['cvv'] = options['cvv']

            billing = {}
            billing_fields = {
                'first_name': 'first_name',
                'last_name': 'last_name',
                'street_address': 'address',
                'locality': 'city',
                'region': 'state',
                'postal_code': 'zip',
                'country_name': 'country',
            }
            for braintree_field, field in billing_fields.iteritems():
                if field in options:
                    billing[braintree_field] = options[field]

            customer = {}
            customer_fields = {
                'first_name': 'first_name',
                'last_name': 'last_name',
                'email': 'email',
                'website': 'website',
                'company': 'company',
            }
            for braintree_field, field in customer_fields.iteritems():
                if field in options:
                    customer[braintree_field] = options[field]

            submit['credit_card'] = credit_card
            submit['billing'] = billing
            if customer:
                submit['customer'] = customer

        result = braintree.Transaction.sale(submit)

        check_for_transaction_errors(result)
        return self._transaction_to_transaction_dict(result.transaction)

    def _transaction_to_transaction_dict(self, transaction):
        try:
            print transaction.customer
        except:
            pass

        ret = {
            'transaction_id': transaction.id,
            'avs_zip_successful': transaction.avs_postal_code_response_code in AVS_ZIP_SUCCESSFUL_RESPONSES,
            'avs_address_successful': transaction.avs_street_address_response_code in AVS_ADDRESS_SUCCESSFUL_RESPONSES,
            'cvv_successful': transaction.cvv_response_code in CVV_SUCCESSFUL_RESPONSES,
            'auth_code': transaction.processor_authorization_code,
            'price': transaction.amount,
            'account_number': transaction.credit_card_details.masked_number,
            'card_type': transaction.credit_card_details.card_type,
            'last_4': transaction.credit_card_details.last_4,
        }
        ret['avs_successful'] = ret['avs_zip_successful'] and ret['avs_address_successful']
        if transaction.customer:
            ret.update({
                'first_name': transaction.customer['first_name'],
                'last_name': transaction.customer['last_name'],
                'email': transaction.customer['email'],
                'website': transaction.customer['website'],
                'company': transaction.customer['company'],
                })

        if transaction.custom_fields:
            for field, value in transaction.custom_fields.iteritems():
                ret[field] = value

        return ret

    def void(self, transaction):
        try:
            result = braintree.Transaction.void(transaction.transaction_id)
        except NotFoundError as e:
            raise PaymentException([InvalidTransactionError(e)])

        check_for_transaction_errors(result)
        return True

    def refund(self, transaction, price):
        amount, price = _convert_amount(price)

        try:
            result = braintree.Transaction.refund(transaction.transaction_id, amount)
        except NotFoundError as e:
            raise PaymentException([InvalidTransactionError(e)])

        check_for_transaction_errors(result)
        return True

    def retrieve(self, transaction_id):
        try:
            result = braintree.Transaction.find(transaction_id)
        except NotFoundError as e:
            raise PaymentException([InvalidTransactionError(e)])

        return self._transaction_to_transaction_dict(result)

    def create_customer(self, options):
        customer, address, credit_card = self._create_all_from_dict(options)
        try:
            result = braintree.Customer.create(customer)
            check_for_errors(result)
            if address:
                address['customer_id'] = result.customer.id
                address_result = braintree.Address.create(address)
                if not address_result.is_success:
                    result.braintree.Customer.delete(result.customer.id)
                    check_for_errors(address_result)
                result.customer.addresses = [address_result.address]

            if credit_card:
                credit_card['customer_id'] = result.customer.id
                credit_card_result = braintree.CreditCard.create(credit_card)
                if not credit_card_result.is_success:
                    result.braintree.Customer.delete(result.customer.id)
                    check_for_errors(credit_card_result)
                result.customer.credit_cards = [credit_card_result.credit_card]

        except NotFoundError as e:
            raise PaymentException([InvalidTransactionError(e)])

        profile = {}
        profile.update(options)
        profile['customer_id'] = result.customer.id

        return profile

    def retrieve_customer(self, customer_id):
        try:
            customer_result = braintree.Customer.find(str(customer_id))
        except NotFoundError as e:
            raise CustomerNotFoundError(e)

        return self._customer_from_customer_result(customer_result)

    def delete_customer(self, customer_id):
        try:
            result = braintree.Customer.delete(str(customer_id))
        except NotFoundError as e:
            raise CustomerNotFoundError(e)

        check_for_errors(result)
        return True

    def update_customer(self, customer_id, options):
        customer, address, credit_card = self._create_all_from_dict(options)

        credit_card_token = None
        address_id = None
        try:
            credit_card_token = options['credit_card_token']
        except KeyError:
            customer_result = braintree.Customer.find(customer_id)
            if customer_result.credit_cards:
                credit_card_token = customer_result.credit_cards[0].token

        try:
            address_id = options['address_id']
        except KeyError:
            customer_result = braintree.Customer.find(customer_id)
            if customer_result.addresses:
                address_id = customer_result.addresses[0].id

        try:
            if customer:
                customer_result = braintree.Customer.update(customer_id, customer)
                check_for_errors(customer_result)

            if address and address_id:
                address_result = braintree.Address.update(customer_id, address_id, address)
                check_for_errors(address_result)

            if credit_card and credit_card_token:
                credit_card_result = braintree.CreditCard.update(credit_card_token, credit_card)
                check_for_errors(credit_card_result)
        except NotFoundError as e:
            raise CustomerNotFoundError(e)

        return True

    def _customer_from_customer_result(self, customer_result):
        ret = {}

        gets = {
            'customer_id':                 'id',
            'first_name':                  'first_name',
            'last_name':                   'last_name',
            'company':                     'company',
            'phone':                       'phone',
            'fax':                         'fax',
            'address':                     'addresses[0].street_address',
            'state':                       'addresses[0].locality',
            'city':                        'addresses[0].region',
            'zip':                         'addresses[0].postal_code',
            'country':                     'addresses[0].country_code_alpha2',
            'last_4':                      'credit_cards[0].last_4',
            # braintree specific
            'credit_card_token':           'credit_cards[0].token',
            'address_id':                  'addresses[0].id',
        }

        for key, kvp in gets.iteritems():
            try:
                kvp = kvp.replace('[', '.').replace(']', '')
                search = kvp.split('.')
                val = customer_result
                while search:
                    current_key = search.pop(0)
                    if re.match('[0-9]+$', current_key):
                        val = val[int(current_key)]
                    else:
                        val = getattr(val, current_key)

                ret[key] = val
            except KeyError:
                pass

        if 'last_4' in ret:
            ret['number'] = 'X' * 12 + ret['last_4']
            # now it's in the form "XXXXXXXXXXXX1234"

        return ret

    def _create_all_from_dict(self, options):
        customer = {}
        address = {}
        credit_card = {}

        customer_fields = {
            'email': 'email',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'company': 'company',
            'phone': 'phone',
            'fax': 'fax',
        }
        for field, braintree_field in customer_fields.iteritems():
            if field in options:
                customer[braintree_field] = options[field]

        address_fields = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'company': 'company',
            'address': 'street_address',
            'state': 'locality',
            'city': 'region',
            'zip': 'postal_code',
            'country': 'country_name',
        }
        for field, braintree_field in address_fields.iteritems():
            if field in options:
                address[braintree_field] = options[field]

        credit_card_fields = {
            # 'merchant_account_id': self.gateway_options['merchant_id'],
            'number': 'number',
            'month': 'expiration_month',
            'year': 'expiration_year',
        }
        for field, braintree_field in credit_card_fields.iteritems():
            if field in options:
                credit_card[braintree_field] = options[field]

        if address:
            credit_card['billing_address'] = address

        return customer, address, credit_card

########NEW FILE########
__FILENAME__ = log
import functools
import logging
import re
import time

logger = logging.getLogger('dinero')


def args_kwargs_to_call(args, kwargs):
    """
    Turns args (a list) and kwargs (a dict) into a string that looks like it could be used to call a function with positional and keyword arguments.

    >>> args_kwargs_to_call([1], {})
    '1'
    >>> args_kwargs_to_call([1,2], {})
    '1, 2'
    >>> args_kwargs_to_call([1], {'foo':'bar'})
    "1, foo='bar'"

    """
    ret = []
    for arg in args:
        if ret:
            ret.append(", ")
        ret.append(repr(arg))
    for k, v in kwargs.iteritems():
        if ret:
            ret.append(", ")
        ret.append("%s=%r" % (k, v))
    return ''.join(ret)


def log(fn):
    """
    Wraps fn in logging calls
    """
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        start_time = time.time()

        def logit(exception=None):
            if exception:
                exception_message = ' and raised %r' % exception
            else:
                exception_message = ''

            end_time = time.time()
            message = '%s(%s) took %s seconds%s' % (
                    fn.__name__,
                    args_kwargs_to_call(args, kwargs),
                    end_time - start_time,
                    exception_message)
            # remove any credit card numbers
            message = re.sub(r"\b([0-9])[0-9- ]{9,16}([0-9]{4})\b", r'\1XXXXXXXXX\2', message)
            logger.info(message)

        try:
            value = fn(*args, **kwargs)
            logit()
            return value
        except Exception as e:
            logit(e)
            raise

    return inner

########NEW FILE########
__FILENAME__ = ordereddict
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#     1. Redistributions of source code must retain the above copyright notice, 
#        this list of conditions and the following disclaimer.
#     
#     2. Redistributions in binary form must reproduce the above copyright 
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
# 
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import copy
from types import GeneratorType


class OrderedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.
    """
    def __new__(cls, *args, **kwargs):
        instance = super(OrderedDict, cls).__new__(cls, *args, **kwargs)
        instance.keyOrder = []
        return instance

    def __init__(self, data=None):
        if data is None:
            data = {}
        elif isinstance(data, GeneratorType):
            # Unfortunately we need to be able to read a generator twice.  Once
            # to get the data into self with our super().__init__ call and a
            # second time to setup keyOrder correctly
            data = list(data)
        super(OrderedDict, self).__init__(data)
        if isinstance(data, dict):
            self.keyOrder = data.keys()
        else:
            self.keyOrder = []
            seen = set()
            for key, value in data:
                if key not in seen:
                    self.keyOrder.append(key)
                    seen.add(key)

    def __deepcopy__(self, memo):
        return self.__class__([(key, copy.deepcopy(value, memo))
                               for key, value in self.iteritems()])

    def __setitem__(self, key, value):
        if key not in self:
            self.keyOrder.append(key)
        super(OrderedDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        return iter(self.keyOrder)

    def pop(self, k, *args):
        result = super(OrderedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(OrderedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def items(self):
        return zip(self.keyOrder, self.values())

    def iteritems(self):
        for key in self.keyOrder:
            yield key, self[key]

    def keys(self):
        return self.keyOrder[:]

    def iterkeys(self):
        return iter(self.keyOrder)

    def values(self):
        return map(self.__getitem__, self.keyOrder)

    def itervalues(self):
        for key in self.keyOrder:
            yield self[key]

    def update(self, dict_):
        for k, v in dict_.iteritems():
            self[k] = v

    def setdefault(self, key, default):
        if key not in self:
            self.keyOrder.append(key)
        return super(OrderedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Returns the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Inserts the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(OrderedDict, self).__setitem__(key, value)

    def copy(self):
        """Returns a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        obj = self.__class__(self)
        obj.keyOrder = self.keyOrder[:]
        return obj

    def __repr__(self):
        """
        Replaces the normal dict.__repr__ with a version that returns the keys
        in their sorted order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def clear(self):
        super(OrderedDict, self).clear()
        self.keyOrder = []

########NEW FILE########
__FILENAME__ = transaction
from dinero import exceptions, get_gateway
from dinero.log import log
from dinero.base import DineroObject


class Transaction(DineroObject):
    """
    :class:`Transaction` is an abstraction over payments in a gateway.  This is
    the interface for creating payments.
    """

    @classmethod
    @log
    def create(cls, price, gateway_name=None, **kwargs):
        """
        Creates a payment.  This method will actually charge your customer.
        :meth:`create` can be called in several different ways.

        You can call this with the credit card information directly. ::

            Transaction.create(
                price=200,
                number='4111111111111111',
                year='2015',
                month='12',

                # optional
                first_name='John',
                last_name='Smith,'
                zip='12345',
                address='123 Elm St',
                city='Denver',
                state='CO',
                cvv='900',
                email='johnsmith@example.com',
            )

        If you have a :class:`dinero.Customer` object, you can create a
        transaction against the customer. ::

            customer = Customer.create(
                ...
            )

            Transaction.create(
                price=200,
                customer=customer,
            )

        Other payment options include ``card`` and ``check``.  See
        :class:`dinero.CreditCard` for more information.
        """
        gateway = get_gateway(gateway_name)
        resp = gateway.charge(price, kwargs)
        return cls(gateway_name=gateway.name, **resp)

    @classmethod
    @log
    def retrieve(cls, transaction_id, gateway_name=None):
        """
        Fetches a transaction object from the gateway.
        """
        gateway = get_gateway(gateway_name)
        resp = gateway.retrieve(transaction_id)
        return cls(gateway_name=gateway.name, **resp)

    def __init__(self, gateway_name, price, transaction_id, **kwargs):
        self.gateway_name = gateway_name
        self.price = price
        self.transaction_id = transaction_id
        self.data = kwargs

    @log
    def refund(self, amount=None):
        """
        If ``amount`` is None dinero will refund the full price of the
        transaction.

        Payment gateways often allow you to refund only a certain amount of
        money from a transaction.  Refund abstracts the difference between
        refunding and voiding a payment so that normally you don't need to
        worry about it.  However, please note that you can only refund the
        entire amount of a transaction before it is settled.
        """
        gateway = get_gateway(self.gateway_name)

        # TODO: can this implementation live in dinero.gateways.AuthorizeNet?
        try:
            return gateway.refund(self, amount or self.price)
        except exceptions.PaymentException:
            if amount is None or amount == self.price:
                return gateway.void(self)
            else:
                raise exceptions.PaymentException(
                    "You cannot refund a transaction that hasn't been settled"
                    " unless you refund it for the full amount."
                )

    @log
    def settle(self, amount=None):
        """
        If you create a transaction without settling it, you can settle it with
        this method.  It is possible to settle only part of a transaction.  If
        ``amount`` is None, the full transaction price is settled.
        """
        gateway = get_gateway(self.gateway_name)
        return gateway.settle(self, amount or self.price)

    def __setattr__(self, attr, val):
        if attr in ['gateway_name', 'transaction_id', 'price', 'data']:
            self.__dict__[attr] = val
        else:
            self.data[attr] = val

    @classmethod
    def from_dict(cls, dict):
        return cls(dict['gateway_name'],
                   dict['price'],
                   dict['transaction_id'],
                   **dict['data']
                   )

    def __repr__(self):
        return "Transaction({gateway_name!r}, {price!r}, {transaction_id!r}, **{data!r})".format(**self.to_dict())

    def __eq__(self, other):
        if not isinstance(other, Transaction):
            return False
        return self.transaction_id == other.transaction_id

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# dinero documentation build configuration file, created by
# sphinx-quickstart on Wed Nov 14 14:29:00 2012.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'dinero'
copyright = u'2012, Fusionbox'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0.1'
# The full version, including alpha/beta/rc tags.
release = '0.0.1'

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
htmlhelp_basename = 'dinerodoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'dinero.tex', u'dinero Documentation',
   u'Fusionbox', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'dinero', u'dinero Documentation',
     [u'Fusionbox'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'dinero', u'dinero Documentation',
   u'Fusionbox', 'dinero', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'dinero'
epub_author = u'Fusionbox'
epub_publisher = u'Fusionbox'
epub_copyright = u'2012, Fusionbox'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

todo_include_todos = True

sys.path.insert(0, os.path.abspath('..'))

########NEW FILE########
__FILENAME__ = test_authorize
import os
import random
import dinero
from dinero.exceptions import *

## These tests require that you provide settings for authorize.net and set up
## your account to reject invalid CVV and AVS responses
try:
    import authorize_net_configuration
except ImportError:
    LOGIN_ID = os.environ["AUTHNET_LOGIN_ID"]
    TRANSACTION_KEY = os.environ["AUTHNET_TRANSACTION_KEY"]
    dinero.configure({
        'authorize.net': {
            'type': 'dinero.gateways.AuthorizeNet',
            'login_id': LOGIN_ID,
            'transaction_key': TRANSACTION_KEY,
            'default': True,
        }
    })


## For information on how to trigger specific errors, see http://community.developer.authorize.net/t5/Integration-and-Testing/Triggering-Specific-Transaction-Responses-Using-Test-Account/td-p/4361


def transact(desired_errors, price=None, number='4' + '1' * 15, month='12', year='2030', **kwargs):
    if not price:
        price = float(random.randint(1, 100000)) / 100

    try:
        transaction = dinero.Transaction.create(price, number=number, month=month, year=year, gateway_name='authorize.net', **kwargs)
    except PaymentException as e:
        if not desired_errors:
            print repr(e)
            assert False, e.message
        else:
            for error in desired_errors:
                assert error in e, str(error) + ' not in desired_errors'
    else:
        assert not desired_errors, 'was supposed to throw %s' % str(desired_errors)
        return transaction


def test_successful():
    transact([])


def test_successful_with_customer():
    transact([], customer_id=123, email='joeyjoejoejunior@example.com')


def test_successful_retrieve():
    transaction = transact([])
    transaction_retrieved = dinero.Transaction.retrieve(transaction.transaction_id, gateway_name='authorize.net')
    assert transaction == transaction_retrieved, 'Transactions are not "equal"'


def test_successful_retrieve_with_customer():
    transaction = transact([], customer_id=123, email='joeyjoejoejunior@example.com')
    transaction_retrieved = dinero.Transaction.retrieve(transaction.transaction_id, gateway_name='authorize.net')
    assert transaction == transaction_retrieved, 'Transactions are not "equal"'
    assert transaction_retrieved.customer_id == 123, 'Transaction.customer_id is not 123, it is %s' % repr(transaction_retrieved.customer_id)
    assert transaction_retrieved.email == 'joeyjoejoejunior@example.com', 'Transaction.email is not "joeyjoejoejunior@example.com", it is %s' % repr(transaction_retrieved.email)


def test_avs():
    # AVS data provided is invalid or AVS is not allowed for the card type that was used.
    transact([AVSError], zip=46203)

    # Address: No Match ZIP Code: No Match
    transact([AVSError], zip=46205)


def test_cvv():
    # CVV Code N, does not match
    transact([CVVError], cvv=901)


def test_cvv_and_avs():
    transact([CVVError, AVSError], cvv=901, zip=46203)


def test_expiry():
    transact([ExpiryError], year='2010')


def test_invalid_card():
    transact([InvalidCardError], number='4' + '1' * 14)


def test_invalid_card_and_expiry():
    transact([InvalidCardError, ExpiryError], number='4' + '1' * 14, month='12', year='2010')


def test_invalid_amount():
    transact([InvalidAmountError], -1)


def test_declined():
    transact([CardDeclinedError], zip=46282)


def test_duplicate():
    price = float(random.randint(100000, 1000000)) / 100
    transact([], price)
    transact([DuplicateTransactionError], price)


def test_cant_refund_unsettled():
    txn = transact([])
    try:
        dinero.get_gateway('authorize.net').refund(txn, txn.price)
    except PaymentException as e:
        assert RefundError in e
    else:
        assert False, "must raise an exception"


def test_cant_refund_more():
    txn = transact([])
    try:
        dinero.get_gateway('authorize.net').refund(txn, txn.price + 1)
    except PaymentException as e:
        assert RefundError in e
    else:
        assert False, "must raise an exception"


# def test_invalid_txn():
#     """
#     FAILS
#     """
#     txn = transact([])
#     txn.transaction_id = '0'
#     try:
#         dinero.get_gateway('authorize.net').refund(txn, txn.price)
#     except PaymentException as e:
#         assert InvalidTransactionError in e
#     else:
#         assert False, "must raise an exception"

########NEW FILE########
__FILENAME__ = test_authorize_customer
import os
import uuid
import datetime
import dinero
from dinero.exceptions import *

## These tests require that you provide settings for authorize.net and set up
## your account to reject invalid CVV and AVS responses
try:
    import authorize_net_configuration
except ImportError:
    LOGIN_ID = os.environ["AUTHNET_LOGIN_ID"]
    TRANSACTION_KEY = os.environ["AUTHNET_TRANSACTION_KEY"]
    dinero.configure({
        'authorize.net': {
            'type': 'dinero.gateways.AuthorizeNet',
            'login_id': LOGIN_ID,
            'transaction_key': TRANSACTION_KEY,
            'default': True,
        }
    })


## For information on how to trigger specific errors, see http://community.developer.authorize.net/t5/Integration-and-Testing/Triggering-Specific-Transaction-Responses-Using-Test-Account/td-p/4361


def test_create_delete_customer():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),

        'first_name': 'Joey',
        'last_name': 'Shabadoo',
        'company': 'Shabadoo, Inc.',
        'phone': '000-000-0000',
        'fax': '000-000-0001',
        'address': '123 somewhere st',
        'state': 'SW',
        'city': 'somewhere',
        'zip': '12345',
        'country': 'US',

        'number': '4' + '1' * 15,
        'month': '12',
        'year': str(datetime.date.today().year + 1),
    }

    customer = dinero.Customer.create(gateway_name='authorize.net', **options)
    try:
        assert customer.card_id, 'customer.card_id is not set'
    except AttributeError:
        assert False, 'customer.card_id is not set'
    for key, val in options.iteritems():
        try:
            assert val == getattr(customer, key), 'customer.%s != options[%s]' % (key, key)
        except AttributeError:
            assert False, 'customer.%s is not set' % key
    customer.delete()


def test_retrieve_nonexistant_customer():
    try:
        customer = dinero.Customer.retrieve(1234567890, gateway_name='authorize.net')
        if customer:
            customer.delete()
            customer = dinero.Customer.retrieve(1234567890, gateway_name='authorize.net')
    except CustomerNotFoundError:
        pass
    else:
        assert False, "CustomerNotFoundError expected"


def test_create_retrieve_delete_customer():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),

        'first_name': 'Joey',
        'last_name': 'Shabadoo',
        'company': 'Shabadoo, Inc.',
        'phone': '000-000-0000',
        'fax': '000-000-0001',
        'address': '123 somewhere st',
        'state': 'SW',
        'city': 'somewhere',
        'zip': '12345',
        'country': 'US',

        'number': '4' + '1' * 15,
        'month': '12',
        'year': str(datetime.date.today().year + 1),
    }

    customer = dinero.Customer.create(gateway_name='authorize.net', **options)
    customer = dinero.Customer.retrieve(customer.customer_id, gateway_name='authorize.net')
    customer.delete()


def test_CRUD_customer():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),

        'first_name': 'Joey',
        'last_name': 'Shabadoo',
        'company': 'Shabadoo, Inc.',
        'phone': '000-000-0000',
        'fax': '000-000-0001',
        'address': '123 somewhere st',
        'state': 'SW',
        'city': 'somewhere',
        'zip': '12345',
        'country': 'US',

        'number': '4' + '1' * 15,
        'month': '12',
        'year': str(datetime.date.today().year + 1),
    }
    new_company = 'Joey Junior, Inc.'

    customer = dinero.Customer.create(gateway_name='authorize.net', **options)
    customer_id = customer.customer_id

    customer = dinero.Customer.retrieve(customer_id, gateway_name='authorize.net')
    customer.company = new_company
    customer.save()

    customer = dinero.Customer.retrieve(customer_id, gateway_name='authorize.net')
    assert customer.company == new_company, 'Customer new_company is "%s" not "%s"' % (customer.company, new_company)
    customer.delete()


def test_create_customer_with_number_change():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),

        'first_name': 'Joey',
        'last_name': 'Shabadoo',
        'company': 'Shabadoo, Inc.',
        'phone': '000-000-0000',
        'fax': '000-000-0001',
        'address': '123 somewhere st',
        'state': 'SW',
        'city': 'somewhere',
        'zip': '12345',
        'country': 'US',

        'number': '4' + '1' * 15,
        'month': '12',
        'year': str(datetime.date.today().year + 1),
    }
    new_company = 'Joey Junior, Inc.'
    new_number = '4' + '2' * 15
    new_last_4_test = '2222'
    new_year = str(datetime.date.today().year + 2)
    new_month = '11'

    customer = dinero.Customer.create(gateway_name='authorize.net', **options)
    customer.company = new_company
    customer.number = new_number
    customer.year = new_year
    customer.month = new_month
    customer.save()

    customer = dinero.Customer.retrieve(customer.customer_id, gateway_name='authorize.net')
    customer.delete()

    assert customer.company == new_company, 'Customer new_company is "%s" not "%s"' % (customer.company, new_company)
    assert customer.last_4 == new_last_4_test, 'Customer new_last_4 is "%s" not "%s"' % (customer.last_4, new_last_4_test)


def test_CRUD_customer_with_number_change():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),

        'first_name': 'Joey',
        'last_name': 'Shabadoo',
        'company': 'Shabadoo, Inc.',
        'phone': '000-000-0000',
        'fax': '000-000-0001',
        'address': '123 somewhere st',
        'state': 'SW',
        'city': 'somewhere',
        'zip': '12345',
        'country': 'US',

        'number': '4' + '1' * 15,
        'month': '12',
        'year': str(datetime.date.today().year + 1),
    }
    new_company = 'Joey Junior, Inc.'
    new_number = '4' + '2' * 15
    new_last_4_test = '2222'
    new_year = str(datetime.date.today().year + 1)
    new_month = '12'

    customer = dinero.Customer.create(gateway_name='authorize.net', **options)
    customer_id = customer.customer_id

    customer = dinero.Customer.retrieve(customer_id, gateway_name='authorize.net')
    customer.company = new_company
    customer.number = new_number
    customer.year = new_year
    customer.month = new_month
    customer.save()

    customer = dinero.Customer.retrieve(customer_id, gateway_name='authorize.net')
    customer.delete()
    assert customer.company == new_company, 'Customer new_company is "%s" not "%s"' % (customer.company, new_company)
    assert customer.last_4 == new_last_4_test, 'Customer new_last_4 is "%s" not "%s"' % (customer.last_4, new_last_4_test)


def test_CRUD_customer_with_number_addition():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),
    }
    number = '4' + '2' * 15
    year = str(datetime.date.today().year + 1)
    month = '12'

    customer = dinero.Customer.create(gateway_name='authorize.net', **options)
    customer.number = number
    customer.year = year
    customer.month = month
    customer.save()
    customer.delete()

########NEW FILE########
__FILENAME__ = test_authorize_customer_errors
import os
import uuid
import dinero
from dinero.exceptions import *

## These tests require that you provide settings for authorize.net and set up
## your account to reject invalid CVV and AVS responses
try:
    import authorize_net_configuration
except ImportError:
    LOGIN_ID = os.environ["AUTHNET_LOGIN_ID"]
    TRANSACTION_KEY = os.environ["AUTHNET_TRANSACTION_KEY"]
    dinero.configure({
        'authorize.net': {
            'type': 'dinero.gateways.AuthorizeNet',
            'login_id': LOGIN_ID,
            'transaction_key': TRANSACTION_KEY,
            'default': True,
        }
    })


## For information on how to trigger specific errors, see http://community.developer.authorize.net/t5/Integration-and-Testing/Triggering-Specific-Transaction-Responses-Using-Test-Account/td-p/4361


def test_create_customer_no_email_error():
    options = {
    }

    try:
        customer = dinero.Customer.create(gateway_name='authorize.net', **options)
        customer.delete()
        assert False, "InvalidCustomerException should be raised"
    except InvalidCustomerException:
        pass


def test_create_customer_not_enough_payment_info_error():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),
        'number': '4' + '1' * 14
    }

    try:
        customer = dinero.Customer.create(gateway_name='authorize.net', **options)
        customer.delete()
        assert False
    except InvalidCardError:
        pass

########NEW FILE########
__FILENAME__ = test_authorize_customer_transactions
import os
import uuid
import datetime
import random
import dinero
from dinero.exceptions import *

## These tests require that you provide settings for authorize.net and set up
## your account to reject invalid CVV and AVS responses
try:
    import authorize_net_configuration
except ImportError:
    LOGIN_ID = os.environ["AUTHNET_LOGIN_ID"]
    TRANSACTION_KEY = os.environ["AUTHNET_TRANSACTION_KEY"]
    dinero.configure({
        'authorize.net': {
            'type': 'dinero.gateways.AuthorizeNet',
            'login_id': LOGIN_ID,
            'transaction_key': TRANSACTION_KEY,
            'default': True,
        }
    })


## For information on how to trigger specific errors, see http://community.developer.authorize.net/t5/Integration-and-Testing/Triggering-Specific-Transaction-Responses-Using-Test-Account/td-p/4361


def test_customer_transaction():
    options = {
        'email': '{0}@example.com'.format(uuid.uuid4()),
        'number': '4' + '1' * 15,
        'month': '12',
        'year': str(datetime.date.today().year + 1),
    }
    price = float(random.randint(1, 100000)) / 100

    customer = dinero.Customer.create(gateway_name='authorize.net', **options)
    transaction = dinero.Transaction.create(price, customer=customer, gateway_name='authorize.net')
    transaction.refund()
    customer.delete()

########NEW FILE########
__FILENAME__ = test_authorize_customer_xml
import os
import dinero
from dinero.exceptions import *
from lxml import etree

## These tests require that you provide settings for authorize.net and set up
## your account to reject invalid CVV and AVS responses
try:
    import authorize_net_configuration
except ImportError:
    LOGIN_ID = os.environ["AUTHNET_LOGIN_ID"]
    TRANSACTION_KEY = os.environ["AUTHNET_TRANSACTION_KEY"]
    dinero.configure({
        'authorize.net': {
            'type': 'dinero.gateways.AuthorizeNet',
            'login_id': LOGIN_ID,
            'transaction_key': TRANSACTION_KEY,
            'default': True,
        }
    })


## For information on how to trigger specific errors, see http://community.developer.authorize.net/t5/Integration-and-Testing/Triggering-Specific-Transaction-Responses-Using-Test-Account/td-p/4361


def trimmy(s):
    return ''.join(line.lstrip() for line in s.splitlines())


def test_minimum_create_customer_xml():
    gateway = dinero.get_gateway('authorize.net')
    options = {
        'email': 'someone@fusionbox.com',
    }
    xml = gateway._create_customer_xml(options)
    should_be = trimmy(
             """<createCustomerProfileRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
                              <merchantAuthentication>
                                  <name>{login_id}</name>
                                  <transactionKey>{transaction_key}</transactionKey>
                              </merchantAuthentication>
                              <profile>
                                  <email>someone@fusionbox.com</email>
                              </profile>
                          </createCustomerProfileRequest>""".format(
                        login_id=gateway.login_id,
                        transaction_key=gateway.transaction_key,
                    ))
    assert etree.tostring(xml) == should_be, 'Invalid XML'


def test_payment_create_customer_xml():
    gateway = dinero.get_gateway('authorize.net')
    options = {
        'email': 'someone@fusionbox.com',

        'number': '4' + '1' * 15,
        'month': '12',
        'year': '2012',
    }
    xml = gateway._create_customer_xml(options)
    should_be = trimmy(
             """<createCustomerProfileRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
                    <merchantAuthentication>
                        <name>{login_id}</name>
                        <transactionKey>{transaction_key}</transactionKey>
                    </merchantAuthentication>
                    <profile>
                        <email>someone@fusionbox.com</email>
                        <paymentProfiles>
                            <payment>
                                <creditCard>
                                    <cardNumber>4111111111111111</cardNumber>
                                    <expirationDate>2012-12</expirationDate>
                                </creditCard>
                            </payment>
                        </paymentProfiles>
                    </profile>
                </createCustomerProfileRequest>""".format(
                        login_id=gateway.login_id,
                        transaction_key=gateway.transaction_key,
                    ))
    assert etree.tostring(xml) == should_be, "Invalid XML (\n\t%s\n\t%s\n)" % (etree.tostring(xml), should_be)


def test_billto_create_customer_xml():
    gateway = dinero.get_gateway('authorize.net')
    options = {
        'email': 'someone@fusionbox.com',

        'first_name': 'Joey',
        'last_name': 'Shabadoo',
        'company': 'Shabadoo, Inc.',
        'phone': '000-000-0000',
        'fax': '000-000-0001',
        'address': '123 somewhere st',
        'state': 'SW',
        'city': 'somewhere',
        'zip': '12345',
        'country': 'US',
    }
    xml = gateway._create_customer_xml(options)
    should_be = trimmy(
             """<createCustomerProfileRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
                    <merchantAuthentication>
                        <name>{login_id}</name>
                        <transactionKey>{transaction_key}</transactionKey>
                    </merchantAuthentication>
                    <profile>
                        <email>someone@fusionbox.com</email>
                        <paymentProfiles>
                            <billTo>
                                <firstName>Joey</firstName>
                                <lastName>Shabadoo</lastName>
                                <company>Shabadoo, Inc.</company>
                                <address>123 somewhere st</address>
                                <city>somewhere</city>
                                <state>SW</state>
                                <zip>12345</zip>
                                <country>US</country>
                                <phoneNumber>000-000-0000</phoneNumber>
                                <faxNumber>000-000-0001</faxNumber>
                            </billTo>
                        </paymentProfiles>
                    </profile>
                </createCustomerProfileRequest>""".format(
                        login_id=gateway.login_id,
                        transaction_key=gateway.transaction_key,
                    ))
    assert etree.tostring(xml) == should_be, "Invalid XML (\n\t%s\n\t%s\n)" % (etree.tostring(xml), should_be)


def test_customer_create_xml():
    gateway = dinero.get_gateway('authorize.net')
    options = {
        'email': 'someone@fusionbox.com',

        'first_name': 'Joey',
        'last_name': 'Shabadoo',
        'company': 'Shabadoo, Inc.',
        'phone': '000-000-0000',
        'fax': '000-000-0001',
        'address': '123 somewhere st',
        'state': 'SW',
        'city': 'somewhere',
        'zip': '12345',
        'country': 'US',

        'number': '4' + '1' * 15,
        'month': '12',
        'year': '2012',
    }
    xml = gateway._create_customer_xml(options)
    should_be = trimmy(
             """<createCustomerProfileRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
                    <merchantAuthentication>
                        <name>{login_id}</name>
                        <transactionKey>{transaction_key}</transactionKey>
                    </merchantAuthentication>
                    <profile>
                        <email>someone@fusionbox.com</email>
                        <paymentProfiles>
                            <billTo>
                                <firstName>Joey</firstName>
                                <lastName>Shabadoo</lastName>
                                <company>Shabadoo, Inc.</company>
                                <address>123 somewhere st</address>
                                <city>somewhere</city>
                                <state>SW</state>
                                <zip>12345</zip>
                                <country>US</country>
                                <phoneNumber>000-000-0000</phoneNumber>
                                <faxNumber>000-000-0001</faxNumber>
                            </billTo>
                            <payment>
                                <creditCard>
                                    <cardNumber>4111111111111111</cardNumber>
                                    <expirationDate>2012-12</expirationDate>
                                </creditCard>
                            </payment>
                        </paymentProfiles>
                    </profile>
                </createCustomerProfileRequest>""".format(
                        login_id=gateway.login_id,
                        transaction_key=gateway.transaction_key,
                    ))
    assert etree.tostring(xml) == should_be, "Invalid XML (\n\t%s\n\t%s\n)" % (etree.tostring(xml), should_be)


def test_update_customer_xml():
    gateway = dinero.get_gateway('authorize.net')
    options = {
        'email': 'someone@fusionbox.com',
    }
    xml = gateway._update_customer_xml('123456789', options)
    should_be = trimmy(
             """<updateCustomerProfileRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
                    <merchantAuthentication>
                        <name>{login_id}</name>
                        <transactionKey>{transaction_key}</transactionKey>
                    </merchantAuthentication>
                    <profile>
                        <email>someone@fusionbox.com</email>
                        <customerProfileId>123456789</customerProfileId>
                    </profile>
                </updateCustomerProfileRequest>""".format(
                        login_id=gateway.login_id,
                        transaction_key=gateway.transaction_key,
                    ))
    assert etree.tostring(xml) == should_be, "Invalid XML (\n\t%s\n\t%s\n)" % (etree.tostring(xml), should_be)


def test_charge_customer_xml():
    gateway = dinero.get_gateway('authorize.net')
    price = 123.45
    customer_id = '123456789'
    card_id = '987654321'
    options = {
        'cvv': '123'
    }
    xml = gateway._charge_customer_xml(customer_id, card_id, price, options)
    should_be = trimmy(
             """<createCustomerProfileTransactionRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
                    <merchantAuthentication>
                        <name>{login_id}</name>
                        <transactionKey>{transaction_key}</transactionKey>
                    </merchantAuthentication>
                    <transaction>
                        <profileTransAuthCapture>
                            <amount>{price}</amount>
                            <customerProfileId>{customer_id}</customerProfileId>
                            <customerPaymentProfileId>{card_id}</customerPaymentProfileId>
                            <cardCode>{cvv}</cardCode>
                        </profileTransAuthCapture>
                    </transaction>
                </createCustomerProfileTransactionRequest>""".format(
                        login_id=gateway.login_id,
                        transaction_key=gateway.transaction_key,
                        price=price,
                        customer_id=customer_id,
                        card_id=card_id,
                        **options
                    ))
    assert etree.tostring(xml) == should_be, "Invalid XML (\n\t%s\n\t%s\n)" % (etree.tostring(xml), should_be)

########NEW FILE########
__FILENAME__ = test_xml_to_dict
from lxml import etree
import unittest
from pprint import pprint

from dinero.ordereddict import OrderedDict

import dinero


barebones = ("<root><a>b</a></root>", OrderedDict([('a', 'b')]))
simple = (
                """
                <root>
                  <x>
                    <a>Text</a>
                    <b>Something Else</b>
                  </x>
                </root>
                """,
                OrderedDict([
                    ('x', OrderedDict([
                        ('a', 'Text'),
                        ('b', 'Something Else'),
                        ])),
                    ])
                )
list_example = ("""
                <root>
                  <messages>
                    <message>1</message>
                    <message>2</message>
                    <message>3</message>
                    <message>
                      <a>Text</a>
                    </message>
                  </messages>
                </root>
                """,
                OrderedDict([
                    ('messages', OrderedDict([
                        ('message', [
                            '1',
                            '2',
                            '3',
                            OrderedDict([
                                ('a', 'Text'),
                                ]),
                            ]),
                        ])),
                    ])
                )
comprehensive = ("""
    <createTransactionResponse>
      <messages>
        <resultCode>Error</resultCode>
        <message>
          <code>E00027</code>
          <text>The transaction was unsuccessful.</text>
        </message>
      </messages>
      <transactionResponse>
        <responseCode>3</responseCode>
        <authCode/>
        <avsResultCode>P</avsResultCode>
        <cvvResultCode/>
        <cavvResultCode/>
        <transId>0</transId>
        <refTransID/>
        <transHash>D15F90A2DCF7B7FD7D15E220B7676708</transHash>
        <testRequest>0</testRequest>
        <accountNumber>XXXX1111</accountNumber>
        <accountType>Visa</accountType>
        <errors>
          <error>
            <errorCode>8</errorCode>
            <errorText>The credit card has expired.</errorText>
          </error>
        </errors>
      </transactionResponse>
    </createTransactionResponse>
    """,
    OrderedDict([
        ('messages', OrderedDict([
            ('resultCode', 'Error'),
            ('message', [
                OrderedDict([
                    ('code', 'E00027'),
                    ('text', 'The transaction was unsuccessful.'),
                    ]),
                ]),
            ]),
            ),
        ('transactionResponse', OrderedDict([
            ('responseCode', '3'),
            ('authCode', ''),
            ('avsResultCode', 'P'),
            ('cvvResultCode', ''),
            ('cavvResultCode', ''),
            ('transId', '0'),
            ('refTransID', ''),
            ('transHash', 'D15F90A2DCF7B7FD7D15E220B7676708'),
            ('testRequest', '0'),
            ('accountNumber', 'XXXX1111'),
            ('accountType', 'Visa'),
            ('errors', OrderedDict([
                ('error', [
                    OrderedDict([
                        ('errorCode', '8'),
                        ('errorText', 'The credit card has expired.'),
                        ]),
                    ])
                ]),
                ),
            ])),
        ])
    )


class TestXmlToDict(unittest.TestCase):
    def _test(self, xml, should):
        xml = etree.XML(xml)
        actual = dinero.gateways.authorizenet_gateway.xml_to_dict(xml)

        if actual != should:
            pprint(actual)
            pprint(should)
        assert actual == should

    def test_barebones(self):
        self._test(*barebones)

    def test_simple(self):
        self._test(*simple)

    def test_list(self):
        self._test(*list_example)

    def test_comprehensive(self):
        self._test(*comprehensive)


class TestDictToXml(unittest.TestCase):
    def _test(self, should, dict, root):
        import textwrap
        xml = etree.XML(textwrap.dedent(should))
        actual = dinero.gateways.authorizenet_gateway._dict_to_xml(root, dict)

        assert etree.tostring(actual, pretty_print=True) == \
                etree.tostring(xml, pretty_print=True)

    def test_barebones(self):
        self._test(*(barebones + ('root',)))

    def test_none_is_no_element(self):
        self._test(
                "<root></root>",
                OrderedDict([
                    ('whatever', None),
                    ]),
                'root')

    def test_simple(self):
        self._test(*(simple + ('root',)))

    def test_list(self):
        self._test(*(list_example + ('root',)))

    def test_comprehensive(self):
        self._test(*(comprehensive + ('createTransactionResponse',)))



########NEW FILE########
