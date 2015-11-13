__FILENAME__ = forms
class UserKwargModelFormMixin(object):
    """
    Generic model form mixin for popping user out of the kwargs and
    attaching it to the instance.

    This mixin must precede forms.ModelForm/forms.Form. The form is not
    expecting these kwargs to be passed in, so they must be popped off before
    anything else is done.
    """
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # Pop the user off the
                                              # passed in kwargs.
        super(UserKwargModelFormMixin, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = _access
import six

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpResponseRedirect
from django.utils.encoding import force_text


class AccessMixin(object):
    """
    'Abstract' mixin that gives access mixins the same customizable
    functionality.
    """
    login_url = None
    raise_exception = False  # Default whether to raise an exception to none
    redirect_field_name = REDIRECT_FIELD_NAME  # Set by django.contrib.auth

    def get_login_url(self):
        """
        Override this method to customize the login_url.
        """
        login_url = self.login_url or settings.LOGIN_URL
        if not login_url:
            raise ImproperlyConfigured(
                'Define {0}.login_url or settings.LOGIN_URL or override '
                '{0}.get_login_url().'.format(self.__class__.__name__))

        return force_text(login_url)

    def get_redirect_field_name(self):
        """
        Override this method to customize the redirect_field_name.
        """
        if self.redirect_field_name is None:
            raise ImproperlyConfigured(
                '{0} is missing the '
                'redirect_field_name. Define {0}.redirect_field_name or '
                'override {0}.get_redirect_field_name().'.format(
                    self.__class__.__name__))
        return self.redirect_field_name


class LoginRequiredMixin(AccessMixin):
    """
    View mixin which verifies that the user is authenticated.

    NOTE:
        This should be the left-most mixin of a view, except when
        combined with CsrfExemptMixin - which in that case should
        be the left-most mixin.
    """
    redirect_unauthenticated_users = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            if self.raise_exception and not self.redirect_unauthenticated_users:
                raise PermissionDenied  # return a forbidden response
            else:
                return redirect_to_login(request.get_full_path(),
                                         self.get_login_url(),
                                         self.get_redirect_field_name())

        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class AnonymousRequiredMixin(object):
    """
    View mixin which redirects to a specified URL if authenticated.
    Can be useful if you wanted to prevent authenticated users from
    accessing signup pages etc.

    NOTE:
        This should be the left-most mixin of a view.

    Example Usage

        class SomeView(AnonymousRequiredMixin, ListView):
            ...
            # required
            authenticated_redirect_url = "/accounts/profile/"
            ...
    """
    authenticated_redirect_url = settings.LOGIN_REDIRECT_URL

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect(self.get_authenticated_redirect_url())
        return super(AnonymousRequiredMixin, self).dispatch(
            request, *args, **kwargs)

    def get_authenticated_redirect_url(self):
        """ Return the reversed authenticated redirect url. """
        if not self.authenticated_redirect_url:
            raise ImproperlyConfigured(
                '{0} is missing an authenticated_redirect_url '
                'url to redirect to. Define '
                '{0}.authenticated_redirect_url or override '
                '{0}.get_authenticated_redirect_url().'.format(
                    self.__class__.__name__))
        return self.authenticated_redirect_url


class PermissionRequiredMixin(AccessMixin):
    """
    View mixin which verifies that the logged in user has the specified
    permission.

    Class Settings
    `permission_required` - the permission to check for.
    `login_url` - the login url of site
    `redirect_field_name` - defaults to "next"
    `raise_exception` - defaults to False - raise 403 if set to True

    Example Usage

        class SomeView(PermissionRequiredMixin, ListView):
            ...
            # required
            permission_required = "app.permission"

            # optional
            login_url = "/signup/"
            redirect_field_name = "hollaback"
            raise_exception = True
            ...
    """
    permission_required = None  # Default required perms to none

    def get_permission_required(self, request=None):
        """
        Get the required permissions and return them.

        Override this to allow for custom permission_required values.
        """
        # Make sure that the permission_required attribute is set on the
        # view, or raise a configuration error.
        if self.permission_required is None:
            raise ImproperlyConfigured(
                '{0} requires the "permission_required" attribute to be '
                'set.'.format(self.__class__.__name__))

        return self.permission_required

    def check_permissions(self, request):
        """
        Returns whether or not the user has permissions
        """
        perms = self.get_permission_required(request)
        return request.user.has_perm(perms)

    def no_permissions_fail(self, request=None):
        """
        Called when the user has no permissions. This should only
        return a valid HTTP response.

        By default we redirect to login.
        """
        return redirect_to_login(request.get_full_path(),
                                 self.get_login_url(),
                                 self.get_redirect_field_name())

    def dispatch(self, request, *args, **kwargs):
        """
        Check to see if the user in the request has the required
        permission.
        """
        has_permission = self.check_permissions(request)

        if not has_permission:  # If the user lacks the permission
            if self.raise_exception:
                raise PermissionDenied  # Return a 403
            return self.no_permissions_fail(request)

        return super(PermissionRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class MultiplePermissionsRequiredMixin(PermissionRequiredMixin):
    """
    View mixin which allows you to specify two types of permission
    requirements. The `permissions` attribute must be a dict which
    specifies two keys, `all` and `any`. You can use either one on
    its own or combine them. The value of each key is required to be a
    list or tuple of permissions. The standard Django permissions
    style is not strictly enforced. If you have created your own
    permissions in a different format, they should still work.

    By specifying the `all` key, the user must have all of
    the permissions in the passed in list.

    By specifying The `any` key , the user must have ONE of the set
    permissions in the list.

    Class Settings
        `permissions` - This is required to be a dict with one or both
            keys of `all` and/or `any` containing a list or tuple of
            permissions.
        `login_url` - the login url of site
        `redirect_field_name` - defaults to "next"
        `raise_exception` - defaults to False - raise 403 if set to True

    Example Usage
        class SomeView(MultiplePermissionsRequiredMixin, ListView):
            ...
            #required
            permissions = {
                "all": ("blog.add_post", "blog.change_post"),
                "any": ("blog.delete_post", "user.change_user")
            }

            #optional
            login_url = "/signup/"
            redirect_field_name = "hollaback"
            raise_exception = True
    """
    permissions = None  # Default required perms to none

    def get_permission_required(self, request=None):
        self._check_permissions_attr()
        return self.permissions

    def check_permissions(self, request):
        permissions = self.get_permission_required(request)
        perms_all = permissions.get('all') or None
        perms_any = permissions.get('any') or None

        self._check_permissions_keys_set(perms_all, perms_any)
        self._check_perms_keys("all", perms_all)
        self._check_perms_keys("any", perms_any)

        # If perms_all, check that user has all permissions in the list/tuple
        if perms_all:
            if not request.user.has_perms(perms_all):
                return False

        # If perms_any, check that user has at least one in the list/tuple
        if perms_any:
            has_one_perm = False
            for perm in perms_any:
                if request.user.has_perm(perm):
                    has_one_perm = True
                    break

            if not has_one_perm:
                return False

        return True

    def _check_permissions_attr(self):
        """
        Check permissions attribute is set and that it is a dict.
        """
        if self.permissions is None or not isinstance(self.permissions, dict):
            raise ImproperlyConfigured(
                '{0} requires the "permissions" attribute to be set as a '
                'dict.'.format(self.__class__.__name__))

    def _check_permissions_keys_set(self, perms_all=None, perms_any=None):
        """
        Check to make sure the keys `any` or `all` are not both blank.
        If both are blank either an empty dict came in or the wrong keys
        came in. Both are invalid and should raise an exception.
        """
        if perms_all is None and perms_any is None:
            raise ImproperlyConfigured(
                '{0} requires the "permissions" attribute to be set to a '
                'dict and the "any" or "all" key to be set.'.format(
                    self.__class__.__name__))

    def _check_perms_keys(self, key=None, perms=None):
        """
        If the permissions list/tuple passed in is set, check to make
        sure that it is of the type list or tuple.
        """
        if perms and not isinstance(perms, (list, tuple)):
            raise ImproperlyConfigured(
                '{0} requires the permisions dict {1} value to be a '
                'list or tuple.'.format(self.__class__.__name__, key))


class GroupRequiredMixin(AccessMixin):
    group_required = None

    def get_group_required(self):
        if self.group_required is None or (
                not isinstance(self.group_required,
                               (list, tuple) + six.string_types)
        ):

            raise ImproperlyConfigured(
                '{0} requires the "group_required" attribute to be set and be '
                'one of the following types: string, unicode, list or '
                'tuple'.format(self.__class__.__name__))
        if not isinstance(self.group_required, (list, tuple)):
            self.group_required = (self.group_required,)
        return self.group_required

    def check_membership(self, groups):
        """ Check required group(s) """
        if self.request.user.is_superuser:
            return True
        user_groups = self.request.user.groups.values_list("name", flat=True)
        return set(groups).intersection(set(user_groups))

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        in_group = False
        if self.request.user.is_authenticated():
            in_group = self.check_membership(self.get_group_required())

        if not in_group:
            if self.raise_exception:
                raise PermissionDenied
            else:
                return redirect_to_login(
                    request.get_full_path(),
                    self.get_login_url(),
                    self.get_redirect_field_name())
        return super(GroupRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class UserPassesTestMixin(AccessMixin):
    """
    CBV Mixin allows you to define test that every user should pass
    to get access into view.

    Class Settings
        `test_func` - This is required to be a method that takes user
            instance and return True or False after checking conditions.
        `login_url` - the login url of site
        `redirect_field_name` - defaults to "next"
        `raise_exception` - defaults to False - raise 403 if set to True
    """

    def test_func(self, user):
        raise NotImplementedError(
            '{0} is missing implementation of the '
            'test_func method. You should write one.'.format(
                self.__class__.__name__))

    def get_test_func(self):
        return getattr(self, "test_func")

    def dispatch(self, request, *args, **kwargs):
        user_test_result = self.get_test_func()(request.user)

        if not user_test_result:  # If user don't pass the test
            if self.raise_exception:  # *and* if an exception was desired
                raise PermissionDenied
            else:
                return redirect_to_login(request.get_full_path(),
                                         self.get_login_url(),
                                         self.get_redirect_field_name())
        return super(UserPassesTestMixin, self).dispatch(
            request, *args, **kwargs)


class SuperuserRequiredMixin(AccessMixin):
    """
    Mixin allows you to require a user with `is_superuser` set to True.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:  # If the user is a standard user,
            if self.raise_exception:  # *and* if an exception was desired
                raise PermissionDenied  # return a forbidden response.
            else:
                return redirect_to_login(request.get_full_path(),
                                         self.get_login_url(),
                                         self.get_redirect_field_name())

        return super(SuperuserRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class StaffuserRequiredMixin(AccessMixin):
    """
    Mixin allows you to require a user with `is_staff` set to True.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:  # If the request's user is not staff,
            if self.raise_exception:  # *and* if an exception was desired
                raise PermissionDenied  # return a forbidden response
            else:
                return redirect_to_login(request.get_full_path(),
                                         self.get_login_url(),
                                         self.get_redirect_field_name())

        return super(StaffuserRequiredMixin, self).dispatch(
            request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = _ajax
import six

from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseBadRequest

## Django 1.5+ compat
try:
    import json
except ImportError:  # pragma: no cover
    from django.utils import simplejson as json


class JSONResponseMixin(object):
    """
    A mixin that allows you to easily serialize simple data such as a dict or
    Django models.
    """
    content_type = None
    json_dumps_kwargs = None
    json_encoder_class = DjangoJSONEncoder

    def get_content_type(self):
        if (self.content_type is not None and
            not isinstance(self.content_type,
                           (six.string_types, six.text_type))):
            raise ImproperlyConfigured(
                '{0} is missing a content type. Define {0}.content_type, '
                'or override {0}.get_content_type().'.format(
                    self.__class__.__name__))
        return self.content_type or u"application/json"

    def get_json_dumps_kwargs(self):
        if self.json_dumps_kwargs is None:
            self.json_dumps_kwargs = {}
        self.json_dumps_kwargs.setdefault(u'ensure_ascii', False)
        return self.json_dumps_kwargs

    def render_json_response(self, context_dict, status=200):
        """
        Limited serialization for shipping plain data. Do not use for models
        or other complex or custom objects.
        """
        json_context = json.dumps(
            context_dict,
            cls=self.json_encoder_class,
            **self.get_json_dumps_kwargs()).encode(u'utf-8')
        return HttpResponse(json_context,
                            content_type=self.get_content_type(),
                            status=status)

    def render_json_object_response(self, objects, **kwargs):
        """
        Serializes objects using Django's builtin JSON serializer. Additional
        kwargs can be used the same way for django.core.serializers.serialize.
        """
        json_data = serializers.serialize(u"json", objects, **kwargs)
        return HttpResponse(json_data, content_type=self.get_content_type())


class AjaxResponseMixin(object):
    """
    Mixin allows you to define alternative methods for ajax requests. Similar
    to the normal get, post, and put methods, you can use get_ajax, post_ajax,
    and put_ajax.
    """
    def dispatch(self, request, *args, **kwargs):
        request_method = request.method.lower()

        if request.is_ajax() and request_method in self.http_method_names:
            handler = getattr(self, u"{0}_ajax".format(request_method),
                              self.http_method_not_allowed)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return handler(request, *args, **kwargs)

        return super(AjaxResponseMixin, self).dispatch(
            request, *args, **kwargs)

    def get_ajax(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post_ajax(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def put_ajax(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def delete_ajax(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class JsonRequestResponseMixin(JSONResponseMixin):
    """
    Extends JSONResponseMixin.  Attempts to parse request as JSON.  If request
    is properly formatted, the json is saved to self.request_json as a Python
    object.  request_json will be None for imparsible requests.
    Set the attribute require_json to True to return a 400 "Bad Request" error
    for requests that don't contain JSON.

    Note: To allow public access to your view, you'll need to use the
    csrf_exempt decorator or CsrfExemptMixin.

    Example Usage:

        class SomeView(CsrfExemptMixin, JsonRequestResponseMixin):
            def post(self, request, *args, **kwargs):
                do_stuff_with_contents_of_request_json()
                return self.render_json_response(
                    {'message': 'Thanks!'})
    """
    require_json = False
    error_response_dict = {u"errors": [u"Improperly formatted request"]}

    def render_bad_request_response(self, error_dict=None):
        if error_dict is None:
            error_dict = self.error_response_dict
        json_context = json.dumps(
            error_dict,
            cls=self.json_encoder_class,
            **self.get_json_dumps_kwargs()
        ).encode(u'utf-8')
        return HttpResponseBadRequest(
            json_context, content_type=self.get_content_type())

    def get_request_json(self):
        try:
            return json.loads(self.request.body.decode(u'utf-8'))
        except ValueError:
            return None

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

        self.request_json = self.get_request_json()
        if self.require_json and self.request_json is None:
            return self.render_bad_request_response()
        return super(JsonRequestResponseMixin, self).dispatch(
            request, *args, **kwargs)


class JSONRequestResponseMixin(JsonRequestResponseMixin):
    pass

########NEW FILE########
__FILENAME__ = _forms
import six

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.functional import curry, Promise
from django.views.decorators.csrf import csrf_exempt


class CsrfExemptMixin(object):
    """
    Exempts the view from CSRF requirements.

    NOTE:
        This should be the left-most mixin of a view.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CsrfExemptMixin, self).dispatch(*args, **kwargs)


class UserFormKwargsMixin(object):
    """
    CBV mixin which puts the user from the request into the form kwargs.
    Note: Using this mixin requires you to pop the `user` kwarg
    out of the dict in the super of your form's `__init__`.
    """
    def get_form_kwargs(self):
        kwargs = super(UserFormKwargsMixin, self).get_form_kwargs()
        # Update the existing form kwargs dict with the request's user.
        kwargs.update({"user": self.request.user})
        return kwargs


class SuccessURLRedirectListMixin(object):
    """
    Simple CBV mixin which sets the success url to the list view of
    a given app. Set success_list_url as a class attribute of your
    CBV and don't worry about overloading the get_success_url.

    This is only to be used for redirecting to a list page. If you need
    to reverse the url with kwargs, this is not the mixin to use.
    """
    success_list_url = None  # Default the success url to none

    def get_success_url(self):
        # Return the reversed success url.
        if self.success_list_url is None:
            raise ImproperlyConfigured(
                '{0} is missing a succes_list_url '
                'name to reverse and redirect to. Define '
                '{0}.success_list_url or override '
                '{0}.get_success_url().'.format(self.__class__.__name__))
        return reverse(self.success_list_url)


class _MessageAPIWrapper(object):
    """
    Wrap the django.contrib.messages.api module to automatically pass a given
    request object as the first parameter of function calls.
    """
    API = set([
        'add_message', 'get_messages',
        'get_level', 'set_level',
        'debug', 'info', 'success', 'warning', 'error',
    ])

    def __init__(self, request):
        for name in self.API:
            api_fn = getattr(messages.api, name)
            setattr(self, name, curry(api_fn, request))


class _MessageDescriptor(object):
    """
    A descriptor that binds the _MessageAPIWrapper to the view's
    request.
    """
    def __get__(self, instance, owner):
        return _MessageAPIWrapper(instance.request)


class MessageMixin(object):
    """
    Add a `messages` attribute on the view instance that wraps
    `django.contrib .messages`, automatically passing the current
    request object.
    """
    messages = _MessageDescriptor()


class FormValidMessageMixin(MessageMixin):
    """
    Mixin allows you to set static message which is displayed by
    Django's messages framework through a static property on the class
    or programmatically by overloading the get_form_valid_message method.
    """
    form_valid_message = None  # Default to None

    def get_form_valid_message(self):
        """
        Validate that form_valid_message is set and is either a
        unicode or str object.
        """
        if self.form_valid_message is None:
            raise ImproperlyConfigured(
                '{0}.form_valid_message is not set. Define '
                '{0}.form_valid_message, or override '
                '{0}.get_form_valid_message().'.format(self.__class__.__name__)
            )

        if not isinstance(self.form_valid_message,
                          (six.string_types, six.text_type, Promise)):
            raise ImproperlyConfigured(
                '{0}.form_valid_message must be a str or unicode '
                'object.'.format(self.__class__.__name__)
            )

        return force_text(self.form_valid_message)

    def form_valid(self, form):
        """
        Call the super first, so that when overriding
        get_form_valid_message, we have access to the newly saved object.
        """
        response = super(FormValidMessageMixin, self).form_valid(form)
        self.messages.success(self.get_form_valid_message(),
                              fail_silently=True)
        return response


class FormInvalidMessageMixin(MessageMixin):
    """
    Mixin allows you to set static message which is displayed by
    Django's messages framework through a static property on the class
    or programmatically by overloading the get_form_invalid_message method.
    """
    form_invalid_message = None

    def get_form_invalid_message(self):
        """
        Validate that form_invalid_message is set and is either a
        unicode or str object.
        """
        if self.form_invalid_message is None:
            raise ImproperlyConfigured(
                '{0}.form_invalid_message is not set. Define '
                '{0}.form_invalid_message, or override '
                '{0}.get_form_invalid_message().'.format(
                    self.__class__.__name__))

        if not isinstance(self.form_invalid_message,
                          (six.string_types, six.text_type, Promise)):
            raise ImproperlyConfigured(
                '{0}.form_invalid_message must be a str or unicode '
                'object.'.format(self.__class__.__name__))

        return force_text(self.form_invalid_message)

    def form_invalid(self, form):
        response = super(FormInvalidMessageMixin, self).form_invalid(form)
        self.messages.error(self.get_form_invalid_message(),
                            fail_silently=True)
        return response


class FormMessagesMixin(FormValidMessageMixin, FormInvalidMessageMixin):
    """
    Mixin is a shortcut to use both FormValidMessageMixin and
    FormInvalidMessageMixin.
    """
    pass

########NEW FILE########
__FILENAME__ = _other
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import resolve
from django.shortcuts import redirect
from django.utils.encoding import force_text


class SetHeadlineMixin(object):
    """
    Mixin allows you to set a static headline through a static property on the
    class or programmatically by overloading the get_headline method.
    """
    headline = None  # Default the headline to none

    def get_context_data(self, **kwargs):
        kwargs = super(SetHeadlineMixin, self).get_context_data(**kwargs)
        # Update the existing context dict with the provided headline.
        kwargs.update({"headline": self.get_headline()})
        return kwargs

    def get_headline(self):
        if self.headline is None:  # If no headline was provided as a view
                                   # attribute and this method wasn't
                                   # overridden raise a configuration error.
            raise ImproperlyConfigured(
                '{0} is missing a headline. '
                'Define {0}.headline, or override '
                '{0}.get_headline().'.format(self.__class__.__name__))
        return force_text(self.headline)


class StaticContextMixin(object):
    """
    Mixin allows you to set static context through a static property on
    the class.
    """
    static_context = None

    def get_context_data(self, **kwargs):
        kwargs = super(StaticContextMixin, self).get_context_data(**kwargs)

        try:
            kwargs.update(self.get_static_context())
        except (TypeError, ValueError):
            raise ImproperlyConfigured(
                '{0}.static_context must be a dictionary or container '
                'of two-tuples.'.format(self.__class__.__name__))
        else:
            return kwargs

    def get_static_context(self):
        if self.static_context is None:
            raise ImproperlyConfigured(
                '{0} is missing the static_context property. Define '
                '{0}.static_context, or override '
                '{0}.get_static_context()'.format(self.__class__.__name__)
            )
        return self.static_context


class CanonicalSlugDetailMixin(object):
    """
    A mixin that enforces a canonical slug in the url.

    If a urlpattern takes a object's pk and slug as arguments and the slug url
    argument does not equal the object's canonical slug, this mixin will
    redirect to the url containing the canonical slug.
    """
    def dispatch(self, request, *args, **kwargs):
        # Set up since we need to super() later instead of earlier.
        self.request = request
        self.args = args
        self.kwargs = kwargs

        # Get the current object, url slug, and
        # urlpattern name (namespace aware).
        obj = self.get_object()
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        match = resolve(request.path_info)
        url_parts = match.namespaces
        url_parts.append(match.url_name)
        current_urlpattern = ":".join(url_parts)

        # Figure out what the slug is supposed to be.
        if hasattr(obj, "get_canonical_slug"):
            canonical_slug = obj.get_canonical_slug()
        else:
            canonical_slug = self.get_canonical_slug()

        # If there's a discrepancy between the slug in the url and the
        # canonical slug, redirect to the canonical slug.
        if canonical_slug != slug:
            params = {self.pk_url_kwarg: obj.pk,
                      self.slug_url_kwarg: canonical_slug,
                      'permanent': True}
            return redirect(current_urlpattern, **params)

        return super(CanonicalSlugDetailMixin, self).dispatch(
            request, *args, **kwargs)

    def get_canonical_slug(self):
        """
        Override this method to customize what slug should be considered
        canonical.

        Alternatively, define the get_canonical_slug method on this view's
        object class. In that case, this method will never be called.
        """
        return self.get_object().slug


class AllVerbsMixin(object):
    """Call a single method for all HTTP verbs.

    The name of the method should be specified using the class attribute
    ``all_handler``. The default value of this attribute is 'all'.
    """
    all_handler = 'all'

    def dispatch(self, request, *args, **kwargs):
        if not self.all_handler:
            raise ImproperlyConfigured(
                '{0} requires the all_handler attribute to be set.'.format(
                    self.__class__.__name__))

        handler = getattr(self, self.all_handler, self.http_method_not_allowed)
        return handler(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = _queries
from django.core.exceptions import ImproperlyConfigured


class SelectRelatedMixin(object):
    """
    Mixin allows you to provide a tuple or list of related models to
    perform a select_related on.
    """
    select_related = None  # Default related fields to none

    def get_queryset(self):
        if self.select_related is None:  # If no fields were provided,
                                         # raise a configuration error
            raise ImproperlyConfigured(
                '{0} is missing the select_related property. This must be '
                'a tuple or list.'.format(self.__class__.__name__))

        if not isinstance(self.select_related, (tuple, list)):
            # If the select_related argument is *not* a tuple or list,
            # raise a configuration error.
            raise ImproperlyConfigured(
                "{0}'s select_related property must be a tuple or "
                "list.".format(self.__class__.__name__))

        # Get the current queryset of the view
        queryset = super(SelectRelatedMixin, self).get_queryset()

        return queryset.select_related(*self.select_related)


class PrefetchRelatedMixin(object):
    """
    Mixin allows you to provide a tuple or list of related models to
    perform a prefetch_related on.
    """
    prefetch_related = None  # Default prefetch fields to none

    def get_queryset(self):
        if self.prefetch_related is None:  # If no fields were provided,
                                           # raise a configuration error
            raise ImproperlyConfigured(
                '{0} is missing the prefetch_related property. This must be '
                'a tuple or list.'.format(self.__class__.__name__))

        if not isinstance(self.prefetch_related, (tuple, list)):
            # If the prefetch_related argument is *not* a tuple or list,
            # raise a configuration error.
            raise ImproperlyConfigured(
                "{0}'s prefetch_related property must be a tuple or "
                "list.".format(self.__class__.__name__))

        # Get the current queryset of the view
        queryset = super(PrefetchRelatedMixin, self).get_queryset()

        return queryset.prefetch_related(*self.prefetch_related)


class OrderableListMixin(object):
    """
    Mixin allows your users to order records using GET parameters
    """

    orderable_columns = None
    orderable_columns_default = None
    order_by = None
    ordering = None

    def get_context_data(self, **kwargs):
        """
        Augments context with:

            * ``order_by`` - name of the field
            * ``ordering`` - order of ordering, either ``asc`` or ``desc``
        """
        context = super(OrderableListMixin, self).get_context_data(**kwargs)
        context["order_by"] = self.order_by
        context["ordering"] = self.ordering
        return context

    def get_orderable_columns(self):
        if not self.orderable_columns:
            raise ImproperlyConfigured(
                '{0} needs the ordering columns defined.'.format(
                    self.__class__.__name__))
        return self.orderable_columns

    def get_orderable_columns_default(self):
        if not self.orderable_columns_default:
            raise ImproperlyConfigured(
                '{0} needs the default ordering column defined.'.format(
                    self.__class__.__name__))
        return self.orderable_columns_default

    def get_ordered_queryset(self, queryset=None):
        """
        Augments ``QuerySet`` with order_by statement if possible

        :param QuerySet queryset: ``QuerySet`` to ``order_by``
        :return: QuerySet
        """
        get_order_by = self.request.GET.get("order_by")

        if get_order_by in self.get_orderable_columns():
            order_by = get_order_by
        else:
            order_by = self.get_orderable_columns_default()

        self.order_by = order_by
        self.ordering = "asc"

        if order_by and self.request.GET.get("ordering", "asc") == "desc":
            order_by = "-" + order_by
            self.ordering = "desc"

        return queryset.order_by(order_by)

    def get_queryset(self):
        """
        Returns ordered ``QuerySet``
        """
        unordered_queryset = super(OrderableListMixin, self).get_queryset()
        return self.get_ordered_queryset(unordered_queryset)

########NEW FILE########
__FILENAME__ = conftest
import os
from django.conf import settings


def pytest_configure():
    if not settings.configured:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-braces documentation build configuration file, created by
# sphinx-quickstart on Mon Apr 30 10:31:44 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.path.insert(0, os.path.abspath('..'))
import braces
from braces import __version__

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['releases']

releases_issue_uri = "https://github.com/brack3t/django-braces/issues/%s"
releases_release_uri = "https://github.com/brack3t/django-braces/tree/%s"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-braces'
copyright = u'2013, Kenneth Love and Chris Jones'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

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
exclude_patterns = ['_build']

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
htmlhelp_basename = 'django-bracesdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-braces.tex', 'django-braces Documentation',
   'Kenneth Love and Chris Jones', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-braces', 'django-braces Documentation',
     ['Kenneth Love and Chris Jones'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-braces', 'django-braces Documentation',
   'Kenneth Love and Chris Jones', 'django-braces', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = compat
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

try:
    import json
except ImportError:
    from django.utils import simplejson as json

try:
    from django.conf.urls import patterns, url, include
except ImportError:
    from django.conf.urls.defaults import patterns, url, include

########NEW FILE########
__FILENAME__ = factories
from __future__ import absolute_import

import factory

from django.contrib.auth.models import Group, Permission, User

from .models import Article


def _get_perm(perm_name):
    """
    Returns permission instance with given name.

    Permission name is a string like 'auth.add_user'.
    """
    app_label, codename = perm_name.split('.')
    return Permission.objects.get(
        content_type__app_label=app_label, codename=codename)


class ArticleFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Article

    title = factory.Sequence(lambda n: 'Article number {0}'.format(n))
    body = factory.Sequence(lambda n: 'Body of article {0}'.format(n))


class GroupFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Group

    name = factory.Sequence(lambda n: 'group{0}'.format(n))


class UserFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = User

    username = factory.Sequence(lambda n: 'user{0}'.format(n))
    first_name = factory.Sequence(lambda n: 'John {0}'.format(n))
    last_name = factory.Sequence(lambda n: 'Doe {0}'.format(n))
    email = factory.Sequence(lambda n: 'user{0}@example.com'.format(n))
    password = 'asdf1234'

    @classmethod
    def _prepare(cls, create, **kwargs):
        password = kwargs.pop('password', None)
        user = super(UserFactory, cls)._prepare(create, **kwargs)
        if password:
            user.set_password(password)
            if create:
                user.save()
        return user

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if create and extracted:
            # We have a saved object and a list of permission names
            self.user_permissions.add(*[_get_perm(pn) for pn in extracted])

########NEW FILE########
__FILENAME__ = forms
from __future__ import absolute_import

from django import forms

from braces.forms import UserKwargModelFormMixin

from .models import Article


class FormWithUserKwarg(UserKwargModelFormMixin, forms.Form):
    field1 = forms.CharField()


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article

########NEW FILE########
__FILENAME__ = helpers
from django import test
from django.contrib.auth.models import AnonymousUser
from django.core.serializers.json import DjangoJSONEncoder


class TestViewHelper(object):
    """
    Helper class for unit-testing class based views.
    """
    view_class = None
    request_factory_class = test.RequestFactory

    def setUp(self):
        super(TestViewHelper, self).setUp()
        self.factory = self.request_factory_class()

    def build_request(self, method='GET', path='/test/', user=None, **kwargs):
        """
        Creates a request using request factory.
        """
        fn = getattr(self.factory, method.lower())
        if user is None:
            user = AnonymousUser()

        req = fn(path, **kwargs)
        req.user = user
        return req

    def build_view(self, request, args=None, kwargs=None, view_class=None,
                   **viewkwargs):
        """
        Creates a `view_class` view instance.
        """
        if not args:
            args = ()
        if not kwargs:
            kwargs = {}
        if view_class is None:
            view_class = self.view_class

        return view_class(
            request=request, args=args, kwargs=kwargs, **viewkwargs)

    def dispatch_view(self, request, args=None, kwargs=None, view_class=None,
                      **viewkwargs):
        """
        Creates and dispatches `view_class` view.
        """
        view = self.build_view(request, args, kwargs, view_class, **viewkwargs)
        return view.dispatch(request, *view.args, **view.kwargs)


class SetJSONEncoder(DjangoJSONEncoder):
    """
    A custom JSONEncoder extending `DjangoJSONEncoder` to handle serialization
    of `set`.
    """
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super(DjangoJSONEncoder, self).default(obj)



########NEW FILE########
__FILENAME__ = models
from django.db import models


class Article(models.Model):
    author = models.ForeignKey('auth.User', null=True, blank=True)
    title = models.CharField(max_length=30)
    body = models.TextField()
    slug = models.SlugField(blank=True)


class CanonicalArticle(models.Model):
    author = models.ForeignKey('auth.User', null=True, blank=True)
    title = models.CharField(max_length=30)
    body = models.TextField()
    slug = models.SlugField(blank=True)

    def get_canonical_slug(self):
        if self.author:
            return "{0.author.username}-{0.slug}".format(self)
        return "unauthored-{0.slug}".format(self)


########NEW FILE########
__FILENAME__ = settings
DEBUG = False
TEMPLATE_DEBUG = DEBUG

TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-US'
SITE_ID = 1
USE_L10N = True
USE_TZ = True

SECRET_KEY = 'local'

ROOT_URLCONF = 'tests.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages'
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'tests',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

import django
if django.VERSION < (1, 4):
    TEMPLATE_CONTEXT_PROCESSORS.remove('django.core.context_processors.tz')
    MIDDLEWARE_CLASSES.remove(
        'django.middleware.clickjacking.XFrameOptionsMiddleware'
    )

########NEW FILE########
__FILENAME__ = test_access_mixins
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django import test
from django.test.utils import override_settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse_lazy

from .compat import force_text
from .factories import GroupFactory, UserFactory
from .helpers import TestViewHelper
from .views import (PermissionRequiredView, MultiplePermissionsRequiredView,
                    SuperuserRequiredView, StaffuserRequiredView,
                    LoginRequiredView, GroupRequiredView, UserPassesTestView,
                    UserPassesTestNotImplementedView, AnonymousRequiredView)


class _TestAccessBasicsMixin(TestViewHelper):
    """
    A set of basic tests for access mixins.
    """
    view_url = None

    def build_authorized_user(self):
        """
        Returns user authorized to access view.
        """
        raise NotImplementedError

    def build_unauthorized_user(self):
        """
        Returns user not authorized to access view.
        """
        raise NotImplementedError

    def test_success(self):
        """
        If user is authorized then view should return normal response.
        """
        user = self.build_authorized_user()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))

    def test_redirects_to_login(self):
        """
        Browser should be redirected to login page if user is not authorized
        to view this page.
        """
        user = self.build_unauthorized_user()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertRedirects(resp, u'/accounts/login/?next={0}'.format(
            self.view_url))

    def test_raise_permission_denied(self):
        """
        PermissionDenied should be raised if user is not authorized and
        raise_exception attribute is set to True.
        """
        user = self.build_unauthorized_user()
        req = self.build_request(user=user, path=self.view_url)

        with self.assertRaises(PermissionDenied):
            self.dispatch_view(req, raise_exception=True)

    def test_custom_login_url(self):
        """
        Login url should be customizable.
        """
        user = self.build_unauthorized_user()
        req = self.build_request(user=user, path=self.view_url)
        resp = self.dispatch_view(req, login_url='/login/')
        self.assertEqual(
            u'/login/?next={0}'.format(self.view_url),
            resp['Location'])

        # Test with reverse_lazy
        resp = self.dispatch_view(req, login_url=reverse_lazy('headline'))
        self.assertEqual(u'/headline/?next={0}'.format(
            self.view_url), resp['Location'])

    def test_custom_redirect_field_name(self):
        """
        Redirect field name should be customizable.
        """
        user = self.build_unauthorized_user()
        req = self.build_request(user=user, path=self.view_url)
        resp = self.dispatch_view(req, redirect_field_name='foo')
        expected_url = u'/accounts/login/?foo={0}'.format(self.view_url)
        self.assertEqual(expected_url, resp['Location'])

    @override_settings(LOGIN_URL=None)
    def test_get_login_url_raises_exception(self):
        """
        Test that get_login_url from AccessMixin raises
        ImproperlyConfigured.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(
                self.build_request(path=self.view_url), login_url=None)

    def test_get_redirect_field_name_raises_exception(self):
        """
        Test that get_redirect_field_name from AccessMixin raises
        ImproperlyConfigured.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(
                self.build_request(path=self.view_url),
                redirect_field_name=None)

    @override_settings(LOGIN_URL="/auth/login/")
    def test_overridden_login_url(self):
        """
        Test that login_url is not set in stone on module load but can be
        overridden dynamically.
        """
        user = self.build_unauthorized_user()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertRedirects(resp, u'/auth/login/?next={0}'.format(
            self.view_url))


class TestLoginRequiredMixin(TestViewHelper, test.TestCase):
    """
    Tests for LoginRequiredMixin.
    """
    view_class = LoginRequiredView
    view_url = '/login_required/'

    def test_anonymous(self):
        resp = self.client.get(self.view_url)
        self.assertRedirects(resp, '/accounts/login/?next=/login_required/')

    def test_anonymous_raises_exception(self):
        with self.assertRaises(PermissionDenied):
            self.dispatch_view(
                self.build_request(path=self.view_url), raise_exception=True)

    def test_authenticated(self):
        user = UserFactory()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        assert resp.status_code == 200
        assert force_text(resp.content) == 'OK'

    def test_anonymous_redirects(self):
        resp = self.dispatch_view(
                self.build_request(path=self.view_url),
                raise_exception=True,
                redirect_unauthenticated_users=True)
        assert resp.status_code == 302
        assert resp['Location'] == '/accounts/login/?next=/login_required/'


class TestAnonymousRequiredMixin(TestViewHelper, test.TestCase):
    """
    Tests for AnonymousRequiredMixin.
    """
    view_class = AnonymousRequiredView
    view_url = '/unauthenticated_view/'

    def test_anonymous(self):
        """
        As a non-authenticated user, it should be possible to access
        the URL.
        """
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))

        # Test with reverse_lazy
        resp = self.dispatch_view(
            self.build_request(),
            login_url=reverse_lazy(self.view_url))
        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))

    def test_authenticated(self):
        """
        Check that the authenticated user has been successfully directed
        to the approparite view.
        """
        user = UserFactory()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertEqual(302, resp.status_code)

        resp = self.client.get(self.view_url, follow=True)
        self.assertRedirects(resp, '/authenticated_view/')

    def test_no_url(self):
        self.view_class.authenticated_redirect_url = None
        user = UserFactory()
        self.client.login(username=user.username, password='asdf1234')
        with self.assertRaises(ImproperlyConfigured):
            self.client.get(self.view_url)

    def test_bad_url(self):
        self.view_class.authenticated_redirect_url = '/epicfailurl/'
        user = UserFactory()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url, follow=True)
        self.assertEqual(404, resp.status_code)


class TestPermissionRequiredMixin(_TestAccessBasicsMixin, test.TestCase):
    """
    Tests for PermissionRequiredMixin.
    """
    view_class = PermissionRequiredView
    view_url = '/permission_required/'

    def build_authorized_user(self):
        return UserFactory(permissions=['auth.add_user'])

    def build_unauthorized_user(self):
        return UserFactory()

    def test_invalid_permission(self):
        """
        ImproperlyConfigured exception should be raised in two situations:
        if permission is None or if permission has invalid name.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(self.build_request(), permission_required=None)


class TestMultiplePermissionsRequiredMixin(
        _TestAccessBasicsMixin, test.TestCase):
    view_class = MultiplePermissionsRequiredView
    view_url = '/multiple_permissions_required/'

    def build_authorized_user(self):
        return UserFactory(permissions=[
            'tests.add_article', 'tests.change_article', 'auth.change_user'])

    def build_unauthorized_user(self):
        return UserFactory(permissions=['tests.add_article'])

    def test_redirects_to_login(self):
        """
        User should be redirected to login page if he or she does not have
        sufficient permissions.
        """
        url = '/multiple_permissions_required/'
        test_cases = (
            # missing one permission from 'any'
            ['tests.add_article', 'tests.change_article'],
            # missing one permission from 'all'
            ['tests.add_article', 'auth.add_user'],
            # no permissions at all
            [],
        )

        for permissions in test_cases:
            user = UserFactory(permissions=permissions)
            self.client.login(username=user.username, password='asdf1234')
            resp = self.client.get(url)
            self.assertRedirects(resp, u'/accounts/login/?next={0}'.format(
                url))

    def test_invalid_permissions(self):
        """
        ImproperlyConfigured exception should be raised if permissions
        attribute is set incorrectly.
        """
        permissions = (
            None,  # permissions must be set
            (),  # and they must be a dict
            {},  # at least one of 'all', 'any' keys must be present
            {'all': None},  # both all and any must be list or a tuple
            {'all': {'a': 1}},
            {'any': None},
            {'any': {'a': 1}},
        )

        for attr in permissions:
            with self.assertRaises(ImproperlyConfigured):
                self.dispatch_view(self.build_request(), permissions=attr)

    def test_raise_permission_denied(self):
        """
        PermissionDenied should be raised if user does not have sufficient
        permissions and raise_exception is set to True.
        """
        test_cases = (
            # missing one permission from 'any'
            ['tests.add_article', 'tests.change_article'],
            # missing one permission from 'all'
            ['tests.add_article', 'auth.add_user'],
            # no permissions at all
            [],
        )

        for permissions in test_cases:
            user = UserFactory(permissions=permissions)
            req = self.build_request(user=user)
            with self.assertRaises(PermissionDenied):
                self.dispatch_view(req, raise_exception=True)

    def test_all_permissions_key(self):
        """
        Tests if everything works if only 'all' permissions has been set.
        """
        permissions = {'all': ['auth.add_user', 'tests.add_article']}
        user = UserFactory(permissions=permissions['all'])
        req = self.build_request(user=user)

        resp = self.dispatch_view(req, permissions=permissions)
        self.assertEqual('OK', force_text(resp.content))

        user = UserFactory(permissions=['auth.add_user'])
        with self.assertRaises(PermissionDenied):
            self.dispatch_view(
                self.build_request(user=user), raise_exception=True,
                permissions=permissions)

    def test_any_permissions_key(self):
        """
        Tests if everything works if only 'any' permissions has been set.
        """
        permissions = {'any': ['auth.add_user', 'tests.add_article']}
        user = UserFactory(permissions=['tests.add_article'])
        req = self.build_request(user=user)

        resp = self.dispatch_view(req, permissions=permissions)
        self.assertEqual('OK', force_text(resp.content))

        user = UserFactory(permissions=[])
        with self.assertRaises(PermissionDenied):
            self.dispatch_view(
                self.build_request(user=user), raise_exception=True,
                permissions=permissions)


class TestSuperuserRequiredMixin(_TestAccessBasicsMixin, test.TestCase):
    view_class = SuperuserRequiredView
    view_url = '/superuser_required/'

    def build_authorized_user(self):
        return UserFactory(is_superuser=True, is_staff=True)

    def build_unauthorized_user(self):
        return UserFactory()


class TestStaffuserRequiredMixin(_TestAccessBasicsMixin, test.TestCase):
    view_class = StaffuserRequiredView
    view_url = '/staffuser_required/'

    def build_authorized_user(self):
        return UserFactory(is_staff=True)

    def build_unauthorized_user(self):
        return UserFactory()


class TestGroupRequiredMixin(_TestAccessBasicsMixin, test.TestCase):
    view_class = GroupRequiredView
    view_url = '/group_required/'

    def build_authorized_user(self):
        user = UserFactory()
        group = GroupFactory(name='test_group')
        user.groups.add(group)
        return user

    def build_superuser(self):
        user = UserFactory()
        user.is_superuser = True
        user.save()
        return user

    def build_unauthorized_user(self):
        return UserFactory()

    def test_with_string(self):
        self.assertEqual('test_group', self.view_class.group_required)
        user = self.build_authorized_user()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))

    def test_with_group_list(self):
        group_list = ['test_group', 'editors']
        # the test client will instantiate a new view on request, so we have to
        # modify the class variable (and restore it when the test finished)
        self.view_class.group_required = group_list
        self.assertEqual(group_list, self.view_class.group_required)
        user = self.build_authorized_user()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))
        self.view_class.group_required = 'test_group'
        self.assertEqual('test_group', self.view_class.group_required)

    def test_superuser_allowed(self):
        user = self.build_superuser()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))

    def test_improperly_configured(self):
        view = self.view_class()
        view.group_required = None
        with self.assertRaises(ImproperlyConfigured):
            view.get_group_required()

        view.group_required = {'foo': 'bar'}
        with self.assertRaises(ImproperlyConfigured):
            view.get_group_required()

    def test_with_unicode(self):
        self.view_class.group_required = u'niño'
        self.assertEqual(u'niño', self.view_class.group_required)

        user = self.build_authorized_user()
        group = user.groups.all()[0]
        group.name = u'niño'
        group.save()
        self.assertEqual(u'niño', user.groups.all()[0].name)

        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))
        self.view_class.group_required = 'test_group'
        self.assertEqual('test_group', self.view_class.group_required)


class TestUserPassesTestMixin(_TestAccessBasicsMixin, test.TestCase):
    view_class = UserPassesTestView
    view_url = '/user_passes_test/'
    view_not_implemented_class = UserPassesTestNotImplementedView
    view_not_implemented_url = '/user_passes_test_not_implemented/'

    # for testing with passing and not passsing func_test
    def build_authorized_user(self, is_superuser=False):
        return UserFactory(is_superuser=is_superuser, is_staff=True,
                           email="user@mydomain.com")

    def build_unauthorized_user(self):
        return UserFactory()

    def test_with_user_pass(self):
        user = self.build_authorized_user()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)

        self.assertEqual(200, resp.status_code)
        self.assertEqual('OK', force_text(resp.content))

    def test_with_user_not_pass(self):
        user = self.build_authorized_user(is_superuser=True)
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get(self.view_url)

        self.assertRedirects(resp, '/accounts/login/?next=/user_passes_test/')

    def test_with_user_raise_exception(self):
        with self.assertRaises(PermissionDenied):
            self.dispatch_view(
                self.build_request(path=self.view_url), raise_exception=True)

    def test_not_implemented(self):
        view = self.view_not_implemented_class()
        with self.assertRaises(NotImplementedError):
            view.dispatch(
                self.build_request(path=self.view_not_implemented_url),
                raise_exception=True)

########NEW FILE########
__FILENAME__ = test_ajax_mixins
from __future__ import absolute_import

import mock

from django import test
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse

from braces.views import AjaxResponseMixin

from .compat import force_text
from .factories import ArticleFactory, UserFactory
from .helpers import TestViewHelper
from .views import (SimpleJsonView, JsonRequestResponseView,
                    CustomJsonEncoderView)
from .compat import json


class TestAjaxResponseMixin(TestViewHelper, test.TestCase):
    """
    Tests for AjaxResponseMixin.
    """
    methods = [u'get', u'post', u'put', u'delete']

    def test_xhr(self):
        """
        Checks if ajax_* method has been called for every http method.
        """
        # AjaxResponseView returns 'AJAX_OK' when requested with XmlHttpRequest
        for m in self.methods:
            fn = getattr(self.client, m)
            resp = fn(u'/ajax_response/',
                      HTTP_X_REQUESTED_WITH=u'XMLHttpRequest')
            assert force_text(resp.content) == u'AJAX_OK'

    def test_not_xhr(self):
        """
        Normal methods (get, post, etc) should be used when handling non-ajax
        requests.
        """
        for m in self.methods:
            fn = getattr(self.client, m)
            resp = fn(u'/ajax_response/')
            assert force_text(resp.content) == u'OK'

    def test_fallback_to_normal_methods(self):
        """
        Ajax methods should fallback to normal methods by default.
        """
        test_cases = [
            (u'get', u'get'),
            (u'post', u'post'),
            (u'put', u'get'),
            (u'delete', u'get'),
        ]

        for ajax_method, fallback in test_cases:
            m, mixin = mock.Mock(), AjaxResponseMixin()
            m.return_value = HttpResponse()
            req = self.build_request()
            setattr(mixin, fallback, m)
            fn = getattr(mixin, u"{0}_ajax".format(ajax_method))
            ret = fn(req, 1, 2, meth=ajax_method)
            # check if appropriate method has been called
            m.assert_called_once_with(req, 1, 2, meth=ajax_method)
            # check if appropriate value has been returned
            self.assertIs(m.return_value, ret)


class TestJSONResponseMixin(TestViewHelper, test.TestCase):
    """
    Tests for JSONResponseMixin.
    """
    view_class = SimpleJsonView

    def assert_json_response(self, resp, status_code=200):
        self.assertEqual(status_code, resp.status_code)
        self.assertEqual(u'application/json',
                         resp[u'content-type'].split(u';')[0])

    def get_content(self, url):
        """
        GET url and return content
        """
        resp = self.client.get(url)
        self.assert_json_response(resp)
        content = force_text(resp.content)
        return content

    def test_simple_json(self):
        """
        Tests render_json_response() method.
        """
        user = UserFactory()
        self.client.login(username=user.username, password=u'asdf1234')
        data = json.loads(self.get_content(u'/simple_json/'))
        self.assertEqual({u'username': user.username}, data)

    def test_serialization(self):
        """
        Tests render_json_object_response() method which serializes objects
        using django's serializer framework.
        """
        a1, a2 = [ArticleFactory() for __ in range(2)]
        data = json.loads(self.get_content(u'/article_list_json/'))
        self.assertIsInstance(data, list)
        self.assertEqual(2, len(data))
        titles = []
        for row in data:
            # only title has been serialized
            self.assertEqual(1, len(row[u'fields']))
            titles.append(row[u'fields'][u'title'])

        self.assertIn(a1.title, titles)
        self.assertIn(a2.title, titles)

    def test_bad_content_type(self):
        """
        ImproperlyConfigured exception should be raised if content_type
        attribute is not set correctly.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(self.build_request(), content_type=['a'])

    def test_pretty_json(self):
        """
        Success if JSON responses are the same, and the well-indented response
        is longer than the normal one.
        """
        user = UserFactory()
        self.client.login(username=user.username, password=u'asfa')
        normal_content = self.get_content(u'/simple_json/')
        self.view_class.json_dumps_kwargs = {u'indent': 2}
        pretty_content = self.get_content(u'/simple_json/')
        normal_json = json.loads(u'{0}'.format(normal_content))
        pretty_json = json.loads(u'{0}'.format(pretty_content))
        self.assertEqual(normal_json, pretty_json)
        self.assertTrue(len(pretty_content) > len(normal_content))

    def test_json_encoder_class_atrribute(self):
        """
        Tests setting custom `json_encoder_class` attribute.
        """
        data = json.loads(self.get_content(u'/simple_json_custom_encoder/'))
        self.assertEqual({u'numbers': [1, 2, 3]}, data)


class TestJsonRequestResponseMixin(TestViewHelper, test.TestCase):
    view_class = JsonRequestResponseView
    request_dict = {u'status': u'operational'}

    def test_get_request_json_properly_formatted(self):
        """
        Properly formatted JSON requests should result in a JSON object
        """
        data = json.dumps(self.request_dict).encode(u'utf-8')
        response = self.client.post(
            u'/json_request/',
            content_type=u'application/json',
            data=data
        )
        response_json = json.loads(response.content.decode(u'utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json, self.request_dict)

    def test_get_request_json_improperly_formatted(self):
        """
        Improperly formatted JSON requests should make request_json == None
        """
        response = self.client.post(
            u'/json_request/',
            data=self.request_dict
        )
        response_json = json.loads(response.content.decode(u'utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json, None)

    def test_bad_request_response(self):
        """
        If a view calls render_bad_request_response when request_json is empty
        or None, the client should get a 400 error
        """
        response = self.client.post(
            u'/json_bad_request/',
            data=self.request_dict
        )
        response_json = json.loads(response.content.decode(u'utf-8'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json, self.view_class.error_response_dict)

    def test_bad_request_response_with_custom_error_message(self):
        """
        If a view calls render_bad_request_response when request_json is empty
        or None, the client should get a 400 error
        """
        response = self.client.post(
            u'/json_custom_bad_request/',
            data=self.request_dict
        )
        response_json = json.loads(response.content.decode(u'utf-8'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json, {u'error': u'you messed up'})

########NEW FILE########
__FILENAME__ = test_forms
from __future__ import absolute_import

from django import test
from django.contrib.auth.models import User

from . import forms


class TestUserKwargModelFormMixin(test.TestCase):
    """
    Tests for UserKwargModelFormMixin.
    """
    def test_without_user_kwarg(self):
        """
        It should be possible to create form without 'user' kwarg.

        In that case 'user' attribute should be set to None.
        """
        form = forms.FormWithUserKwarg()
        assert form.user is None

    def test_with_user_kwarg(self):
        """
        Form's 'user' attribute should be set to value passed as 'user'
        argument.
        """
        user = User(username='test')
        form = forms.FormWithUserKwarg(user=user)
        assert form.user is user

########NEW FILE########
__FILENAME__ = test_other_mixins
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import mock
import pytest

import django
from django.contrib import messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.base import Message
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django import test
from django.test.utils import override_settings
from django.views.generic import View

from braces.views import (SetHeadlineMixin, MessageMixin, _MessageAPIWrapper,
                          FormValidMessageMixin, FormInvalidMessageMixin)
from .compat import force_text
from .factories import UserFactory
from .helpers import TestViewHelper
from .models import Article, CanonicalArticle
from .views import (ArticleListView, AuthorDetailView, OrderableListView,
                    FormMessagesView, ContextView)


class TestSuccessURLRedirectListMixin(test.TestCase):
    """
    Tests for SuccessURLRedirectListMixin.
    """
    def test_redirect(self):
        """
        Test if browser is redirected to list view.
        """
        data = {'title': "Test body", 'body': "Test body"}
        resp = self.client.post('/article_list/create/', data)
        self.assertRedirects(resp, '/article_list/')

    def test_no_url_name(self):
        """
        Test that ImproperlyConfigured is raised.
        """
        data = {'title': "Test body", 'body': "Test body"}
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/article_list_bad/create/', data)


class TestUserFormKwargsMixin(test.TestCase):
    """
    Tests for UserFormKwargsMixin.
    """
    def test_post_method(self):
        user = UserFactory()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.post('/form_with_user_kwarg/', {'field1': 'foo'})
        assert force_text(resp.content) == "username: %s" % user.username

    def test_get_method(self):
        user = UserFactory()
        self.client.login(username=user.username, password='asdf1234')
        resp = self.client.get('/form_with_user_kwarg/')
        assert resp.context['form'].user == user


class TestSetHeadlineMixin(test.TestCase):
    """
    Tests for SetHeadlineMixin.
    """
    def test_dynamic_headline(self):
        """
        Tests if get_headline() is called properly.
        """
        resp = self.client.get('/headline/test-headline/')
        self.assertEqual('test-headline', resp.context['headline'])

    def test_context_data(self):
        """
        Tests if mixin adds proper headline to template context.
        """
        resp = self.client.get('/headline/foo-bar/')
        self.assertEqual("foo-bar", resp.context['headline'])

    def test_get_headline(self):
        """
        Tests if get_headline() method works correctly.
        """
        mixin = SetHeadlineMixin()
        with self.assertRaises(ImproperlyConfigured):
            mixin.get_headline()

        mixin.headline = "Test headline"
        self.assertEqual("Test headline", mixin.get_headline())

    def test_get_headline_lazy(self):
        resp = self.client.get('/headline/lazy/')
        self.assertEqual('Test Headline', resp.context['headline'])


class TestStaticContextMixin(test.TestCase):
    """ Tests for StaticContextMixin. """
    view_class = ContextView
    view_url = '/context/'

    def test_dict(self):
        self.view_class.static_context = {'test': True}
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(True, resp.context['test'])

    def test_two_tuple(self):
        self.view_class.static_context = [('a', 1), ('b', 2)]
        resp = self.client.get(self.view_url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, resp.context['a'])
        self.assertEqual(2, resp.context['b'])

    def test_not_set(self):
        self.view_class.static_context = None
        with self.assertRaises(ImproperlyConfigured):
            self.client.get(self.view_url)

    def test_string_value_error(self):
        self.view_class.static_context = 'Fail'
        with self.assertRaises(ImproperlyConfigured):
            self.client.get(self.view_url)

    def test_list_error(self):
        self.view_class.static_context = ['fail', 'fail']
        with self.assertRaises(ImproperlyConfigured):
            self.client.get(self.view_url)


class TestCsrfExemptMixin(test.TestCase):
    """
    Tests for TestCsrfExemptMixin.
    """
    def setUp(self):
        super(TestCsrfExemptMixin, self).setUp()
        self.client = self.client_class(enforce_csrf_checks=True)

    def test_csrf_token_is_not_required(self):
        """
        Tests if csrf token is not required.
        """
        resp = self.client.post('/csrf_exempt/', {'field1': 'test'})
        self.assertEqual(200, resp.status_code)
        self.assertEqual("OK", force_text(resp.content))


class TestSelectRelatedMixin(TestViewHelper, test.TestCase):
    view_class = ArticleListView

    def test_missing_select_related(self):
        """
        ImproperlyConfigured exception should be raised if select_related
        attribute is missing.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(self.build_request(), select_related=None)

    def test_invalid_select_related(self):
        """
        ImproperlyConfigured exception should be raised if select_related is
        not a tuple or a list.
        :return:
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(self.build_request(), select_related={'a': 1})

    @mock.patch('django.db.models.query.QuerySet.select_related')
    def test_select_related_called(self, m):
        """
        Checks if QuerySet's select_related() was called with correct
        arguments.
        """
        qs = Article.objects.all()
        m.return_value = qs.select_related('author')
        qs.select_related = m
        m.reset_mock()

        resp = self.dispatch_view(self.build_request())
        self.assertEqual(200, resp.status_code)
        m.assert_called_once_with('author')


class TestPrefetchRelatedMixin(TestViewHelper, test.TestCase):
    view_class = AuthorDetailView

    def test_missing_prefetch_related(self):
        """
        ImproperlyConfigured exception should be raised if
        prefetch_related attribute is missing.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(self.build_request(), prefetch_related=None)

    def test_invalid_prefetch_related(self):
        """
        ImproperlyConfigured exception should be raised if
        prefetch_related is not a tuple or a list.
        :return:
        """
        with self.assertRaises(ImproperlyConfigured):
            self.dispatch_view(self.build_request(), prefetch_related={'a': 1})

    @mock.patch('django.db.models.query.QuerySet.prefetch_related')
    def test_prefetch_related_called(self, m):
        """
        Checks if QuerySet's prefetch_related() was called with correct
        arguments.
        """
        qs = Article.objects.all()
        m.return_value = qs.prefetch_related('article_set')
        qs.prefetch_related = m
        m.reset_mock()

        resp = self.dispatch_view(self.build_request())
        self.assertEqual(200, resp.status_code)
        m.assert_called_once_with('article_set')


class TestOrderableListMixin(TestViewHelper, test.TestCase):
    view_class = OrderableListView

    def __make_test_articles(self):
        a1 = Article.objects.create(title='Alpha', body='Zet')
        a2 = Article.objects.create(title='Zet', body='Alpha')
        return a1, a2

    def test_correct_order(self):
        """
        Objects must be properly ordered if requested with valid column names
        """
        a1, a2 = self.__make_test_articles()

        resp = self.dispatch_view(
            self.build_request(path='?order_by=title&ordering=asc'),
            orderable_columns=None,
            get_orderable_columns=lambda: ('id', 'title', ))
        self.assertEqual(list(resp.context_data['object_list']), [a1, a2])

        resp = self.dispatch_view(
            self.build_request(path='?order_by=id&ordering=desc'),
            orderable_columns=None,
            get_orderable_columns=lambda: ('id', 'title', ))
        self.assertEqual(list(resp.context_data['object_list']), [a2, a1])

    def test_default_column(self):
        """
        When no ordering specified in GET, use
        View.get_orderable_columns_default()
        """
        a1, a2 = self.__make_test_articles()

        resp = self.dispatch_view(self.build_request())
        self.assertEqual(list(resp.context_data['object_list']), [a1, a2])

    def test_get_orderable_columns_returns_correct_values(self):
        """
        OrderableListMixin.get_orderable_columns() should return
        View.orderable_columns attribute by default or raise
        ImproperlyConfigured exception in the attribute is None
        """
        view = self.view_class()
        self.assertEqual(view.get_orderable_columns(), view.orderable_columns)
        view.orderable_columns = None
        self.assertRaises(ImproperlyConfigured,
                          lambda: view.get_orderable_columns())

    def test_get_orderable_columns_default_returns_correct_values(self):
        """
        OrderableListMixin.get_orderable_columns_default() should return
        View.orderable_columns_default attribute by default or raise
        ImproperlyConfigured exception in the attribute is None
        """
        view = self.view_class()
        self.assertEqual(view.get_orderable_columns_default(),
                         view.orderable_columns_default)
        view.orderable_columns_default = None
        self.assertRaises(ImproperlyConfigured,
                          lambda: view.get_orderable_columns_default())

    def test_only_allowed_columns(self):
        """
        If column is not in Model.Orderable.columns iterable, the objects
        should be ordered by default column.
        """
        a1, a2 = self.__make_test_articles()

        resp = self.dispatch_view(
            self.build_request(path='?order_by=body&ordering=asc'),
            orderable_columns_default=None,
            get_orderable_columns_default=lambda: 'title')
        self.assertEqual(list(resp.context_data['object_list']), [a1, a2])


class TestCanonicalSlugDetailView(test.TestCase):
    def setUp(self):
        Article.objects.create(title='Alpha', body='Zet', slug='alpha')
        Article.objects.create(title='Zet', body='Alpha', slug='zet')

    def test_canonical_slug(self):
        """
        Test that no redirect occurs when slug is canonical.
        """
        resp = self.client.get('/article-canonical/1-alpha/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/article-canonical/2-zet/')
        self.assertEqual(resp.status_code, 200)

    def test_non_canonical_slug(self):
        """
        Test that a redirect occurs when the slug is non-canonical.
        """
        resp = self.client.get('/article-canonical/1-bad-slug/')
        self.assertEqual(resp.status_code, 301)
        resp = self.client.get('/article-canonical/2-bad-slug/')
        self.assertEqual(resp.status_code, 301)


class TestNamespaceAwareCanonicalSlugDetailView(test.TestCase):
    def setUp(self):
        Article.objects.create(title='Alpha', body='Zet', slug='alpha')
        Article.objects.create(title='Zet', body='Alpha', slug='zet')

    def test_canonical_slug(self):
        """
        Test that no redirect occurs when slug is canonical.
        """
        resp = self.client.get(
            '/article-canonical-namespaced/article/1-alpha/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(
            '/article-canonical-namespaced/article/2-zet/')
        self.assertEqual(resp.status_code, 200)

    def test_non_canonical_slug(self):
        """
        Test that a redirect occurs when the slug is non-canonical and that the
        redirect is namespace aware.
        """
        resp = self.client.get(
            '/article-canonical-namespaced/article/1-bad-slug/')
        self.assertEqual(resp.status_code, 301)
        resp = self.client.get(
            '/article-canonical-namespaced/article/2-bad-slug/')
        self.assertEqual(resp.status_code, 301)


class TestOverriddenCanonicalSlugDetailView(test.TestCase):
    def setUp(self):
        Article.objects.create(title='Alpha', body='Zet', slug='alpha')
        Article.objects.create(title='Zet', body='Alpha', slug='zet')

    def test_canonical_slug(self):
        """
        Test that no redirect occurs when slug is canonical according to the
        overridden canonical slug.
        """
        resp = self.client.get('/article-canonical-override/1-nycun/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/article-canonical-override/2-mrg/')
        self.assertEqual(resp.status_code, 200)

    def test_non_canonical_slug(self):
        """
        Test that a redirect occurs when the slug is non-canonical.
        """
        resp = self.client.get('/article-canonical-override/1-bad-slug/')
        self.assertEqual(resp.status_code, 301)
        resp = self.client.get('/article-canonical-override/2-bad-slug/')
        self.assertEqual(resp.status_code, 301)


class TestCustomUrlKwargsCanonicalSlugDetailView(test.TestCase):
    def setUp(self):
        Article.objects.create(title='Alpha', body='Zet', slug='alpha')
        Article.objects.create(title='Zet', body='Alpha', slug='zet')

    def test_canonical_slug(self):
        """
        Test that no redirect occurs when slug is canonical
        """
        resp = self.client.get('/article-canonical-custom-kwargs/1-alpha/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/article-canonical-custom-kwargs/2-zet/')
        self.assertEqual(resp.status_code, 200)

    def test_non_canonical_slug(self):
        """
        Test that a redirect occurs when the slug is non-canonical.
        """
        resp = self.client.get('/article-canonical-custom-kwargs/1-bad-slug/')
        self.assertEqual(resp.status_code, 301)
        resp = self.client.get('/article-canonical-custom-kwargs/2-bad-slug/')
        self.assertEqual(resp.status_code, 301)


class TestModelCanonicalSlugDetailView(test.TestCase):
    def setUp(self):
        CanonicalArticle.objects.create(
            title='Alpha', body='Zet', slug='alpha')
        CanonicalArticle.objects.create(
            title='Zet', body='Alpha', slug='zet')

    def test_canonical_slug(self):
        """
        Test that no redirect occurs when slug is canonical according to the
        model's canonical slug.
        """
        resp = self.client.get('/article-canonical-model/1-unauthored-alpha/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/article-canonical-model/2-unauthored-zet/')
        self.assertEqual(resp.status_code, 200)

    def test_non_canonical_slug(self):
        """
        Test that a redirect occurs when the slug is non-canonical.
        """
        resp = self.client.get('/article-canonical-model/1-bad-slug/')
        self.assertEqual(resp.status_code, 301)
        resp = self.client.get('/article-canonical-model/2-bad-slug/')
        self.assertEqual(resp.status_code, 301)


# CookieStorage is used because it doesn't require middleware to be installed
@override_settings(
    MESSAGE_STORAGE='django.contrib.messages.storage.cookie.CookieStorage')
class MessageMixinTests(test.TestCase):
    def setUp(self):
        self.rf = test.RequestFactory()
        self.middleware = MessageMiddleware()

    def get_request(self, *args, **kwargs):
        request = self.rf.get('/')
        self.middleware.process_request(request)
        return request

    def get_response(self, request, view):
        response = view(request)
        self.middleware.process_response(request, response)
        return response

    def get_request_response(self, view, *args, **kwargs):
        request = self.get_request(*args, **kwargs)
        response = self.get_response(request, view)
        return request, response

    def test_add_messages(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.add_message(messages.SUCCESS, 'test')
                return HttpResponse('OK')

        request, response = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0].message, 'test')
        self.assertEqual(msg[0].level, messages.SUCCESS)

    def test_get_messages(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.add_message(messages.SUCCESS, 'success')
                self.messages.add_message(messages.WARNING, 'warning')
                content = ','.join(
                    m.message for m in self.messages.get_messages())
                return HttpResponse(content)

        _, response = self.get_request_response(TestView.as_view())
        self.assertEqual(response.content, b"success,warning")

    def test_get_level(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                return HttpResponse(self.messages.get_level())

        _, response = self.get_request_response(TestView.as_view())
        self.assertEqual(int(response.content), messages.INFO)  # default

    def test_set_level(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.set_level(messages.WARNING)
                self.messages.add_message(messages.SUCCESS, 'success')
                self.messages.add_message(messages.WARNING, 'warning')
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(msg, [Message(messages.WARNING, 'warning')])

    @override_settings(MESSAGE_LEVEL=messages.DEBUG)
    def test_debug(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.debug("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.DEBUG, 'test'))

    def test_info(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.info("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.INFO, 'test'))

    def test_success(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.success("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.SUCCESS, 'test'))

    def test_warning(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.warning("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.WARNING, 'test'))

    def test_error(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.error("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.ERROR, 'test'))

    def test_invalid_attribute(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.invalid()
                return HttpResponse('OK')

        with self.assertRaises(AttributeError):
            self.get_request_response(TestView.as_view())

    @pytest.mark.skipif(
        django.VERSION < (1, 5),
        reason='Some features of MessageMixin are only available in '
               'Django >= 1.5')
    def test_wrapper_available_in_dispatch(self):
        """
        Make sure that self.messages is available in dispatch() even before
        calling the parent's implementation.
        """
        class TestView(MessageMixin, View):
            def dispatch(self, request):
                self.messages.add_message(messages.SUCCESS, 'test')
                return super(TestView, self).dispatch(request)

            def get(self, request):
                return HttpResponse('OK')

        request, response = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0].message, 'test')
        self.assertEqual(msg[0].level, messages.SUCCESS)

    def test_API(self):
        """
        Make sure that our assumptions about messages.api are still valid.
        """
        # This test is designed to break when django.contrib.messages.api
        # changes (items being added or removed).
        excluded_API = set()
        if django.VERSION >= (1, 7):
            excluded_API.add('MessageFailure')
        self.assertEqual(
            _MessageAPIWrapper.API | excluded_API,
            set(messages.api.__all__)
        )


class TestFormMessageMixins(test.TestCase):
    def setUp(self):
        self.good_data = {
            'title': 'Good',
            'body': 'Body'
        }
        self.bad_data = {
            'body': 'Missing title'
        }

    def test_valid_message(self):
        url = '/form_messages/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, self.good_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, FormMessagesView().form_valid_message)

    def test_invalid_message(self):
        url = '/form_messages/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, self.bad_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, FormMessagesView().form_invalid_message)

    def test_form_valid_message_not_set(self):
        mixin = FormValidMessageMixin()
        with self.assertRaises(ImproperlyConfigured):
            mixin.get_form_valid_message()

    def test_form_valid_message_not_str(self):
        mixin = FormValidMessageMixin()
        mixin.form_valid_message = ['bad']
        with self.assertRaises(ImproperlyConfigured):
            mixin.get_form_valid_message()

    def test_form_valid_returns_message(self):
        mixin = FormValidMessageMixin()
        mixin.form_valid_message = u'Good øø'
        self.assertEqual(u'Good øø', mixin.get_form_valid_message())

    def test_form_invalid_message_not_set(self):
        mixin = FormInvalidMessageMixin()
        with self.assertRaises(ImproperlyConfigured):
            mixin.get_form_invalid_message()

    def test_form_invalid_message_not_str(self):
        mixin = FormInvalidMessageMixin()
        mixin.form_invalid_message = ['bad']
        with self.assertRaises(ImproperlyConfigured):
            mixin.get_form_invalid_message()

    def test_form_invalid_returns_message(self):
        mixin = FormInvalidMessageMixin()
        mixin.form_invalid_message = u'Bad øø'
        self.assertEqual(u'Bad øø', mixin.get_form_invalid_message())


class TestAllVerbsMixin(test.TestCase):
    def setUp(self):
        self.url = "/all_verbs/"
        self.no_handler_url = "/all_verbs_no_handler/"

    def test_options(self):
        response = self.client.options(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_head(self):
        response = self.client.head(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

    def test_put(self):
        response = self.client.put(self.url)
        self.assertEqual(response.status_code, 200)

    def test_delete(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 200)

    def test_no_all_handler(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.get('/all_verbs_no_handler/')

########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import

from . import views
from .compat import patterns, include, url


urlpatterns = patterns(
    '',
    # LoginRequiredMixin tests
    url(r'^login_required/$', views.LoginRequiredView.as_view()),

    # AnonymousRequiredView tests
    url(r'^unauthenticated_view/$', views.AnonymousRequiredView.as_view(),
        name='unauthenticated_view'),
    url(r'^authenticated_view/$', views.AuthenticatedView.as_view(),
        name='authenticated_view'),

    # AjaxResponseMixin tests
    url(r'^ajax_response/$', views.AjaxResponseView.as_view()),

    # CreateAndRedirectToEditView tests
    url(r'^article/create/$', views.CreateArticleView.as_view()),
    url(r'^article/(?P<pk>\d+)/edit/$', views.EditArticleView.as_view(),
        name="edit_article"),

    url(r'^article_list/create/$',
        views.CreateArticleAndRedirectToListView.as_view()),
    url(r'^article_list_bad/create/$',
        views.CreateArticleAndRedirectToListViewBad.as_view()),
    url(r'^article_list/$', views.ArticleListView.as_view(),
        name='article_list'),

    # CanonicalSlugDetailMixin tests
    url(r'^article-canonical/(?P<pk>\d+)-(?P<slug>[-\w]+)/$',
        views.CanonicalSlugDetailView.as_view()),
    url(r'^article-canonical-namespaced/',
        include('tests.urls_namespaced', namespace='some_namespace')),
    url(r'^article-canonical-override/(?P<pk>\d+)-(?P<slug>[-\w]+)/$',
        views.OverriddenCanonicalSlugDetailView.as_view()),
    url(r'^article-canonical-custom-kwargs/(?P<my_pk>\d+)-(?P<my_slug>[-\w]+)/$',
        views.CanonicalSlugDetailCustomUrlKwargsView.as_view()),
    url(r'^article-canonical-model/(?P<pk>\d+)-(?P<slug>[-\w]+)/$',
        views.ModelCanonicalSlugDetailView.as_view()),

    # UserFormKwargsMixin tests
    url(r'^form_with_user_kwarg/$', views.FormWithUserKwargView.as_view()),

    # SetHeadlineMixin tests
    url(r'^headline/$', views.HeadlineView.as_view(), name='headline'),
    url(r'^headline/lazy/$', views.LazyHeadlineView.as_view()),
    url(r'^headline/(?P<s>[\w-]+)/$', views.DynamicHeadlineView.as_view()),

    # ExtraContextMixin tests
    url(r'^context/$', views.ContextView.as_view(), name='context'),

    # PermissionRequiredMixin tests
    url(r'^permission_required/$', views.PermissionRequiredView.as_view()),

    # MultiplePermissionsRequiredMixin tests
    url(r'^multiple_permissions_required/$',
        views.MultiplePermissionsRequiredView.as_view()),

    # SuperuserRequiredMixin tests
    url(r'^superuser_required/$', views.SuperuserRequiredView.as_view()),

    # StaffuserRequiredMixin tests
    url(r'^staffuser_required/$', views.StaffuserRequiredView.as_view()),

    # GroupRequiredMixin tests
    url(r'^group_required/$', views.GroupRequiredView.as_view()),

    # UserPassesTestMixin tests
    url(r'^user_passes_test/$', views.UserPassesTestView.as_view()),

    # UserPassesTestMixin tests
    url(r'^user_passes_test_not_implemented/$', views.UserPassesTestNotImplementedView.as_view()),

    # CsrfExemptMixin tests
    url(r'^csrf_exempt/$', views.CsrfExemptView.as_view()),

    # JSONResponseMixin tests
    url(r'^simple_json/$', views.SimpleJsonView.as_view()),
    url(r'^simple_json_custom_encoder/$', views.CustomJsonEncoderView.as_view()),
    url(r'^simple_json_400/$', views.SimpleJsonBadRequestView.as_view()),
    url(r'^article_list_json/$', views.ArticleListJsonView.as_view()),

    # JsonRequestResponseMixin tests
    url(r'^json_request/$', views.JsonRequestResponseView.as_view()),
    url(r'^json_bad_request/$', views.JsonBadRequestView.as_view()),
    url(r'^json_custom_bad_request/$', views.JsonCustomBadRequestView.as_view()),

    # FormMessagesMixin tests
    url(r'form_messages/$', views.FormMessagesView.as_view()),

    # AllVerbsMixin tests
    url(r'all_verbs/$', views.AllVerbsView.as_view()),
    url(r'all_verbs_no_handler/$', views.AllVerbsView.as_view(all_handler=None)),
)


urlpatterns += patterns(
    'django.contrib.auth.views',
    # login page, required by some tests
    url(r'^accounts/login/$', 'login', {'template_name': 'blank.html'}),
    url(r'^auth/login/$', 'login', {'template_name': 'blank.html'}),
)

########NEW FILE########
__FILENAME__ = urls_namespaced
from __future__ import absolute_import

from . import views
from .compat import patterns, url


urlpatterns = patterns(
    '',
    # CanonicalSlugDetailMixin namespace tests
    url(r'^article/(?P<pk>\d+)-(?P<slug>[\w-]+)/$',
        views.CanonicalSlugDetailView.as_view(),
        name="namespaced_article"),
)

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import

import codecs

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (View, UpdateView, FormView, TemplateView,
                                  ListView, DetailView, CreateView)

from braces import views

from .models import Article, CanonicalArticle
from .forms import ArticleForm, FormWithUserKwarg
from .helpers import SetJSONEncoder


class OkView(View):
    """
    A view which simply returns "OK" for every request.
    """
    def get(self, request):
        return HttpResponse("OK")

    def post(self, request):
        return self.get(request)

    def put(self, request):
        return self.get(request)

    def delete(self, request):
        return self.get(request)


class LoginRequiredView(views.LoginRequiredMixin, OkView):
    """
    A view for testing LoginRequiredMixin.
    """


class AnonymousRequiredView(views.AnonymousRequiredMixin, OkView):
    """
    A view for testing AnonymousRequiredMixin. Should accept
    unauthenticated users and redirect authenticated users to the
    authenticated_redirect_url set on the view.
    """
    authenticated_redirect_url = '/authenticated_view/'


class AuthenticatedView(views.LoginRequiredMixin, OkView):
    """
    A view for testing AnonymousRequiredMixin. Should accept
    authenticated users.
    """


class AjaxResponseView(views.AjaxResponseMixin, OkView):
    """
    A view for testing AjaxResponseMixin.
    """
    def get_ajax(self, request):
        return HttpResponse("AJAX_OK")

    def post_ajax(self, request):
        return self.get_ajax(request)

    def put_ajax(self, request):
        return self.get_ajax(request)

    def delete_ajax(self, request):
        return self.get_ajax(request)


class SimpleJsonView(views.JSONResponseMixin, View):
    """
    A view for testing JSONResponseMixin's render_json_response() method.
    """
    def get(self, request):
        object = {'username': request.user.username}
        return self.render_json_response(object)


class CustomJsonEncoderView(views.JSONResponseMixin, View):
    """
    A view for testing JSONResponseMixin's `json_encoder_class` attribute
    with custom JSONEncoder class.
    """
    json_encoder_class = SetJSONEncoder

    def get(self, request):
        object = {'numbers': set([1, 2, 3])}
        return self.render_json_response(object)


class SimpleJsonBadRequestView(views.JSONResponseMixin, View):
    """
    A view for testing JSONResponseMixin's render_json_response() method with
    400 HTTP status code.
    """
    def get(self, request):
        object = {'username': request.user.username}
        return self.render_json_response(object, status=400)


class ArticleListJsonView(views.JSONResponseMixin, View):
    """
    A view for testing JSONResponseMixin's render_json_object_response()
    method.
    """
    def get(self, request):
        queryset = Article.objects.all()
        return self.render_json_object_response(
            queryset, fields=('title',))


class JsonRequestResponseView(views.JsonRequestResponseMixin, View):
    """
    A view for testing JsonRequestResponseMixin's json conversion
    """
    def post(self, request):
        return self.render_json_response(self.request_json)


class JsonBadRequestView(views.JsonRequestResponseMixin, View):
    """
    A view for testing JsonRequestResponseMixin's require_json
    and render_bad_request_response methods
    """
    require_json = True

    def post(self, request, *args, **kwargs):
        return self.render_json_response(self.request_json)


class JsonCustomBadRequestView(views.JsonRequestResponseMixin, View):
    """
    A view for testing JsonRequestResponseMixin's
    render_bad_request_response method with a custom error message
    """
    def post(self, request, *args, **kwargs):
        if not self.request_json:
            return self.render_bad_request_response(
                {'error': 'you messed up'})
        return self.render_json_response(self.request_json)


class CreateArticleView(CreateView):
    """
    View for testing CreateAndRedirectEditToView.
    """
    model = Article
    template_name = 'form.html'


class EditArticleView(UpdateView):
    """
    View for testing CreateAndRedirectEditToView.
    """
    model = Article
    template_name = 'form.html'


class CreateArticleAndRedirectToListView(views.SuccessURLRedirectListMixin,
                                         CreateArticleView):
    """
    View for testing SuccessURLRedirectListMixin
    """
    success_list_url = 'article_list'


class CreateArticleAndRedirectToListViewBad(views.SuccessURLRedirectListMixin,
                                            CreateArticleView):
    """
    View for testing SuccessURLRedirectListMixin
    """
    success_list_url = None


class ArticleListView(views.SelectRelatedMixin, ListView):
    """
    A list view for articles, required for testing SuccessURLRedirectListMixin.

    Also used to test SelectRelatedMixin.
    """
    model = Article
    template_name = 'blank.html'
    select_related = ('author',)


class FormWithUserKwargView(views.UserFormKwargsMixin, FormView):
    """
    View for testing UserFormKwargsMixin.
    """
    form_class = FormWithUserKwarg
    template_name = 'form.html'

    def form_valid(self, form):
        return HttpResponse("username: %s" % form.user.username)


class HeadlineView(views.SetHeadlineMixin, TemplateView):
    """
    View for testing SetHeadlineMixin.
    """
    template_name = 'blank.html'
    headline = "Test headline"


class LazyHeadlineView(views.SetHeadlineMixin, TemplateView):
    """
    View for testing SetHeadlineMixin.
    """
    template_name = 'blank.html'
    headline = _("Test Headline")


class ContextView(views.StaticContextMixin, TemplateView):
    """ View for testing StaticContextMixin. """
    template_name = 'blank.html'
    static_context = {'test': True}


class DynamicHeadlineView(views.SetHeadlineMixin, TemplateView):
    """
    View for testing SetHeadlineMixin's get_headline() method.
    """
    template_name = 'blank.html'

    def get_headline(self):
        return self.kwargs['s']


class PermissionRequiredView(views.PermissionRequiredMixin, OkView):
    """
    View for testing PermissionRequiredMixin.
    """
    permission_required = 'auth.add_user'


class MultiplePermissionsRequiredView(views.MultiplePermissionsRequiredMixin,
                                      OkView):
    permissions = {
        'all': ['tests.add_article', 'tests.change_article'],
        'any': ['auth.add_user', 'auth.change_user'],
    }


class SuperuserRequiredView(views.SuperuserRequiredMixin, OkView):
    pass


class StaffuserRequiredView(views.StaffuserRequiredMixin, OkView):
    pass


class CsrfExemptView(views.CsrfExemptMixin, OkView):
    pass


class AuthorDetailView(views.PrefetchRelatedMixin, ListView):
    model = User
    prefetch_related = ['article_set']
    template_name = 'blank.html'


class OrderableListView(views.OrderableListMixin, ListView):
    model = Article
    orderable_columns = ('id', 'title', )
    orderable_columns_default = 'id'


class CanonicalSlugDetailView(views.CanonicalSlugDetailMixin, DetailView):
    model = Article
    template_name = 'blank.html'


class OverriddenCanonicalSlugDetailView(views.CanonicalSlugDetailMixin,
                                        DetailView):
    model = Article
    template_name = 'blank.html'

    def get_canonical_slug(self):
        return codecs.encode(self.get_object().slug, 'rot_13')


class CanonicalSlugDetailCustomUrlKwargsView(views.CanonicalSlugDetailMixin,
                                             DetailView):
    model = Article
    template_name = 'blank.html'
    pk_url_kwarg = 'my_pk'
    slug_url_kwarg = 'my_slug'


class ModelCanonicalSlugDetailView(views.CanonicalSlugDetailMixin,
                                   DetailView):
    model = CanonicalArticle
    template_name = 'blank.html'


class FormMessagesView(views.FormMessagesMixin, CreateView):
    form_class = ArticleForm
    form_invalid_message = _('Invalid')
    form_valid_message = _('Valid')
    model = Article
    success_url = '/form_messages/'
    template_name = 'form.html'


class GroupRequiredView(views.GroupRequiredMixin, OkView):
    group_required = 'test_group'


class UserPassesTestView(views.UserPassesTestMixin, OkView):
    def test_func(self, user):
        return user.is_staff and not user.is_superuser \
            and user.email.endswith('@mydomain.com')


class UserPassesTestNotImplementedView(views.UserPassesTestMixin, OkView):
    pass


class AllVerbsView(views.AllVerbsMixin, View):
    def all(self, request, *args, **kwargs):
        return HttpResponse('All verbs return this!')

########NEW FILE########
