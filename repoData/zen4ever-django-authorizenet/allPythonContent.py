__FILENAME__ = admin
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from authorizenet.models import (Response, CIMResponse, CustomerProfile,
                                 CustomerPaymentProfile)
from authorizenet.forms import CustomerPaymentForm, CustomerPaymentAdminForm
from relatives.utils import object_edit_link


class ResponseAdmin(admin.ModelAdmin):
    list_display = ['response_code',
                    'response_reason_text',
                    'auth_code',
                    'trans_id']

    readonly_fields = ['response_code',
                       'response_subcode',
                       'response_reason_code',
                       'response_reason_text',
                       'auth_code',
                       'avs_code',
                       'trans_id',
                       'invoice_num',
                       'description',
                       'amount',
                       'method',
                       'type',
                       'cust_id',
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
                       'email',
                       'ship_to_first_name',
                       'ship_to_last_name',
                       'ship_to_company',
                       'ship_to_address',
                       'ship_to_city',
                       'ship_to_state',
                       'ship_to_zip',
                       'ship_to_country',
                       'tax',
                       'duty',
                       'freight',
                       'tax_exempt',
                       'po_num',
                       'MD5_Hash',
                       'cvv2_resp_code',
                       'cavv_response',
                       'test_request',
                       'card_type',
                       'account_number',
                       'created']

admin.site.register(Response, ResponseAdmin)


class CIMResponseAdmin(admin.ModelAdmin):
    list_display = ['result_code',
                    'result']

    readonly_fields = ['result',
                       'result_code',
                       'result_text',
                       'response_link',
                       'created']

    exclude = ['transaction_response']

    def response_link(self, obj):
        change_url = reverse('admin:authorizenet_response_change',
                args=(obj.transaction_response.id,))
        return mark_safe('<a href="%s">%s</a>' % (change_url,
            obj.transaction_response))
    response_link.short_description = 'transaction response'

admin.site.register(CIMResponse, CIMResponseAdmin)


class CustomerPaymentProfileInline(admin.TabularInline):
    model = CustomerPaymentProfile
    form = CustomerPaymentForm
    fields = [object_edit_link("Edit"), 'first_name', 'last_name',
              'card_number', 'expiration_date']
    readonly_fields = fields
    extra = 0
    max_num = 0
    can_delete = False


class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['profile_id', 'customer']
    readonly_fields = ['profile_id', 'customer']
    inlines = [CustomerPaymentProfileInline]

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj is not None else ['profile_id']

admin.site.register(CustomerProfile, CustomerProfileAdmin)


class CustomerPaymentProfileAdmin(admin.ModelAdmin):
    list_display = ['payment_profile_id', 'customer_profile', 'customer']
    readonly_fields = ['payment_profile_id', 'customer', 'customer_profile']
    form = CustomerPaymentAdminForm

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj is not None else []

admin.site.register(CustomerPaymentProfile, CustomerPaymentProfileAdmin)

########NEW FILE########
__FILENAME__ = cim
import re
import xml.dom.minidom

from django.utils.datastructures import SortedDict
from authorizenet.conf import settings
import requests

from authorizenet import AUTHNET_CIM_URL, AUTHNET_TEST_CIM_URL
from authorizenet.signals import customer_was_created, customer_was_flagged, \
        payment_was_successful, payment_was_flagged


BILLING_FIELDS = ('firstName',
                  'lastName',
                  'company',
                  'address',
                  'city',
                  'state',
                  'zip',
                  'country',
                  'phoneNumber',
                  'faxNumber')

SHIPPING_FIELDS = ('firstName',
                   'lastName',
                   'company',
                   'address',
                   'city',
                   'state',
                   'zip',
                   'country')

CREDIT_CARD_FIELDS = ('cardNumber',
                      'expirationDate',
                      'cardCode')


def extract_form_data(data):
    """
    Convert all keys in data dictionary from underscore_format to
    camelCaseFormat and return the new dict
    """
    to_upper = lambda match: match.group(1).upper()
    to_camel = lambda x: re.sub("_([a-z])", to_upper, x)
    return dict(map(lambda x: (to_camel(x[0]), x[1]), data.items()))


def extract_payment_form_data(data):
    payment_data = extract_form_data(data)
    if payment_data.get('expirationDate') is not None:
        payment_data['expirationDate'] = \
                payment_data['expirationDate'].strftime('%Y-%m')
    return payment_data


def create_form_data(data):
    """
    Convert all keys in data dictionary from camelCaseFormat to
    underscore_format and return the new dict
    """
    to_lower = lambda match: "_" + match.group(1).lower()
    to_under = lambda x: re.sub("([A-Z])", to_lower, x)
    return dict(map(lambda x: (to_under(x[0]), x[1]), data.items()))


def add_profile(customer_id, payment_form_data, billing_form_data,
                shipping_form_data=None, customer_email=None,
                customer_description=None):
    """
    Add a customer profile with a single payment profile
    and return a tuple of the CIMResponse, profile ID,
    and single-element list of payment profile IDs.

    Arguments (required):
    customer_id -- unique merchant-assigned customer identifier
    payment_form_data -- dictionary with keys in CREDIT_CARD_FIELDS
    billing_form_data -- dictionary with keys in BILLING_FIELDS
    shipping_form_data -- dictionary with keys in SHIPPING_FIELDS

    Keyword Arguments (optional):
    customer_email -- customer email
    customer_description -- customer description
    """
    kwargs = {'customer_id': customer_id,
              'credit_card_data': extract_payment_form_data(payment_form_data),
              'billing_data': extract_form_data(billing_form_data),
              'customer_email': customer_email,
              'customer_description': customer_description}
    if shipping_form_data:
        kwargs['shipping_data'] = extract_form_data(shipping_form_data)
    helper = CreateProfileRequest(**kwargs)
    response = helper.get_response()
    info = helper.customer_info
    if response.success:
        profile_id = helper.profile_id
        payment_profile_ids = helper.payment_profile_ids
        shipping_profile_ids = helper.shipping_profile_ids
        customer_was_created.send(sender=response,
                                  customer_id=info.get("merchantCustomerId"),
                                  customer_description=info.get("description"),
                                  customer_email=info.get("email"),
                                  profile_id=helper.profile_id,
                                  payment_profile_ids=helper.payment_profile_ids)
    else:
        profile_id = None
        payment_profile_ids = None
        shipping_profile_ids = None
        customer_was_flagged.send(sender=response,
                                  customer_id=customer_id)
    return {'response': response,
            'profile_id': profile_id,
            'payment_profile_ids': payment_profile_ids,
            'shipping_profile_ids': shipping_profile_ids}


def delete_profile(profile_id):
    """
    Delete a customer profile and return the CIMResponse.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    """
    helper = DeleteProfileRequest(profile_id)
    response = helper.get_response()
    return response


def update_payment_profile(profile_id,
                           payment_profile_id,
                           payment_form_data,
                           billing_form_data):
    """
    Update a customer payment profile and return the CIMResponse.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    payment_profile_id -- unique gateway-assigned payment profile identifier
    payment_form_data -- dictionary with keys in CREDIT_CARD_FIELDS
    billing_form_data -- dictionary with keys in BILLING_FIELDS
    """
    payment_data = extract_payment_form_data(payment_form_data)
    billing_data = extract_form_data(billing_form_data)
    helper = UpdatePaymentProfileRequest(profile_id,
                                         payment_profile_id,
                                         billing_data,
                                         payment_data)
    response = helper.get_response()
    return response


def create_payment_profile(profile_id, payment_form_data, billing_form_data):
    """
    Create a customer payment profile and return a tuple of the CIMResponse and
    payment profile ID.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    payment_form_data -- dictionary with keys in CREDIT_CARD_FIELDS
    billing_form_data -- dictionary with keys in BILLING_FIELDS
    """
    payment_data = extract_payment_form_data(payment_form_data)
    billing_data = extract_form_data(billing_form_data)
    helper = CreatePaymentProfileRequest(profile_id,
                                         billing_data,
                                         payment_data)
    response = helper.get_response()
    if response.success:
        payment_profile_id = helper.payment_profile_id
    else:
        payment_profile_id = None
    return {'response': response, 'payment_profile_id': payment_profile_id}


def delete_payment_profile(profile_id, payment_profile_id):
    """
    Delete a customer payment profile and return the CIMResponse.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    payment_profile_id -- unique gateway-assigned payment profile identifier
    """
    helper = DeletePaymentProfileRequest(profile_id, payment_profile_id)
    response = helper.get_response()
    return response


def update_shipping_profile(profile_id,
                            shipping_profile_id,
                            shipping_form_data):
    """
    Update a customer shipping profile and return the CIMResponse.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    shipping_profile_id -- unique gateway-assigned shipping profile identifier
    shipping_form_data -- dictionary with keys in SHIPPING_FIELDS
    """
    shipping_data = extract_form_data(shipping_form_data)
    helper = UpdateShippingProfileRequest(profile_id,
                                          shipping_profile_id,
                                          shipping_data)
    response = helper.get_response()
    return response


def create_shipping_profile(profile_id, shipping_form_data):
    """
    Create a customer shipping profile and return a tuple of the CIMResponse and
    shipping profile ID.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    shipping_form_data -- dictionary with keys in SHIPPING_FIELDS
    """
    shipping_data = extract_form_data(shipping_form_data)
    helper = CreateShippingProfileRequest(profile_id,
                                          shipping_data)
    response = helper.get_response()
    if response.success:
        shipping_profile_id = helper.shipping_profile_id
    else:
        shipping_profile_id = None
    return {'response': response, 'shipping_profile_id': shipping_profile_id}


def delete_shipping_profile(profile_id, shipping_profile_id):
    """
    Delete a customer shipping profile and return the CIMResponse.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    shipping_profile_id -- unique gateway-assigned shipping profile identifier
    """
    helper = DeleteShippingProfileRequest(profile_id, shipping_profile_id)
    response = helper.get_response()
    return response


def get_profile(profile_id):
    """
    Retrieve a customer payment profile from the profile ID and return a tuple
    of the CIMResponse and two lists of dictionaries containing data for each
    payment and shipping profile.

    Arguments:
    profile_id -- unique gateway-assigned profile identifier
    """
    helper = GetProfileRequest(profile_id)
    response = helper.get_response()
    return {'response': response,
            'payment_profiles': helper.payment_profiles,
            'shipping_profiles': helper.shipping_profiles}


def process_transaction(*args, **kwargs):
    """
    Retrieve a customer payment profile from the profile ID and return a tuple
    of the CIMResponse and a list of dictionaries containing data for each
    payment profile.

    See CreateTransactionRequest.__init__ for arguments and keyword arguments.
    """
    helper = CreateTransactionRequest(*args, **kwargs)
    response = helper.get_response()
    if response.transaction_response:
        if response.transaction_response.is_approved:
            payment_was_successful.send(sender=response.transaction_response)
        else:
            payment_was_flagged.send(sender=response.transaction_response)
    return response


class BaseRequest(object):
    """
    Abstract class used by all CIM request types
    """

    def __init__(self, action):
        self.create_base_document(action)
        if settings.DEBUG:
            self.endpoint = AUTHNET_TEST_CIM_URL
        else:
            self.endpoint = AUTHNET_CIM_URL

    def create_base_document(self, action):
        """
        Create base document and root node and store them in self.document
        and self.root respectively.  The root node is created based on the
        action parameter.  The required merchant authentication node is added
        to the document automatically.
        """
        doc = xml.dom.minidom.Document()
        namespace = "AnetApi/xml/v1/schema/AnetApiSchema.xsd"
        root = doc.createElementNS(namespace, action)
        root.setAttribute("xmlns", namespace)
        doc.appendChild(root)

        self.document = doc
        authentication = doc.createElement("merchantAuthentication")
        name = self.get_text_node("name", settings.LOGIN_ID)
        key = self.get_text_node("transactionKey",
                                 settings.TRANSACTION_KEY)
        authentication.appendChild(name)
        authentication.appendChild(key)
        root.appendChild(authentication)

        self.root = root

    def get_response(self):
        """
        Submit request to Authorize.NET CIM server and return the resulting
        CIMResponse
        """
        response = requests.post(
            self.endpoint,
            data=self.document.toxml().encode('utf-8'),
            headers={'Content-Type': 'text/xml'})
        text = response.text.encode('utf-8')
        response_xml = xml.dom.minidom.parseString(text)
        self.process_response(response_xml)
        return self.create_response_object()

    def get_text_node(self, node_name, text):
        """
        Create a text-only XML node called node_name
        with contents of text
        """
        node = self.document.createElement(node_name)
        node.appendChild(self.document.createTextNode(unicode(text)))
        return node

    def create_response_object(self):
        from authorizenet.models import CIMResponse
        return CIMResponse.objects.create(result=self.result,
                                          result_code=self.resultCode,
                                          result_text=self.resultText)

    def process_response(self, response):
        for e in response.childNodes[0].childNodes:
            if e.localName == 'messages':
                self.process_message_node(e)

    def process_message_node(self, node):
        for e in node.childNodes:
            if e.localName == 'resultCode':
                self.result = e.childNodes[0].nodeValue
            if e.localName == 'message':
                for f in e.childNodes:
                    if f.localName == 'code':
                        self.resultCode = f.childNodes[0].nodeValue
                    elif f.localName == 'text':
                        self.resultText = f.childNodes[0].nodeValue


class BasePaymentProfileRequest(BaseRequest):
    def get_payment_profile_node(self,
                                 billing_data,
                                 credit_card_data,
                                 node_name="paymentProfile"):
        payment_profile = self.document.createElement(node_name)

        if billing_data:
            bill_to = self.document.createElement("billTo")
            for key in BILLING_FIELDS:
                value = billing_data.get(key)
                if value is not None:
                    node = self.get_text_node(key, value)
                    bill_to.appendChild(node)
            payment_profile.appendChild(bill_to)

        payment = self.document.createElement("payment")
        credit_card = self.document.createElement("creditCard")
        for key in CREDIT_CARD_FIELDS:
            value = credit_card_data.get(key)
            if value is not None:
                node = self.get_text_node(key, value)
                credit_card.appendChild(node)
        payment.appendChild(credit_card)
        payment_profile.appendChild(payment)

        return payment_profile


class GetHostedProfilePageRequest(BaseRequest):
    """
    Request a token for retrieving a Hosted CIM form.

    Arguments (required):
    customer_profile_id -- the customer profile id

    Keyword Arguments (optional): Zero or more of:

    hostedProfileReturnUrl,
    hostedProfileReturnUrlText,
    hostedProfileHeadingBgColor,
    hostedProfilePageBorderVisible,
    hostedProfileIFrameCommunicatorUrl
    """
    def __init__(self, customer_profile_id, **settings):
        super(GetHostedProfilePageRequest,
              self).__init__('getHostedProfilePageRequest')
        self.root.appendChild(self.get_text_node('customerProfileId',
                                                 customer_profile_id))
        form_settings = self.document.createElement('hostedProfileSettings')
        for name, value in settings.iteritems():
            setting = self.document.createElement('setting')
            setting_name = self.get_text_node('settingName', name)
            setting_value = self.get_text_node('settingValue', value)
            setting.appendChild(setting_name)
            setting.appendChild(setting_value)
            form_settings.appendChild(setting)
        self.root.appendChild(form_settings)

    def process_response(self, response):
        self.profile_id = None
        self.payment_profile_id = None
        for e in response.childNodes[0].childNodes:
            if e.localName == 'messages':
                self.process_message_node(e)
            elif e.localName == 'token':
                self.token = e.childNodes[0].nodeValue


class BaseShippingProfileRequest(BaseRequest):
    def get_shipping_profile_node(self,
                                  shipping_data,
                                  node_name="shipToList"):
        shipping_profile = self.document.createElement(node_name)

        for key in SHIPPING_FIELDS:
            value = shipping_data.get(key)
            if value is not None:
                node = self.get_text_node(key, value)
                shipping_profile.appendChild(node)

        return shipping_profile


class CreateProfileRequest(BasePaymentProfileRequest,
                           BaseShippingProfileRequest):
    def __init__(self, customer_id=None, customer_email=None,
                 customer_description=None, billing_data=None,
                  shipping_data=None,credit_card_data=None):
        if not (customer_id or customer_email or customer_description):
            raise ValueError("%s requires one of 'customer_id', \
                             customer_email or customer_description"
                             % self.__class__.__name__)

        super(CreateProfileRequest,
              self).__init__("createCustomerProfileRequest")
        # order is important here, and OrderedDict not available < Python 2.7
        self.customer_info = SortedDict()
        self.customer_info['merchantCustomerId'] = customer_id
        self.customer_info['description'] = customer_description
        self.customer_info['email'] = customer_email
        profile_node = self.get_profile_node()
        if credit_card_data:
            payment_profiles = self.get_payment_profile_node(billing_data,
                                                             credit_card_data,
                                                             "paymentProfiles")
            profile_node.appendChild(payment_profiles)
        if shipping_data:
            shipping_profiles = self.get_shipping_profile_node(shipping_data,
                                                               "shipToList")
            profile_node.appendChild(shipping_profiles)
        self.root.appendChild(profile_node)

    def get_profile_node(self):
        profile = self.document.createElement("profile")
        for node_name, value in self.customer_info.items():
            if value:
                profile.appendChild(self.get_text_node(node_name, value))
        return profile

    def process_response(self, response):
        self.profile_id = None
        self.payment_profile_ids = None
        self.shipping_profile_ids = None
        for e in response.childNodes[0].childNodes:
            if e.localName == 'messages':
                self.process_message_node(e)
            elif e.localName == 'customerProfileId':
                self.profile_id = e.childNodes[0].nodeValue
            elif e.localName == 'customerPaymentProfileIdList':
                self.payment_profile_ids = []
                for f in e.childNodes:
                    self.payment_profile_ids.append(f.childNodes[0].nodeValue)
            elif e.localName == 'customerShippingAddressIdList':
                self.shipping_profile_ids = []
                for f in e.childNodes:
                    self.shipping_profile_ids.append(f.childNodes[0].nodeValue)


class DeleteProfileRequest(BaseRequest):
    """
    Deletes a Customer Profile

    Arguments:
    profile_id: The gateway-assigned customer ID.
    """
    def __init__(self, profile_id):
        super(DeleteProfileRequest,
              self).__init__("deleteCustomerProfileRequest")
        self.root.appendChild(self.get_text_node('customerProfileId',
                                                 profile_id))


class UpdatePaymentProfileRequest(BasePaymentProfileRequest):
    def __init__(self,
                 profile_id,
                 payment_profile_id,
                 billing_data=None,
                 credit_card_data=None):
        super(UpdatePaymentProfileRequest,
                self).__init__("updateCustomerPaymentProfileRequest")
        profile_id_node = self.get_text_node("customerProfileId", profile_id)
        payment_profile = self.get_payment_profile_node(billing_data,
                                                        credit_card_data,
                                                        "paymentProfile")
        payment_profile.appendChild(
                self.get_text_node("customerPaymentProfileId",
                                   payment_profile_id))
        self.root.appendChild(profile_id_node)
        self.root.appendChild(payment_profile)


class CreatePaymentProfileRequest(BasePaymentProfileRequest):
    def __init__(self, profile_id, billing_data=None, credit_card_data=None):
        super(CreatePaymentProfileRequest,
                self).__init__("createCustomerPaymentProfileRequest")
        profile_id_node = self.get_text_node("customerProfileId", profile_id)
        payment_profile = self.get_payment_profile_node(billing_data,
                                                        credit_card_data,
                                                        "paymentProfile")
        self.root.appendChild(profile_id_node)
        self.root.appendChild(payment_profile)

    def process_response(self, response):
        for e in response.childNodes[0].childNodes:
            if e.localName == 'messages':
                self.process_message_node(e)
            elif e.localName == 'customerPaymentProfileId':
                self.payment_profile_id = e.childNodes[0].nodeValue


class DeletePaymentProfileRequest(BasePaymentProfileRequest):
    def __init__(self, profile_id, payment_profile_id):
        super(DeletePaymentProfileRequest,
                self).__init__("deleteCustomerPaymentProfileRequest")
        profile_id_node = self.get_text_node("customerProfileId", profile_id)
        payment_profile_id_node = self.get_text_node(
                "customerPaymentProfileId",
                payment_profile_id)
        self.root.appendChild(profile_id_node)
        self.root.appendChild(payment_profile_id_node)


class UpdateShippingProfileRequest(BaseShippingProfileRequest):
    def __init__(self,
                 profile_id,
                 shipping_profile_id,
                 shipping_data=None,
                 credit_card_data=None):
        super(UpdateShippingProfileRequest,
                self).__init__("updateCustomerShippingAddressRequest")
        profile_id_node = self.get_text_node("customerProfileId", profile_id)
        shipping_profile = self.get_shipping_profile_node(shipping_data,
                                                          "address")
        shipping_profile.appendChild(
                self.get_text_node("customerAddressId",
                                   shipping_profile_id))
        self.root.appendChild(profile_id_node)
        self.root.appendChild(shipping_profile)


class CreateShippingProfileRequest(BaseShippingProfileRequest):
    def __init__(self, profile_id, shipping_data=None, credit_card_data=None):
        super(CreateShippingProfileRequest,
                self).__init__("createCustomerShippingAddressRequest")
        profile_id_node = self.get_text_node("customerProfileId", profile_id)
        shipping_profile = self.get_shipping_profile_node(shipping_data,
                                                          "address")
        self.root.appendChild(profile_id_node)
        self.root.appendChild(shipping_profile)

    def process_response(self, response):
        for e in response.childNodes[0].childNodes:
            if e.localName == 'messages':
                self.process_message_node(e)
            elif e.localName == 'customerAddressId':
                self.shipping_profile_id = e.childNodes[0].nodeValue


class DeleteShippingProfileRequest(BaseShippingProfileRequest):
    def __init__(self, profile_id, shipping_profile_id):
        super(DeleteShippingProfileRequest,
                self).__init__("deleteCustomerShippingAddressRequest")
        profile_id_node = self.get_text_node("customerProfileId", profile_id)
        shipping_profile_id_node = self.get_text_node(
                "customerAddressId",
                shipping_profile_id)
        self.root.appendChild(profile_id_node)
        self.root.appendChild(shipping_profile_id_node)


class GetProfileRequest(BaseRequest):
    def __init__(self, profile_id):
        super(GetProfileRequest, self).__init__("getCustomerProfileRequest")
        profile_id_node = self.get_text_node("customerProfileId", profile_id)
        self.root.appendChild(profile_id_node)

    def process_children(self, node, field_list):
        child_dict = {}
        for e in node.childNodes:
            if e.localName in field_list:
                if e.childNodes:
                    child_dict[e.localName] = e.childNodes[0].nodeValue
                else:
                    child_dict[e.localName] = ""
        return child_dict

    def extract_billing_data(self, node):
        return create_form_data(self.process_children(node, BILLING_FIELDS))

    def extract_credit_card_data(self, node):
        return create_form_data(
                self.process_children(node,
                CREDIT_CARD_FIELDS))

    def extract_payment_profiles_data(self, node):
        data = {}
        for e in node.childNodes:
            if e.localName == 'billTo':
                data['billing'] = self.extract_billing_data(e)
            if e.localName == 'payment':
                data['credit_card'] = self.extract_credit_card_data(
                        e.childNodes[0])
            if e.localName == 'customerPaymentProfileId':
                data['payment_profile_id'] = e.childNodes[0].nodeValue
        return data

    def extract_shipping_profiles_data(self, node):
        data = {}
        data['shipping'] = create_form_data(self.process_children(node, SHIPPING_FIELDS))
        for e in node.childNodes:
            if e.localName == 'customerAddressId':
                data['shipping_profile_id'] = e.childNodes[0].nodeValue
        return data

    def process_response(self, response):
        self.payment_profiles = []
        self.shipping_profiles = []
        for e in response.childNodes[0].childNodes:
            if e.localName == 'messages':
                self.process_message_node(e)
            if e.localName == 'profile':
                for f in e.childNodes:
                    if f.localName == 'paymentProfiles':
                        self.payment_profiles.append(
                                self.extract_payment_profiles_data(f))
                    elif f.localName == 'shipToList':
                        self.shipping_profiles.append(
                                self.extract_shipping_profiles_data(f))


class CreateTransactionRequest(BaseRequest):
    def __init__(self,
                 profile_id,
                 payment_profile_id,
                 transaction_type,
                 amount=None,
                 shipping_profile_id=None,
                 transaction_id=None,
                 card_code=None,
                 delimiter=None,
                 order_info=None):
        """
        Arguments:
        profile_id -- unique gateway-assigned profile identifier
        payment_profile_id -- unique gateway-assigned payment profile
                              identifier
        shipping_profile_id -- unique gateway-assigned shipping profile
                              identifier
        transaction_type -- One of the transaction types listed below.
        amount -- Dollar amount of transaction

        Keyword Arguments:
        transaction_id -- Required by PriorAuthCapture, Refund,
                          and Void transactions
        card_code -- The customer's card code (the three or four digit
                          number on the back or front of a credit card)
        delimiter -- Delimiter used for transaction response data
        order_info -- a dict with optional order parameters `invoice_number`,
                      `description`, and `purchase_order_number` as keys.

        Accepted transaction types:
        AuthOnly, AuthCapture, CaptureOnly, PriorAuthCapture, Refund, Void
        """
        super(CreateTransactionRequest, self).__init__(
                "createCustomerProfileTransactionRequest")
        self.profile_id = profile_id
        self.payment_profile_id = payment_profile_id
        self.shipping_profile_id = shipping_profile_id
        self.transaction_type = transaction_type
        self.amount = amount
        self.transaction_id = transaction_id
        self.card_code = card_code
        if delimiter:
            self.delimiter = delimiter
        else:
            self.delimiter = settings.DELIM_CHAR
        self.add_transaction_node()
        self.add_extra_options()
        if order_info:
            self.add_order_info(**order_info)
        if self.card_code:
            card_code_node = self.get_text_node("cardCode", self.card_code)
            self.type_node.appendChild(card_code_node)

    def add_transaction_node(self):
        transaction_node = self.document.createElement("transaction")
        type_node = self.document.createElement("profileTrans%s" %
                self.transaction_type)

        if self.amount and self.transaction_type != "Void":
            amount_node = self.get_text_node("amount", self.amount)
            type_node.appendChild(amount_node)
        transaction_node.appendChild(type_node)
        self.add_profile_ids(type_node)
        if self.transaction_id:
            trans_id_node = self.get_text_node("transId", self.transaction_id)
            type_node.appendChild(trans_id_node)
        self.root.appendChild(transaction_node)
        self.type_node = type_node

    def add_profile_ids(self, transaction_type_node):
        profile_node = self.get_text_node("customerProfileId", self.profile_id)
        transaction_type_node.appendChild(profile_node)

        payment_profile_node = self.get_text_node("customerPaymentProfileId",
                                                  self.payment_profile_id)
        transaction_type_node.appendChild(payment_profile_node)
        if self.shipping_profile_id:
            shipping_profile_node = self.get_text_node(
                                                "customerShippingAddressId",
                                                self.shipping_profile_id)
            transaction_type_node.appendChild(shipping_profile_node)

    def add_order_info(self, invoice_number=None,
                       description=None,
                       purchase_order_number=None):
        if not (invoice_number or description or purchase_order_number):
            return
        order_node = self.document.createElement("order")
        if invoice_number:
            order_node.appendChild(self.get_text_node('invoiceNumber',
                                                      invoice_number))
        if description:
            order_node.appendChild(self.get_text_node('description',
                                                      description))
        if purchase_order_number:
            order_node.appendChild(self.get_text_node('purchaseOrderNumber',
                                                      purchase_order_number))
        self.type_node.appendChild(order_node)

    def add_extra_options(self):
        extra_options_node = self.get_text_node("extraOptions",
                "x_delim_data=TRUE&x_delim_char=%s" % self.delimiter)
        self.root.appendChild(extra_options_node)

    def create_response_object(self):
        from authorizenet.models import CIMResponse, Response
        try:
            response = Response.objects.create_from_list(
                    self.transaction_result)
        except AttributeError:
            response = None
        return CIMResponse.objects.create(result=self.result,
                                          result_code=self.resultCode,
                                          result_text=self.resultText,
                                          transaction_response=response)

    def process_response(self, response):
        for e in response.childNodes[0].childNodes:
            if e.localName == 'messages':
                self.process_message_node(e)
            if e.localName == 'directResponse':
                self.transaction_result = \
                        e.childNodes[0].nodeValue.split(self.delimiter)

########NEW FILE########
__FILENAME__ = conf
"""
Application-specific settings for django-authorizenet

Available settings:

    - AUTHNET_DEBUG: Set to ``True`` if using Authorize.NET test account
    - AUTHNET_LOGIN_ID: Set to value of Authorize.NET login ID
    - AUTHNET_TRANSACTION_KEY: Set to value of Authorize.NET transaction key
    - AUTHNET_CUSTOMER_MODEL: Used to set customer model used for CIM customers
    (defaults to Django user)
    - AUTHNET_DELIM_CHAR: Used to set delimiter character for CIM requests
    (defaults to "|")
    - AUTHNET_FORCE_TEST_REQUEST
    - AUTHNET_EMAIL_CUSTOMER
    - AUTHNET_MD5_HASH

"""

from django.conf import settings as django_settings


class Settings(object):

    """
    Retrieves django.conf settings, using defaults from Default subclass

    All usable settings are specified in settings attribute.  Use an
    ``AUTHNET_`` prefix when specifying settings in django.conf.
    """

    prefix = 'AUTHNET_'
    settings = set(('DEBUG', 'LOGIN_ID', 'TRANSACTION_KEY', 'CUSTOMER_MODEL',
                   'DELIM_CHAR', 'FORCE_TEST_REQUEST', 'EMAIL_CUSTOMER',
                   'MD5_HASH'))

    class Default:
        CUSTOMER_MODEL = getattr(
            django_settings, 'AUTH_USER_MODEL', "auth.User")
        DELIM_CHAR = "|"
        FORCE_TEST_REQUEST = False
        EMAIL_CUSTOMER = None
        MD5_HASH = ""

    def __init__(self):
        self.defaults = Settings.Default()

    def __getattr__(self, name):
        if name not in self.settings:
            raise AttributeError("Setting %s not understood" % name)
        try:
            return getattr(django_settings, self.prefix + name)
        except AttributeError:
            return getattr(self.defaults, name)

settings = Settings()

########NEW FILE########
__FILENAME__ = creditcard
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# from http://github.com/johnboxall/django-paypal
import re
from string import digits, split as L

# Adapted from:
# http://www.djangosnippets.org/snippets/764/
# http://www.satchmoproject.com/
# http://tinyurl.com/shoppify-credit-cards

# Well known card regular expressions.
CARDS = {
    'Visa': re.compile(r"^4\d{12}(\d{3})?$"),
    'Mastercard': re.compile(r"(5[1-5]\d{4}|677189)\d{10}$"),
    'Dinersclub': re.compile(r"^3(0[0-5]|[68]\d)\d{11}"),
    'Amex': re.compile("^3[47]\d{13}$"),
    'Discover': re.compile("^(6011|65\d{2})\d{12}$"),
}

# Well known test numbers
TEST_NUMBERS = L("378282246310005 371449635398431 378734493671000"
                 "30569309025904 38520000023237 6011111111111117"
                 "6011000990139424 555555555554444 5105105105105100"
                 "4111111111111111 4012888888881881 4222222222222")


def verify_credit_card(number, allow_test=False):
    """Returns the card type for given card number or None if invalid."""
    return CreditCard(number).verify(allow_test)


class CreditCard(object):
    def __init__(self, number):
        self.number = number

    def is_number(self):
        """Returns True if there is at least one digit in number."""
        if isinstance(self.number, basestring):
            self.number = "".join([c for c in self.number if c in digits])
            return self.number.isdigit()
        return False

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

    def verify(self, allow_test):
        """Returns the card type if valid else None."""
        if self.is_number() and \
                (not self.is_test() or allow_test) \
                and self.is_mod10():
            return self.get_type()
        return None

########NEW FILE########
__FILENAME__ = exceptions
class BillingError(Exception):
    """Error due to Authorize.NET request"""

########NEW FILE########
__FILENAME__ = fields
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import date
from calendar import monthrange

from django import forms
from django.utils.translation import ugettext as _

from authorizenet.conf import settings
from authorizenet.creditcard import verify_credit_card


class CreditCardField(forms.CharField):
    """
    Form field for checking out a credit card.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 20)
        super(CreditCardField, self).__init__(*args, **kwargs)

    def clean(self, value):
        """
        Raises a ValidationError if the card is not valid
        and stashes card type.
        """
        self.card_type = verify_credit_card(value, allow_test=settings.DEBUG)
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
    EXP_MONTH = [(x, "%02d" % x) for x in xrange(1, 13)]
    EXP_YEAR = [(x, x) for x in xrange(date.today().year,
                                       date.today().year + 15)]

    default_error_messages = {
        'invalid_month': u'Enter a valid month.',
        'invalid_year': u'Enter a valid year.',
    }

    def __init__(self, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])

        fields = (
            forms.ChoiceField(
                choices=self.EXP_MONTH,
                error_messages={'invalid': errors['invalid_month']}),
            forms.ChoiceField(
                choices=self.EXP_YEAR,
                error_messages={'invalid': errors['invalid_year']}),
        )

        super(CreditCardExpiryField, self).__init__(fields, *args, **kwargs)
        self.widget = CreditCardExpiryWidget(widgets=[fields[0].widget,
                                                      fields[1].widget])

    def clean(self, value):
        exp = super(CreditCardExpiryField, self).clean(value)
        if date.today() > exp:
            raise forms.ValidationError(
                "The expiration date you entered is in the past.")
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
        kwargs.setdefault('min_length', 3)
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
from django import forms
from authorizenet.conf import settings
from authorizenet.fields import CreditCardField, CreditCardExpiryField, \
        CreditCardCVV2Field, CountryField
from authorizenet.models import CustomerPaymentProfile


class SIMPaymentForm(forms.Form):
    x_login = forms.CharField(max_length=20,
                              required=True,
                              widget=forms.HiddenInput,
                              initial=settings.LOGIN_ID)
    x_type = forms.CharField(max_length=20,
                             widget=forms.HiddenInput,
                             initial="AUTH_CAPTURE")
    x_amount = forms.DecimalField(max_digits=15,
                                  decimal_places=2,
                                  widget=forms.HiddenInput)
    x_show_form = forms.CharField(max_length=20,
                                  widget=forms.HiddenInput,
                                  initial="PAYMENT_FORM")
    x_method = forms.CharField(max_length=10,
                               widget=forms.HiddenInput,
                               initial="CC")
    x_fp_sequence = forms.CharField(max_length=10,
                                    widget=forms.HiddenInput,
                                    initial="CC")
    x_version = forms.CharField(max_length=10,
                                widget=forms.HiddenInput,
                                initial="3.1")
    x_relay_response = forms.CharField(max_length=8,
                                       widget=forms.HiddenInput,
                                       initial="TRUE")
    x_fp_timestamp = forms.CharField(max_length=55,
                                     widget=forms.HiddenInput)
    x_relay_url = forms.CharField(max_length=55,
                                  widget=forms.HiddenInput)
    x_fp_hash = forms.CharField(max_length=55,
                                widget=forms.HiddenInput)
    x_invoice_num = forms.CharField(max_length=55,
                                    required=False,
                                    widget=forms.HiddenInput)
    x_description = forms.CharField(max_length=255,
                                    required=False,
                                    widget=forms.HiddenInput)


class SIMBillingForm(forms.Form):
    x_first_name = forms.CharField(max_length=50, widget=forms.HiddenInput)
    x_last_name = forms.CharField(max_length=50, widget=forms.HiddenInput)
    x_company = forms.CharField(max_length=50, widget=forms.HiddenInput)
    x_address = forms.CharField(max_length=60, widget=forms.HiddenInput)
    x_city = forms.CharField(max_length=40, widget=forms.HiddenInput)
    x_state = forms.CharField(max_length=40, widget=forms.HiddenInput)
    x_zip = forms.CharField(max_length=20, widget=forms.HiddenInput)
    x_country = forms.CharField(max_length=60, widget=forms.HiddenInput)
    x_phone = forms.CharField(max_length=25, widget=forms.HiddenInput)
    x_fax = forms.CharField(max_length=25, widget=forms.HiddenInput)
    x_email = forms.CharField(max_length=255, widget=forms.HiddenInput)
    x_cust_id = forms.CharField(max_length=20, widget=forms.HiddenInput)


class BillingAddressForm(forms.Form):
    first_name = forms.CharField(50, label="First Name")
    last_name = forms.CharField(50, label="Last Name")
    company = forms.CharField(50, label="Company", required=False)
    address = forms.CharField(60, label="Street Address")
    city = forms.CharField(40, label="City")
    state = forms.CharField(40, label="State")
    country = CountryField(label="Country", initial="US")
    zip = forms.CharField(20, label="Postal / Zip Code")

class ShippingAddressForm(forms.Form):
    ship_to_first_name = forms.CharField(50, label="First Name")
    ship_to_last_name = forms.CharField(50, label="Last Name")
    ship_to_company = forms.CharField(50, label="Company", required=False)
    ship_to_address = forms.CharField(60, label="Street Address")
    ship_to_city = forms.CharField(40, label="City")
    ship_to_state = forms.CharField(label="State")
    ship_to_zip = forms.CharField(20, label="Postal / Zip Code")
    ship_to_country = CountryField(label="Country", initial="US")

class AIMPaymentForm(forms.Form):
    card_num = CreditCardField(label="Credit Card Number")
    exp_date = CreditCardExpiryField(label="Expiration Date")
    card_code = CreditCardCVV2Field(label="Card Security Code")


class CIMPaymentForm(forms.Form):
    card_number = CreditCardField(label="Credit Card Number")
    expiration_date = CreditCardExpiryField(label="Expiration Date")
    card_code = CreditCardCVV2Field(label="Card Security Code")


class CustomerPaymentForm(forms.ModelForm):

    """Base customer payment form without shipping address"""

    country = CountryField(label="Country", initial="US")
    card_number = CreditCardField(label="Credit Card Number")
    expiration_date = CreditCardExpiryField(label="Expiration Date")
    card_code = CreditCardCVV2Field(label="Card Security Code")

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        return super(CustomerPaymentForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(CustomerPaymentForm, self).save(commit=False)
        if self.customer:
            instance.customer = self.customer
        instance.card_code = self.cleaned_data.get('card_code')
        if commit:
            instance.save()
        return instance

    class Meta:
        model = CustomerPaymentProfile
        fields = ('first_name', 'last_name', 'company', 'address', 'city',
                  'state', 'country', 'zip', 'card_number',
                  'expiration_date', 'card_code')


class CustomerPaymentAdminForm(CustomerPaymentForm):
    class Meta(CustomerPaymentForm.Meta):
        fields = ('customer',) + CustomerPaymentForm.Meta.fields


class HostedCIMProfileForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput)
    def __init__(self, token, *args, **kwargs):
        super(HostedCIMProfileForm, self).__init__(*args, **kwargs)
        self.fields['token'].initial = token
        if settings.DEBUG:
            self.action = "https://test.authorize.net/profile/manage"
        else:
            self.action = "https://secure.authorize.net/profile/manage"
        


def get_test_exp_date():
    from datetime import date, timedelta
    test_date = date.today() + timedelta(days=365)
    return test_date.strftime('%m%y')

########NEW FILE########
__FILENAME__ = helpers
import re

import requests

from authorizenet.conf import settings
from authorizenet import AUTHNET_POST_URL, AUTHNET_TEST_POST_URL


class AIMPaymentHelper(object):
    def __init__(self, defaults):
        self.defaults = defaults
        if settings.DEBUG:
            self.endpoint = AUTHNET_TEST_POST_URL
        else:
            self.endpoint = AUTHNET_POST_URL

    def get_response(self, data):
        final_data = dict(self.defaults)
        final_data.update(data)
        c = final_data['x_delim_char']
        # Escape delimiter characters in request fields
        for k, v in final_data.items():
            if k != 'x_delim_char':
                final_data[k] = unicode(v).replace(c, "\\%s" % c)
        response = requests.post(self.endpoint, data=final_data)
        # Split response by delimiter,
        # unescaping delimiter characters in fields
        response_list = re.split("(?<!\\\\)\%s" % c, response.text)
        response_list = map(lambda s: s.replace("\\%s" % c, c),
                            response_list)
        return response_list

########NEW FILE########
__FILENAME__ = managers
from django.db import models


class CustomerProfileManager(models.Manager):

    def create(self, **data):

        """Create new Authorize.NET customer profile"""

        from .models import CustomerPaymentProfile

        kwargs = data
        sync = kwargs.pop('sync', True)
        kwargs = {
            'customer': kwargs.get('customer', None),
            'profile_id': kwargs.pop('profile_id', None),
        }

        # Create customer profile
        obj = self.model(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db, sync=sync, data=data)

        if sync:
            # Store customer payment profile data locally
            for payment_profile_id in obj.payment_profile_ids:
                CustomerPaymentProfile.objects.create(
                    customer_profile=obj,
                    payment_profile_id=payment_profile_id,
                    sync=False,
                    **data
                )

        return obj

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Response'
        db.create_table('authorizenet_response', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('response_code', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('response_subcode', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('response_reason_code', self.gf('django.db.models.fields.CharField')(max_length=15)),
            ('response_reason_text', self.gf('django.db.models.fields.TextField')()),
            ('auth_code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('avs_code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('trans_id', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('invoice_num', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('amount', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('method', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=20, db_index=True)),
            ('cust_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('company', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('zip', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('fax', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ship_to_first_name', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('ship_to_last_name', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('ship_to_company', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('ship_to_address', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('ship_to_city', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('ship_to_state', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('ship_to_zip', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('ship_to_country', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('tax', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('duty', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('freight', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('tax_exempt', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('po_num', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('MD5_Hash', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('cvv2_resp_code', self.gf('django.db.models.fields.CharField')(max_length=2, blank=True)),
            ('cavv_response', self.gf('django.db.models.fields.CharField')(max_length=2, blank=True)),
            ('test_request', self.gf('django.db.models.fields.CharField')(default='FALSE', max_length=10, blank=True)),
        ))
        db.send_create_signal('authorizenet', ['Response'])

    def backwards(self, orm):

        # Deleting model 'Response'
        db.delete_table('authorizenet_response')

    models = {
        'authorizenet.response': {
            'MD5_Hash': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'Meta': {'object_name': 'Response'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'amount': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'auth_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'avs_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'cavv_response': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'cust_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'cvv2_resp_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'duty': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'freight': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_num': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'po_num': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'response_code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'response_reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'response_reason_text': ('django.db.models.fields.TextField', [], {}),
            'response_subcode': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'ship_to_address': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_company': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_country': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'tax': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'tax_exempt': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'test_request': ('django.db.models.fields.CharField', [], {'default': "'FALSE'", 'max_length': '10', 'blank': 'True'}),
            'trans_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['authorizenet']

########NEW FILE########
__FILENAME__ = 0002_auto__add_cimresponse
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'CIMResponse'
        db.create_table('authorizenet_cimresponse', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('result', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('result_code', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('result_text', self.gf('django.db.models.fields.CharField')(max_length=1023)),
            ('transaction_response', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['authorizenet.Response'], null=True, blank=True)),
        ))
        db.send_create_signal('authorizenet', ['CIMResponse'])

    def backwards(self, orm):

        # Deleting model 'CIMResponse'
        db.delete_table('authorizenet_cimresponse')

    models = {
        'authorizenet.cimresponse': {
            'Meta': {'object_name': 'CIMResponse'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_code': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_text': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'transaction_response': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['authorizenet.Response']", 'null': 'True', 'blank': 'True'})
        },
        'authorizenet.response': {
            'MD5_Hash': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'Meta': {'object_name': 'Response'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'amount': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'auth_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'avs_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'cavv_response': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'cust_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'cvv2_resp_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'duty': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'freight': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_num': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'po_num': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'response_code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'response_reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'response_reason_text': ('django.db.models.fields.TextField', [], {}),
            'response_subcode': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'ship_to_address': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_company': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_country': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'tax': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'tax_exempt': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'test_request': ('django.db.models.fields.CharField', [], {'default': "'FALSE'", 'max_length': '10', 'blank': 'True'}),
            'trans_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['authorizenet']

########NEW FILE########
__FILENAME__ = 0003_missing_response_fields
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Response.card_type'
        db.add_column('authorizenet_response', 'card_type', self.gf('django.db.models.fields.CharField')(default='', max_length=10, blank=True), keep_default=False)

        # Adding field 'Response.account_number'
        db.add_column('authorizenet_response', 'account_number', self.gf('django.db.models.fields.CharField')(default='', max_length=10, blank=True), keep_default=False)

    def backwards(self, orm):

        # Deleting field 'Response.card_type'
        db.delete_column('authorizenet_response', 'card_type')

        # Deleting field 'Response.account_number'
        db.delete_column('authorizenet_response', 'account_number')

    models = {
        'authorizenet.cimresponse': {
            'Meta': {'object_name': 'CIMResponse'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_code': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_text': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'transaction_response': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['authorizenet.Response']", 'null': 'True', 'blank': 'True'})
        },
        'authorizenet.response': {
            'MD5_Hash': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'Meta': {'object_name': 'Response'},
            'account_number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'amount': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'auth_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'avs_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'card_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'cavv_response': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'cust_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'cvv2_resp_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'duty': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'freight': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_num': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'po_num': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'response_code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'response_reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'response_reason_text': ('django.db.models.fields.TextField', [], {}),
            'response_subcode': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'ship_to_address': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_company': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_country': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'tax': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'tax_exempt': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'test_request': ('django.db.models.fields.CharField', [], {'default': "'FALSE'", 'max_length': '10', 'blank': 'True'}),
            'trans_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['authorizenet']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_response_created__add_field_cimresponse_created__chg_f
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Response.created'
        db.add_column('authorizenet_response', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True), keep_default=False)

        # Adding field 'CIMResponse.created'
        db.add_column('authorizenet_cimresponse', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True), keep_default=False)

        # Changing field 'CIMResponse.result_text'
        db.alter_column('authorizenet_cimresponse', 'result_text', self.gf('django.db.models.fields.TextField')(max_length=1023))

    def backwards(self, orm):
        
        # Deleting field 'Response.created'
        db.delete_column('authorizenet_response', 'created')

        # Deleting field 'CIMResponse.created'
        db.delete_column('authorizenet_cimresponse', 'created')

        # Changing field 'CIMResponse.result_text'
        db.alter_column('authorizenet_cimresponse', 'result_text', self.gf('django.db.models.fields.CharField')(max_length=1023))

    models = {
        'authorizenet.cimresponse': {
            'Meta': {'object_name': 'CIMResponse'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_code': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_text': ('django.db.models.fields.TextField', [], {'max_length': '1023'}),
            'transaction_response': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['authorizenet.Response']", 'null': 'True', 'blank': 'True'})
        },
        'authorizenet.response': {
            'MD5_Hash': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'Meta': {'object_name': 'Response'},
            'account_number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'amount': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'auth_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'avs_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'card_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'cavv_response': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'cust_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'cvv2_resp_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'duty': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'freight': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_num': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'po_num': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'response_code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'response_reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'response_reason_text': ('django.db.models.fields.TextField', [], {}),
            'response_subcode': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'ship_to_address': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_company': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_country': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'tax': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'tax_exempt': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'test_request': ('django.db.models.fields.CharField', [], {'default': "'FALSE'", 'max_length': '10', 'blank': 'True'}),
            'trans_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['authorizenet']

########NEW FILE########
__FILENAME__ = 0005_auto__add_customerpaymentprofile__add_customerprofile__chg_field_cimre
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CustomerPaymentProfile'
        db.create_table(u'authorizenet_customerpaymentprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(related_name='payment_profiles', to=orm['doctors.Practice'])),
            ('customer_profile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='payment_profiles', to=orm['authorizenet.CustomerProfile'])),
            ('payment_profile_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('company', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('phone_number', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('fax_number', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('zip', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('card_number', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('expiration_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'authorizenet', ['CustomerPaymentProfile'])

        # Adding model 'CustomerProfile'
        db.create_table(u'authorizenet_customerprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('customer', self.gf('django.db.models.fields.related.OneToOneField')(related_name='customer_profile', unique=True, to=orm['doctors.Practice'])),
            ('profile_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'authorizenet', ['CustomerProfile'])


        # Changing field 'CIMResponse.result_text'
        db.alter_column(u'authorizenet_cimresponse', 'result_text', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):
        # Deleting model 'CustomerPaymentProfile'
        db.delete_table(u'authorizenet_customerpaymentprofile')

        # Deleting model 'CustomerProfile'
        db.delete_table(u'authorizenet_customerprofile')


        # Changing field 'CIMResponse.result_text'
        db.alter_column(u'authorizenet_cimresponse', 'result_text', self.gf('django.db.models.fields.TextField')(max_length=1023))

    models = {
        u'authorizenet.cimresponse': {
            'Meta': {'object_name': 'CIMResponse'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_code': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'result_text': ('django.db.models.fields.TextField', [], {}),
            'transaction_response': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['authorizenet.Response']", 'null': 'True', 'blank': 'True'})
        },
        u'authorizenet.customerpaymentprofile': {
            'Meta': {'object_name': 'CustomerPaymentProfile'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'card_number': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'payment_profiles'", 'to': u"orm['doctors.Practice']"}),
            'customer_profile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'payment_profiles'", 'to': u"orm['authorizenet.CustomerProfile']"}),
            'expiration_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'fax_number': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'payment_profile_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        },
        u'authorizenet.customerprofile': {
            'Meta': {'object_name': 'CustomerProfile'},
            'customer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'customer_profile'", 'unique': 'True', 'to': u"orm['doctors.Practice']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'profile_id': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'authorizenet.response': {
            'MD5_Hash': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'Meta': {'object_name': 'Response'},
            'account_number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'amount': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'auth_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'avs_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'card_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10', 'blank': 'True'}),
            'cavv_response': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'cust_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'cvv2_resp_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'duty': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'freight': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_num': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'po_num': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'response_code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'response_reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'response_reason_text': ('django.db.models.fields.TextField', [], {}),
            'response_subcode': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'ship_to_address': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_company': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_country': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ship_to_first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ship_to_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'ship_to_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'tax': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'tax_exempt': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'test_request': ('django.db.models.fields.CharField', [], {'default': "'FALSE'", 'max_length': '10', 'blank': 'True'}),
            'trans_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'base.address': {
            'Meta': {'object_name': 'Address'},
            'address1': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'address2': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django_localflavor_us.models.USStateField', [], {'max_length': '2', 'blank': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'})
        },
        u'doctors.employeetype': {
            'Meta': {'object_name': 'EmployeeType'},
            'has_profile': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_doctor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_schedulable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        u'doctors.practice': {
            'Meta': {'object_name': 'Practice'},
            'accepted_insurance': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['medical.InsurancePlan']", 'symmetrical': 'False', 'blank': 'True'}),
            'addresses': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.Address']", 'through': u"orm['doctors.PracticeAddress']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'phone': ('base.fields.PhoneNumberField', [], {'max_length': '20'}),
            'practice_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['doctors.PracticeType']"}),
            'statement': ('django.db.models.fields.TextField', [], {'max_length': '5000', 'blank': 'True'}),
            'timezone': ('timezone_field.fields.TimeZoneField', [], {})
        },
        u'doctors.practiceaddress': {
            'Meta': {'object_name': 'PracticeAddress'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.Address']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'practice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['doctors.Practice']"})
        },
        u'doctors.practiceemployeetype': {
            'Meta': {'ordering': "['order']", 'object_name': 'PracticeEmployeeType', 'db_table': "'doctors_practicetype_employee_types'"},
            'employeetype': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['doctors.EmployeeType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'practicetype': ('adminsortable.fields.SortableForeignKey', [], {'to': u"orm['doctors.PracticeType']"})
        },
        u'doctors.practicetype': {
            'Meta': {'ordering': "['order']", 'object_name': 'PracticeType'},
            'employee_types': ('sortedm2m.fields.SortedManyToManyField', [], {'to': u"orm['doctors.EmployeeType']", 'through': u"orm['doctors.PracticeEmployeeType']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'specialties': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['medical.DoctorSpecialty']", 'symmetrical': 'False'})
        },
        u'medical.appointmenttype': {
            'Meta': {'ordering': "['order']", 'object_name': 'AppointmentType'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['medical.BillingCategory']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'specialty': ('adminsortable.fields.SortableForeignKey', [], {'related_name': "'appointment_types'", 'to': u"orm['medical.DoctorSpecialty']"})
        },
        u'medical.billingcategory': {
            'Meta': {'object_name': 'BillingCategory'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'medical.doctorspecialty': {
            'Meta': {'ordering': "['order']", 'object_name': 'DoctorSpecialty'},
            'default_appointment_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['medical.AppointmentType']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'})
        },
        u'medical.insuranceplan': {
            'Meta': {'ordering': "['provider__name', 'name']", 'object_name': 'InsurancePlan'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'plans'", 'to': u"orm['medical.InsuranceProvider']"})
        },
        u'medical.insuranceprovider': {
            'Meta': {'ordering': "['name']", 'object_name': 'InsuranceProvider'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['authorizenet']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.forms.models import model_to_dict

from .conf import settings
from .cim import add_profile, get_profile, update_payment_profile, \
    create_payment_profile, delete_profile, delete_payment_profile

from .managers import CustomerProfileManager
from .exceptions import BillingError


RESPONSE_CHOICES = (
    ('1', 'Approved'),
    ('2', 'Declined'),
    ('3', 'Error'),
    ('4', 'Held for Review'),
)

AVS_RESPONSE_CODE_CHOICES = (
    ('A', 'Address (Street) matches, ZIP does not'),
    ('B', 'Address information not provided for AVS check'),
    ('E', 'AVS error'),
    ('G', 'Non-U.S. Card Issuing Bank'),
    ('N', 'No Match on Address (Street) or ZIP'),
    ('P', 'AVS not applicable for this transaction'),
    ('R', 'Retry - System unavailable or timed out'),
    ('S', 'Service not supported by issuer'),
    ('U', 'Address information is unavailable'),
    ('W', 'Nine digit ZIP matches, Address (Street) does not'),
    ('X', 'Address (Street) and nine digit ZIP match'),
    ('Y', 'Address (Street) and five digit ZIP match'),
    ('Z', 'Five digit ZIP matches, Address (Street) does not'),
)

METHOD_CHOICES = (
    ('CC', 'Credit Card'),
    ('ECHECK', 'eCheck'),
)

TYPE_CHOICES = (
    ('auth_capture', 'Authorize and Capture'),
    ('auth_only', 'Authorize only'),
    ('credit', 'Credit'),
    ('prior_auth_capture', 'Prior capture'),
    ('void', 'Void'),
)

CVV2_RESPONSE_CODE_CHOICES = (
    ('M', 'Match'),
    ('N', 'No Match'),
    ('P', 'Not Processed'),
    ('S', 'Should have been present'),
    ('U', 'Issuer unable to process request'),
)

CAVV_RESPONSE_CODE_CHOICES = (
    ('', 'CAVV not validated'),
    ('0', 'CAVV not validated because erroneous data was submitted'),
    ('1', 'CAVV failed validation'),
    ('2', 'CAVV passed validation'),
    ('3', 'CAVV validation could not be performed; issuer attempt incomplete'),
    ('4', 'CAVV validation could not be performed; issuer system error'),
    ('5', 'Reserved for future use'),
    ('6', 'Reserved for future use'),
    ('7', 'CAVV attempt - failed validation - '
          'issuer available (U.S.-issued card/non-U.S acquirer)'),
    ('8', 'CAVV attempt - passed validation - '
          'issuer available (U.S.-issued card/non-U.S. acquirer)'),
    ('9', 'CAVV attempt - failed validation - '
          'issuer unavailable (U.S.-issued card/non-U.S. acquirer)'),
    ('A', 'CAVV attempt - passed validation - '
          'issuer unavailable (U.S.-issued card/non-U.S. acquirer)'),
    ('B', 'CAVV passed validation, information only, no liability shift'),
)


CIM_RESPONSE_CODE_CHOICES = (
    ('I00001', 'Successful'),
    ('I00003', 'The record has already been deleted.'),
    ('E00001', 'An error occurred during processing. Please try again.'),
    ('E00002', 'The content-type specified is not supported.'),
    ('E00003', 'An error occurred while parsing the XML request.'),
    ('E00004', 'The name of the requested API method is invalid.'),
    ('E00005', 'The merchantAuthentication.transactionKey '
               'is invalid or not present.'),
    ('E00006', 'The merchantAuthentication.name is invalid or not present.'),
    ('E00007', 'User authentication failed '
               'due to invalid authentication values.'),
    ('E00008', 'User authentication failed. The payment gateway account or '
               'user is inactive.'),
    ('E00009', 'The payment gateway account is in Test Mode. '
               'The request cannot be processed.'),
    ('E00010', 'User authentication failed. '
               'You do not have the appropriate permissions.'),
    ('E00011', 'Access denied. You do not have the appropriate permissions.'),
    ('E00013', 'The field is invalid.'),
    ('E00014', 'A required field is not present.'),
    ('E00015', 'The field length is invalid.'),
    ('E00016', 'The field type is invalid.'),
    ('E00019', 'The customer taxId or driversLicense information '
               'is required.'),
    ('E00027', 'The transaction was unsuccessful.'),
    ('E00029', 'Payment information is required.'),
    ('E00039', 'A duplicate record already exists.'),
    ('E00040', 'The record cannot be found.'),
    ('E00041', 'One or more fields must contain a value.'),
    ('E00042', 'The maximum number of payment profiles '
               'for the customer profile has been reached.'),
    ('E00043', 'The maximum number of shipping addresses '
               'for the customer profile has been reached.'),
    ('E00044', 'Customer Information Manager is not enabled.'),
    ('E00045', 'The root node does not reference a valid XML namespace.'),
    ('E00051', 'The original transaction was not issued '
               'for this payment profile.'),
)


class ResponseManager(models.Manager):
    def create_from_dict(self, params):
        kwargs = dict(map(lambda x: (str(x[0][2:]), x[1]), params.items()))
        return self.create(**kwargs)

    def create_from_list(self, items):
        kwargs = dict(zip(map(lambda x: x.name,
                              Response._meta.fields)[1:], items))
        return self.create(**kwargs)


class Response(models.Model):

    """Transaction Response (See Section 4 of AIM Developer Guide)"""

    response_code = models.CharField(max_length=2, choices=RESPONSE_CHOICES)
    response_subcode = models.CharField(max_length=10)
    response_reason_code = models.CharField(max_length=15)
    response_reason_text = models.TextField()
    auth_code = models.CharField(max_length=10)
    avs_code = models.CharField(max_length=10,
                                choices=AVS_RESPONSE_CODE_CHOICES)
    trans_id = models.CharField(max_length=255, db_index=True)
    invoice_num = models.CharField(max_length=20, blank=True)
    description = models.CharField(max_length=255)
    amount = models.CharField(max_length=16)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    type = models.CharField(max_length=20,
                            choices=TYPE_CHOICES,
                            db_index=True)
    cust_id = models.CharField(max_length=20)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.CharField(max_length=50)
    address = models.CharField(max_length=60)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=40)
    zip = models.CharField(max_length=20)
    country = models.CharField(max_length=60)
    phone = models.CharField(max_length=25)
    fax = models.CharField(max_length=25)
    email = models.CharField(max_length=255)
    ship_to_first_name = models.CharField(max_length=50, blank=True)
    ship_to_last_name = models.CharField(max_length=50, blank=True)
    ship_to_company = models.CharField(max_length=50, blank=True)
    ship_to_address = models.CharField(max_length=60, blank=True)
    ship_to_city = models.CharField(max_length=40, blank=True)
    ship_to_state = models.CharField(max_length=40, blank=True)
    ship_to_zip = models.CharField(max_length=20, blank=True)
    ship_to_country = models.CharField(max_length=60, blank=True)
    tax = models.CharField(max_length=16, blank=True)
    duty = models.CharField(max_length=16, blank=True)
    freight = models.CharField(max_length=16, blank=True)
    tax_exempt = models.CharField(max_length=16, blank=True)
    po_num = models.CharField(max_length=25, blank=True)
    MD5_Hash = models.CharField(max_length=255)
    cvv2_resp_code = models.CharField(max_length=2,
                                      choices=CVV2_RESPONSE_CODE_CHOICES,
                                      blank=True)
    cavv_response = models.CharField(max_length=2,
                                     choices=CAVV_RESPONSE_CODE_CHOICES,
                                     blank=True)

    test_request = models.CharField(max_length=10, default="FALSE", blank=True)

    card_type = models.CharField(max_length=10, default="", blank=True)
    account_number = models.CharField(max_length=10, default="", blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    objects = ResponseManager()

    @property
    def is_approved(self):
        return self.response_code == '1'

    def __unicode__(self):
        return u"response_code: %s, trans_id: %s, amount: %s, type: %s" % \
                (self.response_code, self.trans_id, self.amount, self.type)


class CIMResponse(models.Model):

    """Response for CIM API call (See Section 3 in CIM XML Guide)"""

    result = models.CharField(max_length=8)
    result_code = models.CharField(max_length=8,
                                   choices=CIM_RESPONSE_CODE_CHOICES)
    result_text = models.TextField()
    transaction_response = models.ForeignKey(Response, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def success(self):
        return self.result == 'Ok'

    def raise_if_error(self):
        if not self.success:
            raise BillingError(self.result_text)


class CustomerProfile(models.Model):

    """Authorize.NET customer profile"""

    customer = models.OneToOneField(settings.CUSTOMER_MODEL,
                                    related_name='customer_profile')
    profile_id = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        """If creating new instance, create profile on Authorize.NET also"""
        data = kwargs.pop('data', {})
        sync = kwargs.pop('sync', True)
        if not self.id and sync:
            self.push_to_server(data)
        super(CustomerProfile, self).save(*args, **kwargs)

    def delete(self):
        """Delete the customer profile remotely and locally"""
        response = delete_profile(self.profile_id)
        response.raise_if_error()
        super(CustomerProfile, self).delete()

    def push_to_server(self, data):
        """Create customer profile for given ``customer`` on Authorize.NET"""
        output = add_profile(self.customer.pk, data, data)
        output['response'].raise_if_error()
        self.profile_id = output['profile_id']
        self.payment_profile_ids = output['payment_profile_ids']

    def sync(self):
        """Overwrite local customer profile data with remote data"""
        output = get_profile(self.profile_id)
        output['response'].raise_if_error()
        for payment_profile in output['payment_profiles']:
            instance, created = CustomerPaymentProfile.objects.get_or_create(
                customer_profile=self,
                payment_profile_id=payment_profile['payment_profile_id']
            )
            instance.sync(payment_profile)

    objects = CustomerProfileManager()

    def __unicode__(self):
        return self.profile_id


class CustomerPaymentProfile(models.Model):

    """Authorize.NET customer payment profile"""

    customer = models.ForeignKey(settings.CUSTOMER_MODEL,
                                 related_name='payment_profiles')
    customer_profile = models.ForeignKey('CustomerProfile',
                                         related_name='payment_profiles')
    payment_profile_id = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=25, blank=True)
    fax_number = models.CharField(max_length=25, blank=True)
    address = models.CharField(max_length=60, blank=True)
    city = models.CharField(max_length=40, blank=True)
    state = models.CharField(max_length=40, blank=True)
    zip = models.CharField(max_length=20, blank=True, verbose_name="ZIP")
    country = models.CharField(max_length=60, blank=True)
    card_number = models.CharField(max_length=16, blank=True)
    expiration_date = models.DateField(blank=True, null=True)
    card_code = None

    def __init__(self, *args, **kwargs):
        self.card_code = kwargs.pop('card_code', None)
        return super(CustomerPaymentProfile, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Sync payment profile on Authorize.NET if sync kwarg is not False"""
        if kwargs.pop('sync', True):
            self.push_to_server()
        self.card_code = None
        self.card_number = "XXXX%s" % self.card_number[-4:]
        super(CustomerPaymentProfile, self).save(*args, **kwargs)

    def push_to_server(self):
        """
        Use appropriate CIM API call to save payment profile to Authorize.NET

        1. If customer has no profile yet, create one with this payment profile
        2. If payment profile is not on Authorize.NET yet, create it there
        3. If payment profile exists on Authorize.NET update it there

        """
        if not self.customer_profile_id:
            try:
                self.customer_profile = CustomerProfile.objects.get(
                    customer=self.customer)
            except CustomerProfile.DoesNotExist:
                pass
        if self.payment_profile_id:
            response = update_payment_profile(
                self.customer_profile.profile_id,
                self.payment_profile_id,
                self.raw_data,
                self.raw_data,
            )
            response.raise_if_error()
        elif self.customer_profile_id:
            output = create_payment_profile(
                self.customer_profile.profile_id,
                self.raw_data,
                self.raw_data,
            )
            response = output['response']
            response.raise_if_error()
            self.payment_profile_id = output['payment_profile_id']
        else:
            output = add_profile(
                self.customer.id,
                self.raw_data,
                self.raw_data,
            )
            response = output['response']
            response.raise_if_error()
            self.customer_profile = CustomerProfile.objects.create(
                customer=self.customer,
                profile_id=output['profile_id'],
                sync=False,
            )
            self.payment_profile_id = output['payment_profile_ids'][0]

    @property
    def raw_data(self):
        """Return data suitable for use in payment and billing forms"""
        data = model_to_dict(self)
        data['card_code'] = getattr(self, 'card_code')
        return data

    def sync(self, data):
        """Overwrite local customer payment profile data with remote data"""
        for k, v in data.get('billing', {}).items():
            setattr(self, k, v)
        self.card_number = data.get('credit_card', {}).get('card_number',
                                                           self.card_number)
        self.save(sync=False)

    def delete(self):
        """Delete the customer payment profile remotely and locally"""
        response = delete_payment_profile(self.customer_profile.profile_id,
                                          self.payment_profile_id)
        response.raise_if_error()
        return super(CustomerPaymentProfile, self).delete()

    def update(self, **data):
        """Update the customer payment profile remotely and locally"""
        for key, value in data.items():
            setattr(self, key, value)
        self.save()
        return self

    def __unicode__(self):
        return self.payment_profile_id

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

__all__ = ['payment_was_successful',
           'payment_was_flagged',
           'customer_was_created',
           'customer_was_flagged']

payment_was_successful = Signal()
payment_was_flagged = Signal()

customer_was_created = Signal(["customer_id",
                               "customer_description",
                               "customer_email",
                               "profile_id",
                               "payment_profile_ids"])
customer_was_flagged = Signal(["customer_id", "customer_description", "customer_email"])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('authorizenet.views',
     url(r'^sim/payment/$', 'sim_payment', name="authnet_sim_payment"),
)

########NEW FILE########
__FILENAME__ = utils
import hmac

from django.core.exceptions import ImproperlyConfigured

from authorizenet.conf import settings
from authorizenet.helpers import AIMPaymentHelper
from authorizenet.models import Response
from authorizenet.signals import payment_was_successful, payment_was_flagged


def get_fingerprint(x_fp_sequence, x_fp_timestamp, x_amount):
    msg = '^'.join([settings.LOGIN_ID,
           x_fp_sequence,
           x_fp_timestamp,
           x_amount
           ]) + '^'

    return hmac.new(settings.TRANSACTION_KEY, msg).hexdigest()


def extract_form_data(form_data):
    return dict(map(lambda x: ('x_' + x[0], x[1]),
                    form_data.items()))

AIM_DEFAULT_DICT = {
    'x_login': settings.LOGIN_ID,
    'x_tran_key': settings.TRANSACTION_KEY,
    'x_delim_data': "TRUE",
    'x_delim_char': settings.DELIM_CHAR,
    'x_relay_response': "FALSE",
    'x_type': "AUTH_CAPTURE",
    'x_method': "CC"
}


def create_response(data):
    helper = AIMPaymentHelper(defaults=AIM_DEFAULT_DICT)
    response_list = helper.get_response(data)
    response = Response.objects.create_from_list(response_list)
    if response.is_approved:
        payment_was_successful.send(sender=response)
    else:
        payment_was_flagged.send(sender=response)
    return response


def process_payment(form_data, extra_data):
    data = extract_form_data(form_data)
    data.update(extract_form_data(extra_data))
    data['x_exp_date'] = data['x_exp_date'].strftime('%m%y')
    if settings.FORCE_TEST_REQUEST:
        data['x_test_request'] = 'TRUE'
    if settings.EMAIL_CUSTOMER is not None:
        data['x_email_customer'] = settings.EMAIL_CUSTOMER
    return create_response(data)


def combine_form_data(*args):
    data = {}
    for form in args:
        data.update(form.cleaned_data)
    return data


def capture_transaction(response, extra_data=None):
    if response.type.lower() != 'auth_only':
        raise ImproperlyConfigured(
                "You can capture only transactions with AUTH_ONLY type")
    if extra_data is None:
        extra_data = {}
    data = dict(extra_data)
    data['x_trans_id'] = response.trans_id
    #if user already specified x_amount, don't override it with response value
    if not data.get('x_amount', None):
        data['x_amount'] = response.amount
    data['x_type'] = 'PRIOR_AUTH_CAPTURE'
    if settings.FORCE_TEST_REQUEST:
        data['x_test_request'] = 'TRUE'
    return create_response(data)

########NEW FILE########
__FILENAME__ = views
try:
    import hashlib
except ImportError:
    import md5 as hashlib

from authorizenet.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import CreateView, UpdateView

from authorizenet.forms import AIMPaymentForm, BillingAddressForm, CustomerPaymentForm
from authorizenet.models import CustomerProfile, CustomerPaymentProfile
from authorizenet.models import Response
from authorizenet.signals import payment_was_successful, payment_was_flagged
from authorizenet.utils import process_payment, combine_form_data


@csrf_exempt
def sim_payment(request):
    response = Response.objects.create_from_dict(request.POST)
    MD5_HASH = settings.MD5_HASH
    hash_is_valid = True

    #if MD5-Hash value is provided, use it to validate response
    if MD5_HASH:
        hash_is_valid = False
        hash_value = hashlib.md5(''.join([MD5_HASH,
                                          settings.LOGIN_ID,
                                          response.trans_id,
                                          response.amount])).hexdigest()

        hash_is_valid = hash_value.upper() == response.MD5_Hash

    if response.is_approved and hash_is_valid:
        payment_was_successful.send(sender=response)
    else:
        payment_was_flagged.send(sender=response)

    return render(request, 'authorizenet/sim_payment.html')


class AIMPayment(object):
    """
    Class to handle credit card payments to Authorize.NET
    """

    processing_error = ("There was an error processing your payment. "
                        "Check your information and try again.")
    form_error = "Please correct the errors below and try again."

    def __init__(self,
                 extra_data={},
                 payment_form_class=AIMPaymentForm,
                 context={},
                 billing_form_class=BillingAddressForm,
                 shipping_form_class=None,
                 payment_template="authorizenet/aim_payment.html",
                 success_template='authorizenet/aim_success.html',
                 initial_data={}):
        self.extra_data = extra_data
        self.payment_form_class = payment_form_class
        self.payment_template = payment_template
        self.success_template = success_template
        self.context = context
        self.initial_data = initial_data
        self.billing_form_class = billing_form_class
        self.shipping_form_class = shipping_form_class

    def __call__(self, request):
        self.request = request
        if request.method == "GET":
            return self.render_payment_form()
        else:
            return self.validate_payment_form()

    def render_payment_form(self):
        self.context['payment_form'] = self.payment_form_class(
                initial=self.initial_data)
        self.context['billing_form'] = self.billing_form_class(
                initial=self.initial_data)
        if self.shipping_form_class:
            self.context['shipping_form'] = self.shipping_form_class(
                    initial=self.initial_data)
        return render(
            self.request,
            self.payment_template,
            self.context
        )

    def validate_payment_form(self):
        payment_form = self.payment_form_class(self.request.POST)
        billing_form = self.billing_form_class(self.request.POST)
        
        if self.shipping_form_class:
            shipping_form = self.shipping_form_class(self.request.POST)

        #if shipping for exists also validate it
        if payment_form.is_valid() and billing_form.is_valid() and (not self.shipping_form_class or shipping_form.is_valid()):
            
            if not self.shipping_form_class:
                args = payment_form, billing_form
            else:
                args = payment_form, billing_form, shipping_form
            
            form_data = combine_form_data(*args)
            response = process_payment(form_data, self.extra_data)
            self.context['response'] = response
            if response.is_approved:
                return render(
                    self.request,
                    self.success_template,
                    self.context
                )
            else:
                self.context['errors'] = self.processing_error
        self.context['payment_form'] = payment_form
        self.context['billing_form'] = billing_form
        if self.shipping_form_class:
            self.context['shipping_form'] = shipping_form
        self.context.setdefault('errors', self.form_error)
        return render(
            self.request,
            self.payment_template,
            self.context
        )


class PaymentProfileCreateView(CreateView):
    """
    View for creating a CustomerPaymentProfile instance

    CustomerProfile instance will be created automatically if needed.
    """

    template_name = 'authorizenet/create_payment_profile.html'
    form_class = CustomerPaymentForm

    def get_form_kwargs(self):
        kwargs = super(PaymentProfileCreateView, self).get_form_kwargs()
        kwargs['customer'] = self.request.user
        return kwargs


class PaymentProfileUpdateView(UpdateView):
    """
    View for modifying an existing CustomerPaymentProfile instance
    """

    template_name = 'authorizenet/update_payment_profile.html'
    form_class = CustomerPaymentForm

    def get_form_kwargs(self):
        kwargs = super(PaymentProfileUpdateView, self).get_form_kwargs()
        kwargs['customer'] = self.request.user
        return kwargs

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-authorizenet documentation build configuration file, created by
# sphinx-quickstart on Mon Jun 10 13:41:57 2013.
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
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-authorizenet'
copyright = u'2013, Andrii Kurinnyi'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0'
# The full version, including alpha/beta/rc tags.
release = '2.0'

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'django-authorizenetdoc'


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
  ('index', 'django-authorizenet.tex', u'django-authorizenet Documentation',
   u'Andrii Kurinnyi', 'manual'),
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
    ('index', 'django-authorizenet', u'django-authorizenet Documentation',
     [u'Andrii Kurinnyi'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-authorizenet', u'django-authorizenet Documentation',
   u'Andrii Kurinnyi', 'django-authorizenet', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = runtests
import sys
from os.path import abspath, dirname

from django.conf import settings

sys.path.insert(0, abspath(dirname(__file__)))

if not settings.configured:
    settings.configure(
        AUTHNET_DEBUG=False,
        AUTHNET_LOGIN_ID="loginid",
        AUTHNET_TRANSACTION_KEY="key",
        INSTALLED_APPS=(
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django.contrib.sessions',
            'tests',
            'authorizenet',
        ),
        ROOT_URLCONF='tests.urls',
        STATIC_URL='/static/',
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}},
    )


def runtests():
    from django.test.simple import DjangoTestSuiteRunner
    failures = DjangoTestSuiteRunner(failfast=False).run_tests(['tests'])
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from samplestore.models import Invoice, Item, Customer, Address

admin.site.register(Invoice)
admin.site.register(Item)
admin.site.register(Customer)
admin.site.register(Address)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models.signals import post_save

from django.contrib.auth.models import User
from django.contrib.localflavor.us.models import PhoneNumberField, USStateField

from authorizenet.signals import payment_was_successful, payment_was_flagged


ADDRESS_CHOICES = (
     ('billing', 'Billing'),
     ('shipping', 'Shipping'),
)


class Customer(models.Model):
    user = models.ForeignKey(User)
    shipping_same_as_billing = models.BooleanField(default=True)
    cim_profile_id = models.CharField(max_length=10)

    def __unicode__(self):
        return self.user.username


class Address(models.Model):
    type = models.CharField(max_length=10, choices=ADDRESS_CHOICES)
    customer = models.ForeignKey(Customer)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=60)
    city = models.CharField(max_length=40)
    state = USStateField()
    zip_code = models.CharField(max_length=20)
    phone = PhoneNumberField(blank=True)
    fax = PhoneNumberField(blank=True)

    def __unicode__(self):
        return self.customer.user.username


class Item(models.Model):
    title = models.CharField(max_length=55)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __unicode__(self):
        return self.title


class Invoice(models.Model):
    customer = models.ForeignKey(Customer)
    item = models.ForeignKey(Item)

    def __unicode__(self):
        return u"<Invoice: %d - %s>" % (self.id, self.customer.user.username)


def create_customer_profile(sender, instance=None, **kwargs):
    if instance is None:
        return
    profile, created = Customer.objects.get_or_create(user=instance)


post_save.connect(create_customer_profile, sender=User)


def successfull_payment(sender, **kwargs):
    response = sender
    # do something with the response


def flagged_payment(sender, **kwargs):
    response = sender
    # do something with the response


payment_was_successful.connect(successfull_payment)
payment_was_flagged.connect(flagged_payment)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('samplestore.views',
    url(r'^commit/(\d+)/$', 'commit_to_buy', name="samplestore_commit_to_buy"),
    url(r'^make_payment/(\d+)/$', 'make_payment',
        name="samplestore_make_payment"),
    url(r'^$', 'items', name="samplestore_items"),
    url(r'^capture/(\d+)/$', 'capture', name="samplestore_capture"),
    url(r'^capture/index/$', 'capture_index',
        name="samplestore_capture_index"),
    url(r'^create_invoice/(\d+)/$', 'create_invoice',
        name="samplestore_create_invoice"),
    url(r'^create_invoice/(\d+)/auth/$', 'create_invoice',
        {'auth_only': True}, name="samplestore_create_invoice_auth"),
    url(r'^make_direct_payment/(\d+)/$', 'make_direct_payment',
        name="samplestore_make_direct_payment"),
    url(r'^make_direct_payment/(\d+)/auth/$', 'make_direct_payment',
        {'auth_only': True}, name="samplestore_make_direct_payment_auth"),
    
    url(r'^edit_cim_profile/$', 'edit_cim_profile',
        name='edit_cim_profile'),
)

########NEW FILE########
__FILENAME__ = views
import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required

from authorizenet import AUTHNET_POST_URL, AUTHNET_TEST_POST_URL
from authorizenet.forms import SIMPaymentForm, SIMBillingForm, ShippingAddressForm
from authorizenet.models import Response
from authorizenet.views import AIMPayment
from authorizenet.utils import get_fingerprint, capture_transaction

from samplestore.models import Invoice, Item, Address


def items(request):
    return render_to_response('samplestore/items.html',
            {'items': Item.objects.all()},
            context_instance=RequestContext(request))


@login_required
def commit_to_buy(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.POST:
        if "yes" in request.POST:
            invoice = Invoice.objects.create(
                    customer=request.user.get_profile(),
                    item=item)
            return HttpResponseRedirect(reverse('samplestore_make_payment',
                args=[invoice.id]))
        else:
            return HttpResponseRedirect(reverse('samplestore_items'))
    return render_to_response('samplestore/commit_to_buy.html',
            {'item': item},
            context_instance=RequestContext(request))


@login_required
def make_payment(request, invoice_id):
    domain = Site.objects.get_current().domain
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.customer.user != request.user:
        raise Http404
    params = {
        'x_amount': "%.2f" % invoice.item.price,
        'x_fp_sequence': invoice_id,
        'x_invoice_num': invoice_id,
        'x_description': invoice.item.title,
        'x_fp_timestamp': str(int(time.time())),
        'x_relay_url': "http://" + domain + reverse("authnet_sim_payment"),
        }

    try:
        ba = invoice.customer.address_set.get(type='billing')
        billing_params = {'x_first_name': ba.first_name,
                          'x_last_name': ba.last_name,
                          'x_company': ba.company,
                          'x_address': ba.address,
                          'x_city': ba.city,
                          'x_state': ba.state,
                          'x_zip': ba.zip_code,
                          'x_country': "United States",
                          'x_phone': ba.phone,
                          'x_fax': ba.fax,
                          'x_email': request.user.email,
                          'x_cust_id': invoice.customer.id}
        billing_form = SIMBillingForm(initial=billing_params)
    except Address.DoesNotExist:
        billing_form = None

    params['x_fp_hash'] = get_fingerprint(invoice_id,
            params['x_fp_timestamp'],
            params['x_amount'])
    form = SIMPaymentForm(initial=params)
    if settings.DEBUG:
        post_url = AUTHNET_TEST_POST_URL
    else:
        post_url = AUTHNET_POST_URL
    return render_to_response('samplestore/make_payment.html',
            {'form': form,
             'billing_form': billing_form,
             'post_url': post_url},
            context_instance=RequestContext(request))


@login_required
def create_invoice(request, item_id, auth_only=False):
    item = get_object_or_404(Item, id=item_id)
    invoice = Invoice.objects.create(item=item,
            customer=request.user.get_profile())
    if auth_only:
        final_url = reverse('samplestore_make_direct_payment_auth',
                args=[invoice.id])
    else:
        final_url = reverse('samplestore_make_direct_payment',
                args=[invoice.id])
    return HttpResponseRedirect(final_url)


@login_required
def make_direct_payment(request, invoice_id, auth_only=False):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.customer.user != request.user:
        raise Http404
    try:
        ba = invoice.customer.address_set.get(type='billing')
        initial_data = {'first_name': ba.first_name,
                        'last_name': ba.last_name,
                        'company': ba.company,
                        'address': ba.address,
                        'city': ba.city,
                        'state': ba.state,
                        'zip': ba.zip_code}
        extra_data = {'phone': ba.phone,
                      'fax': ba.fax,
                      'email': request.user.email,
                      'cust_id': invoice.customer.id}
    except Address.DoesNotExist:
        initial_data = {}
        extra_data = {}
    if auth_only:
        extra_data['type'] = 'AUTH_ONLY'
    extra_data['amount'] = "%.2f" % invoice.item.price
    extra_data['invoice_num'] = invoice.id
    extra_data['description'] = invoice.item.title
    pp = AIMPayment(
        extra_data=extra_data,
        context={'item': invoice.item},
        initial_data=initial_data,
        shipping_form_class=ShippingAddressForm
    )
    return pp(request)


@login_required
def capture_index(request):
    responses = Response.objects.filter(type='auth_only')
    if request.user.is_staff:
        return render_to_response('samplestore/capture_index.html',
                {'responses': responses},
                 context_instance=RequestContext(request))
    raise Http404


@login_required
def capture(request, id):
    response = get_object_or_404(Response, id=id, type='auth_only')
    if Response.objects.filter(trans_id=response.trans_id,
            type='prior_auth_capture').count() > 0:
        raise Http404
    if request.user.is_staff:
        new_response = capture_transaction(response)
        return render_to_response('samplestore/capture.html',
                {'response': response,
                 'new_response': new_response},
                 context_instance=RequestContext(request))
    raise Http404


from authorizenet.cim import GetHostedProfilePageRequest, CreateProfileRequest, \
                             get_profile
from authorizenet.forms import HostedCIMProfileForm

@login_required
def edit_cim_profile(request):
    customer = request.user.get_profile()
    if not customer.cim_profile_id:
        # Create a new empty profile
        helper = CreateProfileRequest(request.user.id)
        resp = helper.get_response()
        if resp.success:
            customer.cim_profile_id = helper.profile_id
            customer.save()
        else:
            # since this is a sample app, we'll just raise an exception
            raise Exception("Error making Authorize.NET request: %s" % resp.result_text)
    
    # Get the token for displaying the hosted CIM form
    settings = {
        # Pass these when integrating the form as a redirect:
        #'hostedProfileReturnUrl': 'http://localhost:8000/edit_cim_profile',
        #'hostedProfileReturnUrlText': 'Back to the django-authorizenet sample app',
        
        # Pass 'false' for iframes, and 'true' for redirects
        #'hostedProfilePageBorderVisible',
        
        # Pass this for iframes for automatic resizing
        #'hostedProfileIFrameCommunicatorUrl'
        
        # Optional:
        'hostedProfileHeadingBgColor': '#092E20'
    }
    helper = GetHostedProfilePageRequest(customer.cim_profile_id, **settings)
    resp = helper.get_response()
    if not resp.success:
        raise Exception("Error making Authorize.NET request: %s" % resp.result_text)
    
    form = HostedCIMProfileForm(helper.token)
    
    # Optional - retrieve the current payment profile information for display
    response, payment_profiles, shipping_profiles = get_profile(customer.cim_profile_id)
    
    return render_to_response('samplestore/edit_cim_profile.html',
                              {'form': form,
                               'customer': customer,
                               'payment_profiles': payment_profiles,
                               'shipping_profiles': shipping_profiles},
                              context_instance=RequestContext(request))
                                         

########NEW FILE########
__FILENAME__ = settings
# Django settings for authnetsite project.

import os.path

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

try:
    from local_settings import DEBUG
except ImportError:
    DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
   # ('Your name', 'email@example.com'),
)

AUTH_PROFILE_MODULE = 'samplestore.Customer'

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':'django.db.backends.sqlite3',    # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME':'dev.db', # Or path to database file if using sqlite3.
        'USER':'',             # Not used with sqlite3.
        'PASSWORD':'',         # Not used with sqlite3.
        'HOST':'',             # Set to empty string for localhost. Not used with sqlite3.
        'PORT':''             # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

LOGIN_REDIRECT_URL = '/store/'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '=21(@m#)-$5r(cc110zpy$v4od_45r!k1nz!uq@v$w17&!i8=%'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.request",
    "django.core.context_processors.media",
    "django.core.context_processors.csrf"
    )

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.redirects',
    'django.contrib.staticfiles',
    'authorizenet',
    'samplestore',
)

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, include, patterns
from django.conf import settings
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    url(r'^$', RedirectView.as_view(url='/store/')),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', name="auth_login"),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login', name="auth_logout"),
    url(r'^authnet/', include('authorizenet.urls')),
    url(r'^store/', include('samplestore.urls')),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = cim
from copy import deepcopy
from datetime import datetime
from django.test import TestCase
from xml.dom.minidom import parseString
from httmock import HTTMock

from authorizenet.cim import extract_form_data, extract_payment_form_data, \
    add_profile

from .utils import xml_to_dict
from .mocks import cim_url_match, customer_profile_success
from .test_data import create_profile_success


class ExtractFormDataTests(TestCase):

    """Tests for utility functions converting form data to CIM data"""

    def test_extract_form_data(self):
        new_data = extract_form_data({'word': "1", 'multi_word_str': "2"})
        self.assertEqual(new_data, {'word': "1", 'multiWordStr': "2"})

    def test_extract_payment_form_data(self):
        data = extract_payment_form_data({
            'card_number': "1111",
            'expiration_date': datetime(2020, 5, 1),
            'card_code': "123",
        })
        self.assertEqual(data, {
            'cardNumber': "1111",
            'expirationDate': "2020-05",
            'cardCode': "123",
        })


class AddProfileTests(TestCase):

    """Tests for add_profile utility function"""

    def setUp(self):
        self.payment_form_data = {
            'card_number': "5586086832001747",
            'expiration_date': datetime(2020, 5, 1),
            'card_code': "123",
        }
        self.billing_form_data = {
            'first_name': "Danielle",
            'last_name': "Thompson",
            'company': "",
            'address': "101 Broadway Avenue",
            'city': "San Diego",
            'state': "CA",
            'country': "US",
            'zip': "92101",
        }
        self.request_data = deepcopy(create_profile_success)
        profile = self.request_data['createCustomerProfileRequest']['profile']
        del profile['paymentProfiles']['billTo']['phoneNumber']
        del profile['paymentProfiles']['billTo']['faxNumber']

    def test_add_profile_minimal(self):
        """Success test with minimal complexity"""
        @cim_url_match
        def request_handler(url, request):
            request_xml = parseString(request.body)
            self.assertEqual(xml_to_dict(request_xml), self.request_data)
            return customer_profile_success.format('createCustomerProfileResponse')
        with HTTMock(request_handler):
            result = add_profile(42, self.payment_form_data,
                                 self.billing_form_data)
            response = result.pop('response')
            self.assertEqual(result, {
                'profile_id': '6666',
                'payment_profile_ids': ['7777'],
                'shipping_profile_ids': [],
            })
            self.assertEqual(response.result, 'Ok')
            self.assertEqual(response.result_code, 'I00001')
            self.assertEqual(response.result_text, 'Successful.')
            self.assertIsNone(response.transaction_response)

########NEW FILE########
__FILENAME__ = mocks
from httmock import urlmatch


cim_url_match = urlmatch(scheme='https', netloc=r'^api\.authorize\.net$',
                         path=r'^/xml/v1/request\.api$')


delete_success = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<{0}>'
    '<messages>'
    '<resultCode>Ok</resultCode>'
    '<message><code>I00001</code><text>Successful.</text></message>'
    '</messages>'
    '</{0}>'
)


customer_profile_success = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<{0}>'
    '<messages>'
    '<resultCode>Ok</resultCode>'
    '<message><code>I00001</code><text>Successful.</text></message>'
    '</messages>'
    '<customerProfileId>6666</customerProfileId>'
    '<customerPaymentProfileIdList>'
    '<numericString>7777</numericString>'
    '</customerPaymentProfileIdList>'
    '<customerShippingAddressIdList />'
    '<validationDirectResponseList />'
    '</{0}>'
)


payment_profile_success = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<{0}>'
    '<messages>'
    '<resultCode>Ok</resultCode>'
    '<message><code>I00001</code><text>Successful.</text></message>'
    '</messages>'
    '<customerProfileId>6666</customerProfileId>'
    '<customerPaymentProfileId>7777</customerPaymentProfileId>'
    '</{0}>'
)

########NEW FILE########
__FILENAME__ = models
from httmock import HTTMock, with_httmock
from xml.dom.minidom import parseString
from django.test import TestCase
from authorizenet.models import CustomerProfile

from .utils import create_user, xml_to_dict
from .mocks import cim_url_match, customer_profile_success, delete_success
from .test_data import create_empty_profile_success, delete_profile_success


class RequestError(Exception):
    pass


def error_on_request(url, request):
    raise RequestError("CIM Request")


class CustomerProfileModelTests(TestCase):

    """Tests for CustomerProfile model"""

    def setUp(self):
        self.user = create_user(id=42, username='billy', password='password')

    def create_profile(self):
        return CustomerProfile.objects.create(
            customer=self.user, profile_id='6666', sync=False)

    def test_create_sync_no_data(self):
        @cim_url_match
        def request_handler(url, request):
            request_xml = parseString(request.body)
            self.assertEqual(xml_to_dict(request_xml),
                             create_empty_profile_success)
            return customer_profile_success.format(
                'createCustomerProfileResponse')
        profile = CustomerProfile(customer=self.user)
        with HTTMock(error_on_request):
            self.assertRaises(RequestError, profile.save)
        self.assertEqual(profile.profile_id, '')
        with HTTMock(request_handler):
            profile.save(sync=True)
        self.assertEqual(profile.profile_id, '6666')

    @with_httmock(error_on_request)
    def test_create_no_sync(self):
        profile = CustomerProfile(customer=self.user)
        profile.save(sync=False)
        self.assertEqual(profile.profile_id, '')

    @with_httmock(error_on_request)
    def test_edit(self):
        profile = self.create_profile()
        self.assertEqual(profile.profile_id, '6666')
        profile.profile_id = '7777'
        profile.save()
        self.assertEqual(profile.profile_id, '7777')
        profile.profile_id = '8888'
        profile.save(sync=True)
        self.assertEqual(profile.profile_id, '8888')
        profile.profile_id = '9999'
        profile.save(sync=False)
        self.assertEqual(profile.profile_id, '9999')

    def test_delete(self):
        @cim_url_match
        def request_handler(url, request):
            request_xml = parseString(request.body)
            self.assertEqual(xml_to_dict(request_xml),
                             delete_profile_success)
            return delete_success.format(
                'deleteCustomerProfileResponse')
        profile = self.create_profile()
        with HTTMock(request_handler):
            profile.delete()
        self.assertEqual(profile.__class__.objects.count(), 0)

########NEW FILE########
__FILENAME__ = test_data
create_empty_profile_success = {
    'createCustomerProfileRequest': {
        'xmlns': 'AnetApi/xml/v1/schema/AnetApiSchema.xsd',
        'profile': {
            'merchantCustomerId': '42',
        },
        'merchantAuthentication': {
            'transactionKey': 'key',
            'name': 'loginid',
        },
    }
}


create_profile_success = {
    'createCustomerProfileRequest': {
        'xmlns': 'AnetApi/xml/v1/schema/AnetApiSchema.xsd',
        'profile': {
            'merchantCustomerId': '42',
            'paymentProfiles': {
                'billTo': {
                    'firstName': 'Danielle',
                    'lastName': 'Thompson',
                    'company': '',
                    'phoneNumber': '',
                    'faxNumber': '',
                    'address': '101 Broadway Avenue',
                    'city': 'San Diego',
                    'state': 'CA',
                    'zip': '92101',
                    'country': 'US'
                },
                'payment': {
                    'creditCard': {
                        'cardCode': '123',
                        'cardNumber': "5586086832001747",
                        'expirationDate': '2020-05'
                    }
                }
            }
        },
        'merchantAuthentication': {
            'transactionKey': 'key',
            'name': 'loginid',
        },
    }
}


update_profile_success = {
    'updateCustomerPaymentProfileRequest': {
        'xmlns': 'AnetApi/xml/v1/schema/AnetApiSchema.xsd',
        'customerProfileId': '6666',
        'paymentProfile': {
            'customerPaymentProfileId': '7777',
            'billTo': {
                'firstName': 'Danielle',
                'lastName': 'Thompson',
                'company': '',
                'phoneNumber': '',
                'faxNumber': '',
                'address': '101 Broadway Avenue',
                'city': 'San Diego',
                'state': 'CA',
                'zip': '92101',
                'country': 'US'
            },
            'payment': {
                'creditCard': {
                    'cardCode': '123',
                    'cardNumber': "5586086832001747",
                    'expirationDate': '2020-05'
                }
            }
        },
        'merchantAuthentication': {
            'transactionKey': 'key',
            'name': 'loginid',
        },
    }
}


create_payment_profile_success = {
    'createCustomerPaymentProfileRequest': {
        'xmlns': 'AnetApi/xml/v1/schema/AnetApiSchema.xsd',
        'customerProfileId': '6666',
        'paymentProfile': {
            'billTo': {
                'firstName': 'Danielle',
                'lastName': 'Thompson',
                'phoneNumber': '',
                'faxNumber': '',
                'company': '',
                'address': '101 Broadway Avenue',
                'city': 'San Diego',
                'state': 'CA',
                'zip': '92101',
                'country': 'US'
            },
            'payment': {
                'creditCard': {
                    'cardCode': '123',
                    'cardNumber': "5586086832001747",
                    'expirationDate': '2020-05'
                }
            }
        },
        'merchantAuthentication': {
            'transactionKey': 'key',
            'name': 'loginid',
        },
    }
}


delete_profile_success = {
    'deleteCustomerProfileRequest': {
        'xmlns': u'AnetApi/xml/v1/schema/AnetApiSchema.xsd',
        'customerProfileId': '6666',
        'merchantAuthentication': {
            'transactionKey': 'key',
            'name': 'loginid'
        },
    },
}

########NEW FILE########
__FILENAME__ = utils
from django.contrib.auth.models import User


def create_user(id=None, username='', password=''):
    user = User(username=username)
    user.id = id
    user.set_password(password)
    user.save()
    return user


def xml_to_dict(node):
    """Recursively convert minidom XML node to dictionary"""
    node_data = {}
    if node.nodeType == node.TEXT_NODE:
        node_data = node.data
    elif node.nodeType not in (node.DOCUMENT_NODE, node.DOCUMENT_TYPE_NODE):
        node_data.update(node.attributes.items())
    if node.nodeType not in (node.TEXT_NODE, node.DOCUMENT_TYPE_NODE):
        for child in node.childNodes:
            child_name, child_data = xml_to_dict(child)
            if not child_data:
                child_data = ''
            if child_name not in node_data:
                node_data[child_name] = child_data
            else:
                if not isinstance(node_data[child_name], list):
                    node_data[child_name] = [node_data[child_name]]
                node_data[child_name].append(child_data)
        if node_data.keys() == ['#text']:
            node_data = node_data['#text']
    if node.nodeType == node.DOCUMENT_NODE:
        return node_data
    else:
        return node.nodeName, node_data

########NEW FILE########
__FILENAME__ = views
from datetime import date
from django.test import LiveServerTestCase
from xml.dom.minidom import parseString
from httmock import HTTMock

from authorizenet.models import CustomerProfile, CustomerPaymentProfile

from .utils import create_user, xml_to_dict
from .mocks import cim_url_match, customer_profile_success, \
    payment_profile_success
from .test_data import create_profile_success, update_profile_success, \
    create_payment_profile_success


class PaymentProfileCreationTests(LiveServerTestCase):

    def setUp(self):
        self.user = create_user(id=42, username='billy', password='password')
        self.client.login(username='billy', password='password')

    def test_create_new_customer_get(self):
        response = self.client.get('/customers/create')
        self.assertNotIn("This field is required", response.content)
        self.assertIn("Credit Card Number", response.content)
        self.assertIn("City", response.content)

    def test_create_new_customer_post_error(self):
        response = self.client.post('/customers/create')
        self.assertIn("This field is required", response.content)
        self.assertIn("Credit Card Number", response.content)
        self.assertIn("City", response.content)

    def test_create_new_customer_post_success(self):
        @cim_url_match
        def create_customer_success(url, request):
            request_xml = parseString(request.body)
            self.assertEqual(xml_to_dict(request_xml), create_profile_success)
            return customer_profile_success.format('createCustomerProfileResponse')
        with HTTMock(create_customer_success):
            response = self.client.post('/customers/create', {
                'card_number': "5586086832001747",
                'expiration_date_0': "5",
                'expiration_date_1': "2020",
                'card_code': "123",
                'first_name': "Danielle",
                'last_name': "Thompson",
                'address': "101 Broadway Avenue",
                'city': "San Diego",
                'state': "CA",
                'country': "US",
                'zip': "92101",
            }, follow=True)
        self.assertIn("success", response.content)

    def test_create_new_payment_profile_post_success(self):
        @cim_url_match
        def request_handler(url, request):
            request_xml = parseString(request.body)
            self.assertEqual(xml_to_dict(request_xml),
                             create_payment_profile_success)
            return payment_profile_success.format('createCustomerPaymentProfileResponse')
        CustomerProfile.objects.create(customer=self.user, profile_id='6666', sync=False)
        with HTTMock(request_handler):
            response = self.client.post('/customers/create', {
                'card_number': "5586086832001747",
                'expiration_date_0': "5",
                'expiration_date_1': "2020",
                'card_code': "123",
                'first_name': "Danielle",
                'last_name': "Thompson",
                'address': "101 Broadway Avenue",
                'city': "San Diego",
                'state': "CA",
                'country': "US",
                'zip': "92101",
            }, follow=True)
        self.assertIn("success", response.content)


class PaymentProfileUpdateTests(LiveServerTestCase):

    def setUp(self):
        self.user = create_user(id=42, username='billy', password='password')
        profile = CustomerProfile(customer=self.user, profile_id='6666')
        profile.save(sync=False)
        self.payment_profile = CustomerPaymentProfile(
            customer=self.user,
            customer_profile=profile,
            payment_profile_id='7777',
        )
        self.payment_profile.save(sync=False)
        self.client.login(username='billy', password='password')

    def test_update_profile_get(self):
        response = self.client.get('/customers/update')
        self.assertNotIn("This field is required", response.content)
        self.assertIn("Credit Card Number", response.content)
        self.assertIn("City", response.content)

    def test_update_profile_post_error(self):
        response = self.client.post('/customers/update')
        self.assertIn("This field is required", response.content)
        self.assertIn("Credit Card Number", response.content)
        self.assertIn("City", response.content)

    def test_update_profile_post_success(self):
        @cim_url_match
        def create_customer_success(url, request):
            request_xml = parseString(request.body)
            self.assertEqual(xml_to_dict(request_xml),
                             update_profile_success)
            return customer_profile_success.format('updateCustomerProfileResponse')
        with HTTMock(create_customer_success):
            response = self.client.post('/customers/update', {
                'card_number': "5586086832001747",
                'expiration_date_0': "5",
                'expiration_date_1': "2020",
                'card_code': "123",
                'first_name': "Danielle",
                'last_name': "Thompson",
                'address': "101 Broadway Avenue",
                'city': "San Diego",
                'state': "CA",
                'country': "US",
                'zip': "92101",
            }, follow=True)
        self.assertIn("success", response.content)
        payment_profile = self.user.customer_profile.payment_profiles.get()
        self.assertEqual(payment_profile.raw_data, {
            'id': payment_profile.id,
            'customer_profile': self.user.customer_profile.id,
            'customer': self.user.id,
            'payment_profile_id': '7777',
            'card_number': 'XXXX1747',
            'expiration_date': date(2020, 5, 31),
            'card_code': None,
            'first_name': 'Danielle',
            'last_name': 'Thompson',
            'company': '',
            'fax_number': '',
            'phone_number': '',
            'address': '101 Broadway Avenue',
            'city': 'San Diego',
            'state': 'CA',
            'country': 'US',
            'zip': '92101',
        })


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns
from .views import CreateCustomerView, UpdateCustomerView, success_view

urlpatterns = patterns(
    '',
    url(r"^customers/create$", CreateCustomerView.as_view()),
    url(r"^customers/update$", UpdateCustomerView.as_view()),
    url(r"^success$", success_view),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from authorizenet.views import PaymentProfileCreateView, PaymentProfileUpdateView


class CreateCustomerView(PaymentProfileCreateView):
    def get_success_url(self):
        return '/success'


class UpdateCustomerView(PaymentProfileUpdateView):

    def get_object(self):
        return self.request.user.customer_profile.payment_profiles.get()

    def get_success_url(self):
        return '/success'


def success_view(request):
    return HttpResponse("success")

########NEW FILE########
