__FILENAME__ = config
import os

author = 'Zed A. Shaw' # Default author name. Overridden in individual document
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
input_dir = os.path.join(THIS_DIR, 'input')
output_dir = os.path.join(THIS_DIR, 'output')
template_dir = THIS_DIR
template = os.path.join(template_dir, 'template.html')

### Optional parameters
options = { 'baseurl':"", # if not set, relative URLs will be generated
            'sitename':"Lamson Project(TM)",
            'slogan': "Lamson The Python SMTP Server and Framework",
            'extensions':['.txt'],
            'format': 'text/x-textile',
            'siteurl': 'http://lamsonproject.org',
          }

########NEW FILE########
__FILENAME__ = mailocalypse
import email
from email.header import make_header, decode_header
from string import capwords
import sys
import mailbox


ALL_MAIL = 0
BAD_MAIL = 0


def all_parts(msg):
    parts = [m for m in msg.walk() if m != msg]
    
    if not parts:
        parts = [msg]

    return parts

def collapse_header(header):
    if header.strip().startswith("=?"):
        decoded = decode_header(header)
        converted = (unicode(
            x[0], encoding=x[1] or 'ascii', errors='replace')
            for x in decoded)
        value = u"".join(converted)
    else:
        value = unicode(header, errors='replace')

    return value.encode("utf-8")


def convert_header_insanity(header):
    if header is None: 
        return header
    elif type(header) == list:
        return [collapse_header(h) for h in header]
    else:
        return collapse_header(header)


def encode_header(name, val, charset='utf-8'):
    msg[name] = make_header([(val, charset)]).encode()


def bless_headers(msg):
    # go through every header and convert it to utf-8
    headers = {}

    for h in msg.keys():
        headers[capwords(h, '-')] = convert_header_insanity(msg[h])

    return headers

def dump_headers(headers):
    for h in headers:
        print h, headers[h]

def mail_load_cleanse(msg_file):
    global ALL_MAIL
    global BAD_MAIL

    msg = email.message_from_file(msg_file)
    headers = bless_headers(msg)

    # go through every body and convert it to utf-8
    parts = all_parts(msg)
    bodies = []
    for part in parts:
        guts = part.get_payload(decode=True)
        if part.get_content_maintype() == "text":
            charset = part.get_charsets()[0]
            try:
                if charset:
                    uguts = unicode(guts, part.get_charsets()[0])
                    guts = uguts.encode("utf-8")
                else:
                    guts = guts.encode("utf-8")
            except UnicodeDecodeError, exc:
                print >> sys.stderr, "CONFLICTED CHARSET:", exc, part.get_charsets()
                BAD_MAIL += 1
            except LookupError, exc:
                print >> sys.stderr, "UNKNOWN CHARSET:", exc, part.get_charsets()
                BAD_MAIL += 1
            except Exception, exc:
                print >> sys.stderr, "WEIRDO ERROR", exc, part.get_charsets()
                BAD_MAIL += 1


            ALL_MAIL += 1

mb = None

try:
    mb = mailbox.Maildir(sys.argv[1])
    len(mb)  # need this to make the maildir try to read the directory and fail
except OSError:
    print "NOT A MAILDIR, TRYING MBOX"
    mb = mailbox.mbox(sys.argv[1])

if not mb:
    print "NOT A MAILDIR OR MBOX, SORRY"

for key in mb.keys():
    mail_load_cleanse(mb.get_file(key))

print >> sys.stderr, "ALL", ALL_MAIL
print >> sys.stderr, "BAD", BAD_MAIL

########NEW FILE########
__FILENAME__ = webgen
#!/usr/bin/env python
from __future__ import with_statement

import os
import sys
import string
from string import Template
from config import *
from datetime import date
from textile import textile
from stat import *
import datetime
import PyRSS2Gen

rss = PyRSS2Gen.RSS2(
    title = options["sitename"],
    link = options["siteurl"],
    description = options["slogan"],
    lastBuildDate = datetime.datetime.now(),
    items = [])


def add_rss_item(rss, title, link, description, pubDate):
       item = PyRSS2Gen.RSSItem(title = title, link = link,
         description = description,
         guid = PyRSS2Gen.Guid(link),
         pubDate = datetime.datetime.fromtimestamp(pubDate))
       rss.items.append(item)

def ext(fname):
    return os.path.splitext(fname)[1]

def process(fname):
    with open(fname, 'r') as f:
        try:
            head, body = f.read().split('\n\n')
            body
        except:
            print 'Invalid file format : ', fname

def parse(fname):
    with open(fname, 'r') as f:
        raw = f.read()
        headers = {}
        try:
            (header_lines,body) = raw.split("\n\n", 1)
            for header in header_lines.split("\n"):
                (name, value) = header.split(": ", 1)
                headers[name.lower()] = unicode(value.strip())
            return headers, body
        except:
            raise TypeError, "Invalid page file format for %s" % fname

           
def get_template(template):
    """Takes the directory where templates are located and the template name. Returns a blob containing the template."""
    template = os.path.join(template_dir, template)

    return Template(open(template, 'r').read())
       
def source_newer(source, target):
    if len(sys.argv) > 1 and sys.argv[1] == "force":
        return True

    if not os.path.exists(target): 
        return True
    else:
        smtime = os.stat(source)[ST_MTIME]
        tmtime = os.stat(target)[ST_MTIME]
        return smtime > tmtime

def is_blog(current_dir, myself, headers, files):
    """A page tagged as an entry will get the files, sort them by their dates,
    and then the contents will be that directory listing instead."""
    
    if 'content-type' in headers and headers['content-type'] == "text/blog":
        # it's a listing, make it all work
        without_self = files[:]
        without_self.remove(os.path.split(myself)[-1])
        without_self.sort(reverse=True)

        listing = []
        for f in without_self:
            print "Doing blog", f
            # load up the file and peel out the first few paragraphs
            content = os.path.join(current_dir, f)
            head, body = parse(content)
            paras = [p for p in body.split("\n\n") if p]
            if paras:
                # now make a simple listing entry with it
                date, ext = os.path.splitext(f)
                head["link"] = os.path.join("/" + os.path.split(current_dir)[-1], date + ".html")
                head["date"] = date
                format = determine_format(head)
                pubDate = smtime = os.stat(content)[ST_CTIME]
                head["content"] = content_format(current_dir, f, head, files,
                                                 format, "\n\n".join(paras[0:1]))
                template = head['item-template'] if 'item-template' in head else headers['item-template']
                description = get_template(template).safe_substitute(head)

                if "feed" not in headers:
                    add_rss_item(rss, head["title"], options["siteurl"] +
                                 head["link"], description, pubDate)
                listing.append(description)

        return lambda s: "".join(listing)
    else:
        return lambda s: s

def content_format(current_dir, inp, headers, files, format, body):
    return {
            u'text/plain': lambda s: u'<pre>%s</pre>' % s,
            u'text/x-textile':  lambda s: u'%s' % textile(s,head_offset=0, validate=0, 
                                sanitize=0, encoding='utf-8', output='utf-8'),
            u'text/html': lambda s: s,
            u'text/blog': is_blog(current_dir, inp, headers, files)
        }[format](body)

def determine_format(headers):
    if 'content-type' in headers:
        return headers['content-type']
    else:
        return options['format']

def parse_directory(current_dir, files, output_dir):
    files = [f for f in files if ext(f) in options['extensions']]
    for f in files:
        inp = os.path.join(current_dir, f)
        target = os.path.join(output_dir, f)
        # TODO: Allow specifying the target extension from headers
        outp = os.path.splitext(target)[0] + '.html'

        # always redo the indexes since they'll typically list information to
        # update from the directory they are in
        if not source_newer(inp, outp) and f != "index.txt":
            continue

        headers, body = parse(inp)

        if 'template' not in headers:
            blob = get_template(template)
        else:
            blob = get_template(headers['template'])

        format = determine_format(headers)

        print "Processing %s" % inp

        content = content_format(current_dir, inp, headers, files, format, body)
        
        headers['content'] = content
        headers.update(options)
        output = blob.safe_substitute(**headers)

        outf = open(outp, 'w')
        outf.write(output)
        outf.close()

def a_fucking_cmp_for_time(x,y):
    diff = y.pubDate - x.pubDate
    return diff.days * 24 * 60 * 60 + diff.seconds

def main():
    ### Walks through the input dir creating finding all subdirectories.
    for root, dirs, files in os.walk(input_dir):
        output = root.replace(input_dir, output_dir)
        ### Checks if the directory exists in output and creates it if false.
        if not os.path.isdir(output):
            os.makedirs(output)

        parse_directory(root, files, output)

    x,y = rss.items[0], rss.items[-1]
    diff = x.pubDate - y.pubDate
    print "diff!", diff.seconds, diff.days
    rss.items.sort(cmp=lambda x,y: a_fucking_cmp_for_time(x,y))
    rss.write_xml(open("output/feed.xml", "w"))

    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = admin
from email.utils import parseaddr
from config.settings import relay, SPAM, CONFIRM
import logging
from lamson import view, queue
from lamson.routing import route, stateless, route_like, state_key_generator
from lamson.bounce import bounce_to
from lamson.server import SMTPError
from lamson.spam import spam_filter
from app.model import mailinglist, bounce, archive
from app.handlers import bounce


INVALID_LISTS = ["noreply", "unbounce"]


@state_key_generator
def module_and_to(module_name, message):
    name, address = parseaddr(message['to'])
    if '-' in address:
        list_name = address.split('-')[0]
    else:
        list_name = address.split('@')[0]

    return module_name + ':' + list_name


@route("(address)@(host)", address='.+')
def SPAMMING(message, **options):
    return SPAMMING


@route('(bad_list)@(host)', bad_list='.+')
@route('(list_name)@(host)')  # list_name and host regexes are defined in config/settings.py (router_defaults)
@route('(list_name)-subscribe@(host)')
@bounce_to(soft=bounce.BOUNCED_SOFT, hard=bounce.BOUNCED_HARD)
@spam_filter(SPAM['db'], SPAM['rc'], SPAM['queue'], next_state=SPAMMING)
def START(message, list_name=None, host=None, bad_list=None):
    if bad_list:
        if '-' in bad_list:
            # probably put a '.' in it, try to find a similar list
            similar_lists = mailinglist.similar_named_lists(bad_list.replace('-','.'))
        else:
            similar_lists = mailinglist.similar_named_lists(bad_list)

        help = view.respond(locals(), "mail/bad_list_name.msg",
                            From="noreply@%(host)s",
                            To=message['from'],
                            Subject="That's not a valid list name.")
        relay.deliver(help)

        return START

    elif list_name in INVALID_LISTS or message['from'].endswith(host):
        logging.debug("LOOP MESSAGE to %r from %r.", message['to'],
                     message['from'])
        return START

    elif mailinglist.find_list(list_name):
        action = "subscribe to"
        CONFIRM.send(relay, list_name, message, 'mail/confirmation.msg',
                          locals())
        return CONFIRMING_SUBSCRIBE

    else:
        similar_lists = mailinglist.similar_named_lists(list_name)
        CONFIRM.send(relay, list_name, message, 'mail/create_confirmation.msg',
                          locals())

        return CONFIRMING_SUBSCRIBE

@route('(list_name)-confirm-(id_number)@(host)')
def CONFIRMING_SUBSCRIBE(message, list_name=None, id_number=None, host=None):
    original = CONFIRM.verify(list_name, message['from'], id_number)

    if original:
        mailinglist.add_subscriber(message['from'], list_name)

        msg = view.respond(locals(), "mail/subscribed.msg",
                           From="noreply@%(host)s",
                           To=message['from'],
                           Subject="Welcome to %(list_name)s list.")
        relay.deliver(msg)

        CONFIRM.cancel(list_name, message['from'], id_number)

        return POSTING
    else:
        logging.warning("Invalid confirm from %s", message['from'])
        return CONFIRMING_SUBSCRIBE


@route('(list_name)-(action)@(host)', action='[a-z]+')
@route('(list_name)@(host)')
@spam_filter(SPAM['db'], SPAM['rc'], SPAM['queue'], next_state=SPAMMING)
def POSTING(message, list_name=None, action=None, host=None):
    if action == 'unsubscribe':
        action = "unsubscribe from"
        CONFIRM.send(relay, list_name, message, 'mail/confirmation.msg',
                          locals())
        return CONFIRMING_UNSUBSCRIBE
    else:
        mailinglist.post_message(relay, message, list_name, host)
        # archive makes sure it gets cleaned up before archival
        final_msg = mailinglist.craft_response(message, list_name, 
                                               list_name + '@' + host)
        archive.enqueue(list_name, final_msg)
        return POSTING
    

@route_like(CONFIRMING_SUBSCRIBE)
def CONFIRMING_UNSUBSCRIBE(message, list_name=None, id_number=None, host=None):
    original = CONFIRM.verify(list_name, message['from'], id_number)

    if original:
        mailinglist.remove_subscriber(message['from'], list_name)

        msg = view.respond(locals(), 'mail/unsubscribed.msg',
                           From="noreply@%(host)s",
                           To=message['from'],
                           Subject="You are now unsubscribed from %(list_name)s.")
        relay.deliver(msg)

        CONFIRM.cancel(list_name, message['from'], id_number)

        return START
    else:
        logging.warning("Invalid unsubscribe confirm from %s", message['from'])
        return CONFIRMING_UNSUBSCRIBE


@route("(address)@(host)", address=".+")
@spam_filter(SPAM['db'], SPAM['rc'], SPAM['queue'], next_state=SPAMMING)
def BOUNCING(message, address=None, host=None):
    msg = view.respond(locals(), 'mail/we_have_disabled_you.msg',
                       From='unbounce@librelist.com',
                       To=message['from'],
                       Subject='You have bounced and are disabled.')
    relay.deliver(msg)
    return BOUNCING


########NEW FILE########
__FILENAME__ = bounce
from config.settings import relay, CONFIRM
from lamson.routing import route, Router, route_like
from lamson.bounce import bounce_to
from app.model import mailinglist, bounce
from app import handlers
from email.utils import parseaddr



def force_to_bounce_state(message):
    # set their admin module state to disabled
    name, address = parseaddr(message.bounce.final_recipient)
    Router.STATE_STORE.set_all(address, 'BOUNCING')
    Router.STATE_STORE.set('app.handlers.bounce', address, 'BOUNCING')
    mailinglist.disable_all_subscriptions(message.bounce.final_recipient)

@route(".+")
def BOUNCED_HARD(message):
    if mailinglist.find_subscriptions(message.bounce.final_recipient):
        force_to_bounce_state(message)

    bounce.archive_bounce(message)
    return handlers.admin.START

@route(".+")
def BOUNCED_SOFT(message):
    if mailinglist.find_subscriptions(message.bounce.final_recipient):
        force_to_bounce_state(message)
        msg = bounce.mail_to_you_is_bouncing(message)
        relay.deliver(msg)

    bounce.archive_bounce(message)
    return handlers.admin.START


@route('unbounce@(host)')
def BOUNCING(message, host=None):
    CONFIRM.send(relay, 'unbounce', message, 'mail/unbounce_confirm.msg',
                      locals())

    return CONFIRMING_UNBOUNCE


@route('unbounce-confirm-(id_number)@(host)')
def CONFIRMING_UNBOUNCE(message, id_number=None, host=None):
    original = CONFIRM.verify('unbounce', message['from'], id_number)

    if original:
        relay.deliver(bounce.you_are_now_unbounced(message))
        name, address = parseaddr(message['from'])
        Router.STATE_STORE.set_all(address, 'POSTING')
        mailinglist.enable_all_subscriptions(message['from'])
        return UNBOUNCED

@route('unbounce@(host)')
def UNBOUNCED(message, host=None):
    # we just ignore these since they may be strays
    return UNBOUNCED



########NEW FILE########
__FILENAME__ = archive
from __future__ import with_statement
from lamson import queue
from config import settings
from datetime import datetime
import os
import shutil
import simplejson as json
import base64
import stat

ALLOWED_HEADERS = set([
 "From", "In-Reply-To", "List-Id",
 "Precedence", "References", "Reply-To",
 "Return-Path", "Sender",
 "Subject", "To", "Message-Id",
 "Date", "List-Id",
])

DIR_MOD = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
FILE_MOD = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

def day_of_year_path():
    return "%d/%0.2d/%0.2d" % datetime.today().timetuple()[0:3]

def store_path(list_name, name):
    datedir = os.path.join(settings.ARCHIVE_BASE, list_name, day_of_year_path())

    if not os.path.exists(datedir):
        os.makedirs(datedir)

    return os.path.join(datedir, name)

def fix_permissions(path):
    os.chmod(path, DIR_MOD)

    for root, dirs, files in os.walk(path):
        os.chmod(root, DIR_MOD)
        for f in files:
            os.chmod(os.path.join(root, f), FILE_MOD)

def update_json(list_name, key, message):
    jpath = store_path(list_name, 'json')
    json_file = key + ".json"
    json_archive = os.path.join(jpath, json_file)

    if not os.path.exists(jpath):
        os.makedirs(jpath)

    with open(json_archive, "w") as f:
        f.write(to_json(message.base))

    fix_permissions(jpath)


def enqueue(list_name, message):
    qpath = store_path(list_name, 'queue')
    pending = queue.Queue(qpath, safe=True)
    white_list_cleanse(message)

    key = pending.push(message)
    fix_permissions(qpath)

    update_json(list_name, key, message)
    return key

def white_list_cleanse(message):
    for key in message.keys():
        if key not in ALLOWED_HEADERS:
            del message[key]

    message['from'] = message['from'].replace(u'@',u'-AT-')
   

def json_encoding(base):
    ctype, ctp = base.content_encoding['Content-Type']
    cdisp, cdp = base.content_encoding['Content-Disposition']
    ctype = ctype or "text/plain"
    filename = ctp.get('name',None) or cdp.get('filename', None)

    if ctype.startswith('text') or ctype.startswith('message'):
        encoding = None
    else:
        encoding = "base64"

    return {'filename': filename, 'type': ctype, 'disposition': cdisp,
            'format': encoding}

def json_build(base):
    data = {'headers': base.headers,
                'body': base.body,
                'encoding': json_encoding(base),
                'parts': [json_build(p) for p in base.parts],
            }

    if data['encoding']['format'] and base.body:
        data['body'] = base64.b64encode(base.body)

    return data

def to_json(base):
    return json.dumps(json_build(base), sort_keys=True, indent=4)


########NEW FILE########
__FILENAME__ = bounce
from lamson import view, encoding, queue
from config import settings


def mail_to_you_is_bouncing(message):
    reason = message.bounce.error_for_humans()

    msg = view.respond(locals(), 'mail/you_bounced.msg',
                       From='unbounce@librelist.com',
                       To=message.bounce.original['to'],
                       Subject="Email to you is bouncing.")

    if message.bounce.report:
        for report in message.bounce.report:
            msg.attach('bounce_report.msg', content_type='text/plain', data=encoding.to_string(report),
                       disposition='attachment')

    if message.bounce.notification:
        msg.attach('notification_report.msg', content_type='text/plain',
                   data=encoding.to_string(message.bounce.notification),
                   disposition='attachment')

    return msg

def you_are_now_unbounced(message):
    msg = view.respond(locals(), 'mail/you_are_unbounced.msg',
                       From='noreply@librelist.com',
                       To=message['from'],
                       Subject="You are now unbounced.")

    return msg


def archive_bounce(message):
    qu = queue.Queue(settings.BOUNCE_ARCHIVE)
    qu.push(message)


########NEW FILE########
__FILENAME__ = confirmation
from webapp.librelist.models import Confirmation

class DjangoConfirmStorage():
    def clear(self):
        Confirmation.objects.all().delete()

    def get(self, target, from_address):
        confirmations = Confirmation.objects.filter(from_address=from_address, 
                                                list_name=target)
        if confirmations:
            return confirmations[0].expected_secret, confirmations[0].pending_message_id
        else:
            return None, None

    def delete(self, target, from_address):
        Confirmation.objects.filter(from_address=from_address, 
                                                list_name=target).delete()

    def store(self, target, from_address, expected_secret, pending_message_id):
        conf = Confirmation(from_address=from_address,
                            expected_secret = expected_secret,
                            pending_message_id = pending_message_id,
                            list_name=target)
        conf.save()


########NEW FILE########
__FILENAME__ = mailinglist
from webapp.librelist.models import *
from django.db.models import Q
from email.utils import parseaddr
from lamson.mail import MailResponse
from config import settings
from lib import metaphone
import Stemmer

def stem_and_meta(list_name):
    s = Stemmer.Stemmer('english')
    name = " ".join(s.stemWords(list_name.split('.')))
    return metaphone.dm(name)

def create_list(list_name):
    list_name = list_name.lower()
    mlist = find_list(list_name)
    sim_pri, sim_sec = stem_and_meta(list_name)

    if not mlist:
        mlist = MailingList(archive_url = "/archives/" + list_name,
                            archive_queue = "/queues/" + list_name,
                            name=list_name,
                            similarity_pri = sim_pri,
                            similarity_sec = sim_sec)
        mlist.save()

    return mlist

def delete_list(list_name):
    MailingList.objects.filter(name = list_name).delete()

def find_list(list_name):
    mlists = MailingList.objects.filter(name = list_name)
    if mlists:
        return mlists[0]
    else:
        return None

def add_subscriber(address, list_name):
    mlist = create_list(list_name)
    sub_name, sub_addr = parseaddr(address)
    subs = find_subscriptions(address, list_name)

    if not subs:
        sub = Subscription(subscriber_name = sub_name,
                           subscriber_address = sub_addr,
                           mailing_list = mlist)
        sub.save()
        return sub
    else:
        return subs[0]

def remove_subscriber(address, list_name):
    find_subscriptions(address, list_name).delete()

def remove_all_subscriptions(address):
    find_subscriptions(address).delete()

def find_subscriptions(address, list_name=None):
    sub_name, sub_addr = parseaddr(address)

    if list_name:
        mlist = find_list(list_name)
    else:
        mlist = None

    if mlist:
        subs = Subscription.objects.filter(
            subscriber_address=sub_addr, mailing_list = mlist
        ).exclude(
            enabled=False)
    else:
        subs = Subscription.objects.filter(
            subscriber_address=sub_addr
        ).exclude(
            enabled=False)

    return subs


def post_message(relay, message, list_name, host):
    mlist = find_list(list_name)
    assert mlist, "User is somehow able to post to list %s" % list_name

    for sub in mlist.subscription_set.all().values('subscriber_address'):
        list_addr = "%s@%s" % (list_name, host)
        delivery = craft_response(message, list_name, list_addr) 
        relay.deliver(delivery, To=sub['subscriber_address'], From=list_addr)


def craft_response(message, list_name, list_addr):
    response = MailResponse(To=list_addr, 
                            From=message['from'],
                            Subject=message['subject'])

    msg_id = message['message-id']

    response.update({
        "Sender": list_addr, 
        "Reply-To": list_addr,
        "List-Id": list_addr,
        "List-Unsubscribe": "<mailto:%s-unsubscribe@librelist.com>" % list_name,
        "List-Archive": "<http://librelist.com/archives/%s/>" % list_name,
        "List-Post": "<mailto:%s>" % list_addr,
        "List-Help": "<http://librelist.com/help.html>",
        "List-Subscribe": "<mailto:%s-subscribe@librelist.com>" % list_name,
        "Return-Path": list_addr, 
        "Precedence": 'list',
    })

    if 'date' in message:
        response['Date'] = message['date']

    if 'references' in message:
        response['References'] = message['References']
    elif msg_id:
        response['References'] = msg_id

    if msg_id:
        response['message-id'] = msg_id

        if 'in-reply-to' not in message:
            response["In-Reply-To"] = message['Message-Id']

    if message.all_parts():
        response.attach_all_parts(message)
    else:
        response.Body = message.body()

    return response

def disable_all_subscriptions(address):
    Subscription.objects.filter(subscriber_address=address).update(enabled=False)

def enable_all_subscriptions(address):
    Subscription.objects.filter(subscriber_address=address).update(enabled=True)

def similar_named_lists(list_name):
    sim_pri, sim_sec = stem_and_meta(list_name)
    sim_sec = sim_sec or sim_pri

    return MailingList.objects.filter(Q(similarity_pri = sim_pri) | 
                                       Q(similarity_sec =
                                         sim_sec))


########NEW FILE########
__FILENAME__ = state_storage
from lamson.routing import StateStorage, ROUTE_FIRST_STATE
from webapp.librelist.models import UserState

class UserStateStorage(StateStorage):

    def clear(self):
        for state in UserState.objects.all():
            state.delete()

    def _find_state(self, key, sender):
        states = UserState.objects.filter(state_key = key,
                                          from_address = sender)
        if states:
            return states[0]
        else:
            return None

    def get(self, key, sender):
        stored_state = self._find_state(key, sender)
        if stored_state:
            return stored_state.state
        else:
            return ROUTE_FIRST_STATE

    def key(self, key, sender):
        raise Exception("THIS METHOD MEANS NOTHING TO DJANGO!")

    def set(self, key, sender, to_state):
        stored_state = self._find_state(key, sender)

        if stored_state:
            if to_state == "START":
                # don't store these, they're the default when it doesn't exist
                stored_state.delete()

            stored_state.state = to_state
            stored_state.save()
        else:
            # avoid storing start states
            if to_state != "START":
                stored_state = UserState(state_key = key, from_address = sender,
                                         state=to_state)
                stored_state.save()

    def set_all(self, sender, to_state):
        """
        This isn't part of normal lamson code, it's used to 
        control the states for all of the app.handlers.admin
        lists during a bounce.
        """
        stored_states = UserState.objects.filter(from_address = sender)

        for stored in stored_states:
            stored.state = to_state
            stored.save()



########NEW FILE########
__FILENAME__ = boot
from config import settings
from lamson.routing import Router
from lamson.server import Relay, SMTPReceiver
from lamson import view
import logging
import logging.config
import jinja2
from app.model import state_storage

logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=1)

# where to listen for incoming messages
settings.receiver = SMTPReceiver(settings.receiver_config['host'],
                                 settings.receiver_config['port'])

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True
Router.LOG_EXCEPTIONS=True
Router.STATE_STORE=state_storage.UserStateStorage()

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))


########NEW FILE########
__FILENAME__ = settings
# This file contains python variables that configure Lamson for email processing.
import logging
import os
from lamson import confirm, encoding


encoding.VALUE_IS_EMAIL_ADDRESS = lambda v: '@' in v or '-AT-' in v


os.environ['DJANGO_SETTINGS_MODULE'] = 'webapp.settings'

relay_config = {'host': 'localhost', 'port': 8825}

receiver_config = {'host': 'localhost', 'port': 8823}

handlers = ['app.handlers.bounce', 'app.handlers.admin']

router_defaults = {
    'host': 'librelist\\.com',
    'list_name': '[a-zA-Z0-9\.]+',
    'id_number': '[a-z0-9]+',
}

template_config = {'dir': 'app', 'module': 'templates'}

# the config/boot.py will turn these values into variables set in settings

PENDING_QUEUE = "run/pending"
ARCHIVE_BASE = "app/data/archive"
BOUNCE_ARCHIVE = "run/bounces"

SPAM = {'db': 'run/spamdb', 'rc': 'run/spamrc', 'queue': 'run/spam'}

from app.model.confirmation import DjangoConfirmStorage
CONFIRM = confirm.ConfirmationEngine('run/pending', DjangoConfirmStorage())


########NEW FILE########
__FILENAME__ = testing
from config import settings
from lamson import view
from lamson.routing import Router
from lamson.server import Relay
import jinja2
import logging
import logging.config
import os
from app.model import state_storage

logging.config.fileConfig("config/test_logging.conf")

# the relay host to actually send the final message to (set debug=1 to see what
# the relay is saying to the log server).
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=0)


settings.receiver = None

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True
Router.LOG_EXCEPTIONS=False
Router.STATE_STORE=state_storage.UserStateStorage()


view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))

# if you have pyenchant and enchant installed then the template tests will do
# spell checking for you, but you need to tell pyenchant where to find itself
# if 'PYENCHANT_LIBRARY_PATH' not in os.environ:
#     os.environ['PYENCHANT_LIBRARY_PATH'] = '/opt/local/lib/libenchant.dylib'


########NEW FILE########
__FILENAME__ = json_convert
import sys
sys.path.append(".")

from lamson.mail import MailRequest, MailResponse
from lamson.queue import Queue
import config.testing
from app.model import archive
import os


def convert_queue(arg, dirname, names):
    if dirname.endswith("new"):
        print dirname, names

        jpath = dirname + "/../../json"
        if not os.path.exists(jpath):
            os.mkdir(jpath)

        for key in names:
            json_file = key + ".json"
            json_archive = os.path.join(jpath, json_file)

            fpath = os.path.join(dirname, key)
            msg = MailRequest('librelist.com', None, None, open(fpath).read())
            f = open(json_archive, "w")
            f.write(archive.to_json(msg.base))
            f.close()

os.path.walk("app/data/archives", convert_queue, None)


########NEW FILE########
__FILENAME__ = metaphone
#!python
#coding= latin-1
# This script implements the Double Metaphone algorythm (c) 1998, 1999 by Lawrence Philips
# it was translated to Python from the C source written by Kevin Atkinson (http://aspell.net/metaphone/)
# By Andrew Collins - January 12, 2007 who claims no rights to this work
# http://atomboy.isa-geek.com:8080/plone/Members/acoil/programing/double-metaphone
# Tested with Pyhon 2.4.3
# Updated Feb 14, 2007 - Found a typo in the 'gh' section
# Updated Dec 17, 2007 - Bugs fixed in 'S', 'Z', and 'J' sections. Thanks Chris Leong!
def dm(st) :
	"""dm(string) -> (string, string or None)
	returns the double metaphone codes for given string - always a tuple
	there are no checks done on the input string, but it should be a single	word or name."""
	vowels = ['A', 'E', 'I', 'O', 'U', 'Y']
	st = st.decode('ascii', 'ignore')
	st = st.upper() # st is short for string. I usually prefer descriptive over short, but this var is used a lot!
	is_slavo_germanic = (st.find('W') > -1 or st.find('K') > -1 or st.find('CZ') > -1 or st.find('WITZ') > -1)
	length = len(st)
	first = 2
	st = '-' * first + st + '------'  # so we can index beyond the begining and end of the input string
	last = first + length -1
	pos = first # pos is short for position
	pri = sec = '' # primary and secondary metaphone codes
	#skip these silent letters when at start of word
	if st[first:first+2] in ["GN", "KN", "PN", "WR", "PS"] :
		pos += 1
	# Initial 'X' is pronounced 'Z' e.g. 'Xavier'
	if st[first] == 'X' :
		pri = sec = 'S' #'Z' maps to 'S'
		pos += 1
	# main loop through chars in st
	while pos <= last :
		#print str(pos) + '\t' + st[pos]
		ch = st[pos] # ch is short for character
		# nxt (short for next characters in metaphone code) is set to  a tuple of the next characters in
		# the primary and secondary codes and how many characters to move forward in the string.
		# the secondary code letter is given only when it is different than the primary.
		# This is just a trick to make the code easier to write and read.
		nxt = (None, 1) # default action is to add nothing and move to next char
		if ch in vowels :
			nxt = (None, 1)
			if pos == first : # all init vowels now map to 'A'
				nxt = ('A', 1)
		elif ch == 'B' :
			#"-mb", e.g", "dumb", already skipped over... see 'M' below
			if st[pos+1] == 'B' :
				nxt = ('P', 2)
			else :
				nxt = ('P', 1)
		elif ch == 'C' :
			# various germanic
			if (pos > first and st[pos-2] in vowels and st[pos-1:pos+1] == 'ACH' and \
			   (st[pos+2] not in ['I', 'E'] or st[pos-2:pos+4] in ['BACHER', 'MACHER'])) :
				nxt = ('K', 2)
			# special case 'CAESAR'
			elif pos == first and st[first:first+6] == 'CAESAR' :
				nxt = ('S', 2)
			elif st[pos:pos+4] == 'CHIA' : #italian 'chianti'
				nxt = ('K', 2)
			elif st[pos:pos+2] == 'CH' :
				# find 'michael'
				if pos > first and st[pos:pos+4] == 'CHAE' :
					nxt = ('K', 'X', 2)
				elif pos == first and (st[pos+1:pos+6] in ['HARAC', 'HARIS'] or \
				   st[pos+1:pos+4] in ["HOR", "HYM", "HIA", "HEM"]) and st[first:first+5] != 'CHORE' :
					nxt = ('K', 2)
				#germanic, greek, or otherwise 'ch' for 'kh' sound
				elif st[first:first+4] in ['VAN ', 'VON '] or st[first:first+3] == 'SCH' \
				   or st[pos-2:pos+4] in ["ORCHES", "ARCHIT", "ORCHID"] \
				   or st[pos+2] in ['T', 'S'] \
				   or ((st[pos-1] in ["A", "O", "U", "E"] or pos == first) \
				   and st[pos+2] in ["L", "R", "N", "M", "B", "H", "F", "V", "W"]) :
					nxt = ('K', 1)
				else :
					if pos == first :
						if st[first:first+2] == 'MC' :
							nxt = ('K', 2)
						else :
							nxt = ('X', 'K', 2)
					else :
						nxt = ('X', 2)
			#e.g, 'czerny'
			elif st[pos:pos+2] == 'CZ' and st[pos-2:pos+2] != 'WICZ' :
				nxt = ('S', 'X', 2)
			#e.g., 'focaccia'
			elif st[pos+1:pos+4] == 'CIA' :
				nxt = ('X', 3)
			#double 'C', but not if e.g. 'McClellan'
			elif st[pos:pos+2] == 'CC' and not (pos == (first +1) and st[first] == 'M') :
				#'bellocchio' but not 'bacchus'
				if st[pos+2] in ["I", "E", "H"] and st[pos+2:pos+4] != 'HU' :
					#'accident', 'accede' 'succeed'
					if (pos == (first +1) and st[first] == 'A') or \
					   st[pos-1:pos+4] in ['UCCEE', 'UCCES'] :
						nxt = ('KS', 3)
					#'bacci', 'bertucci', other italian
					else:
						nxt = ('X', 3)
				else :
					nxt = ('K', 2)
			elif st[pos:pos+2] in ["CK", "CG", "CQ"] :
				nxt = ('K', 'K', 2)
			elif st[pos:pos+2] in ["CI", "CE", "CY"] :
				#italian vs. english
				if st[pos:pos+3] in ["CIO", "CIE", "CIA"] :
					nxt = ('S', 'X', 2)
				else :
					nxt = ('S', 2)
			else : 
				#name sent in 'mac caffrey', 'mac gregor
				if st[pos+1:pos+3] in [" C", " Q", " G"] :
					nxt = ('K', 3)
				else :
					if st[pos+1] in ["C", "K", "Q"] and st[pos+1:pos+3] not in ["CE", "CI"] :
						nxt = ('K', 2)
					else : # default for 'C'
						nxt = ('K', 1)
		elif ch == u'Ç' : # will never get here with st.encode('ascii', 'replace') above
			nxt = ('S', 1)
		elif ch == 'D' :
			if st[pos:pos+2] == 'DG' :
				if st[pos+2] in ['I', 'E', 'Y'] : #e.g. 'edge'
					nxt = ('J', 3)
				else :
					nxt = ('TK', 2)
			elif st[pos:pos+2] in ['DT', 'DD'] :
				nxt = ('T', 2)
			else :
				nxt = ('T', 1)
		elif ch == 'F' :
			if st[pos+1] == 'F' :
				nxt = ('F', 2)
			else :
				nxt = ('F', 1)
		elif ch == 'G' :
			if st[pos+1] == 'H' :
				if pos > first and st[pos-1] not in vowels :
					nxt = ('K', 2)
				elif pos < (first + 3) :
					if pos == first : #'ghislane', ghiradelli
						if st[pos+2] == 'I' :
							nxt = ('J', 2)
						else :
							nxt = ('K', 2)
				#Parker's rule (with some further refinements) - e.g., 'hugh'
				elif (pos > (first + 1) and st[pos-2] in ['B', 'H', 'D'] ) \
				   or (pos > (first + 2) and st[pos-3] in ['B', 'H', 'D'] ) \
				   or (pos > (first + 3) and st[pos-3] in ['B', 'H'] ) :
					nxt = (None, 2)
				else : 
					# e.g., 'laugh', 'McLaughlin', 'cough', 'gough', 'rough', 'tough'
					if pos > (first + 2) and st[pos-1] == 'U' \
					   and st[pos-3] in ["C", "G", "L", "R", "T"] :
						nxt = ('F', 2)
					else :
						if pos > first and st[pos-1] != 'I' :
							nxt = ('K', 2)
			elif st[pos+1] == 'N' :
				if pos == (first +1) and st[first] in vowels and not is_slavo_germanic :
					nxt = ('KN', 'N', 2)
				else :
					# not e.g. 'cagney'
					if st[pos+2:pos+4] != 'EY' and st[pos+1] != 'Y' and not is_slavo_germanic :
						nxt = ('N', 'KN', 2)
					else :
						nxt = ('KN', 2)
			# 'tagliaro'
			elif st[pos+1:pos+3] == 'LI' and not is_slavo_germanic :
				nxt = ('KL', 'L', 2)
			# -ges-,-gep-,-gel-, -gie- at beginning
			elif pos == first and (st[pos+1] == 'Y' \
			   or st[pos+1:pos+3] in ["ES", "EP", "EB", "EL", "EY", "IB", "IL", "IN", "IE", "EI", "ER"]) :
				nxt = ('K', 'J', 2)
			# -ger-,  -gy-
			elif (st[pos+1:pos+2] == 'ER' or st[pos+1] == 'Y') \
			   and st[first:first+6] not in ["DANGER", "RANGER", "MANGER"] \
			   and st[pos-1] not in ['E', 'I'] and st[pos-1:pos+2] not in ['RGY', 'OGY'] :
				nxt = ('K', 'J', 2)
			# italian e.g, 'biaggi'
			elif st[pos+1] in ['E', 'I', 'Y'] or st[pos-1:pos+3] in ["AGGI", "OGGI"] :
				# obvious germanic
				if st[first:first+4] in ['VON ', 'VAN '] or st[first:first+3] == 'SCH' \
				   or st[pos+1:pos+3] == 'ET' :
					nxt = ('K', 2)
				else :
					# always soft if french ending
					if st[pos+1:pos+5] == 'IER ' :
						nxt = ('J', 2)
					else :
						nxt = ('J', 'K', 2)
			elif st[pos+1] == 'G' :
				nxt = ('K', 2)
			else :
				nxt = ('K', 1)
		elif ch == 'H' :
			# only keep if first & before vowel or btw. 2 vowels
			if (pos == first or st[pos-1] in vowels) and st[pos+1] in vowels :
				nxt = ('H', 2)
			else : # (also takes care of 'HH')
				nxt = (None, 1)
		elif ch == 'J' :
			# obvious spanish, 'jose', 'san jacinto'
			if st[pos:pos+4] == 'JOSE' or st[first:first+4] == 'SAN ' :
				if (pos == first and st[pos+4] == ' ') or st[first:first+4] == 'SAN ' :
					nxt = ('H',)
				else :
					nxt = ('J', 'H')
			elif pos == first and st[pos:pos+4] != 'JOSE' :
				nxt = ('J', 'A') # Yankelovich/Jankelowicz
			else :
				# spanish pron. of e.g. 'bajador'
				if st[pos-1] in vowels and not is_slavo_germanic \
				   and st[pos+1] in ['A', 'O'] :
					nxt = ('J', 'H')
				else :
					if pos == last :
						nxt = ('J', ' ')
					else :
						if st[pos+1] not in ["L", "T", "K", "S", "N", "M", "B", "Z"] \
						   and st[pos-1] not in ["S", "K", "L"] :
							nxt = ('J',)
						else :
							nxt = (None, )
			if st[pos+1] == 'J' :
				nxt = nxt + (2,)
			else :
				nxt = nxt + (1,)
		elif ch == 'K' :
			if st[pos+1] == 'K' :
				nxt = ('K', 2)
			else :
				nxt = ('K', 1)
		elif ch == 'L' :
			if st[pos+1] == 'L' :
				# spanish e.g. 'cabrillo', 'gallegos'
				if (pos == (last - 2) and st[pos-1:pos+3] in ["ILLO", "ILLA", "ALLE"]) \
				   or (st[last-1:last+1] in ["AS", "OS"] or st[last] in ["A", "O"] \
				   and st[pos-1:pos+3] == 'ALLE') :
					nxt = ('L', ' ', 2)
				else :
					nxt = ('L', 2)
			else :
				nxt = ('L', 1)
		elif ch == 'M' :
			if st[pos+1:pos+4] == 'UMB' \
			   and (pos + 1 == last or st[pos+2:pos+4] == 'ER') \
			   or st[pos+1] == 'M' :
				nxt = ('M', 2)
			else :
				nxt = ('M', 1)
		elif ch == 'N' :
			if st[pos+1] == 'N' :
				nxt = ('N', 2)
			else :
				nxt = ('N', 1)
		elif ch == u'Ñ' :
			nxt = ('N', 1)
		elif ch == 'P' :
			if st[pos+1] == 'H' :
				nxt = ('F', 2)
			elif st[pos+1] in ['P', 'B'] : # also account for "campbell", "raspberry"
				nxt = ('P', 2)
			else :
				nxt = ('P', 1)
		elif ch == 'Q' :
			if st[pos+1] == 'Q' :
				nxt = ('K', 2)
			else :
				nxt = ('K', 1)
		elif ch == 'R' :
			# french e.g. 'rogier', but exclude 'hochmeier'
			if pos == last and not is_slavo_germanic \
			   and st[pos-2:pos] == 'IE' and st[pos-4:pos-2] not in ['ME', 'MA'] :
				nxt = ('', 'R')
			else :
				nxt = ('R',)
			if st[pos+1] == 'R' :
				nxt = nxt + (2,)
			else :
				nxt = nxt + (1,)
		elif ch == 'S' :
			# special cases 'island', 'isle', 'carlisle', 'carlysle'
			if st[pos-1:pos+2] in ['ISL', 'YSL'] :
				nxt = (None, 1)
			# special case 'sugar-'
			elif pos == first and st[first:first+5] == 'SUGAR' :
				nxt =('X', 'S', 1)
			elif st[pos:pos+2] == 'SH' :
				# germanic
				if st[pos+1:pos+5] in ["HEIM", "HOEK", "HOLM", "HOLZ"] :
					nxt = ('S', 2)
				else :
					nxt = ('X', 2)
			# italian & armenian
			elif st[pos:pos+3] in ["SIO", "SIA"] or st[pos:pos+4] == 'SIAN' :
				if not is_slavo_germanic :
					nxt = ('S', 'X', 3)
				else :
					nxt = ('S', 3)
			# german & anglicisations, e.g. 'smith' match 'schmidt', 'snider' match 'schneider'
			# also, -sz- in slavic language altho in hungarian it is pronounced 's'
			elif (pos == first and st[pos+1] in ["M", "N", "L", "W"]) or st[pos+1] == 'Z' :
				nxt = ('S', 'X')
				if st[pos+1] == 'Z' :
					nxt = nxt + (2,)
				else :
					nxt = nxt + (1,)
			elif st[pos+2:pos+4] == 'SC' :
				# Schlesinger's rule
				if st[pos+2] == 'H' :
					# dutch origin, e.g. 'school', 'schooner'
					if st[pos+3:pos+5] in ["OO", "ER", "EN", "UY", "ED", "EM"] :
						# 'schermerhorn', 'schenker'
						if st[pos+3:pos+5] in ['ER', 'EN'] :
							nxt = ('X', 'SK', 3)
						else :
							nxt = ('SK', 3)
					else :
						if pos == first and st[first+3] not in vowels and st[first+3] != 'W' :
							nxt = ('X', 'S', 3)
						else :
							nxt = ('X', 3)
				elif st[pos+2] in ['I', 'E', 'Y'] :
					nxt = ('S', 3)
				else :
					nxt = ('SK', 3)
			# french e.g. 'resnais', 'artois'
			elif pos == last and st[pos-2:pos] in ['AI', 'OI'] :
				nxt = ('', 'S', 1)
			else :
				nxt = ('S',)
				if st[pos+1] in ['S', 'Z'] :
					nxt = nxt + (2,)
				else :
					nxt = nxt + (1,)
		elif ch == 'T' :
			if st[pos:pos+4] == 'TION' :
				nxt = ('X', 3)
			elif st[pos:pos+3] in ['TIA', 'TCH'] :
				nxt = ('X', 3)
			elif st[pos:pos+2] == 'TH' or st[pos:pos+3] == 'TTH' :
				# special case 'thomas', 'thames' or germanic
				if st[pos+2:pos+4] in ['OM', 'AM'] or st[first:first+4] in ['VON ', 'VAN '] \
				   or st[first:first+3] == 'SCH' :
					nxt = ('T', 2)
				else :
					nxt = ('0', 'T', 2)
			elif st[pos+1] in ['T', 'D'] :
				nxt = ('T', 2)
			else :
				nxt = ('T', 1)
		elif ch == 'V' :
			if st[pos+1] == 'V' :
				nxt = ('F', 2)
			else :
				nxt = ('F', 1)
		elif ch == 'W' :
			# can also be in middle of word
			if st[pos:pos+2] == 'WR' :
				nxt = ('R', 2)
			elif pos == first and st[pos+1] in vowels or st[pos:pos+2] == 'WH' :
				# Wasserman should match Vasserman
				if st[pos+1] in vowels :
					nxt = ('A', 'F', 1)
				else :
					nxt = ('A', 1)
			# Arnow should match Arnoff
			elif (pos == last and st[pos-1] in vowels) \
			   or st[pos-1:pos+5] in ["EWSKI", "EWSKY", "OWSKI", "OWSKY"] \
			   or st[first:first+3] == 'SCH' :
				nxt = ('', 'F', 1)
			# polish e.g. 'filipowicz'
			elif st[pos:pos+4] in ["WICZ", "WITZ"] :
				nxt = ('TS', 'FX', 4)
			else : # default is to skip it
				nxt = (None, 1)
		elif ch == 'X' :
			# french e.g. breaux
			nxt = (None,)
			if not(pos == last and (st[pos-3:pos] in ["IAU", "EAU"] \
			   or st[pos-2:pos] in ['AU', 'OU'])):
				nxt = ('KS',)
			if st[pos+1] in ['C', 'X'] :
				nxt = nxt + (2,)
			else :
				nxt = nxt + (1,)
		elif ch == 'Z' :
			# chinese pinyin e.g. 'zhao'
			if st[pos+1] == 'H' :
				nxt = ('J',)
			elif st[pos+1:pos+3] in ["ZO", "ZI", "ZA"] \
			   or (is_slavo_germanic and pos > first and st[pos-1] != 'T') :
				nxt = ('S', 'TS')
			else :
				nxt = ('S',)
			if st[pos+1] == 'Z' :
				nxt = nxt + (2,)
			else :
				nxt = nxt + (1,)
		# ----------------------------------
		# --- end checking letters------
		# ----------------------------------
		#print str(nxt)
		if len(nxt) == 2 :
			if nxt[0] :
				pri += nxt[0]
				sec += nxt[0]
			pos += nxt[1]
		elif len(nxt) == 3 :
			if nxt[0] :
				pri += nxt[0]
			if nxt[1] :
				sec += nxt[1]
			pos += nxt[2]
	if pri == sec :
		return (pri, None)
	else :
		return (pri, sec)

if __name__ == '__main__' :
	names = {'maurice':'MRS','aubrey':'APR','cambrillo':'KMPR','heidi':'HT','katherine':'K0RN,KTRN',\
		     'catherine':'K0RN,KTRN','richard':'RXRT,RKRT','bob':'PP','eric':'ARK','geoff':'JF,KF',\
			 'dave':'TF','ray':'R','steven':'STFN','bryce':'PRS','randy':'RNT','bryan':'PRN',\
			 'brian':'PRN','otto':'AT','auto':'AT', 'maisey':'MS, None', 'zhang':'JNK, None', 'solilijs':'SLLS, None'}
	for name in names.keys() :
		print name + '\t-->\t' + str(dm(name)) + '\t(' +names[name] + ')'

########NEW FILE########
__FILENAME__ = admin_tests
from nose.tools import *
from lamson.testing import *
from config import settings
import time
from app.model import archive, confirmation


queue_path = archive.store_path('test.list', 'queue')
sender = "sender-%s@sender.com" % time.time()
host = "librelist.com"
list_name = "test.list"
list_addr = "test.list@%s" % host
client = RouterConversation(sender, 'Admin Tests')

def setup():
    clear_queue("run/posts")
    clear_queue("run/spam")

def test_new_user_subscribes_with_invalid_name():
    client.begin()

    client.say('test-list@%s' % host, "I can't read!", 'noreply')
    client.say('test=list@%s' % host, "I can't read!", 'noreply')
    clear_queue()

    client.say('unbounce@%s' % host, "I have two email addresses!")
    assert not delivered('noreply')
    assert not delivered('unbounce')

    client.say('noreply@%s' % host, "Dumb dumb.")
    assert not delivered('noreply')

def test_new_user_subscribes():
    client.begin()
    msg = client.say(list_addr, "Hey I was wondering how to fix this?",
                     list_name + '-confirm')
    client.say(msg['Reply-To'], 'Confirmed I am.', 'noreply')
    clear_queue()


def test_existing_user_unsubscribes():
    test_new_user_subscribes()
    msg = client.say(list_name + "-unsubscribe@%s" % host, "I would like to unsubscribe.", 'confirm')
    client.say(msg['Reply-To'], 'Confirmed yes I want out.', 'noreply')

def test_existing_user_posts_message():
    test_new_user_subscribes()
    msg = client.say(list_addr, "Howdy folks, I was wondering what this is?",
                     list_addr)
    # make sure it gets archived
    assert delivered(list_addr, to_queue=queue(queue_path))



########NEW FILE########
__FILENAME__ = bounce_tests
from nose.tools import *
from lamson.testing import *
from lamson.mail import MailRequest
from lamson.routing import Router
from app.handlers.admin import module_and_to
from app.model import mailinglist
from handlers import admin_tests
from email.utils import parseaddr
from lamson import bounce
from config import settings

sender = admin_tests.sender
list_addr = admin_tests.list_addr
client = admin_tests.client

def setup():
    clear_queue(queue_dir=settings.BOUNCE_ARCHIVE)

def create_bounce(To, From):
    msg = MailRequest("fakepeer", From, To, open("tests/bounce.msg").read())
    assert msg.is_bounce()

    msg.bounce.final_recipient = From
    msg.bounce.headers['Final-Recipient'] = From
    msg.bounce.original['from'] = From
    msg.bounce.original['to'] = To
    msg.bounce.original.To = set([To])
    msg.bounce.original.From = From

    return msg


def test_hard_bounce_disables_user():
    # get them into a posting state
    admin_tests.test_existing_user_posts_message()
    assert_in_state('app.handlers.admin', list_addr, sender, 'POSTING')
    clear_queue()
    assert mailinglist.find_subscriptions(sender, list_addr)

    # force them to HARD bounce
    msg = create_bounce(list_addr, sender)

    Router.deliver(msg)
    assert_in_state('app.handlers.admin', list_addr, sender, 'BOUNCING')
    assert_in_state('app.handlers.bounce', list_addr, sender, 'BOUNCING')
    assert not delivered('unbounce'), "A HARD bounce should be silent."
    assert_equal(len(queue(queue_dir=settings.BOUNCE_ARCHIVE).keys()), 1)
    assert not mailinglist.find_subscriptions(sender, list_addr)

    # make sure that any attempts to post return a "you're bouncing dude" message
    unbounce = client.say(list_addr, 'So anyway as I was saying.', 'unbounce')
    assert_in_state('app.handlers.admin', list_addr, sender, 'BOUNCING')
   
    # now have them try to unbounce
    msg = client.say(unbounce['from'], "Please put me back on, I'll be good.",
                     'unbounce-confirm')

    # handle the bounce confirmation
    client.say(msg['from'], "Confirmed to unbounce.", 'noreply')

    # alright they should be in the unbounce state for the global bounce handler
    assert_in_state('app.handlers.bounce', list_addr, sender,
                    'UNBOUNCED')

    # and they need to be back to POSTING for regular operations 
    assert_in_state('app.handlers.admin', list_addr, sender, 'POSTING')
    assert mailinglist.find_subscriptions(sender, list_addr)

    # and make sure that only the original bounce is in the bounce archive
    assert_equal(len(queue(queue_dir=settings.BOUNCE_ARCHIVE).keys()), 1)

def test_soft_bounce_tells_them():
    setup()

    # get them into a posting state
    admin_tests.test_existing_user_posts_message()
    assert_in_state('app.handlers.admin', list_addr, sender, 'POSTING')
    clear_queue()
    assert mailinglist.find_subscriptions(sender, list_addr)

    # force them to soft bounce
    msg = create_bounce(list_addr, sender)
    msg.bounce.primary_status = (3, bounce.PRIMARY_STATUS_CODES[u'3'])
    assert msg.bounce.is_soft()

    Router.deliver(msg)
    assert_in_state('app.handlers.admin', list_addr, sender, 'BOUNCING')
    assert_in_state('app.handlers.bounce', list_addr, sender, 'BOUNCING')
    assert delivered('unbounce'), "Looks like unbounce didn't go out."
    assert_equal(len(queue(queue_dir=settings.BOUNCE_ARCHIVE).keys()), 1)
    assert not mailinglist.find_subscriptions(sender, list_addr)

    # make sure that any attempts to post return a "you're bouncing dude" message
    unbounce = client.say(list_addr, 'So anyway as I was saying.', 'unbounce')
    assert_in_state('app.handlers.admin', list_addr, sender, 'BOUNCING')

    # now have them try to unbounce
    msg = client.say(unbounce['from'], "Please put me back on, I'll be good.",
                     'unbounce-confirm')

    # handle the bounce confirmation
    client.say(msg['from'], "Confirmed to unbounce.", 'noreply')

    # alright they should be in the unbounce state for the global bounce handler
    assert_in_state('app.handlers.bounce', list_addr, sender,
                    'UNBOUNCED')

    # and they need to be back to POSTING for regular operations 
    assert_in_state('app.handlers.admin', list_addr, sender, 'POSTING')
    assert mailinglist.find_subscriptions(sender, list_addr)

    # and make sure that only the original bounce is in the bounce archive
    assert_equal(len(queue(queue_dir=settings.BOUNCE_ARCHIVE).keys()), 1)



########NEW FILE########
__FILENAME__ = archive_tests
from nose.tools import *
from lamson.testing import *
from lamson.mail import MailRequest, MailResponse
from app.model import archive, mailinglist
import simplejson as json
import shutil

queue_path = archive.store_path('test.list', 'queue')
json_path = archive.store_path('test.list', 'json')

def setup():
    clear_queue(queue_path)
    shutil.rmtree(json_path)

def teardown():
    clear_queue(queue_path)
    shutil.rmtree(json_path)

def test_archive_enqueue():
    msg = MailResponse(From=u'"p\xf6stal Zed" <zedshaw@zedshaw.com>', 
                       To="test.list@librelist.com",
                       Subject="test message", Body="This is a test.")

    archive.enqueue('test.list', msg)
    archived = delivered('zedshaw', to_queue=queue(queue_path))
    assert archived, "Didn't get archived."
    as_string = str(archived)

    assert '-AT-' in str(archived), "Didn't get obfuscated"
    assert '<' in as_string and '"' in as_string and '>' in as_string, "Unicode email screwed up."



def test_white_list_cleanse():
    msg = MailRequest('fakepeer', None, None, open('tests/lots_of_headers.msg').read())
    resp = mailinglist.craft_response(msg, 'test.list', 'test.list@librelist.com')

    archive.white_list_cleanse(resp)
    
    for key in resp.keys():
        assert key in archive.ALLOWED_HEADERS

    assert '@' not in resp['from']
    assert str(resp)

def test_to_json():
    msg = MailRequest('fakeperr', None, None, open("tests/bounce.msg").read())

    resp = mailinglist.craft_response(msg, 'test.list', 'test.list@librelist.com')
    # attach an the message back but fake it as an image it'll be garbage
    resp.attach(filename="tests/bounce.msg", content_type="image/png", disposition="attachment")
    resp.to_message()  # prime the pump

    js = archive.to_json(resp.base)
    assert js

    rtjs = json.loads(js)
    assert rtjs
    assert rtjs['parts'][-1]['encoding']['format'] == 'base64'

########NEW FILE########
__FILENAME__ = bounce_tests
from nose.tools import *
from lamson.testing import *
from lamson.mail import MailRequest
from app.model import bounce


def test_mail_to_you_is_bouncing():
    msg = MailRequest("fakepeer", None, None, open("tests/bounce.msg").read())
    assert msg.is_bounce()

    bounce_rep = bounce.mail_to_you_is_bouncing(msg)
    assert bounce_rep
    assert_equal(bounce_rep['to'], msg.bounce.final_recipient)


########NEW FILE########
__FILENAME__ = confirmation_tests
from nose.tools import *
from lamson.testing import *
from lamson.mail import MailRequest, MailResponse
from app.model.confirmation import DjangoConfirmStorage
from mock import patch

user = "test_user@localhost"
list_name = "test_list_name"



def test_DjangoConfirmStorage():
    storage = DjangoConfirmStorage()
    storage.clear()

    storage.store(list_name, user, '123456', 'abcdefg')

    secret, pending_id = storage.get(list_name, user)
    assert_equal(secret, '123456')
    assert_equal(pending_id, 'abcdefg')

    storage.delete(list_name, user)

    secret, pending = storage.get(list_name, user)
    assert not secret
    assert not pending



########NEW FILE########
__FILENAME__ = mailinglist_tests
from nose.tools import *
from app.model.mailinglist import *
from email.utils import parseaddr
from webapp.librelist.models import MailingList, Subscription
from lamson.mail import MailRequest, MailResponse
from lamson.testing import *

user_full_address = '"Zed A. Shaw" <zedshaw@zedshaw.com>'
user_name, user_address = parseaddr(user_full_address)
list_name = "test.lists"


def setup():
    MailingList.objects.all().delete()
    Subscription.objects.all().delete()


def test_create_list():
    mlist = create_list(list_name)
    assert mlist
    mlist_found = find_list(list_name)
    assert mlist_found
    assert_equal(mlist.name, mlist_found.name)

    # make sure create doesn't do it more than once
    create_list(list_name)
    assert_equal(MailingList.objects.filter(name = list_name).count(), 1)
    delete_list(list_name)


def test_delete_list():
    delete_list(list_name)
    mlist = find_list(list_name)
    assert not mlist, "Found list: %s, should not." % mlist


def test_remove_all_subscriptions():
    test_add_subscriber()

    remove_all_subscriptions(user_full_address)
    subs = find_subscriptions(user_full_address)
    assert_equal(len(subs), 0)


def test_add_subscriber():
    remove_all_subscriptions(user_full_address)
    sub = add_subscriber(user_full_address, list_name)
    assert sub
    assert_equal(sub.subscriber_address, user_address)
    assert_equal(sub.subscriber_name, user_name)

    subs = find_subscriptions(user_full_address)
    assert_equal(len(subs), 1)


def test_remove_subscriber():
    test_add_subscriber()
    remove_subscriber(user_full_address, list_name)
    subs = find_subscriptions(user_full_address, list_name=list_name)
    assert_equal(len(subs), 0)


def test_post_message():
    for i in range(0,3):
        add_subscriber(user_full_address, list_name)

    sample = MailResponse(To=list_name + "@librelist.com",
                          From=user_full_address,
                          Subject="Test post message.",
                          Body="I am telling you guys you are wrong.")

    sample['Message-Id'] = '12313123123123123'

    msg = MailRequest("fakepeer", sample['from'], sample['to'], str(sample))
    post_message(relay(port=8825), msg, list_name, "librelist.com")


def test_disable_enable_all_subscriptions():
    test_add_subscriber()
    disable_all_subscriptions(user_address)
    assert not find_subscriptions(user_address)

    enable_all_subscriptions(user_address)
    assert find_subscriptions(user_address)

def test_similarily_named_lists():
    test_names = ['test.lists', 'tests.list', 'querylists', 'evil.named',
                 'shouldnot', 'teller.list']
    for name in test_names:
        create_list(name)

    similar = similar_named_lists(list_name)
    assert_equal(len(similar), 2)

    nothing = similar_named_lists("zed.shaw")
    assert not nothing

    similar = similar_named_lists('teler.list')
    assert_equal(len(similar), 1)


def test_craft_response_attachment():
    sample = MailResponse(To=list_name + "@librelist.com",
                          From=user_full_address,
                          Subject="Test message with attachments.",
                          Body="The body as one attachment.")

    sample.attach(filename="tests/model/mailinglist_tests.py",
                  content_type="text/plain",
                  disposition="attachment")

    sample['message-id'] = '123545666'

    im = sample.to_message()
    assert_equal(len([x for x in im.walk()]), 3)
    
    inmsg = MailRequest("fakepeer", None, None, str(sample))
    assert_equal(len(inmsg.all_parts()), 2)

    outmsg = craft_response(inmsg, list_name, list_name +
                                        "@librelist.com")
  
    om = outmsg.to_message()

    assert_equal(len([x for x in om.walk()]),
                 len([x for x in im.walk()]))

    assert 'message-id' in outmsg


def test_craft_response_no_attachment():
    sample = MailResponse(To=list_name + "@librelist.com",
                          From=user_full_address,
                          Subject="Test message with attachments.",
                          Body="The body as one attachment.")

    im = sample.to_message()
    assert_equal(len([x for x in im.walk()]), 1)
    assert_equal(im.get_payload(), sample.Body)
    
    inmsg = MailRequest("fakepeer", None, None, str(sample))
    assert_equal(len(inmsg.all_parts()), 0)
    assert_equal(inmsg.body(), sample.Body)

    outmsg = craft_response(inmsg, list_name, list_name +
                                        "@librelist.com")
  
    om = outmsg.to_message()
    assert_equal(om.get_payload(), sample.Body)

    assert_equal(len([x for x in om.walk()]),
                 len([x for x in im.walk()]))



########NEW FILE########
__FILENAME__ = state_storage_tests
from nose.tools import *
from app.model.state_storage import UserStateStorage
from webapp.librelist.models import UserState
from lamson.routing import ROUTE_FIRST_STATE


def setup():
    for state in UserState.objects.all():
        state.delete()

def test_clear():
    ss = UserStateStorage()
    ss.clear()
    assert_equal(len(UserState.objects.all()), 0)


def test_set():
    ss = UserStateStorage()
    # start states should not be stored
    ss.set("app.handlers.admin", "zedshaw@zedshaw.com", "START")
    assert_equal(len(UserState.objects.all()), 0)

    ss.set("app.handlers.admin", "zedshaw@zedshaw.com", "POSTING")
    assert_equal(len(UserState.objects.all()), 1)
    
    ss.clear()

def test_get():
    ss = UserStateStorage()
    ss.clear()
    state = ss.get("app.handlers.admin", "zedshaw@zedshaw.com")
    assert_equal(state, ROUTE_FIRST_STATE)

    ss.set("app.handlers.admin", "zedshaw@zedshaw.com", "POSTING")
    state = ss.get("app.handlers.admin", "zedshaw@zedshaw.com")
    assert_equal(state, "POSTING")

########NEW FILE########
__FILENAME__ = admin
from webapp.librelist.models import *
from django.contrib import admin


for m in [Confirmation, UserState, MailingList, Subscription]:
    admin.site.register(m)


########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from webapp.librelist.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Subscription'
        db.create_table('librelist_subscription', (
            ('subscriber_name', models.CharField(max_length=200)),
            ('enabled', models.BooleanField(default=True)),
            ('created_on', models.DateTimeField(auto_now_add=True)),
            ('subscriber_address', models.EmailField()),
            ('id', models.AutoField(primary_key=True)),
            ('mailing_list', models.ForeignKey(orm.MailingList)),
        ))
        db.send_create_signal('librelist', ['Subscription'])
        
        # Adding model 'UserState'
        db.create_table('librelist_userstate', (
            ('created_on', models.DateTimeField(auto_now_add=True)),
            ('state', models.CharField(max_length=200)),
            ('id', models.AutoField(primary_key=True)),
            ('state_key', models.CharField(max_length=512)),
            ('from_address', models.EmailField()),
        ))
        db.send_create_signal('librelist', ['UserState'])
        
        # Adding model 'Confirmation'
        db.create_table('librelist_confirmation', (
            ('from_address', models.EmailField()),
            ('request_date', models.DateTimeField(auto_now_add=True)),
            ('expected_secret', models.CharField(max_length=50)),
            ('pending_message_id', models.CharField(max_length=200)),
            ('list_name', models.CharField(max_length=200)),
            ('id', models.AutoField(primary_key=True)),
        ))
        db.send_create_signal('librelist', ['Confirmation'])
        
        # Adding model 'MailingList'
        db.create_table('librelist_mailinglist', (
            ('name', models.CharField(max_length=512)),
            ('archive_url', models.CharField(max_length=512)),
            ('similarity_pri', models.CharField(max_length=50)),
            ('archive_queue', models.CharField(max_length=512)),
            ('similarity_sec', models.CharField(max_length=50, null=True)),
            ('created_on', models.DateTimeField(auto_now_add=True)),
            ('id', models.AutoField(primary_key=True)),
        ))
        db.send_create_signal('librelist', ['MailingList'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'Subscription'
        db.delete_table('librelist_subscription')
        
        # Deleting model 'UserState'
        db.delete_table('librelist_userstate')
        
        # Deleting model 'Confirmation'
        db.delete_table('librelist_confirmation')
        
        # Deleting model 'MailingList'
        db.delete_table('librelist_mailinglist')
        
    
    
    models = {
        'librelist.subscription': {
            'created_on': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'enabled': ('models.BooleanField', [], {'default': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'mailing_list': ('models.ForeignKey', ['MailingList'], {}),
            'subscriber_address': ('models.EmailField', [], {}),
            'subscriber_name': ('models.CharField', [], {'max_length': '200'})
        },
        'librelist.userstate': {
            'created_on': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'from_address': ('models.EmailField', [], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'state': ('models.CharField', [], {'max_length': '200'}),
            'state_key': ('models.CharField', [], {'max_length': '512'})
        },
        'librelist.confirmation': {
            'expected_secret': ('models.CharField', [], {'max_length': '50'}),
            'from_address': ('models.EmailField', [], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'list_name': ('models.CharField', [], {'max_length': '200'}),
            'pending_message_id': ('models.CharField', [], {'max_length': '200'}),
            'request_date': ('models.DateTimeField', [], {'auto_now_add': 'True'})
        },
        'librelist.mailinglist': {
            'archive_queue': ('models.CharField', [], {'max_length': '512'}),
            'archive_url': ('models.CharField', [], {'max_length': '512'}),
            'created_on': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'name': ('models.CharField', [], {'max_length': '512'}),
            'similarity_pri': ('models.CharField', [], {'max_length': '50'}),
            'similarity_sec': ('models.CharField', [], {'max_length': '50', 'null': 'True'})
        }
    }
    
    complete_apps = ['librelist']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from datetime import datetime
from email.utils import formataddr

# Create your models here.

class Confirmation(models.Model):
    from_address = models.EmailField()
    request_date = models.DateTimeField(auto_now_add=True)
    expected_secret = models.CharField(max_length=50)
    pending_message_id = models.CharField(max_length=200)
    list_name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.from_address

class UserState(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    state_key = models.CharField(max_length=512)
    from_address = models.EmailField()
    state = models.CharField(max_length=200)

    def __unicode__(self):
        return "%s:%s (%s)" % (self.state_key, self.from_address, self.state)

class MailingList(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    archive_url = models.CharField(max_length=512)
    archive_queue = models.CharField(max_length=512)
    name = models.CharField(max_length=512)
    similarity_pri = models.CharField(max_length=50)
    similarity_sec = models.CharField(max_length=50, null=True)

    def __unicode__(self):
        return self.name


class Subscription(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    subscriber_address = models.EmailField()
    subscriber_name = models.CharField(max_length=200)
    mailing_list = models.ForeignKey(MailingList)
    enabled = models.BooleanField(default=True)

    def __unicode__(self):
        return '"%s" <%s>' % (self.subscriber_name, self.subscriber_address)

    def subscriber_full_address(self):
        return formataddr((self.subscriber_name, self.subscriber_address))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',)


########NEW FILE########
__FILENAME__ = views
# Create your views here.

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
__FILENAME__ = settings
# Django settings for webapp project.
import os


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Zed A. Shaw', 'zedshaw@librelist.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = os.path.dirname(__file__) + '/../run/data.sqlite3'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5#x-^z6gdg$*x&^1f0qjn=jj^*dopzn5-w52qeo13#11#xz&vw'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'webapp.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'webapp.librelist',
    'south',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    (r'^/', include('webapp.librelist.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
__FILENAME__ = anonymizer
from config.settings import relay, BOUNCES, SPAM, CONFIRM
from lamson.routing import route, Router, route_like
from lamson.bounce import bounce_to
from lamson.spam import spam_filter
from lamson import view, queue, confirm
from app.model import filter, addressing
import logging


@route(".+")
def IGNORE_BOUNCE(message):
    bounces = queue.Queue(BOUNCES)
    bounces.push(message)
    return START

@route(".+")
def SPAMMING(message):
    return SPAMMING

@route("start@(host)")
@route("(user_id)@(host)")
@bounce_to(soft=IGNORE_BOUNCE, hard=IGNORE_BOUNCE)
@spam_filter(SPAM['db'], SPAM['rc'], SPAM['queue'], next_state=SPAMMING)
def START(message, user_id=None, host=None):
    if user_id:
        market_anon = addressing.mapping(message['from'], 'marketroid', host)

        reply = filter.cleanse_incoming(message, user_id, host, market_anon)
        relay.deliver(reply)

        return DEMARKETING
    else:
        CONFIRM.send(relay, "start", message, "mail/start_confirm.msg", locals())
        return CONFIRMING


@route("start-confirm-(id_number)@(host)")
def CONFIRMING(message, id_number=None, host=None):
    original = CONFIRM.verify('start', message['from'], id_number)

    if original:
        user_anon = addressing.mapping(message['from'], 'user', host)

        welcome = view.respond(locals(), "mail/welcome.msg", 
                           From=user_anon,
                           To=message['from'],
                           Subject="Welcome to MyInboxIsNotA.TV")
        relay.deliver(welcome)

        return PROTECTING
    else:
        logging.warning("Invalid confirm from %s", message['from'])
        return CONFIRMING


@route("(user_id)@(host)")
def DEMARKETING(message, user_id=None, host=None):
    reply = filter.cleanse_incoming(message, user_id, host)
    relay.deliver(reply)
    return DEMARKETING


@route("(marketroid_id)@(host)")
@route("(user_id)@(host)")
def PROTECTING(message, marketroid_id=None, host=None, user_id=None):
    if user_id:
        logging.warning("Attempted user->user email from %r", message['from'])
        forbid =  view.respond(locals(), "mail/forbid.msg",
                               From="noreply@%(host)s",
                               To=message['from'],
                               Subject="You cannot email another user or yourself.")
        relay.deliver(forbid)
    else:
        reply = filter.route_reply(message, marketroid_id, host)
        relay.deliver(reply)

    return PROTECTING


########NEW FILE########
__FILENAME__ = addressing
from pytyrant import PyTyrant
import uuid
import zlib
from email.utils import parseaddr


def lookup(address, host=None):
    name, addr = parseaddr(address)
    table = PyTyrant.open()
    user = table[addr]
    table.close()

    if host:
        return user + '@' + host
    else:
        return user

def store(address, maps_to):
    name, addr = parseaddr(address)
    table = PyTyrant.open()
    table[addr] = maps_to
    table.close()

def delete(address):
    name, addr = parseaddr(address)
    table = PyTyrant.open()
    del table[addr]
    table.close()

def random_id():
    return "%x" % abs(zlib.adler32(uuid.uuid4().hex))


def mapping(real_address, anon_type, host):
    assert anon_type in ['user', 'marketroid']
    
    anon_id = "%s-%s" % (anon_type, random_id())

    store(anon_id, real_address)
    store(real_address, anon_id)

    return anon_id + '@' + host


def real(user_id):
    return lookup(user_id)


def anon(real, host):
    return lookup(real, host)




########NEW FILE########
__FILENAME__ = filter
from lamson import mail
from app.model import addressing


def craft_response(message, From, To, contact_addr=None):
    response = mail.MailResponse(To=To,
                            From=From,
                            Subject=message['subject'])

    msg_id = message['message-id']

    if contact_addr:
        response.update({
            "Sender": contact_addr, 
            "Reply-To": contact_addr,
            "Return-Path": contact_addr, 
            "Precedence": "list",
        })

    if 'date' in message:
        response['Date'] = message['date']

    if 'references' in message:
        response['References'] = message['References']
    elif msg_id:
        response['References'] = msg_id

    if msg_id:
        response['message-id'] = msg_id

        if 'in-reply-to' not in message:
            response["In-Reply-To"] = message['Message-Id']

    if message.all_parts():
        response.attach_all_parts(message)
    else:
        response.Body = message.body()

    return response


def cleanse_incoming(message, user_id, host, marketroid_rand=None):
    user_real = addressing.real(user_id)

    if not marketroid_rand:
        marketroid_rand = addressing.anon(message['from'], host)

    reply = craft_response(message, message['from'], user_real, marketroid_rand)

    return reply


def route_reply(message, marketroid_id, host):
    marketroid_real = addressing.real(marketroid_id)
    user_anon = addressing.anon(message['from'], host)

    reply = craft_response(message, user_anon, marketroid_real)

    return reply



########NEW FILE########
__FILENAME__ = html
from lxml import etree, sax
from xml.sax.handler import ContentHandler, EntityResolver

# stolen from http://code.activestate.com/recipes/148061/
def wrap(text, width):
    return reduce(lambda line, word, width=width: '%s%s%s' %
                  (line,
                   ' \n'[(len(line)-line.rfind('\n')-1
                         + len(word.split('\n',1)[0]
                              ) >= width)],
                   word),
                  text.split(' ')
                 )


class TextOnlyContentHandler(ContentHandler):
    def __init__(self):
        self.text = []
        self.stack = []
        self.links = []

    def startElementNS(self, name, qname, attributes):
        if qname in ["h1", "h2", "h3"]:
            self.stack.append((qname, ""))
        elif qname == "a":
            href = attributes.getValueByQName("href")
            self.stack.append((qname, href))
        elif qname == "p":
            if self.stack:
                self.text.append(self.stack.pop()[1])
            self.text.append("\n\n")

    def characters(self, text_data):
        if text_data.strip():
            data = " ".join([l.strip() for l in text_data.split("\n")]).strip()

            if self.stack:
                qname, text = self.stack.pop()
                if qname in ["h1","h2","h3"]:
                    self.text.append("\n\n" + data + "\n" + "=" * len(data) + "\n")
                elif qname == "a":
                    if text not in self.links:
                        self.links.append(text)

                    index = self.links.index(text)
                    self.text.append(data + "[%d]" % len(self.links))
                else:
                    self.text.append(text + " " + data)
            else:
                self.text.append(data)


def strip_html(doc):
    tree = etree.fromstring(doc)
    handler = TextOnlyContentHandler()
    sax.saxify(tree, handler)
    links_list = ""
    for i, link in enumerate(handler.links):
        links_list += "\n[%d] %s" % (i+1, link)

    text = " ".join(handler.text)
    return wrap(text, 72) + "\n\n----" + links_list



########NEW FILE########
__FILENAME__ = boot
from config import settings
from lamson.routing import Router
from lamson.server import Relay, SMTPReceiver
from lamson import view
import logging
import logging.config
import jinja2

logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=1)

# where to listen for incoming messages
settings.receiver = SMTPReceiver(settings.receiver_config['host'],
                                 settings.receiver_config['port'])

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True
Router.LOG_EXCEPTIONS=True
Router.UNDELIVERABLE_QUEUE=queue.Queue(settings.UNDELIVERABLES)

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))


########NEW FILE########
__FILENAME__ = settings
# This file contains python variables that configure Lamson for email processing.
import logging
import shelve
from lamson import confirm

relay_config = {'host': 'localhost', 'port': 8825}

receiver_config = {'host': 'localhost', 'port': 8823}

handlers = ['app.handlers.anonymizer']

router_defaults = {
    'host': 'myinboxisnota.tv',
    'user_id': 'user-[a-z0-9]+',
    'marketroid_id': 'marketroid-[a-z0-9]+',
    'id_number': '[a-z0-9]+',
}

template_config = {'dir': 'app', 'module': 'templates'}

SPAM = {'db': 'run/spamdb', 'rc': 'run/spamrc', 'queue': 'run/spam'}

BOUNCES = 'run/bounces'
UNDELIVERABLES = 'run/undeliverables'
CONFIRM_STORAGE=confirm.ConfirmationStorage(db=shelve.open("run/confirmationsdb"))

CONFIRM = confirm.ConfirmationEngine('run/pending', CONFIRM_STORAGE)

########NEW FILE########
__FILENAME__ = testing
from config import settings
from lamson import view
from lamson.routing import Router
from lamson.server import Relay
import jinja2
import logging
import logging.config
import os

logging.config.fileConfig("config/test_logging.conf")

# the relay host to actually send the final message to (set debug=1 to see what
# the relay is saying to the log server).
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=0)


settings.receiver = None

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True
Router.LOG_EXCEPTIONS=False

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))

# if you have pyenchant and enchant installed then the template tests will do
# spell checking for you, but you need to tell pyenchant where to find itself
# if 'PYENCHANT_LIBRARY_PATH' not in os.environ:
#     os.environ['PYENCHANT_LIBRARY_PATH'] = '/opt/local/lib/libenchant.dylib'


########NEW FILE########
__FILENAME__ = json_convert
import sys
sys.path.append(".")

from lamson.mail import MailRequest, MailResponse
from lamson.queue import Queue
import config.testing
from app.model import archive
import os


def convert_queue(arg, dirname, names):
    if dirname.endswith("new"):
        print dirname, names

        jpath = dirname + "/../../json"
        if not os.path.exists(jpath):
            os.mkdir(jpath)

        for key in names:
            json_file = key + ".json"
            json_archive = os.path.join(jpath, json_file)

            fpath = os.path.join(dirname, key)
            msg = MailRequest('librelist.com', None, None, open(fpath).read())
            f = open(json_archive, "w")
            f.write(archive.to_json(msg.base))
            f.close()

os.path.walk("app/data/archives", convert_queue, None)


########NEW FILE########
__FILENAME__ = anonymizer_tests
from nose.tools import *
from lamson.testing import *
from lamson import mail
from config import settings
from app.model import addressing


client = RouterConversation("person@localhost", "Anonymizing Tests")
marketroid = RouterConversation("buymycrap@localhost", "Marketroid Tests")
host = "myinboxisnota.tv"

def setup():
    client.begin()
    marketroid.begin()

def teardown():
    addressing.delete("person@localhost")
    addressing.delete("buymycrap@localhost")


def test_client_subscribes():
    client.begin()
    confirm = client.say("start@%s" % host, "subscribe me", "start-confirm")
    welcome = client.say(confirm['from'], "confirm me", "user")

    return welcome['from']

def test_client_receives_normal_mail():
    marketroid.begin()
    user_id = test_client_subscribes()
    
    to_user = marketroid.say(user_id, "I have a great offer for you!", "marketroid")

    assert to_user['reply-to'] != "buymycrap@localhost"
    to_marketroid = client.say(to_user['reply-to'], "I don't want your junk.", "user")
   
    assert to_marketroid['from'] != 'person@localhost'

    to_user2 = marketroid.say(to_marketroid['from'], "Hey you should buy my stuff.", "marketroid")

    assert_equal(to_user['reply-to'], to_user2['reply-to'])

    addressing.delete(user_id.split('@')[0])


def test_user_to_user_forbid():
    user_id = test_client_subscribes()

    client.say(user_id, "I want to email myself.", "noreply")
    


########NEW FILE########
__FILENAME__ = addressing_tests
from nose.tools import *
from lamson.testing import *
from lamson import mail
from config import settings
from app.model import addressing

user_real = 'zedshaw@zedshaw.com'
user_id = "user-%s" % addressing.random_id()
host = 'myinboxisnota.tv'

def test_store_lookup_delete():
    addressing.store(user_id, user_real)
    addr = addressing.lookup(user_id)
    assert_equal(addr, user_real)
   
    addressing.delete(user_id)
    assert_raises(KeyError, addressing.lookup, user_id)


def test_store_lookup_delete_with_dumb_addresses():
    addressing.store('"Zed Shaw" <zedshaw@zedshaw.com>', "fake")
    assert_equal("fake", addressing.lookup("zedshaw@zedshaw.com"))
    assert_equal("fake", addressing.lookup('"Zed Shaw" <zedshaw@zedshaw.com>'))
    addressing.delete("zedshaw@zedshaw.com")
    assert_raises(KeyError, addressing.lookup, "zedshaw@zedshaw.com")
    assert_raises(KeyError, addressing.lookup,'"Zed Shaw" <zedshaw@zedshaw.com>')

def test_random_id():
    id_number = addressing.random_id()
    assert id_number

def test_real():
    addressing.store(user_id, user_real)
    assert_equal(addressing.real(user_id), user_real)
    addressing.delete(user_id)


def test_anon():
    addressing.store(user_real, user_id)

    user_anon = addressing.anon(user_real, host)
    assert_equal(user_anon, user_id + '@' + host)

    addressing.delete(user_real)

def test_mapping():
    anon = addressing.mapping(user_real, 'user', host)
    anon_id = anon.split('@')[0]

    assert_equal(addressing.lookup(anon_id), user_real)
    assert_equal(addressing.lookup(user_real), anon_id)
    assert_equal(addressing.lookup(anon_id), user_real)

    addressing.delete(anon_id)
    addressing.delete(user_real)


########NEW FILE########
__FILENAME__ = filter_tests
from nose.tools import *
from lamson.testing import *
from lamson import mail
from config import settings
from app.model import filter, addressing


host = 'myinboxisnota.tv'
user = 'joe@leavemealone.com'
user_anon_addr = addressing.mapping(user, 'user', host)
marketroid = 'marketroid@buymycrap.com'
mk_anon_addr = addressing.mapping(marketroid, 'marketroid', host)
user_id = user_anon_addr.split('@')[0]
marketroid_id = mk_anon_addr.split('@')[0]


from_marketroid = mail.MailResponse(From=marketroid, To=user_anon_addr, Subject="Buy my crap!",
                                    Html="<html></body>You should buy this!</body></html>")
from_user = mail.MailResponse(From=user, To=mk_anon_addr, Subject="No thanks.",
                              Body="Sorry but I'd rather not.")


def setup():
    addressing.store(user_id, user)
    addressing.store(marketroid_id, marketroid)
    addressing.store(marketroid, marketroid_id)

def teardown():
    addressing.delete(user_id)
    addressing.delete(marketroid_id)
    addressing.delete(marketroid)


def test_craft_response():
    # message from marketroid to the user_anon_addr
    msg = mail.MailRequest('fakepeer', from_marketroid['from'],
                           from_marketroid['to'], str(from_marketroid))
    
    # the mail a user would need to respond to
    resp = filter.craft_response(msg, msg['From'], user,
                                 mk_anon_addr).to_message()

    assert_equal(resp['from'], marketroid)
    assert_equal(resp['to'], user)
    assert_equal(resp['reply-to'], mk_anon_addr)

    msg = mail.MailRequest('fakepeer', from_user['from'], from_user['to'],
                           str(from_user))

    # the mail a marketroid could respond to
    resp = filter.craft_response(msg, user_anon_addr, marketroid).to_message()
    assert_equal(resp['from'], user_anon_addr)
    assert_equal(resp['to'], marketroid)

    # make sure the user's address is never in a header
    for k,v in resp.items():
        assert_not_equal(resp[k], user)


def test_cleanse_incoming():
    msg = mail.MailRequest('fakepeer', from_marketroid['from'],
                           from_marketroid['to'], str(from_marketroid))

    reply = filter.cleanse_incoming(msg, user_id, host).to_message()
    assert_equal(reply['from'], marketroid)
    assert_equal(reply['to'], user)
    assert_equal(reply['reply-to'], mk_anon_addr)


def test_route_reply():
    msg = mail.MailRequest('fakepeer', from_user['from'], from_user['to'],
                           str(from_user))
    reply = filter.route_reply(msg, marketroid_id, host).to_message()

    # make sure the user's address is never in a header
    for k,v in reply.items():
        assert_not_equal(reply[k], user)



########NEW FILE########
__FILENAME__ = html_tests
from nose.tools import *
from app.model import html



def test_strip_html():
    doc = """<html><body>
        <h1>Title 1</h1>
        <p>Hello there.</p>
        <p>I like your shirt.</p>
        <p><a href="http://myinboxisnota.tv">Go here for help.</a></p>
        </body></html>
        """
    txt = html.strip_html(doc)

    assert txt
    assert_not_equal(txt, html)
    assert "<" not in txt


def test_strip_big_html():
    doc = open("tests/index.html").read()
    txt = html.strip_html(doc)
    assert txt
    assert_not_equal(txt, html)
    assert "<" not in txt


########NEW FILE########
__FILENAME__ = comment
from app.model import post, comment
from email.utils import parseaddr
from config.settings import relay, SPAM, CONFIRM
from lamson import view, queue
from lamson.routing import route, stateless
from lamson.spam import spam_filter
import logging



@route("(user_id)-AT-(domain)-(post_name)-comment@(host)")
def SPAMMING(message, **options):
    return SPAMMING


@route("(user_id)-AT-(domain)-(post_name)-comment@(host)")
@spam_filter(SPAM['db'], SPAM['rc'], SPAM['queue'], next_state=SPAMMING)
def START(message, user_id=None, post_name=None, host=None, domain=None):
    comment.attach_headers(message, user_id, post_name, domain) 
    CONFIRM.send(relay, "comment", message, "mail/comment_confirm.msg", locals())
    return CONFIRMING


@route("comment-confirm-(id_number)@(host)", id_number="[a-z0-9]+")
def CONFIRMING(message, id_number=None, host=None):
    original = CONFIRM.verify('comment', message['from'], id_number)

    if original:
        # headers are already attached from START
        comment.defer_to_queue(original)
        msg = view.respond(locals(), "mail/comment_submitted.msg",
                           From="noreply@%(host)s",
                           To=original['from'],
                           Subject="Your comment has been posted.")

        relay.deliver(msg)

        return COMMENTING
    else:
        logging.debug("Invalid confirm from %s", message['from'])
        return CONFIRMING


@route("(user_id)-AT-(domain)-(post_name)-comment@(host)")
def COMMENTING(message, user_id=None, post_name=None, host=None, domain=None):
    comment.attach_headers(message, user_id, post_name, domain) 
    comment.defer_to_queue(message)
    original = message # keeps the template happy

    msg = view.respond(locals(), "mail/comment_submitted.msg",
                       From="noreply@%(host)s",
                       To=original['from'],
                       Subject="Your comment has been posted.")
    relay.deliver(msg)

    return COMMENTING




########NEW FILE########
__FILENAME__ = index
from __future__ import with_statement
from email.utils import parseaddr
from lamson import view, queue
from lamson.routing import route, stateless
import logging
from config import settings
from app.model import post
from markdown import markdown



@route("(post_name)@(host)")
@stateless
def POSTING(message, post_name=None, host=None):
    user, address = parseaddr(message['from'])
    user = user or address
    post_url = "posts/%s/%s.html" % (address, post_name)

    index_q = queue.Queue("run/indexed")
    post_keys = sorted(index_q.keys(), reverse=True)
    old_keys = post_keys[50:]
    del post_keys[50:]

    # find the old one and remove it
    posts = []
    for key in post_keys:
        msg = index_q.get(key)
        if msg['x-post-url'] == post_url:
            # this is the old one, take it out
            index_q.remove(key)
        else:
            posts.append(msg)

    # update the index and our posts
    message['X-Post-URL'] = post_url
    index_q.push(message)
    posts.insert(0, message)

    # and generate the index with what we got now
    index = view.render(locals(), "web/index.html")

    f = open("app/data/index.html", "w")
    f.write(index.encode("utf-8"))
    f.close()

    # finally, zap all the old keys
    for old in old_keys: index_q.remove(old)


@route("(user_id)-AT-(domain)-(post_name)-comment@(host)")
@stateless
def COMMENTING(message, user_id=None, domain=None, post_name=None, host=None):
    address = user_id + '@' + domain
    user_dir = post.get_user_dir(address)

    if post.user_exists(address):
        # stuff it here for now, but we'll just build the file rolling
        comments = queue.Queue("%s/comments" % user_dir)
        comments.push(message)
        
        contents = markdown(message.body())
        comment_file = "%s/%s-comments.html" % (user_dir, post_name)
        snippet = view.render(locals(), "web/comments.html")
        with open(comment_file, "a") as out:
            out.write(snippet)

    else:
        logging.warning("Attempt to post to user %r but user doesn't exist.", address)


########NEW FILE########
__FILENAME__ = post
from app.model import post
from email.utils import parseaddr
from config.settings import relay, CONFIRM
from lamson import view, queue
from lamson.routing import route, stateless
import logging


@route("(post_name)@(host)")
def START(message, post_name=None, host=None):
    message['X-Post-Name'] = post_name

    CONFIRM.send(relay, "post", message, "mail/confirm.msg", locals())
    return CONFIRMING


@route("post-confirm-(id_number)@(host)", id_number="[a-z0-9]+")
def CONFIRMING(message, id_number=None, host=None):
    original = CONFIRM.verify('post', message['from'], id_number)

    if original:
        name, address = parseaddr(original['from'])
        post_name = original['x-post-name']

        post_id = post.post(post_name, address, host, original)
        msg = view.respond(locals(), "mail/welcome.msg",
                           From="noreply@%(host)s",
                           To=message['from'],
                           Subject="Welcome, your blog is ready.")
        relay.deliver(msg)

        return POSTING
    else:
        logging.warning("Invalid confirm from %s", message['from'])
        return CONFIRMING



@route("(post_name)@(host)")
@route("(post_name)-(action)@(host)", action="delete")
def POSTING(message, post_name=None, host=None, action=None):
    name, address = parseaddr(message['from'])

    if not action:
        post.post(post_name, address, host, message)
        msg = view.respond(locals(), 'mail/page_ready.msg', 
                           From="noreply@%(host)s",
                           To=message['from'],
                           Subject="Your page '%(post_name)s' is ready.")
        relay.deliver(msg)

        # first real message, now we can index it
        index_q = queue.Queue("run/posts")
        index_q.push(message)
    elif action == "delete":
        post.delete(post_name, address)

        msg = view.respond(locals(), 'mail/deleted.msg', 
                           From="noreply@%(host)s",
                           To=message['from'],
                           Subject="Your page '%(post_name)s' was deleted.")

        relay.deliver(msg)
    else:
        logging.debug("Invalid action: %r", action)

    return POSTING




########NEW FILE########
__FILENAME__ = comment
from lamson import queue


def attach_headers(message, user_id, post_name, domain):
    """Headers are used later by the index.py handler to figure out where
    the message finally goes."""
    message['X-Post-Name'] = post_name
    message['X-Post-User-ID'] = user_id
    message['X-Post-Domain'] = domain


def defer_to_queue(message):
    index_q = queue.Queue("run/posts")  # use a diff queue?
    index_q.push(message)
    print "run/posts count after dever", index_q.count()

########NEW FILE########
__FILENAME__ = post
import os
import logging
from lamson import view, queue
import email
from config.settings import BLOG_BASE
from markdown import markdown


def delete(post_name, user):
    file_name = blog_file_name(post_name, user)

    if os.path.exists(file_name):
        logging.debug("DELETING %s", file_name)
        os.unlink(file_name)
        remove_from_queue(post_name, user)


def post(post_name, user, host, message):
    user_dir = make_user_dir(user)
    user_id, domain = user.split("@")

    # make sure it's removed first if it existed
    delete(post_name, user)

    posting = open("%s/%s.html" % (user_dir, post_name), "w")
    content = markdown(message.body())

    html = view.render(locals(), "web/post.html")

    posting.write(html.encode('utf-8'))

    post_q = get_user_post_queue(user_dir)
    post_q.push(message)


def make_user_dir(user):
    user_dir = get_user_dir(user)

    if not user_exists(user):
        os.mkdir(user_dir)

    return user_dir

def remove_from_queue(post_name, user):
    user_dir = get_user_dir(user)
    post_q = get_user_post_queue(user_dir)
    for k in post_q.keys():
        msg = post_q.get(k)
        name, address = email.utils.parseaddr(msg['to'])
        if address.startswith(post_name):
            logging.debug("Removing %s:%s from the queue", k, address)
            post_q.remove(k)


def user_exists(user):
    return os.path.exists(get_user_dir(user))

def get_user_dir(user):
    return "%s/%s" % (BLOG_BASE, user)

def blog_file_name(post_name, user):
    return "%s/%s.html" % (get_user_dir(user), post_name)

def get_user_post_queue(user_dir):
    queue_dir = "%s/posts_queue" % (user_dir)
    return queue.Queue(queue_dir)


########NEW FILE########
__FILENAME__ = boot
from config import settings
from lamson.routing import Router
from lamson.server import Relay, SMTPReceiver
from lamson import view
import logging
import logging.config
import jinja2

# configure logging to go to a log file
logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=1)

# where to listen for incoming messages
settings.receiver = SMTPReceiver(settings.receiver_config['host'],
                                 settings.receiver_config['port'])


Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))


########NEW FILE########
__FILENAME__ = forward
from config import settings
from lamson.routing import Router
from lamson.server import Relay, QueueReceiver
from lamson import view
import logging
import logging.config
import jinja2

# configure logging to go to a log file
logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=1)

# where to listen for incoming messages
settings.receiver = QueueReceiver('run/undeliverable', settings.queue_config['sleep'])

Router.defaults(**settings.router_defaults)
Router.load(['lamson.handlers.forward'])
Router.RELOAD=True
Router.UNDELIVERABLE_QUEUE=None

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))


########NEW FILE########
__FILENAME__ = queue
from config import settings
from lamson.routing import Router
from lamson.server import Relay, QueueReceiver
from lamson import view
import logging
import logging.config
import jinja2

# configure logging to go to a log file
logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=1)

# where to listen for incoming messages
settings.receiver = QueueReceiver(settings.queue_config['queue'],
                                  settings.queue_config['sleep'])


Router.defaults(**settings.router_defaults)
Router.load(settings.queue_handlers)
Router.RELOAD=True

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))


########NEW FILE########
__FILENAME__ = settings
# This file contains python variables that configure Lamson for email processing.
from lamson import queue, routing, confirm
import logging
import shelve

relay_config = {'host': 'localhost', 'port': 8825}

receiver_config = {'host': 'localhost', 'port': 8823}

handlers = ['app.handlers.post', 'app.handlers.comment']

router_defaults = {'host': 'oneshotblog\\.com', 
                   'domain': "localhost|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}",
                   'user_id': "[a-zA-Z0-9._%+-]+",
                   'post_name': "[a-zA-Z0-9][a-zA-Z0-9.]+"}

template_config = {'dir': 'app', 'module': 'templates'}

BLOG_BASE="app/data/posts"

# this is for when you run the config.queue boot
queue_config = {'queue': 'run/posts', 'sleep': 10}

queue_handlers = ['app.handlers.index']

SPAM = {'db': 'app/spamdb', 'rc': 'spamrc', 'queue': 'run/spam'}

routing.Router.UNDELIVERABLE_QUEUE=queue.Queue("run/undeliverable")

CONFIRM_STORAGE=confirm.ConfirmationStorage(db=shelve.open("run/confirmationsdb"))
CONFIRM = confirm.ConfirmationEngine('run/pending', CONFIRM_STORAGE)


########NEW FILE########
__FILENAME__ = testing
from config import settings
from lamson import view
from lamson.routing import Router
from lamson.server import Relay
import jinja2
import logging
import logging.config
import os

# configure logging to go to a log file
logging.config.fileConfig("config/test_logging.conf")

# the relay host to actually send the final message to (set debug=1 to see what
# the relay is saying to the log server).
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=0)


settings.receiver = None


Router.defaults(**settings.router_defaults)
Router.load(settings.handlers + settings.queue_handlers)
Router.RELOAD=True

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))

# if you have pyenchant and enchant installed then the template tests will do
# spell checking for you, but you need to tell pyenchant where to find itself
if 'PYENCHANT_LIBRARY_PATH' not in os.environ:
    os.environ['PYENCHANT_LIBRARY_PATH'] = '/opt/local/lib/libenchant.dylib'


########NEW FILE########
__FILENAME__ = comments_tests
from nose.tools import *
from lamson.testing import *
from lamson.routing import Router
from app.model import post
import time

sender = "sender-%s@localhost" % time.time()
host = "oneshotblog.com"
comment_id = int(time.time())
comment_address = "tester-AT-localhost-test.blog.%d-comment@%s" % (comment_id, host)
target_user = "tester@localhost"
sender = "commenter-%s@localhost" % time.time()
client = RouterConversation(sender, 'Comment Tests Subject')

def setup():
    clear_queue("run/posts")
    clear_queue("run/spam")
    post.make_user_dir(target_user)

def make_spam():
    spam_data = open("tests/spam").read()
    spam = mail.MailRequest("test_spam_sent_by_unconfirmed_user", "spammer@spamtime.com", "spam" + comment_address, spam_data)
    spam['To'] = "spam" + comment_address
    return spam

def test_new_user_comments():
    client.begin()
    msg = client.say(comment_address, "I totally disagree with you!", 'confirm')
    client.say(msg['Reply-To'], 'Confirmed I am.', 'noreply')
    assert delivered(sender, to_queue=queue("run/posts"))
    assert delivered(sender, to_queue=queue(post.get_user_dir(target_user) + "/comments"))


def test_confirmed_user_comments():
    test_new_user_comments()
    client.say(comment_address, "I said I disagree!", "noreply")
    assert delivered(sender, to_queue=queue("run/posts"))

def test_invalid_confirmation():
    client.begin()
    client.say(comment_address, "I want to break in.", 'confirm')
    clear_queue()  # make sure no message is available

    # attacker does not have the above message
    client.say("confirm-11111111@" + host, 'Sneaky I am.')
    assert not delivered('noreply'), "Should not get a reply to a bad confirm." + str(msg)

def test_spam_sent_by_unconfirmed_user():
    setup()

    client.begin()
    Router.deliver(make_spam())

def test_spam_sent_by_confirmed_user():
    test_confirmed_user_comments()
    clear_queue("run/posts")

    Router.deliver(make_spam())



########NEW FILE########
__FILENAME__ = index_tests
from nose.tools import *
from lamson.testing import *
from handlers import post_tests
import os

index = "app/data/index.html"

def reset_index():
    clear_queue("run/indexed")
    assert queue("run/indexed").count() == 0

    clear_queue("run/posts")
    assert queue("run/posts").count() == 0
    if os.path.exists(index):
        os.unlink(index)

def setup():
    reset_index()

def test_index_updated_after_post():
    post_tests.test_new_user_subscribes()
    assert os.path.exists(index)
    contents = open(index).read()

    post_tests.test_existing_user_posts()
    assert os.path.exists(index)
    updated = open(index).read()

    assert contents != updated, "The index should change."

def test_comment_added_to_list():
    pass


########NEW FILE########
__FILENAME__ = post_tests
from nose.tools import *
from lamson.testing import *
import os
import time
import shutil

relay = relay(port=8823)
sender = "sender-%s@sender.com" % time.time()
host = "oneshotblog.com"
blog_id = int(time.time())
blog_address = "test.blog.%d@%s" % (blog_id, host)

client = RouterConversation(sender, 'Post Tests Subject')

def test_new_user_subscribes():
    client.begin()
    msg = client.say(blog_address, "I'd like a blog thanks.", 'confirm')
    client.say(msg['Reply-To'], 'Confirmed I am.', 'noreply')

def test_bad_user_tries_invalid_confirm():
    client.begin()
    client.say(blog_address, "I want to break in.", 'confirm')
    clear_queue()  # make sure no message is available

    # attacker does not have the above message
    client.say("confirm-11111111@" + host, 'Sneaky I am.')
    assert not delivered('noreply'), "Should not get a reply to a bad confirm." + str(msg)


def test_existing_user_posts():
    test_new_user_subscribes()

    client.say(blog_address, "This is my new page.", "noreply")

    expected_file = "app/data/posts/%s/%s.html" % (sender, 'test.blog.%s' % blog_id)
    assert os.path.exists(expected_file), "Should get an html."


def test_existing_user_posts_invalid_action():
    test_new_user_subscribes()
    clear_queue()

    client.say("test.blog.%s-unfuddleamick@" + host, 'Please unfuddleamick me.')
    assert not delivered('noreply'), "Should get nothing for an invalid action."

def test_existing_user_deletes():
    test_new_user_subscribes()
    clear_queue()

    expected_file = "app/data/posts/%s/%s.html" % (sender, 'test.blog.%s' % blog_id)

    blog_delete = "test.blog.%s-delete@%s" % (blog_id, host)
    client.say(blog_delete, "Please delete.", "noreply")

    assert not os.path.exists(expected_file), "File should be gone."




########NEW FILE########
__FILENAME__ = comment
from nose.tools import *
from lamson import mail
from app.model import comment

def test_attach_headers():
    msg = mail.MailRequest('test_attach_headers', 'tester@localhost', 'test.blog@oneshotblog.com',
                           'Fake body.')

    comment.attach_headers(msg)
    for key in ['X-Post-Name', 'X-Post-User-ID', 'X-Post-Domain']:
        assert key in msg


########NEW FILE########
__FILENAME__ = post_tests
from nose.tools import *
from lamson.mail import MailRequest
from lamson import view
import os
import time
from app.model import post
import jinja2
import config
import shutil

view.LOADER = jinja2.Environment(loader=jinja2.PackageLoader('app', 'templates'))
user = "test_user@localhost"
blog = "test_blog"
name = "Tester Joe"

def test_post():
    message = MailRequest("fakepeer", user,
                          "%s@oneshotblog.com" % blog, "Fake body")
    message['Subject'] = 'Test subject'

    post.post(blog, user, "localhost", message)

    assert post.user_exists(user), "User dir not created."
    assert os.path.exists(post.blog_file_name(blog, user)), "File not made."

def test_delete():
    test_post()
    post.delete(blog, user)
    assert post.user_exists(user), "User dir should stay."
    assert not os.path.exists(post.blog_file_name(blog, user)), "File should go."

def test_make_user_dir():
    assert not os.path.exists("sampleuser")
    dir = post.make_user_dir("sampleuser")
    assert dir == post.get_user_dir("sampleuser")
    assert os.path.exists(dir)
    shutil.rmtree(dir)


def test_remove_from_queue():
    message = MailRequest("fakepeer", user,
                          "%s@oneshotblog.com" % blog, "Fake body")
    message['Subject'] = 'Test subject'

    post_q = post.get_user_post_queue(post.get_user_dir(user))

    post.post(blog, user, 'localhost', message)

    assert post_q.count(), "No messages in the post queue."
    count = post_q.count()

    post.remove_from_queue(blog, user)
    assert post_q.count() == count-1, "It didn't get removed."

def test_user_exists():
    assert post.user_exists(user)
    assert not post.user_exists(user + "nothere")

def test_get_user_dir():
    dir = post.get_user_dir(user)
    assert dir.startswith(config.settings.BLOG_BASE)
    assert dir.endswith(user)

def test_blog_file_name():
    name = post.blog_file_name(blog, user)
    assert name.endswith("html")



########NEW FILE########
__FILENAME__ = osb_tests
from nose.tools import *
from lamson.testing import *
from lamson import view
import os
from glob import glob

def test_spelling():
    message = {}
    original = {}
    for path in glob("app/templates/mail/*.msg"):
        template = "mail/" + os.path.basename(path)
        result = view.render(locals(), template)
        spelling(template, result)


########NEW FILE########
__FILENAME__ = bounce
"""
Bounce analysis module for Lamson.  It uses an algorithm that tries
to simply collect the headers that are most likely found in a bounce
message, and then determine a probability based on what it finds.
"""

import re
from functools import wraps


BOUNCE_MATCHERS = {
    'Action': re.compile(r'(failed|delayed|delivered|relayed|expanded)', re.IGNORECASE | re.DOTALL),
    'Content-Description': re.compile(r'(Notification|Undelivered Message|Delivery Report)', re.IGNORECASE | re.DOTALL),
    'Diagnostic-Code': re.compile(r'(.+);\s*([0-9\-\.]+)?\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Final-Recipient': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Received': re.compile(r'(.+)', re.IGNORECASE | re.DOTALL),
    'Remote-Mta': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Reporting-Mta': re.compile(r'(.+);\s*(.*)', re.IGNORECASE | re.DOTALL),
    'Status': re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)', re.IGNORECASE | re.DOTALL)
}

BOUNCE_MAX = len(BOUNCE_MATCHERS) * 2.0

PRIMARY_STATUS_CODES = {
    u'1': u'Unknown Status Code 1',
    u'2': u'Success',
    u'3': u'Temporary Failure',
    u'4': u'Persistent Transient Failure',
    u'5': u'Permanent Failure'
}

SECONDARY_STATUS_CODES = {
    u'0':   u'Other or Undefined Status',
    u'1':   u'Addressing Status',
    u'2':   u'Mailbox Status',
    u'3':   u'Mail System Status',
    u'4':   u'Network and Routing Status',
    u'5':   u'Mail Delivery Protocol Status',
    u'6':   u'Message Content or Media Status',
    u'7':   u'Security or Policy Status',
}

COMBINED_STATUS_CODES = {
    u'00': u'Not Applicable',
    u'10': u'Other address status',
    u'11': u'Bad destination mailbox address',
    u'12': u'Bad destination system address',
    u'13': u'Bad destination mailbox address syntax',
    u'14': u'Destination mailbox address ambiguous',
    u'15': u'Destination mailbox address valid',
    u'16': u'Mailbox has moved',
    u'17': u'Bad sender\'s mailbox address syntax',
    u'18': u'Bad sender\'s system address',

    u'20': u'Other or undefined mailbox status',
    u'21': u'Mailbox disabled, not accepting messages',
    u'22': u'Mailbox full',
    u'23': u'Message length exceeds administrative limit.',
    u'24': u'Mailing list expansion problem',

    u'30': u'Other or undefined mail system status',
    u'31': u'Mail system full',
    u'32': u'System not accepting network messages',
    u'33': u'System not capable of selected features',
    u'34': u'Message too big for system',

    u'40': u'Other or undefined network or routing status',
    u'41': u'No answer from host',
    u'42': u'Bad connection',
    u'43': u'Routing server failure',
    u'44': u'Unable to route',
    u'45': u'Network congestion',
    u'46': u'Routing loop detected',
    u'47': u'Delivery time expired',

    u'50': u'Other or undefined protocol status',
    u'51': u'Invalid command',
    u'52': u'Syntax error',
    u'53': u'Too many recipients',
    u'54': u'Invalid command arguments',
    u'55': u'Wrong protocol version',

    u'60': u'Other or undefined media error',
    u'61': u'Media not supported',
    u'62': u'Conversion required and prohibited',
    u'63': u'Conversion required but not supported',
    u'64': u'Conversion with loss performed',
    u'65': u'Conversion failed',

    u'70': u'Other or undefined security status',
    u'71': u'Delivery not authorized, message refused',
    u'72': u'Mailing list expansion prohibited',
    u'73': u'Security conversion required but not possible',
    u'74': u'Security features not supported',
    u'75': u'Cryptographic failure',
    u'76': u'Cryptographic algorithm not supported',
    u'77': u'Message integrity failure',
}

def match_bounce_headers(msg):
    """
    Goes through the headers in a potential bounce message recursively
    and collects all the answers for the usual bounce headers.
    """
    matches = {'Content-Description-Parts': {}}
    for part in msg.base.walk():
        for k in BOUNCE_MATCHERS:
            if k in part.headers:
                if k not in matches:
                    matches[k] = set()

                # kind of an odd place to put this, but it's the easiest way
                if k == 'Content-Description':
                    matches['Content-Description-Parts'][part.headers[k].lower()] = part

                matches[k].add(part.headers[k])

    return matches


def detect(msg):
    """
    Given a message, this will calculate a probability score based on
    possible bounce headers it finds and return a lamson.bounce.BounceAnalyzer
    object for further analysis.

    The detection algorithm is very simple but still accurate.  For each header
    it finds it adds a point to the score.  It then uses the regex in BOUNCE_MATCHERS
    to see if the value of that header is parseable, and if it is it adds another
    point to the score.  The final probability is based on how many headers and matchers
    were found out of the total possible.

    Finally, a header will be included in the score if it doesn't match in value, but
    it WILL NOT be included in the headers used by BounceAnalyzer to give you meanings
    like remote_mta and such.

    Because this algorithm is very dumb, you are free to add to BOUNCE_MATCHERS in your
    boot files if there's special headers you need to detect in your own code.
    """
    originals = match_bounce_headers(msg)
    results = {'Content-Description-Parts':
               originals['Content-Description-Parts']}
    score = 0
    del originals['Content-Description-Parts']

    for key in originals:
        score += 1  # score still goes up, even if value doesn't parse
        r = BOUNCE_MATCHERS[key]

        scan = (r.match(v) for v in originals[key])
        matched = [m.groups() for m in scan if m]

        # a key is counted in the score, but only added if it matches
        if len(matched) > 0:
            score += len(matched) / len(originals[key])
            results[key] = matched

    return BounceAnalyzer(results, score / BOUNCE_MAX)


class BounceAnalyzer(object):
    """
    BounceAnalyzer collects up the score and the headers and gives more
    meaningful interaction with them.  You can keep it simple and just use
    is_hard, is_soft, and probable methods to see if there was a bounce.
    If you need more information then attributes are set for each of the following:

        * primary_status -- The main status number that determines hard vs soft.
        * secondary_status -- Advice status.
        * combined_status -- the 2nd and 3rd number combined gives more detail.
        * remote_mta -- The MTA that you sent mail to and aborted.
        * reporting_mta -- The MTA that was sending the mail and has to report to you.
        * diagnostic_codes -- Human readable codes usually with info from the provider.
        * action -- Usually 'failed', and turns out to be not too useful.
        * content_parts -- All the attachments found as a hash keyed by the type.
        * original -- The original message, if it's found.
        * report -- All report elements, as lamson.encoding.MailBase raw messages.
        * notification -- Usually the detailed reason you bounced.
    """
    def __init__(self, headers, score):
        """
        Initializes all the various attributes you can use to analyze the bounce
        results.
        """
        self.headers = headers
        self.score = score

        if 'Status' in self.headers:
            status = self.headers['Status'][0]
            self.primary_status = int(status[0]), PRIMARY_STATUS_CODES[status[0]]
            self.secondary_status = int(status[1]), SECONDARY_STATUS_CODES[status[1]]
            combined = "".join(status[1:])
            self.combined_status = int(combined), COMBINED_STATUS_CODES[combined]
        else:
            self.primary_status = (None, None)
            self.secondary_status = (None, None)
            self.combined_status = (None, None)

        if 'Remote-Mta' in self.headers:
            self.remote_mta = self.headers['Remote-Mta'][0][1]
        else:
            self.remote_mta = None

        if 'Reporting-Mta' in self.headers:
            self.reporting_mta = self.headers['Reporting-Mta'][0][1]
        else:
            self.reporting_mta = None

        if 'Final-Recipient' in self.headers:
            self.final_recipient = self.headers['Final-Recipient'][0][1]
        else:
            self.final_recipient = None

        if 'Diagnostic-Code' in self.headers:
            self.diagnostic_codes = self.headers['Diagnostic-Code'][0][1:]
        else:
            self.diagnostic_codes = [None, None]
       
        if 'Action' in self.headers:
            self.action = self.headers['Action'][0][0]
        else:
            self.action = None

        # these are forced lowercase because they're so damn random
        self.content_parts = self.headers['Content-Description-Parts']
        # and of course, this isn't the original original, it's the wrapper
        self.original = self.content_parts.get('undelivered message', None)

        if self.original and self.original.parts:
            self.original = self.original.parts[0]

        self.report = self.content_parts.get('delivery report', None)
        if self.report and self.report.parts:
            self.report = self.report.parts

        self.notification = self.content_parts.get('notification', None)


    def is_hard(self):
        """
        Tells you if this was a hard bounce, which is determined by the message
        being a probably bounce with a primary_status greater than 4.
        """
        return self.probable() and self.primary_status[0] > 4

    def is_soft(self):
        """Basically the inverse of is_hard()"""
        return self.probable() and self.primary_status[0] <= 4

    def probable(self, threshold=0.3):
        """
        Determines if this is probably a bounce based on the score 
        probability.  Default threshold is 0.3 which is conservative.
        """
        return self.score > threshold

    def error_for_humans(self):
        """
        Constructs an error from the status codes that you can print to
        a user.
        """
        if self.primary_status[0]:
            return "%s, %s, %s" % (self.primary_status[1],
                                   self.secondary_status[1],
                                   self.combined_status[1])
        else:
            return "No status codes found in bounce message."


class bounce_to(object):
    """
    Used to route bounce messages to a handler for either soft or hard bounces.
    Set the soft/hard parameters to the function that represents the handler.
    The function should take one argument of the message that it needs to handle
    and should have a route that handles everything.

    WARNING: You should only place this on the START of modules that will
    receive bounces, and every bounce handler should return START.  The reason
    is that the bounce emails come from *mail daemons* not the actual person
    who bounced.  You can find out who that person is using
    message.bounce.final_recipient.  But the bounce handler is *actually*
    interacting with a message from something like MAILER-DAEMON@somehost.com.
    If you don't go back to start immediately then you will mess with the state
    for this address, which can be bad.
    """
    def __init__(self, soft=None, hard=None):
        self.soft = soft
        self.hard = hard

        assert self.soft and self.hard, "You must give at least soft and/or hard"

    def __call__(self, func):
        @wraps(func)
        def bounce_wrapper(message, *args, **kw):
            if message.is_bounce():
                if message.bounce.is_soft():
                    return self.soft(message)
                else:
                    return self.hard(message)
            else:
                return func(message, *args, **kw)

        return bounce_wrapper


########NEW FILE########
__FILENAME__ = commands
"""
Implements the Lamson command line tool's commands, which are run
by the lamson.args module dynamically.  Each command has it's
actual user displayed command line documentation as the __doc__
string.

You will notice that all of the command functions in this module
end in _command.  This is not required by the lamson.args module
but it is the default.  You could easily use any other suffix, or
none at all.

This is done to disambiguate the command that it implements
so that your command line tools do not clash with Python's
reserved words and built-ins.  With this design you can have a
list_command without clashing with list().

You will also notice that commands which take trailing positional
arguments give a TRAILING=[] or TRAILING=None (if it's required).
This is done instead of *args because we need to use None to indicate
that this command requires positional arguments.  TRAILING=[] is 
like saying they are optional (but expected), and TRAILING=None is
like saying they are required.  You can't (afaik) do TRAILING=None
with *args.

See python-modargs for more details.
"""

from lamson import server, utils, mail, routing, queue, encoding
from modargs import args
from pkg_resources import resource_stream
from zipfile import ZipFile
import glob
import lamson
import os
import signal
import sys
import time
import mailbox
import email

def log_command(port=8825, host='127.0.0.1', chroot=False,
                chdir=".", uid=False, gid=False, umask=False, pid="./run/log.pid",
               FORCE=False, debug=False):
    """
    Runs a logging only server on the given hosts and port.  It logs
    each message it receives and also stores it to the run/queue 
    so that you can make sure it was received in testing.

    lamson log -port 8825 -host 127.0.0.1 \\
            -pid ./run/log.pid -chroot False  \\
            -chdir "." -umask False -uid False -gid False \\
            -FORCE False

    If you specify a uid/gid then this means you want to first change to
    root, set everything up, and then drop to that UID/GID combination.
    This is typically so you can bind to port 25 and then become "safe"
    to continue operating as a non-root user.

    If you give one or the other, this it will just change to that
    uid or gid without doing the priv drop operation.
    """
    loader = lambda: utils.make_fake_settings(host, port)
    utils.start_server(pid, FORCE, chroot, chdir, uid, gid, umask, loader, debug)


def send_command(port=8825, host='127.0.0.1', username=False, password=False,
                 ssl=False, starttls=False, debug=1, sender=None, to=None,
                 subject=None, body=None, attach=False):
    """
    Sends an email to someone as a test message.
    See the sendmail command for a sendmail replacement.
    
    lamson send -port 8825 -host 127.0.0.1 -debug 1 \\
            -sender EMAIL -to EMAIL -subject STR -body STR -attach False'

    There is also a username, password, and starttls option for those 
    who need it.
    """
    message = mail.MailResponse(From=sender,
                                  To=to,
                                  Subject=subject,
                                  Body=body)
    if attach:
        message.attach(attach)

    if username == False:
        username = None
    if password == False:
        password = None

    relay = server.Relay(host, port=port, username=username, password=password,
                         ssl=ssl, starttls=starttls, debug=debug)
    relay.deliver(message)


def sendmail_command(port=8825, host='127.0.0.1', debug=0, TRAILING=None):
    """
    Used as a testing sendmail replacement for use in programs
    like mutt as an MTA.  It reads the email to send on the stdin
    and then delivers it based on the port and host settings.

    lamson sendmail -port 8825 -host 127.0.0.1 -debug 0 -- [recipients]
    """
    relay = server.Relay(host, port=port,
                           debug=debug)
    data = sys.stdin.read()
    msg = mail.MailRequest(Peer=None, From=None, To=None, Data=data)
    relay.deliver(msg, To=TRAILING)




def start_command(pid='./run/smtp.pid', FORCE=False, chroot=False, chdir=".",
                  boot="config.boot", uid=False, gid=False, umask=False, debug=False):
    """
    Runs a lamson server out of the current directory:

    lamson start -pid ./run/smtp.pid -FORCE False -chroot False -chdir "." \\
            -umask False -uid False -gid False -boot config.boot
    """
    loader = lambda: utils.import_settings(True, from_dir=os.getcwd(), boot_module=boot)
    utils.start_server(pid, FORCE, chroot, chdir, uid, gid, umask, loader, debug)


def stop_command(pid='./run/smtp.pid', KILL=False, ALL=False):
    """
    Stops a running lamson server.  Give -KILL True to have it
    stopped violently.  The PID file is removed after the 
    signal is sent.  Give -ALL the name of a run directory and
    it will stop all pid files it finds there.

    lamson stop -pid ./run/smtp.pid -KILL False -ALL False
    """
    pid_files = []

    if ALL:
        pid_files = glob.glob(ALL + "/*.pid")
    else:
        pid_files = [pid]

        if not os.path.exists(pid):
            print "PID file %s doesn't exist, maybe Lamson isn't running?" % pid
            sys.exit(1)
            return # for unit tests mocking sys.exit

    print "Stopping processes with the following PID files: %s" % pid_files

    for pid_f in pid_files:
        pid = open(pid_f).readline()

        print "Attempting to stop lamson at pid %d" % int(pid)

        try:
            if KILL:
                os.kill(int(pid), signal.SIGKILL)
            else:
                os.kill(int(pid), signal.SIGHUP)
            
            os.unlink(pid_f)
        except OSError, exc:
            print "ERROR stopping Lamson on PID %d: %s" % (int(pid), exc)


def restart_command(**options):
    """
    Simply attempts a stop and then a start command.  All options for both
    apply to restart.  See stop and start for options available.
    """

    stop_command(**options)
    time.sleep(2)
    start_command(**options)


def status_command(pid='./run/smtp.pid'):
    """
    Prints out status information about lamson useful for finding out if it's
    running and where.

    lamson status -pid ./run/smtp.pid
    """
    if os.path.exists(pid):
        pid = open(pid).readline()
        print "Lamson running with PID %d" % int(pid)
    else:
        print "Lamson not running."


def help_command(**options):
    """
    Prints out help for the commands. 

    lamson help

    You can get help for one command with:

    lamson help -for STR
    """
    if "for" in options:
        help_text = args.help_for_command(lamson.commands, options['for'])
        if help_text:
            print help_text
        else:
            args.invalid_command_message(lamson.commands, exit_on_error=True)
    else:
        print "Available commands:\n"
        print ", ".join(args.available_commands(lamson.commands))
        print "\nUse lamson help -for <command> to find out more."


def queue_command(pop=False, get=False, keys=False, remove=False, count=False,
                  clear=False, name="run/queue"):
    """
    Let's you do most of the operations available to a queue.

    lamson queue (-pop | -get | -remove | -count | -clear | -keys) -name run/queue
    """
    print "Using queue: %r" % name

    inq = queue.Queue(name)

    if pop:
        key, msg = inq.pop()
        if key:
            print "KEY: ", key
            print msg
    elif get:
        print inq.get(get)
    elif remove:
        inq.remove(remove)
    elif count:
        print "Queue %s contains %d messages" % (name, inq.count())
    elif clear:
        inq.clear()
    elif keys:
        print "\n".join(inq.keys())
    else:
        print "Give something to do.  Try lamson help -for queue to find out what."
        sys.exit(1)
        return # for unit tests mocking sys.exit
        

def routes_command(TRAILING=['config.testing'], path=os.getcwd(), test=""):
    """
    Prints out valuable information about an application's routing configuration
    after everything is loaded and ready to go.  Helps debug problems with
    messages not getting to your handlers.  Path has the search paths you want
    separated by a ':' character, and it's added to the sys.path.

    lamson routes -path $PWD -- config.testing -test ""

    It defaults to running your config.testing to load the routes. 
    If you want it to run the config.boot then give that instead:

    lamson routes -- config.boot

    You can also test a potential target by doing -test EMAIL.

    """
    modules = TRAILING
    sys.path += path.split(':')
    test_case_matches = []

    for module in modules:
        __import__(module, globals(), locals())

    print "Routing ORDER: ", routing.Router.ORDER
    print "Routing TABLE: \n---"
    for format in routing.Router.REGISTERED:
        print "%r: " % format,
        regex, functions = routing.Router.REGISTERED[format]
        for func in functions:
            print "%s.%s " % (func.__module__, func.__name__),
            match = regex.match(test)
            if test and match:
                test_case_matches.append((format, func, match))

        print "\n---"

    if test_case_matches:
        print "\nTEST address %r matches:" % test
        for format, func, match in test_case_matches:
            print "  %r %s.%s" % (format, func.__module__, func.__name__)
            print "  -  %r" % (match.groupdict())
    elif test:
        print "\nTEST address %r didn't match anything." % test



def gen_command(project=None, FORCE=False):
    """
    Generates various useful things for you to get you started.

    lamson gen -project STR -FORCE False
    """
    project = project

    if os.path.exists(project) and not FORCE:
        print "Project %s exists, delete it first." % project
        sys.exit(1)
        return

    prototype = ZipFile(resource_stream(__name__, 'data/prototype.zip'))
    # looks like the very handy ZipFile.extractall is only in python 2.6

    if not os.path.exists(project):
        os.makedirs(project)

    files = prototype.namelist()

    for gen_f in files:
        if str(gen_f).endswith('/'):
            target = os.path.join(project, gen_f)
            if not os.path.exists(target):
                print "mkdir: %s" % target
                os.makedirs(target)
        else:
            target = os.path.join(project, gen_f)
            if os.path.exists(target): 
                continue

            print "copy: %s" % target
            out = open(target, 'w')
            out.write(prototype.read(gen_f))
            out.close()


def web_command(basedir=".", port=8888, host='127.0.0.1'):
    """
    Starts a very simple files only web server for easy testing of applications
    that need to make some HTML files as the result of their operation.
    If you need more than this then use a real web server.

    lamson web -basedir "." -port 8888 -host '127.0.0.1'

    This command doesn't exit so you can view the logs it prints out.
    """
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler 

    os.chdir(basedir)
    web = HTTPServer((host, port), SimpleHTTPRequestHandler)
    print "Starting server on %s:%d out of directory %r" % (
        host, port, basedir)
    web.serve_forever()


def cleanse_command(input=None, output=None):
    """
    Uses Lamson mail cleansing and canonicalization system to take an
    input maildir (or mbox) and replicate the email over into another
    maildir.  It's used mostly for testing and cleaning.
    """
    error_count = 0

    try:
        inbox = mailbox.mbox(input)
    except:
        inbox = mailbox.Maildir(input, factory=None)

    outbox = mailbox.Maildir(output)

    for msg in inbox:
        try:
            mail = encoding.from_message(msg)
            outbox.add(encoding.to_string(mail))
        except encoding.EncodingError, exc:
            print "ERROR: ", exc
            error_count += 1

    outbox.close()
    inbox.close()

    print "TOTAL ERRORS:", error_count


def blast_command(input=None, host='127.0.0.1', port=8823, debug=0):
    """
    Given a maildir, this command will go through each email
    and blast it at your server.  It does nothing to the message, so
    it will be real messages hitting your server, not cleansed ones.
    """
    inbox = mailbox.Maildir(input)
    relay = server.Relay(host, port=port, debug=debug)

    for key in inbox.keys():
        msgfile = inbox.get_file(key)
        msg = email.message_from_file(msgfile)
        relay.deliver(msg)


def version_command():
    """
    Prints the version of Lamson, the reporitory revision, and the
    file it came from.
    """

    from lamson import version

    print "Lamson-Version: ", version.VERSION['version']
    print "Repository-Revision:", version.VERSION['rev'][0]
    print "Repository-Hash:", version.VERSION['rev'][1]
    print "Version-File:", version.__file__
    print ""
    print "Lamson is Copyright (C) Zed A. Shaw 2008-2009.  Licensed GPLv3."
    print "If you didn't get a copy of the LICENSE contact the author at:\n"
    print "   zedshaw@zedshaw.com"
    print ""
    print "Have fun."


########NEW FILE########
__FILENAME__ = confirm
"""
Confirmation handling API that helps you get the whole confirm/pending/verify 
process correct.  It doesn't implement any handlers, but what it does do is
provide the logic for doing the following:

    * Take an email, put it in a "pending" queue, and then send out a confirm
    email with a strong random id.
    * Store the pending message ID and the random secret someplace for later
    verification.
    * Verify an incoming email against the expected ID, and get back the
    original.

You then just work this into your project's state flow, write your own
templates, and possibly write your own storage.
"""

import uuid
from lamson import queue, view
from email.utils import parseaddr

class ConfirmationStorage(object):
    """
    This is the basic confirmation storage.  For simple testing purposes
    you can just use the default hash db parameter.  If you do a deployment
    you can probably get away with a shelf hash instead.

    You can write your own version of this and use it.  The confirmation engine
    only cares that it gets something that supports all of these methods.
    """
    def __init__(self, db={}):
        """
        Change the db parameter to a shelf to get persistent storage.
        """
        self.confirmations = db

    def clear(self):
        """
        Used primarily in testing, this clears out all pending confirmations.
        """
        self.confirmations.clear()

    def key(self, target, from_address):
        """
        Used internally to construct a string key, if you write
        your own you don't need this.

        NOTE: To support proper equality and shelve storage, this encodes the
        key into ASCII.  Make a different subclass if you need unicode and your
        storage supports it.
        """
        key = target + ':' + from_address

        return key.encode('ascii')

    def get(self, target, from_address):
        """
        Given a target and a from address, this returns a tuple of (expected_secret, pending_message_id).
        If it doesn't find that target+from_address, then it should return a (None, None) tuple.
        """
        return self.confirmations.get(self.key(target, from_address), (None, None))

    def delete(self, target, from_address):
        """
        Removes a target+from_address from the storage.
        """
        try:
            del self.confirmations[self.key(target, from_address)]
        except KeyError:
            pass

    def store(self, target, from_address, expected_secret, pending_message_id):
        """
        Given a target, from_address it will store the expected_secret and pending_message_id
        of later verification.  The target should be a string indicating what is being
        confirmed.  Like "subscribe", "post", etc.

        When implementing your own you should *never* allow more than one target+from_address
        combination.
        """
        self.confirmations[self.key(target, from_address)] = (expected_secret,
                                                              pending_message_id)

class ConfirmationEngine(object):
    """
    The confirmation engine is what does the work of sending a confirmation, 
    and verifying that it was confirmed properly.  In order to use it you
    have to construct the ConfirmationEngine (usually in config/settings.py) and
    you write your confirmation message templates for sending.

    The primary methods you use are ConfirmationEngine.send and ConfirmationEngine.verify.
    """
    def __init__(self, pending_queue, storage):
        """
        The pending_queue should be a string with the path to the lamson.queue.Queue 
        that will store pending messages.  These messages are the originals the user
        sent when they tried to confirm.

        Storage should be something that is like ConfirmationStorage so that this
        can store things for later verification.
        """
        self.pending = queue.Queue(pending_queue)
        self.storage = storage

    def get_pending(self, pending_id):
        """
        Returns the pending message for the given ID.
        """
        return self.pending.get(pending_id)

    def push_pending(self, message):
        """
        Puts a pending message into the pending queue.
        """
        return self.pending.push(message)

    def delete_pending(self, pending_id):
        """
        Removes the pending message from the pending queue.
        """
        self.pending.remove(pending_id)


    def cancel(self, target, from_address, expect_secret):
        """
        Used to cancel a pending confirmation.
        """
        name, addr = parseaddr(from_address)

        secret, pending_id = self.storage.get(target, addr)

        if secret == expect_secret:
            self.storage.delete(target, addr)
            self.delete_pending(pending_id)

    def make_random_secret(self):
        """
        Generates a random uuid as the secret, in hex form.
        """
        return uuid.uuid4().hex

    def register(self, target, message):
        """
        Don't call this directly unless you know what you are doing.
        It does the job of registering the original message and the
        expected confirmation into the storage.
        """
        from_address = message.route_from

        pending_id = self.push_pending(message)
        secret = self.make_random_secret()
        self.storage.store(target, from_address, secret, pending_id)

        return "%s-confirm-%s" % (target, secret)

    def verify(self, target, from_address, expect_secret):
        """
        Given a target (i.e. "subscribe", "post", etc), a from_address
        of someone trying to confirm, and the secret they should use, this
        will try to verify their confirmation.  If the verify works then
        you'll get the original message back to do what you want with.

        If the verification fails then you are given None.

        The message is *not* deleted from the pending queue.  You can do
        that yourself with delete_pending.
        """
        assert expect_secret, "Must give an expected ID number."
        name, addr = parseaddr(from_address)

        secret, pending_id = self.storage.get(target, addr)

        if secret == expect_secret:
            self.storage.delete(target, addr)
            return self.get_pending(pending_id)
        else:
            return None

    def send(self, relay, target, message, template, vars):
        """
        This is the method you should use to send out confirmation messages.
        You give it the relay, a target (i.e. "subscribe"), the message they
        sent requesting the confirm, your confirmation template, and any
        vars that template needs.

        The result of calling this is that the template message gets sent through
        the relay, the original message is stored in the pending queue, and 
        data is put into the storage for later calls to verify.
        """
        confirm_address = self.register(target, message)
        vars.update(locals())
        msg = view.respond(vars, template, To=message['from'],
                           From="%(confirm_address)s@%(host)s",
                           Subject="Confirmation required")

        msg['Reply-To'] = "%(confirm_address)s@%(host)s" % vars

        relay.deliver(msg)

    def clear(self):
        """
        Used in testing to make sure there's nothing in the pending
        queue or storage.
        """
        self.pending.clear()
        self.storage.clear()

########NEW FILE########
__FILENAME__ = sample
import logging
from lamson.routing import route, route_like, stateless
from config.settings import relay
from lamson import view


@route("(address)@(host)", address=".+")
def START(message, address=None, host=None):
    return NEW_USER


@route_like(START)
def NEW_USER(message, address=None, host=None):
    return NEW_USER


@route_like(START)
def END(message, address=None, host=None):
    return NEW_USER(message, address, host)


@route_like(START)
@stateless
def FORWARD(message, address=None, host=None):
    relay.deliver(message)


########NEW FILE########
__FILENAME__ = boot
from config import settings
from lamson.routing import Router
from lamson.server import Relay, SMTPReceiver
from lamson import view, queue
import logging
import logging.config
import jinja2

logging.config.fileConfig("config/logging.conf")

# the relay host to actually send the final message to
settings.relay = Relay(host=settings.relay_config['host'],
                       port=settings.relay_config['port'], debug=1)

# where to listen for incoming messages
settings.receiver = SMTPReceiver(settings.receiver_config['host'],
                                 settings.receiver_config['port'])

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True
Router.UNDELIVERABLE_QUEUE=queue.Queue("run/undeliverable")

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['module'],
                                settings.template_config['dir']))

########NEW FILE########
__FILENAME__ = settings
# This file contains python variables that configure Lamson for email processing.
import logging

# You may add additional parameters such as `username' and `password' if your
# relay server requires authentication, `starttls' (boolean) or `ssl' (boolean)
# for secure connections.
relay_config = {'host': 'localhost', 'port': 8825}

receiver_config = {'host': 'localhost', 'port': 8823}

handlers = ['app.handlers.sample']

router_defaults = {'host': '.+'}

# config values for jinja.PackageLoader
template_config = {'module': 'app', 'dir': 'templates'}

# the config/boot.py will turn these values into variables set in settings

########NEW FILE########
__FILENAME__ = testing
from config import settings
from lamson import view
from lamson.routing import Router
from lamson.server import Relay
import jinja2
import logging
import logging.config
import os

logging.config.fileConfig("config/test_logging.conf")

# the relay host to actually send the final message to (set debug=1 to see what
# the relay is saying to the log server).
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=0)


settings.receiver = None

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers)
Router.RELOAD=True
Router.LOG_EXCEPTIONS=False

view.LOADER = jinja2.Environment(
    loader=jinja2.PackageLoader(settings.template_config['dir'], 
                                settings.template_config['module']))

# if you have pyenchant and enchant installed then the template tests will do
# spell checking for you, but you need to tell pyenchant where to find itself
# if 'PYENCHANT_LIBRARY_PATH' not in os.environ:
#     os.environ['PYENCHANT_LIBRARY_PATH'] = '/opt/local/lib/libenchant.dylib'


########NEW FILE########
__FILENAME__ = open_relay_tests
from nose.tools import *
from lamson.testing import *
import os
from lamson import server

relay = relay(port=8823)
client = RouterConversation("somedude@localhost", "requests_tests")
confirm_format = "testing-confirm-[0-9]+@"
noreply_format = "testing-noreply@"


def test_forwards_relay_host():
    """
    !!!!!! YOU MUST CONFIGURE YOUR config/settings.py OR THIS WILL FAIL !!!!!!
    Makes sure that your config/settings.py is configured to forward mail from
    localhost (or your direct host) to your relay.
    """
    client.begin()
    client.say("tester@localhost", "Test that forward works.", "tester@localhost")


def test_drops_open_relay_messages():
    """
    But, make sure that mail NOT for test.com gets dropped silently.
    """
    client.begin()
    client.say("tester@badplace.notinterwebs", "Relay should not happen")
    assert queue().count() == 0, "You are configured currently to accept everything.  You should change config/settings.py router_defaults so host is your actual host name that will receive mail."


########NEW FILE########
__FILENAME__ = encoding
"""
Lamson takes the policy that email it receives is most likely complete garbage 
using bizarre pre-Unicode formats that are irrelevant and unnecessary in today's
modern world.  These emails must be cleansed of their unholy stench of
randomness and turned into something nice and clean that a regular Python
programmer can work with:  unicode.

That's the receiving end, but on the sending end Lamson wants to make the world
better by not increasing the suffering.  To that end, Lamson will canonicalize
all email it sends to be ascii or utf-8 (whichever is simpler and works to
encode the data).  When you get an email from Lamson, it is a pristine easily
parseable clean unit of goodness you can count on.

To accomplish these tasks, Lamson goes back to basics and assert a few simple
rules on each email it receives:

1) NO ENCODING IS TRUSTED, NO LANGUAGE IS SACRED, ALL ARE SUSPECT.
2) Python wants Unicode, it will get Unicode.
3) Any email that CANNOT become Unicode, CANNOT be processed by Lamson or
Python.
4) Email addresses are ESSENTIAL to Lamson's routing and security, and therefore
will be canonicalized and properly encoded.
5) Lamson will therefore try to "upgrade" all email it receives to Unicode
internally, and cleaning all email addresses.
6) It does this by decoding all codecs, and if the codec LIES, then it will
attempt to statistically detect the codec using chardet.
7) If it can't detect the codec, and the codec lies, then the email is bad.
8) All text bodies and attachments are then converted to Python unicode in the
same way as the headers.
9) All other attachments are converted to raw strings as-is.

Once Lamson has done this, your Python handler can now assume that all
MailRequest objects are happily unicode enabled and ready to go.  The rule is:

    IF IT CANNOT BE UNICODE, THEN PYTHON CANNOT WORK WITH IT.

On the outgoing end (when you send a MailResponse), Lamson tries to create the
email it wants to receive by canonicalizing it:

1) All email will be encoded in the simplest cleanest way possible without
losing information.
2) All headers are converted to 'ascii', and if that doesn't work, then 'utf-8'.
3) All text/* attachments and bodies are converted to ascii, and if that doesn't
work, 'utf-8'.
4) All other attachments are left alone.
5) All email addresses are normalized and encoded if they have not been already.

The end result is an email that has the highest probability of not containing
any obfuscation techniques, hidden characters, bad characters, improper
formatting, invalid non-characterset headers, or any of the other billions of
things email clients do to the world.  The output rule of Lamson is:

    ALL EMAIL IS ASCII FIRST, THEN UTF-8, AND IF CANNOT BE EITHER THOSE IT WILL
    NOT BE SENT.

Following these simple rules, this module does the work of converting email
to the canonical format and sending the canonical format.  The code is 
probably the most complex part of Lamson since the job it does is difficult.

Test results show that Lamson can safely canonicalize most email from any
culture (not just English) to the canonical form, and that if it can't then the
email is not formatted right and/or spam.

If you find an instance where this is not the case, then submit it to the
project as a test case.
"""

import string
from email.charset import Charset
import chardet
import re
import email
from email import encoders
from email.mime.base import MIMEBase
from email.utils import parseaddr
import sys


DEFAULT_ENCODING = "utf-8"
DEFAULT_ERROR_HANDLING = "strict"
CONTENT_ENCODING_KEYS = set(['Content-Type', 'Content-Transfer-Encoding',
                             'Content-Disposition', 'Mime-Version'])
CONTENT_ENCODING_REMOVED_PARAMS = ['boundary']

REGEX_OPTS = re.IGNORECASE | re.MULTILINE
ENCODING_REGEX = re.compile(r"\=\?([a-z0-9\-]+?)\?([bq])\?", REGEX_OPTS)
ENCODING_END_REGEX = re.compile(r"\?=", REGEX_OPTS)
INDENT_REGEX = re.compile(r"\n\s+")

VALUE_IS_EMAIL_ADDRESS = lambda v: '@' in v
ADDRESS_HEADERS_WHITELIST = ['From', 'To', 'Delivered-To', 'Cc', 'Bcc']

class EncodingError(Exception): 
    """Thrown when there is an encoding error."""
    pass


class MailBase(object):
    """MailBase is used as the basis of lamson.mail and contains the basics of
    encoding an email.  You actually can do all your email processing with this
    class, but it's more raw.
    """
    def __init__(self, items=()):
        self.headers = dict(items)
        self.parts = []
        self.body = None
        self.content_encoding = {'Content-Type': (None, {}), 
                                 'Content-Disposition': (None, {}),
                                 'Content-Transfer-Encoding': (None, {})}

    def __getitem__(self, key):
        return self.headers.get(normalize_header(key), None)

    def __len__(self):
        return len(self.headers)

    def __iter__(self):
        return iter(self.headers)

    def __contains__(self, key):
        return normalize_header(key) in self.headers

    def __setitem__(self, key, value):
        self.headers[normalize_header(key)] = value

    def __delitem__(self, key):
        del self.headers[normalize_header(key)]

    def __nonzero__(self):
        return self.body != None or len(self.headers) > 0 or len(self.parts) > 0

    def keys(self):
        """Returns the sorted keys."""
        return sorted(self.headers.keys())

    def attach_file(self, filename, data, ctype, disposition):
        """
        A file attachment is a raw attachment with a disposition that
        indicates the file name.
        """
        assert filename, "You can't attach a file without a filename."
        assert ctype.lower() == ctype, "Hey, don't be an ass.  Use a lowercase content type."

        part = MailBase()
        part.body = data
        part.content_encoding['Content-Type'] = (ctype, {'name': filename})
        part.content_encoding['Content-Disposition'] = (disposition,
                                                        {'filename': filename})
        self.parts.append(part)


    def attach_text(self, data, ctype):
        """
        This attaches a simpler text encoded part, which doesn't have a
        filename.
        """
        assert ctype.lower() == ctype, "Hey, don't be an ass.  Use a lowercase content type."

        part = MailBase()
        part.body = data
        part.content_encoding['Content-Type'] = (ctype, {})
        self.parts.append(part)

    def walk(self):
        for p in self.parts:
            yield p
            for x in p.walk():
                yield x


class MIMEPart(MIMEBase):
    """
    A reimplementation of nearly everything in email.mime to be more useful
    for actually attaching things.  Rather than one class for every type of
    thing you'd encode, there's just this one, and it figures out how to
    encode what you ask it.
    """
    def __init__(self, type_, **params):
        self.maintype, self.subtype = type_.split('/')
        MIMEBase.__init__(self, self.maintype, self.subtype, **params)

    def add_text(self, content):
        # this is text, so encode it in canonical form
        try:
            encoded = content.encode('ascii')
            charset = 'ascii'
        except UnicodeError:
            encoded = content.encode('utf-8')
            charset = 'utf-8'

        self.set_payload(encoded, charset=charset)


    def extract_payload(self, mail):
        if mail.body == None: return  # only None, '' is still ok

        ctype, ctype_params = mail.content_encoding['Content-Type']
        cdisp, cdisp_params = mail.content_encoding['Content-Disposition']

        assert ctype, "Extract payload requires that mail.content_encoding have a valid Content-Type."

        if ctype.startswith("text/"):
            self.add_text(mail.body)
        else:
            if cdisp:
                # replicate the content-disposition settings
                self.add_header('Content-Disposition', cdisp, **cdisp_params)

            self.set_payload(mail.body)
            encoders.encode_base64(self)

    def __repr__(self):
        return "<MIMEPart '%s/%s': %r, %r, multipart=%r>" % (self.subtype, self.maintype, self['Content-Type'],
                                              self['Content-Disposition'],
                                                            self.is_multipart())

def from_message(message):
    """
    Given a MIMEBase or similar Python email API message object, this
    will canonicalize it and give you back a pristine MailBase.
    If it can't then it raises a EncodingError.
    """
    mail = MailBase()

    # parse the content information out of message
    for k in CONTENT_ENCODING_KEYS:
        setting, params = parse_parameter_header(message, k)
        setting = setting.lower() if setting else setting
        mail.content_encoding[k] = (setting, params)

    # copy over any keys that are not part of the content information
    for k in message.keys():
        if normalize_header(k) not in mail.content_encoding:
            mail[k] = header_from_mime_encoding(message[k])
  
    decode_message_body(mail, message)

    if message.is_multipart():
        # recursively go through each subpart and decode in the same way
        for msg in message.get_payload():
            if msg != message:  # skip the multipart message itself
                mail.parts.append(from_message(msg))

    return mail



def to_message(mail):
    """
    Given a MailBase message, this will construct a MIMEPart 
    that is canonicalized for use with the Python email API.
    """
    ctype, params = mail.content_encoding['Content-Type']

    if not ctype:
        if mail.parts:
            ctype = 'multipart/mixed'
        else:
            ctype = 'text/plain'
    else:
        if mail.parts:
            assert ctype.startswith("multipart") or ctype.startswith("message"), "Content type should be multipart or message, not %r" % ctype

    # adjust the content type according to what it should be now
    mail.content_encoding['Content-Type'] = (ctype, params)

    try:
        out = MIMEPart(ctype, **params)
    except TypeError, exc:
        raise EncodingError("Content-Type malformed, not allowed: %r; %r (Python ERROR: %s" %
                            (ctype, params, exc.message))

    for k in mail.keys():
        if k in ADDRESS_HEADERS_WHITELIST:
            out[k.encode('ascii')] = header_to_mime_encoding(mail[k])
        else:
            out[k.encode('ascii')] = header_to_mime_encoding(mail[k], not_email=True)

    out.extract_payload(mail)

    # go through the children
    for part in mail.parts:
        out.attach(to_message(part))

    return out


def to_string(mail, envelope_header=False):
    """Returns a canonicalized email string you can use to send or store
    somewhere."""
    msg = to_message(mail).as_string(envelope_header)
    assert "From nobody" not in msg
    return msg


def from_string(data):
    """Takes a string, and tries to clean it up into a clean MailBase."""
    return from_message(email.message_from_string(data))


def to_file(mail, fileobj):
    """Writes a canonicalized message to the given file."""
    fileobj.write(to_string(mail))

def from_file(fileobj):
    """Reads an email and cleans it up to make a MailBase."""
    return from_message(email.message_from_file(fileobj))


def normalize_header(header):
    return string.capwords(header.lower(), '-')


def parse_parameter_header(message, header):
    params = message.get_params(header=header)
    if params:
        value = params.pop(0)[0]
        params_dict = dict(params)

        for key in CONTENT_ENCODING_REMOVED_PARAMS:
            if key in params_dict: del params_dict[key]

        return value, params_dict
    else:
        return None, {}

def decode_message_body(mail, message):
    mail.body = message.get_payload(decode=True)
    if mail.body:
        # decode the payload according to the charset given if it's text
        ctype, params = mail.content_encoding['Content-Type']

        if not ctype:
            charset = 'ascii'
            mail.body = attempt_decoding(charset, mail.body)
        elif ctype.startswith("text/"):
            charset = params.get('charset', 'ascii')
            mail.body = attempt_decoding(charset, mail.body)
        else:
            # it's a binary codec of some kind, so just decode and leave it
            # alone for now
            pass


def properly_encode_header(value, encoder, not_email):
    """
    The only thing special (weird) about this function is that it tries
    to do a fast check to see if the header value has an email address in
    it.  Since random headers could have an email address, and email addresses
    have weird special formatting rules, we have to check for it.

    Normally this works fine, but in Librelist, we need to "obfuscate" email
    addresses by changing the '@' to '-AT-'.  This is where
    VALUE_IS_EMAIL_ADDRESS exists.  It's a simple lambda returning True/False
    to check if a header value has an email address.  If you need to make this
    check different, then change this.
    """
    try:
        return value.encode("ascii")
    except UnicodeEncodeError:
        if not_email is False and VALUE_IS_EMAIL_ADDRESS(value):
            # this could have an email address, make sure we don't screw it up
            name, address = parseaddr(value)
            return '"%s" <%s>' % (encoder.header_encode(name.encode("utf-8")), address)

        return encoder.header_encode(value.encode("utf-8"))


def header_to_mime_encoding(value, not_email=False):
    if not value: return ""

    encoder = Charset(DEFAULT_ENCODING)
    if type(value) == list:
        return "; ".join(properly_encode_header(v, encoder, not_email) for v in value)
    else:
        return properly_encode_header(value, encoder, not_email)


def header_from_mime_encoding(header):
    if header is None: 
        return header
    elif type(header) == list:
        return [properly_decode_header(h) for h in header]
    else:
        return properly_decode_header(header)




def guess_encoding_and_decode(original, data, errors=DEFAULT_ERROR_HANDLING):
    try:
        charset = chardet.detect(str(data))

        if not charset['encoding']:
            raise EncodingError("Header claimed %r charset, but detection found none.  Decoding failed." % original)

        return data.decode(charset["encoding"], errors)
    except UnicodeError, exc:
        raise EncodingError("Header lied and claimed %r charset, guessing said "
                            "%r charset, neither worked so this is a bad email: "
                            "%s." % (original, charset, exc))


def attempt_decoding(charset, dec):
    try:
        if isinstance(dec, unicode):
            # it's already unicode so just return it
            return dec
        else:
            return dec.decode(charset)
    except UnicodeError:
        # looks like the charset lies, try to detect it
        return guess_encoding_and_decode(charset, dec)
    except LookupError:
        # they gave a crap encoding
        return guess_encoding_and_decode(charset, dec)


def apply_charset_to_header(charset, encoding, data):
    if encoding == 'b' or encoding == 'B':
        dec = email.base64mime.decode(data.encode('ascii'))
    elif encoding == 'q' or encoding == 'Q':
        dec = email.quoprimime.header_decode(data.encode('ascii'))
    else:
        raise EncodingError("Invalid header encoding %r should be 'Q' or 'B'." % encoding)

    return attempt_decoding(charset, dec)




def _match(data, pattern, pos):
    found = pattern.search(data, pos)
    if found:
        # contract: returns data before the match, and the match groups
        left = data[pos:found.start()]
        return left, found.groups(), found.end()
    else:
        left = data[pos:]
        return left, None, -1



def _tokenize(data, next):
    enc_data = None

    left, enc_header, next = _match(data, ENCODING_REGEX, next)
   
    if next != -1:
        enc_data, _, next = _match(data, ENCODING_END_REGEX, next)

    return left, enc_header, enc_data, next


def _scan(data):
    next = 0
    continued = False
    while next != -1:
        left, enc_header, enc_data, next = _tokenize(data, next)

        if next != -1 and INDENT_REGEX.match(data, next):
            continued = True
        else:
            continued = False

        yield left, enc_header, enc_data, continued


def _parse_charset_header(data):
    scanner = _scan(data)
    oddness = None

    try:
        while True:
            if not oddness:
                left, enc_header, enc_data, continued = scanner.next()
            else:
                left, enc_header, enc_data, continued = oddness
                oddness = None

            while continued:
                l, eh, ed, continued = scanner.next()
               
                if not eh:
                    assert not ed, "Parsing error, give Zed this: %r" % data
                    oddness = (" " + l.lstrip(), eh, ed, continued)
                elif eh[0] == enc_header[0] and eh[1] == enc_header[1]:
                    enc_data += ed
                else:
                    # odd case, it's continued but not from the same base64
                    # need to stack this for the next loop, and drop the \n\s+
                    oddness = ('', eh, ed, continued)
                    break

            if left:
                yield attempt_decoding('ascii', left)
                       
            if enc_header:
                yield apply_charset_to_header(enc_header[0], enc_header[1], enc_data)

    except StopIteration:
        pass


def properly_decode_header(header):
    return u"".join(_parse_charset_header(header))



########NEW FILE########
__FILENAME__ = forward
"""
Implements a forwarding handler that will take anything it receives and
forwards it to the relay host.  It is intended to use with the
lamson.routing.RoutingBase.UNDELIVERABLE_QUEUE if you want mail that Lamson
doesn't understand to be delivered like normal.  The Router will dump
any mail that doesn't match into that queue if you set it, and then you can
load this handler into a special queue receiver to have it forwarded on.

BE VERY CAREFUL WITH THIS.  It should only be used in testing scenarios as
it can turn your server into an open relay if you're not careful.  You
are probably better off writing your own version of this that knows a list
of allowed hosts your machine answers to and only forwards those.
"""

from lamson.routing import route, stateless
from config import settings
import logging

@route("(to)@(host)", to=".+", host=".+")
@stateless
def START(message, to=None, host=None):
    """Forwards every mail it gets to the relay.  BE CAREFULE WITH THIS."""
    logging.debug("MESSAGE to %s@%s forwarded to the relay host.", to, host)
    settings.relay.deliver(message)


########NEW FILE########
__FILENAME__ = log
"""
Implements a simple logging handler that's actually used by the lamson log
command line tool to run a logging server.  It simply takes every message it
receives and dumps it to the logging.debug stream.
"""

from lamson.routing import route, stateless
import logging

@route("(to)@(host)", to=".+", host=".+")
@stateless
def START(message, to=None, host=None):
    """This is stateless and handles every email no matter what, logging what it receives."""
    logging.debug("MESSAGE to %s@%s:\n%s" % (to, host, str(message)))



########NEW FILE########
__FILENAME__ = queue
"""
Implements a handler that puts every message it receives into 
the run/queue directory.  It is intended as a debug tool so you
can inspect messages the server is receiving using mutt or 
the lamson queue command.
"""

from lamson.routing import route_like, stateless, nolocking
from lamson import queue, handlers
import logging

@route_like(handlers.log.START)
@stateless
@nolocking
def START(message, to=None, host=None):
    """
    @stateless and routes however handlers.log.START routes (everything).
    Has @nolocking, but that's alright since it's just writing to a maildir.
    """
    q = queue.Queue('run/queue')
    q.push(message)


########NEW FILE########
__FILENAME__ = html
"""
This implements an HTML Mail generator that uses templates and CleverCSS
to produce an HTML message with inline CSS attributes so that it will
display correctly.  As long as you can keep most of the HTML and CSS simple you
should have a high success rate at rendering this.

How it works is you create an HtmlMail class and configure it with a CleverCSS
stylesheet (also a template).  This acts as your template for the appearance and
the outer shell of your HTML.

When you go to send, you use a markdown content template to generate the
guts of your HTML.  You hand this, variables, and email headers to 
HtmlMail.respond and it spits back a fully formed lamson.mail.MailResponse
ready to send.

The engine basically parses the CSS, renders your content template, 
render your outer template, and then applies the CSS directly to your HTML
so your CSS attributes are inline and display in the HTML display.

Each element is a template loaded by your loader: the CleverCSS template, out HTML
template, and your own content.

Finally, use this as a generator by making one and having crank out all the emails
you need.  Don't make one HtmlMail for each message.
"""

from BeautifulSoup import BeautifulSoup
import clevercss
from lamson import mail, view
from markdown2 import markdown


class HtmlMail(object):
    """
    Acts as a lamson.mail.MailResponse generator that produces a properly 
    formatted HTML mail message, including inline CSS applied to all HTML tags.
    """
    def __init__(self, css_template, html_template, variables={}, wiki=markdown):
        """
        You pass in a CleverCSS template (it'll be run through the template engine
        before CleverCSS), the html_template, and any variables that the CSS template
        needs.

        The CSS template is processed once, the html_template is processed each time
        you call render or respond.

        If you don't like markdown, then you can set the wiki variable to any callable
        that processes your templates.
        """
        self.template = html_template
        self.load_css(css_template, variables)
        self.wiki = wiki

    def load_css(self, css_template, variables):
        """
        If you want to change the CSS, simply call this with the new CSS and variables.
        It will change internal state so that later calls to render or respond use
        the new CSS.
        """
        self.css = view.render(variables, css_template)
        self.engine = clevercss.Engine(self.css)
        self.stylesheet = []
        
        for selector, style in self.engine.evaluate():
            attr = "; ".join("%s: %s" % (k,v) for k,v in style)
            selectors = selector[0].split()
            # root, path, attr
            self.stylesheet.append((selectors[0], selectors[1:], attr))


    def reduce_tags(self, name, tags):
        """
        Used mostly internally to find all the tags that fit the given
        CSS selector.  It's fairly primitive, working only on tag names,
        classes, and ids.  You shouldn't get too fancy with the CSS you create.
        """
        results = []

        for tag in tags:
            if name.startswith("#"):
                children = tag.findAll(attrs={"class": name[1:]})
            elif name.startswith("."):
                children = tag.findAll(attrs={"id": name[1:]})
            else:
                children = tag.findAll(name)

            if children:
                results += children

        return results

    def apply_styles(self, html):
        """
        Used mostly internally but helpful for testing, this takes the given HTML
        and applies the configured CSS you've set.  It returns a BeautifulSoup
        object with all the style attributes set and nothing else changed.
        """
        doc = BeautifulSoup(html)
        roots = {}  # the roots rarely change, even though the paths do

        for root, path, attr in self.stylesheet:
            tags = roots.get(root, None)
            
            if not tags:
                tags = self.reduce_tags(root, [doc])
                roots[root] = tags
           
            for sel in path:
                tags = self.reduce_tags(sel, tags)


            for node in tags:
                try:
                    node['style'] += "; " + attr
                except KeyError:
                    node['style'] = attr

        return doc

        
    def render(self, variables, content_template,  pretty=False):
        """
        Works like lamson.view.render, but uses apply_styles to modify
        the HTML with the configured CSS before returning it to you.

        If you set the pretty=True then it will prettyprint the results,
        which is a waste of bandwidth, but helps when debugging.

        Remember that content_template is run through the template system,
        and then processed with self.wiki (defaults to markdown).  This
        let's you do template processing and write the HTML contents like
        you would an email.

        You could also attach the content_template as a text version of the
        message for people without HTML.  Simply set the .Body attribute
        of the returned lamson.mail.MailResponse object.
        """
        content = self.wiki(view.render(variables, content_template))
        lvars = variables.copy()
        lvars['content'] = content

        html = view.render(lvars, self.template)
        styled = self.apply_styles(html)

        if pretty:
            return styled.prettify()
        else:
            return str(styled)


    def respond(self, variables, content, **kwd):
        """
        Works like lamson.view.respond letting you craft a
        lamson.mail.MailResponse immediately from the results of
        a lamson.html.HtmlMail.render call.  Simply pass in the
        From, To, and Subject parameters you would normally pass
        in for MailResponse, and it'll craft the HTML mail for
        you and return it ready to deliver.

        A slight convenience in this function is that if the
        Body kw parameter equals the content parameter, then
        it's assumed you want the raw markdown content to be
        sent as the text version, and it will produce a nice
        dual HTML/text email.
        """
        assert content, "You must give a contents template."

        if kwd.get('Body', None) == content:
            kwd['Body'] = view.render(variables, content)

        for key in kwd:
            kwd[key] = kwd[key] % variables
        
        msg = mail.MailResponse(**kwd)
        msg.Html = self.render(variables, content)

        return msg


    

########NEW FILE########
__FILENAME__ = mail
"""
The lamson.mail module contains nothing more than wrappers around the big work
done in lamson.encoding.  These are the actual APIs that you'll interact with
when doing email, and they mostly replicate the lamson.encoding.MailBase 
functionality.

The main design criteria is that MailRequest is mostly for reading email 
that you've received, so it doesn't have functions for attaching files and such.
MailResponse is used when you are going to write an email, so it has the
APIs for doing attachments and such.
"""


import mimetypes
from lamson import encoding, bounce
from email.utils import parseaddr
import os
import warnings


# You can change this to 'Delivered-To' on servers that support it like Postfix
ROUTABLE_TO_HEADER='to'

def _decode_header_randomness(addr):
    """
    This fixes the given address so that it is *always* a set() of 
    just email addresses suitable for routing.
    """
    if not addr:
        return set()
    elif isinstance(addr, list):
        return set(parseaddr(a.lower())[1] for a in addr)
    elif isinstance(addr, basestring):
        return set([parseaddr(addr.lower())[1]])
    else:
        raise encoding.EncodingError("Address must be a string or a list not: %r", type(addr))


class MailRequest(object):
    """
    This is what's handed to your handlers for you to process.  The information
    you get out of this is *ALWAYS* in Python unicode and should be usable 
    by any API.  Modifying this object will cause other handlers that deal
    with it to get your modifications, but in general you don't want to do
    more than maybe tag a few headers.
    """
    def __init__(self, Peer, From, To, Data):
        """
        Peer is the remote peer making the connection (sometimes the queue
        name).  From and To are what you think they are.  Data is the raw
        full email as received by the server.

        NOTE:  It does not handle multiple From headers, if that's even
        possible.  It will parse the From into a list and take the first
        one.
        """

        self.original = Data
        self.base = encoding.from_string(Data)
        self.Peer = Peer
        self.From = From or self.base['from']
        self.To = To or self.base[ROUTABLE_TO_HEADER]

        if 'from' not in self.base: 
            self.base['from'] = self.From
        if 'to' not in self.base:
            # do NOT use ROUTABLE_TO here
            self.base['to'] = self.To

        self.route_to = _decode_header_randomness(self.To)
        self.route_from = _decode_header_randomness(self.From)

        if self.route_from:
            self.route_from = self.route_from.pop()
        else:
            self.route_from = None

        self.bounce = None


    def all_parts(self):
        """Returns all multipart mime parts.  This could be an empty list."""
        return self.base.parts


    def body(self):
        """
        Always returns a body if there is one.  If the message
        is multipart then it returns the first part's body, if
        it's not then it just returns the body.  If returns
        None then this message has nothing for a body.
        """
        if self.base.parts:
            return self.base.parts[0].body
        else:
            return self.base.body


    def __contains__(self, key):
        return self.base.__contains__(key)

    def __getitem__(self, name):
        return self.base.__getitem__(name)

    def __setitem__(self, name, val):
        self.base.__setitem__(name, val)

    def __delitem__(self, name):
        del self.base[name]

    def __str__(self):
        """
        Converts this to a string usable for storage into a queue or 
        transmission.
        """
        return encoding.to_string(self.base)

    def __repr__(self):
        return "From: %r" % [self.Peer, self.From, self.To]

    def keys(self):
        return self.base.keys()

    def to_message(self):
        """
        Converts this to a Python email message you can use to
        interact with the python mail APIs.
        """
        return encoding.to_message(self.base)

    def walk(self):
        """Recursively walks all attached parts and their children."""
        for x in self.base.walk():
            yield x

    def is_bounce(self, threshold=0.3):
        """
        Determines whether the message is a bounce message based on 
        lamson.bounce.BounceAnalzyer given threshold.  0.3 is a good
        conservative base.
        """
        if not self.bounce:
            self.bounce = bounce.detect(self)

        if self.bounce.score > threshold:
            return True
        else:
            return False

    @property
    def msg(self):
        warnings.warn("The .msg attribute is deprecated, use .base instead.  This will be gone in Lamson 1.0",
                          category=DeprecationWarning, stacklevel=2)
        return self.base



class MailResponse(object):
    """
    You are given MailResponse objects from the lamson.view methods, and
    whenever you want to generate an email to send to someone.  It has
    the same basic functionality as MailRequest, but it is designed to
    be written to, rather than read from (although you can do both).

    You can easily set a Body or Html during creation or after by
    passing it as __init__ parameters, or by setting those attributes.

    You can initially set the From, To, and Subject, but they are headers so
    use the dict notation to change them:  msg['From'] = 'joe@test.com'.

    The message is not fully crafted until right when you convert it with
    MailResponse.to_message.  This lets you change it and work with it, then
    send it out when it's ready.
    """
    def __init__(self, To=None, From=None, Subject=None, Body=None, Html=None):
        self.Body = Body
        self.Html = Html
        self.base = encoding.MailBase([('To', To), ('From', From), ('Subject', Subject)])
        self.multipart = self.Body and self.Html
        self.attachments = []

    def __contains__(self, key):
        return self.base.__contains__(key)

    def __getitem__(self, key):
        return self.base.__getitem__(key)

    def __setitem__(self, key, val):
        return self.base.__setitem__(key, val)

    def __delitem__(self, name):
        del self.base[name]

    def attach(self, filename=None, content_type=None, data=None, disposition=None):
        """
        Simplifies attaching files from disk or data as files.  To attach simple
        text simple give data and a content_type.  To attach a file, give the
        data/content_type/filename/disposition combination.

        For convenience, if you don't give data and only a filename, then it
        will read that file's contents when you call to_message() later.  If you 
        give data and filename then it will assume you've filled data with what
        the file's contents are and filename is just the name to use.
        """
        assert filename or data, "You must give a filename or some data to attach."
        assert data or os.path.exists(filename), "File doesn't exist, and no data given."

        self.multipart = True

        if filename and not content_type:
            content_type, encoding = mimetypes.guess_type(filename)

        assert content_type, "No content type given, and couldn't guess from the filename: %r" % filename

        self.attachments.append({'filename': filename,
                                 'content_type': content_type,
                                 'data': data,
                                 'disposition': disposition,})
    def attach_part(self, part):
        """
        Attaches a raw MailBase part from a MailRequest (or anywhere)
        so that you can copy it over.
        """
        self.multipart = True

        self.attachments.append({'filename': None,
                                 'content_type': None,
                                 'data': None,
                                 'disposition': None,
                                 'part': part,
                                 })

    def attach_all_parts(self, mail_request):
        """
        Used for copying the attachment parts of a mail.MailRequest
        object for mailing lists that need to maintain attachments.
        """
        for part in mail_request.all_parts():
            self.attach_part(part)

        self.base.content_encoding = mail_request.base.content_encoding.copy()

    def clear(self):
        """
        Clears out the attachments so you can redo them.  Use this to keep the
        headers for a series of different messages with different attachments.
        """
        del self.attachments[:]
        del self.base.parts[:]
        self.multipart = False


    def update(self, message):
        """
        Used to easily set a bunch of heading from another dict
        like object.
        """
        for k in message.keys():
            self.base[k] = message[k]

    def __str__(self):
        """
        Converts to a string.
        """
        return self.to_message().as_string()

    def _encode_attachment(self, filename=None, content_type=None, data=None, disposition=None, part=None):
        """
        Used internally to take the attachments mentioned in self.attachments
        and do the actual encoding in a lazy way when you call to_message.
        """
        if part:
            self.base.parts.append(part)
        elif filename:
            if not data:
                data = open(filename).read()

            self.base.attach_file(filename, data, content_type, disposition or 'attachment')
        else:
            self.base.attach_text(data, content_type)

        ctype = self.base.content_encoding['Content-Type'][0]

        if ctype and not ctype.startswith('multipart'):
            self.base.content_encoding['Content-Type'] = ('multipart/mixed', {})

    def to_message(self):
        """
        Figures out all the required steps to finally craft the
        message you need and return it.  The resulting message
        is also available as a self.base attribute.

        What is returned is a Python email API message you can
        use with those APIs.  The self.base attribute is the raw
        lamson.encoding.MailBase.
        """
        del self.base.parts[:]

        if self.Body and self.Html:
            self.multipart = True
            self.base.content_encoding['Content-Type'] = ('multipart/alternative', {})

        if self.multipart:
            self.base.body = None
            if self.Body:
                self.base.attach_text(self.Body, 'text/plain')

            if self.Html:
                self.base.attach_text(self.Html, 'text/html')

            for args in self.attachments:
                self._encode_attachment(**args)

        elif self.Body:
            self.base.body = self.Body
            self.base.content_encoding['Content-Type'] = ('text/plain', {})

        elif self.Html:
            self.base.body = self.Html
            self.base.content_encoding['Content-Type'] = ('text/html', {})

        return encoding.to_message(self.base)

    def all_parts(self):
        """
        Returns all the encoded parts.  Only useful for debugging
        or inspecting after calling to_message().
        """
        return self.base.parts

    def keys(self):
        return self.base.keys()

    @property
    def msg(self):
        warnings.warn("The .msg attribute is deprecated, use .base instead.  This will be gone in Lamson 1.0",
                          category=DeprecationWarning, stacklevel=2)
        return self.base

########NEW FILE########
__FILENAME__ = queue
"""
Simpler queue management than the regular mailbox.Maildir stuff.  You
do get a lot more features from the Python library, so if you need
to do some serious surgery go use that.  This works as a good
API for the 90% case of "put mail in, get mail out" queues.
"""

import mailbox
from lamson import mail
import hashlib
import socket
import time
import os
import errno
import logging

# we calculate this once, since the hostname shouldn't change for every
# email we put in a queue
HASHED_HOSTNAME = hashlib.md5(socket.gethostname()).hexdigest()

class SafeMaildir(mailbox.Maildir):
    def _create_tmp(self):
        now = time.time()
        uniq = "%s.M%sP%sQ%s.%s" % (int(now), int(now % 1 * 1e6), os.getpid(),
                                    mailbox.Maildir._count, HASHED_HOSTNAME)
        path = os.path.join(self._path, 'tmp', uniq)
        try:
            os.stat(path)
        except OSError, e:
            if e.errno == errno.ENOENT:
                mailbox.Maildir._count += 1
                try:
                    return mailbox._create_carefully(path)
                except OSError, e:
                    if e.errno != errno.EEXIST:
                        raise
            else:
                raise

        # Fall through to here if stat succeeded or open raised EEXIST.
        raise mailbox.ExternalClashError('Name clash prevented file creation: %s' % path)


class QueueError(Exception):

    def __init__(self, msg, data):
        Exception.__init__(self, msg)
        self._message = msg
        self.data = data


class Queue(object):
    """
    Provides a simplified API for dealing with 'queues' in Lamson.
    It currently just supports maildir queues since those are the 
    most robust, but could implement others later.
    """

    def __init__(self, queue_dir, safe=False, pop_limit=0, oversize_dir=None):
        """
        This gives the Maildir queue directory to use, and whether you want
        this Queue to use the SafeMaildir variant which hashes the hostname
        so you can expose it publicly.

        The pop_limit and oversize_queue both set a upper limit on the mail
        you pop out of the queue.  The size is checked before any Lamson
        processing is done and is based on the size of the file on disk.  The
        purpose is to prevent people from sending 10MB attachments.  If a
        message is over the pop_limit then it is placed into the
        oversize_dir (which should be a maildir).

        The oversize protection only works on pop messages off, not
        putting them in, get, or any other call.  If you use get you can
        use self.oversize to also check if it's oversize manually.
        """
        self.dir = queue_dir

        if safe:
            self.mbox = SafeMaildir(queue_dir)
        else:
            self.mbox = mailbox.Maildir(queue_dir)

        self.pop_limit = pop_limit

        if oversize_dir:
            if not os.path.exists(oversize_dir):
                osmb = mailbox.Maildir(oversize_dir)

            self.oversize_dir = os.path.join(oversize_dir, "new")

            if not os.path.exists(self.oversize_dir):
                os.mkdir(self.oversize_dir)
        else:
            self.oversize_dir = None

    def push(self, message):
        """
        Pushes the message onto the queue.  Remember the order is probably
        not maintained.  It returns the key that gets created.
        """
        return self.mbox.add(str(message))

    def pop(self):
        """
        Pops a message off the queue, order is not really maintained
        like a stack.

        It returns a (key, message) tuple for that item.
        """
        for key in self.mbox.iterkeys():
            over, over_name =  self.oversize(key)

            if over:
                if self.oversize_dir:
                    logging.info("Message key %s over size limit %d, moving to %s.",
                                key, self.pop_limit, self.oversize_dir)
                    os.rename(over_name, os.path.join(self.oversize_dir, key))
                else:
                    logging.info("Message key %s over size limit %d, DELETING (set oversize_dir).", 
                                key, self.pop_limit)
                    os.unlink(over_name)
            else:
                try:
                    msg = self.get(key)
                except QueueError, exc:
                    raise exc
                finally:
                    self.remove(key)
                return key, msg

        return None, None

    def get(self, key):
        """
        Get the specific message referenced by the key.  The message is NOT
        removed from the queue.
        """
        try:
            msg_file = self.mbox.get_file(key)
        except:
            logging.exception("Failed to get file, message gone?")
            return None

        if not msg_file: 
            return None

        msg_data = msg_file.read()

        try:
            return mail.MailRequest(self.dir, None, None, msg_data)
        except:
            logging.exception("Failed to decode message: msg_data: %r", msg_data)
            return None


    def remove(self, key):
        """Removes the queue, but not returned."""
        try:
            self.mbox.remove(key)
        except:
            logging.exception("Failed to remove message from queue.")
    
    def count(self):
        """Returns the number of messages in the queue."""
        return len(self.mbox)

    def clear(self):
        """
        Clears out the contents of the entire queue.
        Warning: This could be horribly inefficient since it
        basically pops until the queue is empty.
        """
        # man this is probably a really bad idea
        while self.count() > 0:
            self.pop()
    
    def keys(self):
        """
        Returns the keys in the queue.
        """
        return self.mbox.keys()

    def oversize(self, key):
        if self.pop_limit:
            file_name = os.path.join(self.dir, "new", key)
            return os.path.getsize(file_name) > self.pop_limit, file_name
        else:
            return False, None




########NEW FILE########
__FILENAME__ = routing

"""
The meat of Lamson, doing all the work that actually takes an email and makes
sure that your code gets it.

The three most important parts for a programmer are the Router variable, the
StateStorage base class, and the @route, @route_like, and @stateless decorators.

The lamson.routing.Router variable (it's not a class, just named like one) is
how the whole system gets to the Router.  It is an instance of RoutingBase and
there's usually only one.

The lamson.routing.StateStorage is what you need to implement if you want Lamson
to store the state in a different way.  By default the lamson.routing.Router
object just uses a default MemoryStorage to do its job.  If you want to use a
custom storage, then in your config/boot.py (or config/testing.py) you would set
lamson.routing.Router.STATE_STORE to what you want to use.

Finally, when you write a state handler, it has functions that act as state
functions for dealing with each state.  To tell the Router what function should
handle what email you use a @route decorator.  To tell the Route that one
function routes the same as another use @route_like.  In the case where a state
function should run on every matching email, just use the @stateless decorator
after a @route or @route_like.

If at any time you need to debug your routing setup just use the lamson routes
command.

Routing Control
===============

To control routing there are a set of decorators that you apply to your
functions.

* @route -- The main routing function that determines what addresses you are
interested in.
* @route_like -- Says that this function routes like another one.
* @stateless -- Indicates this function always runs on each route encountered, and
no state is maintained.
* @nolocking -- Use this if you want this handler to run parallel without any
locking around Lamson internals.  SUPER DANGEROUS, add @stateless as well.
* @state_key_generator -- Used on a function that knows how to make your state
keys for the module, for example if module_name + message.route_to is needed to maintain
state.

It's best to put @route or @route_like as the first decorator, then the others 
after that.

The @state_key_generator is different since it's not intended to go on a handler
but instead on a simple function, so it shouldn't be combined with the others.
"""

from __future__ import with_statement
from functools import wraps
import re
import logging
import sys
import shelve
import threading

ROUTE_FIRST_STATE = 'START'
LOG = logging.getLogger("routing")
DEFAULT_STATE_KEY = lambda mod, msg: mod


class StateStorage(object):
    """
    The base storage class you need to implement for a custom storage
    system.
    """
    def get(self, key, sender):
        """
        You must implement this so that it returns a single string
        of either the state for this combination of arguments, OR
        the ROUTE_FIRST_STATE setting.
        """
        raise NotImplementedError("You have to implement a StateStorage.get.")

    def set(self, key, sender, state):
        """
        Set should take the given parameters and consistently set the state for 
        that combination such that when StateStorage.get is called it gives back
        the same setting.
        """
        raise NotImplementedError("You have to implement a StateStorage.set.")

    def clear(self):
        """
        This should clear ALL states, it is only used in unit testing, so you 
        can have it raise an exception if you want to make this safer.
        """
        raise NotImplementedError("You have to implement a StateStorage.clear for unit testing to work.")


class MemoryStorage(StateStorage):
    """
    The default simplified storage for the Router to hold the states.  This
    should only be used in testing, as you'll lose all your contacts and their
    states if your server shutsdown.  It is also horribly NOT thread safe.
    """
    def __init__(self):
        self.states = {}

    def get(self, key, sender):
        key = self.key(key, sender)
        try:
            return self.states[key]
        except KeyError:
            return ROUTE_FIRST_STATE

    def set(self, key, sender, state):
        key = self.key(key, sender)
        if state == ROUTE_FIRST_STATE:
            try:
                del self.states[key]
            except KeyError:
                pass
        else:
            self.states[key] = state

    def key(self, key, sender):
        return repr([key, sender])

    def clear(self):
        self.states.clear()


class ShelveStorage(MemoryStorage):
    """
    Uses Python's shelve to store the state of the Routers to disk rather than
    in memory like with MemoryStorage.  This will get you going on a small
    install if you need to persist your states (most likely), but if you 
    have a database, you'll need to write your own StateStorage that 
    uses your ORM or database to store.  Consider this an example.

    NOTE: Because of shelve limitations you can only use ASCII encoded keys.
    """
    def __init__(self, database_path):
        """Database path depends on the backing library use by Python's shelve."""
        self.database_path = database_path
        self.lock = threading.RLock()

    def get(self, key, sender):
        """
        This will lock the internal thread lock, and then retrieve from the
        shelf whatever key you request.  If the key is not found then it
        will set (atomically) to ROUTE_FIRST_STATE.
        """
        with self.lock:
            self.states = shelve.open(self.database_path)
            value = super(ShelveStorage, self).get(key.encode('ascii'), sender)
            self.states.close()
            return value

    def set(self, key, sender, state):
        """
        Acquires the self.lock and then sets the requested state in the shelf.
        """
        with self.lock:
            self.states = shelve.open(self.database_path)
            super(ShelveStorage, self).set(key.encode('ascii'), sender, state)
            self.states.close()

    def clear(self):
        """
        Primarily used in the debugging/unit testing process to make sure the
        states are clear.  In production this could be a bad thing.
        """
        with self.lock:
            self.states = shelve.open(self.database_path)
            super(ShelveStorage, self).clear()
            self.states.close()



class RoutingBase(object):
    """
    The self is a globally accessible class that is actually more like a
    glorified module.  It is used mostly internally by the lamson.routing 
    decorators (route, route_like, stateless) to control the routing 
    mechanism.

    It keeps track of the registered routes, their attached functions, the
    order that these routes should be evaluated, any default routing captures,
    and uses the MemoryStorage by default to keep track of the states.

    You can change the storage to another implementation by simple setting:

        self.STATE_STORE = OtherStorage()

    In a config/settings.py file.

    RoutingBase does locking on every write to its internal data (which usually
    only happens during booting and reloading while debugging), and when each
    handler's state function is called.  ALL threads will go through this lock,
    but only as each state is run, so you won't have a situation where the chain
    of state functions will block all the others.  This means that while your
    handler runs nothing will be running, but you have not guarantees about 
    the order of each state function.

    However, this can kill the performance of some kinds of state functions,
    so if you find the need to not have locking, then use the @nolocking 
    decorator and the Router will NOT lock when that function is called.  That
    means while your @nolocking state function is running at least one other
    thread (more if the next ones happen to be @nolocking) could also be
    running.

    It's your job to keep things straight if you do that.

    NOTE: See @state_key_generator for a way to change what the key is to 
    STATE_STORE for different state control options.
    """

    def __init__(self):
        self.REGISTERED = {}
        self.ORDER = []
        self.DEFAULT_CAPTURES = {}
        self.STATE_STORE = MemoryStorage()
        self.HANDLERS = {}
        self.RELOAD = False
        self.LOG_EXCEPTIONS = True
        self.UNDELIVERABLE_QUEUE = None
        self.lock = threading.RLock()
        self.call_lock = threading.RLock()

    def register_route(self, format, func):
        """
        Registers this function func into the routes mapping based on the
        format given.  Format should be a regex string ready to be handed to
        re.compile.
        """
        with self.lock:
            if format in self.REGISTERED:
                self.REGISTERED[format][1].append(func)
            else:
                self.ORDER.append(format)
                self.REGISTERED[format] = (re.compile(format, re.IGNORECASE), [func])

    def match(self, address):
        """
        This is a generator that goes through all the routes and
        yields each match it finds.  It expects you to give it a
        blah@blah.com address, NOT "Joe Blow" <blah@blah.com>.
        """
        for format in self.ORDER:
            regex, functions = self.REGISTERED[format]
            match = regex.match(address)
            if match:
                yield functions, match.groupdict()

    def defaults(self, **captures):
        """
        Updates the defaults for routing captures with the given settings.

        You use this in your handlers or your config/settings.py to set
        common regular expressions you'll have in your @route decorators.
        This saves you typing, but also makes it easy to reconfigure later.

        For example, many times you'll have a single host="..." regex
        for all your application's routes.  Put this in your settings.py
        file using route_defaults={'host': '...'} and you're done.
        """
        with self.lock:
            self.DEFAULT_CAPTURES.update(captures)

    def get_state(self, module_name, message):
        """Returns the state that this module is in for the given message (using its from)."""
        key = self.state_key(module_name, message)
        return self.STATE_STORE.get(key, message.route_from)

    
    def in_state(self, func, message):
        """
        Determines if this function is in the state for the to/from in the
        message.  Doesn't apply to @stateless state handlers.
        """
        state = self.get_state(func.__module__, message)
        return state and state == func.__name__

    def in_error(self, func, message):
        """
        Determines if the this function is in the 'ERROR' state, 
        which is a special state that self puts handlers in that throw
        an exception.
        """
        state = self.get_state(func.__module__, message)
        return state and state == 'ERROR'

    def state_key(self, module_name, message):
        """
        Given a module_name we need to get a state key for, and a
        message that has information to make the key, this function
        calls any registered @state_key_generator and returns that
        as the key.  If none is given then it just returns module_name
        as the key.
        """
        key_func = self.HANDLERS.get(module_name, DEFAULT_STATE_KEY)
        return key_func(module_name, message)

    def set_state(self, module_name, message, state):
        """
        Sets the state of the given module (a string) according to the message to the requested
        state (a string).  This is also how you can force another FSM to a required state.
        """
        key = self.state_key(module_name, message)
        self.STATE_STORE.set(key, message.route_from, state)

    def _collect_matches(self, message, route_to):
        in_state_found = False

        for functions, matchkw in self.match(route_to):
            for func in functions:
                if lamson_setting(func, 'stateless'):
                    yield func, matchkw
                elif not in_state_found and self.in_state(func, message):
                    in_state_found = True
                    yield func, matchkw

    def _enqueue_undeliverable(self, message):
        if self.UNDELIVERABLE_QUEUE:
            LOG.debug("Message to %r from %r undeliverable, putting in undeliverable queue (# of recipients: %d).",
                      message.route_to, message.route_from, len(message.route_to))
            self.UNDELIVERABLE_QUEUE.push(message)
        else:
            LOG.debug("Message to %r from %r didn't match any handlers. (# recipients: %d)",
                      message.route_to, message.route_from, len(message.route_to))

    def deliver(self, message):
        """
        The meat of the whole Lamson operation, this method takes all the
        arguments given, and then goes through the routing listing to figure out
        which state handlers should get the gear.  The routing operates on a
        simple set of rules:

            1) Match on all functions that match the given To in their
            registered format pattern.
            2) Call all @stateless state handlers functions.
            3) Call the first method that's in the right state for the From/To.

        It will log which handlers are being run, and you can use the 'lamson route'
        command to inspect and debug routing problems.

        If you have an ERROR state function, then when your state blows up, it will
        transition to ERROR state and call your function right away.  It will then
        stay in the ERROR state unless you return a different one.
        """
        if self.RELOAD: self.reload()

        called_count = 0

        for routing_on in message.route_to:
            for func, matchkw in self._collect_matches(message, routing_on):
                LOG.debug("Matched %r against %s.", routing_on, func.__name__)

                if lamson_setting(func, 'nolocking'):
                    self.call_safely(func, message,  matchkw)
                else:
                    with self.call_lock:
                        self.call_safely(func, message, matchkw)

                called_count += 1

        if called_count == 0:
            self._enqueue_undeliverable(message)


    def call_safely(self, func, message, kwargs):
        """
        Used by self to call a function and log exceptions rather than
        explode and crash.
        """
        from lamson.server import SMTPError

        try:
            func(message, **kwargs)
            LOG.debug("Message to %s was handled by %s.%s",
                          message.route_to, func.__module__, func.__name__)
        except SMTPError:
            raise
        except:
            if 'ERROR' in dir(sys.modules[func.__module__]):
                self.set_state(func.__module__, message, 'ERROR')

            if self.UNDELIVERABLE_QUEUE:
                self.UNDELIVERABLE_QUEUE.push(message)

            if self.LOG_EXCEPTIONS:
                LOG.exception("!!! ERROR handling %s.%s", func.__module__, func.__name__)
            else:
                raise


    def clear_states(self):
        """Clears out the states for unit testing."""
        with self.lock:
            self.STATE_STORE.clear()

    def clear_routes(self):
        """Clears out the routes for unit testing and reloading."""
        with self.lock:
            self.REGISTERED.clear()
            del self.ORDER[:]

    
    def load(self, handlers):
        """
        Loads the listed handlers making them available for processing.
        This is safe to call multiple times and to duplicate handlers
        listed.
        """
        with self.lock:
            for module in handlers:
                try:
                    __import__(module, globals(), locals())

                    if module not in self.HANDLERS:
                        # they didn't specify a key generator, so use the
                        # default one for now
                        self.HANDLERS[module] = DEFAULT_STATE_KEY
                except:
                    if self.LOG_EXCEPTIONS:
                        LOG.exception("ERROR IMPORTING %r MODULE:" % module)
                    else:
                        raise

    def reload(self):
        """
        Performs a reload of all the handlers and clears out all routes,
        but doesn't touch the internal state.
        """
        with self.lock:
            self.clear_routes()
            for module in sys.modules.keys():
                if module in self.HANDLERS:
                    try:
                        reload(sys.modules[module])
                    except:
                        if self.LOG_EXCEPTIONS:
                            LOG.exception("ERROR RELOADING %r MODULE:" % module)
                        else:
                            raise

Router = RoutingBase()

class route(object):
    """
    The @route decorator is attached to state handlers to configure them in the
    Router so they handle messages for them.  The way this works is, rather than
    just routing working on only messages being sent to a state handler, it also uses
    the state of the sender.  It's like having routing in a web application use
    both the URL and an internal state setting to determine which method to run.

    However, if you'd rather than this state handler process all messages
    matching the @route then tag it @stateless.  This will run the handler 
    no matter what and not change the user's state.
    """

    def __init__(self, format, **captures):
        """
        Sets up the pattern used for the Router configuration.  The format
        parameter is a simple pattern of words, captures, and anything you
        want to ignore.  The captures parameter is a mapping of the words in
        the format to regex that get put into the format.  When the pattern is
        matched, the captures are handed to your state handler as keyword
        arguments.

        For example, if you have:

            @route("(list_name)-(action)@(host)",
                list_name='[a-z]+',
                action='[a-z]+', host='test\.com')
            def STATE(message, list_name=None, action=None, host=None):
                ....

        Then this will be translated so that list_name is replaced with [a-z]+,
        action with [a-z]+, and host with 'test.com' to produce a regex with the
        right format and named captures to that your state handler is called
        with the proper keyword parameters.

        You should also use the Router.defaults() to set default things like the
        host so that you are not putting it into your code.
        """
        self.captures = Router.DEFAULT_CAPTURES.copy()
        self.captures.update(captures)
        self.format = self.parse_format(format, self.captures)

    def __call__(self, func):
        """Returns either a decorator that does a stateless routing or
        a normal routing."""
        self.setup_accounting(func)

        if lamson_setting(func, 'stateless'):
            @wraps(func)
            def routing_wrapper(message, *args, **kw):
                next_state = func(message, *args, **kw)
        else:
            @wraps(func)
            def routing_wrapper(message, *args, **kw):
                next_state = func(message, *args, **kw)

                if next_state:
                    Router.set_state(next_state.__module__, message, next_state.__name__)

        Router.register_route(self.format, routing_wrapper)
        return routing_wrapper

    def __get__(self, obj, of_type=None):
        """
        This is NOT SUPPORTED.  It is here just so that if you try to apply
        this decorator to a class's method it will barf on you.
        """
        raise NotImplementedError("Not supported on methods yet, only module functions.")

    def parse_format(self, format, captures):
        """Does the grunt work of convertion format+captures into the regex."""
        for key in captures:
            format = format.replace("(" + key + ")", "(?P<%s>%s)" % (key, captures[key]))
        return "^" + format + "$"

    def setup_accounting(self, func):
        """Sets up an accounting map attached to the func for routing decorators."""
        attach_lamson_settings(func)
        func._lamson_settings['format'] = self.format
        func._lamson_settings['captures'] = self.captures


def lamson_setting(func, key):
    """Simple way to get the lamson setting off the function, or None."""
    return func._lamson_settings.get(key)


def has_lamson_settings(func):
    return "_lamson_settings" in func.__dict__

def assert_lamson_settings(func):
    """Used to make sure that the func has been setup by a routing decorator."""
    assert has_lamson_settings(func), "Function %s has not be setup with a @route first." % func.__name__


def attach_lamson_settings(func):
    """Use this to setup the _lamson_settings if they aren't already there."""
    if '_lamson_settings' not in func.__dict__:
        func._lamson_settings = {}


class route_like(route):
    """
    Many times you want your state handler to just accept mail like another
    handler.  Use this, passing in the other function.  It even works across
    modules.
    """
    def __init__(self, func):
        assert_lamson_settings(func)
        self.format = func._lamson_settings['format']
        self.captures = func._lamson_settings['captures']


def stateless(func):
    """
    This simple decorator is attached to a handler to indicate to the
    Router.deliver() method that it does NOT maintain state or care about it.
    This is how you create a handler that processes all messages matching the
    given format+captures in a @route.

    Another way to think about a @stateless handler is that it is a passthrough
    handler that does its processing and then passes the results on to others.

    Stateless handlers are NOT guaranteed to run before the handler with state.
    """
    if has_lamson_settings(func):
        assert not lamson_setting(func, 'format'), "You must use @stateless AFTER @route or @route_like."
    
    attach_lamson_settings(func)
    func._lamson_settings['stateless'] = True

    return func

def nolocking(func):
    """
    Normally lamson.routing.Router has a lock around each call to all handlers
    to prevent them from stepping on eachother.  It's assumed that 95% of the
    time this is what you want, so it's the default.  You probably want
    everything to go in order and not step on other things going off from other
    threads in the system.

    However, sometimes you know better what you are doing and this is where
    @nolocking comes in.  Put this decorator on your state functions that you
    don't care about threading issues or that you have found a need to 
    manually tune, and it will run it without any locks.
    """
    attach_lamson_settings(func)
    func._lamson_settings['nolocking'] = True
    return func

def state_key_generator(func):
    """
    Used to indicate that a function in your handlers should be used
    to determine what they key is for state storage.  It should be a 
    function that takes the module_name and message being worked on
    and returns a string.
    """
    Router.HANDLERS[func.__module__] = func
    return func

########NEW FILE########
__FILENAME__ = server
"""
The majority of the server related things Lamson needs to run, like receivers, 
relays, and queue processors.
"""

import smtplib
import smtpd
import asyncore
import threading
import socket
import logging
from lamson import queue, mail, routing
import time
import traceback
from lamson.bounce import PRIMARY_STATUS_CODES, SECONDARY_STATUS_CODES, COMBINED_STATUS_CODES


def undeliverable_message(raw_message, failure_type):
    """
    Used universally in this file to shove totally screwed messages
    into the routing.Router.UNDELIVERABLE_QUEUE (if it's set).
    """
    if routing.Router.UNDELIVERABLE_QUEUE:
        key = routing.Router.UNDELIVERABLE_QUEUE.push(raw_message)

        logging.error("Failed to deliver message because of %r, put it in "
                      "undeliverable queue with key %r", failure_type, key)

class SMTPError(Exception):
    """
    You can raise this error when you want to abort with a SMTP error code to
    the client.  This is really only relevant when you're using the
    SMTPReceiver and the client understands the error.

    If you give a message than it'll use that, but it'll also produce a
    consistent error message based on your code.  It uses the errors in
    lamson.bounce to produce them.
    """
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or self.error_for_code(code)

        Exception.__init__(self, "%d %s" % (self.code, self.message))

    def error_for_code(self, code):
        primary, secondary, tertiary = str(code)
        
        primary = PRIMARY_STATUS_CODES.get(primary, "")
        secondary = SECONDARY_STATUS_CODES.get(secondary, "")
        combined = COMBINED_STATUS_CODES.get(primary + secondary, "")

        return " ".join([primary, secondary, combined]).strip()


class Relay(object):
    """
    Used to talk to your "relay server" or smart host, this is probably the most 
    important class in the handlers next to the lamson.routing.Router.
    It supports a few simple operations for sending mail, replying, and can
    log the protocol it uses to stderr if you set debug=1 on __init__.
    """
    def __init__(self, host='127.0.0.1', port=25, username=None, password=None,
                 ssl=False, starttls=False, debug=0):
        """
        The hostname and port we're connecting to, and the debug level (default to 0).
        Optional username and password for smtp authentication.
        If ssl is True smtplib.SMTP_SSL will be used.
        If starttls is True (and ssl False), smtp connection will be put in TLS mode.
        It does the hard work of delivering messages to the relay host.
        """
        self.hostname = host
        self.port = port
        self.debug = debug
        self.username = username
        self.password = password
        self.ssl = ssl
        self.starttls = starttls

    def configure_relay(self, hostname):
        if self.ssl:
            relay_host = smtplib.SMTP_SSL(hostname, self.port)
        else:
            relay_host = smtplib.SMTP(hostname, self.port)

        relay_host.set_debuglevel(self.debug)

        if self.starttls:
            relay_host.starttls()
        if self.username and self.password:
            relay_host.login(self.username, self.password)

        assert relay_host, 'Code error, tell Zed.'
        return relay_host

    def deliver(self, message, To=None, From=None):
        """
        Takes a fully formed email message and delivers it to the
        configured relay server.

        You can pass in an alternate To and From, which will be used in the
        SMTP send lines rather than what's in the message.
        """
        recipient = To or message['To']
        sender = From or message['From']

        hostname = self.hostname or self.resolve_relay_host(recipient)

        try:
            relay_host = self.configure_relay(hostname)
        except socket.error:
            logging.exception("Failed to connect to host %s:%d" % (hostname, self.port))
            return

        try:
            relay_host.sendmail(sender, recipient, str(message))
        except:
            logging.exception("Failed to send message to host %s:%s" % (hostname, self.port))

        relay_host.quit()

    def resolve_relay_host(self, To):
        import DNS
        address, target_host = To.split('@')
        mx_hosts = DNS.mxlookup(target_host)

        if not mx_hosts:
            logging.debug("Domain %r does not have an MX record, using %r instead.", target_host, target_host)
            return target_host
        else:
            logging.debug("Delivering to MX record %r for target %r", mx_hosts[0], target_host)
            return mx_hosts[0][1]


    def __repr__(self):
        """Used in logging and debugging to indicate where this relay goes."""
        return "<Relay to (%s:%d)>" % (self.hostname, self.port)


    def reply(self, original, From, Subject, Body):
        """Calls self.send but with the from and to of the original message reversed."""
        self.send(original['from'], From=From, Subject=Subject, Body=Body)

    def send(self, To, From, Subject, Body):
        """
        Does what it says, sends an email.  If you need something more complex
        then look at lamson.mail.MailResponse.
        """
        msg = mail.MailResponse(To=To, From=From, Subject=Subject, Body=Body)
        self.deliver(msg)



class SMTPReceiver(smtpd.SMTPServer):
    """Receives emails and hands it to the Router for further processing."""

    def __init__(self, host='127.0.0.1', port=8825):
        """
        Initializes to bind on the given port and host/ipaddress.  Typically
        in deployment you'd give 0.0.0.0 for "all internet devices" but consult
        your operating system.

        This uses smtpd.SMTPServer in the __init__, which means that you have to 
        call this far after you use python-daemonize or else daemonize will
        close the socket.
        """
        self.host = host
        self.port = port
        smtpd.SMTPServer.__init__(self, (self.host, self.port), None)

    def start(self):
        """
        Kicks everything into gear and starts listening on the port.  This
        fires off threads and waits until they are done.
        """
        logging.info("SMTPReceiver started on %s:%d." % (self.host, self.port))
        self.poller = threading.Thread(target=asyncore.loop,
                kwargs={'timeout':0.1, 'use_poll':True})
        self.poller.start()

    def process_message(self, Peer, From, To, Data):
        """
        Called by smtpd.SMTPServer when there's a message received.
        """

        try:
            logging.debug("Message received from Peer: %r, From: %r, to To %r." % (Peer, From, To))
            routing.Router.deliver(mail.MailRequest(Peer, From, To, Data))
        except SMTPError, err:
            # looks like they want to return an error, so send it out
            return str(err)
            undeliverable_message(Data, "Handler raised SMTPError on purpose: %s" % err)
        except:
            logging.exception("Exception while processing message from Peer: %r, From: %r, to To %r." %
                          (Peer, From, To))
            undeliverable_message(Data, "Error in message %r:%r:%r, look in logs." % (Peer, From, To))


    def close(self):
        """Doesn't do anything except log who called this, since nobody should.  Ever."""
        logging.error(traceback.format_exc())


class QueueReceiver(object):
    """
    Rather than listen on a socket this will watch a queue directory and
    process messages it recieves from that.  It works in almost the exact
    same way otherwise.
    """

    def __init__(self, queue_dir, sleep=10, size_limit=0, oversize_dir=None):
        """
        The router should be fully configured and ready to work, the
        queue_dir can be a fully qualified path or relative.
        """
        self.queue = queue.Queue(queue_dir, pop_limit=size_limit,
                                 oversize_dir=oversize_dir)
        self.queue_dir = queue_dir
        self.sleep = sleep

    def start(self, one_shot=False):
        """
        Start simply loops indefinitely sleeping and pulling messages
        off for processing when they are available.

        If you give one_shot=True it will run once rather than do a big
        while loop with a sleep.
        """

        logging.info("Queue receiver started on queue dir %s" %
                     (self.queue_dir))
        logging.debug("Sleeping for %d seconds..." % self.sleep)

        inq = self.queue

        while True:
            keys = inq.keys()

            for key in keys:
                msg = inq.get(key)

                if msg:
                    logging.debug("Pulled message with key: %r off", key)
                    self.process_message(msg)
                    logging.debug("Removed %r key from queue.", key)

	        inq.remove(key)

            if one_shot: 
                return
            else:
                time.sleep(self.sleep)

    def process_message(self, msg):
        """
        Exactly the same as SMTPReceiver.process_message but just designed for the queue's
        quirks.
        """

        try:
            Peer = self.queue_dir # this is probably harmless but I should check it
            From = msg['from']
            To = [msg['to']]

            logging.debug("Message received from Peer: %r, From: %r, to To %r." % (Peer, From, To))
            routing.Router.deliver(msg)
        except SMTPError, err:
            # looks like they want to return an error, so send it out
            logging.exception("Raising SMTPError when running in a QueueReceiver is unsupported.")
            undeliverable_message(msg.original, err.message)
        except:
            logging.exception("Exception while processing message from Peer: "
                              "%r, From: %r, to To %r." % (Peer, From, To))
            undeliverable_message(msg.original, "Router failed to catch exception.")






########NEW FILE########
__FILENAME__ = spam
"""
Uses the SpamBayes system to perform filtering and classification
of email.  It's designed so that you attach a single decorator
to the state functions you need to be "spam free", and then use the
lamson.spam.Filter code to do training.

SpamBayes comes with extensive command line tools for processing
maildir and mbox for spam.  A good way to train SpamBayes is to 
take mail that you know is spam and stuff it into a maildir, then
periodically use the SpamBayes tools to train from that.
"""

from functools import wraps
from lamson import queue
from spambayes import hammie, Options, storage
import os
import logging

class Filter(object):
    """
    This code implements simple filtering and is taken from the
    SpamBayes documentation.
    """
    def __init__(self, storage_file, config):
        options = Options.options
        options["Storage", "persistent_storage_file"] = storage_file
        options.merge_files(['/etc/hammierc', os.path.expanduser(config)])

        self.include_trained = Options.options["Headers", "include_trained"]
        self.dbname, self.usedb = storage.database_type([])

        self.mode = None
        self.h = None

        assert not Options.options["Hammie", "train_on_filter"], "Cannot train_on_filter."

    def open(self, mode):
        assert not self.h, "Cannot reopen, close first."
        assert not self.mode, "Mode should be None on open, bad state."
        assert mode in ['r', 'c'], "Must give a valid mode: r, c."

        self.mode = mode
        self.h = hammie.open(self.dbname, self.usedb, self.mode)

    def close(self):
        if not self.h: return

        assert self.mode, "Mode was not set."
        assert self.mode in ['r','c'], "self.mode was not r or c. Bad state."

        if self.mode == 'c':
            self.h.store()
            self.h.close()

        self.h = None
        self.mode = None


    def filter(self, msg):
        self.open('r')
        result = self.h.filter(msg)
        self.close()
        return result

    def train_ham(self, msg):
        self.open('c')
        self.h.train_ham(msg, self.include_trained)
        self.close()

    def train_spam(self, msg):
        self.open('c')
        self.h.train_spam(msg, self.include_trained)
        self.close()

    def untrain_ham(self, msg):
        self.open('c')
        self.h.untrain_ham(msg)
        self.close()

    def untrain_spam(self, msg):
        self.open('c')
        self.h.untrain_spam(msg)
        self.close()




class spam_filter(object):
    """
    This is a decorator you attach to states that should be protected from spam.
    You use it by doing:

        @spam_filter(ham_db, rcfile, spam_dump_queue, next_state=SPAMMING)

    Where ham_db is the path to your hamdb configuration, rcfile is the 
    SpamBayes config, and spam_dump_queue is where this filter should
    dump spam it detects.

    The next_state argument is optional, defaulting to None, but if you use
    it then Lamson will transition that user into that state.  Use it to mark
    that address as a spammer and to ignore their emails or do something
    fancy with them.
    """

    def __init__(self, storage, config, spam_queue, next_state=None):
        self.storage = storage
        self.config = config
        self.spam_queue = spam_queue
        self.next_state = next_state
        assert self.next_state, "You must give next_state function."

        if not os.path.exists(self.storage):
            logging.warn("SPAM filter for %r does not have a valid storage path, it'll still run but won't do anything.",
                        (self.storage, self.config, self.spam_queue,
                         self.next_state.__name__))
            self.functioning = False
        else:
            self.functioning = True

    def __call__(self, fn):
        @wraps(fn)
        def category_wrapper(message, *args, **kw):
            if self.functioning:
                if self.spam(message.to_message()):
                    self.enqueue_as_spam(message.to_message())
                    return self.next_state
                else:
                    return fn(message, *args, **kw)
            else:
                return fn(message, *args, **kw)
        return category_wrapper

    def spam(self, message):
        """Determines if the message is spam or not."""
        spfilter = Filter(self.storage, self.config)
        spfilter.filter(message)

        if 'X-Spambayes-Classification' in message:
            return message['X-Spambayes-Classification'].startswith('spam')
        else:
            return False

    def enqueue_as_spam(self, message):
        """Drops the message into the configured spam queue."""
        outq = queue.Queue(self.spam_queue)
        outq.push(str(message))


########NEW FILE########
__FILENAME__ = testing
"""
A bag of generally useful things when writing unit tests for your Lamson server.
The most important things are the spelling function and using the
TestConversation vs. RouterConversation to talk to your server.

The TestConversation will use the lamson.server.Relay you have configured to
talk to your actual running Lamson server.  Since by default Lamson reloads each
file you change it will work to run your tests.

However, this isn't that fast, doesn't give you coverage analysis, and doesn't
let you test the results.  For that you use RouterConversation to do the exact
same API (they should be interchangeable) but rather than talk to a running
server through the relay, it just runs all the messages through the router
directly. 

This is faster and will give you code coverage as well as make sure that all the
modules (not just your handlers) will get reloaded.

The spelling function will use PyEnchant to spell check a string.  If it finds
any errors it prints them out, and returns False.
"""


from lamson import server, utils, routing, mail
from lamson.queue import Queue
from nose.tools import assert_equal
import re
import logging

TEST_QUEUE = "run/queue"


def spelling(file_name, contents, language="en_US"):
    """
    You give it a file_name and the contents of that file and it tells you
    if it's spelled correctly.  The reason you give it contents is that you
    will typically run a template through the render process, so spelling 
    can't just load a file and check it.

    It assumes you have PyEnchant installed correctly and configured 
    in your config/testing.py file.  Use "lamson spell" to make sure it
    works right.
    """
    try:
        from enchant.checker import SpellChecker 
        from enchant.tokenize import EmailFilter, URLFilter 
    except:
        print "Failed to load PyEnchant.  Make sure it's installed and lamson spell works."
        return True

    failures = 0
    chkr = SpellChecker(language, filters=[EmailFilter, URLFilter]) 
    chkr.set_text(contents)
    for err in chkr:
        print "%s: %s \t %r" % (file_name, err.word, contents[err.wordpos-20:err.wordpos+20])
        failures += 1

    if failures:
        print "You have %d spelling errors in %s.  Run lamson spell.." % (failures, file_name)
        return False
    else:
        return True




def relay(hostname="127.0.0.1", port=8824):
    """Wires up a default relay on port 8824 (the default lamson log port)."""
    return server.Relay(hostname, port, debug=0)


def queue(queue_dir=TEST_QUEUE):
    """Creates a queue for you to analyze the results of a send, uses the
    TEST_QUEUE setting in settings.py if that exists, otherwise defaults to
    run/queue."""
    return Queue(queue_dir)


def clear_queue(queue_dir=TEST_QUEUE):
    """Clears the default test queue out, as created by lamson.testing.queue."""
    queue(queue_dir).clear()


def delivered(pattern, to_queue=None):
    """
    Checks that a message with that patter is delivered, and then returns it.

    It does this by searching through the queue directory and finding anything that
    matches the pattern regex.
    """
    inq = to_queue or queue()
    for key in inq.keys():
        msg = inq.get(key)
        if not msg:
            # no messages in the queue
            return False

        regp = re.compile(pattern)
        if regp.search(str(msg)):
            msg = inq.get(key)
            return msg

    # didn't find anything
    return False


class TestConversation(object):
    """
    Used to easily do conversations with an email server such that you
    send a message and then expect certain responses.
    """

    def __init__(self, relay_to_use, From, Subject):
        """
        This creates a set of default values for the conversation so that you
        can easily send most basic message.  Each method lets you override the
        Subject and Body when you send.
        """
        self.relay = relay_to_use
        self.From = From
        self.Subject = Subject

    def begin(self):
        """Clears out the queue and Router states so that you have a fresh start."""
        clear_queue()
        routing.Router.clear_states()

    def deliver(self, To, From, Subject, Body):
        """Delivers it to the relay."""
        self.relay.send(To, From, Subject, Body)

    def say(self, To, Body, expect=None, Subject=None):
        """
        Say something to To and expect a reply with a certain address.
        It returns the message expected or None.
        """
        msg = None

        self.deliver(To, self.From, Subject or self.Subject, Body)
        if expect:
            msg = delivered(expect)
            if not msg:
                print "MESSAGE IN QUEUE:"
                inq = queue()
                for key in inq.keys():
                    print "-----"
                    print inq.get(key)

            assert msg, "Expected %r when sending to %r with '%s:%s' message." % (expect, 
                                          To, self.Subject or Subject, Body)
        return msg

class RouterConversation(TestConversation):
    """
    An implementation of TestConversation that routes the messages
    internally to the Router, rather than connecting with a relay.
    Use it in tests that are not integration tests.
    """
    def __init__(self, From, Subject):
        self.From = From
        self.Subject = Subject

    def deliver(self, To, From, Subject, Body):
        """Overrides TestConversation.deliver to do it internally."""
        sample = mail.MailResponse(From=From, To=To, Subject=Subject, Body=Body)
        msg = mail.MailRequest('localhost', sample['From'], sample['To'], str(sample))
        routing.Router.deliver(msg)



def assert_in_state(module, To, From, state):
    """
    Makes sure a user is in a certain state for a certain user.
    Use these sparingly, since every time you change your handler you'll
    have to change up your tests.  It's better to focus on the interaction
    with your handler and expected outputs.
    """
    fake = {'to': To}
    state_key = routing.Router.state_key(module, fake)
    assert_equal(routing.Router.STATE_STORE.get(state_key, From), state)



########NEW FILE########
__FILENAME__ = utils
"""
Mostly utility functions Lamson uses internally that don't
really belong anywhere else in the modules.  This module
is kind of a dumping ground, so if you find something that
can be improved feel free to work up a patch.
"""

from lamson import server, routing
import sys, os
import logging
import daemon

try:
    from daemon import pidlockfile 
except:
    from lockfile import pidlockfile 

import imp
import signal


def import_settings(boot_also, from_dir=None, boot_module="config.boot"):
    """Used to import the settings in a Lamson project."""
    if from_dir:
        sys.path.append(from_dir)

    # Assumes that the settings.py has the same parent module as boot.py
    # ie config.boot -> config.settings (just changes the name of the last module)
    settings_module = ".".join( [ boot_module.rsplit(".", 1)[0], "settings" ] )

    settings = __import__(settings_module, globals(), locals()).settings

    if boot_also:
        __import__(boot_module, globals(), locals())

    return settings


def daemonize(pid, chdir, chroot, umask, files_preserve=None, do_open=True):
    """
    Uses python-daemonize to do all the junk needed to make a
    server a server.  It supports all the features daemonize
    has, except that chroot probably won't work at all without
    some serious configuration on the system.
    """
    context = daemon.DaemonContext()
    context.pidfile = pidlockfile.PIDLockFile(pid)
    context.stdout = open(os.path.join(chdir, "logs/lamson.out"),"a+")                                                                                                       
    context.stderr = open(os.path.join(chdir, "logs/lamson.err"),"a+")                                                                                                       
    context.files_preserve = files_preserve or []
    context.working_directory = os.path.expanduser(chdir)

    if chroot: 
        context.chroot_directory = os.path.expanduser(chroot)
    if umask != False:
        context.umask = umask

    if do_open:
        context.open()

    return context

def drop_priv(uid, gid):
    """
    Changes the uid/gid to the two given, you should give utils.daemonize
    0,0 for the uid,gid so that it becomes root, which will allow you to then
    do this.
    """
    logging.debug("Dropping to uid=%d, gid=%d", uid, gid)
    daemon.daemon.change_process_owner(uid, gid)
    logging.debug("Now running as uid=%d, gid=%d", os.getgid(), os.getuid())



def make_fake_settings(host, port):
    """
    When running as a logging server we need a fake settings module to work with
    since the logging server can be run in any directory, so there may not be
    a config/settings.py file to import.
    """
    logging.basicConfig(filename="logs/logger.log", level=logging.DEBUG)
    routing.Router.load(['lamson.handlers.log', 'lamson.handlers.queue'])
    settings = imp.new_module('settings')
    settings.receiver = server.SMTPReceiver(host, port)
    settings.relay = None
    logging.info("Logging mode enabled, will not send email to anyone, just log.")

    return settings

def check_for_pid(pid, force):
    """Checks if a pid file is there, and if it is sys.exit.  If force given
    then it will remove the file and not exit if it's there."""
    if os.path.exists(pid):
        if not force:
            print "PID file %s exists, so assuming Lamson is running.  Give -FORCE to force it to start." % pid
            sys.exit(1)
            return # for unit tests mocking sys.exit
        else:
            os.unlink(pid)


def start_server(pid, force, chroot, chdir, uid, gid, umask, settings_loader, debug):
    """
    Starts the server by doing a daemonize and then dropping priv
    accordingly.  It will only drop to the uid/gid given if both are given.
    """
    check_for_pid(pid, force)

    if not debug:
        daemonize(pid, chdir, chroot, umask, files_preserve=[])

    sys.path.append(os.getcwd())

    settings = settings_loader()

    if uid and gid:
        drop_priv(uid, gid) 
    elif uid or gid:
        logging.warning("You probably meant to give a uid and gid, but you gave: uid=%r, gid=%r.  Will not change to any user.", uid, gid)

    settings.receiver.start()

    if debug:
        print "Lamson started in debug mode. ctrl-c to quit..."
        import time
        try:
            while True:
                time.sleep(100000)
        except KeyboardInterrupt:
            # hard quit, since receiver starts a new thread. dirty but works
            os._exit(1)

########NEW FILE########
__FILENAME__ = version
VERSION={'version': '1.3.4', 'rev': ['98073386',
'98073386886851f6e68387cf77712d8e99109fe4']}

########NEW FILE########
__FILENAME__ = view
"""
These are helper functions that make it easier to work with either
Jinja2 or Mako templates.  You MUST configure it by setting
lamson.view.LOADER to one of the template loaders in your config.boot
or config.testing.

After that these functions should just work.
"""

from lamson import mail
import email
import warnings

LOADER = None

def load(template):
    """
    Uses the registered loader to load the template you ask for.
    It assumes that your loader works like Jinja2 or Mako in that
    it has a LOADER.get_template() method that returns the template.
    """
    assert LOADER, "You haven't set lamson.view.LOADER to a loader yet."
    return LOADER.get_template(template)


def render(variables, template):
    """
    Takes the variables given and renders the template for you.
    Assumes the template returned by load() will have a .render()
    method that takes the variables as a dict.

    Use this if you just want to render a single template and don't
    want it to be a message.  Use render_message if the contents
    of the template are to be interpreted as a message with headers
    and a body.
    """
    return load(template).render(variables)


def respond(variables, Body=None, Html=None, **kwd):
    """
    Does the grunt work of cooking up a MailResponse that's based
    on a template.  The only difference from the lamson.mail.MailResponse
    class and this (apart from variables passed to a template) are that
    instead of giving actual Body or Html parameters with contents,
    you give the name of a template to render.  The kwd variables are
    the remaining keyword arguments to MailResponse of From/To/Subject.

    For example, to render a template for the body and a .html for the Html
    attachment, and to indicate the From/To/Subject do this:

        msg = view.respond(locals(), Body='template.txt', 
                          Html='template.html',
                          From='test@test.com',
                          To='receiver@test.com',
                          Subject='Test body from "%(dude)s".')

    In this case you're using locals() to gather the variables needed for
    the 'template.txt' and 'template.html' templates.  Each template is
    setup to be a text/plain or text/html attachment.  The From/To/Subject
    are setup as needed.  Finally, the locals() are also available as
    simple Python keyword templates in the From/To/Subject so you can pass
    in variables to modify those when needed (as in the %(dude)s in Subject).
    """

    assert Body or Html, "You need to give either the Body or Html template of the mail."

    for key in kwd:
        kwd[key] = kwd[key] % variables
    
    msg = mail.MailResponse(**kwd)

    if Body:
        msg.Body = render(variables, Body)
    
    if Html:
        msg.Html = render(variables, Html)

    return msg


def attach(msg, variables, template, filename=None, content_type=None,
           disposition=None):
    """
    Useful for rendering an attachment and then attaching it to the message
    given.  All the parameters that are in lamson.mail.MailResponse.attach
    are there as usual.
    """
    data = render(variables, template)

    msg.attach(filename=filename, data=data, content_type=content_type,
               disposition=disposition)


########NEW FILE########
__FILENAME__ = settings
# This file contains python variables that configure Lamson for email processing.
import logging

relay_config = {'host': 'localhost', 'port': 8825}

receiver_config = {'host': 'localhost', 'port': 8823}

handlers = []

router_defaults = {'host': 'localhost'}

template_config = {'dir': 'lamson_tests', 'module': '.'}

BLOG_BASE="app/data/posts"

# this is for when you run the config.queue boot
queue_config = {'queue': 'run/deferred', 'sleep': 10}

queue_handlers = []


########NEW FILE########
__FILENAME__ = testing
from config import settings
from lamson import view
from lamson.routing import Router
from lamson.server import Relay
import jinja2
import logging
import logging.config
import os

# configure logging to go to a log file
logging.config.fileConfig("tests/config/logging.conf")

# the relay host to actually send the final message to (set debug=1 to see what
# the relay is saying to the log server).
settings.relay = Relay(host=settings.relay_config['host'], 
                       port=settings.relay_config['port'], debug=0)


settings.receiver = None

Router.defaults(**settings.router_defaults)
Router.load(settings.handlers + settings.queue_handlers)
Router.RELOAD=False
Router.LOG_EXCEPTIONS=False

view.LOADER = jinja2.Environment(loader=jinja2.PackageLoader('lamson_tests', 'templates'))

# if you have pyenchant and enchant installed then the template tests will do
# spell checking for you, but you need to tell pyenchant where to find itself
if 'PYENCHANT_LIBRARY_PATH' not in os.environ:
    os.environ['PYENCHANT_LIBRARY_PATH'] = '/opt/local/lib/libenchant.dylib'


########NEW FILE########
__FILENAME__ = bounce_filtered_mod
from lamson.routing import route, route_like
from lamson.bounce import bounce_to


SOFT_RAN=False
HARD_RAN=False

@route(".+")
def SOFT_BOUNCED(message):
    global SOFT_RAN
    SOFT_RAN=True
    # remember to transition back to START or the mailer daemon 
    # at that host will be put in a bad state
    return START

@route(".+")
def HARD_BOUNCED(message):
    global HARD_RAN
    HARD_RAN=True
    # remember to transition back to START or the mailer daemon 
    # at that host will be put in a bad state
    return START

@route("(anything)@(host)", anything=".+", host=".+")
@bounce_to(soft=SOFT_BOUNCED, hard=HARD_BOUNCED)
def START(message, **kw):
    return END

@route_like(START)
def END(message, *kw):
    pass



########NEW FILE########
__FILENAME__ = bounce_tests
from nose.tools import *
from lamson import mail
from lamson.routing import Router


def test_bounce_analyzer_on_bounce():
    bm = mail.MailRequest(None,None,None, open("tests/bounce.msg").read())
    assert bm.is_bounce()
    assert bm.bounce
    assert bm.bounce.score == 1.0
    assert bm.bounce.probable()
    assert_equal(bm.bounce.primary_status, (5, u'Permanent Failure'))
    assert_equal(bm.bounce.secondary_status, (1, u'Addressing Status'))
    assert_equal(bm.bounce.combined_status, (11, u'Bad destination mailbox address'))

    assert bm.bounce.is_hard()
    assert_equal(bm.bounce.is_hard(), not bm.bounce.is_soft())

    assert_equal(bm.bounce.remote_mta, u'gmail-smtp-in.l.google.com')
    assert_equal(bm.bounce.reporting_mta, u'mail.zedshaw.com')
    assert_equal(bm.bounce.final_recipient,
                 u'asdfasdfasdfasdfasdfasdfewrqertrtyrthsfgdfgadfqeadvxzvz@gmail.com')
    assert_equal(bm.bounce.diagnostic_codes[0], u'550-5.1.1')
    assert_equal(bm.bounce.action, 'failed')
    assert 'Content-Description-Parts' in bm.bounce.headers

    assert bm.bounce.error_for_humans()

def test_bounce_analyzer_on_regular():
    bm = mail.MailRequest(None,None,None, open("tests/signed.msg").read())
    assert not bm.is_bounce()
    assert bm.bounce
    assert bm.bounce.score == 0.0
    assert not bm.bounce.probable()
    assert_equal(bm.bounce.primary_status, (None, None))
    assert_equal(bm.bounce.secondary_status, (None, None))
    assert_equal(bm.bounce.combined_status, (None, None))

    assert not bm.bounce.is_hard()
    assert not bm.bounce.is_soft()

    assert_equal(bm.bounce.remote_mta, None)
    assert_equal(bm.bounce.reporting_mta, None)
    assert_equal(bm.bounce.final_recipient, None)
    assert_equal(bm.bounce.diagnostic_codes, [None, None])
    assert_equal(bm.bounce.action, None)


def test_bounce_to_decorator():
    import bounce_filtered_mod
    msg = mail.MailRequest(None,None,None, open("tests/bounce.msg").read())

    Router.deliver(msg)
    assert Router.in_state(bounce_filtered_mod.START, msg)
    assert bounce_filtered_mod.HARD_RAN, "Hard bounce state didn't actually run: %r" % msg.route_to

    msg.bounce.primary_status = (4, u'Persistent Transient Failure')
    Router.clear_states()
    Router.deliver(msg)
    assert Router.in_state(bounce_filtered_mod.START, msg)
    assert bounce_filtered_mod.SOFT_RAN, "Soft bounce didn't actually run."

    msg = mail.MailRequest(None, None, None, open("tests/signed.msg").read())
    Router.clear_states()
    Router.deliver(msg)
    assert Router.in_state(bounce_filtered_mod.END, msg), "Regular messages aren't delivering."


def test_bounce_getting_original():
    msg = mail.MailRequest(None,None,None, open("tests/bounce.msg").read())
    msg.is_bounce()

    assert msg.bounce.notification
    assert msg.bounce.notification.body

    assert msg.bounce.report

    for part in msg.bounce.report:
        assert [(k,part[k]) for k in part]
        # these are usually empty, but might not be.  they are in our test
        assert not part.body

    assert msg.bounce.original
    assert_equal(msg.bounce.original['to'], msg.bounce.final_recipient)
    assert msg.bounce.original.body


def test_bounce_no_headers_error_message():
    msg = mail.MailRequest(None, None, None, "Nothing")
    msg.is_bounce()
    assert_equal(msg.bounce.error_for_humans(), 'No status codes found in bounce message.')


########NEW FILE########
__FILENAME__ = command_tests
from lamson import commands, utils, mail, routing, encoding
from lamson.testing import spelling
from nose.tools import *
import os
import shutil
from mock import *
import sys
import imp


def setup():
    if os.path.exists("run/fake.pid"):
        os.unlink("run/fake.pid")

def teardown():
    if os.path.exists("run/fake.pid"):
        os.unlink("run/fake.pid")

def make_fake_pid_file():
    f = open("run/fake.pid","w")
    f.write("0")
    f.close()


def test_send_command():
    commands.send_command(sender='test@localhost',
                           to='test@localhost',
                           body='Test body',
                           subject='Test subject',
                           attach='setup.py',
                           port=8899,debug=0)

def test_status_command():
    commands.status_command(pid='run/log.pid')
    commands.status_command(pid='run/donotexist.pid')


@patch('sys.exit', new=Mock())
def test_help_command():
    commands.help_command()
    commands.help_command(**{'for': 'status'})

    # test with an invalid command
    commands.help_command(**{'for': 'invalid_command'})
    assert sys.exit.called

@patch('lamson.queue.Queue')
@patch('sys.exit', new=Mock())
def test_queue_command(MockQueue):
    mq = MockQueue()
    mq.get.return_value = "A sample message"
    mq.keys.return_value = ["key1","key2"]
    mq.pop.return_value = ('key1', 'message1')
    mq.count.return_value = 1
    
    commands.queue_command(pop=True)
    assert mq.pop.called
    
    commands.queue_command(get='somekey')
    assert mq.get.called
    
    commands.queue_command(remove='somekey')
    assert mq.remove.called
    
    commands.queue_command(clear=True)
    assert mq.clear.called
    
    commands.queue_command(keys=True)
    assert mq.keys.called

    commands.queue_command(count=True)
    assert mq.count.called

    commands.queue_command()
    assert sys.exit.called


@patch('sys.exit', new=Mock())
def test_gen_command():
    project = 'tests/testproject'
    if os.path.exists(project):
        shutil.rmtree(project)

    commands.gen_command(project=project)
    assert os.path.exists(project)

    # test that it exits if the project exists
    commands.gen_command(project=project)
    assert sys.exit.called

    sys.exit.reset_mock()
    commands.gen_command(project=project, FORCE=True)
    assert not sys.exit.called

    shutil.rmtree(project)


def test_routes_command():
    commands.routes_command(TRAILING=['lamson.handlers.log',
                                      'lamson.handlers.queue'])

    # test with the -test option
    commands.routes_command(TRAILING=['lamson.handlers.log',
                                      'lamson.handlers.queue'],
                            test="anything@localhost")

    # test with the -test option but no matches
    routing.Router.clear_routes()
    commands.routes_command(TRAILING=[], test="anything@localhost")


@patch('sys.exit', new=Mock())
@patch('lamson.utils.daemonize', new=Mock())
@patch('lamson.server.SMTPReceiver')
def test_log_command(MockSMTPReceiver):
    ms = MockSMTPReceiver()
    ms.start.function()

    setup()  # make sure it's clear for fake.pid
    commands.log_command(pid="run/fake.pid")
    assert utils.daemonize.called
    assert ms.start.called

    # test that it exits on existing pid
    make_fake_pid_file()
    commands.log_command(pid="run/fake.pid")
    assert sys.exit.called

@patch('sys.stdin', new=Mock())
def test_sendmail_command():
    sys.stdin.read.function()

    msg = mail.MailResponse(To="tests@localhost", From="tests@localhost",
                            Subject="Hello", Body="Test body.")
    sys.stdin.read.return_value = str(msg)
    commands.sendmail_command(port=8899)

@patch('sys.exit', new=Mock())
@patch('lamson.utils.daemonize', new=Mock())
@patch('lamson.utils.import_settings', new=Mock())
@patch('lamson.utils.drop_priv', new=Mock())
@patch('sys.path', new=Mock())
def test_start_command():
    # normal start
    commands.start_command()
    assert utils.daemonize.called
    assert utils.import_settings.called

    # start with pid file existing already
    make_fake_pid_file()
    commands.start_command(pid="run/fake.pid")
    assert sys.exit.called

    # start with pid file existing and force given
    assert os.path.exists("run/fake.pid")
    commands.start_command(FORCE=True, pid="run/fake.pid")
    assert not os.path.exists("run/fake.pid")

    # start with a uid but no gid
    commands.start_command(uid=1000, gid=False, pid="run/fake.pid", FORCE=True)
    assert not utils.drop_priv.called

    # start with a uid/gid given that's valid
    commands.start_command(uid=1000, gid=1000, pid="run/fake.pid", FORCE=True)
    assert utils.drop_priv.called



def raise_OSError(*x, **kw):
    raise OSError('Fail')

@patch('sys.exit', new=Mock())
@patch('os.kill', new=Mock())
@patch('glob.glob', new=lambda x: ['run/fake.pid'])
def test_stop_command():
    # gave a bad pid file
    try:
        commands.stop_command(pid="run/dontexit.pid")
    except IOError:
        assert sys.exit.called

    make_fake_pid_file()
    commands.stop_command(pid="run/fake.pid")

    make_fake_pid_file()
    commands.stop_command(ALL="run")

    make_fake_pid_file()
    commands.stop_command(pid="run/fake.pid", KILL=True)
    assert os.kill.called
    assert not os.path.exists("run/fake.pid")

    make_fake_pid_file()
    os.kill.side_effect = raise_OSError
    commands.stop_command(pid="run/fake.pid", KILL=True)


@patch('glob.glob', new=lambda x: ['run/fake.pid'])
@patch('lamson.utils.daemonize', new=Mock())
@patch('lamson.utils.import_settings', new=Mock())
@patch('os.kill', new=Mock())
@patch('sys.exit', new=Mock())
@patch('sys.path', new=Mock())
def test_restart_command():
    make_fake_pid_file()
    commands.restart_command(pid="run/fake.pid")

@patch('os.chdir', new=Mock())
@patch('BaseHTTPServer.HTTPServer', new=Mock())
@patch('SimpleHTTPServer.SimpleHTTPRequestHandler', new=Mock())
def test_web_command():
    commands.web_command()
    assert os.chdir.called

def test_version_command():
    commands.version_command()


def test_cleanse_command():
    commands.cleanse_command(input='run/queue', output='run/cleansed')
    assert os.path.exists('run/cleansed')

def raises_EncodingError(*args):
    raise encoding.EncodingError

@patch('lamson.encoding.from_message')
def test_cleans_command_with_encoding_error(from_message):
    from_message.side_effect = raises_EncodingError
    commands.cleanse_command(input='run/queue', output='run/cleansed')


def test_blast_command():
    commands.blast_command(input='run/queue', port=8899)


########NEW FILE########
__FILENAME__ = confirm_tests
from nose.tools import *
from lamson.confirm import *
from lamson.testing import *
from lamson import mail, queue
import shutil
import os


def teardown():
    if os.path.exists('run/confirm'):
        shutil.rmtree('run/confirm')

    if os.path.exists('run/queue'):
        shutil.rmtree('run/queue')


teardown()
storage = ConfirmationStorage()
engine = ConfirmationEngine('run/confirm', storage)


def test_ConfirmationStorage():
    storage.store('testing', 'somedude@localhost',
                  '12345', '567890')
    secret, pending_id = storage.get('testing', 'somedude@localhost')
    assert_equal(secret, '12345')
    assert_equal(pending_id, '567890')

    storage.delete('testing', 'somedude@localhost')
    assert_equal(len(storage.confirmations), 0)

    storage.store('testing', 'somedude@localhost',
                  '12345', '567890')
    assert_equal(len(storage.confirmations), 1)
    storage.clear()
    assert_equal(len(storage.confirmations), 0)


def test_ConfirmationEngine_send():
    queue.Queue('run/queue').clear()
    engine.clear()

    list_name = 'testing'
    action = 'subscribing to'
    host = 'localhost'

    message = mail.MailRequest('fakepeer', 'somedude@localhost',
                               'testing-subscribe@localhost', 'Fake body.')

    engine.send(relay(port=8899), 'testing', message, 'confirmation.msg', locals())
   
    confirm = delivered('confirm')
    assert delivered('somedude', to_queue=engine.pending)
    assert confirm

    return confirm

def test_ConfirmationEngine_verify():
    confirm = test_ConfirmationEngine_send()

    resp = mail.MailRequest('fakepeer', '"Somedude Smith" <somedude@localhost>',
                           confirm['Reply-To'], 'Fake body')

    target, _, expect_secret = confirm['Reply-To'].split('-')
    expect_secret = expect_secret.split('@')[0]

    found = engine.verify(target, resp['from'], 'invalid_secret')
    assert not found

    pending = engine.verify(target, resp['from'], expect_secret)
    assert pending, "Verify failed: %r not in %r." % (expect_secret,
                                                      storage.confirmations)

    assert_equal(pending['from'], 'somedude@localhost')
    assert_equal(pending['to'], 'testing-subscribe@localhost')


def test_ConfirmationEngine_cancel():
    confirm = test_ConfirmationEngine_send()

    target, _, expect_secret = confirm['Reply-To'].split('-')
    expect_secret = expect_secret.split('@')[0]

    engine.cancel(target, confirm['To'], expect_secret)
    
    found = engine.verify(target, confirm['To'], expect_secret)
    assert not found

########NEW FILE########
__FILENAME__ = encoding_tests
from __future__ import with_statement
from nose.tools import *
import re
import os
from lamson import encoding, mail
import mailbox
import email
from email import encoders
from email.utils import parseaddr
from mock import *
import chardet


BAD_HEADERS = [
    u'"\u8003\u53d6\u5206\u4eab" <Ernest.Beard@msa.hinet.net>'.encode('utf-8'),
    '"=?windows-1251?B?RXhxdWlzaXRlIFJlcGxpY2E=?="\n\t<wolfem@barnagreatlakes.com>',
    '=?iso-2022-jp?B?Zmlicm91c19mYXZvcmF0ZUB5YWhvby5jby5qcA==?=<fibrous_favorate@yahoo.co.jp>',

    '=?windows-1252?Q?Global_Leadership_in_HandCare_-_Consumer,\n\t_Professional_and_Industrial_Products_OTC_:_FLKI?=',
    '=?windows-1252?q?Global_Leadership_in_Handcare_-_Consumer, _Auto,\n\t_Professional_&_Industrial_Products_-_OTC_:_FLKI?=',
    'I am just normal.',
    '=?koi8-r?B?WW91ciBtYW6ScyBzdGFtaW5hIHdpbGwgY29tZSBiYWNrIHRvIHlvdSBs?=\n\t=?koi8-r?B?aWtlIGEgYm9vbWVyYW5nLg==?=',
    '=?koi8-r?B?WW91IGNhbiBiZSBvbiB0b3AgaW4gYmVkcm9vbSBhZ2FpbiCWIGp1c3Qg?=\n\t=?koi8-r?B?YXNrIHVzIGZvciBhZHZpY2Uu?=',
    '"=?koi8-r?B?5MXMz9DSz8na18/E09TXzw==?=" <daniel@specelec.com>',
    '=?utf-8?b?IumrlOiCsuWckuWNgOermSDihpIg6ZW35bqa6Yar6Zmi56uZIOKGkiDmlofljJbk?=\n =?utf-8?b?uInot6/nq5kiIDx2Z3hkcmp5Y2lAZG5zLmh0Lm5ldC50dz4=?=',
    '=?iso-8859-1?B?SOlhdnkgTel05WwgVW7uY/hk?=\n\t=?iso-8859-1?Q?=E9?=',
]

DECODED_HEADERS = encoding.header_from_mime_encoding(BAD_HEADERS)

NORMALIZED_HEADERS = [encoding.header_to_mime_encoding(x) for x in DECODED_HEADERS]


def test_MailBase():
    the_subject = u'p\xf6stal'
    m = encoding.MailBase()
    
    m['To'] = "testing@localhost"
    m['Subject'] = the_subject

    assert m['To'] == "testing@localhost"
    assert m['TO'] == m['To']
    assert m['to'] == m['To']

    assert m['Subject'] == the_subject
    assert m['subject'] == m['Subject']
    assert m['sUbjeCt'] == m['Subject']
    
    msg = encoding.to_message(m)
    m2 = encoding.from_message(msg)

    assert_equal(len(m), len(m2))

    for k in m:
        assert m[k] == m2[k], "%s: %r != %r" % (k, m[k], m2[k])
    
    for k in m.keys():
        assert k in m
        del m[k]
        assert not k in m

def test_header_to_mime_encoding():
    for i, header in enumerate(DECODED_HEADERS):
        assert_equal(NORMALIZED_HEADERS[i], encoding.header_to_mime_encoding(header))

def test_dumb_shit():
    # this is a sample of possibly the worst case Mutt can produce
    idiot = '=?iso-8859-1?B?SOlhdnkgTel05WwgVW7uY/hk?=\n\t=?iso-8859-1?Q?=E9?='
    should_be = u'H\xe9avy M\xe9t\xe5l Un\xeec\xf8d\xe9'
    assert_equal(encoding.header_from_mime_encoding(idiot), should_be)

def test_header_from_mime_encoding():
    assert not encoding.header_from_mime_encoding(None)
    assert_equal(len(BAD_HEADERS), len(encoding.header_from_mime_encoding(BAD_HEADERS)))
    
    for i, header in enumerate(BAD_HEADERS):
        assert_equal(DECODED_HEADERS[i], encoding.header_from_mime_encoding(header))


def test_to_message_from_message_with_spam():
    mb = mailbox.mbox("tests/spam")
    fails = 0
    total = 0

    for msg in mb:
        try:
            m = encoding.from_message(msg)
            out = encoding.to_message(m)
            assert repr(out)

            m2 = encoding.from_message(out)

            for k in m:
                if '@' in m[k]:
                    assert_equal(parseaddr(m[k]), parseaddr(m2[k]))
                else:
                    assert m[k].strip() == m2[k].strip(), "%s: %r != %r" % (k, m[k], m2[k])

                assert not m[k].startswith(u"=?")
                assert not m2[k].startswith(u"=?")
                assert m.body == m2.body, "Bodies don't match" 

                assert_equal(len(m.parts), len(m2.parts), "Not the same number of parts.")

                for i, part in enumerate(m.parts):
                    assert part.body == m2.parts[i].body, "Part %d isn't the same: %r \nvs\n. %r" % (i, part.body, m2.parts[i].body)
            total += 1
        except encoding.EncodingError, exc:
            fails += 1

    assert fails/total < 0.01, "There were %d failures out of %d total." % (fails, total)


def test_to_file_from_file():
    mb = mailbox.mbox("tests/spam")
    msg = encoding.from_message(mb[0])

    outfile = "run/encoding_test.msg"

    with open(outfile, 'w') as outfp:
        encoding.to_file(msg, outfp)

    with open(outfile) as outfp:
        msg2 = encoding.from_file(outfp)
    
    outdata = open(outfile).read()

    assert_equal(len(msg), len(msg2))
    os.unlink(outfile)


def test_guess_encoding_and_decode():
    for header in DECODED_HEADERS:
        try:
            encoding.guess_encoding_and_decode('ascii', header.encode('utf-8'))
        except encoding.EncodingError:
            pass


def test_attempt_decoding():
    for header in DECODED_HEADERS:
        encoding.attempt_decoding('ascii', header.encode('utf-8'))


def test_properly_decode_header():
    for i, header in enumerate(BAD_HEADERS):
        parsed = encoding.properly_decode_header(header)
        assert_equal(DECODED_HEADERS[i], parsed)


def test_headers_round_trip():
    # round trip the headers to make sure they convert reliably back and forth
    for header in BAD_HEADERS:
        original = encoding.header_from_mime_encoding(header)

        assert original
        assert "=?" not in original and "?=" not in original, "Didn't decode: %r" % (encoding.SCANNER.scan(header),)

        encoded = encoding.header_to_mime_encoding(original)
        assert encoded

        return_original = encoding.header_from_mime_encoding(encoded)
        assert_equal(original, return_original)

        return_encoded = encoding.header_to_mime_encoding(return_original)
        assert_equal(encoded, return_encoded)


def test_MIMEPart():
    text1 = encoding.MIMEPart("text/plain")
    text1.set_payload("The first payload.")
    text2 = encoding.MIMEPart("text/plain")
    text2.set_payload("The second payload.")

    image_data = open("tests/lamson.png").read()
    img1 = encoding.MIMEPart("image/png")
    img1.set_payload(image_data)
    img1.set_param('attachment','', header='Content-Disposition')
    img1.set_param('filename','lamson.png', header='Content-Disposition')
    encoders.encode_base64(img1)
    
    multi = encoding.MIMEPart("multipart/mixed")
    for x in [text1, text2, img1]:
        multi.attach(x)

    mail = encoding.from_message(multi)

    assert mail.parts[0].body == "The first payload."
    assert mail.parts[1].body == "The second payload."
    assert mail.parts[2].body == image_data

    encoding.to_message(mail)


@patch('chardet.detect', new=Mock())
@raises(encoding.EncodingError)
def test_guess_encoding_fails_completely():
    chardet.detect.return_value = {'encoding': None, 'confidence': 0.0}
    encoding.guess_encoding_and_decode('ascii', 'some data', errors='strict')


def test_attach_text():
    mail = encoding.MailBase()
    mail.attach_text("This is some text.", 'text/plain')

    msg = encoding.to_message(mail)
    assert msg.get_payload(0).get_payload() == "This is some text."
    assert encoding.to_string(mail)

    mail.attach_text("<html><body><p>Hi there.</p></body></html>", "text/html")
    msg = encoding.to_message(mail)
    assert len(msg.get_payload()) == 2
    assert encoding.to_string(mail)


def test_attach_file():
    mail = encoding.MailBase()
    png = open("tests/lamson.png").read()
    mail.attach_file("lamson.png", png, "image/png", "attachment")
    msg = encoding.to_message(mail)

    payload = msg.get_payload(0)
    assert payload.get_payload(decode=True) == png
    assert payload.get_filename() == "lamson.png", payload.get_filename()



def test_content_encoding_headers_are_maintained():
    inmail = encoding.from_file(open("tests/signed.msg"))

    ctype, ctype_params = inmail.content_encoding['Content-Type']

    assert_equal(ctype, 'multipart/signed')

    # these have to be maintained
    for key in ['protocol', 'micalg']:
        assert key in ctype_params

    # these get removed
    for key in encoding.CONTENT_ENCODING_REMOVED_PARAMS:
        assert key not in ctype_params

    outmsg = encoding.to_message(inmail)
    ctype, ctype_params = encoding.parse_parameter_header(outmsg, 'Content-Type')
    for key in ['protocol', 'micalg']:
        assert key in ctype_params, key


def test_odd_content_type_with_charset():
    mail = encoding.MailBase()
    mail.body = u"p\xf6stal".encode('utf-8')
    mail.content_encoding['Content-Type'] = ('application/plain', {'charset': 'utf-8'})

    msg = encoding.to_string(mail)
    assert msg

def test_specially_borked_lua_message():
    assert encoding.from_file(open("tests/borked.msg"))

def raises_TypeError(*args):
    raise TypeError()

@patch('lamson.encoding.MIMEPart.__init__')
@raises(encoding.EncodingError)
def test_to_message_encoding_error(mp_init):
    mp_init.side_effect = raises_TypeError
    test = encoding.from_file(open("tests/borked.msg"))
    msg = encoding.to_message(test)

def raises_UnicodeError(*args):
    raise UnicodeError()

@raises(encoding.EncodingError)
def test_guess_encoding_and_decode_unicode_error():
    data = Mock()
    data.__str__ = Mock()
    data.__str__.return_value = u"\0\0"
    data.decode.side_effect = raises_UnicodeError
    encoding.guess_encoding_and_decode("ascii", data)
    
def test_attempt_decoding_with_bad_encoding_name():
    assert_equal("test", encoding.attempt_decoding("asdfasdf", "test"))

@raises(encoding.EncodingError)
def test_apply_charset_to_header_with_bad_encoding_char():
    encoding.apply_charset_to_header('ascii', 'X', 'bad')

def test_odd_roundtrip_bug():
    decoded_addrs=[u'"\u0414\u0435\u043b\u043e\u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u043e" <daniel@specelec.com>',
                   u'"\u8003\u53d6\u5206\u4eab" <Ernest.Beard@msa.hinet.net>',
                   u'"Exquisite Replica"\n\t<wolfem@barnagreatlakes.com>',]

    for decoded in decoded_addrs:
        encoded = encoding.header_to_mime_encoding(decoded)
        assert '<' in encoded and '"' in encoded, "Address wasn't encoded correctly:\n%s" % encoded


########NEW FILE########
__FILENAME__ = handler_tests
from nose.tools import *
from lamson.routing import Router
from lamson_tests import message_tests
import lamson.handlers.log
import lamson.handlers.queue

def test_log_handler():
    Router.deliver(message_tests.test_mail_request())

def test_queue_handler():
    Router.deliver(message_tests.test_mail_request())

########NEW FILE########
__FILENAME__ = html_tests
from nose.tools import *
from config import testing
from lamson import html, view, mail



def test_HtmlMail_load_css():
    title = "load_css Test"
    hs = html.HtmlMail("style.css", "html_test.html")
    assert_equal(len(hs.stylesheet), 8)
    assert_equal(hs.stylesheet[0][0], u"body")


def test_HtmlMail_apply_styles():
    hs = html.HtmlMail("style.css", "html_test.html")
    page = view.render(locals(), "html_test.html")

    styled = hs.apply_styles(page)

    assert "magenta" in str(styled)
    assert_not_equal(str(styled), str(page))


def test_HtmlMail_render():
    title = "render Test"
    hs = html.HtmlMail("style.css", "html_test.html")

    lame = hs.render(locals(), "content.markdown")
    assert lame

    pretty = hs.render(locals(), "content.markdown", pretty=True)

    assert pretty
    assert_not_equal(lame, pretty)


def test_HtmlMail_respond():
    title = "respond Test"
    hs = html.HtmlMail("style.css", "html_test.html")
    variables = locals()

    msg = hs.respond(variables, "content.markdown", From='somedude@localhost',
                     To='zed.shaw@gmail.com',
                     Subject='This is a %(title)s')

    assert 'content' not in variables
    assert msg
    assert_equal(msg['from'], 'somedude@localhost')
    assert_equal(msg['to'], 'zed.shaw@gmail.com')
    assert_equal(msg['subject'], "This is a respond Test")


def test_HtmlMail_content_type_respected():
    generator = html.HtmlMail("style.css", "html_test.html", {})

    resp = generator.respond({}, "content.markdown",
                           From="somedude@localhost",
                           To="somedude@localhost",
                           Subject="Test of an HTML mail.",
                           Body="content.markdown"
                           )

    req = mail.MailRequest('fakepeer', None, None, str(resp))
    
    assert_equal(req.base.content_encoding['Content-Type'][0], 'multipart/alternative')

    resp2 = mail.MailResponse(To=req['to'],
                              From=req['from'],
                              Subject=req['subject'])
    resp2.attach_all_parts(req)
    
    assert_equal(resp2.base.content_encoding['Content-Type'],
                 resp.base.content_encoding['Content-Type'])
    
    assert_equal(resp2.base.content_encoding['Content-Type'][0], 'multipart/alternative')

    req2 = mail.MailRequest('fakepeer', None, None, str(resp2))

    assert_equal(resp2.base.content_encoding['Content-Type'][0], 'multipart/alternative')

    assert_equal(req2.base.content_encoding['Content-Type'][0], 'multipart/alternative')


########NEW FILE########
__FILENAME__ = message_tests
# Copyright (C) 2008 Zed A. Shaw.  Licensed under the terms of the GPLv3.

import warnings
from nose.tools import *
import re
import os
from lamson import mail, encoding
import email

sample_message = """From: somedude@localhost
To: somedude@localhost

Test
"""

def test_mail_request():
    # try with a half-assed message
    msg = mail.MailRequest("localhost", "zedfrom@localhost",
                           "zedto@localhost", "Fake body.")
    assert msg['to'] == "zedto@localhost", "To is %r" % msg['to']
    assert msg['from'] == "zedfrom@localhost", "From is %r" % msg['from']

    msg = mail.MailRequest("localhost", "somedude@localhost",
                             ["somedude@localhost"], sample_message)
    assert msg.original == sample_message

    assert_equal(msg['From'], "somedude@localhost")

    assert("From" in msg)
    del msg["From"]
    assert("From" not in msg)

    msg["From"] = "nobody@localhost"
    assert("From" in msg)
    assert_equal(msg["From"], "nobody@localhost")

    # validate that upper and lower case work for headers
    assert("FroM" in msg)
    assert("from" in msg)
    assert("From" in msg)
    assert_equal(msg['From'], msg['fRom'])
    assert_equal(msg['From'], msg['from'])
    assert_equal(msg['from'], msg['fRom'])

    # make sure repr runs
    print repr(msg)

    return msg

def test_mail_response_plain_text():
    sample = mail.MailResponse(To="receiver@localhost", 
                                 Subject="Test message",
                                 From="sender@localhost",
                                 Body="Test from test_mail_response_plain_text.")
    return sample

def test_mail_response_html():
    sample = mail.MailResponse(To="receiver@localhost", 
                                 Subject="Test message",
                                 From="sender@localhost",
                                 Html="<html><body><p>From test_mail_response_html</p></body></html>")
    return sample

def test_mail_response_html_and_plain_text():
    sample = mail.MailResponse(To="receiver@localhost", 
                                 Subject="Test message",
                                 From="sender@localhost",
                                 Html="<html><body><p>Hi there.</p></body></html>",
                                 Body="Test from test_mail_response_html_and_plain_text.")
    return sample

def test_mail_response_attachments():
    sample = mail.MailResponse(To="receiver@localhost", 
                                 Subject="Test message",
                                 From="sender@localhost",
                                 Body="Test from test_mail_response_attachments.")
    readme_data = open("./README.md").read()

    assert_raises(AssertionError, sample.attach, filename="./README.md", disposition="inline")

    sample.attach(filename="./README.md", content_type="text/plain", disposition="inline")
    assert len(sample.attachments) == 1
    assert sample.multipart

    msg = sample.to_message()
    assert_equal(len(msg.get_payload()), 2)

    sample.clear()
    assert len(sample.attachments) == 0
    assert not sample.multipart

    sample.attach(data=readme_data, filename="./README.md", content_type="text/plain")

    msg = sample.to_message()
    assert_equal(len(msg.get_payload()), 2)
    sample.clear()

    sample.attach(data=readme_data, content_type="text/plain")
    msg = sample.to_message()
    assert_equal(len(msg.get_payload()), 2)

    return sample


def test_mail_request_attachments():
    sample = test_mail_response_attachments()
    data = str(sample)

    msg = mail.MailRequest("localhost", None, None, data)

    msg_parts = msg.all_parts()
    sample_parts = sample.all_parts()

    readme = open("./README.md").read()

    # BUG: Python's MIME text attachment decoding drops trailing newline chars

    assert msg_parts[0].body == sample_parts[0].body
    # python drops chars at the end, so can't compare equally
    assert readme.startswith(msg_parts[1].body)
    assert msg.body() == sample_parts[0].body

    # test that we get at least one message for messages without attachments
    sample = test_mail_response_plain_text()
    msg = mail.MailRequest("localhost", None, None, str(sample))
    msg_parts = msg.all_parts()
    assert len(msg_parts) == 0, "Length is %d should be 0." % len(msg_parts)
    assert msg.body()


def test_mail_response_mailing_list_headers():
    list_addr = "test.users@localhost"

    msg = mail.MailResponse(From='somedude@localhost', To=list_addr, 
            Subject='subject', Body="Mailing list reply.")

    print repr(msg)

    msg["Sender"] = list_addr
    msg["Reply-To"] = list_addr
    msg["List-Id"] = list_addr
    msg["Return-Path"] = list_addr
    msg["In-Reply-To"] = 'Message-Id-1231123'
    msg["References"] = 'Message-Id-838845854'
    msg["Precedence"] = 'list'

    data = str(msg)

    req = mail.MailRequest('localhost', 'somedude@localhost', list_addr, data)

    headers = ['Sender', 'Reply-To', 'List-Id', 'Return-Path', 
               'In-Reply-To', 'References', 'Precedence']
    for header in headers:
        assert msg[header] == req[header]

    # try a delete
    del msg['Precedence']

def test_mail_response_ignore_case_headers():
    msg = test_mail_response_plain_text()
    # validate that upper and lower case work for headers
    assert("FroM" in msg)
    assert("from" in msg)
    assert("From" in msg)
    assert_equal(msg['From'], msg['fRom'])
    assert_equal(msg['From'], msg['from'])
    assert_equal(msg['from'], msg['fRom'])


def test_walk():
    bm = mail.MailRequest(None,None,None, open("tests/bounce.msg").read())
    parts = [x for x in bm.walk()]

    assert parts
    assert_equal(len(parts), 6)


def test_copy_parts():
    bm = mail.MailRequest(None,None,None, open("tests/bounce.msg").read())
    
    resp = mail.MailResponse(To=bm['to'], From=bm['from'],
                             Subject=bm['subject'])

    resp.attach_all_parts(bm)

    resp = resp.to_message()
    bm = bm.to_message()

    assert_equal(len([x for x in bm.walk()]), len([x for x in resp.walk()]))

   
def test_craft_from_sample():
    list_name = "test.list"
    user_full_address = "tester@localhost"

    sample = mail.MailResponse(To=list_name + "@localhost",
                          From=user_full_address,
                          Subject="Test message with attachments.",
                          Body="The body as one attachment.")
    sample.update({"Test": "update"})

    sample.attach(filename="tests/lamson_tests/message_tests.py",
                  content_type="text/plain",
                  disposition="attachment")
    
    inmsg = mail.MailRequest("fakepeer", None, None, str(sample))
    assert "Test" in sample.keys()

    for part in inmsg.to_message().walk():
        assert part.get_payload(), "inmsg busted."

    outmsg = mail.MailResponse(To=inmsg['from'], 
                          From=inmsg['to'],
                          Subject=inmsg['subject'])

    outmsg.attach_all_parts(inmsg)

    result = outmsg.to_message()

    for part in result.walk():
        assert part.get_payload(), "outmsg parts don't have payload."


def test_route_to_from_works():
    msg = mail.MailRequest("fakepeer", "from@localhost",
                                   [u"<to1@localhost>", u"to2@localhost"], "")
    assert '<' not in msg.route_to, msg.route_to

    msg = mail.MailRequest("fakepeer", "from@localhost",
                                   [u"to1@localhost", u"to2@localhost"], "")
    assert '<' not in msg.route_to, msg.route_to
    
    msg = mail.MailRequest("fakepeer", "from@localhost",
                                   [u"to1@localhost", u"<to2@localhost>"], "")
    assert '<' not in msg.route_to, msg.route_to

    msg = mail.MailRequest("fakepeer", "from@localhost",
                                   [u"to1@localhost"], "")
    assert '<' not in msg.route_to, msg.route_to

    msg = mail.MailRequest("fakepeer", "from@localhost",
                                   [u"<to1@localhost>"], "")
    assert '<' not in msg.route_to, msg.route_to


def test_decode_header_randomness():
    assert_equal(mail._decode_header_randomness(None), set())
    assert_equal(mail._decode_header_randomness(["z@localhost", '"Z A" <z@localhost>']), 
                 set(["z@localhost", "z@localhost"]))
    assert_equal(mail._decode_header_randomness("z@localhost"),
                 set(["z@localhost"]))
    assert_raises(encoding.EncodingError, mail._decode_header_randomness, 1)


def test_msg_is_deprecated():
    warnings.simplefilter("ignore")
    msg = mail.MailRequest(None, None, None, "")
    assert_equal(msg.msg, msg.base)
    resp = mail.MailResponse()
    assert_equal(resp.msg, resp.base)


########NEW FILE########
__FILENAME__ = queue_tests
from lamson import queue, server, mail
from nose.tools import *
import shutil
import os
from mock import *
import mailbox

USE_SAFE=False

def setup():
    if os.path.exists("run/big_queue"):
        shutil.rmtree("run/big_queue")

def teardown():
    setup()


def test_push():
    q = queue.Queue("run/queue", safe=USE_SAFE)
    q.clear()

    # the queue doesn't really care if its a request or response, as long
    # as the object answers to str(msg)
    msg = mail.MailResponse(To="test@localhost", From="test@localhost",
                              Subject="Test", Body="Test")
    key = q.push(msg)
    assert key, "Didn't get a key for test_get push."

    return q


def test_pop():
    q = test_push()
    key, msg = q.pop()

    assert key, "Didn't get a key for test_get push."
    assert msg, "Didn't get a message for key %r" % key

    assert msg['to'] == "test@localhost"
    assert msg['from'] == "test@localhost"
    assert msg['subject'] == "Test"
    assert msg.body() == "Test"

    assert q.count() == 0, "Queue should be empty."
    assert not q.pop()[0]


def test_get():
    q = test_push()
    msg = mail.MailResponse(To="test@localhost", From="test@localhost",
                              Subject="Test", Body="Test")
    key = q.push(str(msg))
    assert key, "Didn't get a key for test_get push."

    msg = q.get(key)
    assert msg, "Didn't get a message for key %r" % key

def test_remove():
    q = test_push()
    msg = mail.MailResponse(To="test@localhost", From="test@localhost",
                              Subject="Test", Body="Test")
    key = q.push(str(msg))
    assert key, "Didn't get a key for test_get push."
    assert q.count() == 2, "Wrong count %d should be 2" % q.count()

    q.remove(key)
    assert q.count() == 1, "Wrong count %d should be 1" % q.count()



def test_safe_maildir():
    global USE_SAFE
    USE_SAFE=True
    test_push()
    test_pop()
    test_get()
    test_remove()


def test_oversize_protections():
    # first just make an oversize limited queue
    overq = queue.Queue("run/queue", pop_limit=10)
    overq.clear()

    for i in range(5):
        overq.push("HELLO" * 100)

    assert_equal(overq.count(), 5)

    key, msg = overq.pop()

    assert not key and not msg, "Should get no messages."
    assert_equal(overq.count(), 0)

    # now make sure that oversize mail is moved to the overq
    setup()
    overq = queue.Queue("run/queue", pop_limit=10, oversize_dir="run/big_queue")
    moveq = queue.Queue("run/big_queue")

    for i in range(5):
        overq.push("HELLO" * 100)

    key, msg = overq.pop()

    assert not key and not msg, "Should get no messages."
    assert_equal(overq.count(), 0)
    assert_equal(moveq.count(), 5)

    moveq.clear()
    overq.clear()


@patch('os.stat', new=Mock())
@raises(mailbox.ExternalClashError)
def test_SafeMaildir_name_clash():
    try:
        shutil.rmtree("run/queue")
    except: pass
    sq = queue.SafeMaildir('run/queue')
    sq.add("TEST")

def raise_OSError(*x, **kw):
    err = OSError('Fail')
    err.errno = 0
    raise err

@patch('mailbox._create_carefully', new=Mock())
@raises(OSError)
def test_SafeMaildir_throws_errno_failure():
    setup()
    mailbox._create_carefully.side_effect = raise_OSError
    sq = queue.SafeMaildir('run/queue')
    sq.add("TEST")

@patch('os.stat', new=Mock())
@raises(OSError)
def test_SafeMaildir_reraise_weird_errno():
    try:
        shutil.rmtree("run/queue")
    except: pass

    os.stat.side_effect = raise_OSError
    sq = queue.SafeMaildir('run/queue')
    sq.add('TEST')


########NEW FILE########
__FILENAME__ = routing_tests
from nose.tools import *
from lamson.routing import *
from lamson.mail import MailRequest
from lamson import queue, routing, encoding
from mock import *


def setup():
    Router.clear_states()
    Router.clear_routes()

def teardown():
    setup()

def test_MemoryStorage():
    store = MemoryStorage()
    store.set(test_MemoryStorage.__module__, "tester@localhost", "TESTED")

    assert store.get(test_MemoryStorage.__module__, "tester@localhost") == "TESTED"

    assert store.get(test_MemoryStorage.__module__, "tester2@localhost") == "START"

    store.clear()

    assert store.get(test_MemoryStorage.__module__, "tester@localhost") == "START"

def test_ShelveStorage():
    store = ShelveStorage("tests/statesdb")

    store.set(test_ShelveStorage.__module__, "tester@localhost", "TESTED")
    assert store.get(test_MemoryStorage.__module__, "tester@localhost") == "TESTED"

    assert store.get(test_MemoryStorage.__module__, "tester2@localhost") == "START"

    store.clear()
    assert store.get(test_MemoryStorage.__module__, "tester@localhost") == "START"


def test_RoutingBase():
    assert len(Router.ORDER) == 0
    assert len(Router.REGISTERED) == 0

    Router.load(['lamson_tests.simple_fsm_mod'])
    import simple_fsm_mod

    assert len(Router.ORDER) > 0
    assert len(Router.REGISTERED) > 0

    message = MailRequest('fakepeer', 'zedshaw@localhost', 'users-subscribe@localhost', "")
    Router.deliver(message)
    assert Router.in_state(simple_fsm_mod.CONFIRM, message)

    confirm = MailRequest('fakepeer', '"Zed Shaw" <zedshaw@localhost>',  'users-confirm-1@localhost', "")
    Router.deliver(confirm)
    assert Router.in_state(simple_fsm_mod.POSTING, message)

    Router.deliver(message)
    assert Router.in_state(simple_fsm_mod.NEXT, message)

    Router.deliver(message)
    assert Router.in_state(simple_fsm_mod.END, message)

    Router.deliver(message)
    assert Router.in_state(simple_fsm_mod.START, message)

    Router.clear_states()
    explosion = MailRequest('fakepeer',  '<hacker@localhost>',   'start-explode@localhost', "")
    Router.LOG_EXCEPTIONS=True
    Router.deliver(explosion)

    assert Router.in_error(simple_fsm_mod.END, explosion)

    Router.clear_states()
    Router.LOG_EXCEPTIONS=False
    explosion = MailRequest('fakepeer',  'hacker@localhost',   'start-explode@localhost', "")
    assert_raises(RuntimeError, Router.deliver, explosion)

    Router.reload()
    assert 'lamson_tests.simple_fsm_mod' in Router.HANDLERS
    assert len(Router.ORDER)
    assert len(Router.REGISTERED)


    message = MailRequest('fakepeer', 'zedshaw@localhost',
                          ['users-subscribe@localhost',
                           'users-confirm-1@localhost'], "Fake body.")

    Router.deliver(message)

    assert Router.in_state(simple_fsm_mod.POSTING, message), "Router state: %r" % Router.get_state('simple_fsm_mod', message)


def test_Router_undeliverable_queue():
    Router.clear_routes()
    Router.clear_states()

    Router.UNDELIVERABLE_QUEUE = Mock()
    msg = MailRequest('fakepeer', 'from@localhost', 'to@localhost', "Nothing")

    Router.deliver(msg)
    assert Router.UNDELIVERABLE_QUEUE.push.called



@raises(NotImplementedError)
def test_StateStorage_get_raises():
    s = StateStorage()
    s.get("raises", "raises")

@raises(NotImplementedError)
def test_StateStorage_set_raises():
    s = StateStorage()
    s.set("raises", "raises", "raises")

@raises(NotImplementedError)
def test_StateStorage_clear_raises():
    s = StateStorage()
    s.clear()

@raises(TypeError)
def test_route___get___raises():
    class BadRoute(object):

        @route("test")
        def wont_work(message, **kw):
            pass

    br = BadRoute()
    br.wont_work("raises")

@patch('__builtin__.reload', new=Mock(side_effect=ImportError))
@patch('lamson.routing.LOG', new=Mock())
def test_reload_raises():
    Router.LOG_EXCEPTIONS=True
    Router.reload()
    assert routing.LOG.exception.called

    Router.LOG_EXCEPTIONS=False
    routing.LOG.exception.reset_mock()
    assert_raises(ImportError, Router.reload)
    assert not routing.LOG.exception.called

    routing.LOG.exception.reset_mock()
    Router.LOG_EXCEPTIONS=True
    Router.load(['fake.handler'])
    assert routing.LOG.exception.called

    Router.LOG_EXCEPTIONS=False
    routing.LOG.exception.reset_mock()
    assert_raises(ImportError, Router.load, ['fake.handler'])
    assert not routing.LOG.exception.called



########NEW FILE########
__FILENAME__ = server_tests
# Copyright (C) 2008 Zed A. Shaw.  Licensed under the terms of the GPLv3.

from nose.tools import *
from mock import *
from lamson import server, queue, routing
from message_tests import *


def test_router():
    routing.Router.deliver(test_mail_request())

    # test that fallthrough works too
    msg = test_mail_request()
    msg['to'] = 'unhandled@localhost'
    msg.To = msg['to']

    routing.Router.deliver(msg)

def test_receiver():
    receiver = server.SMTPReceiver(host="localhost", port=8824)
    msg = test_mail_request()
    receiver.process_message(msg.Peer, msg.From, msg.To, str(msg))


def test_relay_deliver():
    relay = server.Relay("localhost", port=8899)

    relay.deliver(test_mail_response_plain_text())
    relay.deliver(test_mail_response_html())
    relay.deliver(test_mail_response_html_and_plain_text())
    relay.deliver(test_mail_response_attachments())

@patch('DNS.mxlookup')
def test_relay_deliver_mx_hosts(DNS_mxlookup):
    DNS_mxlookup.return_value = [[100, "localhost"]]
    relay = server.Relay(None, port=8899)

    msg = test_mail_response_plain_text()
    msg['to'] = 'zedshaw@localhost'
    relay.deliver(msg)
    assert DNS_mxlookup.called

@patch('DNS.mxlookup')
def test_relay_resolve_relay_host(DNS_mxlookup):
    DNS_mxlookup.return_value = []
    relay = server.Relay(None, port=8899)
    host = relay.resolve_relay_host('zedshaw@localhost')
    assert_equal(host, 'localhost')
    assert DNS_mxlookup.called

    DNS_mxlookup.reset_mock()
    DNS_mxlookup.return_value = [[100, "mail.zedshaw.com"]]
    host = relay.resolve_relay_host('zedshaw@zedshaw.com')
    assert_equal(host, 'mail.zedshaw.com')
    assert DNS_mxlookup.called

def test_relay_reply():
    relay = server.Relay("localhost", port=8899)
    print "Relay: %r" % relay

    relay.reply(test_mail_request(), 'from@localhost', 'Test subject', 'Body')

def raises_exception(*x, **kw):
    raise RuntimeError("Raised on purpose.")


@patch('lamson.routing.Router', new=Mock())
def test_queue_receiver():
    receiver = server.QueueReceiver('run/queue')
    run_queue = queue.Queue('run/queue')
    run_queue.push(str(test_mail_response_plain_text()))
    assert run_queue.count() > 0
    receiver.start(one_shot=True)
    assert run_queue.count() == 0

    routing.Router.deliver.side_effect = raises_exception
    receiver.process_message(mail.MailRequest('localhost', 'test@localhost',
                                              'test@localhost', 'Fake body.'))



@patch('threading.Thread', new=Mock())
@patch('lamson.routing.Router', new=Mock())
def test_SMTPReceiver():
    receiver = server.SMTPReceiver(port=9999)
    receiver.start()
    receiver.process_message('localhost', 'test@localhost', 'test@localhost',
                             'Fake body.')

    routing.Router.deliver.side_effect = raises_exception
    receiver.process_message('localhost', 'test@localhost', 'test@localhost',
                             'Fake body.')

    receiver.close()

def test_SMTPError():
    err = server.SMTPError(550)
    assert str(err) == '550 Permanent Failure Mail Delivery Protocol Status', "Error is wrong: %r" % str(err)

    err = server.SMTPError(400)
    assert str(err) == '400 Persistent Transient Failure Other or Undefined Status', "Error is wrong: %r" % str(err)

    err = server.SMTPError(425)
    assert str(err) == '425 Persistent Transient Failure Mailbox Status', "Error is wrong: %r" % str(err)

    err = server.SMTPError(999)
    assert str(err) == "999 ", "Error is wrong: %r" % str(err)

    err = server.SMTPError(999, "Bogus Error Code")
    assert str(err) == "999 Bogus Error Code"


########NEW FILE########
__FILENAME__ = simple_fsm_mod
from lamson.routing import *

@state_key_generator
def simple_key_gen(module_name, message):
    return module_name

# common routing capture regexes go in here, you can override them in @route
Router.defaults(host="localhost", 
                action="[a-zA-Z0-9]+",
                list_name="[a-zA-Z.0-9]+")


@route("(list_name)-(action)@(host)")
def START(message, list_name=None, action=None, host=None):
    print "START", message, list_name, action, host
    if action == 'explode':
        print "EXPLODE!"
        raise RuntimeError("Exploded on purpose.")
    return CONFIRM
    
@route("(list_name)-confirm-(id_number)@(host)", id_number="[0-9]+")
def CONFIRM(message, list_name=None, id_number=None, host=None):
    print "CONFIRM", message, list_name, id_number, host
    return POSTING

@route("(list_name)-(action)@(host)")
def POSTING(message, list_name=None, action=None, host=None):
    print "POSTING", message, list_name, action, host
    return NEXT

@route_like(POSTING)
def NEXT(message, list_name=None, action=None, host=None):
    print "NEXT", message, list_name, action, host
    return END

def ERROR(message):
    return ERROR

@route("(anything)@(host)", anything=".*")
def END(message, anything=None, host=None):
    print "END", anything, host
    return START

@route(".*")
@stateless
@nolocking
def PASSING(message, *args, **kw):
    print "PASSING", args, kw


try:
    @stateless
    @route("badstateless@(host)")
    def BAD_STATELESS(message, *args, **kw):
        print "BAD_STATELESS", args, kw
except AssertionError:
    pass  # we need to get this

########NEW FILE########
__FILENAME__ = spam_filtered_mod
from lamson.routing import route, route_like
from lamson.spam import spam_filter


ham_db = "tests/sddb"

@route(".+")
def SPAMMING(message):
    # the spam black hole
    pass

@route("(anything)@(host)", anything=".+", host=".+")
@spam_filter(ham_db, "tests/.hammierc", "run/queue", next_state=SPAMMING)
def START(message, **kw):
    print "Ham message received. Going to END."
    return END

@route_like(START)
def END(message, **kw):
    print "Done."



########NEW FILE########
__FILENAME__ = spam_tests
### SpamBayes isn't easy to install so I'm disabling this test in 1.1
# until an alternative can be found.

# from nose.tools import *
# from lamson import spam
# from lamson_tests.message_tests import *
# from lamson.routing import Router
# import os
# 
# ham_db = "tests/sddb"
# 
# def setup():
#     Router.clear_states()
#     Router.clear_routes()
#     if os.path.exists(ham_db):
#         os.unlink(ham_db)
# 
# def teardown():
#     setup()
# 
# def test_Filter():
#     sf = spam.Filter(ham_db, 'tests/.hammierc')
#     ham_msg = test_mail_request().to_message()
#     spam_msg = test_mail_response_plain_text().to_message()
# 
#     sf.train_ham(ham_msg)
#     sf.train_spam(spam_msg)
# 
#     sf.untrain_ham(test_mail_request().to_message())
#     sf.untrain_spam(spam_msg)
# 
# 
# def test_spam_filter():
#     import spam_filtered_mod
# 
#     sf = spam.Filter(ham_db, 'tests/.hammierc')
#     msg = test_mail_request()
#     sf.train_spam(msg.to_message())
# 
#     Router.deliver(msg)
#     assert Router.in_state(spam_filtered_mod.SPAMMING, msg), "Spam got through"
# 
#     Router.clear_states()
#     sf.untrain_spam(msg.to_message())
#     sf.train_ham(msg.to_message())
# 
#     Router.deliver(msg)
#     assert Router.in_state(spam_filtered_mod.END, msg), "Ham didn't go through."
# 
#     del spam_filtered_mod
# 
# 
# def test_spam_filter_without_db_file():
#     import spam_filtered_mod
# 
#     msg = test_mail_request()
#     Router.deliver(msg)
#     assert Router.in_state(spam_filtered_mod.END, msg), "Spam got through"
# 

########NEW FILE########
__FILENAME__ = testing_tests
from lamson import server
from lamson.routing import Router
from lamson.testing import *
from nose.tools import *
import os

relay = relay(port=8899)

def setup():
    Router.clear_routes()
    Router.clear_states()
    Router.load(['lamson_tests.simple_fsm_mod'])


def test_clear_queue():
    queue().push("Test")
    assert queue().count() > 0

    clear_queue()
    assert queue().count() == 0


def test_relay():
    clear_queue()
    relay.send('test@localhost', 'zedshaw@localhost', 'Test message', 'Test body')
    assert queue().keys()

def test_delivered():
    clear_queue()
    relay.send("zedshaw@localhost", "tester@localhost", Subject="Test subject.", Body="Test body.")
    assert delivered("zedshaw@localhost"), "Test message not delivered."
    assert delivered("zedshaw@localhost"), "Test message not delivered."
    assert not delivered("badman@localhost")
    assert_in_state('lamson_tests.simple_fsm_mod', 'zedshaw@localhost', 'tester@localhost', 'START')

def test_RouterConversation():
    client = RouterConversation('tester@localhost', 'Test router conversations.')
    client.begin()
    client.say('testlist@localhost', 'This is a test')

def test_spelling():
    # specific to a mac setup, because macs are lame
    if 'PYENCHANT_LIBRARY_PATH' not in os.environ:
        os.environ['PYENCHANT_LIBRARY_PATH'] = '/opt/local/lib/libenchant.dylib'

    template = "tests/lamson_tests/templates/template.txt"
    contents = open(template).read()
    assert spelling(template, contents) 

########NEW FILE########
__FILENAME__ = utils_tests
from nose.tools import *
from lamson import utils, view
from mock import *


def test_make_fake_settings():
    settings = utils.make_fake_settings('localhost', 8800)
    assert settings
    assert settings.receiver
    assert settings.relay == None
    settings.receiver.close()

def test_import_settings():
    loader = view.LOADER

    settings = utils.import_settings(True, from_dir='tests', boot_module='config.testing')
    assert settings
    assert settings.receiver_config

    view.LOADER = loader
    settings = utils.import_settings(False, from_dir='examples/osb')
    assert settings
    assert settings.receiver_config



@patch('daemon.DaemonContext.open')
def test_daemonize_not_fully(dc_open):
    context = utils.daemonize("run/tests.pid", ".", False, False, do_open=False)
    assert context
    assert not dc_open.called
    dc_open.reset_mock()

    context = utils.daemonize("run/tests.pid", ".", "/tmp", 0002, do_open=True)
    assert context
    assert dc_open.called


@patch("daemon.daemon.change_process_owner")
def test_drop_priv(cpo):
    utils.drop_priv(100, 100)
    assert cpo.called


########NEW FILE########
__FILENAME__ = view_tests
from nose.tools import *
from lamson import view
import jinja2


def test_load():
    template = view.load("template.txt")
    assert template
    assert template.render()

def test_render():
    # try with some empty vars
    text = view.render({}, "template.txt")
    assert text


def test_most_basic_form():
    msg = view.respond(locals(), 'template.txt')
    assert msg.Body

def test_respond_cadillac_version():
    dude = 'Tester'

    msg = view.respond(locals(), Body='template.txt', 
                      Html='template.html',
                      From='test@localhost',
                      To='receiver@localhost',
                      Subject='Test body from "%(dude)s".')

    assert msg.Body
    assert msg.Html

    for k in ['From', 'To', 'Subject']:
        assert k in msg


def test_respond_plain_text():
    dude = 'Tester'

    msg = view.respond(locals(), Body='template.txt', 
                      From='test@localhost',
                      To='receiver@localhost',
                      Subject='Test body from "%(dude)s".')

    assert msg.Body
    assert not msg.Html

    for k in ['From', 'To', 'Subject']:
        assert k in msg



def test_respond_html_only():
    dude = 'Tester'

    msg = view.respond(locals(), Html='template.html', 
                      From='test@localhost',
                      To='receiver@localhost',
                      Subject='Test body from "%(dude)s".')

    assert not msg.Body
    assert msg.Html

    for k in ['From', 'To', 'Subject']:
        assert k in msg



def test_respond_attach():
    dude = "hello"
    mail = view.respond(locals(), Body="template.txt",
                       From="test@localhost",
                       To="receiver@localhost",
                       Subject='Test body from someone.')

    view.attach(mail, locals(), 'template.html', content_type="text/html",
               filename="template.html", disposition='attachment')

    assert_equal(len(mail.attachments), 1)

    msg = mail.to_message()
    assert_equal(len(msg.get_payload()), 2)
    assert str(msg)

    mail.clear()

    view.attach(mail, locals(), 'template.html', content_type="text/html")
    assert_equal(len(mail.attachments), 1)

    msg = mail.to_message()
    assert_equal(len(msg.get_payload()), 2)
    assert str(msg)


def test_unicode():
    dude = u'H\xe9avy M\xe9t\xe5l Un\xeec\xf8d\xe9'
    mail = view.respond(locals(), Html="unicode.html",
                       From="test@localhost",
                       To="receiver@localhost",
                       Subject='Test body from someone.')
    assert str(mail)

    view.attach(mail, locals(), "unicode.html", filename="attached.html")

    assert str(mail)


########NEW FILE########
