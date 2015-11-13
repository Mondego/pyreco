__FILENAME__ = admin
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

csrf_protect_m = method_decorator(csrf_protect)


class PreferencesAdmin(admin.ModelAdmin):

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        If we only have a single preference object redirect to it,
        otherwise display listing.
        """
        model = self.model
        if model.objects.all().count() > 1:
            return super(PreferencesAdmin, self).changelist_view(request)
        else:
            obj = model.singleton.get()
            return redirect(reverse('admin:preferences_%s_change' % \
                    model._meta.module_name, args=(obj.id,)))

########NEW FILE########
__FILENAME__ = context_processors
from preferences import preferences


def preferences_cp(request):
    """
    Adds preferences to template context when used
    through TEMPLATE_CONTEXT_PROCESSORS setting.
    """
    return {'preferences': preferences}

########NEW FILE########
__FILENAME__ = managers
from django.conf import settings
from django.db import models
from django.contrib.sites.models import Site


class SingletonManager(models.Manager):
    """
    Returns only a single preferences object per site.
    """
    def get_query_set(self):
        """
        Return the first preferences object for the current site.
        If preferences do not exist create it.
        """
        queryset = super(SingletonManager, self).get_query_set()

        # Get current site
        current_site = None
        if getattr(settings, 'SITE_ID', None) != None:
            current_site = Site.objects.get_current()

        # If site found limit queryset to site.
        if current_site != None:
            queryset = queryset.filter(sites=settings.SITE_ID)

        try:
            queryset.get()
        except self.model.DoesNotExist:
            # Create object (for current site) if it doesn't exist.
            obj = self.model.objects.create()
            if current_site != None:
                obj.sites.add(current_site)

        return queryset

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.dispatch import receiver

import preferences
from preferences.managers import SingletonManager


class Preferences(models.Model):
    singleton = SingletonManager()
    sites = models.ManyToManyField('sites.Site', null=True, blank=True)

    def __unicode__(self):
        """
        Include site names.
        """
        site_names = [site.name for site in self.sites.all()]
        prefix = self._meta.verbose_name_plural.capitalize()

        if len(site_names) > 1:
            return '%s for sites %s and %s.' % (prefix, ', '.\
                    join(site_names[:-1]), site_names[-1])
        elif len(site_names) == 1:
            return '%s for site %s.' % (prefix, site_names[0])
        return '%s without assigned site.' % prefix


@receiver(models.signals.class_prepared)
def preferences_class_prepared(sender, *args, **kwargs):
    """
    Adds various preferences members to preferences.preferences,
    thus enabling easy access from code.
    """
    cls = sender
    if issubclass(cls, Preferences):
        # Add singleton manager to subclasses.
        cls.add_to_class('singleton', SingletonManager())
        # Add property for preferences object to preferences.preferences.
        setattr(preferences.Preferences, cls._meta.object_name, \
                property(lambda x: cls.singleton.get()))


@receiver(models.signals.m2m_changed)
def site_cleanup(sender, action, instance, **kwargs):
    """
    Make sure there is only a single preferences object per site.
    So remove sites from pre-existing preferences objects.
    """
    if action == 'post_add':
        if isinstance(instance, Preferences):
            site_conflicts = instance.__class__.objects.filter(\
                    sites__in=instance.sites.all()).distinct()

            for conflict in site_conflicts:
                if conflict != instance:
                    for site in instance.sites.all():
                        conflict.sites.remove(site)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from preferences.admin import PreferencesAdmin
from preferences.tests.models import MyPreferences

admin.site.register(MyPreferences, PreferencesAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from preferences.models import Preferences


class MyPreferences(Preferences):
    __module__ = 'preferences.models'
    portal_contact_email = models.EmailField()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import include, patterns

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = test_settings
DATABASE_ENGINE = 'sqlite3'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'preferences',
    'preferences.tests',
]

TEMPLATE_CONTEXT_PROCESSORS = (
    'preferences.context_processors.preferences_cp',
)

ROOT_URLCONF='preferences.tests.urls'

########NEW FILE########
