__FILENAME__ = admin
# -*- mode: python; coding: utf-8 -*-
import logging
import os
from drydrop.app.core.controller import AuthenticatedController
from google.appengine.api import memcache, users
from drydrop.app.core.events import log_event
from drydrop.app.models import Event, Settings

class AdminController(AuthenticatedController):

    def before_action(self, *arguments, **keywords):
        if super(AdminController, self).before_action(*arguments, **keywords): return True
        self.view.update({
            'body_class': '',
            'user': self.user,
            'users': users,
            'settings': self.handler.settings
        })
        if not users.is_current_user_admin():
            self.render_view('admin/not_admin.html', {'body_class': 'has_error'})
            return True
        
    def index(self):
        self.render_view("admin/index.html")
        
    def events_flusher(self):
        domain = os.environ['SERVER_NAME']
        deleted = Event.clear(False, 1000, domain=domain)
        done = deleted<1000
        log_event("Removed all events")
        message = 'removed %d event(s)' % deleted
        if not done: message += ' ...'
        return self.render_json_response({
            'finished': done,
            'message': message
        })
        
    def flusher(self):
        log_event("Flushed resource cache")
        vfs = self.handler.vfs
        done, num = vfs.flush_resources()
        message = 'flushed %d resource(s)' % num
        if not done: message += ' ...'
        return self.render_json_response({
            'finished': done,
            'message': message
        })
    
    def _generate_resource_index(self):
        vfs = self.handler.vfs
        resources = vfs.get_all_resources()
        if resources is None:
            resources = []
        return resources
    
    def cache(self):
        self.view['resources'] = self._generate_resource_index()
        self.render_view("admin/cache.html")

    def settings(self):
        self.render_view("admin/settings.html")

    def config(self):
        import pygments
        import pygments.lexers
        import pygments.formatters
        lexer = pygments.lexers.get_lexer_by_name('yaml')
        formatter = pygments.formatters.HtmlFormatter()
        config_source_formatted = pygments.highlight(self.handler.read_config_source_or_provide_default_one(), lexer, formatter)
        self.render_view("admin/config.html", { 'config_source_formatted': config_source_formatted })
    
    def events(self):
        offset = int(self.params.get("offset", 0))
        limit = int(self.params.get("limit", 50))
        events = Event.all().filter("domain =", os.environ['SERVER_NAME']).order('-date').fetch(limit, offset)
        res = []
        for e in events:
            res.append({
                "author": unicode(e.author),
                "action": unicode(e.action),
                "info": unicode(e.info),
                "code": e.code,
                "date": e.date
            })
        
        return self.render_json_response({
            'status': 0,
            'data': res
        })

    def flush_memcache(self):
        memcache.flush_all()
        self.render_text("OK")

    def update_option(self):
        id = self.params.get('id')
        domain=os.environ['SERVER_NAME']
        if not id:
            return self.json_error('No option id specified')
            
        known_options = ['source', 'config', 'github_login', 'github_token']
        if not id in known_options:
            return self.json_error('Unknown option id (%s)' % id)

        value = self.params.get('value') or ""
        log_event("Changed <code>%s</code> to <code>%s</code>" % (id, value))
        settings = self.handler.settings
        settings.__setattr__(id, value)
        settings.version = settings.version + 1 # this effectively invalidates cache
        settings.domain = domain
        settings.put()
            
        return self.render_text(value)

    def _generate_domain_index(self):
        settings = Settings.all()
        domains = []
        for setting in settings:
          domains.append(setting.domain)

        return domains

    def domains(self):
        self.view['domains'] = self._generate_domain_index()
        self.render_view("admin/domains.html")

########NEW FILE########
__FILENAME__ = hook
# -*- mode: python; coding: utf-8 -*-
import os
import datetime
import logging
import string
from drydrop_handler import DRY_ROOT
from drydrop.app.core.controller import BaseController
from drydrop.lib.json import json_parse
from drydrop.app.core.events import log_event

class HookController(BaseController):

    # see http://github.com/guides/post-receive-hooks
    def github(self):
        payload = self.params.get('payload', None)
        logging.info("Received github hook: %s", payload)
        if not payload:
            return
        
        data = json_parse(payload)
        paths = []
        names = []
        info = ""
        for commit in data['commits']:
            author = commit['author']['email']
            try:
                info += "<a target=\"_blank\" href=\"%s\">%s</a>: %s<br/>" % (commit['url'], commit['id'][:6], commit['message'].split("\n")[0])
            except:
                info += "?<br/>"
            try:
                names.index(author)
            except:
                names.append(author)
            try:
                paths.extend(commit['added'])
            except:
                pass
            try:
                paths.extend(commit['removed'])
            except:
                pass
            try:
                paths.extend(commit['modified'])
            except:
                pass
                
        before_url = "%s/commit/%s" % (data['repository']['url'], data['before'])
        after_url = "%s/commit/%s" % (data['repository']['url'], data['after'])
        before = "?"
        try:
            before = data['before'][:6]
        except:
            pass

        after = "?"
        try:
            after = data['after'][:6]
        except:
            pass
        
        plural = ''
        if len(paths)!=1:
            plural = 's'
        authors = string.join(names, ',')
        log_event("Received github hook for commits <a target=\"_blank\" href=\"%s\">%s</a>..<a target=\"_blank\" href=\"%s\">%s</a> (%d change%s)" % (before_url, before, after_url, after, len(paths), plural), 0, authors, info)

        repo_url = data['repository']['url'] # like http://github.com/darwin/drydrop
        branch = data['ref'].split('/').pop() # takes 'master' from 'refs/heads/master'
        
        root_url = "%s/raw/%s" % (repo_url, branch) # creates http://github.com/darwin/drydrop/raw/master
        if not root_url.endswith('/'):
            root_url = root_url + '/'
        source_url = self.handler.settings.source
        if not source_url.endswith('/'):
            source_url = source_url + '/'
            
        # now we have:
        # http://github.com/darwin/drydrop/raw/master/ in root_url
        # http://github.com/darwin/drydrop/raw/master/tutorial/ in source_url
        
        # safety check
        if not source_url.startswith(root_url):
            log_event("<a target=\"_blank\" href=\"%s\"><code>%s</code></a><br/>is not affected by incoming changeset for<br/><a target=\"_blank\" href=\"%s\"><code>%s</code></a>" % (source_url, source_url, root_url, root_url), 0, authors)
            logging.info("Source url '%s' is not affected by incoming changeset for '%s'", source_url, root_url)
            return
        
        vfs = self.handler.vfs
        for path in paths:
            prefix = source_url[len(root_url):] # prefix is 'tutorial/'
            if not path.startswith(prefix):
                logging.warning("Unexpected: path '%s' should begin with '%s'. Skipping file.", path, prefix)
            else:
                # path is something like tutorial/start.html
                path = path[len(prefix):] # stripped to 'start.html'
                logging.info("Flushing resource %s", path)
                vfs.flush_resource(path)
########NEW FILE########
__FILENAME__ = static
# -*- mode: python; coding: utf-8 -*-
import os
import datetime
import logging
from drydrop_handler import DRY_ROOT
from drydrop.app.core.controller import BaseController
from drydrop.lib.utils import *

class StaticController(BaseController):

    def static(self):
        self.base_path = os.path.join(DRY_ROOT, 'static')
        
    def after_action(self):
        path = self.params.get('path')
        return self.serve_static_file(self.base_path, path)
########NEW FILE########
__FILENAME__ = welcome
# -*- mode: python; coding: utf-8 -*-
from drydrop.app.core.controller import BaseController
import logging

class WelcomeController(BaseController):

    def index(self):
        self.render_view('welcome/index.html')

########NEW FILE########
__FILENAME__ = appceptions
# -*- mode: python; coding: utf-8 -*-
import exceptions

class PageException(exceptions.Exception):
    pass

class PageError(PageException):
    def __init__(self, errno, msg):
        self.args = (errno, msg)
        self.errno = errno
        self.errmsg = msg

class PageRedirect(PageException):
    def __init__(self, url):
        self.args = (url)
        self.url = url
        
class DownloadError(PageException):
    def __init__(self, msg):
        self.args = (msg)
        self.errmsg = msg
########NEW FILE########
__FILENAME__ = controller
# -*- mode: python; coding: utf-8 -*-
import os
import re
import logging
import datetime
import mimetypes
import time
import jinja2
import email.Utils
from Cookie import BaseCookie
from routes import url_for
from google.appengine.ext.webapp import Response
from google.appengine.api import memcache, users
from drydrop.lib.json import json_encode
from drydrop_handler import DRY_ROOT, APP_ROOT, APP_ID, VER_ID, LOCAL
from drydrop.app.models import *
from drydrop.app.core.appceptions import *
from drydrop.lib.utils import *
from drydrop.lib.jinja_loaders import InternalTemplateLoader
from drydrop.app.helpers.buster import cache_buster

class AbstractController(object):
    def __init__(self, request, response, handler):
        self.request = request
        self.response = response
        self.handler = handler
        self.view = {'params': request.params }
        self.params = request.params
        self.emited = False
        self.cookies = request.cookies
    
    def render(self, template_name):
        env = jinja2.Environment(loader = InternalTemplateLoader(os.path.join(DRY_ROOT, 'app', 'views')))
        try:
            template = env.get_template(template_name)
        except jinja2.TemplateNotFound:
            raise jinja2.TemplateNotFound(template_name)
        content = template.render(self.view)
        if LOCAL:
            content = cache_buster(content)
        self.response.out.write(content)
            
    def before_action(self):
        pass
    
    def after_action(self):
        pass
    
    def render_view(self, file_name, params = None):
        if params:
            self.view.update(params)
        self.response.headers['Content-Type'] = 'text/html'
        self.render(file_name)
        self.emited = True
    
    def render_text(self, text):
        self.response.headers['Content-Type'] = 'text/html'
        if LOCAL:
            text = cache_buster(text)
        self.response.out.write(text)
        self.emited = True
    
    def render_html(self, html, params = None):
        if params:
            self.view.update(params)
        if LOCAL:
            html = cache_buster(html)
        self.response.out.write(html)
        self.emited = True
    
    def render_xml(self, xml):
        self.response.headers['Content-Type'] = 'text/xml'
        self.render(file_name)
        self.emited = True
    
    def render_json(self, json):
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json)
        self.emited = True
    
    def redirect_to(self, url):
        """Redirects to a specified url"""
        # self.handler.redirect(url)
        # self.emited = True
        # raise PageRedirect, (url)
        
        # mrizka delala problemy pri claimovani openid
        m = re.match(r'^(.*)#.*?$', url)
        if m: url = m.group(1)
        
        logging.info("Redirecting to: %s" % url)
        
        # send the redirect!  we use a meta because appengine bombs out sometimes with long redirect urls
        self.response.out.write("<html><head><meta http-equiv=\"refresh\" content=\"0;url=%s\"></head><body></body></html>" % (url,))
        self.emited = True
        raise PageRedirect, (url)

    def notfound(self, code, message = None):
        self.response.set_status(code, str(message))
        if message is None: message = Response.http_status_message(code)
        self.view['message'] = message
        self.view['code'] = code
        self.render_view('system/notfound.html')
    
    def error(self, code, message = None):
        self.response.set_status(code, str(message))
        if message is None: message = Response.http_status_message(code)
        self.view['message'] = message
        self.view['code'] = code
        self.render_view('system/error.html')

class CookieController(AbstractController):
    def set_cookie(self, key, value='', max_age=None,
                   path='/', domain=None, secure=None, httponly=False,
                   version=None, comment=None):
        """
        Set (add) a cookie for the response
        """
        cookies = BaseCookie()
        cookies[key] = value
        for var_name, var_value in [
            ('max-age', max_age),
            ('path', path),
            ('domain', domain),
            ('secure', secure),
            ('HttpOnly', httponly),
            ('version', version),
            ('comment', comment),
            ]:
            if var_value is not None and var_value is not False:
                cookies[key][var_name] = str(var_value)
            if max_age is not None:
                cookies[key]['expires'] = max_age
        header_value = cookies[key].output(header='').lstrip()
        self.response.headers._headers.append(('Set-Cookie', header_value))
    
    def delete_cookie(self, key, path='/', domain=None):
        """
        Delete a cookie from the client.  Note that path and domain must match
        how the cookie was originally set.
        This sets the cookie to the empty string, and max_age=0 so
        that it should expire immediately.
        """
        self.set_cookie(key, '', path=path, domain=domain, max_age=0)
    
    def unset_cookie(self, key):
        """
        Unset a cookie with the given name (remove it from the
        response).  If there are multiple cookies (e.g., two cookies
        with the same name and different paths or domains), all such
        cookies will be deleted.
        """
        existing = self.response.headers.get_all('Set-Cookie')
        if not existing:
            raise KeyError("No cookies at all have been set")
        del self.response.headers['Set-Cookie']
        found = False
        for header in existing:
            cookies = BaseCookie()
            cookies.load(header)
            if key in cookies:
                found = True
                del cookies[key]
            header = cookies.output(header='').lstrip()
            if header:
                self.response.headers.add('Set-Cookie', header)
        if not found:
            raise KeyError("No cookie has been set with the name %r" % key)

class BaseController(CookieController):
    SESSION_MEMCACHE_TIMEOUT = 0
    CACHE_TIMEOUT = 7200
    
    def serve_static_file(self, base_path, path, more = None, more_placeholder = None, filter=None):
        file_path = os.path.join(base_path, path)
        try:
            logging.debug('Serving static file %s', file_path)
            data = universal_read(file_path)
            if filter: data = filter(data, base_path, path)
            mime_type, encoding = mimetypes.guess_type(path)
            self.response.headers['Content-Type'] = mime_type
            self.set_caching_headers(self.CACHE_TIMEOUT)
            if more and more_placeholder:
                data = data.replace(more_placeholder, more)
            self.response.out.write(data)
            if more and not more_placeholder:
                self.response.out.write(more)
        except IOError:
            return self.error(404, '404 File %s Not Found' % path)
    
    def set_caching_headers(self, max_age, public = True):
        self.response.headers['Expires'] = email.Utils.formatdate(time.time() + max_age, usegmt=True)
        cache_control = []
        if public: cache_control.append('public')
        cache_control.append('max-age=%d' % max_age)
        self.response.headers['Cache-Control'] = ', '.join(cache_control)

    def render_json_response(self, data):
        json = json_encode(data, nice=LOCAL)

        is_test = self.params.get('test')
        if is_test:
            # this branch is here for testing purposes
            return self.render_html("<html><body><pre>%s</pre></body></html>" % json)

        callback = self.params.get('callback')
        if callback:
            # JSONP style
            self.render_text("__callback__(%s);" % json)
        else:
            # classic style
            self.render_json(json)

    def format_json_response(self, message, code=1):
        return {
            "status": code,
            "message": message,
        }
        
    def json_error(self, message, code=1):
        self.render_json_response(self.format_json_response(message, code))
        
    def json_ok(self, message = "OK"):
        self.render_json_response(self.format_json_response(message, 0))

class SessionController(BaseController):
    SESSION_KEY = 'session'
    SESSION_COOKIE_TIMEOUT_IN_SECONDS = 60*60*24*14
    session = None
    
    def _session_memcache_id(self, session_id):
        return "session-"+session_id
    
    def create_session(self, user_id):
        self.session = Session(user_id=user_id)
        self.session.save()
        logging.debug("Created session: %s", self.session.get_id())
    
    def load_session(self):
        if self.session: return self.session
        
        logging.debug("Loading session ...")
        # look for session id in request and cookies
        session_id = self.request.get(self.SESSION_KEY)
        if not session_id: session_id = self.cookies.get(self.SESSION_KEY)
        if not session_id:
            logging.debug("session_id not found in %s", self.cookies)
            return None
        
        # hit memcache first
        cache_id = self._session_memcache_id(session_id)
        self.session = memcache.get(cache_id)
        if self.session:
            logging.debug("Session found in memcache %s", self.session)
            return self.session
        
        # hit database if not in memcache
        self.session = Session.get(session_id)
        if self.session:
            logging.debug("Session loaded from store %s", self.session)
            memcache.set(cache_id, self.session, self.SESSION_MEMCACHE_TIMEOUT)
            return self.session
        
        # session not found
        return None
    
    def store_session(self):
        assert self.session
        cache_id = self._session_memcache_id(self.session.get_id())
        logging.debug("Storing session (%s) into memcache as %s" % (self.session, cache_id))
        self.set_cookie(self.SESSION_KEY,
            str(self.session.key()),
            max_age=self.SESSION_COOKIE_TIMEOUT_IN_SECONDS
        )
        memcache.set(cache_id, self.session, self.SESSION_MEMCACHE_TIMEOUT)
        self.session.save()
    
    def clear_session_cookie(self):
        logging.debug("Clearing session cookie (%s)" % self.SESSION_KEY)
        self.delete_cookie(self.SESSION_KEY)
    
    def clear_session(self):
        if not self.session:
            if not self.load_session(): return
        logging.debug("Clearing session %s", self.session)
        cache_id = self._session_memcache_id(self.session.get_id())
        memcache.delete(cache_id)
        self.session.delete()

class AuthenticatedController(SessionController):
    
    def __init__(self, *arguments, **keywords):
        super(AuthenticatedController, self).__init__(*arguments, **keywords)
        self.user = None
        
    def authenticate_user(self, url=None):
        self.user = users.get_current_user()
        if not self.user:
            return self.redirect_to(users.create_login_url(url or self.request.url))
        logging.info('Authenticated as user %s', self.user)
    
    def before_action(self, *arguments, **keywords):
        if super(AuthenticatedController, self).before_action(*arguments, **keywords): return True
        return self.authenticate_user()
########NEW FILE########
__FILENAME__ = events
import logging
import os
from drydrop.app.models import Event
from google.appengine.api import users

def log_event(action, code = 0, email = None, info = None):
    if email is None:
        user = users.get_current_user()
        if user is None:
            email = None
        else:
            email = user.email()
    domain = os.environ['SERVER_NAME']
    
    event = Event(author=email, action = action, code = code, info = info, domain=domain)
    event.save()

########NEW FILE########
__FILENAME__ = model
# -*- mode: python; coding: utf-8 -*-
import re
import simplejson
import string
from drydrop.lib.utils import *
from drydrop.lib.properties import *
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from drydrop.lib.json import json_encode

class Model(object): 
    
    def __str__(self):
        return self.__unicode__()
        
    def __unicode__(self):
        a = []
        for k, v in self.__dict__.iteritems():
            a.append("%s=%s" % (k, v))
        return "[%s]" % string.join(a, ', ')
            

    def get_id(self):
        return str(self.key())
        
    @classmethod
    def create(cls, *arguments, **keywords):
        instance = cls(*arguments, **keywords)
        instance.put()
        return instance

    @classmethod
    def find(cls, **params):
        query = cls.all()
        for name in params:
            query = query.filter("%s =" % name, params[name])
        return query.get()

    @classmethod
    def clear(cls, verbose=False, count=100000000, **params):
        if verbose: logging.info("clearing %s", cls.model)
        deleted = 0
        while count>0:
            c = 100
            if count<=100: c = count
            query = cls.all()

            for name in params:
              query = query.filter("%s =" % name, params[name])
            records = query.fetch(c)

            if len(records)==0: break
            deleted += len(records)
            db.delete(records)
            count -= c
        return deleted

########NEW FILE########
__FILENAME__ = vfs
# -*- mode: python; coding: utf-8 -*-
import os
import re
import os.path
import logging
import datetime
from drydrop.lib.utils import open_if_exists
from drydrop.app.models import Resource
from google.appengine.api import urlfetch
from google.appengine.ext import db
from drydrop.app.core.events import log_event

class VFS(object):
    """Virtual File System == filesystem abstraction for DryDrop"""
    def __init__(self):
        super(VFS, self).__init__()

    def fetch_resource_content(self, path):
        logging.warning('fetch_resource not implemented for %s', self.__class__.__name__)
        return None

    def fetch_file_timestamp(self, path):
        return None

    def get_resource(self, path):
        domain = os.environ['SERVER_NAME']
        resource = Resource.find(path=path, generation=self.settings.version, domain=domain)
        if resource is None:
            content = self.fetch_resource_content(path)
            created_on = self.fetch_file_timestamp(path)
            resource = Resource(path=path, content=content, generation=self.settings.version)
            if created_on is not None:
                resource.created_on = created_on
            try:
                length = len(resource.content)
            except:
                length = 0
            if length>0:
                log_event("Caching resource <code>%s</code> (%d bytes)" % (path, length))
            logging.debug("VFS: caching resource %s (%d bytes) for %s", path, length, domain)
            resource.domain = domain
            if content!=None:
              resource.save()
        try:
            length = len(resource.content)
        except:
            length = 0
        logging.debug("VFS: serving resource %s (%d bytes) for %s", path, length, domain)
        return resource

    def flush_resources(self, count = 1000):
        domain = os.environ['SERVER_NAME']
        deleted = Resource.clear(False, count, domain=domain)
        finished = deleted<count
        return finished, deleted

    def flush_resource(self, path):
        # purge all generations
        resources = Resource.all().filter("path =", path).filter("domain =", os.environ['SERVER_NAME']).fetch(1000)
        db.delete(resources)

    def get_all_resources(self):
        return Resource.all().filter("generation =", self.settings.version).filter("domain =", os.environ['SERVER_NAME']).fetch(1000)

class LocalVFS(VFS):
    """VFS for local development"""

    def __init__(self, settings):
        super(LocalVFS, self).__init__()
        self.settings = settings

    def get_resource(self, path):
        # check if file is fresh in cache
        resource = Resource.find(path=path, domain=os.environ['SERVER_NAME'])
        if resource is not None:
            stamp = self.fetch_file_timestamp(path)
            if stamp is not None and resource.created_on != stamp:
                logging.debug("VFS: file %s has been modified since last time => purged from cache", path)
                resource.delete()
        return super(LocalVFS, self).get_resource(path)

    def fetch_file_timestamp(self, path):
        root = self.settings.source
        if not root:
            return None
        filepath = os.path.join(root, path)
        try:
            s = os.stat(filepath)
        except:
            return None
        return datetime.datetime.fromtimestamp(s.st_mtime)

    def fetch_resource_content(self, path):
        root = self.settings.source
        if not root:
            return None
        filepath = os.path.join(root, path)
        f = open_if_exists(filepath)
        if f is None:
            return None
        try:
            contents = f.read()
        finally:
            f.close()
        return contents

class GAEVFS(VFS):
    """VFS for production"""

    def __init__(self, settings):
        super(GAEVFS, self).__init__()
        self.settings = settings

    def fetch_resource_content(self, path):
        root = self.settings.source
        if not root:
            return None
        if not root.endswith('/'): root = root + "/"
        url = root + path
        params = []
        if self.settings.github_login:
            params.append("login=%s" % self.settings.github_login)
        if self.settings.github_token:
            params.append("token=%s" % self.settings.github_token)

        # note: params should be url-safe, so no need to escape here
        if len(params)>0:
            url = url + "?" + "&".join(params)

        response = urlfetch.fetch(url, follow_redirects=True)
        if response.status_code!=200:
            return None
        # HACK: if we get 200 with section referring to status404 treat it as 404, this is bug on github side
        #       see http://github.com/darwin/drydrop/issues/#issue/2 for more info
        if re.search(r'id="error" class="status404"', response.content):
            logging.warning("got bogus 404 response for %s", url)
            return None

        return response.content

########NEW FILE########
__FILENAME__ = buster
# -*- mode: python; coding: utf-8 -*-
import os
import os.path
import re
import string
import time
import urlparse
import logging
from drydrop_handler import DRY_ROOT

def cache_buster(html):
    def url_replacer(match):
        def get_stamp(files):
            stamp = ""
            for file in files:
                try:
                    s = os.stat(file)
                    stamp += time.strftime("%H%M%S", time.localtime(s.st_mtime))
                except:
                    # TODO: log this situation? missing main.html is a valid case
                    pass
            return stamp
        
        def adhoc_remapper(path):
            return path.replace('drydrop-static', 'static').replace('.zip', '')
        
        # break url into parts
        url = match.groups(1)[1]
        parts = urlparse.urlparse(url)
        original = match.groups(1)[0]
        
        # do not touch absolute urls
        is_absolute = parts[1]!=''
        if is_absolute:
            return original
        
        path = os.path.join(DRY_ROOT, parts[2].lstrip('/'))
        
        path = adhoc_remapper(path)
        
        dir = os.path.dirname(path)
        files = [path]
        base = os.path.basename(path)
        stamp = get_stamp(files)
        if not stamp:
            return original
        
        if parts[3]=='':
            part3 = stamp
        else:
            part3 = parts[3] + "&" + stamp
            
        new_url = parts[2]+"?"+part3
        result = string.replace(original, url, new_url)
        return result
        
    html = re.sub(r'(src="([^"]*)")', url_replacer, html)
    html = re.sub(r'(src=\'([^\']*)\')', url_replacer, html)
    html = re.sub(r'(href="([^#][^"]*)")', url_replacer, html)
    html = re.sub(r'(href=\'([^#][^\']*)\')', url_replacer, html)
    return html

########NEW FILE########
__FILENAME__ = cacher
# -*- mode: python; coding: utf-8 -*-
from lib.utils import *
from google.appengine.api import memcache

def url_cache(fn, timeout=0):
    def wrapper(self, *arguments, **keywords):
        d = self.params.mixed() # shallow copy
        callback = d['callback']
        del d['callback']
        del d['_']
        hashkey = str(hash_dict(d))
        if not d.has_key('nocache'):
            cached_response = memcache.get(hashkey)
            if cached_response:
                self.handler.response = cached_response
                val = self.handler.response.out.getvalue()
                self.handler.response.clear()
                self.handler.response.out.write(val.replace("__callback__", callback))
                return
        res = fn(self, *arguments, **keywords)
        memcache.set(hashkey, self.handler.response, timeout)
        val = self.handler.response.out.getvalue()
        self.handler.response.clear()
        self.handler.response.out.write(val.replace("__callback__", callback))
        return res
    
    return wrapper
########NEW FILE########
__FILENAME__ = appinfo
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""AppInfo tools

Library for working with AppInfo records in memory, store and load from
configuration files.
"""





import re

from drydrop.app.meta import appinfo_errors
from drydrop.app.meta import validation
from drydrop.app.meta import yaml_listener
from drydrop.app.meta import yaml_builder
from drydrop.app.meta import yaml_object


_URL_REGEX = r'(?!\^)/|\.|(\(.).*(?!\$).'
_FILES_REGEX = r'(?!\^).*(?!\$).'

_DELTA_REGEX = r'([1-9][0-9]*)([DdHhMm]|[sS]?)'
_EXPIRATION_REGEX = r'\s*(%s)(\s+%s)*\s*' % (_DELTA_REGEX, _DELTA_REGEX)

_EXPIRATION_CONVERSIONS = {
  'd': 60 * 60 * 24,
  'h': 60 * 60,
  'm': 60,
  's': 1,
}

APP_ID_MAX_LEN = 100
MAJOR_VERSION_ID_MAX_LEN = 100
MAX_URL_MAPS = 100

APPLICATION_RE_STRING = r'(?!-)[a-z\d\-]{1,%d}' % APP_ID_MAX_LEN
VERSION_RE_STRING = r'(?!-)[a-z\d\-]{1,%d}' % MAJOR_VERSION_ID_MAX_LEN

HANDLER_STATIC_FILES = 'static_files'
HANDLER_STATIC_DIR = 'static_dir'
HANDLER_SCRIPT = 'script'

LOGIN_OPTIONAL = 'optional'
LOGIN_REQUIRED = 'required'
LOGIN_ADMIN = 'admin'

SECURE_HTTP = 'never'
SECURE_HTTPS = 'always'
SECURE_HTTP_OR_HTTPS = 'optional'

RUNTIME_PYTHON = 'python'

DEFAULT_SKIP_FILES = (r"^(.*/)?("
                      r"(app\.yaml)|"
                      r"(app\.yml)|"
                      r"(index\.yaml)|"
                      r"(index\.yml)|"
                      r"(#.*#)|"
                      r"(.*~)|"
                      r"(.*\.py[co])|"
                      r"(.*/RCS/.*)|"
                      r"(\..*)|"
                      r")$")

LOGIN = 'login'
SECURE = 'secure'
URL = 'url'
STATIC_FILES = 'static_files'
UPLOAD = 'upload'
STATIC_DIR = 'static_dir'
MIME_TYPE = 'mime_type'
SCRIPT = 'script'
EXPIRATION = 'expiration'

APPLICATION = 'application'
VERSION = 'version'
RUNTIME = 'runtime'
API_VERSION = 'api_version'
HANDLERS = 'handlers'
DEFAULT_EXPIRATION = 'default_expiration'
SKIP_FILES = 'skip_files'


class URLMap(validation.Validated):
  """Mapping from URLs to handlers.

  This class acts like something of a union type.  Its purpose is to
  describe a mapping between a set of URLs and their handlers.  What
  handler type a given instance has is determined by which handler-id
  attribute is used.

  Each mapping can have one and only one handler type.  Attempting to
  use more than one handler-id attribute will cause an UnknownHandlerType
  to be raised during validation.  Failure to provide any handler-id
  attributes will cause MissingHandlerType to be raised during validation.

  The regular expression used by the url field will be used to match against
  the entire URL path and query string of the request.  This means that
  partial maps will not be matched.  Specifying a url, say /admin, is the
  same as matching against the regular expression '^/admin$'.  Don't begin
  your matching url with ^ or end them with $.  These regular expressions
  won't be accepted and will raise ValueError.

  Attributes:
    login: Whether or not login is required to access URL.  Defaults to
      'optional'.
    secure: Restriction on the protocol which can be used to serve
            this URL/handler (HTTP, HTTPS or either).
    url: Regular expression used to fully match against the request URLs path.
      See Special Cases for using static_dir.
    static_files: Handler id attribute that maps URL to the appropriate
      file.  Can use back regex references to the string matched to url.
    upload: Regular expression used by the application configuration
      program to know which files are uploaded as blobs.  It's very
      difficult to determine this using just the url and static_files
      so this attribute must be included.  Required when defining a
      static_files mapping.
      A matching file name must fully match against the upload regex, similar
      to how url is matched against the request path.  Do not begin upload
      with ^ or end it with $.
    static_dir: Handler id that maps the provided url to a sub-directory
      within the application directory.  See Special Cases.
    mime_type: When used with static_files and static_dir the mime-type
      of files served from those directories are overridden with this
      value.
    script: Handler id that maps URLs to scipt handler within the application
      directory that will run using CGI.
    expiration: When used with static files and directories, the time delta to
      use for cache expiration. Has the form '4d 5h 30m 15s', where each letter
      signifies days, hours, minutes, and seconds, respectively. The 's' for
      seconds may be omitted. Only one amount must be specified, combining
      multiple amounts is optional. Example good values: '10', '1d 6h',
      '1h 30m', '7d 7d 7d', '5m 30'.

  Special cases:
    When defining a static_dir handler, do not use a regular expression
    in the url attribute.  Both the url and static_dir attributes are
    automatically mapped to these equivalents:

      <url>/(.*)
      <static_dir>/\1

    For example:

      url: /images
      static_dir: images_folder

    Is the same as this static_files declaration:

      url: /images/(.*)
      static_files: images/\1
      upload: images/(.*)
  """

  ATTRIBUTES = {

    URL: validation.Optional(_URL_REGEX),
    LOGIN: validation.Options(LOGIN_OPTIONAL,
                              LOGIN_REQUIRED,
                              LOGIN_ADMIN,
                              default=LOGIN_OPTIONAL),

    SECURE: validation.Options(SECURE_HTTP,
                               SECURE_HTTPS,
                               SECURE_HTTP_OR_HTTPS,
                               default=SECURE_HTTP),



    HANDLER_STATIC_FILES: validation.Optional(_FILES_REGEX),
    UPLOAD: validation.Optional(_FILES_REGEX),


    HANDLER_STATIC_DIR: validation.Optional(_FILES_REGEX),


    MIME_TYPE: validation.Optional(str),
    EXPIRATION: validation.Optional(_EXPIRATION_REGEX),


    HANDLER_SCRIPT: validation.Optional(_FILES_REGEX),
  }

  COMMON_FIELDS = set([URL, LOGIN, SECURE])

  ALLOWED_FIELDS = {
    HANDLER_STATIC_FILES: (MIME_TYPE, UPLOAD, EXPIRATION),
    HANDLER_STATIC_DIR: (MIME_TYPE, EXPIRATION),
    HANDLER_SCRIPT: (),
  }

  def GetHandler(self):
    """Get handler for mapping.

    Returns:
      Value of the handler (determined by handler id attribute).
    """
    return getattr(self, self.GetHandlerType())

  def GetHandlerType(self):
    """Get handler type of mapping.

    Returns:
      Handler type determined by which handler id attribute is set.

    Raises:
      UnknownHandlerType when none of the no handler id attributes
      are set.

      UnexpectedHandlerAttribute when an unexpected attribute
      is set for the discovered handler type.

      HandlerTypeMissingAttribute when the handler is missing a
      required attribute for its handler type.
    """
    for id_field in URLMap.ALLOWED_FIELDS.iterkeys():
      if getattr(self, id_field) is not None:
        mapping_type = id_field
        break
    else:
      raise appinfo_errors.UnknownHandlerType(
          'Unknown url handler type.\n%s' % str(self))

    allowed_fields = URLMap.ALLOWED_FIELDS[mapping_type]

    for attribute in self.ATTRIBUTES.iterkeys():
      if (getattr(self, attribute) is not None and
          not (attribute in allowed_fields or
               attribute in URLMap.COMMON_FIELDS or
               attribute == mapping_type)):
            raise appinfo_errors.UnexpectedHandlerAttribute(
                'Unexpected attribute "%s" for mapping type %s.' %
                (attribute, mapping_type))

    if mapping_type == HANDLER_STATIC_FILES and not self.upload:
      raise appinfo_errors.MissingHandlerAttribute(
          'Missing "%s" attribute for URL "%s".' % (UPLOAD, self.url))

    return mapping_type

  def CheckInitialized(self):
    """Adds additional checking to make sure handler has correct fields.

    In addition to normal ValidatedCheck calls GetHandlerType
    which validates all the handler fields are configured
    properly.

    Raises:
      UnknownHandlerType when none of the no handler id attributes
      are set.

      UnexpectedHandlerAttribute when an unexpected attribute
      is set for the discovered handler type.

      HandlerTypeMissingAttribute when the handler is missing a
      required attribute for its handler type.
    """
    super(URLMap, self).CheckInitialized()
    self.GetHandlerType()


class AppInfoExternal(validation.Validated):
  """Class representing users application info.

  This class is passed to a yaml_object builder to provide the validation
  for the application information file format parser.

  Attributes:
    application: Unique identifier for application.
    version: Application's major version number.
    runtime: Runtime used by application.
    api_version: Which version of APIs to use.
    handlers: List of URL handlers.
    default_expiration: Default time delta to use for cache expiration for
      all static files, unless they have their own specific 'expiration' set.
      See the URLMap.expiration field's documentation for more information.
    skip_files: An re object.  Files that match this regular expression will
      not be uploaded by appcfg.py.  For example:
        skip_files: |
          .svn.*|
          #.*#
  """

  ATTRIBUTES = {


    # APPLICATION: APPLICATION_RE_STRING,
    # VERSION: VERSION_RE_STRING,
    # RUNTIME: validation.Options(RUNTIME_PYTHON),
    # 
    # 
    # API_VERSION: validation.Options('1', 'beta'),
    HANDLERS: validation.Optional(validation.Repeated(URLMap)),
    DEFAULT_EXPIRATION: validation.Optional(_EXPIRATION_REGEX),
    SKIP_FILES: validation.RegexStr(default=DEFAULT_SKIP_FILES)
  }

  def CheckInitialized(self):
    """Ensures that at least one url mapping is provided.

    Raises:
      MissingURLMapping when no URLMap objects are present in object.
      TooManyURLMappings when there are too many URLMap entries.
    """
    super(AppInfoExternal, self).CheckInitialized()
    if not self.handlers:
      raise appinfo_errors.MissingURLMapping(
          'No URLMap entries found in application configuration')
    if len(self.handlers) > MAX_URL_MAPS:
      raise appinfo_errors.TooManyURLMappings(
          'Found more than %d URLMap entries in application configuration' %
          MAX_URL_MAPS)


def LoadSingleAppInfo(app_info):
  """Load a single AppInfo object where one and only one is expected.

  Args:
    app_info: A file-like object or string.  If it is a string, parse it as
    a configuration file.  If it is a file-like object, read in data and
    parse.

  Returns:
    An instance of AppInfoExternal as loaded from a YAML file.

  Raises:
    EmptyConfigurationFile when there are no documents in YAML file.
    MultipleConfigurationFile when there is more than one document in YAML
    file.
  """
  builder = yaml_object.ObjectBuilder(AppInfoExternal)
  handler = yaml_builder.BuilderHandler(builder)
  listener = yaml_listener.EventListener(handler)
  listener.Parse(app_info)

  app_infos = handler.GetResults()
  if len(app_infos) < 1:
    raise appinfo_errors.EmptyConfigurationFile()
  if len(app_infos) > 1:
    raise appinfo_errors.MultipleConfigurationFile()
  return app_infos[0]


def ParseExpiration(expiration):
  """Parses an expiration delta string.

  Args:
    expiration: String that matches _DELTA_REGEX.

  Returns:
    Time delta in seconds.
  """
  delta = 0
  for match in re.finditer(_DELTA_REGEX, expiration):
    amount = int(match.group(1))
    units = _EXPIRATION_CONVERSIONS.get(match.group(2).lower(), 1)
    delta += amount * units
  return delta



_file_path_positive_re = re.compile(r'^[ 0-9a-zA-Z\._\+/\$-]{1,256}$')

_file_path_negative_1_re = re.compile(r'\.\.|^\./|\.$|/\./|^-')

_file_path_negative_2_re = re.compile(r'//|/$')

_file_path_negative_3_re = re.compile(r'^ | $|/ | /')


def ValidFilename(filename):
  """Determines if filename is valid.

  filename must be a valid pathname.
  - It must contain only letters, numbers, _, +, /, $, ., and -.
  - It must be less than 256 chars.
  - It must not contain "/./", "/../", or "//".
  - It must not end in "/".
  - All spaces must be in the middle of a directory or file name.

  Args:
    filename: The filename to validate.

  Returns:
    An error string if the filename is invalid.  Returns '' if the filename
    is valid.
  """
  if _file_path_positive_re.match(filename) is None:
    return 'Invalid character in filename: %s' % filename
  if _file_path_negative_1_re.search(filename) is not None:
    return ('Filename cannot contain "." or ".." or start with "-": %s' %
            filename)
  if _file_path_negative_2_re.search(filename) is not None:
    return 'Filename cannot have trailing / or contain //: %s' % filename
  if _file_path_negative_3_re.search(filename) is not None:
    return 'Any spaces must be in the middle of a filename: %s' % filename
  return ''

########NEW FILE########
__FILENAME__ = appinfo_errors
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Errors used in the Python appinfo API, used by app developers."""





class Error(Exception):
  """Base datastore AppInfo type."""

class EmptyConfigurationFile(Error):
  """Tried to load empty configuration file"""

class MultipleConfigurationFile(Error):
  """Tried to load configuration file with multiple AppInfo objects"""

class UnknownHandlerType(Error):
  """Raised when it is not possible to determine URL mapping type."""

class UnexpectedHandlerAttribute(Error):
  """Raised when a handler type has an attribute that it does not use."""

class MissingHandlerAttribute(Error):
  """Raised when a handler is missing an attribute required by its type."""

class MissingURLMapping(Error):
  """Raised when there are no URL mappings in external appinfo."""

class TooManyURLMappings(Error):
  """Raised when there are too many URL mappings in external appinfo."""

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# taken from GAE SDK 1.1.7 modified by Antonin Hildebrand

"""Pure-Python application server for testing applications locally.

Given a port and the paths to a valid application directory (with an 'app.yaml'
file), the external library directory, and a relative URL to use for logins,
creates an HTTP server that can be used to test an application locally. Uses
stubs instead of actual APIs when SetupStubs() is called first.

Example:
  root_path = '/path/to/application/directory'
  login_url = '/login'
  port = 8080
  template_dir = '/path/to/appserver/templates'
  server = dev_appserver.CreateServer(root_path, login_url, port, template_dir)
  server.serve_forever()
"""


import cStringIO
import cgi
import email.Utils
import errno
import httplib
import imp
import inspect
import itertools
import locale
import logging
import mimetools
import mimetypes
import os
import pickle
import pprint
import random

import re
import sre_compile
import sre_constants
import sre_parse

import mimetypes
import socket
import sys
import time
import traceback
import types
import urlparse
import urllib

import google
from google.pyglib import gexcept

from drydrop.app.meta import appinfo
from drydrop.app.meta import yaml_errors
from google.appengine.api import users
from drydrop_handler import ReadDataFile

FILE_MISSING_EXCEPTIONS = frozenset([errno.ENOENT, errno.ENOTDIR])

MAX_URL_LENGTH = 2047

for ext, mime_type in (('.asc', 'text/plain'),
                       ('.diff', 'text/plain'),
                       ('.csv', 'text/comma-separated-values'),
                       ('.rss', 'application/rss+xml'),
                       ('.text', 'text/plain'),
                       ('.wbmp', 'image/vnd.wap.wbmp')):
  mimetypes.add_type(mime_type, ext)

class Error(Exception):
  """Base-class for exceptions in this module."""

class InvalidAppConfigError(Error):
  """The supplied application configuration file is invalid."""

class AppConfigNotFoundError(Error):
  """Application configuration file not found."""

class TemplatesNotLoadedError(Error):
  """Templates for the debugging console were not loaded."""


def SplitURL(relative_url):
  """Splits a relative URL into its path and query-string components.

  Args:
    relative_url: String containing the relative URL (often starting with '/')
      to split. Should be properly escaped as www-form-urlencoded data.

  Returns:
    Tuple (script_name, query_string) where:
      script_name: Relative URL of the script that was accessed.
      query_string: String containing everything after the '?' character.
  """
  scheme, netloc, path, query, fragment = urlparse.urlsplit(relative_url)
  return path, query


class URLDispatcher(object):
  """Base-class for handling HTTP requests."""

  def Dispatch(self,
               relative_url,
               path,
               headers,
               infile,
               outfile,
               base_env_dict=None):
    """Dispatch and handle an HTTP request.

    base_env_dict should contain at least these CGI variables:
      REQUEST_METHOD, REMOTE_ADDR, SERVER_SOFTWARE, SERVER_NAME,
      SERVER_PROTOCOL, SERVER_PORT

    Args:
      relative_url: String containing the URL accessed.
      path: Local path of the resource that was matched; back-references will be
        replaced by values matched in the relative_url. Path may be relative
        or absolute, depending on the resource being served (e.g., static files
        will have an absolute path; scripts will be relative).
      headers: Instance of mimetools.Message with headers from the request.
      infile: File-like object with input data from the request.
      outfile: File-like object where output data should be written.
      base_env_dict: Dictionary of CGI environment parameters if available.
        Defaults to None.
    """
    raise NotImplementedError


class URLMatcher(object):
  """Matches an arbitrary URL using a list of URL patterns from an application.

  Each URL pattern has an associated URLDispatcher instance and path to the
  resource's location on disk. See AddURL for more details. The first pattern
  that matches an inputted URL will have its associated values returned by
  Match().
  """

  def __init__(self):
    """Initializer."""
    self._url_patterns = []

  def AddURL(self, regex, dispatcher, path, requires_login, admin_only):
    """Adds a URL pattern to the list of patterns.

    If the supplied regex starts with a '^' or ends with a '$' an
    InvalidAppConfigError exception will be raised. Start and end symbols
    and implicitly added to all regexes, meaning we assume that all regexes
    consume all input from a URL.

    Args:
      regex: String containing the regular expression pattern.
      dispatcher: Instance of URLDispatcher that should handle requests that
        match this regex.
      path: Path on disk for the resource. May contain back-references like
        r'\1', r'\2', etc, which will be replaced by the corresponding groups
        matched by the regex if present.
      requires_login: True if the user must be logged-in before accessing this
        URL; False if anyone can access this URL.
      admin_only: True if the user must be a logged-in administrator to
        access the URL; False if anyone can access the URL.
    """
    if not isinstance(dispatcher, URLDispatcher):
      raise TypeError, 'dispatcher must be a URLDispatcher sub-class'

    if regex.startswith('^') or regex.endswith('$'):
      raise InvalidAppConfigError, 'regex starts with "^" or ends with "$"'

    adjusted_regex = '^%s$' % regex

    try:
      url_re = re.compile(adjusted_regex)
    except re.error, e:
      raise InvalidAppConfigError, 'regex invalid: %s' % e

    match_tuple = (url_re, dispatcher, path, requires_login, admin_only)
    self._url_patterns.append(match_tuple)

  def Match(self,
            relative_url,
            split_url=SplitURL):
    """Matches a URL from a request against the list of URL patterns.

    The supplied relative_url may include the query string (i.e., the '?'
    character and everything following).

    Args:
      relative_url: Relative URL being accessed in a request.

    Returns:
      Tuple (dispatcher, matched_path, requires_login, admin_only), which are
      the corresponding values passed to AddURL when the matching URL pattern
      was added to this matcher. The matched_path will have back-references
      replaced using values matched by the URL pattern. If no match was found,
      dispatcher will be None.
    """
    adjusted_url, query_string = split_url(relative_url)

    for url_tuple in self._url_patterns:
      url_re, dispatcher, path, requires_login, admin_only = url_tuple
      logging.debug("URL match: %s %s", url_re.pattern, adjusted_url)
      the_match = url_re.match(adjusted_url)

      if the_match:
        adjusted_path = the_match.expand(path)
        return dispatcher, adjusted_path, requires_login, admin_only

    return None, None, None, None

  def GetDispatchers(self):
    """Retrieves the URLDispatcher objects that could be matched.

    Should only be used in tests.

    Returns:
      A set of URLDispatcher objects.
    """
    return set([url_tuple[1] for url_tuple in self._url_patterns])


def GetUserInfo():
    user = users.get_current_user()
    if not user:
        return (None, False)
    return (user.email(), users.is_current_user_admin())
    
def LoginRedirect(login_url,
                  hostname,
                  port,
                  relative_url,
                  outfile):
  # dest_url = "http://%s:%s%s" % (hostname, port, relative_url)
  # redirect_url = 'http://%s:%s%s?%s=%s' % (hostname,
  #                                          port,
  #                                          login_url,
  #                                          CONTINUE_PARAM,
  #                                          urllib.quote(dest_url))
  # outfile.write('Status: 302 Requires login\r\n')
  # outfile.write('Location: %s\r\n\r\n' % redirect_url)
  pass

class MatcherDispatcher(URLDispatcher):
  """Dispatcher across multiple URLMatcher instances."""

  def __init__(self,
               login_url,
               url_matchers,
               get_user_info=GetUserInfo,
               login_redirect=LoginRedirect):
    """Initializer.

    Args:
      login_url: Relative URL which should be used for handling user logins.
      url_matchers: Sequence of URLMatcher objects.
      get_user_info, login_redirect: Used for dependency injection.
    """
    self._login_url = login_url
    self._url_matchers = tuple(url_matchers)
    self._get_user_info = get_user_info
    self._login_redirect = login_redirect

  def Dispatch(self,
               relative_url,
               path,
               headers,
               infile,
               outfile,
               base_env_dict=None):
    """Dispatches a request to the first matching dispatcher.

    Matchers are checked in the order they were supplied to the constructor.
    If no matcher matches, a 404 error will be written to the outfile. The
    path variable supplied to this method is ignored.
    """
    email, admin = self._get_user_info()

    for matcher in self._url_matchers:
      dispatcher, matched_path, requires_login, admin_only = matcher.Match(relative_url)
      if dispatcher is None:
        continue

      logging.debug('Matched "%s" to %s with path %s',
                    relative_url, dispatcher, matched_path)

      if (requires_login or admin_only) and not email:
        logging.debug('Login required, redirecting user')
        self._login_redirect(
          self._login_url,
          base_env_dict['SERVER_NAME'],
          base_env_dict['SERVER_PORT'],
          relative_url,
          outfile)
      elif admin_only and not admin:
        outfile.write('Status: %d Not authorized\r\n'
                      '\r\n'
                      'Current logged in user %s is not '
                      'authorized to view this page.'
                      % (httplib.FORBIDDEN, email))
      else:
        dispatcher.Dispatch(relative_url,
                            matched_path,
                            headers,
                            infile,
                            outfile,
                            base_env_dict=base_env_dict)

      return

    outfile.write('Status: %d URL did not match\r\n'
                  '\r\n'
                  'Not found error: %s did not match any patterns '
                  'in application configuration.'
                  % (httplib.NOT_FOUND, relative_url))

def ExecuteCGI(root_path,
               handler_path,
               cgi_path,
               env,
               infile,
               outfile,
               module_dict,
               exec_script):
  """Executes Python file in this process as if it were a CGI.

  Does not return an HTTP response line. CGIs should output headers followed by
  the body content.

  The modules in sys.modules should be the same before and after the CGI is
  executed, with the specific exception of encodings-related modules, which
  cannot be reloaded and thus must always stay in sys.modules.

  Args:
    root_path: Path to the root of the application.
    handler_path: CGI path stored in the application configuration (as a path
      like 'foo/bar/baz.py'). May contain $PYTHON_LIB references.
    cgi_path: Absolute path to the CGI script file on disk.
    env: Dictionary of environment variables to use for the execution.
    infile: File-like object to read HTTP request input data from.
    outfile: FIle-like object to write HTTP response data to.
    module_dict: Dictionary in which application-loaded modules should be
      preserved between requests. This removes the need to reload modules that
      are reused between requests, significantly increasing load performance.
      This dictionary must be separate from the sys.modules dictionary.
    exec_script: Used for dependency injection.
  """
  # old_module_dict = sys.modules.copy()
  # old_builtin = __builtin__.__dict__.copy()
  # old_argv = sys.argv
  # old_stdin = sys.stdin
  # old_stdout = sys.stdout
  # old_env = os.environ.copy()
  # old_cwd = os.getcwd()
  # old_file_type = types.FileType
  # reset_modules = False
  # 
  # try:
  #   ClearAllButEncodingsModules(sys.modules)
  #   sys.modules.update(module_dict)
  #   sys.argv = [cgi_path]
  #   sys.stdin = infile
  #   sys.stdout = outfile
  #   os.environ.clear()
  #   os.environ.update(env)
  #   before_path = sys.path[:]
  #   cgi_dir = os.path.normpath(os.path.dirname(cgi_path))
  #   root_path = os.path.normpath(os.path.abspath(root_path))
  #   if cgi_dir.startswith(root_path + os.sep):
  #     os.chdir(cgi_dir)
  #   else:
  #     os.chdir(root_path)
  # 
  #   hook = HardenedModulesHook(sys.modules)
  #   sys.meta_path = [hook]
  #   if hasattr(sys, 'path_importer_cache'):
  #     sys.path_importer_cache.clear()
  # 
  #   __builtin__.file = FakeFile
  #   __builtin__.open = FakeFile
  #   types.FileType = FakeFile
  # 
  #   __builtin__.buffer = NotImplementedFakeClass
  # 
  #   logging.debug('Executing CGI with env:\n%s', pprint.pformat(env))
  #   try:
  #     reset_modules = exec_script(handler_path, cgi_path, hook)
  #   except SystemExit, e:
  #     logging.debug('CGI exited with status: %s', e)
  #   except:
  #     reset_modules = True
  #     raise
  # 
  # finally:
  #   sys.meta_path = []
  #   sys.path_importer_cache.clear()
  # 
  #   _ClearTemplateCache(sys.modules)
  # 
  #   module_dict.update(sys.modules)
  #   ClearAllButEncodingsModules(sys.modules)
  #   sys.modules.update(old_module_dict)
  # 
  #   __builtin__.__dict__.update(old_builtin)
  #   sys.argv = old_argv
  #   sys.stdin = old_stdin
  #   sys.stdout = old_stdout
  # 
  #   sys.path[:] = before_path
  # 
  #   os.environ.clear()
  #   os.environ.update(old_env)
  #   os.chdir(old_cwd)
  # 
  #   types.FileType = old_file_type
  pass


def SetupEnvironment(cgi_path,
                       relative_url,
                       headers,
                       split_url=SplitURL,
                       get_user_info=GetUserInfo):
    """Sets up environment variables for a CGI.

    Args:
      cgi_path: Full file-system path to the CGI being executed.
      relative_url: Relative URL used to access the CGI.
      headers: Instance of mimetools.Message containing request headers.
      split_url, get_user_info: Used for dependency injection.

    Returns:
      Dictionary containing CGI environment variables.
    """
    # env = DEFAULT_ENV.copy()
    # 
    # script_name, query_string = split_url(relative_url)
    # 
    # env['SCRIPT_NAME'] = ''
    # env['QUERY_STRING'] = query_string
    # env['PATH_INFO'] = urllib.unquote(script_name)
    # env['PATH_TRANSLATED'] = cgi_path
    # env['CONTENT_TYPE'] = headers.getheader('content-type', 'application/x-www-form-urlencoded')
    # env['CONTENT_LENGTH'] = headers.getheader('content-length', '')
    # 
    # email, admin = get_user_info()
    # env['USER_EMAIL'] = email
    # if admin:
    #   env['USER_IS_ADMIN'] = '1'
    # 
    # for key in headers:
    #   if key in _IGNORE_HEADERS:
    #     continue
    #   adjusted_name = key.replace('-', '_').upper()
    #   env['HTTP_' + adjusted_name] = ', '.join(headers.getheaders(key))

    return {}

class CGIDispatcher(URLDispatcher):
  """Dispatcher that executes Python CGI scripts."""

  def __init__(self,
               module_dict,
               root_path,
               path_adjuster,
               setup_env=SetupEnvironment,
               exec_cgi=ExecuteCGI):
    """Initializer.

    Args:
      module_dict: Dictionary in which application-loaded modules should be
        preserved between requests. This dictionary must be separate from the
        sys.modules dictionary.
      path_adjuster: Instance of PathAdjuster to use for finding absolute
        paths of CGI files on disk.
      setup_env, exec_cgi, create_logging_handler: Used for dependency
        injection.
    """
    self._module_dict = module_dict
    self._root_path = root_path
    self._path_adjuster = path_adjuster
    self._setup_env = setup_env
    self._exec_cgi = exec_cgi

  def Dispatch(self,
               relative_url,
               path,
               headers,
               infile,
               outfile,
               base_env_dict=None):
      """Dispatches the Python CGI."""
      env = {}
      cgi_path = self._path_adjuster.AdjustPath(path)
      env.update(self._setup_env(cgi_path, relative_url, headers))
      self._exec_cgi(self._root_path,
                     path,
                     cgi_path,
                     env,
                     infile,
                     outfile,
                     self._module_dict,
                     None)

  def __str__(self):
    """Returns a string representation of this dispatcher."""
    return 'CGI dispatcher'


class PathAdjuster(object):
  """Adjusts application file paths to paths relative to the application or
  external library directories."""

  def __init__(self, root_path):
    """Initializer.

    Args:
      root_path: Path to the root of the application running on the server.
    """
    self._root_path = os.path.abspath(root_path)

  def AdjustPath(self, path):
    """Adjusts application file path to paths relative to the application or
    external library directories.

    Handler paths that start with $PYTHON_LIB will be converted to paths
    relative to the google directory.

    Args:
      path: File path that should be adjusted.

    Returns:
      The adjusted path.
    """
    if path.startswith('./'):
        path = path[2:]
    if path.startswith('/'):
        path = path[1:]
    return path


class StaticFileConfigMatcher(object):
  """Keeps track of file/directory specific application configuration.

  Specifically:
  - Computes mime type based on URLMap and file extension.
  - Decides on cache expiration time based on URLMap and default expiration.

  To determine the mime type, we first see if there is any mime-type property
  on each URLMap entry. If non is specified, we use the mimetypes module to
  guess the mime type from the file path extension, and use
  application/octet-stream if we can't find the mimetype.
  """

  def __init__(self,
               url_map_list,
               path_adjuster,
               default_expiration):
    """Initializer.

    Args:
      url_map_list: List of appinfo.URLMap objects.
        If empty or None, then we always use the mime type chosen by the
        mimetypes module.
      path_adjuster: PathAdjuster object used to adjust application file paths.
      default_expiration: String describing default expiration time for browser
        based caching of static files.  If set to None this disallows any
        browser caching of static content.
    """
    if default_expiration is not None:
      self._default_expiration = appinfo.ParseExpiration(default_expiration)
    else:
      self._default_expiration = None

    self._patterns = []

    if url_map_list:
      for entry in url_map_list:
        handler_type = entry.GetHandlerType()
        if handler_type not in (appinfo.STATIC_FILES, appinfo.STATIC_DIR):
          continue

        if handler_type == appinfo.STATIC_FILES:
          regex = entry.upload + '$'
        else:
          path = entry.static_dir
          if path[-1] == '/':
            path = path[:-1]
          regex = re.escape(path) + r'/(.*)'

        try:
          path_re = re.compile(regex)
        except re.error, e:
          raise InvalidAppConfigError('regex %s does not compile: %s' %
                                      (regex, e))

        if self._default_expiration is None:
          expiration = 0
        elif entry.expiration is None:
          expiration = self._default_expiration
        else:
          expiration = appinfo.ParseExpiration(entry.expiration)

        self._patterns.append((path_re, entry.mime_type, expiration))

  def GetMimeType(self, path):
    """Returns the mime type that we should use when serving the specified file.

    Args:
      path: String containing the file's path relative to the app.

    Returns:
      String containing the mime type to use. Will be 'application/octet-stream'
      if we have no idea what it should be.
    """
    for (path_re, mime_type, expiration) in self._patterns:
      if mime_type is not None:
        the_match = path_re.match(path)
        if the_match:
          return mime_type

    filename, extension = os.path.splitext(path)
    return mimetypes.types_map.get(extension, 'application/octet-stream')

  def GetExpiration(self, path):
    """Returns the cache expiration duration to be users for the given file.

    Args:
      path: String containing the file's path relative to the app.

    Returns:
      Integer number of seconds to be used for browser cache expiration time.
    """
    for (path_re, mime_type, expiration) in self._patterns:
      the_match = path_re.match(path)
      if the_match:
        return expiration

    return self._default_expiration or 0

class FileDispatcher(URLDispatcher):
  """Dispatcher that reads data files from disk."""

  def __init__(self,
               path_adjuster,
               static_file_config_matcher,
               vfs,
               read_data_file=ReadDataFile):
    """Initializer.

    Args:
      path_adjuster: Instance of PathAdjuster to use for finding absolute
        paths of data files on disk.
      static_file_config_matcher: StaticFileConfigMatcher object.
      read_data_file: Used for dependency injection.
    """
    self._path_adjuster = path_adjuster
    self._static_file_config_matcher = static_file_config_matcher
    self._read_data_file = read_data_file
    self._vfs = vfs

  def Dispatch(self,
               relative_url,
               path,
               headers,
               infile,
               outfile,
               base_env_dict=None):
    """Reads the file and returns the response status and data."""
    SPACE_MARKER = '--~!-real-space-marker-!~--'
    path = path.replace('\\ ', SPACE_MARKER)
    parts = path.split(' ')
    c = 0
    for part in parts:
        c = c + 1
        new_path = part.replace(SPACE_MARKER, ' ')
        full_path = self._path_adjuster.AdjustPath(new_path)
        status, data, created_on = self._read_data_file(full_path, self._vfs)
        if status==httplib.OK or c==len(parts):
            content_type = self._static_file_config_matcher.GetMimeType(new_path)
            expiration = self._static_file_config_matcher.GetExpiration(new_path)

            outfile.write('Status: %d\r\n' % status)
            outfile.write('Content-Type: %s\r\n' % content_type)
            
            # Send a Last-Modified header
            HTTP_date = created_on.strftime('%a, %d %b %Y %H:%M:%S GMT')
            outfile.write('Last-Modified: %s\r\n' % HTTP_date)
            
            if expiration:
              outfile.write('Expires: %s\r\n'
                            % email.Utils.formatdate(time.time() + expiration,
                                                     usegmt=True))
              outfile.write('Cache-Control: public, max-age=%i\r\n' % expiration)
            outfile.write('\r\n')
            outfile.write(data)
            return

  def __str__(self):
    """Returns a string representation of this dispatcher."""
    return 'File dispatcher'


def RewriteResponse(response_file):
  """Interprets server-side headers and adjusts the HTTP response accordingly.

  Handles the server-side 'status' header, which instructs the server to change
  the HTTP response code accordingly. Handles the 'location' header, which
  issues an HTTP 302 redirect to the client. Also corrects the 'content-length'
  header to reflect actual content length in case extra information has been
  appended to the response body.

  If the 'status' header supplied by the client is invalid, this method will
  set the response to a 500 with an error message as content.

  Args:
    response_file: File-like object containing the full HTTP response including
      the response code, all headers, and the request body.

  Returns:
    Tuple (status_code, status_message, header, body) where:
      status_code: Integer HTTP response status (e.g., 200, 302, 404, 500)
      status_message: String containing an informational message about the
        response code, possibly derived from the 'status' header, if supplied.
      header: String containing the HTTP headers of the response, without
        a trailing new-line (CRLF).
      body: String containing the body of the response.
  """
  headers = mimetools.Message(response_file)

  response_status = '%d OK' % httplib.OK
  # 
  location_value = headers.getheader('location')
  status_value = headers.getheader('status')
  if status_value:
    response_status = status_value
    del headers['status']
  elif location_value:
    response_status = '%d Redirecting' % httplib.FOUND
  # 
  # if not 'Cache-Control' in headers:
  #   headers['Cache-Control'] = 'no-cache'

  status_parts = response_status.split(' ', 1)
  status_code, status_message = (status_parts + [''])[:2]
  try:
    status_code = int(status_code)
  except ValueError:
    status_code = 500
    body = 'Error: Invalid "status" header value returned.'
  else:
    body = response_file.read()

  # headers['content-length'] = str(len(body))
  # 
  header_list = []
  for header in headers.headers:
    header = header.rstrip('\n')
    header = header.rstrip('\r')
    header_list.append(header)

  return status_code, status_message, header_list, body


def CreateURLMatcherFromMaps(root_path,
                             url_map_list,
                             module_dict,
                             default_expiration,
                             vfs,
                             create_url_matcher=URLMatcher,
                             create_cgi_dispatcher=CGIDispatcher,
                             create_file_dispatcher=FileDispatcher,
                             create_path_adjuster=PathAdjuster,
                             normpath=os.path.normpath):
  """Creates a URLMatcher instance from URLMap.

  Creates all of the correct URLDispatcher instances to handle the various
  content types in the application configuration.

  Args:
    root_path: Path to the root of the application running on the server.
    url_map_list: List of appinfo.URLMap objects to initialize this
      matcher with. Can be an empty list if you would like to add patterns
      manually.
    module_dict: Dictionary in which application-loaded modules should be
      preserved between requests. This dictionary must be separate from the
      sys.modules dictionary.
    default_expiration: String describing default expiration time for browser
      based caching of static files.  If set to None this disallows any
      browser caching of static content.
    create_url_matcher, create_cgi_dispatcher, create_file_dispatcher,
    create_path_adjuster: Used for dependency injection.

  Returns:
    Instance of URLMatcher with the supplied URLMap objects properly loaded.
  """
  url_matcher = create_url_matcher()
  path_adjuster = create_path_adjuster(root_path)
  cgi_dispatcher = create_cgi_dispatcher(module_dict, root_path, path_adjuster)
  file_dispatcher = create_file_dispatcher(path_adjuster,
      StaticFileConfigMatcher(url_map_list, path_adjuster, default_expiration), vfs)

  for url_map in url_map_list:
    admin_only = url_map.login == appinfo.LOGIN_ADMIN
    requires_login = url_map.login == appinfo.LOGIN_REQUIRED or admin_only

    handler_type = url_map.GetHandlerType()
    if handler_type == appinfo.HANDLER_SCRIPT:
      dispatcher = cgi_dispatcher
    elif handler_type in (appinfo.STATIC_FILES, appinfo.STATIC_DIR):
      dispatcher = file_dispatcher
    else:
      raise InvalidAppConfigError('Unknown handler type "%s"' % handler_type)

    regex = url_map.url
    path = url_map.GetHandler()
    if handler_type == appinfo.STATIC_DIR:
      if regex[-1] == r'/':
        regex = regex[:-1]
      if path[-1] == os.path.sep:
        path = path[:-1]
      regex = '/'.join((re.escape(regex), '(.*)'))
      if os.path.sep == '\\':
        backref = r'\\1'
      else:
        backref = r'\1'
      path = (normpath(path).replace('\\', '\\\\') +
              os.path.sep + backref)

    url_matcher.AddURL(regex,
                       dispatcher,
                       path,
                       requires_login, admin_only)

  return url_matcher


def ParseAppConfig(root_path,
                  config_source,
                  vfs,
                  static_caching=True,
                  create_matcher=CreateURLMatcherFromMaps):
    config = appinfo.LoadSingleAppInfo(config_source)

    if static_caching:
      if config.default_expiration:
        default_expiration = config.default_expiration
      else:
        default_expiration = '0'
    else:
      default_expiration = None

    matcher = create_matcher(root_path,
                             config.handlers,
                             {},
                             default_expiration,
                             vfs)

    return (config, matcher)

########NEW FILE########
__FILENAME__ = validation
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Validation tools for generic object structures.

This library is used for defining classes with constrained attributes.
Attributes are defined on the class which contains them using validators.
Although validators can be defined by any client of this library, a number
of standard validators are provided here.

Validators can be any callable that takes a single parameter which checks
the new value before it is assigned to the attribute.  Validators are
permitted to modify a received value so that it is appropriate for the
attribute definition.  For example, using int as a validator will cast
a correctly formatted string to a number, or raise an exception if it
can not.  This is not recommended, however.  the correct way to use a
validator that ensure the correct type is to use the Type validator.

This validation library is mainly intended for use with the YAML object
builder.  See yaml_object.py.
"""





import re

import yaml


class Error(Exception):
  """Base class for all package errors."""


class AttributeDefinitionError(Error):
  """An error occurred in the definition of class attributes."""


class ValidationError(Error):
  """Base class for raising exceptions during validation."""

  def __init__(self, message, cause=None):
    """Initialize exception."""
    if hasattr(cause, 'args') and cause.args:
      Error.__init__(self, message, *cause.args)
    else:
      Error.__init__(self, message)
    self.message = message
    self.cause = cause

  def __str__(self):
    return str(self.message)


class MissingAttribute(ValidationError):
  """Raised when a required attribute is missing from object."""


def AsValidator(validator):
  """Wrap various types as instances of a validator.

  Used to allow shorthand for common validator types.  It
  converts the following types to the following Validators.

    strings -> Regex
    type -> Type
    collection -> Options
    Validator -> Its self!

  Args:
    validator: Object to wrap in a validator.

  Returns:
    Validator instance that wraps the given value.

  Raises:
    AttributeDefinitionError if validator is not one of the above described
    types.
  """
  if isinstance(validator, (str, unicode)):
    return Regex(validator, type(validator))
  if isinstance(validator, type):
    return Type(validator)
  if isinstance(validator, (list, tuple, set)):
    return Options(*tuple(validator))
  if isinstance(validator, Validator):
    return validator
  else:
    raise AttributeDefinitionError('%s is not a valid validator' %
                                   str(validator))


class Validated(object):
  """Base class for other classes that require validation.

  A class which intends to use validated fields should sub-class itself from
  this class.  Each class should define an 'ATTRIBUTES' class variable which
  should be a map from attribute name to its validator.  For example:

    class Story(Validated):
      ATTRIBUTES = {'title': Type(str),
                    'authors': Repeated(Type(str)),
                    'isbn': Optional(Type(str)),
                    'pages': Type(int),
                    }

  Attributes that are not listed under ATTRIBUTES work like normal and are
  not validated upon assignment.
  """

  ATTRIBUTES = None

  def __init__(self, **attributes):
    """Constructor for Validated classes.

    This constructor can optionally assign values to the class via its
    keyword arguments.

    Raises:
      AttributeDefinitionError when class instance is missing ATTRIBUTE
      definition or when ATTRIBUTE is of the wrong type.
    """
    if not isinstance(self.ATTRIBUTES, dict):
      raise AttributeDefinitionError(
          'The class %s does not define an ATTRIBUTE variable.'
          % self.__class__)

    for key in self.ATTRIBUTES.keys():
      object.__setattr__(self, key, self.GetAttribute(key).default)

    self.Set(**attributes)

  @classmethod
  def GetAttribute(self, key):
    """Safely get the underlying attribute definition as a Validator.

    Args:
      key: Name of attribute to get.

    Returns:
      Validator associated with key or attribute value wrapped in a
      validator.
    """
    return AsValidator(self.ATTRIBUTES[key])

  def Set(self, **attributes):
    """Set multiple values on Validated instance.

    This method can only be used to assign validated methods.

    Args:
      attributes: Attributes to set on object.

    Raises:
      ValidationError when no validated attribute exists on class.
    """
    for key, value in attributes.iteritems():
      if key not in self.ATTRIBUTES:
        raise ValidationError('Class \'%s\' does not have attribute \'%s\''
                               % (self.__class__, key))
      setattr(self, key, value)

  def CheckInitialized(self):
    """Checks that all required fields are initialized.

    Since an instance of Validated starts off in an uninitialized state, it
    is sometimes necessary to check that it has been fully initialized.
    The main problem this solves is how to validate that an instance has
    all of its required fields set.  By default, Validator classes do not
    allow None, but all attributes are initialized to None when instantiated.

    Raises:
      Exception relevant to the kind of validation.  The type of the exception
      is determined by the validator.  Typically this will be ValueError or
      TypeError.
    """
    for key in self.ATTRIBUTES.iterkeys():
      try:
        self.GetAttribute(key)(getattr(self, key))
      except MissingAttribute, e:
        e.message = "Missing required value '%s'." % key
        raise e


  def __setattr__(self, key, value):
    """Set attribute.

    Setting a value on an object of this type will only work for attributes
    defined in ATTRIBUTES.  To make other assignments possible it is necessary
    to override this method in subclasses.

    It is important that assignment is restricted in this way because
    this validation is used as validation for parsing.  Absent this restriction
    it would be possible for method names to be overwritten.

    Args:
      key: Name of attribute to set.
      value: Attributes new value.

    Raises:
      ValidationError when trying to assign to a value that does not exist.
    """

    if key in self.ATTRIBUTES:
      value = self.GetAttribute(key)(value)
      object.__setattr__(self, key, value)
    else:
      raise ValidationError('Class \'%s\' does not have attribute \'%s\''
                            % (self.__class__, key))

  def __eq__(self, other):
    """Comparison operator."""
    if isinstance(other, type(self)):
      for attribute in self.ATTRIBUTES:
        if getattr(self, attribute) != getattr(other, attribute):
          return False
      return True
    else:
      return False

  def __str__(self):
    """Formatted view of validated object and nested values."""
    return repr(self)

  def __repr__(self):
    """Formatted view of validated object and nested values."""
    values = [(attr, getattr(self, attr)) for attr in self.ATTRIBUTES]
    dent = '    '
    value_list = []
    for attr, value in values:
      value_list.append('\n%s%s=%s' % (dent, attr, value))

    return "<%s %s\n%s>" % (self.__class__.__name__, ' '.join(value_list), dent)

  def __eq__(self, other):
    """Equality operator.

    Comparison is done by comparing all attribute values to those in the other
    instance.  Objects which are not of the same type are not equal.

    Args:
      other: Other object to compare against.

    Returns:
      True if validated objects are equal, else False.
    """
    if type(self) != type(other):
      return False
    for key in self.ATTRIBUTES.iterkeys():
      if getattr(self, key) != getattr(other, key):
        return False
    return True

  def __ne__(self, other):
    """Inequality operator."""
    return not self.__eq__(other)

  def __hash__(self):
    """Hash function for using Validated objects in sets and maps.

    Hash is done by hashing all keys and values and xor'ing them together.

    Returns:
      Hash of validated object.
    """
    result = 0
    for key in self.ATTRIBUTES.iterkeys():
      value = getattr(self, key)
      if isinstance(value, list):
        value = tuple(value)
      result = result ^ hash(key) ^ hash(value)
    return result

  @staticmethod
  def _ToValue(validator, value):
    """Convert any value to simplified collections and basic types.

    Args:
      validator: An instance of Validator that corresponds with 'value'.
        May also be 'str' or 'int' if those were used instead of a full
        Validator.
      value: Value to convert to simplified collections.

    Returns:
      The value as a dictionary if it is a Validated object.
      A list of items converted to simplified collections if value is a list
        or a tuple.
      Otherwise, just the value.
    """
    if isinstance(value, Validated):
      return value.ToDict()
    elif isinstance(value, (list, tuple)):
      return [Validated._ToValue(validator, item) for item in value]
    else:
      if isinstance(validator, Validator):
        return validator.ToValue(value)
      return value

  def ToDict(self):
    """Convert Validated object to a dictionary.

    Recursively traverses all of its elements and converts everything to
    simplified collections.

    Returns:
      A dict of all attributes defined in this classes ATTRIBUTES mapped
      to its value.  This structure is recursive in that Validated objects
      that are referenced by this object and in lists are also converted to
      dicts.
    """
    result = {}
    for name, validator in self.ATTRIBUTES.iteritems():
      value = getattr(self, name)
      if not(isinstance(validator, Validator) and value == validator.default):
        result[name] = Validated._ToValue(validator, value)
    return result

  def ToYAML(self):
    """Print validated object as simplified YAML.

    Returns:
      Object as a simplified YAML string compatible with parsing using the
      SafeLoader.
    """
    return yaml.dump(self.ToDict(),
                     default_flow_style=False,
                     Dumper=yaml.SafeDumper)



class Validator(object):
  """Validator base class.

  Though any callable can be used as a validator, this class encapsulates the
  case when a specific validator needs to hold a particular state or
  configuration.

  To implement Validator sub-class, override the validate method.

  This class is permitted to change the ultimate value that is set to the
  attribute if there is a reasonable way to perform the conversion.
  """

  expected_type = object

  def __init__(self, default=None):
    """Constructor.

    Args:
      default: Default assignment is made during initialization and will
        not pass through validation.
    """
    self.default = default

  def __call__(self, value):
    """Main interface to validator is call mechanism."""
    return self.Validate(value)

  def Validate(self, value):
    """Override this method to customize sub-class behavior.

    Args:
      value: Value to validate.

    Returns:
      Value if value is valid, or a valid representation of value.
    """
    return value

  def ToValue(self, value):
    """Convert 'value' to a simplified collection or basic type.

    Subclasses of Validator should override this method when the dumped
    representation of 'value' is not simply <type>(value) (e.g. a regex).

    Args:
      value: An object of the same type that was returned from Validate().

    Returns:
      An instance of a builtin type (e.g. int, str, dict, etc).  By default
      it returns 'value' unmodified.
    """
    return value


class Type(Validator):
  """Verifies property is of expected type.

  Can optionally convert value if it is not of the expected type.

  It is possible to specify a required field of a specific type in shorthand
  by merely providing the type.  This method is slightly less efficient than
  providing an explicit type but is not significant unless parsing a large
  amount of information:

    class Person(Validated):
      ATTRIBUTES = {'name': unicode,
                    'age': int,
                    }

  However, in most instances it is best to use the type constants:

    class Person(Validated):
      ATTRIBUTES = {'name': TypeUnicode,
                    'age': TypeInt,
                    }
  """

  def __init__(self, expected_type, convert=True, default=None):
    """Initialize Type validator.

    Args:
      expected_type: Type that attribute should validate against.
      convert: Cause conversion if value is not the right type.
        Conversion is done by calling the constructor of the type
        with the value as its first parameter.
    """
    super(Type, self).__init__(default)
    self.expected_type = expected_type
    self.convert = convert

  def Validate(self, value):
    """Validate that value is correct type.

    Args:
      value: Value to validate.

    Returns:
      None if value is None, value if value is of correct type, converted
      value if the validator is configured to convert.

    Raises:
      ValidationError if value is not of the right type and validator
      is not configured to convert.
    """
    if not isinstance(value, self.expected_type):
      if value is not None and self.convert:
        try:
          return self.expected_type(value)
        except ValueError, e:
          raise ValidationError('Type conversion failed for value \'%s\'.'
                                % value,
                                e)
        except TypeError, e:
          raise ValidationError('Expected value of type %s, but got \'%s\'.'
                                % (self.expected_type, value))
      else:
        raise MissingAttribute('Missing value is required.')
    else:
      return value


TYPE_BOOL = Type(bool)
TYPE_INT = Type(int)
TYPE_LONG = Type(long)
TYPE_STR = Type(str)
TYPE_UNICODE = Type(unicode)
TYPE_FLOAT = Type(float)


class Options(Validator):
  """Limit field based on pre-determined values.

  Options are used to make sure an enumerated set of values are the only
  one permitted for assignment.  It is possible to define aliases which
  map multiple string values to a single original.  An example of usage:

    class ZooAnimal(validated.Class):
      ATTRIBUTES = {
        'name': str,
        'kind': Options('platypus',                   # No aliases
                        ('rhinoceros', ['rhino']),    # One alias
                        ('canine', ('dog', 'puppy')), # Two aliases
                        )
  """

  def __init__(self, *options, **kw):
    """Initialize options.

    Args:
      options: List of allowed values.
    """
    if 'default' in kw:
      default = kw['default']
    else:
      default = None

    alias_map = {}
    def AddAlias(alias, original):
      """Set new alias on alias_map.

      Raises:
        AttributeDefinitionError when option already exists or if alias is
        not of type str..
      """
      if not isinstance(alias, str):
        raise AttributeDefinitionError(
            'All option values must be of type str.')
      elif alias in alias_map:
        raise AttributeDefinitionError(
            "Option '%s' already defined for options property." % alias)
      alias_map[alias] = original

    for option in options:
      if isinstance(option, str):
        AddAlias(option, option)

      elif isinstance(option, (list, tuple)):
        if len(option) != 2:
          raise AttributeDefinitionError("Alias is defined as a list of tuple "
                                         "with two items.  The first is the "
                                         "original option, while the second "
                                         "is a list or tuple of str aliases.\n"
                                         "\n  Example:\n"
                                         "      ('original', ('alias1', "
                                         "'alias2'")
        original, aliases = option
        AddAlias(original, original)
        if not isinstance(aliases, (list, tuple)):
          raise AttributeDefinitionError('Alias lists must be a list or tuple')

        for alias in aliases:
          AddAlias(alias, original)

      else:
        raise AttributeDefinitionError("All options must be of type str "
                                       "or of the form (str, [str...]).")
    super(Options, self).__init__(default)
    self.options = alias_map

  def Validate(self, value):
    """Validate options.

    Returns:
      Original value for provided alias.

    Raises:
      ValidationError when value is not one of predefined values.
    """
    if value is None:
      raise ValidationError('Value for options field must not be None.')
    value = str(value)
    if value not in self.options:
      raise ValidationError('Value \'%s\' not in %s.'
                            % (value, self.options))
    return self.options[value]


class Optional(Validator):
  """Definition of optional attributes.

  Optional values are attributes which can be set to None or left
  unset.  All values in a basic Validated class are set to None
  at initialization.  Failure to assign to non-optional values
  will result in a validation error when calling CheckInitialized.
  """

  def __init__(self, validator, default=None):
    """Initializer.

    This constructor will make a few guesses about the value passed in
    as the validator:

      - If the validator argument is a type, it automatically creates a Type
        validator around it.

      - If the validator argument is a list or tuple, it automatically
        creates an Options validator around it.

    Args:
      validator: Optional validation condition.

    Raises:
      AttributeDefinitionError if validator is not callable.
    """
    self.validator = AsValidator(validator)
    self.expected_type = self.validator.expected_type
    self.default = default

  def Validate(self, value):
    """Optionally require a value.

    Normal validators do not accept None.  This will accept none on
    behalf of the contained validator.

    Args:
      value: Value to be validated as optional.

    Returns:
      None if value is None, else results of contained validation.
    """
    if value is None:
      return None
    return self.validator(value)


class Regex(Validator):
  """Regular expression validator.

  Regular expression validator always converts value to string.  Note that
  matches must be exact.  Partial matches will not validate.  For example:

    class ClassDescr(Validated):
      ATTRIBUTES = { 'name': Regex(r'[a-zA-Z_][a-zA-Z_0-9]*'),
                     'parent': Type(type),
                     }

  Alternatively, any attribute that is defined as a string is automatically
  interpreted to be of type Regex.  It is possible to specify unicode regex
  strings as well.  This approach is slightly less efficient, but usually
  is not significant unless parsing large amounts of data:

    class ClassDescr(Validated):
      ATTRIBUTES = { 'name': r'[a-zA-Z_][a-zA-Z_0-9]*',
                     'parent': Type(type),
                     }

    # This will raise a ValidationError exception.
    my_class(name='AName with space', parent=AnotherClass)
  """

  def __init__(self, regex, string_type=unicode, default=None):
    """Initialized regex validator.

    Args:
      regex: Regular expression string to use for comparison.

    Raises:
      AttributeDefinitionError if string_type is not a kind of string.
    """
    super(Regex, self).__init__(default)
    if (not issubclass(string_type, basestring) or
        string_type is basestring):
      raise AttributeDefinitionError(
          'Regex fields must be a string type not %s.' % str(string_type))
    if isinstance(regex, basestring):
      self.re = re.compile('^%s$' % regex)
    else:
      raise AttributeDefinitionError(
          'Regular expression must be string.  Found %s.' % str(regex))

    self.expected_type = string_type

  def Validate(self, value):
    """Does validation of a string against a regular expression.

    Args:
      value: String to match against regular expression.

    Raises:
      ValidationError when value does not match regular expression or
      when value does not match provided string type.
    """
    if issubclass(self.expected_type, str):
      cast_value = TYPE_STR(value)
    else:
      cast_value = TYPE_UNICODE(value)

    if self.re.match(cast_value) is None:
      raise ValidationError('Value \'%s\' does not match expression \'%s\''
                            % (value, self.re.pattern))
    return cast_value


class RegexStr(Validator):
  """Validates that a string can compile as a regex without errors.

  Use this validator when the value of a field should be a regex.  That
  means that the value must be a string that can be compiled by re.compile().
  The attribute will then be a compiled re object.
  """

  def __init__(self, string_type=unicode, default=None):
    """Initialized regex validator.

    Raises:
      AttributeDefinitionError if string_type is not a kind of string.
    """
    if default is not None:
      default = re.compile(default)
    super(RegexStr, self).__init__(default)
    if (not issubclass(string_type, basestring) or
        string_type is basestring):
      raise AttributeDefinitionError(
          'RegexStr fields must be a string type not %s.' % str(string_type))

    self.expected_type = string_type

  def Validate(self, value):
    """Validates that the string compiles as a regular expression.

    Because the regular expression might have been expressed as a multiline
    string, this function also strips newlines out of value.

    Args:
      value: String to compile as a regular expression.

    Raises:
      ValueError when value does not compile as a regular expression.  TypeError
      when value does not match provided string type.
    """
    if issubclass(self.expected_type, str):
      cast_value = TYPE_STR(value)
    else:
      cast_value = TYPE_UNICODE(value)

    cast_value = cast_value.replace('\n', '')
    cast_value = cast_value.replace('\r', '')
    try:
      compiled = re.compile(cast_value)
    except re.error, e:
      raise ValidationError('Value \'%s\' does not compile: %s' % (value, e), e)
    return compiled

  def ToValue(self, value):
    """Returns the RE pattern for this validator."""
    return value.pattern


class Range(Validator):
  """Validates that numbers fall within the correct range.

  In theory this class can be emulated using Options, however error
  messages generated from that class will not be very intelligible.
  This class essentially does the same thing, but knows the intended
  integer range.

  Also, this range class supports floats and other types that implement
  ordinality.

  The range is inclusive, meaning 3 is considered in the range
  in Range(1,3).
  """

  def __init__(self, minimum, maximum, range_type=int, default=None):
    """Initializer for range.

    Args:
      minimum: Minimum for attribute.
      maximum: Maximum for attribute.
      range_type: Type of field.  Defaults to int.
    """
    super(Range, self).__init__(default)
    if not isinstance(minimum, range_type):
      raise AttributeDefinitionError(
          'Minimum value must be of type %s, instead it is %s (%s).' %
          (str(range_type), str(type(minimum)), str(minimum)))
    if not isinstance(maximum, range_type):
      raise AttributeDefinitionError(
          'Maximum value must be of type %s, instead it is %s (%s).' %
          (str(range_type), str(type(maximum)), str(maximum)))

    self.minimum = minimum
    self.maximum = maximum
    self.expected_type = range_type
    self._type_validator = Type(range_type)

  def Validate(self, value):
    """Validate that value is within range.

    Validates against range-type then checks the range.

    Args:
      value: Value to validate.

    Raises:
      ValidationError when value is out of range.  ValidationError when value
      is notd of the same range type.
    """
    cast_value = self._type_validator.Validate(value)
    if cast_value < self.minimum or cast_value > self.maximum:
      raise ValidationError('Value \'%s\' is out of range %s - %s'
                            % (str(value),
                               str(self.minimum),
                               str(self.maximum)))
    return cast_value


class Repeated(Validator):
  """Repeated field validator.

  Indicates that attribute is expected to be a repeated value, ie,
  a sequence.  This adds additional validation over just Type(list)
  in that it retains information about what can be stored in the list by
  use of its constructor field.
  """

  def __init__(self, constructor, default=None):
    """Initializer for repeated field.

    Args:
      constructor: Type used for verifying elements of sequence attribute.
    """
    super(Repeated, self).__init__(default)
    self.constructor = constructor
    self.expected_type = list

  def Validate(self, value):
    """Do validation of sequence.

    Value must be a list and all elements must be of type 'constructor'.

    Args:
      value: Value to validate.

    Raises:
      ValidationError if value is None, not a list or one of its elements is the
      wrong type.
    """
    if not isinstance(value, list):
      raise ValidationError('Repeated fields must be sequence, '
                            'but found \'%s\'.' % value)

    for item in value:
      if not isinstance(item, self.constructor):
        raise ValidationError('Repeated items must be %s, but found \'%s\'.'
                              % (str(self.constructor), str(item)))

    return value

########NEW FILE########
__FILENAME__ = yaml_builder
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""PyYAML event builder handler

Receives events from YAML listener and forwards them to a builder
object so that it can construct a properly structured object.
"""





from drydrop.app.meta import yaml_errors
from drydrop.app.meta import yaml_listener

import yaml

_TOKEN_DOCUMENT = 'document'
_TOKEN_SEQUENCE = 'sequence'
_TOKEN_MAPPING = 'mapping'
_TOKEN_KEY = 'key'
_TOKEN_VALUES = frozenset((
  _TOKEN_DOCUMENT,
  _TOKEN_SEQUENCE,
  _TOKEN_MAPPING,
  _TOKEN_KEY))


class Builder(object):
  """Interface for building documents and type from YAML events.

  Implement this interface to create a new builder.  Builders are
  passed to the BuilderHandler and used as a factory and assembler
  for creating concrete representations of YAML files.
  """

  def BuildDocument(self):
    """Build new document.

    The object built by this method becomes the top level entity
    that the builder handler constructs.  The actual type is
    determined by the sub-class of the Builder class and can essentially
    be any type at all.  This method is always called when the parser
    encounters the start of a new document.

    Returns:
      New object instance representing concrete document which is
      returned to user via BuilderHandler.GetResults().
    """

  def InitializeDocument(self, document, value):
    """Initialize document with value from top level of document.

    This method is called when the root document element is encountered at
    the top level of a YAML document.  It should get called immediately
    after BuildDocument.

    Receiving the None value indicates the empty document.

    Args:
      document: Document as constructed in BuildDocument.
      value: Scalar value to initialize the document with.
    """

  def BuildMapping(self, top_value):
    """Build a new mapping representation.

    Called when StartMapping event received.  Type of object is determined
    by Builder sub-class.

    Args:
      top_value: Object which will be new mappings parant.  Will be object
        returned from previous call to BuildMapping or BuildSequence.

    Returns:
      Instance of new object that represents a mapping type in target model.
    """

  def EndMapping(self, top_value, mapping):
    """Previously constructed mapping scope is at an end.

    Called when the end of a mapping block is encountered.  Useful for
    additional clean up or end of scope validation.

    Args:
      top_value: Value which is parent of the mapping.
      mapping: Mapping which is at the end of its scope.
    """

  def BuildSequence(self, top_value):
    """Build a new sequence representation.

    Called when StartSequence event received.  Type of object is determined
    by Builder sub-class.

    Args:
      top_value: Object which will be new sequences parant.  Will be object
        returned from previous call to BuildMapping or BuildSequence.

    Returns:
      Instance of new object that represents a sequence type in target model.
    """

  def EndSequence(self, top_value, sequence):
    """Previously constructed sequence scope is at an end.

    Called when the end of a sequence block is encountered.  Useful for
    additional clean up or end of scope validation.

    Args:
      top_value: Value which is parent of the sequence.
      sequence: Sequence which is at the end of its scope.
    """

  def MapTo(self, subject, key, value):
    """Map value to a mapping representation.

    Implementation is defined by sub-class of Builder.

    Args:
      subject: Object that represents mapping.  Value returned from
        BuildMapping.
      key: Key used to map value to subject.  Can be any scalar value.
      value: Value which is mapped to subject. Can be any kind of value.
    """

  def AppendTo(self, subject, value):
    """Append value to a sequence representation.

    Implementation is defined by sub-class of Builder.

    Args:
      subject: Object that represents sequence.  Value returned from
        BuildSequence
      value: Value to be appended to subject.  Can be any kind of value.
    """


class BuilderHandler(yaml_listener.EventHandler):
  """PyYAML event handler used to build objects.

  Maintains state information as it receives parse events so that object
  nesting is maintained.  Uses provided builder object to construct and
  assemble objects as it goes.

  As it receives events from the YAML parser, it builds a stack of data
  representing structural tokens.  As the scope of documents, mappings
  and sequences end, those token, value pairs are popped from the top of
  the stack so that the original scope can resume processing.

  A special case is made for the _KEY token.  It represents a temporary
  value which only occurs inside mappings.  It is immediately popped off
  the stack when it's associated value is encountered in the parse stream.
  It is necessary to do this because the YAML parser does not combine
  key and value information in to a single event.
  """

  def __init__(self, builder):
    """Initialization for builder handler.

    Args:
      builder: Instance of Builder class.

    Raises:
      ListenerConfigurationError when builder is not a Builder class.
    """
    if not isinstance(builder, Builder):
      raise yaml_errors.ListenerConfigurationError(
        'Must provide builder of type yaml_listener.Builder')
    self._builder = builder
    self._stack = None
    self._top = None
    self._results = []

  def _Push(self, token, value):
    """Push values to stack at start of nesting.

    When a new object scope is beginning, will push the token (type of scope)
    along with the new objects value, the latter of which is provided through
    the various build methods of the builder.

    Args:
      token: Token indicating the type of scope which is being created; must
        belong to _TOKEN_VALUES.
      value: Value to associate with given token.  Construction of value is
        determined by the builder provided to this handler at construction.
    """
    self._top = (token, value)
    self._stack.append(self._top)

  def _Pop(self):
    """Pop values from stack at end of nesting.

    Called to indicate the end of a nested scope.

    Returns:
      Previously pushed value at the top of the stack.
    """
    assert self._stack != [] and self._stack is not None
    token, value = self._stack.pop()
    if self._stack:
      self._top = self._stack[-1]
    else:
      self._top = None
    return value

  def _HandleAnchor(self, event):
    """Handle anchor attached to event.

    Currently will raise an error if anchor is used.  Anchors are used to
    define a document wide tag to a given value (scalar, mapping or sequence).

    Args:
      event: Event which may have anchor property set.

    Raises:
      NotImplementedError if event attempts to use an anchor.
    """
    if hasattr(event, 'anchor') and event.anchor is not None:
      raise NotImplementedError, 'Anchors not supported in this handler'

  def _HandleValue(self, value):
    """Handle given value based on state of parser

    This method handles the various values that are created by the builder
    at the beginning of scope events (such as mappings and sequences) or
    when a scalar value is received.

    Method is called when handler receives a parser, MappingStart or
    SequenceStart.

    Args:
      value: Value received as scalar value or newly constructed mapping or
        sequence instance.

    Raises:
      InternalError if the building process encounters an unexpected token.
      This is an indication of an implementation error in BuilderHandler.
    """
    token, top_value = self._top

    if token == _TOKEN_KEY:
      key = self._Pop()
      mapping_token, mapping = self._top
      assert _TOKEN_MAPPING == mapping_token
      self._builder.MapTo(mapping, key, value)

    elif token == _TOKEN_MAPPING:
      self._Push(_TOKEN_KEY, value)

    elif token == _TOKEN_SEQUENCE:
      self._builder.AppendTo(top_value, value)

    elif token == _TOKEN_DOCUMENT:
      self._builder.InitializeDocument(top_value, value)

    else:
      raise yaml_errors.InternalError('Unrecognized builder token:\n%s' % token)

  def StreamStart(self, event, loader):
    """Initializes internal state of handler

    Args:
      event: Ignored.
    """
    assert self._stack is None
    self._stack = []
    self._top = None
    self._results = []

  def StreamEnd(self, event, loader):
    """Cleans up internal state of handler after parsing

    Args:
      event: Ignored.
    """
    assert self._stack == [] and self._top is None
    self._stack = None

  def DocumentStart(self, event, loader):
    """Build new document.

    Pushes new document on to stack.

    Args:
      event: Ignored.
    """
    assert self._stack == []
    self._Push(_TOKEN_DOCUMENT, self._builder.BuildDocument())

  def DocumentEnd(self, event, loader):
    """End of document.

    Args:
      event: Ignored.
    """
    assert self._top[0] == _TOKEN_DOCUMENT
    self._results.append(self._Pop())

  def Alias(self, event, loader):
    """Not implemented yet.

    Args:
      event: Ignored.
    """
    raise NotImplementedError('Anchors not supported in this handler')

  def Scalar(self, event, loader):
    """Handle scalar value

    Since scalars are simple values that are passed directly in by the
    parser, handle like any value with no additional processing.

    Of course, key values will be handles specially.  A key value is recognized
    when the top token is _TOKEN_MAPPING.

    Args:
      event: Event containing scalar value.
    """
    self._HandleAnchor(event)
    if event.tag is None and self._top[0] != _TOKEN_MAPPING:
      try:
        tag = loader.resolve(yaml.nodes.ScalarNode,
                             event.value, event.implicit)
      except IndexError:
        tag = loader.DEFAULT_SCALAR_TAG
    else:
      tag = event.tag

    if tag is None:
      value = event.value
    else:
      node = yaml.nodes.ScalarNode(tag,
                                   event.value,
                                   event.start_mark,
                                   event.end_mark,
                                   event.style)
      value = loader.construct_object(node)
    self._HandleValue(value)

  def SequenceStart(self, event, loader):
    """Start of sequence scope

    Create a new sequence from the builder and then handle in the context
    of its parent.

    Args:
      event: SequenceStartEvent generated by loader.
      loader: Loader that generated event.
    """
    self._HandleAnchor(event)
    token, parent = self._top

    if token == _TOKEN_KEY:
      token, parent = self._stack[-2]
    sequence = self._builder.BuildSequence(parent)
    self._HandleValue(sequence)
    self._Push(_TOKEN_SEQUENCE, sequence)

  def SequenceEnd(self, event, loader):
    """End of sequence.

    Args:
      event: Ignored
      loader: Ignored.
      """
    assert self._top[0] == _TOKEN_SEQUENCE
    end_object = self._Pop()
    top_value = self._top[1]
    self._builder.EndSequence(top_value, end_object)

  def MappingStart(self, event, loader):
    """Start of mapping scope.

    Create a mapping from builder and then handle in the context of its
    parent.

    Args:
      event: MappingStartEvent generated by loader.
      loader: Loader that generated event.
    """
    self._HandleAnchor(event)
    token, parent = self._top

    if token == _TOKEN_KEY:
      token, parent = self._stack[-2]
    mapping = self._builder.BuildMapping(parent)
    self._HandleValue(mapping)
    self._Push(_TOKEN_MAPPING, mapping)

  def MappingEnd(self, event, loader):
    """End of mapping

    Args:
      event: Ignored.
      loader: Ignored.
    """
    assert self._top[0] == _TOKEN_MAPPING
    end_object = self._Pop()
    top_value = self._top[1]
    self._builder.EndMapping(top_value, end_object)

  def GetResults(self):
    """Get results of document stream processing.

    This method can be invoked after fully parsing the entire YAML file
    to retrieve constructed contents of YAML file.  Called after EndStream.

    Returns:
      A tuple of all document objects that were parsed from YAML stream.

    Raises:
      InternalError if the builder stack is not empty by the end of parsing.
    """
    if self._stack is not None:
      raise yaml_errors.InternalError('Builder stack is not empty.')
    return tuple(self._results)

########NEW FILE########
__FILENAME__ = yaml_errors
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Errors used in the YAML API, which is used by app developers."""



class Error(Exception):
  """Base datastore yaml error type."""

class ProtocolBufferParseError(Error):
  """Error in protocol buffer parsing"""


class EmptyConfigurationFile(Error):
  """Tried to load empty configuration file."""


class MultipleConfigurationFile(Error):
  """Tried to load configuration file with multiple objects."""


class UnexpectedAttribute(Error):
  """Raised when an unexpected attribute is encounted."""


class DuplicateAttribute(Error):
  """Generated when an attribute is assigned to twice."""


class ListenerConfigurationError(Error):
  """Generated when there is a parsing problem due to configuration."""


class IllegalEvent(Error):
  """Raised when an unexpected event type is received by listener."""


class InternalError(Error):
  """Raised when an internal implementation error is detected."""


class EventListenerError(Error):
  """Top level exception raised by YAML listener.

  Any exception raised within the process of parsing a YAML file via an
  EventListener is caught and wrapped in an EventListenerError.  The causing
  exception is maintained, but additional useful information is saved which
  can be used for reporting useful information to users.

  Attributes:
    cause: The original exception which caused the EventListenerError.
  """

  def __init__(self, cause):
    """Initialize event-listener error."""
    if hasattr(cause, 'args') and cause.args:
      Error.__init__(self, *cause.args)
    else:
      Error.__init__(self, str(cause))
    self.cause = cause


class EventListenerYAMLError(EventListenerError):
  """Generated specifically for yaml.error.YAMLError."""


class EventError(EventListenerError):
  """Generated specifically when an error occurs in event handler.

  Attributes:
    cause: The original exception which caused the EventListenerError.
    event: Event being handled when exception occured.
  """

  def __init__(self, cause, event):
    """Initialize event-listener error."""
    EventListenerError.__init__(self, cause)
    self.event = event

  def __str__(self):
    return '%s\n%s' % (self.cause, self.event.start_mark)

########NEW FILE########
__FILENAME__ = yaml_listener
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""PyYAML event listener

Contains class which interprets YAML events and forwards them to
a handler object.
"""


from drydrop.app.meta import yaml_errors
import yaml


_EVENT_METHOD_MAP = {
  yaml.events.StreamStartEvent: 'StreamStart',
  yaml.events.StreamEndEvent: 'StreamEnd',
  yaml.events.DocumentStartEvent: 'DocumentStart',
  yaml.events.DocumentEndEvent: 'DocumentEnd',
  yaml.events.AliasEvent: 'Alias',
  yaml.events.ScalarEvent: 'Scalar',
  yaml.events.SequenceStartEvent: 'SequenceStart',
  yaml.events.SequenceEndEvent: 'SequenceEnd',
  yaml.events.MappingStartEvent: 'MappingStart',
  yaml.events.MappingEndEvent: 'MappingEnd',
}


class EventHandler(object):
  """Handler interface for parsing YAML files.

  Implement this interface to define specific YAML event handling class.
  Implementing classes instances are passed to the constructor of
  EventListener to act as a receiver of YAML parse events.
  """
  def StreamStart(self, event, loader):
    """Handle start of stream event"""

  def StreamEnd(self, event, loader):
    """Handle end of stream event"""

  def DocumentStart(self, event, loader):
    """Handle start of document event"""

  def DocumentEnd(self, event, loader):
    """Handle end of document event"""

  def Alias(self, event, loader):
    """Handle alias event"""

  def Scalar(self, event, loader):
    """Handle scalar event"""

  def SequenceStart(self, event, loader):
    """Handle start of sequence event"""

  def SequenceEnd(self, event, loader):
    """Handle end of sequence event"""

  def MappingStart(self, event, loader):
    """Handle start of mappping event"""

  def MappingEnd(self, event, loader):
    """Handle end of mapping event"""


class EventListener(object):
  """Helper class to re-map PyYAML events to method calls.

  By default, PyYAML generates its events via a Python generator.  This class
  is a helper that iterates over the events from the PyYAML parser and forwards
  them to a handle class in the form of method calls.  For simplicity, the
  underlying event is forwarded to the handler as a parameter to the call.

  This object does not itself produce iterable objects, but is really a mapping
  to a given handler instance.

    Example use:

      class PrintDocumentHandler(object):
        def DocumentStart(event):
          print "A new document has been started"

      EventListener(PrintDocumentHandler()).Parse('''
        key1: value1
        ---
        key2: value2
        '''

      >>> A new document has been started
          A new document has been started

  In the example above, the implemented handler class (PrintDocumentHandler)
  has a single method which reports each time a new document is started within
  a YAML file.  It is not necessary to subclass the EventListener, merely it
  receives a PrintDocumentHandler instance.  Every time a new document begins,
  PrintDocumentHandler.DocumentStart is called with the PyYAML event passed
  in as its parameter..
  """

  def __init__(self, event_handler):
    """Initialize PyYAML event listener.

    Constructs internal mapping directly from event type to method on actual
    handler.  This prevents reflection being used during actual parse time.

    Args:
      event_handler: Event handler that will receive mapped events. Must
        implement at least one appropriate handler method named from
        the values of the _EVENT_METHOD_MAP.

    Raises:
      ListenerConfigurationError if event_handler is not an EventHandler.
    """
    if not isinstance(event_handler, EventHandler):
      raise yaml_errors.ListenerConfigurationError(
        'Must provide event handler of type yaml_listener.EventHandler')
    self._event_method_map = {}
    for event, method in _EVENT_METHOD_MAP.iteritems():
      self._event_method_map[event] = getattr(event_handler, method)

  def HandleEvent(self, event, loader=None):
    """Handle individual PyYAML event.

    Args:
      event: Event to forward to method call in method call.

    Raises:
      IllegalEvent when receives an unrecognized or unsupported event type.
    """
    if event.__class__ not in _EVENT_METHOD_MAP:
      raise yaml_errors.IllegalEvent(
            "%s is not a valid PyYAML class" % event.__class__.__name__)
    if event.__class__ in self._event_method_map:
      self._event_method_map[event.__class__](event, loader)

  def _HandleEvents(self, events):
    """Iterate over all events and send them to handler.

    This method is not meant to be called from the interface.

    Only use in tests.

    Args:
      events: Iterator or generator containing events to process.
    raises:
      EventListenerParserError when a yaml.parser.ParserError is raised.
      EventError when an exception occurs during the handling of an event.
    """
    for event in events:
      try:
        self.HandleEvent(*event)
      except Exception, e:
        event_object, loader = event
        raise yaml_errors.EventError(e, event_object)

  def _GenerateEventParameters(self,
                               stream,
                               loader_class=yaml.loader.SafeLoader):
    """Creates a generator that yields event, loader parameter pairs.

    For use as parameters to HandleEvent method for use by Parse method.
    During testing, _GenerateEventParameters is simulated by allowing
    the harness to pass in a list of pairs as the parameter.

    A list of (event, loader) pairs must be passed to _HandleEvents otherwise
    it is not possible to pass the loader instance to the handler.

    Also responsible for instantiating the loader from the Loader
    parameter.

    Args:
      stream: String document or open file object to process as per the
        yaml.parse method.  Any object that implements a 'read()' method which
        returns a string document will work.
      Loader: Loader class to use as per the yaml.parse method.  Used to
        instantiate new yaml.loader instance.

    Yields:
      Tuple(event, loader) where:
        event: Event emitted by PyYAML loader.
        loader_class: Used for dependency injection.
    """
    assert loader_class is not None
    try:
      loader = loader_class(stream)
      while loader.check_event():
        yield (loader.get_event(), loader)
    except yaml.error.YAMLError, e:
      raise yaml_errors.EventListenerYAMLError(e)

  def Parse(self, stream, loader_class=yaml.loader.SafeLoader):
    """Call YAML parser to generate and handle all events.

    Calls PyYAML parser and sends resulting generator to handle_event method
    for processing.

    Args:
      stream: String document or open file object to process as per the
        yaml.parse method.  Any object that implements a 'read()' method which
        returns a string document will work with the YAML parser.
      loader_class: Used for dependency injection.
    """
    self._HandleEvents(self._GenerateEventParameters(stream, loader_class))

########NEW FILE########
__FILENAME__ = yaml_object
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Builder for mapping YAML documents to object instances.

ObjectBuilder is responsible for mapping a YAML document to classes defined
using the validation mechanism (see drydrop.app.meta.validation.py).
"""





from drydrop.app.meta import validation
from drydrop.app.meta import yaml_listener
from drydrop.app.meta import yaml_builder
from drydrop.app.meta import yaml_errors

import yaml


class _ObjectMapper(object):
  """Wrapper used for mapping attributes from a yaml file to an object.

  This wrapper is required because objects do not know what property they are
  associated with a creation time, and therefore can not be instantiated
  with the correct class until they are mapped to their parents.
  """

  def __init__(self):
    """Object mapper starts off with empty value."""
    self.value = None
    self.seen = set()

  def set_value(self, value):
    """Set value of instance to map to.

    Args:
      value: Instance that this mapper maps to.
    """
    self.value = value

  def see(self, key):
    if key in self.seen:
      raise yaml_errors.DuplicateAttribute("Duplicate attribute '%s'." % key)
    self.seen.add(key)

class _ObjectSequencer(object):
  """Wrapper used for building sequences from a yaml file to a list.

  This wrapper is required because objects do not know what property they are
  associated with a creation time, and therefore can not be instantiated
  with the correct class until they are mapped to their parents.
  """

  def __init__(self):
    """Object sequencer starts off with empty value."""
    self.value = []
    self.constructor = None

  def set_constructor(self, constructor):
    """Set object used for constructing new sequence instances.

    Args:
      constructor: Callable which can accept no arguments.  Must return
        an instance of the appropriate class for the container.
    """
    self.constructor = constructor


class ObjectBuilder(yaml_builder.Builder):
  """Builder used for constructing validated objects.

  Given a class that implements validation.Validated, it will parse a YAML
  document and attempt to build an instance of the class.  It does so by mapping
  YAML keys to Python attributes.  ObjectBuilder will only map YAML fields
  to attributes defined in the Validated subclasses 'ATTRIBUTE' definitions.
  Lists are mapped to validated.  Repeated attributes and maps are mapped to
  validated.Type properties.

  For a YAML map to be compatible with a class, the class must have a
  constructor that can be called with no parameters.  If the provided type
  does not have such a constructor a parse time error will occur.
  """

  def __init__(self, default_class):
    """Initialize validated object builder.

    Args:
      default_class: Class that is instantiated upon the detection of a new
        document.  An instance of this class will act as the document itself.
    """
    self.default_class = default_class

  def _GetRepeated(self, attribute):
    """Get the ultimate type of a repeated validator.

    Looks for an instance of validation.Repeated, returning its constructor.

    Args:
      attribute: Repeated validator attribute to find type for.

    Returns:
      The expected class of of the Type validator, otherwise object.
    """
    if isinstance(attribute, validation.Optional):
      attribute = attribute.validator
    if isinstance(attribute, validation.Repeated):
      return attribute.constructor
    return object

  def BuildDocument(self):
    """Instantiate new root validated object.

    Returns:
      New instance of validated object.
    """
    return self.default_class()

  def BuildMapping(self, top_value):
    """New instance of object mapper for opening map scope.

    Args:
      top_value: Parent of nested object.

    Returns:
      New instance of object mapper.
    """
    result = _ObjectMapper()
    if isinstance(top_value, self.default_class):
      result.value = top_value
    return result

  def EndMapping(self, top_value, mapping):
    """When leaving scope, makes sure new object is initialized.

    This method is mainly for picking up on any missing required attributes.

    Args:
      top_value: Parent of closing mapping object.
      mapping: _ObjectMapper instance that is leaving scope.
    """
    try:
      mapping.value.CheckInitialized()
    except validation.ValidationError:
      raise
    except Exception, e:
      try:
        error_str = str(e)
      except Exception:
        error_str = '<unknown>'

      raise validation.ValidationError("Invalid object:\n%s" % error_str, e)

  def BuildSequence(self, top_value):
    """New instance of object sequence.

    Args:
      top_value: Object that contains the new sequence.

    Returns:
      A new _ObjectSequencer instance.
    """
    return _ObjectSequencer()

  def MapTo(self, subject, key, value):
    """Map key-value pair to an objects attribute.

    Args:
      subject: _ObjectMapper of object that will receive new attribute.
      key: Key of attribute.
      value: Value of new attribute.

    Raises:
      UnexpectedAttribute when the key is not a validated attribute of
      the subject value class.
    """
    assert subject.value is not None
    if key not in subject.value.ATTRIBUTES:
      raise yaml_errors.UnexpectedAttribute(
          'Unexpected attribute \'%s\' for object of type %s.' %
          (key, str(subject.value.__class__)))

    if isinstance(value, _ObjectMapper):
      value.set_value(subject.value.GetAttribute(key).expected_type())
      value = value.value
    elif isinstance(value, _ObjectSequencer):
      value.set_constructor(self._GetRepeated(subject.value.ATTRIBUTES[key]))
      value = value.value

    subject.see(key)
    try:
      setattr(subject.value, key, value)
    except validation.ValidationError, e:
      try:
        error_str = str(e)
      except Exception:
        error_str = '<unknown>'

      try:
        value_str = str(value)
      except Exception:
        value_str = '<unknown>'

      e.message = ("Unable to assign value '%s' to attribute '%s':\n%s" %
                   (value_str, key, error_str))
      raise e
    except Exception, e:
      try:
        error_str = str(e)
      except Exception:
        error_str = '<unknown>'

      try:
        value_str = str(value)
      except Exception:
        value_str = '<unknown>'

      message = ("Unable to assign value '%s' to attribute '%s':\n%s" %
                 (value_str, key, error_str))
      raise validation.ValidationError(message, e)

  def AppendTo(self, subject, value):
    """Append a value to a sequence.

    Args:
      subject: _ObjectSequence that is receiving new value.
      value: Value that is being appended to sequence.
    """
    if isinstance(value, _ObjectMapper):
      value.set_value(subject.constructor())
      subject.value.append(value.value)
    else:
      subject.value.append(value)


def BuildObjects(default_class, stream, loader=yaml.loader.SafeLoader):
  """Build objects from stream.

  Handles the basic case of loading all the objects from a stream.

  Args:
    default_class: Class that is instantiated upon the detection of a new
      document.  An instance of this class will act as the document itself.
    stream: String document or open file object to process as per the
      yaml.parse method.  Any object that implements a 'read()' method which
      returns a string document will work with the YAML parser.
    loader_class: Used for dependency injection.

  Returns:
    List of default_class instances parsed from the stream.
  """
  builder = ObjectBuilder(default_class)
  handler = yaml_builder.BuilderHandler(builder)
  listener = yaml_listener.EventListener(handler)

  listener.Parse(stream, loader)
  return handler.GetResults()


def BuildSingleObject(default_class, stream, loader=yaml.loader.SafeLoader):
  """Build object from stream.

  Handles the basic case of loading a single object from a stream.

  Args:
    default_class: Class that is instantiated upon the detection of a new
      document.  An instance of this class will act as the document itself.
    stream: String document or open file object to process as per the
      yaml.parse method.  Any object that implements a 'read()' method which
      returns a string document will work with the YAML parser.
    loader_class: Used for dependency injection.
  """
  definitions = BuildObjects(default_class, stream, loader)

  if len(definitions) < 1:
    raise yaml_errors.EmptyConfigurationFile()
  if len(definitions) > 1:
    raise yaml_errors.MultipleConfigurationFile()
  return definitions[0]

########NEW FILE########
__FILENAME__ = event
# -*- mode: python; coding: utf-8 -*-
import logging
import google.appengine.ext.db as db
from drydrop.app.core.model import Model
from drydrop.lib.properties import JSONProperty

class Event(db.Expando, Model):
    author = db.StringProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    code = db.IntegerProperty(default=0)
    action = db.StringProperty()
    domain = db.StringProperty()
    info = db.TextProperty()

########NEW FILE########
__FILENAME__ = resource
# -*- mode: python; coding: utf-8 -*-
import logging
import google.appengine.ext.db as db
from drydrop.app.core.model import Model

class Resource(db.Expando, Model):
    path = db.StringProperty()
    generation = db.IntegerProperty()
    content = db.BlobProperty()
    domain = db.StringProperty()
    created_on = db.DateTimeProperty(auto_now_add=True)

########NEW FILE########
__FILENAME__ = session
# -*- mode: python; coding: utf-8 -*-
import logging
import google.appengine.ext.db as db
from drydrop.app.core.model import Model

class Session(db.Expando, Model):
    
    pass
########NEW FILE########
__FILENAME__ = settings
# -*- mode: python; coding: utf-8 -*-
import logging
import google.appengine.ext.db as db
from drydrop.app.core.model import Model

class Settings(db.Expando, Model):
    source = db.StringProperty()
    config = db.StringProperty()
    version = db.IntegerProperty(default=1)
    domain = db.StringProperty()
    last_updated = db.DateTimeProperty()
    github_login = db.StringProperty() # for private repos
    github_token = db.StringProperty() # for private repos

########NEW FILE########
__FILENAME__ = dbg
# -*- mode: python; coding: utf-8 -*-
def b():
  import pdb, sys
  debugger = pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__)
  debugger.set_trace(sys._getframe().f_back)

########NEW FILE########
__FILENAME__ = jinja_loaders
# -*- mode: python; coding: utf-8 -*-
import os.path
from drydrop_handler import LOCAL
from jinja2 import FileSystemLoader, TemplateNotFound
from drydrop.lib.utils import universal_read

class InternalTemplateLoader(FileSystemLoader):
    
    def __init__(self, searchpath, encoding='utf-8'):
        if isinstance(searchpath, basestring):
            searchpath = [searchpath]
        self.searchpath = list(searchpath)
        if LOCAL:
            self.searchpath = [p.replace('.zip', '') for p in self.searchpath]
        self.encoding = encoding
    
    def get_source(self, environment, template):
        if LOCAL:
            # during local development, templates are files and we want "uptodate" feature
            return FileSystemLoader.get_source(self, environment, template)
        
        # on production server template may come from zip file
        for searchpath in self.searchpath:
            filename = os.path.join(searchpath, template)
            contents = universal_read(filename)
            if contents is None:
                continue
            contents = contents.decode(self.encoding)
            def uptodate():
                return True
            return contents, filename, uptodate
        raise TemplateNotFound(template)
########NEW FILE########
__FILENAME__ = json
import types
import simplejson
from decimal import *
import datetime

json_parse = lambda s: simplejson.loads(s.decode("utf-8"))

class DateTimeAwareJSONEncoder(simplejson.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time types
    """
    
    DATE_FORMAT = "%Y-%m-%d" 
    TIME_FORMAT = "%H:%M:%S"
    
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime("%s %s" % (self.DATE_FORMAT, self.TIME_FORMAT))
        elif isinstance(o, datetime.date):
            return o.strftime(self.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            return o.strftime(self.TIME_FORMAT)
        else:
            return super(DateTimeAwareJSONEncoder, self).default(o)

def json_encode(data,**kwargs):
    """
    The main issues with default json serializer is that properties that
    had been added to a object dynamically are being ignored (and it also has 
    problems with some models).
    """

    def _any(data):
        ret = None
        if type(data) is types.ListType:
            ret = _list(data)
        elif type(data) is types.DictType:
            ret = _dict(data)
        elif isinstance(data, Decimal):
            # simplejson.dumps() cant handle Decimal
            ret = str(data)
        else:
            ret = data
        return ret
    
    def _list(data):
        ret = []
        for v in data:
            ret.append(_any(v))
        return ret
    
    def _dict(data):
        ret = {}
        for k,v in data.items():
            ret[k] = _any(v)
        return ret
    
    ret = _any(data)
    if kwargs.get('nice'):
        return simplejson.dumps(ret, cls=DateTimeAwareJSONEncoder, indent=4, ensure_ascii=False)
    else:
        return simplejson.dumps(ret, cls=DateTimeAwareJSONEncoder, ensure_ascii=False)
########NEW FILE########
__FILENAME__ = nice_traceback
# -*- mode: python; coding: utf-8 -*-
import logging
import re
import sys
import os
from traceback import *

# generate nice traceback with optional textmate links
def format_nice_traceback(traceback):
    tb = "<table>"
    lines = traceback.splitlines(1)
    lines.reverse()
    for line in lines[1:len(lines)-2]:
        filename = re.findall('File "(.+)",', line)
        linenumber = re.findall(', line\s(\d+)', line)
        modulename = re.findall(', in ([A-Za-z0-9_]+)', line)
        if filename and linenumber and not re.match("<(.+)>",filename[0]):
            file_name = filename[0]
            module_name = 'in <span class="module">%s</span>' % modulename[0] if modulename else ""
            base_name = os.path.basename(file_name)
            line = linenumber[0]
            html = '<tr><td><a class="file" href="txmt://open/?url=file://%s&line=%s">%s:%s</a></td><td>%s</td></tr>\n' % (file_name,line,base_name,line,module_name)
            tb += html
    tb += '</table>'
    return tb

def show_error(handler, code, log_msg = ''):
    handler.error(code)
    handler.response.out.write('<html><body>')
    if sys.exc_info()[0]:
        if not isinstance(sys.exc_info()[0], str):
            exception_name = sys.exc_info()[0].__name__
            exception_details = str(sys.exc_info()[1])
        else:
            exception_name = 'Exception'
            exception_details = str(sys.exc_info())
        exception_traceback = ''.join(format_exception(*sys.exc_info()))
            
        tb=format_nice_traceback(exception_traceback)
        handler.response.out.write('<html><body><head><title>'+exception_details+'</title>\n')
        handler.response.out.write('<style>\n')
        handler.response.out.write('html {font-family: arial}\n')
        handler.response.out.write('h1 { padding:5px; color: white; background-color:red; font-weight:bold;}\n')
        handler.response.out.write('h2 { padding-bottom: 0px; margin-bottom: 0px; }\n')
        handler.response.out.write('.file { font-family: courier; font-size: 12px; }\n')
        handler.response.out.write('.module { color: darkGreen; }\n')
        handler.response.out.write('</style></head>\n')
        handler.response.out.write('<h1>%s: %s</h1>\n' % (exception_name, exception_details))
        handler.response.out.write('<h2>Traceback:</h2>\n')
        handler.response.out.write('%s' % tb)
    else:
        handler.response.out.write('<h1>%s</h1>\n' % log_msg)
    handler.response.out.write('</body></html>')

def nice_traceback(f):
    def inner(self, *args, **kvargs):
        try:
            f(self, *args, **kvargs)
        except:
            show_error(self, 500)
    return inner
########NEW FILE########
__FILENAME__ = properties
# -*- mode: python; coding: utf-8 -*-
import logging
import pickle
import base64
from google.appengine.ext import db
from google.appengine.api import datastore_types
from drydrop.lib.utils import *
from drydrop.lib.json import *
        
class JSONProperty(db.TextProperty):

    def get_value_for_datastore(self, model_instance):
        value = self.__get__(model_instance, model_instance.__class__)
        return db.Text(self._deflate(value))

    def validate(self, value):
        return value

    def make_value_from_datastore(self, value):
        return self._inflate(value)

    def _inflate(self, value):
        return json_parse(value)

    def _deflate(self, value):
        return json_encode(value)

class PickleProperty(db.BlobProperty):

    def get_value_for_datastore(self, model_instance):
        value = self.__get__(model_instance, model_instance.__class__)
        return db.Blob(self._deflate(value))

    def validate(self, value):
        return value

    def make_value_from_datastore(self, value):
        return self._inflate(value)

    def _inflate(self, value):
        try:
            return pickle.loads(value)
        except:
            return ""

    def _deflate(self, value):
        return pickle.dumps(value)

########NEW FILE########
__FILENAME__ = utils
# -*- mode: python; coding: utf-8 -*-
import os
import os.path
import errno
from string import *
from random import choice
from string import digits, letters
import logging
import urlparse
import re
import simplejson
import sys
import zipfile
import urllib
from drydrop_handler import LOCAL

def import_module(name):
    __import__(name)
    return sys.modules[name]
      
zipfile_cache = {}
def universal_read(path):
    if LOCAL: 
        path = path.replace('.zip', '')
        return open(path, 'r').read()
    m = re.match(r'^(.*?)/([^/]+?)\.zip/(.*)$', path)
    if m is None: return open(path, 'r').read()

    global zipfile_cache
    
    zipfilename = os.path.join(m.group(1), m.group(2)+".zip")
    zipfile_object = zipfile_cache.get(zipfilename)
    if zipfile_object is None:
        try:
            zipfile_object = zipfile.ZipFile(zipfilename)
        except (IOError, RuntimeError), err:
            logging.error('Can\'t open zipfile %s: %s', zipfilename, err)
            return None
        zipfile_cache[zipfilename] = zipfile_object
    relfilename = os.path.join(m.group(2), m.group(3))
    return zipfile_object.read(relfilename)

def read_utf8(path):
    return universal_read(path).decode('utf-8')
    
def camelize(string):
    string = string.replace('-', '_')
    return ''.join([word.capitalize() for word in string.split('_')])

def camelizejs(string):
    string = string.replace('-', '_')
    parts = string.split('_')
    first = parts.pop(0)
    return first+''.join([word.capitalize() for word in parts])
    
def decamelizejs(string):
    s = re.sub(r'([A-Z])', '_\\1', string)
    return s.lower()

def uniqueid(length):
    POOL = digits + letters
    return ''.join([choice(POOL) for i in range(length)])
    
def decode_json_param(value):
    try:
        return simplejson.loads(value)
    except:
        return str(value) # return it as string

class struct: 
    pass
    
def dict2struct(dct):
    if isinstance(dct,dict):
        s=struct()
        for key,val in dct.iteritems():
            setattr(s,key,dict2struct(val))
        return s
    elif isinstance(dct,list):
        return [dict2struct(val) for val in dct]
    else:
        return dct

def array2dict(array,key):
    out={}
    for item in array:
        out[item[key]]=item
    return out

def dict2array(dct):
    arr=[]
    for item in dct.values():
        arr+=item
    return arr
    
def struct2dict(array,key):
    out={}
    for item in array:
        out[getattr(item,key)]=item
    return out

def lastitem(array):
    return array[len(array)-1]
        
def miditem(array):
    return array[len(array)/2]

def filter_dict(mydict,*args,**kwargs):
    out={}
    only=kwargs.get('only')
    remove=kwargs.get('remove')
    if only:
        out.update(dict([ (str(key),mydict[key]) for key in mydict if key in only]))
    if remove:    
        out.update(dict([ (str(key),mydict[key]) for key in mydict if key not in only]))
    return out

def hash_dict(mydict):
    return hash(tuple(mydict.iteritems()))

def key_dict(d):
    return urllib.urlencode(d)
    
def lookup_method(selector, context):
    selectors = selector.split('.')
    method_name = selectors.pop()
    class_name = selectors.pop()
    module_name = join(selectors, '.')
    module = import_module(module_name)
    klass = module.__dict__[class_name]   
    instance = klass(context)
    return instance.__getattribute__(method_name)
    
_base_js_escapes = (
    ("\\", "\\\\"),
    ("'", "\\'"),
    ("\n", "\\\n"),
    
)

def open_if_exists(filename, mode='r'):
    """Returns a file descriptor for the filename if that file exists, otherwise `None`."""
    try:
        return open(filename, mode)
    except IOError, e:
        pass

def escape_codes(start, stop):
    return tuple([('%c' % z, '\\x%02X' % z) for z in range(start, stop)])

# Escape every ASCII character with a value less than 32.
_js_escapes = (_base_js_escapes+escape_codes(0,9)+escape_codes(11,32))

def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    for bad, good in _js_escapes:
        value = value.replace(bad, good)
    return value        
    
def pluralize(noun):
    if re.search('[sxz]$', noun):
        return re.sub('$', 'es', noun)
    elif re.search('[^aeioudgkprt]h$', noun):
        return re.sub('$', 'es', noun)
    elif re.search('[^aeiou]y$', noun):
        return re.sub('y$', 'ies', noun)
    else:
        return noun + 's'
########NEW FILE########
__FILENAME__ = walker
# -*- mode: python; coding: utf-8 -*-
import os
import re
import inspect
import zipfile
from drydrop_handler import APP_ROOT
from drydrop.lib.utils import import_module

def cherrypick_classes_into_module(source, destination, common_ancestor=None):
    for key, item in source.__dict__.iteritems():
        if inspect.isclass(item):
            if common_ancestor is None or (issubclass(item, common_ancestor) and item!=common_ancestor):
                destination.__dict__[key] = item
            
def import_submodules(path, destination, ancestor=None):
    # want to import all classes from all *.py in directory pointed by path and put them into destination module
    #   optionaly also want to take only classes which are descendants of given ancestor
    #
    # classic path is in form: /here/is/some/project/dir/and/some/path/to/__init__.py
    # zip path is in form: something.zip/some/path/to/__init__.py
    # DRY_ROOT is path to project dir, where are located all zip files (it is not possible to extract this form zip path alone)
    #
    dir_path = os.path.dirname(path)
    m = re.match(r'^([^/]*?\.zip)/(.*)$', dir_path)
    if m:
        # zip case (we are on appspot.com)
        zipname = m.group(1)
        subpath = m.group(2)
        dot_module_path = subpath.replace('/', '.')
        module = zipname.split('.')[0]
        z = zipfile.ZipFile(os.path.join(APP_ROOT, zipname), 'r')
        for info in z.infolist():
            f = info.filename
            r = re.compile('^'+subpath+'/([^/]*)\.py$')
            x = re.match(r, f)
            if x:
                module_name =  x.group(1)
                if not module_name.startswith('__'):
                    module_selector = "%s.%s" % (dot_module_path, module_name)
                    module = import_module(module_selector)
                    cherrypick_classes_into_module(module, destination, ancestor)
    else:
        # classic case (local development box)
        for dirpath, dirnames, filenames in os.walk(dir_path):
            modules = [f.split('.')[0] for f in filenames if f.endswith('.py') and not f.startswith('__')]
            for module_name in modules:
                dot_module_path = dir_path[len(APP_ROOT)+1:].replace('/', '.')
                module_selector = "%s.%s" % (dot_module_path, module_name)
                module = import_module(module_selector)
                cherrypick_classes_into_module(module, destination, ancestor)
########NEW FILE########
__FILENAME__ = drydrop_handler
# -*- mode: python; coding: utf-8 -*-

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime
import os
import os.path
import sys
import traceback
import logging

APP_ROOT = os.path.normpath(os.path.dirname(__file__))
DRY_ROOT = os.path.join(APP_ROOT, 'drydrop.zip')

LOCAL = os.environ["SERVER_SOFTWARE"].startswith("Development")
APP_ID = os.environ["APPLICATION_ID"]
VER_ID = os.environ["CURRENT_VERSION_ID"]

DEFAULT_CONFIG_SOURCE = """
handlers:
- url: '/'
  static_files: 'index.html index.htm readme.txt readme.markdown readme.md'
  upload: '.*'
- url: '/'
  static_dir: '/'
"""

def routing(m):
  # Routes from http://routes.groovie.org/
  # see the full documentaiton at http://routes.groovie.org/docs/
  # The priority is based upon order of creation: first created -> highest priority.
  
  # Connect the root of your app "http://yourapp.appspot.com/" to a controller/action
  # m.connect('home', '', controller='blog', action='index')
  # use in your application with url_for('home')
  
  # Named Routes
  # Routes can be named for easier use in your controllers/views
  # m.connect( 'history' , 'archives/by_eon/:century', controller='archives', action='show')
  # 
  # use with url_for('history', '1800') 
  # will route to ArchivesController.show() with self.params['century'] equal to '1800'
  
  # Typical route example.
  # m.connect('archives/:year/:month/:day', controller='archives', action='show')
  # 
  # routes urls like archives/2008/12/10 to
  # ArchivesController.show() with self.params['year'], self.params['month'], self.params['day'] available
  # 
  # use in your aplication views/controllers with url_for(controller='archives', year='2008', month='12', day='10')
  
  
  # Connect entire RESTful Resource routing with mapping
  # m.resource('message','messages') 
  # will be a shortcut for the following pattern of routes:
  # GET    /messages         -> MessagesController.index()          -> url_for('messages')
  # POST   /messages         -> MessagesController.create()         -> url_for('messages')
  # GET    /messages/new     -> MessagesController.new()            -> url_for('new_message')
  # PUT    /messages/1       -> MessagesController.update(id)       -> url_for('message', id=1)
  # DELETE /messages/1       -> MessagesController.delete(id)       -> url_for('message', id=1)
  # GET    /messages/1       -> MessagesController.show(id)         -> url_for('message', id=1)
  # GET    /messages/1;edit  -> MessagesController.edit(id)         -> url_for('edit_message', id=1)
  #
  # see http://routes.groovie.org/class-routes.base.Mapper.html#resource for all options
  
  m.connect('/drydrop-static/*path', controller="static", action="static")
  m.connect('/admin/:action', controller="admin", action="index")
  m.connect('/hook/:action', controller="hook", action="index")
  m.connect('/', controller="welcome", action="index")
  
  # returns the mapper object. Do not remove.
  return m
  
def ReadDataFile(path, vfs):
    import httplib
    import logging
    # try:
    resource = vfs.get_resource(path)
    # except:
    #     logging.error('Unable to retrieve file "%s"', path)
    #     return httplib.NOT_FOUND, ""
        
    if resource.content is None:
        logging.warning('Missing file "%s"', path)
        return httplib.NOT_FOUND, "", datetime.now()
        
    # Return the content and timestamp
    return httplib.OK, resource.content, resource.created_on

class AppHandler(webapp.RequestHandler):
    
    def __init__(self):
        import glob
        import os.path
        import routes

        # create a new routing mapper
        self.mapper = routing(routes.Mapper())

        # routes needs to know all the controllers to generate the regular expressions.
        # controllers = []
        # for file in glob.glob(os.path.join(DRY_ROOT, 'app', 'controllers', '*.py')):
        #     name = os.path.basename(file).replace('.py', '')
        #     if not name.startswith('_'):
        #         controllers.append(name)
        # self.mapper.create_regs(controllers)
    
    def get_base_controller(self):
        from drydrop.app.core.controller import BaseController
        return BaseController(self.request, self.response, self)
    
    def meta_dispatch(self, root, config_source, request_path, request_headers, request_environ):
        from drydrop.app.meta.server import ParseAppConfig, MatcherDispatcher, RewriteResponse, cStringIO
        import string
        import logging
        
        HTTP_date = ''

        logging.debug("Meta: dispatching %s", request_path)
        
        login_url = "/login" # TODO
        config, matcher = ParseAppConfig(self.settings.source, config_source, self.vfs, static_caching=True)
        dispatcher = MatcherDispatcher(login_url, [matcher])

        infile = cStringIO.StringIO()
        outfile = cStringIO.StringIO()
        dispatcher.Dispatch(request_path,
                          None,
                          request_headers,
                          infile,
                          outfile,
                          base_env_dict=request_environ)

        outfile.flush()
        outfile.seek(0)

        status_code, status_message, header_list, body = RewriteResponse(outfile)
        logging.debug("Meta: result: %s %s %s", status_code, status_message, header_list)
        
        if status_code == 404:
            return False
        elif request_path == "/404.html":
            # fixes status for customized not found page
            logging.debug("Page's /404.html, so i'm changing status code")
            status_code = 404

        self.response.clear()
        for k in self.response.headers.keys():
            del self.response.headers[k]
        for h in header_list:
            parts = h.split(':')
            header_name = parts.pop(0)
            header_value = string.join(parts, ':')
            self.response.headers.add_header(header_name, header_value)
            
            # Save the Last-Modified header
            if header_name == 'Last-Modified':
            	HTTP_date = header_value

        # Use the If-Modified-Since header...
        if 'If-Modified-Since' in request_headers:
        	try:
        		format = '%a, %d %b %Y %H:%M:%S GMT'
        		request_date = datetime.strptime(request_headers['If-Modified-Since'].strip(), format)
        		response_date = datetime.strptime(HTTP_date.strip(), format)
        		if request_date >= response_date:
        			# Return 304 (Not Modified)
        			self.response.set_status(304, 'Not Modified')
        			return True
        	except ValueError:
        		pass 

        # If the request doesn't have an extension, return text/html
        basename, extension = os.path.splitext(request_path)
        if not extension:
          self.response.headers['Content-Type'] = "text/html"

        self.response.set_status(status_code, status_message)
        self.response.out.write(body)
        return True
        
    def system_dispatch(self):
        import logging
        import drydrop.app as app
        import datetime
        from drydrop.lib.utils import import_module
        from drydrop.app.core.appceptions import PageException

        # match internal route
        self.mapper.environ = self.request.environ
        controller = self.mapper.match(self.request.path)
        if controller == None:
            return False

        logging.debug("System: dispatching %s to %s", self.request.path, controller)

        # find the controller class
        action = controller['action']
        name = controller['controller']
        mod = import_module('drydrop.app.controllers.%s' % name)
        klass = "%sController" % name.capitalize()
        controller_class = mod.__dict__[klass]

        # add the route information as request parameters
        for param, value in controller.iteritems():
            self.request.GET[param] = value

        # instantiate controller
        controller_instance = controller_class(self.request, self.response, self)

        # get controller's methods
        before_method = controller_instance.__getattribute__('before_action')
        action_method = controller_instance.__getattribute__(action)
        after_method = controller_instance.__getattribute__('after_action')

        # see http://code.google.com/p/googleappengine/issues/detail?id=732
        self.response.headers['Cache-Control'] = "no-cache"
        expires = datetime.datetime.today() + datetime.timedelta(0, -1)
        self.response.headers['Expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # call action methods
        try:
            before_result = before_method()
            if before_result:
                return
            
            action_result = action_method()
            if action_result:
                return
        
            after_result = after_method()
            if after_result:
                return
        except PageException:
            pass 
            
    def load_or_init_settings(self):
        from drydrop.app.models import Settings
        
        # fetch settings
        settings = Settings.all().filter("domain =", os.environ['SERVER_NAME']).fetch(1)
        if len(settings)==0:
            s = Settings()
            s.source = "http://github.com/darwin/drydrop/raw/master/tutorial"
            s.config = "site.yaml"
            s.domain = os.environ['SERVER_NAME']
            s.put()
            settings = [s]
        self.settings = settings[0]
    
    def init_vfs(self):
        from drydrop.app.core.vfs import LocalVFS, GAEVFS
        if self.settings.source.startswith('/'):
            vfs_class = LocalVFS
        else:
            vfs_class = GAEVFS
        self.vfs = vfs_class(self.settings)
    
    def read_config_source_or_provide_default_one(self):
        config_source = None
        if self.settings.config:
            try:
                config_source = self.vfs.get_resource(self.settings.config).content
            except:
                pass
        if config_source is not None:
            config_source = config_source.decode('utf-8')
        else:
            config_source = DEFAULT_CONFIG_SOURCE
        return config_source
    
    def post(self, *args, **kvargs):
        if self.request.POST.has_key('_method'):
            if self.request.POST['_method'] == 'put':
                self.request.environ['REQUEST_METHOD'] = 'PUT'
            elif self.request.POST['_method'] == 'delete':
                self.request.environ['REQUEST_METHOD'] = 'DELETE'

        self.route(*args, **kvargs)

    def get(self, *args, **kvargs):
        self.route(*args, **kvargs)

    def put(self, *args, **kvargs):
        self.route(*args, **kvargs)

    def delete(self, *args, **kvargs):
        self.route(*args, **kvargs)

    def route(self):
        from drydrop.app.core.appceptions import PageError

        try:
            # load self.settings
            self.load_or_init_settings()

            # init self.vfs
            self.init_vfs()

            # read site.yaml
            config_source = self.read_config_source_or_provide_default_one()

            # perform dispatch on meta server and finish if response was successfull
            dispatched = self.meta_dispatch(self.settings.source, config_source, self.request.path, self.request.headers, self.request.environ)

            # perform system dispatch (/admin section, welcome page, etc.)
            if not dispatched: 
                res = self.system_dispatch()
                if res == False:
                    # prepare 404 response
                    # TODO: fake headers and environ
                    dispatched404 = self.meta_dispatch(self.settings.source, config_source, "/404.html", self.request.headers, self.request.environ)
                    if not dispatched404:
                        # need to dispatch our stock 404 response
                        base_controller = self.get_base_controller()
                        try:
                            base_controller.notfound(404, 'File "%s" Not Found' % self.request.path)        
                        except PageError:
                            pass
        
        except Exception, e:
            # need to dispatch error response
            base_controller = self.get_base_controller()
            base_controller.error(404, 'Unable to process the page<br/>%s' % e)


class Application(object):

    def __call__(self, environ, start_response):
        import logging
        import sys

        request = webapp.Request(environ)
        response = webapp.Response()
        Application.active_instance = self

        handler = AppHandler()
        handler.initialize(request, response)

        groups = []
        try:
            method = environ['REQUEST_METHOD']
            if method == 'GET':
                handler.get(*groups)
            elif method == 'POST':
                handler.post(*groups)
            elif method == 'HEAD':
                handler.head(*groups)
            elif method == 'OPTIONS':
                handler.options(*groups)
            elif method == 'PUT':
                handler.put(*groups)
            elif method == 'DELETE':
                handler.delete(*groups)
            elif method == 'TRACE':
                handler.trace(*groups)
            else:
                handler.error(501)
        except:
            logging.exception(sys.exc_info()[1])
            import sys
            from drydrop.lib.nice_traceback import show_error
            show_error(handler, 500)

        handler.response.wsgi_write(start_response)
        return ['']

def main():
    import sys
    import logging
    from google.appengine.api import users

    if LOCAL:
        from google.appengine.tools.dev_appserver import FakeFile
        FakeFile.SetAllowedPaths('/', [])
        sys.meta_path = [] # disables python sandbox in local version
    
    # GENERATED: here we will setup import paths for baked version !!!
    # the domain: os.environ['SERVER_NAME']
    from google.appengine.api import urlfetch
    if not urlfetch.__dict__.has_key("old_fetch"):
        urlfetch.old_fetch = urlfetch.fetch
        def new_fetch(*arguments, **keywords):
            import logging
            from google.appengine.api import urlfetch
            logging.info("Fetching: %s", arguments[0])
            return urlfetch.old_fetch(*arguments, **keywords)
        urlfetch.fetch = new_fetch

    logging.getLogger().setLevel(logging.DEBUG)
    application = Application()
    try:
        from firepython.middleware import FirePythonWSGI
        if LOCAL or users.is_current_user_admin():
            application = FirePythonWSGI(application)
    except:
        pass
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = bccache
# -*- coding: utf-8 -*-
"""
    jinja2.bccache
    ~~~~~~~~~~~~~~

    This module implements the bytecode cache system Jinja is optionally
    using.  This is useful if you have very complex template situations and
    the compiliation of all those templates slow down your application too
    much.

    Situations where this is useful are often forking web applications that
    are initialized on the first request.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
from os import path, listdir
import marshal
import tempfile
import cPickle as pickle
import fnmatch
from cStringIO import StringIO
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1
from jinja2.utils import open_if_exists


bc_version = 1
bc_magic = 'j2' + pickle.dumps(bc_version, 2)


class Bucket(object):
    """Buckets are used to store the bytecode for one template.  It's created
    and initialized by the bytecode cache and passed to the loading functions.

    The buckets get an internal checksum from the cache assigned and use this
    to automatically reject outdated cache material.  Individual bytecode
    cache subclasses don't have to care about cache invalidation.
    """

    def __init__(self, environment, key, checksum):
        self.environment = environment
        self.key = key
        self.checksum = checksum
        self.reset()

    def reset(self):
        """Resets the bucket (unloads the bytecode)."""
        self.code = None

    def load_bytecode(self, f):
        """Loads bytecode from a file or file like object."""
        # make sure the magic header is correct
        magic = f.read(len(bc_magic))
        if magic != bc_magic:
            self.reset()
            return
        # the source code of the file changed, we need to reload
        checksum = pickle.load(f)
        if self.checksum != checksum:
            self.reset()
            return
        # now load the code.  Because marshal is not able to load
        # from arbitrary streams we have to work around that
        if isinstance(f, file):
            self.code = marshal.load(f)
        else:
            self.code = marshal.loads(f.read())

    def write_bytecode(self, f):
        """Dump the bytecode into the file or file like object passed."""
        if self.code is None:
            raise TypeError('can\'t write empty bucket')
        f.write(bc_magic)
        pickle.dump(self.checksum, f, 2)
        if isinstance(f, file):
            marshal.dump(self.code, f)
        else:
            f.write(marshal.dumps(self.code))

    def bytecode_from_string(self, string):
        """Load bytecode from a string."""
        self.load_bytecode(StringIO(string))

    def bytecode_to_string(self):
        """Return the bytecode as string."""
        out = StringIO()
        self.write_bytecode(out)
        return out.getvalue()


class BytecodeCache(object):
    """To implement your own bytecode cache you have to subclass this class
    and override :meth:`load_bytecode` and :meth:`dump_bytecode`.  Both of
    these methods are passed a :class:`~jinja2.bccache.Bucket`.

    A very basic bytecode cache that saves the bytecode on the file system::

        from os import path

        class MyCache(BytecodeCache):

            def __init__(self, directory):
                self.directory = directory

            def load_bytecode(self, bucket):
                filename = path.join(self.directory, bucket.key)
                if path.exists(filename):
                    with file(filename, 'rb') as f:
                        bucket.load_bytecode(f)

            def dump_bytecode(self, bucket):
                filename = path.join(self.directory, bucket.key)
                with file(filename, 'wb') as f:
                    bucket.write_bytecode(f)

    A more advanced version of a filesystem based bytecode cache is part of
    Jinja2.
    """

    def load_bytecode(self, bucket):
        """Subclasses have to override this method to load bytecode into a
        bucket.  If they are not able to find code in the cache for the
        bucket, it must not do anything.
        """
        raise NotImplementedError()

    def dump_bytecode(self, bucket):
        """Subclasses have to override this method to write the bytecode
        from a bucket back to the cache.  If it unable to do so it must not
        fail silently but raise an exception.
        """
        raise NotImplementedError()

    def clear(self):
        """Clears the cache.  This method is not used by Jinja2 but should be
        implemented to allow applications to clear the bytecode cache used
        by a particular environment.
        """

    def get_cache_key(self, name, filename=None):
        """Returns the unique hash key for this template name."""
        hash = sha1(name.encode('utf-8'))
        if filename is not None:
            if isinstance(filename, unicode):
                filename = filename.encode('utf-8')
            hash.update('|' + filename)
        return hash.hexdigest()

    def get_source_checksum(self, source):
        """Returns a checksum for the source."""
        return sha1(source.encode('utf-8')).hexdigest()

    def get_bucket(self, environment, name, filename, source):
        """Return a cache bucket for the given template.  All arguments are
        mandatory but filename may be `None`.
        """
        key = self.get_cache_key(name, filename)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        self.load_bytecode(bucket)
        return bucket

    def set_bucket(self, bucket):
        """Put the bucket into the cache."""
        self.dump_bytecode(bucket)


class FileSystemBytecodeCache(BytecodeCache):
    """A bytecode cache that stores bytecode on the filesystem.  It accepts
    two arguments: The directory where the cache items are stored and a
    pattern string that is used to build the filename.

    If no directory is specified the system temporary items folder is used.

    The pattern can be used to have multiple separate caches operate on the
    same directory.  The default pattern is ``'__jinja2_%s.cache'``.  ``%s``
    is replaced with the cache key.

    >>> bcc = FileSystemBytecodeCache('/tmp/jinja_cache', '%s.cache')

    This bytecode cache supports clearing of the cache using the clear method.
    """

    def __init__(self, directory=None, pattern='__jinja2_%s.cache'):
        if directory is None:
            directory = tempfile.gettempdir()
        self.directory = directory
        self.pattern = pattern

    def _get_cache_filename(self, bucket):
        return path.join(self.directory, self.pattern % bucket.key)

    def load_bytecode(self, bucket):
        f = open_if_exists(self._get_cache_filename(bucket), 'rb')
        if f is not None:
            try:
                bucket.load_bytecode(f)
            finally:
                f.close()

    def dump_bytecode(self, bucket):
        f = file(self._get_cache_filename(bucket), 'wb')
        try:
            bucket.write_bytecode(f)
        finally:
            f.close()

    def clear(self):
        # imported lazily here because google app-engine doesn't support
        # write access on the file system and the function does not exist
        # normally.
        from os import remove
        files = fnmatch.filter(listdir(self.directory), self.pattern % '*')
        for filename in files:
            try:
                remove(path.join(self.directory, filename))
            except OSError:
                pass


class MemcachedBytecodeCache(BytecodeCache):
    """This class implements a bytecode cache that uses a memcache cache for
    storing the information.  It does not enforce a specific memcache library
    (tummy's memcache or cmemcache) but will accept any class that provides
    the minimal interface required.

    Libraries compatible with this class:

    -   `werkzeug <http://werkzeug.pocoo.org/>`_.contrib.cache
    -   `python-memcached <http://www.tummy.com/Community/software/python-memcached/>`_
    -   `cmemcache <http://gijsbert.org/cmemcache/>`_

    (Unfortunately the django cache interface is not compatible because it
    does not support storing binary data, only unicode.  You can however pass
    the underlying cache client to the bytecode cache which is available
    as `django.core.cache.cache._client`.)

    The minimal interface for the client passed to the constructor is this:

    .. class:: MinimalClientInterface

        .. method:: set(key, value[, timeout])

            Stores the bytecode in the cache.  `value` is a string and
            `timeout` the timeout of the key.  If timeout is not provided
            a default timeout or no timeout should be assumed, if it's
            provided it's an integer with the number of seconds the cache
            item should exist.

        .. method:: get(key)

            Returns the value for the cache key.  If the item does not
            exist in the cache the return value must be `None`.

    The other arguments to the constructor are the prefix for all keys that
    is added before the actual cache key and the timeout for the bytecode in
    the cache system.  We recommend a high (or no) timeout.

    This bytecode cache does not support clearing of used items in the cache.
    The clear method is a no-operation function.
    """

    def __init__(self, client, prefix='jinja2/bytecode/', timeout=None):
        self.client = client
        self.prefix = prefix
        self.timeout = timeout

    def load_bytecode(self, bucket):
        code = self.client.get(self.prefix + bucket.key)
        if code is not None:
            bucket.bytecode_from_string(code)

    def dump_bytecode(self, bucket):
        args = (self.prefix + bucket.key, bucket.bytecode_to_string())
        if self.timeout is not None:
            args += (self.timeout,)
        self.client.set(*args)

########NEW FILE########
__FILENAME__ = compiler
# -*- coding: utf-8 -*-
"""
    jinja2.compiler
    ~~~~~~~~~~~~~~~

    Compiles nodes into python code.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
from cStringIO import StringIO
from itertools import chain
from jinja2 import nodes
from jinja2.visitor import NodeVisitor, NodeTransformer
from jinja2.exceptions import TemplateAssertionError
from jinja2.utils import Markup, concat, escape, is_python_keyword


operators = {
    'eq':       '==',
    'ne':       '!=',
    'gt':       '>',
    'gteq':     '>=',
    'lt':       '<',
    'lteq':     '<=',
    'in':       'in',
    'notin':    'not in'
}

try:
    exec '(0 if 0 else 0)'
except SyntaxError:
    have_condexpr = False
else:
    have_condexpr = True


def generate(node, environment, name, filename, stream=None):
    """Generate the python source for a node tree."""
    if not isinstance(node, nodes.Template):
        raise TypeError('Can\'t compile non template nodes')
    generator = CodeGenerator(environment, name, filename, stream)
    generator.visit(node)
    if stream is None:
        return generator.stream.getvalue()


def has_safe_repr(value):
    """Does the node have a safe representation?"""
    if value is None or value is NotImplemented or value is Ellipsis:
        return True
    if isinstance(value, (bool, int, long, float, complex, basestring,
                          xrange, Markup)):
        return True
    if isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            if not has_safe_repr(item):
                return False
        return True
    elif isinstance(value, dict):
        for key, value in value.iteritems():
            if not has_safe_repr(key):
                return False
            if not has_safe_repr(value):
                return False
        return True
    return False


def find_undeclared(nodes, names):
    """Check if the names passed are accessed undeclared.  The return value
    is a set of all the undeclared names from the sequence of names found.
    """
    visitor = UndeclaredNameVisitor(names)
    try:
        for node in nodes:
            visitor.visit(node)
    except VisitorExit:
        pass
    return visitor.undeclared


class Identifiers(object):
    """Tracks the status of identifiers in frames."""

    def __init__(self):
        # variables that are known to be declared (probably from outer
        # frames or because they are special for the frame)
        self.declared = set()

        # undeclared variables from outer scopes
        self.outer_undeclared = set()

        # names that are accessed without being explicitly declared by
        # this one or any of the outer scopes.  Names can appear both in
        # declared and undeclared.
        self.undeclared = set()

        # names that are declared locally
        self.declared_locally = set()

        # names that are declared by parameters
        self.declared_parameter = set()

    def add_special(self, name):
        """Register a special name like `loop`."""
        self.undeclared.discard(name)
        self.declared.add(name)

    def is_declared(self, name, local_only=False):
        """Check if a name is declared in this or an outer scope."""
        if name in self.declared_locally or name in self.declared_parameter:
            return True
        if local_only:
            return False
        return name in self.declared

    def find_shadowed(self, extra=()):
        """Find all the shadowed names.  extra is an iterable of variables
        that may be defined with `add_special` which may occour scoped.
        """
        return (self.declared | self.outer_undeclared) & \
               (self.declared_locally | self.declared_parameter) | \
               set(x for x in extra if self.is_declared(x))


class Frame(object):
    """Holds compile time information for us."""

    def __init__(self, parent=None):
        self.identifiers = Identifiers()

        # a toplevel frame is the root + soft frames such as if conditions.
        self.toplevel = False

        # the root frame is basically just the outermost frame, so no if
        # conditions.  This information is used to optimize inheritance
        # situations.
        self.rootlevel = False

        # in some dynamic inheritance situations the compiler needs to add
        # write tests around output statements.
        self.require_output_check = parent and parent.require_output_check

        # inside some tags we are using a buffer rather than yield statements.
        # this for example affects {% filter %} or {% macro %}.  If a frame
        # is buffered this variable points to the name of the list used as
        # buffer.
        self.buffer = None

        # the name of the block we're in, otherwise None.
        self.block = parent and parent.block or None

        # the parent of this frame
        self.parent = parent

        if parent is not None:
            self.identifiers.declared.update(
                parent.identifiers.declared |
                parent.identifiers.declared_locally |
                parent.identifiers.declared_parameter |
                parent.identifiers.undeclared
            )
            self.identifiers.outer_undeclared.update(
                parent.identifiers.undeclared -
                self.identifiers.declared
            )
            self.buffer = parent.buffer

    def copy(self):
        """Create a copy of the current one."""
        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        rv.identifiers = object.__new__(self.identifiers.__class__)
        rv.identifiers.__dict__.update(self.identifiers.__dict__)
        return rv

    def inspect(self, nodes, hard_scope=False):
        """Walk the node and check for identifiers.  If the scope is hard (eg:
        enforce on a python level) overrides from outer scopes are tracked
        differently.
        """
        visitor = FrameIdentifierVisitor(self.identifiers, hard_scope)
        for node in nodes:
            visitor.visit(node)

    def inner(self):
        """Return an inner frame."""
        return Frame(self)

    def soft(self):
        """Return a soft frame.  A soft frame may not be modified as
        standalone thing as it shares the resources with the frame it
        was created of, but it's not a rootlevel frame any longer.
        """
        rv = self.copy()
        rv.rootlevel = False
        return rv

    __copy__ = copy


class VisitorExit(RuntimeError):
    """Exception used by the `UndeclaredNameVisitor` to signal a stop."""


class DependencyFinderVisitor(NodeVisitor):
    """A visitor that collects filter and test calls."""

    def __init__(self):
        self.filters = set()
        self.tests = set()

    def visit_Filter(self, node):
        self.generic_visit(node)
        self.filters.add(node.name)

    def visit_Test(self, node):
        self.generic_visit(node)
        self.tests.add(node.name)

    def visit_Block(self, node):
        """Stop visiting at blocks."""


class UndeclaredNameVisitor(NodeVisitor):
    """A visitor that checks if a name is accessed without being
    declared.  This is different from the frame visitor as it will
    not stop at closure frames.
    """

    def __init__(self, names):
        self.names = set(names)
        self.undeclared = set()

    def visit_Name(self, node):
        if node.ctx == 'load' and node.name in self.names:
            self.undeclared.add(node.name)
            if self.undeclared == self.names:
                raise VisitorExit()
        else:
            self.names.discard(node.name)

    def visit_Block(self, node):
        """Stop visiting a blocks."""


class FrameIdentifierVisitor(NodeVisitor):
    """A visitor for `Frame.inspect`."""

    def __init__(self, identifiers, hard_scope):
        self.identifiers = identifiers
        self.hard_scope = hard_scope

    def visit_Name(self, node):
        """All assignments to names go through this function."""
        if node.ctx == 'store':
            self.identifiers.declared_locally.add(node.name)
        elif node.ctx == 'param':
            self.identifiers.declared_parameter.add(node.name)
        elif node.ctx == 'load' and not \
             self.identifiers.is_declared(node.name, self.hard_scope):
            self.identifiers.undeclared.add(node.name)

    def visit_Macro(self, node):
        self.identifiers.declared_locally.add(node.name)

    def visit_Import(self, node):
        self.generic_visit(node)
        self.identifiers.declared_locally.add(node.target)

    def visit_FromImport(self, node):
        self.generic_visit(node)
        for name in node.names:
            if isinstance(name, tuple):
                self.identifiers.declared_locally.add(name[1])
            else:
                self.identifiers.declared_locally.add(name)

    def visit_Assign(self, node):
        """Visit assignments in the correct order."""
        self.visit(node.node)
        self.visit(node.target)

    def visit_For(self, node):
        """Visiting stops at for blocks.  However the block sequence
        is visited as part of the outer scope.
        """
        self.visit(node.iter)

    def visit_CallBlock(self, node):
        for child in node.iter_child_nodes(exclude=('body',)):
            self.visit(child)

    def visit_FilterBlock(self, node):
        self.visit(node.filter)

    def visit_Block(self, node):
        """Stop visiting at blocks."""


class CompilerExit(Exception):
    """Raised if the compiler encountered a situation where it just
    doesn't make sense to further process the code.  Any block that
    raises such an exception is not further processed.
    """


class CodeGenerator(NodeVisitor):

    def __init__(self, environment, name, filename, stream=None):
        if stream is None:
            stream = StringIO()
        self.environment = environment
        self.name = name
        self.filename = filename
        self.stream = stream

        # aliases for imports
        self.import_aliases = {}

        # a registry for all blocks.  Because blocks are moved out
        # into the global python scope they are registered here
        self.blocks = {}

        # the number of extends statements so far
        self.extends_so_far = 0

        # some templates have a rootlevel extends.  In this case we
        # can safely assume that we're a child template and do some
        # more optimizations.
        self.has_known_extends = False

        # the current line number
        self.code_lineno = 1

        # registry of all filters and tests (global, not block local)
        self.tests = {}
        self.filters = {}

        # the debug information
        self.debug_info = []
        self._write_debug_info = None

        # the number of new lines before the next write()
        self._new_lines = 0

        # the line number of the last written statement
        self._last_line = 0

        # true if nothing was written so far.
        self._first_write = True

        # used by the `temporary_identifier` method to get new
        # unique, temporary identifier
        self._last_identifier = 0

        # the current indentation
        self._indentation = 0

    # -- Various compilation helpers

    def fail(self, msg, lineno):
        """Fail with a `TemplateAssertionError`."""
        raise TemplateAssertionError(msg, lineno, self.name, self.filename)

    def temporary_identifier(self):
        """Get a new unique identifier."""
        self._last_identifier += 1
        return 't_%d' % self._last_identifier

    def buffer(self, frame):
        """Enable buffering for the frame from that point onwards."""
        frame.buffer = self.temporary_identifier()
        self.writeline('%s = []' % frame.buffer)

    def return_buffer_contents(self, frame):
        """Return the buffer contents of the frame."""
        if self.environment.autoescape:
            self.writeline('return Markup(concat(%s))' % frame.buffer)
        else:
            self.writeline('return concat(%s)' % frame.buffer)

    def indent(self):
        """Indent by one."""
        self._indentation += 1

    def outdent(self, step=1):
        """Outdent by step."""
        self._indentation -= step

    def start_write(self, frame, node=None):
        """Yield or write into the frame buffer."""
        if frame.buffer is None:
            self.writeline('yield ', node)
        else:
            self.writeline('%s.append(' % frame.buffer, node)

    def end_write(self, frame):
        """End the writing process started by `start_write`."""
        if frame.buffer is not None:
            self.write(')')

    def simple_write(self, s, frame, node=None):
        """Simple shortcut for start_write + write + end_write."""
        self.start_write(frame, node)
        self.write(s)
        self.end_write(frame)

    def blockvisit(self, nodes, frame):
        """Visit a list of nodes as block in a frame.  If the current frame
        is no buffer a dummy ``if 0: yield None`` is written automatically
        unless the force_generator parameter is set to False.
        """
        if frame.buffer is None:
            self.writeline('if 0: yield None')
        else:
            self.writeline('pass')
        try:
            for node in nodes:
                self.visit(node, frame)
        except CompilerExit:
            pass

    def write(self, x):
        """Write a string into the output stream."""
        if self._new_lines:
            if not self._first_write:
                self.stream.write('\n' * self._new_lines)
                self.code_lineno += self._new_lines
                if self._write_debug_info is not None:
                    self.debug_info.append((self._write_debug_info,
                                            self.code_lineno))
                    self._write_debug_info = None
            self._first_write = False
            self.stream.write('    ' * self._indentation)
            self._new_lines = 0
        self.stream.write(x)

    def writeline(self, x, node=None, extra=0):
        """Combination of newline and write."""
        self.newline(node, extra)
        self.write(x)

    def newline(self, node=None, extra=0):
        """Add one or more newlines before the next write."""
        self._new_lines = max(self._new_lines, 1 + extra)
        if node is not None and node.lineno != self._last_line:
            self._write_debug_info = node.lineno
            self._last_line = node.lineno

    def signature(self, node, frame, extra_kwargs=None):
        """Writes a function call to the stream for the current node.
        A leading comma is added automatically.  The extra keyword
        arguments may not include python keywords otherwise a syntax
        error could occour.  The extra keyword arguments should be given
        as python dict.
        """
        # if any of the given keyword arguments is a python keyword
        # we have to make sure that no invalid call is created.
        kwarg_workaround = False
        for kwarg in chain((x.key for x in node.kwargs), extra_kwargs or ()):
            if is_python_keyword(kwarg):
                kwarg_workaround = True
                break

        for arg in node.args:
            self.write(', ')
            self.visit(arg, frame)

        if not kwarg_workaround:
            for kwarg in node.kwargs:
                self.write(', ')
                self.visit(kwarg, frame)
            if extra_kwargs is not None:
                for key, value in extra_kwargs.iteritems():
                    self.write(', %s=%s' % (key, value))
        if node.dyn_args:
            self.write(', *')
            self.visit(node.dyn_args, frame)

        if kwarg_workaround:
            if node.dyn_kwargs is not None:
                self.write(', **dict({')
            else:
                self.write(', **{')
            for kwarg in node.kwargs:
                self.write('%r: ' % kwarg.key)
                self.visit(kwarg.value, frame)
                self.write(', ')
            if extra_kwargs is not None:
                for key, value in extra_kwargs.iteritems():
                    self.write('%r: %s, ' % (key, value))
            if node.dyn_kwargs is not None:
                self.write('}, **')
                self.visit(node.dyn_kwargs, frame)
                self.write(')')
            else:
                self.write('}')

        elif node.dyn_kwargs is not None:
            self.write(', **')
            self.visit(node.dyn_kwargs, frame)

    def pull_locals(self, frame):
        """Pull all the references identifiers into the local scope."""
        for name in frame.identifiers.undeclared:
            self.writeline('l_%s = context.resolve(%r)' % (name, name))

    def pull_dependencies(self, nodes):
        """Pull all the dependencies."""
        visitor = DependencyFinderVisitor()
        for node in nodes:
            visitor.visit(node)
        for dependency in 'filters', 'tests':
            mapping = getattr(self, dependency)
            for name in getattr(visitor, dependency):
                if name not in mapping:
                    mapping[name] = self.temporary_identifier()
                self.writeline('%s = environment.%s[%r]' %
                               (mapping[name], dependency, name))

    def push_scope(self, frame, extra_vars=()):
        """This function returns all the shadowed variables in a dict
        in the form name: alias and will write the required assignments
        into the current scope.  No indentation takes place.

        This also predefines locally declared variables from the loop
        body because under some circumstances it may be the case that

        `extra_vars` is passed to `Identifiers.find_shadowed`.
        """
        aliases = {}
        for name in frame.identifiers.find_shadowed(extra_vars):
            aliases[name] = ident = self.temporary_identifier()
            self.writeline('%s = l_%s' % (ident, name))
        to_declare = set()
        for name in frame.identifiers.declared_locally:
            if name not in aliases:
                to_declare.add('l_' + name)
        if to_declare:
            self.writeline(' = '.join(to_declare) + ' = missing')
        return aliases

    def pop_scope(self, aliases, frame):
        """Restore all aliases and delete unused variables."""
        for name, alias in aliases.iteritems():
            self.writeline('l_%s = %s' % (name, alias))
        to_delete = set()
        for name in frame.identifiers.declared_locally:
            if name not in aliases:
                to_delete.add('l_' + name)
        if to_delete:
            self.writeline('del ' + ', '.join(to_delete))

    def function_scoping(self, node, frame, children=None,
                         find_special=True):
        """In Jinja a few statements require the help of anonymous
        functions.  Those are currently macros and call blocks and in
        the future also recursive loops.  As there is currently
        technical limitation that doesn't allow reading and writing a
        variable in a scope where the initial value is coming from an
        outer scope, this function tries to fall back with a common
        error message.  Additionally the frame passed is modified so
        that the argumetns are collected and callers are looked up.

        This will return the modified frame.
        """
        # we have to iterate twice over it, make sure that works
        if children is None:
            children = node.iter_child_nodes()
        children = list(children)
        func_frame = frame.inner()
        func_frame.inspect(children, hard_scope=True)

        # variables that are undeclared (accessed before declaration) and
        # declared locally *and* part of an outside scope raise a template
        # assertion error. Reason: we can't generate reasonable code from
        # it without aliasing all the variables.  XXX: alias them ^^
        overriden_closure_vars = (
            func_frame.identifiers.undeclared &
            func_frame.identifiers.declared &
            (func_frame.identifiers.declared_locally |
             func_frame.identifiers.declared_parameter)
        )
        if overriden_closure_vars:
            self.fail('It\'s not possible to set and access variables '
                      'derived from an outer scope! (affects: %s' %
                      ', '.join(sorted(overriden_closure_vars)), node.lineno)

        # remove variables from a closure from the frame's undeclared
        # identifiers.
        func_frame.identifiers.undeclared -= (
            func_frame.identifiers.undeclared &
            func_frame.identifiers.declared
        )

        # no special variables for this scope, abort early
        if not find_special:
            return func_frame

        func_frame.accesses_kwargs = False
        func_frame.accesses_varargs = False
        func_frame.accesses_caller = False
        func_frame.arguments = args = ['l_' + x.name for x in node.args]

        undeclared = find_undeclared(children, ('caller', 'kwargs', 'varargs'))

        if 'caller' in undeclared:
            func_frame.accesses_caller = True
            func_frame.identifiers.add_special('caller')
            args.append('l_caller')
        if 'kwargs' in undeclared:
            func_frame.accesses_kwargs = True
            func_frame.identifiers.add_special('kwargs')
            args.append('l_kwargs')
        if 'varargs' in undeclared:
            func_frame.accesses_varargs = True
            func_frame.identifiers.add_special('varargs')
            args.append('l_varargs')
        return func_frame

    def macro_body(self, node, frame, children=None):
        """Dump the function def of a macro or call block."""
        frame = self.function_scoping(node, frame, children)
        # macros are delayed, they never require output checks
        frame.require_output_check = False
        args = frame.arguments
        self.writeline('def macro(%s):' % ', '.join(args), node)
        self.indent()
        self.buffer(frame)
        self.pull_locals(frame)
        self.blockvisit(node.body, frame)
        self.return_buffer_contents(frame)
        self.outdent()
        return frame

    def macro_def(self, node, frame):
        """Dump the macro definition for the def created by macro_body."""
        arg_tuple = ', '.join(repr(x.name) for x in node.args)
        name = getattr(node, 'name', None)
        if len(node.args) == 1:
            arg_tuple += ','
        self.write('Macro(environment, macro, %r, (%s), (' %
                   (name, arg_tuple))
        for arg in node.defaults:
            self.visit(arg, frame)
            self.write(', ')
        self.write('), %r, %r, %r)' % (
            bool(frame.accesses_kwargs),
            bool(frame.accesses_varargs),
            bool(frame.accesses_caller)
        ))

    def position(self, node):
        """Return a human readable position for the node."""
        rv = 'line %d' % node.lineno
        if self.name is not None:
            rv += ' in' + repr(self.name)
        return rv

    # -- Statement Visitors

    def visit_Template(self, node, frame=None):
        assert frame is None, 'no root frame allowed'
        from jinja2.runtime import __all__ as exported
        self.writeline('from __future__ import division')
        self.writeline('from jinja2.runtime import ' + ', '.join(exported))

        # do we have an extends tag at all?  If not, we can save some
        # overhead by just not processing any inheritance code.
        have_extends = node.find(nodes.Extends) is not None

        # find all blocks
        for block in node.find_all(nodes.Block):
            if block.name in self.blocks:
                self.fail('block %r defined twice' % block.name, block.lineno)
            self.blocks[block.name] = block

        # find all imports and import them
        for import_ in node.find_all(nodes.ImportedName):
            if import_.importname not in self.import_aliases:
                imp = import_.importname
                self.import_aliases[imp] = alias = self.temporary_identifier()
                if '.' in imp:
                    module, obj = imp.rsplit('.', 1)
                    self.writeline('from %s import %s as %s' %
                                   (module, obj, alias))
                else:
                    self.writeline('import %s as %s' % (imp, alias))

        # add the load name
        self.writeline('name = %r' % self.name)

        # generate the root render function.
        self.writeline('def root(context, environment=environment):', extra=1)

        # process the root
        frame = Frame()
        frame.inspect(node.body)
        frame.toplevel = frame.rootlevel = True
        frame.require_output_check = have_extends and not self.has_known_extends
        self.indent()
        if have_extends:
            self.writeline('parent_template = None')
        if 'self' in find_undeclared(node.body, ('self',)):
            frame.identifiers.add_special('self')
            self.writeline('l_self = TemplateReference(context)')
        self.pull_locals(frame)
        self.pull_dependencies(node.body)
        self.blockvisit(node.body, frame)
        self.outdent()

        # make sure that the parent root is called.
        if have_extends:
            if not self.has_known_extends:
                self.indent()
                self.writeline('if parent_template is not None:')
            self.indent()
            self.writeline('for event in parent_template.'
                           'root_render_func(context):')
            self.indent()
            self.writeline('yield event')
            self.outdent(2 + (not self.has_known_extends))

        # at this point we now have the blocks collected and can visit them too.
        for name, block in self.blocks.iteritems():
            block_frame = Frame()
            block_frame.inspect(block.body)
            block_frame.block = name
            self.writeline('def block_%s(context, environment=environment):'
                           % name, block, 1)
            self.indent()
            undeclared = find_undeclared(block.body, ('self', 'super'))
            if 'self' in undeclared:
                block_frame.identifiers.add_special('self')
                self.writeline('l_self = TemplateReference(context)')
            if 'super' in undeclared:
                block_frame.identifiers.add_special('super')
                self.writeline('l_super = context.super(%r, '
                               'block_%s)' % (name, name))
            self.pull_locals(block_frame)
            self.pull_dependencies(block.body)
            self.blockvisit(block.body, block_frame)
            self.outdent()

        self.writeline('blocks = {%s}' % ', '.join('%r: block_%s' % (x, x)
                                                   for x in self.blocks),
                       extra=1)

        # add a function that returns the debug info
        self.writeline('debug_info = %r' % '&'.join('%s=%s' % x for x
                                                    in self.debug_info))

    def visit_Block(self, node, frame):
        """Call a block and register it for the template."""
        level = 1
        if frame.toplevel:
            # if we know that we are a child template, there is no need to
            # check if we are one
            if self.has_known_extends:
                return
            if self.extends_so_far > 0:
                self.writeline('if parent_template is None:')
                self.indent()
                level += 1
        self.writeline('for event in context.blocks[%r][0](context):' %
                       node.name, node)
        self.indent()
        self.simple_write('event', frame)
        self.outdent(level)

    def visit_Extends(self, node, frame):
        """Calls the extender."""
        if not frame.toplevel:
            self.fail('cannot use extend from a non top-level scope',
                      node.lineno)

        # if the number of extends statements in general is zero so
        # far, we don't have to add a check if something extended
        # the template before this one.
        if self.extends_so_far > 0:

            # if we have a known extends we just add a template runtime
            # error into the generated code.  We could catch that at compile
            # time too, but i welcome it not to confuse users by throwing the
            # same error at different times just "because we can".
            if not self.has_known_extends:
                self.writeline('if parent_template is not None:')
                self.indent()
            self.writeline('raise TemplateRuntimeError(%r)' %
                           'extended multiple times')
            self.outdent()

            # if we have a known extends already we don't need that code here
            # as we know that the template execution will end here.
            if self.has_known_extends:
                raise CompilerExit()

        self.writeline('parent_template = environment.get_template(', node)
        self.visit(node.template, frame)
        self.write(', %r)' % self.name)
        self.writeline('for name, parent_block in parent_template.'
                       'blocks.iteritems():')
        self.indent()
        self.writeline('context.blocks.setdefault(name, []).'
                       'append(parent_block)')
        self.outdent()

        # if this extends statement was in the root level we can take
        # advantage of that information and simplify the generated code
        # in the top level from this point onwards
        if frame.rootlevel:
            self.has_known_extends = True

        # and now we have one more
        self.extends_so_far += 1

    def visit_Include(self, node, frame):
        """Handles includes."""
        if node.with_context:
            self.writeline('template = environment.get_template(', node)
            self.visit(node.template, frame)
            self.write(', %r)' % self.name)
            self.writeline('for event in template.root_render_func('
                           'template.new_context(context.parent, True, '
                           'locals())):')
        else:
            self.writeline('for event in environment.get_template(', node)
            self.visit(node.template, frame)
            self.write(', %r).module._body_stream:' %
                       self.name)
        self.indent()
        self.simple_write('event', frame)
        self.outdent()

    def visit_Import(self, node, frame):
        """Visit regular imports."""
        self.writeline('l_%s = ' % node.target, node)
        if frame.toplevel:
            self.write('context.vars[%r] = ' % node.target)
        self.write('environment.get_template(')
        self.visit(node.template, frame)
        self.write(', %r).' % self.name)
        if node.with_context:
            self.write('make_module(context.parent, True, locals())')
        else:
            self.write('module')
        if frame.toplevel and not node.target.startswith('_'):
            self.writeline('context.exported_vars.discard(%r)' % node.target)

    def visit_FromImport(self, node, frame):
        """Visit named imports."""
        self.newline(node)
        self.write('included_template = environment.get_template(')
        self.visit(node.template, frame)
        self.write(', %r).' % self.name)
        if node.with_context:
            self.write('make_module(context.parent, True)')
        else:
            self.write('module')

        var_names = []
        discarded_names = []
        for name in node.names:
            if isinstance(name, tuple):
                name, alias = name
            else:
                alias = name
            self.writeline('l_%s = getattr(included_template, '
                           '%r, missing)' % (alias, name))
            self.writeline('if l_%s is missing:' % alias)
            self.indent()
            self.writeline('l_%s = environment.undefined(%r %% '
                           'included_template.__name__, '
                           'name=%r)' %
                           (alias, 'the template %%r (imported on %s) does '
                           'not export the requested name %s' % (
                                self.position(node),
                                repr(name)
                           ), name))
            self.outdent()
            if frame.toplevel:
                var_names.append(alias)
                if not alias.startswith('_'):
                    discarded_names.append(alias)

        if var_names:
            if len(var_names) == 1:
                name = var_names[0]
                self.writeline('context.vars[%r] = l_%s' % (name, name))
            else:
                self.writeline('context.vars.update({%s})' % ', '.join(
                    '%r: l_%s' % (name, name) for name in var_names
                ))
        if discarded_names:
            if len(discarded_names) == 1:
                self.writeline('context.exported_vars.discard(%r)' %
                               discarded_names[0])
            else:
                self.writeline('context.exported_vars.difference_'
                               'update((%s))' % ', '.join(map(repr, discarded_names)))

    def visit_For(self, node, frame):
        # when calculating the nodes for the inner frame we have to exclude
        # the iterator contents from it
        children = node.iter_child_nodes(exclude=('iter',))
        if node.recursive:
            loop_frame = self.function_scoping(node, frame, children,
                                               find_special=False)
        else:
            loop_frame = frame.inner()
            loop_frame.inspect(children)

        # try to figure out if we have an extended loop.  An extended loop
        # is necessary if the loop is in recursive mode if the special loop
        # variable is accessed in the body.
        extended_loop = node.recursive or 'loop' in \
                        find_undeclared(node.iter_child_nodes(
                            only=('body',)), ('loop',))

        # if we don't have an recursive loop we have to find the shadowed
        # variables at that point.  Because loops can be nested but the loop
        # variable is a special one we have to enforce aliasing for it.
        if not node.recursive:
            aliases = self.push_scope(loop_frame, ('loop',))

        # otherwise we set up a buffer and add a function def
        else:
            self.writeline('def loop(reciter, loop_render_func):', node)
            self.indent()
            self.buffer(loop_frame)
            aliases = {}

        # make sure the loop variable is a special one and raise a template
        # assertion error if a loop tries to write to loop
        if extended_loop:
            loop_frame.identifiers.add_special('loop')
        for name in node.find_all(nodes.Name):
            if name.ctx == 'store' and name.name == 'loop':
                self.fail('Can\'t assign to special loop variable '
                          'in for-loop target', name.lineno)

        self.pull_locals(loop_frame)
        if node.else_:
            iteration_indicator = self.temporary_identifier()
            self.writeline('%s = 1' % iteration_indicator)

        # Create a fake parent loop if the else or test section of a
        # loop is accessing the special loop variable and no parent loop
        # exists.
        if 'loop' not in aliases and 'loop' in find_undeclared(
           node.iter_child_nodes(only=('else_', 'test')), ('loop',)):
            self.writeline("l_loop = environment.undefined(%r, name='loop')" %
                ("'loop' is undefined. the filter section of a loop as well "
                 "as the else block doesn't have access to the special 'loop'"
                 " variable of the current loop.  Because there is no parent "
                 "loop it's undefined.  Happened in loop on %s" %
                 self.position(node)))

        self.writeline('for ', node)
        self.visit(node.target, loop_frame)
        self.write(extended_loop and ', l_loop in LoopContext(' or ' in ')

        # if we have an extened loop and a node test, we filter in the
        # "outer frame".
        if extended_loop and node.test is not None:
            self.write('(')
            self.visit(node.target, loop_frame)
            self.write(' for ')
            self.visit(node.target, loop_frame)
            self.write(' in ')
            if node.recursive:
                self.write('reciter')
            else:
                self.visit(node.iter, loop_frame)
            self.write(' if (')
            test_frame = loop_frame.copy()
            self.visit(node.test, test_frame)
            self.write('))')

        elif node.recursive:
            self.write('reciter')
        else:
            self.visit(node.iter, loop_frame)

        if node.recursive:
            self.write(', recurse=loop_render_func):')
        else:
            self.write(extended_loop and '):' or ':')

        # tests in not extended loops become a continue
        if not extended_loop and node.test is not None:
            self.indent()
            self.writeline('if not ')
            self.visit(node.test, loop_frame)
            self.write(':')
            self.indent()
            self.writeline('continue')
            self.outdent(2)

        self.indent()
        self.blockvisit(node.body, loop_frame)
        if node.else_:
            self.writeline('%s = 0' % iteration_indicator)
        self.outdent()

        if node.else_:
            self.writeline('if %s:' % iteration_indicator)
            self.indent()
            self.blockvisit(node.else_, loop_frame)
            self.outdent()

        # reset the aliases if there are any.
        self.pop_scope(aliases, loop_frame)

        # if the node was recursive we have to return the buffer contents
        # and start the iteration code
        if node.recursive:
            self.return_buffer_contents(loop_frame)
            self.outdent()
            self.start_write(frame, node)
            self.write('loop(')
            self.visit(node.iter, frame)
            self.write(', loop)')
            self.end_write(frame)

    def visit_If(self, node, frame):
        if_frame = frame.soft()
        self.writeline('if ', node)
        self.visit(node.test, if_frame)
        self.write(':')
        self.indent()
        self.blockvisit(node.body, if_frame)
        self.outdent()
        if node.else_:
            self.writeline('else:')
            self.indent()
            self.blockvisit(node.else_, if_frame)
            self.outdent()

    def visit_Macro(self, node, frame):
        macro_frame = self.macro_body(node, frame)
        self.newline()
        if frame.toplevel:
            if not node.name.startswith('_'):
                self.write('context.exported_vars.add(%r)' % node.name)
            self.writeline('context.vars[%r] = ' % node.name)
        self.write('l_%s = ' % node.name)
        self.macro_def(node, macro_frame)

    def visit_CallBlock(self, node, frame):
        children = node.iter_child_nodes(exclude=('call',))
        call_frame = self.macro_body(node, frame, children)
        self.writeline('caller = ')
        self.macro_def(node, call_frame)
        self.start_write(frame, node)
        self.visit_Call(node.call, call_frame, forward_caller=True)
        self.end_write(frame)

    def visit_FilterBlock(self, node, frame):
        filter_frame = frame.inner()
        filter_frame.inspect(node.iter_child_nodes())
        aliases = self.push_scope(filter_frame)
        self.pull_locals(filter_frame)
        self.buffer(filter_frame)
        self.blockvisit(node.body, filter_frame)
        self.start_write(frame, node)
        self.visit_Filter(node.filter, filter_frame)
        self.end_write(frame)
        self.pop_scope(aliases, filter_frame)

    def visit_ExprStmt(self, node, frame):
        self.newline(node)
        self.visit(node.node, frame)

    def visit_Output(self, node, frame):
        # if we have a known extends statement, we don't output anything
        # if we are in a require_output_check section
        if self.has_known_extends and frame.require_output_check:
            return

        if self.environment.finalize:
            finalize = lambda x: unicode(self.environment.finalize(x))
        else:
            finalize = unicode

        self.newline(node)

        # if we are inside a frame that requires output checking, we do so
        outdent_later = False
        if frame.require_output_check:
            self.writeline('if parent_template is None:')
            self.indent()
            outdent_later = True

        # try to evaluate as many chunks as possible into a static
        # string at compile time.
        body = []
        for child in node.nodes:
            try:
                const = child.as_const()
            except nodes.Impossible:
                body.append(child)
                continue
            try:
                if self.environment.autoescape:
                    if hasattr(const, '__html__'):
                        const = const.__html__()
                    else:
                        const = escape(const)
                const = finalize(const)
            except:
                # if something goes wrong here we evaluate the node
                # at runtime for easier debugging
                body.append(child)
                continue
            if body and isinstance(body[-1], list):
                body[-1].append(const)
            else:
                body.append([const])

        # if we have less than 3 nodes or a buffer we yield or extend/append
        if len(body) < 3 or frame.buffer is not None:
            if frame.buffer is not None:
                # for one item we append, for more we extend
                if len(body) == 1:
                    self.writeline('%s.append(' % frame.buffer)
                else:
                    self.writeline('%s.extend((' % frame.buffer)
                self.indent()
            for item in body:
                if isinstance(item, list):
                    val = repr(concat(item))
                    if frame.buffer is None:
                        self.writeline('yield ' + val)
                    else:
                        self.writeline(val + ', ')
                else:
                    if frame.buffer is None:
                        self.writeline('yield ', item)
                    else:
                        self.newline(item)
                    close = 1
                    if self.environment.autoescape:
                        self.write('escape(')
                    else:
                        self.write('unicode(')
                    if self.environment.finalize is not None:
                        self.write('environment.finalize(')
                        close += 1
                    self.visit(item, frame)
                    self.write(')' * close)
                    if frame.buffer is not None:
                        self.write(', ')
            if frame.buffer is not None:
                # close the open parentheses
                self.outdent()
                self.writeline(len(body) == 1 and ')' or '))')

        # otherwise we create a format string as this is faster in that case
        else:
            format = []
            arguments = []
            for item in body:
                if isinstance(item, list):
                    format.append(concat(item).replace('%', '%%'))
                else:
                    format.append('%s')
                    arguments.append(item)
            self.writeline('yield ')
            self.write(repr(concat(format)) + ' % (')
            idx = -1
            self.indent()
            for argument in arguments:
                self.newline(argument)
                close = 0
                if self.environment.autoescape:
                    self.write('escape(')
                    close += 1
                if self.environment.finalize is not None:
                    self.write('environment.finalize(')
                    close += 1
                self.visit(argument, frame)
                self.write(')' * close + ', ')
            self.outdent()
            self.writeline(')')

        if outdent_later:
            self.outdent()

    def visit_Assign(self, node, frame):
        self.newline(node)
        # toplevel assignments however go into the local namespace and
        # the current template's context.  We create a copy of the frame
        # here and add a set so that the Name visitor can add the assigned
        # names here.
        if frame.toplevel:
            assignment_frame = frame.copy()
            assignment_frame.assigned_names = set()
        else:
            assignment_frame = frame
        self.visit(node.target, assignment_frame)
        self.write(' = ')
        self.visit(node.node, frame)

        # make sure toplevel assignments are added to the context.
        if frame.toplevel:
            public_names = [x for x in assignment_frame.assigned_names
                            if not x.startswith('_')]
            if len(assignment_frame.assigned_names) == 1:
                name = iter(assignment_frame.assigned_names).next()
                self.writeline('context.vars[%r] = l_%s' % (name, name))
            else:
                self.writeline('context.vars.update({')
                for idx, name in enumerate(assignment_frame.assigned_names):
                    if idx:
                        self.write(', ')
                    self.write('%r: l_%s' % (name, name))
                self.write('})')
            if public_names:
                if len(public_names) == 1:
                    self.writeline('context.exported_vars.add(%r)' %
                                   public_names[0])
                else:
                    self.writeline('context.exported_vars.update((%s))' %
                                   ', '.join(map(repr, public_names)))

    # -- Expression Visitors

    def visit_Name(self, node, frame):
        if node.ctx == 'store' and frame.toplevel:
            frame.assigned_names.add(node.name)
        self.write('l_' + node.name)

    def visit_Const(self, node, frame):
        val = node.value
        if isinstance(val, float):
            self.write(str(val))
        else:
            self.write(repr(val))

    def visit_TemplateData(self, node, frame):
        self.write(repr(node.as_const()))

    def visit_Tuple(self, node, frame):
        self.write('(')
        idx = -1
        for idx, item in enumerate(node.items):
            if idx:
                self.write(', ')
            self.visit(item, frame)
        self.write(idx == 0 and ',)' or ')')

    def visit_List(self, node, frame):
        self.write('[')
        for idx, item in enumerate(node.items):
            if idx:
                self.write(', ')
            self.visit(item, frame)
        self.write(']')

    def visit_Dict(self, node, frame):
        self.write('{')
        for idx, item in enumerate(node.items):
            if idx:
                self.write(', ')
            self.visit(item.key, frame)
            self.write(': ')
            self.visit(item.value, frame)
        self.write('}')

    def binop(operator):
        def visitor(self, node, frame):
            self.write('(')
            self.visit(node.left, frame)
            self.write(' %s ' % operator)
            self.visit(node.right, frame)
            self.write(')')
        return visitor

    def uaop(operator):
        def visitor(self, node, frame):
            self.write('(' + operator)
            self.visit(node.node, frame)
            self.write(')')
        return visitor

    visit_Add = binop('+')
    visit_Sub = binop('-')
    visit_Mul = binop('*')
    visit_Div = binop('/')
    visit_FloorDiv = binop('//')
    visit_Pow = binop('**')
    visit_Mod = binop('%')
    visit_And = binop('and')
    visit_Or = binop('or')
    visit_Pos = uaop('+')
    visit_Neg = uaop('-')
    visit_Not = uaop('not ')
    del binop, uaop

    def visit_Concat(self, node, frame):
        self.write('%s((' % (self.environment.autoescape and
                             'markup_join' or 'unicode_join'))
        for arg in node.nodes:
            self.visit(arg, frame)
            self.write(', ')
        self.write('))')

    def visit_Compare(self, node, frame):
        self.visit(node.expr, frame)
        for op in node.ops:
            self.visit(op, frame)

    def visit_Operand(self, node, frame):
        self.write(' %s ' % operators[node.op])
        self.visit(node.expr, frame)

    def visit_Getattr(self, node, frame):
        self.write('environment.getattr(')
        self.visit(node.node, frame)
        self.write(', %r)' % node.attr)

    def visit_Getitem(self, node, frame):
        # slices bypass the environment getitem method.
        if isinstance(node.arg, nodes.Slice):
            self.visit(node.node, frame)
            self.write('[')
            self.visit(node.arg, frame)
            self.write(']')
        else:
            self.write('environment.getitem(')
            self.visit(node.node, frame)
            self.write(', ')
            self.visit(node.arg, frame)
            self.write(')')

    def visit_Slice(self, node, frame):
        if node.start is not None:
            self.visit(node.start, frame)
        self.write(':')
        if node.stop is not None:
            self.visit(node.stop, frame)
        if node.step is not None:
            self.write(':')
            self.visit(node.step, frame)

    def visit_Filter(self, node, frame):
        self.write(self.filters[node.name] + '(')
        func = self.environment.filters.get(node.name)
        if func is None:
            self.fail('no filter named %r' % node.name, node.lineno)
        if getattr(func, 'contextfilter', False):
            self.write('context, ')
        elif getattr(func, 'environmentfilter', False):
            self.write('environment, ')

        # if the filter node is None we are inside a filter block
        # and want to write to the current buffer
        if node.node is not None:
            self.visit(node.node, frame)
        elif self.environment.autoescape:
            self.write('Markup(concat(%s))' % frame.buffer)
        else:
            self.write('concat(%s)' % frame.buffer)
        self.signature(node, frame)
        self.write(')')

    def visit_Test(self, node, frame):
        self.write(self.tests[node.name] + '(')
        if node.name not in self.environment.tests:
            self.fail('no test named %r' % node.name, node.lineno)
        self.visit(node.node, frame)
        self.signature(node, frame)
        self.write(')')

    def visit_CondExpr(self, node, frame):
        def write_expr2():
            if node.expr2 is not None:
                return self.visit(node.expr2, frame)
            self.write('environment.undefined(%r)' % ('the inline if-'
                       'expression on %s evaluated to false and '
                       'no else section was defined.' % self.position(node)))

        if not have_condexpr:
            self.write('((')
            self.visit(node.test, frame)
            self.write(') and (')
            self.visit(node.expr1, frame)
            self.write(',) or (')
            write_expr2()
            self.write(',))[0]')
        else:
            self.write('(')
            self.visit(node.expr1, frame)
            self.write(' if ')
            self.visit(node.test, frame)
            self.write(' else ')
            write_expr2()
            self.write(')')

    def visit_Call(self, node, frame, forward_caller=False):
        if self.environment.sandboxed:
            self.write('environment.call(context, ')
        else:
            self.write('context.call(')
        self.visit(node.node, frame)
        extra_kwargs = forward_caller and {'caller': 'caller'} or None
        self.signature(node, frame, extra_kwargs)
        self.write(')')

    def visit_Keyword(self, node, frame):
        self.write(node.key + '=')
        self.visit(node.value, frame)

    # -- Unused nodes for extensions

    def visit_MarkSafe(self, node, frame):
        self.write('Markup(')
        self.visit(node.expr, frame)
        self.write(')')

    def visit_EnvironmentAttribute(self, node, frame):
        self.write('environment.' + node.name)

    def visit_ExtensionAttribute(self, node, frame):
        self.write('environment.extensions[%r].%s' % (node.identifier, node.name))

    def visit_ImportedName(self, node, frame):
        self.write(self.import_aliases[node.importname])

    def visit_InternalName(self, node, frame):
        self.write(node.name)

    def visit_ContextReference(self, node, frame):
        self.write('context')

    def visit_Continue(self, node, frame):
        self.writeline('continue', node)

    def visit_Break(self, node, frame):
        self.writeline('break', node)

########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-
"""
    jinja.constants
    ~~~~~~~~~~~~~~~

    Various constants.

    :copyright: 2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""


#: list of lorem ipsum words used by the lipsum() helper function
LOREM_IPSUM_WORDS = u'''\
a ac accumsan ad adipiscing aenean aliquam aliquet amet ante aptent arcu at
auctor augue bibendum blandit class commodo condimentum congue consectetuer
consequat conubia convallis cras cubilia cum curabitur curae cursus dapibus
diam dictum dictumst dignissim dis dolor donec dui duis egestas eget eleifend
elementum elit enim erat eros est et etiam eu euismod facilisi facilisis fames
faucibus felis fermentum feugiat fringilla fusce gravida habitant habitasse hac
hendrerit hymenaeos iaculis id imperdiet in inceptos integer interdum ipsum
justo lacinia lacus laoreet lectus leo libero ligula litora lobortis lorem
luctus maecenas magna magnis malesuada massa mattis mauris metus mi molestie
mollis montes morbi mus nam nascetur natoque nec neque netus nibh nisi nisl non
nonummy nostra nulla nullam nunc odio orci ornare parturient pede pellentesque
penatibus per pharetra phasellus placerat platea porta porttitor posuere
potenti praesent pretium primis proin pulvinar purus quam quis quisque rhoncus
ridiculus risus rutrum sagittis sapien scelerisque sed sem semper senectus sit
sociis sociosqu sodales sollicitudin suscipit suspendisse taciti tellus tempor
tempus tincidunt torquent tortor tristique turpis ullamcorper ultrices
ultricies urna ut varius vehicula vel velit venenatis vestibulum vitae vivamus
viverra volutpat vulputate'''


#: a dict of all html entities + apos
HTML_ENTITIES = {
    'AElig': 198,
    'Aacute': 193,
    'Acirc': 194,
    'Agrave': 192,
    'Alpha': 913,
    'Aring': 197,
    'Atilde': 195,
    'Auml': 196,
    'Beta': 914,
    'Ccedil': 199,
    'Chi': 935,
    'Dagger': 8225,
    'Delta': 916,
    'ETH': 208,
    'Eacute': 201,
    'Ecirc': 202,
    'Egrave': 200,
    'Epsilon': 917,
    'Eta': 919,
    'Euml': 203,
    'Gamma': 915,
    'Iacute': 205,
    'Icirc': 206,
    'Igrave': 204,
    'Iota': 921,
    'Iuml': 207,
    'Kappa': 922,
    'Lambda': 923,
    'Mu': 924,
    'Ntilde': 209,
    'Nu': 925,
    'OElig': 338,
    'Oacute': 211,
    'Ocirc': 212,
    'Ograve': 210,
    'Omega': 937,
    'Omicron': 927,
    'Oslash': 216,
    'Otilde': 213,
    'Ouml': 214,
    'Phi': 934,
    'Pi': 928,
    'Prime': 8243,
    'Psi': 936,
    'Rho': 929,
    'Scaron': 352,
    'Sigma': 931,
    'THORN': 222,
    'Tau': 932,
    'Theta': 920,
    'Uacute': 218,
    'Ucirc': 219,
    'Ugrave': 217,
    'Upsilon': 933,
    'Uuml': 220,
    'Xi': 926,
    'Yacute': 221,
    'Yuml': 376,
    'Zeta': 918,
    'aacute': 225,
    'acirc': 226,
    'acute': 180,
    'aelig': 230,
    'agrave': 224,
    'alefsym': 8501,
    'alpha': 945,
    'amp': 38,
    'and': 8743,
    'ang': 8736,
    'apos': 39,
    'aring': 229,
    'asymp': 8776,
    'atilde': 227,
    'auml': 228,
    'bdquo': 8222,
    'beta': 946,
    'brvbar': 166,
    'bull': 8226,
    'cap': 8745,
    'ccedil': 231,
    'cedil': 184,
    'cent': 162,
    'chi': 967,
    'circ': 710,
    'clubs': 9827,
    'cong': 8773,
    'copy': 169,
    'crarr': 8629,
    'cup': 8746,
    'curren': 164,
    'dArr': 8659,
    'dagger': 8224,
    'darr': 8595,
    'deg': 176,
    'delta': 948,
    'diams': 9830,
    'divide': 247,
    'eacute': 233,
    'ecirc': 234,
    'egrave': 232,
    'empty': 8709,
    'emsp': 8195,
    'ensp': 8194,
    'epsilon': 949,
    'equiv': 8801,
    'eta': 951,
    'eth': 240,
    'euml': 235,
    'euro': 8364,
    'exist': 8707,
    'fnof': 402,
    'forall': 8704,
    'frac12': 189,
    'frac14': 188,
    'frac34': 190,
    'frasl': 8260,
    'gamma': 947,
    'ge': 8805,
    'gt': 62,
    'hArr': 8660,
    'harr': 8596,
    'hearts': 9829,
    'hellip': 8230,
    'iacute': 237,
    'icirc': 238,
    'iexcl': 161,
    'igrave': 236,
    'image': 8465,
    'infin': 8734,
    'int': 8747,
    'iota': 953,
    'iquest': 191,
    'isin': 8712,
    'iuml': 239,
    'kappa': 954,
    'lArr': 8656,
    'lambda': 955,
    'lang': 9001,
    'laquo': 171,
    'larr': 8592,
    'lceil': 8968,
    'ldquo': 8220,
    'le': 8804,
    'lfloor': 8970,
    'lowast': 8727,
    'loz': 9674,
    'lrm': 8206,
    'lsaquo': 8249,
    'lsquo': 8216,
    'lt': 60,
    'macr': 175,
    'mdash': 8212,
    'micro': 181,
    'middot': 183,
    'minus': 8722,
    'mu': 956,
    'nabla': 8711,
    'nbsp': 160,
    'ndash': 8211,
    'ne': 8800,
    'ni': 8715,
    'not': 172,
    'notin': 8713,
    'nsub': 8836,
    'ntilde': 241,
    'nu': 957,
    'oacute': 243,
    'ocirc': 244,
    'oelig': 339,
    'ograve': 242,
    'oline': 8254,
    'omega': 969,
    'omicron': 959,
    'oplus': 8853,
    'or': 8744,
    'ordf': 170,
    'ordm': 186,
    'oslash': 248,
    'otilde': 245,
    'otimes': 8855,
    'ouml': 246,
    'para': 182,
    'part': 8706,
    'permil': 8240,
    'perp': 8869,
    'phi': 966,
    'pi': 960,
    'piv': 982,
    'plusmn': 177,
    'pound': 163,
    'prime': 8242,
    'prod': 8719,
    'prop': 8733,
    'psi': 968,
    'quot': 34,
    'rArr': 8658,
    'radic': 8730,
    'rang': 9002,
    'raquo': 187,
    'rarr': 8594,
    'rceil': 8969,
    'rdquo': 8221,
    'real': 8476,
    'reg': 174,
    'rfloor': 8971,
    'rho': 961,
    'rlm': 8207,
    'rsaquo': 8250,
    'rsquo': 8217,
    'sbquo': 8218,
    'scaron': 353,
    'sdot': 8901,
    'sect': 167,
    'shy': 173,
    'sigma': 963,
    'sigmaf': 962,
    'sim': 8764,
    'spades': 9824,
    'sub': 8834,
    'sube': 8838,
    'sum': 8721,
    'sup': 8835,
    'sup1': 185,
    'sup2': 178,
    'sup3': 179,
    'supe': 8839,
    'szlig': 223,
    'tau': 964,
    'there4': 8756,
    'theta': 952,
    'thetasym': 977,
    'thinsp': 8201,
    'thorn': 254,
    'tilde': 732,
    'times': 215,
    'trade': 8482,
    'uArr': 8657,
    'uacute': 250,
    'uarr': 8593,
    'ucirc': 251,
    'ugrave': 249,
    'uml': 168,
    'upsih': 978,
    'upsilon': 965,
    'uuml': 252,
    'weierp': 8472,
    'xi': 958,
    'yacute': 253,
    'yen': 165,
    'yuml': 255,
    'zeta': 950,
    'zwj': 8205,
    'zwnj': 8204
}

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -*-
"""
    jinja2.debug
    ~~~~~~~~~~~~

    Implements the debug interface for Jinja.  This module does some pretty
    ugly stuff with the Python traceback system in order to achieve tracebacks
    with correct line numbers, locals and contents.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
import sys
from jinja2.utils import CodeType


def translate_exception(exc_info):
    """If passed an exc_info it will automatically rewrite the exceptions
    all the way down to the correct line numbers and frames.
    """
    result_tb = prev_tb = None
    initial_tb = tb = exc_info[2].tb_next

    while tb is not None:
        template = tb.tb_frame.f_globals.get('__jinja_template__')
        if template is not None:
            lineno = template.get_corresponding_lineno(tb.tb_lineno)
            tb = fake_exc_info(exc_info[:2] + (tb,), template.filename,
                               lineno, prev_tb)[2]
        if result_tb is None:
            result_tb = tb
        prev_tb = tb
        tb = tb.tb_next

    return exc_info[:2] + (result_tb or initial_tb,)


def fake_exc_info(exc_info, filename, lineno, tb_back=None):
    """Helper for `translate_exception`."""
    exc_type, exc_value, tb = exc_info

    # figure the real context out
    real_locals = tb.tb_frame.f_locals.copy()
    ctx = real_locals.get('context')
    if ctx:
        locals = ctx.get_all()
    else:
        locals = {}
    for name, value in real_locals.iteritems():
        if name.startswith('l_'):
            locals[name[2:]] = value

    # if there is a local called __jinja_exception__, we get
    # rid of it to not break the debug functionality.
    locals.pop('__jinja_exception__', None)

    # assamble fake globals we need
    globals = {
        '__name__':             filename,
        '__file__':             filename,
        '__jinja_exception__':  exc_info[:2]
    }

    # and fake the exception
    code = compile('\n' * (lineno - 1) + 'raise __jinja_exception__[0], ' +
                   '__jinja_exception__[1]', filename, 'exec')

    # if it's possible, change the name of the code.  This won't work
    # on some python environments such as google appengine
    try:
        function = tb.tb_frame.f_code.co_name
        if function == 'root':
            location = 'top-level template code'
        elif function.startswith('block_'):
            location = 'block "%s"' % function[6:]
        else:
            location = 'template'
        code = CodeType(0, code.co_nlocals, code.co_stacksize,
                        code.co_flags, code.co_code, code.co_consts,
                        code.co_names, code.co_varnames, filename,
                        location, code.co_firstlineno,
                        code.co_lnotab, (), ())
    except:
        pass

    # execute the code and catch the new traceback
    try:
        exec code in globals, locals
    except:
        exc_info = sys.exc_info()
        new_tb = exc_info[2].tb_next

    # now we can patch the exc info accordingly
    if tb_set_next is not None:
        if tb_back is not None:
            tb_set_next(tb_back, new_tb)
        if tb is not None:
            tb_set_next(new_tb, tb.tb_next)

    # return without this frame
    return exc_info[:2] + (new_tb,)


def _init_ugly_crap():
    """This function implements a few ugly things so that we can patch the
    traceback objects.  The function returned allows resetting `tb_next` on
    any python traceback object.
    """
    import ctypes
    from types import TracebackType

    # figure out side of _Py_ssize_t
    if hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
        _Py_ssize_t = ctypes.c_int64
    else:
        _Py_ssize_t = ctypes.c_int

    # regular python
    class _PyObject(ctypes.Structure):
        pass
    _PyObject._fields_ = [
        ('ob_refcnt', _Py_ssize_t),
        ('ob_type', ctypes.POINTER(_PyObject))
    ]

    # python with trace
    if object.__basicsize__ != ctypes.sizeof(_PyObject):
        class _PyObject(ctypes.Structure):
            pass
        _PyObject._fields_ = [
            ('_ob_next', ctypes.POINTER(_PyObject)),
            ('_ob_prev', ctypes.POINTER(_PyObject)),
            ('ob_refcnt', _Py_ssize_t),
            ('ob_type', ctypes.POINTER(_PyObject))
        ]

    class _Traceback(_PyObject):
        pass
    _Traceback._fields_ = [
        ('tb_next', ctypes.POINTER(_Traceback)),
        ('tb_frame', ctypes.POINTER(_PyObject)),
        ('tb_lasti', ctypes.c_int),
        ('tb_lineno', ctypes.c_int)
    ]

    def tb_set_next(tb, next):
        """Set the tb_next attribute of a traceback object."""
        if not (isinstance(tb, TracebackType) and
                (next is None or isinstance(next, TracebackType))):
            raise TypeError('tb_set_next arguments must be traceback objects')
        obj = _Traceback.from_address(id(tb))
        if tb.tb_next is not None:
            old = _Traceback.from_address(id(tb.tb_next))
            old.ob_refcnt -= 1
        if next is None:
            obj.tb_next = ctypes.POINTER(_Traceback)()
        else:
            next = _Traceback.from_address(id(next))
            next.ob_refcnt += 1
            obj.tb_next = ctypes.pointer(next)

    return tb_set_next


# try to get a tb_set_next implementation
try:
    from jinja2._speedups import tb_set_next
except ImportError:
    try:
        tb_set_next = _init_ugly_crap()
    except:
        tb_set_next = None
del _init_ugly_crap

########NEW FILE########
__FILENAME__ = defaults
# -*- coding: utf-8 -*-
"""
    jinja2.defaults
    ~~~~~~~~~~~~~~~

    Jinja default filters and tags.

    :copyright: 2007-2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from jinja2.utils import generate_lorem_ipsum, Cycler, Joiner


# defaults for the parser / lexer
BLOCK_START_STRING = '{%'
BLOCK_END_STRING = '%}'
VARIABLE_START_STRING = '{{'
VARIABLE_END_STRING = '}}'
COMMENT_START_STRING = '{#'
COMMENT_END_STRING = '#}'
LINE_STATEMENT_PREFIX = None
TRIM_BLOCKS = False
NEWLINE_SEQUENCE = '\n'


# default filters, tests and namespace
from jinja2.filters import FILTERS as DEFAULT_FILTERS
from jinja2.tests import TESTS as DEFAULT_TESTS
DEFAULT_NAMESPACE = {
    'range':        xrange,
    'dict':         lambda **kw: kw,
    'lipsum':       generate_lorem_ipsum,
    'cycler':       Cycler,
    'joiner':       Joiner
}


# export all constants
__all__ = tuple(x for x in locals() if x.isupper())

########NEW FILE########
__FILENAME__ = environment
# -*- coding: utf-8 -*-
"""
    jinja2.environment
    ~~~~~~~~~~~~~~~~~~

    Provides a class that holds runtime and parsing time options.

    :copyright: 2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
from jinja2 import nodes
from jinja2.defaults import *
from jinja2.lexer import get_lexer, TokenStream
from jinja2.parser import Parser
from jinja2.optimizer import optimize
from jinja2.compiler import generate
from jinja2.runtime import Undefined, Context
from jinja2.exceptions import TemplateSyntaxError
from jinja2.utils import import_string, LRUCache, Markup, missing, \
     concat, consume


# for direct template usage we have up to ten living environments
_spontaneous_environments = LRUCache(10)


def get_spontaneous_environment(*args):
    """Return a new spontaneous environment.  A spontaneous environment is an
    unnamed and unaccessible (in theory) environment that is used for
    templates generated from a string and not from the file system.
    """
    try:
        env = _spontaneous_environments.get(args)
    except TypeError:
        return Environment(*args)
    if env is not None:
        return env
    _spontaneous_environments[args] = env = Environment(*args)
    env.shared = True
    return env


def create_cache(size):
    """Return the cache class for the given size."""
    if size == 0:
        return None
    if size < 0:
        return {}
    return LRUCache(size)


def copy_cache(cache):
    """Create an empty copy of the given cache."""
    if cache is None:
        return Noe
    elif type(cache) is dict:
        return {}
    return LRUCache(cache.capacity)


def load_extensions(environment, extensions):
    """Load the extensions from the list and bind it to the environment.
    Returns a dict of instanciated environments.
    """
    result = {}
    for extension in extensions:
        if isinstance(extension, basestring):
            extension = import_string(extension)
        result[extension.identifier] = extension(environment)
    return result


def _environment_sanity_check(environment):
    """Perform a sanity check on the environment."""
    assert issubclass(environment.undefined, Undefined), 'undefined must ' \
           'be a subclass of undefined because filters depend on it.'
    assert environment.block_start_string != \
           environment.variable_start_string != \
           environment.comment_start_string, 'block, variable and comment ' \
           'start strings must be different'
    assert environment.newline_sequence in ('\r', '\r\n', '\n'), \
           'newline_sequence set to unknown line ending string.'
    return environment


class Environment(object):
    r"""The core component of Jinja is the `Environment`.  It contains
    important shared variables like configuration, filters, tests,
    globals and others.  Instances of this class may be modified if
    they are not shared and if no template was loaded so far.
    Modifications on environments after the first template was loaded
    will lead to surprising effects and undefined behavior.

    Here the possible initialization parameters:

        `block_start_string`
            The string marking the begin of a block.  Defaults to ``'{%'``.

        `block_end_string`
            The string marking the end of a block.  Defaults to ``'%}'``.

        `variable_start_string`
            The string marking the begin of a print statement.
            Defaults to ``'{{'``.

        `variable_end_string`
            The string marking the end of a print statement.  Defaults to
            ``'}}'``.

        `comment_start_string`
            The string marking the begin of a comment.  Defaults to ``'{#'``.

        `comment_end_string`
            The string marking the end of a comment.  Defaults to ``'#}'``.

        `line_statement_prefix`
            If given and a string, this will be used as prefix for line based
            statements.  See also :ref:`line-statements`.

        `trim_blocks`
            If this is set to ``True`` the first newline after a block is
            removed (block, not variable tag!).  Defaults to `False`.

        `newline_sequence`
            The sequence that starts a newline.  Must be one of ``'\r'``,
            ``'\n'`` or ``'\r\n'``.  The default is ``'\n'`` which is a
            useful default for Linux and OS X systems as well as web
            applications.

        `extensions`
            List of Jinja extensions to use.  This can either be import paths
            as strings or extension classes.  For more information have a
            look at :ref:`the extensions documentation <jinja-extensions>`.

        `optimized`
            should the optimizer be enabled?  Default is `True`.

        `undefined`
            :class:`Undefined` or a subclass of it that is used to represent
            undefined values in the template.

        `finalize`
            A callable that finalizes the variable.  Per default no finalizing
            is applied.

        `autoescape`
            If set to true the XML/HTML autoescaping feature is enabled.
            For more details about auto escaping see
            :class:`~jinja2.utils.Markup`.

        `loader`
            The template loader for this environment.

        `cache_size`
            The size of the cache.  Per default this is ``50`` which means
            that if more than 50 templates are loaded the loader will clean
            out the least recently used template.  If the cache size is set to
            ``0`` templates are recompiled all the time, if the cache size is
            ``-1`` the cache will not be cleaned.

        `auto_reload`
            Some loaders load templates from locations where the template
            sources may change (ie: file system or database).  If
            `auto_reload` is set to `True` (default) every time a template is
            requested the loader checks if the source changed and if yes, it
            will reload the template.  For higher performance it's possible to
            disable that.

        `bytecode_cache`
            If set to a bytecode cache object, this object will provide a
            cache for the internal Jinja bytecode so that templates don't
            have to be parsed if they were not changed.

            See :ref:`bytecode-cache` for more information.
    """

    #: if this environment is sandboxed.  Modifying this variable won't make
    #: the environment sandboxed though.  For a real sandboxed environment
    #: have a look at jinja2.sandbox
    sandboxed = False

    #: True if the environment is just an overlay
    overlay = False

    #: the environment this environment is linked to if it is an overlay
    linked_to = None

    #: shared environments have this set to `True`.  A shared environment
    #: must not be modified
    shared = False

    def __init__(self,
                 block_start_string=BLOCK_START_STRING,
                 block_end_string=BLOCK_END_STRING,
                 variable_start_string=VARIABLE_START_STRING,
                 variable_end_string=VARIABLE_END_STRING,
                 comment_start_string=COMMENT_START_STRING,
                 comment_end_string=COMMENT_END_STRING,
                 line_statement_prefix=LINE_STATEMENT_PREFIX,
                 trim_blocks=TRIM_BLOCKS,
                 newline_sequence=NEWLINE_SEQUENCE,
                 extensions=(),
                 optimized=True,
                 undefined=Undefined,
                 finalize=None,
                 autoescape=False,
                 loader=None,
                 cache_size=50,
                 auto_reload=True,
                 bytecode_cache=None):
        # !!Important notice!!
        #   The constructor accepts quite a few arguments that should be
        #   passed by keyword rather than position.  However it's important to
        #   not change the order of arguments because it's used at least
        #   internally in those cases:
        #       -   spontaneus environments (i18n extension and Template)
        #       -   unittests
        #   If parameter changes are required only add parameters at the end
        #   and don't change the arguments (or the defaults!) of the arguments
        #   existing already.

        # lexer / parser information
        self.block_start_string = block_start_string
        self.block_end_string = block_end_string
        self.variable_start_string = variable_start_string
        self.variable_end_string = variable_end_string
        self.comment_start_string = comment_start_string
        self.comment_end_string = comment_end_string
        self.line_statement_prefix = line_statement_prefix
        self.trim_blocks = trim_blocks
        self.newline_sequence = newline_sequence

        # runtime information
        self.undefined = undefined
        self.optimized = optimized
        self.finalize = finalize
        self.autoescape = autoescape

        # defaults
        self.filters = DEFAULT_FILTERS.copy()
        self.tests = DEFAULT_TESTS.copy()
        self.globals = DEFAULT_NAMESPACE.copy()

        # set the loader provided
        self.loader = loader
        self.bytecode_cache = None
        self.cache = create_cache(cache_size)
        self.bytecode_cache = bytecode_cache
        self.auto_reload = auto_reload

        # load extensions
        self.extensions = load_extensions(self, extensions)

        _environment_sanity_check(self)

    def extend(self, **attributes):
        """Add the items to the instance of the environment if they do not exist
        yet.  This is used by :ref:`extensions <writing-extensions>` to register
        callbacks and configuration values without breaking inheritance.
        """
        for key, value in attributes.iteritems():
            if not hasattr(self, key):
                setattr(self, key, value)

    def overlay(self, block_start_string=missing, block_end_string=missing,
                variable_start_string=missing, variable_end_string=missing,
                comment_start_string=missing, comment_end_string=missing,
                line_statement_prefix=missing, trim_blocks=missing,
                extensions=missing, optimized=missing, undefined=missing,
                finalize=missing, autoescape=missing, loader=missing,
                cache_size=missing, auto_reload=missing,
                bytecode_cache=missing):
        """Create a new overlay environment that shares all the data with the
        current environment except of cache and the overriden attributes.
        Extensions cannot be removed for a overlayed environment.  A overlayed
        environment automatically gets all the extensions of the environment it
        is linked to plus optional extra extensions.

        Creating overlays should happen after the initial environment was set
        up completely.  Not all attributes are truly linked, some are just
        copied over so modifications on the original environment may not shine
        through.
        """
        args = dict(locals())
        del args['self'], args['cache_size'], args['extensions']

        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        rv.overlay = True
        rv.linked_to = self

        for key, value in args.iteritems():
            if value is not missing:
                setattr(rv, key, value)

        if cache_size is not missing:
            rv.cache = create_cache(cache_size)
        else:
            rv.cache = copy_cache(self.cache)

        rv.extensions = {}
        for key, value in self.extensions.iteritems():
            rv.extensions[key] = value.bind(rv)
        if extensions is not missing:
            rv.extensions.update(load_extensions(extensions))

        return _environment_sanity_check(rv)

    lexer = property(get_lexer, doc="The lexer for this environment.")

    def getitem(self, obj, argument):
        """Get an item or attribute of an object but prefer the item."""
        try:
            return obj[argument]
        except (TypeError, LookupError):
            if isinstance(argument, basestring):
                try:
                    attr = str(argument)
                except:
                    pass
                else:
                    try:
                        return getattr(obj, attr)
                    except AttributeError:
                        pass
            return self.undefined(obj=obj, name=argument)

    def getattr(self, obj, attribute):
        """Get an item or attribute of an object but prefer the attribute.
        Unlike :meth:`getitem` the attribute *must* be a bytestring.
        """
        try:
            return getattr(obj, attribute)
        except AttributeError:
            pass
        try:
            return obj[attribute]
        except (TypeError, LookupError, AttributeError):
            return self.undefined(obj=obj, name=attribute)

    def parse(self, source, name=None, filename=None):
        """Parse the sourcecode and return the abstract syntax tree.  This
        tree of nodes is used by the compiler to convert the template into
        executable source- or bytecode.  This is useful for debugging or to
        extract information from templates.

        If you are :ref:`developing Jinja2 extensions <writing-extensions>`
        this gives you a good overview of the node tree generated.
        """
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        try:
            return Parser(self, source, name, filename).parse()
        except TemplateSyntaxError, e:
            e.source = source
            raise e

    def lex(self, source, name=None, filename=None):
        """Lex the given sourcecode and return a generator that yields
        tokens as tuples in the form ``(lineno, token_type, value)``.
        This can be useful for :ref:`extension development <writing-extensions>`
        and debugging templates.

        This does not perform preprocessing.  If you want the preprocessing
        of the extensions to be applied you have to filter source through
        the :meth:`preprocess` method.
        """
        source = unicode(source)
        try:
            return self.lexer.tokeniter(source, name, filename)
        except TemplateSyntaxError, e:
            e.source = source
            raise e

    def preprocess(self, source, name=None, filename=None):
        """Preprocesses the source with all extensions.  This is automatically
        called for all parsing and compiling methods but *not* for :meth:`lex`
        because there you usually only want the actual source tokenized.
        """
        return reduce(lambda s, e: e.preprocess(s, name, filename),
                      self.extensions.itervalues(), unicode(source))

    def _tokenize(self, source, name, filename=None, state=None):
        """Called by the parser to do the preprocessing and filtering
        for all the extensions.  Returns a :class:`~jinja2.lexer.TokenStream`.
        """
        source = self.preprocess(source, name, filename)
        stream = self.lexer.tokenize(source, name, filename, state)
        for ext in self.extensions.itervalues():
            stream = ext.filter_stream(stream)
            if not isinstance(stream, TokenStream):
                stream = TokenStream(stream, name, filename)
        return stream

    def compile(self, source, name=None, filename=None, raw=False):
        """Compile a node or template source code.  The `name` parameter is
        the load name of the template after it was joined using
        :meth:`join_path` if necessary, not the filename on the file system.
        the `filename` parameter is the estimated filename of the template on
        the file system.  If the template came from a database or memory this
        can be omitted.

        The return value of this method is a python code object.  If the `raw`
        parameter is `True` the return value will be a string with python
        code equivalent to the bytecode returned otherwise.  This method is
        mainly used internally.
        """
        if isinstance(source, basestring):
            source = self.parse(source, name, filename)
        if self.optimized:
            source = optimize(source, self)
        source = generate(source, self, name, filename)
        if raw:
            return source
        if filename is None:
            filename = '<template>'
        elif isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        return compile(source, filename, 'exec')

    def compile_expression(self, source, undefined_to_none=True):
        """A handy helper method that returns a callable that accepts keyword
        arguments that appear as variables in the expression.  If called it
        returns the result of the expression.

        This is useful if applications want to use the same rules as Jinja
        in template "configuration files" or similar situations.

        Example usage:

        >>> env = Environment()
        >>> expr = env.compile_expression('foo == 42')
        >>> expr(foo=23)
        False
        >>> expr(foo=42)
        True

        Per default the return value is converted to `None` if the
        expression returns an undefined value.  This can be changed
        by setting `undefined_to_none` to `False`.

        >>> env.compile_expression('var')() is None
        True
        >>> env.compile_expression('var', undefined_to_none=False)()
        Undefined

        **new in Jinja 2.1**
        """
        parser = Parser(self, source, state='variable')
        try:
            expr = parser.parse_expression()
            if not parser.stream.eos:
                raise TemplateSyntaxError('chunk after expression',
                                          parser.stream.current.lineno,
                                          None, None)
        except TemplateSyntaxError, e:
            e.source = source
            raise e
        body = [nodes.Assign(nodes.Name('result', 'store'), expr, lineno=1)]
        template = self.from_string(nodes.Template(body, lineno=1))
        return TemplateExpression(template, undefined_to_none)

    def join_path(self, template, parent):
        """Join a template with the parent.  By default all the lookups are
        relative to the loader root so this method returns the `template`
        parameter unchanged, but if the paths should be relative to the
        parent template, this function can be used to calculate the real
        template name.

        Subclasses may override this method and implement template path
        joining here.
        """
        return template

    def get_template(self, name, parent=None, globals=None):
        """Load a template from the loader.  If a loader is configured this
        method ask the loader for the template and returns a :class:`Template`.
        If the `parent` parameter is not `None`, :meth:`join_path` is called
        to get the real template name before loading.

        The `globals` parameter can be used to provide template wide globals.
        These variables are available in the context at render time.

        If the template does not exist a :exc:`TemplateNotFound` exception is
        raised.
        """
        if self.loader is None:
            raise TypeError('no loader for this environment specified')
        if parent is not None:
            name = self.join_path(name, parent)

        if self.cache is not None:
            template = self.cache.get(name)
            if template is not None and (not self.auto_reload or \
                                         template.is_up_to_date):
                return template

        template = self.loader.load(self, name, self.make_globals(globals))
        if self.cache is not None:
            self.cache[name] = template
        return template

    def from_string(self, source, globals=None, template_class=None):
        """Load a template from a string.  This parses the source given and
        returns a :class:`Template` object.
        """
        globals = self.make_globals(globals)
        cls = template_class or self.template_class
        return cls.from_code(self, self.compile(source), globals, None)

    def make_globals(self, d):
        """Return a dict for the globals."""
        if not d:
            return self.globals
        return dict(self.globals, **d)


class Template(object):
    """The central template object.  This class represents a compiled template
    and is used to evaluate it.

    Normally the template object is generated from an :class:`Environment` but
    it also has a constructor that makes it possible to create a template
    instance directly using the constructor.  It takes the same arguments as
    the environment constructor but it's not possible to specify a loader.

    Every template object has a few methods and members that are guaranteed
    to exist.  However it's important that a template object should be
    considered immutable.  Modifications on the object are not supported.

    Template objects created from the constructor rather than an environment
    do have an `environment` attribute that points to a temporary environment
    that is probably shared with other templates created with the constructor
    and compatible settings.

    >>> template = Template('Hello {{ name }}!')
    >>> template.render(name='John Doe')
    u'Hello John Doe!'

    >>> stream = template.stream(name='John Doe')
    >>> stream.next()
    u'Hello John Doe!'
    >>> stream.next()
    Traceback (most recent call last):
        ...
    StopIteration
    """

    def __new__(cls, source,
                block_start_string=BLOCK_START_STRING,
                block_end_string=BLOCK_END_STRING,
                variable_start_string=VARIABLE_START_STRING,
                variable_end_string=VARIABLE_END_STRING,
                comment_start_string=COMMENT_START_STRING,
                comment_end_string=COMMENT_END_STRING,
                line_statement_prefix=LINE_STATEMENT_PREFIX,
                trim_blocks=TRIM_BLOCKS,
                newline_sequence=NEWLINE_SEQUENCE,
                extensions=(),
                optimized=True,
                undefined=Undefined,
                finalize=None,
                autoescape=False):
        env = get_spontaneous_environment(
            block_start_string, block_end_string, variable_start_string,
            variable_end_string, comment_start_string, comment_end_string,
            line_statement_prefix, trim_blocks, newline_sequence,
            frozenset(extensions), optimized, undefined, finalize,
            autoescape, None, 0, False, None)
        return env.from_string(source, template_class=cls)

    @classmethod
    def from_code(cls, environment, code, globals, uptodate=None):
        """Creates a template object from compiled code and the globals.  This
        is used by the loaders and environment to create a template object.
        """
        t = object.__new__(cls)
        namespace = {
            'environment':          environment,
            '__jinja_template__':   t
        }
        exec code in namespace
        t.environment = environment
        t.globals = globals
        t.name = namespace['name']
        t.filename = code.co_filename
        t.blocks = namespace['blocks']

        # render function and module
        t.root_render_func = namespace['root']
        t._module = None

        # debug and loader helpers
        t._debug_info = namespace['debug_info']
        t._uptodate = uptodate

        return t

    def render(self, *args, **kwargs):
        """This method accepts the same arguments as the `dict` constructor:
        A dict, a dict subclass or some keyword arguments.  If no arguments
        are given the context will be empty.  These two calls do the same::

            template.render(knights='that say nih')
            template.render({'knights': 'that say nih'})

        This will return the rendered template as unicode string.
        """
        vars = dict(*args, **kwargs)
        try:
            return concat(self.root_render_func(self.new_context(vars)))
        except:
            from jinja2.debug import translate_exception
            exc_type, exc_value, tb = translate_exception(sys.exc_info())
            raise exc_type, exc_value, tb

    def stream(self, *args, **kwargs):
        """Works exactly like :meth:`generate` but returns a
        :class:`TemplateStream`.
        """
        return TemplateStream(self.generate(*args, **kwargs))

    def generate(self, *args, **kwargs):
        """For very large templates it can be useful to not render the whole
        template at once but evaluate each statement after another and yield
        piece for piece.  This method basically does exactly that and returns
        a generator that yields one item after another as unicode strings.

        It accepts the same arguments as :meth:`render`.
        """
        vars = dict(*args, **kwargs)
        try:
            for event in self.root_render_func(self.new_context(vars)):
                yield event
        except:
            from jinja2.debug import translate_exception
            exc_type, exc_value, tb = translate_exception(sys.exc_info())
            raise exc_type, exc_value, tb

    def new_context(self, vars=None, shared=False, locals=None):
        """Create a new :class:`Context` for this template.  The vars
        provided will be passed to the template.  Per default the globals
        are added to the context.  If shared is set to `True` the data
        is passed as it to the context without adding the globals.

        `locals` can be a dict of local variables for internal usage.
        """
        if vars is None:
            vars = {}
        if shared:
            parent = vars
        else:
            parent = dict(self.globals, **vars)
        if locals:
            # if the parent is shared a copy should be created because
            # we don't want to modify the dict passed
            if shared:
                parent = dict(parent)
            for key, value in locals.iteritems():
                if key[:2] == 'l_' and value is not missing:
                    parent[key[2:]] = value
        return Context(self.environment, parent, self.name, self.blocks)

    def make_module(self, vars=None, shared=False, locals=None):
        """This method works like the :attr:`module` attribute when called
        without arguments but it will evaluate the template every call
        rather then caching the template.  It's also possible to provide
        a dict which is then used as context.  The arguments are the same
        as for the :meth:`new_context` method.
        """
        return TemplateModule(self, self.new_context(vars, shared, locals))

    @property
    def module(self):
        """The template as module.  This is used for imports in the
        template runtime but is also useful if one wants to access
        exported template variables from the Python layer:

        >>> t = Template('{% macro foo() %}42{% endmacro %}23')
        >>> unicode(t.module)
        u'23'
        >>> t.module.foo()
        u'42'
        """
        if self._module is not None:
            return self._module
        self._module = rv = self.make_module()
        return rv

    def get_corresponding_lineno(self, lineno):
        """Return the source line number of a line number in the
        generated bytecode as they are not in sync.
        """
        for template_line, code_line in reversed(self.debug_info):
            if code_line <= lineno:
                return template_line
        return 1

    @property
    def is_up_to_date(self):
        """If this variable is `False` there is a newer version available."""
        if self._uptodate is None:
            return True
        return self._uptodate()

    @property
    def debug_info(self):
        """The debug info mapping."""
        return [tuple(map(int, x.split('='))) for x in
                self._debug_info.split('&')]

    def __repr__(self):
        if self.name is None:
            name = 'memory:%x' % id(self)
        else:
            name = repr(self.name)
        return '<%s %s>' % (self.__class__.__name__, name)


class TemplateModule(object):
    """Represents an imported template.  All the exported names of the
    template are available as attributes on this object.  Additionally
    converting it into an unicode- or bytestrings renders the contents.
    """

    def __init__(self, template, context):
        self._body_stream = list(template.root_render_func(context))
        self.__dict__.update(context.get_exported())
        self.__name__ = template.name

    __unicode__ = lambda x: concat(x._body_stream)
    __html__ = lambda x: Markup(concat(x._body_stream))

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        if self.__name__ is None:
            name = 'memory:%x' % id(self)
        else:
            name = repr(self.__name__)
        return '<%s %s>' % (self.__class__.__name__, name)


class TemplateExpression(object):
    """The :meth:`jinja2.Environment.compile_expression` method returns an
    instance of this object.  It encapsulates the expression-like access
    to the template with an expression it wraps.
    """

    def __init__(self, template, undefined_to_none):
        self._template = template
        self._undefined_to_none = undefined_to_none

    def __call__(self, *args, **kwargs):
        context = self._template.new_context(dict(*args, **kwargs))
        consume(self._template.root_render_func(context))
        rv = context.vars['result']
        if self._undefined_to_none and isinstance(rv, Undefined):
            rv = None
        return rv


class TemplateStream(object):
    """A template stream works pretty much like an ordinary python generator
    but it can buffer multiple items to reduce the number of total iterations.
    Per default the output is unbuffered which means that for every unbuffered
    instruction in the template one unicode string is yielded.

    If buffering is enabled with a buffer size of 5, five items are combined
    into a new unicode string.  This is mainly useful if you are streaming
    big templates to a client via WSGI which flushes after each iteration.
    """

    def __init__(self, gen):
        self._gen = gen
        self.disable_buffering()

    def dump(self, fp, encoding=None, errors='strict'):
        """Dump the complete stream into a file or file-like object.
        Per default unicode strings are written, if you want to encode
        before writing specifiy an `encoding`.

        Example usage::

            Template('Hello {{ name }}!').stream(name='foo').dump('hello.html')
        """
        close = False
        if isinstance(fp, basestring):
            fp = file(fp, 'w')
            close = True
        try:
            if encoding is not None:
                iterable = (x.encode(encoding, errors) for x in self)
            else:
                iterable = self
            if hasattr(fp, 'writelines'):
                fp.writelines(iterable)
            else:
                for item in iterable:
                    fp.write(item)
        finally:
            if close:
                fp.close()

    def disable_buffering(self):
        """Disable the output buffering."""
        self._next = self._gen.next
        self.buffered = False

    def enable_buffering(self, size=5):
        """Enable buffering.  Buffer `size` items before yielding them."""
        if size <= 1:
            raise ValueError('buffer size too small')

        def generator(next):
            buf = []
            c_size = 0
            push = buf.append

            while 1:
                try:
                    while c_size < size:
                        c = next()
                        push(c)
                        if c:
                            c_size += 1
                except StopIteration:
                    if not c_size:
                        return
                yield concat(buf)
                del buf[:]
                c_size = 0

        self.buffered = True
        self._next = generator(self._gen.next).next

    def __iter__(self):
        return self

    def next(self):
        return self._next()


# hook in default template class.  if anyone reads this comment: ignore that
# it's possible to use custom templates ;-)
Environment.template_class = Template

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
"""
    jinja2.exceptions
    ~~~~~~~~~~~~~~~~~

    Jinja exceptions.

    :copyright: 2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""


class TemplateError(Exception):
    """Baseclass for all template errors."""


class TemplateNotFound(IOError, LookupError, TemplateError):
    """Raised if a template does not exist."""

    def __init__(self, name):
        IOError.__init__(self, name)
        self.name = name


class TemplateSyntaxError(TemplateError):
    """Raised to tell the user that there is a problem with the template."""

    def __init__(self, message, lineno, name=None, filename=None):
        if not isinstance(message, unicode):
            message = message.decode('utf-8', 'replace')
        TemplateError.__init__(self, message.encode('utf-8'))
        self.lineno = lineno
        self.name = name
        self.filename = filename
        self.source = None
        self.message = message

    def __unicode__(self):
        location = 'line %d' % self.lineno
        name = self.filename or self.name
        if name:
            location = 'File "%s", %s' % (name, location)
        lines = [self.message, '  ' + location]

        # if the source is set, add the line to the output
        if self.source is not None:
            try:
                line = self.source.splitlines()[self.lineno - 1]
            except IndexError:
                line = None
            if line:
                lines.append('    ' + line.strip())

        return u'\n'.join(lines)

    def __str__(self):
        return unicode(self).encode('utf-8')


class TemplateAssertionError(TemplateSyntaxError):
    """Like a template syntax error, but covers cases where something in the
    template caused an error at compile time that wasn't necessarily caused
    by a syntax error.  However it's a direct subclass of
    :exc:`TemplateSyntaxError` and has the same attributes.
    """


class TemplateRuntimeError(TemplateError):
    """A generic runtime error in the template engine.  Under some situations
    Jinja may raise this exception.
    """


class UndefinedError(TemplateRuntimeError):
    """Raised if a template tries to operate on :class:`Undefined`."""


class SecurityError(TemplateRuntimeError):
    """Raised if a template tries to do something insecure if the
    sandbox is enabled.
    """


class FilterArgumentError(TemplateRuntimeError):
    """This error is raised if a filter was called with inappropriate
    arguments
    """

########NEW FILE########
__FILENAME__ = ext
# -*- coding: utf-8 -*-
"""
    jinja2.ext
    ~~~~~~~~~~

    Jinja extensions allow to add custom tags similar to the way django custom
    tags work.  By default two example extensions exist: an i18n and a cache
    extension.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
from collections import deque
from jinja2 import nodes
from jinja2.defaults import *
from jinja2.environment import get_spontaneous_environment
from jinja2.runtime import Undefined, concat
from jinja2.exceptions import TemplateAssertionError, TemplateSyntaxError
from jinja2.utils import contextfunction, import_string, Markup


# the only real useful gettext functions for a Jinja template.  Note
# that ugettext must be assigned to gettext as Jinja doesn't support
# non unicode strings.
GETTEXT_FUNCTIONS = ('_', 'gettext', 'ngettext')


class ExtensionRegistry(type):
    """Gives the extension an unique identifier."""

    def __new__(cls, name, bases, d):
        rv = type.__new__(cls, name, bases, d)
        rv.identifier = rv.__module__ + '.' + rv.__name__
        return rv


class Extension(object):
    """Extensions can be used to add extra functionality to the Jinja template
    system at the parser level.  Custom extensions are bound to an environment
    but may not store environment specific data on `self`.  The reason for
    this is that an extension can be bound to another environment (for
    overlays) by creating a copy and reassigning the `environment` attribute.

    As extensions are created by the environment they cannot accept any
    arguments for configuration.  One may want to work around that by using
    a factory function, but that is not possible as extensions are identified
    by their import name.  The correct way to configure the extension is
    storing the configuration values on the environment.  Because this way the
    environment ends up acting as central configuration storage the
    attributes may clash which is why extensions have to ensure that the names
    they choose for configuration are not too generic.  ``prefix`` for example
    is a terrible name, ``fragment_cache_prefix`` on the other hand is a good
    name as includes the name of the extension (fragment cache).
    """
    __metaclass__ = ExtensionRegistry

    #: if this extension parses this is the list of tags it's listening to.
    tags = set()

    def __init__(self, environment):
        self.environment = environment

    def bind(self, environment):
        """Create a copy of this extension bound to another environment."""
        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        rv.environment = environment
        return rv

    def preprocess(self, source, name, filename=None):
        """This method is called before the actual lexing and can be used to
        preprocess the source.  The `filename` is optional.  The return value
        must be the preprocessed source.
        """
        return source

    def filter_stream(self, stream):
        """It's passed a :class:`~jinja2.lexer.TokenStream` that can be used
        to filter tokens returned.  This method has to return an iterable of
        :class:`~jinja2.lexer.Token`\s, but it doesn't have to return a
        :class:`~jinja2.lexer.TokenStream`.

        In the `ext` folder of the Jinja2 source distribution there is a file
        called `inlinegettext.py` which implements a filter that utilizes this
        method.
        """
        return stream

    def parse(self, parser):
        """If any of the :attr:`tags` matched this method is called with the
        parser as first argument.  The token the parser stream is pointing at
        is the name token that matched.  This method has to return one or a
        list of multiple nodes.
        """
        raise NotImplementedError()

    def attr(self, name, lineno=None):
        """Return an attribute node for the current extension.  This is useful
        to pass constants on extensions to generated template code::

            self.attr('_my_attribute', lineno=lineno)
        """
        return nodes.ExtensionAttribute(self.identifier, name, lineno=lineno)

    def call_method(self, name, args=None, kwargs=None, dyn_args=None,
                    dyn_kwargs=None, lineno=None):
        """Call a method of the extension.  This is a shortcut for
        :meth:`attr` + :class:`jinja2.nodes.Call`.
        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = []
        return nodes.Call(self.attr(name, lineno=lineno), args, kwargs,
                          dyn_args, dyn_kwargs, lineno=lineno)


@contextfunction
def _gettext_alias(context, string):
    return context.resolve('gettext')(string)


class InternationalizationExtension(Extension):
    """This extension adds gettext support to Jinja2."""
    tags = set(['trans'])

    # TODO: the i18n extension is currently reevaluating values in a few
    # situations.  Take this example:
    #   {% trans count=something() %}{{ count }} foo{% pluralize
    #     %}{{ count }} fooss{% endtrans %}
    # something is called twice here.  One time for the gettext value and
    # the other time for the n-parameter of the ngettext function.

    def __init__(self, environment):
        Extension.__init__(self, environment)
        environment.globals['_'] = _gettext_alias
        environment.extend(
            install_gettext_translations=self._install,
            install_null_translations=self._install_null,
            uninstall_gettext_translations=self._uninstall,
            extract_translations=self._extract
        )

    def _install(self, translations):
        gettext = getattr(translations, 'ugettext', None)
        if gettext is None:
            gettext = translations.gettext
        ngettext = getattr(translations, 'ungettext', None)
        if ngettext is None:
            ngettext = translations.ngettext
        self.environment.globals.update(gettext=gettext, ngettext=ngettext)

    def _install_null(self):
        self.environment.globals.update(
            gettext=lambda x: x,
            ngettext=lambda s, p, n: (n != 1 and (p,) or (s,))[0]
        )

    def _uninstall(self, translations):
        for key in 'gettext', 'ngettext':
            self.environment.globals.pop(key, None)

    def _extract(self, source, gettext_functions=GETTEXT_FUNCTIONS):
        if isinstance(source, basestring):
            source = self.environment.parse(source)
        return extract_from_ast(source, gettext_functions)

    def parse(self, parser):
        """Parse a translatable tag."""
        lineno = parser.stream.next().lineno

        # find all the variables referenced.  Additionally a variable can be
        # defined in the body of the trans block too, but this is checked at
        # a later state.
        plural_expr = None
        variables = {}
        while parser.stream.current.type is not 'block_end':
            if variables:
                parser.stream.expect('comma')

            # skip colon for python compatibility
            if parser.stream.skip_if('colon'):
                break

            name = parser.stream.expect('name')
            if name.value in variables:
                parser.fail('translatable variable %r defined twice.' %
                            name.value, name.lineno,
                            exc=TemplateAssertionError)

            # expressions
            if parser.stream.current.type is 'assign':
                parser.stream.next()
                variables[name.value] = var = parser.parse_expression()
            else:
                variables[name.value] = var = nodes.Name(name.value, 'load')
            if plural_expr is None:
                plural_expr = var

        parser.stream.expect('block_end')

        plural = plural_names = None
        have_plural = False
        referenced = set()

        # now parse until endtrans or pluralize
        singular_names, singular = self._parse_block(parser, True)
        if singular_names:
            referenced.update(singular_names)
            if plural_expr is None:
                plural_expr = nodes.Name(singular_names[0], 'load')

        # if we have a pluralize block, we parse that too
        if parser.stream.current.test('name:pluralize'):
            have_plural = True
            parser.stream.next()
            if parser.stream.current.type is not 'block_end':
                name = parser.stream.expect('name')
                if name.value not in variables:
                    parser.fail('unknown variable %r for pluralization' %
                                name.value, name.lineno,
                                exc=TemplateAssertionError)
                plural_expr = variables[name.value]
            parser.stream.expect('block_end')
            plural_names, plural = self._parse_block(parser, False)
            parser.stream.next()
            referenced.update(plural_names)
        else:
            parser.stream.next()

        # register free names as simple name expressions
        for var in referenced:
            if var not in variables:
                variables[var] = nodes.Name(var, 'load')

        # no variables referenced?  no need to escape
        if not referenced:
            singular = singular.replace('%%', '%')
            if plural:
                plural = plural.replace('%%', '%')

        if not have_plural:
            plural_expr = None
        elif plural_expr is None:
            parser.fail('pluralize without variables', lineno)

        if variables:
            variables = nodes.Dict([nodes.Pair(nodes.Const(x, lineno=lineno), y)
                                    for x, y in variables.items()])
        else:
            variables = None

        node = self._make_node(singular, plural, variables, plural_expr)
        node.set_lineno(lineno)
        return node

    def _parse_block(self, parser, allow_pluralize):
        """Parse until the next block tag with a given name."""
        referenced = []
        buf = []
        while 1:
            if parser.stream.current.type is 'data':
                buf.append(parser.stream.current.value.replace('%', '%%'))
                parser.stream.next()
            elif parser.stream.current.type is 'variable_begin':
                parser.stream.next()
                name = parser.stream.expect('name').value
                referenced.append(name)
                buf.append('%%(%s)s' % name)
                parser.stream.expect('variable_end')
            elif parser.stream.current.type is 'block_begin':
                parser.stream.next()
                if parser.stream.current.test('name:endtrans'):
                    break
                elif parser.stream.current.test('name:pluralize'):
                    if allow_pluralize:
                        break
                    parser.fail('a translatable section can have only one '
                                'pluralize section')
                parser.fail('control structures in translatable sections are '
                            'not allowed')
            elif parser.stream.eos:
                parser.fail('unclosed translation block')
            else:
                assert False, 'internal parser error'

        return referenced, concat(buf)

    def _make_node(self, singular, plural, variables, plural_expr):
        """Generates a useful node from the data provided."""
        # singular only:
        if plural_expr is None:
            gettext = nodes.Name('gettext', 'load')
            node = nodes.Call(gettext, [nodes.Const(singular)],
                              [], None, None)

        # singular and plural
        else:
            ngettext = nodes.Name('ngettext', 'load')
            node = nodes.Call(ngettext, [
                nodes.Const(singular),
                nodes.Const(plural),
                plural_expr
            ], [], None, None)

        # mark the return value as safe if we are in an
        # environment with autoescaping turned on
        if self.environment.autoescape:
            node = nodes.MarkSafe(node)

        if variables:
            node = nodes.Mod(node, variables)
        return nodes.Output([node])


class ExprStmtExtension(Extension):
    """Adds a `do` tag to Jinja2 that works like the print statement just
    that it doesn't print the return value.
    """
    tags = set(['do'])

    def parse(self, parser):
        node = nodes.ExprStmt(lineno=parser.stream.next().lineno)
        node.node = parser.parse_tuple()
        return node


class LoopControlExtension(Extension):
    """Adds break and continue to the template engine."""
    tags = set(['break', 'continue'])

    def parse(self, parser):
        token = parser.stream.next()
        if token.value == 'break':
            return nodes.Break(lineno=token.lineno)
        return nodes.Continue(lineno=token.lineno)


def extract_from_ast(node, gettext_functions=GETTEXT_FUNCTIONS,
                     babel_style=True):
    """Extract localizable strings from the given template node.  Per
    default this function returns matches in babel style that means non string
    parameters as well as keyword arguments are returned as `None`.  This
    allows Babel to figure out what you really meant if you are using
    gettext functions that allow keyword arguments for placeholder expansion.
    If you don't want that behavior set the `babel_style` parameter to `False`
    which causes only strings to be returned and parameters are always stored
    in tuples.  As a consequence invalid gettext calls (calls without a single
    string parameter or string parameters after non-string parameters) are
    skipped.

    This example explains the behavior:

    >>> from jinja2 import Environment
    >>> env = Environment()
    >>> node = env.parse('{{ (_("foo"), _(), ngettext("foo", "bar", 42)) }}')
    >>> list(extract_from_ast(node))
    [(1, '_', 'foo'), (1, '_', ()), (1, 'ngettext', ('foo', 'bar', None))]
    >>> list(extract_from_ast(node, babel_style=False))
    [(1, '_', ('foo',)), (1, 'ngettext', ('foo', 'bar'))]

    For every string found this function yields a ``(lineno, function,
    message)`` tuple, where:

    * ``lineno`` is the number of the line on which the string was found,
    * ``function`` is the name of the ``gettext`` function used (if the
      string was extracted from embedded Python code), and
    *  ``message`` is the string itself (a ``unicode`` object, or a tuple
       of ``unicode`` objects for functions with multiple string arguments).
    """
    for node in node.find_all(nodes.Call):
        if not isinstance(node.node, nodes.Name) or \
           node.node.name not in gettext_functions:
            continue

        strings = []
        for arg in node.args:
            if isinstance(arg, nodes.Const) and \
               isinstance(arg.value, basestring):
                strings.append(arg.value)
            else:
                strings.append(None)

        for arg in node.kwargs:
            strings.append(None)
        if node.dyn_args is not None:
            strings.append(None)
        if node.dyn_kwargs is not None:
            strings.append(None)

        if not babel_style:
            strings = tuple(x for x in strings if x is not None)
            if not strings:
                continue
        else:
            if len(strings) == 1:
                strings = strings[0]
            else:
                strings = tuple(strings)
        yield node.lineno, node.node.name, strings


def babel_extract(fileobj, keywords, comment_tags, options):
    """Babel extraction method for Jinja templates.

    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results.  (Unused)
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples.
             (comments will be empty currently)
    """
    extensions = set()
    for extension in options.get('extensions', '').split(','):
        extension = extension.strip()
        if not extension:
            continue
        extensions.add(import_string(extension))
    if InternationalizationExtension not in extensions:
        extensions.add(InternationalizationExtension)

    environment = get_spontaneous_environment(
        options.get('block_start_string', BLOCK_START_STRING),
        options.get('block_end_string', BLOCK_END_STRING),
        options.get('variable_start_string', VARIABLE_START_STRING),
        options.get('variable_end_string', VARIABLE_END_STRING),
        options.get('comment_start_string', COMMENT_START_STRING),
        options.get('comment_end_string', COMMENT_END_STRING),
        options.get('line_statement_prefix') or LINE_STATEMENT_PREFIX,
        str(options.get('trim_blocks', TRIM_BLOCKS)).lower() in \
            ('1', 'on', 'yes', 'true'),
        NEWLINE_SEQUENCE, frozenset(extensions),
        # fill with defaults so that environments are shared
        # with other spontaneus environments.  The rest of the
        # arguments are optimizer, undefined, finalize, autoescape,
        # loader, cache size, auto reloading setting and the
        # bytecode cache
        True, Undefined, None, False, None, 0, False, None
    )

    source = fileobj.read().decode(options.get('encoding', 'utf-8'))
    try:
        node = environment.parse(source)
    except TemplateSyntaxError, e:
        # skip templates with syntax errors
        return
    for lineno, func, message in extract_from_ast(node, keywords):
        yield lineno, func, message, []


#: nicer import names
i18n = InternationalizationExtension
do = ExprStmtExtension
loopcontrols = LoopControlExtension

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-
"""
    jinja2.filters
    ~~~~~~~~~~~~~~

    Bundled jinja filters.

    :copyright: 2008 by Armin Ronacher, Christoph Hack.
    :license: BSD, see LICENSE for more details.
"""
import re
import math
from random import choice
from operator import itemgetter
from itertools import imap, groupby
from jinja2.utils import Markup, escape, pformat, urlize, soft_unicode
from jinja2.runtime import Undefined
from jinja2.exceptions import FilterArgumentError, SecurityError


_word_re = re.compile(r'\w+')


def contextfilter(f):
    """Decorator for marking context dependent filters. The current
    :class:`Context` will be passed as first argument.
    """
    if getattr(f, 'environmentfilter', False):
        raise TypeError('filter already marked as environment filter')
    f.contextfilter = True
    return f


def environmentfilter(f):
    """Decorator for marking evironment dependent filters.  The current
    :class:`Environment` is passed to the filter as first argument.
    """
    if getattr(f, 'contextfilter', False):
        raise TypeError('filter already marked as context filter')
    f.environmentfilter = True
    return f


def do_forceescape(value):
    """Enforce HTML escaping.  This will probably double escape variables."""
    if hasattr(value, '__html__'):
        value = value.__html__()
    return escape(unicode(value))


@environmentfilter
def do_replace(environment, s, old, new, count=None):
    """Return a copy of the value with all occurrences of a substring
    replaced with a new one. The first argument is the substring
    that should be replaced, the second is the replacement string.
    If the optional third argument ``count`` is given, only the first
    ``count`` occurrences are replaced:

    .. sourcecode:: jinja

        {{ "Hello World"|replace("Hello", "Goodbye") }}
            -> Goodbye World

        {{ "aaaaargh"|replace("a", "d'oh, ", 2) }}
            -> d'oh, d'oh, aaargh
    """
    if count is None:
        count = -1
    if not environment.autoescape:
        return unicode(s).replace(unicode(old), unicode(new), count)
    if hasattr(old, '__html__') or hasattr(new, '__html__') and \
       not hasattr(s, '__html__'):
        s = escape(s)
    else:
        s = soft_unicode(s)
    return s.replace(soft_unicode(old), soft_unicode(new), count)


def do_upper(s):
    """Convert a value to uppercase."""
    return soft_unicode(s).upper()


def do_lower(s):
    """Convert a value to lowercase."""
    return soft_unicode(s).lower()


@environmentfilter
def do_xmlattr(_environment, d, autospace=True):
    """Create an SGML/XML attribute string based on the items in a dict.
    All values that are neither `none` nor `undefined` are automatically
    escaped:

    .. sourcecode:: html+jinja

        <ul{{ {'class': 'my_list', 'missing': none,
                'id': 'list-%d'|format(variable)}|xmlattr }}>
        ...
        </ul>

    Results in something like this:

    .. sourcecode:: html

        <ul class="my_list" id="list-42">
        ...
        </ul>

    As you can see it automatically prepends a space in front of the item
    if the filter returned something unless the second parameter is false.
    """
    rv = u' '.join(
        u'%s="%s"' % (escape(key), escape(value))
        for key, value in d.iteritems()
        if value is not None and not isinstance(value, Undefined)
    )
    if autospace and rv:
        rv = u' ' + rv
    if _environment.autoescape:
        rv = Markup(rv)
    return rv


def do_capitalize(s):
    """Capitalize a value. The first character will be uppercase, all others
    lowercase.
    """
    return soft_unicode(s).capitalize()


def do_title(s):
    """Return a titlecased version of the value. I.e. words will start with
    uppercase letters, all remaining characters are lowercase.
    """
    return soft_unicode(s).title()


def do_dictsort(value, case_sensitive=False, by='key'):
    """Sort a dict and yield (key, value) pairs. Because python dicts are
    unsorted you may want to use this function to order them by either
    key or value:

    .. sourcecode:: jinja

        {% for item in mydict|dictsort %}
            sort the dict by key, case insensitive

        {% for item in mydict|dicsort(true) %}
            sort the dict by key, case sensitive

        {% for item in mydict|dictsort(false, 'value') %}
            sort the dict by key, case insensitive, sorted
            normally and ordered by value.
    """
    if by == 'key':
        pos = 0
    elif by == 'value':
        pos = 1
    else:
        raise FilterArgumentError('You can only sort by either '
                                  '"key" or "value"')
    def sort_func(item):
        value = item[pos]
        if isinstance(value, basestring) and not case_sensitive:
            value = value.lower()
        return value

    return sorted(value.items(), key=sort_func)


def do_sort(value, case_sensitive=False):
    """Sort an iterable.  If the iterable is made of strings the second
    parameter can be used to control the case sensitiveness of the
    comparison which is disabled by default.

    .. sourcecode:: jinja

        {% for item in iterable|sort %}
            ...
        {% endfor %}
    """
    if not case_sensitive:
        def sort_func(item):
            if isinstance(item, basestring):
                item = item.lower()
            return item
    else:
        sort_func = None
    return sorted(seq, key=sort_func)


def do_default(value, default_value=u'', boolean=False):
    """If the value is undefined it will return the passed default value,
    otherwise the value of the variable:

    .. sourcecode:: jinja

        {{ my_variable|default('my_variable is not defined') }}

    This will output the value of ``my_variable`` if the variable was
    defined, otherwise ``'my_variable is not defined'``. If you want
    to use default with variables that evaluate to false you have to
    set the second parameter to `true`:

    .. sourcecode:: jinja

        {{ ''|default('the string was empty', true) }}
    """
    if (boolean and not value) or isinstance(value, Undefined):
        return default_value
    return value


@environmentfilter
def do_join(environment, value, d=u''):
    """Return a string which is the concatenation of the strings in the
    sequence. The separator between elements is an empty string per
    default, you can define it with the optional parameter:

    .. sourcecode:: jinja

        {{ [1, 2, 3]|join('|') }}
            -> 1|2|3

        {{ [1, 2, 3]|join }}
            -> 123
    """
    # no automatic escaping?  joining is a lot eaiser then
    if not environment.autoescape:
        return unicode(d).join(imap(unicode, value))

    # if the delimiter doesn't have an html representation we check
    # if any of the items has.  If yes we do a coercion to Markup
    if not hasattr(d, '__html__'):
        value = list(value)
        do_escape = False
        for idx, item in enumerate(value):
            if hasattr(item, '__html__'):
                do_escape = True
            else:
                value[idx] = unicode(item)
        if do_escape:
            d = escape(d)
        else:
            d = unicode(d)
        return d.join(value)

    # no html involved, to normal joining
    return soft_unicode(d).join(imap(soft_unicode, value))


def do_center(value, width=80):
    """Centers the value in a field of a given width."""
    return unicode(value).center(width)


@environmentfilter
def do_first(environment, seq):
    """Return the first item of a sequence."""
    try:
        return iter(seq).next()
    except StopIteration:
        return environment.undefined('No first item, sequence was empty.')


@environmentfilter
def do_last(environment, seq):
    """Return the last item of a sequence."""
    try:
        return iter(reversed(seq)).next()
    except StopIteration:
        return environment.undefined('No last item, sequence was empty.')


@environmentfilter
def do_random(environment, seq):
    """Return a random item from the sequence."""
    try:
        return choice(seq)
    except IndexError:
        return environment.undefined('No random item, sequence was empty.')


def do_filesizeformat(value, binary=False):
    """Format the value like a 'human-readable' file size (i.e. 13 KB,
    4.1 MB, 102 bytes, etc).  Per default decimal prefixes are used (mega,
    giga etc.), if the second parameter is set to `True` the binary
    prefixes are (mebi, gibi).
    """
    bytes = float(value)
    base = binary and 1024 or 1000
    middle = binary and 'i' or ''
    if bytes < base:
        return "%d Byte%s" % (bytes, bytes != 1 and 's' or '')
    elif bytes < base * base:
        return "%.1f K%sB" % (bytes / base, middle)
    elif bytes < base * base * base:
        return "%.1f M%sB" % (bytes / (base * base), middle)
    return "%.1f G%sB" % (bytes / (base * base * base), middle)


def do_pprint(value, verbose=False):
    """Pretty print a variable. Useful for debugging.

    With Jinja 1.2 onwards you can pass it a parameter.  If this parameter
    is truthy the output will be more verbose (this requires `pretty`)
    """
    return pformat(value, verbose=verbose)


@environmentfilter
def do_urlize(environment, value, trim_url_limit=None, nofollow=False):
    """Converts URLs in plain text into clickable links.

    If you pass the filter an additional integer it will shorten the urls
    to that number. Also a third argument exists that makes the urls
    "nofollow":

    .. sourcecode:: jinja

        {{ mytext|urlize(40, true) }}
            links are shortened to 40 chars and defined with rel="nofollow"
    """
    rv = urlize(value, trim_url_limit, nofollow)
    if environment.autoescape:
        rv = Markup(rv)
    return rv


def do_indent(s, width=4, indentfirst=False):
    """Return a copy of the passed string, each line indented by
    4 spaces. The first line is not indented. If you want to
    change the number of spaces or indent the first line too
    you can pass additional parameters to the filter:

    .. sourcecode:: jinja

        {{ mytext|indent(2, true) }}
            indent by two spaces and indent the first line too.
    """
    indention = u' ' * width
    rv = (u'\n' + indention).join(s.splitlines())
    if indentfirst:
        rv = indention + rv
    return rv


def do_truncate(s, length=255, killwords=False, end='...'):
    """Return a truncated copy of the string. The length is specified
    with the first parameter which defaults to ``255``. If the second
    parameter is ``true`` the filter will cut the text at length. Otherwise
    it will try to save the last word. If the text was in fact
    truncated it will append an ellipsis sign (``"..."``). If you want a
    different ellipsis sign than ``"..."`` you can specify it using the
    third parameter.

    .. sourcecode jinja::

        {{ mytext|truncate(300, false, '&raquo;') }}
            truncate mytext to 300 chars, don't split up words, use a
            right pointing double arrow as ellipsis sign.
    """
    if len(s) <= length:
        return s
    elif killwords:
        return s[:length] + end
    words = s.split(' ')
    result = []
    m = 0
    for word in words:
        m += len(word) + 1
        if m > length:
            break
        result.append(word)
    result.append(end)
    return u' '.join(result)


def do_wordwrap(s, width=79, break_long_words=True):
    """
    Return a copy of the string passed to the filter wrapped after
    ``79`` characters.  You can override this default using the first
    parameter.  If you set the second parameter to `false` Jinja will not
    split words apart if they are longer than `width`.
    """
    import textwrap
    return u'\n'.join(textwrap.wrap(s, width=width, expand_tabs=False,
                                   replace_whitespace=False,
                                   break_long_words=break_long_words))


def do_wordcount(s):
    """Count the words in that string."""
    return len(_word_re.findall(s))


def do_int(value, default=0):
    """Convert the value into an integer. If the
    conversion doesn't work it will return ``0``. You can
    override this default using the first parameter.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        # this quirk is necessary so that "42.23"|int gives 42.
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def do_float(value, default=0.0):
    """Convert the value into a floating point number. If the
    conversion doesn't work it will return ``0.0``. You can
    override this default using the first parameter.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def do_format(value, *args, **kwargs):
    """
    Apply python string formatting on an object:

    .. sourcecode:: jinja

        {{ "%s - %s"|format("Hello?", "Foo!") }}
            -> Hello? - Foo!
    """
    if args and kwargs:
        raise FilterArgumentError('can\'t handle positional and keyword '
                                  'arguments at the same time')
    return soft_unicode(value) % (kwargs or args)


def do_trim(value):
    """Strip leading and trailing whitespace."""
    return soft_unicode(value).strip()


def do_striptags(value):
    """Strip SGML/XML tags and replace adjacent whitespace by one space.
    """
    if hasattr(value, '__html__'):
        value = value.__html__()
    return Markup(unicode(value)).striptags()


def do_slice(value, slices, fill_with=None):
    """Slice an iterator and return a list of lists containing
    those items. Useful if you want to create a div containing
    three div tags that represent columns:

    .. sourcecode:: html+jinja

        <div class="columwrapper">
          {%- for column in items|slice(3) %}
            <ul class="column-{{ loop.index }}">
            {%- for item in column %}
              <li>{{ item }}</li>
            {%- endfor %}
            </ul>
          {%- endfor %}
        </div>

    If you pass it a second argument it's used to fill missing
    values on the last iteration.
    """
    seq = list(value)
    length = len(seq)
    items_per_slice = length // slices
    slices_with_extra = length % slices
    offset = 0
    for slice_number in xrange(slices):
        start = offset + slice_number * items_per_slice
        if slice_number < slices_with_extra:
            offset += 1
        end = offset + (slice_number + 1) * items_per_slice
        tmp = seq[start:end]
        if fill_with is not None and slice_number >= slices_with_extra:
            tmp.append(fill_with)
        yield tmp


def do_batch(value, linecount, fill_with=None):
    """
    A filter that batches items. It works pretty much like `slice`
    just the other way round. It returns a list of lists with the
    given number of items. If you provide a second parameter this
    is used to fill missing items. See this example:

    .. sourcecode:: html+jinja

        <table>
        {%- for row in items|batch(3, '&nbsp;') %}
          <tr>
          {%- for column in row %}
            <tr>{{ column }}</td>
          {%- endfor %}
          </tr>
        {%- endfor %}
        </table>
    """
    result = []
    tmp = []
    for item in value:
        if len(tmp) == linecount:
            yield tmp
            tmp = []
        tmp.append(item)
    if tmp:
        if fill_with is not None and len(tmp) < linecount:
            tmp += [fill_with] * (linecount - len(tmp))
        yield tmp


def do_round(value, precision=0, method='common'):
    """Round the number to a given precision. The first
    parameter specifies the precision (default is ``0``), the
    second the rounding method:

    - ``'common'`` rounds either up or down
    - ``'ceil'`` always rounds up
    - ``'floor'`` always rounds down

    If you don't specify a method ``'common'`` is used.

    .. sourcecode:: jinja

        {{ 42.55|round }}
            -> 43
        {{ 42.55|round(1, 'floor') }}
            -> 42.5
    """
    if not method in ('common', 'ceil', 'floor'):
        raise FilterArgumentError('method must be common, ceil or floor')
    if precision < 0:
        raise FilterArgumentError('precision must be a postive integer '
                                  'or zero.')
    if method == 'common':
        return round(value, precision)
    func = getattr(math, method)
    if precision:
        return func(value * 10 * precision) / (10 * precision)
    else:
        return func(value)


def do_sort(value, reverse=False):
    """Sort a sequence. Per default it sorts ascending, if you pass it
    true as first argument it will reverse the sorting.
    """
    return sorted(value, reverse=reverse)


@environmentfilter
def do_groupby(environment, value, attribute):
    """Group a sequence of objects by a common attribute.

    If you for example have a list of dicts or objects that represent persons
    with `gender`, `first_name` and `last_name` attributes and you want to
    group all users by genders you can do something like the following
    snippet:

    .. sourcecode:: html+jinja

        <ul>
        {% for group in persons|groupby('gender') %}
            <li>{{ group.grouper }}<ul>
            {% for person in group.list %}
                <li>{{ person.first_name }} {{ person.last_name }}</li>
            {% endfor %}</ul></li>
        {% endfor %}
        </ul>

    Additionally it's possible to use tuple unpacking for the grouper and
    list:

    .. sourcecode:: html+jinja

        <ul>
        {% for grouper, list in persons|groupby('gender') %}
            ...
        {% endfor %}
        </ul>

    As you can see the item we're grouping by is stored in the `grouper`
    attribute and the `list` contains all the objects that have this grouper
    in common.
    """
    expr = lambda x: environment.getitem(x, attribute)
    return sorted(map(_GroupTuple, groupby(sorted(value, key=expr), expr)))


class _GroupTuple(tuple):
    __slots__ = ()
    grouper = property(itemgetter(0))
    list = property(itemgetter(1))

    def __new__(cls, (key, value)):
        return tuple.__new__(cls, (key, list(value)))


def do_list(value):
    """Convert the value into a list.  If it was a string the returned list
    will be a list of characters.
    """
    return list(value)


def do_mark_safe(value):
    """Mark the value as safe which means that in an environment with automatic
    escaping enabled this variable will not be escaped.
    """
    return Markup(value)


def do_mark_unsafe(value):
    """Mark a value as unsafe.  This is the reverse operation for :func:`safe`."""
    return unicode(value)


def do_reverse(value):
    """Reverse the object or return an iterator the iterates over it the other
    way round.
    """
    if isinstance(value, basestring):
        return value[::-1]
    try:
        return reversed(value)
    except TypeError:
        try:
            rv = list(value)
            rv.reverse()
            return rv
        except TypeError:
            raise FilterArgumentError('argument must be iterable')


@environmentfilter
def do_attr(environment, obj, name):
    """Get an attribute of an object.  ``foo|attr("bar")`` works like
    ``foo["bar"]`` just that always an attribute is returned and items are not
    looked up.

    See :ref:`Notes on subscriptions <notes-on-subscriptions>` for more details.
    """
    try:
        name = str(name)
    except UnicodeError:
        pass
    else:
        try:
            value = getattr(obj, name)
        except AttributeError:
            pass
        else:
            if environment.sandboxed and not \
               environment.is_safe_attribute(obj, name, value):
                return environment.unsafe_undefined(obj, name)
            return value
    return environment.undefined(obj=obj, name=name)


FILTERS = {
    'attr':                 do_attr,
    'replace':              do_replace,
    'upper':                do_upper,
    'lower':                do_lower,
    'escape':               escape,
    'e':                    escape,
    'forceescape':          do_forceescape,
    'capitalize':           do_capitalize,
    'title':                do_title,
    'default':              do_default,
    'd':                    do_default,
    'join':                 do_join,
    'count':                len,
    'dictsort':             do_dictsort,
    'sort':                 do_sort,
    'length':               len,
    'reverse':              do_reverse,
    'center':               do_center,
    'indent':               do_indent,
    'title':                do_title,
    'capitalize':           do_capitalize,
    'first':                do_first,
    'last':                 do_last,
    'random':               do_random,
    'filesizeformat':       do_filesizeformat,
    'pprint':               do_pprint,
    'truncate':             do_truncate,
    'wordwrap':             do_wordwrap,
    'wordcount':            do_wordcount,
    'int':                  do_int,
    'float':                do_float,
    'string':               soft_unicode,
    'list':                 do_list,
    'urlize':               do_urlize,
    'format':               do_format,
    'trim':                 do_trim,
    'striptags':            do_striptags,
    'slice':                do_slice,
    'batch':                do_batch,
    'sum':                  sum,
    'abs':                  abs,
    'round':                do_round,
    'sort':                 do_sort,
    'groupby':              do_groupby,
    'safe':                 do_mark_safe,
    'xmlattr':              do_xmlattr
}

########NEW FILE########
__FILENAME__ = lexer
# -*- coding: utf-8 -*-
"""
    jinja2.lexer
    ~~~~~~~~~~~~

    This module implements a Jinja / Python combination lexer. The
    `Lexer` class provided by this module is used to do some preprocessing
    for Jinja.

    On the one hand it filters out invalid operators like the bitshift
    operators we don't allow in templates. On the other hand it separates
    template code and python code in expressions.

    :copyright: 2007-2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import re
from operator import itemgetter
from collections import deque
from jinja2.exceptions import TemplateSyntaxError
from jinja2.utils import LRUCache


# cache for the lexers. Exists in order to be able to have multiple
# environments with the same lexer
_lexer_cache = LRUCache(50)

# static regular expressions
whitespace_re = re.compile(r'\s+', re.U)
string_re = re.compile(r"('([^'\\]*(?:\\.[^'\\]*)*)'"
                       r'|"([^"\\]*(?:\\.[^"\\]*)*)")', re.S)
integer_re = re.compile(r'\d+')
name_re = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')
float_re = re.compile(r'(?<!\.)\d+\.\d+')
newline_re = re.compile(r'(\r\n|\r|\n)')

# bind operators to token types
operators = {
    '+':            'add',
    '-':            'sub',
    '/':            'div',
    '//':           'floordiv',
    '*':            'mul',
    '%':            'mod',
    '**':           'pow',
    '~':            'tilde',
    '[':            'lbracket',
    ']':            'rbracket',
    '(':            'lparen',
    ')':            'rparen',
    '{':            'lbrace',
    '}':            'rbrace',
    '==':           'eq',
    '!=':           'ne',
    '>':            'gt',
    '>=':           'gteq',
    '<':            'lt',
    '<=':           'lteq',
    '=':            'assign',
    '.':            'dot',
    ':':            'colon',
    '|':            'pipe',
    ',':            'comma',
    ';':            'semicolon'
}

reverse_operators = dict([(v, k) for k, v in operators.iteritems()])
assert len(operators) == len(reverse_operators), 'operators dropped'
operator_re = re.compile('(%s)' % '|'.join(re.escape(x) for x in
                         sorted(operators, key=lambda x: -len(x))))


def count_newlines(value):
    """Count the number of newline characters in the string.  This is
    useful for extensions that filter a stream.
    """
    return len(newline_re.findall(value))


class Failure(object):
    """Class that raises a `TemplateSyntaxError` if called.
    Used by the `Lexer` to specify known errors.
    """

    def __init__(self, message, cls=TemplateSyntaxError):
        self.message = message
        self.error_class = cls

    def __call__(self, lineno, filename):
        raise self.error_class(self.message, lineno, filename)


class Token(tuple):
    """Token class."""
    __slots__ = ()
    lineno, type, value = (property(itemgetter(x)) for x in range(3))

    def __new__(cls, lineno, type, value):
        return tuple.__new__(cls, (lineno, intern(str(type)), value))

    def __str__(self):
        if self.type in reverse_operators:
            return reverse_operators[self.type]
        elif self.type is 'name':
            return self.value
        return self.type

    def test(self, expr):
        """Test a token against a token expression.  This can either be a
        token type or ``'token_type:token_value'``.  This can only test
        against string values and types.
        """
        # here we do a regular string equality check as test_any is usually
        # passed an iterable of not interned strings.
        if self.type == expr:
            return True
        elif ':' in expr:
            return expr.split(':', 1) == [self.type, self.value]
        return False

    def test_any(self, *iterable):
        """Test against multiple token expressions."""
        for expr in iterable:
            if self.test(expr):
                return True
        return False

    def __repr__(self):
        return 'Token(%r, %r, %r)' % (
            self.lineno,
            self.type,
            self.value
        )


class TokenStreamIterator(object):
    """The iterator for tokenstreams.  Iterate over the stream
    until the eof token is reached.
    """

    def __init__(self, stream):
        self.stream = stream

    def __iter__(self):
        return self

    def next(self):
        token = self.stream.current
        if token.type == 'eof':
            self.stream.close()
            raise StopIteration()
        self.stream.next()
        return token


class TokenStream(object):
    """A token stream is an iterable that yields :class:`Token`\s.  The
    parser however does not iterate over it but calls :meth:`next` to go
    one token ahead.  The current active token is stored as :attr:`current`.
    """

    def __init__(self, generator, name, filename):
        self._next = iter(generator).next
        self._pushed = deque()
        self.name = name
        self.filename = filename
        self.closed = False
        self.current = Token(1, 'initial', '')
        self.next()

    def __iter__(self):
        return TokenStreamIterator(self)

    def __nonzero__(self):
        """Are we at the end of the stream?"""
        return bool(self._pushed) or self.current.type != 'eof'

    eos = property(lambda x: not x.__nonzero__(), doc=__nonzero__.__doc__)

    def push(self, token):
        """Push a token back to the stream."""
        self._pushed.append(token)

    def look(self):
        """Look at the next token."""
        old_token = self.next()
        result = self.current
        self.push(result)
        self.current = old_token
        return result

    def skip(self, n=1):
        """Got n tokens ahead."""
        for x in xrange(n):
            self.next()

    def next_if(self, expr):
        """Perform the token test and return the token if it matched.
        Otherwise the return value is `None`.
        """
        if self.current.test(expr):
            return self.next()

    def skip_if(self, expr):
        """Like :meth:`next_if` but only returns `True` or `False`."""
        return self.next_if(expr) is not None

    def next(self):
        """Go one token ahead and return the old one"""
        rv = self.current
        if self._pushed:
            self.current = self._pushed.popleft()
        elif self.current.type is not 'eof':
            try:
                self.current = self._next()
            except StopIteration:
                self.close()
        return rv

    def close(self):
        """Close the stream."""
        self.current = Token(self.current.lineno, 'eof', '')
        self._next = None
        self.closed = True

    def expect(self, expr):
        """Expect a given token type and return it.  This accepts the same
        argument as :meth:`jinja2.lexer.Token.test`.
        """
        if not self.current.test(expr):
            if ':' in expr:
                expr = expr.split(':')[1]
            if self.current.type is 'eof':
                raise TemplateSyntaxError('unexpected end of template, '
                                          'expected %r.' % expr,
                                          self.current.lineno,
                                          self.name, self.filename)
            raise TemplateSyntaxError("expected token %r, got %r" %
                                      (expr, str(self.current)),
                                      self.current.lineno,
                                      self.name, self.filename)
        try:
            return self.current
        finally:
            self.next()


def get_lexer(environment):
    """Return a lexer which is probably cached."""
    key = (environment.block_start_string,
           environment.block_end_string,
           environment.variable_start_string,
           environment.variable_end_string,
           environment.comment_start_string,
           environment.comment_end_string,
           environment.line_statement_prefix,
           environment.trim_blocks,
           environment.newline_sequence)
    lexer = _lexer_cache.get(key)
    if lexer is None:
        lexer = Lexer(environment)
        _lexer_cache[key] = lexer
    return lexer


class Lexer(object):
    """Class that implements a lexer for a given environment. Automatically
    created by the environment class, usually you don't have to do that.

    Note that the lexer is not automatically bound to an environment.
    Multiple environments can share the same lexer.
    """

    def __init__(self, environment):
        # shortcuts
        c = lambda x: re.compile(x, re.M | re.S)
        e = re.escape

        # lexing rules for tags
        tag_rules = [
            (whitespace_re, 'whitespace', None),
            (float_re, 'float', None),
            (integer_re, 'integer', None),
            (name_re, 'name', None),
            (string_re, 'string', None),
            (operator_re, 'operator', None)
        ]

        # assamble the root lexing rule. because "|" is ungreedy
        # we have to sort by length so that the lexer continues working
        # as expected when we have parsing rules like <% for block and
        # <%= for variables. (if someone wants asp like syntax)
        # variables are just part of the rules if variable processing
        # is required.
        root_tag_rules = [
            ('comment',     environment.comment_start_string),
            ('block',       environment.block_start_string),
            ('variable',    environment.variable_start_string)
        ]
        root_tag_rules.sort(key=lambda x: -len(x[1]))

        # now escape the rules.  This is done here so that the escape
        # signs don't count for the lengths of the tags.
        root_tag_rules = [(a, e(b)) for a, b in root_tag_rules]

        # if we have a line statement prefix we need an extra rule for
        # that.  We add this rule *after* all the others.
        if environment.line_statement_prefix is not None:
            prefix = e(environment.line_statement_prefix)
            root_tag_rules.insert(0, ('linestatement', '^\s*' + prefix))

        # block suffix if trimming is enabled
        block_suffix_re = environment.trim_blocks and '\\n?' or ''

        self.newline_sequence = environment.newline_sequence

        # global lexing rules
        self.rules = {
            'root': [
                # directives
                (c('(.*?)(?:%s)' % '|'.join(
                    ['(?P<raw_begin>(?:\s*%s\-|%s)\s*raw\s*%s)' % (
                        e(environment.block_start_string),
                        e(environment.block_start_string),
                        e(environment.block_end_string)
                    )] + [
                        '(?P<%s_begin>\s*%s\-|%s)' % (n, r, r)
                        for n, r in root_tag_rules
                    ])), ('data', '#bygroup'), '#bygroup'),
                # data
                (c('.+'), 'data', None)
            ],
            # comments
            'comment_begin': [
                (c(r'(.*?)((?:\-%s\s*|%s)%s)' % (
                    e(environment.comment_end_string),
                    e(environment.comment_end_string),
                    block_suffix_re
                )), ('comment', 'comment_end'), '#pop'),
                (c('(.)'), (Failure('Missing end of comment tag'),), None)
            ],
            # blocks
            'block_begin': [
                (c('(?:\-%s\s*|%s)%s' % (
                    e(environment.block_end_string),
                    e(environment.block_end_string),
                    block_suffix_re
                )), 'block_end', '#pop'),
            ] + tag_rules,
            # variables
            'variable_begin': [
                (c('\-%s\s*|%s' % (
                    e(environment.variable_end_string),
                    e(environment.variable_end_string)
                )), 'variable_end', '#pop')
            ] + tag_rules,
            # raw block
            'raw_begin': [
                (c('(.*?)((?:\s*%s\-|%s)\s*endraw\s*(?:\-%s\s*|%s%s))' % (
                    e(environment.block_start_string),
                    e(environment.block_start_string),
                    e(environment.block_end_string),
                    e(environment.block_end_string),
                    block_suffix_re
                )), ('data', 'raw_end'), '#pop'),
                (c('(.)'), (Failure('Missing end of raw directive'),), None)
            ],
            # line statements
            'linestatement_begin': [
                (c(r'\s*(\n|$)'), 'linestatement_end', '#pop')
            ] + tag_rules
        }

    def _normalize_newlines(self, value):
        """Called for strings and template data to normlize it to unicode."""
        return newline_re.sub(self.newline_sequence, value)

    def tokenize(self, source, name=None, filename=None, state=None):
        """Calls tokeniter + tokenize and wraps it in a token stream.
        """
        stream = self.tokeniter(source, name, filename, state)
        return TokenStream(self.wrap(stream, name, filename), name, filename)

    def wrap(self, stream, name=None, filename=None):
        """This is called with the stream as returned by `tokenize` and wraps
        every token in a :class:`Token` and converts the value.
        """
        for lineno, token, value in stream:
            if token in ('comment_begin', 'comment', 'comment_end',
                         'whitespace'):
                continue
            elif token == 'linestatement_begin':
                token = 'block_begin'
            elif token == 'linestatement_end':
                token = 'block_end'
            # we are not interested in those tokens in the parser
            elif token in ('raw_begin', 'raw_end'):
                continue
            elif token == 'data':
                value = self._normalize_newlines(value)
            elif token == 'keyword':
                token = value
            elif token == 'name':
                value = str(value)
            elif token == 'string':
                # try to unescape string
                try:
                    value = self._normalize_newlines(value[1:-1]) \
                        .encode('ascii', 'backslashreplace') \
                        .decode('unicode-escape')
                except Exception, e:
                    msg = str(e).split(':')[-1].strip()
                    raise TemplateSyntaxError(msg, lineno, name, filename)
                # if we can express it as bytestring (ascii only)
                # we do that for support of semi broken APIs
                # as datetime.datetime.strftime
                try:
                    value = str(value)
                except UnicodeError:
                    pass
            elif token == 'integer':
                value = int(value)
            elif token == 'float':
                value = float(value)
            elif token == 'operator':
                token = operators[value]
            yield Token(lineno, token, value)

    def tokeniter(self, source, name, filename=None, state=None):
        """This method tokenizes the text and returns the tokens in a
        generator.  Use this method if you just want to tokenize a template.
        """
        source = '\n'.join(unicode(source).splitlines())
        pos = 0
        lineno = 1
        stack = ['root']
        if state is not None and state != 'root':
            assert state in ('variable', 'block'), 'invalid state'
            stack.append(state + '_begin')
        else:
            state = 'root'
        statetokens = self.rules[stack[-1]]
        source_length = len(source)

        balancing_stack = []

        while 1:
            # tokenizer loop
            for regex, tokens, new_state in statetokens:
                m = regex.match(source, pos)
                # if no match we try again with the next rule
                if m is None:
                    continue

                # we only match blocks and variables if brances / parentheses
                # are balanced. continue parsing with the lower rule which
                # is the operator rule. do this only if the end tags look
                # like operators
                if balancing_stack and \
                   tokens in ('variable_end', 'block_end',
                              'linestatement_end'):
                    continue

                # tuples support more options
                if isinstance(tokens, tuple):
                    for idx, token in enumerate(tokens):
                        # failure group
                        if token.__class__ is Failure:
                            raise token(lineno, filename)
                        # bygroup is a bit more complex, in that case we
                        # yield for the current token the first named
                        # group that matched
                        elif token == '#bygroup':
                            for key, value in m.groupdict().iteritems():
                                if value is not None:
                                    yield lineno, key, value
                                    lineno += value.count('\n')
                                    break
                            else:
                                raise RuntimeError('%r wanted to resolve '
                                                   'the token dynamically'
                                                   ' but no group matched'
                                                   % regex)
                        # normal group
                        else:
                            data = m.group(idx + 1)
                            if data:
                                yield lineno, token, data
                            lineno += data.count('\n')

                # strings as token just are yielded as it.
                else:
                    data = m.group()
                    # update brace/parentheses balance
                    if tokens == 'operator':
                        if data == '{':
                            balancing_stack.append('}')
                        elif data == '(':
                            balancing_stack.append(')')
                        elif data == '[':
                            balancing_stack.append(']')
                        elif data in ('}', ')', ']'):
                            if not balancing_stack:
                                raise TemplateSyntaxError('unexpected "%s"' %
                                                          data, lineno, name,
                                                          filename)
                            expected_op = balancing_stack.pop()
                            if expected_op != data:
                                raise TemplateSyntaxError('unexpected "%s", '
                                                          'expected "%s"' %
                                                          (data, expected_op),
                                                          lineno, name,
                                                          filename)
                    # yield items
                    yield lineno, tokens, data
                    lineno += data.count('\n')

                # fetch new position into new variable so that we can check
                # if there is a internal parsing error which would result
                # in an infinite loop
                pos2 = m.end()

                # handle state changes
                if new_state is not None:
                    # remove the uppermost state
                    if new_state == '#pop':
                        stack.pop()
                    # resolve the new state by group checking
                    elif new_state == '#bygroup':
                        for key, value in m.groupdict().iteritems():
                            if value is not None:
                                stack.append(key)
                                break
                        else:
                            raise RuntimeError('%r wanted to resolve the '
                                               'new state dynamically but'
                                               ' no group matched' %
                                               regex)
                    # direct state name given
                    else:
                        stack.append(new_state)
                    statetokens = self.rules[stack[-1]]
                # we are still at the same position and no stack change.
                # this means a loop without break condition, avoid that and
                # raise error
                elif pos2 == pos:
                    raise RuntimeError('%r yielded empty string without '
                                       'stack change' % regex)
                # publish new function and start again
                pos = pos2
                break
            # if loop terminated without break we havn't found a single match
            # either we are at the end of the file or we have a problem
            else:
                # end of text
                if pos >= source_length:
                    return
                # something went wrong
                raise TemplateSyntaxError('unexpected char %r at %d' %
                                          (source[pos], pos), lineno,
                                          name, filename)

########NEW FILE########
__FILENAME__ = loaders
# -*- coding: utf-8 -*-
"""
    jinja2.loaders
    ~~~~~~~~~~~~~~

    Jinja loader classes.

    :copyright: 2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from os import path
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import LRUCache, open_if_exists


def split_template_path(template):
    """Split a path into segments and perform a sanity check.  If it detects
    '..' in the path it will raise a `TemplateNotFound` error.
    """
    pieces = []
    for piece in template.split('/'):
        if path.sep in piece \
           or (path.altsep and path.altsep in piece) or \
           piece == path.pardir:
            raise TemplateNotFound(template)
        elif piece and piece != '.':
            pieces.append(piece)
    return pieces


class BaseLoader(object):
    """Baseclass for all loaders.  Subclass this and override `get_source` to
    implement a custom loading mechanism.  The environment provides a
    `get_template` method that calls the loader's `load` method to get the
    :class:`Template` object.

    A very basic example for a loader that looks up templates on the file
    system could look like this::

        from jinja2 import BaseLoader, TemplateNotFound
        from os.path import join, exists, getmtime

        class MyLoader(BaseLoader):

            def __init__(self, path):
                self.path = path

            def get_source(self, environment, template):
                path = join(self.path, template)
                if not exists(path):
                    raise TemplateNotFound(template)
                mtime = getmtime(path)
                with file(path) as f:
                    source = f.read().decode('utf-8')
                return source, path, lambda: mtime == getmtime(path)
    """

    def get_source(self, environment, template):
        """Get the template source, filename and reload helper for a template.
        It's passed the environment and template name and has to return a
        tuple in the form ``(source, filename, uptodate)`` or raise a
        `TemplateNotFound` error if it can't locate the template.

        The source part of the returned tuple must be the source of the
        template as unicode string or a ASCII bytestring.  The filename should
        be the name of the file on the filesystem if it was loaded from there,
        otherwise `None`.  The filename is used by python for the tracebacks
        if no loader extension is used.

        The last item in the tuple is the `uptodate` function.  If auto
        reloading is enabled it's always called to check if the template
        changed.  No arguments are passed so the function must store the
        old state somewhere (for example in a closure).  If it returns `False`
        the template will be reloaded.
        """
        raise TemplateNotFound(template)

    def load(self, environment, name, globals=None):
        """Loads a template.  This method looks up the template in the cache
        or loads one by calling :meth:`get_source`.  Subclasses should not
        override this method as loaders working on collections of other
        loaders (such as :class:`PrefixLoader` or :class:`ChoiceLoader`)
        will not call this method but `get_source` directly.
        """
        code = None
        if globals is None:
            globals = {}

        # first we try to get the source for this template together
        # with the filename and the uptodate function.
        source, filename, uptodate = self.get_source(environment, name)

        # try to load the code from the bytecode cache if there is a
        # bytecode cache configured.
        bcc = environment.bytecode_cache
        if bcc is not None:
            bucket = bcc.get_bucket(environment, name, filename, source)
            code = bucket.code

        # if we don't have code so far (not cached, no longer up to
        # date) etc. we compile the template
        if code is None:
            code = environment.compile(source, name, filename)

        # if the bytecode cache is available and the bucket doesn't
        # have a code so far, we give the bucket the new code and put
        # it back to the bytecode cache.
        if bcc is not None and bucket.code is None:
            bucket.code = code
            bcc.set_bucket(bucket)

        return environment.template_class.from_code(environment, code,
                                                    globals, uptodate)


class FileSystemLoader(BaseLoader):
    """Loads templates from the file system.  This loader can find templates
    in folders on the file system and is the preferred way to load them.

    The loader takes the path to the templates as string, or if multiple
    locations are wanted a list of them which is then looked up in the
    given order:

    >>> loader = FileSystemLoader('/path/to/templates')
    >>> loader = FileSystemLoader(['/path/to/templates', '/other/path'])

    Per default the template encoding is ``'utf-8'`` which can be changed
    by setting the `encoding` parameter to something else.
    """

    def __init__(self, searchpath, encoding='utf-8'):
        if isinstance(searchpath, basestring):
            searchpath = [searchpath]
        self.searchpath = list(searchpath)
        self.encoding = encoding

    def get_source(self, environment, template):
        pieces = split_template_path(template)
        for searchpath in self.searchpath:
            filename = path.join(searchpath, *pieces)
            f = open_if_exists(filename)
            if f is None:
                continue
            try:
                contents = f.read().decode(self.encoding)
            finally:
                f.close()

            mtime = path.getmtime(filename)
            def uptodate():
                try:
                    return path.getmtime(filename) == mtime
                except OSError:
                    return False
            return contents, filename, uptodate
        raise TemplateNotFound(template)


class PackageLoader(BaseLoader):
    """Load templates from python eggs or packages.  It is constructed with
    the name of the python package and the path to the templates in that
    package:

    >>> loader = PackageLoader('mypackage', 'views')

    If the package path is not given, ``'templates'`` is assumed.

    Per default the template encoding is ``'utf-8'`` which can be changed
    by setting the `encoding` parameter to something else.  Due to the nature
    of eggs it's only possible to reload templates if the package was loaded
    from the file system and not a zip file.
    """

    def __init__(self, package_name, package_path='templates',
                 encoding='utf-8'):
        from pkg_resources import DefaultProvider, ResourceManager, \
                                  get_provider
        provider = get_provider(package_name)
        self.encoding = encoding
        self.manager = ResourceManager()
        self.filesystem_bound = isinstance(provider, DefaultProvider)
        self.provider = provider
        self.package_path = package_path

    def get_source(self, environment, template):
        pieces = split_template_path(template)
        p = '/'.join((self.package_path,) + tuple(pieces))
        if not self.provider.has_resource(p):
            raise TemplateNotFound(template)

        filename = uptodate = None
        if self.filesystem_bound:
            filename = self.provider.get_resource_filename(self.manager, p)
            mtime = path.getmtime(filename)
            def uptodate():
                try:
                    return path.getmtime(filename) == mtime
                except OSError:
                    return False

        source = self.provider.get_resource_string(self.manager, p)
        return source.decode(self.encoding), filename, uptodate


class DictLoader(BaseLoader):
    """Loads a template from a python dict.  It's passed a dict of unicode
    strings bound to template names.  This loader is useful for unittesting:

    >>> loader = DictLoader({'index.html': 'source here'})

    Because auto reloading is rarely useful this is disabled per default.
    """

    def __init__(self, mapping):
        self.mapping = mapping

    def get_source(self, environment, template):
        if template in self.mapping:
            source = self.mapping[template]
            return source, None, lambda: source != self.mapping.get(template)
        raise TemplateNotFound(template)


class FunctionLoader(BaseLoader):
    """A loader that is passed a function which does the loading.  The
    function becomes the name of the template passed and has to return either
    an unicode string with the template source, a tuple in the form ``(source,
    filename, uptodatefunc)`` or `None` if the template does not exist.

    >>> def load_template(name):
    ...     if name == 'index.html'
    ...         return '...'
    ...
    >>> loader = FunctionLoader(load_template)

    The `uptodatefunc` is a function that is called if autoreload is enabled
    and has to return `True` if the template is still up to date.  For more
    details have a look at :meth:`BaseLoader.get_source` which has the same
    return value.
    """

    def __init__(self, load_func):
        self.load_func = load_func

    def get_source(self, environment, template):
        rv = self.load_func(template)
        if rv is None:
            raise TemplateNotFound(template)
        elif isinstance(rv, basestring):
            return rv, None, None
        return rv


class PrefixLoader(BaseLoader):
    """A loader that is passed a dict of loaders where each loader is bound
    to a prefix.  The prefix is delimited from the template by a slash per
    default, which can be changed by setting the `delimiter` argument to
    something else.

    >>> loader = PrefixLoader({
    ...     'app1':     PackageLoader('mypackage.app1'),
    ...     'app2':     PackageLoader('mypackage.app2')
    ... })

    By loading ``'app1/index.html'`` the file from the app1 package is loaded,
    by loading ``'app2/index.html'`` the file from the second.
    """

    def __init__(self, mapping, delimiter='/'):
        self.mapping = mapping
        self.delimiter = delimiter

    def get_source(self, environment, template):
        try:
            prefix, template = template.split(self.delimiter, 1)
            loader = self.mapping[prefix]
        except (ValueError, KeyError):
            raise TemplateNotFound(template)
        return loader.get_source(environment, template)


class ChoiceLoader(BaseLoader):
    """This loader works like the `PrefixLoader` just that no prefix is
    specified.  If a template could not be found by one loader the next one
    is tried.

    >>> loader = ChoiceLoader([
    ...     FileSystemLoader('/path/to/user/templates'),
    ...     PackageLoader('mypackage')
    ... ])

    This is useful if you want to allow users to override builtin templates
    from a different location.
    """

    def __init__(self, loaders):
        self.loaders = loaders

    def get_source(self, environment, template):
        for loader in self.loaders:
            try:
                return loader.get_source(environment, template)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(template)

########NEW FILE########
__FILENAME__ = nodes
# -*- coding: utf-8 -*-
"""
    jinja2.nodes
    ~~~~~~~~~~~~

    This module implements additional nodes derived from the ast base node.

    It also provides some node tree helper functions like `in_lineno` and
    `get_nodes` used by the parser and translator in order to normalize
    python and jinja nodes.

    :copyright: 2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import operator
from itertools import chain, izip
from collections import deque
from jinja2.utils import Markup


_binop_to_func = {
    '*':        operator.mul,
    '/':        operator.truediv,
    '//':       operator.floordiv,
    '**':       operator.pow,
    '%':        operator.mod,
    '+':        operator.add,
    '-':        operator.sub
}

_uaop_to_func = {
    'not':      operator.not_,
    '+':        operator.pos,
    '-':        operator.neg
}

_cmpop_to_func = {
    'eq':       operator.eq,
    'ne':       operator.ne,
    'gt':       operator.gt,
    'gteq':     operator.ge,
    'lt':       operator.lt,
    'lteq':     operator.le,
    'in':       lambda a, b: a in b,
    'notin':    lambda a, b: a not in b
}


class Impossible(Exception):
    """Raised if the node could not perform a requested action."""


class NodeType(type):
    """A metaclass for nodes that handles the field and attribute
    inheritance.  fields and attributes from the parent class are
    automatically forwarded to the child."""

    def __new__(cls, name, bases, d):
        for attr in 'fields', 'attributes':
            storage = []
            storage.extend(getattr(bases[0], attr, ()))
            storage.extend(d.get(attr, ()))
            assert len(bases) == 1, 'multiple inheritance not allowed'
            assert len(storage) == len(set(storage)), 'layout conflict'
            d[attr] = tuple(storage)
        d.setdefault('abstract', False)
        return type.__new__(cls, name, bases, d)


class Node(object):
    """Baseclass for all Jinja2 nodes.  There are a number of nodes available
    of different types.  There are three major types:

    -   :class:`Stmt`: statements
    -   :class:`Expr`: expressions
    -   :class:`Helper`: helper nodes
    -   :class:`Template`: the outermost wrapper node

    All nodes have fields and attributes.  Fields may be other nodes, lists,
    or arbitrary values.  Fields are passed to the constructor as regular
    positional arguments, attributes as keyword arguments.  Each node has
    two attributes: `lineno` (the line number of the node) and `environment`.
    The `environment` attribute is set at the end of the parsing process for
    all nodes automatically.
    """
    __metaclass__ = NodeType
    fields = ()
    attributes = ('lineno', 'environment')
    abstract = True

    def __init__(self, *fields, **attributes):
        if self.abstract:
            raise TypeError('abstract nodes are not instanciable')
        if fields:
            if len(fields) != len(self.fields):
                if not self.fields:
                    raise TypeError('%r takes 0 arguments' %
                                    self.__class__.__name__)
                raise TypeError('%r takes 0 or %d argument%s' % (
                    self.__class__.__name__,
                    len(self.fields),
                    len(self.fields) != 1 and 's' or ''
                ))
            for name, arg in izip(self.fields, fields):
                setattr(self, name, arg)
        for attr in self.attributes:
            setattr(self, attr, attributes.pop(attr, None))
        if attributes:
            raise TypeError('unknown attribute %r' %
                            iter(attributes).next())

    def iter_fields(self, exclude=None, only=None):
        """This method iterates over all fields that are defined and yields
        ``(key, value)`` tuples.  Per default all fields are returned, but
        it's possible to limit that to some fields by providing the `only`
        parameter or to exclude some using the `exclude` parameter.  Both
        should be sets or tuples of field names.
        """
        for name in self.fields:
            if (exclude is only is None) or \
               (exclude is not None and name not in exclude) or \
               (only is not None and name in only):
                try:
                    yield name, getattr(self, name)
                except AttributeError:
                    pass

    def iter_child_nodes(self, exclude=None, only=None):
        """Iterates over all direct child nodes of the node.  This iterates
        over all fields and yields the values of they are nodes.  If the value
        of a field is a list all the nodes in that list are returned.
        """
        for field, item in self.iter_fields(exclude, only):
            if isinstance(item, list):
                for n in item:
                    if isinstance(n, Node):
                        yield n
            elif isinstance(item, Node):
                yield item

    def find(self, node_type):
        """Find the first node of a given type.  If no such node exists the
        return value is `None`.
        """
        for result in self.find_all(node_type):
            return result

    def find_all(self, node_type):
        """Find all the nodes of a given type."""
        for child in self.iter_child_nodes():
            if isinstance(child, node_type):
                yield child
            for result in child.find_all(node_type):
                yield result

    def set_ctx(self, ctx):
        """Reset the context of a node and all child nodes.  Per default the
        parser will all generate nodes that have a 'load' context as it's the
        most common one.  This method is used in the parser to set assignment
        targets and other nodes to a store context.
        """
        todo = deque([self])
        while todo:
            node = todo.popleft()
            if 'ctx' in node.fields:
                node.ctx = ctx
            todo.extend(node.iter_child_nodes())
        return self

    def set_lineno(self, lineno, override=False):
        """Set the line numbers of the node and children."""
        todo = deque([self])
        while todo:
            node = todo.popleft()
            if 'lineno' in node.attributes:
                if node.lineno is None or override:
                    node.lineno = lineno
            todo.extend(node.iter_child_nodes())
        return self

    def set_environment(self, environment):
        """Set the environment for all nodes."""
        todo = deque([self])
        while todo:
            node = todo.popleft()
            node.environment = environment
            todo.extend(node.iter_child_nodes())
        return self

    def __eq__(self, other):
        return type(self) is type(other) and \
               tuple(self.iter_fields()) == tuple(other.iter_fields())

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join('%s=%r' % (arg, getattr(self, arg, None)) for
                      arg in self.fields)
        )


class Stmt(Node):
    """Base node for all statements."""
    abstract = True


class Helper(Node):
    """Nodes that exist in a specific context only."""
    abstract = True


class Template(Node):
    """Node that represents a template.  This must be the outermost node that
    is passed to the compiler.
    """
    fields = ('body',)


class Output(Stmt):
    """A node that holds multiple expressions which are then printed out.
    This is used both for the `print` statement and the regular template data.
    """
    fields = ('nodes',)


class Extends(Stmt):
    """Represents an extends statement."""
    fields = ('template',)


class For(Stmt):
    """The for loop.  `target` is the target for the iteration (usually a
    :class:`Name` or :class:`Tuple`), `iter` the iterable.  `body` is a list
    of nodes that are used as loop-body, and `else_` a list of nodes for the
    `else` block.  If no else node exists it has to be an empty list.

    For filtered nodes an expression can be stored as `test`, otherwise `None`.
    """
    fields = ('target', 'iter', 'body', 'else_', 'test', 'recursive')


class If(Stmt):
    """If `test` is true, `body` is rendered, else `else_`."""
    fields = ('test', 'body', 'else_')


class Macro(Stmt):
    """A macro definition.  `name` is the name of the macro, `args` a list of
    arguments and `defaults` a list of defaults if there are any.  `body` is
    a list of nodes for the macro body.
    """
    fields = ('name', 'args', 'defaults', 'body')


class CallBlock(Stmt):
    """Like a macro without a name but a call instead.  `call` is called with
    the unnamed macro as `caller` argument this node holds.
    """
    fields = ('call', 'args', 'defaults', 'body')


class FilterBlock(Stmt):
    """Node for filter sections."""
    fields = ('body', 'filter')


class Block(Stmt):
    """A node that represents a block."""
    fields = ('name', 'body')


class Include(Stmt):
    """A node that represents the include tag."""
    fields = ('template', 'with_context')


class Import(Stmt):
    """A node that represents the import tag."""
    fields = ('template', 'target', 'with_context')


class FromImport(Stmt):
    """A node that represents the from import tag.  It's important to not
    pass unsafe names to the name attribute.  The compiler translates the
    attribute lookups directly into getattr calls and does *not* use the
    subscript callback of the interface.  As exported variables may not
    start with double underscores (which the parser asserts) this is not a
    problem for regular Jinja code, but if this node is used in an extension
    extra care must be taken.

    The list of names may contain tuples if aliases are wanted.
    """
    fields = ('template', 'names', 'with_context')


class ExprStmt(Stmt):
    """A statement that evaluates an expression and discards the result."""
    fields = ('node',)


class Assign(Stmt):
    """Assigns an expression to a target."""
    fields = ('target', 'node')


class Expr(Node):
    """Baseclass for all expressions."""
    abstract = True

    def as_const(self):
        """Return the value of the expression as constant or raise
        :exc:`Impossible` if this was not possible:

        >>> Add(Const(23), Const(42)).as_const()
        65
        >>> Add(Const(23), Name('var', 'load')).as_const()
        Traceback (most recent call last):
          ...
        Impossible

        This requires the `environment` attribute of all nodes to be
        set to the environment that created the nodes.
        """
        raise Impossible()

    def can_assign(self):
        """Check if it's possible to assign something to this node."""
        return False


class BinExpr(Expr):
    """Baseclass for all binary expressions."""
    fields = ('left', 'right')
    operator = None
    abstract = True

    def as_const(self):
        f = _binop_to_func[self.operator]
        try:
            return f(self.left.as_const(), self.right.as_const())
        except:
            raise Impossible()


class UnaryExpr(Expr):
    """Baseclass for all unary expressions."""
    fields = ('node',)
    operator = None
    abstract = True

    def as_const(self):
        f = _uaop_to_func[self.operator]
        try:
            return f(self.node.as_const())
        except:
            raise Impossible()


class Name(Expr):
    """Looks up a name or stores a value in a name.
    The `ctx` of the node can be one of the following values:

    -   `store`: store a value in the name
    -   `load`: load that name
    -   `param`: like `store` but if the name was defined as function parameter.
    """
    fields = ('name', 'ctx')

    def can_assign(self):
        return self.name not in ('true', 'false', 'none',
                                 'True', 'False', 'None')


class Literal(Expr):
    """Baseclass for literals."""
    abstract = True


class Const(Literal):
    """All constant values.  The parser will return this node for simple
    constants such as ``42`` or ``"foo"`` but it can be used to store more
    complex values such as lists too.  Only constants with a safe
    representation (objects where ``eval(repr(x)) == x`` is true).
    """
    fields = ('value',)

    def as_const(self):
        return self.value

    @classmethod
    def from_untrusted(cls, value, lineno=None, environment=None):
        """Return a const object if the value is representable as
        constant value in the generated code, otherwise it will raise
        an `Impossible` exception.
        """
        from compiler import has_safe_repr
        if not has_safe_repr(value):
            raise Impossible()
        return cls(value, lineno=lineno, environment=environment)


class TemplateData(Literal):
    """A constant template string."""
    fields = ('data',)

    def as_const(self):
        if self.environment.autoescape:
            return Markup(self.data)
        return self.data


class Tuple(Literal):
    """For loop unpacking and some other things like multiple arguments
    for subscripts.  Like for :class:`Name` `ctx` specifies if the tuple
    is used for loading the names or storing.
    """
    fields = ('items', 'ctx')

    def as_const(self):
        return tuple(x.as_const() for x in self.items)

    def can_assign(self):
        for item in self.items:
            if not item.can_assign():
                return False
        return True


class List(Literal):
    """Any list literal such as ``[1, 2, 3]``"""
    fields = ('items',)

    def as_const(self):
        return [x.as_const() for x in self.items]


class Dict(Literal):
    """Any dict literal such as ``{1: 2, 3: 4}``.  The items must be a list of
    :class:`Pair` nodes.
    """
    fields = ('items',)

    def as_const(self):
        return dict(x.as_const() for x in self.items)


class Pair(Helper):
    """A key, value pair for dicts."""
    fields = ('key', 'value')

    def as_const(self):
        return self.key.as_const(), self.value.as_const()


class Keyword(Helper):
    """A key, value pair for keyword arguments where key is a string."""
    fields = ('key', 'value')

    def as_const(self):
        return self.key, self.value.as_const()


class CondExpr(Expr):
    """A conditional expression (inline if expression).  (``{{
    foo if bar else baz }}``)
    """
    fields = ('test', 'expr1', 'expr2')

    def as_const(self):
        if self.test.as_const():
            return self.expr1.as_const()

        # if we evaluate to an undefined object, we better do that at runtime
        if self.expr2 is None:
            raise Impossible()

        return self.expr2.as_const()


class Filter(Expr):
    """This node applies a filter on an expression.  `name` is the name of
    the filter, the rest of the fields are the same as for :class:`Call`.

    If the `node` of a filter is `None` the contents of the last buffer are
    filtered.  Buffers are created by macros and filter blocks.
    """
    fields = ('node', 'name', 'args', 'kwargs', 'dyn_args', 'dyn_kwargs')

    def as_const(self, obj=None):
        if self.node is obj is None:
            raise Impossible()
        filter = self.environment.filters.get(self.name)
        if filter is None or getattr(filter, 'contextfilter', False):
            raise Impossible()
        if obj is None:
            obj = self.node.as_const()
        args = [x.as_const() for x in self.args]
        if getattr(filter, 'environmentfilter', False):
            args.insert(0, self.environment)
        kwargs = dict(x.as_const() for x in self.kwargs)
        if self.dyn_args is not None:
            try:
                args.extend(self.dyn_args.as_const())
            except:
                raise Impossible()
        if self.dyn_kwargs is not None:
            try:
                kwargs.update(self.dyn_kwargs.as_const())
            except:
                raise Impossible()
        try:
            return filter(obj, *args, **kwargs)
        except:
            raise Impossible()


class Test(Expr):
    """Applies a test on an expression.  `name` is the name of the test, the
    rest of the fields are the same as for :class:`Call`.
    """
    fields = ('node', 'name', 'args', 'kwargs', 'dyn_args', 'dyn_kwargs')


class Call(Expr):
    """Calls an expression.  `args` is a list of arguments, `kwargs` a list
    of keyword arguments (list of :class:`Keyword` nodes), and `dyn_args`
    and `dyn_kwargs` has to be either `None` or a node that is used as
    node for dynamic positional (``*args``) or keyword (``**kwargs``)
    arguments.
    """
    fields = ('node', 'args', 'kwargs', 'dyn_args', 'dyn_kwargs')

    def as_const(self):
        obj = self.node.as_const()

        # don't evaluate context functions
        args = [x.as_const() for x in self.args]
        if getattr(obj, 'contextfunction', False):
            raise Impossible()
        elif getattr(obj, 'environmentfunction', False):
            args.insert(0, self.environment)

        kwargs = dict(x.as_const() for x in self.kwargs)
        if self.dyn_args is not None:
            try:
                args.extend(self.dyn_args.as_const())
            except:
                raise Impossible()
        if self.dyn_kwargs is not None:
            try:
                kwargs.update(self.dyn_kwargs.as_const())
            except:
                raise Impossible()
        try:
            return obj(*args, **kwargs)
        except:
            raise Impossible()


class Getitem(Expr):
    """Get an attribute or item from an expression and prefer the item."""
    fields = ('node', 'arg', 'ctx')

    def as_const(self):
        if self.ctx != 'load':
            raise Impossible()
        try:
            return self.environment.getitem(self.node.as_const(),
                                            self.arg.as_const())
        except:
            raise Impossible()

    def can_assign(self):
        return False


class Getattr(Expr):
    """Get an attribute or item from an expression that is a ascii-only
    bytestring and prefer the attribute.
    """
    fields = ('node', 'attr', 'ctx')

    def as_const(self):
        if self.ctx != 'load':
            raise Impossible()
        try:
            return self.environment.getattr(self.node.as_const(), arg)
        except:
            raise Impossible()

    def can_assign(self):
        return False


class Slice(Expr):
    """Represents a slice object.  This must only be used as argument for
    :class:`Subscript`.
    """
    fields = ('start', 'stop', 'step')

    def as_const(self):
        def const(obj):
            if obj is None:
                return obj
            return obj.as_const()
        return slice(const(self.start), const(self.stop), const(self.step))


class Concat(Expr):
    """Concatenates the list of expressions provided after converting them to
    unicode.
    """
    fields = ('nodes',)

    def as_const(self):
        return ''.join(unicode(x.as_const()) for x in self.nodes)


class Compare(Expr):
    """Compares an expression with some other expressions.  `ops` must be a
    list of :class:`Operand`\s.
    """
    fields = ('expr', 'ops')

    def as_const(self):
        result = value = self.expr.as_const()
        try:
            for op in self.ops:
                new_value = op.expr.as_const()
                result = _cmpop_to_func[op.op](value, new_value)
                value = new_value
        except:
            raise Impossible()
        return result


class Operand(Helper):
    """Holds an operator and an expression."""
    fields = ('op', 'expr')

if __debug__:
    Operand.__doc__ += '\nThe following operators are available: ' + \
        ', '.join(sorted('``%s``' % x for x in set(_binop_to_func) |
                  set(_uaop_to_func) | set(_cmpop_to_func)))


class Mul(BinExpr):
    """Multiplies the left with the right node."""
    operator = '*'


class Div(BinExpr):
    """Divides the left by the right node."""
    operator = '/'


class FloorDiv(BinExpr):
    """Divides the left by the right node and truncates conver the
    result into an integer by truncating.
    """
    operator = '//'


class Add(BinExpr):
    """Add the left to the right node."""
    operator = '+'


class Sub(BinExpr):
    """Substract the right from the left node."""
    operator = '-'


class Mod(BinExpr):
    """Left modulo right."""
    operator = '%'


class Pow(BinExpr):
    """Left to the power of right."""
    operator = '**'


class And(BinExpr):
    """Short circuited AND."""
    operator = 'and'

    def as_const(self):
        return self.left.as_const() and self.right.as_const()


class Or(BinExpr):
    """Short circuited OR."""
    operator = 'or'

    def as_const(self):
        return self.left.as_const() or self.right.as_const()


class Not(UnaryExpr):
    """Negate the expression."""
    operator = 'not'


class Neg(UnaryExpr):
    """Make the expression negative."""
    operator = '-'


class Pos(UnaryExpr):
    """Make the expression positive (noop for most expressions)"""
    operator = '+'


# Helpers for extensions


class EnvironmentAttribute(Expr):
    """Loads an attribute from the environment object.  This is useful for
    extensions that want to call a callback stored on the environment.
    """
    fields = ('name',)


class ExtensionAttribute(Expr):
    """Returns the attribute of an extension bound to the environment.
    The identifier is the identifier of the :class:`Extension`.

    This node is usually constructed by calling the
    :meth:`~jinja2.ext.Extension.attr` method on an extension.
    """
    fields = ('identifier', 'name')


class ImportedName(Expr):
    """If created with an import name the import name is returned on node
    access.  For example ``ImportedName('cgi.escape')`` returns the `escape`
    function from the cgi module on evaluation.  Imports are optimized by the
    compiler so there is no need to assign them to local variables.
    """
    fields = ('importname',)


class InternalName(Expr):
    """An internal name in the compiler.  You cannot create these nodes
    yourself but the parser provides a
    :meth:`~jinja2.parser.Parser.free_identifier` method that creates
    a new identifier for you.  This identifier is not available from the
    template and is not threated specially by the compiler.
    """
    fields = ('name',)

    def __init__(self):
        raise TypeError('Can\'t create internal names.  Use the '
                        '`free_identifier` method on a parser.')


class MarkSafe(Expr):
    """Mark the wrapped expression as safe (wrap it as `Markup`)."""
    fields = ('expr',)

    def as_const(self):
        return Markup(self.expr.as_const())


class ContextReference(Expr):
    """Returns the current template context."""


class Continue(Stmt):
    """Continue a loop."""


class Break(Stmt):
    """Break a loop."""


# make sure nobody creates custom nodes
def _failing_new(*args, **kwargs):
    raise TypeError('can\'t create custom node types')
NodeType.__new__ = staticmethod(_failing_new); del _failing_new

########NEW FILE########
__FILENAME__ = optimizer
# -*- coding: utf-8 -*-
"""
    jinja2.optimizer
    ~~~~~~~~~~~~~~~~

    The jinja optimizer is currently trying to constant fold a few expressions
    and modify the AST in place so that it should be easier to evaluate it.

    Because the AST does not contain all the scoping information and the
    compiler has to find that out, we cannot do all the optimizations we
    want.  For example loop unrolling doesn't work because unrolled loops would
    have a different scoping.

    The solution would be a second syntax tree that has the scoping rules stored.

    :copyright: Copyright 2008 by Christoph Hack, Armin Ronacher.
    :license: BSD.
"""
from jinja2 import nodes
from jinja2.visitor import NodeTransformer


def optimize(node, environment):
    """The context hint can be used to perform an static optimization
    based on the context given."""
    optimizer = Optimizer(environment)
    return optimizer.visit(node)


class Optimizer(NodeTransformer):

    def __init__(self, environment):
        self.environment = environment

    def visit_If(self, node):
        """Eliminate dead code."""
        # do not optimize ifs that have a block inside so that it doesn't
        # break super().
        if node.find(nodes.Block) is not None:
            return self.generic_visit(node)
        try:
            val = self.visit(node.test).as_const()
        except nodes.Impossible:
            return self.generic_visit(node)
        if val:
            body = node.body
        else:
            body = node.else_
        result = []
        for node in body:
            result.extend(self.visit_list(node))
        return result

    def fold(self, node):
        """Do constant folding."""
        node = self.generic_visit(node)
        try:
            return nodes.Const.from_untrusted(node.as_const(),
                                              lineno=node.lineno,
                                              environment=self.environment)
        except nodes.Impossible:
            return node

    visit_Add = visit_Sub = visit_Mul = visit_Div = visit_FloorDiv = \
    visit_Pow = visit_Mod = visit_And = visit_Or = visit_Pos = visit_Neg = \
    visit_Not = visit_Compare = visit_Getitem = visit_Getattr = visit_Call = \
    visit_Filter = visit_Test = visit_CondExpr = fold
    del fold

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-
"""
    jinja2.parser
    ~~~~~~~~~~~~~

    Implements the template parser.

    :copyright: 2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from jinja2 import nodes
from jinja2.exceptions import TemplateSyntaxError, TemplateAssertionError


_statement_keywords = frozenset(['for', 'if', 'block', 'extends', 'print',
                                 'macro', 'include', 'from', 'import',
                                 'set'])
_compare_operators = frozenset(['eq', 'ne', 'lt', 'lteq', 'gt', 'gteq'])


class Parser(object):
    """This is the central parsing class Jinja2 uses.  It's passed to
    extensions and can be used to parse expressions or statements.
    """

    def __init__(self, environment, source, name=None, filename=None,
                 state=None):
        self.environment = environment
        self.stream = environment._tokenize(source, name, filename, state)
        self.name = name
        self.filename = filename
        self.closed = False
        self.extensions = {}
        for extension in environment.extensions.itervalues():
            for tag in extension.tags:
                self.extensions[tag] = extension.parse
        self._last_identifier = 0

    def fail(self, msg, lineno=None, exc=TemplateSyntaxError):
        """Convenience method that raises `exc` with the message, passed
        line number or last line number as well as the current name and
        filename.
        """
        if lineno is None:
            lineno = self.stream.current.lineno
        raise exc(msg, lineno, self.name, self.filename)

    def is_tuple_end(self, extra_end_rules=None):
        """Are we at the end of a tuple?"""
        if self.stream.current.type in ('variable_end', 'block_end', 'rparen'):
            return True
        elif extra_end_rules is not None:
            return self.stream.current.test_any(extra_end_rules)
        return False

    def free_identifier(self, lineno=None):
        """Return a new free identifier as :class:`~jinja2.nodes.InternalName`."""
        self._last_identifier += 1
        rv = object.__new__(nodes.InternalName)
        nodes.Node.__init__(rv, 'fi%d' % self._last_identifier, lineno=lineno)
        return rv

    def parse_statement(self):
        """Parse a single statement."""
        token = self.stream.current
        if token.type is not 'name':
            self.fail('tag name expected', token.lineno)
        if token.value in _statement_keywords:
            return getattr(self, 'parse_' + self.stream.current.value)()
        if token.value == 'call':
            return self.parse_call_block()
        if token.value == 'filter':
            return self.parse_filter_block()
        ext = self.extensions.get(token.value)
        if ext is not None:
            return ext(self)
        self.fail('unknown tag %r' % token.value, token.lineno)

    def parse_statements(self, end_tokens, drop_needle=False):
        """Parse multiple statements into a list until one of the end tokens
        is reached.  This is used to parse the body of statements as it also
        parses template data if appropriate.  The parser checks first if the
        current token is a colon and skips it if there is one.  Then it checks
        for the block end and parses until if one of the `end_tokens` is
        reached.  Per default the active token in the stream at the end of
        the call is the matched end token.  If this is not wanted `drop_needle`
        can be set to `True` and the end token is removed.
        """
        # the first token may be a colon for python compatibility
        self.stream.skip_if('colon')

        # in the future it would be possible to add whole code sections
        # by adding some sort of end of statement token and parsing those here.
        self.stream.expect('block_end')
        result = self.subparse(end_tokens)

        if drop_needle:
            self.stream.next()
        return result

    def parse_set(self):
        """Parse an assign statement."""
        lineno = self.stream.next().lineno
        target = self.parse_assign_target()
        self.stream.expect('assign')
        expr = self.parse_tuple()
        return nodes.Assign(target, expr, lineno=lineno)

    def parse_for(self):
        """Parse a for loop."""
        lineno = self.stream.expect('name:for').lineno
        target = self.parse_assign_target(extra_end_rules=('name:in',))
        self.stream.expect('name:in')
        iter = self.parse_tuple(with_condexpr=False,
                                extra_end_rules=('name:recursive',))
        test = None
        if self.stream.skip_if('name:if'):
            test = self.parse_expression()
        recursive = self.stream.skip_if('name:recursive')
        body = self.parse_statements(('name:endfor', 'name:else'))
        if self.stream.next().value == 'endfor':
            else_ = []
        else:
            else_ = self.parse_statements(('name:endfor',), drop_needle=True)
        return nodes.For(target, iter, body, else_, test,
                         recursive, lineno=lineno)

    def parse_if(self):
        """Parse an if construct."""
        node = result = nodes.If(lineno=self.stream.expect('name:if').lineno)
        while 1:
            node.test = self.parse_tuple(with_condexpr=False)
            node.body = self.parse_statements(('name:elif', 'name:else',
                                               'name:endif'))
            token = self.stream.next()
            if token.test('name:elif'):
                new_node = nodes.If(lineno=self.stream.current.lineno)
                node.else_ = [new_node]
                node = new_node
                continue
            elif token.test('name:else'):
                node.else_ = self.parse_statements(('name:endif',),
                                                   drop_needle=True)
            else:
                node.else_ = []
            break
        return result

    def parse_block(self):
        node = nodes.Block(lineno=self.stream.next().lineno)
        node.name = self.stream.expect('name').value
        node.body = self.parse_statements(('name:endblock',), drop_needle=True)
        self.stream.skip_if('name:' + node.name)
        return node

    def parse_extends(self):
        node = nodes.Extends(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        return node

    def parse_import_context(self, node, default):
        if self.stream.current.test_any('name:with', 'name:without') and \
           self.stream.look().test('name:context'):
            node.with_context = self.stream.next().value == 'with'
            self.stream.skip()
        else:
            node.with_context = default
        return node

    def parse_include(self):
        node = nodes.Include(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        return self.parse_import_context(node, True)

    def parse_import(self):
        node = nodes.Import(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        self.stream.expect('name:as')
        node.target = self.parse_assign_target(name_only=True).name
        return self.parse_import_context(node, False)

    def parse_from(self):
        node = nodes.FromImport(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        self.stream.expect('name:import')
        node.names = []

        def parse_context():
            if self.stream.current.value in ('with', 'without') and \
               self.stream.look().test('name:context'):
                node.with_context = self.stream.next().value == 'with'
                self.stream.skip()
                return True
            return False

        while 1:
            if node.names:
                self.stream.expect('comma')
            if self.stream.current.type is 'name':
                if parse_context():
                    break
                target = self.parse_assign_target(name_only=True)
                if target.name.startswith('_'):
                    self.fail('names starting with an underline can not '
                              'be imported', target.lineno,
                              exc=TemplateAssertionError)
                if self.stream.skip_if('name:as'):
                    alias = self.parse_assign_target(name_only=True)
                    node.names.append((target.name, alias.name))
                else:
                    node.names.append(target.name)
                if parse_context() or self.stream.current.type is not 'comma':
                    break
            else:
                break
        if not hasattr(node, 'with_context'):
            node.with_context = False
            self.stream.skip_if('comma')
        return node

    def parse_signature(self, node):
        node.args = args = []
        node.defaults = defaults = []
        self.stream.expect('lparen')
        while self.stream.current.type is not 'rparen':
            if args:
                self.stream.expect('comma')
            arg = self.parse_assign_target(name_only=True)
            arg.set_ctx('param')
            if self.stream.skip_if('assign'):
                defaults.append(self.parse_expression())
            args.append(arg)
        self.stream.expect('rparen')

    def parse_call_block(self):
        node = nodes.CallBlock(lineno=self.stream.next().lineno)
        if self.stream.current.type is 'lparen':
            self.parse_signature(node)
        else:
            node.args = []
            node.defaults = []

        node.call = self.parse_expression()
        if not isinstance(node.call, nodes.Call):
            self.fail('expected call', node.lineno)
        node.body = self.parse_statements(('name:endcall',), drop_needle=True)
        return node

    def parse_filter_block(self):
        node = nodes.FilterBlock(lineno=self.stream.next().lineno)
        node.filter = self.parse_filter(None, start_inline=True)
        node.body = self.parse_statements(('name:endfilter',),
                                          drop_needle=True)
        return node

    def parse_macro(self):
        node = nodes.Macro(lineno=self.stream.next().lineno)
        node.name = self.parse_assign_target(name_only=True).name
        self.parse_signature(node)
        node.body = self.parse_statements(('name:endmacro',),
                                          drop_needle=True)
        return node

    def parse_print(self):
        node = nodes.Output(lineno=self.stream.next().lineno)
        node.nodes = []
        while self.stream.current.type is not 'block_end':
            if node.nodes:
                self.stream.expect('comma')
            node.nodes.append(self.parse_expression())
        return node

    def parse_assign_target(self, with_tuple=True, name_only=False,
                            extra_end_rules=None):
        """Parse an assignment target.  As Jinja2 allows assignments to
        tuples, this function can parse all allowed assignment targets.  Per
        default assignments to tuples are parsed, that can be disable however
        by setting `with_tuple` to `False`.  If only assignments to names are
        wanted `name_only` can be set to `True`.  The `extra_end_rules`
        parameter is forwarded to the tuple parsing function.
        """
        if name_only:
            token = self.stream.expect('name')
            target = nodes.Name(token.value, 'store', lineno=token.lineno)
        else:
            if with_tuple:
                target = self.parse_tuple(simplified=True,
                                          extra_end_rules=extra_end_rules)
            else:
                target = self.parse_primary(with_postfix=False)
            target.set_ctx('store')
        if not target.can_assign():
            self.fail('can\'t assign to %r' % target.__class__.
                      __name__.lower(), target.lineno)
        return target

    def parse_expression(self, with_condexpr=True):
        """Parse an expression.  Per default all expressions are parsed, if
        the optional `with_condexpr` parameter is set to `False` conditional
        expressions are not parsed.
        """
        if with_condexpr:
            return self.parse_condexpr()
        return self.parse_or()

    def parse_condexpr(self):
        lineno = self.stream.current.lineno
        expr1 = self.parse_or()
        while self.stream.skip_if('name:if'):
            expr2 = self.parse_or()
            if self.stream.skip_if('name:else'):
                expr3 = self.parse_condexpr()
            else:
                expr3 = None
            expr1 = nodes.CondExpr(expr2, expr1, expr3, lineno=lineno)
            lineno = self.stream.current.lineno
        return expr1

    def parse_or(self):
        lineno = self.stream.current.lineno
        left = self.parse_and()
        while self.stream.skip_if('name:or'):
            right = self.parse_and()
            left = nodes.Or(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_and(self):
        lineno = self.stream.current.lineno
        left = self.parse_compare()
        while self.stream.skip_if('name:and'):
            right = self.parse_compare()
            left = nodes.And(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_compare(self):
        lineno = self.stream.current.lineno
        expr = self.parse_add()
        ops = []
        while 1:
            token_type = self.stream.current.type
            if token_type in _compare_operators:
                self.stream.next()
                ops.append(nodes.Operand(token_type, self.parse_add()))
            elif self.stream.skip_if('name:in'):
                ops.append(nodes.Operand('in', self.parse_add()))
            elif self.stream.current.test('name:not') and \
                 self.stream.look().test('name:in'):
                self.stream.skip(2)
                ops.append(nodes.Operand('notin', self.parse_add()))
            else:
                break
            lineno = self.stream.current.lineno
        if not ops:
            return expr
        return nodes.Compare(expr, ops, lineno=lineno)

    def parse_add(self):
        lineno = self.stream.current.lineno
        left = self.parse_sub()
        while self.stream.current.type is 'add':
            self.stream.next()
            right = self.parse_sub()
            left = nodes.Add(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_sub(self):
        lineno = self.stream.current.lineno
        left = self.parse_concat()
        while self.stream.current.type is 'sub':
            self.stream.next()
            right = self.parse_concat()
            left = nodes.Sub(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_concat(self):
        lineno = self.stream.current.lineno
        args = [self.parse_mul()]
        while self.stream.current.type is 'tilde':
            self.stream.next()
            args.append(self.parse_mul())
        if len(args) == 1:
            return args[0]
        return nodes.Concat(args, lineno=lineno)

    def parse_mul(self):
        lineno = self.stream.current.lineno
        left = self.parse_div()
        while self.stream.current.type is 'mul':
            self.stream.next()
            right = self.parse_div()
            left = nodes.Mul(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_div(self):
        lineno = self.stream.current.lineno
        left = self.parse_floordiv()
        while self.stream.current.type is 'div':
            self.stream.next()
            right = self.parse_floordiv()
            left = nodes.Div(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_floordiv(self):
        lineno = self.stream.current.lineno
        left = self.parse_mod()
        while self.stream.current.type is 'floordiv':
            self.stream.next()
            right = self.parse_mod()
            left = nodes.FloorDiv(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_mod(self):
        lineno = self.stream.current.lineno
        left = self.parse_pow()
        while self.stream.current.type is 'mod':
            self.stream.next()
            right = self.parse_pow()
            left = nodes.Mod(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_pow(self):
        lineno = self.stream.current.lineno
        left = self.parse_unary()
        while self.stream.current.type is 'pow':
            self.stream.next()
            right = self.parse_unary()
            left = nodes.Pow(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_unary(self):
        token_type = self.stream.current.type
        lineno = self.stream.current.lineno
        if token_type is 'name' and self.stream.current.value == 'not':
            self.stream.next()
            node = self.parse_unary()
            return nodes.Not(node, lineno=lineno)
        if token_type is 'sub':
            self.stream.next()
            node = self.parse_unary()
            return nodes.Neg(node, lineno=lineno)
        if token_type is 'add':
            self.stream.next()
            node = self.parse_unary()
            return nodes.Pos(node, lineno=lineno)
        return self.parse_primary()

    def parse_primary(self, with_postfix=True):
        token = self.stream.current
        if token.type is 'name':
            if token.value in ('true', 'false', 'True', 'False'):
                node = nodes.Const(token.value in ('true', 'True'),
                                   lineno=token.lineno)
            elif token.value in ('none', 'None'):
                node = nodes.Const(None, lineno=token.lineno)
            else:
                node = nodes.Name(token.value, 'load', lineno=token.lineno)
            self.stream.next()
        elif token.type is 'string':
            self.stream.next()
            buf = [token.value]
            lineno = token.lineno
            while self.stream.current.type is 'string':
                buf.append(self.stream.current.value)
                self.stream.next()
            node = nodes.Const(''.join(buf), lineno=lineno)
        elif token.type in ('integer', 'float'):
            self.stream.next()
            node = nodes.Const(token.value, lineno=token.lineno)
        elif token.type is 'lparen':
            self.stream.next()
            node = self.parse_tuple()
            self.stream.expect('rparen')
        elif token.type is 'lbracket':
            node = self.parse_list()
        elif token.type is 'lbrace':
            node = self.parse_dict()
        else:
            self.fail("unexpected token '%s'" % (token,), token.lineno)
        if with_postfix:
            node = self.parse_postfix(node)
        return node

    def parse_tuple(self, simplified=False, with_condexpr=True,
                    extra_end_rules=None):
        """Works like `parse_expression` but if multiple expressions are
        delimited by a comma a :class:`~jinja2.nodes.Tuple` node is created.
        This method could also return a regular expression instead of a tuple
        if no commas where found.

        The default parsing mode is a full tuple.  If `simplified` is `True`
        only names and literals are parsed.  The `no_condexpr` parameter is
        forwarded to :meth:`parse_expression`.

        Because tuples do not require delimiters and may end in a bogus comma
        an extra hint is needed that marks the end of a tuple.  For example
        for loops support tuples between `for` and `in`.  In that case the
        `extra_end_rules` is set to ``['name:in']``.
        """
        lineno = self.stream.current.lineno
        if simplified:
            parse = lambda: self.parse_primary(with_postfix=False)
        elif with_condexpr:
            parse = self.parse_expression
        else:
            parse = lambda: self.parse_expression(with_condexpr=False)
        args = []
        is_tuple = False
        while 1:
            if args:
                self.stream.expect('comma')
            if self.is_tuple_end(extra_end_rules):
                break
            args.append(parse())
            if self.stream.current.type is 'comma':
                is_tuple = True
            else:
                break
            lineno = self.stream.current.lineno
        if not is_tuple and args:
            return args[0]
        return nodes.Tuple(args, 'load', lineno=lineno)

    def parse_list(self):
        token = self.stream.expect('lbracket')
        items = []
        while self.stream.current.type is not 'rbracket':
            if items:
                self.stream.expect('comma')
            if self.stream.current.type == 'rbracket':
                break
            items.append(self.parse_expression())
        self.stream.expect('rbracket')
        return nodes.List(items, lineno=token.lineno)

    def parse_dict(self):
        token = self.stream.expect('lbrace')
        items = []
        while self.stream.current.type is not 'rbrace':
            if items:
                self.stream.expect('comma')
            if self.stream.current.type == 'rbrace':
                break
            key = self.parse_expression()
            self.stream.expect('colon')
            value = self.parse_expression()
            items.append(nodes.Pair(key, value, lineno=key.lineno))
        self.stream.expect('rbrace')
        return nodes.Dict(items, lineno=token.lineno)

    def parse_postfix(self, node):
        while 1:
            token_type = self.stream.current.type
            if token_type is 'dot' or token_type is 'lbracket':
                node = self.parse_subscript(node)
            elif token_type is 'lparen':
                node = self.parse_call(node)
            elif token_type is 'pipe':
                node = self.parse_filter(node)
            elif token_type is 'name' and self.stream.current.value == 'is':
                node = self.parse_test(node)
            else:
                break
        return node

    def parse_subscript(self, node):
        token = self.stream.next()
        if token.type is 'dot':
            attr_token = self.stream.current
            self.stream.next()
            if attr_token.type is 'name':
                return nodes.Getattr(node, attr_token.value, 'load',
                                     lineno=token.lineno)
            elif attr_token.type is not 'integer':
                self.fail('expected name or number', attr_token.lineno)
            arg = nodes.Const(attr_token.value, lineno=attr_token.lineno)
            return nodes.Getitem(node, arg, 'load', lineno=token.lineno)
        if token.type is 'lbracket':
            priority_on_attribute = False
            args = []
            while self.stream.current.type is not 'rbracket':
                if args:
                    self.stream.expect('comma')
                args.append(self.parse_subscribed())
            self.stream.expect('rbracket')
            if len(args) == 1:
                arg = args[0]
            else:
                arg = nodes.Tuple(args, self.lineno, self.filename)
            return nodes.Getitem(node, arg, 'load', lineno=token.lineno)
        self.fail('expected subscript expression', self.lineno)

    def parse_subscribed(self):
        lineno = self.stream.current.lineno

        if self.stream.current.type is 'colon':
            self.stream.next()
            args = [None]
        else:
            node = self.parse_expression()
            if self.stream.current.type is not 'colon':
                return node
            self.stream.next()
            args = [node]

        if self.stream.current.type is 'colon':
            args.append(None)
        elif self.stream.current.type not in ('rbracket', 'comma'):
            args.append(self.parse_expression())
        else:
            args.append(None)

        if self.stream.current.type is 'colon':
            self.stream.next()
            if self.stream.current.type not in ('rbracket', 'comma'):
                args.append(self.parse_expression())
            else:
                args.append(None)
        else:
            args.append(None)

        return nodes.Slice(lineno=lineno, *args)

    def parse_call(self, node):
        token = self.stream.expect('lparen')
        args = []
        kwargs = []
        dyn_args = dyn_kwargs = None
        require_comma = False

        def ensure(expr):
            if not expr:
                self.fail('invalid syntax for function call expression',
                          token.lineno)

        while self.stream.current.type is not 'rparen':
            if require_comma:
                self.stream.expect('comma')
                # support for trailing comma
                if self.stream.current.type is 'rparen':
                    break
            if self.stream.current.type is 'mul':
                ensure(dyn_args is None and dyn_kwargs is None)
                self.stream.next()
                dyn_args = self.parse_expression()
            elif self.stream.current.type is 'pow':
                ensure(dyn_kwargs is None)
                self.stream.next()
                dyn_kwargs = self.parse_expression()
            else:
                ensure(dyn_args is None and dyn_kwargs is None)
                if self.stream.current.type is 'name' and \
                    self.stream.look().type is 'assign':
                    key = self.stream.current.value
                    self.stream.skip(2)
                    value = self.parse_expression()
                    kwargs.append(nodes.Keyword(key, value,
                                                lineno=value.lineno))
                else:
                    ensure(not kwargs)
                    args.append(self.parse_expression())

            require_comma = True
        self.stream.expect('rparen')

        if node is None:
            return args, kwargs, dyn_args, dyn_kwargs
        return nodes.Call(node, args, kwargs, dyn_args, dyn_kwargs,
                          lineno=token.lineno)

    def parse_filter(self, node, start_inline=False):
        while self.stream.current.type == 'pipe' or start_inline:
            if not start_inline:
                self.stream.next()
            token = self.stream.expect('name')
            name = token.value
            while self.stream.current.type is 'dot':
                self.stream.next()
                name += '.' + self.stream.expect('name').value
            if self.stream.current.type is 'lparen':
                args, kwargs, dyn_args, dyn_kwargs = self.parse_call(None)
            else:
                args = []
                kwargs = []
                dyn_args = dyn_kwargs = None
            node = nodes.Filter(node, name, args, kwargs, dyn_args,
                                dyn_kwargs, lineno=token.lineno)
            start_inline = False
        return node

    def parse_test(self, node):
        token = self.stream.next()
        if self.stream.current.test('name:not'):
            self.stream.next()
            negated = True
        else:
            negated = False
        name = self.stream.expect('name').value
        while self.stream.current.type is 'dot':
            self.stream.next()
            name += '.' + self.stream.expect('name').value
        dyn_args = dyn_kwargs = None
        kwargs = []
        if self.stream.current.type is 'lparen':
            args, kwargs, dyn_args, dyn_kwargs = self.parse_call(None)
        elif self.stream.current.type in ('name', 'string', 'integer',
                                          'float', 'lparen', 'lbracket',
                                          'lbrace') and not \
             self.stream.current.test_any('name:else', 'name:or',
                                          'name:and'):
            if self.stream.current.test('name:is'):
                self.fail('You cannot chain multiple tests with is')
            args = [self.parse_expression()]
        else:
            args = []
        node = nodes.Test(node, name, args, kwargs, dyn_args,
                          dyn_kwargs, lineno=token.lineno)
        if negated:
            node = nodes.Not(node, lineno=token.lineno)
        return node

    def subparse(self, end_tokens=None):
        body = []
        data_buffer = []
        add_data = data_buffer.append

        def flush_data():
            if data_buffer:
                lineno = data_buffer[0].lineno
                body.append(nodes.Output(data_buffer[:], lineno=lineno))
                del data_buffer[:]

        while self.stream:
            token = self.stream.current
            if token.type is 'data':
                if token.value:
                    add_data(nodes.TemplateData(token.value,
                                                lineno=token.lineno))
                self.stream.next()
            elif token.type is 'variable_begin':
                self.stream.next()
                add_data(self.parse_tuple(with_condexpr=True))
                self.stream.expect('variable_end')
            elif token.type is 'block_begin':
                flush_data()
                self.stream.next()
                if end_tokens is not None and \
                   self.stream.current.test_any(*end_tokens):
                    return body
                rv = self.parse_statement()
                if isinstance(rv, list):
                    body.extend(rv)
                else:
                    body.append(rv)
                self.stream.expect('block_end')
            else:
                raise AssertionError('internal parsing error')

        flush_data()
        return body

    def parse(self):
        """Parse the whole template into a `Template` node."""
        result = nodes.Template(self.subparse(), lineno=1)
        result.set_environment(self.environment)
        return result

########NEW FILE########
__FILENAME__ = runtime
# -*- coding: utf-8 -*-
"""
    jinja2.runtime
    ~~~~~~~~~~~~~~

    Runtime helpers.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
import sys
from itertools import chain, imap
from jinja2.utils import Markup, partial, soft_unicode, escape, missing, \
     concat, MethodType, FunctionType
from jinja2.exceptions import UndefinedError, TemplateRuntimeError


# these variables are exported to the template runtime
__all__ = ['LoopContext', 'Context', 'TemplateReference', 'Macro', 'Markup',
           'TemplateRuntimeError', 'missing', 'concat', 'escape',
           'markup_join', 'unicode_join']


#: the types we support for context functions
_context_function_types = (FunctionType, MethodType)


def markup_join(seq):
    """Concatenation that escapes if necessary and converts to unicode."""
    buf = []
    iterator = imap(soft_unicode, seq)
    for arg in iterator:
        buf.append(arg)
        if hasattr(arg, '__html__'):
            return Markup(u'').join(chain(buf, iterator))
    return concat(buf)


def unicode_join(seq):
    """Simple args to unicode conversion and concatenation."""
    return concat(imap(unicode, seq))


class Context(object):
    """The template context holds the variables of a template.  It stores the
    values passed to the template and also the names the template exports.
    Creating instances is neither supported nor useful as it's created
    automatically at various stages of the template evaluation and should not
    be created by hand.

    The context is immutable.  Modifications on :attr:`parent` **must not**
    happen and modifications on :attr:`vars` are allowed from generated
    template code only.  Template filters and global functions marked as
    :func:`contextfunction`\s get the active context passed as first argument
    and are allowed to access the context read-only.

    The template context supports read only dict operations (`get`,
    `keys`, `values`, `items`, `iterkeys`, `itervalues`, `iteritems`,
    `__getitem__`, `__contains__`).  Additionally there is a :meth:`resolve`
    method that doesn't fail with a `KeyError` but returns an
    :class:`Undefined` object for missing variables.
    """
    __slots__ = ('parent', 'vars', 'environment', 'exported_vars', 'name',
                 'blocks', '__weakref__')

    def __init__(self, environment, parent, name, blocks):
        self.parent = parent
        self.vars = vars = {}
        self.environment = environment
        self.exported_vars = set()
        self.name = name

        # create the initial mapping of blocks.  Whenever template inheritance
        # takes place the runtime will update this mapping with the new blocks
        # from the template.
        self.blocks = dict((k, [v]) for k, v in blocks.iteritems())

    def super(self, name, current):
        """Render a parent block."""
        try:
            blocks = self.blocks[name]
            index = blocks.index(current) + 1
            blocks[index]
        except LookupError:
            return self.environment.undefined('there is no parent block '
                                              'called %r.' % name,
                                              name='super')
        return BlockReference(name, self, blocks, index)

    def get(self, key, default=None):
        """Returns an item from the template context, if it doesn't exist
        `default` is returned.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def resolve(self, key):
        """Looks up a variable like `__getitem__` or `get` but returns an
        :class:`Undefined` object with the name of the name looked up.
        """
        if key in self.vars:
            return self.vars[key]
        if key in self.parent:
            return self.parent[key]
        return self.environment.undefined(name=key)

    def get_exported(self):
        """Get a new dict with the exported variables."""
        return dict((k, self.vars[k]) for k in self.exported_vars)

    def get_all(self):
        """Return a copy of the complete context as dict including the
        exported variables.
        """
        return dict(self.parent, **self.vars)

    def call(__self, __obj, *args, **kwargs):
        """Call the callable with the arguments and keyword arguments
        provided but inject the active context or environment as first
        argument if the callable is a :func:`contextfunction` or
        :func:`environmentfunction`.
        """
        if __debug__:
            __traceback_hide__ = True
        if isinstance(__obj, _context_function_types):
            if getattr(__obj, 'contextfunction', 0):
                args = (__self,) + args
            elif getattr(__obj, 'environmentfunction', 0):
                args = (__self.environment,) + args
        return __obj(*args, **kwargs)

    def _all(meth):
        proxy = lambda self: getattr(self.get_all(), meth)()
        proxy.__doc__ = getattr(dict, meth).__doc__
        proxy.__name__ = meth
        return proxy

    keys = _all('keys')
    values = _all('values')
    items = _all('items')
    iterkeys = _all('iterkeys')
    itervalues = _all('itervalues')
    iteritems = _all('iteritems')
    del _all

    def __contains__(self, name):
        return name in self.vars or name in self.parent

    def __getitem__(self, key):
        """Lookup a variable or raise `KeyError` if the variable is
        undefined.
        """
        item = self.resolve(key)
        if isinstance(item, Undefined):
            raise KeyError(key)
        return item

    def __repr__(self):
        return '<%s %s of %r>' % (
            self.__class__.__name__,
            repr(self.get_all()),
            self.name
        )


# register the context as mapping if possible
try:
    from collections import Mapping
    Mapping.register(Context)
except ImportError:
    pass


class TemplateReference(object):
    """The `self` in templates."""

    def __init__(self, context):
        self.__context = context

    def __getitem__(self, name):
        blocks = self.__context.blocks[name]
        wrap = self.__context.environment.autoescape and \
               Markup or (lambda x: x)
        return BlockReference(name, self.__context, blocks, 0)

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.__context.name
        )


class BlockReference(object):
    """One block on a template reference."""

    def __init__(self, name, context, stack, depth):
        self.name = name
        self._context = context
        self._stack = stack
        self._depth = depth

    @property
    def super(self):
        """Super the block."""
        if self._depth + 1 >= len(self._stack):
            return self._context.environment. \
                undefined('there is no parent block called %r.' %
                          self.name, name='super')
        return BlockReference(self.name, self._context, self._stack,
                              self._depth + 1)

    def __call__(self):
        rv = concat(self._stack[self._depth](self._context))
        if self._context.environment.autoescape:
            rv = Markup(rv)
        return rv


class LoopContext(object):
    """A loop context for dynamic iteration."""

    def __init__(self, iterable, recurse=None):
        self._iterator = iter(iterable)
        self._recurse = recurse
        self.index0 = -1

        # try to get the length of the iterable early.  This must be done
        # here because there are some broken iterators around where there
        # __len__ is the number of iterations left (i'm looking at your
        # listreverseiterator!).
        try:
            self._length = len(iterable)
        except (TypeError, AttributeError):
            self._length = None

    def cycle(self, *args):
        """Cycles among the arguments with the current loop index."""
        if not args:
            raise TypeError('no items for cycling given')
        return args[self.index0 % len(args)]

    first = property(lambda x: x.index0 == 0)
    last = property(lambda x: x.index0 + 1 == x.length)
    index = property(lambda x: x.index0 + 1)
    revindex = property(lambda x: x.length - x.index0)
    revindex0 = property(lambda x: x.length - x.index)

    def __len__(self):
        return self.length

    def __iter__(self):
        return LoopContextIterator(self)

    def loop(self, iterable):
        if self._recurse is None:
            raise TypeError('Tried to call non recursive loop.  Maybe you '
                            "forgot the 'recursive' modifier.")
        return self._recurse(iterable, self._recurse)

    # a nifty trick to enhance the error message if someone tried to call
    # the the loop without or with too many arguments.
    __call__ = loop; del loop

    @property
    def length(self):
        if self._length is None:
            # if was not possible to get the length of the iterator when
            # the loop context was created (ie: iterating over a generator)
            # we have to convert the iterable into a sequence and use the
            # length of that.
            iterable = tuple(self._iterator)
            self._iterator = iter(iterable)
            self._length = len(iterable) + self.index0 + 1
        return self._length

    def __repr__(self):
        return '<%s %r/%r>' % (
            self.__class__.__name__,
            self.index,
            self.length
        )


class LoopContextIterator(object):
    """The iterator for a loop context."""
    __slots__ = ('context',)

    def __init__(self, context):
        self.context = context

    def __iter__(self):
        return self

    def next(self):
        ctx = self.context
        ctx.index0 += 1
        return ctx._iterator.next(), ctx


class Macro(object):
    """Wraps a macro."""

    def __init__(self, environment, func, name, arguments, defaults,
                 catch_kwargs, catch_varargs, caller):
        self._environment = environment
        self._func = func
        self._argument_count = len(arguments)
        self.name = name
        self.arguments = arguments
        self.defaults = defaults
        self.catch_kwargs = catch_kwargs
        self.catch_varargs = catch_varargs
        self.caller = caller

    def __call__(self, *args, **kwargs):
        arguments = []
        for idx, name in enumerate(self.arguments):
            try:
                value = args[idx]
            except:
                try:
                    value = kwargs.pop(name)
                except:
                    try:
                        value = self.defaults[idx - self._argument_count]
                    except:
                        value = self._environment.undefined(
                            'parameter %r was not provided' % name, name=name)
            arguments.append(value)

        # it's important that the order of these arguments does not change
        # if not also changed in the compiler's `function_scoping` method.
        # the order is caller, keyword arguments, positional arguments!
        if self.caller:
            caller = kwargs.pop('caller', None)
            if caller is None:
                caller = self._environment.undefined('No caller defined',
                                                     name='caller')
            arguments.append(caller)
        if self.catch_kwargs:
            arguments.append(kwargs)
        elif kwargs:
            raise TypeError('macro %r takes no keyword argument %r' %
                            (self.name, iter(kwargs).next()))
        if self.catch_varargs:
            arguments.append(args[self._argument_count:])
        elif len(args) > self._argument_count:
            raise TypeError('macro %r takes not more than %d argument(s)' %
                            (self.name, len(self.arguments)))
        return self._func(*arguments)

    def __repr__(self):
        return '<%s %s>' % (
            self.__class__.__name__,
            self.name is None and 'anonymous' or repr(self.name)
        )


class Undefined(object):
    """The default undefined type.  This undefined type can be printed and
    iterated over, but every other access will raise an :exc:`UndefinedError`:

    >>> foo = Undefined(name='foo')
    >>> str(foo)
    ''
    >>> not foo
    True
    >>> foo + 42
    Traceback (most recent call last):
      ...
    UndefinedError: 'foo' is undefined
    """
    __slots__ = ('_undefined_hint', '_undefined_obj', '_undefined_name',
                 '_undefined_exception')

    def __init__(self, hint=None, obj=None, name=None, exc=UndefinedError):
        self._undefined_hint = hint
        self._undefined_obj = obj
        self._undefined_name = name
        self._undefined_exception = exc

    def _fail_with_undefined_error(self, *args, **kwargs):
        """Regular callback function for undefined objects that raises an
        `UndefinedError` on call.
        """
        if self._undefined_hint is None:
            if self._undefined_obj is None:
                hint = '%r is undefined' % self._undefined_name
            elif not isinstance(self._undefined_name, basestring):
                hint = '%r object has no element %r' % (
                    self._undefined_obj.__class__.__name__,
                    self._undefined_name
                )
            else:
                hint = '%r object has no attribute %r' % (
                    self._undefined_obj.__class__.__name__,
                    self._undefined_name
                )
        else:
            hint = self._undefined_hint
        raise self._undefined_exception(hint)

    __add__ = __radd__ = __mul__ = __rmul__ = __div__ = __rdiv__ = \
    __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = \
    __mod__ = __rmod__ = __pos__ = __neg__ = __call__ = \
    __getattr__ = __getitem__ = __lt__ = __le__ = __gt__ = __ge__ = \
    __int__ = __float__ = __complex__ = __pow__ = __rpow__ = \
        _fail_with_undefined_error

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u''

    def __len__(self):
        return 0

    def __iter__(self):
        if 0:
            yield None

    def __nonzero__(self):
        return False

    def __repr__(self):
        return 'Undefined'


class DebugUndefined(Undefined):
    """An undefined that returns the debug info when printed.

    >>> foo = DebugUndefined(name='foo')
    >>> str(foo)
    '{{ foo }}'
    >>> not foo
    True
    >>> foo + 42
    Traceback (most recent call last):
      ...
    UndefinedError: 'foo' is undefined
    """
    __slots__ = ()

    def __unicode__(self):
        if self._undefined_hint is None:
            if self._undefined_obj is None:
                return u'{{ %s }}' % self._undefined_name
            return '{{ no such element: %s[%r] }}' % (
                self._undefined_obj.__class__.__name__,
                self._undefined_name
            )
        return u'{{ undefined value printed: %s }}' % self._undefined_hint


class StrictUndefined(Undefined):
    """An undefined that barks on print and iteration as well as boolean
    tests and all kinds of comparisons.  In other words: you can do nothing
    with it except checking if it's defined using the `defined` test.

    >>> foo = StrictUndefined(name='foo')
    >>> str(foo)
    Traceback (most recent call last):
      ...
    UndefinedError: 'foo' is undefined
    >>> not foo
    Traceback (most recent call last):
      ...
    UndefinedError: 'foo' is undefined
    >>> foo + 42
    Traceback (most recent call last):
      ...
    UndefinedError: 'foo' is undefined
    """
    __slots__ = ()
    __iter__ = __unicode__ = __len__ = __nonzero__ = __eq__ = __ne__ = \
        Undefined._fail_with_undefined_error


# remove remaining slots attributes, after the metaclass did the magic they
# are unneeded and irritating as they contain wrong data for the subclasses.
del Undefined.__slots__, DebugUndefined.__slots__, StrictUndefined.__slots__

########NEW FILE########
__FILENAME__ = sandbox
# -*- coding: utf-8 -*-
"""
    jinja2.sandbox
    ~~~~~~~~~~~~~~

    Adds a sandbox layer to Jinja as it was the default behavior in the old
    Jinja 1 releases.  This sandbox is slightly different from Jinja 1 as the
    default behavior is easier to use.

    The behavior can be changed by subclassing the environment.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
import operator
from jinja2.runtime import Undefined
from jinja2.environment import Environment
from jinja2.exceptions import SecurityError
from jinja2.utils import FunctionType, MethodType, TracebackType, CodeType, \
     FrameType, GeneratorType


#: maximum number of items a range may produce
MAX_RANGE = 100000

#: attributes of function objects that are considered unsafe.
UNSAFE_FUNCTION_ATTRIBUTES = set(['func_closure', 'func_code', 'func_dict',
                                  'func_defaults', 'func_globals'])

#: unsafe method attributes.  function attributes are unsafe for methods too
UNSAFE_METHOD_ATTRIBUTES = set(['im_class', 'im_func', 'im_self'])


from collections import deque
from sets import Set, ImmutableSet
from UserDict import UserDict, DictMixin
from UserList import UserList
_mutable_set_types = (ImmutableSet, Set, set)
_mutable_mapping_types = (UserDict, DictMixin, dict)
_mutable_sequence_types = (UserList, list)

#: register Python 2.6 abstract base classes
try:
    from collections import MutableSet, MutableMapping, MutableSequence
    _mutable_set_types += (MutableSet,)
    _mutable_mapping_types += (MutableMapping,)
    _mutable_sequence_types += (MutableSequence,)
except ImportError:
    pass

_mutable_spec = (
    (_mutable_set_types, frozenset([
        'add', 'clear', 'difference_update', 'discard', 'pop', 'remove',
        'symmetric_difference_update', 'update'
    ])),
    (_mutable_mapping_types, frozenset([
        'clear', 'pop', 'popitem', 'setdefault', 'update'
    ])),
    (_mutable_sequence_types, frozenset([
        'append', 'reverse', 'insert', 'sort', 'extend', 'remove'
    ])),
    (deque, frozenset([
        'append', 'appendleft', 'clear', 'extend', 'extendleft', 'pop',
        'popleft', 'remove', 'rotate'
    ]))
)


def safe_range(*args):
    """A range that can't generate ranges with a length of more than
    MAX_RANGE items.
    """
    rng = xrange(*args)
    if len(rng) > MAX_RANGE:
        raise OverflowError('range too big, maximum size for range is %d' %
                            MAX_RANGE)
    return rng


def unsafe(f):
    """
    Mark a function or method as unsafe::

        @unsafe
        def delete(self):
            pass
    """
    f.unsafe_callable = True
    return f


def is_internal_attribute(obj, attr):
    """Test if the attribute given is an internal python attribute.  For
    example this function returns `True` for the `func_code` attribute of
    python objects.  This is useful if the environment method
    :meth:`~SandboxedEnvironment.is_safe_attribute` is overriden.

    >>> from jinja2.sandbox import is_internal_attribute
    >>> is_internal_attribute(lambda: None, "func_code")
    True
    >>> is_internal_attribute((lambda x:x).func_code, 'co_code')
    True
    >>> is_internal_attribute(str, "upper")
    False
    """
    if isinstance(obj, FunctionType):
        if attr in UNSAFE_FUNCTION_ATTRIBUTES:
            return True
    elif isinstance(obj, MethodType):
        if attr in UNSAFE_FUNCTION_ATTRIBUTES or \
           attr in UNSAFE_METHOD_ATTRIBUTES:
            return True
    elif isinstance(obj, type):
        if attr == 'mro':
            return True
    elif isinstance(obj, (CodeType, TracebackType, FrameType)):
        return True
    elif isinstance(obj, GeneratorType):
        if attr == 'gi_frame':
            return True
    return attr.startswith('__')


def modifies_known_mutable(obj, attr):
    """This function checks if an attribute on a builtin mutable object
    (list, dict, set or deque) would modify it if called.  It also supports
    the "user"-versions of the objects (`sets.Set`, `UserDict.*` etc.) and
    with Python 2.6 onwards the abstract base classes `MutableSet`,
    `MutableMapping`, and `MutableSequence`.

    >>> modifies_known_mutable({}, "clear")
    True
    >>> modifies_known_mutable({}, "keys")
    False
    >>> modifies_known_mutable([], "append")
    True
    >>> modifies_known_mutable([], "index")
    False

    If called with an unsupported object (such as unicode) `False` is
    returned.

    >>> modifies_known_mutable("foo", "upper")
    False
    """
    for typespec, unsafe in _mutable_spec:
        if isinstance(obj, typespec):
            return attr in unsafe
    return False


class SandboxedEnvironment(Environment):
    """The sandboxed environment.  It works like the regular environment but
    tells the compiler to generate sandboxed code.  Additionally subclasses of
    this environment may override the methods that tell the runtime what
    attributes or functions are safe to access.

    If the template tries to access insecure code a :exc:`SecurityError` is
    raised.  However also other exceptions may occour during the rendering so
    the caller has to ensure that all exceptions are catched.
    """
    sandboxed = True

    def __init__(self, *args, **kwargs):
        Environment.__init__(self, *args, **kwargs)
        self.globals['range'] = safe_range

    def is_safe_attribute(self, obj, attr, value):
        """The sandboxed environment will call this method to check if the
        attribute of an object is safe to access.  Per default all attributes
        starting with an underscore are considered private as well as the
        special attributes of internal python objects as returned by the
        :func:`is_internal_attribute` function.
        """
        return not (attr.startswith('_') or is_internal_attribute(obj, attr))

    def is_safe_callable(self, obj):
        """Check if an object is safely callable.  Per default a function is
        considered safe unless the `unsafe_callable` attribute exists and is
        True.  Override this method to alter the behavior, but this won't
        affect the `unsafe` decorator from this module.
        """
        return not (getattr(obj, 'unsafe_callable', False) or \
                    getattr(obj, 'alters_data', False))

    def getitem(self, obj, argument):
        """Subscribe an object from sandboxed code."""
        try:
            return obj[argument]
        except (TypeError, LookupError):
            if isinstance(argument, basestring):
                try:
                    attr = str(argument)
                except:
                    pass
                else:
                    try:
                        value = getattr(obj, attr)
                    except AttributeError:
                        pass
                    else:
                        if self.is_safe_attribute(obj, argument, value):
                            return value
                        return self.unsafe_undefined(obj, argument)
        return self.undefined(obj=obj, name=argument)

    def getattr(self, obj, attribute):
        """Subscribe an object from sandboxed code and prefer the
        attribute.  The attribute passed *must* be a bytestring.
        """
        try:
            value = getattr(obj, attribute)
        except AttributeError:
            try:
                return obj[attribute]
            except (TypeError, LookupError):
                pass
        else:
            if self.is_safe_attribute(obj, attribute, value):
                return value
            return self.unsafe_undefined(obj, attribute)
        return self.undefined(obj=obj, name=attribute)

    def unsafe_undefined(self, obj, attribute):
        """Return an undefined object for unsafe attributes."""
        return self.undefined('access to attribute %r of %r '
                              'object is unsafe.' % (
            attribute,
            obj.__class__.__name__
        ), name=attribute, obj=obj, exc=SecurityError)

    def call(__self, __context, __obj, *args, **kwargs):
        """Call an object from sandboxed code."""
        # the double prefixes are to avoid double keyword argument
        # errors when proxying the call.
        if not __self.is_safe_callable(__obj):
            raise SecurityError('%r is not safely callable' % (__obj,))
        return __context.call(__obj, *args, **kwargs)


class ImmutableSandboxedEnvironment(SandboxedEnvironment):
    """Works exactly like the regular `SandboxedEnvironment` but does not
    permit modifications on the builtin mutable objects `list`, `set`, and
    `dict` by using the :func:`modifies_known_mutable` function.
    """

    def is_safe_attribute(self, obj, attr, value):
        if not SandboxedEnvironment.is_safe_attribute(self, obj, attr, value):
            return False
        return not modifies_known_mutable(obj, attr)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
"""
    jinja2.tests
    ~~~~~~~~~~~~

    Jinja test functions. Used with the "is" operator.

    :copyright: 2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import re
from jinja2.runtime import Undefined


number_re = re.compile(r'^-?\d+(\.\d+)?$')
regex_type = type(number_re)


def test_odd(value):
    """Return true if the variable is odd."""
    return value % 2 == 1


def test_even(value):
    """Return true if the variable is even."""
    return value % 2 == 0


def test_divisibleby(value, num):
    """Check if a variable is divisible by a number."""
    return value % num == 0


def test_defined(value):
    """Return true if the variable is defined:

    .. sourcecode:: jinja

        {% if variable is defined %}
            value of variable: {{ variable }}
        {% else %}
            variable is not defined
        {% endif %}

    See the :func:`default` filter for a simple way to set undefined
    variables.
    """
    return not isinstance(value, Undefined)


def test_undefined(value):
    """Like :func:`defined` but the other way round."""
    return isinstance(value, Undefined)


def test_none(value):
    """Return true if the variable is none."""
    return value is None


def test_lower(value):
    """Return true if the variable is lowercased."""
    return unicode(value).islower()


def test_upper(value):
    """Return true if the variable is uppercased."""
    return unicode(value).isupper()


def test_string(value):
    """Return true if the object is a string."""
    return isinstance(value, basestring)


def test_number(value):
    """Return true if the variable is a number."""
    return isinstance(value, (int, long, float, complex))


def test_sequence(value):
    """Return true if the variable is a sequence. Sequences are variables
    that are iterable.
    """
    try:
        len(value)
        value.__getitem__
    except:
        return False
    return True


def test_sameas(value, other):
    """Check if an object points to the same memory address than another
    object:

    .. sourcecode:: jinja

        {% if foo.attribute is sameas false %}
            the foo attribute really is the `False` singleton
        {% endif %}
    """
    return value is other


def test_iterable(value):
    """Check if it's possible to iterate over an object."""
    try:
        iter(value)
    except TypeError:
        return False
    return True


def test_escaped(value):
    """Check if the value is escaped."""
    return hasattr(value, '__html__')


TESTS = {
    'odd':              test_odd,
    'even':             test_even,
    'divisibleby':      test_divisibleby,
    'defined':          test_defined,
    'undefined':        test_undefined,
    'none':             test_none,
    'lower':            test_lower,
    'upper':            test_upper,
    'string':           test_string,
    'number':           test_number,
    'sequence':         test_sequence,
    'iterable':         test_iterable,
    'callable':         callable,
    'sameas':           test_sameas,
    'escaped':          test_escaped
}

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    jinja2.utils
    ~~~~~~~~~~~~

    Utility functions.

    :copyright: 2008 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import re
import sys
import errno
try:
    from thread import allocate_lock
except ImportError:
    from dummy_thread import allocate_lock
from collections import deque
from itertools import imap


_word_split_re = re.compile(r'(\s+)')
_punctuation_re = re.compile(
    '^(?P<lead>(?:%s)*)(?P<middle>.*?)(?P<trail>(?:%s)*)$' % (
        '|'.join(imap(re.escape, ('(', '<', '&lt;'))),
        '|'.join(imap(re.escape, ('.', ',', ')', '>', '\n', '&gt;')))
    )
)
_simple_email_re = re.compile(r'^\S+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+$')
_striptags_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
_entity_re = re.compile(r'&([^;]+);')
_letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
_digits = '0123456789'

# special singleton representing missing values for the runtime
missing = type('MissingType', (), {'__repr__': lambda x: 'missing'})()


# concatenate a list of strings and convert them to unicode.
# unfortunately there is a bug in python 2.4 and lower that causes
# unicode.join trash the traceback.
_concat = u''.join
try:
    def _test_gen_bug():
        raise TypeError(_test_gen_bug)
        yield None
    _concat(_test_gen_bug())
except TypeError, _error:
    if not _error.args or _error.args[0] is not _test_gen_bug:
        def concat(gen):
            try:
                return _concat(list(gen))
            except:
                # this hack is needed so that the current frame
                # does not show up in the traceback.
                exc_type, exc_value, tb = sys.exc_info()
                raise exc_type, exc_value, tb.tb_next
    else:
        concat = _concat
    del _test_gen_bug, _error


# ironpython without stdlib doesn't have keyword
try:
    from keyword import iskeyword as is_python_keyword
except ImportError:
    _py_identifier_re = re.compile(r'^[a-zA-Z_][a-zA-Z0-9]*$')
    def is_python_keyword(name):
        if _py_identifier_re.search(name) is None:
            return False
        try:
            exec name + " = 42"
        except SyntaxError:
            return False
        return True


# common types.  These do exist in the special types module too which however
# does not exist in IronPython out of the box.
class _C(object):
    def method(self): pass
def _func():
    yield None
FunctionType = type(_func)
GeneratorType = type(_func())
MethodType = type(_C.method)
CodeType = type(_C.method.func_code)
try:
    raise TypeError()
except TypeError:
    _tb = sys.exc_info()[2]
    TracebackType = type(_tb)
    FrameType = type(_tb.tb_frame)
del _C, _tb, _func


def contextfunction(f):
    """This decorator can be used to mark a function or method context callable.
    A context callable is passed the active :class:`Context` as first argument when
    called from the template.  This is useful if a function wants to get access
    to the context or functions provided on the context object.  For example
    a function that returns a sorted list of template variables the current
    template exports could look like this::

        @contextfunction
        def get_exported_names(context):
            return sorted(context.exported_vars)
    """
    f.contextfunction = True
    return f


def environmentfunction(f):
    """This decorator can be used to mark a function or method as environment
    callable.  This decorator works exactly like the :func:`contextfunction`
    decorator just that the first argument is the active :class:`Environment`
    and not context.
    """
    f.environmentfunction = True
    return f


def is_undefined(obj):
    """Check if the object passed is undefined.  This does nothing more than
    performing an instance check against :class:`Undefined` but looks nicer.
    This can be used for custom filters or tests that want to react to
    undefined variables.  For example a custom default filter can look like
    this::

        def default(var, default=''):
            if is_undefined(var):
                return default
            return var
    """
    from jinja2.runtime import Undefined
    return isinstance(obj, Undefined)


def consume(iterable):
    """Consumes an iterable without doing anything with it."""
    for event in iterable:
        pass


def clear_caches():
    """Jinja2 keeps internal caches for environments and lexers.  These are
    used so that Jinja2 doesn't have to recreate environments and lexers all
    the time.  Normally you don't have to care about that but if you are
    messuring memory consumption you may want to clean the caches.
    """
    from jinja2.environment import _spontaneous_environments
    from jinja2.lexer import _lexer_cache
    _spontaneous_environments.clear()
    _lexer_cache.clear()


def import_string(import_name, silent=False):
    """Imports an object based on a string.  This use useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If the `silent` is True the return value will be `None` if the import
    fails.

    :return: imported object
    """
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            items = import_name.split('.')
            module = '.'.join(items[:-1])
            obj = items[-1]
        else:
            return __import__(import_name)
        return getattr(__import__(module, None, None, [obj]), obj)
    except (ImportError, AttributeError):
        if not silent:
            raise


def open_if_exists(filename, mode='r'):
    """Returns a file descriptor for the filename if that file exists,
    otherwise `None`.
    """
    try:
        return file(filename, mode)
    except IOError, e:
        if e.errno not in (errno.ENOENT, errno.EISDIR):
            raise


def pformat(obj, verbose=False):
    """Prettyprint an object.  Either use the `pretty` library or the
    builtin `pprint`.
    """
    try:
        from pretty import pretty
        return pretty(obj, verbose=verbose)
    except ImportError:
        from pprint import pformat
        return pformat(obj)


def urlize(text, trim_url_limit=None, nofollow=False):
    """Converts any URLs in text into clickable links. Works on http://,
    https:// and www. links. Links can have trailing punctuation (periods,
    commas, close-parens) and leading punctuation (opening parens) and
    it'll still do the right thing.

    If trim_url_limit is not None, the URLs in link text will be limited
    to trim_url_limit characters.

    If nofollow is True, the URLs in link text will get a rel="nofollow"
    attribute.
    """
    trim_url = lambda x, limit=trim_url_limit: limit is not None \
                         and (x[:limit] + (len(x) >=limit and '...'
                         or '')) or x
    words = _word_split_re.split(unicode(escape(text)))
    nofollow_attr = nofollow and ' rel="nofollow"' or ''
    for i, word in enumerate(words):
        match = _punctuation_re.match(word)
        if match:
            lead, middle, trail = match.groups()
            if middle.startswith('www.') or (
                '@' not in middle and
                not middle.startswith('http://') and
                len(middle) > 0 and
                middle[0] in _letters + _digits and (
                    middle.endswith('.org') or
                    middle.endswith('.net') or
                    middle.endswith('.com')
                )):
                middle = '<a href="http://%s"%s>%s</a>' % (middle,
                    nofollow_attr, trim_url(middle))
            if middle.startswith('http://') or \
               middle.startswith('https://'):
                middle = '<a href="%s"%s>%s</a>' % (middle,
                    nofollow_attr, trim_url(middle))
            if '@' in middle and not middle.startswith('www.') and \
               not ':' in middle and _simple_email_re.match(middle):
                middle = '<a href="mailto:%s">%s</a>' % (middle, middle)
            if lead + middle + trail != word:
                words[i] = lead + middle + trail
    return u''.join(words)


def generate_lorem_ipsum(n=5, html=True, min=20, max=100):
    """Generate some lorem impsum for the template."""
    from jinja2.constants import LOREM_IPSUM_WORDS
    from random import choice, random, randrange
    words = LOREM_IPSUM_WORDS.split()
    result = []

    for _ in xrange(n):
        next_capitalized = True
        last_comma = last_fullstop = 0
        word = None
        last = None
        p = []

        # each paragraph contains out of 20 to 100 words.
        for idx, _ in enumerate(xrange(randrange(min, max))):
            while True:
                word = choice(words)
                if word != last:
                    last = word
                    break
            if next_capitalized:
                word = word.capitalize()
                next_capitalized = False
            # add commas
            if idx - randrange(3, 8) > last_comma:
                last_comma = idx
                last_fullstop += 2
                word += ','
            # add end of sentences
            if idx - randrange(10, 20) > last_fullstop:
                last_comma = last_fullstop = idx
                word += '.'
                next_capitalized = True
            p.append(word)

        # ensure that the paragraph ends with a dot.
        p = u' '.join(p)
        if p.endswith(','):
            p = p[:-1] + '.'
        elif not p.endswith('.'):
            p += '.'
        result.append(p)

    if not html:
        return u'\n\n'.join(result)
    return Markup(u'\n'.join(u'<p>%s</p>' % escape(x) for x in result))


class Markup(unicode):
    r"""Marks a string as being safe for inclusion in HTML/XML output without
    needing to be escaped.  This implements the `__html__` interface a couple
    of frameworks and web applications use.  :class:`Markup` is a direct
    subclass of `unicode` and provides all the methods of `unicode` just that
    it escapes arguments passed and always returns `Markup`.

    The `escape` function returns markup objects so that double escaping can't
    happen.  If you want to use autoescaping in Jinja just enable the
    autoescaping feature in the environment.

    The constructor of the :class:`Markup` class can be used for three
    different things:  When passed an unicode object it's assumed to be safe,
    when passed an object with an HTML representation (has an `__html__`
    method) that representation is used, otherwise the object passed is
    converted into a unicode string and then assumed to be safe:

    >>> Markup("Hello <em>World</em>!")
    Markup(u'Hello <em>World</em>!')
    >>> class Foo(object):
    ...  def __html__(self):
    ...   return '<a href="#">foo</a>'
    ... 
    >>> Markup(Foo())
    Markup(u'<a href="#">foo</a>')

    If you want object passed being always treated as unsafe you can use the
    :meth:`escape` classmethod to create a :class:`Markup` object:

    >>> Markup.escape("Hello <em>World</em>!")
    Markup(u'Hello &lt;em&gt;World&lt;/em&gt;!')

    Operations on a markup string are markup aware which means that all
    arguments are passed through the :func:`escape` function:

    >>> em = Markup("<em>%s</em>")
    >>> em % "foo & bar"
    Markup(u'<em>foo &amp; bar</em>')
    >>> strong = Markup("<strong>%(text)s</strong>")
    >>> strong % {'text': '<blink>hacker here</blink>'}
    Markup(u'<strong>&lt;blink&gt;hacker here&lt;/blink&gt;</strong>')
    >>> Markup("<em>Hello</em> ") + "<foo>"
    Markup(u'<em>Hello</em> &lt;foo&gt;')
    """
    __slots__ = ()

    def __new__(cls, base=u'', encoding=None, errors='strict'):
        if hasattr(base, '__html__'):
            base = base.__html__()
        if encoding is None:
            return unicode.__new__(cls, base)
        return unicode.__new__(cls, base, encoding, errors)

    def __html__(self):
        return self

    def __add__(self, other):
        if hasattr(other, '__html__') or isinstance(other, basestring):
            return self.__class__(unicode(self) + unicode(escape(other)))
        return NotImplemented

    def __radd__(self, other):
        if hasattr(other, '__html__') or isinstance(other, basestring):
            return self.__class__(unicode(escape(other)) + unicode(self))
        return NotImplemented

    def __mul__(self, num):
        if isinstance(num, (int, long)):
            return self.__class__(unicode.__mul__(self, num))
        return NotImplemented
    __rmul__ = __mul__

    def __mod__(self, arg):
        if isinstance(arg, tuple):
            arg = tuple(imap(_MarkupEscapeHelper, arg))
        else:
            arg = _MarkupEscapeHelper(arg)
        return self.__class__(unicode.__mod__(self, arg))

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            unicode.__repr__(self)
        )

    def join(self, seq):
        return self.__class__(unicode.join(self, imap(escape, seq)))
    join.__doc__ = unicode.join.__doc__

    def split(self, *args, **kwargs):
        return map(self.__class__, unicode.split(self, *args, **kwargs))
    split.__doc__ = unicode.split.__doc__

    def rsplit(self, *args, **kwargs):
        return map(self.__class__, unicode.rsplit(self, *args, **kwargs))
    rsplit.__doc__ = unicode.rsplit.__doc__

    def splitlines(self, *args, **kwargs):
        return map(self.__class__, unicode.splitlines(self, *args, **kwargs))
    splitlines.__doc__ = unicode.splitlines.__doc__

    def unescape(self):
        r"""Unescape markup again into an unicode string.  This also resolves
        known HTML4 and XHTML entities:

        >>> Markup("Main &raquo; <em>About</em>").unescape()
        u'Main \xbb <em>About</em>'
        """
        from jinja2.constants import HTML_ENTITIES
        def handle_match(m):
            name = m.group(1)
            if name in HTML_ENTITIES:
                return unichr(HTML_ENTITIES[name])
            try:
                if name[:2] in ('#x', '#X'):
                    return unichr(int(name[2:], 16))
                elif name.startswith('#'):
                    return unichr(int(name[1:]))
            except ValueError:
                pass
            return u''
        return _entity_re.sub(handle_match, unicode(self))

    def striptags(self):
        r"""Unescape markup into an unicode string and strip all tags.  This
        also resolves known HTML4 and XHTML entities.  Whitespace is
        normalized to one:

        >>> Markup("Main &raquo;  <em>About</em>").striptags()
        u'Main \xbb About'
        """
        stripped = u' '.join(_striptags_re.sub('', self).split())
        return Markup(stripped).unescape()

    @classmethod
    def escape(cls, s):
        """Escape the string.  Works like :func:`escape` with the difference
        that for subclasses of :class:`Markup` this function would return the
        correct subclass.
        """
        rv = escape(s)
        if rv.__class__ is not cls:
            return cls(rv)
        return rv

    def make_wrapper(name):
        orig = getattr(unicode, name)
        def func(self, *args, **kwargs):
            args = _escape_argspec(list(args), enumerate(args))
            _escape_argspec(kwargs, kwargs.iteritems())
            return self.__class__(orig(self, *args, **kwargs))
        func.__name__ = orig.__name__
        func.__doc__ = orig.__doc__
        return func

    for method in '__getitem__', '__getslice__', 'capitalize', \
                  'title', 'lower', 'upper', 'replace', 'ljust', \
                  'rjust', 'lstrip', 'rstrip', 'center', 'strip', \
                  'translate', 'expandtabs', 'swapcase', 'zfill':
        locals()[method] = make_wrapper(method)

    # new in python 2.5
    if hasattr(unicode, 'partition'):
        partition = make_wrapper('partition'),
        rpartition = make_wrapper('rpartition')

    # new in python 2.6
    if hasattr(unicode, 'format'):
        format = make_wrapper('format')

    del method, make_wrapper


def _escape_argspec(obj, iterable):
    """Helper for various string-wrapped functions."""
    for key, value in iterable:
        if hasattr(value, '__html__') or isinstance(value, basestring):
            obj[key] = escape(value)
    return obj


class _MarkupEscapeHelper(object):
    """Helper for Markup.__mod__"""

    def __init__(self, obj):
        self.obj = obj

    __getitem__ = lambda s, x: _MarkupEscapeHelper(s.obj[x])
    __unicode__ = lambda s: unicode(escape(s.obj))
    __str__ = lambda s: str(escape(s.obj))
    __repr__ = lambda s: str(escape(repr(s.obj)))
    __int__ = lambda s: int(s.obj)
    __float__ = lambda s: float(s.obj)


class LRUCache(object):
    """A simple LRU Cache implementation."""

    # this is fast for small capacities (something below 1000) but doesn't
    # scale.  But as long as it's only used as storage for templates this
    # won't do any harm.

    def __init__(self, capacity):
        self.capacity = capacity
        self._mapping = {}
        self._queue = deque()
        self._postinit()

    def _postinit(self):
        # alias all queue methods for faster lookup
        self._popleft = self._queue.popleft
        self._pop = self._queue.pop
        if hasattr(self._queue, 'remove'):
            self._remove = self._queue.remove
        self._wlock = allocate_lock()
        self._append = self._queue.append

    def _remove(self, obj):
        """Python 2.4 compatibility."""
        for idx, item in enumerate(self._queue):
            if item == obj:
                del self._queue[idx]
                break

    def __getstate__(self):
        return {
            'capacity':     self.capacity,
            '_mapping':     self._mapping,
            '_queue':       self._queue
        }

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._postinit()

    def __getnewargs__(self):
        return (self.capacity,)

    def copy(self):
        """Return an shallow copy of the instance."""
        rv = self.__class__(self.capacity)
        rv._mapping.update(self._mapping)
        rv._queue = deque(self._queue)
        return rv

    def get(self, key, default=None):
        """Return an item from the cache dict or `default`"""
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        """Set `default` if the key is not in the cache otherwise
        leave unchanged. Return the value of this key.
        """
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def clear(self):
        """Clear the cache."""
        self._wlock.acquire()
        try:
            self._mapping.clear()
            self._queue.clear()
        finally:
            self._wlock.release()

    def __contains__(self, key):
        """Check if a key exists in this cache."""
        return key in self._mapping

    def __len__(self):
        """Return the current size of the cache."""
        return len(self._mapping)

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self._mapping
        )

    def __getitem__(self, key):
        """Get an item from the cache. Moves the item up so that it has the
        highest priority then.

        Raise an `KeyError` if it does not exist.
        """
        rv = self._mapping[key]
        if self._queue[-1] != key:
            self._remove(key)
            self._append(key)
        return rv

    def __setitem__(self, key, value):
        """Sets the value for an item. Moves the item up so that it
        has the highest priority then.
        """
        self._wlock.acquire()
        try:
            if key in self._mapping:
                self._remove(key)
            elif len(self._mapping) == self.capacity:
                del self._mapping[self._popleft()]
            self._append(key)
            self._mapping[key] = value
        finally:
            self._wlock.release()

    def __delitem__(self, key):
        """Remove an item from the cache dict.
        Raise an `KeyError` if it does not exist.
        """
        self._wlock.acquire()
        try:
            del self._mapping[key]
            self._remove(key)
        finally:
            self._wlock.release()

    def items(self):
        """Return a list of items."""
        result = [(key, self._mapping[key]) for key in list(self._queue)]
        result.reverse()
        return result

    def iteritems(self):
        """Iterate over all items."""
        return iter(self.items())

    def values(self):
        """Return a list of all values."""
        return [x[1] for x in self.items()]

    def itervalue(self):
        """Iterate over all values."""
        return iter(self.values())

    def keys(self):
        """Return a list of all keys ordered by most recent usage."""
        return list(self)

    def iterkeys(self):
        """Iterate over all keys in the cache dict, ordered by
        the most recent usage.
        """
        return reversed(tuple(self._queue))

    __iter__ = iterkeys

    def __reversed__(self):
        """Iterate over the values in the cache dict, oldest items
        coming first.
        """
        return iter(tuple(self._queue))

    __copy__ = copy


# register the LRU cache as mutable mapping if possible
try:
    from collections import MutableMapping
    MutableMapping.register(LRUCache)
except ImportError:
    pass


class Cycler(object):
    """A cycle helper for templates."""

    def __init__(self, *items):
        if not items:
            raise RuntimeError('at least one item has to be provided')
        self.items = items
        self.reset()

    def reset(self):
        """Resets the cycle."""
        self.pos = 0

    @property
    def current(self):
        """Returns the current item."""
        return self.items[self.pos]

    def next(self):
        """Goes one item ahead and returns it."""
        rv = self.current
        self.pos = (self.pos + 1) % len(self.items)
        return rv


class Joiner(object):
    """A joining helper for templates."""

    def __init__(self, sep=u', '):
        self.sep = sep
        self.used = False

    def __call__(self):
        if not self.used:
            self.used = True
            return u''
        return self.sep


# we have to import it down here as the speedups module imports the
# markup type which is define above.
try:
    from jinja2._speedups import escape, soft_unicode
except ImportError:
    def escape(s):
        """Convert the characters &, <, >, ' and " in string s to HTML-safe
        sequences.  Use this if you need to display text that might contain
        such characters in HTML.  Marks return value as markup string.
        """
        if hasattr(s, '__html__'):
            return s.__html__()
        return Markup(unicode(s)
            .replace('&', '&amp;')
            .replace('>', '&gt;')
            .replace('<', '&lt;')
            .replace("'", '&#39;')
            .replace('"', '&#34;')
        )

    def soft_unicode(s):
        """Make a string unicode if it isn't already.  That way a markup
        string is not converted back to unicode.
        """
        if not isinstance(s, unicode):
            s = unicode(s)
        return s


# partials
try:
    from functools import partial
except ImportError:
    class partial(object):
        def __init__(self, _func, *args, **kwargs):
            self._func = _func
            self._args = args
            self._kwargs = kwargs
        def __call__(self, *args, **kwargs):
            kwargs.update(self._kwargs)
            return self._func(*(self._args + args), **kwargs)

########NEW FILE########
__FILENAME__ = visitor
# -*- coding: utf-8 -*-
"""
    jinja2.visitor
    ~~~~~~~~~~~~~~

    This module implements a visitor for the nodes.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
from jinja2.nodes import Node


class NodeVisitor(object):
    """Walks the abstract syntax tree and call visitor functions for every
    node found.  The visitor functions may return values which will be
    forwarded by the `visit` method.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `get_visitor` function.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.
    """

    def get_visitor(self, node):
        """Return the visitor function for this node or `None` if no visitor
        exists for this node.  In that case the generic visit function is
        used instead.
        """
        method = 'visit_' + node.__class__.__name__
        return getattr(self, method, None)

    def visit(self, node, *args, **kwargs):
        """Visit a node."""
        f = self.get_visitor(node)
        if f is not None:
            return f(node, *args, **kwargs)
        return self.generic_visit(node, *args, **kwargs)

    def generic_visit(self, node, *args, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        for node in node.iter_child_nodes():
            self.visit(node, *args, **kwargs)


class NodeTransformer(NodeVisitor):
    """Walks the abstract syntax tree and allows modifications of nodes.

    The `NodeTransformer` will walk the AST and use the return value of the
    visitor functions to replace or remove the old node.  If the return
    value of the visitor function is `None` the node will be removed
    from the previous location otherwise it's replaced with the return
    value.  The return value may be the original node in which case no
    replacement takes place.
    """

    def generic_visit(self, node, *args, **kwargs):
        for field, old_value in node.iter_fields():
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, Node):
                        value = self.visit(value, *args, **kwargs)
                        if value is None:
                            continue
                        elif not isinstance(value, Node):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, Node):
                new_node = self.visit(old_value, *args, **kwargs)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node

    def visit_list(self, node, *args, **kwargs):
        """As transformers may return lists in some places this method
        can be used to enforce a list as return value.
        """
        rv = self.visit(node, *args, **kwargs)
        if not isinstance(rv, list):
            rv = [rv]
        return rv

########NEW FILE########
__FILENAME__ = _ipysupport
# -*- coding: utf-8 -*-
"""
    jinja2._ipysupport
    ~~~~~~~~~~~~~~~~~~

    IronPython support library.  This library exports functionality from
    the CLR to Python that is normally available in the standard library.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
from System import DateTime
from System.IO import Path, File, FileInfo


epoch = DateTime(1970, 1, 1)


class _PathModule(object):
    """A minimal path module."""

    sep = str(Path.DirectorySeparatorChar)
    altsep = str(Path.AltDirectorySeparatorChar)
    pardir = '..'

    def join(self, path, *args):
        args = list(args[::-1])
        while args:
            path = Path.Combine(path, args.pop())
        return path

    def isfile(self, filename):
        return File.Exists(filename)

    def getmtime(self, filename):
        info = FileInfo(filename)
        return int((info.LastAccessTimeUtc - epoch).TotalSeconds)


path = _PathModule()

########NEW FILE########
__FILENAME__ = filter
# -*- coding: utf-8 -*-
"""
    pygments.filter
    ~~~~~~~~~~~~~~~

    Module that implements the default filter.

    :copyright: 2006-2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""


def apply_filters(stream, filters, lexer=None):
    """
    Use this method to apply an iterable of filters to
    a stream. If lexer is given it's forwarded to the
    filter, otherwise the filter receives `None`.
    """
    def _apply(filter_, stream):
        for token in filter_.filter(lexer, stream):
            yield token
    for filter_ in filters:
        stream = _apply(filter_, stream)
    return stream


def simplefilter(f):
    """
    Decorator that converts a function into a filter::

        @simplefilter
        def lowercase(lexer, stream, options):
            for ttype, value in stream:
                yield ttype, value.lower()
    """
    return type(f.__name__, (FunctionFilter,), {
                'function':     f,
                '__module__':   getattr(f, '__module__'),
                '__doc__':      f.__doc__
            })


class Filter(object):
    """
    Default filter. Subclass this class or use the `simplefilter`
    decorator to create own filters.
    """

    def __init__(self, **options):
        self.options = options

    def filter(self, lexer, stream):
        raise NotImplementedError()


class FunctionFilter(Filter):
    """
    Abstract class used by `simplefilter` to create simple
    function filters on the fly. The `simplefilter` decorator
    automatically creates subclasses of this class for
    functions passed to it.
    """
    function = None

    def __init__(self, **options):
        if not hasattr(self, 'function'):
            raise TypeError('%r used without bound function' %
                            self.__class__.__name__)
        Filter.__init__(self, **options)

    def filter(self, lexer, stream):
        # pylint: disable-msg=E1102
        for ttype, value in self.function(lexer, stream, self.options):
            yield ttype, value

########NEW FILE########
__FILENAME__ = formatter
# -*- coding: utf-8 -*-
"""
    pygments.formatter
    ~~~~~~~~~~~~~~~~~~

    Base formatter class.

    :copyright: 2006-2007 by Georg Brandl, Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

from pygments.util import get_bool_opt
from pygments.styles import get_style_by_name

__all__ = ['Formatter']


def _lookup_style(style):
    if isinstance(style, basestring):
        return get_style_by_name(style)
    return style


class Formatter(object):
    """
    Converts a token stream to text.

    Options accepted:

    ``style``
        The style to use, can be a string or a Style subclass
        (default: "default"). Not used by e.g. the
        TerminalFormatter.
    ``full``
        Tells the formatter to output a "full" document, i.e.
        a complete self-contained document. This doesn't have
        any effect for some formatters (default: false).
    ``title``
        If ``full`` is true, the title that should be used to
        caption the document (default: '').
    ``encoding``
        If given, must be an encoding name. This will be used to
        convert the Unicode token strings to byte strings in the
        output. If it is "" or None, Unicode strings will be written
        to the output file, which most file-like objects do not
        support (default: None).
    ``outencoding``
        Overrides ``encoding`` if given.
    """

    #: Name of the formatter
    name = None

    #: Shortcuts for the formatter
    aliases = []

    #: fn match rules
    filenames = []

    #: If True, this formatter outputs Unicode strings when no encoding
    #: option is given.
    unicodeoutput = True

    def __init__(self, **options):
        self.style = _lookup_style(options.get('style', 'default'))
        self.full  = get_bool_opt(options, 'full', False)
        self.title = options.get('title', '')
        self.encoding = options.get('encoding', None) or None
        self.encoding = options.get('outencoding', None) or self.encoding
        self.options = options

    def get_style_defs(self, arg=''):
        """
        Return the style definitions for the current style as a string.

        ``arg`` is an additional argument whose meaning depends on the
        formatter used. Note that ``arg`` can also be a list or tuple
        for some formatters like the html formatter.
        """
        return ''

    def format(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.
        """
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = html
# -*- coding: utf-8 -*-
"""
    pygments.formatters.html
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for HTML output.

    :copyright: 2006-2008 by Georg Brandl, Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys, os
import StringIO

try:
    set
except NameError:
    from sets import Set as set

from pygments.formatter import Formatter
from pygments.token import Token, Text, STANDARD_TYPES
from pygments.util import get_bool_opt, get_int_opt, get_list_opt


__all__ = ['HtmlFormatter']


def escape_html(text):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.replace('&', '&amp;').  \
                replace('<', '&lt;').   \
                replace('>', '&gt;').   \
                replace('"', '&quot;'). \
                replace("'", '&#39;')


def get_random_id():
    """Return a random id for javascript fields."""
    from random import random
    from time import time
    try:
        from hashlib import sha1 as sha
    except ImportError:
        import sha
        sha = sha.new
    return sha('%s|%s' % (random(), time())).hexdigest()


def _get_ttype_class(ttype):
    fname = STANDARD_TYPES.get(ttype)
    if fname:
        return fname
    aname = ''
    while fname is None:
        aname = '-' + ttype[-1] + aname
        ttype = ttype.parent
        fname = STANDARD_TYPES.get(ttype)
    return fname + aname


CSSFILE_TEMPLATE = '''\
td.linenos { background-color: #f0f0f0; padding-right: 10px; }
span.lineno { background-color: #f0f0f0; padding: 0 5px 0 5px; }
pre { line-height: 125%%; }
%(styledefs)s
'''

DOC_HEADER = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <style type="text/css">
''' + CSSFILE_TEMPLATE + '''
  </style>
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_HEADER_EXTERNALCSS = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <link rel="stylesheet" href="%(cssfile)s" type="text/css">
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_FOOTER = '''\
</body>
</html>
'''


class HtmlFormatter(Formatter):
    r"""
    Format tokens as HTML 4 ``<span>`` tags within a ``<pre>`` tag, wrapped
    in a ``<div>`` tag. The ``<div>``'s CSS class can be set by the `cssclass`
    option.

    If the `linenos` option is set to ``"table"``, the ``<pre>`` is
    additionally wrapped inside a ``<table>`` which has one row and two
    cells: one containing the line numbers and one containing the code.
    Example:

    .. sourcecode:: html

        <div class="highlight" >
        <table><tr>
          <td class="linenos" title="click to toggle"
            onclick="with (this.firstChild.style)
                     { display = (display == '') ? 'none' : '' }">
            <pre>1
            2</pre>
          </td>
          <td class="code">
            <pre><span class="Ke">def </span><span class="NaFu">foo</span>(bar):
              <span class="Ke">pass</span>
            </pre>
          </td>
        </tr></table></div>

    (whitespace added to improve clarity).

    Wrapping can be disabled using the `nowrap` option.

    A list of lines can be specified using the `hl_lines` option to make these
    lines highlighted (as of Pygments 0.11).

    With the `full` option, a complete HTML 4 document is output, including
    the style definitions inside a ``<style>`` tag, or in a separate file if
    the `cssfile` option is given.

    The `get_style_defs(arg='')` method of a `HtmlFormatter` returns a string
    containing CSS rules for the CSS classes used by the formatter. The
    argument `arg` can be used to specify additional CSS selectors that
    are prepended to the classes. A call `fmter.get_style_defs('td .code')`
    would result in the following CSS classes:

    .. sourcecode:: css

        td .code .kw { font-weight: bold; color: #00FF00 }
        td .code .cm { color: #999999 }
        ...

    If you have Pygments 0.6 or higher, you can also pass a list or tuple to the
    `get_style_defs()` method to request multiple prefixes for the tokens:

    .. sourcecode:: python

        formatter.get_style_defs(['div.syntax pre', 'pre.syntax'])

    The output would then look like this:

    .. sourcecode:: css

        div.syntax pre .kw,
        pre.syntax .kw { font-weight: bold; color: #00FF00 }
        div.syntax pre .cm,
        pre.syntax .cm { color: #999999 }
        ...

    Additional options accepted:

    `nowrap`
        If set to ``True``, don't wrap the tokens at all, not even inside a ``<pre>``
        tag. This disables most other options (default: ``False``).

    `full`
        Tells the formatter to output a "full" document, i.e. a complete
        self-contained document (default: ``False``).

    `title`
        If `full` is true, the title that should be used to caption the
        document (default: ``''``).

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `noclasses`
        If set to true, token ``<span>`` tags will not use CSS classes, but
        inline styles. This is not recommended for larger pieces of code since
        it increases output size by quite a bit (default: ``False``).

    `classprefix`
        Since the token types use relatively short class names, they may clash
        with some of your own class names. In this case you can use the
        `classprefix` option to give a string to prepend to all Pygments-generated
        CSS class names for token types.
        Note that this option also affects the output of `get_style_defs()`.

    `cssclass`
        CSS class for the wrapping ``<div>`` tag (default: ``'highlight'``).
        If you set this option, the default selector for `get_style_defs()`
        will be this class.

        *New in Pygments 0.9:* If you select the ``'table'`` line numbers, the
        wrapping table will have a CSS class of this string plus ``'table'``,
        the default is accordingly ``'highlighttable'``.

    `cssstyles`
        Inline CSS styles for the wrapping ``<div>`` tag (default: ``''``).

    `prestyles`
        Inline CSS styles for the ``<pre>`` tag (default: ``''``).  *New in
        Pygments 0.11.*

    `cssfile`
        If the `full` option is true and this option is given, it must be the
        name of an external file. If the filename does not include an absolute
        path, the file's path will be assumed to be relative to the main output
        file's path, if the latter can be found. The stylesheet is then written
        to this file instead of the HTML file. *New in Pygments 0.6.*

    `linenos`
        If set to ``'table'``, output line numbers as a table with two cells,
        one containing the line numbers, the other the whole code.  This is
        copy-and-paste-friendly, but may cause alignment problems with some
        browsers or fonts.  If set to ``'inline'``, the line numbers will be
        integrated in the ``<pre>`` tag that contains the code (that setting
        is *new in Pygments 0.8*).

        For compatibility with Pygments 0.7 and earlier, every true value
        except ``'inline'`` means the same as ``'table'`` (in particular, that
        means also ``True``).

        The default value is ``False``, which means no line numbers at all.

        **Note:** with the default ("table") line number mechanism, the line
        numbers and code can have different line heights in Internet Explorer
        unless you give the enclosing ``<pre>`` tags an explicit ``line-height``
        CSS property (you get the default line spacing with ``line-height:
        125%``).

    `hl_lines`
        Specify a list of lines to be highlighted.  *New in Pygments 0.11.*

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `linenospecial`
        If set to a number n > 0, every nth line number is given the CSS
        class ``"special"`` (default: ``0``).

    `nobackground`
        If set to ``True``, the formatter won't output the background color
        for the wrapping element (this automatically defaults to ``False``
        when there is no wrapping element [eg: no argument for the
        `get_syntax_defs` method given]) (default: ``False``). *New in
        Pygments 0.6.*

    `lineseparator`
        This string is output between lines of code. It defaults to ``"\n"``,
        which is enough to break a line inside ``<pre>`` tags, but you can
        e.g. set it to ``"<br>"`` to get HTML line breaks. *New in Pygments
        0.7.*

    `lineanchors`
        If set to a nonempty string, e.g. ``foo``, the formatter will wrap each
        output line in an anchor tag with a ``name`` of ``foo-linenumber``.
        This allows easy linking to certain lines. *New in Pygments 0.9.*


    **Subclassing the HTML formatter**

    *New in Pygments 0.7.*

    The HTML formatter is now built in a way that allows easy subclassing, thus
    customizing the output HTML code. The `format()` method calls
    `self._format_lines()` which returns a generator that yields tuples of ``(1,
    line)``, where the ``1`` indicates that the ``line`` is a line of the
    formatted source code.

    If the `nowrap` option is set, the generator is the iterated over and the
    resulting HTML is output.

    Otherwise, `format()` calls `self.wrap()`, which wraps the generator with
    other generators. These may add some HTML code to the one generated by
    `_format_lines()`, either by modifying the lines generated by the latter,
    then yielding them again with ``(1, line)``, and/or by yielding other HTML
    code before or after the lines, with ``(0, html)``. The distinction between
    source lines and other code makes it possible to wrap the generator multiple
    times.

    The default `wrap()` implementation adds a ``<div>`` and a ``<pre>`` tag.

    A custom `HtmlFormatter` subclass could look like this:

    .. sourcecode:: python

        class CodeHtmlFormatter(HtmlFormatter):

            def wrap(self, source, outfile):
                return self._wrap_code(source)

            def _wrap_code(self, source):
                yield 0, '<code>'
                for i, t in source:
                    if i == 1:
                        # it's a line of formatted code
                        t += '<br>'
                    yield i, t
                yield 0, '</code>'

    This results in wrapping the formatted lines with a ``<code>`` tag, where the
    source lines are broken using ``<br>`` tags.

    After calling `wrap()`, the `format()` method also adds the "line numbers"
    and/or "full document" wrappers if the respective options are set. Then, all
    HTML yielded by the wrapped generator is output.
    """

    name = 'HTML'
    aliases = ['html']
    filenames = ['*.html', '*.htm']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.title = self._encodeifneeded(self.title)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.noclasses = get_bool_opt(options, 'noclasses', False)
        self.classprefix = options.get('classprefix', '')
        self.cssclass = self._encodeifneeded(options.get('cssclass', 'highlight'))
        self.cssstyles = self._encodeifneeded(options.get('cssstyles', ''))
        self.prestyles = self._encodeifneeded(options.get('prestyles', ''))
        self.cssfile = self._encodeifneeded(options.get('cssfile', ''))
        linenos = options.get('linenos', False)
        if linenos == 'inline':
            self.linenos = 2
        elif linenos:
            # compatibility with <= 0.7
            self.linenos = 1
        else:
            self.linenos = 0
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.linenospecial = abs(get_int_opt(options, 'linenospecial', 0))
        self.nobackground = get_bool_opt(options, 'nobackground', False)
        self.lineseparator = options.get('lineseparator', '\n')
        self.lineanchors = options.get('lineanchors', '')
        self.hl_lines = set()
        for lineno in get_list_opt(options, 'hl_lines', []):
            try:
                self.hl_lines.add(int(lineno))
            except ValueError:
                pass

        self._class_cache = {}
        self._create_stylesheet()

    def _get_css_class(self, ttype):
        """Return the css class of this token type prefixed with
        the classprefix option."""
        if ttype in self._class_cache:
            return self._class_cache[ttype]
        return self.classprefix + _get_ttype_class(ttype)

    def _create_stylesheet(self):
        t2c = self.ttype2class = {Token: ''}
        c2s = self.class2style = {}
        cp = self.classprefix
        for ttype, ndef in self.style:
            name = cp + _get_ttype_class(ttype)
            style = ''
            if ndef['color']:
                style += 'color: #%s; ' % ndef['color']
            if ndef['bold']:
                style += 'font-weight: bold; '
            if ndef['italic']:
                style += 'font-style: italic; '
            if ndef['underline']:
                style += 'text-decoration: underline; '
            if ndef['bgcolor']:
                style += 'background-color: #%s; ' % ndef['bgcolor']
            if ndef['border']:
                style += 'border: 1px solid #%s; ' % ndef['border']
            if style:
                t2c[ttype] = name
                # save len(ttype) to enable ordering the styles by
                # hierarchy (necessary for CSS cascading rules!)
                c2s[name] = (style[:-2], ttype, len(ttype))

    def get_style_defs(self, arg=None):
        """
        Return CSS style definitions for the classes produced by the current
        highlighting style. ``arg`` can be a string or list of selectors to
        insert before the token type classes.
        """
        if arg is None:
            arg = ('cssclass' in self.options and '.'+self.cssclass or '')
        if isinstance(arg, basestring):
            args = [arg]
        else:
            args = list(arg)

        def prefix(cls):
            if cls:
                cls = '.' + cls
            tmp = []
            for arg in args:
                tmp.append((arg and arg + ' ' or '') + cls)
            return ', '.join(tmp)

        styles = [(level, ttype, cls, style)
                  for cls, (style, ttype, level) in self.class2style.iteritems()
                  if cls and style]
        styles.sort()
        lines = ['%s { %s } /* %s */' % (prefix(cls), style, repr(ttype)[6:])
                 for (level, ttype, cls, style) in styles]
        if arg and not self.nobackground and \
           self.style.background_color is not None:
            text_style = ''
            if Text in self.ttype2class:
                text_style = ' ' + self.class2style[self.ttype2class[Text]][0]
            lines.insert(0, '%s { background: %s;%s }' %
                         (prefix(''), self.style.background_color, text_style))
        if self.style.highlight_color is not None:
            lines.insert(0, '%s.hll { background-color: %s }' %
                         (prefix(''), self.style.highlight_color))
        return '\n'.join(lines)

    def _encodeifneeded(self, value):
        if not self.encoding or isinstance(value, str):
            return value
        return value.encode(self.encoding)

    def _wrap_full(self, inner, outfile):
        if self.cssfile:
            if os.path.isabs(self.cssfile):
                # it's an absolute filename
                cssfilename = self.cssfile
            else:
                try:
                    filename = outfile.name
                    if not filename or filename[0] == '<':
                        # pseudo files, e.g. name == '<fdopen>'
                        raise AttributeError
                    cssfilename = os.path.join(os.path.dirname(filename), self.cssfile)
                except AttributeError:
                    print >>sys.stderr, 'Note: Cannot determine output file name, ' \
                          'using current directory as base for the CSS file name'
                    cssfilename = self.cssfile
            # write CSS file
            try:
                cf = open(cssfilename, "w")
                cf.write(CSSFILE_TEMPLATE %
                         {'styledefs': self.get_style_defs('body')})
                cf.close()
            except IOError, err:
                err.strerror = 'Error writing CSS file: ' + err.strerror
                raise

            yield 0, (DOC_HEADER_EXTERNALCSS %
                      dict(title     = self.title,
                           cssfile   = self.cssfile,
                           encoding  = self.encoding))
        else:
            yield 0, (DOC_HEADER %
                      dict(title     = self.title,
                           styledefs = self.get_style_defs('body'),
                           encoding  = self.encoding))

        for t, line in inner:
            yield t, line
        yield 0, DOC_FOOTER

    def _wrap_tablelinenos(self, inner):
        dummyoutfile = StringIO.StringIO()
        lncount = 0
        for t, line in inner:
            if t:
                lncount += 1
            dummyoutfile.write(line)

        fl = self.linenostart
        mw = len(str(lncount + fl - 1))
        sp = self.linenospecial
        st = self.linenostep
        if sp:
            ls = '\n'.join([(i%st == 0 and
                             (i%sp == 0 and '<span class="special">%*d</span>'
                              or '%*d') % (mw, i)
                             or '')
                            for i in range(fl, fl + lncount)])
        else:
            ls = '\n'.join([(i%st == 0 and ('%*d' % (mw, i)) or '')
                            for i in range(fl, fl + lncount)])

        yield 0, ('<table class="%stable">' % self.cssclass +
                  '<tr><td class="linenos"><pre>' +
                  ls + '</pre></td><td class="code">')
        yield 0, dummyoutfile.getvalue()
        yield 0, '</td></tr></table>'

    def _wrap_inlinelinenos(self, inner):
        # need a list of lines since we need the width of a single number :(
        lines = list(inner)
        sp = self.linenospecial
        st = self.linenostep
        num = self.linenostart
        mw = len(str(len(lines) + num - 1))

        if sp:
            for t, line in lines:
                yield 1, '<span class="lineno%s">%*s</span> ' % (
                    num%sp == 0 and ' special' or '', mw, (num%st and ' ' or num)) + line
                num += 1
        else:
            for t, line in lines:
                yield 1, '<span class="lineno">%*s</span> ' % (
                    mw, (num%st and ' ' or num)) + line
                num += 1

    def _wrap_lineanchors(self, inner):
        s = self.lineanchors
        i = 0
        for t, line in inner:
            if t:
                i += 1
                yield 1, '<a name="%s-%d"></a>' % (s, i) + line
            else:
                yield 0, line

    def _wrap_div(self, inner):
        yield 0, ('<div' + (self.cssclass and ' class="%s"' % self.cssclass)
                  + (self.cssstyles and ' style="%s"' % self.cssstyles) + '>')
        for tup in inner:
            yield tup
        yield 0, '</div>\n'

    def _wrap_pre(self, inner):
        yield 0, ('<pre'
                  + (self.prestyles and ' style="%s"' % self.prestyles) + '>')
        for tup in inner:
            yield tup
        yield 0, '</pre>'

    def _format_lines(self, tokensource):
        """
        Just format the tokens, without any wrapping tags.
        Yield individual lines.
        """
        nocls = self.noclasses
        enc = self.encoding
        lsep = self.lineseparator
        # for <span style=""> lookup only
        getcls = self.ttype2class.get
        c2s = self.class2style

        lspan = ''
        line = ''
        for ttype, value in tokensource:
            if nocls:
                cclass = getcls(ttype)
                while cclass is None:
                    ttype = ttype.parent
                    cclass = getcls(ttype)
                cspan = cclass and '<span style="%s">' % c2s[cclass][0] or ''
            else:
                cls = self._get_css_class(ttype)
                cspan = cls and '<span class="%s">' % cls or ''

            if enc:
                value = value.encode(enc)

            parts = escape_html(value).split('\n')

            # for all but the last line
            for part in parts[:-1]:
                if line:
                    if lspan != cspan:
                        line += (lspan and '</span>') + cspan + part + \
                                (cspan and '</span>') + lsep
                    else: # both are the same
                        line += part + (lspan and '</span>') + lsep
                    yield 1, line
                    line = ''
                elif part:
                    yield 1, cspan + part + (cspan and '</span>') + lsep
                else:
                    yield 1, lsep
            # for the last line
            if line and parts[-1]:
                if lspan != cspan:
                    line += (lspan and '</span>') + cspan + parts[-1]
                    lspan = cspan
                else:
                    line += parts[-1]
            elif parts[-1]:
                line = cspan + parts[-1]
                lspan = cspan
            # else we neither have to open a new span nor set lspan

        if line:
            yield 1, line + (lspan and '</span>') + lsep

    def _highlight_lines(self, tokensource):
        """
        Highlighted the lines specified in the `hl_lines` option by
        post-processing the token stream coming from `_format_lines`.
        """
        hls = self.hl_lines

        for i, (t, value) in enumerate(tokensource):
            if t != 1:
                yield t, value
            if i + 1 in hls: # i + 1 because Python indexes start at 0
                yield 1, '<span class="hll">%s</span>' % value
            else:
                yield 1, value

    def wrap(self, source, outfile):
        """
        Wrap the ``source``, which is a generator yielding
        individual lines, in custom generators. See docstring
        for `format`. Can be overridden.
        """
        return self._wrap_div(self._wrap_pre(source))

    def format(self, tokensource, outfile):
        """
        The formatting process uses several nested generators; which of
        them are used is determined by the user's options.

        Each generator should take at least one argument, ``inner``,
        and wrap the pieces of text generated by this.

        Always yield 2-tuples: (code, text). If "code" is 1, the text
        is part of the original tokensource being highlighted, if it's
        0, the text is some piece of wrapping. This makes it possible to
        use several different wrappers that process the original source
        linewise, e.g. line number generators.
        """
        source = self._format_lines(tokensource)
        if self.hl_lines:
            source = self._highlight_lines(source)
        if not self.nowrap:
            if self.linenos == 2:
                source = self._wrap_inlinelinenos(source)
            if self.lineanchors:
                source = self._wrap_lineanchors(source)
            source = self.wrap(source, outfile)
            if self.linenos == 1:
                source = self._wrap_tablelinenos(source)
            if self.full:
                source = self._wrap_full(source, outfile)

        for t, piece in source:
            outfile.write(piece)

########NEW FILE########
__FILENAME__ = _mapping
# -*- coding: utf-8 -*-
"""
    pygments.formatters._mapping
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter mapping defintions. This file is generated by itself. Everytime
    you change something on a builtin formatter defintion, run this script from
    the formatters folder to update it.

    Do not alter the FORMATTERS dictionary by hand.

    :copyright: 2006-2007 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""

from pygments.util import docstring_headline

# start
from pygments.formatters.html import HtmlFormatter

FORMATTERS = {
    HtmlFormatter: ('HTML', ('html',), ('*.html', '*.htm'), "Format tokens as HTML 4 ``<span>`` tags within a ``<pre>`` tag, wrapped in a ``<div>`` tag. The ``<div>``'s CSS class can be set by the `cssclass` option."),
}

if __name__ == '__main__':
    import sys
    import os

    # lookup formatters
    found_formatters = []
    imports = []
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    for filename in os.listdir('.'):
        if filename.endswith('.py') and not filename.startswith('_'):
            module_name = 'pygments.formatters.%s' % filename[:-3]
            print module_name
            module = __import__(module_name, None, None, [''])
            for formatter_name in module.__all__:
                imports.append((module_name, formatter_name))
                formatter = getattr(module, formatter_name)
                found_formatters.append(
                    '%s: %r' % (formatter_name,
                                (formatter.name,
                                 tuple(formatter.aliases),
                                 tuple(formatter.filenames),
                                 docstring_headline(formatter))))
    # sort them, that should make the diff files for svn smaller
    found_formatters.sort()
    imports.sort()

    # extract useful sourcecode from this file
    f = open(__file__)
    try:
        content = f.read()
    finally:
        f.close()
    header = content[:content.find('# start')]
    footer = content[content.find("if __name__ == '__main__':"):]

    # write new file
    f = open(__file__, 'w')
    f.write(header)
    f.write('# start\n')
    f.write('\n'.join(['from %s import %s' % imp for imp in imports]))
    f.write('\n\n')
    f.write('FORMATTERS = {\n    %s\n}\n\n' % ',\n    '.join(found_formatters))
    f.write(footer)
    f.close()

########NEW FILE########
__FILENAME__ = lexer
# -*- coding: utf-8 -*-
"""
    pygments.lexer
    ~~~~~~~~~~~~~~

    Base lexer classes.

    :copyright: 2006-2007 by Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import re

try:
    set
except NameError:
    from sets import Set as set

from pygments.filter import apply_filters, Filter
from pygments.filters import get_filter_by_name
from pygments.token import Error, Text, Other, _TokenType
from pygments.util import get_bool_opt, get_int_opt, get_list_opt, \
     make_analysator


__all__ = ['Lexer', 'RegexLexer', 'ExtendedRegexLexer', 'DelegatingLexer',
           'LexerContext', 'include', 'flags', 'bygroups', 'using', 'this']


_default_analyse = staticmethod(lambda x: 0.0)


class LexerMeta(type):
    """
    This metaclass automagically converts ``analyse_text`` methods into
    static methods which always return float values.
    """

    def __new__(cls, name, bases, d):
        if 'analyse_text' in d:
            d['analyse_text'] = make_analysator(d['analyse_text'])
        return type.__new__(cls, name, bases, d)


class Lexer(object):
    """
    Lexer for a specific language.

    Basic options recognized:
    ``stripnl``
        Strip leading and trailing newlines from the input (default: True).
    ``stripall``
        Strip all leading and trailing whitespace from the input
        (default: False).
    ``tabsize``
        If given and greater than 0, expand tabs in the input (default: 0).
    ``encoding``
        If given, must be an encoding name. This encoding will be used to
        convert the input string to Unicode, if it is not already a Unicode
        string (default: ``'latin1'``).
        Can also be ``'guess'`` to use a simple UTF-8 / Latin1 detection, or
        ``'chardet'`` to use the chardet library, if it is installed.
    """

    #: Name of the lexer
    name = None

    #: Shortcuts for the lexer
    aliases = []

    #: fn match rules
    filenames = []

    #: fn alias filenames
    alias_filenames = []

    #: mime types
    mimetypes = []

    __metaclass__ = LexerMeta

    def __init__(self, **options):
        self.options = options
        self.stripnl = get_bool_opt(options, 'stripnl', True)
        self.stripall = get_bool_opt(options, 'stripall', False)
        self.tabsize = get_int_opt(options, 'tabsize', 0)
        self.encoding = options.get('encoding', 'latin1')
        # self.encoding = options.get('inencoding', None) or self.encoding
        self.filters = []
        for filter_ in get_list_opt(options, 'filters', ()):
            self.add_filter(filter_)

    def __repr__(self):
        if self.options:
            return '<pygments.lexers.%s with %r>' % (self.__class__.__name__,
                                                     self.options)
        else:
            return '<pygments.lexers.%s>' % self.__class__.__name__

    def add_filter(self, filter_, **options):
        """
        Add a new stream filter to this lexer.
        """
        if not isinstance(filter_, Filter):
            filter_ = get_filter_by_name(filter_, **options)
        self.filters.append(filter_)

    def analyse_text(text):
        """
        Has to return a float between ``0`` and ``1`` that indicates
        if a lexer wants to highlight this text. Used by ``guess_lexer``.
        If this method returns ``0`` it won't highlight it in any case, if
        it returns ``1`` highlighting with this lexer is guaranteed.

        The `LexerMeta` metaclass automatically wraps this function so
        that it works like a static method (no ``self`` or ``cls``
        parameter) and the return value is automatically converted to
        `float`. If the return value is an object that is boolean `False`
        it's the same as if the return values was ``0.0``.
        """

    def get_tokens(self, text, unfiltered=False):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.
        """
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        if not isinstance(text, unicode):
            if self.encoding == 'guess':
                try:
                    text = text.decode('utf-8')
                    if text.startswith(u'\ufeff'):
                        text = text[len(u'\ufeff'):]
                except UnicodeDecodeError:
                    text = text.decode('latin1')
            elif self.encoding == 'chardet':
                try:
                    import chardet
                except ImportError:
                    raise ImportError('To enable chardet encoding guessing, '
                                      'please install the chardet library '
                                      'from http://chardet.feedparser.org/')
                enc = chardet.detect(text)
                text = text.decode(enc['encoding'])
            else:
                text = text.decode(self.encoding)
        if self.stripall:
            text = text.strip()
        elif self.stripnl:
            text = text.strip('\n')
        if self.tabsize > 0:
            text = text.expandtabs(self.tabsize)
        if not text.endswith('\n'):
            text += '\n'

        def streamer():
            for i, t, v in self.get_tokens_unprocessed(text):
                yield t, v
        stream = streamer()
        if not unfiltered:
            stream = apply_filters(stream, self.filters, self)
        return stream

    def get_tokens_unprocessed(self, text):
        """
        Return an iterable of (tokentype, value) pairs.
        In subclasses, implement this method as a generator to
        maximize effectiveness.
        """
        raise NotImplementedError


class DelegatingLexer(Lexer):
    """
    This lexer takes two lexer as arguments. A root lexer and
    a language lexer. First everything is scanned using the language
    lexer, afterwards all ``Other`` tokens are lexed using the root
    lexer.

    The lexers from the ``template`` lexer package use this base lexer.
    """

    def __init__(self, _root_lexer, _language_lexer, _needle=Other, **options):
        self.root_lexer = _root_lexer(**options)
        self.language_lexer = _language_lexer(**options)
        self.needle = _needle
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        buffered = ''
        insertions = []
        lng_buffer = []
        for i, t, v in self.language_lexer.get_tokens_unprocessed(text):
            if t is self.needle:
                if lng_buffer:
                    insertions.append((len(buffered), lng_buffer))
                    lng_buffer = []
                buffered += v
            else:
                lng_buffer.append((i, t, v))
        if lng_buffer:
            insertions.append((len(buffered), lng_buffer))
        return do_insertions(insertions,
                             self.root_lexer.get_tokens_unprocessed(buffered))


#-------------------------------------------------------------------------------
# RegexLexer and ExtendedRegexLexer
#


class include(str):
    """
    Indicates that a state should include rules from another state.
    """
    pass


class combined(tuple):
    """
    Indicates a state combined from multiple states.
    """

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    def __init__(self, *args):
        # tuple.__init__ doesn't do anything
        pass


class _PseudoMatch(object):
    """
    A pseudo match object constructed from a string.
    """

    def __init__(self, start, text):
        self._text = text
        self._start = start

    def start(self, arg=None):
        return self._start

    def end(self, arg=None):
        return self._start + len(self._text)

    def group(self, arg=None):
        if arg:
            raise IndexError('No such group')
        return self._text

    def groups(self):
        return (self._text,)

    def groupdict(self):
        return {}


def bygroups(*args):
    """
    Callback that yields multiple actions for each group in the match.
    """
    def callback(lexer, match, ctx=None):
        for i, action in enumerate(args):
            if action is None:
                continue
            elif type(action) is _TokenType:
                data = match.group(i + 1)
                if data:
                    yield match.start(i + 1), action, data
            else:
                if ctx:
                    ctx.pos = match.start(i + 1)
                for item in action(lexer, _PseudoMatch(match.start(i + 1),
                                   match.group(i + 1)), ctx):
                    if item:
                        yield item
        if ctx:
            ctx.pos = match.end()
    return callback


class _This(object):
    """
    Special singleton used for indicating the caller class.
    Used by ``using``.
    """
this = _This()


def using(_other, **kwargs):
    """
    Callback that processes the match with a different lexer.

    The keyword arguments are forwarded to the lexer, except `state` which
    is handled separately.

    `state` specifies the state that the new lexer will start in, and can
    be an enumerable such as ('root', 'inline', 'string') or a simple
    string which is assumed to be on top of the root state.

    Note: For that to work, `_other` must not be an `ExtendedRegexLexer`.
    """
    gt_kwargs = {}
    if 'state' in kwargs:
        s = kwargs.pop('state')
        if isinstance(s, (list, tuple)):
            gt_kwargs['stack'] = s
        else:
            gt_kwargs['stack'] = ('root', s)

    if _other is this:
        def callback(lexer, match, ctx=None):
            # if keyword arguments are given the callback
            # function has to create a new lexer instance
            if kwargs:
                # XXX: cache that somehow
                kwargs.update(lexer.options)
                lx = lexer.__class__(**kwargs)
            else:
                lx = lexer
            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    else:
        def callback(lexer, match, ctx=None):
            # XXX: cache that somehow
            kwargs.update(lexer.options)
            lx = _other(**kwargs)

            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    return callback


class RegexLexerMeta(LexerMeta):
    """
    Metaclass for RegexLexer, creates the self._tokens attribute from
    self.tokens on the first instantiation.
    """

    def _process_state(cls, unprocessed, processed, state):
        assert type(state) is str, "wrong state name %r" % state
        assert state[0] != '#', "invalid state name %r" % state
        if state in processed:
            return processed[state]
        tokens = processed[state] = []
        rflags = cls.flags
        for tdef in unprocessed[state]:
            if isinstance(tdef, include):
                # it's a state reference
                assert tdef != state, "circular state reference %r" % state
                tokens.extend(cls._process_state(unprocessed, processed, str(tdef)))
                continue

            assert type(tdef) is tuple, "wrong rule def %r" % tdef

            try:
                rex = re.compile(tdef[0], rflags).match
            except Exception, err:
                raise ValueError("uncompilable regex %r in state %r of %r: %s" %
                                 (tdef[0], state, cls, err))

            assert type(tdef[1]) is _TokenType or callable(tdef[1]), \
                   'token type must be simple type or callable, not %r' % (tdef[1],)

            if len(tdef) == 2:
                new_state = None
            else:
                tdef2 = tdef[2]
                if isinstance(tdef2, str):
                    # an existing state
                    if tdef2 == '#pop':
                        new_state = -1
                    elif tdef2 in unprocessed:
                        new_state = (tdef2,)
                    elif tdef2 == '#push':
                        new_state = tdef2
                    elif tdef2[:5] == '#pop:':
                        new_state = -int(tdef2[5:])
                    else:
                        assert False, 'unknown new state %r' % tdef2
                elif isinstance(tdef2, combined):
                    # combine a new state from existing ones
                    new_state = '_tmp_%d' % cls._tmpname
                    cls._tmpname += 1
                    itokens = []
                    for istate in tdef2:
                        assert istate != state, 'circular state ref %r' % istate
                        itokens.extend(cls._process_state(unprocessed,
                                                          processed, istate))
                    processed[new_state] = itokens
                    new_state = (new_state,)
                elif isinstance(tdef2, tuple):
                    # push more than one state
                    for state in tdef2:
                        assert (state in unprocessed or
                                state in ('#pop', '#push')), \
                               'unknown new state ' + state
                    new_state = tdef2
                else:
                    assert False, 'unknown new state def %r' % tdef2
            tokens.append((rex, tdef[1], new_state))
        return tokens

    def process_tokendef(cls, name, tokendefs=None):
        processed = cls._all_tokens[name] = {}
        tokendefs = tokendefs or cls.tokens[name]
        for state in tokendefs.keys():
            cls._process_state(tokendefs, processed, state)
        return processed

    def __call__(cls, *args, **kwds):
        if not hasattr(cls, '_tokens'):
            cls._all_tokens = {}
            cls._tmpname = 0
            if hasattr(cls, 'token_variants') and cls.token_variants:
                # don't process yet
                pass
            else:
                cls._tokens = cls.process_tokendef('', cls.tokens)

        return type.__call__(cls, *args, **kwds)


class RegexLexer(Lexer):
    """
    Base for simple stateful regular expression-based lexers.
    Simplifies the lexing process so that you need only
    provide a list of states and regular expressions.
    """
    __metaclass__ = RegexLexerMeta

    #: Flags for compiling the regular expressions.
    #: Defaults to MULTILINE.
    flags = re.MULTILINE

    #: Dict of ``{'state': [(regex, tokentype, new_state), ...], ...}``
    #:
    #: The initial state is 'root'.
    #: ``new_state`` can be omitted to signify no state transition.
    #: If it is a string, the state is pushed on the stack and changed.
    #: If it is a tuple of strings, all states are pushed on the stack and
    #: the current state will be the topmost.
    #: It can also be ``combined('state1', 'state2', ...)``
    #: to signify a new, anonymous state combined from the rules of two
    #: or more existing ones.
    #: Furthermore, it can be '#pop' to signify going back one step in
    #: the state stack, or '#push' to push the current state on the stack
    #: again.
    #:
    #: The tuple can also be replaced with ``include('state')``, in which
    #: case the rules from the state named by the string are included in the
    #: current one.
    tokens = {}

    def get_tokens_unprocessed(self, text, stack=('root',)):
        """
        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the inital stack (default: ``['root']``)
        """
        pos = 0
        tokendefs = self._tokens
        statestack = list(stack)
        statetokens = tokendefs[statestack[-1]]
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)
                if m:
                    # print rex.pattern
                    if type(action) is _TokenType:
                        yield pos, action, m.group()
                    else:
                        for item in action(self, m):
                            yield item
                    pos = m.end()
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    statestack.pop()
                                elif state == '#push':
                                    statestack.append(statestack[-1])
                                else:
                                    statestack.append(state)
                        elif isinstance(new_state, int):
                            # pop
                            del statestack[new_state:]
                        elif new_state == '#push':
                            statestack.append(statestack[-1])
                        else:
                            assert False, "wrong state def: %r" % new_state
                        statetokens = tokendefs[statestack[-1]]
                    break
            else:
                try:
                    if text[pos] == '\n':
                        # at EOL, reset state to "root"
                        pos += 1
                        statestack = ['root']
                        statetokens = tokendefs['root']
                        yield pos, Text, u'\n'
                        continue
                    yield pos, Error, text[pos]
                    pos += 1
                except IndexError:
                    break


class LexerContext(object):
    """
    A helper object that holds lexer position data.
    """

    def __init__(self, text, pos, stack=None, end=None):
        self.text = text
        self.pos = pos
        self.end = end or len(text) # end=0 not supported ;-)
        self.stack = stack or ['root']

    def __repr__(self):
        return 'LexerContext(%r, %r, %r)' % (
            self.text, self.pos, self.stack)


class ExtendedRegexLexer(RegexLexer):
    """
    A RegexLexer that uses a context object to store its state.
    """

    def get_tokens_unprocessed(self, text=None, context=None):
        """
        Split ``text`` into (tokentype, text) pairs.
        If ``context`` is given, use this lexer context instead.
        """
        tokendefs = self._tokens
        if not context:
            ctx = LexerContext(text, 0)
            statetokens = tokendefs['root']
        else:
            ctx = context
            statetokens = tokendefs[ctx.stack[-1]]
            text = ctx.text
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, ctx.pos, ctx.end)
                if m:
                    if type(action) is _TokenType:
                        yield ctx.pos, action, m.group()
                        ctx.pos = m.end()
                    else:
                        for item in action(self, m, ctx):
                            yield item
                        if not new_state:
                            # altered the state stack?
                            statetokens = tokendefs[ctx.stack[-1]]
                    # CAUTION: callback must set ctx.pos!
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            ctx.stack.extend(new_state)
                        elif isinstance(new_state, int):
                            # pop
                            del ctx.stack[new_state:]
                        elif new_state == '#push':
                            ctx.stack.append(ctx.stack[-1])
                        else:
                            assert False, "wrong state def: %r" % new_state
                        statetokens = tokendefs[ctx.stack[-1]]
                    break
            else:
                try:
                    if ctx.pos >= ctx.end:
                        break
                    if text[ctx.pos] == '\n':
                        # at EOL, reset state to "root"
                        ctx.pos += 1
                        ctx.stack = ['root']
                        statetokens = tokendefs['root']
                        yield ctx.pos, Text, u'\n'
                        continue
                    yield ctx.pos, Error, text[ctx.pos]
                    ctx.pos += 1
                except IndexError:
                    break


def do_insertions(insertions, tokens):
    """
    Helper for lexers which must combine the results of several
    sublexers.

    ``insertions`` is a list of ``(index, itokens)`` pairs.
    Each ``itokens`` iterable should be inserted at position
    ``index`` into the token stream given by the ``tokens``
    argument.

    The result is a combined token stream.

    TODO: clean up the code here.
    """
    insertions = iter(insertions)
    try:
        index, itokens = insertions.next()
    except StopIteration:
        # no insertions
        for item in tokens:
            yield item
        return

    realpos = None
    insleft = True

    # iterate over the token stream where we want to insert
    # the tokens from the insertion list.
    for i, t, v in tokens:
        # first iteration. store the postition of first item
        if realpos is None:
            realpos = i
        oldi = 0
        while insleft and i + len(v) >= index:
            tmpval = v[oldi:index - i]
            yield realpos, t, tmpval
            realpos += len(tmpval)
            for it_index, it_token, it_value in itokens:
                yield realpos, it_token, it_value
                realpos += len(it_value)
            oldi = index - i
            try:
                index, itokens = insertions.next()
            except StopIteration:
                insleft = False
                break  # not strictly necessary
        yield realpos, t, v[oldi:]
        realpos += len(v) - oldi

    # leftover tokens
    if insleft:
        # no normal tokens, set realpos to zero
        realpos = realpos or 0
        for p, t, v in itokens:
            yield realpos, t, v
            realpos += len(v)

########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
"""
    pygments.lexers.text
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for non-source code file types.

    :copyright: 2006-2008 by Armin Ronacher, Georg Brandl,
                Tim Hatch <tim@timhatch.com>,
                Ronny Pfannschmidt,
                Dennis Kaarsemaker,
                Kumar Appaiah <akumar@ee.iitm.ac.in>,
                Varun Hiremath <varunhiremath@gmail.com>,
                Jeremy Thurgood,
                Max Battcher <me@worldmaker.net>,
                Kirill Simonov <xi@resolvent.net>.
    :license: BSD, see LICENSE for more details.
"""

import re
try:
    set
except NameError:
    from sets import Set as set
from bisect import bisect

from pygments.lexer import Lexer, LexerContext, RegexLexer, ExtendedRegexLexer, \
     bygroups, include, using, this, do_insertions
from pygments.token import Punctuation, Text, Comment, Keyword, Name, String, \
     Generic, Operator, Number, Whitespace, Literal
from pygments.util import get_bool_opt

__all__ = ['YamlLexer']

class YamlLexerContext(LexerContext):
    """Indentation context for the YAML lexer."""

    def __init__(self, *args, **kwds):
        super(YamlLexerContext, self).__init__(*args, **kwds)
        self.indent_stack = []
        self.indent = -1
        self.next_indent = 0
        self.block_scalar_indent = None


class YamlLexer(ExtendedRegexLexer):
    """
    Lexer for `YAML <http://yaml.org/>`_, a human-friendly data serialization
    language.

    *New in Pygments 0.11.*
    """

    name = 'YAML'
    aliases = ['yaml']
    filenames = ['*.yaml', '*.yml']
    mimetypes = ['text/x-yaml']


    def something(token_class):
        """Do not produce empty tokens."""
        def callback(lexer, match, context):
            text = match.group()
            if not text:
                return
            yield match.start(), token_class, text
            context.pos = match.end()
        return callback

    def reset_indent(token_class):
        """Reset the indentation levels."""
        def callback(lexer, match, context):
            text = match.group()
            context.indent_stack = []
            context.indent = -1
            context.next_indent = 0
            context.block_scalar_indent = None
            yield match.start(), token_class, text
            context.pos = match.end()
        return callback

    def save_indent(token_class, start=False):
        """Save a possible indentation level."""
        def callback(lexer, match, context):
            text = match.group()
            extra = ''
            if start:
                context.next_indent = len(text)
                if context.next_indent < context.indent:
                    while context.next_indent < context.indent:
                        context.indent = context.indent_stack.pop()
                    if context.next_indent > context.indent:
                        extra = text[context.indent:]
                        text = text[:context.indent]
            else:
                context.next_indent += len(text)
            if text:
                yield match.start(), token_class, text
            if extra:
                yield match.start()+len(text), token_class.Error, extra
            context.pos = match.end()
        return callback

    def set_indent(token_class, implicit=False):
        """Set the previously saved indentation level."""
        def callback(lexer, match, context):
            text = match.group()
            if context.indent < context.next_indent:
                context.indent_stack.append(context.indent)
                context.indent = context.next_indent
            if not implicit:
                context.next_indent += len(text)
            yield match.start(), token_class, text
            context.pos = match.end()
        return callback

    def set_block_scalar_indent(token_class):
        """Set an explicit indentation level for a block scalar."""
        def callback(lexer, match, context):
            text = match.group()
            context.block_scalar_indent = None
            if not text:
                return
            increment = match.group(1)
            if increment:
                current_indent = max(context.indent, 0)
                increment = int(increment)
                context.block_scalar_indent = current_indent + increment
            if text:
                yield match.start(), token_class, text
                context.pos = match.end()
        return callback

    def parse_block_scalar_empty_line(indent_token_class, content_token_class):
        """Process an empty line in a block scalar."""
        def callback(lexer, match, context):
            text = match.group()
            if (context.block_scalar_indent is None or
                    len(text) <= context.block_scalar_indent):
                if text:
                    yield match.start(), indent_token_class, text
            else:
                indentation = text[:context.block_scalar_indent]
                content = text[context.block_scalar_indent:]
                yield match.start(), indent_token_class, indentation
                yield (match.start()+context.block_scalar_indent,
                        content_token_class, content)
            context.pos = match.end()
        return callback

    def parse_block_scalar_indent(token_class):
        """Process indentation spaces in a block scalar."""
        def callback(lexer, match, context):
            text = match.group()
            if context.block_scalar_indent is None:
                if len(text) <= max(context.indent, 0):
                    context.stack.pop()
                    context.stack.pop()
                    return
                context.block_scalar_indent = len(text)
            else:
                if len(text) < context.block_scalar_indent:
                    context.stack.pop()
                    context.stack.pop()
                    return
            if text:
                yield match.start(), token_class, text
                context.pos = match.end()
        return callback

    def parse_plain_scalar_indent(token_class):
        """Process indentation spaces in a plain scalar."""
        def callback(lexer, match, context):
            text = match.group()
            if len(text) <= context.indent:
                context.stack.pop()
                context.stack.pop()
                return
            if text:
                yield match.start(), token_class, text
                context.pos = match.end()
        return callback



    tokens = {
        # the root rules
        'root': [
            # ignored whitespaces
            (r'[ ]+(?=#|$)', Text),
            # line breaks
            (r'\n+', Text),
            # a comment
            (r'#[^\n]*', Comment.Single),
            # the '%YAML' directive
            (r'^%YAML(?=[ ]|$)', reset_indent(Name.Tag), 'yaml-directive'),
            # the %TAG directive
            (r'^%TAG(?=[ ]|$)', reset_indent(Name.Tag), 'tag-directive'),
            # document start and document end indicators
            (r'^(?:---|\.\.\.)(?=[ ]|$)', reset_indent(Name.Namespace),
             'block-line'),
            # indentation spaces
            (r'[ ]*(?![ \t\n\r\f\v]|$)', save_indent(Text, start=True),
             ('block-line', 'indentation')),
        ],

        # trailing whitespaces after directives or a block scalar indicator
        'ignored-line': [
            # ignored whitespaces
            (r'[ ]+(?=#|$)', Text),
            # a comment
            (r'#[^\n]*', Comment.Single),
            # line break
            (r'\n', Text, '#pop:2'),
        ],

        # the %YAML directive
        'yaml-directive': [
            # the version number
            (r'([ ]+)([0-9]+\.[0-9]+)',
             bygroups(Text, Number), 'ignored-line'),
        ],

        # the %YAG directive
        'tag-directive': [
            # a tag handle and the corresponding prefix
            (r'([ ]+)(!|![0-9A-Za-z_-]*!)'
             r'([ ]+)(!|!?[0-9A-Za-z;/?:@&=+$,_.!~*\'()\[\]%-]+)',
             bygroups(Text, Keyword.Type, Text, Keyword.Type),
             'ignored-line'),
        ],

        # block scalar indicators and indentation spaces
        'indentation': [
            # trailing whitespaces are ignored
            (r'[ ]*$', something(Text), '#pop:2'),
            # whitespaces preceeding block collection indicators
            (r'[ ]+(?=[?:-](?:[ ]|$))', save_indent(Text)),
            # block collection indicators
            (r'[?:-](?=[ ]|$)', set_indent(Punctuation.Indicator)),
            # the beginning a block line
            (r'[ ]*', save_indent(Text), '#pop'),
        ],

        # an indented line in the block context
        'block-line': [
            # the line end
            (r'[ ]*(?=#|$)', something(Text), '#pop'),
            # whitespaces separating tokens
            (r'[ ]+', Text),
            # tags, anchors and aliases,
            include('descriptors'),
            # block collections and scalars
            include('block-nodes'),
            # flow collections and quoted scalars
            include('flow-nodes'),
            # a plain scalar
            (r'(?=[^ \t\n\r\f\v?:,\[\]{}#&*!|>\'"%@`-]|[?:-][^ \t\n\r\f\v])',
             something(Name.Variable),
             'plain-scalar-in-block-context'),
        ],

        # tags, anchors, aliases
        'descriptors' : [
            # a full-form tag
            (r'!<[0-9A-Za-z;/?:@&=+$,_.!~*\'()\[\]%-]+>', Keyword.Type),
            # a tag in the form '!', '!suffix' or '!handle!suffix'
            (r'!(?:[0-9A-Za-z_-]+)?'
             r'(?:![0-9A-Za-z;/?:@&=+$,_.!~*\'()\[\]%-]+)?', Keyword.Type),
            # an anchor
            (r'&[0-9A-Za-z_-]+', Name.Label),
            # an alias
            (r'\*[0-9A-Za-z_-]+', Name.Variable),
        ],

        # block collections and scalars
        'block-nodes': [
            # implicit key
            (r':(?=[ ]|$)', set_indent(Punctuation.Indicator, implicit=True)),
            # literal and folded scalars
            (r'[|>]', Punctuation.Indicator,
             ('block-scalar-content', 'block-scalar-header')),
        ],

        # flow collections and quoted scalars
        'flow-nodes': [
            # a flow sequence
            (r'\[', Punctuation.Indicator, 'flow-sequence'),
            # a flow mapping
            (r'\{', Punctuation.Indicator, 'flow-mapping'),
            # a single-quoted scalar
            (r'\'', String, 'single-quoted-scalar'),
            # a double-quoted scalar
            (r'\"', String, 'double-quoted-scalar'),
        ],

        # the content of a flow collection
        'flow-collection': [
            # whitespaces
            (r'[ ]+', Text),
            # line breaks
            (r'\n+', Text),
            # a comment
            (r'#[^\n]*', Comment.Single),
            # simple indicators
            (r'[?:,]', Punctuation.Indicator),
            # tags, anchors and aliases
            include('descriptors'),
            # nested collections and quoted scalars
            include('flow-nodes'),
            # a plain scalar
            (r'(?=[^ \t\n\r\f\v?:,\[\]{}#&*!|>\'"%@`])',
             something(Name.Variable),
             'plain-scalar-in-flow-context'),
        ],

        # a flow sequence indicated by '[' and ']'
        'flow-sequence': [
            # include flow collection rules
            include('flow-collection'),
            # the closing indicator
            (r'\]', Punctuation.Indicator, '#pop'),
        ],

        # a flow mapping indicated by '{' and '}'
        'flow-mapping': [
            # include flow collection rules
            include('flow-collection'),
            # the closing indicator
            (r'\}', Punctuation.Indicator, '#pop'),
        ],

        # block scalar lines
        'block-scalar-content': [
            # line break
            (r'\n', Text),
            # empty line
            (r'^[ ]+$',
             parse_block_scalar_empty_line(Text, Name.Constant)),
            # indentation spaces (we may leave the state here)
            (r'^[ ]*', parse_block_scalar_indent(Text)),
            # line content
            (r'[^\n\r\f\v]+', Name.Constant),
        ],

        # the content of a literal or folded scalar
        'block-scalar-header': [
            # indentation indicator followed by chomping flag
            (r'([1-9])?[+-]?(?=[ ]|$)',
             set_block_scalar_indent(Punctuation.Indicator),
             'ignored-line'),
            # chomping flag followed by indentation indicator
            (r'[+-]?([1-9])?(?=[ ]|$)',
             set_block_scalar_indent(Punctuation.Indicator),
             'ignored-line'),
        ],

        # ignored and regular whitespaces in quoted scalars
        'quoted-scalar-whitespaces': [
            # leading and trailing whitespaces are ignored
            (r'^[ ]+|[ ]+$', Text),
            # line breaks are ignored
            (r'\n+', Text),
            # other whitespaces are a part of the value
            (r'[ ]+', Name.Variable),
        ],

        # single-quoted scalars
        'single-quoted-scalar': [
            # include whitespace and line break rules
            include('quoted-scalar-whitespaces'),
            # escaping of the quote character
            (r'\'\'', String.Escape),
            # regular non-whitespace characters
            (r'[^ \t\n\r\f\v\']+', String),
            # the closing quote
            (r'\'', String, '#pop'),
        ],

        # double-quoted scalars
        'double-quoted-scalar': [
            # include whitespace and line break rules
            include('quoted-scalar-whitespaces'),
            # escaping of special characters
            (r'\\[0abt\tn\nvfre "\\N_LP]', String),
            # escape codes
            (r'\\(?:x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})',
             String.Escape),
            # regular non-whitespace characters
            (r'[^ \t\n\r\f\v\"\\]+', String),
            # the closing quote
            (r'"', String, '#pop'),
        ],

        # the beginning of a new line while scanning a plain scalar
        'plain-scalar-in-block-context-new-line': [
            # empty lines
            (r'^[ ]+$', Text),
            # line breaks
            (r'\n+', Text),
            # document start and document end indicators
            (r'^(?=---|\.\.\.)', something(Name.Namespace), '#pop:3'),
            # indentation spaces (we may leave the block line state here)
            (r'^[ ]*', parse_plain_scalar_indent(Text), '#pop'),
        ],

        # a plain scalar in the block context
        'plain-scalar-in-block-context': [
            # the scalar ends with the ':' indicator
            (r'[ ]*(?=:[ ]|:$)', something(Text), '#pop'),
            # the scalar ends with whitespaces followed by a comment
            (r'[ ]+(?=#)', Text, '#pop'),
            # trailing whitespaces are ignored
            (r'[ ]+$', Text),
            # line breaks are ignored
            (r'\n+', Text, 'plain-scalar-in-block-context-new-line'),
            # other whitespaces are a part of the value
            (r'[ ]+', Literal.Scalar.Plain),
            # regular non-whitespace characters
            (r'(?::(?![ \t\n\r\f\v])|[^ \t\n\r\f\v:])+', Literal.Scalar.Plain),
        ],

        # a plain scalar is the flow context
        'plain-scalar-in-flow-context': [
            # the scalar ends with an indicator character
            (r'[ ]*(?=[,:?\[\]{}])', something(Text), '#pop'),
            # the scalar ends with a comment
            (r'[ ]+(?=#)', Text, '#pop'),
            # leading and trailing whitespaces are ignored
            (r'^[ ]+|[ ]+$', Text),
            # line breaks are ignored
            (r'\n+', Text),
            # other whitespaces are a part of the value
            (r'[ ]+', Name.Variable),
            # regular non-whitespace characters
            (r'[^ \t\n\r\f\v,:?\[\]{}]+', Name.Variable),
        ],

    }

    def get_tokens_unprocessed(self, text=None, context=None):
        if context is None:
            context = YamlLexerContext(text, 0)
        return super(YamlLexer, self).get_tokens_unprocessed(text, context)


########NEW FILE########
__FILENAME__ = _mapping
# -*- coding: utf-8 -*-
"""
    pygments.lexers._mapping
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer mapping defintions. This file is generated by itself. Everytime
    you change something on a builtin lexer defintion, run this script from
    the lexers folder to update it.

    Do not alter the LEXERS dictionary by hand.

    :copyright: 2006-2007 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""

LEXERS = {
    'YamlLexer': ('pygments.lexers.text', 'YAML', ('yaml',), ('*.yaml', '*.yml'), ('text/x-yaml',))
}

if __name__ == '__main__':
    import sys
    import os

    # lookup lexers
    found_lexers = []
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    for filename in os.listdir('.'):
        if filename.endswith('.py') and not filename.startswith('_'):
            module_name = 'pygments.lexers.%s' % filename[:-3]
            print module_name
            module = __import__(module_name, None, None, [''])
            for lexer_name in module.__all__:
                lexer = getattr(module, lexer_name)
                found_lexers.append(
                    '%r: %r' % (lexer_name,
                                (module_name,
                                 lexer.name,
                                 tuple(lexer.aliases),
                                 tuple(lexer.filenames),
                                 tuple(lexer.mimetypes))))
    # sort them, that should make the diff files for svn smaller
    found_lexers.sort()

    # extract useful sourcecode from this file
    f = open(__file__)
    try:
        content = f.read()
    finally:
        f.close()
    header = content[:content.find('LEXERS = {')]
    footer = content[content.find("if __name__ == '__main__':"):]

    # write new file
    f = open(__file__, 'w')
    f.write(header)
    f.write('LEXERS = {\n    %s\n}\n\n' % ',\n    '.join(found_lexers))
    f.write(footer)
    f.close()

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-
"""
    pygments.plugin
    ~~~~~~~~~~~~~~~

    Pygments setuptools plugin interface. The methods defined
    here also work if setuptools isn't installed but they just
    return nothing.

    lexer plugins::

        [pygments.lexers]
        yourlexer = yourmodule:YourLexer

    formatter plugins::

        [pygments.formatters]
        yourformatter = yourformatter:YourFormatter
        /.ext = yourformatter:YourFormatter

    As you can see, you can define extensions for the formatter
    with a leading slash.

    syntax plugins::

        [pygments.styles]
        yourstyle = yourstyle:YourStyle

    filter plugin::

        [pygments.filter]
        yourfilter = yourfilter:YourFilter


    :copyright: 2006-2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
try:
    import pkg_resources
except ImportError:
    pkg_resources = None

LEXER_ENTRY_POINT = 'pygments.lexers'
FORMATTER_ENTRY_POINT = 'pygments.formatters'
STYLE_ENTRY_POINT = 'pygments.styles'
FILTER_ENTRY_POINT = 'pygments.filters'


def find_plugin_lexers():
    if pkg_resources is None:
        return
    for entrypoint in pkg_resources.iter_entry_points(LEXER_ENTRY_POINT):
        yield entrypoint.load()


def find_plugin_formatters():
    if pkg_resources is None:
        return
    for entrypoint in pkg_resources.iter_entry_points(FORMATTER_ENTRY_POINT):
        yield entrypoint.name, entrypoint.load()


def find_plugin_styles():
    if pkg_resources is None:
        return
    for entrypoint in pkg_resources.iter_entry_points(STYLE_ENTRY_POINT):
        yield entrypoint.name, entrypoint.load()


def find_plugin_filters():
    if pkg_resources is None:
        return
    for entrypoint in pkg_resources.iter_entry_points(FILTER_ENTRY_POINT):
        yield entrypoint.name, entrypoint.load()

########NEW FILE########
__FILENAME__ = scanner
# -*- coding: utf-8 -*-
"""
    pygments.scanner
    ~~~~~~~~~~~~~~~~

    This library implements a regex based scanner. Some languages
    like Pascal are easy to parse but have some keywords that
    depend on the context. Because of this it's impossible to lex
    that just by using a regular expression lexer like the
    `RegexLexer`.

    Have a look at the `DelphiLexer` to get an idea of how to use
    this scanner.

    :copyright: 2006-2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import re


class EndOfText(RuntimeError):
    """
    Raise if end of text is reached and the user
    tried to call a match function.
    """


class Scanner(object):
    """
    Simple scanner

    All method patterns are regular expression strings (not
    compiled expressions!)
    """

    def __init__(self, text, flags=0):
        """
        :param text:    The text which should be scanned
        :param flags:   default regular expression flags
        """
        self.data = text
        self.data_length = len(text)
        self.start_pos = 0
        self.pos = 0
        self.flags = flags
        self.last = None
        self.match = None
        self._re_cache = {}

    def eos(self):
        """`True` if the scanner reached the end of text."""
        return self.pos >= self.data_length
    eos = property(eos, eos.__doc__)

    def check(self, pattern):
        """
        Apply `pattern` on the current position and return
        the match object. (Doesn't touch pos). Use this for
        lookahead.
        """
        if self.eos:
            raise EndOfText()
        if pattern not in self._re_cache:
            self._re_cache[pattern] = re.compile(pattern, self.flags)
        return self._re_cache[pattern].match(self.data, self.pos)

    def test(self, pattern):
        """Apply a pattern on the current position and check
        if it patches. Doesn't touch pos."""
        return self.check(pattern) is not None

    def scan(self, pattern):
        """
        Scan the text for the given pattern and update pos/match
        and related fields. The return value is a boolen that
        indicates if the pattern matched. The matched value is
        stored on the instance as ``match``, the last value is
        stored as ``last``. ``start_pos`` is the position of the
        pointer before the pattern was matched, ``pos`` is the
        end position.
        """
        if self.eos:
            raise EndOfText()
        if pattern not in self._re_cache:
            self._re_cache[pattern] = re.compile(pattern, self.flags)
        self.last = self.match
        m = self._re_cache[pattern].match(self.data, self.pos)
        if m is None:
            return False
        self.start_pos = m.start()
        self.pos = m.end()
        self.match = m.group()
        return True

    def get_char(self):
        """Scan exactly one char."""
        self.scan('.')

    def __repr__(self):
        return '<%s %d/%d>' % (
            self.__class__.__name__,
            self.pos,
            self.data_length
        )

########NEW FILE########
__FILENAME__ = style
# -*- coding: utf-8 -*-
"""
    pygments.style
    ~~~~~~~~~~~~~~

    Basic style object.

    :copyright: 2006-2007 by Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""

from pygments.token import Token, STANDARD_TYPES


class StyleMeta(type):

    def __new__(mcs, name, bases, dct):
        obj = type.__new__(mcs, name, bases, dct)
        for token in STANDARD_TYPES:
            if token not in obj.styles:
                obj.styles[token] = ''

        def colorformat(text):
            if text[0:1] == '#':
                col = text[1:]
                if len(col) == 6:
                    return col
                elif len(col) == 3:
                    return col[0]+'0'+col[1]+'0'+col[2]+'0'
            elif text == '':
                return ''
            assert False, "wrong color format %r" % text

        _styles = obj._styles = {}

        for ttype in obj.styles:
            for token in ttype.split():
                if token in _styles:
                    continue
                ndef = _styles.get(token.parent, None)
                styledefs = obj.styles.get(token, '').split()
                if  not ndef or token is None:
                    ndef = ['', 0, 0, 0, '', '', 0, 0, 0]
                elif 'noinherit' in styledefs and token is not Token:
                    ndef = _styles[Token][:]
                else:
                    ndef = ndef[:]
                _styles[token] = ndef
                for styledef in obj.styles.get(token, '').split():
                    if styledef == 'noinherit':
                        pass
                    elif styledef == 'bold':
                        ndef[1] = 1
                    elif styledef == 'nobold':
                        ndef[1] = 0
                    elif styledef == 'italic':
                        ndef[2] = 1
                    elif styledef == 'noitalic':
                        ndef[2] = 0
                    elif styledef == 'underline':
                        ndef[3] = 1
                    elif styledef == 'nounderline':
                        ndef[3] = 0
                    elif styledef[:3] == 'bg:':
                        ndef[4] = colorformat(styledef[3:])
                    elif styledef[:7] == 'border:':
                        ndef[5] = colorformat(styledef[7:])
                    elif styledef == 'roman':
                        ndef[6] = 1
                    elif styledef == 'sans':
                        ndef[7] = 1
                    elif styledef == 'mono':
                        ndef[8] = 1
                    else:
                        ndef[0] = colorformat(styledef)

        return obj

    def style_for_token(cls, token):
        t = cls._styles[token]
        return {
            'color':        t[0] or None,
            'bold':         bool(t[1]),
            'italic':       bool(t[2]),
            'underline':    bool(t[3]),
            'bgcolor':      t[4] or None,
            'border':       t[5] or None,
            'roman':        bool(t[6]) or None,
            'sans':         bool(t[7]) or None,
            'mono':         bool(t[8]) or None,
        }

    def list_styles(cls):
        return list(cls)

    def styles_token(cls, ttype):
        return ttype in cls._styles

    def __iter__(cls):
        for token in cls._styles:
            yield token, cls.style_for_token(token)

    def __len__(cls):
        return len(cls._styles)


class Style(object):
    __metaclass__ = StyleMeta

    #: overall background color (``None`` means transparent)
    background_color = '#ffffff'

    #: highlight background color
    highlight_color = '#ffffcc'

    #: Style definitions for individual token types.
    styles = {}

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
"""
    pygments.styles.default
    ~~~~~~~~~~~~~~~~~~~~~~~

    The default highlighting style.

    :copyright: 2007 by Tiberius Teng.
    :copyright: 2006 by Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""

from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace


class DefaultStyle(Style):
    """
    The default style (inspired by Emacs 22).
    """

    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        Whitespace:                "#bbbbbb",
        Comment:                   "italic #408080",
        Comment.Preproc:           "noitalic #BC7A00",

        #Keyword:                   "bold #AA22FF",
        Keyword:                   "bold #008000",
        Keyword.Pseudo:            "nobold",
        Keyword.Type:              "nobold #B00040",

        Operator:                  "#666666",
        Operator.Word:             "bold #AA22FF",

        Name.Builtin:              "#008000",
        Name.Function:             "#0000FF",
        Name.Class:                "bold #0000FF",
        Name.Namespace:            "bold #0000FF",
        Name.Exception:            "bold #D2413A",
        Name.Variable:             "#19177C",
        Name.Constant:             "#880000",
        Name.Label:                "#A0A000",
        Name.Entity:               "bold #999999",
        Name.Attribute:            "#7D9029",
        Name.Tag:                  "bold #008000",
        Name.Decorator:            "#AA22FF",

        String:                    "#BA2121",
        String.Doc:                "italic",
        String.Interpol:           "bold #BB6688",
        String.Escape:             "bold #BB6622",
        String.Regex:              "#BB6688",
        #String.Symbol:             "#B8860B",
        String.Symbol:             "#19177C",
        String.Other:              "#008000",
        Number:                    "#666666",

        Generic.Heading:           "bold #000080",
        Generic.Subheading:        "bold #800080",
        Generic.Deleted:           "#A00000",
        Generic.Inserted:          "#00A000",
        Generic.Error:             "#FF0000",
        Generic.Emph:              "italic",
        Generic.Strong:            "bold",
        Generic.Prompt:            "bold #000080",
        Generic.Output:            "#888",
        Generic.Traceback:         "#04D",

        Error:                     "border:#FF0000"
    }

########NEW FILE########
__FILENAME__ = token
# -*- coding: utf-8 -*-
"""
    pygments.token
    ~~~~~~~~~~~~~~

    Basic token types and the standard tokens.

    :copyright: 2006-2007 by Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
try:
    set
except NameError:
    from sets import Set as set


class _TokenType(tuple):
    parent = None

    def split(self):
        buf = []
        node = self
        while node is not None:
            buf.append(node)
            node = node.parent
        buf.reverse()
        return buf

    def __init__(self, *args):
        # no need to call super.__init__
        self.subtypes = set()

    def __contains__(self, val):
        return self is val or (
            type(val) is self.__class__ and
            val[:len(self)] == self
        )

    def __getattr__(self, val):
        if not val or not val[0].isupper():
            return tuple.__getattribute__(self, val)
        new = _TokenType(self + (val,))
        setattr(self, val, new)
        self.subtypes.add(new)
        new.parent = self
        return new

    def __hash__(self):
        return hash(tuple(self))

    def __repr__(self):
        return 'Token' + (self and '.' or '') + '.'.join(self)


Token       = _TokenType()

# Special token types
Text        = Token.Text
Whitespace  = Text.Whitespace
Error       = Token.Error
# Text that doesn't belong to this lexer (e.g. HTML in PHP)
Other       = Token.Other

# Common token types for source code
Keyword     = Token.Keyword
Name        = Token.Name
Literal     = Token.Literal
String      = Literal.String
Number      = Literal.Number
Punctuation = Token.Punctuation
Operator    = Token.Operator
Comment     = Token.Comment

# Generic types for non-source code
Generic     = Token.Generic

# String and some others are not direct childs of Token.
# alias them:
Token.Token = Token
Token.String = String
Token.Number = Number


def is_token_subtype(ttype, other):
    """
    Return True if ``ttype`` is a subtype of ``other``.

    exists for backwards compatibility. use ``ttype in other`` now.
    """
    return ttype in other


def string_to_tokentype(s):
    """
    Convert a string into a token type::

        >>> string_to_token('String.Double')
        Token.Literal.String.Double
        >>> string_to_token('Token.Literal.Number')
        Token.Literal.Number
        >>> string_to_token('')
        Token

    Tokens that are already tokens are returned unchanged:

        >>> string_to_token(String)
        Token.Literal.String
    """
    if isinstance(s, _TokenType):
        return s
    if not s:
        return Token
    node = Token
    for item in s.split('.'):
        node = getattr(node, item)
    return node


# Map standard token types to short names, used in CSS class naming.
# If you add a new item, please be sure to run this file to perform
# a consistency check for duplicate values.
STANDARD_TYPES = {
    Token:                         '',

    Text:                          '',
    Whitespace:                    'w',
    Error:                         'err',
    Other:                         'x',

    Keyword:                       'k',
    Keyword.Constant:              'kc',
    Keyword.Declaration:           'kd',
    Keyword.Namespace:             'kn',
    Keyword.Pseudo:                'kp',
    Keyword.Reserved:              'kr',
    Keyword.Type:                  'kt',

    Name:                          'n',
    Name.Attribute:                'na',
    Name.Builtin:                  'nb',
    Name.Builtin.Pseudo:           'bp',
    Name.Class:                    'nc',
    Name.Constant:                 'no',
    Name.Decorator:                'nd',
    Name.Entity:                   'ni',
    Name.Exception:                'ne',
    Name.Function:                 'nf',
    Name.Property:                 'py',
    Name.Label:                    'nl',
    Name.Namespace:                'nn',
    Name.Other:                    'nx',
    Name.Tag:                      'nt',
    Name.Variable:                 'nv',
    Name.Variable.Class:           'vc',
    Name.Variable.Global:          'vg',
    Name.Variable.Instance:        'vi',

    Literal:                       'l',
    Literal.Date:                  'ld',

    String:                        's',
    String.Backtick:               'sb',
    String.Char:                   'sc',
    String.Doc:                    'sd',
    String.Double:                 's2',
    String.Escape:                 'se',
    String.Heredoc:                'sh',
    String.Interpol:               'si',
    String.Other:                  'sx',
    String.Regex:                  'sr',
    String.Single:                 's1',
    String.Symbol:                 'ss',

    Number:                        'm',
    Number.Float:                  'mf',
    Number.Hex:                    'mh',
    Number.Integer:                'mi',
    Number.Integer.Long:           'il',
    Number.Oct:                    'mo',

    Operator:                      'o',
    Operator.Word:                 'ow',

    Punctuation:                   'p',

    Comment:                       'c',
    Comment.Multiline:             'cm',
    Comment.Preproc:               'cp',
    Comment.Single:                'c1',
    Comment.Special:               'cs',

    Generic:                       'g',
    Generic.Deleted:               'gd',
    Generic.Emph:                  'ge',
    Generic.Error:                 'gr',
    Generic.Heading:               'gh',
    Generic.Inserted:              'gi',
    Generic.Output:                'go',
    Generic.Prompt:                'gp',
    Generic.Strong:                'gs',
    Generic.Subheading:            'gu',
    Generic.Traceback:             'gt',
}

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
"""
    pygments.util
    ~~~~~~~~~~~~~

    Utility functions.

    :copyright: 2006-2008 by Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import re


split_path_re = re.compile(r'[/\\ ]')
doctype_lookup_re = re.compile(r'''(?smx)
    (<\?.*?\?>)?\s*
    <!DOCTYPE\s+(
     [a-zA-Z_][a-zA-Z0-9]*\s+
     [a-zA-Z_][a-zA-Z0-9]*\s+
     "[^"]*")
     [^>]*>
''')
tag_re = re.compile(r'<(.+?)(\s.*?)?>.*?</.+?>(?uism)')


class ClassNotFound(ValueError):
    """
    If one of the get_*_by_* functions didn't find a matching class.
    """


class OptionError(Exception):
    pass


def get_choice_opt(options, optname, allowed, default=None, normcase=False):
    string = options.get(optname, default)
    if normcase:
        string = string.lower()
    if string not in allowed:
        raise OptionError('Value for option %s must be one of %s' %
                          (optname, ', '.join(map(str, allowed))))
    return string


def get_bool_opt(options, optname, default=None):
    string = options.get(optname, default)
    if isinstance(string, bool):
        return string
    elif isinstance(string, int):
        return bool(string)
    elif not isinstance(string, basestring):
        raise OptionError('Invalid type %r for option %s; use '
                          '1/0, yes/no, true/false, on/off' % (
                          string, optname))
    elif string.lower() in ('1', 'yes', 'true', 'on'):
        return True
    elif string.lower() in ('0', 'no', 'false', 'off'):
        return False
    else:
        raise OptionError('Invalid value %r for option %s; use '
                          '1/0, yes/no, true/false, on/off' % (
                          string, optname))


def get_int_opt(options, optname, default=None):
    string = options.get(optname, default)
    try:
        return int(string)
    except TypeError:
        raise OptionError('Invalid type %r for option %s; you '
                          'must give an integer value' % (
                          string, optname))
    except ValueError:
        raise OptionError('Invalid value %r for option %s; you '
                          'must give an integer value' % (
                          string, optname))


def get_list_opt(options, optname, default=None):
    val = options.get(optname, default)
    if isinstance(val, basestring):
        return val.split()
    elif isinstance(val, (list, tuple)):
        return list(val)
    else:
        raise OptionError('Invalid type %r for option %s; you '
                          'must give a list value' % (
                          val, optname))


def docstring_headline(obj):
    if not obj.__doc__:
        return ''
    res = []
    for line in obj.__doc__.strip().splitlines():
        if line.strip():
            res.append(" " + line.strip())
        else:
            break
    return ''.join(res).lstrip()


def make_analysator(f):
    """
    Return a static text analysation function that
    returns float values.
    """
    def text_analyse(text):
        rv = f(text)
        if not rv:
            return 0.0
        return min(1.0, max(0.0, float(rv)))
    text_analyse.__doc__ = f.__doc__
    return staticmethod(text_analyse)


def shebang_matches(text, regex):
    """
    Check if the given regular expression matches the last part of the
    shebang if one exists.

        >>> from pygments.util import shebang_matches
        >>> shebang_matches('#!/usr/bin/env python', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python2.4', r'python(2\.\d)?')
        True
        >>> shebang_matches('#!/usr/bin/python-ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/python/ruby', r'python(2\.\d)?')
        False
        >>> shebang_matches('#!/usr/bin/startsomethingwith python',
        ...                 r'python(2\.\d)?')
        True

    It also checks for common windows executable file extensions::

        >>> shebang_matches('#!C:\\Python2.4\\Python.exe', r'python(2\.\d)?')
        True

    Parameters (``'-f'`` or ``'--foo'`` are ignored so ``'perl'`` does
    the same as ``'perl -e'``)

    Note that this method automatically searches the whole string (eg:
    the regular expression is wrapped in ``'^$'``)
    """
    index = text.find('\n')
    if index >= 0:
        first_line = text[:index].lower()
    else:
        first_line = text.lower()
    if first_line.startswith('#!'):
        try:
            found = [x for x in split_path_re.split(first_line[2:].strip())
                     if x and not x.startswith('-')][-1]
        except IndexError:
            return False
        regex = re.compile('^%s(\.(exe|cmd|bat|bin))?$' % regex, re.IGNORECASE)
        if regex.search(found) is not None:
            return True
    return False


def doctype_matches(text, regex):
    """
    Check if the doctype matches a regular expression (if present).
    Note that this method only checks the first part of a DOCTYPE.
    eg: 'html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
    """
    m = doctype_lookup_re.match(text)
    if m is None:
        return False
    doctype = m.group(2)
    return re.compile(regex).match(doctype.strip()) is not None


def html_doctype_matches(text):
    """
    Check if the file looks like it has a html doctype.
    """
    return doctype_matches(text, r'html\s+PUBLIC\s+"-//W3C//DTD X?HTML.*')


_looks_like_xml_cache = {}
def looks_like_xml(text):
    """
    Check if a doctype exists or if we have some tags.
    """
    key = hash(text)
    try:
        return _looks_like_xml_cache[key]
    except KeyError:
        m = doctype_lookup_re.match(text)
        if m is not None:
            return True
        rv = tag_re.search(text[:1000]) is not None
        _looks_like_xml_cache[key] = rv
        return rv

########NEW FILE########
__FILENAME__ = base
"""Route and Mapper core classes"""
from routes import request_config
from routes.mapper import Mapper
from routes.route import Route

########NEW FILE########
__FILENAME__ = mapper
import re
import sys
import threading
import threadinglocal

if sys.version < '2.4':
    from sets import ImmutableSet as frozenset

from routes import request_config
from routes.util import controller_scan, RouteException
from routes.route import Route


def strip_slashes(name):
    """Remove slashes from the beginning and end of a part/URL."""
    if name.startswith('/'):
        name = name[1:]
    if name.endswith('/'):
        name = name[:-1]
    return name


class Mapper(object):
    """Mapper handles URL generation and URL recognition in a web
    application.
    
    Mapper is built handling dictionary's. It is assumed that the web
    application will handle the dictionary returned by URL recognition
    to dispatch appropriately.
    
    URL generation is done by passing keyword parameters into the
    generate function, a URL is then returned.
    
    """
    def __init__(self, controller_scan=controller_scan, directory=None, 
                 always_scan=False, register=True, explicit=False):
        """Create a new Mapper instance
        
        All keyword arguments are optional.
        
        ``controller_scan``
            Function reference that will be used to return a list of
            valid controllers used during URL matching. If
            ``directory`` keyword arg is present, it will be passed
            into the function during its call. This option defaults to
            a function that will scan a directory for controllers.
        
        ``directory``
            Passed into controller_scan for the directory to scan. It
            should be an absolute path if using the default 
            ``controller_scan`` function.
        
        ``always_scan``
            Whether or not the ``controller_scan`` function should be
            run during every URL match. This is typically a good idea
            during development so the server won't need to be restarted
            anytime a controller is added.
        
        ``register``
            Boolean used to determine if the Mapper should use 
            ``request_config`` to register itself as the mapper. Since
            it's done on a thread-local basis, this is typically best
            used during testing though it won't hurt in other cases.
        
        ``explicit``
            Boolean used to determine if routes should be connected
            with implicit defaults of::
                
                {'controller':'content','action':'index','id':None}
            
            When set to True, these defaults will not be added to route
            connections and ``url_for`` will not use Route memory.
                
        Additional attributes that may be set after mapper
        initialization (ie, map.ATTRIBUTE = 'something'):
        
        ``encoding``
            Used to indicate alternative encoding/decoding systems to
            use with both incoming URL's, and during Route generation
            when passed a Unicode string. Defaults to 'utf-8'.
        
        ``decode_errors``
            How to handle errors in the encoding, generally ignoring
            any chars that don't convert should be sufficient. Defaults
            to 'ignore'.
        
        ``minimization``
            Boolean used to indicate whether or not Routes should
            minimize URL's and the generated URL's, or require every
            part where it appears in the path. Defaults to True.
        
        ``hardcode_names``
            Whether or not Named Routes result in the default options
            for the route being used *or* if they actually force url
            generation to use the route. Defaults to False.
        
        """
        self.matchlist = []
        self.maxkeys = {}
        self.minkeys = {}
        self.urlcache = {}
        self._created_regs = False
        self._created_gens = False
        self.prefix = None
        self.req_data = threadinglocal.local()
        self.directory = directory
        self.always_scan = always_scan
        self.controller_scan = controller_scan
        self._regprefix = None
        self._routenames = {}
        self.debug = False
        self.append_slash = False
        self.sub_domains = False
        self.sub_domains_ignore = []
        self.domain_match = '[^\.\/]+?\.[^\.\/]+'
        self.explicit = explicit
        self.encoding = 'utf-8'
        self.decode_errors = 'ignore'
        self.hardcode_names = True
        self.minimization = True
        self.create_regs_lock = threading.Lock()
        if register:
            config = request_config()
            config.mapper = self
    
    def _envget(self):
        return getattr(self.req_data, 'environ', None)
    def _envset(self, env):
        self.req_data.environ = env
    def _envdel(self):
        del self.req_data.environ
    environ = property(_envget, _envset, _envdel)

    def connect(self, *args, **kargs):
        """Create and connect a new Route to the Mapper.
        
        Usage:
        
        .. code-block:: python
        
            m = Mapper()
            m.connect(':controller/:action/:id')
            m.connect('date/:year/:month/:day', controller="blog", action="view")
            m.connect('archives/:page', controller="blog", action="by_page",
            requirements = { 'page':'\d{1,2}' })
            m.connect('category_list', 'archives/category/:section', controller='blog', action='category',
            section='home', type='list')
            m.connect('home', '', controller='blog', action='view', section='home')
        
        """
        routename = None
        if len(args) > 1:
            routename = args[0]
            args = args[1:]
        if '_explicit' not in kargs:
            kargs['_explicit'] = self.explicit
        if '_minimize' not in kargs:
            kargs['_minimize'] = self.minimization
        route = Route(*args, **kargs)
                
        # Apply encoding and errors if its not the defaults and the route 
        # didn't have one passed in.
        if (self.encoding != 'utf-8' or self.decode_errors != 'ignore') and \
           '_encoding' not in kargs:
            route.encoding = self.encoding
            route.decode_errors = self.decode_errors
        
        self.matchlist.append(route)
        if routename:
            self._routenames[routename] = route
        if route.static:
            return
        exists = False
        for key in self.maxkeys:
            if key == route.maxkeys:
                self.maxkeys[key].append(route)
                exists = True
                break
        if not exists:
            self.maxkeys[route.maxkeys] = [route]
        self._created_gens = False
    
    def _create_gens(self):
        """Create the generation hashes for route lookups"""
        # Use keys temporailly to assemble the list to avoid excessive
        # list iteration testing with "in"
        controllerlist = {}
        actionlist = {}
        
        # Assemble all the hardcoded/defaulted actions/controllers used
        for route in self.matchlist:
            if route.static:
                continue
            if route.defaults.has_key('controller'):
                controllerlist[route.defaults['controller']] = True
            if route.defaults.has_key('action'):
                actionlist[route.defaults['action']] = True
        
        # Setup the lists of all controllers/actions we'll add each route
        # to. We include the '*' in the case that a generate contains a
        # controller/action that has no hardcodes
        controllerlist = controllerlist.keys() + ['*']
        actionlist = actionlist.keys() + ['*']
        
        # Go through our list again, assemble the controllers/actions we'll
        # add each route to. If its hardcoded, we only add it to that dict key.
        # Otherwise we add it to every hardcode since it can be changed.
        gendict = {} # Our generated two-deep hash
        for route in self.matchlist:
            if route.static:
                continue
            clist = controllerlist
            alist = actionlist
            if 'controller' in route.hardcoded:
                clist = [route.defaults['controller']]
            if 'action' in route.hardcoded:
                alist = [unicode(route.defaults['action'])]
            for controller in clist:
                for action in alist:
                    actiondict = gendict.setdefault(controller, {})
                    actiondict.setdefault(action, ([], {}))[0].append(route)
        self._gendict = gendict
        self._created_gens = True

    def create_regs(self, *args, **kwargs):
        """Atomically creates regular expressions for all connected
        routes
        """
        self.create_regs_lock.acquire()
        try:
            self._create_regs(*args, **kwargs)
        finally:
            self.create_regs_lock.release()
    
    def _create_regs(self, clist=None):
        """Creates regular expressions for all connected routes"""
        if clist is None:
            if self.directory:
                clist = self.controller_scan(self.directory)
            else:
                clist = self.controller_scan()
            
        for key, val in self.maxkeys.iteritems():
            for route in val:
                route.makeregexp(clist)
        
        
        # Create our regexp to strip the prefix
        if self.prefix:
            self._regprefix = re.compile(self.prefix + '(.*)')
        self._created_regs = True
    
    def _match(self, url):
        """Internal Route matcher
        
        Matches a URL against a route, and returns a tuple of the match
        dict and the route object if a match is successfull, otherwise
        it returns empty.
        
        For internal use only.
        
        """
        if not self._created_regs and self.controller_scan:
            self.create_regs()
        elif not self._created_regs:
            raise RouteException("You must generate the regular expressions"
                                 " before matching.")
        
        if self.always_scan:
            self.create_regs()
        
        matchlog = []
        if self.prefix:
            if re.match(self._regprefix, url):
                url = re.sub(self._regprefix, r'\1', url)
                if not url:
                    url = '/'
            else:
                return (None, None, matchlog)
        for route in self.matchlist:
            if route.static:
                if self.debug:
                    matchlog.append(dict(route=route, static=True))
                continue
            match = route.match(url, self.environ, self.sub_domains, 
                self.sub_domains_ignore, self.domain_match)
            if self.debug:
                matchlog.append(dict(route=route, regexp=bool(match)))
            if match:
                return (match, route, matchlog)
        return (None, None, matchlog)
    
    def match(self, url):
        """Match a URL against against one of the routes contained.
        
        Will return None if no valid match is found.
        
        .. code-block:: python
            
            resultdict = m.match('/joe/sixpack')
        
        """
        if not url:
            raise RouteException('No URL provided, the minimum URL necessary'
                                 ' to match is "/".')
        
        result = self._match(url)
        if self.debug:
            return result[0], result[1], result[2]
        if result[0]:
            return result[0]
        return None
    
    def routematch(self, url):
        """Match a URL against against one of the routes contained.
        
        Will return None if no valid match is found, otherwise a
        result dict and a route object is returned.
        
        .. code-block:: python
        
            resultdict, route_obj = m.match('/joe/sixpack')
        
        """
        result = self._match(url)
        if self.debug:
            return result[0], result[1], result[2]
        if result[0]:
            return result[0], result[1]
        return None
    
    def generate(self, *args, **kargs):
        """Generate a route from a set of keywords
        
        Returns the url text, or None if no URL could be generated.
        
        .. code-block:: python
            
            m.generate(controller='content',action='view',id=10)
        
        """
        # Generate ourself if we haven't already
        if not self._created_gens:
            self._create_gens()
        
        if self.append_slash:
            kargs['_append_slash'] = True
                
        if not self.explicit:
            if 'controller' not in kargs:
                kargs['controller'] = 'content'
            if 'action' not in kargs:
                kargs['action'] = 'index'
        
        controller = kargs.get('controller', None)
        action = kargs.get('action', None)

        # If the URL didn't depend on the SCRIPT_NAME, we'll cache it
        # keyed by just by kargs; otherwise we need to cache it with
        # both SCRIPT_NAME and kargs:
        cache_key = unicode(args).encode('utf8') + \
            unicode(kargs).encode('utf8')
        
        if self.urlcache is not None:
            if self.environ:
                cache_key_script_name = '%s:%s' % (
                    self.environ.get('SCRIPT_NAME', ''), cache_key)
            else:
                cache_key_script_name = cache_key
        
            # Check the url cache to see if it exists, use it if it does
            for key in [cache_key, cache_key_script_name]:
                if key in self.urlcache:
                    return self.urlcache[key]
        
        actionlist = self._gendict.get(controller) or self._gendict.get('*')
        if not actionlist:
            return None
        (keylist, sortcache) = actionlist.get(action) or \
                               actionlist.get('*', (None, None))
        if not keylist:
            return None
        
        keys = frozenset(kargs.keys())
        cacheset = False
        cachekey = unicode(keys)
        cachelist = sortcache.get(cachekey)
        if args:
            keylist = args
        elif cachelist:
            keylist = cachelist
        else:
            cacheset = True
            newlist = []
            for route in keylist:
                if len(route.minkeys-keys) == 0:
                    newlist.append(route)
            keylist = newlist
            
            def keysort(a, b):
                """Sorts two sets of sets, to order them ideally for
                matching."""
                am = a.minkeys
                a = a.maxkeys
                b = b.maxkeys
                
                lendiffa = len(keys^a)
                lendiffb = len(keys^b)
                # If they both match, don't switch them
                if lendiffa == 0 and lendiffb == 0:
                    return 0
                
                # First, if a matches exactly, use it
                if lendiffa == 0:
                    return -1
                
                # Or b matches exactly, use it
                if lendiffb == 0:
                    return 1
                
                # Neither matches exactly, return the one with the most in 
                # common
                if cmp(lendiffa, lendiffb) != 0:
                    return cmp(lendiffa, lendiffb)
                
                # Neither matches exactly, but if they both have just as much 
                # in common
                if len(keys&b) == len(keys&a):
                    # Then we return the shortest of the two
                    return cmp(len(a), len(b))
                
                # Otherwise, we return the one that has the most in common
                else:
                    return cmp(len(keys&b), len(keys&a))
            
            keylist.sort(keysort)
            if cacheset:
                sortcache[cachekey] = keylist
        
        # Iterate through the keylist of sorted routes (or a single route if
        # it was passed in explicitly for hardcoded named routes)
        for route in keylist:
            fail = False
            for key in route.hardcoded:
                kval = kargs.get(key)
                if not kval:
                    continue
                if kval != route.defaults[key]:
                    fail = True
                    break
            if fail:
                continue
            path = route.generate(**kargs)
            if path:
                if self.prefix:
                    path = self.prefix + path
                if self.environ and self.environ.get('SCRIPT_NAME', '') != ''\
                    and not route.absolute:
                    path = self.environ['SCRIPT_NAME'] + path
                    key = cache_key_script_name
                else:
                    key = cache_key
                if self.urlcache is not None:
                    self.urlcache[key] = str(path)
                return str(path)
            else:
                continue
        return None
    
    def resource(self, member_name, collection_name, **kwargs):
        """Generate routes for a controller resource
        
        The member_name name should be the appropriate singular version
        of the resource given your locale and used with members of the
        collection. The collection_name name will be used to refer to
        the resource collection methods and should be a plural version
        of the member_name argument. By default, the member_name name
        will also be assumed to map to a controller you create.
        
        The concept of a web resource maps somewhat directly to 'CRUD' 
        operations. The overlying things to keep in mind is that
        mapping a resource is about handling creating, viewing, and
        editing that resource.
        
        All keyword arguments are optional.
        
        ``controller``
            If specified in the keyword args, the controller will be
            the actual controller used, but the rest of the naming
            conventions used for the route names and URL paths are
            unchanged.
        
        ``collection``
            Additional action mappings used to manipulate/view the
            entire set of resources provided by the controller.
            
            Example::
                
                map.resource('message', 'messages', collection={'rss':'GET'})
                # GET /message/rss (maps to the rss action)
                # also adds named route "rss_message"
        
        ``member``
            Additional action mappings used to access an individual
            'member' of this controllers resources.
            
            Example::
                
                map.resource('message', 'messages', member={'mark':'POST'})
                # POST /message/1/mark (maps to the mark action)
                # also adds named route "mark_message"
        
        ``new``
            Action mappings that involve dealing with a new member in
            the controller resources.
            
            Example::
                
                map.resource('message', 'messages', new={'preview':'POST'})
                # POST /message/new/preview (maps to the preview action)
                # also adds a url named "preview_new_message"
        
        ``path_prefix``
            Prepends the URL path for the Route with the path_prefix
            given. This is most useful for cases where you want to mix
            resources or relations between resources.
        
        ``name_prefix``
            Perpends the route names that are generated with the
            name_prefix given. Combined with the path_prefix option,
            it's easy to generate route names and paths that represent
            resources that are in relations.
            
            Example::
                
                map.resource('message', 'messages', controller='categories', 
                    path_prefix='/category/:category_id', 
                    name_prefix="category_")
                # GET /category/7/message/1
                # has named route "category_message"
                
        ``parent_resource`` 
            A ``dict`` containing information about the parent
            resource, for creating a nested resource. It should contain
            the ``member_name`` and ``collection_name`` of the parent
            resource. This ``dict`` will 
            be available via the associated ``Route`` object which can
            be accessed during a request via
            ``request.environ['routes.route']``
 
            If ``parent_resource`` is supplied and ``path_prefix``
            isn't, ``path_prefix`` will be generated from
            ``parent_resource`` as
            "<parent collection name>/:<parent member name>_id". 

            If ``parent_resource`` is supplied and ``name_prefix``
            isn't, ``name_prefix`` will be generated from
            ``parent_resource`` as  "<parent member name>_". 
 
            Example:: 
 
                >>> from routes.util import url_for 
                >>> m = Mapper() 
                >>> m.resource('location', 'locations', 
                ...            parent_resource=dict(member_name='region', 
                ...                                 collection_name='regions'))
                >>> # path_prefix is "regions/:region_id" 
                >>> # name prefix is "region_"  
                >>> url_for('region_locations', region_id=13) 
                '/regions/13/locations'
                >>> url_for('region_new_location', region_id=13) 
                '/regions/13/locations/new'
                >>> url_for('region_location', region_id=13, id=60) 
                '/regions/13/locations/60'
                >>> url_for('region_edit_location', region_id=13, id=60) 
                '/regions/13/locations/60/edit'

            Overriding generated ``path_prefix``::

                >>> m = Mapper()
                >>> m.resource('location', 'locations',
                ...            parent_resource=dict(member_name='region',
                ...                                 collection_name='regions'),
                ...            path_prefix='areas/:area_id')
                >>> # name prefix is "region_"
                >>> url_for('region_locations', area_id=51)
                '/areas/51/locations'

            Overriding generated ``name_prefix``::

                >>> m = Mapper()
                >>> m.resource('location', 'locations',
                ...            parent_resource=dict(member_name='region',
                ...                                 collection_name='regions'),
                ...            name_prefix='')
                >>> # path_prefix is "regions/:region_id" 
                >>> url_for('locations', region_id=51)
                '/regions/51/locations'

        """
        collection = kwargs.pop('collection', {})
        member = kwargs.pop('member', {})
        new = kwargs.pop('new', {})
        path_prefix = kwargs.pop('path_prefix', None)
        name_prefix = kwargs.pop('name_prefix', None)
        parent_resource = kwargs.pop('parent_resource', None)
        
        # Generate ``path_prefix`` if ``path_prefix`` wasn't specified and 
        # ``parent_resource`` was. Likewise for ``name_prefix``. Make sure
        # that ``path_prefix`` and ``name_prefix`` *always* take precedence if
        # they are specified--in particular, we need to be careful when they
        # are explicitly set to "".
        if parent_resource is not None: 
            if path_prefix is None: 
                path_prefix = '%s/:%s_id' % (parent_resource['collection_name'], 
                                             parent_resource['member_name']) 
            if name_prefix is None:
                name_prefix = '%s_' % parent_resource['member_name']
        else:
            if path_prefix is None: path_prefix = ''
            if name_prefix is None: name_prefix = ''
        
        # Ensure the edit and new actions are in and GET
        member['edit'] = 'GET'
        new.update({'new': 'GET'})
        
        # Make new dict's based off the old, except the old values become keys,
        # and the old keys become items in a list as the value
        def swap(dct, newdct):
            """Swap the keys and values in the dict, and uppercase the values
            from the dict during the swap."""
            for key, val in dct.iteritems():
                newdct.setdefault(val.upper(), []).append(key)
            return newdct
        collection_methods = swap(collection, {})
        member_methods = swap(member, {})
        new_methods = swap(new, {})
        
        # Insert create, update, and destroy methods
        collection_methods.setdefault('POST', []).insert(0, 'create')
        member_methods.setdefault('PUT', []).insert(0, 'update')
        member_methods.setdefault('DELETE', []).insert(0, 'delete')
        
        # If there's a path prefix option, use it with the controller
        controller = strip_slashes(collection_name)
        path_prefix = strip_slashes(path_prefix)
        path_prefix = '/' + path_prefix
        if path_prefix and path_prefix != '/':
            path = path_prefix + '/' + controller
        else:
            path = '/' + controller
        collection_path = path
        new_path = path + "/new"
        member_path = path + "/:(id)"
        
        options = { 
            'controller': kwargs.get('controller', controller),
            '_member_name': member_name,
            '_collection_name': collection_name,
            '_parent_resource': parent_resource,
        }
        
        def requirements_for(meth):
            """Returns a new dict to be used for all route creation as the
            route options"""
            opts = options.copy()
            if method != 'any': 
                opts['conditions'] = {'method':[meth.upper()]}
            return opts
        
        # Add the routes for handling collection methods
        for method, lst in collection_methods.iteritems():
            primary = (method != 'GET' and lst.pop(0)) or None
            route_options = requirements_for(method)
            for action in lst:
                route_options['action'] = action
                route_name = "%s%s_%s" % (name_prefix, action, collection_name)
                self.connect("formatted_" + route_name, "%s/%s.:(format)" % \
                             (collection_path, action), **route_options)
                self.connect(route_name, "%s/%s" % (collection_path, action),
                                                    **route_options)
            if primary:
                route_options['action'] = primary
                self.connect("%s.:(format)" % collection_path, **route_options)
                self.connect(collection_path, **route_options)
        
        # Specifically add in the built-in 'index' collection method and its 
        # formatted version
        self.connect("formatted_" + name_prefix + collection_name, 
            collection_path + ".:(format)", action='index', 
            conditions={'method':['GET']}, **options)
        self.connect(name_prefix + collection_name, collection_path, 
                     action='index', conditions={'method':['GET']}, **options)
        
        # Add the routes that deal with new resource methods
        for method, lst in new_methods.iteritems():
            route_options = requirements_for(method)
            for action in lst:
                path = (action == 'new' and new_path) or "%s/%s" % (new_path, 
                                                                    action)
                name = "new_" + member_name
                if action != 'new':
                    name = action + "_" + name
                route_options['action'] = action
                formatted_path = (action == 'new' and new_path + '.:(format)') or \
                    "%s/%s.:(format)" % (new_path, action)
                self.connect("formatted_" + name_prefix + name, formatted_path, 
                             **route_options)
                self.connect(name_prefix + name, path, **route_options)
        
        requirements_regexp = '[^\/]+'

        # Add the routes that deal with member methods of a resource
        for method, lst in member_methods.iteritems():
            route_options = requirements_for(method)
            route_options['requirements'] = {'id':requirements_regexp}
            if method not in ['POST', 'GET', 'any']:
                primary = lst.pop(0)
            else:
                primary = None
            for action in lst:
                route_options['action'] = action
                self.connect("formatted_%s%s_%s" % (name_prefix, action, 
                                                    member_name),
                    "%s/%s.:(format)" % (member_path, action), **route_options)
                self.connect("%s%s_%s" % (name_prefix, action, member_name),
                    "%s/%s" % (member_path, action), **route_options)
            if primary:
                route_options['action'] = primary
                self.connect("%s.:(format)" % member_path, **route_options)
                self.connect(member_path, **route_options)
        
        # Specifically add the member 'show' method
        route_options = requirements_for('GET')
        route_options['action'] = 'show'
        route_options['requirements'] = {'id':requirements_regexp}
        self.connect("formatted_" + name_prefix + member_name, 
                     member_path + ".:(format)", **route_options)
        self.connect(name_prefix + member_name, member_path, **route_options)

########NEW FILE########
__FILENAME__ = middleware
"""Routes WSGI Middleware"""
import re
import logging

try:
    from paste.wsgiwrappers import WSGIRequest
except:
    pass

from routes.base import request_config

log = logging.getLogger('routes.middleware')

class RoutesMiddleware(object):
    """Routing middleware that handles resolving the PATH_INFO in
    addition to optionally recognizing method overriding."""
    def __init__(self, wsgi_app, mapper, use_method_override=True, 
                 path_info=True):
        """Create a Route middleware object
        
        Using the use_method_override keyword will require Paste to be
        installed, and your application should use Paste's WSGIRequest
        object as it will properly handle POST issues with wsgi.input
        should Routes check it.
        
        If path_info is True, then should a route var contain
        path_info, the SCRIPT_NAME and PATH_INFO will be altered
        accordingly. This should be used with routes like:
        
        .. code-block:: python
        
            map.connect('blog/*path_info', controller='blog', path_info='')
        
        """
        self.app = wsgi_app
        self.mapper = mapper
        self.use_method_override = use_method_override
        self.path_info = path_info
        log.debug("Initialized with method overriding = %s, and path info "
                  "altering = %s", use_method_override, path_info)
    
    def __call__(self, environ, start_response):
        """Resolves the URL in PATH_INFO, and uses wsgi.routing_args
        to pass on URL resolver results."""
        config = request_config()
        config.mapper = self.mapper
        
        old_method = None
        if self.use_method_override:
            req = WSGIRequest(environ)
            req.errors = 'ignore'
            if '_method' in environ.get('QUERY_STRING', '') and \
                '_method' in req.GET:
                old_method = environ['REQUEST_METHOD']
                environ['REQUEST_METHOD'] = req.GET['_method'].upper()
                log.debug("_method found in QUERY_STRING, altering request"
                          " method to %s", environ['REQUEST_METHOD'])
            elif is_form_post(environ) and '_method' in req.POST:
                old_method = environ['REQUEST_METHOD']
                environ['REQUEST_METHOD'] = req.POST['_method'].upper()
                log.debug("_method found in POST data, altering request "
                          "method to %s", environ['REQUEST_METHOD'])
        
        # Run the actual route matching
        # -- Assignment of environ to config triggers route matching
        config.environ = environ
        
        match = config.mapper_dict
        route = config.route
        
        if old_method:
            environ['REQUEST_METHOD'] = old_method
        
        urlinfo = "%s %s" % (environ['REQUEST_METHOD'], environ['PATH_INFO'])
        if not match:
            match = {}
            log.debug("No route matched for %s", urlinfo)
        else:
            log.debug("Matched %s", urlinfo)
            log.debug("Route path: '%s', defaults: %s", route.routepath, 
                      route.defaults)
            log.debug("Match dict: %s", match)
                
        environ['wsgiorg.routing_args'] = ((), match)
        environ['routes.route'] = route

        # If the route included a path_info attribute and it should be used to
        # alter the environ, we'll pull it out
        if self.path_info and match.get('path_info'):
            oldpath = environ['PATH_INFO']
            newpath = match.get('path_info') or ''
            environ['PATH_INFO'] = newpath
            if not environ['PATH_INFO'].startswith('/'):
                environ['PATH_INFO'] = '/' + environ['PATH_INFO']
            environ['SCRIPT_NAME'] += re.sub(r'^(.*?)/' + newpath + '$', 
                                             r'\1', oldpath)
            if environ['SCRIPT_NAME'].endswith('/'):
                environ['SCRIPT_NAME'] = environ['SCRIPT_NAME'][:-1]
        
        response = self.app(environ, start_response)
        del config.environ
        del self.mapper.environ
        return response

def is_form_post(environ):
    """Determine whether the request is a POSTed html form"""
    if environ['REQUEST_METHOD'] != 'POST':
        return False
    content_type = environ.get('CONTENT_TYPE', '').lower()
    if ';' in content_type:
        content_type = content_type.split(';', 1)[0]
    return content_type in ('application/x-www-form-urlencoded',
                            'multipart/form-data')

########NEW FILE########
__FILENAME__ = route
import re
import sys
import urllib

if sys.version < '2.4':
    from sets import ImmutableSet as frozenset

from routes.util import _url_quote as url_quote


class Route(object):
    """The Route object holds a route recognition and generation
    routine.
    
    See Route.__init__ docs for usage.
    
    """
    def __init__(self, routepath, **kargs):
        """Initialize a route, with a given routepath for
        matching/generation
        
        The set of keyword args will be used as defaults.
        
        Usage::
        
            >>> from routes.base import Route
            >>> newroute = Route(':controller/:action/:id')
            >>> newroute.defaults
            {'action': 'index', 'id': None}
            >>> newroute = Route('date/:year/:month/:day',  
            ...     controller="blog", action="view")
            >>> newroute = Route('archives/:page', controller="blog", 
            ...     action="by_page", requirements = { 'page':'\d{1,2}' })
            >>> newroute.reqs
            {'page': '\\\d{1,2}'}
        
        .. Note:: 
            Route is generally not called directly, a Mapper instance
            connect method should be used to add routes.
        
        """
        self.routepath = routepath
        self.sub_domains = False
        self.prior = None
        self.minimization = kargs.pop('_minimize', True)
        self.encoding = kargs.pop('_encoding', 'utf-8')
        self.reqs = kargs.get('requirements', {})
        self.decode_errors = 'replace'
        
        # Don't bother forming stuff we don't need if its a static route
        self.static = kargs.get('_static', False)
        self.filter = kargs.pop('_filter', None)
        self.absolute = kargs.pop('_absolute', False)
        
        # Pull out the member/collection name if present, this applies only to
        # map.resource
        self.member_name = kargs.pop('_member_name', None)
        self.collection_name = kargs.pop('_collection_name', None)
        self.parent_resource = kargs.pop('_parent_resource', None)
        
        # Pull out route conditions
        self.conditions = kargs.pop('conditions', None)
        
        # Determine if explicit behavior should be used
        self.explicit = kargs.pop('_explicit', False)
        
        # reserved keys that don't count
        reserved_keys = ['requirements']
        
        # special chars to indicate a natural split in the URL
        self.done_chars = ('/', ',', ';', '.', '#')
        
        # Strip preceding '/' if present, and not minimizing
        if routepath.startswith('/') and self.minimization:
            routepath = routepath[1:]
        
        # Build our routelist, and the keys used in the route
        self.routelist = routelist = self._pathkeys(routepath)
        routekeys = frozenset([key['name'] for key in routelist \
                               if isinstance(key, dict)])
        
        if not self.minimization:
            self.make_full_route()
        
        # Build a req list with all the regexp requirements for our args
        self.req_regs = {}
        for key, val in self.reqs.iteritems():
            self.req_regs[key] = re.compile('^' + val + '$')
        # Update our defaults and set new default keys if needed. defaults
        # needs to be saved
        (self.defaults, defaultkeys) = self._defaults(routekeys, 
                                                      reserved_keys, kargs)
        # Save the maximum keys we could utilize
        self.maxkeys = defaultkeys | routekeys
        
        # Populate our minimum keys, and save a copy of our backward keys for
        # quicker generation later
        (self.minkeys, self.routebackwards) = self._minkeys(routelist[:])
        
        # Populate our hardcoded keys, these are ones that are set and don't 
        # exist in the route
        self.hardcoded = frozenset([key for key in self.maxkeys \
            if key not in routekeys and self.defaults[key] is not None])
    
    def make_full_route(self):
        """Make a full routelist string for use with non-minimized
        generation"""
        regpath = ''
        for part in self.routelist:
            if isinstance(part, dict):
                regpath += '%(' + part['name'] + ')s'
            else:
                regpath += part
        self.regpath = regpath
    
    def make_unicode(self, s):
        """Transform the given argument into a unicode string."""
        if isinstance(s, unicode):
            return s
        elif isinstance(s, str):
            return s.decode(self.encoding)
        elif callable(s):
            return s
        else:
            return unicode(s)
    
    def _pathkeys(self, routepath):
        """Utility function to walk the route, and pull out the valid
        dynamic/wildcard keys."""
        collecting = False
        current = ''
        done_on = ''
        var_type = ''
        just_started = False
        routelist = []
        for char in routepath:
            if char in [':', '*', '{'] and not collecting:
                just_started = True
                collecting = True
                var_type = char
                if char == '{':
                    done_on = '}'
                    just_started = False
                if len(current) > 0:
                    routelist.append(current)
                    current = ''
            elif collecting and just_started:
                just_started = False
                if char == '(':
                    done_on = ')'
                else:
                    current = char
                    done_on = self.done_chars + ('-',)
            elif collecting and char not in done_on:
                current += char
            elif collecting:
                collecting = False
                if var_type == '{':
                    opts = current.split(':')
                    if len(opts) > 1:
                        current = opts[0]
                        self.reqs[current] = opts[1]
                    var_type = ':'
                routelist.append(dict(type=var_type, name=current))
                if char in self.done_chars:
                    routelist.append(char)
                done_on = var_type = current = ''
            else:
                current += char
        if collecting:
            routelist.append(dict(type=var_type, name=current))
        elif current:
            routelist.append(current)
        return routelist

    def _minkeys(self, routelist):
        """Utility function to walk the route backwards
        
        Will also determine the minimum keys we can handle to generate
        a working route.
        
        routelist is a list of the '/' split route path
        defaults is a dict of all the defaults provided for the route
        
        """
        minkeys = []
        backcheck = routelist[:]
        
        # If we don't honor minimization, we need all the keys in the
        # route path
        if not self.minimization:
            for part in backcheck:
                if isinstance(part, dict):
                    minkeys.append(part['name'])
            return (frozenset(minkeys), backcheck)
        
        gaps = False
        backcheck.reverse()
        for part in backcheck:
            if not isinstance(part, dict) and part not in self.done_chars:
                gaps = True
                continue
            elif not isinstance(part, dict):
                continue
            key = part['name']
            if self.defaults.has_key(key) and not gaps:
                continue
            minkeys.append(key)
            gaps = True
        return  (frozenset(minkeys), backcheck)
    
    def _defaults(self, routekeys, reserved_keys, kargs):
        """Creates default set with values stringified
        
        Put together our list of defaults, stringify non-None values
        and add in our action/id default if they use it and didn't
        specify it.
        
        defaultkeys is a list of the currently assumed default keys
        routekeys is a list of the keys found in the route path
        reserved_keys is a list of keys that are not
        
        """
        defaults = {}
        # Add in a controller/action default if they don't exist
        if 'controller' not in routekeys and 'controller' not in kargs \
           and not self.explicit:
            kargs['controller'] = 'content'
        if 'action' not in routekeys and 'action' not in kargs \
           and not self.explicit:
            kargs['action'] = 'index'
        defaultkeys = frozenset([key for key in kargs.keys() \
                                 if key not in reserved_keys])
        for key in defaultkeys:
            if kargs[key] is not None:
                defaults[key] = self.make_unicode(kargs[key])
            else:
                defaults[key] = None
        if 'action' in routekeys and not defaults.has_key('action') \
           and not self.explicit:
            defaults['action'] = 'index'
        if 'id' in routekeys and not defaults.has_key('id') \
           and not self.explicit:
            defaults['id'] = None
        newdefaultkeys = frozenset([key for key in defaults.keys() \
                                    if key not in reserved_keys])
        
        return (defaults, newdefaultkeys)
        
    def makeregexp(self, clist):
        """Create a regular expression for matching purposes
        
        Note: This MUST be called before match can function properly.
        
        clist should be a list of valid controller strings that can be 
        matched, for this reason makeregexp should be called by the web
        framework after it knows all available controllers that can be
        utilized.
        
        """
        if self.minimization:
            reg = self.buildnextreg(self.routelist, clist)[0]
            if not reg:
                reg = '/'
            reg = reg + '(/)?' + '$'
        
            if not reg.startswith('/'):
                reg = '/' + reg
        else:
            reg = self.buildfullreg(clist)
        
        reg = '^' + reg
        
        self.regexp = reg
        self.regmatch = re.compile(reg)
    
    def buildfullreg(self, clist):
        """Build the regexp by iterating through the routelist and
        replacing dicts with the appropriate regexp match"""
        regparts = []
        for part in self.routelist:
            if isinstance(part, dict):
                var = part['name']
                if var == 'controller':
                    partmatch = '|'.join(map(re.escape, clist))
                elif part['type'] == ':':
                    partmatch = self.reqs.get(var) or '[^/]+?'
                else:
                    partmatch = self.reqs.get(var) or '.+?'
                regparts.append('(?P<%s>%s)' % (var, partmatch))
            else:
                regparts.append(re.escape(part))
        regexp = ''.join(regparts) + '$'
        return regexp
    
    def buildnextreg(self, path, clist):
        """Recursively build our regexp given a path, and a controller
        list.
        
        Returns the regular expression string, and two booleans that
        can be ignored as they're only used internally by buildnextreg.
        
        """
        if path:
            part = path[0]
        else:
            part = ''
        reg = ''
        
        # noreqs will remember whether the remainder has either a string 
        # match, or a non-defaulted regexp match on a key, allblank remembers
        # if the rest could possible be completely empty
        (rest, noreqs, allblank) = ('', True, True)
        if len(path[1:]) > 0:
            self.prior = part
            (rest, noreqs, allblank) = self.buildnextreg(path[1:], clist)
        
        if isinstance(part, dict) and part['type'] == ':':
            var = part['name']
            partreg = ''
            
            # First we plug in the proper part matcher
            if self.reqs.has_key(var):
                partreg = '(?P<' + var + '>' + self.reqs[var] + ')'
            elif var == 'controller':
                partreg = '(?P<' + var + '>' + '|'.join(map(re.escape, clist))
                partreg += ')'
            elif self.prior in ['/', '#']:
                partreg = '(?P<' + var + '>[^' + self.prior + ']+?)'
            else:
                if not rest:
                    partreg = '(?P<' + var + '>[^%s]+?)' % '/'
                else:
                    end = ''.join(self.done_chars)
                    rem = rest
                    if rem[0] == '\\' and len(rem) > 1:
                        rem = rem[1]
                    elif rem.startswith('(\\') and len(rem) > 2:
                        rem = rem[2]
                    else:
                        rem = end
                    rem = frozenset(rem) | frozenset(['/'])
                    partreg = '(?P<' + var + '>[^%s]+?)' % ''.join(rem)
            
            if self.reqs.has_key(var):
                noreqs = False
            if not self.defaults.has_key(var): 
                allblank = False
                noreqs = False
            
            # Now we determine if its optional, or required. This changes 
            # depending on what is in the rest of the match. If noreqs is 
            # true, then its possible the entire thing is optional as there's
            # no reqs or string matches.
            if noreqs:
                # The rest is optional, but now we have an optional with a 
                # regexp. Wrap to ensure that if we match anything, we match
                # our regexp first. It's still possible we could be completely
                # blank as we have a default
                if self.reqs.has_key(var) and self.defaults.has_key(var):
                    reg = '(' + partreg + rest + ')?'
                
                # Or we have a regexp match with no default, so now being 
                # completely blank form here on out isn't possible
                elif self.reqs.has_key(var):
                    allblank = False
                    reg = partreg + rest
                
                # If the character before this is a special char, it has to be
                # followed by this
                elif self.defaults.has_key(var) and \
                     self.prior in (',', ';', '.'):
                    reg = partreg + rest
                
                # Or we have a default with no regexp, don't touch the allblank
                elif self.defaults.has_key(var):
                    reg = partreg + '?' + rest
                
                # Or we have a key with no default, and no reqs. Not possible
                # to be all blank from here
                else:
                    allblank = False
                    reg = partreg + rest
            # In this case, we have something dangling that might need to be
            # matched
            else:
                # If they can all be blank, and we have a default here, we know
                # its safe to make everything from here optional. Since 
                # something else in the chain does have req's though, we have
                # to make the partreg here required to continue matching
                if allblank and self.defaults.has_key(var):
                    reg = '(' + partreg + rest + ')?'
                    
                # Same as before, but they can't all be blank, so we have to 
                # require it all to ensure our matches line up right
                else:
                    reg = partreg + rest
        elif isinstance(part, dict) and part['type'] == '*':
            var = part['name']
            if noreqs:
                if self.defaults.has_key(var):
                    reg = '(?P<' + var + '>.*)' + rest
                else:
                    reg = '(?P<' + var + '>.*)' + rest
                    allblank = False
                    noreqs = False
            else:
                if allblank and self.defaults.has_key(var):
                    reg = '(?P<' + var + '>.*)' + rest
                elif self.defaults.has_key(var):
                    reg = '(?P<' + var + '>.*)' + rest
                else:
                    allblank = False
                    noreqs = False
                    reg = '(?P<' + var + '>.*)' + rest
        elif part and part[-1] in self.done_chars:
            if allblank:
                reg = re.escape(part[:-1]) + '(' + re.escape(part[-1]) + rest
                reg += ')?'
            else:
                allblank = False
                reg = re.escape(part) + rest
        
        # We have a normal string here, this is a req, and it prevents us from 
        # being all blank
        else:
            noreqs = False
            allblank = False
            reg = re.escape(part) + rest
        
        return (reg, noreqs, allblank)
    
    def match(self, url, environ=None, sub_domains=False, 
              sub_domains_ignore=None, domain_match=''):
        """Match a url to our regexp. 
        
        While the regexp might match, this operation isn't
        guaranteed as there's other factors that can cause a match to
        fail even though the regexp succeeds (Default that was relied
        on wasn't given, requirement regexp doesn't pass, etc.).
        
        Therefore the calling function shouldn't assume this will
        return a valid dict, the other possible return is False if a
        match doesn't work out.
        
        """
        # Static routes don't match, they generate only
        if self.static:
            return False
        
        match = self.regmatch.match(url)
        
        if not match:
            return False
            
        if not environ:
            environ = {}
        
        sub_domain = None
        
        if environ.get('HTTP_HOST') and sub_domains:
            host = environ['HTTP_HOST'].split(':')[0]
            sub_match = re.compile('^(.+?)\.%s$' % domain_match)
            subdomain = re.sub(sub_match, r'\1', host)
            if subdomain not in sub_domains_ignore and host != subdomain:
                sub_domain = subdomain
        
        if self.conditions:
            if self.conditions.has_key('method') and \
                environ.get('REQUEST_METHOD') not in self.conditions['method']:
                return False
            
            # Check sub-domains?
            use_sd = self.conditions.get('sub_domain')
            if use_sd and not sub_domain:
                return False
            if isinstance(use_sd, list) and sub_domain not in use_sd:
                return False
        
        matchdict = match.groupdict()
        result = {}
        extras = frozenset(self.defaults.keys()) - frozenset(matchdict.keys())
        for key, val in matchdict.iteritems():
            if key != 'path_info' and self.encoding:
                # change back into python unicode objects from the URL 
                # representation
                try:
                    val = val and val.decode(self.encoding, self.decode_errors)
                except UnicodeDecodeError:
                    return False
            
            if not val and self.defaults.has_key(key) and self.defaults[key]:
                result[key] = self.defaults[key]
            else:
                result[key] = val
        for key in extras:
            result[key] = self.defaults[key]
        
        # Add the sub-domain if there is one
        if sub_domains:
            result['sub_domain'] = sub_domain
        
        # If there's a function, call it with environ and expire if it
        # returns False
        if self.conditions and self.conditions.has_key('function') and \
            not self.conditions['function'](environ, result):
            return False
        
        return result
    
    def generate_non_minimized(self, kargs):
        """Generate a non-minimal version of the URL"""
        # Iterate through the keys that are defaults, and NOT in the route
        # path. If its not in kargs, or doesn't match, or is None, this
        # route won't work
        for k in self.maxkeys - self.minkeys:
            if k not in kargs:
                return False
            elif self.make_unicode(kargs[k]) != \
                self.make_unicode(self.defaults[k]):
                return False
        
        # Ensure that all the args in the route path are present and not None
        for arg in self.minkeys:
            if arg not in kargs or kargs[arg] is None:
                return False
        return self.regpath % kargs
    
    def generate_minimized(self, kargs):
        """Generate a minimized version of the URL"""
        routelist = self.routebackwards
        urllist = []
        gaps = False
        for part in routelist:
            if isinstance(part, dict) and part['type'] == ':':
                arg = part['name']
                
                # For efficiency, check these just once
                has_arg = kargs.has_key(arg)
                has_default = self.defaults.has_key(arg)
                
                # Determine if we can leave this part off
                # First check if the default exists and wasn't provided in the 
                # call (also no gaps)
                if has_default and not has_arg and not gaps:
                    continue
                    
                # Now check to see if there's a default and it matches the 
                # incoming call arg
                if (has_default and has_arg) and self.make_unicode(kargs[arg]) == \
                    self.make_unicode(self.defaults[arg]) and not gaps: 
                    continue
                
                # We need to pull the value to append, if the arg is None and 
                # we have a default, use that
                if has_arg and kargs[arg] is None and has_default and not gaps:
                    continue
                
                # Otherwise if we do have an arg, use that
                elif has_arg:
                    val = kargs[arg]
                
                elif has_default and self.defaults[arg] is not None:
                    val = self.defaults[arg]
                
                # No arg at all? This won't work
                else:
                    return False
                
                urllist.append(url_quote(val, self.encoding))
                if has_arg:
                    del kargs[arg]
                gaps = True
            elif isinstance(part, dict) and part['type'] == '*':
                arg = part['name']
                kar = kargs.get(arg)
                if kar is not None:
                    urllist.append(url_quote(kar, self.encoding))
                    gaps = True
            elif part and part[-1] in self.done_chars:
                if not gaps and part in self.done_chars:
                    continue
                elif not gaps:
                    urllist.append(part[:-1])
                    gaps = True
                else:
                    gaps = True
                    urllist.append(part)
            else:
                gaps = True
                urllist.append(part)
        urllist.reverse()
        url = ''.join(urllist)
        return url
    
    def generate(self, _ignore_req_list=False, _append_slash=False, **kargs):
        """Generate a URL from ourself given a set of keyword arguments
        
        Toss an exception if this
        set of keywords would cause a gap in the url.
        
        """
        # Verify that our args pass any regexp requirements
        if not _ignore_req_list:
            for key in self.reqs.keys():
                val = kargs.get(key)
                if val and not self.req_regs[key].match(self.make_unicode(val)):
                    return False
        
        # Verify that if we have a method arg, its in the method accept list. 
        # Also, method will be changed to _method for route generation
        meth = kargs.get('method')
        if meth:
            if self.conditions and 'method' in self.conditions \
                and meth.upper() not in self.conditions['method']:
                return False
            kargs.pop('method')
        
        if self.minimization:
            url = self.generate_minimized(kargs)
        else:
            url = self.generate_non_minimized(kargs)
        
        if url is False:
            return url
        
        if not url.startswith('/'):
            url = '/' + url
        extras = frozenset(kargs.keys()) - self.maxkeys
        if extras:
            if _append_slash and not url.endswith('/'):
                url += '/'
            url += '?'
            fragments = []
            # don't assume the 'extras' set preserves order: iterate
            # through the ordered kargs instead
            for key in kargs:
                if key not in extras:
                    continue
                if key == 'action' or key == 'controller':
                    continue
                val = kargs[key]
                if isinstance(val, (tuple, list)):
                    for value in val:
                        fragments.append((key, value))
                else:
                    fragments.append((key, val))
                
            url += urllib.urlencode(fragments)
        elif _append_slash and not url.endswith('/'):
            url += '/'
        return url

########NEW FILE########
__FILENAME__ = threadinglocal
try:
    import threading
except ImportError:
    # No threads, so "thread local" means process-global
    class local(object):
        pass
else:
    try:
        local = threading.local
    except AttributeError:
        # Added in 2.4, but now we'll have to define it ourselves
        import thread
        class local(object):

            def __init__(self):
                self.__dict__['__objs'] = {}

            def __getattr__(self, attr, g=thread.get_ident):
                try:
                    return self.__dict__['__objs'][g()][attr]
                except KeyError:
                    raise AttributeError(
                        "No variable %s defined for the thread %s"
                        % (attr, g()))

            def __setattr__(self, attr, value, g=thread.get_ident):
                self.__dict__['__objs'].setdefault(g(), {})[attr] = value

            def __delattr__(self, attr, g=thread.get_ident):
                try:
                    del self.__dict__['__objs'][g()][attr]
                except KeyError:
                    raise AttributeError(
                        "No variable %s defined for thread %s"
                        % (attr, g()))


########NEW FILE########
__FILENAME__ = util
"""Utility functions for use in templates / controllers

*PLEASE NOTE*: Many of these functions expect an initialized RequestConfig
object. This is expected to have been initialized for EACH REQUEST by the web
framework.

"""
import os
import re
import urllib
from routes import request_config

def _screenargs(kargs):
    """
    Private function that takes a dict, and screens it against the current 
    request dict to determine what the dict should look like that is used. 
    This is responsible for the requests "memory" of the current.
    """
    config = request_config()
    
    # Coerce any unicode args with the encoding
    encoding = config.mapper.encoding
    for key, val in kargs.iteritems():
        if isinstance(val, unicode):
            kargs[key] = val.encode(encoding)
    
    if config.mapper.explicit and config.mapper.sub_domains:
        return _subdomain_check(config, kargs)
    elif config.mapper.explicit:
        return kargs
    
    controller_name = kargs.get('controller')
    
    if controller_name and controller_name.startswith('/'):
        # If the controller name starts with '/', ignore route memory
        kargs['controller'] = kargs['controller'][1:]
        return kargs
    elif controller_name and not kargs.has_key('action'):
        # Fill in an action if we don't have one, but have a controller
        kargs['action'] = 'index'
    
    memory_kargs = getattr(config, 'mapper_dict', {}).copy()
    
    # Remove keys from memory and kargs if kargs has them as None
    for key in [key for key in kargs.keys() if kargs[key] is None]:
        del kargs[key]
        if memory_kargs.has_key(key):
            del memory_kargs[key]
    
    # Merge the new args on top of the memory args
    memory_kargs.update(kargs)
    
    # Setup a sub-domain if applicable
    if config.mapper.sub_domains:
        memory_kargs = _subdomain_check(config, memory_kargs)
    
    return memory_kargs

def _subdomain_check(config, kargs):
    """Screen the kargs for a subdomain and alter it appropriately depending
    on the current subdomain or lack therof."""
    if config.mapper.sub_domains:
        subdomain = kargs.pop('sub_domain', None)
        if isinstance(subdomain, unicode):
            subdomain = str(subdomain)
        
        # We use a try/except here, cause the only time there should be no
        # environ is when we're unit testing, in which case we shouldn't be
        # changing kargs and such. The exception catching also won't hurt as
        # badly here vs doing a hasattr on every url check
        try:
            fullhost = config.environ.get('HTTP_HOST') or \
                config.environ.get('SERVER_NAME')
        except AttributeError:
            return kargs
        
        hostmatch = fullhost.split(':')
        host = hostmatch[0]
        port = ''
        if len(hostmatch) > 1:
            port += ':' + hostmatch[1]
        sub_match = re.compile('^.+?\.(%s)$' % config.mapper.domain_match)
        domain = re.sub(sub_match, r'\1', host)
        if subdomain and not host.startswith(subdomain) and \
            subdomain not in config.mapper.sub_domains_ignore:
            kargs['_host'] = subdomain + '.' + domain + port
        elif (subdomain in config.mapper.sub_domains_ignore or \
            subdomain is None) and domain != host:
            kargs['_host'] = domain + port
        return kargs
    else:
        return kargs
    

def _url_quote(string, encoding):
    """A Unicode handling version of urllib.quote."""
    if encoding:
        if isinstance(string, unicode):
            s = string.encode(encoding)
        elif isinstance(string, str):
            # assume the encoding is already correct
            s = string
        else:
            s = unicode(string).encode(encoding)
    else:
        s = str(string)
    return urllib.quote(s, '/')

def url_for(*args, **kargs):
    """Generates a URL 
    
    All keys given to url_for are sent to the Routes Mapper instance for 
    generation except for::
        
        anchor          specified the anchor name to be appened to the path
        host            overrides the default (current) host if provided
        protocol        overrides the default (current) protocol if provided
        qualified       creates the URL with the host/port information as 
                        needed
        
    The URL is generated based on the rest of the keys. When generating a new 
    URL, values will be used from the current request's parameters (if 
    present). The following rules are used to determine when and how to keep 
    the current requests parameters:
    
    * If the controller is present and begins with '/', no defaults are used
    * If the controller is changed, action is set to 'index' unless otherwise 
      specified
    
    For example, if the current request yielded a dict of
    {'controller': 'blog', 'action': 'view', 'id': 2}, with the standard 
    ':controller/:action/:id' route, you'd get the following results::
    
        url_for(id=4)                    =>  '/blog/view/4',
        url_for(controller='/admin')     =>  '/admin',
        url_for(controller='admin')      =>  '/admin/view/2'
        url_for(action='edit')           =>  '/blog/edit/2',
        url_for(action='list', id=None)  =>  '/blog/list'
    
    **Static and Named Routes**
    
    If there is a string present as the first argument, a lookup is done 
    against the named routes table to see if there's any matching routes. The
    keyword defaults used with static routes will be sent in as GET query 
    arg's if a route matches.
    
    If no route by that name is found, the string is assumed to be a raw URL. 
    Should the raw URL begin with ``/`` then appropriate SCRIPT_NAME data will
    be added if present, otherwise the string will be used as the url with 
    keyword args becoming GET query args.
    """
    anchor = kargs.get('anchor')
    host = kargs.get('host')
    protocol = kargs.get('protocol')
    qualified = kargs.pop('qualified', None)
    
    # Remove special words from kargs, convert placeholders
    for key in ['anchor', 'host', 'protocol']:
        if kargs.get(key):
            del kargs[key]
        if kargs.has_key(key+'_'):
            kargs[key] = kargs.pop(key+'_')
    config = request_config()
    route = None
    static = False
    encoding = config.mapper.encoding
    url = ''
    if len(args) > 0:
        route = config.mapper._routenames.get(args[0])
        
        if route and route.defaults.has_key('_static'):
            static = True
            url = route.routepath
        
        # No named route found, assume the argument is a relative path
        if not route:
            static = True
            url = args[0]
        
        if url.startswith('/') and hasattr(config, 'environ') \
                and config.environ.get('SCRIPT_NAME'):
            url = config.environ.get('SCRIPT_NAME') + url
        
        if static:
            if kargs:
                url += '?'
                query_args = []
                for key, val in kargs.iteritems():
                    if isinstance(val, (list, tuple)):
                        for value in val:
                            query_args.append("%s=%s" % (
                                urllib.quote(unicode(key).encode(encoding)),
                                urllib.quote(unicode(value).encode(encoding))))
                    else:
                        query_args.append("%s=%s" % (
                            urllib.quote(unicode(key).encode(encoding)),
                            urllib.quote(unicode(val).encode(encoding))))
                url += '&'.join(query_args)
    if not static:
        route_args = []
        if route:
            if config.mapper.hardcode_names:
                route_args.append(route)
            newargs = route.defaults.copy()
            newargs.update(kargs)
            
            # If this route has a filter, apply it
            if route.filter:
                newargs = route.filter(newargs)
            
            # Handle sub-domains
            newargs = _subdomain_check(config, newargs)
        else:
            newargs = _screenargs(kargs)
        anchor = newargs.pop('_anchor', None) or anchor
        host = newargs.pop('_host', None) or host
        protocol = newargs.pop('_protocol', None) or protocol
        url = config.mapper.generate(*route_args, **newargs)
    if anchor:
        url += '#' + _url_quote(anchor, encoding)
    if host or protocol or qualified:
        if not host and not qualified:
            # Ensure we don't use a specific port, as changing the protocol
            # means that we most likely need a new port
            host = config.host.split(':')[0]
        elif not host:
            host = config.host
        if not protocol:
            protocol = config.protocol
        if url is not None:
            url = protocol + '://' + host + url
    
    if not isinstance(url, str) and url is not None:
        raise RouteException("url_for can only return a string, got "
                        "unicode instead: %s" % url)
    if url is None:
        raise RouteException(
            "url_for could not generate URL. Called with args: %s %s" % \
            (args, kargs))
    return url

def redirect_to(*args, **kargs):
    """Issues a redirect based on the arguments. 
    
    Redirect's *should* occur as a "302 Moved" header, however the web 
    framework may utilize a different method.
    
    All arguments are passed to url_for to retrieve the appropriate URL, then
    the resulting URL it sent to the redirect function as the URL.
    """
    target = url_for(*args, **kargs)
    config = request_config()
    return config.redirect(target)

def controller_scan(directory=None):
    """Scan a directory for python files and use them as controllers"""
    if directory is None:
        return []
    
    def find_controllers(dirname, prefix=''):
        """Locate controllers in a directory"""
        controllers = []
        for fname in os.listdir(dirname):
            filename = os.path.join(dirname, fname)
            if os.path.isfile(filename) and \
                re.match('^[^_]{1,1}.*\.py$', fname):
                controllers.append(prefix + fname[:-3])
            elif os.path.isdir(filename):
                controllers.extend(find_controllers(filename, 
                                                    prefix=prefix+fname+'/'))
        return controllers
    def longest_first(fst, lst):
        """Compare the length of one string to another, shortest goes first"""
        return cmp(len(lst), len(fst))
    controllers = find_controllers(directory)
    controllers.sort(longest_first)
    return controllers

class RouteException(Exception):
    """Tossed during Route exceptions"""
    pass

########NEW FILE########
__FILENAME__ = decoder
"""Implementation of JSONDecoder
"""
import re
import sys
import struct

from simplejson.scanner import make_scanner
try:
    from simplejson._speedups import scanstring as c_scanstring
except ImportError:
    c_scanstring = None

__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    # Note that this function is called from _speedups
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True, _b=BACKSLASH, _m=STRINGCHUNK.match):
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        end = chunk.end()
        content, terminator = chunk.groups()
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                raise ValueError(errmsg("Invalid control character %r at", s, end))
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        if esc != 'u':
            try:
                m = _b[esc]
            except KeyError:
                raise ValueError(
                    errmsg("Invalid \\escape: %r" % (esc,), s, end))
            end += 1
        else:
            esc = s[end + 1:end + 5]
            next_end = end + 5
            msg = "Invalid \\uXXXX escape"
            try:
                if len(esc) != 4:
                    raise ValueError
                uni = int(esc, 16)
                if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                    msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                    if not s[end + 5:end + 7] == '\\u':
                        raise ValueError
                    esc2 = s[end + 7:end + 11]
                    if len(esc2) != 4:
                        raise ValueError
                    uni2 = int(esc2, 16)
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                    next_end += 6
                m = unichr(uni)
            except ValueError:
                raise ValueError(errmsg(msg, s, end))
            end = next_end
        _append(m)
    return u''.join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject((s, end), encoding, strict, scan_once, object_hook, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    pairs = {}
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            return pairs, end + 1
        elif nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end))
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise ValueError(errmsg("Expecting : delimiter", s, end))

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        pairs[key] = value

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end - 1))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end - 1))

    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray((s, end), scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    _append = values.append
    while True:
        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end))

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True):
        """``encoding`` determines the encoding used to interpret any ``str``
        objects decoded by this instance (utf-8 by default).  It has no
        effect when decoding ``unicode`` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as ``unicode``.

        ``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.

        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise ValueError(errmsg("Extra data", s, end, len(s)))
        return obj

    def raw_decode(self, s, idx=0):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode`` beginning
        with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        try:
            obj, end = self.scan_once(s, idx)
        except StopIteration:
            raise ValueError("No JSON object could be decoded")
        return obj, end

########NEW FILE########
__FILENAME__ = encoder
"""Implementation of JSONEncoder
"""
import re

try:
    from simplejson._speedups import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError:
    c_encode_basestring_ascii = None
try:
    from simplejson._speedups import make_encoder as c_make_encoder
except ImportError:
    c_make_encoder = None

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# Assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')
FLOAT_REPR = repr

def encode_basestring(s):
    """Return a JSON representation of a Python string

    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'


def py_encode_basestring_ascii(s):
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = c_encode_basestring_ascii or py_encode_basestring_ascii

class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.

        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        if default is not None:
            self.default = default
        self.encoding = encoding

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        """
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None
                        and not (_encoding == 'utf-8')):
                    o = o.decode(_encoding)
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = self.iterencode(o, _one_shot=True)
        if not isinstance(chunks, (list, tuple)):
            chunks = list(chunks)
        return ''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring
        if self.encoding != 'utf-8':
            def _encoder(o, _orig_encoder=_encoder, _encoding=self.encoding):
                if isinstance(o, str):
                    o = o.decode(_encoding)
                return _orig_encoder(o)

        def floatstr(o, allow_nan=self.allow_nan, _repr=FLOAT_REPR, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor- and/or
            # platform-specific, so do tests which don't depend on the internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError("Out of range float values are not JSON compliant: %r"
                    % (o,))

            return text


        if _one_shot and c_make_encoder is not None and not self.indent and not self.sort_keys:
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan)
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot)
        return _iterencode(o, 0)

def _make_iterencode(markers, _default, _encoder, _indent, _floatstr, _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        ## HACK: hand-optimized bytecode; turn globals into locals
        False=False,
        True=True,
        ValueError=ValueError,
        basestring=basestring,
        dict=dict,
        float=float,
        id=id,
        int=int,
        isinstance=isinstance,
        list=list,
        long=long,
        str=str,
        tuple=tuple,
    ):

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, basestring):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, (int, long)):
                yield buf + str(value)
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (' ' * (_indent * _current_indent_level))
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = dct.items()
            items.sort(key=lambda kv: kv[0])
        else:
            items = dct.iteritems()
        for key, value in items:
            if isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = _floatstr(key)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif _skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, basestring):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, (int, long)):
                yield str(value)
            elif isinstance(value, float):
                yield _floatstr(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (' ' * (_indent * _current_indent_level))
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, basestring):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield _floatstr(o)
        elif isinstance(o, (list, tuple)):
            for chunk in _iterencode_list(o, _current_indent_level):
                yield chunk
        elif isinstance(o, dict):
            for chunk in _iterencode_dict(o, _current_indent_level):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            for chunk in _iterencode(o, _current_indent_level):
                yield chunk
            if markers is not None:
                del markers[markerid]

    return _iterencode

########NEW FILE########
__FILENAME__ = scanner
"""JSON token scanner
"""
import re
try:
    from simplejson._speedups import make_scanner as c_make_scanner
except ImportError:
    c_make_scanner = None

__all__ = ['make_scanner']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict, _scan_once, object_hook)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration

    return _scan_once

make_scanner = c_make_scanner or py_make_scanner

########NEW FILE########
__FILENAME__ = composer

__all__ = ['Composer', 'ComposerError']

from error import MarkedYAMLError
from events import *
from nodes import *

class ComposerError(MarkedYAMLError):
    pass

class Composer(object):

    def __init__(self):
        self.anchors = {}

    def check_node(self):
        # Drop the STREAM-START event.
        if self.check_event(StreamStartEvent):
            self.get_event()

        # If there are more documents available?
        return not self.check_event(StreamEndEvent)

    def get_node(self):
        # Get the root node of the next document.
        if not self.check_event(StreamEndEvent):
            return self.compose_document()

    def compose_document(self):
        # Drop the DOCUMENT-START event.
        self.get_event()

        # Compose the root node.
        node = self.compose_node(None, None)

        # Drop the DOCUMENT-END event.
        self.get_event()

        self.anchors = {}
        return node

    def compose_node(self, parent, index):
        if self.check_event(AliasEvent):
            event = self.get_event()
            anchor = event.anchor
            if anchor not in self.anchors:
                raise ComposerError(None, None, "found undefined alias %r"
                        % anchor.encode('utf-8'), event.start_mark)
            return self.anchors[anchor]
        event = self.peek_event()
        anchor = event.anchor
        if anchor is not None:
            if anchor in self.anchors:
                raise ComposerError("found duplicate anchor %r; first occurence"
                        % anchor.encode('utf-8'), self.anchors[anchor].start_mark,
                        "second occurence", event.start_mark)
        self.descend_resolver(parent, index)
        if self.check_event(ScalarEvent):
            node = self.compose_scalar_node(anchor)
        elif self.check_event(SequenceStartEvent):
            node = self.compose_sequence_node(anchor)
        elif self.check_event(MappingStartEvent):
            node = self.compose_mapping_node(anchor)
        self.ascend_resolver()
        return node

    def compose_scalar_node(self, anchor):
        event = self.get_event()
        tag = event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(ScalarNode, event.value, event.implicit)
        node = ScalarNode(tag, event.value,
                event.start_mark, event.end_mark, style=event.style)
        if anchor is not None:
            self.anchors[anchor] = node
        return node

    def compose_sequence_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(SequenceNode, None, start_event.implicit)
        node = SequenceNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        index = 0
        while not self.check_event(SequenceEndEvent):
            node.value.append(self.compose_node(node, index))
            index += 1
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node

    def compose_mapping_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == u'!':
            tag = self.resolve(MappingNode, None, start_event.implicit)
        node = MappingNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        while not self.check_event(MappingEndEvent):
            #key_event = self.peek_event()
            item_key = self.compose_node(node, None)
            #if item_key in node.value:
            #    raise ComposerError("while composing a mapping", start_event.start_mark,
            #            "found duplicate key", key_event.start_mark)
            item_value = self.compose_node(node, item_key)
            #node.value[item_key] = item_value
            node.value.append((item_key, item_value))
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node


########NEW FILE########
__FILENAME__ = constructor

__all__ = ['BaseConstructor', 'SafeConstructor', 'Constructor',
    'ConstructorError']

from error import *
from nodes import *

import datetime

try:
    set
except NameError:
    from sets import Set as set

import binascii, re, sys, types

class ConstructorError(MarkedYAMLError):
    pass

class BaseConstructor(object):

    yaml_constructors = {}
    yaml_multi_constructors = {}

    def __init__(self):
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.state_generators = []
        self.deep_construct = False

    def check_data(self):
        # If there are more documents available?
        return self.check_node()

    def get_data(self):
        # Construct and return the next document.
        if self.check_node():
            return self.construct_document(self.get_node())

    def construct_document(self, node):
        data = self.construct_object(node)
        while self.state_generators:
            state_generators = self.state_generators
            self.state_generators = []
            for generator in state_generators:
                for dummy in generator:
                    pass
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.deep_construct = False
        return data

    def construct_object(self, node, deep=False):
        if deep:
            old_deep = self.deep_construct
            self.deep_construct = True
        if node in self.constructed_objects:
            return self.constructed_objects[node]
        if node in self.recursive_objects:
            raise ConstructorError(None, None,
                    "found unconstructable recursive node", node.start_mark)
        self.recursive_objects[node] = None
        constructor = None
        state_constructor = None
        tag_suffix = None
        if node.tag in self.yaml_constructors:
            constructor = self.yaml_constructors[node.tag]
        else:
            for tag_prefix in self.yaml_multi_constructors:
                if node.tag.startswith(tag_prefix):
                    tag_suffix = node.tag[len(tag_prefix):]
                    constructor = self.yaml_multi_constructors[tag_prefix]
                    break
            else:
                if None in self.yaml_multi_constructors:
                    tag_suffix = node.tag
                    constructor = self.yaml_multi_constructors[None]
                elif None in self.yaml_constructors:
                    constructor = self.yaml_constructors[None]
                elif isinstance(node, ScalarNode):
                    constructor = self.__class__.construct_scalar
                elif isinstance(node, SequenceNode):
                    constructor = self.__class__.construct_sequence
                elif isinstance(node, MappingNode):
                    constructor = self.__class__.construct_mapping
        if tag_suffix is None:
            data = constructor(self, node)
        else:
            data = constructor(self, tag_suffix, node)
        if isinstance(data, types.GeneratorType):
            generator = data
            data = generator.next()
            if self.deep_construct:
                for dummy in generator:
                    pass
            else:
                self.state_generators.append(generator)
        self.constructed_objects[node] = data
        del self.recursive_objects[node]
        if deep:
            self.deep_construct = old_deep
        return data

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            raise ConstructorError(None, None,
                    "expected a scalar node, but found %s" % node.id,
                    node.start_mark)
        return node.value

    def construct_sequence(self, node, deep=False):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None,
                    "expected a sequence node, but found %s" % node.id,
                    node.start_mark)
        return [self.construct_object(child, deep=deep)
                for child in node.value]

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise ConstructorError("while constructing a mapping", node.start_mark,
                        "found unacceptable key (%s)" % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

    def construct_pairs(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        pairs = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            pairs.append((key, value))
        return pairs

    def add_constructor(cls, tag, constructor):
        if not 'yaml_constructors' in cls.__dict__:
            cls.yaml_constructors = cls.yaml_constructors.copy()
        cls.yaml_constructors[tag] = constructor
    add_constructor = classmethod(add_constructor)

    def add_multi_constructor(cls, tag_prefix, multi_constructor):
        if not 'yaml_multi_constructors' in cls.__dict__:
            cls.yaml_multi_constructors = cls.yaml_multi_constructors.copy()
        cls.yaml_multi_constructors[tag_prefix] = multi_constructor
    add_multi_constructor = classmethod(add_multi_constructor)

class SafeConstructor(BaseConstructor):

    def construct_scalar(self, node):
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if key_node.tag == u'tag:yaml.org,2002:value':
                    return self.construct_scalar(value_node)
        return BaseConstructor.construct_scalar(self, node)

    def flatten_mapping(self, node):
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == u'tag:yaml.org,2002:merge':
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError("while constructing a mapping",
                                    node.start_mark,
                                    "expected a mapping for merging, but found %s"
                                    % subnode.id, subnode.start_mark)
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "expected a mapping or list of mappings for merging, but found %s"
                            % value_node.id, value_node.start_mark)
            elif key_node.tag == u'tag:yaml.org,2002:value':
                key_node.tag = u'tag:yaml.org,2002:str'
                index += 1
            else:
                index += 1
        if merge:
            node.value = merge + node.value

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        return BaseConstructor.construct_mapping(self, node, deep=deep)

    def construct_yaml_null(self, node):
        self.construct_scalar(node)
        return None

    bool_values = {
        u'yes':     True,
        u'no':      False,
        u'true':    True,
        u'false':   False,
        u'on':      True,
        u'off':     False,
    }

    def construct_yaml_bool(self, node):
        value = self.construct_scalar(node)
        return self.bool_values[value.lower()]

    def construct_yaml_int(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value[0] == '0':
            return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

    inf_value = 1e300
    while inf_value != inf_value*inf_value:
        inf_value *= inf_value
    nan_value = -inf_value/inf_value   # Trying to make a quiet NaN (like C99).

    def construct_yaml_float(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '').lower()
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '.inf':
            return sign*self.inf_value
        elif value == '.nan':
            return self.nan_value
        elif ':' in value:
            digits = [float(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0.0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*float(value)

    def construct_yaml_binary(self, node):
        value = self.construct_scalar(node)
        try:
            return str(value).decode('base64')
        except (binascii.Error, UnicodeEncodeError), exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark) 

    timestamp_regexp = re.compile(
            ur'''^(?P<year>[0-9][0-9][0-9][0-9])
                -(?P<month>[0-9][0-9]?)
                -(?P<day>[0-9][0-9]?)
                (?:(?:[Tt]|[ \t]+)
                (?P<hour>[0-9][0-9]?)
                :(?P<minute>[0-9][0-9])
                :(?P<second>[0-9][0-9])
                (?:\.(?P<fraction>[0-9]*))?
                (?:[ \t]*(?P<tz>Z|(?P<tz_sign>[-+])(?P<tz_hour>[0-9][0-9]?)
                (?::(?P<tz_minute>[0-9][0-9]))?))?)?$''', re.X)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        year = int(values['year'])
        month = int(values['month'])
        day = int(values['day'])
        if not values['hour']:
            return datetime.date(year, month, day)
        hour = int(values['hour'])
        minute = int(values['minute'])
        second = int(values['second'])
        fraction = 0
        if values['fraction']:
            fraction = int(values['fraction'][:6].ljust(6, '0'))
        delta = None
        if values['tz_sign']:
            tz_hour = int(values['tz_hour'])
            tz_minute = int(values['tz_minute'] or 0)
            delta = datetime.timedelta(hours=tz_hour, minutes=tz_minute)
            if values['tz_sign'] == '-':
                delta = -delta
        data = datetime.datetime(year, month, day, hour, minute, second, fraction)
        if delta:
            data -= delta
        return data

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        omap = []
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap.append((key, value))

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = []
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing pairs", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = set()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        value = self.construct_scalar(node)
        try:
            return value.encode('ascii')
        except UnicodeEncodeError:
            return value

    def construct_yaml_seq(self, node):
        data = []
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = {}
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = cls.__new__(cls)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)

    def construct_undefined(self, node):
        raise ConstructorError(None, None,
                "could not determine a constructor for the tag %r" % node.tag.encode('utf-8'),
                node.start_mark)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:null',
        SafeConstructor.construct_yaml_null)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:bool',
        SafeConstructor.construct_yaml_bool)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:int',
        SafeConstructor.construct_yaml_int)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:float',
        SafeConstructor.construct_yaml_float)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:binary',
        SafeConstructor.construct_yaml_binary)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:timestamp',
        SafeConstructor.construct_yaml_timestamp)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:omap',
        SafeConstructor.construct_yaml_omap)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:pairs',
        SafeConstructor.construct_yaml_pairs)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:set',
        SafeConstructor.construct_yaml_set)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:str',
        SafeConstructor.construct_yaml_str)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:seq',
        SafeConstructor.construct_yaml_seq)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:map',
        SafeConstructor.construct_yaml_map)

SafeConstructor.add_constructor(None,
        SafeConstructor.construct_undefined)

class Constructor(SafeConstructor):

    def construct_python_str(self, node):
        return self.construct_scalar(node).encode('utf-8')

    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

    def construct_python_long(self, node):
        return long(self.construct_yaml_int(node))

    def construct_python_complex(self, node):
       return complex(self.construct_scalar(node))

    def construct_python_tuple(self, node):
        return tuple(self.construct_sequence(node))

    def find_python_module(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python module", mark,
                    "expected non-empty name appended to the tag", mark)
        try:
            __import__(name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python module", mark,
                    "cannot find module %r (%s)" % (name.encode('utf-8'), exc), mark)
        return sys.modules[name]

    def find_python_name(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python object", mark,
                    "expected non-empty name appended to the tag", mark)
        if u'.' in name:
            # Python 2.4 only
            #module_name, object_name = name.rsplit('.', 1)
            items = name.split('.')
            object_name = items.pop()
            module_name = '.'.join(items)
        else:
            module_name = '__builtin__'
            object_name = name
        try:
            __import__(module_name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find module %r (%s)" % (module_name.encode('utf-8'), exc), mark)
        module = sys.modules[module_name]
        if not hasattr(module, object_name):
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find %r in the module %r" % (object_name.encode('utf-8'),
                        module.__name__), mark)
        return getattr(module, object_name)

    def construct_python_name(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python name", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_name(suffix, node.start_mark)

    def construct_python_module(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python module", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_module(suffix, node.start_mark)

    class classobj: pass

    def make_python_instance(self, suffix, node,
            args=None, kwds=None, newobj=False):
        if not args:
            args = []
        if not kwds:
            kwds = {}
        cls = self.find_python_name(suffix, node.start_mark)
        if newobj and isinstance(cls, type(self.classobj))  \
                and not args and not kwds:
            instance = self.classobj()
            instance.__class__ = cls
            return instance
        elif newobj and isinstance(cls, type):
            return cls.__new__(cls, *args, **kwds)
        else:
            return cls(*args, **kwds)

    def set_python_instance_state(self, instance, state):
        if hasattr(instance, '__setstate__'):
            instance.__setstate__(state)
        else:
            slotstate = {}
            if isinstance(state, tuple) and len(state) == 2:
                state, slotstate = state
            if hasattr(instance, '__dict__'):
                instance.__dict__.update(state)
            elif state:
                slotstate.update(state)
            for key, value in slotstate.items():
                setattr(object, key, value)

    def construct_python_object(self, suffix, node):
        # Format:
        #   !!python/object:module.name { ... state ... }
        instance = self.make_python_instance(suffix, node, newobj=True)
        yield instance
        deep = hasattr(instance, '__setstate__')
        state = self.construct_mapping(node, deep=deep)
        self.set_python_instance_state(instance, state)

    def construct_python_object_apply(self, suffix, node, newobj=False):
        # Format:
        #   !!python/object/apply       # (or !!python/object/new)
        #   args: [ ... arguments ... ]
        #   kwds: { ... keywords ... }
        #   state: ... state ...
        #   listitems: [ ... listitems ... ]
        #   dictitems: { ... dictitems ... }
        # or short format:
        #   !!python/object/apply [ ... arguments ... ]
        # The difference between !!python/object/apply and !!python/object/new
        # is how an object is created, check make_python_instance for details.
        if isinstance(node, SequenceNode):
            args = self.construct_sequence(node, deep=True)
            kwds = {}
            state = {}
            listitems = []
            dictitems = {}
        else:
            value = self.construct_mapping(node, deep=True)
            args = value.get('args', [])
            kwds = value.get('kwds', {})
            state = value.get('state', {})
            listitems = value.get('listitems', [])
            dictitems = value.get('dictitems', {})
        instance = self.make_python_instance(suffix, node, args, kwds, newobj)
        if state:
            self.set_python_instance_state(instance, state)
        if listitems:
            instance.extend(listitems)
        if dictitems:
            for key in dictitems:
                instance[key] = dictitems[key]
        return instance

    def construct_python_object_new(self, suffix, node):
        return self.construct_python_object_apply(suffix, node, newobj=True)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/none',
    Constructor.construct_yaml_null)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/bool',
    Constructor.construct_yaml_bool)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/str',
    Constructor.construct_python_str)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/unicode',
    Constructor.construct_python_unicode)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/int',
    Constructor.construct_yaml_int)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/long',
    Constructor.construct_python_long)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/float',
    Constructor.construct_yaml_float)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/complex',
    Constructor.construct_python_complex)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/list',
    Constructor.construct_yaml_seq)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/tuple',
    Constructor.construct_python_tuple)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/dict',
    Constructor.construct_yaml_map)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/name:',
    Constructor.construct_python_name)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/module:',
    Constructor.construct_python_module)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object:',
    Constructor.construct_python_object)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/apply:',
    Constructor.construct_python_object_apply)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/new:',
    Constructor.construct_python_object_new)


########NEW FILE########
__FILENAME__ = cyaml

__all__ = ['CBaseLoader', 'CSafeLoader', 'CLoader',
        'CBaseDumper', 'CSafeDumper', 'CDumper']

from _yaml import CParser, CEmitter

from constructor import *

from serializer import *
from representer import *

from resolver import *

class CBaseLoader(CParser, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class CSafeLoader(CParser, SafeConstructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class CLoader(CParser, Constructor, Resolver):

    def __init__(self, stream):
        CParser.__init__(self, stream)
        Constructor.__init__(self)
        Resolver.__init__(self)

class CBaseDumper(CEmitter, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CSafeDumper(CEmitter, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class CDumper(CEmitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        CEmitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = dumper

__all__ = ['BaseDumper', 'SafeDumper', 'Dumper']

from emitter import *
from serializer import *
from representer import *
from resolver import *

class BaseDumper(Emitter, Serializer, BaseRepresenter, BaseResolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_uncode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class SafeDumper(Emitter, Serializer, SafeRepresenter, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        SafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class Dumper(Emitter, Serializer, Representer, Resolver):

    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        Representer.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = emitter

# Emitter expects events obeying the following grammar:
# stream ::= STREAM-START document* STREAM-END
# document ::= DOCUMENT-START node DOCUMENT-END
# node ::= SCALAR | sequence | mapping
# sequence ::= SEQUENCE-START node* SEQUENCE-END
# mapping ::= MAPPING-START (node node)* MAPPING-END

__all__ = ['Emitter', 'EmitterError']

from error import YAMLError
from events import *

import re

class EmitterError(YAMLError):
    pass

class ScalarAnalysis(object):
    def __init__(self, scalar, empty, multiline,
            allow_flow_plain, allow_block_plain,
            allow_single_quoted, allow_double_quoted,
            allow_block):
        self.scalar = scalar
        self.empty = empty
        self.multiline = multiline
        self.allow_flow_plain = allow_flow_plain
        self.allow_block_plain = allow_block_plain
        self.allow_single_quoted = allow_single_quoted
        self.allow_double_quoted = allow_double_quoted
        self.allow_block = allow_block

class Emitter(object):

    DEFAULT_TAG_PREFIXES = {
        u'!' : u'!',
        u'tag:yaml.org,2002:' : u'!!',
    }

    def __init__(self, stream, canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None):

        # The stream should have the methods `write` and possibly `flush`.
        self.stream = stream

        # Encoding can be overriden by STREAM-START.
        self.encoding = None

        # Emitter is a state machine with a stack of states to handle nested
        # structures.
        self.states = []
        self.state = self.expect_stream_start

        # Current event and the event queue.
        self.events = []
        self.event = None

        # The current indentation level and the stack of previous indents.
        self.indents = []
        self.indent = None

        # Flow level.
        self.flow_level = 0

        # Contexts.
        self.root_context = False
        self.sequence_context = False
        self.mapping_context = False
        self.simple_key_context = False

        # Characteristics of the last emitted character:
        #  - current position.
        #  - is it a whitespace?
        #  - is it an indention character
        #    (indentation space, '-', '?', or ':')?
        self.line = 0
        self.column = 0
        self.whitespace = True
        self.indention = True

        # Formatting details.
        self.canonical = canonical
        self.allow_unicode = allow_unicode
        self.best_indent = 2
        if indent and 1 < indent < 10:
            self.best_indent = indent
        self.best_width = 80
        if width and width > self.best_indent*2:
            self.best_width = width
        self.best_line_break = u'\n'
        if line_break in [u'\r', u'\n', u'\r\n']:
            self.best_line_break = line_break

        # Tag prefixes.
        self.tag_prefixes = None

        # Prepared anchor and tag.
        self.prepared_anchor = None
        self.prepared_tag = None

        # Scalar analysis and style.
        self.analysis = None
        self.style = None

    def emit(self, event):
        self.events.append(event)
        while not self.need_more_events():
            self.event = self.events.pop(0)
            self.state()
            self.event = None

    # In some cases, we wait for a few next events before emitting.

    def need_more_events(self):
        if not self.events:
            return True
        event = self.events[0]
        if isinstance(event, DocumentStartEvent):
            return self.need_events(1)
        elif isinstance(event, SequenceStartEvent):
            return self.need_events(2)
        elif isinstance(event, MappingStartEvent):
            return self.need_events(3)
        else:
            return False

    def need_events(self, count):
        level = 0
        for event in self.events[1:]:
            if isinstance(event, (DocumentStartEvent, CollectionStartEvent)):
                level += 1
            elif isinstance(event, (DocumentEndEvent, CollectionEndEvent)):
                level -= 1
            elif isinstance(event, StreamEndEvent):
                level = -1
            if level < 0:
                return False
        return (len(self.events) < count+1)

    def increase_indent(self, flow=False, indentless=False):
        self.indents.append(self.indent)
        if self.indent is None:
            if flow:
                self.indent = self.best_indent
            else:
                self.indent = 0
        elif not indentless:
            self.indent += self.best_indent

    # States.

    # Stream handlers.

    def expect_stream_start(self):
        if isinstance(self.event, StreamStartEvent):
            if self.event.encoding:
                self.encoding = self.event.encoding
            self.write_stream_start()
            self.state = self.expect_first_document_start
        else:
            raise EmitterError("expected StreamStartEvent, but got %s"
                    % self.event)

    def expect_nothing(self):
        raise EmitterError("expected nothing, but got %s" % self.event)

    # Document handlers.

    def expect_first_document_start(self):
        return self.expect_document_start(first=True)

    def expect_document_start(self, first=False):
        if isinstance(self.event, DocumentStartEvent):
            if self.event.version:
                version_text = self.prepare_version(self.event.version)
                self.write_version_directive(version_text)
            self.tag_prefixes = self.DEFAULT_TAG_PREFIXES.copy()
            if self.event.tags:
                handles = self.event.tags.keys()
                handles.sort()
                for handle in handles:
                    prefix = self.event.tags[handle]
                    self.tag_prefixes[prefix] = handle
                    handle_text = self.prepare_tag_handle(handle)
                    prefix_text = self.prepare_tag_prefix(prefix)
                    self.write_tag_directive(handle_text, prefix_text)
            implicit = (first and not self.event.explicit and not self.canonical
                    and not self.event.version and not self.event.tags
                    and not self.check_empty_document())
            if not implicit:
                self.write_indent()
                self.write_indicator(u'---', True)
                if self.canonical:
                    self.write_indent()
            self.state = self.expect_document_root
        elif isinstance(self.event, StreamEndEvent):
            self.write_stream_end()
            self.state = self.expect_nothing
        else:
            raise EmitterError("expected DocumentStartEvent, but got %s"
                    % self.event)

    def expect_document_end(self):
        if isinstance(self.event, DocumentEndEvent):
            self.write_indent()
            if self.event.explicit:
                self.write_indicator(u'...', True)
                self.write_indent()
            self.flush_stream()
            self.state = self.expect_document_start
        else:
            raise EmitterError("expected DocumentEndEvent, but got %s"
                    % self.event)

    def expect_document_root(self):
        self.states.append(self.expect_document_end)
        self.expect_node(root=True)

    # Node handlers.

    def expect_node(self, root=False, sequence=False, mapping=False,
            simple_key=False):
        self.root_context = root
        self.sequence_context = sequence
        self.mapping_context = mapping
        self.simple_key_context = simple_key
        if isinstance(self.event, AliasEvent):
            self.expect_alias()
        elif isinstance(self.event, (ScalarEvent, CollectionStartEvent)):
            self.process_anchor(u'&')
            self.process_tag()
            if isinstance(self.event, ScalarEvent):
                self.expect_scalar()
            elif isinstance(self.event, SequenceStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_sequence():
                    self.expect_flow_sequence()
                else:
                    self.expect_block_sequence()
            elif isinstance(self.event, MappingStartEvent):
                if self.flow_level or self.canonical or self.event.flow_style   \
                        or self.check_empty_mapping():
                    self.expect_flow_mapping()
                else:
                    self.expect_block_mapping()
        else:
            raise EmitterError("expected NodeEvent, but got %s" % self.event)

    def expect_alias(self):
        if self.event.anchor is None:
            raise EmitterError("anchor is not specified for alias")
        self.process_anchor(u'*')
        self.state = self.states.pop()

    def expect_scalar(self):
        self.increase_indent(flow=True)
        self.process_scalar()
        self.indent = self.indents.pop()
        self.state = self.states.pop()

    # Flow sequence handlers.

    def expect_flow_sequence(self):
        self.write_indicator(u'[', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_sequence_item

    def expect_first_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(u']', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    def expect_flow_sequence_item(self):
        if isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(u',', False)
                self.write_indent()
            self.write_indicator(u']', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(u',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            self.states.append(self.expect_flow_sequence_item)
            self.expect_node(sequence=True)

    # Flow mapping handlers.

    def expect_flow_mapping(self):
        self.write_indicator(u'{', True, whitespace=True)
        self.flow_level += 1
        self.increase_indent(flow=True)
        self.state = self.expect_first_flow_mapping_key

    def expect_first_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            self.write_indicator(u'}', False)
            self.state = self.states.pop()
        else:
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_key(self):
        if isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.flow_level -= 1
            if self.canonical:
                self.write_indicator(u',', False)
                self.write_indent()
            self.write_indicator(u'}', False)
            self.state = self.states.pop()
        else:
            self.write_indicator(u',', False)
            if self.canonical or self.column > self.best_width:
                self.write_indent()
            if not self.canonical and self.check_simple_key():
                self.states.append(self.expect_flow_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True)
                self.states.append(self.expect_flow_mapping_value)
                self.expect_node(mapping=True)

    def expect_flow_mapping_simple_value(self):
        self.write_indicator(u':', False)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    def expect_flow_mapping_value(self):
        if self.canonical or self.column > self.best_width:
            self.write_indent()
        self.write_indicator(u':', True)
        self.states.append(self.expect_flow_mapping_key)
        self.expect_node(mapping=True)

    # Block sequence handlers.

    def expect_block_sequence(self):
        indentless = (self.mapping_context and not self.indention)
        self.increase_indent(flow=False, indentless=indentless)
        self.state = self.expect_first_block_sequence_item

    def expect_first_block_sequence_item(self):
        return self.expect_block_sequence_item(first=True)

    def expect_block_sequence_item(self, first=False):
        if not first and isinstance(self.event, SequenceEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            self.write_indicator(u'-', True, indention=True)
            self.states.append(self.expect_block_sequence_item)
            self.expect_node(sequence=True)

    # Block mapping handlers.

    def expect_block_mapping(self):
        self.increase_indent(flow=False)
        self.state = self.expect_first_block_mapping_key

    def expect_first_block_mapping_key(self):
        return self.expect_block_mapping_key(first=True)

    def expect_block_mapping_key(self, first=False):
        if not first and isinstance(self.event, MappingEndEvent):
            self.indent = self.indents.pop()
            self.state = self.states.pop()
        else:
            self.write_indent()
            if self.check_simple_key():
                self.states.append(self.expect_block_mapping_simple_value)
                self.expect_node(mapping=True, simple_key=True)
            else:
                self.write_indicator(u'?', True, indention=True)
                self.states.append(self.expect_block_mapping_value)
                self.expect_node(mapping=True)

    def expect_block_mapping_simple_value(self):
        self.write_indicator(u':', False)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    def expect_block_mapping_value(self):
        self.write_indent()
        self.write_indicator(u':', True, indention=True)
        self.states.append(self.expect_block_mapping_key)
        self.expect_node(mapping=True)

    # Checkers.

    def check_empty_sequence(self):
        return (isinstance(self.event, SequenceStartEvent) and self.events
                and isinstance(self.events[0], SequenceEndEvent))

    def check_empty_mapping(self):
        return (isinstance(self.event, MappingStartEvent) and self.events
                and isinstance(self.events[0], MappingEndEvent))

    def check_empty_document(self):
        if not isinstance(self.event, DocumentStartEvent) or not self.events:
            return False
        event = self.events[0]
        return (isinstance(event, ScalarEvent) and event.anchor is None
                and event.tag is None and event.implicit and event.value == u'')

    def check_simple_key(self):
        length = 0
        if isinstance(self.event, NodeEvent) and self.event.anchor is not None:
            if self.prepared_anchor is None:
                self.prepared_anchor = self.prepare_anchor(self.event.anchor)
            length += len(self.prepared_anchor)
        if isinstance(self.event, (ScalarEvent, CollectionStartEvent))  \
                and self.event.tag is not None:
            if self.prepared_tag is None:
                self.prepared_tag = self.prepare_tag(self.event.tag)
            length += len(self.prepared_tag)
        if isinstance(self.event, ScalarEvent):
            if self.analysis is None:
                self.analysis = self.analyze_scalar(self.event.value)
            length += len(self.analysis.scalar)
        return (length < 128 and (isinstance(self.event, AliasEvent)
            or (isinstance(self.event, ScalarEvent)
                    and not self.analysis.empty and not self.analysis.multiline)
            or self.check_empty_sequence() or self.check_empty_mapping()))

    # Anchor, Tag, and Scalar processors.

    def process_anchor(self, indicator):
        if self.event.anchor is None:
            self.prepared_anchor = None
            return
        if self.prepared_anchor is None:
            self.prepared_anchor = self.prepare_anchor(self.event.anchor)
        if self.prepared_anchor:
            self.write_indicator(indicator+self.prepared_anchor, True)
        self.prepared_anchor = None

    def process_tag(self):
        tag = self.event.tag
        if isinstance(self.event, ScalarEvent):
            if self.style is None:
                self.style = self.choose_scalar_style()
            if ((not self.canonical or tag is None) and
                ((self.style == '' and self.event.implicit[0])
                        or (self.style != '' and self.event.implicit[1]))):
                self.prepared_tag = None
                return
            if self.event.implicit[0] and tag is None:
                tag = u'!'
                self.prepared_tag = None
        else:
            if (not self.canonical or tag is None) and self.event.implicit:
                self.prepared_tag = None
                return
        if tag is None:
            raise EmitterError("tag is not specified")
        if self.prepared_tag is None:
            self.prepared_tag = self.prepare_tag(tag)
        if self.prepared_tag:
            self.write_indicator(self.prepared_tag, True)
        self.prepared_tag = None

    def choose_scalar_style(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.event.style == '"' or self.canonical:
            return '"'
        if not self.event.style and self.event.implicit[0]:
            if (not (self.simple_key_context and
                    (self.analysis.empty or self.analysis.multiline))
                and (self.flow_level and self.analysis.allow_flow_plain
                    or (not self.flow_level and self.analysis.allow_block_plain))):
                return ''
        if self.event.style and self.event.style in '|>':
            if (not self.flow_level and not self.simple_key_context
                    and self.analysis.allow_block):
                return self.event.style
        if not self.event.style or self.event.style == '\'':
            if (self.analysis.allow_single_quoted and
                    not (self.simple_key_context and self.analysis.multiline)):
                return '\''
        return '"'

    def process_scalar(self):
        if self.analysis is None:
            self.analysis = self.analyze_scalar(self.event.value)
        if self.style is None:
            self.style = self.choose_scalar_style()
        split = (not self.simple_key_context)
        #if self.analysis.multiline and split    \
        #        and (not self.style or self.style in '\'\"'):
        #    self.write_indent()
        if self.style == '"':
            self.write_double_quoted(self.analysis.scalar, split)
        elif self.style == '\'':
            self.write_single_quoted(self.analysis.scalar, split)
        elif self.style == '>':
            self.write_folded(self.analysis.scalar)
        elif self.style == '|':
            self.write_literal(self.analysis.scalar)
        else:
            self.write_plain(self.analysis.scalar, split)
        self.analysis = None
        self.style = None

    # Analyzers.

    def prepare_version(self, version):
        major, minor = version
        if major != 1:
            raise EmitterError("unsupported YAML version: %d.%d" % (major, minor))
        return u'%d.%d' % (major, minor)

    def prepare_tag_handle(self, handle):
        if not handle:
            raise EmitterError("tag handle must not be empty")
        if handle[0] != u'!' or handle[-1] != u'!':
            raise EmitterError("tag handle must start and end with '!': %r"
                    % (handle.encode('utf-8')))
        for ch in handle[1:-1]:
            if not (u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'    \
                    or ch in u'-_'):
                raise EmitterError("invalid character %r in the tag handle: %r"
                        % (ch.encode('utf-8'), handle.encode('utf-8')))
        return handle

    def prepare_tag_prefix(self, prefix):
        if not prefix:
            raise EmitterError("tag prefix must not be empty")
        chunks = []
        start = end = 0
        if prefix[0] == u'!':
            end = 1
        while end < len(prefix):
            ch = prefix[end]
            if u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'  \
                    or ch in u'-;/?!:@&=+$,_.~*\'()[]':
                end += 1
            else:
                if start < end:
                    chunks.append(prefix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append(u'%%%02X' % ord(ch))
        if start < end:
            chunks.append(prefix[start:end])
        return u''.join(chunks)

    def prepare_tag(self, tag):
        if not tag:
            raise EmitterError("tag must not be empty")
        if tag == u'!':
            return tag
        handle = None
        suffix = tag
        for prefix in self.tag_prefixes:
            if tag.startswith(prefix)   \
                    and (prefix == u'!' or len(prefix) < len(tag)):
                handle = self.tag_prefixes[prefix]
                suffix = tag[len(prefix):]
        chunks = []
        start = end = 0
        while end < len(suffix):
            ch = suffix[end]
            if u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'  \
                    or ch in u'-;/?:@&=+$,_.~*\'()[]'   \
                    or (ch == u'!' and handle != u'!'):
                end += 1
            else:
                if start < end:
                    chunks.append(suffix[start:end])
                start = end = end+1
                data = ch.encode('utf-8')
                for ch in data:
                    chunks.append(u'%%%02X' % ord(ch))
        if start < end:
            chunks.append(suffix[start:end])
        suffix_text = u''.join(chunks)
        if handle:
            return u'%s%s' % (handle, suffix_text)
        else:
            return u'!<%s>' % suffix_text

    def prepare_anchor(self, anchor):
        if not anchor:
            raise EmitterError("anchor must not be empty")
        for ch in anchor:
            if not (u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'    \
                    or ch in u'-_'):
                raise EmitterError("invalid character %r in the anchor: %r"
                        % (ch.encode('utf-8'), anchor.encode('utf-8')))
        return anchor

    def analyze_scalar(self, scalar):

        # Empty scalar is a special case.
        if not scalar:
            return ScalarAnalysis(scalar=scalar, empty=True, multiline=False,
                    allow_flow_plain=False, allow_block_plain=True,
                    allow_single_quoted=True, allow_double_quoted=True,
                    allow_block=False)

        # Indicators and special characters.
        block_indicators = False
        flow_indicators = False
        line_breaks = False
        special_characters = False

        # Whitespaces.
        inline_spaces = False          # non-space space+ non-space
        inline_breaks = False          # non-space break+ non-space
        leading_spaces = False         # ^ space+ (non-space | $)
        leading_breaks = False         # ^ break+ (non-space | $)
        trailing_spaces = False        # (^ | non-space) space+ $
        trailing_breaks = False        # (^ | non-space) break+ $
        inline_breaks_spaces = False   # non-space break+ space+ non-space
        mixed_breaks_spaces = False    # anything else

        # Check document indicators.
        if scalar.startswith(u'---') or scalar.startswith(u'...'):
            block_indicators = True
            flow_indicators = True

        # First character or preceded by a whitespace.
        preceeded_by_space = True

        # Last character or followed by a whitespace.
        followed_by_space = (len(scalar) == 1 or
                scalar[1] in u'\0 \t\r\n\x85\u2028\u2029')

        # The current series of whitespaces contain plain spaces.
        spaces = False

        # The current series of whitespaces contain line breaks.
        breaks = False

        # The current series of whitespaces contain a space followed by a
        # break.
        mixed = False

        # The current series of whitespaces start at the beginning of the
        # scalar.
        leading = False

        index = 0
        while index < len(scalar):
            ch = scalar[index]

            # Check for indicators.

            if index == 0:
                # Leading indicators are special characters.
                if ch in u'#,[]{}&*!|>\'\"%@`': 
                    flow_indicators = True
                    block_indicators = True
                if ch in u'?:':
                    flow_indicators = True
                    if followed_by_space:
                        block_indicators = True
                if ch == u'-' and followed_by_space:
                    flow_indicators = True
                    block_indicators = True
            else:
                # Some indicators cannot appear within a scalar as well.
                if ch in u',?[]{}':
                    flow_indicators = True
                if ch == u':':
                    flow_indicators = True
                    if followed_by_space:
                        block_indicators = True
                if ch == u'#' and preceeded_by_space:
                    flow_indicators = True
                    block_indicators = True

            # Check for line breaks, special, and unicode characters.

            if ch in u'\n\x85\u2028\u2029':
                line_breaks = True
            if not (ch == u'\n' or u'\x20' <= ch <= u'\x7E'):
                if (ch == u'\x85' or u'\xA0' <= ch <= u'\uD7FF'
                        or u'\uE000' <= ch <= u'\uFFFD') and ch != u'\uFEFF':
                    unicode_characters = True
                    if not self.allow_unicode:
                        special_characters = True
                else:
                    special_characters = True

            # Spaces, line breaks, and how they are mixed. State machine.

            # Start or continue series of whitespaces.
            if ch in u' \n\x85\u2028\u2029':
                if spaces and breaks:
                    if ch != u' ':      # break+ (space+ break+)    => mixed
                        mixed = True
                elif spaces:
                    if ch != u' ':      # (space+ break+)   => mixed
                        breaks = True
                        mixed = True
                elif breaks:
                    if ch == u' ':      # break+ space+
                        spaces = True
                else:
                    leading = (index == 0)
                    if ch == u' ':      # space+
                        spaces = True
                    else:               # break+
                        breaks = True

            # Series of whitespaces ended with a non-space.
            elif spaces or breaks:
                if leading:
                    if spaces and breaks:
                        mixed_breaks_spaces = True
                    elif spaces:
                        leading_spaces = True
                    elif breaks:
                        leading_breaks = True
                else:
                    if mixed:
                        mixed_breaks_spaces = True
                    elif spaces and breaks:
                        inline_breaks_spaces = True
                    elif spaces:
                        inline_spaces = True
                    elif breaks:
                        inline_breaks = True
                spaces = breaks = mixed = leading = False

            # Series of whitespaces reach the end.
            if (spaces or breaks) and (index == len(scalar)-1):
                if spaces and breaks:
                    mixed_breaks_spaces = True
                elif spaces:
                    trailing_spaces = True
                    if leading:
                        leading_spaces = True
                elif breaks:
                    trailing_breaks = True
                    if leading:
                        leading_breaks = True
                spaces = breaks = mixed = leading = False

            # Prepare for the next character.
            index += 1
            preceeded_by_space = (ch in u'\0 \t\r\n\x85\u2028\u2029')
            followed_by_space = (index+1 >= len(scalar) or
                    scalar[index+1] in u'\0 \t\r\n\x85\u2028\u2029')

        # Let's decide what styles are allowed.
        allow_flow_plain = True
        allow_block_plain = True
        allow_single_quoted = True
        allow_double_quoted = True
        allow_block = True

        # Leading and trailing whitespace are bad for plain scalars. We also
        # do not want to mess with leading whitespaces for block scalars.
        if leading_spaces or leading_breaks or trailing_spaces:
            allow_flow_plain = allow_block_plain = allow_block = False

        # Trailing breaks are fine for block scalars, but unacceptable for
        # plain scalars.
        if trailing_breaks:
            allow_flow_plain = allow_block_plain = False

        # The combination of (space+ break+) is only acceptable for block
        # scalars.
        if inline_breaks_spaces:
            allow_flow_plain = allow_block_plain = allow_single_quoted = False

        # Mixed spaces and breaks, as well as special character are only
        # allowed for double quoted scalars.
        if mixed_breaks_spaces or special_characters:
            allow_flow_plain = allow_block_plain =  \
            allow_single_quoted = allow_block = False

        # We don't emit multiline plain scalars.
        if line_breaks:
            allow_flow_plain = allow_block_plain = False

        # Flow indicators are forbidden for flow plain scalars.
        if flow_indicators:
            allow_flow_plain = False

        # Block indicators are forbidden for block plain scalars.
        if block_indicators:
            allow_block_plain = False

        return ScalarAnalysis(scalar=scalar,
                empty=False, multiline=line_breaks,
                allow_flow_plain=allow_flow_plain,
                allow_block_plain=allow_block_plain,
                allow_single_quoted=allow_single_quoted,
                allow_double_quoted=allow_double_quoted,
                allow_block=allow_block)

    # Writers.

    def flush_stream(self):
        if hasattr(self.stream, 'flush'):
            self.stream.flush()

    def write_stream_start(self):
        # Write BOM if needed.
        if self.encoding and self.encoding.startswith('utf-16'):
            self.stream.write(u'\xFF\xFE'.encode(self.encoding))

    def write_stream_end(self):
        self.flush_stream()

    def write_indicator(self, indicator, need_whitespace,
            whitespace=False, indention=False):
        if self.whitespace or not need_whitespace:
            data = indicator
        else:
            data = u' '+indicator
        self.whitespace = whitespace
        self.indention = self.indention and indention
        self.column += len(data)
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_indent(self):
        indent = self.indent or 0
        if not self.indention or self.column > indent   \
                or (self.column == indent and not self.whitespace):
            self.write_line_break()
        if self.column < indent:
            self.whitespace = True
            data = u' '*(indent-self.column)
            self.column = indent
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)

    def write_line_break(self, data=None):
        if data is None:
            data = self.best_line_break
        self.whitespace = True
        self.indention = True
        self.line += 1
        self.column = 0
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)

    def write_version_directive(self, version_text):
        data = u'%%YAML %s' % version_text
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    def write_tag_directive(self, handle_text, prefix_text):
        data = u'%%TAG %s %s' % (handle_text, prefix_text)
        if self.encoding:
            data = data.encode(self.encoding)
        self.stream.write(data)
        self.write_line_break()

    # Scalar streams.

    def write_single_quoted(self, text, split=True):
        self.write_indicator(u'\'', True)
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch is None or ch != u' ':
                    if start+1 == end and self.column > self.best_width and split   \
                            and start != 0 and end != len(text):
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    if text[start] == u'\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029' or ch == u'\'':
                    if start < end:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                        start = end
            if ch == u'\'':
                data = u'\'\''
                self.column += 2
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                start = end + 1
            if ch is not None:
                spaces = (ch == u' ')
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1
        self.write_indicator(u'\'', False)

    ESCAPE_REPLACEMENTS = {
        u'\0':      u'0',
        u'\x07':    u'a',
        u'\x08':    u'b',
        u'\x09':    u't',
        u'\x0A':    u'n',
        u'\x0B':    u'v',
        u'\x0C':    u'f',
        u'\x0D':    u'r',
        u'\x1B':    u'e',
        u'\"':      u'\"',
        u'\\':      u'\\',
        u'\x85':    u'N',
        u'\xA0':    u'_',
        u'\u2028':  u'L',
        u'\u2029':  u'P',
    }

    def write_double_quoted(self, text, split=True):
        self.write_indicator(u'"', True)
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if ch is None or ch in u'"\\\x85\u2028\u2029\uFEFF' \
                    or not (u'\x20' <= ch <= u'\x7E'
                        or (self.allow_unicode
                            and (u'\xA0' <= ch <= u'\uD7FF'
                                or u'\uE000' <= ch <= u'\uFFFD'))):
                if start < end:
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
                if ch is not None:
                    if ch in self.ESCAPE_REPLACEMENTS:
                        data = u'\\'+self.ESCAPE_REPLACEMENTS[ch]
                    elif ch <= u'\xFF':
                        data = u'\\x%02X' % ord(ch)
                    elif ch <= u'\uFFFF':
                        data = u'\\u%04X' % ord(ch)
                    else:
                        data = u'\\U%08X' % ord(ch)
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end+1
            if 0 < end < len(text)-1 and (ch == u' ' or start >= end)   \
                    and self.column+(end-start) > self.best_width and split:
                data = text[start:end]+u'\\'
                if start < end:
                    start = end
                self.column += len(data)
                if self.encoding:
                    data = data.encode(self.encoding)
                self.stream.write(data)
                self.write_indent()
                self.whitespace = False
                self.indention = False
                if text[start] == u' ':
                    data = u'\\'
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
            end += 1
        self.write_indicator(u'"', False)

    def determine_chomp(self, text):
        tail = text[-2:]
        while len(tail) < 2:
            tail = u' '+tail
        if tail[-1] in u'\n\x85\u2028\u2029':
            if tail[-2] in u'\n\x85\u2028\u2029':
                return u'+'
            else:
                return u''
        else:
            return u'-'

    def write_folded(self, text):
        chomp = self.determine_chomp(text)
        self.write_indicator(u'>'+chomp, True)
        self.write_indent()
        leading_space = False
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    if not leading_space and ch is not None and ch != u' '  \
                            and text[start] == u'\n':
                        self.write_line_break()
                    leading_space = (ch == u' ')
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            elif spaces:
                if ch != u' ':
                    if start+1 == end and self.column > self.best_width:
                        self.write_indent()
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029':
                    data = text[start:end]
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in u'\n\x85\u2028\u2029')
                spaces = (ch == u' ')
            end += 1

    def write_literal(self, text):
        chomp = self.determine_chomp(text)
        self.write_indicator(u'|'+chomp, True)
        self.write_indent()
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if breaks:
                if ch is None or ch not in u'\n\x85\u2028\u2029':
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    if ch is not None:
                        self.write_indent()
                    start = end
            else:
                if ch is None or ch in u'\n\x85\u2028\u2029':
                    data = text[start:end]
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    if ch is None:
                        self.write_line_break()
                    start = end
            if ch is not None:
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1

    def write_plain(self, text, split=True):
        if not text:
            return
        if not self.whitespace:
            data = u' '
            self.column += len(data)
            if self.encoding:
                data = data.encode(self.encoding)
            self.stream.write(data)
        self.writespace = False
        self.indention = False
        spaces = False
        breaks = False
        start = end = 0
        while end <= len(text):
            ch = None
            if end < len(text):
                ch = text[end]
            if spaces:
                if ch != u' ':
                    if start+1 == end and self.column > self.best_width and split:
                        self.write_indent()
                        self.writespace = False
                        self.indention = False
                    else:
                        data = text[start:end]
                        self.column += len(data)
                        if self.encoding:
                            data = data.encode(self.encoding)
                        self.stream.write(data)
                    start = end
            elif breaks:
                if ch not in u'\n\x85\u2028\u2029':
                    if text[start] == u'\n':
                        self.write_line_break()
                    for br in text[start:end]:
                        if br == u'\n':
                            self.write_line_break()
                        else:
                            self.write_line_break(br)
                    self.write_indent()
                    self.whitespace = False
                    self.indention = False
                    start = end
            else:
                if ch is None or ch in u' \n\x85\u2028\u2029':
                    data = text[start:end]
                    self.column += len(data)
                    if self.encoding:
                        data = data.encode(self.encoding)
                    self.stream.write(data)
                    start = end
            if ch is not None:
                spaces = (ch == u' ')
                breaks = (ch in u'\n\x85\u2028\u2029')
            end += 1


########NEW FILE########
__FILENAME__ = error

__all__ = ['Mark', 'YAMLError', 'MarkedYAMLError']

class Mark(object):

    def __init__(self, name, index, line, column, buffer, pointer):
        self.name = name
        self.index = index
        self.line = line
        self.column = column
        self.buffer = buffer
        self.pointer = pointer

    def get_snippet(self, indent=4, max_length=75):
        if self.buffer is None:
            return None
        head = ''
        start = self.pointer
        while start > 0 and self.buffer[start-1] not in u'\0\r\n\x85\u2028\u2029':
            start -= 1
            if self.pointer-start > max_length/2-1:
                head = ' ... '
                start += 5
                break
        tail = ''
        end = self.pointer
        while end < len(self.buffer) and self.buffer[end] not in u'\0\r\n\x85\u2028\u2029':
            end += 1
            if end-self.pointer > max_length/2-1:
                tail = ' ... '
                end -= 5
                break
        snippet = self.buffer[start:end].encode('utf-8')
        return ' '*indent + head + snippet + tail + '\n'  \
                + ' '*(indent+self.pointer-start+len(head)) + '^'

    def __str__(self):
        snippet = self.get_snippet()
        where = "  in \"%s\", line %d, column %d"   \
                % (self.name, self.line+1, self.column+1)
        if snippet is not None:
            where += ":\n"+snippet
        return where

class YAMLError(Exception):
    pass

class MarkedYAMLError(YAMLError):

    def __init__(self, context=None, context_mark=None,
            problem=None, problem_mark=None, note=None):
        self.context = context
        self.context_mark = context_mark
        self.problem = problem
        self.problem_mark = problem_mark
        self.note = note

    def __str__(self):
        lines = []
        if self.context is not None:
            lines.append(self.context)
        if self.context_mark is not None  \
            and (self.problem is None or self.problem_mark is None
                    or self.context_mark.name != self.problem_mark.name
                    or self.context_mark.line != self.problem_mark.line
                    or self.context_mark.column != self.problem_mark.column):
            lines.append(str(self.context_mark))
        if self.problem is not None:
            lines.append(self.problem)
        if self.problem_mark is not None:
            lines.append(str(self.problem_mark))
        if self.note is not None:
            lines.append(self.note)
        return '\n'.join(lines)


########NEW FILE########
__FILENAME__ = events

# Abstract classes.

class Event(object):
    def __init__(self, start_mark=None, end_mark=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in ['anchor', 'tag', 'implicit', 'value']
                if hasattr(self, key)]
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

class NodeEvent(Event):
    def __init__(self, anchor, start_mark=None, end_mark=None):
        self.anchor = anchor
        self.start_mark = start_mark
        self.end_mark = end_mark

class CollectionStartEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, start_mark=None, end_mark=None,
            flow_style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class CollectionEndEvent(Event):
    pass

# Implementations.

class StreamStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None, encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndEvent(Event):
    pass

class DocumentStartEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None, version=None, tags=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit
        self.version = version
        self.tags = tags

class DocumentEndEvent(Event):
    def __init__(self, start_mark=None, end_mark=None,
            explicit=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.explicit = explicit

class AliasEvent(NodeEvent):
    pass

class ScalarEvent(NodeEvent):
    def __init__(self, anchor, tag, implicit, value,
            start_mark=None, end_mark=None, style=None):
        self.anchor = anchor
        self.tag = tag
        self.implicit = implicit
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class SequenceStartEvent(CollectionStartEvent):
    pass

class SequenceEndEvent(CollectionEndEvent):
    pass

class MappingStartEvent(CollectionStartEvent):
    pass

class MappingEndEvent(CollectionEndEvent):
    pass


########NEW FILE########
__FILENAME__ = loader

__all__ = ['BaseLoader', 'SafeLoader', 'Loader']

from reader import *
from scanner import *
from parser import *
from composer import *
from constructor import *
from resolver import *

class BaseLoader(Reader, Scanner, Parser, Composer, BaseConstructor, BaseResolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        BaseConstructor.__init__(self)
        BaseResolver.__init__(self)

class SafeLoader(Reader, Scanner, Parser, Composer, SafeConstructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

class Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver):

    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        Constructor.__init__(self)
        Resolver.__init__(self)


########NEW FILE########
__FILENAME__ = nodes

class Node(object):
    def __init__(self, tag, value, start_mark, end_mark):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        value = self.value
        #if isinstance(value, list):
        #    if len(value) == 0:
        #        value = '<empty>'
        #    elif len(value) == 1:
        #        value = '<1 item>'
        #    else:
        #        value = '<%d items>' % len(value)
        #else:
        #    if len(value) > 75:
        #        value = repr(value[:70]+u' ... ')
        #    else:
        #        value = repr(value)
        value = repr(value)
        return '%s(tag=%r, value=%s)' % (self.__class__.__name__, self.tag, value)

class ScalarNode(Node):
    id = 'scalar'
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style

class CollectionNode(Node):
    def __init__(self, tag, value,
            start_mark=None, end_mark=None, flow_style=None):
        self.tag = tag
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.flow_style = flow_style

class SequenceNode(CollectionNode):
    id = 'sequence'

class MappingNode(CollectionNode):
    id = 'mapping'


########NEW FILE########
__FILENAME__ = parser

# The following YAML grammar is LL(1) and is parsed by a recursive descent
# parser.
#
# stream            ::= STREAM-START implicit_document? explicit_document* STREAM-END
# implicit_document ::= block_node DOCUMENT-END*
# explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*
# block_node_or_indentless_sequence ::=
#                       ALIAS
#                       | properties (block_content | indentless_block_sequence)?
#                       | block_content
#                       | indentless_block_sequence
# block_node        ::= ALIAS
#                       | properties block_content?
#                       | block_content
# flow_node         ::= ALIAS
#                       | properties flow_content?
#                       | flow_content
# properties        ::= TAG ANCHOR? | ANCHOR TAG?
# block_content     ::= block_collection | flow_collection | SCALAR
# flow_content      ::= flow_collection | SCALAR
# block_collection  ::= block_sequence | block_mapping
# flow_collection   ::= flow_sequence | flow_mapping
# block_sequence    ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END
# indentless_sequence   ::= (BLOCK-ENTRY block_node?)+
# block_mapping     ::= BLOCK-MAPPING_START
#                       ((KEY block_node_or_indentless_sequence?)?
#                       (VALUE block_node_or_indentless_sequence?)?)*
#                       BLOCK-END
# flow_sequence     ::= FLOW-SEQUENCE-START
#                       (flow_sequence_entry FLOW-ENTRY)*
#                       flow_sequence_entry?
#                       FLOW-SEQUENCE-END
# flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
# flow_mapping      ::= FLOW-MAPPING-START
#                       (flow_mapping_entry FLOW-ENTRY)*
#                       flow_mapping_entry?
#                       FLOW-MAPPING-END
# flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?
#
# FIRST sets:
#
# stream: { STREAM-START }
# explicit_document: { DIRECTIVE DOCUMENT-START }
# implicit_document: FIRST(block_node)
# block_node: { ALIAS TAG ANCHOR SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_node: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_content: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# flow_content: { FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# block_collection: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_sequence: { BLOCK-SEQUENCE-START }
# block_mapping: { BLOCK-MAPPING-START }
# block_node_or_indentless_sequence: { ALIAS ANCHOR TAG SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START BLOCK-ENTRY }
# indentless_sequence: { ENTRY }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_sequence: { FLOW-SEQUENCE-START }
# flow_mapping: { FLOW-MAPPING-START }
# flow_sequence_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }
# flow_mapping_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }

__all__ = ['Parser', 'ParserError']

from error import MarkedYAMLError
from tokens import *
from events import *
from scanner import *

class ParserError(MarkedYAMLError):
    pass

class Parser(object):
    # Since writing a recursive-descendant parser is a straightforward task, we
    # do not give many comments here.
    # Note that we use Python generators. If you rewrite the parser in another
    # language, you may replace all 'yield'-s with event handler calls.

    DEFAULT_TAGS = {
        u'!':   u'!',
        u'!!':  u'tag:yaml.org,2002:',
    }

    def __init__(self):
        self.current_event = None
        self.yaml_version = None
        self.tag_handles = {}
        self.states = []
        self.marks = []
        self.state = self.parse_stream_start

    def check_event(self, *choices):
        # Check the type of the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        if self.current_event is not None:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.current_event, choice):
                    return True
        return False

    def peek_event(self):
        # Get the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        return self.current_event

    def get_event(self):
        # Get the next event and proceed further.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        value = self.current_event
        self.current_event = None
        return value

    # stream    ::= STREAM-START implicit_document? explicit_document* STREAM-END
    # implicit_document ::= block_node DOCUMENT-END*
    # explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*

    def parse_stream_start(self):

        # Parse the stream start.
        token = self.get_token()
        event = StreamStartEvent(token.start_mark, token.end_mark,
                encoding=token.encoding)

        # Prepare the next state.
        self.state = self.parse_implicit_document_start

        return event

    def parse_implicit_document_start(self):

        # Parse an implicit document.
        if not self.check_token(DirectiveToken, DocumentStartToken,
                StreamEndToken):
            self.tag_handles = self.DEFAULT_TAGS
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=False)

            # Prepare the next state.
            self.states.append(self.parse_document_end)
            self.state = self.parse_block_node

            return event

        else:
            return self.parse_document_start()

    def parse_document_start(self):

        # Parse any extra document end indicators.
        while self.check_token(DocumentEndToken):
            self.get_token()

        # Parse an explicit document.
        if not self.check_token(StreamEndToken):
            token = self.peek_token()
            start_mark = token.start_mark
            version, tags = self.process_directives()
            if not self.check_token(DocumentStartToken):
                raise ParserError(None, None,
                        "expected '<document start>', but found %r"
                        % self.peek_token().id,
                        self.peek_token().start_mark)
            token = self.get_token()
            end_mark = token.end_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=True, version=version, tags=tags)
            self.states.append(self.parse_document_end)
            self.state = self.parse_document_content
        else:
            # Parse the end of the stream.
            token = self.get_token()
            event = StreamEndEvent(token.start_mark, token.end_mark)
            assert not self.states
            assert not self.marks
            self.state = None
        return event

    def parse_document_end(self):

        # Parse the document end.
        token = self.peek_token()
        start_mark = end_mark = token.start_mark
        explicit = False
        if self.check_token(DocumentEndToken):
            token = self.get_token()
            end_mark = token.end_mark
            explicit = True
        event = DocumentEndEvent(start_mark, end_mark,
                explicit=explicit)

        # Prepare the next state.
        self.state = self.parse_document_start

        return event

    def parse_document_content(self):
        if self.check_token(DirectiveToken,
                DocumentStartToken, DocumentEndToken, StreamEndToken):
            event = self.process_empty_scalar(self.peek_token().start_mark)
            self.state = self.states.pop()
            return event
        else:
            return self.parse_block_node()

    def process_directives(self):
        self.yaml_version = None
        self.tag_handles = {}
        while self.check_token(DirectiveToken):
            token = self.get_token()
            if token.name == u'YAML':
                if self.yaml_version is not None:
                    raise ParserError(None, None,
                            "found duplicate YAML directive", token.start_mark)
                major, minor = token.value
                if major != 1:
                    raise ParserError(None, None,
                            "found incompatible YAML document (version 1.* is required)",
                            token.start_mark)
                self.yaml_version = token.value
            elif token.name == u'TAG':
                handle, prefix = token.value
                if handle in self.tag_handles:
                    raise ParserError(None, None,
                            "duplicate tag handle %r" % handle.encode('utf-8'),
                            token.start_mark)
                self.tag_handles[handle] = prefix
        if self.tag_handles:
            value = self.yaml_version, self.tag_handles.copy()
        else:
            value = self.yaml_version, None
        for key in self.DEFAULT_TAGS:
            if key not in self.tag_handles:
                self.tag_handles[key] = self.DEFAULT_TAGS[key]
        return value

    # block_node_or_indentless_sequence ::= ALIAS
    #               | properties (block_content | indentless_block_sequence)?
    #               | block_content
    #               | indentless_block_sequence
    # block_node    ::= ALIAS
    #                   | properties block_content?
    #                   | block_content
    # flow_node     ::= ALIAS
    #                   | properties flow_content?
    #                   | flow_content
    # properties    ::= TAG ANCHOR? | ANCHOR TAG?
    # block_content     ::= block_collection | flow_collection | SCALAR
    # flow_content      ::= flow_collection | SCALAR
    # block_collection  ::= block_sequence | block_mapping
    # flow_collection   ::= flow_sequence | flow_mapping

    def parse_block_node(self):
        return self.parse_node(block=True)

    def parse_flow_node(self):
        return self.parse_node()

    def parse_block_node_or_indentless_sequence(self):
        return self.parse_node(block=True, indentless_sequence=True)

    def parse_node(self, block=False, indentless_sequence=False):
        if self.check_token(AliasToken):
            token = self.get_token()
            event = AliasEvent(token.value, token.start_mark, token.end_mark)
            self.state = self.states.pop()
        else:
            anchor = None
            tag = None
            start_mark = end_mark = tag_mark = None
            if self.check_token(AnchorToken):
                token = self.get_token()
                start_mark = token.start_mark
                end_mark = token.end_mark
                anchor = token.value
                if self.check_token(TagToken):
                    token = self.get_token()
                    tag_mark = token.start_mark
                    end_mark = token.end_mark
                    tag = token.value
            elif self.check_token(TagToken):
                token = self.get_token()
                start_mark = tag_mark = token.start_mark
                end_mark = token.end_mark
                tag = token.value
                if self.check_token(AnchorToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    anchor = token.value
            if tag is not None:
                handle, suffix = tag
                if handle is not None:
                    if handle not in self.tag_handles:
                        raise ParserError("while parsing a node", start_mark,
                                "found undefined tag handle %r" % handle.encode('utf-8'),
                                tag_mark)
                    tag = self.tag_handles[handle]+suffix
                else:
                    tag = suffix
            #if tag == u'!':
            #    raise ParserError("while parsing a node", start_mark,
            #            "found non-specific tag '!'", tag_mark,
            #            "Please check 'http://pyyaml.org/wiki/YAMLNonSpecificTag' and share your opinion.")
            if start_mark is None:
                start_mark = end_mark = self.peek_token().start_mark
            event = None
            implicit = (tag is None or tag == u'!')
            if indentless_sequence and self.check_token(BlockEntryToken):
                end_mark = self.peek_token().end_mark
                event = SequenceStartEvent(anchor, tag, implicit,
                        start_mark, end_mark)
                self.state = self.parse_indentless_sequence_entry
            else:
                if self.check_token(ScalarToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    if (token.plain and tag is None) or tag == u'!':
                        implicit = (True, False)
                    elif tag is None:
                        implicit = (False, True)
                    else:
                        implicit = (False, False)
                    event = ScalarEvent(anchor, tag, implicit, token.value,
                            start_mark, end_mark, style=token.style)
                    self.state = self.states.pop()
                elif self.check_token(FlowSequenceStartToken):
                    end_mark = self.peek_token().end_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_sequence_first_entry
                elif self.check_token(FlowMappingStartToken):
                    end_mark = self.peek_token().end_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_mapping_first_key
                elif block and self.check_token(BlockSequenceStartToken):
                    end_mark = self.peek_token().start_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_sequence_first_entry
                elif block and self.check_token(BlockMappingStartToken):
                    end_mark = self.peek_token().start_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_mapping_first_key
                elif anchor is not None or tag is not None:
                    # Empty scalars are allowed even if a tag or an anchor is
                    # specified.
                    event = ScalarEvent(anchor, tag, (implicit, False), u'',
                            start_mark, end_mark)
                    self.state = self.states.pop()
                else:
                    if block:
                        node = 'block'
                    else:
                        node = 'flow'
                    token = self.peek_token()
                    raise ParserError("while parsing a %s node" % node, start_mark,
                            "expected the node content, but found %r" % token.id,
                            token.start_mark)
        return event

    # block_sequence ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END

    def parse_block_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_sequence_entry()

    def parse_block_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken, BlockEndToken):
                self.states.append(self.parse_block_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_block_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block collection", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    # indentless_sequence ::= (BLOCK-ENTRY block_node?)+

    def parse_indentless_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken,
                    KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_indentless_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_indentless_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        token = self.peek_token()
        event = SequenceEndEvent(token.start_mark, token.start_mark)
        self.state = self.states.pop()
        return event

    # block_mapping     ::= BLOCK-MAPPING_START
    #                       ((KEY block_node_or_indentless_sequence?)?
    #                       (VALUE block_node_or_indentless_sequence?)?)*
    #                       BLOCK-END

    def parse_block_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_mapping_key()

    def parse_block_mapping_key(self):
        if self.check_token(KeyToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_value)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_value
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block mapping", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_block_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_key)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_block_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    # flow_sequence     ::= FLOW-SEQUENCE-START
    #                       (flow_sequence_entry FLOW-ENTRY)*
    #                       flow_sequence_entry?
    #                       FLOW-SEQUENCE-END
    # flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
    #
    # Note that while production rules for both flow_sequence_entry and
    # flow_mapping_entry are equal, their interpretations are different.
    # For `flow_sequence_entry`, the part `KEY flow_node? (VALUE flow_node?)?`
    # generate an inline mapping (set syntax).

    def parse_flow_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_sequence_entry(first=True)

    def parse_flow_sequence_entry(self, first=False):
        if not self.check_token(FlowSequenceEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow sequence", self.marks[-1],
                            "expected ',' or ']', but got %r" % token.id, token.start_mark)
            
            if self.check_token(KeyToken):
                token = self.peek_token()
                event = MappingStartEvent(None, None, True,
                        token.start_mark, token.end_mark,
                        flow_style=True)
                self.state = self.parse_flow_sequence_entry_mapping_key
                return event
            elif not self.check_token(FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry)
                return self.parse_flow_node()
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_sequence_entry_mapping_key(self):
        token = self.get_token()
        if not self.check_token(ValueToken,
                FlowEntryToken, FlowSequenceEndToken):
            self.states.append(self.parse_flow_sequence_entry_mapping_value)
            return self.parse_flow_node()
        else:
            self.state = self.parse_flow_sequence_entry_mapping_value
            return self.process_empty_scalar(token.end_mark)

    def parse_flow_sequence_entry_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry_mapping_end)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_sequence_entry_mapping_end
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_sequence_entry_mapping_end
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_sequence_entry_mapping_end(self):
        self.state = self.parse_flow_sequence_entry
        token = self.peek_token()
        return MappingEndEvent(token.start_mark, token.start_mark)

    # flow_mapping  ::= FLOW-MAPPING-START
    #                   (flow_mapping_entry FLOW-ENTRY)*
    #                   flow_mapping_entry?
    #                   FLOW-MAPPING-END
    # flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?

    def parse_flow_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_mapping_key(first=True)

    def parse_flow_mapping_key(self, first=False):
        if not self.check_token(FlowMappingEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow mapping", self.marks[-1],
                            "expected ',' or '}', but got %r" % token.id, token.start_mark)
            if self.check_token(KeyToken):
                token = self.get_token()
                if not self.check_token(ValueToken,
                        FlowEntryToken, FlowMappingEndToken):
                    self.states.append(self.parse_flow_mapping_value)
                    return self.parse_flow_node()
                else:
                    self.state = self.parse_flow_mapping_value
                    return self.process_empty_scalar(token.end_mark)
            elif not self.check_token(FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_empty_value)
                return self.parse_flow_node()
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_key)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_mapping_empty_value(self):
        self.state = self.parse_flow_mapping_key
        return self.process_empty_scalar(self.peek_token().start_mark)

    def process_empty_scalar(self, mark):
        return ScalarEvent(None, None, (True, False), u'', mark, mark)


########NEW FILE########
__FILENAME__ = reader
# This module contains abstractions for the input stream. You don't have to
# looks further, there are no pretty code.
#
# We define two classes here.
#
#   Mark(source, line, column)
# It's just a record and its only use is producing nice error messages.
# Parser does not use it for any other purposes.
#
#   Reader(source, data)
# Reader determines the encoding of `data` and converts it to unicode.
# Reader provides the following methods and attributes:
#   reader.peek(length=1) - return the next `length` characters
#   reader.forward(length=1) - move the current position to `length` characters.
#   reader.index - the number of the current character.
#   reader.line, stream.column - the line and the column of the current character.

__all__ = ['Reader', 'ReaderError']

from error import YAMLError, Mark

import codecs, re

# Unfortunately, codec functions in Python 2.3 does not support the `finish`
# arguments, so we have to write our own wrappers.

try:
    codecs.utf_8_decode('', 'strict', False)
    from codecs import utf_8_decode, utf_16_le_decode, utf_16_be_decode

except TypeError:

    def utf_16_le_decode(data, errors, finish=False):
        if not finish and len(data) % 2 == 1:
            data = data[:-1]
        return codecs.utf_16_le_decode(data, errors)

    def utf_16_be_decode(data, errors, finish=False):
        if not finish and len(data) % 2 == 1:
            data = data[:-1]
        return codecs.utf_16_be_decode(data, errors)

    def utf_8_decode(data, errors, finish=False):
        if not finish:
            # We are trying to remove a possible incomplete multibyte character
            # from the suffix of the data.
            # The first byte of a multi-byte sequence is in the range 0xc0 to 0xfd.
            # All further bytes are in the range 0x80 to 0xbf.
            # UTF-8 encoded UCS characters may be up to six bytes long.
            count = 0
            while count < 5 and count < len(data)   \
                    and '\x80' <= data[-count-1] <= '\xBF':
                count -= 1
            if count < 5 and count < len(data)  \
                    and '\xC0' <= data[-count-1] <= '\xFD':
                data = data[:-count-1]
        return codecs.utf_8_decode(data, errors)

class ReaderError(YAMLError):

    def __init__(self, name, position, character, encoding, reason):
        self.name = name
        self.character = character
        self.position = position
        self.encoding = encoding
        self.reason = reason

    def __str__(self):
        if isinstance(self.character, str):
            return "'%s' codec can't decode byte #x%02x: %s\n"  \
                    "  in \"%s\", position %d"    \
                    % (self.encoding, ord(self.character), self.reason,
                            self.name, self.position)
        else:
            return "unacceptable character #x%04x: %s\n"    \
                    "  in \"%s\", position %d"    \
                    % (ord(self.character), self.reason,
                            self.name, self.position)

class Reader(object):
    # Reader:
    # - determines the data encoding and converts it to unicode,
    # - checks if characters are in allowed range,
    # - adds '\0' to the end.

    # Reader accepts
    #  - a `str` object,
    #  - a `unicode` object,
    #  - a file-like object with its `read` method returning `str`,
    #  - a file-like object with its `read` method returning `unicode`.

    # Yeah, it's ugly and slow.

    def __init__(self, stream):
        self.name = None
        self.stream = None
        self.stream_pointer = 0
        self.eof = True
        self.buffer = u''
        self.pointer = 0
        self.raw_buffer = None
        self.raw_decode = None
        self.encoding = None
        self.index = 0
        self.line = 0
        self.column = 0
        if isinstance(stream, unicode):
            self.name = "<unicode string>"
            self.check_printable(stream)
            self.buffer = stream+u'\0'
        elif isinstance(stream, str):
            self.name = "<string>"
            self.raw_buffer = stream
            self.determine_encoding()
        else:
            self.stream = stream
            self.name = getattr(stream, 'name', "<file>")
            self.eof = False
            self.raw_buffer = ''
            self.determine_encoding()

    def peek(self, index=0):
        try:
            return self.buffer[self.pointer+index]
        except IndexError:
            self.update(index+1)
            return self.buffer[self.pointer+index]

    def prefix(self, length=1):
        if self.pointer+length >= len(self.buffer):
            self.update(length)
        return self.buffer[self.pointer:self.pointer+length]

    def forward(self, length=1):
        if self.pointer+length+1 >= len(self.buffer):
            self.update(length+1)
        while length:
            ch = self.buffer[self.pointer]
            self.pointer += 1
            self.index += 1
            if ch in u'\n\x85\u2028\u2029'  \
                    or (ch == u'\r' and self.buffer[self.pointer] != u'\n'):
                self.line += 1
                self.column = 0
            elif ch != u'\uFEFF':
                self.column += 1
            length -= 1

    def get_mark(self):
        if self.stream is None:
            return Mark(self.name, self.index, self.line, self.column,
                    self.buffer, self.pointer)
        else:
            return Mark(self.name, self.index, self.line, self.column,
                    None, None)

    def determine_encoding(self):
        while not self.eof and len(self.raw_buffer) < 2:
            self.update_raw()
        if not isinstance(self.raw_buffer, unicode):
            if self.raw_buffer.startswith(codecs.BOM_UTF16_LE):
                self.raw_decode = utf_16_le_decode
                self.encoding = 'utf-16-le'
            elif self.raw_buffer.startswith(codecs.BOM_UTF16_BE):
                self.raw_decode = utf_16_be_decode
                self.encoding = 'utf-16-be'
            else:
                self.raw_decode = utf_8_decode
                self.encoding = 'utf-8'
        self.update(1)

    NON_PRINTABLE = re.compile(u'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD]')
    def check_printable(self, data):
        match = self.NON_PRINTABLE.search(data)
        if match:
            character = match.group()
            position = self.index+(len(self.buffer)-self.pointer)+match.start()
            raise ReaderError(self.name, position, character,
                    'unicode', "special characters are not allowed")

    def update(self, length):
        if self.raw_buffer is None:
            return
        self.buffer = self.buffer[self.pointer:]
        self.pointer = 0
        while len(self.buffer) < length:
            if not self.eof:
                self.update_raw()
            if self.raw_decode is not None:
                try:
                    data, converted = self.raw_decode(self.raw_buffer,
                            'strict', self.eof)
                except UnicodeDecodeError, exc:
                    character = exc.object[exc.start]
                    if self.stream is not None:
                        position = self.stream_pointer-len(self.raw_buffer)+exc.start
                    else:
                        position = exc.start
                    raise ReaderError(self.name, position, character,
                            exc.encoding, exc.reason)
            else:
                data = self.raw_buffer
                converted = len(data)
            self.check_printable(data)
            self.buffer += data
            self.raw_buffer = self.raw_buffer[converted:]
            if self.eof:
                self.buffer += u'\0'
                self.raw_buffer = None
                break

    def update_raw(self, size=1024):
        data = self.stream.read(size)
        if data:
            self.raw_buffer += data
            self.stream_pointer += len(data)
        else:
            self.eof = True

#try:
#    import psyco
#    psyco.bind(Reader)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = representer

__all__ = ['BaseRepresenter', 'SafeRepresenter', 'Representer',
    'RepresenterError']

from error import *
from nodes import *

import datetime

try:
    set
except NameError:
    from sets import Set as set

import sys, copy_reg, types

class RepresenterError(YAMLError):
    pass

class BaseRepresenter(object):

    yaml_representers = {}
    yaml_multi_representers = {}

    def __init__(self, default_style=None, default_flow_style=None):
        self.default_style = default_style
        self.default_flow_style = default_flow_style
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def represent(self, data):
        node = self.represent_data(data)
        self.serialize(node)
        self.represented_objects = {}
        self.object_keeper = []
        self.alias_key = None

    def get_classobj_bases(self, cls):
        bases = [cls]
        for base in cls.__bases__:
            bases.extend(self.get_classobj_bases(base))
        return bases

    def represent_data(self, data):
        if self.ignore_aliases(data):
            self.alias_key = None
        else:
            self.alias_key = id(data)
        if self.alias_key is not None:
            if self.alias_key in self.represented_objects:
                node = self.represented_objects[self.alias_key]
                #if node is None:
                #    raise RepresenterError("recursive objects are not allowed: %r" % data)
                return node
            #self.represented_objects[alias_key] = None
            self.object_keeper.append(data)
        data_types = type(data).__mro__
        if type(data) is types.InstanceType:
            data_types = self.get_classobj_bases(data.__class__)+list(data_types)
        if data_types[0] in self.yaml_representers:
            node = self.yaml_representers[data_types[0]](self, data)
        else:
            for data_type in data_types:
                if data_type in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[data_type](self, data)
                    break
            else:
                if None in self.yaml_multi_representers:
                    node = self.yaml_multi_representers[None](self, data)
                elif None in self.yaml_representers:
                    node = self.yaml_representers[None](self, data)
                else:
                    node = ScalarNode(None, unicode(data))
        #if alias_key is not None:
        #    self.represented_objects[alias_key] = node
        return node

    def add_representer(cls, data_type, representer):
        if not 'yaml_representers' in cls.__dict__:
            cls.yaml_representers = cls.yaml_representers.copy()
        cls.yaml_representers[data_type] = representer
    add_representer = classmethod(add_representer)

    def add_multi_representer(cls, data_type, representer):
        if not 'yaml_multi_representers' in cls.__dict__:
            cls.yaml_multi_representers = cls.yaml_multi_representers.copy()
        cls.yaml_multi_representers[data_type] = representer
    add_multi_representer = classmethod(add_multi_representer)

    def represent_scalar(self, tag, value, style=None):
        if style is None:
            style = self.default_style
        node = ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node

    def represent_sequence(self, tag, sequence, flow_style=None):
        value = []
        node = SequenceNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        for item in sequence:
            node_item = self.represent_data(item)
            if not (isinstance(node_item, ScalarNode) and not node_item.style):
                best_style = False
            value.append(node_item)
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = mapping.items()
            mapping.sort()
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)
            if not (isinstance(node_key, ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node

    def ignore_aliases(self, data):
        return False

class SafeRepresenter(BaseRepresenter):

    def ignore_aliases(self, data):
        if data in [None, ()]:
            return True
        if isinstance(data, (str, unicode, bool, int, float)):
            return True

    def represent_none(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:null',
                u'null')

    def represent_str(self, data):
        tag = None
        style = None
        try:
            data = unicode(data, 'ascii')
            tag = u'tag:yaml.org,2002:str'
        except UnicodeDecodeError:
            try:
                data = unicode(data, 'utf-8')
                tag = u'tag:yaml.org,2002:str'
            except UnicodeDecodeError:
                data = data.encode('base64')
                tag = u'tag:yaml.org,2002:binary'
                style = '|'
        return self.represent_scalar(tag, data, style=style)

    def represent_unicode(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:str', data)

    def represent_bool(self, data):
        if data:
            value = u'true'
        else:
            value = u'false'
        return self.represent_scalar(u'tag:yaml.org,2002:bool', value)

    def represent_int(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:int', unicode(data))

    def represent_long(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:int', unicode(data))

    inf_value = 1e300
    while repr(inf_value) != repr(inf_value*inf_value):
        inf_value *= inf_value

    def represent_float(self, data):
        if data != data or (data == 0.0 and data == 1.0):
            value = u'.nan'
        elif data == self.inf_value:
            value = u'.inf'
        elif data == -self.inf_value:
            value = u'-.inf'
        else:
            value = unicode(repr(data)).lower()
            # Note that in some cases `repr(data)` represents a float number
            # without the decimal parts.  For instance:
            #   >>> repr(1e17)
            #   '1e17'
            # Unfortunately, this is not a valid float representation according
            # to the definition of the `!!float` tag.  We fix this by adding
            # '.0' before the 'e' symbol.
            if u'.' not in value and u'e' in value:
                value = value.replace(u'e', u'.0e', 1)
        return self.represent_scalar(u'tag:yaml.org,2002:float', value)

    def represent_list(self, data):
        #pairs = (len(data) > 0 and isinstance(data, list))
        #if pairs:
        #    for item in data:
        #        if not isinstance(item, tuple) or len(item) != 2:
        #            pairs = False
        #            break
        #if not pairs:
            return self.represent_sequence(u'tag:yaml.org,2002:seq', data)
        #value = []
        #for item_key, item_value in data:
        #    value.append(self.represent_mapping(u'tag:yaml.org,2002:map',
        #        [(item_key, item_value)]))
        #return SequenceNode(u'tag:yaml.org,2002:pairs', value)

    def represent_dict(self, data):
        return self.represent_mapping(u'tag:yaml.org,2002:map', data)

    def represent_set(self, data):
        value = {}
        for key in data:
            value[key] = None
        return self.represent_mapping(u'tag:yaml.org,2002:set', value)

    def represent_date(self, data):
        value = unicode(data.isoformat())
        return self.represent_scalar(u'tag:yaml.org,2002:timestamp', value)

    def represent_datetime(self, data):
        value = unicode(data.isoformat(' '))
        return self.represent_scalar(u'tag:yaml.org,2002:timestamp', value)

    def represent_yaml_object(self, tag, data, cls, flow_style=None):
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__.copy()
        return self.represent_mapping(tag, state, flow_style=flow_style)

    def represent_undefined(self, data):
        raise RepresenterError("cannot represent an object: %s" % data)

SafeRepresenter.add_representer(type(None),
        SafeRepresenter.represent_none)

SafeRepresenter.add_representer(str,
        SafeRepresenter.represent_str)

SafeRepresenter.add_representer(unicode,
        SafeRepresenter.represent_unicode)

SafeRepresenter.add_representer(bool,
        SafeRepresenter.represent_bool)

SafeRepresenter.add_representer(int,
        SafeRepresenter.represent_int)

SafeRepresenter.add_representer(long,
        SafeRepresenter.represent_long)

SafeRepresenter.add_representer(float,
        SafeRepresenter.represent_float)

SafeRepresenter.add_representer(list,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(tuple,
        SafeRepresenter.represent_list)

SafeRepresenter.add_representer(dict,
        SafeRepresenter.represent_dict)

SafeRepresenter.add_representer(set,
        SafeRepresenter.represent_set)

SafeRepresenter.add_representer(datetime.date,
        SafeRepresenter.represent_date)
SafeRepresenter.add_representer(datetime.datetime,
        SafeRepresenter.represent_datetime)

SafeRepresenter.add_representer(None,
        SafeRepresenter.represent_undefined)

class Representer(SafeRepresenter):

    def represent_str(self, data):
        tag = None
        style = None
        try:
            data = unicode(data, 'ascii')
            tag = u'tag:yaml.org,2002:str'
        except UnicodeDecodeError:
            try:
                data = unicode(data, 'utf-8')
                tag = u'tag:yaml.org,2002:python/str'
            except UnicodeDecodeError:
                data = data.encode('base64')
                tag = u'tag:yaml.org,2002:binary'
                style = '|'
        return self.represent_scalar(tag, data, style=style)

    def represent_unicode(self, data):
        tag = None
        try:
            data.encode('ascii')
            tag = u'tag:yaml.org,2002:python/unicode'
        except UnicodeEncodeError:
            tag = u'tag:yaml.org,2002:str'
        return self.represent_scalar(tag, data)

    def represent_long(self, data):
        tag = u'tag:yaml.org,2002:int'
        if int(data) is not data:
            tag = u'tag:yaml.org,2002:python/long'
        return self.represent_scalar(tag, unicode(data))

    def represent_complex(self, data):
        if data.imag == 0.0:
            data = u'%r' % data.real
        elif data.real == 0.0:
            data = u'%rj' % data.imag
        elif data.imag > 0:
            data = u'%r+%rj' % (data.real, data.imag)
        else:
            data = u'%r%rj' % (data.real, data.imag)
        return self.represent_scalar(u'tag:yaml.org,2002:python/complex', data)

    def represent_tuple(self, data):
        return self.represent_sequence(u'tag:yaml.org,2002:python/tuple', data)

    def represent_name(self, data):
        name = u'%s.%s' % (data.__module__, data.__name__)
        return self.represent_scalar(u'tag:yaml.org,2002:python/name:'+name, u'')

    def represent_module(self, data):
        return self.represent_scalar(
                u'tag:yaml.org,2002:python/module:'+data.__name__, u'')

    def represent_instance(self, data):
        # For instances of classic classes, we use __getinitargs__ and
        # __getstate__ to serialize the data.

        # If data.__getinitargs__ exists, the object must be reconstructed by
        # calling cls(**args), where args is a tuple returned by
        # __getinitargs__. Otherwise, the cls.__init__ method should never be
        # called and the class instance is created by instantiating a trivial
        # class and assigning to the instance's __class__ variable.

        # If data.__getstate__ exists, it returns the state of the object.
        # Otherwise, the state of the object is data.__dict__.

        # We produce either a !!python/object or !!python/object/new node.
        # If data.__getinitargs__ does not exist and state is a dictionary, we
        # produce a !!python/object node . Otherwise we produce a
        # !!python/object/new node.

        cls = data.__class__
        class_name = u'%s.%s' % (cls.__module__, cls.__name__)
        args = None
        state = None
        if hasattr(data, '__getinitargs__'):
            args = list(data.__getinitargs__())
        if hasattr(data, '__getstate__'):
            state = data.__getstate__()
        else:
            state = data.__dict__
        if args is None and isinstance(state, dict):
            return self.represent_mapping(
                    u'tag:yaml.org,2002:python/object:'+class_name, state)
        if isinstance(state, dict) and not state:
            return self.represent_sequence(
                    u'tag:yaml.org,2002:python/object/new:'+class_name, args)
        value = {}
        if args:
            value['args'] = args
        value['state'] = state
        return self.represent_mapping(
                u'tag:yaml.org,2002:python/object/new:'+class_name, value)

    def represent_object(self, data):
        # We use __reduce__ API to save the data. data.__reduce__ returns
        # a tuple of length 2-5:
        #   (function, args, state, listitems, dictitems)

        # For reconstructing, we calls function(*args), then set its state,
        # listitems, and dictitems if they are not None.

        # A special case is when function.__name__ == '__newobj__'. In this
        # case we create the object with args[0].__new__(*args).

        # Another special case is when __reduce__ returns a string - we don't
        # support it.

        # We produce a !!python/object, !!python/object/new or
        # !!python/object/apply node.

        cls = type(data)
        if cls in copy_reg.dispatch_table:
            reduce = copy_reg.dispatch_table[cls](data)
        elif hasattr(data, '__reduce_ex__'):
            reduce = data.__reduce_ex__(2)
        elif hasattr(data, '__reduce__'):
            reduce = data.__reduce__()
        else:
            raise RepresenterError("cannot represent object: %r" % data)
        reduce = (list(reduce)+[None]*5)[:5]
        function, args, state, listitems, dictitems = reduce
        args = list(args)
        if state is None:
            state = {}
        if listitems is not None:
            listitems = list(listitems)
        if dictitems is not None:
            dictitems = dict(dictitems)
        if function.__name__ == '__newobj__':
            function = args[0]
            args = args[1:]
            tag = u'tag:yaml.org,2002:python/object/new:'
            newobj = True
        else:
            tag = u'tag:yaml.org,2002:python/object/apply:'
            newobj = False
        function_name = u'%s.%s' % (function.__module__, function.__name__)
        if not args and not listitems and not dictitems \
                and isinstance(state, dict) and newobj:
            return self.represent_mapping(
                    u'tag:yaml.org,2002:python/object:'+function_name, state)
        if not listitems and not dictitems  \
                and isinstance(state, dict) and not state:
            return self.represent_sequence(tag+function_name, args)
        value = {}
        if args:
            value['args'] = args
        if state or not isinstance(state, dict):
            value['state'] = state
        if listitems:
            value['listitems'] = listitems
        if dictitems:
            value['dictitems'] = dictitems
        return self.represent_mapping(tag+function_name, value)

Representer.add_representer(str,
        Representer.represent_str)

Representer.add_representer(unicode,
        Representer.represent_unicode)

Representer.add_representer(long,
        Representer.represent_long)

Representer.add_representer(complex,
        Representer.represent_complex)

Representer.add_representer(tuple,
        Representer.represent_tuple)

Representer.add_representer(type,
        Representer.represent_name)

Representer.add_representer(types.ClassType,
        Representer.represent_name)

Representer.add_representer(types.FunctionType,
        Representer.represent_name)

Representer.add_representer(types.BuiltinFunctionType,
        Representer.represent_name)

Representer.add_representer(types.ModuleType,
        Representer.represent_module)

Representer.add_multi_representer(types.InstanceType,
        Representer.represent_instance)

Representer.add_multi_representer(object,
        Representer.represent_object)


########NEW FILE########
__FILENAME__ = resolver

__all__ = ['BaseResolver', 'Resolver']

from error import *
from nodes import *

import re

class ResolverError(YAMLError):
    pass

class BaseResolver(object):

    DEFAULT_SCALAR_TAG = u'tag:yaml.org,2002:str'
    DEFAULT_SEQUENCE_TAG = u'tag:yaml.org,2002:seq'
    DEFAULT_MAPPING_TAG = u'tag:yaml.org,2002:map'

    yaml_implicit_resolvers = {}
    yaml_path_resolvers = {}

    def __init__(self):
        self.resolver_exact_paths = []
        self.resolver_prefix_paths = []

    def add_implicit_resolver(cls, tag, regexp, first):
        if not 'yaml_implicit_resolvers' in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()
        if first is None:
            first = [None]
        for ch in first:
            cls.yaml_implicit_resolvers.setdefault(ch, []).append((tag, regexp))
    add_implicit_resolver = classmethod(add_implicit_resolver)

    def add_path_resolver(cls, tag, path, kind=None):
        # Note: `add_path_resolver` is experimental.  The API could be changed.
        # `new_path` is a pattern that is matched against the path from the
        # root to the node that is being considered.  `node_path` elements are
        # tuples `(node_check, index_check)`.  `node_check` is a node class:
        # `ScalarNode`, `SequenceNode`, `MappingNode` or `None`.  `None`
        # matches any kind of a node.  `index_check` could be `None`, a boolean
        # value, a string value, or a number.  `None` and `False` match against
        # any _value_ of sequence and mapping nodes.  `True` matches against
        # any _key_ of a mapping node.  A string `index_check` matches against
        # a mapping value that corresponds to a scalar key which content is
        # equal to the `index_check` value.  An integer `index_check` matches
        # against a sequence value with the index equal to `index_check`.
        if not 'yaml_path_resolvers' in cls.__dict__:
            cls.yaml_path_resolvers = cls.yaml_path_resolvers.copy()
        new_path = []
        for element in path:
            if isinstance(element, (list, tuple)):
                if len(element) == 2:
                    node_check, index_check = element
                elif len(element) == 1:
                    node_check = element[0]
                    index_check = True
                else:
                    raise ResolverError("Invalid path element: %s" % element)
            else:
                node_check = None
                index_check = element
            if node_check is str:
                node_check = ScalarNode
            elif node_check is list:
                node_check = SequenceNode
            elif node_check is dict:
                node_check = MappingNode
            elif node_check not in [ScalarNode, SequenceNode, MappingNode]  \
                    and not isinstance(node_check, basestring)  \
                    and node_check is not None:
                raise ResolverError("Invalid node checker: %s" % node_check)
            if not isinstance(index_check, (basestring, int))   \
                    and index_check is not None:
                raise ResolverError("Invalid index checker: %s" % index_check)
            new_path.append((node_check, index_check))
        if kind is str:
            kind = ScalarNode
        elif kind is list:
            kind = SequenceNode
        elif kind is dict:
            kind = MappingNode
        elif kind not in [ScalarNode, SequenceNode, MappingNode]    \
                and kind is not None:
            raise ResolverError("Invalid node kind: %s" % kind)
        cls.yaml_path_resolvers[tuple(new_path), kind] = tag
    add_path_resolver = classmethod(add_path_resolver)

    def descend_resolver(self, current_node, current_index):
        if not self.yaml_path_resolvers:
            return
        exact_paths = {}
        prefix_paths = []
        if current_node:
            depth = len(self.resolver_prefix_paths)
            for path, kind in self.resolver_prefix_paths[-1]:
                if self.check_resolver_prefix(depth, path, kind,
                        current_node, current_index):
                    if len(path) > depth:
                        prefix_paths.append((path, kind))
                    else:
                        exact_paths[kind] = self.yaml_path_resolvers[path, kind]
        else:
            for path, kind in self.yaml_path_resolvers:
                if not path:
                    exact_paths[kind] = self.yaml_path_resolvers[path, kind]
                else:
                    prefix_paths.append((path, kind))
        self.resolver_exact_paths.append(exact_paths)
        self.resolver_prefix_paths.append(prefix_paths)

    def ascend_resolver(self):
        if not self.yaml_path_resolvers:
            return
        self.resolver_exact_paths.pop()
        self.resolver_prefix_paths.pop()

    def check_resolver_prefix(self, depth, path, kind,
            current_node, current_index):
        node_check, index_check = path[depth-1]
        if isinstance(node_check, basestring):
            if current_node.tag != node_check:
                return
        elif node_check is not None:
            if not isinstance(current_node, node_check):
                return
        if index_check is True and current_index is not None:
            return
        if (index_check is False or index_check is None)    \
                and current_index is None:
            return
        if isinstance(index_check, basestring):
            if not (isinstance(current_index, ScalarNode)
                    and index_check == current_index.value):
                return
        elif isinstance(index_check, int) and not isinstance(index_check, bool):
            if index_check != current_index:
                return
        return True

    def resolve(self, kind, value, implicit):
        if kind is ScalarNode and implicit[0]:
            if value == u'':
                resolvers = self.yaml_implicit_resolvers.get(u'', [])
            else:
                resolvers = self.yaml_implicit_resolvers.get(value[0], [])
            resolvers += self.yaml_implicit_resolvers.get(None, [])
            for tag, regexp in resolvers:
                if regexp.match(value):
                    return tag
            implicit = implicit[1]
        if self.yaml_path_resolvers:
            exact_paths = self.resolver_exact_paths[-1]
            if kind in exact_paths:
                return exact_paths[kind]
            if None in exact_paths:
                return exact_paths[None]
        if kind is ScalarNode:
            return self.DEFAULT_SCALAR_TAG
        elif kind is SequenceNode:
            return self.DEFAULT_SEQUENCE_TAG
        elif kind is MappingNode:
            return self.DEFAULT_MAPPING_TAG

class Resolver(BaseResolver):
    pass

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:bool',
        re.compile(ur'''^(?:yes|Yes|YES|no|No|NO
                    |true|True|TRUE|false|False|FALSE
                    |on|On|ON|off|Off|OFF)$''', re.X),
        list(u'yYnNtTfFoO'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:float',
        re.compile(ur'''^(?:[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*(?:[eE][-+][0-9]+)?
                    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$''', re.X),
        list(u'-+0123456789.'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:int',
        re.compile(ur'''^(?:[-+]?0b[0-1_]+
                    |[-+]?0[0-7_]+
                    |[-+]?(?:0|[1-9][0-9_]*)
                    |[-+]?0x[0-9a-fA-F_]+
                    |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$''', re.X),
        list(u'-+0123456789'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:merge',
        re.compile(ur'^(?:<<)$'),
        ['<'])

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:null',
        re.compile(ur'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
        [u'~', u'n', u'N', u''])

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:timestamp',
        re.compile(ur'''^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
                    |[0-9][0-9][0-9][0-9] -[0-9][0-9]? -[0-9][0-9]?
                     (?:[Tt]|[ \t]+)[0-9][0-9]?
                     :[0-9][0-9] :[0-9][0-9] (?:\.[0-9]*)?
                     (?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$''', re.X),
        list(u'0123456789'))

Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:value',
        re.compile(ur'^(?:=)$'),
        ['='])

# The following resolver is only for documentation purposes. It cannot work
# because plain scalars cannot start with '!', '&', or '*'.
Resolver.add_implicit_resolver(
        u'tag:yaml.org,2002:yaml',
        re.compile(ur'^(?:!|&|\*)$'),
        list(u'!&*'))


########NEW FILE########
__FILENAME__ = scanner

# Scanner produces tokens of the following types:
# STREAM-START
# STREAM-END
# DIRECTIVE(name, value)
# DOCUMENT-START
# DOCUMENT-END
# BLOCK-SEQUENCE-START
# BLOCK-MAPPING-START
# BLOCK-END
# FLOW-SEQUENCE-START
# FLOW-MAPPING-START
# FLOW-SEQUENCE-END
# FLOW-MAPPING-END
# BLOCK-ENTRY
# FLOW-ENTRY
# KEY
# VALUE
# ALIAS(value)
# ANCHOR(value)
# TAG(value)
# SCALAR(value, plain, style)
#
# Read comments in the Scanner code for more details.
#

__all__ = ['Scanner', 'ScannerError']

from error import MarkedYAMLError
from tokens import *

class ScannerError(MarkedYAMLError):
    pass

class SimpleKey(object):
    # See below simple keys treatment.

    def __init__(self, token_number, required, index, line, column, mark):
        self.token_number = token_number
        self.required = required
        self.index = index
        self.line = line
        self.column = column
        self.mark = mark

class Scanner(object):

    def __init__(self):
        """Initialize the scanner."""
        # It is assumed that Scanner and Reader will have a common descendant.
        # Reader do the dirty work of checking for BOM and converting the
        # input data to Unicode. It also adds NUL to the end.
        #
        # Reader supports the following methods
        #   self.peek(i=0)       # peek the next i-th character
        #   self.prefix(l=1)     # peek the next l characters
        #   self.forward(l=1)    # read the next l characters and move the pointer.

        # Had we reached the end of the stream?
        self.done = False

        # The number of unclosed '{' and '['. `flow_level == 0` means block
        # context.
        self.flow_level = 0

        # List of processed tokens that are not yet emitted.
        self.tokens = []

        # Add the STREAM-START token.
        self.fetch_stream_start()

        # Number of tokens that were emitted through the `get_token` method.
        self.tokens_taken = 0

        # The current indentation level.
        self.indent = -1

        # Past indentation levels.
        self.indents = []

        # Variables related to simple keys treatment.

        # A simple key is a key that is not denoted by the '?' indicator.
        # Example of simple keys:
        #   ---
        #   block simple key: value
        #   ? not a simple key:
        #   : { flow simple key: value }
        # We emit the KEY token before all keys, so when we find a potential
        # simple key, we try to locate the corresponding ':' indicator.
        # Simple keys should be limited to a single line and 1024 characters.

        # Can a simple key start at the current position? A simple key may
        # start:
        # - at the beginning of the line, not counting indentation spaces
        #       (in block context),
        # - after '{', '[', ',' (in the flow context),
        # - after '?', ':', '-' (in the block context).
        # In the block context, this flag also signifies if a block collection
        # may start at the current position.
        self.allow_simple_key = True

        # Keep track of possible simple keys. This is a dictionary. The key
        # is `flow_level`; there can be no more that one possible simple key
        # for each level. The value is a SimpleKey record:
        #   (token_number, required, index, line, column, mark)
        # A simple key may start with ALIAS, ANCHOR, TAG, SCALAR(flow),
        # '[', or '{' tokens.
        self.possible_simple_keys = {}

    # Public methods.

    def check_token(self, *choices):
        # Check if the next token is one of the given types.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.tokens[0], choice):
                    return True
        return False

    def peek_token(self):
        # Return the next token, but do not delete if from the queue.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            return self.tokens[0]

    def get_token(self):
        # Return the next token.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            self.tokens_taken += 1
            return self.tokens.pop(0)

    # Private methods.

    def need_more_tokens(self):
        if self.done:
            return False
        if not self.tokens:
            return True
        # The current token may be a potential simple key, so we
        # need to look further.
        self.stale_possible_simple_keys()
        if self.next_possible_simple_key() == self.tokens_taken:
            return True

    def fetch_more_tokens(self):

        # Eat whitespaces and comments until we reach the next token.
        self.scan_to_next_token()

        # Remove obsolete possible simple keys.
        self.stale_possible_simple_keys()

        # Compare the current indentation and column. It may add some tokens
        # and decrease the current indentation level.
        self.unwind_indent(self.column)

        # Peek the next character.
        ch = self.peek()

        # Is it the end of stream?
        if ch == u'\0':
            return self.fetch_stream_end()

        # Is it a directive?
        if ch == u'%' and self.check_directive():
            return self.fetch_directive()

        # Is it the document start?
        if ch == u'-' and self.check_document_start():
            return self.fetch_document_start()

        # Is it the document end?
        if ch == u'.' and self.check_document_end():
            return self.fetch_document_end()

        # TODO: support for BOM within a stream.
        #if ch == u'\uFEFF':
        #    return self.fetch_bom()    <-- issue BOMToken

        # Note: the order of the following checks is NOT significant.

        # Is it the flow sequence start indicator?
        if ch == u'[':
            return self.fetch_flow_sequence_start()

        # Is it the flow mapping start indicator?
        if ch == u'{':
            return self.fetch_flow_mapping_start()

        # Is it the flow sequence end indicator?
        if ch == u']':
            return self.fetch_flow_sequence_end()

        # Is it the flow mapping end indicator?
        if ch == u'}':
            return self.fetch_flow_mapping_end()

        # Is it the flow entry indicator?
        if ch == u',':
            return self.fetch_flow_entry()

        # Is it the block entry indicator?
        if ch == u'-' and self.check_block_entry():
            return self.fetch_block_entry()

        # Is it the key indicator?
        if ch == u'?' and self.check_key():
            return self.fetch_key()

        # Is it the value indicator?
        if ch == u':' and self.check_value():
            return self.fetch_value()

        # Is it an alias?
        if ch == u'*':
            return self.fetch_alias()

        # Is it an anchor?
        if ch == u'&':
            return self.fetch_anchor()

        # Is it a tag?
        if ch == u'!':
            return self.fetch_tag()

        # Is it a literal scalar?
        if ch == u'|' and not self.flow_level:
            return self.fetch_literal()

        # Is it a folded scalar?
        if ch == u'>' and not self.flow_level:
            return self.fetch_folded()

        # Is it a single quoted scalar?
        if ch == u'\'':
            return self.fetch_single()

        # Is it a double quoted scalar?
        if ch == u'\"':
            return self.fetch_double()

        # It must be a plain scalar then.
        if self.check_plain():
            return self.fetch_plain()

        # No? It's an error. Let's produce a nice error message.
        raise ScannerError("while scanning for the next token", None,
                "found character %r that cannot start any token"
                % ch.encode('utf-8'), self.get_mark())

    # Simple keys treatment.

    def next_possible_simple_key(self):
        # Return the number of the nearest possible simple key. Actually we
        # don't need to loop through the whole dictionary. We may replace it
        # with the following code:
        #   if not self.possible_simple_keys:
        #       return None
        #   return self.possible_simple_keys[
        #           min(self.possible_simple_keys.keys())].token_number
        min_token_number = None
        for level in self.possible_simple_keys:
            key = self.possible_simple_keys[level]
            if min_token_number is None or key.token_number < min_token_number:
                min_token_number = key.token_number
        return min_token_number

    def stale_possible_simple_keys(self):
        # Remove entries that are no longer possible simple keys. According to
        # the YAML specification, simple keys
        # - should be limited to a single line,
        # - should be no longer than 1024 characters.
        # Disabling this procedure will allow simple keys of any length and
        # height (may cause problems if indentation is broken though).
        for level in self.possible_simple_keys.keys():
            key = self.possible_simple_keys[level]
            if key.line != self.line  \
                    or self.index-key.index > 1024:
                if key.required:
                    raise ScannerError("while scanning a simple key", key.mark,
                            "could not found expected ':'", self.get_mark())
                del self.possible_simple_keys[level]

    def save_possible_simple_key(self):
        # The next token may start a simple key. We check if it's possible
        # and save its position. This function is called for
        #   ALIAS, ANCHOR, TAG, SCALAR(flow), '[', and '{'.

        # Check if a simple key is required at the current position.
        required = not self.flow_level and self.indent == self.column

        # A simple key is required only if it is the first token in the current
        # line. Therefore it is always allowed.
        assert self.allow_simple_key or not required

        # The next token might be a simple key. Let's save it's number and
        # position.
        if self.allow_simple_key:
            self.remove_possible_simple_key()
            token_number = self.tokens_taken+len(self.tokens)
            key = SimpleKey(token_number, required,
                    self.index, self.line, self.column, self.get_mark())
            self.possible_simple_keys[self.flow_level] = key

    def remove_possible_simple_key(self):
        # Remove the saved possible key position at the current flow level.
        if self.flow_level in self.possible_simple_keys:
            key = self.possible_simple_keys[self.flow_level]
            
            if key.required:
                raise ScannerError("while scanning a simple key", key.mark,
                        "could not found expected ':'", self.get_mark())

            del self.possible_simple_keys[self.flow_level]

    # Indentation functions.

    def unwind_indent(self, column):

        ## In flow context, tokens should respect indentation.
        ## Actually the condition should be `self.indent >= column` according to
        ## the spec. But this condition will prohibit intuitively correct
        ## constructions such as
        ## key : {
        ## }
        #if self.flow_level and self.indent > column:
        #    raise ScannerError(None, None,
        #            "invalid intendation or unclosed '[' or '{'",
        #            self.get_mark())

        # In the flow context, indentation is ignored. We make the scanner less
        # restrictive then specification requires.
        if self.flow_level:
            return

        # In block context, we may need to issue the BLOCK-END tokens.
        while self.indent > column:
            mark = self.get_mark()
            self.indent = self.indents.pop()
            self.tokens.append(BlockEndToken(mark, mark))

    def add_indent(self, column):
        # Check if we need to increase indentation.
        if self.indent < column:
            self.indents.append(self.indent)
            self.indent = column
            return True
        return False

    # Fetchers.

    def fetch_stream_start(self):
        # We always add STREAM-START as the first token and STREAM-END as the
        # last token.

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-START.
        self.tokens.append(StreamStartToken(mark, mark,
            encoding=self.encoding))
        

    def fetch_stream_end(self):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset everything (not really needed).
        self.allow_simple_key = False
        self.possible_simple_keys = {}

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-END.
        self.tokens.append(StreamEndToken(mark, mark))

        # The steam is finished.
        self.done = True

    def fetch_directive(self):
        
        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Scan and add DIRECTIVE.
        self.tokens.append(self.scan_directive())

    def fetch_document_start(self):
        self.fetch_document_indicator(DocumentStartToken)

    def fetch_document_end(self):
        self.fetch_document_indicator(DocumentEndToken)

    def fetch_document_indicator(self, TokenClass):

        # Set the current intendation to -1.
        self.unwind_indent(-1)

        # Reset simple keys. Note that there could not be a block collection
        # after '---'.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Add DOCUMENT-START or DOCUMENT-END.
        start_mark = self.get_mark()
        self.forward(3)
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_start(self):
        self.fetch_flow_collection_start(FlowSequenceStartToken)

    def fetch_flow_mapping_start(self):
        self.fetch_flow_collection_start(FlowMappingStartToken)

    def fetch_flow_collection_start(self, TokenClass):

        # '[' and '{' may start a simple key.
        self.save_possible_simple_key()

        # Increase the flow level.
        self.flow_level += 1

        # Simple keys are allowed after '[' and '{'.
        self.allow_simple_key = True

        # Add FLOW-SEQUENCE-START or FLOW-MAPPING-START.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_end(self):
        self.fetch_flow_collection_end(FlowSequenceEndToken)

    def fetch_flow_mapping_end(self):
        self.fetch_flow_collection_end(FlowMappingEndToken)

    def fetch_flow_collection_end(self, TokenClass):

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Decrease the flow level.
        self.flow_level -= 1

        # No simple keys after ']' or '}'.
        self.allow_simple_key = False

        # Add FLOW-SEQUENCE-END or FLOW-MAPPING-END.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_entry(self):

        # Simple keys are allowed after ','.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add FLOW-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(FlowEntryToken(start_mark, end_mark))

    def fetch_block_entry(self):

        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a new entry?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "sequence entries are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-SEQUENCE-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockSequenceStartToken(mark, mark))

        # It's an error for the block entry to occur in the flow context,
        # but we let the parser detect this.
        else:
            pass

        # Simple keys are allowed after '-'.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add BLOCK-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(BlockEntryToken(start_mark, end_mark))

    def fetch_key(self):
        
        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a key (not nessesary a simple)?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "mapping keys are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-MAPPING-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockMappingStartToken(mark, mark))

        # Simple keys are allowed after '?' in the block context.
        self.allow_simple_key = not self.flow_level

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add KEY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(KeyToken(start_mark, end_mark))

    def fetch_value(self):

        # Do we determine a simple key?
        if self.flow_level in self.possible_simple_keys:

            # Add KEY.
            key = self.possible_simple_keys[self.flow_level]
            del self.possible_simple_keys[self.flow_level]
            self.tokens.insert(key.token_number-self.tokens_taken,
                    KeyToken(key.mark, key.mark))

            # If this key starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.
            if not self.flow_level:
                if self.add_indent(key.column):
                    self.tokens.insert(key.token_number-self.tokens_taken,
                            BlockMappingStartToken(key.mark, key.mark))

            # There cannot be two simple keys one after another.
            self.allow_simple_key = False

        # It must be a part of a complex key.
        else:
            
            # Block context needs additional checks.
            # (Do we really need them? They will be catched by the parser
            # anyway.)
            if not self.flow_level:

                # We are allowed to start a complex value if and only if
                # we can start a simple key.
                if not self.allow_simple_key:
                    raise ScannerError(None, None,
                            "mapping values are not allowed here",
                            self.get_mark())

            # If this value starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.  It will be detected as an error later by
            # the parser.
            if not self.flow_level:
                if self.add_indent(self.column):
                    mark = self.get_mark()
                    self.tokens.append(BlockMappingStartToken(mark, mark))

            # Simple keys are allowed after ':' in the block context.
            self.allow_simple_key = not self.flow_level

            # Reset possible simple key on the current level.
            self.remove_possible_simple_key()

        # Add VALUE.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(ValueToken(start_mark, end_mark))

    def fetch_alias(self):

        # ALIAS could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after ALIAS.
        self.allow_simple_key = False

        # Scan and add ALIAS.
        self.tokens.append(self.scan_anchor(AliasToken))

    def fetch_anchor(self):

        # ANCHOR could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after ANCHOR.
        self.allow_simple_key = False

        # Scan and add ANCHOR.
        self.tokens.append(self.scan_anchor(AnchorToken))

    def fetch_tag(self):

        # TAG could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after TAG.
        self.allow_simple_key = False

        # Scan and add TAG.
        self.tokens.append(self.scan_tag())

    def fetch_literal(self):
        self.fetch_block_scalar(style='|')

    def fetch_folded(self):
        self.fetch_block_scalar(style='>')

    def fetch_block_scalar(self, style):

        # A simple key may follow a block scalar.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Scan and add SCALAR.
        self.tokens.append(self.scan_block_scalar(style))

    def fetch_single(self):
        self.fetch_flow_scalar(style='\'')

    def fetch_double(self):
        self.fetch_flow_scalar(style='"')

    def fetch_flow_scalar(self, style):

        # A flow scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after flow scalars.
        self.allow_simple_key = False

        # Scan and add SCALAR.
        self.tokens.append(self.scan_flow_scalar(style))

    def fetch_plain(self):

        # A plain scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after plain scalars. But note that `scan_plain` will
        # change this flag if the scan is finished at the beginning of the
        # line.
        self.allow_simple_key = False

        # Scan and add SCALAR. May change `allow_simple_key`.
        self.tokens.append(self.scan_plain())

    # Checkers.

    def check_directive(self):

        # DIRECTIVE:        ^ '%' ...
        # The '%' indicator is already checked.
        if self.column == 0:
            return True

    def check_document_start(self):

        # DOCUMENT-START:   ^ '---' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == u'---'  \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_document_end(self):

        # DOCUMENT-END:     ^ '...' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == u'...'  \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_block_entry(self):

        # BLOCK-ENTRY:      '-' (' '|'\n')
        return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_key(self):

        # KEY(flow context):    '?'
        if self.flow_level:
            return True

        # KEY(block context):   '?' (' '|'\n')
        else:
            return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_value(self):

        # VALUE(flow context):  ':'
        if self.flow_level:
            return True

        # VALUE(block context): ':' (' '|'\n')
        else:
            return self.peek(1) in u'\0 \t\r\n\x85\u2028\u2029'

    def check_plain(self):

        # A plain scalar may start with any non-space character except:
        #   '-', '?', ':', ',', '[', ']', '{', '}',
        #   '#', '&', '*', '!', '|', '>', '\'', '\"',
        #   '%', '@', '`'.
        #
        # It may also start with
        #   '-', '?', ':'
        # if it is followed by a non-space character.
        #
        # Note that we limit the last rule to the block context (except the
        # '-' character) because we want the flow context to be space
        # independent.
        ch = self.peek()
        return ch not in u'\0 \t\r\n\x85\u2028\u2029-?:,[]{}#&*!|>\'\"%@`'  \
                or (self.peek(1) not in u'\0 \t\r\n\x85\u2028\u2029'
                        and (ch == u'-' or (not self.flow_level and ch in u'?:')))

    # Scanners.

    def scan_to_next_token(self):
        # We ignore spaces, line breaks and comments.
        # If we find a line break in the block context, we set the flag
        # `allow_simple_key` on.
        # The byte order mark is stripped if it's the first character in the
        # stream. We do not yet support BOM inside the stream as the
        # specification requires. Any such mark will be considered as a part
        # of the document.
        #
        # TODO: We need to make tab handling rules more sane. A good rule is
        #   Tabs cannot precede tokens
        #   BLOCK-SEQUENCE-START, BLOCK-MAPPING-START, BLOCK-END,
        #   KEY(block), VALUE(block), BLOCK-ENTRY
        # So the checking code is
        #   if <TAB>:
        #       self.allow_simple_keys = False
        # We also need to add the check for `allow_simple_keys == True` to
        # `unwind_indent` before issuing BLOCK-END.
        # Scanners for block, flow, and plain scalars need to be modified.

        if self.index == 0 and self.peek() == u'\uFEFF':
            self.forward()
        found = False
        while not found:
            while self.peek() == u' ':
                self.forward()
            if self.peek() == u'#':
                while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                    self.forward()
            if self.scan_line_break():
                if not self.flow_level:
                    self.allow_simple_key = True
            else:
                found = True

    def scan_directive(self):
        # See the specification for details.
        start_mark = self.get_mark()
        self.forward()
        name = self.scan_directive_name(start_mark)
        value = None
        if name == u'YAML':
            value = self.scan_yaml_directive_value(start_mark)
            end_mark = self.get_mark()
        elif name == u'TAG':
            value = self.scan_tag_directive_value(start_mark)
            end_mark = self.get_mark()
        else:
            end_mark = self.get_mark()
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        self.scan_directive_ignored_line(start_mark)
        return DirectiveToken(name, value, start_mark, end_mark)

    def scan_directive_name(self, start_mark):
        # See the specification for details.
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'  \
                or ch in u'-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        return value

    def scan_yaml_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        major = self.scan_yaml_directive_number(start_mark)
        if self.peek() != '.':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or '.', but found %r"
                    % self.peek().encode('utf-8'),
                    self.get_mark())
        self.forward()
        minor = self.scan_yaml_directive_number(start_mark)
        if self.peek() not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or ' ', but found %r"
                    % self.peek().encode('utf-8'),
                    self.get_mark())
        return (major, minor)

    def scan_yaml_directive_number(self, start_mark):
        # See the specification for details.
        ch = self.peek()
        if not (u'0' <= ch <= '9'):
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit, but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        length = 0
        while u'0' <= self.peek(length) <= u'9':
            length += 1
        value = int(self.prefix(length))
        self.forward(length)
        return value

    def scan_tag_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        handle = self.scan_tag_directive_handle(start_mark)
        while self.peek() == u' ':
            self.forward()
        prefix = self.scan_tag_directive_prefix(start_mark)
        return (handle, prefix)

    def scan_tag_directive_handle(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_handle('directive', start_mark)
        ch = self.peek()
        if ch != u' ':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return value

    def scan_tag_directive_prefix(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_uri('directive', start_mark)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return value

    def scan_directive_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        if self.peek() == u'#':
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in u'\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        self.scan_line_break()

    def scan_anchor(self, TokenClass):
        # The specification does not restrict characters for anchors and
        # aliases. This may lead to problems, for instance, the document:
        #   [ *alias, value ]
        # can be interpteted in two ways, as
        #   [ "value" ]
        # and
        #   [ *alias , "value" ]
        # Therefore we restrict aliases to numbers and ASCII letters.
        start_mark = self.get_mark()
        indicator = self.peek()
        if indicator == '*':
            name = 'alias'
        else:
            name = 'anchor'
        self.forward()
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'  \
                or ch in u'-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in u'\0 \t\r\n\x85\u2028\u2029?:,]}%@`':
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch.encode('utf-8'), self.get_mark())
        end_mark = self.get_mark()
        return TokenClass(value, start_mark, end_mark)

    def scan_tag(self):
        # See the specification for details.
        start_mark = self.get_mark()
        ch = self.peek(1)
        if ch == u'<':
            handle = None
            self.forward(2)
            suffix = self.scan_tag_uri('tag', start_mark)
            if self.peek() != u'>':
                raise ScannerError("while parsing a tag", start_mark,
                        "expected '>', but found %r" % self.peek().encode('utf-8'),
                        self.get_mark())
            self.forward()
        elif ch in u'\0 \t\r\n\x85\u2028\u2029':
            handle = None
            suffix = u'!'
            self.forward()
        else:
            length = 1
            use_handle = False
            while ch not in u'\0 \r\n\x85\u2028\u2029':
                if ch == u'!':
                    use_handle = True
                    break
                length += 1
                ch = self.peek(length)
            handle = u'!'
            if use_handle:
                handle = self.scan_tag_handle('tag', start_mark)
            else:
                handle = u'!'
                self.forward()
            suffix = self.scan_tag_uri('tag', start_mark)
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a tag", start_mark,
                    "expected ' ', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        value = (handle, suffix)
        end_mark = self.get_mark()
        return TagToken(value, start_mark, end_mark)

    def scan_block_scalar(self, style):
        # See the specification for details.

        if style == '>':
            folded = True
        else:
            folded = False

        chunks = []
        start_mark = self.get_mark()

        # Scan the header.
        self.forward()
        chomping, increment = self.scan_block_scalar_indicators(start_mark)
        self.scan_block_scalar_ignored_line(start_mark)

        # Determine the indentation level and go to the first non-empty line.
        min_indent = self.indent+1
        if min_indent < 1:
            min_indent = 1
        if increment is None:
            breaks, max_indent, end_mark = self.scan_block_scalar_indentation()
            indent = max(min_indent, max_indent)
        else:
            indent = min_indent+increment-1
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
        line_break = u''

        # Scan the inner part of the block scalar.
        while self.column == indent and self.peek() != u'\0':
            chunks.extend(breaks)
            leading_non_space = self.peek() not in u' \t'
            length = 0
            while self.peek(length) not in u'\0\r\n\x85\u2028\u2029':
                length += 1
            chunks.append(self.prefix(length))
            self.forward(length)
            line_break = self.scan_line_break()
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
            if self.column == indent and self.peek() != u'\0':

                # Unfortunately, folding rules are ambiguous.
                #
                # This is the folding according to the specification:
                
                if folded and line_break == u'\n'   \
                        and leading_non_space and self.peek() not in u' \t':
                    if not breaks:
                        chunks.append(u' ')
                else:
                    chunks.append(line_break)
                
                # This is Clark Evans's interpretation (also in the spec
                # examples):
                #
                #if folded and line_break == u'\n':
                #    if not breaks:
                #        if self.peek() not in ' \t':
                #            chunks.append(u' ')
                #        else:
                #            chunks.append(line_break)
                #else:
                #    chunks.append(line_break)
            else:
                break

        # Chomp the tail.
        if chomping is not False:
            chunks.append(line_break)
        if chomping is True:
            chunks.extend(breaks)

        # We are done.
        return ScalarToken(u''.join(chunks), False, start_mark, end_mark,
                style)

    def scan_block_scalar_indicators(self, start_mark):
        # See the specification for details.
        chomping = None
        increment = None
        ch = self.peek()
        if ch in u'+-':
            if ch == '+':
                chomping = True
            else:
                chomping = False
            self.forward()
            ch = self.peek()
            if ch in u'0123456789':
                increment = int(ch)
                if increment == 0:
                    raise ScannerError("while scanning a block scalar", start_mark,
                            "expected indentation indicator in the range 1-9, but found 0",
                            self.get_mark())
                self.forward()
        elif ch in u'0123456789':
            increment = int(ch)
            if increment == 0:
                raise ScannerError("while scanning a block scalar", start_mark,
                        "expected indentation indicator in the range 1-9, but found 0",
                        self.get_mark())
            self.forward()
            ch = self.peek()
            if ch in u'+-':
                if ch == '+':
                    chomping = True
                else:
                    chomping = False
                self.forward()
        ch = self.peek()
        if ch not in u'\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected chomping or indentation indicators, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        return chomping, increment

    def scan_block_scalar_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == u' ':
            self.forward()
        if self.peek() == u'#':
            while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in u'\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch.encode('utf-8'), self.get_mark())
        self.scan_line_break()

    def scan_block_scalar_indentation(self):
        # See the specification for details.
        chunks = []
        max_indent = 0
        end_mark = self.get_mark()
        while self.peek() in u' \r\n\x85\u2028\u2029':
            if self.peek() != u' ':
                chunks.append(self.scan_line_break())
                end_mark = self.get_mark()
            else:
                self.forward()
                if self.column > max_indent:
                    max_indent = self.column
        return chunks, max_indent, end_mark

    def scan_block_scalar_breaks(self, indent):
        # See the specification for details.
        chunks = []
        end_mark = self.get_mark()
        while self.column < indent and self.peek() == u' ':
            self.forward()
        while self.peek() in u'\r\n\x85\u2028\u2029':
            chunks.append(self.scan_line_break())
            end_mark = self.get_mark()
            while self.column < indent and self.peek() == u' ':
                self.forward()
        return chunks, end_mark

    def scan_flow_scalar(self, style):
        # See the specification for details.
        # Note that we loose indentation rules for quoted scalars. Quoted
        # scalars don't need to adhere indentation because " and ' clearly
        # mark the beginning and the end of them. Therefore we are less
        # restrictive then the specification requires. We only need to check
        # that document separators are not included in scalars.
        if style == '"':
            double = True
        else:
            double = False
        chunks = []
        start_mark = self.get_mark()
        quote = self.peek()
        self.forward()
        chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        while self.peek() != quote:
            chunks.extend(self.scan_flow_scalar_spaces(double, start_mark))
            chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        self.forward()
        end_mark = self.get_mark()
        return ScalarToken(u''.join(chunks), False, start_mark, end_mark,
                style)

    ESCAPE_REPLACEMENTS = {
        u'0':   u'\0',
        u'a':   u'\x07',
        u'b':   u'\x08',
        u't':   u'\x09',
        u'\t':  u'\x09',
        u'n':   u'\x0A',
        u'v':   u'\x0B',
        u'f':   u'\x0C',
        u'r':   u'\x0D',
        u'e':   u'\x1B',
        u' ':   u'\x20',
        u'\"':  u'\"',
        u'\\':  u'\\',
        u'N':   u'\x85',
        u'_':   u'\xA0',
        u'L':   u'\u2028',
        u'P':   u'\u2029',
    }

    ESCAPE_CODES = {
        u'x':   2,
        u'u':   4,
        u'U':   8,
    }

    def scan_flow_scalar_non_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            length = 0
            while self.peek(length) not in u'\'\"\\\0 \t\r\n\x85\u2028\u2029':
                length += 1
            if length:
                chunks.append(self.prefix(length))
                self.forward(length)
            ch = self.peek()
            if not double and ch == u'\'' and self.peek(1) == u'\'':
                chunks.append(u'\'')
                self.forward(2)
            elif (double and ch == u'\'') or (not double and ch in u'\"\\'):
                chunks.append(ch)
                self.forward()
            elif double and ch == u'\\':
                self.forward()
                ch = self.peek()
                if ch in self.ESCAPE_REPLACEMENTS:
                    chunks.append(self.ESCAPE_REPLACEMENTS[ch])
                    self.forward()
                elif ch in self.ESCAPE_CODES:
                    length = self.ESCAPE_CODES[ch]
                    self.forward()
                    for k in range(length):
                        if self.peek(k) not in u'0123456789ABCDEFabcdef':
                            raise ScannerError("while scanning a double-quoted scalar", start_mark,
                                    "expected escape sequence of %d hexdecimal numbers, but found %r" %
                                        (length, self.peek(k).encode('utf-8')), self.get_mark())
                    code = int(self.prefix(length), 16)
                    chunks.append(unichr(code))
                    self.forward(length)
                elif ch in u'\r\n\x85\u2028\u2029':
                    self.scan_line_break()
                    chunks.extend(self.scan_flow_scalar_breaks(double, start_mark))
                else:
                    raise ScannerError("while scanning a double-quoted scalar", start_mark,
                            "found unknown escape character %r" % ch.encode('utf-8'), self.get_mark())
            else:
                return chunks

    def scan_flow_scalar_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        length = 0
        while self.peek(length) in u' \t':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch == u'\0':
            raise ScannerError("while scanning a quoted scalar", start_mark,
                    "found unexpected end of stream", self.get_mark())
        elif ch in u'\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            breaks = self.scan_flow_scalar_breaks(double, start_mark)
            if line_break != u'\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(u' ')
            chunks.extend(breaks)
        else:
            chunks.append(whitespaces)
        return chunks

    def scan_flow_scalar_breaks(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            # Instead of checking indentation, we check for document
            # separators.
            prefix = self.prefix(3)
            if (prefix == u'---' or prefix == u'...')   \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                raise ScannerError("while scanning a quoted scalar", start_mark,
                        "found unexpected document separator", self.get_mark())
            while self.peek() in u' \t':
                self.forward()
            if self.peek() in u'\r\n\x85\u2028\u2029':
                chunks.append(self.scan_line_break())
            else:
                return chunks

    def scan_plain(self):
        # See the specification for details.
        # We add an additional restriction for the flow context:
        #   plain scalars in the flow context cannot contain ',', ':' and '?'.
        # We also keep track of the `allow_simple_key` flag here.
        # Indentation rules are loosed for the flow context.
        chunks = []
        start_mark = self.get_mark()
        end_mark = start_mark
        indent = self.indent+1
        # We allow zero indentation for scalars, but then we need to check for
        # document separators at the beginning of the line.
        #if indent == 0:
        #    indent = 1
        spaces = []
        while True:
            length = 0
            if self.peek() == u'#':
                break
            while True:
                ch = self.peek(length)
                if ch in u'\0 \t\r\n\x85\u2028\u2029'   \
                        or (not self.flow_level and ch == u':' and
                                self.peek(length+1) in u'\0 \t\r\n\x85\u2028\u2029') \
                        or (self.flow_level and ch in u',:?[]{}'):
                    break
                length += 1
            # It's not clear what we should do with ':' in the flow context.
            if (self.flow_level and ch == u':'
                    and self.peek(length+1) not in u'\0 \t\r\n\x85\u2028\u2029,[]{}'):
                self.forward(length)
                raise ScannerError("while scanning a plain scalar", start_mark,
                    "found unexpected ':'", self.get_mark(),
                    "Please check http://pyyaml.org/wiki/YAMLColonInFlowContext for details.")
            if length == 0:
                break
            self.allow_simple_key = False
            chunks.extend(spaces)
            chunks.append(self.prefix(length))
            self.forward(length)
            end_mark = self.get_mark()
            spaces = self.scan_plain_spaces(indent, start_mark)
            if not spaces or self.peek() == u'#' \
                    or (not self.flow_level and self.column < indent):
                break
        return ScalarToken(u''.join(chunks), True, start_mark, end_mark)

    def scan_plain_spaces(self, indent, start_mark):
        # See the specification for details.
        # The specification is really confusing about tabs in plain scalars.
        # We just forbid them completely. Do not use tabs in YAML!
        chunks = []
        length = 0
        while self.peek(length) in u' ':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch in u'\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            self.allow_simple_key = True
            prefix = self.prefix(3)
            if (prefix == u'---' or prefix == u'...')   \
                    and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                return
            breaks = []
            while self.peek() in u' \r\n\x85\u2028\u2029':
                if self.peek() == ' ':
                    self.forward()
                else:
                    breaks.append(self.scan_line_break())
                    prefix = self.prefix(3)
                    if (prefix == u'---' or prefix == u'...')   \
                            and self.peek(3) in u'\0 \t\r\n\x85\u2028\u2029':
                        return
            if line_break != u'\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(u' ')
            chunks.extend(breaks)
        elif whitespaces:
            chunks.append(whitespaces)
        return chunks

    def scan_tag_handle(self, name, start_mark):
        # See the specification for details.
        # For some strange reasons, the specification does not allow '_' in
        # tag handles. I have allowed it anyway.
        ch = self.peek()
        if ch != u'!':
            raise ScannerError("while scanning a %s" % name, start_mark,
                    "expected '!', but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        length = 1
        ch = self.peek(length)
        if ch != u' ':
            while u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'  \
                    or ch in u'-_':
                length += 1
                ch = self.peek(length)
            if ch != u'!':
                self.forward(length)
                raise ScannerError("while scanning a %s" % name, start_mark,
                        "expected '!', but found %r" % ch.encode('utf-8'),
                        self.get_mark())
            length += 1
        value = self.prefix(length)
        self.forward(length)
        return value

    def scan_tag_uri(self, name, start_mark):
        # See the specification for details.
        # Note: we do not check if URI is well-formed.
        chunks = []
        length = 0
        ch = self.peek(length)
        while u'0' <= ch <= u'9' or u'A' <= ch <= 'Z' or u'a' <= ch <= 'z'  \
                or ch in u'-;/?:@&=+$,_.!~*\'()[]%':
            if ch == u'%':
                chunks.append(self.prefix(length))
                self.forward(length)
                length = 0
                chunks.append(self.scan_uri_escapes(name, start_mark))
            else:
                length += 1
            ch = self.peek(length)
        if length:
            chunks.append(self.prefix(length))
            self.forward(length)
            length = 0
        if not chunks:
            raise ScannerError("while parsing a %s" % name, start_mark,
                    "expected URI, but found %r" % ch.encode('utf-8'),
                    self.get_mark())
        return u''.join(chunks)

    def scan_uri_escapes(self, name, start_mark):
        # See the specification for details.
        bytes = []
        mark = self.get_mark()
        while self.peek() == u'%':
            self.forward()
            for k in range(2):
                if self.peek(k) not in u'0123456789ABCDEFabcdef':
                    raise ScannerError("while scanning a %s" % name, start_mark,
                            "expected URI escape sequence of 2 hexdecimal numbers, but found %r" %
                                (self.peek(k).encode('utf-8')), self.get_mark())
            bytes.append(chr(int(self.prefix(2), 16)))
            self.forward(2)
        try:
            value = unicode(''.join(bytes), 'utf-8')
        except UnicodeDecodeError, exc:
            raise ScannerError("while scanning a %s" % name, start_mark, str(exc), mark)
        return value

    def scan_line_break(self):
        # Transforms:
        #   '\r\n'      :   '\n'
        #   '\r'        :   '\n'
        #   '\n'        :   '\n'
        #   '\x85'      :   '\n'
        #   '\u2028'    :   '\u2028'
        #   '\u2029     :   '\u2029'
        #   default     :   ''
        ch = self.peek()
        if ch in u'\r\n\x85':
            if self.prefix(2) == u'\r\n':
                self.forward(2)
            else:
                self.forward()
            return u'\n'
        elif ch in u'\u2028\u2029':
            self.forward()
            return ch
        return u''

#try:
#    import psyco
#    psyco.bind(Scanner)
#except ImportError:
#    pass


########NEW FILE########
__FILENAME__ = serializer

__all__ = ['Serializer', 'SerializerError']

from error import YAMLError
from events import *
from nodes import *

class SerializerError(YAMLError):
    pass

class Serializer(object):

    ANCHOR_TEMPLATE = u'id%03d'

    def __init__(self, encoding=None,
            explicit_start=None, explicit_end=None, version=None, tags=None):
        self.use_encoding = encoding
        self.use_explicit_start = explicit_start
        self.use_explicit_end = explicit_end
        self.use_version = version
        self.use_tags = tags
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_anchor_id = 0
        self.closed = None

    def open(self):
        if self.closed is None:
            self.emit(StreamStartEvent(encoding=self.use_encoding))
            self.closed = False
        elif self.closed:
            raise SerializerError("serializer is closed")
        else:
            raise SerializerError("serializer is already opened")

    def close(self):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif not self.closed:
            self.emit(StreamEndEvent())
            self.closed = True

    #def __del__(self):
    #    self.close()

    def serialize(self, node):
        if self.closed is None:
            raise SerializerError("serializer is not opened")
        elif self.closed:
            raise SerializerError("serializer is closed")
        self.emit(DocumentStartEvent(explicit=self.use_explicit_start,
            version=self.use_version, tags=self.use_tags))
        self.anchor_node(node)
        self.serialize_node(node, None, None)
        self.emit(DocumentEndEvent(explicit=self.use_explicit_end))
        self.serialized_nodes = {}
        self.anchors = {}
        self.last_alias_id = 0

    def anchor_node(self, node):
        if node in self.anchors:
            if self.anchors[node] is None:
                self.anchors[node] = self.generate_anchor(node)
        else:
            self.anchors[node] = None
            if isinstance(node, SequenceNode):
                for item in node.value:
                    self.anchor_node(item)
            elif isinstance(node, MappingNode):
                for key, value in node.value:
                    self.anchor_node(key)
                    self.anchor_node(value)

    def generate_anchor(self, node):
        self.last_anchor_id += 1
        return self.ANCHOR_TEMPLATE % self.last_anchor_id

    def serialize_node(self, node, parent, index):
        alias = self.anchors[node]
        if node in self.serialized_nodes:
            self.emit(AliasEvent(alias))
        else:
            self.serialized_nodes[node] = True
            self.descend_resolver(parent, index)
            if isinstance(node, ScalarNode):
                detected_tag = self.resolve(ScalarNode, node.value, (True, False))
                default_tag = self.resolve(ScalarNode, node.value, (False, True))
                implicit = (node.tag == detected_tag), (node.tag == default_tag)
                self.emit(ScalarEvent(alias, node.tag, implicit, node.value,
                    style=node.style))
            elif isinstance(node, SequenceNode):
                implicit = (node.tag
                            == self.resolve(SequenceNode, node.value, True))
                self.emit(SequenceStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                index = 0
                for item in node.value:
                    self.serialize_node(item, node, index)
                    index += 1
                self.emit(SequenceEndEvent())
            elif isinstance(node, MappingNode):
                implicit = (node.tag
                            == self.resolve(MappingNode, node.value, True))
                self.emit(MappingStartEvent(alias, node.tag, implicit,
                    flow_style=node.flow_style))
                for key, value in node.value:
                    self.serialize_node(key, node, None)
                    self.serialize_node(value, node, key)
                self.emit(MappingEndEvent())
            self.ascend_resolver()


########NEW FILE########
__FILENAME__ = tokens

class Token(object):
    def __init__(self, start_mark, end_mark):
        self.start_mark = start_mark
        self.end_mark = end_mark
    def __repr__(self):
        attributes = [key for key in self.__dict__
                if not key.endswith('_mark')]
        attributes.sort()
        arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
                for key in attributes])
        return '%s(%s)' % (self.__class__.__name__, arguments)

#class BOMToken(Token):
#    id = '<byte order mark>'

class DirectiveToken(Token):
    id = '<directive>'
    def __init__(self, name, value, start_mark, end_mark):
        self.name = name
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class DocumentStartToken(Token):
    id = '<document start>'

class DocumentEndToken(Token):
    id = '<document end>'

class StreamStartToken(Token):
    id = '<stream start>'
    def __init__(self, start_mark=None, end_mark=None,
            encoding=None):
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.encoding = encoding

class StreamEndToken(Token):
    id = '<stream end>'

class BlockSequenceStartToken(Token):
    id = '<block sequence start>'

class BlockMappingStartToken(Token):
    id = '<block mapping start>'

class BlockEndToken(Token):
    id = '<block end>'

class FlowSequenceStartToken(Token):
    id = '['

class FlowMappingStartToken(Token):
    id = '{'

class FlowSequenceEndToken(Token):
    id = ']'

class FlowMappingEndToken(Token):
    id = '}'

class KeyToken(Token):
    id = '?'

class ValueToken(Token):
    id = ':'

class BlockEntryToken(Token):
    id = '-'

class FlowEntryToken(Token):
    id = ','

class AliasToken(Token):
    id = '<alias>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class AnchorToken(Token):
    id = '<anchor>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class TagToken(Token):
    id = '<tag>'
    def __init__(self, value, start_mark, end_mark):
        self.value = value
        self.start_mark = start_mark
        self.end_mark = end_mark

class ScalarToken(Token):
    id = '<scalar>'
    def __init__(self, value, plain, start_mark, end_mark, style=None):
        self.value = value
        self.plain = plain
        self.start_mark = start_mark
        self.end_mark = end_mark
        self.style = style


########NEW FILE########
