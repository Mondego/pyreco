__FILENAME__ = models
class SortableInline(object):
    sortable_field_name = "position"

    class Media:
        js = (
            'admin/js/jquery.sortable.js',
        )

        css = {
            'all': ('admin/css/admin-inlines.css', )
        }

class CollapsibleInline(object):
    start_collapsed = False

########NEW FILE########
__FILENAME__ = models


########NEW FILE########
__FILENAME__ = bootstrapped_goodies_tags
from django import template
from django.template.loader import render_to_string, TemplateDoesNotExist

register = template.Library()


@register.simple_tag(takes_context=True)
def render_with_template_if_exist(context, template, fallback):
    text = fallback
    try:
        text = render_to_string(template, context)
    except:
        pass
    return text

@register.simple_tag(takes_context=True)
def language_selector(context):
    """ displays a language selector dropdown in the admin, based on Django "LANGUAGES" context.
        requires:
            * USE_I18N = True / settings.py
            * LANGUAGES specified / settings.py (otherwise all Django locales will be displayed)
            * "set_language" url configured (see https://docs.djangoproject.com/en/dev/topics/i18n/translation/#the-set-language-redirect-view)
    """
    output = ""
    from django.conf import settings
    i18 = getattr(settings, 'USE_I18N', False)
    if i18:
        template = "admin/language_selector.html"
        context['i18n_is_set'] = True
        try:
            output = render_to_string(template, context)
        except:
            pass
    return output


@register.filter(name='column_width')
def column_width(value):
    return 12/len(list(value))
########NEW FILE########
__FILENAME__ = widgets
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse, NoReverseMatch
from django.forms.widgets import Select
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe


def silent_reverse(url):
    try:
        return reverse(url)
    except NoReverseMatch:
        return ''


class GenericContentTypeSelect(Select):
    allow_multiple_selected = False

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_text(option_value)
        extra_attrs = {}
        if option_value:
            ct = ContentType.objects.get(pk=option_value)
            extra_attrs = {
                'data-generic-lookup-enabled': 'yes',
                'data-admin-url': silent_reverse('admin:{0.app_label}_' \
                                             '{0.name}_changelist'.format(ct)),
            }

        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return format_html('<option value="{0}"{1} {2}>{3}</option>',
                           option_value,
                           selected_html,
                           mark_safe(' '.join(['{0}="{1}"'.format(k, v) \
                                            for k, v in extra_attrs.items()])),
                           force_text(option_label))

    class Media(object):
        js = ('admin/js/generic-lookup.js', )

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from .models import CapitalModel

# Register your models here.
admin.site.register(CapitalModel)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.
class CapitalModel(models.Model):
  name = models.TextField()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

# Create your tests here.

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_django_admin_bootstrapped.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django_admin_bootstrapped.admin.models import SortableInline
from .models import TestMe, TestThat, TestMeProxyForFieldsets, TestSortable


class TestThatStackedInline(admin.StackedInline):
    model = TestThat


class TestThatTabularInline(admin.TabularInline):
    model = TestThat


class TestSortable(admin.StackedInline, SortableInline):
    model = TestSortable
    extra = 0


class TestMeAdmin(admin.ModelAdmin):
    list_display = ['test_ip', 'test_url', 'test_int', 'test_img', 'test_file', 'test_date', 'test_char', 'test_bool', 'test_time', 'test_slug', 'test_text', 'test_email', 'test_float', 'test_bigint', 'test_positive_integer', 'test_decimal', 'test_comma_separated_int', 'test_small_int', 'test_nullbool', 'test_filepath', 'test_positive_small_int', ]
    search_fields = ['test_int', ]
    list_editable = ['test_int', ]
    list_filter = ['test_ip', 'test_url', 'test_int', ]
    list_per_page = 3
    date_hierarchy = 'test_date'
    inlines = [TestThatStackedInline, TestThatTabularInline, TestSortable]
    save_as = True
    save_on_top = True


class TestMeAdminFieldsets(TestMeAdmin):
    actions_on_bottom = True
    fieldsets = (
        ('A fieldset', {
            'fields': ['test_m2m', 'test_ip', 'test_url', 'test_int', 'test_img', 'test_file', 'test_date', 'test_char', 'test_bool', 'test_time', 'test_slug', 'test_text', ],
        }),
        ('Another fieldset', {
            'fields': ['test_email', 'test_float', 'test_bigint', 'test_positive_integer', 'test_decimal', 'test_comma_separated_int', 'test_small_int', 'test_nullbool', 'test_filepath', 'test_positive_small_int', ],
        }),
    )

admin.site.register(TestMeProxyForFieldsets, TestMeAdminFieldsets)
admin.site.register(TestMe, TestMeAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class TestMe(models.Model):
    test_m2m = models.ManyToManyField('self', blank=True, help_text="Lorem dolor")
    test_ip = models.IPAddressField(help_text="Lorem dolor")
    test_url = models.URLField(help_text="Lorem dolor")
    test_int = models.IntegerField(help_text="Lorem dolor")
    test_img = models.ImageField(upload_to='dummy', blank=True)
    test_file = models.FileField(upload_to='dummy', blank=True)
    test_date = models.DateField(help_text="Lorem dolor")
    test_char = models.CharField(max_length=50, help_text="Lorem dolor")
    test_bool = models.BooleanField(help_text="Lorem dolor")
    test_time = models.TimeField(help_text="Lorem dolor")
    test_slug = models.SlugField(help_text="Lorem dolor")
    test_text = models.TextField(help_text="Lorem dolor")
    test_email = models.EmailField(help_text="Lorem dolor")
    test_float = models.FloatField(help_text="Lorem dolor")
    test_bigint = models.BigIntegerField(help_text="Lorem dolor")
    test_positive_integer = models.PositiveIntegerField(help_text="Lorem dolor")
    test_decimal = models.DecimalField(max_digits=5, decimal_places=2, help_text="Lorem dolor")
    test_comma_separated_int = models.CommaSeparatedIntegerField(max_length=100, help_text="Lorem dolor")
    test_small_int = models.SmallIntegerField(help_text="Lorem dolor")
    test_nullbool = models.NullBooleanField(help_text="Lorem dolor")
    test_filepath = models.FilePathField(blank=True, help_text="Lorem dolor")
    test_positive_small_int = models.PositiveSmallIntegerField(help_text="Lorem dolor")

    class Meta:
        verbose_name = u'Test me'
        verbose_name_plural = u'Lot of Test me'


class TestMeProxyForFieldsets(TestMe):
    class Meta:
        proxy = True
        verbose_name = u'Test me fieldsets'
        verbose_name_plural = u'Lot of Test me fieldsets'


class TestThat(models.Model):
    that = models.ForeignKey(TestMe, help_text="Lorem dolor")
    test_ip = models.IPAddressField(help_text="Lorem dolor")
    test_url = models.URLField(help_text="Lorem dolor")
    test_int = models.IntegerField(help_text="Lorem dolor")
    test_date = models.DateField(help_text="Lorem dolor")
    test_bool = models.BooleanField(help_text="Lorem dolor")

    class Meta:
        verbose_name = u'Test that'
        verbose_name_plural = u'Lot of Test that'


class TestSortable(models.Model):
    that = models.ForeignKey(TestMe)
    position = models.PositiveSmallIntegerField("Position")
    test_char = models.CharField(max_length=5)

    class Meta:
        ordering = ('position', )

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for test_django_admin_bootstrapped project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '3!^@q06fn2-zl%2f%rmux58ybi9u=9k_lq^k*+^429foc#7fzn'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django_admin_bootstrapped.bootstrap3',
    'django_admin_bootstrapped',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'test_django_admin_bootstrapped',
    'CapitalApp',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'test_django_admin_bootstrapped.urls'

WSGI_APPLICATION = 'test_django_admin_bootstrapped.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_django_admin_bootstrapped_p3.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for test_django_admin_bootstrapped_p3 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_django_admin_bootstrapped_p3.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
