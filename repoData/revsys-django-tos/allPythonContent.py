__FILENAME__ = admin
from django.contrib import admin 

from tos.models import TermsOfService, UserAgreement

class TermsOfServiceAdmin(admin.ModelAdmin): 
    model = TermsOfService   

admin.site.register(TermsOfService, TermsOfServiceAdmin)


class UserAgreementAdmin(admin.ModelAdmin): 
    model = UserAgreement

admin.site.register(UserAgreement, UserAgreementAdmin)

########NEW FILE########
__FILENAME__ = models
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

# Django 1.4 compatability
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
    get_user_model = lambda: User


USER_MODEL = get_user_model()


class NoActiveTermsOfService(ValidationError):
    pass


class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class TermsOfServiceManager(models.Manager):
    def get_current_tos(self):
        try:
            return self.get(active=True)
        except self.model.DoesNotExist:
            raise NoActiveTermsOfService(u'Please create an active Terms-of-Service')


class TermsOfService(BaseModel):
    active = models.BooleanField(verbose_name=_('active'),
                                 help_text=_(u'Only one terms of service is allowed to be active'))
    content = models.TextField(verbose_name=_('content'), blank=True)
    objects = TermsOfServiceManager()

    class Meta:
        get_latest_by = 'created'
        ordering = ('-created',)
        verbose_name = _('Terms of Service')
        verbose_name_plural = _('Terms of Service')

    def __unicode__(self):
        active = 'inactive'
        if self.active:
            active = 'active'
        return '{0}: {1}'.format(self.created, active)

    def save(self, *args, **kwargs):
        """ Ensure we're being saved properly """

        if self.active:
            TermsOfService.objects.exclude(id=self.id).update(active=False)

        else:
            if not TermsOfService.objects\
                    .exclude(id=self.id)\
                    .filter(active=True):
                raise NoActiveTermsOfService(u'One of the terms of service must be marked active')

        super(TermsOfService, self).save(*args, **kwargs)


class UserAgreement(BaseModel):
    terms_of_service = models.ForeignKey(TermsOfService, related_name='terms')
    user = models.ForeignKey(USER_MODEL, related_name='user_agreement')

    def __unicode__(self):
        return u'%s agreed to TOS: %s' % (self.user.username,
                                          unicode(self.terms_of_service))


def has_user_agreed_latest_tos(user):
    if UserAgreement.objects.filter(terms_of_service=TermsOfService.objects.get_current_tos(), user=user):
        return True
    return False

########NEW FILE########
__FILENAME__ = test_models
from django.core.exceptions import ValidationError
from django.test import TestCase


# Django 1.4 compatability
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
    get_user_model = lambda: User

USER_MODEL = get_user_model()

from tos.models import TermsOfService, UserAgreement, has_user_agreed_latest_tos


class TestModels(TestCase):

    def setUp(self):
        self.user1 = USER_MODEL.objects.create_user('user1', 'user1@example.com', 'user1pass')
        self.user2 = USER_MODEL.objects.create_user('user2', 'user2@example.com', 'user2pass')
        self.user3 = USER_MODEL.objects.create_user('user3', 'user3@example.com', 'user3pass')

        self.tos1 = TermsOfService.objects.create(
            content="first edition of the terms of service",
            active=True
        )
        self.tos2 = TermsOfService.objects.create(
            content="second edition of the terms of service",
            active=False
        )

    def test_terms_of_service(self):

        tos_objects = TermsOfService.objects.all()
        self.assertEquals(TermsOfService.objects.count(), 2)

        # order is by -created
        latest = TermsOfService.objects.latest()
        self.assertFalse(latest.active)

        # setting a tos to True changes all others to False
        latest.active = True
        latest.save()
        first = TermsOfService.objects.get(id=self.tos1.id)
        self.assertFalse(first.active)

        # latest is active though
        self.assertTrue(latest.active)

    def test_terms_of_service_manager(self):

        self.assertEquals(TermsOfService.objects.get_current_tos(), self.tos1)

    def test_validation_error_all_set_false(self):
        """ If you try and set all to false the model will throw a ValidationError """

        self.tos1.active = False
        self.assertRaises(ValidationError, self.tos1.save)

    def test_user_agreement(self):

        # simple agreement
        UserAgreement.objects.create(
            terms_of_service=self.tos1,
            user=self.user1
        )

        self.assertTrue(has_user_agreed_latest_tos(self.user1))
        self.assertFalse(has_user_agreed_latest_tos(self.user2))
        self.assertFalse(has_user_agreed_latest_tos(self.user3))

        # Now set self.tos2.active to True and see what happens
        self.tos2.active = True
        self.tos2.save()
        self.assertFalse(has_user_agreed_latest_tos(self.user1))
        self.assertFalse(has_user_agreed_latest_tos(self.user2))
        self.assertFalse(has_user_agreed_latest_tos(self.user3))

        # add in a couple agreements and try again
        UserAgreement.objects.create(
            terms_of_service=self.tos2,
            user=self.user1
        )
        UserAgreement.objects.create(
            terms_of_service=self.tos2,
            user=self.user3
        )

        self.assertTrue(has_user_agreed_latest_tos(self.user1))
        self.assertFalse(has_user_agreed_latest_tos(self.user2))
        self.assertTrue(has_user_agreed_latest_tos(self.user3))

########NEW FILE########
__FILENAME__ = test_settings
DEBUG = True
TEMPLATE_DEBUG = DEBUG
SITE_ID = 1
SECRET_KEY = 'foobarbaz'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase'
    }
}

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'tos',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)

TEMPLATE_DIRS = (
        '/Users/frank/work/src/django-tos/templates/',
)

ROOT_URLCONF = 'tos.tests.test_urls'

LOGIN_URL = '/login/'

import logging
logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s',
)

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import * 

from tos.views import * 

urlpatterns = patterns('', 
        (r'^login/$', 'tos.views.login', {}, 'login',), 
        (r'^tos/', include('tos.urls')), 
    ) 

########NEW FILE########
__FILENAME__ = test_views
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

# Django 1.4 compatability
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
    get_user_model = lambda: User

from tos.models import TermsOfService, UserAgreement, has_user_agreed_latest_tos

USER = get_user_model()


class TestViews(TestCase):

    def setUp(self):
        self.user1 = USER.objects.create_user('user1', 'user1@example.com', 'user1pass')
        self.user2 = USER.objects.create_user('user2', 'user2@example.com', 'user2pass')

        self.tos1 = TermsOfService.objects.create(
            content="first edition of the terms of service",
            active=True
        )
        self.tos2 = TermsOfService.objects.create(
            content="second edition of the terms of service",
            active=False
        )

        self.login_url = getattr(settings, 'LOGIN_URL', '/login/')

        UserAgreement.objects.create(
            terms_of_service=self.tos1,
            user=self.user1
        )

    def test_login(self):
        """ Make sure we didn't break the authentication system
            This assumes that login urls are named 'login'
        """

        self.assertTrue(has_user_agreed_latest_tos(self.user1))
        login = self.client.login(username='user1', password='user1pass')
        self.failUnless(login, 'Could not log in')
        self.assertTrue(has_user_agreed_latest_tos(self.user1))

    def test_need_agreement(self):
        """ user2 tries to login and then has to go and agree to terms"""

        self.assertFalse(has_user_agreed_latest_tos(self.user2))

        response = self.client.post(self.login_url, dict(username='user2', password='user2pass'))
        self.assertContains(response, "first edition of the terms of service")

        self.assertFalse(has_user_agreed_latest_tos(self.user2))

    def test_reject_agreement(self):

        self.assertFalse(has_user_agreed_latest_tos(self.user2))

        response = self.client.post(self.login_url, dict(username='user2', password='user2pass'))
        self.assertContains(response, "first edition of the terms of service")
        url = reverse('tos_check_tos')
        response = self.client.post(url, {'accept': 'reject'})

        self.assertFalse(has_user_agreed_latest_tos(self.user2))

    def test_accept_agreement(self):

        self.assertFalse(has_user_agreed_latest_tos(self.user2))

        response = self.client.post(self.login_url, dict(username='user2', password='user2pass'))
        self.assertContains(response, "first edition of the terms of service")
        self.assertFalse(has_user_agreed_latest_tos(self.user2))
        url = reverse('tos_check_tos')
        response = self.client.post(url, {'accept': 'accept'})

        self.assertTrue(has_user_agreed_latest_tos(self.user2))

    def test_bump_new_agreement(self):

        # Change the tos
        self.tos2.active = True
        self.tos2.save()

        # is user1 agreed now?
        self.assertFalse(has_user_agreed_latest_tos(self.user1))

        # user1 agrees again
        response = self.client.post(self.login_url, dict(username='user1', password='user1pass'))
        self.assertContains(response, "second edition of the terms of service")
        self.assertFalse(has_user_agreed_latest_tos(self.user2))
        url = reverse('tos_check_tos')
        response = self.client.post(url, {'accept': 'accept'})

        self.assertTrue(has_user_agreed_latest_tos(self.user1))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns
from tos.views import check_tos, TosView

urlpatterns = patterns('',
        # Terms of Service conform
        url(r'^confirm/$', check_tos, name='tos_check_tos'),

        # Terms of service simple display
        url(r'^$', TosView.as_view(), name='tos'),
    )
########NEW FILE########
__FILENAME__ = views
from django.views.generic import TemplateView
import re
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.models import Site, RequestSite
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import ugettext_lazy as _

from tos.models import has_user_agreed_latest_tos, TermsOfService, UserAgreement


# Django 1.4 compatability
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
    get_user_model = lambda: User

USER = get_user_model()


class TosView(TemplateView):
    template_name = "tos/tos.html"

    def get_context_data(self, **kwargs):
        context = super(TosView, self).get_context_data(**kwargs)
        context['tos'] = TermsOfService.objects.get_current_tos()
        return context


def _redirect_to(redirect_to):
    """ Moved redirect_to logic here to avoid duplication in views"""

    # Light security check -- make sure redirect_to isn't garbage.
    if not redirect_to or ' ' in redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL

    # Heavier security check -- redirects to http://example.com should
    # not be allowed, but things like /view/?param=http://example.com
    # should be allowed. This regex checks if there is a '//' *before* a
    # question mark.
    elif '//' in redirect_to and re.match(r'[^\?]*//', redirect_to):
            redirect_to = settings.LOGIN_REDIRECT_URL
    return redirect_to


@csrf_protect
@never_cache
def check_tos(request, template_name='tos/tos_check.html',
              redirect_field_name=REDIRECT_FIELD_NAME,):

    redirect_to = _redirect_to(request.REQUEST.get(redirect_field_name, ''))
    tos = TermsOfService.objects.get_current_tos()
    if request.method == "POST":
        if request.POST.get("accept", "") == "accept":
            user = get_user_model().objects.get(pk=request.session['tos_user'])
            user.backend = request.session['tos_backend']

            # Save the user agreement to the new TOS
            UserAgreement.objects.create(terms_of_service=tos, user=user)

            # Log the user in
            auth_login(request, user)

            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()

            return HttpResponseRedirect(redirect_to)
        else:
            messages.error(request, _(u"You cannot login without agreeing to the terms of this site."))

    return render_to_response(template_name, {
        'tos': tos,
        redirect_field_name: redirect_to,
    }, context_instance=RequestContext(request))


@csrf_protect
@never_cache
def login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm):
    """Displays the login form and handles the login action."""

    redirect_to = request.REQUEST.get(redirect_field_name, '')

    if request.method == "POST":
        form = authentication_form(data=request.POST)
        if form.is_valid():

            redirect_to = _redirect_to(redirect_to)

            # Okay, security checks complete. Check to see if user agrees to terms
            user = form.get_user()
            if has_user_agreed_latest_tos(user):

                # Log the user in.
                auth_login(request, user)

                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()

                return HttpResponseRedirect(redirect_to)

            else:
                # user has not yet agreed to latest tos
                # force them to accept or refuse

                request.session['tos_user'] = user.pk
                # Pass the used backend as well since django will require it
                # and it can only be optained by calling authenticate, but we got no credentials in check_tos.
                # see: https://docs.djangoproject.com/en/1.6/topics/auth/default/#how-to-log-a-user-in
                request.session['tos_backend'] = user.backend

                return render_to_response('tos/tos_check.html', {
                    redirect_field_name: redirect_to,
                    'tos': TermsOfService.objects.get_current_tos()
                }, context_instance=RequestContext(request))

    else:
        form = authentication_form(request)

    request.session.set_test_cookie()

    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)

    return render_to_response(template_name, {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from tos.admin import TermsOfServiceAdmin

# Admin translation for django-plans
from tos.models import TermsOfService


class TranslatedTermsOfServiceAdmin(TermsOfServiceAdmin, TranslationAdmin):
    pass

admin.site.unregister(TermsOfService)
admin.site.register(TermsOfService, TranslatedTermsOfServiceAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = translation
from modeltranslation.translator import translator, TranslationOptions
from tos.models import TermsOfService

# Translations for django-tos

class TermsOfServiceTranslationOptions(TranslationOptions):
    fields = ('content', )

translator.register(TermsOfService, TermsOfServiceTranslationOptions)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
