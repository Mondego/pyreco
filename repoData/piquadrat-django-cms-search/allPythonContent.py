__FILENAME__ = cms_app
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _

from cms.app_base import CMSApp

from haystack.views import search_view_factory

class HaystackSearchApphook(CMSApp):
    name = _("search apphook")
    urls = [patterns('',
        url('^$', search_view_factory(), name='haystack-search'),
    ),]


########NEW FILE########
__FILENAME__ = models
from cms.models import Page
from cms.models.managers import PageManager
from django.conf import settings
from django.utils.translation import ugettext_lazy, string_concat, activate, get_language

def proxy_name(language_code):
    safe_code = language_code.replace('-', ' ').title().replace(' ', '_')
    return 'Page_%s' % safe_code


def page_proxy_factory(language_code, language_name):
    def get_absolute_url(self):
        if 'cms.middleware.multilingual.MultilingualURLMiddleware' in settings.MIDDLEWARE_CLASSES:
            old_language = get_language()
            try:
                activate(language_code)
                return '/%s%s' % (language_code, Page.get_absolute_url(self))
            finally:
                activate(old_language)
        else:
            return Page.get_absolute_url(self)

    class Meta:
        proxy = True
        app_label = 'cms_search'
        if len(settings.LANGUAGES) > 1:
            verbose_name = string_concat(Page._meta.verbose_name, ' (', language_name, ')')
            verbose_name_plural = string_concat(Page._meta.verbose_name_plural, ' (', language_name, ')')
        else:
            verbose_name = Page._meta.verbose_name
            verbose_name_plural = Page._meta.verbose_name_plural

    attrs = {'__module__': Page.__module__,
             'Meta': Meta,
             'objects': PageManager(),
             'get_absolute_url': get_absolute_url}

    _PageProxy = type(proxy_name(language_code), (Page,), attrs)

    _PageProxy._meta.parent_attr = 'parent'
    _PageProxy._meta.left_attr = 'lft'
    _PageProxy._meta.right_attr = 'rght'
    _PageProxy._meta.tree_id_attr = 'tree_id'

    return _PageProxy

module_namespace = globals()

for language_code, language_name in settings.LANGUAGES:
    if isinstance(language_name, basestring):
        language_name = ugettext_lazy(language_name)
    proxy_model = page_proxy_factory(language_code, language_name)
    module_namespace[proxy_model.__name__] = proxy_model
########NEW FILE########
__FILENAME__ = fields
from django.conf import settings
from haystack import indexes
from django.utils.translation import get_language, activate
from django.template import loader, Context

try:
    from django.test.client import RequestFactory
except ImportError:
    from cms_search.utils import RequestFactory

rf = RequestFactory()

class MultiLangTemplateField(indexes.CharField):

    def __init__(self, needs_request=False, **kwargs):
        kwargs['use_template'] = True
        self.needs_request = needs_request
        super(MultiLangTemplateField, self).__init__(**kwargs)

    def prepare_template(self, obj):
        content = []
        current_lang = get_language()
        try:
            for lang, lang_name in settings.LANGUAGES:
                activate(lang)
                content.append(self._prepare_template(obj, needs_request=self.needs_request))
        finally:
            activate(current_lang)
        return '\n'.join(content)

    def _prepare_template(self, obj, needs_request=False):
        """
        This is a copy of CharField.prepare_template, except that it adds a fake
        request to the context, which is mainly needed to render CMS placeholders
        """
        if self.instance_name is None and self.template_name is None:
            raise SearchFieldError("This field requires either its instance_name variable to be populated or an explicit template_name in order to load the correct template.")

        if self.template_name is not None:
            template_names = self.template_name

            if not isinstance(template_names, (list, tuple)):
                template_names = [template_names]
        else:
            template_names = ['search/indexes/%s/%s_%s.txt' % (obj._meta.app_label, obj._meta.module_name, self.instance_name)]

        t = loader.select_template(template_names)
        ctx = {'object': obj}
        if needs_request:
            request = rf.get("/")
            request.session = {}
            ctx['request'] = request
        return t.render(Context(ctx))

########NEW FILE########
__FILENAME__ = indexes
import inspect

from django.conf import settings
from haystack import indexes
from django.utils.translation import activate, get_language


class MultiLangPrepareDecorator(object):
    def __init__(self, language):
        self.language = language

    def __call__(self, func):
        def wrapped(*args):
            old_language = get_language()
            activate(self.language)
            try:
                return func(*args)
            finally:
                activate(old_language)
        return wrapped


class MultiLanguageIndexBase(indexes.DeclarativeMetaclass):

    @classmethod
    def _get_field_copy(cls, field, language):
        model_attr = field.model_attr
        if model_attr:
            model_attr += '_%s' % language.replace('-', '_')
        arg_names = inspect.getargspec(indexes.SearchField.__init__)[0][2:]
        kwargs = dict((arg_name, getattr(field, arg_name)) for arg_name in arg_names if hasattr(field, arg_name))
        kwargs['model_attr'] = model_attr
        copy = field.__class__(**kwargs)
        copy.null = True
        return copy

    def __new__(cls, name, bases, attrs):
        if 'HaystackTrans' in attrs:
            for field in getattr(attrs['HaystackTrans'], 'fields', []):
                if field not in attrs:
                    continue
                for lang_tuple in settings.LANGUAGES:
                    lang = lang_tuple[0]
                    safe_lang = lang.replace('-', '_')
                    attrs['%s_%s' % (field, safe_lang)] = cls._get_field_copy(attrs[field], lang)
                    if 'prepare_' + field in attrs:
                        attrs['prepare_%s_%s' % (field, safe_lang)] = MultiLangPrepareDecorator(lang)(attrs['prepare_' + field])
        return super(MultiLanguageIndexBase, cls).__new__(cls, name, bases, attrs)


class MultiLanguageIndex(indexes.SearchIndex):
    __metaclass__ = MultiLanguageIndexBase

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = cms_search_tags
from classytags.arguments import Argument
from classytags.core import Options
from classytags.helpers import AsTag
import haystack
from django import template
from django.conf import settings
from django.utils.translation import get_language

register = template.Library()

class GetTransFieldTag(AsTag):
    """
    Templatetag to access translated attributes of a `haystack.models.SearchResult`.

    By default, it looks for a translated field at `field_name`_`language`. To
    customize this, subclass `GetTransFieldTag` and override `get_translated_value`.

    """
    EMPTY_VALUE = ''
    FALLBACK = True
    name = 'get_translated_value'
    options = Options(
        Argument('obj'),
        Argument('field_name'),
        'as',
        Argument('varname', resolve=False, required=False)
    )
    
    def get_value(self, context, obj, field_name):
        """
        gets the translated value of field name. If `FALLBACK`evaluates to `True` and the field
        has no translation for the current language, it tries to find a fallback value, using
        the languages defined in `settings.LANGUAGES`.

        """
        try:
            language = get_language()
            value = self.get_translated_value(obj, field_name, language)
            if value:
                return value
            if self.FALLBACK:
                for lang, lang_name in settings.LANGUAGES:
                    if lang == language:
                        # already tried this one...
                        continue
                    value = self.get_translated_value(obj, field_name, lang)
                    if value:
                        return value
            untranslated = getattr(obj, field_name)
            if self._is_truthy(untranslated):
                return untranslated
            else:
                return self.EMPTY_VALUE
        except Exception:
            if settings.TEMPLATE_DEBUG:
                raise
            return self.EMPTY_VALUE

    def get_translated_value(self, obj, field_name, language):
        safe_lang = language.replace('-', '_')
        value = getattr(obj, '%s_%s' % (field_name, safe_lang), '')
        if self._is_truthy(value):
            return value
        else:
            return self.EMPTY_VALUE

    def _is_truthy(self, value):
        if isinstance(value, haystack.fields.NOT_PROVIDED):
            return False
        elif isinstance(value, basestring) and value.startswith('<haystack.fields.NOT_PROVIDED instance at '): #UUUGLY!!
            return False
        return bool(value)


register.tag(GetTransFieldTag)
########NEW FILE########
__FILENAME__ = search_indexes
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.models import Site
from django.db.models import Q
from django.db.models.query import EmptyQuerySet
from django.template import RequestContext
from django.test.client import RequestFactory
from django.utils.encoding import force_unicode
from django.utils.translation import get_language, activate


def _strip_tags(value):
    """
    Returns the given HTML with all tags stripped.

    This is a copy of django.utils.html.strip_tags, except that it adds some
    whitespace in between replaced tags to make sure words are not erroneously
    concatenated.
    """
    return re.sub(r'<[^>]*?>', ' ', force_unicode(value))

try:
    import importlib
except ImportError:
    from django.utils import importlib

from haystack import indexes, site

from cms.models.pluginmodel import CMSPlugin

from cms_search import models as proxy_models
from cms_search import settings as search_settings

def _get_index_base():
    index_string = search_settings.INDEX_BASE_CLASS
    module, class_name = index_string.rsplit('.', 1)
    mod = importlib.import_module(module)
    base_class = getattr(mod, class_name, None)
    if not base_class:
        raise ImproperlyConfigured('CMS_SEARCH_INDEX_BASE_CLASS: module %s has no class %s' % (module, class_name))
    if not issubclass(base_class, indexes.SearchIndex):
        raise ImproperlyConfigured('CMS_SEARCH_INDEX_BASE_CLASS: %s is not a subclass of haystack.indexes.SearchIndex' % search_settings.INDEX_BASE_CLASS)
    return base_class

rf = RequestFactory()

def page_index_factory(language_code):

    class _PageIndex(_get_index_base()):
        _language = language_code
        language = indexes.CharField()

        text = indexes.CharField(document=True, use_template=False)
        pub_date = indexes.DateTimeField(model_attr='publication_date', null=True)
        login_required = indexes.BooleanField(model_attr='login_required')
        url = indexes.CharField(stored=True, indexed=False, model_attr='get_absolute_url')
        title = indexes.CharField(stored=True, indexed=False, model_attr='get_title')
        site_id = indexes.IntegerField(stored=True, indexed=True, model_attr='site_id')

        def prepare(self, obj):
            current_languge = get_language()
            try:
                if current_languge != self._language:
                    activate(self._language)
                request = rf.get("/")
                request.session = {}
                request.LANGUAGE_CODE = self._language
                self.prepared_data = super(_PageIndex, self).prepare(obj)
                plugins = CMSPlugin.objects.filter(language=language_code, placeholder__in=obj.placeholders.all())
                text = u''
                for base_plugin in plugins:
                    instance, plugin_type = base_plugin.get_plugin_instance()
                    if instance is None:
                        # this is an empty plugin
                        continue
                    if hasattr(instance, 'search_fields'):
                        text += u' '.join(force_unicode(_strip_tags(getattr(instance, field, ''))) for field in instance.search_fields)
                    if getattr(instance, 'search_fulltext', False) or getattr(plugin_type, 'search_fulltext', False):
                        text += _strip_tags(instance.render_plugin(context=RequestContext(request))) + u' '
                text += obj.get_meta_description() or u''
                text += u' '
                text += obj.get_meta_keywords() or u''
                self.prepared_data['text'] = text
                self.prepared_data['language'] = self._language
                return self.prepared_data
            finally:
                if get_language() != current_languge:
                    activate(current_languge)

        def index_queryset(self):
            # get the correct language and exclude pages that have a redirect
            base_qs = super(_PageIndex, self).index_queryset()
            result_qs = EmptyQuerySet()
            for site_obj in Site.objects.all():
                qs = base_qs.published(site=site_obj.id).filter(
                    Q(title_set__language=language_code) & (Q(title_set__redirect__exact='') | Q(title_set__redirect__isnull=True)))
                if 'publisher' in settings.INSTALLED_APPS:
                    qs = qs.filter(publisher_is_draft=True)
                qs = qs.distinct()
                result_qs |= qs
            return result_qs

    return _PageIndex

for language_code, language_name in settings.LANGUAGES:
    proxy_model = getattr(proxy_models, proxy_models.proxy_name(language_code))
    index = page_index_factory(language_code)
    if proxy_model:
        site.register(proxy_model, index)
    else:
        print "no page proxy model found for language %s" % language_code

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

INDEX_BASE_CLASS = getattr(settings, 'CMS_SEARCH_INDEX_BASE_CLASS', 'haystack.indexes.SearchIndex')
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-cms-search documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 31 22:33:26 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
sys.path.append(os.path.join(os.path.abspath('.'), '_ext'))
extensions = ['djangorefs', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-cms-search'
copyright = u'2012, Divio AG'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6.2'
# The full version, including alpha/beta/rc tags.
release = '0.6.2'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-cms-searchdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-cms-search.tex', u'django-cms-search Documentation',
   u'Divio GmbH', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
    'haystack': ('http://readthedocs.org/docs/django-haystack/en/latest/', None),
    'django': ('http://readthedocs.org/docs/django/en/latest/', None),
    'cms': ('http://readthedocs.org/docs/django-cms/en/2.1.3/', None),
}


########NEW FILE########
__FILENAME__ = djangorefs
def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    ) 
########NEW FILE########
__FILENAME__ = metadata
package_name = 'cms_search'
name = 'django-cms-search'
author = 'Benjamin Wohlwend'
author_email = 'piquadrat@gmail.com'
description = "An extension to django CMS to provide multilingual Haystack indexes"
version = __import__(package_name).__version__
project_url = 'http://github.com/piquadrat/%s' % name
license = 'BSD'

########NEW FILE########
