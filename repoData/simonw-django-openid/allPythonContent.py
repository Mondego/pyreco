__FILENAME__ = admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered

from models import UserOpenidAssociation

class OpenIDInline(admin.StackedInline):
    model = UserOpenidAssociation

class UserAdminWithOpenIDs(UserAdmin):
    inlines = [OpenIDInline]

# Add OpenIDs to the user admin, but only if User has been registered
try:
    admin.site.unregister(User)
    admin.site.register(User, UserAdminWithOpenIDs)
except NotRegistered:
    pass

#from models import Nonce, Association
#admin.site.register(Nonce)
#admin.site.register(Association)

########NEW FILE########
__FILENAME__ = auth
from django.http import HttpResponseRedirect as Redirect, Http404
from django_openid import consumer, signed
from django_openid.utils import hex_to_int, int_to_hex
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail

import hashlib, datetime
from urlparse import urljoin

# TODO: prevent multiple associations of same OpenID

class AuthConsumer(consumer.SessionConsumer):
    """
    An OpenID consumer endpoint that integrates with Django's auth system.
    Uses SessionConsumer rather than CookieConsumer because the auth system
    relies on sessions already.
    """
    after_login_redirect_url = '/'
    
    associations_template = 'django_openid/associations.html'
    login_plus_password_template = 'django_openid/login_plus_password.html'
    recover_template = 'django_openid/recover.html'
    already_logged_in_template = 'django_openid/already_logged_in.html'
    pick_account_template = 'django_openid/pick_account.html'
    show_associate_template = 'django_openid/associate.html'
    recovery_email_template = 'django_openid/recovery_email.txt'
    recovery_expired_template = 'django_openid/recovery_expired.html'
    recovery_complete_template = 'django_openid/recovery_complete.html'
    
    recovery_email_from = None
    recovery_email_subject = 'Recover your account'
    
    password_logins_enabled = True
    account_recovery_enabled = True
    
    need_authenticated_user_message = 'You need to sign in with an ' \
        'existing user account to access this page.'
    csrf_failed_message = 'Invalid submission'
    associate_tampering_message = 'Invalid submission'
    association_deleted_message = '%s has been deleted'
    openid_now_associated_message = \
        'The OpenID "%s" is now associated with your account.'
    bad_password_message = 'Incorrect username or password'
    invalid_token_message = 'Invalid token'
    recovery_email_sent_message = 'Check your mail for further instructions'
    recovery_not_found_message = 'No matching user was found'
    recovery_multiple_found_message = 'Try entering your username instead'
    r_user_not_found_message = 'That user account does not exist'
    
    account_recovery_url = None
    
    associate_salt = 'associate-salt'
    associate_delete_salt = 'associate-delete-salt'
    recovery_link_salt = 'recovery-link-salt'
    recovery_link_secret = None # If None, uses settings.SECRET_KEY
    
    # For generating recovery URLs
    recovery_origin_date = datetime.date(2000, 1, 1)
    recovery_expires_after_days = 3 # Number of days recovery URL is valid for
    
    def show_login(self, request, extra_message=None):
        if request.user.is_authenticated():
            return self.show_already_logged_in(request)
        
        response = super(AuthConsumer, self).show_login(
            request, extra_message
        )
        
        if self.password_logins_enabled:
            response.template_name = self.login_plus_password_template
            response.template_context.update({
                'account_recovery': self.account_recovery_enabled and (
                    self.account_recovery_url or (request.path + 'recover/')
                ),
            })
        return response
    
    def show_already_logged_in(self, request):
        return self.render(request, self.already_logged_in_template) 
    
    def do_login(self, request, extra_message=None):
        if request.method == 'POST' and \
                request.POST.get('username', '').strip():
            # Do a username/password login instead
            user = authenticate(
                username = request.POST.get('username'),
                password = request.POST.get('password')
            )
            if not user:
                return self.show_login(request, self.bad_password_message)
            else:
                self.log_in_user(request, user)
                return self.on_login_complete(request, user, openid=None)
        else:
            return super(AuthConsumer, self).do_login(request, extra_message)
    
    def lookup_openid(self, request, identity_url):
        # Imports lives inside this method so User won't get imported if you 
        # over-ride this in your own sub-class and use something else.
        from django.contrib.auth.models import User
        return list(
            User.objects.filter(openids__openid = identity_url).distinct()
        )
    
    def log_in_user(self, request, user):
        # Remember, openid might be None (after registration with none set)
        from django.contrib.auth import login
        # Nasty but necessary - annotate user and pretend it was the regular 
        # auth backend. This is needed so django.contrib.auth.get_user works:
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
    
    def on_login_complete(self, request, user, openid=None):
        response = self.redirect_if_valid_next(request)
        if not response:
            response = Redirect(self.after_login_redirect_url)
        return response
    
    def on_logged_in(self, request, openid, openid_response):
        # Do we recognise their OpenID?
        matches = self.lookup_openid(request, openid)
        # Are they logged in already?
        if request.user.is_authenticated():
            # Did we find their account already? If so, ignore login
            if request.user.id in [u.id for u in matches]:
                response = self.redirect_if_valid_next(request)
                if not response:
                    response = Redirect(self.after_login_redirect_url)
                return response
            else:
                # Offer to associate this OpenID with their account
                return self.show_associate(request, openid)
        if matches:
            # If there's only one match, log them in as that user
            if len(matches) == 1:
                user = matches[0]
                if self.user_can_login(request, user):
                    self.log_in_user(request, user)
                    return self.on_login_complete(request, user, openid)
                else:
                    # User is not allowed to log in for some other reason - 
                    # for example, they have not yet validated their e-mail 
                    # or they have been banned from the site.
                    return self.show_you_cannot_login(request, user, openid)
            # Otherwise, let them to pick which account they want to log in as
            else:
                return self.show_pick_account(request, openid)
        else:
            # We don't know anything about this openid
            return self.show_unknown_openid(request, openid)
    
    def user_can_login(self, request, user):
        "Over-ride for things like user bans or account e-mail validation"
        return user.is_active
    
    def show_pick_account(self, request, openid):
        """
        The user's OpenID is associated with more than one account - ask them
        which one they would like to sign in as
        """
        return self.render(request, self.pick_account_template, {
            'action': urljoin(request.path, '../pick/'),
            'openid': openid,
            'users': self.lookup_openid(request, openid),
        })
    
    def do_pick(self, request):
        # User MUST be logged in with an OpenID and it MUST be associated
        # with the selected account. The error messages in here are a bit 
        # weird, unfortunately.
        if not request.openid:
            return self.show_error(request, 'You should be logged in here')
        users = self.lookup_openid(request, request.openid.openid)
        try:
            user_id = [
                v.split('-')[1] for v in request.POST if v.startswith('user-')
            ][0]
            user = [u for u in users if str(u.id) == user_id][0]
        except IndexError, e:
            return self.show_error(request, "You didn't pick a valid user")
        # OK, log them in
        self.log_in_user(request, user)
        return self.on_login_complete(request, user, request.openid.openid)
    
    def on_logged_out(self, request):
        # After logging out the OpenID, log out the user auth session too
        from django.contrib.auth import logout
        response = super(AuthConsumer, self).on_logged_out(request)
        logout(request)
        return response
    
    def show_unknown_openid(self, request, openid):
        # This can be over-ridden to show a registration form
        return self.show_message(
            request, 'Unknown OpenID', '%s is an unknown OpenID' % openid
        )
    
    def show_you_cannot_login(self, request, user, openid):
        return self.show_message(
            request, 'You cannot log in',
            'You cannot log in with that account'
        )
    
    def show_associate(self, request, openid=None):
        "Screen that offers to associate an OpenID with a user's account"
        if not request.user.is_authenticated():
            return self.need_authenticated_user(request)
        return self.render(request, self.show_associate_template, {
            'action': urljoin(request.path, '../associate/'),
            'user': request.user,
            'specific_openid': openid,
            'openid_token': signed.dumps(
               # Use user.id as part of extra_key to prevent attackers from
               # creating their own openid_token for use in CSRF attack
               openid, extra_key = self.associate_salt + str(request.user.id)
            ),
        })
    
    def do_associate(self, request):
        if request.method == 'POST':
            try:
                openid = signed.loads(
                    request.POST.get('openid_token', ''),
                    extra_key = self.associate_salt + str(request.user.id)
                )
            except signed.BadSignature:
                return self.show_error(request, self.csrf_failed_message)
            # Associate openid with their account, if it isn't already
            if not request.user.openids.filter(openid = openid):
                request.user.openids.create(openid = openid)
            return self.show_associate_done(request, openid)
            
        return self.show_error(request, 'Should POST to here')
    
    def show_associate_done(self, request, openid):
        response = self.redirect_if_valid_next(request)
        if not response:
            response = self.show_message(request, 'Associated', 
                self.openid_now_associated_message % openid
            )
        return response
    
    def need_authenticated_user(self, request):
        return self.show_error(request, self.need_authenticated_user_message)
    
    def do_associations(self, request):
        "Interface for managing your account's associated OpenIDs"
        if not request.user.is_authenticated():
            return self.need_authenticated_user(request)
        message = None
        if request.method == 'POST':
            if 'todelete' in request.POST:
                # Something needs deleting; find out what
                try:
                    todelete = signed.loads(
                        request.POST['todelete'],
                        extra_key = self.associate_delete_salt
                    )
                    if todelete['user_id'] != request.user.id:
                        message = self.associate_tampering_message
                    else:
                        # It matches! Delete the OpenID relationship
                        request.user.openids.filter(
                            pk = todelete['association_id']
                        ).delete()
                        message = self.association_deleted_message % (
                            todelete['openid']
                        )
                except signed.BadSignature:
                    message = self.associate_tampering_message
        # We construct a button to delete each existing association
        openids = []
        for association in request.user.openids.all():
            openids.append({
                'openid': association.openid,
                'button': signed.dumps({
                    'user_id': request.user.id,
                    'association_id': association.id,
                    'openid': association.openid,
                }, extra_key = self.associate_delete_salt),
            })
        return self.render(request, self.associations_template, {
            'openids': openids,
            'user': request.user,
            'action': request.path,
            'message': message,
            'action_new': '../',
            'associate_next': self.sign_next(request.path),
        })
    
    def do_recover(self, request, extra_message = None):
        if request.method == 'POST':
            submitted = request.POST.get('recover', '').strip()
            user = None
            if '@' not in submitted: # They entered a username
                user = self.lookup_user_by_username(submitted)
            else: # They entered an e-mail address
                users = self.lookup_users_by_email(submitted)
                if users:
                    if len(users) > 1:
                        extra_message = self.recovery_multiple_found_message
                        user = None
                    else:
                        user = users[0]
            if user:
                self.send_recovery_email(request, user)
                return self.show_message(
                    request, 'E-mail sent', self.recovery_email_sent_message
                )
            else:
                extra_message = self.recovery_not_found_message
        return self.render(request, self.recover_template, {
            'action': request.path,
            'message': extra_message,
        })
    
    def lookup_users_by_email(self, email):
        from django.contrib.auth.models import User
        return list(User.objects.filter(email = email))
    
    def lookup_user_by_username(self, username):
        from django.contrib.auth.models import User
        try:
            return User.objects.get(username = username)
        except User.DoesNotExist:
            return None
    
    def lookup_user_by_id(self, id):
        from django.contrib.auth.models import User
        try:
            return User.objects.get(pk = id)
        except User.DoesNotExist:
            return None
    
    def do_r(self, request, token = ''):
        if not token:
            # TODO: show a form where they can paste in their token?
            raise Http404
        token = token.rstrip('/').encode('utf8')
        try:
            value = signed.unsign(token, key = (
                self.recovery_link_secret or settings.SECRET_KEY
            ) + self.recovery_link_salt)
        except signed.BadSignature:
            return self.show_message(
                request, self.invalid_token_message,
                self.invalid_token_message + ': ' + token
            )
        hex_days, hex_user_id = (value.split('.') + ['', ''])[:2]
        days = hex_to_int(hex_days)
        user_id = hex_to_int(hex_user_id)
        user = self.lookup_user_by_id(user_id)
        if not user: # Maybe the user was deleted?
            return self.show_error(request, r_user_not_found_message)
        
        # Has the token expired?
        now_days = (datetime.date.today() - self.recovery_origin_date).days
        if (now_days - days) > self.recovery_expires_after_days:
            return self.render(request, self.recovery_expired_template, {
                'days': self.recovery_expires_after_days,
                'recover_url': urljoin(request.path, '../../recover/'),
            })
        
        # Token is valid! Log them in as that user and show the recovery page
        self.log_in_user(request, user)
        return self.render(request, self.recovery_complete_template, {
            'change_password_url': urljoin(request.path, '../../password/'),
            'associate_url': urljoin(request.path, '../../associations/'),
            'user': user,
        })
    do_r.urlregex = '^r/([^/]+)/$'
    
    def generate_recovery_code(self, user):
        # Code is {hex-days}.{hex-userid}.{signature}
        days = int_to_hex(
            (datetime.date.today() - self.recovery_origin_date).days
        )
        token = '%s.%s' % (days, int_to_hex(user.id))
        return signed.sign(token, key = (
            self.recovery_link_secret or settings.SECRET_KEY
        ) + self.recovery_link_salt)
    
    def send_recovery_email(self, request, user):
        code = self.generate_recovery_code(user)
        path = urljoin(request.path, '../r/%s/' % code)
        url = request.build_absolute_uri(path)
        email_body = self.render(request, self.recovery_email_template, {
            'url': url,
            'code': code,
            'theuser': user,
        }).content
        send_mail(
            subject = self.recovery_email_subject,
            message = email_body,
            from_email = self.recovery_email_from or \
                settings.DEFAULT_FROM_EMAIL,
            recipient_list = [user.email]
        )

# Monkey-patch to add openid login form to the Django admin
def make_display_login_form_with_openid(bind_to_me, openid_path):
    "openid_path is the path the OpenID login should submit to, e.g. /openid/"
    from django.contrib.admin.sites import AdminSite
    def display_login_form(request, error_message='', 
            extra_context=None):
        extra_context = extra_context or {}
        extra_context['openid_path'] = openid_path
        return AdminSite.display_login_form(
            bind_to_me, request, error_message, extra_context
        )
    return display_login_form

def monkeypatch_adminsite(admin_site, openid_path = '/openid/'):
    admin_site.display_login_form = make_display_login_form_with_openid(
        admin_site, openid_path
    )


########NEW FILE########
__FILENAME__ = consumer
"""
Consumer is a class-based generic view which handles all aspects of consuming
and providing OpenID. User applications should define subclasses of this, 
then hook those up directly to the urlconf.

from myapp import MyConsumerSubclass

urlpatterns = patterns('',
    ('r^openid/(.*)', MyConsumerSubclass()),
    ...
)
"""
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from openid.consumer import consumer
from openid.consumer.discover import DiscoveryFailure
from openid.yadis import xri
from django_openid.models import DjangoOpenIDStore
from django_openid.utils import OpenID, Router
from django_openid import signed
from django_openid.response import TemplateResponse

class SessionPersist(object):
    def get_user_session(self, request):
        return request.session
    
    def set_user_session(self, request, response, user_session):
        pass

class CookiePersist(object):
    """
    Use this if you are avoiding Django's session support entirely.
    """
    cookie_user_session_key = 'o_user_session'
    cookie_user_session_path = '/'
    cookie_user_session_domain = None
    cookie_user_session_secure = None
    
    def get_user_session(self, request):
        try:
            user_session = signed.loads(
                request.COOKIES.get(self.cookie_user_session_key, '')
            )
        except ValueError:
            user_session = {}
        return user_session
    
    def set_user_session(self, request, response, user_session):
        if user_session:
            response.set_cookie(
                key = self.cookie_user_session_key,
                value = signed.dumps(user_session, compress = True),
                path = self.cookie_user_session_path,
                domain = self.cookie_user_session_domain,
                secure = self.cookie_user_session_secure,
            )
        else:
            response.delete_cookie(
                key = self.cookie_user_session_key,
                path = self.cookie_user_session_path,
                domain = self.cookie_user_session_domain,
            )

class Consumer(object):
    """
    This endpoint can take a user through the most basic OpenID flow, starting
    with an "enter your OpenID" form, dealing with the redirect to the user's 
    provider and calling self.on_success(...) once they've successfully 
    authenticated. You should subclass this and provide your own on_success 
    method, or use CookieConsumer or SessionConsumer if you just want to 
    persist their OpenID in some way.
    """
    # Default templates
    base_template = 'django_openid/base.html'
    login_template = 'django_openid/login.html'
    error_template = 'django_openid/error.html'
    message_template = 'django_openid/message.html'
    
    # Extension args; most of the time you'll just need the sreg shortcuts
    extension_args = {}
    extension_namespaces = {
        'sreg': 'http://openid.net/sreg/1.0',
    }
    
    # Simple registration. Possible fields are:
    # nickname,email,fullname,dob,gender,postcode,country,language,timezone
    sreg = sreg_optional = [] # sreg is alias for sreg_optional
    sreg_required = [] # Recommend NOT using this; use sreg instead
    sreg_policy_url = None
    
    # Default messages
    openid_required_message = 'Enter an OpenID'
    xri_disabled_message = 'i-names are not supported'
    openid_invalid_message = 'The OpenID was invalid'
    request_cancelled_message = 'The request was cancelled'
    failure_message = 'Failure: %s'
    setup_needed_message = 'Setup needed'
    
    sign_next_param = True # Set to False to disable signed ?next= URLs
    salt_next = 'salt-next-token' # Adds extra saltiness to the ?next= salt
    xri_enabled = False
    on_complete_url = None
    trust_root = None # If None, full URL to endpoint is used
    logo_path = None # Path to the OpenID logo, as used by the login view
    
    OPENID_LOGO_BASE_64 = """
R0lGODlhEAAQAMQAAO3t7eHh4srKyvz8/P5pDP9rENLS0v/28P/17tXV1dHEvPDw8M3Nzfn5+d3d
3f5jA97Syvnv6MfLzcfHx/1mCPx4Kc/S1Pf189C+tP+xgv/k1N3OxfHy9NLV1/39/f///yH5BAAA
AAAALAAAAAAQABAAAAVq4CeOZGme6KhlSDoexdO6H0IUR+otwUYRkMDCUwIYJhLFTyGZJACAwQcg
EAQ4kVuEE2AIGAOPQQAQwXCfS8KQGAwMjIYIUSi03B7iJ+AcnmclHg4TAh0QDzIpCw4WGBUZeikD
Fzk0lpcjIQA7""".strip()
    
    urlname_pattern = 'openid-%s'
    
    def __init__(self, persist_class=CookiePersist):
        self.persist = persist_class()
    
    def sign_next(self, url):
        if self.sign_next_param:
            return signed.dumps(url, extra_key = self.salt_next)
        else:
            return url
    
    def render(self, request, template, context=None):
        context = context or {}
        context['base_template'] = self.base_template
        return TemplateResponse(request, template, context)
    
    def get_urlpatterns(self):
        # Default behaviour is to introspect self for do_* methods
        from django.conf.urls.defaults import url 
        urlpatterns = []
        for method in dir(self):
            if method.startswith('do_'):
                callback = getattr(self, method)
                name = method.replace('do_', '')
                urlname = self.urlname_pattern % name
                urlregex = getattr(callback, 'urlregex', '^%s/$' % name)
                urlpatterns.append(
                    url(urlregex, callback, name=urlname)
                )
        return urlpatterns
    
    def get_urls(self):
        # In Django 1.1 and later you can hook this in to your urlconf
        from django.conf.urls.defaults import patterns
        return patterns('', *self.get_urlpatterns())
    
    def urls(self):
        return self.get_urls()
    urls = property(urls)
    
    def __call__(self, request, rest_of_url=''):
        if not request.path.endswith('/'):
            return HttpResponseRedirect(request.path + '/')
        router = Router(*self.get_urlpatterns())
        return router(request, path_override = rest_of_url)

    def do_index(self, request, extra_message=None):
        return self.do_login(request, extra_message)
    do_index.urlregex = '^$'
    
    def show_login(self, request, message=None):
        if self.sign_next_param:
            try:
                next = signed.loads(
                    request.REQUEST.get('next', ''), extra_key=self.salt_next
                )
            except ValueError:
                next = ''
        else:
            next = request.REQUEST.get('next', '')
        return self.render(request, self.login_template, {
            'action': request.path,
            'logo': self.logo_path or (request.path + 'logo/'),
            'message': message,
            'next': next and request.REQUEST.get('next', '') or None,
        })
    
    def show_error(self, request, message, exception=None):
        return self.render(request, self.error_template, {
            'message': message,
            'exception': exception,
        })
    
    def show_message(self, request, title, message):
        return self.render(request, self.message_template, {
            'title': title,
            'message': message,
        })
    
    def get_consumer(self, request, session_store):
        return consumer.Consumer(session_store, DjangoOpenIDStore())
    
    def add_extension_args(self, request, auth_request):
        # Add extension args (for things like simple registration)
        extension_args = dict(self.extension_args) # Create a copy
        if self.sreg:
            extension_args['sreg.optional'] = ','.join(self.sreg)
        if self.sreg_required:
            extension_args['sreg.required'] = ','.join(self.sreg_required)
        if self.sreg_policy_url:
            extension_args['sreg.policy_url'] = self.sreg_policy_url
        
        for name, value in extension_args.items():
            namespace, key = name.split('.', 1)
            namespace = self.extension_namespaces.get(namespace, namespace)
            auth_request.addExtensionArg(namespace, key, value)
    
    def get_on_complete_url(self, request, on_complete_url=None):
        "Derives an appropriate on_complete_url from the request"
        on_complete_url = on_complete_url or self.on_complete_url or \
            (request.path + 'complete/')
        on_complete_url = self.ensure_absolute_url(request, on_complete_url)
        return on_complete_url
        
        if self.sign_next_param:
            try:
                next = signed.loads(
                    request.POST.get('next', ''), extra_key=self.salt_next
                )
            except ValueError:
                return on_complete_url
        else:
            next = request.POST.get('next', '')
        if '?' not in on_complete_url:
            on_complete_url += '?next=' + next
        else:
            on_complete_url += '&next=' + next
        return on_complete_url
    
    def get_trust_root(self, request, trust_root=None):
        "Derives an appropriate trust_root from the request"
        trust_root = trust_root or self.trust_root or \
            request.build_absolute_uri()
        return self.ensure_absolute_url(
            request, trust_root
        )
    
    def do_login(self, request, extra_message=None):
        if request.method == 'GET':
            return self.show_login(request, extra_message)
        
        user_url = request.POST.get('openid_url', None)
        if not user_url:
            return self.show_login(request, self.openid_required_message)
        
        return self.start_openid_process(request, user_url)
    
    def is_xri(self, user_url):
        return xri.identifierScheme(user_url) == 'XRI'
    
    def start_openid_process(
            self, request, user_url, on_complete_url=None, trust_root=None
        ):
        if self.is_xri(user_url) and not self.xri_enabled:
            return self.show_login(request, self.xri_disabled_message)
        
        user_session = self.persist.get_user_session(request)
        
        try:
            auth_request = self.get_consumer(
                request, user_session
            ).begin(user_url)
        except DiscoveryFailure, e:
            return self.show_error(request, self.openid_invalid_message, e)
        
        self.add_extension_args(request, auth_request)
        
        trust_root = self.get_trust_root(request, trust_root)
        on_complete_url = self.get_on_complete_url(request, on_complete_url)
        
        redirect_url = auth_request.redirectURL(trust_root, on_complete_url)
        response = HttpResponseRedirect(redirect_url)
        self.persist.set_user_session(request, response, user_session)
        return response
        
    def dispatch_openid_complete(self, request, handlers):
        user_session = self.persist.get_user_session(request)
        
        openid_response = self.get_consumer(
            request, user_session
        ).complete(
            dict(request.GET.items()),
            request.build_absolute_uri().split('?')[0] # to verify return_to
        )
        if openid_response.status == consumer.SUCCESS:
            response = handlers[consumer.SUCCESS](
                request, openid_response.identity_url, openid_response
            )
        else:
            response = handlers[openid_response.status](
                request, openid_response
            )
        
        self.persist.set_user_session(request, response, user_session)
        
        return response
    
    def do_complete(self, request):
        return self.dispatch_openid_complete(request, {
            consumer.SUCCESS: self.on_success,
            consumer.CANCEL: self.on_cancel,
            consumer.FAILURE: self.on_failure,
            consumer.SETUP_NEEDED: self.on_setup_needed
        })
    
    def do_debug(self, request):
        from django.conf import settings
        if not settings.DEBUG:
            raise Http404
        assert False, 'debug!'
    
    def redirect_if_valid_next(self, request):
        "Logic for checking if a signed ?next= token is included in request"
        if self.sign_next_param:
            try:
                next = signed.loads(
                    request.REQUEST.get('next', ''), extra_key=self.salt_next
                )
                return HttpResponseRedirect(next)
            except ValueError:
                return None
        else:
            next = request.REQUEST.get('next', '')
            if next.startswith('/'):
                return HttpResponseRedirect(next)
            else:
                return None
    
    def on_success(self, request, identity_url, openid_response):
        response = self.redirect_if_valid_next(request)
        if not response:
            response = self.show_message(
                request, 'Logged in', "You logged in as %s" % identity_url
            )
        return response
    
    def on_cancel(self, request, openid_response):
        return self.show_error(request, self.request_cancelled_message)
    
    def on_failure(self, request, openid_response):
        return self.show_error(
            request, self.failure_message % openid_response.message
        )
    
    def on_setup_needed(self, request, openid_response):
        return self.show_error(request, self.setup_needed_message)
    
    def do_logo(self, request):
        return HttpResponse(
            self.OPENID_LOGO_BASE_64.decode('base64'), mimetype='image/gif'
        )
    
    def ensure_absolute_url(self, request, url):
        if not (url.startswith('http://') or url.startswith('https://')):
            url = request.build_absolute_uri(url)
        return url

class LoginConsumer(Consumer):
    redirect_after_login = '/'
    redirect_after_logout = '/'
    
    def persist_openid(self, request, response, openid_object):
        assert False, 'LoginConsumer must be subclassed before use'
    
    def on_success(self, request, identity_url, openid_response):
        openid_object = OpenID.from_openid_response(openid_response)
        response = self.on_logged_in(request, identity_url, openid_response)
        self.persist_openid(request, response, openid_object)
        return response
    
    def on_logged_in(self, request, identity_url, openid_response):
        response = self.redirect_if_valid_next(request)
        if not response:
            response = HttpResponseRedirect(self.redirect_after_login)
        return response
    
    def on_logged_out(self, request):
        response = self.redirect_if_valid_next(request)
        if not response:
            response = HttpResponseRedirect(self.redirect_after_logout)
        return response
    
class SessionConsumer(LoginConsumer):
    """
    When the user logs in, save their OpenID in the session. This can handle 
    multiple OpenIDs being signed in at the same time.
    """
    session_key = 'openids'
    
    def __init__(self):
        return super(SessionConsumer, self).__init__(SessionPersist)
    
    def persist_openid(self, request, response, openid_object):
        if self.session_key not in request.session.keys():
            request.session[self.session_key] = []
        # Eliminate any duplicates
        request.session[self.session_key] = [
            o for o in request.session[self.session_key] 
            if o.openid != openid_object.openid
        ]
        request.session[self.session_key].append(openid_object)
        request.session.modified = True
    
    def do_logout(self, request):
        openid = request.GET.get('openid', '').strip()
        if openid:
            # Just sign out that one
            request.session[self.session_key] = [
                o for o in request.session[self.session_key] 
                if o.openid != openid
            ]
        else:
            # Sign out ALL openids
            request.session[self.session_key] = []
        request.session.modified = True
        return self.on_logged_out(request)
    
    # This class doubles up as middleware
    def process_request(self, request):
        request.openid = None
        request.openids = []
        if self.session_key in request.session:
            try:
                request.openid = request.session[self.session_key][0]
            except IndexError:
                request.openid = None
            request.openids = request.session[self.session_key]

class CookieConsumer(LoginConsumer):
    """
    When the user logs in, save their OpenID details in a signed cookie. To 
    avoid cookies getting too big, this endpoint only stores the most 
    recently signed in OpenID; if you want multiple OpenIDs signed in at once
    you should use the SessionConsumer instead.
    """
    cookie_key = 'openid'
    cookie_max_age = None
    cookie_expires = None
    cookie_path = '/'
    cookie_domain = None
    cookie_secure = None
    
    extra_salt = 'cookie-consumer'
    
    def delete_cookie(self, response):
        response.delete_cookie(
            self.cookie_key, self.cookie_path, self.cookie_domain
        )
    
    def persist_openid(self, request, response, openid_object):
        response.set_cookie(
            key = self.cookie_key,
            value = signed.dumps(
                openid_object, compress = True, extra_key = self.extra_salt
            ),
            max_age = self.cookie_max_age,
            expires = self.cookie_expires,
            path = self.cookie_path,
            domain = self.cookie_domain,
            secure = self.cookie_secure,
        )
    
    def do_logout(self, request):
        response = self.on_logged_out(request)
        self.delete_cookie(response)
        return response
    
    def do_debug(self, request):
        from django.conf import settings
        if not settings.DEBUG:
            raise Http404
        if self.cookie_key in request.COOKIES:
            obj = signed.loads(
                request.COOKIES[self.cookie_key], extra_key = self.extra_salt
            )
            assert False, (obj, obj.__dict__)
        assert False, 'no cookie named %s' % self.cookie_key
    
    # This class doubles up as middleware
    def process_request(self, request):
        self._cookie_needs_deleting = False
        request.openid = None
        request.openids = []
        cookie_value = request.COOKIES.get(self.cookie_key, '')
        if cookie_value:
            try:
                request.openid = signed.loads(
                    cookie_value, extra_key = self.extra_salt
                )
                request.openids = [request.openid]
            except ValueError: # Signature failed
                self._cookie_needs_deleting = True
    
    def process_response(self, request, response):
        if getattr(self, '_cookie_needs_deleting', False):
            self.delete_cookie(response)
        return response

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
sys.path.insert(0, '../../../') # parent of django_openid directory
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
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'data.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

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
SECRET_KEY = '_vpc(7bu)r323l2td%)o&c&!$)8n(rh55^@#3)=h&^z6)%2w&0'

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

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django_openid',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect
from django_openid.consumer import Consumer

urlpatterns = patterns('',
    (r'^$', lambda r: HttpResponseRedirect('/openid/')),
    (r'^openid/(.*)', Consumer()),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
sys.path.insert(0, '../../../') # parent of django_openid directory
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
from django_openid.demos.consumer.settings import *

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect
from django_openid.consumer import Consumer

consumer = Consumer()

urlpatterns = patterns('',
    (r'^$', lambda r: HttpResponseRedirect('/openid/')),
    # As of Django 1.1 (actually changeset [9739]) you can use include here:
    (r'^openid/', include(consumer.urls)),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
sys.path.insert(0, '../../../') # parent of django_openid directory
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
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'data.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

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
SECRET_KEY = '_vpc(7bu)r323l2td%)o&c&!$)8n(rh55^@#3)=h&^z6)%2w&0'

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

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django_openid',
    'anon_provider',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect
from anon_provider import AnonProvider, openid_page

urlpatterns = patterns('',
    (r'^$', lambda r: HttpResponseRedirect('/openid/')),
    (r'^server/$', AnonProvider()),
    (r'^(\w+)/$', openid_page),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
sys.path.insert(0, '../../../') # parent of django_openid directory
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
# run "python -m smtpd -n -c DebuggingServer localhost:1025" to see outgoing
# messages dumped to the terminal
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'data.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

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
SECRET_KEY = '_vpc(7bu)r323l2td%)o&c&!$)8n(rh55^@#3)=h&^z6)%2w&0'

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
    'django_openid.registration.RegistrationConsumer',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django_openid',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect
from django_openid.registration import RegistrationConsumer

class NoSignNext(RegistrationConsumer):
    sign_next_param = False

urlpatterns = patterns('',
    (r'^$', lambda r: HttpResponseRedirect('/openid/')),
    (r'^openid/(.*)', NoSignNext()),
)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-openid documentation build configuration file, created by
# sphinx-quickstart on Thu Apr  9 08:47:42 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'django-openid'
copyright = '2009, Simon Willison'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '2.0a'
# The full version, including alpha/beta/rc tags.
release = '2.0a'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
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
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-openiddoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'django-openid.tex', 'django-openid Documentation',
   'Simon Willison', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = settings
# Fake settings.py so we can get sphinx autodoc to run against Django without 
# complaining.

DEBUG = True
TEMPLATE_DEBUG = True

DATABASE_ENGINE = ''
DATABASE_NAME = ''
DATABASE_USER = ''


########NEW FILE########
__FILENAME__ = forms
from django.contrib.auth.models import User
from django import forms

import re

class RegistrationForm(forms.ModelForm):
    no_password_error = 'You must either set a password or attach an OpenID'
    invalid_username_error = 'Usernames must consist of letters and numbers'
    reserved_username_error = 'That username cannot be registered'
    duplicate_email_error = 'That e-mail address is already in use'
    
    username_re = re.compile('^[a-zA-Z0-9]+$')
    
    # Additional required fields (above what the User model says)
    extra_required = ('first_name', 'last_name', 'email')
    
    def __init__(self, *args, **kwargs):
        """
        Accepts openid as optional keyword argument, for password validation.
        Also accepts optional reserved_usernames keyword argument which is a
        list of usernames that should not be registered (e.g. 'security')
        """
        try:
            self.openid = kwargs.pop('openid')
        except KeyError:
            self.openid = None
        try:
            self.reserved_usernames = kwargs.pop('reserved_usernames')
        except KeyError:
            self.reserved_usernames = []
        try:
            self.no_duplicate_emails = kwargs.pop('no_duplicate_emails')
        except KeyError:
            self.no_duplicate_emails = False
        
        # Super's __init__ creates self.fields for us
        super(RegistrationForm, self).__init__(*args, **kwargs)
        # Now we can modify self.fields with our extra required information
        for field in self.extra_required:
            self.fields[field].required = True
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
    
    # Password is NOT required as a general rule; we only validate that they 
    # have set a password if an OpenID is not being associated
    password = forms.CharField(
        widget = forms.PasswordInput,
        required = False
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if not self.username_re.match(username):
            raise forms.ValidationError, self.invalid_username_error
        if username in self.reserved_usernames:
            raise forms.ValidationError, self.reserved_username_error
        return username
    
    def clean_password(self):
        "Password is only required if no OpenID was specified"
        password = self.cleaned_data.get('password', '')
        if not self.openid and not password:
            raise forms.ValidationError, self.no_password_error
        return password
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        if self.no_duplicate_emails and User.objects.filter(
            email = email
        ).count() > 0:
            raise forms.ValidationError, self.duplicate_email_error
        return email

class RegistrationFormPasswordConfirm(RegistrationForm):
    password_mismatch_error = 'Your passwords do not match'
    
    password2 = forms.CharField(
        widget = forms.PasswordInput,
        required = False,
        label = "Confirm password"
    )
    
    def clean_password2(self):
        password = self.cleaned_data.get('password', '')
        password2 = self.cleaned_data.get('password2', '')
        if password and (password != password2):
            raise forms.ValidationError, self.password_mismatch_error
        return password2

class ChangePasswordForm(forms.Form):
    password = forms.CharField(
        widget = forms.PasswordInput,
        required = True
    )
    password2 = forms.CharField(
        widget = forms.PasswordInput,
        required = True,
        label = 'Confirm password'
    )
    password_mismatch_error = 'Your passwords do not match'
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
    
    def clean_password2(self):
        password = self.cleaned_data.get('password', '')
        password2 = self.cleaned_data.get('password2', '')
        if password and (password != password2):
            raise forms.ValidationError, self.password_mismatch_error
        return password2

class ChangePasswordVerifyOldForm(ChangePasswordForm):
    """
    Use this if you want the user to enter their old password first
    
    Careful though... if hte user has just recovered their account, they
    should be able to reset their password without having to enter the old
    one. This case is not currently handled.
    """
    password_incorrect_error = 'Your password is incorrect'
    
    def __init__(self, *args, **kwargs):
        super(ChangePasswordVerifyOldForm, self).__init__(*args, **kwargs)
        if self.user.has_usable_password() and self.user.password:
            # Only ask for their old password if they have set it already
            self.fields['old_password'] = forms.CharField(
                widget = forms.PasswordInput,
                required = True
            )
    
    def clean_old_password(self):
        password = self.cleaned_data.get('old_password', '')
        if not self.user.check_password(password):
            raise forms.ValidationError, self.password_incorrect_error

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
import hashlib
from openid.store.interface import OpenIDStore
import openid.store
from openid.association import Association as OIDAssociation
import time, base64


md5_constructor = hashlib.md5


class Nonce(models.Model):
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=128)
    
    def __unicode__(self):
        return u"Nonce: %s for %s" % (self.salt, self.server_url)

class Association(models.Model):
    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField(max_length=255) # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)
    
    def __unicode__(self):
        return u"Association: %s, %s" % (self.server_url, self.handle)

class DjangoOpenIDStore(OpenIDStore):
    """
    The Python openid library needs an OpenIDStore subclass to persist data 
    related to OpenID authentications. This one uses our Django models.
    """
    
    def storeAssociation(self, server_url, association):
        assoc = Association(
            server_url = server_url,
            handle = association.handle,
            secret = base64.encodestring(association.secret),
            issued = association.issued,
            lifetime = association.issued,
            assoc_type = association.assoc_type
        )
        assoc.save()
    
    def getAssociation(self, server_url, handle=None):
        assocs = []
        if handle is not None:
            assocs = Association.objects.filter(
                server_url = server_url, handle = handle
            )
        else:
            assocs = Association.objects.filter(
                server_url = server_url
            )
        if not assocs:
            return None
        associations = []
        for assoc in assocs:
            association = OIDAssociation(
                assoc.handle, base64.decodestring(assoc.secret), assoc.issued,
                assoc.lifetime, assoc.assoc_type
            )
            if association.getExpiresIn() == 0:
                self.removeAssociation(server_url, assoc.handle)
            else:
                associations.append((association.issued, association))
        if not associations:
            return None
        return associations[-1][1]
    
    def removeAssociation(self, server_url, handle):
        assocs = list(Association.objects.filter(
            server_url = server_url, handle = handle
        ))
        assocs_exist = len(assocs) > 0
        for assoc in assocs:
            assoc.delete()
        return assocs_exist
    
    def useNonce(self, server_url, timestamp, salt):
        # Has nonce expired?
        if abs(timestamp - time.time()) > openid.store.nonce.SKEW:
            return False
        try:
            nonce = Nonce.objects.get(
                server_url__exact = server_url,
                timestamp__exact = timestamp,
                salt__exact = salt
            )
        except Nonce.DoesNotExist:
            nonce = Nonce.objects.create(
                server_url = server_url,
                timestamp = timestamp,
                salt = salt
            )
            return True
        nonce.delete()
        return False
    
    def cleanupNonce(self):
        Nonce.objects.filter(
            timestamp__lt = (int(time.time()) - nonce.SKEW)
        ).delete()
    
    def cleaupAssociations(self):
        Association.objects.extra(
            where=['issued + lifetimeint < (%s)' % time.time()]
        ).delete()
    
    def getAuthKey(self):
        # Use first AUTH_KEY_LEN characters of md5 hash of SECRET_KEY
        return md5_constructor.new(settings.SECRET_KEY).hexdigest()[:self.AUTH_KEY_LEN]
    
    def isDumb(self):
        return False

# Only include table for User->OpenID associations if User model is installed
user_model = models.get_model('auth', 'User')
if user_model and user_model._meta.installed:
    class UserOpenidAssociation(models.Model):
        "Auth integration - lets you associate 1+ OpenIDs with a User"
        user = models.ForeignKey('auth.User', related_name = 'openids')
        openid = models.CharField(max_length = 255)
        created = models.DateTimeField(auto_now_add = True)
        
        def __unicode__(self):
            return u'%s can log in with %s' % (self.user, self.openid)

########NEW FILE########
__FILENAME__ = provider
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from openid.server.server import Server
from openid.extensions import sreg
from django_openid.models import DjangoOpenIDStore
from django_openid import signed
from django_openid.response import TemplateResponse

class Provider(object):
    """
    The default OpenID server, designed to be subclassed.
    """
    base_template = 'django_openid/base.html'
    this_is_a_server_template = 'django_openid/this_is_an_openid_server.html'
    landing_page_template = 'django_openid/landing_page.html'
    error_template = 'django_openid/error.html'
    decide_template = 'django_openid/decide.html'
    
    not_your_openid_message = 'You are signed in but do not own that OpenID'
    invalid_decide_post_message = 'Your submission cannot be processed'
    
    save_trusted_roots = False # If true, tries to persist trusted roots
    secret_key = None
    
    incomplete_orequest_cookie_key = 'incomplete_orequest'
    orequest_salt = 'orequest-salt'
    
    def render(self, request, template, context=None):
        context = context or {}
        context['base_template'] = self.base_template
        return TemplateResponse(request, template, context)
    
    def get_server(self, request):
        url = request.build_absolute_uri(request.path)
        return Server(DjangoOpenIDStore(), op_endpoint=url)
    
    def user_is_logged_in(self, request):
        return False
    
    def openid_is_authorized(self, request, openid, trust_root):
        return self.user_is_logged_in(request) and \
            self.user_owns_openid(request, openid) and \
            self.user_trusts_root(request, openid, trust_root)
    
    def user_owns_openid(self, request, openid):
        return False
    
    def user_trusts_root(self, request, openid, trust_root):
        # Over-ride to implement trust root whitelisting style functionality
        return False
    
    def server_response(self, request, oresponse):
        webresponse = self.get_server(request).encodeResponse(oresponse)
        response = HttpResponse(webresponse.body)
        response.status_code = webresponse.code
        for key, value in webresponse.headers.items():
            response[key] = value
        return response
    
    def show_landing_page(self, request, orequest):
        # Stash the incomplete orequest in a signed cookie
        response = self.render(request, self.landing_page_template, {
            'identity_url': orequest.identity,
        })
        self.stash_incomplete_orequest(request, response, orequest)
        return response
    
    def stash_incomplete_orequest(self, request, response, orequest):
        response.set_cookie(
            self.incomplete_orequest_cookie_key, signed.dumps(
                orequest, extra_key = self.orequest_salt
            )
        )
    
    def show_error(self, request, message):
        return self.render(request, self.error_template, {
            'message': message,
        })
    
    def show_decide(self, request, orequest):
        # If user is logged in, ask if they want to trust this trust_root
        # If they are NOT logged in, show the landing page:
        if not self.user_is_logged_in(request):
            return self.show_landing_page(request, orequest)
        
        # Check that the user owns the requested identity
        if not self.user_owns_openid(request, orequest.identity):
            return self.show_error(request, self.not_your_openid_message)
        
        # They are logged in - ask if they want to trust this root
        return self.render(request, self.decide_template, {
            'trust_root': orequest.trust_root,
            'identity': orequest.identity,
            'orequest': signed.dumps(orequest, self.secret_key),
            'action': request.path,
            'save_trusted_roots': self.save_trusted_roots
        })
    
    def get_sreg_data(self, request, openid):
        return {}
    
    def add_sreg_data(self, request, orequest, oresponse):
        sreg_req = sreg.SRegRequest.fromOpenIDRequest(orequest)
        sreg_resp = sreg.SRegResponse.extractResponse(
            sreg_req, self.get_sreg_data(request, orequest.identity)
        )
        oresponse.addExtension(sreg_resp)
    
    def save_trusted_root(self, request, openid, trust_root):
        pass
    
    def process_decide(self, request):
        try:
            orequest = signed.loads(
                request.POST.get('orequest', ''), self.secret_key
            )
        except ValueError:
            return self.show_error(request, self.invalid_decide_post_message)
        
        they_said_yes = bool(
            ('yes_once' in request.POST) or
            ('yes_always' in request.POST)
        )
        if 'yes_always' in request.POST:
            self.save_trusted_root(
                request, orequest.identity, orequest.trust_root
            )
        
        # TODO: Double check what we should be passing as identity= here:
        oresponse = orequest.answer(they_said_yes, identity=orequest.identity)
        self.add_sreg_data(request, orequest, oresponse)
        return self.server_response(request, oresponse)
    
    def extract_incomplete_orequest(self, request):
        # Incomplete orequests are stashed in a cookie
        try:
            return signed.loads(request.COOKIES.get(
                self.incomplete_orequest_cookie_key, ''
            ), extra_key = self.orequest_salt)
        except signed.BadSignature:
            return None
    
    def __call__(self, request):
        # If this is a POST from the decide page, behave differently
        if '_decide' in request.POST:
            return self.process_decide(request)
        
        querydict = dict(request.REQUEST.items())
        orequest = self.get_server(request).decodeRequest(querydict)
        if not orequest:
            # This case (accessing the /server/ page without any args) serves 
            # two purposes. If the user has a partially complete OpenID 
            # request stashed in a signed cookie (i.e. they weren't logged 
            # in when they hit the anti-phishing landing page, then went 
            # away and logged in again, then were pushed back to here) we 
            # need to offer to complete that. Otherwise, just show a message.
            orequest = self.extract_incomplete_orequest(request)
            if orequest:
                return self.show_decide(request, orequest)
            return self.show_this_is_an_openid_server(request)
        
        if orequest.mode in ("checkid_immediate", "checkid_setup"):
            if self.openid_is_authorized(
                    request, orequest.identity, orequest.trust_root
                ):
                oresponse = orequest.answer(True)
            elif orequest.immediate:
                oresponse = orequest.answer(
                    False, request.build_absolute_uri()
                )
            else:
                return self.show_decide(request, orequest)
        else:
            oresponse = self.get_server(request).handleRequest(orequest)
        return self.server_response(request, oresponse)
    
    def show_this_is_an_openid_server(self, request):
        return self.render(request, self.this_is_a_server_template)

########NEW FILE########
__FILENAME__ = registration
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings

from django_openid.auth import AuthConsumer
from django_openid.utils import OpenID, int_to_hex, hex_to_int
from django_openid import signed
from django_openid import forms

from openid.consumer import consumer

import urlparse

class RegistrationConsumer(AuthConsumer):
    already_signed_in_message = 'You are already signed in to this site'
    unknown_openid_message = \
        'That OpenID is not recognised. Would you like to create an account?'
    c_already_confirmed_message = 'Your account is already confirmed'
    
    register_template = 'django_openid/register.html'
    set_password_template = 'django_openid/set_password.html'
    confirm_email_template = 'django_openid/register_confirm_email.txt'
    register_email_sent_template = 'django_openid/register_email_sent.html'
    register_complete_template = 'django_openid/register_complete.html'
    
    after_registration_url = None # None means "show a message instead"
    unconfirmed_group = 'Unconfirmed users'
    
    # Registration options
    reserved_usernames = ['security', 'info', 'admin']
    no_duplicate_emails = True    
    confirm_email_addresses = True
    
    confirm_email_from = None # If None, uses settings.DEFAULT_FROM_EMAIL
    confirm_email_subject = 'Confirm your e-mail address'
    confirm_link_secret = None
    confirm_link_salt = 'confirm-link-salt'
    
    # sreg
    sreg = ['nickname', 'email', 'fullname']
    
    RegistrationForm = forms.RegistrationFormPasswordConfirm
    ChangePasswordForm = forms.ChangePasswordForm
    
    def user_is_confirmed(self, user):
        return not self.user_is_unconfirmed(user)
    
    def user_is_unconfirmed(self, user):
        return user.groups.filter(name = self.unconfirmed_group).count()
    
    def mark_user_unconfirmed(self, user):
        from django.contrib.auth.models import Group
        user.is_active = False
        user.save()
        group, _ = Group.objects.get_or_create(name = self.unconfirmed_group)
        user.groups.add(group)
    
    def mark_user_confirmed(self, user):
        user.groups.filter(name = self.unconfirmed_group).delete()
    
    def get_registration_form_class(self, request):
        return self.RegistrationForm
    
    def get_change_password_form_class(self, request):
        return self.ChangePasswordForm
    
    def show_i_have_logged_you_in(self, request):
        return self.show_message(
            request, 'You are logged in',
            'You already have an account for that OpenID. ' + 
            'You are now logged in.'
        )
    
    def do_register_complete(self, request):
        
        def on_success(request, identity_url, openid_response):
            # We need to behave differently from the default AuthConsumer
            # success behaviour. For simplicity, we do the following:
            # 1. "Log them in" as that OpenID i.e. stash it in the session
            # 2. If it's already associated with an account, log them in as 
            #    that account and show a message.
            # 2. If NOT already associated, redirect back to /register/ again
            openid_object = OpenID.from_openid_response(openid_response)
            matches = self.lookup_openid(request, identity_url)
            if matches:
                # Log them in and show the message
                self.log_in_user(request, matches[0])
                response = self.show_i_have_logged_you_in(request)
            else:
                response = HttpResponseRedirect(urlparse.urljoin(
                    request.path, '../register/'
                ))
            self.persist_openid(request, response, openid_object)
            return response
        
        return self.dispatch_openid_complete(request, {
            consumer.SUCCESS: on_success,
            consumer.CANCEL: 
                lambda request, openid_response: self.do_register(request, 
                    message = self.request_cancelled_message
                ),
            consumer.FAILURE: 
                lambda request, openid_response: self.do_register(request, 
                    message = self.failure_message % openid_response.message
                ),
            consumer.SETUP_NEEDED: 
                lambda request, openid_response: self.do_register(request, 
                    message = self.setup_needed_message
                ),
        })
    
    def on_registration_complete(self, request):
        if self.after_registration_url:
            return HttpResponseRedirect(self.after_registration_url)
        else:
            return self.render(request, self.register_complete_template)
    
    def do_register(self, request, message=None):
        # Show a registration / signup form, provided the user is not 
        # already logged in
        if not request.user.is_anonymous():
            return self.show_already_signed_in(request)
        
        # Spot incoming openid_url authentication requests
        if request.POST.get('openid_url', None):
            return self.start_openid_process(request,
                user_url = request.POST.get('openid_url'),
                on_complete_url = urlparse.urljoin(
                    request.path, '../register_complete/'
                ),
                trust_root = urlparse.urljoin(request.path, '..')
            )
        
        RegistrationForm = self.get_registration_form_class(request)
        
        try:
            openid = request.openid and request.openid.openid or None
        except AttributeError:
            return self.show_error(
                request, 'Add CookieConsumer or similar to your middleware'
            )
        
        if request.method == 'POST':
            # TODO: The user might have entered an OpenID as a starting point,
            # or they might have decided to sign up normally
            form = RegistrationForm(
                request.POST,
                openid = openid,
                reserved_usernames = self.reserved_usernames,
                no_duplicate_emails = self.no_duplicate_emails
            )
            if form.is_valid():
                user = self.create_user(request, form.cleaned_data, openid)
                if self.confirm_email_addresses:
                    return self.confirm_email_step(request, user)
                else:
                    self.log_in_user(request, user)
                    return self.on_registration_complete(request)
        else:
            form = RegistrationForm(
                initial = request.openid and self.initial_from_sreg(
                    request.openid.sreg
                ) or {},
                openid = openid,
                reserved_usernames = self.reserved_usernames,
                no_duplicate_emails = self.no_duplicate_emails
            )
        
        return self.render(request, self.register_template, {
            'form': form,
            'message': message,
            'openid': request.openid,
            'logo': self.logo_path or (urlparse.urljoin(
                request.path, '../logo/'
            )),
            'no_thanks': self.sign_next(request.path),
            'action': request.path,
        })
    
    def confirm_email_step(self, request, user):
        self.mark_user_unconfirmed(user)
        self.send_confirm_email(request, user)
        return self.render(request, self.register_email_sent_template, {
            'email': user.email,
        })
    
    def generate_confirm_code(self, user):
        return signed.sign(int_to_hex(user.id), key = (
            self.confirm_link_secret or settings.SECRET_KEY
        ) + self.confirm_link_salt)
    
    def send_confirm_email(self, request, user):
        from_email = self.confirm_email_from or settings.DEFAULT_FROM_EMAIL
        code = self.generate_confirm_code(user)
        path = urlparse.urljoin(request.path, '../c/%s/' % code)
        url = request.build_absolute_uri(path)
        send_mail(
            subject = self.confirm_email_subject,
            message = self.render(request, self.confirm_email_template, {
                'url': url,
                'code': code,
                'newuser': user,
            }).content,
            from_email = from_email,
            recipient_list = [user.email]
        )
    
    def do_c(self, request, token = ''):
        if not token:
            # TODO: show a form where they can paste in their token?
            raise Http404
        token = token.rstrip('/').encode('utf8')
        try:
            value = signed.unsign(token, key = (
                self.confirm_link_secret or settings.SECRET_KEY
            ) + self.confirm_link_salt)
        except signed.BadSignature:
            return self.show_message(
                request, self.invalid_token_message,
                self.invalid_token_message + ': ' + token
            )
        user_id = hex_to_int(value)
        user = self.lookup_user_by_id(user_id)
        if not user: # Maybe the user was deleted?
            return self.show_error(request, r_user_not_found_message)
        
        # Check user is NOT active but IS in the correct group
        if self.user_is_unconfirmed(user):
            # Confirm them
            user.is_active = True
            user.save()
            self.mark_user_confirmed(user)
            self.log_in_user(request, user)
            return self.on_registration_complete(request)
        else:
            return self.show_error(request, self.c_already_confirmed_message)
    
    do_c.urlregex = '^c/([^/]+)/$'
    
    def create_user(self, request, data, openid=None):
        from django.contrib.auth.models import User
        user = User.objects.create(
            username = data['username'],
            first_name = data.get('first_name', ''),
            last_name = data.get('last_name', ''),
            email = data.get('email', ''),
        )
        # Set OpenID, if one has been associated
        if openid:
            user.openids.create(openid = openid)
        # Set password, if one has been specified
        password = data.get('password')
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user
    
    def do_password(self, request):
        "Allow users to set a password on their account"
        if request.user.is_anonymous():
            return self.show_error(request, 'You need to log in first')
        ChangePasswordForm = self.get_change_password_form_class(request)
        if request.method == 'POST':
            form = ChangePasswordForm(request.user, data=request.POST)
            if form.is_valid():
                u = request.user
                u.set_password(form.cleaned_data['password'])
                u.save()
                return self.show_password_has_been_set(request)
        else:
            form = ChangePasswordForm(request.user)
        return self.render(request, self.set_password_template, {
            'form': form,
            'action': request.path,
        })
    
    def show_password_has_been_set(self, request):
        return self.show_message(
            request, 'Password set', 'Your password has been set.'
        )
    
    def initial_from_sreg(self, sreg):
        "Maps sreg to data for populating registration form"
        fullname = sreg.get('fullname', '')
        first_name, last_name = '', ''
        if fullname:
            bits = fullname.split()
            first_name = bits[0]
            if len(bits) > 1:
                last_name = ' '.join(bits[1:])
        return {
            'username': self.suggest_nickname(sreg.get('nickname', '')),
            'first_name': first_name,
            'last_name': last_name,
            'email': sreg.get('email', ''),
        }
    
    def suggest_nickname(self, nickname):
        "Return a suggested nickname that has not yet been taken"
        from django.contrib.auth.models import User
        if not nickname:
            return ''
        original_nickname = nickname
        suffix = None
        while User.objects.filter(username = nickname).count():
            if suffix is None:
                suffix = 1
            else:
                suffix += 1
            nickname = original_nickname + str(suffix)
        return nickname
    
    def show_unknown_openid(self, request, openid):
        # If the user gets here, they have attempted to log in using an 
        # OpenID BUT it's an OpenID we have never seen before - so show 
        # them the index page but with an additional message
        return self.do_index(request, self.unknown_openid_message)
    
    def show_already_signed_in(self, request):
        return self.show_message(
            request, 'Already signed in', self.already_signed_in_message
        )

########NEW FILE########
__FILENAME__ = response
from django.http import HttpResponse
from django.template import loader, Context, RequestContext

class SimpleTemplateResponse(HttpResponse):
    
    def __init__(self, template, context, *args, **kwargs):
        # These two properties were originally called 'template' and 'context'
        # but django.test.client.Client was clobbering those leading to really
        # tricky-to-debug problems
        self.template_name = template
        self.template_context = context
        self.baked = False
        super(SimpleTemplateResponse, self).__init__(*args, **kwargs)
    
    def resolve_template(self, template):
        "Accepts a template object, path-to-template or list of paths"
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        elif isinstance(template, basestring):
            return loader.get_template(template)
        else:
            return template
    
    def resolve_context(self, context):
        "context can be a dictionary or a context object"
        if isinstance(context, Context):
            return context
        else:
            return Context(context)
    
    def render(self):
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.template_context)
        content = template.render(context)
        return content
    
    def bake(self):
        """
        The template is baked the first time you try to access 
        response.content or iterate over it. This is a bit ugly, but is 
        necessary because Django middleware sometimes expects to be able to 
        over-write the content of a response.
        """
        if not self.baked:
            self.force_bake()
    
    def force_bake(self):
        "Call this if you have modified the template or context but are "
        "unsure if the template has already been baked."
        self._set_content(self.render())
        self.baked = True
    
    def __iter__(self):
        self.bake()
        return super(SimpleTemplateResponse, self).__iter__()
    
    def _get_content(self):
        self.bake()
        return super(SimpleTemplateResponse, self)._get_content()
    
    def _set_content(self, value):
        "Overrides rendered content, unless you later call force_bake()"
        return super(SimpleTemplateResponse, self)._set_content(value)
    
    content = property(_get_content, _set_content)

class TemplateResponse(SimpleTemplateResponse):
    
    def __init__(self, request, template, context, *args, **kwargs):
        # self.request gets over-written by django.test.client.Client - and 
        # unlike template_context and template_name the _request should not 
        # be considered part of the public API.
        self._request = request
        super(TemplateResponse, self).__init__(
            template, context, *args, **kwargs
        )
    
    def resolve_context(self, context):
        if isinstance(context, Context):
            return context
        else:
            return RequestContext(self._request, context)

# Even less verbose alias:
render = TemplateResponse

########NEW FILE########
__FILENAME__ = signed
"""
Functions for creating and restoring url-safe signed pickled objects.

The format used looks like this:

>>> signed.dumps("hello")
'UydoZWxsbycKcDAKLg.AfZVu7tE6T1K1AecbLiLOGSqZ-A'

There are two components here, separatad by a '.'. The first component is a 
URLsafe base64 encoded pickle of the object passed to dumps(). The second 
component is a base64 encoded hmac/SHA1 hash of "$first_component.$secret"

Calling signed.loads(s) checks the signature BEFORE unpickling the object - 
this protects against malformed pickle attacks. If the signature fails, a 
ValueError subclass is raised (actually a BadSignature):

>>> signed.loads('UydoZWxsbycKcDAKLg.AfZVu7tE6T1K1AecbLiLOGSqZ-A')
'hello'
>>> signed.loads('UydoZWxsbycKcDAKLg.AfZVu7tE6T1K1AecbLiLOGSqZ-A-modified')
...
BadSignature: Signature failed: AfZVu7tE6T1K1AecbLiLOGSqZ-A-modified

You can optionally compress the pickle prior to base64 encoding it to save 
space, using the compress=True argument. This checks if compression actually
helps and only applies compression if the result is a shorter string:

>>> signed.dumps(range(1, 10), compress=True)
'.eJzTyCkw4PI05Er0NAJiYyA2AWJTIDYDYnMgtgBiS65EPQDQyQme.EQpzZCCMd3mIa4RXDGnAuMCCAx0'

The fact that the string is compressed is signalled by the prefixed '.' at the
start of the base64 pickle.

There are 65 url-safe characters: the 64 used by url-safe base64 and the '.'. 
These functions make use of all of them.
"""

import pickle, base64
from django.conf import settings
from django.utils.hashcompat import sha_constructor
import hmac

def dumps(obj, key = None, compress = False, extra_key = ''):
    """
    Returns URL-safe, sha1 signed base64 compressed pickle. If key is 
    None, settings.SECRET_KEY is used instead.
    
    If compress is True (not the default) checks if compressing using zlib can
    save some space. Prepends a '.' to signify compression. This is included 
    in the signature, to protect against zip bombs.
    
    extra_key can be used to further salt the hash, in case you're worried 
    that the NSA might try to brute-force your SHA-1 protected secret.
    """
    pickled = pickle.dumps(obj)
    is_compressed = False # Flag for if it's been compressed or not
    if compress:
        import zlib # Avoid zlib dependency unless compress is being used
        compressed = zlib.compress(pickled)
        if len(compressed) < (len(pickled) - 1):
            pickled = compressed
            is_compressed = True
    base64d = encode(pickled).strip('=')
    if is_compressed:
        base64d = '.' + base64d
    return sign(base64d, (key or settings.SECRET_KEY) + extra_key)

def loads(s, key = None, extra_key = ''):
    "Reverse of dumps(), raises ValueError if signature fails"
    if isinstance(s, unicode):
        s = s.encode('utf8') # base64 works on bytestrings, not on unicodes
    try:
        base64d = unsign(s, (key or settings.SECRET_KEY) + extra_key)
    except ValueError:
        raise
    decompress = False
    if base64d[0] == '.':
        # It's compressed; uncompress it first
        base64d = base64d[1:]
        decompress = True
    pickled = decode(base64d)
    if decompress:
        import zlib
        pickled = zlib.decompress(pickled)
    return pickle.loads(pickled)

def encode(s):
    return base64.urlsafe_b64encode(s).strip('=')

def decode(s):
    return base64.urlsafe_b64decode(s + '=' * (len(s) % 4))

class BadSignature(ValueError):
    # Extends ValueError, which makes it more convenient to catch and has 
    # basically the correct semantics.
    pass

def sign(value, key = None):
    if isinstance(value, unicode):
        raise TypeError, \
            'sign() needs bytestring, not unicode: %s' % repr(value)
    if key is None:
        key = settings.SECRET_KEY
    return value + '.' + base64_hmac(value, key)

def unsign(signed_value, key = None):
    if isinstance(signed_value, unicode):
        raise TypeError, 'unsign() needs bytestring, not unicode'
    if key is None:
        key = settings.SECRET_KEY
    if not '.' in signed_value:
        raise BadSignature, 'Missing sig (no . found in value)'
    value, sig = signed_value.rsplit('.', 1)
    if base64_hmac(value, key) == sig:
        return value
    else:
        raise BadSignature, 'Signature failed: %s' % sig

def base64_hmac(value, key):
    return encode(hmac.new(key, value, sha_constructor).digest())

########NEW FILE########
__FILENAME__ = auth_tests
from django.test import TestCase
from django.test.client import Client
from django.http import Http404
from django.conf import settings
from django.core import mail

from django_openid.registration import RegistrationConsumer
from django_openid import signed

from django.contrib.auth.models import User
from django.utils.decorators import decorator_from_middleware
from request_factory import RequestFactory
from openid_mocks import *

from openid.consumer import consumer as janrain_consumer

rf = RequestFactory()

class AuthTestBase(TestCase):
    urls = 'django_openid.tests.auth_test_urls'
    
    def setUp(self):
        # Monkey-patch in the correct middleware
        self.old_middleware = settings.MIDDLEWARE_CLASSES
        settings.MIDDLEWARE_CLASSES = (
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django_openid.registration.RegistrationConsumer',
        )
        
        # Create user accounts associated with OpenIDs
        self.no_openids = User.objects.create(
            username = 'noopenids',
            email = 'noopenids@example.com'
        )
        self.no_openids.set_password('password')
        self.no_openids.save()
        self.one_openid = User.objects.create(username = 'oneopenid')
        self.one_openid.openids.create(openid = 'http://a.example.com/')
        self.two_openid = User.objects.create(username = 'twoopenids')
        self.two_openid.openids.create(openid = 'http://b.example.com/')
        self.two_openid.openids.create(openid = 'http://c.example.com/')
    
    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.old_middleware

class AuthTest(AuthTestBase):
    
    def testLoginWithPassword(self):
        response = self.client.post('/openid/login/', {
            'username': 'noopenids',
            'password': 'incorrect-password',
        })
        self.assertEqual(
            response.template_name, 'django_openid/login_plus_password.html'
        )
        response = self.client.post('/openid/login/', {
            'username': 'noopenids',
            'password': 'password',
        })
        self.assertRedirects(response, '/')

class RegistrationTest(AuthTestBase):
    
    def testInvalidRegistrationWithPassword(self):
        response = self.client.post('/openid/register/', data = {
            'username': 'noopenids', # already in use
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'password',
            'password2': 'password',
        })
        self.assertEqual(
            response.template_name, 'django_openid/register.html'
        )
        self.assert_(
            'User with this Username already exists' in str(response)
        )
    
    def testRegisterWithPassword(self):
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post('/openid/register/', data = {
            'username': 'newuser', # already in use
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'password',
            'password2': 'password',
        })
        self.assertEqual(
            response.template_name, 'django_openid/register_email_sent.html'
        )
        # newuser should belong to 'Unconfirmed users' and have is_active=0
        user = User.objects.get(username = 'newuser')
        self.assertEqual(user.is_active, False)
        self.assertEqual(
            user.groups.filter(name = 'Unconfirmed users').count(), 1
        )
        # An e-mail should have been sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Now extract and click that link
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [u'test@example.com'])
        link = [
            l.strip() for l in msg.body.splitlines()
            if l.startswith('http://testserver/')
        ][0]
        response = self.client.get(link)
        self.assertEqual(
            response.template_name, 'django_openid/register_complete.html'
        )
        
        user = User.objects.get(username = 'newuser')
        self.assertEqual(user.is_active, True)
        self.assertEqual(
            user.groups.filter(name = 'Unconfirmed users').count(), 0
        )

class AccountRecoveryTest(AuthTestBase):
    
    def testRecoverAccountBadUsername(self):
        response = self.client.get('/openid/recover/')
        self.assertEqual(
            response.template_name, 'django_openid/recover.html'
        )
        response = self.client.post('/openid/recover/', {
            'recover': 'does-not-exist'
        })
        self.assertEqual(
            response.template_context['message'],
            RegistrationConsumer.recovery_not_found_message
        )
        
    def testRecoverAccountByUsername(self):
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post('/openid/recover/', {
            'recover': 'noopenids'
        })
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [u'noopenids@example.com'])
        link = [
            l.strip() for l in msg.body.splitlines()
            if l.startswith('http://testserver/')
        ][0]
        
        # Tampering with the link should cause it to fail
        bits = link.split('.')
        bits[-1] = 'X' + bits[-1]
        tampered = '.'.join(bits)
        response = self.client.get(tampered)
        self.assert_('Invalid token' in str(response))
        self.assertNotEqual(
            response.template_name, 'django_openid/recovery_complete.html'
        )
        # Following that link should log us in
        response = self.client.get(link)
        self.assertEqual(
            response.template_name, 'django_openid/recovery_complete.html'
        )
        self.assertEqual(response._request.user.username, 'noopenids')



########NEW FILE########
__FILENAME__ = auth_test_urls
from django.conf.urls.defaults import *
from django.http import HttpResponse
from django_openid.registration import RegistrationConsumer

urlpatterns = patterns('',
    (r'^$', lambda r: HttpResponse('Index')),
    (r'^openid/(.*)', RegistrationConsumer()),
)

########NEW FILE########
__FILENAME__ = consumer_tests
from django.test import TestCase
from django.http import Http404
from django_openid.consumer import Consumer
from django_openid import signed

from request_factory import RequestFactory
from openid_mocks import *

from openid.consumer import consumer as janrain_consumer

rf = RequestFactory()

class ConsumerTest(TestCase):
    
    def testBadMethod(self):
        "Non existent methods should result in a 404"
        openid_consumer = MyConsumer()
        get = rf.get('/openid/foo/')
        self.assertRaises(Http404, openid_consumer, get, 'foo/')
    
    def testLoginBegin(self):
        "Can log in with an OpenID"
        openid_consumer = MyConsumer()
        post = rf.post('/openid/', {
            'openid_url': 'http://simonwillison.net/'
        })
        post.session = MockSession()
        response = openid_consumer(post)
        self.assertEqual(response['Location'], 'http://url-of-openid-server/')
        oid_session = signed.loads(response.cookies['o_user_session'].value)
        self.assert_('openid_bits' in oid_session)
    
    def testLoginDiscoverFail(self):
        "E.g. the user enters an invalid URL"
        openid_consumer = MyDiscoverFailConsumer()
        post = rf.post('/openid/', {
            'openid_url': 'not-an-openid'
        })
        post.session = MockSession()
        response = openid_consumer(post)
        self.assert_(openid_consumer.openid_invalid_message in str(response))
    
    def testLoginSuccess(self):
        "Simulate a successful login"
        openid_consumer = MyConsumer()
        openid_consumer.set_mock_response(
            status = janrain_consumer.SUCCESS,
            identity_url = 'http://simonwillison.net/',
        )
        get = rf.get('/openid/complete/', {'openid-args': 'go-here'})
        get.session = MockSession()
        response = openid_consumer(get, 'complete/')
        self.assert_(
            'You logged in as http://simonwillison.net/' in response.content
        )
    
    def testLoginNext(self):
        "?next=<signed> causes final redirect to go there instead"
        openid_consumer = MyConsumer()
        openid_consumer.set_mock_response(
            status = janrain_consumer.SUCCESS,
            identity_url = 'http://simonwillison.net/',
        )
        get = rf.get('/openid/complete/', {
            'openid-args': 'go-here',
            'next': openid_consumer.sign_next('/foo/')
        })
        get.session = MockSession()
        response = openid_consumer(get, 'complete/')
        self.assertEqual(response['Location'], '/foo/')
    
    def testLoginCancel(self):
        openid_consumer = MyConsumer()
        openid_consumer.set_mock_response(
            status = janrain_consumer.CANCEL,
            identity_url = 'http://simonwillison.net/',
        )
        get = rf.get('/openid/complete/', {'openid-args': 'go-here'})
        get.session = MockSession()
        response = openid_consumer(get, 'complete/')
        self.assert_(
            openid_consumer.request_cancelled_message in response.content
        )
    
    def testLoginFailure(self):
        openid_consumer = MyConsumer()
        openid_consumer.set_mock_response(
            status = janrain_consumer.FAILURE,
            identity_url = 'http://simonwillison.net/',
        )
        get = rf.get('/openid/complete/', {'openid-args': 'go-here'})
        get.session = MockSession()
        response = openid_consumer(get, 'complete/')
        self.assert_('Failure: ' in response.content)
    
    def testLoginSetupNeeded(self):
        openid_consumer = MyConsumer()
        openid_consumer.set_mock_response(
            status = janrain_consumer.SETUP_NEEDED,
            identity_url = 'http://simonwillison.net/',
        )
        get = rf.get('/openid/complete/', {'openid-args': 'go-here'})
        get.session = MockSession()
        response = openid_consumer(get, 'complete/')
        self.assert_(openid_consumer.setup_needed_message in response.content)
    
    def testLogo(self):
        openid_consumer = MyConsumer()
        get = rf.get('/openid/logo/')
        response = openid_consumer(get, 'logo/')
        self.assert_('image/gif' in response['Content-Type'])

class SessionConsumerTest(TestCase):
    
    def login(self):
        openid_consumer = MySessionConsumer()
        openid_consumer.set_mock_response(
            status = janrain_consumer.SUCCESS,
            identity_url = 'http://simonwillison.net/',
        )
        get = rf.get('/openid/complete/', {'openid-args': 'go-here'})
        get.session = MockSession()
        response = openid_consumer(get, 'complete/')
        return get, response
    
    def testLogin(self):
        "Simulate a successful login"
        request, response = self.login()
        self.assertEqual(response['Location'], '/')
        self.assert_('openids' in request.session)
        self.assertEqual(len(request.session['openids']), 1)
        self.assertEqual(
            request.session['openids'][0].openid, 'http://simonwillison.net/'
        )
    
    def testLogout(self):
        request, response = self.login()
        get = rf.get('/openid/logout/')
        get.session = request.session
        openid_consumer = MySessionConsumer()
        response = openid_consumer(get, 'logout/')
        self.assertEqual(response['Location'], '/')
        self.assertEqual(len(request.session['openids']), 0)

class CookieConsumerTest(TestCase):
    
    def login(self):
        openid_consumer = MyCookieConsumer()
        openid_consumer.set_mock_response(
            status = janrain_consumer.SUCCESS,
            identity_url = 'http://simonwillison.net/',
        )
        get = rf.get('/openid/complete/', {'openid-args': 'go-here'})
        response = openid_consumer(get, 'complete/')
        return get, response
    
    def testLogin(self):
        "Simulate a successful login"
        request, response = self.login()
        self.assert_('openid' in response.cookies, 'openid cookie not set')
        self.assertEqual(response['Location'], '/')
        # Decrypt the cookie and check it's the right thing
        cookie = response.cookies['openid'].value
        openid = signed.loads(
            cookie, extra_key = MyCookieConsumer().extra_salt
        )
        self.assertEqual(openid.openid, 'http://simonwillison.net/')
    
    def testLogout(self):
        request, response = self.login()
        get = rf.get('/openid/logout/')
        openid_consumer = MyCookieConsumer()
        response = openid_consumer(get, 'logout/')
        self.assert_('openid' in response.cookies, 'openid cookie not set')
        self.assertEqual(response['Location'], '/')
        self.assertEqual(response.cookies['openid'].value, '')


########NEW FILE########
__FILENAME__ = openid_mocks
"""
Mock objects for the bits of the OpenID flow that would normally involve 
communicating with an external service.
"""
from django_openid.consumer import Consumer, SessionConsumer, CookieConsumer
from django_openid.auth import AuthConsumer
from openid.message import Message

class MockSession(dict):
    def __init__(self, **kwargs):
        super(MockSession, self).__init__(**kwargs)
        self.modified = False

class MockAuthRequest(object):
    def __init__(self, consumer):
        self.consumer = consumer
    
    def redirectURL(self, trust_root, on_complete_url):
        return self.consumer.redirect_url

class MockOpenIDResponse(object):
    def __init__(self, status, identity_url):
        self.status = status
        self.identity_url = identity_url
        self.message = Message()
    
    def getSignedNS(self, *args):
        return {}

class MockConsumer(object):
    def __init__(self, consumer, user_url, redirect_url, session_store,
            raise_discover_failure=None):
        self.consumer = consumer
        self.user_url = user_url
        self.redirect_url = redirect_url
        self.session_store = session_store
        self.raise_discover_failure = raise_discover_failure
    
    def complete(self, *args, **kwargs):
        return self.consumer._mock_response
    
    def begin(self, user_url):
        from openid.consumer.discover import DiscoveryFailure
        if self.raise_discover_failure:
            raise DiscoveryFailure(500, 'Error')
        self.session_store['openid_bits'] = {'foo': 'bar'}
        return MockAuthRequest(self)

class MyDiscoverFailConsumer(Consumer):
    def get_consumer(self, request, session_store):
        return MockConsumer(
            consumer = self,
            user_url = 'http://simonwillison.net/',
            redirect_url = 'http://url-of-openid-server/',
            session_store = session_store,
            raise_discover_failure = True,
        )

class MyConsumerMixin(object):
    def get_consumer(self, request, session_store):
        return MockConsumer(
            consumer = self,
            user_url = 'http://simonwillison.net/',
            redirect_url = 'http://url-of-openid-server/',
            session_store = session_store,
        )
    
    def set_mock_response(self, status, identity_url):
        self._mock_response = MockOpenIDResponse(status, identity_url)

class MyConsumer(MyConsumerMixin, Consumer):
    pass

class MySessionConsumer(MyConsumerMixin, SessionConsumer):
    pass

class MyCookieConsumer(MyConsumerMixin, CookieConsumer):
    pass

class MyAuthConsumer(MyConsumerMixin, AuthConsumer):
    pass

########NEW FILE########
__FILENAME__ = request_factory
from django.test import Client
from django.core.handlers.wsgi import WSGIRequest

# From http://www.djangosnippets.org/snippets/963/

class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.
    
    Usage:
    
    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})
    
    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client
    
    Once you have a request object you can pass it to any view function, 
    just as if that view had been hooked up using a URLconf.
    
    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)

########NEW FILE########
__FILENAME__ = signing_tests
from django_openid import signed
from django.conf import settings

from unittest import TestCase

class TestSignUnsign(TestCase):

    def test_sign_unsign_no_unicode(self):
        "sign/unsign functions should not accept unicode strings"
        self.assertRaises(TypeError, signed.sign, u'\u2019')
        self.assertRaises(TypeError, signed.unsign, u'\u2019')
    
    def test_sign_uses_correct_key(self):
        "If a key is provided, sign should use it; otherwise, use SECRET_KEY"
        s = 'This is a string'
        self.assertEqual(
            signed.sign(s),
            s + '.' + signed.base64_hmac(s, settings.SECRET_KEY)
        )
        self.assertEqual(
            signed.sign(s, 'sekrit'),
            s + '.' + signed.base64_hmac(s, 'sekrit')
        )
    
    def sign_is_reversible(self):
        examples = (
            'q;wjmbk;wkmb',
            '3098247529087',
            '3098247:529:087:',
            'jkw osanteuh ,rcuh nthu aou oauh ,ud du',
            u'\u2019'.encode('utf8'),
        )
        for example in examples:
            self.assert_(example != signed.sign(example))
            self.assertEqual(example, signed.unsign(utils.sign(example)))
    
    def unsign_detects_tampering(self):
        value = 'Another string'
        signed_value = signed.sign(value)
        transforms = (
            lambda s: s.upper(),
            lambda s: s + 'a',
            lambda s: 'a' + s[1:],
            lambda s: s.replace(':', ''),
        )
        self.assertEqual(value, signed.unsign(signed_value))
        for transform in transforms:
            self.assertRaises(
                signed.BadSignature, signed.unsign, transform(signed_value)
            )

class TestEncodeDecodeObject(TestCase):
    
    def test_encode_decode(self):
        objects = (
            ('a', 'tuple'),
            'a string',
            u'a unicode string \u2019',
            {'a': 'dictionary'},
        )
        for o in objects:
            self.assert_(o != signed.dumps(o))
            self.assertEqual(o, signed.loads(signed.dumps(o)))
    
    def test_decode_detects_tampering(self):
        transforms = (
            lambda s: s.upper(),
            lambda s: s + 'a',
            lambda s: 'a' + s[1:],
            lambda s: s.replace('.', ''),
        )
        value = {'foo': 'bar', 'baz': 1}
        encoded = signed.dumps(value)
        self.assertEqual(value, signed.loads(encoded))
        for transform in transforms:
            self.assertRaises(
                signed.BadSignature, signed.loads, transform(encoded)
            )

########NEW FILE########
__FILENAME__ = utils
from openid.extensions import sreg
from openid.yadis import xri
import datetime

hex_to_int = lambda s: int(s, 16)
int_to_hex = lambda i: hex(i).replace('0x', '').lower().replace('l', '')

class OpenID:
    def __init__(self, openid, issued, sreg=None):
        self.openid = openid
        self.issued = issued # datetime (used to be int(time.time()))
        self.sreg = sreg or {}
    
    def is_iname(self):
        return xri.identifierScheme(self.openid) == 'XRI'
    
    def __repr__(self):
        return '<OpenID: %s>' % self.openid
    
    def __unicode__(self):
        return self.openid
    
    @classmethod
    def from_openid_response(cls, openid_response):
        return cls(
            openid = openid_response.identity_url,
            issued = datetime.datetime.now(),
            sreg = sreg.SRegResponse.fromSuccessResponse(openid_response),
        )

"""
Convenient wrapper around Django's urlresolvers, allowing them to be used 
from normal application code.

from django.http import HttpResponse
from django_openid.request_factory import RequestFactory
from django.conf.urls.defaults import url
router = Router(
    url('^foo/$', lambda r: HttpResponse('foo'), name='foo'),
    url('^bar/$', lambda r: HttpResponse('bar'), name='bar')
)
rf = RequestFactory()
print router(rf.get('/bar/'))
"""

from django.conf.urls.defaults import patterns
from django.core import urlresolvers

class Router(object):
    def __init__(self, *urlpairs):
        self.urlpatterns = patterns('', *urlpairs)
        # for 1.0 compatibility we pass in None for urlconf_name and then
        # modify the _urlconf_module to make self hack as if its the module.
        self.resolver = urlresolvers.RegexURLResolver(r'^/', None)
        self.resolver._urlconf_module = self
    
    def handle(self, request, path_override=None):
        if path_override is not None:
            path = path_override
        else:
            path = request.path_info
        path = '/' + path # Or it doesn't work
        callback, callback_args, callback_kwargs = self.resolver.resolve(path)
        return callback(request, *callback_args, **callback_kwargs)
    
    def __call__(self, request, path_override=None):
        return self.handle(request, path_override)

########NEW FILE########
