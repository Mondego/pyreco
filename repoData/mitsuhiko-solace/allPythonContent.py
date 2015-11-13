__FILENAME__ = application
# -*- coding: utf-8 -*-
"""
    solace.application
    ~~~~~~~~~~~~~~~~~~

    The WSGI application for Solace.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
from urlparse import urlparse, urlsplit, urljoin
from fnmatch import fnmatch
from functools import update_wrapper
from simplejson import dumps

from babel import UnknownLocaleError, Locale
from werkzeug import Request as RequestBase, Response, cached_property, \
     import_string, redirect, SharedDataMiddleware, url_quote, \
     url_decode
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, Forbidden
from werkzeug.routing import BuildError, RequestRedirect
from werkzeug.contrib.securecookie import SecureCookie

from solace.utils.ctxlocal import local, LocalProperty


# already resolved and imported views
_resolved_views = {}


class Request(RequestBase):
    """The request class."""

    in_api = False
    csrf_protected = False
    _locale = None
    _pulled_flash_messages = None

    #: each request might transmit up to four megs of payload that
    #: is stored in memory.  If more is transmitted, Werkzeug will
    #: abort the request with an appropriate status code.  This should
    #: not happen unless someone really tempers with the data.
    max_form_memory_size = 4 * 1024 * 1024

    def __init__(self, environ):
        RequestBase.__init__(self, environ)
        before_request_init.emit()
        self.url_adapter = url_map.bind_to_environ(self.environ)
        self.view_lang = self.match_exception = None
        try:
            self.endpoint, self.view_arguments = self.url_adapter.match()
            view_lang = self.view_arguments.pop('lang_code', None)
            if view_lang is not None:
                try:
                    self.view_lang = Locale.parse(view_lang)
                    if not has_section(self.view_lang):
                        raise UnknownLocaleError(str(self.view_lang))
                except UnknownLocaleError:
                    self.view_lang = None
                    self.match_exception = NotFound()
        except HTTPException, e:
            self.endpoint = self.view_arguments = None
            self.match_exception = e
        self.sql_queries = []
        local.request = self
        after_request_init.emit(request=self)

    current = LocalProperty('request')

    def dispatch(self):
        """Where do we want to go today?"""
        before_request_dispatch.emit(request=self)
        try:
            if self.match_exception is not None:
                raise self.match_exception
            rv = self.view(self, **self.view_arguments)
        except BadRequest, e:
            rv = get_view('core.bad_request')(self)
        except Forbidden, e:
            rv = get_view('core.forbidden')(self)
        except NotFound, e:
            rv = get_view('core.not_found')(self)
        rv = self.process_view_result(rv)
        after_request_dispatch.emit(request=self, response=rv)
        return rv

    def process_view_result(self, rv):
        """Processes a view's return value and ensures it's a response
        object.  This is automatically called by the dispatch function
        but is also handy for view decorators.
        """
        if isinstance(rv, basestring):
            rv = Response(rv, mimetype='text/html')
        elif not isinstance(rv, Response):
            rv = Response.force_type(rv, self.environ)
        return rv

    def _get_locale(self):
        """The locale of the incoming request.  If a locale is unsupported, the
        default english locale is used.  If the locale is assigned it will be
        stored in the session so that that language changes are persistent.
        """
        if self._locale is not None:
            return self._locale
        rv = self.session.get('locale')
        if rv is not None:
            rv = Locale.parse(rv)
            # we could trust the cookie here because it's signed, but we do not
            # because the configuration could have changed in the meantime.
            if not has_section(rv):
                rv = None
        if rv is None:
            rv = select_locale(self.accept_languages)
        self._locale = rv
        return rv
    def _set_locale(self, locale):
        self._locale = Locale.parse(locale)
        self.__dict__.pop('translations', None)
        self.session['locale'] = str(self._locale)
    locale = property(_get_locale, _set_locale)
    del _get_locale, _set_locale

    @cached_property
    def translations(self):
        """The translations for this request."""
        return load_translations(self.locale)

    @property
    def timezone_known(self):
        """If the JavaScript on the client set the timezone already this returns
        True, otherwise False.
        """
        return self.session.get('timezone') is not None

    @cached_property
    def tzinfo(self):
        """The timezone information."""
        offset = self.session.get('timezone')
        if offset is not None:
            return Timezone(offset)

    @cached_property
    def next_url(self):
        """Sometimes we want to redirect to different URLs back or forth.
        For example the login function uses this attribute to find out
        where it should go.

        If there is a `next` parameter on the URL or in the form data, the
        function will redirect there, if it's not there, it checks the
        referrer.

        It's usually better to use the get_redirect_target method.
        """
        return self.get_redirect_target()

    def get_localized_next_url(self, locale=None):
        """Like `next_url` but tries to go to the localized section."""
        if locale is None:
            locale = self.locale
        next_url = self.get_redirect_target()
        if next_url is None:
            return
        scheme, netloc, path, query = urlsplit(next_url)[:4]
        path = path.decode('utf-8')

        # aha. we're redirecting somewhere out of our control
        if netloc != self.host or not path.startswith(self.script_root):
            return next_url

        path = path[len(self.script_root):]
        try:
            endpoint, values = self.url_adapter.match(path)
        except NotFound, e:
            return next_url
        except RequestRedirect:
            pass
        if 'lang_code' not in values:
            return next_url

        values['lang_code'] = str(locale)
        return self.url_adapter.build(endpoint, values) + \
               (query and '?' + query or '')

    def get_redirect_target(self, invalid_targets=()):
        """Check the request and get the redirect target if possible.
        If not this function returns just `None`.  The return value of this
        function is suitable to be passed to `redirect`.
        """
        check_target = self.values.get('_redirect_target') or \
                       self.values.get('next') or \
                       self.referrer

        # if there is no information in either the form data
        # or the wsgi environment about a jump target we have
        # to use the target url
        if not check_target:
            return

        # otherwise drop the leading slash
        check_target = check_target.lstrip('/')

        root_url = self.url_root
        root_parts = urlparse(root_url)

        check_parts = urlparse(urljoin(root_url, check_target))
        check_query = url_decode(check_parts[4])

        def url_equals(to_check):
            if to_check[:4] != check_parts[:4]:
                return False
            args = url_decode(to_check[4])
            for key, value in args.iteritems():
                if check_query.get(key) != value:
                    return False
            return True

        # if the jump target is on a different server we probably have
        # a security problem and better try to use the target url.
        # except the host is whitelisted in the config
        if root_parts[:2] != check_parts[:2]:
            host = check_parts[1].split(':', 1)[0]
            for rule in settings.ALLOWED_REDIRECTS:
                if fnmatch(host, rule):
                    break
            else:
                return

        # if the jump url is the same url as the current url we've had
        # a bad redirect before and use the target url to not create a
        # infinite redirect.
        if url_equals(urlparse(self.url)):
            return

        # if the `check_target` is one of the invalid targets we also
        # fall back.
        for invalid in invalid_targets:
            if url_equals(urlparse(urljoin(root_url, invalid))):
                return

        return check_target

    @cached_property
    def user(self):
        """The current user."""
        return get_auth_system().get_user(self)

    @property
    def is_logged_in(self):
        """Is the user logged in?"""
        return self.user is not None

    @cached_property
    def view(self):
        """The view function."""
        return get_view(self.endpoint)

    @cached_property
    def session(self):
        """The active session."""
        return SecureCookie.load_cookie(self, settings.COOKIE_NAME,
                                        settings.SECRET_KEY)

    @property
    def is_behind_proxy(self):
        """Are we behind a proxy?  Accessed by Werkzeug when needed."""
        return settings.IS_BEHIND_PROXY

    def list_languages(self):
        """Lists all languages."""
        return [dict(
            name=locale.display_name,
            key=key,
            selected=self.locale == locale,
            select_url=url_for('core.set_language', locale=key),
            section_url=url_for('kb.overview', lang_code=key)
        ) for key, locale in list_languages()]

    def flash(self, message, error=False):
        """Flashes a message."""
        type = error and 'error' or 'info'
        self.session.setdefault('flashes', []).append((type, message))

    def pull_flash_messages(self):
        """Returns all flash messages.  They will be removed from the
        session at the same time.  This also pulls the messages from
        the database that are queued for the user.
        """
        msgs = self._pulled_flash_messages or []
        if self.user is not None:
            to_delete = set()
            for msg in UserMessage.query.filter_by(user=self.user).all():
                msgs.append((msg.type, msg.text))
                to_delete.add(msg.id)
            if to_delete:
                UserMessage.query.filter(UserMessage.id.in_(to_delete)).delete(synchronize_session='fetch')
                session.commit()
        if 'flashes' in self.session:
            msgs += self.session.pop('flashes')
            self._pulled_flash_messages = msgs
        return msgs


def get_view(endpoint):
    """Returns the view for the endpoint.  It will cache both positive and
    negative hits, so never pass untrusted values to it.  If a view does
    not exist, `None` is returned.
    """
    view = _resolved_views.get(endpoint)
    if view is not None:
        return view
    try:
        view = import_string('solace.views.' + endpoint)
    except (ImportError, AttributeError):
        view = import_string(endpoint, silent=True)
    _resolved_views[endpoint] = view
    return view


def json_response(message=None, html=None, error=False, login_could_fix=False,
                  **extra):
    """Returns a JSON response for the JavaScript code.  The "wire protocoll"
    is basically just a JSON object with some common attributes that are
    checked by the success callback in the JavaScript code before the handler
    processes it.

    The `error` and `login_could_fix` keys are internally used by the flashing
    system on the client.
    """
    extra.update(message=message, html=html, error=error,
                 login_could_fix=login_could_fix)
    for key, value in extra.iteritems():
        extra[key] = remote_export_primitive(value)
    return Response(dumps(extra), mimetype='application/json')


def not_logged_in_json_response():
    """Standard response that the user is not logged in."""
    return json_response(message=_(u'You have to login in order to '
                                   u'visit this page.'),
                         error=True, login_could_fix=True)


def require_admin(f):
    """Decorates a view function so that it requires a user that is
    logged in.
    """
    def decorated(request, **kwargs):
        if not request.user.is_admin:
            message = _(u'You cannot access this resource.')
            if request.is_xhr:
                return json_response(message=message, error=True)
            raise Forbidden(message)
        return f(request, **kwargs)
    return require_login(update_wrapper(decorated, f))


def require_login(f):
    """Decorates a view function so that it requires a user that is
    logged in.
    """
    def decorated(request, **kwargs):
        if not request.is_logged_in:
            if request.is_xhr:
                return not_logged_in_json_response()
            request.flash(_(u'You have to login in order to visit this page.'))
            return redirect(url_for('core.login', next=request.url))
        return f(request, **kwargs)
    return update_wrapper(decorated, f)


def iter_endpoint_choices(new, current=None):
    """Iterate over all possibilities for URL generation."""
    yield new
    if current is not None and '.' in current:
        yield current.rsplit('.', 1)[0] + '.' + new


def inject_lang_code(request, endpoint, values):
    """Returns a dict with the values for the given endpoint.  You must not alter
    the dict because it might be shared.  If the given endpoint does not exist
    `None` is returned.
    """
    rv = values
    if 'lang_code' not in rv:
        try:
            if request.url_adapter.map.is_endpoint_expecting(
                    endpoint, 'lang_code'):
                rv = values.copy()
                rv['lang_code'] = request.view_lang or str(request.locale)
        except KeyError:
            return
    return rv


def url_for(endpoint, **values):
    """Returns a URL for a given endpoint with some interpolation."""
    external = values.pop('_external', False)
    if hasattr(endpoint, 'get_url_values'):
        endpoint, values = endpoint.get_url_values(**values)
    request = Request.current
    anchor = values.pop('_anchor', None)
    assert request is not None, 'no active request'
    for endpoint_choice in iter_endpoint_choices(endpoint, request.endpoint):
        real_values = inject_lang_code(request, endpoint_choice, values)
        if real_values is None:
            continue
        try:
            url = request.url_adapter.build(endpoint_choice, real_values,
                                            force_external=external)
        except BuildError:
            continue
        view = get_view(endpoint)
        if is_exchange_token_protected(view):
            xt = get_exchange_token(request)
            url = '%s%s_xt=%s' % (url, '?' in url and '&' or '?', xt)
        if anchor is not None:
            url += '#' + url_quote(anchor)
        return url
    raise BuildError(endpoint, values, 'GET')


def save_session(request, response):
    """Saves the session to the response.  Called automatically at
    the end of a request.
    """
    if not request.in_api and request.session.should_save:
        request.session.save_cookie(response, settings.COOKIE_NAME)


def finalize_response(request, response):
    """Finalizes the response.  Applies common response processors."""
    if not isinstance(response, Response):
        response = Response.force_type(response, request.environ)
    if response.status == 200:
        response.add_etag()
        response = response.make_conditional(request)
    before_response_sent.emit(request=request, response=response)
    return response


@Request.application
def application(request):
    """The WSGI application.  The majority of the handling here happens
    in the :meth:`Request.dispatch` method and the functions that are
    connected to the request signals.
    """
    try:
        try:
            response = request.dispatch()
        except HTTPException, e:
            response = e.get_response(request.environ)
        return finalize_response(request, response)
    finally:
        after_request_shutdown.emit()


application = SharedDataMiddleware(application, {
    '/_static':     os.path.join(os.path.dirname(__file__), 'static')
})


# imported here because of possible circular dependencies
from solace import settings
from solace.urls import url_map
from solace.i18n import select_locale, load_translations, Timezone, _, \
     list_languages, has_section
from solace.auth import get_auth_system
from solace.database import session
from solace.models import UserMessage
from solace.signals import before_request_init, after_request_init, \
     before_request_dispatch, after_request_dispatch, \
     after_request_shutdown, before_response_sent
from solace.utils.remoting import remote_export_primitive
from solace.utils.csrf import get_exchange_token, is_exchange_token_protected

# remember to save the session
before_response_sent.connect(save_session)

# important because of initialization code (such as signal subscriptions)
import solace.badges

########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-
"""
    solace.auth
    ~~~~~~~~~~~

    This module implements the auth system.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
from threading import Lock
from werkzeug import import_string, redirect
from werkzeug.contrib.securecookie import SecureCookie
from datetime import datetime

from solace import settings
from solace.i18n import lazy_gettext
from solace.utils.support import UIException
from solace.utils.mail import send_email


_auth_system = None
_auth_select_lock = Lock()


def get_auth_system():
    """Return the auth system."""
    global _auth_system
    with _auth_select_lock:
        if _auth_system is None:
            _auth_system = import_string(settings.AUTH_SYSTEM)()
        return _auth_system


def refresh_auth_system():
    """Tears down the auth system after a config change."""
    global _auth_system
    with _auth_system_lock:
        _auth_system = None


def check_used_openids(identity_urls, ignored_owner=None):
    """Returns a set of all the identity URLs from the list of identity
    URLs that are already associated on the system.  If a owner is given,
    items that are owned by the given user will not show up in the result
    list.
    """
    query = _OpenIDUserMapping.query.filter(
        _OpenIDUserMapping.identity_url.in_(identity_urls)
    )
    if ignored_owner:
        query = query.filter(_OpenIDUserMapping.user != ignored_owner)
    return set([x.identity_url for x in query.all()])


class LoginUnsucessful(UIException):
    """Raised if the login failed."""


class AuthSystemBase(object):
    """The base auth system.

    Most functionality is described in the methods and properties you have
    to override for subclasses.  A special notice applies for user
    registration.

    Different auth systems may create users at different stages (first login,
    register etc.).  At that point (where the user is created in the
    database) the system has to call `after_register` and pass it the user
    (and request) object.  That method handles the confirmation mails and
    whatever else is required.  If you do not want your auth system to send
    confirmation mails you still have to call the method but tell the user
    of your class to disable registration activation in the configuration.

    `after_register` should *not* be called if the registration process
    should happen transparently for the user.  eg, the user has already
    registered somewhere else and the Solace account is created based on the
    already existing account on first login.
    """

    #: for auth systems that are managing the email externally this
    #: attributes has to set to `True`.  In that case the user will
    #: be unable to change the email from the profile.  (True for
    #: the plurk auth, possible OpenID support and more.)
    email_managed_external = False

    #: like `email_managed_external` but for the password
    password_managed_external = False

    #: set to True to indicate that this login system does not use
    #: a password.  This will also affect the standard login form
    #: and the standard profile form.
    passwordless = False

    #: if you don't want to see a register link in the user interface
    #: for this auth system, you can disable it here.
    show_register_link = True

    @property
    def can_reset_password(self):
        """You can either override this property or leave the default
        implementation that should work most of the time.  By default
        the auth system can reset the password if the password is not
        externally managed and not passwordless.
        """
        return not (self.passwordless or self.password_managed_external)

    def reset_password(self, request, user):
        if settings.REGISTRATION_REQUIRES_ACTIVATION:
            user.is_active = False
            confirmation_url = url_for('core.activate_user', email=user.email,
                                       key=user.activation_key, _external=True)
            send_email(_(u'Registration Confirmation'),
                       render_template('mails/activate_user.txt', user=user,
                                       confirmation_url=confirmation_url),
                       user.email)
            request.flash(_(u'A mail was sent to %s with a link to finish the '
                            u'registration.') % user.email)
        else:
            request.flash(_(u'You\'re registered.  You can login now.'))

    def before_register(self, request):
        """Invoked before the standard register form processing.  This is
        intended to be used to redirect to an external register URL if
        if the syncronization is only one-directional.  If this function
        returns a response object, Solace will abort standard registration
        handling.
        """

    def register(self, request):
        """Called like a view function with only the request.  Has to do the
        register heavy-lifting.  Auth systems that only use the internal
        database do not have to override this method.  Implementers that
        override this function *have* to call `after_register` to finish
        the registration of the new user.  If `before_register` is unnused
        it does not have to be called, otherwise as documented.
        """
        rv = self.before_register(request)
        if rv is not None:
            return rv

        form = RegistrationForm()
        if request.method == 'POST' and form.validate():
            user = User(form['username'], form['email'], form['password'])
            self.after_register(request, user)
            session.commit()
            if rv is not None:
                return rv
            return form.redirect('kb.overview')

        return render_template('core/register.html', form=form.as_widget())

    def after_register(self, request, user):
        """Handles activation."""
        if settings.REGISTRATION_REQUIRES_ACTIVATION:
            user.is_active = False
            confirmation_url = url_for('core.activate_user', email=user.email,
                                       key=user.activation_key, _external=True)
            send_email(_(u'Registration Confirmation'),
                       render_template('mails/activate_user.txt', user=user,
                                       confirmation_url=confirmation_url),
                       user.email)
            request.flash(_(u'A mail was sent to %s with a link to finish the '
                            u'registration.') % user.email)
        else:
            request.flash(_(u'You\'re registered.  You can login now.'))

    def get_login_form(self):
        """Return the login form to be used by `login`."""
        return StandardLoginForm()

    def before_login(self, request):
        """If this login system uses an external login URL, this function
        has to return a redirect response, otherwise None.  This is called
        before the standard form handling to allow redirecting to an
        external login URL.  This function is called by the default
        `login` implementation.

        If the actual login happens here because of a back-redirect the
        system might raise a `LoginUnsucessful` exception.
        """

    def login(self, request):
        """Like `register` just for login."""
        form = self.get_login_form()

        # some login systems require an external login URL.  For example
        # the one we use as Plurk.
        try:
            rv = self.before_login(request)
            if rv is not None:
                return rv
        except LoginUnsucessful, e:
            form.add_error(unicode(e))

        # only validate if the before_login handler did not already cause
        # an error.  In that case there is not much win in validating
        # twice, it would clear the error added.
        if form.is_valid and request.method == 'POST' and form.validate():
            try:
                rv = self.perform_login(request, **form.data)
            except LoginUnsucessful, e:
                form.add_error(unicode(e))
            else:
                session.commit()
                if rv is not None:
                    return rv
                request.flash(_(u'You are now logged in.'))
                return form.redirect('kb.overview')

        return self.render_login_template(request, form)

    def perform_login(self, request, **form_data):
        """If `login` is not overridden, this is called with the submitted
        form data and might raise `LoginUnsucessful` so signal a login
        error.
        """
        raise NotImplementedError()

    def render_login_template(self, request, form):
        """Renders the login template"""
        return render_template('core/login.html', form=form.as_widget())

    def get_edit_profile_form(self, user):
        """Returns the profile form to be used by the auth system."""
        return StandardProfileEditForm(user)

    def edit_profile(self, request):
        """Invoked like a view and does the profile handling."""
        form = self.get_edit_profile_form(request.user)

        if request.method == 'POST' and form.validate():
            request.flash(_(u'Your profile was updated'))
            form.apply_changes()
            session.commit()
            return form.redirect(form.user)

        return self.render_edit_profile_template(request, form)

    def render_edit_profile_template(self, request, form):
        """Renders the template for the profile edit page."""
        return render_template('users/edit_profile.html',
                               form=form.as_widget())

    def logout(self, request):
        """This has to logout the user again.  This method must not fail.
        If the logout requires the redirect to an external resource it
        might return a redirect response.  That resource then should not
        redirect back to the logout page, but instead directly to the
        **current** `request.next_url`.

        Most auth systems do not have to implement this method.  The
        default one calls `set_user(request, None)`.
        """
        self.set_user(request, None)

    def get_user(self, request):
        """If the user is logged in this method has to return the user
        object for the user that is logged in.  Beware: the request
        class provides some attributes such as `user` and `is_logged_in`
        you may never use from this function to avoid recursion.  The
        request object will call this function for those two attributes.

        If the user is not logged in, the return value has to be `None`.
        This method also has to check if the user was not banned.  If the
        user is banned, it has to ensure that `None` is returned and
        should ensure that future requests do not trigger this method.

        Most auth systems do not have to implement this method.
        """
        user_id = request.session.get('user_id')
        if user_id is not None:
            user = User.query.get(user_id)
            if user is not None and user.is_banned:
                del request.session['user_id']
            else:
                return user

    def set_user(self, request, user):
        """Can be used by the login function to set the user.  This function
        should only be used for auth systems internally if they are not using
        an external session.
        """
        if user is None:
            request.session.pop('user_id', None)
        else:
            user.last_login = datetime.utcnow()
            request.session['user_id'] = user.id


class InternalAuth(AuthSystemBase):
    """Authenticate against the internal database."""

    def perform_login(self, request, username, password):
        user = User.query.filter_by(username=username).first()
        if user is None:
            raise LoginUnsucessful(_(u'No user named %s') % username)
        if not user.is_active:
            raise LoginUnsucessful(_(u'The user is not yet activated.'))
        if not user.check_password(password):
            raise LoginUnsucessful(_(u'Invalid password'))
        if user.is_banned:
            raise LoginUnsucessful(_(u'The user got banned from the system.'))
        self.set_user(request, user)


# the openid support will be only available if the openid library is installed.
# otherwise we create a dummy auth system that fails upon usage.
try:
    from solace._openid_auth import OpenIDAuth
except ImportError:
    class OpenIDAuth(AuthSystemBase):
        def __init__(self):
            raise RuntimeError('python-openid library not installed but '
                               'required for openid support.')


# circular dependencies
from solace.application import url_for
from solace.models import User, _OpenIDUserMapping
from solace.database import session
from solace.i18n import _
from solace.forms import StandardLoginForm, RegistrationForm, \
     StandardProfileEditForm
from solace.templating import render_template

########NEW FILE########
__FILENAME__ = badges
# -*- coding: utf-8 -*-
"""
    solace.badges
    ~~~~~~~~~~~~~

    This module implements the badge system.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from operator import attrgetter

from solace.i18n import lazy_gettext, _
from solace.utils.remoting import RemoteObject


def try_award(event, *args):
    """Tries to avard a badge for the given event.  The events correspond
    to the `on_X` callbacks on the badges, just without the `on_` prefix.
    """
    lookup = attrgetter('on_' + event)
    for badge in badge_list:
        cb = lookup(badge)
        if cb is None:
            continue
        user = cb(*args)
        if user is not None:
            if isinstance(user, tuple):
                user, payload = user
            else:
                payload = None
            if badge.single_awarded and badge in user.badges:
                continue
            user._badges.append(UserBadge(badge, payload))
            # inactive or banned users don't get messages.
            if user.is_active and not user.is_banned:
                UserMessage(user, _(u'You earned the “%s” badge') % badge.name)


_numeric_levels = dict(zip(('bronce', 'silver', 'gold', 'platin'),
                           range(4)))


class Badge(RemoteObject):
    """Represents a badge.

    It can react to the following events::

        on_vote = lambda user, post, delta
        on_accept = lambda user, post, answer
        on_reply = lambda user, post
        on_new_topic = lambda user, topic
        on_edit = lambda user, post
    """

    remote_object_type = 'solace.badge'
    public_fields = ('level', 'identifier', 'name', 'description')

    def __init__(self, level, identifier, name, description=None,
                 single_awarded=False,
                 on_vote=None, on_accept=None, on_reply=None,
                 on_new_topic=None, on_edit=None):
        assert level in ('bronce', 'silver', 'gold', 'platin')
        assert len(identifier) <= 30
        self.level = level
        self.identifier = identifier
        self.name = name
        self.single_awarded = single_awarded
        self.description = description
        self.on_vote = on_vote
        self.on_accept = on_accept
        self.on_reply = on_reply
        self.on_new_topic = on_new_topic
        self.on_edit = on_edit

    @property
    def numeric_level(self):
        return _numeric_levels[self.level]

    def get_url_values(self):
        return 'badges.show_badge', {'identifier': self.identifier}

    def __repr__(self):
        return '<%s \'%s\' (%s)>' % (
            type(self).__name__,
            self.name.encode('utf-8'),
            ('bronce', 'silver', 'gold', 'platin')[self.numeric_level]
        )


def _try_award_special_answer(post, badge, votes_required):
    """Helper for nice and good answer."""
    pid = str(post.id)
    user = post.author
    for user_badge in user._badges:
        if user_badge.badge == badge and \
           user_badge.payload == pid:
            return
    if post.is_answer and post.votes >= votes_required:
        return user, pid


def _try_award_self_learner(post):
    """Helper for the self learner badge."""
    pid = str(post.id)
    user = post.author
    for user_badge in user._badges:
        if user_badge.badge == SELF_LEARNER and \
           user_badge.payload == pid:
            return
    if post.is_answer and post.author == post.topic.author \
       and post.votes >= 3:
        return user, pid


def _try_award_reversal(post):
    """Helper for the reversal badge."""
    pid = str(post.id)
    user = post.author
    for user_badge in user._badges:
        if user_badge.badge == REVERSAL and \
           user_badge.payload == pid:
            return
    if post.is_answer and post.votes >= 20 and \
       post.topic.votes <= -5:
        return user, pid


CRITIC = Badge('bronce', 'critic', lazy_gettext(u'Critic'),
    lazy_gettext(u'First down vote'),
    single_awarded=True,
    on_vote=lambda user, post, delta:
        user if delta < 0 and user != post.author else None
)

SELF_CRITIC = Badge('silver', 'self-critic', lazy_gettext(u'Self-Critic'),
    lazy_gettext(u'First downvote on own reply or question'),
    single_awarded=True,
    on_vote=lambda user, post, delta:
        user if delta < 0 and user == post.author else None
)

EDITOR = Badge('bronce', 'editor', lazy_gettext(u'Editor'),
    lazy_gettext(u'First edited post'),
    single_awarded=True,
    on_edit=lambda user, post: user
)

INQUIRER = Badge('bronce', 'inquirer', lazy_gettext(u'Inquirer'),
    lazy_gettext(u'First asked question'),
    single_awarded=True,
    on_new_topic=lambda user, topic: user
)

TROUBLESHOOTER = Badge('silver', 'troubleshooter',
    lazy_gettext(u'Troubleshooter'),
    lazy_gettext(u'First answered question'),
    single_awarded=True,
    on_accept=lambda user, topic, post: post.author if post else None
)

NICE_ANSWER = Badge('bronce', 'nice-answer', lazy_gettext(u'Nice Answer'),
    lazy_gettext(u'Answer was upvoted 10 times'),
    on_accept=lambda user, topic, post: _try_award_special_answer(post,
        NICE_ANSWER, 10) if post else None,
    on_vote=lambda user, post, delta: _try_award_special_answer(post,
        NICE_ANSWER, 10)
)

GOOD_ANSWER = Badge('silver', 'good-answer', lazy_gettext(u'Good Answer'),
    lazy_gettext(u'Answer was upvoted 25 times'),
    on_accept=lambda user, topic, post: _try_award_special_answer(post,
        GOOD_ANSWER, 25) if post else None,
    on_vote=lambda user, post, delta: _try_award_special_answer(post,
        GOOD_ANSWER, 25)
)

GREAT_ANSWER = Badge('gold', 'great-answer', lazy_gettext(u'Great Answer'),
    lazy_gettext(u'Answer was upvoted 75 times'),
    on_accept=lambda user, topic, post: _try_award_special_answer(post,
        GOOD_ANSWER, 75) if post else None,
    on_vote=lambda user, post, delta: _try_award_special_answer(post,
        GOOD_ANSWER, 75)
)

UNIQUE_ANSWER = Badge('platin', 'unique-answer', lazy_gettext(u'Unique Answer'),
    lazy_gettext(u'Answer was upvoted 150 times'),
    on_accept=lambda user, topic, post: _try_award_special_answer(post,
        GOOD_ANSWER, 150) if post else None,
    on_vote=lambda user, post, delta: _try_award_special_answer(post,
        GOOD_ANSWER, 150)
)

REVERSAL = Badge('gold', 'reversal', lazy_gettext(u'Reversal'),
    lazy_gettext(u'Provided answer of +20 score to a question of -5 score'),
    on_accept=lambda user, topic, post: _try_award_reversal(post) if post else None,
    on_vote=lambda user, post, delta: _try_award_reversal(post)
)

SELF_LEARNER = Badge('silver', 'self-learner', lazy_gettext(u'Self-Learner'),
    lazy_gettext(u'Answered your own question with at least 4 upvotes'),
    on_accept=lambda user, topic, post: _try_award_self_learner(post) if post else None,
    on_vote=lambda user, post, delta: _try_award_self_learner(post)
)


#: list of all badges
badge_list = [CRITIC, EDITOR, INQUIRER, TROUBLESHOOTER, NICE_ANSWER,
              GOOD_ANSWER, SELF_LEARNER, SELF_CRITIC, GREAT_ANSWER,
              UNIQUE_ANSWER, REVERSAL]

#: all the badges by key
badges_by_id = dict((x.identifier, x) for x in badge_list)


# circular dependencies
from solace.models import UserBadge, UserMessage

########NEW FILE########
__FILENAME__ = database
# -*- coding: utf-8 -*-
"""
    solace.database
    ~~~~~~~~~~~~~~~

    This module defines lower-level database support.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
import sys
import time
from threading import Lock
from datetime import datetime
from babel import Locale
from sqlalchemy.types import TypeDecorator
from sqlalchemy.engine.url import make_url
from sqlalchemy.interfaces import ConnectionProxy
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.interfaces import SessionExtension, MapperExtension, \
     EXT_CONTINUE
from sqlalchemy.util import to_list
from sqlalchemy import String, orm, sql, create_engine, MetaData


_engine = None
_engine_lock = Lock()


# the best timer for the platform. on windows systems we're using clock
# for timing which has a higher resolution.
if sys.platform == 'win32':
    _timer = time.clock
else:
    _timer = time.time


def get_engine():
    """Creates or returns the engine."""
    global _engine
    with _engine_lock:
        if _engine is None:
            options = {'echo': settings.DATABASE_ECHO,
                       'convert_unicode': True}
            if settings.TRACK_QUERIES:
                options['proxy'] = ConnectionQueryTrackingProxy()
            uri = make_url(settings.DATABASE_URI)

            # if mysql is the database engine and no connection encoding is
            # provided we set it to the mysql charset (defaults to utf8)
            # and set up a mysql friendly pool
            if uri.drivername == 'mysql':
                uri.query.setdefault('charset', 'utf8')
                options['pool_recycle'] = settings.MYSQL_POOL_RECYCLE

            _engine = create_engine(uri, **options)
        return _engine


def refresh_engine():
    """Gets rid of the existing engine.  Useful for unittesting, use with care.
    Do not call this function if there are multiple threads accessing the
    engine.  Only do that in single-threaded test environments or console
    sessions.
    """
    global _engine
    with _engine_lock:
        session.remove()
        if _engine is not None:
            _engine.dispose()
        _engine = None


def atomic_add(obj, column, delta, expire=False):
    """Performs an atomic add (or subtract) of the given column on the
    object.  This updates the object in place for reflection but does
    the real add on the server to avoid race conditions.  This assumes
    that the database's '+' operation is atomic.

    If `expire` is set to `True`, the value is expired and reloaded instead
    of added of the local value.  This is a good idea if the value should
    be used for reflection.
    """
    sess = orm.object_session(obj) or session
    mapper = orm.object_mapper(obj)
    pk = mapper.primary_key_from_instance(obj)
    assert len(pk) == 1, 'atomic_add not supported for classes with ' \
                         'more than one primary key'

    val = orm.attributes.get_attribute(obj, column)
    if expire:
        dict_ = orm.attributes.instance_dict(obj)
        orm.attributes.instance_state(obj).expire_attributes(dict_, [column])
    else:
        orm.attributes.set_committed_value(obj, column, val + delta)

    table = mapper.tables[0]
    stmt = sql.update(table, mapper.primary_key[0] == pk[0], {
        column:     table.c[column] + delta
    })
    sess.execute(stmt)


def mapper(model, table, **options):
    """A mapper that hooks in standard extensions."""
    extensions = to_list(options.pop('extension', None), [])
    extensions.append(SignalTrackingMapperExtension())
    options['extension'] = extensions
    return orm.mapper(model, table, **options)


class ConnectionQueryTrackingProxy(ConnectionProxy):
    """A proxy that if enabled counts the queries."""

    def cursor_execute(self, execute, cursor, statement, parameters,
                       context, executemany):
        before_cursor_executed.emit(cursor=self, statement=statement,
                                    parameters=parameters)
        start = _timer()
        try:
            return execute(cursor, statement, parameters, context)
        finally:
            after_cursor_executed.emit(cursor=self, statement=statement,
                                       parameters=parameters,
                                       time=_timer() - start)


class SignalTrackingMapperExtension(MapperExtension):
    """Remembers model changes for the session commit code."""

    def after_delete(self, mapper, connection, instance):
        return self._record(instance, 'delete')

    def after_insert(self, mapper, connection, instance):
        return self._record(instance, 'insert')

    def after_update(self, mapper, connection, instance):
        return self._record(instance, 'update')

    def _record(self, model, operation):
        pk = tuple(orm.object_mapper(model).primary_key_from_instance(model))
        orm.object_session(model)._model_changes[pk] = (model, operation)
        return EXT_CONTINUE


class SignalEmittingSessionExtension(SessionExtension):
    """Emits signals the mapper extension accumulated."""

    def before_commit(self, session):
        d = session._model_changes
        if d:
            before_models_committed.emit(changes=d.values())
        return EXT_CONTINUE

    def after_commit(self, session):
        d = session._model_changes
        if d:
            after_models_committed.emit(changes=d.values())
            d.clear()
        return EXT_CONTINUE

    def after_rollback(self, session):
        session._model_changes.clear()
        return EXT_CONTINUE


class SignalTrackingSession(Session):
    """A session that tracks signals for later"""

    def __init__(self):
        extension = [SignalEmittingSessionExtension()]
        Session.__init__(self, get_engine(), autoflush=True,
                         autocommit=False, extension=extension)
        self._model_changes = {}


class LocaleType(TypeDecorator):
    """A locale in the database."""

    impl = String

    def __init__(self):
        TypeDecorator.__init__(self, 10)

    def process_bind_param(self, value, dialect):
        if value is None:
            return
        return unicode(str(value))

    def process_result_value(self, value, dialect):
        if value is not None:
            return Locale.parse(value)

    def is_mutable(self):
        return False


class BadgeType(TypeDecorator):
    """Holds a badge."""

    impl = String

    def __init__(self):
        TypeDecorator.__init__(self, 30)

    def process_bind_param(self, value, dialect):
        if value is None:
            return
        return value.identifier

    def process_result_value(self, value, dialect):
        if value is not None:
            from solace.badges import badges_by_id
            return badges_by_id.get(value)

    def is_mutable(self):
        return False


metadata = MetaData()
session = orm.scoped_session(SignalTrackingSession)


def init():
    """Initializes the database."""
    import solace.schema
    engine = get_engine()
    if engine.name == 'mysql':
        for table in metadata.tables.itervalues():
            table.kwargs.update(mysql_engine=settings.MYSQL_ENGINE,
                                mysql_charset=settings.MYSQL_TABLE_CHARSET)
    metadata.create_all(bind=engine)


def drop_tables():
    """Drops all tables again."""
    import solace.schema
    metadata.drop_all(bind=get_engine())


def add_query_debug_headers(request, response):
    """Add headers with the SQL info."""
    if settings.TRACK_QUERIES:
        count = len(request.sql_queries)
        sql_time = 0.0
        for stmt, param, time in request.sql_queries:
            sql_time += time
        response.headers['X-SQL-Query-Count'] = str(count)
        response.headers['X-SQL-Query-Time'] = str(sql_time)


def request_track_query(cursor, statement, parameters, time):
    """If there is an active request, it logs the query on it."""
    if settings.TRACK_QUERIES:
        from solace.application import Request
        request = Request.current
        if request is not None:
            request.sql_queries.append((statement, parameters, time))


# make sure the session is removed at the end of the request and that
# query logging for the request works.
from solace.signals import after_request_shutdown, before_response_sent, \
     after_cursor_executed, before_cursor_executed, before_models_committed, \
     after_models_committed
after_request_shutdown.connect(session.remove)
before_response_sent.connect(add_query_debug_headers)
after_cursor_executed.connect(request_track_query)


# circular dependencies
from solace import settings

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
"""
    solace.forms
    ~~~~~~~~~~~~

    The forms for the kb and core views.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import urlparse
from solace import settings
from solace.utils import forms
from solace.i18n import lazy_gettext, _, ngettext
from solace.models import Topic, Post, Comment, User


def is_valid_email(form, value):
    """Due to stupid rules in emails, we just check if there is an
    at-sign in the email and that it's not too long.
    """
    if '@' not in value or len(value) > 200:
        raise forms.ValidationError(_('Invalid email address'))


def is_valid_username(form, value):
    """Checks if the value is a valid username."""
    if len(value) > 40:
        raise forms.ValidationError(_(u'The username is too long.'))
    if '/' in value:
        raise forms.ValidationError(_(u'The username may not contain '
                                      u'slashes.'))
    if value[:1] == '.' or value[-1:] == '.':
        raise forms.ValidationError(_(u'The username may not begin or '
                                      u'end with a dot.'))
    if ' ' in value:
        raise forms.ValidationError(_(u'The username may not contain '
                                      u'spaces.'))


def is_http_url(form, value):
    """Checks if the value is a HTTP URL."""
    scheme, netloc = urlparse.urlparse(value)[:2]
    if scheme not in ('http', 'https') or not netloc:
        raise forms.ValidationError(_(u'A valid HTTP URL is required.'))


class StandardLoginForm(forms.Form):
    """Used to log in users."""
    username = forms.TextField(lazy_gettext(u'Username'), required=True)
    password = forms.TextField(lazy_gettext(u'Password'), required=True,
                               widget=forms.PasswordInput)

    def __init__(self, initial=None, action=None, request=None):
        forms.Form.__init__(self, initial, action, request)
        self.auth_system = get_auth_system()
        if self.auth_system.passwordless:
            del self.fields['password']


class OpenIDLoginForm(forms.Form):
    """Used to log in users with the OpenID auth system."""
    openid_identifier = forms.TextField(lazy_gettext(u'OpenID'), required=True)


class RegistrationForm(forms.Form):
    """Used to register the user."""
    username = forms.TextField(lazy_gettext(u'Username'), required=True,
                               validators=[is_valid_username])
    password = forms.TextField(lazy_gettext(u'Password'),
                               widget=forms.PasswordInput)
    password_repeat = forms.TextField(lazy_gettext(u'Password (repeat)'),
                                      widget=forms.PasswordInput)
    email = forms.TextField(lazy_gettext(u'E-Mail'), required=True,
                            validators=[is_valid_email])

    @property
    def captcha_protected(self):
        """We're protected if the config says so."""
        return settings.RECAPTCHA_ENABLE

    def validate_username(self, value):
        user = User.query.filter_by(username=value).first()
        if user is not None:
            raise forms.ValidationError(_('This username is already in use.'))

    def context_validate(self, data):
        password = data.get('password')
        password_repeat = data.get('password_repeat')
        if password != password_repeat:
            raise forms.ValidationError(_(u'The two passwords do not match.'))


class OpenIDRegistrationForm(forms.Form):
    """Used to register the user."""
    username = forms.TextField(lazy_gettext(u'Username'), required=True,
                               validators=[is_valid_username])
    email = forms.TextField(lazy_gettext(u'E-Mail'), required=True,
                            validators=[is_valid_email])

    @property
    def captcha_protected(self):
        """We're protected if the config says so."""
        return settings.RECAPTCHA_ENABLE

    def validate_username(self, value):
        user = User.query.filter_by(username=value).first()
        if user is not None:
            raise forms.ValidationError(_('This username is already in use.'))


class ResetPasswordForm(forms.Form):
    """Resets a password."""
    username = forms.TextField(lazy_gettext(u'Username'))
    email = forms.TextField(lazy_gettext(u'E-Mail'), validators=[is_valid_email])

    @property
    def captcha_protected(self):
        """We're protected if the config says so."""
        return settings.RECAPTCHA_ENABLE

    def __init__(self, initial=None, action=None, request=None):
        forms.Form.__init__(self, initial, action, request)
        self.user = None

    def _check_active(self, user):
        if not user.is_active:
            raise forms.ValidationError(_(u'The user was not yet activated.'))

    def validate_username(self, username):
        if not username:
            return
        user = User.query.filter_by(username=username).first()
        if user is None:
            raise forms.ValidationError(_(u'No user named “%s” found.') % username)
        self._check_active(user)
        self.user = user

    def validate_email(self, email):
        if not email:
            return
        user = User.query.filter_by(email=email).first()
        if user is None:
            raise forms.ValidationError(_(u'No user with that e-mail address found.'))
        self._check_active(user)
        self.user = user

    def context_validate(self, data):
        has_username = bool(data['username'])
        has_email = bool(data['email'])
        if not has_username and not has_email:
            raise forms.ValidationError(_(u'Either username or e-mail address '
                                          u' is required.'))
        if has_username and has_email:
            raise forms.ValidationError(_(u'You have to provide either a username '
                                          u'or an e-mail address, not both.'))


class ProfileEditForm(forms.Form):
    """Used to change profile details."""
    real_name = forms.TextField(lazy_gettext(u'Real name'))
    email = forms.TextField(lazy_gettext(u'E-Mail'), required=True,
                            validators=[is_valid_email])

    def __init__(self, user, initial=None, action=None, request=None):
        self.user = user
        self.auth_system = get_auth_system()
        if user is not None:
            initial = forms.fill_dict(initial, real_name=user.real_name)
            if not self.auth_system.email_managed_external:
                initial['email'] = user.email
        forms.Form.__init__(self, initial, action, request)
        if self.auth_system.email_managed_external:
            del self.fields['email']

    def apply_changes(self):
        if 'email' in self.data:
            self.user.email = self.data['email']
        self.user.real_name = self.data['real_name']


class StandardProfileEditForm(ProfileEditForm):
    """Used to change profile details for the basic auth systems."""
    password = forms.TextField(lazy_gettext(u'Password'),
                               widget=forms.PasswordInput)
    password_repeat = forms.TextField(lazy_gettext(u'Password (repeat)'),
                                      widget=forms.PasswordInput)

    def __init__(self, user, initial=None, action=None, request=None):
        ProfileEditForm.__init__(self, user, initial, action, request)
        if self.auth_system.passwordless or \
           self.auth_system.password_managed_external:
            del self.fields['password']
            del self.fields['password_repeat']

    def context_validate(self, data):
        password = data.get('password')
        password_repeat = data.get('password_repeat')
        if password != password_repeat:
            raise forms.ValidationError(_(u'The two passwords do not match.'))

    def apply_changes(self):
        super(StandardProfileEditForm, self).apply_changes()
        password = self.data.get('password')
        if password:
            self.user.set_password(password)


class QuestionForm(forms.Form):
    """The form for new topics and topic editing."""
    title = forms.TextField(
        lazy_gettext(u'Title'), required=True, max_length=100,
        messages=dict(
            required=lazy_gettext(u'You have to provide a title.')),
        help_text=lazy_gettext(u'Type your question'))
    text = forms.TextField(
        lazy_gettext(u'Text'), required=True, max_length=20000,
        widget=forms.Textarea, messages=dict(
            required=lazy_gettext(u'You have to provide a text.')),
        help_text=lazy_gettext(u'Describe your problem'))
    tags = forms.CommaSeparated(
        forms.TagField(), lazy_gettext(u'Tags'), max_size=10,
        messages=dict(too_big=lazy_gettext(u'You attached too many tags. '
                                           u'You may only use 10 tags.')))

    def __init__(self, topic=None, revision=None, initial=None, action=None,
                 request=None):
        self.topic = topic
        self.revision = revision
        if topic is not None:
            text = (revision or topic.question).text
            initial = forms.fill_dict(initial, title=topic.title,
                                      text=text, tags=[x.name for x in topic.tags])
        forms.Form.__init__(self, initial, action, request)

    def create_topic(self, view_lang=None, user=None):
        """Creates a new topic."""
        if view_lang is None:
            view_lang = self.request.view_lang
        if user is None:
            user = self.request.user
        topic = Topic(view_lang, self['title'], self['text'], user)
        topic.bind_tags(self['tags'])
        return topic

    def save_changes(self, user=None):
        assert self.topic is not None
        self.topic.title = self['title']
        self.topic.bind_tags(self['tags'])
        if user is None:
            user = self.request.user
        self.topic.question.edit(self['text'], user)


class ReplyForm(forms.Form):
    """A form for new replies."""
    text = forms.TextField(
        lazy_gettext(u'Text'), required=True, max_length=10000,
        widget=forms.Textarea,
        help_text=lazy_gettext(u'Write your reply and answer the question'))

    def __init__(self, topic=None, post=None, revision=None,
                 initial=None, action=None):
        if post is not None:
            assert topic is None
            topic = post.topic
            self.post = post
            initial = forms.fill_dict(initial, text=(revision or post).text)
        else:
            self.post = None
        self.topic = topic
        self.revision = revision
        forms.Form.__init__(self, initial, action)

    def create_reply(self, user=None):
        if user is None:
            user = self.request.user
        return Post(self.topic, user, self['text'])

    def save_changes(self, user=None):
        assert self.post is not None
        if user is None:
            user = self.request.user
        self.post.edit(self['text'], user)


class CommentForm(forms.Form):
    """A form for new comments."""
    text = forms.TextField(
        lazy_gettext(u'Text'), required=True, max_length=2000,
        widget=forms.Textarea)

    def __init__(self, post, initial=None, action=None):
        forms.Form.__init__(self, initial, action)
        self.post = post

    def create_comment(self, user=None):
        if user is None:
            user = self.request.user
        return Comment(self.post, user, self['text'])


class BanUserForm(forms.Form):
    """Used to ban new users."""
    username = forms.TextField(lazy_gettext(u'Username'), required=True)

    def validate_username(self, value):
        user = User.query.filter_by(username=value).first()
        if user is None:
            raise forms.ValidationError(_(u'No such user.'))
        if self.request is not None and \
           self.request.user == user:
            raise forms.ValidationError(_(u'You cannot ban yourself.'))
        self.user = user


class EditUserRedirectForm(forms.Form):
    """Redirects to a user edit page."""
    username = forms.TextField(lazy_gettext(u'Username'), required=True)

    def validate_username(self, value):
        user = User.query.filter_by(username=value).first()
        if user is None:
            raise forms.ValidationError(_(u'No such user.'))
        self.user = user


class EditUserForm(ProfileEditForm):
    """Like the profile form."""
    username = forms.TextField(lazy_gettext(u'Username'))
    is_admin = forms.BooleanField(lazy_gettext(u'Administrator'),
        help_text=lazy_gettext(u'Enable if this user is an admin.'))
    openid_logins = forms.LineSeparated(forms.TextField(validators=[is_http_url]),
                                        lazy_gettext(u'Associated OpenID Identities'))

    def __init__(self, user, initial=None, action=None, request=None):
        if user is not None:
            initial = forms.fill_dict(initial, username=user.username,
                                      is_admin=user.is_admin,
                                      openid_logins=sorted(user.openid_logins))
        ProfileEditForm.__init__(self, user, initial, action, request)

    def validate_is_admin(self, value):
        if not value and self.request and self.request.user == self.user:
            raise forms.ValidationError(u'You cannot remove your own '
                                        u'admin rights.')

    def validate_openid_logins(self, value):
        ids_to_check = set(value) - set(self.user.openid_logins)
        in_use = check_used_openids(ids_to_check, self.user)
        if in_use:
            count = len(in_use)
            message = ngettext(u'The following %(count)d URL is already '
                               u'associated to a different user: %(urls)s',
                               u'The following %(count)d URLs are already '
                               u'associated to different users: %(urls)s',
                               count) % dict(count=count,
                                             urls=u', '.join(sorted(in_use)))
            raise forms.ValidationError(message)

    def apply_changes(self):
        super(EditUserForm, self).apply_changes()
        self.user.username = self.data['username']
        self.user.is_admin = self.data['is_admin']
        self.user.bind_openid_logins(self.data['openid_logins'])


from solace.auth import get_auth_system, check_used_openids

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
    solace.models
    ~~~~~~~~~~~~~

    The high-level models are implemented in this module.  This also
    covers denormlization for columns.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re
import string
import hmac
from math import log
from random import randrange, choice
from hashlib import sha1, md5
from itertools import chain
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import relation, backref, synonym, Query, \
     dynamic_loader, synonym, eagerload
from sqlalchemy.orm.interfaces import AttributeExtension
from sqlalchemy.ext.associationproxy import association_proxy
from werkzeug import escape, ImmutableList, ImmutableDict, cached_property
from babel import Locale

from solace import settings
from solace.database import atomic_add, mapper
from solace.utils.formatting import format_creole
from solace.utils.remoting import RemoteObject
from solace.database import session
from solace.schema import users, topics, posts, votes, comments, \
     post_revisions, tags, topic_tags, user_activities, user_badges, \
     user_messages, openid_user_mapping


_paragraph_re = re.compile(r'(?:\r?\n){2,}')
_key_chars = unicode(string.letters + string.digits)


def random_key(length):
    """Generates a random key for activation and password reset."""
    return u''.join(choice(_key_chars) for x in xrange(length))


def random_password(length=8):
    """Generate a pronounceable password."""
    consonants = 'bcdfghjklmnprstvwz'
    vowels = 'aeiou'
    return u''.join([choice(consonants) +
                     choice(vowels) +
                     choice(consonants + vowels) for _
                     in xrange(length // 3 + 1)])[:length]


def simple_repr(f):
    """Implements a simple class repr."""
    def __repr__(self):
        try:
            val = f(self)
            if isinstance(val, unicode):
                val = val.encode('utf-8')
        except Exception:
            val = '???'
        return '<%s %s>' % (type(self).__name__, val)
    return __repr__


class TextRendererMixin(object):
    """Mixin that renders the text to `rendered_text` when set.  Combine
    with a synonym column mapping for `text` to `_text`.
    """

    render_text_inline = False

    def _get_text(self):
        return self._text

    def _set_text(self, value):
        self._text = value
        self.rendered_text = format_creole(value, inline=self.render_text_inline)

    text = property(_get_text, _set_text)
    del _get_text, _set_text


class UserQuery(Query):
    """Adds extra query methods for users."""

    def by_openid_login(self, identity_url):
        """Filters by open id identity URL."""
        ss = select([openid_user_mapping.c.user_id],
                    openid_user_mapping.c.identity_url == identity_url)
        return self.filter(User.id.in_(ss))

    def active_in(self, locale):
        """Only return users that are active in the given locale."""
        ua = user_activities.c
        return self.filter(User.id.in_(select([ua.user_id],
                                              ua.locale == str(locale))))


class User(RemoteObject):
    """Represents a user on the system."""
    query = session.query_property(UserQuery)

    remote_object_type = 'solace.user'
    public_fields = ('id', 'username', 'upvotes', 'downvotes',
                     'reputation', 'real_name', 'is_admin', 'active_in',
                     'is_moderator', ('badges', 'get_badges_with_count'))

    def __init__(self, username, email, password=None, is_admin=False):
        self.username = username
        self.email = email
        self.pw_hash = None
        self.upvotes = self.downvotes = self.reputation = \
            self.bronce_badges = self.silver_badges = \
            self.gold_badges = self.platin_badges = 0
        self.real_name = u''
        self.is_admin = is_admin
        self.is_active = True
        self.is_banned = False
        self.last_login = None
        if password is not None:
            self.set_password(password)
        session.add(self)

    badges = association_proxy('_badges', 'badge')
    openid_logins = association_proxy('_openid_logins', 'identity_url')

    def bind_openid_logins(self, logins):
        """Rebinds the openid logins."""
        currently_attached = set(self.openid_logins)
        new_logins = set(logins)
        self.openid_logins.difference_update(
            currently_attached.difference(new_logins))
        self.openid_logins.update(
            new_logins.difference(currently_attached))

    def _get_active(self):
        return self.activation_key is None
    def _set_active(self, val):
        if val:
            self.activation_key = None
        else:
            self.activation_key = random_key(10)
    is_active = property(_get_active, _set_active)
    del _get_active, _set_active

    @property
    def is_moderator(self):
        """Does this user have moderation rights?"""
        return self.is_admin or self.reputation >= \
            settings.REPUTATION_MAP['IS_MODERATOR']

    @property
    def display_name(self):
        return self.real_name or self.username

    def get_avatar_url(self, size=80):
        """The URL to the avatar."""
        assert 8 < size < 256, 'unsupported dimensions'
        return '%s/%s?d=%s&size=%d' % (
            settings.GRAVATAR_URL.rstrip('/'),
            md5(self.email.lower()).hexdigest(),
            settings.GRAVATAR_FALLBACK,
            size
        )

    avatar_url = property(get_avatar_url)

    def get_url_values(self):
        return 'users.profile', dict(username=self.username)

    def upvote(self, obj):
        """Votes a post or topic up."""
        obj._set_vote(self, 1)

    def downvote(self, obj):
        """Votes a post or topic down."""
        obj._set_vote(self, -1)

    def unvote(self, obj):
        """Removes the vote from the post or topic."""
        obj._set_vote(self, 0)

    def has_upvoted(self, obj):
        """Has the user upvoted the object?"""
        return obj._get_vote(self) > 0

    def has_downvoted(self, obj):
        """Has the user upvoted the object?"""
        return obj._get_vote(self) < 0

    def has_not_voted(self, obj):
        """Has the user not yet voted on his object?"""
        return obj._get_vote(self) == 0

    def pull_votes(self, posts):
        """Pulls in the vote-status of the user for all the posts.
        This reduces the number of queries emitted.
        """
        if not hasattr(self, '_vote_cache'):
            self._vote_cache = {}
        to_pull = set()
        for post in posts:
            if post.id not in self._vote_cache:
                to_pull.add(post.id)
        if to_pull:
            votes = _Vote.query.filter(
                (_Vote.post_id.in_(to_pull)) &
                (_Vote.user == self)
            ).all()
            for vote in votes:
                self._vote_cache[vote.post_id] = vote.delta
                to_pull.discard(vote.post_id)
            self._vote_cache.update((x, 0) for x in to_pull)

    @property
    def password_reset_key(self):
        """The key that is needed to reset the password.  The key is created
        from volatile information and is automatically invalidated when one
        of the following things change:

        - the user was logged in
        - the password was changed
        - the email address was changed
        - the real name was changed
        """
        mac = hmac.new(settings.SECRET_KEY)
        mac.update(str(self.pw_hash))
        mac.update(self.email.encode('utf-8'))
        if self.real_name:
            mac.update(self.real_name.encode('utf-8'))
        mac.update(str(self.last_login))
        return mac.hexdigest()

    def check_password(self, password):
        """Checks the *internally* stored password against the one supplied.
        If an external authentication system is used that method is useless.
        """
        if self.pw_hash is None:
            return False
        salt, pwhash = self.pw_hash.split('$', 1)
        check = sha1('%s$%s' % (salt, password.encode('utf-8'))).hexdigest()
        return check == pwhash

    def set_password(self, password):
        """Sets the *internal* password to a new one."""
        salt = randrange(1000, 10000)
        self.pw_hash = '%s$%s' % (salt, sha1('%s$%s' % (
            salt,
            password.encode('utf-8')
        )).hexdigest())

    def set_random_password(self):
        """Sets a random password and returns it."""
        password = random_password()
        self.set_password(password)
        return password

    def can_edit(self, post):
        """Is this used allowed to edit the given post?"""
        if self.is_admin:
            return True
        if post.author == self:
            return True
        return self.reputation >= \
                settings.REPUTATION_MAP['EDIT_OTHER_POSTS']

    def can_accept_as_answer(self, post):
        """Can the user accept the given post as answer?"""
        if self.is_admin:
            return True
        if post.topic.author == self:
            return True
        if post.author == self:
            return self.reputation >= \
                settings.REPUTATION_MAP['ACCEPT_OWN_ANSWERS']
        return self.reputation >= \
                settings.REPUTATION_MAP['ACCEPT_OTHER_ANSWERS']

    def can_unaccept_as_answer(self, post):
        """Can the user unaccept the given post as answer?"""
        if self.is_admin:
            return True
        if post.topic.author == self:
            return True
        return self.reputation >= \
            settings.REPUTATION_MAP['UNACCEPT_ANSWER']

    def touch_activity(self, locale, points):
        """Touches the activity of the user for the given locale."""
        if not hasattr(self, '_activity_cache'):
            self._activity_cache = {}
        activity = self._activity_cache.get(locale)
        if activity is None:
            activity = _UserActivity.query.filter_by(
                user=self, locale=locale).first()
            if activity is None:
                activity = _UserActivity(self, locale)
            self._activity_cache[locale] = activity
        atomic_add(activity, 'counter', points)
        activity.last_activity = datetime.utcnow()

    @property
    def activities(self):
        """A immutable dict of all the user's activities by lang."""
        if not hasattr(self, '_activity_cache'):
            self._activity_cache = d = {}
            activities = _UserActivity.query.filter_by(user=self).all()
            for activity in activities:
                d[activity.locale] = activity
        return ImmutableDict(self._activity_cache)

    @property
    def active_in(self):
        """Returns a list of all sections the user is active in."""
        return ImmutableList(x[0] for x in sorted(self.activities.items(),
                                                  key=lambda x: -x[1].counter))

    def get_badges_with_count(self):
        """Returns the badges with the count in a list.  The keys of the
        dict are the badge identifiers, not the badge objects.
        """
        result = {}
        for badge in self.badges:
            result[badge.identifier] = result.get(badge.identifier, 0) + 1
        return result

    @simple_repr
    def __repr__(self):
        return repr(self.username)


class UserMessage(object):
    """A message for a user."""
    query = session.query_property()

    def __init__(self, user, text, type='info'):
        assert type in ('info', 'error'), 'invalid message type'
        self.user = user
        self.text = text
        self.type = type
        session.add(self)

    @simple_repr
    def __repr__(self):
        return '%d to %r' % (self.id, self.user.username)


class TopicQuery(Query):
    """Special query for topics.  Allows to filter by trending topics and
    more.
    """

    def language(self, locale):
        """Filters by language."""
        return self.filter_by(locale=Locale.parse(locale))

    def unanswered(self):
        """Only return unanswered topics."""
        return self.filter_by(answer=None)

    def eagerposts(self):
        """Loads the post data eagerly."""
        return self.options(eagerload('posts'),
                            eagerload('posts.author'),
                            eagerload('posts.editor'))


class Topic(RemoteObject):
    """Represents a topic.  A topic is basically a post for the question, some
    replies any maybe an accepted answer.  Additionally it has a title and some
    denormalized values.
    """
    query = session.query_property(TopicQuery)

    remote_object_type = 'solace.question'
    public_fields = ('id', 'guid', 'locale', 'title', 'reply_count',
                     'is_deleted', 'votes', 'date', 'author', 'last_change',
                     'question.text', 'question.rendered_text')

    def __init__(self, locale, title, text, user, date=None):
        self.locale = Locale.parse(locale)
        self.title = title
        # start with -1, when the question post is created the code will
        # increment it to zero automatically.
        self.reply_count = -1
        self.is_deleted = False
        self.votes = 0
        self.question = Post(self, user, text, date, is_reply=False)
        self.date = self.question.created
        self.author = self.question.author
        self.answer = None
        self.last_change = self.question.created
        self._update_hotness()

        session.add(self)
        try_award('new_topic', user, self)

    @property
    def guid(self):
        """The global unique ID for the topic."""
        return u'tag:%s,%s:topic/%s' % (
            settings.TAG_AUTHORITY,
            self.date.strftime('%Y-%m-%d'),
            self.question.id
        )

    @property
    def replies(self):
        return ImmutableList([x for x in self.posts if not x.is_question])

    @property
    def slug(self):
        return slugify(self.title) or None

    def delete(self):
        """Just forward the call to the question."""
        self.question.delete()

    def restore(self):
        """Just forward the call to the question."""
        self.question.restore()

    def accept_answer(self, post, user=None):
        """Accept a post as answer."""
        assert post is None or post.topic == self, \
            'that post does not belong to the topic'
        if self.answer is not None:
            self.answer.is_answer = False
            atomic_add(self.answer.author, 'reputation',
                       -settings.REPUTATION_MAP['LOSE_ON_LOST_ANSWER'])
        if user is None:
            user = post and post.author or self.author
        if post is not None:
            post.is_answer = True
            atomic_add(post.author, 'reputation',
                       settings.REPUTATION_MAP['GAIN_ON_ACCEPTED_ANSWER'])
            self.answer_author = post.author
            self.answer_date = post.created
        self.answer = post
        try_award('accept', user, self, post)

    def bind_tags(self, tags):
        """Rebinds the tags to a list of tags (strings, not tag objects)."""
        current_map = dict((x.name, x) for x in self.tags)
        currently_attached = set(x.name for x in self.tags)
        new_tags = set(tags)

        def lookup_tag(name):
            tag = Tag.query.filter_by(locale=self.locale,
                                       name=name).first()
            if tag is not None:
                return tag
            return Tag(name, self.locale)

        # delete outdated tags
        for name in currently_attached.difference(new_tags):
            self.tags.remove(current_map[name])

        # add new tags
        for name in new_tags.difference(currently_attached):
            self.tags.append(lookup_tag(name))

    def get_url_values(self, action=None):
        endpoint = 'kb.topic_feed' if action == 'feed' else 'kb.topic'
        return endpoint, dict(
            lang_code=self.locale,
            id=self.id,
            slug=self.slug
        )

    def _set_vote(self, user, delta):
        self.question._set_vote(user, delta)

    def _get_vote(self, user):
        self.question._get_vote(user)

    @property
    def is_answered(self):
        """Returns true if the post is answered."""
        return self.answer_post_id is not None or self.answer is not None

    def sync_counts(self):
        """Syncs the topic counts with the question counts and recounts the
        replies from the posts.
        """
        self.votes = self.question.votes
        self.reply_count = Post.filter_by(topic=self).count() - 1

    def _update_hotness(self):
        """Updates the hotness column"""
        # algorithm from code.reddit.com by CondeNet, Inc.
        delta = self.date - datetime(1970, 1, 1)
        secs = (delta.days * 86400 + delta.seconds +
                (delta.microseconds / 1e6)) - 1134028003
        order = log(max(abs(self.votes), 1), 10)
        sign = 1 if self.votes > 0 else -1 if self.votes < 0 else 0
        self.hotness = round(order + sign * secs / 45000, 7)

    @simple_repr
    def __repr__(self):
        return '%r [%s] (%+d)' % (self.title, self.locale, self.votes)


class Post(RemoteObject, TextRendererMixin):
    """Represents a single post.  That can be a question, an answer or
    just a regular reply.
    """
    query = session.query_property()

    remote_object_type = 'solace.reply'
    public_fields = ('id', 'guid', ('topic_id', 'topic.id'), 'author', 'editor',
                     'text', 'rendered_text', 'is_deleted', 'is_answer',
                     'is_question', 'updated', 'created', 'votes', 'edits')

    def __init__(self, topic, author, text, date=None, is_reply=True):
        self.topic = topic
        self.author = author
        self.editor = None
        self.text = text
        self.is_deleted = False
        self.is_answer = False
        self.is_question = not is_reply
        if date is None:
            date = datetime.utcnow()
        topic.last_change = self.updated = self.created = date
        self.votes = 0
        self.edits = 0
        self.comment_count = 0
        author.touch_activity(topic.locale, 50)
        session.add(self)
        if not is_reply:
            try_award('reply', author, self)

    @property
    def guid(self):
        """The global unique ID for the post."""
        return u'tag:%s,%s:post/%s' % (
            settings.TAG_AUTHORITY,
            self.created.strftime('%Y-%m-%d'),
            self.id
        )

    def delete(self):
        """Mark this post as deleted.  Reflects that value to the
        topic as well.  This also decreases the count on the tag so
        that it's no longer counted.  For moderators this will cause
        some confusion on the tag pages but I think it's acceptable.
        """
        if self.is_deleted:
            return
        if self.is_question:
            self.topic.is_deleted = True
            for tag in self.topic.tags:
                atomic_add(tag, 'tagged', -1)
        else:
            atomic_add(self.topic, 'reply_count', -1)
        self.is_deleted = True

    def restore(self):
        """Restores a deleted post."""
        if not self.is_deleted:
            return
        if self.is_question:
            self.topic.is_deleted = False
            for tag in self.topic.tags:
                atomic_add(tag, 'tagged', 1)
        else:
            atomic_add(self.topic, 'reply_count', 1)
        self.is_deleted = False

    @property
    def was_edited(self):
        """True if the post was edited."""
        return self.editor_id is not None

    def get_url_values(self, action=None):
        """Returns a direct link to the post."""
        if action is not None:
            assert action in ('edit', 'delete', 'restore')
            return 'kb.%s_post' % action, {
                'lang_code':    self.topic.locale,
                'id':           self.id
            }
        if self.is_question:
            return self.topic.get_url_values()
        endpoint, args = self.topic.get_url_values()
        if not self.is_question:
            args['_anchor'] = 'reply-%d' % self.id
        return endpoint, args

    def edit(self, new_text, editor=None, date=None):
        """Changes the post contents and moves the current one into
        the attic.
        """
        if editor is None:
            editor = self.author
        if date is None:
            date = datetime.utcnow()

        PostRevision(self)
        self.text = new_text
        self.editor = editor
        self.updated = self.topic.last_change = date
        self.topic._update_hotness()
        atomic_add(self, 'edits', 1)

        try_award('edit', editor, self)
        editor.touch_activity(self.topic.locale, 20)

    def get_revision(self, id):
        """Gets a revision for this post."""
        entry = PostRevision.query.get(id)
        if entry is not None and entry.post == self:
            return entry

    def _revert_vote(self, vote, user):
        atomic_add(self, 'votes', -vote.delta)
        if vote.delta > 0:
            atomic_add(user, 'upvotes', -1)
            if self.is_question:
                atomic_add(self.author, 'reputation',
                           -settings.REPUTATION_MAP['GAIN_ON_QUESTION_UPVOTE'])
            else:
                atomic_add(self.author, 'reputation',
                           -settings.REPUTATION_MAP['GAIN_ON_UPVOTE'])
        elif vote.delta < 0:
            atomic_add(user, 'downvotes', -1)
            # downvoting yourself does not harm your reputation
            if user != self.author:
                atomic_add(self.author, 'reputation',
                           settings.REPUTATION_MAP['LOSE_ON_DOWNVOTE'])
                atomic_add(user, 'reputation',
                           settings.REPUTATION_MAP['DOWNVOTE_PENALTY'])

    def _set_vote(self, user, delta):
        """Invoked by the user voting functions."""
        assert delta in (0, 1, -1), 'you can only cast one vote'
        vote = _Vote.query.filter_by(user=user, post=self).first()

        # first things first.  If the delta is zero we get rid of an
        # already existing vote.
        if delta == 0:
            if vote:
                session.delete(vote)
                self._revert_vote(vote, user)

        # otherwise we create a new vote entry or update the existing
        else:
            if vote is None:
                vote = _Vote(user, self, delta)
            else:
                self._revert_vote(vote, user)
                vote.delta = delta
            atomic_add(self, 'votes', delta, expire=True)

        # if this post is a topic, reflect the new value to the
        # topic table.
        topic = Topic.query.filter_by(question=self).first()
        if topic is not None:
            topic.votes = self.votes

        if delta > 0:
            atomic_add(user, 'upvotes', 1)
            if self.is_question:
                atomic_add(self.author, 'reputation',
                           settings.REPUTATION_MAP['GAIN_ON_QUESTION_UPVOTE'])
            else:
                atomic_add(self.author, 'reputation',
                           settings.REPUTATION_MAP['GAIN_ON_UPVOTE'])
        elif delta < 0:
            atomic_add(user, 'downvotes', 1)
            # downvoting yourself does not harm your reputation
            if self.author != user:
                atomic_add(self.author, 'reputation',
                           -settings.REPUTATION_MAP['LOSE_ON_DOWNVOTE'])
                atomic_add(user, 'reputation',
                           -settings.REPUTATION_MAP['DOWNVOTE_PENALTY'])

        # remember the vote in the user cache
        if not hasattr(user, '_vote_cache'):
            user._vote_cache = {}
        user._vote_cache[self.id] = delta

        # update hotness, activity and award badges
        if self.is_question:
            self.topic._update_hotness()
        user.touch_activity(self.topic.locale, 1)
        try_award('vote', user, self, delta)

    def _get_vote(self, user):
        """Returns the current vote.  Invoked by user.has_*"""
        cache = getattr(user, '_vote_cache', None)
        if cache is None:
            user._vote_cache = {}
        cacheval = user._vote_cache.get(self.id)
        if cacheval is None:
            vote = _Vote.query.filter_by(user=user, post=self).first()
            if vote is None:
                cacheval = 0
            else:
                cacheval = vote.delta
            user._vote_cache[self.id] = cacheval
        return cacheval

    @simple_repr
    def __repr__(self):
        return '%s@\'%s\' (%+d)' % (
            repr(self.author.username),
            self.updated.strftime('%d.%m.%Y %H:%M'),
            self.votes
        )


class Comment(TextRendererMixin):
    """Represents a comment on a post."""
    query = session.query_property()

    #: comments do not allow multiple lines.  We don't want long
    #: discussions there.
    render_text_inline = True

    def __init__(self, post, author, text, date=None):
        if date is None:
            date = datetime.utcnow()
        self.post = post
        self.author = author
        self.date = date
        self.text = text
        session.add(self)

    @simple_repr
    def __repr__(self):
        return '#%s by %r on #%s' % (
            self.id,
            self.author.username,
            self.post_id
        )


class _Vote(object):
    """A helper for post voting."""
    query = session.query_property()

    def __init__(self, user, post, delta=1):
        self.user = user
        self.post = post
        self.delta = delta
        session.add(self)

    @simple_repr
    def __repr__(self):
        return '%+d by %d on %d' % (
            self.delta,
            self.user.username,
            self.post_id
        )


class _UserActivity(object):
    """Stores the user activity per-locale.  The activity is currently
    just used to find out what users to display on the per-locale user
    list but will later also be used together with the reputation for
    privilege management.
    """
    query = session.query_property()

    def __init__(self, user, locale):
        self.user = user
        self.locale = Locale.parse(locale)
        self.counter = 0
        self.first_activity = self.last_activity = datetime.utcnow()
        session.add(self)

    @simple_repr
    def __repr__(self):
        return 'of \'%s\' in \'%s\' (%d)' % (
            self.user.username,
            self.locale,
            self.counter
        )


class _OpenIDUserMapping(object):
    """Internal helper for the openid auth system."""
    query = session.query_property()

    def __init__(self, identity_url):
        self.identity_url = identity_url
        session.add(self)


class PostRevision(object):
    """A single entry in the post attic."""
    query = session.query_property()

    def __init__(self, post):
        self.post = post
        self.editor = post.editor or post.author
        self.date = post.updated
        self.text = post.text
        session.add(self)

    def restore(self):
        """Make this the current one again."""
        self.post.edit(self.text, self.editor, self.date)

    @property
    def rendered_text(self):
        """The rendered text."""
        return format_creole(self.text)

    @simple_repr
    def __repr__(self):
        return '#%d by %s on %s' % (
            self.id,
            self.editor.username,
            self.post_id
        )


class Tag(object):
    """Holds a tag."""
    query = session.query_property()

    def __init__(self, name, locale):
        self.name = name
        self.locale = Locale.parse(locale)
        self.tagged = 0
        session.add(self)

    @property
    def size(self):
        return 100 + log(self.tagged or 1) * 20

    def get_url_values(self):
        return 'kb.by_tag', dict(
            name=self.name,
            lang_code=self.locale
        )

    @simple_repr
    def __repr__(self):
        return '%s [%s]' % (self.name, self.locale)


class UserBadge(object):
    """Wrapper for the association proxy."""

    query = session.query_property()

    def __init__(self, badge, payload=None):
        self.badge = badge
        self.awarded = datetime.utcnow()
        self.payload = payload


class BadgeExtension(AttributeExtension):
    """Recounts badges on appening."""

    def count_badges(self, user, badgeiter):
        user.bronce_badges = user.silver_badges = \
        user.gold_badges = user.platin_badges = 0
        for badge in badgeiter:
            if badge:
                attr = badge.level + '_badges'
                setattr(user, attr, getattr(user, attr, 0) + 1)

    def append(self, state, value, initiator):
        user = state.obj()
        self.count_badges(user, chain(user.badges, [value.badge]))
        return value

    def remove(self, state, value, initiator):
        user = state.obj()
        badges = set(user.badges)
        badges.discard(value.badge)
        self.count_badges(user, badges)
        return value


class ReplyCollectionExtension(AttributeExtension):
    """Counts the replies on the topic and updates the last_change column
    in the topic table.
    """

    def append(self, state, value, initiator):
        atomic_add(state.obj(), 'reply_count', 1)
        return value

    def remove(self, state, value, initiator):
        atomic_add(state.obj(), 'reply_count', -1)
        return value


class CommentCounterExtension(AttributeExtension):
    """Counts the comments on the post."""

    def append(self, state, value, initiator):
        atomic_add(state.obj(), 'comment_count', 1)
        return value

    def remove(self, state, value, initiator):
        atomic_add(state.obj(), 'comment_count', -1)
        return value


class TagCounterExtension(AttributeExtension):
    """Counts the comments on the post."""

    def append(self, state, value, initiator):
        atomic_add(value, 'tagged', 1)
        return value

    def remove(self, state, value, initiator):
        atomic_add(value, 'tagged', -1)
        return value


mapper(User, users, properties=dict(
    id=users.c.user_id
))
mapper(_UserActivity, user_activities, properties=dict(
    id=user_activities.c.activity_id,
    user=relation(User)
))
mapper(UserBadge, user_badges, properties=dict(
    id=user_badges.c.badge_id,
    user=relation(User, backref=backref('_badges', extension=BadgeExtension()))
))
mapper(UserMessage, user_messages, properties=dict(
    id=user_messages.c.message_id,
    user=relation(User)
))
mapper(Post, posts, properties=dict(
    id=posts.c.post_id,
    author=relation(User, primaryjoin=posts.c.author_id == users.c.user_id),
    editor=relation(User, primaryjoin=posts.c.editor_id == users.c.user_id),
    comments=relation(Comment, backref='post',
                      extension=CommentCounterExtension(),
                      order_by=[comments.c.date]),
    text=synonym('_text', map_column=True)
))
mapper(Topic, topics, properties=dict(
    id=topics.c.topic_id,
    author=relation(User, primaryjoin=
        topics.c.author_id == users.c.user_id),
    answer_author=relation(User, primaryjoin=
        topics.c.answer_author_id == users.c.user_id),
    question=relation(Post, primaryjoin=
        topics.c.question_post_id == posts.c.post_id,
        post_update=True),
    answer=relation(Post, primaryjoin=
        topics.c.answer_post_id == posts.c.post_id,
        post_update=True),
    posts=relation(Post, primaryjoin=
        posts.c.topic_id == topics.c.topic_id,
        order_by=[posts.c.is_answer.desc(),
                  posts.c.votes.desc()],
        backref=backref('topic', post_update=True),
        extension=ReplyCollectionExtension()),
    tags=relation(Tag, secondary=topic_tags, order_by=[tags.c.name],
                  lazy=False, extension=TagCounterExtension())
), order_by=[topics.c.last_change.desc()])
mapper(Comment, comments, properties=dict(
    author=relation(User),
    text=synonym('_text', map_column=True)
))
mapper(Tag, tags, properties=dict(
    id=tags.c.tag_id,
    topics=dynamic_loader(Topic, secondary=topic_tags,
                          query_class=TopicQuery)
))
mapper(_Vote, votes, properties=dict(
    user=relation(User),
    post=relation(Post)
), primary_key=[votes.c.user_id, votes.c.post_id])
mapper(_OpenIDUserMapping, openid_user_mapping, properties=dict(
    user=relation(User, lazy=False, backref=backref('_openid_logins', lazy=True,
                                                    collection_class=set))
))
mapper(PostRevision, post_revisions, properties=dict(
    id=post_revisions.c.revision_id,
    post=relation(Post, backref=backref('revisions', lazy='dynamic')),
    editor=relation(User)
))


# circular dependencies
from solace.utils.support import slugify
from solace.badges import try_award

########NEW FILE########
__FILENAME__ = packs
# -*- coding: utf-8 -*-
"""
    solace.packs
    ~~~~~~~~~~~~

    The packs for static files.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
from solace.utils.packs import PackManager


pack_mgr = PackManager(os.path.join(os.path.dirname(__file__), 'static'))
pack_mgr.add_pack('default', ['layout.css', 'jquery.js', 'babel.js', 'solace.js',
                              'jquery.form.js', 'jquery.autocomplete.js',
                              'creole.js'])

########NEW FILE########
__FILENAME__ = schema
# -*- coding: utf-8 -*-
"""
    solace.schema
    ~~~~~~~~~~~~~

    This module defines the solace schema.  The structure is pretty simple
    and should scale up to the number of posts we expect.  Not much magic
    happening here.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, \
     ForeignKey, Boolean, Float
from solace.database import LocaleType, BadgeType, metadata


users = Table('users', metadata,
    # the internal ID of the user.  Even if an external Auth system is
    # used, we're storing the users a second time internal so that we
    # can easilier work with relations.
    Column('user_id', Integer, primary_key=True),
    # the user's reputation
    Column('reputation', Integer, nullable=False),
    # the username of the user.  For external auth systems it makes a
    # lot of sense to allow the user to chose a name on first login.
    Column('username', String(40), unique=True),
    # the email of the user.  If an external auth system is used, the
    # login code should update that information automatically on login
    Column('email', String(200), index=True),
    # the password hash.  This might not be used by every auth system.
    # the OpenID auth for example does not use it at all.  But also
    # external auth systems might not store the password here.
    Column('pw_hash', String(60)),
    # the realname of the user
    Column('real_name', String(200)),
    # the number of upvotes casted
    Column('upvotes', Integer, nullable=False),
    # the number of downvotes casted
    Column('downvotes', Integer, nullable=False),
    # the number of bronce badges
    Column('bronce_badges', Integer, nullable=False),
    # the number of silver badges
    Column('silver_badges', Integer, nullable=False),
    # the number of gold badges
    Column('gold_badges', Integer, nullable=False),
    # the number of platin badges
    Column('platin_badges', Integer, nullable=False),
    # true if the user is an administrator
    Column('is_admin', Boolean, nullable=False),
    # true if the user is banned
    Column('is_banned', Boolean, nullable=False),
    # the date of the last login
    Column('last_login', DateTime),
    # the user's activation key.  If this is NULL, the user is already
    # activated, otherwise this is the key the user has to enter on the
    # activation page (it's part of the link actually) to activate the
    # account.
    Column('activation_key', String(10))
)

user_activities = Table('user_activities', metadata,
    # the id of the actitity, exists only for the database
    Column('activity_id', Integer, primary_key=True),
    # the user the activity is for
    Column('user_id', Integer, ForeignKey('users.user_id')),
    # the language code for this activity stat
    Column('locale', LocaleType, index=True),
    # the internal activity counter
    Column('counter', Integer, nullable=False),
    # the date of the first activity in a language
    Column('first_activity', DateTime, nullable=False),
    # the date of the last activity in the language
    Column('last_activity', DateTime, nullable=False)
)

user_badges = Table('user_badges', metadata,
    # the internal id
    Column('badge_id', Integer, primary_key=True),
    # who was the badge awarded to?
    Column('user_id', Integer, ForeignKey('users.user_id')),
    # which badge?
    Column('badge', BadgeType(), index=True),
    # when was the badge awarded?
    Column('awarded', DateTime),
    # optional extra information for the badge system
    Column('payload', String(255))
)

user_messages = Table('user_messages', metadata,
    # the message id
    Column('message_id', Integer, primary_key=True),
    # who was the message sent to?
    Column('user_id', Integer, ForeignKey('users.user_id')),
    # the text of the message
    Column('text', String(512)),
    # the type of the message
    Column('type', String(10))
)

topics = Table('topics', metadata,
    # each topic has an internal ID.  This ID is also displayed in the
    # URL next to an automatically slugified version of the title.
    Column('topic_id', Integer, primary_key=True),
    # the language of the topic
    Column('locale', LocaleType, index=True),
    # the number of votes on the question_post (reflected)
    Column('votes', Integer, nullable=False),
    # the title for the topic (actually, the title of the question, just
    # that posts do not have titles, so it's only stored here)
    Column('title', String(100)),
    # the ID of the first post, the post that is the actual question.
    Column('question_post_id', Integer, ForeignKey('posts.post_id')),
    # the ID of the post that is accepted as answer.  If no answer is
    # accepted, this is None.
    Column('answer_post_id', Integer, ForeignKey('posts.post_id')),
    # the following information is denormalized from the posts table
    # in the PostSetterExtension
    Column('date', DateTime),
    Column('author_id', Integer, ForeignKey('users.user_id')),
    Column('answer_date', DateTime),
    Column('answer_author_id', Integer, ForeignKey('users.user_id')),
    # the date of the last change in the topic
    Column('last_change', DateTime),
    # the number of replies on the question (post-count - 1)
    # the ReplyCounterExtension takes care of that
    Column('reply_count', Integer, nullable=False),
    # the hotness
    Column('hotness', Float, nullable=False),
    # reflected from the question post. True if deleted
    Column('is_deleted', Boolean, nullable=False)
)

posts = Table('posts', metadata,
    # the internal ID of the post, also used as anchor
    Column('post_id', Integer, primary_key=True),
    # the id of the topic the post belongs to
    Column('topic_id', Integer, ForeignKey('topics.topic_id', use_alter=True,
                                           name='topics_topic_id_fk')),
    # the text of the post
    Column('text', Text),
    # the text rendered to HTML
    Column('rendered_text', Text),
    # the id of the user that wrote the post.
    Column('author_id', Integer, ForeignKey('users.user_id')),
    # the id of the user that edited the post.
    Column('editor_id', Integer, ForeignKey('users.user_id')),
    # true if the post is an answer
    Column('is_answer', Boolean),
    # true if the post is a question
    Column('is_question', Boolean),
    # the date of the post creation
    Column('created', DateTime),
    # the date of the last edit
    Column('updated', DateTime),
    # the number of votes
    Column('votes', Integer),
    # the number of edits
    Column('edits', Integer, nullable=False),
    # the number of comments attached to the post
    Column('comment_count', Integer, nullable=False),
    # true if the post is deleted
    Column('is_deleted', Boolean)
)

comments = Table('comments', metadata,
    # the internal comment id
    Column('comment_id', Integer, primary_key=True),
    # the post the comment belongs to
    Column('post_id', Integer, ForeignKey('posts.post_id')),
    # the author of the comment
    Column('author_id', Integer, ForeignKey('users.user_id')),
    # the date of the comment creation
    Column('date', DateTime),
    # the text of the comment
    Column('text', Text),
    # the text rendered to HTML
    Column('rendered_text', Text)
)

tags = Table('tags', metadata,
    # the internal tag id
    Column('tag_id', Integer, primary_key=True),
    # the language code
    Column('locale', LocaleType, index=True),
    # the number of items tagged
    Column('tagged', Integer, nullable=False),
    # the name of the tag
    Column('name', String(40), index=True)
)

topic_tags = Table('topic_tags', metadata,
    Column('topic_id', Integer, ForeignKey('topics.topic_id')),
    Column('tag_id', Integer, ForeignKey('tags.tag_id'))
)

votes = Table('votes', metadata,
    # who casted the vote?
    Column('user_id', Integer, ForeignKey('users.user_id')),
    # what was voted on?
    Column('post_id', Integer, ForeignKey('posts.post_id')),
    # what's the delta of the vote? (1 = upvote, -1 = downvote)
    Column('delta', Integer, nullable=False)
)

post_revisions = Table('post_revisions', metadata,
    # the internal id of the attic entry
    Column('revision_id', Integer, primary_key=True),
    # the post the entry was created from
    Column('post_id', Integer, ForeignKey('posts.post_id')),
    # the editor of the attic entry.  Because the original author may
    # not change there is no field for it.
    Column('editor_id', Integer, ForeignKey('users.user_id')),
    # the date of the attic entry.
    Column('date', DateTime),
    # the text contents of the entry.
    Column('text', Text)
)


# openid support
openid_association = Table('openid_association', metadata,
    Column('association_id', Integer, primary_key=True),
    Column('server_url', String(2048)),
    Column('handle', String(255)),
    Column('secret', String(255)),
    Column('issued', Integer),
    Column('lifetime', Integer),
    Column('assoc_type', String(64))
)

openid_user_nonces = Table('openid_user_nonces', metadata,
    Column('user_nonce_id', Integer, primary_key=True),
    Column('server_url', String(2048)),
    Column('timestamp', Integer),
    Column('salt', String(40))
)

openid_user_mapping = Table('openid_user_mapping', metadata,
    Column('user_mapping_id', Integer, primary_key=True),
    Column('identity_url', String(2048), unique=True),
    Column('user_id', Integer, ForeignKey('users.user_id'))
)

########NEW FILE########
__FILENAME__ = scripts
# -*- coding: utf-8 -*-
"""
    solace.scripts
    ~~~~~~~~~~~~~~

    Provides some setup.py commands.  The js-translation compiler is taken
    from Sphinx, the Python documentation tool.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
                (c) 2009 by the Sphinx Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
# note on imports:  This module must not import anything from the
# solace package, so that the initial import happens in the commands.
import os
import sys
from datetime import datetime, timedelta
from distutils import log
from distutils.cmd import Command
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from random import randrange, choice, random, shuffle
from jinja2.utils import generate_lorem_ipsum

from babel.messages.pofile import read_po
from babel.messages.frontend import compile_catalog
from simplejson import dump as dump_json


class RunserverCommand(Command):
    description = 'runs the development server'
    user_options = [
        ('host=', 'h',
         'the host of the server, defaults to localhost'),
        ('port=', 'p',
         'the port of the server, defaults to 3000'),
        ('no-reloader', None,
         'disable the automatic reloader'),
        ('no-debugger', None,
         'disable the integrated debugger')
    ]
    boolean_options = ['no-reloader', 'no-debugger']

    def initialize_options(self):
        self.host = 'localhost'
        self.port = 3000
        self.no_reloader = False
        self.no_debugger = False

    def finalize_options(self):
        if not str(self.port).isdigit():
            raise DistutilsOptionError('port has to be numeric')

    def run(self):
        from werkzeug import run_simple
        def wsgi_app(*a):
            from solace.application import application
            return application(*a)

        # werkzeug restarts the interpreter with the same arguments
        # which would print "running runserver" a second time.  Because
        # of this we force distutils into quiet mode.
        import sys
        sys.argv.insert(1, '-q')

        run_simple(self.host, int(self.port), wsgi_app,
                   use_reloader=not self.no_reloader,
                   use_debugger=not self.no_debugger)


class InitDatabaseCommand(Command):
    description = 'initializes the database'
    user_options = [
        ('drop-first', 'D',
         'drops existing tables first')
    ]
    boolean_options = ['drop-first']

    def initialize_options(self):
        self.drop_first = False

    def finalize_options(self):
        pass

    def run(self):
        from solace import database
        if self.drop_first:
            database.drop_tables()
            print 'dropped existing tables'
        database.init()
        print 'created database tables'


class ResetDatabaseCommand(Command):
    description = 'like initdb, but creates an admin:default user'
    user_options = [
        ('username', 'u', 'the admin username'),
        ('email', 'e', 'the admin email'),
        ('password', 'p', 'the admin password')
    ]

    def initialize_options(self):
        self.username = 'admin'
        self.email = None
        self.password = 'default'

    def finalize_options(self):
        if self.email is None:
            self.email = self.username + '@localhost'

    def run(self):
        from solace import database, models
        database.drop_tables()
        print 'dropped existing tables'
        database.init()
        print 'created database tables'
        admin = models.User(self.username, self.email, self.password,
                            is_admin=True)
        database.session.commit()
        print 'Created %s:%s (%s)' % (self.username, self.password,
                                      self.email)


class MakeTestDataCommand(Command):
    description = 'adds tons of test data into the database'
    user_options = [
        ('data-set-size', 's', 'the size of the dataset '
         '(small, medium, large)')
    ]

    USERNAMES = '''
        asanuma bando chiba ekiguchi erizawa fukuyama inouye ise jo kanada
        kaneko kasahara kasuse kazuyoshi koyama kumasaka matsushina
        matsuzawa mazaki miwa momotami morri moto nakamoto nakazawa obinata
        ohira okakura okano oshima raikatuji saigo sakoda santo sekigawa
        shibukji sugita tadeshi takahashi takizawa taniguchi tankoshitsu
        tenshin umehara yamakage yamana yamanouchi yamashita yamura
        aebru aendra afui asanna callua clesil daev danu eadyel eane efae
        ettannis fisil frudali glapao glofen grelnor halissa iorran oamira
        oinnan ondar orirran oudin paenael
    '''.split()
    TAGS = '''
        ajhar amuse animi apiin azoic bacon bala bani bazoo bear bloom bone
        broke bungo burse caam cento clack clear clog coyly creem cush deity
        durry ella evan firn grasp gype hance hanky havel hunks ingot javer
        juno kroo larix lift luke malo marge mart mash nairy nomos noyau
        papey parch parge parka pheal pint poche pooch puff quit ravin ream
        remap rotal rowen ruach sadhu saggy saura savor scops seat sere
        shone shorn sitao skair skep smush snoop soss sprig stalk stiff
        stipa study swept tang tars taxis terry thirt ulex unkin unmix unsin
        uprid vire wally wheat woven xylan
    '''.split()
    EPOCH = datetime(1930, 1, 1)

    def initialize_options(self):
        from solace import settings
        self.data_set_size = 'small'
        self.highest_date = None
        self.locales = settings.LANGUAGE_SECTIONS[:]

    def finalize_options(self):
        if self.data_set_size not in ('small', 'medium', 'large'):
            raise DistutilsOptionError('invalid value for data-set-size')

    def get_date(self, last=None):
        secs = randrange(10, 120)
        d = (last or self.EPOCH) + timedelta(seconds=secs)
        if self.highest_date is None or d > self.highest_date:
            self.highest_date = d
        return d

    def create_users(self):
        """Creates a bunch of test users."""
        from solace.models import User
        num = {'small': 15, 'medium': 30, 'large': 50}[self.data_set_size]
        result = []
        used = set()
        for x in xrange(num):
            while 1:
                username = choice(self.USERNAMES)
                if username not in used:
                    used.add(username)
                    break
            result.append(User(username, '%s@example.com' % username,
                               'default'))
        print 'Generated %d users' % num
        return result

    def create_tags(self):
        """Creates a bunch of tags."""
        from solace.models import Tag
        num = {'small': 10, 'medium': 20, 'large': 50}[self.data_set_size]
        result = {}
        tag_count = 0
        for locale in self.locales:
            c = result[locale] = []
            used = set()
            for x in xrange(randrange(num - 5, num + 5)):
                while 1:
                    tag = choice(self.TAGS)
                    if tag not in used:
                        used.add(tag)
                        break
                c.append(Tag(tag, locale).name)
                tag_count += 1
        print 'Generated %d tags' % tag_count
        return result

    def create_topics(self, tags, users):
        """Generates a bunch of topics."""
        from solace.models import Topic
        last_date = None
        topics = []
        num, var = {'small': (50, 10), 'medium': (200, 20),
                    'large': (1000, 200)}[self.data_set_size]
        count = 0
        for locale in self.locales:
            for x in xrange(randrange(num - var, num + var)):
                topic = Topic(locale, generate_lorem_ipsum(1, False, 3, 9),
                              generate_lorem_ipsum(randrange(1, 5), False,
                                                   40, 140), choice(users),
                              date=self.get_date(last_date))
                last_date = topic.last_change
                these_tags = list(tags[locale])
                shuffle(these_tags)
                topic.bind_tags(these_tags[:randrange(2, 6)])
                topics.append(topic)
                count += 1
        print 'Generated %d topics in %d locales' % (count, len(self.locales))
        return topics

    def answer_and_vote(self, topics, users):
        from solace.models import Post
        replies = {'small': 4, 'medium': 8, 'large': 12}[self.data_set_size]
        posts = [x.question for x in topics]
        last_date = topics[-1].last_change
        for topic in topics:
            for x in xrange(randrange(2, replies)):
                post = Post(topic, choice(users),
                            generate_lorem_ipsum(randrange(1, 3), False,
                                                 20, 100),
                            self.get_date(last_date))
                posts.append(post)
                last_date = post.created
        print 'Generated %d posts' % len(posts)

        votes = 0
        for post in posts:
            for x in xrange(randrange(replies * 4)):
                post = choice(posts)
                user = choice(users)
                if user != post.author:
                    if random() >= 0.05:
                        user.upvote(post)
                    else:
                        user.downvote(post)
                    votes += 1

        print 'Casted %d votes' % votes

        answered = 0
        for topic in topics:
            replies = list(topic.replies)
            if replies:
                replies.sort(key=lambda x: x.votes)
                post = choice(replies[:4])
                if post.votes > 0 and random() > 0.2:
                    topic.accept_answer(post, choice(users))
                    answered += 1

        print 'Answered %d posts' % answered
        return posts

    def create_comments(self, posts, users):
        """Creates comments for the posts."""
        from solace.models import Comment
        num = {'small': 3, 'medium': 6, 'large': 10}[self.data_set_size]
        last_date = posts[-1].created
        comments = 0
        for post in posts:
            for x in xrange(randrange(num)):
                comment = Comment(post, choice(users),
                                  generate_lorem_ipsum(1, False, 10, 40),
                                  self.get_date(last_date))
                last_date = comment.date
                comments += 1
        print 'Generated %d comments' % comments

    def rebase_dates(self, topics):
        """Rebase all dates so that they are most recent."""
        print 'Rebasing dates...',
        delta = datetime.utcnow() - self.highest_date
        for topic in topics:
            topic.last_change += delta
            topic.date += delta
            for post in topic.posts:
                post.updated += delta
                post.created += delta
                for comment in post.comments:
                    comment.date += delta
            topic._update_hotness()
        print 'done'

    def run(self):
        from solace.database import session
        users = self.create_users()
        tags = self.create_tags()
        topics = self.create_topics(tags, users)
        posts = self.answer_and_vote(topics, users)
        self.create_comments(posts, users)
        self.rebase_dates(topics)
        session.commit()


class CompileCatalogExCommand(compile_catalog):
    """Extends the standard catalog compiler to one that also creates
    .js files for the strings that are needed in JavaScript.
    """

    def run(self):
        compile_catalog.run(self)

        po_files = []
        js_files = []

        if not self.input_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.directory, self.locale,
                                              'LC_MESSAGES',
                                              self.domain + '.po')))
                js_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.js'))
            else:
                for locale in os.listdir(self.directory):
                    po_file = os.path.join(self.directory, locale,
                                           'LC_MESSAGES',
                                           self.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        js_files.append(os.path.join(self.directory, locale,
                                                     'LC_MESSAGES',
                                                     self.domain + '.js'))
        else:
            po_files.append((self.locale, self.input_file))
            if self.output_file:
                js_files.append(self.output_file)
            else:
                js_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.js'))

        for js_file, (locale, po_file) in zip(js_files, po_files):
            infile = open(po_file, 'r')
            try:
                catalog = read_po(infile, locale)
            finally:
                infile.close()

            if catalog.fuzzy and not self.use_fuzzy:
                continue

            log.info('writing JavaScript strings in catalog %r to %r',
                     po_file, js_file)

            jscatalog = {}
            for message in catalog:
                if any(x[0].endswith('.js') for x in message.locations):
                    msgid = message.id
                    if isinstance(msgid, (list, tuple)):
                        msgid = msgid[0]
                    jscatalog[msgid] = message.string

            outfile = open(js_file, 'wb')
            try:
                outfile.write('Solace.TRANSLATIONS.load(');
                dump_json(dict(
                    messages=jscatalog,
                    plural_expr=catalog.plural_expr,
                    locale=str(catalog.locale),
                    domain=str(self.domain)
                ), outfile)
                outfile.write(');\n')
            finally:
                outfile.close()


class CompressDependenciesCommand(Command):
    """A distutils command for dep compression."""

    description = 'Compresses web dependencies'
    user_options = [
        ('clean', None, 'removes the compressed files'),
        ('compressor', 'c', 'the compressor to use (defaults to auto)')
    ]
    boolean_options = ['clean']

    def initialize_options(self):
        self.clean = False
        self.compressor = 'auto'

    def finalize_options(self):
        pass

    def run(self):
        from solace.packs import pack_mgr
        if self.clean:
            print 'Remove compressed files'
            pack_mgr.remove_compressed()
        else:
            pack_mgr.compress(log=log)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
"""
    solace.settings
    ~~~~~~~~~~~~~~~

    This module just stores the solace settings.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
del with_statement

# propagate early.  That way we can import "from solace import settings"
# when the settings is not yet set up.  This is needed because during
# bootstrapping we're have carefully crafted circular dependencies between
# the settings and the internationalization support module.
import sys, solace
solace.settings = sys.modules['solace.settings']
del sys, solace

#: i18n support, leave in place for custom settings modules
from solace.i18n import lazy_gettext as _


def configure(**values):
    """Configuration shortcut."""
    for key, value in values.iteritems():
        if key.startswith('_') or not key.isupper():
            raise TypeError('invalid configuration variable %r' % key)
        d[key] = value


def revert_to_default():
    """Reverts the known settings to the defaults."""
    from os.path import join, dirname
    configure_from_file(join(dirname(__file__), 'default_settings.cfg'))


def autodiscover_settings():
    """Finds settings in the environment."""
    import os
    if 'SOLACE_SETTINGS_FILE' in os.environ:
        configure_from_file(os.environ['SOLACE_SETTINGS_FILE'])


def configure_from_file(filename):
    """Configures from a file."""
    d = globals()
    ns = dict(d)
    execfile(filename, ns)
    for key, value in ns.iteritems():
        if not key.startswith('_') and key.isupper():
            d[key] = value


def describe_settings():
    """Describes the settings.  Returns a list of
    ``(key, current_value, description)`` tuples.
    """
    import re
    from pprint import pformat
    from os.path import join, dirname
    assignment_re = re.compile(r'\s*([A-Z_][A-Z0-9_]*)\s*=')

    # use items() here instead of iteritems so that if a different
    # thread somehow fiddles with the globals, we don't break
    items = dict((k, (pformat(v).decode('utf-8', 'replace'), u''))
                 for (k, v) in globals().items() if k.isupper())

    with open(join(dirname(__file__), 'default_settings.cfg')) as f:
        comment_buf = []
        for line in f:
            line = line.rstrip().decode('utf-8')
            if line.startswith('#:'):
                comment_buf.append(line[2:].lstrip())
            else:
                match = assignment_re.match(line)
                if match is not None:
                    key = match.group(1)
                    tup = items.get(key)
                    if tup is not None and comment_buf:
                        items[key] = (tup[0], u'\n'.join(comment_buf))
                    del comment_buf[:]

    return sorted([(k,) + v for k, v in items.items()])


revert_to_default()
autodiscover_settings()

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
"""
    solace.signals
    ~~~~~~~~~~~~~~

    Very basic signalling system.

    :copyright: 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
from types import MethodType
from inspect import ismethod, currentframe
from weakref import WeakKeyDictionary, ref as weakref
from threading import Lock
from operator import itemgetter
from contextlib import contextmanager


_subscribe_lock = Lock()
_subscriptions = {}
_ref_lock = Lock()
_method_refs = WeakKeyDictionary()


def _ref(func):
    """Return a safe reference to the callable."""
    assert callable(func), 'expected callable, got %r' % type(func).__name__
    if not ismethod(func) or func.im_self is None:
        return func
    with _ref_lock:
        self = func.im_self
        d = _method_refs.get(self)
        if d is None:
            d = _method_refs[self] = WeakKeyDictionary()
        method = d.get(func.im_func)
        if method is not None:
            return method
        d[func.im_func] = rv = _MethodRef(self, func.im_func, func.im_class)
        return rv


class _MethodRef(object):
    """A weak method reference."""

    def __init__(self, im_self, im_func, im_class):
        self.im_self = weakref(im_self)
        self.im_func = weakref(im_func)
        self.im_class = weakref(im_class)

    def resolve(self):
        """Returns the reference as standard Python method.  If the
        reference is already dead, `None` is returned.
        """
        cls = self.im_class()
        obj = self.im_self()
        func = self.im_func()
        if obj is not None and func is not None and cls is not None:
            return MethodType(func, obj, cls)


def SIG(name, args=None):
    """Macroish signal definition.  Only use at global scope.  The
    following pieces of code are the same::

        SIG('FOO', ['args'])
        FOO = Signal('FOO', ['args'])
    """
    frm = currentframe(1)
    assert frm.f_globals is frm.f_locals, \
        'SIG() may not be used at local scope'
    frm.f_globals[name] = Signal(name, args, _frm=frm)


class Signal(object):
    """Represents a signal.  The first argument is the name of the signal
    which should also be the name of the variable in the module the signal is
    stored and the second is a list of named arguments.

    Signals can be created by instanciating this class, or by using the
    :func:`SIG` helper::

        FOO = Signal('FOO', ['args'])
        SIG('FOO', ['args'])

    The important difference is that the :func:`SIG` helper only works at
    global scope.  The use of :func:`SIG` is recommended because it avoids
    errors that are hard to spot when the name of the variable does not
    match the name of the signal.
    """

    def __init__(self, name, args=None, _frm=None):
        if _frm is None:
            _frm = currentframe(1)
        if _frm.f_globals is _frm.f_locals:
            mod = _frm.f_globals['__name__']
        else:
            mod = '<temporary>'
        self.__module__ = mod
        self.__name__ = name
        self.args = tuple(args or ())

    def connect(self, func):
        """Connect the function to the signal.  The function can be a regular
        Python function object or a bound method.  Internally a weak reference
        to this object is subscribed so it's not a good idea to pass an arbitrary
        callable to the function which most likely is then unregistered pretty
        quickly by the garbage collector.

        >>> def handle_foo(arg):
        ...   print arg
        ...
        >>> foo = Signal('foo', ['arg'])
        >>> foo.connect(handle_foo)

        The return value of the function is always `None`, there is no ID for the
        newly established connection.  To disconnect the function and signal is
        needed.  There can only be one connection of the function to the signal
        which means that if you're connecting twice the function will still only
        be called once and the first disconnect closes the connection.

        :param func: the function to connect
        """
        func = _ref(func)
        with _subscribe_lock:
            d = _subscriptions.get(self)
            if d is None:
                d = _subscriptions[self] = WeakKeyDictionary()
            d[func] = None

    def is_connected(self, func):
        """Checks if the function is connected to the signal.

        :param func: the function to check for an active connection.
        :return: `True` if connected, otherwise `False`.
        """
        func = _ref(func)
        with _subscribe_lock:
            d = _subscriptions.get(self)
            if d is None:
                return False
            return d.get(func, 0) is not 0

    def get_connections(self):
        """Returns a list of active connections a set.  The return value may
        only be used for introspection.  After the call the connections might
        have changed already, so do not attempt to call the handlers yourself.

        :return: a `set` of connections
        """
        with _subscribe_lock:
            d = _subscriptions.get(self)
            result = set()
            if d is not None:
                for con in d.keys():
                    if isinstance(con, _MethodRef):
                        con = con.resolve()
                    if con is not None:
                        result.add(con)
            return result

    def disconnect(self, func):
        """Disconnects the function from the signal.  Disconnecting automatically
        happens if the connected function is garbage collected.  However if you
        have a local function that should connect to signals for a short period
        of time use the :func:`temporary_connection` function for performance
        reasons and clarity.

        :param func: the name of the function to disconnect
        :param signal: the signal to disconnect from
        """
        func = _ref(func)
        with _subscribe_lock:
            d = _subscriptions.get(self)
            if d is not None:
                d.pop(func, None)

    def emit(self, **args):
        """Emits a signal with the given named arguments.  The arguments have
        to match the argument signature from the signal.  However this check
        is only performed in debug runs for performance reasons.  Arguments are
        passed as keyword arguments only.

        The return value of the emit function is a list of the handlers and their
        return values

        >>> foo = Signal('foo', ['arg'])
        >>> foo.emit(arg=42)
        []

        :param signal: the signal to emit
        :param args: the arguments for the signal.
        :return: a list of ``(handler, return_value)`` tuples.
        """
        assert set(self.args) == set(args), \
            'passed arguments to not match signal signature'
        listeners = _subscriptions.get(self)
        result = []
        if listeners is not None:
            for func in listeners.keys():
                # if a listener is a method reference we have to resolve it.
                # there is a small window where this could be garbage collected
                # while we have the reference so we handle the case when the
                # resolving returns `None`.
                if isinstance(func, _MethodRef):
                    func = func.resolve()
                    if func is None:
                        continue
                result.append((func, func(**args)))

        # send the special broadcast signal to notify listeners of the
        # broadcast signal that a signal was sent.
        if self is not broadcast:
            Signal.emit(broadcast, signal=self, args=args)

        return result

    def __reduce__(self):
        if self.__module__ == '<temporary>':
            raise TypeError('cannot pickle temporary signal')
        return self.__name__

    def __repr__(self):
        if self.__module__ != '<temporary>':
            return self.__module__ + '.' + self.__name__
        return self.__name__


class _BroadcastSignal(Signal):
    """Special broadcast signal.  Connect to it to be notified about
    all signals.  This signal is automatically send with each other
    signal.
    """

    __slots__ = ()

    def emit(self, **args):
        """You cannot emit broadcast signals."""
        raise TypeError('emitting broadcast signals is unsupported')


# the singleton instance of the broadcast signal
broadcast = _BroadcastSignal('broadcast', ['signal', 'args'])
del _BroadcastSignal


@contextmanager
def temporary_connection(func, signal):
    """A temporary connection to a signal::

        def handle_foo(arg):
            pass

        with temporary_connection(handle_foo, FOO):
            ...
    """
    signal.connect(func)
    try:
        yield
    finally:
        signal.disconnect(func)


def handler(signal):
    """Helper decorator for function registering.  Connects the decorated
    function to the signal given:

    >>> foo = Signal('foo', ['arg'])
    >>> @handler(foo)
    ... def handle_foo(arg):
    ...   print arg
    ...
    >>> rv = foo.emit(arg=42)
    42

    :param signal: the signal to connect the handler to
    """
    def decorator(func):
        signal.connect(func)
        return func
    return decorator


#: this signal is emitted before the request is initialized.  At that point
#: you don't know anything yet, not even the WSGI environment.  The local
#: manager indent is already set to the correct thread though, so you might
#: add something to the local object from the ctxlocal module.
SIG('before_request_init')

#: emitted when the request was initialized successfully.
SIG('after_request_init', ['request'])

#: emitted right before the request dispatching kicks in.
SIG('before_request_dispatch', ['request'])

#: emitted after the request dispatching ended.  Usually it's a bad idea to
#: use this signal, use the BEFORE_RESPONSE_SENT signal instead.
SIG('after_request_dispatch', ['request', 'response'])

#: emitted after the request was shut down.  This might be called with an
#: exception on the stack if an error happened.
SIG('after_request_shutdown')

#: emitted before the response is sent.  The response object might be modified
#: in place, but it's not possible to replace it or abort the handling.
SIG('before_response_sent', ['request', 'response'])

#: emitted after some models where properly comitted to the database.  The
#: changes list a list of ``(model, operation)`` tuples.  Operation is a
#: string that can either be "insert", "update" or "delete".
SIG('after_models_committed', ['changes'])

#: like `after_models_committed` but fired before the actual commit.  Mostly
#: useless but exists for completeness.
SIG('before_models_committed', ['changes'])

#: emitted before a database cursor was executed
SIG('before_cursor_executed', ['cursor', 'statement', 'parameters'])

#: emitted after a database cursor was executed
SIG('after_cursor_executed', ['cursor', 'statement', 'parameters', 'time'])

########NEW FILE########
__FILENAME__ = templating
# -*- coding: utf-8 -*-
"""
    solace.templating
    ~~~~~~~~~~~~~~~~~

    Very simple bridge to Jinja2.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
from os import path
from itertools import chain
from threading import Lock
from werkzeug import escape
from werkzeug.exceptions import NotFound
from jinja2 import Environment, PackageLoader, BaseLoader, TemplateNotFound, \
                   Markup
from solace.utils.ini import parse_ini
from solace.utils.packs import PackManager


_theme = None
_theme_lock = Lock()


DEFAULT_THEME_PATH = [path.join(path.dirname(__file__), 'themes')]


def split_path_safely(template):
    """Splits up a path into individual components.  If one of the
    components is unsafe on the file system, `None` is returned:

    >>> from solace.templating import split_path_safely
    >>> split_path_safely("foo/bar/baz")
    ['foo', 'bar', 'baz']
    >>> split_path_safely("foo/bar/baz/../meh")
    >>> split_path_safely("/meh/muh")
    ['meh', 'muh']
    >>> split_path_safely("/blafasel/.muh")
    ['blafasel', '.muh']
    >>> split_path_safely("/blafasel/./x")
    ['blafasel', 'x']
    """
    pieces = []
    for piece in template.split('/'):
        if path.sep in piece \
           or (path.altsep and path.altsep in piece) or \
           piece == path.pardir:
            return None
        elif piece and piece != '.':
            pieces.append(piece)
    return pieces


def get_theme(name=None):
    """Returns the specified theme of the one from the config.  If the
    theme does not exist, `None` is returned.
    """
    global _theme
    set_theme = False
    with _theme_lock:
        if name is None:
            if _theme is not None:
                return _theme
            name = settings.THEME
            set_theme = True
        for folder in chain(settings.THEME_PATH, DEFAULT_THEME_PATH):
            theme_dir = path.join(folder, name)
            if path.isfile(path.join(theme_dir, 'theme.ini')):
                rv = Theme(theme_dir)
                if set_theme:
                    _theme = rv
                return rv


def refresh_theme():
    """After a config change this unloads the theme to refresh it."""
    global _theme
    _theme = None

    # if we have a cache, clear it.  This makes sure that imports no
    # longer point to the old theme's layout files etc.
    cache = jinja_env.cache
    if cache:
        cache.clear()


class Theme(object):
    """Represents a theme."""

    def __init__(self, folder):
        self.id = path.basename(folder)
        self.folder = folder
        self.template_path = path.join(folder, 'templates')
        with open(path.join(folder, 'theme.ini')) as f:
            self.config = parse_ini(f)
        self.name = self.config.get('theme.name', self.id)
        self.packs = PackManager(path.join(folder, 'static'),
                                 self.get_link)
        for key, value in self.config.iteritems():
            if key.startswith('packs.'):
                self.packs.add_pack(key[6:], value.split())

    def open_resource(self, filename):
        """Opens a resource from the static folder as fd."""
        pieces = split_path_safely(filename)
        if pieces is not None:
            fn = path.join(self.folder, 'static', *pieces)
            if path.isfile(fn):
                return open(fn, 'rb')

    def get_link(self, filename, ext=None):
        return url_for('themes.get_resource', theme=self.id,
                       file=filename)


class SolaceThemeLoader(PackageLoader):
    """The solace loader checks for templates in the template folder of
    the current theme for templaes first, then it falls back to the
    builtin templates.

    A template can force to load the builtin one by prefixing the path
    with a bang (eg: ``{% extends '!layout.html' %}``).
    """

    def __init__(self):
        PackageLoader.__init__(self, 'solace')

    def get_source(self, environment, template):
        if template[:1] == '!':
            template = template[1:]
        else:
            pieces = split_path_safely(template)
            if pieces is None:
                raise TemplateNotFound()
            theme = get_theme()
            if theme is None:
                raise RuntimeError('theme not found')
            fn = path.join(theme.template_path, *pieces)
            if path.isfile(fn):
                with open(fn, 'r') as f:
                    contents = f.read().decode(self.encoding)
                mtime = path.getmtime(fn)
                def uptodate():
                    try:
                        return path.getmtime(fn) == mtime
                    except OSError:
                        return False
                return contents, fn, uptodate
        return PackageLoader.get_source(self, environment, template)


def shall_use_autoescape(template_name):
    if template_name is None or '.' not in template_name:
        return False
    ext = template_name.rsplit('.', 1)[1]
    return ext == 'html'


jinja_env = Environment(loader=SolaceThemeLoader(),
                        autoescape=shall_use_autoescape,
                        extensions=['jinja2.ext.i18n',
                                    'jinja2.ext.autoescape'])


def render_template(template_name, **context):
    """Renders a template into a string."""
    template = jinja_env.get_template(template_name)
    context['request'] = Request.current
    context['theme'] = get_theme()
    context['auth_system'] = get_auth_system()
    return template.render(context)


def get_macro(template_name, macro_name):
    """Return a macro from a template."""
    template = jinja_env.get_template(template_name)
    return getattr(template.module, macro_name)


def datetimeformat_filter(obj, html=True, prefixed=True):
    rv = format_datetime(obj)
    if prefixed:
        rv = _(u'on %s') % rv
    if html:
        rv = u'<span class="datetime" title="%s">%s</span>' % (
            obj.strftime('%Y-%m-%dT%H:%M:%SZ'),
            escape(rv)
        )
    return Markup(rv)


from solace import settings
from solace.application import Request, url_for
from solace.auth import get_auth_system
from solace.packs import pack_mgr
from solace.i18n import gettext, ngettext, format_datetime, format_number, _
jinja_env.globals.update(
    url_for=url_for,
    _=gettext,
    gettext=gettext,
    ngettext=ngettext,
    settings=settings,
    packs=pack_mgr
)
jinja_env.filters.update(
    datetimeformat=datetimeformat_filter,
    numberformat=format_number
)

########NEW FILE########
__FILENAME__ = core_views
# -*- coding: utf-8 -*-
"""
    solace.tests.core_views
    ~~~~~~~~~~~~~~~~~~~~~~~

    Test the kb views.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re
import unittest
from solace.tests import SolaceTestCase

from solace import models, settings
from solace.database import session


_link_re = re.compile(r'http://\S+')


class CoreViewsTestCase(SolaceTestCase):

    def test_login(self):
        """Logging a user in"""
        models.User('THE_USER', 'the.user@example.com', 'default')
        session.commit()
        response = self.client.get('/en/')
        self.assert_('THE_USER' not in response.data)
        self.login('THE_USER', 'default')
        response = self.client.get('/en/')
        self.assert_('THE_USER' in response.data)

    def test_logout(self):
        """Logging a user out"""
        models.User('THE_USER', 'the.user@example.com', 'default')
        session.commit()
        self.login('THE_USER', 'default')
        self.logout()
        response = self.client.get('/en/')
        self.assert_('THE_USER' not in response.data)

    def test_register_without_confirm(self):
        """Registering a user without mail confirmation"""
        settings.REGISTRATION_REQUIRES_ACTIVATION = False
        settings.RECAPTCHA_ENABLE = False
        self.submit_form('/register', {
            'username':         'A_USER',
            'password':         'default',
            'password_repeat':  'default',
            'email':            'a.user@example.com'
        })
        self.login('A_USER', 'default')
        response = self.client.get('/en/')
        self.assert_('A_USER' in response.data)
        user = models.User.query.filter_by(username='A_USER').first()
        self.assertEqual(user.email, 'a.user@example.com')
        self.assertEqual(user.is_active, True)

    def test_register_with_confirm(self):
        """Registering a user with mail confirmation"""
        settings.REGISTRATION_REQUIRES_ACTIVATION = True
        settings.RECAPTCHA_ENABLE = False
        self.submit_form('/register', {
            'username':         'A_USER',
            'password':         'default',
            'password_repeat':  'default',
            'email':            'a.user@example.com'
        })

        response = self.login('A_USER', 'default')
        self.assert_('not yet activated' in response.data)

        mails = self.get_mails()
        self.assert_(mails)
        for link in _link_re.findall(mails[0].get_payload()):
            if 'activate' in link:
                self.client.get('/' + link.split('/', 3)[-1])
                break
        else:
            self.assert_(False, 'Did not find activation link')

        self.login('A_USER', 'default')
        response = self.client.get('/en/')
        self.assert_('A_USER' in response.data)
        user = models.User.query.filter_by(username='A_USER').first()
        self.assertEqual(user.email, 'a.user@example.com')
        self.assertEqual(user.is_active, True)

    def test_reset_password(self):
        """Reset password."""
        settings.RECAPTCHA_ENABLE = False
        user = models.User('A_USER', 'a.user@example.com', 'default')
        session.commit()

        self.submit_form('/_reset_password', {
            'username':         'A_USER',
            'email':            ''
        })

        mails = self.get_mails()
        self.assert_(mails)

        for link in _link_re.findall(mails[0].get_payload()):
            if 'reset_password' in link:
                response = self.client.get('/' + link.split('/', 3)[-1])
                break
        else:
            self.assert_(False, 'Did not find password reset link')

        match = re.compile(r'password was reset to <code>(.*?)</code>') \
            .search(response.data)
        self.assert_(match)
        self.login('A_USER', match.group(1))
        response = self.client.get('/en/')
        self.assert_('A_USER' in response.data)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CoreViewsTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = kb_views
# -*- coding: utf-8 -*-
"""
    solace.tests.kb_views
    ~~~~~~~~~~~~~~~~~~~~~

    Test the kb views.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import unittest
from solace.tests import SolaceTestCase, html_xpath

from solace import models, settings
from solace.database import session


class KBViewsTestCase(SolaceTestCase):

    def test_new_topic(self):
        """Creating new topics and replying"""
        # create the user
        models.User('user1', 'user1@example.com', 'default')
        session.commit()

        # login and submit
        self.login('user1', 'default')
        response = self.submit_form('/en/new', {
            'title':    'Hello World',
            'text':     'This is just a small test\n\n**test**',
            'tags':     'foo, bar, baz'
        })

        # we will need the topic URL later for commit submission,
        # capture it!
        topic_url = '/' + response.headers['Location'].split('/', 3)[-1]
        response = self.client.get(topic_url)
        q = lambda x: html_xpath(response.html, x)

        # we have a headline
        self.assertEqual(q('//html:h1')[0].text, 'Hello World')

        # and all the tags
        tags = sorted(x.text for x in q('//html:p[@class="tags"]/html:a'))
        self.assertEqual(tags, ['bar', 'baz', 'foo'])

        # and the text is present and parsed
        pars = q('//html:div[@class="text"]/html:p')
        self.assertEqual(len(pars), 2)
        self.assertEqual(pars[0].text, 'This is just a small test')
        self.assertEqual(pars[1][0].tag, '{http://www.w3.org/1999/xhtml}strong')
        self.assertEqual(pars[1][0].text, 'test')

        # now try to submit a reply
        response = self.submit_form(topic_url, {
            'text':     'This is a reply\n\nwith //text//'
        }, follow_redirects=True)
        q = lambda x: html_xpath(response.html, x)

        # do we have the text?
        pars = q('//html:div[@class="replies"]//html:div[@class="text"]/html:p')
        self.assertEqual(len(pars), 2)
        self.assertEqual(pars[0].text, 'This is a reply')
        self.assertEqual(pars[1].text, 'with ')
        self.assertEqual(pars[1][0].tag, '{http://www.w3.org/1999/xhtml}em')
        self.assertEqual(pars[1][0].text, 'text')

    def test_voting(self):
        """Voting from the web interface"""
        # create a bunch of users and let one of them create a topic
        users = [models.User('user_%d' % x, 'user%d@example.com' % x,
                             'default') for x in xrange(5)]
        for user in users:
            user.reputation = 50
        topic = models.Topic('en', 'Hello World', 'foo', users[0])
        session.commit()
        tquid = topic.question.id

        def get_vote_count(response):
            el = html_xpath(response.html, '//html:div[@class="votebox"]/html:h4')
            return int(el[0].text)

        vote_url = '/_vote/%s?val=%%d&_xt=%s' % (tquid, self.get_exchange_token())

        # the author should not be able to upvote
        self.login('user_0', 'default')
        response = self.client.get(vote_url % 1, follow_redirects=True)
        self.assert_('cannot upvote your own post' in response.data)

        # by default the user should not be able to downvote, because
        # he does not have enough reputation
        response = self.client.get(vote_url % -1, follow_redirects=True)
        self.assert_('to downvote you need at least 100 reputation'
                     in response.data)

        # so give him and all other users reputation
        for user in models.User.query.all():
            user.reputation = 10000
        session.commit()

        # and let him downvote
        response = self.client.get(vote_url % -1, follow_redirects=True)
        self.assertEqual(get_vote_count(response), -1)

        # and now let *all* users vote up, including the author, but his
        # request will fail.
        for num in xrange(5):
            self.logout()
            self.login('user_%d' % num, 'default')
            response = self.client.get(vote_url % 1, follow_redirects=True)

        # we should be at 4, author -1 the other four +1
        self.assertEqual(get_vote_count(response), 3)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(KBViewsTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = link_check
# -*- coding: utf-8 -*-
"""
    solace.tests.link_check
    ~~~~~~~~~~~~~~~~~~~~~~~

    A test that finds 404 links in the default templates.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re
import unittest
from urlparse import urljoin
from solace.tests import SolaceTestCase, html_xpath

from solace import models, settings
from solace.database import session


BASE_URL = 'http://localhost/'
MIN_VISITED = 12


class LinkCheckTestCase(SolaceTestCase):

    def test_only_valid_links(self):
        """Make sure that all links are valid"""
        settings.LANGUAGE_SECTIONS = ['en']
        user = models.User('user1', 'user1@example.com', 'default')
        user.is_admin = True
        banned_user = models.User('user2', 'user2@example.com', 'default')
        banned_user.is_banned = True
        topic = models.Topic('en', 'This is a test topic', 'Foobar', user)
        post1 = models.Post(topic, user, 'meh1')
        post2 = models.Post(topic, user, 'meh2')
        topic.accept_answer(post1)
        session.commit()

        visited_links = set()
        def visit(url):
            url = urljoin(BASE_URL, url).split('#', 1)[0]
            if not url.startswith(BASE_URL) or url in visited_links:
                return
            visited_links.add(url)
            path = '/' + url.split('/', 3)[-1]
            if path.startswith('/logout?'):
                return
            response = self.client.get(path, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            for link in html_xpath(response.html, '//html:a[@href]'):
                visit(link.attrib['href'])

        # logged out
        visit('/')
        self.assert_(len(visited_links) > MIN_VISITED)

        # logged in
        visited_links.clear()
        self.login('user1', 'default')
        visit('/')
        self.assert_(len(visited_links) > MIN_VISITED)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LinkCheckTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
    solace.tests.models
    ~~~~~~~~~~~~~~~~~~~

    Does the model tests.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import unittest
import datetime
from solace.tests import SolaceTestCase

from babel import Locale
from solace import models, settings
from solace.database import session


class ModelTestCase(SolaceTestCase):
    """Performs basic model tests"""

    def make_test_user(self, username='test user'):
        user = models.User(username, "foo@example.com")
        session.commit()
        return user

    def test_user_class_basic_operations(self):
        """Basic User operations"""
        user = self.make_test_user()
        self.assertEqual(user, models.User.query.get(user.id))
        self.assertEqual(user.check_password('something'), False)
        user.set_password('blafasel')
        self.assertEqual(user.check_password('blafasel'), True)
        self.assertEqual(user.check_password('blafasels'), False)

    def test_topic_creation_and_denormalization(self):
        """Topic creation and denormalization"""
        user = self.make_test_user()
        topic = models.Topic('en', 'This is a test topic', 'Foobar', user)
        self.assertEqual(topic.question.text, 'Foobar')
        self.assertEqual(topic.question.is_question, True)
        self.assertEqual(topic.question.is_answer, False)
        self.assertEqual(topic.title, 'This is a test topic')
        self.assertEqual(topic.last_change, topic.question.created)
        self.assertEqual(topic.is_answered, False)
        self.assertEqual(topic.votes, 0)
        self.assertEqual(topic.author, user)
        post1 = models.Post(topic, user, 'meh1')
        post2 = models.Post(topic, user, 'meh2')
        topic.accept_answer(post1)
        topic.accept_answer(post2)
        self.assertEqual(post1.is_answer, False)
        self.assertEqual(post2.is_answer, True)
        topic.accept_answer(None)
        self.assertEqual(post2.is_answer, False)

    def test_topic_voting(self):
        """Voting on topics"""
        user1 = self.make_test_user('user1')
        user2 = self.make_test_user('user2')
        topic = models.Topic('en', 'This is a test topic', 'Foobar', user1)
        session.commit()
        user1.upvote(topic)
        user2.upvote(topic)
        user2.upvote(topic)
        session.commit()
        self.assertEqual(topic.votes, 2)
        user2.downvote(topic.question)
        self.assertEqual(topic.votes, 0)
        user1.unvote(topic.question)
        self.assertEqual(topic.votes, -1)
        session.commit()

    def test_topic_replying_and_answering(self):
        """Replies to topics and answering"""
        user = self.make_test_user()
        topic = models.Topic('en', 'This is a test topic', 'Foobar', user)
        session.commit()
        topic_id = topic.id
        self.assertEqual(topic.last_change, topic.question.created)
        self.assertEqual(topic.is_answered, False)
        self.assertEqual(len(topic.posts), 1)
        models.Post(topic, user, 'This is more text')
        topic.accept_answer(models.Post(topic, user, 'And this is another answer'))
        self.assertEqual(topic.answer.is_answer, True)
        self.assertEqual(topic.answer.is_question, False)
        session.commit()

        def internal_test():
            self.assertEqual(len(topic.posts), 3)
            self.assertEqual(topic.answer_date, topic.answer.created)
            self.assertEqual(topic.answer_author, topic.answer.author)
            self.assertEqual(topic.last_change, topic.answer.created)
            self.assertEqual(topic.is_answered, True)

        # do the test now
        internal_test()
        topic = None
        session.remove()

        # and a second time with the queried data from the database
        topic = models.Topic.query.get(topic_id)
        internal_test()

        self.assertEqual(topic.reply_count, 2)

    def test_post_revisions(self):
        """Internal revisions for posts"""
        creator = self.make_test_user('creator')
        editor = self.make_test_user('editor')
        topic = models.Topic('en', 'Topic with revisions', 'Original text.', creator)
        session.commit()
        self.assertEqual(topic.question.revisions.count(), 0)
        topic.question.edit('New text with default params.')
        session.commit()
        self.assertEqual(topic.question.text, 'New text with default params.')
        rev = topic.question.revisions.first()
        self.assertEqual(rev.editor, creator)
        self.assertEqual(rev.date, topic.date)
        self.assertEqual(rev.text, 'Original text.')
        d = datetime.datetime.utcnow()
        topic.question.edit('From the editor', editor, d)
        session.commit()
        self.assertEqual(topic.question.author, creator)
        self.assertEqual(topic.question.editor, editor)
        self.assertEqual(topic.question.updated, d)
        self.assertEqual(topic.last_change, d)
        rev.restore()
        session.commit()
        self.assertEqual(topic.question.editor, rev.editor)
        self.assertEqual(topic.question.updated, rev.date)
        self.assertEqual(topic.question.text, rev.text)
        self.assertEqual(topic.question.edits, 3)

    def test_post_and_comment_rendering(self):
        """Posts and comments render text when set"""
        u = models.User('user', 'user@example.com', 'default')
        t = models.Topic('en', 'Test', 'foo **bar** baz', u)
        p = models.Post(t, u, 'foo //bar// baz')
        c = models.Comment(p, u, 'foo {{{bar}}} baz')
        self.assertEqual(t.question.rendered_text.strip(),
                         '<p>foo <strong>bar</strong> baz</p>')
        self.assertEqual(p.rendered_text.strip(),
                         '<p>foo <em>bar</em> baz</p>')
        self.assertEqual(c.rendered_text.strip(),
                         'foo <code>bar</code> baz')

    def test_basic_reputation_changes(self):
        """Basic reputation changes"""
        user1 = self.make_test_user('user1')
        user2 = self.make_test_user('user2')
        user3 = self.make_test_user('user3')
        user4 = self.make_test_user('user4')
        topic = models.Topic('en', 'This is a test topic', 'Foobar', user1)
        session.commit()
        user2.upvote(topic)
        user3.upvote(topic)
        session.commit()
        self.assertEqual(user1.reputation, 2)

        user4.downvote(topic)
        session.commit()
        self.assertEqual(user1.reputation, 0)
        self.assertEqual(user4.reputation, -1)

        topic.accept_answer(models.Post(topic, user4, 'blafasel'))
        session.commit()
        self.assertEqual(user4.reputation, 49)

        topic.accept_answer(models.Post(topic, user1, 'another answer'))
        user1.upvote(topic.answer)
        session.commit()
        self.assertEqual(user4.reputation, -1)
        self.assertEqual(user1.reputation, 60)

    def test_post_commenting(self):
        """Post commenting"""
        user = self.make_test_user()
        topic = models.Topic('en', 'This is a test topic', 'text', user)
        session.commit()
        self.assertEqual(topic.question.comment_count, 0)
        a = models.Comment(topic.question, user, 'Blafasel')
        session.commit()
        self.assertEqual(topic.question.comment_count, 1)
        b = models.Comment(topic.question, user, 'woooza')
        session.commit()
        self.assertEqual(topic.question.comment_count, 2)
        self.assertEqual(topic.question.comments, [a, b])

    def test_topic_tagging(self):
        """Topic tagging"""
        user = self.make_test_user()
        en_topic = models.Topic('en', 'This is a test topic', 'text', user)
        en_topic.bind_tags(['foo', 'bar', 'baz'])
        de_topic = models.Topic('de', 'This is a test topic', 'text', user)
        de_topic.bind_tags(['foo'])
        session.commit()
        foo = models.Tag.query.filter_by(locale=Locale('de'), name='foo').first()
        self.assertEqual(foo.name, 'foo')
        self.assertEqual(foo.tagged, 1)
        self.assertEqual(foo.topics.first(), de_topic)
        models.Topic('de', 'Another topic', 'text', user) \
            .bind_tags(['foo', 'bar'])
        session.commit()
        self.assertEqual(foo.tagged, 2)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ModelTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = querycount
# -*- coding: utf-8 -*-
"""
    solace.tests.querycount
    ~~~~~~~~~~~~~~~~~~~~~~~

    Counts the queries needed for a certain page.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import unittest
from random import choice
from solace.tests import SolaceTestCase

from solace import models, settings
from solace.database import session


class QueryCountTestCase(SolaceTestCase):

    def create_test_data(self, topics=20):
        # don't put ourselves into the query.  The user that logs in must not be
        # part of the generated content, otherwise we could end up with less
        # queries which would result in random failures
        me = models.User('me', 'me@example.com', 'default')
        users = []
        for x in xrange(5):
            username = 'user_%d' % x
            users.append(models.User(username, username + '@example.com'))
        for x in xrange(topics):
            t = models.Topic('en', 'Topic %d' % x, 'test contents', choice(users))
            for x in xrange(4):
                models.Post(t, choice(users), 'test contents')
        session.commit()

    def test_index_queries(self):
        """Number of queries for the index page under control"""
        self.create_test_data()

        # if one is logged out, we need two queries.  One for the topics that
        # are displayed and another one for the pagination count
        response = self.client.get('/en/')
        self.assertEqual(response.sql_query_count, 2)

        # if you're logged in, there is another query for the user needed and
        # another to check for messages from the database.
        self.login('me', 'default')
        response = self.client.get('/en/')
        self.assertEqual(response.sql_query_count, 4)

    def test_topic_view_queries(self):
        """Number of queries for the topic page under control"""
        self.create_test_data(topics=1)
        response = self.client.get('/en/topic/1', follow_redirects=True)

        # the topic page has to load everything in one query
        self.assertEqual(response.sql_query_count, 1)

        # and if we're logged in we have another one for the user
        # and a third for the vote cast status and a fourth to
        # check for messages from the database.
        self.login('me', 'default')
        response = self.client.get('/en/topic/1', follow_redirects=True)
        self.assertEqual(response.sql_query_count, 4)

    def test_userlist_queries(self):
        """Number of queries for the user list under control"""
        self.create_test_data(topics=1)
        response = self.client.get('/users/')
        # not being logged in we expect one query for the list and a
        # second for the limit.  If we are logged in we expect one or
        # two, depending on if the request user is on the page and if
        # it was accessed before the list was loaded, or later.
        self.assertEqual(response.sql_query_count, 2)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(QueryCountTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
"""
    solace.tests.signals
    ~~~~~~~~~~~~~~~~~~~~

    Tests the signal system.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
import re
import gc
import pickle
import unittest
import doctest
from solace.tests import SolaceTestCase

from solace import signals


signals.SIG('TEST_SIGNAL')


class SignalTestCase(SolaceTestCase):

    def test_simple_subscriptions(self):
        """Simple signal subscriptions"""
        sig = signals.Signal('FOO', ('a', 'b'))
        self.assertEqual(repr(sig), 'FOO')
        self.assertEqual(sig.args, ('a', 'b'))

        called = []
        def foo(a, b):
            called.append((a, b))

        sig.emit(a=1, b=2)
        self.assertEqual(called, [])

        sig.connect(foo)
        sig.emit(a=1, b=2)
        self.assertEqual(called, [(1, 2)])

        del foo
        gc.collect()

        sig.emit(a=3, b=4)
        self.assertEqual(called, [(1, 2)])

    def test_weak_method_subscriptions(self):
        """Weak method signal subscriptions"""
        called = []
        class Foo(object):
            def foo(self, a):
                called.append(a)
        f = Foo()

        sig = signals.Signal('FOO', ('a',))
        sig.connect(f.foo)
        sig.emit(a=42)

        self.assertEqual(called, [42])
        sig.disconnect(f.foo)

        del f
        gc.collect()

        sig.emit(a=23)
        self.assertEqual(called, [42])

    def test_temporary_subscriptions(self):
        """Temporary signal subscriptions"""
        called = []
        sig = signals.Signal('FOO')
        def foo():
            called.append(True)
        sig.emit()
        with signals.temporary_connection(foo, sig):
            sig.emit()
        sig.emit()
        self.assertEqual(len(called), 1)

    def test_pickle(self):
        """Signal pickling"""
        x = pickle.loads(pickle.dumps(TEST_SIGNAL))
        self.assert_(x is TEST_SIGNAL)

    def test_SIG(self):
        """Tests the `SIG` function"""
        self.assertEqual(repr(TEST_SIGNAL), 'solace.tests.signals.TEST_SIGNAL')

    def test_model_signals(self):
        """Model signalling"""
        from solace.models import User, session
        model_changes = []
        def listen(changes):
            model_changes.append(changes)
        signals.after_models_committed.connect(listen)

        me = User('A_USER', 'a-user@example.com')
        self.assertEqual(model_changes, [])
        session.rollback()
        self.assertEqual(model_changes, [])
        me = User('A_USER', 'a-user@example.com')
        self.assertEqual(model_changes, [])
        session.commit()
        self.assertEqual(model_changes, [[(me, 'insert')]])
        del model_changes[:]
        session.delete(me)
        session.commit()
        self.assertEqual(model_changes, [[(me, 'delete')]])

    def test_signal_introspection(self):
        """Signal introspection"""
        sig = signals.Signal('sig')
        self.assertEqual(sig.get_connections(), set())

        def on_foo():
            pass
        class Foo(object):
            def f(self):
                pass
        f = Foo()

        sig.connect(on_foo)
        sig.connect(f.f)

        self.assertEqual(sig.get_connections(), set([on_foo, f.f]))

        sig.disconnect(on_foo)
        self.assertEqual(sig.get_connections(), set([f.f]))

        del f
        gc.collect()
        self.assertEqual(sig.get_connections(), set())

    def test_broadcasting(self):
        """Broadcast signals"""
        on_signal = []
        def listen(signal, args):
            on_signal.append((signal, args))
        signals.broadcast.connect(listen)

        sig = signals.Signal('sig', ['foo'])
        sig.emit(foo=42)

        self.assertEqual(on_signal, [(sig, {'foo': 42})])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(signals))
    suite.addTest(unittest.makeSuite(SignalTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = templating
# -*- coding: utf-8 -*-
"""
    solace.tests.templating
    ~~~~~~~~~~~~~~~~~~~~~~~

    Tests the templating features.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from os.path import dirname, join
import unittest
import doctest

from solace.tests import SolaceTestCase
from solace import templating, models, settings


class TemplatingTestCase(SolaceTestCase):

    def test_simple_render(self):
        """Basic Template rendering."""
        me = models.User('me', 'me@example.com')
        rv = templating.render_template('mails/activate_user.txt', user=me,
                                        confirmation_url='MEH')
        self.assert_('Hi me!' in rv)
        self.assert_('MEH' in rv)
        self.assert_('See you soon on Solace' in rv)

    def test_theme_switches(self):
        """Theme based template switches."""
        settings.THEME_PATH.append(dirname(__file__))
        settings.THEME = 'test_theme'
        templating.refresh_theme()

        resp = self.client.get('/en/')
        self.assert_('I AM THE TEST THEME HEAD' in resp.data)
        self.assert_('_themes/test_theme' in resp.data)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TemplatingTestCase))
    suite.addTest(doctest.DocTestSuite(templating))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = validation
# -*- coding: utf-8 -*-
"""
    solace.tests.validation
    ~~~~~~~~~~~~~~~~~~~~~~~

    A unittest that validates the pages using the validator.nu HTML5
    validator.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re
import sys
import unittest
from simplejson import loads
from urllib2 import urlopen, Request, URLError
from urlparse import urljoin
from solace.tests import SolaceTestCase, html_xpath

from solace import models, settings
from solace.database import session


VALIDATOR_URL = 'http://html5.validator.nu/'
BASE_URL = 'http://localhost/'
MIN_VISITED = 12


class ValidatorTestCase(SolaceTestCase):

    def doExternalValidation(self, url, response, content_type):
        """Do the validation."""
        request = Request(VALIDATOR_URL + '?out=json',
                          response, {'Content-Type': content_type})
        response = urlopen(request)
        body = loads(response.read())
        response.close()

        for message in body['messages']:
            if message['type'] == 'error':
                detail = u'on line %s [%s]\n%s' % (
                    message['lastLine'],
                    message['extract'],
                    message['message']
                )
                self.fail((u'Got a validation error for %r:\n%s' %
                    (url, detail)).encode('utf-8'))

    def test_pages(self):
        """Make sure that all pages are valid HTML5"""
        settings.LANGUAGE_SECTIONS = ['en']
        user = models.User('user1', 'user1@example.com', 'default')
        user.active = True
        topic = models.Topic('en', 'This is a test topic', 'Foobar', user)
        post1 = models.Post(topic, user, 'meh1')
        post2 = models.Post(topic, user, 'meh2')
        topic.accept_answer(post1)
        session.commit()

        visited_links = set()
        def visit(url):
            url = urljoin(BASE_URL, url).split('#', 1)[0]
            if not url.startswith(BASE_URL) or url in visited_links:
                return
            visited_links.add(url)
            path = url.split('/', 3)[-1]
            response = self.client.get(path, follow_redirects=True)
            content_type = response.headers['Content-Type']
            if content_type.split(';')[0].strip() == 'text/html':
                self.doExternalValidation(url, response.data, content_type)
            for link in html_xpath(response.html, '//html:a[@href]'):
                visit(link.attrib['href'])

        self.login('user1', 'default')
        visit('/')


def suite():
    suite = unittest.TestSuite()
    # skip the test if the validator is not reachable
    try:
        urlopen(VALIDATOR_URL)
    except URLError:
        print >> sys.stderr, 'Skiping HTML5 validation tests'
        return suite
    suite.addTest(unittest.makeSuite(ValidatorTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""
    solace.urls
    ~~~~~~~~~~~

    Where do we want to point to?

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug.routing import Map, Rule as RuleBase, Submount


class Rule(RuleBase):

    def __gt__(self, endpoint):
        self.endpoint = endpoint
        return self


url_map = Map([
    # language dependent
    Submount('/<string(length=2):lang_code>', [
        Rule('/', defaults={'order_by': 'newest'}) > 'kb.overview',
        Rule('/<any(hot, votes, activity):order_by>') > 'kb.overview',
        Rule('/<any(newest, hot, votes, activity):order_by>.atom') > 'kb.overview_feed',
        Rule('/unanswered/', defaults={'order_by': 'newest'}) > 'kb.unanswered',
        Rule('/unanswered/<any(hot, votes, activity):order_by>') > 'kb.unanswered',
        Rule('/unanswered/<any(newest, hot, votes, activity):order_by>.atom') > 'kb.unanswered_feed',
        Rule('/new') > 'kb.new',
        Rule('/topic/<int:id>-<slug>') > 'kb.topic',
        Rule('/topic/<int:id>') > 'kb.topic',
        Rule('/topic/<int:id>.atom') > 'kb.topic_feed',
        Rule('/topic/<int:id>-<slug>.atom') > 'kb.topic_feed',
        Rule('/tags/') > 'kb.tags',
        Rule('/tags/<name>/', defaults={'order_by': 'newest'}) > 'kb.by_tag',
        Rule('/tags/<name>/<any(hot, votes, activity):order_by>') > 'kb.by_tag',
        Rule('/tags/<name>/<any(newest, hot, votes, activity):order_by>.atom') > 'kb.by_tag_feed',
        Rule('/post/<int:id>/edit') > 'kb.edit_post',
        Rule('/post/<int:id>/delete') > 'kb.delete_post',
        Rule('/post/<int:id>/restore') > 'kb.restore_post',
        Rule('/post/<int:id>/revisions') > 'kb.post_revisions',
        Rule('/users/') > 'kb.userlist'
    ]),

    # kb sections not depending on the lang code
    Rule('/sections/') > 'kb.sections',

    # the badges
    Rule('/badges/') > 'badges.show_list',
    Rule('/badges/<identifier>') > 'badges.show_badge',

    # user profiles
    Rule('/users/') > 'users.userlist',
    Rule('/users/<username>') > 'users.profile',
    Rule('/profile') > 'users.edit_profile',

    # core pages
    Rule('/') > 'core.language_redirect',
    Rule('/login') > 'core.login',
    Rule('/logout') > 'core.logout',
    Rule('/register') > 'core.register',
    Rule('/about') > 'core.about',
    Rule('/_reset_password') > 'core.reset_password',
    Rule('/_reset_password/<email>/<key>') > 'core.reset_password',
    Rule('/_activate/<email>/<key>') > 'core.activate_user',

    # administration
    Rule('/admin/') > 'admin.overview',
    Rule('/admin/status') > 'admin.status',
    Rule('/admin/bans') > 'admin.bans',
    Rule('/admin/ban/<user>') > 'admin.ban_user',
    Rule('/admin/unban/<user>') > 'admin.unban_user',
    Rule('/admin/users/') > 'admin.edit_users',
    Rule('/admin/users/<user>') > 'admin.edit_user',

    # AJAX
    Rule('/_set_language/<locale>') > 'core.set_language',
    Rule('/_set_timezone_offset') > 'core.set_timezone_offset',
    Rule('/_vote/<post>') > 'kb.vote',
    Rule('/_accept/<post>') > 'kb.accept',
    Rule('/_get_comments/<post>') > 'kb.get_comments',
    Rule('/_submit_comment/<post>') > 'kb.submit_comment',
    Rule('/_get_tags/<lang_code>') > 'kb.get_tags',
    Rule('/_no_javascript') > 'core.no_javascript',
    Rule('/_update_csrf_token') > 'core.update_csrf_token',
    Rule('/_request_exchange_token') > 'core.request_exchange_token',
    Rule('/_i18n/<lang>.js') > 'core.get_translations',

    # the API (version 1.0)
    Rule('/api/') > 'api.default_redirect',
    Submount('/api/1.0', [
        Rule('/') > 'api.help',
        Rule('/ping/<int:value>') > 'api.ping',
        Rule('/users/') > 'api.list_users',
        Rule('/users/<username>') > 'api.get_user',
        Rule('/users/+<int:user_id>') > 'api.get_user',
        Rule('/badges/') > 'api.list_badges',
        Rule('/badges/<identifier>') > 'api.get_badge',
        Rule('/questions/') > 'api.list_questions',
        Rule('/questions/<int:question_id>') > 'api.get_question',
        Rule('/replies/<int:reply_id>') > 'api.get_reply'
    ]),

    # support for theme resources.
    Rule('/_themes/<theme>/<file>') > 'themes.get_resource',

    # Build only stuff
    Rule('/_static/<file>', build_only=True) > 'static',
])

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
"""
    solace.utils.admin
    ~~~~~~~~~~~~~~~~~~

    Admin helpers.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from solace import settings
from solace.i18n import _
from solace.application import url_for
from solace.templating import render_template
from solace.utils.mail import send_email
from solace.models import User, session


def ban_user(user):
    """Bans a user if it was not already banned.  This also sends the
    user an email that he was banned.
    """
    if user.is_banned:
        return

    user.is_banned = True
    send_email(_(u'User account banned'),
               render_template('mails/user_banned.txt', user=user),
               user.email)
    session.commit()


def unban_user(user):
    """Unbans the user.  What this actually does is sending the user
    an email with a link to reactivate his account.  For reactivation
    he has to give himself a new password.
    """
    if not user.is_banned:
        return

    if settings.REQUIRE_NEW_PASSWORD_ON_UNBAN:
        user.is_active = False
    user.is_banned = False
    reset_url = url_for('core.reset_password', email=user.email,
                        key=user.password_reset_key, _external=True)
    send_email(_(u'Your ban was lifted'),
               render_template('mails/user_unbanned.txt', user=user,
                               reset_url=reset_url), user.email)
    session.commit()

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-
"""
    solace.utils.api
    ~~~~~~~~~~~~~~~~

    Provides basic helpers for the API.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re
import inspect
import simplejson
from xml.sax.saxutils import quoteattr
from functools import update_wrapper
from babel import Locale, UnknownLocaleError
from werkzeug.exceptions import MethodNotAllowed, BadRequest
from werkzeug import Response, escape

from solace.application import get_view
from solace.urls import url_map
from solace.templating import render_template
from solace.i18n import _, has_section
from solace.utils.remoting import remote_export_primitive
from solace.utils.formatting import format_creole


XML_NS = 'http://opensource.plurk.com/solace/'


_escaped_newline_re = re.compile(r'(?:(?:\\r)?\\n)')


def debug_dump(obj):
    """Dumps the data into a HTML page for debugging."""
    dump = _escaped_newline_re.sub('\n',
        simplejson.dumps(obj, ensure_ascii=False, indent=2))
    return render_template('api/debug_dump.html', dump=dump)


def dump_xml(obj):
    """Dumps data into a simple XML format."""
    def _dump(obj):
        if isinstance(obj, dict):
            d = dict(obj)
            obj_type = d.pop('#type', None)
            key = start = 'dict'
            if obj_type is not None:
                if obj_type.startswith('solace.'):
                    key = start = obj_type[7:]
                else:
                    start += ' type=%s' % quoteattr(obj_type)
            return u'<%s>%s</%s>' % (
                start,
                u''.join((u'<%s>%s</%s>' % (key, _dump(value), key)
                         for key, value in d.iteritems())),
                key
            )
        if isinstance(obj, (tuple, list)):
            def _item_dump(obj):
                if not isinstance(obj, (tuple, list, dict)):
                    return u'<item>%s</item>' % _dump(obj)
                return _dump(obj)
            return u'<list>%s</list>' % (u''.join(map(_item_dump, obj)))
        if isinstance(obj, bool):
            return obj and u'yes' or u'no'
        return escape(unicode(obj))
    return (
        u'<?xml version="1.0" encoding="utf-8"?>'
        u'<result xmlns="%s">%s</result>'
    ) % (XML_NS, _dump(obj))


def get_serializer(request):
    """Returns the serializer for the given API request."""
    format = request.args.get('format')
    if format is not None:
        rv = _serializer_map.get(format)
        if rv is None:
            raise BadRequest(_(u'Unknown format "%s"') % escape(format))
        return rv

    # webkit sends useless accept headers. They accept XML over
    # HTML or have no preference at all. We spotted them, so they
    # are obviously not regular API users, just ignore the accept
    # header and return the debug serializer.
    if request.user_agent.browser in ('chrome', 'safari'):
        return _serializer_map['debug']

    best_match = (None, 0)
    for mimetype, serializer in _serializer_for_mimetypes.iteritems():
        quality = request.accept_mimetypes[mimetype]
        if quality > best_match[1]:
            best_match = (serializer, quality)

    if best_match[0] is None:
        raise BadRequest(_(u'Could not detect format.  You have to specify '
                           u'the format as query argument or in the accept '
                           u'HTTP header.'))

    # special case.  If the best match is not html and the quality of
    # text/html is the same as the best match, we prefer HTML.
    if best_match[0] != 'text/html' and \
       best_match[1] == request.accept_mimetypes['text/html']:
        return _serializer_map['debug']

    return _serializer_map[best_match[0]]


def prepare_api_request(request):
    """Prepares the request for API usage."""
    request.in_api = True
    lang = request.args.get('lang')
    if lang is not None:
        if not has_section(lang):
            raise BadRequest(_(u'Unknown language'))
        request.locale = lang

    locale = request.args.get('locale')
    if locale is not None:
        try:
            locale = Locale.parse(locale)
            if not has_locale(locale):
                raise UnknownLocaleError()
        except UnknownLocaleError:
            raise BadRquest(_(u'Unknown locale'))
        request.view_lang = locale


def send_api_response(request, result):
    """Sends the API response."""
    ro = remote_export_primitive(result)
    serializer, mimetype = get_serializer(request)
    return Response(serializer(ro), mimetype=mimetype)


def api_method(methods=('GET',)):
    """Helper decorator for API methods."""
    def decorator(f):
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                raise MethodNotAllowed(methods)
            prepare_api_request(request)
            rv = f(request, *args, **kwargs)
            return send_api_response(request, rv)
        f.is_api_method = True
        f.valid_methods = tuple(methods)
        return update_wrapper(wrapper, f)
    return decorator


def list_api_methods():
    """List all API methods."""
    result = []
    for rule in url_map.iter_rules():
        if rule.build_only:
            continue
        view = get_view(rule.endpoint)
        if not getattr(view, 'is_api_method', False):
            continue
        handler = view.__name__
        if handler.startswith('api.'):
            handler = handler[4:]
        result.append(dict(
            handler=handler,
            valid_methods=view.valid_methods,
            doc=format_creole((inspect.getdoc(view) or '').decode('utf-8')),
            url=unicode(rule)
        ))
    result.sort(key=lambda x: (x['url'], x['handler']))
    return result


_serializer_for_mimetypes = {
    'application/json':     'json',
    'application/xml':      'xml',
    'text/xml':             'xml',
    'text/html':            'debug',
}
_serializer_map = {
    'json':     (simplejson.dumps, 'application/json'),
    'xml':      (dump_xml, 'application/xml'),
    'debug':    (debug_dump, 'text/html')
}

########NEW FILE########
__FILENAME__ = caching
# -*- coding: utf-8 -*-
"""
    solace.utils.caching
    ~~~~~~~~~~~~~~~~~~~~

    Implements cache helpers.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from functools import update_wrapper


def no_cache(f):
    """A decorator for views.  Adds no-cache headers to the response."""
    def new_view(request, *args, **kwargs):
        response = request.process_view_result(f(request, *args, **kwargs))
        response.headers.extend([
            ('Cache-Control', 'no-cache, must-revalidate'),
            ('Pragma', 'no-cache'),
            ('Expires', '-1')
        ])
        return response
    return update_wrapper(new_view, f)

########NEW FILE########
__FILENAME__ = csrf
# -*- coding: utf-8 -*-
"""
    solace.utils.csrf
    ~~~~~~~~~~~~~~~~~

    Implements helpers for the CSRF protection the form use.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
import hmac
from functools import update_wrapper
from zlib import adler32
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1
from werkzeug.exceptions import BadRequest
from solace import settings


#: the maximum number of csrf tokens kept in the session.  After that, the
#: oldest item is deleted
MAX_CSRF_TOKENS = 4


def csrf_url_hash(url):
    """A hash for a URL for the CSRF system."""
    if isinstance(url, unicode):
        url = url.encode('utf-8')
    return int(adler32(url) & 0xffffffff)


def random_token():
    """Creates a random token.  10 byte in size."""
    return os.urandom(10)


def exchange_token_protected(f):
    """Applies an exchange token check for each request to this view.  Using
    this also has the advantage that the URL generation system will
    automatically put the exchange token into the URL.
    """
    def new_view(request, *args, **kwargs):
        if request.values.get('_xt') != get_exchange_token(request):
            raise BadRequest()
        return f(request, *args, **kwargs)
    f.is_exchange_token_protected = True
    return update_wrapper(new_view, f)


def is_exchange_token_protected(f):
    """Is the given view function exchange token protected?"""
    return getattr(f, 'is_exchange_token_protected', False)


def get_exchange_token(request):
    """Returns a unique hash for the request.  This hash will always be the
    same as long as the user has not closed the session and can be used to
    protect "dangerous" pages that are triggered by `GET` requests.

    Exchange tokens have to be submitted as a URL or form parameter named
    `_xt`.

    This token is valid for one session only (it's based on the username
    and login time).
    """
    xt = request.session.get('xt', None)
    if xt is None:
        xt = request.session['xt'] = random_token().encode('hex')
    return xt


def get_csrf_token(request, url, force_update=False):
    """Return a CSRF token."""
    url_hash = csrf_url_hash(url)
    tokens = request.session.setdefault('csrf_tokens', [])
    token = None

    if not force_update:
        for stored_hash, stored_token in tokens:
            if stored_hash == url_hash:
                token = stored_token
                break
    if token is None:
        if len(tokens) >= MAX_CSRF_TOKENS:
            tokens.pop(0)

        token = random_token()
        tokens.append((url_hash, token))
        request.session.modified = True

    return token.encode('hex')


def invalidate_csrf_token(request, url):
    """Clears the CSRF token for the given URL."""
    url_hash = csrf_url_hash(url)
    tokens = request.session.get('csrf_tokens', None)
    if not tokens:
        return
    request.session['csrf_tokens'] = [(h, t) for h, t in tokens
                                      if h != url_hash]

########NEW FILE########
__FILENAME__ = ctxlocal
# -*- coding: utf-8 -*-
"""
    solace.utils.ctxlocal
    ~~~~~~~~~~~~~~~~~~~~~

    The context local that is used in the application and i18n system.  The
    application makes this request-bound.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug import Local, LocalManager


local = Local()
local_mgr = LocalManager([local])


class LocalProperty(object):
    """Class/Instance property that returns something from the local."""

    def __init__(self, name):
        self.__name__ = name

    def __get__(self, obj, type=None):
        return getattr(local, self.__name__, None)


# make sure the request local is removed at the end of the request
from solace.signals import after_request_shutdown
after_request_shutdown.connect(local_mgr.cleanup)

########NEW FILE########
__FILENAME__ = formatting
# -*- coding: utf-8 -*-
"""
    solace.utils.formatting
    ~~~~~~~~~~~~~~~~~~~~~~~

    Implements the formatting.  Uses creoleparser internally.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
import re
import creoleparser
from difflib import SequenceMatcher
from operator import itemgetter
from itertools import chain
from genshi.core import Stream, QName, Attrs, START, END, TEXT
from contextlib import contextmanager

from jinja2 import Markup


_leading_space_re = re.compile(r'^(\s+)(?u)')
_diff_split_re = re.compile(r'(\s+)(?u)')


_parser = creoleparser.Parser(
    dialect=creoleparser.create_dialect(creoleparser.creole10_base),
    method='html'
)


def format_creole(text, inline=False):
    """Format creole markup."""
    kwargs = {}
    if inline:
        kwargs['context'] = 'inline'
    return Markup(_parser.render(text, encoding=None, **kwargs))


def format_creole_diff(old, new):
    """Renders a creole diff for two texts."""
    differ = StreamDiffer(_parser.generate(old),
                          _parser.generate(new))
    return Markup(differ.get_diff_stream().render('html', encoding=None))


def longzip(a, b):
    """Like `izip` but yields `None` for missing items."""
    aiter = iter(a)
    biter = iter(b)
    try:
        for item1 in aiter:
            yield item1, biter.next()
    except StopIteration:
        for item1 in aiter:
            yield item1, None
    else:
        for item2 in biter:
            yield None, item2


class StreamDiffer(object):
    """A class that can diff a stream of Genshi events.  It will inject
    ``<ins>`` and ``<del>`` tags into the stream.  It probably breaks
    in very ugly ways if you pass a random Genshi stream to it.  I'm
    not exactly sure if it's correct what creoleparser is doing here,
    but it appears that it's not using a namespace.  That's fine with me
    so the tags the `StreamDiffer` adds are also unnamespaced.
    """

    def __init__(self, old_stream, new_stream):
        self._old = list(old_stream)
        self._new = list(new_stream)
        self._result = None
        self._stack = []
        self._context = None

    @contextmanager
    def context(self, kind):
        old_context = self._context
        self._context = kind
        try:
            yield
        finally:
            self._context = old_context

    def inject_class(self, attrs, classname):
        cls = attrs.get('class')
        attrs |= [(QName('class'), cls and cls + ' ' + classname or classname)]
        return attrs

    def append(self, type, data, pos):
        self._result.append((type, data, pos))

    def text_split(self, text):
        worditer = chain([u''], _diff_split_re.split(text))
        return [x + worditer.next() for x in worditer]

    def cut_leading_space(self, s):
        match = _leading_space_re.match(s)
        if match is None:
            return u'', s
        return match.group(), s[match.end():]

    def mark_text(self, pos, text, tag):
        ws, text = self.cut_leading_space(text)
        tag = QName(tag)
        if ws:
            self.append(TEXT, ws, pos)
        self.append(START, (tag, Attrs()), pos)
        self.append(TEXT, text, pos)
        self.append(END, tag, pos)

    def diff_text(self, pos, old_text, new_text):
        old = self.text_split(old_text)
        new = self.text_split(new_text)
        matcher = SequenceMatcher(None, old, new)

        def wrap(tag, words):
            return self.mark_text(pos, u''.join(words), tag)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                wrap('del', old[i1:i2])
                wrap('ins', new[j1:j2])
            elif tag == 'delete':
                wrap('del', old[i1:i2])
            elif tag == 'insert':
                wrap('ins', new[j1:j2])
            else:
                self.append(TEXT, u''.join(old[i1:i2]), pos)

    def replace(self, old_start, old_end, new_start, new_end):
        old = self._old[old_start:old_end]
        new = self._new[new_start:new_end]

        for idx, (old_event, new_event) in enumerate(longzip(old, new)):
            if old_event is None:
                self.insert(new_start + idx, new_end + idx)
                break
            elif new_event is None:
                self.delete(old_start + idx, old_end + idx)
                break

            # the best case.  We're in both cases dealing with the same
            # event type.  This is the easiest because all routines we
            # have can deal with that.
            if old_event[0] == new_event[0]:
                type = old_event[0]
                # start tags are easy.  handle them first.
                if type == START:
                    _, (tag, attrs), pos = new_event
                    self.enter_mark_replaced(pos, tag, attrs)
                # ends in replacements are a bit tricker, we try to
                # leave the new one first, then the old one.  One
                # should succeed.
                elif type == END:
                    _, tag, pos = new_event
                    if not self.leave(pos, tag):
                        self.leave(pos, old_event[1])
                # replaced text is internally diffed again
                elif type == TEXT:
                    _, new_text, pos = new_event
                    self.diff_text(pos, old_event[1], new_text)
                # for all other stuff we ignore the old event
                else:
                    self.append(*new_event)

            # ob boy, now the ugly stuff starts.  Let's handle the
            # easy one first.  If the old event was text and the
            # new one is the start or end of a tag, we just process
            # both of them.  The text is deleted, the rest is handled.
            elif old_event[0] == TEXT and new_event[0] in (START, END):
                _, text, pos = old_event
                self.mark_text(pos, text, 'del')
                type, data, pos = new_event
                if type == START:
                    self.enter(pos, *data)
                else:
                    self.leave(pos, data)

            # now the case that the old stream opened or closed a tag
            # that went away in the new one.  In this case we just
            # insert the text and totally ignore the fact that we had
            # a tag.  There is no way this could be rendered in a sane
            # way.
            elif old_event[0] in (START, END) and new_event[0] == TEXT:
                _, text, pos = new_event
                self.mark_text(pos, text, 'ins')

            # meh. no idea how to handle that, let's just say nothing
            # happened.
            else:
                pass

    def delete(self, start, end):
        with self.context('del'):
            self.block_process(self._old[start:end])

    def insert(self, start, end):
        with self.context('ins'):
            self.block_process(self._new[start:end])

    def unchanged(self, start, end):
        with self.context(None):
            self.block_process(self._old[start:end])

    def enter(self, pos, tag, attrs):
        self._stack.append(tag)
        self.append(START, (tag, attrs), pos)

    def enter_mark_replaced(self, pos, tag, attrs):
        attrs = self.inject_class(attrs, 'tagdiff_replaced')
        self._stack.append(tag)
        self.append(START, (tag, attrs), pos)

    def leave(self, pos, tag):
        if not self._stack:
            return False
        current_tag = self._stack[-1]
        if tag == self._stack[-1]:
            self.append(END, tag, pos)
            self._stack.pop()
            return True
        return False

    def leave_all(self):
        if self._stack:
            last_pos = (self._new or self._old)[-1][2]
            for tag in reversed(self._stack):
                self.append(END, tag, last_pos)
        del self._stack[:]

    def block_process(self, events):
        for event in events:
            type, data, pos = event
            if type == START:
                self.enter(pos, *data)
            elif type == END:
                self.leave(pos, data)
            elif type == TEXT:
                if self._context is not None and data.strip():
                    tag = QName(self._context)
                    self.append(START, (QName(tag), Attrs()), pos)
                    self.append(type, data, pos)
                    self.append(END, tag, pos)
                else:
                    self.append(type, data, pos)
            else:
                self.append(type, data, pos)

    def process(self):
        self._result = []
        matcher = SequenceMatcher(None, self._old, self._new)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                self.replace(i1, i2, j1, j2)
            elif tag == 'delete':
                self.delete(i1, i2)
            elif tag == 'insert':
                self.insert(j1, j2)
            else:
                self.unchanged(i1, i2)
        self.leave_all()

    def get_diff_stream(self):
        if self._result is None:
            self.process()
        return Stream(self._result)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
"""
    solace.forms
    ~~~~~~~~~~~~

    Implements the form handling.  The code here largely comes from the
    Zine form handling system, without the Zine dependency.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
                (c) 2009 by Plurk Inc., see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re
import string
from datetime import datetime
from itertools import chain, count
from functools import update_wrapper
from threading import Lock
from urlparse import urljoin

from werkzeug import html, MultiDict, redirect, cached_property

from jinja2 import Markup, escape

from solace import settings
from solace.i18n import _, ngettext, lazy_gettext
from solace.utils.support import OrderedDict
from solace.utils.recaptcha import get_recaptcha_html, validate_recaptcha
from solace.utils.csrf import get_csrf_token, invalidate_csrf_token


_last_position_hint = -1
_position_hint_lock = Lock()
_missing = object()
_tag_punct_re = re.compile(r'[\s%s]' % re.escape(string.punctuation))


class ValidationError(ValueError):
    """Exception raised when invalid data is encountered."""

    def __init__(self, message):
        if not isinstance(message, (list, tuple)):
            messages = [message]
        # make all items in the list unicode (this also evaluates
        # lazy translations in there)
        messages = map(unicode, messages)
        Exception.__init__(self, messages[0])
        self.messages = ErrorList(messages)

    def unpack(self, key=None):
        return {key: self.messages}


def fill_dict(_dict, **kwargs):
    """A helper to fill the dict passed with the items passed as keyword
    arguments if they are not yet in the dict.  If the dict passed was
    `None` a new dict is created and returned.

    This can be used to prepopulate initial dicts in overriden constructors:

        class MyForm(forms.Form):
            foo = forms.TextField()
            bar = forms.TextField()

            def __init__(self, initial=None):
                forms.Form.__init__(self, forms.fill_dict(initial,
                    foo="nothing",
                    bar="nothing"
                ))
    """
    if _dict is None:
        return kwargs
    for key, value in kwargs.iteritems():
        if key not in _dict:
            _dict[key] = value
    return _dict


def set_fields(obj, data, *fields):
    """Set all the fields on obj with data if changed."""
    for field in fields:
        value = data[field]
        if getattr(obj, field) != value:
            setattr(obj, field, value)


_next_position_hint = count().next


def _decode(data):
    """Decodes the flat dictionary d into a nested structure.

    >>> _decode({'foo': 'bar'})
    {'foo': 'bar'}
    >>> _decode({'foo.0': 'bar', 'foo.1': 'baz'})
    {'foo': ['bar', 'baz']}
    >>> data = _decode({'foo.bar': '1', 'foo.baz': '2'})
    >>> data == {'foo': {'bar': '1', 'baz': '2'}}
    True

    More complex mappings work too:

    >>> _decode({'foo.bar.0': 'baz', 'foo.bar.1': 'buzz'})
    {'foo': {'bar': ['baz', 'buzz']}}
    >>> _decode({'foo.0.bar': '23', 'foo.1.baz': '42'})
    {'foo': [{'bar': '23'}, {'baz': '42'}]}
    >>> _decode({'foo.0.0': '23', 'foo.0.1': '42'})
    {'foo': [['23', '42']]}
    >>> _decode({'foo': ['23', '42']})
    {'foo': ['23', '42']}

    _missing items in lists are ignored for convenience reasons:

    >>> _decode({'foo.42': 'a', 'foo.82': 'b'})
    {'foo': ['a', 'b']}

    This can be used for help client side DOM processing (inserting and
    deleting rows in dynamic forms).

    It also supports werkzeug's multi dicts:

    >>> _decode(MultiDict({"foo": ['1', '2']}))
    {'foo': ['1', '2']}
    >>> _decode(MultiDict({"foo.0": '1', "foo.1": '2'}))
    {'foo': ['1', '2']}

    Those two submission ways can also be used combined:

    >>> _decode(MultiDict({"foo": ['1'], "foo.0": '2', "foo.1": '3'}))
    {'foo': ['1', '2', '3']}

    This function will never raise exceptions except for argument errors
    but the recovery behavior for invalid form data is undefined.
    """
    list_marker = object()
    value_marker = object()

    if isinstance(data, MultiDict):
        listiter = data.iterlists()
    else:
        listiter = ((k, [v]) for k, v in data.iteritems())

    def _split_key(name):
        result = name.split('.')
        for idx, part in enumerate(result):
            if part.isdigit():
                result[idx] = int(part)
        return result

    def _enter_container(container, key):
        if key not in container:
            return container.setdefault(key, {list_marker: False})
        return container[key]

    def _convert(container):
        if value_marker in container:
            force_list = False
            values = container.pop(value_marker)
            if container.pop(list_marker):
                force_list = True
                values.extend(_convert(x[1]) for x in
                              sorted(container.items()))
            if not force_list and len(values) == 1:
                values = values[0]
            return values
        elif container.pop(list_marker):
            return [_convert(x[1]) for x in sorted(container.items())]
        return dict((k, _convert(v)) for k, v in container.iteritems())

    result = {list_marker: False}
    for key, values in listiter:
        parts = _split_key(key)
        if not parts:
            continue
        container = result
        for part in parts:
            last_container = container
            container = _enter_container(container, part)
            last_container[list_marker] = isinstance(part, (int, long))
        container[value_marker] = values[:]

    return _convert(result)


def _bind(obj, form, memo):
    """Helper for the field binding.  This is inspired by the way `deepcopy`
    is implemented.
    """
    if memo is None:
        memo = {}
    obj_id = id(obj)
    if obj_id in memo:
        return memo[obj_id]
    rv = obj._bind(form, memo)
    memo[obj_id] = rv
    return rv


def _force_dict(value):
    """If the value is not a dict, raise an exception."""
    if value is None or not isinstance(value, dict):
        return {}
    return value


def _force_list(value):
    """If the value is not a list, make it one."""
    if value is None:
        return []
    try:
        if isinstance(value, basestring):
            raise TypeError()
        return list(value)
    except TypeError:
        return [value]


def _make_widget(field, name, value, errors):
    """Shortcut for widget creation."""
    return field.widget(field, name, value, errors)


def _make_name(parent, child):
    """Joins a name."""
    if parent is None:
        result = child
    else:
        result = '%s.%s' % (parent, child)

    # try to return a ascii only bytestring if possible
    try:
        return str(result)
    except UnicodeError:
        return unicode(result)


def _to_string(value):
    """Convert a value to unicode, None means empty string."""
    if value is None:
        return u''
    return unicode(value)


def _to_list(value):
    """Similar to `_force_list` but always succeeds and never drops data."""
    if value is None:
        return []
    if isinstance(value, basestring):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _value_matches_choice(value, choice):
    """Checks if a given value matches a choice."""
    # this algorithm is also implemented in `MultiChoiceField.convert`
    # for better scaling with multiple items.  If it's changed here, it
    # must be changed for the multi choice field too.
    return choice == value or _to_string(choice) == _to_string(value)


def _iter_choices(choices):
    """Iterate over choices."""
    if choices is not None:
        for choice in choices:
            if not isinstance(choice, tuple):
                choice = (choice, choice)
            yield choice


def _is_choice_selected(field, value, choice):
    """Checks if a choice is selected.  If the field is a multi select
    field it's checked if the choice is in the passed iterable of values,
    otherwise it's checked if the value matches the choice.
    """
    if field.multiple_choices:
        for value in value:
            if _value_matches_choice(value, choice):
                return True
        return False
    return _value_matches_choice(value, choice)


class _Renderable(object):
    """Mixin for renderable HTML objects."""

    def render(self):
        return u''

    def __call__(self, *args, **kwargs):
        return self.render(*args, **kwargs)


class Widget(_Renderable):
    """Baseclass for all widgets.  All widgets share a common interface
    that can be used from within templates.

    Take this form as an example:

    >>> class LoginForm(Form):
    ...     username = TextField(required=True)
    ...     password = TextField(widget=PasswordInput)
    ...     flags = MultiChoiceField(choices=[1, 2, 3])
    ...
    >>> form = LoginForm()
    >>> form.validate({'username': '', 'password': '',
    ...                'flags': [1, 3]})
    False
    >>> widget = form.as_widget()

    You can get the subwidgets by using the normal indexing operators:

    >>> username = widget['username']
    >>> password = widget['password']

    To render a widget you can usually invoke the `render()` method.  All
    keyword parameters are used as HTML attribute in the resulting tag.
    You can also call the widget itself (``username()`` instead of
    ``username.render()``) which does the same if there are no errors for
    the field but adds the default error list after the widget if there
    are errors.

    Widgets have some public attributes:

    `errors`

        gives the list of errors:

        >>> username.errors
        [u'This field is required.']

        This error list is printable:

        >>> print username.errors()
        <ul class="errors"><li>This field is required.</li></ul>

        Like any other sequence that yields list items it provides
        `as_ul` and `as_ol` methods:

        >>> print username.errors.as_ul()
        <ul><li>This field is required.</li></ul>

        Keep in mind that ``widget.errors()`` is equivalent to
        ``widget.errors.as_ul(class_='errors', hide_empty=True)``.

    `value`

        returns the value of the widget as primitive.  For basic
        widgets this is always a string, for widgets with subwidgets or
        widgets with multiple values a dict or a list:

        >>> username.value
        u''
        >>> widget['flags'].value
        [u'1', u'3']

    `name` gives you the name of the field for form submissions:

        >>> username.name
        'username'

        Please keep in mind that the name is not always that obvious.  This
        form system supports nested form fields so it's a good idea to
        always use the name attribute.

    `id`

        gives you the default domain for the widget.  This is either none
        if there is no idea for the field or `f_` + the field name with
        underscores instead of dots:

        >>> username.id
        'f_username'

    `all_errors`

        like `errors` but also contains the errors of child
        widgets.
    """

    disable_dt = False

    def __init__(self, field, name, value, all_errors):
        self._field = field
        self._value = value
        self._all_errors = all_errors
        self.name = name

    def hidden(self):
        """Return one or multiple hidden fields for the current value.  This
        also handles subwidgets.  This is useful for transparent form data
        passing.
        """
        fields = []

        def _add_field(name, value):
            fields.append(html.input(type='hidden', name=name, value=value))

        def _to_hidden(value, name):
            if isinstance(value, list):
                for idx, value in enumerate(value):
                    _to_hidden(value, _make_name(name, idx))
            elif isinstance(value, dict):
                for key, value in value.iteritems():
                    _to_hidden(value, _make_name(name, key))
            else:
                _add_field(name, value)

        _to_hidden(self.value, self.name)
        return Markup(u'\n'.join(fields))

    @property
    def localname(self):
        """The local name of the field."""
        return self.name.rsplit('.', 1)[-1]

    @property
    def id(self):
        """The proposed id for this widget."""
        if self.name is not None:
            return 'f_' + self.name.replace('.', '__')

    @property
    def value(self):
        """The primitive value for this widget."""
        return self._field.to_primitive(self._value)

    @property
    def label(self):
        """The label for the widget."""
        if self._field.label is not None:
            return Label(unicode(self._field.label), self.id)

    @property
    def help_text(self):
        """The help text of the widget."""
        if self._field.help_text is not None:
            return unicode(self._field.help_text)

    @property
    def errors(self):
        """The direct errors of this widget."""
        if self.name in self._all_errors:
            return self._all_errors[self.name]
        return ErrorList()

    @property
    def all_errors(self):
        """The current errors and the errors of all child widgets."""
        items = sorted(self._all_errors.items())
        if self.name is None:
            return ErrorList(chain(*(item[1] for item in items)))
        result = ErrorList()
        for key, value in items:
            if key == self.name or (key is not None and
                                    key.startswith(self.name + '.')):
                result.extend(value)
        return result

    @property
    def default_display_errors(self):
        """The errors that should be displayed."""
        return self.errors

    def as_dd(self, **attrs):
        """Return a dt/dd item."""
        rv = []
        if not self.disable_dt:
            label = self.label
            if label:
                rv.append(html.dt(label()))
        rv.append(html.dd(self(**attrs)))
        if self.help_text:
            rv.append(html.dd(self.help_text, class_='explanation'))
        return Markup(u''.join(rv))

    def _attr_setdefault(self, attrs):
        """Add an ID to the attrs if there is none."""
        if 'id' not in attrs and self.id is not None:
            attrs['id'] = self.id

    def __call__(self, **attrs):
        """The default display is the form + error list as ul if needed."""
        return self.render(**attrs) + self.default_display_errors()


class Label(_Renderable):
    """Holds a label."""

    def __init__(self, text, linked_to=None):
        self.text = text
        self.linked_to = linked_to

    def render(self, **attrs):
        attrs.setdefault('for', self.linked_to)
        return Markup(html.label(escape(self.text), **attrs))


class InternalWidget(Widget):
    """Special widgets are widgets that can't be used on arbitrary
    form fields but belong to others.
    """

    def __init__(self, parent):
        self._parent = parent

    value = name = None
    errors = all_errors = property(lambda x: ErrorList())


class Input(Widget):
    """A widget that is a HTML input field."""
    hide_value = False
    type = None

    def render(self, **attrs):
        self._attr_setdefault(attrs)
        value = self.value
        if self.hide_value:
            value = u''
        return Markup(html.input(name=self.name, value=value, type=self.type,
                                 **attrs))


class TextInput(Input):
    """A widget that holds text."""
    type = 'text'


class PasswordInput(TextInput):
    """A widget that holds a password."""
    type = 'password'
    hide_value = True


class HiddenInput(Input):
    """A hidden input field for text."""
    type = 'hidden'


class Textarea(Widget):
    """Displays a textarea."""

    @property
    def default_display_errors(self):
        """A textarea is often used with multiple, it makes sense to
        display the errors of all childwidgets then which are not
        renderable because they are text.
        """
        return self.all_errors

    def _attr_setdefault(self, attrs):
        Widget._attr_setdefault(self, attrs)
        attrs.setdefault('rows', 8)
        attrs.setdefault('cols', 40)

    def render(self, **attrs):
        self._attr_setdefault(attrs)
        return Markup(html.textarea(self.value, name=self.name, **attrs))


class Checkbox(Widget):
    """A simple checkbox."""

    @property
    def checked(self):
        return self.value != u'False'

    def with_help_text(self, **attrs):
        """Render the checkbox with help text."""
        data = self(**attrs)
        if self.help_text:
            data += u' ' + html.label(self.help_text, class_='explanation',
                                      for_=self.id)
        return Markup(data)

    def as_dd(self, **attrs):
        """Return a dt/dd item."""
        rv = []
        label = self.label
        if label:
            rv.append(html.dt(label()))
        rv.append(html.dd(self.with_help_text()))
        return Markup(u''.join(rv))

    def as_li(self, **attrs):
        """Return a li item."""
        rv = [self.render(**attrs)]
        if self.label:
            rv.append(u' ' + self.label())
        if self.help_text:
            rv.append(html.div(self.help_text, class_='explanation'))
        rv.append(self.default_display_errors())
        return Markup(html.li(u''.join(rv)))

    def render(self, **attrs):
        self._attr_setdefault(attrs)
        return Markup(html.input(name=self.name, type='checkbox',
                                 checked=self.checked, **attrs))


class SelectBox(Widget):
    """A select box."""

    def _attr_setdefault(self, attrs):
        Widget._attr_setdefault(self, attrs)
        attrs.setdefault('multiple', self._field.multiple_choices)

    def render(self, **attrs):
        self._attr_setdefault(attrs)
        items = []
        for choice in self._field.choices:
            if isinstance(choice, tuple):
                key, value = choice
            else:
                key = value = choice
            selected = _is_choice_selected(self._field, self.value, key)
            items.append(html.option(unicode(value), value=unicode(key),
                                     selected=selected))
        return Markup(html.select(name=self.name, *items, **attrs))


class _InputGroupMember(InternalWidget):
    """A widget that is a single radio button."""

    # override the label descriptor
    label = None
    inline_label = True

    def __init__(self, parent, value, label):
        InternalWidget.__init__(self, parent)
        self.value = unicode(value)
        self.label = Label(label, self.id)

    @property
    def name(self):
        return self._parent.name

    @property
    def id(self):
        return 'f_%s_%s' % (self._parent.name, self.value)

    @property
    def checked(self):
        return _is_choice_selected(self._parent._field, self._parent.value,
                                   self.value)

    def render(self, **attrs):
        self._attr_setdefault(attrs)
        return Markup(html.input(type=self.type, name=self.name,
                                 value=self.value, checked=self.checked,
                                 **attrs))


class RadioButton(_InputGroupMember):
    """A radio button in an input group."""
    type = 'radio'


class GroupCheckbox(_InputGroupMember):
    """A checkbox in an input group."""
    type = 'checkbox'


class _InputGroup(Widget):

    def __init__(self, field, name, value, all_errors):
        Widget.__init__(self, field, name, value, all_errors)
        self.choices = []
        self._subwidgets = {}
        for value, label in _iter_choices(self._field.choices):
            widget = self.subwidget(self, value, label)
            self.choices.append(widget)
            self._subwidgets[value] = widget

    def __getitem__(self, value):
        """Return a subwidget."""
        return self._subwidgets[value]

    def _as_list(self, list_type, attrs):
        if attrs.pop('hide_empty', False) and not self.choices:
            return u''
        self._attr_setdefault(attrs)
        empty_msg = attrs.pop('empty_msg', None)
        label = not attrs.pop('nolabel', False)
        class_ = attrs.pop('class_', attrs.pop('class', None))
        if class_ is None:
            class_ = 'choicegroup'
        attrs['class'] = class_
        choices = [u'<li>%s %s</li>' % (
            choice(),
            label and choice.label() or u''
        ) for choice in self.choices]
        if not choices:
            if empty_msg is None:
                empty_msg = _('No choices.')
            choices.append(u'<li>%s</li>' % _(empty_msg))
        return Markup(list_type(*choices, **attrs))

    def as_ul(self, **attrs):
        """Render the radio buttons widget as <ul>"""
        return self._as_list(html.ul, attrs)

    def as_ol(self, **attrs):
        """Render the radio buttons widget as <ol>"""
        return self._as_list(html.ol, attrs)

    def as_table(self, **attrs):
        """Render the radio buttons widget as <table>"""
        self._attr_setdefault(attrs)
        return Markup(list_type(*[u'<tr><td>%s</td><td>%s</td></tr>' % (
            choice,
            choice.label
        ) for choice in self.choices], **attrs))

    def render(self, **attrs):
        return self.as_ul(**attrs)


class RadioButtonGroup(_InputGroup):
    """A group of radio buttons."""
    subwidget = RadioButton


class CheckboxGroup(_InputGroup):
    """A group of checkboxes."""
    subwidget = GroupCheckbox


class MappingWidget(Widget):
    """Special widget for dict-like fields."""

    def __init__(self, field, name, value, all_errors):
        Widget.__init__(self, field, name, _force_dict(value), all_errors)
        self._subwidgets = {}

    def __getitem__(self, name):
        subwidget = self._subwidgets.get(name)
        if subwidget is None:
            # this could raise a KeyError we pass through
            subwidget = _make_widget(self._field.fields[name],
                                     _make_name(self.name, name),
                                     self._value.get(name),
                                     self._all_errors)
            self._subwidgets[name] = subwidget
        return subwidget

    def as_dl(self, **attrs):
        return Markup(html.dl(*[x.as_dd() for x in self], **attrs))

    def __call__(self, *args, **kwargs):
        return self.as_dl(*args, **kwargs)

    def __iter__(self):
        for key in self._field.fields:
            yield self[key]


class FormWidget(MappingWidget):
    """A widget for forms."""

    def get_hidden_fields(self):
        """This method is called by the `hidden_fields` property to return
        a list of (key, value) pairs for the special hidden fields.
        """
        fields = []
        if self._field.form.request is not None:
            if self._field.form.csrf_protected:
                fields.append(('_csrf_token', self.csrf_token))
            if self._field.form.redirect_tracking:
                target = self.redirect_target
                if target is not None:
                    fields.append(('_redirect_target', target))
        return fields

    @property
    def hidden_fields(self):
        """The hidden fields as string."""
        return Markup(u''.join(html.input(type='hidden', name=name, value=value)
                               for name, value in self.get_hidden_fields()))

    @cached_property
    def captcha(self):
        """The captcha if one exists for this form."""
        if self._field.form.captcha_protected:
            return get_recaptcha_html()

    @property
    def csrf_token(self):
        """Forward the CSRF check token for templates."""
        return self._field.form.csrf_token

    @property
    def redirect_target(self):
        """The redirect target for this form."""
        return self._field.form.redirect_target

    def default_actions(self, **attrs):
        """Returns a default action div with a submit button."""
        label = attrs.pop('label', None)
        if label is None:
            label = _('Submit')
        attrs.setdefault('class', 'actions')
        return Markup(html.div(html.input(type='submit', value=label), **attrs))

    def render(self, method=None, **attrs):
        self._attr_setdefault(attrs)
        with_errors = attrs.pop('with_errors', False)
        if method is None:
            method = self._field.form.default_method.lower()

        # support jinja's caller
        caller = attrs.pop('caller', None)
        if caller is not None:
            body = caller()
        else:
            body = self.as_dl() + self.default_actions()

        hidden = self.hidden_fields
        if hidden:
            # if there are hidden fields we put an invisible div around
            # it.  the HTML standard doesn't allow input fields as direct
            # childs of a <form> tag...
            body = Markup('<div style="display: none">%s</div>%s') % (hidden, body)

        if with_errors:
            body = self.default_display_errors() + body
        return Markup(html.form(body, action=self._field.form.action,
                                method=method, **attrs))

    def __call__(self, *args, **attrs):
        attrs.setdefault('with_errors', True)
        return self.render(*args, **attrs)


class ListWidget(Widget):
    """Special widget for list-like fields."""

    def __init__(self, field, name, value, all_errors):
        Widget.__init__(self, field, name, _force_list(value), all_errors)
        self._subwidgets = {}

    def as_ul(self, **attrs):
        return self._as_list(html.ul, attrs)

    def as_ol(self, **attrs):
        return self._as_list(html.ol, attrs)

    def _as_list(self, factory, attrs):
        if attrs.pop('hide_empty', False) and not self:
            return u''
        items = []
        for index in xrange(len(self) + attrs.pop('extra_rows', 1)):
            items.append(html.li(self[index]()))
        return Markup(factory(*items, **attrs))

    def __getitem__(self, index):
        if not isinstance(index, (int, long)):
            raise TypeError('list widget indices must be integers')
        subwidget = self._subwidgets.get(index)
        if subwidget is None:
            try:
                value = self._value[index]
            except IndexError:
                # return an widget without value if we try
                # to access a field not in the list
                value = None
            subwidget = _make_widget(self._field.field,
                                     _make_name(self.name, index), value,
                                     self._all_errors)
            self._subwidgets[index] = subwidget
        return subwidget

    def __iter__(self):
        for index in xrange(len(self)):
            yield self[index]

    def __len__(self):
        return len(self._value)

    def __call__(self, *args, **kwargs):
        return self.as_ul(*args, **kwargs)


class ErrorList(_Renderable, list):
    """The class that is used to display the errors."""

    def render(self, **attrs):
        return self.as_ul(**attrs)

    def as_ul(self, **attrs):
        return self._as_list(html.ul, attrs)

    def as_ol(self, **attrs):
        return self._as_list(html.ol, attrs)

    def _as_list(self, factory, attrs):
        if attrs.pop('hide_empty', False) and not self:
            return u''
        return Markup(factory(*(html.li(item) for item in self), **attrs))

    def __call__(self, **attrs):
        attrs.setdefault('class', attrs.pop('class_', 'errors'))
        attrs.setdefault('hide_empty', True)
        return self.render(**attrs)


class MultipleValidationErrors(ValidationError):
    """A validation error subclass for multiple errors raised by
    subfields.  This is used by the mapping and list fields.
    """

    def __init__(self, errors):
        ValidationError.__init__(self, '%d error%s' % (
            len(errors), len(errors) != 1 and 's' or ''
        ))
        self.errors = errors

    def __unicode__(self):
        return ', '.join(map(unicode, self.errors.itervalues()))

    def unpack(self, key=None):
        rv = {}
        for name, error in self.errors.iteritems():
            rv.update(error.unpack(_make_name(key, name)))
        return rv


class FieldMeta(type):

    def __new__(cls, name, bases, d):
        messages = {}
        for base in reversed(bases):
            if hasattr(base, 'messages'):
                messages.update(base.messages)
        if 'messages' in d:
            messages.update(d['messages'])
        d['messages'] = messages
        return type.__new__(cls, name, bases, d)


class Field(object):
    """Abstract field base class."""

    __metaclass__ = FieldMeta
    messages = dict(required=lazy_gettext('This field is required.'))
    form = None
    widget = TextInput

    # these attributes are used by the widgets to get an idea what
    # choices to display.  Not every field will also validate them.
    multiple_choices = False
    choices = ()

    # fields that have this attribute set get special treatment on
    # validation.  It means that even though a value was not in the
    # submitted data it's validated against a default value.
    validate_on_omission = False

    def __init__(self, label=None, help_text=None, validators=None,
                 widget=None, messages=None):
        self._position_hint = _next_position_hint()
        self.label = label
        self.help_text = help_text
        if validators is None:
            validators = []
        self.validators = validators
        self.custom_converter = None
        if widget is not None:
            self.widget = widget
        if messages:
            self.messages = self.messages.copy()
            self.messages.update(messages)
        assert not issubclass(self.widget, InternalWidget), \
            'can\'t use internal widgets as widgets for fields'

    def __call__(self, value):
        value = self.convert(value)
        self.apply_validators(value)
        return value

    def __copy__(self):
        return _bind(self, None, None)

    def apply_validators(self, value):
        """Applies all validators on the value."""
        if self.should_validate(value):
            for validate in self.validators:
                validate(self.form, value)

    def should_validate(self, value):
        """Per default validate if the value is not None.  This method is
        called before the custom validators are applied to not perform
        validation if the field is empty and not required.

        For example a validator like `is_valid_ip` is never called if the
        value is an empty string and the field hasn't raised a validation
        error when checking if the field is required.
        """
        return value is not None

    def convert(self, value):
        """This can be overridden by subclasses and performs the value
        conversion.
        """
        return _to_string(value)

    def to_primitive(self, value):
        """Convert a value into a primitve (string or a list/dict of lists,
        dicts or strings).

        This method must never fail!
        """
        return _to_string(value)

    def _bind(self, form, memo):
        """Method that binds a field to a form. If `form` is None, a copy of
        the field is returned."""
        if form is not None and self.bound:
            raise TypeError('%r already bound' % type(obj).__name__)
        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        rv.validators = self.validators[:]
        rv.messages = self.messages.copy()
        if form is not None:
            rv.form = form
        return rv

    @property
    def bound(self):
        """True if the form is bound."""
        return 'form' in self.__dict__

    def __repr__(self):
        rv = object.__repr__(self)
        if self.bound:
            rv = rv[:-1] + ' [bound]>'
        return rv


class Mapping(Field):
    """Apply a set of fields to a dictionary of values.

    >>> field = Mapping(name=TextField(), age=IntegerField())
    >>> field({'name': u'John Doe', 'age': u'42'})
    {'age': 42, 'name': u'John Doe'}

    Although it's possible to reassign the widget after field construction
    it's not recommended because the `MappingWidget` is the only builtin
    widget that is able to handle mapping structures.
    """

    widget = MappingWidget

    def __init__(self, *args, **fields):
        Field.__init__(self)
        if len(args) == 1:
            if fields:
                raise TypeError('keyword arguments and dict given')
            self.fields = OrderedDict(args[0])
        else:
            if args:
                raise TypeError('no positional arguments allowed if keyword '
                                'arguments provided.')
            self.fields = OrderedDict(fields)
        self.fields.sort(key=lambda i: i[1]._position_hint)

    def convert(self, value):
        value = _force_dict(value)
        errors = {}
        result = {}
        for name, field in self.fields.iteritems():
            try:
                result[name] = field(value.get(name))
            except ValidationError, e:
                errors[name] = e
        if errors:
            raise MultipleValidationErrors(errors)
        return result

    def to_primitive(self, value):
        value = _force_dict(value)
        result = {}
        for key, field in self.fields.iteritems():
            result[key] = field.to_primitive(value.get(key))
        return result

    def _bind(self, form, memo):
        rv = Field._bind(self, form, memo)
        rv.fields = OrderedDict()
        for key, field in self.fields.iteritems():
            rv.fields[key] = _bind(field, form, memo)
        return rv


class FormMapping(Mapping):
    """Like a mapping but does csrf protection and stuff."""

    widget = FormWidget

    def convert(self, value):
        if self.form is None:
            raise TypeError('form mapping without form passed is unable '
                            'to convert data')
        if self.form.csrf_protected and self.form.request is not None:
            token = self.form.request.values.get('_csrf_token')
            if token != self.form.csrf_token:
                raise ValidationError(_(u'Form submitted multiple times or '
                                        u'session expired.  Try again.'))
        if self.form.captcha_protected:
            request = self.form.request
            if request is None:
                raise RuntimeError('captcha protected forms need a request')
            if not validate_recaptcha(request.values.get('recaptcha_challenge_field'),
                                      request.values.get('recaptcha_response_field'),
                                      request.remote_addr):
                raise ValidationError(_('You entered an invalid captcha.'))
        return Mapping.convert(self, value)


class FormAsField(Mapping):
    """If a form is converted into a field the returned field object is an
    instance of this class.  The behavior is mostly equivalent to a normal
    :class:`Mapping` field with the difference that it as an attribute called
    :attr:`form_class` that points to the form class it was created from.
    """

    def __init__(self):
        raise TypeError('can\'t create %r instances' %
                        self.__class__.__name__)


class Multiple(Field):
    """Apply a single field to a sequence of values.

    >>> field = Multiple(IntegerField())
    >>> field([u'1', u'2', u'3'])
    [1, 2, 3]

    Recommended widgets:

    -   `ListWidget` -- the default one and useful if multiple complex
        fields are in use.
    -   `CheckboxGroup` -- useful in combination with choices
    -   `SelectBoxWidget` -- useful in combination with choices
    """

    widget = ListWidget
    messages = dict(too_small=None, too_big=None)
    validate_on_omission = True

    def __init__(self, field, label=None, help_text=None, min_size=None,
                 max_size=None, validators=None, widget=None, messages=None):
        Field.__init__(self, label, help_text, validators, widget, messages)
        self.field = field
        self.min_size = min_size
        self.max_size = max_size

    @property
    def multiple_choices(self):
        return self.max_size is None or self.max_size > 1

    def convert(self, value):
        value = _force_list(value)
        if self.min_size is not None and len(value) < self.min_size:
            message = self.messages['too_small']
            if message is None:
                message = ngettext(u'Please provide at least %d item.',
                                   u'Please provide at least %d items.',
                                   self.min_size) % self.min_size
            raise ValidationError(message)
        if self.max_size is not None and len(value) > self.max_size:
            message = self.messages['too_big']
            if message is None:
                message = ngettext(u'Please provide no more than %d item.',
                                   u'Please provide no more than %d items.',
                                   self.max_size) % self.max_size
            raise ValidationError(message)
        result = []
        errors = {}
        for idx, item in enumerate(value):
            try:
                result.append(self.field(item))
            except ValidationError, e:
                errors[idx] = e
        if errors:
            raise MultipleValidationErrors(errors)
        return result

    def to_primitive(self, value):
        return map(self.field.to_primitive, _force_list(value))

    def _bind(self, form, memo):
        rv = Field._bind(self, form, memo)
        rv.field = _bind(self.field, form, memo)
        return rv


class CommaSeparated(Multiple):
    """Works like the multiple field but for comma separated values:

    >>> field = CommaSeparated(IntegerField())
    >>> field(u'1, 2, 3')
    [1, 2, 3]

    The default widget is a `TextInput` but `Textarea` would be a possible
    choices as well.
    """

    widget = TextInput

    def __init__(self, field, label=None, help_text=None, min_size=None,
                 max_size=None, sep=u',', validators=None, widget=None,
                 messages=None):
        Multiple.__init__(self, field, label, help_text, min_size,
                          max_size, validators, widget, messages)
        self.sep = sep

    def convert(self, value):
        if isinstance(value, basestring):
            value = filter(None, [x.strip() for x in value.split(self.sep)])
        return Multiple.convert(self, value)

    def to_primitive(self, value):
        if value is None:
            return u''
        if isinstance(value, basestring):
            return value
        return (self.sep + u' ').join(map(self.field.to_primitive, value))


class LineSeparated(Multiple):
    r"""Works like `CommaSeparated` but uses multiple lines:

    >>> field = LineSeparated(IntegerField())
    >>> field(u'1\n2\n3')
    [1, 2, 3]

    The default widget is a `Textarea` and taht is pretty much the only thing
    that makes sense for this widget.
    """
    widget = Textarea

    def convert(self, value):
        if isinstance(value, basestring):
            value = filter(None, [x.strip() for x in value.splitlines()])
        return Multiple.convert(self, value)

    def to_primitive(self, value):
        if value is None:
            return u''
        if isinstance(value, basestring):
            return value
        return u'\n'.join(map(self.field.to_primitive, value))


class TextField(Field):
    """Field for strings.

    >>> field = TextField(required=True, min_length=6)
    >>> field('foo bar')
    u'foo bar'
    >>> field('')
    Traceback (most recent call last):
      ...
    ValidationError: This field is required.
    """

    messages = dict(too_short=None, too_long=None)

    def __init__(self, label=None, help_text=None, required=False,
                 min_length=None, max_length=None, validators=None,
                 widget=None, messages=None):
        Field.__init__(self, label, help_text, validators, widget, messages)
        self.required = required
        self.min_length = min_length
        self.max_length = max_length

    def convert(self, value):
        value = _to_string(value)
        if self.required:
            if not value:
                raise ValidationError(self.messages['required'])
        if value:
            if self.min_length is not None and len(value) < self.min_length:
                message = self.messages['too_short']
                if message is None:
                    message = ngettext(u'Please enter at least %d character.',
                                       u'Please enter at least %d characters.',
                                       self.min_length) % self.min_length
                raise ValidationError(message)
            if self.max_length is not None and len(value) > self.max_length:
                message = self.messages['too_long']
                if message is None:
                    message = ngettext(u'Please enter no more than %d character.',
                                       u'Please enter no more than %d characters.',
                                       self.max_length) % self.max_length
                raise ValidationError(message)
        return value

    def should_validate(self, value):
        """Validate if the string is not empty."""
        return bool(value)


class TagField(TextField):
    """Like a text field but with normalization rules for tags.

    >>> field = TagField(required=True)
    >>> field('Foo  bar baz')
    u'foo-bar-baz'
    >>> field('')
    Traceback (most recent call last):
      ...
    ValidationError: This field is required.
    """

    def __init__(self, label=None, help_text=None, required=False,
                 validators=None, widget=None, messages=None):
        TextField.__init__(self, label, help_text, required,
                           None, None, validators, widget, messages)

    def convert(self, value):
        tag = _tag_punct_re.sub(u'-', value.strip().lower())
        return TextField.convert(self, tag)


class ChoiceField(Field):
    """A field that lets a user select one out of many choices.

    A choice field accepts some choices that are valid values for it.
    Values are compared after converting to unicode which means that
    ``1 == "1"``:

    >>> field = ChoiceField(choices=[1, 2, 3])
    >>> field('1')
    1
    >>> field('42')
    Traceback (most recent call last):
      ...
    ValidationError: Please enter a valid choice.

    Two values `a` and `b` are considered equal if either ``a == b`` or
    ``primitive(a) == primitive(b)`` where `primitive` is the primitive
    of the value.  Primitives are created with the following algorithm:

        1.  if the object is `None` the primitive is the empty string
        2.  otherwise the primitive is the string value of the object

    A choice field also accepts lists of tuples as argument where the
    first item is used for comparing and the second for displaying
    (which is used by the `SelectBoxWidget`):

    >>> field = ChoiceField(choices=[(0, 'inactive'), (1, 'active')])
    >>> field('0')
    0

    Because all fields are bound to the form before validation it's
    possible to assign the choices later:

    >>> class MyForm(Form):
    ...     status = ChoiceField()
    ...
    >>> form = MyForm()
    >>> form.status.choices = [(0, 'inactive', 1, 'active')]
    >>> form.validate({'status': '0'})
    True
    >>> form.data
    {'status': 0}

    If a choice field is set to "not required" and a `SelectBox` is used
    as widget you have to provide an empty choice or the field cannot be
    left blank.

    >>> field = ChoiceField(required=False, choices=[('', _('Nothing')),
    ...                                              ('1', _('Something'))])
    """

    widget = SelectBox
    messages = dict(
        invalid_choice=lazy_gettext('Please enter a valid choice.')
    )

    def __init__(self, label=None, help_text=None, required=True,
                 choices=None, validators=None, widget=None, messages=None):
        Field.__init__(self, label, help_text, validators, widget, messages)
        self.required = required
        self.choices = choices

    def convert(self, value):
        if not value and not self.required:
            return
        if self.choices:
            for choice in self.choices:
                if isinstance(choice, tuple):
                    choice = choice[0]
                if _value_matches_choice(value, choice):
                    return choice
        raise ValidationError(self.messages['invalid_choice'])

    def _bind(self, form, memo):
        rv = Field._bind(self, form, memo)
        if self.choices is not None:
            rv.choices = list(self.choices)
        return rv


class MultiChoiceField(ChoiceField):
    """A field that lets a user select multiple choices."""

    multiple_choices = True
    messages = dict(too_small=None, too_big=None)
    validate_on_omission = True

    def __init__(self, label=None, help_text=None, choices=None,
                 min_size=None, max_size=None, validators=None,
                 widget=None, messages=None):
        ChoiceField.__init__(self, label, help_text, min_size > 0, choices,
                             validators, widget, messages)
        self.min_size = min_size
        self.max_size = max_size

    def convert(self, value):
        result = []
        known_choices = {}
        for choice in self.choices:
            if isinstance(choice, tuple):
                choice = choice[0]
            known_choices[choice] = choice
            known_choices.setdefault(_to_string(choice), choice)

        x = _to_list(value)
        for value in _to_list(value):
            for version in value, _to_string(value):
                if version in known_choices:
                    result.append(known_choices[version])
                    break
            else:
                raise ValidationError(_(u'“%s” is not a valid choice') %
                                      value)

        if self.min_size is not None and len(result) < self.min_size:
            message = self.messages['too_small']
            if message is None:
                message = ngettext(u'Please provide at least %d item.',
                                   u'Please provide at least %d items.',
                                   self.min_size) % self.min_size
            raise ValidationError(message)
        if self.max_size is not None and len(result) > self.max_size:
            message = self.messages['too_big']
            if message is None:
                message = ngettext(u'Please provide no more than %d item.',
                                   u'Please provide no more than %d items.',
                                   self.min_size) % self.min_size
            raise ValidationError(message)

        return result

    def to_primitive(self, value):
        return map(unicode, _force_list(value))


class IntegerField(Field):
    """Field for integers.

    >>> field = IntegerField(min_value=0, max_value=99)
    >>> field('13')
    13

    >>> field('thirteen')
    Traceback (most recent call last):
      ...
    ValidationError: Please enter a whole number.

    >>> field('193')
    Traceback (most recent call last):
      ...
    ValidationError: Ensure this value is less than or equal to 99.
    """

    messages = dict(
        too_small=None,
        too_big=None,
        no_integer=lazy_gettext('Please enter a whole number.')
    )

    def __init__(self, label=None, help_text=None, required=False,
                 min_value=None, max_value=None, validators=None,
                 widget=None, messages=None):
        Field.__init__(self, label, help_text, validators, widget, messages)
        self.required = required
        self.min_value = min_value
        self.max_value = max_value

    def convert(self, value):
        value = _to_string(value)
        if not value:
            if self.required:
                raise ValidationError(self.messages['required'])
            return None
        try:
            value = int(value)
        except ValueError:
            raise ValidationError(self.messages['no_integer'])

        if self.min_value is not None and value < self.min_value:
            message = self.messages['too_small']
            if message is None:
                message = _(u'Ensure this value is greater than or '
                            u'equal to %s.') % self.min_value
            raise ValidationError(message)
        if self.max_value is not None and value > self.max_value:
            message = self.messages['too_big']
            if message is None:
                message = _(u'Ensure this value is less than or '
                            u'equal to %s.') % self.max_value
            raise ValidationError(message)

        return int(value)


class BooleanField(Field):
    """Field for boolean values.

    >>> field = BooleanField()
    >>> field('1')
    True

    >>> field = BooleanField()
    >>> field('')
    False
    """

    widget = Checkbox
    validate_on_omission = True
    choices = [
        (u'True', lazy_gettext(u'True')),
        (u'False', lazy_gettext(u'False'))
    ]

    def convert(self, value):
        return value != u'False' and bool(value)

    def to_primitive(self, value):
        if self.convert(value):
            return u'True'
        return u'False'


class FormMeta(type):
    """Meta class for forms.  Handles form inheritance and registers
    validator functions.
    """

    def __new__(cls, name, bases, d):
        fields = {}
        validator_functions = {}
        root_validator_functions = []

        for base in reversed(bases):
            if hasattr(base, '_root_field'):
                # base._root_field is always a FormMapping field
                fields.update(base._root_field.fields)
                root_validator_functions.extend(base._root_field.validators)

        for key, value in d.iteritems():
            if key.startswith('validate_') and callable(value):
                validator_functions[key[9:]] = value
            elif isinstance(value, Field):
                fields[key] = value
                d[key] = FieldDescriptor(key)

        for field_name, func in validator_functions.iteritems():
            if field_name in fields:
                fields[field_name].validators.append(func)

        d['_root_field'] = root = FormMapping(**fields)
        context_validate = d.get('context_validate')
        root.validators.extend(root_validator_functions)
        if context_validate is not None:
            root.validators.append(context_validate)

        return type.__new__(cls, name, bases, d)

    def as_field(cls):
        """Returns a field object for this form.  The field object returned
        is independent of the form and can be modified in the same manner as
        a bound field.
        """
        field = object.__new__(FormAsField)
        field.__dict__.update(cls._root_field.__dict__)
        field.form_class = cls
        field.validators = cls._root_field.validators[:]
        field.fields = cls._root_field.fields.copy()
        return field

    @property
    def validators(cls):
        return cls._root_field.validators

    @property
    def fields(cls):
        return cls._root_field.fields


class FieldDescriptor(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        try:
            return (obj or type).fields[self.name]
        except KeyError:
            raise AttributeError(self.name)

    def __set__(self, obj, value):
        obj.fields[self.name] = value

    def __delete__(self, obj):
        if self.name not in obj.fields:
            raise AttributeError('%r has no attribute %r' %
                                 (type(obj).__name__, self.name))
        del obj.fields[self.name]


class Form(object):
    """Form base class.

    >>> class PersonForm(Form):
    ...     name = TextField(required=True)
    ...     age = IntegerField()

    >>> form = PersonForm()
    >>> form.validate({'name': 'johnny', 'age': '42'})
    True
    >>> form.data['name']
    u'johnny'
    >>> form.data['age']
    42

    Let's cause a simple validation error:

    >>> form = PersonForm()
    >>> form.validate({'name': '', 'age': 'fourty-two'})
    False
    >>> print form.errors['age'][0]
    Please enter a whole number.
    >>> print form.errors['name'][0]
    This field is required.

    You can also add custom validation routines for fields by adding methods
    that start with the prefix ``validate_`` and the field name that take the
    value as argument. For example:

    >>> class PersonForm(Form):
    ...     name = TextField(required=True)
    ...     age = IntegerField()
    ...
    ...     def validate_name(self, value):
    ...         if not value.isalpha():
    ...             raise ValidationError(u'The value must only contain letters')

    >>> form = PersonForm()
    >>> form.validate({'name': 'mr.t', 'age': '42'})
    False
    >>> form.errors
    {'name': [u'The value must only contain letters']}

    You can also validate multiple fields in the context of other fields.
    That validation is performed after all other validations.  Just add a
    method called ``context_validate`` that is passed the dict of all fields::

    >>> class RegisterForm(Form):
    ...     username = TextField(required=True)
    ...     password = TextField(required=True)
    ...     password_again = TextField(required=True)
    ...
    ...     def context_validate(self, data):
    ...         if data['password'] != data['password_again']:
    ...             raise ValidationError(u'The two passwords must be the same')

    >>> form = RegisterForm()
    >>> form.validate({'username': 'admin', 'password': 'blah',
    ...                'password_again': 'blag'})
    ...
    False
    >>> form.errors
    {None: [u'The two passwords must be the same']}

    Forms can be used as fields for other forms.  To create a form field of
    a form you can call the `as_field` class method::

    >>> field = RegisterForm.as_field()

    This field can be used like any other field class.  What's important about
    forms as fields is that validators don't get an instance of `RegisterForm`
    passed as `form` / `self` but the form where it's used in if the field is
    used from a form.

    Form fields are bound to the form on form instanciation.  This makes it
    possible to modify a particular instance of the form.  For example you
    can create an instance of it and drop some fiels by using
    ``del form.fields['name']`` or reassign choices of choice fields.  It's
    however not easily possible to add new fields to an instance because newly
    added fields wouldn't be bound.  The fields that are stored directly on
    the form can also be accessed with their name like a regular attribute.

    Example usage:

    >>> class StatusForm(Form):
    ...     status = ChoiceField()
    ...
    >>> StatusForm.status.bound
    False
    >>> form = StatusForm()
    >>> form.status.bound
    True
    >>> form.status.choices = [u'happy', u'unhappy']
    >>> form.validate({'status': u'happy'})
    True
    >>> form['status']
    u'happy'

    Forms can be recaptcha protected by setting `catcha_protected` to `True`.
    If catpcha protection is enabled the catcha has to be rendered from the
    widget created, like a field.

    Forms are CSRF protected if they are created in the context of an active
    request or if an request is passed to the constructor.  In order for the
    CSRF protection to work it will modify the session on the request.

    The consequence of that is that the application must not ignore session
    changes.
    """
    __metaclass__ = FormMeta

    csrf_protected = None
    redirect_tracking = True
    captcha_protected = False
    default_method = 'POST'

    def __init__(self, initial=None, action=None, request=None):
        if request is None:
            request = Request.current
        self.request = request
        if initial is None:
            initial = {}
        self.initial = initial
        self.action = action
        self.invalid_redirect_targets = set()

        if self.request is not None:
            if self.csrf_protected is None:
                self.csrf_protected = True
            if self.action in (None, '', '.'):
                self.action = request.url
            else:
                self.action = urljoin(request.url, self.action)
        elif self.csrf_protected is None:
            self.csrf_protected = False

        self._root_field = _bind(self.__class__._root_field, self, {})
        self.reset()

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def as_widget(self):
        """Return the form as widget."""
        # if there is submitted data, use that for the widget
        if self.raw_data is not None:
            data = self.raw_data
        # otherwise go with the data from the source (eg: database)
        else:
            data = self.data
        return _make_widget(self._root_field, None, data, self.errors)

    def add_invalid_redirect_target(self, *args, **kwargs):
        """Add an invalid target. Invalid targets are URLs we don't want to
        visit again. For example if a post is deleted from the post edit page
        it's a bad idea to redirect back to the edit page because in that
        situation the edit page would return a page not found.

        This function accepts the same parameters as `url_for`.
        """
        self.invalid_redirect_targets.add(url_for(*args, **kwargs))

    @property
    def redirect_target(self):
        """The back-redirect target for this form."""
        if self.request is not None:
            return self.request.get_redirect_target(
                self.invalid_redirect_targets)

    def redirect(self, *args, **kwargs):
        """Redirects to the url rule given or back to the URL where we are
        comming from if `redirect_tracking` is enabled.
        """
        target = None
        if self.redirect_tracking:
            target = self.redirect_target
        if target is None:
            return redirect(url_for(*args, **kwargs))
        return redirect(target)

    @property
    def csrf_token(self):
        """The unique CSRF security token for this form."""
        if not self.csrf_protected:
            raise AttributeError('no csrf token because form not '
                                 'csrf protected')
        return get_csrf_token(self.request, self.action)

    @property
    def is_valid(self):
        """True if the form is valid."""
        return not self.errors

    @property
    def has_changed(self):
        """True if the form has changed."""
        return self._root_field.to_primitive(self.initial) != \
               self._root_field.to_primitive(self.data)

    @property
    def fields(self):
        return self._root_field.fields

    @property
    def validators(self):
        return self._root_field.validators

    def reset(self):
        """Resets the form."""
        self.data = self.initial.copy()
        self.errors = {}
        self.raw_data = None

    def add_error(self, error, field=None):
        """Adds an error to a field."""
        seq = self.errors.get(field)
        if seq is None:
            seq = self.errors[field] = ErrorList()
        seq.append(error)

    def autodiscover_data(self):
        """Called by `validate` if no data is provided.  Finds the
        matching data from the request object by default depending
        on the default submit method of the form.
        """
        if self.request is None:
            raise RuntimeError('cannot validate implicitly without '
                               'form being bound to request')
        if self.default_method == 'GET':
            return self.request.args
        elif self.default_method == 'POST':
            return self.request.form
        raise RuntimeError('for unknown methods you have to '
                           'explicitly provide a data dict')

    def validate(self, data=None):
        """Validate the form against the data passed.  If no data is provided
        the form data of the current request is taken.
        """
        if data is None:
            data = self.autodiscover_data()
        self.raw_data = _decode(data)

        # for each field in the root that requires validation on value
        # omission we add `None` into the raw data dict.  Because the
        # implicit switch between initial data and user submitted data
        # only happens on the "root level" for obvious reasons we only
        # have to hook the data in here.
        for name, field in self._root_field.fields.iteritems():
            if field.validate_on_omission and name not in self.raw_data:
                self.raw_data.setdefault(name)

        d = self.data.copy()
        d.update(self.raw_data)
        errors = {}
        try:
            data = self._root_field(d)
        except ValidationError, e:
            errors = e.unpack()
        self.errors = errors

        # every time we validate, we invalidate the csrf token if there
        # was one.
        if self.csrf_protected:
            invalidate_csrf_token(self.request, self.action)

        if errors:
            return False

        self.data.update(data)
        return True


# circular dependencies
from solace.application import Request, url_for

########NEW FILE########
__FILENAME__ = ini
# -*- coding: utf-8 -*-
"""
    solace.utils.ini
    ~~~~~~~~~~~~~~~~

    Parses an ini file into a dict.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re


_coding_re = re.compile('coding(?:\s*[:=]\s*|\s+)(\S+)')

COOKIE_LIMIT = 2
DEFAULT_ENCODING = 'utf-8'


def parse_ini(filename_or_fileobj):
    """Parses a config file in ini format into a dict."""
    if isinstance(filename_or_fileobj, basestring):
        f = open(filename_or_fileobj)
        close_later = True
    else:
        f = filename_or_fileobj
        close_later = False

    try:
        result = {}
        encoding = None
        section = ''

        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if line[0] in '#;':
                if encoding is None and idx < COOKIE_LIMIT:
                    match = _coding_re.match(line)
                    if match is not None:
                        encoding = match.group()
                continue
            if line[0] == '[' and line[-1] == ']':
                section = line[1:-1]
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.rstrip()

                # if we haven't seen an encoding cookie so far, we
                # use the default encoding
                if encoding is None:
                    encoding = DEFAULT_ENCODING
                value = value.lstrip().decode(encoding, 'replace')
            else:
                key = line
                value = u''
            if section:
                key = '%s.%s' % (section, key)
            result[key] = value
    finally:
        if close_later:
            f.close()

    return result

########NEW FILE########
__FILENAME__ = lazystring
# -*- coding: utf-8 -*-
"""
    solace.utils.lazystring
    ~~~~~~~~~~~~~~~~~~~~~~~

    Implements a lazy string used by the i18n system.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""


def is_lazy_string(obj):
    """Checks if the given object is a lazy string."""
    return isinstance(obj, _LazyString)


def make_lazy_string(func, *args):
    """Creates a lazy string by invoking func with args."""
    return _LazyString(func, args)


class _LazyString(object):
    """Class for strings created by a function call.

    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting.
    """
    __slots__ = ('_func', '_args')

    def __init__(self, func, args):
        self._func = func
        self._args = args

    value = property(lambda x: x._func(*x._args))

    def __contains__(self, key):
        return key in self.value

    def __nonzero__(self):
        return bool(self.value)

    def __dir__(self):
        return dir(unicode)

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

    def __getattr__(self, name):
        if name == '__members__':
            return self.__dir__()
        return getattr(self.value, name)

    def __getstate__(self):
        return self._func, self._args

    def __setstate__(self, tup):
        self._func, self._args = tup

    def __getitem__(self, key):
        return self.value[key]

    def __copy__(self):
        return self

    def __repr__(self):
        try:
            return 'l' + repr(unicode(self.value))
        except:
            return '<%s broken>' % self.__class__.__name__

########NEW FILE########
__FILENAME__ = mail
# -*- coding: utf-8 -*-
"""
    solace.utils.mail
    ~~~~~~~~~~~~~~~~~

    This module can be used to send mails.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
                (c) 2009 by the Zine Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
import re
try:
    from email.mime.text import MIMEText
except ImportError:
    from email.MIMEText import MIMEText
from smtplib import SMTP, SMTPException
from urlparse import urlparse

from solace import settings


def send_email(subject, text, to_addrs, quiet=True):
    """Send a mail using the `EMail` class.  This will log the email instead
    if the application configuration wants to log email.
    """
    e = EMail(subject, text, to_addrs)
    if settings.MAIL_LOG_FILE is not None:
        return e.log(settings.MAIL_LOG_FILE)
    if quiet:
        return e.send_quiet()
    return e.send()


class EMail(object):
    """Represents one E-Mail message that can be sent."""

    def __init__(self, subject=None, text='', to_addrs=None):
        self.subject = u' '.join(subject.splitlines())
        self.text = text
        self.from_addr = u'%s <%s>' % (
            settings.MAIL_FROM_NAME or settings.WEBSITE_TITLE,
            settings.MAIL_FROM
        )
        self.to_addrs = []
        if isinstance(to_addrs, basestring):
            self.add_addr(to_addrs)
        else:
            for addr in to_addrs:
                self.add_addr(addr)

    def add_addr(self, addr):
        """Add an mail address to the list of recipients"""
        lines = addr.splitlines()
        if len(lines) != 1:
            raise ValueError('invalid value for email address')
        self.to_addrs.append(lines[0])

    def as_message(self):
        """Return the email as MIMEText object."""
        if not self.subject or not self.text or not self.to_addrs:
            raise RuntimeError("Not all mailing parameters filled in")

        from_addr = self.from_addr.encode('utf-8')
        to_addrs = [x.encode('utf-8') for x in self.to_addrs]

        msg = MIMEText(self.text.encode('utf-8'))

        #: MIMEText sucks, it does not override the values on
        #: setitem, it appends them.  We get rid of some that
        #: are predefined under some versions of python
        del msg['Content-Transfer-Encoding']
        del msg['Content-Type']

        msg['From'] = from_addr.encode('utf-8')
        msg['To'] = ', '.join(x.encode('utf-8') for x in self.to_addrs)
        msg['Subject'] = self.subject.encode('utf-8')
        msg['Content-Transfer-Encoding'] = '8bit'
        msg['Content-Type'] = 'text/plain; charset=utf-8'
        return msg

    def format(self, sep='\r\n'):
        """Format the message into a string."""
        return sep.join(self.as_message().as_string().splitlines())

    def log(self, fp_or_filename):
        """Logs the email"""
        if isinstance(fp_or_filename, basestring):
            f = open(fp_or_filename, 'a')
            close_later = True
        else:
            f = fp_or_filename
            close_later = False
        try:
            f.write('%s\n%s\n\n' % ('-' * 79, self.format('\n').rstrip()))
            f.flush()
        finally:
            if close_later:
                f.close()

    def send(self):
        """Send the message."""
        try:
            smtp = SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        except SMTPException, e:
            raise RuntimeError(str(e))

        if settings.SMTP_USE_TLS:
            smtp.ehlo()
            if not smtp.esmtp_features.has_key('starttls'):
                raise RuntimeError('TLS enabled but server does not '
                                   'support TLS')
            smtp.starttls()
            smtp.ehlo()

        if settings.SMTP_USER:
            try:
                smtp.login(settings.SMTP_USER,
                           settings.SMTP_PASSWORD)
            except SMTPException, e:
                raise RuntimeError(str(e))

        msgtext = self.format()
        try:
            try:
                return smtp.sendmail(self.from_addr, self.to_addrs, msgtext)
            except SMTPException, e:
                raise RuntimeError(str(e))
        finally:
            if settings.SMTP_USE_TLS:
                # avoid false failure detection when the server closes
                # the SMTP connection with TLS enabled
                import socket
                try:
                    smtp.quit()
                except socket.sslerror:
                    pass
            else:
                smtp.quit()

    def send_quiet(self):
        """Send the message, swallowing exceptions."""
        try:
            return self.send()
        except Exception:
            return

########NEW FILE########
__FILENAME__ = packs
# -*- coding: utf-8 -*-
"""
    solace.utils.packs
    ~~~~~~~~~~~~~~~~~~

    Implements the system for static file packs.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
import re
from weakref import ref as weakref
from operator import itemgetter

from jinja2 import Markup


CSS_TEMPLATE = '<link rel="stylesheet" type="text/css" href="%s">'
JS_TEMPLATE = '<script type="text/javascript" src="%s"></script>'
DEFAULT_COMPRESSORS = ('yui', 'naive')

operators = [
    '+', '-', '*', '%', '!=', '==', '<', '>', '<=', '>=', '=',
    '+=', '-=', '*=', '%=', '<<', '>>', '>>>', '<<=', '>>=', '?',
    '>>>=', '&', '&=', '|', '|=', '&&', '||', '^', '^=', '(', ')',
    '[', ']', '{', '}', '!', '--', '++', '~', ',', ';', '.', ':'
]
operators.sort(key=lambda x: -len(x))

rules = [
    ('whitespace', re.compile(r'\s+(?ums)')),
    ('dummycomment', re.compile(r'<!--.*')),
    ('linecomment', re.compile(r'//.*')),
    ('multilinecomment', re.compile(r'/\*.*?\*/(?us)')),
    ('name', re.compile(r'([\w$_][\w\d_$]*)(?u)')),
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
ignored_tokens = frozenset(('dummycomment', 'linecomment', 'multilinecomment'))

css_ws_re = re.compile(r'\s+(?u)')
css_preserve_re = re.compile(r'((?:"(?:\\\\|\\"|[^"])*")|'
                             r"(?:'(?:\\\\|\\'|[^'])*')|"
                             r'(?:url\(.*?\)))|(/\*.*?\*/)(?usi)')
css_useless_space_re = re.compile(r' ?([:;,{}]) ?')
css_null_value_re = re.compile(r'(:)(0)(px|em|%|in|cm|mm|pc|pt|ex)')
css_null_float_re = re.compile(r'(:|\s)0+\.(\\d+)')
css_multi_semicolon_re = re.compile(r';{2,}')


class Pack(object):
    """Represents a pack."""

    def __init__(self, mgr, name, files):
        self._mgr = weakref(mgr)
        self.name = name
        self._css = []
        self._js = []
        for filename in files:
            assert '.' in filename, 'unknown file without extension'
            ext = filename.rsplit('.', 1)[-1]
            if ext == 'js':
                self._js.append(filename)
            elif ext == 'css':
                self._css.append(filename)
            else:
                assert False, 'unknown extension ".%s"' % ext

    def get_mgr(self):
        rv = self._mgr()
        if rv is None:
            raise RuntimeError('manager got garbage collected')
        return rv

    def _compressed_filename(self, ext):
        return self.get_mgr().build_filename % {'name': self.name, 'ext': ext}

    def _make_gen_iterator(ext):
        def iter_ext(self):
            mgr = self.get_mgr()
            def _format(link):
                return getattr(mgr, ext + '_template') % mgr.link_func(link, ext)
            fn = self._compressed_filename(ext)
            if os.path.isfile(os.path.join(mgr.directory, fn)):
                yield _format(fn)
                return
            for filename in getattr(self, '_' + ext):
                yield _format(filename)
        return iter_ext

    iter_css = _make_gen_iterator('css')
    iter_js = _make_gen_iterator('js')
    del _make_gen_iterator

    def compress(self, compressor):
        mgr = self.get_mgr()
        for ext in 'css', 'js':
            files = getattr(self, '_' + ext)
            if not files:
                continue
            filename = self._compressed_filename(ext)
            dst = open(os.path.join(mgr.directory, filename), 'w')
            try:
                getattr(compressor, 'compress_' + ext)(dst, files)
            finally:
                dst.close()

    def remove_compressed(self):
        mgr = self.get_mgr()
        for ext in 'css', 'js':
            filename = os.path.join(mgr.directory, self._compressed_filename(ext))
            if os.path.isfile(filename):
                os.remove(filename)

    def __iter__(self):
        mgr = self.get_mgr()
        iters = self.iter_css, self.iter_js
        if not mgr.css_first:
            iters = reversed(iters)
        for func in iters:
            for item in func():
                yield item

    def __unicode__(self):
        return u'\n'.join(self)

    def __str__(self):
        return '\n'.join(x.encode('utf-8') for x in self)

    def __html__(self):
        return Markup(unicode(self))


def default_link_func(fn, ext):
    from solace.application import url_for
    return url_for('static', file=fn)


class PackManager(object):

    compressor_class = None

    def __init__(self, directory, link_func=None, css_first=True,
                 css_template=CSS_TEMPLATE, js_template=JS_TEMPLATE,
                 build_filename='%(name)s.compressed.%(ext)s',
                 charset='utf-8'):
        self.directory = directory
        if link_func is None:
            link_func = default_link_func
        self.link_func = link_func
        self.css_first = css_first
        self.css_template = CSS_TEMPLATE
        self.js_template = JS_TEMPLATE
        self.build_filename = build_filename
        self.charset = charset
        self._packs = {}

    def compress(self, log=None):
        compressor = self.compressor_class(self, log)
        for pack in self._packs.itervalues():
            pack.compress(compressor)

    def remove_compressed(self):
        for pack in self._packs.itervalues():
            pack.remove_compressed()

    def add_pack(self, name, files):
        self._packs[name] = Pack(self, name, files)

    def remove_pack(self, name):
        rv = self._packs.pop(name, None)
        if rv is None:
            raise ValueError('no pack named %r found' % name)

    def __getitem__(self, name):
        return self._packs[name]


class CompressorBase(object):

    def __init__(self, mgr, log):
        self.mgr = mgr
        self.log = log

    def compress_css(self, stream, files):
        pass

    def compress_js(self, stream, files):
        pass


class Token(tuple):
    """Represents a token as returned by `js_tokenize`."""
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


def contains_newline(string):
    """Checks if a newline sign is in the string."""
    return '\n' in string or '\r' in string


def js_tokenize(source):
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
            if token_type not in ('whitespace', 'dummycomment',
                                  'multilinecomment', 'linecomment'):
                may_divide = indicates_division(token)
            yield token
        lineno += len(line_re.findall(token_value))
        pos = match.end()


def remove_css_junk(code):
    """Remove useless stuff from CSS source."""
    pieces = []
    end = len(code)
    pos = 0

    # find all the stuff we have to preserve.
    while pos < end:
        match = css_preserve_re.search(code, pos)
        if match is None:
            pieces.append((False, code[pos:]))
            break
        pieces.append((False, code[pos:match.start()]))
        token, comment = match.groups()
        if token is not None:
            pieces.append((True, token))
        pos = match.end()

    for idx, (preserved, value) in enumerate(pieces):
        if preserved:
            continue

        # normalize whitespace
        value = css_ws_re.sub(u' ', value)
        # remove spaces before things that do not need them
        value = css_useless_space_re.sub(r'\1', value)
        # get rid of useless semicolons
        value = value.replace(u';}', u'}').replace(u'; }', u'}')
        # normalize 0UNIT to 0
        value = css_null_value_re.sub(r'\1\2', value)
        # normalize (0 0 0 0), (0 0 0) and (0 0) to 0
        value = value.replace(u':0 0 0 0;', u':0;') \
                     .replace(u':0 0 0;', u':0;') \
                     .replace(u':0 0;', u':0;') \
                     .replace(u'background-position:0;',
                              u'background-position:0 0;')
        # shorten 0.x to .x
        value = css_null_float_re.sub(r'\1.\2', value)
        pieces[idx] = (False, value)
        # remove multiple semicolons
        value = css_multi_semicolon_re.sub(r';', value)

        pieces[idx] = (False, value)

    return u''.join(x[1] for x in pieces).strip() + '\n'


class NaiveCompressor(CompressorBase):
    """Basic compressor that just strips whitespace and comments."""

    def compress_js(self, stream, files):
        for filename in files:
            src = open(os.path.join(self.mgr.directory, filename), 'r')
            try:
                tokeniter = js_tokenize(src.read().decode(self.mgr.charset))
            finally:
                src.close()
            last_token = None
            safe_to_join = False
            was_newline = False
            for token in tokeniter:
                if token.type == 'whitespace':
                    if last_token and contains_newline(token.value) and not safe_to_join:
                        stream.write('\n')
                        last_token = token
                        safe_to_join = True
                        was_newline = True
                elif token.type not in ignored_tokens:
                    if token.type == 'name' and \
                       last_token and last_token.type == 'name':
                        stream.write(' ')
                    stream.write(token.value.encode(self.mgr.charset))
                    last_token = token
                    safe_to_join = token.type == 'operator' and \
                                   token.value in (';', '{', '[', '(', ',')
                    was_newline = False
            if not was_newline:
                stream.write('\n')

    def compress_css(self, stream, files):
        for filename in files:
            src = open(os.path.join(self.mgr.directory, filename), 'r')
            try:
                cleaned = remove_css_junk(src.read().decode(self.mgr.charset))
                stream.write(cleaned.encode('utf-8'))
            finally:
                src.close()


PackManager.compressor_class = NaiveCompressor

########NEW FILE########
__FILENAME__ = pagination
# -*- coding: utf-8 -*-
"""
    solace.utils.pagination
    ~~~~~~~~~~~~~~~~~~~~~~~

    Implements a pagination helper.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import math
from werkzeug import url_encode
from werkzeug.exceptions import NotFound
from jinja2 import Markup
from solace.i18n import _


class Pagination(object):
    """Pagination helper."""

    threshold = 3
    left_threshold = 3
    right_threshold = 1
    normal = u'<a href="%(url)s">%(page)d</a>'
    active = u'<strong>%(page)d</strong>'
    commata = u'<span class="commata">,\n</span>'
    ellipsis = u'<span class="ellipsis"> …\n</span>'

    def __init__(self, request, query, page=None, per_page=15, link_func=None):
        if page is None:
            page = 1
        self.request = request
        self.query = query
        self.page = page
        self.per_page = per_page
        self.total = query.count()
        self.pages = int(math.ceil(self.total / float(self.per_page)))
        self.necessary = self.pages > 1

        if link_func is None:
            link_func = lambda x: '?page=%d' % page
            url_args = self.request.args.copy()
            def link_func(page):
                url_args['page'] = page
                return u'?' + url_encode(url_args)
        self.link_func = link_func

    def __unicode__(self):
        if not self.necessary:
            return u''
        return u'<div class="pagination">%s</div>' % self.generate()

    def __html__(self):
        return Markup(unicode(self))

    def get_objects(self, raise_not_found=True):
        """Returns the objects for the page."""
        if raise_not_found and self.page < 1:
            raise NotFound()
        rv = self.query.offset(self.offset).limit(self.per_page).all()
        if raise_not_found and self.page > 1 and not rv:
            raise NotFound()
        return rv

    @property
    def offset(self):
        return (self.page - 1) * self.per_page

    def generate(self):
        """This method generates the pagination."""
        was_ellipsis = False
        result = []
        next = None

        for num in xrange(1, self.pages + 1):
            if num == self.page:
                was_ellipsis = False
            if num - 1 == self.page:
                next = num
            if num <= self.left_threshold or \
               num > self.pages - self.right_threshold or \
               abs(self.page - num) < self.threshold:
                if result and not was_ellipsis:
                    result.append(self.commata)
                link = self.link_func(num)
                template = num == self.page and self.active or self.normal
                result.append(template % {
                    'url':      link,
                    'page':     num
                })
            elif not was_ellipsis:
                was_ellipsis = True
                result.append(self.ellipsis)

        if next is not None:
            result.append(u'<span class="sep"> </span>'
                          u'<a href="%s" class="next">%s</a>' %
                          (self.link_func(next), _(u'Next »')))

        return u''.join(result)

########NEW FILE########
__FILENAME__ = recaptcha
# -*- coding: utf-8 -*-
"""
    solace.utils.recaptcha
    ~~~~~~~~~~~~~~~~~~~~~~

    Provides basic recaptcha integration.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import urllib2
from simplejson import dumps
from werkzeug import url_encode
from jinja2 import Markup

from solace import settings
from solace.i18n import _


API_SERVER = 'http://api.recaptcha.net/'
SSL_API_SERVER = 'https://api-secure.recaptcha.net/'
VERIFY_SERVER = 'http://api-verify.recaptcha.net/verify'


def get_recaptcha_html(error=None):
    """Returns the recaptcha input HTML."""
    server = settings.RECAPTCHA_USE_SSL and API_SERVER or SSL_API_SERVER
    options = dict(k=settings.RECAPTCHA_PUBLIC_KEY)
    if error is not None:
        options['error'] = unicode(error)
    query = url_encode(options)
    return Markup(u'''
    <script type="text/javascript">var RecaptchaOptions = %(options)s;</script>
    <script type="text/javascript" src="%(script_url)s"></script>
    <noscript>
      <div><iframe src="%(frame_url)s" height="300" width="500"></iframe></div>
      <div><textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
      <input type="hidden" name="recaptcha_response_field" value="manual_challenge"></div>
    </noscript>
    ''') % dict(
        script_url='%schallenge?%s' % (server, query),
        frame_url='%snoscript?%s' % (server, query),
        options=dumps({
            'theme':    'clean',
            'custom_translations': {
                'visual_challenge': _("Get a visual challenge"),
                'audio_challenge': _("Get an audio challenge"),
                'refresh_btn': _("Get a new challenge"),
                'instructions_visual': _("Type the two words:"),
                'instructions_audio': _("Type what you hear:"),
                'help_btn': _("Help"),
                'play_again': _("Play sound again"),
                'cant_hear_this': _("Download sound as MP3"),
                'incorrect_try_again': _("Incorrect. Try again.")
            }
        })
    )


def validate_recaptcha(challenge, response, remote_ip):
    """Validates the recaptcha.  If the validation fails a `RecaptchaValidationFailed`
    error is raised.
    """
    request = urllib2.Request(VERIFY_SERVER, data=url_encode({
        'privatekey':       settings.RECAPTCHA_PRIVATE_KEY,
        'remoteip':         remote_ip,
        'challenge':        challenge,
        'response':         response
    }))
    response = urllib2.urlopen(request)
    rv = response.read().splitlines()
    response.close()
    if rv and rv[0] == 'true':
        return True
    if len(rv) > 1:
        error = rv[1]
        if error == 'invalid-site-public-key':
            raise RuntimeError('invalid public key for recaptcha set')
        if error == 'invalid-site-private-key':
            raise RuntimeError('invalid private key for recaptcha set')
        if error == 'invalid-referrer':
            raise RuntimeError('key not valid for the current domain')
    return False

########NEW FILE########
__FILENAME__ = remoting
# -*- coding: utf-8 -*-
"""
    solace.utils.remoting
    ~~~~~~~~~~~~~~~~~~~~~

    This module implements a baseclass for remote objects.  These
    objects can be exposed via JSON on the URL and are also used
    by libsolace's direct connection.

    It also provides basic helpers for the API.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from datetime import datetime
from babel import Locale
from solace.utils.lazystring import is_lazy_string


def remote_export_primitive(obj):
    """Remote exports a primitive."""
    if isinstance(obj, RemoteObject):
        return obj.remote_export()
    if is_lazy_string(obj):
        return unicode(obj)
    if isinstance(obj, datetime):
        return {'#type': 'solace.datetime',
                'value': obj.strftime('%Y-%m-%dT%H:%M:%SZ')}
    if isinstance(obj, Locale):
        return unicode(str(obj))
    if isinstance(obj, dict):
        return dict((key, remote_export_primitive(value))
                    for key, value in obj.iteritems())
    if hasattr(obj, '__iter__'):
        return map(remote_export_primitive, obj)
    return obj


def _recursive_getattr(obj, key):
    for attr in key.split('.'):
        obj = getattr(obj, attr, None)
    return obj


class RemoteObject(object):
    """Baseclass for remote objects."""

    #: the type of the object
    remote_object_type = None

    #: subclasses have to provide this as a list
    public_fields = None

    def remote_export(self):
        """Exports the object into a data structure ready to be
        serialized.  This is always a dict with string keys and
        the values are safe for pickeling.
        """
        result = {'#type': self.remote_object_type}
        for key in self.public_fields:
            if isinstance(key, tuple):
                alias, key = key
            else:
                alias = key.rsplit('.', 1)[-1]
            value = _recursive_getattr(self, key)
            if callable(value):
                value = value()
            result[alias] = remote_export_primitive(value)
        return result

    def remote_export_field(self, name):
        """Remote-exports a field only."""
        from solace.i18n import is_lazy_string
        value = getattr(self, name, None)
        if value is not None:
            value = remote_export_primitive(value)
        return value

########NEW FILE########
__FILENAME__ = support
# -*- coding: utf-8 -*-
"""
    solace.support
    ~~~~~~~~~~~~~~

    A support module.  Provides various support methods and helpers.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import re
import unicodedata
from itertools import izip, imap

# imported for the side effects, registers a codec
import translitcodec


_punctuation_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
_missing = object()


def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punctuation_re.split(text.lower()):
        word = _punctuation_re.sub(u'', word.encode('translit/long'))
        if word:
            result.append(word)
    return unicode(delim.join(result))


class UIException(Exception):
    """Exceptions that are displayed in the user interface.  The big
    difference to a regular exception is that this exception uses
    an unicode string as message.
    """

    message = None

    def __init__(self, message):
        Exception.__init__(self, message.encode('utf-8'))
        self.message = message

    def __unicode__(self):
        return self.message

    def __str__(self):
        return self.message.encode('utf-8')

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.message)


class OrderedDict(dict):
    """Simple ordered dict implementation.

    It's a dict subclass and provides some list functions.  The implementation
    of this class is inspired by the implementation of Babel but incorporates
    some ideas from the `ordereddict`_ and Django's ordered dict.

    The constructor and `update()` both accept iterables of tuples as well as
    mappings:

    >>> d = OrderedDict([('a', 'b'), ('c', 'd')])
    >>> d.update({'foo': 'bar'})
    >>> d
    OrderedDict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])

    Keep in mind that when updating from dict-literals the order is not
    preserved as these dicts are unsorted!

    You can copy an OrderedDict like a dict by using the constructor, `copy.copy`
    or the `copy` method and make deep copies with `copy.deepcopy`:

    >>> from copy import copy, deepcopy
    >>> copy(d)
    OrderedDict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> d.copy()
    OrderedDict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> OrderedDict(d)
    OrderedDict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> d['spam'] = []
    >>> d2 = deepcopy(d)
    >>> d2['spam'].append('eggs')
    >>> d
    OrderedDict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])])
    >>> d2
    OrderedDict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', ['eggs'])])

    All iteration methods as well as `keys`, `values` and `items` return
    the values ordered by the the time the key-value pair is inserted:

    >>> d.keys()
    ['a', 'c', 'foo', 'spam']
    >>> d.values()
    ['b', 'd', 'bar', []]
    >>> d.items()
    [('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])]
    >>> list(d.iterkeys())
    ['a', 'c', 'foo', 'spam']
    >>> list(d.itervalues())
    ['b', 'd', 'bar', []]
    >>> list(d.iteritems())
    [('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])]

    Index based lookup is supported too by `byindex` which returns the
    key/value pair for an index:

    >>> d.byindex(2)
    ('foo', 'bar')

    You can reverse the OrderedDict as well:

    >>> d.reverse()
    >>> d
    OrderedDict([('spam', []), ('foo', 'bar'), ('c', 'd'), ('a', 'b')])

    And sort it like a list:

    >>> d.sort(key=lambda x: x[0].lower())
    >>> d
    OrderedDict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])])

    For performance reasons the ordering is not taken into account when
    comparing two ordered dicts.

    .. _ordereddict: http://www.xs4all.nl/~anthon/Python/ordereddict/
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self._keys = []
        self.update(*args, **kwargs)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        if key not in self:
            self._keys.append(key)
        dict.__setitem__(self, key, item)

    def __deepcopy__(self, memo):
        d = memo.get(id(self), _missing)
        memo[id(self)] = d = self.__class__()
        dict.__init__(d, deepcopy(self.items(), memo))
        d._keys = self._keys[:]
        return d

    def __reduce__(self):
        return type(self), self.items()

    def __reversed__(self):
        return reversed(self._keys)

    @classmethod
    def fromkeys(cls, iterable, default=None):
        return cls((key, default) for key in iterable)

    def clear(self):
        del self._keys[:]
        dict.clear(self)

    def move(self, key, index):
        self._keys.remove(key)
        self._keys.insert(index, key)

    def copy(self):
        return self.__class__(self)

    def items(self):
        return zip(self._keys, self.values())

    def iteritems(self):
        return izip(self._keys, self.itervalues())

    def keys(self):
        return self._keys[:]

    def iterkeys(self):
        return iter(self._keys)

    def pop(self, key, default=_missing):
        if default is _missing:
            return dict.pop(self, key)
        elif key not in self:
            return default
        self._keys.remove(key)
        return dict.pop(self, key, default)

    def popitem(self, key):
        self._keys.remove(key)
        return dict.popitem(self, key)

    def setdefault(self, key, default=None):
        if key not in self:
            self._keys.append(key)
        dict.setdefault(self, key, default)

    def update(self, *args, **kwargs):
        sources = []
        if len(args) == 1:
            if hasattr(args[0], 'iteritems'):
                sources.append(args[0].iteritems())
            else:
                sources.append(iter(args[0]))
        elif args:
            raise TypeError('expected at most one positional argument')
        if kwargs:
            sources.append(kwargs.iteritems())
        for iterable in sources:
            for key, val in iterable:
                self[key] = val

    def values(self):
        return map(self.get, self._keys)

    def itervalues(self):
        return imap(self.get, self._keys)

    def index(self, item):
        return self._keys.index(item)

    def byindex(self, item):
        key = self._keys[item]
        return (key, dict.__getitem__(self, key))

    def reverse(self):
        self._keys.reverse()

    def sort(self, cmp=None, key=None, reverse=False):
        if key is not None:
            self._keys.sort(key=lambda k: key((k, self[k])))
        elif cmp is not None:
            self._keys.sort(lambda a, b: cmp((a, self[a]), (b, self[b])))
        else:
            self._keys.sort()
        if reverse:
            self._keys.reverse()

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.items())

    __copy__ = copy
    __iter__ = iterkeys


from solace.i18n import _

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
"""
    solace.views.admin
    ~~~~~~~~~~~~~~~~~~

    This module implements the views for the admin interface.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug import redirect, Response
from werkzeug.exceptions import Forbidden, NotFound

from solace.i18n import _
from solace.application import require_admin, url_for
from solace.models import User, session
from solace.forms import BanUserForm, EditUserRedirectForm, EditUserForm
from solace.settings import describe_settings
from solace.templating import render_template
from solace.utils.pagination import Pagination
from solace.utils.csrf import exchange_token_protected
from solace.utils import admin as admin_utils


@require_admin
def overview(request):
    """Currently just a redirect."""
    return redirect(url_for('admin.status'))


@require_admin
def status(request):
    """Displays system statistics such as the database settings."""
    return render_template('admin/status.html',
                           active_settings=describe_settings())


@require_admin
def bans(request):
    """Manages banned users"""
    form = BanUserForm()
    query = User.query.filter_by(is_banned=True)
    pagination = Pagination(request, query, request.args.get('page', type=int))

    if request.method == 'POST' and form.validate():
        admin_utils.ban_user(form.user)
        request.flash(_(u'The user “%s” was successfully banned and notified.') %
                      form.user.username)
        return form.redirect('admin.bans')

    return render_template('admin/bans.html', pagination=pagination,
                           banned_users=pagination.get_objects(),
                           form=form.as_widget())


@require_admin
def edit_users(request):
    """Edit a user."""
    pagination = Pagination(request, User.query, request.args.get('page', type=int))
    form = EditUserRedirectForm()

    if request.method == 'POST' and form.validate():
        return redirect(url_for('admin.edit_user', user=form.user.username))

    return render_template('admin/edit_users.html', pagination=pagination,
                           users=pagination.get_objects(), form=form.as_widget())


@require_admin
def edit_user(request, user):
    """Edits a user."""
    user = User.query.filter_by(username=user).first()
    if user is None:
        raise NotFound()
    form = EditUserForm(user)
    if request.method == 'POST' and form.validate():
        form.apply_changes()
        request.flash(_(u'The user details where changed.'))
        session.commit()
        return form.redirect('admin.edit_users')
    return render_template('admin/edit_user.html', form=form.as_widget(), user=user)


@exchange_token_protected
@require_admin
def unban_user(request, user):
    """Unbans a given user."""
    user = User.query.filter_by(username=user).first()
    if user is None:
        raise NotFound()
    next = request.next_url or url_for('admin.bans')
    if not user.is_banned:
        request.flash(_(u'The user is not banned.'))
        return redirect(next)
    admin_utils.unban_user(user)
    request.flash(_(u'The user “%s” was successfully unbanned and notified.') %
                  user.username)
    return redirect(next)


@exchange_token_protected
@require_admin
def ban_user(request, user):
    """Bans a given user."""
    user = User.query.filter_by(username=user).first()
    if user is None:
        raise NotFound()
    next = request.next_url or url_for('admin.bans')
    if user.is_banned:
        request.flash(_(u'The user is already banned.'))
        return redirect(next)
    if user == request.user:
        request.flash(_(u'You cannot ban yourself.'), error=True)
        return redirect(next)
    admin_utils.ban_user(user)
    request.flash(_(u'The user “%s” was successfully banned and notified.') %
                  user.username)
    return redirect(next)

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-
"""
    solace.views.api
    ~~~~~~~~~~~~~~~~

    This module implements version 1.0 of the API.  If we ever provide
    a new version, it should be renamed.

    Because the docstrings of this module are displayed on the API page
    different rules apply.  Format docstrings with creole markup, not with
    rst!

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug import redirect
from werkzeug.exceptions import NotFound

from solace.application import url_for
from solace.templating import render_template
from solace.utils.api import api_method, list_api_methods, XML_NS
from solace.models import User, Topic, Post
from solace.badges import badge_list, badges_by_id


def default_redirect(request):
    return redirect(url_for('api.help'))


def help(request):
    return render_template('api/help.html', methods=list_api_methods(),
                           xmlns=XML_NS)


@api_method()
def ping(request, value):
    """Helper function to simpliy test the API.  Answers with the
    same value.  Once API limitations are in place this method will
    continue to be "free" and as such suitable for connection checking.
    """
    return dict(value=value)


@api_method()
def list_users(request):
    """Returns a list of users.  You can retrieve up to 50 users at
    once.  Each user has the same format as a call to "get user".

    ==== Parameters ====

    * {{{limit}}} — the number of items to load at once.  Defaults to
                    10, maximum allowed number is 50.
    * {{{offset}}} — the offset of the returned list.  Defaults to 0
    """
    offset = max(0, request.args.get('offset', type=int) or 0)
    limit = max(0, min(50, request.args.get('limit', 10, type=int)))
    q = User.query.order_by(User.username)
    count = q.count()
    q = q.limit(limit).offset(offset)
    return dict(users=q.all(), total_count=count,
                limit=limit, offset=offset)


@api_method()
def get_user(request, username=None, user_id=None):
    """Looks up a user by username or user id and returns it.  If the user
    is looked up by id, a plus symbol has to be prefixed to the ID.
    """
    if username is not None:
        user = User.query.filter_by(username=username).first()
    else:
        user = User.query.get(user_id)
    if user is None:
        raise NotFound()
    return dict(user=user)


@api_method()
def list_badges(request):
    """Returns a list of all badges.  Each badge in the returned list
    has the same format as returned by the "get badge" method.
    """
    return dict(badges=badge_list)


@api_method()
def get_badge(request, identifier):
    """Returns a single badge."""
    badge = badges_by_id.get(identifier)
    if badge is None:
        raise NotFound()
    return dict(badge=badge)


@api_method()
def list_questions(request):
    """Lists all questions or all questions in a section."""
    q = Topic.query.order_by(Topic.date.desc())
    if request.view_lang is not None:
        q = q.filter_by(locale=request.view_lang)
    offset = max(0, request.args.get('offset', type=int) or 0)
    limit = max(0, min(50, request.args.get('limit', 10, type=int)))
    count = q.count()
    q = q.limit(limit).offset(offset)
    return dict(questions=q.all(), total_count=count,
                limit=limit, offset=offset)


@api_method()
def get_question(request, question_id):
    """Returns a single question and the replies."""
    t = Topic.query.get(question_id)
    if t is None:
        raise NotFound()
    return dict(question=t, replies=t.replies)


@api_method()
def get_reply(request, reply_id):
    """Returns a single reply."""
    r = Post.query.get(reply_id)
    if r is None or r.is_question:
        raise NotFound()
    return dict(reply=r)

########NEW FILE########
__FILENAME__ = badges
# -*- coding: utf-8 -*-
"""
    solace.views.badges
    ~~~~~~~~~~~~~~~~~~~

    Shows some information for the badges.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug.exceptions import NotFound

from solace.models import User, UserBadge
from solace.badges import badge_list, badges_by_id
from solace.templating import render_template


def show_list(request):
    """Shows a list of all badges."""
    return render_template('badges/show_list.html',
                           badges=sorted(badge_list,
                                         key=lambda x: (x.numeric_level,
                                                        x.name.lower())))


def show_badge(request, identifier):
    """Shows a single badge."""
    badge = badges_by_id.get(identifier)
    if badge is None:
        raise NotFound()

    user_badges = UserBadge.query.filter_by(badge=badge) \
        .order_by(UserBadge.awarded.desc()).limit(20).all()
    return render_template('badges/show_badge.html', badge=badge,
                           user_badges=user_badges)

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
"""
    solace.views.core
    ~~~~~~~~~~~~~~~~~

    This module implements the core views.  These are usually language
    independent view functions such as the overall index page.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug import redirect, Response
from werkzeug.exceptions import NotFound, MethodNotAllowed
from babel import Locale, UnknownLocaleError

from solace.application import url_for, json_response
from solace.auth import get_auth_system, LoginUnsucessful
from solace.templating import render_template
from solace.i18n import _, has_section, get_js_translations
from solace.forms import RegistrationForm, ResetPasswordForm
from solace.models import User
from solace.database import session
from solace.utils.mail import send_email
from solace.utils.csrf import get_csrf_token, exchange_token_protected, \
     get_exchange_token


def language_redirect(request):
    """Redirects to the index page of the requested language.  Thanks
    to the magic in the `url_for` function there is very few code here.
    """
    return redirect(url_for('kb.overview'))


def login(request):
    """Shows the login page."""
    next_url = request.next_url or url_for('kb.overview')
    if request.is_logged_in:
        return redirect(next_url)
    return get_auth_system().login(request)


@exchange_token_protected
def logout(request):
    """Logs the user out."""
    if request.is_logged_in:
        rv = get_auth_system().logout(request)
        if rv is not None:
            return rv
        request.flash(_(u'You were logged out.'))
    return redirect(request.next_url or url_for('kb.overview'))


def register(request):
    """Register a new user."""
    if request.is_logged_in:
        return redirect(request.next_url or url_for('kb.overview'))
    return get_auth_system().register(request)


def reset_password(request, email=None, key=None):
    """Resets the password if possible."""
    auth = get_auth_system()
    if not auth.can_reset_password:
        raise NotFound()

    form = ResetPasswordForm()
    new_password = None

    # if the user is logged in, he goes straight back to the overview
    # page.  Why would a user that is logged in (and does not anywhere
    # see a link to that page) reset the password?  Of course that does
    # not give us anything security wise because he just has to logout.
    if request.is_logged_in:
        return redirect(url_for('kb.overview'))

    # we came back from the link in the mail, try to reset the password
    if email is not None:
        for user in User.query.filter_by(email=email).all():
            if user.password_reset_key == key:
                break
        else:
            request.flash(_(u'The password-reset key expired or the link '
                            u'was invalid.'), error=True)
            return redirect(url_for('core.reset_password'))
        new_password = user.set_random_password()
        session.commit()

    # otherwise validate the form
    elif request.method == 'POST' and form.validate(request.form):
        user = form.user
        reset_url = url_for('core.reset_password', email=user.email,
                            key=user.password_reset_key, _external=True)
        send_email(_(u'Reset Password'),
                   render_template('mails/reset_password.txt', user=user,
                                   reset_url=reset_url), user.email)
        request.flash(_(u'A mail with a link to reset the password '
                        u'was sent to “%s”') % user.email)
        return redirect(url_for('kb.overview'))

    return render_template('core/reset_password.html', form=form.as_widget(),
                           new_password=new_password)


def activate_user(request, email, key):
    """Activates the user."""
    # the email is not unique on the database, we try all matching users.
    # Most likely it's only one, otherwise we activate the first matching.
    user = User.query.filter_by(email=email, activation_key=key).first()
    if user is not None:
        user.is_active = True
        session.commit()
        request.flash(_(u'Your account was activated.  You can '
                        u'log in now.'))
        return redirect(url_for('core.login'))
    request.flash(_(u'User activation failed.  The user is either already '
                    u'activated or you followed a wrong link.'), error=True)
    return redirect(url_for('kb.overview'))


def about(request):
    """Just shows a simple about page that explains the system."""
    return render_template('core/about.html')


def set_timezone_offset(request):
    """Sets the timezone offset."""
    request.session['timezone'] = request.form.get('offset', type=int)
    return 'OKAY'


def set_language(request, locale):
    """Sets the new locale."""
    try:
        locale = Locale.parse(locale)
        if not has_section(locale):
            raise UnknownLocaleError(str(locale))
    except UnknownLocaleError:
        raise NotFound()

    next_url = request.get_localized_next_url(locale)
    request.locale = locale
    request.flash(_('The interface language was set to %s.  You were also '
                    'forwarded to the help section of that language.') %
                  locale.display_name)
    return redirect(next_url or url_for('kb.overview', lang_code=locale))


def no_javascript(request):
    """Displays a page to the user that tells him to enable JavaScript.
    Some non-critical functionality requires it.
    """
    return render_template('core/no_javascript.html')


def update_csrf_token(request):
    """Updates the CSRF token.  Required for forms that are submitted multiple
    times using JavaScript.  This updates the token.
    """
    if not request.is_xhr:
        raise BadRequest()
    elif not request.method == 'POST':
        raise MethodNotAllowed(valid=['POST'])
    token = get_csrf_token(request, request.form['url'], force_update=True)
    return json_response(token=token)


def request_exchange_token(request):
    """Return the exchange token."""
    token = get_exchange_token(request)
    return json_response(token=token)


def get_translations(request, lang):
    """Returns the translations for the given language."""
    rv = get_js_translations(lang)
    if rv is None:
        raise NotFound()
    return Response(rv, mimetype='application/javascript')


def not_found(request):
    """Shows a not found page."""
    return Response(render_template('core/not_found.html'), status=404,
                    mimetype='text/html')


def bad_request(request):
    """Shows a "bad request" page."""
    return Response(render_template('core/bad_request.html'),
                    status=400, mimetype='text/html')


def forbidden(request):
    """Shows a forbidden page."""
    return Response(render_template('core/forbidden.html'),
                    status=401, mimetype='text/html')

########NEW FILE########
__FILENAME__ = kb
# -*- coding: utf-8 -*-
"""
    solace.views.kb
    ~~~~~~~~~~~~~~~

    The knowledge base views.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from sqlalchemy.orm import eagerload
from werkzeug import Response, redirect
from werkzeug.exceptions import NotFound, BadRequest, Forbidden
from werkzeug.contrib.atom import AtomFeed

from solace import settings
from solace.application import url_for, require_login, json_response
from solace.database import session
from solace.models import Topic, Post, Tag, PostRevision
from solace.utils.pagination import Pagination
from solace.templating import render_template, get_macro
from solace.i18n import _, format_datetime, list_sections
from solace.forms import QuestionForm, ReplyForm, CommentForm
from solace.utils.forms import Form as EmptyForm
from solace.utils.formatting import format_creole_diff, format_creole
from solace.utils.csrf import exchange_token_protected
from solace.utils.caching import no_cache


_topic_order = {
    'newest':       Topic.date.desc(),
    'hot':          Topic.hotness.desc(),
    'votes':        Topic.votes.desc(),
    'activity':     Topic.last_change.desc()
}


def sections(request):
    """Shows a page where all sections are listed for the user to
    select one.
    """
    if len(settings.LANGUAGE_SECTIONS) == 1:
        return redirect(url_for('kb.overview', lang_code=settings.LANGUAGE_SECTIONS[0]))
    return render_template('kb/sections.html',
                           languages=list_sections())


def _topic_list(template_name, request, query, order_by, **context):
    """Helper for views rendering a topic list."""
    # non moderators cannot see deleted posts, so we filter them out first
    # for moderators the template marks the posts up as deleted so that
    # they can be kept apart from non-deleted ones.
    if not request.user or not request.user.is_moderator:
        query = query.filter_by(is_deleted=False)
    query = query.order_by(_topic_order[order_by])

    # optimize the query for the template.  The template needs the author
    # of the topic as well (but not the editor) which is not eagerly
    # loaded by default.
    query = query.options(eagerload('author'))

    pagination = Pagination(request, query, request.args.get('page', type=int))
    return render_template(template_name, pagination=pagination,
                           order_by=order_by, topics=pagination.get_objects(),
                           **context)


def _topic_feed(request, title, query, order_by):
    # non moderators cannot see deleted posts, so we filter them out first
    # for moderators we mark the posts up as deleted so that
    # they can be kept apart from non-deleted ones.
    if not request.user or not request.user.is_moderator:
        query = query.filter_by(is_deleted=False)
    query = query.order_by(_topic_order[order_by])
    query = query.options(eagerload('author'), eagerload('question'))
    query = query.limit(max(0, min(50, request.args.get('num', 10, type=int))))

    feed = AtomFeed(u'%s — %s' % (title, settings.WEBSITE_TITLE),
                    subtitle=settings.WEBSITE_TAGLINE,
                    feed_url=request.url,
                    url=request.url_root)

    for topic in query.all():
        title = topic.title
        if topic.is_deleted:
            title += u' ' + _(u'(deleted)')
        feed.add(title, topic.question.rendered_text, content_type='html',
                 author=topic.author.display_name,
                 url=url_for(topic, _external=True),
                 id=topic.guid, updated=topic.last_change, published=topic.date)

    return feed.get_response()


def overview(request, order_by):
    """Shows the overview page for the given language of the knowledge base.
    This page tries to select the "hottest" topics.
    """
    query = Topic.query.language(request.view_lang)
    return _topic_list('kb/overview.html', request, query, order_by)


def overview_feed(request, order_by):
    """Feed for the overview page."""
    return _topic_feed(request, _(u'Questions'),
                       Topic.query.language(request.view_lang), order_by)


def unanswered(request, order_by):
    """Show only the unanswered topics."""
    query = Topic.query.language(request.view_lang).unanswered()
    return _topic_list('kb/unanswered.html', request, query, order_by)


def unanswered_feed(request, order_by):
    """Feed for the unanswered topic list."""
    return _topic_feed(request, _(u'Unanswered Questions'),
                       Topic.query.language(request.view_lang).unanswered(),
                       order_by)


def by_tag(request, name, order_by):
    """Show only the unanswered topics."""
    tag = Tag.query.filter(
        (Tag.name == name) &
        (Tag.locale == request.view_lang)
    ).first()
    if tag is None:
        raise NotFound()
    return _topic_list('kb/by_tag.html', request, tag.topics, order_by,
                       tag=tag)


def by_tag_feed(request, name, order_by):
    """The feed for a tag."""
    tag = Tag.query.filter(
        (Tag.name == name) &
        (Tag.locale == request.view_lang)
    ).first()
    if tag is None:
        raise NotFound()
    return _topic_feed(request, _(u'Questions Tagged “%s”') % tag.name,
                       tag.topics, order_by)


def tags(request):
    """Shows the tag-cloud."""
    tags = Tag.query.filter(
        (Tag.tagged > 0) &
        (Tag.locale == request.view_lang)
    ).order_by(Tag.tagged.desc()).limit(40).all()
    tags.sort(key=lambda x: x.name.lower())
    return render_template('kb/tags.html', tags=tags)


def topic(request, id, slug=None):
    """Shows a topic."""
    topic = Topic.query.eagerposts().get(id)

    # if the topic id does not exist or the topic is from a different
    # language, we abort with 404 early
    if topic is None or topic.locale != request.view_lang:
        raise NotFound()

    # make sure the slug is okay, otherwise redirect to the real one
    # to ensure URLs are unique.
    if slug is None or topic.slug != slug:
        return redirect(url_for(topic))

    # deleted posts cannot be seen by people without privilegs
    if topic.is_deleted and not (request.user and request.user.is_moderator):
        raise Forbidden()

    # a form for the replies.
    form = ReplyForm(topic)

    if request.method == 'POST' and form.validate():
        reply = form.create_reply()
        session.commit()
        request.flash(_(u'Your reply was posted.'))
        return redirect(url_for(reply))

    # pull in the votes in a single query for all the posts related to the
    # topic so that we only have to fire the database once.
    if request.is_logged_in:
        request.user.pull_votes(topic.posts)

    return render_template('kb/topic.html', topic=topic,
                           reply_form=form.as_widget())


def topic_feed(request, id, slug=None):
    """A feed for the answers to a question."""
    topic = Topic.query.eagerposts().get(id)

    # if the topic id does not exist or the topic is from a different
    # language, we abort with 404 early
    if topic is None or topic.locale != request.view_lang:
        raise NotFound()

    # make sure the slug is okay, otherwise redirect to the real one
    # to ensure URLs are unique.
    if slug is None or topic.slug != slug:
        return redirect(url_for(topic, action='feed'))

    # deleted posts cannot be seen by people without privilegs
    if topic.is_deleted and not (request.user and request.user.is_moderator):
        raise Forbidden()

    feed = AtomFeed(u'%s — %s' % (topic.title, settings.WEBSITE_TITLE),
                    subtitle=settings.WEBSITE_TAGLINE,
                    feed_url=request.url,
                    url=request.url_root)

    feed.add(topic.title, topic.question.rendered_text, content_type='html',
             author=topic.question.author.display_name,
             url=url_for(topic, _external=True),
             id=topic.guid, updated=topic.question.updated,
             published=topic.question.created)

    for reply in topic.replies:
        if reply.is_deleted and not (request.user and request.user.is_moderator):
            continue
        title = _(u'Answer by %s') % reply.author.display_name
        if reply.is_deleted:
            title += u' ' + _('(deleted)')
        feed.add(title, reply.rendered_text, content_type='html',
                 author=reply.author.display_name,
                 url=url_for(reply, _external=True),
                 id=reply.guid, updated=reply.updated, created=reply.created)

    return feed.get_response()


@require_login
def new(request):
    """The new-question form."""
    form = QuestionForm()

    if request.method == 'POST' and form.validate():
        topic = form.create_topic()
        session.commit()
        request.flash(_(u'Your question was posted.'))
        return redirect(url_for(topic))

    return render_template('kb/new.html', form=form.as_widget())


def _load_post_and_revision(request, id):
    post = Post.query.get(id)
    if post is None or post.topic.locale != request.view_lang:
        raise NotFound()
    if post.is_deleted and not (request.user and request.user.is_moderator):
        raise Forbidden()
    revision_id = request.args.get('rev', type=int)
    revision = None
    if revision_id is not None:
        revision = post.get_revision(revision_id)
        if revision is None:
            raise NotFound()
    return post, revision


@require_login
def edit_post(request, id):
    post, revision = _load_post_and_revision(request, id)
    if not request.user.can_edit(post):
        raise Forbidden()

    if post.is_question:
        form = QuestionForm(post.topic, revision=revision)
    else:
        form = ReplyForm(post=post, revision=revision)

    if request.method == 'POST' and form.validate():
        form.save_changes()
        session.commit()
        request.flash(_('The post was edited.'))
        return redirect(url_for(post))

    def _format_entry(author, date, extra=u''):
        return _(u'%s (%s)') % (author, format_datetime(date)) + extra
    post_revisions = [(revision is None, '', _format_entry(
            (post.editor or post.author).display_name, post.updated,
            u' [%s]' % _(u'Current revision')))] + \
        [(revision == entry, entry.id, _format_entry(
            entry.editor.display_name, entry.date))
         for entry in post.revisions.order_by(PostRevision.date.desc())]

    return render_template('kb/edit_post.html', form=form.as_widget(),
                           post=post, all_revisions=post_revisions)


@require_login
def delete_post(request, id):
    post = Post.query.get(id)

    # sanity checks
    if not request.user.is_moderator:
        raise Forbidden()
    elif post.is_deleted:
        return redirect(url_for(post))

    form = EmptyForm()
    if request.method == 'POST' and form.validate():
        if 'yes' in request.form:
            post.delete()
            session.commit()
            request.flash(_('The post was deleted'))
        return redirect(url_for(post))

    return render_template('kb/delete_post.html', post=post,
                           form=form.as_widget())


@require_login
def restore_post(request, id):
    post, revision = _load_post_and_revision(request, id)

    # sanity checks
    if revision is None:
        if not request.user.is_moderator:
            raise Forbidden()
        elif not post.is_deleted:
            return redirect(url_for(post))
    elif not request.user.can_edit(post):
        raise Forbidden()

    form = EmptyForm()
    if request.method == 'POST' and form.validate():
        if 'yes' in request.form:
            if revision is None:
                request.flash(_(u'The post was restored'))
                post.restore()
            else:
                request.flash(_(u'The revision was restored'))
                revision.restore()
            session.commit()
        return form.redirect(post)

    return render_template('kb/restore_post.html', form=form.as_widget(),
                           post=post, revision=revision)


def post_revisions(request, id):
    """Shows all post revisions and a diff of the text."""
    post = Post.query.get(id)
    if post is None or post.topic.locale != request.view_lang:
        raise NotFound()
    if post.is_deleted and not (request.user and request.user.is_moderator):
        raise Forbidden()

    revisions = [{
        'id':       None,
        'latest':   True,
        'date':     post.updated,
        'editor':   post.editor or post.author,
        'text':     post.text
    }] + [{
        'id':       revision.id,
        'latest':   False,
        'date':     revision.date,
        'editor':   revision.editor,
        'text':     revision.text
    } for revision in post.revisions.order_by(PostRevision.date.desc())]

    last_text = None
    for revision in reversed(revisions):
        if last_text is not None:
            revision['diff'] = format_creole_diff(last_text, revision['text'])
        else:
            revision['diff'] = format_creole(revision['text'])
        last_text = revision['text']

    return render_template('kb/post_revisions.html', post=post,
                           revisions=revisions)


def userlist(request):
    """Shows a user list."""
    return common_userlist(request, locale=request.view_lang)


@no_cache
@require_login
@exchange_token_protected
def vote(request, post):
    """Votes on a post."""
    # TODO: this is currently also fired as GET if JavaScript is
    # not available.  Not very nice.
    post = Post.query.get(post)
    if post is None:
        raise NotFound()

    # you cannot cast votes on deleted shit
    if post.is_deleted:
        message = _(u'You cannot vote on deleted posts.')
        if request.is_xhr:
            return json_response(message=message, error=True)
        request.flash(message, error=True)
        return redirect(url_for(post))

    # otherwise
    val = request.args.get('val', 0, type=int)
    if val == 0:
        request.user.unvote(post)
    elif val == 1:
        # users cannot upvote on their own stuff
        if post.author == request.user:
            message = _(u'You cannot upvote your own post.')
            if request.is_xhr:
                return json_response(message=message, error=True)
            request.flash(message, error=True)
            return redirect(url_for(post))
        # also some reputation is needed
        if not request.user.is_admin and \
           request.user.reputation < settings.REPUTATION_MAP['UPVOTE']:
            message = _(u'In order to upvote you '
                        u'need at least %d reputation') % \
                settings.REPUTATION_MAP['UPVOTE']
            if request.is_xhr:
                return json_response(message=message, error=True)
            request.flash(message, error=True)
            return redirect(url_for(post))
        request.user.upvote(post)
    elif val == -1:
        # users need some reputation to downvote.  Keep in mind that
        # you *can* downvote yourself.
        if not request.user.is_admin and \
           request.user.reputation < settings.REPUTATION_MAP['DOWNVOTE']:
            message = _(u'In order to downvote you '
                        u'need at least %d reputation') % \
                settings.REPUTATION_MAP['DOWNVOTE']
            if request.is_xhr:
                return json_response(message=message, error=True)
            request.flash(message, error=True)
            return redirect(url_for(post))
        request.user.downvote(post)
    else:
        raise BadRequest()
    session.commit()

    # standard requests are answered with a redirect back
    if not request.is_xhr:
        return redirect(url_for(post))

    # others get a re-rendered vote box
    box = get_macro('kb/_boxes.html', 'render_vote_box')
    return json_response(html=box(post, request.user))


@no_cache
@exchange_token_protected
@require_login
def accept(request, post):
    """Accept a post as an answer."""
    # TODO: this is currently also fired as GET if JavaScript is
    # not available.  Not very nice.
    post = Post.query.get(post)
    if post is None:
        raise NotFound()

    # just for sanity.  It makes no sense to accept the question
    # as answer.  The UI does not allow that, so the user must have
    # tampered with the data here.
    if post.is_question:
        raise BadRequest()

    # likewise you cannot accept a deleted post as answer
    if post.is_deleted:
        message = _(u'You cannot accept deleted posts as answers')
        if request.is_xhr:
            return json_response(message=message, error=True)
        request.flash(message, error=True)
        return redirect(url_for(post))

    topic = post.topic

    # if the post is already the accepted answer, we unaccept the
    # post as answer.
    if post.is_answer:
        if not request.user.can_unaccept_as_answer(post):
            message = _(u'You cannot unaccept this reply as an answer.')
            if request.is_xhr:
                return json_response(message=message, error=True)
            request.flash(message, error=True)
            return redirect(url_for(post))
        topic.accept_answer(None, request.user)
        session.commit()
        if request.is_xhr:
            return json_response(accepted=False)
        return redirect(url_for(post))

    # otherwise we try to accept the post as answer.
    if not request.user.can_accept_as_answer(post):
        message = _(u'You cannot accept this reply as answer.')
        if request.is_xhr:
            return json_response(message=message, error=True)
        request.flash(message, error=True)
        return redirect(url_for(post))
    topic.accept_answer(post, request.user)
    session.commit()
    if request.is_xhr:
        return json_response(accepted=True)
    return redirect(url_for(post))


def _get_comment_form(post):
    return CommentForm(post, action=url_for('kb.submit_comment',
                                            post=post.id))


def get_comments(request, post, form=None):
    """Returns the partial comment template.  This is intended to be
    used on by XHR requests.
    """
    if not request.is_xhr:
        raise BadRequest()
    post = Post.query.get(post)
    if post is None:
        raise NotFound()

    # sanity check.  This should not happen because the UI does not provide
    # a link to retrieve the comments, but it could happen if the user
    # accesses the URL directly or if he requests the comments to be loaded
    # after a moderator deleted the post.
    if post.is_deleted and not (request.user and request.user.is_moderator):
        raise Forbidden()

    form = _get_comment_form(post)
    return json_response(html=render_template('kb/_comments.html', post=post,
                                              form=form.as_widget()))


@require_login
def submit_comment(request, post):
    """Used by the form on `get_comments` to submit the form data to
    the database.  Returns partial data for the remote side.
    """
    if not request.is_xhr:
        raise BadRequest()
    post = Post.query.get(post)
    if post is None:
        raise NotFound()

    # not even moderators can submit comments for deleted posts.
    if post.is_deleted:
        message = _(u'You cannot submit comments for deleted posts')
        return json_response(success=False, form_errors=[message])

    form = _get_comment_form(post)
    if form.validate():
        comment = form.create_comment()
        session.commit()
        comment_box = get_macro('kb/_boxes.html', 'render_comment')
        comment_link = get_macro('kb/_boxes.html', 'render_comment_link')
        return json_response(html=comment_box(comment),
                             link=comment_link(post),
                             success=True)
    return json_response(success=False, form_errors=form.as_widget().all_errors)


def get_tags(request):
    """A helper that returns the tags for the language."""
    limit = max(0, min(request.args.get('limit', 10, type=int), 20))
    query = Tag.query.filter(
        (Tag.locale == request.view_lang) &
        (Tag.tagged > 0)
    )
    q = request.args.get('q')
    if q:
        query = query.filter(Tag.name.like('%%%s%%' % q))
    query = query.order_by(Tag.tagged.desc(), Tag.name)
    return json_response(tags=[(tag.name, tag.tagged)
                               for tag in query.limit(limit).all()])


#: the knowledge base userlist is just a wrapper around the common
#: userlist from the users module.
from solace.views.users import userlist as common_userlist

########NEW FILE########
__FILENAME__ = themes
# -*- coding: utf-8 -*-
"""
    solace.views.themes
    ~~~~~~~~~~~~~~~~~~~

    Implements support for the themes.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
import mimetypes
from werkzeug import Response, wrap_file
from werkzeug.exceptions import NotFound
from solace.templating import get_theme
from solace import settings


def get_resource(request, theme, file):
    """Returns a file from the theme."""
    theme = get_theme(theme)
    if theme is None:
        raise NotFound()
    f = theme.open_resource(file)
    if f is None:
        raise NotFound()
    resp = Response(wrap_file(request.environ, f),
                    mimetype=mimetypes.guess_type(file)[0] or 'text/plain',
                    direct_passthrough=True)
    resp.add_etag()
    return resp.make_conditional(request)

########NEW FILE########
__FILENAME__ = users
# -*- coding: utf-8 -*-
"""
    solace.views.users
    ~~~~~~~~~~~~~~~~~~

    User profiles and account management.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from sqlalchemy.orm import eagerload
from werkzeug import redirect
from werkzeug.exceptions import NotFound
from babel import Locale

from solace import settings
from solace.application import url_for, require_login
from solace.auth import get_auth_system
from solace.database import session
from solace.models import User, Topic, Post
from solace.templating import render_template
from solace.utils.pagination import Pagination
from solace.i18n import list_sections, _


def userlist(request, locale=None):
    """Displays list of users.  Optionally a locale identifier can be passed
    in that replaces the default "all users" query.  This is used by the
    userlist form the knowledge base that forwards the call here.
    """
    query = User.query
    if locale is not None:
        # if we just have one language, we ignore that there is such a thing
        # as being active in a section of the webpage and redirect to the
        # general user list.
        if len(settings.LANGUAGE_SECTIONS) == 1:
            return redirect(url_for('users.userlist'))
        locale = Locale.parse(locale)
        query = query.active_in(locale)
    query = query.order_by(User.reputation.desc())
    pagination = Pagination(request, query, request.args.get('page', type=int))
    return render_template('users/userlist.html', pagination=pagination,
                           users=pagination.get_objects(), locale=locale,
                           sections=list_sections())


def profile(request, username):
    """Shows a users's profile."""
    user = User.query.filter_by(username=username).first()
    if user is None:
        raise NotFound()

    topics = Topic.query.eagerposts().filter_by(author=user) \
        .order_by(Topic.votes.desc()).limit(4).all()
    replies = Post.query.options(eagerload('topic')) \
        .filter_by(is_question=False, author=user) \
        .order_by(Post.votes.desc()).limit(15).all()

    # count and sort all badges
    badges = {}
    for badge in user.badges:
        badges[badge] = badges.get(badge, 0) + 1
    badges = sorted(badges.items(), key=lambda x: (-x[1], x[0].name.lower()))

    # we only create the active_in list if there are multiple sections
    if len(settings.LANGUAGE_SECTIONS) > 1:
        active_in = sorted(user.activities.items(),
                           key=lambda x: x[1].counter, reverse=True)
    else:
        active_in = None

    return render_template('users/profile.html', user=user,
                           active_in=active_in, topics=topics,
                           replies=replies, badges=badges)



@require_login
def edit_profile(request):
    """Allows the user to change profile information."""
    return get_auth_system().edit_profile(request)

########NEW FILE########
__FILENAME__ = _openid_auth
# -*- coding: utf-8 -*-
"""
    solace._openid_auth
    ~~~~~~~~~~~~~~~~~~~

    Implements a simple OpenID driven store.

    :copyright: (c) 2010 by the Solace Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

from time import time
from hashlib import sha1
from contextlib import closing

from openid.association import Association
from openid.store.interface import OpenIDStore
from openid.consumer.consumer import Consumer, SUCCESS, CANCEL
from openid.consumer import discover
from openid.store import nonce

from sqlalchemy.orm import scoped_session
from sqlalchemy.exceptions import SQLError

from werkzeug import redirect
from werkzeug.exceptions import NotFound

from solace.i18n import _, lazy_gettext
from solace.application import url_for
from solace.templating import render_template
from solace.database import get_engine, session
from solace.schema import openid_association, openid_user_nonces
from solace.models import User
from solace.forms import OpenIDLoginForm, OpenIDRegistrationForm
from solace.auth import AuthSystemBase, LoginUnsucessful
from solace import settings


class SolaceOpenIDStore(OpenIDStore):
    """Implements the open store for solace using the database."""

    def connection(self):
        return closing(get_engine().connect())

    def storeAssociation(self, server_url, association):
        with self.connection() as con:
            con.execute(openid_association.insert(),
                server_url=server_url,
                handle=association.handle,
                secret=association.secret.encode('base64'),
                issued=association.issued,
                lifetime=association.lifetime,
                assoc_type=association.assoc_type
            )

    def getAssociation(self, server_url, handle=None):
        filter = openid_association.c.server_url == server_url
        if handle is not None:
            filter &= openid_association.c.handle == handle
        with self.connection() as con:
            result = con.execute(openid_association.select(filter))
            result_assoc = None
            for row in result.fetchall():
                assoc = Association(row.handle, row.secret.decode('base64'),
                                    row.issued, row.lifetime, row.assoc_type)
                if assoc.getExpiresIn() <= 0:
                    self.removeAssociation(server_url, assoc.handle)
                else:
                    result_assoc = assoc
            return result_assoc

    def removeAssociation(self, server_url, handle):
        with self.connection() as con:
            return con.execute(openid_association.delete(
                (openid_association.c.server_url == server_url) &
                (openid_association.c.handle == handle)
            )).rowcount > 0

    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time()) > nonce.SKEW:
            return False
        with self.connection() as con:
            row = con.execute(openid_user_nonces.select(
                (openid_user_nonces.c.server_url == server_url) &
                (openid_user_nonces.c.timestamp == timestamp) &
                (openid_user_nonces.c.salt == salt)
            )).fetchone()
            if row is not None:
                return False
            con.execute(openid_user_nonces.insert(),
                server_url=server_url,
                timestamp=timestamp,
                salt=salt
            )
            return True

    def cleanupNonces(self):
        with self.connection() as con:
            return con.execute(openid_user_nonces.delete(
                openid_user_nonces.c.timestamp <= int(time() - nonce.SKEW)
            )).rowcount

    def cleanupAssociations(self):
        with self.connection() as con:
            return con.execute(openid_association.delete(
                openid_association.c.issued +
                    openid_association.c.lifetime < int(time())
            )).rowcount

    def getAuthKey(self):
        return sha1(settings.SECRET_KEY).hexdigest()[:self.AUTH_KEY_LEN]

    def isDump(self):
        return False


class OpenIDAuth(AuthSystemBase):
    """Authenticate against openid.  Requires the Python OpenID library
    to be installed.  (python-openid).
    """

    password_managed_external = True
    passwordless = True
    show_register_link = False

    def register(self, request):
        # the register link is a complete noop.  The actual user registration
        # on first login happens in the login handling.
        raise NotFound()

    def first_login(self, request):
        """Until the openid information is removed from the session, this view
        will be use to create the user account based on the openid url.
        """
        identity_url = request.session.get('openid')
        if identity_url is None:
            return redirect(url_for('core.login'))
        if request.is_logged_in:
            del request.session['openid']
            return redirect(request.next_url or url_for('kb.overview'))

        form = OpenIDRegistrationForm()
        if request.method == 'POST' and form.validate():
            user = User(form['username'], form['email'])
            user.openid_logins.add(identity_url)
            self.after_register(request, user)
            session.commit()
            del request.session['openid']
            self.set_user_checked(request, user)
            return self.redirect_back(request)

        return render_template('core/register_openid.html', form=form.as_widget(),
                               identity_url=identity_url)

    def redirect_back(self, request):
        return redirect(request.get_redirect_target([
            url_for('core.login'),
            url_for('core.register')
        ]) or url_for('kb.overview'))

    def before_login(self, request):
        if request.args.get('openid_complete') == 'yes':
            return self.complete_login(request)
        elif request.args.get('firstlogin') == 'yes':
            return self.first_login(request)

    def complete_login(self, request):
        consumer = Consumer(request.session, SolaceOpenIDStore())
        openid_response = consumer.complete(request.args.to_dict(),
                                            url_for('core.login', _external=True))
        if openid_response.status == SUCCESS:
            return self.create_or_login(request, openid_response.identity_url)
        elif openid_response.status == CANCEL:
            raise LoginUnsucessful(_(u'The request was cancelled'))
        else:
            raise LoginUnsucessful(_(u'OpenID authentication error'))

    def create_or_login(self, request, identity_url):
        user = User.query.by_openid_login(identity_url).first()
        # we don't have a user for this openid yet.  What we want to do
        # now is to remember the openid in the session until we have the
        # user.  We're using the session because it is signed.
        if user is None:
            request.session['openid'] = identity_url
            return redirect(url_for('core.login', firstlogin='yes',
                                    next=request.next_url))

        self.set_user_checked(request, user)
        return self.redirect_back(request)

    def set_user_checked(self, request, user):
        if not user.is_active:
            raise LoginUnsucessful(_(u'The user is not yet activated.'))
        if user.is_banned:
            raise LoginUnsucessful(_(u'The user got banned from the system.'))
        self.set_user(request, user)

    def perform_login(self, request, openid_identifier):
        try:
            consumer = Consumer(request.session, SolaceOpenIDStore())
            auth_request = consumer.begin(openid_identifier)
        except discover.DiscoveryFailure:
            raise LoginUnsucessful(_(u'The OpenID was invalid'))
        trust_root = request.host_url
        redirect_to = url_for('core.login', openid_complete='yes',
                              next=request.next_url, _external=True)
        return redirect(auth_request.redirectURL(trust_root, redirect_to))

    def get_login_form(self):
        return OpenIDLoginForm()

    def render_login_template(self, request, form):
        return render_template('core/login_openid.html', form=form.as_widget())

########NEW FILE########
