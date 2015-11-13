__FILENAME__ = address
from braintree.successful_result import SuccessfulResult
from braintree.error_result import ErrorResult
from braintree.resource import Resource
from braintree.configuration import Configuration

class Address(Resource):
    """
    A class representing Braintree Address objects.

    An example of creating an address with all available fields::

        customer = braintree.Customer.create().customer
        result = braintree.Address.create({
            "customer_id": customer.id,
            "first_name": "John",
            "last_name": "Doe",
            "company": "Braintree",
            "street_address": "111 First Street",
            "extended_address": "Apartment 1",
            "locality": "Chicago",
            "region": "IL",
            "postal_code": "60606",
            "country_name": "United States of America"
        })

        print(result.customer.first_name)
        print(result.customer.last_name)
    """

    def __repr__(self):
        detail_list = ["customer_id", "street_address", "extended_address", "postal_code", "country_code_alpha2"]
        return super(Address, self).__repr__(detail_list)


    @staticmethod
    def create(params={}):
        """
        Create an Address.

        A customer_id is required::

            customer = braintree.Customer.create().customer
            result = braintree.Address.create({
                "customer_id": customer.id,
                "first_name": "John",
                ...
            })

        """

        return Configuration.gateway().address.create(params)

    @staticmethod
    def delete(customer_id, address_id):
        """
        Delete an address

        Given a customer_id and address_id::

            result = braintree.Address.delete("my_customer_id", "my_address_id")

        """

        return Configuration.gateway().address.delete(customer_id, address_id)

    @staticmethod
    def find(customer_id, address_id):
        """
        Find an address, given a customer_id and address_id. This does not return
        a result object. This will raise a :class:`NotFoundError <braintree.exceptions.not_found_error.NotFoundError>` if the provided
        customer_id/address_id are not found. ::

            address = braintree.Address.find("my_customer_id", "my_address_id")
        """
        return Configuration.gateway().address.find(customer_id, address_id)

    @staticmethod
    def update(customer_id, address_id, params={}):
        """
        Update an existing Address.

        A customer_id and address_id are required::

            result = braintree.Address.update("my_customer_id", "my_address_id", {
                "first_name": "John"
            })

        """

        return Configuration.gateway().address.update(customer_id, address_id, params)

    @staticmethod
    def create_signature():
        return ["company", "country_code_alpha2", "country_code_alpha3", "country_code_numeric",
                "country_name", "customer_id", "extended_address", "first_name",
                "last_name", "locality", "postal_code", "region", "street_address"]

    @staticmethod
    def update_signature():
        return Address.create_signature()

########NEW FILE########
__FILENAME__ = address_gateway
import re
import braintree
from braintree.address import Address
from braintree.error_result import ErrorResult
from braintree.exceptions.not_found_error import NotFoundError
from braintree.resource import Resource
from braintree.successful_result import SuccessfulResult

class AddressGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def create(self, params={}):
        Resource.verify_keys(params, Address.create_signature())
        if not "customer_id" in params:
            raise KeyError("customer_id must be provided")
        if not re.search("\A[0-9A-Za-z_-]+\Z", params["customer_id"]):
            raise KeyError("customer_id contains invalid characters")

        response = self.config.http().post("/customers/" + params.pop("customer_id") + "/addresses", {"address": params})
        if "address" in response:
            return SuccessfulResult({"address": Address(self.gateway, response["address"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def delete(self, customer_id, address_id):
        self.config.http().delete("/customers/" + customer_id + "/addresses/" + address_id)
        return SuccessfulResult()

    def find(self, customer_id, address_id):
        try:
            if customer_id == None or customer_id.strip() == "" or address_id == None or address_id.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/customers/" + customer_id + "/addresses/" + address_id)
            return Address(self.gateway, response["address"])
        except NotFoundError:
            raise NotFoundError("address for customer " + customer_id + " with id " + address_id + " not found")

    def update(self, customer_id, address_id, params={}):
        Resource.verify_keys(params, Address.update_signature())
        response = self.config.http().put(
            "/customers/" + customer_id + "/addresses/" + address_id,
            {"address": params}
        )
        if "address" in response:
            return SuccessfulResult({"address": Address(self.gateway, response["address"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])


########NEW FILE########
__FILENAME__ = add_on
from braintree.configuration import Configuration
from braintree.modification import Modification

class AddOn(Modification):
    @staticmethod
    def all():
        return Configuration.gateway().add_on.all()

########NEW FILE########
__FILENAME__ = add_on_gateway
import braintree
from braintree.add_on import AddOn
from braintree.resource_collection import ResourceCollection

class AddOnGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def all(self):
        response = self.config.http().get("/add_ons/")
        add_ons = {"add_on": response["add_ons"]}
        return [AddOn(self.gateway, item) for item in ResourceCollection._extract_as_array(add_ons, "add_on")]

########NEW FILE########
__FILENAME__ = attribute_getter
class AttributeGetter(object):
    def __init__(self, attributes={}):
        self._setattrs = []
        for key, val in attributes.iteritems():
            setattr(self, key, val)
            self._setattrs.append(key)

    def __repr__(self, detail_list=None):
        if detail_list is None:
            detail_list = self._setattrs

        details = ", ".join("%s: %r" % (attr, getattr(self, attr))
                                for attr in detail_list
                                    if hasattr(self, attr))
        return "<%s {%s} at %d>" % (self.__class__.__name__, details, id(self))

########NEW FILE########
__FILENAME__ = braintree_gateway
from braintree.add_on_gateway import AddOnGateway
from braintree.address_gateway import AddressGateway
from braintree.client_token_gateway import ClientTokenGateway
from braintree.credit_card_gateway import CreditCardGateway
from braintree.customer_gateway import CustomerGateway
from braintree.discount_gateway import DiscountGateway
from braintree.merchant_account_gateway import MerchantAccountGateway
from braintree.plan_gateway import PlanGateway
from braintree.settlement_batch_summary_gateway import SettlementBatchSummaryGateway
from braintree.subscription_gateway import SubscriptionGateway
from braintree.transaction_gateway import TransactionGateway
from braintree.transparent_redirect_gateway import TransparentRedirectGateway
from braintree.credit_card_verification_gateway import CreditCardVerificationGateway
from braintree.webhook_notification_gateway import WebhookNotificationGateway
from braintree.webhook_testing_gateway import WebhookTestingGateway

class BraintreeGateway(object):
    def __init__(self, config):
        self.config = config
        self.add_on = AddOnGateway(self)
        self.address = AddressGateway(self)
        self.client_token = ClientTokenGateway(self)
        self.credit_card = CreditCardGateway(self)
        self.customer = CustomerGateway(self)
        self.discount = DiscountGateway(self)
        self.merchant_account = MerchantAccountGateway(self)
        self.plan = PlanGateway(self)
        self.settlement_batch_summary = SettlementBatchSummaryGateway(self)
        self.subscription = SubscriptionGateway(self)
        self.transaction = TransactionGateway(self)
        self.transparent_redirect = TransparentRedirectGateway(self)
        self.verification = CreditCardVerificationGateway(self)
        self.webhook_notification = WebhookNotificationGateway(self)
        self.webhook_testing = WebhookTestingGateway(self)

########NEW FILE########
__FILENAME__ = client_token
import datetime
import json
import urllib
from braintree.configuration import Configuration
from braintree.signature_service import SignatureService
from braintree.util.crypto import Crypto
from braintree import exceptions

class ClientToken(object):

    @staticmethod
    def generate(params=None, gateway=None):

        if gateway is None:
            gateway = Configuration.gateway().client_token

        if params and "options" in params and not "customer_id" in params:
            for option in ["verify_card", "make_default", "fail_on_duplicate_payment_method"]:
                if option in params["options"]:
                    raise exceptions.InvalidSignatureError("cannot specify %s without a customer_id" % option)

        return gateway.generate(params)

    @staticmethod
    def generate_signature():
        return [
            "customer_id", "proxy_merchant_id",
            {"options": ["make_default", "verify_card", "fail_on_duplicate_payment_method"]}
        ]

########NEW FILE########
__FILENAME__ = client_token_gateway
import braintree
from braintree.client_token import ClientToken
from braintree.resource import Resource
from braintree import exceptions

class ClientTokenGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config


    def generate(self, params):
        if params:
            Resource.verify_keys(params, ClientToken.generate_signature())
            params = {'client_token': params}

        response = self.config.http().post("/client_token", params)

        if "client_token" in response:
            return response["client_token"]["value"]
        else:
            raise exceptions.ValueError(response["api_error_response"]["message"])

########NEW FILE########
__FILENAME__ = configuration
import os
import sys
import braintree
import braintree.util.http_strategy.pycurl_strategy
import braintree.util.http_strategy.httplib_strategy
import braintree.util.http_strategy.requests_strategy

class Configuration(object):
    """
    A class representing the configuration of your Braintree account.
    You must call configure before any other Braintree operations. ::

        braintree.Configuration.configure(
            braintree.Environment.Sandbox,
            "your_merchant_id",
            "your_public_key",
            "your_private_key"
        )

    By default, every request to the Braintree servers verifies the SSL connection
    using the `PycURL <http://pycurl.sourceforge.net/>`_
    library.  This ensures valid encryption of data and prevents man-in-the-middle attacks.

    If you are in an environment where you absolutely cannot load `PycURL <http://pycurl.sourceforge.net/>`_, you
    can turn off SSL Verification by setting::

        Configuration.use_unsafe_ssl = True

    This is highly discouraged, however, since it leaves you susceptible to
    man-in-the-middle attacks.

    If you are using Google App Engine, you must use unsafe ssl [1]_::

        The proxy the URL Fetch service uses cannot authenticate the host it
        is contacting. Because there is no certificate trust chain, the proxy
        accepts all certificates, including self-signed certificates. The
        proxy server cannot detect "man in the middle" attacks between App
        Engine and the remote host when using HTTPS.

.. [1] `URL Fetch Python API Overview <https://developers.google.com/appengine/docs/python/urlfetch/overview>`_
    """
    use_unsafe_ssl = False

    @staticmethod
    def configure(environment, merchant_id, public_key, private_key, http_strategy=None):
        Configuration.environment = environment
        Configuration.merchant_id = merchant_id
        Configuration.public_key = public_key
        Configuration.private_key = private_key
        Configuration.default_http_strategy = http_strategy

    @staticmethod
    def for_partner(environment, partner_id, public_key, private_key, http_strategy=None):
        return Configuration(
            environment=environment,
            merchant_id=partner_id,
            public_key=public_key,
            private_key=private_key,
            http_strategy=http_strategy
        )

    @staticmethod
    def gateway():
        return braintree.braintree_gateway.BraintreeGateway(Configuration.instantiate())

    @staticmethod
    def instantiate():
        return Configuration(
            environment=Configuration.environment,
            merchant_id=Configuration.merchant_id,
            public_key=Configuration.public_key,
            private_key=Configuration.private_key,
            http_strategy=Configuration.default_http_strategy
        )

    @staticmethod
    def api_version():
        return "3"

    def __init__(self, environment, merchant_id, public_key, private_key, http_strategy=None):
        self.environment = environment
        self.merchant_id = merchant_id
        self.public_key = public_key
        self.private_key = private_key

        if http_strategy:
            self._http_strategy = http_strategy(self, self.environment)
        else:
            self._http_strategy = self.__determine_http_strategy()

    def base_merchant_path(self):
        return "/merchants/" + self.merchant_id

    def base_merchant_url(self):
        return self.environment.protocol + self.environment.server_and_port + self.base_merchant_path()

    def http(self):
        return braintree.util.http.Http(self)

    def http_strategy(self):
        if Configuration.use_unsafe_ssl:
            return braintree.util.http_strategy.httplib_strategy.HttplibStrategy(self, self.environment)
        else:
            return self._http_strategy

    def __determine_http_strategy(self):
        if "PYTHON_HTTP_STRATEGY" in os.environ:
            return self.__http_strategy_from_environment()

        if sys.version_info[0] == 2 and sys.version_info[1] == 5:
            return braintree.util.http_strategy.pycurl_strategy.PycurlStrategy(self, self.environment)
        else:
            return braintree.util.http_strategy.requests_strategy.RequestsStrategy(self, self.environment)

    def __http_strategy_from_environment(self):
        strategy_name = os.environ["PYTHON_HTTP_STRATEGY"]
        if strategy_name == "httplib":
            return braintree.util.http_strategy.httplib_strategy.HttplibStrategy(self, self.environment)
        elif strategy_name == "pycurl":
            return braintree.util.http_strategy.pycurl_strategy.PycurlStrategy(self, self.environment)
        elif strategy_name == "requests":
            return braintree.util.http_strategy.requests_strategy.RequestsStrategy(self, self.environment)
        else:
            raise ValueError("invalid http strategy")

########NEW FILE########
__FILENAME__ = credit_card
import braintree
import warnings
from braintree.resource import Resource
from braintree.address import Address
from braintree.configuration import Configuration
from braintree.transparent_redirect import TransparentRedirect

class CreditCard(Resource):
    """
    A class representing Braintree CreditCard objects.

    An example of creating an credit card with all available fields::

        result = braintree.CreditCard.create({
            "cardholder_name": "John Doe",
            "cvv": "123",
            "expiration_date": "12/2012",
            "number": "4111111111111111",
            "token": "my_token",
            "billing_address": {
                "first_name": "John",
                "last_name": "Doe",
                "company": "Braintree",
                "street_address": "111 First Street",
                "extended_address": "Unit 1",
                "locality": "Chicago",
                "postal_code": "60606",
                "region": "IL",
                "country_name": "United States of America"
            },
            "options": {
                "verify_card": True
            }
        })

        print(result.credit_card.token)
        print(result.credit_card.masked_number)

    For more information on CreditCards, see https://www.braintreepayments.com/docs/python/credit_cards/create

    """
    class CardType(object):
        """
        Contants representing the type of the credit card.  Available types are:

        * Braintree.CreditCard.AmEx
        * Braintree.CreditCard.CarteBlanche
        * Braintree.CreditCard.ChinaUnionPay
        * Braintree.CreditCard.DinersClubInternational
        * Braintree.CreditCard.Discover
        * Braintree.CreditCard.JCB
        * Braintree.CreditCard.Laser
        * Braintree.CreditCard.Maestro
        * Braintree.CreditCard.MasterCard
        * Braintree.CreditCard.Solo
        * Braintree.CreditCard.Switch
        * Braintree.CreditCard.Visa
        * Braintree.CreditCard.Unknown
        """

        AmEx = "American Express"
        CarteBlanche = "Carte Blanche"
        ChinaUnionPay = "China UnionPay"
        DinersClubInternational = "Diners Club"
        Discover = "Discover"
        JCB = "JCB"
        Laser = "Laser"
        Maestro = "Maestro"
        MasterCard = "MasterCard"
        Solo = "Solo"
        Switch = "Switch"
        Visa = "Visa"
        Unknown = "Unknown"

    class CustomerLocation(object):
        """
        Contants representing the issuer location of the credit card.  Available locations are:

        * braintree.CreditCard.CustomerLocation.International
        * braintree.CreditCard.CustomerLocation.US
        """

        International = "international"
        US = "us"

    class CardTypeIndicator(object):
        """
        Constants representing the three states for the card type indicator attributes

        * braintree.CreditCard.CardTypeIndicator.Yes
        * braintree.CreditCard.CardTypeIndicator.No
        * braintree.CreditCard.CardTypeIndicator.Unknown
        """
        Yes = "Yes"
        No = "No"
        Unknown = "Unknown"

    Commercial = DurbinRegulated = Debit = Healthcare = \
            CountryOfIssuance = IssuingBank = Payroll = Prepaid = CardTypeIndicator

    @staticmethod
    def confirm_transparent_redirect(query_string):
        """
        Confirms a transparent redirect request. It expects the query string from the
        redirect request. The query string should _not_ include the leading "?" character. ::

            result = braintree.CreditCard.confirm_transparent_redirect_request("foo=bar&id=12345")
        """

        warnings.warn("Please use TransparentRedirect.confirm instead", DeprecationWarning)
        return Configuration.gateway().credit_card.confirm_transparent_redirect(query_string)

    @staticmethod
    def create(params={}):
        """
        Create a CreditCard.

        A number and expiration_date are required. ::

            result = braintree.CreditCard.create({
                "number": "4111111111111111",
                "expiration_date": "12/2012"
            })

        """

        return Configuration.gateway().credit_card.create(params)

    @staticmethod
    def update(credit_card_token, params={}):
        """
        Update an existing CreditCard

        By credit_card_id.  The params are similar to create::

            result = braintree.CreditCard.update("my_credit_card_id", {
                "cardholder_name": "John Doe"
            })

        """

        return Configuration.gateway().credit_card.update(credit_card_token, params)

    @staticmethod
    def delete(credit_card_token):
        """
        Delete a credit card

        Given a credit_card_id::

            result = braintree.CreditCard.delete("my_credit_card_id")

        """

        return Configuration.gateway().credit_card.delete(credit_card_token)

    @staticmethod
    def expired():
        """ Return a collection of expired credit cards. """
        return Configuration.gateway().credit_card.expired()

    @staticmethod
    def expiring_between(start_date, end_date):
        """ Return a collection of credit cards expiring between the given dates. """
        return Configuration.gateway().credit_card.expiring_between(start_date, end_date)

    @staticmethod
    def find(credit_card_token):
        """
        Find a credit card, given a credit_card_id. This does not return
        a result object. This will raise a :class:`NotFoundError <braintree.exceptions.not_found_error.NotFoundError>` if the provided
        credit_card_id is not found. ::

            credit_card = braintree.CreditCard.find("my_credit_card_token")
        """
        return Configuration.gateway().credit_card.find(credit_card_token)

    @staticmethod
    def from_nonce(nonce):
        """
        Convert a payment method nonce into a CreditCard. This does not return
        a result object. This will raise a :class:`NotFoundError <braintree.exceptions.not_found_error.NotFoundError>` if the provided
        credit_card_id is not found. ::

            credit_card = braintree.CreditCard.from_nonce("my_payment_method_nonce")
        """
        return Configuration.gateway().credit_card.from_nonce(nonce)

    @staticmethod
    def create_signature():
        return CreditCard.signature("create")

    @staticmethod
    def update_signature():
        return CreditCard.signature("update")

    @staticmethod
    def signature(type):
        billing_address_params = [
            "company", "country_code_alpha2", "country_code_alpha3", "country_code_numeric", "country_name",
            "extended_address", "first_name", "last_name", "locality", "postal_code", "region", "street_address"
        ]
        options = ["make_default", "verification_merchant_account_id", "verify_card", "venmo_sdk_session"]

        signature = [
            "billing_address_id", "cardholder_name", "cvv", "expiration_date", "expiration_month", "expiration_year",
            "device_session_id", "fraud_merchant_id", "number", "token", "venmo_sdk_payment_method_code", "device_data",
            "payment_method_nonce",
            {"billing_address": billing_address_params},
            {"options": options}
        ]

        if type == "create":
            signature.append("customer_id")
            options.append("fail_on_duplicate_payment_method")
        elif type == "update":
            billing_address_params.append({"options": ["update_existing"]})
        elif type == "update_via_customer":
            options.append("update_existing_token")
            billing_address_params.append({"options": ["update_existing"]})
        else:
            raise AttributeError

        return signature

    @staticmethod
    def transparent_redirect_create_url():
        """
        Returns the url to use for creating CreditCards through transparent redirect.
        """
        warnings.warn("Please use TransparentRedirect.url instead", DeprecationWarning)
        return Configuration.gateway().credit_card.transparent_redirect_create_url()

    @staticmethod
    def tr_data_for_create(tr_data, redirect_url):
        """
        Builds tr_data for CreditCard creation.
        """

        return Configuration.gateway().credit_card.tr_data_for_create(tr_data, redirect_url)

    @staticmethod
    def tr_data_for_update(tr_data, redirect_url):
        """
        Builds tr_data for CreditCard updating.
        """

        return Configuration.gateway().credit_card.tr_data_for_update(tr_data, redirect_url)

    @staticmethod
    def transparent_redirect_update_url():
        """
        Returns the url to be used for updating CreditCards through transparent redirect.
        """
        warnings.warn("Please use TransparentRedirect.url instead", DeprecationWarning)
        return Configuration.gateway().credit_card.transparent_redirect_update_url()

    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)
        self.is_expired = self.expired
        if "billing_address" in attributes:
            self.billing_address = Address(gateway, self.billing_address)
        else:
            self.billing_address = None

        if "subscriptions" in attributes:
            self.subscriptions = [braintree.subscription.Subscription(gateway, subscription) for subscription in self.subscriptions]

    @property
    def expiration_date(self):
        return self.expiration_month + "/" + self.expiration_year

    @property
    def masked_number(self):
        """
        Returns the masked number of the CreditCard.
        """
        return self.bin + "******" + self.last_4


########NEW FILE########
__FILENAME__ = credit_card_gateway
import braintree
from braintree.credit_card import CreditCard
from braintree.error_result import ErrorResult
from braintree.exceptions.not_found_error import NotFoundError
from braintree.ids_search import IdsSearch
from braintree.resource import Resource
from braintree.resource_collection import ResourceCollection
from braintree.successful_result import SuccessfulResult
from braintree.transparent_redirect import TransparentRedirect

class CreditCardGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def confirm_transparent_redirect(self, query_string):
        id = self.gateway.transparent_redirect._parse_and_validate_query_string(query_string)["id"][0]
        return self._post("/payment_methods/all/confirm_transparent_redirect_request", {"id": id})

    def create(self, params={}):
        Resource.verify_keys(params, CreditCard.create_signature())
        return self._post("/payment_methods", {"credit_card": params})

    def delete(self, credit_card_token):
        self.config.http().delete("/payment_methods/" + credit_card_token)
        return SuccessfulResult()

    def expired(self):
        response = self.config.http().post("/payment_methods/all/expired_ids")
        return ResourceCollection(None, response, self.__fetch_expired)

    def expiring_between(self, start_date, end_date):
        formatted_start_date = start_date.strftime("%m%Y")
        formatted_end_date = end_date.strftime("%m%Y")
        query = "start=%s&end=%s" % (formatted_start_date, formatted_end_date)
        response = self.config.http().post("/payment_methods/all/expiring_ids?" + query)
        return ResourceCollection(query, response, self.__fetch_existing_between)

    def find(self, credit_card_token):
        try:
            if credit_card_token == None or credit_card_token.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/payment_methods/" + credit_card_token)
            return CreditCard(self.gateway, response["credit_card"])
        except NotFoundError:
            raise NotFoundError("payment method with token " + credit_card_token + " not found")

    def from_nonce(self, nonce):
        try:
            if nonce == None or nonce.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/payment_methods/from_nonce/" + nonce)
            return CreditCard(self.gateway, response["credit_card"])
        except NotFoundError:
            raise NotFoundError("payment method with nonce " + nonce + " locked, consumed or not found")

    def tr_data_for_create(self, tr_data, redirect_url):
        Resource.verify_keys(tr_data, [{"credit_card": CreditCard.create_signature()}])
        tr_data["kind"] = TransparentRedirect.Kind.CreatePaymentMethod
        return self.gateway.transparent_redirect.tr_data(tr_data, redirect_url)

    def tr_data_for_update(self, tr_data, redirect_url):
        Resource.verify_keys(tr_data, ["payment_method_token", {"credit_card": CreditCard.update_signature()}])
        tr_data["kind"] = TransparentRedirect.Kind.UpdatePaymentMethod
        return self.gateway.transparent_redirect.tr_data(tr_data, redirect_url)

    def transparent_redirect_create_url(self):
        return self.config.base_merchant_url() + "/payment_methods/all/create_via_transparent_redirect_request"

    def transparent_redirect_update_url(self):
        return self.config.base_merchant_url() + "/payment_methods/all/update_via_transparent_redirect_request"

    def update(self, credit_card_token, params={}):
        Resource.verify_keys(params, CreditCard.update_signature())
        response = self.config.http().put("/payment_methods/" + credit_card_token, {"credit_card": params})
        if "credit_card" in response:
            return SuccessfulResult({"credit_card": CreditCard(self.gateway, response["credit_card"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def __fetch_expired(self, query, ids):
        criteria = {}
        criteria["ids"] = IdsSearch.ids.in_list(ids).to_param()
        response = self.config.http().post("/payment_methods/all/expired", {"search": criteria})
        return [CreditCard(self.gateway, item) for item in ResourceCollection._extract_as_array(response["payment_methods"], "credit_card")]

    def __fetch_existing_between(self, query, ids):
        criteria = {}
        criteria["ids"] = IdsSearch.ids.in_list(ids).to_param()
        response = self.config.http().post("/payment_methods/all/expiring?" + query, {"search": criteria})
        return [CreditCard(self.gateway, item) for item in ResourceCollection._extract_as_array(response["payment_methods"], "credit_card")]

    def _post(self, url, params={}):
        response = self.config.http().post(url, params)
        if "credit_card" in response:
            return SuccessfulResult({"credit_card": CreditCard(self.gateway, response["credit_card"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])


########NEW FILE########
__FILENAME__ = credit_card_verification
from braintree.attribute_getter import AttributeGetter
from braintree.configuration import Configuration

class CreditCardVerification(AttributeGetter):

    class Status(object):
        """
        Constants representing transaction statuses. Available statuses are:

        * braintree.CreditCardVerification.Status.Failed
        * braintree.CreditCardVerification.Status.GatewayRejected
        * braintree.CreditCardVerification.Status.ProcessorDeclined
        * braintree.CreditCardVerification.Status.Unrecognized
        * braintree.CreditCardVerification.Status.Verified
        """

        Failed                 = "failed"
        GatewayRejected        = "gateway_rejected"
        ProcessorDeclined      = "processor_declined"
        Unrecognized           = "unrecognized"
        Verified               = "verified"

    def __init__(self, gateway, attributes):
        AttributeGetter.__init__(self, attributes)
        if "processor_response_code" not in attributes:
            self.processor_response_code = None
        if "processor_response_text" not in attributes:
            self.processor_response_text = None

    @staticmethod
    def find(verification_id):
        return Configuration.gateway().verification.find(verification_id)

    @staticmethod
    def search(*query):
        return Configuration.gateway().verification.search(*query)

    def __eq__(self, other):
        if not isinstance(other, CreditCardVerification):
            return False
        return self.id == other.id

########NEW FILE########
__FILENAME__ = credit_card_verification_gateway
from braintree.credit_card_verification import CreditCardVerification
from braintree.credit_card_verification_search import CreditCardVerificationSearch
from braintree.exceptions.not_found_error import NotFoundError
from braintree.ids_search import IdsSearch
from braintree.resource_collection import ResourceCollection

class CreditCardVerificationGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def find(self, verification_id):
        try:
            if verification_id == None or verification_id.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/verifications/" + verification_id)
            return CreditCardVerification(self.gateway, response["verification"])
        except NotFoundError:
            raise NotFoundError("Verification with id " + verification_id + " not found")

    def __criteria(self, query):
        criteria = {}
        for term in query:
            if criteria.get(term.name):
                criteria[term.name] = dict(criteria[term.name].items() + term.to_param().items())
            else:
                criteria[term.name] = term.to_param()
        return criteria

    def __fetch(self, query, ids):
        criteria = self.__criteria(query)
        criteria["ids"] = CreditCardVerificationSearch.ids.in_list(ids).to_param()
        response = self.config.http().post("/verifications/advanced_search", {"search": criteria})
        return [CreditCardVerification(self.gateway, item) for item in
                ResourceCollection._extract_as_array(response["credit_card_verifications"], "verification")]


    def search(self, *query):
        if isinstance(query[0], list):
            query = query[0]

        response = self.config.http().post("/verifications/advanced_search_ids", {"search": self.__criteria(query)})
        return ResourceCollection(query, response, self.__fetch)

    def __fetch_verifications(self, query, verification_ids):
        criteria = {}
        criteria["ids"] = IdsSearch.ids.in_list(verification_ids).to_param()
        response = self.config.http().post("/verifications/advanced_search", {"search": criteria})
        return [CreditCardVerification(self.gateway, item) for item in ResourceCollection._extract_as_array(response["credit_card_verifications"], "verification")]

########NEW FILE########
__FILENAME__ = credit_card_verification_search
from braintree.credit_card import CreditCard
from braintree.search import Search
from braintree.util import Constants

class CreditCardVerificationSearch:
    credit_card_cardholder_name  = Search.TextNodeBuilder("credit_card_cardholder_name")
    id                           = Search.TextNodeBuilder("id")
    credit_card_expiration_date  = Search.EqualityNodeBuilder("credit_card_expiration_date")
    credit_card_number           = Search.PartialMatchNodeBuilder("credit_card_number")
    status                       = Search.MultipleValueNodeBuilder("credit_card_type", Constants.get_all_constant_values_from_class(CreditCard.CardType))
    ids                          = Search.MultipleValueNodeBuilder("ids")
    created_at                   = Search.RangeNodeBuilder("created_at")

########NEW FILE########
__FILENAME__ = customer
import warnings
from braintree.util.http import Http
from braintree.successful_result import SuccessfulResult
from braintree.error_result import ErrorResult
from braintree.resource import Resource
from braintree.credit_card import CreditCard
from braintree.address import Address
from braintree.configuration import Configuration
from braintree.ids_search import IdsSearch
from braintree.exceptions.not_found_error import NotFoundError
from braintree.resource_collection import ResourceCollection
from braintree.transparent_redirect import TransparentRedirect

class Customer(Resource):
    """
    A class representing a customer.

    An example of creating an customer with all available fields::

        result = braintree.Customer.create({
            "id": "my_customer_id",
            "company": "Some company",
            "email": "john.doe@example.com",
            "fax": "123-555-1212",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "123-555-1221",
            "website": "http://www.example.com",
            "credit_card": {
                "cardholder_name": "John Doe",
                "cvv": "123",
                "expiration_date": "12/2012",
                "number": "4111111111111111",
                "token": "my_token",
                "billing_address": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "company": "Braintree",
                    "street_address": "111 First Street",
                    "extended_address": "Unit 1",
                    "locality": "Chicago",
                    "postal_code": "60606",
                    "region": "IL",
                    "country_name": "United States of America"
                },
                "options": {
                    "verify_card": True
                }
            },
            "custom_fields": {
                "my_key": "some value"
            }
        })

        print(result.customer.id)
        print(result.customer.first_name)

    For more information on Customers, see https://www.braintreepayments.com/docs/python/customers/create

    """

    def __repr__(self):
        detail_list = ["first_name", "last_name", "id"]
        return super(Customer, self).__repr__(detail_list)

    @staticmethod
    def all():
        """ Return a collection of all customers. """
        return Configuration.gateway().customer.all()

    @staticmethod
    def confirm_transparent_redirect(query_string):
        """
        Confirms a transparent redirect request.  It expects the query string from the
        redirect request.  The query string should _not_ include the leading "?" character. ::

            result = braintree.Customer.confirm_transparent_redirect_request("foo=bar&id=12345")
        """

        warnings.warn("Please use TransparentRedirect.confirm instead", DeprecationWarning)
        return Configuration.gateway().customer.confirm_transparent_redirect(query_string)

    @staticmethod
    def create(params={}):
        """
        Create a Customer

        No field is required::

            result = braintree.Customer.create({
                "company": "Some company",
                "first_name": "John"
            })

        """

        return Configuration.gateway().customer.create(params)

    @staticmethod
    def delete(customer_id):
        """
        Delete a customer

        Given a customer_id::

            result = braintree.Customer.delete("my_customer_id")

        """

        return Configuration.gateway().customer.delete(customer_id)

    @staticmethod
    def find(customer_id):
        """
        Find an customer, given a customer_id.  This does not return a result
        object.  This will raise a :class:`NotFoundError <braintree.exceptions.not_found_error.NotFoundError>` if the provided customer_id
        is not found. ::

            customer = braintree.Customer.find("my_customer_id")
        """

        return Configuration.gateway().customer.find(customer_id)

    @staticmethod
    def search(*query):
        return Configuration.gateway().customer.search(*query)

    @staticmethod
    def tr_data_for_create(tr_data, redirect_url):
        """ Builds tr_data for creating a Customer. """

        return Configuration.gateway().customer.tr_data_for_create(tr_data, redirect_url)

    @staticmethod
    def tr_data_for_update(tr_data, redirect_url):
        """ Builds tr_data for updating a Customer. """

        return Configuration.gateway().customer.tr_data_for_update(tr_data, redirect_url)

    @staticmethod
    def transparent_redirect_create_url():
        """ Returns the url to use for creating Customers through transparent redirect. """

        warnings.warn("Please use TransparentRedirect.url instead", DeprecationWarning)
        return Configuration.gateway().customer.transparent_redirect_create_url()

    @staticmethod
    def transparent_redirect_update_url():
        """ Returns the url to use for updating Customers through transparent redirect. """

        warnings.warn("Please use TransparentRedirect.url instead", DeprecationWarning)
        return Configuration.gateway().customer.transparent_redirect_update_url()

    @staticmethod
    def update(customer_id, params={}):
        """
        Update an existing Customer

        By customer_id. The params are similar to create::

            result = braintree.Customer.update("my_customer_id", {
                "last_name": "Smith"
            })

        """

        return Configuration.gateway().customer.update(customer_id, params)

    @staticmethod
    def create_signature():
        return [
            "company", "email", "fax", "first_name", "id", "last_name", "phone", "website", "device_data", "device_session_id", "fraud_merchant_id",
            {"credit_card": CreditCard.create_signature()},
            {"custom_fields": ["__any_key__"]}
        ]

    @staticmethod
    def update_signature():
        return [
            "company", "email", "fax", "first_name", "id", "last_name", "phone", "website", "device_data", "device_session_id", "fraud_merchant_id",
            {"credit_card": CreditCard.signature("update_via_customer")},
            {"custom_fields": ["__any_key__"]}
        ]

    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)
        if "credit_cards" in attributes:
            self.credit_cards = [CreditCard(gateway, credit_card) for credit_card in self.credit_cards]
        if "addresses" in attributes:
            self.addresses = [Address(gateway, address) for address in self.addresses]

########NEW FILE########
__FILENAME__ = customer_gateway
import braintree
from braintree.customer import Customer
from braintree.error_result import ErrorResult
from braintree.exceptions.not_found_error import NotFoundError
from braintree.ids_search import IdsSearch
from braintree.resource import Resource
from braintree.resource_collection import ResourceCollection
from braintree.successful_result import SuccessfulResult
from braintree.transparent_redirect import TransparentRedirect

class CustomerGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def all(self):
        response = self.config.http().post("/customers/advanced_search_ids")
        return ResourceCollection({}, response, self.__fetch)

    def confirm_transparent_redirect(self, query_string):
        id = self.gateway.transparent_redirect._parse_and_validate_query_string(query_string)["id"][0]
        return self._post("/customers/all/confirm_transparent_redirect_request", {"id": id})

    def create(self, params={}):
        Resource.verify_keys(params, Customer.create_signature())
        return self._post("/customers", {"customer": params})

    def delete(self, customer_id):
        self.config.http().delete("/customers/" + customer_id)
        return SuccessfulResult()

    def find(self, customer_id):
        try:
            if customer_id == None or customer_id.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/customers/" + customer_id)
            return Customer(self.gateway, response["customer"])
        except NotFoundError:
            raise NotFoundError("customer with id " + customer_id + " not found")

    def search(self, *query):
        if isinstance(query[0], list):
            query = query[0]

        response = self.config.http().post("/customers/advanced_search_ids", {"search": self.__criteria(query)})
        return ResourceCollection(query, response, self.__fetch)

    def tr_data_for_create(self, tr_data, redirect_url):
        Resource.verify_keys(tr_data, [{"customer": Customer.create_signature()}])
        tr_data["kind"] = TransparentRedirect.Kind.CreateCustomer
        return self.gateway.transparent_redirect.tr_data(tr_data, redirect_url)

    def tr_data_for_update(self, tr_data, redirect_url):
        Resource.verify_keys(tr_data, ["customer_id", {"customer": Customer.update_signature()}])
        tr_data["kind"] = TransparentRedirect.Kind.UpdateCustomer
        return self.gateway.transparent_redirect.tr_data(tr_data, redirect_url)

    def transparent_redirect_create_url(self):
        return self.config.base_merchant_url() + "/customers/all/create_via_transparent_redirect_request"

    def transparent_redirect_update_url(self):
        return self.config.base_merchant_url() + "/customers/all/update_via_transparent_redirect_request"

    def update(self, customer_id, params={}):
        Resource.verify_keys(params, Customer.update_signature())
        response = self.config.http().put("/customers/" + customer_id, {"customer": params})
        if "customer" in response:
            return SuccessfulResult({"customer": Customer(self.gateway, response["customer"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def __criteria(self, query):
        criteria = {}
        for term in query:
            if criteria.get(term.name):
                criteria[term.name] = dict(criteria[term.name].items() + term.to_param().items())
            else:
                criteria[term.name] = term.to_param()
        return criteria

    def __fetch(self, query, ids):
        criteria = self.__criteria(query)
        criteria["ids"] = braintree.customer_search.CustomerSearch.ids.in_list(ids).to_param()
        response = self.config.http().post("/customers/advanced_search", {"search": criteria})
        return [Customer(self.gateway, item) for item in ResourceCollection._extract_as_array(response["customers"], "customer")]

    def _post(self, url, params={}):
        response = self.config.http().post(url, params)
        if "customer" in response:
            return SuccessfulResult({"customer": Customer(self.gateway, response["customer"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])
        else:
            pass


########NEW FILE########
__FILENAME__ = customer_search
from braintree.search import Search

class CustomerSearch:
      address_extended_address             = Search.TextNodeBuilder("address_extended_address")
      address_first_name                   = Search.TextNodeBuilder("address_first_name")
      address_last_name                    = Search.TextNodeBuilder("address_last_name")
      address_locality                     = Search.TextNodeBuilder("address_locality")
      address_postal_code                  = Search.TextNodeBuilder("address_postal_code")
      address_region                       = Search.TextNodeBuilder("address_region")
      address_street_address               = Search.TextNodeBuilder("address_street_address")
      address_country_name                 = Search.TextNodeBuilder("address_country_name")
      cardholder_name                      = Search.TextNodeBuilder("cardholder_name")
      company                              = Search.TextNodeBuilder("company")
      created_at                           = Search.RangeNodeBuilder("created_at")
      credit_card_expiration_date          = Search.EqualityNodeBuilder("credit_card_expiration_date")
      credit_card_number                   = Search.TextNodeBuilder("credit_card_number")
      email                                = Search.TextNodeBuilder("email")
      fax                                  = Search.TextNodeBuilder("fax")
      first_name                           = Search.TextNodeBuilder("first_name")
      id                                   = Search.TextNodeBuilder("id")
      ids                                  = Search.MultipleValueNodeBuilder("ids")
      last_name                            = Search.TextNodeBuilder("last_name")
      payment_method_token                 = Search.TextNodeBuilder("payment_method_token")
      payment_method_token_with_duplicates = Search.IsNodeBuilder("payment_method_token_with_duplicates")
      phone                                = Search.TextNodeBuilder("phone")
      website                              = Search.TextNodeBuilder("website")

########NEW FILE########
__FILENAME__ = descriptor
from braintree.resource import Resource

class Descriptor(Resource):
    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)

########NEW FILE########
__FILENAME__ = disbursement
from decimal import Decimal
from braintree.resource import Resource
from braintree.transaction_search import TransactionSearch
from braintree.merchant_account import MerchantAccount

class Disbursement(Resource):
    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)
        self.amount = Decimal(self.amount)
        self.merchant_account = MerchantAccount(gateway, attributes["merchant_account"])

    def __repr__(self):
        detail_list = ["amount", "disbursement_date", "exception_message", "follow_up_action", "id", "success", "retry"]
        return super(Disbursement, self).__repr__(detail_list)

    def transactions(self):
        return self.gateway.transaction.search([TransactionSearch.ids.in_list(self.transaction_ids)])



########NEW FILE########
__FILENAME__ = disbursement_detail
from decimal import Decimal
from braintree.attribute_getter import AttributeGetter

class DisbursementDetail(AttributeGetter):
    def __init__(self, attributes):
        AttributeGetter.__init__(self, attributes)

        if self.settlement_amount is not None:
            self.settlement_amount = Decimal(self.settlement_amount)
        if self.settlement_currency_exchange_rate is not None:
            self.settlement_currency_exchange_rate = Decimal(self.settlement_currency_exchange_rate)

    @property
    def is_valid(self):
        return self.disbursement_date is not None

########NEW FILE########
__FILENAME__ = discount
from braintree.modification import Modification
from braintree.configuration import Configuration


class Discount(Modification):

    @staticmethod
    def all():
        return Configuration.gateway().discount.all()

########NEW FILE########
__FILENAME__ = discount_gateway
import braintree
from braintree.discount import Discount
from braintree.resource_collection import ResourceCollection

class DiscountGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def all(self):
        response = self.config.http().get("/discounts/")
        discounts = {"discount": response["discounts"]}
        return [Discount(self.gateway, item) for item in ResourceCollection._extract_as_array(discounts, "discount")]

########NEW FILE########
__FILENAME__ = dispute
from decimal import Decimal
from braintree.attribute_getter import AttributeGetter

class Dispute(AttributeGetter):
    class Status(object):
        """
        Constants representing dispute statuses. Available types are:

        * braintree.Dispute.Status.Open
        * braintree.Dispute.Status.Won
        * braintree.Dispute.Status.Lost
        """
        Open  = "open"
        Won  = "won"
        Lost = "lost"

    class Reason(object):
        """
        Constants representing dispute reasons. Available types are:

        * braintree.Dispute.Reason.CancelledRecurringTransaction
        * braintree.Dispute.Reason.CreditNotProcessed
        * braintree.Dispute.Reason.Duplicate
        * braintree.Dispute.Reason.Fraud
        * braintree.Dispute.Reason.General
        * braintree.Dispute.Reason.InvalidAccount
        * braintree.Dispute.Reason.NotRecognized
        * braintree.Dispute.Reason.ProductNotReceived
        * braintree.Dispute.Reason.ProductUnsatisfactory
        * braintree.Dispute.Reason.TransactionAmountDiffers
        """
        CancelledRecurringTransaction = "cancelled_recurring_transaction"
        CreditNotProcessed            = "credit_not_processed"
        Duplicate                     = "duplicate"
        Fraud                         = "fraud"
        General                       = "general"
        InvalidAccount                = "invalid_account"
        NotRecognized                 = "not_recognized"
        ProductNotReceived            = "product_not_received"
        ProductUnsatisfactory         = "product_unsatisfactory"
        TransactionAmountDiffers      = "transaction_amount_differs"


    def __init__(self, attributes):
        AttributeGetter.__init__(self, attributes)

        if self.amount is not None:
            self.amount = Decimal(self.amount)

########NEW FILE########
__FILENAME__ = environment
import os
import inspect

class Environment(object):
    """
    A class representing which environment the client library is using.
    Pass in one of the following values as the first argument to
    :class:`braintree.Configuration.configure() <braintree.configuration.Configuration>` ::

        braintree.Environment.Sandbox
        braintree.Environment.Production
    """

    def __init__(self, server, port, auth_url, is_ssl, ssl_certificate):
        self.__server = server
        self.__port = port
        self.is_ssl = is_ssl
        self.ssl_certificate = ssl_certificate
        self.__auth_url = auth_url

    @property
    def base_url(self):
        return "%s%s:%s" % (self.protocol, self.server, self.port)

    @property
    def port(self):
        return int(self.__port)

    @property
    def auth_url(self):
        return self.__auth_url

    @property
    def protocol(self):
        return self.__port == "443" and "https://" or "http://"

    @property
    def server(self):
        return self.__server

    @property
    def server_and_port(self):
        return self.__server + ":" + self.__port

    @staticmethod
    def braintree_root():
        return os.path.dirname(inspect.getfile(Environment))

Environment.Development = Environment("localhost", os.getenv("GATEWAY_PORT") or "3000", "http://auth.venmo.dev:9292", False, None)
Environment.Sandbox = Environment("api.sandbox.braintreegateway.com", "443", "https://auth.sandbox.venmo.com", True, Environment.braintree_root() + "/ssl/api_braintreegateway_com.ca.crt")
Environment.Production = Environment("api.braintreegateway.com", "443", "https://auth.venmo.com", True, Environment.braintree_root() + "/ssl/api_braintreegateway_com.ca.crt")

########NEW FILE########
__FILENAME__ = errors
from braintree.validation_error_collection import ValidationErrorCollection

class Errors(object):
    def __init__(self, data):
        data["errors"] = []
        self.errors = ValidationErrorCollection(data)
        self.size = self.errors.deep_size

    @property
    def deep_errors(self):
        return self.errors.deep_errors

    def for_object(self, key):
        return self.errors.for_object(key)

    def __len__(self):
        return self.size

########NEW FILE########
__FILENAME__ = error_codes
class ErrorCodes(object):
    """
    A set of constants representing validation errors.  Validation error messages can change, but the codes will not.
    See the source for a list of all errors codes.

    Codes can be used to check for specific validation errors::

        result = Transaction.sale({})
        assert(result.is_success == False)
        assert(result.errors.for_object("transaction").on("amount")[0].code == ErrorCodes.Transaction.AmountIsRequired)
    """

    class Address(object):
        CannotBeBlank = "81801"
        CompanyIsInvalid = "91821"
        CompanyIsTooLong = "81802"
        CountryCodeAlpha2IsNotAccepted = "91814"
        CountryCodeAlpha3IsNotAccepted = "91816"
        CountryCodeNumericIsNotAccepted = "91817"
        CountryNameIsNotAccepted = "91803"
        ExtedAddressIsTooLong = "81804" # Deprecated
        ExtendedAddressIsInvalid = "91823"
        ExtendedAddressIsTooLong = "81804"
        FirstNameIsInvalid = "91819"
        FirstNameIsTooLong = "81805"
        InconsistentCountry = "91815"
        LastNameIsInvalid = "91820"
        LastNameIsTooLong = "81806"
        LocalityIsInvalid = "91824"
        LocalityIsTooLong = "81807"
        PostalCodeInvalidCharacters = "81813"
        PostalCodeIsInvalid = "91826"
        PostalCodeIsRequired = "81808"
        PostalCodeIsTooLong = "81809"
        RegionIsInvalid = "91825"
        RegionIsTooLong = "81810"
        StreetAddressIsInvalid = "91822"
        StreetAddressIsRequired = "81811"
        StreetAddressIsTooLong = "81812"
        TooManyAddressesPerCustomer = "91818"

    class CreditCard(object):
        BillingAddressConflict = "91701"
        BillingAddressIdIsInvalid = "91702"
        CardholderNameIsTooLong = "81723"
        CreditCardTypeIsNotAccepted = "81703"
        CreditCardTypeIsNotAcceptedBySubscriptionMerchantAccount = "81718"
        CustomerIdIsInvalid = "91705"
        CustomerIdIsRequired = "91704"
        CvvIsInvalid = "81707"
        CvvIsRequired = "81706"
        DuplicateCardExists = "81724"
        ExpirationDateConflict = "91708"
        ExpirationDateIsInvalid = "81710"
        ExpirationDateIsRequired = "81709"
        ExpirationDateYearIsInvalid = "81711"
        ExpirationMonthIsInvalid = "81712"
        ExpirationYearIsInvalid = "81713"
        InvalidVenmoSDKPaymentMethodCode = "91727"
        NumberHasInvalidLength = NumberLengthIsInvalid = "81716"
        NumberIsInvalid = "81715"
        NumberIsRequired = "81714"
        NumberMustBeTestNumber = "81717"
        PaymentMethodConflict = "81725"
        TokenInvalid = TokenFormatIsInvalid = "91718"
        TokenIsInUse = "91719"
        TokenIsNotAllowed = "91721"
        TokenIsRequired = "91722"
        TokenIsTooLong = "91720"
        VenmoSDKPaymentMethodCodeCardTypeIsNotAccepted = "91726"
        VerificationNotSupportedOnThisMerchantAccount = "91730"

        class Options(object):
            UpdateExistingTokenIsInvalid = "91723"
            VerificationMerchantAccountIdIsInvalid = "91728"
            UpdateExistingTokenNotAllowed = "91729"


    class Customer(object):
        CompanyIsTooLong = "81601"
        CustomFieldIsInvalid = "91602"
        CustomFieldIsTooLong = "81603"
        EmailIsInvalid = EmailFormatIsInvalid = "81604"
        EmailIsRequired = "81606"
        EmailIsTooLong = "81605"
        FaxIsTooLong = "81607"
        FirstNameIsTooLong = "81608"
        IdIsInUse = "91609"
        IdIsInvaild = "91610" # Deprecated
        IdIsInvalid = "91610"
        IdIsNotAllowed = "91611"
        IdIsRequired = "91613"
        IdIsTooLong = "91612"
        LastNameIsTooLong = "81613"
        PhoneIsTooLong = "81614"
        WebsiteIsInvalid = WebsiteFormatIsInvalid = "81616"
        WebsiteIsTooLong = "81615"

    class Descriptor(object):
        DynamicDescriptorsDisabled = "92203"
        InternationalNameFormatIsInvalid = "92204"
        InternationalPhoneFormatIsInvalid = "92205"
        NameFormatIsInvalid = "92201"
        PhoneFormatIsInvalid = "92202"

    class MerchantAccount(object):
        IdFormatIsInvalid = "82603"
        IdIsInUse = "82604"
        IdIsNotAllowed = "82605"
        IdIsTooLong = "82602"
        MasterMerchantAccountIdIsInvalid = "82607"
        MasterMerchantAccountIdIsRequired = "82606"
        MasterMerchantAccountMustBeActive = "82608"
        TosAcceptedIsRequired = "82610"
        CannotBeUpdated = "82674"
        IdCannotBeUpdated = "82675"
        MasterMerchantAccountIdCannotBeUpdated = "82676"
        Declined = "82626"
        DeclinedMasterCardMatch = "82622"
        DeclinedOFAC = "82621"
        DeclinedFailedKYC = "82623"
        DeclinedSsnInvalid = "82624"
        DeclinedSsnMatchesDeceased = "82625"

        class ApplicantDetails(object):
            AccountNumberIsRequired = "82614"
            CompanyNameIsInvalid = "82631"
            CompanyNameIsRequiredWithTaxId = "82633"
            DateOfBirthIsRequired = "82612"
            Declined = "82626" # Keep for backwards compatibility
            DeclinedMasterCardMatch = "82622" # Keep for backwards compatibility
            DeclinedOFAC = "82621" # Keep for backwards compatibility
            DeclinedFailedKYC = "82623" # Keep for backwards compatibility
            DeclinedSsnInvalid = "82624" # Keep for backwards compatibility
            DeclinedSsnMatchesDeceased = "82625" # Keep for backwards compatibility
            EmailAddressIsInvalid = "82616"
            FirstNameIsInvalid = "82627"
            FirstNameIsRequired = "82609"
            LastNameIsInvalid = "82628"
            LastNameIsRequired = "82611"
            PhoneIsInvalid = "82636"
            RoutingNumberIsInvalid = "82635"
            RoutingNumberIsRequired = "82613"
            SsnIsInvalid = "82615"
            TaxIdIsInvalid = "82632"
            TaxIdIsRequiredWithCompanyName = "82634"
            DateOfBirthIsInvalid = "82663"
            EmailAddressIsRequired = "82665"
            AccountNumberIsInvalid = "82670"
            TaxIdMustBeBlank = "82673"

            class Address(object):
                LocalityIsRequired = "82618"
                PostalCodeIsInvalid = "82630"
                PostalCodeIsRequired = "82619"
                RegionIsRequired = "82620"
                StreetAddressIsInvalid = "82629"
                StreetAddressIsRequired = "82617"
                RegionIsInvalid = "82664"

        class Individual(object):
            FirstNameIsRequired = "82637"
            LastNameIsRequired = "82638"
            DateOfBirthIsRequired = "82639"
            SsnIsInvalid = "82642"
            EmailAddressIsInvalid = "82643"
            FirstNameIsInvalid = "82644"
            LastNameIsInvalid = "82645"
            PhoneIsInvalid = "82656"
            DateOfBirthIsInvalid = "82666"
            EmailAddressIsRequired = "82667"

            class Address(object):
                StreetAddressIsRequired = "82657"
                LocalityIsRequired = "82658"
                PostalCodeIsRequired = "82659"
                RegionIsRequired = "82660"
                StreetAddressIsInvalid = "82661"
                PostalCodeIsInvalid = "82662"
                RegionIsInvalid = "82668"

        class Business(object):
            DbaNameIsInvalid = "82646"
            LegalNameIsInvalid = "82677"
            LegalNameIsRequiredWithTaxId = "82669"
            TaxIdIsInvalid = "82647"
            TaxIdIsRequiredWithLegalName = "82648"
            TaxIdMustBeBlank = "82672"
            class Address(object):
                StreetAddressIsInvalid = "82685"
                PostalCodeIsInvalid = "82686"
                RegionIsInvalid = "82684"

        class Funding(object):
            RoutingNumberIsRequired = "82640"
            AccountNumberIsRequired = "82641"
            RoutingNumberIsInvalid = "82649"
            AccountNumberIsInvalid = "82671"
            DestinationIsInvalid = "82679"
            DestinationIsRequired = "82678"
            EmailAddressIsInvalid = "82681"
            EmailAddressIsRequired = "82680"
            MobilePhoneIsInvalid = "82683"
            MobilePhoneIsRequired = "82682"

    class SettlementBatchSummary(object):
        CustomFieldIsInvalid = "82303"
        SettlementDateIsInvalid = "82302"
        SettlementDateIsRequired = "82301"

    class Subscription(object):
        BillingDayOfMonthCannotBeUpdated = "91918"
        BillingDayOfMonthIsInvalid = "91914"
        BillingDayOfMonthMustBeNumeric = "91913"
        CannotAddDuplicateAddonOrDiscount = "91911"
        CannotEditCanceledSubscription = "81901"
        CannotEditExpiredSubscription = "81910"
        CannotEditPriceChangingFieldsOnPastDueSubscription = "91920"
        FirstBillingDateCannotBeInThePast = "91916"
        FirstBillingDateCannotBeUpdated = "91919"
        FirstBillingDateIsInvalid = "91915"
        IdIsInUse = "81902"
        InconsistentNumberOfBillingCycles = "91908"
        InconsistentStartDate = "91917"
        InvalidRequestFormat = "91921"
        MerchantAccountIdIsInvalid = "91901"
        MismatchCurrencyISOCode = "91923"
        NumberOfBillingCyclesCannotBeBlank = "91912"
        NumberOfBillingCyclesIsTooSmall = "91909"
        NumberOfBillingCyclesMustBeGreaterThanZero = "91907"
        NumberOfBillingCyclesMustBeNumeric = "91906"
        PaymentMethodTokenCardTypeIsNotAccepted = "91902"
        PaymentMethodTokenIsInvalid = "91903"
        PaymentMethodTokenNotAssociatedWithCustomer = "91905"
        PlanBillingFrequencyCannotBeUpdated = "91922"
        PlanIdIsInvalid = "91904"
        PriceCannotBeBlank = "81903"
        PriceFormatIsInvalid = "81904"
        PriceIsTooLarge = "81923"
        StatusIsCanceled = "81905"
        TokenFormatIsInvalid = "81906"
        TrialDurationFormatIsInvalid = "81907"
        TrialDurationIsRequired = "81908"
        TrialDurationUnitIsInvalid = "81909"

        class Modification(object):
            AmountCannotBeBlank = "92003"
            AmountIsInvalid = "92002"
            AmountIsTooLarge = "92023"
            CannotEditModificationsOnPastDueSubscription = "92022"
            CannotUpdateAndRemove = "92015"
            ExistingIdIsIncorrectKind = "92020"
            ExistingIdIsInvalid = "92011"
            ExistingIdIsRequired = "92012"
            IdToRemoveIsIncorrectKind = "92021"
            IdToRemoveIsNotPresent = "92016"
            InconsistentNumberOfBillingCycles = "92018"
            InheritedFromIdIsInvalid = "92013"
            InheritedFromIdIsRequired = "92014"
            Missing = "92024"
            NumberOfBillingCyclesCannotBeBlank = "92017"
            NumberOfBillingCyclesIsInvalid = "92005"
            NumberOfBillingCyclesMustBeGreaterThanZero = "92019"
            QuantityCannotBeBlank = "92004"
            QuantityIsInvalid = "92001"
            QuantityMustBeGreaterThanZero = "92010"

    class Transaction(object):
        AmountCannotBeNegative = "81501"
        AmountIsInvalid = AmountFormatIsInvalid = "81503"
        AmountIsRequired = "81502"
        AmountIsTooLarge = "81528"
        AmountMustBeGreaterThanZero = "81531"
        BillingAddressConflict = "91530"
        CannotBeVoided = "91504"
        CannotCancelRelease = "91562"
        CannotCloneCredit = "91543"
        CannotCloneTransactionWithVaultCreditCard = "91540"
        CannotCloneUnsuccessfulTransaction = "91542"
        CannotCloneVoiceAuthorizations = "91541"
        CannotHoldInEscrow = "91560"
        CannotPartiallyRefundEscrowedTransaction = "91563"
        CannotRefundCredit = "91505"
        CannotRefundUnlessSettled = "91506"
        CannotRefundWithPendingMerchantAccount = "91559"
        CannotRefundWithSuspendedMerchantAccount = "91538"
        CannotReleaseFromEscrow = "91561"
        CannotSubmitForSettlement = "91507"
        ChannelIsTooLong = "91550"
        ChannelIsTooLong = "91550"
        CreditCardIsRequired = "91508"
        CustomFieldIsInvalid = "91526"
        CustomFieldIsTooLong = "81527"
        CustomerDefaultPaymentMethodCardTypeIsNotAccepted = "81509"
        CustomerDoesNotHaveCreditCard = "91511"
        CustomerIdIsInvalid = "91510"
        HasAlreadyBeenRefunded = "91512"
        MerchantAccountDoesNotSupportMOTO = "91558"
        MerchantAccountDoesNotSupportRefunds = "91547"
        MerchantAccountIdIsInvalid = "91513"
        MerchantAccountIsSusped = "91514" # Deprecated
        MerchantAccountIsSuspended = "91514"
        MerchantAccountNameIsInvalid = "91513" # Deprecated
        OrderIdIsTooLong = "91501"
        PaymentMethodConflict = "91515"
        PaymentMethodConflictWithVenmoSDK = "91549"
        PaymentMethodDoesNotBelongToCustomer = "91516"
        PaymentMethodDoesNotBelongToSubscription = "91527"
        PaymentMethodTokenCardTypeIsNotAccepted = "91517"
        PaymentMethodTokenIsInvalid = "91518"
        ProcessorAuthorizationCodeCannotBeSet = "91519"
        ProcessorAuthorizationCodeIsInvalid = "81520"
        ProcessorDoesNotSupportCredits = "91546"
        ProcessorDoesNotSupportVoiceAuthorizations = "91545"
        PurchaseOrderNumberIsInvalid = "91548"
        PurchaseOrderNumberIsTooLong = "91537"
        RefundAmountIsTooLarge = "91521"
        ServiceFeeAmountCannotBeNegative = "91554"
        ServiceFeeAmountFormatIsInvalid = "91555"
        ServiceFeeAmountIsTooLarge = "91556"
        ServiceFeeAmountNotAllowedOnMasterMerchantAccount = "91557"
        ServiceFeeIsNotAllowedOnCredits = "91552"
        SettlementAmountIsLessThanServiceFeeAmount = "91551"
        SettlementAmountIsTooLarge = "91522"
        SubMerchantAccountRequiresServiceFeeAmount = "91553"
        SubscriptionDoesNotBelongToCustomer = "91529"
        SubscriptionIdIsInvalid = "91528"
        SubscriptionStatusMustBePastDue = "91531"
        TaxAmountCannotBeNegative = "81534"
        TaxAmountFormatIsInvalid = "81535"
        TaxAmountIsTooLarge = "81536"
        TypeIsInvalid = "91523"
        TypeIsRequired = "91524"
        UnsupportedVoiceAuthorization = "91539"

        class Options(object):
            VaultIsDisabled = "91525"
            SubmitForSettlementIsRequiredForCloning = "91544"


########NEW FILE########
__FILENAME__ = error_result
import braintree
from braintree.errors import Errors
from braintree.credit_card_verification import CreditCardVerification

class ErrorResult(object):
    """
    An instance of this class is returned from most operations when there is a validation error.  Call :func:`errors` to get the collection of errors::

        error_result = Transaction.sale({})
        assert(error_result.is_success == False)
        assert(error_result.errors.for_object("transaction").on("amount")[0].code == ErrorCodes.Transaction.AmountIsRequired)

    Errors can be nested at different levels.  For example, creating a transaction with a credit card can have errors at the transaction level as well as the credit card level.  :func:`for_object` returns the :class:`ValidationErrorCollection <braintree.validation_error_collection.ValidationErrorCollection>` for the errors at that level.  For example::

        error_result = Transaction.sale({"credit_card": {"number": "invalid"}})
        assert(error_result.errors.for_object("transaction").for_object("credit_card").on("number")[0].code == ErrorCodes.CreditCard.NumberHasInvalidLength)
    """

    def __init__(self, gateway, attributes):
        if "params" in attributes:
            self.params = attributes["params"]
        else:
            self.params = None

        self.errors = Errors(attributes["errors"])
        self.message = attributes["message"]

        if "verification" in attributes:
            self.credit_card_verification = CreditCardVerification(gateway, attributes["verification"])
        else:
            self.credit_card_verification = None

        if "transaction" in attributes:
            self.transaction = braintree.transaction.Transaction(gateway, attributes["transaction"])
        else:
            self.transaction = None

        if "subscription" in attributes:
            self.subscription = braintree.subscription.Subscription(gateway, attributes["subscription"])
        else:
            self.subscription = None

        if "merchant_account" in attributes:
            self.merchant_account = braintree.merchant_account.MerchantAccount(gateway, attributes["merchant_account"])
        else:
            self.merchant_account = None

    def __repr__(self):
        return "<%s '%s' at %x>" % (self.__class__.__name__, self.message, id(self))

    @property
    def is_success(self):
        """ Returns whether the result from the gateway is a successful response. """

        return False

########NEW FILE########
__FILENAME__ = authentication_error
from braintree.exceptions.braintree_error import BraintreeError

class AuthenticationError(BraintreeError):
    """
    Raised when the client library cannot authenticate with the gateway.  This generally means the public_key/private key are incorrect, or the user is not active.

    See https://www.braintreepayments.com/docs/python/general/exceptions#authentication_error
    """
    pass

########NEW FILE########
__FILENAME__ = authorization_error
from braintree.exceptions.braintree_error import BraintreeError

class AuthorizationError(BraintreeError):
    """
    Raised when the user does not have permission to complete the requested operation.

    See https://www.braintreepayments.com/docs/python/general/exceptions#authorization_error
    """
    pass

########NEW FILE########
__FILENAME__ = braintree_error
class BraintreeError(Exception):
    pass

########NEW FILE########
__FILENAME__ = down_for_maintenance_error
from braintree.exceptions.braintree_error import BraintreeError

class DownForMaintenanceError(BraintreeError):
    """
    Raised when the gateway is down for maintenance.

    See https://www.braintreepayments.com/docs/python/general/exceptions#down_for_maintenance_error
    """
    pass

########NEW FILE########
__FILENAME__ = forged_query_string_error
from braintree.exceptions.braintree_error import BraintreeError

class ForgedQueryStringError(BraintreeError):
    """
    Raised when the query string has been forged or tampered with during a transparent redirect.

    See https://www.braintreepayments.com/docs/python/general/exceptions#forged_query_string
    """
    pass

########NEW FILE########
__FILENAME__ = invalid_signature_error
from braintree.exceptions.braintree_error import BraintreeError

class InvalidSignatureError(BraintreeError):
    pass

########NEW FILE########
__FILENAME__ = not_found_error
from braintree.exceptions.braintree_error import BraintreeError

class NotFoundError(BraintreeError):
    """
    Raised when an object is not found in the gateway, such as a Transaction.find("bad_id").

    https://www.braintreepayments.com/docs/python/general/exceptions#not_found_error
    """
    pass

########NEW FILE########
__FILENAME__ = server_error
from braintree.exceptions.braintree_error import BraintreeError

class ServerError(BraintreeError):
    """
    Raised when the gateway raises an error.  Please contant support at support@getbraintree.com.

    See https://www.braintreepayments.com/docs/python/general/exceptions#server_error
    """
    pass

########NEW FILE########
__FILENAME__ = unexpected_error
from braintree.exceptions.braintree_error import BraintreeError

class UnexpectedError(BraintreeError):
    """ Raised for unknown or unexpected errors. """
    pass

########NEW FILE########
__FILENAME__ = upgrade_required_error
from braintree.exceptions.braintree_error import BraintreeError

class UpgradeRequiredError(BraintreeError):
    """
    Raised for unsupported client library versions.

    See https://www.braintreepayments.com/docs/python/general/exceptions#upgrade_required_error
    """
    pass

########NEW FILE########
__FILENAME__ = ids_search
from braintree.search import Search

class IdsSearch:
    ids = Search.MultipleValueNodeBuilder("ids")

########NEW FILE########
__FILENAME__ = address_details
from braintree.attribute_getter import AttributeGetter

class AddressDetails(AttributeGetter):
    detail_list = [
        "street_address",
        "locality",
        "region",
        "postal_code",
    ]

    def __init__(self, attributes):
        AttributeGetter.__init__(self, attributes)

    def __repr__(self):
        return super(AddressDetails, self).__repr__(self.detail_list)

########NEW FILE########
__FILENAME__ = business_details
from braintree.attribute_getter import AttributeGetter
from braintree.merchant_account.address_details import AddressDetails

class BusinessDetails(AttributeGetter):
    detail_list = [
        "dba_name",
        "legal_name",
        "tax_id",
        "address_details",
    ]

    def __init__(self, attributes):
        AttributeGetter.__init__(self, attributes)
        self.address_details = AddressDetails(attributes.get("address", {}))

    def __repr__(self):
        return super(BusinessDetails, self).__repr__(self.detail_list)

########NEW FILE########
__FILENAME__ = funding_details
from braintree.attribute_getter import AttributeGetter

class FundingDetails(AttributeGetter):
    detail_list = [
        "account_number_last_4",
        "routing_number",
        "destination",
        "email",
        "mobile_phone",
    ]

    def __init__(self, attributes):
        AttributeGetter.__init__(self, attributes)

    def __repr__(self):
        return super(FundingDetails, self).__repr__(self.detail_list)

########NEW FILE########
__FILENAME__ = individual_details
from braintree.attribute_getter import AttributeGetter
from braintree.merchant_account.address_details import AddressDetails

class IndividualDetails(AttributeGetter):
    detail_list = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "date_of_birth",
        "ssn_last_4",
        "address_details",
    ]

    def __init__(self, attributes):
        AttributeGetter.__init__(self, attributes)
        self.address_details = AddressDetails(attributes.get("address", {}))

    def __repr__(self):
        return super(IndividualDetails, self).__repr__(self.detail_list)

########NEW FILE########
__FILENAME__ = merchant_account
from braintree.configuration import Configuration
from braintree.resource import Resource
from braintree.merchant_account import BusinessDetails, FundingDetails, IndividualDetails

class MerchantAccount(Resource):
    class Status(object):
        Active = "active"
        Pending = "pending"
        Suspended = "suspended"

    class FundingDestination(object):
        Bank = "bank"
        Email = "email"
        MobilePhone = "mobile_phone"

    FundingDestinations = FundingDestination

    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)
        self.individual_details = IndividualDetails(attributes.get("individual", {}))
        self.business_details = BusinessDetails(attributes.get("business", {}))
        self.funding_details = FundingDetails(attributes.get("funding", {}))
        if "master_merchant_account" in attributes:
            self.master_merchant_account = MerchantAccount(gateway, attributes.pop("master_merchant_account"))

    def __repr__(self):
        detail_list = ["id", "status", "master_merchant_account", "individual_details", "business_details", "funding_details"]
        return super(MerchantAccount, self).__repr__(detail_list)

    @staticmethod
    def create(params={}):
        return Configuration.gateway().merchant_account.create(params)

    @staticmethod
    def update(id, attributes):
        return Configuration.gateway().merchant_account.update(id, attributes)

    @staticmethod
    def find(id):
        return Configuration.gateway().merchant_account.find(id)

########NEW FILE########
__FILENAME__ = merchant_account_gateway
from braintree.error_result import ErrorResult
from braintree.merchant_account import MerchantAccount
from braintree.resource import Resource
from braintree.successful_result import SuccessfulResult
from braintree.exceptions.not_found_error import NotFoundError

class MerchantAccountGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def create(self, params={}):
        Resource.verify_keys(params, MerchantAccountGateway._detect_signature(params))
        return self._post("/merchant_accounts/create_via_api", {"merchant_account": params})

    def update(self, merchant_account_id, params={}):
        Resource.verify_keys(params, MerchantAccountGateway._update_signature())
        return self._put("/merchant_accounts/%s/update_via_api" % merchant_account_id, {"merchant_account": params})

    def find(self, merchant_account_id):
        try:
            if merchant_account_id == None or merchant_account_id.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/merchant_accounts/" + merchant_account_id)
            return MerchantAccount(self.gateway, response["merchant_account"])
        except NotFoundError:
            raise NotFoundError("merchant account with id " + merchant_account_id + " not found")

    def _post(self, url, params={}):
        response = self.config.http().post(url, params)
        if "merchant_account" in response:
            return SuccessfulResult({"merchant_account": MerchantAccount(self.gateway, response["merchant_account"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def _put(self, url, params={}):
        response = self.config.http().put(url, params)
        if "merchant_account" in response:
            return SuccessfulResult({"merchant_account": MerchantAccount(self.gateway, response["merchant_account"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    @staticmethod
    def _detect_signature(attributes):
        if attributes.has_key('applicant_details'):
            # Warn deprecated
            return MerchantAccountGateway._create_deprecated_signature()
        else:
            return MerchantAccountGateway._create_signature()

    @staticmethod
    def _create_deprecated_signature():
        return [
            {'applicant_details': [
                'company_name',
                'first_name',
                'last_name',
                'email',
                'phone',
                'date_of_birth',
                'ssn',
                'tax_id',
                'routing_number',
                'account_number',
                {'address': [
                    'street_address',
                    'postal_code',
                    'locality',
                    'region']}
                ]
            },
            'tos_accepted',
            'master_merchant_account_id',
            'id'
        ]

    @staticmethod
    def _create_signature():
        return [
            {'individual': [
                'first_name',
                'last_name',
                'email',
                'phone',
                'date_of_birth',
                'ssn',
                {'address': [
                    'street_address',
                    'postal_code',
                    'locality',
                    'region']}
                ]
            },
            {'business': [
                'dba_name',
                'legal_name',
                'tax_id',
                {'address': [
                    'street_address',
                    'postal_code',
                    'locality',
                    'region']}
                ]
            },
            {'funding': [
                'routing_number',
                'account_number',
                'destination',
                'email',
                'mobile_phone',
                ]
            },
            'tos_accepted',
            'master_merchant_account_id',
            'id'
        ]

    @staticmethod
    def _update_signature():
        return [
            {'individual': [
                'first_name',
                'last_name',
                'email',
                'phone',
                'date_of_birth',
                'ssn',
                {'address': [
                    'street_address',
                    'postal_code',
                    'locality',
                    'region']}
                ]
            },
            {'business': [
                'dba_name',
                'legal_name',
                'tax_id',
                {'address': [
                    'street_address',
                    'postal_code',
                    'locality',
                    'region']}
                ]
            },
            {'funding': [
                'routing_number',
                'account_number',
                'destination',
                'email',
                'mobile_phone',
                ]
            },
            'master_merchant_account_id',
            'id'
        ]

########NEW FILE########
__FILENAME__ = modification
from decimal import Decimal
from braintree.resource import Resource

class Modification(Resource):
    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)
        self.amount = Decimal(self.amount)

########NEW FILE########
__FILENAME__ = partner_merchant
from braintree.configuration import Configuration
from braintree.resource import Resource

class PartnerMerchant(Resource):

    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)
        if "partner_merchant_id" in attributes:
            self.partner_merchant_id = attributes.pop("partner_merchant_id")
        if "private_key" in attributes:
            self.private_key = attributes.pop("private_key")
        if "public_key" in attributes:
            self.public_key = attributes.pop("public_key")
        if "merchant_public_id" in attributes:
            self.merchant_public_id = attributes.pop("merchant_public_id")
        if "client_side_encryption_key" in attributes:
            self.client_side_encryption_key = attributes.pop("client_side_encryption_key")

    def __repr__(self):
        detail_list = ["partner_merchant_id", "public_key", "merchant_public_id", "client_side_encryption_key"]
        return super(PartnerMerchant, self).__repr__(detail_list)

########NEW FILE########
__FILENAME__ = plan
from braintree.util.http import Http
import braintree
from braintree.add_on import AddOn
from braintree.configuration import Configuration
from braintree.discount import Discount
from braintree.resource_collection import ResourceCollection
from braintree.resource import Resource

class Plan(Resource):

    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)
        if "add_ons" in attributes:
            self.add_ons = [AddOn(gateway, add_on) for add_on in self.add_ons]
        if "discounts" in attributes:
            self.discounts = [Discount(gateway, discount) for discount in self.discounts]

    @staticmethod
    def all():
        return Configuration.gateway().plan.all()


########NEW FILE########
__FILENAME__ = plan_gateway
import re
import braintree
from braintree.plan import Plan
from braintree.error_result import ErrorResult
from braintree.exceptions.not_found_error import NotFoundError
from braintree.resource import Resource
from braintree.resource_collection import ResourceCollection
from braintree.successful_result import SuccessfulResult

class PlanGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def all(self):
        response = self.config.http().get("/plans/")
        return [Plan(self.gateway, item) for item in ResourceCollection._extract_as_array(response, "plans")]

########NEW FILE########
__FILENAME__ = resource
import re
import string
from braintree.attribute_getter import AttributeGetter

class Resource(AttributeGetter):
    @staticmethod
    def verify_keys(params, signature):
        allowed_keys = Resource.__flattened_signature(signature)
        params_keys = Resource.__flattened_params_keys(params)

        invalid_keys = [key for key in params_keys if key not in allowed_keys]
        invalid_keys = Resource.__remove_wildcard_keys(allowed_keys, invalid_keys)

        if len(invalid_keys) > 0:
            keys_string = ", ".join(invalid_keys)
            raise KeyError("Invalid keys: " + keys_string)

    @staticmethod
    def __flattened_params_keys(params, parent=None):
        if isinstance(params, str):
            return [ "%s[%s]" % (parent, params) ]
        else:
            keys = []
            for key, val in params.iteritems():
                full_key = "%s[%s]" % (parent, key) if parent else key
                if isinstance(val, dict):
                    keys += Resource.__flattened_params_keys(val, full_key)
                elif isinstance(val, list):
                    for item in val:
                        keys += Resource.__flattened_params_keys(item, full_key)
                else:
                    keys.append(full_key)
            return keys

    @staticmethod
    def __flattened_signature(signature, parent=None):
        flat_sig = []
        for item in signature:
            if isinstance(item, dict):
                for key, val in item.iteritems():
                    full_key = parent + "[" + key + "]" if parent else key
                    flat_sig += Resource.__flattened_signature(val, full_key)
            else:
                full_key = parent + "[" + item + "]" if parent else item
                flat_sig.append(full_key)
        return flat_sig

    @staticmethod
    def __remove_wildcard_keys(allowed_keys, invalid_keys):
        wildcard_keys = [re.escape(key).replace("\\[\\_\\_any\\_key\\_\\_\\]", "\\[[\w-]+\\]") for key in allowed_keys if re.search("\\[__any_key__\\]", key)]
        new_keys = []
        for key in invalid_keys:
            if len([match for match in wildcard_keys if re.match("\A" + match + "\Z", key)]) == 0:
                new_keys.append(key)
        return new_keys

    def __init__(self, gateway, attributes):
        AttributeGetter.__init__(self, attributes)
        self.gateway = gateway


########NEW FILE########
__FILENAME__ = resource_collection
class ResourceCollection(object):
    """
    A class representing results from a search.  Iterate over the results by calling items::

        results = braintree.Transaction.search("411111")
        for transaction in results.items:
            print transaction.id
    """

    def __init__(self, query, results, method):
        self.__page_size = results["search_results"]["page_size"]
        self.__ids = results["search_results"]["ids"]
        self.__query = query
        self.__method = method

    @property
    def maximum_size(self):
        """
        Returns the approximate size of the results.  The size is approximate due to race conditions when pulling
        back results.  Due to its inexact nature, maximum_size should be avoided.
        """
        return len(self.__ids)

    @property
    def first(self):
        """ Returns the first item in the results. """
        return self.__method(self.__query, self.__ids[0:1])[0]

    @property
    def items(self):
        """ Returns a generator allowing iteration over all of the results. """
        for batch in self.__batch_ids():
            for item in self.__method(self.__query, batch):
                yield item

    def __batch_ids(self):
        for i in xrange(0, len(self.__ids), self.__page_size):
                yield self.__ids[i:i+self.__page_size]


    @staticmethod
    def _extract_as_array(results, attribute):
        if not attribute in results:
            return []

        value = results[attribute]
        if not isinstance(value, list):
            value = [value]
        return value


########NEW FILE########
__FILENAME__ = search
class Search:
	class IsNodeBuilder(object):
		def __init__(self, name):
			self.name = name

		def __eq__(self, value):
			return self.is_equal(value)

		def is_equal(self, value):
			return Search.Node(self.name, {"is": value})

	class EqualityNodeBuilder(IsNodeBuilder):
		def __ne__(self, value):
			return self.is_not_equal(value)

		def is_not_equal(self, value):
			return Search.Node(self.name, {"is_not": value})

	class KeyValueNodeBuilder(object):
		def __init__(self, name):
			self.name = name

		def __eq__(self, value):
			return self.is_equal(value)

		def is_equal(self, value):
			return Search.Node(self.name, value)

		def __ne__(self, value):
			return self.is_not_equal(value)

		def is_not_equal(self, value):
			return Search.Node(self.name, not value)

	class PartialMatchNodeBuilder(EqualityNodeBuilder):
		def starts_with(self, value):
			return Search.Node(self.name, {"starts_with": value})

		def ends_with(self, value):
			return Search.Node(self.name, {"ends_with": value})

	class TextNodeBuilder(PartialMatchNodeBuilder):
		def contains(self, value):
			return Search.Node(self.name, {"contains": value})

	class Node(object):
		def __init__(self, name, dict):
			self.name = name
			self.dict = dict

		def to_param(self):
			return self.dict

	class MultipleValueNodeBuilder(object):
		def __init__(self, name, whitelist = []):
			self.name = name
			self.whitelist = whitelist

		def in_list(self, *values):
			if isinstance(values[0], list):
				values = values[0]

			invalid_args = set(values) - set(self.whitelist)
			if len(self.whitelist) > 0 and len(invalid_args) > 0:
				error_string = "Invalid argument(s) for %s: %s" % (self.name, ", ".join(invalid_args))
				raise AttributeError(error_string)
			return Search.Node(self.name, list(values))

		def __eq__(self, value):
			return self.in_list([value])

	class MultipleValueOrTextNodeBuilder(TextNodeBuilder, MultipleValueNodeBuilder):
		def __init__(self, name, whitelist = []):
			Search.MultipleValueNodeBuilder.__init__(self, name, whitelist)

	class RangeNodeBuilder(object):
		def __init__(self, name):
			self.name = name

		def __eq__(self, value):
			return self.is_equal(value)

		def is_equal(self, value):
			return Search.EqualityNodeBuilder(self.name) == value

		def __ge__(self, min):
			return self.greater_than_or_equal_to(min)

		def greater_than_or_equal_to(self, min):
			return Search.Node(self.name, {"min": min})

		def __le__(self, max):
			return self.less_than_or_equal_to(max)

		def less_than_or_equal_to(self, max):
			return Search.Node(self.name, {"max": max})

		def between(self, min, max):
			return Search.Node(self.name, {"min": min, "max": max})

########NEW FILE########
__FILENAME__ = settlement_batch_summary
from braintree.util.http import Http
import braintree
import warnings
from braintree.exceptions.not_found_error import NotFoundError
from braintree.resource_collection import ResourceCollection
from braintree.successful_result import SuccessfulResult
from braintree.error_result import ErrorResult
from braintree.resource import Resource
from braintree.configuration import Configuration

class SettlementBatchSummary(Resource):
    @staticmethod
    def generate(settlement_date, group_by_custom_field=None):
        return Configuration.gateway().settlement_batch_summary.generate(settlement_date, group_by_custom_field)

########NEW FILE########
__FILENAME__ = settlement_batch_summary_gateway
import braintree
from braintree.resource import Resource
from braintree.settlement_batch_summary import SettlementBatchSummary
from braintree.successful_result import SuccessfulResult
from braintree.error_result import ErrorResult

class SettlementBatchSummaryGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def generate(self, settlement_date, group_by_custom_field=None):
        criteria = {"settlement_date": settlement_date}

        if group_by_custom_field:
            criteria["group_by_custom_field"] = group_by_custom_field

        response = self.config.http().post('/settlement_batch_summary', {"settlement_batch_summary": criteria})
        if "settlement_batch_summary" in response:
            return SuccessfulResult({"settlement_batch_summary": SettlementBatchSummary(self.gateway, response["settlement_batch_summary"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

########NEW FILE########
__FILENAME__ = signature_service
import urllib
from braintree.util.crypto import Crypto

class SignatureService(object):

    def __init__(self, private_key, hashfunc=Crypto.sha1_hmac_hash):
        self.private_key = private_key
        self.hmac_hash = hashfunc

    def sign(self, data):
        equalities = ['%s=%s' % (str(key), str(data[key])) for key in data]
        data_string = '&'.join(equalities)
        return "%s|%s" % (self.hash(data_string), data_string)

    def hash(self, data):
        return self.hmac_hash(self.private_key, data)

########NEW FILE########
__FILENAME__ = status_event
from decimal import Decimal
from braintree.resource import Resource

class StatusEvent(Resource):
    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)

        self.amount = Decimal(self.amount)

########NEW FILE########
__FILENAME__ = subscription
from decimal import Decimal
from braintree.util.http import Http
import braintree
import warnings
from braintree.add_on import AddOn
from braintree.descriptor import Descriptor
from braintree.discount import Discount
from braintree.exceptions.not_found_error import NotFoundError
from braintree.resource_collection import ResourceCollection
from braintree.successful_result import SuccessfulResult
from braintree.error_result import ErrorResult
from braintree.transaction import Transaction
from braintree.resource import Resource
from braintree.configuration import Configuration

class Subscription(Resource):
    """
    A class representing a Subscription.

    An example of creating a subscription with all available fields::

        result = braintree.Subscription.create({
            "id": "my_subscription_id",
            "merchant_account_id": "merchant_account_one",
            "payment_method_token": "my_payment_token",
            "plan_id": "some_plan_id",
            "price": "29.95",
            "trial_duration": 1,
            "trial_duration_unit": braintree.Subscription.TrialDurationUnit.Month,
            "trial_period": True
        })

    For more information on Subscriptions, see https://www.braintreepayments.com/docs/python/subscriptions/overview

    """

    class TrialDurationUnit(object):
        """
        Constants representing trial duration units.  Available types are:

        * braintree.Subscription.TrialDurationUnit.Day
        * braintree.Subscription.TrialDurationUnit.Month
        """

        Day = "day"
        Month = "month"

    class Status(object):
        """
        Constants representing subscription statusues.  Available statuses are:

        * braintree.Subscription.Status.Active
        * braintree.Subscription.Status.Canceled
        * braintree.Subscription.Status.Expired
        * braintree.Subscription.Status.PastDue
        * braintree.Subscription.Status.Pending
        """

        Active = "Active"
        Canceled = "Canceled"
        Expired = "Expired"
        PastDue = "Past Due"
        Pending = "Pending"

    @staticmethod
    def create(params={}):
        """
        Create a Subscription

        Token and Plan are required:::

            result = braintree.Subscription.create({
                "payment_method_token": "my_payment_token",
                "plan_id": "some_plan_id",
            })

        """

        return Configuration.gateway().subscription.create(params)

    @staticmethod
    def create_signature():
        return [
            "billing_day_of_month",
            "first_billing_date",
            "id",
            "merchant_account_id",
            "never_expires",
            "number_of_billing_cycles",
            "payment_method_nonce",
            "payment_method_token",
            "plan_id",
            "price",
            "trial_duration",
            "trial_duration_unit",
            "trial_period",
            {
                "descriptor": [ "name", "phone" ]
            },
            {
                "options": [
                    "do_not_inherit_add_ons_or_discounts",
                    "start_immediately"
                ]
            }
        ] + Subscription._add_ons_discounts_signature()

    @staticmethod
    def find(subscription_id):
        """
        Find a subscription given a subscription_id.  This does not return a result
        object.  This will raise a :class:`NotFoundError <braintree.exceptions.not_found_error.NotFoundError>`
        if the provided subscription_id is not found. ::

            subscription = braintree.Subscription.find("my_subscription_id")
        """

        return Configuration.gateway().subscription.find(subscription_id)

    @staticmethod
    def retryCharge(subscription_id, amount=None):
        warnings.warn("Please use Subscription.retry_charge instead", DeprecationWarning)
        return Subscription.retry_charge(subscription_id, amount)

    @staticmethod
    def retry_charge(subscription_id, amount=None):
        return Configuration.gateway().subscription.retry_charge(subscription_id, amount)

    @staticmethod
    def update(subscription_id, params={}):
        """
        Update an existing subscription

        By subscription_id. The params are similar to create::


            result = braintree.Subscription.update("my_subscription_id", {
                "price": "9.99",
            })

        """

        return Configuration.gateway().subscription.update(subscription_id, params)

    @staticmethod
    def cancel(subscription_id):
        """
        Cancel a subscription

        By subscription_id::

            result = braintree.Subscription.cancel("my_subscription_id")

        """

        return Configuration.gateway().subscription.cancel(subscription_id)

    @staticmethod
    def search(*query):
        """
        Allows searching on subscriptions. There are two types of fields that are searchable: text and
        multiple value fields. Searchable text fields are:
        - plan_id
        - days_past_due

        Searchable multiple value fields are:
        - status

        For text fields, you can search using the following operators: ==, !=, starts_with, ends_with
        and contains. For mutiple value fields, you can search using the in_list operator. An example::

            braintree.Subscription.search([
                braintree.SubscriptionSearch.plan_id.starts_with("abc"),
                braintree.SubscriptionSearch.days_past_due == "30",
                braintree.SubscriptionSearch.status.in_list([braintree.Subscription.Status.PastDue])
            ])
        """

        return Configuration.gateway().subscription.search(*query)

    @staticmethod
    def update_signature():
        return [
            "id",
            "merchant_account_id",
            "never_expires",
            "number_of_billing_cycles",
            "payment_method_nonce",
            "payment_method_token",
            "plan_id",
            "price",
            {
                "descriptor": [ "name", "phone" ]
            },
            {
                "options": [ "prorate_charges", "replace_all_add_ons_and_discounts", "revert_subscription_on_proration_failure" ]
            }
        ] + Subscription._add_ons_discounts_signature()

    @staticmethod
    def _add_ons_discounts_signature():
        return [
            {
                "add_ons": [{
                    "add": ["amount", "inherited_from_id", "never_expires", "number_of_billing_cycles", "quantity"],
                    "remove": ["__any_key__"],
                    "update": ["amount", "existing_id", "never_expires", "number_of_billing_cycles", "quantity"]
                }],
                "discounts": [{
                    "add": ["amount", "inherited_from_id", "never_expires", "number_of_billing_cycles", "quantity"],
                    "remove": ["__any_key__"],
                    "update": ["amount", "existing_id", "never_expires", "number_of_billing_cycles", "quantity"]
                }]
            }
        ]

    def __init__(self, gateway, attributes):
        if "next_bill_amount" in attributes.keys():
            self._next_bill_amount = Decimal(attributes["next_bill_amount"])
            del(attributes["next_bill_amount"])
        Resource.__init__(self, gateway, attributes)
        if "price" in attributes:
            self.price = Decimal(self.price)
        if "balance" in attributes:
            self.balance = Decimal(self.balance)
        if "next_billing_period_amount" in attributes:
            self.next_billing_period_amount = Decimal(self.next_billing_period_amount)
        if "add_ons" in attributes:
            self.add_ons = [AddOn(gateway, add_on) for add_on in self.add_ons]
        if "descriptor" in attributes:
            self.descriptor = Descriptor(gateway, attributes.pop("descriptor"))
        if "discounts" in attributes:
            self.discounts = [Discount(gateway, discount) for discount in self.discounts]
        if "transactions" in attributes:
            self.transactions = [Transaction(gateway, transaction) for transaction in self.transactions]

    @property
    def next_bill_amount(self):
        warnings.warn("Please use Subscription.next_billing_period_amount instead", DeprecationWarning)
        return self._next_bill_amount

########NEW FILE########
__FILENAME__ = subscription_details
from braintree.attribute_getter import AttributeGetter

class SubscriptionDetails(AttributeGetter):
    pass

########NEW FILE########
__FILENAME__ = subscription_gateway
import re
import braintree
from braintree.subscription import Subscription
from braintree.error_result import ErrorResult
from braintree.exceptions.not_found_error import NotFoundError
from braintree.resource import Resource
from braintree.resource_collection import ResourceCollection
from braintree.successful_result import SuccessfulResult
from braintree.transaction import Transaction

class SubscriptionGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def cancel(self, subscription_id):
        response = self.config.http().put("/subscriptions/" + subscription_id + "/cancel")
        if "subscription" in response:
            return SuccessfulResult({"subscription": Subscription(self.gateway, response["subscription"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def create(self, params={}):
        Resource.verify_keys(params, Subscription.create_signature())
        response = self.config.http().post("/subscriptions", {"subscription": params})
        if "subscription" in response:
            return SuccessfulResult({"subscription": Subscription(self.gateway, response["subscription"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def find(self, subscription_id):
        try:
            if subscription_id == None or subscription_id.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/subscriptions/" + subscription_id)
            return Subscription(self.gateway, response["subscription"])
        except NotFoundError:
            raise NotFoundError("subscription with id " + subscription_id + " not found")

    def retry_charge(self, subscription_id, amount=None):
        response = self.config.http().post("/transactions", {"transaction": {
            "amount": amount,
            "subscription_id": subscription_id,
            "type": Transaction.Type.Sale
            }})
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def search(self, *query):
        if isinstance(query[0], list):
            query = query[0]

        response = self.config.http().post("/subscriptions/advanced_search_ids", {"search": self.__criteria(query)})
        return ResourceCollection(query, response, self.__fetch)

    def update(self, subscription_id, params={}):
        Resource.verify_keys(params, Subscription.update_signature())
        response = self.config.http().put("/subscriptions/" + subscription_id, {"subscription": params})
        if "subscription" in response:
            return SuccessfulResult({"subscription": Subscription(self.gateway, response["subscription"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def __criteria(self, query):
        criteria = {}
        for term in query:
            if criteria.get(term.name):
                criteria[term.name] = dict(criteria[term.name].items() + term.to_param().items())
            else:
                criteria[term.name] = term.to_param()
        return criteria

    def __fetch(self, query, ids):
        criteria = self.__criteria(query)
        criteria["ids"] = braintree.subscription_search.SubscriptionSearch.ids.in_list(ids).to_param()
        response = self.config.http().post("/subscriptions/advanced_search", {"search": criteria})
        return [Subscription(self.gateway, item) for item in ResourceCollection._extract_as_array(response["subscriptions"], "subscription")]


########NEW FILE########
__FILENAME__ = subscription_search
from braintree.util import Constants
from braintree import Subscription
from braintree.search import Search

class SubscriptionSearch:
    billing_cycles_remaining = Search.RangeNodeBuilder("billing_cycles_remaining")
    days_past_due = Search.RangeNodeBuilder("days_past_due")
    id = Search.TextNodeBuilder("id")
    ids = Search.MultipleValueNodeBuilder("ids")
    in_trial_period = Search.MultipleValueNodeBuilder("in_trial_period")
    merchant_account_id = Search.MultipleValueNodeBuilder("merchant_account_id")
    next_billing_date = Search.RangeNodeBuilder("next_billing_date")
    plan_id = Search.MultipleValueOrTextNodeBuilder("plan_id")
    price = Search.RangeNodeBuilder("price")
    status = Search.MultipleValueNodeBuilder("status", Constants.get_all_constant_values_from_class(Subscription.Status))
    transaction_id = Search.TextNodeBuilder("transaction_id")

########NEW FILE########
__FILENAME__ = successful_result
from braintree.attribute_getter import AttributeGetter

class SuccessfulResult(AttributeGetter):
    """
    An instance of this class is returned from most operations when the request is successful.  Call the name of the resource (eg, customer, credit_card, etc) to get the object::

        result = Transaction.sale({..})
        if result.is_success:
            transaction = result.transaction
        else:
            print [error.code for error in result.errors.all]
    """

    @property
    def is_success(self):
        """ Returns whether the result from the gateway is a successful response. """
        return True

########NEW FILE########
__FILENAME__ = credit_card_defaults
class CreditCardDefaults(object):
    CountryOfIssuance = "USA"
    IssuingBank = "NETWORK ONLY"

########NEW FILE########
__FILENAME__ = credit_card_numbers
class CreditCardNumbers(object):
    class CardTypeIndicators(object):
        Commercial = "4111111111131010"
        DurbinRegulated = "4111161010101010"
        Debit = "4117101010101010"
        Healthcare = "4111111510101010"
        Payroll  = "4111111114101010"
        Prepaid = "4111111111111210"
        IssuingBank = "4111111141010101"
        CountryOfIssuance = "4111111111121102"

        No  = "4111111111310101"
        Unknown = "4111111111112101"

    class FailsSandboxVerification(object):
        AmEx       = "378734493671000"
        Discover   = "6011000990139424"
        MasterCard = "5105105105105100"
        Visa       = "4000111111111115"

########NEW FILE########
__FILENAME__ = merchant_account
Approve = "approve_me"

InsufficientFundsContactUs = "insufficient_funds__contact"
AccountNotAuthorizedContactUs = "account_not_authorized__contact"
BankRejectedUpdateFundingInformation = "bank_rejected__update"
BankRejectedNone = "bank_rejected__none"

########NEW FILE########
__FILENAME__ = venmo_sdk
def generate_test_payment_method_code(number):
    return "stub-" + number

VisaPaymentMethodCode = generate_test_payment_method_code("4111111111111111")
InvalidPaymentMethodCode = generate_test_payment_method_code("invalid-payment-method-code")

Session = "stub-session"
InvalidSession = "stub-invalid-session"

########NEW FILE########
__FILENAME__ = transaction
import braintree
import urllib
import warnings
from decimal import Decimal
from braintree.add_on import AddOn
from braintree.disbursement_detail import DisbursementDetail
from braintree.dispute import Dispute
from braintree.discount import Discount
from braintree.successful_result import SuccessfulResult
from braintree.status_event import StatusEvent
from braintree.error_result import ErrorResult
from braintree.resource import Resource
from braintree.address import Address
from braintree.configuration import Configuration
from braintree.credit_card import CreditCard
from braintree.customer import Customer
from braintree.subscription_details import SubscriptionDetails
from braintree.resource_collection import ResourceCollection
from braintree.transparent_redirect import TransparentRedirect
from braintree.exceptions.not_found_error import NotFoundError
from braintree.descriptor import Descriptor

class Transaction(Resource):
    """
    A class representing Braintree Transaction objects.

    An example of creating an sale transaction with all available fields::

        result = Transaction.sale({
            "amount": "100.00",
            "order_id": "123",
            "channel": "MyShoppingCartProvider",
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2011",
                "cvv": "123"
            },
            "customer": {
                "first_name": "Dan",
                "last_name": "Smith",
                "company": "Braintree",
                "email": "dan@example.com",
                "phone": "419-555-1234",
                "fax": "419-555-1235",
                "website": "https://www.braintreepayments.com"
            },
            "billing": {
                "first_name": "Carl",
                "last_name": "Jones",
                "company": "Braintree",
                "street_address": "123 E Main St",
                "extended_address": "Suite 403",
                "locality": "Chicago",
                "region": "IL",
                "postal_code": "60622",
                "country_name": "United States of America"
            },
            "shipping": {
                "first_name": "Andrew",
                "last_name": "Mason",
                "company": "Braintree",
                "street_address": "456 W Main St",
                "extended_address": "Apt 2F",
                "locality": "Bartlett",
                "region": "IL",
                "postal_code": "60103",
                "country_name": "United States of America"
            }
        })

        print(result.transaction.amount)
        print(result.transaction.order_id)

    For more information on Transactions, see https://www.braintreepayments.com/docs/python/transactions/create

    """

    def __repr__(self):
        detail_list = ["amount", "credit_card", "payment_method_token", "customer_id"]
        return super(Transaction, self).__repr__(detail_list)

    class CreatedUsing(object):
        """
        Constants representing how the transaction was created.  Available types are:

        * braintree.Transaction.CreatedUsing.FullInformation
        * braintree.Transaction.CreatedUsing.Token
        """

        FullInformation = "full_information"
        Token           = "token"
        Unrecognized    = "unrecognized"

    class GatewayRejectionReason(object):
        """
        Constants representing gateway rejection reasons. Available types are:

        * braintree.Transaction.GatewayRejectionReason.Avs
        * braintree.Transaction.GatewayRejectionReason.AvsAndCvv
        * braintree.Transaction.GatewayRejectionReason.Cvv
        * braintree.Transaction.GatewayRejectionReason.Duplicate
        """
        Avs          = "avs"
        AvsAndCvv    = "avs_and_cvv"
        Cvv          = "cvv"
        Duplicate    = "duplicate"
        Fraud        = "fraud"
        Unrecognized = "unrecognized"

    class Source(object):
        Api          = "api"
        ControlPanel = "control_panel"
        Recurring    = "recurring"
        Unrecognized = "unrecognized"

    class EscrowStatus(object):
        """
        Constants representing transaction escrow statuses. Available statuses are:

        * braintree.Transaction.EscrowStatus.HoldPending
        * braintree.Transaction.EscrowStatus.Held
        * braintree.Transaction.EscrowStatus.ReleasePending
        * braintree.Transaction.EscrowStatus.Released
        * braintree.Transaction.EscrowStatus.Refunded
        """

        HoldPending    = "hold_pending"
        Held           = "held"
        ReleasePending = "release_pending"
        Released       = "released"
        Refunded       = "refunded"
        Unrecognized   = "unrecognized"

    class Status(object):
        """
        Constants representing transaction statuses. Available statuses are:

        * braintree.Transaction.Status.Authorized
        * braintree.Transaction.Status.Authorizing
        * braintree.Transaction.Status.Failed
        * braintree.Transaction.Status.GatewayRejected
        * braintree.Transaction.Status.ProcessorDeclined
        * braintree.Transaction.Status.Settled
        * braintree.Transaction.Status.SettlementFailed
        * braintree.Transaction.Status.Settling
        * braintree.Transaction.Status.SubmittedForSettlement
        * braintree.Transaction.Status.Void
        """

        AuthorizationExpired   = "authorization_expired"
        Authorized             = "authorized"
        Authorizing            = "authorizing"
        Failed                 = "failed"
        GatewayRejected        = "gateway_rejected"
        ProcessorDeclined      = "processor_declined"
        Settled                = "settled"
        SettlementFailed       = "settlement_failed"
        Settling               = "settling"
        SubmittedForSettlement = "submitted_for_settlement"
        Voided                 = "voided"
        Unrecognized           = "unrecognized"

    class Type(object):
        """
        Constants representing transaction types. Available types are:

        * braintree.Transaction.Type.Credit
        * braintree.Transaction.Type.Sale
        """

        Credit = "credit"
        Sale = "sale"

    @staticmethod
    def clone_transaction(transaction_id, params):
        return Configuration.gateway().transaction.clone_transaction(transaction_id, params)

    @staticmethod
    def cancel_release(transaction_id):
        """
        Cancels a pending release from escrow for a transaction.

        Requires the transaction id::

            result = braintree.Transaction.cancel_release("my_transaction_id")

        """

        return Configuration.gateway().transaction.cancel_release(transaction_id)

    @staticmethod
    def confirm_transparent_redirect(query_string):
        """
        Confirms a transparent redirect request. It expects the query string from the
        redirect request. The query string should _not_ include the leading "?" character. ::

            result = braintree.Transaction.confirm_transparent_redirect_request("foo=bar&id=12345")
        """

        warnings.warn("Please use TransparentRedirect.confirm instead", DeprecationWarning)
        return Configuration.gateway().transaction.confirm_transparent_redirect(query_string)

    @staticmethod
    def credit(params={}):
        """
        Creates a transaction of type Credit.

        Amount is required. Also, a credit card,
        customer_id or payment_method_token is required. ::

            result = braintree.Transaction.credit({
                "amount": "100.00",
                "payment_method_token": "my_token"
            })

            result = braintree.Transaction.credit({
                "amount": "100.00",
                "credit_card": {
                    "number": "4111111111111111",
                    "expiration_date": "12/2012"
                }
            })

            result = braintree.Transaction.credit({
                "amount": "100.00",
                "customer_id": "my_customer_id"
            })

        """

        params["type"] = Transaction.Type.Credit
        return Transaction.create(params)

    @staticmethod
    def find(transaction_id):
        """
        Find a transaction, given a transaction_id. This does not return
        a result object. This will raise a :class:`NotFoundError <braintree.exceptions.not_found_error.NotFoundError>` if the provided
        credit_card_id is not found. ::

            transaction = braintree.Transaction.find("my_transaction_id")
        """
        return Configuration.gateway().transaction.find(transaction_id)


    @staticmethod
    def hold_in_escrow(transaction_id):
        """
        Holds an existing submerchant transaction for escrow.

        It expects a transaction_id.::

            result = braintree.Transaction.hold_in_escrow("my_transaction_id")
        """
        return Configuration.gateway().transaction.hold_in_escrow(transaction_id)


    @staticmethod
    def refund(transaction_id, amount=None):
        """
        Refunds an existing transaction.

        It expects a transaction_id.::

            result = braintree.Transaction.refund("my_transaction_id")

        """

        return Configuration.gateway().transaction.refund(transaction_id, amount)


    @staticmethod
    def sale(params={}):
        """
        Creates a transaction of type Sale. Amount is required. Also, a credit card,
        customer_id or payment_method_token is required. ::

            result = braintree.Transaction.sale({
                "amount": "100.00",
                "payment_method_token": "my_token"
            })

            result = braintree.Transaction.sale({
                "amount": "100.00",
                "credit_card": {
                    "number": "4111111111111111",
                    "expiration_date": "12/2012"
                }
            })

            result = braintree.Transaction.sale({
                "amount": "100.00",
                "customer_id": "my_customer_id"
            })
        """

        params["type"] = Transaction.Type.Sale
        return Transaction.create(params)

    @staticmethod
    def search(*query):
        return Configuration.gateway().transaction.search(*query)

    @staticmethod
    def release_from_escrow(transaction_id):
        """
        Submits an escrowed transaction for release.

        Requires the transaction id::

            result = braintree.Transaction.release_from_escrow("my_transaction_id")

        """

        return Configuration.gateway().transaction.release_from_escrow(transaction_id)

    @staticmethod
    def submit_for_settlement(transaction_id, amount=None):
        """
        Submits an authorized transaction for settlement.

        Requires the transaction id::

            result = braintree.Transaction.submit_for_settlement("my_transaction_id")

        """

        return Configuration.gateway().transaction.submit_for_settlement(transaction_id, amount)

    @staticmethod
    def tr_data_for_credit(tr_data, redirect_url):
        """
        Builds tr_data for a Transaction of type Credit
        """
        return Configuration.gateway().transaction.tr_data_for_credit(tr_data, redirect_url)

    @staticmethod
    def tr_data_for_sale(tr_data, redirect_url):
        """
        Builds tr_data for a Transaction of type Sale
        """
        return Configuration.gateway().transaction.tr_data_for_sale(tr_data, redirect_url)

    @staticmethod
    def transparent_redirect_create_url():
        """
        Returns the url to be used for creating Transactions through transparent redirect.
        """

        warnings.warn("Please use TransparentRedirect.url instead", DeprecationWarning)
        return Configuration.gateway().transaction.transparent_redirect_create_url()

    @staticmethod
    def void(transaction_id):
        """
        Voids an existing transaction.

        It expects a transaction_id.::

            result = braintree.Transaction.void("my_transaction_id")

        """

        return Configuration.gateway().transaction.void(transaction_id)

    @staticmethod
    def create(params):
        """
        Creates a transaction. Amount and type are required. Also, a credit card,
        customer_id or payment_method_token is required. ::

            result = braintree.Transaction.sale({
                "type": braintree.Transaction.Type.Sale,
                "amount": "100.00",
                "payment_method_token": "my_token"
            })

            result = braintree.Transaction.sale({
                "type": braintree.Transaction.Type.Sale,
                "amount": "100.00",
                "credit_card": {
                    "number": "4111111111111111",
                    "expiration_date": "12/2012"
                }
            })

            result = braintree.Transaction.sale({
                "type": braintree.Transaction.Type.Sale,
                "amount": "100.00",
                "customer_id": "my_customer_id"
            })
        """
        return Configuration.gateway().transaction.create(params)

    @staticmethod
    def clone_signature():
        return ["amount", "channel", {"options": ["submit_for_settlement"]}]

    @staticmethod
    def create_signature():
        return [
            "amount", "customer_id", "device_session_id", "fraud_merchant_id", "merchant_account_id", "order_id", "channel",
            "payment_method_token", "purchase_order_number", "recurring", "shipping_address_id",
            "device_data", "billing_address_id", "payment_method_nonce",
            "tax_amount", "tax_exempt", "type", "venmo_sdk_payment_method_code", "service_fee_amount",
            {
                "credit_card": [
                    "token", "cardholder_name", "cvv", "expiration_date", "expiration_month", "expiration_year", "number"
                ]
            },
            {
                "customer": [
                    "id", "company", "email", "fax", "first_name", "last_name", "phone", "website"
                ]
            },
            {
                "billing": [
                    "first_name", "last_name", "company", "country_code_alpha2", "country_code_alpha3",
                    "country_code_numeric", "country_name", "extended_address", "locality",
                    "postal_code", "region", "street_address"
                ]
            },
            {
                "shipping": [
                    "first_name", "last_name", "company", "country_code_alpha2", "country_code_alpha3",
                    "country_code_numeric", "country_name", "extended_address", "locality",
                    "postal_code", "region", "street_address"
                ]
            },
            {
                "options": [
                    "add_billing_address_to_payment_method",
                    "hold_in_escrow",
                    "store_in_vault",
                    "store_in_vault_on_success",
                    "store_shipping_address_in_vault",
                    "submit_for_settlement",
                    "venmo_sdk_session"
                ]
            },
            {"custom_fields": ["__any_key__"]},
            {"descriptor": ["name", "phone"]}
        ]

    def __init__(self, gateway, attributes):
        if "refund_id" in attributes.keys():
            self._refund_id = attributes["refund_id"]
            del(attributes["refund_id"])
        else:
            self._refund_id = None

        Resource.__init__(self, gateway, attributes)

        self.amount = Decimal(self.amount)
        if self.tax_amount:
            self.tax_amount = Decimal(self.tax_amount)
        if "billing" in attributes:
            self.billing_details = Address(gateway, attributes.pop("billing"))
        if "credit_card" in attributes:
            self.credit_card_details = CreditCard(gateway, attributes.pop("credit_card"))
        if "customer" in attributes:
            self.customer_details = Customer(gateway, attributes.pop("customer"))
        if "shipping" in attributes:
            self.shipping_details = Address(gateway, attributes.pop("shipping"))
        if "add_ons" in attributes:
            self.add_ons = [AddOn(gateway, add_on) for add_on in self.add_ons]
        if "discounts" in attributes:
            self.discounts = [Discount(gateway, discount) for discount in self.discounts]
        if "status_history" in attributes:
            self.status_history = [StatusEvent(gateway, status_event) for status_event in self.status_history]
        if "subscription" in attributes:
            self.subscription_details = SubscriptionDetails(attributes.pop("subscription"))
        if "descriptor" in attributes:
            self.descriptor = Descriptor(gateway, attributes.pop("descriptor"))
        if "disbursement_details" in attributes:
            self.disbursement_details = DisbursementDetail(attributes.pop("disbursement_details"))
        if "disputes" in attributes:
            self.disputes = [Dispute(dispute) for dispute in self.disputes]

    @property
    def refund_id(self):
        warnings.warn("Please use Transaction.refund_ids instead", DeprecationWarning)
        return self._refund_id

    @property
    def vault_billing_address(self):
        """
        The vault billing address associated with this transaction
        """

        return self.gateway.address.find(self.customer_details.id, self.billing_details.id)

    @property
    def vault_credit_card(self):
        """
        The vault credit card associated with this transaction
        """
        if self.credit_card_details.token is None:
            return None
        return self.gateway.credit_card.find(self.credit_card_details.token)

    @property
    def vault_customer(self):
        """
        The vault customer associated with this transaction
        """
        if self.customer_details.id is None:
            return None
        return self.gateway.customer.find(self.customer_details.id)

    @property
    def is_disbursed(self):
       return self.disbursement_details.is_valid


########NEW FILE########
__FILENAME__ = transaction_amounts
class TransactionAmounts(object):
    """ A class of constants for transaction amounts that will cause different statuses. """

    Authorize = "1000.00"
    Decline = "2000.00"
    Fail = "3000.00"

########NEW FILE########
__FILENAME__ = transaction_gateway
import braintree
from braintree.error_result import ErrorResult
from braintree.resource import Resource
from braintree.resource_collection import ResourceCollection
from braintree.successful_result import SuccessfulResult
from braintree.transaction import Transaction
from braintree.transparent_redirect import TransparentRedirect
from braintree.exceptions.not_found_error import NotFoundError
from braintree.exceptions.down_for_maintenance_error import DownForMaintenanceError

class TransactionGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def clone_transaction(self, transaction_id, params):
        Resource.verify_keys(params, Transaction.clone_signature())
        return self._post("/transactions/" + transaction_id + "/clone", {"transaction-clone": params})

    def cancel_release(self, transaction_id):
        response = self.config.http().put("/transactions/" + transaction_id + "/cancel_release", {})
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def confirm_transparent_redirect(self, query_string):
        id = self.gateway.transparent_redirect._parse_and_validate_query_string(query_string)["id"][0]
        return self._post("/transactions/all/confirm_transparent_redirect_request", {"id": id})

    def create(self, params):
        Resource.verify_keys(params, Transaction.create_signature())
        return self._post("/transactions", {"transaction": params})

    def find(self, transaction_id):
        try:
            if transaction_id == None or transaction_id.strip() == "":
                raise NotFoundError()
            response = self.config.http().get("/transactions/" + transaction_id)
            return Transaction(self.gateway, response["transaction"])
        except NotFoundError:
            raise NotFoundError("transaction with id " + transaction_id + " not found")

    def hold_in_escrow(self, transaction_id):
        """
        Holds an existing submerchant transaction for escrow. It expects a transaction_id. ::

            result = braintree.Transaction.hold_in_escrow("my_transaction_id")
        """

        response = self.config.http().put("/transactions/" + transaction_id + "/hold_in_escrow", {})
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def refund(self, transaction_id, amount=None):
        """
        Refunds an existing transaction. It expects a transaction_id. ::

            result = braintree.Transaction.refund("my_transaction_id")
        """

        response = self.config.http().post("/transactions/" + transaction_id + "/refund", {"transaction": {"amount": amount}})
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def search(self, *query):
        if isinstance(query[0], list):
            query = query[0]

        response = self.config.http().post("/transactions/advanced_search_ids", {"search": self.__criteria(query)})
        if "search_results" in response:
            return ResourceCollection(query, response, self.__fetch)
        else:
            raise DownForMaintenanceError("search timeout")

    def release_from_escrow(self, transaction_id):
        response = self.config.http().put("/transactions/" + transaction_id + "/release_from_escrow", {})
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def submit_for_settlement(self, transaction_id, amount=None):
        response = self.config.http().put("/transactions/" + transaction_id + "/submit_for_settlement",
                {"transaction": {"amount": amount}})
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def tr_data_for_credit(self, tr_data, redirect_url):
        if "transaction" not in tr_data:
            tr_data["transaction"] = {}
        tr_data["transaction"]["type"] = Transaction.Type.Credit
        Resource.verify_keys(tr_data, [{"transaction": Transaction.create_signature()}])
        tr_data["kind"] = TransparentRedirect.Kind.CreateTransaction
        return self.gateway.transparent_redirect.tr_data(tr_data, redirect_url)

    def tr_data_for_sale(self, tr_data, redirect_url):
        if "transaction" not in tr_data:
            tr_data["transaction"] = {}
        tr_data["transaction"]["type"] = Transaction.Type.Sale
        Resource.verify_keys(tr_data, [{"transaction": Transaction.create_signature()}])
        tr_data["kind"] = TransparentRedirect.Kind.CreateTransaction
        return self.gateway.transparent_redirect.tr_data(tr_data, redirect_url)

    def transparent_redirect_create_url(self):
        return self.config.base_merchant_url() + "/transactions/all/create_via_transparent_redirect_request"

    def void(self, transaction_id):
        response = self.config.http().put("/transactions/" + transaction_id + "/void")
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])

    def __fetch(self, query, ids):
        criteria = self.__criteria(query)
        criteria["ids"] = braintree.transaction_search.TransactionSearch.ids.in_list(ids).to_param()
        response = self.config.http().post("/transactions/advanced_search", {"search": criteria})
        return [Transaction(self.gateway, item) for item in  ResourceCollection._extract_as_array(response["credit_card_transactions"], "transaction")]

    def __criteria(self, query):
        criteria = {}
        for term in query:
            if criteria.get(term.name):
                criteria[term.name] = dict(criteria[term.name].items() + term.to_param().items())
            else:
                criteria[term.name] = term.to_param()
        return criteria

    def _post(self, url, params={}):
        response = self.config.http().post(url, params)
        if "transaction" in response:
            return SuccessfulResult({"transaction": Transaction(self.gateway, response["transaction"])})
        elif "api_error_response" in response:
            return ErrorResult(self.gateway, response["api_error_response"])


########NEW FILE########
__FILENAME__ = transaction_search
from braintree.credit_card import CreditCard
from braintree.search import Search
from braintree.transaction import Transaction
from braintree.util import Constants

class TransactionSearch:
    billing_first_name           = Search.TextNodeBuilder("billing_first_name")
    billing_company              = Search.TextNodeBuilder("billing_company")
    billing_country_name         = Search.TextNodeBuilder("billing_country_name")
    billing_extended_address     = Search.TextNodeBuilder("billing_extended_address")
    billing_first_name           = Search.TextNodeBuilder("billing_first_name")
    billing_last_name            = Search.TextNodeBuilder("billing_last_name")
    billing_locality             = Search.TextNodeBuilder("billing_locality")
    billing_postal_code          = Search.TextNodeBuilder("billing_postal_code")
    billing_region               = Search.TextNodeBuilder("billing_region")
    billing_street_address       = Search.TextNodeBuilder("billing_street_address")
    credit_card_cardholder_name  = Search.TextNodeBuilder("credit_card_cardholder_name")
    currency                     = Search.TextNodeBuilder("currency")
    customer_company             = Search.TextNodeBuilder("customer_company")
    customer_email               = Search.TextNodeBuilder("customer_email")
    customer_fax                 = Search.TextNodeBuilder("customer_fax")
    customer_first_name          = Search.TextNodeBuilder("customer_first_name")
    customer_id                  = Search.TextNodeBuilder("customer_id")
    customer_last_name           = Search.TextNodeBuilder("customer_last_name")
    customer_phone               = Search.TextNodeBuilder("customer_phone")
    customer_website             = Search.TextNodeBuilder("customer_website")
    id                           = Search.TextNodeBuilder("id")
    order_id                     = Search.TextNodeBuilder("order_id")
    payment_method_token         = Search.TextNodeBuilder("payment_method_token")
    processor_authorization_code = Search.TextNodeBuilder("processor_authorization_code")
    settlement_batch_id          = Search.TextNodeBuilder("settlement_batch_id")
    shipping_company             = Search.TextNodeBuilder("shipping_company")
    shipping_country_name        = Search.TextNodeBuilder("shipping_country_name")
    shipping_extended_address    = Search.TextNodeBuilder("shipping_extended_address")
    shipping_first_name          = Search.TextNodeBuilder("shipping_first_name")
    shipping_last_name           = Search.TextNodeBuilder("shipping_last_name")
    shipping_locality            = Search.TextNodeBuilder("shipping_locality")
    shipping_postal_code         = Search.TextNodeBuilder("shipping_postal_code")
    shipping_region              = Search.TextNodeBuilder("shipping_region")
    shipping_street_address      = Search.TextNodeBuilder("shipping_street_address")

    credit_card_expiration_date  = Search.EqualityNodeBuilder("credit_card_expiration_date")
    credit_card_number           = Search.PartialMatchNodeBuilder("credit_card_number")

    ids                          = Search.MultipleValueNodeBuilder("ids")
    merchant_account_id          = Search.MultipleValueNodeBuilder("merchant_account_id")

    created_using = Search.MultipleValueNodeBuilder(
        "created_using",
        Constants.get_all_constant_values_from_class(Transaction.CreatedUsing)
    )

    credit_card_card_type = Search.MultipleValueNodeBuilder(
        "credit_card_card_type",
        Constants.get_all_constant_values_from_class(CreditCard.CardType)
    )

    credit_card_customer_location = Search.MultipleValueNodeBuilder(
        "credit_card_customer_location",
        Constants.get_all_constant_values_from_class(CreditCard.CustomerLocation)
    )

    source = Search.MultipleValueNodeBuilder(
        "source",
        Constants.get_all_constant_values_from_class(Transaction.Source)
    )

    status = Search.MultipleValueNodeBuilder(
        "status",
        Constants.get_all_constant_values_from_class(Transaction.Status)
    )

    type = Search.MultipleValueNodeBuilder(
        "type",
        Constants.get_all_constant_values_from_class(Transaction.Type)
    )

    refund = Search.KeyValueNodeBuilder("refund")

    amount = Search.RangeNodeBuilder("amount")
    authorization_expired_at = Search.RangeNodeBuilder("authorization_expired_at")
    authorized_at = Search.RangeNodeBuilder("authorized_at")
    created_at = Search.RangeNodeBuilder("created_at")
    disbursement_date = Search.RangeNodeBuilder("disbursement_date")
    dispute_date = Search.RangeNodeBuilder("dispute_date")
    failed_at = Search.RangeNodeBuilder("failed_at")
    gateway_rejected_at = Search.RangeNodeBuilder("gateway_rejected_at")
    processor_declined_at = Search.RangeNodeBuilder("processor_declined_at")
    settled_at = Search.RangeNodeBuilder("settled_at")
    submitted_for_settlement_at = Search.RangeNodeBuilder("submitted_for_settlement_at")
    voided_at = Search.RangeNodeBuilder("voided_at")

########NEW FILE########
__FILENAME__ = transparent_redirect
import braintree
from braintree.configuration import Configuration

class TransparentRedirect:
    """
    A class used for Transparent Redirect operations
    """

    class Kind(object):
        CreateCustomer = "create_customer"
        UpdateCustomer = "update_customer"
        CreatePaymentMethod = "create_payment_method"
        UpdatePaymentMethod = "update_payment_method"
        CreateTransaction = "create_transaction"

    @staticmethod
    def confirm(query_string):
        """
        Confirms a transparent redirect request. It expects the query string from the
        redirect request. The query string should _not_ include the leading "?" character. ::

            result = braintree.TransparentRedirect.confirm("foo=bar&id=12345")
        """
        return Configuration.gateway().transparent_redirect.confirm(query_string)


    @staticmethod
    def tr_data(data, redirect_url):
        return Configuration.gateway().transparent_redirect.tr_data(data, redirect_url)

    @staticmethod
    def url():
        """
        Returns the url for POSTing Transparent Redirect HTML forms
        """
        return Configuration.gateway().transparent_redirect.url()


########NEW FILE########
__FILENAME__ = transparent_redirect_gateway
import cgi
from datetime import datetime
import urllib
import braintree
from braintree.util.crypto import Crypto
from braintree.error_result import ErrorResult
from braintree.exceptions.forged_query_string_error import ForgedQueryStringError
from braintree.util.http import Http
from braintree.signature_service import SignatureService
from braintree.successful_result import SuccessfulResult
from braintree.transparent_redirect import TransparentRedirect

class TransparentRedirectGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def confirm(self, query_string):
        """
        Confirms a transparent redirect request. It expects the query string from the
        redirect request. The query string should _not_ include the leading "?" character. ::

            result = braintree.TransparentRedirect.confirm("foo=bar&id=12345")
        """
        parsed_query_string = self._parse_and_validate_query_string(query_string)
        confirmation_gateway = {
            TransparentRedirect.Kind.CreateCustomer: "customer",
            TransparentRedirect.Kind.UpdateCustomer: "customer",
            TransparentRedirect.Kind.CreatePaymentMethod: "credit_card",
            TransparentRedirect.Kind.UpdatePaymentMethod: "credit_card",
            TransparentRedirect.Kind.CreateTransaction: "transaction"
        }[parsed_query_string["kind"][0]]

        return getattr(self.gateway, confirmation_gateway)._post("/transparent_redirect_requests/" + parsed_query_string["id"][0] + "/confirm")

    def tr_data(self, data, redirect_url):
        data = self.__flatten_dictionary(data)
        date_string = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        data["time"] = date_string
        data["redirect_url"] = redirect_url
        data["public_key"] = self.config.public_key
        data["api_version"] = self.config.api_version()

        return SignatureService(self.config.private_key).sign(data)

    def url(self):
        """
        Returns the url for POSTing Transparent Redirect HTML forms
        """
        return self.config.base_merchant_url() + "/transparent_redirect_requests"

    def _parse_and_validate_query_string(self, query_string):
        query_params = cgi.parse_qs(query_string)
        http_status = int(query_params["http_status"][0])
        message = query_params.get("bt_message")
        if message != None:
            message = message[0]

        if Http.is_error_status(http_status):
            Http.raise_exception_from_status(http_status, message)

        if not self._is_valid_tr_query_string(query_string):
            raise ForgedQueryStringError

        return query_params

    def _is_valid_tr_query_string(self, query_string):
        content, hash = query_string.split("&hash=")
        return hash == Crypto.sha1_hmac_hash(self.config.private_key, content)

    def __flatten_dictionary(self, params, parent=None):
        data = {}
        for key, val in params.iteritems():
            full_key = parent + "[" + key + "]" if parent else key
            if isinstance(val, dict):
                data.update(self.__flatten_dictionary(val, full_key))
            else:
                data[full_key] = val
        return data


########NEW FILE########
__FILENAME__ = constants
class Constants(object):
    @staticmethod
    def get_all_constant_values_from_class(klass):
        return [klass.__dict__[item] for item in dir(klass) if not item.startswith("__")]

########NEW FILE########
__FILENAME__ = crypto
import hashlib
import hmac

class Crypto:
    @staticmethod
    def sha1_hmac_hash(secret_key, content):
        return hmac.new(hashlib.sha1(secret_key).digest(), content, hashlib.sha1).hexdigest()

    @staticmethod
    def sha256_hmac_hash(secret_key, content):
        return hmac.new(hashlib.sha256(secret_key).digest(), content, hashlib.sha256).hexdigest()

    @staticmethod
    def secure_compare(left, right):
        if left == None or right == None:
            return False

        left_bytes = bytearray(left)
        right_bytes = bytearray(right)

        if len(left_bytes) != len(right_bytes):
            return False

        result = 0
        for left_byte, right_byte in zip(left_bytes, right_bytes):
            result |= left_byte ^ right_byte
        return result == 0

########NEW FILE########
__FILENAME__ = generator
import datetime
import types
from decimal import Decimal

class Generator(object):
    def __init__(self, dict):
        self.dict = dict

    def generate(self):
        return self.__generate_dict(self.dict)

    def __escape(self, value):
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace("\"", "&quot;");

    def __generate_boolean(self, value):
        return str(value).lower()

    def __generate_datetime(self, value):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    def __generate_dict(self, dictionary):
        xml = ""
        for key, val in dictionary.iteritems():
            xml += self.__generate_node(key, val)
        return xml

    def __generate_list(self, list):
        xml = ""
        for item in list:
            xml += self.__generate_node("item", item)
        return xml

    def __generate_node(self, key, value):
        open_tag = "<" + self.__escape(key) + ">"
        close_tag = "</" + self.__escape(key) + ">"

        if isinstance(value, unicode):
            return open_tag + self.__escape(value).encode('ascii', 'xmlcharrefreplace') + close_tag
        elif isinstance(value, str):
            return open_tag + self.__escape(value) + close_tag
        elif isinstance(value, Decimal):
            return open_tag + str(value) + close_tag
        elif isinstance(value, dict):
            return open_tag + self.__generate_dict(value) + close_tag
        elif isinstance(value, list):
            open_tag = "<" + key + " type=\"array\">"
            return open_tag + self.__generate_list(value) + close_tag
        elif isinstance(value, bool):
            open_tag = "<" + key + " type=\"boolean\">"
            return open_tag + self.__generate_boolean(value) + close_tag
        elif isinstance(value, (int, long)) and not isinstance(value, bool):
            open_tag = "<" + key + " type=\"integer\">"
            return open_tag + str(value) + close_tag
        elif isinstance(value, types.NoneType):
            return open_tag + close_tag
        elif isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
            open_tag = "<" + key + " type=\"datetime\">"
            return open_tag + self.__generate_datetime(value) + close_tag
        else:
            raise RuntimeError("Unexpected XML node type: " + str(type(value)))

########NEW FILE########
__FILENAME__ = http
import base64
import braintree
from braintree import version
from braintree.util.xml_util import XmlUtil
from braintree.exceptions.authentication_error import AuthenticationError
from braintree.exceptions.authorization_error import AuthorizationError
from braintree.exceptions.down_for_maintenance_error import DownForMaintenanceError
from braintree.exceptions.not_found_error import NotFoundError
from braintree.exceptions.server_error import ServerError
from braintree.exceptions.unexpected_error import UnexpectedError
from braintree.exceptions.upgrade_required_error import UpgradeRequiredError

class Http(object):
    @staticmethod
    def is_error_status(status):
        return status not in [200, 201, 422]

    @staticmethod
    def raise_exception_from_status(status, message=None):
        if status == 401:
            raise AuthenticationError()
        elif status == 403:
            raise AuthorizationError(message)
        elif status == 404:
            raise NotFoundError()
        elif status == 426:
            raise UpgradeRequiredError()
        elif status == 500:
            raise ServerError()
        elif status == 503:
            raise DownForMaintenanceError()
        else:
            raise UnexpectedError("Unexpected HTTP_RESPONSE " + str(status))

    def __init__(self, config):
        self.config = config
        self.environment = self.config.environment

    def post(self, path, params={}):
        return self.__http_do("POST", path, params)

    def delete(self, path):
        return self.__http_do("DELETE", path)

    def get(self, path):
        return self.__http_do("GET", path)

    def put(self, path, params={}):
        return self.__http_do("PUT", path, params)

    def __http_do(self, http_verb, path, params=None):
        http_strategy = self.config.http_strategy()
        request_body = XmlUtil.xml_from_dict(params) if params else ''
        full_path = self.config.base_merchant_path() + path
        status, response_body = http_strategy.http_do(http_verb, full_path, self.__headers(), request_body)

        if Http.is_error_status(status):
            Http.raise_exception_from_status(status)
        else:
            if len(response_body.strip()) == 0:
                return {}
            else:
                return XmlUtil.dict_from_xml(response_body)

    def __authorization_header(self):
        return "Basic " + base64.encodestring(self.config.public_key + ":" + self.config.private_key).strip()

    def __headers(self):
        return {
            "Accept": "application/xml",
            "Authorization": self.__authorization_header(),
            "Content-type": "application/xml",
            "User-Agent": "Braintree Python " + version.Version,
            "X-ApiVersion": braintree.configuration.Configuration.api_version()
        }


########NEW FILE########
__FILENAME__ = httplib_strategy
import httplib

class HttplibStrategy(object):
    def __init__(self, config, environment):
        self.config = config
        self.environment = environment

    def http_do(self, http_verb, path, headers, request_body):
        if self.environment.is_ssl:
            conn = httplib.HTTPSConnection(self.environment.server, self.environment.port)
        else:
            conn = httplib.HTTPConnection(self.environment.server, self.environment.port)

        conn.request(http_verb, path, request_body, headers)
        response = conn.getresponse()
        status = response.status
        response_body = response.read()
        conn.close()
        return [status, response_body]

########NEW FILE########
__FILENAME__ = pycurl_strategy
import httplib
import StringIO

try:
    import pycurl
except ImportError:
    pass

class PycurlStrategy(object):
    def __init__(self, config, environment):
        self.config = config
        self.environment = environment

    def http_do(self, http_verb, path, headers, request_body):
        curl = pycurl.Curl()
        response = StringIO.StringIO()

        if self.environment.ssl_certificate:
            curl.setopt(pycurl.CAINFO, self.environment.ssl_certificate)
        curl.setopt(pycurl.SSL_VERIFYPEER, 1)
        curl.setopt(pycurl.SSL_VERIFYHOST, 2)
        curl.setopt(pycurl.URL, str(self.environment.base_url + path))
        curl.setopt(pycurl.ENCODING, 'gzip')
        curl.setopt(pycurl.WRITEFUNCTION, response.write)
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.HTTPHEADER, self._format_headers(headers))
        self._set_request_method_and_body(curl, http_verb, request_body)

        curl.perform()

        status = curl.getinfo(pycurl.HTTP_CODE)
        response = response.getvalue()
        return [status, response]

    def _set_request_method_and_body(self, curl, method, body):
        if method == "GET":
            curl.setopt(pycurl.HTTPGET, 1)
        elif method == "POST":
            curl.setopt(pycurl.POST, 1)
            curl.setopt(pycurl.POSTFIELDSIZE, len(body))
        elif method == "PUT":
            curl.setopt(pycurl.PUT, 1)
            curl.setopt(pycurl.INFILESIZE, len(body))
        elif method == "DELETE":
            curl.setopt(curl.CUSTOMREQUEST, "DELETE")

        if body:
            curl.setopt(pycurl.READFUNCTION, StringIO.StringIO(body).read)

    def _format_headers(self, headers):
        return [key + ": " + value for key, value in headers.iteritems()]

########NEW FILE########
__FILENAME__ = requests_strategy
try:
    import requests
except ImportError:
    pass

class RequestsStrategy(object):
    def __init__(self, config, environment):
        self.config = config
        self.environment = environment

    def http_do(self, http_verb, path, headers, request_body):
        response = requests.request(
            http_verb,
            self.environment.base_url + path,
            headers=headers,
            data=request_body,
            verify=self.environment.ssl_certificate
        )

        return [response.status_code, response.text]

########NEW FILE########
__FILENAME__ = parser
from xml.dom import minidom
from datetime import datetime
import re

class Parser(object):
    def __init__(self, xml):
        self.doc = minidom.parseString("><".join(re.split(">\s+<", xml)).strip())

    def parse(self):
        return {self.__underscored(self.doc.documentElement.tagName): self.__parse_node(self.doc.documentElement)}

    def __parse_node(self, root):
        child = root.firstChild
        if self.__get_node_attribute(root, "type") == "array":
            return self.__build_list(child)
        elif not child:
            return self.__node_content(root, None)
        elif (child.nodeType == minidom.Node.TEXT_NODE):
            return self.__node_content(root, child.nodeValue)
        else:
            return self.__build_dict(child)

    def __convert_to_boolean(self, value):
        if value == "true" or value == "1":
            return True
        else:
            return False

    def __convert_to_date(self, value):
        return datetime.strptime(value, "%Y-%m-%d").date()

    def __convert_to_datetime(self, value):
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")

    def __convert_to_list(self, dict, key):
        val = dict[key]
        if not isinstance(val, list):
            dict[key] = [val]

    def __build_list(self, child):
        l = []
        while child is not None:
            if (child.nodeType == minidom.Node.ELEMENT_NODE):
                l.append(self.__parse_node(child))
            child = child.nextSibling
        return l

    def __build_dict(self, child):
        d = {}
        while child is not None:
            if (child.nodeType == minidom.Node.ELEMENT_NODE):
                child_tag = self.__underscored(child.tagName)
                if self.__get_node_attribute(child, "type") == "array" or child.firstChild and child.firstChild.nodeType == minidom.Node.TEXT_NODE:
                    d[child_tag] = self.__parse_node(child)
                else:
                    if not d.get(child_tag):
                        d[child_tag] = self.__parse_node(child)
                    else:
                        self.__convert_to_list(d, child_tag)
                        d[child_tag].append(self.__parse_node(child))

            child = child.nextSibling
        return d

    def __get_node_attribute(self, node, attribute):
        attribute_node = node.attributes.get(attribute)
        return attribute_node and attribute_node.value

    def __node_content(self, parent, content):
        parent_type = self.__get_node_attribute(parent, "type")
        parent_nil = self.__get_node_attribute(parent, "nil")

        if parent_type == "integer":
            return int(content)
        elif parent_type == "boolean":
            return self.__convert_to_boolean(content)
        elif parent_type == "datetime":
            return self.__convert_to_datetime(content)
        elif parent_type == "date":
            return self.__convert_to_date(content)
        elif parent_nil == "true":
            return None
        else:
            return content or ""

    def __underscored(self, string):
        return string.replace("-","_")

########NEW FILE########
__FILENAME__ = xml_util
from braintree.util.parser import Parser
from braintree.util.generator import Generator

class XmlUtil(object):
    @staticmethod
    def xml_from_dict(dict):
        return Generator(dict).generate()

    @staticmethod
    def dict_from_xml(xml):
        return Parser(xml).parse()

########NEW FILE########
__FILENAME__ = validation_error
from braintree.attribute_getter import AttributeGetter

class ValidationError(AttributeGetter):
    """
    A validation error returned from the server, with information about the error:

    * **attribute**: The field which had an error.
    * **code**: A numeric error code. See :class:`ErrorCodes <braintree.error_codes.ErrorCodes>`
    * **message**: A description of the error.  Note: error messages may change, but the code will not.
    """
    pass

########NEW FILE########
__FILENAME__ = validation_error_collection
from braintree.validation_error import ValidationError

class ValidationErrorCollection(object):
    """
    A class representing a collection of validation errors.

    For more information on ValidationErrors, see https://www.braintreepayments.com/docs/python/general/validation_errors

    """

    def __init__(self, data={"errors": []}):
        self.data = data

    @property
    def deep_errors(self):
        """
        Return all :class:`ValidationErrors <braintree.validation_error.ValidationError>`, including nested errors.
        """

        result = []
        result.extend(self.errors)
        for nested_error in self.__nested_errors.values():
            result.extend(nested_error.deep_errors)
        return result

    def for_index(self, index):
        return self.for_object("index_%s" % index)

    def for_object(self, nested_key):
        """
        Returns a :class:`ValidationErrorCollection <braintree.validation_error_collection.ValidationErrorCollection>`

        It represents the errors at the nested level:::

            error_result = Transaction.sale({"credit_card": {"number": "invalid"}})
            print error_result.errors.for_object("transaction").for_object("credit_card").on("number")[0].code

        """

        return self.__get_nested_errrors(nested_key)

    def on(self, attribute):
        """
        Returns the list of errors

        Restricted to a given attribute::

            error_result = Transaction.sale({"credit_card": {"number": "invalid"}})
            print [ error.code for error in error_result.errors.for_object("transaction").for_object("credit_card").on("number") ]

        """
        return [error for error in self.errors if error.attribute == attribute]

    @property
    def deep_size(self):
        """Returns the number of errors on this object and any nested objects."""

        size = len(self.errors)
        for error in self.__nested_errors.values():
            size += error.deep_size
        return size

    @property
    def errors(self):
        """Returns a list of :class:`ValidationError <braintree.validation_error.ValidationError>` objects."""

        return [ValidationError(error) for error in self.data["errors"]]

    @property
    def size(self):
        """Returns the number of errors on this object, without counting nested errors."""
        return len(self.errors)

    def __get_nested_errrors(self, nested_key):
        if nested_key in self.__nested_errors:
            return self.__nested_errors[nested_key]
        else:
            return ValidationErrorCollection()

    def __getitem__(self, index):
        return self.errors[index]

    def __len__(self):
        return self.size

    @property
    def __nested_errors(self):
        nested_errors = {}
        for key in self.data.keys():
            if key == "errors": continue
            nested_errors[key] = ValidationErrorCollection(self.data[key])
        return nested_errors


########NEW FILE########
__FILENAME__ = version
Version = "2.29.1"

########NEW FILE########
__FILENAME__ = webhook_notification
from braintree.resource import Resource
from braintree.configuration import Configuration
from braintree.subscription import Subscription
from braintree.merchant_account import MerchantAccount
from braintree.transaction import Transaction
from braintree.partner_merchant import PartnerMerchant
from braintree.disbursement import Disbursement
from braintree.error_result import ErrorResult
from braintree.validation_error_collection import ValidationErrorCollection

class WebhookNotification(Resource):
    class Kind(object):
        PartnerMerchantConnected = "partner_merchant_connected"
        PartnerMerchantDisconnected = "partner_merchant_disconnected"
        PartnerMerchantDeclined = "partner_merchant_declined"
        SubscriptionCanceled = "subscription_canceled"
        SubscriptionChargedSuccessfully = "subscription_charged_successfully"
        SubscriptionChargedUnsuccessfully = "subscription_charged_unsuccessfully"
        SubscriptionExpired = "subscription_expired"
        SubscriptionTrialEnded = "subscription_trial_ended"
        SubscriptionWentActive = "subscription_went_active"
        SubscriptionWentPastDue = "subscription_went_past_due"
        SubMerchantAccountApproved = "sub_merchant_account_approved"
        SubMerchantAccountDeclined = "sub_merchant_account_declined"
        TransactionDisbursed = "transaction_disbursed"
        DisbursementException = "disbursement_exception"
        Disbursement = "disbursement"

    @staticmethod
    def parse(signature, payload):
        return Configuration.gateway().webhook_notification.parse(signature, payload)

    @staticmethod
    def verify(challenge):
        return Configuration.gateway().webhook_notification.verify(challenge)

    def __init__(self, gateway, attributes):
        Resource.__init__(self, gateway, attributes)

        if "api_error_response" in attributes["subject"]:
            node_wrapper = attributes["subject"]["api_error_response"]
        else:
            node_wrapper = attributes["subject"]

        if "subscription" in node_wrapper:
            self.subscription = Subscription(gateway, node_wrapper['subscription'])
        elif "merchant_account" in node_wrapper:
            self.merchant_account = MerchantAccount(gateway, node_wrapper['merchant_account'])
        elif "transaction" in node_wrapper:
            self.transaction = Transaction(gateway, node_wrapper['transaction'])
        elif "partner_merchant" in node_wrapper:
            self.partner_merchant = PartnerMerchant(gateway, node_wrapper['partner_merchant'])
        elif "disbursement" in node_wrapper:
            self.disbursement = Disbursement(gateway, node_wrapper['disbursement'])

        if "errors" in node_wrapper:
            self.errors = ValidationErrorCollection(node_wrapper['errors'])
            self.message = node_wrapper['message']

########NEW FILE########
__FILENAME__ = webhook_notification_gateway
import re
import base64
from braintree.exceptions.invalid_signature_error import InvalidSignatureError
from braintree.util.crypto import Crypto
from braintree.util.xml_util import XmlUtil
from braintree.webhook_notification import WebhookNotification

class WebhookNotificationGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def parse(self, signature, payload):
        if re.search("[^A-Za-z0-9+=/\n]", payload):
            raise InvalidSignatureError("payload contains illegal characters")
        self.__validate_signature(signature, payload)
        attributes = XmlUtil.dict_from_xml(base64.decodestring(payload))
        return WebhookNotification(self.gateway, attributes['notification'])

    def verify(self, challenge):
        digest = Crypto.sha1_hmac_hash(self.config.private_key, challenge)
        return "%s|%s" % (self.config.public_key, digest)

    def __matching_signature(self, signature_pairs):
        for public_key, signature in signature_pairs:
            if public_key == self.config.public_key:
                return signature
        return None

    def __validate_signature(self, signature_string, payload):
        signature_pairs = [pair.split("|") for pair in signature_string.split("&") if "|" in pair]
        signature = self.__matching_signature(signature_pairs)
        if not signature:
            raise InvalidSignatureError("no matching public key")
        if not any(self.__payload_matches(signature, p) for p in [payload, payload + "\n"]):
            raise InvalidSignatureError("signature does not match payload - one has been modified")

    def __payload_matches(self, signature, payload):
        payload_signature = Crypto.sha1_hmac_hash(self.config.private_key, payload)
        return Crypto.secure_compare(payload_signature, signature)

########NEW FILE########
__FILENAME__ = webhook_testing
import braintree
from braintree.configuration import Configuration

class WebhookTesting(object):
    @staticmethod
    def sample_notification(kind, id):
        return Configuration.gateway().webhook_testing.sample_notification(kind, id)

########NEW FILE########
__FILENAME__ = webhook_testing_gateway
from braintree.util.crypto import Crypto
from braintree.webhook_notification import WebhookNotification
import base64
from datetime import datetime

class WebhookTestingGateway(object):
    def __init__(self, gateway):
        self.gateway = gateway
        self.config = gateway.config

    def sample_notification(self, kind, id):
        payload = base64.encodestring(self.__sample_xml(kind, id))
        hmac_payload = Crypto.sha1_hmac_hash(self.gateway.config.private_key, payload)
        signature = "%s|%s" % (self.gateway.config.public_key, hmac_payload)
        return signature, payload

    def __sample_xml(self, kind, id):
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return """
            <notification>
                <timestamp type="datetime">%s</timestamp>
                <kind>%s</kind>
                <subject>%s</subject>
            </notification>
        """ % (timestamp, kind, self.__subject_sample_xml(kind, id))

    def __subject_sample_xml(self, kind, id):
        if kind == WebhookNotification.Kind.SubMerchantAccountApproved:
            return self.__merchant_account_approved_sample_xml(id)
        elif kind == WebhookNotification.Kind.SubMerchantAccountDeclined:
            return self.__merchant_account_declined_sample_xml(id)
        elif kind == WebhookNotification.Kind.TransactionDisbursed:
            return self.__transaction_disbursed_sample_xml(id)
        elif kind == WebhookNotification.Kind.PartnerMerchantConnected:
            return self.__partner_merchant_connected_sample_xml()
        elif kind == WebhookNotification.Kind.PartnerMerchantDisconnected:
            return self.__partner_merchant_disconnected_sample_xml()
        elif kind == WebhookNotification.Kind.PartnerMerchantDeclined:
            return self.__partner_merchant_declined_sample_xml()
        elif kind == WebhookNotification.Kind.DisbursementException:
            return self.__disbursement_exception_sample_xml(id)
        elif kind == WebhookNotification.Kind.Disbursement:
            return self.__disbursement_sample_xml(id)
        else:
            return self.__subscription_sample_xml(id)

    def __transaction_disbursed_sample_xml(self, id):
        return """
            <transaction>
              <id>%s</id>
              <amount>100</amount>
              <tax-amount>10</tax-amount>
              <disbursement-details>
                <settlement-amount>100</settlement-amount>
                <settlement-currency-exchange-rate>10</settlement-currency-exchange-rate>
                <disbursement-date type="datetime">2013-07-09T18:23:29Z</disbursement-date>
              </disbursement-details>
            </transaction>
        """ % id

    def __disbursement_exception_sample_xml(self, id):
        return """
            <disbursement>
              <id>%s</id>
              <transaction-ids type="array">
                <item>afv56j</item>
                <item>kj8hjk</item>
              </transaction-ids>
              <success type="boolean">false</success>
              <retry type="boolean">false</retry>
              <merchant-account>
                <id>merchant_account_token</id>
                <currency-iso-code>USD</currency-iso-code>
                <sub-merchant-account type="boolean">false</sub-merchant-account>
                <status>active</status>
              </merchant-account>
              <amount>100.00</amount>
              <disbursement-date type="date">2014-02-09</disbursement-date>
              <exception-message>bank_rejected</exception-message>
              <follow-up-action>update_funding_information</follow-up-action>
            </disbursement>
        """ % id

    def __disbursement_sample_xml(self, id):
        return """
            <disbursement>
              <id>%s</id>
              <transaction-ids type="array">
                <item>afv56j</item>
                <item>kj8hjk</item>
              </transaction-ids>
              <success type="boolean">true</success>
              <retry type="boolean">false</retry>
              <merchant-account>
                <id>merchant_account_token</id>
                <currency-iso-code>USD</currency-iso-code>
                <sub-merchant-account type="boolean">false</sub-merchant-account>
                <status>active</status>
              </merchant-account>
              <amount>100.00</amount>
              <disbursement-date type="date">2014-02-09</disbursement-date>
              <exception-message nil="true"/>
              <follow-up-action nil="true"/>
            </disbursement>
        """ % id

    def __subscription_sample_xml(self, id):
        return """
            <subscription>
                <id>%s</id>
                <transactions type="array"></transactions>
                <add_ons type="array"></add_ons>
                <discounts type="array"></discounts>
            </subscription>
        """ % id

    def __merchant_account_approved_sample_xml(self, id):
        return """
            <merchant-account>
                <id>%s</id>
                <status>active</status>
                <master-merchant-account>
                    <id>master_ma_for_%s</id>
                    <status>active</status>
                </master-merchant-account>
            </merchant-account>
        """ % (id, id)

    def __merchant_account_declined_sample_xml(self, id):
        return """
            <api-error-response>
                <message>Credit score is too low</message>
                <errors>
                    <errors type="array"/>
                        <merchant-account>
                            <errors type="array">
                                <error>
                                    <code>82621</code>
                                    <message>Credit score is too low</message>
                                    <attribute type="symbol">base</attribute>
                                </error>
                            </errors>
                        </merchant-account>
                    </errors>
                    <merchant-account>
                        <id>%s</id>
                        <status>suspended</status>
                        <master-merchant-account>
                            <id>master_ma_for_%s</id>
                            <status>suspended</status>
                        </master-merchant-account>
                    </merchant-account>
            </api-error-response>
            """ % (id, id)

    def __partner_merchant_connected_sample_xml(self):
        return """
            <partner-merchant>
                <partner-merchant-id>abc123</partner-merchant-id>
                <public-key>public_key</public-key>
                <private-key>private_key</private-key>
                <merchant-public-id>public_id</merchant-public-id>
                <client-side-encryption-key>cse_key</client-side-encryption-key>
            </partner-merchant>
            """

    def __partner_merchant_disconnected_sample_xml(self):
        return """
            <partner-merchant>
                <partner-merchant-id>abc123</partner-merchant-id>
            </partner-merchant>
            """

    def __partner_merchant_declined_sample_xml(self):
        return """
            <partner-merchant>
                <partner-merchant-id>abc123</partner-merchant-id>
            </partner-merchant>
            """

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Braintree documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 29 14:46:55 2010.
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
#sys.path.append(os.path.abspath('.'))
sys.path.insert(0, os.path.dirname(__file__) + '/../')
import braintree

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['_templates']
templates_path = []

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Braintree'
copyright = u'2012, Braintree'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = braintree.version.Version
# The full version, including alpha/beta/rc tags.
release = braintree.version.Version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Braintreedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Braintree.tex', u'Braintree Documentation',
   u'Braintree', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = test_address
from tests.test_helper import *

class TestAddress(unittest.TestCase):
    def test_create_returns_successful_result_if_valid(self):
        customer = Customer.create().customer
        result = Address.create({
            "customer_id": customer.id,
            "first_name": "Ben",
            "last_name": "Moore",
            "company": "Moore Co.",
            "street_address": "1811 E Main St",
            "extended_address": "Suite 200",
            "locality": "Chicago",
            "region": "Illinois",
            "postal_code": "60622",
            "country_name": "United States of America",
            "country_code_alpha2": "US",
            "country_code_alpha3": "USA",
            "country_code_numeric": "840"
        })

        self.assertTrue(result.is_success)
        address = result.address
        self.assertEquals(customer.id, address.customer_id)
        self.assertEquals("Ben", address.first_name)
        self.assertEquals("Moore", address.last_name)
        self.assertEquals("Moore Co.", address.company)
        self.assertEquals("1811 E Main St", address.street_address)
        self.assertEquals("Suite 200", address.extended_address)
        self.assertEquals("Chicago", address.locality)
        self.assertEquals("Illinois", address.region)
        self.assertEquals("60622", address.postal_code)
        self.assertEquals("US", address.country_code_alpha2)
        self.assertEquals("USA", address.country_code_alpha3)
        self.assertEquals("840", address.country_code_numeric)
        self.assertEquals("United States of America", address.country_name)

    def test_error_response_if_invalid(self):
        customer = Customer.create().customer
        result = Address.create({
            "customer_id": customer.id,
            "country_name": "zzzzzz",
            "country_code_alpha2": "zz",
            "country_code_alpha3": "zzz",
            "country_code_numeric": "000"
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.Address.CountryNameIsNotAccepted, result.errors.for_object("address").on("country_name")[0].code)
        self.assertEquals(ErrorCodes.Address.CountryCodeAlpha2IsNotAccepted, result.errors.for_object("address").on("country_code_alpha2")[0].code)
        self.assertEquals(ErrorCodes.Address.CountryCodeAlpha3IsNotAccepted, result.errors.for_object("address").on("country_code_alpha3")[0].code)
        self.assertEquals(ErrorCodes.Address.CountryCodeNumericIsNotAccepted, result.errors.for_object("address").on("country_code_numeric")[0].code)

    def test_error_response_if_inconsistent_country(self):
        customer = Customer.create().customer
        result = Address.create({
            "customer_id": customer.id,
            "country_code_alpha2": "US",
            "country_code_alpha3": "MEX"
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.Address.InconsistentCountry, result.errors.for_object("address").on("base")[0].code)

    def test_delete_with_valid_customer_id_and_address_id(self):
        customer = Customer.create().customer
        address = Address.create({"customer_id": customer.id, "street_address": "123 Main St."}).address
        result = Address.delete(customer.id, address.id)

        self.assertTrue(result.is_success)

    @raises(NotFoundError)
    def test_delete_with_valid_customer_id_and_non_existing_address(self):
        customer = Customer.create().customer
        result = Address.delete(customer.id, "notreal")

    def test_find_with_valid_customer_id_and_address_id(self):
        customer = Customer.create().customer
        address = Address.create({"customer_id": customer.id, "street_address": "123 Main St."}).address
        found_address = Address.find(customer.id, address.id)

        self.assertEquals(address.street_address, found_address.street_address)

    def test_find_with_invalid_customer_id_and_address_id(self):
        try:
            Address.find("notreal", "badaddress")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertEquals("address for customer notreal with id badaddress not found", str(e))

    def test_update_with_valid_values(self):
        customer = Customer.create().customer
        address = Address.create({
            "customer_id": customer.id,
            "street_address": "1811 E Main St",
            "extended_address": "Suite 200",
            "locality": "Chicago",
            "region": "Illinois",
            "postal_code": "60622",
            "country_name": "United States of America"
        }).address

        result = Address.update(customer.id, address.id, {
            "street_address": "123 E New St",
            "extended_address": "New Suite 3",
            "locality": "Chicago",
            "region": "Illinois",
            "postal_code": "60621",
            "country_code_alpha2": "MX",
            "country_code_alpha3": "MEX",
            "country_code_numeric": "484",
            "country_name": "Mexico"
        })

        self.assertTrue(result.is_success)
        address = result.address
        self.assertEquals(customer.id, address.customer_id)
        self.assertEquals("123 E New St", address.street_address)
        self.assertEquals("New Suite 3", address.extended_address)
        self.assertEquals("Chicago", address.locality)
        self.assertEquals("Illinois", address.region)
        self.assertEquals("60621", address.postal_code)
        self.assertEquals("MX", address.country_code_alpha2)
        self.assertEquals("MEX", address.country_code_alpha3)
        self.assertEquals("484", address.country_code_numeric)
        self.assertEquals("Mexico", address.country_name)

    def test_update_with_invalid_values(self):
        customer = Customer.create().customer
        address = Address.create({
            "customer_id": customer.id,
            "street_address": "1811 E Main St",
            "extended_address": "Suite 200",
            "locality": "Chicago",
            "region": "Illinois",
            "postal_code": "60622",
            "country_name": "United States of America"
        }).address

        result = Address.update(customer.id, address.id, {
            "street_address": "123 E New St",
            "country_name": "United States of Invalid"
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.Address.CountryNameIsNotAccepted, result.errors.for_object("address").on("country_name")[0].code)

    @raises(NotFoundError)
    def test_update_raises_not_found_error_if_given_bad_address(self):
        customer = Customer.create().customer
        Address.update(customer.id, "notfound", {"street_address": "123 Main St."})


########NEW FILE########
__FILENAME__ = test_add_ons
from tests.test_helper import *

class TestAddOn(unittest.TestCase):
    def test_all_returns_all_add_ons(self):
        new_id = str(random.randint(1, 1000000))
        attributes = {
            "amount": "100.00",
            "description": "some description",
            "id": new_id,
            "kind": "add_on",
            "name": "python_add_on",
            "never_expires": False,
            "number_of_billing_cycles": 1
        }

        Configuration.instantiate().http().post("/modifications/create_modification_for_tests", {"modification": attributes})

        add_ons = AddOn.all()

        for add_on in add_ons:
            if add_on.id == new_id:
                break
        else:
            add_on = None

        self.assertNotEquals(None, add_on)

        self.assertEquals(add_on.amount, Decimal("100.00"))
        self.assertEquals(add_on.description, "some description")
        self.assertEquals(add_on.id, new_id)
        self.assertEquals(add_on.kind, "add_on")
        self.assertEquals(add_on.name, "python_add_on")
        self.assertEquals(add_on.never_expires, False)
        self.assertEquals(add_on.number_of_billing_cycles, 1)

########NEW FILE########
__FILENAME__ = test_client_token
from tests.test_helper import *
import base64
import json
import urllib
import datetime
import braintree
from braintree.util import Http

class TestClientToken(unittest.TestCase):

    def test_is_authorized_with_authorization_fingerprint(self):
        config = Configuration.instantiate()
        client_token = ClientToken.generate()
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]

        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.get_cards()
        self.assertEqual(status_code, 200)

    def test_can_pass_verify_card(self):
        config = Configuration.instantiate()
        result = braintree.Customer.create()
        customer_id = result.customer.id

        client_token = ClientToken.generate({
            "customer_id": customer_id,
            "options": {
                "verify_card": True
            }
        })
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4000111111111115",
                "expiration_month": "11",
                "expiration_year": "2099",
            }
        })
        self.assertEqual(status_code, 422)

    def test_can_pass_make_default(self):
        config = Configuration.instantiate()
        result = braintree.Customer.create()
        customer_id = result.customer.id

        client_token = ClientToken.generate({
            "customer_id": customer_id,
            "options": {
                "make_default": True
            }
        })
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            }
        })
        self.assertEqual(status_code, 201)

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4005519200000004",
                "expiration_month": "11",
                "expiration_year": "2099",
            }
        })
        self.assertEqual(status_code, 201)

        customer = braintree.Customer.find(customer_id)
        self.assertEqual(len(customer.credit_cards), 2)
        for credit_card in customer.credit_cards:
            if credit_card.bin == "400551":
                self.assertTrue(credit_card.default)

    def test_can_pass_fail_on_duplicate_payment_method(self):
        config = Configuration.instantiate()
        result = braintree.Customer.create()
        customer_id = result.customer.id

        client_token = ClientToken.generate({
            "customer_id": customer_id,
        })
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            }
        })
        self.assertEqual(status_code, 201)

        client_token = ClientToken.generate({
            "customer_id": customer_id,
            "options": {
                "fail_on_duplicate_payment_method": True
            }
        })
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http.set_authorization_fingerprint(authorization_fingerprint)
        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            }
        })
        self.assertEqual(status_code, 422)

        customer = braintree.Customer.find(customer_id)
        self.assertEqual(len(customer.credit_cards), 1)

    def test_required_data_cannot_be_overridden(self):
        try:
            client_token = ClientToken.generate({
                "merchant_id": "1234"
            })
            self.fail("Should have raised exception!")
        except Exception, e:
            self.assertEqual("'Invalid keys: merchant_id'", str(e))

########NEW FILE########
__FILENAME__ = test_credit_card
from tests.test_helper import *
from braintree.test.credit_card_defaults import CreditCardDefaults
from braintree.test.credit_card_numbers import CreditCardNumbers
import braintree.test.venmo_sdk as venmo_sdk

class TestCreditCard(unittest.TestCase):
    def test_create_adds_credit_card_to_existing_customer(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        })

        self.assertTrue(result.is_success)
        credit_card = result.credit_card
        self.assertTrue(re.search("\A\w{4,5}\Z", credit_card.token) != None)
        self.assertEquals("411111", credit_card.bin)
        self.assertEquals("1111", credit_card.last_4)
        self.assertEquals("05", credit_card.expiration_month)
        self.assertEquals("2009", credit_card.expiration_year)
        self.assertEquals("05/2009", credit_card.expiration_date)
        self.assertEquals("John Doe", credit_card.cardholder_name)
        self.assertNotEquals(re.search("\A\w{32}\Z", credit_card.unique_number_identifier), None)
        self.assertFalse(credit_card.venmo_sdk)
        self.assertNotEquals(re.search("png", credit_card.image_url), None)

    def test_create_and_make_default(self):
        customer = Customer.create().customer
        card1 = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        }).credit_card

        self.assertTrue(card1.default)

        card2 = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe",
            "options":
                {"make_default": True}
        }).credit_card

        card1 = CreditCard.find(card1.token)
        self.assertFalse(card1.default)
        self.assertTrue(card2.default)

    def test_create_with_expiration_month_and_year(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_month": "05",
            "expiration_year": "2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        })

        self.assertTrue(result.is_success)
        credit_card = result.credit_card
        self.assertEquals("05/2009", credit_card.expiration_date)

    def test_create_with_security_params(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_month": "05",
            "expiration_year": "2009",
            "cvv": "100",
            "cardholder_name": "John Doe",
            "device_session_id": "abc123",
            "fraud_merchant_id": "456"
        })

        self.assertTrue(result.is_success)

    def test_create_can_specify_the_desired_token(self):
        token = str(random.randint(1, 1000000))
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "token": token
        })

        self.assertTrue(result.is_success)
        credit_card = result.credit_card
        self.assertEquals(token, credit_card.token)

    def test_create_with_billing_address(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "billing_address": {
                "street_address": "123 Abc Way",
                "locality": "Chicago",
                "region": "Illinois",
                "postal_code": "60622",
                "country_code_alpha2": "MX",
                "country_code_alpha3": "MEX",
                "country_code_numeric": "484",
                "country_name": "Mexico"
            }
        })

        self.assertTrue(result.is_success)
        address = result.credit_card.billing_address
        self.assertEquals("123 Abc Way", address.street_address)
        self.assertEquals("Chicago", address.locality)
        self.assertEquals("Illinois", address.region)
        self.assertEquals("60622", address.postal_code)
        self.assertEquals("MX", address.country_code_alpha2)
        self.assertEquals("MEX", address.country_code_alpha3)
        self.assertEquals("484", address.country_code_numeric)
        self.assertEquals("Mexico", address.country_name)

    def test_create_with_billing_address_id(self):
        customer = Customer.create().customer
        address = Address.create({
            "customer_id": customer.id,
            "street_address": "123 Abc Way"
        }).address

        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "billing_address_id": address.id
        })

        self.assertTrue(result.is_success)
        billing_address = result.credit_card.billing_address
        self.assertEquals(address.id, billing_address.id)
        self.assertEquals("123 Abc Way", billing_address.street_address)

    def test_create_without_billing_address_still_has_billing_address_method(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
        })
        self.assertTrue(result.is_success)
        self.assertEquals(None, result.credit_card.billing_address)

    def test_create_with_card_verification(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4000111111111115",
            "expiration_date": "05/2009",
            "options": {"verify_card": True}
        })

        self.assertFalse(result.is_success)
        verification = result.credit_card_verification
        self.assertEquals(CreditCardVerification.Status.ProcessorDeclined, verification.status)
        self.assertEquals("2000", verification.processor_response_code)
        self.assertEquals("Do Not Honor", verification.processor_response_text)
        self.assertEquals("I", verification.cvv_response_code)
        self.assertEquals(None, verification.avs_error_response_code)
        self.assertEquals("I", verification.avs_postal_code_response_code)
        self.assertEquals("I", verification.avs_street_address_response_code)
        self.assertEquals(TestHelper.default_merchant_account_id, verification.merchant_account_id)

    def test_create_with_card_verification_and_non_default_merchant_account(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4000111111111115",
            "expiration_date": "05/2009",
            "options": {
                "verification_merchant_account_id": TestHelper.non_default_merchant_account_id,
                "verify_card": True
            }
        })

        self.assertFalse(result.is_success)
        verification = result.credit_card_verification
        self.assertEquals(CreditCardVerification.Status.ProcessorDeclined, verification.status)
        self.assertEquals(None, verification.gateway_rejection_reason)
        self.assertEquals(TestHelper.non_default_merchant_account_id, verification.merchant_account_id)

    def test_verify_gateway_rejected_responds_to_processor_response_code(self):
        old_merchant_id = Configuration.merchant_id
        old_public_key = Configuration.public_key
        old_private_key = Configuration.private_key

        try:
            Configuration.merchant_id = "processing_rules_merchant_id"
            Configuration.public_key = "processing_rules_public_key"
            Configuration.private_key = "processing_rules_private_key"

            customer = Customer.create().customer
            result = CreditCard.create({
                "customer_id": customer.id,
                "number": "4111111111111111",
                "expiration_date": "05/2009",
                "billing_address": {
                    "postal_code": "20000"
                },
                "options": {
                    "verify_card": True
                }
            })


            self.assertFalse(result.is_success)
            self.assertEquals('1000', result.credit_card_verification.processor_response_code)
            self.assertEquals('Approved', result.credit_card_verification.processor_response_text)
        finally:
            Configuration.merchant_id = old_merchant_id
            Configuration.public_key = old_public_key
            Configuration.private_key = old_private_key

    def test_expose_gateway_rejection_reason_on_verification(self):
        old_merchant_id = Configuration.merchant_id
        old_public_key = Configuration.public_key
        old_private_key = Configuration.private_key

        try:
            Configuration.merchant_id = "processing_rules_merchant_id"
            Configuration.public_key = "processing_rules_public_key"
            Configuration.private_key = "processing_rules_private_key"

            customer = Customer.create().customer
            result = CreditCard.create({
                "customer_id": customer.id,
                "number": "4111111111111111",
                "expiration_date": "05/2009",
                "cvv": "200",
                "options": {
                    "verify_card": True
                }
            })

            self.assertFalse(result.is_success)
            verification = result.credit_card_verification
            self.assertEquals(Transaction.GatewayRejectionReason.Cvv, verification.gateway_rejection_reason)
        finally:
            Configuration.merchant_id = old_merchant_id
            Configuration.public_key = old_public_key
            Configuration.private_key = old_private_key

    def test_create_with_card_verification_set_to_false(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4000111111111115",
            "expiration_date": "05/2009",
            "options": {"verify_card": False}
        })

        self.assertTrue(result.is_success)

    def test_create_with_fail_on_duplicate_payment_method_set_to_true(self):
        customer = Customer.create().customer
        CreditCard.create({
            "customer_id": customer.id,
            "number": "4000111111111115",
            "expiration_date": "05/2009"
        })

        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4000111111111115",
            "expiration_date": "05/2009",
            "options": {"fail_on_duplicate_payment_method": True}
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.CreditCard.DuplicateCardExists, result.errors.for_object("credit_card").on("number")[0].code)
        self.assertEquals("Duplicate card exists in the vault.", result.message)

    def test_create_with_invalid_invalid_options(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "invalid_date",
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.CreditCard.ExpirationDateIsInvalid, result.errors.for_object("credit_card").on("expiration_date")[0].code)
        self.assertEquals("Expiration date is invalid.", result.message)

    def test_create_with_invalid_country_codes(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2012",
            "billing_address": {
                "country_code_alpha2": "ZZ",
                "country_code_alpha3": "ZZZ",
                "country_code_numeric": "000",
                "country_name": "zzzzzzz"
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Address.CountryCodeAlpha2IsNotAccepted,
            result.errors.for_object("credit_card").for_object("billing_address").on("country_code_alpha2")[0].code
        )
        self.assertEquals(
            ErrorCodes.Address.CountryCodeAlpha3IsNotAccepted,
            result.errors.for_object("credit_card").for_object("billing_address").on("country_code_alpha3")[0].code
        )
        self.assertEquals(
            ErrorCodes.Address.CountryCodeNumericIsNotAccepted,
            result.errors.for_object("credit_card").for_object("billing_address").on("country_code_numeric")[0].code
        )
        self.assertEquals(
            ErrorCodes.Address.CountryNameIsNotAccepted,
            result.errors.for_object("credit_card").for_object("billing_address").on("country_name")[0].code
        )

    def test_create_with_venmo_sdk_payment_method_code(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "venmo_sdk_payment_method_code": venmo_sdk.VisaPaymentMethodCode
        })

        self.assertTrue(result.is_success)
        self.assertEquals("411111", result.credit_card.bin)
        self.assertTrue(result.credit_card.venmo_sdk)

    def test_create_with_invalid_venmo_sdk_payment_method_code(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "venmo_sdk_payment_method_code": venmo_sdk.InvalidPaymentMethodCode
        })

        self.assertFalse(result.is_success)
        self.assertEquals(result.message, "Invalid VenmoSDK payment method code")
        self.assertEquals(result.errors.for_object("credit_card") \
                .on("venmo_sdk_payment_method_code")[0].code, ErrorCodes.CreditCard.InvalidVenmoSDKPaymentMethodCode)

    def test_create_with_payment_method_nonce(self):
        config = Configuration.instantiate()
        authorization_fingerprint = json.loads(ClientToken.generate())["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })
        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            },
            "share": True
        })
        nonce = json.loads(response)["nonce"]
        customer = Customer.create().customer

        result = CreditCard.create({
            "customer_id": customer.id,
            "payment_method_nonce": nonce
        })

        self.assertTrue(result.is_success)
        self.assertEquals("411111", result.credit_card.bin)

    def test_create_with_venmo_sdk_session(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe",
            "options": {
                "venmo_sdk_session": venmo_sdk.Session
            }
        })
        self.assertTrue(result.is_success)
        self.assertTrue(result.credit_card.venmo_sdk)

    def test_create_with_invalid_venmo_sdk_session(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe",
            "options": {
                "venmo_sdk_session": venmo_sdk.InvalidSession
            }
        })
        self.assertTrue(result.is_success)
        self.assertFalse(result.credit_card.venmo_sdk)

    def test_update_with_valid_options(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        }).credit_card

        result = CreditCard.update(credit_card.token, {
            "number": "5105105105105100",
            "expiration_date": "06/2010",
            "cvv": "123",
            "cardholder_name": "Jane Jones"
        })

        self.assertTrue(result.is_success)
        credit_card = result.credit_card
        self.assertTrue(re.search("\A\w{4,5}\Z", credit_card.token) != None)
        self.assertEquals("510510", credit_card.bin)
        self.assertEquals("5100", credit_card.last_4)
        self.assertEquals("06", credit_card.expiration_month)
        self.assertEquals("2010", credit_card.expiration_year)
        self.assertEquals("06/2010", credit_card.expiration_date)
        self.assertEquals("Jane Jones", credit_card.cardholder_name)

    def test_update_billing_address_creates_new_by_default(self):
        customer = Customer.create().customer
        initial_credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "billing_address": {
                "street_address": "123 Nigeria Ave",
            }
        }).credit_card

        updated_credit_card = CreditCard.update(initial_credit_card.token, {
            "billing_address": {
                "region": "IL",
                "country_code_alpha2": "NG",
                "country_code_alpha3": "NGA",
                "country_code_numeric": "566",
                "country_name": "Nigeria"
            }
        }).credit_card

        self.assertEquals("IL", updated_credit_card.billing_address.region)
        self.assertEquals("NG", updated_credit_card.billing_address.country_code_alpha2)
        self.assertEquals("NGA", updated_credit_card.billing_address.country_code_alpha3)
        self.assertEquals("566", updated_credit_card.billing_address.country_code_numeric)
        self.assertEquals("Nigeria", updated_credit_card.billing_address.country_name)
        self.assertEquals(None, updated_credit_card.billing_address.street_address)
        self.assertNotEquals(initial_credit_card.billing_address.id, updated_credit_card.billing_address.id)

    def test_update_billing_address_when_update_existing_is_True(self):
        customer = Customer.create().customer
        initial_credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "billing_address": {
                "street_address": "123 Nigeria Ave",
            }
        }).credit_card

        updated_credit_card = CreditCard.update(initial_credit_card.token, {
            "billing_address": {
                "region": "IL",
                "options": {
                    "update_existing": True
                }
            }
        }).credit_card

        self.assertEquals("IL", updated_credit_card.billing_address.region)
        self.assertEquals("123 Nigeria Ave", updated_credit_card.billing_address.street_address)
        self.assertEquals(initial_credit_card.billing_address.id, updated_credit_card.billing_address.id)

    def test_update_and_make_default(self):
        customer = Customer.create().customer
        card1 = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        }).credit_card
        card2 = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        }).credit_card

        self.assertTrue(card1.default)
        self.assertFalse(card2.default)

        result = CreditCard.update(card2.token, {
            "options": {
                "make_default": True
            }
        })
        self.assertFalse(CreditCard.find(card1.token).default)
        self.assertTrue(CreditCard.find(card2.token).default)


    def test_update_verifies_card_if_option_is_provided(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        }).credit_card

        result = CreditCard.update(credit_card.token, {
            "number": "4000111111111115",
            "expiration_date": "06/2010",
            "cvv": "123",
            "cardholder_name": "Jane Jones",
            "options": {"verify_card": True}
        })

        self.assertFalse(result.is_success)
        self.assertEquals(CreditCardVerification.Status.ProcessorDeclined, result.credit_card_verification.status)

    def test_update_verifies_card_with_non_default_merchant_account(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        }).credit_card

        result = CreditCard.update(credit_card.token, {
            "number": "4000111111111115",
            "expiration_date": "06/2010",
            "cvv": "123",
            "cardholder_name": "Jane Jones",
            "options": {
                "verification_merchant_account_id": TestHelper.non_default_merchant_account_id,
                "verify_card": True
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(CreditCardVerification.Status.ProcessorDeclined, result.credit_card_verification.status)

    def test_update_billing_address(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "billing_address": {
                "street_address": "321 Xyz Way",
                "locality": "Chicago",
                "region": "Illinois",
                "postal_code": "60621"
            }
        }).credit_card

        result = CreditCard.update(credit_card.token, {
            "billing_address": {
                "street_address": "123 Abc Way",
                "locality": "Chicago",
                "region": "Illinois",
                "postal_code": "60622"
            }
        })

        self.assertTrue(result.is_success)
        address = result.credit_card.billing_address
        self.assertEquals("123 Abc Way", address.street_address)
        self.assertEquals("Chicago", address.locality)
        self.assertEquals("Illinois", address.region)
        self.assertEquals("60622", address.postal_code)

    def test_update_returns_error_if_invalid(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009"
        }).credit_card

        result = CreditCard.update(credit_card.token, {
            "expiration_date": "invalid_date"
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.CreditCard.ExpirationDateIsInvalid, result.errors.for_object("credit_card").on("expiration_date")[0].code)

    def test_delete_with_valid_token(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009"
        }).credit_card

        result = CreditCard.delete(credit_card.token)
        self.assertTrue(result.is_success)

    @raises(NotFoundError)
    def test_delete_raises_error_when_deleting_twice(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009"
        }).credit_card

        CreditCard.delete(credit_card.token)
        CreditCard.delete(credit_card.token)

    @raises(NotFoundError)
    def test_delete_with_invalid_token(self):
        result = CreditCard.delete("notreal")

    def test_find_with_valid_token(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009"
        }).credit_card

        found_credit_card = CreditCard.find(credit_card.token)
        self.assertTrue(re.search("\A\w{4,5}\Z", credit_card.token) != None)
        self.assertEquals("411111", credit_card.bin)
        self.assertEquals("1111", credit_card.last_4)
        self.assertEquals("05", credit_card.expiration_month)
        self.assertEquals("2009", credit_card.expiration_year)
        self.assertEquals("05/2009", credit_card.expiration_date)

    def test_find_returns_associated_subsriptions(self):
        customer = Customer.create().customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009"
        }).credit_card
        id = "id_" + str(random.randint(1, 1000000))
        subscription = Subscription.create({
            "id": id,
            "plan_id": "integration_trialless_plan",
            "payment_method_token": credit_card.token,
            "price": Decimal("1.00")
        }).subscription

        found_credit_card = CreditCard.find(credit_card.token)
        self.assertEquals(id, found_credit_card.subscriptions[0].id)
        self.assertEquals(Decimal("1.00"), found_credit_card.subscriptions[0].price)
        self.assertEquals(credit_card.token, found_credit_card.subscriptions[0].payment_method_token)

    def test_find_with_invalid_token(self):
        try:
            CreditCard.find("bad_token")
            self.assertTrue(False)
        except Exception, e:
            self.assertEquals("payment method with token bad_token not found", str(e))

    def test_from_nonce_with_unlocked_nonce(self):
        config = Configuration.instantiate()
        customer = Customer.create().customer

        client_token = ClientToken.generate({
            "customer_id": customer.id,
        })
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            }
        })
        self.assertEqual(status_code, 201)
        nonce = json.loads(response)["nonce"]

        card = CreditCard.from_nonce(nonce)
        customer = Customer.find(customer.id)
        self.assertEquals(customer.credit_cards[0].token, card.token)

    def test_from_nonce_with_unlocked_nonce_pointing_to_shared_card(self):
        config = Configuration.instantiate()

        client_token = ClientToken.generate()
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            },
            "share": True
        })
        self.assertEqual(status_code, 201)
        nonce = json.loads(response)["nonce"]

        try:
            CreditCard.from_nonce(nonce)
            self.assertTrue(False)
        except Exception, e:
            self.assertIn("not found", str(e))

    def test_from_nonce_with_consumed_nonce(self):
        config = Configuration.instantiate()
        customer = Customer.create().customer

        client_token = ClientToken.generate({
            "customer_id": customer.id,
        })
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            }
        })
        self.assertEqual(status_code, 201)
        nonce = json.loads(response)["nonce"]

        CreditCard.from_nonce(nonce)
        try:
            CreditCard.from_nonce(nonce)
            self.assertTrue(False)
        except Exception, e:
            self.assertIn("consumed", str(e))

    def test_from_nonce_with_locked_nonce(self):
        config = Configuration.instantiate()

        client_token = ClientToken.generate()
        authorization_fingerprint = json.loads(client_token)["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })

        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            },
            "share": True
        })
        self.assertEqual(status_code, 201)

        status_code, response = http.get_cards()
        self.assertEqual(status_code, 200)
        nonce = json.loads(response)["creditCards"][0]["nonce"]

        try:
            CreditCard.from_nonce(nonce)
            self.assertTrue(False)
        except Exception, e:
            self.assertIn("locked", str(e))

    def test_create_from_transparent_redirect(self):
        customer = Customer.create().customer
        tr_data = {
            "credit_card": {
                "customer_id": customer.id
            }
        }
        post_params = {
            "tr_data": CreditCard.tr_data_for_create(tr_data, "http://example.com/path?foo=bar"),
            "credit_card[cardholder_name]": "Card Holder",
            "credit_card[number]": "4111111111111111",
            "credit_card[expiration_date]": "05/2012",
            "credit_card[billing_address][country_code_alpha2]": "MX",
            "credit_card[billing_address][country_code_alpha3]": "MEX",
            "credit_card[billing_address][country_code_numeric]": "484",
            "credit_card[billing_address][country_name]": "Mexico",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_create_url())
        result = CreditCard.confirm_transparent_redirect(query_string)
        self.assertTrue(result.is_success)
        credit_card = result.credit_card
        self.assertEquals("411111", credit_card.bin)
        self.assertEquals("1111", credit_card.last_4)
        self.assertEquals("05", credit_card.expiration_month)
        self.assertEquals("2012", credit_card.expiration_year)
        self.assertEquals(customer.id, credit_card.customer_id)
        self.assertEquals("MX", credit_card.billing_address.country_code_alpha2)
        self.assertEquals("MEX", credit_card.billing_address.country_code_alpha3)
        self.assertEquals("484", credit_card.billing_address.country_code_numeric)
        self.assertEquals("Mexico", credit_card.billing_address.country_name)


    def test_create_from_transparent_redirect_and_make_default(self):
        customer = Customer.create().customer
        card1 = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": "John Doe"
        }).credit_card
        self.assertTrue(card1.default)

        tr_data = {
            "credit_card": {
                "customer_id": customer.id,
                "options": {
                    "make_default": True
                }
            }
        }
        post_params = {
            "tr_data": CreditCard.tr_data_for_create(tr_data, "http://example.com/path?foo=bar"),
            "credit_card[cardholder_name]": "Card Holder",
            "credit_card[number]": "4111111111111111",
            "credit_card[expiration_date]": "05/2012",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_create_url())
        card2 = CreditCard.confirm_transparent_redirect(query_string).credit_card

        self.assertFalse(CreditCard.find(card1.token).default)
        self.assertTrue(card2.default)

    def test_create_from_transparent_redirect_with_error_result(self):
        customer = Customer.create().customer
        tr_data = {
            "credit_card": {
                "customer_id": customer.id
            }
        }

        post_params = {
            "tr_data": CreditCard.tr_data_for_create(tr_data, "http://example.com/path"),
            "credit_card[cardholder_name]": "Card Holder",
            "credit_card[number]": "eleventy",
            "credit_card[expiration_date]": "y2k"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_create_url())
        result = CreditCard.confirm_transparent_redirect(query_string)
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.CreditCard.NumberHasInvalidLength,
            result.errors.for_object("credit_card").on("number")[0].code
        )
        self.assertEquals(
            ErrorCodes.CreditCard.ExpirationDateIsInvalid,
            result.errors.for_object("credit_card").on("expiration_date")[0].code
        )

    def test_update_from_transparent_redirect_with_successful_result(self):
        old_token = str(random.randint(1, 1000000))
        new_token = str(random.randint(1, 1000000))
        credit_card = Customer.create({
            "credit_card": {
                "cardholder_name": "Old Cardholder Name",
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "token": old_token
            }
        }).customer.credit_cards[0]

        tr_data = {
            "payment_method_token": old_token,
            "credit_card": {
                "token": new_token
            }
        }

        post_params = {
            "tr_data": CreditCard.tr_data_for_update(tr_data, "http://example.com/path"),
            "credit_card[cardholder_name]": "New Cardholder Name",
            "credit_card[expiration_date]": "05/2014"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_update_url())
        result = CreditCard.confirm_transparent_redirect(query_string)
        self.assertTrue(result.is_success)
        credit_card = result.credit_card
        self.assertEquals(new_token, credit_card.token)
        self.assertEquals("411111", credit_card.bin)
        self.assertEquals("1111", credit_card.last_4)
        self.assertEquals("05", credit_card.expiration_month)
        self.assertEquals("2014", credit_card.expiration_year)

    def test_update_from_transparent_redirect_and_make_default(self):
        customer = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).customer
        card1 = customer.credit_cards[0]

        card2 = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
        }).credit_card

        self.assertTrue(card1.default)
        self.assertFalse(card2.default)

        tr_data = {
            "payment_method_token": card2.token,
            "credit_card": {
                "options": {
                    "make_default": True
                }
            }
        }

        post_params = {
            "tr_data": CreditCard.tr_data_for_update(tr_data, "http://example.com/path"),
            "credit_card[cardholder_name]": "New Cardholder Name",
            "credit_card[expiration_date]": "05/2014"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_update_url())
        result = CreditCard.confirm_transparent_redirect(query_string)

        self.assertFalse(CreditCard.find(card1.token).default)
        self.assertTrue(CreditCard.find(card2.token).default)

    def test_update_from_transparent_redirect_and_update_existing_billing_address(self):
        customer = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "billing_address": {
                    "street_address": "123 Old St",
                    "locality": "Chicago",
                    "region": "Illinois",
                    "postal_code": "60621"
                }
            }
        }).customer
        card = customer.credit_cards[0]

        tr_data = {
            "payment_method_token": card.token,
            "credit_card": {
                "billing_address": {
                    "street_address": "123 New St",
                    "locality": "Columbus",
                    "region": "Ohio",
                    "postal_code": "43215",
                    "options": {
                        "update_existing": True
                    }
                }
            }
        }

        post_params = {
            "tr_data": CreditCard.tr_data_for_update(tr_data, "http://example.com/path")
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_update_url())
        result = CreditCard.confirm_transparent_redirect(query_string)

        self.assertEquals(1, len(Customer.find(customer.id).addresses))
        updated_card = CreditCard.find(card.token)
        self.assertEquals("123 New St", updated_card.billing_address.street_address)
        self.assertEquals("Columbus", updated_card.billing_address.locality)
        self.assertEquals("Ohio", updated_card.billing_address.region)
        self.assertEquals("43215", updated_card.billing_address.postal_code)

    def test_update_from_transparent_redirect_with_error_result(self):
        old_token = str(random.randint(1, 1000000))
        credit_card = Customer.create({
            "credit_card": {
                "cardholder_name": "Old Cardholder Name",
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "token": old_token
            }
        }).customer.credit_cards[0]

        tr_data = {
            "payment_method_token": old_token,
            "credit_card": {
                "token": "bad token"
            }
        }

        post_params = {
            "tr_data": CreditCard.tr_data_for_update(tr_data, "http://example.com/path"),
            "credit_card[cardholder_name]": "New Cardholder Name",
            "credit_card[expiration_date]": "05/2014"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_update_url())
        result = CreditCard.confirm_transparent_redirect(query_string)
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.CreditCard.TokenInvalid,
            result.errors.for_object("credit_card").on("token")[0].code
        )

    def test_expired_can_iterate_over_all_items(self):
        customer_id = Customer.all().first.id

        for i in range(110 - CreditCard.expired().maximum_size):
            CreditCard.create({
                "customer_id": customer_id,
                "number": "4111111111111111",
                "expiration_date": "05/2009",
                "cvv": "100",
                "cardholder_name": "John Doe"
            })

        collection = CreditCard.expired()
        self.assertTrue(collection.maximum_size > 100)

        credit_card_tokens = [credit_card.token for credit_card in collection.items]
        self.assertEquals(collection.maximum_size, len(TestHelper.unique(credit_card_tokens)))

        self.assertEquals(set([True]), TestHelper.unique([credit_card.is_expired for credit_card in collection.items]))

    def test_expiring_between(self):
        customer_id = Customer.all().first.id

        for i in range(110 - CreditCard.expiring_between(date(2010, 1, 1), date(2010, 12, 31)).maximum_size):
            CreditCard.create({
                "customer_id": customer_id,
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100",
                "cardholder_name": "John Doe"
            })

        collection = CreditCard.expiring_between(date(2010, 1, 1), date(2010, 12, 31))
        self.assertTrue(collection.maximum_size > 100)

        credit_card_tokens = [credit_card.token for credit_card in collection.items]
        self.assertEquals(collection.maximum_size, len(TestHelper.unique(credit_card_tokens)))

        self.assertEquals(set(['2010']), TestHelper.unique([credit_card.expiration_year for credit_card in collection.items]))

    def test_commercial_card(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.Commercial,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.Commercial.Yes, credit_card.commercial)

    def test_issuing_bank(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.IssuingBank,
            "expiration_date": "05/2014"
        })

        credit_card = result.credit_card

        self.assertEquals(credit_card.issuing_bank, CreditCardDefaults.IssuingBank)

    def test_country_of_issuance(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.CountryOfIssuance,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(credit_card.country_of_issuance, CreditCardDefaults.CountryOfIssuance)

    def test_durbin_regulated_card(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.DurbinRegulated,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.DurbinRegulated.Yes, credit_card.durbin_regulated)

    def test_debit_card(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.Debit,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.Debit.Yes, credit_card.debit)

    def test_healthcare_card(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.Healthcare,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.Healthcare.Yes, credit_card.healthcare)

    def test_payroll_card(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.Payroll,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.Payroll.Yes, credit_card.payroll)

    def test_prepaid_card(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.Prepaid,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.Prepaid.Yes, credit_card.prepaid)

    def test_all_negative_card_type_indicators(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.No,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.Debit.No, credit_card.debit)
        self.assertEquals(CreditCard.DurbinRegulated.No, credit_card.durbin_regulated)
        self.assertEquals(CreditCard.Prepaid.No, credit_card.prepaid)
        self.assertEquals(CreditCard.Payroll.No, credit_card.payroll)
        self.assertEquals(CreditCard.Commercial.No, credit_card.commercial)
        self.assertEquals(CreditCard.Healthcare.No, credit_card.healthcare)

    def test_card_without_card_type_indicators(self):
        customer = Customer.create().customer
        result = CreditCard.create({
            "customer_id": customer.id,
            "number": CreditCardNumbers.CardTypeIndicators.Unknown,
            "expiration_date": "05/2014",
            "options": {"verify_card": True}
        })

        credit_card = result.credit_card

        self.assertEquals(CreditCard.Debit.Unknown, credit_card.debit)
        self.assertEquals(CreditCard.DurbinRegulated.Unknown, credit_card.durbin_regulated)
        self.assertEquals(CreditCard.Prepaid.Unknown, credit_card.prepaid)
        self.assertEquals(CreditCard.Payroll.Unknown, credit_card.payroll)
        self.assertEquals(CreditCard.Commercial.Unknown, credit_card.commercial)
        self.assertEquals(CreditCard.Healthcare.Unknown, credit_card.healthcare)
        self.assertEquals(CreditCard.IssuingBank.Unknown, credit_card.issuing_bank)
        self.assertEquals(CreditCard.CountryOfIssuance.Unknown, credit_card.country_of_issuance)

########NEW FILE########
__FILENAME__ = test_credit_card_verification
from tests.test_helper import *
from braintree.test.credit_card_numbers import CreditCardNumbers

class TestCreditCard(unittest.TestCase):
    def test_find_with_verification_id(self):
        customer = Customer.create({
            "credit_card": {
                "number": CreditCardNumbers.FailsSandboxVerification.MasterCard,
                "expiration_date": "05/2012",
                "cardholder_name": "Tom Smith",
                "options": {"verify_card": True}
        }})

        created_verification = customer.credit_card_verification
        found_verification = CreditCardVerification.find(created_verification.id)
        self.assertEquals(created_verification, found_verification)

    def test_verification_not_found(self):
        self.assertRaises(NotFoundError, CreditCardVerification.find,
          "invalid-id")

    def test_card_type_indicators(self):
        cardholder_name = "Tom %s" % randint(1, 10000)
        Customer.create({"credit_card": {
            "cardholder_name": cardholder_name,
            "expiration_date": "10/2012",
            "number": CreditCardNumbers.CardTypeIndicators.Unknown,
            "options": {"verify_card": True}
        }})
        found_verifications = CreditCardVerification.search(
            CreditCardVerificationSearch.credit_card_cardholder_name == cardholder_name
        )

        self.assertEqual(CreditCard.Prepaid.Unknown, found_verifications.first.credit_card['prepaid'])
        self.assertEqual(CreditCard.Debit.Unknown, found_verifications.first.credit_card['debit'])
        self.assertEqual(CreditCard.Commercial.Unknown, found_verifications.first.credit_card['commercial'])
        self.assertEqual(CreditCard.Healthcare.Unknown, found_verifications.first.credit_card['healthcare'])
        self.assertEqual(CreditCard.Payroll.Unknown, found_verifications.first.credit_card['payroll'])
        self.assertEqual(CreditCard.DurbinRegulated.Unknown, found_verifications.first.credit_card['durbin_regulated'])
        self.assertEqual(CreditCard.CardTypeIndicator.Unknown, found_verifications.first.credit_card['issuing_bank'])
        self.assertEqual(CreditCard.CardTypeIndicator.Unknown, found_verifications.first.credit_card['country_of_issuance'])


########NEW FILE########
__FILENAME__ = test_credit_card_verification_search
from tests.test_helper import *
from braintree.test.credit_card_numbers import CreditCardNumbers

class TestVerificationSearch(unittest.TestCase):
    def test_advanced_search_no_results(self):
        collection = CreditCardVerification.search([
            CreditCardVerificationSearch.credit_card_cardholder_name == "no such person"])
        self.assertEquals(0, collection.maximum_size)

    def test_all_text_fields(self):
        cardholder_name = "Tom %s" % randint(1, 10000)
        expiration_date = "10/2012"
        number = CreditCardNumbers.FailsSandboxVerification.MasterCard
        unsuccessful_result = Customer.create({"credit_card": {
            "cardholder_name": cardholder_name,
            "expiration_date": expiration_date,
            "number": number,
            "options": {"verify_card": True}
        }})

        found_verifications = CreditCardVerification.search(
            CreditCardVerificationSearch.credit_card_expiration_date == expiration_date,
            CreditCardVerificationSearch.credit_card_cardholder_name == cardholder_name,
            CreditCardVerificationSearch.credit_card_number == number
        )

        self.assertEqual(1, found_verifications.maximum_size)
        created_verification = unsuccessful_result.credit_card_verification
        self.assertEqual(created_verification, found_verifications.first)

    def test_multiple_value_fields(self):
        cardholder_name = "Tom %s" % randint(1, 10000)
        number = CreditCardNumbers.FailsSandboxVerification.MasterCard
        unsuccessful_result1 = Customer.create({"credit_card": {
            "cardholder_name": cardholder_name,
            "expiration_date": "10/2013",
            "number": number,
            "options": {"verify_card": True}
        }})

        cardholder_name = "Tom %s" % randint(1, 10000)
        number = CreditCardNumbers.FailsSandboxVerification.Visa
        unsuccessful_result2 = Customer.create({"credit_card": {
            "cardholder_name": cardholder_name,
            "expiration_date": "10/2012",
            "number": number,
            "options": {"verify_card": True}
        }})

        verification_id1 = unsuccessful_result1.credit_card_verification.id
        verification_id2 = unsuccessful_result2.credit_card_verification.id

        search_results = CreditCardVerification.search(
                CreditCardVerificationSearch.ids.in_list([
                    verification_id1, verification_id2
        ]))

        self.assertEquals(2, search_results.maximum_size)

    def test_range_field(self):
        cardholder_name = "Tom %s" % randint(1, 10000)
        number = CreditCardNumbers.FailsSandboxVerification.MasterCard
        unsuccessful_result = Customer.create({"credit_card": {
            "cardholder_name": cardholder_name,
            "expiration_date": "10/2013",
            "number": number,
            "options": {"verify_card": True}
        }})

        created_verification = unsuccessful_result.credit_card_verification
        created_time = created_verification.created_at
        before_creation = created_time - timedelta(minutes=10)
        after_creation = created_time + timedelta(minutes=10)
        found_verifications = CreditCardVerification.search(
                CreditCardVerificationSearch.id == created_verification.id,
                CreditCardVerificationSearch.created_at.between(before_creation, after_creation))

        self.assertEquals(1, found_verifications.maximum_size)

        way_before_creation = created_time - timedelta(minutes=10)
        just_before_creation = created_time - timedelta(minutes=1)
        found_verifications = CreditCardVerification.search(
                CreditCardVerificationSearch.id == created_verification.id,
                CreditCardVerificationSearch.created_at.between(way_before_creation, just_before_creation))

        self.assertEquals(0, found_verifications.maximum_size)

        found_verifications = CreditCardVerification.search(
                CreditCardVerificationSearch.id == created_verification.id,
                CreditCardVerificationSearch.created_at == created_time)

        self.assertEquals(1, found_verifications.maximum_size)


########NEW FILE########
__FILENAME__ = test_customer
from tests.test_helper import *
import braintree.test.venmo_sdk as venmo_sdk

class TestCustomer(unittest.TestCase):
    def test_all(self):
        collection = Customer.all()
        self.assertTrue(collection.maximum_size > 100)
        customer_ids = [c.id for c in collection.items]
        self.assertEquals(collection.maximum_size, len(TestHelper.unique(customer_ids)))
        self.assertEquals(Customer, type(collection.first))

    def test_create(self):
        result = Customer.create({
            "first_name": "Bill",
            "last_name": "Gates",
            "company": "Microsoft",
            "email": "bill@microsoft.com",
            "phone": "312.555.1234",
            "fax": "614.555.5678",
            "website": "www.microsoft.com"
        })

        self.assertTrue(result.is_success)
        customer = result.customer

        self.assertEqual("Bill", customer.first_name)
        self.assertEqual("Gates", customer.last_name)
        self.assertEqual("Microsoft", customer.company)
        self.assertEqual("bill@microsoft.com", customer.email)
        self.assertEqual("312.555.1234", customer.phone)
        self.assertEqual("614.555.5678", customer.fax)
        self.assertEqual("www.microsoft.com", customer.website)
        self.assertNotEqual(None, customer.id)
        self.assertNotEqual(None, re.search("\A\d{6,7}\Z", customer.id))

    def test_create_with_device_session_id_and_fraud_merchant_id(self):
        result = Customer.create({
            "first_name": "Bill",
            "last_name": "Gates",
            "company": "Microsoft",
            "email": "bill@microsoft.com",
            "phone": "312.555.1234",
            "fax": "614.555.5678",
            "website": "www.microsoft.com",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100",
                "device_session_id": "abc123",
                "fraud_merchant_id": "456"
            }
        })

        self.assertTrue(result.is_success)

    def test_create_with_unicode(self):
        result = Customer.create({
            "first_name": u"Bill<&>",
            "last_name": u"G\u1F00t\u1F18s",
            "company": "Microsoft",
            "email": "bill@microsoft.com",
            "phone": "312.555.1234",
            "fax": "614.555.5678",
            "website": "www.microsoft.com"
        })

        self.assertTrue(result.is_success)
        customer = result.customer

        self.assertEqual(u"Bill<&>", customer.first_name)
        self.assertEqual(u"G\u1f00t\u1F18s", customer.last_name)
        self.assertEqual("Microsoft", customer.company)
        self.assertEqual("bill@microsoft.com", customer.email)
        self.assertEqual("312.555.1234", customer.phone)
        self.assertEqual("614.555.5678", customer.fax)
        self.assertEqual("www.microsoft.com", customer.website)
        self.assertNotEqual(None, customer.id)
        self.assertNotEqual(None, re.search("\A\d{6,7}\Z", customer.id))

        found_customer = Customer.find(customer.id)
        self.assertEqual(u"G\u1f00t\u1F18s", found_customer.last_name)

    def test_create_with_no_attributes(self):
        result = Customer.create()
        self.assertTrue(result.is_success)
        self.assertNotEqual(None, result.customer.id)

    def test_create_with_special_chars(self):
        result = Customer.create({"first_name": "XML Chars <>&'\""})
        self.assertTrue(result.is_success)
        self.assertEqual("XML Chars <>&'\"", result.customer.first_name)

    def test_create_returns_an_error_response_if_invalid(self):
        result = Customer.create({
            "email": "@invalid.com",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "billing_address": {
                    "country_code_alpha2": "MX",
                    "country_code_alpha3": "USA"
                }
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(2, result.errors.size)
        self.assertEquals(ErrorCodes.Customer.EmailIsInvalid, result.errors.for_object("customer").on("email")[0].code)
        self.assertEquals(
            ErrorCodes.Address.InconsistentCountry,
            result.errors.for_object("customer").for_object("credit_card").for_object("billing_address").on("base")[0].code
        )

    def test_create_customer_and_payment_method_at_the_same_time(self):
        result = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100"
            }
        })

        self.assertTrue(result.is_success)

        customer = result.customer
        self.assertEqual("Mike", customer.first_name)
        self.assertEqual("Jones", customer.last_name)

        credit_card = customer.credit_cards[0]
        self.assertEqual("411111", credit_card.bin)
        self.assertEqual("1111", credit_card.last_4)
        self.assertEqual("05/2010", credit_card.expiration_date)

    def test_create_customer_and_verify_payment_method(self):
        result = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4000111111111115",
                "expiration_date": "05/2010",
                "cvv": "100",
                "options": {"verify_card": True}
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(CreditCardVerification.Status.ProcessorDeclined, result.credit_card_verification.status)

    def test_create_customer_with_check_duplicate_payment_method(self):
        attributes = {
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4000111111111115",
                "expiration_date": "05/2010",
                "cvv": "100",
                "options": {"fail_on_duplicate_payment_method": True}
            }
        }

        Customer.create(attributes)
        result = Customer.create(attributes)

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.CreditCard.DuplicateCardExists, result.errors.for_object("customer").for_object("credit_card").on("number")[0].code)
        self.assertEquals("Duplicate card exists in the vault.", result.message)

    def test_create_customer_with_payment_method_and_billing_address(self):
        result = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100",
                "billing_address": {
                    "street_address": "123 Abc Way",
                    "locality": "Chicago",
                    "region": "Illinois",
                    "postal_code": "60622",
                    "country_code_alpha2": "US",
                    "country_code_alpha3": "USA",
                    "country_code_numeric": "840",
                    "country_name": "United States of America"
                }
            }
        })

        self.assertTrue(result.is_success)

        customer = result.customer
        self.assertEqual("Mike", customer.first_name)
        self.assertEqual("Jones", customer.last_name)

        address = customer.credit_cards[0].billing_address
        self.assertEqual("123 Abc Way", address.street_address)
        self.assertEqual("Chicago", address.locality)
        self.assertEqual("Illinois", address.region)
        self.assertEqual("60622", address.postal_code)
        self.assertEqual("US", address.country_code_alpha2)
        self.assertEqual("USA", address.country_code_alpha3)
        self.assertEqual("840", address.country_code_numeric)
        self.assertEqual("United States of America", address.country_name)

    def test_create_with_customer_fields(self):
        result = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "custom_fields": {
                "store_me": "custom value"
            }
        })

        self.assertTrue(result.is_success)
        self.assertEquals("custom value", result.customer.custom_fields["store_me"])

    def test_create_returns_nested_errors(self):
        result = Customer.create({
            "email": "invalid",
            "credit_card": {
                "number": "invalid",
                "billing_address": {
                    "country_name": "invalid"
                }
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Customer.EmailIsInvalid,
            result.errors.for_object("customer").on("email")[0].code
        )
        self.assertEquals(
            ErrorCodes.CreditCard.NumberHasInvalidLength,
            result.errors.for_object("customer").for_object("credit_card").on("number")[0].code
        )
        self.assertEquals(
            ErrorCodes.Address.CountryNameIsNotAccepted,
            result.errors.for_object("customer").for_object("credit_card").for_object("billing_address").on("country_name")[0].code
        )

    def test_create_returns_errors_if_custom_fields_are_not_registered(self):
        result = Customer.create({
            "first_name": "Jack",
            "last_name": "Kennedy",
            "custom_fields": {
                "spouse_name": "Jacqueline"
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.Customer.CustomFieldIsInvalid, result.errors.for_object("customer").on("custom_fields")[0].code)

    def test_create_with_venmo_sdk_session(self):
        result = Customer.create({
            "first_name": "Jack",
            "last_name": "Kennedy",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "options": {
                    "venmo_sdk_session": venmo_sdk.Session
                }
            }
        })

        self.assertTrue(result.is_success)
        self.assertTrue(result.customer.credit_cards[0].venmo_sdk)

    def test_create_with_venmo_sdk_payment_method_code(self):
        result = Customer.create({
            "first_name": "Jack",
            "last_name": "Kennedy",
            "credit_card": {
                "venmo_sdk_payment_method_code": venmo_sdk.generate_test_payment_method_code("4111111111111111")
            }
        })

        self.assertTrue(result.is_success)
        self.assertEquals("411111", result.customer.credit_cards[0].bin)

    def test_create_with_payment_method_nonce(self):
        config = Configuration.instantiate()
        authorization_fingerprint = json.loads(ClientToken.generate())["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })
        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            },
            "share": True
        })
        nonce = json.loads(response)["nonce"]

        result = Customer.create({
            "credit_card": {
                "payment_method_nonce": nonce
            }
        })

        self.assertTrue(result.is_success)
        self.assertEquals("411111", result.customer.credit_cards[0].bin)

    def test_delete_with_valid_customer(self):
        customer = Customer.create().customer
        result = Customer.delete(customer.id)

        self.assertTrue(result.is_success)

    @raises(NotFoundError)
    def test_delete_with_invalid_customer(self):
        customer = Customer.create().customer
        Customer.delete(customer.id)
        Customer.delete(customer.id)

    def test_find_with_valid_customer(self):
        customer = Customer.create({
            "first_name": "Joe",
            "last_name": "Cool"
        }).customer

        found_customer = Customer.find(customer.id)
        self.assertEquals(customer.id, found_customer.id)
        self.assertEquals(customer.first_name, found_customer.first_name)
        self.assertEquals(customer.last_name, found_customer.last_name)

    def test_find_with_invalid_customer(self):
        try:
            Customer.find("badid")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertEquals("customer with id badid not found", str(e))

    def test_update_with_valid_options(self):
        customer = Customer.create({
            "first_name": "Steve",
            "last_name": "Jobs",
            "company": "Apple",
            "email": "steve@apple.com",
            "phone": "312.555.5555",
            "fax": "614.555.5555",
            "website": "www.apple.com"
        }).customer

        result = Customer.update(customer.id, {
            "first_name": "Bill",
            "last_name": "Gates",
            "company": "Microsoft",
            "email": "bill@microsoft.com",
            "phone": "312.555.1234",
            "fax": "614.555.5678",
            "website": "www.microsoft.com"
        })

        self.assertTrue(result.is_success)
        customer = result.customer

        self.assertEqual("Bill", customer.first_name)
        self.assertEqual("Gates", customer.last_name)
        self.assertEqual("Microsoft", customer.company)
        self.assertEqual("bill@microsoft.com", customer.email)
        self.assertEqual("312.555.1234", customer.phone)
        self.assertEqual("614.555.5678", customer.fax)
        self.assertEqual("www.microsoft.com", customer.website)
        self.assertNotEqual(None, customer.id)
        self.assertNotEqual(None, re.search("\A\d{6,7}\Z", customer.id))

    def test_update_with_nested_values(self):
        customer = Customer.create({
            "first_name": "Steve",
            "last_name": "Jobs",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "10/10",
                "billing_address": {
                    "postal_code": "11111"
                }
            }
        }).customer
        credit_card = customer.credit_cards[0]
        address = credit_card.billing_address

        updated_customer = Customer.update(customer.id, {
            "first_name": "Bill",
            "last_name": "Gates",
            "credit_card": {
                "expiration_date": "12/12",
                "options": {
                    "update_existing_token": credit_card.token
                },
                "billing_address": {
                    "postal_code": "44444",
                    "country_code_alpha2": "US",
                    "country_code_alpha3": "USA",
                    "country_code_numeric": "840",
                    "country_name": "United States of America",
                    "options": {
                        "update_existing": True
                    }
                }
            }
        }).customer
        updated_credit_card = CreditCard.find(credit_card.token)
        updated_address = Address.find(customer.id, address.id)

        self.assertEqual("Bill", updated_customer.first_name)
        self.assertEqual("Gates", updated_customer.last_name)
        self.assertEqual("12/2012", updated_credit_card.expiration_date)
        self.assertEqual("44444", updated_address.postal_code)
        self.assertEqual("US", updated_address.country_code_alpha2)
        self.assertEqual("USA", updated_address.country_code_alpha3)
        self.assertEqual("840", updated_address.country_code_numeric)
        self.assertEqual("United States of America", updated_address.country_name)

    def test_update_with_nested_billing_address_id(self):
        customer = Customer.create().customer
        address = Address.create({
            "customer_id": customer.id,
            "postal_code": "11111"
        }).address

        updated_customer = Customer.update(customer.id, {
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "12/12",
                "billing_address_id": address.id
            }
        }).customer

        credit_card = updated_customer.credit_cards[0]

        self.assertEqual(address.id, credit_card.billing_address.id)
        self.assertEqual("11111", credit_card.billing_address.postal_code)

    def test_update_with_invalid_options(self):
        customer = Customer.create({
            "first_name": "Steve",
            "last_name": "Jobs",
            "company": "Apple",
            "email": "steve@apple.com",
            "phone": "312.555.5555",
            "fax": "614.555.5555",
            "website": "www.apple.com"
        }).customer

        result = Customer.update(customer.id, {
            "email": "@microsoft.com",
        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Customer.EmailIsInvalid,
            result.errors.for_object("customer").on("email")[0].code
        )

    def test_create_from_transparent_redirect_with_successful_result(self):
        tr_data = {
            "customer": {
                "first_name": "John",
                "last_name": "Doe",
                "company": "Doe Co",
            }
        }
        post_params = {
            "tr_data": Customer.tr_data_for_create(tr_data, "http://example.com/path"),
            "customer[email]": "john@doe.com",
            "customer[phone]": "312.555.2323",
            "customer[fax]": "614.555.5656",
            "customer[website]": "www.johndoe.com",
            "customer[credit_card][number]": "4111111111111111",
            "customer[credit_card][expiration_date]": "05/2012",
            "customer[credit_card][billing_address][country_code_alpha2]": "MX",
            "customer[credit_card][billing_address][country_code_alpha3]": "MEX",
            "customer[credit_card][billing_address][country_code_numeric]": "484",
            "customer[credit_card][billing_address][country_name]": "Mexico",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Customer.transparent_redirect_create_url())
        result = Customer.confirm_transparent_redirect(query_string)
        self.assertTrue(result.is_success)
        customer = result.customer
        self.assertEquals("John", customer.first_name)
        self.assertEquals("Doe", customer.last_name)
        self.assertEquals("Doe Co", customer.company)
        self.assertEquals("john@doe.com", customer.email)
        self.assertEquals("312.555.2323", customer.phone)
        self.assertEquals("614.555.5656", customer.fax)
        self.assertEquals("www.johndoe.com", customer.website)
        self.assertEquals("05/2012", customer.credit_cards[0].expiration_date)
        self.assertEquals("MX", customer.credit_cards[0].billing_address.country_code_alpha2)
        self.assertEquals("MEX", customer.credit_cards[0].billing_address.country_code_alpha3)
        self.assertEquals("484", customer.credit_cards[0].billing_address.country_code_numeric)
        self.assertEquals("Mexico", customer.credit_cards[0].billing_address.country_name)

    def test_create_from_transparent_redirect_with_error_result(self):
        tr_data = {
            "customer": {
                "company": "Doe Co",
            }
        }
        post_params = {
            "tr_data": Customer.tr_data_for_create(tr_data, "http://example.com/path"),
            "customer[email]": "john#doe.com",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Customer.transparent_redirect_create_url())
        result = Customer.confirm_transparent_redirect(query_string)
        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.Customer.EmailIsInvalid, result.errors.for_object("customer").on("email")[0].code)

    def test_update_from_transparent_redirect_with_successful_result(self):
        customer = Customer.create({
            "first_name": "Jane",
        }).customer

        tr_data = {
            "customer_id": customer.id,
            "customer": {
                "first_name": "John",
            }
        }
        post_params = {
            "tr_data": Customer.tr_data_for_update(tr_data, "http://example.com/path"),
            "customer[email]": "john@doe.com",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Customer.transparent_redirect_update_url())
        result = Customer.confirm_transparent_redirect(query_string)
        self.assertTrue(result.is_success)
        customer = result.customer
        self.assertEquals("John", customer.first_name)
        self.assertEquals("john@doe.com", customer.email)

    def test_update_with_nested_values_via_transparent_redirect(self):
        customer = Customer.create({
            "first_name": "Steve",
            "last_name": "Jobs",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "10/10",
                "billing_address": {
                    "postal_code": "11111"
                }
            }
        }).customer
        credit_card = customer.credit_cards[0]
        address = credit_card.billing_address

        tr_data = {
            "customer_id": customer.id,
            "customer": {
                "first_name": "Bill",
                "last_name": "Gates",
                "credit_card": {
                    "expiration_date": "12/12",
                    "options": {
                        "update_existing_token": credit_card.token
                    },
                    "billing_address": {
                        "postal_code": "44444",
                        "options": {
                            "update_existing": True
                        }
                    }
                }
            }
        }
        post_params = {
            "tr_data": Customer.tr_data_for_update(tr_data, "http://example.com/path"),
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Customer.transparent_redirect_update_url())
        updated_customer = Customer.confirm_transparent_redirect(query_string).customer
        updated_credit_card = CreditCard.find(credit_card.token)
        updated_address = Address.find(customer.id, address.id)

        self.assertEqual("Bill", updated_customer.first_name)
        self.assertEqual("Gates", updated_customer.last_name)
        self.assertEqual("12/2012", updated_credit_card.expiration_date)
        self.assertEqual("44444", updated_address.postal_code)

    def test_update_from_transparent_redirect_with_error_result(self):
        customer = Customer.create({
            "first_name": "Jane",
        }).customer

        tr_data = {
            "customer_id": customer.id,
            "customer": {
                "first_name": "John",
            }
        }
        post_params = {
            "tr_data": Customer.tr_data_for_update(tr_data, "http://example.com/path"),
            "customer[email]": "john#doe.com",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Customer.transparent_redirect_update_url())
        result = Customer.confirm_transparent_redirect(query_string)
        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.Customer.EmailIsInvalid, result.errors.for_object("customer").on("email")[0].code)

########NEW FILE########
__FILENAME__ = test_customer_search
from tests.test_helper import *

class TestCustomerSearch(unittest.TestCase):
    def test_advanced_search_no_results(self):
        collection = Transaction.search([
            TransactionSearch.billing_first_name == "no_such_person"
        ])
        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_finds_duplicate_cards_given_payment_method_token(self):
        credit_card_dict = {
            "number": "63049580000009",
            "expiration_date": "05/2010"
        }

        jim_dict = {
            "first_name": "Jim",
            "credit_card": credit_card_dict
        }

        joe_dict = {
            "first_name": "Joe",
            "credit_card": credit_card_dict
        }

        jim = Customer.create(jim_dict).customer
        joe = Customer.create(joe_dict).customer

        collection = Customer.search(
            CustomerSearch.payment_method_token_with_duplicates == jim.credit_cards[0].token,
        )

        customer_ids = [customer.id for customer in collection.items]
        self.assertTrue(jim.id in customer_ids)
        self.assertTrue(joe.id in customer_ids)


    def test_advanced_search_searches_all_text_fields(self):
        token = "creditcard%s" % randint(1, 100000)

        customer = Customer.create({
            "first_name": "Timmy",
            "last_name": "O'Toole",
            "company": "O'Toole and Son(s)",
            "email": "timmy@example.com",
            "fax": "3145551234",
            "phone": "5551231234",
            "website": "http://example.com",
            "credit_card": {
                "cardholder_name": "Tim Toole",
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "token": token,
                "billing_address": {
                    "first_name": "Thomas",
                    "last_name": "Otool",
                    "street_address": "1 E Main St",
                    "extended_address": "Suite 3",
                    "locality": "Chicago",
                    "region": "Illinois",
                    "postal_code": "60622",
                    "country_name": "United States of America"
                }
            }
        }).customer

        search_criteria = {
            "first_name": "Timmy",
            "last_name": "O'Toole",
            "company": "O'Toole and Son(s)",
            "email": "timmy@example.com",
            "phone": "5551231234",
            "fax": "3145551234",
            "website": "http://example.com",
            "address_first_name": "Thomas",
            "address_last_name": "Otool",
            "address_street_address": "1 E Main St",
            "address_postal_code": "60622",
            "address_extended_address": "Suite 3",
            "address_locality": "Chicago",
            "address_region": "Illinois",
            "address_country_name": "United States of America",
            "payment_method_token": token,
            "cardholder_name": "Tim Toole",
            "credit_card_number": "4111111111111111",
            "credit_card_expiration_date": "05/2010"
        }

        criteria = [getattr(CustomerSearch, search_field) == value for search_field, value in search_criteria.items()]
        criteria.append(CustomerSearch.id == customer.id)

        collection = Customer.search(criteria)

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(customer.id, collection.first.id)

        for search_field, value in search_criteria.items():
            collection = Customer.search(
                CustomerSearch.id == customer.id,
                getattr(CustomerSearch, search_field) == value
            )

            self.assertEquals(1, collection.maximum_size)
            self.assertEquals(customer.id, collection.first.id)

    def test_advanced_search_range_node_created_at(self):
        customer = Customer.create().customer

        past = customer.created_at - timedelta(minutes=10)
        future = customer.created_at + timedelta(minutes=10)

        collection = Customer.search(
            CustomerSearch.id == customer.id,
            CustomerSearch.created_at.between(past, future)
        )

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(customer.id, collection.first.id)

        collection = Customer.search(
            CustomerSearch.id == customer.id,
            CustomerSearch.created_at <= future
        )

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(customer.id, collection.first.id)

        collection = Customer.search(
            CustomerSearch.id == customer.id,
            CustomerSearch.created_at >= past
        )

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(customer.id, collection.first.id)

########NEW FILE########
__FILENAME__ = test_disbursement
from tests.test_helper import *
from datetime import date

class TestDisbursement(unittest.TestCase):
    def test_disbursement_finds_transactions(self):
        disbursement = Disbursement(Configuration.gateway(), {
            "merchant_account": {
                "id": "sub_merchant_account",
                "status": "active",
                "master_merchant_account": {
                    "id": "master_merchant_account",
                    "status": "active"
                },
            },
            "id": "123456",
            "exception_message": "invalid_account_number",
            "amount": "100.00",
            "disbursement_date": date(2013, 4, 10),
            "follow_up_action": "update",
            "transaction_ids": ["sub_merchant_transaction"]
        })

        transactions = disbursement.transactions()
        self.assertEquals(1, transactions.maximum_size)
        self.assertEquals("sub_merchant_transaction", transactions.first.id)

########NEW FILE########
__FILENAME__ = test_discounts
from tests.test_helper import *

class TestDiscounts(unittest.TestCase):

    def test_all_returns_all_discounts(self):
        new_id = str(random.randint(1, 1000000))
        attributes = {
            "amount": "100.00",
            "description": "some description",
            "id": new_id,
            "kind": "discount",
            "name": "python_discount",
            "never_expires": False,
            "number_of_billing_cycles": 1
        }

        Configuration.instantiate().http().post("/modifications/create_modification_for_tests", {"modification": attributes})

        discounts = Discount.all()

        for discount in discounts:
            if discount.id == new_id:
                break
        else:
            discount = None

        self.assertNotEquals(None, discount)

        self.assertEquals(discount.amount, Decimal("100.00"))
        self.assertEquals(discount.description, "some description")
        self.assertEquals(discount.id, new_id)
        self.assertEquals(discount.kind, "discount")
        self.assertEquals(discount.name, "python_discount")
        self.assertEquals(discount.never_expires, False)
        self.assertEquals(discount.number_of_billing_cycles, 1)

########NEW FILE########
__FILENAME__ = test_http
from tests.test_helper import *
from distutils.version import LooseVersion
import platform
import braintree
import requests
import pycurl

class CommonHttpTests(object):
    def test_successful_connection_sandbox(self):
        http = self.get_http(Environment.Sandbox)
        try:
            http.get("/")
        except AuthenticationError:
            pass
        else:
            self.assertTrue(False)

    def test_successful_connection_production(self):
        http = self.get_http(Environment.Production)
        try:
            http.get("/")
        except AuthenticationError:
            pass
        else:
            self.assertTrue(False)

    def test_unsafe_ssl_connection(self):
        Configuration.use_unsafe_ssl = True;
        environment = Environment(Environment.Sandbox.server, "443", "http://auth.venmo.dev:9292", True, Environment.Production.ssl_certificate)
        http = self.get_http(environment)
        try:
            http.get("/")
        except AuthenticationError:
            pass
        finally:
            Configuration.use_unsafe_ssl = False;

class TestPyCurl(CommonHttpTests, unittest.TestCase):
    def get_http(self, environment):
        config = Configuration(environment, "merchant_id", "public_key", "private_key")
        config._http_strategy = braintree.util.http_strategy.pycurl_strategy.PycurlStrategy(config, config.environment)
        return config.http()

    def test_unsuccessful_connection_to_good_ssl_server_with_wrong_cert(self):
        if platform.system() == "Darwin":
            return

        environment = Environment("www.google.com", "443", "http://auth.venmo.dev:9292", True, Environment.Production.ssl_certificate)
        http = self.get_http(environment)
        try:
            http.get("/")
        except pycurl.error, e:
            error_code, error_msg = e
            self.assertEquals(pycurl.E_SSL_CACERT, error_code)
            self.assertTrue(re.search('verif(y|ication) failed', error_msg))
        except AuthenticationError:
            self.fail("Expected to receive an SSL error but received an Authentication Error instead, check your local openssl installation")
        else:
            self.fail("Expected to receive an SSL error but no exception was raised")

    def test_unsuccessful_connection_to_ssl_server_with_wrong_domain(self):
        #ip address of api.braintreegateway.com
        environment = Environment("204.109.13.121", "443", "http://auth.venmo.dev:9292", True, Environment.Production.ssl_certificate)
        http = self.get_http(environment)
        try:
            http.get("/")
        except pycurl.error, e:
            error_code, error_msg = e
            self.assertEquals(pycurl.E_SSL_PEER_CERTIFICATE, error_code)
            self.assertTrue(re.search("SSL: certificate subject name", error_msg))
        else:
            self.fail("Expected to receive an SSL error but no exception was raised")

class TestRequests(CommonHttpTests, unittest.TestCase):
    if LooseVersion(requests.__version__) >= LooseVersion('1.0.0'):
        SSLError = requests.exceptions.SSLError
    else:
        SSLError = requests.models.SSLError

    def get_http(self, environment):
        config = Configuration(environment, "merchant_id", "public_key", "private_key")
        config._http_strategy = braintree.util.http_strategy.requests_strategy.RequestsStrategy(config, config.environment)
        return config.http()

    def test_unsuccessful_connection_to_good_ssl_server_with_wrong_cert(self):
        if platform.system() == "Darwin":
            return

        environment = Environment("www.google.com", "443", "http://auth.venmo.dev:9292", True, Environment.Production.ssl_certificate)
        http = self.get_http(environment)
        try:
            http.get("/")
        except self.SSLError, e:
            self.assertTrue("SSL3_GET_SERVER_CERTIFICATE:certificate verify failed" in str(e.message))
        except AuthenticationError:
            self.fail("Expected to receive an SSL error but received an Authentication Error instead, check your local openssl installation")
        else:
            self.fail("Expected to receive an SSL error but no exception was raised")

    def test_unsuccessful_connection_to_ssl_server_with_wrong_domain(self):
        #ip address of api.braintreegateway.com
        environment = Environment("204.109.13.121", "443", "http://auth.venmo.dev:9292", True, Environment.Production.ssl_certificate)
        http = self.get_http(environment)
        try:
            http.get("/")
        except self.SSLError, e:
            pass
        else:
            self.fail("Expected to receive an SSL error but no exception was raised")

########NEW FILE########
__FILENAME__ = test_merchant_account
from tests.test_helper import *

class TestMerchantAccount(unittest.TestCase):
    DEPRECATED_APPLICATION_PARAMS = {
        "applicant_details": {
            "company_name": "Garbage Garage",
            "first_name": "Joe",
            "last_name": "Bloggs",
            "email": "joe@bloggs.com",
            "phone": "555-555-5555",
            "address": {
                "street_address": "123 Credibility St.",
                "postal_code": "60606",
                "locality": "Chicago",
                "region": "IL",
            },
            "date_of_birth": "10/9/1980",
            "ssn": "123-00-1234",
            "tax_id": "123456789",
            "routing_number": "122100024",
            "account_number": "43759348798"
        },
        "tos_accepted": True,
        "master_merchant_account_id": "sandbox_master_merchant_account"
    }

    VALID_APPLICATION_PARAMS = {
        "individual": {
            "first_name": "Joe",
            "last_name": "Bloggs",
            "email": "joe@bloggs.com",
            "phone": "555-555-5555",
            "address": {
                "street_address": "123 Credibility St.",
                "postal_code": "60606",
                "locality": "Chicago",
                "region": "IL",
            },
            "date_of_birth": "10/9/1980",
            "ssn": "123-00-1234",
        },
        "business": {
            "dba_name": "Garbage Garage",
            "legal_name": "Junk Jymnasium",
            "tax_id": "123456789",
            "address": {
                "street_address": "123 Reputation St.",
                "postal_code": "40222",
                "locality": "Louisville",
                "region": "KY",
            },
        },
        "funding": {
            "routing_number": "122100024",
            "account_number": "43759348798",
            "destination": MerchantAccount.FundingDestination.Bank
        },
        "tos_accepted": True,
        "master_merchant_account_id": "sandbox_master_merchant_account"
    }

    def test_create_accepts_deprecated_parameters(self):
        result = MerchantAccount.create(self.DEPRECATED_APPLICATION_PARAMS)

        self.assertTrue(result.is_success)
        self.assertEquals(MerchantAccount.Status.Pending, result.merchant_account.status)
        self.assertEquals("sandbox_master_merchant_account", result.merchant_account.master_merchant_account.id)

    def test_create_application_with_valid_params_and_no_id(self):
        customer = Customer.create().customer
        result = MerchantAccount.create(self.VALID_APPLICATION_PARAMS)

        self.assertTrue(result.is_success)
        self.assertEquals(MerchantAccount.Status.Pending, result.merchant_account.status)
        self.assertEquals("sandbox_master_merchant_account", result.merchant_account.master_merchant_account.id)

    def test_create_allows_an_id_to_pass(self):
        params_with_id = self.VALID_APPLICATION_PARAMS.copy()
        rand = str(random.randrange(1000000))
        params_with_id['id'] = 'sub_merchant_account_id' + rand
        result = MerchantAccount.create(params_with_id)

        self.assertTrue(result.is_success)
        self.assertEquals(MerchantAccount.Status.Pending, result.merchant_account.status)
        self.assertEquals(params_with_id['id'], result.merchant_account.id)
        self.assertEquals("sandbox_master_merchant_account", result.merchant_account.master_merchant_account.id)

    def test_create_handles_unsuccessful_results(self):
        result = MerchantAccount.create({})
        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.MerchantAccount.MasterMerchantAccountIdIsRequired, result.errors.for_object("merchant_account").on("master_merchant_account_id")[0].code)

    def test_create_requires_all_fields(self):
        result = MerchantAccount.create(
            {"master_merchant_account_id": "sandbox_master_merchant_account",
             "applicant_details": {},
            "tos_accepted": True}
        )
        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.MerchantAccount.ApplicantDetails.FirstNameIsRequired, result.errors.for_object("merchant_account").for_object("applicant_details").on("first_name")[0].code)

    def test_create_funding_destination_accepts_a_bank(self):
        params = self.VALID_APPLICATION_PARAMS.copy()
        params['funding']['destination'] = MerchantAccount.FundingDestination.Bank
        result = MerchantAccount.create(params)
        self.assertTrue(result.is_success)

    def test_create_funding_destination_accepts_an_email(self):
        params = self.VALID_APPLICATION_PARAMS.copy()
        params['funding']['destination'] = MerchantAccount.FundingDestination.Email
        params['funding']['email'] = "junkman@hotmail.com"
        result = MerchantAccount.create(params)
        self.assertTrue(result.is_success)

    def test_create_funding_destination_accepts_a_mobile_phone(self):
        params = self.VALID_APPLICATION_PARAMS.copy()
        params['funding']['destination'] = MerchantAccount.FundingDestination.MobilePhone
        params['funding']['mobile_phone'] = "1112223333"
        result = MerchantAccount.create(params)
        self.assertTrue(result.is_success)

    def test_update_all_merchant_account_fields(self):
        UPDATE_PARAMS = {
            "individual": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "312-555-1234",
                "address": {
                    "street_address": "123 Fake St",
                    "postal_code": "60622",
                    "locality": "Chicago",
                    "region": "IL",
                },
                "date_of_birth": "1970-01-01",
                "ssn": "987-65-4321",
            },
            "business": {
                "dba_name": "James's Bloggs",
                "legal_name": "James's Junkyard",
                "tax_id": "987654321",
                "address": {
                    "street_address": "456 Fake St",
                    "postal_code": "48104",
                    "locality": "Ann Arbor",
                    "region": "MI",
                },
            },
            "funding": {
                "routing_number": "071000013",
                "account_number": "666666789",
                "destination": MerchantAccount.FundingDestination.Email,
                "email": "check@this.com",
                "mobile_phone": "9998887777"
            }
        }

        result = MerchantAccount.update("sandbox_sub_merchant_account", UPDATE_PARAMS)
        self.assertTrue(result.is_success)
        self.assertEquals(result.merchant_account.status, "active")
        self.assertEquals(result.merchant_account.id, "sandbox_sub_merchant_account")
        self.assertEquals(result.merchant_account.master_merchant_account.id, "sandbox_master_merchant_account")
        self.assertEquals(result.merchant_account.individual_details.first_name, "John")
        self.assertEquals(result.merchant_account.individual_details.last_name, "Doe")
        self.assertEquals(result.merchant_account.individual_details.email, "john.doe@example.com")
        self.assertEquals(result.merchant_account.individual_details.date_of_birth, "1970-01-01")
        self.assertEquals(result.merchant_account.individual_details.phone, "3125551234")
        self.assertEquals(result.merchant_account.individual_details.address_details.street_address, "123 Fake St")
        self.assertEquals(result.merchant_account.individual_details.address_details.locality, "Chicago")
        self.assertEquals(result.merchant_account.individual_details.address_details.region, "IL")
        self.assertEquals(result.merchant_account.individual_details.address_details.postal_code, "60622")
        self.assertEquals(result.merchant_account.business_details.dba_name, "James's Bloggs")
        self.assertEquals(result.merchant_account.business_details.legal_name, "James's Junkyard")
        self.assertEquals(result.merchant_account.business_details.tax_id, "987654321")
        self.assertEquals(result.merchant_account.business_details.address_details.street_address, "456 Fake St")
        self.assertEquals(result.merchant_account.business_details.address_details.postal_code, "48104")
        self.assertEquals(result.merchant_account.business_details.address_details.locality, "Ann Arbor")
        self.assertEquals(result.merchant_account.business_details.address_details.region, "MI")
        self.assertEquals(result.merchant_account.funding_details.routing_number, "071000013")
        self.assertEquals(result.merchant_account.funding_details.account_number_last_4, "6789")
        self.assertEquals(result.merchant_account.funding_details.destination, MerchantAccount.FundingDestination.Email)
        self.assertEquals(result.merchant_account.funding_details.email, "check@this.com")
        self.assertEquals(result.merchant_account.funding_details.mobile_phone, "9998887777")

    def test_update_does_not_require_all_fields(self):
        result = MerchantAccount.update("sandbox_sub_merchant_account", { "individual": { "first_name": "Jose" } })
        self.assertTrue(result.is_success)

    def test_update_handles_validation_errors_for_blank_fields(self):
        params = {
            "individual": {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone": "",
                "date_of_birth": "",
                "ssn": "",
                "address": {
                    "street_address": "",
                    "postal_code": "",
                    "locality": "",
                    "region": "",
                },
            },
            "business": {
                "legal_name": "",
                "dba_name": "",
                "tax_id": ""
            },
            "funding": {
                "destination": "",
                "routing_number": "",
                "account_number": ""
            }
        }
        result = MerchantAccount.update("sandbox_sub_merchant_account", params)

        self.assertFalse(result.is_success)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("first_name")[0].code, ErrorCodes.MerchantAccount.Individual.FirstNameIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("last_name")[0].code, ErrorCodes.MerchantAccount.Individual.LastNameIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("date_of_birth")[0].code, ErrorCodes.MerchantAccount.Individual.DateOfBirthIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("email")[0].code, ErrorCodes.MerchantAccount.Individual.EmailAddressIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").for_object("address").on("street_address")[0].code, ErrorCodes.MerchantAccount.Individual.Address.StreetAddressIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").for_object("address").on("postal_code")[0].code, ErrorCodes.MerchantAccount.Individual.Address.PostalCodeIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").for_object("address").on("locality")[0].code, ErrorCodes.MerchantAccount.Individual.Address.LocalityIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").for_object("address").on("region")[0].code, ErrorCodes.MerchantAccount.Individual.Address.RegionIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("destination")[0].code, ErrorCodes.MerchantAccount.Funding.DestinationIsRequired)
        self.assertEquals(len(result.errors.for_object("merchant_account").on("base")), 0)

    def test_update_handles_validation_errors_for_invalid_fields(self):
        params = {
          "individual": {
            "first_name": "<>",
            "last_name": "<>",
            "email": "bad",
            "phone": "999",
            "address": {
              "street_address": "nope",
              "postal_code": "1",
              "region": "QQ",
            },
            "date_of_birth": "hah",
            "ssn": "12345",
          },
          "business": {
            "legal_name": "``{}",
            "dba_name": "{}``",
            "tax_id": "bad",
            "address": {
              "street_address": "nope",
              "postal_code": "1",
              "region": "QQ",
            },
          },
          "funding": {
            "destination": "MY WALLET",
            "routing_number": "LEATHER",
            "account_number": "BACK POCKET",
            "email": "BILLFOLD",
            "mobile_phone": "TRIFOLD"
          },
        }

        result = MerchantAccount.update("sandbox_sub_merchant_account", params)

        self.assertFalse(result.is_success)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("first_name")[0].code, ErrorCodes.MerchantAccount.Individual.FirstNameIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("last_name")[0].code, ErrorCodes.MerchantAccount.Individual.LastNameIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("email")[0].code, ErrorCodes.MerchantAccount.Individual.EmailAddressIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("phone")[0].code, ErrorCodes.MerchantAccount.Individual.PhoneIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").for_object("address").on("street_address")[0].code,  ErrorCodes.MerchantAccount.Individual.Address.StreetAddressIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").for_object("address").on("postal_code")[0].code, ErrorCodes.MerchantAccount.Individual.Address.PostalCodeIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").for_object("address").on("region")[0].code, ErrorCodes.MerchantAccount.Individual.Address.RegionIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("individual").on("ssn")[0].code, ErrorCodes.MerchantAccount.Individual.SsnIsInvalid)

        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").on("legal_name")[0].code, ErrorCodes.MerchantAccount.Business.LegalNameIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").on("dba_name")[0].code, ErrorCodes.MerchantAccount.Business.DbaNameIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").on("tax_id")[0].code, ErrorCodes.MerchantAccount.Business.TaxIdIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").for_object("address").on("street_address")[0].code,  ErrorCodes.MerchantAccount.Business.Address.StreetAddressIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").for_object("address").on("postal_code")[0].code, ErrorCodes.MerchantAccount.Business.Address.PostalCodeIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").for_object("address").on("region")[0].code, ErrorCodes.MerchantAccount.Business.Address.RegionIsInvalid)

        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("destination")[0].code, ErrorCodes.MerchantAccount.Funding.DestinationIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("routing_number")[0].code, ErrorCodes.MerchantAccount.Funding.RoutingNumberIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("account_number")[0].code, ErrorCodes.MerchantAccount.Funding.AccountNumberIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("email")[0].code, ErrorCodes.MerchantAccount.Funding.EmailAddressIsInvalid)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("mobile_phone")[0].code, ErrorCodes.MerchantAccount.Funding.MobilePhoneIsInvalid)

        self.assertEquals(len(result.errors.for_object("merchant_account").on("base")), 0)

    def test_update_handles_validation_errors_for_business_fields(self):
        result = MerchantAccount.update("sandbox_sub_merchant_account", {
            "business": {
                "legal_name": "",
                "tax_id": "111223333"
                }
            }
        )

        self.assertFalse(result.is_success)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").on("legal_name")[0].code, ErrorCodes.MerchantAccount.Business.LegalNameIsRequiredWithTaxId)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").on("tax_id")[0].code, ErrorCodes.MerchantAccount.Business.TaxIdMustBeBlank)

        result = MerchantAccount.update("sandbox_sub_merchant_account", {
            "business": {
                "legal_name": "legal name",
                "tax_id": ""
                }
            }
        )

        self.assertFalse(result.is_success)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("business").on("tax_id")[0].code, ErrorCodes.MerchantAccount.Business.TaxIdIsRequiredWithLegalName)

    def test_update_handles_validation_errors_for_funding_fields(self):
        result = MerchantAccount.update("sandbox_sub_merchant_account", {
            "funding": {
                "destination": MerchantAccount.FundingDestination.Bank,
                "routing_number": "",
                "account_number": ""
                }
            }
        )

        self.assertFalse(result.is_success)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("routing_number")[0].code, ErrorCodes.MerchantAccount.Funding.RoutingNumberIsRequired)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("account_number")[0].code, ErrorCodes.MerchantAccount.Funding.AccountNumberIsRequired)

        result = MerchantAccount.update("sandbox_sub_merchant_account", {
            "funding": {
                "destination": MerchantAccount.FundingDestination.Email,
                "email": ""
                }
            }
        )

        self.assertFalse(result.is_success)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("email")[0].code, ErrorCodes.MerchantAccount.Funding.EmailAddressIsRequired)

        result = MerchantAccount.update("sandbox_sub_merchant_account", {
            "funding": {
                "destination": MerchantAccount.FundingDestination.MobilePhone,
                "mobile_phone": ""
                }
            }
        )

        self.assertFalse(result.is_success)
        self.assertEquals(result.errors.for_object("merchant_account").for_object("funding").on("mobile_phone")[0].code, ErrorCodes.MerchantAccount.Funding.MobilePhoneIsRequired)

    def test_find(self):
        result = MerchantAccount.create(self.VALID_APPLICATION_PARAMS)
        self.assertTrue(result.is_success)
        merchant_account_id = result.merchant_account.id
        merchant_account = MerchantAccount.find(merchant_account_id)

    def test_find_404(self):
        try:
            MerchantAccount.find("not_a_real_id")
        except NotFoundError:
            pass
        else:
            self.assertTrue(False)

########NEW FILE########
__FILENAME__ = test_plan
from tests.test_helper import *

class TestPlan(unittest.TestCase):

    def test_all_returns_empty_list(self):
        Configuration.configure(
            Environment.Development,
            "test_merchant_id",
            "test_public_key",
            "test_private_key"
        )
        plans = Plan.all()
        self.assertEquals(plans, [])
        Configuration.configure(
            Environment.Development,
            "integration_merchant_id",
            "integration_public_key",
            "integration_private_key"
        )

    def test_all_returns_all_the_plans(self):
        plan_token = str(random.randint(1, 1000000))
        attributes = {
            "id": plan_token,
            "billing_day_of_month": 1,
            "billing_frequency": 1,
            "currency_iso_code": "USD",
            "description": "some description",
            "name": "python test plan",
            "number_of_billing_cycles": 1,
            "price": "1.00",
        }

        Configuration.instantiate().http().post("/plans/create_plan_for_tests", {"plan": attributes})

        add_on_attributes = {
            "amount": "100.00",
            "description": "some description",
            "plan_id": plan_token,
            "kind": "add_on",
            "name": "python_add_on",
            "never_expires": False,
            "number_of_billing_cycles": 1
        }

        Configuration.instantiate().http().post("/modifications/create_modification_for_tests", {"modification": add_on_attributes})
        discount_attributes = {
            "amount": "100.00",
            "description": "some description",
            "plan_id": plan_token,
            "kind": "discount",
            "name": "python_discount",
            "never_expires": False,
            "number_of_billing_cycles": 1
        }

        Configuration.instantiate().http().post("/modifications/create_modification_for_tests", {"modification": discount_attributes})

        plans = Plan.all()

        for plan in plans:
            if plan.id == plan_token:
                actual_plan = plan

        self.assertNotEquals(None, actual_plan)

        self.assertEquals(attributes["billing_day_of_month"], 1)
        self.assertEquals(attributes["billing_frequency"], 1)
        self.assertEquals(attributes["currency_iso_code"], "USD")
        self.assertEquals(attributes["description"], "some description")
        self.assertEquals(attributes["name"], "python test plan")
        self.assertEquals(attributes["number_of_billing_cycles"], 1)
        self.assertEquals(attributes["price"], "1.00")

        self.assertEquals(add_on_attributes["name"], actual_plan.add_ons[0].name)
        self.assertEquals(discount_attributes["name"], actual_plan.discounts[0].name)

########NEW FILE########
__FILENAME__ = test_search
from tests.test_helper import *

class TestSearch(unittest.TestCase):
    def test_text_node_is(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        trial_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trial_plan["id"]
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.plan_id == "integration_trial_plan"
        ])

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertFalse(TestHelper.includes(collection, trialless_subscription))

    def test_text_node_is_not(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        trial_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trial_plan["id"]
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.plan_id != "integration_trialless_plan"
        ])

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertFalse(TestHelper.includes(collection, trialless_subscription))

    def test_text_node_starts_with(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        trial_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trial_plan["id"]
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.plan_id.starts_with("integration_trial_p")
        ])

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertFalse(TestHelper.includes(collection, trialless_subscription))

    def test_text_node_ends_with(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }

        }).customer.credit_cards[0]
        trial_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trial_plan["id"]
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.plan_id.ends_with("trial_plan")
        ])

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertFalse(TestHelper.includes(collection, trialless_subscription))

    def test_text_node_contains(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        trial_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trial_plan["id"]
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.plan_id.contains("rial_pl")
        ])

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertFalse(TestHelper.includes(collection, trialless_subscription))

    def test_multiple_value_node_in_list(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        active_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        canceled_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription
        Subscription.cancel(canceled_subscription.id)

        collection = Subscription.search([
            SubscriptionSearch.status.in_list([Subscription.Status.Active, Subscription.Status.Canceled])
        ])

        self.assertTrue(TestHelper.includes(collection, active_subscription))
        self.assertTrue(TestHelper.includes(collection, canceled_subscription))

    def test_multiple_value_node_in_list_as_arg_list(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        active_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        canceled_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription
        Subscription.cancel(canceled_subscription.id)

        collection = Subscription.search([
            SubscriptionSearch.status.in_list(Subscription.Status.Active, Subscription.Status.Canceled)
        ])

        self.assertTrue(TestHelper.includes(collection, active_subscription))
        self.assertTrue(TestHelper.includes(collection, canceled_subscription))

    def test_multiple_value_node_is(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        active_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        canceled_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription
        Subscription.cancel(canceled_subscription.id)

        collection = Subscription.search([
            SubscriptionSearch.status == Subscription.Status.Active
        ])

        self.assertTrue(TestHelper.includes(collection, active_subscription))
        self.assertFalse(TestHelper.includes(collection, canceled_subscription))

    def test_range_node_min(self):
        name = "Henrietta Livingston%s" % randint(1,100000)
        t_1500 = Transaction.sale({
            "amount": "1500.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        t_1800 = Transaction.sale({
            "amount": "1800.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount >= "1700"
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1800.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount.greater_than_or_equal_to("1700")
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1800.id, collection.first.id)

    def test_range_node_max(self):
        name = "Henrietta Livingston%s" % randint(1,100000)
        t_1500 = Transaction.sale({
            "amount": "1500.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        t_1800 = Transaction.sale({
            "amount": "1800.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount <= "1700"
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1500.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount.less_than_or_equal_to("1700")
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1500.id, collection.first.id)

    def test_range_node_is(self):
        name = "Henrietta Livingston%s" % randint(1,100000)
        t_1500 = Transaction.sale({
            "amount": "1500.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        t_1800 = Transaction.sale({
            "amount": "1800.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount == "1800"
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1800.id, collection.first.id)

    def test_range_node_between(self):
        name = "Henrietta Livingston%s" % randint(1,100000)
        t_1000 = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        t_1500 = Transaction.sale({
            "amount": "1500.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        t_1800 = Transaction.sale({
            "amount": "1800.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount.between("1100", "1600")
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1500.id, collection.first.id)

    def test_search_on_multiple_values(self):
        credit_card = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
            }
        }).customer.credit_cards[0]

        active_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        canceled_subscription = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription
        Subscription.cancel(canceled_subscription.id)

        collection = Subscription.search([
            SubscriptionSearch.plan_id == "integration_trialless_plan",
            SubscriptionSearch.status.in_list([Subscription.Status.Active])
        ])

        self.assertTrue(TestHelper.includes(collection, active_subscription))
        self.assertFalse(TestHelper.includes(collection, canceled_subscription))


########NEW FILE########
__FILENAME__ = test_settlement_batch_summary
from tests.test_helper import *

class TestSettlementBatchSummary(unittest.TestCase):
    def test_generate_returns_empty_collection_if_there_is_no_data(self):
        result = SettlementBatchSummary.generate('2011-01-01')

        self.assertTrue(result.is_success)
        self.assertEquals([], result.settlement_batch_summary.records)

    def test_generate_returns_error_if_date_can_not_be_parsed(self):
        result = SettlementBatchSummary.generate('THIS AINT NO DATE')

        self.assertFalse(result.is_success)
        code = result.errors.for_object('settlement_batch_summary').on('settlement_date')[0].code
        self.assertEquals(ErrorCodes.SettlementBatchSummary.SettlementDateIsInvalid, code)

    def test_generate_returns_transactions_settled_on_a_given_day(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Sergio Ramos"
            },
            "options": {"submit_for_settlement": True}
        })

        self.assertTrue(result.is_success)

        transaction = result.transaction
        TestHelper.settle_transaction(transaction.id)

        result = SettlementBatchSummary.generate(TestHelper.now_in_eastern())
        self.assertTrue(result.is_success)

        visa_records = [row for row in result.settlement_batch_summary.records if row['card_type'] == 'Visa'][0]
        self.assertTrue(int(visa_records['count']) >= 1)
        self.assertTrue(float(visa_records['amount_settled']) >= float(TransactionAmounts.Authorize))

    def test_generate_can_be_grouped_by_a_custom_field(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Sergio Ramos"
            },
            "options": {"submit_for_settlement": True},
            "custom_fields": {
                "store_me": 1
            }
        })

        transaction = result.transaction
        TestHelper.settle_transaction(transaction.id)

        result = SettlementBatchSummary.generate(TestHelper.now_in_eastern(), 'store_me')
        self.assertTrue(result.is_success)

        self.assertTrue('store_me' in result.settlement_batch_summary.records[0])

########NEW FILE########
__FILENAME__ = test_subscription
from tests.test_helper import *

class TestSubscription(unittest.TestCase):
    def setUp(self):
        self.credit_card = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100"
            }
        }).customer.credit_cards[0]

        self.updateable_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "price": Decimal("54.32"),
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription


    def test_create_returns_successful_result_if_valid(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        })

        self.assertTrue(result.is_success)
        subscription = result.subscription
        self.assertNotEquals(None, re.search("\A\w{6}\Z", subscription.id))
        self.assertEquals(Decimal("12.34"), subscription.price)
        self.assertEquals(Decimal("12.34"), subscription.next_bill_amount)
        self.assertEquals(Decimal("12.34"), subscription.next_billing_period_amount)
        self.assertEquals(Subscription.Status.Active, subscription.status)
        self.assertEquals("integration_trialless_plan", subscription.plan_id)
        self.assertEquals(TestHelper.default_merchant_account_id, subscription.merchant_account_id)
        self.assertEquals(Decimal("0.00"), subscription.balance)

        self.assertEquals(date, type(subscription.first_billing_date))
        self.assertEquals(date, type(subscription.next_billing_date))
        self.assertEquals(date, type(subscription.billing_period_start_date))
        self.assertEquals(date, type(subscription.billing_period_end_date))
        self.assertEquals(date, type(subscription.paid_through_date))

        self.assertEquals(1, subscription.current_billing_cycle)
        self.assertEquals(0, subscription.failure_count)
        self.assertEquals(self.credit_card.token, subscription.payment_method_token)

    def test_create_returns_successful_result_with_payment_method_nonce(self):
        config = Configuration.instantiate()
        customer_id = Customer.create().customer.id
        authorization_fingerprint = json.loads(ClientToken.generate({"customer_id": customer_id}))["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })
        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            },
            "share": True
        })
        nonce = json.loads(response)["nonce"]

        result = Subscription.create({
            "payment_method_nonce": nonce,
            "plan_id": TestHelper.trialless_plan["id"]
        })

        self.assertTrue(result.is_success)
        transaction = result.subscription.transactions[0]
        self.assertEqual("411111", transaction.credit_card_details.bin)


    def test_create_can_set_the_id(self):
        new_id = str(random.randint(1, 1000000))
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "id": new_id
        })

        self.assertTrue(result.is_success)
        self.assertEquals(new_id, result.subscription.id)

    def test_create_can_set_the_merchant_account_id(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "merchant_account_id": TestHelper.non_default_merchant_account_id
        })

        self.assertTrue(result.is_success)
        self.assertEquals(TestHelper.non_default_merchant_account_id, result.subscription.merchant_account_id)

    def test_create_defaults_to_plan_without_trial(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription

        self.assertEquals(TestHelper.trialless_plan["trial_period"], subscription.trial_period)
        self.assertEquals(None, subscription.trial_duration)
        self.assertEquals(None, subscription.trial_duration_unit)

    def test_create_defaults_to_plan_with_trial(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
        }).subscription

        self.assertEquals(TestHelper.trial_plan["trial_period"], subscription.trial_period)
        self.assertEquals(TestHelper.trial_plan["trial_duration"], subscription.trial_duration)
        self.assertEquals(TestHelper.trial_plan["trial_duration_unit"], subscription.trial_duration_unit)

    def test_create_and_override_plan_with_trial(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "trial_duration": 5,
            "trial_duration_unit": Subscription.TrialDurationUnit.Month
        }).subscription

        self.assertEquals(True, subscription.trial_period)
        self.assertEquals(5, subscription.trial_duration)
        self.assertEquals(Subscription.TrialDurationUnit.Month, subscription.trial_duration_unit)

    def test_create_and_override_trial_period(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "trial_period": False
        }).subscription

        self.assertEquals(False, subscription.trial_period)

    def test_create_and_override_number_of_billing_cycles(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "number_of_billing_cycles": 10
        }).subscription

        self.assertEquals(10, subscription.number_of_billing_cycles)

    def test_create_and_override_number_of_billing_cycles_to_never_expire(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "never_expires": True
        }).subscription

        self.assertEquals(None, subscription.number_of_billing_cycles)

    def test_create_creates_a_transaction_if_no_trial_period(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription

        self.assertEquals(1, len(subscription.transactions))
        transaction = subscription.transactions[0]
        self.assertEquals(Transaction, type(transaction))
        self.assertEquals(TestHelper.trialless_plan["price"], transaction.amount)
        self.assertEquals("sale", transaction.type)
        self.assertEquals(subscription.id, transaction.subscription_id)

    def test_create_has_transaction_with_billing_period_dates(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription
        transaction = subscription.transactions[0]
        self.assertEquals(subscription.billing_period_start_date, transaction.subscription_details.billing_period_start_date)
        self.assertEquals(subscription.billing_period_end_date, transaction.subscription_details.billing_period_end_date)

    def test_create_returns_a_transaction_if_transaction_is_declined(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "price": TransactionAmounts.Decline
        })

        self.assertFalse(result.is_success)
        self.assertEquals(Transaction.Status.ProcessorDeclined, result.transaction.status)

    def test_create_doesnt_creates_a_transaction_if_trial_period(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
        }).subscription

        self.assertEquals(0, len(subscription.transactions))

    def test_create_with_error_result(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "id": "invalid token"
        })

        self.assertFalse(result.is_success)
        self.assertEquals("81906", result.errors.for_object("subscription").on("id")[0].code)

    def test_create_inherits_billing_day_of_month_from_plan(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.billing_day_of_month_plan["id"],
        })

        self.assertTrue(result.is_success)
        self.assertEquals(5, result.subscription.billing_day_of_month)

    def test_create_allows_overriding_billing_day_of_month(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.billing_day_of_month_plan["id"],
            "billing_day_of_month": 19
        })

        self.assertTrue(result.is_success)
        self.assertEquals(19, result.subscription.billing_day_of_month)

    def test_create_allows_overriding_billing_day_of_month_with_start_immediately(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.billing_day_of_month_plan["id"],
            "options": {
                "start_immediately": True
            }
        })

        self.assertTrue(result.is_success)
        self.assertEquals(1, len(result.subscription.transactions))

    def test_create_allows_specifying_first_billing_date(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.billing_day_of_month_plan["id"],
            "first_billing_date": date.today() + timedelta(days=3)
        })

        self.assertTrue(result.is_success)
        self.assertEquals(date.today() + timedelta(days=3), result.subscription.first_billing_date)
        self.assertEquals(Subscription.Status.Pending, result.subscription.status)

    def test_create_does_not_allow_first_billing_date_in_the_past(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.billing_day_of_month_plan["id"],
            "first_billing_date": date.today() - timedelta(days=3)
        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Subscription.FirstBillingDateCannotBeInThePast,
            result.errors.for_object("subscription").on("first_billing_date")[0].code
        )

    def test_create_does_not_inherit_add_ons_or_discounts_from_the_plan_when_flag_is_set(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
            "options": {
                "do_not_inherit_add_ons_or_discounts": True
            }
        }).subscription

        self.assertEquals(0, len(subscription.add_ons))
        self.assertEquals(0, len(subscription.discounts))

    def test_create_inherits_add_ons_and_discounts_from_the_plan_when_not_specified(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"]
        }).subscription

        self.assertEquals(2, len(subscription.add_ons))
        add_ons = sorted(subscription.add_ons, key=lambda add_on: add_on.id)

        self.assertEquals("increase_10", add_ons[0].id)
        self.assertEquals(Decimal("10.00"), add_ons[0].amount)
        self.assertEquals(1, add_ons[0].quantity)
        self.assertEquals(None, add_ons[0].number_of_billing_cycles)
        self.assertTrue(add_ons[0].never_expires)
        self.assertEquals(0, add_ons[0].current_billing_cycle)

        self.assertEquals("increase_20", add_ons[1].id)
        self.assertEquals(Decimal("20.00"), add_ons[1].amount)
        self.assertEquals(1, add_ons[1].quantity)
        self.assertEquals(None, add_ons[1].number_of_billing_cycles)
        self.assertTrue(add_ons[1].never_expires)
        self.assertEquals(0, add_ons[1].current_billing_cycle)

        self.assertEquals(2, len(subscription.discounts))
        discounts = sorted(subscription.discounts, key=lambda discount: discount.id)

        self.assertEquals("discount_11", discounts[0].id)
        self.assertEquals(Decimal("11.00"), discounts[0].amount)
        self.assertEquals(1, discounts[0].quantity)
        self.assertEquals(None, discounts[0].number_of_billing_cycles)
        self.assertTrue(discounts[0].never_expires)
        self.assertEquals(0, discounts[0].current_billing_cycle)

        self.assertEquals("discount_7", discounts[1].id)
        self.assertEquals(Decimal("7.00"), discounts[1].amount)
        self.assertEquals(1, discounts[1].quantity)
        self.assertEquals(None, discounts[1].number_of_billing_cycles)
        self.assertTrue(discounts[1].never_expires)
        self.assertEquals(0, discounts[1].current_billing_cycle)

    def test_create_allows_overriding_of_inherited_add_ons_and_discounts(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
            "add_ons": {
                "update": [
                    {
                        "amount": Decimal("50.00"),
                        "existing_id": "increase_10",
                        "quantity": 2,
                        "number_of_billing_cycles": 5
                    },
                    {
                        "amount": Decimal("100.00"),
                        "existing_id": "increase_20",
                        "quantity": 4,
                        "never_expires": True
                    }
                ]
            },
            "discounts": {
                "update": [
                    {
                        "amount": Decimal("15.00"),
                        "existing_id": "discount_7",
                        "quantity": 3,
                        "number_of_billing_cycles": 19
                    }
                ]
            }
        }).subscription

        self.assertEquals(2, len(subscription.add_ons))
        add_ons = sorted(subscription.add_ons, key=lambda add_on: add_on.id)

        self.assertEquals("increase_10", add_ons[0].id)
        self.assertEquals(Decimal("50.00"), add_ons[0].amount)
        self.assertEquals(2, add_ons[0].quantity)
        self.assertEquals(5, add_ons[0].number_of_billing_cycles)
        self.assertFalse(add_ons[0].never_expires)
        self.assertEquals(0, add_ons[0].current_billing_cycle)

        self.assertEquals("increase_20", add_ons[1].id)
        self.assertEquals(Decimal("100.00"), add_ons[1].amount)
        self.assertEquals(4, add_ons[1].quantity)
        self.assertEquals(None, add_ons[1].number_of_billing_cycles)
        self.assertTrue(add_ons[1].never_expires)
        self.assertEquals(0, add_ons[1].current_billing_cycle)

        self.assertEquals(2, len(subscription.discounts))
        discounts = sorted(subscription.discounts, key=lambda discount: discount.id)

        self.assertEquals("discount_11", discounts[0].id)
        self.assertEquals(Decimal("11.00"), discounts[0].amount)
        self.assertEquals(1, discounts[0].quantity)
        self.assertEquals(None, discounts[0].number_of_billing_cycles)
        self.assertTrue(discounts[0].never_expires)
        self.assertEquals(0, discounts[0].current_billing_cycle)

        self.assertEquals("discount_7", discounts[1].id)
        self.assertEquals(Decimal("15.00"), discounts[1].amount)
        self.assertEquals(3, discounts[1].quantity)
        self.assertEquals(19, discounts[1].number_of_billing_cycles)
        self.assertFalse(discounts[1].never_expires)
        self.assertEquals(0, discounts[1].current_billing_cycle)

    def test_create_allows_deleting_of_inherited_add_ons_and_discounts(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
            "add_ons": {
                "remove": ["increase_10", "increase_20"]
            },
            "discounts": {
                "remove": ["discount_7"]
            }
        }).subscription

        self.assertEquals(0, len(subscription.add_ons))
        self.assertEquals(1, len(subscription.discounts))
        self.assertEquals("discount_11", subscription.discounts[0].id)

    def test_create_allows_adding_add_ons_and_discounts(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
            "add_ons": {
                "add": [
                    {
                        "amount": Decimal("50.00"),
                        "inherited_from_id": "increase_30",
                        "quantity": 2,
                        "number_of_billing_cycles": 5
                    }
                ],
                "remove": ["increase_10", "increase_20"]
            },
            "discounts": {
                "add": [
                    {
                        "amount": Decimal("17.00"),
                        "inherited_from_id": "discount_15",
                        "never_expires": True
                    }
                ],
                "remove": ["discount_7", "discount_11"]
            }
        }).subscription

        self.assertEquals(1, len(subscription.add_ons))

        self.assertEquals("increase_30", subscription.add_ons[0].id)
        self.assertEquals(Decimal("50.00"), subscription.add_ons[0].amount)
        self.assertEquals(2, subscription.add_ons[0].quantity)
        self.assertEquals(5, subscription.add_ons[0].number_of_billing_cycles)
        self.assertFalse(subscription.add_ons[0].never_expires)
        self.assertEquals(0, subscription.add_ons[0].current_billing_cycle)

        self.assertEquals(1, len(subscription.discounts))

        self.assertEquals("discount_15", subscription.discounts[0].id)
        self.assertEquals(Decimal("17.00"), subscription.discounts[0].amount)
        self.assertEquals(1, subscription.discounts[0].quantity)
        self.assertEquals(None, subscription.discounts[0].number_of_billing_cycles)
        self.assertTrue(subscription.discounts[0].never_expires)
        self.assertEquals(0, subscription.discounts[0].current_billing_cycle)

    def test_create_properly_parses_validation_errors_for_arrays(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
            "add_ons": {
                "update": [
                    {
                        "existing_id": "increase_10",
                        "amount": "invalid"
                    },
                    {
                        "existing_id": "increase_20",
                        "quantity": -2
                    }
                ]
            }
        })

        self.assertFalse(result.is_success)

        self.assertEquals(
            ErrorCodes.Subscription.Modification.AmountIsInvalid,
            result.errors.for_object("subscription").for_object("add_ons").for_object("update").for_index(0).on("amount")[0].code
        )
        self.assertEquals(
            ErrorCodes.Subscription.Modification.QuantityIsInvalid,
            result.errors.for_object("subscription").for_object("add_ons").for_object("update").for_index(1).on("quantity")[0].code
        )

    def test_descriptors_accepts_name_and_phone(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "descriptor": {
                "name": "123*123456789012345678",
                "phone": "3334445555"
            }
        })

        self.assertTrue(result.is_success)
        subscription = result.subscription
        self.assertEquals("123*123456789012345678", subscription.descriptor.name)
        self.assertEquals("3334445555", subscription.descriptor.phone)

        transaction = subscription.transactions[0]
        self.assertEquals("123*123456789012345678", transaction.descriptor.name)
        self.assertEquals("3334445555", transaction.descriptor.phone)

    def test_descriptors_has_validation_errors_if_format_is_invalid(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "descriptor": {
                "name": "badcompanyname12*badproduct12",
                "phone": "%bad4445555"
            }
        })
        self.assertFalse(result.is_success)
        transaction = result.transaction
        self.assertEquals(
            ErrorCodes.Descriptor.NameFormatIsInvalid,
            result.errors.for_object("transaction").for_object("descriptor").on("name")[0].code
        )
        self.assertEquals(
            ErrorCodes.Descriptor.PhoneFormatIsInvalid,
            result.errors.for_object("transaction").for_object("descriptor").on("phone")[0].code
        )

    def test_find_with_valid_id(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
        }).subscription

        found_subscription = Subscription.find(subscription.id)
        self.assertEquals(subscription.id, found_subscription.id)

    def test_find_with_invalid_token(self):
        try:
            Subscription.find("bad_token")
            self.assertTrue(False)
        except Exception, e:
            self.assertEquals("subscription with id bad_token not found", str(e))

    def test_update_creates_a_prorated_transaction_when_merchant_is_set_to_prorate(self):
        new_id = str(random.randint(1, 1000000))
        result = Subscription.update(self.updateable_subscription.id, {
            "price": self.updateable_subscription.price + Decimal("1"),
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(2, len(subscription.transactions))

    def test_update_creates_a_prorated_transaction_when_flag_is_passed_as_True(self):
        new_id = str(random.randint(1, 1000000))
        result = Subscription.update(self.updateable_subscription.id, {
            "price": self.updateable_subscription.price + Decimal("1"),
            "options": {
                "prorate_charges": True
            }
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(2, len(subscription.transactions))

    def test_update_does_not_create_a_prorated_transaction_when_flag_is_passed_as_False(self):
        new_id = str(random.randint(1, 1000000))
        result = Subscription.update(self.updateable_subscription.id, {
            "price": self.updateable_subscription.price + Decimal("1"),
            "options": {
                "prorate_charges": False
            }
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(1, len(subscription.transactions))

    def test_update_does_not_update_subscription_when_revert_subscription_on_proration_failure_is_true(self):
        new_id = str(random.randint(1, 1000000))
        result = Subscription.update(self.updateable_subscription.id, {
            "price": self.updateable_subscription.price + Decimal("2100"),
            "options": {
                "prorate_charges": True,
                "revert_subscription_on_proration_failure": True
            }
        })

        self.assertFalse(result.is_success)

        found_subscription = Subscription.find(result.subscription.id)
        self.assertEquals(len(self.updateable_subscription.transactions) + 1, len(result.subscription.transactions))
        self.assertEqual("processor_declined", result.subscription.transactions[0].status)

        self.assertEqual(Decimal("0.00"), found_subscription.balance)
        self.assertEquals(self.updateable_subscription.price, found_subscription.price)

    def test_update_updates_subscription_when_revert_subscription_on_proration_failure_is_false(self):
        new_id = str(random.randint(1, 1000000))
        result = Subscription.update(self.updateable_subscription.id, {
            "price": self.updateable_subscription.price + Decimal("2100"),
            "options": {
                "prorate_charges": True,
                "revert_subscription_on_proration_failure": False
            }
        })

        self.assertTrue(result.is_success)

        found_subscription = Subscription.find(result.subscription.id)
        self.assertEquals(len(self.updateable_subscription.transactions) + 1, len(result.subscription.transactions))
        self.assertEqual("processor_declined", result.subscription.transactions[0].status)

        self.assertEqual(result.subscription.transactions[0].amount, Decimal(found_subscription.balance))
        self.assertEquals(self.updateable_subscription.price + Decimal("2100"), found_subscription.price)

    def test_update_with_successful_result(self):
        new_id = str(random.randint(1, 1000000))
        result = Subscription.update(self.updateable_subscription.id, {
            "id": new_id,
            "price": Decimal("9999.88"),
            "plan_id": TestHelper.trial_plan["id"]
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(new_id, subscription.id)
        self.assertEquals(TestHelper.trial_plan["id"], subscription.plan_id)
        self.assertEquals(Decimal("9999.88"), subscription.price)

    def test_update_with_merchant_account_id(self):
        result = Subscription.update(self.updateable_subscription.id, {
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(TestHelper.non_default_merchant_account_id, subscription.merchant_account_id)

    def test_update_with_payment_method_token(self):
        newCard = CreditCard.create({
            "customer_id": self.credit_card.customer_id,
            "number": "4111111111111111",
            "expiration_date": "05/2009",
            "cvv": "100",
            "cardholder_name": self.credit_card.cardholder_name
        }).credit_card

        result = Subscription.update(self.updateable_subscription.id, {
            "payment_method_token": newCard.token
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(newCard.token, subscription.payment_method_token)

    def test_update_with_payment_method_nonce(self):
        config = Configuration.instantiate()
        customer_id = self.credit_card.customer_id
        authorization_fingerprint = json.loads(ClientToken.generate({"customer_id": customer_id}))["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })
        status_code, response = http.add_card({
            "credit_card": {
                "number": "4242424242424242",
                "expiration_month": "11",
                "expiration_year": "2099",
            },
            "share": True
        })
        nonce = json.loads(response)["nonce"]

        result = Subscription.update(self.updateable_subscription.id, {
            "payment_method_nonce": nonce
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        newCard = CreditCard.find(subscription.payment_method_token)
        self.assertEquals("4242", newCard.last_4)
        self.assertNotEquals(newCard.last_4, self.credit_card.last_4)

    def test_update_with_number_of_billing_cycles(self):
        result = Subscription.update(self.updateable_subscription.id, {
            "number_of_billing_cycles": 10
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(10, subscription.number_of_billing_cycles)

    def test_update_with_never_expires(self):
        result = Subscription.update(self.updateable_subscription.id, {
            "never_expires": True
        })

        self.assertTrue(result.is_success)

        subscription = result.subscription
        self.assertEquals(None, subscription.number_of_billing_cycles)

    def test_update_with_error_result(self):
        result = Subscription.update(self.updateable_subscription.id, {
            "id": "bad id",
        })

        self.assertFalse(result.is_success)
        self.assertEquals("81906", result.errors.for_object("subscription").on("id")[0].code)

    @raises(NotFoundError)
    def test_update_raises_error_when_subscription_not_found(self):
        Subscription.update("notfound", {
            "id": "newid",
        })

    def test_update_allows_overriding_of_inherited_add_ons_and_discounts(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
        }).subscription

        subscription = Subscription.update(subscription.id, {
            "add_ons": {
                "update": [
                    {
                        "amount": Decimal("50.00"),
                        "existing_id": "increase_10",
                        "quantity": 2,
                        "number_of_billing_cycles": 5
                    },
                    {
                        "amount": Decimal("100.00"),
                        "existing_id": "increase_20",
                        "quantity": 4,
                        "never_expires": True
                    }
                ]
            },
            "discounts": {
                "update": [
                    {
                        "amount": Decimal("15.00"),
                        "existing_id": "discount_7",
                        "quantity": 3,
                        "number_of_billing_cycles": 19
                    }
                ]
            }
        }).subscription

        self.assertEquals(2, len(subscription.add_ons))
        add_ons = sorted(subscription.add_ons, key=lambda add_on: add_on.id)

        self.assertEquals("increase_10", add_ons[0].id)
        self.assertEquals(Decimal("50.00"), add_ons[0].amount)
        self.assertEquals(2, add_ons[0].quantity)
        self.assertEquals(5, add_ons[0].number_of_billing_cycles)
        self.assertFalse(add_ons[0].never_expires)

        self.assertEquals("increase_20", add_ons[1].id)
        self.assertEquals(Decimal("100.00"), add_ons[1].amount)
        self.assertEquals(4, add_ons[1].quantity)
        self.assertEquals(None, add_ons[1].number_of_billing_cycles)
        self.assertTrue(add_ons[1].never_expires)

        self.assertEquals(2, len(subscription.discounts))
        discounts = sorted(subscription.discounts, key=lambda discount: discount.id)

        self.assertEquals("discount_11", discounts[0].id)
        self.assertEquals(Decimal("11.00"), discounts[0].amount)
        self.assertEquals(1, discounts[0].quantity)
        self.assertEquals(None, discounts[0].number_of_billing_cycles)
        self.assertTrue(discounts[0].never_expires)

        self.assertEquals("discount_7", discounts[1].id)
        self.assertEquals(Decimal("15.00"), discounts[1].amount)
        self.assertEquals(3, discounts[1].quantity)
        self.assertEquals(19, discounts[1].number_of_billing_cycles)
        self.assertFalse(discounts[1].never_expires)

    def test_update_allows_adding_and_removing_add_ons_and_discounts(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
        }).subscription

        subscription = Subscription.update(subscription.id, {
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
            "add_ons": {
                "add": [
                    {
                        "amount": Decimal("50.00"),
                        "inherited_from_id": "increase_30",
                        "quantity": 2,
                        "number_of_billing_cycles": 5
                    }
                ],
                "remove": ["increase_10", "increase_20"]
            },
            "discounts": {
                "add": [
                    {
                        "amount": Decimal("17.00"),
                        "inherited_from_id": "discount_15",
                        "never_expires": True
                    }
                ],
                "remove": ["discount_7", "discount_11"]
            }
        }).subscription

        self.assertEquals(1, len(subscription.add_ons))

        self.assertEquals("increase_30", subscription.add_ons[0].id)
        self.assertEquals(Decimal("50.00"), subscription.add_ons[0].amount)
        self.assertEquals(2, subscription.add_ons[0].quantity)
        self.assertEquals(5, subscription.add_ons[0].number_of_billing_cycles)
        self.assertFalse(subscription.add_ons[0].never_expires)

        self.assertEquals(1, len(subscription.discounts))

        self.assertEquals("discount_15", subscription.discounts[0].id)
        self.assertEquals(Decimal("17.00"), subscription.discounts[0].amount)
        self.assertEquals(1, subscription.discounts[0].quantity)
        self.assertEquals(None, subscription.discounts[0].number_of_billing_cycles)
        self.assertTrue(subscription.discounts[0].never_expires)

    def test_update_can_replace_entire_set_of_add_ons_and_discounts(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
        }).subscription

        subscription = Subscription.update(subscription.id, {
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.add_on_discount_plan["id"],
            "add_ons": {
                "add": [
                    { "inherited_from_id": "increase_30", },
                    { "inherited_from_id": "increase_20", }
                ]
            },
            "discounts": {
                "add": [
                    { "inherited_from_id": "discount_15", }
                ]
            },
            "options": {
                "replace_all_add_ons_and_discounts": True
            }
        }).subscription

        self.assertEquals(2, len(subscription.add_ons))
        add_ons = sorted(subscription.add_ons, key=lambda add_on: add_on.id)

        self.assertEquals("increase_20", add_ons[0].id)
        self.assertEquals(Decimal("20.00"), add_ons[0].amount)
        self.assertEquals(1, add_ons[0].quantity)
        self.assertEquals(None, add_ons[0].number_of_billing_cycles)
        self.assertTrue(add_ons[0].never_expires)

        self.assertEquals("increase_30", add_ons[1].id)
        self.assertEquals(Decimal("30.00"), add_ons[1].amount)
        self.assertEquals(1, add_ons[1].quantity)
        self.assertEquals(None, add_ons[1].number_of_billing_cycles)
        self.assertTrue(add_ons[1].never_expires)

        self.assertEquals(1, len(subscription.discounts))

        self.assertEquals("discount_15", subscription.discounts[0].id)
        self.assertEquals(Decimal("15.00"), subscription.discounts[0].amount)
        self.assertEquals(1, subscription.discounts[0].quantity)
        self.assertEquals(None, subscription.discounts[0].number_of_billing_cycles)
        self.assertTrue(subscription.discounts[0].never_expires)

    def test_update_descriptor_name_and_phone(self):
        result = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "descriptor": {
                "name": "123*123456789012345678",
                "phone": "1234567890"
            }
        })

        self.assertTrue(result.is_success)
        subscription = result.subscription
        updated_subscription = Subscription.update(subscription.id, {
            "descriptor": {
                "name": "999*99",
                "phone": "1234567890"
            }
        }).subscription

        self.assertEquals("999*99", updated_subscription.descriptor.name)
        self.assertEquals("1234567890", updated_subscription.descriptor.phone)

    def test_cancel_with_successful_response(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        result = Subscription.cancel(subscription.id)
        self.assertTrue(result.is_success)
        self.assertEqual("Canceled", result.subscription.status)

    def test_unsuccessful_cancel_returns_validation_error(self):
        Subscription.cancel(self.updateable_subscription.id)
        result = Subscription.cancel(self.updateable_subscription.id)

        self.assertFalse(result.is_success)
        self.assertEquals("81905", result.errors.for_object("subscription").on("status")[0].code)

    @raises(NotFoundError)
    def test_cancel_raises_not_found_error_with_bad_subscription(self):
        Subscription.cancel("notreal")

    def test_search_with_argument_list_rather_than_literal_list(self):
        trial_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("1")
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "price": Decimal("1")
        }).subscription

        collection = Subscription.search(
            SubscriptionSearch.plan_id == "integration_trial_plan",
            SubscriptionSearch.price == Decimal("1")
        )

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertFalse(TestHelper.includes(collection, trialless_subscription))

    def test_search_on_billing_cycles_remaining(self):
        subscription_5 = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "number_of_billing_cycles": 5
        }).subscription

        subscription_10 = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "number_of_billing_cycles": 10
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.billing_cycles_remaining >= 7
        ])

        self.assertTrue(TestHelper.includes(collection, subscription_10))
        self.assertFalse(TestHelper.includes(collection, subscription_5))

    def test_search_on_days_past_due(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription
        TestHelper.make_past_due(subscription, 3)

        collection = Subscription.search([
            SubscriptionSearch.days_past_due.between(2, 10)
        ])

        self.assertTrue(collection.maximum_size > 0)
        for subscription in collection.items:
            self.assertTrue(2 <= subscription.days_past_due <= 10)

    def test_search_on_plan_id(self):
        trial_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("2")
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "price": Decimal("2")
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.plan_id == "integration_trial_plan",
            SubscriptionSearch.price == Decimal("2")
        ])

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertFalse(TestHelper.includes(collection, trialless_subscription))

        collection = Subscription.search([
            SubscriptionSearch.plan_id.in_list("integration_trial_plan", "integration_trialless_plan"),
            SubscriptionSearch.price == Decimal("2")
        ])

        self.assertTrue(TestHelper.includes(collection, trial_subscription))
        self.assertTrue(TestHelper.includes(collection, trialless_subscription))

    def test_search_on_plan_id_is_acts_like_text_node_instead_of_multiple_value(self):
        trial_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("3")
        }).subscription

        trialless_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "price": Decimal("3")
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.plan_id == "no such plan id",
            SubscriptionSearch.price == Decimal("3")
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_search_on_status(self):
        active_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "price": Decimal("3")
        }).subscription

        canceled_subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "price": Decimal("3")
        }).subscription
        Subscription.cancel(canceled_subscription.id)

        collection = Subscription.search([
            SubscriptionSearch.status.in_list([Subscription.Status.Active, Subscription.Status.Canceled]),
            SubscriptionSearch.price == Decimal("3")
        ])

        self.assertTrue(TestHelper.includes(collection, active_subscription))
        self.assertTrue(TestHelper.includes(collection, canceled_subscription))

    def test_search_on_merchant_account_id(self):
        subscription_default_ma = Subscription.create({
            "merchant_account_id": TestHelper.default_merchant_account_id,
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("4")
        }).subscription

        subscription_non_default_ma = Subscription.create({
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("4")
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.merchant_account_id == TestHelper.default_merchant_account_id,
            SubscriptionSearch.price == Decimal("4")
        ])

        self.assertTrue(TestHelper.includes(collection, subscription_default_ma))
        self.assertFalse(TestHelper.includes(collection, subscription_non_default_ma))

    def test_search_on_bogus_merchant_account_id(self):
        subscription = Subscription.create({
            "merchant_account_id": TestHelper.default_merchant_account_id,
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("4")
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.merchant_account_id == subscription.merchant_account_id,
            SubscriptionSearch.price == Decimal("4")
        ])

        self.assertTrue(TestHelper.includes(collection, subscription))

        collection = Subscription.search([
            SubscriptionSearch.merchant_account_id.in_list(["totally_bogus_id", subscription.merchant_account_id]),
            SubscriptionSearch.price == Decimal("4")
        ])

        self.assertTrue(TestHelper.includes(collection, subscription))

        collection = Subscription.search([
            SubscriptionSearch.merchant_account_id == "totally_bogus_id",
            SubscriptionSearch.price == Decimal("4")
        ])

        self.assertFalse(TestHelper.includes(collection, subscription))

    def test_search_on_price(self):
        subscription_900 = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("900")
        }).subscription

        subscription_1000 = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
            "price": Decimal("1000")
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.price >= Decimal("950")
        ])

        self.assertTrue(TestHelper.includes(collection, subscription_1000))
        self.assertFalse(TestHelper.includes(collection, subscription_900))

    def test_search_on_transaction_id(self):
        subscription_found = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription

        subscription_not_found = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription

        collection = Subscription.search(
            SubscriptionSearch.transaction_id == subscription_found.transactions[0].id
        )

        self.assertTrue(TestHelper.includes(collection, subscription_found))
        self.assertFalse(TestHelper.includes(collection, subscription_not_found))

    def test_search_on_id(self):
        subscription_found = Subscription.create({
            "id": "find_me_%s" % random.randint(1,1000000),
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
        }).subscription

        subscription_not_found = Subscription.create({
            "id": "do_not_find_me_%s" % random.randint(1,1000000),
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"],
        }).subscription

        collection = Subscription.search([
            SubscriptionSearch.id.starts_with("find_me")
        ])

        self.assertTrue(TestHelper.includes(collection, subscription_found))
        self.assertFalse(TestHelper.includes(collection, subscription_not_found))

    def test_search_on_next_billing_date(self):
        subscription_found = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"]
        }).subscription

        subscription_not_found = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trial_plan["id"]
        }).subscription

        next_billing_date_cutoff = datetime.today() + timedelta(days=5)

        collection = Subscription.search(
            SubscriptionSearch.next_billing_date >= next_billing_date_cutoff
        )

        self.assertTrue(TestHelper.includes(collection, subscription_found))
        self.assertFalse(TestHelper.includes(collection, subscription_not_found))

    def test_retryCharge_without_amount__deprecated(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription
        TestHelper.make_past_due(subscription)

        result = Subscription.retryCharge(subscription.id);

        self.assertTrue(result.is_success);
        transaction = result.transaction;

        self.assertEquals(subscription.price, transaction.amount);
        self.assertNotEqual(None, transaction.processor_authorization_code);
        self.assertEquals(Transaction.Type.Sale, transaction.type);
        self.assertEquals(Transaction.Status.Authorized, transaction.status);

    def test_retry_charge_without_amount(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription
        TestHelper.make_past_due(subscription)

        result = Subscription.retry_charge(subscription.id);

        self.assertTrue(result.is_success);
        transaction = result.transaction;

        self.assertEquals(subscription.price, transaction.amount);
        self.assertNotEqual(None, transaction.processor_authorization_code);
        self.assertEquals(Transaction.Type.Sale, transaction.type);
        self.assertEquals(Transaction.Status.Authorized, transaction.status);

    def test_retryCharge_with_amount__deprecated(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription
        TestHelper.make_past_due(subscription)

        result = Subscription.retryCharge(subscription.id, Decimal(TransactionAmounts.Authorize));

        self.assertTrue(result.is_success);
        transaction = result.transaction;

        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount);
        self.assertNotEqual(None, transaction.processor_authorization_code);
        self.assertEquals(Transaction.Type.Sale, transaction.type);
        self.assertEquals(Transaction.Status.Authorized, transaction.status);


    def test_retry_charge_with_amount(self):
        subscription = Subscription.create({
            "payment_method_token": self.credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
        }).subscription
        TestHelper.make_past_due(subscription)

        result = Subscription.retry_charge(subscription.id, Decimal(TransactionAmounts.Authorize));

        self.assertTrue(result.is_success);
        transaction = result.transaction;

        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount);
        self.assertNotEqual(None, transaction.processor_authorization_code);
        self.assertEquals(Transaction.Type.Sale, transaction.type);
        self.assertEquals(Transaction.Status.Authorized, transaction.status);


########NEW FILE########
__FILENAME__ = test_transaction
import json
from tests.test_helper import *
from braintree.test.credit_card_numbers import CreditCardNumbers
from braintree.dispute import Dispute
import braintree.test.venmo_sdk as venmo_sdk

class TestTransaction(unittest.TestCase):
    def test_sale_returns_a_successful_result_with_type_of_sale(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEqual(None, re.search("\A\w{6}\Z", transaction.id))
        self.assertEquals(Transaction.Type.Sale, transaction.type)
        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount)
        self.assertEquals("411111", transaction.credit_card_details.bin)
        self.assertEquals("1111", transaction.credit_card_details.last_4)
        self.assertEquals("05/2009", transaction.credit_card_details.expiration_date)
        self.assertEquals(None, transaction.voice_referral_number)

    def test_sale_allows_amount_as_a_decimal(self):
        result = Transaction.sale({
            "amount": Decimal(TransactionAmounts.Authorize),
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEqual(None, re.search("\A\w{6}\Z", transaction.id))
        self.assertEquals(Transaction.Type.Sale, transaction.type)
        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount)
        self.assertEquals("411111", transaction.credit_card_details.bin)
        self.assertEquals("1111", transaction.credit_card_details.last_4)
        self.assertEquals("05/2009", transaction.credit_card_details.expiration_date)

    def test_sale_with_expiration_month_and_year_separately(self):
        result = Transaction.sale({
            "amount": Decimal(TransactionAmounts.Authorize),
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "05",
                "expiration_year": "2012"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(Transaction.Type.Sale, transaction.type)
        self.assertEquals("05", transaction.credit_card_details.expiration_month)
        self.assertEquals("2012", transaction.credit_card_details.expiration_year)

    def test_sale_works_with_all_attributes(self):
        result = Transaction.sale({
            "amount": "100.00",
            "order_id": "123",
            "channel": "MyShoppingCartProvider",
            "credit_card": {
                "cardholder_name": "The Cardholder",
                "number": "5105105105105100",
                "expiration_date": "05/2011",
                "cvv": "123"
            },
            "customer": {
                "first_name": "Dan",
                "last_name": "Smith",
                "company": "Braintree",
                "email": "dan@example.com",
                "phone": "419-555-1234",
                "fax": "419-555-1235",
                "website": "http://braintreepayments.com"
            },
            "billing": {
                "first_name": "Carl",
                "last_name": "Jones",
                "company": "Braintree",
                "street_address": "123 E Main St",
                "extended_address": "Suite 403",
                "locality": "Chicago",
                "region": "IL",
                "postal_code": "60622",
                "country_name": "United States of America",
                "country_code_alpha2": "US",
                "country_code_alpha3": "USA",
                "country_code_numeric": "840"
            },
            "shipping": {
                "first_name": "Andrew",
                "last_name": "Mason",
                "company": "Braintree",
                "street_address": "456 W Main St",
                "extended_address": "Apt 2F",
                "locality": "Bartlett",
                "region": "IL",
                "postal_code": "60103",
                "country_name": "Mexico",
                "country_code_alpha2": "MX",
                "country_code_alpha3": "MEX",
                "country_code_numeric": "484"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEquals(None, re.search("\A\w{6}\Z", transaction.id))
        self.assertEquals(Transaction.Type.Sale, transaction.type)
        self.assertEquals(Transaction.Status.Authorized, transaction.status)
        self.assertEquals(Decimal("100.00"), transaction.amount)
        self.assertEquals("123", transaction.order_id)
        self.assertEquals("MyShoppingCartProvider", transaction.channel)
        self.assertEquals("1000", transaction.processor_response_code)
        self.assertEquals(datetime, type(transaction.created_at))
        self.assertEquals(datetime, type(transaction.updated_at))
        self.assertEquals("510510", transaction.credit_card_details.bin)
        self.assertEquals("5100", transaction.credit_card_details.last_4)
        self.assertEquals("510510******5100", transaction.credit_card_details.masked_number)
        self.assertEquals("MasterCard", transaction.credit_card_details.card_type)
        self.assertEquals("The Cardholder", transaction.credit_card_details.cardholder_name)
        self.assertEquals(None, transaction.avs_error_response_code)
        self.assertEquals("M", transaction.avs_postal_code_response_code)
        self.assertEquals("M", transaction.avs_street_address_response_code)
        self.assertEquals("Dan", transaction.customer_details.first_name)
        self.assertEquals("Smith", transaction.customer_details.last_name)
        self.assertEquals("Braintree", transaction.customer_details.company)
        self.assertEquals("dan@example.com", transaction.customer_details.email)
        self.assertEquals("419-555-1234", transaction.customer_details.phone)
        self.assertEquals("419-555-1235", transaction.customer_details.fax)
        self.assertEquals("http://braintreepayments.com", transaction.customer_details.website)
        self.assertEquals("Carl", transaction.billing_details.first_name)
        self.assertEquals("Jones", transaction.billing_details.last_name)
        self.assertEquals("Braintree", transaction.billing_details.company)
        self.assertEquals("123 E Main St", transaction.billing_details.street_address)
        self.assertEquals("Suite 403", transaction.billing_details.extended_address)
        self.assertEquals("Chicago", transaction.billing_details.locality)
        self.assertEquals("IL", transaction.billing_details.region)
        self.assertEquals("60622", transaction.billing_details.postal_code)
        self.assertEquals("United States of America", transaction.billing_details.country_name)
        self.assertEquals("US", transaction.billing_details.country_code_alpha2)
        self.assertEquals("USA", transaction.billing_details.country_code_alpha3)
        self.assertEquals("840", transaction.billing_details.country_code_numeric)
        self.assertEquals("Andrew", transaction.shipping_details.first_name)
        self.assertEquals("Mason", transaction.shipping_details.last_name)
        self.assertEquals("Braintree", transaction.shipping_details.company)
        self.assertEquals("456 W Main St", transaction.shipping_details.street_address)
        self.assertEquals("Apt 2F", transaction.shipping_details.extended_address)
        self.assertEquals("Bartlett", transaction.shipping_details.locality)
        self.assertEquals("IL", transaction.shipping_details.region)
        self.assertEquals("60103", transaction.shipping_details.postal_code)
        self.assertEquals("Mexico", transaction.shipping_details.country_name)
        self.assertEquals("MX", transaction.shipping_details.country_code_alpha2)
        self.assertEquals("MEX", transaction.shipping_details.country_code_alpha3)
        self.assertEquals("484", transaction.shipping_details.country_code_numeric)

    def test_sale_with_vault_customer_and_credit_card_data(self):
        customer = Customer.create({
            "first_name": "Pingu",
            "last_name": "Penguin",
        }).customer

        result = Transaction.sale({
            "amount": Decimal(TransactionAmounts.Authorize),
            "customer_id": customer.id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(transaction.credit_card_details.masked_number, "411111******1111")
        self.assertEquals(None, transaction.vault_credit_card)

    def test_sale_with_vault_customer_and_credit_card_data_and_store_in_vault(self):
        customer = Customer.create({
            "first_name": "Pingu",
            "last_name": "Penguin",
        }).customer

        result = Transaction.sale({
            "amount": Decimal(TransactionAmounts.Authorize),
            "customer_id": customer.id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "store_in_vault": True
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals("411111******1111", transaction.credit_card_details.masked_number)
        self.assertEquals("411111******1111", transaction.vault_credit_card.masked_number)

    def test_sale_with_custom_fields(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "custom_fields": {
                "store_me": "some extra stuff"
            }

        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals("some extra stuff", transaction.custom_fields["store_me"])

    def test_sale_with_merchant_account_id(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(TestHelper.non_default_merchant_account_id, transaction.merchant_account_id)

    def test_sale_without_merchant_account_id_falls_back_to_default(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(TestHelper.default_merchant_account_id, transaction.merchant_account_id)

    def test_sale_with_shipping_address_id(self):
        result = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010"
            }
        })
        self.assertTrue(result.is_success)
        customer = result.customer

        result = Address.create({
            "customer_id": customer.id,
            "street_address": "123 Fake St."
        })
        self.assertTrue(result.is_success)
        address = result.address

        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "customer_id": customer.id,
            "shipping_address_id": address.id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals("123 Fake St.", transaction.shipping_details.street_address)
        self.assertEquals(address.id, transaction.shipping_details.id)

    def test_sale_with_billing_address_id(self):
        result = Customer.create({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010"
            }
        })
        self.assertTrue(result.is_success)
        customer = result.customer

        result = Address.create({
            "customer_id": customer.id,
            "street_address": "123 Fake St."
        })
        self.assertTrue(result.is_success)
        address = result.address

        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "customer_id": customer.id,
            "billing_address_id": address.id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals("123 Fake St.", transaction.billing_details.street_address)
        self.assertEquals(address.id, transaction.billing_details.id)

    def test_sale_with_device_session_id_and_fraud_merchant_id(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010"
            },
            "device_session_id": "abc123",
            "fraud_merchant_id": "456"
        })

        self.assertTrue(result.is_success)


    def test_sale_with_level_2(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "purchase_order_number": "12345",
            "tax_amount": Decimal("10.00"),
            "tax_exempt": True,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals("12345", transaction.purchase_order_number)
        self.assertEquals(Decimal("10.00"), transaction.tax_amount)
        self.assertEquals(True, transaction.tax_exempt)

    def test_create_with_invalid_tax_amount(self):
        result = Transaction.sale({
            "amount": Decimal("100"),
            "tax_amount": "asdf",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.TaxAmountFormatIsInvalid,
            result.errors.for_object("transaction").on("tax_amount")[0].code
        )

    def test_create_with_too_long_purchase_order_number(self):
        result = Transaction.sale({
            "amount": Decimal("100"),
            "purchase_order_number": "aaaaaaaaaaaaaaaaaa",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.PurchaseOrderNumberIsTooLong,
            result.errors.for_object("transaction").on("purchase_order_number")[0].code
        )

    def test_create_with_invalid_purchase_order_number(self):
        result = Transaction.sale({
            "amount": Decimal("100"),
            "purchase_order_number": "\xc3\x9f\xc3\xa5\xe2\x88\x82",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.PurchaseOrderNumberIsInvalid,
            result.errors.for_object("transaction").on("purchase_order_number")[0].code
        )

    def test_sale_with_processor_declined(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Decline,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertFalse(result.is_success)
        transaction = result.transaction
        self.assertEquals(Transaction.Status.ProcessorDeclined, transaction.status)

    def test_sale_with_gateway_rejected_with_avs(self):
        old_merchant_id = Configuration.merchant_id
        old_public_key = Configuration.public_key
        old_private_key = Configuration.private_key

        try:
            Configuration.merchant_id = "processing_rules_merchant_id"
            Configuration.public_key = "processing_rules_public_key"
            Configuration.private_key = "processing_rules_private_key"

            result = Transaction.sale({
                "amount": TransactionAmounts.Authorize,
                "billing": {
                    "street_address": "200 Fake Street"
                },
                "credit_card": {
                    "number": "4111111111111111",
                    "expiration_date": "05/2009"
                }
            })

            self.assertFalse(result.is_success)
            transaction = result.transaction
            self.assertEquals(Transaction.GatewayRejectionReason.Avs, transaction.gateway_rejection_reason)
        finally:
            Configuration.merchant_id = old_merchant_id
            Configuration.public_key = old_public_key
            Configuration.private_key = old_private_key

    def test_sale_with_gateway_rejected_with_avs_and_cvv(self):
        old_merchant_id = Configuration.merchant_id
        old_public_key = Configuration.public_key
        old_private_key = Configuration.private_key

        try:
            Configuration.merchant_id = "processing_rules_merchant_id"
            Configuration.public_key = "processing_rules_public_key"
            Configuration.private_key = "processing_rules_private_key"

            result = Transaction.sale({
                "amount": TransactionAmounts.Authorize,
                "billing": {
                    "postal_code": "20000"
                },
                "credit_card": {
                    "number": "4111111111111111",
                    "expiration_date": "05/2009",
                    "cvv": "200"
                }
            })

            self.assertFalse(result.is_success)
            transaction = result.transaction
            self.assertEquals(Transaction.GatewayRejectionReason.AvsAndCvv, transaction.gateway_rejection_reason)
        finally:
            Configuration.merchant_id = old_merchant_id
            Configuration.public_key = old_public_key
            Configuration.private_key = old_private_key

    def test_sale_with_gateway_rejected_with_cvv(self):
        old_merchant_id = Configuration.merchant_id
        old_public_key = Configuration.public_key
        old_private_key = Configuration.private_key

        try:
            Configuration.merchant_id = "processing_rules_merchant_id"
            Configuration.public_key = "processing_rules_public_key"
            Configuration.private_key = "processing_rules_private_key"

            result = Transaction.sale({
                "amount": TransactionAmounts.Authorize,
                "credit_card": {
                    "number": "4111111111111111",
                    "expiration_date": "05/2009",
                    "cvv": "200"
                }
            })

            self.assertFalse(result.is_success)
            transaction = result.transaction
            self.assertEquals(Transaction.GatewayRejectionReason.Cvv, transaction.gateway_rejection_reason)
        finally:
            Configuration.merchant_id = old_merchant_id
            Configuration.public_key = old_public_key
            Configuration.private_key = old_private_key

    def test_sale_with_gateway_rejected_with_fraud(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4000111111111511",
                "expiration_date": "05/2017",
                "cvv": "333"
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(Transaction.GatewayRejectionReason.Fraud, result.transaction.gateway_rejection_reason)

    def test_sale_with_service_fee(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_sub_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "service_fee_amount": "1.00"
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEqual(transaction.service_fee_amount, "1.00")

    def test_sale_on_master_merchant_accoount_is_invalid_with_service_fee(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "service_fee_amount": "1.00"
        })
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.ServiceFeeAmountNotAllowedOnMasterMerchantAccount,
            result.errors.for_object("transaction").on("service_fee_amount")[0].code
        )

    def test_sale_on_submerchant_is_invalid_without_with_service_fee(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_sub_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.SubMerchantAccountRequiresServiceFeeAmount,
            result.errors.for_object("transaction").on("merchant_account_id")[0].code
        )

    def test_sale_with_hold_in_escrow_option(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_sub_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "hold_in_escrow": True
            },
            "service_fee_amount": "1.00"
        })
        self.assertTrue(result.is_success)
        self.assertEquals(
            Transaction.EscrowStatus.HoldPending,
            result.transaction.escrow_status
        )

    def test_sale_with_hold_in_escrow_option_fails_for_master_merchant_account(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "hold_in_escrow": True
            }
        })
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.CannotHoldInEscrow,
            result.errors.for_object("transaction").on("base")[0].code
        )

    def test_hold_in_escrow_after_sale(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_sub_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "service_fee_amount": "1.00"
        })
        self.assertTrue(result.is_success)
        result = Transaction.hold_in_escrow(result.transaction.id)
        self.assertTrue(result.is_success)
        self.assertEquals(
            Transaction.EscrowStatus.HoldPending,
            result.transaction.escrow_status
        )

    def test_hold_in_escrow_after_sale_fails_for_master_merchant_account(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })
        self.assertTrue(result.is_success)
        result = Transaction.hold_in_escrow(result.transaction.id)
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.CannotHoldInEscrow,
            result.errors.for_object("transaction").on("base")[0].code
        )

    def test_release_from_escrow_from_escrow(self):
        transaction = self.__create_escrowed_transaction()
        result = Transaction.release_from_escrow(transaction.id)
        self.assertTrue(result.is_success)
        self.assertEquals(
            Transaction.EscrowStatus.ReleasePending,
            result.transaction.escrow_status
        )


    def test_release_from_escrow_from_escrow_fails_when_transaction_not_in_escrow(self):
        result = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })
        self.assertTrue(result.is_success)
        result = Transaction.release_from_escrow(result.transaction.id)
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.CannotReleaseFromEscrow,
            result.errors.for_object("transaction").on("base")[0].code
        )

    def test_cancel_release_from_escrow(self):
        transaction = self.__create_escrowed_transaction()
        submit_result = Transaction.release_from_escrow(transaction.id)
        result = Transaction.cancel_release(submit_result.transaction.id)
        self.assertTrue(result.is_success)
        self.assertEquals(
                Transaction.EscrowStatus.Held,
                result.transaction.escrow_status
        )

    def test_cancel_release_from_escrow_fails_if_transaction_is_not_pending_release(self):
        transaction = self.__create_escrowed_transaction()
        result = Transaction.cancel_release(transaction.id)
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.CannotCancelRelease,
            result.errors.for_object("transaction").on("base")[0].code
        )

    def test_sale_with_venmo_sdk_session(self):
        result = Transaction.sale({
            "amount": "10.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "venmo_sdk_session": venmo_sdk.Session
            }
        })

        self.assertTrue(result.is_success)
        self.assertTrue(result.transaction.credit_card_details.venmo_sdk)

    def test_sale_with_venmo_sdk_payment_method_code(self):
        result = Transaction.sale({
            "amount": "10.00",
            "venmo_sdk_payment_method_code": venmo_sdk.VisaPaymentMethodCode
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEqual("411111", transaction.credit_card_details.bin)

    def test_sale_with_payment_method_nonce(self):
        config = Configuration.instantiate()
        authorization_fingerprint = json.loads(ClientToken.generate())["authorizationFingerprint"]
        http = ClientApiHttp(config, {
            "authorization_fingerprint": authorization_fingerprint,
            "shared_customer_identifier": "fake_identifier",
            "shared_customer_identifier_type": "testing"
        })
        status_code, response = http.add_card({
            "credit_card": {
                "number": "4111111111111111",
                "expiration_month": "11",
                "expiration_year": "2099",
            },
            "share": True
        })
        nonce = json.loads(response)["nonce"]


        result = Transaction.sale({
            "amount": "10.00",
            "payment_method_nonce": nonce
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEqual("411111", transaction.credit_card_details.bin)

    def test_validation_error_on_invalid_custom_fields(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "custom_fields": {
                "invalid_key": "some extra stuff"
            }

        })

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.CustomFieldIsInvalid,
            result.errors.for_object("transaction").on("custom_fields")[0].code
        )

    def test_card_type_indicators(self):
        result = Transaction.sale({
            "amount": Decimal(TransactionAmounts.Authorize),
            "credit_card": {
                "number": CreditCardNumbers.CardTypeIndicators.Unknown,
                "expiration_month": "05",
                "expiration_year": "2012"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(CreditCard.Prepaid.Unknown, transaction.credit_card_details.prepaid)
        self.assertEquals(CreditCard.Debit.Unknown, transaction.credit_card_details.debit)
        self.assertEquals(CreditCard.Commercial.Unknown, transaction.credit_card_details.commercial)
        self.assertEquals(CreditCard.Healthcare.Unknown, transaction.credit_card_details.healthcare)
        self.assertEquals(CreditCard.Payroll.Unknown, transaction.credit_card_details.payroll)
        self.assertEquals(CreditCard.DurbinRegulated.Unknown, transaction.credit_card_details.durbin_regulated)
        self.assertEquals(CreditCard.CardTypeIndicator.Unknown, transaction.credit_card_details.issuing_bank)
        self.assertEquals(CreditCard.CardTypeIndicator.Unknown, transaction.credit_card_details.country_of_issuance)

    def test_create_can_set_recurring_flag(self):
        result = Transaction.sale({
            "amount": "100",
            "customer": {
                "first_name": "Adam",
                "last_name": "Williams"
            },
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "recurring": True
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(True, transaction.recurring)

    def test_create_can_store_customer_and_credit_card_in_the_vault(self):
        result = Transaction.sale({
            "amount": "100",
            "customer": {
                "first_name": "Adam",
                "last_name": "Williams"
            },
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "store_in_vault": True
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEqual(None, re.search("\A\d{6,7}\Z", transaction.customer_details.id))
        self.assertEquals(transaction.customer_details.id, transaction.vault_customer.id)
        self.assertNotEqual(None, re.search("\A\w{4,5}\Z", transaction.credit_card_details.token))
        self.assertEquals(transaction.credit_card_details.token, transaction.vault_credit_card.token)

    def test_create_can_store_customer_and_credit_card_in_the_vault_on_success(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "customer": {
                "first_name": "Adam",
                "last_name": "Williams"
            },
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "store_in_vault_on_success": True
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEqual(None, re.search("\A\d{6,7}\Z", transaction.customer_details.id))
        self.assertEquals(transaction.customer_details.id, transaction.vault_customer.id)
        self.assertNotEqual(None, re.search("\A\w{4,5}\Z", transaction.credit_card_details.token))
        self.assertEquals(transaction.credit_card_details.token, transaction.vault_credit_card.token)

    def test_create_does_not_store_customer_and_credit_card_in_the_vault_on_failure(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Decline,
            "customer": {
                "first_name": "Adam",
                "last_name": "Williams"
            },
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "store_in_vault_on_success": True
            }
        })

        self.assertFalse(result.is_success)
        transaction = result.transaction
        self.assertEqual(None, transaction.customer_details.id)
        self.assertEqual(None, transaction.credit_card_details.token)
        self.assertEqual(None, transaction.vault_customer)
        self.assertEqual(None, transaction.vault_credit_card)

    def test_create_associated_a_billing_address_with_credit_card_in_vault(self):
        result = Transaction.sale({
            "amount": "100",
            "customer": {
                "first_name": "Adam",
                "last_name": "Williams"
            },
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2012"
            },
            "billing": {
                "first_name": "Carl",
                "last_name": "Jones",
                "company": "Braintree",
                "street_address": "123 E Main St",
                "extended_address": "Suite 403",
                "locality": "Chicago",
                "region": "IL",
                "postal_code": "60622",
                "country_name": "United States of America"
            },
            "options": {
                "store_in_vault": True,
                "add_billing_address_to_payment_method": True,
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEquals(None, re.search("\A\d{6,7}\Z", transaction.customer_details.id))
        self.assertEquals(transaction.customer_details.id, transaction.vault_customer.id)
        credit_card = CreditCard.find(transaction.vault_credit_card.token)
        self.assertEquals(credit_card.billing_address.id, transaction.billing_details.id)
        self.assertEquals(credit_card.billing_address.id, transaction.vault_billing_address.id)
        self.assertEquals("Carl", credit_card.billing_address.first_name)
        self.assertEquals("Jones", credit_card.billing_address.last_name)
        self.assertEquals("Braintree", credit_card.billing_address.company)
        self.assertEquals("123 E Main St", credit_card.billing_address.street_address)
        self.assertEquals("Suite 403", credit_card.billing_address.extended_address)
        self.assertEquals("Chicago", credit_card.billing_address.locality)
        self.assertEquals("IL", credit_card.billing_address.region)
        self.assertEquals("60622", credit_card.billing_address.postal_code)
        self.assertEquals("United States of America", credit_card.billing_address.country_name)

    def test_create_and_store_the_shipping_address_in_the_vault(self):
        result = Transaction.sale({
            "amount": "100",
            "customer": {
                "first_name": "Adam",
                "last_name": "Williams"
            },
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2012"
            },
            "shipping": {
                "first_name": "Carl",
                "last_name": "Jones",
                "company": "Braintree",
                "street_address": "123 E Main St",
                "extended_address": "Suite 403",
                "locality": "Chicago",
                "region": "IL",
                "postal_code": "60622",
                "country_name": "United States of America"
            },
            "options": {
                "store_in_vault": True,
                "store_shipping_address_in_vault": True,
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEquals(None, re.search("\A\d{6,7}\Z", transaction.customer_details.id))
        self.assertEquals(transaction.customer_details.id, transaction.vault_customer.id)
        shipping_address = transaction.vault_customer.addresses[0]
        self.assertEquals("Carl", shipping_address.first_name)
        self.assertEquals("Jones", shipping_address.last_name)
        self.assertEquals("Braintree", shipping_address.company)
        self.assertEquals("123 E Main St", shipping_address.street_address)
        self.assertEquals("Suite 403", shipping_address.extended_address)
        self.assertEquals("Chicago", shipping_address.locality)
        self.assertEquals("IL", shipping_address.region)
        self.assertEquals("60622", shipping_address.postal_code)
        self.assertEquals("United States of America", shipping_address.country_name)

    def test_create_submits_for_settlement_if_given_submit_for_settlement_option(self):
        result = Transaction.sale({
            "amount": "100",
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2012"
            },
            "options": {
                "submit_for_settlement": True
            }
        })

        self.assertTrue(result.is_success)
        self.assertEquals(Transaction.Status.SubmittedForSettlement, result.transaction.status)

    def test_create_does_not_submit_for_settlement_if_submit_for_settlement_is_false(self):
        result = Transaction.sale({
            "amount": "100",
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2012"
            },
            "options": {
                "submit_for_settlement": False
            }
        })

        self.assertTrue(result.is_success)
        self.assertEquals(Transaction.Status.Authorized, result.transaction.status)

    def test_create_can_specify_the_customer_id_and_payment_method_token(self):
        customer_id = "customer_" + str(random.randint(1, 1000000))
        payment_method_token = "credit_card_" + str(random.randint(1, 1000000))

        result = Transaction.sale({
            "amount": "100",
            "customer": {
              "id": customer_id,
              "first_name": "Adam",
              "last_name": "Williams"
            },
            "credit_card": {
              "token": payment_method_token,
              "number": "5105105105105100",
              "expiration_date": "05/2012"
            },
            "options": {
              "store_in_vault": True
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(customer_id, transaction.customer_details.id)
        self.assertEquals(customer_id, transaction.vault_customer.id)
        self.assertEquals(payment_method_token, transaction.credit_card_details.token)
        self.assertEquals(payment_method_token, transaction.vault_credit_card.token)

    def test_create_using_customer_id(self):
        result = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100"
            }
        })
        self.assertTrue(result.is_success)
        customer = result.customer
        credit_card = customer.credit_cards[0]

        result = Transaction.sale({
            "amount": "100",
            "customer_id": customer.id
        })
        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(customer.id, transaction.customer_details.id)
        self.assertEquals(customer.id, transaction.vault_customer.id)
        self.assertEquals(credit_card.token, transaction.credit_card_details.token)
        self.assertEquals(credit_card.token, transaction.vault_credit_card.token)

    def test_create_using_payment_method_token(self):
        result = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100"
            }
        })
        self.assertTrue(result.is_success)
        customer = result.customer
        credit_card = customer.credit_cards[0]

        result = Transaction.sale({
            "amount": "100",
            "payment_method_token": credit_card.token
        })
        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(customer.id, transaction.customer_details.id)
        self.assertEquals(customer.id, transaction.vault_customer.id)
        self.assertEquals(credit_card.token, transaction.credit_card_details.token)
        self.assertEquals(credit_card.token, transaction.vault_credit_card.token)

    def test_create_using_payment_method_token_with_cvv(self):
        result = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100"
            }
        })
        self.assertTrue(result.is_success)
        customer = result.customer
        credit_card = customer.credit_cards[0]

        result = Transaction.sale({
            "amount": "100",
            "payment_method_token": credit_card.token,
            "credit_card": {
                "cvv": "301"
            }
        })
        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(customer.id, transaction.customer_details.id)
        self.assertEquals(customer.id, transaction.vault_customer.id)
        self.assertEquals(credit_card.token, transaction.credit_card_details.token)
        self.assertEquals(credit_card.token, transaction.vault_credit_card.token)
        self.assertEquals("S", transaction.cvv_response_code)

    def test_create_with_failing_validations(self):
        params = {
            "transaction": {
                "amount": None,
                "credit_card": {
                    "number": "4111111111111111",
                    "expiration_date": "05/2009"
                }
            }
        }
        result = Transaction.sale(params["transaction"])
        params["transaction"]["credit_card"].pop("number")
        self.assertFalse(result.is_success)
        self.assertEquals(params, result.params)
        self.assertEquals(
            ErrorCodes.Transaction.AmountIsRequired,
            result.errors.for_object("transaction").on("amount")[0].code
        )

    def test_credit_with_a_successful_result(self):
        result = Transaction.credit({
            "amount": Decimal(TransactionAmounts.Authorize),
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertNotEquals(None, re.search("\A\w{6}\Z", transaction.id))
        self.assertEquals(Transaction.Type.Credit, transaction.type)
        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount)
        cc_details = transaction.credit_card_details
        self.assertEquals("411111", cc_details.bin)
        self.assertEquals("1111", cc_details.last_4)
        self.assertEquals("05/2009", cc_details.expiration_date)

    def test_credit_with_unsuccessful_result(self):
        result = Transaction.credit({
            "amount": None,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        params = {
            "transaction": {
                "type": Transaction.Type.Credit,
                "amount": None,
                "credit_card": {
                    "expiration_date": "05/2009"
                }
            }
        }

        self.assertFalse(result.is_success)
        self.assertEquals(params, result.params)
        self.assertEquals(
            ErrorCodes.Transaction.AmountIsRequired,
            result.errors.for_object("transaction").on("amount")[0].code
        )

    def test_service_fee_not_allowed_with_credits(self):
        result = Transaction.credit({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "service_fee_amount": "1.00"
        })

        self.assertFalse(result.is_success)
        self.assertTrue(
            ErrorCodes.Transaction.ServiceFeeIsNotAllowedOnCredits in [error.code for error in result.errors.for_object("transaction").on("base")]
        )

    def test_credit_with_merchant_account_id(self):
        result = Transaction.credit({
            "amount": TransactionAmounts.Authorize,
            "merchant_account_id": TestHelper.non_default_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(TestHelper.non_default_merchant_account_id, transaction.merchant_account_id)

    def test_credit_without_merchant_account_id_falls_back_to_default(self):
        result = Transaction.credit({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(TestHelper.default_merchant_account_id, transaction.merchant_account_id)

    def test_find_returns_a_found_transaction(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        }).transaction
        found_transaction = Transaction.find(transaction.id)
        self.assertEquals(transaction.id, found_transaction.id)

    def test_find_for_bad_transaction_raises_not_found_error(self):
        try:
            Transaction.find("notreal")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertEquals("transaction with id notreal not found", str(e))

    def test_void_with_successful_result(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        }).transaction

        result = Transaction.void(transaction.id)
        self.assertTrue(result.is_success)
        self.assertEquals(transaction.id, result.transaction.id)
        self.assertEquals(Transaction.Status.Voided, result.transaction.status)

    def test_void_with_unsuccessful_result(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Decline,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        }).transaction

        result = Transaction.void(transaction.id)
        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.CannotBeVoided,
            result.errors.for_object("transaction").on("base")[0].code
        )

    def test_create_with_successful_result(self):
        result = Transaction.create({
            "type": Transaction.Type.Sale,
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals(Transaction.Type.Sale, transaction.type)

    def test_create_with_error_result(self):
        result = Transaction.create({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "billing": {
                "country_code_alpha2": "ZZ",
                "country_code_alpha3": "ZZZ",
                "country_code_numeric": "000",
                "country_name": "zzzzzz"
            }
        })

        self.assertFalse(result.is_success)
        self.assertEquals(ErrorCodes.Transaction.TypeIsRequired, result.errors.for_object("transaction").on("type")[0].code)
        self.assertEquals(
            ErrorCodes.Address.CountryCodeAlpha2IsNotAccepted,
            result.errors.for_object("transaction").for_object("billing").on("country_code_alpha2")[0].code
        )
        self.assertEquals(
            ErrorCodes.Address.CountryCodeAlpha3IsNotAccepted,
            result.errors.for_object("transaction").for_object("billing").on("country_code_alpha3")[0].code
        )
        self.assertEquals(
            ErrorCodes.Address.CountryCodeNumericIsNotAccepted,
            result.errors.for_object("transaction").for_object("billing").on("country_code_numeric")[0].code
        )
        self.assertEquals(
            ErrorCodes.Address.CountryNameIsNotAccepted,
            result.errors.for_object("transaction").for_object("billing").on("country_name")[0].code
        )

    def test_sale_from_transparent_redirect_with_successful_result(self):
        tr_data = {
            "transaction": {
                "amount": TransactionAmounts.Authorize,
            }
        }
        post_params = {
            "tr_data": Transaction.tr_data_for_sale(tr_data, "http://example.com/path"),
            "transaction[credit_card][number]": "4111111111111111",
            "transaction[credit_card][expiration_date]": "05/2010",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Transaction.transparent_redirect_create_url())
        result = Transaction.confirm_transparent_redirect(query_string)
        self.assertTrue(result.is_success)

        transaction = result.transaction
        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount)
        self.assertEquals(Transaction.Type.Sale, transaction.type)
        self.assertEquals("411111", transaction.credit_card_details.bin)
        self.assertEquals("1111", transaction.credit_card_details.last_4)
        self.assertEquals("05/2010", transaction.credit_card_details.expiration_date)

    def test_sale_from_transparent_redirect_with_error_result(self):
        tr_data = {
            "transaction": {
                "amount": TransactionAmounts.Authorize,
            }
        }
        post_params = {
            "tr_data": Transaction.tr_data_for_sale(tr_data, "http://example.com/path"),
            "transaction[credit_card][number]": "booya",
            "transaction[credit_card][expiration_date]": "05/2010",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Transaction.transparent_redirect_create_url())
        result = Transaction.confirm_transparent_redirect(query_string)
        self.assertFalse(result.is_success)
        self.assertTrue(len(result.errors.for_object("transaction").for_object("credit_card").on("number")) > 0)

    def test_sale_from_transparent_redirect_with_403_and_message(self):
        tr_data = {
            "transaction": {
                "amount": TransactionAmounts.Authorize
            }
        }
        post_params = {
            "tr_data": Transaction.tr_data_for_sale(tr_data, "http://example.com/path"),
            "transaction[credit_card][number]": "booya",
            "transaction[credit_card][expiration_date]": "05/2010",
            "transaction[bad]": "value"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Transaction.transparent_redirect_create_url())
        try:
            result = Transaction.confirm_transparent_redirect(query_string)
            self.fail()
        except AuthorizationError, e:
            self.assertEquals("Invalid params: transaction[bad]", e.message)

    def test_credit_from_transparent_redirect_with_successful_result(self):
        tr_data = {
            "transaction": {
                "amount": TransactionAmounts.Authorize,
            }
        }
        post_params = {
            "tr_data": Transaction.tr_data_for_credit(tr_data, "http://example.com/path"),
            "transaction[credit_card][number]": "4111111111111111",
            "transaction[credit_card][expiration_date]": "05/2010",
            "transaction[billing][country_code_alpha2]": "US",
            "transaction[billing][country_code_alpha3]": "USA",
            "transaction[billing][country_code_numeric]": "840",
            "transaction[billing][country_name]": "United States of America"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Transaction.transparent_redirect_create_url())
        result = Transaction.confirm_transparent_redirect(query_string)
        self.assertTrue(result.is_success)

        transaction = result.transaction
        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount)
        self.assertEquals(Transaction.Type.Credit, transaction.type)
        self.assertEquals("411111", transaction.credit_card_details.bin)
        self.assertEquals("1111", transaction.credit_card_details.last_4)
        self.assertEquals("05/2010", transaction.credit_card_details.expiration_date)

        self.assertEquals("US", transaction.billing_details.country_code_alpha2)
        self.assertEquals("USA", transaction.billing_details.country_code_alpha3)
        self.assertEquals("840", transaction.billing_details.country_code_numeric)
        self.assertEquals("United States of America", transaction.billing_details.country_name)

    def test_credit_from_transparent_redirect_with_error_result(self):
        tr_data = {
            "transaction": {
                "amount": TransactionAmounts.Authorize,
            }
        }
        post_params = {
            "tr_data": Transaction.tr_data_for_credit(tr_data, "http://example.com/path"),
            "transaction[credit_card][number]": "booya",
            "transaction[credit_card][expiration_date]": "05/2010",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Transaction.transparent_redirect_create_url())
        result = Transaction.confirm_transparent_redirect(query_string)
        self.assertFalse(result.is_success)
        self.assertTrue(len(result.errors.for_object("transaction").for_object("credit_card").on("number")) > 0)

    def test_submit_for_settlement_without_amount(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        }).transaction

        submitted_transaction = Transaction.submit_for_settlement(transaction.id).transaction

        self.assertEquals(Transaction.Status.SubmittedForSettlement, submitted_transaction.status)
        self.assertEquals(Decimal(TransactionAmounts.Authorize), submitted_transaction.amount)

    def test_submit_for_settlement_with_amount(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        }).transaction

        submitted_transaction = Transaction.submit_for_settlement(transaction.id, Decimal("900")).transaction

        self.assertEquals(Transaction.Status.SubmittedForSettlement, submitted_transaction.status)
        self.assertEquals(Decimal("900.00"), submitted_transaction.amount)

    def test_submit_for_settlement_with_validation_error(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        }).transaction

        result = Transaction.submit_for_settlement(transaction.id, Decimal("1200"))
        self.assertFalse(result.is_success)

        self.assertEquals(
            ErrorCodes.Transaction.SettlementAmountIsTooLarge,
            result.errors.for_object("transaction").on("amount")[0].code
        )

    def test_submit_for_settlement_with_validation_error_on_service_fee(self):
        transaction = Transaction.sale({
            "amount": "10.00",
            "merchant_account_id": TestHelper.non_default_sub_merchant_account_id,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "service_fee_amount": "5.00"
        }).transaction

        result = Transaction.submit_for_settlement(transaction.id, "1.00")

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.SettlementAmountIsLessThanServiceFeeAmount,
            result.errors.for_object("transaction").on("amount")[0].code
        )

    def test_status_history(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            }
        }).transaction

        submitted_transaction = Transaction.submit_for_settlement(transaction.id).transaction

        self.assertEquals(2, len(submitted_transaction.status_history))
        self.assertEquals(Transaction.Status.Authorized, submitted_transaction.status_history[0].status)
        self.assertEquals(Decimal(TransactionAmounts.Authorize), submitted_transaction.status_history[0].amount)
        self.assertEquals(Transaction.Status.SubmittedForSettlement, submitted_transaction.status_history[1].status)
        self.assertEquals(Decimal(TransactionAmounts.Authorize), submitted_transaction.status_history[1].amount)

    def test_successful_refund(self):
        transaction = self.__create_transaction_to_refund()

        result = Transaction.refund(transaction.id)

        self.assertTrue(result.is_success)
        refund = result.transaction

        self.assertEquals(Transaction.Type.Credit, refund.type)
        self.assertEquals(Decimal(TransactionAmounts.Authorize), refund.amount)
        self.assertEquals(transaction.id, refund.refunded_transaction_id)

        self.assertEquals(refund.id, Transaction.find(transaction.id).refund_id)

    def test_successful_partial_refund(self):
        transaction = self.__create_transaction_to_refund()

        result = Transaction.refund(transaction.id, Decimal("500.00"))

        self.assertTrue(result.is_success)
        self.assertEquals(Transaction.Type.Credit, result.transaction.type)
        self.assertEquals(Decimal("500.00"), result.transaction.amount)

    def test_multiple_successful_partial_refunds(self):
        transaction = self.__create_transaction_to_refund()

        refund1 = Transaction.refund(transaction.id, Decimal("500.00")).transaction
        self.assertEquals(Transaction.Type.Credit, refund1.type)
        self.assertEquals(Decimal("500.00"), refund1.amount)

        refund2 = Transaction.refund(transaction.id, Decimal("500.00")).transaction
        self.assertEquals(Transaction.Type.Credit, refund2.type)
        self.assertEquals(Decimal("500.00"), refund2.amount)

        transaction = Transaction.find(transaction.id)

        self.assertEquals(2, len(transaction.refund_ids))
        self.assertTrue(TestHelper.in_list(transaction.refund_ids, refund1.id))
        self.assertTrue(TestHelper.in_list(transaction.refund_ids, refund2.id))

    def test_refund_already_refunded_transation_fails(self):
        transaction = self.__create_transaction_to_refund()

        Transaction.refund(transaction.id)
        result = Transaction.refund(transaction.id)

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.HasAlreadyBeenRefunded,
            result.errors.for_object("transaction").on("base")[0].code
        )

    def test_refund_returns_an_error_if_unsettled(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "submit_for_settlement": True
            }
        }).transaction

        result = Transaction.refund(transaction.id)

        self.assertFalse(result.is_success)
        self.assertEquals(
            ErrorCodes.Transaction.CannotRefundUnlessSettled,
            result.errors.for_object("transaction").on("base")[0].code
        )

    def __create_transaction_to_refund(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "options": {
                "submit_for_settlement": True
            }
        }).transaction

        TestHelper.settle_transaction(transaction.id)
        return transaction

    def __create_escrowed_transaction(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            },
            "service_fee_amount": "10.00",
            "merchant_account_id": TestHelper.non_default_sub_merchant_account_id,
            "options": {
                "hold_in_escrow": True
            }
        }).transaction

        TestHelper.escrow_transaction(transaction.id)
        return transaction

    def test_snapshot_plan_id_add_ons_and_discounts_from_subscription(self):
        credit_card = Customer.create({
            "first_name": "Mike",
            "last_name": "Jones",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2010",
                "cvv": "100"
            }
        }).customer.credit_cards[0]

        result = Subscription.create({
            "payment_method_token": credit_card.token,
            "plan_id": TestHelper.trialless_plan["id"],
            "add_ons": {
                "add": [
                    {
                        "amount": Decimal("11.00"),
                        "inherited_from_id": "increase_10",
                        "quantity": 2,
                        "number_of_billing_cycles": 5
                    },
                    {
                        "amount": Decimal("21.00"),
                        "inherited_from_id": "increase_20",
                        "quantity": 3,
                        "number_of_billing_cycles": 6
                    }
                ]
            },
            "discounts": {
                "add": [
                    {
                        "amount": Decimal("7.50"),
                        "inherited_from_id": "discount_7",
                        "quantity": 2,
                        "never_expires": True
                    }
                ]
            }
        })

        transaction = result.subscription.transactions[0]

        self.assertEquals(TestHelper.trialless_plan["id"], transaction.plan_id)

        self.assertEquals(2, len(transaction.add_ons))
        add_ons = sorted(transaction.add_ons, key=lambda add_on: add_on.id)

        self.assertEquals("increase_10", add_ons[0].id)
        self.assertEquals(Decimal("11.00"), add_ons[0].amount)
        self.assertEquals(2, add_ons[0].quantity)
        self.assertEquals(5, add_ons[0].number_of_billing_cycles)
        self.assertFalse(add_ons[0].never_expires)

        self.assertEquals("increase_20", add_ons[1].id)
        self.assertEquals(Decimal("21.00"), add_ons[1].amount)
        self.assertEquals(3, add_ons[1].quantity)
        self.assertEquals(6, add_ons[1].number_of_billing_cycles)
        self.assertFalse(add_ons[1].never_expires)

        self.assertEquals(1, len(transaction.discounts))
        discounts = transaction.discounts

        self.assertEquals("discount_7", discounts[0].id)
        self.assertEquals(Decimal("7.50"), discounts[0].amount)
        self.assertEquals(2, discounts[0].quantity)
        self.assertEquals(None, discounts[0].number_of_billing_cycles)
        self.assertTrue(discounts[0].never_expires)

    def test_descriptors_accepts_name_and_phone(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "descriptor": {
                "name": "123*123456789012345678",
                "phone": "3334445555"
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction
        self.assertEquals("123*123456789012345678", transaction.descriptor.name)
        self.assertEquals("3334445555", transaction.descriptor.phone)

    def test_descriptors_has_validation_errors_if_format_is_invalid(self):
        result = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009"
            },
            "descriptor": {
                "name": "badcompanyname12*badproduct12",
                "phone": "%bad4445555"
            }
        })
        self.assertFalse(result.is_success)
        transaction = result.transaction
        self.assertEquals(
            ErrorCodes.Descriptor.NameFormatIsInvalid,
            result.errors.for_object("transaction").for_object("descriptor").on("name")[0].code
        )
        self.assertEquals(
            ErrorCodes.Descriptor.PhoneFormatIsInvalid,
            result.errors.for_object("transaction").for_object("descriptor").on("phone")[0].code
        )

    def test_clone_transaction(self):
        result = Transaction.sale({
            "amount": "100.00",
            "order_id": "123",
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2011",
            },
            "customer": {
                "first_name": "Dan",
            },
            "billing": {
                "first_name": "Carl",
            },
            "shipping": {
                "first_name": "Andrew",
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction

        clone_result = Transaction.clone_transaction(
                transaction.id,
                {
                    "amount": "123.45",
                    "channel": "MyShoppingCartProvider",
                    "options": {"submit_for_settlement": "false"}
                })
        self.assertTrue(clone_result.is_success)
        clone_transaction = clone_result.transaction

        self.assertNotEquals(transaction.id, clone_transaction.id)

        self.assertEquals(Transaction.Type.Sale, clone_transaction.type)
        self.assertEquals(Transaction.Status.Authorized, clone_transaction.status)
        self.assertEquals(Decimal("123.45"), clone_transaction.amount)
        self.assertEquals("MyShoppingCartProvider", clone_transaction.channel)
        self.assertEquals("123", clone_transaction.order_id)
        self.assertEquals("510510******5100", clone_transaction.credit_card_details.masked_number)
        self.assertEquals("Dan", clone_transaction.customer_details.first_name)
        self.assertEquals("Carl", clone_transaction.billing_details.first_name)
        self.assertEquals("Andrew", clone_transaction.shipping_details.first_name)

    def test_clone_transaction_submits_for_settlement(self):
        result = Transaction.sale({
            "amount": "100.00",
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2011",
            }
        })
        self.assertTrue(result.is_success)
        transaction = result.transaction

        clone_result = Transaction.clone_transaction(transaction.id, {"amount": "123.45", "options": {"submit_for_settlement": "true"}})
        self.assertTrue(clone_result.is_success)
        clone_transaction = clone_result.transaction

        self.assertEquals(Transaction.Type.Sale, clone_transaction.type)
        self.assertEquals(Transaction.Status.SubmittedForSettlement, clone_transaction.status)

    def test_clone_transaction_with_validations(self):
        result = Transaction.credit({
            "amount": "100.00",
            "credit_card": {
                "number": "5105105105105100",
                "expiration_date": "05/2011",
            }
        })

        self.assertTrue(result.is_success)
        transaction = result.transaction

        clone_result = Transaction.clone_transaction(transaction.id, {"amount": "123.45"})
        self.assertFalse(clone_result.is_success)

        self.assertEquals(
            ErrorCodes.Transaction.CannotCloneCredit,
            clone_result.errors.for_object("transaction").on("base")[0].code
        )

    def test_find_exposes_disbursement_details(self):
        transaction = Transaction.find("deposittransaction")
        disbursement_details = transaction.disbursement_details

        self.assertEquals(date(2013, 4, 10), disbursement_details.disbursement_date)
        self.assertEquals("USD", disbursement_details.settlement_currency_iso_code)
        self.assertEquals(Decimal("1"), disbursement_details.settlement_currency_exchange_rate)
        self.assertEquals(False, disbursement_details.funds_held)
        self.assertEquals(True, disbursement_details.success)
        self.assertEquals(Decimal("100.00"), disbursement_details.settlement_amount)

    def test_find_exposes_disputes(self):
        transaction = Transaction.find("disputedtransaction")
        dispute = transaction.disputes[0]

        self.assertEquals(date(2014, 3, 1), dispute.received_date)
        self.assertEquals(date(2014, 3, 21), dispute.reply_by_date)
        self.assertEquals("USD", dispute.currency_iso_code)
        self.assertEquals(Decimal("250.00"), dispute.amount)
        self.assertEquals(Dispute.Status.Won, dispute.status)
        self.assertEquals(Dispute.Reason.Fraud, dispute.reason)

########NEW FILE########
__FILENAME__ = test_transaction_search
from tests.test_helper import *

class TestTransactionSearch(unittest.TestCase):
    def test_advanced_search_no_results(self):
        collection = Transaction.search([
            TransactionSearch.billing_first_name == "no_such_person"
        ])
        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_searches_all_text_fields_at_once(self):
        first_name = "Tim%s" % randint(1, 100000)
        token = "creditcard%s" % randint(1, 100000)
        customer_id = "customer%s" % randint(1, 100000)

        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Tom Smith",
                "token": token,
            },
            "billing": {
                "company": "Braintree",
                "country_name": "United States of America",
                "extended_address": "Suite 123",
                "first_name": first_name,
                "last_name": "Smith",
                "locality": "Chicago",
                "postal_code": "12345",
                "region": "IL",
                "street_address": "123 Main St"
            },
            "customer": {
                "company": "Braintree",
                "email": "smith@example.com",
                "fax": "5551231234",
                "first_name": "Tom",
                "id": customer_id,
                "last_name": "Smith",
                "phone": "5551231234",
                "website": "http://example.com",
            },
            "options": {
                "store_in_vault": True,
                "submit_for_settlement": True
            },
            "order_id": "myorder",
            "shipping": {
                "company": "Braintree P.S.",
                "country_name": "Mexico",
                "extended_address": "Apt 456",
                "first_name": "Thomas",
                "last_name": "Smithy",
                "locality": "Braintree",
                "postal_code": "54321",
                "region": "MA",
                "street_address": "456 Road"
            }
        }).transaction

        TestHelper.settle_transaction(transaction.id)
        transaction = Transaction.find(transaction.id)

        collection = Transaction.search([
            TransactionSearch.billing_company == "Braintree",
            TransactionSearch.billing_country_name == "United States of America",
            TransactionSearch.billing_extended_address == "Suite 123",
            TransactionSearch.billing_first_name == first_name,
            TransactionSearch.billing_last_name == "Smith",
            TransactionSearch.billing_locality == "Chicago",
            TransactionSearch.billing_postal_code == "12345",
            TransactionSearch.billing_region == "IL",
            TransactionSearch.billing_street_address == "123 Main St",
            TransactionSearch.credit_card_cardholder_name == "Tom Smith",
            TransactionSearch.credit_card_expiration_date == "05/2012",
            TransactionSearch.credit_card_number == "4111111111111111",
            TransactionSearch.customer_company == "Braintree",
            TransactionSearch.customer_email == "smith@example.com",
            TransactionSearch.customer_fax == "5551231234",
            TransactionSearch.customer_first_name == "Tom",
            TransactionSearch.customer_id == customer_id,
            TransactionSearch.customer_last_name == "Smith",
            TransactionSearch.customer_phone == "5551231234",
            TransactionSearch.customer_website == "http://example.com",
            TransactionSearch.order_id == "myorder",
            TransactionSearch.payment_method_token == token,
            TransactionSearch.processor_authorization_code == transaction.processor_authorization_code,
            TransactionSearch.settlement_batch_id == transaction.settlement_batch_id,
            TransactionSearch.shipping_company == "Braintree P.S.",
            TransactionSearch.shipping_country_name == "Mexico",
            TransactionSearch.shipping_extended_address == "Apt 456",
            TransactionSearch.shipping_first_name == "Thomas",
            TransactionSearch.shipping_last_name == "Smithy",
            TransactionSearch.shipping_locality == "Braintree",
            TransactionSearch.shipping_postal_code == "54321",
            TransactionSearch.shipping_region == "MA",
            TransactionSearch.shipping_street_address == "456 Road",
            TransactionSearch.id == transaction.id
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

    def test_advanced_search_search_each_text_field(self):
        first_name = "Tim%s" % randint(1, 100000)
        token = "creditcard%s" % randint(1, 100000)
        customer_id = "customer%s" % randint(1, 100000)

        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Tom Smith",
                "token": token,
            },
            "billing": {
                "company": "Braintree",
                "country_name": "United States of America",
                "extended_address": "Suite 123",
                "first_name": first_name,
                "last_name": "Smith",
                "locality": "Chicago",
                "postal_code": "12345",
                "region": "IL",
                "street_address": "123 Main St"
            },
            "customer": {
                "company": "Braintree",
                "email": "smith@example.com",
                "fax": "5551231234",
                "first_name": "Tom",
                "id": customer_id,
                "last_name": "Smith",
                "phone": "5551231234",
                "website": "http://example.com",
            },
            "options": {
                "store_in_vault": True
            },
            "order_id": "myorder",
            "shipping": {
                "company": "Braintree P.S.",
                "country_name": "Mexico",
                "extended_address": "Apt 456",
                "first_name": "Thomas",
                "last_name": "Smithy",
                "locality": "Braintree",
                "postal_code": "54321",
                "region": "MA",
                "street_address": "456 Road"
            }
        }).transaction

        search_criteria = {
            "billing_company": "Braintree",
            "billing_country_name": "United States of America",
            "billing_extended_address": "Suite 123",
            "billing_first_name": first_name,
            "billing_last_name": "Smith",
            "billing_locality": "Chicago",
            "billing_postal_code": "12345",
            "billing_region": "IL",
            "billing_street_address": "123 Main St",
            "credit_card_cardholder_name": "Tom Smith",
            "credit_card_expiration_date": "05/2012",
            "credit_card_number": "4111111111111111",
            "customer_company": "Braintree",
            "customer_email": "smith@example.com",
            "customer_fax": "5551231234",
            "customer_first_name": "Tom",
            "customer_id": customer_id,
            "customer_last_name": "Smith",
            "customer_phone": "5551231234",
            "customer_website": "http://example.com",
            "order_id": "myorder",
            "payment_method_token": token,
            "processor_authorization_code": transaction.processor_authorization_code,
            "shipping_company": "Braintree P.S.",
            "shipping_country_name": "Mexico",
            "shipping_extended_address": "Apt 456",
            "shipping_first_name": "Thomas",
            "shipping_last_name": "Smithy",
            "shipping_locality": "Braintree",
            "shipping_postal_code": "54321",
            "shipping_region": "MA",
            "shipping_street_address": "456 Road"
        }

        for criterion, value in search_criteria.iteritems():
            text_node = getattr(TransactionSearch, criterion)

            collection = Transaction.search([
                TransactionSearch.id == transaction.id,
                text_node == value
            ])
            self.assertEquals(1, collection.maximum_size)
            self.assertEquals(transaction.id, collection.first.id)

            collection = Transaction.search([
                TransactionSearch.id == transaction.id,
                text_node == "invalid"
            ])
            self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_with_argument_list_rather_than_literal_list(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Tom Smith",
            },
        }).transaction

        collection = Transaction.search(
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name == "Tom Smith"
        )

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

    def test_advanced_search_text_node_contains(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Jane Shea"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name.contains("ane She")
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name.contains("invalid")
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_text_node_starts_with(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Jane Shea"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name.starts_with("Jane S")
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name.starts_with("invalid")
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_text_node_ends_with(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Jane Shea"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name.ends_with("e Shea")
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name.ends_with("invalid")
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_text_node_is_not(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": "Jane Shea"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name != "invalid"
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_cardholder_name != "Jane Shea"
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_multiple_value_node_created_using(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_using == Transaction.CreatedUsing.FullInformation
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_using.in_list([Transaction.CreatedUsing.FullInformation, Transaction.CreatedUsing.Token])
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_using == Transaction.CreatedUsing.Token
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_multiple_value_node_allowed_values_created_using(self):
        try:
            collection = Transaction.search([
                TransactionSearch.created_using == "noSuchCreatedUsing"
            ])
            self.assertTrue(False)
        except AttributeError, error:
            self.assertEquals("Invalid argument(s) for created_using: noSuchCreatedUsing", str(error))

    def test_advanced_search_multiple_value_node_credit_card_customer_location(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_customer_location == CreditCard.CustomerLocation.US
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_customer_location.in_list([CreditCard.CustomerLocation.US, CreditCard.CustomerLocation.International])
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_customer_location == CreditCard.CustomerLocation.International
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_multiple_value_node_allowed_values_credit_card_customer_location(self):
        try:
            collection = Transaction.search([
                TransactionSearch.credit_card_customer_location == "noSuchCreditCardCustomerLocation"
            ])
            self.assertTrue(False)
        except AttributeError, error:
            self.assertEquals("Invalid argument(s) for credit_card_customer_location: noSuchCreditCardCustomerLocation", str(error))

    def test_advanced_search_multiple_value_node_merchant_account_id(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.merchant_account_id == transaction.merchant_account_id
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.merchant_account_id.in_list([transaction.merchant_account_id, "bogus_merchant_account_id"])
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.merchant_account_id == "bogus_merchant_account_id"
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_multiple_value_node_credit_card_card_type(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_card_type == transaction.credit_card_details.card_type
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_card_type.in_list([transaction.credit_card_details.card_type, CreditCard.CardType.AmEx])
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.credit_card_card_type == CreditCard.CardType.AmEx
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_multiple_value_node_allowed_values_credit_card_card_type(self):
        try:
            collection = Transaction.search([
                TransactionSearch.credit_card_card_type == "noSuchCreditCardCardType"
            ])
            self.assertTrue(False)
        except AttributeError, error:
            self.assertEquals("Invalid argument(s) for credit_card_card_type: noSuchCreditCardCardType", str(error))

    def test_advanced_search_multiple_value_node_status(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.status == Transaction.Status.Authorized
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.status.in_list([Transaction.Status.Authorized, Transaction.Status.Settled])
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.status == Transaction.Status.Settled
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_authorization_expired_status(self):
        collection = Transaction.search(
            TransactionSearch.status == Transaction.Status.AuthorizationExpired
        )

        self.assertTrue(collection.maximum_size > 0)
        self.assertEqual(Transaction.Status.AuthorizationExpired, collection.first.status)

    def test_advanced_search_multiple_value_node_allowed_values_status(self):
        try:
            collection = Transaction.search([
                TransactionSearch.status == "noSuchStatus"
            ])
            self.assertTrue(False)
        except AttributeError, error:
            self.assertEquals("Invalid argument(s) for status: noSuchStatus", str(error))

    def test_advanced_search_multiple_value_node_source(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.source == Transaction.Source.Api
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.source.in_list([Transaction.Source.Api, Transaction.Source.ControlPanel])
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.source == Transaction.Source.ControlPanel
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_multiple_value_node_allowed_values_source(self):
        try:
            collection = Transaction.search([
                TransactionSearch.source == "noSuchSource"
            ])
            self.assertTrue(False)
        except AttributeError, error:
            self.assertEquals("Invalid argument(s) for source: noSuchSource", str(error))

    def test_advanced_search_multiple_value_node_type(self):
        transaction = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012"
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.type == Transaction.Type.Sale
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.type.in_list([Transaction.Type.Sale, Transaction.Type.Credit])
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.type == Transaction.Type.Credit
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_multiple_value_node_allowed_values_type(self):
        try:
            collection = Transaction.search([
                TransactionSearch.type == "noSuchType"
            ])
            self.assertTrue(False)
        except AttributeError, error:
            self.assertEquals("Invalid argument(s) for type: noSuchType", str(error))

    def test_advanced_search_multiple_value_node_type_with_refund(self):
        name = "Anabel Atkins%s" % randint(1,100000)
        sale = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            },
            'options': {
                'submit_for_settlement': True
            }
        }).transaction
        TestHelper.settle_transaction(sale.id)

        refund = Transaction.refund(sale.id).transaction

        credit = Transaction.credit({
            "amount": Decimal(TransactionAmounts.Authorize),
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2009",
                "cardholder_name": name
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.type == Transaction.Type.Credit
        ])

        self.assertEquals(2, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.type == Transaction.Type.Credit,
            TransactionSearch.refund == True
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(refund.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.type == Transaction.Type.Credit,
            TransactionSearch.refund == False
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(credit.id, collection.first.id)

    def test_advanced_search_range_node_amount(self):
        name = "Henrietta Livingston%s" % randint(1,100000)
        t_1000 = Transaction.sale({
            "amount": TransactionAmounts.Authorize,
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        t_1500 = Transaction.sale({
            "amount": "1500.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        t_1800 = Transaction.sale({
            "amount": "1800.00",
            "credit_card": {
                "number": "4111111111111111",
                "expiration_date": "05/2012",
                "cardholder_name": name
            }
        }).transaction

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount >= "1700"
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1800.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount <= "1250"
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1000.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.credit_card_cardholder_name == name,
            TransactionSearch.amount.between("1100", "1600")
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(t_1500.id, collection.first.id)

    def test_advanced_search_range_node_created_at_less_than_or_equal_to(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
         }).transaction

        past = transaction.created_at - timedelta(minutes=10)
        now = transaction.created_at
        future = transaction.created_at + timedelta(minutes=10)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at <= past
        ])

        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at <= now
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at <= future
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

    def test_advanced_search_range_node_created_at_greater_than_or_equal_to(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
         }).transaction

        past = transaction.created_at - timedelta(minutes=10)
        now = transaction.created_at
        future = transaction.created_at + timedelta(minutes=10)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at >= past
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at >= now
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at >= future
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_created_at_between(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
         }).transaction

        past = transaction.created_at - timedelta(minutes=10)
        now = transaction.created_at
        future = transaction.created_at + timedelta(minutes=10)
        future2 = transaction.created_at + timedelta(minutes=20)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at.between(past, now)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at.between(now, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_created_at_is(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
         }).transaction

        past = transaction.created_at - timedelta(minutes=10)
        now = transaction.created_at
        future = transaction.created_at + timedelta(minutes=10)
        future2 = transaction.created_at + timedelta(minutes=20)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at == past
        ])

        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at == now
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at == future
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_created_with_dates(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
         }).transaction

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.created_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

    def test_advanced_search_range_node_disbursement_date_less_than_or_equal_to(self):
        transaction_id = "deposittransaction"
        disbursement_time = datetime(2013, 4, 10, 0, 0, 0)
        past = disbursement_time - timedelta(minutes=10)
        future = disbursement_time + timedelta(minutes=10)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date <= past
        ])

        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date <= disbursement_time
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date <= future
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

    def test_advanced_search_range_node_disbursement_date_greater_than_or_equal_to(self):
        transaction_id = "deposittransaction"
        disbursement_time = datetime(2013, 4, 10, 0, 0, 0)
        past = disbursement_time - timedelta(minutes=10)
        future = disbursement_time + timedelta(days=1)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date >= past
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date >= disbursement_time
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date >= future
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_disbursement_date_between(self):
        transaction_id = "deposittransaction"
        disbursement_time = datetime(2013, 4, 10, 0, 0, 0)
        past = disbursement_time - timedelta(days=1)
        future = disbursement_time + timedelta(days=1)
        future2 = disbursement_time + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date.between(past, disbursement_time)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date.between(disbursement_time, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_disbursement_date_is(self):
        transaction_id = "deposittransaction"
        disbursement_time = datetime(2013, 4, 10, 0, 0, 0)
        past = disbursement_time - timedelta(days=10)
        now = disbursement_time
        future = disbursement_time + timedelta(days=10)
        future2 = disbursement_time + timedelta(days=20)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date == past
        ])

        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date == now
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date == future
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_disbursement_date_with_dates(self):
        transaction_id = "deposittransaction"
        disbursement_date = date(2013, 4, 10)
        past = disbursement_date - timedelta(days=1)
        future = disbursement_date + timedelta(days=1)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.disbursement_date.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

    def test_advanced_search_range_node_disputed_date_less_than_or_equal_to(self):
        transaction_id = "disputedtransaction"
        disputed_time = datetime(2014, 3, 1, 0, 0, 0)
        past = disputed_time - timedelta(minutes=10)
        future = disputed_time + timedelta(minutes=10)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date <= past
        ])

        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date <= disputed_time
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date <= future
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

    def test_advanced_search_range_node_disputed_date_greater_than_or_equal_to(self):
        transaction_id = "2disputetransaction"
        disputed_time = datetime(2014, 3, 1, 0, 0, 0)
        past = disputed_time - timedelta(minutes=10)
        future = disputed_time + timedelta(days=1)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date >= past
        ])

        self.assertEquals(2, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date >= disputed_time
        ])

        self.assertEquals(2, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date >= future
        ])

        self.assertEquals(1, collection.maximum_size)

    def test_advanced_search_range_node_disputed_date_between(self):
        transaction_id = "disputedtransaction"
        disputed_time = datetime(2014, 3, 1, 0, 0, 0)
        past = disputed_time - timedelta(days=1)
        future = disputed_time + timedelta(days=1)
        future2 = disputed_time + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date.between(past, disputed_time)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date.between(disputed_time, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_disputed_date_is(self):
        transaction_id = "disputedtransaction"
        disputed_time = datetime(2014, 3, 1, 0, 0, 0)
        past = disputed_time - timedelta(days=10)
        now = disputed_time
        future = disputed_time + timedelta(days=10)
        future2 = disputed_time + timedelta(days=20)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date == past
        ])

        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date == now
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date == future
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_disputed_date_with_dates(self):
        transaction_id = "disputedtransaction"
        disputed_date = date(2014, 3, 1)
        past = disputed_date - timedelta(days=1)
        future = disputed_date + timedelta(days=1)

        collection = Transaction.search([
            TransactionSearch.id == transaction_id,
            TransactionSearch.dispute_date.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction_id, collection.first.id)

    def test_advanced_search_range_node_authorization_expired_at(self):
        two_days_ago = datetime.today() - timedelta(days=2)
        yesterday = datetime.today() - timedelta(days=1)
        tomorrow = datetime.today() + timedelta(days=1)

        collection = Transaction.search(
            TransactionSearch.authorization_expired_at.between(two_days_ago, yesterday)
        )
        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search(
            TransactionSearch.authorization_expired_at.between(yesterday, tomorrow)
        )
        self.assertTrue(collection.maximum_size > 0)
        self.assertEquals(Transaction.Status.AuthorizationExpired, collection.first.status)


    def test_advanced_search_range_node_authorized_at(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
        }).transaction

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)
        future2 = datetime.today() + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.authorized_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.authorized_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_failed_at(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Fail,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
        }).transaction

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)
        future2 = datetime.today() + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.failed_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.failed_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_gateway_rejected_at(self):
        old_merchant_id = Configuration.merchant_id
        old_public_key = Configuration.public_key
        old_private_key = Configuration.private_key

        try:
            Configuration.merchant_id = "processing_rules_merchant_id"
            Configuration.public_key = "processing_rules_public_key"
            Configuration.private_key = "processing_rules_private_key"

            transaction  = Transaction.sale({
                 "amount": TransactionAmounts.Authorize,
                 "credit_card": {
                     "number": "4111111111111111",
                     "expiration_date": "05/2012",
                     "cvv": "200"
                 }
            }).transaction

            past = datetime.today() - timedelta(days=1)
            future = datetime.today() + timedelta(days=1)
            future2 = datetime.today() + timedelta(days=2)

            collection = Transaction.search([
                TransactionSearch.id == transaction.id,
                TransactionSearch.gateway_rejected_at.between(past, future)
            ])

            self.assertEquals(1, collection.maximum_size)
            self.assertEquals(transaction.id, collection.first.id)

            collection = Transaction.search([
                TransactionSearch.id == transaction.id,
                TransactionSearch.gateway_rejected_at.between(future, future2)
            ])

            self.assertEquals(0, collection.maximum_size)
        finally:
            Configuration.merchant_id = old_merchant_id
            Configuration.public_key = old_public_key
            Configuration.private_key = old_private_key

    def test_advanced_search_range_node_processor_declined_at(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Decline,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
        }).transaction

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)
        future2 = datetime.today() + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.processor_declined_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.processor_declined_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_settled_at(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             },
             "options": {
                 "submit_for_settlement": True
             }
        }).transaction

        TestHelper.settle_transaction(transaction.id)
        transaction = Transaction.find(transaction.id)

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)
        future2 = datetime.today() + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.settled_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.settled_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_submitted_for_settlement_at(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             },
             "options": {
                 "submit_for_settlement": True
             }
        }).transaction

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)
        future2 = datetime.today() + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.submitted_for_settlement_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.submitted_for_settlement_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_voided_at(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             }
        }).transaction
        transaction = Transaction.void(transaction.id).transaction

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)
        future2 = datetime.today() + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.voided_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.voided_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_range_node_can_search_on_multiple_statuses(self):
        transaction  = Transaction.sale({
             "amount": TransactionAmounts.Authorize,
             "credit_card": {
                 "number": "4111111111111111",
                 "expiration_date": "05/2012"
             },
             "options": {
                 "submit_for_settlement": True
             }
        }).transaction

        past = datetime.today() - timedelta(days=1)
        future = datetime.today() + timedelta(days=1)
        future2 = datetime.today() + timedelta(days=2)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.authorized_at.between(past, future),
            TransactionSearch.submitted_for_settlement_at.between(past, future)
        ])

        self.assertEquals(1, collection.maximum_size)
        self.assertEquals(transaction.id, collection.first.id)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.authorized_at.between(future, future2),
            TransactionSearch.submitted_for_settlement_at.between(future, future2)
        ])

        self.assertEquals(0, collection.maximum_size)

        collection = Transaction.search([
            TransactionSearch.id == transaction.id,
            TransactionSearch.authorized_at.between(past, future),
            TransactionSearch.voided_at.between(past, future)
        ])

        self.assertEquals(0, collection.maximum_size)

    def test_advanced_search_returns_iteratable_results(self):
        collection = Transaction.search([
            TransactionSearch.credit_card_number.starts_with("411")
        ])

        self.assertTrue(collection.maximum_size > 100)

        transaction_ids = [transaction.id for transaction in collection.items]
        self.assertEquals(collection.maximum_size, len(TestHelper.unique(transaction_ids)))

    @raises(DownForMaintenanceError)
    def test_search_handles_a_search_timeout(self):
        Transaction.search([
            TransactionSearch.amount.between("-1100", "1600")
        ])


########NEW FILE########
__FILENAME__ = test_transparent_redirect
from tests.test_helper import *

class TestTransparentRedirect(unittest.TestCase):
    @raises(DownForMaintenanceError)
    def test_parse_and_validate_query_string_checks_http_status_before_hash(self):
        customer = Customer.create().customer
        tr_data = {
            "credit_card": {
                "customer_id": customer.id
            }
        }
        post_params = {
            "tr_data": CreditCard.tr_data_for_create(tr_data, "http://example.com/path?foo=bar"),
            "credit_card[cardholder_name]": "Card Holder",
            "credit_card[number]": "4111111111111111",
            "credit_card[expiration_date]": "05/2012",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params, Configuration.instantiate().base_merchant_url() + "/test/maintenance")
        CreditCard.confirm_transparent_redirect(query_string)

    @raises(AuthenticationError)
    def test_parse_and_validate_query_string_raises_authentication_error_with_bad_credentials(self):
        customer = Customer.create().customer
        tr_data = {
            "credit_card": {
                "customer_id": customer.id
            }
        }

        old_private_key = Configuration.private_key
        try:
            Configuration.private_key = "bad"

            post_params = {
                "tr_data": CreditCard.tr_data_for_create(tr_data, "http://example.com/path?foo=bar"),
                "credit_card[cardholder_name]": "Card Holder",
                "credit_card[number]": "4111111111111111",
                "credit_card[expiration_date]": "05/2012",
            }
            query_string = TestHelper.simulate_tr_form_post(post_params, CreditCard.transparent_redirect_create_url())
            CreditCard.confirm_transparent_redirect(query_string)
        finally:
            Configuration.private_key = old_private_key

    def test_transaction_sale_from_transparent_redirect_with_successful_result(self):
        tr_data = {
            "transaction": {
                "amount": TransactionAmounts.Authorize,
            }
        }
        post_params = {
            "tr_data": Transaction.tr_data_for_sale(tr_data, "http://example.com/path"),
            "transaction[credit_card][number]": "4111111111111111",
            "transaction[credit_card][expiration_date]": "05/2010",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params)
        result = TransparentRedirect.confirm(query_string)
        self.assertTrue(result.is_success)

        transaction = result.transaction
        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount)
        self.assertEquals(Transaction.Type.Sale, transaction.type)
        self.assertEquals("411111", transaction.credit_card_details.bin)
        self.assertEquals("1111", transaction.credit_card_details.last_4)
        self.assertEquals("05/2010", transaction.credit_card_details.expiration_date)

    def test_transaction_credit_from_transparent_redirect_with_successful_result(self):
        tr_data = {
            "transaction": {
                "amount": TransactionAmounts.Authorize,
            }
        }
        post_params = {
            "tr_data": Transaction.tr_data_for_credit(tr_data, "http://example.com/path"),
            "transaction[credit_card][number]": "4111111111111111",
            "transaction[credit_card][expiration_date]": "05/2010",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params)
        result = TransparentRedirect.confirm(query_string)
        self.assertTrue(result.is_success)

        transaction = result.transaction
        self.assertEquals(Decimal(TransactionAmounts.Authorize), transaction.amount)
        self.assertEquals(Transaction.Type.Credit, transaction.type)
        self.assertEquals("411111", transaction.credit_card_details.bin)
        self.assertEquals("1111", transaction.credit_card_details.last_4)
        self.assertEquals("05/2010", transaction.credit_card_details.expiration_date)

    def test_customer_create_from_transparent_redirect(self):
        tr_data = {
            "customer": {
                "first_name": "John",
                "last_name": "Doe",
                "company": "Doe Co",
            }
        }
        post_params = {
            "tr_data": Customer.tr_data_for_create(tr_data, "http://example.com/path"),
            "customer[email]": "john@doe.com",
            "customer[phone]": "312.555.2323",
            "customer[fax]": "614.555.5656",
            "customer[website]": "www.johndoe.com"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params)
        result = TransparentRedirect.confirm(query_string)
        self.assertTrue(result.is_success)
        customer = result.customer
        self.assertEquals("John", customer.first_name)
        self.assertEquals("Doe", customer.last_name)
        self.assertEquals("Doe Co", customer.company)
        self.assertEquals("john@doe.com", customer.email)
        self.assertEquals("312.555.2323", customer.phone)
        self.assertEquals("614.555.5656", customer.fax)
        self.assertEquals("www.johndoe.com", customer.website)

    def test_customer_update_from_transparent_redirect(self):
        customer = Customer.create({"first_name": "Sarah", "last_name": "Humphrey"}).customer

        tr_data = {
            "customer_id": customer.id,
            "customer": {
                "first_name": "Stan",
            }
        }
        post_params = {
            "tr_data": Customer.tr_data_for_update(tr_data, "http://example.com/path"),
            "customer[last_name]": "Humphrey",
        }

        query_string = TestHelper.simulate_tr_form_post(post_params)
        result = TransparentRedirect.confirm(query_string)
        self.assertTrue(result.is_success)

        customer = Customer.find(customer.id)
        self.assertEquals("Stan", customer.first_name)
        self.assertEquals("Humphrey", customer.last_name)

    def test_payment_method_create_from_transparent_redirect(self):
        customer = Customer.create({"first_name": "Sarah", "last_name": "Humphrey"}).customer
        tr_data = {
            "credit_card": {
                "customer_id": customer.id,
                "number": "4111111111111111",
            }
        }
        post_params = {
            "tr_data": CreditCard.tr_data_for_create(tr_data, "http://example.com/path"),
            "credit_card[expiration_month]": "01",
            "credit_card[expiration_year]": "10"
        }

        query_string = TestHelper.simulate_tr_form_post(post_params)
        result = TransparentRedirect.confirm(query_string)
        self.assertTrue(result.is_success)
        credit_card = result.credit_card
        self.assertEquals("411111", credit_card.bin)
        self.assertEquals("1111", credit_card.last_4)
        self.assertEquals("01/2010", credit_card.expiration_date)

    def test_payment_method_update_from_transparent_redirect(self):
        customer = Customer.create({"first_name": "Sarah", "last_name": "Humphrey"}).customer
        credit_card = CreditCard.create({
            "customer_id": customer.id,
            "number": "4111111111111111",
            "expiration_date": "10/10"
        }).credit_card

        tr_data = {
            "payment_method_token": credit_card.token,
            "credit_card": {
                "expiration_date": "12/12"
            }
        }
        post_params = {
            "tr_data": CreditCard.tr_data_for_update(tr_data, "http://example.com/path"),
        }

        query_string = TestHelper.simulate_tr_form_post(post_params)
        TransparentRedirect.confirm(query_string)
        credit_card = CreditCard.find(credit_card.token)

        self.assertEquals("12/2012", credit_card.expiration_date)

########NEW FILE########
__FILENAME__ = test_helper
import httplib
import os
import random
import re
import unittest
import urllib
import warnings
import json
from braintree import *
from braintree.exceptions import *
from braintree.util import *
from datetime import date, datetime, timedelta
from decimal import Decimal
from nose.tools import raises
from random import randint

Configuration.configure(
    Environment.Development,
    "integration_merchant_id",
    "integration_public_key",
    "integration_private_key"
)

def showwarning(message, category, filename, lineno, file=None, line=None):
    pass
warnings.showwarning = showwarning

class TestHelper(object):

    default_merchant_account_id = "sandbox_credit_card"
    non_default_merchant_account_id = "sandbox_credit_card_non_default"
    non_default_sub_merchant_account_id = "sandbox_sub_merchant_account"
    add_on_discount_plan = {
         "description": "Plan for integration tests -- with add-ons and discounts",
         "id": "integration_plan_with_add_ons_and_discounts",
         "price": Decimal("9.99"),
         "trial_duration": 2,
         "trial_duration_unit": Subscription.TrialDurationUnit.Day,
         "trial_period": True
    }

    billing_day_of_month_plan = {
         "description": "Plan for integration tests -- with billing day of month",
         "id": "integration_plan_with_billing_day_of_month",
         "billing_day_of_month": 5,
         "price": Decimal("8.88"),
    }

    trial_plan = {
        "description": "Plan for integration tests -- with trial",
        "id": "integration_trial_plan",
        "price": Decimal("43.21"),
        "trial_period": True,
        "trial_duration": 2,
        "trial_duration_unit": Subscription.TrialDurationUnit.Day
    }

    trialless_plan = {
        "description": "Plan for integration tests -- without a trial",
        "id": "integration_trialless_plan",
        "price": Decimal("12.34"),
        "trial_period": False
    }

    @staticmethod
    def make_past_due(subscription, number_of_days_past_due=1):
        Configuration.instantiate().http().put("/subscriptions/%s/make_past_due?days_past_due=%s" % (subscription.id, number_of_days_past_due))

    @staticmethod
    def escrow_transaction(transaction_id):
        Configuration.instantiate().http().put("/transactions/" + transaction_id + "/escrow")

    @staticmethod
    def settle_transaction(transaction_id):
        Configuration.instantiate().http().put("/transactions/" + transaction_id + "/settle")

    @staticmethod
    def simulate_tr_form_post(post_params, url=TransparentRedirect.url()):
        form_data = urllib.urlencode(post_params)
        conn = httplib.HTTPConnection(Configuration.environment.server_and_port)
        conn.request("POST", url, form_data, TestHelper.__headers())
        response = conn.getresponse()
        query_string = response.getheader("location").split("?", 1)[1]
        conn.close()
        return query_string

    @staticmethod
    def includes(collection, expected):
        for item in collection.items:
            if item.id == expected.id:
                return True
        return False

    @staticmethod
    def in_list(collection, expected):
        for item in collection:
            if item == expected:
                return True
        return False

    @staticmethod
    def includes_status(collection, status):
        for item in collection.items:
            if item.status == status:
                return True
        return False

    @staticmethod
    def now_in_eastern():
        now  = datetime.utcnow()
        offset  = timedelta(hours=5)
        return (now - offset).strftime("%Y-%m-%d")

    @staticmethod
    def unique(list):
        return set(list)

    @staticmethod
    def __headers():
        return {
            "Accept": "application/xml",
            "Content-type": "application/x-www-form-urlencoded",
        }

class ClientApiHttp(Http):
    def __init__(self, config, options):
        self.config = config
        self.options = options
        self.http = Http(config)

    def get(self, path):
        return self.__http_do("GET", path)

    def post(self, path, params = None):
        return self.__http_do("POST", path, params)

    def __http_do(self, http_verb, path, params=None):
        self.config.use_unsafe_ssl = True
        http_strategy = self.config.http_strategy()
        request_body = json.dumps(params) if params else None
        return http_strategy.http_do(http_verb, path, self.__headers(), request_body)

    def set_authorization_fingerprint(self, authorization_fingerprint):
        self.options['authorization_fingerprint'] = authorization_fingerprint

    def get_cards(self):
        encoded_fingerprint = urllib.quote_plus(self.options["authorization_fingerprint"])
        url = "/merchants/%s/client_api/nonces.json" % self.config.merchant_id
        url += "?authorizationFingerprint=%s" % encoded_fingerprint
        url += "&sharedCustomerIdentifier=%s" % self.options["shared_customer_identifier"]
        url += "&sharedCustomerIdentifierType=%s" % self.options["shared_customer_identifier_type"]

        return self.get(url)

    def add_card(self, params):
        url = "/merchants/%s/client_api/nonces.json" % self.config.merchant_id

        if 'authorization_fingerprint' in self.options:
            params['authorizationFingerprint'] = self.options['authorization_fingerprint']

        if 'shared_customer_identifier' in self.options:
            params['sharedCustomerIdentifier'] = self.options['shared_customer_identifier']

        if 'shared_customer_identifier_type' in self.options:
            params['sharedCustomerIdentifierType'] = self.options['shared_customer_identifier_type']

        return self.post(url, params)

    def __headers(self):
        return {
            "Content-type": "application/json",
            "User-Agent": "Braintree Python " + version.Version,
            "X-ApiVersion": Configuration.api_version()
        }

########NEW FILE########
__FILENAME__ = test_address
from tests.test_helper import *

class TestAddress(unittest.TestCase):
    def test_create_raise_exception_with_bad_keys(self):
        try:
            Address.create({"customer_id": "12345", "bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_create_raises_error_if_no_customer_id_given(self):
        try:
            Address.create({"country_name": "United States of America"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'customer_id must be provided'", str(e))

    def test_create_raises_key_error_if_given_invalid_customer_id(self):
        try:
            Address.create({"customer_id": "!@#$%"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'customer_id contains invalid characters'", str(e))

    def test_update_raise_exception_with_bad_keys(self):
        try:
            Address.update("customer_id", "address_id", {"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_finding_address_with_empty_customer_id_raises_not_found_exception(self):
        try:
            Address.find(" ", "address_id")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertTrue(True)

    def test_finding_address_with_empty_address_id_raises_not_found_exception(self):
        try:
            Address.find("customer_id", " ")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertTrue(True)

########NEW FILE########
__FILENAME__ = test_address_details
from tests.test_helper import *
from braintree.merchant_account.address_details import AddressDetails

class TestAddressDetails(unittest.TestCase):
    def test_repr_has_all_fields(self):
        details = AddressDetails({
            "street_address": "123 First St",
            "region": "Las Vegas",
            "locality": "NV",
            "postal_code": "89913"
        })

        regex = "<AddressDetails {street_address: '123 First St', locality: 'NV', region: 'Las Vegas', postal_code: '89913'} at \w+>"

        matches = re.match(regex, repr(details))
        self.assertTrue(matches)

########NEW FILE########
__FILENAME__ = test_business_details
from tests.test_helper import *

class TestBusinessDetails(unittest.TestCase):
    def test_repr_has_all_fields(self):
        details = BusinessDetails({
            "dba_name": "Bar Suenami",
            "legal_name": "Suenami Restaurant Group",
            "tax_id": "123001234",
            "address": {
                "street_address": "123 First St",
                "region": "Las Vegas",
                "locality": "NV",
            }
        })

        regex = "<BusinessDetails {dba_name: 'Bar Suenami', legal_name: 'Suenami Restaurant Group', tax_id: '123001234', address_details: <AddressDetails {street_address: '123 First St', locality: 'NV', region: 'Las Vegas'} at \w+>} at \w+>"

        matches = re.match(regex, repr(details))
        self.assertTrue(matches)

########NEW FILE########
__FILENAME__ = test_client_token
import json
from tests.test_helper import *

class TestClientToken(unittest.TestCase):
    def test_credit_card_options_require_customer_id(self):
        for option in ["verify_card", "make_default", "fail_on_duplicate_payment_method"]:
            try:
                client_token = ClientToken.generate({
                    "options": {option: True}
                })
                self.assertTrue(False, "Should have raised an exception")
            except InvalidSignatureError, e:
                self.assertTrue(str(e).find(option))

    def test_generate_delegates_client_token_generation_to_gateway(self):
        class MockGateway():
            def generate(self, _):
                return "mock_client_token"

        mock_gateway = MockGateway()
        client_token = ClientToken.generate({}, mock_gateway)

        self.assertEqual("mock_client_token", client_token)

########NEW FILE########
__FILENAME__ = test_configuration
from tests.test_helper import *
import braintree
import os

class TestConfiguration(unittest.TestCase):
    def test_works_with_unconfigured_configuration(self):
        try:
            # reset class level attributes on Configuration set in test helper
            reload(braintree.configuration)
            config = Configuration(
                environment=braintree.Environment.Sandbox,
                merchant_id='my_merchant_id',
                public_key='public_key',
                private_key='private_key'
            )
            config.http_strategy()
        except AttributeError, e:
            print e
            self.assertTrue(False)
        finally:
            # repopulate class level attributes on Configuration
            import tests.test_helper
            reload(tests.test_helper)

    def test_base_merchant_path_for_development(self):
        self.assertEqual("/merchants/integration_merchant_id", Configuration.instantiate().base_merchant_path())

    def test_configuration_construction_for_merchant(self):
        config = Configuration(
            environment=braintree.Environment.Sandbox,
            merchant_id='my_merchant_id',
            public_key='public_key',
            private_key='private_key'
        )
        self.assertEqual(config.merchant_id, 'my_merchant_id')
        self.assertEqual(config.public_key, 'public_key')
        self.assertEqual(config.private_key, 'private_key')

    def test_configuration_construction_for_partner(self):
        config = Configuration.for_partner(
            environment=braintree.Environment.Sandbox,
            partner_id='my_partner_id',
            public_key='public_key',
            private_key='private_key'
        )
        self.assertEqual(config.merchant_id, 'my_partner_id')
        self.assertEqual(config.public_key, 'public_key')
        self.assertEqual(config.private_key, 'private_key')

    def test_overriding_http_strategy_blows_up_if_setting_an_invalid_strategy(self):
        old_http_strategy = None

        if "PYTHON_HTTP_STRATEGY" in os.environ:
            old_http_strategy = os.environ["PYTHON_HTTP_STRATEGY"]

        try:
            os.environ["PYTHON_HTTP_STRATEGY"] = "invalid"
            strategy = Configuration.instantiate().http_strategy()
            self.assertTrue(False, "Expected StandardError")
        except ValueError, e:
            self.assertEqual("invalid http strategy", e.message)
        finally:
            if old_http_strategy == None:
                del(os.environ["PYTHON_HTTP_STRATEGY"])
            else:
                os.environ["PYTHON_HTTP_STRATEGY"] = old_http_strategy

    def test_overriding_http_strategy(self):
        old_http_strategy = None

        if "PYTHON_HTTP_STRATEGY" in os.environ:
            old_http_strategy = os.environ["PYTHON_HTTP_STRATEGY"]

        try:
            os.environ["PYTHON_HTTP_STRATEGY"] = "httplib"
            strategy = Configuration.instantiate().http_strategy()
            self.assertTrue(isinstance(strategy, braintree.util.http_strategy.httplib_strategy.HttplibStrategy))
        finally:
            if old_http_strategy == None:
                del(os.environ["PYTHON_HTTP_STRATEGY"])
            else:
                os.environ["PYTHON_HTTP_STRATEGY"] = old_http_strategy

    def test_configuring_with_an_http_strategy(self):
        old_http_strategy = Configuration.default_http_strategy

        try:
            Configuration.default_http_strategy = braintree.util.http_strategy.httplib_strategy.HttplibStrategy
            strategy = Configuration.instantiate().http_strategy()
            self.assertTrue(isinstance(strategy, braintree.util.http_strategy.httplib_strategy.HttplibStrategy))
        finally:
            Configuration.default_http_strategy = old_http_strategy

########NEW FILE########
__FILENAME__ = test_credit_card
from tests.test_helper import *
import braintree.test.venmo_sdk as venmo_sdk

class TestCreditCard(unittest.TestCase):
    def test_create_raises_exception_with_bad_keys(self):
        try:
            CreditCard.create({"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_update_raises_exception_with_bad_keys(self):
        try:
            CreditCard.update("token", {"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_tr_data_for_create_raises_error_with_bad_keys(self):
        try:
            CreditCard.tr_data_for_create({"bad_key": "value"}, "http://example.com")
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_tr_data_for_update_raises_error_with_bad_keys(self):
        try:
            CreditCard.tr_data_for_update({"bad_key": "value"}, "http://example.com")
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_transparent_redirect_create_url(self):
        port = os.getenv("GATEWAY_PORT") or "3000"
        self.assertEquals(
            "http://localhost:" + port + "/merchants/integration_merchant_id/payment_methods/all/create_via_transparent_redirect_request",
            CreditCard.transparent_redirect_create_url()
        )

    def test_transparent_redirect_update_url(self):
        port = os.getenv("GATEWAY_PORT") or "3000"
        self.assertEquals(
            "http://localhost:" + port + "/merchants/integration_merchant_id/payment_methods/all/update_via_transparent_redirect_request",
            CreditCard.transparent_redirect_update_url()
        )

    @raises(DownForMaintenanceError)
    def test_confirm_transaprant_redirect_raises_error_given_503_status_in_query_string(self):
        CreditCard.confirm_transparent_redirect(
            "http_status=503&id=6kdj469tw7yck32j&hash=1b3d29199a282e63074a7823b76bccacdf732da6"
        )

    def test_create_signature(self):
        expected = ["billing_address_id", "cardholder_name", "cvv", "expiration_date", "expiration_month",
            "expiration_year", "device_session_id", "fraud_merchant_id", "number", "token", "venmo_sdk_payment_method_code",
            "device_data", "payment_method_nonce",
            {
                "billing_address": [
                    "company", "country_code_alpha2", "country_code_alpha3", "country_code_numeric", "country_name",
                    "extended_address", "first_name", "last_name", "locality", "postal_code", "region", "street_address"
                ]
            },
            {"options": ["make_default", "verification_merchant_account_id", "verify_card", "venmo_sdk_session", "fail_on_duplicate_payment_method"]},
            "customer_id"
        ]
        self.assertEquals(expected, CreditCard.create_signature())

    def test_update_signature(self):
        expected = ["billing_address_id", "cardholder_name", "cvv", "expiration_date", "expiration_month",
            "expiration_year", "device_session_id", "fraud_merchant_id", "number", "token", "venmo_sdk_payment_method_code",
            "device_data", "payment_method_nonce",
            {
                "billing_address": [
                    "company", "country_code_alpha2", "country_code_alpha3", "country_code_numeric", "country_name",
                    "extended_address", "first_name", "last_name", "locality", "postal_code", "region", "street_address",
                    {"options": ["update_existing"]}
                ]
            },
            {"options": ["make_default", "verification_merchant_account_id", "verify_card", "venmo_sdk_session"]}
        ]
        self.assertEquals(expected, CreditCard.update_signature())

    def test_finding_empty_id_raises_not_found_exception(self):
        try:
            CreditCard.find(" ")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertTrue(True)


########NEW FILE########
__FILENAME__ = test_crypto
from tests.test_helper import *

class TestCrypto(unittest.TestCase):
    def test_sha1_hmac_hash(self):
        actual = Crypto.sha1_hmac_hash("secretKey", "hello world")
        self.assertEquals("d503d7a1a6adba1e6474e9ff2c4167f9dfdf4247", actual)

    def test_sha256_hmac_hash(self):
        actual = Crypto.sha256_hmac_hash("secret-key", "secret-message")
        self.assertEquals("68e7f2ecab71db67b1aca2a638f5122810315c3013f27c2196cd53e88709eecc", actual)

    def test_secure_compare_returns_true_when_same(self):
        self.assertTrue(Crypto.secure_compare("a_string", "a_string"))

    def test_secure_compare_returns_false_when_different_lengths(self):
        self.assertFalse(Crypto.secure_compare("a_string", "a_string_that_is_longer"))

    def test_secure_compare_returns_false_when_different(self):
        self.assertFalse(Crypto.secure_compare("a_string", "a_strong"))

########NEW FILE########
__FILENAME__ = test_customer
from tests.test_helper import *

class TestCustomer(unittest.TestCase):
    def test_create_raise_exception_with_bad_keys(self):
        try:
            Customer.create({"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_create_raise_exception_with_bad_nested_keys(self):
        try:
            Customer.create({"credit_card": {"bad_key": "value"}})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: credit_card[bad_key]'", str(e))

    def test_update_raise_exception_with_bad_keys(self):
        try:
            Customer.update("id", {"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_update_raise_exception_with_bad_nested_keys(self):
        try:
            Customer.update("id", {"credit_card": {"bad_key": "value"}})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: credit_card[bad_key]'", str(e))

    def test_tr_data_for_create_raises_error_with_bad_keys(self):
        try:
            Customer.tr_data_for_create({"bad_key": "value"}, "http://example.com")
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_tr_data_for_update_raises_error_with_bad_keys(self):
        try:
            Customer.tr_data_for_update({"bad_key": "value"}, "http://example.com")
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_finding_empty_id_raises_not_found_exception(self):
        try:
            Customer.find(" ")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertTrue(True)

########NEW FILE########
__FILENAME__ = test_disbursement
from tests.test_helper import *
from datetime import date

class TestDisbursement(unittest.TestCase):
    def test_constructor(self):
        attributes = {
            "merchant_account": {
                "id": "sub_merchant_account",
                "status": "active",
                "master_merchant_account": {
                    "id": "master_merchant_account",
                    "status": "active"
                },
            },
            "id": "123456",
            "exception_message": "invalid_account_number",
            "amount": "100.00",
            "disbursement_date": date(2013, 4, 10),
            "follow_up_action": "update",
            "transaction_ids": ["asdf", "qwer"]
        }

        disbursement = Disbursement(None, attributes)

        self.assertEquals(disbursement.id, "123456")
        self.assertEquals(disbursement.amount, Decimal("100.00"))
        self.assertEquals(disbursement.transaction_ids, ["asdf", "qwer"])
        self.assertEquals(disbursement.merchant_account.master_merchant_account.id, "master_merchant_account")

########NEW FILE########
__FILENAME__ = test_disbursement_detail

from tests.test_helper import *
from braintree.resource import Resource
from braintree.disbursement_detail import DisbursementDetail

class TestDisbursementDetail(unittest.TestCase):
    def test_is_valid_true(self):
        detail_hash = {
            'settlement_amount': '27.00',
            'settlement_currency_iso_code': 'USD',
            'settlement_currency_exchange_rate': '1',
            'disbursed_at': datetime(2013, 4, 11, 0, 0, 0),
            'disbursement_date': date(2013, 4, 10),
            'funds_held': False
        }
        disbursement_details = DisbursementDetail(detail_hash)
        self.assertTrue(disbursement_details.is_valid)

    def test_is_valid_false(self):
        detail_hash = {
            'settlement_amount': None,
            'settlement_currency_iso_code': None,
            'settlement_currency_exchange_rate': None,
            'disbursed_at': None,
            'disbursement_date': None,
            'funds_held': None
        }
        disbursement_details = DisbursementDetail(detail_hash)
        self.assertEquals(False, disbursement_details.is_valid)


########NEW FILE########
__FILENAME__ = test_environment
from tests.test_helper import *

class TestEnvironment(unittest.TestCase):
    def test_server_and_port_for_development(self):
        port = os.getenv("GATEWAY_PORT") or "3000"
        self.assertEquals("localhost:" + port, Environment.Development.server_and_port)

    def test_base_url(self):
        self.assertEquals("https://api.sandbox.braintreegateway.com:443", Environment.Sandbox.base_url)
        self.assertEquals("https://api.braintreegateway.com:443", Environment.Production.base_url)

    def test_server_and_port_for_sandbox(self):
        self.assertEquals("api.sandbox.braintreegateway.com:443", Environment.Sandbox.server_and_port)

    def test_server_and_port_for_production(self):
        self.assertEquals("api.braintreegateway.com:443", Environment.Production.server_and_port)

    def test_server_for_development(self):
        self.assertEquals("localhost", Environment.Development.server)

    def test_server_for_sandbox(self):
        self.assertEquals("api.sandbox.braintreegateway.com", Environment.Sandbox.server)

    def test_server_for_production(self):
        self.assertEquals("api.braintreegateway.com", Environment.Production.server)

    def test_port_for_development(self):
        port = os.getenv("GATEWAY_PORT") or "3000"
        port = int(port)
        self.assertEquals(port, Environment.Development.port)

    def test_port_for_sandbox(self):
        self.assertEquals(443, Environment.Sandbox.port)

    def test_port_for_production(self):
        self.assertEquals(443, Environment.Production.port)

    def test_is_ssl_for_development(self):
        self.assertFalse(Environment.Development.is_ssl)

    def test_is_ssl_for_sandbox(self):
        self.assertTrue(Environment.Sandbox.is_ssl)

    def test_is_ssl_for_production(self):
        self.assertTrue(Environment.Production.is_ssl)

    def test_protocol_for_development(self):
        self.assertEquals("http://", Environment.Development.protocol)

    def test_protocol_for_sandbox(self):
        self.assertEquals("https://", Environment.Sandbox.protocol)

    def test_protocol_for_production(self):
        self.assertEquals("https://", Environment.Production.protocol)

    def test_ssl_certificate_for_development(self):
        self.assertEquals(None, Environment.Development.ssl_certificate)


########NEW FILE########
__FILENAME__ = test_errors
from tests.test_helper import *

class TestErrors(unittest.TestCase):
    def test_errors_for_the_given_scope(self):
        errors = Errors({"level1": {"errors": [{"code": "code1", "attribute": "attr", "message": "message"}]}})
        self.assertEquals(1, errors.for_object("level1").size)
        self.assertEquals(1, len(errors.for_object("level1")))

    def test_for_object_returns_empty_errors_collection_if_no_errors_at_given_scope(self):
        errors = Errors({"level1": {"errors": [{"code": "code1", "attribute": "attr", "message": "message"}]}})
        self.assertEquals(0, errors.for_object("no_errors_here").size)
        self.assertEquals(0, len(errors.for_object("no_errors_here")))

    def test_size_returns_number_of_errors_at_first_level_if_only_one_level_exists(self):
        hash = {
            "level1": {"errors": [{"code": "code1", "attribute": "attr", "message": "message"}]}
        }
        self.assertEqual(1, Errors(hash).size)
        self.assertEqual(1, len(Errors(hash)))

    def test_size_returns_number_of_errors_at_all_levels(self):
        hash = {
            "level1": {
                "errors": [{"code": "code1", "attribute": "attr", "message": "message"}],
                "level2": {
                    "errors": [
                        {"code": "code2", "attribute": "attr", "message": "message"},
                        {"code": "code3", "attribute": "attr", "message": "message"}
                    ]
                }
            }
        }
        self.assertEqual(3, Errors(hash).size)
        self.assertEqual(3, len(Errors(hash)))

    def test_deep_errors_returns_all_errors(self):
        hash = {
            "level1": {
                "errors": [{"code": "code1", "attribute": "attr", "message": "message"}],
                "level2": {
                    "errors": [
                        {"code": "code2", "attribute": "attr", "message": "message"},
                        {"code": "code3", "attribute": "attr", "message": "message"}
                    ]
                }
            }
        }

        errors = Errors(hash).deep_errors
        self.assertEquals(["code1", "code2", "code3"], [error.code for error in errors])


########NEW FILE########
__FILENAME__ = test_error_result
from tests.test_helper import *

class TestErrorResult(unittest.TestCase):
    def test_it_initializes_params_and_errors(self):
        errors = {
            "scope": {
                "errors": [{"code": 123, "message": "something is invalid", "attribute": "something"}]
            }
        }

        result = ErrorResult("gateway", {"errors": errors, "params": "params", "message": "brief description"})
        self.assertFalse(result.is_success)
        self.assertEquals("params", result.params)
        self.assertEquals(1, result.errors.size)
        self.assertEquals("something is invalid", result.errors.for_object("scope")[0].message)
        self.assertEquals("something", result.errors.for_object("scope")[0].attribute)
        self.assertEquals(123, result.errors.for_object("scope")[0].code)

    def test_it_ignores_other_params(self):
        errors = {
            "scope": {
                "errors": [{"code": 123, "message": "something is invalid", "attribute": "something"}]
            }
        }

        result = ErrorResult("gateway", {"errors": errors, "params": "params", "message": "brief description", "other": "stuff"})
        self.assertFalse(result.is_success)

    def test_transaction_is_none_if_not_set(self):
        result = ErrorResult("gateway", {"errors": {}, "params": {}, "message": "brief description"})
        self.assertTrue(result.transaction == None)

    def test_verification_is_none_if_not_set(self):
        result = ErrorResult("gateway", {"errors": {}, "params": {}, "message": "brief description"})
        self.assertTrue(result.credit_card_verification == None)

########NEW FILE########
__FILENAME__ = test_funding_details
from tests.test_helper import *

class TestFundingDetails(unittest.TestCase):
    def test_repr_has_all_fields(self):
        details = FundingDetails({
            "destination": "bank",
            "routing_number": "11112222",
            "account_number_last_4": "3333",
            "email": "lucyloo@work.com",
            "mobile_phone": "9998887777"
        })

        regex = "<FundingDetails {account_number_last_4: '3333', routing_number: '11112222', destination: 'bank', email: 'lucyloo@work.com', mobile_phone: '9998887777'} at \w+>"

        matches = re.match(regex, repr(details))
        self.assertTrue(matches)

########NEW FILE########
__FILENAME__ = test_http
from tests.test_helper import *

class TestHttp(unittest.TestCase):
    def test_raise_exception_from_status_for_upgrade_required(self):
        try:
            Http.raise_exception_from_status(426)
            self.assertTrue(False)
        except UpgradeRequiredError:
            pass

########NEW FILE########
__FILENAME__ = test_individual_details
from tests.test_helper import *

class TestIndividualDetails(unittest.TestCase):
    def test_repr_has_all_fields(self):
        details = IndividualDetails({
            "first_name": "Sue",
            "last_name": "Smith",
            "email": "sue@hotmail.com",
            "phone": "1112223333",
            "date_of_birth": "1980-12-05",
            "ssn_last_4": "5555",
            "address": {
                "street_address": "123 First St",
            }
        })

        regex = "<IndividualDetails {first_name: 'Sue', last_name: 'Smith', email: 'sue@hotmail.com', phone: '1112223333', date_of_birth: '1980-12-05', ssn_last_4: '5555', address_details: <AddressDetails {street_address: '123 First St'} at \w+>} at \w+>"

        matches = re.match(regex, repr(details))
        self.assertTrue(matches)

########NEW FILE########
__FILENAME__ = test_merchant_account
from tests.test_helper import *

class TestMerchantAccount(unittest.TestCase):
    def test_create_new_merchant_account_with_all_params(self):
        params = {
            "id": "sub_merchant_account",
            "status": "active",
            "master_merchant_account": {
                "id": "master_merchant_account",
                "status": "active"
            },
            "individual": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "date_of_birth": "1970-01-01",
                "phone": "3125551234",
                "ssn_last_4": "6789",
                "address": {
                    "street_address": "123 Fake St",
                    "locality": "Chicago",
                    "region": "IL",
                    "postal_code": "60622",
                }
            },
            "business": {
                "dba_name": "James's Bloggs",
                "tax_id": "123456789",
            },
            "funding": {
                "account_number_last_4": "8798",
                "routing_number": "071000013",
            }
        }

        merchant_account = MerchantAccount(None, params)

        self.assertEquals(merchant_account.status, "active")
        self.assertEquals(merchant_account.id, "sub_merchant_account")
        self.assertEquals(merchant_account.master_merchant_account.id, "master_merchant_account")
        self.assertEquals(merchant_account.master_merchant_account.status, "active")
        self.assertEquals(merchant_account.individual_details.first_name, "John")
        self.assertEquals(merchant_account.individual_details.last_name, "Doe")
        self.assertEquals(merchant_account.individual_details.email, "john.doe@example.com")
        self.assertEquals(merchant_account.individual_details.date_of_birth, "1970-01-01")
        self.assertEquals(merchant_account.individual_details.phone, "3125551234")
        self.assertEquals(merchant_account.individual_details.ssn_last_4, "6789")
        self.assertEquals(merchant_account.individual_details.address_details.street_address, "123 Fake St")
        self.assertEquals(merchant_account.individual_details.address_details.locality, "Chicago")
        self.assertEquals(merchant_account.individual_details.address_details.region, "IL")
        self.assertEquals(merchant_account.individual_details.address_details.postal_code, "60622")
        self.assertEquals(merchant_account.business_details.dba_name, "James's Bloggs")
        self.assertEquals(merchant_account.business_details.tax_id, "123456789")
        self.assertEquals(merchant_account.funding_details.account_number_last_4, "8798")
        self.assertEquals(merchant_account.funding_details.routing_number, "071000013")

########NEW FILE########
__FILENAME__ = test_partner_merchant
from tests.test_helper import *

class TestPartnerMerchant(unittest.TestCase):
    def test_representation(self):
        merchant = PartnerMerchant(None, {"partner_merchant_id": "abc123",
                                          "private_key": "my_private_key",
                                          "public_key": "my_public_key",
                                          "merchant_public_id": "foobar",
                                          "client_side_encryption_key": "cse_key"})
        self.assertTrue("partner_merchant_id: 'abc123'" in repr(merchant))
        self.assertTrue("public_key: 'my_public_key'" in repr(merchant))
        self.assertTrue("merchant_public_id: 'foobar'" in repr(merchant))
        self.assertTrue("client_side_encryption_key: 'cse_key'" in repr(merchant))

        self.assertFalse("private_key: 'my_private_key'" in repr(merchant))

########NEW FILE########
__FILENAME__ = test_resource
from tests.test_helper import *
from braintree.resource import Resource

class TestResource(unittest.TestCase):
    def test_verify_keys_allows_wildcard_keys(self):
        signature = [
            {"foo": [{"bar": ["__any_key__"]}]}
        ]
        params = {
            "foo[bar][lower]": "lowercase",
            "foo[bar][UPPER]": "uppercase",
            "foo[bar][123]": "numeric",
            "foo[bar][under_scores]": "underscores",
            "foo[bar][dash-es]": "dashes",
            "foo[bar][ABC-abc_123]": "all together"
        }
        Resource.verify_keys(params, signature)

    @raises(KeyError)
    def test_verify_keys_escapes_brackets_in_signature(self):
        signature = [
            {"customer": [{"custom_fields": ["__any_key__"]}]}
        ]
        params = {
            "customer_id": "value",
        }
        Resource.verify_keys(params, signature)

    def test_verify_keys_works_with_array_param(self):
        signature = [
            {"customer": ["one", "two"]}
        ]
        params = {
            "customer": {
                "one": "foo"
            }
        }
        Resource.verify_keys(params, signature)

    @raises(KeyError)
    def test_verify_keys_raises_on_bad_array_param(self):
        signature = [
            {"customer": ["one", "two"]}
        ]
        params = {
            "customer": {
                "invalid": "foo"
            }
        }
        Resource.verify_keys(params, signature)

    def test_verify_keys_works_with_arrays(self):
        signature = [
            {"add_ons": [{"update": ["existing_id", "quantity"]}]}
        ]
        params = {
            "add_ons": {
                "update": [
                    {
                        "existing_id": "foo",
                        "quantity": 10
                    }
                ]
            }
        }
        Resource.verify_keys(params, signature)

    @raises(KeyError)
    def test_verify_keys_raises_with_invalid_param_in_arrays(self):
        signature = [
            {"add_ons": [{"update": ["existing_id", "quantity"]}]}
        ]
        params = {
            "add_ons": {
                "update": [
                    {
                        "invalid": "foo",
                        "quantity": 10
                    }
                ]
            }
        }
        Resource.verify_keys(params, signature)

########NEW FILE########
__FILENAME__ = test_resource_collection
from tests.test_helper import *

class TestResourceCollection(unittest.TestCase):
    class TestResource:
        items = ["a", "b", "c", "d", "e"]

        @staticmethod
        def fetch(query, ids):
            return [TestResourceCollection.TestResource.items[int(id)] for id in ids]

    def test_iterating_over_contents(self):
        collection_data = {
            "search_results": {
                "page_size": 2,
                "ids": ["0", "1", "2", "3", "4"]
            }
        }
        collection = ResourceCollection("some_query", collection_data, TestResourceCollection.TestResource.fetch)
        new_items = []
        index = 0
        for item in collection.items:
            self.assertEquals(TestResourceCollection.TestResource.items[index], item)
            new_items.append(item)
            index += 1

        self.assertEquals(5, len(new_items))


########NEW FILE########
__FILENAME__ = test_search
from tests.test_helper import *

class TestSearch(unittest.TestCase):
    def test_text_node_is(self):
        node = Search.TextNodeBuilder("name")
        self.assertEquals({"is": "value"}, (node == "value").to_param())

    def test_text_node_is_not(self):
        node = Search.TextNodeBuilder("name")
        self.assertEquals({"is_not": "value"}, (node != "value").to_param())

    def test_text_node_starts_with(self):
        node = Search.TextNodeBuilder("name")
        self.assertEquals({"starts_with": "value"}, (node.starts_with("value")).to_param())

    def test_text_node_ends_with(self):
        node = Search.TextNodeBuilder("name")
        self.assertEquals({"ends_with": "value"}, (node.ends_with("value")).to_param())

    def test_text_node_contains(self):
        node = Search.TextNodeBuilder("name")
        self.assertEquals({"contains": "value"}, (node.contains("value")).to_param())

    def test_multiple_value_node_in_list(self):
        node = Search.MultipleValueNodeBuilder("name")
        self.assertEquals(["value1", "value2"], (node.in_list(["value1", "value2"])).to_param())

    def test_multiple_value_node_in_list_as_arg_list(self):
        node = Search.MultipleValueNodeBuilder("name")
        self.assertEquals(["value1", "value2"], (node.in_list("value1", "value2")).to_param())

    def test_multiple_value_node_is(self):
        node = Search.MultipleValueNodeBuilder("name")
        self.assertEquals(["value1"], (node == "value1").to_param())

    def test_multiple_value_node_with_value_in_whitelist(self):
        node = Search.MultipleValueNodeBuilder("name", ["okay"])
        self.assertEquals(["okay"], (node == "okay").to_param())

    @raises(AttributeError)
    def test_multiple_value_node_with_value_not_in_whitelist(self):
        node = Search.MultipleValueNodeBuilder("name", ["okay", "also okay"])
        node == "not okay"

    def test_multiple_value_or_text_node_is(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals({"is": "value"}, (node == "value").to_param())

    def test_multiple_value_or_text_node_is_not(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals({"is_not": "value"}, (node != "value").to_param())

    def test_multiple_value_or_text_node_starts_with(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals({"starts_with": "value"}, (node.starts_with("value")).to_param())

    def test_multiple_value_or_text_node_ends_with(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals({"ends_with": "value"}, (node.ends_with("value")).to_param())

    def test_multiple_value_or_text_node_contains(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals({"contains": "value"}, (node.contains("value")).to_param())

    def test_multiple_value_or_text_node_in_list(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals(["value1", "value2"], (node.in_list(["value1", "value2"])).to_param())

    def test_multiple_value_or_text_node_in_list_as_arg_list(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals(["value1", "value2"], (node.in_list("value1", "value2")).to_param())

    def test_multiple_value_or_text_node_is(self):
        node = Search.MultipleValueOrTextNodeBuilder("name")
        self.assertEquals({"is": "value1"}, (node == "value1").to_param())

    def test_multiple_value_or_text_node_with_value_in_whitelist(self):
        node = Search.MultipleValueOrTextNodeBuilder("name", ["okay"])
        self.assertEquals(["okay"], node.in_list("okay").to_param())

    @raises(AttributeError)
    def test_multiple_value_or_text_node_with_value_not_in_whitelist(self):
        node = Search.MultipleValueOrTextNodeBuilder("name", ["okay"])
        node.in_list("not okay").to_param()

    def test_range_node_min_ge(self):
        node = Search.RangeNodeBuilder("name")
        self.assertEquals({"min": "value"}, (node >= "value").to_param())

    def test_range_node_min_greater_than_or_equal_to(self):
        node = Search.RangeNodeBuilder("name")
        self.assertEquals({"min": "value"}, (node.greater_than_or_equal_to("value")).to_param())

    def test_range_node_max_le(self):
        node = Search.RangeNodeBuilder("name")
        self.assertEquals({"max": "value"}, (node <= "value").to_param())

    def test_range_node_max_less_than_or_equal_to(self):
        node = Search.RangeNodeBuilder("name")
        self.assertEquals({"max": "value"}, (node.less_than_or_equal_to("value")).to_param())

    def test_range_node_between(self):
        node = Search.RangeNodeBuilder("name")
        self.assertEquals({"min": "min_value", "max": "max_value"}, (node.between("min_value", "max_value")).to_param())

    def test_range_node_is(self):
        node = Search.RangeNodeBuilder("name")
        self.assertEquals({"is": "value"}, (node == "value").to_param())

    def test_key_value_node_is_eq(self):
        node = Search.KeyValueNodeBuilder("name")
        self.assertEquals(True, (node == True).to_param())

    def test_key_value_node_is_equal(self):
        node = Search.KeyValueNodeBuilder("name")
        self.assertEquals(True, (node.is_equal(True)).to_param())

    def test_key_value_node_is_not_equal(self):
        node = Search.KeyValueNodeBuilder("name")
        self.assertEquals(False, (node.is_not_equal(True)).to_param())

    def test_key_value_node_is_not_equal(self):
        node = Search.KeyValueNodeBuilder("name")
        self.assertEquals(False, (node != True).to_param())


########NEW FILE########
__FILENAME__ = test_signature_service
from tests.test_helper import *

class FakeDigest(object):

    @staticmethod
    def hmac_hash(key, data):
        return "%s_signed_with_%s" % (data, key)

class TestSignatureService(unittest.TestCase):

    def test_hashes_with_digest(self):
        signature_service = SignatureService("fake_key", FakeDigest.hmac_hash)
        signed = signature_service.sign({"foo": "bar"})
        self.assertEquals("foo=bar_signed_with_fake_key|foo=bar", signed)

########NEW FILE########
__FILENAME__ = test_subscription
from tests.test_helper import *

class TestSubscription(unittest.TestCase):
    def test_create_raises_exception_with_bad_keys(self):
        try:
            Subscription.create({"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_update_raises_exception_with_bad_keys(self):
        try:
            Subscription.update("id", {"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_finding_empty_id_raises_not_found_exception(self):
        try:
            Subscription.find(" ")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertTrue(True)

########NEW FILE########
__FILENAME__ = test_subscription_search
from tests.test_helper import *

class TestSubscriptionSearch(unittest.TestCase):
    def test_billing_cycles_remaining_is_a_range_node(self):
        self.assertEquals(Search.RangeNodeBuilder, type(SubscriptionSearch.billing_cycles_remaining))

    def test_days_past_due_is_a_range_node(self):
        self.assertEquals(Search.RangeNodeBuilder, type(SubscriptionSearch.days_past_due))

    def test_id_is_a_text_node(self):
        self.assertEquals(Search.TextNodeBuilder, type(SubscriptionSearch.id))

    def test_merchant_account_id_is_a_multiple_value_node(self):
        self.assertEquals(Search.MultipleValueNodeBuilder, type(SubscriptionSearch.merchant_account_id))

    def test_plan_id_is_a_multiple_value_or_text_node(self):
        self.assertEquals(Search.MultipleValueOrTextNodeBuilder, type(SubscriptionSearch.plan_id))

    def test_price_is_a_range_node(self):
        self.assertEquals(Search.RangeNodeBuilder, type(SubscriptionSearch.price))

    def test_status_is_a_multiple_value_node(self):
        self.assertEquals(Search.MultipleValueNodeBuilder, type(SubscriptionSearch.status))

    def test_in_trial_period_is_multiple_value_node(self):
        self.assertEquals(Search.MultipleValueNodeBuilder, type(SubscriptionSearch.in_trial_period))

    def test_status_whitelist(self):
        SubscriptionSearch.status.in_list(
            Subscription.Status.Active,
            Subscription.Status.Canceled,
            Subscription.Status.Expired,
            Subscription.Status.PastDue
        )

    @raises(AttributeError)
    def test_status_not_in_whitelist(self):
        SubscriptionSearch.status.in_list(
            Subscription.Status.Active,
            Subscription.Status.Canceled,
            Subscription.Status.Expired,
            "not a status"
        )

    def test_ids_is_a_multiple_value_node(self):
        self.assertEquals(Search.MultipleValueNodeBuilder, type(SubscriptionSearch.ids))

########NEW FILE########
__FILENAME__ = test_successful_result
from tests.test_helper import *

class TestSuccessfulResult(unittest.TestCase):
    def test_is_success(self):
        self.assertTrue(SuccessfulResult({}).is_success)

    def test_attributes_are_exposed(self):
        result = SuccessfulResult({"name": "drew"})
        self.assertEqual("drew", result.name)


########NEW FILE########
__FILENAME__ = test_transaction
from tests.test_helper import *
from datetime import datetime
from datetime import date

class TestTransaction(unittest.TestCase):
    def test_clone_transaction_raises_exception_with_bad_keys(self):
        try:
            Transaction.clone_transaction("an id", {"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_sale_raises_exception_with_bad_keys(self):
        try:
            Transaction.sale({"bad_key": "value"})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_sale_raises_exception_with_nested_bad_keys(self):
        try:
            Transaction.sale({"credit_card": {"bad_key": "value"}})
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: credit_card[bad_key]'", str(e))

    def test_tr_data_for_sale_raises_error_with_bad_keys(self):
        try:
            Transaction.tr_data_for_sale({"bad_key": "value"}, "http://example.com")
            self.assertTrue(False)
        except KeyError, e:
            self.assertEquals("'Invalid keys: bad_key'", str(e))

    def test_finding_empty_id_raises_not_found_exception(self):
        try:
            Transaction.find(" ")
            self.assertTrue(False)
        except NotFoundError, e:
            self.assertTrue(True)

    def test_constructor_includes_disbursement_information(self):
        attributes = {
            'amount': '27.00',
            'tax_amount': '1.00',
            'customer_id': '4096',
            'merchant_account_id': '8192',
            'order_id': '106601',
            'channel': '101',
            'payment_method_token': 'sometoken',
            'purchase_order_number': '20202',
            'recurring': 'False',
            'disbursement_details': {
                'settlement_amount': '27.00',
                'settlement_currency_iso_code': 'USD',
                'settlement_currency_exchange_rate': '1',
                'disbursement_date': date(2013, 4, 10),
                'funds_held': False
            }
        }

        tran = Transaction(None, attributes)

        self.assertEquals(tran.disbursement_details.settlement_amount, Decimal('27.00'))
        self.assertEquals(tran.disbursement_details.settlement_currency_iso_code, 'USD')
        self.assertEquals(tran.disbursement_details.settlement_currency_exchange_rate, Decimal('1'))
        self.assertEquals(tran.disbursement_details.disbursement_date, date(2013, 4, 10))
        self.assertEquals(tran.disbursement_details.funds_held, False)
        self.assertEquals(tran.is_disbursed, True)

    def test_is_disbursed_false(self):
        attributes = {
            'amount': '27.00',
            'tax_amount': '1.00',
            'customer_id': '4096',
            'merchant_account_id': '8192',
            'order_id': '106601',
            'channel': '101',
            'payment_method_token': 'sometoken',
            'purchase_order_number': '20202',
            'recurring': 'False',
            'disbursement_details': {
                'settlement_amount': None,
                'settlement_currency_iso_code': None,
                'settlement_currency_exchange_rate': None,
                'disbursement_date': None,
                'funds_held': None,
            }
        }

        tran = Transaction(None, attributes)

        self.assertEquals(tran.is_disbursed, False)

########NEW FILE########
__FILENAME__ = test_transparent_redirect
from tests.test_helper import *

class TestTransparentRedirect(unittest.TestCase):
    def test_tr_data(self):
        data = TransparentRedirect.tr_data({"key": "val"}, "http://example.com/path?foo=bar")
        self.__assert_valid_tr_data(data)

    def __assert_valid_tr_data(self, data):
        hash, content = data.split("|", 1)
        self.assertEquals(hash, Crypto.sha1_hmac_hash(Configuration.private_key, content))

    @raises(ForgedQueryStringError)
    def test_parse_and_validate_query_string_raises_for_invalid_hash(self):
        Configuration.gateway().transparent_redirect._parse_and_validate_query_string(
            "http_status=200&id=7kdj469tw7yck32j&hash=99c9ff20cd7910a1c1e793ff9e3b2d15586dc6b9"
        )

    @raises(AuthenticationError)
    def test_parse_and_validate_query_string_raises_for_http_status_401(self):
        Configuration.gateway().transparent_redirect._parse_and_validate_query_string(
            "http_status=401&id=6kdj469tw7yck32j&hash=5a26e3cde5ebedb0ec1ba8d35724360334fbf419"
        )

    @raises(AuthorizationError)
    def test_parse_and_validate_query_string_raises_for_http_status_403(self):
        Configuration.gateway().transparent_redirect._parse_and_validate_query_string(
            "http_status=403&id=6kdj469tw7yck32j&hash=126d5130b71a4907e460fad23876ed70dd41dcd2"
        )

    @raises(NotFoundError)
    def test_parse_and_validate_query_string_raises_for_http_status_404(self):
        Configuration.gateway().transparent_redirect._parse_and_validate_query_string(
            "http_status=404&id=6kdj469tw7yck32j&hash=0d3724a45cf1cda5524aa68f1f28899d34d2ff3a"
        )

    @raises(ServerError)
    def test_parse_and_validate_query_string_raises_for_http_status_500(self):
        Configuration.gateway().transparent_redirect._parse_and_validate_query_string(
            "http_status=500&id=6kdj469tw7yck32j&hash=a839a44ca69d59a3d6f639c294794989676632dc"
        )

    @raises(DownForMaintenanceError)
    def test_parse_and_validate_query_string_raises_for_http_status_503(self):
        Configuration.gateway().transparent_redirect._parse_and_validate_query_string(
            "http_status=503&id=6kdj469tw7yck32j&hash=1b3d29199a282e63074a7823b76bccacdf732da6"
        )

    @raises(UnexpectedError)
    def test_parse_and_validate_query_string_raises_for_unexpected_http_status(self):
        Configuration.gateway().transparent_redirect._parse_and_validate_query_string(
            "http_status=600&id=6kdj469tw7yck32j&hash=740633356f93384167d887de0c1d9745e3de8fb6"
        )

    def test_api_version(self):
        data = TransparentRedirect.tr_data({"key": "val"}, "http://example.com/path?foo=bar")
        self.assertTrue("api_version=3" in data)

########NEW FILE########
__FILENAME__ = test_validation_error_collection
from tests.test_helper import *

class TestValidationErrorCollection(unittest.TestCase):
    def test_it_builds_an_array_of_errors_given_an_array_of_hashes(self):
        hash = {"errors": [{"attribute": "some model attribute", "code": 1, "message": "bad juju"}]}
        errors = ValidationErrorCollection(hash)
        error = errors[0]
        self.assertEquals("some model attribute", error.attribute)
        self.assertEquals(1, error.code)
        self.assertEquals("bad juju", error.message)

    def test_for_object_provides_access_to_nested_attributes(self):
        hash = {
            "errors": [{"attribute": "some model attribute", "code": 1, "message": "bad juju"}],
            "nested": {
                "errors": [{"attribute": "number", "code": 2, "message": "badder juju"}]
            }
        }
        errors = ValidationErrorCollection(hash)
        error = errors.for_object("nested").on("number")[0]

        self.assertEquals("number", error.attribute)
        self.assertEquals(2, error.code)
        self.assertEquals("badder juju", error.message)

    def test_deep_size_non_nested(self):
        hash = {
            "errors": [
                {"attribute": "one", "code": 1, "message": "is too long"},
                {"attribute": "two", "code": 2, "message": "contains invalid chars"},
                {"attribute": "thr", "code": 3, "message": "is invalid"}
            ]
        }

        self.assertEquals(3, ValidationErrorCollection(hash).deep_size)

    def test_deep_size_nested(self):
        hash = {
            "errors": [{"attribute": "one", "code": 1, "message": "is too long"}],
            "nested": {
                "errors": [{"attribute": "two", "code": 2, "message": "contains invalid chars"}]
            }
        }

        self.assertEquals(2, ValidationErrorCollection(hash).deep_size)

    def test_deep_size_multiple_nestings(self):
        hash = {
            "errors": [{"attribute": "one", "code": 1, "message": "is too long"}],
            "nested": {
                "errors": [{"attribute": "two", "code": 2, "message": "contains invalid chars"}],
                "nested_again": {
                    "errors": [
                        {"attribute": "three", "code": 3, "message": "super nested"},
                        {"attribute": "four", "code": 4, "message": "super nested 2"}
                    ]
                }
            }
        }

        self.assertEquals(4, ValidationErrorCollection(hash).deep_size)

    def test_len_multiple_nestings(self):
        hash = {
            "errors": [{"attribute": "one", "code": 1, "message": "is too long"}],
            "nested": {
                "errors": [{"attribute": "two", "code": 2, "message": "contains invalid chars"}],
                "nested_again": {
                    "errors": [
                        {"attribute": "three", "code": 3, "message": "super nested"},
                        {"attribute": "four", "code": 4, "message": "super nested 2"}
                    ]
                }
            }
        }
        validation_error_collection = ValidationErrorCollection(hash)
        self.assertEquals(1, len(validation_error_collection))
        self.assertEquals(1, len(validation_error_collection.for_object("nested")))
        self.assertEquals(2, len(validation_error_collection.for_object("nested").for_object("nested_again")))

    def test_deep_errors(self):
        hash = {
            "errors": [{"attribute": "one", "code": 1, "message": "is too long"}],
            "nested": {
                "errors": [{"attribute": "two", "code": 2, "message": "contains invalid chars"}],
                "nested_again": {
                    "errors": [
                        {"attribute": "three", "code": 3, "message": "super nested"},
                        {"attribute": "four", "code": 4, "message": "super nested 2"}
                    ]
                }
            }
        }
        validation_error_collection = ValidationErrorCollection(hash)
        self.assertEquals([1, 2, 3, 4], [error.code for error in validation_error_collection.deep_errors])

    def test_errors(self):
        hash = {
            "errors": [{"attribute": "one", "code": 1, "message": "is too long"}],
            "nested": {
                "errors": [{"attribute": "two", "code": 2, "message": "contains invalid chars"}],
                "nested_again": {
                    "errors": [
                        {"attribute": "three", "code": 3, "message": "super nested"},
                        {"attribute": "four", "code": 4, "message": "super nested 2"}
                    ]
                }
            }
        }
        validation_error_collection = ValidationErrorCollection(hash)

        self.assertEquals([1], [error.code for error in validation_error_collection.errors])

        self.assertEquals([2], [error.code for error in validation_error_collection.for_object("nested").errors])
        self.assertEquals([3,4], [error.code for error in validation_error_collection.for_object("nested").for_object("nested_again").errors])

########NEW FILE########
__FILENAME__ = test_webhooks
from tests.test_helper import *

class TestWebhooks(unittest.TestCase):
    def test_sample_notification_builds_a_parsable_notification(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubscriptionWentPastDue,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.SubscriptionWentPastDue, notification.kind)
        self.assertEquals("my_id", notification.subscription.id)
        self.assertTrue((datetime.utcnow() - notification.timestamp).seconds < 10)

    @raises(InvalidSignatureError)
    def test_completely_invalid_signature(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubscriptionWentPastDue,
            "my_id"
        )

        WebhookNotification.parse("bad_stuff", payload)

    def test_parse_raises_when_public_key_is_wrong(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubscriptionWentPastDue,
            "my_id"
        )

        config = Configuration(
            environment=Environment.Development,
            merchant_id="integration_merchant_id",
            public_key="wrong_public_key",
            private_key="wrong_private_key"
        )
        gateway = BraintreeGateway(config)

        try:
            gateway.webhook_notification.parse(signature, payload)
        except InvalidSignatureError, e:
            self.assertEquals("no matching public key", e.message)
        else:
            self.assertFalse("raises exception")

    def test_invalid_signature_when_payload_modified(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubscriptionWentPastDue,
            "my_id"
        )

        try:
            WebhookNotification.parse(signature, "badstuff" + payload)
        except InvalidSignatureError, e:
            self.assertEquals("signature does not match payload - one has been modified", e.message)
        else:
            self.assertFalse("raises exception")

    def test_invalid_signature_when_contains_invalid_characters(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubscriptionWentPastDue,
            "my_id"
        )

        try:
            WebhookNotification.parse(signature, "~* invalid! *~")
        except InvalidSignatureError, e:
            self.assertEquals("payload contains illegal characters", e.message)
        else:
            self.assertFalse("raises exception")

    def test_parse_allows_all_valid_characters(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubscriptionWentPastDue,
            "my_id"
        )

        try:
            WebhookNotification.parse(signature, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+=/\n")
        except InvalidSignatureError, e:
            self.assertNotEquals("payload contains illegal characters", e.message)

    def test_parse_retries_payload_with_a_newline(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubscriptionWentPastDue,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload.rstrip())

        self.assertEquals(WebhookNotification.Kind.SubscriptionWentPastDue, notification.kind)
        self.assertEquals("my_id", notification.subscription.id)
        self.assertTrue((datetime.utcnow() - notification.timestamp).seconds < 10)

    def test_verify_returns_a_correct_challenge_response(self):
        response = WebhookNotification.verify("verification_token")
        self.assertEquals("integration_public_key|c9f15b74b0d98635cd182c51e2703cffa83388c3", response)

    def test_builds_notification_for_approved_sub_merchant_account(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubMerchantAccountApproved,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.SubMerchantAccountApproved, notification.kind)
        self.assertEquals("my_id", notification.merchant_account.id)
        self.assertEquals(MerchantAccount.Status.Active, notification.merchant_account.status)
        self.assertEquals("master_ma_for_my_id", notification.merchant_account.master_merchant_account.id)
        self.assertEquals(MerchantAccount.Status.Active, notification.merchant_account.master_merchant_account.status)

    def test_builds_notification_for_declined_sub_merchant_account(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.SubMerchantAccountDeclined,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.SubMerchantAccountDeclined, notification.kind)
        self.assertEquals("my_id", notification.merchant_account.id)
        self.assertEquals(MerchantAccount.Status.Suspended, notification.merchant_account.status)
        self.assertEquals("master_ma_for_my_id", notification.merchant_account.master_merchant_account.id)
        self.assertEquals(MerchantAccount.Status.Suspended, notification.merchant_account.master_merchant_account.status)
        self.assertEquals("Credit score is too low", notification.message)
        self.assertEquals(ErrorCodes.MerchantAccount.DeclinedOFAC, notification.errors.for_object("merchant_account").on("base")[0].code)

    def test_builds_notification_for_disbursed_transactions(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.TransactionDisbursed,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.TransactionDisbursed, notification.kind)
        self.assertEquals("my_id", notification.transaction.id)
        self.assertEquals(100, notification.transaction.amount)
        self.assertEquals(datetime(2013, 7, 9, 18, 23, 29), notification.transaction.disbursement_details.disbursement_date)

    def test_builds_notification_for_disbursements(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.Disbursement,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.Disbursement, notification.kind)
        self.assertEquals("my_id", notification.disbursement.id)
        self.assertEquals(100, notification.disbursement.amount)
        self.assertEquals(None, notification.disbursement.exception_message)
        self.assertEquals(None, notification.disbursement.follow_up_action)
        self.assertEquals(date(2014, 2, 9), notification.disbursement.disbursement_date)

    def test_builds_notification_for_disbursement_exceptions(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.DisbursementException,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.DisbursementException, notification.kind)
        self.assertEquals("my_id", notification.disbursement.id)
        self.assertEquals(100, notification.disbursement.amount)
        self.assertEquals("bank_rejected", notification.disbursement.exception_message)
        self.assertEquals("update_funding_information", notification.disbursement.follow_up_action)
        self.assertEquals(date(2014, 2, 9), notification.disbursement.disbursement_date)

    def test_builds_notification_for_partner_merchant_connected(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.PartnerMerchantConnected,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.PartnerMerchantConnected, notification.kind)
        self.assertEquals("abc123", notification.partner_merchant.partner_merchant_id)
        self.assertEquals("public_key", notification.partner_merchant.public_key)
        self.assertEquals("private_key", notification.partner_merchant.private_key)
        self.assertEquals("public_id", notification.partner_merchant.merchant_public_id)
        self.assertEquals("cse_key", notification.partner_merchant.client_side_encryption_key)
        self.assertTrue((datetime.utcnow() - notification.timestamp).seconds < 10)

    def test_builds_notification_for_partner_merchant_disconnected(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.PartnerMerchantDisconnected,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.PartnerMerchantDisconnected, notification.kind)
        self.assertEquals("abc123", notification.partner_merchant.partner_merchant_id)
        self.assertTrue((datetime.utcnow() - notification.timestamp).seconds < 10)

    def test_builds_notification_for_partner_merchant_declined(self):
        signature, payload = WebhookTesting.sample_notification(
            WebhookNotification.Kind.PartnerMerchantDeclined,
            "my_id"
        )

        notification = WebhookNotification.parse(signature, payload)

        self.assertEquals(WebhookNotification.Kind.PartnerMerchantDeclined, notification.kind)
        self.assertEquals("abc123", notification.partner_merchant.partner_merchant_id)
        self.assertTrue((datetime.utcnow() - notification.timestamp).seconds < 10)

########NEW FILE########
__FILENAME__ = test_xml_util
from tests.test_helper import *

class TestXmlUtil(unittest.TestCase):
    def test_dict_from_xml_simple(self):
        xml = """
        <container>val</container>
        """
        expected = {"container": "val"}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_typecasts_ints(self):
        xml = """
        <container type="integer">1</container>
        """
        expected = {"container": 1}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_typecasts_nils(self):
        xml = """
        <root>
          <a_nil_value nil="true"></a_nil_value>
          <an_empty_string></an_empty_string>
        </root>
        """
        expected = {"root": {"a_nil_value": None, "an_empty_string": ""}}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_typecasts_booleans(self):
        xml = """
        <root>
          <casted-true type="boolean">true</casted-true>
          <casted-one type="boolean">1</casted-one>
          <casted-false type="boolean">false</casted-false>
          <casted-anything type="boolean">anything</casted-anything>
          <uncasted-true>true</uncasted-true>
        </root>
        """
        expected = {
            "root": {
                "casted_true": True,
                "casted_one": True,
                "casted_false": False,
                "casted_anything": False,
                "uncasted_true": "true"
            }
        }
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_typecasts_datetimes(self):
        xml = """
        <root>
          <created-at type="datetime">2009-10-28T10:19:49Z</created-at>
        </root>
        """
        expected = {"root": {"created_at": datetime(2009, 10, 28, 10, 19, 49)}}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_with_dashes(self):
        xml = """
        <my-item>val</my-item>
        """
        expected = {"my_item": "val"}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_nested(self):
        xml = """
        <container>
            <elem>val</elem>
        </container>
        """
        expected = {"container": {"elem": "val"}}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_array(self):
        xml = """
        <container>
            <elements type="array">
                <elem>val1</elem>
                <elem>val2</elem>
                <elem>val3</elem>
            </elements>
        </container>
        """
        expected = {"container": {"elements": ["val1", "val2", "val3"]}}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_with_empty_array(self):
        xml = """
        <container>
            <elements type="array" />
        </container>
        """
        expected = {"container": {"elements": []}}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_dict_from_xml_array_of_hashes(self):
        xml = """
        <container>
            <elements type="array">
                <elem><val>val1</val></elem>
                <elem><val>val2</val></elem>
                <elem><val>val3</val></elem>
            </elements>
        </container>
        """
        expected = {"container": {"elements": [{"val": "val1"}, {"val": "val2"}, {"val": "val3"}]}}
        self.assertEqual(expected, XmlUtil.dict_from_xml(xml))

    def test_xml_from_dict_escapes_keys_and_values(self):
        dict = {"k<ey": "va&lue"}
        self.assertEqual("<k&lt;ey>va&amp;lue</k&lt;ey>", XmlUtil.xml_from_dict(dict))

    def test_xml_from_dict_simple(self):
        dict = {"a": "b"}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_with_integer(self):
        dict = {"a": 1}
        self.assertEqual('<a type="integer">1</a>', XmlUtil.xml_from_dict(dict))

    def test_xml_from_dict_with_long(self):
        dict = {"a": 12341234123412341234}
        self.assertEqual('<a type="integer">12341234123412341234</a>', XmlUtil.xml_from_dict(dict))

    def test_xml_from_dict_with_boolean(self):
        dict = {"a": True}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_simple_xml_and_back_twice(self):
        dict = {"a": "b"}
        self.assertEqual(dict, self.__xml_and_back(self.__xml_and_back(dict)))

    def test_xml_from_dict_nested(self):
        dict = {"container": {"item": "val"}}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_with_array(self):
        dict = {"container": {"elements": ["val1", "val2", "val3"]}}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_with_array_of_hashes(self):
        dict = {"container": {"elements": [{"val": "val1"}, {"val": "val2"}, {"val": "val3"}]}}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_retains_underscores(self):
        dict = {"container": {"my_element": "val"}}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_escapes_special_chars(self):
        dict = {"container": {"element": "<&>'\""}}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_with_datetime(self):
        dict = {"a": datetime(2010, 1, 2, 3, 4, 5)}
        self.assertEqual(dict, self.__xml_and_back(dict))

    def test_xml_from_dict_with_unicode_characters(self):
        dict = {"a": u"\u1f61hat?"}
        self.assertEqual('<a>&#8033;hat?</a>', XmlUtil.xml_from_dict(dict))

    def test_xml_from_dict_with_dates_formats_as_datetime(self):
        dict = {"a": date(2010, 1, 2)}
        self.assertEqual('<a type="datetime">2010-01-02T00:00:00Z</a>', XmlUtil.xml_from_dict(dict))

    def __xml_and_back(self, dict):
        return XmlUtil.dict_from_xml(XmlUtil.xml_from_dict(dict))

########NEW FILE########
__FILENAME__ = test_constants
from tests.test_helper import *

class TestConstants(unittest.TestCase):
    def test_get_all_constant_values_from_class(self):
        self.assertEquals(["Active", "Canceled", "Expired", "Past Due", "Pending"], Constants.get_all_constant_values_from_class(Subscription.Status))

########NEW FILE########
