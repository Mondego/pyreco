__FILENAME__ = client
import smtplib, time

messages_sent = 0.0
start_time = time.time()
msg = file('test/fixtures/valid_dkim.eml').read()

while True:

    if (messages_sent % 10) == 0:
        current_time = time.time()
        print '%s msg-written/sec' % (messages_sent / (current_time - start_time))

    server = smtplib.SMTP('localhost', port=10025)
    server.sendmail('foo@localhost', ['bar@localhost'], msg)
    server.quit()

    messages_sent += 1.0

########NEW FILE########
__FILENAME__ = server
import time
from smtproutes import Route, Server
from smtproutes.decorators import route

class BenchmarkRoute(Route):
    @route(r'(?P<prefix>[^@]*)@(?P<suffix>.*)')
    def benchmark_route(self):
        pass

Server(('0.0.0.0', 10025), None).add_route(BenchmarkRoute).start()

########NEW FILE########
__FILENAME__ = example_route
import smtproutes
import logging

from smtproutes import Route, Server
from smtproutes.sender_auth import DKIMAuth, GmailSPFAuth, SPFAuth
from smtproutes.decorators import route

class ExampleRoute(Route):
    
    @route(r'(?P<prefix>open)@(?P<suffix>.*)')
    def open_route(self):
        print "%s at %s triggered route with message: \n\n %s" % (
            self.prefix,
            self.suffix,
            self.message
        )
    
    @route(r'(?P<prefix>dkim)@(?P<suffix>.*)', sender_auth=DKIMAuth)
    def dkim_route(self):
        print "%s at %s triggered route with message: \n\n %s" % (
            self.prefix,
            self.suffix,
            self.message
        )

    @route(r'(?P<prefix>spf)@(?P<suffix>.*)', sender_auth=SPFAuth)
    def spf_route(self):
        print "%s at %s triggered route with message: \n\n %s" % (
            self.prefix,
            self.suffix,
            self.message
        )

    @route(r'(?P<prefix>spf_google)@(?P<suffix>.*)', sender_auth=[SPFAuth, GmailSPFAuth])
    def google_apps_spf_route(self):
        print "%s at %s triggered route with message: \n\n %s" % (
            self.prefix,
            self.suffix,
            self.message
        )

logger = logging.getLogger( smtproutes.LOG_NAME )
logger.setLevel(logging.INFO)

Server(('0.0.0.0', 25), None).add_route(ExampleRoute).start()
########NEW FILE########
__FILENAME__ = log
import logging, sys
from logging.handlers import RotatingFileHandler
from logging import StreamHandler

LOG_NAME = 'smtproutes'

class Log(object):
    
    def __init__(self, log_name):
        self.log_name = log_name
        self.logger = logging.getLogger( self.log_name )
        self._remove_handlers()
        self._add_handler()
        self.logger.setLevel(logging.DEBUG)
    
    def _remove_handlers(self):
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
    
    def _add_handler(self):
        try:
            handler = RotatingFileHandler(
                '/var/log/%s.log' % self.log_name,
                maxBytes=10485760,
                backupCount=3
            )
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        except IOError:
            self.logger.addHandler(StreamHandler(sys.stderr))

Log(LOG_NAME)
########NEW FILE########
__FILENAME__ = route
class route(object):
    
    def __init__(self, route, sender_auth=None):
        self.route = route
        self.sender_auth = sender_auth
    
    def __call__(self, f):
        def wrapped_f(self, route=self.route, sender_auth=self.sender_auth, *args, **kwargs):
            f(self, *args, **kwargs)
        return wrapped_f
########NEW FILE########
__FILENAME__ = attachment
import re

class Attachment(object):
    
    def __init__(self, filename=None, data=None, mime_type=None):
        self.filename = filename
        self.data = data
        self.mime_type = mime_type
        self._populate_extension()
    
    def _populate_extension(self):
        self.extension = None
        match = re.match('.*\.(?P<extension>.*)', self.filename)
        if match:
            self.extension = match.group('extension')
########NEW FILE########
__FILENAME__ = contact
from email.utils import parseaddr, getaddresses

class Contact(object):
    
    def __init__(self, raw_addr=None, parsed_raw_addr=None):
        if raw_addr:
            parsed_raw_addr = parseaddr( raw_addr )
        self.name = parsed_raw_addr[0]
        self.email = parsed_raw_addr[1]
    
    def __str__(self):
        return '%s <%s>' % (self.name, self.email)
    
    @classmethod
    def create_contacts_from_message_field(cls, field_name, message):
        contacts = []
        raw_addrs = message.get_all(field_name, [])
        for parsed_raw_addr in getaddresses( raw_addrs ):
            contacts.append( Contact(parsed_raw_addr=parsed_raw_addr) )
        return contacts
########NEW FILE########
__FILENAME__ = message
import re, base64
import email.message
from attachment import Attachment

class Message(email.message.Message):

    @property
    def attachments(self):
        attachments = []
        
        for part in self.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            
            filename = part.get_filename()
            
            if not filename:
                continue
            
            data = part.get_payload(decode=True)
            attachments.append(Attachment(filename=self._decode_string( filename ), data=data, mime_type=part.get_content_type()))
        return attachments
    
    @property
    def body(self):
        for part in self.walk():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
        return ''
    
    def _decode_string(self, filename):
        try:
            if '?B?' in filename:
                match = re.match(r'=\?(?P<encoding>.*)\?B\?(?P<text>.*)\?=', filename)
                codes = base64.b64decode(match.group( 'text' ))
                return codes.decode( match.group('encoding') )
        except Exception:
            pass
        return filename
########NEW FILE########
__FILENAME__ = route
import smtproutes
import re, email, inspect, logging

from model import Contact, Message
from routing_exception import RoutingException
from sender_auth import SenderAuthException

class Route(object):
    
    def _initialize(self, peer_ip='0.0.0.0'):
        self._peer_ip = peer_ip
        self.logger = logging.getLogger( smtproutes.LOG_NAME )
        self._register_routes()
    
    def _route(self, message_data=None):
        self.raw_message_data = message_data
        self.message = email.message_from_string(message_data, Message)
        self.mailfrom = Contact.create_contacts_from_message_field('from', self.message)[0]
        self.tos = Contact.create_contacts_from_message_field('to', self.message)
        self.tos.extend( Contact.create_contacts_from_message_field('x-forwarded-to', self.message) )
        self.ccs = Contact.create_contacts_from_message_field('cc', self.message)
        self.bccs = Contact.create_contacts_from_message_field('bcc', self.message)
        self._call_routes()
    
    def _call_routes(self):
        route_found = False
        
        recipients = []
        recipients.append(self.mailfrom)
        recipients.extend(self.tos)
        recipients.extend(self.ccs)
        recipients.extend(self.bccs)
        
        for recipient in recipients:
            for route in self._routes.keys():
                if re.match(route, recipient.email):
                    self.logger.info('Route %s matched email %s' % (route, recipient.email))
                    route_found = True
                    self._auth_sender(route)
                    self._populate_instance_variables_from_named_capture_groups(route, recipient.email)
                    self._routes[route]['method']()
        
        if not route_found:
            raise RoutingException('No matching route found for %s.' % ', '.join(str(r) for r in recipients) )
    
    def _auth_sender(self, route):
        auth_instance = self._routes[route].get('sender_auth')
        if auth_instance:
            
            auth_approaches = []
            if type(auth_instance) == list:
                auth_approaches.extend(auth_instance)
            else:
                auth_approaches.append(auth_instance)
            
            authed = False
            for auth_approach in auth_approaches:
                if auth_approach().auth(self.raw_message_data, self._peer_ip, self.message):
                    authed = True
                    break
            
            if not authed:
                raise SenderAuthException('Sender %s authentication failed.' % self.mailfrom)            
    
    def _populate_instance_variables_from_named_capture_groups(self, regex, addr):
        match = re.match(regex, addr)
        for k, v in match.groupdict().items():
            self.__dict__[k] = v
        
    def _register_routes(self):
        self._routes = {}
        
        for attr_name in self.__class__.__dict__:
            if attr_name[0:1] == '_':
                continue
            
            method = getattr(self, attr_name)
            if type(method) == type(self._register_routes):
                default_kwargs = self._extract_default_kwargs(method)
                if default_kwargs.get('route'):
                    self._routes[default_kwargs.get('route')] = {
                        'method': method,
                        'sender_auth': default_kwargs.get('sender_auth')
                    }
        
    def _extract_default_kwargs(self, method):
        argspec = inspect.getargspec(method)
        
        argspec_defaults = list( argspec.defaults )
        default_kwargs = {}
        for arg in argspec.args:
            if arg == 'self':
                continue
                
            default_kwargs[arg] = argspec_defaults.pop(0)
        return default_kwargs
########NEW FILE########
__FILENAME__ = routing_exception
class RoutingException(Exception):
    pass
########NEW FILE########
__FILENAME__ = dkim_auth
import dkim

class DKIMAuth(object):
    
    def auth(self, message_data=None, peer_ip=None, message=None):
        return dkim.verify(message_data)
########NEW FILE########
__FILENAME__ = gmail_spf_auth
import spf

class GmailSPFAuth(object):
    def auth(self, message_data=None, peer_ip=None, message=None):
        result_status = spf.check(i=peer_ip, s='@gmail.com', h='google.com')[0]
        if 'pass' in result_status:
            return True
        return False
########NEW FILE########
__FILENAME__ = sender_auth_exception
class SenderAuthException(Exception):
    pass
########NEW FILE########
__FILENAME__ = spf_auth
import spf, re, email
from smtproutes.model import Contact

class SPFAuth(object):

    def auth(self, message_data=None, peer_ip=None, message=None):
        mailfrom = Contact.create_contacts_from_message_field('from', message)[0]
        host = re.match('[^@]*@(.*)', mailfrom.email).group(1)
        result_status = spf.check(i=peer_ip, s=mailfrom.email, h=host)[0]
        if 'pass' in result_status:
            return True
        return False

########NEW FILE########
__FILENAME__ = server
import smtproutes
import ssl, asyncore, logging

from secure_smtpd import SMTPServer
from routing_exception import RoutingException

class Server(SMTPServer):

    def __init__(self, localaddr, remoteaddr, ssl=False, certfile=None, keyfile=None, ssl_version=ssl.PROTOCOL_SSLv23, require_authentication=False, credential_validator=None, maximum_execution_time=30, process_count=5):
        SMTPServer.__init__(self, localaddr, remoteaddr, ssl, certfile, keyfile, ssl_version, require_authentication, credential_validator, maximum_execution_time, process_count)
        self.routes = []
        self.logger = logging.getLogger( smtproutes.LOG_NAME )

    def add_route(self, RouteClass):
        self.routes.append(RouteClass)
        return self

    def process_message(self, peer, mailfrom, rcpttos, message_data):
        for RouteClass in self.routes:
            try:
                route = RouteClass()
                route._initialize(peer_ip=peer[0])
                route._route(message_data)
            except RoutingException, re:
                self.logger.warn( re )
            except Exception, e:
                self.logger.error( e )

    def start(self):
      self.run()

########NEW FILE########
__FILENAME__ = test_attachment
import unittest, email
from smtproutes.model import Message, Attachment

class TestAttachment(unittest.TestCase):
    
    def setUp(self):
        self.attachment_eml = file('test/fixtures/attachments.eml').read()
    
    def test_attachments_filenames_populated(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(message.attachments[0].filename, 'tokyo.jpg')
        self.assertEqual(message.attachments[1].filename, 'attachments_logo_fix_02_300.png')
    
    def test_attachments_data_right_number_of_bytes(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(len(message.attachments[0].data), 62116)
        self.assertEqual(len(message.attachments[1].data), 2475)
    
    def test_attachment_extension_populated(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(message.attachments[0].extension, 'jpg' )
        self.assertEqual(message.attachments[1].extension, 'png' )
        
    def test_attachment_mime_type_populated(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(message.attachments[0].mime_type, 'image/jpeg' )
        self.assertEqual(message.attachments[1].mime_type, 'image/png' )
        

########NEW FILE########
__FILENAME__ = test_contact
import unittest, email
from smtproutes.model import Contact, Message

class TestContact(unittest.TestCase):

    def setUp(self):
        self.attachment_eml = file('test/fixtures/valid_dkim.eml').read()
        self.message = email.message_from_string(self.attachment_eml, Message)

    def test_create_contacts_from_message_field_successfully_creates_contact_object(self):
        contacts = Contact.create_contacts_from_message_field('to', self.message)
        self.assertEqual(contacts[0].email, 'ben@npmjs.com')

########NEW FILE########
__FILENAME__ = test_dkim_auth
import unittest, email
from smtproutes.sender_auth import DKIMAuth

class TestDKIMAuth(unittest.TestCase):
    
    def setUp(self):
        self.valid_dkim_eml = file('test/fixtures/valid_dkim.eml').read()
        self.invalid_dkim_eml = file('test/fixtures/invalid_dkim.eml').read()
    
    def test_auth_returns_true_for_message_with_valid_dkim_signature(self):
        dkim_auth = DKIMAuth()
        self.assertTrue(dkim_auth.auth(self.valid_dkim_eml, '0.0.0.0'))
        
    def test_auth_returns_false_for_message_with_invalid_dkim_signature(self):
        dkim_auth = DKIMAuth()
        self.assertFalse(dkim_auth.auth(self.invalid_dkim_eml, '0.0.0.0'))
########NEW FILE########
__FILENAME__ = test_gmail_spf_auth
import unittest, email
from smtproutes.sender_auth import GmailSPFAuth

class TestGmailSPFAuth(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def test_valid_google_ip_address_returns_true(self):
        auth = GmailSPFAuth()
        self.assertTrue(auth.auth(None, '209.85.213.46'))
        
    def test_invalid_google_ip_address_returns_false(self):
        auth = GmailSPFAuth()
        self.assertFalse(auth.auth(None, '0.0.0.0'))
########NEW FILE########
__FILENAME__ = test_message
import unittest, email
from smtproutes.model import Message

class TestMessage(unittest.TestCase):
    
    def setUp(self):
        self.attachment_eml = file('test/fixtures/attachments.eml').read()
    
    def test_parsing_message_with_custom_message_class(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(message.get('to'), 'bencoe@gmail.com')
    
    def test_attachments_returned_by_messages_attachments_property(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(len(message.attachments), 2)
    
    def test_body_returns_text_body_of_message(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(message.body, 'message with attachments.\n')
    
    def test_decode_filename_decodes_non_ascii_filenames(self):
        message = email.message_from_string(self.attachment_eml, Message)
        self.assertEqual(message._decode_string('=?Big5?B?xKy7t6fTsdCxwsKyvvoucGRm?='), u'\u8607\u9060\u5FD7\u6559\u6388\u7C21\u6B77.pdf')
########NEW FILE########
__FILENAME__ = test_route
import unittest
from smtproutes import Route, RoutingException
from smtproutes.sender_auth import DKIMAuth, GmailSPFAuth, SenderAuthException
from smtproutes.decorators import route

class TestRoute(unittest.TestCase):

    def setUp(self):
        self.valid_dkim_eml = file('test/fixtures/valid_dkim.eml').read()
        self.invalid_dkim_eml = file('test/fixtures/invalid_dkim.eml').read()

    def test_route_regexes_extracted_from_methods_on_class_inheriting_from_Route(self):

        class RouteImpl(Route):

            def route1(self, route=r'ben@example.com'):
                pass

            def route2(self, route=r'ben2@example.com'):
                pass

        route = RouteImpl()
        route._initialize()
        self.assertTrue('ben@example.com' in route._routes)
        self.assertTrue('ben2@example.com' in route._routes)

    def test_calling_route_with_a_matching_regex_results_in_the_appropriate_route_being_invoked(self):

        class RouteImpl(Route):

            def route1(self, route=r'ben@example.com'):
                self.bar = 'bar'

            def route2(self, route=r'ben2@example.com'):
                self.bar = 'foo'

        message =  'To: Benjamin <ben@example.com>, eric@foo.com, Eric <eric2@example.com>\nFrom: Ben Coe <bencoe@example.com>'

        route = RouteImpl()
        route._initialize()
        route._route(
            message_data=message
        )
        self.assertEqual('bar', route.bar)

    def test_route_decorator_can_be_used_to_define_endpoint_rather_than_kwarg(self):

        class RouteImpl(Route):

            @route('ben@example.com')
            def route1(self):
                self.bar = 'bar'

            @route('ben2@example.com')
            def route2(self):
                self.bar = 'foo'

        message =  'To: Benjamin <ben@example.com>, eric@foo.com, Eric <eric2@example.com>\nFrom: Ben Coe <bencoe@example.com>'

        r = RouteImpl()
        r._initialize()
        r._route(
            message_data=message
        )
        self.assertEqual('bar', r.bar)

    def test_a_cc_field_that_matches_a_route_causes_the_route_to_be_triggered(self):

        class RouteImpl(Route):
            @route(r'ben@example.com')
            def route1(self):
                self.bar = 'bar'

            @route(r'ben2@example.com')
            def route2(self):
                self.bar = 'foo'

        message =  'To: Benjamin <foo@example.com>, eric@foo.com, Eric <eric2@example.com>\nCC: ben@example.com\nFrom: Ben Coe <bencoe@example.com>'

        r = RouteImpl()
        r._initialize()
        r._route(
            message_data=message
        )
        self.assertEqual('bar', r.bar)

    def test_a_bcc_field_that_matches_a_route_causes_the_route_to_be_triggered(self):

        class RouteImpl(Route):
            @route(r'ben@example.com')
            def route1(self):
                self.bar = 'bar'

            @route(r'ben2@example.com')
            def route2(self):
                self.bar = 'foo'

        message =  'BCC: chuck@example.com, ben@example.com\nTo: Benjamin <foo@example.com>, eric@foo.com, Eric <eric2@example.com>\nCC: bar@example.com\nFrom: Ben Coe <bencoe@example.com>'

        r = RouteImpl()
        r._initialize()
        r._route(
            message_data=message
        )
        self.assertEqual('bar', r.bar)

    def test_x_forwarded_to_address_is_treated_as_to_address(self):

        class RouteImpl(Route):
            @route(r'ben@example.com')
            def route1(self):
                self.bar = 'bar'

        message =  'X-Forwarded-To: chuck@example.com, ben@example.com\nTo: Benjamin <foo@example.com>, eric@foo.com, Eric <eric2@example.com>\nCC: bar@example.com\nFrom: Ben Coe <bencoe@example.com>'

        r = RouteImpl()
        r._initialize()
        r._route(message)
        self.assertEqual(r.tos[3].email, 'chuck@example.com')

    def test_a_routing_exception_should_be_raised_if_the_route_is_not_found(self):
        class RouteImpl(Route):
            pass

        message =  'To: Benjamin <ben@example.com>, eric@foo.com, Eric <eric2@example.com>\nFrom: Ben Coe <bencoe@example.com>'
        route = RouteImpl()
        route._initialize()
        try:
            route._route(
                message_data=message
            )
            self.assertTrue(False)
        except RoutingException, re:
            self.assertTrue('ben@example.com' in str(re))
            self.assertTrue(True)

    def test_named_groups_stored_as_instance_variables_on_route(self):
        class RouteImpl(Route):

            def route(self, route=r'(?P<user>[^-]*)-(?P<folder>.*)@.*'):
                self.called = True

        message =  'To: Benjamin <bencoe-awesome-folder@example.com>\nFrom: bencoe@example.com'
        route = RouteImpl()
        route._initialize()
        route._route(message_data=message)
        self.assertEqual(route.user, 'bencoe')
        self.assertEqual(route.folder, 'awesome-folder')
        self.assertEqual(route.called, True)

    def test_instance_variables_populated_based_on_email_message(self):
        class RouteImpl(Route):

            def route(self, route=r'a@example.com'):
                self.called = True

        message =  'To: a <a@example.com>, b@example.com\nFrom: c@example.com\nCC: d <d@example.com>, e@example.com\nBCC: f@example.com'
        route = RouteImpl()
        route._initialize()
        route._route(message_data=message)
        self.assertTrue(route.message)
        self.assertEqual(route.tos[0].email, 'a@example.com')
        self.assertEqual(route.tos[1].email, 'b@example.com')
        self.assertEqual(route.mailfrom.email, 'c@example.com')
        self.assertEqual(route.ccs[0].email, 'd@example.com')
        self.assertEqual(route.ccs[1].email, 'e@example.com')
        self.assertEqual(route.bccs[0].email, 'f@example.com')

    def test_exception_raised_when_sender_auth_fails_on_route(self):
        class RouteImpl(Route):
            def route(self, route=r'bcoe@.*', sender_auth=DKIMAuth):
                self.called = True

        route = RouteImpl()
        route._initialize()
        route.called = False
        try:
            route._route(
                message_data=self.invalid_dkim_eml
            )
            self.assertTrue(False)
        except SenderAuthException:
            self.assertTrue(True)
        self.assertFalse(route.called)

    def test_no_exception_raised_when_sender_auth_succeeds_on_route(self):
        class RouteImpl(Route):
            def route(self, route=r'ben@.*', sender_auth=GmailSPFAuth):
                self.called = True

        route = RouteImpl()
        route._initialize(peer_ip='209.85.213.46')
        route._route(
            message_data=self.valid_dkim_eml
        )
        self.assertTrue(route.called)

    def test_route_decorator_can_be_used_rather_than_kwarg_to_specify_sender_auth(self):
        class RouteImpl(Route):
            @route('bcoe@.*', sender_auth=GmailSPFAuth)
            def route(self):
                self.called = True

        route = RouteImpl()
        route._initialize(peer_ip='209.85.213.46')
        route._route(
            message_data=self.invalid_dkim_eml
        )
        self.assertTrue(route.called)

    def test_if_list_of_sender_authentication_approaches_is_provided_route_called_if_any_pass(self):
        class RouteImpl(Route):
            def route(self, route=r'bcoe@.*', sender_auth=[DKIMAuth, GmailSPFAuth]):
                self.called = True

        route = RouteImpl()
        route._initialize(peer_ip='209.85.213.46')
        route._route(
            message_data=self.invalid_dkim_eml
        )
        self.assertTrue(route.called)

    def test_if_list_of_sender_authentication_approaches_is_provided_exception_raised_if_all_fail(self):
        class RouteImpl(Route):
            def route(self, route=r'bcoe@.*', sender_auth=[DKIMAuth, GmailSPFAuth]):
                self.called = True

        route = RouteImpl()
        route._initialize()
        route.called = False

        try:
            route._route(
                message_data=self.invalid_dkim_eml
            )
            self.assertTrue(False)
        except SenderAuthException:
            self.assertTrue(True)
        self.assertFalse(route.called)

########NEW FILE########
__FILENAME__ = test_server
import unittest
from smtproutes import Server, Route

class TestServer(unittest.TestCase):

    def setUp(self):
        pass

    def test_process_message_should_delegate_to_a_route_registered_with_it(self):
        class RouteImpl(Route):

            def route(self, route=r'ben@example.com'):
                self.called = True

        message =  'To: Benjamin <ben@example.com>, eric@foo.com, Eric <eric2@example.com>\nFrom: Ben Coe <bencoe@example.com>'

        server = Server(('0.0.0.0', 10465), None)
        server.add_route(RouteImpl)
        server.process_message(('0.0.0.0', '333'), 'mailfrom@example.com', 'rcpttos@example.com', message)

########NEW FILE########
__FILENAME__ = test_spf_auth
import unittest, email
from smtproutes.sender_auth import SPFAuth

class TestSPFAuth(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def test_valid_ip_address_returns_true(self):
        auth = SPFAuth()
        message = email.message_from_string('From: Benjamin Coe <bcoe@uoguelph.ca>')
        self.assertTrue(auth.auth(str(message), '131.104.91.44', message))
        
    def test_invalid_ip_address_returns_false(self):
        auth = SPFAuth()
        message = email.message_from_string('From: Benjamin Coe <bcoe@uoguelph.ca>')
        self.assertFalse(auth.auth(str(message), '0.0.0.0', message))
########NEW FILE########
