__FILENAME__ = admin
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

from .widgets import FilteredSelectMultipleWrapper, RelatedFieldWidgetWrapper


class EnhancedAdminMixin(object):
    enhance_exclude = ()
    filtered_multiple_wrapper = FilteredSelectMultipleWrapper
    related_widget_wrapper = RelatedFieldWidgetWrapper

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(EnhancedAdminMixin, self).formfield_for_dbfield(db_field, **kwargs)
        if (formfield and db_field.name not in self.enhance_exclude and
            isinstance(formfield.widget, admin.widgets.RelatedFieldWidgetWrapper)):
            request = kwargs.pop('request', None)
            related_modeladmin = self.admin_site._registry.get(db_field.rel.to)
            if related_modeladmin:
                can_change_related = related_modeladmin.has_change_permission(request)
                can_delete_related = related_modeladmin.has_delete_permission(request)
                if isinstance(formfield.widget.widget, admin.widgets.FilteredSelectMultiple):
                    formfield.widget.widget = self.filtered_multiple_wrapper.wrap(formfield.widget.widget)
                widget = self.related_widget_wrapper.wrap(formfield.widget,
                                                          can_change_related,
                                                          can_delete_related)
                formfield.widget = widget
        return formfield

    def delete_view(self, request, object_id, extra_context=None):
        """ Sets is_popup context variable to hide admin header
        """
        if not extra_context:
            extra_context = {}
        extra_context['is_popup'] = request.REQUEST.get('_popup', 0)
        return super(EnhancedAdminMixin, self).delete_view(request, object_id, extra_context)

class EnhancedModelAdminMixin(EnhancedAdminMixin):
    
    def response_change(self, request, obj):
        if '_popup' in request.REQUEST:
            return render_to_response('admin_enhancer/dismiss-change-related-popup.html',
                                     {'obj': obj})
        else:
            return super(EnhancedModelAdminMixin, self).response_change(request, obj)
        
    def delete_view(self, request, object_id, extra_context=None):
        delete_view_response = super(EnhancedModelAdminMixin, self).delete_view(request, object_id, extra_context)
        if (request.POST and '_popup' in request.REQUEST and
            isinstance(delete_view_response, HttpResponseRedirect)):
            return render_to_response('admin_enhancer/dismiss-delete-related-popup.html',
                                     {'object_id': object_id})
        else:
            return delete_view_response

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from ...admin import EnhancedModelAdminMixin

try:
    from cms.admin.pageadmin import PageAdmin, Page

    class EnhancedPageAdmin(EnhancedModelAdminMixin, PageAdmin):
        pass

    admin.site.unregister(Page)
    admin.site.register(Page, EnhancedPageAdmin)
except ImportError:
    raise ImproperlyConfigured("Error while importing django-cms, please check your configuration")

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from ...admin import EnhancedModelAdminMixin

try:
    from cmsplugin_filer_image.admin import ThumbnailOption

    class EnhancedThumbnailOptionAdmin(EnhancedModelAdminMixin,
                                       admin.ModelAdmin):
        list_display = ('name', 'width', 'height')

    admin.site.unregister(ThumbnailOption)
    admin.site.register(ThumbnailOption, EnhancedThumbnailOptionAdmin)
except ImportError:
    raise ImproperlyConfigured("Error while importing cmsplugin_filer, please check your configuration")

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from .. import admin as enhanced_admin

from .models import Author, Book, Character, Theme


class EnhancedModelAdmin(enhanced_admin.EnhancedModelAdminMixin,
                         admin.ModelAdmin):
    pass

class CharacterInline(enhanced_admin.EnhancedAdminMixin,
                      admin.TabularInline):
    model = Character

class BookAdmin(EnhancedModelAdmin):
    inlines = (CharacterInline,)
    filter_horizontal = ('themes',)


admin.site.register(Author, EnhancedModelAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Theme, EnhancedModelAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Collection(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Book(models.Model):
    author = models.ForeignKey(Author)
    collection = models.ForeignKey(Collection, null=True, blank=True)
    themes = models.ManyToManyField('Theme')


class Theme(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class Character(models.Model):
    name = models.CharField(max_length=100)
    book = models.ForeignKey(Book)
    main_theme = models.ForeignKey(Theme)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

from contextlib import contextmanager
import time

from django.contrib.auth.models import User
from django.contrib.admin.tests import AdminSeleniumWebDriverTestCase
from django.core.urlresolvers import reverse


class InteractionTest(AdminSeleniumWebDriverTestCase):
    def setUp(self):
        super(InteractionTest, self).setUp()
        User.objects.create_superuser('super', '', 'secret')

    def wait_for_popup(self, name):
        def popup_is_loaded(driver):
            return driver.current_window_handle == name
        self.wait_until(popup_is_loaded)

    @contextmanager
    def handle_popup(self, trigger):
        initial_window_handle = self.selenium.current_window_handle
        window_handles = set(self.selenium.window_handles)
        try:
            trigger()
            self.wait_until(lambda driver: set(driver.window_handles) != window_handles)
            new_window_handle = (set(self.selenium.window_handles) - window_handles).pop()
            self.selenium.switch_to_window(new_window_handle)
            yield new_window_handle
        finally:
            time.sleep(1)
            self.selenium.switch_to_window(initial_window_handle)

    def test_widget_interactions(self):
        self.admin_login('super', 'secret')
        driver = self.selenium
        driver.get("%s%s" % (self.live_server_url, reverse('admin:tests_book_add')))

        author_select = driver.find_element_by_id('id_author')
        edit_author_btn = driver.find_element_by_id('edit_id_author')
        add_author_btn = driver.find_element_by_id('add_id_author')
        delete_author_btn = driver.find_element_by_id('delete_id_author')

        self.assertIsNone(edit_author_btn.get_attribute('href'))
        self.assertIsNone(delete_author_btn.get_attribute('href'))

        def author_options():
            author_options = author_select.find_elements_by_tag_name('option')
            options_label = []
            selected_option_label = None
            for option in author_options:
                label = option.get_attribute('innerHTML')
                options_label.append(label)
                if option.get_attribute('selected'):
                    selected_option_label = label
            return selected_option_label, options_label

        def interact(button, name):
            with self.handle_popup(button.click):
                driver.implicitly_wait(1)
                driver.find_element_by_id('id_name').clear()
                driver.find_element_by_id('id_name').send_keys(name)
                driver.find_element_by_name('_save').click()
            selected_option_label, options_label = author_options()
            self.assertEqual(['---------', name], options_label)
            self.assertEqual(name, selected_option_label)

        interact(add_author_btn, 'David Abraham')

        self.assertIsNotNone(edit_author_btn.get_attribute('href'))
        self.assertIsNotNone(delete_author_btn.get_attribute('href'))

        interact(edit_author_btn, 'David Abram')

        with self.handle_popup(delete_author_btn.click):
            driver.find_element_by_css_selector('input[type="submit"]').click()

        selected_option_label, options_label = author_options()
        self.assertEqual(['---------'], options_label)
        self.assertEqual('---------', selected_option_label)

        self.assertIsNone(edit_author_btn.get_attribute('href'))
        self.assertIsNone(delete_author_btn.get_attribute('href'))

########NEW FILE########
__FILENAME__ = urls
from django.contrib import admin
from django.conf.urls import patterns, include, url


admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
########NEW FILE########
__FILENAME__ = widgets
from django.contrib.admin.widgets import (FilteredSelectMultiple,
    RelatedFieldWidgetWrapper)
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


class RelatedFieldWidgetWrapper(RelatedFieldWidgetWrapper):
    
    class Media:
        css = {
            'screen': ('admin_enhancer/css/related-widget-wrapper.css',)
        }
        js = ('admin_enhancer/js/related-widget-wrapper.js',)
    
    def __init__(self, *args, **kwargs):
        self.can_change_related = kwargs.pop('can_change_related', None)
        self.can_delete_related = kwargs.pop('can_delete_related', None)
        super(RelatedFieldWidgetWrapper, self).__init__(*args, **kwargs)
    
    @classmethod
    def wrap(cls, wrapper, can_change_related, can_delete_related):
        return cls(wrapper.widget, wrapper.rel, wrapper.admin_site,
                   can_add_related=wrapper.can_add_related,
                   can_change_related=can_change_related,
                   can_delete_related=can_delete_related)
    
    def get_related_url(self, rel_to, info, action, args=[]):
        return reverse("admin:%s_%s_%s" % (info + (action,)),
                       current_app=self.admin_site.name, args=args)
    
    def render(self, name, value, attrs=None, *args, **kwargs):
        if attrs is None:
            attrs = {}
        rel_to = self.rel.to
        info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
        self.widget.choices = self.choices
        attrs['class'] = ' '.join((attrs.get('class', ''), 'related-widget-wrapper'))
        context = {'widget': self.widget.render(name, value, attrs, *args, **kwargs),
                   'name': name,
                   'can_change_related': self.can_change_related,
                   'can_add_related': self.can_add_related,
                   'can_delete_related': self.can_delete_related,}
        if self.can_change_related:
            if value:
                context['change_url'] = self.get_related_url(rel_to, info, 'change', [value])
            template = self.get_related_url(rel_to, info, 'change', ['__pk__'])
            context.update({'change_url_template': template,
                            'change_help_text': _(u'Change related model'),})
        if self.can_add_related:
            context.update({'add_url': self.get_related_url(rel_to, info, 'add'),
                            'add_help_text': _(u'Add another'),})
        if self.can_delete_related:
            if value:
                context['delete_url'] = self.get_related_url(rel_to, info, 'delete', [value])
            template = self.get_related_url(rel_to, info, 'delete', ['__pk__'])
            context.update({'delete_url_template': template,
                            'delete_help_text': _(u'Delete related model'),})
        
        return mark_safe(render_to_string('admin_enhancer/related-widget-wrapper.html', context))

class FilteredSelectMultipleWrapper(FilteredSelectMultiple):

    @classmethod
    def wrap(cls, widget):
        return cls(widget.verbose_name, widget.is_stacked,
                   widget.attrs, widget.choices)

    def render(self, *args, **kwargs):
        output = super(FilteredSelectMultipleWrapper, self).render(*args, **kwargs)
        return mark_safe("<div class=\"related-widget-wrapper\">%s</div>" % output)

########NEW FILE########
__FILENAME__ = test_settings
DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

SITE_ID = 1

ROOT_URLCONF = 'admin_enhancer.tests.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'admin_enhancer.tests',
    'admin_enhancer',
)

STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = 'not-anymore'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

########NEW FILE########
