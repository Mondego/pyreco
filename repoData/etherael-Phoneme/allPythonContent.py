__FILENAME__ = crypt_gmail
import gnupg
from email.parser import HeaderParser
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from StringIO import StringIO
from email.generator import Generator
import getpass
import imaplib

gpg = gnupg.GPG()
gpg.encoding = 'utf-8'
print "Gmail user"
recipient = raw_input()
print "Gmail folder (label) to encrypt (leave blank for all mail - case sensitive)"
specific_folder = raw_input()
password = getpass.getpass("Gmail password:")
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(recipient,password)

def encrypt_msg(msg):
  encrypted_body = str(gpg.encrypt(get_mime_payload(msg),recipient,always_trust=True))
  multipart = MIMEMultipart("encrypted")
  multipart.preamble = "This is a GPG/MIME encrypted message (RFC 4880 and 3156)"

  del multipart['MIME-version']
  encrypted = MIMEApplication("Version: 1","pgp-encrypted",email.encoders.encode_noop)
  encrypted.add_header("Content-Description","PGP/MIME version identification")
  del encrypted['MIME-Version']

  octetstream = MIMEApplication(encrypted_body,"octet-stream",email.encoders.encode_noop,name="encrypted.asc")
  octetstream.add_header("Content-Disposition","inline",filename="encrypted.asc")
  octetstream.add_header("Content-Description","GPG encrypted message")
  del octetstream['MIME-Version']
  multipart.attach(encrypted)
  multipart.attach(octetstream)

  for key in msg.keys():
    multipart[key] = msg[key]
  multipart.set_param("protocol","application/pgp-encrypted")
  del multipart['Content-Transfer-Encoding']

  return multipart

def get_mime_payload(msg):
  if not msg.is_multipart():
    mimemail = MIMEBase(msg.get_content_maintype(),msg.get_content_subtype(),charset=msg.get_content_charset())
    mimemail.set_payload(msg.get_payload())
    if msg.has_key('Content-Transfer-Encoding'):
      mimemail['Content-Transfer-Encoding'] = msg['Content-Transfer-Encoding']
  else:
    mimemail = MIMEMultipart(msg.get_content_subtype())
    for payload in msg.get_payload():
      mimemail.attach(payload)

  return flatten_message(mimemail)

def flatten_message(msg):
  fp = StringIO()
  g = Generator(fp,mangle_from_=False, maxheaderlen=60)
  g.flatten(msg)
  return fp.getvalue()


def all_folders():
  if specific_folder != '':
    yield specific_folder
  else:
    for folder in mail.list()[1]:
      yield folder.split("/")[1].split('"')[2]

def all_mail():
  for folder in all_folders():
    print 'Processing folder:', folder
    mail.select(folder)
    result, data = mail.search(None,'(NOT BODY "BEGIN PGP MESSAGE")')
    ids = data[0]
    id_list = ids.split()
    for imap_id in id_list:
      result,data = mail.fetch(imap_id,'(RFC822)')
      mail.store(imap_id, '+X-GM-LABELS', '\\Trash')
      mail.expunge()

      msg = email.message_from_string(data[0][1])
      parser = HeaderParser()
      headers = parser.parsestr(data[0][1])

      if headers == None:
        date = ''
      else:
        pz = email.utils.parsedate_tz(headers['Date'])
        stamp = email.utils.mktime_tz(pz)
        date = imaplib.Time2Internaldate(stamp)

      yield (folder,msg,date,headers)

def send_mail(data,send_from,rcpt_to,subject):
  msg = MIMEText(data)

  msg['Subject'] = subject
  msg['From'] = send_from
  msg['To'] = rcpt_to

  session.sendmail(send_from,rcpt_to,msg.as_string())

for folder,msg,date,headers in all_mail():
  try:
    encrypted_body = encrypt_msg(msg)
    mail.append(folder,'\\seen',date, flatten_message(encrypted_body))
    print "Encrypted %s from %s in folder %s" % (headers['Subject'],headers['From'],folder)
  except Exception, e:
    print e

########NEW FILE########
