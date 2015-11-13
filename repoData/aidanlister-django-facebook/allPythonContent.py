__FILENAME__ = auth
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
import facebook

class FacebookBackend(ModelBackend):
    """ Authenticate a facebook user. """
    def authenticate(self, fb_uid=None, fb_graphtoken=None):
        """ If we receive a facebook uid then the cookie has already been validated. """
        if fb_uid:
            user, created = User.objects.get_or_create(username=fb_uid)
            return user
        return None


class FacebookProfileBackend(ModelBackend):
    """ Authenticate a facebook user and autopopulate facebook data into the users profile. """
    def authenticate(self, fb_uid=None, fb_graphtoken=None):
        """ If we receive a facebook uid then the cookie has already been validated. """
        if fb_uid and fb_graphtoken:
            user, created = User.objects.get_or_create(username=fb_uid)
            if created:
                # It would be nice to replace this with an asynchronous request
                graph = facebook.GraphAPI(fb_graphtoken)
                me = graph.get_object('me')
                if me:
                    if me.get('first_name'): user.first_name = me['first_name']
                    if me.get('last_name'): user.last_name = me['last_name']
                    if me.get('email'): user.email = me['email']
                    user.save()
            return user
        return None

########NEW FILE########
__FILENAME__ = decorators
import facebook
from functools import update_wrapper, wraps
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.utils.decorators import available_attrs
from django.utils.http import urlquote
from django.conf import settings


def canvas_only(function=None):
    """
    Decorator ensures that a page is only accessed from within a facebook application.
    """
    def _dec(view_func):
        def _view(request, *args, **kwargs):
            # Make sure we're receiving a signed_request from facebook
            if not request.POST.get('signed_request'):
                return HttpResponseBadRequest('<h1>400 Bad Request</h1><p>Missing <em>signed_request</em>.</p>')

            # Parse the request and ensure it's valid
            signed_request = request.POST["signed_request"]
            data = facebook.parse_signed_request(signed_request, settings.FACEBOOK_SECRET_KEY)
            if data is False:
                return HttpResponseBadRequest('<h1>400 Bad Request</h1><p>Malformed <em>signed_request</em>.</p>')

            # If the user has not authorised redirect them
            if not data.get('user_id'):
                scope = getattr(settings, 'FACEBOOK_PERMS', None)
                auth_url = facebook.auth_url(settings.FACEBOOK_APP_ID, settings.FACEBOOK_CANVAS_PAGE, scope)
                markup = '<script type="text/javascript">top.location.href="%s"</script>' % auth_url
                return HttpResponse(markup)

            # Success so return the view
            return view_func(request, *args, **kwargs)
        return _view
    return _dec(function)


def facebook_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    def _passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
        if not login_url:
            from django.conf import settings
            login_url = settings.LOGIN_URL

        def decorator(view_func):
            def _wrapped_view(request, *args, **kwargs):
                if test_func(request):
                    return view_func(request, *args, **kwargs)
                path = urlquote(request.get_full_path())
                tup = login_url, redirect_field_name, path
                return HttpResponseRedirect('%s?%s=%s' % tup)
            return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)
        return decorator

    actual_decorator = _passes_test(
        lambda r: r.facebook,
        redirect_field_name=redirect_field_name
    )

    if function:
        return actual_decorator(function)
    return actual_decorator

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.contrib import auth
import facebook
import datetime


class DjangoFacebook(object):
    """ Simple accessor object for the Facebook user. """
    def __init__(self, user):
        self.user = user
        self.uid = user['uid']
        self.graph = facebook.GraphAPI(user['access_token'])


class FacebookDebugCanvasMiddleware(object):
    """ Emulates signed_request behaviour to test your applications embedding.

    This should be a raw string as is sent from facebook to the server in the POST
    data, obtained by LiveHeaders, Firebug or similar. This should initialised
    before FacebookMiddleware.
    """
    def process_request(self, request):
        cp = request.POST.copy()
        request.POST = cp
        request.POST['signed_request'] = settings.FACEBOOK_DEBUG_SIGNEDREQ
        return None


class FacebookDebugCookieMiddleware(object):
    """ Sets an imaginary cookie to make it easy to work from a development environment.

    This should be a raw string as is sent from a browser to the server, obtained by
    LiveHeaders, Firebug or similar. The middleware takes care of naming the cookie
    correctly. This should initialised before FacebookMiddleware.
    """
    def process_request(self, request):
        cookie_name = "fbs_" + settings.FACEBOOK_APP_ID
        request.COOKIES[cookie_name] = settings.FACEBOOK_DEBUG_COOKIE
        return None


class FacebookDebugTokenMiddleware(object):
    """ Forces a specific access token to be used.

    This should be used instead of FacebookMiddleware. Make sure you have
    FACEBOOK_DEBUG_UID and FACEBOOK_DEBUG_TOKEN set in your configuration.
    """
    def process_request(self, request):
        user = {
            'uid':settings.FACEBOOK_DEBUG_UID,
            'access_token':settings.FACEBOOK_DEBUG_TOKEN,
        }
        request.facebook = DjangoFacebook(user)
        return None


class FacebookMiddleware(object):
    """ Transparently integrate Django accounts with Facebook.

    If the user presents with a valid facebook cookie, then we want them to be
    automatically logged in as that user. We rely on the authentication backend
    to create the user if it does not exist.

    We do not want to persist the facebook login, so we avoid calling auth.login()
    with the rationale that if they log out via fb:login-button we want them to
    be logged out of Django also.

    We also want to allow people to log in with other backends, which means we
    need to be careful before replacing request.user.
    """

    def get_fb_user_cookie(self, request):
        """ Attempt to find a facebook user using a cookie. """
        fb_user = facebook.get_user_from_cookie(request.COOKIES,
            settings.FACEBOOK_APP_ID, settings.FACEBOOK_SECRET_KEY)
        if fb_user:
          fb_user['method'] = 'cookie'
        return fb_user

    def get_fb_user_canvas(self, request):
        """ Attempt to find a user using a signed_request (canvas). """
        fb_user = None
        if request.POST.get('signed_request'):
            signed_request = request.POST["signed_request"]
            data = facebook.parse_signed_request(signed_request, settings.FACEBOOK_SECRET_KEY)
            if data and data.get('user_id'):
                fb_user = data['user']
                fb_user['method'] = 'canvas'
                fb_user['uid'] = data['user_id']
                fb_user['access_token'] = data['oauth_token']
        return fb_user

    def get_fb_user(self, request):
        """ Return a dict containing the facebook user details, if found.

        The dict must contain the auth method, uid, access_token and any
        other information that was made available by the authentication
        method.
        """
        fb_user = None
        methods = ['get_fb_user_cookie', 'get_fb_user_canvas']
        for method in methods:
            fb_user = getattr(self, method)(request)
            if (fb_user):
                break
        return fb_user

    def process_request(self, request):
        """ Add `facebook` into the request context and attempt to authenticate the user.

        If no user was found, request.facebook will be None. Otherwise it will contain
        a DjangoFacebook object containing:
          uid: The facebook users UID
          user: Any user information made available as part of the authentication process
          graph: A GraphAPI object connected to the current user.

        An attempt to authenticate the user is also made. The fb_uid and fb_graphtoken
        parameters are passed and are available for any AuthenticationBackends.

        The user however is not "logged in" via login() as facebook sessions are ephemeral
        and must be revalidated on every request.
        """
        fb_user = self.get_fb_user(request)
        request.facebook = DjangoFacebook(fb_user) if fb_user else None

        if fb_user and request.user.is_anonymous():
            user = auth.authenticate(fb_uid=fb_user['uid'], fb_graphtoken=fb_user['access_token'])
            if user:
                user.last_login = datetime.datetime.now()
                user.save()
                request.user = user
        return None

########NEW FILE########
__FILENAME__ = facebook
from django import template
from django.conf import settings
register = template.Library()


@register.inclusion_tag('tags/facebook_load.html')
def facebook_load():
    pass

@register.tag
def facebook_init(parser, token):
    nodelist = parser.parse(('endfacebook',))
    parser.delete_first_token()
    return FacebookNode(nodelist)

class FacebookNode(template.Node):
    """ Allow code to be added inside the facebook asynchronous closure. """
    def __init__(self, nodelist):
        try:
            app_id = settings.FACEBOOK_APP_ID
        except AttributeError:
            raise template.TemplateSyntaxError, "%r tag requires FACEBOOK_APP_ID to be configured." \
                % token.contents.split()[0]
        self.app_id   = app_id
        self.nodelist = nodelist

    def render(self, context):
        t = template.loader.get_template('tags/facebook_init.html')
        code = self.nodelist.render(context)
        custom_context = context
        custom_context['code'] = code
        custom_context['app_id'] = self.app_id
        return t.render(context)

@register.simple_tag
def facebook_perms():
    return ",".join(getattr(settings, 'FACEBOOK_PERMS', []))

########NEW FILE########
