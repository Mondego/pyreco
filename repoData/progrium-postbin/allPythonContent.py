__FILENAME__ = bin
import wsgiref.handlers
from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from models import Bin, Post
import urllib
import re
import hashlib
from cgi import FieldStorage
import logging
from google.appengine.api.labs import taskqueue

class NotFound(Exception): pass


class BinHandler(webapp.RequestHandler):
    def get(self):
        path = self.request.path
        if path[-1] == '/':
            self.redirect(path[:-1])
        path, feed = re.subn(r'^(.+)\/feed$', r'\1', path)
        bin = self._get_bin(path)
        if self.request.query_string:
            self._record_post(bin, True)
            self.redirect('/%s' % bin.name)
        else:
            posts = bin.post_set.order('-created').fetch(50)
            self.response.out.write(template.render('templates/bin.%s' % ('atom' if feed else 'html'), 
                {'bin':bin, 'posts':posts, 'request':self.request}))

    def post(self):
        bin = self._get_bin(self.request.path)
        post = self._record_post(bin)
        # TODO: This should maybe be a header thing
        if 'http://' in self.request.query_string:
            params = dict(self.request.POST.items())
            params['_url'] = self.request.query_string
            urlfetch.fetch(url='http://hookah.progrium.com/dispatch',
                            payload=urllib.urlencode(params), method='POST')
        taskqueue.add(url='/tasks/newpost', params={'ip': post.remote_addr, 'size': post.size, 'bin': bin.name})
        self.response.set_status(201)
        self.response.headers['Location'] = str("/%s" % bin.name)
        self.response.out.write('<html><head><meta http-equiv="refresh" content="0;url=/%s" /></head><body>201 Created. Redirecting...</body></html>' % bin.name)
    
    def head(self):
        bin = self._get_bin(self.request.path)
        if self.request.query_string:
            self._record_post(bin, True)
        else:
            self._record_post(bin)

    def handle_exception(self, exception, debug_mode):
        if isinstance(exception, NotFound):
            self.error(404)
        else:
            super(BinHandler, self).handle_exception(exception, debug_mode)

    def _record_post(self, bin, use_get=False):
        post = Post(bin=bin, remote_addr=self.request.remote_addr)
        post.headers        = dict(self.request.headers)
        try:
            post.body           = self.request.body
        except UnicodeDecodeError:
            #post.body_binary    = self.request.body
            pass
        post.query_string   = self.request.query_string
        post.form_data = []
        data_source = self.request.GET if use_get else self.request.POST
        post.size = len(post.body) if post.body else 0
        for k,v in data_source.items():
            if isinstance(v, FieldStorage):
                file_body = v.file.read()
                post.form_data.append([k, {
                    'file_name': v.filename,
                    'file_extension': v.filename.split('.')[-1],
                    'file_digest': hashlib.md5(file_body).hexdigest(),
                    'file_size': round(len(file_body) / 1024.0, 1),
                }])
                post.size += len(file_body)
            else:
                post.form_data.append([k,v])
        post.put()
        return post

    def _get_bin(self, path):
        name = path[1:].split('/')[0]
        bin = Bin.all().filter('name =', name).get()
        if bin:
            return bin
        else:
            raise NotFound()



if __name__ == '__main__':
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([
        ('/.*', BinHandler),
        ], debug=True))

########NEW FILE########
__FILENAME__ = main
import wsgiref.handlers
import datetime
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from models import Bin, Post, App
from google.appengine.api import datastore_errors
from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.runtime import DeadlineExceededError
import time, yaml

class MainHandler(webapp.RequestHandler):
    def get(self):
        app = App.instance()
        self.response.out.write(template.render('templates/main.html', locals()))

    def post(self):
        bin = Bin()
        bin.put()
        self.redirect('/%s' % bin.name)

class StatsHandler(webapp.RequestHandler):
    def get(self):
        posts = Post.all().order('-size').fetch(20)
        try:
            current_post = None
            for post in posts:
                current_post = post
                bin = post.bin
            self.response.out.write(template.render('templates/stats.html', locals()))
        except datastore_errors.Error, e:
            if e.args[0] == "ReferenceProperty failed to be resolved":
                current_post.delete()
                self.redirect('/stats')

class BlacklistHandler(webapp.RequestHandler):
    def get(self):
        blacklist = yaml.load(open('dos.yaml').read())
        blacklist = [(b['subnet'], b['description'].split(' - ')) for b in blacklist['blacklist']]
        self.response.out.write(template.render('templates/blacklist.html', locals()))

class CleanupTask(webapp.RequestHandler):
    def get(self):
        posts = Post.all().filter('created <', datetime.datetime.now() - datetime.timedelta(days=90))
        assert posts.count()
        try:
            while True:
                db.delete(posts.fetch(100))
                time.sleep(0.1)
        except DeadlineExceededError:
            self.response.clear()
            self.response.set_status(200)

class NewPostTask(webapp.RequestHandler):
    def post(self):
        app = App.instance()
        app.total_posts += 1
        app.put()
        ip = self.request.get('ip')
        bin = self.request.get('bin')
        size = int(self.request.get('size'))
        day = datetime.datetime.now().day
        
        daily_ip_key = 'usage-%s-%s' % (day, ip)
        daily_ip_usage = memcache.get(daily_ip_key) or 0
        memcache.set(daily_ip_key, int(daily_ip_usage)+size, time=24*3600)
        if daily_ip_usage > 500000000: # about 500MB
            mail.send_mail(sender="progrium@gmail.com", to="progrium@gmail.com",
                subject="PostBin user IP over quota", body=ip)
        
        daily_bin_key = 'usage-%s-%s' % (day, bin)
        daily_bin_usage = memcache.get(daily_bin_key) or 0
        memcache.set(daily_bin_key, int(daily_bin_usage)+size, time=24*3600)
        if daily_bin_usage > 10485760: # 10MB
            obj = Bin.get_by_name(bin)
            obj.delete()

if __name__ == '__main__':
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/stats', StatsHandler), 
        ('/tasks/cleanup', CleanupTask),
        ('/tasks/newpost', NewPostTask),
        ('/blacklist', BlacklistHandler)], debug=True))

########NEW FILE########
__FILENAME__ = models
import time
import yaml
import datetime
from google.appengine.ext import db
from google.appengine.api import datastore_types
from google.appengine.api import memcache
from django.utils import simplejson


def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])
    
class ObjectProperty(db.Property):
    data_type = datastore_types.Text
    def get_value_for_datastore(self, model_instance):
        value = super(ObjectProperty, self).get_value_for_datastore(model_instance)
        return db.Text(self._deflate(value))
    def validate(self, value):
        return self._inflate(value)
    def make_value_from_datastore(self, value):
        return self._inflate(value)
    def _inflate(self, value):
        if value is None:
            return {}
        if isinstance(value, basestring):
            return simplejson.loads(value)
        return value
    def _deflate(self, value):
        return simplejson.dumps(value)

class App(db.Model):
    total_posts = db.IntegerProperty(default=0)
    
    @classmethod
    def instance(cls):
        app = cls.all().get()
        if not app:
            app = App()
            app.put()
        return app

class Bin(db.Model):
    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        kwargs['name'] = kwargs.get('name', baseN(abs(hash(time.time())), 36))
        super(Bin, self).__init__(*args, **kwargs)
    
    @classmethod
    def get_by_name(cls, name):
        return Bin.all().filter('name =', name).get()
    
    def usage_today_in_bytes(self):
        day = datetime.datetime.now().day
        daily_bin_key = 'usage-%s-%s' % (day, self.name)
        return memcache.get(daily_bin_key) or 0
    
    def usage_today_in_megabytes(self):
        return self.usage_today_in_bytes() / 1048576 
        
class Post(db.Model):
    bin = db.ReferenceProperty(Bin)
    created = db.DateTimeProperty(auto_now_add=True)
    remote_addr = db.StringProperty(required=True)
    headers = ObjectProperty()
    query_string = db.StringProperty()
    form_data = ObjectProperty()
    body = db.TextProperty()
    size = db.IntegerProperty()
    #body_binary = db.BlobProperty()
    
    def id(self):
        return baseN(abs(hash(self.created)), 36)[0:6]

    def __iter__(self):
        out = []
        if self.form_data:
            if hasattr(self.form_data, 'items'):
                items = self.form_data.items()
            else:
                items = self.form_data
            for k,v in items:
                try:
                    outval = simplejson.dumps(simplejson.loads(v), sort_keys=True, indent=2)
                except (ValueError, TypeError):
                    outval = v
                out.append((k, outval))
        else:
            try:
                out = (('body', simplejson.dumps(simplejson.loads(self.body), sort_keys=True, indent=2)),)
            except (ValueError, TypeError):
                out = (('body', self.body),)

        # Sort by field/file then by field name
        files = list()
        fields = list()
        for (k,v) in out:
            if type(v) is dict:
                files.append((k,v))
            else:
                fields.append((k,v))
        return iter(sorted(fields) + sorted(files))

    def __str__(self):
        return '\n'.join("%s = %s" % (k,v) for k,v in self)

########NEW FILE########
