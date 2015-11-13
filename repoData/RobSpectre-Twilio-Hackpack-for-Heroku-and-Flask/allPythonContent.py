__FILENAME__ = app
import os

from hackpack.app import app

# If PORT not specified by environment, assume development config.
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if port == 5000:
        app.debug = True
    app.run(host='0.0.0.0', port=port)

########NEW FILE########
__FILENAME__ = configure
'''
Hackpack Configure
A script to configure your TwiML apps and Twilio phone numbers to use your
hackpack's Heroku app.

Usage:

Auto-configure using your local_settings.py:
    python configure.py

Deploy to new Twilio number and App Sid:
    python configure.py --new

Deploy to specific App Sid:
    python configure.py --app APxxxxxxxxxxxxxx

Deploy to specific Twilio number:
    python configure.py --number +15556667777

Deploy to custom domain:
    python configure.py --domain example.com
'''

from optparse import OptionParser
import subprocess
import logging

from twilio.rest import TwilioRestClient
from twilio import TwilioRestException

from hackpack import local_settings


class Configure(object):
    def __init__(self, account_sid=local_settings.TWILIO_ACCOUNT_SID,
            auth_token=local_settings.TWILIO_AUTH_TOKEN,
            app_sid=local_settings.TWILIO_APP_SID,
            phone_number=local_settings.TWILIO_CALLER_ID,
            voice_url='/voice',
            sms_url='/sms',
            host=None):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.app_sid = app_sid
        self.phone_number = phone_number
        self.host = host
        self.voice_url = voice_url
        self.sms_url = sms_url
        self.friendly_phone_number = None

    def start(self):
        logging.info("Configuring your Twilio hackpack...")
        logging.debug("Checking if credentials are set...")
        if not self.account_sid:
            raise ConfigurationError("ACCOUNT_SID is not set in " \
                    "local_settings.")
        if not self.auth_token:
            raise ConfigurationError("AUTH_TOKEN is not set in " \
                    "local_settings.")

        logging.debug("Creating Twilio client...")
        self.client = TwilioRestClient(self.account_sid, self.auth_token)

        logging.debug("Checking if host is set.")
        if not self.host:
            logging.debug("Hostname is not set...")
            self.host = self.getHerokuHostname()

        # Check if urls are set.
        logging.debug("Checking if all urls are set.")
        if "http://" not in self.voice_url:
            self.voice_url = self.host + self.voice_url
            logging.debug("Setting voice_url with host: %s" % self.voice_url)
        if "http://" not in self.sms_url:
            self.sms_url = self.host + self.sms_url
            logging.debug("Setting sms_url with host: %s" % self.sms_url)

        if self.configureHackpack(self.voice_url, self.sms_url,
                self.app_sid, self.phone_number):

            # Configure Heroku environment variables.
            self.setHerokuEnvironmentVariables(
                    TWILIO_ACCOUNT_SID=self.account_sid,
                    TWILIO_AUTH_TOKEN=self.auth_token,
                    TWILIO_APP_SID=self.app_sid,
                    TWILIO_CALLER_ID=self.phone_number)

            # Ensure local environment variables are set.
            self.printLocalEnvironmentVariableCommands(
                    TWILIO_ACCOUNT_SID=self.account_sid,
                    TWILIO_AUTH_TOKEN=self.auth_token,
                    TWILIO_APP_SID=self.app_sid,
                    TWILIO_CALLER_ID=self.phone_number)

            logging.info("Hackpack is now configured.  Call %s to test!"
                    % self.friendly_phone_number)
        else:
            logging.error("There was an error configuring your hackpack. " \
                    "Weak sauce.")

    def configureHackpack(self, voice_url, sms_url, app_sid,
            phone_number, *args):

        # Check if app sid is configured and available.
        if not app_sid:
            app = self.createNewTwiMLApp(voice_url, sms_url)
        else:
            app = self.setAppRequestUrls(app_sid, voice_url, sms_url)

        # Check if phone_number is set.
        if not phone_number:
            number = self.purchasePhoneNumber()
        else:
            number = self.retrievePhoneNumber(phone_number)

        # Configure phone number to use App Sid.
        logging.info("Setting %s to use application sid: %s" %
                (number.friendly_name, app.sid))
        try:
            self.client.phone_numbers.update(number.sid,
                    voice_application_sid=app.sid,
                    sms_application_sid=app.sid)
            logging.debug("Number set.")
        except TwilioRestException, e:
            raise ConfigurationError("An error occurred setting the " \
                    "application sid for %s: %s" % (number.friendly_name,
                        e))

        # We're done!
        if number:
            return number
        else:
            raise ConfigurationError("An unknown error occurred configuring " \
                    "request urls for this hackpack.")

    def createNewTwiMLApp(self, voice_url, sms_url):
        logging.debug("Asking user to create new app sid...")
        i = 0
        while True:
            i = i + 1
            choice = raw_input("Your APP_SID is not configured in your " \
                 "local_settings.  Create a new one? [y/n]").lower()
            if choice == "y":
                try:
                    logging.info("Creating new application...")
                    app = self.client.applications.create(voice_url=voice_url,
                            sms_url=sms_url,
                            friendly_name="Hackpack for Heroku and Flask")
                    break
                except TwilioRestException, e:
                    raise ConfigurationError("Your Twilio app couldn't " \
                            "be created: %s" % e)
            elif choice == "n" or i >= 3:
                raise ConfigurationError("Your APP_SID setting must be  " \
                        "set in local_settings.")
            else:
                logging.error("Please choose yes or no with a 'y' or 'n'")
        if app:
            logging.info("Application created: %s" % app.sid)
            self.app_sid = app.sid
            return app
        else:
            raise ConfigurationError("There was an unknown error " \
                    "creating your TwiML application.")

    def setAppRequestUrls(self, app_sid, voice_url, sms_url):
        logging.info("Setting request urls for application sid: %s" \
                % app_sid)

        try:
            app = self.client.applications.update(app_sid, voice_url=voice_url,
                    sms_url=sms_url,
                    friendly_name="Hackpack for Heroku and Flask")
        except TwilioRestException, e:
            if "HTTP ERROR 404" in str(e):
                raise ConfigurationError("This application sid was not " \
                        "found: %s" % app_sid)
            else:
                raise ConfigurationError("An error setting the request URLs " \
                        "occured: %s" % e)
        if app:
            logging.debug("Updated application sid: %s " % app.sid)
            return app
        else:
            raise ConfigurationError("An unknown error occuring "\
                   "configuring request URLs for app sid.")

    def retrievePhoneNumber(self, phone_number):
        logging.debug("Retrieving phone number: %s" % phone_number)
        try:
            logging.debug("Getting sid for phone number: %s" % phone_number)
            number = self.client.phone_numbers.list(
                    phone_number=phone_number)
        except TwilioRestException, e:
            raise ConfigurationError("An error setting the request URLs " \
                    "occured: %s" % e)
        if number:
            logging.debug("Retrieved sid: %s" % number[0].sid)
            self.friendly_phone_number = number[0].friendly_name
            return number[0]
        else:
            raise ConfigurationError("An unknown error occurred retrieving " \
                    "number: %s" % phone_number)

    def purchasePhoneNumber(self):
        logging.debug("Asking user to purchase phone number...")

        i = 0
        while True:
            i = i + 1
            # Find number to purchase
            choice = raw_input("Your CALLER_ID is not configured in your " \
                "local_settings.  Purchase a new one? [y/n]").lower()
            if choice == "y":
                break
            elif choice == "n" or i >= 3:
                raise ConfigurationError("To configure this " \
                        "hackpack CALLER_ID must set in local_settings or " \
                        "a phone number must be purchased.")
            else:
                logging.error("Please choose yes or no with a 'y' or 'n'")

        logging.debug("Confirming purchase...")
        i = 0
        while True:
            i = i + 1
            # Confirm phone number purchase.
            choice = raw_input("Are you sure you want to purchase? " \
                "Your Twilio account will be charged $1. [y/n]").lower()
            if choice == "y":
                try:
                    logging.debug("Purchasing phone number...")
                    number = self.client.phone_numbers.purchase(
                            area_code="646")
                    logging.debug("Phone number purchased: %s" %
                            number.friendly_name)
                    break
                except TwilioRestException, e:
                    raise ConfigurationError("Your Twilio app couldn't " \
                            "be created: %s" % e)
            elif choice == "n" or i >= 3:
                raise ConfigurationError("To configure this " \
                        "hackpack CALLER_ID must set in local_settings or " \
                        "a phone number must be purchased.")
            else:
                logging.error("Please choose yes or no with a 'y' or 'n'")

        # Return number or error out.
        if number:
            logging.debug("Returning phone number: %s " % number.friendly_name)
            self.phone_number = number.phone_number
            self.friendly_phone_number = number.friendly_name
            return number
        else:
            raise ConfigurationError("There was an unknown error purchasing " \
                    "your phone number.")

    def getHerokuHostname(self, git_config_path='./.git/config'):
        logging.debug("Getting hostname from git configuration file: %s" \
                % git_config_path)
        # Load git configuration
        try:
            logging.debug("Loading git config...")
            git_config = file(git_config_path).readlines()
        except IOError, e:
            raise ConfigurationError("Could not find .git config.  Does it " \
                    "still exist? Failed path: %s" % e)

        logging.debug("Finding Heroku remote in git configuration...")
        subdomain = None
        for line in git_config:
            if "git@heroku.com" in line:
                s = line.split(":")
                subdomain = s[1].replace('.git', '')
                logging.debug("Heroku remote found: %s" % subdomain)

        if subdomain:
            host = "http://%s.herokuapp.com" % subdomain.strip()
            logging.debug("Returning full host: %s" % host)
            return host
        else:
            raise ConfigurationError("Could not find Heroku remote in " \
                    "your .git config.  Have you created the Heroku app?")

    def printLocalEnvironmentVariableCommands(self, **kwargs):
        logging.info("Copy/paste these commands to set your local " \
                "environment to use this hackpack...")
        print "\n"
        for k, v in kwargs.iteritems():
            if v:
                print "export %s=%s" % (k, v)
        print "\n"

    def setHerokuEnvironmentVariables(self, **kwargs):
        logging.info("Setting Heroku environment variables...")
        envvars = ["%s=%s" % (k, v) for k, v in kwargs.iteritems() if v]
        envvars.insert(0, "heroku")
        envvars.insert(1, "config:add")
        return subprocess.call(envvars)


class ConfigurationError(Exception):
    def __init__(self, message):
        #Exception.__init__(self, message)
        logging.error(message)


# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Parser configuration
usage = "Twilio Hackpack Configurator - an easy way to configure " \
        "configure your hackpack!\n%prog [options] arg1 arg2"
parser = OptionParser(usage=usage, version="Twilio Hackpack Configurator 1.0")
parser.add_option("-S", "--account_sid", default=None,
        help="Use a specific Twilio ACCOUNT_SID.")
parser.add_option("-K", "--auth_token", default=None,
        help="Use a specific Twilio AUTH_TOKEN.")
parser.add_option("-n", "--new", default=False, action="store_true",
        help="Purchase new Twilio phone number and configure app to use " \
            "your hackpack.")
parser.add_option("-N", "--new_app", default=False, action="store_true",
        help="Create a new TwiML application sid to use for your " \
            "hackpack.")
parser.add_option("-a", "--app_sid", default=None,
        help="Configure specific AppSid to use your hackpack.")
parser.add_option("-#", "--phone-number", default=None,
        help="Configure specific Twilio number to use your hackpack.")
parser.add_option("-v", "--voice_url", default=None,
        help="Set the route for your Voice Request URL: (e.g. '/voice').")
parser.add_option("-s", "--sms_url", default=None,
        help="Set the route for your SMS Request URL: (e.g. '/sms').")
parser.add_option("-d", "--domain", default=None,
        help="Set a custom domain.")
parser.add_option("-D", "--debug", default=False,
        action="store_true", help="Turn on debug output.")


def main():
    (options, args) = parser.parse_args()

    # Configurator configuration :)
    configure = Configure()

    # Options tree
    if options.account_sid:
        configure.account_sid = options.account_sid
    if options.auth_token:
        configure.auth_token = options.auth_token
    if options.new:
        configure.phone_number = None
    if options.new_app:
        configure.app_sid = None
    if options.app_sid:
        configure.app_sid = options.app_sid
    if options.phone_number:
        configure.phone_number = options.phone_number
    if options.voice_url:
        configure.voice_url = options.voice_url
    if options.sms_url:
        configure.sms_url = options.sms_url
    if options.domain:
        configure.host = options.domain
    if options.debug:
        logging.basicConfig(level=logging.DEBUG,
                format='%(levelname)s - %(message)s')

    configure.start()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = app
import re

from flask import Flask
from flask import render_template
from flask import url_for
from flask import request

from twilio import twiml
from twilio.util import TwilioCapability

# Declare and configure application
app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')

# Voice Request URL
@app.route('/voice', methods=['GET', 'POST'])
def voice():
    response = twiml.Response()
    response.say("Congratulations! You deployed the Twilio Hackpack" \
            " for Heroku and Flask.")
    return str(response)


# SMS Request URL
@app.route('/sms', methods=['GET', 'POST'])
def sms():
    response = twiml.Response()
    response.sms("Congratulations! You deployed the Twilio Hackpack" \
            " for Heroku and Flask.")
    return str(response)


# Twilio Client demo template
@app.route('/client')
def client():
    configuration_error = None
    for key in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_APP_SID',
            'TWILIO_CALLER_ID'):
        if not app.config[key]:
            configuration_error = "Missing from local_settings.py: " \
                    "%s" % key
            token = None

    if not configuration_error:
        capability = TwilioCapability(app.config['TWILIO_ACCOUNT_SID'],
            app.config['TWILIO_AUTH_TOKEN'])
        capability.allow_client_incoming("joey_ramone")
        capability.allow_client_outgoing(app.config['TWILIO_APP_SID'])
        token = capability.generate()
    params = {'token': token}
    return render_template('client.html', params=params,
            configuration_error=configuration_error)

@app.route('/client/incoming', methods=['POST'])
def client_incoming():
    try:
        from_number = request.values.get('PhoneNumber', None)

        resp = twiml.Response()

        if not from_number:
            resp.say(
                "Your app is missing a Phone Number. "
                "Make a request with a Phone Number to make outgoing calls with "
                "the Twilio hack pack.")
            return str(resp)

        if 'TWILIO_CALLER_ID' not in app.config:
            resp.say(
                "Your app is missing a Caller ID parameter. "
                "Please add a Caller ID to make outgoing calls with Twilio Client")
            return str(resp)

        with resp.dial(callerId=app.config['TWILIO_CALLER_ID']) as r:
            # If we have a number, and it looks like a phone number:
            if from_number and re.search('^[\d\(\)\- \+]+$', from_number):
                r.number(from_number)
            else:
                r.say("We couldn't find a phone number to dial. Make sure you are "
                      "sending a Phone Number when you make a request with Twilio "
                      "Client")

        return str(resp)

    except:
        resp = twiml.Response()
        resp.say("An error occurred. Check your debugger at twilio dot com "
                 "for more information.")
        return str(resp)


# Installation success page
@app.route('/')
def index():
    params = {
        'Voice Request URL': url_for('.voice', _external=True),
        'SMS Request URL': url_for('.sms', _external=True),
        'Client URL': url_for('.client', _external=True)}
    return render_template('index.html', params=params,
            configuration_error=None)


########NEW FILE########
__FILENAME__ = local_settings
'''
Configuration Settings
'''

''' Uncomment to configure using the file.  
WARNING: Be careful not to post your account credentials on GitHub.

TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxx" 
TWILIO_AUTH_TOKEN = "yyyyyyyyyyyyyyyy"
TWILIO_APP_SID = "APzzzzzzzzz"
TWILIO_CALLER_ID = "+17778889999"
'''

# Begin Heroku configuration - configured through environment variables.
import os
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)
TWILIO_CALLER_ID = os.environ.get('TWILIO_CALLER_ID', None)
TWILIO_APP_SID = os.environ.get('TWILIO_APP_SID', None)

########NEW FILE########
__FILENAME__ = context
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

from twilio.rest import resources

import configure
from app import app

########NEW FILE########
__FILENAME__ = test_configure
import unittest
from mock import Mock
from mock import patch
import subprocess

from twilio.rest import TwilioRestClient

from .context import configure


class ConfigureTest(unittest.TestCase):
    def setUp(self):
        self.configure = configure.Configure(
                account_sid="ACxxxxx",
                auth_token="yyyyyyyy",
                phone_number="+15555555555",
                app_sid="APzzzzzzzzz")
        self.configure.client = TwilioRestClient(self.configure.account_sid,
                self.configure.auth_token)


class TwilioTest(ConfigureTest):
    @patch('twilio.rest.resources.Applications')
    @patch('twilio.rest.resources.Application')
    def test_createNewTwiMLApp(self, MockApp, MockApps):
        # Mock the Applications resource and its create method.
        self.configure.client.applications = MockApps.return_value
        self.configure.client.applications.create.return_value = \
            MockApp.return_value

        # Mock our input.
        configure.raw_input = lambda _: 'y'

        # Test
        self.configure.createNewTwiMLApp(self.configure.voice_url,
                self.configure.sms_url)

        # Assert
        self.configure.client.applications.create.assert_called_once_with(
                voice_url=self.configure.voice_url,
                sms_url=self.configure.sms_url,
                friendly_name="Hackpack for Heroku and Flask")

    @patch('twilio.rest.resources.Applications')
    @patch('twilio.rest.resources.Application')
    def test_createNewTwiMLAppNegativeInput(self, MockApp, MockApps):
        # Mock the Applications resource and its create method.
        self.configure.client.applications = MockApps.return_value
        self.configure.client.applications.create.return_value = \
            MockApp.return_value

        # Mock our input .
        configure.raw_input = lambda _: 'n'

        # Test / Assert
        self.assertRaises(configure.ConfigurationError,
                self.configure.createNewTwiMLApp,
                self.configure.voice_url, self.configure.sms_url)

    @patch('twilio.rest.resources.Applications')
    @patch('twilio.rest.resources.Application')
    def test_setAppSidRequestUrls(self, MockApp, MockApps):
        # Mock the Applications resource and its update method.
        self.configure.client.applications = MockApps.return_value
        self.configure.client.applications.update.return_value = \
            MockApp.return_value

        # Test
        self.configure.setAppRequestUrls(self.configure.app_sid,
                self.configure.voice_url,
                self.configure.sms_url)

        # Assert
        self.configure.client.applications.update.assert_called_once_with(
                self.configure.app_sid,
                voice_url=self.configure.voice_url,
                sms_url=self.configure.sms_url,
                friendly_name='Hackpack for Heroku and Flask')

    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_retrievePhoneNumber(self, MockPhoneNumber, MockPhoneNumbers):
        # Mock the PhoneNumbers resource and its list method.
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.list.return_value = \
                [mock_phone_number]

        # Test
        self.configure.retrievePhoneNumber(self.configure.phone_number)

        # Assert
        self.configure.client.phone_numbers.list.assert_called_once_with(
                phone_number=self.configure.phone_number)

    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_purchasePhoneNumber(self, MockPhoneNumber, MockPhoneNumbers):
        # Mock the PhoneNumbers resource and its search and purchase methods
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.purchase = \
                mock_phone_number

        # Mock our input.
        configure.raw_input = lambda _: 'y'

        # Test
        self.configure.purchasePhoneNumber()

        # Assert
        self.configure.client.phone_numbers.purchase.assert_called_once_with(
                area_code="646")

    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_purchasePhoneNumberNegativeInput(self, MockPhoneNumbers,
            MockPhoneNumber):
        # Mock the PhoneNumbers resource and its search and purchase methods
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.purchase = \
                mock_phone_number

        # Mock our input.
        configure.raw_input = lambda _: 'n'

        # Test / Assert
        self.assertRaises(configure.ConfigurationError,
                self.configure.purchasePhoneNumber)

    @patch('twilio.rest.resources.Applications')
    @patch('twilio.rest.resources.Application')
    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_configure(self, MockPhoneNumber, MockPhoneNumbers, MockApp,
            MockApps):
        # Mock the Applications resource and its update method.
        mock_app = MockApp.return_value
        mock_app.sid = self.configure.app_sid
        self.configure.client.applications = MockApps.return_value
        self.configure.client.applications.update.return_value = \
            mock_app

        # Mock the PhoneNumbers resource and its list method.
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.sid = "PN123"
        mock_phone_number.friendly_name = "(555) 555-5555"
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.list.return_value = \
            [mock_phone_number]

        # Test
        self.configure.configureHackpack(self.configure.voice_url,
                self.configure.sms_url,
                self.configure.app_sid,
                self.configure.phone_number)

        # Assert
        self.configure.client.applications.update.assert_called_once_with(
                self.configure.app_sid,
                voice_url=self.configure.voice_url,
                sms_url=self.configure.sms_url,
                friendly_name='Hackpack for Heroku and Flask')

        self.configure.client.phone_numbers.update.assert_called_once_with(
                "PN123",
                voice_application_sid=self.configure.app_sid,
                sms_application_sid=self.configure.app_sid)

    @patch('twilio.rest.resources.Applications')
    @patch('twilio.rest.resources.Application')
    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_configureNoApp(self, MockPhoneNumber, MockPhoneNumbers, MockApp,
            MockApps):
        # Mock the Applications resource and its update method.
        mock_app = MockApp.return_value
        mock_app.sid = self.configure.app_sid
        self.configure.client.applications = MockApps.return_value
        self.configure.client.applications.create.return_value = \
            mock_app

        # Mock the PhoneNumbers resource and its list method.
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.sid = "PN123"
        mock_phone_number.friendly_name = "(555) 555-5555"
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.list.return_value = \
            [mock_phone_number]

        # Set AppSid to None
        self.configure.app_sid = None

        # Mock our input.
        configure.raw_input = lambda _: 'y'

        # Test
        self.configure.configureHackpack(self.configure.voice_url,
                self.configure.sms_url,
                self.configure.app_sid,
                self.configure.phone_number)

        # Assert
        self.configure.client.applications.create.assert_called_once_with(
                voice_url=self.configure.voice_url,
                sms_url=self.configure.sms_url,
                friendly_name="Hackpack for Heroku and Flask")

        self.configure.client.phone_numbers.update.assert_called_once_with(
                "PN123",
                voice_application_sid=mock_app.sid,
                sms_application_sid=mock_app.sid)

    @patch('twilio.rest.resources.Applications')
    @patch('twilio.rest.resources.Application')
    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_configureNoPhoneNumber(self, MockPhoneNumber, MockPhoneNumbers,
            MockApp, MockApps):
        # Mock the Applications resource and its update method.
        mock_app = MockApp.return_value
        mock_app.sid = self.configure.app_sid
        self.configure.client.applications = MockApps.return_value
        self.configure.client.applications.update.return_value = \
            mock_app

        # Mock the PhoneNumbers resource and its list method.
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.sid = "PN123"
        mock_phone_number.friendly_name = "(555) 555-5555"
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.purchase.return_value = \
            mock_phone_number

        # Set AppSid to None
        self.configure.phone_number = None

        # Mock our input.
        configure.raw_input = lambda _: 'y'

        # Test
        self.configure.configureHackpack(self.configure.voice_url,
                self.configure.sms_url,
                self.configure.app_sid,
                self.configure.phone_number)

        # Assert
        self.configure.client.applications.update.assert_called_once_with(
                self.configure.app_sid,
                voice_url=self.configure.voice_url,
                sms_url=self.configure.sms_url,
                friendly_name='Hackpack for Heroku and Flask')

        self.configure.client.phone_numbers.update.assert_called_once_with(
                "PN123",
                voice_application_sid=self.configure.app_sid,
                sms_application_sid=self.configure.app_sid)

    @patch.object(subprocess, 'call')
    @patch.object(configure.Configure, 'configureHackpack')
    def test_start(self, mock_configureHackpack, mock_call):
        mock_call.return_value = None
        self.configure.host = 'http://look-here-snacky-11211.herokuapp.com'
        self.configure.start()
        mock_configureHackpack.assert_called_once_with(
                'http://look-here-snacky-11211.herokuapp.com/voice',
                'http://look-here-snacky-11211.herokuapp.com/sms',
                self.configure.app_sid,
                self.configure.phone_number)

    @patch.object(subprocess, 'call')
    @patch.object(configure.Configure, 'configureHackpack')
    @patch.object(configure.Configure, 'getHerokuHostname')
    def test_startWithoutHostname(self, mock_getHerokuHostname,
            mock_configureHackpack, mock_call):
        mock_call.return_value = None
        mock_getHerokuHostname.return_value = \
                'http://look-here-snacky-11211.herokuapp.com'
        self.configure.start()
        mock_configureHackpack.assert_called_once_with(
                'http://look-here-snacky-11211.herokuapp.com/voice',
                'http://look-here-snacky-11211.herokuapp.com/sms',
                self.configure.app_sid,
                self.configure.phone_number)


class HerokuTest(ConfigureTest):
    def test_getHerokuHostname(self):
        test = self.configure.getHerokuHostname(
                git_config_path='./tests/test_assets/good_git_config')
        self.assertEquals(test, 'http://look-here-snacky-11211.herokuapp.com')

    def test_getHerokuHostnameNoSuchFile(self):
        self.assertRaises(configure.ConfigurationError,
                self.configure.getHerokuHostname,
                git_config_path='/tmp')

    def test_getHerokuHostnameNoHerokuRemote(self):
        self.assertRaises(configure.ConfigurationError,
                self.configure.getHerokuHostname,
                git_config_path='./tests/test_assets/bad_git_config')

    @patch.object(subprocess, 'call')
    def test_setHerokuEnvironmentVariables(self, mock_call):
        mock_call.return_value = None
        self.configure.setHerokuEnvironmentVariables(
                TWILIO_ACCOUNT_SID=self.configure.account_sid,
                TWILIO_AUTH_TOKEN=self.configure.auth_token,
                TWILIO_APP_SID=self.configure.app_sid,
                TWILIO_CALLER_ID=self.configure.phone_number)
        mock_call.assert_called_once_with(["heroku", "config:add",
                '%s=%s' % ('TWILIO_ACCOUNT_SID', self.configure.account_sid),
                '%s=%s' % ('TWILIO_CALLER_ID', self.configure.phone_number),
                '%s=%s' % ('TWILIO_AUTH_TOKEN', self.configure.auth_token),
                '%s=%s' % ('TWILIO_APP_SID', self.configure.app_sid)])


class MiscellaneousTest(unittest.TestCase):
    def test_configureWithoutAccountSid(self):
        test = configure.Configure(account_sid=None, auth_token=None,
                phone_number=None, app_sid=None)
        self.assertRaises(configure.ConfigurationError,
                test.start)

    def test_configureWithoutAuthToken(self):
        test = configure.Configure(account_sid='ACxxxxxxx', auth_token=None,
                phone_number=None, app_sid=None)
        self.assertRaises(configure.ConfigurationError,
                test.start)


class InputTest(ConfigureTest):
    @patch('twilio.rest.resources.Applications')
    @patch('twilio.rest.resources.Application')
    def test_createNewTwiMLAppWtfInput(self, MockApp, MockApps):
        # Mock the Applications resource and its create method.
        self.configure.client.applications = MockApps.return_value
        self.configure.client.applications.create.return_value = \
            MockApp.return_value

        # Mock our input
        configure.raw_input = Mock()
        configure.raw_input.return_value = 'wtf'
        
        # Test / Assert
        self.assertRaises(configure.ConfigurationError,
                self.configure.createNewTwiMLApp, self.configure.voice_url,
                self.configure.sms_url)
        self.assertTrue(configure.raw_input.call_count == 3, "Prompt did " \
                "not appear three times, instead: %i" %
                configure.raw_input.call_count)
        self.assertFalse(self.configure.client.applications.create.called,
            "Unexpected request to create AppSid made.")

    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_purchasePhoneNumberWtfInput(self, MockPhoneNumbers,
            MockPhoneNumber):
        # Mock the PhoneNumbers resource and its search and purchase methods
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.purchase = \
                mock_phone_number

        # Mock our input.
        configure.raw_input = Mock()
        configure.raw_input.return_value = 'wtf'

        # Test / Assert
        self.assertRaises(configure.ConfigurationError,
                self.configure.purchasePhoneNumber)
        self.assertTrue(configure.raw_input.call_count == 3, "Prompt did " \
                "not appear three times, instead: %i" %
                configure.raw_input.call_count)
        self.assertFalse(self.configure.client.phone_numbers.purchase.called,
                "Unexpected request to create AppSid made.")

    @patch('twilio.rest.resources.PhoneNumbers')
    @patch('twilio.rest.resources.PhoneNumber')
    def test_purchasePhoneNumberWtfInputConfirm(self,
            MockPhoneNumbers, MockPhoneNumber):
        # Mock the PhoneNumbers resource and its search and purchase methods
        mock_phone_number = MockPhoneNumber.return_value
        mock_phone_number.phone_number = self.configure.phone_number
        self.configure.client.phone_numbers = MockPhoneNumbers.return_value
        self.configure.client.phone_numbers.purchase = \
                mock_phone_number

        # Mock our input.
        configure.raw_input = Mock()
        configure.raw_input.side_effect = ['y', 'wtf', 'wtf', 'wtf']

        # Test / Assert
        self.assertRaises(configure.ConfigurationError,
                self.configure.purchasePhoneNumber)
        self.assertTrue(configure.raw_input.call_count == 4, "Prompt did " \
                "not appear three times, instead: %i" %
                configure.raw_input.call_count)
        self.assertFalse(self.configure.client.phone_numbers.purchase.called,
                "Unexpectedly requested phone number purchase.")

########NEW FILE########
__FILENAME__ = test_twilio
import unittest
from .context import app


app.config['TWILIO_ACCOUNT_SID'] = 'ACxxxxxx'
app.config['TWILIO_AUTH_TOKEN'] = 'yyyyyyyyy'
app.config['TWILIO_CALLER_ID'] = '+15558675309'


class TwiMLTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def assertTwiML(self, response):
        self.assertTrue("<Response>" in response.data, "Did not find " \
                "<Response>: %s" % response.data)
        self.assertTrue("</Response>" in response.data, "Did not find " \
                "</Response>: %s" % response.data)
        self.assertEqual("200 OK", response.status)

    def sms(self, body, url='/sms', to=app.config['TWILIO_CALLER_ID'],
            from_='+15558675309', extra_params=None):
        params = {
            'SmsSid': 'SMtesting',
            'AccountSid': app.config['TWILIO_ACCOUNT_SID'],
            'To': to,
            'From': from_,
            'Body': body,
            'FromCity': 'BROOKLYN',
            'FromState': 'NY',
            'FromCountry': 'US',
            'FromZip': '55555'}
        if extra_params:
            params = dict(params.items() + extra_params.items())
        return self.app.post(url, data=params)

    def call(self, url='/voice', to=app.config['TWILIO_CALLER_ID'],
            from_='+15558675309', digits=None, extra_params=None):
        params = {
            'CallSid': 'CAtesting',
            'AccountSid': app.config['TWILIO_ACCOUNT_SID'],
            'To': to,
            'From': from_,
            'CallStatus': 'ringing',
            'Direction': 'inbound',
            'FromCity': 'BROOKLYN',
            'FromState': 'NY',
            'FromCountry': 'US',
            'FromZip': '55555'}
        if digits:
            params['Digits'] = digits
        if extra_params:
            params = dict(params.items() + extra_params.items())
        return self.app.post(url, data=params)


class ExampleTests(TwiMLTest):
    def test_sms(self):
        response = self.sms("Test")
        self.assertTwiML(response)

    def test_voice(self):
        response = self.call()
        self.assertTwiML(response)

########NEW FILE########
__FILENAME__ = test_web
import unittest
from .context import app

class WebTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()


class ExampleTests(WebTest):
    def test_index(self):
        response = self.app.get('/')
        self.assertEqual("200 OK", response.status)

    def test_client(self):
        response = self.app.get('/client')
        self.assertEqual("200 OK", response.status)

########NEW FILE########
