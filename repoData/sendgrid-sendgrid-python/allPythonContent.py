__FILENAME__ = exceptions
class SendGridError(Exception):

    """Base class for SendGrid-related errors."""


class SendGridClientError(SendGridError):

    """Client error, which corresponds to a 4xx HTTP error."""


class SendGridServerError(SendGridError):

    """Server error, which corresponds to a 5xx HTTP error."""

########NEW FILE########
__FILENAME__ = message
import io
import sys
try:
    import rfc822
except Exception as e:
    import email.utils as rfc822
from smtpapi import SMTPAPIHeader


class Mail(SMTPAPIHeader):

    """SendGrid Message."""

    def __init__(self, **opts):
        """
        Constructs SendGrid Message object.

        Args:
            to: Recipient
            to_name: Recipient name
            from_email: Sender email
            from_name: Sender name
            subject: Email title
            text: Email body
            html: Email body
            bcc: Recipient
            reply_to: Reply address
            date: Set date
            headers: Set headers
            files: Attachments
        """
        super(Mail, self).__init__()
        self.to = []
        self.to_name = []
        self.add_to(opts.get('to', []))
        self.add_to_name(opts.get('to_name', []))
        self.from_email = opts.get('from_email', '')
        self.from_name = opts.get('from_name', '')
        self.subject = opts.get('subject', '')
        self.text = opts.get('text', '')
        self.html = opts.get('html', '')
        self.bcc = []
        self.add_bcc(opts.get('bcc', []))
        self.reply_to = opts.get('reply_to', '')
        self.files = opts.get('files', {})
        self.headers = opts.get('headers', '')
        self.date = opts.get('date', rfc822.formatdate())

    def parse_and_add(self, to):
        super(Mail, self).add_to(to)
        name, email = rfc822.parseaddr(to.replace(',', ''))
        if email:
            self.to.append(email)
        if name:
            self.add_to_name(name)

    def add_to(self, to):
        if isinstance(to, str):
            self.parse_and_add(to)
        elif sys.version_info < (3, 0) and isinstance(to, unicode):
            self.parse_and_add(to.encode('utf-8'))
        elif hasattr(to, '__iter__'):
            for email in to:
                self.add_to(email)

    def add_to_name(self, to_name):
        if isinstance(to_name, str):
            self.to_name.append(to_name)
        elif sys.version_info < (3, 0) and isinstance(to_name, unicode):
            self.to_name.append(to_name.encode('utf-8'))
        elif hasattr(to_name, '__iter__'):
            self.to_name = self.to_name + to_name

    def set_from(self, from_email):
        name, email = rfc822.parseaddr(from_email.replace(',', ''))
        if email:
            self.from_email = email
        if name:
            self.set_from_name(name)

    def set_from_name(self, from_name):
        self.from_name = from_name

    def set_subject(self, subject):
        self.subject = subject

    def set_text(self, text):
        self.text = text

    def set_html(self, html):
        self.html = html

    def add_bcc(self, bcc):
        if isinstance(bcc, str):
            email = rfc822.parseaddr(bcc.replace(',', ''))[1]
            self.bcc.append(email)
        elif sys.version_info < (3, 0) and isinstance(bcc, unicode):
            email = rfc822.parseaddr(bcc.replace(',', ''))[1].encode('utf-8')
            self.bcc.append(email)
        elif hasattr(bcc, '__iter__'):
            for email in bcc:
                self.add_bcc(email)

    def set_replyto(self, replyto):
        self.reply_to = replyto

    def add_attachment(self, name, file_):
        if isinstance(file_, str):  # filepath
            with open(file_, 'rb') as f:
                self.files[name] = f.read()
        elif hasattr(file_, 'read'):
            self.files[name] = file_.read()

    def add_attachment_stream(self, name, string):
        if isinstance(string, str):
            self.files[name] = string
        elif isinstance(string, io.BytesIO):
            self.files[name] = string.read()
        elif sys.version_info < (3, 0) and isinstance(string, unicode):
            self.files[name] = string

    def set_headers(self, headers):
        self.headers = headers

    def set_date(self, date):
        self.date = date

########NEW FILE########
__FILENAME__ = sendgrid
import sys
from socket import timeout
try:
    import urllib.request as urllib_request
    from urllib.parse import urlencode
    from urllib.error import HTTPError
except ImportError:  # Python 2
    import urllib2 as urllib_request
    from urllib2 import HTTPError
    from urllib import urlencode

from .exceptions import SendGridClientError, SendGridServerError


class SendGridClient(object):

    """SendGrid API."""

    def __init__(self, username, password, **opts):
        """
        Construct SendGrid API object.

        Args:
            username: SendGrid username
            password: SendGrid password
            user: Send mail on behalf of this user (web only)
            raise_errors: If set to False (default): in case of error, `.send`
                method will return a tuple (http_code, error_message). If set
                to True: `.send` will raise SendGridError. Note, from version
                1.0.0, the default will be changed to True, so you are
                recommended to pass True for forwards compatability.
        """
        self.username = username
        self.password = password
        self.host = opts.get('host', 'https://api.sendgrid.com')
        self.port = str(opts.get('port', '443'))
        self.endpoint = opts.get('endpoint', '/api/mail.send.json')
        self.mail_url = self.host + ':' + self.port + self.endpoint
        self._raise_errors = opts.get('raise_errors', False)
        # urllib cannot connect to SSL servers using proxies
        self.proxies = opts.get('proxies', None)

    def _build_body(self, message):
        if sys.version_info < (3, 0):
            ks = ['from_email', 'from_name', 'subject',
                  'text', 'html', 'reply_to']
            for k in ks:
                v = getattr(message, k)
                if isinstance(v, unicode):
                    setattr(message, k, v.encode('utf-8'))

        if (message.bcc):
            message.set_tos([])

        values = {
            'api_user': self.username,
            'api_key': self.password,
            'to[]': message.to,
            'toname[]': message.to_name,
            'bcc[]': message.bcc,
            'from': message.from_email,
            'fromname': message.from_name,
            'subject': message.subject,
            'text': message.text,
            'html': message.html,
            'replyto': message.reply_to,
            'headers': message.headers,
            'date': message.date,
            'x-smtpapi': message.json_string()
        }
        for k in list(values.keys()):
            if not values[k]:
                del values[k]
        for filename in message.files:
            if message.files[filename]:
                values['files[' + filename + ']'] = message.files[filename]
        return values

    def _make_request(self, message):
        if self.proxies:
            proxy_support = urllib_request.ProxyHandler(self.proxies)
            opener = urllib_request.build_opener(proxy_support)
            urllib_request.install_opener(opener)
        data = urlencode(self._build_body(message), True).encode('utf-8')
        req = urllib_request.Request(self.mail_url, data)
        response = urllib_request.urlopen(req, timeout=10)
        body = response.read()
        return response.getcode(), body

    def send(self, message):
        if self._raise_errors:
            return self._raising_send(message)
        else:
            return self._legacy_send(message)

    def _legacy_send(self, message):
        try:
            return self._make_request(message)
        except HTTPError as e:
            return e.code, e.read()
        except timeout as e:
            return 408, e

    def _raising_send(self, message):
        try:
            self._make_request(message)
        except HTTPError as e:
            if e.code in range(400, 500):
                raise SendGridClientError(e.code, e.read())
            elif e.code in range(500, 600):
                raise SendGridServerError(e.code, e.read())
            else:
                assert False
        except timeout as e:
            raise SendGridClientError(408, 'Request timeout')

########NEW FILE########
