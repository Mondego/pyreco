__FILENAME__ = backends
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User


class SuBackend(object):

    def authenticate(self, su=False, pk=None, **credentials):

        if not su:
            return None

        return User.objects.get(pk=pk)

    def get_user(self, pk):
        return User.objects.get(pk=pk)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

from django.utils.translation import ugettext_lazy as _


class UserSuForm(forms.Form):

    user = forms.ModelChoiceField(label=_('users'),
                  queryset=User.objects.all(),
                  required=True)

    def __init__(self, *args, **kwargs):
        super(UserSuForm, self).__init__(*args, **kwargs)
        self.need_jquery = False
        if 'ajax_select' in settings.INSTALLED_APPS and \
            getattr(settings, 'AJAX_LOOKUP_CHANNELS', None):
            django_su_lookup = settings.AJAX_LOOKUP_CHANNELS.get('django_su', )
            if django_su_lookup:
                from ajax_select.fields import AutoCompleteSelectField
                old_field = self.fields['user']
                self.fields['user'] = AutoCompleteSelectField('django_su',
                                            required=old_field.required,
                                            label=old_field.label)
                self.need_jquery = True

    def get_user(self):
        return self.cleaned_data.get('user', None)

    def __unicode__(self):
        if 'formadmin' in settings.INSTALLED_APPS:
            try:
                from formadmin.forms import as_django_admin
                return as_django_admin(self)
            except ImportError:
                pass
        return super(UserSuForm, self).__unicode__()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = su_tags
from django import template

from django_su.utils import can_su_login
register = template.Library()


@register.inclusion_tag('su/login_link.html', takes_context=True)
def login_su_link(context, user):
    return {'can_su_login': can_su_login(user)}

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, url


urlpatterns = patterns("django_su.views",
    url(r"^$", "su_exit", name="su_exit"),
    url(r"^login/$", "su_login", name="su_login"),
    url(r"^(?P<user_id>[\d]+)/$", "login_as_user", name="login_as_user"),
)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings


def import_function(name, package=None):
    path = name.split('.')
    module_path = '.'.join(path[:-1])
    try:
        from django.utils.importlib import import_module
        module = import_module(module_path, package)
    except ImportError:  # compatible with old version of Django
        module = __import__(module_path, {}, {}, path[-1])
    return getattr(module, path[-1])


def can_su_login(user):
    su_login = getattr(settings, 'SU_LOGIN', None)
    if su_login:
        if not callable(su_login):
            su_login = import_function(su_login)
        return su_login(user)
    return user.has_perm('auth.change_user')


def custom_login_action(request, su_user):
    custom_login_action = getattr(settings, 'SU_CUSTOM_LOGIN_ACTION', None)
    if custom_login_action:
        if not callable(custom_login_action):
            custom_login_action = import_function(custom_login_action)
        custom_login_action(request, su_user)
        return True
    return False


def get_static_url():
    static_url = getattr(settings, 'STATIC_URL', None)
    if static_url:
        return static_url
    else:  # To old django versions
        return '%sajax_select/' % getattr(settings, 'MEDIA_URL', None)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import user_passes_test

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.http import Http404
from django.template import RequestContext

from django_su.forms import UserSuForm
from django_su.utils import can_su_login, get_static_url, custom_login_action

from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY


@user_passes_test(can_su_login)
def login_as_user(request, user_id):
    su_user = authenticate(su=True, pk=user_id)

    if not su_user:
        raise Http404("User not found")

    exit_user_pk = (request.session[SESSION_KEY], request.session[BACKEND_SESSION_KEY])
    exit_users_pk = request.session.get("exit_users_pk", default=[])
    exit_users_pk.append(exit_user_pk)
    if not custom_login_action(request, su_user):
        login(request, su_user)
    request.session["exit_users_pk"] = exit_users_pk
    return HttpResponseRedirect(getattr(settings, "SU_REDIRECT_LOGIN", "/"))


@user_passes_test(can_su_login)
def su_login(request, user_form=UserSuForm):
    data = None
    if request.method == 'POST':
        data = request.POST
    form = user_form(data=data)
    if form.is_valid():
        user = form.get_user()
        return login_as_user(request, user.pk)
    return render_to_response('su/login.html',
                              {'form': form,
                               'STATIC_URL': get_static_url()},
                              context_instance=RequestContext(request))


def su_exit(request):
    exit_users_pk = request.session.get("exit_users_pk", default=[])
    if not exit_users_pk:
        return HttpResponseBadRequest(("This session was not su'ed into."
                                       "Cannot exit."))
    staff_user = User.objects.get(pk=exit_users_pk[-1][0])
    staff_user.backend = exit_users_pk[-1][1]
    if not custom_login_action(request, staff_user):
        login(request, staff_user)
    request.session["exit_users_pk"] = exit_users_pk[:-1]
    return HttpResponseRedirect(getattr(settings, "SU_REDIRECT_EXIT", "/"))

########NEW FILE########
