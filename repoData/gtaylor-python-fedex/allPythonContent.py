__FILENAME__ = address_validation
#!/usr/bin/env python
"""
This example shows how to validate addresses. Note that the validation
class can handle up to 100 addresses for validation.
"""
import logging
from example_config import CONFIG_OBJ
from fedex.services.address_validation_service import FedexAddressValidationRequest

# Set this to the INFO level to see the response from Fedex printed in stdout.
logging.basicConfig(level=logging.INFO)

# This is the object that will be handling our tracking request.
# We're using the FedexConfig object from example_config.py in this dir.
connection = FedexAddressValidationRequest(CONFIG_OBJ)

# The AddressValidationOptions are created with default values of None, which
# will cause WSDL validation errors. To make things work, each option needs to
# be explicitly set or deleted.

## Set the flags we want to True (or a value).
connection.AddressValidationOptions.CheckResidentialStatus = True
connection.AddressValidationOptions.VerifyAddresses = True
connection.AddressValidationOptions.RecognizeAlternateCityNames = True
connection.AddressValidationOptions.MaximumNumberOfMatches = 3

## Delete the flags we don't want.
del connection.AddressValidationOptions.ConvertToUpperCase
del connection.AddressValidationOptions.ReturnParsedElements

## *Accuracy fields can be TIGHT, EXACT, MEDIUM, or LOOSE. Or deleted.
connection.AddressValidationOptions.StreetAccuracy = 'LOOSE'
del connection.AddressValidationOptions.DirectionalAccuracy
del connection.AddressValidationOptions.CompanyNameAccuracy

## Create some addresses to validate
address1 = connection.create_wsdl_object_of_type('AddressToValidate')
address1.CompanyName = 'International Paper'
address1.Address.StreetLines = ['155 Old Greenville Hwy', 'Suite 103']
address1.Address.City = 'Clemson'
address1.Address.StateOrProvinceCode = 'SC'
address1.Address.PostalCode = 29631
address1.Address.CountryCode = 'US'
address1.Address.Residential = False
connection.add_address(address1)

address2 = connection.create_wsdl_object_of_type('AddressToValidate')
address2.Address.StreetLines = ['320 S Cedros', '#200']
address2.Address.City = 'Solana Beach'
address2.Address.StateOrProvinceCode = 'CA'
address2.Address.PostalCode = 92075
address2.Address.CountryCode = 'US'
connection.add_address(address2)

## Send the request and print the response
connection.send_request()
print connection.response

########NEW FILE########
__FILENAME__ = create_shipment
#!/usr/bin/env python
"""
This example shows how to create shipments. The variables populated below
represents the minimum required values. You will need to fill all of these, or
risk seeing a SchemaValidationError exception thrown.

Near the bottom of the module, you'll see some different ways to handle the
label data that is returned with the reply.
"""
import logging
import binascii
from example_config import CONFIG_OBJ
from fedex.services.ship_service import FedexProcessShipmentRequest

# Set this to the INFO level to see the response from Fedex printed in stdout.
logging.basicConfig(level=logging.INFO)

# This is the object that will be handling our tracking request.
# We're using the FedexConfig object from example_config.py in this dir.
shipment = FedexProcessShipmentRequest(CONFIG_OBJ)

# This is very generalized, top-level information.
# REGULAR_PICKUP, REQUEST_COURIER, DROP_BOX, BUSINESS_SERVICE_CENTER or STATION
shipment.RequestedShipment.DropoffType = 'REGULAR_PICKUP'

# See page 355 in WS_ShipService.pdf for a full list. Here are the common ones:
# STANDARD_OVERNIGHT, PRIORITY_OVERNIGHT, FEDEX_GROUND, FEDEX_EXPRESS_SAVER
shipment.RequestedShipment.ServiceType = 'PRIORITY_OVERNIGHT'

# What kind of package this will be shipped in.
# FEDEX_BOX, FEDEX_PAK, FEDEX_TUBE, YOUR_PACKAGING
shipment.RequestedShipment.PackagingType = 'FEDEX_PAK'

# No idea what this is.
# INDIVIDUAL_PACKAGES, PACKAGE_GROUPS, PACKAGE_SUMMARY 
shipment.RequestedShipment.PackageDetail = 'INDIVIDUAL_PACKAGES'

# Shipper contact info.
shipment.RequestedShipment.Shipper.Contact.PersonName = 'Sender Name'
shipment.RequestedShipment.Shipper.Contact.CompanyName = 'Some Company'
shipment.RequestedShipment.Shipper.Contact.PhoneNumber = '9012638716'

# Shipper address.
shipment.RequestedShipment.Shipper.Address.StreetLines = ['Address Line 1']
shipment.RequestedShipment.Shipper.Address.City = 'Herndon'
shipment.RequestedShipment.Shipper.Address.StateOrProvinceCode = 'VA'
shipment.RequestedShipment.Shipper.Address.PostalCode = '20171'
shipment.RequestedShipment.Shipper.Address.CountryCode = 'US'
shipment.RequestedShipment.Shipper.Address.Residential = True

# Recipient contact info.
shipment.RequestedShipment.Recipient.Contact.PersonName = 'Recipient Name'
shipment.RequestedShipment.Recipient.Contact.CompanyName = 'Recipient Company'
shipment.RequestedShipment.Recipient.Contact.PhoneNumber = '9012637906'

# Recipient address
shipment.RequestedShipment.Recipient.Address.StreetLines = ['Address Line 1']
shipment.RequestedShipment.Recipient.Address.City = 'Herndon'
shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = 'VA'
shipment.RequestedShipment.Recipient.Address.PostalCode = '20171'
shipment.RequestedShipment.Recipient.Address.CountryCode = 'US'
# This is needed to ensure an accurate rate quote with the response.
shipment.RequestedShipment.Recipient.Address.Residential = True

# Who pays for the shipment?
# RECIPIENT, SENDER or THIRD_PARTY
shipment.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER' 

# Specifies the label type to be returned.
# LABEL_DATA_ONLY or COMMON2D
shipment.RequestedShipment.LabelSpecification.LabelFormatType = 'COMMON2D'

# Specifies which format the label file will be sent to you in.
# DPL, EPL2, PDF, PNG, ZPLII
shipment.RequestedShipment.LabelSpecification.ImageType = 'PNG'

# To use doctab stocks, you must change ImageType above to one of the
# label printer formats (ZPLII, EPL2, DPL).
# See documentation for paper types, there quite a few.
shipment.RequestedShipment.LabelSpecification.LabelStockType = 'PAPER_4X6'

# This indicates if the top or bottom of the label comes out of the 
# printer first.
# BOTTOM_EDGE_OF_TEXT_FIRST or TOP_EDGE_OF_TEXT_FIRST
shipment.RequestedShipment.LabelSpecification.LabelPrintingOrientation = 'BOTTOM_EDGE_OF_TEXT_FIRST'

package1_weight = shipment.create_wsdl_object_of_type('Weight')
# Weight, in pounds.
package1_weight.Value = 1.0
package1_weight.Units = "LB"

package1 = shipment.create_wsdl_object_of_type('RequestedPackageLineItem')
package1.Weight = package1_weight
# Un-comment this to see the other variables you may set on a package.
#print package1

# This adds the RequestedPackageLineItem WSDL object to the shipment. It
# increments the package count and total weight of the shipment for you.
shipment.add_package(package1)

# If you'd like to see some documentation on the ship service WSDL, un-comment
# this line. (Spammy).
#print shipment.client

# Un-comment this to see your complete, ready-to-send request as it stands
# before it is actually sent. This is useful for seeing what values you can
# change.
#print shipment.RequestedShipment

# If you want to make sure that all of your entered details are valid, you
# can call this and parse it just like you would via send_request(). If
# shipment.response.HighestSeverity == "SUCCESS", your shipment is valid.
#shipment.send_validation_request()

# Fires off the request, sets the 'response' attribute on the object.
shipment.send_request()

# This will show the reply to your shipment being sent. You can access the
# attributes through the response attribute on the request object. This is
# good to un-comment to see the variables returned by the Fedex reply.
print shipment.response

# Here is the overall end result of the query.
print "HighestSeverity:", shipment.response.HighestSeverity
# Getting the tracking number from the new shipment.
print "Tracking #:", shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].TrackingIds[0].TrackingNumber
# Net shipping costs.
print "Net Shipping Cost (US$):", shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].PackageRating.PackageRateDetails[0].NetCharge.Amount

# Get the label image in ASCII format from the reply. Note the list indices
# we're using. You'll need to adjust or iterate through these if your shipment
# has multiple packages.
ascii_label_data = shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].Label.Parts[0].Image
# Convert the ASCII data to binary.
label_binary_data = binascii.a2b_base64(ascii_label_data)

"""
This is an example of how to dump a label to a PNG file.
"""
# This will be the file we write the label out to.
png_file = open('example_shipment_label.png', 'wb')
png_file.write(label_binary_data)
png_file.close()

"""
This is an example of how to print the label to a serial printer. This will not
work for all label printers, consult your printer's documentation for more
details on what formats it can accept.
"""
# Pipe the binary directly to the label printer. Works under Linux
# without requiring PySerial. This WILL NOT work on other platforms.
#label_printer = open("/dev/ttyS0", "w")
#label_printer.write(label_binary_data)
#label_printer.close()

"""
This is a potential cross-platform solution using pySerial. This has not been
tested in a long time and may or may not work. For Windows, Mac, and other
platforms, you may want to go this route.
"""
#import serial
#label_printer = serial.Serial(0)
#print "SELECTED SERIAL PORT: "+ label_printer.portstr
#label_printer.write(label_binary_data)
#label_printer.close()
########NEW FILE########
__FILENAME__ = delete_shipment
#!/usr/bin/env python
"""
This example shows how to delete existing shipments.
"""
import logging
from example_config import CONFIG_OBJ
from fedex.services.ship_service import FedexDeleteShipmentRequest

# Set this to the INFO level to see the response from Fedex printed in stdout.
logging.basicConfig(level=logging.INFO)

# This is the object that will be handling our tracking request.
# We're using the FedexConfig object from example_config.py in this dir.
del_request = FedexDeleteShipmentRequest(CONFIG_OBJ)

# Either delete all packages in a shipment, or delete an individual package.
# Docs say this isn't required, but the WSDL won't validate without it.
# DELETE_ALL_PACKAGES, DELETE_ONE_PACKAGE
del_request.DeletionControlType = "DELETE_ALL_PACKAGES"

# The tracking number of the shipment to delete.
del_request.TrackingId.TrackingNumber = '794798682968'

# What kind of shipment the tracking number used.
# Docs say this isn't required, but the WSDL won't validate without it.
# EXPRESS, GROUND, or USPS
del_request.TrackingId.TrackingIdType = 'EXPRESS'

# Fires off the request, sets the 'response' attribute on the object.
del_request.send_request()

# See the response printed out.
print del_request.response

########NEW FILE########
__FILENAME__ = example_config
"""
This file holds various configuration options used for all of the examples.

You will need to change the values below to match your test account.
"""
import os
import sys
# Use the fedex directory included in the downloaded package instead of
# any globally installed versions.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fedex.config import FedexConfig

# Change these values to match your testing account/meter number.
CONFIG_OBJ = FedexConfig(key='xxxxxxxxxxxxxxxx',
                         password='xxxxxxxxxxxxxxxxxxxxxxxxx',
                         account_number='#########',
                         meter_number='#########',
                         use_test_server=True)
########NEW FILE########
__FILENAME__ = postal_inquiry
#!/usr/bin/env python
"""
PostalCodeInquiryRequest classes are used to validate and receive additional
information about postal codes.
"""
import logging
from example_config import CONFIG_OBJ
from fedex.services.package_movement import PostalCodeInquiryRequest

# Set this to the INFO level to see the response from Fedex printed in stdout.
logging.basicConfig(level=logging.INFO)

# We're using the FedexConfig object from example_config.py in this dir.
inquiry = PostalCodeInquiryRequest(CONFIG_OBJ)
inquiry.PostalCode = '29631'
inquiry.CountryCode = 'US'

# Fires off the request, sets the 'response' attribute on the object.
inquiry.send_request()

# See the response printed out.
print inquiry.response
########NEW FILE########
__FILENAME__ = rate_request
#!/usr/bin/env python
"""
This example shows how to use the FedEx RateRequest service. 
The variables populated below represents the minimum required values. 
You will need to fill all of these, or risk seeing a SchemaValidationError 
exception thrown by suds.

TIP: Near the bottom of the module, see how to check the if the destination 
     is Out of Delivery Area (ODA).
"""
import logging
from example_config import CONFIG_OBJ
from fedex.services.rate_service import FedexRateServiceRequest

# Set this to the INFO level to see the response from Fedex printed in stdout.
logging.basicConfig(level=logging.INFO)

# This is the object that will be handling our tracking request.
# We're using the FedexConfig object from example_config.py in this dir.
rate_request = FedexRateServiceRequest(CONFIG_OBJ)

# If you wish to have transit data returned with your request you
# need to uncomment the following
# rate_request.ReturnTransitAndCommit = True

# This is very generalized, top-level information.
# REGULAR_PICKUP, REQUEST_COURIER, DROP_BOX, BUSINESS_SERVICE_CENTER or STATION
rate_request.RequestedShipment.DropoffType = 'REGULAR_PICKUP'

# See page 355 in WS_ShipService.pdf for a full list. Here are the common ones:
# STANDARD_OVERNIGHT, PRIORITY_OVERNIGHT, FEDEX_GROUND, FEDEX_EXPRESS_SAVER
# To receive rates for multiple ServiceTypes set to None.
rate_request.RequestedShipment.ServiceType = 'FEDEX_GROUND'

# What kind of package this will be shipped in.
# FEDEX_BOX, FEDEX_PAK, FEDEX_TUBE, YOUR_PACKAGING
rate_request.RequestedShipment.PackagingType = 'YOUR_PACKAGING'

# No idea what this is.
# INDIVIDUAL_PACKAGES, PACKAGE_GROUPS, PACKAGE_SUMMARY 
rate_request.RequestedShipment.PackageDetail = 'INDIVIDUAL_PACKAGES'

# Shipper's address
rate_request.RequestedShipment.Shipper.Address.PostalCode = '29631'
rate_request.RequestedShipment.Shipper.Address.CountryCode = 'US'
rate_request.RequestedShipment.Shipper.Address.Residential = False

# Recipient address
rate_request.RequestedShipment.Recipient.Address.PostalCode = '27577'
rate_request.RequestedShipment.Recipient.Address.CountryCode = 'US'
# This is needed to ensure an accurate rate quote with the response.
#rate_request.RequestedShipment.Recipient.Address.Residential = True
#include estimated duties and taxes in rate quote, can be ALL or NONE
rate_request.RequestedShipment.EdtRequestType = 'NONE'

# Who pays for the rate_request?
# RECIPIENT, SENDER or THIRD_PARTY
rate_request.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER' 

package1_weight = rate_request.create_wsdl_object_of_type('Weight')
# Weight, in LB.
package1_weight.Value = 1.0
package1_weight.Units = "LB"

package1 = rate_request.create_wsdl_object_of_type('RequestedPackageLineItem')
package1.Weight = package1_weight
#can be other values this is probably the most common
package1.PhysicalPackaging = 'BOX'
# Un-comment this to see the other variables you may set on a package.
#print package1

# This adds the RequestedPackageLineItem WSDL object to the rate_request. It
# increments the package count and total weight of the rate_request for you.
rate_request.add_package(package1)

# If you'd like to see some documentation on the ship service WSDL, un-comment
# this line. (Spammy).
#print rate_request.client

# Un-comment this to see your complete, ready-to-send request as it stands
# before it is actually sent. This is useful for seeing what values you can
# change.
#print rate_request.RequestedShipment

# Fires off the request, sets the 'response' attribute on the object.
rate_request.send_request()

# This will show the reply to your rate_request being sent. You can access the
# attributes through the response attribute on the request object. This is
# good to un-comment to see the variables returned by the FedEx reply.
#print rate_request.response

# Here is the overall end result of the query.
print "HighestSeverity:", rate_request.response.HighestSeverity

# RateReplyDetails can contain rates for multiple ServiceTypes if ServiceType was set to None
for service in rate_request.response.RateReplyDetails:
    for detail in service.RatedShipmentDetails:
        for surcharge in detail.ShipmentRateDetail.Surcharges:
            if surcharge.SurchargeType == 'OUT_OF_DELIVERY_AREA':
                print "%s: ODA rate_request charge %s" % (service.ServiceType, surcharge.Amount.Amount)
            
    for rate_detail in service.RatedShipmentDetails:
        print "%s: Net FedEx Charge %s %s" % (service.ServiceType, rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Currency,
                rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Amount)


########NEW FILE########
__FILENAME__ = track_shipment
#!/usr/bin/env python
"""
This example shows how to track shipments.
"""
import logging
from example_config import CONFIG_OBJ
from fedex.services.track_service import FedexTrackRequest

# Set this to the INFO level to see the response from Fedex printed in stdout.
logging.basicConfig(level=logging.INFO)

# NOTE: TRACKING IS VERY ERRATIC ON THE TEST SERVERS. YOU MAY NEED TO USE
# PRODUCTION KEYS/PASSWORDS/ACCOUNT #.
# We're using the FedexConfig object from example_config.py in this dir.
track = FedexTrackRequest(CONFIG_OBJ)
track.TrackPackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
track.TrackPackageIdentifier.Value = '798114182456'

# Fires off the request, sets the 'response' attribute on the object.
track.send_request()

# See the response printed out.
print track.response

# Look through the matches (there should only be one for a tracking number
# query), and show a few details about each shipment.
print "== Results =="
for match in track.response.TrackDetails:
    print "Tracking #:", match.TrackingNumber
    print "Status:", match.StatusDescription
########NEW FILE########
__FILENAME__ = base_service
"""
The L{base_service} module contains classes that form the low level foundations
of the Web Service API. Things that many different kinds of requests have in
common may be found here.

In particular, the L{FedexBaseService} class handles most of the basic,
repetetive setup work that most requests do.
"""
import os
import logging
import suds
from suds.client import Client

class FedexBaseServiceException(Exception):
    """
    Exception: Serves as the base exception that other service-related
    exception objects are sub-classed from.
    """
    def __init__(self, error_code, value):
        self.error_code = error_code
        self.value = value
    def __unicode__(self):
        return "%s (Error code: %s)" % (repr(self.value), self.error_code)
    def __str__(self):
        return self.__unicode__()

class FedexFailure(FedexBaseServiceException):
    """
    Exception: The request could not be handled at this time. This is generally
    a server problem.
    """
    pass

class FedexError(FedexBaseServiceException):
    """
    Exception: These are generally problems with the client-provided data.
    """
    pass

class SchemaValidationError(FedexBaseServiceException):
    """
    Exception: There is probably a problem in the data you provided.
    """
    def __init__(self):
        self.error_code = -1
        self.value = "suds encountered an error validating your data against this service's WSDL schema. Please double-check for missing or invalid values, filling all required fields."

class FedexBaseService(object):
    """
    This class is the master class for all Fedex request objects. It gets all
    of the common SOAP objects created via suds and populates them with
    values from a L{FedexConfig} object, along with keyword arguments
    via L{__init__}.

    @note: This object should never be used directly, use one of the included
        sub-classes.
    """
    def __init__(self, config_obj, wsdl_name, *args, **kwargs):
        """
        This constructor should only be called by children of the class. As is
        such, only the optional keyword arguments caught by C{**kwargs} will
        be documented.

        @type customer_transaction_id: L{str}
        @keyword customer_transaction_id: A user-specified identifier to
            differentiate this transaction from others. This value will be
            returned with the response from Fedex.
        """
        self.logger = logging.getLogger('fedex')
        """@ivar: Python logger instance with name 'fedex'."""
        self.config_obj = config_obj
        """@ivar: The FedexConfig object to pull auth info from."""

        # If the config object is set to use the test server, point
        # suds at the test server WSDL directory.
        if config_obj.use_test_server:
            self.logger.info("Using test server.")
            self.wsdl_path = os.path.join(config_obj.wsdl_path,
                                          'test_server_wsdl', wsdl_name)
        else:
            self.logger.info("Using production server.")
            self.wsdl_path = os.path.join(config_obj.wsdl_path, wsdl_name)

        self.client = Client('file:///%s' % self.wsdl_path.lstrip('/'))

        #print self.client

        self.VersionId = None
        """@ivar: Holds details on the version numbers of the WSDL."""
        self.WebAuthenticationDetail = None
        """@ivar: WSDL object that holds authentication info."""
        self.ClientDetail = None
        """@ivar: WSDL object that holds client account details."""
        self.response = None
        """@ivar: The response from Fedex. You will want to pick what you
            want out here here. This object does have a __str__() method,
            you'll want to print or log it to see what possible values
            you can pull."""
        self.TransactionDetail = None
        """@ivar: Holds customer-specified transaction IDs."""

        self.__set_web_authentication_detail()
        self.__set_client_detail()
        self.__set_version_id()
        self.__set_transaction_detail(*args, **kwargs)
        self._prepare_wsdl_objects()

    def __set_web_authentication_detail(self):
        """
        Sets up the WebAuthenticationDetail node. This is required for all
        requests.
        """
        # Start of the authentication stuff.
        WebAuthenticationCredential = self.client.factory.create('WebAuthenticationCredential')
        WebAuthenticationCredential.Key = self.config_obj.key
        WebAuthenticationCredential.Password = self.config_obj.password

        # Encapsulates the auth credentials.
        WebAuthenticationDetail = self.client.factory.create('WebAuthenticationDetail')
        WebAuthenticationDetail.UserCredential = WebAuthenticationCredential
        self.WebAuthenticationDetail = WebAuthenticationDetail

    def __set_client_detail(self):
        """
        Sets up the ClientDetail node, which is required for all shipping
        related requests.
        """
        ClientDetail = self.client.factory.create('ClientDetail')
        ClientDetail.AccountNumber = self.config_obj.account_number
        ClientDetail.MeterNumber = self.config_obj.meter_number
        ClientDetail.IntegratorId = self.config_obj.integrator_id
        if hasattr(ClientDetail, 'Region'):
            ClientDetail.Region = self.config_obj.express_region_code
        self.ClientDetail = ClientDetail

    def __set_transaction_detail(self, *args, **kwargs):
        """
        Checks kwargs for 'customer_transaction_id' and sets it if present.
        """
        customer_transaction_id = kwargs.get('customer_transaction_id', False)
        if customer_transaction_id:
            TransactionDetail = self.client.factory.create('TransactionDetail')
            TransactionDetail.CustomerTransactionId = customer_transaction_id
            self.logger.debug(TransactionDetail)
            self.TransactionDetail = TransactionDetail

    def __set_version_id(self):
        """
        Pulles the versioning info for the request from the child request.
        """
        VersionId = self.client.factory.create('VersionId')
        VersionId.ServiceId = self._version_info['service_id']
        VersionId.Major = self._version_info['major']
        VersionId.Intermediate = self._version_info['intermediate']
        VersionId.Minor = self._version_info['minor']
        self.logger.debug(VersionId)
        self.VersionId = VersionId

    def __prepare_wsdl_objects(self):
        """
        This method should be over-ridden on each sub-class. It instantiates
        any of the required WSDL objects so the user can just print their
        __str__() methods and see what they need to fill in.
        """
        pass

    def __check_response_for_fedex_error(self):
        """
        This checks the response for general Fedex errors that aren't related
        to any one WSDL.
        """
        if self.response.HighestSeverity == "FAILURE":
            for notification in self.response.Notifications:
                if notification.Severity == "FAILURE":
                    raise FedexFailure(notification.Code,
                                       notification.Message)

    def _check_response_for_request_errors(self):
        """
        Override this in each service module to check for errors that are
        specific to that module. For example, invalid tracking numbers in
        a Tracking request.
        """
        if self.response.HighestSeverity == "ERROR":
            for notification in self.response.Notifications:
                if notification.Severity == "ERROR":
                    raise FedexError(notification.Code,
                                     notification.Message)

    def create_wsdl_object_of_type(self, type_name):
        """
        Creates and returns a WSDL object of the specified type.
        """
        return self.client.factory.create(type_name)

    def send_request(self, send_function=None):
        """
        Sends the assembled request on the child object.
        @type send_function: function reference
        @keyword send_function: A function reference (passed without the
            parenthesis) to a function that will send the request. This
            allows for overriding the default function in cases such as
            validation requests.
        """
        # Send the request and get the response back.
        try:
            # If the user has overridden the send function, use theirs
            # instead of the default.
            if send_function:
                # Follow the overridden function.
                self.response = send_function()
            else:
                # Default scenario, business as usual.
                self.response = self._assemble_and_send_request()
        except suds.WebFault:
            # When this happens, throw an informative message reminding the
            # user to check all required variables, making sure they are
            # populated and valid.
            raise SchemaValidationError()

        # Check the response for general Fedex errors/failures that aren't
        # specific to any given WSDL/request.
        self.__check_response_for_fedex_error()
        # Check the response for errors specific to the particular request.
        # This is handled by an overridden method on the child object.
        self._check_response_for_request_errors()

        # Debug output.
        self.logger.debug("== FEDEX QUERY RESULT ==")
        self.logger.debug(self.response)

########NEW FILE########
__FILENAME__ = config
"""
The L{config} module contains the L{FedexConfig} class, which is passed to
the Fedex API calls. It stores useful information such as your Web Services
account numbers and keys.

It is strongly suggested that you create a single L{FedexConfig} object in
your project and pass that to the various API calls, rather than create new
L{FedexConfig} objects haphazardly. This is merely a design suggestion,
treat it as such.
"""
import os
import sys

class FedexConfig(object):
    """
    Base configuration class that is used for the different Fedex SOAP calls.
    These are generally passed to the Fedex request classes as arguments.
    You may instantiate a L{FedexConfig} object with the minimal C{key} and
    C{password} arguments and set the instance variables documented below
    at a later time if you must.
    """
    def __init__(self, key, password, account_number=None, meter_number=None,
                 integrator_id=None, wsdl_path=None, express_region_code=None, use_test_server=False):
        """
        @type key: L{str}
        @param key: Developer test key.
        @type password: L{str}
        @param password: The Fedex-generated password for your Web Systems
            account. This is generally emailed to you after registration.
        @type account_number: L{str}
        @keyword account_number: The account number sent to you by Fedex after
            registering for Web Services.
        @type meter_number: L{str}
        @keyword meter_number: The meter number sent to you by Fedex after
            registering for Web Services.
        @type integrator_id: L{str}
        @keyword integrator_id: The integrator string sent to you by Fedex after
            registering for Web Services.
        @type wsdl_path: L{str}
        @keyword wsdl_path: In the event that you want to override the path to
            your WSDL directory, do so with this argument.
        @type use_test_server: L{bool}
        @keyword use_test_server: When this is True, test server WSDLs are used
            instead of the production server. You will also need to make sure
            that your L{FedexConfig} object has a production account number,
            meter number, authentication key, and password.
        """
        self.key = key
        """@ivar: Developer test key."""
        self.password = password
        """@ivar: Fedex Web Services password."""
        self.account_number = account_number
        """@ivar: Web Services account number."""
        self.meter_number = meter_number
        """@ivar: Web services meter number."""
        self.integrator_id = integrator_id
        """@ivar: Web services integrator ID."""
        self.express_region_code = express_region_code
        """@icar: Web services ExpressRegionCode"""
        self.use_test_server = use_test_server
        """@ivar: When True, point to the test server."""
        
        # Allow overriding of the WDSL path.
        if wsdl_path == None:
            self.wsdl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                          'wsdl')
        else:
            self.wsdl_path = wsdl_path
########NEW FILE########
__FILENAME__ = unix
"""
This module provides a label printing wrapper class for Unix-based
installations. By "Unix", we mean Linux, Mac OS, BSD, and various flavors
of Unix.
"""
import binascii

class DirectDevicePrinter(object):
    """
    This class pipes the label data directly through a /dev/* entry.
    Consequently, this is very Unix/Linux specific. It *MAY* work on Mac too.
    """
    def __init__(self, shipment, device="/dev/ttyS0"):
        """
        Instantiates from a shipment object. You may optionally specify
        a path to a /dev/ device. Defaults to /dev/ttyS0.
        
        @type shipment: L{FedexProcessShipmentRequest}
        @param shipment: A Fedex ProcessShipmentRequest object to pull the
                         printed label data from.
        """
        self.device = device
        """@ivar: A string with the path to the device to print to."""
        self.shipment = shipment
        """@ivar: A reference to the L{FedexProcessShipmentRequest} to print."""
        
    def print_label(self, package_num=None):
        """
        Prints all of a shipment's labels, or optionally just one.
        
        @type package_num: L{int}
        @param package_num: 0-based index of the package to print. This is
                            only useful for shipments with more than one package.
        """
        if package_num:
            packages = [self.shipment.response.CompletedShipmentDetail.CompletedPackageDetails[package_num]]
        else:
            packages = self.shipment.response.CompletedShipmentDetail.CompletedPackageDetails

        for package in packages:
            label_binary = binascii.a2b_base64(package.Label.Parts[0].Image)
            self._print_base64(label_binary)
    
    def _print_base64(self, base64_data):
        """
        Pipe the binary directly to the label printer. Works under Linux
        without requiring PySerial. This is not typically something you
        should call directly, unless you have special needs.
        
        @type base64_data: L{str}
        @param base64_data: The base64 encoded string for the label to print.
        """
        label_file = open(self.device, "w")
        label_file.write(base64_data)
        label_file.close()
########NEW FILE########
__FILENAME__ = address_validation_service
"""
Address Validation Service Module
=================================
This package contains the shipping methods defined by Fedex's 
AddressValidationService WSDL file. Each is encapsulated in a class for 
easy access. For more details on each, refer to the respective class's 
documentation.
"""
from datetime import datetime
from .. base_service import FedexBaseService

class FedexAddressValidationRequest(FedexBaseService):
    """
    This class allows you validate anywhere from one to a hundred addresses
    in one go. Create AddressToValidate WSDL objects and add them to each
    instance of this request using add_address().
    """
    def __init__(self, config_obj, *args, **kwargs):
        """
        @type config_obj: L{FedexConfig}
        @param config_obj: A valid FedexConfig object.        
        """
        self._config_obj = config_obj
        
        # Holds version info for the VersionId SOAP object.
        self._version_info = {'service_id': 'aval', 'major': '2', 
                             'intermediate': '0', 'minor': '0'}
        
        self.AddressValidationOptions = None
        """@ivar: Holds the AddressValidationOptions WSDL object."""
        self.addresses_to_validate = []
        """@ivar: Holds the AddressToValidate WSDL object."""
        # Call the parent FedexBaseService class for basic setup work.
        super(FedexAddressValidationRequest, self).__init__(self._config_obj, 
                                                         'AddressValidationService_v2.wsdl',
                                                         *args, **kwargs)
        
    def _prepare_wsdl_objects(self):
        """
        Create the data structure and get it ready for the WSDL request.
        """
        # This holds some optional options for the request..
        self.AddressValidationOptions = self.client.factory.create('AddressValidationOptions')
                               
        # This is good to review if you'd like to see what the data structure
        # looks like.
        self.logger.debug(self.AddressValidationOptions)
    
    def _assemble_and_send_request(self):
        """
        Fires off the Fedex request.
        
        @warning: NEVER CALL THIS METHOD DIRECTLY. CALL send_request(), 
            WHICH RESIDES ON FedexBaseService AND IS INHERITED.
        """
        # We get an exception like this when specifying an IntegratorId:
        # suds.TypeNotFound: Type not found: 'IntegratorId'
        # Setting it to None does not seem to appease it.
        del self.ClientDetail.IntegratorId
        self.logger.debug(self.WebAuthenticationDetail)
        self.logger.debug(self.ClientDetail)
        self.logger.debug(self.TransactionDetail)
        self.logger.debug(self.VersionId)
        # Fire off the query.
        response = self.client.service.addressValidation(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                        ClientDetail=self.ClientDetail,
                                        TransactionDetail=self.TransactionDetail,
                                        Version=self.VersionId,
                                        RequestTimestamp=datetime.now(),
                                        Options=self.AddressValidationOptions,
                                        AddressesToValidate=self.addresses_to_validate)
        return response

    def add_address(self, address_item):
        """
        Adds an address to self.addresses_to_validate.
        
        @type address_item: WSDL object, type of AddressToValidate WSDL object.
        @keyword address_item: A AddressToValidate, created by
            calling create_wsdl_object_of_type('AddressToValidate') on
            this FedexAddressValidationRequest object. 
            See examples/create_shipment.py for more details.
        """
        self.addresses_to_validate.append(address_item)
########NEW FILE########
__FILENAME__ = package_movement
"""
Package Movement Information Service
====================================
This package contains classes to check service availability, route, and postal
codes. Defined by the PackageMovementInformationService WSDL file. 
"""
import logging
from .. base_service import FedexBaseService, FedexError

class FedexPostalCodeNotFound(FedexError):
    """
    Exception: Sent when the postalcode is missing.
    """
    pass

class FedexInvalidPostalCodeFormat(FedexError):
    """
    Exception: Sent when the postal code is invalid
    """
    pass

class PostalCodeInquiryRequest(FedexBaseService):
    """
    The postal code inquiry enables customers to validate postal codes
    and service commitments.
    """
    def __init__(self, config_obj, postal_code=None, country_code=None, *args, **kwargs):
        """
        Sets up an inquiry request. The optional keyword args
        detailed on L{FedexBaseService} apply here as well.
        
        @type config_obj: L{FedexConfig}
        @param config_obj: A valid FedexConfig object
        @param postal_code: a valid postal code
        @param country_code: ISO country code to which the postal code belongs to.
        """
        self._config_obj = config_obj
        
        # Holds version info for the VersionId SOAP object.
        self._version_info = {'service_id': 'pmis', 'major': '4',
                             'intermediate': '0', 'minor': '0'}
        self.PostalCode = postal_code
        self.CountryCode = country_code
       
       
        # Call the parent FedexBaseService class for basic setup work.
        super(PostalCodeInquiryRequest, self).__init__(self._config_obj,
                                                'PackageMovementInformationService_v4.wsdl',
                                                *args, **kwargs)
        

    def _check_response_for_request_errors(self):
        """
        Checks the response to see if there were any errors specific to
        this WSDL.
        """
        if self.response.HighestSeverity == "ERROR":
            for notification in self.response.Notifications:
                if notification.Severity == "ERROR":
                    if "Postal Code Not Found" in notification.Message:
                        raise FedexPostalCodeNotFound(notification.Code,
                                                         notification.Message)

                    elif "Invalid Postal Code Format" in self.response.Notifications:
                        raise FedexInvalidPostalCodeFormat(notification.Code,
                                                         notification.Message)
                    else:
                        raise FedexError(notification.Code,
                                         notification.Message)
                                         
    def _prepare_wsdl_objects(self):
        pass
 
        
    def _assemble_and_send_request(self):
        """
        Fires off the Fedex request.
        
        @warning: NEVER CALL THIS METHOD DIRECTLY. CALL send_request(), WHICH RESIDES
            ON FedexBaseService AND IS INHERITED.
        """
        client = self.client
        
       
        # We get an exception like this when specifying an IntegratorId:
        # suds.TypeNotFound: Type not found: 'IntegratorId'
        # Setting it to None does not seem to appease it.
        
        del self.ClientDetail.IntegratorId
        
        # Fire off the query.
        response = client.service.postalCodeInquiry(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                        ClientDetail=self.ClientDetail,
                                        TransactionDetail=self.TransactionDetail,
                                        Version=self.VersionId,
                                        PostalCode = self.PostalCode,
                                        CountryCode = self.CountryCode)

        return response
        
########NEW FILE########
__FILENAME__ = rate_service
"""
Rate Service Module
===================
This package contains classes to request pre-ship rating information and to
determine estimated or courtesy billing quotes. Time in Transit can be
returned with the rates if it is specified in the request.
"""
from datetime import datetime
from .. base_service import FedexBaseService

class FedexRateServiceRequest(FedexBaseService):
    """
    This class allows you to get the shipping charges for a particular address. 
    You will need to populate the data structures in self.RequestedShipment, 
    then send the request.
    """
    def __init__(self, config_obj, *args, **kwargs):
        """
        The optional keyword args detailed on L{FedexBaseService} 
        apply here as well.

        @type config_obj: L{FedexConfig}
        @param config_obj: A valid FedexConfig object.        
        """
        self._config_obj = config_obj
        
        # Holds version info for the VersionId SOAP object.
        self._version_info = {'service_id': 'crs', 'major': '8', 
                             'intermediate': '0', 'minor': '0'}
        
        self.RequestedShipment = None
        """@ivar: Holds the RequestedShipment WSDL object."""
        # Call the parent FedexBaseService class for basic setup work.
        super(FedexRateServiceRequest, self).__init__(self._config_obj, 
                                                         'RateService_v8.wsdl',
                                                         *args, **kwargs)
        self.ClientDetail.Region = config_obj.express_region_code
        
    def _prepare_wsdl_objects(self):
        """
        This is the data that will be used to create your shipment. Create
        the data structure and get it ready for the WSDL request.
        """

	# Default behavior is to not request transit information
	self.ReturnTransitAndCommit = False

        # This is the primary data structure for processShipment requests.
        self.RequestedShipment = self.client.factory.create('RequestedShipment')
        self.RequestedShipment.ShipTimestamp = datetime.now()
        
        TotalWeight = self.client.factory.create('Weight')
        # Start at nothing.
        TotalWeight.Value = 0.0
        # Default to pounds.
        TotalWeight.Units = 'LB'
        # This is the total weight of the entire shipment. Shipments may
        # contain more than one package.
        self.RequestedShipment.TotalWeight = TotalWeight
            
        # This is the top level data structure for Shipper information.
        ShipperParty = self.client.factory.create('Party')
        ShipperParty.Address = self.client.factory.create('Address')
        ShipperParty.Contact = self.client.factory.create('Contact')
        
        # Link the ShipperParty to our master data structure.
        self.RequestedShipment.Shipper = ShipperParty

        # This is the top level data structure for Recipient information.
        RecipientParty = self.client.factory.create('Party')
        RecipientParty.Contact = self.client.factory.create('Contact')
        RecipientParty.Address = self.client.factory.create('Address')
        
        # Link the RecipientParty object to our master data structure.
        self.RequestedShipment.Recipient = RecipientParty
                
        Payor = self.client.factory.create('Payor')
        # Grab the account number from the FedexConfig object by default.
        Payor.AccountNumber = self._config_obj.account_number
        # Assume US.
        Payor.CountryCode = 'US'
        
        ShippingChargesPayment = self.client.factory.create('Payment')
        ShippingChargesPayment.Payor = Payor

        self.RequestedShipment.ShippingChargesPayment = ShippingChargesPayment
        
        # ACCOUNT or LIST
        self.RequestedShipment.RateRequestTypes = ['ACCOUNT'] 
        
        # Start with no packages, user must add them.
        self.RequestedShipment.PackageCount = 0
        self.RequestedShipment.RequestedPackageLineItems = []
                
        # This is good to review if you'd like to see what the data structure
        # looks like.
        self.logger.debug(self.RequestedShipment)
        

        
    
    def _assemble_and_send_request(self):
        """
        Fires off the Fedex request.
        
        @warning: NEVER CALL THIS METHOD DIRECTLY. CALL send_request(), 
            WHICH RESIDES ON FedexBaseService AND IS INHERITED.
        """
        # Fire off the query.
        response = self.client.service.getRates(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                        ClientDetail=self.ClientDetail,
                                        TransactionDetail=self.TransactionDetail,
                                        Version=self.VersionId,
                                        RequestedShipment=self.RequestedShipment,
					ReturnTransitAndCommit=self.ReturnTransitAndCommit)
        return response
    
    def add_package(self, package_item):
        """
        Adds a package to the ship request.
        
        @type package_item: WSDL object, type of RequestedPackageLineItem 
            WSDL object.
        @keyword package_item: A RequestedPackageLineItem, created by
            calling create_wsdl_object_of_type('RequestedPackageLineItem') on
            this ShipmentRequest object. See examples/create_shipment.py for
            more details.
        """
        self.RequestedShipment.RequestedPackageLineItems.append(package_item)
        package_weight = package_item.Weight.Value
        self.RequestedShipment.TotalWeight.Value += package_weight
        self.RequestedShipment.PackageCount += 1
        

########NEW FILE########
__FILENAME__ = ship_service
"""
Ship Service Module
===================
This package contains the shipping methods defined by Fedex's 
ShipService WSDL file. Each is encapsulated in a class for easy access. 
For more details on each, refer to the respective class's documentation.
"""
from datetime import datetime
from .. base_service import FedexBaseService

class FedexProcessShipmentRequest(FedexBaseService):
    """
    This class allows you to process (create) a new FedEx shipment. You will
    need to populate the data structures in self.RequestedShipment, then
    send the request. Label printing is supported and very configurable,
    returning an ASCII representation with the response as well.
    """
    def __init__(self, config_obj, *args, **kwargs):
        """
        The optional keyword args detailed on L{FedexBaseService} 
        apply here as well.

        @type config_obj: L{FedexConfig}
        @param config_obj: A valid FedexConfig object.        
        """
        self._config_obj = config_obj
        
        # Holds version info for the VersionId SOAP object.
        self._version_info = {'service_id': 'ship', 'major': '7', 
                             'intermediate': '0', 'minor': '0'}
        
        self.RequestedShipment = None
        """@ivar: Holds the RequestedShipment WSDL object."""
        # Call the parent FedexBaseService class for basic setup work.
        super(FedexProcessShipmentRequest, self).__init__(self._config_obj, 
                                                         'ShipService_v7.wsdl',
                                                         *args, **kwargs)
        
    def _prepare_wsdl_objects(self):
        """
        This is the data that will be used to create your shipment. Create
        the data structure and get it ready for the WSDL request.
        """
        # This is the primary data structure for processShipment requests.
        self.RequestedShipment = self.client.factory.create('RequestedShipment')
        self.RequestedShipment.ShipTimestamp = datetime.now()
        
        TotalWeight = self.client.factory.create('Weight')
        # Start at nothing.
        TotalWeight.Value = 0.0
        # Default to pounds.
        TotalWeight.Units = 'LB'
        # This is the total weight of the entire shipment. Shipments may
        # contain more than one package.
        self.RequestedShipment.TotalWeight = TotalWeight
            
        # This is the top level data structure for Shipper information.
        ShipperParty = self.client.factory.create('Party')
        ShipperParty.Address = self.client.factory.create('Address')
        ShipperParty.Contact = self.client.factory.create('Contact')
        
        # Link the ShipperParty to our master data structure.
        self.RequestedShipment.Shipper = ShipperParty

        # This is the top level data structure for Recipient information.
        RecipientParty = self.client.factory.create('Party')
        RecipientParty.Contact = self.client.factory.create('Contact')
        RecipientParty.Address = self.client.factory.create('Address')
        
        # Link the RecipientParty object to our master data structure.
        self.RequestedShipment.Recipient = RecipientParty
                
        Payor = self.client.factory.create('Payor')
        # Grab the account number from the FedexConfig object by default.
        Payor.AccountNumber = self._config_obj.account_number
        # Assume US.
        Payor.CountryCode = 'US'
        
        ShippingChargesPayment = self.client.factory.create('Payment')
        ShippingChargesPayment.Payor = Payor

        self.RequestedShipment.ShippingChargesPayment = ShippingChargesPayment
        self.RequestedShipment.LabelSpecification = self.client.factory.create('LabelSpecification')
        # ACCOUNT or LIST
        self.RequestedShipment.RateRequestTypes = ['ACCOUNT'] 
        
        # Start with no packages, user must add them.
        self.RequestedShipment.PackageCount = 0
        self.RequestedShipment.RequestedPackageLineItems = []
                
        # This is good to review if you'd like to see what the data structure
        # looks like.
        self.logger.debug(self.RequestedShipment)
        
    def send_validation_request(self):
        """
        This is very similar to just sending the shipment via the typical
        send_request() function, but this doesn't create a shipment. It is
        used to make sure "good" values are given by the user or the
        application using the library.
        """
        self.send_request(send_function=self._assemble_and_send_validation_request)
        
    def _assemble_and_send_validation_request(self):
        """
        Fires off the Fedex shipment validation request.
        
        @warning: NEVER CALL THIS METHOD DIRECTLY. CALL 
            send_validation_request(), WHICH RESIDES ON FedexBaseService 
            AND IS INHERITED.
        """
        # Fire off the query.
        response = self.client.service.validateShipment(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                        ClientDetail=self.ClientDetail,
                                        TransactionDetail=self.TransactionDetail,
                                        Version=self.VersionId,
                                        RequestedShipment=self.RequestedShipment)
        return response
    
    def _assemble_and_send_request(self):
        """
        Fires off the Fedex request.
        
        @warning: NEVER CALL THIS METHOD DIRECTLY. CALL send_request(), 
            WHICH RESIDES ON FedexBaseService AND IS INHERITED.
        """
        # Fire off the query.
        response = self.client.service.processShipment(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                        ClientDetail=self.ClientDetail,
                                        TransactionDetail=self.TransactionDetail,
                                        Version=self.VersionId,
                                        RequestedShipment=self.RequestedShipment)
        return response
    
    def add_package(self, package_item):
        """
        Adds a package to the ship request.
        
        @type package_item: WSDL object, type of RequestedPackageLineItem 
            WSDL object.
        @keyword package_item: A RequestedPackageLineItem, created by
            calling create_wsdl_object_of_type('RequestedPackageLineItem') on
            this ShipmentRequest object. See examples/create_shipment.py for
            more details.
        """
        self.RequestedShipment.RequestedPackageLineItems.append(package_item)
        package_weight = package_item.Weight.Value
        self.RequestedShipment.TotalWeight.Value += package_weight
        self.RequestedShipment.PackageCount += 1
        
class FedexDeleteShipmentRequest(FedexBaseService):
    """
    This class allows you to delete a shipment, given a tracking number.
    """
    def __init__(self, config_obj, *args, **kwargs):
        """
        Deletes a shipment via a tracking number.
        """
        self._config_obj = config_obj
        
        # Holds version info for the VersionId SOAP object.
        self._version_info = {'service_id': 'ship', 'major': '7', 
                             'intermediate': '0', 'minor': '0'}
        self.DeletionControlType = None
        """@ivar: Holds the DeletrionControlType WSDL object."""
        self.TrackingId = None
        """@ivar: Holds the TrackingId WSDL object."""
        # Call the parent FedexBaseService class for basic setup work.
        super(FedexDeleteShipmentRequest, self).__init__(self._config_obj, 
                                                'ShipService_v7.wsdl',
                                                *args, **kwargs)

    def _prepare_wsdl_objects(self):
        """
        Preps the WSDL data structures for the user.
        """
        self.DeletionControlType = self.client.factory.create('DeletionControlType')
        self.TrackingId = self.client.factory.create('TrackingId')
        self.TrackingId.TrackingIdType = self.client.factory.create('TrackingIdType')
        
    def _assemble_and_send_request(self):
        """
        Fires off the Fedex request.
        
        @warning: NEVER CALL THIS METHOD DIRECTLY. CALL send_request(), WHICH RESIDES
            ON FedexBaseService AND IS INHERITED.
        """
        client = self.client
        # Fire off the query.
        response = client.service.deleteShipment(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                        ClientDetail=self.ClientDetail,
                                        TransactionDetail=self.TransactionDetail,
                                        Version=self.VersionId,
                                        ShipTimestamp = datetime.now(), 
                                        TrackingId=self.TrackingId,
                                        DeletionControl=self.DeletionControlType)

        return response
########NEW FILE########
__FILENAME__ = track_service
"""
Tracking Service Module
=======================
This package contains the shipment tracking methods defined by Fedex's 
TrackService WSDL file. Each is encapsulated in a class for easy access. 
For more details on each, refer to the respective class's documentation.
"""
import logging
from .. base_service import FedexBaseService, FedexError

class FedexInvalidTrackingNumber(FedexError):
    """
    Exception: Sent when a bad tracking number is provided.
    """
    pass

class FedexTrackRequest(FedexBaseService):
    """
    This class allows you to track shipments by providing a tracking
    number or other identifying features. By default, you
    can simply pass a tracking number to the constructor. If you would like
    to query shipments based on something other than tracking number, you will
    want to read the documentation for the L{__init__} method. 
    Particularly, the tracking_value and package_identifier arguments.
    """
    def __init__(self, config_obj, *args, **kwargs):
        """
        Sends a shipment tracking request. The optional keyword args
        detailed on L{FedexBaseService} apply here as well.
        
        @type config_obj: L{FedexConfig}
        @param config_obj: A valid FedexConfig object.
        
        @type tracking_number_unique_id: str
        @param tracking_number_unique_id: Used to distinguish duplicate FedEx tracking numbers.
        """
        self._config_obj = config_obj
        
        # Holds version info for the VersionId SOAP object.
        self._version_info = {'service_id': 'trck', 'major': '5', 
                             'intermediate': '0', 'minor': '0'}
        self.TrackPackageIdentifier = None
        """@ivar: Holds the TrackPackageIdentifier WSDL object."""
        
        self.TrackingNumberUniqueIdentifier = kwargs.pop('tracking_number_unique_id', None)
        
        """@ivar: Holds the TrackingNumberUniqueIdentifier WSDL object."""
        # Call the parent FedexBaseService class for basic setup work.
        super(FedexTrackRequest, self).__init__(self._config_obj, 
                                                'TrackService_v5.wsdl',
                                                *args, **kwargs)
        self.IncludeDetailedScans = False
        
    def _prepare_wsdl_objects(self):
        """
        This sets the package identifier information. This may be a tracking
        number or a few different things as per the Fedex spec.
        """
        self.TrackPackageIdentifier = self.client.factory.create('TrackPackageIdentifier')
        # Default to tracking number.
        self.TrackPackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
        
    def _check_response_for_request_errors(self):
        """
        Checks the response to see if there were any errors specific to
        this WSDL.
        """
        if self.response.HighestSeverity == "ERROR":
            for notification in self.response.Notifications:
                if notification.Severity == "ERROR":
                    if "Invalid tracking number" in notification.Message:
                        raise FedexInvalidTrackingNumber(notification.Code,
                                                         notification.Message)
                    else:
                        raise FedexError(notification.Code,
                                         notification.Message)
        
    def _assemble_and_send_request(self):
        """
        Fires off the Fedex request.
        
        @warning: NEVER CALL THIS METHOD DIRECTLY. CALL send_request(), WHICH RESIDES
            ON FedexBaseService AND IS INHERITED.
        """
        client = self.client
        # Fire off the query.
        response = client.service.track(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                        ClientDetail=self.ClientDetail,
                                        TransactionDetail=self.TransactionDetail,
                                        Version=self.VersionId,
                                        IncludeDetailedScans=self.IncludeDetailedScans,
                                        PackageIdentifier=self.TrackPackageIdentifier,
                                        TrackingNumberUniqueIdentifier = self.TrackingNumberUniqueIdentifier)

        return response

########NEW FILE########
__FILENAME__ = cert_config
"""
This file holds configuration for your test account. Make SURE to change
the values below to your account's TESTING meter number.
"""
import os
import sys
# Use the fedex directory included in the downloaded package instead of
# any globally installed versions.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fedex.config import FedexConfig
from fedex.printers.unix import DirectDevicePrinter

# Change these values to match your testing account/meter number.
CONFIG_OBJ = FedexConfig(key='xxxxxxxxxxxxxxxx',
                         password='xxxxxxxxxxxxxxxxxxxxxxxxx',
                         account_number='#########',
                         meter_number='#########',
                         use_test_server=True)

# Change this to whoever should be the contact person for shipments.
SHIPPER_CONTACT_INFO = {'PersonName': 'Some Person',
                        'CompanyName': 'Your Company',
                        'PhoneNumber': '##########'}

# The dictionary below should be your office/client's address that shipping
# will be originating from.
SHIPPER_ADDRESS = {'StreetLines': ['Address Line 1'],
                   'City': 'Some City',
                   'StateOrProvinceCode': 'SC',
                   'PostalCode': '29631',
                   'CountryCode': 'US',
                   'Residential': False}

# This contains the configuration for your label printer.
LABEL_SPECIFICATION = {
                       # Specifies the label type to be returned.
                       # LABEL_DATA_ONLY or COMMON2D
                       'LabelFormatType': 'COMMON2D',
                       # Specifies which format the label file will be 
                       # sent to you in.
                       # DPL, EPL2, PDF, PNG, ZPLII
                       'ImageType': 'EPL2',
                       # To use doctab stocks, you must change ImageType above 
                       # to one of the label printer formats (ZPLII, EPL2, DPL).
                       # See documentation for paper types, there quite a few.
                       'LabelStockType': 'STOCK_4X6.75_LEADING_DOC_TAB',
                       # This indicates if the top or bottom of the label comes 
                       # out of the printer first.
                       # BOTTOM_EDGE_OF_TEXT_FIRST or TOP_EDGE_OF_TEXT_FIRST
                       'LabelPrintingOrientation': 'BOTTOM_EDGE_OF_TEXT_FIRST'
}

# This should just be a reference to the correct printer class for your
# label printer. You may find these under the fedex.printers module.
# NOTE: This should NOT be an instance. It should just be a reference.
LabelPrinterClass = DirectDevicePrinter

def transfer_config_dict(soap_object, data_dict):
    """
    This is a utility function used in the certification modules to transfer
    the data dicts above to SOAP objects. This avoids repetition and allows
    us to store all of our variable configuration here rather than in
    each certification script.
    """
    for key, val in data_dict.items():
        # Transfer each key to the matching attribute ont he SOAP object.
        setattr(soap_object, key, val)
########NEW FILE########
__FILENAME__ = express
#!/usr/bin/env python
"""
This module prints three FedEx Express shipping labels for the label
certification process. See your FedEx Label Developer Tool Kit documentation
for more details.
"""
import logging
from cert_config import CONFIG_OBJ, SHIPPER_CONTACT_INFO, SHIPPER_ADDRESS, LABEL_SPECIFICATION
from cert_config import transfer_config_dict
from cert_config import LabelPrinterClass
from fedex.services.ship_service import FedexProcessShipmentRequest

logging.basicConfig(level=logging.INFO)

shipment = FedexProcessShipmentRequest(CONFIG_OBJ)
shipment.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
shipment.RequestedShipment.ServiceType = 'PRIORITY_OVERNIGHT'
shipment.RequestedShipment.PackagingType = 'YOUR_PACKAGING'
shipment.RequestedShipment.PackageDetail = 'INDIVIDUAL_PACKAGES'

# Shipper contact info.
transfer_config_dict(shipment.RequestedShipment.Shipper.Contact, 
                     SHIPPER_CONTACT_INFO)

# Shipper address.
transfer_config_dict(shipment.RequestedShipment.Shipper.Address, 
                     SHIPPER_ADDRESS)

# Recipient contact info.
shipment.RequestedShipment.Recipient.Contact.PersonName = 'Recipient Name'
shipment.RequestedShipment.Recipient.Contact.CompanyName = 'Recipient Company'
shipment.RequestedShipment.Recipient.Contact.PhoneNumber = '9012637906'

# Recipient address
shipment.RequestedShipment.Recipient.Address.StreetLines = ['Address Line 1']
shipment.RequestedShipment.Recipient.Address.City = 'Herndon'
shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = 'VA'
shipment.RequestedShipment.Recipient.Address.PostalCode = '20171'
shipment.RequestedShipment.Recipient.Address.CountryCode = 'US'

shipment.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER' 

# Label config.
transfer_config_dict(shipment.RequestedShipment.LabelSpecification, 
                     LABEL_SPECIFICATION)

package1_weight = shipment.create_wsdl_object_of_type('Weight')
package1_weight.Value = 1.0
package1_weight.Units = "LB"
package1 = shipment.create_wsdl_object_of_type('RequestedPackageLineItem')
package1.Weight = package1_weight
shipment.add_package(package1)

if __name__ == "__main__":
    shipment.send_request()
    device = LabelPrinterClass(shipment)
    device.print_label()
    
    shipment.RequestedShipment.Recipient.Address.StreetLines = ['456 Peach St']
    shipment.RequestedShipment.Recipient.Address.City = 'Atlanta'
    shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = 'GA'
    shipment.RequestedShipment.Recipient.Address.PostalCode = '30303'
    shipment.RequestedShipment.Recipient.Address.CountryCode = 'US'
    
    shipment.send_request()
    device = LabelPrinterClass(shipment)
    device.print_label()
    
    shipment.RequestedShipment.Recipient.Address.StreetLines = ['987 Main St']
    shipment.RequestedShipment.Recipient.Address.City = 'Boston'
    shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = 'MA'
    shipment.RequestedShipment.Recipient.Address.PostalCode = '02115'
    shipment.RequestedShipment.Recipient.Address.CountryCode = 'US'
    
    shipment.send_request()
    device = LabelPrinterClass(shipment)
    device.print_label()
########NEW FILE########
__FILENAME__ = ground
#!/usr/bin/env python
"""
This module prints three FedEx Ground shipping labels for the label
certification process. See your FedEx Label Developer Tool Kit documentation
for more details.
"""
import logging
from cert_config import CONFIG_OBJ, SHIPPER_CONTACT_INFO, SHIPPER_ADDRESS, LABEL_SPECIFICATION
from cert_config import transfer_config_dict
from cert_config import LabelPrinterClass
from fedex.services.ship_service import FedexProcessShipmentRequest

logging.basicConfig(level=logging.INFO)

shipment = FedexProcessShipmentRequest(CONFIG_OBJ)
shipment.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
shipment.RequestedShipment.ServiceType = 'FEDEX_GROUND'
shipment.RequestedShipment.PackagingType = 'YOUR_PACKAGING'
shipment.RequestedShipment.PackageDetail = 'INDIVIDUAL_PACKAGES'

# Shipper contact info.
transfer_config_dict(shipment.RequestedShipment.Shipper.Contact, 
                     SHIPPER_CONTACT_INFO)

# Shipper address.
transfer_config_dict(shipment.RequestedShipment.Shipper.Address, 
                     SHIPPER_ADDRESS)

# Recipient contact info.
shipment.RequestedShipment.Recipient.Contact.PersonName = 'Recipient Name'
shipment.RequestedShipment.Recipient.Contact.CompanyName = 'Recipient Company'
shipment.RequestedShipment.Recipient.Contact.PhoneNumber = '9012637906'

# Recipient address
shipment.RequestedShipment.Recipient.Address.StreetLines = ['Address Line 1']
shipment.RequestedShipment.Recipient.Address.City = 'Herndon'
shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = 'VA'
shipment.RequestedShipment.Recipient.Address.PostalCode = '20171'
shipment.RequestedShipment.Recipient.Address.CountryCode = 'US'

shipment.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER' 

# Label config.
transfer_config_dict(shipment.RequestedShipment.LabelSpecification, 
                     LABEL_SPECIFICATION)

package1_weight = shipment.create_wsdl_object_of_type('Weight')
package1_weight.Value = 1.0
package1_weight.Units = "LB"
package1 = shipment.create_wsdl_object_of_type('RequestedPackageLineItem')
package1.Weight = package1_weight
shipment.add_package(package1)

if __name__ == "__main__":
    shipment.send_request()
    device = LabelPrinterClass(shipment)
    device.print_label()
    
    shipment.RequestedShipment.Recipient.Address.StreetLines = ['456 Peach St']
    shipment.RequestedShipment.Recipient.Address.City = 'Atlanta'
    shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = 'GA'
    shipment.RequestedShipment.Recipient.Address.PostalCode = '30303'
    shipment.RequestedShipment.Recipient.Address.CountryCode = 'US'
    
    shipment.send_request()
    device = LabelPrinterClass(shipment)
    device.print_label()
    
    shipment.RequestedShipment.Recipient.Address.StreetLines = ['987 Main St']
    shipment.RequestedShipment.Recipient.Address.City = 'Boston'
    shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = 'MA'
    shipment.RequestedShipment.Recipient.Address.PostalCode = '02115'
    shipment.RequestedShipment.Recipient.Address.CountryCode = 'US'
    
    shipment.send_request()
    device = LabelPrinterClass(shipment)
    device.print_label()
########NEW FILE########
__FILENAME__ = common
"""
This module contains common definitions and functions used within the
test suite.
"""
from fedex.config import FedexConfig

def get_test_config():
    """
    Returns a basic FedexConfig to test with.
    """
    # Test server (Enter your credentials here)
    return FedexConfig(key='xxxxxxxxxxxxxxxxx',
                       password='xxxxxxxxxxxxxxxxxxxxxxxxx',
                       account_number='xxxxxxxxx',
                       meter_number='xxxxxxxxxx',
                       use_test_server=True)
########NEW FILE########
__FILENAME__ = t_track_service
"""
Test module for the Fedex ShipService WSDL.
"""
import unittest
from fedex.services.track_service import FedexTrackRequest
import common

# Common global config object for testing.
CONFIG_OBJ = common.get_test_config()

class TrackServiceTests(unittest.TestCase):
    """
    These tests verify that the shipping service WSDL is in good shape.
    """
    def test_track(self):
        """
        Test shipment tracking. Query for a tracking number and make sure the
        first (and hopefully only) result matches up.
        """
        track = FedexTrackRequest(CONFIG_OBJ)
        track.TrackPackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
        track.TrackPackageIdentifier.Value = '798114182456'
        track.send_request()
            
        for match in track.response.TrackDetails:
            # This should be the same tracking number on the response that we
            # asked for in the request.
            self.assertEqual(match.TrackingNumber, tracking_num)

########NEW FILE########
