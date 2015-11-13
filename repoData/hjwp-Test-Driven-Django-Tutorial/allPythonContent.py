__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
from collections import namedtuple
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

PollInfo = namedtuple('PollInfo', ['question', 'choices'])
POLL1 = PollInfo(
    question="How awesome is Test-Driven Development?",
    choices=[
        'Very awesome',
        'Quite awesome',
        'Moderately awesome',
    ],
)
POLL2 = PollInfo(
    question="Which workshop treat do you prefer?",
    choices=[
        'Beer',
        'Pizza',
        'The Acquisition of Knowledge',
    ],
)


class PollsTest(LiveServerTestCase):
    fixtures = ['admin_user.json']

    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(3)

    def tearDown(self):
        self.browser.quit()

    def test_can_create_new_poll_via_admin_site(self):
        # Gertrude opens her web browser, and goes to the admin page
        self.browser.get(self.live_server_url + '/admin/')

        # She sees the familiar 'Django administration' heading
        body = self.browser.find_element_by_tag_name('body')
        self.assertIn('Django administration', body.text)

        # She types in her username and passwords and hits return
        username_field = self.browser.find_element_by_name('username')
        username_field.send_keys('admin')

        password_field = self.browser.find_element_by_name('password')
        password_field.send_keys('adm1n')
        password_field.send_keys(Keys.RETURN)

        # her username and password are accepted, and she is taken to
        # the Site Administration page
        body = self.browser.find_element_by_tag_name('body')
        self.assertIn('Site administration', body.text)

        # She now sees a couple of hyperlink that says "Polls"
        polls_links = self.browser.find_elements_by_link_text('Polls')
        self.assertEquals(len(polls_links), 2)

        # The second one looks more exciting, so she clicks it
        polls_links[1].click()

        # She is taken to the polls listing page, which shows she has
        # no polls yet
        body = self.browser.find_element_by_tag_name('body')
        self.assertIn('0 polls', body.text)

        # She sees a link to 'add' a new poll, so she clicks it
        new_poll_link = self.browser.find_element_by_link_text('Add poll')
        new_poll_link.click()

        # She sees some input fields for "Question" and "Date published"
        body = self.browser.find_element_by_tag_name('body')
        self.assertIn('Question:', body.text)
        self.assertIn('Date published:', body.text)
        # She types in an interesting question for the Poll
        question_field = self.browser.find_element_by_name('question')
        question_field.send_keys("How awesome is Test-Driven Development?")

        # She sets the date and time of publication - it'll be a new year's
        # poll!
        date_field = self.browser.find_element_by_name('pub_date_0')
        date_field.send_keys('01/01/12')
        time_field = self.browser.find_element_by_name('pub_date_1')
        time_field.send_keys('00:00')

        # She sees she can enter choices for the Poll.  She adds three
        choice_1 = self.browser.find_element_by_name('choice_set-0-choice')
        choice_1.send_keys('Very awesome')
        choice_2 = self.browser.find_element_by_name('choice_set-1-choice')
        choice_2.send_keys('Quite awesome')
        choice_3 = self.browser.find_element_by_name('choice_set-2-choice')
        choice_3.send_keys('Moderately awesome')

        # Gertrude clicks the save button
        save_button = self.browser.find_element_by_css_selector("input[value='Save']")
        save_button.click()

        # She is returned to the "Polls" listing, where she can see her
        # new poll, listed as a clickable link
        new_poll_links = self.browser.find_elements_by_link_text(
                "How awesome is Test-Driven Development?"
        )
        self.assertEquals(len(new_poll_links), 1)

        # Satisfied, she goes back to sleep


    def _setup_polls_via_admin(self):
        # Gertrude logs into the admin site
        self.browser.get(self.live_server_url + '/admin/')
        username_field = self.browser.find_element_by_name('username')
        username_field.send_keys('admin')
        password_field = self.browser.find_element_by_name('password')
        password_field.send_keys('adm1n')
        password_field.send_keys(Keys.RETURN)

        # She has a number of polls to enter.  For each one, she:
        for poll_info in [POLL1, POLL2]:
            # Follows the link to the Polls app, and adds a new Poll
            self.browser.find_elements_by_link_text('Polls')[1].click()
            self.browser.find_element_by_link_text('Add poll').click()

            # Enters its name, and uses the 'today' and 'now' buttons to set
            # the publish date
            question_field = self.browser.find_element_by_name('question')
            question_field.send_keys(poll_info.question)
            self.browser.find_element_by_link_text('Today').click()
            self.browser.find_element_by_link_text('Now').click()

            # Sees she can enter choices for the Poll on this same page,
            # so she does
            for i, choice_text in enumerate(poll_info.choices):
                choice_field = self.browser.find_element_by_name('choice_set-%d-choice' % i)
                choice_field.send_keys(choice_text)

            # Saves her new poll
            save_button = self.browser.find_element_by_css_selector("input[value='Save']")
            save_button.click()

            # Is returned to the "Polls" listing, where she can see her
            # new poll, listed as a clickable link by its name
            new_poll_links = self.browser.find_elements_by_link_text(
                    poll_info.question
            )
            self.assertEquals(len(new_poll_links), 1)

            # She goes back to the root of the admin site
            self.browser.get(self.live_server_url + '/admin/')

        # She logs out of the admin site
        self.browser.find_element_by_link_text('Log out').click()


    def test_voting_on_a_new_poll(self):
        # First, Gertrude the administrator logs into the admin site and
        # creates a couple of new Polls, and their response choices
        self._setup_polls_via_admin()

        # Now, Herbert the regular user goes to the homepage of the site. He
        # sees a list of polls.
        self.browser.get(self.live_server_url)
        heading = self.browser.find_element_by_tag_name('h1')
        self.assertEquals(heading.text, 'Polls')

        # He clicks on the link to the first Poll, which is called
        # 'How awesome is test-driven development?'
        first_poll_title = 'How awesome is Test-Driven Development?'
        self.browser.find_element_by_link_text(first_poll_title).click()

        # He is taken to a poll 'results' page, which says
        # "no-one has voted on this poll yet"
        main_heading = self.browser.find_element_by_tag_name('h1')
        self.assertEquals(main_heading.text, 'Poll Results')
        sub_heading = self.browser.find_element_by_tag_name('h2')
        self.assertEquals(sub_heading.text, first_poll_title)
        body = self.browser.find_element_by_tag_name('body')
        self.assertIn('No-one has voted on this poll yet', body.text)

        # He also sees a form, which offers him several choices.
        # There are three options with radio buttons
        choice_inputs = self.browser.find_elements_by_css_selector(
                "input[type='radio']"
        )
        self.assertEquals(len(choice_inputs), 3)

        # The buttons have labels to explain them
        choice_labels = self.browser.find_elements_by_tag_name('label')
        choices_text = [c.text for c in choice_labels]
        self.assertEquals(choices_text, [
            'Vote:', # this label is auto-generated for the whole form
            'Very awesome',
            'Quite awesome',
            'Moderately awesome',
        ])
        # He decided to select "very awesome", which is answer #1
        chosen = self.browser.find_element_by_css_selector(
                "input[value='1']"
        )
        chosen.click()

        # Herbert clicks 'submit'
        self.browser.find_element_by_css_selector(
                "input[type='submit']"
            ).click()

        # The page refreshes, and he sees that his choice
        # has updated the results.  they now say
        # "100 %: very awesome".
        body_text = self.browser.find_element_by_tag_name('body').text
        self.assertIn('100 %: Very awesome', body_text)

        # The page also says "1 vote"
        self.assertIn('1 vote', body_text)

        # But not "1 votes" -- Herbert is impressed at the attention to detail
        self.assertNotIn('1 votes', body_text)

        # Herbert suspects that the website isn't very well protected
        # against people submitting multiple votes yet, so he tries
        # to do a little astroturfing
        self.browser.find_element_by_css_selector("input[value='1']").click()
        self.browser.find_element_by_css_selector("input[type='submit']").click()

        # The page refreshes, and he sees that his choice has updated the
        # results.  it still says # "100 %: very awesome".
        body_text = self.browser.find_element_by_tag_name('body').text
        self.assertIn('100 %: Very awesome', body_text)

        # But the page now says "2 votes"
        self.assertIn('2 votes', body_text)

        # Cackling manically over his l33t haxx0ring skills, he tries
        # voting for a different choice
        self.browser.find_element_by_css_selector("input[value='2']").click()
        self.browser.find_element_by_css_selector("input[type='submit']").click()

        # Now, the percentages update, as well as the votes
        body_text = self.browser.find_element_by_tag_name('body').text
        self.assertIn('67 %: Very awesome', body_text)
        self.assertIn('33 %: Quite awesome', body_text)
        self.assertIn('3 votes', body_text)

        # Satisfied, he goes back to sleep



########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for mysite project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'database.sqlite',                      # Or path to database file if using sqlite3.
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
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'i%wqqa*4o=seu-sie_oy)fp=*uc0*j)m5p)ju6#g2g=dfp#6ks'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'mysite.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'mysite.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'fts',
    'polls',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'polls.views.home'),
    url(r'^poll/(\d+)/$', 'polls.views.poll'),
    url(r'^admin/', include(admin.site.urls)),
)


########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for mysite project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from polls.models import Choice, Poll

class ChoiceInline(admin.StackedInline):
    model = Choice
    extra = 3

class PollAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]

admin.site.register(Poll, PollAdmin)


########NEW FILE########
__FILENAME__ = forms
from django import forms

class PollVoteForm(forms.Form):
    vote = forms.ChoiceField(widget=forms.RadioSelect())

    def __init__(self, poll):
        forms.Form.__init__(self)
        self.fields['vote'].choices = [(c.id, c.choice) for c in poll.choice_set.all()]

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField(verbose_name='Date published')

    def __unicode__(self):
        return self.question

    def total_votes(self):
        return sum(c.votes for c in self.choice_set.all())



class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def percentage(self):
        try:
            return 100.0 * self.votes / self.poll.total_votes()
        except ZeroDivisionError:
            return 0

########NEW FILE########
__FILENAME__ = test_forms
from polls.forms import PollVoteForm
from django.test import TestCase
from django.utils import timezone
from polls.models import Choice, Poll



class PollsVoteFormTest(TestCase):

    def test_form_renders_poll_choices_as_radio_inputs(self):
        # set up a poll with a couple of choices
        poll1 = Poll(question='6 times 7', pub_date=timezone.now())
        poll1.save()
        choice1 = Choice(poll=poll1, choice='42', votes=0)
        choice1.save()
        choice2 = Choice(poll=poll1, choice='The Ultimate Answer', votes=0)
        choice2.save()

        # set up another poll to make sure we only see the right choices
        poll2 = Poll(question='time', pub_date=timezone.now())
        poll2.save()
        choice3 = Choice(poll=poll2, choice='PM', votes=0)
        choice3.save()

        # build a voting form for poll1
        form = PollVoteForm(poll=poll1)

        # check it has a single field called 'vote', which has right choices:
        self.assertEquals(form.fields.keys(), ['vote'])

        # choices are tuples in the format (choice_number, choice_text):
        self.assertEquals(form.fields['vote'].choices, [
            (choice1.id, choice1.choice),
            (choice2.id, choice2.choice),
        ])

        # check it uses radio inputs to render
        self.assertIn('input type="radio"', form.as_p())


    def test_page_shows_choices_using_form(self):
        # set up a poll with choices
        poll1 = Poll(question='time', pub_date=timezone.now())
        poll1.save()
        choice1 = Choice(poll=poll1, choice="PM", votes=0)
        choice1.save()
        choice2 = Choice(poll=poll1, choice="Gardener's", votes=0)
        choice2.save()

        response = self.client.get('/poll/%d/' % (poll1.id, ))

        # check we've passed in a form of the right type
        self.assertTrue(isinstance(response.context['form'], PollVoteForm))

        # and check the check the form is being used in the template,
        # by checking for the choice text
        self.assertIn(choice1.choice, response.content.replace('&#39;', "'"))
        self.assertIn(choice2.choice, response.content.replace('&#39;', "'"))

########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase
from django.utils import timezone
from polls.models import Choice, Poll

class PollModelTest(TestCase):
    def test_creating_a_new_poll_and_saving_it_to_the_database(self):
        # start by creating a new Poll object with its "question" and
        # "pub_date" attributes set
        poll = Poll()
        poll.question = "What's up?"
        poll.pub_date = timezone.now()

        # check we can save it to the database
        poll.save()

        # now check we can find it in the database again
        all_polls_in_database = Poll.objects.all()
        self.assertEquals(len(all_polls_in_database), 1)
        only_poll_in_database = all_polls_in_database[0]
        self.assertEquals(only_poll_in_database, poll)

        # and check that it's saved its two attributes: question and pub_date
        self.assertEquals(only_poll_in_database.question, "What's up?")
        self.assertEquals(only_poll_in_database.pub_date, poll.pub_date)


    def test_verbose_name_for_pub_date(self):
        for field in Poll._meta.fields:
            if field.name ==  'pub_date':
                self.assertEquals(field.verbose_name, 'Date published')


    def test_poll_objects_are_named_after_their_question(self):
        p = Poll()
        p.question = 'How is babby formed?'
        self.assertEquals(unicode(p), 'How is babby formed?')


    def test_poll_can_tell_you_its_total_number_of_votes(self):
        p = Poll(question='where',pub_date=timezone.now())
        p.save()
        c1 = Choice(poll=p,choice='here',votes=0)
        c1.save()
        c2 = Choice(poll=p,choice='there',votes=0)
        c2.save()

        self.assertEquals(p.total_votes(), 0)

        c1.votes = 1000
        c1.save()
        c2.votes = 22
        c2.save()
        self.assertEquals(p.total_votes(), 1022)



class ChoiceModelTest(TestCase):

    def test_creating_some_choices_for_a_poll(self):
        # start by creating a new Poll object
        poll = Poll()
        poll.question="What's up?"
        poll.pub_date = timezone.now()
        poll.save()

        # now create a Choice object
        choice = Choice()

        # link it with our Poll
        choice.poll = poll

        # give it some text
        choice.choice = "doin' fine..."

        # and let's say it's had some votes
        choice.votes = 3

        # save it
        choice.save()

        # try retrieving it from the database, using the poll object's reverse
        # lookup
        poll_choices = poll.choice_set.all()
        self.assertEquals(poll_choices.count(), 1)

        # finally, check its attributes have been saved
        choice_from_db = poll_choices[0]
        self.assertEquals(choice_from_db, choice)
        self.assertEquals(choice_from_db.choice, "doin' fine...")
        self.assertEquals(choice_from_db.votes, 3)


    def test_choice_defaults(self):
        choice = Choice()
        self.assertEquals(choice.votes, 0)


    def test_choice_can_calculate_its_own_percentage_of_votes(self):
        poll = Poll(question='who?', pub_date=timezone.now())
        poll.save()
        choice1 = Choice(poll=poll,choice='me',votes=2)
        choice1.save()
        choice2 = Choice(poll=poll,choice='you',votes=1)
        choice2.save()

        self.assertEquals(choice1.percentage(), 100 * 2 / 3.0)
        self.assertEquals(choice2.percentage(), 100 * 1 / 3.0)

        # also check 0-votes case
        choice1.votes = 0
        choice1.save()
        choice2.votes = 0
        choice2.save()
        self.assertEquals(choice1.percentage(), 0)
        self.assertEquals(choice2.percentage(), 0)

########NEW FILE########
__FILENAME__ = test_views
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone
from polls.models import Choice, Poll


class HomePageViewTest(TestCase):

    def test_root_url_shows_links_to_all_polls(self):
        # set up some polls
        poll1 = Poll(question='6 times 7', pub_date=timezone.now())
        poll1.save()
        poll2 = Poll(question='life, the universe and everything', pub_date=timezone.now())
        poll2.save()

        response = self.client.get('/')

        # check we've used the right template
        self.assertTemplateUsed(response, 'home.html')

        # check we've passed the polls to the template
        polls_in_context = response.context['polls']
        self.assertEquals(list(polls_in_context), [poll1, poll2])

        # check the poll names appear on the page
        self.assertIn(poll1.question, response.content)
        self.assertIn(poll2.question, response.content)

        # check the page also contains the urls to individual polls pages
        poll1_url = reverse('polls.views.poll', args=[poll1.id,])
        self.assertIn(poll1_url, response.content)
        poll2_url = reverse('polls.views.poll', args=[poll2.id,])
        self.assertIn(poll2_url, response.content)



class SinglePollViewTest(TestCase):

    def test_page_shows_poll_title_and_no_votes_message(self):
        # set up two polls, to check the right one is displayed
        poll1 = Poll(question='6 times 7', pub_date=timezone.now())
        poll1.save()
        poll2 = Poll(question='life, the universe and everything', pub_date=timezone.now())
        poll2.save()

        response = self.client.get('/poll/%d/' % (poll2.id, ))

        # check we've used the poll template
        self.assertTemplateUsed(response, 'poll.html')

        # check we've passed the right poll into the context
        self.assertEquals(response.context['poll'], poll2)

        # check the poll's question appears on the page
        self.assertIn(poll2.question, response.content)

        # check our 'no votes yet' message appears
        self.assertIn('No-one has voted on this poll yet', response.content)


    def test_view_shows_percentage_of_votes(self):
        # set up a poll with choices
        poll1 = Poll(question='6 times 7', pub_date=timezone.now())
        poll1.save()
        choice1 = Choice(poll=poll1, choice='42', votes=1)
        choice1.save()
        choice2 = Choice(poll=poll1, choice='The Ultimate Answer', votes=2)
        choice2.save()

        response = self.client.get('/poll/%d/' % (poll1.id, ))

        # check the percentages of votes are shown, sensibly rounded
        self.assertIn('33 %: 42', response.content)
        self.assertIn('67 %: The Ultimate Answer', response.content)

        # and that the 'no-one has voted' message is gone
        self.assertNotIn('No-one has voted', response.content)

    def test_view_shows_total_votes(self):
        # set up a poll with choices
        poll1 = Poll(question='6 times 7', pub_date=timezone.now())
        poll1.save()
        choice1 = Choice(poll=poll1, choice='42', votes=1)
        choice1.save()
        choice2 = Choice(poll=poll1, choice='The Ultimate Answer', votes=2)
        choice2.save()

        response = self.client.get('/poll/%d/' % (poll1.id, ))
        self.assertIn('3 votes', response.content)

        # also check we only pluralise "votes" if necessary. details!
        choice2.votes = 0
        choice2.save()
        response = self.client.get('/poll/%d/' % (poll1.id, ))
        self.assertIn('1 vote', response.content)
        self.assertNotIn('1 votes', response.content)


    def test_view_can_handle_votes_via_POST(self):
        # set up a poll with choices
        poll1 = Poll(question='6 times 7', pub_date=timezone.now())
        poll1.save()
        choice1 = Choice(poll=poll1, choice='42', votes=1)
        choice1.save()
        choice2 = Choice(poll=poll1, choice='The Ultimate Answer', votes=3)
        choice2.save()

        # set up our POST data - keys and values are strings
        post_data = {'vote': str(choice2.id)}

        # make our request to the view
        poll_url = '/poll/%d/' % (poll1.id,)
        response = self.client.post(poll_url, data=post_data)

        # retrieve the updated choice from the database
        choice_in_db = Choice.objects.get(pk=choice2.id)

        # check it's votes have gone up by 1
        self.assertEquals(choice_in_db.votes, 4)

        # always redirect after a POST - even if, in this case, we go back
        # to the same page.
        self.assertRedirects(response, poll_url)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from polls.forms import PollVoteForm
from polls.models import Choice, Poll

def home(request):
    context = {'polls': Poll.objects.all()}
    return render(request, 'home.html', context)


def poll(request, poll_id):
    if request.method == 'POST':
        choice = Choice.objects.get(id=request.POST['vote'])
        choice.votes += 1
        choice.save()
        return HttpResponseRedirect(reverse('polls.views.poll', args=[poll_id,]))
    poll = Poll.objects.get(pk=poll_id)
    form = PollVoteForm(poll=poll)
    return render(request, 'poll.html', {'poll': poll, 'form': form})

########NEW FILE########
