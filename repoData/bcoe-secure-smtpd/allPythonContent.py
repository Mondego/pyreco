__FILENAME__ = client
import smtplib, time

messages_sent = 0.0
start_time = time.time()
msg = file('examples/benchmarking/benchmark.eml').read()

while True:
    
    if (messages_sent % 10) == 0:
        current_time = time.time()
        print '%s msg-written/sec' % (messages_sent / (current_time - start_time))
    
    server = smtplib.SMTP('localhost', port=1025)
    server.sendmail('foo@localhost', ['bar@localhost'], msg)
    server.quit()
    
    messages_sent += 1.0

########NEW FILE########
__FILENAME__ = server
from secure_smtpd import SMTPServer

class SecureSMTPServer(SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, message_data):
        pass
        
server = SecureSMTPServer(('0.0.0.0', 1025), None)
server.run()

########NEW FILE########
__FILENAME__ = evil_ssl_client
import smtplib
import time

msg = """From: foo@localhost
To: bar@localhost

Here's my message!
"""
count = 0
while True:
    try:
        count += 1
        if (count % 10) == 0:
            server = smtplib.SMTP('localhost', port=465)
        else:
            server = smtplib.SMTP_SSL('localhost', port=465)
        
        server.set_debuglevel(1)
        server.login('bcoe', 'foobar')
        server.sendmail('foo@localhost', ['bar@localhost'], msg)
        server.quit()
    except Exception, e:
        print e
    time.sleep(0.05)
########NEW FILE########
__FILENAME__ = mail_relay
#!/usr/bin/env python
import argparse
from secure_smtpd import ProxyServer

def run(cmdargs):
    args = [
        (cmdargs.localhost, cmdargs.localport),
        (cmdargs.remotehost, cmdargs.remoteport)
    ]
    kwargs = {}

    if cmdargs.sslboth:
        kwargs['ssl'] = True
    elif cmdargs.sslout:
        kwargs['ssl_out_only'] = True

    if not cmdargs.quiet:
        kwargs['debug'] = True

    server = ProxyServer(*args, **kwargs)
    server.run()

parser = argparse.ArgumentParser(description='mail relay tool')

parser.add_argument(
    '--localhost',
    default='127.0.0.1',
    help='Local address to attach to for receiving mail.  Defaults to 127.0.0.1'
)
    
parser.add_argument(
    '--localport',
    default=1025,
    type=int,
    help='Local port to attach to for receiving mail.  Defaults to 1025'
)

parser.add_argument(
    '--remotehost',
    required=True,
    help='Address of the remote server for connection.'
)

parser.add_argument(
    '--remoteport',
    default=25,
    type=int, 
    help='Port of the remote server for connection.  Defaults to 25'
)

parser.add_argument(
    '--quiet',
    action='store_true',
    help='Use this to turn off the message printing'
)

group = parser.add_mutually_exclusive_group()

group.add_argument(
    '--sslboth',
    action='store_true', 
    help='Use this parameter if both the inbound and outbound connections should use SSL'
)
    
group.add_argument(
    '--sslout',
    action='store_true', 
    help='Use this parameter if inbound connection is plain but the outbound connection uses SSL'
)

args = parser.parse_args()

print 'Starting ProxyServer'
print 'local: %s:%s' % (args.localhost, args.localport)
print 'remote: %s:%s' % (args.remotehost, args.remoteport)
print 'sslboth: ', args.sslboth
print 'sslout: ', args.sslout
print
run(args)

########NEW FILE########
__FILENAME__ = ssl_client
import smtplib

msg = """From: foo@localhost
To: bar@localhost

Here's my message!
"""

server = smtplib.SMTP_SSL('localhost', port=1025)
server.set_debuglevel(1)
server.login('bcoe', 'foobar')
server.sendmail('foo@localhost', ['bar@localhost'], msg)
server.quit()

########NEW FILE########
__FILENAME__ = ssl_server
import logging
from secure_smtpd import SMTPServer, FakeCredentialValidator, LOG_NAME

class SSLSMTPServer(SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, message_data):
        print message_data

logger = logging.getLogger( LOG_NAME )
logger.setLevel(logging.INFO)

server = SSLSMTPServer(
    ('0.0.0.0', 1025),
    None,
    require_authentication=True,
    ssl=True,
    certfile='examples/server.crt',
    keyfile='examples/server.key',
    credential_validator=FakeCredentialValidator(),
    maximum_execution_time = 1.0
    )

server.run()

########NEW FILE########
__FILENAME__ = log
import logging, sys
from logging.handlers import RotatingFileHandler
from logging import StreamHandler

LOG_NAME = 'secure-smtpd'

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
__FILENAME__ = fake_credential_validator
import secure_smtpd
import logging

# Implment this interface with an actual
# methodlogy for validating credentials, e.g.,
# lookup credentials for a user in Redis.
class FakeCredentialValidator(object):
    
    def validate(self, username, password):
        
        logger = logging.getLogger( secure_smtpd.LOG_NAME )
        logger.warn('FakeCredentialValidator: you should replace this with an actual implementation of a credential validator.')
        
        if username == 'bcoe' and password == 'foobar':
            return True
        return False
########NEW FILE########
__FILENAME__ = process_pool
import time
from multiprocessing import Process, Queue

class ProcessPool(object):
    
    def __init__(self, func, process_count=5):
        self.func = func
        self.process_count = process_count
        self.queue = Queue()
        self._create_processes()
    
    def _create_processes(self):
        for i in range(0, self.process_count):
            process = Process(target=self.func, args=[self.queue])
            process.daemon = True
            process.start()

########NEW FILE########
__FILENAME__ = proxy_server
import smtplib
import secure_smtpd
from smtp_server import SMTPServer
from store_credentials import StoreCredentials

class ProxyServer(SMTPServer):
    """Implements an open relay.  Inherits from secure_smtpd, so can handle
    SSL incoming.  Modifies attributes slightly:

    * if "ssl" is true accepts SSL connections inbound and connects via SSL
        outbound
    * adds "ssl_out_only", which can be set to True when "ssl" is False so that
        inbound connections are in plain text but outbound are in SSL
    * adds "debug", which if True copies all inbound messages to logger.info()
    * ignores any credential validators, passing any credentials upstream
    """
    def __init__(self, *args, **kwargs):
        self.ssl_out_only = False
        if kwargs.has_key('ssl_out_only'):
            self.ssl_out_only = kwargs.pop('ssl_out_only')

        self.debug = False
        if kwargs.has_key('debug'):
            self.debug = kwargs.pop('debug')

        kwargs['credential_validator'] = StoreCredentials()
        SMTPServer.__init__(self, *args, **kwargs)

    def process_message(self, peer, mailfrom, rcpttos, data):
        if self.debug:
            # ------------------------
            # stolen directly from stmpd.DebuggingServer
            inheaders = 1
            lines = data.split('\n')
            self.logger.info('---------- MESSAGE FOLLOWS ----------')
            for line in lines:
                # headers first
                if inheaders and not line:
                    self.logger.info('X-Peer: %s', peer[0])
                    inheaders = 0
                self.logger.info(line)
            self.logger.info('------------ END MESSAGE ------------')

        # ------------------------
        # following code is direct from smtpd.PureProxy
        lines = data.split('\n')
        # Look for the last header
        i = 0
        for line in lines:
            if not line:
                break
            i += 1
        lines.insert(i, 'X-Peer: %s' % peer[0])
        data = '\n'.join(lines)
        self._deliver(mailfrom, rcpttos, data)

    def _deliver(self, mailfrom, rcpttos, data):
        # ------------------------
        # following code is adapted from smtpd.PureProxy with modifications to
        # handle upstream SSL
        refused = {}
        try:
            if self.ssl or self.ssl_out_only:
                s = smtplib.SMTP_SSL()
            else:
                s = smtplib.SMTP()

            s.connect(self._remoteaddr[0], self._remoteaddr[1])
            if self.credential_validator.stored:
                # we had credentials passed in, use them
                s.login(
                    self.credential_validator.username,
                    self.credential_validator.password
                )
            try:
                refused = s.sendmail(mailfrom, rcpttos, data)
                if refused != {}:
                    self.logger.error('some connections refused %s', refused)
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused, e:
            self.logger.exception('')
            refused = e.recipients
        except (socket.error, smtplib.SMTPException), e:
            self.logger.exception('')

            # All recipients were refused.  If the exception had an associated
            # error code, use it.  Otherwise,fake it with a non-triggering
            # exception code.
            errcode = getattr(e, 'smtp_code', -1)
            errmsg = getattr(e, 'smtp_error', 'ignore')
            for r in rcpttos:
                refused[r] = (errcode, errmsg)
        return refused

########NEW FILE########
__FILENAME__ = smtp_channel
import secure_smtpd
import smtpd, base64, secure_smtpd, asynchat, logging

from asyncore import ExitNow
from smtpd import NEWLINE, EMPTYSTRING

class SMTPChannel(smtpd.SMTPChannel):
    
    def __init__(self, smtp_server, newsocket, fromaddr, require_authentication=False, credential_validator=None, map=None):
        smtpd.SMTPChannel.__init__(self, smtp_server, newsocket, fromaddr)
        asynchat.async_chat.__init__(self, newsocket, map=map)
        
        self.require_authentication = require_authentication
        self.authenticating = False
        self.authenticated = False
        self.username = None
        self.password = None
        self.credential_validator = credential_validator
        self.logger = logging.getLogger( secure_smtpd.LOG_NAME )
    
    def smtp_QUIT(self, arg):
        self.push('221 Bye')
        self.close_when_done()
        raise ExitNow()
        
    def collect_incoming_data(self, data):
        self.__line.append(data)
    
    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
            return
        if self.__greeting:
            self.push('503 Duplicate HELO/EHLO')
        else:
            self.push('250-%s Hello %s' %  (self.__fqdn, arg))
            self.push('250-AUTH LOGIN')
            self.push('250 EHLO')
    
    def smtp_AUTH(self, arg):
        if 'LOGIN' in arg:
            self.authenticating = True
            split_args = arg.split(' ')
            
            # Some implmentations of 'LOGIN' seem to provide the username
            # along with the 'LOGIN' stanza, hence both situations are
            # handled.
            if len(split_args) == 2:
                self.username = base64.b64decode( arg.split(' ')[1] )
                self.push('334 ' + base64.b64encode('Username'))
            else:
                self.push('334 ' + base64.b64encode('Username'))
                
        elif not self.username:
            self.username = base64.b64decode( arg )
            self.push('334 ' + base64.b64encode('Password'))
        else:
            self.authenticating = False
            self.password = base64.b64decode(arg)
            if self.credential_validator and self.credential_validator.validate(self.username, self.password):
                self.authenticated = True
                self.push('235 Authentication successful.')
            else:
                self.push('454 Temporary authentication failure.')
                raise ExitNow()
    
    # This code is taken directly from the underlying smtpd.SMTPChannel
    # support for AUTH is added.
    def found_terminator(self):
        line = EMPTYSTRING.join(self.__line)
        
        if self.debug:
            self.logger.info('found_terminator(): data: %s' % repr(line))
            
        self.__line = []
        if self.__state == self.COMMAND:
            if not line:
                self.push('500 Error: bad syntax')
                return
            method = None
            i = line.find(' ')
            
            if self.authenticating:
                # If we are in an authenticating state, call the
                # method smtp_AUTH.
                arg = line.strip()
                command = 'AUTH'
            elif i < 0:
                command = line.upper()
                arg = None
            else:
                command = line[:i].upper()
                arg = line[i+1:].strip()
            
            # White list of operations that are allowed prior to AUTH.
            if not command in ['AUTH', 'EHLO', 'HELO', 'NOOP', 'RSET', 'QUIT']:
                if self.require_authentication and not self.authenticated:
                    self.push('530 Authentication required')
                    
            method = getattr(self, 'smtp_' + command, None)
            if not method:
                self.push('502 Error: command "%s" not implemented' % command)
                return
            method(arg)
            return
        else:
            if self.__state != self.DATA:
                self.push('451 Internal confusion')
                return
            # Remove extraneous carriage returns and de-transparency according
            # to RFC 821, Section 4.5.2.
            data = []
            for text in line.split('\r\n'):
                if text and text[0] == '.':
                    data.append(text[1:])
                else:
                    data.append(text)
            self.__data = NEWLINE.join(data)
            status = self.__server.process_message(
                self.__peer,
                self.__mailfrom,
                self.__rcpttos,
                self.__data
            )
            self.__rcpttos = []
            self.__mailfrom = None
            self.__state = self.COMMAND
            self.set_terminator('\r\n')
            if not status:
                self.push('250 Ok')
            else:
                self.push(status)

########NEW FILE########
__FILENAME__ = smtp_server
import secure_smtpd
import ssl, smtpd, asyncore, socket, logging, signal, time, sys

from smtp_channel import SMTPChannel
from asyncore import ExitNow
from process_pool import ProcessPool
from Queue import Empty
from ssl import SSLError

class SMTPServer(smtpd.SMTPServer):

    def __init__(self, localaddr, remoteaddr, ssl=False, certfile=None, keyfile=None, ssl_version=ssl.PROTOCOL_SSLv23, require_authentication=False, credential_validator=None, maximum_execution_time=30, process_count=5):
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)
        self.logger = logging.getLogger( secure_smtpd.LOG_NAME )
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version
        self.subprocesses = []
        self.require_authentication = require_authentication
        self.credential_validator = credential_validator
        self.ssl = ssl
        self.maximum_execution_time = maximum_execution_time
        self.process_count = process_count
        self.process_pool = None

    def handle_accept(self):
        self.process_pool = ProcessPool(self._accept_subprocess, process_count=self.process_count)
        self.close()

    def _accept_subprocess(self, queue):
        while True:
            try:
                self.socket.setblocking(1)
                pair = self.accept()
                map = {}

                if pair is not None:

                    self.logger.info('_accept_subprocess(): smtp connection accepted within subprocess.')

                    newsocket, fromaddr = pair
                    newsocket.settimeout(self.maximum_execution_time)

                    if self.ssl:
                        newsocket = ssl.wrap_socket(
                            newsocket,
                            server_side=True,
                            certfile=self.certfile,
                            keyfile=self.keyfile,
                            ssl_version=self.ssl_version,
                        )
                    channel = SMTPChannel(
                        self,
                        newsocket,
                        fromaddr,
                        require_authentication=self.require_authentication,
                        credential_validator=self.credential_validator,
                        map=map
                    )

                    self.logger.info('_accept_subprocess(): starting asyncore within subprocess.')

                    asyncore.loop(map=map)

                    self.logger.error('_accept_subprocess(): asyncore loop exited.')
            except (ExitNow, SSLError):
                self._shutdown_socket(newsocket)
                self.logger.info('_accept_subprocess(): smtp channel terminated asyncore.')
            except Exception, e:
                self._shutdown_socket(newsocket)
                self.logger.error('_accept_subprocess(): uncaught exception: %s' % str(e))

    def _shutdown_socket(self, s):
        try:
            s.shutdown(socket.SHUT_RDWR)
            s.close()
        except Exception, e:
            self.logger.error('_shutdown_socket(): failed to cleanly shutdown socket: %s' % str(e))


    def run(self):
        asyncore.loop()
        if hasattr(signal, 'SIGTERM'):
            def sig_handler(signal,frame):
                self.logger.info("Got signal %s, shutting down." % signal)
                sys.exit(0)
            signal.signal(signal.SIGTERM, sig_handler)
        while 1:
            time.sleep(1)

########NEW FILE########
__FILENAME__ = store_credentials
class StoreCredentials(object):
    def __init__(self):
        self.stored = False
        self.username = None
        self.password = None

    def validate(self, username, password):
        self.stored = True
        self.username = username
        self.password = password
        return True

########NEW FILE########
