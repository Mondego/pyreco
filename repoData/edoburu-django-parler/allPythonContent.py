__FILENAME__ = admin
from django.contrib import admin
from django.contrib.admin.widgets import AdminTextInputWidget, AdminTextareaWidget
from parler.admin import TranslatableAdmin
from .models import Article
from parler.forms import TranslatableModelForm, TranslatedField


class ArticleAdminForm(TranslatableModelForm):
    """
    Example form

    Translated fields can be enhanced by manually declaring them:
    """
    title = TranslatedField(widget=AdminTextInputWidget)
    content = TranslatedField(widget=AdminTextareaWidget)


class ArticleAdmin(TranslatableAdmin):
    """
    Example admin.

    Using an empty class would already work,
    but this example shows some additional options.
    """

    # The 'language_column' is provided by the base class:
    list_display = ('title', 'language_column')
    list_filter = ('published',)

    # Example custom form usage.
    form = ArticleAdminForm

    # NOTE: when using Django 1.4, use declared_fieldsets= instead of fieldsets=
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'published'),
        }),
        ("Contents", {
            'fields': ('content',),
        })
    )

    def get_prepopulated_fields(self, request, obj=None):
        # Can't use prepopulated_fields= yet, but this is a workaround.
        return {'slug': ('title',)}



admin.site.register(Article, ArticleAdmin)

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.utils import translation
from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class Article(TranslatableModel):
    """
    Example translatable model.
    """

    # The translated fields:
    translations = TranslatedFields(
        title = models.CharField("Title", max_length=200),
        slug = models.SlugField("Slug", unique=True),
        content = models.TextField()
    )

    # Regular fields
    published = models.BooleanField("Is published", default=False)

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __unicode__(self):
        # Fetching the title just works, as all
        # attributes are proxied to the translated model.
        # Fallbacks are handled as well.
        return self.title

    def get_absolute_url(self):
        # The override is only needed because we use the /##/ prefix by i18n_patterns()
        # If the language is part of the URL parameters, you can pass it directly off course.
        with translation.override(self.get_current_language()):
            return reverse('article-details', kwargs={'slug': self.slug})

    def get_all_slugs(self):
        # Example illustration, how to fetch all slugs in a single query:
        return dict(self.translations.values_list('language_code', 'slug'))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from .views import ArticleListView, ArticleDetailView

urlpatterns = patterns('',
    url(r'^$', ArticleListView.as_view(), name='article-list'),
    url(r'^(?P<slug>[^/]+)/$', ArticleDetailView.as_view(), name='article-details'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import Http404
from django.utils.translation import get_language
from django.views.generic import ListView, DetailView
from .models import Article


class BaseArticleMixin(object):
    # Only show published articles.
    def get_queryset(self):
        return super(BaseArticleMixin, self).get_queryset().filter(published=True)


class ArticleListView(BaseArticleMixin, ListView):
    model = Article
    template_name = 'article/list.html'

    def get_queryset(self):
        # Only show objects translated in the current language.
        language = get_language()
        return super(ArticleListView, self).get_queryset().filter(translations__language_code=language)


class ArticleDetailView(BaseArticleMixin, DetailView):
    model = Article
    slug_field = 'translations__slug'
    template_name = 'article/details.html'  # This works as expected

    def get_object(self, queryset=None):
        slug = self.kwargs['slug']
        language = get_language()
        try:
            return self.get_queryset().get(translations__language_code=language, translations__slug=slug)
        except Article.DoesNotExist as e:
            raise Http404(e)

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
from os.path import join, dirname, realpath

SRC_DIR = dirname(dirname(realpath(__file__)))

# Add parent path,
# Allow starting the app without installing the module.
import sys
sys.path.insert(0, dirname(SRC_DIR))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': SRC_DIR + '/example.db',
    }
}

TIME_ZONE = 'Europe/Amsterdam'
LANGUAGE_CODE = 'en'
SITE_ID = 1

USE_I18N = True
USE_L10N = True

MEDIA_ROOT = join(dirname(__file__), "media")
MEDIA_URL = '/media/'
STATIC_ROOT = join(dirname(__file__), "static")
STATIC_URL = '/static/'

STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '-#@bi6bue%#1j)6+4b&#i0g-*xro@%f@_#zwv=2-g_@n3n_kj5'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',   # Inserted language switcher, easy way to have multiple frontend languages.
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    join(dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    # Apps
    'article',
    'theme1',

    # Dependencies
    'parler',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
         'require_debug_false': {
             '()': 'django.utils.log.RequireDebugFalse',
         }
     },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
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

PARLER_DEFAULT_LANGUAGE = 'en'

PARLER_LANGUAGES = {
    1: (
        {'code': 'en'},
        {'code': 'de'},
        {'code': 'fr'},
        {'code': 'nl'},
        {'code': 'es'},
    ),
    'default': {
        #'fallback': 'en',
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin

admin.autodiscover()

# Patterns are prefixed with the language code.
# This is not mandatory, can also use a `django_language` cookie,
# or custom middleware that calls `django.utils.translation.activate()`.
urlpatterns = i18n_patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('article.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
"""
Translation support for admin forms.
"""
import django
from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m, BaseModelAdmin, InlineModelAdmin
try:
    from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
except ImportError:
    # Django <1.6 does not preserve filters
    def add_preserved_filters(context, form_url):
        return form_url
from django.contrib.admin.util import get_deleted_objects, unquote
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import router
from django.forms import Media
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseRedirect, Http404, HttpRequest
from django.shortcuts import render
from django.utils.encoding import iri_to_uri, force_text
from django.utils.functional import lazy
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _, get_language
from django.utils import six
from parler import appsettings
from parler.forms import TranslatableModelForm
from parler.managers import TranslatableQuerySet
from parler.models import TranslatableModel
from parler.utils.compat import transaction_atomic
from parler.utils.i18n import get_language_title, is_multilingual_project
from parler.utils.views import get_language_parameter, get_language_tabs
from parler.utils.template import select_template_name

# Code partially taken from django-hvad
# which is (c) 2011, Jonas Obrist, BSD licensed


_language_media = Media(css={
    'all': ('parler/admin/language_tabs.css',)
})
_language_prepopulated_media = _language_media + Media(js=(
    'admin/js/urlify.js',
    'admin/js/prepopulate.min.js'
))

_fakeRequest = HttpRequest()


class BaseTranslatableAdmin(BaseModelAdmin):
    """
    The shared code between the regular model admin and inline classes.
    """
    form = TranslatableModelForm
    query_language_key = 'language'


    @property
    def media(self):
        # Currently, `prepopulated_fields` can't be used because it breaks the admin validation.
        # TODO: as a fix TranslatedFields should become a RelatedField on the shared model (may also support ORM queries)
        # As workaround, declare the fields in get_prepopulated_fields() and we'll provide the admin media automatically.
        has_prepoplated = len(self.get_prepopulated_fields(_fakeRequest))
        base_media = super(BaseTranslatableAdmin, self).media
        if has_prepoplated:
            return base_media + _language_prepopulated_media
        else:
            return base_media + _language_media


    def _has_translatable_model(self):
        # Allow fallback to regular models when needed.
        return issubclass(self.model, TranslatableModel)


    def _language(self, request, obj=None):
        """
        Get the language parameter from the current request.
        """
        return get_language_parameter(request, self.query_language_key, object=obj)


    def get_form_language(self, request, obj=None):
        """
        Return the current language for the currently displayed object fields.
        """
        if obj is not None:
            return obj.get_current_language()
        else:
            return self._language(request)


    def get_queryset_language(self, request):
        """
        Return the language to use in the queryset.
        """
        if not is_multilingual_project():
            # Make sure the current translations remain visible, not the dynamically set get_language() value.
            return appsettings.PARLER_LANGUAGES.get_default_language()
        else:
            # Allow to adjust to current language
            # This is overwritten for the inlines, which follow the primary object.
            return get_language()


    def queryset(self, request):
        """
        Make sure the current language is selected.
        """
        qs = super(BaseTranslatableAdmin, self).queryset(request)

        if self._has_translatable_model():
            if not isinstance(qs, TranslatableQuerySet):
                raise ImproperlyConfigured("{0} class does not inherit from TranslatableQuerySet".format(qs.__class__.__name__))

            # Apply a consistent language to all objects.
            qs_language = self.get_queryset_language(request)
            if qs_language:
                qs = qs.language(qs_language)

        return qs


    def get_language_tabs(self, request, obj, available_languages, css_class=None):
        """
        Determine the language tabs to show.
        """
        current_language = self.get_form_language(request, obj)
        return get_language_tabs(request, current_language, available_languages, css_class=css_class)



class TranslatableAdmin(BaseTranslatableAdmin, admin.ModelAdmin):
    """
    Base class for translated admins.

    This class also works as regular admin for non TranslatableModel objects.
    When using this class with a non-TranslatableModel,
    all operations effectively become a NO-OP.
    """

    deletion_not_allowed_template = 'admin/parler/deletion_not_allowed.html'

    #: Whether translations of inlines should also be deleted when deleting a translation.
    delete_inline_translations = True


    @property
    def change_form_template(self):
        # Dynamic property to support transition to regular models.
        if self._has_translatable_model():
            # While this breaks the admin template name detection,
            # the get_change_form_base_template() makes sure it inherits from your template.
            return 'admin/parler/change_form.html'
        else:
            return None # get default admin selection


    def language_column(self, object):
        """
        The language column which can be included in the ``list_display``.
        """
        languages = self.get_available_languages(object)
        languages = [self.get_language_short_title(code) for code in languages]
        return u'<span class="available-languages">{0}</span>'.format(' '.join(languages))

    language_column.allow_tags = True
    language_column.short_description = _("Languages")


    def get_language_short_title(self, language_code):
        """
        Hook for allowing to change the title in the :func:`language_column` of the list_display.
        """
        return language_code


    def get_available_languages(self, obj):
        """
        Fetching the available languages as queryset.
        """
        if obj:
            return obj.get_available_languages()
        else:
            return self.model._translations_model.objects.none()


    def get_object(self, request, object_id):
        """
        Make sure the object is fetched in the correct language.
        """
        obj = super(TranslatableAdmin, self).get_object(request, object_id)
        if obj is not None and self._has_translatable_model():  # Allow fallback to regular models.
            obj.set_current_language(self._language(request, obj), initialize=True)

        return obj


    def get_form(self, request, obj=None, **kwargs):
        """
        Pass the current language to the form.
        """
        form_class = super(TranslatableAdmin, self).get_form(request, obj, **kwargs)
        if self._has_translatable_model():
            form_class.language_code = self.get_form_language(request, obj)

        return form_class


    def get_urls(self):
        """
        Add a delete-translation view.
        """
        urlpatterns = super(TranslatableAdmin, self).get_urls()
        if not self._has_translatable_model():
            return urlpatterns
        else:
            info = self.model._meta.app_label, self.model._meta.module_name

            return patterns('',
                url(r'^(.+)/delete-translation/(.+)/$',
                    self.admin_site.admin_view(self.delete_translation),
                    name='{0}_{1}_delete_translation'.format(*info)
                ),
            ) + urlpatterns


    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """
        Insert the language tabs.
        """
        if self._has_translatable_model():
            lang_code = self.get_form_language(request, obj)
            lang = get_language_title(lang_code)

            available_languages = self.get_available_languages(obj)
            language_tabs = self.get_language_tabs(request, obj, available_languages)
            context['language_tabs'] = language_tabs
            if language_tabs:
                context['title'] = '%s (%s)' % (context['title'], lang)
            if not language_tabs.current_is_translated:
                add = True  # lets prepopulated_fields_js work.

        # django-fluent-pages uses the same technique
        if 'default_change_form_template' not in context:
            context['default_change_form_template'] = self.get_change_form_base_template()

        # Patch form_url to contain the "language" GET parameter.
        # Otherwise AdminModel.render_change_form will clean the URL
        # and remove the "language" when coming from a filtered object
        # list causing the wrong translation to be changed.
        form_url = add_preserved_filters({'preserved_filters': urlencode({'language': lang_code}), 'opts': self.model._meta}, form_url)

        #context['base_template'] = self.get_change_form_base_template()
        return super(TranslatableAdmin, self).render_change_form(request, context, add, change, form_url, obj)


    def response_add(self, request, obj, post_url_continue=None):
        # Minor behavior difference for Django 1.4
        if post_url_continue is None and django.VERSION < (1,5):
            post_url_continue = '../%s/'

        # Make sure ?language=... is included in the redirects.
        redirect = super(TranslatableAdmin, self).response_add(request, obj, post_url_continue)
        return self._patch_redirect(request, obj, redirect)


    def response_change(self, request, obj):
        # Make sure ?language=... is included in the redirects.
        redirect = super(TranslatableAdmin, self).response_change(request, obj)
        return self._patch_redirect(request, obj, redirect)


    def _patch_redirect(self, request, obj, redirect):
        if redirect.status_code not in (301,302):
            return redirect  # a 200 response likely.

        uri = iri_to_uri(request.path)
        info = (self.model._meta.app_label, self.model._meta.module_name)

        # Pass ?language=.. to next page.
        language = request.GET.get(self.query_language_key)
        if language:
            continue_urls = (uri, "../add/", reverse('admin:{0}_{1}_add'.format(*info)))
            if redirect['Location'] in continue_urls and self.query_language_key in request.GET:
                # "Save and add another" / "Save and continue" URLs
                redirect['Location'] += "?{0}={1}".format(self.query_language_key, language)
        return redirect


    @csrf_protect_m
    @transaction_atomic
    def delete_translation(self, request, object_id, language_code):
        """
        The 'delete translation' admin view for this model.
        """
        opts = self.model._meta
        translations_model = self.model._translations_model

        try:
            translation = translations_model.objects.select_related('master').get(master=unquote(object_id), language_code=language_code)
        except translations_model.DoesNotExist:
            raise Http404

        if not self.has_delete_permission(request, translation):
            raise PermissionDenied

        if self.get_available_languages(translation.master).count() <= 1:
            return self.deletion_not_allowed(request, translation, language_code)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.

        using = router.db_for_write(translations_model)
        lang = get_language_title(language_code)
        (deleted_objects, perms_needed, protected) = get_deleted_objects(
            [translation], translations_model._meta, request.user, self.admin_site, using)

        # Extend deleted objects with the inlines.
        if self.delete_inline_translations:
            shared_obj = translation.master
            for inline, qs in self._get_inline_translations(request, translation.language_code, obj=shared_obj):
                (del2, perms2, protected2) = get_deleted_objects(qs, qs.model._meta, request.user, self.admin_site, using)
                deleted_objects += del2
                perms_needed = perms_needed or perms2
                protected += protected2

        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = _('{0} translation of {1}').format(lang, force_text(translation))  # in hvad: (translation.master)

            self.log_deletion(request, translation, obj_display)
            self.delete_model_translation(request, translation)
            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % dict(
                name=force_text(opts.verbose_name), obj=force_text(obj_display)
            ))

            if self.has_change_permission(request, None):
                return HttpResponseRedirect(reverse('admin:{0}_{1}_changelist'.format(opts.app_label, opts.module_name)))
            else:
                return HttpResponseRedirect(reverse('admin:index'))

        object_name = _('{0} Translation').format(force_text(opts.verbose_name))
        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = {
            "title": title,
            "object_name": object_name,
            "object": translation,
            "deleted_objects": deleted_objects,
            "perms_lacking": perms_needed,
            "protected": protected,
            "opts": opts,
            "app_label": opts.app_label,
        }

        return render(request, self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (opts.app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % opts.app_label,
            "admin/delete_confirmation.html"
        ], context)


    def deletion_not_allowed(self, request, obj, language_code):
        """
        Deletion-not-allowed view.
        """
        opts = self.model._meta
        context = {
            'object': obj.master,
            'language_code': language_code,
            'opts': opts,
            'app_label': opts.app_label,
            'language_name': get_language_title(language_code),
            'object_name': force_text(opts.verbose_name)
        }
        return render(request, self.deletion_not_allowed_template, context)


    def delete_model_translation(self, request, translation):
        """
        Hook for deleting a translation.
        """
        translation.delete()

        # Also delete translations of inlines which the user has access to.
        if self.delete_inline_translations:
            master = translation.master
            for inline, qs in self._get_inline_translations(request, translation.language_code, obj=master):
                qs.delete()


    def _get_inline_translations(self, request, language_code, obj=None):
        """
        Fetch the inline translations
        """
        for inline in self.get_inline_instances(request, obj=obj):
            if issubclass(inline.model, TranslatableModel):
                # leverage inlineformset_factory() to find the ForeignKey.
                # This also resolves the fk_name if it's set.
                fk = inline.get_formset(request, obj).fk

                rel_name = 'master__{0}'.format(fk.name)
                filters = {
                    'language_code': language_code,
                    rel_name: obj
                }

                qs = inline.model._translations_model.objects.filter(**filters)
                if obj is not None:
                    qs = qs.using(obj._state.db)

                yield inline, qs


    def get_change_form_base_template(self):
        """
        Determine what the actual `change_form_template` should be.
        """
        opts = self.model._meta
        app_label = opts.app_label
        return _lazy_select_template_name((
            "admin/{0}/{1}/change_form.html".format(app_label, opts.object_name.lower()),
            "admin/{0}/change_form.html".format(app_label),
            "admin/change_form.html"
        ))


_lazy_select_template_name = lazy(select_template_name, six.text_type)


class TranslatableBaseInlineFormSet(BaseInlineFormSet):
    language_code = None

    def _construct_form(self, i, **kwargs):
        form = super(TranslatableBaseInlineFormSet, self)._construct_form(i, **kwargs)
        form.language_code = self.language_code   # Pass the language code for new objects!
        return form

    def save_new(self, form, commit=True):
        obj = super(TranslatableBaseInlineFormSet, self).save_new(form, commit)
        return obj


class TranslatableInlineModelAdmin(BaseTranslatableAdmin, InlineModelAdmin):
    """
    Base class for inline models.
    """
    form = TranslatableModelForm
    formset = TranslatableBaseInlineFormSet

    @property
    def inline_tabs(self):
        """
        Whether to show inline tabs, can be set as attribute on the inline.
        """
        return not self._has_translatable_parent_model()

    def _has_translatable_parent_model(self):
        # Allow fallback to regular models when needed.
        return issubclass(self.parent_model, TranslatableModel)

    def get_queryset_language(self, request):
        if not is_multilingual_project():
            # Make sure the current translations remain visible, not the dynamically set get_language() value.
            return appsettings.PARLER_LANGUAGES.get_default_language()
        else:
            # Set the initial language for fetched objects.
            # This is needed for the TranslatableInlineModelAdmin
            return self._language(request)

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super(TranslatableInlineModelAdmin, self).get_formset(request, obj, **kwargs)
        # Existing objects already got the language code from the queryset().language() method.
        # For new objects, the language code should be set here.
        FormSet.language_code = self.get_form_language(request, obj)

        if self.inline_tabs:
            # Need to pass information to the template, this can only happen via the FormSet object.
            available_languages = self.get_available_languages(obj, FormSet)
            FormSet.language_tabs = self.get_language_tabs(request, obj, available_languages, css_class='parler-inline-language-tabs')
            FormSet.language_tabs.allow_deletion = self._has_translatable_parent_model()   # Views not available otherwise.

        return FormSet

    def get_form_language(self, request, obj=None):
        if self._has_translatable_parent_model():
            return super(TranslatableInlineModelAdmin, self).get_form_language(request, obj=obj)
        else:
            # Follow the ?language parameter
            return self._language(request)

    def get_available_languages(self, obj, formset):
        """
        Fetching the available inline languages as queryset.
        """
        if obj:
            # Inlines dictate language code, not the parent model.
            # Hence, not looking at obj.get_available_languages(), but see what languages
            # are used by the inline objects that point to it.
            filter = {
                'master__{0}'.format(formset.fk.name): obj
            }
            return self.model._translations_model.objects.using(obj._state.db).filter(**filter) \
                   .values_list('language_code', flat=True).distinct().order_by('language_code')
        else:
            return self.model._translations_model.objects.none()


class TranslatableStackedInline(TranslatableInlineModelAdmin):
    @property
    def template(self):
        if self.inline_tabs:
            return 'admin/parler/edit_inline/stacked_tabs.html'
        else:
            # Admin default
            return 'admin/edit_inline/stacked.html'


class TranslatableTabularInline(TranslatableInlineModelAdmin):
    @property
    def template(self):
        if self.inline_tabs:
            return 'admin/parler/edit_inline/tabular_tabs.html'
        else:
            # Admin default
            return 'admin/edit_inline/tabular.html'

########NEW FILE########
__FILENAME__ = appsettings
"""
Overview of all settings which can be customized.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from parler.utils import normalize_language_code, is_supported_django_language
from parler.utils.conf import LanguagesSetting

PARLER_DEFAULT_LANGUAGE_CODE = getattr(settings, 'PARLER_DEFAULT_LANGUAGE_CODE', settings.LANGUAGE_CODE)

PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = getattr(settings, 'PARLER_SHOW_EXCLUDED_LANGUAGE_TABS', False)

PARLER_LANGUAGES = getattr(settings, 'PARLER_LANGUAGES', {})

PARLER_ENABLE_CACHING = getattr(settings, 'PARLER_ENABLE_CACHING', True)


def add_default_language_settings(languages_list, var_name='PARLER_LANGUAGES', **extra_defaults):
    """
    Apply extra defaults to the language settings.
    This function can also be used by other packages to
    create their own variation of ``PARLER_LANGUAGES`` with extra fields.
    For example::

        from django.conf import settings
        from parler import appsettings as parler_appsettings

        # Create local names, which are based on the global parler settings
        MYAPP_DEFAULT_LANGUAGE_CODE = getattr(settings, 'MYAPP_DEFAULT_LANGUAGE_CODE', parler_appsettings.PARLER_DEFAULT_LANGUAGE_CODE)
        MYAPP_LANGUAGES = getattr(settings, 'MYAPP_LANGUAGES', parler_appsettings.PARLER_LANGUAGES)

        # Apply the defaults to the languages
        MYAPP_LANGUAGES = parler_appsettings.add_default_language_settings(MYAPP_LANGUAGES, 'MYAPP_LANGUAGES',
            code=MYAPP_DEFAULT_LANGUAGE_CODE,
            fallback=MYAPP_DEFAULT_LANGUAGE_CODE,
            hide_untranslated=False
        )

    The returned object will be an :class:`~parler.utils.conf.LanguagesSetting` object,
    which adds additional methods to the :class:`dict` object.
    """
    languages_list = LanguagesSetting(languages_list)

    languages_list.setdefault('default', {})
    defaults = languages_list['default']
    defaults.setdefault('code', PARLER_DEFAULT_LANGUAGE_CODE)
    defaults.setdefault('fallback', PARLER_DEFAULT_LANGUAGE_CODE)
    defaults.setdefault('hide_untranslated', False)   # Whether queries with .active_translations() may or may not return the fallback language.
    defaults.update(extra_defaults)  # Also allow to override code and fallback this way.

    if not is_supported_django_language(defaults['code']):
        raise ImproperlyConfigured("The value for {0}['defaults']['code'] ('{1}') does not exist in LANGUAGES".format(var_name, defaults['code']))

    for site_id, lang_choices in six.iteritems(languages_list):
        if site_id == 'default':
            continue

        if not isinstance(lang_choices, (list, tuple)):
            raise ImproperlyConfigured("{0}[{1}] should be a tuple of language choices!".format(var_name, site_id))
        for i, choice in enumerate(lang_choices):
            if not is_supported_django_language(choice['code']):
                raise ImproperlyConfigured("{0}[{1}][{2}]['code'] does not exist in LANGUAGES".format(var_name, site_id, i))

            # Copy all items from the defaults, so you can provide new fields too.
            for key, value in six.iteritems(defaults):
                choice.setdefault(key, value)

    return languages_list


# Clean settings
PARLER_DEFAULT_LANGUAGE_CODE = normalize_language_code(PARLER_DEFAULT_LANGUAGE_CODE)
PARLER_LANGUAGES = add_default_language_settings(PARLER_LANGUAGES)

########NEW FILE########
__FILENAME__ = cache
from django.core.cache import cache
from django.utils import six
from parler import appsettings
from parler.utils import get_language_settings

if six.PY3:
    long = int


def get_object_cache_keys(instance):
    """
    Return the cache keys associated with an object.
    """
    if not instance.pk or instance._state.adding:
        return []

    keys = []
    # TODO: performs a query to fetch the language codes. Store that in memcached too.
    for language in instance.get_available_languages():
        keys.append(get_translation_cache_key(instance._translations_model, instance.pk, language))

    return keys


def get_translation_cache_key(translated_model, master_id, language_code):
    """
    The low-level function to get the cache key for a translation.
    """
    # Always cache the entire object, as this already produces
    # a lot of queries. Don't go for caching individual fields.
    return 'parler.{0}.{1}.{2}.{3}'.format(translated_model._meta.app_label, translated_model.__name__, long(master_id), language_code)


def get_cached_translation(instance, language_code, use_fallback=False):
    """
    Fetch an cached translation.
    """
    if not appsettings.PARLER_ENABLE_CACHING or not instance.pk or instance._state.adding:
        return None

    key = get_translation_cache_key(instance._translations_model, instance.pk, language_code)
    values = cache.get(key)
    if not values:
        return None

    # Check for a stored fallback marker
    if values.get('__FALLBACK__', False):
        # Allow to return the fallback language instead.
        if use_fallback:
            lang_dict = get_language_settings(language_code)
            if lang_dict['fallback'] != language_code:
                return get_cached_translation(instance, lang_dict['fallback'], use_fallback=False)
        return None

    values['master'] = instance
    values['language_code'] = language_code
    translation = instance._translations_model(**values)
    translation._state.adding = False
    return translation


def get_cached_translated_field(instance, language_code, field_name):
    """
    Fetch an cached field.
    """
    if not appsettings.PARLER_ENABLE_CACHING or not instance.pk or instance._state.adding:
        return None

    key = get_translation_cache_key(instance._translations_model, instance.pk, language_code)
    values = cache.get(key)
    if not values:
        return None

    # Allow older cached versions where the field didn't exist yet.
    return values.get(field_name, None)


def _cache_translation(translation, timeout=0):
    """
    Store a new translation in the cache.
    """
    if not appsettings.PARLER_ENABLE_CACHING:
        return

    # Cache a translation object.
    # For internal usage, object parameters are not suited for outside usage.
    fields = translation.get_translated_fields()
    values = {'id': translation.id}
    for name in fields:
        values[name] = getattr(translation, name)

    key = get_translation_cache_key(translation.__class__, translation.master_id, translation.language_code)
    cache.set(key, values, timeout=timeout)


def _cache_translation_needs_fallback(instance, language_code, timeout=0):
    """
    Store the fact that a translation doesn't exist, and the fallback should be used.
    """
    if not instance.pk or instance._state.adding:
        return

    key = get_translation_cache_key(instance._translations_model, instance.pk, language_code)
    cache.set(key, {'__FALLBACK__': True}, timeout=timeout)


def _delete_cached_translations(shared_model):
    for key in get_object_cache_keys(shared_model):
        cache.delete(key)


def _delete_cached_translation(translation):
    if not appsettings.PARLER_ENABLE_CACHING:
        return

    # Delete a cached translation
    # For internal usage, object parameters are not suited for outside usage.
    key = get_translation_cache_key(translation.__class__, translation.master_id, translation.language_code)
    cache.delete(key)

########NEW FILE########
__FILENAME__ = fields
"""
Model fields
"""
from __future__ import unicode_literals
from django.db.models.fields import Field


# TODO: inherit RelatedField?
class TranslatedField(object):
    """
    Proxy field attached to a model.

    The field is automatically added to the shared model.
    However, this can be assigned manually to be more explicit, or to pass the ``any_language`` value.
    The ``any_language=True`` option causes the attribute to always return a translated value,
    even when the current language and fallback are missing.
    This can be useful for "title" attributes for example.

    Example::
        from django.db import models
        from parler.models import TranslatableModel, TranslatedFieldsModel

        class MyModel(TranslatableModel):
            title = TranslatedField(any_language=True)
            slug = TranslatedField()   # Optional, but explicitly mentioned

        # Manual model class
        class MyModelTranslation(TranslatedFieldsModel):
            master = models.ForeignKey(MyModel, related_name='translations', null=True)
            title = models.CharField("Title", max_length=200)
            slug = models.SlugField("Slug")
    """
    def __init__(self, any_language=False):
        self.model = None
        self.name = None
        self.any_language = any_language

    def contribute_to_class(self, cls, name):
        #super(TranslatedField, self).contribute_to_class(cls, name)
        self.model = cls
        self.name = name

        # Add the proxy attribute
        setattr(cls, self.name, TranslatedFieldDescriptor(self))


class TranslatedFieldDescriptor(object):
    """
    Descriptor for translated attributes.

    This attribute proxies all get/set calls to the translated model.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if not instance:
            # Return the class attribute when asked for by the admin.
            return self

        # Auto create is useless for __get__, will return empty titles everywhere.
        # Better use a fallback instead, just like gettext does.
        translation = None
        try:
            translation = instance._get_translated_model(use_fallback=True)
        except instance._translations_model.DoesNotExist as e:
            if self.field.any_language:
                translation = instance._get_any_translated_model()  # returns None on error.

            if translation is None:
                # Improve error message
                e.args = ("{1}\nAttempted to read attribute {0}.".format(self.field.name, e.args[0]),)
                raise

        return getattr(translation, self.field.name)

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("{0} must be accessed via instance".format(self.field.opts.object_name))

        # When assigning the property, assign to the current language.
        # No fallback is used in this case.
        translation = instance._get_translated_model(use_fallback=False, auto_create=True)
        setattr(translation, self.field.name, value)

    def __delete__(self, instance):
        # No autocreate or fallback, as this is delete.
        # Rather blow it all up when the attribute doesn't exist.
        # Similar to getting a KeyError on `del dict['UNKNOWN_KEY']`
        translation = instance._get_translated_model()
        delattr(translation, self.field.name)

    def __repr__(self):
        return "<{0} for {1}.{2}>".format(self.__class__.__name__, self.field.model.__name__, self.field.name)


class LanguageCodeDescriptor(object):
    """
    This is the property to access the ``language_code`` in the ``TranslatableModel``.
    """
    def __get__(self, instance, instance_type=None):
        if not instance:
            raise AttributeError("language_code must be accessed via instance")

        return instance._current_language

    def __set__(self, instance, value):
        raise AttributeError("The 'language_code' attribute cannot be changed directly! Use the set_current_language() method instead.")

    def __delete__(self, instance):
        raise AttributeError("The 'language_code' attribute cannot be deleted!")


try:
    from south.modelsinspector import add_ignored_fields
except ImportError:
    pass
else:
    _name_re = "^" + __name__.replace(".", "\.")
    add_ignored_fields((
        _name_re + "\.TranslatedField",
    ))

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.forms.models import ModelFormMetaclass
from django.utils.translation import get_language
from django.utils import six
from parler.models import TranslatableModel, TranslationDoesNotExist


def get_model_form_field(model, name, formfield_callback=None, **kwargs):
    """
    Utility to create the formfield from a model field.
    When a field is not editable, a ``None`` will be returned.
    """
    field = model._meta.get_field_by_name(name)[0]
    if not field.editable:  # see fields_for_model() logic in Django.
        return None

    # Apply admin formfield_overrides
    if formfield_callback is None:
        formfield = field.formfield(**kwargs)
    elif not callable(formfield_callback):
        raise TypeError('formfield_callback must be a function or callable')
    else:
        formfield = formfield_callback(field, **kwargs)

    return formfield


class TranslatedField(object):
    """
    A wrapper for a translated form field.

    This wrapper can be used to declare translated fields on the form, e.g.

    .. code-block:: python

        class MyForm(TranslatableModelForm):
            title = TranslatedField()
            slug = TranslatedField()

            description = TranslatedField(form_class=forms.CharField, widget=TinyMCE)
    """
    def __init__(self, **kwargs):
        # The metaclass performs the magic replacement with the actual formfield.
        self.kwargs = kwargs



class TranslatableModelFormMixin(object):
    """
    Form mixin, to fetch+store translated fields.
    """
    language_code = None    # Set by TranslatableAdmin.get_form() on the constructed subclass.


    def __init__(self, *args, **kwargs):
        current_language = kwargs.pop('_current_language', None)   # Used for TranslatableViewMixin
        super(TranslatableModelFormMixin, self).__init__(*args, **kwargs)

        # Load the initial values for the translated fields
        instance = kwargs.get('instance', None)
        if instance:
            try:
                # By not auto creating a model, any template code that reads the fields
                # will continue to see one of the other translations.
                # This also causes admin inlines to show the fallback title in __unicode__.
                translation = instance._get_translated_model()
            except TranslationDoesNotExist:
                pass
            else:
                for field in self._get_translated_fields():
                    self.initial.setdefault(field, getattr(translation, field))

        # Typically already set by admin
        if self.language_code is None:
            if instance:
                self.language_code = instance.get_current_language()
                return
            else:
                self.language_code = current_language or get_language()

    def save(self, *args, **kwargs):
        # Using args, kwargs to support custom parent arguments too.
        self.instance.set_current_language(self.language_code)
        self.save_translated_fields(*args, **kwargs)
        return super(TranslatableModelFormMixin, self).save(*args, **kwargs)

    def save_translated_fields(self, *args, **kwargs):
        # Assign translated fields to the model (using the TranslatedAttribute descriptor)
        for field in self._get_translated_fields():
            setattr(self.instance, field, self.cleaned_data[field])

    def _get_translated_fields(self):
        return [f_name for f_name in self._meta.model._translations_model.get_translated_fields() if f_name in self.fields]



class TranslatableModelFormMetaclass(ModelFormMetaclass):
    """
    Meta class to add translated form fields to the form.
    """
    def __new__(mcs, name, bases, attrs):
        # Before constructing class, fetch attributes from bases list.
        form_meta = _get_mro_attribute(bases, '_meta')
        form_base_fields = _get_mro_attribute(bases, 'base_fields', {})  # set by previous class level.

        if form_meta:
            # Not declaring the base class itself, this is a subclass.

            # Read the model from the 'Meta' attribute. This even works in the admin,
            # as `modelform_factory()` includes a 'Meta' attribute.
            # The other options can be read from the base classes.
            form_new_meta = attrs.get('Meta', form_meta)
            form_model = form_new_meta.model if form_new_meta else form_meta.model

            # Detect all placeholders at this class level.
            translated_fields = [
                f_name for f_name, attr_value in six.iteritems(attrs) if isinstance(attr_value, TranslatedField)
            ]

            # Include the translated fields as attributes, pretend that these exist on the form.
            # This also works when assigning `form = TranslatableModelForm` in the admin,
            # since the admin always uses modelform_factory() on the form class, and therefore triggering this metaclass.
            if form_model:
                translations_model = form_model._translations_model
                fields = getattr(form_new_meta, 'fields', form_meta.fields)
                exclude = getattr(form_new_meta, 'exclude', form_meta.exclude) or ()
                widgets = getattr(form_new_meta, 'widgets', form_meta.widgets) or ()
                formfield_callback = attrs.get('formfield_callback', None)

                if fields == '__all__':
                    fields = None

                for f_name in translations_model.get_translated_fields():
                    # Add translated field if not already added, and respect exclude options.
                    if f_name in translated_fields:
                        # The TranslatedField placeholder can be replaced directly with actual field, so do that.
                        attrs[f_name] = get_model_form_field(translations_model, f_name, formfield_callback=formfield_callback, **translated_fields[f_name].kwargs)
                    # The next code holds the same logic as fields_for_model()
                    # The f.editable check happens in get_model_form_field()
                    elif f_name not in form_base_fields \
                     and (fields is None or f_name in fields) \
                     and f_name not in exclude \
                     and not f_name in attrs:
                        # Get declared widget kwargs
                        if f_name in widgets:
                            # Not combined with declared fields (e.g. the TranslatedField placeholder)
                            kwargs = {'widget': widgets[f_name]}
                        else:
                            kwargs = {}

                        # See if this formfield was previously defined using a TranslatedField placeholder.
                        placeholder = _get_mro_attribute(bases, f_name)
                        if placeholder and isinstance(placeholder, TranslatedField):
                            kwargs.update(placeholder.kwargs)

                        # Add the form field as attribute to the class.
                        formfield = get_model_form_field(translations_model, f_name, formfield_callback=formfield_callback, **kwargs)
                        if formfield is not None:
                            attrs[f_name] = formfield

        # Call the super class with updated `attrs` dict.
        return super(TranslatableModelFormMetaclass, mcs).__new__(mcs, name, bases, attrs)



def _get_mro_attribute(bases, name, default=None):
    for base in bases:
        try:
            return getattr(base, name)
        except AttributeError:
            continue
    return default


class TranslatableModelForm(six.with_metaclass(TranslatableModelFormMetaclass, TranslatableModelFormMixin), forms.ModelForm):
    """
    A model form for translated models.
    """
    # six.with_metaclass does not handle more than 2 parent classes for django < 1.6
    # so only one is wrapped within with_metaclass

########NEW FILE########
__FILENAME__ = managers
"""
Custom generic managers
"""
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import get_language
from django.utils import six
from parler import appsettings
from parler.utils import get_active_language_choices


class TranslatableQuerySet(QuerySet):
    """
    An enhancement of the QuerySet which sets the objects language before they are returned.

    When using this method with *django-polymorphic*, make sure this
    class is first in the chain of inherited classes.
    """

    def __init__(self, *args, **kwargs):
        super(TranslatableQuerySet, self).__init__(*args, **kwargs)
        self._language = []


    def _clone(self, klass=None, setup=False, **kw):
        c = super(TranslatableQuerySet, self)._clone(klass, setup, **kw)
        c._language = self._language
        return c


    def language(self, language_code=None):
        """
        Set the language code to assign to objects retrieved using this QuerySet.
        """
        if language_code is None:
            language_code = appsettings.PARLER_LANGUAGES.get_default_language()

        self._language = language_code
        return self


    def translated(self, *language_codes, **translated_fields):
        """
        Only return translated objects which of the given languages.

        When no language codes are given, only the currently active language is returned.

        NOTE: due to Django `ORM limitations <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_,
        this method can't be combined with other filters that access the translated fields. As such, query the fields in one filter:

        .. code-block:: python

            qs.translated('en', name="Cheese Omelette")

        This will query the translated model for the ``name`` field.
        """
        relname = self.model._translations_field

        if not language_codes:
            language_codes = (get_language(),)

        filters = {}
        for field_name, val in six.iteritems(translated_fields):
            if field_name.startswith('master__'):
                filters[field_name[8:]] = val  # avoid translations__master__ back and forth
            else:
                filters["{0}__{1}".format(relname, field_name)] = val

        if len(language_codes) == 1:
            filters[relname + '__language_code'] = language_codes[0]
            return self.filter(**filters)
        else:
            filters[relname + '__language_code__in'] = language_codes
            return self.filter(**filters).distinct()


    def active_translations(self, language_code=None, **translated_fields):
        """
        Only return objects which are translated, or have a fallback that should be displayed.

        Typically that's the currently active language and fallback language.
        When ``hide_untranslated = True``, only the currently active language will be returned.
        """
        # Default:     (language, fallback) when hide_translated == False
        # Alternative: (language,)          when hide_untranslated == True
        language_codes = get_active_language_choices(language_code)
        return self.translated(*language_codes, **translated_fields)


    def iterator(self):
        """
        Overwritten iterator which will apply the decorate functions before returning it.
        """
        # Based on django-queryset-transform.
        # This object however, operates on a per-object instance
        # without breaking the result generators
        base_iterator = super(TranslatableQuerySet, self).iterator()
        for obj in base_iterator:
            # Apply the language setting.
            if self._language:
                obj.set_current_language(self._language)

            yield obj


class TranslatableManager(models.Manager):
    """
    The manager class which ensures the enhanced TranslatableQuerySet object is used.
    """
    queryset_class = TranslatableQuerySet

    def get_query_set(self):
        return self.queryset_class(self.model, using=self._db)

    def language(self, language_code=None):
        """
        Set the language code to assign to objects retrieved using this Manager.
        """
        return self.get_query_set().language(language_code)

    def translated(self, *language_codes, **translated_fields):
        """
        Only return objects which are translated in the given languages.

        NOTE: due to Django `ORM limitations <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_,
        this method can't be combined with other filters that access the translated fields. As such, query the fields in one filter:

        .. code-block:: python

            qs.translated('en', name="Cheese Omelette")

        This will query the translated model for the ``name`` field.
        """
        return self.get_query_set().translated(*language_codes, **translated_fields)

    def active_translations(self, language_code=None, **translated_fields):
        """
        Only return objects which are translated, or have a fallback that should be displayed.

        Typically that's the currently active language and fallback language.
        When ``hide_untranslated = True``, only the currently active language will be returned.
        """
        return self.get_query_set().active_translations(language_code, **translated_fields)


# Export the names in django-hvad style too:
TranslationQueryset = TranslatableQuerySet
TranslationManager = TranslatableManager

########NEW FILE########
__FILENAME__ = models
"""
Simple but effective translation support.

Integrating *django-hvad* (v0.3) in advanced projects turned out to be really hard,
as it changes the behavior of the QuerySet iterator, manager methods
and model metaclass which *django-polymorphic* and friends also rely on.
The following is a "crude, but effective" way to introduce multilingual support.

Added on top of that, the API-suger is provided, similar to what django-hvad has.
It's possible to create the translations model manually,
or let it be created dynamically when using the :class:`TranslatedFields` field.
"""
from __future__ import unicode_literals
import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models, router
from django.db.models.base import ModelBase
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
from django.utils.functional import lazy
from django.utils.translation import get_language, ugettext, ugettext_lazy as _
from django.utils import six
from parler import signals
from parler.cache import _cache_translation, _cache_translation_needs_fallback, _delete_cached_translation, get_cached_translation, _delete_cached_translations, get_cached_translated_field
from parler.fields import TranslatedField, LanguageCodeDescriptor, TranslatedFieldDescriptor
from parler.managers import TranslatableManager
from parler.utils.i18n import normalize_language_code, get_language_settings, get_language_title
import sys
import logging

logger = logging.getLogger(__name__)



class TranslationDoesNotExist(AttributeError):
    """
    A tagging interface to detect missing translations.
    The exception inherits from :class:`AttributeError` to reflect what is actually happening.
    It also causes the templates to handle the missing attributes silently, which is very useful in the admin for example.
    """
    pass


_lazy_verbose_name = lazy(lambda x: ugettext("{0} Translation").format(x._meta.verbose_name), six.text_type)


def create_translations_model(shared_model, related_name, meta, **fields):
    """
    Dynamically create the translations model.
    Create the translations model for the shared model 'model'.

    :param related_name: The related name for the reverse FK from the translations model.
    :param meta: A (optional) dictionary of attributes for the translations model's inner Meta class.
    :param fields: A dictionary of fields to put on the translations model.

    Two fields are enforced on the translations model:

        language_code: A 15 char, db indexed field.
        master: A ForeignKey back to the shared model.

    Those two fields are unique together.
    """
    if not meta:
        meta = {}

    # Define inner Meta class
    meta['unique_together'] = list(meta.get('unique_together', [])) + [('language_code', 'master')]
    meta['app_label'] = shared_model._meta.app_label
    meta.setdefault('db_table', shared_model._meta.db_table + '_translation')
    meta.setdefault('verbose_name', _lazy_verbose_name(shared_model))

    # Define attributes for translation table
    name = str('{0}Translation'.format(shared_model.__name__))  # makes it bytes, for type()

    attrs = {}
    attrs.update(fields)
    attrs['Meta'] = type(str('Meta'), (object,), meta)
    attrs['__module__'] = shared_model.__module__
    attrs['objects'] = models.Manager()
    attrs['master'] = models.ForeignKey(shared_model, related_name=related_name, editable=False, null=True)

    # Create and return the new model
    translations_model = TranslatedFieldsModelBase(name, (TranslatedFieldsModel,), attrs)

    # Register it as a global in the shared model's module.
    # This is needed so that Translation model instances, and objects which refer to them, can be properly pickled and unpickled.
    # The Django session and caching frameworks, in particular, depend on this behaviour.
    mod = sys.modules[shared_model.__module__]
    setattr(mod, name, translations_model)

    return translations_model


class TranslatedFields(object):
    """
    Wrapper class to define translated fields on a model.

    The field name becomes the related name of the :class:`TranslatedFieldsModel` subclass.

    Example::
        from django.db import models
        from parler.models import TranslatableModel, TranslatedFields

        class MyModel(TranslatableModel):
            translations = TranslatedFields(
                title = models.CharField("Title", max_length=200)
            )
    """
    def __init__(self, meta=None, **fields):
        self.fields = fields
        self.meta = meta
        self.name = None

    def contribute_to_class(self, cls, name):
        self.name = name

        # Called from django.db.models.base.ModelBase.__new__
        translations_model = create_translations_model(cls, name, self.meta, **self.fields)

        # The metaclass (TranslatedFieldsModelBase) should configure this already:
        assert cls._translations_model == translations_model
        assert cls._translations_field == name



class TranslatableModel(models.Model):
    """
    Base model class to handle translations.
    """

    # Consider these fields "protected" or "internal" attributes.
    # Not part of the public API, but used internally in the class hierarchy.
    _translations_field = None
    _translations_model = None

    language_code = LanguageCodeDescriptor()

    # change the default manager to the translation manager
    objects = TranslatableManager()

    class Meta:
        abstract = True


    def __init__(self, *args, **kwargs):
        # Still allow to pass the translated fields (e.g. title=...) to this function.
        translated_kwargs = {}
        current_language = None
        if kwargs:
            current_language = kwargs.pop('_current_language', None)
            for field in self._translations_model.get_translated_fields():
                try:
                    translated_kwargs[field] = kwargs.pop(field)
                except KeyError:
                    pass

        # Run original Django model __init__
        super(TranslatableModel, self).__init__(*args, **kwargs)

        self._translations_cache = {}
        self._current_language = normalize_language_code(current_language or get_language())  # What you used to fetch the object is what you get.

        # Assign translated args manually.
        if translated_kwargs:
            translation = self._get_translated_model(auto_create=True)
            for field, value in six.iteritems(translated_kwargs):
                setattr(translation, field, value)


    def get_current_language(self):
        """
        Get the current language.
        """
        # not a property, so won't conflict with model fields.
        return self._current_language


    def set_current_language(self, language_code, initialize=False):
        """
        Switch the currently activate language of the object.
        """
        self._current_language = normalize_language_code(language_code or get_language())

        # Ensure the translation is present for __get__ queries.
        if initialize:
            self._get_translated_model(use_fallback=False, auto_create=True)


    def get_fallback_language(self):
        """
        Return the fallback language code,
        which is used in case there is no translation for the currently active language.
        """
        lang_dict = get_language_settings(self._current_language)
        return lang_dict['fallback'] if lang_dict['fallback'] != self._current_language else None


    def has_translation(self, language_code=None):
        """
        Return whether a translation for the given language exists.
        Defaults to the current language code.
        """
        if language_code is None:
            language_code = self._current_language

        try:
            # Check the local cache directly, and the answer is known.
            # NOTE this may also return newly auto created translations which are not saved yet.
            return self._translations_cache[language_code] is not None
        except KeyError:
            try:
                # Fetch from DB, fill the cache.
                self._get_translated_model(language_code, use_fallback=False, auto_create=False)
            except self._translations_model.DoesNotExist:
                return False
            else:
                return True


    def get_available_languages(self):
        """
        Return the language codes of all translated variations.
        """
        qs = self._get_translated_queryset()
        if qs._prefetch_done:
            return sorted(obj.language_code for obj in qs)
        else:
            return qs.values_list('language_code', flat=True).order_by('language_code')


    def _get_translated_model(self, language_code=None, use_fallback=False, auto_create=False):
        """
        Fetch the translated fields model.
        """
        if not self._translations_model or not self._translations_field:
            raise ImproperlyConfigured("No translation is assigned to the current model!")

        if not language_code:
            language_code = self._current_language

        # 1. fetch the object from the local cache
        try:
            object = self._translations_cache[language_code]

            # If cached object indicates the language doesn't exist, need to query the fallback.
            if object is not None:
                return object
        except KeyError:
            # 2. No cache, need to query
            # Check that this object already exists, would be pointless otherwise to check for a translation.
            if not self._state.adding and self.pk:
                qs = self._get_translated_queryset()
                if qs._prefetch_done:
                    # 2.1, use prefetched data
                    # If the object is not found in the prefetched data (which contains all translations),
                    # it's pointless to check for memcached (2.2) or perform a single query (2.3)
                    for object in qs:
                        if object.language_code == language_code:
                            self._translations_cache[language_code] = object
                            _cache_translation(object)  # Store in memcached
                            return object
                else:
                    # 2.2, fetch from memcached
                    object = get_cached_translation(self, language_code, use_fallback=use_fallback)
                    if object is not None:
                        # Track in local cache
                        if object.language_code != language_code:
                            self._translations_cache[language_code] = None  # Set fallback marker
                        self._translations_cache[object.language_code] = object
                        return object
                    else:
                        # 2.3, fetch from database
                        try:
                            object = qs.get(language_code=language_code)
                        except self._translations_model.DoesNotExist:
                            pass
                        else:
                            self._translations_cache[language_code] = object
                            _cache_translation(object)  # Store in memcached
                            return object

        # Not in cache, or default.
        # Not fetched from DB

        # 3. Auto create?
        if auto_create:
            # Auto create policy first (e.g. a __set__ call)
            object = self._translations_model(
                language_code=language_code,
                master=self  # ID might be None at this point
            )
            self._translations_cache[language_code] = object
            # Not stored in memcached here yet, first fill + save it.
            return object

        # 4. Fallback?
        fallback_msg = None
        lang_dict = get_language_settings(language_code)

        if use_fallback and (lang_dict['fallback'] != language_code):
            # Explicitly set a marker for the fact that this translation uses the fallback instead.
            # Avoid making that query again.
            self._translations_cache[language_code] = None  # None value is the marker.
            if not self._state.adding or self.pk:
                _cache_translation_needs_fallback(self, language_code)

            # Jump to fallback language, return directly.
            # Don't cache under this language_code
            try:
                return self._get_translated_model(lang_dict['fallback'], use_fallback=False, auto_create=auto_create)
            except self._translations_model.DoesNotExist:
                fallback_msg = " (tried fallback {0})".format(lang_dict['fallback'])

        # None of the above, bail out!
        raise self._translations_model.DoesNotExist(
            "{0} does not have a translation for the current language!\n"
            "{0} ID #{1}, language={2}{3}".format(self._meta.verbose_name, self.pk, language_code, fallback_msg or ''
        ))


    def _get_any_translated_model(self):
        """
        Return any available translation.
        Returns None if there are no translations at all.
        """
        if self._translations_cache:
            # There is already a language available in the case. No need for queries.
            # Give consistent answers if they exist.
            try:
                return self._translations_cache.get(self._current_language, None) \
                    or self._translations_cache.get(self.get_fallback_language(), None) \
                    or next(t for t in six.itervalues(self._translations_cache) if t if not None)  # Skip fallback markers.
            except StopIteration:
                pass

        try:
            # Use prefetch if available, otherwise perform separate query.
            qs = self._get_translated_queryset()
            if qs._prefetch_done:
                translation = list(qs)[0]
            else:
                translation = qs[0]
        except IndexError:
            return None
        else:
            self._translations_cache[translation.language_code] = translation
            _cache_translation(translation)
            return translation


    def _get_translated_queryset(self):
        """
        Return the queryset that points to the translated model.
        If there is a prefetch, it can be read from this queryset.
        """
        # Get via self.TRANSLATIONS_FIELD.get(..) so it also uses the prefetch/select_related cache.
        accessor = getattr(self, self._translations_field)
        try:
            return accessor.get_queryset()
        except AttributeError:
            # Fallback for Django 1.4 and Django 1.5
            return accessor.get_query_set()


    def save(self, *args, **kwargs):
        super(TranslatableModel, self).save(*args, **kwargs)
        self.save_translations(*args, **kwargs)


    def delete(self, using=None):
        _delete_cached_translations(self)
        super(TranslatableModel, self).delete(using)


    def save_translations(self, *args, **kwargs):
        # Copy cache, new objects (e.g. fallbacks) might be fetched if users override save_translation()
        translations = self._translations_cache.values()

        # Save all translated objects which were fetched.
        # This also supports switching languages several times, and save everything in the end.
        for translation in translations:
            if translation is None:  # Skip fallback markers
                continue

            self.save_translation(translation, *args, **kwargs)


    def save_translation(self, translation, *args, **kwargs):
        # Translation models without any fields are also supported.
        # This is useful for parent objects that have inlines;
        # the parent object defines how many translations there are.
        if translation.is_modified or (translation.is_empty and not translation.pk):
            if not translation.master_id:  # Might not exist during first construction
                translation._state.db = self._state.db
                translation.master = self
            translation.save(*args, **kwargs)


    def safe_translation_getter(self, field, default=None, language_code=None, any_language=False):
        """
        Fetch a translated property, and return a default value
        when both the translation and fallback language are missing.

        When ``any_language=True`` is used, the function also looks
        into other languages to find a suitable value. This feature can be useful
        for "title" attributes for example, to make sure there is at least something being displayed.
        Also consider using ``field = TranslatedField(any_language=True)`` in the model itself,
        to make this behavior the default for the given field.
        """
        # By default, query via descriptor (TranslatedFieldDescriptor)
        # which also attempts the fallback language if configured to do so.
        tr_model = self

        # Extra feature: query a single field from a other translation.
        if language_code and language_code != self._current_language:
            # Try to fetch a cached value first.
            value = get_cached_translated_field(self, language_code, field)
            if value is not None:
                return value

            try:
                tr_model = self._get_translated_model(language_code)
            except TranslationDoesNotExist:
                pass  # Use 'self'

        try:
            return getattr(tr_model, field)
        except TranslationDoesNotExist:
            pass

        if any_language:
            translation = self._get_any_translated_model()
            if translation is not None:
                return getattr(translation, field, default)

        return default


class TranslatedFieldsModelBase(ModelBase):
    """
    Meta-class for the translated fields model.

    It performs the following steps:
    - It validates the 'master' field, in case it's added manually.
    - It tells the original model to use this model for translations.
    - It adds the proxy attributes to the shared model.
    """
    def __new__(mcs, name, bases, attrs):

        # Workaround compatibility issue with six.with_metaclass() and custom Django model metaclasses:
        if not attrs and name == 'NewBase':
            if django.VERSION < (1,5):
                # Let Django fully ignore the class which is inserted in between.
                # Django 1.5 fixed this, see https://code.djangoproject.com/ticket/19688
                attrs['__module__'] = 'django.utils.six'
                attrs['Meta'] = type(str('Meta'), (), {'abstract': True})
            return super(TranslatedFieldsModelBase, mcs).__new__(mcs, name, bases, attrs)

        new_class = super(TranslatedFieldsModelBase, mcs).__new__(mcs, name, bases, attrs)
        if bases[0] == models.Model:
            return new_class

        # No action in abstract models.
        if new_class._meta.abstract or new_class._meta.proxy:
            return new_class

        # Validate a manually configured class.
        shared_model = _validate_master(new_class)

        # Add wrappers for all translated fields to the shared models.
        new_class.contribute_translations(shared_model)

        return new_class


def _validate_master(new_class):
    """
    Check whether the 'master' field on a TranslatedFieldsModel is correctly configured.
    """
    if not new_class.master or not isinstance(new_class.master, ReverseSingleRelatedObjectDescriptor):
        msg = "{0}.master should be a ForeignKey to the shared table.".format(new_class.__name__)
        logger.error(msg)
        raise TypeError(msg)

    shared_model = new_class.master.field.rel.to
    if not issubclass(shared_model, models.Model):
        # Not supporting models.ForeignKey("tablename") yet. Can't use get_model() as the models are still being constructed.
        msg = "{0}.master should point to a model class, can't use named field here.".format(new_class.__name__)
        logger.error(msg)
        raise TypeError(msg)

    if shared_model._translations_model:
        msg = "The model '{0}' already has an associated translation table!".format(shared_model.__name__)
        logger.error(msg)
        raise TypeError(msg)

    return shared_model


class TranslatedFieldsModel(six.with_metaclass(TranslatedFieldsModelBase, models.Model)):
    """
    Base class for the model that holds the translated fields.
    """

    language_code = models.CharField(_("Language"), choices=settings.LANGUAGES, max_length=15, db_index=True)
    master = None   # FK to shared model.

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        signals.pre_translation_init.send(sender=self.__class__, args=args, kwargs=kwargs)
        super(TranslatedFieldsModel, self).__init__(*args, **kwargs)
        self._original_values = self._get_field_values()

        signals.post_translation_init.send(sender=self.__class__, args=args, kwargs=kwargs)

    @property
    def is_modified(self):
        return self._original_values != self._get_field_values()

    @property
    def is_empty(self):
        return len(self.get_translated_fields()) == 0

    @property
    def shared_model(self):
        return self.__class__.master.field.rel.to

    def save_base(self, raw=False, using=None, **kwargs):
        # Send the pre_save signal
        using = using or router.db_for_write(self.__class__, instance=self)
        record_exists = self.pk is not None  # Ignoring force_insert/force_update for now.
        if not self._meta.auto_created:
            signals.pre_translation_save.send(
                sender=self.shared_model, instance=self,
                raw=raw, using=using
            )

        # Perform save
        super(TranslatedFieldsModel, self).save_base(raw=raw, using=using, **kwargs)
        self._original_values = self._get_field_values()
        _cache_translation(self)

        # Send the post_save signal
        if not self._meta.auto_created:
            signals.post_translation_save.send(
                sender=self.shared_model, instance=self, created=(not record_exists),
                raw=raw, using=using
            )

    def delete(self, using=None):
        # Send pre-delete signal
        using = using or router.db_for_write(self.__class__, instance=self)
        if not self._meta.auto_created:
            signals.pre_translation_delete.send(sender=self.shared_model, instance=self, using=using)

        super(TranslatedFieldsModel, self).delete(using=using)
        _delete_cached_translation(self)

        # Send post-delete signal
        if not self._meta.auto_created:
            signals.post_translation_delete.send(sender=self.shared_model, instance=self, using=using)

    def _get_field_values(self):
        # Return all field values in a consistent (sorted) manner.
        return [getattr(self, field.get_attname()) for field, _ in self._meta.get_fields_with_model()]

    @classmethod
    def get_translated_fields(cls):
        # Not using get `get_all_field_names()` because that also invokes a model scan.
        return [f.name for f, _ in cls._meta.get_fields_with_model() if f.name not in ('language_code', 'master', 'id')]

    @classmethod
    def contribute_translations(cls, shared_model):
        """
        Add the proxy attributes to the shared model.
        """
        # Link the translated fields model to the shared model.
        shared_model._translations_model = cls
        shared_model._translations_field = cls.master.field.rel.related_name

        # Assign the proxy fields
        for name in cls.get_translated_fields():
            try:
                # Check if the field already exists.
                # Note that the descriptor even proxies this request, so it should return our field.
                field = getattr(shared_model, name)
            except AttributeError:
                # Add the proxy field for the shared field.
                TranslatedField().contribute_to_class(shared_model, name)
            else:
                if not isinstance(field, (models.Field, TranslatedFieldDescriptor)):
                    raise TypeError("The model '{0}' already has a field named '{1}'".format(shared_model.__name__, name))

        # Make sure the DoesNotExist error can be detected als shared_model.DoesNotExist too,
        # and by inheriting from AttributeError it makes sure (admin) templates can handle the missing attribute.
        cls.DoesNotExist = type(str('DoesNotExist'), (TranslationDoesNotExist, shared_model.DoesNotExist, cls.DoesNotExist,), {})


    def __unicode__(self):
        return get_language_title(self.language_code)

    def __repr__(self):
        return "<{0}: #{1}, {2}, master: #{3}>".format(
            self.__class__.__name__, self.pk, self.language_code, self.master_id
        )

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

pre_translation_init = Signal(providing_args=["instance", "args", "kwargs"])
post_translation_init = Signal(providing_args=["instance"])

pre_translation_save = Signal(providing_args=["instance", "raw", "using"])
post_translation_save = Signal(providing_args=["instance", "raw", "created", "using"])

pre_translation_delete = Signal(providing_args=["instance", "using"])
post_translation_delete = Signal(providing_args=["instance", "using"])

########NEW FILE########
__FILENAME__ = parler_tags
from django.core.urlresolvers import resolve, reverse, Resolver404
from django.template import Node, Library, TemplateSyntaxError
from django.utils.translation import get_language
from parler.models import TranslatableModel, TranslationDoesNotExist
from parler.utils.context import switch_language, smart_override

register = Library()


class ObjectLanguageNode(Node):
    def __init__(self, nodelist, object_var, language_var=None):
        self.nodelist = nodelist  # This name is special in the Node baseclass
        self.object_var = object_var
        self.language_var = language_var

    def render(self, context):
        # Read context data
        object = self.object_var.resolve(context)
        new_language = self.language_var.resolve(context) if self.language_var else get_language()
        if not isinstance(object, TranslatableModel):
            raise TemplateSyntaxError("Object '{0}' is not an instance of TranslableModel".format(object))

        with switch_language(object, new_language):
            # Render contents inside
            output = self.nodelist.render(context)

        return output


@register.tag
def objectlanguage(parser, token):
    """
    Template tag to switch an object language
    Example::

        {% objectlanguage object "en" %}
          {{ object.title }}
        {% endobjectlanguage %}

    A TranslatedObject is not affected by the ``{% language .. %}`` tag
    as it maintains it's own state. This tag temporary switches the object state.

    Note that using this tag is not thread-safe if the object is shared between threads.
    It temporary changes the current language of the object.
    """
    bits = token.split_contents()
    if len(bits) == 2:
        object_var = parser.compile_filter(bits[1])
        language_var = None
    elif len(bits) == 3:
        object_var = parser.compile_filter(bits[1])
        language_var = parser.compile_filter(bits[2])
    else:
        raise TemplateSyntaxError("'%s' takes one argument (object) and has one optional argument (language)" % bits[0])

    nodelist = parser.parse(('endobjectlanguage',))
    parser.delete_first_token()
    return ObjectLanguageNode(nodelist, object_var, language_var)


@register.assignment_tag(takes_context=True)
def get_translated_url(context, lang_code, object=None):
    """
    Get the proper URL for this page in a different language.

    Note that this algorithm performs a "best effect" approach to give a proper URL.
    To make sure the proper view URL is returned, add the :class:`~parler.views.ViewUrlMixin` to your view.

    Example, to build a language menu::

        <ul>
            {% for lang_code, title in LANGUAGES %}
                {% get_language_info for lang_code as lang %}
                {% get_translated_url lang_code as tr_url %}
                {% if tr_url %}<li{% if lang_code == LANGUAGE_CODE %} class="is-selected"{% endif %}><a href="{{ tr_url }}" hreflang="{{ lang_code }}">{{ lang.name_local|capfirst }}</a></li>{% endif %}
            {% endfor %}
        </ul>

    Or to inform search engines about the translated pages::

       {% for lang_code, title in LANGUAGES %}
           {% get_translated_url lang_code as tr_url %}
           {% if tr_url %}<link rel="alternate" hreflang="{{ lang_code }}" href="{{ tr_url }}" />{% endif %}
       {% endfor %}

    Note that using this tag is not thread-safe if the object is shared between threads.
    It temporary changes the current language of the view object.
    """
    view = context.get('view', None)
    if object is None:
        # Try a few common object variables, the SingleObjectMixin object,
        # The Django CMS "current_page" variable, or the "page" from django-fluent-pages and Mezzanine.
        # This makes this tag work with most CMSes out of the box.
        object = context.get('object', None) \
              or context.get('current_page', None) \
              or context.get('page', None)

    try:
        if view is not None:
            # Allow a view to specify what the URL should be.
            # This handles situations where the slug might be translated,
            # and gives you complete control over the results of this template tag.
            get_view_url = getattr(view, 'get_view_url', None)
            if get_view_url:
                with smart_override(lang_code):
                    return view.get_view_url()

            # Now, the "best effort" part starts.
            # See if it's a DetailView that exposes the object.
            if object is None:
                object = getattr(view, 'object', None)

        if object is not None and hasattr(object, 'get_absolute_url'):
            # There is an object, get the URL in the different language.
            # NOTE: this *assumes* that there is a detail view, not some edit view.
            # In such case, a language menu would redirect a user from the edit page
            # to a detail page; which is still way better a 404 or homepage.
            if isinstance(object, TranslatableModel):
                # Need to handle object URL translations.
                # Just using smart_override() should be enough, as a translated object
                # should use `switch_language(self)` internally before returning an URL.
                # However, it doesn't hurt to help a bit here.
                with switch_language(object, lang_code):
                    return object.get_absolute_url()
            else:
                # Always switch the language before resolving, so i18n_patterns() are supported.
                with smart_override(lang_code):
                    return object.get_absolute_url()
    except TranslationDoesNotExist:
        # Typically projects have a fallback language, so even unknown languages will return something.
        # This either means fallbacks are disabled, or the fallback language is not found!
        return ''

    # Just reverse the current URL again in a new language, and see where we end up.
    # This doesn't handle translated slugs, but will resolve to the proper view name.
    path = context['request'].path
    try:
        resolvermatch = resolve(path)
    except Resolver404:
        # Can't resolve the page itself, the page is apparently a 404.
        # This can also happen for the homepage in an i18n_patterns situation.
        return ''

    with smart_override(lang_code):
        return reverse(resolvermatch.view_name, args=resolvermatch.args, kwargs=resolvermatch.kwargs)

########NEW FILE########
__FILENAME__ = forms
from django.utils import translation
from parler.forms import TranslatableModelForm
from .utils import AppTestCase
from .testapp.models import SimpleModel


class SimpleForm(TranslatableModelForm):
    class Meta:
        model = SimpleModel


class FormTests(AppTestCase):
    """
    Test model construction
    """
    def test_form_fields(self):
        """
        Check if the form fields exist.
        """
        self.assertTrue('shared' in SimpleForm.base_fields)
        self.assertTrue('tr_title' in SimpleForm.base_fields)


    def test_form_save(self):
        """
        Check if the form receives and stores data.
        """
        with translation.override('fr'):
            # Initialize form in other language.
            x = SimpleForm(data={'shared': 'TEST', 'tr_title': 'TRANS'})
            x.language_code = 'nl'
            self.assertFalse(x.errors)

            # Data should come out
            self.assertEqual(x.cleaned_data['shared'], 'TEST')
            self.assertEqual(x.cleaned_data['tr_title'], 'TRANS')

            # Data should be saved
            instance = x.save()
            self.assertEqual(instance.get_current_language(), 'nl')

            x = SimpleModel.objects.language('nl').get(pk=instance.pk)
            self.assertEqual(x.shared, 'TEST')
            self.assertEqual(x.tr_title, 'TRANS')

########NEW FILE########
__FILENAME__ = model_attributes
from __future__ import unicode_literals
from django.conf import settings
from django.utils import translation
from parler.models import TranslationDoesNotExist
from parler import appsettings
from .utils import AppTestCase
from .testapp.models import SimpleModel, AnyLanguageModel, EmptyModel


class ModelAttributeTests(AppTestCase):
    """
    Test model construction
    """
    def test_untranslated_get(self):
        """
        Test the metaclass of the model.
        """
        try:
            value = SimpleModel().tr_title
        except Exception as e:
            self.assertIsInstance(e, TranslationDoesNotExist)
            self.assertIsInstance(e, AttributeError)
        else:
            self.fail("Expected exception from reading untranslated title, got {0}.".format(repr(value)))

        # Raising attribute error gives some additional benefits:
        self.assertEqual(getattr(SimpleModel(), 'tr_title', 'FOO'), 'FOO')
        self.assertFalse(hasattr(SimpleModel(), 'tr_title'))


    def test_default_language(self):
        """
        Test whether simple language assignments work.
        """
        with translation.override('ca-fr'):
            x = SimpleModel()   # should use get_language()
            self.assertEqual(x.get_current_language(), translation.get_language())
            self.assertEqual(translation.get_language(), 'ca-fr')

        x.shared = 'SHARED'
        x.tr_title = 'TRANS_CA'
        x.save()

        # Refetch
        with translation.override('en'):
            x = SimpleModel.objects.get(pk=x.pk)
            self.assertRaises(TranslationDoesNotExist, lambda: x.tr_title)

            # Switch context
            x.set_current_language('ca-fr')
            self.assertEqual(x.tr_title, 'TRANS_CA')


    def test_init_args(self):
        """
        Test whether passing translated attributes to __init__() works.
        """
        x = SimpleModel(tr_title='TRANS_TITLE')
        self.assertEqual(x.tr_title, "TRANS_TITLE")

        y = SimpleModel(tr_title='TRANS_TITLE', _current_language='nl')
        self.assertEqual(y.get_current_language(), 'nl')
        self.assertEqual(y.tr_title, "TRANS_TITLE")


    def test_save_multiple(self):
        """
        Test the save_translations() function to store multiple languages.
        """
        x = SimpleModel()
        x.set_current_language('en')
        x.tr_title = "TITLE_EN"
        x.set_current_language('fr')
        x.tr_title = "TITLE_FR"
        x.set_current_language('es')
        x.tr_title = "TITLE_ES"
        x.set_current_language('nl')
        x.tr_title = "TITLE_NL"

        x.save()

        # Check if all translations are saved.
        self.assertEqual(sorted(x.translations.values_list('tr_title', flat=True)), ['TITLE_EN', 'TITLE_ES', 'TITLE_FR', 'TITLE_NL'])
        self.assertEqual(sorted(x.get_available_languages()), ['en', 'es', 'fr', 'nl'])
        self.assertTrue(x.has_translation('en'))
        self.assertTrue(x.has_translation('es'))
        self.assertFalse(x.has_translation('fi'))

        # Update 2 translations.
        # Only those should be updated in the database.
        x.set_current_language('es')
        x.tr_title = "TITLE_ES2"
        x.set_current_language('nl')
        x.tr_title = "TITLE_NL2"

        self.assertNumQueries(2, x.save_translations())

        # Any unmodified language is not saved.
        x.set_current_language('it', initialize=True)
        self.assertTrue(x.has_translation('it'))  # does return true for this object.
        self.assertNumQueries(0, x.save_translations())
        self.assertEqual(sorted(x.get_available_languages()), ['en', 'es', 'fr', 'nl'])


    def test_empty_model(self):
        """
        Test whether a translated model without any fields still works.
        """
        x = EmptyModel()
        x.set_current_language('en', initialize=True)
        x.set_current_language('fr', initialize=True)
        x.set_current_language('es')
        x.set_current_language('nl', initialize=True)
        x.save()

        self.assertEqual(sorted(x.get_available_languages()), ['en', 'fr', 'nl'])


    def test_fallback_language(self):
        """
        Test whether the fallback language will be returned.
        """
        x = SimpleModel()
        x.set_current_language(self.conf_fallback)
        x.tr_title = "TITLE_FALLBACK"

        x.set_current_language(self.other_lang1)
        x.tr_title = 'TITLE_XX'
        x.save()

        with translation.override(self.other_lang2):
            x = SimpleModel.objects.get(pk=x.pk)
            self.assertEqual(x.tr_title, 'TITLE_FALLBACK')


    def test_any_fallback_model(self):
        """
        Test whether a failure in the fallback language can return any saved language (if configured for it).
        """
        x = AnyLanguageModel()
        x.set_current_language(self.other_lang1)
        x.tr_title = "TITLE_XX"

        x.save()

        with translation.override(self.other_lang2):
            x = AnyLanguageModel.objects.get(pk=x.pk)
            self.assertRaises(TranslationDoesNotExist, lambda: x._get_translated_model(use_fallback=True))
            self.assertEqual(x.tr_title, 'TITLE_XX')  # Even though there is no current language, there is a value.

            self.assertNumQueries(0, lambda: x._get_any_translated_model())   # Can fetch from cache next time.
            self.assertEqual(x._get_any_translated_model().language_code, self.other_lang1)


    def test_any_fallback_function(self):
        x = SimpleModel()
        x.set_current_language(self.other_lang1)
        x.tr_title = "TITLE_XX"

        x.save()

        with translation.override(self.other_lang2):
            x = SimpleModel.objects.get(pk=x.pk)
            self.assertRaises(TranslationDoesNotExist, lambda: x._get_translated_model(use_fallback=True))
            self.assertIs(x.safe_translation_getter('tr_title', 'DEFAULT'), 'DEFAULT')  # No lanuage, gives default
            self.assertEqual(x.safe_translation_getter('tr_title', any_language=True), 'TITLE_XX')  # Even though there is no current language, there is a value.

            self.assertNumQueries(0, lambda: x._get_any_translated_model())   # Can fetch from cache next time.
            self.assertEqual(x._get_any_translated_model().language_code, self.other_lang1)


    def test_save_ignore_fallback_marker(self):
        """
        Test whether the ``save_translations()`` method skips fallback languages
        """
        x = SimpleModel()
        x.set_current_language(self.other_lang1)
        x.tr_title = "TITLE_XX"
        x.set_current_language(self.other_lang2)
        # try fetching, causing an fallback marker
        x.safe_translation_getter('tr_title', any_language=True)

        # Now save. This should not raise errors
        x.save()

########NEW FILE########
__FILENAME__ = model_construction
from django.db.models import Manager
from .utils import AppTestCase
from .testapp.models import ManualModel, ManualModelTranslations, SimpleModel


class ModelConstructionTests(AppTestCase):
    """
    Test model construction
    """
    def test_manual_model(self):
        """
        Test the metaclass of the model.
        """
        # Test whether the link has taken place
        self.assertIsInstance(ManualModel().translations, Manager)  # RelatedManager class
        self.assertIs(ManualModel().translations.model, ManualModelTranslations)
        self.assertIs(ManualModel._translations_model, ManualModelTranslations)


    def test_simple_model(self):
        """
        Test the simple model syntax.
        """
        self.assertIs(SimpleModel().translations.model, SimpleModel._translations_model)

########NEW FILE########
__FILENAME__ = query_count
from django.core.cache import cache
from django.test.utils import override_settings
from django.utils import translation

from .utils import AppTestCase
from .testapp.models import SimpleModel


class QueryCountTests(AppTestCase):
    """
    Test model construction
    """

    @classmethod
    def setUpClass(cls):
        super(QueryCountTests, cls).setUpClass()

        cls.country_list = (
            'Mexico',
            'Monaco',
            'Morocco',
            'Netherlands',
            'Norway',
            'Poland',
            'Portugal',
            'Romania',
            'Russia',
            'South Africa',
        )

        for country in cls.country_list:
            SimpleModel.objects.create(_current_language=cls.conf_fallback, tr_title=country)


    def assertNumTranslatedQueries(self, num, qs, language_code=None):
        # Use default language if available.
        if language_code is None:
            language_code = self.conf_fallback

        # Easier to understand then a oneline lambda
        # Using str(), not unicode() to be python 3 compatible.
        def test_qs():
            for obj in qs:
                str(obj.tr_title)

        # Queryset is not set to a language, the individual models
        # will default to the currently active project language.
        with translation.override(language_code):
            self.assertNumQueries(num, test_qs)


    def test_uncached_queries(self):
        """
        Test that uncached queries work, albeit slowly.
        """
        with override_settings(PARLER_ENABLE_CACHING=False):
            self.assertNumTranslatedQueries(1 + len(self.country_list), SimpleModel.objects.all())


    def test_prefetch_queries(self):
        """
        Test that .prefetch_related() works
        """
        with override_settings(PARLER_ENABLE_CACHING=False):
            self.assertNumTranslatedQueries(2, SimpleModel.objects.prefetch_related('translations'))


    def test_model_cache_queries(self):
        """
        Test that the ``_translations_cache`` works.
        """
        cache.clear()

        with override_settings(PARLER_ENABLE_CACHING=False):
            qs = SimpleModel.objects.all()
            self.assertNumTranslatedQueries(1 + len(self.country_list), qs)
            self.assertNumTranslatedQueries(0, qs)   # All should be cached on the QuerySet and object now.

            qs = SimpleModel.objects.prefetch_related('translations')
            self.assertNumTranslatedQueries(2, qs)
            self.assertNumTranslatedQueries(0, qs)   # All should be cached on the QuerySet and object now.

########NEW FILE########
__FILENAME__ = models
from django.db import models
from parler.fields import TranslatedField
from parler.models import TranslatableModel, TranslatedFields, TranslatedFieldsModel


class ManualModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

class ManualModelTranslations(TranslatedFieldsModel):
    master = models.ForeignKey(ManualModel, related_name='translations')
    tr_title = models.CharField(max_length=200)


class SimpleModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    translations = TranslatedFields(
        tr_title = models.CharField(max_length=200)
    )

    def __unicode__(self):
        return self.tr_title


class AnyLanguageModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')
    tr_title = TranslatedField(any_language=True)

    translations = TranslatedFields(
        tr_title = models.CharField(max_length=200)
    )

    def __unicode__(self):
        return self.tr_title



class EmptyModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    # Still tracks how many languages there are, but no actual translated fields exist yet.
    # This is useful when the model is a parent object for inlines. The parent model defines the language tabs.
    translations = TranslatedFields()

    def __unicode__(self):
        return self.shared

########NEW FILE########
__FILENAME__ = utils
from __future__ import print_function
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.contrib.sites.models import Site
from django.db.models import loading
from django.template.loaders import app_directories
from django.test import TestCase
from django.utils.importlib import import_module
import os
from parler import appsettings


class AppTestCase(TestCase):
    """
    Tests for URL resolving.
    """
    user = None
    install_apps = (
        'parler.tests.testapp',
    )


    @classmethod
    def setUpClass(cls):
        if cls.install_apps:
            # When running this app via `./manage.py test fluent_pages`, auto install the test app + models.
            run_syncdb = False
            for appname in cls.install_apps:
                if appname not in settings.INSTALLED_APPS:
                    print('Adding {0} to INSTALLED_APPS'.format(appname))
                    settings.INSTALLED_APPS = (appname,) + tuple(settings.INSTALLED_APPS)
                    run_syncdb = True

                    # Flush caches
                    testapp = import_module(appname)
                    loading.cache.loaded = False
                    app_directories.app_template_dirs += (
                        os.path.join(os.path.dirname(testapp.__file__), 'templates'),
                    )

            if run_syncdb:
                call_command('syncdb', verbosity=0)  # may run south's overlaid version

        # Create basic objects
        # 1.4 does not create site automatically with the defined SITE_ID, 1.3 does.
        Site.objects.get_or_create(id=settings.SITE_ID, defaults=dict(domain='django.localhost', name='django at localhost'))
        cls.user, _ = User.objects.get_or_create(is_superuser=True, is_staff=True, username="admin")

        # Be supportive for other project settings too.
        cls.conf_fallback = appsettings.PARLER_LANGUAGES['default']['fallback'] or 'en'
        cls.other_lang1 = next(x for x, _ in settings.LANGUAGES if x != cls.conf_fallback)
        cls.other_lang2 = next(x for x, _ in settings.LANGUAGES if x not in (cls.conf_fallback, cls.other_lang1))

########NEW FILE########
__FILENAME__ = compat
"""
Django compatibility features
"""
from django.db import transaction

__all__ = (
    'transaction_atomic',
)

# New transaction support in Django 1.6
try:
    transaction_atomic = transaction.atomic
except AttributeError:
    transaction_atomic = transaction.commit_on_success

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings
from django.utils.translation import get_language



class LanguagesSetting(dict):
    """
    The languages settings dictionary, with extra methods attached.
    """

    def get_language(self, language_code, site_id=None):
        """
        Return the language settings for the current site

        This function can be used with other settings variables
        to support modules which create their own variation of the ``PARLER_LANGUAGES`` setting.
        For an example, see :func:`~parler.appsettings.add_default_language_settings`.
        """
        if site_id is None:
            site_id = getattr(settings, 'SITE_ID', None)

        for lang_dict in self.get(site_id, ()):
            if lang_dict['code'] == language_code:
                return lang_dict

        return self['default']


    def get_active_choices(self, language_code=None, site_id=None):
        """
        Find out which translations should be visible in the site.
        It returns a tuple with either a single choice (the current language),
        or a tuple with the current language + fallback language.
        """
        if language_code is None:
            language_code = get_language()

        lang_dict = self.get_language(language_code, site_id=site_id)
        if not lang_dict['hide_untranslated'] and lang_dict['fallback'] != language_code:
            return (language_code, lang_dict['fallback'])
        else:
            return (language_code,)


    def get_fallback_language(self, language_code=None, site_id=None):
        """
        Find out what the fallback language is for a given language choice.
        """
        choices = self.get_active_choices(language_code, site_id=site_id)
        if choices and len(choices) > 1:
            return choices[-1]
        else:
            return None


    def get_default_language(self):
        """
        Return the default language.
        """
        return self['default']['code']


    def get_first_language(self, site_id=None):
        """
        Return the first language for the current site.
        This can be used for user interfaces, where the languages are displayed in tabs.
        """
        if site_id is None:
            site_id = getattr(settings, 'SITE_ID', None)

        try:
            return self[site_id][0]['code']
        except (KeyError, IndexError):
            # No configuration, always fallback to default language.
            # This is essentially a non-multilingual configuration.
            return self['default']['code']

########NEW FILE########
__FILENAME__ = context
from django.utils.translation import get_language, activate

__all__ = (
    'smart_override',
    'switch_language',
)

class smart_override(object):
    """
    A contextmanager to switch the translation if needed.

    This context manager can be used to switch the Django translations
    to the current object langauge::

        def get_absolute_url(self):
            with smart_override(language):
                return reverse('myobject-details', args=(self.id,))
    """

    def __init__(self, language_code):
        self.language = language_code
        self.old_language = get_language()

    def __enter__(self):
        # Switch both Django language and object language.
        # For example, when using `object.get_absolute_url()`,
        # a i18n_url() may apply, and a translated database field.
        #
        # Be smarter then translation.override(), also avoid unneeded switches.
        if self.language != self.old_language:
            activate(self.language)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.language != self.old_language:
            activate(self.old_language)


class switch_language(object):
    """
    A contextmanager to switch the translation of an object.

    It changes both the translation language, and object language temporary.
    NOTE: when the object is shared between threads, this is not thread-safe.

    This context manager can be used to switch the Django translations
    to the current object langauge::

        def get_absolute_url(self):
            with switch_language(self):
                return reverse('myobject-details', args=(self.id,))

    It can also be used to render objects in a different language::

        with switch_language(object, 'nl'):
            print object.title
    """

    def __init__(self, object, language_code=None):
        self.object = object
        self.language = language_code or object.get_current_language()
        self.old_language = get_language()
        self.old_parler_language = object.get_current_language()

    def __enter__(self):
        # Switch both Django language and object language.
        # For example, when using `object.get_absolute_url()`,
        # a i18n_url() may apply, and a translated database field.
        #
        # Be smarter then translation.override(), also avoid unneeded switches.
        if self.language != self.old_language:
            activate(self.language)
        if self.language != self.old_parler_language:
            self.object.set_current_language(self.language)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.language != self.old_language:
            activate(self.old_language)
        if self.language != self.old_parler_language:
            self.object.set_current_language(self.old_parler_language)

########NEW FILE########
__FILENAME__ = i18n
"""
Utils for translations
"""
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

__all__ = (
    'normalize_language_code',
    'is_supported_django_language',
    'get_language_title',
    'get_language_settings',
    'get_active_language_choices',
    'is_multilingual_project',
)


LANGUAGES_DICT = dict(settings.LANGUAGES)


def normalize_language_code(code):
    """
    Undo the differences between language code notations
    """
    return code.lower().replace('_', '-')


def is_supported_django_language(language_code):
    """
    Return whether a language code is supported.
    """
    language_code2 = language_code.split('-')[0] # e.g. if fr-ca is not supported fallback to fr
    return language_code in LANGUAGES_DICT or language_code2 in LANGUAGES_DICT


def get_language_title(language_code):
    """
    Return the verbose_name for a language code.
    """
    # Avoid weird lookup errors.
    if not language_code:
        raise KeyError("Missing language_code in get_language_title()")

    try:
        return _(LANGUAGES_DICT[language_code])
    except KeyError:
        language_code = language_code.split('-')[0] # e.g. if fr-ca is not supported fallback to fr
        return _(LANGUAGES_DICT[language_code])


def get_language_settings(language_code, site_id=None):
    """
    Return the language settings for the current site
    """
    # This method mainly exists for ease-of-use.
    # the body is part of the settings, to allow third party packages
    # to have their own variation of the settings with this method functionality included.
    from parler import appsettings
    return appsettings.PARLER_LANGUAGES.get_language(language_code, site_id)


def get_active_language_choices(language_code=None):
    """
    Find out which translations should be visible in the site.
    It returns a tuple with either a single choice (the current language),
    or a tuple with the current language + fallback language.
    """
    from parler import appsettings
    return appsettings.PARLER_LANGUAGES.get_active_choices(language_code)


def is_multilingual_project(site_id=None):
    """
    Whether the current Django project is configured for multilingual support.
    """
    from parler import appsettings
    if site_id is None:
        site_id = getattr(settings, 'SITE_ID', None)
    return appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS or site_id in appsettings.PARLER_LANGUAGES

########NEW FILE########
__FILENAME__ = template
from django.template import TemplateDoesNotExist
from django.template.loader import find_template
from django.utils import six

_cached_name_lookups = {}


def select_template_name(template_name_list):
    """
    Given a list of template names, find the first one that exists.
    """
    if not isinstance(template_name_list, tuple):
        template_name_list = tuple(template_name_list)

    try:
        return _cached_name_lookups[template_name_list]
    except KeyError:
        # Find which template of the template_names is selected by the Django loader.
        for template_name in template_name_list:
            try:
                find_template(template_name)
            except TemplateDoesNotExist:
                continue
            else:
                template_name = six.text_type(template_name)  # consistent value for lazy() function.
                _cached_name_lookups[template_name_list] = template_name
                return template_name

        return None

########NEW FILE########
__FILENAME__ = views
"""
Internal DRY functions.
"""
from django.conf import settings
from parler import appsettings
from parler.utils import normalize_language_code, is_multilingual_project, get_language_title


def get_language_parameter(request, query_language_key='language', object=None, default=None):
    """
    Get the language parameter from the current request.
    """
    # This is the same logic as the django-admin uses.
    # The only difference is the origin of the request parameter.
    if not is_multilingual_project():
        # By default, the objects are stored in a single static language.
        # This makes the transition to multilingual easier as well.
        # The default language can operate as fallback language too.
        return default or appsettings.PARLER_LANGUAGES.get_default_language()
    else:
        # In multilingual mode, take the provided language of the request.
        code = request.GET.get(query_language_key)

        if not code:
            # forms: show first tab by default
            code = default or appsettings.PARLER_LANGUAGES.get_first_language()

        return normalize_language_code(code)


def get_language_tabs(request, current_language, available_languages, css_class=None):
    """
    Determine the language tabs to show.
    """
    tabs = TabsList(css_class=css_class)
    get = request.GET.copy()  # QueryDict object
    tab_languages = []

    base_url = '{0}://{1}{2}'.format(request.is_secure() and 'https' or 'http', request.get_host(), request.path)

    site_id = getattr(settings, 'SITE_ID', None)
    for lang_dict in appsettings.PARLER_LANGUAGES.get(site_id, ()):
        code = lang_dict['code']
        title = get_language_title(code)
        get['language'] = code
        url = '{0}?{1}'.format(base_url, get.urlencode())

        if code == current_language:
            status = 'current'
        elif code in available_languages:
            status = 'available'
        else:
            status = 'empty'

        tabs.append((url, title, code, status))
        tab_languages.append(code)

    # Additional stale translations in the database?
    if appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS:
        for code in available_languages:
            if code not in tab_languages:
                get['language'] = code
                url = '{0}?{1}'.format(base_url, get.urlencode())

                if code == current_language:
                    status = 'current'
                else:
                    status = 'available'

                tabs.append((url, get_language_title(code), code, status))

    tabs.current_is_translated = current_language in available_languages
    tabs.allow_deletion = len(available_languages) > 1
    return tabs


class TabsList(list):
    def __init__(self, seq=(), css_class=None):
        self.css_class = css_class
        self.current_is_translated = False
        self.allow_deletion = False
        super(TabsList, self).__init__(seq)

########NEW FILE########
__FILENAME__ = views
import django
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.views import generic
from django.views.generic.edit import ModelFormMixin
from parler.forms import TranslatableModelForm
from parler.models import TranslatableModel
from parler.utils.views import get_language_parameter, get_language_tabs

__all__ = (
    'ViewUrlMixin',
    'TranslatableSingleObjectMixin',
    'TranslatableModelFormMixin',
    'TranslatableCreateView',
    'TranslatableUpdateView',
)


class ViewUrlMixin(object):
    """
    Provide a ``view.get_view_url`` method in the template.

    This tells the template what the exact canonical URL should be of a view.
    The ``get_translated_url`` template tag uses this to find the proper translated URL of the current page.
    """
    #: The default view name used by :func:`get_view_url`, which should correspond with the view name in the URLConf.
    view_url_name = None


    def get_view_url(self):
        """
        This method is used by the ``get_translated_url`` template tag.

        By default, it uses the :attr:`view_url_name` to generate an URL.
        Override this function in case the translated URL is a bit more complex.
        """
        if not self.view_url_name:
            # Sadly, class based views can't work with reverse(func_pointer) as that's unknown.
            # Neither is it possible to use resolve(self.request.path).view_name in this function as auto-detection.
            # This function can be called in the context of a different language.
            # When i18n_patterns() is applied, that resolve() will fail.
            #
            # Hence, you need to provide a "view_url_name" as static configuration option.
            raise ImproperlyConfigured("Missing `view_url_name` attribute on {0}".format(self.__class__.__name__))

        return reverse(self.view_url_name, args=self.args, kwargs=self.kwargs)


    if django.VERSION < (1,5):
        # The `get_translated_url` tag relies on the fact that the template can access the view again.
        # This was not possible until Django 1.5, so provide the `ContextMixin` logic for earlier Django versions.

        def get_context_data(self, **kwargs):
            if 'view' not in kwargs:
                kwargs['view'] = self
            return kwargs



class TranslatableSingleObjectMixin(object):
    """
    Mixin to add translation support to class based views.
    """
    query_language_key = 'language'


    def get_object(self, queryset=None):
        """
        Assign the language for the retrieved object.
        """
        object = super(TranslatableSingleObjectMixin, self).get_object(queryset)
        if isinstance(object, TranslatableModel):
            object.set_current_language(self._language(object), initialize=True)
        return object


    def _language(self, object=None):
        """
        Get the language parameter from the current request.
        """
        return get_language_parameter(self.request, self.query_language_key, object=object, default=self.get_default_language(object=object))


    def get_default_language(self, object=None):
        """
        Return the default language to use, if no language parameter is given.
        By default, it uses the default parler-language.
        """
        # Some users may want to override this, to return get_language()
        return None


class TranslatableModelFormMixin(TranslatableSingleObjectMixin):
    """
    Mixin to add translation support to class based views.
    """

    def get_form_class(self):
        """
        Return a ``TranslatableModelForm`` by default if no form_class is set.
        """
        super_method = super(TranslatableModelFormMixin, self).get_form_class
        if not (super_method.__func__ is ModelFormMixin.get_form_class.__func__):
            # Don't get in your way, if you've overwritten stuff.
            return super_method()
        else:
            # Same logic as ModelFormMixin.get_form_class, but using the right form base class.
            if self.form_class:
                return self.form_class
            else:
                model = _get_view_model(self)
                return modelform_factory(model, form=TranslatableModelForm)


    def get_form_kwargs(self):
        """
        Pass the current language to the form.
        """
        kwargs = super(TranslatableModelFormMixin, self).get_form_kwargs()
        # The TranslatableAdmin can set form.language_code, because the modeladmin always creates a fresh subclass.
        # If that would be done here, the original globally defined form class would be updated.
        kwargs['_current_language'] = self.get_form_language()
        return kwargs


    def get_form_language(self):
        """
        Return the current language for the currently displayed object fields.
        """
        if self.object is not None:
            return self.object.get_current_language()
        else:
            return self._language()


    def get_context_data(self, **kwargs):
        context = super(TranslatableModelFormMixin, self).get_context_data(**kwargs)
        context['language_tabs'] = self.get_language_tabs()
        return context


    def get_language_tabs(self):
        """
        Determine the language tabs to show.
        """
        current_language = self.get_form_language()
        if self.object:
            available_languages = list(self.object.get_available_languages())
        else:
            available_languages = []

        return get_language_tabs(self.request, current_language, available_languages)


# For the lazy ones:
class TranslatableCreateView(TranslatableModelFormMixin, generic.CreateView):
    """
    Create view that supports translated models.
    """
    pass


class TranslatableUpdateView(TranslatableModelFormMixin, generic.UpdateView):
    """
    Update view that supports translated models.
    """
    pass



def _get_view_model(self):
    if self.model is not None:
        # If a model has been explicitly provided, use it
        return self.model
    elif hasattr(self, 'object') and self.object is not None:
        # If this view is operating on a single object, use the class of that object
        return self.object.__class__
    else:
        # Try to get a queryset and extract the model class from that
        return self.get_queryset().model

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from django.conf import settings, global_settings as default_settings
from django.core.management import execute_from_command_line
from os import path

if not settings.configured:
    module_root = path.dirname(path.realpath(__file__))

    settings.configure(
        DEBUG = False,  # will be False anyway by DjangoTestRunner.
        TEMPLATE_DEBUG = True,
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        },
        TEMPLATE_LOADERS = (
            'django.template.loaders.app_directories.Loader',
        ),
        TEMPLATE_CONTEXT_PROCESSORS = default_settings.TEMPLATE_CONTEXT_PROCESSORS + (
            'django.core.context_processors.request',
        ),
        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sites',
            'django.contrib.admin',
            'django.contrib.sessions',
            'parler',
            'parler.tests.testapp',
        ),
        TEST_RUNNER='django.test.simple.DjangoTestSuiteRunner',   # for Django 1.6, see https://docs.djangoproject.com/en/dev/releases/1.6/#new-test-runner

        SITE_ID = 4,
        LANGUAGE_CODE = 'en',
        PARLER_LANGUAGES = {
            4: (
                {'code': 'nl'},
                {'code': 'de'},
                {'code': 'en'},
            ),
            'default': {
                'fallback': 'en',
            },
        },
    )

def runtests():
    argv = sys.argv[:1] + ['test', 'parler'] + sys.argv[1:]
    execute_from_command_line(argv)

if __name__ == '__main__':
    runtests()

########NEW FILE########
