__FILENAME__ = manage
#!/usr/bin/env python
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
__FILENAME__ = admin
from django.contrib import admin
from polls.models import Poll, Choice


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class PollAdmin(admin.ModelAdmin):
    date_hierarchy = 'pub_date'
    fieldsets = [
        (None,               {'fields': ['question']}),
        ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    inlines = [ChoiceInline]
    list_display = ('question', 'pub_date', 'was_published_today')
    list_filter = ['pub_date']
    search_fields = ['question']


admin.site.register(Poll, PollAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from polls.models import Choice


class PollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # We require an ``instance`` parameter.
        self.instance = kwargs.pop('instance')
        
        # We call ``super`` (without the ``instance`` param) to finish
        # off the setup.
        super(PollForm, self).__init__(*args, **kwargs)
        
        # We add on a ``choice`` field based on the instance we've got.
        # This has to be done here (instead of declaratively) because the
        # ``Poll`` instance will change from request to request.
        self.fields['choice'] = forms.ModelChoiceField(queryset=Choice.objects.filter(poll=self.instance.pk), empty_label=None, widget=forms.RadioSelect)
    
    def save(self):
        if not self.is_valid():
            raise forms.ValidationError("PollForm was not validated first before trying to call 'save'.")
        
        choice = self.cleaned_data['choice']
        choice.record_vote()
        return choice

########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models


class PollManager(models.Manager):
    def get_query_set(self):
        now = datetime.datetime.now()
        return super(PollManager, self).get_query_set().filter(pub_date__lte=now)


class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', default=datetime.datetime.now)
    
    objects = models.Manager()
    published = PollManager()
    
    def __unicode__(self):
        return self.question
    
    def was_published_today(self):
        return self.pub_date.date() == datetime.date.today()
    was_published_today.short_description = 'Published today?'


class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)
    
    def __unicode__(self):
        return self.choice
    
    def record_vote(self):
        self.votes += 1
        self.save()

########NEW FILE########
__FILENAME__ = forms
from django.test import TestCase
from polls.forms import PollForm
from polls.models import Poll, Choice


class PollFormTestCase(TestCase):
    fixtures = ['polls_forms_testdata.json']
    
    def setUp(self):
        super(PollFormTestCase, self).setUp()
        self.poll_1 = Poll.objects.get(pk=1)
        self.poll_2 = Poll.objects.get(pk=2)
    
    def test_init(self):
        # Test successful init without data.
        form = PollForm(instance=self.poll_1)
        self.assertTrue(isinstance(form.instance, Poll))
        self.assertEqual(form.instance.pk, self.poll_1.pk)
        self.assertEqual([c for c in form.fields['choice'].choices], [(1, u'Yes'), (2, u'No')])
        
        # Test successful init with data.
        form = PollForm({'choice': 3}, instance=self.poll_2)
        self.assertTrue(isinstance(form.instance, Poll))
        self.assertEqual(form.instance.pk, self.poll_2.pk)
        self.assertEqual([c for c in form.fields['choice'].choices], [(3, u'Alright.'), (4, u'Meh.'), (5, u'Not so good.')])
        
        # Test a failed init without data.
        self.assertRaises(KeyError, PollForm)
        
        # Test a failed init with data.
        self.assertRaises(KeyError, PollForm, {})
    
    def test_save(self):
        self.assertEqual(self.poll_1.choice_set.get(pk=1).votes, 1)
        self.assertEqual(self.poll_1.choice_set.get(pk=2).votes, 0)
        
        # Test the first choice.
        form_1 = PollForm({'choice': 1}, instance=self.poll_1)
        form_1.save()
        self.assertEqual(self.poll_1.choice_set.get(pk=1).votes, 2)
        self.assertEqual(self.poll_1.choice_set.get(pk=2).votes, 0)
        
        # Test the second choice.
        form_2 = PollForm({'choice': 2}, instance=self.poll_1)
        form_2.save()
        self.assertEqual(self.poll_1.choice_set.get(pk=1).votes, 2)
        self.assertEqual(self.poll_1.choice_set.get(pk=2).votes, 1)
        
        # Test the other poll.
        self.assertEqual(self.poll_2.choice_set.get(pk=3).votes, 1)
        self.assertEqual(self.poll_2.choice_set.get(pk=4).votes, 0)
        self.assertEqual(self.poll_2.choice_set.get(pk=5).votes, 0)
        
        form_3 = PollForm({'choice': 5}, instance=self.poll_2)
        form_3.save()
        self.assertEqual(self.poll_2.choice_set.get(pk=3).votes, 1)
        self.assertEqual(self.poll_2.choice_set.get(pk=4).votes, 0)
        self.assertEqual(self.poll_2.choice_set.get(pk=5).votes, 1)

########NEW FILE########
__FILENAME__ = models
import datetime
from django.test import TestCase
from polls.models import Poll, Choice


class PollTestCase(TestCase):
    fixtures = ['polls_forms_testdata.json']
    
    def setUp(self):
        super(PollTestCase, self).setUp()
        self.poll_1 = Poll.objects.get(pk=1)
        self.poll_2 = Poll.objects.get(pk=2)
    
    def test_was_published_today(self):
        # Because unless you're timetraveling, they weren't.
        self.assertFalse(self.poll_1.was_published_today())
        self.assertFalse(self.poll_2.was_published_today())
        
        # Modify & check again.
        now = datetime.datetime.now()
        self.poll_1.pub_date = now
        self.poll_1.save()
        self.assertTrue(self.poll_1.was_published_today())
    
    def test_better_defaults(self):
        now = datetime.datetime.now()
        poll = Poll.objects.create(
            question="A test question."
        )
        self.assertEqual(poll.pub_date.date(), now.date())
    
    def test_no_future_dated_polls(self):
        # Create the future-dated ``Poll``.
        poll = Poll.objects.create(
            question="Do we have flying cars yet?",
            pub_date=datetime.datetime.now() + datetime.timedelta(days=1)
        )
        self.assertEqual(list(Poll.objects.all().values_list('id', flat=True)), [1, 2, 3])
        self.assertEqual(list(Poll.published.all().values_list('id', flat=True)), [1, 2])


class ChoiceTestCase(TestCase):
    fixtures = ['polls_forms_testdata.json']
    
    def test_record_vote(self):
        choice_1 = Choice.objects.get(pk=1)
        choice_2 = Choice.objects.get(pk=2)
        
        self.assertEqual(Choice.objects.get(pk=1).votes, 1)
        self.assertEqual(Choice.objects.get(pk=2).votes, 0)
        
        choice_1.record_vote()
        self.assertEqual(Choice.objects.get(pk=1).votes, 2)
        self.assertEqual(Choice.objects.get(pk=2).votes, 0)
        
        choice_2.record_vote()
        self.assertEqual(Choice.objects.get(pk=1).votes, 2)
        self.assertEqual(Choice.objects.get(pk=2).votes, 1)
        
        choice_1.record_vote()
        self.assertEqual(Choice.objects.get(pk=1).votes, 3)
        self.assertEqual(Choice.objects.get(pk=2).votes, 1)
    
    def test_better_defaults(self):
        poll = Poll.objects.create(
            question="Are you still there?"
        )
        choice = Choice.objects.create(
            poll=poll,
            choice="I don't blame you."
        )
        
        self.assertEqual(poll.choice_set.all()[0].choice, "I don't blame you.")
        self.assertEqual(poll.choice_set.all()[0].votes, 0)

########NEW FILE########
__FILENAME__ = views
import datetime
from django.core.urlresolvers import reverse
from django.test import TestCase
from polls.models import Poll, Choice


class PollsViewsTestCase(TestCase):
    fixtures = ['polls_views_testdata.json']
    
    def test_index(self):
        resp = self.client.get(reverse('polls_index'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('latest_poll_list' in resp.context)
        self.assertEqual([poll.pk for poll in resp.context['latest_poll_list']], [1])
        poll_1 = resp.context['latest_poll_list'][0]
        self.assertEqual(poll_1.question, 'Are you learning about testing in Django?')
        self.assertEqual(poll_1.choice_set.count(), 2)
        choices = poll_1.choice_set.all()
        self.assertEqual(choices[0].choice, 'Yes')
        self.assertEqual(choices[0].votes, 1)
        self.assertEqual(choices[1].choice, 'No')
        self.assertEqual(choices[1].votes, 0)
    
    def test_detail(self):
        resp = self.client.get(reverse('polls_detail', kwargs={'poll_id': 1}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['poll'].pk, 1)
        self.assertEqual(resp.context['poll'].question, 'Are you learning about testing in Django?')
        
        # Ensure that non-existent polls throw a 404.
        resp = self.client.get(reverse('polls_detail', kwargs={'poll_id': 2}))
        self.assertEqual(resp.status_code, 404)
    
    def test_results(self):
        resp = self.client.get(reverse('polls_results', kwargs={'poll_id': 1}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['poll'].pk, 1)
        self.assertEqual(resp.context['poll'].question, 'Are you learning about testing in Django?')
        
        # Ensure that non-existent polls throw a 404.
        resp = self.client.get(reverse('polls_results', kwargs={'poll_id': 2}))
        self.assertEqual(resp.status_code, 404)
    
    def test_good_vote(self):
        poll_1 = Poll.objects.get(pk=1)
        self.assertEqual(poll_1.choice_set.get(pk=1).votes, 1)
        
        resp = self.client.post(reverse('polls_detail', kwargs={'poll_id': 1}), {'choice': 1})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/polls/1/results/')
        
        self.assertEqual(poll_1.choice_set.get(pk=1).votes, 2)
    
    def test_bad_votes(self):
        # Ensure a non-existant PK throws a Not Found.
        resp = self.client.post(reverse('polls_detail', kwargs={'poll_id': 1000000}))
        self.assertEqual(resp.status_code, 404)
        
        # Sanity check.
        poll_1 = Poll.objects.get(pk=1)
        self.assertEqual(poll_1.choice_set.get(pk=1).votes, 1)
        
        # Send no POST data.
        resp = self.client.post(reverse('polls_detail', kwargs={'poll_id': 1}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['form']['choice'].errors, [u'This field is required.'])
        
        # Send junk POST data.
        resp = self.client.post(reverse('polls_detail', kwargs={'poll_id': 1}), {'foo': 'bar'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['form']['choice'].errors, [u'This field is required.'])
        
        # Send a non-existant Choice PK.
        resp = self.client.post(reverse('polls_detail', kwargs={'poll_id': 1}), {'choice': 300})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['form']['choice'].errors, [u'Select a valid choice. That choice is not one of the available choices.'])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('polls.views',
    url(r'^$', 'index', name='polls_index'),
    url(r'^(?P<poll_id>\d+)/$', 'detail', name='polls_detail'),
    url(r'^(?P<poll_id>\d+)/results/$', 'results', name='polls_results'),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from polls.forms import PollForm
from polls.models import Poll, Choice


def index(request):
    latest_poll_list = Poll.published.all().order_by('-pub_date')[:5]
    return render_to_response('polls/index.html', {'latest_poll_list': latest_poll_list})


def detail(request, poll_id):
    p = get_object_or_404(Poll.published.all(), pk=poll_id)
    
    if request.method == 'POST':
        form = PollForm(request.POST, instance=p)
        
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('polls_results', kwargs={'poll_id': p.id}))
    else:
        form = PollForm(instance=p)
    
    return render_to_response('polls/detail.html', {
        'poll': p,
        'form': form,
    }, context_instance=RequestContext(request))


def results(request, poll_id):
    p = get_object_or_404(Poll.published.all(), pk=poll_id)
    return render_to_response('polls/results.html', {'poll': p})

########NEW FILE########
__FILENAME__ = settings
# Django settings for guide_to_testing project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'polls.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory that holds static files.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL that handles the static files served from STATIC_ROOT.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# A list of locations of additional static files
STATICFILES_DIRS = ()

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'p(u%@fn&r_d7@$p@jqfwwp#$l-@=_pdf_$y$2jztv_dmcgk@g5'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

import os
PROJECT_ROOT = os.path.dirname(__file__)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'polls',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request':{
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Example:
    # (r'^guide_to_testing/', include('guide_to_testing.foo.urls')),

    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^polls/', include('polls.urls')),
)

########NEW FILE########
