__FILENAME__ = admin
from django.contrib import admin

from solo.admin import SingletonModelAdmin

from config.models import SiteConfiguration


admin.site.register(SiteConfiguration, SingletonModelAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    site_name = models.CharField(max_length=255, default='Site Name')
    maintenance_mode = models.BooleanField(default=False)

    def __unicode__(self):
        return u"Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

########NEW FILE########
__FILENAME__ = admin
from django.conf.urls import url, patterns
from django.contrib import admin
from django.http import HttpResponseRedirect
try:
    from django.utils.encoding import force_unicode
except ImportError:
    from django.utils.encoding import force_text as force_unicode 
from django.utils.translation import ugettext as _


class SingletonModelAdmin(admin.ModelAdmin):
    object_history_template = "admin/solo/object_history.html"
    change_form_template = "admin/solo/change_form.html"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super(SingletonModelAdmin, self).get_urls()
        url_name_prefix = '%(app_name)s_%(model_name)s' % {
            'app_name': self.model._meta.app_label,
            'model_name': self.model._meta.module_name,
        }
        custom_urls = patterns('',
            url(r'^history/$',
                self.admin_site.admin_view(self.history_view),
                {'object_id': '1'},
                name='%s_history' % url_name_prefix),
            url(r'^$',
                self.admin_site.admin_view(self.change_view),
                {'object_id': '1'},
                name='%s_change' % url_name_prefix),
        )
        # By inserting the custom URLs first, we overwrite the standard URLs.
        return custom_urls + urls

    def response_change(self, request, obj):
        msg = _('%(obj)s was changed successfully.') % {'obj': force_unicode(obj)}
        if '_continue' in request.POST:
            self.message_user(request, msg + ' ' + _('You may edit it again below.'))
            return HttpResponseRedirect(request.path)
        else:
            self.message_user(request, msg)
            return HttpResponseRedirect("../../")

    def change_view(self, request, object_id, extra_context=None):
        if object_id == '1':
            self.model.objects.get_or_create(pk=1)
        return super(SingletonModelAdmin, self).change_view(
            request,
            object_id,
            extra_context=extra_context,
        )

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.core.cache import get_cache
from django.db import models

from solo import settings as solo_settings


class SingletonModel(models.Model):

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        self.set_to_cache()
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def set_to_cache(self):
        cache_name = getattr(settings, 'SOLO_CACHE', solo_settings.SOLO_CACHE)
        if not cache_name:
            return None
        cache = get_cache(cache_name)
        cache_key = self.get_cache_key()
        timeout = getattr(settings, 'SOLO_CACHE_TIMEOUT', solo_settings.SOLO_CACHE_TIMEOUT)
        cache.set(cache_key, self, timeout)

    @classmethod
    def get_cache_key(cls):
        prefix = solo_settings.SOLO_CACHE_PREFIX
        return '%s:%s' % (prefix, cls.__name__.lower())

    @classmethod
    def get_solo(cls):
        cache_name = getattr(settings, 'SOLO_CACHE', solo_settings.SOLO_CACHE)
        if not cache_name:
            obj, creted = cls.objects.get_or_create(pk=1)
            return obj
        cache = get_cache(cache_name)
        cache_key = cls.get_cache_key()
        obj = cache.get(cache_key)
        if not obj:
            obj, created = cls.objects.get_or_create(pk=1)
            obj.set_to_cache()
        return obj

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

GET_SOLO_TEMPLATE_TAG_NAME = getattr(settings,
    'GET_SOLO_TEMPLATE_TAG_NAME', 'get_solo')

# The cache that should be used, e.g. 'default'. Refers to Django CACHES setting.
# Set to None to disable caching.
SOLO_CACHE = None

SOLO_CACHE_TIMEOUT = 60*5

SOLO_CACHE_PREFIX = 'solo'

########NEW FILE########
__FILENAME__ = solo_tags
from django import template
from django.db import models
from django.utils.translation import ugettext as _

from solo import settings as solo_settings


register = template.Library()


@register.assignment_tag(name=solo_settings.GET_SOLO_TEMPLATE_TAG_NAME)
def get_solo(model_path):
    try:
        app_label, model_name = model_path.rsplit('.', 1)
    except ValueError:
        raise template.TemplateSyntaxError(_(
            "Templatetag requires the model dotted path: 'app_label.ModelName'. "
            "Received '%s'." % model_path
        ))
    model_class = models.get_model(app_label, model_name)
    if not model_class:
        raise template.TemplateSyntaxError(_(
            "Could not get the model name '%(model)s' from the application "
            "named '%(app)s'" % {
                'model': model_name,
                'app': app_label,
            }
        ))
    return model_class.get_solo()

########NEW FILE########
__FILENAME__ = models
from django.db import models

from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    site_name = models.CharField(max_length=255, default='Default Config')

    def __unicode__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'solo-tests.db',
    }
}

INSTALLED_APPS = (
    'solo',
    'solo.tests',
)

SECRET_KEY = 'any-key'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': '127.0.0.1:11211',
    },
}

SOLO_CACHE = 'default'

########NEW FILE########
__FILENAME__ = tests
from django.core.cache import get_cache
from django.template import Template, Context
from django.test import TestCase

from django.test.utils import override_settings
from solo.tests.models import SiteConfiguration


class SigletonTest(TestCase):

    def setUp(self):
        self.template = Template(
            '{% load solo_tags %}'
            '{% get_solo "tests.SiteConfiguration" as site_config  %}'
            '{{ site_config.site_name }}'
        )
        self.cache = get_cache('default')
        self.cache_key = SiteConfiguration.get_cache_key()
        self.cache.clear()
        SiteConfiguration.objects.all().delete()

    def test_template_tag_renders_default_site_config(self):
        SiteConfiguration.objects.all().delete()
        # At this point, there is no configuration object and we expect a
        # one to be created automatically with the default name value as
        # defined in models.
        output = self.template.render(Context())
        self.assertIn('Default Config', output)

    def test_template_tag_renders_site_config(self):
        SiteConfiguration.objects.create(site_name='Test Config')
        output = self.template.render(Context())
        self.assertIn('Test Config', output)

    @override_settings(SOLO_CACHE='default')
    def test_template_tag_uses_cache_if_enabled(self):
        SiteConfiguration.objects.create(site_name='Config In Database')
        fake_configuration = {'site_name': 'Config In Cache'}
        self.cache.set(self.cache_key, fake_configuration, 10)
        output = self.template.render(Context())
        self.assertNotIn('Config In Database', output)
        self.assertNotIn('Default Config', output)
        self.assertIn('Config In Cache', output)

    @override_settings(SOLO_CACHE=None)
    def test_template_tag_uses_database_if_cache_disabled(self):
        SiteConfiguration.objects.create(site_name='Config In Database')
        fake_configuration = {'site_name': 'Config In Cache'}
        self.cache.set(self.cache_key, fake_configuration, 10)
        output = self.template.render(Context())
        self.assertNotIn('Config In Cache', output)
        self.assertNotIn('Default Config', output)
        self.assertIn('Config In Database', output)

########NEW FILE########
