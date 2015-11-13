__FILENAME__ = admin
from email.utils import parseaddr
from config.settings import relay, SPAM, CONFIRM
import logging
from lamson import view, queue
from lamson.routing import route, stateless, route_like, state_key_generator
from lamson.bounce import bounce_to
from lamson.server import SMTPError
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
    spam = queue.Queue(SPAM['queue'])
    spam.push(message)
    return SPAMMING


@route('(bad_list)@(host)', bad_list='.+')
@route('(list_name)@(host)')
@route('(list_name)-subscribe@(host)')
@bounce_to(soft=bounce.BOUNCED_SOFT, hard=bounce.BOUNCED_HARD)
def START(message, list_name=None, host=None, bad_list=None):
    list_name = list_name.lower() if list_name else None
    bad_list = bad_list.lower() if bad_list else None
    host = host.lower() if host else None

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

    elif list_name in INVALID_LISTS or message.route_from.endswith(host):
        logging.debug("LOOP MESSAGE to %r from %r.", message['to'],
                     message.route_from)
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
    list_name = list_name.lower() if list_name else None
    host = host.lower() if host else None

    original = CONFIRM.verify(list_name, message.route_from, id_number)

    if original:
        mailinglist.add_subscriber(message.route_from, list_name)

        msg = view.respond(locals(), "mail/subscribed.msg",
                           From="noreply@%(host)s",
                           To=message['from'],
                           Subject="Welcome to %(list_name)s list.")
        relay.deliver(msg)

        CONFIRM.cancel(list_name, message.route_from, id_number)

        return POSTING
    else:
        logging.warning("Invalid confirm from %s", message.route_from)
        return CONFIRMING_SUBSCRIBE


@route('(list_name)-(action)@(host)', action='[a-z]+')
@route('(list_name)@(host)')
def POSTING(message, list_name=None, action=None, host=None):
    list_name = list_name.lower() if list_name else None
    action = action.lower() if action else None
    host = host.lower() if host else None

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
    list_name = list_name.lower() if list_name else None
    host = host.lower() if host else None

    original = CONFIRM.verify(list_name, message.route_from, id_number)

    if original:
        mailinglist.remove_subscriber(message.route_from, list_name)

        msg = view.respond(locals(), 'mail/unsubscribed.msg',
                           From="noreply@%(host)s",
                           To=message['from'],
                           Subject="You are now unsubscribed from %(list_name)s.")
        relay.deliver(msg)

        CONFIRM.cancel(list_name, message.route_from, id_number)

        return START
    else:
        logging.warning("Invalid unsubscribe confirm from %s",
                        message.route_from)
        return CONFIRMING_UNSUBSCRIBE


@route("(address)@(host)", address=".+")
def BOUNCING(message, address=None, host=None):
    # don't send out a message if they are bouncing
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
from lamson import queue, view
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

def build_index():
    lists = sorted(os.listdir(settings.ARCHIVE_BASE))
    html = view.render(locals(), "web/list_index.html")
    open(os.path.join(settings.ARCHIVE_BASE, "lists.html"), "w").write(html)

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
from app.model.archive import build_index

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
        build_index()

    return mlist

def delete_list(list_name):
    assert list_name == list_name.lower()
    MailingList.objects.filter(name = list_name).delete()

def find_list(list_name):
    assert list_name == list_name.lower()
    mlists = MailingList.objects.filter(name = list_name)
    if mlists:
        return mlists[0]
    else:
        return None

def add_subscriber(address, list_name):
    assert list_name == list_name.lower()
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
    assert list_name == list_name.lower()
    find_subscriptions(address, list_name).delete()

def remove_all_subscriptions(address):
    find_subscriptions(address).delete()

def find_subscriptions(address, list_name=None):
    if list_name: assert list_name == list_name.lower()
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
    assert list_name == list_name.lower()
    mlist = find_list(list_name)
    assert mlist, "User is somehow able to post to list %s" % list_name

    for sub in mlist.subscription_set.all().values('subscriber_address'):
        list_addr = "%s@%s" % (list_name, host)
        delivery = craft_response(message, list_name, list_addr)

        subject_mod = "[%s]" % list_name

        if subject_mod not in delivery['subject']:
            delivery['subject'] = subject_mod + " " + delivery['subject']

        relay.deliver(delivery, To=sub['subscriber_address'], From=list_addr)


def craft_response(message, list_name, list_addr):
    assert list_name == list_name.lower()
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
        sender = sender.lower()
        key = key.lower()
        states = UserState.objects.filter(state_key = key,
                                          from_address = sender)
        if states:
            return states[0]
        else:
            return None

    def get(self, key, sender):
        sender = sender.lower()
        key = key.lower()
        stored_state = self._find_state(key, sender)
        if stored_state:
            return stored_state.state
        else:
            return ROUTE_FIRST_STATE

    def key(self, key, sender):
        raise Exception("THIS METHOD MEANS NOTHING TO DJANGO!")

    def set(self, key, sender, to_state):
        sender = sender.lower()
        key = key.lower()
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
        sender = sender.lower()
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
    'host': 'librelist\\.(com|org|net)',
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

os.path.walk("app/data/archive", convert_queue, None)


########NEW FILE########
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
            'sitename':"librelist.com",
            'slogan': "No logins. No tracking. Just lists.",
            'extensions':['.txt'],
            'format': 'text/x-textile',
           'siteurl': 'http://librelist.com',
        }

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
                                                 format, "\n\n".join(paras[0:2]))
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
    client.say(list_addr, 'So anyway as I was saying.')
    assert not delivered('unbounce')
    assert_in_state('app.handlers.admin', list_addr, sender, 'BOUNCING')
   
    # now have them try to unbounce
    msg = client.say('unbounce@librelist.com', "Please put me back on, I'll be good.",
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
    assert not delivered('unbounce'), "We shouldn't be sending on bounde."
    assert_equal(len(queue(queue_dir=settings.BOUNCE_ARCHIVE).keys()), 1)
    assert not mailinglist.find_subscriptions(sender, list_addr)

    # make sure that any attempts to post return a "you're bouncing dude" message
    client.say(list_addr, 'So anyway as I was saying.')
    assert not delivered('unbounce')
    assert_in_state('app.handlers.admin', list_addr, sender, 'BOUNCING')

    # now have them try to unbounce
    msg = client.say('unbounce@librelist.com', "Please put me back on, I'll be good.",
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
import os
from config import settings

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

    assert '-AT-' not in str(archived), "Should not longer be obfuscated"
    assert '<' in as_string and '"' in as_string and '>' in as_string, "Unicode email screwed up."



def test_white_list_cleanse():
    msg = MailRequest('fakepeer', None, None, open('tests/lots_of_headers.msg').read())
    resp = mailinglist.craft_response(msg, 'test.list', 'test.list@librelist.com')

    archive.white_list_cleanse(resp)
    
    for key in resp.keys():
        assert key in archive.ALLOWED_HEADERS

    assert '@' in resp['from']
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

def test_build_index():
    archive.build_index()
    assert os.path.exists(settings.ARCHIVE_BASE + "/lists.html")

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
SECRET_KEY = '####################'

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
