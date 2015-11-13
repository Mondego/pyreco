__FILENAME__ = decorators
from pyramid.httpexceptions import HTTPFound
from apex import MessageFactory as _
from pyramid.security import authenticated_userid
from pyramid.url import route_url

from apex.lib.flash import flash

def login_required(wrapped):
    """ login_requred - Decorator to be used if you don't want to use
    permission='user'
    """
    def wrapper(request):
        result = wrapped(request)
        if not authenticated_userid(request):
            flash(_('Not logged in, please log in'), 'error')
            return HTTPFound(location=route_url('apex_login', request))
    return wrapper

########NEW FILE########
__FILENAME__ = exceptions
class MessageException(Exception):
    def __init__(self, message=None):
        Exception.__init__(self, message or self.message)

class ApexAuthSecret(MessageException):
    """ Exception called if there is no Auth Secret
    """
    message = 'Unable to find the apex.auth_secret setting, check your settings.'

class ApexSessionSecret(MessageException):
    """ Exception called if there is no Session Secret
    """
    message = 'Unable to find the apex.session_secret setting, check your settings.'

########NEW FILE########
__FILENAME__ = deform
import colander

@colander.deferred
def deferred_csrf_token(node, kw):
    """
    generate the value for the csrf token to be inserted into the form

    .. codeblock:: python

    # define form schema
    from apex.ext.deform import deferred_csrf_token

    class SubmitNewsSchema(MappingSchema):
        csrf_token = colander.SchemaNode(
        colander.String(),
            widget = deform.widget.HiddenWidget(),
            default = deferred_csrf_token,
        )

    # in your view, bind the token to the schema
    schema = SubmitNewsSchema(validator=SubmitNewsValidator).bind(csrf_token=request.session.get_csrf_token())

    """
    csrf_token = kw.get('csrf_token')
    return csrf_token

########NEW FILE########
__FILENAME__ = forms
import apex.lib.libapex

from wtforms import (HiddenField,
                     PasswordField,
                     TextField,
                     validators)

from apex import MessageFactory as _
from pyramid.security import authenticated_userid
from pyramid.threadlocal import (get_current_registry,
                                 get_current_request)

from apex.models import (AuthGroup,
                         AuthID,
                         AuthUser,
                         DBSession)
from apex.lib.form import ExtendedForm

class RegisterForm(ExtendedForm):
    """ Registration Form
    """
    login = TextField(_('Username'), [validators.Required(), \
                         validators.Length(min=4, max=25)])
    password = PasswordField(_('Password'), [validators.Required(), \
                             validators.EqualTo('password2', \
                             message=_('Passwords must match'))])
    password2 = PasswordField(_('Repeat Password'), [validators.Required()])
    email = TextField(_('Email Address'), [validators.Required(), \
                      validators.Email()])

    def validate_login(form, field):
        if AuthUser.get_by_login(field.data) is not None:
            raise validators.ValidationError(_('Sorry that username already exists.'))

    def create_user(self, login):
        group = self.request.registry.settings.get('apex.default_user_group',
                                                   None)
        user = apex.lib.libapex.create_user(username=login,
                                            password=self.data['password'],
                                            email=self.data['email'],
                                            group=group)
        return user

    def save(self):
        new_user = self.create_user(self.data['login'])
        self.after_signup(user=new_user)

        return new_user

    def after_signup(self, **kwargs):
        """ Function to be overloaded and called after form submission
        to allow you the ability to save additional form data or perform
        extra actions after the form submission.
        """
        pass

class ChangePasswordForm(ExtendedForm):
    """ Change Password Form
    """
    user_id = HiddenField('')
    old_password = PasswordField(_('Old Password'), [validators.Required()])
    password = PasswordField(_('New Password'), [validators.Required(), \
                             validators.EqualTo('password2', \
                             message=_('Passwords must match'))])
    password2 = PasswordField(_('Repeat New Password'), [validators.Required()])

    def validate_old_password(form, field):
        request = get_current_request()
        if not AuthUser.check_password(id=authenticated_userid(request), \
                                       password=field.data):
            raise validators.ValidationError(_('Your old password doesn\'t match'))

class LoginForm(ExtendedForm):
    login = TextField(_('Username'), validators=[validators.Required()])
    password = PasswordField(_('Password'), validators=[validators.Required()])

    def clean(self):
        errors = []
        if not AuthUser.check_password(login=self.data.get('login'), \
                                       password=self.data.get('password')):
            errors.append(_('Login Error -- please try again'))
        return errors

class ForgotForm(ExtendedForm):
    login = TextField(_('Username'), [validators.Optional()])
    label = HiddenField(label='Or')
    email = TextField(_('Email Address'), [validators.Optional(), \
                                           validators.Email()])
    label = HiddenField(label='')
    label = HiddenField(label=_('If your username and email weren\'t found, ' \
                              'you may have logged in with a login ' \
                              'provider and didn\'t set your email ' \
                              'address.'))

    """ I realize the potential issue here, someone could continuously
        hit the page to find valid username/email combinations and leak
        information, however, that is an enhancement that will be added
        at a later point.
    """
    def validate_login(form, field):
        if AuthUser.get_by_login(field.data) is None:
            raise validators.ValidationError(_('Sorry that username doesn\'t exist.'))

    def validate_email(form, field):
        if AuthUser.get_by_email(field.data) is None:
            raise validators.ValidationError(_('Sorry that email doesn\'t exist.'))

    def clean(self):
        errors = []
        if not self.data.get('login') and not self.data.get('email'):
            errors.append(_('You need to specify either a Username or ' \
                            'Email address'))
        return errors

class ResetPasswordForm(ExtendedForm):
    password = PasswordField(_('New Password'), [validators.Required(), \
                             validators.EqualTo('password2', \
                             message=_('Passwords must match'))])
    password2 = PasswordField(_('Repeat New Password'), [validators.Required()])

class AddAuthForm(ExtendedForm):
    login = TextField(_('Username'), [validators.Required(), \
                         validators.Length(min=4, max=25)])
    password = PasswordField(_('Password'), [validators.Required(), \
                             validators.EqualTo('password2', \
                             message=_('Passwords must match'))])
    password2 = PasswordField(_('Repeat Password'), [validators.Required()])
    email = TextField(_('Email Address'), [validators.Required(), \
                      validators.Email()])

    def validate_login(form, field):
        if AuthUser.get_by_login(field.data) is not None:
            raise validators.ValidationError(_('Sorry that username already exists.'))

    def create_user(self, auth_id, login):
        id = DBSession.query(AuthID).filter(AuthID.id==auth_id).one()
        user = AuthUser(
            login=login,
            password=self.data['password'],
            email=self.data['email'],
        )
        id.users.append(user)
        DBSession.add(user)
        DBSession.flush()

        return user

    def save(self, auth_id):
        new_user = self.create_user(auth_id, self.data['login'])
        self.after_signup(user=new_user)

    def after_signup(self, **kwargs):
        """ Function to be overloaded and called after form submission
        to allow you the ability to save additional form data or perform
        extra actions after the form submission.
        """
        pass

class OAuthForm(ExtendedForm):
    end_point = HiddenField('')
    csrf_token = HiddenField('')

class OpenIdLogin(OAuthForm):
    provider_name = 'openid'
    provider_proper_name = 'OpenID'

    openid_identifier = TextField(_('OpenID Identifier'), \
                                  [validators.Required()])

class GoogleLogin(OAuthForm):
    provider_name = 'google'
    provider_proper_name = 'Google'

class FacebookLogin(OAuthForm):
    provider_name = 'facebook'
    provider_proper_name = 'Facebook'
    scope = HiddenField('')

class YahooLogin(OAuthForm):
    provider_name = 'yahoo'
    provider_proper_name = 'Yahoo'

class TwitterLogin(OAuthForm):
    provider_name = 'twitter'
    provider_proper_name = 'Twitter'

class WindowsLiveLogin(OAuthForm):
    provider_name = 'live'
    provider_proper_name = 'Microsoft Live'

class BitbucketLogin(OAuthForm):
    provider_name = 'bitbucket'
    provider_proper_name = 'Bitbucket'

class GithubLogin(OAuthForm):
    provider_name = 'github'
    provider_proper_name = 'Github'

class IdenticaLogin(OAuthForm):
    provider_name = 'identica'
    provider_proper_name = 'Identi.ca'

class LastfmLogin(OAuthForm):
    provider_name = 'lastfm'
    provider_proper_name = 'Last.fm'

class LinkedinLogin(OAuthForm):
    provider_name = 'linkedin'
    provider_proper_name = 'LinkedIn'

class OpenIDRequiredForm(ExtendedForm):
    pass

########NEW FILE########
__FILENAME__ = i18n
from pyramid.i18n import TranslationStringFactory
MessageFactory = TranslationStringFactory("Apex")

########NEW FILE########
__FILENAME__ = interfaces
from zope.interface import implements
from zope.interface import Interface

class IApex(Interface):
    """ Class so that we can tell if Apex is installed from other 
    applications
    """
    pass

class ApexImplementation(object):
    """ Class so that we can tell if Apex is installed from other 
    applications
    """
    implements(IApex)

########NEW FILE########
__FILENAME__ = db
from pyramid.httpexceptions import HTTPNotFound
from pyramid.i18n import TranslationString as _

def get_or_create(session, model, **kw):
    """ Django's get_or_create function

http://stackoverflow.com/questions/2546207/does-sqlalchemy-have-an-equivalent-of-djangos-get-or-create
    """
    obj = session.query(model).filter_by(**kw).first()
    if obj:
        return obj
    else:
        obj = model(**kw)
        session.add(obj)
        session.flush()
        return obj

def get_object_or_404(session, model, **kw):
    """ Django's get_object_or_404 function
    """
    obj = session.query(model).filter_by(**kw).first()
    if obj is None:
        raise HTTPNotFound(detail=_('No %s matches the given query.') % model.__name__)
    return obj

def merge_session_with_post(session, post):
    """ Basic function to merge data into an sql object.
        This function doesn't work with relations.
    """
    for key, value in post:
        setattr(session, key, value)
    return session

########NEW FILE########
__FILENAME__ = fallbacks
# -*- coding: utf-8 -*-
import hashlib

from apex.lib.libapex import apex_settings

"""
This fallback routine attempts to check existing hashes that have failed
the bcrypt check against md5, hardcoded salt+md5, fieldbased salt+md5,
sha1, hardcoded salt+sha1, fieldbased salt+md5, and plaintext.

If any of the hash methods match, the user record is updated with the new
password. You can also write your own GenericFallback class to handle 
any other authentication scheme.

Options set in (development|production).ini:

apex.fallback_prefix_salt = salt to be prepended to password string
apex.fallback_salt_field = field in user table containing salt

"""

class GenericFallback(object):
    def check(self, DBSession, request, user, password):
        salted_passwd = user.password
        prefix_salt = apex_settings('fallback_prefix_salt', None)
        if prefix_salt:
            salted_passwd = '%s%s' % (prefix_salt, salted_passwd)
        salt_field = apex_settings('fallback_salt_field', None)
        if salt_field:
            prefix_salt = getattr(user, salt_field)
            salted_passwd = '%s%s' % (prefix_salt, salted_passwd)

        if salted_passwd is not None:
            if len(salted_passwd) == 32:
                # md5
                m = hashlib.md5()
                # password='····� breaks when type=unicode
                m.update(password)
                if m.hexdigest() == salted_passwd:
                    user.password = password
                    DBSession.merge(user)
                    DBSession.flush()
                    return True

            if len(salted_passwd) == 40:
                # sha1
                m = hashlib.sha1()
                m.update(password)
                if m.hexdigest() == salted_passwd:
                    user.password = password
                    DBSession.merge(user)
                    DBSession.flush()
                    return True

            if salted_passwd == password:
                # plaintext
                user.password = password
                DBSession.merge(user)
                DBSession.flush()
                return True

        return False

########NEW FILE########
__FILENAME__ = flash
from pyramid.threadlocal import get_current_request

class Flash(object):
    """ There are 4 default queues, warning, notice, error and success
    """

    queues = ['warning', 'error', 'success', 'notice']
    default_queue = 'notice'
        
    def __init__(self, queues=None, default_queue=None, allow_duplicate=True):
        self.allow_duplicate = allow_duplicate

        if queues is not None:
            self.queues = queues
        if default_queue is not None:
            self.default_queue = default_queue

    def __call__(self, msg, queue=default_queue):
        request = get_current_request()
        request.session.flash(msg, queue, self.allow_duplicate)

    def get_all(self):
        """ Returns all queued Flash Messages
        """
        request = get_current_request()
        messages = []
        for queue in self.queues:
            for peeked in request.session.peek_flash(queue):
                messages.append({'message': peeked, 'queue': queue,})
            request.session.pop_flash(queue)
        return messages

flash = Flash(allow_duplicate=False)

########NEW FILE########
__FILENAME__ = form
import cgi

from wtforms import Form
from wtforms import validators

from pyramid.i18n import get_localizer
from pyramid.renderers import render
from pyramid.threadlocal import get_current_request

from apex.lib.db import merge_session_with_post
from apex.lib.i18n import Translator

class ExtendedForm(Form):
    """ Base Model used to wrap WTForms for local use
    Global Validator, Renderer Function, determines whether
    it needs to be multipart based on file field present in form.

    http://groups.google.com/group/wtforms/msg/d6e5aca36a69ff5d
    """

    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        self.request = kwargs.pop('request', get_current_request())
        super(Form, self).__init__(self._unbound_fields, prefix=prefix)

        self.is_multipart = False

        for name, field in self._fields.iteritems():
            if field.type == 'FileField':
                self.is_multipart = True

            setattr(self, name, field)

        self.process(formdata, obj, **kwargs)

    def hidden_fields(self):
        """ Returns all the hidden fields.
        """
        return [self._fields[name] for name, field in self._unbound_fields
            if self._fields.has_key(name) and self._fields[name].type == 'HiddenField']

    def visible_fields(self):
        """ Returns all the visible fields.
        """
        return [self._fields[name] for name, field in self._unbound_fields
            if self._fields.has_key(name) and not self._fields[name].type == 'HiddenField']

    def _get_translations(self): 
        if self.request:
            localizer = get_localizer(self.request)
            return Translator(localizer)

    def clean(self): 
        """Override me to validate a whole form.""" 
        pass

    def validate(self): 
        if not super(ExtendedForm, self).validate(): 
            return False 
        errors = self.clean() 
        if errors: 
            self._errors = {'whole_form': errors} 
            return False 
        return True
        
    def render(self, **kwargs):
        action = kwargs.pop('action', '')
        submit_text = kwargs.pop('submit_text', 'Submit')
        template = kwargs.pop('template', False)

        if not template:
            settings = self.request.registry.settings

            template = settings.get('apex.form_template', \
                'apex:templates/forms/tableform.mako')

        return render(template, {
            'form': self,
            'action': action,
            'submit_text': submit_text,
            'args': kwargs,
        }, request=self.request)

class StyledWidget(object): 
    """ Allows a user to pass style to specific form field

    http://groups.google.com/group/wtforms/msg/6c7dd4dc7fee872d
    """
    def __init__(self, widget=None, **kwargs): 
        self.widget = widget
        self.kw = kwargs

    def __call__(self, field, **kwargs):
        if not self.widget:
            self.widget = field.__class__.widget

        return self.widget(field, **dict(self.kw, **kwargs)) 

class FileRequired(validators.Required): 
    """ 
    Required validator for file upload fields. 

    Bug mention for validating file field:
    http://groups.google.com/group/wtforms/msg/666254426eff1102
    """ 
    def __call__(self, form, field): 
        if not isinstance(field.data, cgi.FieldStorage): 
            if self.message is None: 
                self.message = field.gettext(u'This field is required.') 
            field.errors[:] = [] 
            raise validators.StopValidation(self.message)

class ModelForm(ExtendedForm):
    """ Simple form that adds a save method to forms for saving 
        forms that use WTForms' model_form function.
    """
    def save(self, session, model, commit=True):
        record = model()
        record = merge_session_with_post(record, self.data.items())
        if commit:
            session.add(record)
            session.flush()

        return record

########NEW FILE########
__FILENAME__ = i18n
class Translator(object):
    def __init__(self, localizer):
        self.t = localizer
    def gettext(self, string):
        return self.t.translate(string)
    def ngettext(self, single, plural, string):
        return self.t.pluralize(single, plural, string)

########NEW FILE########
__FILENAME__ = libapex
import requests
from sqlalchemy.orm.exc import NoResultFound

from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.security import (Allow,
                              Authenticated,
                              authenticated_userid,
                              Everyone,
                              remember)
from pyramid.settings import asbool
from pyramid.request import Request
from pyramid.threadlocal import get_current_registry
from pyramid.url import route_url
from pyramid.util import DottedNameResolver

from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from apex import MessageFactory as _
from apex.forms import (OpenIdLogin,
                        GoogleLogin,
                        FacebookLogin,
                        YahooLogin,
                        WindowsLiveLogin,
                        TwitterLogin,
                        BitbucketLogin,
                        GithubLogin,
                        LastfmLogin,
                        IdenticaLogin,
                        LinkedinLogin)
from apex.models import (AuthID,
                         AuthUser,
                         AuthGroup,
                         AuthUserLog,
                         DBSession)

class EmailMessageText(object):
    """ Default email message text class
    """

    def forgot(self):
        """
In the message body, %_url_% is replaced with:

::

    route_url('apex_reset', request, user_id=user_id, hmac=hmac))
        """
        return {
                'subject': _('Password reset request received'),
                'body': _("""
A request to reset your password has been received. Please go to
the following URL to change your password:

%_url_%

If you did not make this request, you can safely ignore it.
"""),
        }

    def activate(self):
        """
In the message body, %_url_% is replaced with:

::

    route_url('apex_activate', request, user_id=user_id, hmac=hmac))
        """
        return {
                'subject': _('Account activation. Please activate your account.'),
                'body': _("""
This site requires account validation. Please follow the link below to
activate your account:

%_url_%

If you did not make this request, you can safely ignore it.
"""),
        }

def apex_id_from_token(request):
    """ Returns the apex id from the OpenID Token
    """
    payload = {'format': 'json', 'token': request.POST['token']}
    velruse = requests.get(request.host_url + '/velruse/auth_info', \
        params=payload)
    if velruse.status_code == 200:
        try:
            auth = velruse.json()
        except:
            raise HTTPBadRequest(_('Velruse error while decoding json'))
        if 'profile' in auth:
            auth['id'] = auth['profile']['accounts'][0]['userid']
            auth['provider'] = auth['profile']['accounts'][0]['domain']
            return auth
        return None
    else:
        raise HTTPBadRequest(_('Velruse backing store unavailable'))

def groupfinder(userid, request):
    """ Returns ACL formatted list of groups for the userid in the
    current request
    """
    auth = AuthID.get_by_id(userid)
    if auth:
        return [('group:%s' % group.name) for group in auth.groups]

class RootFactory(object):
    """ Defines the default ACLs, groups populated from SQLAlchemy.
    """
    def __init__(self, request):
        if request.matchdict:
            self.__dict__.update(request.matchdict)

    @property
    def __acl__(self):
        dbsession = DBSession()
        groups = dbsession.query(AuthGroup.name).all()
        defaultlist = [ (Allow, Everyone, 'view'),
                (Allow, Authenticated, 'authenticated'),]
        for g in groups:
            defaultlist.append( (Allow, 'group:%s' % g, g[0]) )
        return defaultlist

provider_forms = {
    'openid': OpenIdLogin,
    'google': GoogleLogin,
    'twitter': TwitterLogin,
    'yahoo': YahooLogin,
    'live': WindowsLiveLogin,
    'facebook': FacebookLogin,
    'bitbucket': BitbucketLogin,
    'github': GithubLogin,
    'identica': IdenticaLogin,
    'lastfm': LastfmLogin,
    'linkedin': LinkedinLogin,
}

def apex_email(request, recipients, subject, body, sender=None):
    """ Sends email message
    """
    mailer = get_mailer(request)
    if not sender:
        sender = apex_settings('sender_email')
        if not sender:
            sender = 'nobody@example.com'
    message = Message(subject=subject,
                      sender=sender,
                      recipients=[recipients],
                      body=body)
    mailer.send(message)

    report_recipients = apex_settings('email_report_recipients')
    if not report_recipients:
        return

    report_recipients = [s.strip() for s in report_recipients.split(',')]

    # since the config options are interpreted (not raw)
    # the report_subject variable is not easily customizable.
    report_subject = "Registration activity for '%(recipients)s' : %(subject)s"

    report_prefix = apex_settings('email_report_prefix')
    if report_prefix:
        report_subject = report_prefix + ' ' + report_subject

    d = { 'recipients': recipients, 'subject': subject }
    report_subject = report_subject % d

    body = "The following registration-related activity occurred: \r\n" + \
        "--------------------------------------------\r\n" + body

    message = Message(subject=report_subject,
                      sender=sender,
                      recipients=report_recipients,
                      body=body)
    mailer.send(message)

def apex_email_forgot(request, user_id, email, hmac):
    message_class_name = get_module(apex_settings('email_message_text', \
                             'apex.lib.libapex.EmailMessageText'))
    message_class = message_class_name()
    message_text = getattr(message_class, 'forgot')()

    message_body = message_text['body'].replace('%_url_%', \
        route_url('apex_reset', request, user_id=user_id, hmac=hmac))

    apex_email(request, email, message_text['subject'], message_body)

def apex_email_activate(request, user_id, email, hmac):
    message_class_name = get_module(apex_settings('email_message_text', \
                             'apex.lib.libapex.EmailMessageText'))
    message_class = message_class_name()
    message_text = getattr(message_class, 'activate')()

    message_body = message_text['body'].replace('%_url_%', \
        route_url('apex_activate', request, user_id=user_id, hmac=hmac))

    apex_email(request, email, message_text['subject'], message_body)

def apex_id_providers(auth_id):
    """ return a list of the providers that are currently active for 
        this auth_id
    """
    return [x[0] for x in DBSession.query(AuthUser.provider). \
        filter(AuthUser.auth_id==auth_id).all()]

def apex_settings(key=None, default=None):
    """ Gets an apex setting if the key is set.
        If no key it set, returns all the apex settings.

        Some settings have issue with a Nonetype value error,
        you can set the default to fix this issue.
    """
    settings = get_current_registry().settings

    if key:
        return settings.get('apex.%s' % key, default)
    else:
        apex_settings = []
        for k, v in settings.items():
            if k.startswith('apex.'):
                apex_settings.append({k.split('.')[1]: v})

        return apex_settings

def create_user(**kwargs):
    """

::

    from apex.lib.libapex import create_user

    create_user(username='test', password='my_password', active='Y')

    Optional Parameters:

    display_name
    group



    Returns: AuthID object
    """
    auth_id = AuthID(active=kwargs.get('active', 'Y'))
    if 'display_name' in kwargs:
        auth_id.display_name = kwargs['display_name']
        del kwargs['display_name']

    user = AuthUser(login=kwargs['username'], password=kwargs['password'], \
               active=kwargs.get('active', 'Y'))
    auth_id.users.append(user)

    if 'group' in kwargs:
        try:
            group = DBSession.query(AuthGroup). \
            filter(AuthGroup.name==kwargs['group']).one()

            auth_id.groups.append(group)
        except NoResultFound:
            pass

        del kwargs['group']

    for key, value in kwargs.items():
        setattr(user, key, value)

    DBSession.add(auth_id)
    DBSession.add(user)
    DBSession.flush()
    return user

def generate_velruse_forms(request, came_from, exclude=set([])):
    """ Generates variable form based on OpenID providers
    """
    velruse_forms = []
    providers = apex_settings('velruse_providers', None)
    if providers:
        providers = list(set([x.strip() for x in providers.split(',')]) - \
            exclude)
        for provider in providers:
            if provider_forms.has_key(provider):
                form = provider_forms[provider](
                    end_point='%s?csrf_token=%s&came_from=%s' % \
                     (request.route_url('apex_callback'), \
                      request.session.get_csrf_token(),
                      came_from), \
                     csrf_token = request.session.get_csrf_token(),
                )
                velruse_forms.append(form)
    return velruse_forms

def get_module(package):
    """ Returns a module based on the string passed
    """
    resolver = DottedNameResolver(package.split('.', 1)[0])
    return resolver.resolve(package)

def apex_remember(request, user, max_age=None):
    if asbool(apex_settings('log_logins')):
        if apex_settings('log_login_header'):
            ip_addr = request.environ.get(apex_settings('log_login_header'), \
                    u'invalid value - apex.log_login_header')
        else:
             ip_addr = unicode(request.environ['REMOTE_ADDR'])
        record = AuthUserLog(auth_id=user.auth_id, user_id=user.id, \
            ip_addr=ip_addr)
        DBSession.add(record)
        DBSession.flush()
    return remember(request, user.auth_id, max_age=max_age)

def get_came_from(request):
    return request.GET.get('came_from',
                           request.POST.get(
                               'came_from',
                               route_url(apex_settings('came_from_route'), \
                               request))
                          )

class RequestFactory(Request):
    """ Custom Request factory, that adds the user context
        to request.

        http://docs.pylonsproject.org/projects/pyramid_cookbook/dev/authentication.html
    """
    @reify
    def user(self):
        user = None
        if authenticated_userid(self):
            user = AuthID.get_by_id(authenticated_userid(self))
        return user

########NEW FILE########
__FILENAME__ = subscribers
import logging

from pyramid.httpexceptions import HTTPForbidden
from pyramid.threadlocal import get_current_request
from pyramid.threadlocal import get_current_registry
from pyramid.renderers import get_renderer

from apex.lib.flash import flash
from apex.lib.libapex import apex_settings

from apex.i18n import MessageFactory as _

log = logging.getLogger('apex.lib.subscribers')

def csrf_validation(event):
    """ CSRF token validation Subscriber

        As of Pyramid 1.2a3, passing messages through HTTPForbidden broke,
        and don't appear to be exposed to exception handlers.

        It appears that we cannot decorate a view and have it affect an event
        until after the event has fired, so, temporarily we're going to
        have to use a value in the config to specify a list of paths that
        should not have CSRF validation.

        Ideally, we'll be able to do

        ::
            @no_csrf
            @view_config(route_name='test')
            def test(request):

        which would prevent CSRF tracking on that view. With the event hooks,
        our decorator is not read until AFTER the event, which makes this
        method fail at this point.

        Temporarily, we'll use a field in the development.ini:

        apex.no_csrf = routename1:routename2

        Disabled apex CSRF (20121118) - CSRF token not being passed 
        through new Velruse

    """
    if event.request.method == 'POST':
        # will never hit GET
        token = event.request.POST.get('csrf_token') \
            or event.request.GET.get('csrf_token') \
            or event.request.json_body.get('csrf_token') \
            or event.request.headers.get('X-CSRF-Token')
                                    
        no_csrf = apex_settings('no_csrf', '').split(',')
        if (token is None or token != event.request.session.get_csrf_token()):
            if event.request.matched_route and \
                event.request.matched_route.name not in no_csrf \
                and not event.request.matched_route.name.startswith('debugtoolbar.') \
                and not event.request.matched_route.name.startswith('apex_'):
                    log.debug('apex: CSRF token received %s didn\'t match %s' % \
                        (token, event.request.session.get_csrf_token()))
                    raise HTTPForbidden(_('CSRF token is missing or invalid'))

def add_renderer_globals(event):
    """ add globals to templates

    csrf_token - bare token
    csrf_token_field - hidden input field with token inserted
    flash - flash messages
    """

    request = event.get('request')
    settings = get_current_registry().settings
    template = settings['apex.apex_render_template']

    if request is None:
        request = get_current_request()

    csrf_token = request.session.get_csrf_token()

    globs = {
        'csrf_token': csrf_token,
        'csrf_token_field': '<input type="hidden" name="csrf_token" value="%s" />' % csrf_token,
        'flash': flash,
    }


    if template.endswith('.pt'):
        globs['flash_t'] = get_renderer('apex:templates/flash_template.pt').implementation()
    event.update(globs)

########NEW FILE########
__FILENAME__ = models
import hashlib
import random
import string
import transaction

from cryptacular.bcrypt import BCRYPTPasswordManager

from pyramid.threadlocal import get_current_request
from pyramid.util import DottedNameResolver

from sqlalchemy import (Column,
                        ForeignKey,
                        Index,
                        Table,
                        types,
                        Unicode)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (relationship,
                            scoped_session,
                            sessionmaker,
                            synonym)
from sqlalchemy.sql.expression import func

from zope.sqlalchemy import ZopeTransactionExtension 

from apex.lib.db import get_or_create

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

auth_group_table = Table('auth_auth_groups', Base.metadata,
    Column('auth_id', types.Integer(), \
        ForeignKey('auth_id.id', onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', types.Integer(), \
        ForeignKey('auth_groups.id', onupdate='CASCADE', ondelete='CASCADE'))
)
# need to create Unique index on (auth_id,group_id)
Index('auth_group', auth_group_table.c.auth_id, auth_group_table.c.group_id)

class AuthGroup(Base):
    """ Table name: auth_groups
    
::

    id = Column(types.Integer(), primary_key=True)
    name = Column(Unicode(80), unique=True, nullable=False)
    description = Column(Unicode(255), default=u'')
    """
    __tablename__ = 'auth_groups'
    __table_args__ = {'sqlite_autoincrement': True}
    
    id = Column(types.Integer(), primary_key=True)
    name = Column(Unicode(80), unique=True, nullable=False)
    description = Column(Unicode(255), default=u'')

    users = relationship('AuthID', secondary=auth_group_table, \
                     backref='auth_groups')

    def __repr__(self):
        return u'%s' % self.name

    def __unicode__(self):
        return self.name
    

class AuthID(Base):
    """ Table name: auth_id

::

    id = Column(types.Integer(), primary_key=True)
    display_name = Column(Unicode(80), default=u'')
    active = Column(types.Enum(u'Y',u'N',u'D', name=u'active'), default=u'Y')
    created = Column(types.DateTime(), default=func.now())

    """

    __tablename__ = 'auth_id'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(types.Integer(), primary_key=True)
    display_name = Column(Unicode(80), default=u'')
    active = Column(types.Enum(u'Y',u'N',u'D', name=u'active'), default=u'Y')
    created = Column(types.DateTime(), default=func.now())

    groups = relationship('AuthGroup', secondary=auth_group_table, \
                      backref='auth_users')

    users = relationship('AuthUser')

    """
    Fix this to use association_proxy
    groups = association_proxy('auth_group_table', 'authgroup')
    """

    last_login = relationship('AuthUserLog', \
                         order_by='AuthUserLog.id.desc()', uselist=False)
    login_log = relationship('AuthUserLog', \
                         order_by='AuthUserLog.id')

    def in_group(self, group):
        """
        Returns True or False if the user is or isn't in the group.
        """
        return group in [g.name for g in self.groups]

    @classmethod
    def get_by_id(cls, id):
        """ 
        Returns AuthID object or None by id

        .. code-block:: python

           from apex.models import AuthID

           user = AuthID.get_by_id(1)
        """
        return DBSession.query(cls).filter(cls.id==id).first()    

    def get_profile(self, request=None):
        """
        Returns AuthUser.profile object, creates record if it doesn't exist.

        .. code-block:: python

           from apex.models import AuthUser

           user = AuthUser.get_by_id(1)
           profile = user.get_profile(request)

        in **development.ini**

        .. code-block:: python

           apex.auth_profile = 
        """
        if not request:
            request = get_current_request()

        auth_profile = request.registry.settings.get('apex.auth_profile')
        if auth_profile:
            resolver = DottedNameResolver(auth_profile.split('.')[0])
            profile_cls = resolver.resolve(auth_profile)
            return get_or_create(DBSession, profile_cls, auth_id=self.id)

    @property
    def group_list(self):
        group_list = []
        if self.groups:
            for group in self.groups:
                group_list.append(group.name)
        return ','.join( map( str, group_list ) )

class AuthUser(Base):
    """ Table name: auth_users

::

    id = Column(types.Integer(), primary_key=True)
    login = Column(Unicode(80), default=u'', index=True)
    _password = Column('password', Unicode(80), default=u'')
    email = Column(Unicode(80), default=u'', index=True)
    active = Column(types.Enum(u'Y',u'N',u'D'), default=u'Y')
    """
    __tablename__ = 'auth_users'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(types.Integer(), primary_key=True)
    auth_id = Column(types.Integer, ForeignKey(AuthID.id), index=True)
    provider = Column(Unicode(80), default=u'local', index=True)
    login = Column(Unicode(80), default=u'', index=True)
    salt = Column(Unicode(24))
    _password = Column('password', Unicode(80), default=u'')
    email = Column(Unicode(80), default=u'', index=True)
    created = Column(types.DateTime(), default=func.now())
    active = Column(types.Enum(u'Y',u'N',u'D', name=u'active'), default=u'Y')

    # need unique index on auth_id, provider, login
    # create unique index ilp on auth_users (auth_id,login,provider);
    # how do we handle same auth on multiple ids?

    def _set_password(self, password):
        self.salt = self.get_salt(24)
        password = password + self.salt
        self._password = BCRYPTPasswordManager().encode(password, rounds=12)

    def _get_password(self):
        return self._password

    password = synonym('_password', descriptor=property(_get_password, \
                       _set_password))

    def get_salt(self, length):
        m = hashlib.sha256()
        word = ''

        for i in xrange(length):
            word += random.choice(string.ascii_letters)

        m.update(word)

        return unicode(m.hexdigest()[:length])

    @classmethod
    def get_by_id(cls, id):
        """ 
        Returns AuthUser object or None by id

        .. code-block:: python

           from apex.models import AuthID

           user = AuthID.get_by_id(1)
        """
        return DBSession.query(cls).filter(cls.id==id).first()    

    @classmethod
    def get_by_login(cls, login):
        """ 
        Returns AuthUser object or None by login

        .. code-block:: python

           from apex.models import AuthUser

           user = AuthUser.get_by_login('login')
        """
        return DBSession.query(cls).filter(cls.login==login).first()

    @classmethod
    def get_by_email(cls, email):
        """ 
        Returns AuthUser object or None by email

        .. code-block:: python

           from apex.models import AuthUser

           user = AuthUser.get_by_email('email@address.com')
        """
        return DBSession.query(cls).filter(cls.email==email).first()

    @classmethod
    def check_password(cls, **kwargs):
        if kwargs.has_key('id'):
            user = cls.get_by_id(kwargs['id'])
        if kwargs.has_key('login'):
            user = cls.get_by_login(kwargs['login'])

        if not user:
            return False
        try:
            if BCRYPTPasswordManager().check(user.password,
                '%s%s' % (kwargs['password'], user.salt)):
                return True
        except TypeError:
            pass

        request = get_current_request()
        fallback_auth = request.registry.settings.get('apex.fallback_auth')
        if fallback_auth:
            resolver = DottedNameResolver(fallback_auth.split('.', 1)[0])
            fallback = resolver.resolve(fallback_auth)
            return fallback().check(DBSession, request, user, \
                       kwargs['password'])

        return False

class AuthUserLog(Base):
    """
    event: 
      L - Login
      R - Register
      P - Password
      F - Forgot
    """
    __tablename__ = 'auth_user_log'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(types.Integer, primary_key=True)
    auth_id = Column(types.Integer, ForeignKey(AuthID.id), index=True)
    user_id = Column(types.Integer, ForeignKey(AuthUser.id), index=True)
    time = Column(types.DateTime(), default=func.now())
    ip_addr = Column(Unicode(39), nullable=False)
    event = Column(types.Enum(u'L',u'R',u'P',u'F', name=u'event'), default=u'L')

def populate(settings):
    session = DBSession()

    default_groups = []
    if settings.has_key('apex.default_groups'):
        for name in settings['apex.default_groups'].split(','):
            default_groups.append((unicode(name.strip()),u''))
    else:
        default_groups = [(u'users',u'User Group'), \
                          (u'admin',u'Admin Group')]
    for name, description in default_groups:
        group = AuthGroup(name=name, description=description)
        session.add(group)

    session.flush()
    transaction.commit()

def initialize_sql(engine, settings):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    if settings.has_key('apex.velruse_providers'):
        pass
        #SQLBase.metadata.bind = engine
        #SQLBase.metadata.create_all(engine)
    try:
        populate(settings)
    except IntegrityError:
        transaction.abort()

########NEW FILE########
__FILENAME__ = models
import transaction

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class MyModel(Base):
    __tablename__ = 'models'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), unique=True)
    value = Column(Integer)

    def __init__(self, name, value):
        self.name = name
        self.value = value

def populate():
    session = DBSession()
    model = MyModel(name='root', value=55)
    session.add(model)
    session.flush()
    transaction.commit()

def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    try:
        populate()
    except IntegrityError:
        transaction.abort()

########NEW FILE########
__FILENAME__ = test_lib_libapex
import unittest

from pyramid import testing
from apex.tests import BaseTestCase


class Test_lib_libapex(BaseTestCase):
    def test_apex_id_from_token(self):
        # apex_id_from_token(request)
        pass

    def test_groupfinder(self):
        # groupfinder(userid, request)
        from apex.lib.libapex import (create_user,
                                      groupfinder)

        user = create_user(username='libtest', password='password', \
            group='users')
        self.assertEqual([u'group:users'], groupfinder(user.auth_id, None))
        self.assertNotEqual(None, groupfinder(user.auth_id, None))
        self.assertEqual(None, groupfinder(18, None))
        self.assertNotEqual([u'group:users'], groupfinder(18, None))

    def test_apex_email(self):
        # apex_email(request, recipients, subject, body, sender=None)
        pass

    def test_apex_email_forgot(self):
        # apex_email_forgot(request, user_id, email, hmac)
        pass

    def test_apex_email_activate(self):
        # apex_email_activate(request, user_id, email, hmac)
        pass

    def test_apex_settings(self):
        # apex_settings(key=None, default=None)
        # settings not being set in registry
        from apex.lib.libapex import apex_settings

        """
        self.assertEqual([], apex_settings(key=None, default=None))
        depends on registry which isn't being passed

        self.assertEqual('session_secret', \
            apex_settings(key='session_secret', default=None))
        self.assertEqual('home', apex_settings(key='came_from_route', \
            default=None))
        self.assertEqual(None, apex_settings(key='no_match', default=None))
        """

    def test_create_user(self):
        # create_user(**kwargs)
        from apex.lib.libapex import create_user
        from apex.models import (AuthUser,
                                 DBSession)

        create_user(username='libtest', password='password')
        # check that auth_id, auth_user, auth_group are added
        self.assertEqual('libtest', DBSession.query(AuthUser.login). \
            filter(AuthUser.login=='libtest').one()[0])

    def test_generate_velruse_forms(self):
        # generate_velruse_forms(request, came_from)
        pass

    def test_get_module(self):
        # get_module(package)
        pass

    def test_apex_remember(self):
        # apex_remember(request, user, max_age=None)
        pass

    def test_get_came_from(self):
        # get_came_from(request)
        pass

########NEW FILE########
__FILENAME__ = test_views
import os
import webob.multidict
import apex.views

from pyramid import testing
from apex.tests import BaseTestCase
from apex.lib.libapex import create_user

here = os.path.abspath(os.path.dirname(__file__))

""" added to provide dummy environment to prevent exception when
hostname isn't defined.
"""
environ = {
    'HTTP_HOST': 'test.com',
    'SERVER_NAME': 'test.com',
    'REMOTE_ADDR': '127.0.0.1',
}


class Test_views(BaseTestCase):
    def test_view_login(self):
        create_user(username='test', password='password')

        request = testing.DummyRequest()

        # wtforms requires this
        request.POST = webob.multidict.MultiDict()
        request.context = testing.DummyResource()
        response = apex.views.login(request)

        self.assertEqual(response['title'], 'You need to login')

    def test_login(self):
        create_user(username='test', password='password')

        request = testing.DummyRequest(environ=environ)
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        request.POST['login'] = 'test'
        request.POST['password'] = 'password'
        request.context = testing.DummyResource()
        response = apex.views.login(request)
        self.assertEqual(response.status, "302 Found")

    def test_fail_login(self):
        create_user(username='test', password='password1')

        request = testing.DummyRequest(environ=environ)
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        request.POST['login'] = 'test'
        request.POST['password'] = 'password'
        request.context = testing.DummyResource()
        response = apex.views.login(request)
        self.assertEqual(len(response['form'].errors), 1)

    def test_logout(self):
        """ need to import environ for SERVER_NAME and HOST_NAME
        since we're dealing with cookies.
        """
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        response = apex.views.logout(request)

        self.assertEqual('302 Found', response.status)

    def test_change_password_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        # no user
        self.assertRaises(AttributeError, apex.views.change_password, request)

    def test_change_password(self):
        pass

    def test_forgot_password_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        response = apex.views.forgot_password(request)
        self.assertEqual(len(response['form'].errors), 1)

    def test_forgot_password(self):
        pass

    def test_reset_password_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        response = apex.views.reset_password(request)
        self.assertEqual(len(response['form'].errors), 2)

    def test_reset_password(self):
        pass

    def test_activate_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        response = apex.views.reset_password(request)
        self.assertEqual(len(response['form'].errors), 2)

    def test_activate(self):
        pass

    def test_register_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        response = apex.views.register(request)
        self.assertEqual(len(response['form'].errors), 4)

    def test_register(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        request.POST['login'] = 'test'
        request.POST['password'] = 'password'
        request.POST['password2'] = 'password'
        request.POST['email'] = 'mau@wau.de'
        response = apex.views.register(request)
        self.assertEqual(response.status, "302 Found")

    def test_add_auth_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        response = apex.views.add_auth(request)
        self.assertEqual(len(response['form'].errors), 4)

    def test_add_auth(self):
        pass

    def test_apex_callback_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        request.POST['token'] = 'test'
        response = apex.views.apex_callback(request)
        self.assertEqual(response.status, "302 Found")

    def test_apex_callback(self):
        pass

    def test_openid_required_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        self.assertRaises(AttributeError, apex.views.openid_required, request)

    def test_openid_required(self):
        pass

    def test_forbidden(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.matched_route = None
        response = apex.views.forbidden(request)
        # TODO return something != 200 OK
        self.assertEqual(response.status, "200 OK")

    def test_edit_fail(self):
        request = testing.DummyRequest(environ=environ)
        request.context = testing.DummyResource()
        request.method = 'POST'
        request.POST = webob.multidict.MultiDict()
        self.assertRaises(AttributeError, apex.views.edit, request)

    def test_edit(self):
        pass

########NEW FILE########
__FILENAME__ = views
import base64
import hmac
import time

from wtforms import (TextField,
                     validators)
from wtforms.ext.sqlalchemy.orm import model_form

from wtfrecaptcha.fields import RecaptchaField

from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.security import (authenticated_userid,
                              forget)
from pyramid.settings import asbool
from pyramid.url import (current_route_url,
                         route_url)

from apex import MessageFactory as _
from apex.lib.db import merge_session_with_post
from apex.lib.libapex import (apex_email_forgot,
                              apex_id_from_token,
                              apex_id_providers,
                              apex_remember,
                              apex_settings,
                              generate_velruse_forms,
                              get_came_from,
                              get_module)
from apex.lib.flash import flash
from apex.lib.form import ExtendedForm
from apex.models import (AuthGroup,
                         AuthID,
                         AuthUser,
                         DBSession)
from apex.forms import (ChangePasswordForm,
                        ForgotForm,
                        ResetPasswordForm)


def login(request):
    """ login(request)
    No return value

    Function called from route_url('apex_login', request)
    """
    title = _('You need to login')
    came_from = get_came_from(request)

    if apex_settings('login_form_class'):
        LoginForm = get_module(apex_settings('login_form_class'))
    else:
        from apex.forms import LoginForm

    if not apex_settings('exclude_local'):
        if asbool(apex_settings('use_recaptcha_on_login')):
            if apex_settings('recaptcha_public_key') and \
                apex_settings('recaptcha_private_key'):
                LoginForm.captcha = RecaptchaField(
                    public_key=apex_settings('recaptcha_public_key'),
                    private_key=apex_settings('recaptcha_private_key'),
                )
            form = LoginForm(request.POST,
                             captcha={'ip_address': \
                             request.environ['REMOTE_ADDR']})
        else:
            form = LoginForm(request.POST)
    else:
        form = None

    velruse_forms = generate_velruse_forms(request, came_from)

    if request.method == 'POST' and form.validate():
        user = AuthUser.get_by_login(form.data.get('login'))
        if user:
            headers = apex_remember(request, user, \
                max_age=apex_settings('max_cookie_age', None))
            return HTTPFound(location=came_from, headers=headers)

    return {'title': title, 'form': form, 'velruse_forms': velruse_forms, \
            'form_url': request.route_url('apex_login'),
            'action': 'login'}

def logout(request):
    """ logout(request):
    no return value, called with route_url('apex_logout', request)
    """
    headers = forget(request)
    came_from = get_came_from(request)
    request.session.invalidate()
    return HTTPFound(location=came_from, headers=headers)

def change_password(request):
    """ change_password(request):
        no return value, called with route_url('apex_change_password', request)
        FIXME doesn't adjust auth_user based on local ID, how do we handle
        multiple IDs that are local? Do we tell person that they don't have
        local permissions?
    """
    title = _('Change your Password')

    came_from = get_came_from(request)
    user = DBSession.query(AuthUser). \
               filter(AuthUser.auth_id==authenticated_userid(request)). \
               filter(AuthUser.provider=='local').first()
    form = ChangePasswordForm(request.POST, user_id=user.id)

    if request.method == 'POST' and form.validate():
        #user = AuthID.get_by_id(authenticated_userid(request))
        user.password = form.data['password']
        DBSession.merge(user)
        DBSession.flush()
        return HTTPFound(location=came_from)

    return {'title': title, 'form': form, 'action': 'changepass'}

def forgot_password(request):
    """ forgot_password(request):
    no return value, called with route_url('apex_forgot_password', request)
    """
    title = _('Forgot my password')

    if asbool(apex_settings('use_recaptcha_on_forgot')):
        if apex_settings('recaptcha_public_key') and \
            apex_settings('recaptcha_private_key'):
            ForgotForm.captcha = RecaptchaField(
                public_key=apex_settings('recaptcha_public_key'),
                private_key=apex_settings('recaptcha_private_key'),
            )
    form = ForgotForm(request.POST, \
               captcha={'ip_address': request.environ['REMOTE_ADDR']})
    if request.method == 'POST' and form.validate():
        """ Special condition - if email imported from OpenID/Auth, we can
            direct the person to the appropriate login through a flash
            message.
        """
        if form.data['email']:
            user = AuthUser.get_by_email(form.data['email'])
            if user.provider != 'local':
                provider_name = user.provider
                flash(_('You used %s as your login provider' % \
                     provider_name))
                return HTTPFound(location=route_url('apex_login', \
                                          request))
        if form.data['login']:
            user = AuthUser.get_by_login(form.data['login'])
        if user:
            timestamp = time.time()+3600
            hmac_key = hmac.new('%s:%s:%d' % (str(user.id), \
                                apex_settings('auth_secret'), timestamp), \
                                user.email).hexdigest()[0:10]
            time_key = base64.urlsafe_b64encode('%d' % timestamp)
            email_hash = '%s%s' % (hmac_key, time_key)
            apex_email_forgot(request, user.id, user.email, email_hash)
            flash(_('Password Reset email sent.'))
            return HTTPFound(location=route_url('apex_login', \
                                                request))
        flash(_('An error occurred, please contact the support team.'))
    return {'title': title, 'form': form, 'action': 'forgot'}

def reset_password(request):
    """ reset_password(request):
    no return value, called with route_url('apex_reset_password', request)
    """
    title = _('Reset My Password')

    if asbool(apex_settings('use_recaptcha_on_reset')):
        if apex_settings('recaptcha_public_key') and \
            apex_settings('recaptcha_private_key'):
            ResetPasswordForm.captcha = RecaptchaField(
                public_key=apex_settings('recaptcha_public_key'),
                private_key=apex_settings('recaptcha_private_key'),
            )
    form = ResetPasswordForm(request.POST, \
               captcha={'ip_address': request.environ['REMOTE_ADDR']})
    if request.method == 'POST' and form.validate():
        user_id = request.matchdict.get('user_id')
        user = AuthUser.get_by_id(user_id)
        submitted_hmac = request.matchdict.get('hmac')
        current_time = time.time()
        time_key = int(base64.b64decode(submitted_hmac[10:]))
        if current_time < time_key:
            hmac_key = hmac.new('%s:%s:%d' % (str(user.id), \
                                apex_settings('auth_secret'), time_key), \
                                user.email).hexdigest()[0:10]
            if hmac_key == submitted_hmac[0:10]:
                #FIXME reset email, no such attribute email
                user.password = form.data['password']
                DBSession.merge(user)
                DBSession.flush()
                flash(_('Password Changed. Please log in.'))
                return HTTPFound(location=route_url('apex_login', \
                                                    request))
            else:
                flash(_('Invalid request, please try again'))
                return HTTPFound(location=route_url('apex_forgot', \
                                                    request))
    return {'title': title, 'form': form, 'action': 'reset'}

def activate(request):
    """
    """
    user_id = request.matchdict.get('user_id')
    user = AuthID.get_by_id(user_id)
    submitted_hmac = request.matchdict.get('hmac')
    current_time = time.time()
    time_key = int(base64.b64decode(submitted_hmac[10:]))
    if current_time < time_key:
        hmac_key = hmac.new('%s:%s:%d' % (str(user.id), \
                            apex_settings('auth_secret'), time_key), \
                            user.email).hexdigest()[0:10]
        if hmac_key == submitted_hmac[0:10]:
            user.active = 'Y'
            DBSession.merge(user)
            DBSession.flush()
            flash(_('Account activated. Please log in.'))
            return HTTPFound(location=route_url('apex_login', \
                                                request))
    flash(_('Invalid request, please try again'))
    return HTTPFound(location=route_url(apex_settings('came_from_route'), \
                                        request))

def register(request):
    """ register(request):
    no return value, called with route_url('apex_register', request)
    """
    title = _('Register')
    came_from = request.params.get('came_from', \
                    route_url(apex_settings('came_from_route'), request))
    velruse_forms = generate_velruse_forms(request, came_from)

    #This fixes the issue with RegisterForm throwing an UnboundLocalError
    if apex_settings('register_form_class'):
        RegisterForm = get_module(apex_settings('register_form_class'))
    else:
        from apex.forms import RegisterForm

    if not apex_settings('exclude_local'):
        if asbool(apex_settings('use_recaptcha_on_register')):
            if apex_settings('recaptcha_public_key') and \
                apex_settings('recaptcha_private_key'):
                RegisterForm.captcha = RecaptchaField(
                    public_key=apex_settings('recaptcha_public_key'),
                    private_key=apex_settings('recaptcha_private_key'),
                )

        form = RegisterForm(request.POST, captcha={'ip_address': \
            request.environ['REMOTE_ADDR']})
    else:
        form = None

    if request.method == 'POST' and form.validate():
        user = form.save()

        headers = apex_remember(request, user)
        return HTTPFound(location=came_from, headers=headers)

    return {'title': title, 'form': form, 'velruse_forms': velruse_forms, \
            'action': 'register'}

def add_auth(request):
    title = _('Add another Authentication method')
    came_from = request.params.get('came_from', \
                    route_url(apex_settings('came_from_route'), request))
    auth_id = authenticated_userid(request)
    request.session['id'] = auth_id
    auth_providers = apex_id_providers(auth_id)
    exclude = set([])
    if not apex_settings('allow_duplicate_providers'):
        exclude = set([x.split('.')[0] for x in auth_providers])

    velruse_forms = generate_velruse_forms(request, came_from, exclude)

    #This fixes the issue with RegisterForm throwing an UnboundLocalError
    if apex_settings('auth_form_class'):
        AddAuthForm = get_module(apex_settings('auth_form_class'))
    else:
        from apex.forms import AddAuthForm

    form = None
    if not apex_settings('exclude_local') and 'local' not in exclude:
        if not asbool(apex_settings('use_recaptcha_on_auth')):
            if apex_settings('recaptcha_public_key') and \
                apex_settings('recaptcha_private_key'):
                AddAuthForm.captcha = RecaptchaField(
                    public_key=apex_settings('recaptcha_public_key'),
                    private_key=apex_settings('recaptcha_private_key'),
                )

        form = AddAuthForm(request.POST, captcha={'ip_address': \
            request.environ['REMOTE_ADDR']})

    if request.method == 'POST' and form.validate():
        form.save(auth_id)

        return HTTPFound(location=came_from)

    return {'title': title, 'form': form, 'velruse_forms': velruse_forms, \
            'action': 'add_auth'}

def apex_callback(request):
    """ apex_callback(request):
    no return value, called with route_url('apex_callback', request)

    This is the URL that Velruse returns an OpenID request to
    """
    redir = request.GET.get('came_from', \
                route_url(apex_settings('came_from_route'), request))
    headers = []
    if 'token' in request.POST:
        auth = None
        try:
            auth = apex_id_from_token(request)
        except:
            # TODO add logging
            pass
        if auth:
            user = None
            if not request.session.has_key('id'):
                user = AuthUser.get_by_login(auth['id'])
            if not user:
                id = None
                if request.session.has_key('id'):
                    id = AuthID.get_by_id(request.session['id'])
                else:
                    id = AuthID()
                    DBSession.add(id)
                auth_info = auth['profile']['accounts'][0]
                user = AuthUser(
                    login=auth_info['userid'],
                    provider=auth_info['domain'],
                )
                if auth['profile'].has_key('verifiedEmail'):
                    user.email = auth['profile']['verifiedEmail']
                id.users.append(user)
                if apex_settings('default_user_group'):
                    for name in apex_settings('default_user_group'). \
                                              split(','):
                        group = DBSession.query(AuthGroup). \
                           filter(AuthGroup.name==name.strip()).one()
                        id.groups.append(group)
                if apex_settings('create_openid_after'):
                    openid_after = get_module(apex_settings('create_openid_after'))
                    openid_after().after_signup(request=request, user=user)
                DBSession.flush()
            if apex_settings('openid_required'):
                openid_required = False
                for required in apex_settings('openid_required').split(','):
                    if not getattr(user, required):
                        openid_required = True
                if openid_required:
                    request.session['id'] = id.id
                    request.session['userid'] = user.id
                    return HTTPFound(location='%s?came_from=%s' % \
                        (route_url('apex_openid_required', request), \
                        request.GET.get('came_from', \
                        route_url(apex_settings('came_from_route'), request))))
            headers = apex_remember(request, user)
            redir = request.GET.get('came_from', \
                        route_url(apex_settings('came_from_route'), request))
            flash(_('Successfully Logged in, welcome!'), 'success')
    return HTTPFound(location=redir, headers=headers)

def openid_required(request):
    """ openid_required(request)
    no return value

    If apex_settings.openid_required is set, and the ax/sx from the OpenID
    auth doesn't return the required fields, this is called which builds
    a dynamic form to ask for the missing inforation.

    Called on Registration or Login with OpenID Authentication.
    """
    title = _('OpenID Registration')
    came_from = request.params.get('came_from', \
                    route_url(apex_settings('came_from_route'), request))

    #This fixes the issue with RegisterForm throwing an UnboundLocalError
    if apex_settings('openid_register_form_class'):
        OpenIDRequiredForm = get_module(apex_settings('openid_register_form_class'))
    else:
        from apex.forms import OpenIDRequiredForm

    for required in apex_settings('openid_required').split(','):
        setattr(OpenIDRequiredForm, required, \
            TextField(required, [validators.Required()]))

    form = OpenIDRequiredForm(request.POST, \
               captcha={'ip_address': request.environ['REMOTE_ADDR']})

    if request.method == 'POST' and form.validate():
        """
            need to have the AuthUser id that corresponds to the login
            method.
        """
        user = AuthUser.get_by_id(request.session['userid'])
        for required in apex_settings('openid_required').split(','):
            setattr(user, required, form.data[required])
        DBSession.merge(user)
        DBSession.flush()
        headers = apex_remember(request, user)
        return HTTPFound(location=came_from, headers=headers)

    return {'title': title, 'form': form, 'action': 'openid_required'}

def forbidden(request):
    """ forbidden(request)
    No return value

    Called when user hits a resource that requires a permission and the
    user doesn't have the required permission. Will prompt for login.

    request.environ['repoze.bfg.message'] contains our forbidden error in case
    of a csrf problem. Proper solution is probably an error page that
    can be customized.

    bfg.routes.route and repoze.bfg.message are scheduled to be deprecated,
    however, corresponding objects are not present in the request to be able
    to determine why the Forbidden exception was called.

    **THIS WILL BREAK EVENTUALLY**
    **THIS DID BREAK WITH Pyramid 1.2a3**
    """
    if request.matched_route:
        flash(_('Not logged in, please log in'), 'error')
        return HTTPFound(location='%s?came_from=%s' %
                        (route_url('apex_login', request),
                        current_route_url(request)))
    else:
        return Response('Unknown error message')

def edit(request):
    """ edit(request)
        no return value, called with route_url('apex_edit', request)

        This function will only work if you have set apex.auth_profile.

        This is a very simple edit function it works off your auth_profile
        class, all columns inside your auth_profile class will be rendered.
    """
    title = _('Edit')

    ProfileForm = model_form(
        model=get_module(apex_settings('auth_profile')),
        base_class=ExtendedForm,
        exclude=('id', 'user_id'),
    )

    record = AuthUser.get_profile(request)
    form = ProfileForm(obj=record)
    if request.method == 'POST' and form.validate():
        record = merge_session_with_post(record, request.POST.items())
        DBSession.merge(record)
        DBSession.flush()
        flash(_('Profile Updated'))
        return HTTPFound(location=request.url)

    return {'title': title, 'form': form, 'action': 'edit'}

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Apex documentation build configuration file, created by
# sphinx-quickstart on Sat Aug 20 16:29:13 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Apex'
copyright = u'2011, Chris Davies, Matthew Housden'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.9'
# The full version, including alpha/beta/rc tags.
release = '0.9.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Apexdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Apex.tex', u'Apex Documentation',
   u'Chris Davies, Matthew Housden', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'apex', u'Apex Documentation',
     [u'Chris Davies, Matthew Housden'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Unicode

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension

from apex.models import AuthUser
""" To Extend the User Model, make sure you import AuthUser in your
model.py
"""

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class ExtendedProfile(AuthUser):
    __mapper_args__ = {'polymorphic_identity': 'profile'}
    
    first_name = Column(Unicode(80))
    last_name = Column(Unicode(80))
    

class ForeignKeyProfile(Base):
    """ We're extending AuthUser by adding a Foreign Key to Profile. 
    Make sure you set index=True on user_id.
    """
    __tablename__ = 'auth_user_profile'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(AuthUser.id), index=True)
    user = relationship(AuthUser, backref=backref('profile', uselist=False))

    """ Everything below this point can be customized. In your templates, 
    you can access the user object through the request context as 

    **request.user** or **request.user.profile.firstname**
    """
    first_name = Column(Unicode(80))
    last_name = Column(Unicode(80))

def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)

########NEW FILE########
__FILENAME__ = views
from pyramid.view import view_config

@view_config(route_name='home', renderer='index.mako')
def index(request):
    return {}

@view_config(route_name='test', renderer='test.mako')
def test(request):
    return {}

@view_config(route_name='protected', renderer='protected.mako',
             permission='authenticated')
def protected(request):
    return {}

@view_config(route_name='groupusers', renderer='groupusers.mako',
             permission='users')
def groupusers(request):
    return {}

########NEW FILE########
