__FILENAME__ = api
import wsgiref.handlers
import hashlib, time, os, re
import base64
import logging

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch, memcache
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

from models import Account, Notification, Channel
from config import API_HOST, API_VERSION
from app import RequestHandler

def strip_tags(value):
    return re.sub(r'<[^>]*?>', '', value or '')

class ReplayHandler(RequestHandler):
    def post(self, hash): 
        hash = hash.lower()
        notice = Notification.all().filter('hash =', hash).get()
        target = Account.all().filter('api_key =', self.request.get('api_key')).get()
        channel = notice.channel
        if notice and channel.status == 'enabled' and channel.target.key() == target.key():
            notice.dispatch()
            self.response.out.write("OK\n")
        else:
            self.error(404)


class NotifyHandler(RequestHandler):
    def post(self, hash): 
        hash = hash.lower()
        target = Account.all().filter('hash =', hash).get()
        if not target:
            target = Account.all().filter('hashes =', hash).get()
        source = Account.all().filter('api_key =', self.request.get('api_key')).get()
        
        channel = Channel.all().filter('target =', target).filter('source =', source).get()
        approval_notice = None
        if not channel and source and target:
            channel = Channel(target=target, source=source, outlet=target.get_default_outlet())
            channel.put()
            approval_notice = channel.get_approval_notice()
            channel.send_activation_email()
            
        if channel:
            notice = Notification(channel=channel, text=strip_tags(self.request.get('text')), icon=source.source_icon)
            for arg in ['title', 'link', 'icon', 'sticky', 'tags']:
                value = strip_tags(self.request.get(arg, None))
                if value:
                    setattr(notice, arg, value)
            notice.put()
            
            # Increment the counter on the channel to represent number of notices sent
            channel.count += 1
            channel.put()
            
            if channel.status == 'enabled':
                notice.dispatch()
                self.response.out.write("OK\n")
                
            elif channel.status == 'pending':
                self.response.set_status(202)
                if approval_notice:
                    approval_notice.dispatch()
                    self.response.out.write("OK\n")
                else:
                    self.response.out.write("202 Pending approval")
            elif channel.status == 'disabled':
                self.response.set_status(202)
                self.response.out.write("202 Accepted but disabled")
        else:
            self.error(404)
            self.response.out.write("404 Target or source not found")

class HistoryHandler(webapp.RequestHandler):
    def get(self):
        try:
            method, encoded = self.request.headers['AUTHORIZATION'].split()
            if method.lower() == 'basic':
                username, password = base64.b64decode(encoded).split(':')
                account = Account.all().filter('api_key =', username).get()
                if account:
                    notifications = Notification.get_history_by_target(account).fetch(20)
                    self.response.headers['Content-Type'] = 'application/json'
                    def to_json(notice):
                        o = notice.to_dict()
                        o['created'] = notice.created.strftime('%a %b %d %H:%M:%S +0000 %Y')
                        o['source_icon'] = notice.source.source_or_default_icon()
                        return simplejson.dumps(o)
                    self.response.out.write("[%s]" % ', '.join([to_json(n) for n in notifications]))
                else:
                    raise KeyError()
        except KeyError:
            self.response.headers['WWW-Authenticate'] = 'Basic realm="%s"' % 'Notify.io'
            self.error(401)

class ListenHandler(webapp.RequestHandler):
    def get(self, hash):
        if not 'Nio/1.0 CFNetwork' in self.request.headers['user-agent']:
            self.redirect('http://listen.notify.io/~1/listen/%s' % hash)
        else:
            message = memcache.get(self.request.remote_addr)
            if not message:
                memcache.set(self.request.remote_addr, True, time=300)
                self.response.out.write('{"text": "Click here to upgrade your client", "title": "This client is now deprecated", "link": "http://code.google.com/p/notify-io/downloads/detail?name=DesktopNotifier.dmg"}\n')
            else:
                time.sleep(20)

class VerifyHandler(webapp.RequestHandler):
  def get(self, hash):
    if Account.all().filter('api_key =', self.request.get('api_key')).get():
      if (Account.all().filter('hash =', hash.lower()).get()) or (Account.all().filter('hashes =', hash.lower()).get()):
        self.response.out.write("200 OK")
      else:
        self.error(404)
        self.response.out.write("404 User not found")
    else:
      self.error(403)
      self.response.out.write("403 Missing required parameters")

def application():
   return webapp.WSGIApplication([
        ('/v1/notify/(.*)', NotifyHandler),
        ('/v1/replay/(.*)', ReplayHandler),
        ('/v1/listen/(.*)', ListenHandler),
        ('/v1/users/(.*)', VerifyHandler),
        ('/api/history.json', HistoryHandler)
        ], debug=True)


def main():
  wsgiref.handlers.CGIHandler().run(application())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = app
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users

from models import Account, Channel, Outlet, Notification
from config import API_HOST, WWW_HOST, API_VERSION 

register = webapp.template.create_template_register()

@register.filter
def replace(value, arg):
    old, new = arg.split(',')
    return value.replace(old, new)

@register.filter
def shortago(value):
    value = value.replace(' hours', 'h').replace(' hour', 'h') \
                .replace(' minutes', 'm').replace(' minute', 'm') \
                .replace(' days', 'd').replace(' day', 'd')
    return '%s ago' % value

class RequestHandler(webapp.RequestHandler):
    def initialize(self, request, response):
        super(RequestHandler, self).initialize(request, response)
        self.user = users.get_current_user()
        if self.user:
            self.login_url = None
            self.logout_url = users.create_logout_url('/')
            self.account = Account.all().filter('user =', self.user).get()
            if not self.account:
                # Set up a Notify.io account
                
                self.account = Account()
                self.account.set_hash_and_key()
                #self.account.source_name = self.user.nick() # More useful default than None
                self.account.put()
                
                # Create default Desktop Notifier
                o = Outlet(target=self.account, type_name='DesktopNotifier')
                o.set_name("Default Desktop Notifier")
                o.put()
             
            # This is to update existing accounts before outlets   
            if not self.account.get_default_outlet():
                # Create default Desktop Notifier
                o = Outlet(target=self.account, type_name='DesktopNotifier')
                o.set_name("Default Desktop Notifier")
                o.put()
                for channel in Channel.get_all_by_target(self.account):
                    if not channel.outlet:
                        channel.outlet = o
                        channel.put()
                
        else:
            self.logout_url = None
            self.account = None
            self.login_url = users.create_login_url(request.path)
        
        # Hide the Get Started tip
        if request.query_string == 'hide':
            self.account.started = True
            self.account.put()
    
    def render(self, template_path, locals):
        locals.update({
            'user': self.user,
            'logout_url': self.logout_url,
            'login_url': self.login_url,
            'account': self.account,
            'api_host': API_HOST,
            'api_version': API_VERSION,
            'www_host': WWW_HOST,
        })
        self.response.out.write(template.render(template_path, locals))

class DashboardHandler(RequestHandler):
    def render(self, template_path, locals):
        locals['pending_channels'] = Channel.get_all_by_target(self.account).filter('status =', 'pending').fetch(10)
        locals['recent_notifications'] = Notification.get_history_by_target(self.account).fetch(3)
        super(DashboardHandler, self).render(template_path, locals)
########NEW FILE########
__FILENAME__ = config
import os

try:
    is_dev = os.environ['SERVER_SOFTWARE'].startswith('Dev')
except:
    is_dev = False

API_VERSION = 'v1'
if is_dev:
    API_HOST = 'localhost:8081'
    WWW_HOST = 'localhost:8081'
else:
    API_HOST = 'api.notify.io'
    WWW_HOST = 'www.notify.io'
########NEW FILE########
__FILENAME__ = main
import wsgiref.handlers
import hashlib, time, os, logging

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

from models import Account, Notification, Channel, Outlet, Email
from app import RequestHandler, DashboardHandler
from config import API_HOST, API_VERSION
import outlet_types

template.register_template_library('app')

class MainHandler(RequestHandler):
    def get(self):
        self.render('templates/main.html', locals())

class GetStartedHandler(RequestHandler):
    def get(self):
        if self.account:
            start_outlet = self.account.get_default_outlet()
        self.render('templates/getstarted.html', locals())
        
class SourcesAvailableHandler(RequestHandler):
    def get(self):
        self.render('templates/sources_available.html', locals())

class SettingsHandler(DashboardHandler):
    @login_required
    def get(self):
        if 'activate' in self.request.path:
            Email.activate(self.request.path.split('/')[-1])
            self.redirect('/settings')
        else:
            self.render('templates/settings.html', locals())
    
    def post(self):
        action = self.request.get('action')
        if action == 'reset':
            self.account.set_hash_and_key()
        elif action == 'addemail':
            email = self.request.get('email')
            if not Email.find_existing(email):
                e = Email(email=self.request.get('email'), account=self.account)
                e.send_activation_email()
                e.put()
        elif action == 'removeemail':
            e = Email.get_by_id(int(self.request.get('email-id')))
            if e.account.key() == self.account.key():
                if e.hash() in self.account.hashes:
                    self.account.hashes.remove(e.hash())
                    self.account.put()
                e.delete()
        else:
            if self.request.get('source_enabled', None):
                self.account.source_enabled = True
                self.account.source_name = self.request.get('source_name', None)
                self.account.source_url = self.request.get('source_url', None)
                self.account.source_icon = self.request.get('source_icon', None)
            else:
                self.account.source_enabled = False
        self.account.put()
        self.redirect('/settings')

class HistoryHandler(DashboardHandler):
    @login_required
    def get(self):
        notifications = Notification.get_history_by_target(self.account).fetch(20)
        self.render('templates/history.html', locals())
    
    def post(self):
        action = self.request.get('action')
        if action == 'delete':
            notice = Notification.get_by_hash(self.request.get('notification'))
            if self.account.key() == notice.target.key():
                notice.delete()
        self.redirect('/history')

class SourcesHandler(DashboardHandler):
    @login_required
    def get(self):
        outlets = Outlet.all().filter('target =', self.account).fetch(100)
        if len(self.request.path.split('/')) > 2:
            source = Account.get_by_hash(self.request.path.split('/')[-1])
            channel = Channel.get_by_source_and_target(source, self.account)
            self.render('templates/source.html', locals())
        else:
            enabled_channels = Channel.get_all_by_target(self.account).order('-count').filter('status =', 'enabled')
            # TODO: remove me after a while. this is to fix my poor reference management
            for c in enabled_channels:
                try:
                    c.outlet
                except:
                    c.outlet = None
                    c.put()
            self.render('templates/sources.html', locals())
    
    def post(self):
        action = self.request.get('action')
        source = Account.get_by_hash(self.request.get('source'))
        channel = Channel.get_by_source_and_target(source, self.account)
        if action == 'approve':
            channel.status = 'enabled'
            channel.put()
        elif action == 'delete':
            channel.delete()
        elif action == 'route':
            outlet = Outlet.get_by_hash(self.request.get('outlet'))
            channel.outlet = outlet
            channel.put()
            
        if 'return' in self.request.query_string:
            self.redirect('/sources/%s' % self.request.get('source'))
        else:
            self.redirect('/sources')

class OutletsHandler(DashboardHandler):
    @login_required
    def get(self):
        if self.request.path.endswith('.ListenURL'):
            filename = self.request.path.split('/')[-1]
            outlet = filename.split('.')[0]
            
            self.account.started = True
            self.account.put()

            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Content-disposition'] = 'attachment; filename=%s.ListenURL' % outlet
            self.response.out.write("http://%s/%s/listen/%s\n" % (API_HOST, API_VERSION, outlet))
        else:
            types = outlet_types.all
            outlets = Outlet.all().filter('target =', self.account)
            self.render('templates/outlets.html', locals())
    
    def post(self):
        action = self.request.get('action')
        if action == 'add':
            o = Outlet(target=self.account, type_name=self.request.get('type'))
            o.setup(self.request.POST)
            o.put()
        elif action == 'remove':
            o = Outlet.get_by_hash(self.request.get('outlet'))
            o.delete()
        elif action == 'rename':
            name = self.request.get('name')
            if name:
                o = Outlet.get_by_hash(self.request.get('outlet'))
                o.name = name
                o.put()
        self.redirect('/outlets')

def redirect_to(path):
    class redirector(webapp.RequestHandler):
        def get(self):
            self.redirect(path)
    return redirector

def application():
  return webapp.WSGIApplication([
    ('/', MainHandler), 
    ('/getstarted', GetStartedHandler),
    ('/sources/available', SourcesAvailableHandler),
    ('/settings.*', SettingsHandler),
    ('/history', HistoryHandler),
    ('/sources.*', SourcesHandler),
    ('/outlets.*', OutletsHandler),
    ('/dashboard/history', redirect_to('/history')),
    ('/dashboard/settings', redirect_to('/settings')),
    ('/dashboard/sources', redirect_to('/sources')),
    ], debug=True)

def main():
   wsgiref.handlers.CGIHandler().run(application())


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = models
import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail, users, urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

import logging

from config import WWW_HOST
import outlet_types

def baseN(num,b=36,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class Account(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    hash = db.StringProperty()
    hashes = db.StringListProperty()
    api_key = db.StringProperty()
    
    source_enabled = db.BooleanProperty()
    source_name = db.StringProperty()
    source_url = db.StringProperty()
    source_icon = db.StringProperty()
    
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    started = db.BooleanProperty(default=False)

    @classmethod
    def get_by_user(cls, user):
        return cls.all().filter('user =', user).get()
    
    @classmethod
    def get_by_hash(cls, hash):
        return cls.all().filter('hash = ', hash).get()

    def source_or_default_icon(self):
        return self.source_icon or 'http://%s/favicon.ico' % WWW_HOST

    def get_default_outlet(self):
        return Outlet.all().filter('target =', self).filter('type_name =', 'DesktopNotifier').order('-created').get()

    def set_hash_and_key(self):
        self.hash = hashlib.md5(self.user.email().lower()).hexdigest()
        d = hashlib.md5(str(time.time()) + self.hash).hexdigest()
        self.api_key = '-'.join([d[0:6], d[8:14], d[16:22], d[24:30]])

class Email(db.Model):
    account = db.ReferenceProperty(Account, required=True)
    email = db.StringProperty(required=True)
    pending_token = db.StringProperty()
    
    def __init__(self, *args, **kwargs):
        kwargs['pending_token'] = kwargs.get('pending_token', hashlib.sha1(str(time.time())).hexdigest())
        super(Email, self).__init__(*args, **kwargs)
    
    def hash(self):
        return hashlib.md5(self.email).hexdigest()
    
    def send_activation_email(self):
        if self.pending_token:
            mail.send_mail(
                sender="Notify.io <no-reply@notify-io.appspotmail.com>",
                to=self.email,
                subject="Activate additional email address",
                body="Hello,\n\nClick on this link to activate this email address:\nhttp://%s/settings/activate/%s" % (WWW_HOST, self.pending_token))
        else:
            raise Exception("pending_token is not set")
    
    @classmethod
    def activate(cls, token):
        email = cls.all().filter('pending_token =', token).get()
        if email:
            email.account.hashes.append(email.hash())
            email.account.put()
            email.pending_token = None
            email.put()
    
    @classmethod
    def find_existing(cls, email):
        hash = hashlib.md5(email).hexdigest()
        found = Account.all().filter('hash =', hash).get()
        if not found:
            found = Account.all().filter('hashes =', hash).get()
        if not found:
            found = Email.all().filter('email =', email).get()
        return found

class Outlet(db.Model):
    hash = db.StringProperty()
    target = db.ReferenceProperty(Account, required=True)
    type_name = db.StringProperty(required=True)
    name = db.StringProperty()
    params = db.StringProperty()
    
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    

    def __init__(self, *args, **kwargs):
        kwargs['hash'] = kwargs.get('hash', hashlib.sha1(str(time.time())).hexdigest())
        super(Outlet, self).__init__(*args, **kwargs)
    
    @classmethod
    def get_by_hash(cls, hash):
        return cls.all().filter('hash = ', hash).get()
    
    def delete(self):
        for channel in Channel.get_all_by_target(self.target):
            channel.outlet = None
            channel.put()
        super(Outlet, self).delete()
    
    def type(self):
        return outlet_types.get(self.type_name)
    
    def is_push(self):
        return self.type().push
    
    def push_destination(self):
        if self.is_push():
            return [self.type().fields[0], self.get_param(self.type().fields[0])]
        else:
            return None
    
    def get_param(self, key):
        return simplejson.loads(self.params)[key]
    
    def set_params(self, input):
        params = dict()
        for f in self.type().fields:
            params[f] = input.get(f)
        self._tmp_params = params
        self.params = simplejson.dumps(params)
    
    def set_name(self, name=None):
        if not name:
            name = self.type().default_name(self._tmp_params)
        self.name = name
    
    def setup(self, params):
        self.set_params(params)
        self.set_name()
        self.type().setup(self)


class Channel(db.Model):
    target = db.ReferenceProperty(Account, required=True, collection_name='channels_as_target')
    source = db.ReferenceProperty(Account, required=True, collection_name='channels_as_source')
    outlet = db.ReferenceProperty(Outlet)
    count = db.IntegerProperty(default=0)

    status = db.StringProperty(required=True, default='pending')
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
    @classmethod
    def get_all_by_target(cls, account):
        return cls.all().filter('target =', account)

    @classmethod
    def get_all_by_source(cls, account):
        return cls.all().filter('source =', account)
    
    @classmethod
    def get_by_source_and_target(cls, source, target):
        return cls.all().filter('source =', source).filter('target =', target).get()
    
    def delete(self):
        notices = Notification.all().filter('channel =', self)
        for n in notices:
            n.channel = None
            n.put()
        super(Channel, self).delete()
    
    def get_approval_notice(self):
        notice = Notification(channel=self, target=self.target, text="%s wants to send you notifications. Click here to approve/deny this request." % self.source.source_name)
        notice.title = "New Notification Source"
        notice.link = "http://%s/sources" % WWW_HOST
        notice.icon = self.source.source_icon
        notice.sticky = 'true'
        return notice

    def send_activation_email(self):
        if self.status == 'pending':
            mail.send_mail(
                sender="Notify.io <no-reply@notify-io.appspotmail.com>",
                to="%s@gmail.com" % self.target.user,
                subject="Approve a channel",
                body="Hello,\n\nClick on this link to approve this channel:\n http://%s/sources" % WWW_HOST)
        else:
            raise Exception("Channel not pending")
 
class Notification(db.Model):
    hash = db.StringProperty()
    channel = db.ReferenceProperty(Channel)
    target = db.ReferenceProperty(Account, collection_name='target_notifications')
    source = db.ReferenceProperty(Account, collection_name='source_notifications')
    
    title = db.StringProperty()
    text = db.StringProperty(multiline=True, required=True)
    link = db.StringProperty()
    icon = db.StringProperty()
    sticky = db.StringProperty()
    tags = db.StringProperty()

    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        channel = kwargs.get('channel')
        if channel and isinstance(channel, Channel):
            kwargs['source'] = channel.source
            kwargs['target'] = channel.target
        kwargs['hash'] = kwargs.get('hash', hashlib.sha1(str(time.time())).hexdigest())
        super(Notification, self).__init__(*args, **kwargs) 
    
    def dispatch(self):
        if self.channel.outlet:
            return str(self.channel.outlet.type().dispatch(self))
        else:
            return ''
    
    @classmethod
    def get_by_hash(cls, hash):
        return cls.all().filter('hash = ', hash).get()

    @classmethod
    def get_history_by_target(cls, target):
        return cls.all().filter('target =', target).order('-created')
    
    def icon_with_default(self):
        return self.icon or self.source.source_or_default_icon()
    
    def to_dict(self):
        o = {'text': self.text.replace('\r\n', '\n')}
        for arg in ['title', 'link', 'icon', 'sticky', 'tags']:
            value = getattr(self, arg)
            if value:
                o[arg] = value
        o['source'] = self.source.source_name
        return o
        
    def to_json(self):
        return simplejson.dumps(self.to_dict())

########NEW FILE########
__FILENAME__ = outlet_types
from django.utils import simplejson
from google.appengine.api import mail, xmpp, urlfetch
import urllib
import logging
import base64

try:
  import keys
except ImportError:
  keys = None

def push_to_realtime(hash, message):
    #urlfetch.make_fetch_call(urlfetch.create_rpc(),'https://AC43b69b055a6b5299cd211a53d82047bb.twiliort.com/~1/listen/%s' % hash, 
    urlfetch.fetch('https://AC43b69b055a6b5299cd211a53d82047bb.twiliort.com/~1/listen/%s' % hash, 
        method='POST', payload=message, headers={
            "Content-Type": "application/json", 
            "Authorization": 'Basic %s' % base64.encodestring('%s:x' % keys.auth_token)[:-1]})

class BaseOutlet(object):
    name = None
    push = True
    fields = []
    help = ""
    
    @classmethod
    def type(cls):
        return str(cls).split('.')[-1][:-2]
        
    @classmethod
    def default_name(cls, params):
        pass
    
    @classmethod
    def setup(cls, outlet):
        pass
    
    @classmethod
    def dispatch(cls, notice):
        return ":".join([notice.channel.outlet.hash, notice.to_json()])

class Prowl(BaseOutlet):
	name = "Prowl"
	fields = ['api_key']
	help = 'Get your API key at the <a href="http://prowl.weks.net/">Prowl website</a>.'
	
	@classmethod
	def default_name(cls, params):
		return "An iPhone with Prowl" 

	@classmethod
	def dispatch(cls, notice):
		api_key = notice.channel.outlet.get_param('api_key')
		data = {
		    'apikey': api_key,
            'application': notice.source.source_name,
            'event': notice.title or '',
            'description': notice.text,
	    }
		data = urllib.urlencode(utf8encode(data))
		urlfetch.fetch("https://prowl.weks.net/publicapi/add/", method='POST', payload=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
		return None
		
		

class NMA(BaseOutlet):
	name = "NotifyMyAndroid"
	fields = ['api_key']
	help = 'Get your API key at <a href="http://nma.usk.bz/">NotifyMyAndroid website</a>.'
	
	@classmethod
	def default_name(cls, params):
		return "An Android with NotifyMyAndroid" 

	@classmethod
	def dispatch(cls, notice):
		api_key = notice.channel.outlet.get_param('api_key')
		data = {
		    'apikey': api_key,
            'application': notice.source.source_name,
            'event': notice.title or '',
            'description': notice.text,
	    }
		data = urllib.urlencode(utf8encode(data))
		urlfetch.fetch("https://nma.usk.bz/publicapi/notify", method='POST', payload=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
		return None
		
		

class DesktopNotifier(BaseOutlet):
    name = "Desktop Notifier"
    push = False
    
    @classmethod
    def default_name(cls, params):
        return "A Desktop Notifier"
    
    @classmethod
    def dispatch(cls, notice):
        push_to_realtime(notice.channel.outlet.hash, notice.to_json())



class Email(BaseOutlet):
    name = "Email"
    fields = ['email']
    
    @classmethod
    def default_name(cls, params):
        return "Email to %s" % params['email']
    
    @classmethod
    def dispatch(cls, notice):
        email = notice.channel.outlet.get_param('email')
        mail.send_mail(sender="%s <no-reply@notify-io.appspotmail.com>" % notice.source.source_name, to=email, \
            subject="[Notification] %s" % (notice.title or notice.text), \
            body="%s\n%s\n\n---\nSent by Notify.io" % (notice.text, (notice.link or '')))
        return None

class Jabber(BaseOutlet):
    name = "Jabber IM"
    fields = ['jid']
    
    @classmethod
    def default_name(cls, params):
        return "Send IM to %s" % params['jid']
    
    @classmethod
    def setup(cls, outlet):
        jid = outlet.get_param('jid')
        xmpp.send_invite(jid)
    
    @classmethod
    def dispatch(cls, notice):
        jid = notice.channel.outlet.get_param('jid')
        if xmpp.get_presence(jid):
            body = "%s: %s" % (notice.title, notice.text) if notice.title else notice.text 
            xmpp.send_message(jid, "%s %s [%s]" % (body, notice.link or '', notice.source.source_name))
        return None

class SMS(BaseOutlet):
    name = "SMS"
    fields = ['cellnumber', 'token']
    help = 'Get an access token at <a href="http://textauth.com/">TextAuth</a>.'
    
    @classmethod
    def default_name(cls, params):
        return "Send SMS to %s" % params['cellnumber']
    
    @classmethod
    def dispatch(cls, notice):
        cellnumber = notice.channel.outlet.get_param('cellnumber')
        token = notice.channel.outlet.get_param('token')
        if notice.title:
            body = "%s: %s [%s]" % (notice.title, notice.text, notice.source.source_name) 
        else:
            body = "%s [%s]" % (notice.text, notice.source.source_name)
        urlfetch.fetch('http://www.textauth.com/api/v1/send', method='POST', payload=urllib.urlencode({
            'to': cellnumber,
            'token': token,
            'body': body,
        }))
        return None

class Webhook(BaseOutlet):
    name = "Webhook"
    fields = ['url']
    
    @classmethod
    def default_name(cls, params):
        return "Webhook at %s" % params['url']
    
    @classmethod
    def dispatch(cls, notice):
        url = notice.channel.outlet.get_param('url')
        urlfetch.fetch(url, method='POST', payload=urllib.urlencode(notice.to_dict()))
        return None

def utf8encode(source):
    return dict([(k, v.encode('utf-8') if v else None) for (k, v) in source.items()])

_globals = globals()
def get(outlet_name):
    return _globals[outlet_name]

available = ['DesktopNotifier', 'Email', 'Jabber', 'SMS', 'Webhook', 'Prowl', 'NotifyMyAndroid']
all = [get(o) for o in available]

########NEW FILE########
__FILENAME__ = test_placeholder
from webtest import TestApp
from api import application

app = TestApp(application())

def test_placeholder():
  app.post("/v1/notify/1234", status=404)


########NEW FILE########
__FILENAME__ = test_verify_userhash
from webtest import TestApp
from api import application
from google.appengine.api import users
from models import Account
import test

app = TestApp(application())

def test_unauthenticated_request():
  """
  Should return a 403 if request does not provide a valid api key
  """
  response = app.get("/v1/users/abcdef", status=403)
  assert response.body == "403 Missing required parameters"

  test.reset_datastore()


def test_verify_non_existing_user():
  """
  Should return a 404 if userhash does not have a Notify.io account
  """
  user = users.User("source@example.com")
  account = Account(user=user)
  account.set_hash_and_key()
  account.put()

  response = app.get("/v1/users/abcdef?api_key=%s" % account.api_key, status=404)

  assert response.body == "404 User not found"

  test.reset_datastore()


def test_verify_existing_user():
  """
  Should return 200
  """
  user = users.User("target@example.com")
  account = Account(user=user)
  account.set_hash_and_key()
  account.put()

  response = app.get("/v1/users/%s?api_key=%s" % (account.hash,
    account.api_key), status=200)

  assert response.body == "200 OK"

  test.reset_datastore()


########NEW FILE########
__FILENAME__ = test_home
from webtest import TestApp
from main import application

app = TestApp(application())

def test_foo():
  app.get("/")


########NEW FILE########
__FILENAME__ = test_account
import unittest
from models import Account
from google.appengine.api import users

class TestAccount(unittest.TestCase):
  def test_placeholder(self):

    user = users.User("target@example.com")
    account = Account(user=user)
    account.set_hash_and_key()
    account.put()

    self.assertTrue(account.user.email() == "target@example.com")


########NEW FILE########
__FILENAME__ = test_nma
import unittest
from outlet_types import NMA

class TestNMA(unittest.TestCase):
  def test_placeholder(self):
    self.assertEqual(NMA.name, "NotifyMyAndroid")


########NEW FILE########
__FILENAME__ = test_prowl
import unittest
from outlet_types import Prowl

class TestProwl(unittest.TestCase):
  def test_placeholder(self):
    self.assertEqual(Prowl.name, "Prowl")


########NEW FILE########
