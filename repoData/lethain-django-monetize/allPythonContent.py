__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = monetize
"""
Contains the template tags used to facilitate the django_monetize app.

Usage (from within a template):

    {% load monetize %}
    
    {% monetize_slot "top" object.tags %}

    <p> Some content. </p>
    {% monetize_slot "bottom" request.META.HTTP_USER_AGENT %}

    <div class="sidebar">
    {% monetize_slot "side bar" request.META object.tags "django" %}
    </div>


In the first of those examples we are targeting monetization using an object's tags, and in the second example we are targeting monetization using a request's user agent.

The third example (at the "side bar" slot) shows passing an arbitrary number of dictionaries, lists and strings into the slot. Excluding the first parameter, which is the name of the slot, they will be systematically searched for values specified in your ``MONETIZE_TARGET`` dictionary.

The first value matching a targeting value will be used. Values will be matched as follows:

1.  It will sensibly match against the contents of lists, tuples
    and dictionaries, but **all other objects will be matched by
    using the value returned by their __repr__ method**.

2.  **String/Unicode objects** will be matched against the keys
    in the ``MONETIZE_TARGET`` dictionary. (If you specify "django"
    it will check for a key named "django" and use its targeting logic.)

3.  **Lists/Tuples** will be stepped through, with each value being checked against the keys in the ``MONETIZE_TARGET`` dictionary.

4.  **Dictionaries** will be replaced by a list of their items, which will then be processed normally as a list.

5.  The **None** value will be ignored.

6.  If there are no matches, then the system will fall back onto the ``MONETIZE_DEFAULT`` value. If ``MONETIZE_DEFAULT`` is not specified (or its value is NONE) then it will simply return an empty string.


Don't be fooled by the above example: ``django_monetize`` doesn't help you inject ``request`` into your templates' context; you'll have to handle that yourself.
"""

from django import template
from django.conf import settings

register = template.Library()

@register.tag(name="monetize_slot")
def monetize_slot(parser, token):
    'Template tag for displaying a monetization option in a slot.'
    lst = token.split_contents()
    return MonetizeSlotNode(*lst[1:])


class MonetizeSlotNode(template.Node):
    def __init__(self, *vals):
        if len(vals) > 0:
            self.slot = vals[0].strip('"')
            self.params = vals[1:]
        else:
            self.slot = None
            self.params = ()

    def render(self,context):
        'Apply targeting and render monetization option for value/slot combo.'
        target = self.acquire_target(self.params,context)
        return self.target(target,self.slot,context)

    def acquire_target(self,params,context):
        'Go through parameters and try to find a valid targeting parameter.'
        logic_dict = getattr(settings,'MONETIZE_TARGET',{})

        for param in params:
            try:
                param = template.resolve_variable(param,context)
            except template.VariableDoesNotExist:
                pass
            if type(param) == dict:
                param = dict.iteritems()

            if hasattr(param,'__iter__'):
                for x in param:
                    x = unicode(x)
                    if logic_dict.has_key(x):
                        return x
            else:
                param = unicode(param)
                if logic_dict.has_key(param):
                    return param

        return None

    def target(self,value,slot,context):
        '''
        Returns the rendered text for 'value'. 'value' should be
        the output of the 'choose_target' method.

        Also be aware the distinction being made between
        False and None. None refers to the concept of using
        the default monetization option, while False refers
        to not using a monetization option.
        '''
        logic_dict = getattr(settings,'MONETIZE_TARGET',{})
        if logic_dict.has_key(value):
            logic = logic_dict[value]
        else:
            logic = getattr(settings,"MONETIZE_DEFAULT",False)

        # Deconstruct slot specific logic from dict.
        if type(logic) == dict:
            if logic.has_key(slot):
                # Check for slot specific logic.
                logic = logic[slot]
            elif logic.has_key(None):
                # Check for value specific default logic.
                logic = logic[None]
            else:
                # Otherwise display nothing.
                logic = False

        if type(logic) == tuple or type(logic) == list:
            context_dict = getattr(settings,'MONETIZE_CONTEXT',{}).copy()
            if len(logic) == 0:
                logic = False
            else:
                # load extra context from list
                for key,val in logic[1:]:
                    context_dict[key] = val
                logic = logic[0]
        else:
            context_dict = getattr(settings,'MONETIZE_CONTEXT',{})

        # At this point ``logic`` should be a string for a template, or False
        if logic == False:
            # False means no monetization option, so return empty string.
            rendered = u""
        else:
            new_context = template.Context(context_dict,context.autoescape)
            t = template.loader.get_template(logic)
            rendered = t.render(new_context)

        return rendered

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
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
__FILENAME__ = settings
# Django settings for monetize_project project.

import os
ROOT_PATH = os.path.dirname(__file__)



MONETIZE_CONTEXT = {
    # Amazon Honor System
    'amazon_paypage':'url',

    # Amazon Affilliates (used for all others)
    'amazon_affiliates_id':'affiliates_id',

    # Amazon Affiliates: Custom Links
    'amazon_custom_link_title':'Look at the Kindle!',
    'amazon_custom_link_url':'http://www.amazon.com/etc/etc',

    # Amazon Affilliates: Omakase
    'amazon_omakase_width':'728',
    'amazon_omakase_height':'90',

    # Amazon Affiliates: Search
    'amazon_search_terms':"Django book",
    'amazon_search_title':"Search for Django books!",

    # Slicehost Referrals
    'slicehost_referral_id':'slicehost referal id',

    # Dreamhost Referrals
    'dreamhost_referral_code':'dreamhost referal id',

    # Google AdSense: Ad Unit
    'adsense_ad_unit_client':'ad unit client',
    'adsense_ad_unit_slot':'ad slot id',
    'adsense_ad_unit_width':'336',
    'adsense_ad_unit_height':'280',

    # Paypal
    'paypal_business':'email',
    'paypal_item_name':'name',
    'paypal_currency_code':'USD',
    'paypal_amount':None, # '5.00',
    'paypal_tax':'0',
    'paypal_lc':'US',
    'paypal_bn':'PP-DonationsBF',
    'paypal_image':'http://www.paypal.com/en_US/i/btn/btn_donate_LG.gif'
}

MONETIZE_TARGET = {
    'django':'django_monetize/amazon_search.html',
    'python':'django_monetize/paypal_donate.html',

}

MONETIZE_DEFAULT = 'django_monetize/slicehost_referral.html'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Make this unique, and don't share it with anybody.
SECRET_KEY = '#==th24xb_-*gpf-ovp@91cb+atycl-rlwc(jnim-j5erag^6t'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'monetize_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ROOT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'django_monetize',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

tags = ['python','ruby','django']

urlpatterns = patterns('django.views.generic.simple',
    (r'^$','direct_to_template', {'template': 'sample.html','extra_context':{'tags':tags},}),
)

########NEW FILE########
