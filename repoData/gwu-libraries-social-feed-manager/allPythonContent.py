__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfm.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
from os.path import dirname, abspath

from django.core.urlresolvers import reverse_lazy

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

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
STATIC_ROOT = dirname(dirname(abspath(__file__))) + '/static'

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
SECRET_KEY = 'zb$q+qf-3rqtd4b)a^%y&lz-pgs&o3_7k-+-45!)i^d(q)+ma%'

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
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'sfm.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'sfm.wsgi.application'

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
    'django.contrib.admin',
    'django.contrib.humanize',
    'social_auth',
    'south',
    'ui',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
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


# BEGIN social_auth configuration (also INSTALLED_APP)
AUTHENTICATION_BACKENDS = (
    'social_auth.backends.twitter.TwitterBackend',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_ENABLED_BACKENDS = (
    'twitter',
)

TWITTER_API_ROOT = '/1.1'
TWITTER_USE_SECURE = True
TWITTER_CONSUMER_KEY = ''
TWITTER_CONSUMER_SECRET = ''
TWITTER_DEFAULT_USERNAME = ''

INTERNAL_IPS = ['127.0.0.1', 'localhost']

# BEGIN django-standard settings with not-default values
LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('home')
LOGOUT_REDIRECT_URL = reverse_lazy('home')

# A directory in which to store streams using "pullstream"
DATA_DIR = 'data'
# Autodetect SFM_ROOT as 'my location' minus trailing '/sfm/sfm'
SFM_ROOT = dirname(__file__)[:-8]

# How often to save polled data to the DATA_DIR
SAVE_INTERVAL_SECONDS = 60 * 15  # 15 minutes

# Be sure to create your own 'local_settings.py' file as described in README
try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
)

urlpatterns += patterns('ui.views',
    url(r'^$', 'home', name='home'),
    url(r'^logout/$', 'logout', name='logout'),
    url(r'^about/$', TemplateView.as_view(template_name='about.html'),
        name='about'),

    # twitter data patterns
    url(r'^search/$', 'search', name='search'),
    url(r'^tweets/$', 'tweets', name='tweets'),
    url(r'^users/alpha/$', 'users_alpha', name='users_alpha'),
    url(r'^twitter-user/(?P<name>[a-zA-Z0-9_]+)/$', 'twitter_user',
        name='twitter_user'),
    url(r'^twitter-user/(?P<name>[a-zA-Z0-9_]+).csv$', 'twitter_user_csv',
        name='twitter_user_csv'),
    url(r'^twitter-item/(?P<id>[0-9]+)/$', 'twitter_item',
        name='twitter_item'),
    url(r'^twitter-item/(?P<id>[0-9]+)/links/$', 'twitter_item_links',
        name='twitter_item_links'),

    url(r'', include('social_auth.urls')),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from ui import models as m


class TwitterFilterAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'is_active', 'words', 'people',
                    'locations']
    list_filter = ['is_active']
    search_fields = ['name', 'words', 'people', 'locations']
    fields = ('name', 'user', 'is_active', 'words', 'people', 'locations')
admin.site.register(m.TwitterFilter, TwitterFilterAdmin)


class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_active', 'uid', 'name', 'former_names',
                    'date_last_checked']
    list_filter = ['is_active']
    search_fields = ['name', 'former_names', 'uid']
    readonly_fields = ['uid', 'former_names', 'date_last_checked']
    filter_horizontal = ['sets']
admin.site.register(m.TwitterUser, TwitterUserAdmin)


class TwitterUserItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'twitter_user', 'date_published', 'twitter_id']
    list_filter = ['date_published']
    search_fields = ['twitter_id', 'item_text']
    readonly_fields = ['twitter_id', 'twitter_user', 'date_published',
                       'item_text', 'item_json', 'place', 'source']
admin.site.register(m.TwitterUserItem, TwitterUserItemAdmin)


class DurationSecondsFilter(admin.SimpleListFilter):
    title = 'duration (s)'
    parameter_name = 'duration_seconds'

    def lookups(self, request, model_admin):
        return (
            ('lt-0.25', '<= 0.25'),
            ('0.25-0.5', '0.25 - 0.5'),
            ('0.5-2', '0.5 - 2'),
            ('gt-2', '>= 2'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'lt-0.25':
            return queryset.filter(duration_seconds__lte=0.25)
        if self.value() == '0.25-0.5':
            return queryset.filter(duration_seconds__gt=0.25,
                                   duration_seconds__lte=0.5)
        if self.value() == '0.5-2':
            return queryset.filter(duration_seconds__gt=0.5,
                                   duration_seconds__lte=2)
        if self.value() == 'gt-2':
            return queryset.filter(duration_seconds__gt=2)


class TwitterUserItemUrlAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'final_status', 'duration_seconds',
                    'expanded_url', 'final_url']
    list_filter = ['date_checked', 'final_status', DurationSecondsFilter]
    search_fields = ['id', 'start_url', 'expanded_url', 'final_url']
    readonly_fields = ['item']
admin.site.register(m.TwitterUserItemUrl, TwitterUserItemUrlAdmin)


class TwitterUserSetAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'name', 'notes']
    search_fields = ['user', 'name']
admin.site.register(m.TwitterUserSet, TwitterUserSetAdmin)


class TwitterUserTimelineJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'date_started', 'date_finished', 'num_added']
    list_filter = ['date_started']
    search_fields = ['id']
    readonly_fields = ['date_started', 'date_finished', 'num_added']
admin.site.register(m.TwitterUserTimelineJob, TwitterUserTimelineJobAdmin)


class TwitterUserTimelineErrorAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'user', 'error']
    search_fields = ['job', 'user']
    readonly_fields = ['job', 'user', 'error']
admin.site.register(m.TwitterUserTimelineError, TwitterUserTimelineErrorAdmin)

########NEW FILE########
__FILENAME__ = createconf
import getpass
import os
import stat
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

from ui.models import TwitterFilter


class Command(BaseCommand):
    help = "create/update filterstream process config files for supervisord"
    option_list = BaseCommand.option_list + (
        make_option('--twitterfilter', action='store', default=None,
                    dest='twitterfilter', help='specify the filter rule id'),
        )

    def handle(self, *args, **options):
        twitter_filters = TwitterFilter.objects.filter(is_active=True)
        if options.get('twitterfilter', None):
            twitter_filters = twitter_filters.filter(
                id=options.get('twitterfilter'))
        projectroot = settings.SFM_ROOT
        if hasattr(settings, 'SUPERVISOR_PROCESS_USER'):
            processowner = settings.SUPERVISOR_PROCESS_USER
        else:
            processowner = getpass.getuser()
        for tf in twitter_filters:
            contents = "[program:twitterfilter-%s]" % tf.id + '\n' + \
                       "command=%s/ENV/bin/python " % projectroot + \
                       "%s/sfm/manage.py " % projectroot + \
                       "filterstream %s --save" % tf.id + '\n' \
                       "user=%s" % processowner + '\n' \
                       "autostart=true" + '\n' \
                       "autorestart=true" + '\n' \
                       "stderr_logfile=/var/log/sfm/" \
                       "twitterfilter-%s.err.log" % tf.id + '\n' \
                       "stdout_logfile=/var/log/sfm/" \
                       "twitterfilter-%s.out.log" % tf.id + '\n'
            filename = "twitterfilter-%s.conf" % tf.id
            file_path = "%s/sfm/sfm/supervisor.d/%s" % (projectroot, filename)
            # Remove any existing config file
            # we don't assume that the contents are up-to-date
            # (PATH settings may have changed, etc.)
            if os.path.exists(file_path):
                os.remove(file_path)
                print "Removed old configuration file for TwitterFilter %d" % \
                    tf.id

            fp = open(file_path, "wb")
            fp.write(contents)
            filestatus = os.stat(file_path)
            # do a chmod +x
            os.chmod(file_path, filestatus.st_mode | stat.S_IXUSR |
                     stat.S_IXGRP | stat.S_IXOTH)
            fp.close()
            print "Created configuration file for TwitterFilter %d" % \
                  tf.id

########NEW FILE########
__FILENAME__ = export_csv
import codecs
from optparse import make_option
import sys

from django.core.management.base import BaseCommand, CommandError

from ui.models import TwitterUser, TwitterUserSet, TwitterUserItem
from ui.utils import make_date_aware


class Command(BaseCommand):
    help = 'export data for a user or a set in csv'

    option_list = BaseCommand.option_list + (
        make_option('--start-date', action='store', default=None,
                    type='string', dest='start_date',
                    help='earliest date (YYYY-MM-DD) for export'),
        make_option('--end-date', action='store', default=None,
                    type='string', dest='end_date',
                    help='latest date (YYYY-MM-DD) for export'),
        make_option('--twitter-user', action='store', default=None,
                    type='string', dest='twitter_user',
                    help='username to export'),
        make_option('--set-name', action='store', default=None,
                    type='string', dest='set_name',
                    help='set name to export'),
    )

    def handle(self, *args, **options):
        # FIXME: why use options.get again and again?
        twitter_user = None
        user_set = None
        start_dt = None
        end_dt = None
        if options.get('twitter_user', False):
            try:
                twitter_user = TwitterUser.objects.get(
                    name=options.get('twitter_user'))
            except TwitterUser.DoesNotExist:
                raise CommandError('TwitterUser %s does not exist' %
                                   options.get('twitter_user'))
        elif options.get('set_name', False):
            user_set = None
            try:
                user_set = TwitterUserSet.objects.get(
                    name=options.get('set_name'))
            except TwitterUserSet.DoesNotExist:
                raise CommandError('TwitterUserSet %s does not exist' %
                                   options.get('set_name'))
        else:
            raise CommandError('please specify a twitter user or set name')

        if options.get('start_date', False):
            start_dt = make_date_aware(options.get('start_date'))
            if not start_dt:
                raise CommandError('dates must be in the format YYYY-MM-DD')
        else:
            start_dt = None
        if options.get('end_date', False):
            end_dt = make_date_aware(options.get('end_date'))
            if not end_dt:
                raise CommandError('dates must be in the format YYYY-MM-DD')
        else:
            end_dt = None
        if start_dt and end_dt:
            if end_dt < start_dt:
                raise CommandError('start date must be earlier than end date')

        if twitter_user:
            qs = twitter_user.items.all()
        elif user_set:
            qs = TwitterUserItem.objects.filter(
                twitter_user__sets__in=[user_set])

        if start_dt:
            qs = qs.filter(date_published__gte=start_dt)
        if end_dt:
            qs = qs.filter(date_published__lte=end_dt)

        # tweak for python 2.7 to avoid having to set PYTHONIOENCODING=utf8
        # in environment, see Graham Fawcett's comment/suggestion at:
        #   nedbatchelder.com/blog/200401/printing_unicode_from_python.html
        writer_class = codecs.getwriter('utf-8')
        sys.stdout = writer_class(sys.stdout, 'replace')
        for tui in qs:
            print '\t'.join(tui.csv)

########NEW FILE########
__FILENAME__ = fetch_tweets_by_id
import json
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

import tweepy
import sys
from ui.models import authenticated_api


class Command(BaseCommand):
    help = 'Fetch tweet data as JSON for a list of tweet ids' \

    option_list = BaseCommand.option_list + (
        make_option('--inputfile', action='store',
                    default=None, help='Path of the input file containing \
                            a list of tweet ids, each on a separate line'),
        make_option('--outputfile', action='store',
                    default=None, help='Path of the output file'),
    )

    def handle(self, *args, **options):
        if options['inputfile'] is None:
            print 'Please specify a valid input file using --inputfile'
            return

        infile = options['inputfile']
        fin = open(infile, 'r+')
        logfile = infile + '.log'
        flog = open(logfile, 'w')
        if options['outputfile']:
            outfile = options['outputfile']
            outstream = open(outfile, 'w')
        else:
            outstream = sys.stdout
        api = authenticated_api(username=settings.TWITTER_DEFAULT_USERNAME)
        errors_occurred = False
        for tweetidline in fin:
            try:
                status = api.get_status(id=tweetidline)
                json_value = json.dumps(status) + '\n\n'
                outstream.write(json_value)
            except tweepy.error.TweepError as e:
                content = 'Error: %s for the tweetid: %s' \
                          % (e, tweetidline) + '\n'
                flog.write(content)
                errors_occurred = True
        fin.close()
        flog.close()
        if options.get('outputfile', True):
            outstream.close()
        if errors_occurred:
            print 'Completed with errors. Please view the log file for details'

########NEW FILE########
__FILENAME__ = fetch_urls
import json
from optparse import make_option
import sys

import requests

from django.core.management.base import BaseCommand, CommandError

from ui.models import TwitterUser, TwitterUserItem, TwitterUserItemUrl
from ui.utils import make_date_aware


class Command(BaseCommand):
    help = 'fetch expanded urls for tweets with urls in text'

    option_list = BaseCommand.option_list + (
        make_option('--start-date', action='store', default=None,
                    type='string', dest='start_date',
                    help='earliest date (YYYY-MM-DD) for export'),
        make_option('--end-date', action='store', default=None,
                    type='string', dest='end_date',
                    help='latest date (YYYY-MM-DD) for export'),
        make_option('--twitter-user', action='store', default=None,
                    type='string', dest='twitter_user',
                    help='username to export'),
        make_option('--limit', action='store', default=0,
                    type='int', dest='limit',
                    help='max number of links to check'),
        make_option('--refetch', action='store_true', default=False,
                    help='refetch urls that have been fetched before'),
    )

    def handle(self, *args, **options):
        twitter_user = None
        start_dt = None
        end_dt = None
        if options['twitter_user']:
            try:
                twitter_user = TwitterUser.objects.get(
                    name=options['twitter_user'])
            except TwitterUser.DoesNotExist:
                raise CommandError('TwitterUser %s does not exist' %
                                   options['twitter_user'])

        if options['start_date']:
            start_dt = make_date_aware(options['start_date'])
            if not start_dt:
                raise CommandError('dates must be in the format YYYY-MM-DD')
        else:
            start_dt = None
        if options['end_date']:
            end_dt = make_date_aware(options['end_date'])
            if not end_dt:
                raise CommandError('dates must be in the format YYYY-MM-DD')
        else:
            end_dt = None
        if start_dt and end_dt:
            if end_dt < start_dt:
                raise CommandError('start date must be earlier than end date')

        if twitter_user:
            qs = twitter_user.items.all()
        else:
            qs = TwitterUserItem.objects.all()

        if start_dt:
            qs = qs.filter(date_published__gte=start_dt)
        if end_dt:
            qs = qs.filter(date_published__lte=end_dt)

        # be sure we move through the list in a consistent order
        qs = qs.order_by('date_published')

        session = requests.Session()
        count = 0
        for tui in qs:
            urls = []
            urls.extend(tui.tweet['entities']['urls'])
            if not urls:
                # use of entities.urls was spotty at first
                for u in tui.links:
                    urls.append({'url': u, 'expanded_url': u})
            for url in urls:
                # use filter because 0-to-many might already exist
                qs_tuiu = TwitterUserItemUrl.objects.filter(
                    item=tui,
                    start_url=url['url'],
                    expanded_url=url['expanded_url'])
                # if any already exist, and we're not refetching, move on
                if qs_tuiu.count() > 0 and \
                        not options['refetch']:
                    continue
                # otherwise, create a new one from scratch
                try:
                    r = session.get(url['url'], allow_redirects=True,
                                    stream=False)
                    r.close()
                except:
                    # TODO: consider trapping/recording
                    # requests.exceptions.ConnectionError,
                    # requests.exceptions.TooManyRedirects etc.
                    # and flagging records as having errored out
                    tuiu = TwitterUserItemUrl(
                        item=tui,
                        start_url=url['url'],
                        expanded_url=url['url'],
                        final_url=url['url'],
                        final_status=410)
                    tuiu.save()
                    continue
                tuiu = TwitterUserItemUrl(
                    item=tui,
                    start_url=url['url'],
                    expanded_url=url['expanded_url'],
                    history=json.dumps([(
                        req.status_code, req.url, dict(req.headers))
                        for req in r.history]),
                    final_url=r.url,
                    final_status=r.status_code,
                    final_headers=json.dumps(dict(r.headers)),
                    duration_seconds=r.elapsed.total_seconds())
                tuiu.save()
            count += 1
            if options['limit']:
                if count >= options['limit']:
                    sys.exit()

########NEW FILE########
__FILENAME__ = filterstream
from optparse import make_option
import traceback

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

import tweepy
from tweepy.streaming import StreamListener

from ui.models import RotatingFile, TwitterFilter


# NOTE: "filter" is both a python built-in function and the name of
# the twitter api / tweepy function we are invoking, so we use the
# variable name "twitter_filter" throughout to avoid possible confusion
# http://docs.python.org/2/library/functions.html#filter


class StdOutListener(StreamListener):

    def on_data(self, data):
        print data
        return True

    def on_error(self, status):
        print status


class Command(BaseCommand):
    help = 'Filter tweets based on active filters'

    option_list = BaseCommand.option_list + (
        make_option('--save', action='store_true', default=False,
                    dest='save', help='save the data to disk'),
        make_option('--verbose', action='store_true', default=False,
                    dest='verbose', help='print debugging info to stdout'),
        make_option('--dir', action='store', type='string',
                    default=settings.DATA_DIR, dest='dir',
                    help='directory for storing the data (default=%s)'
                    % settings.DATA_DIR),
        make_option('--interval', action='store', type='int',
                    default=settings.SAVE_INTERVAL_SECONDS, dest='interval',
                    help='how often to save data (default=%s)'
                    % settings.SAVE_INTERVAL_SECONDS),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("one argument is required: twitterfilter id") 
        try:
            twitter_filter = TwitterFilter.objects.get(id=int(args[0]))
        except:
            raise CommandError("unable to load that TwitterFilter") 
        if twitter_filter.is_active is False:
            raise CommandError("TwitterFilter is not active")

        words = set()
        people = set()
        locations = set()
        words.update(twitter_filter.words.strip().split(' ')
                     if twitter_filter.words else [])
        people.update(twitter_filter.people.strip().split(' ')
                      if twitter_filter.people else [])
        locations.update(twitter_filter.locations.strip().split(' ')
                         if twitter_filter.locations else [])
        if options.get('verbose', False):
            print 'track:', words
            print 'follow:', people
            print 'locations:', locations

        try:
            sa = twitter_filter.user.social_auth.all()[0]
            auth = tweepy.OAuthHandler(settings.TWITTER_CONSUMER_KEY,
                                       settings.TWITTER_CONSUMER_SECRET)
            auth.set_access_token(sa.tokens['oauth_token'],
                                  sa.tokens['oauth_token_secret'])
            filename_prefix = 'twitterfilter-%s' % args[0]
            if options.get('save', True):
                listener = RotatingFile(
                    filename_prefix=filename_prefix,
                    save_interval_seconds=options['interval'],
                    data_dir=options['dir'])
                stream = tweepy.Stream(auth, listener)
                stream.filter(track=words, follow=people, locations=locations)
            else:
                listener = StdOutListener()
                stream = tweepy.Stream(auth, listener)
                StdOutListener(stream.filter(
                    track=words, follow=people, locations=locations))
        except Exception, e:
            if options.get('verbose', False):
                print 'Disconnected from twitter:', e
                print traceback.print_exc()

########NEW FILE########
__FILENAME__ = organizedata
from django.conf import settings
from django.core.management.base import BaseCommand

import os
import shutil
import time


class Command(BaseCommand):
    help = 'move data from the data_dir into date-structured dirs'

    def handle(self, *args, **options):
        # for every file in the data dir, eg:
        #   DATA/PREFIX-2012-04-22T17:33:44Z.xml.gz
        # if the modification time is greater than
        #   (2 * settings.SAVE_INTERVAL_SECONDS):
        # make sure there's a directory under DATA names PREFIX
        # make sure there's a DATA/PREFIX/2012/04/22
        # move it there, without changing its name
        data_files = os.listdir(settings.DATA_DIR)
        for fname in data_files:
            data_file = '%s/%s' % (settings.DATA_DIR, fname)
            stat = os.stat(data_file)
            threshhold_seconds = 2 * settings.SAVE_INTERVAL_SECONDS
            if time.time() - stat.st_mtime < threshhold_seconds:
                continue
            # pull out the prefix, year, month, day, and hour
            try:
                # patterns:
                #   twitterfilter-2-2014-04-11T04:34:28Z.gz
                #   sample-2014-04-11T04:34:28Z.gz
                prefixed_date, t, time_ext = fname.partition('T')
                # get process name by truncating last 11 chars: -YYYY-MM-DD
                processname = prefixed_date[:-11]
                # get date as the last 10 chars: YYYY-MM-DD
                the_date = prefixed_date[-10:]
                year, month, day = the_date.split('-')
                hour, minute, seconds_ext = time_ext.split(':')
            except:
                # probably a prefix/directory
                continue
            subdir = '%s/%s/%s/%s/%s/%s' % (settings.DATA_DIR, processname,
                                            year, month, day, hour)
            try:
                os.stat(subdir)
            except:
                os.makedirs(subdir)
            try:
                shutil.copy2(data_file, subdir)
                os.remove(data_file)
                print 'moved %s to %s' % (data_file, subdir)
            except Exception, e:
                print 'unable to move %s' % data_file
                print e

########NEW FILE########
__FILENAME__ = populate_uids
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

from ui.models import authenticated_api
from ui.models import populate_uid
from ui.models import TwitterUser


class Command(BaseCommand):
    """
    Cycle through all the TwitterUsers we're tracking.  For each TwitterUser,
    if the uid==0 (default value, i.e. it hasn't been set yet), look the
    user up by name and populate the uid.
    """

    help = 'Fetch uids for twitter users by name, where uids ' \
           + 'are not populated.  Intended for migrating old ' \
           + 'databases prior to m2_001.'

    option_list = BaseCommand.option_list + (
        make_option('--user', dest='user',
                    default=None, help='Specific user to update'),
    )

    def handle(self, *args, **options):
        api = authenticated_api(username=settings.TWITTER_DEFAULT_USERNAME)
        qs_tweeps = TwitterUser.objects.filter(is_active=True)
        # if a username has been specified, limit to only that user
        if options.get('user', None):
            qs_tweeps = qs_tweeps.filter(name=options.get('user'))
        for tweep in qs_tweeps:
            print 'user: %s' % tweep.name
            # check user status, update twitter user name if it has changed
            populate_uid(tweep.name, api)

########NEW FILE########
__FILENAME__ = streamsample
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

import tweepy
from tweepy.streaming import StreamListener

from ui.models import RotatingFile


class StdOutListener(StreamListener):

    def on_data(self, data):
        print data
        return True

    def on_error(self, status):
        print status


class Command(BaseCommand):
    help = 'Show or save the Twitter sample/spritzer feed'

    option_list = BaseCommand.option_list + (
        make_option('--save', action='store_true', default=False,
                    dest='save', help='save the data to disk'),
        make_option('--dir', action='store', type='string',
                    default=settings.DATA_DIR, dest='dir',
                    help='directory for storing the data (default=%s)'
                    % settings.DATA_DIR),
        make_option('--interval', action='store', type='int',
                    default=settings.SAVE_INTERVAL_SECONDS, dest='interval',
                    help='how often to save data (default=%s)'
                    % settings.SAVE_INTERVAL_SECONDS),
    )

    def handle(self, *args, **options):
        user = User.objects.get(username=settings.TWITTER_DEFAULT_USERNAME)
        sa = user.social_auth.all()[0]
        auth = tweepy.OAuthHandler(settings.TWITTER_CONSUMER_KEY,
                                   settings.TWITTER_CONSUMER_SECRET)
        auth.set_access_token(sa.tokens['oauth_token'],
                              sa.tokens['oauth_token_secret'])
        if options.get('save', True):
            listener = RotatingFile(
                filename_prefix='streamsample',
                save_interval_seconds=options['interval'],
                data_dir=options['dir'])
            stream = tweepy.Stream(auth, listener)
            stream.sample()
        else:
            listener = StdOutListener()
            stream = tweepy.Stream(auth, listener)
            StdOutListener(stream.sample())

########NEW FILE########
__FILENAME__ = update_usernames
import datetime
import json
from optparse import make_option
import time

from django.conf import settings
from django.core.management.base import BaseCommand

import tweepy

from ui.models import authenticated_api
from ui.models import TwitterUser
from ui.utils import set_wait_time


class Command(BaseCommand):
    help = 'update any screen names that have changed'
    """
    Cycle through all the TwitterUsers we're tracking and update any
    screen names that have changed.

    see https://dev.twitter.com/docs/api/1.1/get/statuses/user_timeline
      for explanation of user_timeline call
    see https://dev.twitter.com/docs/working-with-timelines
      for explanation of max_id, since_id usage
    see also:
      https://dev.twitter.com/docs/error-codes-responses
      https://dev.twitter.com/docs/rate-limiting
    """

    option_list = BaseCommand.option_list + (
        make_option('--user', action='store', dest='user',
                    default=None, help='Specific user to fetch'),
    )

    def handle(self, *args, **options):
        api = authenticated_api(username=settings.TWITTER_DEFAULT_USERNAME)
        qs_tweeps = TwitterUser.objects.filter(is_active=True)
        if options.get('user', None):
            qs_tweeps = qs_tweeps.filter(name=options.get('user'))
        for tweep in qs_tweeps:
            print 'user: %s' % tweep.name
            # check user status, update twitter user name if it has changed
            if tweep.uid == 0:
                print 'uid has not been set yet - skipping.'
                continue
            try:
                user_status = api.get_user(id=tweep.uid)
                if user_status['screen_name'] != tweep.name:
                    print ' -- updating screen name to %s' % \
                        user_status['screen_name']
                    former_names = tweep.former_names
                    if not tweep.former_names:
                        former_names = '{}'
                    oldnames = json.loads(former_names)
                    oldnames[datetime.datetime.utcnow().strftime(
                        '%Y-%m-%dT%H:%M:%SZ')] = tweep.name
                    tweep.former_names = json.dumps(oldnames)
                    tweep.name = user_status['screen_name']
                    #TODO: Is this save unnecessary, since it gets saved below?
                    tweep.save()
            except tweepy.error.TweepError as e:
                print 'Error: %s' % e
                #go to the next tweep in the for loop
                continue
            finally:
                time.sleep(set_wait_time(api.last_response))

########NEW FILE########
__FILENAME__ = user_timeline
# Cycle through all the TwitterUsers we're tracking and fetch as many
# new items as possible. Attempt to backfill up to the limit twitter
# provides (currently 3200 statuses).  Obey timeline and rate limit laws
# like a good citizen.  For more info:
#
# see https://dev.twitter.com/docs/api/1.1/get/statuses/user_timeline
#   for explanation of user_timeline call
# see https://dev.twitter.com/docs/working-with-timelines
#   for explanation of max_id, since_id usage
# see also:
#   https://dev.twitter.com/docs/error-codes-responses
#   https://dev.twitter.com/docs/rate-limiting

import json
from optparse import make_option
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.db.utils import IntegrityError

import tweepy

from ui.models import authenticated_api, dt_aware_from_created_at
from ui.models import TwitterUser, TwitterUserItem
from ui.models import TwitterUserTimelineJob, TwitterUserTimelineError
from ui.utils import set_wait_time


class Command(BaseCommand):
    help = 'fetch status updates from twitter user timelines'

    option_list = BaseCommand.option_list + (
        make_option('--user', action='store', dest='user',
                    default=None, help='Specific user to fetch'),
    )

    def handle(self, *args, **options):
        api = authenticated_api(username=settings.TWITTER_DEFAULT_USERNAME)
        job = TwitterUserTimelineJob()
        job.save()
        qs_tweeps = TwitterUser.objects.filter(is_active=True)
        if options.get('user', None):
            qs_tweeps = qs_tweeps.filter(name=options.get('user'))
        else:
            # NOTE: randomizing here might be healthier when considering
            # possibility of multiple parallel jobs running and competing
            # for api calls but this is an instinctual call, not data-driven
            qs_tweeps = qs_tweeps.order_by('?')
        for tweep in qs_tweeps:
            print 'user: %s' % tweep.name
            # can't do this unless we have a twitter user_id stored
            if tweep.uid == 0:
                skipmsg = 'uid has not been set yet - skipping this ' + \
                          'user.  May need to run populate_uids if this ' + \
                          'is an old database.'
                print skipmsg
                error = TwitterUserTimelineError(job=job, user=tweep,
                                                 error=skipmsg)
                error.save()
                continue
            # now move on to determining first tweet id to get
            since_id = 1
            # set since_id if they have any statuses recorded
            if tweep.items.count() > 0:
                max_dict = tweep.items.all().aggregate(Max('twitter_id'))
                since_id = max_dict['twitter_id__max']
            max_id = 0
            # update their record (auto_now) as we're checking it now
            tweep.save()
            while True:
                # wait before next call no matter what;
                # use getattr() because api might be None the first time or
                # after errors
                time.sleep(set_wait_time(getattr(api, 'last_response', None)))
                job.save()
                stop = False
                try:
                    print 'since: %s' % (since_id)
                    if max_id:
                        print 'max: %s' % max_id
                        timeline = api.user_timeline(id=tweep.uid,
                                                     since_id=since_id,
                                                     max_id=max_id, count=200)
                    else:
                        timeline = api.user_timeline(id=tweep.uid,
                                                     since_id=since_id,
                                                     count=200)
                except tweepy.error.TweepError as e:
                    print 'ERROR: %s' % e
                    error = TwitterUserTimelineError(job=job, user=tweep,
                                                     error=e)
                    error.save()
                    timeline = []
                    break
                if len(timeline) == 0:
                    # Nothing new; stop for this user
                    stop = True
                new_status_count = 0
                for status in timeline:
                    # eg 'Mon Oct 15 20:15:12 +0000 2012'
                    dt_aware = dt_aware_from_created_at(status['created_at'])
                    try:
                        item, created = TwitterUserItem.objects.get_or_create(
                            twitter_user=tweep,
                            twitter_id=status['id'],
                            date_published=dt_aware,
                            item_text=status['text'],
                            item_json=json.dumps(status),
                            place=status['place'] or '',
                            source=status['source'])
                        if created:
                            max_id = item.twitter_id - 1
                            new_status_count += 1
                        else:
                            print 'skip: id %s' % item.id
                    except IntegrityError as ie:
                        print 'ERROR: %s' % ie
                        error = TwitterUserTimelineError(job=job, user=tweep,
                                                         error=ie)
                        error.save()
                print 'saved: %s item(s)' % new_status_count
                job.num_added += new_status_count
                # max new statuses per call is 200, so check for less than
                # a reasonable fraction of that to see if we should stop
                if new_status_count < 150:
                    print 'stop: < 150 new statuses'
                    stop = True
                if max_id < since_id:
                    # Got 'em all, stop for this user
                    print 'stop: max_id < since_id'
                    stop = True
                # Check response codes for issues
                response_status = api.last_response.status
                if response_status >= 400:
                    print 'error:', api.last_response.getheader('status')
                    error = TwitterUserTimelineError(job=job, user=tweep,
                                                     error=e)
                    error.save()
                    stop = True
                if stop:
                    break

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass


    def backwards(self, orm):
        pass


    models = {
        
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0002_auto__add_status
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Status'
        db.create_table('ui_status', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user_id', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('date_published', self.gf('django.db.models.fields.DateTimeField')()),
            ('avatar_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('status_id', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('summary', self.gf('django.db.models.fields.TextField')()),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('rule_tag', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('rule_match', self.gf('django.db.models.fields.TextField')(db_index=True)),
        ))
        db.send_create_signal('ui', ['Status'])


    def backwards(self, orm):
        
        # Deleting model 'Status'
        db.delete_table('ui_status')


    models = {
        'ui.status': {
            'Meta': {'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_status_avatar_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Status.avatar_url'
        db.alter_column('ui_status', 'avatar_url', self.gf('django.db.models.fields.TextField')())


    def backwards(self, orm):
        
        # Changing field 'Status.avatar_url'
        db.alter_column('ui_status', 'avatar_url', self.gf('django.db.models.fields.URLField')(max_length=200))


    models = {
        'ui.status': {
            'Meta': {'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0004_auto
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding index on 'Status', fields ['date_published']
        db.create_index('ui_status', ['date_published'])


    def backwards(self, orm):
        
        # Removing index on 'Status', fields ['date_published']
        db.delete_index('ui_status', ['date_published'])


    models = {
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0005_auto__add_trendweekly
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'TrendWeekly'
        db.create_table('ui_trendweekly', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('events', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('promoted_content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('ui', ['TrendWeekly'])


    def backwards(self, orm):
        
        # Deleting model 'TrendWeekly'
        db.delete_table('ui_trendweekly')


    models = {
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'ui.trendweekly': {
            'Meta': {'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_trendweekly_sequence_num
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'TrendWeekly.sequence_num'
        db.add_column('ui_trendweekly', 'sequence_num', self.gf('django.db.models.fields.SmallIntegerField')(default=1), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'TrendWeekly.sequence_num'
        db.delete_column('ui_trendweekly', 'sequence_num')


    models = {
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'sequence_num']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'sequence_num': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0007_auto__add_trenddaily
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'TrendDaily'
        db.create_table('ui_trenddaily', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('events', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('promoted_content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
            ('sequence_num', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
        ))
        db.send_create_signal('ui', ['TrendDaily'])


    def backwards(self, orm):
        
        # Deleting model 'TrendDaily'
        db.delete_table('ui_trenddaily')


    models = {
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'sequence_num']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'sequence_num': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'sequence_num']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'sequence_num': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0008_auto__del_field_trendweekly_sequence_num__del_field_trenddaily_sequenc
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'TrendWeekly.sequence_num'
        db.delete_column('ui_trendweekly', 'sequence_num')

        # Deleting field 'TrendDaily.sequence_num'
        db.delete_column('ui_trenddaily', 'sequence_num')

    def backwards(self, orm):
        # Adding field 'TrendWeekly.sequence_num'
        db.add_column('ui_trendweekly', 'sequence_num',
                      self.gf('django.db.models.fields.SmallIntegerField')(default=1),
                      keep_default=False)

        # Adding field 'TrendDaily.sequence_num'
        db.add_column('ui_trenddaily', 'sequence_num',
                      self.gf('django.db.models.fields.SmallIntegerField')(default=1),
                      keep_default=False)

    models = {
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0009_auto__add_rule
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Rule'
        db.create_table('ui_rule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('people', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('words', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('locations', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('ui', ['Rule'])

    def backwards(self, orm):
        # Deleting model 'Rule'
        db.delete_table('ui_rule')

    models = {
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0010_auto__add_twitteruser__add_twitteruseritem
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TwitterUser'
        db.create_table('ui_twitteruser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')(db_index=True)),
        ))
        db.send_create_signal('ui', ['TwitterUser'])

        # Adding model 'TwitterUserItem'
        db.create_table('ui_twitteruseritem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('twitter_user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ui.TwitterUser'])),
            ('twitter_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('date_published', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('item_text', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('item_json', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('place', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('source', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal('ui', ['TwitterUserItem'])

    def backwards(self, orm):
        # Deleting model 'TwitterUser'
        db.delete_table('ui_twitteruser')

        # Deleting model 'TwitterUserItem'
        db.delete_table('ui_twitteruseritem')

    models = {
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0011_auto__add_unique_twitteruseritem_twitter_url
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'TwitterUserItem', fields ['twitter_url']
        db.create_unique('ui_twitteruseritem', ['twitter_url'])

    def backwards(self, orm):
        # Removing unique constraint on 'TwitterUserItem', fields ['twitter_url']
        db.delete_unique('ui_twitteruseritem', ['twitter_url'])

    models = {
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.status': {
            'Meta': {'ordering': "['-date_published']", 'object_name': 'Status'},
            'avatar_url': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule_match': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'rule_tag': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'status_id': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'user_id': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0012_auto__del_status
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Status'
        db.delete_table('ui_status')

    def backwards(self, orm):
        # Adding model 'Status'
        db.create_table('ui_status', (
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('date_published', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('user_id', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('rule_match', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('avatar_url', self.gf('django.db.models.fields.TextField')()),
            ('rule_tag', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('status_id', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('summary', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('ui', ['Status'])

    models = {
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0013_auto__add_field_rule_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Rule.user'
        db.add_column('ui_rule', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['auth.User']),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Rule.user'
        db.delete_column('ui_rule', 'user_id')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0014_auto__add_field_twitteruser_date_last_checked__del_field_twitteruserit
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TwitterUser.date_last_checked'
        db.add_column('ui_twitteruser', 'date_last_checked',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2012, 10, 15, 0, 0), db_index=True, blank=True),
                      keep_default=False)

        # Deleting field 'TwitterUserItem.twitter_url'
        db.delete_column('ui_twitteruseritem', 'twitter_url')

        # Adding field 'TwitterUserItem.twitter_id'
        db.add_column('ui_twitteruseritem', 'twitter_id',
                      self.gf('django.db.models.fields.BigIntegerField')(default=0, unique=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'TwitterUser.date_last_checked'
        db.delete_column('ui_twitteruser', 'date_last_checked')

        # Adding field 'TwitterUserItem.twitter_url'
        db.add_column('ui_twitteruseritem', 'twitter_url',
                      self.gf('django.db.models.fields.URLField')(default='', max_length=200, unique=True),
                      keep_default=False)

        # Deleting field 'TwitterUserItem.twitter_id'
        db.delete_column('ui_twitteruseritem', 'twitter_id')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0015_auto__add_dailytwitteruseritemcount
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DailyTwitterUserItemCount'
        db.create_table('ui_dailytwitteruseritemcount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('twitter_user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ui.TwitterUser'])),
            ('date', self.gf('django.db.models.fields.DateField')(db_index=True, blank=True)),
            ('num_tweets', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('ui', ['DailyTwitterUserItemCount'])


    def backwards(self, orm):
        # Deleting model 'DailyTwitterUserItemCount'
        db.delete_table('ui_dailytwitteruseritemcount')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ui.dailytwitteruseritemcount': {
            'Meta': {'object_name': 'DailyTwitterUserItemCount'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tweets': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ui.TwitterUser']"})
        },
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0016_auto__add_field_twitteruser_is_active
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TwitterUser.is_active'
        db.add_column('ui_twitteruser', 'is_active',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'TwitterUser.is_active'
        db.delete_column('ui_twitteruser', 'is_active')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ui.dailytwitteruseritemcount': {
            'Meta': {'ordering': "['date']", 'object_name': 'DailyTwitterUserItemCount'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tweets': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'daily_counts'", 'to': "orm['ui.TwitterUser']"})
        },
        'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'ui.trenddaily': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendDaily'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.trendweekly': {
            'Meta': {'ordering': "['-date', 'name']", 'object_name': 'TrendWeekly'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'events': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'promoted_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0017_auto__del_trendweekly__del_trenddaily
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'TrendWeekly'
        db.delete_table(u'ui_trendweekly')

        # Deleting model 'TrendDaily'
        db.delete_table(u'ui_trenddaily')


    def backwards(self, orm):
        # Adding model 'TrendWeekly'
        db.create_table(u'ui_trendweekly', (
            ('name', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('promoted_content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
            ('events', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('ui', ['TrendWeekly'])

        # Adding model 'TrendDaily'
        db.create_table(u'ui_trenddaily', (
            ('name', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('promoted_content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
            ('events', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('ui', ['TrendDaily'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.dailytwitteruseritemcount': {
            'Meta': {'ordering': "['date']", 'object_name': 'DailyTwitterUserItemCount'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tweets': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'daily_counts'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0018_auto__add_twitteruserset__add_unique_twitteruserset_user_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TwitterUserSet'
        db.create_table(u'ui_twitteruserset', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sets', to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('notes', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal(u'ui', ['TwitterUserSet'])

        # Adding unique constraint on 'TwitterUserSet', fields ['user', 'name']
        db.create_unique(u'ui_twitteruserset', ['user_id', 'name'])

        # Adding M2M table for field sets on 'TwitterUser'
        db.create_table(u'ui_twitteruser_sets', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('twitteruser', models.ForeignKey(orm[u'ui.twitteruser'], null=False)),
            ('twitteruserset', models.ForeignKey(orm[u'ui.twitteruserset'], null=False))
        ))
        db.create_unique(u'ui_twitteruser_sets', ['twitteruser_id', 'twitteruserset_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'TwitterUserSet', fields ['user', 'name']
        db.delete_unique(u'ui_twitteruserset', ['user_id', 'name'])

        # Deleting model 'TwitterUserSet'
        db.delete_table(u'ui_twitteruserset')

        # Removing M2M table for field sets on 'TwitterUser'
        db.delete_table('ui_twitteruser_sets')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.dailytwitteruseritemcount': {
            'Meta': {'ordering': "['date']", 'object_name': 'DailyTwitterUserItemCount'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tweets': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'daily_counts'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0019_auto__add_field_twitteruser_former_names
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TwitterUser.former_names'
        db.add_column(u'ui_twitteruser', 'former_names',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TwitterUser.former_names'
        db.delete_column(u'ui_twitteruser', 'former_names')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.dailytwitteruseritemcount': {
            'Meta': {'ordering': "['date']", 'object_name': 'DailyTwitterUserItemCount'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tweets': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'daily_counts'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'former_names': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0020_auto__add_field_twitteruser_uid
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TwitterUser.uid'
        db.add_column(u'ui_twitteruser', 'uid',
                      self.gf('django.db.models.fields.BigIntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TwitterUser.uid'
        db.delete_column(u'ui_twitteruser', 'uid')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.dailytwitteruseritemcount': {
            'Meta': {'ordering': "['date']", 'object_name': 'DailyTwitterUserItemCount'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_tweets': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'daily_counts'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'former_names': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False', 'blank': 'True'}),
            'uid': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0021_auto__del_dailytwitteruseritemcount
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'DailyTwitterUserItemCount'
        db.delete_table(u'ui_dailytwitteruseritemcount')


    def backwards(self, orm):
        # Adding model 'DailyTwitterUserItemCount'
        db.create_table(u'ui_dailytwitteruseritemcount', (
            ('date', self.gf('django.db.models.fields.DateField')(blank=True, db_index=True)),
            ('num_tweets', self.gf('django.db.models.fields.IntegerField')(default=0)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('twitter_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='daily_counts', to=orm['ui.TwitterUser'])),
        ))
        db.send_create_signal(u'ui', ['DailyTwitterUserItemCount'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'former_names': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False', 'blank': 'True'}),
            'uid': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0022_auto__add_unique_twitteruser_uid
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'TwitterUser', fields ['uid']
        db.create_unique(u'ui_twitteruser', ['uid'])


    def backwards(self, orm):
        # Removing unique constraint on 'TwitterUser', fields ['uid']
        db.delete_unique(u'ui_twitteruser', ['uid'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'former_names': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False', 'blank': 'True'}),
            'uid': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0023_auto__add_twitterusertimelineerror__add_twitterusertimelinejob
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TwitterUserTimelineError'
        db.create_table(u'ui_twitterusertimelineerror', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(related_name='errors', to=orm['ui.TwitterUserTimelineJob'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ui.TwitterUser'])),
            ('error', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'ui', ['TwitterUserTimelineError'])

        # Adding model 'TwitterUserTimelineJob'
        db.create_table(u'ui_twitterusertimelinejob', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_started', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('date_finished', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, db_index=True, blank=True)),
            ('num_added', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'ui', ['TwitterUserTimelineJob'])


    def backwards(self, orm):
        # Deleting model 'TwitterUserTimelineError'
        db.delete_table(u'ui_twitterusertimelineerror')

        # Deleting model 'TwitterUserTimelineJob'
        db.delete_table(u'ui_twitterusertimelinejob')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.rule': {
            'Meta': {'object_name': 'Rule'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'former_names': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False', 'blank': 'True'}),
            'uid': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        },
        u'ui.twitterusertimelineerror': {
            'Meta': {'object_name': 'TwitterUserTimelineError'},
            'error': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'errors'", 'to': u"orm['ui.TwitterUserTimelineJob']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitterusertimelinejob': {
            'Meta': {'object_name': 'TwitterUserTimelineJob'},
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'date_started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_added': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = 0024_rename_Rule_to_TwitterFilter
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Renaming model 'Rule'
        db.rename_table(u'ui_rule', u'ui_twitterfilter')

    def backwards(self, orm):
        # Unrenaming model 'Rule'
        db.rename_table(u'ui_twitterfilter', u'ui_rule')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.twitterfilter': {
            'Meta': {'object_name': 'TwitterFilter'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'former_names': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False', 'blank': 'True'}),
            'uid': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        },
        u'ui.twitterusertimelineerror': {
            'Meta': {'object_name': 'TwitterUserTimelineError'},
            'error': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'errors'", 'to': u"orm['ui.TwitterUserTimelineJob']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitterusertimelinejob': {
            'Meta': {'object_name': 'TwitterUserTimelineJob'},
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'date_started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_added': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['ui']

########NEW FILE########
__FILENAME__ = 0025_auto__add_twitteruseritemurl
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TwitterUserItemUrl'
        db.create_table(u'ui_twitteruseritemurl', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='urls', to=orm['ui.TwitterUserItem'])),
            ('date_checked', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('start_url', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('expanded_url', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('history', self.gf('django.db.models.fields.TextField')(default='{}', blank=True)),
            ('final_url', self.gf('django.db.models.fields.TextField')(db_index=True)),
            ('final_status', self.gf('django.db.models.fields.IntegerField')(default=200, db_index=True)),
            ('final_headers', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('duration_seconds', self.gf('django.db.models.fields.FloatField')(default=0)),
        ))
        db.send_create_signal(u'ui', ['TwitterUserItemUrl'])


    def backwards(self, orm):
        # Deleting model 'TwitterUserItemUrl'
        db.delete_table(u'ui_twitteruseritemurl')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ui.twitterfilter': {
            'Meta': {'object_name': 'TwitterFilter'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locations': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'people': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'words': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'ui.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            'date_last_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'former_names': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'sets': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ui.TwitterUserSet']", 'symmetrical': 'False', 'blank': 'True'}),
            'uid': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'})
        },
        u'ui.twitteruseritem': {
            'Meta': {'object_name': 'TwitterUserItem'},
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_json': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'item_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'unique': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitteruseritemurl': {
            'Meta': {'object_name': 'TwitterUserItemUrl'},
            'date_checked': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'duration_seconds': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'expanded_url': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'final_headers': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'final_status': ('django.db.models.fields.IntegerField', [], {'default': '200', 'db_index': 'True'}),
            'final_url': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'history': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'urls'", 'to': u"orm['ui.TwitterUserItem']"}),
            'start_url': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        u'ui.twitteruserset': {
            'Meta': {'ordering': "['user', 'name']", 'unique_together': "(['user', 'name'],)", 'object_name': 'TwitterUserSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets'", 'to': u"orm['auth.User']"})
        },
        u'ui.twitterusertimelineerror': {
            'Meta': {'object_name': 'TwitterUserTimelineError'},
            'error': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'errors'", 'to': u"orm['ui.TwitterUserTimelineJob']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ui.TwitterUser']"})
        },
        u'ui.twitterusertimelinejob': {
            'Meta': {'object_name': 'TwitterUserTimelineJob'},
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'date_started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_added': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['ui']
########NEW FILE########
__FILENAME__ = models
import datetime
import gzip
import json
import re
import time

import requests
import tweepy
from tweepy.parsers import JSONParser
from tweepy.streaming import StreamListener

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db import models as m
from django.utils import timezone

from ui.utils import delete_conf_file, set_wait_time

RE_LINKS = re.compile(r'(https?://\S+)')
RE_MENTIONS = re.compile(u'(@[a-zA-z0-9_]+)')


def authenticated_api(username, api_root=None, parser=None):
    """Return an oauthenticated tweety API object."""
    auth = tweepy.OAuthHandler(settings.TWITTER_CONSUMER_KEY,
                               settings.TWITTER_CONSUMER_SECRET)
    try:
        user = User.objects.get(username__iexact=username)
        sa = user.social_auth.all()[0]
        auth.set_access_token(sa.tokens['oauth_token'],
                              sa.tokens['oauth_token_secret'])
        return tweepy.API(auth,
                          api_root=api_root or settings.TWITTER_API_ROOT,
                          parser=parser or JSONParser(),
                          secure=settings.TWITTER_USE_SECURE)
    except:
        return None


def dt_aware_from_created_at(created_at):
    ts = time.mktime(time.strptime(created_at, '%a %b %d %H:%M:%S +0000 %Y'))
    dt = datetime.datetime.fromtimestamp(ts)
    return timezone.make_aware(dt, timezone.utc)


class RotatingFile(StreamListener):

    def __init__(self, filename_prefix='data', save_interval_seconds=0,
                 data_dir='', compress=True):
        self.filename_prefix = filename_prefix
        self.save_interval_seconds = save_interval_seconds \
            or settings.SAVE_INTERVAL_SECONDS
        self.data_dir = data_dir or settings.DATA_DIR
        self.compress = compress
        self.start_time = time.time()
        self.fp = self._get_file()

    def on_data(self, data):
        self.fp.write('%s\n' % data)
        time_now = time.time()
        if time_now - self.start_time > self.save_interval_seconds:
            self.fp.close()
            self.fp = self._get_file()
            self.start_time = time_now

    def _get_file(self):
        if self.compress:
            return gzip.open(self._get_filename(), 'wb')
        else:
            return open(self._get_filename(), 'wb')

    def _get_filename(self):
        return '%s/%s-%s%s' % (self.data_dir, self.filename_prefix,
                               time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                             time.gmtime()),
                               '.gz' if self.compress else '')


class TwitterUserSet(m.Model):
    user = m.ForeignKey(User, related_name='sets')
    name = m.CharField(max_length=255)
    notes = m.TextField(blank=True, default='')

    def __unicode__(self):
        return '<Set: %s for user %s>' % (self.name, self.user.username)

    class Meta:
        ordering = ['user', 'name']
        unique_together = ['user', 'name']


class TwitterUser(m.Model):
    name = m.TextField(db_index=True)
    date_last_checked = m.DateTimeField(db_index=True, auto_now=True,
                                        help_text='Date twitter uid was \
                                                   last checked for \
                                                   username changes')
    uid = m.BigIntegerField(unique=True)
    former_names = m.TextField(default='{}', blank=True)
    is_active = m.BooleanField(default=True)
    sets = m.ManyToManyField(TwitterUserSet, blank=True)

    def __unicode__(self):
        return 'user %s (sfm id %s)' % (self.name, self.id)

    @property
    def counts(self):
        return ','.join([str(dc.num_tweets) for dc in self.daily_counts.all()])

    def clean(self):
        # if we are updating an existing TwitterUser
        # AND is_active=False
        if self.id is not None and self.is_active is False:
            return
        # else proceed because:
        #     either we are creating rather than updating
        #     OR we are updating with active=True

        # remove left whitespace, leading '@', and right whitespace
        self.name = self.name.lstrip().lstrip("@").rstrip()
        # look up user
        try:
            api = authenticated_api(username=settings.TWITTER_DEFAULT_USERNAME)
        except tweepy.error.TweepError as e:
            raise ValidationError('Could not connect to Twitter \
                                   API using configured credentials. \
                                   Error: %s' % e)
        if api is None:
            raise ValidationError('Could not connect to Twitter \
                                   API using configured credentials.')
        try:
            user_status = api.get_user(screen_name=self.name)
        except tweepy.error.TweepError as e:
            if "'code': 34" in e.reason:
                raise ValidationError('Twitter screen name \'%s\' was \
                                      not found.' % self.name)
            elif "'code': 32" in e.reason:
                raise ValidationError('Could not connect to Twitter \
                                       API using configured credentials.')
            else:
                raise ValidationError('Twitter returned the following \
                                      error: %s' % e.message)

        # check to prevent duplicates
        dups = TwitterUser.objects.filter(uid=user_status['id'])
        if self.id is not None:
            # if updating (vs. creating), remove myself
            dups = dups.exclude(id=self.id)
        if dups:
            raise ValidationError('TwitterUser uids must be unique. %s \
                                   is already present.' % user_status['id'])

        self.uid = user_status['id']
        # use the screen name from twitter (may be capitalized differently)
        self.name = user_status['screen_name']


def populate_uid(name, force=False, api=None):
    """
    For a TwitterUser, populate its uid based on its stored screen name,
    if uid==0 (default value, indicating it hasn't been set yet).
    if force==True, do it even if uid isn't 0
    Only do this for active users.

    see https://dev.twitter.com/docs/api/1.1/get/users/lookup
       for explanation of get_user call
    see https://dev.twitter.com/docs/working-with-timelines
       for explanation of max_id, since_id usage
    see also:
       https://dev.twitter.com/docs/error-codes-responses
       https://dev.twitter.com/docs/rate-limiting
    """

    if api is None:
        api = authenticated_api(username=settings.TWITTER_DEFAULT_USERNAME)
    qs_tweeps = TwitterUser.objects.filter(is_active=True, name=name)
    for tweep in qs_tweeps:
        if tweep.uid == 0 or force is True:
            try:
                user_status = api.get_user(screen_name=name)
                tweep.uid = user_status['id']
                tweep.save()
                print 'updated user \'%s\' uid to %d' % (name, tweep.uid)
            except tweepy.error.TweepError as e:
                print 'Failed to find user \'%s\'. Error: %s' % (name, e)
            finally:
                time.sleep(set_wait_time(api.last_response))


class TwitterUserItem(m.Model):
    twitter_user = m.ForeignKey(TwitterUser, related_name='items')
    twitter_id = m.BigIntegerField(unique=True, default=0)
    date_published = m.DateTimeField(db_index=True)
    item_text = m.TextField(default='', blank=True)
    item_json = m.TextField(default='', blank=True)
    place = m.TextField(default='', blank=True)
    source = m.TextField(default='', blank=True)

    def __unicode__(self):
        return '<useritem (%s)>' % (self.id)

    @property
    def twitter_url(self):
        return 'http://twitter.com/%s/status/%s' % (self.twitter_user.name,
                                                    self.twitter_id)

    @property
    def tweet(self):
        """Cache/return a parsed version of the json if available."""
        try:
            return self._parsed_tweet
        except:
            if self.item_json:
                self._parsed_tweet = json.loads(self.item_json)
            else:
                self._parsed_tweet = {}
            return self._parsed_tweet

    @property
    def text(self):
        try:
            return self.tweet['text']
        except:
            return self.item_text

    @property
    def mentions(self):
        return RE_MENTIONS.findall(self.text)

    @property
    def links(self):
        """A list of bare urls from tweet text, including twitpic etc.
        Note that TwitterUserItem.urls should return a manager for
        related TwitterUserItemUrls"""
        return RE_LINKS.findall(self.text)

    def is_retweet(self, strict=True):
        """A simple-minded attempt to catch RTs that aren't flagged
        by twitter proper with a retweeted_status.  This will catch
        some cases, others will slip through, e.g. quoted RTs in
        responses, or "RT this please".  Can't get them all. Likely
        heavily biased toward english."""
        if self.tweet.get('retweeted_status', False):
            return True
        if not strict:
            text_lower = self.tweet['text'].lower()
            if text_lower.startswith('rt '):
                return True
            if ' rt ' in text_lower:
                if not 'please rt' in text_lower \
                    and not 'pls rt' in text_lower \
                        and not 'plz rt' in text_lower:
                    return True
        return False

    def unshorten(self, url):
        """Don't try to guess; just resolve it, and follow 301s"""
        h = requests.get(url)
        stack = [i.url for i in h.history]
        stack.append(h.url)
        return stack

    @property
    def csv(self):
        """A list of values suitable for csv-ification"""
        r = [str(self.id),
             datetime.datetime.strftime(self.date_published,
                                        '%Y-%m-%dT%H:%M:%SZ'),
             datetime.datetime.strftime(self.date_published,
                                        '%m/%d/%Y'),
             self.tweet['id_str'],
             self.tweet['user']['screen_name'],
             str(self.tweet['user']['followers_count']),
             str(self.tweet['user']['friends_count']),
             str(self.tweet['retweet_count']),
             ', '.join([ht['text']
                        for ht in self.tweet['entities']['hashtags']]),
             self.tweet['in_reply_to_screen_name'] or '',
             ', '.join([m for m in self.mentions]),
             self.twitter_url,
             str(self.is_retweet()),
             str(self.is_retweet(strict=False)),
             self.tweet['text'].replace('\n', ' '),
             ]
        # only show up to two urls w/expansions
        for url in self.tweet['entities']['urls'][:2]:
            r.extend([url['url'], url['expanded_url']])
        return r


class TwitterUserItemUrl(m.Model):
    item = m.ForeignKey(TwitterUserItem, related_name='urls')
    date_checked = m.DateTimeField(auto_now_add=True)
    start_url = m.TextField(db_index=True)
    expanded_url = m.TextField(db_index=True)
    history = m.TextField(default='{}', blank=True)
    final_url = m.TextField(db_index=True)
    final_status = m.IntegerField(default=200, db_index=True)
    final_headers = m.TextField(blank=True)
    duration_seconds = m.FloatField(default=0)

    def __unicode__(self):
        return '<TwitterUserItemUrl %s>' % self.id


class TwitterUserTimelineJob(m.Model):
    date_started = m.DateTimeField(db_index=True, auto_now_add=True)
    date_finished = m.DateTimeField(db_index=True, auto_now=True)
    num_added = m.IntegerField(default=0)

    def __unicode__(self):
        return '<TwitterUserTimelineJob %s>' % self.id


class TwitterUserTimelineError(m.Model):
    job = m.ForeignKey(TwitterUserTimelineJob, related_name="errors")
    user = m.ForeignKey(TwitterUser)
    error = m.TextField(blank=True)


class TwitterFilter(m.Model):
    name = m.CharField(max_length=255, unique=True,
                       help_text="Name of this TwitterFilter")
    user = m.ForeignKey(User,
                        help_text="Account to use for authentication")
    is_active = m.BooleanField(default=False)
    people = m.TextField(blank=True,
                         help_text="""Space-separated list of user IDs \
for which tweets, retweets, and mentions will be captured. See the \
<a href="https://dev.twitter.com/docs/streaming-apis/parameters#follow" \
onclick="window.open(this.href); return false;">follow parameter \
documentation</a> for more information.""")
    words = m.TextField(blank=True,
                        help_text="""Space-separated keywords to track. See \
<a href="https://dev.twitter.com/docs/streaming-apis/parameters#track" \
onclick="window.open(this.href); return false;">the track parameter \
documentation</a> for more information.""")
    locations = m.TextField(blank=True,
                            help_text="""
Specifies a set of bounding boxes to track. See the \
<a href="https://dev.twitter.com/docs/streaming-apis/parameters#locations" \
onclick="window.open(this.href); return false;">locations parameter \
documentation</a> for more information.""")

    def __unicode__(self):
        return '%s' % self.id

    def clean(self):
        # if it's inactive, then do no validation
        if self.is_active is False:
            return

        # check against TWITTER_DEFAULT_USERNAME
        if self.user.username == settings.TWITTER_DEFAULT_USERNAME:
            raise ValidationError('''Streamsample is also configured to
                                     authenticate as \'%s\'.  Please select
                                     a different user or mark this filter as
                                     inactive.''' % self.user.username)

        # check against other active TwitterFilters' user.usernames
        conflicting_tfs = \
            TwitterFilter.objects.exclude(id=self.id).\
            filter(is_active=True, user__username=self.user.username)
        if conflicting_tfs:
            raise ValidationError('''Filter %d is active and is configured
                                     to authenticate as \'%s\'.
                                     Please select a different user or mark
                                     this filter as inactive.''' %
                                  (conflicting_tfs[0].id, self.user.username))


@receiver(post_save, sender=TwitterFilter)
def call_create_conf(sender, instance, **kwargs):
    if instance.is_active is True:
        call_command('createconf', twitterfilter=instance.id)
    else:
        delete_conf_file(instance.id)


@receiver(post_delete, sender=TwitterFilter)
def call_delete_conf(sender, instance, **kwargs):
    delete_conf_file(instance.id)

########NEW FILE########
__FILENAME__ = compress
#!/usr/bin/env python
import os
import optparse
import subprocess
import sys

here = os.path.dirname(__file__)

def main():
    usage = "usage: %prog [file1..fileN]"
    description = """With no file paths given this script will automatically
compress all jQuery-based files of the admin app. Requires the Google Closure
Compiler library and Java version 6 or later."""
    parser = optparse.OptionParser(usage, description=description)
    parser.add_option("-c", dest="compiler", default="~/bin/compiler.jar",
                      help="path to Closure Compiler jar file")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose")
    (options, args) = parser.parse_args()

    compiler = os.path.expanduser(options.compiler)
    if not os.path.exists(compiler):
        sys.exit("Google Closure compiler jar file %s not found. Please use the -c option to specify the path." % compiler)

    if not args:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        args = [os.path.join(here, f) for f in [
            "actions.js", "collapse.js", "inlines.js", "prepopulate.js"]]

    for arg in args:
        if not arg.endswith(".js"):
            arg = arg + ".js"
        to_compress = os.path.expanduser(arg)
        if os.path.exists(to_compress):
            to_compress_min = "%s.min.js" % "".join(arg.rsplit(".js"))
            cmd = "java -jar %s --js %s --js_output_file %s" % (compiler, to_compress, to_compress_min)
            if options.verbose:
                sys.stdout.write("Running: %s\n" % cmd)
            subprocess.call(cmd.split())
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sfm_extras
from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, '')


@register.assignment_tag
def assign_settings_value(name):
    return getattr(settings, name, '')

########NEW FILE########
__FILENAME__ = twitterize
import re

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import urlize
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='twitterize')
@stringfilter
def twitterize(value, autoescape=None):
    # Link URLs
    value = urlize(value, nofollow=False, autoescape=autoescape)
    # Link twitter usernames prefixed with @
    value = re.sub(r'(\s+|\A)@([a-zA-Z0-9\-_]*)\b',
                   r'\1<a href="https://twitter.com/\2">@\2</a>', value)
    # Link hash tags
    value = re.sub(r'(\s+|\A)#([a-zA-Z0-9\-_]*)\b',
                   r'\1<a href="https://twitter.com/search?q=%23\2">#\2</a>',
                   value)
    return mark_safe(value)
twitterize.is_safe = True
twitterize.needs_autoescape = True

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = utils
import datetime
import os
import time
import traceback

from django.utils import timezone

from django.conf import settings


# A little added cushion
WAIT_BUFFER_SECONDS = 2


def set_wait_time(last_response):
    """based on last tweepy api response, calculate a time buffer in
    seconds to wait before issuing next api call."""
    wait_time = 0
    try:
        remaining = int(last_response.getheader('x-rate-limit-remaining'))
        reset = int(last_response.getheader('x-rate-limit-reset'))
        reset_seconds = reset - int(time.time())
    except:
        remaining = reset_seconds = 1
    # the out-of-calls-for-this-window case
    if remaining == 0:
        return reset_seconds + WAIT_BUFFER_SECONDS
    else:
        wait_time = (reset_seconds / remaining) + WAIT_BUFFER_SECONDS
    # #22: saw some negative ratelimit-reset/wait_times
    # so cushion around that too
    while wait_time < WAIT_BUFFER_SECONDS:
        wait_time += WAIT_BUFFER_SECONDS
    return wait_time


def make_date_aware(date_str):
    """take a date in the format YYYY-MM-DD and return an aware date"""
    try:
        year, month, day = [int(x) for x in date_str.split('-')]
        dt = datetime.datetime(year, month, day)
        dt_aware = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt_aware
    except:
        print traceback.print_exc()
        return None


def delete_conf_file(twitterfilter):
    filename = "twitterfilter-%s.conf" % twitterfilter
    file_path = "%s/sfm/sfm/supervisor.d/%s" % (settings.SFM_ROOT, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

########NEW FILE########
__FILENAME__ = views
import codecs
import cStringIO
import csv

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.db import connection
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import TwitterUser, TwitterUserItem


def _paginate(request, paginator):
    page = request.GET.get('page', 1)
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)
    return page, items


@login_required
def home(request):
    qs_users = TwitterUser.objects.all()
    qs_users_alpha = qs_users.order_by('?')
    qs_items = TwitterUserItem.objects.order_by('-date_published')
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT DATE_TRUNC('day', date_published) AS day,
                   COUNT(*) AS item_count
            FROM ui_twitteruseritem
            WHERE date_published > NOW() - INTERVAL '1 month'
            GROUP BY 1
            ORDER BY day
            LIMIT 31 OFFSET 1;
            """)
        daily_counts = [[row[0].strftime('%Y-%m-%d'), int(row[1])]
                        for row in cursor.fetchall()]
        # Workaround for known "slow count(*)" issue
        cursor.execute("""
            SELECT reltuples FROM pg_class WHERE relname='ui_twitteruseritem'
            """)
        item_count = int(cursor.fetchone()[0])
    except:
        daily_counts = []
        item_count = 0
    return render(request, 'home.html', {
        'title': 'home',
        'users': qs_users,
        'users_alpha': qs_users_alpha[:25],
        'items': qs_items[:10],
        'item_count': item_count,
        'daily_counts': daily_counts,
    })


@login_required
def search(request):
    q = request.GET.get('q', '')
    title = ''
    if q:
        qs_users = TwitterUser.objects.filter(name__icontains=q)
        qs_users = qs_users.extra(select={'lower_name': 'lower(name)'})
        qs_users = qs_users.order_by('lower_name')
        title = 'search: "%s"' % q
    return render(request, 'search.html', {
        'title': title,
        'users': qs_users,
        'q': q,
    })


@login_required
def tweets(request):
    qs_tweets = TwitterUserItem.objects.order_by('-date_published')
    paginator = Paginator(qs_tweets, 50)
    page, tweets = _paginate(request, paginator)
    return render(request, 'tweets.html', {
        'title': 'all tweets, chronologically',
        'tweets': tweets,
        'paginator': paginator,
        'page': page,
    })


@login_required
def users_alpha(request):
    qs_users = TwitterUser.objects.all()
    qs_users = qs_users.extra(select={'lower_name': 'lower(name)'})
    qs_users = qs_users.order_by('lower_name')
    paginator = Paginator(qs_users, 25)
    page, users = _paginate(request, paginator)
    return render(request, 'users_alpha.html', {
        'title': 'all users, alphabetically',
        'users': users,
        'paginator': paginator,
        'page': page,
    })


@login_required
def twitter_user(request, name=''):
    user = get_object_or_404(TwitterUser, name=name)
    qs_tweets = user.items.order_by('-date_published')
    # grab a slightly older tweet to use for bio info
    if qs_tweets.count() > 20:
        recent_tweet = qs_tweets[20]
    elif qs_tweets.count() > 0:
        recent_tweet = qs_tweets[0]
    else:
        recent_tweet = None
    paginator = Paginator(qs_tweets, 50)
    page, tweets = _paginate(request, paginator)
    # fetch 90 days' worth of counts
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT DATE_TRUNC('day', date_published) AS day,
                   COUNT(*) AS item_count
                   FROM ui_twitteruseritem
            WHERE twitter_user_id = %s
                AND date_published > NOW() - INTERVAL '3 months'
            GROUP BY 1
            ORDER BY day
            LIMIT 91 OFFSET 1;
        """ % (user.id))
        daily_counts = [[row[0].strftime('%Y-%m-%d'), int(row[1])]
                        for row in cursor.fetchall()]
    except:
        daily_counts = []
    return render(request, 'twitter_user.html', {
        'title': 'twitter user: %s' % name,
        'user': user,
        'qs_tweets': qs_tweets,
        'tweets': tweets,
        'recent_tweet': recent_tweet,
        'daily_counts': daily_counts,
        'paginator': paginator,
        'page': page,
    })


@login_required
def twitter_user_csv(request, name=''):
    fieldnames = ['sfm_id', 'created_at', 'created_at_date', 'twitter_id',
                  'screen_name', 'followers_count', 'friends_count',
                  'retweet_count', 'hashtags', 'in_reply_to_screen_name',
                  'mentions', 'twitter_url', 'is_retweet_strict', 'is_retweet',
                  'text', 'url1', 'url1_expanded', 'url2', 'url2_expanded']
    user = get_object_or_404(TwitterUser, name=name)
    qs_tweets = user.items.order_by('-date_published')
    csvwriter = UnicodeCSVWriter()
    csvwriter.writerow(fieldnames)
    for t in qs_tweets:
        csvwriter.writerow(t.csv)
    response = StreamingHttpResponse(csvwriter.out(), content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="%s.csv"' % name
    return response


@login_required
def twitter_item(request, id=0):
    item = get_object_or_404(TwitterUserItem, id=int(id))
    return HttpResponse(item.item_json, content_type='application/json')


@login_required
def twitter_item_links(request, id=0):
    item = get_object_or_404(TwitterUserItem, id=int(id))
    unshortened = [item.unshorten(l) for l in item.links]
    return render(request, 'twitter_item_links.html', {
        'item': item,
        'unshortened': unshortened,
    })


def logout(request):
    auth.logout(request)
    return redirect(reverse('home'))


class UnicodeCSVWriter:

    def __init__(self, dialect=csv.excel, encoding='utf-8', **params):
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **params)
        self.encoding = encoding
        self.encoder = codecs.getincrementalencoder(self.encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode(self.encoding) for s in row])

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

    def out(self):
        return cStringIO.StringIO(self.queue.getvalue())

########NEW FILE########
