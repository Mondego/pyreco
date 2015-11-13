__FILENAME__ = decorators
import functools

from django.conf import settings
from django.http import HttpResponseForbidden

def debug_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(settings, 'DEBUG_TOOLBAR_USER_DEBUG', settings.DEBUG):
            return HttpResponseForbidden()
        return fn(*args, **kwargs)
    return wrapper

########NEW FILE########
__FILENAME__ = forms
from django.contrib.auth.models import User

from django import forms

class UserForm(forms.Form):
    val = forms.CharField(label='User.{id,username,email}')

    def get_lookup(self):
        val = self.cleaned_data['val']

        if '@' in val:
            return {'email': val}

        try:
            return {'pk': int(val)}
        except:
            return {'username': val}

########NEW FILE########
__FILENAME__ = models
import debug_toolbar.urls

try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include

from .urls import urlpatterns

debug_toolbar.urls.urlpatterns += patterns('',
    ('', include(urlpatterns)),
)

########NEW FILE########
__FILENAME__ = panels
"""
:mod:`django-debug-toolbar-user-panel`
======================================

Panel for the `Django Debug Toolbar <https://github.com/django-debug-toolbar/django-debug-toolbar>`_
to easily and quickly switch between users.

 * View details on the currently logged in user.
 * Login as any user from an arbitrary email address, username or user ID.
 * Easily switch between recently logged in users.

.. figure::  screenshot.png
   :align:   center

The panel supports ``django.contrib.auth.models.User`` models that have had
the `username` field removed.

Installation
------------

Add ``debug_toolbar_user_panel`` to your ``INSTALLED_APPS``::

    INSTALLED_APPS = (
        ...
        'debug_toolbar_user_panel',
        ...
    )

Add ``debug_toolbar_user_panel.panels.UserPanel`` to ``DEBUG_TOOLBAR_PANELS``::

    DEBUG_TOOLBAR_PANELS = (
        'debug_toolbar_user_panel.panels.UserPanel'
        'debug_toolbar.panels.version.VersionDebugPanel',
        'debug_toolbar.panels.timer.TimerDebugPanel',
        'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
        'debug_toolbar.panels.headers.HeaderDebugPanel',
        'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
        'debug_toolbar.panels.sql.SQLDebugPanel',
        'debug_toolbar.panels.template.TemplateDebugPanel',
        'debug_toolbar.panels.signals.SignalDebugPanel',
        'debug_toolbar.panels.logger.LoggingPanel',
    )

Include ``debug_toolbar_user_panel.urls`` somewhere in your ``urls.py``::

    urlpatterns = patterns('',
        ...
        url(r'', include('debug_toolbar_user_panel.urls')),
        ...
    )

Links
-----

View/download code
  https://github.com/playfire/django-debug-toolbar-user-panel

File a bug
  https://github.com/playfire/django-debug-toolbar-user-panel/issues
"""

from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from debug_toolbar.panels import DebugPanel

class UserPanel(DebugPanel):
    """
    Panel that allows you to login as other recently-logged in users.
    """

    name = 'User'
    has_content = True

    def nav_title(self):
        return _('User')

    def url(self):
        return ''

    def title(self):
        return _('User')

    def nav_subtitle(self):
        return self.request.user.is_authenticated() and self.request.user

    def content(self):
        context = self.context.copy()
        context.update({
            'request': self.request,
        })

        return render_to_string('debug_toolbar_user_panel/panel.html', context)

    def process_response(self, request, response):
        self.request = request

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

from debug_toolbar.urls import _PREFIX

urlpatterns = patterns('debug_toolbar_user_panel.views',
    url(r'^%s/users/$' % _PREFIX, 'content',
        name='debug-userpanel'),
    url(r'^%s/users/login/$' % _PREFIX, 'login_form',
        name='debug-userpanel-login-form'),
    url(r'^%s/users/login/(?P<pk>-?\d+)$' % _PREFIX, 'login',
        name='debug-userpanel-login'),
    url(r'^%s/users/logout$' % _PREFIX, 'logout',
        name='debug-userpanel-logout'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.conf import settings
from django.contrib import auth
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth import logout as django_logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import UserForm
from .decorators import debug_required

@debug_required
def content(request):
    current = []

    if request.user.is_authenticated():
        for field in User._meta.fields:
            if field.name == 'password':
                continue
            current.append(
                (field.attname, getattr(request.user, field.attname))
            )

    return render_to_response('debug_toolbar_user_panel/content.html', {
        'form': UserForm(),
        'next': request.GET.get('next'),
        'users': User.objects.order_by('-last_login')[:10],
        'current': current,
    }, context_instance=RequestContext(request))

@csrf_exempt
@require_POST
@debug_required
def login_form(request):
    form = UserForm(request.POST)

    if not form.is_valid():
        return HttpResponseBadRequest()

    return login(request, **form.get_lookup())

@csrf_exempt
@require_POST
@debug_required
def login(request, **kwargs):
    user = get_object_or_404(User, **kwargs)

    user.backend = settings.AUTHENTICATION_BACKENDS[0]
    auth.login(request, user)

    return HttpResponseRedirect(request.POST.get('next', '/'))

@csrf_exempt
@require_POST
@debug_required
def logout(request):
    django_logout(request)
    return HttpResponseRedirect(request.POST.get('next', '/'))

########NEW FILE########
__FILENAME__ = conf
project = 'django-debug-toolbar-user-panel'
version = ''
release = ''
copyright = '2010, 2011 UUMC Ltd.'

html_logo = 'playfire.png'
html_theme = 'nature'
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
html_title = "%s documentation" % project
master_doc = 'index'
exclude_trees = ['_build']
templates_path = ['_templates']
latex_documents = [
  ('index', '%s.tex' % project, html_title, u'Playfire', 'manual'),
]
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
