__FILENAME__ = imap
from imaplib import IMAP4, IMAP4_SSL


class ImapTransport(object):
	
	def __init__(self, hostname, port=None, ssl=False):
		self.hostname = hostname
		self.port = port
		
		if ssl:
			self.transport = IMAP4_SSL
			if not self.port:
				self.port = 993
		else:
			self.transport = IMAP4
			if not self.port:
				self.port = 143

		self.server = self.transport(self.hostname, self.port)

	def list_folders(self):
		return self.server.list()

	def connect(self, username, password):
		self.server.login(username, password)
		self.server.select()

		return self.server
	


########NEW FILE########
__FILENAME__ = parser
import re
import StringIO
import email
import base64, quopri
import time 
from datetime import datetime
from email.header import Header, decode_header


class Struct(object):
	def __init__(self, **entries):
		self.__dict__.update(entries)

	def keys(self):
		return self.__dict__.keys()

	def __repr__(self):
		return str(self.__dict__)


def decode_mail_header(value, default_charset='us-ascii'):
	"""
	Decode a header value into a unicode string. 
	"""
	try:
		headers=decode_header(value)
	except email.errors.HeaderParseError:
		return value.encode(default_charset, 'replace').decode(default_charset)
	else:
		for index, (text, charset) in enumerate(headers):
			try:
				headers[index]=text.decode(charset or default_charset, 'replace')
			except LookupError:
				# if the charset is unknown, force default 
				headers[index]=text.decode(default_charset, 'replace')

		return u"".join(headers)


def get_mail_addresses(message, header_name):
	"""
	Retrieve all email addresses from one message header.
	""" 
	addresses = email.utils.getaddresses(header for header in message.get_all(header_name, []))

	for index, (address_name, address_email) in enumerate(addresses):
		addresses[index]={'name': decode_mail_header(address_name), 'email': address_email}

	return addresses


def decode_param(param):
	name, v = param.split('=', 1)
	values = v.split('\n')
	value_results = []
	for value in values:
		match = re.search(r'=\?(\w+)\?(Q|B)\?(.+)\?=', value)
		if match:
			encoding, type_, code = match.groups()
			if type_ == 'Q':
				value = quopri.decodestring(code)
			elif type_ == 'B':
				value = base64.decodestring(code)
			value = unicode(value, encoding)
			value_results.append(value)
	if value_results: v = ''.join(value_results)
	return name, v 



def parse_attachment(message_part):
	content_disposition = message_part.get("Content-Disposition", None) # Check again if this is a valid attachment
	if content_disposition != None:
		dispositions = content_disposition.strip().split(";")
		
		if dispositions[0].lower() in ["attachment", "inline"]:
			file_data = message_part.get_payload(decode=True)

			attachment = {
				'content-type': message_part.get_content_type(),
				'size': len(file_data),
				'content': StringIO.StringIO(file_data)
			}

			for param in dispositions[1:]:
				name, value = decode_param(param)

				if 'file' in  name:
					attachment['filename'] = value
				
				if 'create-date' in name:
					attachment['create-date'] = value
			
			return attachment

	return None 

def parse_email(raw_email):
	email_message = email.message_from_string(raw_email)
	maintype = email_message.get_content_maintype()
	parsed_email = {}
	
	body = {
		"plain": [],
		"html": []
	}
	attachments = []

	if maintype == 'multipart':
		for part in email_message.walk():
			content = part.get_payload(decode=True)
			content_type = part.get_content_type()
			content_disposition = part.get('Content-Disposition', None)
			
			if content_type == "text/plain" and content_disposition == None:
				body['plain'].append(content)
			elif content_type == "text/html" and content_disposition == None:
				body['html'].append(content)
			elif content_disposition:
				attachment = parse_attachment(part)
				if attachment: attachments.append(attachment)
	
	elif maintype == 'text':
		body['plain'].append(email_message.get_payload(decode=True))

	parsed_email['attachments'] = attachments

	parsed_email['body'] = body
	email_dict = dict(email_message.items())

	parsed_email['sent_from'] = get_mail_addresses(email_message, 'from')
	parsed_email['sent_to'] = get_mail_addresses(email_message, 'to')


	value_headers_keys = ['Subject', 'Date','Message-ID']
	key_value_header_keys = ['Received-SPF', 
							'MIME-Version',
							'X-Spam-Status',
							'X-Spam-Score',
							'Content-Type']

	parsed_email['headers'] = []
	for key, value in email_dict.iteritems():
		
		if key in value_headers_keys:
			valid_key_name = key.lower().replace('-', '_')
			parsed_email[valid_key_name] = decode_mail_header(value)
		
		if key in key_value_header_keys:
			parsed_email['headers'].append({'Name': key,
				'Value': value})

	if parsed_email.get('date'):
		timetuple = email.utils.parsedate(parsed_email['date'])
		parsed_email['parsed_date'] = datetime.fromtimestamp(time.mktime(timetuple)) if timetuple else None

	return Struct(**parsed_email)


########NEW FILE########
__FILENAME__ = query
# TODO - Validate query arguments
def build_search_query(**kwargs):

	# Parse keyword arguments 
	unread = kwargs.get('unread', False)
	sent_from = kwargs.get('sent_from', False)
	sent_to = kwargs.get('sent_to', False)
	date__gt = kwargs.get('date__gt', False)
	date__lt = kwargs.get('date__lt', False)

	query = "(ALL)"

	if unread != False:
		query = "(UNSEEN)"

	if sent_from:
		query = '{0} (FROM "{1}")'.format(query, sent_from)

	if sent_to:
		query = '{0} (TO "{1}")'.format(query, sent_to)

	if date__gt:
		query = '{0} (SINCE "{1}")'.format(query, date__gt)

	if date__lt:
		query = '{0} (BEFORE "{1}")'.format(query, date__lt)

	return str(query)
########NEW FILE########
__FILENAME__ = parser_tests
import unittest
import email
from imbox.parser import *

raw_email = """Delivered-To: johndoe@gmail.com
X-Originating-Email: [martin@amon.cx]
Message-ID: <test0@example.com>
Return-Path: martin@amon.cx
Date: Tue, 30 Jul 2013 15:56:29 +0300
From: Martin Rusev <martin@amon.cx>
MIME-Version: 1.0
To: John Doe <johndoe@gmail.com>
Subject: Test email - no attachment
Content-Type: multipart/alternative;
	boundary="------------080505090108000500080106"
X-OriginalArrivalTime: 30 Jul 2013 12:56:43.0604 (UTC) FILETIME=[3DD52140:01CE8D24]

--------------080505090108000500080106
Content-Type: text/plain; charset="ISO-8859-1"; format=flowed
Content-Transfer-Encoding: 7bit

Hi, this is a test email with no attachments

--------------080505090108000500080106
Content-Type: text/html; charset="ISO-8859-1"
Content-Transfer-Encoding: 7bit

<html><head>
<meta http-equiv="content-type" content="text/html; charset=ISO-8859-1"></head><body
 bgcolor="#FFFFFF" text="#000000">
Hi, this is a test email with no <span style="font-weight: bold;">attachments</span><br>
</body>
</html>

--------------080505090108000500080106--
"""

class TestParser(unittest.TestCase):


	
	def test_parse_email(self):
		parsed_email = parse_email(raw_email)

		self.assertEqual(u'Test email - no attachment', parsed_email.subject)


	# TODO - Complete the test suite
	def test_parse_attachment(self):
		pass

 	def test_decode_mail_header(self):
 		pass
   
	
	
	def test_get_mail_addresses(self):

		to_message_object = email.message_from_string("To: John Doe <johndoe@gmail.com>")
		self.assertEqual([{'email': 'johndoe@gmail.com', 'name': u'John Doe'}], get_mail_addresses(to_message_object, 'to'))

		from_message_object = email.message_from_string("From: John Smith <johnsmith@gmail.com>")
		self.assertEqual([{'email': 'johnsmith@gmail.com', 'name': u'John Smith'}], get_mail_addresses(from_message_object, 'from'))


########NEW FILE########
