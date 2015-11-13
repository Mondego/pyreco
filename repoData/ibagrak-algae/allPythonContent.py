__FILENAME__ = app
import webapp2

import settings
from handlers import index, api, common, email_auth, locale

routes = [webapp2.Route('/',                  handler = index.Index),
          webapp2.Route('/login_only',        handler = index.WithLogin),
          
          # email authentication routes
          webapp2.Route('/email-confirm',     handler = email_auth.EmailConfirm),
          webapp2.Route('/email-signin',      handler = email_auth.EmailAuthHandler, handler_method="signin_email"),
          webapp2.Route('/email-signup',      handler = email_auth.EmailAuthHandler, handler_method="signup_email"),
          
          # oauth authentication routes
          webapp2.Route('/auth/<provider>',   handler='handlers.oauth.AuthHandler:_simple_auth', name='auth_login'),
          webapp2.Route('/auth/<provider>/callback', handler='handlers.oauth.AuthHandler:_auth_callback', name='auth_callback'),
          
          # common logout
          webapp2.Route('/logout', handler='handlers.oauth.AuthHandler:logout', name='logout'),
          
          # i18n manual locale change
          webapp2.Route('/locale/<locale>', handler=locale.SetLocale),

          # REST API
          webapp2.Route('/rest/<obj_t>s', 
                        methods = ['PUT'], 
                        handler = common.BaseRESTHandler), # note the s at the end of URI
          webapp2.Route('/rest/<obj_t>/<identifier:\d+>', 
                        methods = ['GET', 'POST', 'DELETE'], 
                        handler = common.BaseRESTHandler), 
          
          # RPC API
          webapp2.Route('/rpc/<action>',               handler = api.RPCHandler), 
          ]                             
                                       
application = webapp2.WSGIApplication(routes,   
                                      debug = settings.DEBUG,
                                      config = settings.app_config)

application.error_handlers[404] = common.handle_404
application.error_handlers[500] = common.handle_500

def main():
    application.run()

########NEW FILE########
__FILENAME__ = model
'''
Created on Mar 29, 2012

@author: ibagrak
'''
import logging
from datetime import datetime
from webapp2_extras import json

import settings
import utils

from google.appengine.ext import db

class UnsupportedFieldTypeError(Exception): pass
class InvalidFieldValueError(Exception): pass

class RESTModel(db.Model):
    # implemented by subclasses
    @classmethod
    def validate(cls, kvs):
        pass
    
    # returns an entity based on id
    @classmethod
    def get(cls, i):
        return cls.get_by_id(i)
    
    # creates a new entity
    @classmethod
    def put(cls, kvs, entity = None):
        
        # prevent malicious overwriting of system attrs
        for k in kvs.keys(): 
            if not k in cls.properties():
                del kvs[k]
                continue
            
            v = cls.__dict__[k]
            
            # convert unicode values to datastore value types
            if isinstance(v, db.IntegerProperty): 
                kvs[k] = int(kvs[k])
            elif isinstance(v, db.FloatProperty):
                kvs[k] = float(kvs[k])
            elif isinstance(v, db.BooleanProperty):
                kvs[k] = True if kvs[k] == 'True' else False
            elif isinstance(v, db.StringProperty) or isinstance(v, db.TextProperty):
                kvs[k] = kvs[k]
            elif isinstance(v, db.DateProperty):
                kvs[k] = datetime.strptime(kvs[k], settings.DATE_FORMAT).date()
            elif isinstance(v, db.LinkProperty):
                kvs[k] = kvs[k] #TODO: verify URL
            elif isinstance(v, db.EmailProperty):
                kvs[k] = kvs[k] #TODO: verify email address
            else:
                raise UnsupportedFieldTypeError(v)
        
        # validate key/value pairs (semantic validation, assume type checking is finished)
        cls.validate(kvs)
        
        try:
            if not entity:
                entity = cls(**kvs)
            else: 
                for k in kvs.keys(): 
                    setattr(entity, k, kvs[k])

            db.put(entity)
        except Exception as e: 
            logging.error("Couldn't put entity: %s" % kvs)
            logging.error(e)
            return None
        
        return entity
    
    # updates existing entity based on id
    @classmethod
    def post(cls, i, kvs):
        entity = cls.get_by_id(i)
        return cls.put(kvs, entity = entity)
    
    # deletes an entity based on id
    @classmethod
    def delete1(cls, i):
        item = cls.get_by_id(i)
        if item: 
            item.delete()
            return True
        
        return False

    @property
    def str(self):
        return str(json.encode(utils.to_dict(self)))

def generate_model_form(cls, with_key = False):
    fields = filter(lambda x: issubclass(type(x[1]), db.Property), cls.__dict__.iteritems())
    
    #firstly, let's add key to the form and make it disabled
    form = [{'element' : 'text', 'label' : 'id', 'id' : 'id'}] if with_key else []
    
    for (k, t) in fields: 
        d = {'label' : k, 'id' : k}

        if isinstance(t, db.IntegerProperty) or isinstance(t, db.FloatProperty):
            d['element'] = 'text'
            d['class'] = 'number'
        
        elif isinstance(t, db.StringProperty):
            d['element'] = 'text'

        elif isinstance(t, db.TextProperty):
            d['element'] = 'textarea'
            d['class'] = 'textarea'

        elif isinstance(t, db.DateProperty):
            d['element'] = 'text'
            d['class'] = 'date'
            d['format'] = settings.DATE_FORMAT_HTML

        elif isinstance(t, db.BooleanProperty):
            d['element'] = 'checkbox'
            d['class'] = 'checkbox'

        elif isinstance(t, db.EmailProperty):
            d['element'] = 'text'
            d['class'] = 'email'

        elif isinstance(t, db.LinkProperty):
            d['element'] = 'text'
            d['class'] = 'url'

        else:
            raise UnsupportedFieldTypeError(k)
        
        form.append(d)
        
    return form
        
class Widget(RESTModel):
    int_field = db.IntegerProperty(required = True)
    boolean_field = db.BooleanProperty(required = True)
    string_field = db.StringProperty(required = True)
    text_field = db.TextProperty(required = True)
    email_field = db.EmailProperty(required = True)
    link_field = db.LinkProperty(required = True)
    date_field = db.DateProperty(required = True)

class EmailAddr(db.Model):
    email = db.EmailProperty(required = True)

########NEW FILE########
__FILENAME__ = api
from google.appengine.ext import db

import settings
from core import model
import common

class RPCHandler(common.BaseAPIHandler):
    
    def get(self, action, *args):
        args = self.request.GET
        
        for arg in args:
            args[arg] = self.request.get(arg)
        
        if not action in settings.APIS:
            self.prep_json_response(400, key = 'unsupported')
        else:    
            getattr(self, action)(args)

    def signup_mailing_list(self, args):
    	if 'email_mailinglist' in args:
            if not db.Query(model.EmailAddr).filter("email =", args['email_mailinglist']).get():
                db.put(model.EmailAddr(email = args['email_mailinglist']))
                
            self.prep_json_response(200, message = "Thanks for signing up!")
    	else:
    		self.prep_json_response(400, key = "noemail")

    @common.with_login
    def change_email_addr(self, args):
    	if 'email_change' in args: 
    		self.current_user.email = args['email_change']
    		self.current_user.put()

    		self.prep_json_response(200, message = "Email updated!")
    	else:
    		self.prep_json_response(400, key = "noemail")

class RESTHandler(common.BaseRESTHandler):
	
	def get(self, *args, **kwargs):
		pass

########NEW FILE########
__FILENAME__ = common
import logging
import cgi
import sys
import traceback
import hashlib
import os
from functools import wraps

import webapp2

from webapp2_extras import sessions, json, auth, i18n
from jinja2.runtime import TemplateNotFound

import settings
import utils
from handlers import jinja_environment

def get_json_error(code, key = None, message = None):
    logging.debug(json.encode(get_error(code, key = key, message = message)))
    return json.encode(get_error(code, key = key, message = message))

def get_error(code, key = None, message = None):
    if message:
        text = message
    elif key: 
        text = settings.API_CODES[code][key]
    
    if not message and not key:
        text = settings.API_CODES[code]
    
    # try to translate the text
    try:
      text = i18n.gettext(text)
    except Exception:
      pass
    
    return {'code' : code, 'response' : text }

def with_login(func):
	@wraps(func)
        def _with_login(*args, **kwargs):
            self = args[0]
            if not self.logged_in and issubclass(args[0].__class__, BaseAPIHandler):
                return args[0].prep_json_response(401)
            elif not args[0].logged_in and issubclass(args[0].__class__, BaseHandler):
                return args[0].prep_html_response("generic_error.html", { 'code' : 401 })

            func(*args, **kwargs)
        return _with_login

class BaseHandler(webapp2.RequestHandler):
    # if we don't have this then spammy head requests would clutter the error log
    def head(self):
        pass
        
    def handle_exception(self, exception, debug_mode):    
        logging.exception("handler exception: " + exception)
        self.response.clear()

        if debug_mode:
            lines = ''.join(traceback.format_exception(*sys.exc_info()))
            self.response.write('<pre>%s</pre>' % (cgi.escape(lines, quote=True)))
        else:
            # If the exception is a HTTPException, use its error code.
            # Otherwise use a generic 500 error code.
            if isinstance(exception, webapp2.HTTPException):
                code = exception.code
            else:
                code = 500
            
            self.response.set_status(code)
            self.response.out.write(jinja_environment.get_template("generic_error.html").render({'code' : 500}))
            
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        # Set the loale
        i18n.get_i18n().set_locale(self.locale)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
        
    @webapp2.cached_property
    def session(self):
        session = self.session_store.get_session()
        
        if len(session) == 0:
            for k, v in settings.COOKIE_TEMPLATE.iteritems(): 
                session[k] = v
        
            # initialize random session ID
            session['id'] = hashlib.md5(os.urandom(16)).hexdigest()
        # Returns a session using the default cookie key.
        return session
    
    @webapp2.cached_property
    def locale(self):
        if 'locale' in self.session:
            return self.session['locale']
        else:
            # find good locale from accept-language header
            header = self.request.headers.get('Accept-Language', '')
            locales = [locale.split(';')[0] for locale in header.split(',')]
            available = settings.AVAILABLE_LOCALES
            # 1. find exact match
            for locale in locales:
                if locale in available:
                    self.session['locale'] = locale
                    return locale
            # 2. find match in substring
            for locale in locales:
                len1 = len(locale)
                locales2 = [ l for l in available if l[0:(len1-1)] == locale ]
                if len(locales2)>0:
                    self.session['locale'] = locales2[0]
                    return locales2[0]
            # 3. find match in two-character match only
            for l2 in [ locale[0:2] for locale in locales ]:
                locales2 = [ l for l in available if l[0:2] == l2 ]
                if len(locales2)>0:
                    self.session['locale'] = locales2[0]
                    return locales2[0]
            # 4. return first available locale as fallback
            self.session['locale'] = available[0]
            return available[0]

    @webapp2.cached_property
    def auth(self):
        return auth.get_auth()
  
    @webapp2.cached_property
    def current_user(self):
        """Returns currently logged in user"""
        user_dict = self.auth.get_user_by_session()
        return self.auth.store.user_model.get_by_id(user_dict['user_id'])
      
    @webapp2.cached_property
    def logged_in(self):
        """Returns true if a user is currently logged in, false otherwise"""
        return self.auth.get_user_by_session() is not None
        
    def session_inc_pageviews(self):
        self.session['pageviews'] = self.session['pageviews'] + 1
    
    def prep_html_response(self, template_name, template_vars={}):
        # set header for IE to use edge (no "compatibility")
        self.response.headers.add_header("X-UA-Compatible", "IE=Edge,chrome=1")
        # Preset values for the template
        values = {
          'url_for'      : self.uri_for,
          'logged_in'    : self.logged_in,
          'current_user' : self.current_user if self.logged_in else None
        }
        
        # Add manually supplied template values
        values.update(template_vars)
        
        logging.info("session: %s" % self.session)
        logging.info("template vars: %s" % values)
        
        try:
            template = jinja_environment.get_template(template_name)
            self.response.out.write(template.render(**values))
        except TemplateNotFound:
            self.abort(404)

class BaseAPIHandler(BaseHandler):

    def handle_exception(self, exception, debug_mode):
        # Log the error.
        logging.exception(exception)

        # If the exception is a HTTPException, use its error code.
        # Otherwise use a generic 500 error code.
        if isinstance(exception, webapp2.HTTPException):
            self.response.set_status(exception.code)
        else:
            self.response.set_status(500)
            
        if debug_mode:
            lines = ''.join(traceback.format_exception(*sys.exc_info()))
            result = get_error(500, message = lines) 
        else:
            result = get_error(500, key = 'admin_required') 
            
        self.response.clear()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.encode(result))

    def put(self):
        pass
    
    def post(self):
        pass
    
    def delete(self):
        pass
    
    def prep_json_response(self, code, key = None, message = None):
        self.response.set_status(code)
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(get_json_error(code, key = key, message = message))

class BaseRESTHandler(BaseAPIHandler):
    
    @with_login
    def put(self, obj_t, *args):
        kvs = json.decode(self.request.body)
        
        # find model class
        cls = getattr(sys.modules['core.model'], obj_t)
        
        # dispatch put to that model class. all model classes need to a subclass model.RESTModel
        obj = utils.to_dict(cls.put(kvs))
        
        return self.prep_json_response(200, message = obj)

    def get(self, obj_t, identifier, *args):
        cls = getattr(sys.modules['core.model'], obj_t)
        
        # dispatch put to that model class. all model classes need to a subclass model.RESTModel
        obj = utils.to_dict(cls.get(int(identifier)))
        
        return self.prep_json_response(200, message = obj)

    def post(self, obj_t, identifier, *args):
        kvs = json.decode(self.request.body)

        # find model class
        cls = getattr(sys.modules['core.model'], obj_t)

        obj = utils.to_dict(cls.post(int(identifier), kvs))

        return self.prep_json_response(200, message = obj)
    
    @with_login
    def delete(self, obj_t, identifier, *args):
        cls = getattr(sys.modules['core.model'], obj_t)
        obj = cls.delete1(int(identifier))
        return self.prep_json_response(200, message = json.encode(obj))
    
def handle_404(request, response, exception):
    response.set_status(404)
    response.out.write(jinja_environment.get_template("404.html").render({'code' : 404}))

def handle_500(request, response, exception): 
    response.set_status(500)
    response.out.write(jinja_environment.get_template("generic_error.html").render({'code' : 500}))
    

    

########NEW FILE########
__FILENAME__ = email_auth
'''
Created on Jun 9, 2012

@author: ibagrak
'''
import re
import hashlib
import urllib
import logging

from google.appengine.api import mail

import settings
import common
import utils
            
class EmailConfirm(common.BaseHandler):
    def get(self, *args):
        kwargs = self.request.GET
        
        if not ('email' in kwargs and 'token' in kwargs):
            return self.prep_html_response('email_confirm.html', { 'confirm_status' : 'Invalid confirmation link.'})
        
        auth_id = '%s:%s' % ("own", kwargs['email'])
        
        if self.auth.store.user_model.validate_signup_token(kwargs['email'], kwargs['token']):     
            self.auth.store.user_model.delete_signup_token(kwargs['email'], kwargs['token'])
            user = self.auth.store.user_model.get_by_auth_id(auth_id)
            
            # confirm email by removing token field from user (hackish, need ability to check token existence) 
            if hasattr(user, 'token'):
                del user.token
                user.put()
            
            tvars = { 'confirm_status' : 'Email confirmed.'}
        else: 
            tvars = { 'confirm_status' : 'Email not confirmed.'}
        
        self.prep_html_response('email_confirm.html', tvars)

        
# email authentication is handled through form submission
#   -> /email/action=signin_email&email=<>&pw_hash=<>           : email signin  
#   <- json response   
#   -> /email/action=signup_email&email=<>&pw_hash=<>&nick=<>   : email signup
#   <- json response
class EmailAuthHandler(common.BaseAPIHandler):
    
    def signin_email(self, *args):
        kwargs = self.request.GET
        
        if not ('email' in kwargs and 'password' in kwargs):
            return self.prep_json_response(400, key = 'missing')
        
        auth_id = '%s:%s' % ("own", kwargs['email'])
        
        try: 
            user = self.auth.store.user_model.get_by_auth_password(auth_id, kwargs['password'])

            logging.info('Found existing user to log in')
            logging.info('user: %s' % user)
            
            # check if there is a signup token (we delete token when user confirms)
            if hasattr(user, 'token'):
                return self.prep_json_response(402, key = 'unconfirmed')
            
            logging.info('user: %s' % user)
            
            # set "remember me" cookie
            self.response.set_cookie(settings.APP_ID + '_login', 
                                     value = 'provider=email&username=%s' % user.username.encode(),
                                     max_age = 315360000, # 10 years
                                     path = '/') 
                
            # existing user. just log them in.
            self.auth.set_session(
              self.auth.store.user_to_dict(user)
            )
            
            return self.prep_json_response(200)
        except Exception as e:
            logging.info(type(e))
            return self.prep_json_response(400, key = 'email_password')
              
    def signup_email(self, *args):
        kwargs = self.request.GET
        
        if not ('email' in kwargs and 'username' in kwargs and 'password_raw' in kwargs):
            return self.prep_json_response(400, key = 'missing')
            
        if re.match(utils.email_re, kwargs['email']):
            auth_id = '%s:%s' % ("own", kwargs['email'])
            kwargs['pic'] = utils.to_gravatar_url(kwargs['email'])
            kwargs['profile'] = 'mailto:' + kwargs['email']
            
            logging.info('Creating a brand new user')

            # try to create a new user
            ok, user = self.auth.store.user_model.create_user(auth_id, **kwargs)
                
            logging.info('user: %s' % user)
                
            if ok:
                token = self.auth.store.user_model.create_signup_token(kwargs['email'])
                # there is no way to check if toekn still exists for a given email (i.e. email hasn't been
                # confirmed) without having the token to we cheat here and temporarily store it in user
                user.token = token
                user.put()
                
                link = "http://%s.appspot.com/email-confirm?token=%s&email=%s" % (settings.APP_ID, token, kwargs['email']) 
                mail.send_mail(sender = "%s Notifier <%s>" % (settings.APP_ID, settings.EMAIL_SENDER), 
                               to = kwargs['email'],
                               subject = "%s Email Confirmation" % settings.APP_ID, 
                               body = settings.EMAIL_CONFIRM_BODY % (kwargs['username'], link))
                logging.info("sending out confirm link: %s", link)
                return self.prep_json_response(200)
            else:
                return self.prep_json_response(402, key = 'duplicate')
        else:
            # invalid email
            return self.prep_json_response(400, key = 'email')

########NEW FILE########
__FILENAME__ = index
import common
import logging
from core import model

from google.appengine.ext import db

class Index(common.BaseHandler):
    
    def get(self):
        # demonstrates how session state can be changed        
        self.session_inc_pageviews()
        
        self.prep_html_response('index.html', 
                                { 'pageviews' : self.session['pageviews'], 
                                'widgets' : db.Query(model.Widget).order('-__key__').fetch(5), 
                                'form' : model.generate_model_form(model.Widget)})


class WithLogin(common.BaseHandler):
	@common.with_login
	def get(self):
		self.prep_html_response('index.html', 
                                { 'pageviews' : self.session['pageviews'], 
                                'widgets' : db.Query(model.Widget).order('-__key__').fetch(5), 
                                'form' : model.generate_model_form(model.Widget)})

########NEW FILE########
__FILENAME__ = locale
'''
Created on Aug 31, 2012

@author: helmuthb
'''
import settings
import common

class SetLocale(common.BaseHandler):
    """ Set the locale in the session (if locale is valid)
        then redirect back to referer
        copied from fishwebby @ stackoverflow
    """
    def get(self, locale):
        if locale in settings.AVAILABLE_LOCALES:
            self.session["locale"] = locale
        self.redirect(self.request.headers.get('Referer','/'))

########NEW FILE########
__FILENAME__ = oauth
'''
Created on Jun 14, 2012

@author: ibagrak
'''
import logging

from libs import simpleauth
import secrets
import common

class AuthHandler(common.BaseHandler, simpleauth.SimpleAuthHandler):
    """Authentication handler for OAuth 2.0, 1.0(a) and OpenID."""

    USER_ATTRS = {
       'google'   : {
         'picture': 'pic',
         'name'   : 'username',
         'link'   : 'profile'
       },
      'facebook' : {
        'id'     : lambda id: ('pic', 'http://graph.facebook.com/{0}/picture?type=large'.format(id)),
        'name'   : 'username',
        'link'   : 'profile'
      },
#      'windows_live': {
#        'avatar_url': 'avatar_url',
#        'name'      : 'name',
#        'link'      : 'link'
#      },
      'twitter'  : {
                    'profile_image_url': 'pic',
                    'screen_name'      : 'username',
                    'link'             : 'profile'
                    },
#      'linkedin' : {
#        'picture-url'       : 'avatar_url',
#        'first-name'        : 'name',
#        'public-profile-url': 'link'
#      },
#      'openid'   : {
#        'id'      : lambda id: ('avatar_url', '/img/missing-avatar.png'),
#        'nickname': 'name',
#        'email'   : 'link'
#      }
    }

    def _on_signin(self, data, auth_info, provider):
        """Callback whenever a new or existing user is logging in.
         data is a user info dictionary.
         auth_info contains access token or oauth token and secret.
        """
        auth_id = '%s:%s' % (provider, data['id'])
        logging.info('Looking for a user with id %s' % auth_id)

        user = self.auth.store.user_model.get_by_auth_id(auth_id)
        if user:
            logging.info('Found existing user to log in')
            # existing user. just log them in.
            self.auth.set_session(
              self.auth.store.user_to_dict(user)
            )

        else:
            # check whether there's a user currently logged in
            # then, create a new user if nobody's signed in,
            # otherwise add this auth_id to currently logged in user.
            if self.logged_in:
                logging.info('Updating currently logged in user')

                u = self.current_user
                u.auth_ids.append(auth_id)
                u.populate(**self._to_user_model_attrs(data, self.USER_ATTRS[provider]))
                u.put()

            else:
                logging.info('Creating a brand new user')

                ok, user = self.auth.store.user_model.create_user(
                  auth_id, **self._to_user_model_attrs(data, self.USER_ATTRS[provider])
                )
                
                logging.info('user: %s' % user)
                
                if ok:
                    self.auth.set_session(
                      self.auth.store.user_to_dict(user)
                    )

        self.redirect('/')

    def logout(self):
        self.auth.unset_session()
        self.redirect('/')

    def _callback_uri_for(self, provider):
        return self.uri_for('auth_callback', provider=provider, _full=True)

    def _get_consumer_info_for(self, provider):
        """Returns a tuple (key, secret) for auth init requests."""
        return secrets.AUTH_CONFIG[provider]

    def _to_user_model_attrs(self, data, attrs_map):
        user_attrs = {}
        for k, v in data.iteritems():
            if k in attrs_map:
                key = attrs_map[k]
                if isinstance(key, str):
                    user_attrs.setdefault(key, v)
                else:
                    user_attrs.setdefault(*key(v))

        return user_attrs

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Core locale representation and locale data access."""

import os
import pickle

from babel import localedata

__all__ = ['UnknownLocaleError', 'Locale', 'default_locale', 'negotiate_locale',
           'parse_locale']
__docformat__ = 'restructuredtext en'

_global_data = None

def get_global(key):
    """Return the dictionary for the given key in the global data.
    
    The global data is stored in the ``babel/global.dat`` file and contains
    information independent of individual locales.
    
    >>> get_global('zone_aliases')['UTC']
    'Etc/GMT'
    >>> get_global('zone_territories')['Europe/Berlin']
    'DE'
    
    :param key: the data key
    :return: the dictionary found in the global data under the given key
    :rtype: `dict`
    :since: version 0.9
    """
    global _global_data
    if _global_data is None:
        dirname = os.path.join(os.path.dirname(__file__))
        filename = os.path.join(dirname, 'global.dat')
        fileobj = open(filename, 'rb')
        try:
            _global_data = pickle.load(fileobj)
        finally:
            fileobj.close()
    return _global_data.get(key, {})


LOCALE_ALIASES = {
    'ar': 'ar_SY', 'bg': 'bg_BG', 'bs': 'bs_BA', 'ca': 'ca_ES', 'cs': 'cs_CZ', 
    'da': 'da_DK', 'de': 'de_DE', 'el': 'el_GR', 'en': 'en_US', 'es': 'es_ES', 
    'et': 'et_EE', 'fa': 'fa_IR', 'fi': 'fi_FI', 'fr': 'fr_FR', 'gl': 'gl_ES', 
    'he': 'he_IL', 'hu': 'hu_HU', 'id': 'id_ID', 'is': 'is_IS', 'it': 'it_IT', 
    'ja': 'ja_JP', 'km': 'km_KH', 'ko': 'ko_KR', 'lt': 'lt_LT', 'lv': 'lv_LV', 
    'mk': 'mk_MK', 'nl': 'nl_NL', 'nn': 'nn_NO', 'no': 'nb_NO', 'pl': 'pl_PL', 
    'pt': 'pt_PT', 'ro': 'ro_RO', 'ru': 'ru_RU', 'sk': 'sk_SK', 'sl': 'sl_SI', 
    'sv': 'sv_SE', 'th': 'th_TH', 'tr': 'tr_TR', 'uk': 'uk_UA'
}


class UnknownLocaleError(Exception):
    """Exception thrown when a locale is requested for which no locale data
    is available.
    """

    def __init__(self, identifier):
        """Create the exception.
        
        :param identifier: the identifier string of the unsupported locale
        """
        Exception.__init__(self, 'unknown locale %r' % identifier)
        self.identifier = identifier


class Locale(object):
    """Representation of a specific locale.
    
    >>> locale = Locale('en', 'US')
    >>> repr(locale)
    '<Locale "en_US">'
    >>> locale.display_name
    u'English (United States)'
    
    A `Locale` object can also be instantiated from a raw locale string:
    
    >>> locale = Locale.parse('en-US', sep='-')
    >>> repr(locale)
    '<Locale "en_US">'
    
    `Locale` objects provide access to a collection of locale data, such as
    territory and language names, number and date format patterns, and more:
    
    >>> locale.number_symbols['decimal']
    u'.'
    
    If a locale is requested for which no locale data is available, an
    `UnknownLocaleError` is raised:
    
    >>> Locale.parse('en_DE')
    Traceback (most recent call last):
        ...
    UnknownLocaleError: unknown locale 'en_DE'
    
    :see: `IETF RFC 3066 <http://www.ietf.org/rfc/rfc3066.txt>`_
    """

    def __init__(self, language, territory=None, script=None, variant=None):
        """Initialize the locale object from the given identifier components.
        
        >>> locale = Locale('en', 'US')
        >>> locale.language
        'en'
        >>> locale.territory
        'US'
        
        :param language: the language code
        :param territory: the territory (country or region) code
        :param script: the script code
        :param variant: the variant code
        :raise `UnknownLocaleError`: if no locale data is available for the
                                     requested locale
        """
        self.language = language
        self.territory = territory
        self.script = script
        self.variant = variant
        self.__data = None

        identifier = str(self)
        if not localedata.exists(identifier):
            raise UnknownLocaleError(identifier)

    def default(cls, category=None, aliases=LOCALE_ALIASES):
        """Return the system default locale for the specified category.
        
        >>> for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE']:
        ...     os.environ[name] = ''
        >>> os.environ['LANG'] = 'fr_FR.UTF-8'
        >>> Locale.default('LC_MESSAGES')
        <Locale "fr_FR">

        :param category: one of the ``LC_XXX`` environment variable names
        :param aliases: a dictionary of aliases for locale identifiers
        :return: the value of the variable, or any of the fallbacks
                 (``LANGUAGE``, ``LC_ALL``, ``LC_CTYPE``, and ``LANG``)
        :rtype: `Locale`
        :see: `default_locale`
        """
        return cls(default_locale(category, aliases=aliases))
    default = classmethod(default)

    def negotiate(cls, preferred, available, sep='_', aliases=LOCALE_ALIASES):
        """Find the best match between available and requested locale strings.
        
        >>> Locale.negotiate(['de_DE', 'en_US'], ['de_DE', 'de_AT'])
        <Locale "de_DE">
        >>> Locale.negotiate(['de_DE', 'en_US'], ['en', 'de'])
        <Locale "de">
        >>> Locale.negotiate(['de_DE', 'de'], ['en_US'])
        
        You can specify the character used in the locale identifiers to separate
        the differnet components. This separator is applied to both lists. Also,
        case is ignored in the comparison:
        
        >>> Locale.negotiate(['de-DE', 'de'], ['en-us', 'de-de'], sep='-')
        <Locale "de_DE">
        
        :param preferred: the list of locale identifers preferred by the user
        :param available: the list of locale identifiers available
        :param aliases: a dictionary of aliases for locale identifiers
        :return: the `Locale` object for the best match, or `None` if no match
                 was found
        :rtype: `Locale`
        :see: `negotiate_locale`
        """
        identifier = negotiate_locale(preferred, available, sep=sep,
                                      aliases=aliases)
        if identifier:
            return Locale.parse(identifier, sep=sep)
    negotiate = classmethod(negotiate)

    def parse(cls, identifier, sep='_'):
        """Create a `Locale` instance for the given locale identifier.
        
        >>> l = Locale.parse('de-DE', sep='-')
        >>> l.display_name
        u'Deutsch (Deutschland)'
        
        If the `identifier` parameter is not a string, but actually a `Locale`
        object, that object is returned:
        
        >>> Locale.parse(l)
        <Locale "de_DE">
        
        :param identifier: the locale identifier string
        :param sep: optional component separator
        :return: a corresponding `Locale` instance
        :rtype: `Locale`
        :raise `ValueError`: if the string does not appear to be a valid locale
                             identifier
        :raise `UnknownLocaleError`: if no locale data is available for the
                                     requested locale
        :see: `parse_locale`
        """
        if isinstance(identifier, basestring):
            return cls(*parse_locale(identifier, sep=sep))
        return identifier
    parse = classmethod(parse)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<Locale "%s">' % str(self)

    def __str__(self):
        return '_'.join(filter(None, [self.language, self.script,
                                      self.territory, self.variant]))

    def _data(self):
        if self.__data is None:
            self.__data = localedata.LocaleDataDict(localedata.load(str(self)))
        return self.__data
    _data = property(_data)

    def get_display_name(self, locale=None):
        """Return the display name of the locale using the given locale.
        
        The display name will include the language, territory, script, and
        variant, if those are specified.
        
        >>> Locale('zh', 'CN', script='Hans').get_display_name('en')
        u'Chinese (Simplified Han, China)'
        
        :param locale: the locale to use
        :return: the display name
        """
        if locale is None:
            locale = self
        locale = Locale.parse(locale)
        retval = locale.languages.get(self.language)
        if self.territory or self.script or self.variant:
            details = []
            if self.script:
                details.append(locale.scripts.get(self.script))
            if self.territory:
                details.append(locale.territories.get(self.territory))
            if self.variant:
                details.append(locale.variants.get(self.variant))
            details = filter(None, details)
            if details:
                retval += ' (%s)' % u', '.join(details)
        return retval

    display_name = property(get_display_name, doc="""\
        The localized display name of the locale.
        
        >>> Locale('en').display_name
        u'English'
        >>> Locale('en', 'US').display_name
        u'English (United States)'
        >>> Locale('sv').display_name
        u'svenska'
        
        :type: `unicode`
        """)

    def english_name(self):
        return self.get_display_name(Locale('en'))
    english_name = property(english_name, doc="""\
        The english display name of the locale.
        
        >>> Locale('de').english_name
        u'German'
        >>> Locale('de', 'DE').english_name
        u'German (Germany)'
        
        :type: `unicode`
        """)

    #{ General Locale Display Names

    def languages(self):
        return self._data['languages']
    languages = property(languages, doc="""\
        Mapping of language codes to translated language names.
        
        >>> Locale('de', 'DE').languages['ja']
        u'Japanisch'
        
        :type: `dict`
        :see: `ISO 639 <http://www.loc.gov/standards/iso639-2/>`_
        """)

    def scripts(self):
        return self._data['scripts']
    scripts = property(scripts, doc="""\
        Mapping of script codes to translated script names.
        
        >>> Locale('en', 'US').scripts['Hira']
        u'Hiragana'
        
        :type: `dict`
        :see: `ISO 15924 <http://www.evertype.com/standards/iso15924/>`_
        """)

    def territories(self):
        return self._data['territories']
    territories = property(territories, doc="""\
        Mapping of script codes to translated script names.
        
        >>> Locale('es', 'CO').territories['DE']
        u'Alemania'
        
        :type: `dict`
        :see: `ISO 3166 <http://www.iso.org/iso/en/prods-services/iso3166ma/>`_
        """)

    def variants(self):
        return self._data['variants']
    variants = property(variants, doc="""\
        Mapping of script codes to translated script names.
        
        >>> Locale('de', 'DE').variants['1901']
        u'Alte deutsche Rechtschreibung'
        
        :type: `dict`
        """)

    #{ Number Formatting

    def currencies(self):
        return self._data['currency_names']
    currencies = property(currencies, doc="""\
        Mapping of currency codes to translated currency names.
        
        >>> Locale('en').currencies['COP']
        u'Colombian Peso'
        >>> Locale('de', 'DE').currencies['COP']
        u'Kolumbianischer Peso'
        
        :type: `dict`
        """)

    def currency_symbols(self):
        return self._data['currency_symbols']
    currency_symbols = property(currency_symbols, doc="""\
        Mapping of currency codes to symbols.
        
        >>> Locale('en', 'US').currency_symbols['USD']
        u'$'
        >>> Locale('es', 'CO').currency_symbols['USD']
        u'US$'
        
        :type: `dict`
        """)

    def number_symbols(self):
        return self._data['number_symbols']
    number_symbols = property(number_symbols, doc="""\
        Symbols used in number formatting.
        
        >>> Locale('fr', 'FR').number_symbols['decimal']
        u','
        
        :type: `dict`
        """)

    def decimal_formats(self):
        return self._data['decimal_formats']
    decimal_formats = property(decimal_formats, doc="""\
        Locale patterns for decimal number formatting.
        
        >>> Locale('en', 'US').decimal_formats[None]
        <NumberPattern u'#,##0.###'>
        
        :type: `dict`
        """)

    def currency_formats(self):
        return self._data['currency_formats']
    currency_formats = property(currency_formats, doc=r"""\
        Locale patterns for currency number formatting.
        
        >>> print Locale('en', 'US').currency_formats[None]
        <NumberPattern u'\xa4#,##0.00'>
        
        :type: `dict`
        """)

    def percent_formats(self):
        return self._data['percent_formats']
    percent_formats = property(percent_formats, doc="""\
        Locale patterns for percent number formatting.
        
        >>> Locale('en', 'US').percent_formats[None]
        <NumberPattern u'#,##0%'>
        
        :type: `dict`
        """)

    def scientific_formats(self):
        return self._data['scientific_formats']
    scientific_formats = property(scientific_formats, doc="""\
        Locale patterns for scientific number formatting.
        
        >>> Locale('en', 'US').scientific_formats[None]
        <NumberPattern u'#E0'>
        
        :type: `dict`
        """)

    #{ Calendar Information and Date Formatting

    def periods(self):
        return self._data['periods']
    periods = property(periods, doc="""\
        Locale display names for day periods (AM/PM).
        
        >>> Locale('en', 'US').periods['am']
        u'AM'
        
        :type: `dict`
        """)

    def days(self):
        return self._data['days']
    days = property(days, doc="""\
        Locale display names for weekdays.
        
        >>> Locale('de', 'DE').days['format']['wide'][3]
        u'Donnerstag'
        
        :type: `dict`
        """)

    def months(self):
        return self._data['months']
    months = property(months, doc="""\
        Locale display names for months.
        
        >>> Locale('de', 'DE').months['format']['wide'][10]
        u'Oktober'
        
        :type: `dict`
        """)

    def quarters(self):
        return self._data['quarters']
    quarters = property(quarters, doc="""\
        Locale display names for quarters.
        
        >>> Locale('de', 'DE').quarters['format']['wide'][1]
        u'1. Quartal'
        
        :type: `dict`
        """)

    def eras(self):
        return self._data['eras']
    eras = property(eras, doc="""\
        Locale display names for eras.
        
        >>> Locale('en', 'US').eras['wide'][1]
        u'Anno Domini'
        >>> Locale('en', 'US').eras['abbreviated'][0]
        u'BC'
        
        :type: `dict`
        """)

    def time_zones(self):
        return self._data['time_zones']
    time_zones = property(time_zones, doc="""\
        Locale display names for time zones.
        
        >>> Locale('en', 'US').time_zones['Europe/London']['long']['daylight']
        u'British Summer Time'
        >>> Locale('en', 'US').time_zones['America/St_Johns']['city']
        u"St. John's"
        
        :type: `dict`
        """)

    def meta_zones(self):
        return self._data['meta_zones']
    meta_zones = property(meta_zones, doc="""\
        Locale display names for meta time zones.
        
        Meta time zones are basically groups of different Olson time zones that
        have the same GMT offset and daylight savings time.
        
        >>> Locale('en', 'US').meta_zones['Europe_Central']['long']['daylight']
        u'Central European Summer Time'
        
        :type: `dict`
        :since: version 0.9
        """)

    def zone_formats(self):
        return self._data['zone_formats']
    zone_formats = property(zone_formats, doc=r"""\
        Patterns related to the formatting of time zones.
        
        >>> Locale('en', 'US').zone_formats['fallback']
        u'%(1)s (%(0)s)'
        >>> Locale('pt', 'BR').zone_formats['region']
        u'Hor\xe1rio %s'
        
        :type: `dict`
        :since: version 0.9
        """)

    def first_week_day(self):
        return self._data['week_data']['first_day']
    first_week_day = property(first_week_day, doc="""\
        The first day of a week, with 0 being Monday.
        
        >>> Locale('de', 'DE').first_week_day
        0
        >>> Locale('en', 'US').first_week_day
        6
        
        :type: `int`
        """)

    def weekend_start(self):
        return self._data['week_data']['weekend_start']
    weekend_start = property(weekend_start, doc="""\
        The day the weekend starts, with 0 being Monday.
        
        >>> Locale('de', 'DE').weekend_start
        5
        
        :type: `int`
        """)

    def weekend_end(self):
        return self._data['week_data']['weekend_end']
    weekend_end = property(weekend_end, doc="""\
        The day the weekend ends, with 0 being Monday.
        
        >>> Locale('de', 'DE').weekend_end
        6
        
        :type: `int`
        """)

    def min_week_days(self):
        return self._data['week_data']['min_days']
    min_week_days = property(min_week_days, doc="""\
        The minimum number of days in a week so that the week is counted as the
        first week of a year or month.
        
        >>> Locale('de', 'DE').min_week_days
        4
        
        :type: `int`
        """)

    def date_formats(self):
        return self._data['date_formats']
    date_formats = property(date_formats, doc="""\
        Locale patterns for date formatting.
        
        >>> Locale('en', 'US').date_formats['short']
        <DateTimePattern u'M/d/yy'>
        >>> Locale('fr', 'FR').date_formats['long']
        <DateTimePattern u'd MMMM yyyy'>
        
        :type: `dict`
        """)

    def time_formats(self):
        return self._data['time_formats']
    time_formats = property(time_formats, doc="""\
        Locale patterns for time formatting.
        
        >>> Locale('en', 'US').time_formats['short']
        <DateTimePattern u'h:mm a'>
        >>> Locale('fr', 'FR').time_formats['long']
        <DateTimePattern u'HH:mm:ss z'>
        
        :type: `dict`
        """)

    def datetime_formats(self):
        return self._data['datetime_formats']
    datetime_formats = property(datetime_formats, doc="""\
        Locale patterns for datetime formatting.
        
        >>> Locale('en').datetime_formats[None]
        u'{1} {0}'
        >>> Locale('th').datetime_formats[None]
        u'{1}, {0}'
        
        :type: `dict`
        """)


def default_locale(category=None, aliases=LOCALE_ALIASES):
    """Returns the system default locale for a given category, based on
    environment variables.
    
    >>> for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE']:
    ...     os.environ[name] = ''
    >>> os.environ['LANG'] = 'fr_FR.UTF-8'
    >>> default_locale('LC_MESSAGES')
    'fr_FR'

    The "C" or "POSIX" pseudo-locales are treated as aliases for the
    "en_US_POSIX" locale:

    >>> os.environ['LC_MESSAGES'] = 'POSIX'
    >>> default_locale('LC_MESSAGES')
    'en_US_POSIX'

    :param category: one of the ``LC_XXX`` environment variable names
    :param aliases: a dictionary of aliases for locale identifiers
    :return: the value of the variable, or any of the fallbacks (``LANGUAGE``,
             ``LC_ALL``, ``LC_CTYPE``, and ``LANG``)
    :rtype: `str`
    """
    varnames = (category, 'LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LANG')
    for name in filter(None, varnames):
        locale = os.getenv(name)
        if locale:
            if name == 'LANGUAGE' and ':' in locale:
                # the LANGUAGE variable may contain a colon-separated list of
                # language codes; we just pick the language on the list
                locale = locale.split(':')[0]
            if locale in ('C', 'POSIX'):
                locale = 'en_US_POSIX'
            elif aliases and locale in aliases:
                locale = aliases[locale]
            try:
                return '_'.join(filter(None, parse_locale(locale)))
            except ValueError:
                pass

def negotiate_locale(preferred, available, sep='_', aliases=LOCALE_ALIASES):
    """Find the best match between available and requested locale strings.
    
    >>> negotiate_locale(['de_DE', 'en_US'], ['de_DE', 'de_AT'])
    'de_DE'
    >>> negotiate_locale(['de_DE', 'en_US'], ['en', 'de'])
    'de'
    
    Case is ignored by the algorithm, the result uses the case of the preferred
    locale identifier:
    
    >>> negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at'])
    'de_DE'
    
    >>> negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at'])
    'de_DE'
    
    By default, some web browsers unfortunately do not include the territory
    in the locale identifier for many locales, and some don't even allow the
    user to easily add the territory. So while you may prefer using qualified
    locale identifiers in your web-application, they would not normally match
    the language-only locale sent by such browsers. To workaround that, this
    function uses a default mapping of commonly used langauge-only locale
    identifiers to identifiers including the territory:
    
    >>> negotiate_locale(['ja', 'en_US'], ['ja_JP', 'en_US'])
    'ja_JP'
    
    Some browsers even use an incorrect or outdated language code, such as "no"
    for Norwegian, where the correct locale identifier would actually be "nb_NO"
    (Bokmål) or "nn_NO" (Nynorsk). The aliases are intended to take care of
    such cases, too:
    
    >>> negotiate_locale(['no', 'sv'], ['nb_NO', 'sv_SE'])
    'nb_NO'
    
    You can override this default mapping by passing a different `aliases`
    dictionary to this function, or you can bypass the behavior althogher by
    setting the `aliases` parameter to `None`.
    
    :param preferred: the list of locale strings preferred by the user
    :param available: the list of locale strings available
    :param sep: character that separates the different parts of the locale
                strings
    :param aliases: a dictionary of aliases for locale identifiers
    :return: the locale identifier for the best match, or `None` if no match
             was found
    :rtype: `str`
    """
    available = [a.lower() for a in available if a]
    for locale in preferred:
        ll = locale.lower()
        if ll in available:
            return locale
        if aliases:
            alias = aliases.get(ll)
            if alias:
                alias = alias.replace('_', sep)
                if alias.lower() in available:
                    return alias
        parts = locale.split(sep)
        if len(parts) > 1 and parts[0].lower() in available:
            return parts[0]
    return None

def parse_locale(identifier, sep='_'):
    """Parse a locale identifier into a tuple of the form::
    
      ``(language, territory, script, variant)``
    
    >>> parse_locale('zh_CN')
    ('zh', 'CN', None, None)
    >>> parse_locale('zh_Hans_CN')
    ('zh', 'CN', 'Hans', None)
    
    The default component separator is "_", but a different separator can be
    specified using the `sep` parameter:
    
    >>> parse_locale('zh-CN', sep='-')
    ('zh', 'CN', None, None)
    
    If the identifier cannot be parsed into a locale, a `ValueError` exception
    is raised:
    
    >>> parse_locale('not_a_LOCALE_String')
    Traceback (most recent call last):
      ...
    ValueError: 'not_a_LOCALE_String' is not a valid locale identifier
    
    Encoding information and locale modifiers are removed from the identifier:
    
    >>> parse_locale('it_IT@euro')
    ('it', 'IT', None, None)
    >>> parse_locale('en_US.UTF-8')
    ('en', 'US', None, None)
    >>> parse_locale('de_DE.iso885915@euro')
    ('de', 'DE', None, None)
    
    :param identifier: the locale identifier string
    :param sep: character that separates the different components of the locale
                identifier
    :return: the ``(language, territory, script, variant)`` tuple
    :rtype: `tuple`
    :raise `ValueError`: if the string does not appear to be a valid locale
                         identifier
    
    :see: `IETF RFC 4646 <http://www.ietf.org/rfc/rfc4646.txt>`_
    """
    if '.' in identifier:
        # this is probably the charset/encoding, which we don't care about
        identifier = identifier.split('.', 1)[0]
    if '@' in identifier:
        # this is a locale modifier such as @euro, which we don't care about
        # either
        identifier = identifier.split('@', 1)[0]

    parts = identifier.split(sep)
    lang = parts.pop(0).lower()
    if not lang.isalpha():
        raise ValueError('expected only letters, got %r' % lang)

    script = territory = variant = None
    if parts:
        if len(parts[0]) == 4 and parts[0].isalpha():
            script = parts.pop(0).title()

    if parts:
        if len(parts[0]) == 2 and parts[0].isalpha():
            territory = parts.pop(0).upper()
        elif len(parts[0]) == 3 and parts[0].isdigit():
            territory = parts.pop(0)

    if parts:
        if len(parts[0]) == 4 and parts[0][0].isdigit() or \
                len(parts[0]) >= 5 and parts[0][0].isalpha():
            variant = parts.pop()

    if parts:
        raise ValueError('%r is not a valid locale identifier' % identifier)

    return lang, territory, script, variant

########NEW FILE########
__FILENAME__ = dates
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Locale dependent formatting and parsing of dates and times.

The default locale for the functions in this module is determined by the
following environment variables, in that order:

 * ``LC_TIME``,
 * ``LC_ALL``, and
 * ``LANG``
"""

from datetime import date, datetime, time, timedelta, tzinfo
import re

from babel.core import default_locale, get_global, Locale
from babel.util import UTC

__all__ = ['format_date', 'format_datetime', 'format_time',
           'get_timezone_name', 'parse_date', 'parse_datetime', 'parse_time']
__docformat__ = 'restructuredtext en'

LC_TIME = default_locale('LC_TIME')

# Aliases for use in scopes where the modules are shadowed by local variables
date_ = date
datetime_ = datetime
time_ = time

def get_period_names(locale=LC_TIME):
    """Return the names for day periods (AM/PM) used by the locale.
    
    >>> get_period_names(locale='en_US')['am']
    u'AM'
    
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of period names
    :rtype: `dict`
    """
    return Locale.parse(locale).periods

def get_day_names(width='wide', context='format', locale=LC_TIME):
    """Return the day names used by the locale for the specified format.
    
    >>> get_day_names('wide', locale='en_US')[1]
    u'Tuesday'
    >>> get_day_names('abbreviated', locale='es')[1]
    u'mar'
    >>> get_day_names('narrow', context='stand-alone', locale='de_DE')[1]
    u'D'
    
    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of day names
    :rtype: `dict`
    """
    return Locale.parse(locale).days[context][width]

def get_month_names(width='wide', context='format', locale=LC_TIME):
    """Return the month names used by the locale for the specified format.
    
    >>> get_month_names('wide', locale='en_US')[1]
    u'January'
    >>> get_month_names('abbreviated', locale='es')[1]
    u'ene'
    >>> get_month_names('narrow', context='stand-alone', locale='de_DE')[1]
    u'J'
    
    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of month names
    :rtype: `dict`
    """
    return Locale.parse(locale).months[context][width]

def get_quarter_names(width='wide', context='format', locale=LC_TIME):
    """Return the quarter names used by the locale for the specified format.
    
    >>> get_quarter_names('wide', locale='en_US')[1]
    u'1st quarter'
    >>> get_quarter_names('abbreviated', locale='de_DE')[1]
    u'Q1'
    
    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of quarter names
    :rtype: `dict`
    """
    return Locale.parse(locale).quarters[context][width]

def get_era_names(width='wide', locale=LC_TIME):
    """Return the era names used by the locale for the specified format.
    
    >>> get_era_names('wide', locale='en_US')[1]
    u'Anno Domini'
    >>> get_era_names('abbreviated', locale='de_DE')[1]
    u'n. Chr.'
    
    :param width: the width to use, either "wide", "abbreviated", or "narrow"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of era names
    :rtype: `dict`
    """
    return Locale.parse(locale).eras[width]

def get_date_format(format='medium', locale=LC_TIME):
    """Return the date formatting patterns used by the locale for the specified
    format.
    
    >>> get_date_format(locale='en_US')
    <DateTimePattern u'MMM d, yyyy'>
    >>> get_date_format('full', locale='de_DE')
    <DateTimePattern u'EEEE, d. MMMM yyyy'>
    
    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    :return: the date format pattern
    :rtype: `DateTimePattern`
    """
    return Locale.parse(locale).date_formats[format]

def get_datetime_format(format='medium', locale=LC_TIME):
    """Return the datetime formatting patterns used by the locale for the
    specified format.
    
    >>> get_datetime_format(locale='en_US')
    u'{1} {0}'
    
    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    :return: the datetime format pattern
    :rtype: `unicode`
    """
    patterns = Locale.parse(locale).datetime_formats
    if format not in patterns:
        format = None
    return patterns[format]

def get_time_format(format='medium', locale=LC_TIME):
    """Return the time formatting patterns used by the locale for the specified
    format.
    
    >>> get_time_format(locale='en_US')
    <DateTimePattern u'h:mm:ss a'>
    >>> get_time_format('full', locale='de_DE')
    <DateTimePattern u'HH:mm:ss v'>
    
    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    :return: the time format pattern
    :rtype: `DateTimePattern`
    """
    return Locale.parse(locale).time_formats[format]

def get_timezone_gmt(datetime=None, width='long', locale=LC_TIME):
    """Return the timezone associated with the given `datetime` object formatted
    as string indicating the offset from GMT.
    
    >>> dt = datetime(2007, 4, 1, 15, 30)
    >>> get_timezone_gmt(dt, locale='en')
    u'GMT+00:00'
    
    >>> from pytz import timezone
    >>> tz = timezone('America/Los_Angeles')
    >>> dt = datetime(2007, 4, 1, 15, 30, tzinfo=tz)
    >>> get_timezone_gmt(dt, locale='en')
    u'GMT-08:00'
    >>> get_timezone_gmt(dt, 'short', locale='en')
    u'-0800'
    
    The long format depends on the locale, for example in France the acronym
    UTC string is used instead of GMT:
    
    >>> get_timezone_gmt(dt, 'long', locale='fr_FR')
    u'UTC-08:00'
    
    :param datetime: the ``datetime`` object; if `None`, the current date and
                     time in UTC is used
    :param width: either "long" or "short"
    :param locale: the `Locale` object, or a locale string
    :return: the GMT offset representation of the timezone
    :rtype: `unicode`
    :since: version 0.9
    """
    if datetime is None:
        datetime = datetime_.utcnow()
    elif isinstance(datetime, (int, long)):
        datetime = datetime_.utcfromtimestamp(datetime).time()
    if datetime.tzinfo is None:
        datetime = datetime.replace(tzinfo=UTC)
    locale = Locale.parse(locale)

    offset = datetime.tzinfo.utcoffset(datetime)
    seconds = offset.days * 24 * 60 * 60 + offset.seconds
    hours, seconds = divmod(seconds, 3600)
    if width == 'short':
        pattern = u'%+03d%02d'
    else:
        pattern = locale.zone_formats['gmt'] % '%+03d:%02d'
    return pattern % (hours, seconds // 60)

def get_timezone_location(dt_or_tzinfo=None, locale=LC_TIME):
    """Return a representation of the given timezone using "location format".
    
    The result depends on both the local display name of the country and the
    city associated with the time zone:
    
    >>> from pytz import timezone
    >>> tz = timezone('America/St_Johns')
    >>> get_timezone_location(tz, locale='de_DE')
    u"Kanada (St. John's)"
    >>> tz = timezone('America/Mexico_City')
    >>> get_timezone_location(tz, locale='de_DE')
    u'Mexiko (Mexiko-Stadt)'
    
    If the timezone is associated with a country that uses only a single
    timezone, just the localized country name is returned:
    
    >>> tz = timezone('Europe/Berlin')
    >>> get_timezone_name(tz, locale='de_DE')
    u'Deutschland'
    
    :param dt_or_tzinfo: the ``datetime`` or ``tzinfo`` object that determines
                         the timezone; if `None`, the current date and time in
                         UTC is assumed
    :param locale: the `Locale` object, or a locale string
    :return: the localized timezone name using location format
    :rtype: `unicode`
    :since: version 0.9
    """
    if dt_or_tzinfo is None or isinstance(dt_or_tzinfo, (int, long)):
        dt = None
        tzinfo = UTC
    elif isinstance(dt_or_tzinfo, (datetime, time)):
        dt = dt_or_tzinfo
        if dt.tzinfo is not None:
            tzinfo = dt.tzinfo
        else:
            tzinfo = UTC
    else:
        dt = None
        tzinfo = dt_or_tzinfo
    locale = Locale.parse(locale)

    if hasattr(tzinfo, 'zone'):
        zone = tzinfo.zone
    else:
        zone = tzinfo.tzname(dt or datetime.utcnow())

    # Get the canonical time-zone code
    zone = get_global('zone_aliases').get(zone, zone)

    info = locale.time_zones.get(zone, {})

    # Otherwise, if there is only one timezone for the country, return the
    # localized country name
    region_format = locale.zone_formats['region']
    territory = get_global('zone_territories').get(zone)
    if territory not in locale.territories:
        territory = 'ZZ' # invalid/unknown
    territory_name = locale.territories[territory]
    if territory and len(get_global('territory_zones').get(territory, [])) == 1:
        return region_format % (territory_name)

    # Otherwise, include the city in the output
    fallback_format = locale.zone_formats['fallback']
    if 'city' in info:
        city_name = info['city']
    else:
        metazone = get_global('meta_zones').get(zone)
        metazone_info = locale.meta_zones.get(metazone, {})
        if 'city' in metazone_info:
            city_name = metainfo['city']
        elif '/' in zone:
            city_name = zone.split('/', 1)[1].replace('_', ' ')
        else:
            city_name = zone.replace('_', ' ')

    return region_format % (fallback_format % {
        '0': city_name,
        '1': territory_name
    })

def get_timezone_name(dt_or_tzinfo=None, width='long', uncommon=False,
                      locale=LC_TIME):
    r"""Return the localized display name for the given timezone. The timezone
    may be specified using a ``datetime`` or `tzinfo` object.
    
    >>> from pytz import timezone
    >>> dt = time(15, 30, tzinfo=timezone('America/Los_Angeles'))
    >>> get_timezone_name(dt, locale='en_US')
    u'Pacific Standard Time'
    >>> get_timezone_name(dt, width='short', locale='en_US')
    u'PST'
    
    If this function gets passed only a `tzinfo` object and no concrete
    `datetime`,  the returned display name is indenpendent of daylight savings
    time. This can be used for example for selecting timezones, or to set the
    time of events that recur across DST changes:
    
    >>> tz = timezone('America/Los_Angeles')
    >>> get_timezone_name(tz, locale='en_US')
    u'Pacific Time'
    >>> get_timezone_name(tz, 'short', locale='en_US')
    u'PT'
    
    If no localized display name for the timezone is available, and the timezone
    is associated with a country that uses only a single timezone, the name of
    that country is returned, formatted according to the locale:
    
    >>> tz = timezone('Europe/Berlin')
    >>> get_timezone_name(tz, locale='de_DE')
    u'Deutschland'
    >>> get_timezone_name(tz, locale='pt_BR')
    u'Hor\xe1rio Alemanha'
    
    On the other hand, if the country uses multiple timezones, the city is also
    included in the representation:
    
    >>> tz = timezone('America/St_Johns')
    >>> get_timezone_name(tz, locale='de_DE')
    u"Kanada (St. John's)"
    
    The `uncommon` parameter can be set to `True` to enable the use of timezone
    representations that are not commonly used by the requested locale. For
    example, while in French the central European timezone is usually
    abbreviated as "HEC", in Canadian French, this abbreviation is not in
    common use, so a generic name would be chosen by default:
    
    >>> tz = timezone('Europe/Paris')
    >>> get_timezone_name(tz, 'short', locale='fr_CA')
    u'France'
    >>> get_timezone_name(tz, 'short', uncommon=True, locale='fr_CA')
    u'HEC'
    
    :param dt_or_tzinfo: the ``datetime`` or ``tzinfo`` object that determines
                         the timezone; if a ``tzinfo`` object is used, the
                         resulting display name will be generic, i.e.
                         independent of daylight savings time; if `None`, the
                         current date in UTC is assumed
    :param width: either "long" or "short"
    :param uncommon: whether even uncommon timezone abbreviations should be used
    :param locale: the `Locale` object, or a locale string
    :return: the timezone display name
    :rtype: `unicode`
    :since: version 0.9
    :see:  `LDML Appendix J: Time Zone Display Names
            <http://www.unicode.org/reports/tr35/#Time_Zone_Fallback>`_
    """
    if dt_or_tzinfo is None or isinstance(dt_or_tzinfo, (int, long)):
        dt = None
        tzinfo = UTC
    elif isinstance(dt_or_tzinfo, (datetime, time)):
        dt = dt_or_tzinfo
        if dt.tzinfo is not None:
            tzinfo = dt.tzinfo
        else:
            tzinfo = UTC
    else:
        dt = None
        tzinfo = dt_or_tzinfo
    locale = Locale.parse(locale)

    if hasattr(tzinfo, 'zone'):
        zone = tzinfo.zone
    else:
        zone = tzinfo.tzname(dt)

    # Get the canonical time-zone code
    zone = get_global('zone_aliases').get(zone, zone)

    info = locale.time_zones.get(zone, {})
    # Try explicitly translated zone names first
    if width in info:
        if dt is None:
            field = 'generic'
        else:
            dst = tzinfo.dst(dt)
            if dst is None:
                field = 'generic'
            elif dst == 0:
                field = 'standard'
            else:
                field = 'daylight'
        if field in info[width]:
            return info[width][field]

    metazone = get_global('meta_zones').get(zone)
    if metazone:
        metazone_info = locale.meta_zones.get(metazone, {})
        if width in metazone_info and (uncommon or metazone_info.get('common')):
            if dt is None:
                field = 'generic'
            else:
                field = tzinfo.dst(dt) and 'daylight' or 'standard'
            if field in metazone_info[width]:
                return metazone_info[width][field]

    # If we have a concrete datetime, we assume that the result can't be
    # independent of daylight savings time, so we return the GMT offset
    if dt is not None:
        return get_timezone_gmt(dt, width=width, locale=locale)

    return get_timezone_location(dt_or_tzinfo, locale=locale)

def format_date(date=None, format='medium', locale=LC_TIME):
    """Return a date formatted according to the given pattern.
    
    >>> d = date(2007, 04, 01)
    >>> format_date(d, locale='en_US')
    u'Apr 1, 2007'
    >>> format_date(d, format='full', locale='de_DE')
    u'Sonntag, 1. April 2007'
    
    If you don't want to use the locale default formats, you can specify a
    custom date pattern:
    
    >>> format_date(d, "EEE, MMM d, ''yy", locale='en')
    u"Sun, Apr 1, '07"
    
    :param date: the ``date`` or ``datetime`` object; if `None`, the current
                 date is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param locale: a `Locale` object or a locale identifier
    :rtype: `unicode`
    
    :note: If the pattern contains time fields, an `AttributeError` will be
           raised when trying to apply the formatting. This is also true if
           the value of ``date`` parameter is actually a ``datetime`` object,
           as this function automatically converts that to a ``date``.
    """
    if date is None:
        date = date_.today()
    elif isinstance(date, datetime):
        date = date.date()

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        format = get_date_format(format, locale=locale)
    pattern = parse_pattern(format)
    return pattern.apply(date, locale)

def format_datetime(datetime=None, format='medium', tzinfo=None,
                    locale=LC_TIME):
    """Return a date formatted according to the given pattern.
    
    >>> dt = datetime(2007, 04, 01, 15, 30)
    >>> format_datetime(dt, locale='en_US')
    u'Apr 1, 2007 3:30:00 PM'
    
    For any pattern requiring the display of the time-zone, the third-party
    ``pytz`` package is needed to explicitly specify the time-zone:
    
    >>> from pytz import timezone
    >>> format_datetime(dt, 'full', tzinfo=timezone('Europe/Paris'),
    ...                 locale='fr_FR')
    u'dimanche 1 avril 2007 17:30:00 HEC'
    >>> format_datetime(dt, "yyyy.MM.dd G 'at' HH:mm:ss zzz",
    ...                 tzinfo=timezone('US/Eastern'), locale='en')
    u'2007.04.01 AD at 11:30:00 EDT'
    
    :param datetime: the `datetime` object; if `None`, the current date and
                     time is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the timezone to apply to the time for display
    :param locale: a `Locale` object or a locale identifier
    :rtype: `unicode`
    """
    if datetime is None:
        datetime = datetime_.utcnow()
    elif isinstance(datetime, (int, long)):
        datetime = datetime_.utcfromtimestamp(datetime)
    elif isinstance(datetime, time):
        datetime = datetime_.combine(date.today(), datetime)
    if datetime.tzinfo is None:
        datetime = datetime.replace(tzinfo=UTC)
    if tzinfo is not None:
        datetime = datetime.astimezone(tzinfo)
        if hasattr(tzinfo, 'normalize'): # pytz
            datetime = tzinfo.normalize(datetime)

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        return get_datetime_format(format, locale=locale) \
            .replace('{0}', format_time(datetime, format, tzinfo=None,
                                        locale=locale)) \
            .replace('{1}', format_date(datetime, format, locale=locale))
    else:
        return parse_pattern(format).apply(datetime, locale)

def format_time(time=None, format='medium', tzinfo=None, locale=LC_TIME):
    """Return a time formatted according to the given pattern.
    
    >>> t = time(15, 30)
    >>> format_time(t, locale='en_US')
    u'3:30:00 PM'
    >>> format_time(t, format='short', locale='de_DE')
    u'15:30'
    
    If you don't want to use the locale default formats, you can specify a
    custom time pattern:
    
    >>> format_time(t, "hh 'o''clock' a", locale='en')
    u"03 o'clock PM"
    
    For any pattern requiring the display of the time-zone, the third-party
    ``pytz`` package is needed to explicitly specify the time-zone:
    
    >>> from pytz import timezone
    >>> t = datetime(2007, 4, 1, 15, 30)
    >>> tzinfo = timezone('Europe/Paris')
    >>> t = tzinfo.localize(t)
    >>> format_time(t, format='full', tzinfo=tzinfo, locale='fr_FR')
    u'15:30:00 HEC'
    >>> format_time(t, "hh 'o''clock' a, zzzz", tzinfo=timezone('US/Eastern'),
    ...             locale='en')
    u"09 o'clock AM, Eastern Daylight Time"
    
    As that example shows, when this function gets passed a
    ``datetime.datetime`` value, the actual time in the formatted string is
    adjusted to the timezone specified by the `tzinfo` parameter. If the
    ``datetime`` is "naive" (i.e. it has no associated timezone information),
    it is assumed to be in UTC.
    
    These timezone calculations are **not** performed if the value is of type
    ``datetime.time``, as without date information there's no way to determine
    what a given time would translate to in a different timezone without
    information about whether daylight savings time is in effect or not. This
    means that time values are left as-is, and the value of the `tzinfo`
    parameter is only used to display the timezone name if needed:
    
    >>> t = time(15, 30)
    >>> format_time(t, format='full', tzinfo=timezone('Europe/Paris'),
    ...             locale='fr_FR')
    u'15:30:00 HEC'
    >>> format_time(t, format='full', tzinfo=timezone('US/Eastern'),
    ...             locale='en_US')
    u'3:30:00 PM ET'
    
    :param time: the ``time`` or ``datetime`` object; if `None`, the current
                 time in UTC is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the time-zone to apply to the time for display
    :param locale: a `Locale` object or a locale identifier
    :rtype: `unicode`
    
    :note: If the pattern contains date fields, an `AttributeError` will be
           raised when trying to apply the formatting. This is also true if
           the value of ``time`` parameter is actually a ``datetime`` object,
           as this function automatically converts that to a ``time``.
    """
    if time is None:
        time = datetime.utcnow()
    elif isinstance(time, (int, long)):
        time = datetime.utcfromtimestamp(time)
    if time.tzinfo is None:
        time = time.replace(tzinfo=UTC)
    if isinstance(time, datetime):
        if tzinfo is not None:
            time = time.astimezone(tzinfo)
            if hasattr(tzinfo, 'normalize'): # pytz
                time = tzinfo.normalize(time)
        time = time.timetz()
    elif tzinfo is not None:
        time = time.replace(tzinfo=tzinfo)

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        format = get_time_format(format, locale=locale)
    return parse_pattern(format).apply(time, locale)

def parse_date(string, locale=LC_TIME):
    """Parse a date from a string.
    
    This function uses the date format for the locale as a hint to determine
    the order in which the date fields appear in the string.
    
    >>> parse_date('4/1/04', locale='en_US')
    datetime.date(2004, 4, 1)
    >>> parse_date('01.04.2004', locale='de_DE')
    datetime.date(2004, 4, 1)
    
    :param string: the string containing the date
    :param locale: a `Locale` object or a locale identifier
    :return: the parsed date
    :rtype: `date`
    """
    # TODO: try ISO format first?
    format = get_date_format(locale=locale).pattern.lower()
    year_idx = format.index('y')
    month_idx = format.index('m')
    if month_idx < 0:
        month_idx = format.index('l')
    day_idx = format.index('d')

    indexes = [(year_idx, 'Y'), (month_idx, 'M'), (day_idx, 'D')]
    indexes.sort()
    indexes = dict([(item[1], idx) for idx, item in enumerate(indexes)])

    # FIXME: this currently only supports numbers, but should also support month
    #        names, both in the requested locale, and english

    numbers = re.findall('(\d+)', string)
    year = numbers[indexes['Y']]
    if len(year) == 2:
        year = 2000 + int(year)
    else:
        year = int(year)
    month = int(numbers[indexes['M']])
    day = int(numbers[indexes['D']])
    if month > 12:
        month, day = day, month
    return date(year, month, day)

def parse_datetime(string, locale=LC_TIME):
    """Parse a date and time from a string.
    
    This function uses the date and time formats for the locale as a hint to
    determine the order in which the time fields appear in the string.
    
    :param string: the string containing the date and time
    :param locale: a `Locale` object or a locale identifier
    :return: the parsed date/time
    :rtype: `datetime`
    """
    raise NotImplementedError

def parse_time(string, locale=LC_TIME):
    """Parse a time from a string.
    
    This function uses the time format for the locale as a hint to determine
    the order in which the time fields appear in the string.
    
    >>> parse_time('15:30:00', locale='en_US')
    datetime.time(15, 30)
    
    :param string: the string containing the time
    :param locale: a `Locale` object or a locale identifier
    :return: the parsed time
    :rtype: `time`
    """
    # TODO: try ISO format first?
    format = get_time_format(locale=locale).pattern.lower()
    hour_idx = format.index('h')
    if hour_idx < 0:
        hour_idx = format.index('k')
    min_idx = format.index('m')
    sec_idx = format.index('s')

    indexes = [(hour_idx, 'H'), (min_idx, 'M'), (sec_idx, 'S')]
    indexes.sort()
    indexes = dict([(item[1], idx) for idx, item in enumerate(indexes)])

    # FIXME: support 12 hour clock, and 0-based hour specification
    #        and seconds should be optional, maybe minutes too
    #        oh, and time-zones, of course

    numbers = re.findall('(\d+)', string)
    hour = int(numbers[indexes['H']])
    minute = int(numbers[indexes['M']])
    second = int(numbers[indexes['S']])
    return time(hour, minute, second)


class DateTimePattern(object):

    def __init__(self, pattern, format):
        self.pattern = pattern
        self.format = format

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.pattern)

    def __unicode__(self):
        return self.pattern

    def __mod__(self, other):
        assert type(other) is DateTimeFormat
        return self.format % other

    def apply(self, datetime, locale):
        return self % DateTimeFormat(datetime, locale)


class DateTimeFormat(object):

    def __init__(self, value, locale):
        assert isinstance(value, (date, datetime, time))
        if isinstance(value, (datetime, time)) and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        self.value = value
        self.locale = Locale.parse(locale)

    def __getitem__(self, name):
        char = name[0]
        num = len(name)
        if char == 'G':
            return self.format_era(char, num)
        elif char in ('y', 'Y', 'u'):
            return self.format_year(char, num)
        elif char in ('Q', 'q'):
            return self.format_quarter(char, num)
        elif char in ('M', 'L'):
            return self.format_month(char, num)
        elif char in ('w', 'W'):
            return self.format_week(char, num)
        elif char == 'd':
            return self.format(self.value.day, num)
        elif char == 'D':
            return self.format_day_of_year(num)
        elif char == 'F':
            return self.format_day_of_week_in_month()
        elif char in ('E', 'e', 'c'):
            return self.format_weekday(char, num)
        elif char == 'a':
            return self.format_period(char)
        elif char == 'h':
            if self.value.hour % 12 == 0:
                return self.format(12, num)
            else:
                return self.format(self.value.hour % 12, num)
        elif char == 'H':
            return self.format(self.value.hour, num)
        elif char == 'K':
            return self.format(self.value.hour % 12, num)
        elif char == 'k':
            if self.value.hour == 0:
                return self.format(24, num)
            else:
                return self.format(self.value.hour, num)
        elif char == 'm':
            return self.format(self.value.minute, num)
        elif char == 's':
            return self.format(self.value.second, num)
        elif char == 'S':
            return self.format_frac_seconds(num)
        elif char == 'A':
            return self.format_milliseconds_in_day(num)
        elif char in ('z', 'Z', 'v', 'V'):
            return self.format_timezone(char, num)
        else:
            raise KeyError('Unsupported date/time field %r' % char)

    def format_era(self, char, num):
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[max(3, num)]
        era = int(self.value.year >= 0)
        return get_era_names(width, self.locale)[era]

    def format_year(self, char, num):
        value = self.value.year
        if char.isupper():
            week = self.get_week_number(self.get_day_of_year())
            if week == 0:
                value -= 1
        year = self.format(value, num)
        if num == 2:
            year = year[-2:]
        return year

    def format_quarter(self, char, num):
        quarter = (self.value.month - 1) // 3 + 1
        if num <= 2:
            return ('%%0%dd' % num) % quarter
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {'Q': 'format', 'q': 'stand-alone'}[char]
        return get_quarter_names(width, context, self.locale)[quarter]

    def format_month(self, char, num):
        if num <= 2:
            return ('%%0%dd' % num) % self.value.month
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {'M': 'format', 'L': 'stand-alone'}[char]
        return get_month_names(width, context, self.locale)[self.value.month]

    def format_week(self, char, num):
        if char.islower(): # week of year
            day_of_year = self.get_day_of_year()
            week = self.get_week_number(day_of_year)
            if week == 0:
                date = self.value - timedelta(days=day_of_year)
                week = self.get_week_number(self.get_day_of_year(date),
                                            date.weekday())
            return self.format(week, num)
        else: # week of month
            week = self.get_week_number(self.value.day)
            if week == 0:
                date = self.value - timedelta(days=self.value.day)
                week = self.get_week_number(date.day, date.weekday())
                pass
            return '%d' % week

    def format_weekday(self, char, num):
        if num < 3:
            if char.islower():
                value = 7 - self.locale.first_week_day + self.value.weekday()
                return self.format(value % 7 + 1, num)
            num = 3
        weekday = self.value.weekday()
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {3: 'format', 4: 'format', 5: 'stand-alone'}[num]
        return get_day_names(width, context, self.locale)[weekday]

    def format_day_of_year(self, num):
        return self.format(self.get_day_of_year(), num)

    def format_day_of_week_in_month(self):
        return '%d' % ((self.value.day - 1) / 7 + 1)

    def format_period(self, char):
        period = {0: 'am', 1: 'pm'}[int(self.value.hour >= 12)]
        return get_period_names(locale=self.locale)[period]

    def format_frac_seconds(self, num):
        value = str(self.value.microsecond)
        return self.format(round(float('.%s' % value), num) * 10**num, num)

    def format_milliseconds_in_day(self, num):
        msecs = self.value.microsecond // 1000 + self.value.second * 1000 + \
                self.value.minute * 60000 + self.value.hour * 3600000
        return self.format(msecs, num)

    def format_timezone(self, char, num):
        width = {3: 'short', 4: 'long'}[max(3, num)]
        if char == 'z':
            return get_timezone_name(self.value, width, locale=self.locale)
        elif char == 'Z':
            return get_timezone_gmt(self.value, width, locale=self.locale)
        elif char == 'v':
            return get_timezone_name(self.value.tzinfo, width,
                                     locale=self.locale)
        elif char == 'V':
            if num == 1:
                return get_timezone_name(self.value.tzinfo, width,
                                         uncommon=True, locale=self.locale)
            return get_timezone_location(self.value.tzinfo, locale=self.locale)

    def format(self, value, length):
        return ('%%0%dd' % length) % value

    def get_day_of_year(self, date=None):
        if date is None:
            date = self.value
        return (date - date_(date.year, 1, 1)).days + 1

    def get_week_number(self, day_of_period, day_of_week=None):
        """Return the number of the week of a day within a period. This may be
        the week number in a year or the week number in a month.
        
        Usually this will return a value equal to or greater than 1, but if the
        first week of the period is so short that it actually counts as the last
        week of the previous period, this function will return 0.
        
        >>> format = DateTimeFormat(date(2006, 1, 8), Locale.parse('de_DE'))
        >>> format.get_week_number(6)
        1
        
        >>> format = DateTimeFormat(date(2006, 1, 8), Locale.parse('en_US'))
        >>> format.get_week_number(6)
        2
        
        :param day_of_period: the number of the day in the period (usually
                              either the day of month or the day of year)
        :param day_of_week: the week day; if ommitted, the week day of the
                            current date is assumed
        """
        if day_of_week is None:
            day_of_week = self.value.weekday()
        first_day = (day_of_week - self.locale.first_week_day -
                     day_of_period + 1) % 7
        if first_day < 0:
            first_day += 7
        week_number = (day_of_period + first_day - 1) / 7
        if 7 - first_day >= self.locale.min_week_days:
            week_number += 1
        return week_number


PATTERN_CHARS = {
    'G': [1, 2, 3, 4, 5],                                           # era
    'y': None, 'Y': None, 'u': None,                                # year
    'Q': [1, 2, 3, 4], 'q': [1, 2, 3, 4],                           # quarter
    'M': [1, 2, 3, 4, 5], 'L': [1, 2, 3, 4, 5],                     # month
    'w': [1, 2], 'W': [1],                                          # week
    'd': [1, 2], 'D': [1, 2, 3], 'F': [1], 'g': None,               # day
    'E': [1, 2, 3, 4, 5], 'e': [1, 2, 3, 4, 5], 'c': [1, 3, 4, 5],  # week day
    'a': [1],                                                       # period
    'h': [1, 2], 'H': [1, 2], 'K': [1, 2], 'k': [1, 2],             # hour
    'm': [1, 2],                                                    # minute
    's': [1, 2], 'S': None, 'A': None,                              # second
    'z': [1, 2, 3, 4], 'Z': [1, 2, 3, 4], 'v': [1, 4], 'V': [1, 4]  # zone
}

def parse_pattern(pattern):
    """Parse date, time, and datetime format patterns.
    
    >>> parse_pattern("MMMMd").format
    u'%(MMMM)s%(d)s'
    >>> parse_pattern("MMM d, yyyy").format
    u'%(MMM)s %(d)s, %(yyyy)s'
    
    Pattern can contain literal strings in single quotes:
    
    >>> parse_pattern("H:mm' Uhr 'z").format
    u'%(H)s:%(mm)s Uhr %(z)s'
    
    An actual single quote can be used by using two adjacent single quote
    characters:
    
    >>> parse_pattern("hh' o''clock'").format
    u"%(hh)s o'clock"
    
    :param pattern: the formatting pattern to parse
    """
    if type(pattern) is DateTimePattern:
        return pattern

    result = []
    quotebuf = None
    charbuf = []
    fieldchar = ['']
    fieldnum = [0]

    def append_chars():
        result.append(''.join(charbuf).replace('%', '%%'))
        del charbuf[:]

    def append_field():
        limit = PATTERN_CHARS[fieldchar[0]]
        if limit and fieldnum[0] not in limit:
            raise ValueError('Invalid length for field: %r'
                             % (fieldchar[0] * fieldnum[0]))
        result.append('%%(%s)s' % (fieldchar[0] * fieldnum[0]))
        fieldchar[0] = ''
        fieldnum[0] = 0

    for idx, char in enumerate(pattern.replace("''", '\0')):
        if quotebuf is None:
            if char == "'": # quote started
                if fieldchar[0]:
                    append_field()
                elif charbuf:
                    append_chars()
                quotebuf = []
            elif char in PATTERN_CHARS:
                if charbuf:
                    append_chars()
                if char == fieldchar[0]:
                    fieldnum[0] += 1
                else:
                    if fieldchar[0]:
                        append_field()
                    fieldchar[0] = char
                    fieldnum[0] = 1
            else:
                if fieldchar[0]:
                    append_field()
                charbuf.append(char)

        elif quotebuf is not None:
            if char == "'": # end of quote
                charbuf.extend(quotebuf)
                quotebuf = None
            else: # inside quote
                quotebuf.append(char)

    if fieldchar[0]:
        append_field()
    elif charbuf:
        append_chars()

    return DateTimePattern(pattern, u''.join(result).replace('\0', "'"))

########NEW FILE########
__FILENAME__ = localedata
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Low-level locale data access.

:note: The `Locale` class, which uses this module under the hood, provides a
       more convenient interface for accessing the locale data.
"""

import os
import pickle
try:
    import threading
except ImportError:
    import dummy_threading as threading
from UserDict import DictMixin

__all__ = ['exists', 'list', 'load']
__docformat__ = 'restructuredtext en'

_cache = {}
_cache_lock = threading.RLock()
_dirname = os.path.join(os.path.dirname(__file__), 'localedata')


def exists(name):
    """Check whether locale data is available for the given locale.
    
    :param name: the locale identifier string
    :return: `True` if the locale data exists, `False` otherwise
    :rtype: `bool`
    """
    if name in _cache:
        return True
    return os.path.exists(os.path.join(_dirname, '%s.dat' % name))


def list():
    """Return a list of all locale identifiers for which locale data is
    available.
    
    :return: a list of locale identifiers (strings)
    :rtype: `list`
    :since: version 0.8.1
    """
    return [stem for stem, extension in [
        os.path.splitext(filename) for filename in os.listdir(_dirname)
    ] if extension == '.dat' and stem != 'root']


def load(name, merge_inherited=True):
    """Load the locale data for the given locale.
    
    The locale data is a dictionary that contains much of the data defined by
    the Common Locale Data Repository (CLDR). This data is stored as a
    collection of pickle files inside the ``babel`` package.
    
    >>> d = load('en_US')
    >>> d['languages']['sv']
    u'Swedish'
    
    Note that the results are cached, and subsequent requests for the same
    locale return the same dictionary:
    
    >>> d1 = load('en_US')
    >>> d2 = load('en_US')
    >>> d1 is d2
    True
    
    :param name: the locale identifier string (or "root")
    :param merge_inherited: whether the inherited data should be merged into
                            the data of the requested locale
    :return: the locale data
    :rtype: `dict`
    :raise `IOError`: if no locale data file is found for the given locale
                      identifer, or one of the locales it inherits from
    """
    _cache_lock.acquire()
    try:
        data = _cache.get(name)
        if not data:
            # Load inherited data
            if name == 'root' or not merge_inherited:
                data = {}
            else:
                parts = name.split('_')
                if len(parts) == 1:
                    parent = 'root'
                else:
                    parent = '_'.join(parts[:-1])
                data = load(parent).copy()
            filename = os.path.join(_dirname, '%s.dat' % name)
            fileobj = open(filename, 'rb')
            try:
                if name != 'root' and merge_inherited:
                    merge(data, pickle.load(fileobj))
                else:
                    data = pickle.load(fileobj)
                _cache[name] = data
            finally:
                fileobj.close()
        return data
    finally:
        _cache_lock.release()


def merge(dict1, dict2):
    """Merge the data from `dict2` into the `dict1` dictionary, making copies
    of nested dictionaries.
    
    >>> d = {1: 'foo', 3: 'baz'}
    >>> merge(d, {1: 'Foo', 2: 'Bar'})
    >>> items = d.items(); items.sort(); items
    [(1, 'Foo'), (2, 'Bar'), (3, 'baz')]
    
    :param dict1: the dictionary to merge into
    :param dict2: the dictionary containing the data that should be merged
    """
    for key, val2 in dict2.items():
        if val2 is not None:
            val1 = dict1.get(key)
            if isinstance(val2, dict):
                if val1 is None:
                    val1 = {}
                if isinstance(val1, Alias):
                    val1 = (val1, val2)
                elif isinstance(val1, tuple):
                    alias, others = val1
                    others = others.copy()
                    merge(others, val2)
                    val1 = (alias, others)
                else:
                    val1 = val1.copy()
                    merge(val1, val2)
            else:
                val1 = val2
            dict1[key] = val1


class Alias(object):
    """Representation of an alias in the locale data.
    
    An alias is a value that refers to some other part of the locale data,
    as specified by the `keys`.
    """

    def __init__(self, keys):
        self.keys = tuple(keys)

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.keys)

    def resolve(self, data):
        """Resolve the alias based on the given data.
        
        This is done recursively, so if one alias resolves to a second alias,
        that second alias will also be resolved.
        
        :param data: the locale data
        :type data: `dict`
        """
        base = data
        for key in self.keys:
            data = data[key]
        if isinstance(data, Alias):
            data = data.resolve(base)
        elif isinstance(data, tuple):
            alias, others = data
            data = alias.resolve(base)
        return data


class LocaleDataDict(DictMixin, dict):
    """Dictionary wrapper that automatically resolves aliases to the actual
    values.
    """

    def __init__(self, data, base=None):
        dict.__init__(self, data)
        if base is None:
            base = data
        self.base = base

    def __getitem__(self, key):
        orig = val = dict.__getitem__(self, key)
        if isinstance(val, Alias): # resolve an alias
            val = val.resolve(self.base)
        if isinstance(val, tuple): # Merge a partial dict with an alias
            alias, others = val
            val = alias.resolve(self.base).copy()
            merge(val, others)
        if type(val) is dict: # Return a nested alias-resolving dict
            val = LocaleDataDict(val, base=self.base)
        if val is not orig:
            self[key] = val
        return val

    def copy(self):
        return LocaleDataDict(dict.copy(self), base=self.base)

########NEW FILE########
__FILENAME__ = catalog
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Data structures for message catalogs."""

from cgi import parse_header
from datetime import datetime
from difflib import get_close_matches
from email import message_from_string
from copy import copy
import re
import time

from babel import __version__ as VERSION
from babel.core import Locale
from babel.dates import format_datetime
from babel.messages.plurals import get_plural
from babel.util import odict, distinct, set, LOCALTZ, UTC, FixedOffsetTimezone

__all__ = ['Message', 'Catalog', 'TranslationError']
__docformat__ = 'restructuredtext en'


PYTHON_FORMAT = re.compile(r'''(?x)
    \%
        (?:\(([\w]*)\))?
        (
            [-#0\ +]?(?:\*|[\d]+)?
            (?:\.(?:\*|[\d]+))?
            [hlL]?
        )
        ([diouxXeEfFgGcrs%])
''')


class Message(object):
    """Representation of a single message in a catalog."""

    def __init__(self, id, string=u'', locations=(), flags=(), auto_comments=(),
                 user_comments=(), previous_id=(), lineno=None):
        """Create the message object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filenname, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments for the message
        :param user_comments: a sequence of user comments for the message
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        """
        self.id = id #: The message ID
        if not string and self.pluralizable:
            string = (u'', u'')
        self.string = string #: The message translation
        self.locations = list(distinct(locations))
        self.flags = set(flags)
        if id and self.python_format:
            self.flags.add('python-format')
        else:
            self.flags.discard('python-format')
        self.auto_comments = list(distinct(auto_comments))
        self.user_comments = list(distinct(user_comments))
        if isinstance(previous_id, basestring):
            self.previous_id = [previous_id]
        else:
            self.previous_id = list(previous_id)
        self.lineno = lineno

    def __repr__(self):
        return '<%s %r (flags: %r)>' % (type(self).__name__, self.id,
                                        list(self.flags))

    def __cmp__(self, obj):
        """Compare Messages, taking into account plural ids"""
        if isinstance(obj, Message):
            plural = self.pluralizable
            obj_plural = obj.pluralizable
            if plural and obj_plural:
                return cmp(self.id[0], obj.id[0])
            elif plural:
                return cmp(self.id[0], obj.id)
            elif obj_plural:
                return cmp(self.id, obj.id[0])
        return cmp(self.id, obj.id)

    def clone(self):
        return Message(*map(copy, (self.id, self.string, self.locations,
                                   self.flags, self.auto_comments,
                                   self.user_comments, self.previous_id,
                                   self.lineno)))

    def check(self, catalog=None):
        """Run various validation checks on the message.  Some validations
        are only performed if the catalog is provided.  This method returns
        a sequence of `TranslationError` objects.

        :rtype: ``iterator``
        :param catalog: A catalog instance that is passed to the checkers
        :see: `Catalog.check` for a way to perform checks for all messages
              in a catalog.
        """
        from babel.messages.checkers import checkers
        errors = []
        for checker in checkers:
            try:
                checker(catalog, self)
            except TranslationError, e:
                errors.append(e)
        return errors

    def fuzzy(self):
        return 'fuzzy' in self.flags
    fuzzy = property(fuzzy, doc="""\
        Whether the translation is fuzzy.

        >>> Message('foo').fuzzy
        False
        >>> msg = Message('foo', 'foo', flags=['fuzzy'])
        >>> msg.fuzzy
        True
        >>> msg
        <Message 'foo' (flags: ['fuzzy'])>

        :type:  `bool`
        """)

    def pluralizable(self):
        return isinstance(self.id, (list, tuple))
    pluralizable = property(pluralizable, doc="""\
        Whether the message is plurizable.

        >>> Message('foo').pluralizable
        False
        >>> Message(('foo', 'bar')).pluralizable
        True

        :type:  `bool`
        """)

    def python_format(self):
        ids = self.id
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        return bool(filter(None, [PYTHON_FORMAT.search(id) for id in ids]))
    python_format = property(python_format, doc="""\
        Whether the message contains Python-style parameters.

        >>> Message('foo %(name)s bar').python_format
        True
        >>> Message(('foo %(name)s', 'foo %(name)s')).python_format
        True

        :type:  `bool`
        """)


class TranslationError(Exception):
    """Exception thrown by translation checkers when invalid message
    translations are encountered."""


DEFAULT_HEADER = u"""\
# Translations template for PROJECT.
# Copyright (C) YEAR ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#"""


class Catalog(object):
    """Representation of a message catalog."""

    def __init__(self, locale=None, domain=None, header_comment=DEFAULT_HEADER,
                 project=None, version=None, copyright_holder=None,
                 msgid_bugs_address=None, creation_date=None,
                 revision_date=None, last_translator=None, language_team=None,
                 charset='utf-8', fuzzy=True):
        """Initialize the catalog object.

        :param locale: the locale identifier or `Locale` object, or `None`
                       if the catalog is not bound to a locale (which basically
                       means it's a template)
        :param domain: the message domain
        :param header_comment: the header comment as string, or `None` for the
                               default header
        :param project: the project's name
        :param version: the project's version
        :param copyright_holder: the copyright holder of the catalog
        :param msgid_bugs_address: the email address or URL to submit bug
                                   reports to
        :param creation_date: the date the catalog was created
        :param revision_date: the date the catalog was revised
        :param last_translator: the name and email of the last translator
        :param language_team: the name and email of the language team
        :param charset: the encoding to use in the output
        :param fuzzy: the fuzzy bit on the catalog header
        """
        self.domain = domain #: The message domain
        if locale:
            locale = Locale.parse(locale)
        self.locale = locale #: The locale or `None`
        self._header_comment = header_comment
        self._messages = odict()

        self.project = project or 'PROJECT' #: The project name
        self.version = version or 'VERSION' #: The project version
        self.copyright_holder = copyright_holder or 'ORGANIZATION'
        self.msgid_bugs_address = msgid_bugs_address or 'EMAIL@ADDRESS'

        self.last_translator = last_translator or 'FULL NAME <EMAIL@ADDRESS>'
        """Name and email address of the last translator."""
        self.language_team = language_team or 'LANGUAGE <LL@li.org>'
        """Name and email address of the language team."""

        self.charset = charset or 'utf-8'

        if creation_date is None:
            creation_date = datetime.now(LOCALTZ)
        elif isinstance(creation_date, datetime) and not creation_date.tzinfo:
            creation_date = creation_date.replace(tzinfo=LOCALTZ)
        self.creation_date = creation_date #: Creation date of the template
        if revision_date is None:
            revision_date = datetime.now(LOCALTZ)
        elif isinstance(revision_date, datetime) and not revision_date.tzinfo:
            revision_date = revision_date.replace(tzinfo=LOCALTZ)
        self.revision_date = revision_date #: Last revision date of the catalog
        self.fuzzy = fuzzy #: Catalog header fuzzy bit (`True` or `False`)

        self.obsolete = odict() #: Dictionary of obsolete messages
        self._num_plurals = None
        self._plural_expr = None

    def _get_header_comment(self):
        comment = self._header_comment
        comment = comment.replace('PROJECT', self.project) \
                         .replace('VERSION', self.version) \
                         .replace('YEAR', self.revision_date.strftime('%Y')) \
                         .replace('ORGANIZATION', self.copyright_holder)
        if self.locale:
            comment = comment.replace('Translations template', '%s translations'
                                      % self.locale.english_name)
        return comment

    def _set_header_comment(self, string):
        self._header_comment = string

    header_comment = property(_get_header_comment, _set_header_comment, doc="""\
    The header comment for the catalog.

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> print catalog.header_comment #doctest: +ELLIPSIS
    # Translations template for Foobar.
    # Copyright (C) ... Foo Company
    # This file is distributed under the same license as the Foobar project.
    # FIRST AUTHOR <EMAIL@ADDRESS>, ....
    #

    The header can also be set from a string. Any known upper-case variables
    will be replaced when the header is retrieved again:

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> catalog.header_comment = '''\\
    ... # The POT for my really cool PROJECT project.
    ... # Copyright (C) 1990-2003 ORGANIZATION
    ... # This file is distributed under the same license as the PROJECT
    ... # project.
    ... #'''
    >>> print catalog.header_comment
    # The POT for my really cool Foobar project.
    # Copyright (C) 1990-2003 Foo Company
    # This file is distributed under the same license as the Foobar
    # project.
    #

    :type: `unicode`
    """)

    def _get_mime_headers(self):
        headers = []
        headers.append(('Project-Id-Version',
                        '%s %s' % (self.project, self.version)))
        headers.append(('Report-Msgid-Bugs-To', self.msgid_bugs_address))
        headers.append(('POT-Creation-Date',
                        format_datetime(self.creation_date, 'yyyy-MM-dd HH:mmZ',
                                        locale='en')))
        if self.locale is None:
            headers.append(('PO-Revision-Date', 'YEAR-MO-DA HO:MI+ZONE'))
            headers.append(('Last-Translator', 'FULL NAME <EMAIL@ADDRESS>'))
            headers.append(('Language-Team', 'LANGUAGE <LL@li.org>'))
        else:
            headers.append(('PO-Revision-Date',
                            format_datetime(self.revision_date,
                                            'yyyy-MM-dd HH:mmZ', locale='en')))
            headers.append(('Last-Translator', self.last_translator))
            headers.append(('Language-Team',
                           self.language_team.replace('LANGUAGE',
                                                      str(self.locale))))
            headers.append(('Plural-Forms', self.plural_forms))
        headers.append(('MIME-Version', '1.0'))
        headers.append(('Content-Type',
                        'text/plain; charset=%s' % self.charset))
        headers.append(('Content-Transfer-Encoding', '8bit'))
        headers.append(('Generated-By', 'Babel %s\n' % VERSION))
        return headers

    def _set_mime_headers(self, headers):
        for name, value in headers:
            if name.lower() == 'content-type':
                mimetype, params = parse_header(value)
                if 'charset' in params:
                    self.charset = params['charset'].lower()
                break
        for name, value in headers:
            name = name.lower().decode(self.charset)
            value = value.decode(self.charset)
            if name == 'project-id-version':
                parts = value.split(' ')
                self.project = u' '.join(parts[:-1])
                self.version = parts[-1]
            elif name == 'report-msgid-bugs-to':
                self.msgid_bugs_address = value
            elif name == 'last-translator':
                self.last_translator = value
            elif name == 'language-team':
                self.language_team = value
            elif name == 'plural-forms':
                _, params = parse_header(' ;' + value)
                self._num_plurals = int(params.get('nplurals', 2))
                self._plural_expr = params.get('plural', '(n != 1)')
            elif name == 'pot-creation-date':
                # FIXME: this should use dates.parse_datetime as soon as that
                #        is ready
                value, tzoffset, _ = re.split('([+-]\d{4})$', value, 1)

                tt = time.strptime(value, '%Y-%m-%d %H:%M')
                ts = time.mktime(tt)

                # Separate the offset into a sign component, hours, and minutes
                plus_minus_s, rest = tzoffset[0], tzoffset[1:]
                hours_offset_s, mins_offset_s = rest[:2], rest[2:]

                # Make them all integers
                plus_minus = int(plus_minus_s + '1')
                hours_offset = int(hours_offset_s)
                mins_offset = int(mins_offset_s)

                # Calculate net offset
                net_mins_offset = hours_offset * 60
                net_mins_offset += mins_offset
                net_mins_offset *= plus_minus

                # Create an offset object
                tzoffset = FixedOffsetTimezone(net_mins_offset)

                # Store the offset in a datetime object
                dt = datetime.fromtimestamp(ts)
                self.creation_date = dt.replace(tzinfo=tzoffset)
            elif name == 'po-revision-date':
                # Keep the value if it's not the default one
                if 'YEAR' not in value:
                    # FIXME: this should use dates.parse_datetime as soon as
                    #        that is ready
                    value, tzoffset, _ = re.split('([+-]\d{4})$', value, 1)
                    tt = time.strptime(value, '%Y-%m-%d %H:%M')
                    ts = time.mktime(tt)

                    # Separate the offset into a sign component, hours, and
                    # minutes
                    plus_minus_s, rest = tzoffset[0], tzoffset[1:]
                    hours_offset_s, mins_offset_s = rest[:2], rest[2:]

                    # Make them all integers
                    plus_minus = int(plus_minus_s + '1')
                    hours_offset = int(hours_offset_s)
                    mins_offset = int(mins_offset_s)

                    # Calculate net offset
                    net_mins_offset = hours_offset * 60
                    net_mins_offset += mins_offset
                    net_mins_offset *= plus_minus

                    # Create an offset object
                    tzoffset = FixedOffsetTimezone(net_mins_offset)

                    # Store the offset in a datetime object
                    dt = datetime.fromtimestamp(ts)
                    self.revision_date = dt.replace(tzinfo=tzoffset)

    mime_headers = property(_get_mime_headers, _set_mime_headers, doc="""\
    The MIME headers of the catalog, used for the special ``msgid ""`` entry.

    The behavior of this property changes slightly depending on whether a locale
    is set or not, the latter indicating that the catalog is actually a template
    for actual translations.

    Here's an example of the output for such a catalog template:

    >>> created = datetime(1990, 4, 1, 15, 30, tzinfo=UTC)
    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   creation_date=created)
    >>> for name, value in catalog.mime_headers:
    ...     print '%s: %s' % (name, value)
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    And here's an example of the output when the locale is set:

    >>> revised = datetime(1990, 8, 3, 12, 0, tzinfo=UTC)
    >>> catalog = Catalog(locale='de_DE', project='Foobar', version='1.0',
    ...                   creation_date=created, revision_date=revised,
    ...                   last_translator='John Doe <jd@example.com>',
    ...                   language_team='de_DE <de@example.com>')
    >>> for name, value in catalog.mime_headers:
    ...     print '%s: %s' % (name, value)
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: 1990-08-03 12:00+0000
    Last-Translator: John Doe <jd@example.com>
    Language-Team: de_DE <de@example.com>
    Plural-Forms: nplurals=2; plural=(n != 1)
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    :type: `list`
    """)

    def num_plurals(self):
        if self._num_plurals is None:
            num = 2
            if self.locale:
                num = get_plural(self.locale)[0]
            self._num_plurals = num
        return self._num_plurals
    num_plurals = property(num_plurals, doc="""\
    The number of plurals used by the catalog or locale.

    >>> Catalog(locale='en').num_plurals
    2
    >>> Catalog(locale='ga').num_plurals
    3

    :type: `int`
    """)

    def plural_expr(self):
        if self._plural_expr is None:
            expr = '(n != 1)'
            if self.locale:
                expr = get_plural(self.locale)[1]
            self._plural_expr = expr
        return self._plural_expr
    plural_expr = property(plural_expr, doc="""\
    The plural expression used by the catalog or locale.

    >>> Catalog(locale='en').plural_expr
    '(n != 1)'
    >>> Catalog(locale='ga').plural_expr
    '(n==1 ? 0 : n==2 ? 1 : 2)'

    :type: `basestring`
    """)

    def plural_forms(self):
        return 'nplurals=%s; plural=%s' % (self.num_plurals, self.plural_expr)
    plural_forms = property(plural_forms, doc="""\
    Return the plural forms declaration for the locale.

    >>> Catalog(locale='en').plural_forms
    'nplurals=2; plural=(n != 1)'
    >>> Catalog(locale='pt_BR').plural_forms
    'nplurals=2; plural=(n > 1)'

    :type: `str`
    """)

    def __contains__(self, id):
        """Return whether the catalog has a message with the specified ID."""
        return self._key_for(id) in self._messages

    def __len__(self):
        """The number of messages in the catalog.

        This does not include the special ``msgid ""`` entry.
        """
        return len(self._messages)

    def __iter__(self):
        """Iterates through all the entries in the catalog, in the order they
        were added, yielding a `Message` object for every entry.

        :rtype: ``iterator``
        """
        buf = []
        for name, value in self.mime_headers:
            buf.append('%s: %s' % (name, value))
        flags = set()
        if self.fuzzy:
            flags |= set(['fuzzy'])
        yield Message(u'', '\n'.join(buf), flags=flags)
        for key in self._messages:
            yield self._messages[key]

    def __repr__(self):
        locale = ''
        if self.locale:
            locale = ' %s' % self.locale
        return '<%s %r%s>' % (type(self).__name__, self.domain, locale)

    def __delitem__(self, id):
        """Delete the message with the specified ID."""
        key = self._key_for(id)
        if key in self._messages:
            del self._messages[key]

    def __getitem__(self, id):
        """Return the message with the specified ID.

        :param id: the message ID
        :return: the message with the specified ID, or `None` if no such message
                 is in the catalog
        :rtype: `Message`
        """
        return self._messages.get(self._key_for(id))

    def __setitem__(self, id, message):
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo')
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        If a message with that ID is already in the catalog, it is updated
        to include the locations and flags of the new message.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo', locations=[('main.py', 1)])
        >>> catalog[u'foo'].locations
        [('main.py', 1)]
        >>> catalog[u'foo'] = Message(u'foo', locations=[('utils.py', 5)])
        >>> catalog[u'foo'].locations
        [('main.py', 1), ('utils.py', 5)]

        :param id: the message ID
        :param message: the `Message` object
        """
        assert isinstance(message, Message), 'expected a Message object'
        key = self._key_for(id)
        current = self._messages.get(key)
        if current:
            if message.pluralizable and not current.pluralizable:
                # The new message adds pluralization
                current.id = message.id
                current.string = message.string
            current.locations = list(distinct(current.locations +
                                              message.locations))
            current.auto_comments = list(distinct(current.auto_comments +
                                                  message.auto_comments))
            current.user_comments = list(distinct(current.user_comments +
                                                  message.user_comments))
            current.flags |= message.flags
            message = current
        elif id == '':
            # special treatment for the header message
            headers = message_from_string(message.string.encode(self.charset))
            self.mime_headers = headers.items()
            self.header_comment = '\n'.join(['# %s' % comment for comment
                                             in message.user_comments])
            self.fuzzy = message.fuzzy
        else:
            if isinstance(id, (list, tuple)):
                assert isinstance(message.string, (list, tuple)), \
                    'Expected sequence but got %s' % type(message.string)
            self._messages[key] = message

    def add(self, id, string=None, locations=(), flags=(), auto_comments=(),
            user_comments=(), previous_id=(), lineno=None):
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog.add(u'foo')
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        This method simply constructs a `Message` object with the given
        arguments and invokes `__setitem__` with that object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filenname, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments
        :param user_comments: a sequence of user comments
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        """
        self[id] = Message(id, string, list(locations), flags, auto_comments,
                           user_comments, previous_id, lineno=lineno)

    def check(self):
        """Run various validation checks on the translations in the catalog.

        For every message which fails validation, this method yield a
        ``(message, errors)`` tuple, where ``message`` is the `Message` object
        and ``errors`` is a sequence of `TranslationError` objects.

        :rtype: ``iterator``
        """
        for message in self._messages.values():
            errors = message.check(catalog=self)
            if errors:
                yield message, errors

    def update(self, template, no_fuzzy_matching=False):
        """Update the catalog based on the given template catalog.

        >>> from babel.messages import Catalog
        >>> template = Catalog()
        >>> template.add('green', locations=[('main.py', 99)])
        >>> template.add('blue', locations=[('main.py', 100)])
        >>> template.add(('salad', 'salads'), locations=[('util.py', 42)])
        >>> catalog = Catalog(locale='de_DE')
        >>> catalog.add('blue', u'blau', locations=[('main.py', 98)])
        >>> catalog.add('head', u'Kopf', locations=[('util.py', 33)])
        >>> catalog.add(('salad', 'salads'), (u'Salat', u'Salate'),
        ...             locations=[('util.py', 38)])

        >>> catalog.update(template)
        >>> len(catalog)
        3

        >>> msg1 = catalog['green']
        >>> msg1.string
        >>> msg1.locations
        [('main.py', 99)]

        >>> msg2 = catalog['blue']
        >>> msg2.string
        u'blau'
        >>> msg2.locations
        [('main.py', 100)]

        >>> msg3 = catalog['salad']
        >>> msg3.string
        (u'Salat', u'Salate')
        >>> msg3.locations
        [('util.py', 42)]

        Messages that are in the catalog but not in the template are removed
        from the main collection, but can still be accessed via the `obsolete`
        member:

        >>> 'head' in catalog
        False
        >>> catalog.obsolete.values()
        [<Message 'head' (flags: [])>]

        :param template: the reference catalog, usually read from a POT file
        :param no_fuzzy_matching: whether to use fuzzy matching of message IDs
        """
        messages = self._messages
        remaining = messages.copy()
        self._messages = odict()

        # Prepare for fuzzy matching
        fuzzy_candidates = []
        if not no_fuzzy_matching:
            fuzzy_candidates = [
                self._key_for(msgid) for msgid in messages
                if msgid and messages[msgid].string
            ]
        fuzzy_matches = set()

        def _merge(message, oldkey, newkey):
            message = message.clone()
            fuzzy = False
            if oldkey != newkey:
                fuzzy = True
                fuzzy_matches.add(oldkey)
                oldmsg = messages.get(oldkey)
                if isinstance(oldmsg.id, basestring):
                    message.previous_id = [oldmsg.id]
                else:
                    message.previous_id = list(oldmsg.id)
            else:
                oldmsg = remaining.pop(oldkey, None)
            message.string = oldmsg.string
            if isinstance(message.id, (list, tuple)):
                if not isinstance(message.string, (list, tuple)):
                    fuzzy = True
                    message.string = tuple(
                        [message.string] + ([u''] * (len(message.id) - 1))
                    )
                elif len(message.string) != self.num_plurals:
                    fuzzy = True
                    message.string = tuple(message.string[:len(oldmsg.string)])
            elif isinstance(message.string, (list, tuple)):
                fuzzy = True
                message.string = message.string[0]
            message.flags |= oldmsg.flags
            if fuzzy:
                message.flags |= set([u'fuzzy'])
            self[message.id] = message

        for message in template:
            if message.id:
                key = self._key_for(message.id)
                if key in messages:
                    _merge(message, key, key)
                else:
                    if no_fuzzy_matching is False:
                        # do some fuzzy matching with difflib
                        matches = get_close_matches(key.lower().strip(),
                                                    fuzzy_candidates, 1)
                        if matches:
                            _merge(message, matches[0], key)
                            continue

                    self[message.id] = message

        self.obsolete = odict()
        for msgid in remaining:
            if no_fuzzy_matching or msgid not in fuzzy_matches:
                self.obsolete[msgid] = remaining[msgid]
        # Make updated catalog's POT-Creation-Date equal to the template
        # used to update the catalog
        self.creation_date = template.creation_date

    def _key_for(self, id):
        """The key for a message is just the singular ID even for pluralizable
        messages.
        """
        key = id
        if isinstance(key, (list, tuple)):
            key = id[0]
        return key

########NEW FILE########
__FILENAME__ = checkers
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Various routines that help with validation of translations.

:since: version 0.9
"""

from itertools import izip
from babel.messages.catalog import TranslationError, PYTHON_FORMAT
from babel.util import set

#: list of format chars that are compatible to each other
_string_format_compatibilities = [
    set(['i', 'd', 'u']),
    set(['x', 'X']),
    set(['f', 'F', 'g', 'G'])
]


def num_plurals(catalog, message):
    """Verify the number of plurals in the translation."""
    if not message.pluralizable:
        if not isinstance(message.string, basestring):
            raise TranslationError("Found plural forms for non-pluralizable "
                                   "message")
        return

    # skip further tests if no catalog is provided.
    elif catalog is None:
        return

    msgstrs = message.string
    if not isinstance(msgstrs, (list, tuple)):
        msgstrs = (msgstrs,)
    if len(msgstrs) != catalog.num_plurals:
        raise TranslationError("Wrong number of plural forms (expected %d)" %
                               catalog.num_plurals)


def python_format(catalog, message):
    """Verify the format string placeholders in the translation."""
    if 'python-format' not in message.flags:
        return
    msgids = message.id
    if not isinstance(msgids, (list, tuple)):
        msgids = (msgids,)
    msgstrs = message.string
    if not isinstance(msgstrs, (list, tuple)):
        msgstrs = (msgstrs,)

    for msgid, msgstr in izip(msgids, msgstrs):
        if msgstr:
            _validate_format(msgid, msgstr)


def _validate_format(format, alternative):
    """Test format string `alternative` against `format`.  `format` can be the
    msgid of a message and `alternative` one of the `msgstr`\s.  The two
    arguments are not interchangeable as `alternative` may contain less
    placeholders if `format` uses named placeholders.

    The behavior of this function is undefined if the string does not use
    string formattings.

    If the string formatting of `alternative` is compatible to `format` the
    function returns `None`, otherwise a `TranslationError` is raised.

    Examples for compatible format strings:

    >>> _validate_format('Hello %s!', 'Hallo %s!')
    >>> _validate_format('Hello %i!', 'Hallo %d!')

    Example for an incompatible format strings:

    >>> _validate_format('Hello %(name)s!', 'Hallo %s!')
    Traceback (most recent call last):
      ...
    TranslationError: the format strings are of different kinds

    This function is used by the `python_format` checker.

    :param format: The original format string
    :param alternative: The alternative format string that should be checked
                        against format
    :return: None on success
    :raises TranslationError: on formatting errors
    """

    def _parse(string):
        result = []
        for match in PYTHON_FORMAT.finditer(string):
            name, format, typechar = match.groups()
            if typechar == '%' and name is None:
                continue
            result.append((name, str(typechar)))
        return result

    def _compatible(a, b):
        if a == b:
            return True
        for set in _string_format_compatibilities:
            if a in set and b in set:
                return True
        return False

    def _check_positional(results):
        positional = None
        for name, char in results:
            if positional is None:
                positional = name is None
            else:
                if (name is None) != positional:
                    raise TranslationError('format string mixes positional '
                                           'and named placeholders')
        return bool(positional)

    a, b = map(_parse, (format, alternative))

    # now check if both strings are positional or named
    a_positional, b_positional = map(_check_positional, (a, b))
    if a_positional and not b_positional and not b:
        raise TranslationError('placeholders are incompatible')
    elif a_positional != b_positional:
        raise TranslationError('the format strings are of different kinds')

    # if we are operating on positional strings both must have the
    # same number of format chars and those must be compatible
    if a_positional:
        if len(a) != len(b):
            raise TranslationError('positional format placeholders are '
                                   'unbalanced')
        for idx, ((_, first), (_, second)) in enumerate(izip(a, b)):
            if not _compatible(first, second):
                raise TranslationError('incompatible format for placeholder '
                                       '%d: %r and %r are not compatible' %
                                       (idx + 1, first, second))

    # otherwise the second string must not have names the first one
    # doesn't have and the types of those included must be compatible
    else:
        type_map = dict(a)
        for name, typechar in b:
            if name not in type_map:
                raise TranslationError('unknown named placeholder %r' % name)
            elif not _compatible(typechar, type_map[name]):
                raise TranslationError('incompatible format for '
                                       'placeholder %r: '
                                       '%r and %r are not compatible' %
                                       (name, typechar, type_map[name]))


def _find_checkers():
    try:
        from pkg_resources import working_set
    except ImportError:
        return [num_plurals, python_format]
    checkers = []
    for entry_point in working_set.iter_entry_points('babel.checkers'):
        checkers.append(entry_point.load())
    return checkers


checkers = _find_checkers()

########NEW FILE########
__FILENAME__ = extract
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Basic infrastructure for extracting localizable messages from source files.

This module defines an extensible system for collecting localizable message
strings from a variety of sources. A native extractor for Python source files
is builtin, extractors for other sources can be added using very simple plugins.

The main entry points into the extraction functionality are the functions
`extract_from_dir` and `extract_from_file`.
"""

import os
try:
    set
except NameError:
    from sets import Set as set
import sys
from tokenize import generate_tokens, COMMENT, NAME, OP, STRING

from babel.util import parse_encoding, pathmatch, relpath
from textwrap import dedent

__all__ = ['extract', 'extract_from_dir', 'extract_from_file']
__docformat__ = 'restructuredtext en'

GROUP_NAME = 'babel.extractors'

DEFAULT_KEYWORDS = {
    '_': None,
    'gettext': None,
    'ngettext': (1, 2),
    'ugettext': None,
    'ungettext': (1, 2),
    'dgettext': (2,),
    'dngettext': (2, 3),
    'N_': None
}

DEFAULT_MAPPING = [('**.py', 'python')]

empty_msgid_warning = (
'%s: warning: Empty msgid.  It is reserved by GNU gettext: gettext("") '
'returns the header entry with meta information, not the empty string.')


def _strip_comment_tags(comments, tags):
    """Helper function for `extract` that strips comment tags from strings
    in a list of comment lines.  This functions operates in-place.
    """
    def _strip(line):
        for tag in tags:
            if line.startswith(tag):
                return line[len(tag):].strip()
        return line
    comments[:] = map(_strip, comments)


def extract_from_dir(dirname=os.getcwd(), method_map=DEFAULT_MAPPING,
                     options_map=None, keywords=DEFAULT_KEYWORDS,
                     comment_tags=(), callback=None, strip_comment_tags=False):
    """Extract messages from any source files found in the given directory.

    This function generates tuples of the form:

        ``(filename, lineno, message, comments)``

    Which extraction method is used per file is determined by the `method_map`
    parameter, which maps extended glob patterns to extraction method names.
    For example, the following is the default mapping:

    >>> method_map = [
    ...     ('**.py', 'python')
    ... ]

    This basically says that files with the filename extension ".py" at any
    level inside the directory should be processed by the "python" extraction
    method. Files that don't match any of the mapping patterns are ignored. See
    the documentation of the `pathmatch` function for details on the pattern
    syntax.

    The following extended mapping would also use the "genshi" extraction
    method on any file in "templates" subdirectory:

    >>> method_map = [
    ...     ('**/templates/**.*', 'genshi'),
    ...     ('**.py', 'python')
    ... ]

    The dictionary provided by the optional `options_map` parameter augments
    these mappings. It uses extended glob patterns as keys, and the values are
    dictionaries mapping options names to option values (both strings).

    The glob patterns of the `options_map` do not necessarily need to be the
    same as those used in the method mapping. For example, while all files in
    the ``templates`` folders in an application may be Genshi applications, the
    options for those files may differ based on extension:

    >>> options_map = {
    ...     '**/templates/**.txt': {
    ...         'template_class': 'genshi.template:TextTemplate',
    ...         'encoding': 'latin-1'
    ...     },
    ...     '**/templates/**.html': {
    ...         'include_attrs': ''
    ...     }
    ... }

    :param dirname: the path to the directory to extract messages from
    :param method_map: a list of ``(pattern, method)`` tuples that maps of
                       extraction method names to extended glob patterns
    :param options_map: a dictionary of additional options (optional)
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of tags of translator comments to search for
                         and include in the results
    :param callback: a function that is called for every file that message are
                     extracted from, just before the extraction itself is
                     performed; the function is passed the filename, the name
                     of the extraction method and and the options dictionary as
                     positional arguments, in that order
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :return: an iterator over ``(filename, lineno, funcname, message)`` tuples
    :rtype: ``iterator``
    :see: `pathmatch`
    """
    if options_map is None:
        options_map = {}

    absname = os.path.abspath(dirname)
    for root, dirnames, filenames in os.walk(absname):
        for subdir in dirnames:
            if subdir.startswith('.') or subdir.startswith('_'):
                dirnames.remove(subdir)
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            filename = relpath(
                os.path.join(root, filename).replace(os.sep, '/'),
                dirname
            )
            for pattern, method in method_map:
                if pathmatch(pattern, filename):
                    filepath = os.path.join(absname, filename)
                    options = {}
                    for opattern, odict in options_map.items():
                        if pathmatch(opattern, filename):
                            options = odict
                    if callback:
                        callback(filename, method, options)
                    for lineno, message, comments in \
                          extract_from_file(method, filepath,
                                            keywords=keywords,
                                            comment_tags=comment_tags,
                                            options=options,
                                            strip_comment_tags=
                                                strip_comment_tags):
                        yield filename, lineno, message, comments
                    break


def extract_from_file(method, filename, keywords=DEFAULT_KEYWORDS,
                      comment_tags=(), options=None, strip_comment_tags=False):
    """Extract messages from a specific file.

    This function returns a list of tuples of the form:

        ``(lineno, funcname, message)``

    :param filename: the path to the file to extract messages from
    :param method: a string specifying the extraction method (.e.g. "python")
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :param options: a dictionary of additional options (optional)
    :return: the list of extracted messages
    :rtype: `list`
    """
    fileobj = open(filename, 'U')
    try:
        return list(extract(method, fileobj, keywords, comment_tags, options,
                            strip_comment_tags))
    finally:
        fileobj.close()


def extract(method, fileobj, keywords=DEFAULT_KEYWORDS, comment_tags=(),
            options=None, strip_comment_tags=False):
    """Extract messages from the given file-like object using the specified
    extraction method.

    This function returns a list of tuples of the form:

        ``(lineno, message, comments)``

    The implementation dispatches the actual extraction to plugins, based on the
    value of the ``method`` parameter.

    >>> source = '''# foo module
    ... def run(argv):
    ...    print _('Hello, world!')
    ... '''

    >>> from StringIO import StringIO
    >>> for message in extract('python', StringIO(source)):
    ...     print message
    (3, u'Hello, world!', [])

    :param method: a string specifying the extraction method (.e.g. "python");
                   if this is a simple name, the extraction function will be
                   looked up by entry point; if it is an explicit reference
                   to a function (of the form ``package.module:funcname`` or
                   ``package.module.funcname``), the corresponding function
                   will be imported and used
    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :return: the list of extracted messages
    :rtype: `list`
    :raise ValueError: if the extraction method is not registered
    """
    func = None
    if ':' in method or '.' in method:
        if ':' not in method:
            lastdot = method.rfind('.')
            module, attrname = method[:lastdot], method[lastdot + 1:]
        else:
            module, attrname = method.split(':', 1)
        func = getattr(__import__(module, {}, {}, [attrname]), attrname)
    else:
        try:
            from pkg_resources import working_set
        except ImportError:
            # pkg_resources is not available, so we resort to looking up the
            # builtin extractors directly
            builtin = {'ignore': extract_nothing, 'python': extract_python}
            func = builtin.get(method)
        else:
            for entry_point in working_set.iter_entry_points(GROUP_NAME,
                                                             method):
                func = entry_point.load(require=True)
                break
    if func is None:
        raise ValueError('Unknown extraction method %r' % method)

    results = func(fileobj, keywords.keys(), comment_tags,
                   options=options or {})

    for lineno, funcname, messages, comments in results:
        if funcname:
            spec = keywords[funcname] or (1,)
        else:
            spec = (1,)
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        if not messages:
            continue

        # Validate the messages against the keyword's specification
        msgs = []
        invalid = False
        # last_index is 1 based like the keyword spec
        last_index = len(messages)
        for index in spec:
            if last_index < index:
                # Not enough arguments
                invalid = True
                break
            message = messages[index - 1]
            if message is None:
                invalid = True
                break
            msgs.append(message)
        if invalid:
            continue

        first_msg_index = spec[0] - 1
        if not messages[first_msg_index]:
            # An empty string msgid isn't valid, emit a warning
            where = '%s:%i' % (hasattr(fileobj, 'name') and \
                                   fileobj.name or '(unknown)', lineno)
            print >> sys.stderr, empty_msgid_warning % where
            continue

        messages = tuple(msgs)
        if len(messages) == 1:
            messages = messages[0]

        if strip_comment_tags:
            _strip_comment_tags(comments, comment_tags)
        yield lineno, messages, comments


def extract_nothing(fileobj, keywords, comment_tags, options):
    """Pseudo extractor that does not actually extract anything, but simply
    returns an empty list.
    """
    return []


def extract_python(fileobj, keywords, comment_tags, options):
    """Extract messages from Python source code.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    funcname = lineno = message_lineno = None
    call_stack = -1
    buf = []
    messages = []
    translator_comments = []
    in_def = in_translator_comments = False
    comment_tag = None

    encoding = parse_encoding(fileobj) or options.get('encoding', 'iso-8859-1')

    tokens = generate_tokens(fileobj.readline)
    for tok, value, (lineno, _), _, _ in tokens:
        if call_stack == -1 and tok == NAME and value in ('def', 'class'):
            in_def = True
        elif tok == OP and value == '(':
            if in_def:
                # Avoid false positives for declarations such as:
                # def gettext(arg='message'):
                in_def = False
                continue
            if funcname:
                message_lineno = lineno
                call_stack += 1
        elif in_def and tok == OP and value == ':':
            # End of a class definition without parens
            in_def = False
            continue
        elif call_stack == -1 and tok == COMMENT:
            # Strip the comment token from the line
            value = value.decode(encoding)[1:].strip()
            if in_translator_comments and \
                    translator_comments[-1][0] == lineno - 1:
                # We're already inside a translator comment, continue appending
                translator_comments.append((lineno, value))
                continue
            # If execution reaches this point, let's see if comment line
            # starts with one of the comment tags
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    in_translator_comments = True
                    translator_comments.append((lineno, value))
                    break
        elif funcname and call_stack == 0:
            if tok == OP and value == ')':
                if buf:
                    messages.append(''.join(buf))
                    del buf[:]
                else:
                    messages.append(None)

                if len(messages) > 1:
                    messages = tuple(messages)
                else:
                    messages = messages[0]
                # Comments don't apply unless they immediately preceed the
                # message
                if translator_comments and \
                        translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                yield (message_lineno, funcname, messages,
                       [comment[1] for comment in translator_comments])

                funcname = lineno = message_lineno = None
                call_stack = -1
                messages = []
                translator_comments = []
                in_translator_comments = False
            elif tok == STRING:
                # Unwrap quotes in a safe manner, maintaining the string's
                # encoding
                # https://sourceforge.net/tracker/?func=detail&atid=355470&
                # aid=617979&group_id=5470
                value = eval('# coding=%s\n%s' % (encoding, value),
                             {'__builtins__':{}}, {})
                if isinstance(value, str):
                    value = value.decode(encoding)
                buf.append(value)
            elif tok == OP and value == ',':
                if buf:
                    messages.append(''.join(buf))
                    del buf[:]
                else:
                    messages.append(None)
                if translator_comments:
                    # We have translator comments, and since we're on a
                    # comma(,) user is allowed to break into a new line
                    # Let's increase the last comment's lineno in order
                    # for the comment to still be a valid one
                    old_lineno, old_comment = translator_comments.pop()
                    translator_comments.append((old_lineno+1, old_comment))
        elif call_stack > 0 and tok == OP and value == ')':
            call_stack -= 1
        elif funcname and call_stack == -1:
            funcname = None
        elif tok == NAME and value in keywords:
            funcname = value


def extract_javascript(fileobj, keywords, comment_tags, options):
    """Extract messages from JavaScript source code.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    from babel.messages.jslexer import tokenize, unquote_string
    funcname = message_lineno = None
    messages = []
    last_argument = None
    translator_comments = []
    concatenate_next = False
    encoding = options.get('encoding', 'utf-8')
    last_token = None
    call_stack = -1

    for token in tokenize(fileobj.read().decode(encoding)):
        if token.type == 'operator' and token.value == '(':
            if funcname:
                message_lineno = token.lineno
                call_stack += 1

        elif call_stack == -1 and token.type == 'linecomment':
            value = token.value[2:].strip()
            if translator_comments and \
               translator_comments[-1][0] == token.lineno - 1:
                translator_comments.append((token.lineno, value))
                continue

            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    translator_comments.append((token.lineno, value.strip()))
                    break

        elif token.type == 'multilinecomment':
            # only one multi-line comment may preceed a translation
            translator_comments = []
            value = token.value[2:-2].strip()
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    lines = value.splitlines()
                    if lines:
                        lines[0] = lines[0].strip()
                        lines[1:] = dedent('\n'.join(lines[1:])).splitlines()
                        for offset, line in enumerate(lines):
                            translator_comments.append((token.lineno + offset,
                                                        line))
                    break

        elif funcname and call_stack == 0:
            if token.type == 'operator' and token.value == ')':
                if last_argument is not None:
                    messages.append(last_argument)
                if len(messages) > 1:
                    messages = tuple(messages)
                elif messages:
                    messages = messages[0]
                else:
                    messages = None

                # Comments don't apply unless they immediately precede the
                # message
                if translator_comments and \
                   translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                if messages is not None:
                    yield (message_lineno, funcname, messages,
                           [comment[1] for comment in translator_comments])

                funcname = message_lineno = last_argument = None
                concatenate_next = False
                translator_comments = []
                messages = []
                call_stack = -1

            elif token.type == 'string':
                new_value = unquote_string(token.value)
                if concatenate_next:
                    last_argument = (last_argument or '') + new_value
                    concatenate_next = False
                else:
                    last_argument = new_value

            elif token.type == 'operator':
                if token.value == ',':
                    if last_argument is not None:
                        messages.append(last_argument)
                        last_argument = None
                    else:
                        messages.append(None)
                    concatenate_next = False
                elif token.value == '+':
                    concatenate_next = True

        elif call_stack > 0 and token.type == 'operator' \
             and token.value == ')':
            call_stack -= 1

        elif funcname and call_stack == -1:
            funcname = None

        elif call_stack == -1 and token.type == 'name' and \
             token.value in keywords and \
             (last_token is None or last_token.type != 'name' or
              last_token.value != 'function'):
            funcname = token.value

        last_token = token

########NEW FILE########
__FILENAME__ = frontend
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Frontends for the message extraction functionality."""

from ConfigParser import RawConfigParser
from datetime import datetime
from distutils import log
from distutils.cmd import Command
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from locale import getpreferredencoding
import logging
from optparse import OptionParser
import os
import re
import shutil
from StringIO import StringIO
import sys
import tempfile

from babel import __version__ as VERSION
from babel import Locale, localedata
from babel.core import UnknownLocaleError
from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir, DEFAULT_KEYWORDS, \
                                   DEFAULT_MAPPING
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po
from babel.messages.plurals import PLURALS
from babel.util import odict, LOCALTZ

__all__ = ['CommandLineInterface', 'compile_catalog', 'extract_messages',
           'init_catalog', 'check_message_extractors', 'update_catalog']
__docformat__ = 'restructuredtext en'


class compile_catalog(Command):
    """Catalog compilation command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import compile_catalog

        setup(
            ...
            cmdclass = {'compile_catalog': compile_catalog}
        )

    :since: version 0.9
    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'compile message catalogs to binary MO files'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('directory=', 'd',
         'path to base directory containing the catalogs'),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('use-fuzzy', 'f',
         'also include fuzzy translations'),
        ('statistics', None,
         'print statistics about translations')
    ]
    boolean_options = ['use-fuzzy', 'statistics']

    def initialize_options(self):
        self.domain = 'messages'
        self.directory = None
        self.input_file = None
        self.output_file = None
        self.locale = None
        self.use_fuzzy = False
        self.statistics = False

    def finalize_options(self):
        if not self.input_file and not self.directory:
            raise DistutilsOptionError('you must specify either the input file '
                                       'or the base directory')
        if not self.output_file and not self.directory:
            raise DistutilsOptionError('you must specify either the input file '
                                       'or the base directory')

    def run(self):
        po_files = []
        mo_files = []

        if not self.input_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.directory, self.locale,
                                              'LC_MESSAGES',
                                              self.domain + '.po')))
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.mo'))
            else:
                for locale in os.listdir(self.directory):
                    po_file = os.path.join(self.directory, locale,
                                           'LC_MESSAGES', self.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        mo_files.append(os.path.join(self.directory, locale,
                                                     'LC_MESSAGES',
                                                     self.domain + '.mo'))
        else:
            po_files.append((self.locale, self.input_file))
            if self.output_file:
                mo_files.append(self.output_file)
            else:
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.mo'))

        if not po_files:
            raise DistutilsOptionError('no message catalogs found')

        for idx, (locale, po_file) in enumerate(po_files):
            mo_file = mo_files[idx]
            infile = open(po_file, 'r')
            try:
                catalog = read_po(infile, locale)
            finally:
                infile.close()

            if self.statistics:
                translated = 0
                for message in list(catalog)[1:]:
                    if message.string:
                        translated +=1
                percentage = 0
                if len(catalog):
                    percentage = translated * 100 // len(catalog)
                log.info('%d of %d messages (%d%%) translated in %r',
                         translated, len(catalog), percentage, po_file)

            if catalog.fuzzy and not self.use_fuzzy:
                log.warn('catalog %r is marked as fuzzy, skipping', po_file)
                continue

            for message, errors in catalog.check():
                for error in errors:
                    log.error('error: %s:%d: %s', po_file, message.lineno,
                              error)

            log.info('compiling catalog %r to %r', po_file, mo_file)

            outfile = open(mo_file, 'wb')
            try:
                write_mo(outfile, catalog, use_fuzzy=self.use_fuzzy)
            finally:
                outfile.close()


class extract_messages(Command):
    """Message extraction command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import extract_messages

        setup(
            ...
            cmdclass = {'extract_messages': extract_messages}
        )

    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'extract localizable strings from the project code'
    user_options = [
        ('charset=', None,
         'charset to use in the output file'),
        ('keywords=', 'k',
         'space-separated list of keywords to look for in addition to the '
         'defaults'),
        ('no-default-keywords', None,
         'do not include the default keywords'),
        ('mapping-file=', 'F',
         'path to the mapping configuration file'),
        ('no-location', None,
         'do not include location comments with filename and line number'),
        ('omit-header', None,
         'do not include msgid "" entry in header'),
        ('output-file=', 'o',
         'name of the output file'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
        ('sort-output', None,
         'generate sorted output (default False)'),
        ('sort-by-file', None,
         'sort output by file location (default False)'),
        ('msgid-bugs-address=', None,
         'set report address for msgid'),
        ('copyright-holder=', None,
         'set copyright holder in output'),
        ('add-comments=', 'c',
         'place comment block with TAG (or those preceding keyword lines) in '
         'output file. Seperate multiple TAGs with commas(,)'),
        ('strip-comments', None,
         'strip the comment TAGs from the comments.'),
        ('input-dirs=', None,
         'directories that should be scanned for messages'),
    ]
    boolean_options = [
        'no-default-keywords', 'no-location', 'omit-header', 'no-wrap',
        'sort-output', 'sort-by-file', 'strip-comments'
    ]

    def initialize_options(self):
        self.charset = 'utf-8'
        self.keywords = ''
        self._keywords = DEFAULT_KEYWORDS.copy()
        self.no_default_keywords = False
        self.mapping_file = None
        self.no_location = False
        self.omit_header = False
        self.output_file = None
        self.input_dirs = None
        self.width = None
        self.no_wrap = False
        self.sort_output = False
        self.sort_by_file = False
        self.msgid_bugs_address = None
        self.copyright_holder = None
        self.add_comments = None
        self._add_comments = []
        self.strip_comments = False

    def finalize_options(self):
        if self.no_default_keywords and not self.keywords:
            raise DistutilsOptionError('you must specify new keywords if you '
                                       'disable the default ones')
        if self.no_default_keywords:
            self._keywords = {}
        if self.keywords:
            self._keywords.update(parse_keywords(self.keywords.split()))

        if not self.output_file:
            raise DistutilsOptionError('no output file specified')
        if self.no_wrap and self.width:
            raise DistutilsOptionError("'--no-wrap' and '--width' are mutually "
                                       "exclusive")
        if not self.no_wrap and not self.width:
            self.width = 76
        elif self.width is not None:
            self.width = int(self.width)

        if self.sort_output and self.sort_by_file:
            raise DistutilsOptionError("'--sort-output' and '--sort-by-file' "
                                       "are mutually exclusive")

        if not self.input_dirs:
            self.input_dirs = dict.fromkeys([k.split('.',1)[0]
                for k in self.distribution.packages
            ]).keys()

        if self.add_comments:
            self._add_comments = self.add_comments.split(',')

    def run(self):
        mappings = self._get_mappings()
        outfile = open(self.output_file, 'w')
        try:
            catalog = Catalog(project=self.distribution.get_name(),
                              version=self.distribution.get_version(),
                              msgid_bugs_address=self.msgid_bugs_address,
                              copyright_holder=self.copyright_holder,
                              charset=self.charset)

            for dirname, (method_map, options_map) in mappings.items():
                def callback(filename, method, options):
                    if method == 'ignore':
                        return
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    optstr = ''
                    if options:
                        optstr = ' (%s)' % ', '.join(['%s="%s"' % (k, v) for
                                                      k, v in options.items()])
                    log.info('extracting messages from %s%s', filepath, optstr)

                extracted = extract_from_dir(dirname, method_map, options_map,
                                             keywords=self._keywords,
                                             comment_tags=self._add_comments,
                                             callback=callback,
                                             strip_comment_tags=
                                                self.strip_comments)
                for filename, lineno, message, comments in extracted:
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    catalog.add(message, None, [(filepath, lineno)],
                                auto_comments=comments)

            log.info('writing PO template file to %s' % self.output_file)
            write_po(outfile, catalog, width=self.width,
                     no_location=self.no_location,
                     omit_header=self.omit_header,
                     sort_output=self.sort_output,
                     sort_by_file=self.sort_by_file)
        finally:
            outfile.close()

    def _get_mappings(self):
        mappings = {}

        if self.mapping_file:
            fileobj = open(self.mapping_file, 'U')
            try:
                method_map, options_map = parse_mapping(fileobj)
                for dirname in self.input_dirs:
                    mappings[dirname] = method_map, options_map
            finally:
                fileobj.close()

        elif getattr(self.distribution, 'message_extractors', None):
            message_extractors = self.distribution.message_extractors
            for dirname, mapping in message_extractors.items():
                if isinstance(mapping, basestring):
                    method_map, options_map = parse_mapping(StringIO(mapping))
                else:
                    method_map, options_map = [], {}
                    for pattern, method, options in mapping:
                        method_map.append((pattern, method))
                        options_map[pattern] = options or {}
                mappings[dirname] = method_map, options_map

        else:
            for dirname in self.input_dirs:
                mappings[dirname] = DEFAULT_MAPPING, {}

        return mappings


def check_message_extractors(dist, name, value):
    """Validate the ``message_extractors`` keyword argument to ``setup()``.

    :param dist: the distutils/setuptools ``Distribution`` object
    :param name: the name of the keyword argument (should always be
                 "message_extractors")
    :param value: the value of the keyword argument
    :raise `DistutilsSetupError`: if the value is not valid
    :see: `Adding setup() arguments
           <http://peak.telecommunity.com/DevCenter/setuptools#adding-setup-arguments>`_
    """
    assert name == 'message_extractors'
    if not isinstance(value, dict):
        raise DistutilsSetupError('the value of the "message_extractors" '
                                  'parameter must be a dictionary')


class init_catalog(Command):
    """New catalog initialization command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import init_catalog

        setup(
            ...
            cmdclass = {'init_catalog': init_catalog}
        )

    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'create a new catalog based on a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to output directory'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale for the new localized catalog'),
    ]

    def initialize_options(self):
        self.output_dir = None
        self.output_file = None
        self.input_file = None
        self.locale = None
        self.domain = 'messages'

    def finalize_options(self):
        if not self.input_file:
            raise DistutilsOptionError('you must specify the input file')

        if not self.locale:
            raise DistutilsOptionError('you must provide a locale for the '
                                       'new catalog')
        try:
            self._locale = Locale.parse(self.locale)
        except UnknownLocaleError, e:
            raise DistutilsOptionError(e)

        if not self.output_file and not self.output_dir:
            raise DistutilsOptionError('you must specify the output directory')
        if not self.output_file:
            self.output_file = os.path.join(self.output_dir, self.locale,
                                            'LC_MESSAGES', self.domain + '.po')

        if not os.path.exists(os.path.dirname(self.output_file)):
            os.makedirs(os.path.dirname(self.output_file))

    def run(self):
        log.info('creating catalog %r based on %r', self.output_file,
                 self.input_file)

        infile = open(self.input_file, 'r')
        try:
            # Although reading from the catalog template, read_po must be fed
            # the locale in order to correcly calculate plurals
            catalog = read_po(infile, locale=self.locale)
        finally:
            infile.close()

        catalog.locale = self._locale
        catalog.fuzzy = False

        outfile = open(self.output_file, 'w')
        try:
            write_po(outfile, catalog)
        finally:
            outfile.close()


class update_catalog(Command):
    """Catalog merging command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import update_catalog

        setup(
            ...
            cmdclass = {'update_catalog': update_catalog}
        )

    :since: version 0.9
    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'update message catalogs from a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to base directory containing the catalogs'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('ignore-obsolete=', None,
         'whether to omit obsolete messages from the output'),
        ('no-fuzzy-matching', 'N',
         'do not use fuzzy matching'),
        ('previous', None,
         'keep previous msgids of translated messages')
    ]
    boolean_options = ['ignore_obsolete', 'no_fuzzy_matching', 'previous']

    def initialize_options(self):
        self.domain = 'messages'
        self.input_file = None
        self.output_dir = None
        self.output_file = None
        self.locale = None
        self.ignore_obsolete = False
        self.no_fuzzy_matching = False
        self.previous = False

    def finalize_options(self):
        if not self.input_file:
            raise DistutilsOptionError('you must specify the input file')
        if not self.output_file and not self.output_dir:
            raise DistutilsOptionError('you must specify the output file or '
                                       'directory')
        if self.output_file and not self.locale:
            raise DistutilsOptionError('you must specify the locale')
        if self.no_fuzzy_matching and self.previous:
            self.previous = False

    def run(self):
        po_files = []
        if not self.output_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.output_dir, self.locale,
                                              'LC_MESSAGES',
                                              self.domain + '.po')))
            else:
                for locale in os.listdir(self.output_dir):
                    po_file = os.path.join(self.output_dir, locale,
                                           'LC_MESSAGES',
                                           self.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
        else:
            po_files.append((self.locale, self.output_file))

        domain = self.domain
        if not domain:
            domain = os.path.splitext(os.path.basename(self.input_file))[0]

        infile = open(self.input_file, 'U')
        try:
            template = read_po(infile)
        finally:
            infile.close()

        if not po_files:
            raise DistutilsOptionError('no message catalogs found')

        for locale, filename in po_files:
            log.info('updating catalog %r based on %r', filename,
                     self.input_file)
            infile = open(filename, 'U')
            try:
                catalog = read_po(infile, locale=locale, domain=domain)
            finally:
                infile.close()

            catalog.update(template, self.no_fuzzy_matching)

            tmpname = os.path.join(os.path.dirname(filename),
                                   tempfile.gettempprefix() +
                                   os.path.basename(filename))
            tmpfile = open(tmpname, 'w')
            try:
                try:
                    write_po(tmpfile, catalog,
                             ignore_obsolete=self.ignore_obsolete,
                             include_previous=self.previous)
                finally:
                    tmpfile.close()
            except:
                os.remove(tmpname)
                raise

            try:
                os.rename(tmpname, filename)
            except OSError:
                # We're probably on Windows, which doesn't support atomic
                # renames, at least not through Python
                # If the error is in fact due to a permissions problem, that
                # same error is going to be raised from one of the following
                # operations
                os.remove(filename)
                shutil.copy(tmpname, filename)
                os.remove(tmpname)


class CommandLineInterface(object):
    """Command-line interface.

    This class provides a simple command-line interface to the message
    extraction and PO file generation functionality.
    """

    usage = '%%prog %s [options] %s'
    version = '%%prog %s' % VERSION
    commands = {
        'compile': 'compile message catalogs to MO files',
        'extract': 'extract messages from source files and generate a POT file',
        'init':    'create new message catalogs from a POT file',
        'update':  'update existing message catalogs from a POT file'
    }

    def run(self, argv=sys.argv):
        """Main entry point of the command-line interface.

        :param argv: list of arguments passed on the command-line
        """
        self.parser = OptionParser(usage=self.usage % ('command', '[args]'),
                                   version=self.version)
        self.parser.disable_interspersed_args()
        self.parser.print_help = self._help
        self.parser.add_option('--list-locales', dest='list_locales',
                               action='store_true',
                               help="print all known locales and exit")
        self.parser.add_option('-v', '--verbose', action='store_const',
                               dest='loglevel', const=logging.DEBUG,
                               help='print as much as possible')
        self.parser.add_option('-q', '--quiet', action='store_const',
                               dest='loglevel', const=logging.ERROR,
                               help='print as little as possible')
        self.parser.set_defaults(list_locales=False, loglevel=logging.INFO)

        options, args = self.parser.parse_args(argv[1:])

        self._configure_logging(options.loglevel)
        if options.list_locales:
            identifiers = localedata.list()
            longest = max([len(identifier) for identifier in identifiers])
            identifiers.sort()
            format = u'%%-%ds %%s' % (longest + 1)
            for identifier in identifiers:
                locale = Locale.parse(identifier)
                output = format % (identifier, locale.english_name)
                print output.encode(sys.stdout.encoding or
                                    getpreferredencoding() or
                                    'ascii', 'replace')
            return 0

        if not args:
            self.parser.error('no valid command or option passed. '
                              'Try the -h/--help option for more information.')

        cmdname = args[0]
        if cmdname not in self.commands:
            self.parser.error('unknown command "%s"' % cmdname)

        return getattr(self, cmdname)(args[1:])

    def _configure_logging(self, loglevel):
        self.log = logging.getLogger('babel')
        self.log.setLevel(loglevel)
        # Don't add a new handler for every instance initialization (#227), this
        # would cause duplicated output when the CommandLineInterface as an
        # normal Python class.
        if self.log.handlers:
            handler = self.log.handlers[0]
        else:
            handler = logging.StreamHandler()
            self.log.addHandler(handler)
        handler.setLevel(loglevel)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

    def _help(self):
        print self.parser.format_help()
        print "commands:"
        longest = max([len(command) for command in self.commands])
        format = "  %%-%ds %%s" % max(8, longest + 1)
        commands = self.commands.items()
        commands.sort()
        for name, description in commands:
            print format % (name, description)

    def compile(self, argv):
        """Subcommand for compiling a message catalog to a MO file.

        :param argv: the command arguments
        :since: version 0.9
        """
        parser = OptionParser(usage=self.usage % ('compile', ''),
                              description=self.commands['compile'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of MO and PO files (default '%default')")
        parser.add_option('--directory', '-d', dest='directory',
                          metavar='DIR', help='base directory of catalog files')
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale of the catalog')
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.mo')")
        parser.add_option('--use-fuzzy', '-f', dest='use_fuzzy',
                          action='store_true',
                          help='also include fuzzy translations (default '
                               '%default)')
        parser.add_option('--statistics', dest='statistics',
                          action='store_true',
                          help='print statistics about translations')

        parser.set_defaults(domain='messages', use_fuzzy=False,
                            compile_all=False, statistics=False)
        options, args = parser.parse_args(argv)

        po_files = []
        mo_files = []
        if not options.input_file:
            if not options.directory:
                parser.error('you must specify either the input file or the '
                             'base directory')
            if options.locale:
                po_files.append((options.locale,
                                 os.path.join(options.directory,
                                              options.locale, 'LC_MESSAGES',
                                              options.domain + '.po')))
                mo_files.append(os.path.join(options.directory, options.locale,
                                             'LC_MESSAGES',
                                             options.domain + '.mo'))
            else:
                for locale in os.listdir(options.directory):
                    po_file = os.path.join(options.directory, locale,
                                           'LC_MESSAGES', options.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        mo_files.append(os.path.join(options.directory, locale,
                                                     'LC_MESSAGES',
                                                     options.domain + '.mo'))
        else:
            po_files.append((options.locale, options.input_file))
            if options.output_file:
                mo_files.append(options.output_file)
            else:
                if not options.directory:
                    parser.error('you must specify either the input file or '
                                 'the base directory')
                mo_files.append(os.path.join(options.directory, options.locale,
                                             'LC_MESSAGES',
                                             options.domain + '.mo'))
        if not po_files:
            parser.error('no message catalogs found')

        for idx, (locale, po_file) in enumerate(po_files):
            mo_file = mo_files[idx]
            infile = open(po_file, 'r')
            try:
                catalog = read_po(infile, locale)
            finally:
                infile.close()

            if options.statistics:
                translated = 0
                for message in list(catalog)[1:]:
                    if message.string:
                        translated +=1
                percentage = 0
                if len(catalog):
                    percentage = translated * 100 // len(catalog)
                self.log.info("%d of %d messages (%d%%) translated in %r",
                              translated, len(catalog), percentage, po_file)

            if catalog.fuzzy and not options.use_fuzzy:
                self.log.warn('catalog %r is marked as fuzzy, skipping',
                              po_file)
                continue

            for message, errors in catalog.check():
                for error in errors:
                    self.log.error('error: %s:%d: %s', po_file, message.lineno,
                                   error)

            self.log.info('compiling catalog %r to %r', po_file, mo_file)

            outfile = open(mo_file, 'wb')
            try:
                write_mo(outfile, catalog, use_fuzzy=options.use_fuzzy)
            finally:
                outfile.close()

    def extract(self, argv):
        """Subcommand for extracting messages from source files and generating
        a POT file.

        :param argv: the command arguments
        """
        parser = OptionParser(usage=self.usage % ('extract', 'dir1 <dir2> ...'),
                              description=self.commands['extract'])
        parser.add_option('--charset', dest='charset',
                          help='charset to use in the output (default '
                               '"%default")')
        parser.add_option('-k', '--keyword', dest='keywords', action='append',
                          help='keywords to look for in addition to the '
                               'defaults. You can specify multiple -k flags on '
                               'the command line.')
        parser.add_option('--no-default-keywords', dest='no_default_keywords',
                          action='store_true',
                          help="do not include the default keywords")
        parser.add_option('--mapping', '-F', dest='mapping_file',
                          help='path to the extraction mapping file')
        parser.add_option('--no-location', dest='no_location',
                          action='store_true',
                          help='do not include location comments with filename '
                               'and line number')
        parser.add_option('--omit-header', dest='omit_header',
                          action='store_true',
                          help='do not include msgid "" entry in header')
        parser.add_option('-o', '--output', dest='output',
                          help='path to the output POT file')
        parser.add_option('-w', '--width', dest='width', type='int',
                          help="set output line width (default 76)")
        parser.add_option('--no-wrap', dest='no_wrap', action = 'store_true',
                          help='do not break long message lines, longer than '
                               'the output line width, into several lines')
        parser.add_option('--sort-output', dest='sort_output',
                          action='store_true',
                          help='generate sorted output (default False)')
        parser.add_option('--sort-by-file', dest='sort_by_file',
                          action='store_true',
                          help='sort output by file location (default False)')
        parser.add_option('--msgid-bugs-address', dest='msgid_bugs_address',
                          metavar='EMAIL@ADDRESS',
                          help='set report address for msgid')
        parser.add_option('--copyright-holder', dest='copyright_holder',
                          help='set copyright holder in output')
        parser.add_option('--project', dest='project',
                          help='set project name in output')
        parser.add_option('--version', dest='version',
                          help='set project version in output')
        parser.add_option('--add-comments', '-c', dest='comment_tags',
                          metavar='TAG', action='append',
                          help='place comment block with TAG (or those '
                               'preceding keyword lines) in output file. One '
                               'TAG per argument call')
        parser.add_option('--strip-comment-tags', '-s',
                          dest='strip_comment_tags', action='store_true',
                          help='Strip the comment tags from the comments.')

        parser.set_defaults(charset='utf-8', keywords=[],
                            no_default_keywords=False, no_location=False,
                            omit_header = False, width=None, no_wrap=False,
                            sort_output=False, sort_by_file=False,
                            comment_tags=[], strip_comment_tags=False)
        options, args = parser.parse_args(argv)
        if not args:
            parser.error('incorrect number of arguments')

        if options.output not in (None, '-'):
            outfile = open(options.output, 'w')
        else:
            outfile = sys.stdout

        keywords = DEFAULT_KEYWORDS.copy()
        if options.no_default_keywords:
            if not options.keywords:
                parser.error('you must specify new keywords if you disable the '
                             'default ones')
            keywords = {}
        if options.keywords:
            keywords.update(parse_keywords(options.keywords))

        if options.mapping_file:
            fileobj = open(options.mapping_file, 'U')
            try:
                method_map, options_map = parse_mapping(fileobj)
            finally:
                fileobj.close()
        else:
            method_map = DEFAULT_MAPPING
            options_map = {}

        if options.width and options.no_wrap:
            parser.error("'--no-wrap' and '--width' are mutually exclusive.")
        elif not options.width and not options.no_wrap:
            options.width = 76

        if options.sort_output and options.sort_by_file:
            parser.error("'--sort-output' and '--sort-by-file' are mutually "
                         "exclusive")

        try:
            catalog = Catalog(project=options.project,
                              version=options.version,
                              msgid_bugs_address=options.msgid_bugs_address,
                              copyright_holder=options.copyright_holder,
                              charset=options.charset)

            for dirname in args:
                if not os.path.isdir(dirname):
                    parser.error('%r is not a directory' % dirname)

                def callback(filename, method, options):
                    if method == 'ignore':
                        return
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    optstr = ''
                    if options:
                        optstr = ' (%s)' % ', '.join(['%s="%s"' % (k, v) for
                                                      k, v in options.items()])
                    self.log.info('extracting messages from %s%s', filepath,
                                  optstr)

                extracted = extract_from_dir(dirname, method_map, options_map,
                                             keywords, options.comment_tags,
                                             callback=callback,
                                             strip_comment_tags=
                                                options.strip_comment_tags)
                for filename, lineno, message, comments in extracted:
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    catalog.add(message, None, [(filepath, lineno)],
                                auto_comments=comments)

            if options.output not in (None, '-'):
                self.log.info('writing PO template file to %s' % options.output)
            write_po(outfile, catalog, width=options.width,
                     no_location=options.no_location,
                     omit_header=options.omit_header,
                     sort_output=options.sort_output,
                     sort_by_file=options.sort_by_file)
        finally:
            if options.output:
                outfile.close()

    def init(self, argv):
        """Subcommand for creating new message catalogs from a template.

        :param argv: the command arguments
        """
        parser = OptionParser(usage=self.usage % ('init', ''),
                              description=self.commands['init'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of PO file (default '%default')")
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-dir', '-d', dest='output_dir',
                          metavar='DIR', help='path to output directory')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.po')")
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale for the new localized catalog')

        parser.set_defaults(domain='messages')
        options, args = parser.parse_args(argv)

        if not options.locale:
            parser.error('you must provide a locale for the new catalog')
        try:
            locale = Locale.parse(options.locale)
        except UnknownLocaleError, e:
            parser.error(e)

        if not options.input_file:
            parser.error('you must specify the input file')

        if not options.output_file and not options.output_dir:
            parser.error('you must specify the output file or directory')

        if not options.output_file:
            options.output_file = os.path.join(options.output_dir,
                                               options.locale, 'LC_MESSAGES',
                                               options.domain + '.po')
        if not os.path.exists(os.path.dirname(options.output_file)):
            os.makedirs(os.path.dirname(options.output_file))

        infile = open(options.input_file, 'r')
        try:
            # Although reading from the catalog template, read_po must be fed
            # the locale in order to correcly calculate plurals
            catalog = read_po(infile, locale=options.locale)
        finally:
            infile.close()

        catalog.locale = locale
        catalog.revision_date = datetime.now(LOCALTZ)

        self.log.info('creating catalog %r based on %r', options.output_file,
                      options.input_file)

        outfile = open(options.output_file, 'w')
        try:
            write_po(outfile, catalog)
        finally:
            outfile.close()

    def update(self, argv):
        """Subcommand for updating existing message catalogs from a template.

        :param argv: the command arguments
        :since: version 0.9
        """
        parser = OptionParser(usage=self.usage % ('update', ''),
                              description=self.commands['update'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of PO file (default '%default')")
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-dir', '-d', dest='output_dir',
                          metavar='DIR', help='path to output directory')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.po')")
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale of the translations catalog')
        parser.add_option('--ignore-obsolete', dest='ignore_obsolete',
                          action='store_true',
                          help='do not include obsolete messages in the output '
                               '(default %default)')
        parser.add_option('--no-fuzzy-matching', '-N', dest='no_fuzzy_matching',
                          action='store_true',
                          help='do not use fuzzy matching (default %default)')
        parser.add_option('--previous', dest='previous', action='store_true',
                          help='keep previous msgids of translated messages '
                               '(default %default)')

        parser.set_defaults(domain='messages', ignore_obsolete=False,
                            no_fuzzy_matching=False, previous=False)
        options, args = parser.parse_args(argv)

        if not options.input_file:
            parser.error('you must specify the input file')
        if not options.output_file and not options.output_dir:
            parser.error('you must specify the output file or directory')
        if options.output_file and not options.locale:
            parser.error('you must specify the locale')
        if options.no_fuzzy_matching and options.previous:
            options.previous = False

        po_files = []
        if not options.output_file:
            if options.locale:
                po_files.append((options.locale,
                                 os.path.join(options.output_dir,
                                              options.locale, 'LC_MESSAGES',
                                              options.domain + '.po')))
            else:
                for locale in os.listdir(options.output_dir):
                    po_file = os.path.join(options.output_dir, locale,
                                           'LC_MESSAGES',
                                           options.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
        else:
            po_files.append((options.locale, options.output_file))

        domain = options.domain
        if not domain:
            domain = os.path.splitext(os.path.basename(options.input_file))[0]

        infile = open(options.input_file, 'U')
        try:
            template = read_po(infile)
        finally:
            infile.close()

        if not po_files:
            parser.error('no message catalogs found')

        for locale, filename in po_files:
            self.log.info('updating catalog %r based on %r', filename,
                          options.input_file)
            infile = open(filename, 'U')
            try:
                catalog = read_po(infile, locale=locale, domain=domain)
            finally:
                infile.close()

            catalog.update(template, options.no_fuzzy_matching)

            tmpname = os.path.join(os.path.dirname(filename),
                                   tempfile.gettempprefix() +
                                   os.path.basename(filename))
            tmpfile = open(tmpname, 'w')
            try:
                try:
                    write_po(tmpfile, catalog,
                             ignore_obsolete=options.ignore_obsolete,
                             include_previous=options.previous)
                finally:
                    tmpfile.close()
            except:
                os.remove(tmpname)
                raise

            try:
                os.rename(tmpname, filename)
            except OSError:
                # We're probably on Windows, which doesn't support atomic
                # renames, at least not through Python
                # If the error is in fact due to a permissions problem, that
                # same error is going to be raised from one of the following
                # operations
                os.remove(filename)
                shutil.copy(tmpname, filename)
                os.remove(tmpname)


def main():
    return CommandLineInterface().run(sys.argv)

def parse_mapping(fileobj, filename=None):
    """Parse an extraction method mapping from a file-like object.

    >>> buf = StringIO('''
    ... [extractors]
    ... custom = mypackage.module:myfunc
    ... 
    ... # Python source files
    ... [python: **.py]
    ...
    ... # Genshi templates
    ... [genshi: **/templates/**.html]
    ... include_attrs =
    ... [genshi: **/templates/**.txt]
    ... template_class = genshi.template:TextTemplate
    ... encoding = latin-1
    ... 
    ... # Some custom extractor
    ... [custom: **/custom/*.*]
    ... ''')

    >>> method_map, options_map = parse_mapping(buf)
    >>> len(method_map)
    4

    >>> method_map[0]
    ('**.py', 'python')
    >>> options_map['**.py']
    {}
    >>> method_map[1]
    ('**/templates/**.html', 'genshi')
    >>> options_map['**/templates/**.html']['include_attrs']
    ''
    >>> method_map[2]
    ('**/templates/**.txt', 'genshi')
    >>> options_map['**/templates/**.txt']['template_class']
    'genshi.template:TextTemplate'
    >>> options_map['**/templates/**.txt']['encoding']
    'latin-1'

    >>> method_map[3]
    ('**/custom/*.*', 'mypackage.module:myfunc')
    >>> options_map['**/custom/*.*']
    {}

    :param fileobj: a readable file-like object containing the configuration
                    text to parse
    :return: a `(method_map, options_map)` tuple
    :rtype: `tuple`
    :see: `extract_from_directory`
    """
    extractors = {}
    method_map = []
    options_map = {}

    parser = RawConfigParser()
    parser._sections = odict(parser._sections) # We need ordered sections
    parser.readfp(fileobj, filename)
    for section in parser.sections():
        if section == 'extractors':
            extractors = dict(parser.items(section))
        else:
            method, pattern = [part.strip() for part in section.split(':', 1)]
            method_map.append((pattern, method))
            options_map[pattern] = dict(parser.items(section))

    if extractors:
        for idx, (pattern, method) in enumerate(method_map):
            if method in extractors:
                method = extractors[method]
            method_map[idx] = (pattern, method)

    return (method_map, options_map)

def parse_keywords(strings=[]):
    """Parse keywords specifications from the given list of strings.

    >>> kw = parse_keywords(['_', 'dgettext:2', 'dngettext:2,3']).items()
    >>> kw.sort()
    >>> for keyword, indices in kw:
    ...     print (keyword, indices)
    ('_', None)
    ('dgettext', (2,))
    ('dngettext', (2, 3))
    """
    keywords = {}
    for string in strings:
        if ':' in string:
            funcname, indices = string.split(':')
        else:
            funcname, indices = string, None
        if funcname not in keywords:
            if indices:
                indices = tuple([(int(x)) for x in indices.split(',')])
            keywords[funcname] = indices
    return keywords


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = jslexer
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""A simple JavaScript 1.5 lexer which is used for the JavaScript
extractor.
"""

import re

from babel.util import itemgetter


operators = [
    '+', '-', '*', '%', '!=', '==', '<', '>', '<=', '>=', '=',
    '+=', '-=', '*=', '%=', '<<', '>>', '>>>', '<<=', '>>=',
    '>>>=', '&', '&=', '|', '|=', '&&', '||', '^', '^=', '(', ')',
    '[', ']', '{', '}', '!', '--', '++', '~', ',', ';', '.', ':'
]
operators.sort(lambda a, b: cmp(-len(a), -len(b)))

escapes = {'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}

rules = [
    (None, re.compile(r'\s+(?u)')),
    (None, re.compile(r'<!--.*')),
    ('linecomment', re.compile(r'//.*')),
    ('multilinecomment', re.compile(r'/\*.*?\*/(?us)')),
    ('name', re.compile(r'(\$+\w*|[^\W\d]\w*)(?u)')),
    ('number', re.compile(r'''(?x)(
        (?:0|[1-9]\d*)
        (\.\d+)?
        ([eE][-+]?\d+)? |
        (0x[a-fA-F0-9]+)
    )''')),
    ('operator', re.compile(r'(%s)' % '|'.join(map(re.escape, operators)))),
    ('string', re.compile(r'''(?xs)(
        '(?:[^'\\]*(?:\\.[^'\\]*)*)'  |
        "(?:[^"\\]*(?:\\.[^"\\]*)*)"
    )'''))
]

division_re = re.compile(r'/=?')
regex_re = re.compile(r'/(?:[^/\\]*(?:\\.[^/\\]*)*)/[a-zA-Z]*(?s)')
line_re = re.compile(r'(\r\n|\n|\r)')
line_join_re = re.compile(r'\\' + line_re.pattern)
uni_escape_re = re.compile(r'[a-fA-F0-9]{1,4}')


class Token(tuple):
    """Represents a token as returned by `tokenize`."""
    __slots__ = ()

    def __new__(cls, type, value, lineno):
        return tuple.__new__(cls, (type, value, lineno))

    type = property(itemgetter(0))
    value = property(itemgetter(1))
    lineno = property(itemgetter(2))


def indicates_division(token):
    """A helper function that helps the tokenizer to decide if the current
    token may be followed by a division operator.
    """
    if token.type == 'operator':
        return token.value in (')', ']', '}', '++', '--')
    return token.type in ('name', 'number', 'string', 'regexp')


def unquote_string(string):
    """Unquote a string with JavaScript rules.  The string has to start with
    string delimiters (``'`` or ``"``.)

    :return: a string
    """
    assert string and string[0] == string[-1] and string[0] in '"\'', \
        'string provided is not properly delimited'
    string = line_join_re.sub('\\1', string[1:-1])
    result = []
    add = result.append
    pos = 0

    while 1:
        # scan for the next escape
        escape_pos = string.find('\\', pos)
        if escape_pos < 0:
            break
        add(string[pos:escape_pos])

        # check which character is escaped
        next_char = string[escape_pos + 1]
        if next_char in escapes:
            add(escapes[next_char])

        # unicode escapes.  trie to consume up to four characters of
        # hexadecimal characters and try to interpret them as unicode
        # character point.  If there is no such character point, put
        # all the consumed characters into the string.
        elif next_char in 'uU':
            escaped = uni_escape_re.match(string, escape_pos + 2)
            if escaped is not None:
                escaped_value = escaped.group()
                if len(escaped_value) == 4:
                    try:
                        add(unichr(int(escaped_value, 16)))
                    except ValueError:
                        pass
                    else:
                        pos = escape_pos + 6
                        continue
                add(next_char + escaped_value)
                pos = escaped.end()
                continue
            else:
                add(next_char)

        # bogus escape.  Just remove the backslash.
        else:
            add(next_char)
        pos = escape_pos + 2

    if pos < len(string):
        add(string[pos:])

    return u''.join(result)


def tokenize(source):
    """Tokenize a JavaScript source.

    :return: generator of `Token`\s
    """
    may_divide = False
    pos = 0
    lineno = 1
    end = len(source)

    while pos < end:
        # handle regular rules first
        for token_type, rule in rules:
            match = rule.match(source, pos)
            if match is not None:
                break
        # if we don't have a match we don't give up yet, but check for
        # division operators or regular expression literals, based on
        # the status of `may_divide` which is determined by the last
        # processed non-whitespace token using `indicates_division`.
        else:
            if may_divide:
                match = division_re.match(source, pos)
                token_type = 'operator'
            else:
                match = regex_re.match(source, pos)
                token_type = 'regexp'
            if match is None:
                # woops. invalid syntax. jump one char ahead and try again.
                pos += 1
                continue

        token_value = match.group()
        if token_type is not None:
            token = Token(token_type, token_value, lineno)
            may_divide = indicates_division(token)
            yield token
        lineno += len(line_re.findall(token_value))
        pos = match.end()

########NEW FILE########
__FILENAME__ = mofile
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Writing of files in the ``gettext`` MO (machine object) format.

:since: version 0.9
:see: `The Format of MO Files
       <http://www.gnu.org/software/gettext/manual/gettext.html#MO-Files>`_
"""

import array
import struct

__all__ = ['write_mo']
__docformat__ = 'restructuredtext en'

def write_mo(fileobj, catalog, use_fuzzy=False):
    """Write a catalog to the specified file-like object using the GNU MO file
    format.
    
    >>> from babel.messages import Catalog
    >>> from gettext import GNUTranslations
    >>> from StringIO import StringIO
    
    >>> catalog = Catalog(locale='en_US')
    >>> catalog.add('foo', 'Voh')
    >>> catalog.add((u'bar', u'baz'), (u'Bahr', u'Batz'))
    >>> catalog.add('fuz', 'Futz', flags=['fuzzy'])
    >>> catalog.add('Fizz', '')
    >>> catalog.add(('Fuzz', 'Fuzzes'), ('', ''))
    >>> buf = StringIO()
    
    >>> write_mo(buf, catalog)
    >>> buf.seek(0)
    >>> translations = GNUTranslations(fp=buf)
    >>> translations.ugettext('foo')
    u'Voh'
    >>> translations.ungettext('bar', 'baz', 1)
    u'Bahr'
    >>> translations.ungettext('bar', 'baz', 2)
    u'Batz'
    >>> translations.ugettext('fuz')
    u'fuz'
    >>> translations.ugettext('Fizz')
    u'Fizz'
    >>> translations.ugettext('Fuzz')
    u'Fuzz'
    >>> translations.ugettext('Fuzzes')
    u'Fuzzes'
    
    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param use_fuzzy: whether translations marked as "fuzzy" should be included
                      in the output
    """
    messages = list(catalog)
    if not use_fuzzy:
        messages[1:] = [m for m in messages[1:] if not m.fuzzy]
    messages.sort()

    ids = strs = ''
    offsets = []

    for message in messages:
        # For each string, we need size and file offset.  Each string is NUL
        # terminated; the NUL does not count into the size.
        if message.pluralizable:
            msgid = '\x00'.join([
                msgid.encode(catalog.charset) for msgid in message.id
            ])
            msgstrs = []
            for idx, string in enumerate(message.string):
                if not string:
                    msgstrs.append(message.id[min(int(idx), 1)])
                else:
                    msgstrs.append(string)
            msgstr = '\x00'.join([
                msgstr.encode(catalog.charset) for msgstr in msgstrs
            ])
        else:
            msgid = message.id.encode(catalog.charset)
            if not message.string:
                msgstr = message.id.encode(catalog.charset)
            else:
                msgstr = message.string.encode(catalog.charset)
        offsets.append((len(ids), len(msgid), len(strs), len(msgstr)))
        ids += msgid + '\x00'
        strs += msgstr + '\x00'

    # The header is 7 32-bit unsigned integers.  We don't use hash tables, so
    # the keys start right after the index tables.
    keystart = 7 * 4 + 16 * len(messages)
    valuestart = keystart + len(ids)

    # The string table first has the list of keys, then the list of values.
    # Each entry has first the size of the string, then the file offset.
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    offsets = koffsets + voffsets

    fileobj.write(struct.pack('Iiiiiii',
        0x950412deL,                # magic
        0,                          # version
        len(messages),              # number of entries
        7 * 4,                      # start of key index
        7 * 4 + len(messages) * 8,  # start of value index
        0, 0                        # size and offset of hash table
    ) + array.array("i", offsets).tostring() + ids + strs)

########NEW FILE########
__FILENAME__ = plurals
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Plural form definitions."""

from babel.core import default_locale, Locale
from babel.util import itemgetter


LC_CTYPE = default_locale('LC_CTYPE')


PLURALS = {
    # Afar
    # 'aa': (),
    # Abkhazian
    # 'ab': (),
    # Avestan
    # 'ae': (),
    # Afrikaans - From Pootle's PO's
    'af': (2, '(n != 1)'),
    # Akan
    # 'ak': (),
    # Amharic
    # 'am': (),
    # Aragonese
    # 'an': (),
    # Arabic - From Pootle's PO's
    'ar': (6, '(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n>=3 && n<=10 ? 3 : n>=11 && n<=99 ? 4 : 5)'),
    # Assamese
    # 'as': (),
    # Avaric
    # 'av': (),
    # Aymara
    # 'ay': (),
    # Azerbaijani
    # 'az': (),
    # Bashkir
    # 'ba': (),
    # Belarusian
    # 'be': (),
    # Bulgarian - From Pootle's PO's
    'bg': (2, '(n != 1)'),
    # Bihari
    # 'bh': (),
    # Bislama
    # 'bi': (),
    # Bambara
    # 'bm': (),
    # Bengali - From Pootle's PO's
    'bn': (2, '(n != 1)'),
    # Tibetan - as discussed in private with Andrew West
    'bo': (1, '0'),
    # Breton
    # 'br': (),
    # Bosnian
    # 'bs': (),
    # Catalan - From Pootle's PO's
    'ca': (2, '(n != 1)'),
    # Chechen
    # 'ce': (),
    # Chamorro
    # 'ch': (),
    # Corsican
    # 'co': (),
    # Cree
    # 'cr': (),
    # Czech
    'cs': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Church Slavic
    # 'cu': (),
    # Chuvash
    'cv': (1, '0'),
    # Welsh
    'cy': (5, '(n==1 ? 1 : n==2 ? 2 : n==3 ? 3 : n==6 ? 4 : 0)'),
    # Danish
    'da': (2, '(n != 1)'),
    # German
    'de': (2, '(n != 1)'),
    # Divehi
    # 'dv': (),
    # Dzongkha
    'dz': (1, '0'),
    # Greek
    'el': (2, '(n != 1)'),
    # English
    'en': (2, '(n != 1)'),
    # Esperanto
    'eo': (2, '(n != 1)'),
    # Spanish
    'es': (2, '(n != 1)'),
    # Estonian
    'et': (2, '(n != 1)'),
    # Basque - From Pootle's PO's
    'eu': (2, '(n != 1)'),
    # Persian - From Pootle's PO's
    'fa': (1, '0'),
    # Finnish
    'fi': (2, '(n != 1)'),
    # French
    'fr': (2, '(n > 1)'),
    # Friulian - From Pootle's PO's
    'fur': (2, '(n > 1)'),
    # Irish
    'ga': (3, '(n==1 ? 0 : n==2 ? 1 : 2)'),
    # Galician - From Pootle's PO's
    'gl': (2, '(n != 1)'),
    # Hausa - From Pootle's PO's
    'ha': (2, '(n != 1)'),
    # Hebrew
    'he': (2, '(n != 1)'),
    # Hindi - From Pootle's PO's
    'hi': (2, '(n != 1)'),
    # Croatian
    'hr': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Hungarian
    'hu': (1, '0'),
    # Armenian - From Pootle's PO's
    'hy': (1, '0'),
    # Icelandic - From Pootle's PO's
    'is': (2, '(n != 1)'),
    # Italian
    'it': (2, '(n != 1)'),
    # Japanese
    'ja': (1, '0'),
    # Georgian - From Pootle's PO's
    'ka': (1, '0'),
    # Kongo - From Pootle's PO's
    'kg': (2, '(n != 1)'),
    # Khmer - From Pootle's PO's
    'km': (1, '0'),
    # Korean
    'ko': (1, '0'),
    # Kurdish - From Pootle's PO's
    'ku': (2, '(n != 1)'),
    # Lao - Another member of the Tai language family, like Thai.
    'lo': (1, '0'),
    # Lithuanian
    'lt': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Latvian
    'lv': (3, '(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2)'),
    # Maltese - From Pootle's PO's
    'mt': (4, '(n==1 ? 0 : n==0 || ( n%100>1 && n%100<11) ? 1 : (n%100>10 && n%100<20 ) ? 2 : 3)'),
    # Norwegian Bokmål
    'nb': (2, '(n != 1)'),
    # Dutch
    'nl': (2, '(n != 1)'),
    # Norwegian Nynorsk
    'nn': (2, '(n != 1)'),
    # Norwegian
    'no': (2, '(n != 1)'),
    # Punjabi - From Pootle's PO's
    'pa': (2, '(n != 1)'),
    # Polish
    'pl': (3, '(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Portuguese
    'pt': (2, '(n != 1)'),
    # Brazilian
    'pt_BR': (2, '(n > 1)'),
    # Romanian - From Pootle's PO's
    'ro': (3, '(n==1 ? 0 : (n==0 || (n%100 > 0 && n%100 < 20)) ? 1 : 2)'),
    # Russian
    'ru': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Slovak
    'sk': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Slovenian
    'sl': (4, '(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3)'),
    # Serbian - From Pootle's PO's
    'sr': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Southern Sotho - From Pootle's PO's
    'st': (2, '(n != 1)'),
    # Swedish
    'sv': (2, '(n != 1)'),
    # Thai
    'th': (1, '0'),
    # Turkish
    'tr': (1, '0'),
    # Ukrainian
    'uk': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Venda - From Pootle's PO's
    've': (2, '(n != 1)'),
    # Vietnamese - From Pootle's PO's
    'vi': (1, '0'),
    # Xhosa - From Pootle's PO's
    'xh': (2, '(n != 1)'),
    # Chinese - From Pootle's PO's
    'zh_CN': (1, '0'),
    'zh_HK': (1, '0'),
    'zh_TW': (1, '0'),
}


DEFAULT_PLURAL = (2, '(n != 1)')


class _PluralTuple(tuple):
    """A tuple with plural information."""

    __slots__ = ()
    num_plurals = property(itemgetter(0), doc="""
    The number of plurals used by the locale.""")
    plural_expr = property(itemgetter(1), doc="""
    The plural expression used by the locale.""")
    plural_forms = property(lambda x: 'npurals=%s; plural=%s' % x, doc="""
    The plural expression used by the catalog or locale.""")

    def __str__(self):
        return self.plural_forms


def get_plural(locale=LC_CTYPE):
    """A tuple with the information catalogs need to perform proper
    pluralization.  The first item of the tuple is the number of plural
    forms, the second the plural expression.

    >>> get_plural(locale='en')
    (2, '(n != 1)')
    >>> get_plural(locale='ga')
    (3, '(n==1 ? 0 : n==2 ? 1 : 2)')

    The object returned is a special tuple with additional members:

    >>> tup = get_plural("ja")
    >>> tup.num_plurals
    1
    >>> tup.plural_expr
    '0'
    >>> tup.plural_forms
    'npurals=1; plural=0'

    Converting the tuple into a string prints the plural forms for a
    gettext catalog:

    >>> str(tup)
    'npurals=1; plural=0'
    """
    locale = Locale.parse(locale)
    try:
        tup = PLURALS[str(locale)]
    except KeyError:
        try:
            tup = PLURALS[locale.language]
        except KeyError:
            tup = DEFAULT_PLURAL
    return _PluralTuple(tup)

########NEW FILE########
__FILENAME__ = pofile
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Reading and writing of files in the ``gettext`` PO (portable object)
format.

:see: `The Format of PO Files
       <http://www.gnu.org/software/gettext/manual/gettext.html#PO-Files>`_
"""

from datetime import date, datetime
import os
import re

from babel import __version__ as VERSION
from babel.messages.catalog import Catalog, Message
from babel.util import set, wraptext, LOCALTZ

__all__ = ['read_po', 'write_po']
__docformat__ = 'restructuredtext en'

def unescape(string):
    r"""Reverse `escape` the given string.

    >>> print unescape('"Say:\\n  \\"hello, world!\\"\\n"')
    Say:
      "hello, world!"
    <BLANKLINE>

    :param string: the string to unescape
    :return: the unescaped string
    :rtype: `str` or `unicode`
    """
    return string[1:-1].replace('\\\\', '\\') \
                       .replace('\\t', '\t') \
                       .replace('\\r', '\r') \
                       .replace('\\n', '\n') \
                       .replace('\\"', '\"')

def denormalize(string):
    r"""Reverse the normalization done by the `normalize` function.

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"hello, world!\"\n"''')
    Say:
      "hello, world!"
    <BLANKLINE>

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"Lorem ipsum dolor sit "
    ... "amet, consectetur adipisicing"
    ... " elit, \"\n"''')
    Say:
      "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    <BLANKLINE>

    :param string: the string to denormalize
    :return: the denormalized string
    :rtype: `unicode` or `str`
    """
    if string.startswith('""'):
        lines = []
        for line in string.splitlines()[1:]:
            lines.append(unescape(line))
        return ''.join(lines)
    else:
        return unescape(string)

def read_po(fileobj, locale=None, domain=None, ignore_obsolete=False):
    """Read messages from a ``gettext`` PO (portable object) file from the given
    file-like object and return a `Catalog`.

    >>> from StringIO import StringIO
    >>> buf = StringIO('''
    ... #: main.py:1
    ... #, fuzzy, python-format
    ... msgid "foo %(name)s"
    ... msgstr ""
    ...
    ... # A user comment
    ... #. An auto comment
    ... #: main.py:3
    ... msgid "bar"
    ... msgid_plural "baz"
    ... msgstr[0] ""
    ... msgstr[1] ""
    ... ''')
    >>> catalog = read_po(buf)
    >>> catalog.revision_date = datetime(2007, 04, 01)

    >>> for message in catalog:
    ...     if message.id:
    ...         print (message.id, message.string)
    ...         print ' ', (message.locations, message.flags)
    ...         print ' ', (message.user_comments, message.auto_comments)
    (u'foo %(name)s', '')
      ([(u'main.py', 1)], set([u'fuzzy', u'python-format']))
      ([], [])
    ((u'bar', u'baz'), ('', ''))
      ([(u'main.py', 3)], set([]))
      ([u'A user comment'], [u'An auto comment'])

    :param fileobj: the file-like object to read the PO file from
    :param locale: the locale identifier or `Locale` object, or `None`
                   if the catalog is not bound to a locale (which basically
                   means it's a template)
    :param domain: the message domain
    :param ignore_obsolete: whether to ignore obsolete messages in the input
    :return: an iterator over ``(message, translation, location)`` tuples
    :rtype: ``iterator``
    """
    catalog = Catalog(locale=locale, domain=domain)

    counter = [0]
    offset = [0]
    messages = []
    translations = []
    locations = []
    flags = []
    user_comments = []
    auto_comments = []
    obsolete = [False]
    in_msgid = [False]
    in_msgstr = [False]

    def _add_message():
        translations.sort()
        if len(messages) > 1:
            msgid = tuple([denormalize(m) for m in messages])
        else:
            msgid = denormalize(messages[0])
        if isinstance(msgid, (list, tuple)):
            string = []
            for idx in range(catalog.num_plurals):
                try:
                    string.append(translations[idx])
                except IndexError:
                    string.append((idx, ''))
            string = tuple([denormalize(t[1]) for t in string])
        else:
            string = denormalize(translations[0][1])
        message = Message(msgid, string, list(locations), set(flags),
                          auto_comments, user_comments, lineno=offset[0] + 1)
        if obsolete[0]:
            if not ignore_obsolete:
                catalog.obsolete[msgid] = message
        else:
            catalog[msgid] = message
        del messages[:]; del translations[:]; del locations[:];
        del flags[:]; del auto_comments[:]; del user_comments[:]
        obsolete[0] = False
        counter[0] += 1

    def _process_message_line(lineno, line):
        if line.startswith('msgid_plural'):
            in_msgid[0] = True
            msg = line[12:].lstrip()
            messages.append(msg)
        elif line.startswith('msgid'):
            in_msgid[0] = True
            offset[0] = lineno
            txt = line[5:].lstrip()
            if messages:
                _add_message()
            messages.append(txt)
        elif line.startswith('msgstr'):
            in_msgid[0] = False
            in_msgstr[0] = True
            msg = line[6:].lstrip()
            if msg.startswith('['):
                idx, msg = msg[1:].split(']', 1)
                translations.append([int(idx), msg.lstrip()])
            else:
                translations.append([0, msg])
        elif line.startswith('"'):
            if in_msgid[0]:
                messages[-1] += u'\n' + line.rstrip()
            elif in_msgstr[0]:
                translations[-1][1] += u'\n' + line.rstrip()

    for lineno, line in enumerate(fileobj.readlines()):
        line = line.strip()
        if not isinstance(line, unicode):
            line = line.decode(catalog.charset)
        if line.startswith('#'):
            in_msgid[0] = in_msgstr[0] = False
            if messages and translations:
                _add_message()
            if line[1:].startswith(':'):
                for location in line[2:].lstrip().split():
                    pos = location.rfind(':')
                    if pos >= 0:
                        try:
                            lineno = int(location[pos + 1:])
                        except ValueError:
                            continue
                        locations.append((location[:pos], lineno))
            elif line[1:].startswith(','):
                for flag in line[2:].lstrip().split(','):
                    flags.append(flag.strip())
            elif line[1:].startswith('~'):
                obsolete[0] = True
                _process_message_line(lineno, line[2:].lstrip())
            elif line[1:].startswith('.'):
                # These are called auto-comments
                comment = line[2:].strip()
                if comment: # Just check that we're not adding empty comments
                    auto_comments.append(comment)
            else:
                # These are called user comments
                user_comments.append(line[1:].strip())
        else:
            _process_message_line(lineno, line)

    if messages:
        _add_message()

    # No actual messages found, but there was some info in comments, from which
    # we'll construct an empty header message
    elif not counter[0] and (flags or user_comments or auto_comments):
        messages.append(u'')
        translations.append([0, u''])
        _add_message()

    return catalog

WORD_SEP = re.compile('('
    r'\s+|'                                 # any whitespace
    r'[^\s\w]*\w+[a-zA-Z]-(?=\w+[a-zA-Z])|' # hyphenated words
    r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w)'   # em-dash
')')

def escape(string):
    r"""Escape the given string so that it can be included in double-quoted
    strings in ``PO`` files.

    >>> escape('''Say:
    ...   "hello, world!"
    ... ''')
    '"Say:\\n  \\"hello, world!\\"\\n"'

    :param string: the string to escape
    :return: the escaped string
    :rtype: `str` or `unicode`
    """
    return '"%s"' % string.replace('\\', '\\\\') \
                          .replace('\t', '\\t') \
                          .replace('\r', '\\r') \
                          .replace('\n', '\\n') \
                          .replace('\"', '\\"')

def normalize(string, prefix='', width=76):
    r"""Convert a string into a format that is appropriate for .po files.

    >>> print normalize('''Say:
    ...   "hello, world!"
    ... ''', width=None)
    ""
    "Say:\n"
    "  \"hello, world!\"\n"

    >>> print normalize('''Say:
    ...   "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    ... ''', width=32)
    ""
    "Say:\n"
    "  \"Lorem ipsum dolor sit "
    "amet, consectetur adipisicing"
    " elit, \"\n"

    :param string: the string to normalize
    :param prefix: a string that should be prepended to every line
    :param width: the maximum line width; use `None`, 0, or a negative number
                  to completely disable line wrapping
    :return: the normalized string
    :rtype: `unicode`
    """
    if width and width > 0:
        prefixlen = len(prefix)
        lines = []
        for idx, line in enumerate(string.splitlines(True)):
            if len(escape(line)) + prefixlen > width:
                chunks = WORD_SEP.split(line)
                chunks.reverse()
                while chunks:
                    buf = []
                    size = 2
                    while chunks:
                        l = len(escape(chunks[-1])) - 2 + prefixlen
                        if size + l < width:
                            buf.append(chunks.pop())
                            size += l
                        else:
                            if not buf:
                                # handle long chunks by putting them on a
                                # separate line
                                buf.append(chunks.pop())
                            break
                    lines.append(u''.join(buf))
            else:
                lines.append(line)
    else:
        lines = string.splitlines(True)

    if len(lines) <= 1:
        return escape(string)

    # Remove empty trailing line
    if lines and not lines[-1]:
        del lines[-1]
        lines[-1] += '\n'
    return u'""\n' + u'\n'.join([(prefix + escape(l)) for l in lines])

def write_po(fileobj, catalog, width=76, no_location=False, omit_header=False,
             sort_output=False, sort_by_file=False, ignore_obsolete=False,
             include_previous=False):
    r"""Write a ``gettext`` PO (portable object) template file for a given
    message catalog to the provided file-like object.

    >>> catalog = Catalog()
    >>> catalog.add(u'foo %(name)s', locations=[('main.py', 1)],
    ...             flags=('fuzzy',))
    >>> catalog.add((u'bar', u'baz'), locations=[('main.py', 3)])
    >>> from StringIO import StringIO
    >>> buf = StringIO()
    >>> write_po(buf, catalog, omit_header=True)
    >>> print buf.getvalue()
    #: main.py:1
    #, fuzzy, python-format
    msgid "foo %(name)s"
    msgstr ""
    <BLANKLINE>
    #: main.py:3
    msgid "bar"
    msgid_plural "baz"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    <BLANKLINE>

    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param width: the maximum line width for the generated output; use `None`,
                  0, or a negative number to completely disable line wrapping
    :param no_location: do not emit a location comment for every message
    :param omit_header: do not include the ``msgid ""`` entry at the top of the
                        output
    :param sort_output: whether to sort the messages in the output by msgid
    :param sort_by_file: whether to sort the messages in the output by their
                         locations
    :param ignore_obsolete: whether to ignore obsolete messages and not include
                            them in the output; by default they are included as
                            comments
    :param include_previous: include the old msgid as a comment when
                             updating the catalog
    """
    def _normalize(key, prefix=''):
        return normalize(key, prefix=prefix, width=width) \
            .encode(catalog.charset, 'backslashreplace')

    def _write(text):
        if isinstance(text, unicode):
            text = text.encode(catalog.charset)
        fileobj.write(text)

    def _write_comment(comment, prefix=''):
        # xgettext always wraps comments even if --no-wrap is passed;
        # provide the same behaviour
        if width and width > 0:
            _width = width
        else:
            _width = 76
        for line in wraptext(comment, _width):
            _write('#%s %s\n' % (prefix, line.strip()))

    def _write_message(message, prefix=''):
        if isinstance(message.id, (list, tuple)):
            _write('%smsgid %s\n' % (prefix, _normalize(message.id[0], prefix)))
            _write('%smsgid_plural %s\n' % (
                prefix, _normalize(message.id[1], prefix)
            ))

            for idx in range(catalog.num_plurals):
                try:
                    string = message.string[idx]
                except IndexError:
                    string = ''
                _write('%smsgstr[%d] %s\n' % (
                    prefix, idx, _normalize(string, prefix)
                ))
        else:
            _write('%smsgid %s\n' % (prefix, _normalize(message.id, prefix)))
            _write('%smsgstr %s\n' % (
                prefix, _normalize(message.string or '', prefix)
            ))

    messages = list(catalog)
    if sort_output:
        messages.sort()
    elif sort_by_file:
        messages.sort(lambda x,y: cmp(x.locations, y.locations))

    for message in messages:
        if not message.id: # This is the header "message"
            if omit_header:
                continue
            comment_header = catalog.header_comment
            if width and width > 0:
                lines = []
                for line in comment_header.splitlines():
                    lines += wraptext(line, width=width,
                                      subsequent_indent='# ')
                comment_header = u'\n'.join(lines) + u'\n'
            _write(comment_header)

        for comment in message.user_comments:
            _write_comment(comment)
        for comment in message.auto_comments:
            _write_comment(comment, prefix='.')

        if not no_location:
            locs = u' '.join([u'%s:%d' % (filename.replace(os.sep, '/'), lineno)
                              for filename, lineno in message.locations])
            _write_comment(locs, prefix=':')
        if message.flags:
            _write('#%s\n' % ', '.join([''] + list(message.flags)))

        if message.previous_id and include_previous:
            _write_comment('msgid %s' % _normalize(message.previous_id[0]),
                           prefix='|')
            if len(message.previous_id) > 1:
                _write_comment('msgid_plural %s' % _normalize(
                    message.previous_id[1]
                ), prefix='|')

        _write_message(message)
        _write('\n')

    if not ignore_obsolete:
        for message in catalog.obsolete.values():
            for comment in message.user_comments:
                _write_comment(comment)
            _write_message(message, prefix='#~ ')
            _write('\n')

########NEW FILE########
__FILENAME__ = numbers
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Locale dependent formatting and parsing of numeric data.

The default locale for the functions in this module is determined by the
following environment variables, in that order:

 * ``LC_NUMERIC``,
 * ``LC_ALL``, and
 * ``LANG``
"""
# TODO:
#  Padding and rounding increments in pattern:
#  - http://www.unicode.org/reports/tr35/ (Appendix G.6)
import math
import re
try:
    from decimal import Decimal
    have_decimal = True
except ImportError:
    have_decimal = False

from babel.core import default_locale, Locale
from babel.util import rsplit

__all__ = ['format_number', 'format_decimal', 'format_currency',
           'format_percent', 'format_scientific', 'parse_number',
           'parse_decimal', 'NumberFormatError']
__docformat__ = 'restructuredtext en'

LC_NUMERIC = default_locale('LC_NUMERIC')

def get_currency_name(currency, locale=LC_NUMERIC):
    """Return the name used by the locale for the specified currency.
    
    >>> get_currency_name('USD', 'en_US')
    u'US Dollar'
    
    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    :return: the currency symbol
    :rtype: `unicode`
    :since: version 0.9.4
    """
    return Locale.parse(locale).currencies.get(currency, currency)

def get_currency_symbol(currency, locale=LC_NUMERIC):
    """Return the symbol used by the locale for the specified currency.
    
    >>> get_currency_symbol('USD', 'en_US')
    u'$'
    
    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    :return: the currency symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).currency_symbols.get(currency, currency)

def get_decimal_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate decimal fractions.
    
    >>> get_decimal_symbol('en_US')
    u'.'
    
    :param locale: the `Locale` object or locale identifier
    :return: the decimal symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('decimal', u'.')

def get_plus_sign_symbol(locale=LC_NUMERIC):
    """Return the plus sign symbol used by the current locale.
    
    >>> get_plus_sign_symbol('en_US')
    u'+'
    
    :param locale: the `Locale` object or locale identifier
    :return: the plus sign symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('plusSign', u'+')

def get_minus_sign_symbol(locale=LC_NUMERIC):
    """Return the plus sign symbol used by the current locale.
    
    >>> get_minus_sign_symbol('en_US')
    u'-'
    
    :param locale: the `Locale` object or locale identifier
    :return: the plus sign symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('minusSign', u'-')

def get_exponential_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate mantissa and exponent.
    
    >>> get_exponential_symbol('en_US')
    u'E'
    
    :param locale: the `Locale` object or locale identifier
    :return: the exponential symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('exponential', u'E')

def get_group_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate groups of thousands.
    
    >>> get_group_symbol('en_US')
    u','
    
    :param locale: the `Locale` object or locale identifier
    :return: the group symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('group', u',')

def format_number(number, locale=LC_NUMERIC):
    """Return the given number formatted for a specific locale.
    
    >>> format_number(1099, locale='en_US')
    u'1,099'
    
    :param number: the number to format
    :param locale: the `Locale` object or locale identifier
    :return: the formatted number
    :rtype: `unicode`
    """
    # Do we really need this one?
    return format_decimal(number, locale=locale)

def format_decimal(number, format=None, locale=LC_NUMERIC):
    """Return the given decimal number formatted for a specific locale.
    
    >>> format_decimal(1.2345, locale='en_US')
    u'1.234'
    >>> format_decimal(1.2346, locale='en_US')
    u'1.235'
    >>> format_decimal(-1.2346, locale='en_US')
    u'-1.235'
    >>> format_decimal(1.2345, locale='sv_SE')
    u'1,234'
    >>> format_decimal(12345, locale='de')
    u'12.345'

    The appropriate thousands grouping and the decimal separator are used for
    each locale:
    
    >>> format_decimal(12345.5, locale='en_US')
    u'12,345.5'

    :param number: the number to format
    :param format: 
    :param locale: the `Locale` object or locale identifier
    :return: the formatted decimal number
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.decimal_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)

def format_currency(number, currency, format=None, locale=LC_NUMERIC):
    u"""Return formatted currency value.
    
    >>> format_currency(1099.98, 'USD', locale='en_US')
    u'$1,099.98'
    >>> format_currency(1099.98, 'USD', locale='es_CO')
    u'US$\\xa01.099,98'
    >>> format_currency(1099.98, 'EUR', locale='de_DE')
    u'1.099,98\\xa0\\u20ac'
    
    The pattern can also be specified explicitly:
    
    >>> format_currency(1099.98, 'EUR', u'\xa4\xa4 #,##0.00', locale='en_US')
    u'EUR 1,099.98'
    
    :param number: the number to format
    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    :return: the formatted currency value
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.currency_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale, currency=currency)

def format_percent(number, format=None, locale=LC_NUMERIC):
    """Return formatted percent value for a specific locale.
    
    >>> format_percent(0.34, locale='en_US')
    u'34%'
    >>> format_percent(25.1234, locale='en_US')
    u'2,512%'
    >>> format_percent(25.1234, locale='sv_SE')
    u'2\\xa0512\\xa0%'

    The format pattern can also be specified explicitly:
    
    >>> format_percent(25.1234, u'#,##0\u2030', locale='en_US')
    u'25,123\u2030'

    :param number: the percent number to format
    :param format: 
    :param locale: the `Locale` object or locale identifier
    :return: the formatted percent number
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.percent_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)

def format_scientific(number, format=None, locale=LC_NUMERIC):
    """Return value formatted in scientific notation for a specific locale.
    
    >>> format_scientific(10000, locale='en_US')
    u'1E4'

    The format pattern can also be specified explicitly:
    
    >>> format_scientific(1234567, u'##0E00', locale='en_US')
    u'1.23E06'

    :param number: the number to format
    :param format: 
    :param locale: the `Locale` object or locale identifier
    :return: value formatted in scientific notation.
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.scientific_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)


class NumberFormatError(ValueError):
    """Exception raised when a string cannot be parsed into a number."""


def parse_number(string, locale=LC_NUMERIC):
    """Parse localized number string into a long integer.
    
    >>> parse_number('1,099', locale='en_US')
    1099L
    >>> parse_number('1.099', locale='de_DE')
    1099L
    
    When the given string cannot be parsed, an exception is raised:
    
    >>> parse_number('1.099,98', locale='de')
    Traceback (most recent call last):
        ...
    NumberFormatError: '1.099,98' is not a valid number
    
    :param string: the string to parse
    :param locale: the `Locale` object or locale identifier
    :return: the parsed number
    :rtype: `long`
    :raise `NumberFormatError`: if the string can not be converted to a number
    """
    try:
        return long(string.replace(get_group_symbol(locale), ''))
    except ValueError:
        raise NumberFormatError('%r is not a valid number' % string)

def parse_decimal(string, locale=LC_NUMERIC):
    """Parse localized decimal string into a float.
    
    >>> parse_decimal('1,099.98', locale='en_US')
    1099.98
    >>> parse_decimal('1.099,98', locale='de')
    1099.98
    
    When the given string cannot be parsed, an exception is raised:
    
    >>> parse_decimal('2,109,998', locale='de')
    Traceback (most recent call last):
        ...
    NumberFormatError: '2,109,998' is not a valid decimal number
    
    :param string: the string to parse
    :param locale: the `Locale` object or locale identifier
    :return: the parsed decimal number
    :rtype: `float`
    :raise `NumberFormatError`: if the string can not be converted to a
                                decimal number
    """
    locale = Locale.parse(locale)
    try:
        return float(string.replace(get_group_symbol(locale), '')
                           .replace(get_decimal_symbol(locale), '.'))
    except ValueError:
        raise NumberFormatError('%r is not a valid decimal number' % string)


PREFIX_END = r'[^0-9@#.,]'
NUMBER_TOKEN = r'[0-9@#.\-,E+]'

PREFIX_PATTERN = r"(?P<prefix>(?:'[^']*'|%s)*)" % PREFIX_END
NUMBER_PATTERN = r"(?P<number>%s+)" % NUMBER_TOKEN
SUFFIX_PATTERN = r"(?P<suffix>.*)"

number_re = re.compile(r"%s%s%s" % (PREFIX_PATTERN, NUMBER_PATTERN,
                                    SUFFIX_PATTERN))

def split_number(value):
    """Convert a number into a (intasstring, fractionasstring) tuple"""
    if have_decimal and isinstance(value, Decimal):
        text = str(value)
    else:
        text = ('%.9f' % value).rstrip('0')
    if '.' in text:
        a, b = text.split('.', 1)
        if b == '0':
            b = ''
    else:
        a, b = text, ''
    return a, b

def bankersround(value, ndigits=0):
    """Round a number to a given precision.

    Works like round() except that the round-half-even (banker's rounding)
    algorithm is used instead of round-half-up.

    >>> bankersround(5.5, 0)
    6.0
    >>> bankersround(6.5, 0)
    6.0
    >>> bankersround(-6.5, 0)
    -6.0
    >>> bankersround(1234.0, -2)
    1200.0
    """
    sign = int(value < 0) and -1 or 1
    value = abs(value)
    a, b = split_number(value)
    digits = a + b
    add = 0
    i = len(a) + ndigits
    if i < 0 or i >= len(digits):
        pass
    elif digits[i] > '5':
        add = 1
    elif digits[i] == '5' and digits[i-1] in '13579':
        add = 1
    scale = 10**ndigits
    if have_decimal and isinstance(value, Decimal):
        return Decimal(int(value * scale + add)) / scale * sign
    else:
        return float(int(value * scale + add)) / scale * sign

def parse_pattern(pattern):
    """Parse number format patterns"""
    if isinstance(pattern, NumberPattern):
        return pattern

    # Do we have a negative subpattern?
    if ';' in pattern:
        pattern, neg_pattern = pattern.split(';', 1)
        pos_prefix, number, pos_suffix = number_re.search(pattern).groups()
        neg_prefix, _, neg_suffix = number_re.search(neg_pattern).groups()
    else:
        pos_prefix, number, pos_suffix = number_re.search(pattern).groups()
        neg_prefix = '-' + pos_prefix
        neg_suffix = pos_suffix
    if 'E' in number:
        number, exp = number.split('E', 1)
    else:
        exp = None
    if '@' in number:
        if '.' in number and '0' in number:
            raise ValueError('Significant digit patterns can not contain '
                             '"@" or "0"')
    if '.' in number:
        integer, fraction = rsplit(number, '.', 1)
    else:
        integer = number
        fraction = ''
    min_frac = max_frac = 0

    def parse_precision(p):
        """Calculate the min and max allowed digits"""
        min = max = 0
        for c in p:
            if c in '@0':
                min += 1
                max += 1
            elif c == '#':
                max += 1
            elif c == ',':
                continue
            else:
                break
        return min, max

    def parse_grouping(p):
        """Parse primary and secondary digit grouping

        >>> parse_grouping('##')
        0, 0
        >>> parse_grouping('#,###')
        3, 3
        >>> parse_grouping('#,####,###')
        3, 4
        """
        width = len(p)
        g1 = p.rfind(',')
        if g1 == -1:
            return 1000, 1000
        g1 = width - g1 - 1
        g2 = p[:-g1 - 1].rfind(',')
        if g2 == -1:
            return g1, g1
        g2 = width - g1 - g2 - 2
        return g1, g2

    int_prec = parse_precision(integer)
    frac_prec = parse_precision(fraction)
    if exp:
        frac_prec = parse_precision(integer+fraction)
        exp_plus = exp.startswith('+')
        exp = exp.lstrip('+')
        exp_prec = parse_precision(exp)
    else:
        exp_plus = None
        exp_prec = None
    grouping = parse_grouping(integer)
    return NumberPattern(pattern, (pos_prefix, neg_prefix), 
                         (pos_suffix, neg_suffix), grouping,
                         int_prec, frac_prec, 
                         exp_prec, exp_plus)


class NumberPattern(object):

    def __init__(self, pattern, prefix, suffix, grouping,
                 int_prec, frac_prec, exp_prec, exp_plus):
        self.pattern = pattern
        self.prefix = prefix
        self.suffix = suffix
        self.grouping = grouping
        self.int_prec = int_prec
        self.frac_prec = frac_prec
        self.exp_prec = exp_prec
        self.exp_plus = exp_plus
        if '%' in ''.join(self.prefix + self.suffix):
            self.scale = 100
        elif u'‰' in ''.join(self.prefix + self.suffix):
            self.scale = 1000
        else:
            self.scale = 1

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.pattern)

    def apply(self, value, locale, currency=None):
        value *= self.scale
        is_negative = int(value < 0)
        if self.exp_prec: # Scientific notation
            value = abs(value)
            if value:
                exp = int(math.floor(math.log(value, 10)))
            else:
                exp = 0
            # Minimum number of integer digits
            if self.int_prec[0] == self.int_prec[1]:
                exp -= self.int_prec[0] - 1
            # Exponent grouping
            elif self.int_prec[1]:
                exp = int(exp) / self.int_prec[1] * self.int_prec[1]
            if not have_decimal or not isinstance(value, Decimal):
                value = float(value)
            if exp < 0:
                value = value * 10**(-exp)
            else:
                value = value / 10**exp
            exp_sign = ''
            if exp < 0:
                exp_sign = get_minus_sign_symbol(locale)
            elif self.exp_plus:
                exp_sign = get_plus_sign_symbol(locale)
            exp = abs(exp)
            number = u'%s%s%s%s' % \
                 (self._format_sigdig(value, self.frac_prec[0], 
                                     self.frac_prec[1]), 
                  get_exponential_symbol(locale),  exp_sign,
                  self._format_int(str(exp), self.exp_prec[0],
                                   self.exp_prec[1], locale))
        elif '@' in self.pattern: # Is it a siginificant digits pattern?
            text = self._format_sigdig(abs(value),
                                      self.int_prec[0],
                                      self.int_prec[1])
            if '.' in text:
                a, b = text.split('.')
                a = self._format_int(a, 0, 1000, locale)
                if b:
                    b = get_decimal_symbol(locale) + b
                number = a + b
            else:
                number = self._format_int(text, 0, 1000, locale)
        else: # A normal number pattern
            a, b = split_number(bankersround(abs(value), 
                                             self.frac_prec[1]))
            b = b or '0'
            a = self._format_int(a, self.int_prec[0],
                                 self.int_prec[1], locale)
            b = self._format_frac(b, locale)
            number = a + b
        retval = u'%s%s%s' % (self.prefix[is_negative], number,
                                self.suffix[is_negative])
        if u'¤' in retval:
            retval = retval.replace(u'¤¤', currency.upper())
            retval = retval.replace(u'¤', get_currency_symbol(currency, locale))
        return retval

    def _format_sigdig(self, value, min, max):
        """Convert value to a string.

        The resulting string will contain between (min, max) number of
        significant digits.
        """
        a, b = split_number(value)
        ndecimals = len(a)
        if a == '0' and b != '':
            ndecimals = 0
            while b.startswith('0'):
                b = b[1:]
                ndecimals -= 1
        a, b = split_number(bankersround(value, max - ndecimals))
        digits = len((a + b).lstrip('0'))
        if not digits:
            digits = 1
        # Figure out if we need to add any trailing '0':s
        if len(a) >= max and a != '0':
            return a
        if digits < min:
            b += ('0' * (min - digits))
        if b:
            return '%s.%s' % (a, b)
        return a

    def _format_int(self, value, min, max, locale):
        width = len(value)
        if width < min:
            value = '0' * (min - width) + value
        gsize = self.grouping[0]
        ret = ''
        symbol = get_group_symbol(locale)
        while len(value) > gsize:
            ret = symbol + value[-gsize:] + ret
            value = value[:-gsize]
            gsize = self.grouping[1]
        return value + ret

    def _format_frac(self, value, locale):
        min, max = self.frac_prec
        if len(value) < min:
            value += ('0' * (min - len(value)))
        if max == 0 or (min == 0 and int(value) == 0):
            return ''
        width = len(value)
        while len(value) > min and value[-1] == '0':
            value = value[:-1]
        return get_decimal_symbol(locale) + value

########NEW FILE########
__FILENAME__ = support
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Several classes and functions that help with integrating and using Babel
in applications.

.. note: the code in this module is not used by Babel itself
"""

from datetime import date, datetime, time
import gettext

from babel.core import Locale
from babel.dates import format_date, format_datetime, format_time, LC_TIME
from babel.numbers import format_number, format_decimal, format_currency, \
                          format_percent, format_scientific, LC_NUMERIC
from babel.util import set, UTC

__all__ = ['Format', 'LazyProxy', 'Translations']
__docformat__ = 'restructuredtext en'


class Format(object):
    """Wrapper class providing the various date and number formatting functions
    bound to a specific locale and time-zone.
    
    >>> fmt = Format('en_US', UTC)
    >>> fmt.date(date(2007, 4, 1))
    u'Apr 1, 2007'
    >>> fmt.decimal(1.2345)
    u'1.234'
    """

    def __init__(self, locale, tzinfo=None):
        """Initialize the formatter.
        
        :param locale: the locale identifier or `Locale` instance
        :param tzinfo: the time-zone info (a `tzinfo` instance or `None`)
        """
        self.locale = Locale.parse(locale)
        self.tzinfo = tzinfo

    def date(self, date=None, format='medium'):
        """Return a date formatted according to the given pattern.
        
        >>> fmt = Format('en_US')
        >>> fmt.date(date(2007, 4, 1))
        u'Apr 1, 2007'
        
        :see: `babel.dates.format_date`
        """
        return format_date(date, format, locale=self.locale)

    def datetime(self, datetime=None, format='medium'):
        """Return a date and time formatted according to the given pattern.
        
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.datetime(datetime(2007, 4, 1, 15, 30))
        u'Apr 1, 2007 11:30:00 AM'
        
        :see: `babel.dates.format_datetime`
        """
        return format_datetime(datetime, format, tzinfo=self.tzinfo,
                               locale=self.locale)

    def time(self, time=None, format='medium'):
        """Return a time formatted according to the given pattern.
        
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.time(datetime(2007, 4, 1, 15, 30))
        u'11:30:00 AM'
        
        :see: `babel.dates.format_time`
        """
        return format_time(time, format, tzinfo=self.tzinfo, locale=self.locale)

    def number(self, number):
        """Return an integer number formatted for the locale.
        
        >>> fmt = Format('en_US')
        >>> fmt.number(1099)
        u'1,099'
        
        :see: `babel.numbers.format_number`
        """
        return format_number(number, locale=self.locale)

    def decimal(self, number, format=None):
        """Return a decimal number formatted for the locale.
        
        >>> fmt = Format('en_US')
        >>> fmt.decimal(1.2345)
        u'1.234'
        
        :see: `babel.numbers.format_decimal`
        """
        return format_decimal(number, format, locale=self.locale)

    def currency(self, number, currency):
        """Return a number in the given currency formatted for the locale.
        
        :see: `babel.numbers.format_currency`
        """
        return format_currency(number, currency, locale=self.locale)

    def percent(self, number, format=None):
        """Return a number formatted as percentage for the locale.
        
        >>> fmt = Format('en_US')
        >>> fmt.percent(0.34)
        u'34%'
        
        :see: `babel.numbers.format_percent`
        """
        return format_percent(number, format, locale=self.locale)

    def scientific(self, number):
        """Return a number formatted using scientific notation for the locale.
        
        :see: `babel.numbers.format_scientific`
        """
        return format_scientific(number, locale=self.locale)


class LazyProxy(object):
    """Class for proxy objects that delegate to a specified function to evaluate
    the actual object.
    
    >>> def greeting(name='world'):
    ...     return 'Hello, %s!' % name
    >>> lazy_greeting = LazyProxy(greeting, name='Joe')
    >>> print lazy_greeting
    Hello, Joe!
    >>> u'  ' + lazy_greeting
    u'  Hello, Joe!'
    >>> u'(%s)' % lazy_greeting
    u'(Hello, Joe!)'
    
    This can be used, for example, to implement lazy translation functions that
    delay the actual translation until the string is actually used. The
    rationale for such behavior is that the locale of the user may not always
    be available. In web applications, you only know the locale when processing
    a request.
    
    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting:
    
    >>> greetings = [
    ...     LazyProxy(greeting, 'world'),
    ...     LazyProxy(greeting, 'Joe'),
    ...     LazyProxy(greeting, 'universe'),
    ... ]
    >>> greetings.sort()
    >>> for greeting in greetings:
    ...     print greeting
    Hello, Joe!
    Hello, universe!
    Hello, world!
    """
    __slots__ = ['_func', '_args', '_kwargs', '_value']

    def __init__(self, func, *args, **kwargs):
        # Avoid triggering our own __setattr__ implementation
        object.__setattr__(self, '_func', func)
        object.__setattr__(self, '_args', args)
        object.__setattr__(self, '_kwargs', kwargs)
        object.__setattr__(self, '_value', None)

    def value(self):
        if self._value is None:
            value = self._func(*self._args, **self._kwargs)
            object.__setattr__(self, '_value', value)
        return self._value
    value = property(value)

    def __contains__(self, key):
        return key in self.value

    def __nonzero__(self):
        return bool(self.value)

    def __dir__(self):
        return dir(self.value)

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def __add__(self, other):
        return self.value + other

    def __radd__(self, other):
        return other + self.value

    def __mod__(self, other):
        return self.value % other

    def __rmod__(self, other):
        return other % self.value

    def __mul__(self, other):
        return self.value * other

    def __rmul__(self, other):
        return other * self.value

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)

    def __lt__(self, other):
        return self.value < other

    def __le__(self, other):
        return self.value <= other

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __gt__(self, other):
        return self.value > other

    def __ge__(self, other):
        return self.value >= other

    def __delattr__(self, name):
        delattr(self.value, name)

    def __getattr__(self, name):
        return getattr(self.value, name)

    def __setattr__(self, name, value):
        setattr(self.value, name, value)

    def __delitem__(self, key):
        del self.value[key]

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

    
class Translations(gettext.GNUTranslations, object):
    """An extended translation catalog class."""

    DEFAULT_DOMAIN = 'messages'

    def __init__(self, fileobj=None, domain=DEFAULT_DOMAIN):
        """Initialize the translations catalog.

        :param fileobj: the file-like object the translation should be read
                        from
        """
        gettext.GNUTranslations.__init__(self, fp=fileobj)
        self.files = filter(None, [getattr(fileobj, 'name', None)])
        self.domain = domain
        self._domains = {}

    def load(cls, dirname=None, locales=None, domain=DEFAULT_DOMAIN):
        """Load translations from the given directory.

        :param dirname: the directory containing the ``MO`` files
        :param locales: the list of locales in order of preference (items in
                        this list can be either `Locale` objects or locale
                        strings)
        :param domain: the message domain
        :return: the loaded catalog, or a ``NullTranslations`` instance if no
                 matching translations were found
        :rtype: `Translations`
        """
        if locales is not None:
            if not isinstance(locales, (list, tuple)):
                locales = [locales]
            locales = [str(locale) for locale in locales]
        if not domain:
            domain = cls.DEFAULT_DOMAIN
        filename = gettext.find(domain, dirname, locales)
        if not filename:
            return gettext.NullTranslations()
        return cls(fileobj=open(filename, 'rb'), domain=domain)
    load = classmethod(load)

    def __repr__(self):
        return '<%s: "%s">' % (type(self).__name__,
                               self._info.get('project-id-version'))

    def add(self, translations, merge=True):
        """Add the given translations to the catalog.

        If the domain of the translations is different than that of the
        current catalog, they are added as a catalog that is only accessible
        by the various ``d*gettext`` functions.

        :param translations: the `Translations` instance with the messages to
                             add
        :param merge: whether translations for message domains that have
                      already been added should be merged with the existing
                      translations
        :return: the `Translations` instance (``self``) so that `merge` calls
                 can be easily chained
        :rtype: `Translations`
        """
        domain = getattr(translations, 'domain', self.DEFAULT_DOMAIN)
        if merge and domain == self.domain:
            return self.merge(translations)

        existing = self._domains.get(domain)
        if merge and existing is not None:
            existing.merge(translations)
        else:
            translations.add_fallback(self)
            self._domains[domain] = translations

        return self

    def merge(self, translations):
        """Merge the given translations into the catalog.

        Message translations in the specified catalog override any messages
        with the same identifier in the existing catalog.

        :param translations: the `Translations` instance with the messages to
                             merge
        :return: the `Translations` instance (``self``) so that `merge` calls
                 can be easily chained
        :rtype: `Translations`
        """
        if isinstance(translations, gettext.GNUTranslations):
            self._catalog.update(translations._catalog)
            if isinstance(translations, Translations):
                self.files.extend(translations.files)

        return self

    def dgettext(self, domain, message):
        """Like ``gettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).gettext(message)
    
    def ldgettext(self, domain, message):
        """Like ``lgettext()``, but look the message up in the specified 
        domain.
        """ 
        return self._domains.get(domain, self).lgettext(message)
    
    def dugettext(self, domain, message):
        """Like ``ugettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ugettext(message)
    
    def dngettext(self, domain, singular, plural, num):
        """Like ``ngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ngettext(singular, plural, num)
    
    def ldngettext(self, domain, singular, plural, num):
        """Like ``lngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).lngettext(singular, plural, num)
    
    def dungettext(self, domain, singular, plural, num):
        """Like ``ungettext()`` but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ungettext(singular, plural, num)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Various utility classes and functions."""

import codecs
from datetime import timedelta, tzinfo
import os
import re
try:
    set = set
except NameError:
    from sets import Set as set
import textwrap
import time
from itertools import izip, imap
missing = object()

__all__ = ['distinct', 'pathmatch', 'relpath', 'wraptext', 'odict', 'UTC',
           'LOCALTZ']
__docformat__ = 'restructuredtext en'


def distinct(iterable):
    """Yield all items in an iterable collection that are distinct.

    Unlike when using sets for a similar effect, the original ordering of the
    items in the collection is preserved by this function.

    >>> print list(distinct([1, 2, 1, 3, 4, 4]))
    [1, 2, 3, 4]
    >>> print list(distinct('foobar'))
    ['f', 'o', 'b', 'a', 'r']

    :param iterable: the iterable collection providing the data
    :return: the distinct items in the collection
    :rtype: ``iterator``
    """
    seen = set()
    for item in iter(iterable):
        if item not in seen:
            yield item
            seen.add(item)

# Regexp to match python magic encoding line
PYTHON_MAGIC_COMMENT_re = re.compile(
    r'[ \t\f]* \# .* coding[=:][ \t]*([-\w.]+)', re.VERBOSE)
def parse_encoding(fp):
    """Deduce the encoding of a source file from magic comment.

    It does this in the same way as the `Python interpreter`__

    .. __: http://docs.python.org/ref/encodings.html

    The ``fp`` argument should be a seekable file object.

    (From Jeff Dairiki)
    """
    pos = fp.tell()
    fp.seek(0)
    try:
        line1 = fp.readline()
        has_bom = line1.startswith(codecs.BOM_UTF8)
        if has_bom:
            line1 = line1[len(codecs.BOM_UTF8):]

        m = PYTHON_MAGIC_COMMENT_re.match(line1)
        if not m:
            try:
                import parser
                parser.suite(line1)
            except (ImportError, SyntaxError):
                # Either it's a real syntax error, in which case the source is
                # not valid python source, or line2 is a continuation of line1,
                # in which case we don't want to scan line2 for a magic
                # comment.
                pass
            else:
                line2 = fp.readline()
                m = PYTHON_MAGIC_COMMENT_re.match(line2)

        if has_bom:
            if m:
                raise SyntaxError(
                    "python refuses to compile code with both a UTF8 "
                    "byte-order-mark and a magic encoding comment")
            return 'utf_8'
        elif m:
            return m.group(1)
        else:
            return None
    finally:
        fp.seek(pos)

def pathmatch(pattern, filename):
    """Extended pathname pattern matching.
    
    This function is similar to what is provided by the ``fnmatch`` module in
    the Python standard library, but:
    
     * can match complete (relative or absolute) path names, and not just file
       names, and
     * also supports a convenience pattern ("**") to match files at any
       directory level.
    
    Examples:
    
    >>> pathmatch('**.py', 'bar.py')
    True
    >>> pathmatch('**.py', 'foo/bar/baz.py')
    True
    >>> pathmatch('**.py', 'templates/index.html')
    False
    
    >>> pathmatch('**/templates/*.html', 'templates/index.html')
    True
    >>> pathmatch('**/templates/*.html', 'templates/foo/bar.html')
    False
    
    :param pattern: the glob pattern
    :param filename: the path name of the file to match against
    :return: `True` if the path name matches the pattern, `False` otherwise
    :rtype: `bool`
    """
    symbols = {
        '?':   '[^/]',
        '?/':  '[^/]/',
        '*':   '[^/]+',
        '*/':  '[^/]+/',
        '**/': '(?:.+/)*?',
        '**':  '(?:.+/)*?[^/]+',
    }
    buf = []
    for idx, part in enumerate(re.split('([?*]+/?)', pattern)):
        if idx % 2:
            buf.append(symbols[part])
        elif part:
            buf.append(re.escape(part))
    match = re.match(''.join(buf) + '$', filename.replace(os.sep, '/'))
    return match is not None


class TextWrapper(textwrap.TextWrapper):
    wordsep_re = re.compile(
        r'(\s+|'                                  # any whitespace
        r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))'    # em-dash
    )


def wraptext(text, width=70, initial_indent='', subsequent_indent=''):
    """Simple wrapper around the ``textwrap.wrap`` function in the standard
    library. This version does not wrap lines on hyphens in words.
    
    :param text: the text to wrap
    :param width: the maximum line width
    :param initial_indent: string that will be prepended to the first line of
                           wrapped output
    :param subsequent_indent: string that will be prepended to all lines save
                              the first of wrapped output
    :return: a list of lines
    :rtype: `list`
    """
    wrapper = TextWrapper(width=width, initial_indent=initial_indent,
                          subsequent_indent=subsequent_indent,
                          break_long_words=False)
    return wrapper.wrap(text)


class odict(dict):
    """Ordered dict implementation.
    
    :see: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/107747
    """
    def __init__(self, data=None):
        dict.__init__(self, data or {})
        self._keys = dict.keys(self)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        if key not in self._keys:
            self._keys.append(key)

    def __iter__(self):
        return iter(self._keys)
    iterkeys = __iter__

    def clear(self):
        dict.clear(self)
        self._keys = []

    def copy(self):
        d = odict()
        d.update(self)
        return d

    def items(self):
        return zip(self._keys, self.values())

    def iteritems(self):
        return izip(self._keys, self.itervalues())

    def keys(self):
        return self._keys[:]

    def pop(self, key, default=missing):
        if default is missing:
            return dict.pop(self, key)
        elif key not in self:
            return default
        self._keys.remove(key)
        return dict.pop(self, key, default)

    def popitem(self, key):
        self._keys.remove(key)
        return dict.popitem(key)

    def setdefault(self, key, failobj = None):
        dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)

    def update(self, dict):
        for (key, val) in dict.items():
            self[key] = val

    def values(self):
        return map(self.get, self._keys)

    def itervalues(self):
        return imap(self.get, self._keys)


try:
    relpath = os.path.relpath
except AttributeError:
    def relpath(path, start='.'):
        """Compute the relative path to one path from another.
        
        >>> relpath('foo/bar.txt', '').replace(os.sep, '/')
        'foo/bar.txt'
        >>> relpath('foo/bar.txt', 'foo').replace(os.sep, '/')
        'bar.txt'
        >>> relpath('foo/bar.txt', 'baz').replace(os.sep, '/')
        '../foo/bar.txt'
        
        :return: the relative path
        :rtype: `basestring`
        """
        start_list = os.path.abspath(start).split(os.sep)
        path_list = os.path.abspath(path).split(os.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list) - i) + path_list[i:]
        return os.path.join(*rel_list)

try:
    from operator import attrgetter, itemgetter
except ImportError:
    def itemgetter(name):
        def _getitem(obj):
            return obj[name]
        return _getitem

try:
    ''.rsplit
    def rsplit(a_string, sep=None, maxsplit=None):
        return a_string.rsplit(sep, maxsplit)
except AttributeError:
    def rsplit(a_string, sep=None, maxsplit=None):
        parts = a_string.split(sep)
        if maxsplit is None or len(parts) <= maxsplit:
            return parts
        maxsplit_index = len(parts) - maxsplit
        non_splitted_part = sep.join(parts[:maxsplit_index])
        splitted = parts[maxsplit_index:]
        return [non_splitted_part] + splitted

ZERO = timedelta(0)


class FixedOffsetTimezone(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name=None):
        self._offset = timedelta(minutes=offset)
        if name is None:
            name = 'Etc/GMT+%d' % offset
        self.zone = name

    def __str__(self):
        return self.zone

    def __repr__(self):
        return '<FixedOffset "%s" %s>' % (self.zone, self._offset)

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self.zone

    def dst(self, dt):
        return ZERO


try:
    from pytz import UTC
except ImportError:
    UTC = FixedOffsetTimezone(0, 'UTC')
    """`tzinfo` object for UTC (Universal Time).
    
    :type: `tzinfo`
    """

STDOFFSET = timedelta(seconds = -time.timezone)
if time.daylight:
    DSTOFFSET = timedelta(seconds = -time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET


class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0


LOCALTZ = LocalTimezone()
"""`tzinfo` object for local time-zone.

:type: `tzinfo`
"""

########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri
        
if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [ 
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))
            
        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()

    
########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import base64
import socket
import struct
import sys

if getattr(socket, 'socket', None) is None:
    raise ImportError('socket.socket missing, proxy support unusable')

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None
        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header 
        for non-tunneling proxies if needed 
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)
        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies 
        (i.e. those which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt: 
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if (self.__proxy[4] != None and self.__proxy[5] != None):
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))
        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + ":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth)

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers =  ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        headers += ["Host: ", destaddr, "\r\n"]
        if (self.__proxy[4] != None and self.__proxy[5] != None):
            headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (type(destpair[0]) != type('')) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            if destpair[1] == 443:
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))
########NEW FILE########
__FILENAME__ = _version
# This is the version of this source code.

manual_verstr = "1.5"



auto_build_num = "211"



verstr = manual_verstr + "." + auto_build_num
try:
    from pyutil.version_class import Version as pyutil_Version
    __version__ = pyutil_Version(verstr)
except (ImportError, ValueError):
    # Maybe there is no pyutil installed.
    from distutils.version import LooseVersion as distutils_Version
    __version__ = distutils_Version(verstr)

########NEW FILE########
__FILENAME__ = gae
"""
    A pytz version that runs smoothly on Google App Engine.

    Based on http://appengine-cookbook.appspot.com/recipe/caching-pytz-helper/

    To use, add pytz to your path normally, but import it from the gae module:

        from pytz.gae import pytz

    Applied patches:

      - The zoneinfo dir is removed from pytz, as this module includes a ziped
        version of it.

      - pytz is monkey patched to load zoneinfos from a zipfile.

      - pytz is patched to not check all zoneinfo files when loaded. This is
        sad, I wish that was lazy, so it could be monkey patched. As it is,
        the zipfile patch doesn't work and it'll spend resources checking
        hundreds of files that we know aren't there.

    pytz caches loaded zoneinfos, and this module will additionally cache them
    in memcache to avoid unzipping constantly. The cache key includes the
    OLSON_VERSION so it is invalidated when pytz is updated.
"""
import os
import logging
import pytz
import zipfile
from cStringIO import StringIO

# Fake memcache for when we're not running under the SDK, likely a script.
class memcache(object):
    @classmethod
    def add(*args, **kwargs):
        pass

    @classmethod
    def get(*args, **kwargs):
        return None

try:
    # Don't use memcache outside of Google App Engine or with GAE's dev server.
    if not os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
        from google.appengine.api import memcache
except ImportError:
    pass

zoneinfo = None
zoneinfo_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
    'zoneinfo.zip'))


def get_zoneinfo():
    """Cache the opened zipfile in the module."""
    global zoneinfo
    if zoneinfo is None:
        zoneinfo = zipfile.ZipFile(zoneinfo_path)

    return zoneinfo


class TimezoneLoader(object):
    """A loader that that reads timezones using ZipFile."""
    def __init__(self):
        self.available = {}

    def open_resource(self, name):
        """Opens a resource from the zoneinfo subdir for reading."""
        name_parts = name.lstrip('/').split('/')
        if os.path.pardir in name_parts:
            raise ValueError('Bad path segment: %r' % os.path.pardir)

        cache_key = 'pytz.zoneinfo.%s.%s' % (pytz.OLSON_VERSION, name)
        zonedata = memcache.get(cache_key)
        if zonedata is None:
            zonedata = get_zoneinfo().read('zoneinfo/' + '/'.join(name_parts))
            memcache.add(cache_key, zonedata)
            logging.info('Added timezone to memcache: %s' % cache_key)
        else:
            logging.info('Loaded timezone from memcache: %s' % cache_key)

        return StringIO(zonedata)

    def resource_exists(self, name):
        """Return true if the given resource exists"""
        if name not in self.available:
            try:
                get_zoneinfo().getinfo('zoneinfo/' + name)
                self.available[name] = True
            except KeyError:
                self.available[name] = False

        return self.available[name]


pytz.loader = TimezoneLoader()

########NEW FILE########
__FILENAME__ = reference
'''
Reference tzinfo implementations from the Python docs.
Used for testing against as they are only correct for the years
1987 to 2006. Do not use these for real code.
'''

from datetime import tzinfo, timedelta, datetime
from pytz import utc, UTC, HOUR, ZERO

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

Local = LocalTimezone()

# A complete implementation of current DST rules for major US time zones.

def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt

# In the US, DST starts at 2am (standard time) on the first Sunday in April.
DSTSTART = datetime(1, 4, 1, 2)
# and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
# which is the first Sunday on or after Oct 25.
DSTEND = datetime(1, 10, 25, 1)

class USTimeZone(tzinfo):

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = first_sunday_on_or_after(DSTSTART.replace(year=dt.year))
        end = first_sunday_on_or_after(DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

Eastern  = USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = USTimeZone(-8, "Pacific",  "PST", "PDT")


########NEW FILE########
__FILENAME__ = tzfile
#!/usr/bin/env python
'''
$Id: tzfile.py,v 1.8 2004/06/03 00:15:24 zenzen Exp $
'''

from cStringIO import StringIO
from datetime import datetime, timedelta
from struct import unpack, calcsize

from pytz.tzinfo import StaticTzInfo, DstTzInfo, memorized_ttinfo
from pytz.tzinfo import memorized_datetime, memorized_timedelta


def build_tzinfo(zone, fp):
    head_fmt = '>4s c 15x 6l'
    head_size = calcsize(head_fmt)
    (magic, format, ttisgmtcnt, ttisstdcnt,leapcnt, timecnt,
        typecnt, charcnt) =  unpack(head_fmt, fp.read(head_size))

    # Make sure it is a tzfile(5) file
    assert magic == 'TZif'

    # Read out the transition times, localtime indices and ttinfo structures.
    data_fmt = '>%(timecnt)dl %(timecnt)dB %(ttinfo)s %(charcnt)ds' % dict(
        timecnt=timecnt, ttinfo='lBB'*typecnt, charcnt=charcnt)
    data_size = calcsize(data_fmt)
    data = unpack(data_fmt, fp.read(data_size))

    # make sure we unpacked the right number of values
    assert len(data) == 2 * timecnt + 3 * typecnt + 1
    transitions = [memorized_datetime(trans)
                   for trans in data[:timecnt]]
    lindexes = list(data[timecnt:2 * timecnt])
    ttinfo_raw = data[2 * timecnt:-1]
    tznames_raw = data[-1]
    del data

    # Process ttinfo into separate structs
    ttinfo = []
    tznames = {}
    i = 0
    while i < len(ttinfo_raw):
        # have we looked up this timezone name yet?
        tzname_offset = ttinfo_raw[i+2]
        if tzname_offset not in tznames:
            nul = tznames_raw.find('\0', tzname_offset)
            if nul < 0:
                nul = len(tznames_raw)
            tznames[tzname_offset] = tznames_raw[tzname_offset:nul]
        ttinfo.append((ttinfo_raw[i],
                       bool(ttinfo_raw[i+1]),
                       tznames[tzname_offset]))
        i += 3

    # Now build the timezone object
    if len(transitions) == 0:
        ttinfo[0][0], ttinfo[0][2]
        cls = type(zone, (StaticTzInfo,), dict(
            zone=zone,
            _utcoffset=memorized_timedelta(ttinfo[0][0]),
            _tzname=ttinfo[0][2]))
    else:
        # Early dates use the first standard time ttinfo
        i = 0
        while ttinfo[i][1]:
            i += 1
        if ttinfo[i] == ttinfo[lindexes[0]]:
            transitions[0] = datetime.min
        else:
            transitions.insert(0, datetime.min)
            lindexes.insert(0, i)

        # calculate transition info
        transition_info = []
        for i in range(len(transitions)):
            inf = ttinfo[lindexes[i]]
            utcoffset = inf[0]
            if not inf[1]:
                dst = 0
            else:
                for j in range(i-1, -1, -1):
                    prev_inf = ttinfo[lindexes[j]]
                    if not prev_inf[1]:
                        break
                dst = inf[0] - prev_inf[0] # dst offset

                if dst <= 0: # Bad dst? Look further.
                    for j in range(i+1, len(transitions)):
                        stdinf = ttinfo[lindexes[j]]
                        if not stdinf[1]:
                            dst = inf[0] - stdinf[0]
                            if dst > 0:
                                break # Found a useful std time.

            tzname = inf[2]

            # Round utcoffset and dst to the nearest minute or the
            # datetime library will complain. Conversions to these timezones
            # might be up to plus or minus 30 seconds out, but it is
            # the best we can do.
            utcoffset = int((utcoffset + 30) / 60) * 60
            dst = int((dst + 30) / 60) * 60
            transition_info.append(memorized_ttinfo(utcoffset, dst, tzname))

        cls = type(zone, (DstTzInfo,), dict(
            zone=zone,
            _utc_transition_times=transitions,
            _transition_info=transition_info))

    return cls()

if __name__ == '__main__':
    import os.path
    from pprint import pprint
    base = os.path.join(os.path.dirname(__file__), 'zoneinfo')
    tz = build_tzinfo('Australia/Melbourne',
                      open(os.path.join(base,'Australia','Melbourne'), 'rb'))
    tz = build_tzinfo('US/Eastern',
                      open(os.path.join(base,'US','Eastern'), 'rb'))
    pprint(tz._utc_transition_times)
    #print tz.asPython(4)
    #print tz.transitions_mapping

########NEW FILE########
__FILENAME__ = tzinfo
'''Base classes and helpers for building zone specific tzinfo classes'''

from datetime import datetime, timedelta, tzinfo
from bisect import bisect_right
try:
    set
except NameError:
    from sets import Set as set

import pytz

__all__ = []

_timedelta_cache = {}
def memorized_timedelta(seconds):
    '''Create only one instance of each distinct timedelta'''
    try:
        return _timedelta_cache[seconds]
    except KeyError:
        delta = timedelta(seconds=seconds)
        _timedelta_cache[seconds] = delta
        return delta

_epoch = datetime.utcfromtimestamp(0)
_datetime_cache = {0: _epoch}
def memorized_datetime(seconds):
    '''Create only one instance of each distinct datetime'''
    try:
        return _datetime_cache[seconds]
    except KeyError:
        # NB. We can't just do datetime.utcfromtimestamp(seconds) as this
        # fails with negative values under Windows (Bug #90096)
        dt = _epoch + timedelta(seconds=seconds)
        _datetime_cache[seconds] = dt
        return dt

_ttinfo_cache = {}
def memorized_ttinfo(*args):
    '''Create only one instance of each distinct tuple'''
    try:
        return _ttinfo_cache[args]
    except KeyError:
        ttinfo = (
                memorized_timedelta(args[0]),
                memorized_timedelta(args[1]),
                args[2]
                )
        _ttinfo_cache[args] = ttinfo
        return ttinfo

_notime = memorized_timedelta(0)

def _to_seconds(td):
    '''Convert a timedelta to seconds'''
    return td.seconds + td.days * 24 * 60 * 60


class BaseTzInfo(tzinfo):
    # Overridden in subclass
    _utcoffset = None
    _tzname = None
    zone = None

    def __str__(self):
        return self.zone


class StaticTzInfo(BaseTzInfo):
    '''A timezone that has a constant offset from UTC

    These timezones are rare, as most locations have changed their
    offset at some point in their history
    '''
    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        return (dt + self._utcoffset).replace(tzinfo=self)

    def utcoffset(self,dt):
        '''See datetime.tzinfo.utcoffset'''
        return self._utcoffset

    def dst(self,dt):
        '''See datetime.tzinfo.dst'''
        return _notime

    def tzname(self,dt):
        '''See datetime.tzinfo.tzname'''
        return self._tzname

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time'''
        if dt.tzinfo is not None:
            raise ValueError, 'Not naive datetime (tzinfo is already set)'
        return dt.replace(tzinfo=self)

    def normalize(self, dt, is_dst=False):
        '''Correct the timezone information on the given datetime'''
        if dt.tzinfo is None:
            raise ValueError, 'Naive time - no tzinfo set'
        return dt.replace(tzinfo=self)

    def __repr__(self):
        return '<StaticTzInfo %r>' % (self.zone,)

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes. 
        return pytz._p, (self.zone,)


class DstTzInfo(BaseTzInfo):
    '''A timezone that has a variable offset from UTC

    The offset might change if daylight savings time comes into effect,
    or at a point in history when the region decides to change their
    timezone definition.
    '''
    # Overridden in subclass
    _utc_transition_times = None # Sorted list of DST transition times in UTC
    _transition_info = None # [(utcoffset, dstoffset, tzname)] corresponding
                            # to _utc_transition_times entries
    zone = None

    # Set in __init__
    _tzinfos = None
    _dst = None # DST offset

    def __init__(self, _inf=None, _tzinfos=None):
        if _inf:
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = _inf
        else:
            _tzinfos = {}
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = self._transition_info[0]
            _tzinfos[self._transition_info[0]] = self
            for inf in self._transition_info[1:]:
                if not _tzinfos.has_key(inf):
                    _tzinfos[inf] = self.__class__(inf, _tzinfos)

    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        dt = dt.replace(tzinfo=None)
        idx = max(0, bisect_right(self._utc_transition_times, dt) - 1)
        inf = self._transition_info[idx]
        return (dt + inf[0]).replace(tzinfo=self._tzinfos[inf])

    def normalize(self, dt):
        '''Correct the timezone information on the given datetime

        If date arithmetic crosses DST boundaries, the tzinfo
        is not magically adjusted. This method normalizes the
        tzinfo to the correct one.

        To test, first we need to do some setup

        >>> from pytz import timezone
        >>> utc = timezone('UTC')
        >>> eastern = timezone('US/Eastern')
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'

        We next create a datetime right on an end-of-DST transition point,
        the instant when the wallclocks are wound back one hour.

        >>> utc_dt = datetime(2002, 10, 27, 6, 0, 0, tzinfo=utc)
        >>> loc_dt = utc_dt.astimezone(eastern)
        >>> loc_dt.strftime(fmt)
        '2002-10-27 01:00:00 EST (-0500)'

        Now, if we subtract a few minutes from it, note that the timezone
        information has not changed.

        >>> before = loc_dt - timedelta(minutes=10)
        >>> before.strftime(fmt)
        '2002-10-27 00:50:00 EST (-0500)'

        But we can fix that by calling the normalize method

        >>> before = eastern.normalize(before)
        >>> before.strftime(fmt)
        '2002-10-27 01:50:00 EDT (-0400)'
        '''
        if dt.tzinfo is None:
            raise ValueError, 'Naive time - no tzinfo set'

        # Convert dt in localtime to UTC
        offset = dt.tzinfo._utcoffset
        dt = dt.replace(tzinfo=None)
        dt = dt - offset
        # convert it back, and return it
        return self.fromutc(dt)

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time.

        This method should be used to construct localtimes, rather
        than passing a tzinfo argument to a datetime constructor.

        is_dst is used to determine the correct timezone in the ambigous
        period at the end of daylight savings time.

        >>> from pytz import timezone
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'
        >>> amdam = timezone('Europe/Amsterdam')
        >>> dt  = datetime(2004, 10, 31, 2, 0, 0)
        >>> loc_dt1 = amdam.localize(dt, is_dst=True)
        >>> loc_dt2 = amdam.localize(dt, is_dst=False)
        >>> loc_dt1.strftime(fmt)
        '2004-10-31 02:00:00 CEST (+0200)'
        >>> loc_dt2.strftime(fmt)
        '2004-10-31 02:00:00 CET (+0100)'
        >>> str(loc_dt2 - loc_dt1)
        '1:00:00'

        Use is_dst=None to raise an AmbiguousTimeError for ambiguous
        times at the end of daylight savings

        >>> loc_dt1 = amdam.localize(dt, is_dst=None)
        Traceback (most recent call last):
            [...]
        AmbiguousTimeError: 2004-10-31 02:00:00

        is_dst defaults to False

        >>> amdam.localize(dt) == amdam.localize(dt, False)
        True

        is_dst is also used to determine the correct timezone in the
        wallclock times jumped over at the start of daylight savings time.

        >>> pacific = timezone('US/Pacific')
        >>> dt = datetime(2008, 3, 9, 2, 0, 0)
        >>> ploc_dt1 = pacific.localize(dt, is_dst=True)
        >>> ploc_dt2 = pacific.localize(dt, is_dst=False)
        >>> ploc_dt1.strftime(fmt)
        '2008-03-09 02:00:00 PDT (-0700)'
        >>> ploc_dt2.strftime(fmt)
        '2008-03-09 02:00:00 PST (-0800)'
        >>> str(ploc_dt2 - ploc_dt1)
        '1:00:00'

        Use is_dst=None to raise a NonExistentTimeError for these skipped
        times.

        >>> loc_dt1 = pacific.localize(dt, is_dst=None)
        Traceback (most recent call last):
            [...]
        NonExistentTimeError: 2008-03-09 02:00:00
        '''
        if dt.tzinfo is not None:
            raise ValueError, 'Not naive datetime (tzinfo is already set)'

        # Find the two best possibilities.
        possible_loc_dt = set()
        for delta in [timedelta(days=-1), timedelta(days=1)]:
            loc_dt = dt + delta
            idx = max(0, bisect_right(
                self._utc_transition_times, loc_dt) - 1)
            inf = self._transition_info[idx]
            tzinfo = self._tzinfos[inf]
            loc_dt = tzinfo.normalize(dt.replace(tzinfo=tzinfo))
            if loc_dt.replace(tzinfo=None) == dt:
                possible_loc_dt.add(loc_dt)

        if len(possible_loc_dt) == 1:
            return possible_loc_dt.pop()

        # If there are no possibly correct timezones, we are attempting
        # to convert a time that never happened - the time period jumped
        # during the start-of-DST transition period.
        if len(possible_loc_dt) == 0:
            # If we refuse to guess, raise an exception.
            if is_dst is None:
                raise NonExistentTimeError(dt)

            # If we are forcing the pre-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock forward a few
            # hours.
            elif is_dst:
                return self.localize(
                    dt + timedelta(hours=6), is_dst=True) - timedelta(hours=6)

            # If we are forcing the post-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock back.
            else:
                return self.localize(
                    dt - timedelta(hours=6), is_dst=False) + timedelta(hours=6)


        # If we get this far, we have multiple possible timezones - this
        # is an ambiguous case occuring during the end-of-DST transition.

        # If told to be strict, raise an exception since we have an
        # ambiguous case
        if is_dst is None:
            raise AmbiguousTimeError(dt)

        # Filter out the possiblilities that don't match the requested
        # is_dst
        filtered_possible_loc_dt = [
            p for p in possible_loc_dt
                if bool(p.tzinfo._dst) == is_dst
            ]

        # Hopefully we only have one possibility left. Return it.
        if len(filtered_possible_loc_dt) == 1:
            return filtered_possible_loc_dt[0]

        if len(filtered_possible_loc_dt) == 0:
            filtered_possible_loc_dt = list(possible_loc_dt)

        # If we get this far, we have in a wierd timezone transition
        # where the clocks have been wound back but is_dst is the same
        # in both (eg. Europe/Warsaw 1915 when they switched to CET).
        # At this point, we just have to guess unless we allow more
        # hints to be passed in (such as the UTC offset or abbreviation),
        # but that is just getting silly.
        #
        # Choose the earliest (by UTC) applicable timezone.
        def mycmp(a,b):
            return cmp(
                    a.replace(tzinfo=None) - a.tzinfo._utcoffset,
                    b.replace(tzinfo=None) - b.tzinfo._utcoffset,
                    )
        filtered_possible_loc_dt.sort(mycmp)
        return filtered_possible_loc_dt[0]

    def utcoffset(self, dt):
        '''See datetime.tzinfo.utcoffset'''
        return self._utcoffset

    def dst(self, dt):
        '''See datetime.tzinfo.dst'''
        return self._dst

    def tzname(self, dt):
        '''See datetime.tzinfo.tzname'''
        return self._tzname

    def __repr__(self):
        if self._dst:
            dst = 'DST'
        else:
            dst = 'STD'
        if self._utcoffset > _notime:
            return '<DstTzInfo %r %s+%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )
        else:
            return '<DstTzInfo %r %s%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes.
        return pytz._p, (
                self.zone,
                _to_seconds(self._utcoffset),
                _to_seconds(self._dst),
                self._tzname
                )


class InvalidTimeError(Exception):
    '''Base class for invalid time exceptions.'''


class AmbiguousTimeError(InvalidTimeError):
    '''Exception raised when attempting to create an ambiguous wallclock time.

    At the end of a DST transition period, a particular wallclock time will
    occur twice (once before the clocks are set back, once after). Both
    possibilities may be correct, unless further information is supplied.

    See DstTzInfo.normalize() for more info
    '''


class NonExistentTimeError(InvalidTimeError):
    '''Exception raised when attempting to create a wallclock time that
    cannot exist.

    At the start of a DST transition period, the wallclock time jumps forward.
    The instants jumped over never occur.
    '''


def unpickler(zone, utcoffset=None, dstoffset=None, tzname=None):
    """Factory function for unpickling pytz tzinfo instances.

    This is shared for both StaticTzInfo and DstTzInfo instances, because
    database changes could cause a zones implementation to switch between
    these two base classes and we can't break pickles on a pytz version
    upgrade.
    """
    # Raises a KeyError if zone no longer exists, which should never happen
    # and would be a bug.
    tz = pytz.timezone(zone)

    # A StaticTzInfo - just return it
    if utcoffset is None:
        return tz

    # This pickle was created from a DstTzInfo. We need to
    # determine which of the list of tzinfo instances for this zone
    # to use in order to restore the state of any datetime instances using
    # it correctly.
    utcoffset = memorized_timedelta(utcoffset)
    dstoffset = memorized_timedelta(dstoffset)
    try:
        return tz._tzinfos[(utcoffset, dstoffset, tzname)]
    except KeyError:
        # The particular state requested in this timezone no longer exists.
        # This indicates a corrupt pickle, or the timezone database has been
        # corrected violently enough to make this particular
        # (utcoffset,dstoffset) no longer exist in the zone, or the
        # abbreviation has been changed.
        pass

    # See if we can find an entry differing only by tzname. Abbreviations
    # get changed from the initial guess by the database maintainers to
    # match reality when this information is discovered.
    for localized_tz in tz._tzinfos.values():
        if (localized_tz._utcoffset == utcoffset
                and localized_tz._dst == dstoffset):
            return localized_tz

    # This (utcoffset, dstoffset) information has been removed from the
    # zone. Add it back. This might occur when the database maintainers have
    # corrected incorrect information. datetime instances using this
    # incorrect information will continue to do so, exactly as they were
    # before being pickled. This is purely an overly paranoid safety net - I
    # doubt this will ever been needed in real life.
    inf = (utcoffset, dstoffset, tzname)
    tz._tzinfos[inf] = tz.__class__(inf, tz._tzinfos)
    return tz._tzinfos[inf]


########NEW FILE########
__FILENAME__ = handler
# -*- coding: utf-8 -*-
import sys
import logging

from urllib import urlencode
import urlparse

# taken from anyjson.py
try:
    import simplejson as json
except ImportError: # pragma: no cover
    try:
        # Try to import from django, should work on App Engine
        from django.utils import simplejson as json
    except ImportError:
        # Should work for Python2.6 and higher.
        import json

# already in the App Engine libs, see app.yaml on how to specify libraries
# need this for providers like LinkedIn
from lxml import etree

# it's a OAuth 1.0 spec even though the lib is called oauth2
import libs.oauth2 as oauth1

# users module is needed for OpenID authentication.
from google.appengine.api import urlfetch, users


__all__ = ['SimpleAuthHandler']


class SimpleAuthHandler(object):
    """
    Google auth:
    http://code.google.com/apis/accounts/docs/OAuth2WebServer.html

    Facbook auth:
    http://developers.facebook.com/docs/authentication/

    LinkedIn auth:
    https://developer.linkedin.com/documents/linkedins-oauth-details

    Windows Live:
    http://msdn.microsoft.com/en-us/library/hh243648.aspx#user

    Twtitter:
    https://dev.twitter.com/docs/auth/oauth
    """

    PROVIDERS = {
      'google'      : ('oauth2',
        'https://accounts.google.com/o/oauth2/auth?{0}',
        'https://accounts.google.com/o/oauth2/token'),
      'windows_live': ('oauth2',
        'https://oauth.live.com/authorize?{0}',
        'https://oauth.live.com/token'),
      'facebook'    : ('oauth2',
        'https://www.facebook.com/dialog/oauth?{0}',
        'https://graph.facebook.com/oauth/access_token'),
      'linkedin'    : ('oauth1', {
        'request': 'https://api.linkedin.com/uas/oauth/requestToken',
        'auth'   : 'https://www.linkedin.com/uas/oauth/authenticate?{0}'
      },           'https://api.linkedin.com/uas/oauth/accessToken'),
      'twitter'     : ('oauth1', {
         'request': 'https://api.twitter.com/oauth/request_token',
         'auth'   : 'https://api.twitter.com/oauth/authenticate?{0}'
      },            'https://api.twitter.com/oauth/access_token'),
      'openid'      : ('openid', None)
    }


    TOKEN_RESPONSE_PARSERS = {
      'google'      : '_json_parser',
      'windows_live': '_json_parser',
      'facebook'    : '_query_string_parser',
      'linkedin'    : '_query_string_parser',
      'twitter'     : '_query_string_parser'
    }

    def _simple_auth(self, provider=None):
        """Dispatcher of auth init requests, e.g.
        GET /auth/PROVIDER

        It'll call _<authtype>_init() method, where
        <authtype> is oauth2, oauth1 or openid (defined in PROVIDERS dict).

        If a particular provider is not defined in the PROVIDERS
        or _<authtype>_init() does not exist for a specific auth type,
        it'll fall back to self._provider_not_supported() passing in the origina provider name.
        """
        cfg = self.PROVIDERS.get(provider, (None,))
        meth = '_%s_init' % cfg[0]
        if hasattr(self, meth):
            try:

                # initiate openid, oauth1 or oauth2 authentication
                # we don't respond directly in here: specific methods are in charge
                # with redirecting user to an auth endpoint
                getattr(self, meth)(provider, cfg[1])

            except:
                error_msg = str(sys.exc_info()[1])
                logging.error(error_msg)
                self._auth_error(provider, msg=error_msg)

        else:
            logging.error('Provider %s is not supported' % provider)
            self._provider_not_supported(provider)

    def _auth_callback(self, provider=None):
        """Dispatcher of callbacks from auth providers, e.g.
        /auth/PROVIDER/callback?params=...

        It'll call _<authtype>_callback() method, where
        <authtype> is oauth2, oauth1 or openid (defined in PROVIDERS dict).

        Falls back to self._provider_not_supported(provider).
        """
        cfg = self.PROVIDERS.get(provider, (None,))
        meth = '_%s_callback' % cfg[0]
        if hasattr(self, meth):
            try:

                user_data, auth_info = getattr(self, meth)(provider, *cfg[-1:])
                # we're done here. the rest should be implemented by the actual app
                self._on_signin(user_data, auth_info, provider)

            except:
                error_msg = str(sys.exc_info()[1])
                logging.error(error_msg)
                self._auth_error(provider, msg=error_msg)
        else:
            logging.error('Provider %s is not supported' % provider)
            self._provider_not_supported(provider)

    def _provider_not_supported(self, provider=None):
        """Callback triggered whenever user's trying to authenticate agains a provider we don't support,
        or provider wasn't specified for some reason.

        Defaults to redirecting to / (root).
        Override this method for a custom behaviour.
        """
        self.redirect('/')

    def _auth_error(self, provider, msg=None):
        """Being called on any error during auth process, with optional text message provided.
        Defaults to redirecting to /"""
        self.redirect('/')

    def _oauth2_init(self, provider, auth_url):
        """Initiates OAuth 2.0 dance. Falls back to self._provider_not_supported(provider)
        if either key or secret is missing."""
        key, secret, scope = self._get_consumer_info_for(provider)
        callback_url = self._callback_uri_for(provider)

        if key and secret and auth_url and callback_url:
            params = { 'response_type': 'code', 'client_id': key, 'redirect_uri': callback_url }
            if scope:
                params.update(scope=scope)

            target_url = auth_url.format(urlencode(params))
            logging.debug('Redirecting user to %s' % target_url)

            self.redirect(target_url)

        else:
            logging.error('Provider %s is not supported' % provider)
            self._provider_not_supported(provider)

    def _oauth2_callback(self, provider, access_token_url):
        """Step 2 of OAuth 2.0, whenever the user accepts or denies access."""
        code = self.request.get('code', None)
        error = self.request.get('error', None)
        callback_url = self._callback_uri_for(provider)
        consumer_key, consumer_secret, scope = self._get_consumer_info_for(provider)

        if error:
            raise Exception(error)

        payload = {
          'code': code,
          'client_id': consumer_key,
          'client_secret': consumer_secret,
          'redirect_uri': callback_url,
          'grant_type': 'authorization_code'
        }

        resp = urlfetch.fetch(
          url=access_token_url,
          payload=urlencode(payload),
          method=urlfetch.POST,
          headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        auth_info = getattr(self, self.TOKEN_RESPONSE_PARSERS[provider])(resp.content)
        user_data = getattr(self, '_get_%s_user_info' % provider)(auth_info, key=consumer_key, secret=consumer_secret)

        return (user_data, auth_info)

    def _oauth1_init(self, provider, auth_urls):
        """Initiates OAuth 1.0 dance"""
        key, secret = self._get_consumer_info_for(provider)
        callback_url = self._callback_uri_for(provider)
        token_request_url = auth_urls.get('request', None)
        auth_url = auth_urls.get('auth', None)
        _parse = getattr(self, self.TOKEN_RESPONSE_PARSERS[provider], None)

        if not(key or secret or token_request_url or auth_url or callback_url or _parse):
            raise Exception('Provider %s is not supported' % provider)

        # make a request_token request
        client = self._oauth1_client(consumer_key=key, consumer_secret=secret)
        resp, content = client.request(auth_urls['request'], "GET")

        if resp.status != 200:
            raise Exception("Could not fetch a valid response from %s" % provider)

        # parse token request response
        request_token = _parse(content)
        if not request_token.get('oauth_token', None):
            raise Exception("Couldn't get a valid token from %s\n%s" % (provider, str(request_token)))

        target_url = auth_urls['auth'].format(urlencode({
          'oauth_token': request_token.get('oauth_token', None),
          'oauth_callback': callback_url
        }))

        logging.debug('Redirecting user to %s' % target_url)

        # save request token for later, the callback
        self.session['req_token'] = request_token
        self.redirect(target_url)

    def _oauth1_callback(self, provider, access_token_url):
        """Third step of OAuth 1.0 dance."""
        request_token = self.session.pop('req_token', None)
        verifier = self.request.get('oauth_verifier', None)
        consumer_key, consumer_secret = self._get_consumer_info_for(provider)

        if not request_token:
            raise Exception("Couldn't find request token")

        if not verifier:
            raise Exception("No OAuth verifier was provided")

        token = oauth1.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(verifier)
        client = self._oauth1_client(token, consumer_key, consumer_secret)

        resp, content = client.request(access_token_url, "POST")
        auth_info = getattr(self, self.TOKEN_RESPONSE_PARSERS[provider])(content)
        user_data = getattr(self, '_get_%s_user_info' % provider)(auth_info, key=consumer_key, secret=consumer_secret)

        return (user_data, auth_info)

    def _openid_init(self, provider='openid', identity=None):
        """Initiates OpenID dance using App Engine users module API."""
        identity_url = identity or self.request.get('identity_url', None)
        callback_url = self._callback_uri_for(provider)

        if identity_url and callback_url:
            target_url = users.create_login_url(
              dest_url=callback_url,
              federated_identity=identity_url
            )
            logging.debug('Redirecting user to %s' % target_url)
            self.redirect(target_url)

        else:
            logging.error('Either identity or callback were not specified (%s, %s)' % (identity_url, callback_url))
            self._provider_not_supported(provider)

    def _openid_callback(self, provider='openid', _identity=None):
        """Being called back by an OpenID provider
        after the user has been authenticated.
        """
        user = users.get_current_user()

        if not user or not user.federated_identity():
            raise Exception('OpenID Authentication failed')

        uinfo = {
          'id'      : user.federated_identity(),
          'nickname': user.nickname(),
          'email'   : user.email()
        }

        return (uinfo, {'provider': user.federated_provider()})


    #
    # callbacks and consumer key/secrets
    #

    def _callback_uri_for(self, provider):
        """Returns a callback URL for a 2nd step of the auth process.
        Override this with something like:

          return self.uri_for('auth_callback', provider=provider, _full=True)
        """
        return None

    def _get_consumer_info_for(self, provider):
        """Should return a tuple (key, secret, desired_scopes).
        Defaults to None. You should redefine this method and return real values."""
        return (None, None, None)

    #
    # user profile/info
    #

    def _get_google_user_info(self, auth_info, key=None, secret=None):
        """Returns a dict of currenly logging in user.
        Google API endpoint:
        https://www.googleapis.com/oauth2/v1/userinfo
        """
        resp = self._oauth2_request(
          'https://www.googleapis.com/oauth2/v1/userinfo?{0}',
          auth_info['access_token']
        )
        return json.loads(resp)

    def _get_windows_live_user_info(self, auth_info, key=None, secret=None):
        """Windows Live API user profile endpoint:
        https://apis.live.net/v5.0/me

        Profile picture:
        https://apis.live.net/v5.0/USER_ID/picture
        """
        resp = self._oauth2_request(
          'https://apis.live.net/v5.0/me?{0}',
          auth_info['access_token']
        )
        uinfo = json.loads(resp)
        uinfo.update(avatar_url='https://apis.live.net/v5.0/{0}/picture'.format(uinfo['id']))
        return uinfo

    def _get_facebook_user_info(self, auth_info, key=None, secret=None):
        """Facebook Graph API endpoint:
        https://graph.facebook.com/me
        """
        resp = self._oauth2_request(
          'https://graph.facebook.com/me?{0}',
          auth_info['access_token']
        )
        return json.loads(resp)

    def _get_linkedin_user_info(self, auth_info, key=None, secret=None):
        """Returns a dict of currently logging in linkedin user
        LinkedIn user profile API endpoint:
        http://api.linkedin.com/v1/people/~
        or
        http://api.linkedin.com/v1/people/~:(id,first-name,last-name,picture-url,public-profile-url,headline)
        """
        token = oauth1.Token(key=auth_info['oauth_token'], secret=auth_info['oauth_token_secret'])
        client = self._oauth1_client(token, key, secret)
        resp, content = client.request(
          'http://api.linkedin.com/v1/people/~:(id,first-name,last-name,picture-url,public-profile-url,headline)'
        )

        person = etree.fromstring(content)
        uinfo = {}
        for e in person:
            uinfo.setdefault(e.tag, e.text)

        return uinfo

    def _get_twitter_user_info(self, auth_info, key=None, secret=None):
        """Returns a dict of twitter user using
        https://api.twitter.com/1/account/verify_credentials.json
        """
        token = oauth1.Token(key=auth_info['oauth_token'], secret=auth_info['oauth_token_secret'])
        client = self._oauth1_client(token, key, secret)

        resp, content = client.request(
          'https://api.twitter.com/1/account/verify_credentials.json'
        )
        uinfo = json.loads(content)
        uinfo.setdefault('link', 'http://twitter.com/%s' % uinfo['screen_name'])
        return uinfo

    #
    # aux methods
    #

    def _oauth1_client(self, token=None, consumer_key=None, consumer_secret=None):
        """Returns OAuth 1.0 client that is capable of signing requests."""
        args = [oauth1.Consumer(key=consumer_key, secret=consumer_secret)]
        if token:
            args.append(token)

        return oauth1.Client(*args)

    def _oauth2_request(self, url, token):
        """Makes an HTTP request with OAuth 2.0 access token using App Engine URLfetch API"""
        return urlfetch.fetch(url.format(urlencode({'access_token':token}))).content

    def _query_string_parser(self, body):
        """Parses response body of an access token request query and returns
        the result in JSON format.

        Facebook, LinkedIn and Twitter respond with a query string, not JSON."""
        return dict(urlparse.parse_qsl(body))

    def _json_parser(self, body):
        """Parses body string into JSON dict"""
        return json.loads(body)

########NEW FILE########
__FILENAME__ = settings
import os
from google.appengine.api.app_identity import get_default_version_hostname, get_application_id

from secrets import SESSION_KEY

if 'SERVER_SOFTWARE' in os.environ and os.environ['SERVER_SOFTWARE'].startswith('Dev'):
    DEBUG = True
    HOME_URL = 'http://localhost' + ':8085'
else:
    DEBUG = False
    HOME_URL = 'http://' + get_default_version_hostname()

# webapp2 config
app_config = {
  'webapp2_extras.sessions': {
    'cookie_name': '_simpleauth_sess',
    'secret_key': SESSION_KEY
  },
  'webapp2_extras.auth': {
    'user_attributes': []
  }
}

# i18n config
AVAILABLE_LOCALES = ['en_US', 'de_DE']

# List of valid APIs
APIS = frozenset({'signup_mailing_list', 'change_email_addr'})

#200 OK - Everything worked as expected.
#400 Bad Request - Often missing a required parameter.
#401 Unauthorized - No valid API key provided.
#402 Request Failed - Parameters were valid but request failed.
#404 Not Found - The requested item doesn't exist.
#500, 502, 503, 504 Server errors - something went wrong on Stripe's end.

API_CODES  = { 200 : 'Success', 
               400 : {'email'       : 'Invalid email address', 
                      'password'    : 'Invalid password', 
                      'email_password' : 'Invalid email or password', 
                      'unsupported' : 'Unsupported API', 
                      'missing'     : 'Not all parameter present', 
                      'noemail'     : 'Email not valid'}, 
               401 : 'Unauthorized', 
               402 : {'unconfirmed' : 'Email has not been confirmed.', 
                      'duplicate'   : 'User already exists.'},
               404 : 'Does not exist', 
               500 : {'generic'        : 'Server error', 
                      'admin_required' : 'Please contact application administrator for support'}}

# URLs
APP_ID = get_application_id()

COOKIE_TEMPLATE = { 'id'        : 0,     #session id
                    'pageviews' : 0, 
                    'authed'    : False, 
                    'active'    : True }

DATE_FORMAT_HTML = "dd-mm-yyyy"
DATE_FORMAT = "%d-%m-%Y"

# Email Authentication
EMAIL_CONFIRM_BODY = """ 
Hello, %s!

Please click the link below to confirm your email address: 

%s

Thank you. 
""" 

EMAIL_SENDER = "ilya.bagrak@gmail.com"

########NEW FILE########
__FILENAME__ = testrunner
#!/usr/bin/python
import optparse
import sys
# Install the Python unittest2 package before you run this script.
import unittest2

USAGE = """%prog SDK_PATH TEST_PATH
Run unit tests for App Engine apps.

SDK_PATH    Path to the SDK installation
TEST_PATH   Path to package containing test modules"""


def main(sdk_path, test_path):
    sys.path.insert(0, sdk_path)
    import dev_appserver
    dev_appserver.fix_sys_path()
    suite = unittest2.loader.TestLoader().discover(test_path)
    unittest2.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    parser = optparse.OptionParser(USAGE)
    options, args = parser.parse_args()
    if len(args) != 2:
        print 'Error: Exactly 2 arguments required.'
        parser.print_help()
        sys.exit(1)
    SDK_PATH = args[0]
    TEST_PATH = args[1]
    main(SDK_PATH, TEST_PATH)
########NEW FILE########
__FILENAME__ = test_api
import webapp2
import webtest
import unittest2
import copy
import urllib
import logging

from google.appengine.ext import testbed
from google.appengine.ext import db
from webapp2_extras import json
from webapp2_extras.appengine.auth import models as users

import app
import settings
import handlers
from core import model

class RESTTest(unittest2.TestCase):
	str_widget = '{"int_field":1,"email_field":"i@co.co","boolean_field":true,"date_field":"12-02-2012","text_field":"daf","id":2,"string_field":"dfa","link_field":"http://i.co"}'
	json_widget = json.decode(str_widget)

	faux_db_user = {'email' : 'ibagrak@hotmail.com', 
					'password_raw' : 'blah', 
					'pic' : 'http://www.gravatar.com/avatar/759e5b31901d7d20a106f7f8f60a9383?d=http%3A//green-algae.appspot.com/img/algae.png', 
					'profile' : 'mailto:ibagrak@hotmail.com', 
					'username' : 'ilya' }
	
	def signin_faux_user(self):
		users.User.create_user('own:ibagrak@hotmail.com', **self.faux_db_user)

		response = self.testapp.get('/email-signin?action=signin_email&email=%s&password=%s' % (self.faux_db_user['email'], self.faux_db_user['password_raw']))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'application/json')

	def setUp(self):
		# Create a WSGI application.
		application = webapp2.WSGIApplication(app.routes, debug = True, config = settings.app_config)
		application.error_handlers[404] = handlers.common.handle_404
		application.error_handlers[500] = handlers.common.handle_500
	
		# Wrap the app with WebTest's TestApp.
		self.testapp = webtest.TestApp(application)

		# First, create an instance of the Testbed class.
		self.testbed = testbed.Testbed()

		# Then activate the testbed, which prepares the service stubs for use.
		self.testbed.activate()

		# Next, declare which service stubs you want to use.
		self.testbed.init_datastore_v3_stub()
		self.testbed.init_memcache_stub()

	def tearDown(self):
		self.testbed.deactivate()

	# test the handler.
	def test_handler_smoke(self):
		response = self.testapp.get('/')
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')

	# test common.BaseRESTHandler APIs
	def test_put_unauth(self):
		response = self.testapp.put('/rest/Widgets', 
				params = self.str_widget, 
				expect_errors=True, 
				content_type = "application/json; charset=utf-8")
		
		self.assertEqual(response.status_int, 401)
		self.assertEqual(json.decode(response.body)['code'], 401)

	def test_get(self):
		# create widget in DB and get its id
		widget = copy.copy(self.json_widget)
		ident = model.Widget.put(widget).key().id()

		self.assertEqual(1, len(model.Widget.all().fetch(2)))

		# get widget with the same id through API and verify that email field is correct
		response = self.testapp.get('/rest/Widget/' + str(ident), 
				params = self.str_widget, 
				expect_errors=True)
		
		self.assertEqual(response.status_int, 200)
		self.assertEqual(json.decode(response.body)['code'], 200)
		self.assertEqual(json.decode(response.body)['response']['email_field'], "i@co.co")
	
	def test_post(self):
		# create widget in DB and get its id
		widget = copy.copy(self.json_widget)
		ident = model.Widget.put(widget).key().id()

		self.assertEqual(1, len(model.Widget.all().fetch(2)))

		# update widget with the same id through API
		widget = copy.copy(self.json_widget)
		widget['email_field'] = 'newemail@co.co'
		response = self.testapp.post('/rest/Widget/' + str(ident), 
				params = json.encode(widget), 
				expect_errors=True, 
				content_type = "application/json; charset=utf-8")
		
		self.assertEqual(response.status_int, 200)
		self.assertEqual(json.decode(response.body)['code'], 200)

		# get widget with the same id through API and verify that email field is correct
		response = self.testapp.get('/rest/Widget/' + str(ident), 
				params = self.str_widget, 
				expect_errors=True)
		
		self.assertEqual(response.status_int, 200)
		self.assertEqual(json.decode(response.body)['code'], 200)
		self.assertEqual(json.decode(response.body)['response']['email_field'], "newemail@co.co")

	def test_delete_unauth(self):
		# create widget in DB and get its id
		widget = copy.copy(self.json_widget)
		ident = model.Widget.put(widget).key().id()

		self.assertEqual(1, len(model.Widget.all().fetch(2)))

		response = self.testapp.delete('/rest/Widget/' + str(ident), 
				expect_errors=True)
		
		self.assertEqual(response.status_int, 401)
		self.assertEqual(json.decode(response.body)['code'], 401)

	def test_put_auth(self):
		self.signin_faux_user()

		response = self.testapp.put('/rest/Widgets', 
				params = self.str_widget, 
				expect_errors=True, 
				content_type = "application/json; charset=utf-8")
		
		self.assertEqual(response.status_int, 200)
		self.assertEqual(json.decode(response.body)['code'], 200)

	def test_delete_auth(self):
		self.signin_faux_user()

		# create widget in DB and get its id
		widget = copy.copy(self.json_widget)
		ident = model.Widget.put(widget).key().id()

		self.assertEqual(1, len(model.Widget.all().fetch(2)))

		response = self.testapp.delete('/rest/Widget/' + str(ident), 
				expect_errors=True)
		
		self.assertEqual(response.status_int, 200)
		self.assertEqual(json.decode(response.body)['code'], 200)

class RPCTest(unittest2.TestCase):
	str_widget = '{"int_field":1,"email_field":"i@co.co","boolean_field":true,"date_field":"12-02-2012","text_field":"daf","id":2,"string_field":"dfa","link_field":"http://i.co"}'
	json_widget = json.decode(str_widget)

	faux_db_user = {'email' : 'ibagrak@hotmail.com', 
					'password_raw' : 'blah', 
					'pic' : 'http://www.gravatar.com/avatar/759e5b31901d7d20a106f7f8f60a9383?d=http%3A//green-algae.appspot.com/img/algae.png', 
					'profile' : 'mailto:ibagrak@hotmail.com', 
					'username' : 'ilya' }

	user = None
	def signin_faux_user(self):
		ok, self.user = users.User.create_user('own:ibagrak@hotmail.com', **self.faux_db_user)

		response = self.testapp.get('/email-signin?action=signin_email&email=%s&password=%s' % (self.faux_db_user['email'], self.faux_db_user['password_raw']))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'application/json')

	def setUp(self):
		# Create a WSGI application.
		application = webapp2.WSGIApplication(app.routes, debug = True, config = settings.app_config)
		application.error_handlers[404] = handlers.common.handle_404
		application.error_handlers[500] = handlers.common.handle_500
	
		# Wrap the app with WebTest's TestApp.
		self.testapp = webtest.TestApp(application)

		# First, create an instance of the Testbed class.
		self.testbed = testbed.Testbed()

		# Then activate the testbed, which prepares the service stubs for use.
		self.testbed.activate()

		# Next, declare which service stubs you want to use.
		self.testbed.init_datastore_v3_stub()
		self.testbed.init_memcache_stub()

	def test_mailing_list(self):
		response = self.testapp.get('/rpc/signup_mailing_list?email_mailinglist=%s' % urllib.quote('ibagrak@hotmail.com'))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'application/json')

		self.assertNotEqual(None, db.Query(model.EmailAddr).filter('email =', 'ibagrak@hotmail.com').get())

	def test_update_email_noauth(self):
		response = self.testapp.get('/rpc/change_email_addr?email_change=%s' % urllib.quote('ibagrak@hotmail.com'), expect_errors=True)
		self.assertEqual(response.status_int, 401)
		self.assertEqual(response.content_type, 'application/json')

	def test_update_email_auth(self):
		self.signin_faux_user()

		response = self.testapp.get('/rpc/change_email_addr?email_change=%s' % urllib.quote('ibagrak@hotmail.com'))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'application/json')

		self.assertEqual(self.user.email, 'ibagrak@hotmail.com')




########NEW FILE########
__FILENAME__ = test_i18n
import webapp2
import webtest
import unittest2
import copy
import urllib
import logging

from google.appengine.ext import testbed
from google.appengine.ext import db
from webapp2_extras import json
from webapp2_extras.appengine.auth import models as users

import app
import settings
import handlers
import re
from core import model

class I18NTest(unittest2.TestCase):
	# Language-Accept: header values for tests
	hdr_english_accept = {'Accept-Language': 'en'}
	hdr_other_accept   = {'Accept-Language': 'da, fr'}
	hdr_german_accept  = {'Accept-Language': 'de'}
	hdr_english_prefer = {'Accept-Language': 'en, de'}
	hdr_german_prefer  = {'Accept-Language': 'de, en'}

	# text to check if english response
	txt_in_english = r'was created by'
	txt_in_german  = r'ist ein Werk von'

	def setUp(self):
		# Create a WSGI application.
		application = webapp2.WSGIApplication(app.routes, debug = True, config = settings.app_config)
		application.error_handlers[404] = handlers.common.handle_404
		application.error_handlers[500] = handlers.common.handle_500
	
		# Wrap the app with WebTest's TestApp.
		self.testapp = webtest.TestApp(application)

		# First, create an instance of the Testbed class.
		self.testbed = testbed.Testbed()

		# Then activate the testbed, which prepares the service stubs for use.
		self.testbed.activate()

		# Next, declare which service stubs you want to use.
		self.testbed.init_datastore_v3_stub()
		self.testbed.init_memcache_stub()

	def tearDown(self):
		self.testbed.deactivate()

	# test with 'only english'
	def test_english(self):
		response = self.testapp.get('/', headers=self.hdr_english_accept)
		self.assertEqual(response.status_int, 200)
		self.assertIn(self.txt_in_english, response.body)
		self.assertNotIn(self.txt_in_german, response.body)

	# test with 'only german'
	def test_german(self):
		response = self.testapp.get('/', headers=self.hdr_german_accept)
		self.assertEqual(response.status_int, 200)
		self.assertIn(self.txt_in_german, response.body)
		self.assertNotIn(self.txt_in_english, response.body)

	# test with 'english preferred'
	def test_english_preferred(self):
		response = self.testapp.get('/', headers=self.hdr_english_prefer)
		self.assertEqual(response.status_int, 200)
		self.assertIn(self.txt_in_english, response.body)
		self.assertNotIn(self.txt_in_german, response.body)

	# test with 'german preferred'
	def test_german(self):
		response = self.testapp.get('/', headers=self.hdr_german_prefer)
		self.assertEqual(response.status_int, 200)
		self.assertIn(self.txt_in_german, response.body)
		self.assertNotIn(self.txt_in_english, response.body)

	# test with 'other'
	def test_other(self):
		response = self.testapp.get('/', headers=self.hdr_other_accept)
		self.assertEqual(response.status_int, 200)
		self.assertIn(self.txt_in_english, response.body)
		self.assertNotIn(self.txt_in_german, response.body)

	# test with 'english', then request german
	def test_german_explicit(self):
		response = self.testapp.get('/', headers=self.hdr_english_accept)
		response = self.testapp.get('/locale/de_DE', headers=self.hdr_english_accept)
		self.assertEqual(response.status_int, 302)
		response = self.testapp.get('/', headers=self.hdr_english_accept)
		self.assertEqual(response.status_int, 200)
		self.assertIn(self.txt_in_german, response.body)
		self.assertNotIn(self.txt_in_english, response.body)

	# test with 'german', then request english
	def test_english_explicit(self):
		response = self.testapp.get('/', headers=self.hdr_german_accept)
		response = self.testapp.get('/locale/en_US', headers=self.hdr_german_accept)
		self.assertEqual(response.status_int, 302)
		response = self.testapp.get('/', headers=self.hdr_german_accept)
		self.assertEqual(response.status_int, 200)
		self.assertIn(self.txt_in_english, response.body)
		self.assertNotIn(self.txt_in_german, response.body)

########NEW FILE########
__FILENAME__ = test_model
import unittest2
import copy

from google.appengine.ext import testbed
from webapp2_extras import json

from core import model

class ModelTestCase(unittest2.TestCase):

	fixture_widget = json.decode('{"int_field":1,"email_field":"i@co.co","boolean_field":true,"date_field":"12-02-2012","text_field":"daf","id":2,"string_field":"dfa","link_field":"http://i.co"}')

	def setUp(self):
		# First, create an instance of the Testbed class.
		self.testbed = testbed.Testbed()

		# Then activate the testbed, which prepares the service stubs for use.
		self.testbed.activate()

		# Next, declare which service stubs you want to use.
		self.testbed.init_datastore_v3_stub()
		self.testbed.init_memcache_stub()

	def tearDown(self):
		self.testbed.deactivate()

	def test_create(self):
		widget = copy.copy(self.fixture_widget)
		model.Widget.put(widget)

		self.assertEqual(1, len(model.Widget.all().fetch(2)))

	def test_read(self):
		widget = copy.copy(self.fixture_widget)
		widget['int_field'] = 123

		entity = model.Widget.put(widget)
		
		self.assertNotEqual(None, entity)

		entity = model.Widget.get(entity.key().id())
		self.assertEqual(entity.int_field, 123)

	def test_update(self):
		widget = copy.copy(self.fixture_widget)
		identifier = model.Widget.put(widget).key().id()

		widget = copy.copy(self.fixture_widget)
		widget['int_field'] = 234
		widget['email_field'] = 'ibagrak@co.co'
		widget['boolean_field'] = False

		entity = model.Widget.post(identifier, widget)
		self.assertEqual(entity.int_field, 234)
		self.assertEqual(entity.email_field, 'ibagrak@co.co')
		self.assertEqual(entity.boolean_field, False)

	def test_delete(self):
		widget = copy.copy(self.fixture_widget)
		identifier = model.Widget.put(widget).key().id()

		self.assertEqual(model.Widget.delete1(identifier), True)

		self.assertEqual(0, len(model.Widget.all().fetch(2)))
		
########NEW FILE########
__FILENAME__ = utils
'''
Created on Aug 6, 2012

@author: ibagrak
'''
import datetime, re
import hashlib
import urllib
from google.appengine.ext import db

import settings

SIMPLE_TYPES = (int, long, float, bool, dict, basestring, list)

def to_dict(model):
    output = {}

    for key, prop in model.properties().iteritems():
        value = getattr(model, key)

        if value is None or isinstance(value, SIMPLE_TYPES):
            output[key] = value
        elif isinstance(value, datetime.date):
            # Convert date/datetime to ms-since-epoch ("new Date()").
            output[key] = value.strftime(settings.DATE_FORMAT)
            #ms = time.mktime(value.utctimetuple())
            #ms += getattr(value, 'microseconds', 0) / 1000
            #output[key] = int(ms)
        elif isinstance(value, db.GeoPt):
            output[key] = {'lat': value.lat, 'lon': value.lon}
        elif isinstance(value, db.Model):
            output[key] = to_dict(value)
        else:
            raise ValueError('cannot encode ' + repr(prop))

    output['id'] = model.key().id()
    return output

def to_gravatar_url(email): 
    return "http://www.gravatar.com/avatar/" + hashlib.md5(email).hexdigest() + "?d=" + urllib.quote(settings.HOME_URL + '/img/algae.png')

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE) # domain


########NEW FILE########
