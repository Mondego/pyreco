__FILENAME__ = manage
#!/usr/bin/env python

#add faq app to python path
import sys
from os.path import abspath, dirname, join
sys.path.append(abspath(join(dirname(__file__), '..')))

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
__FILENAME__ = settings
# Django settings for [name] project.
import os, os.path, sys

#set DEBUG = False and django will send exception emails
DEBUG = True 
TEMPLATE_DEBUG = DEBUG
PROJECT_DIR = os.path.dirname(__file__)

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'pressbox.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be avilable on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
#MEDIA_URL = 'http://127.0.0.1:8000/site_media/'
MEDIA_URL = '/media/' #

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'c#zi(mv^n+4te_sy$hpb*zdo7#f7ccmp9ro84yz9bmmfqj9y*c'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
	'django.core.context_processors.media',
)

MIDDLEWARE_CLASSES = (
	#'django.middleware.cache.CacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'example.urls'

INTERNAL_IPS = (
    '127.0.0.1',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    [os.path.join(PROJECT_DIR, "templates")]
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'pressbox',
)


try:
   from local_settings import *
except ImportError:
   pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
from django.views.generic.simple import direct_to_template

from pressbox import urls as pressbox_urls
from pressbox.views import press_detail, press_list, press_regroup, press_with_templatetag

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
    url (
        regex = r'^press/$',
        view = press_list,
        name = 'press_list',
        ),
    url (
        regex = r'^press_regroup/$',
        view = press_regroup,
        name = 'press_regroup',
        ),
    url (
        regex = r'^press_bytag/$',
        view = press_with_templatetag,
        name = 'press_with_templatetag',
        ),
    url (
        regex = r'^press/(?P<slug>[-\w]+)/$',
        view = press_detail,
        name = 'press_detail',
        ),
    url (
        r'^$',
        direct_to_template,
        {'template': 'home.html'},
        name = 'home',
        ),
)

urlpatterns += patterns('',
	(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from pressbox.models import PressItem, PressImage, PressCategory
from pressbox.forms import PressItemForm

class PressImageInline(admin.StackedInline):
    extra = 2
    max_num = 8
    model = PressImage


class PressItemAdmin(admin.ModelAdmin):
    model = PressItem    
    form = PressItemForm
    prepopulated_fields = {'slug':("title",),}
    
    search_fields = ('title',)
    list_display = ('title', 'published_on','is_active')
    inlines = [
      PressImageInline
    ]

class PressCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':("title",),}

admin.site.register(PressItem, PressItemAdmin)
admin.site.register(PressImage)
admin.site.register(PressCategory, PressCategoryAdmin)
########NEW FILE########
__FILENAME__ = forms
from django import forms

class PressItemForm(forms.ModelForm):
    short_description = forms.CharField(widget=forms.Textarea())

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models.query import QuerySet
import datetime

class PressItemManager(models.Manager):
    """
    A basic ''Manager'' subclass. It provides access to helpful utility methods.  
    """
    
    def active(self,):
        qs = self.get_query_set().filter(is_active__exact=True)
        return qs

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models import permalink
from pressbox.managers import PressItemManager

class ModelBase(models.Model):
    """
    Abstract base class for all model instances in django-pressbox.
    
    """
    created_on = models.DateTimeField(_('created on'), default=datetime.now, 
        editable=False, )
    updated_on = models.DateTimeField(_('updated on'), editable=False)

    class Meta:
        abstract = True

    def save(self):
        self.updated_on = datetime.now()    
        super(ModelBase, self).save()

class PressCategory(models.Model):
    """
    Represents a category for organizing press items.
    
    """
    
    title = models.CharField(_('title'), max_length=100, unique=True)
    slug = models.SlugField(_('slug field'), unique=True)
    sort_order = models.PositiveIntegerField(_('sort order'), default=0)
    
    class Meta:
        verbose_name = _('press category')
        verbose_name_plural = _('press categories')
        ordering = ['sort_order', '-title']

    def __unicode__(self):
        return self.title

class PressItem(ModelBase):
    """
    Represents a press release or any unique press item.
    
    """
    
    title = models.CharField(_('title'), max_length=100)
    slug = models.SlugField(_('slug'), unique_for_date="published_on")
    category = models.ForeignKey(PressCategory, related_name="press_items")
    short_description = models.CharField(_('short descrption'), 
        max_length=500, blank=True, null=True, help_text=_("Max 500 characters."))
    body =  models.TextField(_('body'), blank=True, null=True)
    published_on = models.DateField(_('published on'), blank=False, null=True)
    download_file = models.FileField(_('downloadable file'), blank=True, 
        null=True, upload_to='uploads/pressbox')
    download_title = models.CharField(_('downloadabe file title'), max_length=255, blank=True, null=True)
    sort_order = models.PositiveIntegerField(_('sort order'), default=0)
    is_active = models.BooleanField(_('is active'), default=True)
    
    objects = PressItemManager()

    class Meta:
        verbose_name = _("press item")
        verbose_name_plural = _("press items")
        ordering = ['sort_order', '-published_on',]

    def __unicode__(self):
        return self.title
    
    @property
    def main_image(self):
        """ Returns either the first sorted image for the associated press images. """
        try:
            return images.all()[0]
        except:
            return None
        
    @permalink
    def get_absolute_url(self):
        return ('press_detail', None, {
            'slug': self.slug,
        })
        

class PressImage(models.Model):
    """
    Represents an image related to a press item.
    
    """

    press_item = models.ForeignKey(PressItem, related_name='images')
    image = models.ImageField(_('image'), upload_to='uploads/pressbox' )
    alt_text = models.CharField(_('alt text'), max_length=50, blank=True, 
        null=True)
    sort_order = models.PositiveIntegerField(_('sort order'))

    class Meta:
        verbose_name = _("press image")
        verbose_name_plural = _("press images")
        ordering = ['-sort_order', '-created_on', ]
        
    def save(self):
        self.updated_on = datetime.now()
        super(PressImage,self).save()

    def __unicode__(self):
        return self.alt_text
        
    class Meta:
        ordering = ['sort_order',]
    
    

########NEW FILE########
__FILENAME__ = press_items
import datetime
from django import template
from django.conf import settings
from pressbox.models import PressItem, PressImage, PressCategory

register = template.Library()

@register.inclusion_tag('includes/templatetags/press_items.html', takes_context=True)
def press_items(context, max=10):
    items = PressItem.objects.active()
    return {
        'objects': items[:max],
    }
    
@register.inclusion_tag('includes/templatetags/press_item.html', takes_context=True)
def press_item(context):
    return context
    
 
@register.inclusion_tag('includes/templatetags/press_items_by_category.html', takes_context=True)
def press_items_by_category(context):
    items = PressCategory.objects.all()
    return {
        'objects': items,
    }  
    

def do_get_press_category_items(parser, token):
    """    
    A template tag to retrieve PressCategory by slug.
    
    Example:
    
    {% get_category_press_items "press-release" as category %}
    
    """
    
    import re
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name
    format_string, var_name = m.groups()
    if not (format_string[0] == format_string[-1] and format_string[0] in ('"', "'")):
        raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name
    return PressCategoryNode(format_string[1:-1], var_name)

class PressCategoryNode(template.Node):
    """ """
    
    def __init__(self, slug, var_name):
       self.slug = slug
       self.var_name = var_name

    def render(self, context):
        try:
            category = PressCategory.objects.get(slug=self.slug)
        except PressCategory.DoesNotExist:
            category = None
        
        context[self.var_name] = category
        return ''

register.tag('get_category_press_items', do_get_press_category_items)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from pressbox.views import press_detail, press_list


urlpatterns = patterns('',

url(r'^(?P<slug>[-\w]+)/$', 
    view = press_detail, 
    name= 'press_detail'),

url(r'^$', 
    view = press_list, 
    name = 'press_list'),
    
)

#TODO:
#RSS press items
########NEW FILE########
__FILENAME__ = views
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template import RequestContext
from django.views.generic import list_detail
from pressbox.models import PressItem

def press_list(request, template_name='pressbox/object_list.html', extra_context={}):
    return render_to_response(template_name, extra_context, RequestContext(request))

def press_regroup(request, template_name='pressbox/object_list_by_category.html', extra_context={}):
    return render_to_response(template_name, extra_context, RequestContext(request))

def press_with_templatetag(request, template_name='pressbox/object_list_by_category_tag.html', extra_context={}):
    return render_to_response(template_name, extra_context, RequestContext(request))

def press_detail(request, slug, template_name='pressbox/object_detail.html', extra_context={}):
    
    return list_detail.object_detail(request,
        queryset = PressItem.objects.active(),
        slug = slug,
        slug_field = "slug",
        template_name = template_name,
        extra_context = extra_context,
    )


########NEW FILE########
