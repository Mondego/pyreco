__FILENAME__ = admin
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.comments.admin import CommentsAdmin
from django.utils.translation import ugettext_lazy as _

from django_comments_xtd import get_model as get_comment_model


XtdComment = get_comment_model()

class XtdCommentsAdmin(CommentsAdmin):
    list_display = ('thread_level', 'cid', 'name', 'content_type', 'object_pk', 'ip_address', 'submit_date', 'followup', 'is_public', 'is_removed')
    list_display_links = ('cid',)
    list_filter = ('content_type', 'is_public', 'is_removed', 'followup')
    fieldsets = (
        (None,          {'fields': ('content_type', 'object_pk', 'site')}),
        (_('Content'),  {'fields': ('user', 'user_name', 'user_email', 
                                    'user_url', 'comment', 'followup')}),
        (_('Metadata'), {'fields': ('submit_date', 'ip_address',
                                    'is_public', 'is_removed')}),
    )
    date_hierarchy = 'submit_date'
    ordering = ('thread_id', 'order')

    def thread_level(self, obj):
        rep = '|'
        if obj.level:
            rep += '-' * obj.level
            rep += " c%d to c%d" % (obj.id, obj.parent_id)
        else: 
            rep += " c%d" % obj.id
        return rep

    def cid(self, obj):
        return 'c%d' % obj.id

admin.site.register(XtdComment, XtdCommentsAdmin)

########NEW FILE########
__FILENAME__ = compat
# Ripped from Django1.5
import sys

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.importlib import import_module


def import_by_path(dotted_path, error_prefix=''):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImproperlyConfigured if something goes wrong.
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError:
        raise ImproperlyConfigured("%s%s doesn't look like a module path" % (
            error_prefix, dotted_path))
    try:
        module = import_module(module_path)
    except ImportError as e:
        msg = '%sError importing module %s: "%s"' % (
            error_prefix, module_path, e)
        six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg),
                    sys.exc_info()[2])
    try:
        attr = getattr(module, class_name)
    except AttributeError:
        raise ImproperlyConfigured('%sModule "%s" does not define a "%s" attribute/class' % (
            error_prefix, module_path, class_name))
    return attr


########NEW FILE########
__FILENAME__ = defaults
from __future__ import unicode_literals

COMMENT_MAX_LENGTH = 3000

# Extra key to salt the XtdCommentForm
COMMENTS_XTD_SALT = b""

# Whether comment posts should be confirmed by email
COMMENTS_XTD_CONFIRM_EMAIL = True

# Maximum Thread Level
COMMENTS_XTD_MAX_THREAD_LEVEL = 0

# Maximum Thread Level per app.model basis
COMMENTS_XTD_MAX_THREAD_LEVEL_BY_APP_MODEL = {}

# Default order to list comments in
COMMENTS_XTD_LIST_ORDER = ('thread_id', 'order')

# Form class to use
COMMENTS_XTD_FORM_CLASS = "django_comments_xtd.forms.XtdCommentForm"

# Model to use
COMMENTS_XTD_MODEL = "django_comments_xtd.models.XtdComment"

# Send HTML emails
COMMENTS_XTD_SEND_HTML_EMAIL = True

# Whether to send emails in separate threads or use the regular method.
# Set it to False to use a third-party app like django-celery-email or 
# your own celery app.
COMMENTS_XTD_THREADED_EMAILS = True

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from multiple.blog.models import Story, Quote


class StoryAdmin(admin.ModelAdmin):
    list_display  = ('title', 'publish', 'allow_comments')
    list_filter   = ('publish',)
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = ((None, 
                  {'fields': ('title', 'slug', 'body', 
                              'allow_comments', 'publish',)}),)

admin.site.register(Story, StoryAdmin)


class QuoteAdmin(admin.ModelAdmin):
    list_display  = ('title', 'publish', 'allow_comments')
    list_filter   = ('publish',)
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = ((None, 
                  {'fields': ('title', 'slug', 'quote', 'author', 'url_source',
                              'allow_comments', 'publish',)}),)

admin.site.register(Quote, QuoteAdmin)

########NEW FILE########
__FILENAME__ = models
#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.db import models
from django.db.models import permalink
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


class PublicManager(models.Manager):
    """Returns published articles that are not in the future."""
    
    def published(self):
        return self.get_query_set().filter(publish__lte=datetime.now())


@python_2_unicode_compatible
class Story(models.Model):
    """Story that accepts comments."""

    title = models.CharField('title', max_length=200)
    slug = models.SlugField('slug', unique_for_date='publish')
    body = models.TextField('body')
    allow_comments = models.BooleanField('allow comments', default=True)
    publish = models.DateTimeField('publish', default=datetime.now)

    objects = PublicManager()

    class Meta:
        db_table = 'stories'
        ordering = ('-publish',)
        verbose_name = _('story')
        verbose_name_plural = _('stories')

    def __str__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('blog-story-detail', None, 
                {'year': self.publish.year,
                 'month': int(self.publish.strftime('%m').lower()),
                 'day': self.publish.day,
                 'slug': self.slug})


@python_2_unicode_compatible
class Quote(models.Model):
    """Quote that accepts comments."""

    title = models.CharField('title', max_length=100)
    slug = models.SlugField('slug', max_length=255, unique=True)
    quote = models.TextField('quote')
    author = models.CharField('author', max_length=255)
    url_source = models.URLField('url source', blank=True, null=True)
    allow_comments = models.BooleanField('allow comments', default=True)
    publish = models.DateTimeField('publish', default=datetime.now)

    objects = PublicManager()

    class Meta:
        db_table = 'quotes'
        ordering = ('-publish',)
        verbose_name = _('quote')
        verbose_name_plural = _('quotes')

    def __str__(self):
        return '%s' % self.title

    @models.permalink
    def get_absolute_url(self):
        return ('blog-quote-detail', (), {'slug': self.slug})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic import ListView, DateDetailView, DetailView

from django_comments_xtd.models import XtdComment

from multiple.blog.models import Story, Quote
from multiple.blog.views import homepage, StoryDetailView, QuoteDetailView

urlpatterns = patterns('',
    url(r'^$', homepage, name='blog-index'),

    url(r'^stories$', 
        ListView.as_view(queryset=Story.objects.published()),
        name='blog-story-index'),

    url(r'^quotes$', 
        ListView.as_view(queryset=Quote.objects.published()),
        name='blog-quote-index'),

    url(r'^story/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$',
        StoryDetailView.as_view(),
        name='blog-story-detail'),

    url(r'^quote/(?P<slug>[-\w]+)/$', 
        QuoteDetailView.as_view(),
        name='blog-quote-detail'),

    # list all comments using pagination, newer first
    url(r'^comments$', 
        ListView.as_view(
            queryset=XtdComment.objects.for_app_models("blog.story", 
                                                       "blog.quote"), 
            template_name="django_comments_xtd/blog/comment_list.html",
            paginate_by=5),
        name='blog-comments'),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import DateDetailView, DetailView

from multiple.blog.models import Story, Quote


def homepage(request):
    stories = Story.objects.published()[:1]
    quotes = Quote.objects.published()[:5]
    return render_to_response("blog/homepage.html",
                              { "stories": stories, "quotes": quotes },
                              context_instance=RequestContext(request))


class StoryDetailView(DateDetailView):
    model = Story
    date_field = "publish"
    month_format = "%m"

    def get_context_data(self, **kwargs):
        context = super(StoryDetailView, self).get_context_data(**kwargs)
        context.update({'next': reverse('comments-xtd-sent')})
        return context
        

class QuoteDetailView(DetailView):
    model = Quote
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        context = super(QuoteDetailView, self).get_context_data(**kwargs)
        context.update({'next': reverse('comments-xtd-sent')})
        return context

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

sys.path.insert(0, '../../..') # parent of django_comments_xtd directory
sys.path.insert(0, '..') # demos directory

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    import imp
    try:
        imp.find_module('settings') # Assumed to be in the same directory.
    except ImportError:
        import sys
        sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "multiple.settings")
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from multiple.projects.models import Project, Release


class ReleaseInline(admin.StackedInline):
    model = Release
    extra = 1
    prepopulated_fields = {'slug': ('release_name',)}

class ProjectAdmin(admin.ModelAdmin):
    list_display  = ('project_name', 'is_active')
    search_fields = ('project_name', 'short_description')
    prepopulated_fields = {'slug': ('project_name',)}
    fieldsets = ((None, 
                  {'fields': ('project_name', 'slug',
                              'short_description',
                              'is_active',)}),)
    inlines = [ReleaseInline]

admin.site.register(Project, ProjectAdmin)

########NEW FILE########
__FILENAME__ = models
#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.db import models
from django.db.models import permalink
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


class ProjectManager(models.Manager):
    """Returns active projects."""
    
    def active(self):
        return self.get_query_set().filter(is_active=True)


@python_2_unicode_compatible
class Project(models.Model):
    """Project that accepts comments."""

    class Meta:
        db_table = 'projects'
        ordering = ('project_name',)

    project_name = models.CharField(blank=False, max_length=18)
    slug = models.SlugField(primary_key=True)
    short_description = models.CharField(blank=False, max_length=110)
    is_active = models.BooleanField()

    objects = ProjectManager()

    def __str__(self):
        return "%s" % (self.project_name)

    @models.permalink
    def get_absolute_url(self):
        return ('projects-project-detail', [self.slug])


class ReleaseManager(models.Manager):
    """Returns active published releases that are not in the future."""
    
    def published(self):
        return self.get_query_set().filter(publish__lte=datetime.now(), 
                                           is_active=True)


@python_2_unicode_compatible
class Release(models.Model):
    """Project evolution is divided in releases."""

    class Meta:
        db_table = 'releases'
        unique_together = ('project', 'slug',)
        ordering = ('project', 'release_name',)

    project = models.ForeignKey(Project)
    release_name = models.CharField(blank=False, max_length=18)
    slug = models.SlugField(max_length=255)
    release_date = models.DateTimeField(default=datetime.today)
    body = models.TextField(max_length=2048, help_text=_("Release description"))
    is_active = models.BooleanField()
    allow_comments = models.BooleanField(default=True)
    
    def __str__(self):
        return "%s/%s" % (self.project.project_name, self.release_name)

    @models.permalink
    def get_absolute_url(self):
        return ('projects-release-detail', [self.project.slug, self.slug])

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
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic import ListView, DateDetailView, DetailView

from multiple.projects import views

urlpatterns = patterns('',
    url(r'^$', 
        views.ProjectsView.as_view(), 
        name='projects-index'),

    url(r'^(?P<slug>[-\w]+)/$', 
        views.ProjectDetailView.as_view(),
        name='projects-project-detail'),

    url(r'^(?P<project_slug>[-\w]+)/(?P<release_slug>[-\w]+)/$', 
        views.ReleaseDetailView.as_view(),
        name='projects-release-detail'),
)


########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import DetailView, ListView

from multiple.projects.models import Project, Release


class ProjectsView(ListView):
    queryset = Project.objects.filter(is_active=True)
    template_name = "projects/homepage.html"

    def get_context_data(self, **kwargs):
        context = super(ProjectsView, self).get_context_data(**kwargs)

        items = []
        for project in self.object_list:
            try:
                last_published_release = project.release_set.filter(
                    is_active=True).order_by("-release_date")[0]
            except IndexError:
                continue
            else:
                items.append({"project": project, 
                              "release": last_published_release})

        if len(items):
            items.sort(key=lambda item: item['release'].release_date, 
                       reverse=True)

        context['items'] = items
        return context


class ProjectDetailView(DetailView):
    model = Project

    def get_context_data(self, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        context['release_list'] = []
        for release in self.get_object().release_set.filter(is_active=True).order_by("-release_date"):
            context['release_list'].append(release)
        return context


class ReleaseDetailView(DetailView):
    model = Release

    def get_object(self, queryset=None):
        project_pk = self.kwargs.get('project_slug', None)
        release_slug = self.kwargs.get('release_slug', None)
        try:
            obj = Release.objects.get(project=project_pk, slug=release_slug)
        except ObjectDoesNotExist:
            raise Http404(_("No releases found matching the query"))
        return obj

    def get_context_data(self, **kwargs):
        context = super(ReleaseDetailView, self).get_context_data(**kwargs)
        context.update({'next': reverse('comments-xtd-sent')})
        return context
        

########NEW FILE########
__FILENAME__ = settings
#-*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

PRJ_PATH = os.path.abspath(os.path.curdir)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Alice Bloggs', 'alice@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.sqlite3', 
        'NAME':     'django_comments_xtd_demo.db',
        'USER':     '', 
        'PASSWORD': '', 
        'HOST':     '', 
        'PORT':     '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Brussels'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PRJ_PATH, "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
# ADMIN_MEDIA_PREFIX = '/media/'

STATIC_ROOT = os.path.join(PRJ_PATH, "static")
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #os.path.join(PRJ_PATH, "static"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = 'v2824l&2-n+4zznbsk9c-ap5i)b3e8b+%*a=dxqlahm^%)68jn'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.comments',

    'multiple.blog',
    'multiple.projects',
    'django_comments_xtd',
    'django_markup',
    'south',
)

# EMAIL_HOST          = "smtp.gmail.com" 
# EMAIL_PORT          = "587"
# EMAIL_HOST_USER     = "username@gmail.com"
# EMAIL_HOST_PASSWORD = ""
# EMAIL_USE_TLS       = True # Yes for Gmail
# DEFAULT_FROM_EMAIL  = "Alice Bloggs <alice@example.com>"
# SERVER_EMAIL        = DEFAULT_FROM_EMAIL

# Fill in actual EMAIL settings above, and comment out the 
# following line to let this django demo sending emails
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

COMMENTS_APP = "django_comments_xtd"
COMMENTS_XTD_CONFIRM_EMAIL = False
COMMENTS_XTD_SALT = b"es-war-einmal-una-bella-princesa-in-a-beautiful-castle"
COMMENTS_XTD_MAX_THREAD_LEVEL = 3
COMMENTS_XTD_MAX_THREAD_LEVEL_BY_APP_MODEL = {'projects.release': 1}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.comments.feeds import LatestCommentFeed


admin.autodiscover()

urlpatterns = patterns('multiple.views',
    url(r'^admin/',           include(admin.site.urls)),
    url(r'^blog/',            include('multiple.blog.urls')),
    url(r'^projects/',        include('multiple.projects.urls')),
    url(r'^comments/',        include('django_comments_xtd.urls')),
    url(r'^$',                'homepage_v',        name='homepage'),
    url(r'^feeds/comments/$', LatestCommentFeed(), name='comments-feed'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response as render
from django.template import RequestContext


def homepage_v(request):
    return render("homepage.html", context_instance=RequestContext(request))

def contact_v(request):
    return render("contact.html", context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from simple.articles.models import Article

class ArticleAdmin(admin.ModelAdmin):
    list_display  = ('title', 'publish', 'allow_comments')
    list_filter   = ('publish',)
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = ((None, 
                  {'fields': ('title', 'slug', 'body', 
                              'allow_comments', 'publish',)}),)

admin.site.register(Article, ArticleAdmin)

########NEW FILE########
__FILENAME__ = models
#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.db import models
from django.db.models import permalink
from django.utils.encoding import python_2_unicode_compatible


class PublicManager(models.Manager):
    """Returns published articles that are not in the future."""
    
    def published(self):
        return self.get_query_set().filter(publish__lte=datetime.now())


@python_2_unicode_compatible
class Article(models.Model):
    """Article, that accepts comments."""

    title = models.CharField('title', max_length=200)
    slug = models.SlugField('slug', unique_for_date='publish')
    body = models.TextField('body')
    allow_comments = models.BooleanField('allow comments', default=True)
    publish = models.DateTimeField('publish', default=datetime.now)

    objects = PublicManager()

    class Meta:
        db_table = 'simple_articles'
        ordering = ('-publish',)

    def __str__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('articles-article-detail', None, 
                {'year': self.publish.year,
                 'month': int(self.publish.strftime('%m').lower()),
                 'day': self.publish.day,
                 'slug': self.slug})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic import ListView, DateDetailView

from simple.articles.models import Article
from simple.articles.views import ArticleDetailView

urlpatterns = patterns('',
    url(r'^$', 
        ListView.as_view(queryset=Article.objects.published()),
        name='articles-index'),

    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$',
        ArticleDetailView.as_view(), 
        name='articles-article-detail'),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.views.generic import DateDetailView

from simple.articles.models import Article


class ArticleDetailView(DateDetailView):
    model = Article
    date_field = "publish"
    month_format = "%m"

    def get_context_data(self, **kwargs):
        context = super(ArticleDetailView, self).get_context_data(**kwargs)
        context.update({'next': reverse('comments-xtd-sent')})
        return context

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

sys.path.insert(0, '../../..') # parent of django_comments_xtd directory
sys.path.insert(0, '..') # demos directory

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    import imp
    try:
        imp.find_module('settings') # Assumed to be in the same directory.
    except ImportError:
        import sys
        sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simple.settings")
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
#-*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

PRJ_PATH = os.path.abspath(os.path.curdir)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Alice Bloggs', 'alice@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.sqlite3', 
        'NAME':     'django_comments_xtd_demo.db',
        'USER':     '', 
        'PASSWORD': '', 
        'HOST':     '', 
        'PORT':     '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Brussels'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PRJ_PATH, "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
# ADMIN_MEDIA_PREFIX = '/media/'

STATIC_ROOT = os.path.join(PRJ_PATH, "static")
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #os.path.join(PRJ_PATH, "static"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = 'v2824l&2-n+4zznbsk9c-ap5i)b3e8b+%*a=dxqlahm^%)68jn'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'simple.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.comments',

    'simple.articles',
    'django_comments_xtd',
    'south',
)

# EMAIL_HOST          = "smtp.gmail.com" 
# EMAIL_PORT          = "587"
# EMAIL_HOST_USER     = "username@gmail.com"
# EMAIL_HOST_PASSWORD = ""
# EMAIL_USE_TLS       = True # Yes for Gmail
# DEFAULT_FROM_EMAIL  = "Alice Bloggs <alice@example.com>"
# SERVER_EMAIL        = DEFAULT_FROM_EMAIL

# Fill in actual EMAIL settings above, and comment out the 
# following line to let this django demo sending emails
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

COMMENTS_APP = "django_comments_xtd"
COMMENTS_XTD_CONFIRM_EMAIL = False # Set to True to request confirmations
COMMENTS_XTD_SALT = b"es-war-einmal-una-bella-princesa-in-a-beautiful-castle"
#COMMENTS_XTD_MAX_THREAD_LEVEL = 0 # Default value
COMMENTS_XTD_THREADED_EMAILS = False # default to True, use False to allow
                                     # other backend (say Celery based) send
                                     # your emails.

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.comments.feeds import LatestCommentFeed
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


admin.autodiscover()

urlpatterns = patterns('simple.views',
    url(r'^admin/',           include(admin.site.urls)),
    url(r'^articles/',        include('simple.articles.urls')),
    url(r'^comments/',        include('django_comments_xtd.urls')),
    url(r'^$',                'homepage_v',        name='homepage'),
    url(r'^feeds/comments/$', LatestCommentFeed(), name='comments-feed'),    
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response as render
from django.template import RequestContext


def homepage_v(request):
    return render("homepage.html", context_instance=RequestContext(request))

def contact_v(request):
    return render("contact.html", context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from simple_threads.articles.models import Article

class ArticleAdmin(admin.ModelAdmin):
    list_display  = ('title', 'publish', 'allow_comments')
    list_filter   = ('publish',)
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = ((None, 
                  {'fields': ('title', 'slug', 'body', 
                              'allow_comments', 'publish',)}),)

admin.site.register(Article, ArticleAdmin)

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from datetime import datetime

from django.db import models
from django.db.models import permalink
from django.utils.encoding import python_2_unicode_compatible


class PublicManager(models.Manager):
    """Returns published articles that are not in the future."""
    
    def published(self):
        return self.get_query_set().filter(publish__lte=datetime.now())


@python_2_unicode_compatible
class Article(models.Model):
    """Article, that accepts comments."""

    title = models.CharField('title', max_length=200)
    slug = models.SlugField('slug', unique_for_date='publish')
    body = models.TextField('body')
    allow_comments = models.BooleanField('allow comments', default=True)
    publish = models.DateTimeField('publish', default=datetime.now)

    objects = PublicManager()

    class Meta:
        db_table = 'simple_threads_articles'
        ordering = ('-publish',)

    def __str__(self):
        return self.title

    @permalink
    def get_absolute_url(self):
        return ('articles-article-detail', None, 
                {'year': self.publish.year,
                 'month': int(self.publish.strftime('%m').lower()),
                 'day': self.publish.day,
                 'slug': self.slug})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic import ListView, DateDetailView

from simple_threads.articles.models import Article
from simple_threads.articles.views import ArticleDetailView

urlpatterns = patterns('',
    url(r'^$', 
        ListView.as_view(queryset=Article.objects.published()),
        name='articles-index'),

    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$',
        ArticleDetailView.as_view(), 
        name='articles-article-detail'),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.views.generic import DateDetailView

from simple_threads.articles.models import Article


class ArticleDetailView(DateDetailView):
    model = Article
    date_field = "publish"
    month_format = "%m"

    def get_context_data(self, **kwargs):
        context = super(ArticleDetailView, self).get_context_data(**kwargs)
        context.update({'next': reverse('comments-xtd-sent')})
        return context

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

sys.path.insert(0, '../../..') # parent of django_comments_xtd directory
sys.path.insert(0, '..') # demos directory

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    import imp
    try:
        imp.find_module('settings') # Assumed to be in the same directory.
    except ImportError:
        import sys
        sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simple_threads.settings")
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
#-*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

PRJ_PATH = os.path.abspath(os.path.curdir)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Alice Bloggs', 'alice@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.sqlite3', 
        'NAME':     'django_comments_xtd_demo.db',
        'USER':     '', 
        'PASSWORD': '', 
        'HOST':     '', 
        'PORT':     '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Brussels'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PRJ_PATH, "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
# ADMIN_MEDIA_PREFIX = '/media/'

STATIC_ROOT = os.path.join(PRJ_PATH, "static")
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #os.path.join(PRJ_PATH, "static"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = 'v2824l&2-n+4zznbsk9c-ap5i)b3e8b+%*a=dxqlahm^%)68jn'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.comments',

    'simple_threads.articles',
    'django_comments_xtd',
#    'south',
)

# EMAIL_HOST          = "smtp.gmail.com" 
# EMAIL_PORT          = "587"
# EMAIL_HOST_USER     = "username@gmail.com"
# EMAIL_HOST_PASSWORD = ""
# EMAIL_USE_TLS       = True # Yes for Gmail
# DEFAULT_FROM_EMAIL  = "Alice Bloggs <alice@example.com>"
# SERVER_EMAIL        = DEFAULT_FROM_EMAIL

# Fill in actual EMAIL settings above, and comment out the 
# following line to let this django demo sending emails
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

COMMENTS_APP = "django_comments_xtd"
COMMENTS_XTD_CONFIRM_EMAIL = True
COMMENTS_XTD_SALT = b"es-war-einmal-una-bella-princesa-in-a-beautiful-castle"
COMMENTS_XTD_MAX_THREAD_LEVEL = 2


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.comments.feeds import LatestCommentFeed


admin.autodiscover()

urlpatterns = patterns('views',
    url(r'^admin/',           include(admin.site.urls)),
    url(r'^articles/',        include('simple_threads.articles.urls')),
    url(r'^comments/',        include('django_comments_xtd.urls')),
    url(r'^$',                'homepage_v',        name='homepage'),
    url(r'^feeds/comments/$', LatestCommentFeed(), name='comments-feed'),    
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response as render
from django.template import RequestContext


def homepage_v(request):
    return render("homepage.html", context_instance=RequestContext(request))

def contact_v(request):
    return render("contact.html", context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.comments.forms import CommentForm
from django.utils.translation import ugettext_lazy as _
from django_comments_xtd.conf import settings
from django_comments_xtd.models import TmpXtdComment


class XtdCommentForm(CommentForm):
    followup = forms.BooleanField(
        required=False, label=_("Notify me of follow up comments via email"))
    reply_to = forms.IntegerField(required=True, initial=0, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        comment = kwargs.pop("comment", None)
        if comment:
            initial = kwargs.pop("initial", {})
            initial.update({"reply_to": comment.pk})
            kwargs["initial"] = initial
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields['name'] = forms.CharField(
            widget=forms.TextInput(attrs={'placeholder':_('name')}))
        self.fields['email'] = forms.EmailField(
            label=_("Email"), help_text=_("Required for comment verification"),
            widget=forms.TextInput(attrs={'placeholder':_('email')})
            )
        self.fields['url'] = forms.URLField(
            required=False,
            widget=forms.TextInput(attrs={'placeholder':_('website')}))
        self.fields['comment'] = forms.CharField(
            widget=forms.Textarea(attrs={'placeholder':_('comment')}), 
            max_length=settings.COMMENT_MAX_LENGTH)

    def get_comment_model(self):
        return TmpXtdComment

    def get_comment_create_data(self):
        data = super(CommentForm, self).get_comment_create_data()
        data.update({'thread_id': 0, 'level': 0, 'order': 1,
                     'parent_id': self.cleaned_data['reply_to'],
                     'followup': self.cleaned_data['followup']})
        if settings.COMMENTS_XTD_CONFIRM_EMAIL:
            # comment must be verified before getting approved
            data['is_public'] = False
        return data

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'XtdComment'
        db.create_table('django_comments_xtd_xtdcomment', (
            ('comment_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['comments.Comment'], unique=True, primary_key=True)),
            ('followup', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('django_comments_xtd', ['XtdComment'])


    def backwards(self, orm):
        # Deleting model 'XtdComment'
        db.delete_table('django_comments_xtd_xtdcomment')


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
        'comments.comment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'Comment', 'db_table': "'django_comments'"},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '3000'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_type_set_for_comment'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_pk': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'comment_comments'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'user_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'django_comments_xtd.xtdcomment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'XtdComment', '_ormbases': ['comments.Comment']},
            'comment_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['comments.Comment']", 'unique': 'True', 'primary_key': 'True'}),
            'followup': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['django_comments_xtd']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_xtdcomment_thread__add_field_xtdcomment_parent__add_fi
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'XtdComment.thread_id'
        db.add_column('django_comments_xtd_xtdcomment', 'thread_id',
                      self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True),
                      keep_default=False)

        # Adding field 'XtdComment.parent_id'
        db.add_column('django_comments_xtd_xtdcomment', 'parent_id',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'XtdComment.level'
        db.add_column('django_comments_xtd_xtdcomment', 'level',
                      self.gf('django.db.models.fields.SmallIntegerField')(default=0),
                      keep_default=False)

        # Adding field 'XtdComment.order'
        db.add_column('django_comments_xtd_xtdcomment', 'order',
                      self.gf('django.db.models.fields.IntegerField')(default=1, db_index=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'XtdComment.thread_id'
        db.delete_column('django_comments_xtd_xtdcomment', 'thread_id')

        # Deleting field 'XtdComment.parent_id'
        db.delete_column('django_comments_xtd_xtdcomment', 'parent_id')

        # Deleting field 'XtdComment.level'
        db.delete_column('django_comments_xtd_xtdcomment', 'level')

        # Deleting field 'XtdComment.order'
        db.delete_column('django_comments_xtd_xtdcomment', 'order')


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
        'comments.comment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'Comment', 'db_table': "'django_comments'"},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '3000'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_type_set_for_comment'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_pk': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'comment_comments'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'user_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'django_comments_xtd.xtdcomment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'XtdComment', '_ormbases': ['comments.Comment']},
            'comment_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['comments.Comment']", 'unique': 'True', 'primary_key': 'True'}),
            'followup': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'parent': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'thread': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['django_comments_xtd']

########NEW FILE########
__FILENAME__ = 0003_threads
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."
        for comment in orm.XtdComment.objects.all():
            comment.thread_id = comment.id
            comment.parent_id = comment.id
            comment.level = 0
            comment.order = 1
            comment.save()

    def backwards(self, orm):
        "Write your backwards methods here."
        raise RuntimeError("Cannot reverse this migration.")

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
        'comments.comment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'Comment', 'db_table': "'django_comments'"},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '3000'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_type_set_for_comment'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_pk': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'comment_comments'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'user_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'django_comments_xtd.xtdcomment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'XtdComment', '_ormbases': ['comments.Comment']},
            'comment_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['comments.Comment']", 'unique': 'True', 'primary_key': 'True'}),
            'followup': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['django_comments_xtd.XtdComment']"}),
            'thread': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['django_comments_xtd.XtdComment']"})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['django_comments_xtd']
    symmetrical = True

########NEW FILE########
__FILENAME__ = models
import six

from django.db import models, transaction
from django.db.models import F, Max, Min
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext, ugettext_lazy as _
from django_comments_xtd.conf import settings


def max_thread_level_for_content_type(content_type):
    app_model = "%s.%s" % (content_type.app_label, content_type.model)
    if app_model in settings.COMMENTS_XTD_MAX_THREAD_LEVEL_BY_APP_MODEL:
        return settings.COMMENTS_XTD_MAX_THREAD_LEVEL_BY_APP_MODEL[app_model]
    else:
        return settings.COMMENTS_XTD_MAX_THREAD_LEVEL


class MaxThreadLevelExceededException(Exception):
    def __init__(self, content_type=None):
        self.max_by_app = max_thread_level_for_content_type(content_type)

    def __str__(self):
        return ugettext("Can not post comments over the thread level %{max_thread_level}") % {"max_thread_level": self.max_by_app}


class XtdCommentManager(models.Manager):
    def for_app_models(self, *args):
        """Return XtdComments for pairs "app.model" given in args"""
        content_types = []
        for app_model in args:
            app, model = app_model.split(".")
            content_types.append(ContentType.objects.get(app_label=app,
                                                         model=model))
        return self.for_content_types(content_types)

    def for_content_types(self, content_types):
        qs = self.get_query_set().filter(content_type__in=content_types).reverse()
        return qs


class XtdComment(Comment):
    thread_id = models.IntegerField(default=0, db_index=True)
    parent_id = models.IntegerField(default=0)
    level = models.SmallIntegerField(default=0)
    order = models.IntegerField(default=1, db_index=True)
    followup = models.BooleanField(help_text=_("Receive by email further comments in this conversation"), blank=True, default=False)
    objects = XtdCommentManager()

    class Meta:
        ordering = settings.COMMENTS_XTD_LIST_ORDER

    def save(self, *args, **kwargs):
        is_new = self.pk == None
        super(Comment, self).save(*args, **kwargs)
        if is_new:
            if not self.parent_id:
                self.parent_id = self.id
                self.thread_id = self.id
            else:
                if max_thread_level_for_content_type(self.content_type):
                    with transaction.commit_on_success():
                        self._calculate_thread_data()
                else:
                    raise MaxThreadLevelExceededException(self.content_type)
            kwargs["force_insert"] = False
            super(Comment, self).save(*args, **kwargs)

    def _calculate_thread_data(self):
        # Implements the following approach:
        #  http://www.sqlteam.com/article/sql-for-threaded-discussion-forums
        parent = XtdComment.objects.get(pk=self.parent_id)
        if parent.level == max_thread_level_for_content_type(self.content_type):
            raise MaxThreadLevelExceededException(self.content_type)

        self.thread_id = parent.thread_id
        self.level = parent.level + 1
        qc_eq_thread = XtdComment.objects.filter(thread_id = parent.thread_id)
        qc_ge_level = qc_eq_thread.filter(level__lte = parent.level,
                                          order__gt = parent.order)
        if qc_ge_level.count():
            min_order = qc_ge_level.aggregate(Min('order'))['order__min']
            XtdComment.objects.filter(thread_id = parent.thread_id,
                                      order__gte = min_order).update(order=F('order')+1)
            self.order = min_order
        else:
            max_order = qc_eq_thread.aggregate(Max('order'))['order__max']
            self.order = max_order + 1

    @models.permalink
    def get_reply_url(self):
        return ("comments-xtd-reply", None, {"cid": self.pk})

    def allow_thread(self):
        if self.level < max_thread_level_for_content_type(self.content_type):
            return True
        else:
            return False

class DummyDefaultManager:
    """
    Dummy Manager to mock django's CommentForm.check_for_duplicate method.
    """
    def __getattr__(self, name):
        return lambda *args, **kwargs: []

    def using(self, *args, **kwargs):
        return self


class TmpXtdComment(dict):
    """
    Temporary XtdComment to be pickled, ziped and appended to a URL.
    """
    _default_manager = DummyDefaultManager()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def save(self, *args, **kwargs):
        pass

    def _get_pk_val(self):
        if self.xtd_comment:
            return self.xtd_comment._get_pk_val()
        else:
            return ""

    def __reduce__(self):
        return (TmpXtdComment, (), None, None, six.iteritems(self))

########NEW FILE########
__FILENAME__ = signals
"""
Signals relating to django-comments-xtd.
"""
from django.dispatch import Signal

# Sent just after a comment has been verified.
confirmation_received = Signal(providing_args=["comment", "request"])

# Sent just after a user has muted a comments thread.
comment_thread_muted = Signal(providing_args=["comment", "requests"])

########NEW FILE########
__FILENAME__ = signed
"""
Borrowed from Simon Willison's Django-OpenID project:
  * https://github.com/simonw/django-openid

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
from __future__ import unicode_literals

import base64
import hmac
import pickle
import hashlib

from django.utils import six
from django_comments_xtd.conf import settings


def dumps(obj, key = None, compress = False, extra_key = b''):
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
    base64d = encode(pickled).strip(b'=')
    if is_compressed:
        base64d = b'.' + base64d
    return sign(base64d, 
                (key or settings.SECRET_KEY.encode('ascii')) + extra_key)

def loads(s, key = None, extra_key = b''):
    "Reverse of dumps(), raises ValueError if signature fails"
    if isinstance(s, six.text_type):
        s = s.encode('utf8') # base64 works on bytestrings
    try:
        base64d = unsign(s, 
                         (key or settings.SECRET_KEY.encode('ascii')) + 
                         extra_key)
    except ValueError:
        raise
    decompress = False
    if base64d.startswith(b'.'):
        # It's compressed; uncompress it first
        base64d = base64d[1:]
        decompress = True
    pickled = decode(base64d)
    if decompress:
        import zlib
        pickled = zlib.decompress(pickled)
    return pickle.loads(pickled)

def encode(s):
    return base64.urlsafe_b64encode(s).strip(b'=')

def decode(s):
    return base64.urlsafe_b64decode(s + b'=' * (len(s) % 4))

class BadSignature(ValueError):
    # Extends ValueError, which makes it more convenient to catch and has 
    # basically the correct semantics.
    pass

def sign(value, key = None):
    if isinstance(value, six.text_type):
        raise TypeError('sign() needs bytestring: %s' % repr(value))
    if key is None:
        key = settings.SECRET_KEY.encode('ascii')
    return value + b'.' + base64_hmac(value, key)

def unsign(signed_value, key = None):
    if isinstance(signed_value, six.text_type):
        raise TypeError('unsign() needs bytestring')
    if key is None:
        key = settings.SECRET_KEY.encode('ascii')
    if signed_value.find(b'.') == -1:
        raise BadSignature('Missing sig (no . found in value)')
    value, sig = signed_value.rsplit(b'.', 1)
    if base64_hmac(value, key) == sig:
        return value
    else:
        raise BadSignature('Signature failed: %s' % sig)

def base64_hmac(value, key):
    return encode(hmac.new(key, value, hashlib.sha1).digest())

########NEW FILE########
__FILENAME__ = comments_xtd
#-*- coding: utf-8 -*-

import re

from django.contrib.contenttypes.models import ContentType
from django.template import (Library, Node, TemplateSyntaxError,
                             Variable, loader, RequestContext)
from django.utils.safestring import mark_safe

from django_comments_xtd import get_model as get_comment_model

from ..utils import import_formatter


XtdComment = get_comment_model()

formatter = import_formatter()

register = Library()


class XtdCommentCountNode(Node):
    """Store the number of XtdComments for the given list of app.models"""

    def __init__(self, as_varname, content_types):
        """Class method to parse get_xtdcomment_list and return a Node."""
        self.as_varname = as_varname
        self.qs = XtdComment.objects.for_content_types(content_types)

    def render(self, context):
        context[self.as_varname] = self.qs.count()
        return ''


def get_xtdcomment_count(parser, token):
    """
    Gets the comment count for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_xtdcomment_count as [varname] for [app].[model] [[app].[model]] %}

    Example usage::

        {% get_xtdcomment_count as comments_count for blog.story blog.quote %}

    """
    tokens = token.contents.split()

    if tokens[1] != 'as':
        raise TemplateSyntaxError("2nd. argument in %r tag must be 'for'" % tokens[0])

    as_varname = tokens[2]

    if tokens[3] != 'for':
        raise TemplateSyntaxError("4th. argument in %r tag must be 'for'" % tokens[0])

    content_types = _get_content_types(tokens[0], tokens[4:])
    return XtdCommentCountNode(as_varname, content_types)


class BaseLastXtdCommentsNode(Node):
    """Base class to deal with the last N XtdComments for a list of app.model"""

    def __init__(self, count, content_types, template_path=None):
        """Class method to parse get_xtdcomment_list and return a Node."""
        try:
            self.count = int(count)
        except:
            self.count = Variable(count)

        self.content_types = content_types
        self.template_path = template_path


class RenderLastXtdCommentsNode(BaseLastXtdCommentsNode):

    def render(self, context):
        if not isinstance(self.count, int):
            self.count = int( self.count.resolve(context) )

        self.qs = XtdComment.objects.for_content_types(self.content_types)[:self.count]

        strlist = []
        for xtd_comment in self.qs:
            if self.template_path:
                template_arg = self.template_path
            else:
                template_arg = [
                    "django_comments_xtd/%s/%s/comment.html" % (
                        xtd_comment.content_type.app_label, 
                        xtd_comment.content_type.model),
                    "django_comments_xtd/%s/comment.html" % (
                        xtd_comment.content_type.app_label,),
                    "django_comments_xtd/comment.html"
                ]
            strlist.append(
                loader.render_to_string(
                    template_arg, {"comment": xtd_comment}, context))
        return ''.join(strlist)


class GetLastXtdCommentsNode(BaseLastXtdCommentsNode):

    def __init__(self, count, as_varname, content_types):
        super(GetLastXtdCommentsNode, self).__init__(count, content_types)
        self.as_varname = as_varname

    def render(self, context):
        if not isinstance(self.count, int):
            self.count = int( self.count.resolve(context) )

        self.qs = XtdComment.objects.for_content_types(self.content_types)[:self.count]
        context[self.as_varname] = self.qs
        return ''
        

def _get_content_types(tagname, tokens):
    content_types = []
    for token in tokens:
        try:
            app, model = token.split('.')
            content_types.append(
                ContentType.objects.get(app_label=app, model=model))
        except ValueError:
            raise TemplateSyntaxError(
                "Argument %s in %r must be in the format 'app.model'" % (
                    token, tagname))
        except ContentType.DoesNotExist:
            raise TemplateSyntaxError(
                "%r tag has non-existant content-type: '%s.%s'" % (
                    tagname, app, model))
    return content_types


def render_last_xtdcomments(parser, token):
    """
    Render the last N XtdComments through the 
      ``comments_xtd/comment.html`` template

    Syntax::

        {% render_last_xtdcomments [N] for [app].[model] [[app].[model]] using [template] %}

    Example usage::

        {% render_last_xtdcomments 5 for blog.story blog.quote using "comments/blog/comment.html" %}

    """
    tokens = token.contents.split()

    try:
        count = tokens[1]
    except ValueError:
        raise TemplateSyntaxError(
            "Second argument in %r tag must be a integer" % tokens[0])

    if tokens[2] != 'for':
        raise TemplateSyntaxError(
            "Third argument in %r tag must be 'for'" % tokens[0])

    try:
        token_using = tokens.index("using")
        content_types = _get_content_types(tokens[0], tokens[3:token_using])
        try:
            template = tokens[token_using+1].strip('" ')
        except IndexError:
            raise TemplateSyntaxError(
                "Last argument in %r tag must be a relative template path" % tokens[0])       
    except ValueError:
        content_types = _get_content_types(tokens[0], tokens[3:])
        template = None

    return RenderLastXtdCommentsNode(count, content_types, template)


def get_last_xtdcomments(parser, token):
    """
    Get the last N XtdComments

    Syntax::

        {% get_last_xtdcomments [N] as [varname] for [app].[model] [[app].[model]] %}

    Example usage::

        {% get_last_xtdcomments 5 as last_comments for blog.story blog.quote %}

    """
    tokens = token.contents.split()

    try:
        count = int(tokens[1])
    except ValueError:
        raise TemplateSyntaxError(
            "Second argument in %r tag must be a integer" % tokens[0])

    if tokens[2] != 'as':
        raise TemplateSyntaxError(
            "Third argument in %r tag must be 'as'" % tokens[0])

    as_varname = tokens[3]

    if tokens[4] != 'for':
        raise TemplateSyntaxError(
            "Fifth argument in %r tag must be 'for'" % tokens[0])

    content_types = _get_content_types(tokens[0], tokens[5:])
    return GetLastXtdCommentsNode(count, as_varname, content_types)


def render_markup_comment(value):
    """
    Renders a comment using a markup language specified in the first line of the comment.

    Template Syntax::

        {{ comment.comment|render_markup_comment }}

    The first line of the comment field must start with the name of the markup language.

    A comment like::

        comment = r'''#!markdown\n\rAn [example](http://url.com/ "Title")'''

    Would be rendered as a markdown text, producing the output::

        <p><a href="http://url.com/" title="Title">example</a></p>
    """
    lines = value.splitlines()
    rawstr = r"""^#!(?P<markup_filter>\w+)$"""
    match_obj = re.search(rawstr, lines[0])
    if match_obj:
        markup_filter = match_obj.group('markup_filter')
        try:
            if formatter:
                return mark_safe(formatter("\n".join(lines[1:]), filter_name=markup_filter))
            else:
                raise TemplateSyntaxError(
                    "In order to use this templatetag you need django-markup, docutils and markdown installed")
        except ValueError as exc:
            output = "<p>Warning: %s</p>" % exc
            return output + value
    else:
        return value


register.tag(get_xtdcomment_count)
register.tag(render_last_xtdcomments)
register.tag(get_last_xtdcomments)
register.filter(render_markup_comment)

########NEW FILE########
__FILENAME__ = forms
from django.test import TestCase
from django.contrib import comments

from django_comments_xtd.models import TmpXtdComment
from django_comments_xtd.forms import XtdCommentForm
from django_comments_xtd.tests.models import Article


class GetFormTestCase(TestCase):

    def test_get_form(self):
        # check function django_comments_xtd.get_form retrieves the due class
        self.assert_(comments.get_form() == XtdCommentForm)


class XtdCommentFormTestCase(TestCase):

    def setUp(self):
        self.article = Article.objects.create(title="September", 
                                              slug="september",
                                              body="What I did on September...")
        self.form = comments.get_form()(self.article)

    def test_get_comment_model(self):
        # check get_comment_model retrieves the due model class
        self.assert_(self.form.get_comment_model() == TmpXtdComment)

    def test_get_comment_create_data(self):
        # as it's used in django.contrib.comments.views.comments
        data = {"name":"Daniel", 
                "email":"danirus@eml.cc", 
                "followup": True, 
                "reply_to": 0, "level": 1, "order": 1,
                "comment":"Es war einmal iene kleine..." }
        data.update(self.form.initial)
        form = comments.get_form()(self.article, data)
        self.assert_(self.form.security_errors() == {})
        self.assert_(self.form.errors == {})
        comment = form.get_comment_object()

        # it does have the new field 'followup'
        self.assert_("followup" in comment)

        # and as long as settings.COMMENTS_XTD_CONFIRM_EMAIL is True
        # is_public is set to False until receive the user confirmation
        self.assert_(comment.is_public == False) 

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models
from django.db.models import permalink
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import TestCase as DjangoTestCase

from django_comments_xtd.models import (XtdComment, 
                                        MaxThreadLevelExceededException)


class PublicManager(models.Manager):
    """Returns published articles that are not in the future."""
    
    def published(self):
        return self.get_query_set().filter(publish__lte=datetime.now())


class Article(models.Model):
    """Article, that accepts comments."""

    title = models.CharField('title', max_length=200)
    slug = models.SlugField('slug', unique_for_date='publish')
    body = models.TextField('body')
    allow_comments = models.BooleanField('allow comments', default=True)
    publish = models.DateTimeField('publish', default=datetime.now)

    objects = PublicManager()

    class Meta:
        db_table = 'demo_articles'
        ordering = ('-publish',)

    @permalink
    def get_absolute_url(self):
        return ('articles-article-detail', None, 
                {'year': self.publish.year,
                 'month': int(self.publish.strftime('%m').lower()),
                 'day': self.publish.day,
                 'slug': self.slug})

class Diary(models.Model):
    """Diary, that accepts comments."""
    body = models.TextField('body')
    allow_comments = models.BooleanField('allow comments', default=True)
    publish = models.DateTimeField('publish', default=datetime.now)

    objects = PublicManager()

    class Meta:
        db_table = 'demo_diary'
        ordering = ('-publish',)


class ArticleBaseTestCase(DjangoTestCase):
    def setUp(self):
        self.article_1 = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.article_2 = Article.objects.create(
            title="October", slug="october", body="What I did on October...")

class XtdCommentManagerTestCase(ArticleBaseTestCase):
    def test_for_app_models(self):
        # there is no comment posted yet to article_1 nor article_2
        count = XtdComment.objects.for_app_models("tests.article").count()
        self.assert_(count == 0)

        article_ct = ContentType.objects.get(app_label="tests", model="article")
        site = Site.objects.get(pk=1)

        # post one comment to article_1
        XtdComment.objects.create(content_type   = article_ct, 
                                  object_pk      = self.article_1.id,
                                  content_object = self.article_1,
                                  site           = site, 
                                  comment        ="just a testing comment",
                                  submit_date    = datetime.now())

        count = XtdComment.objects.for_app_models("tests.article").count()
        self.assert_(count == 1)

        # post one comment to article_2
        XtdComment.objects.create(content_type   = article_ct, 
                                  object_pk      = self.article_2.id,
                                  content_object = self.article_2,
                                  site           = site, 
                                  comment        = "yet another comment",
                                  submit_date    = datetime.now())

        count = XtdComment.objects.for_app_models("tests.article").count()
        self.assert_(count == 2)

        # post a second comment to article_2
        XtdComment.objects.create(content_type   = article_ct, 
                                  object_pk      = self.article_2.id,
                                  content_object = self.article_2,
                                  site           = site, 
                                  comment        = "and another one",
                                  submit_date    = datetime.now())

        count = XtdComment.objects.for_app_models("tests.article").count()
        self.assert_(count == 3)

# In order to methods save and test _calculate_thread_ata, simulate the 
# following threads, in order of arrival:
#
# testcase cmt.id   parent level-0  level-1  level-2
#  step1     1        -      c1                        <-                 cmt1
#  step1     2        -      c2                        <-                 cmt2
#  step2     3        1      --       c3               <-         cmt1 to cmt1
#  step2     4        1      --       c4               <-         cmt2 to cmt1
#  step3     5        2      --       c5               <-         cmt1 to cmt2
#  step4     6        5      --       --        c6     <- cmt1 to cmt1 to cmt2
#  step4     7        4      --       --        c7     <- cmt1 to cmt2 to cmt1
#  step5     8        3      --       --        c8     <- cmt1 to cmt1 to cmt1
#  step5     9        -      c9                        <-                 cmt9

def thread_test_step_1(article):
    article_ct = ContentType.objects.get(app_label="tests", model="article")
    site = Site.objects.get(pk=1)

    # post Comment 1 with parent_id 0
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="comment 1 to article",
                              submit_date    = datetime.now())
    
    # post Comment 2 with parent_id 0
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="comment 2 to article",
                              submit_date    = datetime.now())

def thread_test_step_2(article):
    article_ct = ContentType.objects.get(app_label="tests", model="article")
    site = Site.objects.get(pk=1)

    # post Comment 3 to parent_id 1
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="comment 1 to comment 1",
                              submit_date    = datetime.now(),
                              parent_id      = 1)
    
    # post Comment 4 to parent_id 1
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="comment 2 to comment 1",
                              submit_date    = datetime.now(),
                              parent_id      = 1)

def thread_test_step_3(article):
    article_ct = ContentType.objects.get(app_label="tests", model="article")
    site = Site.objects.get(pk=1)
    
    # post Comment 5 to parent_id 2
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="comment 1 to comment 1",
                              submit_date    = datetime.now(),
                              parent_id      = 2)
    
def thread_test_step_4(article):
    article_ct = ContentType.objects.get(app_label="tests", model="article")
    site = Site.objects.get(pk=1)
    
    # post Comment 6 to parent_id 5
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="cmt 1 to cmt 1 to cmt 2",
                              submit_date    = datetime.now(),
                              parent_id      = 5)
    
        # post Comment 7 to parent_id 4
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="cmt 1 to cmt 2 to cmt 1",
                              submit_date    = datetime.now(),
                              parent_id      = 4)

def thread_test_step_5(article):
    article_ct = ContentType.objects.get(app_label="tests", model="article")
    site = Site.objects.get(pk=1)

    # post Comment 8 to parent_id 3
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="cmt 1 to cmt 1 to cmt 1",
                              submit_date    = datetime.now(),
                              parent_id      = 3)
    
    # post Comment 9 with parent_id 0
    XtdComment.objects.create(content_type   = article_ct, 
                              object_pk      = article.id,
                              content_object = article,
                              site           = site, 
                              comment        ="cmt 1 to cmt 2 to cmt 1",
                              submit_date    = datetime.now())


class BaseThreadStep1TestCase(ArticleBaseTestCase):
    def setUp(self):
        super(BaseThreadStep1TestCase, self).setUp()
        thread_test_step_1(self.article_1)
        (            #  cmt.id  thread_id  parent_id  level  order
            self.c1, #    1         1          1        0      1 
            self.c2  #    2         2          2        0      1
        ) = XtdComment.objects.all()

    def test_threaded_comments_step_1_level_0(self):
        # comment 1
        self.assert_(self.c1.parent_id == 1 and self.c1.thread_id == 1)
        self.assert_(self.c1.level == 0 and self.c1.order == 1)
        # comment 2
        self.assert_(self.c2.parent_id == 2 and self.c2.thread_id == 2)
        self.assert_(self.c2.level == 0 and self.c2.order == 1)


class ThreadStep2TestCase(ArticleBaseTestCase):
    def setUp(self):
        super(ThreadStep2TestCase, self).setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)        
        (            #  cmt.id  thread_id  parent_id  level  order
            self.c1, #    1         1          1        0      1 
            self.c3, #    3         1          1        1      2
            self.c4, #    4         1          1        1      3
            self.c2  #    2         2          2        0      1
        ) = XtdComment.objects.all()

    def test_threaded_comments_step_2_level_0(self):
        # comment 1
        self.assert_(self.c1.parent_id == 1 and self.c1.thread_id == 1)
        self.assert_(self.c1.level == 0 and self.c1.order == 1)
        # comment 2
        self.assert_(self.c2.parent_id == 2 and self.c2.thread_id == 2)
        self.assert_(self.c2.level == 0 and self.c2.order == 1)

    def test_threaded_comments_step_2_level_1(self):
        # comment 3
        self.assert_(self.c3.parent_id == 1 and self.c3.thread_id == 1)
        self.assert_(self.c3.level == 1 and self.c3.order == 2)
        # comment 4
        self.assert_(self.c4.parent_id == 1 and self.c4.thread_id == 1)
        self.assert_(self.c4.level == 1 and self.c4.order == 3)

class ThreadStep3TestCase(ArticleBaseTestCase):
    def setUp(self):
        super(ThreadStep3TestCase, self).setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)        
        thread_test_step_3(self.article_1)        

        (            #  cmt.id  thread_id  parent_id  level  order
            self.c1, #    1         1          1        0      1
            self.c3, #    3         1          1        1      2
            self.c4, #    4         1          1        1      3
            self.c2, #    2         2          2        0      1
            self.c5  #    5         2          2        1      2
        ) = XtdComment.objects.all()
        
    def test_threaded_comments_step_3_level_0(self):
        # comment 1
        self.assert_(self.c1.parent_id == 1 and self.c1.thread_id == 1)
        self.assert_(self.c1.level == 0 and self.c1.order == 1)
        # comment 2
        self.assert_(self.c2.parent_id == 2 and self.c2.thread_id == 2)
        self.assert_(self.c2.level == 0 and self.c2.order == 1)

    def test_threaded_comments_step_3_level_1(self):
        # comment 3
        self.assert_(self.c3.parent_id == 1 and self.c3.thread_id == 1)
        self.assert_(self.c3.level == 1 and self.c3.order == 2)
        # comment 4
        self.assert_(self.c4.parent_id == 1 and  self.c4.thread_id == 1)
        self.assert_(self.c4.level == 1 and self.c4.order == 3)
        # comment 5
        self.assert_(self.c5.parent_id == 2 and self.c5.thread_id == 2)
        self.assert_(self.c5.level == 1 and self.c5.order == 2)


class ThreadStep4TestCase(ArticleBaseTestCase):
    def setUp(self):
        super(ThreadStep4TestCase, self).setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)        
        thread_test_step_3(self.article_1)        
        thread_test_step_4(self.article_1)        

        (            #  cmt.id  thread_id  parent_id  level  order
            self.c1, #    1         1          1        0      1
            self.c3, #    3         1          1        1      2
            self.c4, #    4         1          1        1      3
            self.c7, #    7         1          4        2      4
            self.c2, #    2         2          2        0      1
            self.c5, #    5         2          2        1      2
            self.c6  #    6         2          5        2      3
        ) = XtdComment.objects.all()
        
    def test_threaded_comments_step_4_level_0(self):
        # comment 1
        self.assert_(self.c1.parent_id == 1 and self.c1.thread_id == 1)
        self.assert_(self.c1.level == 0 and self.c1.order == 1)
        # comment 2
        self.assert_(self.c2.parent_id == 2 and self.c2.thread_id == 2)
        self.assert_(self.c2.level == 0 and self.c2.order == 1)

    def test_threaded_comments_step_4_level_1(self):
        # comment 3
        self.assert_(self.c3.parent_id == 1 and self.c3.thread_id == 1)
        self.assert_(self.c3.level == 1 and self.c3.order == 2)
        # comment 4
        self.assert_(self.c4.parent_id == 1 and  self.c4.thread_id == 1)
        self.assert_(self.c4.level == 1 and self.c4.order == 3)
        # comment 5
        self.assert_(self.c5.parent_id == 2 and self.c5.thread_id == 2)
        self.assert_(self.c5.level == 1 and self.c5.order == 2)

    def test_threaded_comments_step_4_level_2(self):
        # comment 6
        self.assert_(self.c6.parent_id == 5 and self.c6.thread_id == 2)
        self.assert_(self.c6.level == 2 and self.c6.order == 3)
        # comment 7
        self.assert_(self.c7.parent_id == 4 and  self.c7.thread_id == 1)
        self.assert_(self.c7.level == 2 and self.c7.order == 4)


class ThreadStep5TestCase(ArticleBaseTestCase):
    def setUp(self):
        super(ThreadStep5TestCase, self).setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)        
        thread_test_step_3(self.article_1)        
        thread_test_step_4(self.article_1)        
        thread_test_step_5(self.article_1)        

        (            #  cmt.id  thread_id  parent_id  level  order
            self.c1, #    1         1          1        0      1
            self.c3, #    3         1          1        1      2
            self.c8, #    8         1          3        2      3
            self.c4, #    4         1          1        1      4
            self.c7, #    7         1          4        2      5
            self.c2, #    2         2          2        0      1
            self.c5, #    5         2          2        1      2
            self.c6, #    6         2          5        2      3
            self.c9  #    9         9          9        0      1
        ) = XtdComment.objects.all()
        
    def test_threaded_comments_step_5_level_0(self):
        # comment 1
        self.assert_(self.c1.parent_id == 1 and self.c1.thread_id == 1)
        self.assert_(self.c1.level == 0 and self.c1.order == 1)
        # comment 2
        self.assert_(self.c2.parent_id == 2 and self.c2.thread_id == 2)
        self.assert_(self.c2.level == 0 and self.c2.order == 1)
        # comment 9
        self.assert_(self.c9.parent_id == 9 and self.c9.thread_id == 9)
        self.assert_(self.c9.level == 0 and self.c9.order == 1)

    def test_threaded_comments_step_5_level_1(self):
        # comment 3
        self.assert_(self.c3.parent_id == 1 and self.c3.thread_id == 1)
        self.assert_(self.c3.level == 1 and self.c3.order == 2)
        # comment 4
        self.assert_(self.c4.parent_id == 1 and  self.c4.thread_id == 1)
        self.assert_(self.c4.level == 1 and self.c4.order == 4) # changed
        # comment 5
        self.assert_(self.c5.parent_id == 2 and self.c5.thread_id == 2)
        self.assert_(self.c5.level == 1 and self.c5.order == 2)

    def test_threaded_comments_step_5_level_2(self):
        # comment 6
        self.assert_(self.c6.parent_id == 5 and self.c6.thread_id == 2)
        self.assert_(self.c6.level == 2 and self.c6.order == 3)
        # comment 7
        self.assert_(self.c7.parent_id == 4 and  self.c7.thread_id == 1)
        self.assert_(self.c7.level == 2 and self.c7.order == 5) # changed
        # comment 8
        self.assert_(self.c8.parent_id == 3 and  self.c8.thread_id == 1)
        self.assert_(self.c8.level == 2 and self.c8.order == 3)

    def test_exceed_max_thread_level_raises_exception(self):
        article_ct = ContentType.objects.get(app_label="tests", model="article")
        site = Site.objects.get(pk=1)
        with self.assertRaises(MaxThreadLevelExceededException):
            XtdComment.objects.create(content_type   = article_ct, 
                                      object_pk      = self.article_1.id,
                                      content_object = self.article_1,
                                      site           = site, 
                                      comment        = ("cmt 1 to cmt 2 to "
                                                        "cmt 1"),
                                      submit_date    = datetime.now(),
                                      parent_id      = 8) # already max thread 
                                                          # level


class DiaryBaseTestCase(DjangoTestCase):
    def setUp(self):
        self.day_in_diary = Diary.objects.create(body="About Today...")
        diary_ct = ContentType.objects.get(app_label="tests", model="diary")
        site = Site.objects.get(pk=1)
        XtdComment.objects.create(content_type   = diary_ct, 
                                  object_pk      = self.day_in_diary.id,
                                  content_object = self.day_in_diary,
                                  site           = site, 
                                  comment        ="cmt to day in diary",
                                  submit_date    = datetime.now())

    def test_max_thread_level_by_app_model(self):
        diary_ct = ContentType.objects.get(app_label="tests", model="diary")
        site = Site.objects.get(pk=1)
        with self.assertRaises(MaxThreadLevelExceededException):
            XtdComment.objects.create(content_type   = diary_ct, 
                                      object_pk      = self.day_in_diary.id,
                                      content_object = self.day_in_diary,
                                      site           = site, 
                                      comment        = ("cmt to cmt to day "
                                                        "in diary"),
                                      submit_date    = datetime.now(),
                                      parent_id      = 1) # already max thread 
                                                          # level
        

########NEW FILE########
__FILENAME__ = templatetags
#-*- coding: utf-8 -*-

import unittest

from django.template import TemplateSyntaxError
from django.test import TestCase as DjangoTestCase

from django_comments_xtd.templatetags.comments_xtd import render_markup_comment, formatter


@unittest.skipIf(not formatter, "This test case needs django-markup, docutils and markdown installed to be run")
class RenderMarkupValueFilterTestCase(DjangoTestCase):

    def test_render_markup_comment_in_markdown(self):
        comment = r'''#!markdown
An [example](http://url.com/ "Title")'''
        result = render_markup_comment(comment)
        self.assertEqual(result,
                         '<p>An <a href="http://url.com/" title="Title">example</a></p>')

    def test_render_markup_comment_in_restructuredtext(self):
        comment = r'''#!restructuredtext
A fibonacci generator in Python, taken from `LiteratePrograms <http://en.literateprograms.org/Fibonacci_numbers_%28Python%29>`_::

    def fib():
        a, b = 0, 1
        while 1:
            yield a
            a, b = b, a + b'''
        result = render_markup_comment(comment)
        self.assertEqual(result,
                         r'''<p>A fibonacci generator in Python, taken from <a class="reference external" href="http://en.literateprograms.org/Fibonacci_numbers_%28Python%29">LiteratePrograms</a>:</p>
<pre class="literal-block">
def fib():
    a, b = 0, 1
    while 1:
        yield a
        a, b = b, a + b
</pre>
''')


@unittest.skipIf(formatter, "This test case needs django-markup or docutils or markdown not installed to be run")
class MarkupNotAvailableTestCase(DjangoTestCase):

    def test_render_markup_comment(self):
        comment = r'''#!markdown
An [example](http://url.com/ "Title")'''
        render_markup_comment, comment
        self.assertRaises(TemplateSyntaxError, render_markup_comment, comment)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^articles/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$',
        'django_comments_xtd.tests.views.dummy_view',
        name='articles-article-detail'),

    (r'^comments/', include('django_comments_xtd.urls')),
)

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

import re
from mock import patch
from datetime import datetime

# from django.conf import settings
from django.contrib import comments
from django.contrib.comments.signals import comment_was_posted
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse, NoReverseMatch
from django.http import HttpResponse
from django.test import TestCase
# from django.test.utils import override_settings

from django_comments_xtd import signals, signed
from django_comments_xtd.conf import settings
from django_comments_xtd.models import XtdComment, TmpXtdComment
from django_comments_xtd.tests.models import Article, Diary
from django_comments_xtd.views import on_comment_was_posted


def dummy_view(request, *args, **kwargs):
    return HttpResponse("Got it")


class OnCommentWasPostedTestCase(TestCase):
    def setUp(self):
        patcher = patch('django_comments_xtd.views.send_mail')
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="October", slug="october", body="What I did on October...")
        self.form = comments.get_form()(self.article)
        
    def post_valid_data(self, wait_mail=True):
        data = {"name":"Bob", "email":"bob@example.com", "followup": True, 
                "reply_to": 0, "level": 1, "order": 1,
                "comment":"Es war einmal iene kleine..."}
        data.update(self.form.initial)
        self.response = self.client.post(reverse("comments-post-comment"), 
                                        data=data, follow=True)

    def test_post_as_authenticated_user(self):
        auth_user = User.objects.create_user("bob", "bob@example.com", "pwd")
        self.client.login(username="bob", password="pwd")
        self.assert_(self.mock_mailer.call_count == 0)
        self.post_valid_data(wait_mail=False)
        # no confirmation email sent as user is authenticated
        self.assert_(self.mock_mailer.call_count == 0)

    def test_confirmation_email_is_sent(self):
        self.assert_(self.mock_mailer.call_count == 0)
        self.post_valid_data()
        self.assert_(self.mock_mailer.call_count == 1)
        self.assertTemplateUsed(self.response, "comments/posted.html")


class ConfirmCommentTestCase(TestCase):
    def setUp(self):
        patcher = patch('django_comments_xtd.views.send_mail')
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(title="September", 
                                              slug="september",
                                              body="What I did on September...")
        self.form = comments.get_form()(self.article)
        data = {"name": "Bob", "email": "bob@example.com", "followup": True, 
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal iene kleine..." }
        data.update(self.form.initial)
        self.response = self.client.post(reverse("comments-post-comment"), 
                                        data=data)
        self.assert_(self.mock_mailer.call_count == 1)
        self.key = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                                 self.mock_mailer.call_args[0][1]).group("key"))
        self.addCleanup(patcher.stop)

    def get_confirm_comment_url(self, key):
        self.response = self.client.get(reverse("comments-xtd-confirm",
                                                kwargs={'key': key}), 
                                        follow=True)

    def test_404_on_bad_signature(self):
        self.get_confirm_comment_url(self.key[:-1])
        self.assertContains(self.response, "404", status_code=404)

    def test_consecutive_confirmation_url_visits_fail(self):
        # test that consecutives visits to the same confirmation URL produce
        # an Http 404 code, as the comment has already been verified in the
        # first visit
        self.get_confirm_comment_url(self.key)
        self.get_confirm_comment_url(self.key)
        self.assertContains(self.response, "404", status_code=404)
        
    def test_signal_receiver_may_discard_the_comment(self):
        # test that receivers of signal confirmation_received may return False
        # and thus rendering a template_discarded output
        def on_signal(sender, comment, request, **kwargs):
            return False

        self.assertEqual(self.mock_mailer.call_count, 1) # sent during setUp
        signals.confirmation_received.connect(on_signal)
        self.get_confirm_comment_url(self.key)
        # mailing avoided by on_signal:
        self.assertEqual(self.mock_mailer.call_count, 1)
        self.assertTemplateUsed(self.response, 
                                "django_comments_xtd/discarded.html")

    def test_comment_is_created_and_view_redirect(self):
        # testing that visiting a correct confirmation URL creates a XtdComment
        # and redirects to the article detail page
        Site.objects.get_current().domain = "testserver" # django bug #7743
        self.get_confirm_comment_url(self.key)
        data = signed.loads(self.key, extra_key=settings.COMMENTS_XTD_SALT)
        try:
            comment = XtdComment.objects.get(
                content_type=data["content_type"], 
                user_name=data["user_name"],
                user_email=data["user_email"],
                submit_date=data["submit_date"])
        except:
            comment = None
        self.assert_(comment != None)
        self.assertRedirects(self.response, self.article.get_absolute_url())

    def test_notify_comment_followers(self):
        # send a couple of comments to the article with followup=True and check
        # that when the second comment is confirmed a followup notification 
        # email is sent to the user who sent the first comment
        self.assertEqual(self.mock_mailer.call_count, 1)
        self.get_confirm_comment_url(self.key)
        # no comment followers yet:
        self.assertEqual(self.mock_mailer.call_count, 1)
        # send 2nd comment
        self.form = comments.get_form()(self.article)
        data = {"name":"Alice", "email":"alice@example.com", "followup": True, 
                "reply_to": 0, "level": 1, "order": 1,
                "comment":"Es war einmal eine kleine..." }
        data.update(self.form.initial)
        self.response = self.client.post(reverse("comments-post-comment"), 
                                        data=data)
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.key = re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                             self.mock_mailer.call_args[0][1]).group("key")
        self.get_confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 3)
        self.assert_(self.mock_mailer.call_args[0][3] == ["bob@example.com"])
        self.assert_(self.mock_mailer.call_args[0][1].find("There is a new comment following up yours.") > -1)

    def test_notify_followers_dupes(self):
        # first of all confirm Bob's comment otherwise it doesn't reach DB
        self.get_confirm_comment_url(self.key)
        # then put in play pull-request-15's assert...
        # https://github.com/danirus/django-comments-xtd/pull/15
        diary = Diary.objects.create(
            body='Lorem ipsum',
            allow_comments=True
        )
        self.assertEqual(diary.pk, self.article.pk)

        self.form = comments.get_form()(diary)
        data = {"name": "Charlie", "email": "charlie@example.com", 
                "followup": True, "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..." }
        data.update(self.form.initial)

        self.response = self.client.post(reverse("comments-post-comment"), 
                                        data=data)
        self.key = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                                 self.mock_mailer.call_args[0][1]).group("key"))
        # 1) confirmation for Bob (sent in `setUp()`)
        # 2) confirmation for Charlie
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.get_confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 2)

        self.form = comments.get_form()(self.article)
        data = {"name":"Alice", "email":"alice@example.com", "followup": True, 
                "reply_to": 0, "level": 1, "order": 1,
                "comment":"Es war einmal iene kleine..." }
        data.update(self.form.initial)
        self.response = self.client.post(reverse("comments-post-comment"), 
                                        data=data)
        self.assertEqual(self.mock_mailer.call_count, 3)
        self.key = re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                             self.mock_mailer.call_args[0][1]).group("key")
        self.get_confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 4)
        self.assert_(self.mock_mailer.call_args[0][3] == ["bob@example.com"])
        self.assert_(self.mock_mailer.call_args[0][1].find("There is a new comment following up yours.") > -1)

    def test_no_notification_for_same_user_email(self):
        # test that a follow-up user_email don't get a notification when 
        # sending another email to the thread
        self.assertEqual(self.mock_mailer.call_count, 1)
        self.get_confirm_comment_url(self.key) #  confirm Bob's comment 
        # no comment followers yet:
        self.assertEqual(self.mock_mailer.call_count, 1)
        # send Bob's 2nd comment
        self.form = comments.get_form()(self.article)
        data = {"name":"Alice", "email":"bob@example.com", "followup": True, 
                "reply_to": 0, "level": 1, "order": 1,
                "comment":"Bob's comment he shouldn't get notified about" }
        data.update(self.form.initial)
        self.response = self.client.post(reverse("comments-post-comment"), 
                                        data=data)
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.key = re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                             self.mock_mailer.call_args[0][1]).group("key")
        self.get_confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 2)


class ReplyNoCommentTestCase(TestCase):
    def test_reply_non_existing_comment_raises_404(self):
        response = self.client.get(reverse("comments-xtd-reply", 
                                           kwargs={"cid": 1}))
        self.assertContains(response, "404", status_code=404)
        
    
class ReplyCommentTestCase(TestCase):
    def setUp(self):
        article = Article.objects.create(title="September", 
                                         slug="september",
                                         body="What I did on September...")
        article_ct = ContentType.objects.get(app_label="tests", model="article")
        site = Site.objects.get(pk=1)
        
        # post Comment 1 to article, level 0
        XtdComment.objects.create(content_type   = article_ct, 
                                  object_pk      = article.id,
                                  content_object = article,
                                  site           = site, 
                                  comment        ="comment 1 to article",
                                  submit_date    = datetime.now())

        # post Comment 2 to article, level 1
        XtdComment.objects.create(content_type   = article_ct, 
                                  object_pk      = article.id,
                                  content_object = article,
                                  site           = site, 
                                  comment        ="comment 1 to comment 1",
                                  submit_date    = datetime.now(),
                                  parent_id      = 1)

        # post Comment 3 to article, level 2 (max according to test settings)
        XtdComment.objects.create(content_type   = article_ct, 
                                  object_pk      = article.id,
                                  content_object = article,
                                  site           = site, 
                                  comment        ="comment 1 to comment 1",
                                  submit_date    = datetime.now(),
                                  parent_id      = 2)

    def test_reply_renders_max_thread_level_template(self):
        response = self.client.get(reverse("comments-xtd-reply", 
                                                kwargs={"cid": 3}))
        self.assertTemplateUsed(response, 
                                "django_comments_xtd/max_thread_level.html")

class MuteFollowUpsTestCase(TestCase):
    def setUp(self):
        # Creates an article and send two comments to the article with follow-up
        # notifications. First comment doesn't have to send any notification.
        # Second comment has to send one notification (to Bob).
        patcher = patch('django_comments_xtd.views.send_mail')
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="September", slug="september", body="John's September")
        self.form = comments.get_form()(self.article)

        # Bob sends 1st comment to the article with follow-up
        data = {"name": "Bob", "email": "bob@example.com", "followup": True, 
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Nice September you had..." }
        data.update(self.form.initial)
        response = self.client.post(reverse("comments-post-comment"), 
                                    data=data)
        self.assert_(self.mock_mailer.call_count == 1)
        bobkey = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                                 self.mock_mailer.call_args[0][1]).group("key"))
        self.get_confirm_comment_url(bobkey) #  confirm Bob's comment 

        # Alice sends 2nd comment to the article with follow-up
        data = {"name": "Alice", "email": "alice@example.com", "followup": True, 
                "reply_to": 1, "level": 1, "order": 1,
                "comment": "Yeah, great photos" }
        data.update(self.form.initial)
        response = self.client.post(reverse("comments-post-comment"), 
                                    data=data)
        self.assert_(self.mock_mailer.call_count == 2)
        alicekey = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                                 self.mock_mailer.call_args[0][1]).group("key"))
        self.get_confirm_comment_url(alicekey) #  confirm Alice's comment 

        # Bob receives a follow-up notification
        self.assert_(self.mock_mailer.call_count == 3)
        self.bobs_mutekey = str(re.search(
            r'http://.+/mute/(?P<key>[\S]+)', 
            self.mock_mailer.call_args[0][1]).group("key"))
        self.addCleanup(patcher.stop)

    def get_confirm_comment_url(self, key):
        self.response = self.client.get(reverse("comments-xtd-confirm",
                                                kwargs={'key': key}), 
                                        follow=True)

    def get_mute_followup_url(self, key):
        self.response = self.client.get(reverse("comments-xtd-mute",
                                                kwargs={'key': key}),
                                        follow=True)

    def test_mute_followup_notifications(self):
        # Bob's receive a notification and clicka on the mute link to
        # avoid additional comment messages on the same article.
        self.get_mute_followup_url(self.bobs_mutekey)
        # Alice sends 3rd comment to the article with follow-up
        data = {"name": "Alice", "email": "alice@example.com", "followup": True, 
                "reply_to": 2, "level": 1, "order": 1,
                "comment": "And look at this and that..." }
        data.update(self.form.initial)
        response = self.client.post(reverse("comments-post-comment"), 
                                    data=data)
        # Alice confirms her comment...
        self.assert_(self.mock_mailer.call_count == 4)
        alicekey = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)', 
                                 self.mock_mailer.call_args[0][1]).group("key"))
        self.get_confirm_comment_url(alicekey) #  confirm Alice's comment 
        # Alice confirmed her comment, but this time Bob won't receive any
        # notification, neither do Alice being the sender
        self.assert_(self.mock_mailer.call_count == 4)


class HTMLDisabledMailTestCase(TestCase):
    def setUp(self):
        # Create an article and send a comment. Test method will chech headers
        # to see wheter messages has multiparts or not.
        patcher = patch('django_comments_xtd.views.send_mail')
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="September", slug="september", body="John's September")
        self.form = comments.get_form()(self.article)

        # Bob sends 1st comment to the article with follow-up
        self.data = {"name": "Bob", "email": "bob@example.com", 
                     "followup": True, "reply_to": 0, "level": 1, "order": 1,
                     "comment": "Nice September you had..." }
        self.data.update(self.form.initial)
    
    @patch.multiple('django_comments_xtd.conf.settings', 
                    COMMENTS_XTD_SEND_HTML_EMAIL=False)
    def test_mail_does_not_contain_html_part(self):
        with patch.multiple('django_comments_xtd.conf.settings', 
                            COMMENTS_XTD_SEND_HTML_EMAIL=False):
            self.client.post(reverse("comments-post-comment"), data=self.data)
            self.assert_(self.mock_mailer.call_count == 1)
            self.assert_(self.mock_mailer.call_args[1]['html'] == None)

    def test_mail_does_contain_html_part(self):
        self.client.post(reverse("comments-post-comment"), data=self.data)
        self.assert_(self.mock_mailer.call_count == 1)
        self.assert_(self.mock_mailer.call_args[1]['html'] != None)
    

########NEW FILE########
__FILENAME__ = urls
#-*- coding: utf-8 -*-

from django import VERSION as DJANGO_VERSION
if DJANGO_VERSION[0:2] < (1, 4):
    from django.conf.urls.defaults import include, patterns, url
else:
    from django.conf.urls import include, patterns, url

from django.views import generic

from django_comments_xtd import views, models
from django_comments_xtd.conf import settings


urlpatterns = patterns('',
    url(r'', include("django.contrib.comments.urls")),
    url(r'^sent/$', views.sent, name='comments-xtd-sent'),
    url(r'^confirm/(?P<key>[^/]+)$', views.confirm, name='comments-xtd-confirm'),
    url(r'^mute/(?P<key>[^/]+)$', views.mute, name='comments-xtd-mute'),
)

if settings.COMMENTS_XTD_MAX_THREAD_LEVEL > 0:
    urlpatterns += patterns("",
        url(r'^reply/(?P<cid>[\d]+)$',   views.reply,   name='comments-xtd-reply'),
    )

########NEW FILE########
__FILENAME__ = utils
# Idea borrowed from Selwin Ong post:
# http://ui.co.id/blog/asynchronous-send_mail-in-django

try:
    import Queue as queue # python2
except ImportError:
    import queue as queue # python3

import threading
from django.core.mail import EmailMultiAlternatives
from django_comments_xtd.conf import settings


mail_sent_queue = queue.Queue()

class EmailThread(threading.Thread):
    def __init__(self, subject, body, from_email, recipient_list, 
                 fail_silently, html):
        self.subject = subject
        self.body = body
        self.recipient_list = recipient_list
        self.from_email = from_email
        self.fail_silently = fail_silently
        self.html = html
        threading.Thread.__init__(self)

    def run(self):
        _send_mail(self.subject, self.body, self.from_email, 
                   self.recipient_list, self.html, self.fail_silently)
        mail_sent_queue.put(True)        


def _send_mail(subject, body, from_email, recipient_list, 
               fail_silently=False, html=None):
    msg = EmailMultiAlternatives(subject, body, from_email, recipient_list)
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send(fail_silently)


def send_mail(subject, body, from_email, recipient_list, 
              fail_silently=False, html=None):
    if settings.COMMENTS_XTD_THREADED_EMAILS:
        EmailThread(subject, body, from_email, recipient_list, 
                    fail_silently, html).start()
    else:
        _send_mail(subject, body, from_email, recipient_list,
                   fail_silently, html)

def import_formatter():
    try:
        from django_markup.markup import formatter
        from markdown import markdown
        from docutils import core
        return formatter
    except ImportError:
        return False

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals
import six

from django.db import models
from django.contrib.comments import get_form
from django.contrib.comments.signals import comment_was_posted
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect, render_to_response
from django.template import loader, Context, RequestContext
from django.utils.translation import ugettext_lazy as _
from django_comments_xtd import signals, signed
from django_comments_xtd import get_model as get_comment_model
from django_comments_xtd.conf import settings
from django_comments_xtd.models import (TmpXtdComment, 
                                        max_thread_level_for_content_type)
from django_comments_xtd.utils import send_mail


XtdComment = get_comment_model()


def send_email_confirmation_request(
        comment, target, key, 
        text_template="django_comments_xtd/email_confirmation_request.txt", 
        html_template="django_comments_xtd/email_confirmation_request.html"):
    """Send email requesting comment confirmation"""
    subject = _("comment confirmation request")
    confirmation_url = reverse("comments-xtd-confirm", args=[key])
    message_context = Context({ 'comment': comment, 
                                'content_object': target, 
                                'confirmation_url': confirmation_url,
                                'contact': settings.DEFAULT_FROM_EMAIL,
                                'site': Site.objects.get_current() })
    # prepare text message
    text_message_template = loader.get_template(text_template)
    text_message = text_message_template.render(message_context)
    if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
        # prepare html message
        html_message_template = loader.get_template(html_template)
        html_message = html_message_template.render(message_context)
    else: 
        html_message = None

    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL,
              [ comment.user_email, ], html=html_message)

def _comment_exists(comment):
    """
    True if exists a XtdComment with same user_name, user_email and submit_date.
    """
    return (XtdComment.objects.filter(
        user_name=comment.user_name, 
        user_email=comment.user_email,
        followup=comment.followup,
        submit_date=comment.submit_date
    ).count() > 0)

def _create_comment(tmp_comment):
    """
    Creates a XtdComment from a TmpXtdComment.
    """
    comment = XtdComment(**tmp_comment)
    comment.is_public = True
    comment.save()
    return comment

def on_comment_was_posted(sender, comment, request, **kwargs):
    """
    Post the comment if a user is authenticated or send a confirmation email.
    
    On signal django.contrib.comments.signals.comment_was_posted check if the 
    user is authenticated or if settings.COMMENTS_XTD_CONFIRM_EMAIL is False. 
    In both cases will post the comment. Otherwise will send a confirmation
    email to the person who posted the comment.
    """
    if settings.COMMENTS_APP != "django_comments_xtd":
        return False

    if (not settings.COMMENTS_XTD_CONFIRM_EMAIL or 
        (comment.user and comment.user.is_authenticated())):
        if not _comment_exists(comment):
            new_comment = _create_comment(comment)
            comment.xtd_comment = new_comment
            notify_comment_followers(new_comment)
    else:
        ctype = request.POST["content_type"]
        object_pk = request.POST["object_pk"]
        model = models.get_model(*ctype.split("."))
        target = model._default_manager.get(pk=object_pk)
        key = signed.dumps(comment, compress=True, 
                           extra_key=settings.COMMENTS_XTD_SALT)
        send_email_confirmation_request(comment, target, key)

comment_was_posted.connect(on_comment_was_posted)


def sent(request):
    comment_pk = request.GET.get("c", None)
    try:
        comment_pk = int(comment_pk)
        comment = XtdComment.objects.get(pk=comment_pk)
    except (TypeError, ValueError, XtdComment.DoesNotExist):
        template_arg = ["django_comments_xtd/posted.html",
                        "comments/posted.html"]
        return render_to_response(template_arg, 
                                  context_instance=RequestContext(request))
    else:
        if (request.is_ajax() and comment.user 
            and comment.user.is_authenticated()):
            template_arg = [
                "django_comments_xtd/%s/%s/comment.html" % (
                    comment.content_type.app_label, 
                    comment.content_type.model),
                "django_comments_xtd/%s/comment.html" % (
                    comment.content_type.app_label,),
                "django_comments_xtd/comment.html"
            ]
            return render_to_response(template_arg, {"comment": comment},
                                      context_instance=RequestContext(request))
        else:
            return redirect(comment)


def confirm(request, key, 
            template_discarded="django_comments_xtd/discarded.html"):
    try:
        tmp_comment = signed.loads(str(key), 
                                   extra_key=settings.COMMENTS_XTD_SALT)
    except (ValueError, signed.BadSignature):
        raise Http404
    # the comment does exist if the URL was already confirmed, then: Http404
    if _comment_exists(tmp_comment):
        raise Http404
    # Send signal that the comment confirmation has been received
    responses = signals.confirmation_received.send(sender  = TmpXtdComment,
                                                   comment = tmp_comment,
                                                   request = request
    )
    # Check whether a signal receiver decides to discard the comment
    for (receiver, response) in responses:
        if response == False:
            return render_to_response(template_discarded, 
                                      {'comment': tmp_comment},
                                      context_instance=RequestContext(request))

    comment = _create_comment(tmp_comment)
    notify_comment_followers(comment)
    return redirect(comment)


def notify_comment_followers(comment):
    followers = {} 

    previous_comments = XtdComment.objects.filter(
        content_type=comment.content_type,
        object_pk=comment.object_pk, is_public=True,
        followup=True).exclude(user_email=comment.user_email)

    for instance in previous_comments:
        followers[instance.user_email] = (
            instance.user_name, 
            signed.dumps(instance, compress=True,
                         extra_key=settings.COMMENTS_XTD_SALT))

    model = models.get_model(comment.content_type.app_label,
                             comment.content_type.model)
    target = model._default_manager.get(pk=comment.object_pk)
    subject = _("new comment posted")
    text_message_template = loader.get_template(
        "django_comments_xtd/email_followup_comment.txt")
    if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
        html_message_template = loader.get_template(
            "django_comments_xtd/email_followup_comment.html")

    for email, (name, key) in six.iteritems(followers):
        mute_url = reverse('comments-xtd-mute', args=[key])
        message_context = Context({ 'user_name': name,
                                    'comment': comment, 
                                    'content_object': target,
                                    'mute_url': mute_url,
                                    'site': Site.objects.get_current() })
        text_message = text_message_template.render(message_context)
        if settings.COMMENTS_XTD_SEND_HTML_EMAIL:
            html_message = html_message_template.render(message_context)
        else:
            html_message = None
        send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, 
                  [ email, ], html=html_message)


def reply(request, cid):
    try:
        comment = XtdComment.objects.get(pk=cid)
    except (XtdComment.DoesNotExist):
        raise Http404

    if comment.level == max_thread_level_for_content_type(comment.content_type):
        return render_to_response(
            "django_comments_xtd/max_thread_level.html", 
            {'max_level': settings.COMMENTS_XTD_MAX_THREAD_LEVEL},
            context_instance=RequestContext(request))

    form = get_form()(comment.content_object, comment=comment)
    next = request.GET.get("next", reverse("comments-xtd-sent"))

    template_arg = [
        "django_comments_xtd/%s/%s/reply.html" % (
            comment.content_type.app_label, 
            comment.content_type.model),
        "django_comments_xtd/%s/reply.html" % (
            comment.content_type.app_label,),
        "django_comments_xtd/reply.html"
    ]
    return render_to_response(template_arg, 
                              {"comment": comment, "form": form, "next": next },
                              context_instance=RequestContext(request))

def mute(request, key):
    try:
        comment = signed.loads(str(key), 
                               extra_key=settings.COMMENTS_XTD_SALT)
    except (ValueError, signed.BadSignature):
        raise Http404
    # the comment does exist if the URL was already confirmed, then: Http404
    if not comment.followup or not _comment_exists(comment):
        raise Http404

    # Send signal that the comment thread has been muted
    signals.comment_thread_muted.send(sender=XtdComment,
                                      comment=comment,
                                      request=request)

    XtdComment.objects.filter(
        content_type=comment.content_type, object_pk=comment.object_pk, 
        is_public=True, followup=True, user_email=comment.user_email
    ).update(followup=False)

    model = models.get_model(comment.content_type.app_label,
                             comment.content_type.model)
    target = model._default_manager.get(pk=comment.object_pk)
    
    template_arg = [
        "django_comments_xtd/%s/%s/muted.html" % (
            comment.content_type.app_label, 
            comment.content_type.model),
        "django_comments_xtd/%s/muted.html" % (
            comment.content_type.app_label,),
        "django_comments_xtd/muted.html"
    ]
    return render_to_response(template_arg, 
                              {"content_object": target },
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-comments-xtd documentation build configuration file, created by
# sphinx-quickstart on Mon Dec 19 19:20:12 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-comments-xtd'
copyright = u'2014, Daniel Rus Morales'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# import django_comments_xtd
# The short X.Y version.
version = '1.3'
# The full version, including alpha/beta/rc tags.
release = '1.3a1'

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
#html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

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
htmlhelp_basename = 'django-comments-xtddoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-comments-xtd.tex', u'django-comments-xtd Documentation',
   u'Daniel Rus Morales', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-comments-xtd', u'django-comments-xtd Documentation',
     [u'Daniel Rus Morales'], 1)
]



########NEW FILE########
__FILENAME__ = runtests
import os
import sys

def setup_django_settings():
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, os.getcwd())
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"


def run_tests():
    if not os.environ.get("DJANGO_SETTINGS_MODULE", False):
        setup_django_settings()

    from django.conf import settings
    from django.test.utils import get_runner

    runner = get_runner(settings,"django.test.simple.DjangoTestSuiteRunner")
    test_suite = runner(verbosity=2, interactive=True, failfast=False)
    return test_suite.run_tests(["django_comments_xtd"])


if __name__ == "__main__":
    run_tests()

########NEW FILE########
__FILENAME__ = settings
#-*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.sqlite3', 
        'NAME':     'django_comments_xtd_test',
        'USER':     '', 
        'PASSWORD': '', 
        'HOST':     '', 
        'PORT':     '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

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

SECRET_KEY = 'v2824l&2-n+4zznbsk9c-ap5i)b3e8b+%*a=dxqlahm^%)68jn'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'django_comments_xtd.tests.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), "..", "templates"),
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.comments',
    'django_comments_xtd',
    'django_comments_xtd.tests',
]
COMMENTS_APP = "django_comments_xtd"

COMMENTS_XTD_CONFIRM_EMAIL = True
COMMENTS_XTD_SALT = b"es-war-einmal-una-bella-princesa-in-a-beautiful-castle"
COMMENTS_XTD_MAX_THREAD_LEVEL = 2
COMMENTS_XTD_MAX_THREAD_LEVEL_BY_APP_MODEL = {'tests.diary': 0}

########NEW FILE########
