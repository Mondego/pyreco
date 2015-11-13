__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

"""
gmail.exceptions
~~~~~~~~~~~~~~~~~~~

This module contains the set of Gmails' exceptions.

"""


class GmailException(RuntimeError):
    """There was an ambiguous exception that occurred while handling your
    request."""

class ConnectionError(GmailException):
    """A Connection error occurred."""

class AuthenticationError(GmailException):
    """Gmail Authentication failed."""

class Timeout(GmailException):
    """The request timed out."""

########NEW FILE########
__FILENAME__ = gmail
import re
import imaplib

from mailbox import Mailbox
from utf import encode as encode_utf7, decode as decode_utf7
from exceptions import *

class Gmail():
    # GMail IMAP defaults
    GMAIL_IMAP_HOST = 'imap.gmail.com'
    GMAIL_IMAP_PORT = 993

    # GMail SMTP defaults
    # TODO: implement SMTP functions
    GMAIL_SMTP_HOST = "smtp.gmail.com"
    GMAIL_SMTP_PORT = 587

    def __init__(self):
        self.username = None
        self.password = None
        self.access_token = None

        self.imap = None
        self.smtp = None
        self.logged_in = False
        self.mailboxes = {}
        self.current_mailbox = None


        # self.connect()


    def connect(self, raise_errors=True):
        # try:
        #     self.imap = imaplib.IMAP4_SSL(self.GMAIL_IMAP_HOST, self.GMAIL_IMAP_PORT)
        # except socket.error:
        #     if raise_errors:
        #         raise Exception('Connection failure.')
        #     self.imap = None

        self.imap = imaplib.IMAP4_SSL(self.GMAIL_IMAP_HOST, self.GMAIL_IMAP_PORT)

        # self.smtp = smtplib.SMTP(self.server,self.port)
        # self.smtp.set_debuglevel(self.debug)
        # self.smtp.ehlo()
        # self.smtp.starttls()
        # self.smtp.ehlo()

        return self.imap


    def fetch_mailboxes(self):
        response, mailbox_list = self.imap.list()
        if response == 'OK':
            for mailbox in mailbox_list:
                mailbox_name = mailbox.split('"/"')[-1].replace('"', '').strip()
                mailbox = Mailbox(self)
                mailbox.external_name = mailbox_name
                self.mailboxes[mailbox_name] = mailbox

    def use_mailbox(self, mailbox):
        if mailbox:
            self.imap.select(mailbox)
        self.current_mailbox = mailbox

    def mailbox(self, mailbox_name):
        if mailbox_name not in self.mailboxes:
            mailbox_name = encode_utf7(mailbox_name)
        mailbox = self.mailboxes.get(mailbox_name)

        if mailbox and not self.current_mailbox == mailbox_name:
            self.use_mailbox(mailbox_name)

        return mailbox

    def create_mailbox(self, mailbox_name):
        mailbox = self.mailboxes.get(mailbox_name)
        if not mailbox:
            self.imap.create(mailbox_name)
            mailbox = Mailbox(self, mailbox_name)
            self.mailboxes[mailbox_name] = mailbox

        return mailbox

    def delete_mailbox(self, mailbox_name):
        mailbox = self.mailboxes.get(mailbox_name)
        if mailbox:
            self.imap.delete(mailbox_name)
            del self.mailboxes[mailbox_name]



    def login(self, username, password):
        self.username = username
        self.password = password

        if not self.imap:
            self.connect()

        try:
            imap_login = self.imap.login(self.username, self.password)
            self.logged_in = (imap_login and imap_login[0] == 'OK')
            if self.logged_in:
                self.fetch_mailboxes()
        except imaplib.IMAP4.error:
            raise AuthenticationError


        # smtp_login(username, password)

        return self.logged_in

    def authenticate(self, username, access_token):
        self.username = username
        self.access_token = access_token

        if not self.imap:
            self.connect()

        try:
            auth_string = 'user=%s\1auth=Bearer %s\1\1' % (username, access_token)
            imap_auth = self.imap.authenticate('XOAUTH2', lambda x: auth_string)
            self.logged_in = (imap_auth and imap_auth[0] == 'OK')
            if self.logged_in:
                self.fetch_mailboxes()
        except imaplib.IMAP4.error:
            raise AuthenticationError

        return self.logged_in

    def logout(self):
        self.imap.logout()
        self.logged_in = False


    def label(self, label_name):
        return self.mailbox(label_name)

    def find(self, mailbox_name="[Gmail]/All Mail", **kwargs):
        box = self.mailbox(mailbox_name)
        return box.mail(**kwargs)

    
    def copy(self, uid, to_mailbox, from_mailbox=None):
        if from_mailbox:
            self.use_mailbox(from_mailbox)
        self.imap.uid('COPY', uid, to_mailbox)

    def fetch_multiple_messages(self, messages):
        fetch_str =  ','.join(messages.keys())
        response, results = self.imap.uid('FETCH', fetch_str, '(BODY.PEEK[] FLAGS X-GM-THRID X-GM-MSGID X-GM-LABELS)')
        for index in xrange(len(results) - 1):
            raw_message = results[index]
            if re.search(r'UID (\d+)', raw_message[0]):
                uid = re.search(r'UID (\d+)', raw_message[0]).groups(1)[0]
                messages[uid].parse(raw_message)

        return messages


    def labels(self, require_unicode=False):
        keys = self.mailboxes.keys()
        if require_unicode:
            keys = [decode_utf7(key) for key in keys]
        return keys

    def inbox(self):
        return self.mailbox("INBOX")

    def spam(self):
        return self.mailbox("[Gmail]/Spam")

    def starred(self):
        return self.mailbox("[Gmail]/Starred")

    def all_mail(self):
        return self.mailbox("[Gmail]/All Mail")

    def sent_mail(self):
        return self.mailbox("[Gmail]/Sent Mail")

    def important(self):
        return self.mailbox("[Gmail]/Important")

    def mail_domain(self):
        return self.username.split('@')[-1]

########NEW FILE########
__FILENAME__ = mailbox
from message import Message
from utf import encode as encode_utf7, decode as decode_utf7


class Mailbox():

    def __init__(self, gmail, name="INBOX"):
        self.name = name
        self.gmail = gmail
        self.date_format = "%d-%b-%Y"
        self.messages = {}

    @property
    def external_name(self):
        if "external_name" not in vars(self):
            vars(self)["external_name"] = encode_utf7(self.name)
        return vars(self)["external_name"]

    @external_name.setter
    def external_name(self, value):
        if "external_name" in vars(self):
            del vars(self)["external_name"]
        self.name = decode_utf7(value)

    def mail(self, prefetch=False, **kwargs):
        search = ['ALL']

        kwargs.get('read')   and search.append('SEEN')
        kwargs.get('unread') and search.append('UNSEEN')

        kwargs.get('starred')   and search.append('FLAGGED')
        kwargs.get('unstarred') and search.append('UNFLAGGED')

        kwargs.get('deleted')   and search.append('DELETED')
        kwargs.get('undeleted') and search.append('UNDELETED')

        kwargs.get('draft')   and search.append('DRAFT')
        kwargs.get('undraft') and search.append('UNDRAFT')

        kwargs.get('before') and search.extend(['BEFORE', kwargs.get('before').strftime(self.date_format)])
        kwargs.get('after')  and search.extend(['SINCE', kwargs.get('after').strftime(self.date_format)])
        kwargs.get('on')     and search.extend(['ON', kwargs.get('on').strftime(self.date_format)])

        kwargs.get('header') and search.extend(['HEADER', kwargs.get('header')[0], kwargs.get('header')[1]])

        kwargs.get('sender') and search.extend(['FROM', kwargs.get('sender')])
        kwargs.get('fr') and search.extend(['FROM', kwargs.get('fr')])
        kwargs.get('to') and search.extend(['TO', kwargs.get('to')])
        kwargs.get('cc') and search.extend(['CC', kwargs.get('cc')])

        kwargs.get('subject') and search.extend(['SUBJECT', kwargs.get('subject')])
        kwargs.get('body') and search.extend(['BODY', kwargs.get('body')])

        kwargs.get('label') and search.extend(['X-GM-LABELS', kwargs.get('label')])
        kwargs.get('attachment') and search.extend(['HAS', 'attachment'])

        kwargs.get('query') and search.extend([kwargs.get('query')])

        emails = []
        # print search
        response, data = self.gmail.imap.uid('SEARCH', *search)
        if response == 'OK':    
            uids = filter(None, data[0].split(' ')) # filter out empty strings

            for uid in uids:
                if not self.messages.get(uid):
                    self.messages[uid] = Message(self, uid)
                emails.append(self.messages[uid])

            if prefetch and emails:
                messages_dict = {}
                for email in emails:
                    messages_dict[email.uid] = email
                self.messages.update(self.gmail.fetch_multiple_messages(messages_dict))

        return emails

    # WORK IN PROGRESS. NOT FOR ACTUAL USE
    def threads(self, prefetch=False, **kwargs):
        emails = []
        response, data = self.gmail.imap.uid('SEARCH', 'ALL')
        if response == 'OK':    
            uids = data[0].split(' ') 


            for uid in uids:
                if not self.messages.get(uid):
                    self.messages[uid] = Message(self, uid)
                emails.append(self.messages[uid])

            if prefetch:
                fetch_str = ','.join(uids)
                response, results = self.gmail.imap.uid('FETCH', fetch_str, '(BODY.PEEK[] FLAGS X-GM-THRID X-GM-MSGID X-GM-LABELS)')
                for index in xrange(len(results) - 1):
                    raw_message = results[index]
                    if re.search(r'UID (\d+)', raw_message[0]):
                        uid = re.search(r'UID (\d+)', raw_message[0]).groups(1)[0]
                        self.messages[uid].parse(raw_message)

        return emails

    def count(self, **kwargs):
        return len(self.mail(**kwargs))

    def cached_messages(self):
        return self.messages

########NEW FILE########
__FILENAME__ = message
import datetime
import email
import re
import time
import os
from email.header import decode_header, make_header
from imaplib import ParseFlags

class Message():


    def __init__(self, mailbox, uid):
        self.uid = uid
        self.mailbox = mailbox
        self.gmail = mailbox.gmail if mailbox else None

        self.message = None
        self.headers = {}

        self.subject = None
        self.body = None
        self.html = None

        self.to = None
        self.fr = None
        self.cc = None
        self.delivered_to = None

        self.sent_at = None

        self.flags = []
        self.labels = []

        self.thread_id = None
        self.thread = []
        self.message_id = None
 
        self.attachments = None
        


    def is_read(self):
        return ('\\Seen' in self.flags)

    def read(self):
        flag = '\\Seen'
        self.gmail.imap.uid('STORE', self.uid, '+FLAGS', flag)
        if flag not in self.flags: self.flags.append(flag)

    def unread(self):
        flag = '\\Seen'
        self.gmail.imap.uid('STORE', self.uid, '-FLAGS', flag)
        if flag in self.flags: self.flags.remove(flag)

    def is_starred(self):
        return ('\\Flagged' in self.flags)

    def star(self):
        flag = '\\Flagged'
        self.gmail.imap.uid('STORE', self.uid, '+FLAGS', flag)
        if flag not in self.flags: self.flags.append(flag)

    def unstar(self):
        flag = '\\Flagged'
        self.gmail.imap.uid('STORE', self.uid, '-FLAGS', flag)
        if flag in self.flags: self.flags.remove(flag)

    def is_draft(self):
        return ('\\Draft' in self.flags)

    def has_label(self, label):
        full_label = '%s' % label
        return (full_label in self.labels)

    def add_label(self, label):
        full_label = '%s' % label
        self.gmail.imap.uid('STORE', self.uid, '+X-GM-LABELS', full_label)
        if full_label not in self.labels: self.labels.append(full_label)

    def remove_label(self, label):
        full_label = '%s' % label
        self.gmail.imap.uid('STORE', self.uid, '-X-GM-LABELS', full_label)
        if full_label in self.labels: self.labels.remove(full_label)


    def is_deleted(self):
        return ('\\Deleted' in self.flags)

    def delete(self):
        flag = '\\Deleted'
        self.gmail.imap.uid('STORE', self.uid, '+FLAGS', flag)
        if flag not in self.flags: self.flags.append(flag)

        trash = '[Gmail]/Trash' if '[Gmail]/Trash' in self.gmail.labels() else '[Gmail]/Bin'
        if self.mailbox.name not in ['[Gmail]/Bin', '[Gmail]/Trash']:
            self.move_to(trash)

    # def undelete(self):
    #     flag = '\\Deleted'
    #     self.gmail.imap.uid('STORE', self.uid, '-FLAGS', flag)
    #     if flag in self.flags: self.flags.remove(flag)


    def move_to(self, name):
        self.gmail.copy(self.uid, name, self.mailbox.name)
        if name not in ['[Gmail]/Bin', '[Gmail]/Trash']:
            self.delete()



    def archive(self):
        self.move_to('[Gmail]/All Mail')

    def parse_headers(self, message):
        hdrs = {}
        for hdr in message.keys():
            hdrs[hdr] = message[hdr]
        return hdrs

    def parse_flags(self, headers):
        return list(ParseFlags(headers))
        # flags = re.search(r'FLAGS \(([^\)]*)\)', headers).groups(1)[0].split(' ')

    def parse_labels(self, headers):
        if re.search(r'X-GM-LABELS \(([^\)]+)\)', headers):
            labels = re.search(r'X-GM-LABELS \(([^\)]+)\)', headers).groups(1)[0].split(' ')
            return map(lambda l: l.replace('"', '').decode("string_escape"), labels)
        else:
            return list()

    def parse_subject(self, encoded_subject):
        dh = decode_header(encoded_subject)
        default_charset = 'ASCII'
        return ''.join([ unicode(t[0], t[1] or default_charset) for t in dh ])

    def parse(self, raw_message):
        raw_headers = raw_message[0]
        raw_email = raw_message[1]

        self.message = email.message_from_string(raw_email)
        self.headers = self.parse_headers(self.message)

        self.to = self.message['to']
        self.fr = self.message['from']
        self.delivered_to = self.message['delivered_to']

        self.subject = self.parse_subject(self.message['subject'])

        if self.message.get_content_maintype() == "multipart":
            for content in self.message.walk():
                if content.get_content_type() == "text/plain":
                    self.body = content.get_payload(decode=True)
                elif content.get_content_type() == "text/html":
                    self.html = content.get_payload(decode=True)
        elif self.message.get_content_maintype() == "text":
            self.body = self.message.get_payload()

        self.sent_at = datetime.datetime.fromtimestamp(time.mktime(email.utils.parsedate_tz(self.message['date'])[:9]))

        self.flags = self.parse_flags(raw_headers)

        self.labels = self.parse_labels(raw_headers)

        if re.search(r'X-GM-THRID (\d+)', raw_headers):
            self.thread_id = re.search(r'X-GM-THRID (\d+)', raw_headers).groups(1)[0]
        if re.search(r'X-GM-MSGID (\d+)', raw_headers):
            self.message_id = re.search(r'X-GM-MSGID (\d+)', raw_headers).groups(1)[0]

        
        # Parse attachments into attachment objects array for this message
        self.attachments = [
            Attachment(attachment) for attachment in self.message._payload
                if not isinstance(attachment, basestring) and attachment.get('Content-Disposition') is not None
        ]
        

    def fetch(self):
        if not self.message:
            response, results = self.gmail.imap.uid('FETCH', self.uid, '(BODY.PEEK[] FLAGS X-GM-THRID X-GM-MSGID X-GM-LABELS)')

            self.parse(results[0])

        return self.message

    # returns a list of fetched messages (both sent and received) in chronological order
    def fetch_thread(self):
        self.fetch()
        original_mailbox = self.mailbox
        self.gmail.use_mailbox(original_mailbox.name)

        # fetch and cache messages from inbox or other received mailbox
        response, results = self.gmail.imap.uid('SEARCH', None, '(X-GM-THRID ' + self.thread_id + ')')
        received_messages = {}
        uids = results[0].split(' ')
        if response == 'OK':
            for uid in uids: received_messages[uid] = Message(original_mailbox, uid)
            self.gmail.fetch_multiple_messages(received_messages)
            self.mailbox.messages.update(received_messages)

        # fetch and cache messages from 'sent'
        self.gmail.use_mailbox('[Gmail]/Sent Mail')
        response, results = self.gmail.imap.uid('SEARCH', None, '(X-GM-THRID ' + self.thread_id + ')')
        sent_messages = {}
        uids = results[0].split(' ')
        if response == 'OK':
            for uid in uids: sent_messages[uid] = Message(self.gmail.mailboxes['[Gmail]/Sent Mail'], uid)
            self.gmail.fetch_multiple_messages(sent_messages)
            self.gmail.mailboxes['[Gmail]/Sent Mail'].messages.update(sent_messages)

        self.gmail.use_mailbox(original_mailbox.name)

        # combine and sort sent and received messages
        return sorted(dict(received_messages.items() + sent_messages.items()).values(), key=lambda m: m.sent_at)


class Attachment:

    def __init__(self, attachment):
        self.name = attachment.get_filename()
        # Raw file data
        self.payload = attachment.get_payload(decode=True)
        # Filesize in kilobytes
        self.size = int(round(len(self.payload)/1000.0))

    def save(self, path=None):
        if path is None:
            # Save as name of attachment if there is no path specified
            path = self.name
        elif os.path.isdir(path):
            # If the path is a directory, save as name of attachment in that directory
            path = os.path.join(path, self.name)

        with open(path, 'wb') as f:
            f.write(self.payload)

########NEW FILE########
__FILENAME__ = utf
# The contents of this file has been derived code from the Twisted project
# (http://twistedmatrix.com/). The original author is Jp Calderone.

# Twisted project license follows:

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

text_type = unicode
binary_type = str

PRINTABLE = set(range(0x20, 0x26)) | set(range(0x27, 0x7f))

def encode(s):
    """Encode a folder name using IMAP modified UTF-7 encoding.

    Despite the function's name, the output is still a unicode string.
    """
    if not isinstance(s, text_type):
        return s

    r = []
    _in = []

    def extend_result_if_chars_buffered():
        if _in:
            r.extend(['&', modified_utf7(''.join(_in)), '-'])
            del _in[:]

    for c in s:
        if ord(c) in PRINTABLE:
            extend_result_if_chars_buffered()
            r.append(c)
        elif c == '&':
            extend_result_if_chars_buffered()
            r.append('&-')
        else:
            _in.append(c)

    extend_result_if_chars_buffered()

    return ''.join(r)

def decode(s):
    """Decode a folder name from IMAP modified UTF-7 encoding to unicode.

    Despite the function's name, the input may still be a unicode
    string. If the input is bytes, it's first decoded to unicode.
    """
    if isinstance(s, binary_type):
        s = s.decode('latin-1')
    if not isinstance(s, text_type):
        return s

    r = []
    _in = []
    for c in s:
        if c == '&' and not _in:
            _in.append('&')
        elif c == '-' and _in:
            if len(_in) == 1:
                r.append('&')
            else:
                r.append(modified_deutf7(''.join(_in[1:])))
            _in = []
        elif _in:
            _in.append(c)
        else:
            r.append(c)
    if _in:
        r.append(modified_deutf7(''.join(_in[1:])))

    return ''.join(r)

def modified_utf7(s):
    # encode to utf-7: '\xff' => b'+AP8-', decode from latin-1 => '+AP8-'
    s_utf7 = s.encode('utf-7').decode('latin-1')
    return s_utf7[1:-1].replace('/', ',')

def modified_deutf7(s):
    s_utf7 = '+' + s.replace(',', '/') + '-'
    # encode to latin-1: '+AP8-' => b'+AP8-', decode from utf-7 => '\xff'
    return s_utf7.encode('latin-1').decode('utf-7')
########NEW FILE########
__FILENAME__ = utils


from .gmail import Gmail 

def login(username, password):
    gmail = Gmail()
    gmail.login(username, password)
    return gmail

def authenticate(username, access_token):
    gmail = Gmail()
    gmail.authenticate(username, access_token)
    return gmail
########NEW FILE########
