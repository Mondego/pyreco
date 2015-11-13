__FILENAME__ = conf
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys, os

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

sys.path.append(os.path.abspath(os.pardir))

from pelican import __version__

# -- General configuration -----------------------------------------------------
templates_path = ['_templates']
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.ifconfig', 'sphinx.ext.extlinks']
source_suffix = '.rst'
master_doc = 'index'
project = 'Pelican'
copyright = '2014, Alexis Metaireau and contributors'
exclude_patterns = ['_build']
release = __version__
version = '.'.join(release.split('.')[:1])
last_stable = '3.3.0'
rst_prolog = '''
.. |last_stable| replace:: :pelican-doc:`{0}`
'''.format(last_stable)

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

extlinks = {
    'pelican-doc':  ('http://docs.getpelican.com/%s/', '')
}

# -- Options for HTML output ---------------------------------------------------

html_theme = 'default'
if not on_rtd:
    try:
        import sphinx_rtd_theme
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    except ImportError:
        pass

html_static_path = ['_static']

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pelicandoc'

html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = False

# If false, no index is generated.
html_use_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False


def setup(app):
    # overrides for wide tables in RTD theme
    app.add_stylesheet('theme_overrides.css')   # path relative to _static


# -- Options for LaTeX output --------------------------------------------------
latex_documents = [
    ('index', 'Pelican.tex', 'Pelican Documentation',
   'Alexis Métaireau', 'manual'),
]

# -- Options for manual page output --------------------------------------------
man_pages = [
    ('index', 'pelican', 'pelican documentation',
     ['Alexis Métaireau'], 1),
    ('pelican-themes', 'pelican-themes', 'A theme manager for Pelican',
     ['Mickaël Raybaud'], 1),
    ('themes', 'pelican-theming', 'How to create themes for Pelican',
     ['The Pelican contributors'], 1)
]

########NEW FILE########
__FILENAME__ = contents
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import six
from six.moves.urllib.parse import unquote

import copy
import locale
import logging
import functools
import os
import re
import sys

try:
    from urlparse import urlparse, urlunparse
except ImportError:
    from urllib.parse import urlparse, urlunparse

from datetime import datetime


from pelican import signals
from pelican.settings import DEFAULT_CONFIG
from pelican.utils import (slugify, truncate_html_words, memoized, strftime,
                           python_2_unicode_compatible, deprecated_attribute,
                           path_to_url)

# Import these so that they're avalaible when you import from pelican.contents.
from pelican.urlwrappers import (URLWrapper, Author, Category, Tag)  # NOQA

logger = logging.getLogger(__name__)


class Content(object):
    """Represents a content.

    :param content: the string to parse, containing the original content.
    :param metadata: the metadata associated to this page (optional).
    :param settings: the settings dictionary (optional).
    :param source_path: The location of the source of this content (if any).
    :param context: The shared context between generators.

    """
    @deprecated_attribute(old='filename', new='source_path', since=(3, 2, 0))
    def filename():
        return None

    def __init__(self, content, metadata=None, settings=None,
                 source_path=None, context=None):
        if metadata is None:
            metadata = {}
        if settings is None:
            settings = copy.deepcopy(DEFAULT_CONFIG)

        self.settings = settings
        self._content = content
        if context is None:
            context = {}
        self._context = context
        self.translations = []

        local_metadata = dict(settings['DEFAULT_METADATA'])
        local_metadata.update(metadata)

        # set metadata as attributes
        for key, value in local_metadata.items():
            if key in ('save_as', 'url'):
                key = 'override_' + key
            setattr(self, key.lower(), value)

        # also keep track of the metadata attributes available
        self.metadata = local_metadata

        #default template if it's not defined in page
        self.template = self._get_template()

        # First, read the authors from "authors", if not, fallback to "author"
        # and if not use the settings defined one, if any.
        if not hasattr(self, 'author'):
            if hasattr(self, 'authors'):
                self.author = self.authors[0]
            elif 'AUTHOR' in settings:
                self.author = Author(settings['AUTHOR'], settings)

        if not hasattr(self, 'authors') and hasattr(self, 'author'):
            self.authors = [self.author]

        # XXX Split all the following code into pieces, there is too much here.

        # manage languages
        self.in_default_lang = True
        if 'DEFAULT_LANG' in settings:
            default_lang = settings['DEFAULT_LANG'].lower()
            if not hasattr(self, 'lang'):
                self.lang = default_lang

            self.in_default_lang = (self.lang == default_lang)

        # create the slug if not existing, generate slug according to 
        # setting of SLUG_ATTRIBUTE
        if not hasattr(self, 'slug'):
            if settings['SLUGIFY_SOURCE'] == 'title' and hasattr(self, 'title'):
                self.slug = slugify(self.title,
                                settings.get('SLUG_SUBSTITUTIONS', ()))
            elif settings['SLUGIFY_SOURCE'] == 'basename' and source_path != None:
                basename = os.path.basename(os.path.splitext(source_path)[0])
                self.slug = slugify(basename,
                                settings.get('SLUG_SUBSTITUTIONS', ()))

        self.source_path = source_path

        # manage the date format
        if not hasattr(self, 'date_format'):
            if hasattr(self, 'lang') and self.lang in settings['DATE_FORMATS']:
                self.date_format = settings['DATE_FORMATS'][self.lang]
            else:
                self.date_format = settings['DEFAULT_DATE_FORMAT']

        if isinstance(self.date_format, tuple):
            locale_string = self.date_format[0]
            if sys.version_info < (3, ) and isinstance(locale_string,
                                                       six.text_type):
                locale_string = locale_string.encode('ascii')
            locale.setlocale(locale.LC_ALL, locale_string)
            self.date_format = self.date_format[1]

        if hasattr(self, 'date'):
            self.locale_date = strftime(self.date, self.date_format)
        if hasattr(self, 'modified'):
            self.locale_modified = strftime(self.modified, self.date_format)

        # manage status
        if not hasattr(self, 'status'):
            self.status = settings['DEFAULT_STATUS']
            if not settings['WITH_FUTURE_DATES']:
                if hasattr(self, 'date') and self.date > datetime.now():
                    self.status = 'draft'

        # store the summary metadata if it is set
        if 'summary' in metadata:
            self._summary = metadata['summary']

        signals.content_object_init.send(self)

    def __str__(self):
        if self.source_path is None:
            return repr(self)
        elif six.PY3:
            return self.source_path or repr(self)
        else:
            return str(self.source_path.encode('utf-8', 'replace'))

    def check_properties(self):
        """Test mandatory properties are set."""
        for prop in self.mandatory_properties:
            if not hasattr(self, prop):
                raise NameError(prop)

    @property
    def url_format(self):
        """Returns the URL, formatted with the proper values"""
        metadata = copy.copy(self.metadata)
        path = self.metadata.get('path', self.get_relative_source_path())
        default_category = self.settings['DEFAULT_CATEGORY']
        slug_substitutions = self.settings.get('SLUG_SUBSTITUTIONS', ())
        metadata.update({
            'path': path_to_url(path),
            'slug': getattr(self, 'slug', ''),
            'lang': getattr(self, 'lang', 'en'),
            'date': getattr(self, 'date', datetime.now()),
            'author': slugify(
                getattr(self, 'author', ''),
                slug_substitutions
            ),
            'category': slugify(
                getattr(self, 'category', default_category),
                slug_substitutions
            )
        })
        return metadata

    def _expand_settings(self, key):
        fq_key = ('%s_%s' % (self.__class__.__name__, key)).upper()
        return self.settings[fq_key].format(**self.url_format)

    def get_url_setting(self, key):
        if hasattr(self, 'override_' + key):
            return getattr(self, 'override_' + key)
        key = key if self.in_default_lang else 'lang_%s' % key
        return self._expand_settings(key)

    def _update_content(self, content, siteurl):
        """Update the content attribute.

        Change all the relative paths of the content to relative paths
        suitable for the ouput content.

        :param content: content resource that will be passed to the templates.
        :param siteurl: siteurl which is locally generated by the writer in
                        case of RELATIVE_URLS.
        """
        if not content:
            return content

        instrasite_link_regex = self.settings['INTRASITE_LINK_REGEX']
        regex = r"""
            (?P<markup><\s*[^\>]*  # match tag with all url-value attributes
                (?:href|src|poster|data|cite|formaction|action)\s*=)

            (?P<quote>["\'])      # require value to be quoted
            (?P<path>{0}(?P<value>.*?))  # the url value
            \2""".format(instrasite_link_regex)
        hrefs = re.compile(regex, re.X)

        def replacer(m):
            what = m.group('what')
            value = urlparse(m.group('value'))
            path = value.path
            origin = m.group('path')

            # XXX Put this in a different location.
            if what == 'filename':
                if path.startswith('/'):
                    path = path[1:]
                else:
                    # relative to the source path of this content
                    path = self.get_relative_source_path(
                        os.path.join(self.relative_dir, path)
                    )

                if path not in self._context['filenames']:
                    unquoted_path = path.replace('%20', ' ')

                    if unquoted_path in self._context['filenames']:
                        path = unquoted_path

                if path in self._context['filenames']:
                    origin = '/'.join((siteurl,
                             self._context['filenames'][path].url))
                    origin = origin.replace('\\', '/')  # for Windows paths.
                else:
                    logger.warning(("Unable to find {fn}, skipping url"
                                    " replacement".format(fn=value),
                                    "Other resources were not found"
                                    " and their urls not replaced"))
            elif what == 'category':
                origin = Category(path, self.settings).url
            elif what == 'tag':
                origin = Tag(path, self.settings).url

            # keep all other parts, such as query, fragment, etc.
            parts = list(value)
            parts[2] = origin
            origin = urlunparse(parts)

            return ''.join((m.group('markup'), m.group('quote'), origin,
                            m.group('quote')))

        return hrefs.sub(replacer, content)

    @memoized
    def get_content(self, siteurl):

        if hasattr(self, '_get_content'):
            content = self._get_content()
        else:
            content = self._content
        return self._update_content(content, siteurl)

    @property
    def content(self):
        return self.get_content(self._context.get('localsiteurl', ''))

    def _get_summary(self):
        """Returns the summary of an article.

        This is based on the summary metadata if set, otherwise truncate the
        content.
        """
        if hasattr(self, '_summary'):
            return self._summary

        if self.settings['SUMMARY_MAX_LENGTH'] is None:
            return self.content

        return truncate_html_words(self.content,
                                   self.settings['SUMMARY_MAX_LENGTH'])

    def _set_summary(self, summary):
        """Dummy function"""
        pass

    summary = property(_get_summary, _set_summary, "Summary of the article."
                       "Based on the content. Can't be set")
    url = property(functools.partial(get_url_setting, key='url'))
    save_as = property(functools.partial(get_url_setting, key='save_as'))

    def _get_template(self):
        if hasattr(self, 'template') and self.template is not None:
            return self.template
        else:
            return self.default_template

    def get_relative_source_path(self, source_path=None):
        """Return the relative path (from the content path) to the given
        source_path.

        If no source path is specified, use the source path of this
        content object.
        """
        if not source_path:
            source_path = self.source_path
        if source_path is None:
            return None

        return os.path.relpath(
            os.path.abspath(os.path.join(self.settings['PATH'], source_path)),
            os.path.abspath(self.settings['PATH'])
        )

    @property
    def relative_dir(self):
        return os.path.dirname(os.path.relpath(
            os.path.abspath(self.source_path),
            os.path.abspath(self.settings['PATH']))
        )


class Page(Content):
    mandatory_properties = ('title',)
    default_template = 'page'


class Article(Page):
    mandatory_properties = ('title', 'date', 'category')
    default_template = 'article'


class Draft(Page):
    mandatory_properties = ('title', 'category')
    default_template = 'article'


class Quote(Page):
    base_properties = ('author', 'date')


@python_2_unicode_compatible
class Static(Page):
    @deprecated_attribute(old='filepath', new='source_path', since=(3, 2, 0))
    def filepath():
        return None

    @deprecated_attribute(old='src', new='source_path', since=(3, 2, 0))
    def src():
        return None

    @deprecated_attribute(old='dst', new='save_as', since=(3, 2, 0))
    def dst():
        return None


def is_valid_content(content, f):
    try:
        content.check_properties()
        return True
    except NameError as e:
        logger.error("Skipping %s: could not find information about "
                     "'%s'" % (f, e))
        return False

########NEW FILE########
__FILENAME__ = generators
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
import math
import random
import logging
import shutil
import fnmatch
import calendar

from codecs import open
from collections import defaultdict
from functools import partial
from itertools import chain, groupby
from operator import attrgetter, itemgetter

from jinja2 import (Environment, FileSystemLoader, PrefixLoader, ChoiceLoader,
                    BaseLoader, TemplateNotFound)

from pelican.contents import Article, Draft, Page, Static, is_valid_content
from pelican.readers import Readers
from pelican.utils import (copy, process_translations, mkdir_p, DateFormatter,
                           FileStampDataCacher)
from pelican import signals


logger = logging.getLogger(__name__)


class Generator(object):
    """Baseclass generator"""

    def __init__(self, context, settings, path, theme, output_path,
                 readers_cache_name='', **kwargs):
        self.context = context
        self.settings = settings
        self.path = path
        self.theme = theme
        self.output_path = output_path

        for arg, value in kwargs.items():
            setattr(self, arg, value)

        self.readers = Readers(self.settings, readers_cache_name)

        # templates cache
        self._templates = {}
        self._templates_path = []
        self._templates_path.append(os.path.expanduser(
            os.path.join(self.theme, 'templates')))
        self._templates_path += self.settings['EXTRA_TEMPLATES_PATHS']

        theme_path = os.path.dirname(os.path.abspath(__file__))

        simple_loader = FileSystemLoader(os.path.join(theme_path,
                                         "themes", "simple", "templates"))
        self.env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            loader=ChoiceLoader([
                FileSystemLoader(self._templates_path),
                simple_loader,  # implicit inheritance
                PrefixLoader({'!simple': simple_loader})  # explicit one
            ]),
            extensions=self.settings['JINJA_EXTENSIONS'],
        )

        logger.debug('template list: {0}'.format(self.env.list_templates()))

        # provide utils.strftime as a jinja filter
        self.env.filters.update({'strftime': DateFormatter()})

        # get custom Jinja filters from user settings
        custom_filters = self.settings['JINJA_FILTERS']
        self.env.filters.update(custom_filters)

        signals.generator_init.send(self)

    def get_template(self, name):
        """Return the template by name.
        Use self.theme to get the templates to use, and return a list of
        templates ready to use with Jinja2.
        """
        if name not in self._templates:
            try:
                self._templates[name] = self.env.get_template(name + '.html')
            except TemplateNotFound:
                raise Exception('[templates] unable to load %s.html from %s'
                                % (name, self._templates_path))
        return self._templates[name]

    def _include_path(self, path, extensions=None):
        """Inclusion logic for .get_files(), returns True/False

        :param path: the path which might be including
        :param extensions: the list of allowed extensions (if False, all
            extensions are allowed)
        """
        if extensions is None:
            extensions = tuple(self.readers.extensions)
        basename = os.path.basename(path)

        #check IGNORE_FILES
        ignores = self.settings['IGNORE_FILES']
        if any(fnmatch.fnmatch(basename, ignore) for ignore in ignores):
            return False

        if extensions is False or basename.endswith(extensions):
            return True
        return False

    def get_files(self, path, exclude=[], extensions=None):
        """Return a list of files to use, based on rules

        :param path: the path to search (relative to self.path)
        :param exclude: the list of path to exclude
        :param extensions: the list of allowed extensions (if False, all
            extensions are allowed)
        """
        files = []
        root = os.path.join(self.path, path)

        if os.path.isdir(root):
            for dirpath, dirs, temp_files in os.walk(root, followlinks=True):
                for e in exclude:
                    if e in dirs:
                        dirs.remove(e)
                reldir = os.path.relpath(dirpath, self.path)
                for f in temp_files:
                    fp = os.path.join(reldir, f)
                    if self._include_path(fp, extensions):
                        files.append(fp)
        elif os.path.exists(root) and self._include_path(path, extensions):
            files.append(path)  # can't walk non-directories
        return files

    def add_source_path(self, content):
        location = content.get_relative_source_path()
        self.context['filenames'][location] = content

    def _update_context(self, items):
        """Update the context with the given items from the currrent
        processor.
        """
        for item in items:
            value = getattr(self, item)
            if hasattr(value, 'items'):
                value = list(value.items())  # py3k safeguard for iterators
            self.context[item] = value


class CachingGenerator(Generator, FileStampDataCacher):
    '''Subclass of Generator and FileStampDataCacher classes

    enables content caching, either at the generator or reader level
    '''

    def __init__(self, *args, **kwargs):
        '''Initialize the generator, then set up caching

        note the multiple inheritance structure
        '''
        cls_name = self.__class__.__name__
        Generator.__init__(self, *args,
                           readers_cache_name=(cls_name + '-Readers'),
                           **kwargs)

        cache_this_level = self.settings['CONTENT_CACHING_LAYER'] == 'generator'
        caching_policy = cache_this_level and self.settings['CACHE_CONTENT']
        load_policy = cache_this_level and self.settings['LOAD_CONTENT_CACHE']
        FileStampDataCacher.__init__(self, self.settings, cls_name,
                                     caching_policy, load_policy
                                     )

    def _get_file_stamp(self, filename):
        '''Get filestamp for path relative to generator.path'''
        filename = os.path.join(self.path, filename)
        return super(CachingGenerator, self)._get_file_stamp(filename)


class _FileLoader(BaseLoader):

    def __init__(self, path, basedir):
        self.path = path
        self.fullpath = os.path.join(basedir, path)

    def get_source(self, environment, template):
        if template != self.path or not os.path.exists(self.fullpath):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(self.fullpath)
        with open(self.fullpath, 'r', encoding='utf-8') as f:
            source = f.read()
        return (source, self.fullpath,
                lambda: mtime == os.path.getmtime(self.fullpath))


class TemplatePagesGenerator(Generator):

    def generate_output(self, writer):
        for source, dest in self.settings['TEMPLATE_PAGES'].items():
            self.env.loader.loaders.insert(0, _FileLoader(source, self.path))
            try:
                template = self.env.get_template(source)
                rurls = self.settings['RELATIVE_URLS']
                writer.write_file(dest, template, self.context, rurls,
                                  override_output=True)
            finally:
                del self.env.loader.loaders[0]


class ArticlesGenerator(CachingGenerator):
    """Generate blog articles"""

    def __init__(self, *args, **kwargs):
        """initialize properties"""
        self.articles = []  # only articles in default language
        self.translations = []
        self.dates = {}
        self.tags = defaultdict(list)
        self.categories = defaultdict(list)
        self.related_posts = []
        self.authors = defaultdict(list)
        self.drafts = [] # only drafts in default language
        self.drafts_translations = []
        super(ArticlesGenerator, self).__init__(*args, **kwargs)
        signals.article_generator_init.send(self)

    def generate_feeds(self, writer):
        """Generate the feeds from the current context, and output files."""

        if self.settings.get('FEED_ATOM'):
            writer.write_feed(self.articles, self.context,
                              self.settings['FEED_ATOM'])

        if self.settings.get('FEED_RSS'):
            writer.write_feed(self.articles, self.context,
                              self.settings['FEED_RSS'], feed_type='rss')

        if (self.settings.get('FEED_ALL_ATOM')
                or self.settings.get('FEED_ALL_RSS')):
            all_articles = list(self.articles)
            for article in self.articles:
                all_articles.extend(article.translations)
            all_articles.sort(key=attrgetter('date'), reverse=True)

            if self.settings.get('FEED_ALL_ATOM'):
                writer.write_feed(all_articles, self.context,
                                  self.settings['FEED_ALL_ATOM'])

            if self.settings.get('FEED_ALL_RSS'):
                writer.write_feed(all_articles, self.context,
                                  self.settings['FEED_ALL_RSS'],
                                  feed_type='rss')

        for cat, arts in self.categories:
            arts.sort(key=attrgetter('date'), reverse=True)
            if self.settings.get('CATEGORY_FEED_ATOM'):
                writer.write_feed(arts, self.context,
                                  self.settings['CATEGORY_FEED_ATOM']
                                  % cat.slug)

            if self.settings.get('CATEGORY_FEED_RSS'):
                writer.write_feed(arts, self.context,
                                  self.settings['CATEGORY_FEED_RSS']
                                  % cat.slug, feed_type='rss')

        for auth, arts in self.authors:
            arts.sort(key=attrgetter('date'), reverse=True)
            if self.settings.get('AUTHOR_FEED_ATOM'):
                writer.write_feed(arts, self.context,
                                  self.settings['AUTHOR_FEED_ATOM']
                                  % auth.slug)

            if self.settings.get('AUTHOR_FEED_RSS'):
                writer.write_feed(arts, self.context,
                                  self.settings['AUTHOR_FEED_RSS']
                                  % auth.slug, feed_type='rss')

        if (self.settings.get('TAG_FEED_ATOM')
                or self.settings.get('TAG_FEED_RSS')):
            for tag, arts in self.tags.items():
                arts.sort(key=attrgetter('date'), reverse=True)
                if self.settings.get('TAG_FEED_ATOM'):
                    writer.write_feed(arts, self.context,
                                      self.settings['TAG_FEED_ATOM']
                                      % tag.slug)

                if self.settings.get('TAG_FEED_RSS'):
                    writer.write_feed(arts, self.context,
                                      self.settings['TAG_FEED_RSS'] % tag.slug,
                                      feed_type='rss')

        if (self.settings.get('TRANSLATION_FEED_ATOM')
                or self.settings.get('TRANSLATION_FEED_RSS')):
            translations_feeds = defaultdict(list)
            for article in chain(self.articles, self.translations):
                translations_feeds[article.lang].append(article)

            for lang, items in translations_feeds.items():
                items.sort(key=attrgetter('date'), reverse=True)
                if self.settings.get('TRANSLATION_FEED_ATOM'):
                    writer.write_feed(
                        items, self.context,
                        self.settings['TRANSLATION_FEED_ATOM'] % lang)
                if self.settings.get('TRANSLATION_FEED_RSS'):
                    writer.write_feed(
                        items, self.context,
                        self.settings['TRANSLATION_FEED_RSS'] % lang,
                        feed_type='rss')

    def generate_articles(self, write):
        """Generate the articles."""
        for article in chain(self.translations, self.articles):
            signals.article_generator_write_article.send(self, content=article)
            write(article.save_as, self.get_template(article.template),
                  self.context, article=article, category=article.category,
                  override_output=hasattr(article, 'override_save_as'))

    def generate_period_archives(self, write):
        """Generate per-year, per-month, and per-day archives."""
        try:
            template = self.get_template('period_archives')
        except Exception:
            template = self.get_template('archives')

        period_save_as = {
            'year': self.settings['YEAR_ARCHIVE_SAVE_AS'],
            'month': self.settings['MONTH_ARCHIVE_SAVE_AS'],
            'day': self.settings['DAY_ARCHIVE_SAVE_AS'],
        }

        period_date_key = {
            'year': attrgetter('date.year'),
            'month': attrgetter('date.year', 'date.month'),
            'day': attrgetter('date.year', 'date.month', 'date.day')
        }

        def _generate_period_archives(dates, key, save_as_fmt):
            """Generate period archives from `dates`, grouped by
            `key` and written to `save_as`.
            """
            # `dates` is already sorted by date
            for _period, group in groupby(dates, key=key):
                archive = list(group)
                # arbitrarily grab the first date so that the usual
                # format string syntax can be used for specifying the
                # period archive dates
                date = archive[0].date
                # Under python 2, with non-ascii locales, u"{:%b}".format(date) might raise UnicodeDecodeError
                # because u"{:%b}".format(date) will call date.__format__(u"%b"), which will return a byte string
                # and not a unicode string.
                # eg:
                # locale.setlocale(locale.LC_ALL, 'ja_JP.utf8')
                # date.__format__(u"%b") == '12\xe6\x9c\x88' # True
                try:
                    save_as = save_as_fmt.format(date=date)
                except UnicodeDecodeError:
                    # Python2 only:
                    # Let date.__format__() work with byte strings instead of characters since it fails to work with characters
                    bytes_save_as_fmt = save_as_fmt.encode('utf8')
                    bytes_save_as     = bytes_save_as_fmt.format(date=date)
                    save_as           = unicode(bytes_save_as,'utf8')
                context = self.context.copy()

                if key == period_date_key['year']:
                    context["period"] = (_period,)
                elif key == period_date_key['month']:
                    context["period"] = (_period[0],
                                         calendar.month_name[_period[1]])
                else:
                    context["period"] = (_period[0],
                                         calendar.month_name[_period[1]],
                                         _period[2])

                write(save_as, template, context,
                      dates=archive, blog=True)

        for period in 'year', 'month', 'day':
            save_as = period_save_as[period]
            if save_as:
                key = period_date_key[period]
                _generate_period_archives(self.dates, key, save_as)

    def generate_direct_templates(self, write):
        """Generate direct templates pages"""
        PAGINATED_TEMPLATES = self.settings['PAGINATED_DIRECT_TEMPLATES']
        for template in self.settings['DIRECT_TEMPLATES']:
            paginated = {}
            if template in PAGINATED_TEMPLATES:
                paginated = {'articles': self.articles, 'dates': self.dates}
            save_as = self.settings.get("%s_SAVE_AS" % template.upper(),
                                        '%s.html' % template)
            if not save_as:
                continue

            write(save_as, self.get_template(template),
                  self.context, blog=True, paginated=paginated,
                  page_name=os.path.splitext(save_as)[0])

    def generate_tags(self, write):
        """Generate Tags pages."""
        tag_template = self.get_template('tag')
        for tag, articles in self.tags.items():
            articles.sort(key=attrgetter('date'), reverse=True)
            dates = [article for article in self.dates if article in articles]
            write(tag.save_as, tag_template, self.context, tag=tag,
                  articles=articles, dates=dates,
                  paginated={'articles': articles, 'dates': dates},
                  page_name=tag.page_name, all_articles=self.articles)

    def generate_categories(self, write):
        """Generate category pages."""
        category_template = self.get_template('category')
        for cat, articles in self.categories:
            articles.sort(key=attrgetter('date'), reverse=True)
            dates = [article for article in self.dates if article in articles]
            write(cat.save_as, category_template, self.context,
                  category=cat, articles=articles, dates=dates,
                  paginated={'articles': articles, 'dates': dates},
                  page_name=cat.page_name, all_articles=self.articles)

    def generate_authors(self, write):
        """Generate Author pages."""
        author_template = self.get_template('author')
        for aut, articles in self.authors:
            articles.sort(key=attrgetter('date'), reverse=True)
            dates = [article for article in self.dates if article in articles]
            write(aut.save_as, author_template, self.context,
                  author=aut, articles=articles, dates=dates,
                  paginated={'articles': articles, 'dates': dates},
                  page_name=aut.page_name, all_articles=self.articles)

    def generate_drafts(self, write):
        """Generate drafts pages."""
        for draft in chain(self.drafts_translations, self.drafts):
            write(draft.save_as, self.get_template(draft.template),
                self.context, article=draft, category=draft.category,
                override_output=hasattr(draft, 'override_save_as'),
                all_articles=self.articles)

    def generate_pages(self, writer):
        """Generate the pages on the disk"""
        write = partial(writer.write_file,
                        relative_urls=self.settings['RELATIVE_URLS'])

        # to minimize the number of relative path stuff modification
        # in writer, articles pass first
        self.generate_articles(write)
        self.generate_period_archives(write)
        self.generate_direct_templates(write)

        # and subfolders after that
        self.generate_tags(write)
        self.generate_categories(write)
        self.generate_authors(write)
        self.generate_drafts(write)

    def generate_context(self):
        """Add the articles into the shared context"""

        all_articles = []
        all_drafts = []
        for f in self.get_files(
                self.settings['ARTICLE_DIR'],
                exclude=self.settings['ARTICLE_EXCLUDES']):
            article = self.get_cached_data(f, None)
            if article is None:
                try:
                    article = self.readers.read_file(
                        base_path=self.path, path=f, content_class=Article,
                        context=self.context,
                        preread_signal=signals.article_generator_preread,
                        preread_sender=self,
                        context_signal=signals.article_generator_context,
                        context_sender=self)
                except Exception as e:
                    logger.warning('Could not process {}\n{}'.format(f, e))
                    continue

                if not is_valid_content(article, f):
                    continue

                self.cache_data(f, article)

            self.add_source_path(article)

            if article.status.lower() == "published":
                all_articles.append(article)
            elif article.status.lower() == "draft":
                draft = self.readers.read_file(
                    base_path=self.path, path=f, content_class=Draft,
                    context=self.context,
                    preread_signal=signals.article_generator_preread,
                    preread_sender=self,
                    context_signal=signals.article_generator_context,
                    context_sender=self)
                all_drafts.append(draft)
            else:
                logger.warning("Unknown status %s for file %s, skipping it." %
                               (repr(article.status),
                                repr(f)))

        self.articles, self.translations = process_translations(all_articles)
        self.drafts, self.drafts_translations = \
            process_translations(all_drafts)

        signals.article_generator_pretaxonomy.send(self)

        for article in self.articles:
            # only main articles are listed in categories and tags
            # not translations
            self.categories[article.category].append(article)
            if hasattr(article, 'tags'):
                for tag in article.tags:
                    self.tags[tag].append(article)
            # ignore blank authors as well as undefined
            for author in getattr(article, 'authors', []):
                if author.name != '':
                    self.authors[author].append(article)
        # sort the articles by date
        self.articles.sort(key=attrgetter('date'), reverse=True)
        self.dates = list(self.articles)
        self.dates.sort(key=attrgetter('date'),
                        reverse=self.context['NEWEST_FIRST_ARCHIVES'])

        # create tag cloud
        tag_cloud = defaultdict(int)
        for article in self.articles:
            for tag in getattr(article, 'tags', []):
                tag_cloud[tag] += 1

        tag_cloud = sorted(tag_cloud.items(), key=itemgetter(1), reverse=True)
        tag_cloud = tag_cloud[:self.settings.get('TAG_CLOUD_MAX_ITEMS')]

        tags = list(map(itemgetter(1), tag_cloud))
        if tags:
            max_count = max(tags)
        steps = self.settings.get('TAG_CLOUD_STEPS')

        # calculate word sizes
        self.tag_cloud = [
            (
                tag,
                int(math.floor(steps - (steps - 1) * math.log(count)
                    / (math.log(max_count)or 1)))
            )
            for tag, count in tag_cloud
        ]
        # put words in chaos
        random.shuffle(self.tag_cloud)

        # and generate the output :)

        # order the categories per name
        self.categories = list(self.categories.items())
        self.categories.sort(
            reverse=self.settings['REVERSE_CATEGORY_ORDER'])

        self.authors = list(self.authors.items())
        self.authors.sort()

        self._update_context(('articles', 'dates', 'tags', 'categories',
                              'tag_cloud', 'authors', 'related_posts'))
        self.save_cache()
        self.readers.save_cache()
        signals.article_generator_finalized.send(self)

    def generate_output(self, writer):
        self.generate_feeds(writer)
        self.generate_pages(writer)
        signals.article_writer_finalized.send(self, writer=writer)


class PagesGenerator(CachingGenerator):
    """Generate pages"""

    def __init__(self, *args, **kwargs):
        self.pages = []
        self.hidden_pages = []
        self.hidden_translations = []
        super(PagesGenerator, self).__init__(*args, **kwargs)
        signals.page_generator_init.send(self)

    def generate_context(self):
        all_pages = []
        hidden_pages = []
        for f in self.get_files(
                self.settings['PAGE_DIR'],
                exclude=self.settings['PAGE_EXCLUDES']):
            page = self.get_cached_data(f, None)
            if page is None:
                try:
                    page = self.readers.read_file(
                        base_path=self.path, path=f, content_class=Page,
                        context=self.context,
                        preread_signal=signals.page_generator_preread,
                        preread_sender=self,
                        context_signal=signals.page_generator_context,
                        context_sender=self)
                except Exception as e:
                    logger.warning('Could not process {}\n{}'.format(f, e))
                    continue

                if not is_valid_content(page, f):
                    continue

                self.cache_data(f, page)

            self.add_source_path(page)

            if page.status == "published":
                all_pages.append(page)
            elif page.status == "hidden":
                hidden_pages.append(page)
            else:
                logger.warning("Unknown status %s for file %s, skipping it." %
                               (repr(page.status),
                                repr(f)))

        self.pages, self.translations = process_translations(all_pages)
        self.hidden_pages, self.hidden_translations = (
            process_translations(hidden_pages))

        self._update_context(('pages', ))
        self.context['PAGES'] = self.pages

        self.save_cache()
        self.readers.save_cache()
        signals.page_generator_finalized.send(self)

    def generate_output(self, writer):
        for page in chain(self.translations, self.pages,
                          self.hidden_translations, self.hidden_pages):
            writer.write_file(
                page.save_as, self.get_template(page.template),
                self.context, page=page,
                relative_urls=self.settings['RELATIVE_URLS'],
                override_output=hasattr(page, 'override_save_as'))


class StaticGenerator(Generator):
    """copy static paths (what you want to copy, like images, medias etc.
    to output"""

    def __init__(self, *args, **kwargs):
        super(StaticGenerator, self).__init__(*args, **kwargs)
        signals.static_generator_init.send(self)

    def _copy_paths(self, paths, source, destination, output_path,
                    final_path=None):
        """Copy all the paths from source to destination"""
        for path in paths:
            if final_path:
                copy(os.path.join(source, path),
                     os.path.join(output_path, destination, final_path))
            else:
                copy(os.path.join(source, path),
                     os.path.join(output_path, destination, path))

    def generate_context(self):
        self.staticfiles = []

        # walk static paths
        for static_path in self.settings['STATIC_PATHS']:
            for f in self.get_files(
                    static_path, extensions=False):
                static = self.readers.read_file(
                    base_path=self.path, path=f, content_class=Static,
                    fmt='static', context=self.context,
                    preread_signal=signals.static_generator_preread,
                    preread_sender=self,
                    context_signal=signals.static_generator_context,
                    context_sender=self)
                self.staticfiles.append(static)
                self.add_source_path(static)
        self._update_context(('staticfiles',))
        signals.static_generator_finalized.send(self)

    def generate_output(self, writer):
        self._copy_paths(self.settings['THEME_STATIC_PATHS'], self.theme,
                         self.settings['THEME_STATIC_DIR'], self.output_path,
                         os.curdir)
        # copy all Static files
        for sc in self.context['staticfiles']:
            source_path = os.path.join(self.path, sc.source_path)
            save_as = os.path.join(self.output_path, sc.save_as)
            mkdir_p(os.path.dirname(save_as))
            shutil.copy2(source_path, save_as)
            logger.info('copying {} to {}'.format(sc.source_path, sc.save_as))


class SourceFileGenerator(Generator):

    def generate_context(self):
        self.output_extension = self.settings['OUTPUT_SOURCES_EXTENSION']

    def _create_source(self, obj):
        output_path, _ = os.path.splitext(obj.save_as)
        dest = os.path.join(self.output_path,
                            output_path + self.output_extension)
        copy(obj.source_path, dest)

    def generate_output(self, writer=None):
        logger.info(' Generating source files...')
        for obj in chain(self.context['articles'], self.context['pages']):
            self._create_source(obj)
            for obj_trans in obj.translations:
                self._create_source(obj_trans)

########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

__all__ = [
    'init'
]

import os
import sys
import logging

from collections import defaultdict


RESET_TERM = '\033[0;m'

COLOR_CODES = {
    'red': 31,
    'yellow': 33,
    'cyan': 36,
    'white': 37,
    'bgred': 41,
    'bggrey': 100,
}


def ansi(color, text):
    """Wrap text in an ansi escape sequence"""
    code = COLOR_CODES[color]
    return '\033[1;{0}m{1}{2}'.format(code, text, RESET_TERM)


class ANSIFormatter(logging.Formatter):
    """Convert a `logging.LogRecord' object into colored text, using ANSI
       escape sequences.

    """
    def format(self, record):
        msg = record.getMessage()
        if record.levelname == 'INFO':
            return ansi('cyan', '-> ') + msg
        elif record.levelname == 'WARNING':
            return ansi('yellow', record.levelname) + ': ' + msg
        elif record.levelname == 'ERROR':
            return ansi('red', record.levelname) + ': ' + msg
        elif record.levelname == 'CRITICAL':
            return ansi('bgred', record.levelname) + ': ' + msg
        elif record.levelname == 'DEBUG':
            return ansi('bggrey', record.levelname) + ': ' + msg
        else:
            return ansi('white', record.levelname) + ': ' + msg


class TextFormatter(logging.Formatter):
    """
    Convert a `logging.LogRecord' object into text.
    """

    def format(self, record):
        if not record.levelname or record.levelname == 'INFO':
            return record.getMessage()
        else:
            return record.levelname + ': ' + record.getMessage()


class LimitFilter(logging.Filter):
    """
    Remove duplicates records, and limit the number of records in the same
    group.

    Groups are specified by the message to use when the number of records in
    the same group hit the limit.
    E.g.: log.warning(('43 is not the answer', 'More erroneous answers'))
    """

    ignore = set()
    threshold = 5
    group_count = defaultdict(int)

    def filter(self, record):
        # don't limit log messages for anything above "warning"
        if record.levelno > logging.WARN:
            return record
        # extract group
        group = None
        if len(record.msg) == 2:
            record.msg, group = record.msg
        # ignore record if it was already raised
        # use .getMessage() and not .msg for string formatting
        ignore_key = (record.levelno, record.getMessage())
        to_ignore = ignore_key in LimitFilter.ignore
        LimitFilter.ignore.add(ignore_key)
        if to_ignore:
            return False
        # check if we went over threshold
        if group:
            key = (record.levelno, group)
            LimitFilter.group_count[key] += 1
            if LimitFilter.group_count[key] == LimitFilter.threshold:
                record.msg = group
            if LimitFilter.group_count[key] > LimitFilter.threshold:
                return False
        return record


class LimitLogger(logging.Logger):
    """
    A logger which adds LimitFilter automatically
    """

    limit_filter = LimitFilter()

    def __init__(self, *args, **kwargs):
        super(LimitLogger, self).__init__(*args, **kwargs)
        self.addFilter(LimitLogger.limit_filter)

logging.setLoggerClass(LimitLogger)


def init(level=None, handler=logging.StreamHandler()):

    logger = logging.getLogger()

    if (os.isatty(sys.stdout.fileno())
            and not sys.platform.startswith('win')):
        fmt = ANSIFormatter()
    else:
        fmt = TextFormatter()
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    if level:
        logger.setLevel(level)


if __name__ == '__main__':
    init(level=logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.debug('debug')
    root_logger.info('info')
    root_logger.warning('warning')
    root_logger.error('error')
    root_logger.critical('critical')

########NEW FILE########
__FILENAME__ = paginator
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import six

# From django.core.paginator
from collections import namedtuple
import functools
import logging
import os

from math import ceil

logger = logging.getLogger(__name__)


PaginationRule = namedtuple(
    'PaginationRule',
    'min_page URL SAVE_AS',
)


class Paginator(object):
    def __init__(self, name, object_list, settings):
        self.name = name
        self.object_list = object_list
        self.settings = settings

        if settings.get('DEFAULT_PAGINATION'):
            self.per_page = settings.get('DEFAULT_PAGINATION')
            self.orphans = settings.get('DEFAULT_ORPHANS')
        else:
            self.per_page = len(object_list)
            self.orphans = 0

        self._num_pages = self._count = None

    def page(self, number):
        "Returns a Page object for the given 1-based page number."
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top + self.orphans >= self.count:
            top = self.count
        return Page(self.name, self.object_list[bottom:top], number, self,
                    self.settings)

    def _get_count(self):
        "Returns the total number of objects, across all pages."
        if self._count is None:
            self._count = len(self.object_list)
        return self._count
    count = property(_get_count)

    def _get_num_pages(self):
        "Returns the total number of pages."
        if self._num_pages is None:
            hits = max(1, self.count - self.orphans)
            self._num_pages = int(ceil(hits / (float(self.per_page) or 1)))
        return self._num_pages
    num_pages = property(_get_num_pages)

    def _get_page_range(self):
        """
        Returns a 1-based range of pages for iterating through within
        a template for loop.
        """
        return list(range(1, self.num_pages + 1))
    page_range = property(_get_page_range)


class Page(object):
    def __init__(self, name, object_list, number, paginator, settings):
        self.name, self.extension = os.path.splitext(name)
        self.object_list = object_list
        self.number = number
        self.paginator = paginator
        self.settings = settings

    def __repr__(self):
        return '<Page %s of %s>' % (self.number, self.paginator.num_pages)

    def has_next(self):
        return self.number < self.paginator.num_pages

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    def next_page_number(self):
        return self.number + 1

    def previous_page_number(self):
        return self.number - 1

    def start_index(self):
        """
        Returns the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        # Special case, return zero if no items.
        if self.paginator.count == 0:
            return 0
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self):
        """
        Returns the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        # Special case for the last page because there can be orphans.
        if self.number == self.paginator.num_pages:
            return self.paginator.count
        return self.number * self.paginator.per_page

    def _from_settings(self, key):
        """Returns URL information as defined in settings. Similar to
        URLWrapper._from_settings, but specialized to deal with pagination
        logic."""

        rule = None

        # find the last matching pagination rule
        for p in self.settings['PAGINATION_PATTERNS']:
            if p.min_page <= self.number:
                rule = p

        if not rule:
            return ''

        prop_value = getattr(rule, key)

        if not isinstance(prop_value, six.string_types):
            logger.warning('%s is set to %s' % (key, prop_value))
            return prop_value

        # URL or SAVE_AS is a string, format it with a controlled context
        context = {
            'name': self.name,
            'object_list': self.object_list,
            'number': self.number,
            'paginator': self.paginator,
            'settings': self.settings,
            'base_name': os.path.dirname(self.name),
            'number_sep': '/',
            'extension':  self.extension,
        }

        if self.number == 1:
            # no page numbers on the first page
            context['number'] = ''
            context['number_sep'] = ''

        ret = prop_value.format(**context)
        if ret[0] == '/':
            ret = ret[1:]
        return ret

    url = property(functools.partial(_from_settings, key='URL'))
    save_as = property(functools.partial(_from_settings, key='SAVE_AS'))

########NEW FILE########
__FILENAME__ = readers
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import datetime
import logging
import os
import re

import docutils
import docutils.core
import docutils.io
from docutils.writers.html4css1 import HTMLTranslator

# import the directives to have pygments support
from pelican import rstdirectives  # NOQA
try:
    from markdown import Markdown
except ImportError:
    Markdown = False  # NOQA
try:
    from asciidocapi import AsciiDocAPI
    asciidoc = True
except ImportError:
    asciidoc = False
try:
    from html import escape
except ImportError:
    from cgi import escape
try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

from pelican import signals
from pelican.contents import Page, Category, Tag, Author
from pelican.utils import get_date, pelican_open, FileStampDataCacher


METADATA_PROCESSORS = {
    'tags': lambda x, y: [Tag(tag, y) for tag in x.split(',')],
    'date': lambda x, y: get_date(x),
    'modified': lambda x, y: get_date(x),
    'status': lambda x, y: x.strip(),
    'category': Category,
    'author': Author,
    'authors': lambda x, y: [Author(author.strip(), y) for author in x.split(',')],
}

logger = logging.getLogger(__name__)


class BaseReader(object):
    """Base class to read files.

    This class is used to process static files, and it can be inherited for
    other types of file. A Reader class must have the following attributes:

    - enabled: (boolean) tell if the Reader class is enabled. It
      generally depends on the import of some dependency.
    - file_extensions: a list of file extensions that the Reader will process.
    - extensions: a list of extensions to use in the reader (typical use is
      Markdown).

    """
    enabled = True
    file_extensions = ['static']
    extensions = None

    def __init__(self, settings):
        self.settings = settings

    def process_metadata(self, name, value):
        if name in METADATA_PROCESSORS:
            return METADATA_PROCESSORS[name](value, self.settings)
        return value

    def read(self, source_path):
        "No-op parser"
        content = None
        metadata = {}
        return content, metadata


class _FieldBodyTranslator(HTMLTranslator):

    def __init__(self, document):
        HTMLTranslator.__init__(self, document)
        self.compact_p = None

    def astext(self):
        return ''.join(self.body)

    def visit_field_body(self, node):
        pass

    def depart_field_body(self, node):
        pass


def render_node_to_html(document, node):
    visitor = _FieldBodyTranslator(document)
    node.walkabout(visitor)
    return visitor.astext()


class PelicanHTMLTranslator(HTMLTranslator):

    def visit_abbreviation(self, node):
        attrs = {}
        if node.hasattr('explanation'):
            attrs['title'] = node['explanation']
        self.body.append(self.starttag(node, 'abbr', '', **attrs))

    def depart_abbreviation(self, node):
        self.body.append('</abbr>')

    def visit_image(self, node):
        # set an empty alt if alt is not specified
        # avoids that alt is taken from src
        node['alt'] = node.get('alt', '')
        return HTMLTranslator.visit_image(self, node)


class RstReader(BaseReader):
    """Reader for reStructuredText files"""

    enabled = bool(docutils)
    file_extensions = ['rst']

    def __init__(self, *args, **kwargs):
        super(RstReader, self).__init__(*args, **kwargs)

    def _parse_metadata(self, document):
        """Return the dict containing document metadata"""
        output = {}
        for docinfo in document.traverse(docutils.nodes.docinfo):
            for element in docinfo.children:
                if element.tagname == 'field':  # custom fields (e.g. summary)
                    name_elem, body_elem = element.children
                    name = name_elem.astext()
                    if name == 'summary':
                        value = render_node_to_html(document, body_elem)
                    else:
                        value = body_elem.astext()
                elif element.tagname == 'authors':  # author list
                    name = element.tagname
                    value = [element.astext() for element in element.children]
                    value = ','.join(value) # METADATA_PROCESSORS expects a string
                else:  # standard fields (e.g. address)
                    name = element.tagname
                    value = element.astext()
                name = name.lower()

                output[name] = self.process_metadata(name, value)
        return output

    def _get_publisher(self, source_path):
        extra_params = {'initial_header_level': '2',
                        'syntax_highlight': 'short',
                        'input_encoding': 'utf-8',
                        'exit_status_level': 2}
        user_params = self.settings.get('DOCUTILS_SETTINGS')
        if user_params:
            extra_params.update(user_params)

        pub = docutils.core.Publisher(
            destination_class=docutils.io.StringOutput)
        pub.set_components('standalone', 'restructuredtext', 'html')
        pub.writer.translator_class = PelicanHTMLTranslator
        pub.process_programmatic_settings(None, extra_params, None)
        pub.set_source(source_path=source_path)
        pub.publish(enable_exit_status=True)
        return pub

    def read(self, source_path):
        """Parses restructured text"""
        pub = self._get_publisher(source_path)
        parts = pub.writer.parts
        content = parts.get('body')

        metadata = self._parse_metadata(pub.document)
        metadata.setdefault('title', parts.get('title'))

        return content, metadata


class MarkdownReader(BaseReader):
    """Reader for Markdown files"""

    enabled = bool(Markdown)
    file_extensions = ['md', 'markdown', 'mkd', 'mdown']

    def __init__(self, *args, **kwargs):
        super(MarkdownReader, self).__init__(*args, **kwargs)
        self.extensions = list(self.settings['MD_EXTENSIONS'])
        if 'meta' not in self.extensions:
            self.extensions.append('meta')

    def _parse_metadata(self, meta):
        """Return the dict containing document metadata"""
        output = {}
        for name, value in meta.items():
            name = name.lower()
            if name == "summary":
                # handle summary metadata as markdown
                # summary metadata is special case and join all list values
                summary_values = "\n".join(value)
                # reset the markdown instance to clear any state
                self._md.reset()
                summary = self._md.convert(summary_values)
                output[name] = self.process_metadata(name, summary)
            elif len(value) > 1:
                # handle list metadata as list of string
                output[name] = self.process_metadata(name, value)
            else:
                # otherwise, handle metadata as single string
                output[name] = self.process_metadata(name, value[0])
        return output

    def read(self, source_path):
        """Parse content and metadata of markdown files"""

        self._md = Markdown(extensions=self.extensions)
        with pelican_open(source_path) as text:
            content = self._md.convert(text)

        metadata = self._parse_metadata(self._md.Meta)
        return content, metadata


class HTMLReader(BaseReader):
    """Parses HTML files as input, looking for meta, title, and body tags"""

    file_extensions = ['htm', 'html']
    enabled = True

    class _HTMLParser(HTMLParser):
        def __init__(self, settings, filename):
            HTMLParser.__init__(self)
            self.body = ''
            self.metadata = {}
            self.settings = settings

            self._data_buffer = ''

            self._filename = filename

            self._in_top_level = True
            self._in_head = False
            self._in_title = False
            self._in_body = False
            self._in_tags = False

        def handle_starttag(self, tag, attrs):
            if tag == 'head' and self._in_top_level:
                self._in_top_level = False
                self._in_head = True
            elif tag == 'title' and self._in_head:
                self._in_title = True
                self._data_buffer = ''
            elif tag == 'body' and self._in_top_level:
                self._in_top_level = False
                self._in_body = True
                self._data_buffer = ''
            elif tag == 'meta' and self._in_head:
                self._handle_meta_tag(attrs)

            elif self._in_body:
                self._data_buffer += self.build_tag(tag, attrs, False)

        def handle_endtag(self, tag):
            if tag == 'head':
                if self._in_head:
                    self._in_head = False
                    self._in_top_level = True
            elif tag == 'title':
                self._in_title = False
                self.metadata['title'] = self._data_buffer
            elif tag == 'body':
                self.body = self._data_buffer
                self._in_body = False
                self._in_top_level = True
            elif self._in_body:
                self._data_buffer += '</{}>'.format(escape(tag))

        def handle_startendtag(self, tag, attrs):
            if tag == 'meta' and self._in_head:
                self._handle_meta_tag(attrs)
            if self._in_body:
                self._data_buffer += self.build_tag(tag, attrs, True)

        def handle_comment(self, data):
            self._data_buffer += '<!--{}-->'.format(data)

        def handle_data(self, data):
            self._data_buffer += data

        def handle_entityref(self, data):
            self._data_buffer += '&{};'.format(data)

        def handle_charref(self, data):
            self._data_buffer += '&#{};'.format(data)

        def build_tag(self, tag, attrs, close_tag):
            result = '<{}'.format(escape(tag))
            for k, v in attrs:
                result += ' ' + escape(k)
                if v is not None:
                    result += '="{}"'.format(escape(v))
            if close_tag:
                return result + ' />'
            return result + '>'

        def _handle_meta_tag(self, attrs):
            name = self._attr_value(attrs, 'name')
            if name is None:
                attr_serialized = ', '.join(['{}="{}"'.format(k, v) for k, v in attrs])
                logger.warning("Meta tag in file %s does not have a 'name' attribute, skipping. Attributes: %s", self._filename, attr_serialized)
                return
            name = name.lower()
            contents = self._attr_value(attrs, 'content', '')
            if not contents:
                contents = self._attr_value(attrs, 'contents', '')
                if contents:
                    logger.warning((
                        "Meta tag attribute 'contents' used in file {}, should"
                        " be changed to 'content'".format(self._filename),
                        "Other files have meta tag attribute 'contents' that"
                        " should be changed to 'content'"))

            if name == 'keywords':
                name = 'tags'
            self.metadata[name] = contents

        @classmethod
        def _attr_value(cls, attrs, name, default=None):
            return next((x[1] for x in attrs if x[0] == name), default)

    def read(self, filename):
        """Parse content and metadata of HTML files"""
        with pelican_open(filename) as content:
            parser = self._HTMLParser(self.settings, filename)
            parser.feed(content)
            parser.close()

        metadata = {}
        for k in parser.metadata:
            metadata[k] = self.process_metadata(k, parser.metadata[k])
        return parser.body, metadata


class AsciiDocReader(BaseReader):
    """Reader for AsciiDoc files"""

    enabled = bool(asciidoc)
    file_extensions = ['asc', 'adoc', 'asciidoc']
    default_options = ["--no-header-footer", "-a newline=\\n"]

    def read(self, source_path):
        """Parse content and metadata of asciidoc files"""
        from cStringIO import StringIO
        with pelican_open(source_path) as source:
            text = StringIO(source)
        content = StringIO()
        ad = AsciiDocAPI()

        options = self.settings['ASCIIDOC_OPTIONS']
        if isinstance(options, (str, unicode)):
            options = [m.strip() for m in options.split(',')]
        options = self.default_options + options
        for o in options:
            ad.options(*o.split())

        ad.execute(text, content, backend="html4")
        content = content.getvalue()

        metadata = {}
        for name, value in ad.asciidoc.document.attributes.items():
            name = name.lower()
            metadata[name] = self.process_metadata(name, value)
        if 'doctitle' in metadata:
            metadata['title'] = metadata['doctitle']
        return content, metadata


class Readers(FileStampDataCacher):
    """Interface for all readers.

    This class contains a mapping of file extensions / Reader classes, to know
    which Reader class must be used to read a file (based on its extension).
    This is customizable both with the 'READERS' setting, and with the
    'readers_init' signall for plugins.

    """

    def __init__(self, settings=None, cache_name=''):
        self.settings = settings or {}
        self.readers = {}
        self.reader_classes = {}

        for cls in [BaseReader] + BaseReader.__subclasses__():
            if not cls.enabled:
                logger.debug('Missing dependencies for {}'
                             .format(', '.join(cls.file_extensions)))
                continue

            for ext in cls.file_extensions:
                self.reader_classes[ext] = cls

        if self.settings['READERS']:
            self.reader_classes.update(self.settings['READERS'])

        signals.readers_init.send(self)

        for fmt, reader_class in self.reader_classes.items():
            if not reader_class:
                continue

            self.readers[fmt] = reader_class(self.settings)

        # set up caching
        cache_this_level = (cache_name != '' and
                            self.settings['CONTENT_CACHING_LAYER'] == 'reader')
        caching_policy = cache_this_level and self.settings['CACHE_CONTENT']
        load_policy = cache_this_level and self.settings['LOAD_CONTENT_CACHE']
        super(Readers, self).__init__(settings, cache_name,
                                      caching_policy, load_policy,
                                      )

    @property
    def extensions(self):
        return self.readers.keys()

    def read_file(self, base_path, path, content_class=Page, fmt=None,
                  context=None, preread_signal=None, preread_sender=None,
                  context_signal=None, context_sender=None):
        """Return a content object parsed with the given format."""

        path = os.path.abspath(os.path.join(base_path, path))
        source_path = os.path.relpath(path, base_path)
        logger.debug('read file {} -> {}'.format(
            source_path, content_class.__name__))

        if not fmt:
            _, ext = os.path.splitext(os.path.basename(path))
            fmt = ext[1:]

        if fmt not in self.readers:
            raise TypeError(
                'Pelican does not know how to parse {}'.format(path))

        if preread_signal:
            logger.debug('signal {}.send({})'.format(
                preread_signal, preread_sender))
            preread_signal.send(preread_sender)

        reader = self.readers[fmt]

        metadata = default_metadata(
            settings=self.settings, process=reader.process_metadata)
        metadata.update(path_metadata(
            full_path=path, source_path=source_path,
            settings=self.settings))
        metadata.update(parse_path_metadata(
            source_path=source_path, settings=self.settings,
            process=reader.process_metadata))

        content, reader_metadata = self.get_cached_data(path, (None, None))
        if content is None:
            content, reader_metadata = reader.read(path)
            self.cache_data(path, (content, reader_metadata))
        metadata.update(reader_metadata)

        if content:
            # find images with empty alt
            find_empty_alt(content, path)

        # eventually filter the content with typogrify if asked so
        if self.settings['TYPOGRIFY']:
            from typogrify.filters import typogrify
            if content:
                content = typogrify(content)
                metadata['title'] = typogrify(metadata['title'])
            if 'summary' in metadata:
                metadata['summary'] = typogrify(metadata['summary'])

        if context_signal:
            logger.debug('signal {}.send({}, <metadata>)'.format(
                context_signal, context_sender))
            context_signal.send(context_sender, metadata=metadata)

        return content_class(content=content, metadata=metadata,
                             settings=self.settings, source_path=path,
                             context=context)


def find_empty_alt(content, path):
    """Find images with empty alt

    Create warnings for all images with empty alt (up to a certain number),
    as they are really likely to be accessibility flaws.

    """
    imgs = re.compile(r"""
        (?:
            # src before alt
            <img
            [^\>]*
            src=(['"])(.*)\1
            [^\>]*
            alt=(['"])\3
        )|(?:
            # alt before src
            <img
            [^\>]*
            alt=(['"])\4
            [^\>]*
            src=(['"])(.*)\5
        )
        """, re.X)
    for match in re.findall(imgs, content):
        logger.warning(('Empty alt attribute for image {} in {}'.format(
            os.path.basename(match[1] + match[5]), path),
            'Other images have empty alt attributes'))


def default_metadata(settings=None, process=None):
    metadata = {}
    if settings:
        if 'DEFAULT_CATEGORY' in settings:
            value = settings['DEFAULT_CATEGORY']
            if process:
                value = process('category', value)
            metadata['category'] = value
        if settings.get('DEFAULT_DATE', None) and settings['DEFAULT_DATE'] != 'fs':
            metadata['date'] = datetime.datetime(*settings['DEFAULT_DATE'])
    return metadata


def path_metadata(full_path, source_path, settings=None):
    metadata = {}
    if settings:
        if settings.get('DEFAULT_DATE', None) == 'fs':
            metadata['date'] = datetime.datetime.fromtimestamp(
                os.stat(full_path).st_ctime)
        metadata.update(settings.get('EXTRA_PATH_METADATA', {}).get(
            source_path, {}))
    return metadata


def parse_path_metadata(source_path, settings=None, process=None):
    """Extract a metadata dictionary from a file's path

    >>> import pprint
    >>> settings = {
    ...     'FILENAME_METADATA': '(?P<slug>[^.]*).*',
    ...     'PATH_METADATA':
    ...         '(?P<category>[^/]*)/(?P<date>\d{4}-\d{2}-\d{2})/.*',
    ...     }
    >>> reader = BaseReader(settings=settings)
    >>> metadata = parse_path_metadata(
    ...     source_path='my-cat/2013-01-01/my-slug.html',
    ...     settings=settings,
    ...     process=reader.process_metadata)
    >>> pprint.pprint(metadata)  # doctest: +ELLIPSIS
    {'category': <pelican.urlwrappers.Category object at ...>,
     'date': datetime.datetime(2013, 1, 1, 0, 0),
     'slug': 'my-slug'}
    """
    metadata = {}
    dirname, basename = os.path.split(source_path)
    base, ext = os.path.splitext(basename)
    subdir = os.path.basename(dirname)
    if settings:
        checks = []
        for key, data in [('FILENAME_METADATA', base),
                          ('PATH_METADATA', source_path)]:
            checks.append((settings.get(key, None), data))
        if settings.get('USE_FOLDER_AS_CATEGORY', None):
            checks.insert(0, ('(?P<category>.*)', subdir))
        for regexp, data in checks:
            if regexp and data:
                match = re.match(regexp, data)
                if match:
                    # .items() for py3k compat.
                    for k, v in match.groupdict().items():
                        if k not in metadata:
                            k = k.lower()  # metadata must be lowercase
                            if process:
                                v = process(k, v)
                            metadata[k] = v
    return metadata

########NEW FILE########
__FILENAME__ = rstdirectives
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from docutils import nodes, utils
from docutils.parsers.rst import directives, roles, Directive
from pygments.formatters import HtmlFormatter
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
import re
import six
import pelican.settings as pys


class Pygments(Directive):
    """ Source code syntax highlighting.
    """
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'anchorlinenos': directives.flag,
        'classprefix': directives.unchanged,
        'hl_lines': directives.unchanged,
        'lineanchors': directives.unchanged,
        'linenos': directives.unchanged,
        'linenospecial': directives.nonnegative_int,
        'linenostart': directives.nonnegative_int,
        'linenostep': directives.nonnegative_int,
        'lineseparator': directives.unchanged,
        'linespans': directives.unchanged,
        'nobackground': directives.flag,
        'nowrap': directives.flag,
        'tagsfile': directives.unchanged,
        'tagurlformat': directives.unchanged,
    }
    has_content = True

    def run(self):
        self.assert_has_content()
        try:
            lexer = get_lexer_by_name(self.arguments[0])
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()

        # Fetch the defaults
        if pys.PYGMENTS_RST_OPTIONS is not None:
            for k, v in six.iteritems(pys.PYGMENTS_RST_OPTIONS):
                # Locally set options overrides the defaults
                if k not in self.options:
                    self.options[k] = v

        if ('linenos' in self.options and
                self.options['linenos'] not in ('table', 'inline')):
            if self.options['linenos'] == 'none':
                self.options.pop('linenos')
            else:
                self.options['linenos'] = 'table'

        for flag in ('nowrap', 'nobackground', 'anchorlinenos'):
            if flag in self.options:
                self.options[flag] = True

        # noclasses should already default to False, but just in case...
        formatter = HtmlFormatter(noclasses=False, **self.options)
        parsed = highlight('\n'.join(self.content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]

directives.register_directive('code-block', Pygments)
directives.register_directive('sourcecode', Pygments)


_abbr_re = re.compile('\((.*)\)$')


class abbreviation(nodes.Inline, nodes.TextElement):
    pass


def abbr_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    m = _abbr_re.search(text)
    if m is None:
        return [abbreviation(text, text)], []
    abbr = text[:m.start()].strip()
    expl = m.group(1)
    return [abbreviation(abbr, abbr, explanation=expl)], []

roles.register_local_role('abbr', abbr_role)

########NEW FILE########
__FILENAME__ = server
from __future__ import print_function
import os
import sys
import logging
try:
    import SimpleHTTPServer as srvmod
except ImportError:
    import http.server as srvmod  # NOQA

try:
    import SocketServer as socketserver
except ImportError:
    import socketserver  # NOQA

PORT = len(sys.argv) == 2 and int(sys.argv[1]) or 8000
SUFFIXES = ['', '.html', '/index.html']


class ComplexHTTPRequestHandler(srvmod.SimpleHTTPRequestHandler):
    def do_GET(self):
        # we are trying to detect the file by having a fallback mechanism
        found = False
        for suffix in SUFFIXES:
            if not hasattr(self,'original_path'):
                self.original_path = self.path
            self.path = self.original_path + suffix
            path = self.translate_path(self.path)
            if os.path.exists(path):
                srvmod.SimpleHTTPRequestHandler.do_GET(self)
                logging.info("Found: %s" % self.path)
                found = True
                break
            logging.info("Tried to find file %s, but it doesn't exist. " % self.path)
        if not found:
            logging.warning("Unable to find file %s or variations." % self.path)

Handler = ComplexHTTPRequestHandler

socketserver.TCPServer.allow_reuse_address = True
try:
    httpd = socketserver.TCPServer(("", PORT), Handler)
except OSError as e:
    logging.error("Could not listen on port %s" % PORT)
    sys.exit(getattr(e, 'exitcode', 1))


logging.info("serving at port %s" % PORT)
try:
    httpd.serve_forever()
except KeyboardInterrupt as e:
    logging.info("shutting down server")
    httpd.socket.close()

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import six

import copy
import inspect
import os
import locale
import logging

try:
    # SourceFileLoader is the recommended way in 3.3+
    from importlib.machinery import SourceFileLoader
    load_source = lambda name, path: SourceFileLoader(name, path).load_module()
except ImportError:
    # but it does not exist in 3.2-, so fall back to imp
    import imp
    load_source = imp.load_source

from os.path import isabs

from pelican.log import LimitFilter


logger = logging.getLogger(__name__)


DEFAULT_THEME = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'themes', 'notmyidea')
DEFAULT_CONFIG = {
    'PATH': os.curdir,
    'ARTICLE_DIR': '',
    'ARTICLE_EXCLUDES': ('pages',),
    'PAGE_DIR': 'pages',
    'PAGE_EXCLUDES': (),
    'THEME': DEFAULT_THEME,
    'OUTPUT_PATH': 'output',
    'READERS': {},
    'STATIC_PATHS': ['images', ],
    'THEME_STATIC_DIR': 'theme',
    'THEME_STATIC_PATHS': ['static', ],
    'FEED_ALL_ATOM': os.path.join('feeds', 'all.atom.xml'),
    'CATEGORY_FEED_ATOM': os.path.join('feeds', '%s.atom.xml'),
    'AUTHOR_FEED_ATOM': os.path.join('feeds', '%s.atom.xml'),
    'AUTHOR_FEED_RSS': os.path.join('feeds', '%s.rss.xml'),
    'TRANSLATION_FEED_ATOM': os.path.join('feeds', 'all-%s.atom.xml'),
    'FEED_MAX_ITEMS': '',
    'SITEURL': '',
    'SITENAME': 'A Pelican Blog',
    'DISPLAY_PAGES_ON_MENU': True,
    'DISPLAY_CATEGORIES_ON_MENU': True,
    'OUTPUT_SOURCES': False,
    'OUTPUT_SOURCES_EXTENSION': '.text',
    'USE_FOLDER_AS_CATEGORY': True,
    'DEFAULT_CATEGORY': 'misc',
    'WITH_FUTURE_DATES': True,
    'CSS_FILE': 'main.css',
    'NEWEST_FIRST_ARCHIVES': True,
    'REVERSE_CATEGORY_ORDER': False,
    'DELETE_OUTPUT_DIRECTORY': False,
    'OUTPUT_RETENTION': (),
    'ARTICLE_URL': '{slug}.html',
    'ARTICLE_SAVE_AS': '{slug}.html',
    'ARTICLE_LANG_URL': '{slug}-{lang}.html',
    'ARTICLE_LANG_SAVE_AS': '{slug}-{lang}.html',
    'DRAFT_URL': 'drafts/{slug}.html',
    'DRAFT_SAVE_AS': os.path.join('drafts', '{slug}.html'),
    'DRAFT_LANG_URL': 'drafts/{slug}-{lang}.html',
    'DRAFT_LANG_SAVE_AS': os.path.join('drafts', '{slug}-{lang}.html'),
    'PAGE_URL': 'pages/{slug}.html',
    'PAGE_SAVE_AS': os.path.join('pages', '{slug}.html'),
    'PAGE_LANG_URL': 'pages/{slug}-{lang}.html',
    'PAGE_LANG_SAVE_AS': os.path.join('pages', '{slug}-{lang}.html'),
    'STATIC_URL': '{path}',
    'STATIC_SAVE_AS': '{path}',
    'PDF_GENERATOR': False,
    'PDF_STYLE_PATH': '',
    'PDF_STYLE': 'twelvepoint',
    'CATEGORY_URL': 'category/{slug}.html',
    'CATEGORY_SAVE_AS': os.path.join('category', '{slug}.html'),
    'TAG_URL': 'tag/{slug}.html',
    'TAG_SAVE_AS': os.path.join('tag', '{slug}.html'),
    'AUTHOR_URL': 'author/{slug}.html',
    'AUTHOR_SAVE_AS': os.path.join('author', '{slug}.html'),
    'PAGINATION_PATTERNS': [
        (0, '{name}{number}{extension}', '{name}{number}{extension}'),
    ],
    'YEAR_ARCHIVE_SAVE_AS': '',
    'MONTH_ARCHIVE_SAVE_AS': '',
    'DAY_ARCHIVE_SAVE_AS': '',
    'RELATIVE_URLS': False,
    'DEFAULT_LANG': 'en',
    'TAG_CLOUD_STEPS': 4,
    'TAG_CLOUD_MAX_ITEMS': 100,
    'DIRECT_TEMPLATES': ('index', 'tags', 'categories', 'authors', 'archives'),
    'EXTRA_TEMPLATES_PATHS': [],
    'PAGINATED_DIRECT_TEMPLATES': ('index', ),
    'PELICAN_CLASS': 'pelican.Pelican',
    'DEFAULT_DATE_FORMAT': '%a %d %B %Y',
    'DATE_FORMATS': {},
    'ASCIIDOC_OPTIONS': [],
    'MD_EXTENSIONS': ['codehilite(css_class=highlight)', 'extra'],
    'JINJA_EXTENSIONS': [],
    'JINJA_FILTERS': {},
    'LOG_FILTER': [],
    'LOCALE': [''],  # defaults to user locale
    'DEFAULT_PAGINATION': False,
    'DEFAULT_ORPHANS': 0,
    'DEFAULT_METADATA': (),
    'FILENAME_METADATA': '(?P<date>\d{4}-\d{2}-\d{2}).*',
    'PATH_METADATA': '',
    'EXTRA_PATH_METADATA': {},
    'DEFAULT_STATUS': 'published',
    'ARTICLE_PERMALINK_STRUCTURE': '',
    'TYPOGRIFY': False,
    'SUMMARY_MAX_LENGTH': 50,
    'PLUGIN_PATH': [],
    'PLUGINS': [],
    'PYGMENTS_RST_OPTIONS': {},
    'TEMPLATE_PAGES': {},
    'IGNORE_FILES': ['.#*'],
    'SLUG_SUBSTITUTIONS': (),
    'INTRASITE_LINK_REGEX': '[{|](?P<what>.*?)[|}]',
    'SLUGIFY_SOURCE': 'title',
    'CACHE_CONTENT': True,
    'CONTENT_CACHING_LAYER': 'reader',
    'CACHE_PATH': 'cache',
    'GZIP_CACHE': True,
    'CHECK_MODIFIED_METHOD': 'mtime',
    'LOAD_CONTENT_CACHE': True,
    'AUTORELOAD_IGNORE_CACHE': False,
    'WRITE_SELECTED': [],
    }

PYGMENTS_RST_OPTIONS = None


def read_settings(path=None, override=None):
    if path:
        local_settings = get_settings_from_file(path)
        # Make the paths relative to the settings file
        for p in ['PATH', 'OUTPUT_PATH', 'THEME', 'CACHE_PATH']:
            if p in local_settings and local_settings[p] is not None \
                    and not isabs(local_settings[p]):
                absp = os.path.abspath(os.path.normpath(os.path.join(
                    os.path.dirname(path), local_settings[p])))
                if p not in ('THEME') or os.path.exists(absp):
                    local_settings[p] = absp

        if isinstance(local_settings['PLUGIN_PATH'], six.string_types):
            logger.warning("Defining %s setting as string has been deprecated (should be a list)" % 'PLUGIN_PATH')
            local_settings['PLUGIN_PATH'] = [local_settings['PLUGIN_PATH']]
        else:
            if 'PLUGIN_PATH' in local_settings and local_settings['PLUGIN_PATH'] is not None:
                local_settings['PLUGIN_PATH'] = [os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(path), pluginpath)))
                                    if not isabs(pluginpath) else pluginpath for pluginpath in local_settings['PLUGIN_PATH']]
    else:
        local_settings = copy.deepcopy(DEFAULT_CONFIG)

    if override:
        local_settings.update(override)

    parsed_settings = configure_settings(local_settings)
    # This is because there doesn't seem to be a way to pass extra
    # parameters to docutils directive handlers, so we have to have a
    # variable here that we'll import from within Pygments.run (see
    # rstdirectives.py) to see what the user defaults were.
    global PYGMENTS_RST_OPTIONS
    PYGMENTS_RST_OPTIONS = parsed_settings.get('PYGMENTS_RST_OPTIONS', None)
    return parsed_settings


def get_settings_from_module(module=None, default_settings=DEFAULT_CONFIG):
    """Loads settings from a module, returns a dictionary."""

    context = copy.deepcopy(default_settings)
    if module is not None:
        context.update(
            (k, v) for k, v in inspect.getmembers(module) if k.isupper())
    return context


def get_settings_from_file(path, default_settings=DEFAULT_CONFIG):
    """Loads settings from a file path, returning a dict."""

    name, ext = os.path.splitext(os.path.basename(path))
    module = load_source(name, path)
    return get_settings_from_module(module, default_settings=default_settings)


def configure_settings(settings):
    """Provide optimizations, error checking, and warnings for the given
    settings.
    Also, specify the log messages to be ignored.
    """
    if not 'PATH' in settings or not os.path.isdir(settings['PATH']):
        raise Exception('You need to specify a path containing the content'
                        ' (see pelican --help for more information)')

    # specify the log messages to be ignored
    LimitFilter.ignore.update(set(settings.get('LOG_FILTER',
                                               DEFAULT_CONFIG['LOG_FILTER'])))

    # lookup the theme in "pelican/themes" if the given one doesn't exist
    if not os.path.isdir(settings['THEME']):
        theme_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'themes',
            settings['THEME'])
        if os.path.exists(theme_path):
            settings['THEME'] = theme_path
        else:
            raise Exception("Could not find the theme %s"
                            % settings['THEME'])

    # make paths selected for writing absolute if necessary
    settings['WRITE_SELECTED'] = [
        os.path.abspath(path) for path in
        settings.get('WRITE_SELECTED', DEFAULT_CONFIG['WRITE_SELECTED'])
        ]

    # standardize strings to lowercase strings
    for key in [
            'DEFAULT_LANG',
            ]:
        if key in settings:
            settings[key] = settings[key].lower()

    # standardize strings to lists
    for key in [
            'LOCALE',
            ]:
        if key in settings and isinstance(settings[key], six.string_types):
            settings[key] = [settings[key]]

    # check settings that must be a particular type
    for key, types in [
            ('OUTPUT_SOURCES_EXTENSION', six.string_types),
            ('FILENAME_METADATA', six.string_types),
            ]:
        if key in settings and not isinstance(settings[key], types):
            value = settings.pop(key)
            logger.warn(
                'Detected misconfigured {} ({}), '
                'falling back to the default ({})'.format(
                    key, value, DEFAULT_CONFIG[key]))

    # try to set the different locales, fallback on the default.
    locales = settings.get('LOCALE', DEFAULT_CONFIG['LOCALE'])

    for locale_ in locales:
        try:
            locale.setlocale(locale.LC_ALL, str(locale_))
            break  # break if it is successful
        except locale.Error:
            pass
    else:
        logger.warning("LOCALE option doesn't contain a correct value")

    if ('SITEURL' in settings):
        # If SITEURL has a trailing slash, remove it and provide a warning
        siteurl = settings['SITEURL']
        if (siteurl.endswith('/')):
            settings['SITEURL'] = siteurl[:-1]
            logger.warning("Removed extraneous trailing slash from SITEURL.")
        # If SITEURL is defined but FEED_DOMAIN isn't,
        # set FEED_DOMAIN to SITEURL
        if not 'FEED_DOMAIN' in settings:
            settings['FEED_DOMAIN'] = settings['SITEURL']

    # check content caching layer and warn of incompatibilities
    if (settings.get('CACHE_CONTENT', False) and
        settings.get('CONTENT_CACHING_LAYER', '') == 'generator' and
        settings.get('WITH_FUTURE_DATES', DEFAULT_CONFIG['WITH_FUTURE_DATES'])):
        logger.warning('WITH_FUTURE_DATES conflicts with '
                        "CONTENT_CACHING_LAYER set to 'generator', "
                        "use 'reader' layer instead")

    # Warn if feeds are generated with both SITEURL & FEED_DOMAIN undefined
    feed_keys = [
        'FEED_ATOM', 'FEED_RSS',
        'FEED_ALL_ATOM', 'FEED_ALL_RSS',
        'CATEGORY_FEED_ATOM', 'CATEGORY_FEED_RSS',
        'AUTHOR_FEED_ATOM', 'AUTHOR_FEED_RSS',
        'TAG_FEED_ATOM', 'TAG_FEED_RSS',
        'TRANSLATION_FEED_ATOM', 'TRANSLATION_FEED_RSS',
    ]

    if any(settings.get(k) for k in feed_keys):
        if not settings.get('SITEURL'):
            logger.warning('Feeds generated without SITEURL set properly may'
                           ' not be valid')

    if not 'TIMEZONE' in settings:
        logger.warning(
            'No timezone information specified in the settings. Assuming'
            ' your timezone is UTC for feed generation. Check '
            'http://docs.getpelican.com/en/latest/settings.html#timezone '
            'for more information')

    # fix up pagination rules
    from pelican.paginator import PaginationRule
    pagination_rules = [
        PaginationRule(*r) for r in settings.get(
            'PAGINATION_PATTERNS',
            DEFAULT_CONFIG['PAGINATION_PATTERNS'],
        )
    ]
    settings['PAGINATION_PATTERNS'] = sorted(
        pagination_rules,
        key=lambda r: r[0],
    )

    # Save people from accidentally setting a string rather than a list
    path_keys = (
        'ARTICLE_EXCLUDES',
        'DEFAULT_METADATA',
        'DIRECT_TEMPLATES',
        'EXTRA_TEMPLATES_PATHS',
        'FILES_TO_COPY',
        'IGNORE_FILES',
        'JINJA_EXTENSIONS',
        'PAGINATED_DIRECT_TEMPLATES',
        'PLUGINS',
        'STATIC_PATHS',
        'THEME_STATIC_PATHS',
    )
    for PATH_KEY in filter(lambda k: k in settings, path_keys):
            if isinstance(settings[PATH_KEY], six.string_types):
                logger.warning("Detected misconfiguration with %s setting "
                               "(must be a list), falling back to the default"
                               % PATH_KEY)
                settings[PATH_KEY] = DEFAULT_CONFIG[PATH_KEY]

    for old, new, doc in [
            ('LESS_GENERATOR', 'the Webassets plugin', None),
            ('FILES_TO_COPY', 'STATIC_PATHS and EXTRA_PATH_METADATA',
             'https://github.com/getpelican/pelican/blob/master/docs/settings.rst#path-metadata'),
            ]:
        if old in settings:
            message = 'The {} setting has been removed in favor of {}'.format(
                old, new)
            if doc:
                message += ', see {} for details'.format(doc)
            logger.warning(message)

    return settings

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from blinker import signal

# Run-level signals:

initialized = signal('pelican_initialized')
get_generators = signal('get_generators')
get_writer = signal('get_writer')
finalized = signal('pelican_finalized')

# Reader-level signals

readers_init = signal('readers_init')

# Generator-level signals

generator_init = signal('generator_init')

article_generator_init = signal('article_generator_init')
article_generator_pretaxonomy = signal('article_generator_pretaxonomy')
article_generator_finalized = signal('article_generator_finalized')
article_generator_write_article = signal('article_generator_write_article')
article_writer_finalized = signal('article_writer_finalized')

page_generator_init = signal('page_generator_init')
page_generator_finalized = signal('page_generator_finalized')

static_generator_init = signal('static_generator_init')
static_generator_finalized = signal('static_generator_finalized')

# Page-level signals

article_generator_preread = signal('article_generator_preread')
article_generator_context = signal('article_generator_context')

page_generator_preread = signal('page_generator_preread')
page_generator_context = signal('page_generator_context')

static_generator_preread = signal('static_generator_preread')
static_generator_context = signal('static_generator_context')

content_object_init = signal('content_object_init')

# Writers signals
content_written = signal('content_written')

########NEW FILE########
__FILENAME__ = default_conf
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
AUTHOR = 'Alexis Métaireau'
SITENAME = "Alexis' log"
SITEURL = 'http://blog.notmyidea.org'
TIMEZONE = 'UTC'

GITHUB_URL = 'http://github.com/ametaireau/'
DISQUS_SITENAME = "blog-notmyidea"
PDF_GENERATOR = False
REVERSE_CATEGORY_ORDER = True
DEFAULT_PAGINATION = 2

FEED_RSS = 'feeds/all.rss.xml'
CATEGORY_FEED_RSS = 'feeds/%s.rss.xml'

LINKS = (('Biologeek', 'http://biologeek.org'),
         ('Filyb', "http://filyb.info/"),
         ('Libert-fr', "http://www.libert-fr.com"),
         ('N1k0', "http://prendreuncafe.com/blog/"),
         ('Tarek Ziadé', "http://ziade.org/blog"),
         ('Zubin Mithra', "http://zubin71.wordpress.com/"),)

SOCIAL = (('twitter', 'http://twitter.com/ametaireau'),
          ('lastfm', 'http://lastfm.com/user/akounet'),
          ('github', 'http://github.com/ametaireau'),)

# global metadata to all the contents
DEFAULT_METADATA = (('yeah', 'it is'),)

# path-specific metadata
EXTRA_PATH_METADATA = {
    'extra/robots.txt': {'path': 'robots.txt'},
    }

# static paths will be copied without parsing their contents
STATIC_PATHS = [
    'pictures',
    'extra/robots.txt',
    ]

# foobar will not be used, because it's not in caps. All configuration keys
# have to be in caps
foobar = "barbaz"

########NEW FILE########
__FILENAME__ = support
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
__all__ = ['get_article', 'unittest', ]

import os
import re
import subprocess
import sys
from six import StringIO
import logging
from logging.handlers import BufferingHandler
import unittest
import locale

from functools import wraps
from contextlib import contextmanager
from tempfile import mkdtemp
from shutil import rmtree

from pelican.contents import Article
from pelican.settings import DEFAULT_CONFIG


@contextmanager
def temporary_folder():
    """creates a temporary folder, return it and delete it afterwards.

    This allows to do something like this in tests:

        >>> with temporary_folder() as d:
            # do whatever you want
    """
    tempdir = mkdtemp()
    try:
        yield tempdir
    finally:
        rmtree(tempdir)


def isplit(s, sep=None):
    """Behaves like str.split but returns a generator instead of a list.

    >>> list(isplit('\tUse the force\n')) == '\tUse the force\n'.split()
    True
    >>> list(isplit('\tUse the force\n')) == ['Use', 'the', 'force']
    True
    >>> (list(isplit('\tUse the force\n', "e"))
         == '\tUse the force\n'.split("e"))
    True
    >>> list(isplit('Use the force', "e")) == 'Use the force'.split("e")
    True
    >>> list(isplit('Use the force', "e")) == ['Us', ' th', ' forc', '']
    True

    """
    sep, hardsep = r'\s+' if sep is None else re.escape(sep), sep is not None
    exp, pos, l = re.compile(sep), 0, len(s)
    while True:
        m = exp.search(s, pos)
        if not m:
            if pos < l or hardsep:
                #      ^ mimic "split()": ''.split() returns []
                yield s[pos:]
            break
        start = m.start()
        if pos < start or hardsep:
            #           ^ mimic "split()": includes trailing empty string
            yield s[pos:start]
        pos = m.end()


def mute(returns_output=False):
    """Decorate a function that prints to stdout, intercepting the output.
    If "returns_output" is True, the function will return a generator
    yielding the printed lines instead of the return values.

    The decorator litterally hijack sys.stdout during each function
    execution, so be careful with what you apply it to.

    >>> def numbers():
        print "42"
        print "1984"
    ...
    >>> numbers()
    42
    1984
    >>> mute()(numbers)()
    >>> list(mute(True)(numbers)())
    ['42', '1984']

    """

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            saved_stdout = sys.stdout
            sys.stdout = StringIO()

            try:
                out = func(*args, **kwargs)
                if returns_output:
                    out = isplit(sys.stdout.getvalue().strip())
            finally:
                sys.stdout = saved_stdout

            return out

        return wrapper

    return decorator


def get_article(title, slug, content, lang, extra_metadata=None):
    metadata = {'slug': slug, 'title': title, 'lang': lang}
    if extra_metadata is not None:
        metadata.update(extra_metadata)
    return Article(content, metadata=metadata)


def skipIfNoExecutable(executable):
    """Skip test if `executable` is not found

    Tries to run `executable` with subprocess to make sure it's in the path,
    and skips the tests if not found (if subprocess raises a `OSError`).
    """

    with open(os.devnull, 'w') as fnull:
        try:
            res = subprocess.call(executable, stdout=fnull, stderr=fnull)
        except OSError:
            res = None

    if res is None:
        return unittest.skip('{0} executable not found'.format(executable))

    return lambda func: func


def module_exists(module_name):
    """Test if a module is importable."""

    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True


def locale_available(locale_):
    old_locale = locale.setlocale(locale.LC_TIME)

    try:
        locale.setlocale(locale.LC_TIME, str(locale_))
    except locale.Error:
        return False
    else:
        locale.setlocale(locale.LC_TIME, old_locale)
        return True


def get_settings(**kwargs):
    """Provide tweaked setting dictionaries for testing

    Set keyword arguments to override specific settings.
    """
    settings = DEFAULT_CONFIG.copy()
    for key,value in kwargs.items():
        settings[key] = value
    return settings


class LogCountHandler(BufferingHandler):
    """Capturing and counting logged messages."""

    def __init__(self, capacity=1000):
        logging.handlers.BufferingHandler.__init__(self, capacity)

    def count_logs(self, msg=None, level=None):
        return len([l for l in self.buffer
            if (msg is None or re.match(msg, l.getMessage()))
            and (level is None or l.levelno == level)
            ])


class LoggedTestCase(unittest.TestCase):
    """A test case that captures log messages."""

    def setUp(self):
        super(LoggedTestCase, self).setUp()
        self._logcount_handler = LogCountHandler()
        logging.getLogger().addHandler(self._logcount_handler)

    def tearDown(self):
        logging.getLogger().removeHandler(self._logcount_handler)
        super(LoggedTestCase, self).tearDown()

    def assertLogCountEqual(self, count=None, msg=None, **kwargs):
        actual = self._logcount_handler.count_logs(msg=msg, **kwargs)
        self.assertEqual(
            actual, count,
            msg='expected {} occurrences of {!r}, but found {}'.format(
                count, msg, actual))

########NEW FILE########
__FILENAME__ = test_contents
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import six
from datetime import datetime
from sys import platform
import locale

from pelican.tests.support import unittest, get_settings

from pelican.contents import Page, Article, URLWrapper
from pelican.settings import DEFAULT_CONFIG
from pelican.utils import truncate_html_words
from pelican.signals import content_object_init
from jinja2.utils import generate_lorem_ipsum

# generate one paragraph, enclosed with <p>
TEST_CONTENT = str(generate_lorem_ipsum(n=1))
TEST_SUMMARY = generate_lorem_ipsum(n=1, html=False)


class TestPage(unittest.TestCase):

    def setUp(self):
        super(TestPage, self).setUp()
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))
        self.page_kwargs = {
            'content': TEST_CONTENT,
            'context': {
                'localsiteurl': '',
            },
            'metadata': {
                'summary': TEST_SUMMARY,
                'title': 'foo bar',
                'author': 'Blogger',
            },
            'source_path': '/path/to/file/foo.ext'
        }

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self.old_locale)

    def test_use_args(self):
        # Creating a page with arguments passed to the constructor should use
        # them to initialise object's attributes.
        metadata = {'foo': 'bar', 'foobar': 'baz', 'title': 'foobar', }
        page = Page(TEST_CONTENT, metadata=metadata,
                context={'localsiteurl': ''})
        for key, value in metadata.items():
            self.assertTrue(hasattr(page, key))
            self.assertEqual(value, getattr(page, key))
        self.assertEqual(page.content, TEST_CONTENT)

    def test_mandatory_properties(self):
        # If the title is not set, must throw an exception.
        page = Page('content')
        with self.assertRaises(NameError):
            page.check_properties()

        page = Page('content', metadata={'title': 'foobar'})
        page.check_properties()

    def test_summary_from_metadata(self):
        # If a :summary: metadata is given, it should be used
        page = Page(**self.page_kwargs)
        self.assertEqual(page.summary, TEST_SUMMARY)

    def test_summary_max_length(self):
        # If a :SUMMARY_MAX_LENGTH: is set, and there is no other summary,
        # generated summary should not exceed the given length.
        page_kwargs = self._copy_page_kwargs()
        settings = get_settings()
        page_kwargs['settings'] = settings
        del page_kwargs['metadata']['summary']
        settings['SUMMARY_MAX_LENGTH'] = None
        page = Page(**page_kwargs)
        self.assertEqual(page.summary, TEST_CONTENT)
        settings['SUMMARY_MAX_LENGTH'] = 10
        page = Page(**page_kwargs)
        self.assertEqual(page.summary, truncate_html_words(TEST_CONTENT, 10))
        settings['SUMMARY_MAX_LENGTH'] = 0
        page = Page(**page_kwargs)
        self.assertEqual(page.summary, '')

    def test_slug(self):
        page_kwargs = self._copy_page_kwargs()
        settings = get_settings()
        page_kwargs['settings'] = settings
        settings['SLUGIFY_SOURCE'] = "title"
        page = Page(**page_kwargs)
        self.assertEqual(page.slug, 'foo-bar')
        settings['SLUGIFY_SOURCE'] = "basename"
        page = Page(**page_kwargs)
        self.assertEqual(page.slug, 'foo')

    def test_defaultlang(self):
        # If no lang is given, default to the default one.
        page = Page(**self.page_kwargs)
        self.assertEqual(page.lang, DEFAULT_CONFIG['DEFAULT_LANG'])

        # it is possible to specify the lang in the metadata infos
        self.page_kwargs['metadata'].update({'lang': 'fr', })
        page = Page(**self.page_kwargs)
        self.assertEqual(page.lang, 'fr')

    def test_save_as(self):
        # If a lang is not the default lang, save_as should be set
        # accordingly.

        # if a title is defined, save_as should be set
        page = Page(**self.page_kwargs)
        self.assertEqual(page.save_as, "pages/foo-bar.html")

        # if a language is defined, save_as should include it accordingly
        self.page_kwargs['metadata'].update({'lang': 'fr', })
        page = Page(**self.page_kwargs)
        self.assertEqual(page.save_as, "pages/foo-bar-fr.html")

    def test_metadata_url_format(self):
        # Arbitrary metadata should be passed through url_format()
        page = Page(**self.page_kwargs)
        self.assertIn('summary', page.url_format.keys())
        page.metadata['directory'] = 'test-dir'
        page.settings = get_settings(PAGE_SAVE_AS='{directory}/{slug}')
        self.assertEqual(page.save_as, 'test-dir/foo-bar')

    def test_datetime(self):
        # If DATETIME is set to a tuple, it should be used to override LOCALE
        dt = datetime(2015, 9, 13)

        page_kwargs = self._copy_page_kwargs()

        # set its date to dt
        page_kwargs['metadata']['date'] = dt
        page = Page(**page_kwargs)

        # page.locale_date is a unicode string in both python2 and python3
        dt_date = dt.strftime(DEFAULT_CONFIG['DEFAULT_DATE_FORMAT']) 
        # dt_date is a byte string in python2, and a unicode string in python3
        # Let's make sure it is a unicode string (relies on python 3.3 supporting the u prefix)
        if type(dt_date) != type(u''):
            # python2:
            dt_date = unicode(dt_date, 'utf8')

        self.assertEqual(page.locale_date, dt_date )
        page_kwargs['settings'] = get_settings()

        # I doubt this can work on all platforms ...
        if platform == "win32":
            locale = 'jpn'
        else:
            locale = 'ja_JP.utf8'
        page_kwargs['settings']['DATE_FORMATS'] = {'jp': (locale,
                                                          '%Y-%m-%d(%a)')}
        page_kwargs['metadata']['lang'] = 'jp'

        import locale as locale_module
        try:
            page = Page(**page_kwargs)
            self.assertEqual(page.locale_date, '2015-09-13(\u65e5)')
        except locale_module.Error:
            # The constructor of ``Page`` will try to set the locale to
            # ``ja_JP.utf8``. But this attempt will failed when there is no
            # such locale in the system. You can see which locales there are
            # in your system with ``locale -a`` command.
            #
            # Until we find some other method to test this functionality, we
            # will simply skip this test.
            unittest.skip("There is no locale %s in this system." % locale)

    def test_template(self):
        # Pages default to page, metadata overwrites
        default_page = Page(**self.page_kwargs)
        self.assertEqual('page', default_page.template)
        page_kwargs = self._copy_page_kwargs()
        page_kwargs['metadata']['template'] = 'custom'
        custom_page = Page(**page_kwargs)
        self.assertEqual('custom', custom_page.template)

    def _copy_page_kwargs(self):
        # make a deep copy of page_kwargs
        page_kwargs = dict([(key, self.page_kwargs[key]) for key in
                            self.page_kwargs])
        for key in page_kwargs:
            if not isinstance(page_kwargs[key], dict):
                break
            page_kwargs[key] = dict([(subkey, page_kwargs[key][subkey])
                                     for subkey in page_kwargs[key]])

        return page_kwargs

    def test_signal(self):
        # If a title is given, it should be used to generate the slug.

        def receiver_test_function(sender, instance):
            pass

        content_object_init.connect(receiver_test_function, sender=Page)
        Page(**self.page_kwargs)
        self.assertTrue(content_object_init.has_receivers_for(Page))

    def test_get_content(self):
        # Test that the content is updated with the relative links to
        # filenames, tags and categories.
        settings = get_settings()
        args = self.page_kwargs.copy()
        args['settings'] = settings

        # Tag
        args['content'] = ('A simple test, with a '
                           '<a href="|tag|tagname">link</a>')
        page = Page(**args)
        content = page.get_content('http://notmyidea.org')
        self.assertEqual(content, ('A simple test, with a '
                                   '<a href="tag/tagname.html">link</a>'))

        # Category
        args['content'] = ('A simple test, with a '
                           '<a href="|category|category">link</a>')
        page = Page(**args)
        content = page.get_content('http://notmyidea.org')
        self.assertEqual(content,
                         ('A simple test, with a '
                          '<a href="category/category.html">link</a>'))

    def test_intrasite_link(self):
        # type does not take unicode in PY2 and bytes in PY3, which in
        # combination with unicode literals leads to following insane line:
        cls_name = '_DummyArticle' if six.PY3 else b'_DummyArticle'
        article = type(cls_name, (object,), {'url': 'article.html'})

        args = self.page_kwargs.copy()
        args['settings'] = get_settings()
        args['source_path'] = 'content'
        args['context']['filenames'] = {'article.rst': article}

        # Classic intrasite link via filename
        args['content'] = (
            'A simple test, with a '
            '<a href="|filename|article.rst">link</a>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'A simple test, with a '
            '<a href="http://notmyidea.org/article.html">link</a>'
        )

        # fragment
        args['content'] = (
            'A simple test, with a '
            '<a href="|filename|article.rst#section-2">link</a>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'A simple test, with a '
            '<a href="http://notmyidea.org/article.html#section-2">link</a>'
        )

        # query
        args['content'] = (
            'A simple test, with a '
            '<a href="|filename|article.rst'
            '?utm_whatever=234&highlight=word">link</a>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'A simple test, with a '
            '<a href="http://notmyidea.org/article.html'
            '?utm_whatever=234&highlight=word">link</a>'
        )

        # combination
        args['content'] = (
            'A simple test, with a '
            '<a href="|filename|article.rst'
            '?utm_whatever=234&highlight=word#section-2">link</a>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'A simple test, with a '
            '<a href="http://notmyidea.org/article.html'
            '?utm_whatever=234&highlight=word#section-2">link</a>'
        )

    def test_intrasite_link_more(self):
        # type does not take unicode in PY2 and bytes in PY3, which in
        # combination with unicode literals leads to following insane line:
        cls_name = '_DummyAsset' if six.PY3 else b'_DummyAsset'

        args = self.page_kwargs.copy()
        args['settings'] = get_settings()
        args['source_path'] = 'content'
        args['context']['filenames'] = {
            'images/poster.jpg': type(cls_name, (object,), {'url': 'images/poster.jpg'}),
            'assets/video.mp4': type(cls_name, (object,), {'url': 'assets/video.mp4'}),
            'images/graph.svg': type(cls_name, (object,), {'url': 'images/graph.svg'}),
            'reference.rst': type(cls_name, (object,), {'url': 'reference.html'}),
        }

        # video.poster
        args['content'] = (
            'There is a video with poster '
            '<video controls poster="{filename}/images/poster.jpg">'
            '<source src="|filename|/assets/video.mp4" type="video/mp4">'
            '</video>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'There is a video with poster '
            '<video controls poster="http://notmyidea.org/images/poster.jpg">'
            '<source src="http://notmyidea.org/assets/video.mp4" type="video/mp4">'
            '</video>'
        )

        # object.data
        args['content'] = (
            'There is a svg object '
            '<object data="{filename}/images/graph.svg" type="image/svg+xml"></object>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'There is a svg object '
            '<object data="http://notmyidea.org/images/graph.svg" type="image/svg+xml"></object>'
        )

        # blockquote.cite
        args['content'] = (
            'There is a blockquote with cite attribute '
            '<blockquote cite="{filename}reference.rst">blah blah</blockquote>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'There is a blockquote with cite attribute '
            '<blockquote cite="http://notmyidea.org/reference.html">blah blah</blockquote>'
        )

    def test_intrasite_link_markdown_spaces(self):
        # Markdown introduces %20 instead of spaces, this tests that
        # we support markdown doing this.
        cls_name = '_DummyArticle' if six.PY3 else b'_DummyArticle'
        article = type(cls_name, (object,), {'url': 'article-spaces.html'})

        args = self.page_kwargs.copy()
        args['settings'] = get_settings()
        args['source_path'] = 'content'
        args['context']['filenames'] = {'article spaces.rst': article}

        # An intrasite link via filename with %20 as a space
        args['content'] = (
            'A simple test, with a '
            '<a href="|filename|article%20spaces.rst">link</a>'
        )
        content = Page(**args).get_content('http://notmyidea.org')
        self.assertEqual(
            content,
            'A simple test, with a '
            '<a href="http://notmyidea.org/article-spaces.html">link</a>'
        )

    def test_multiple_authors(self):
        """Test article with multiple authors."""
        args = self.page_kwargs.copy()
        content = Page(**args)
        assert content.authors == [content.author]
        args['metadata'].pop('author')
        args['metadata']['authors'] = ['First Author', 'Second Author']
        content = Page(**args)
        assert content.authors
        assert content.author == content.authors[0]


class TestArticle(TestPage):
    def test_template(self):
        # Articles default to article, metadata overwrites
        default_article = Article(**self.page_kwargs)
        self.assertEqual('article', default_article.template)
        article_kwargs = self._copy_page_kwargs()
        article_kwargs['metadata']['template'] = 'custom'
        custom_article = Article(**article_kwargs)
        self.assertEqual('custom', custom_article.template)

    def test_slugify_category_author(self):
        settings = get_settings()
        settings['SLUG_SUBSTITUTIONS'] = [ ('C#', 'csharp') ]
        settings['ARTICLE_URL'] = '{author}/{category}/{slug}/'
        settings['ARTICLE_SAVE_AS'] = '{author}/{category}/{slug}/index.html'
        article_kwargs = self._copy_page_kwargs()
        article_kwargs['metadata']['author'] = "O'Brien"
        article_kwargs['metadata']['category'] = 'C# & stuff'
        article_kwargs['metadata']['title'] = 'fnord'
        article_kwargs['settings'] = settings
        article = Article(**article_kwargs)
        self.assertEqual(article.url, 'obrien/csharp-stuff/fnord/')
        self.assertEqual(article.save_as, 'obrien/csharp-stuff/fnord/index.html')


class TestURLWrapper(unittest.TestCase):
    def test_comparisons(self):
        # URLWrappers are sorted by name
        wrapper_a = URLWrapper(name='first', settings={})
        wrapper_b = URLWrapper(name='last', settings={})
        self.assertFalse(wrapper_a > wrapper_b)
        self.assertFalse(wrapper_a >= wrapper_b)
        self.assertFalse(wrapper_a == wrapper_b)
        self.assertTrue(wrapper_a != wrapper_b)
        self.assertTrue(wrapper_a <= wrapper_b)
        self.assertTrue(wrapper_a < wrapper_b)
        wrapper_b.name = 'first'
        self.assertFalse(wrapper_a > wrapper_b)
        self.assertTrue(wrapper_a >= wrapper_b)
        self.assertTrue(wrapper_a == wrapper_b)
        self.assertFalse(wrapper_a != wrapper_b)
        self.assertTrue(wrapper_a <= wrapper_b)
        self.assertFalse(wrapper_a < wrapper_b)
        wrapper_a.name = 'last'
        self.assertTrue(wrapper_a > wrapper_b)
        self.assertTrue(wrapper_a >= wrapper_b)
        self.assertFalse(wrapper_a == wrapper_b)
        self.assertTrue(wrapper_a != wrapper_b)
        self.assertFalse(wrapper_a <= wrapper_b)
        self.assertFalse(wrapper_a < wrapper_b)

########NEW FILE########
__FILENAME__ = test_generators
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from codecs import open
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock
from shutil import rmtree
from tempfile import mkdtemp

from pelican.generators import (Generator, ArticlesGenerator, PagesGenerator,
                                TemplatePagesGenerator)
from pelican.writers import Writer
from pelican.tests.support import unittest, get_settings
import locale

CUR_DIR = os.path.dirname(__file__)
CONTENT_DIR = os.path.join(CUR_DIR, 'content')


class TestGenerator(unittest.TestCase):
    def setUp(self):
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))
        self.settings = get_settings()
        self.settings['READERS'] = {'asc': None}
        self.generator = Generator(self.settings.copy(), self.settings,
                                   CUR_DIR, self.settings['THEME'], None)

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self.old_locale)


    def test_include_path(self):
        filename = os.path.join(CUR_DIR, 'content', 'article.rst')
        include_path = self.generator._include_path
        self.assertTrue(include_path(filename))
        self.assertTrue(include_path(filename, extensions=('rst',)))
        self.assertFalse(include_path(filename, extensions=('md',)))


class TestArticlesGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        settings = get_settings(filenames={})
        settings['DEFAULT_CATEGORY'] = 'Default'
        settings['DEFAULT_DATE'] = (1970, 1, 1)
        settings['READERS'] = {'asc': None}
        settings['CACHE_CONTENT'] = False   # cache not needed for this logic tests

        cls.generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        cls.generator.generate_context()
        cls.articles = [[page.title, page.status, page.category.name,
                         page.template] for page in cls.generator.articles]

    def setUp(self):
        self.temp_cache = mkdtemp(prefix='pelican_cache.')

    def tearDown(self):
        rmtree(self.temp_cache)

    def test_generate_feeds(self):
        settings = get_settings()
        settings['CACHE_PATH'] = self.temp_cache
        generator = ArticlesGenerator(
            context=settings, settings=settings,
            path=None, theme=settings['THEME'], output_path=None)
        writer = MagicMock()
        generator.generate_feeds(writer)
        writer.write_feed.assert_called_with([], settings,
                                             'feeds/all.atom.xml')

        generator = ArticlesGenerator(
            context=settings, settings=get_settings(FEED_ALL_ATOM=None),
            path=None, theme=settings['THEME'], output_path=None)
        writer = MagicMock()
        generator.generate_feeds(writer)
        self.assertFalse(writer.write_feed.called)

    def test_generate_context(self):

        articles_expected = [
            ['Article title', 'published', 'Default', 'article'],
            ['Article with markdown and summary metadata multi', 'published',
             'Default', 'article'],
            ['Article with markdown and summary metadata single', 'published',
             'Default', 'article'],
            ['Article with markdown containing footnotes', 'published',
             'Default', 'article'],
            ['Article with template', 'published', 'Default', 'custom'],
            ['Rst with filename metadata', 'published', 'yeah', 'article'],
            ['Test Markdown extensions', 'published', 'Default', 'article'],
            ['Test markdown File', 'published', 'test', 'article'],
            ['Test md File', 'published', 'test', 'article'],
            ['Test mdown File', 'published', 'test', 'article'],
            ['Test mkd File', 'published', 'test', 'article'],
            ['This is a super article !', 'published', 'Yeah', 'article'],
            ['This is a super article !', 'published', 'Yeah', 'article'],
            ['Article with Nonconformant HTML meta tags', 'published', 'Default', 'article'],
            ['This is a super article !', 'published', 'yeah', 'article'],
            ['This is a super article !', 'published', 'yeah', 'article'],
            ['This is a super article !', 'published', 'yeah', 'article'],
            ['This is a super article !', 'published', 'Default', 'article'],
            ['This is an article with category !', 'published', 'yeah',
             'article'],
            ['This is an article with multiple authors!', 'published', 'Default', 'article'],
            ['This is an article with multiple authors!', 'published', 'Default', 'article'],
            ['This is an article without category !', 'published', 'Default',
             'article'],
            ['This is an article without category !', 'published',
             'TestCategory', 'article'],
            ['マックOS X 10.8でパイソンとVirtualenvをインストールと設定', 'published',
             '指導書', 'article'],
        ]
        self.assertEqual(sorted(articles_expected), sorted(self.articles))

    def test_generate_categories(self):

        # test for name
        # categories are grouped by slug; if two categories have the same slug
        # but different names they will be grouped together, the first one in
        # terms of process order will define the name for that category
        categories = [cat.name for cat, _ in self.generator.categories]
        categories_alternatives = (
            sorted(['Default', 'TestCategory', 'Yeah', 'test', '指導書']),
            sorted(['Default', 'TestCategory', 'yeah', 'test', '指導書']),
        )
        self.assertIn(sorted(categories), categories_alternatives)
        # test for slug
        categories = [cat.slug for cat, _ in self.generator.categories]
        categories_expected = ['default', 'testcategory', 'yeah', 'test',
                               'zhi-dao-shu']
        self.assertEqual(sorted(categories), sorted(categories_expected))

    def test_do_not_use_folder_as_category(self):

        settings = get_settings(filenames={})
        settings['DEFAULT_CATEGORY'] = 'Default'
        settings['DEFAULT_DATE'] = (1970, 1, 1)
        settings['USE_FOLDER_AS_CATEGORY'] = False
        settings['CACHE_PATH'] = self.temp_cache
        settings['READERS'] = {'asc': None}
        settings['filenames'] = {}
        generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        # test for name
        # categories are grouped by slug; if two categories have the same slug
        # but different names they will be grouped together, the first one in
        # terms of process order will define the name for that category
        categories = [cat.name for cat, _ in generator.categories]
        categories_alternatives = (
            sorted(['Default', 'Yeah', 'test', '指導書']),
            sorted(['Default', 'yeah', 'test', '指導書']),
        )
        self.assertIn(sorted(categories), categories_alternatives)
        # test for slug
        categories = [cat.slug for cat, _ in generator.categories]
        categories_expected = ['default', 'yeah', 'test', 'zhi-dao-shu']
        self.assertEqual(sorted(categories), sorted(categories_expected))

    def test_direct_templates_save_as_default(self):

        settings = get_settings(filenames={})
        settings['CACHE_PATH'] = self.temp_cache
        generator = ArticlesGenerator(
            context=settings, settings=settings,
            path=None, theme=settings['THEME'], output_path=None)
        write = MagicMock()
        generator.generate_direct_templates(write)
        write.assert_called_with("archives.html",
                                 generator.get_template("archives"), settings,
                                 blog=True, paginated={}, page_name='archives')

    def test_direct_templates_save_as_modified(self):

        settings = get_settings()
        settings['DIRECT_TEMPLATES'] = ['archives']
        settings['ARCHIVES_SAVE_AS'] = 'archives/index.html'
        settings['CACHE_PATH'] = self.temp_cache
        generator = ArticlesGenerator(
            context=settings, settings=settings,
            path=None, theme=settings['THEME'], output_path=None)
        write = MagicMock()
        generator.generate_direct_templates(write)
        write.assert_called_with("archives/index.html",
                                 generator.get_template("archives"), settings,
                                 blog=True, paginated={},
                                 page_name='archives/index')

    def test_direct_templates_save_as_false(self):

        settings = get_settings()
        settings['DIRECT_TEMPLATES'] = ['archives']
        settings['ARCHIVES_SAVE_AS'] = 'archives/index.html'
        settings['CACHE_PATH'] = self.temp_cache
        generator = ArticlesGenerator(
            context=settings, settings=settings,
            path=None, theme=settings['THEME'], output_path=None)
        write = MagicMock()
        generator.generate_direct_templates(write)
        write.assert_called_count == 0

    def test_per_article_template(self):
        """
        Custom template articles get the field but standard/unset are None
        """
        custom_template = ['Article with template', 'published', 'Default',
                           'custom']
        standard_template = ['This is a super article !', 'published', 'Yeah',
                             'article']
        self.assertIn(custom_template, self.articles)
        self.assertIn(standard_template, self.articles)

    def test_period_in_timeperiod_archive(self):
        """
        Test that the context of a generated period_archive is passed
        'period' : a tuple of year, month, day according to the time period
        """
        settings = get_settings(filenames={})

        settings['YEAR_ARCHIVE_SAVE_AS'] = 'posts/{date:%Y}/index.html'
        settings['CACHE_PATH'] = self.temp_cache
        generator = ArticlesGenerator(
            context=settings, settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        write = MagicMock()
        generator.generate_period_archives(write)
        dates = [d for d in generator.dates if d.date.year == 1970]
        self.assertEqual(len(dates), 1)
        #among other things it must have at least been called with this
        settings["period"] = (1970,)
        write.assert_called_with("posts/1970/index.html",
                                 generator.get_template("period_archives"),
                                 settings,
                                 blog=True, dates=dates)

        del settings["period"]
        settings['MONTH_ARCHIVE_SAVE_AS'] = 'posts/{date:%Y}/{date:%b}/index.html'
        generator = ArticlesGenerator(
            context=settings, settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        write = MagicMock()
        generator.generate_period_archives(write)
        dates = [d for d in generator.dates if d.date.year == 1970
                                            and d.date.month == 1]
        self.assertEqual(len(dates), 1)
        settings["period"] = (1970, "January")
        #among other things it must have at least been called with this
        write.assert_called_with("posts/1970/Jan/index.html",
                                 generator.get_template("period_archives"),
                                 settings,
                                 blog=True, dates=dates)

        del settings["period"]
        settings['DAY_ARCHIVE_SAVE_AS'] = 'posts/{date:%Y}/{date:%b}/{date:%d}/index.html'
        generator = ArticlesGenerator(
            context=settings, settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        write = MagicMock()
        generator.generate_period_archives(write)
        dates = [d for d in generator.dates if d.date.year == 1970
                                            and d.date.month == 1
                                            and d.date.day == 1]
        self.assertEqual(len(dates), 1)
        settings["period"] = (1970, "January", 1)
        #among other things it must have at least been called with this
        write.assert_called_with("posts/1970/Jan/01/index.html",
                                 generator.get_template("period_archives"),
                                 settings,
                                 blog=True, dates=dates)

    def test_generate_authors(self):
        """Check authors generation."""
        authors = [author.name for author, _ in self.generator.authors]
        authors_expected = sorted(['Alexis Métaireau', 'First Author', 'Second Author'])
        self.assertEqual(sorted(authors), authors_expected)
        # test for slug
        authors = [author.slug for author, _ in self.generator.authors]
        authors_expected = ['alexis-metaireau', 'first-author', 'second-author']
        self.assertEqual(sorted(authors), sorted(authors_expected))

    def test_article_object_caching(self):
        """Test Article objects caching at the generator level"""
        settings = get_settings(filenames={})
        settings['CACHE_PATH'] = self.temp_cache
        settings['CONTENT_CACHING_LAYER'] = 'generator'
        settings['READERS'] = {'asc': None}

        generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        self.assertTrue(hasattr(generator, '_cache'))

        generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.readers.read_file = MagicMock()
        generator.generate_context()
        generator.readers.read_file.assert_called_count == 0

    def test_reader_content_caching(self):
        """Test raw content caching at the reader level"""
        settings = get_settings(filenames={})
        settings['CACHE_PATH'] = self.temp_cache
        settings['READERS'] = {'asc': None}

        generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        self.assertTrue(hasattr(generator.readers, '_cache'))

        generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        readers = generator.readers.readers
        for reader in readers.values():
            reader.read = MagicMock()
        generator.generate_context()
        for reader in readers.values():
            reader.read.assert_called_count == 0

    def test_ignore_cache(self):
        """Test that all the articles are read again when not loading cache

        used in --ignore-cache or autoreload mode"""
        settings = get_settings(filenames={})
        settings['CACHE_PATH'] = self.temp_cache
        settings['READERS'] = {'asc': None}

        generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.readers.read_file = MagicMock()
        generator.generate_context()
        self.assertTrue(hasattr(generator, '_cache_open'))
        orig_call_count = generator.readers.read_file.call_count

        settings['LOAD_CONTENT_CACHE'] = False
        generator = ArticlesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.readers.read_file = MagicMock()
        generator.generate_context()
        generator.readers.read_file.assert_called_count == orig_call_count


class TestPageGenerator(unittest.TestCase):
    # Note: Every time you want to test for a new field; Make sure the test
    # pages in "TestPages" have all the fields Add it to distilled in
    # distill_pages Then update the assertEqual in test_generate_context
    # to match expected

    def setUp(self):
        self.temp_cache = mkdtemp(prefix='pelican_cache.')

    def tearDown(self):
        rmtree(self.temp_cache)

    def distill_pages(self, pages):
        return [[page.title, page.status, page.template] for page in pages]

    def test_generate_context(self):
        settings = get_settings(filenames={})
        settings['PAGE_DIR'] = 'TestPages'  # relative to CUR_DIR
        settings['CACHE_PATH'] = self.temp_cache
        settings['DEFAULT_DATE'] = (1970, 1, 1)

        generator = PagesGenerator(
            context=settings.copy(), settings=settings,
            path=CUR_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        pages = self.distill_pages(generator.pages)
        hidden_pages = self.distill_pages(generator.hidden_pages)

        pages_expected = [
            ['This is a test page', 'published', 'page'],
            ['This is a markdown test page', 'published', 'page'],
            ['This is a test page with a preset template', 'published',
             'custom']
        ]
        hidden_pages_expected = [
            ['This is a test hidden page', 'hidden', 'page'],
            ['This is a markdown test hidden page', 'hidden', 'page'],
            ['This is a test hidden page with a custom template', 'hidden',
             'custom']
        ]

        self.assertEqual(sorted(pages_expected), sorted(pages))
        self.assertEqual(sorted(hidden_pages_expected), sorted(hidden_pages))

    def test_page_object_caching(self):
        """Test Page objects caching at the generator level"""
        settings = get_settings(filenames={})
        settings['CACHE_PATH'] = self.temp_cache
        settings['CONTENT_CACHING_LAYER'] = 'generator'
        settings['READERS'] = {'asc': None}

        generator = PagesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        self.assertTrue(hasattr(generator, '_cache'))

        generator = PagesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.readers.read_file = MagicMock()
        generator.generate_context()
        generator.readers.read_file.assert_called_count == 0

    def test_reader_content_caching(self):
        """Test raw content caching at the reader level"""
        settings = get_settings(filenames={})
        settings['CACHE_PATH'] = self.temp_cache
        settings['READERS'] = {'asc': None}

        generator = PagesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.generate_context()
        self.assertTrue(hasattr(generator.readers, '_cache'))

        generator = PagesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        readers = generator.readers.readers
        for reader in readers.values():
            reader.read = MagicMock()
        generator.generate_context()
        for reader in readers.values():
            reader.read.assert_called_count == 0

    def test_ignore_cache(self):
        """Test that all the pages are read again when not loading cache

        used in --ignore_cache or autoreload mode"""
        settings = get_settings(filenames={})
        settings['CACHE_PATH'] = self.temp_cache
        settings['READERS'] = {'asc': None}

        generator = PagesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.readers.read_file = MagicMock()
        generator.generate_context()
        self.assertTrue(hasattr(generator, '_cache_open'))
        orig_call_count = generator.readers.read_file.call_count

        settings['LOAD_CONTENT_CACHE'] = False
        generator = PagesGenerator(
            context=settings.copy(), settings=settings,
            path=CONTENT_DIR, theme=settings['THEME'], output_path=None)
        generator.readers.read_file = MagicMock()
        generator.generate_context()
        generator.readers.read_file.assert_called_count == orig_call_count


class TestTemplatePagesGenerator(unittest.TestCase):

    TEMPLATE_CONTENT = "foo: {{ foo }}"

    def setUp(self):
        self.temp_content = mkdtemp(prefix='pelicantests.')
        self.temp_output = mkdtemp(prefix='pelicantests.')
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))


    def tearDown(self):
        rmtree(self.temp_content)
        rmtree(self.temp_output)
        locale.setlocale(locale.LC_ALL, self.old_locale)

    def test_generate_output(self):

        settings = get_settings()
        settings['STATIC_PATHS'] = ['static']
        settings['TEMPLATE_PAGES'] = {
            'template/source.html': 'generated/file.html'
        }

        generator = TemplatePagesGenerator(
            context={'foo': 'bar'}, settings=settings,
            path=self.temp_content, theme='', output_path=self.temp_output)

        # create a dummy template file
        template_dir = os.path.join(self.temp_content, 'template')
        template_path = os.path.join(template_dir, 'source.html')
        os.makedirs(template_dir)
        with open(template_path, 'w') as template_file:
            template_file.write(self.TEMPLATE_CONTENT)

        writer = Writer(self.temp_output, settings=settings)
        generator.generate_output(writer)

        output_path = os.path.join(self.temp_output, 'generated', 'file.html')

        # output file has been generated
        self.assertTrue(os.path.exists(output_path))

        # output content is correct
        with open(output_path, 'r') as output_file:
            self.assertEqual(output_file.read(), 'foo: bar')

########NEW FILE########
__FILENAME__ = test_importer
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
import re

import locale
from pelican.tools.pelican_import import wp2fields, fields2pelican, decode_wp_content, build_header, build_markdown_header, get_attachments, download_attachments
from pelican.tests.support import (unittest, temporary_folder, mute,
                                   skipIfNoExecutable)

from pelican.utils import slugify

CUR_DIR = os.path.abspath(os.path.dirname(__file__))
WORDPRESS_XML_SAMPLE = os.path.join(CUR_DIR, 'content', 'wordpressexport.xml')
WORDPRESS_ENCODED_CONTENT_SAMPLE = os.path.join(CUR_DIR,
                                                'content',
                                                'wordpress_content_encoded')
WORDPRESS_DECODED_CONTENT_SAMPLE = os.path.join(CUR_DIR,
                                                'content',
                                                'wordpress_content_decoded')

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = False  # NOQA


@skipIfNoExecutable(['pandoc', '--version'])
@unittest.skipUnless(BeautifulSoup, 'Needs BeautifulSoup module')
class TestWordpressXmlImporter(unittest.TestCase):

    def setUp(self):
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))
        self.posts = list(wp2fields(WORDPRESS_XML_SAMPLE))
        self.custposts = list(wp2fields(WORDPRESS_XML_SAMPLE, True))

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self.old_locale)

    def test_ignore_empty_posts(self):
        self.assertTrue(self.posts)
        for title, content, fname, date, author, categ, tags, kind, format in self.posts:
            self.assertTrue(title.strip())

    def test_recognise_page_kind(self):
        """ Check that we recognise pages in wordpress, as opposed to posts """
        self.assertTrue(self.posts)
        # Collect (title, filename, kind) of non-empty posts recognised as page
        pages_data = []
        for title, content, fname, date, author, categ, tags, kind, format in self.posts:
            if kind == 'page':
                pages_data.append((title, fname))
        self.assertEqual(2, len(pages_data))
        self.assertEqual(('Page', 'contact'), pages_data[0])
        self.assertEqual(('Empty Page', 'empty'), pages_data[1])

    def test_dirpage_directive_for_page_kind(self):
        silent_f2p = mute(True)(fields2pelican)
        test_post = filter(lambda p: p[0].startswith("Empty Page"), self.posts)
        with temporary_folder() as temp:
            fname = list(silent_f2p(test_post, 'markdown', temp, dirpage=True))[0]
            self.assertTrue(fname.endswith('pages%sempty.md' % os.path.sep))

    def test_dircat(self):
        silent_f2p = mute(True)(fields2pelican)
        test_posts = []
        for post in self.posts:
            # check post kind
            if len(post[5]) > 0: # Has a category
                test_posts.append(post)
        with temporary_folder() as temp:
            fnames = list(silent_f2p(test_posts, 'markdown', temp, dircat=True))
        index = 0
        for post in test_posts:
            name = post[2]
            category = slugify(post[5][0])
            name += '.md'
            filename = os.path.join(category, name)
            out_name = fnames[index]
            self.assertTrue(out_name.endswith(filename))
            index += 1

    def test_unless_custom_post_all_items_should_be_pages_or_posts(self):
        self.assertTrue(self.posts)
        pages_data = []
        for title, content, fname, date, author, categ, tags, kind, format in self.posts:
            if kind == 'page' or kind == 'article':
                pass
            else:
                pages_data.append((title, fname))
        self.assertEqual(0, len(pages_data))

    def test_recognise_custom_post_type(self):
        self.assertTrue(self.custposts)
        cust_data = []
        for title, content, fname, date, author, categ, tags, kind, format in self.custposts:
            if kind == 'article' or kind == 'page':
                pass
            else:
                cust_data.append((title, kind))
        self.assertEqual(3, len(cust_data))
        self.assertEqual(('A custom post in category 4', 'custom1'), cust_data[0])
        self.assertEqual(('A custom post in category 5', 'custom1'), cust_data[1])
        self.assertEqual(('A 2nd custom post type also in category 5', 'custom2'), cust_data[2])

    def test_custom_posts_put_in_own_dir(self):
        silent_f2p = mute(True)(fields2pelican)
        test_posts = []
        for post in self.custposts:
            # check post kind
            if post[7] == 'article' or post[7] == 'page':
                pass
            else:
                test_posts.append(post)
        with temporary_folder() as temp:
            fnames = list(silent_f2p(test_posts, 'markdown', temp, wp_custpost = True))
        index = 0
        for post in test_posts:
            name = post[2]
            kind = post[7]
            name += '.md'
            filename = os.path.join(kind, name)
            out_name = fnames[index]
            self.assertTrue(out_name.endswith(filename))
            index += 1

    def test_custom_posts_put_in_own_dir_and_catagory_sub_dir(self):
        silent_f2p = mute(True)(fields2pelican)
        test_posts = []
        for post in self.custposts:
            # check post kind
            if post[7] == 'article' or post[7] == 'page':
                pass
            else:
                test_posts.append(post)
        with temporary_folder() as temp:
            fnames = list(silent_f2p(test_posts, 'markdown', temp,
                wp_custpost=True, dircat=True))
        index = 0
        for post in test_posts:
            name = post[2]
            kind = post[7]
            category = slugify(post[5][0])
            name += '.md'
            filename = os.path.join(kind, category, name)
            out_name = fnames[index]
            self.assertTrue(out_name.endswith(filename))
            index += 1

    def test_wp_custpost_true_dirpage_false(self):
        #pages should only be put in their own directory when dirpage = True
        silent_f2p = mute(True)(fields2pelican)
        test_posts = []
        for post in self.custposts:
            # check post kind
            if post[7] == 'page':
                test_posts.append(post)
        with temporary_folder() as temp:
            fnames = list(silent_f2p(test_posts, 'markdown', temp,
                wp_custpost=True, dirpage=False))
        index = 0
        for post in test_posts:
            name = post[2]
            name += '.md'
            filename = os.path.join('pages', name)
            out_name = fnames[index]
            self.assertFalse(out_name.endswith(filename))


    def test_can_toggle_raw_html_code_parsing(self):
        def r(f):
            with open(f) as infile:
                return infile.read()
        silent_f2p = mute(True)(fields2pelican)

        with temporary_folder() as temp:

            rst_files = (r(f) for f in silent_f2p(self.posts, 'markdown', temp))
            self.assertTrue(any('<iframe' in rst for rst in rst_files))
            rst_files = (r(f) for f in silent_f2p(self.posts, 'markdown', temp,
                         strip_raw=True))
            self.assertFalse(any('<iframe' in rst for rst in rst_files))
            # no effect in rst
            rst_files = (r(f) for f in silent_f2p(self.posts, 'rst', temp))
            self.assertFalse(any('<iframe' in rst for rst in rst_files))
            rst_files = (r(f) for f in silent_f2p(self.posts, 'rst', temp,
                         strip_raw=True))
            self.assertFalse(any('<iframe' in rst for rst in rst_files))

    def test_decode_html_entities_in_titles(self):
        test_posts = [post for post in self.posts if post[2] == 'html-entity-test']
        self.assertEqual(len(test_posts), 1)

        post = test_posts[0]
        title = post[0]
        self.assertTrue(title, "A normal post with some <html> entities in the"
                               " title. You can't miss them.")
        self.assertNotIn('&', title)

    def test_decode_wp_content_returns_empty(self):
        """ Check that given an empty string we return an empty string."""
        self.assertEqual(decode_wp_content(""), "")

    def test_decode_wp_content(self):
        """ Check that we can decode a wordpress content string."""
        with open(WORDPRESS_ENCODED_CONTENT_SAMPLE, 'r') as encoded_file:
            encoded_content = encoded_file.read()
            with open(WORDPRESS_DECODED_CONTENT_SAMPLE, 'r') as decoded_file:
                decoded_content = decoded_file.read()
                self.assertEqual(decode_wp_content(encoded_content, br=False), decoded_content)

    def test_preserve_verbatim_formatting(self):
        def r(f):
            with open(f) as infile:
                return infile.read()
        silent_f2p = mute(True)(fields2pelican)
        test_post = filter(lambda p: p[0].startswith("Code in List"), self.posts)
        with temporary_folder() as temp:
            md = [r(f) for f in silent_f2p(test_post, 'markdown', temp)][0]
            self.assertTrue(re.search(r'\s+a = \[1, 2, 3\]', md))
            self.assertTrue(re.search(r'\s+b = \[4, 5, 6\]', md))

            for_line = re.search(r'\s+for i in zip\(a, b\):', md).group(0)
            print_line = re.search(r'\s+print i', md).group(0)
            self.assertTrue(for_line.rindex('for') < print_line.rindex('print'))

    def test_code_in_list(self):
        def r(f):
            with open(f) as infile:
                return infile.read()
        silent_f2p = mute(True)(fields2pelican)
        test_post = filter(lambda p: p[0].startswith("Code in List"), self.posts)
        with temporary_folder() as temp:
            md = [r(f) for f in silent_f2p(test_post, 'markdown', temp)][0]
            sample_line = re.search(r'-   This is a code sample', md).group(0)
            code_line = re.search(r'\s+a = \[1, 2, 3\]', md).group(0)
            self.assertTrue(sample_line.rindex('This') < code_line.rindex('a'))


class TestBuildHeader(unittest.TestCase):
    def test_build_header(self):
        header = build_header('test', None, None, None, None, None)
        self.assertEqual(header, 'test\n####\n\n')

    def test_build_header_with_east_asian_characters(self):
        header = build_header('これは広い幅の文字だけで構成されたタイトルです',
                None, None, None, None, None)

        self.assertEqual(header,
                'これは広い幅の文字だけで構成されたタイトルです\n' +
                '##############################################\n\n')

    def test_galleries_added_to_header(self):
        header = build_header('test', None, None, None, None,
                None, ['output/test1', 'output/test2'])
        self.assertEqual(header, 'test\n####\n' + ':attachments: output/test1, '
                + 'output/test2\n\n')

    def test_galleries_added_to_markdown_header(self):
        header = build_markdown_header('test', None, None, None, None, None,
            ['output/test1', 'output/test2'])
        self.assertEqual(header, 'Title: test\n' + 'Attachments: output/test1, '
                + 'output/test2\n\n')

@unittest.skipUnless(BeautifulSoup, 'Needs BeautifulSoup module')
class TestWordpressXMLAttachements(unittest.TestCase):
    def setUp(self):
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))
        self.attachments = get_attachments(WORDPRESS_XML_SAMPLE)

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self.old_locale)

    def test_recognise_attachments(self):
        self.assertTrue(self.attachments)
        self.assertTrue(len(self.attachments.keys()) == 3)

    def test_attachments_associated_with_correct_post(self):
        self.assertTrue(self.attachments)
        for post in self.attachments.keys():
            if post is None:
                self.assertTrue(self.attachments[post][0] == 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Pelican_lakes_entrance02.jpg/240px-Pelican_lakes_entrance02.jpg')
            elif post == 'with-excerpt':
                self.assertTrue(self.attachments[post][0] == 'http://thisurlisinvalid.notarealdomain/not_an_image.jpg')
                self.assertTrue(self.attachments[post][1] == 'http://en.wikipedia.org/wiki/File:Pelikan_Walvis_Bay.jpg')
            elif post == 'with-tags':
                self.assertTrue(self.attachments[post][0] == 'http://thisurlisinvalid.notarealdomain')
            else:
                self.fail('all attachments should match to a filename or None, {}'.format(post))

    def test_download_attachments(self):
        real_file = os.path.join(CUR_DIR, 'content/article.rst')
        good_url = 'file://' + real_file
        bad_url = 'http://localhost:1/not_a_file.txt'
        silent_da = mute()(download_attachments)
        with temporary_folder() as temp:
            #locations = download_attachments(temp, [good_url, bad_url])
            locations = list(silent_da(temp, [good_url, bad_url]))
            self.assertTrue(len(locations) == 1)
            directory = locations[0]
            self.assertTrue(directory.endswith('content/article.rst'))

########NEW FILE########
__FILENAME__ = test_paginator
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import six
import locale

from pelican.tests.support import unittest, get_settings

from pelican.paginator import Paginator
from pelican.contents import Article
from pelican.settings import DEFAULT_CONFIG
from jinja2.utils import generate_lorem_ipsum

# generate one paragraph, enclosed with <p>
TEST_CONTENT = str(generate_lorem_ipsum(n=1))
TEST_SUMMARY = generate_lorem_ipsum(n=1, html=False)

class TestPage(unittest.TestCase):
    def setUp(self):
        super(TestPage, self).setUp()
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))
        self.page_kwargs = {
            'content': TEST_CONTENT,
            'context': {
                'localsiteurl': '',
            },
            'metadata': {
                'summary': TEST_SUMMARY,
                'title': 'foo bar',
                'author': 'Blogger',
            },
            'source_path': '/path/to/file/foo.ext'
        }

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self.old_locale)

    def test_save_as_preservation(self):
        settings = get_settings()
        # fix up pagination rules
        from pelican.paginator import PaginationRule
        pagination_rules = [
            PaginationRule(*r) for r in settings.get(
                'PAGINATION_PATTERNS',
                DEFAULT_CONFIG['PAGINATION_PATTERNS'],
            )
        ]
        settings['PAGINATION_PATTERNS'] = sorted(
            pagination_rules,
            key=lambda r: r[0],
        )

        object_list = [Article(**self.page_kwargs), Article(**self.page_kwargs)]
        paginator = Paginator('foobar.foo', object_list, settings)
        page = paginator.page(1)
        self.assertEqual(page.save_as, 'foobar.foo')

########NEW FILE########
__FILENAME__ = test_pelican
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
from tempfile import mkdtemp
from shutil import rmtree
import locale
import logging
import subprocess

from pelican import Pelican
from pelican.settings import read_settings
from pelican.tests.support import LoggedTestCase, mute

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_PATH = os.path.abspath(os.path.join(
        CURRENT_DIR, os.pardir, os.pardir, 'samples'))
OUTPUT_PATH = os.path.abspath(os.path.join(CURRENT_DIR, 'output'))

INPUT_PATH = os.path.join(SAMPLES_PATH, "content")
SAMPLE_CONFIG = os.path.join(SAMPLES_PATH, "pelican.conf.py")


def recursiveDiff(dcmp):
    diff = {
            'diff_files': [os.path.join(dcmp.right, f)
                for f in dcmp.diff_files],
            'left_only': [os.path.join(dcmp.right, f)
                for f in dcmp.left_only],
            'right_only': [os.path.join(dcmp.right, f)
                for f in dcmp.right_only],
            }
    for sub_dcmp in dcmp.subdirs.values():
        for k, v in recursiveDiff(sub_dcmp).items():
            diff[k] += v
    return diff


class TestPelican(LoggedTestCase):
    # general functional testing for pelican. Basically, this test case tries
    # to run pelican in different situations and see how it behaves

    def setUp(self):
        super(TestPelican, self).setUp()
        self.temp_path = mkdtemp(prefix='pelicantests.')
        self.temp_cache = mkdtemp(prefix='pelican_cache.')
        self.maxDiff = None
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))

    def tearDown(self):
        rmtree(self.temp_path)
        rmtree(self.temp_cache)
        locale.setlocale(locale.LC_ALL, self.old_locale)
        super(TestPelican, self).tearDown()

    def assertFilesEqual(self, diff):
        msg = ("some generated files differ from the expected functional "
               "tests output.\n"
               "This is probably because the HTML generated files "
               "changed. If these changes are normal, please refer "
               "to docs/contribute.rst to update the expected "
               "output of the functional tests.")

        self.assertEqual(diff['left_only'], [], msg=msg)
        self.assertEqual(diff['right_only'], [], msg=msg)
        self.assertEqual(diff['diff_files'], [], msg=msg)

    def assertDirsEqual(self, left_path, right_path):
        out, err = subprocess.Popen(
            ['git', 'diff', '--no-ext-diff', '--exit-code', '-w', left_path, right_path], env={'PAGER': ''},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        assert not out, out
        assert not err, err

    def test_basic_generation_works(self):
        # when running pelican without settings, it should pick up the default
        # ones and generate correct output without raising any exception
        settings = read_settings(path=None, override={
            'PATH': INPUT_PATH,
            'OUTPUT_PATH': self.temp_path,
            'CACHE_PATH': self.temp_cache,
            'LOCALE': locale.normalize('en_US'),
            })
        pelican = Pelican(settings=settings)
        mute(True)(pelican.run)()
        self.assertDirsEqual(self.temp_path, os.path.join(OUTPUT_PATH, 'basic'))
        self.assertLogCountEqual(
            count=3,
            msg="Unable to find.*skipping url replacement",
            level=logging.WARNING)

    def test_custom_generation_works(self):
        # the same thing with a specified set of settings should work
        settings = read_settings(path=SAMPLE_CONFIG, override={
            'PATH': INPUT_PATH,
            'OUTPUT_PATH': self.temp_path,
            'CACHE_PATH': self.temp_cache,
            'LOCALE': locale.normalize('en_US'),
            })
        pelican = Pelican(settings=settings)
        mute(True)(pelican.run)()
        self.assertDirsEqual(self.temp_path, os.path.join(OUTPUT_PATH, 'custom'))

    def test_theme_static_paths_copy(self):
        # the same thing with a specified set of settings should work
        settings = read_settings(path=SAMPLE_CONFIG, override={
            'PATH': INPUT_PATH,
            'OUTPUT_PATH': self.temp_path,
            'CACHE_PATH': self.temp_cache,
            'THEME_STATIC_PATHS': [os.path.join(SAMPLES_PATH, 'very'),
                                   os.path.join(SAMPLES_PATH, 'kinda'),
                                   os.path.join(SAMPLES_PATH, 'theme_standard')]
            })
        pelican = Pelican(settings=settings)
        mute(True)(pelican.run)()
        theme_output = os.path.join(self.temp_path, 'theme')
        extra_path = os.path.join(theme_output, 'exciting', 'new', 'files')

        for file in ['a_stylesheet', 'a_template']:
            self.assertTrue(os.path.exists(os.path.join(theme_output, file)))

        for file in ['wow!', 'boom!', 'bap!', 'zap!']:
            self.assertTrue(os.path.exists(os.path.join(extra_path, file)))

    def test_theme_static_paths_copy_single_file(self):
        # the same thing with a specified set of settings should work
        settings = read_settings(path=SAMPLE_CONFIG, override={
            'PATH': INPUT_PATH,
            'OUTPUT_PATH': self.temp_path,
            'CACHE_PATH': self.temp_cache,
            'THEME_STATIC_PATHS': [os.path.join(SAMPLES_PATH, 'theme_standard')]
            })

        pelican = Pelican(settings=settings)
        mute(True)(pelican.run)()
        theme_output = os.path.join(self.temp_path, 'theme')

        for file in ['a_stylesheet', 'a_template']:
            self.assertTrue(os.path.exists(os.path.join(theme_output, file)))

    def test_write_only_selected(self):
        """Test that only the selected files are written"""
        settings = read_settings(path=None, override={
            'PATH': INPUT_PATH,
            'OUTPUT_PATH': self.temp_path,
            'CACHE_PATH': self.temp_cache,
            'WRITE_SELECTED': [
                os.path.join(self.temp_path, 'oh-yeah.html'),
                os.path.join(self.temp_path, 'categories.html'),
                ],
            'LOCALE': locale.normalize('en_US'),
            })
        pelican = Pelican(settings=settings)
        logger = logging.getLogger()
        orig_level = logger.getEffectiveLevel()
        logger.setLevel(logging.INFO)
        mute(True)(pelican.run)()
        logger.setLevel(orig_level)
        self.assertLogCountEqual(
            count=2,
            msg="writing .*",
            level=logging.INFO)

########NEW FILE########
__FILENAME__ = test_readers
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import datetime
import os

from pelican import readers
from pelican.tests.support import unittest, get_settings

CUR_DIR = os.path.dirname(__file__)
CONTENT_PATH = os.path.join(CUR_DIR, 'content')


def _path(*args):
    return os.path.join(CONTENT_PATH, *args)


class ReaderTest(unittest.TestCase):

    def read_file(self, path, **kwargs):
        # Isolate from future API changes to readers.read_file
        r = readers.Readers(settings=get_settings(**kwargs))
        return r.read_file(base_path=CONTENT_PATH, path=path)


class DefaultReaderTest(ReaderTest):

    def test_readfile_unknown_extension(self):
        with self.assertRaises(TypeError):
            self.read_file(path='article_with_metadata.unknownextension')


class RstReaderTest(ReaderTest):

    def test_article_with_metadata(self):
        page = self.read_file(path='article_with_metadata.rst')
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'title': 'This is a super article !',
            'summary': '<p class="first last">Multi-line metadata should be'
                       ' supported\nas well as <strong>inline'
                       ' markup</strong> and stuff to &quot;typogrify'
                       '&quot;...</p>\n',
            'date': datetime.datetime(2010, 12, 2, 10, 14),
            'modified': datetime.datetime(2010, 12, 2, 10, 20),
            'tags': ['foo', 'bar', 'foobar'],
            'custom_field': 'http://notmyidea.org',
        }

        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

    def test_article_with_filename_metadata(self):
        page = self.read_file(
            path='2012-11-29_rst_w_filename_meta#foo-bar.rst',
            FILENAME_METADATA=None)
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'title': 'Rst with filename metadata',
        }
        for key, value in page.metadata.items():
            self.assertEqual(value, expected[key], key)

        page = self.read_file(
            path='2012-11-29_rst_w_filename_meta#foo-bar.rst',
            FILENAME_METADATA='(?P<date>\d{4}-\d{2}-\d{2}).*')
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'title': 'Rst with filename metadata',
            'date': datetime.datetime(2012, 11, 29),
        }
        for key, value in page.metadata.items():
            self.assertEqual(value, expected[key], key)

        page = self.read_file(
            path='2012-11-29_rst_w_filename_meta#foo-bar.rst',
            FILENAME_METADATA=(
                '(?P<date>\d{4}-\d{2}-\d{2})_'
                '_(?P<Slug>.*)'
                '#(?P<MyMeta>.*)-(?P<author>.*)'))
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'title': 'Rst with filename metadata',
            'date': datetime.datetime(2012, 11, 29),
            'slug': 'article_with_filename_metadata',
            'mymeta': 'foo',
        }
        for key, value in page.metadata.items():
            self.assertEqual(value, expected[key], key)

    def test_article_metadata_key_lowercase(self):
        # Keys of metadata should be lowercase.
        reader = readers.RstReader(settings=get_settings())
        content, metadata = reader.read(
            _path('article_with_uppercase_metadata.rst'))

        self.assertIn('category', metadata, 'Key should be lowercase.')
        self.assertEqual('Yeah', metadata.get('category'),
                         'Value keeps case.')

    def test_typogrify(self):
        # if nothing is specified in the settings, the content should be
        # unmodified
        page = self.read_file(path='article.rst')
        expected = ('<p>THIS is some content. With some stuff to '
                    '&quot;typogrify&quot;...</p>\n<p>Now with added '
                    'support for <abbr title="three letter acronym">'
                    'TLA</abbr>.</p>\n')

        self.assertEqual(page.content, expected)

        try:
            # otherwise, typogrify should be applied
            page = self.read_file(path='article.rst', TYPOGRIFY=True)
            expected = (
                '<p><span class="caps">THIS</span> is some content. '
                'With some stuff to&nbsp;&quot;typogrify&quot;&#8230;</p>\n'
                '<p>Now with added support for <abbr title="three letter '
                'acronym"><span class="caps">TLA</span></abbr>.</p>\n')

            self.assertEqual(page.content, expected)
        except ImportError:
            return unittest.skip('need the typogrify distribution')

    def test_typogrify_summary(self):
        # if nothing is specified in the settings, the summary should be
        # unmodified
        page = self.read_file(path='article_with_metadata.rst')
        expected = ('<p class="first last">Multi-line metadata should be'
                    ' supported\nas well as <strong>inline'
                    ' markup</strong> and stuff to &quot;typogrify'
                    '&quot;...</p>\n')

        self.assertEqual(page.metadata['summary'], expected)

        try:
            # otherwise, typogrify should be applied
            page = self.read_file(path='article_with_metadata.rst',
                                  TYPOGRIFY=True)
            expected = ('<p class="first last">Multi-line metadata should be'
                        ' supported\nas well as <strong>inline'
                        ' markup</strong> and stuff to&nbsp;&quot;typogrify'
                        '&quot;&#8230;</p>\n')

            self.assertEqual(page.metadata['summary'], expected)
        except ImportError:
            return unittest.skip('need the typogrify distribution')

    def test_article_with_multiple_authors(self):
        page = self.read_file(path='article_with_multiple_authors.rst')
        expected = {
            'authors': ['First Author', 'Second Author']
        }

        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)


class MdReaderTest(ReaderTest):

    @unittest.skipUnless(readers.Markdown, "markdown isn't installed")
    def test_article_with_metadata(self):
        reader = readers.MarkdownReader(settings=get_settings())
        content, metadata = reader.read(
            _path('article_with_md_extension.md'))
        expected = {
            'category': 'test',
            'title': 'Test md File',
            'summary': '<p>I have a lot to test</p>',
            'date': datetime.datetime(2010, 12, 2, 10, 14),
            'modified': datetime.datetime(2010, 12, 2, 10, 20),
            'tags': ['foo', 'bar', 'foobar'],
        }
        for key, value in metadata.items():
            self.assertEqual(value, expected[key], key)

        content, metadata = reader.read(
            _path('article_with_markdown_and_nonascii_summary.md'))
        expected = {
            'title': 'マックOS X 10.8でパイソンとVirtualenvをインストールと設定',
            'summary': '<p>パイソンとVirtualenvをまっくでインストールする方法について明確に説明します。</p>',
            'category': '指導書',
            'date': datetime.datetime(2012, 12, 20),
            'modified': datetime.datetime(2012, 12, 22),
            'tags': ['パイソン', 'マック'],
            'slug': 'python-virtualenv-on-mac-osx-mountain-lion-10.8',
        }
        for key, value in metadata.items():
            self.assertEqual(value, expected[key], key)

    @unittest.skipUnless(readers.Markdown, "markdown isn't installed")
    def test_article_with_footnote(self):
        reader = readers.MarkdownReader(settings=get_settings())
        content, metadata = reader.read(
            _path('article_with_markdown_and_footnote.md'))
        expected_content = (
            '<p>This is some content'
            '<sup id="fnref:1"><a class="footnote-ref" href="#fn:1" '
            'rel="footnote">1</a></sup>'
            ' with some footnotes'
            '<sup id="fnref:footnote"><a class="footnote-ref" '
            'href="#fn:footnote" rel="footnote">2</a></sup></p>\n'

            '<div class="footnote">\n'
            '<hr />\n<ol>\n<li id="fn:1">\n'
            '<p>Numbered footnote&#160;'
            '<a class="footnote-backref" href="#fnref:1" rev="footnote" '
            'title="Jump back to footnote 1 in the text">&#8617;</a></p>\n'
            '</li>\n<li id="fn:footnote">\n'
            '<p>Named footnote&#160;'
            '<a class="footnote-backref" href="#fnref:footnote" rev="footnote"'
            ' title="Jump back to footnote 2 in the text">&#8617;</a></p>\n'
            '</li>\n</ol>\n</div>')
        expected_metadata = {
            'title': 'Article with markdown containing footnotes',
            'summary': (
                '<p>Summary with <strong>inline</strong> markup '
                '<em>should</em> be supported.</p>'),
            'date': datetime.datetime(2012, 10, 31),
            'modified': datetime.datetime(2012, 11, 1),
            'slug': 'article-with-markdown-containing-footnotes',
            'multiline': [
                'Line Metadata should be handle properly.',
                'See syntax of Meta-Data extension of Python Markdown package:',
                'If a line is indented by 4 or more spaces,',
                'that line is assumed to be an additional line of the value',
                'for the previous keyword.',
                'A keyword may have as many lines as desired.',
            ]
        }
        self.assertEqual(content, expected_content)
        for key, value in metadata.items():
            self.assertEqual(value, expected_metadata[key], key)

    @unittest.skipUnless(readers.Markdown, "markdown isn't installed")
    def test_article_with_file_extensions(self):
        reader = readers.MarkdownReader(settings=get_settings())
        # test to ensure the md file extension is being processed by the
        # correct reader
        content, metadata = reader.read(
            _path('article_with_md_extension.md'))
        expected = (
            "<h1>Test Markdown File Header</h1>\n"
            "<h2>Used for pelican test</h2>\n"
            "<p>The quick brown fox jumped over the lazy dog's back.</p>")
        self.assertEqual(content, expected)
        # test to ensure the mkd file extension is being processed by the
        # correct reader
        content, metadata = reader.read(
            _path('article_with_mkd_extension.mkd'))
        expected = ("<h1>Test Markdown File Header</h1>\n<h2>Used for pelican"
                    " test</h2>\n<p>This is another markdown test file.  Uses"
                    " the mkd extension.</p>")
        self.assertEqual(content, expected)
        # test to ensure the markdown file extension is being processed by the
        # correct reader
        content, metadata = reader.read(
            _path('article_with_markdown_extension.markdown'))
        expected = ("<h1>Test Markdown File Header</h1>\n<h2>Used for pelican"
                    " test</h2>\n<p>This is another markdown test file.  Uses"
                    " the markdown extension.</p>")
        self.assertEqual(content, expected)
        # test to ensure the mdown file extension is being processed by the
        # correct reader
        content, metadata = reader.read(
            _path('article_with_mdown_extension.mdown'))
        expected = ("<h1>Test Markdown File Header</h1>\n<h2>Used for pelican"
                    " test</h2>\n<p>This is another markdown test file.  Uses"
                    " the mdown extension.</p>")
        self.assertEqual(content, expected)

    @unittest.skipUnless(readers.Markdown, "markdown isn't installed")
    def test_article_with_markdown_markup_extension(self):
        # test to ensure the markdown markup extension is being processed as
        # expected
        page = self.read_file(
            path='article_with_markdown_markup_extensions.md',
            MD_EXTENSIONS=['toc', 'codehilite', 'extra'])
        expected = ('<div class="toc">\n'
                    '<ul>\n'
                    '<li><a href="#level1">Level1</a><ul>\n'
                    '<li><a href="#level2">Level2</a></li>\n'
                    '</ul>\n'
                    '</li>\n'
                    '</ul>\n'
                    '</div>\n'
                    '<h2 id="level1">Level1</h2>\n'
                    '<h3 id="level2">Level2</h3>')

        self.assertEqual(page.content, expected)

    @unittest.skipUnless(readers.Markdown, "markdown isn't installed")
    def test_article_with_filename_metadata(self):
        page = self.read_file(
            path='2012-11-30_md_w_filename_meta#foo-bar.md',
            FILENAME_METADATA=None)
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
        }
        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

        page = self.read_file(
            path='2012-11-30_md_w_filename_meta#foo-bar.md',
            FILENAME_METADATA='(?P<date>\d{4}-\d{2}-\d{2}).*')
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'date': datetime.datetime(2012, 11, 30),
        }
        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

        page = self.read_file(
            path='2012-11-30_md_w_filename_meta#foo-bar.md',
            FILENAME_METADATA=(
                '(?P<date>\d{4}-\d{2}-\d{2})'
                '_(?P<Slug>.*)'
                '#(?P<MyMeta>.*)-(?P<author>.*)'))
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'date': datetime.datetime(2012, 11, 30),
            'slug': 'md_w_filename_meta',
            'mymeta': 'foo',
        }
        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)


class AdReaderTest(ReaderTest):

    @unittest.skipUnless(readers.asciidoc, "asciidoc isn't installed")
    def test_article_with_asc_extension(self):
        # Ensure the asc extension is being processed by the correct reader
        page = self.read_file(
            path='article_with_asc_extension.asc')
        expected = ('<hr>\n<h2><a name="_used_for_pelican_test">'
                    '</a>Used for pelican test</h2>\n'
                    '<p>The quick brown fox jumped over'
                    ' the lazy dog&#8217;s back.</p>\n')
        self.assertEqual(page.content, expected)
        expected = {
            'category': 'Blog',
            'author': 'Author O. Article',
            'title': 'Test AsciiDoc File Header',
            'date': datetime.datetime(2011, 9, 15, 9, 5),
            'tags': ['Linux', 'Python', 'Pelican'],
        }

        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

    @unittest.skipUnless(readers.asciidoc, "asciidoc isn't installed")
    def test_article_with_asc_options(self):
        # test to ensure the ASCIIDOC_OPTIONS is being used
        reader = readers.AsciiDocReader(
            dict(ASCIIDOC_OPTIONS=["-a revision=1.0.42"]))
        content, metadata = reader.read(_path('article_with_asc_options.asc'))
        expected = ('<hr>\n<h2><a name="_used_for_pelican_test"></a>Used for'
                    ' pelican test</h2>\n<p>version 1.0.42</p>\n'
                    '<p>The quick brown fox jumped over the lazy'
                    ' dog&#8217;s back.</p>\n')
        self.assertEqual(content, expected)


class HTMLReaderTest(ReaderTest):
    def test_article_with_comments(self):
        page = self.read_file(path='article_with_comments.html')

        self.assertEqual('''
        Body content
        <!--  This comment is included (including extra whitespace)   -->
    ''', page.content)

    def test_article_with_keywords(self):
        page = self.read_file(path='article_with_keywords.html')
        expected = {
            'tags': ['foo', 'bar', 'foobar'],
        }

        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

    def test_article_with_metadata(self):
        page = self.read_file(path='article_with_metadata.html')
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'title': 'This is a super article !',
            'summary': 'Summary and stuff',
            'date': datetime.datetime(2010, 12, 2, 10, 14),
            'tags': ['foo', 'bar', 'foobar'],
            'custom_field': 'http://notmyidea.org',
        }

        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

    def test_article_with_multiple_authors(self):
        page = self.read_file(path='article_with_multiple_authors.html')
        expected = {
            'authors': ['First Author', 'Second Author']
        }

        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

    def test_article_with_metadata_and_contents_attrib(self):
        page = self.read_file(path='article_with_metadata_and_contents.html')
        expected = {
            'category': 'yeah',
            'author': 'Alexis Métaireau',
            'title': 'This is a super article !',
            'summary': 'Summary and stuff',
            'date': datetime.datetime(2010, 12, 2, 10, 14),
            'tags': ['foo', 'bar', 'foobar'],
            'custom_field': 'http://notmyidea.org',
        }
        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

    def test_article_with_null_attributes(self):
        page = self.read_file(path='article_with_null_attributes.html')

        self.assertEqual('''
        Ensure that empty attributes are copied properly.
        <input name="test" disabled style="" />
    ''', page.content)

    def test_article_metadata_key_lowercase(self):
        # Keys of metadata should be lowercase.
        page = self.read_file(path='article_with_uppercase_metadata.html')
        self.assertIn('category', page.metadata, 'Key should be lowercase.')
        self.assertEqual('Yeah', page.metadata.get('category'),
                         'Value keeps cases.')

    def test_article_with_nonconformant_meta_tags(self):
        page = self.read_file(path='article_with_nonconformant_meta_tags.html')
        expected = {
            'summary': 'Summary and stuff',
            'title': 'Article with Nonconformant HTML meta tags',
        }

        for key, value in expected.items():
            self.assertEqual(value, page.metadata[key], key)

########NEW FILE########
__FILENAME__ = test_settings
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import copy
import os
import locale
from os.path import dirname, abspath, join

from pelican.settings import (read_settings, configure_settings,
                              DEFAULT_CONFIG, DEFAULT_THEME)
from pelican.tests.support import unittest


class TestSettingsConfiguration(unittest.TestCase):
    """Provided a file, it should read it, replace the default values,
    append new values to the settings (if any), and apply basic settings
    optimizations.
    """
    def setUp(self):
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))
        self.PATH = abspath(dirname(__file__))
        default_conf = join(self.PATH, 'default_conf.py')
        self.settings = read_settings(default_conf)

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self.old_locale)

    def test_overwrite_existing_settings(self):
        self.assertEqual(self.settings.get('SITENAME'), "Alexis' log")
        self.assertEqual(self.settings.get('SITEURL'),
                'http://blog.notmyidea.org')

    def test_keep_default_settings(self):
        # Keep default settings if not defined.
        self.assertEqual(self.settings.get('DEFAULT_CATEGORY'),
            DEFAULT_CONFIG['DEFAULT_CATEGORY'])

    def test_dont_copy_small_keys(self):
        # Do not copy keys not in caps.
        self.assertNotIn('foobar', self.settings)

    def test_read_empty_settings(self):
        # Providing no file should return the default values.
        settings = read_settings(None)
        expected = copy.deepcopy(DEFAULT_CONFIG)
        expected['FEED_DOMAIN'] = ''  # Added by configure settings
        self.maxDiff = None
        self.assertDictEqual(settings, expected)

    def test_settings_return_independent(self):
        # Make sure that the results from one settings call doesn't
        # effect past or future instances.
        self.PATH = abspath(dirname(__file__))
        default_conf = join(self.PATH, 'default_conf.py')
        settings = read_settings(default_conf)
        settings['SITEURL'] = 'new-value'
        new_settings = read_settings(default_conf)
        self.assertNotEqual(new_settings['SITEURL'], settings['SITEURL'])

    def test_defaults_not_overwritten(self):
        # This assumes 'SITENAME': 'A Pelican Blog'
        settings = read_settings(None)
        settings['SITENAME'] = 'Not a Pelican Blog'
        self.assertNotEqual(settings['SITENAME'], DEFAULT_CONFIG['SITENAME'])

    def test_path_settings_safety(self):
        """Don't let people setting the static path listings to strs"""
        settings = {'STATIC_PATHS': 'foo/bar',
                'THEME_STATIC_PATHS': 'bar/baz',
                # These 4 settings are required to run configure_settings
                'PATH': '.',
                'THEME': DEFAULT_THEME,
                'SITEURL': 'http://blog.notmyidea.org/',
                'LOCALE': '',
                }
        configure_settings(settings)
        self.assertEqual(settings['STATIC_PATHS'],
                DEFAULT_CONFIG['STATIC_PATHS'])
        self.assertEqual(settings['THEME_STATIC_PATHS'],
                DEFAULT_CONFIG['THEME_STATIC_PATHS'])

    def test_configure_settings(self):
        #Manipulations to settings should be applied correctly.

        settings = {
                'SITEURL': 'http://blog.notmyidea.org/',
                'LOCALE': '',
                'PATH': os.curdir,
                'THEME': DEFAULT_THEME,
                }
        configure_settings(settings)
        # SITEURL should not have a trailing slash
        self.assertEqual(settings['SITEURL'], 'http://blog.notmyidea.org')

        # FEED_DOMAIN, if undefined, should default to SITEURL
        self.assertEqual(settings['FEED_DOMAIN'], 'http://blog.notmyidea.org')

        settings['FEED_DOMAIN'] = 'http://feeds.example.com'
        configure_settings(settings)
        self.assertEqual(settings['FEED_DOMAIN'], 'http://feeds.example.com')

    def test_default_encoding(self):
        # test that the default locale is set if
        # locale is not specified in the settings

        #reset locale to python default
        locale.setlocale(locale.LC_ALL, str('C'))
        self.assertEqual(self.settings['LOCALE'], DEFAULT_CONFIG['LOCALE'])

        configure_settings(self.settings)
        self.assertEqual(locale.getlocale(), locale.getdefaultlocale())

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import
import logging
import shutil
import os
import datetime
import time
import locale
from sys import platform, version_info
from tempfile import mkdtemp

import pytz

from pelican.generators import TemplatePagesGenerator
from pelican.writers import Writer
from pelican.settings import read_settings
from pelican import utils
from pelican.tests.support import get_article, LoggedTestCase, locale_available, unittest


class TestUtils(LoggedTestCase):
    _new_attribute = 'new_value'

    @utils.deprecated_attribute(
        old='_old_attribute', new='_new_attribute',
        since=(3, 1, 0), remove=(4, 1, 3))
    def _old_attribute():
        return None

    def test_deprecated_attribute(self):
        value = self._old_attribute
        self.assertEqual(value, self._new_attribute)
        self.assertLogCountEqual(
            count=1,
            msg=('_old_attribute has been deprecated since 3.1.0 and will be '
                 'removed by version 4.1.3.  Use _new_attribute instead'),
            level=logging.WARNING)

    def test_get_date(self):
        # valid ones
        date = datetime.datetime(year=2012, month=11, day=22)
        date_hour = datetime.datetime(
            year=2012, month=11, day=22, hour=22, minute=11)
        date_hour_z = datetime.datetime(
            year=2012, month=11, day=22, hour=22, minute=11,
            tzinfo=pytz.timezone('UTC'))
        date_hour_est = datetime.datetime(
            year=2012, month=11, day=22, hour=22, minute=11,
            tzinfo=pytz.timezone('EST'))
        date_hour_sec = datetime.datetime(
            year=2012, month=11, day=22, hour=22, minute=11, second=10)
        date_hour_sec_z = datetime.datetime(
            year=2012, month=11, day=22, hour=22, minute=11, second=10,
            tzinfo=pytz.timezone('UTC'))
        date_hour_sec_est = datetime.datetime(
            year=2012, month=11, day=22, hour=22, minute=11, second=10,
            tzinfo=pytz.timezone('EST'))
        date_hour_sec_frac_z = datetime.datetime(
            year=2012, month=11, day=22, hour=22, minute=11, second=10,
            microsecond=123000, tzinfo=pytz.timezone('UTC'))
        dates = {
            '2012-11-22': date,
            '2012/11/22': date,
            '2012-11-22 22:11': date_hour,
            '2012/11/22 22:11': date_hour,
            '22-11-2012': date,
            '22/11/2012': date,
            '22.11.2012': date,
            '22.11.2012 22:11': date_hour,
            '2012-11-22T22:11Z': date_hour_z,
            '2012-11-22T22:11-0500': date_hour_est,
            '2012-11-22 22:11:10': date_hour_sec,
            '2012-11-22T22:11:10Z': date_hour_sec_z,
            '2012-11-22T22:11:10-0500': date_hour_sec_est,
            '2012-11-22T22:11:10.123Z': date_hour_sec_frac_z,
            }

        # examples from http://www.w3.org/TR/NOTE-datetime
        iso_8601_date = datetime.datetime(year=1997, month=7, day=16)
        iso_8601_date_hour_tz = datetime.datetime(
            year=1997, month=7, day=16, hour=19, minute=20,
            tzinfo=pytz.timezone('CET'))
        iso_8601_date_hour_sec_tz = datetime.datetime(
            year=1997, month=7, day=16, hour=19, minute=20, second=30,
            tzinfo=pytz.timezone('CET'))
        iso_8601_date_hour_sec_ms_tz = datetime.datetime(
            year=1997, month=7, day=16, hour=19, minute=20, second=30,
            microsecond=450000, tzinfo=pytz.timezone('CET'))
        iso_8601 = {
            '1997-07-16': iso_8601_date,
            '1997-07-16T19:20+01:00': iso_8601_date_hour_tz,
            '1997-07-16T19:20:30+01:00': iso_8601_date_hour_sec_tz,
            '1997-07-16T19:20:30.45+01:00': iso_8601_date_hour_sec_ms_tz,
        }

        # invalid ones
        invalid_dates = ['2010-110-12', 'yay']


        for value, expected in dates.items():
            self.assertEqual(utils.get_date(value), expected, value)

        for value, expected in iso_8601.items():
            self.assertEqual(utils.get_date(value), expected, value)

        for item in invalid_dates:
            self.assertRaises(ValueError, utils.get_date, item)

    def test_slugify(self):

        samples = (('this is a test', 'this-is-a-test'),
                   ('this        is a test', 'this-is-a-test'),
                   ('this → is ← a ↑ test', 'this-is-a-test'),
                   ('this--is---a test', 'this-is-a-test'),
                   ('unicode測試許功蓋，你看到了嗎？',
                    'unicodece-shi-xu-gong-gai-ni-kan-dao-liao-ma'),
                   ('大飯原発４号機、１８日夜起動へ',
                    'da-fan-yuan-fa-4hao-ji-18ri-ye-qi-dong-he'),)

        for value, expected in samples:
            self.assertEqual(utils.slugify(value), expected)

    def test_slugify_substitute(self):

        samples = (('C++ is based on C', 'cpp-is-based-on-c'),
                   ('C+++ test C+ test', 'cpp-test-c-test'),
                   ('c++, c#, C#, C++', 'cpp-c-sharp-c-sharp-cpp'),
                   ('c++-streams', 'cpp-streams'),)

        subs = (('C++', 'CPP'), ('C#', 'C-SHARP'))
        for value, expected in samples:
            self.assertEqual(utils.slugify(value, subs), expected)

    def test_get_relative_path(self):

        samples = ((os.path.join('test', 'test.html'), os.pardir),
                   (os.path.join('test', 'test', 'test.html'),
                    os.path.join(os.pardir, os.pardir)),
                   ('test.html', os.curdir),
                   (os.path.join('/test', 'test.html'), os.pardir),
                   (os.path.join('/test', 'test', 'test.html'),
                    os.path.join(os.pardir, os.pardir)),
                   ('/test.html', os.curdir),)

        for value, expected in samples:
            self.assertEqual(utils.get_relative_path(value), expected)

    def test_process_translations(self):
        # create a bunch of articles
        # 1: no translation metadata
        fr_article1 = get_article(lang='fr', slug='yay', title='Un titre',
                                  content='en français')
        en_article1 = get_article(lang='en', slug='yay', title='A title',
                                  content='in english')
        # 2: reverse which one is the translation thanks to metadata
        fr_article2 = get_article(lang='fr', slug='yay2', title='Un titre',
                                  content='en français')
        en_article2 = get_article(lang='en', slug='yay2', title='A title',
                                  content='in english',
                                  extra_metadata={'translation': 'true'})
        # 3: back to default language detection if all items have the
        #    translation metadata
        fr_article3 = get_article(lang='fr', slug='yay3', title='Un titre',
                                  content='en français',
                                  extra_metadata={'translation': 'yep'})
        en_article3 = get_article(lang='en', slug='yay3', title='A title',
                                  content='in english',
                                  extra_metadata={'translation': 'yes'})

        articles = [fr_article1, en_article1, fr_article2, en_article2,
                    fr_article3, en_article3]

        index, trans = utils.process_translations(articles)

        self.assertIn(en_article1, index)
        self.assertIn(fr_article1, trans)
        self.assertNotIn(en_article1, trans)
        self.assertNotIn(fr_article1, index)

        self.assertIn(fr_article2, index)
        self.assertIn(en_article2, trans)
        self.assertNotIn(fr_article2, trans)
        self.assertNotIn(en_article2, index)

        self.assertIn(en_article3, index)
        self.assertIn(fr_article3, trans)
        self.assertNotIn(en_article3, trans)
        self.assertNotIn(fr_article3, index)

    def test_watchers(self):
        # Test if file changes are correctly detected
        # Make sure to handle not getting any files correctly.

        dirname = os.path.join(os.path.dirname(__file__), 'content')
        folder_watcher = utils.folder_watcher(dirname, ['rst'])

        path = os.path.join(dirname, 'article_with_metadata.rst')
        file_watcher = utils.file_watcher(path)

        # first check returns True
        self.assertEqual(next(folder_watcher), True)
        self.assertEqual(next(file_watcher), True)

        # next check without modification returns False
        self.assertEqual(next(folder_watcher), False)
        self.assertEqual(next(file_watcher), False)

        # after modification, returns True
        t = time.time()
        os.utime(path, (t, t))
        self.assertEqual(next(folder_watcher), True)
        self.assertEqual(next(file_watcher), True)

        # file watcher with None or empty path should return None
        self.assertEqual(next(utils.file_watcher('')), None)
        self.assertEqual(next(utils.file_watcher(None)), None)

        empty_path = os.path.join(os.path.dirname(__file__), 'empty')
        try:
            os.mkdir(empty_path)
            os.mkdir(os.path.join(empty_path, "empty_folder"))
            shutil.copy(__file__, empty_path)

            # if no files of interest, returns None
            watcher = utils.folder_watcher(empty_path, ['rst'])
            self.assertEqual(next(watcher), None)
        except OSError:
            self.fail("OSError Exception in test_files_changed test")
        finally:
            shutil.rmtree(empty_path, True)

    def test_clean_output_dir(self):
        retention = ()
        test_directory = os.path.join(os.path.dirname(__file__),
                                      'clean_output')
        content = os.path.join(os.path.dirname(__file__), 'content')
        shutil.copytree(content, test_directory)
        utils.clean_output_dir(test_directory, retention)
        self.assertTrue(os.path.isdir(test_directory))
        self.assertListEqual([], os.listdir(test_directory))
        shutil.rmtree(test_directory)

    def test_clean_output_dir_not_there(self):
        retention = ()
        test_directory = os.path.join(os.path.dirname(__file__),
                                      'does_not_exist')
        utils.clean_output_dir(test_directory, retention)
        self.assertFalse(os.path.exists(test_directory))

    def test_clean_output_dir_is_file(self):
        retention = ()
        test_directory = os.path.join(os.path.dirname(__file__),
                                      'this_is_a_file')
        f = open(test_directory, 'w')
        f.write('')
        f.close()
        utils.clean_output_dir(test_directory, retention)
        self.assertFalse(os.path.exists(test_directory))

    def test_strftime(self):
        d = datetime.date(2012, 8, 29)

        # simple formatting
        self.assertEqual(utils.strftime(d, '%d/%m/%y'), '29/08/12')
        self.assertEqual(utils.strftime(d, '%d/%m/%Y'), '29/08/2012')

        # % escaped
        self.assertEqual(utils.strftime(d, '%d%%%m%%%y'), '29%08%12')
        self.assertEqual(utils.strftime(d, '%d %% %m %% %y'), '29 % 08 % 12')
        # not valid % formatter
        self.assertEqual(utils.strftime(d, '10% reduction in %Y'),
                         '10% reduction in 2012')
        self.assertEqual(utils.strftime(d, '%10 reduction in %Y'),
                         '%10 reduction in 2012')

        # with text
        self.assertEqual(utils.strftime(d, 'Published in %d-%m-%Y'),
                         'Published in 29-08-2012')

        # with non-ascii text
        self.assertEqual(utils.strftime(d, '%d/%m/%Y Øl trinken beim Besäufnis'),
                         '29/08/2012 Øl trinken beim Besäufnis')


    # test the output of utils.strftime in a different locale
    # Turkish locale
    @unittest.skipUnless(locale_available('tr_TR.UTF-8') or
                         locale_available('Turkish'),
                         'Turkish locale needed')
    def test_strftime_locale_dependent_turkish(self):
        # store current locale
        old_locale = locale.setlocale(locale.LC_TIME)

        if platform == 'win32':
            locale.setlocale(locale.LC_TIME, str('Turkish'))
        else:
            locale.setlocale(locale.LC_TIME, str('tr_TR.UTF-8'))

        d = datetime.date(2012, 8, 29)

        # simple
        self.assertEqual(utils.strftime(d, '%d %B %Y'), '29 Ağustos 2012')
        self.assertEqual(utils.strftime(d, '%A, %d %B %Y'),
                         'Çarşamba, 29 Ağustos 2012')

        # with text
        self.assertEqual(utils.strftime(d, 'Yayınlanma tarihi: %A, %d %B %Y'),
            'Yayınlanma tarihi: Çarşamba, 29 Ağustos 2012')

        # non-ascii format candidate (someone might pass it... for some reason)
        self.assertEqual(utils.strftime(d, '%Y yılında %üretim artışı'),
            '2012 yılında %üretim artışı')

        # restore locale back
        locale.setlocale(locale.LC_TIME, old_locale)


    # test the output of utils.strftime in a different locale
    # French locale
    @unittest.skipUnless(locale_available('fr_FR.UTF-8') or
                         locale_available('French'),
                         'French locale needed')
    def test_strftime_locale_dependent_french(self):
        # store current locale
        old_locale = locale.setlocale(locale.LC_TIME)

        if platform == 'win32':
            locale.setlocale(locale.LC_TIME, str('French'))
        else:
            locale.setlocale(locale.LC_TIME, str('fr_FR.UTF-8'))

        d = datetime.date(2012, 8, 29)

        # simple
        self.assertEqual(utils.strftime(d, '%d %B %Y'), '29 août 2012')

        # depending on OS, the first letter is m or M
        self.assertTrue(utils.strftime(d, '%A') in ('mercredi', 'Mercredi'))

        # with text
        self.assertEqual(utils.strftime(d, 'Écrit le %d %B %Y'),
            'Écrit le 29 août 2012')

        # non-ascii format candidate (someone might pass it... for some reason)
        self.assertEqual(utils.strftime(d, '%écrits en %Y'),
            '%écrits en 2012')

        # restore locale back
        locale.setlocale(locale.LC_TIME, old_locale)


class TestCopy(unittest.TestCase):
    '''Tests the copy utility'''

    def setUp(self):
        self.root_dir = mkdtemp(prefix='pelicantests.')
        self.old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))

    def tearDown(self):
        shutil.rmtree(self.root_dir)
        locale.setlocale(locale.LC_ALL, self.old_locale)

    def _create_file(self, *path):
        with open(os.path.join(self.root_dir, *path), 'w') as f:
            f.write('42\n')

    def _create_dir(self, *path):
        os.makedirs(os.path.join(self.root_dir, *path))

    def _exist_file(self, *path):
        path = os.path.join(self.root_dir, *path)
        self.assertTrue(os.path.isfile(path), 'File does not exist: %s' % path)

    def _exist_dir(self, *path):
        path = os.path.join(self.root_dir, *path)
        self.assertTrue(os.path.exists(path),
                        'Directory does not exist: %s' % path)

    def test_copy_file_same_path(self):
        self._create_file('a.txt')
        utils.copy(os.path.join(self.root_dir, 'a.txt'),
                   os.path.join(self.root_dir, 'b.txt'))
        self._exist_file('b.txt')

    def test_copy_file_different_path(self):
        self._create_dir('a')
        self._create_dir('b')
        self._create_file('a', 'a.txt')
        utils.copy(os.path.join(self.root_dir, 'a', 'a.txt'),
                   os.path.join(self.root_dir, 'b', 'b.txt'))
        self._exist_dir('b')
        self._exist_file('b', 'b.txt')

    def test_copy_file_create_dirs(self):
        self._create_file('a.txt')
        utils.copy(os.path.join(self.root_dir, 'a.txt'),
                   os.path.join(self.root_dir, 'b0', 'b1', 'b2', 'b3', 'b.txt'))
        self._exist_dir('b0')
        self._exist_dir('b0', 'b1')
        self._exist_dir('b0', 'b1', 'b2')
        self._exist_dir('b0', 'b1', 'b2', 'b3')
        self._exist_file('b0', 'b1', 'b2', 'b3', 'b.txt')

    def test_copy_dir_same_path(self):
        self._create_dir('a')
        self._create_file('a', 'a.txt')
        utils.copy(os.path.join(self.root_dir, 'a'),
                   os.path.join(self.root_dir, 'b'))
        self._exist_dir('b')
        self._exist_file('b', 'a.txt')

    def test_copy_dir_different_path(self):
        self._create_dir('a0')
        self._create_dir('a0', 'a1')
        self._create_file('a0', 'a1', 'a.txt')
        self._create_dir('b0')
        utils.copy(os.path.join(self.root_dir, 'a0', 'a1'),
                   os.path.join(self.root_dir, 'b0', 'b1'))
        self._exist_dir('b0', 'b1')
        self._exist_file('b0', 'b1', 'a.txt')

    def test_copy_dir_create_dirs(self):
        self._create_dir('a')
        self._create_file('a', 'a.txt')
        utils.copy(os.path.join(self.root_dir, 'a'),
                   os.path.join(self.root_dir, 'b0', 'b1', 'b2', 'b3', 'b'))
        self._exist_dir('b0')
        self._exist_dir('b0', 'b1')
        self._exist_dir('b0', 'b1', 'b2')
        self._exist_dir('b0', 'b1', 'b2', 'b3')
        self._exist_dir('b0', 'b1', 'b2', 'b3', 'b')
        self._exist_file('b0', 'b1', 'b2', 'b3', 'b', 'a.txt')


class TestDateFormatter(unittest.TestCase):
    '''Tests that the output of DateFormatter jinja filter is same as
    utils.strftime'''

    def setUp(self):
        # prepare a temp content and output folder
        self.temp_content = mkdtemp(prefix='pelicantests.')
        self.temp_output = mkdtemp(prefix='pelicantests.')

        # prepare a template file
        template_dir = os.path.join(self.temp_content, 'template')
        template_path = os.path.join(template_dir, 'source.html')
        os.makedirs(template_dir)
        with open(template_path, 'w') as template_file:
            template_file.write('date = {{ date|strftime("%A, %d %B %Y") }}')
        self.date = datetime.date(2012, 8, 29)


    def tearDown(self):
        shutil.rmtree(self.temp_content)
        shutil.rmtree(self.temp_output)
        # reset locale to default
        locale.setlocale(locale.LC_ALL, '')


    @unittest.skipUnless(locale_available('fr_FR.UTF-8') or
                         locale_available('French'),
                         'French locale needed')
    def test_french_strftime(self):
        # This test tries to reproduce an issue that occured with python3.3 under macos10 only
        locale.setlocale(locale.LC_ALL, str('fr_FR.UTF-8'))
        date = datetime.datetime(2014,8,14)
        # we compare the lower() dates since macos10 returns "Jeudi" for %A whereas linux reports "jeudi"
        self.assertEqual( u'jeudi, 14 août 2014', utils.strftime(date, date_format="%A, %d %B %Y").lower() )
        df = utils.DateFormatter()
        self.assertEqual( u'jeudi, 14 août 2014', df(date, date_format="%A, %d %B %Y").lower() )
        # Let us now set the global locale to C:
        locale.setlocale(locale.LC_ALL, str('C'))
        # DateFormatter should still work as expected since it is the whole point of DateFormatter
        # (This is where pre-2014/4/15 code fails on macos10)
        df_date = df(date, date_format="%A, %d %B %Y").lower()
        self.assertEqual( u'jeudi, 14 août 2014', df_date )


    @unittest.skipUnless(locale_available('fr_FR.UTF-8') or
                         locale_available('French'),
                         'French locale needed')
    def test_french_locale(self):
        settings = read_settings(
            override={'LOCALE': locale.normalize('fr_FR.UTF-8'),
                      'TEMPLATE_PAGES': {'template/source.html':
                                         'generated/file.html'}})

        generator = TemplatePagesGenerator(
            {'date': self.date}, settings,
            self.temp_content, '', self.temp_output)
        generator.env.filters.update({'strftime': utils.DateFormatter()})

        writer = Writer(self.temp_output, settings=settings)
        generator.generate_output(writer)

        output_path = os.path.join(
                self.temp_output, 'generated', 'file.html')

        # output file has been generated
        self.assertTrue(os.path.exists(output_path))

        # output content is correct
        with utils.pelican_open(output_path) as output_file:
            self.assertEqual(output_file,
                             utils.strftime(self.date, 'date = %A, %d %B %Y'))


    @unittest.skipUnless(locale_available('tr_TR.UTF-8') or
                         locale_available('Turkish'),
                         'Turkish locale needed')
    def test_turkish_locale(self):
        settings = read_settings(
            override = {'LOCALE': locale.normalize('tr_TR.UTF-8'),
                        'TEMPLATE_PAGES': {'template/source.html':
                                           'generated/file.html'}})

        generator = TemplatePagesGenerator(
            {'date': self.date}, settings,
            self.temp_content, '', self.temp_output)
        generator.env.filters.update({'strftime': utils.DateFormatter()})

        writer = Writer(self.temp_output, settings=settings)
        generator.generate_output(writer)

        output_path = os.path.join(
                self.temp_output, 'generated', 'file.html')

        # output file has been generated
        self.assertTrue(os.path.exists(output_path))

        # output content is correct
        with utils.pelican_open(output_path) as output_file:
            self.assertEqual(output_file,
                             utils.strftime(self.date, 'date = %A, %d %B %Y'))

########NEW FILE########
__FILENAME__ = pelican_import
#!/usr/bin/env python

# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import argparse
try:
    # py3k import
    from html.parser import HTMLParser
    from urllib.request import urlretrieve
    from urllib.parse import urlparse
    from urllib.error import URLError
except ImportError:
    # py2 import
    from HTMLParser import HTMLParser  # NOQA
    from urllib import urlretrieve
    from urlparse import urlparse
    from urllib2 import URLError
import os
import re
import subprocess
import sys
import time
import logging

from codecs import open

from pelican.utils import slugify
from pelican.log import init

logger = logging.getLogger(__name__)


def decode_wp_content(content, br=True):
    pre_tags = {}
    if content.strip() == "":
        return ""

    content += "\n"
    if "<pre" in content:
        pre_parts = content.split("</pre>")
        last_pre = pre_parts.pop()
        content = ""
        pre_index = 0

        for pre_part in pre_parts:
            start = pre_part.find("<pre")
            if start == -1:
                content = content + pre_part
                continue
            name = "<pre wp-pre-tag-{0}></pre>".format(pre_index)
            pre_tags[name] = pre_part[start:] + "</pre>"
            content = content + pre_part[0:start] + name
            pre_index += 1
        content = content + last_pre

    content = re.sub(r'<br />\s*<br />', "\n\n", content)
    allblocks = ('(?:table|thead|tfoot|caption|col|colgroup|tbody|tr|'
                 'td|th|div|dl|dd|dt|ul|ol|li|pre|select|option|form|'
                 'map|area|blockquote|address|math|style|p|h[1-6]|hr|'
                 'fieldset|noscript|samp|legend|section|article|aside|'
                 'hgroup|header|footer|nav|figure|figcaption|details|'
                 'menu|summary)')
    content = re.sub(r'(<' + allblocks + r'[^>]*>)', "\n\\1", content)
    content = re.sub(r'(</' + allblocks + r'>)', "\\1\n\n", content)
    #    content = content.replace("\r\n", "\n")
    if "<object" in content:
        # no <p> inside object/embed
        content = re.sub(r'\s*<param([^>]*)>\s*', "<param\\1>", content)
        content = re.sub(r'\s*</embed>\s*', '</embed>', content)
        #    content = re.sub(r'/\n\n+/', '\n\n', content)
    pgraphs = filter(lambda s: s != "", re.split(r'\n\s*\n', content))
    content = ""
    for p in pgraphs:
        content = content + "<p>" + p.strip() + "</p>\n"
    # under certain strange conditions it could create a P of entirely whitespace
    content = re.sub(r'<p>\s*</p>', '', content)
    content = re.sub(r'<p>([^<]+)</(div|address|form)>', "<p>\\1</p></\\2>", content)
    # don't wrap tags
    content = re.sub(r'<p>\s*(</?' + allblocks + r'[^>]*>)\s*</p>', "\\1", content)
    #problem with nested lists
    content = re.sub(r'<p>(<li.*)</p>', "\\1", content)
    content = re.sub(r'<p><blockquote([^>]*)>', "<blockquote\\1><p>", content)
    content = content.replace('</blockquote></p>', '</p></blockquote>')
    content = re.sub(r'<p>\s*(</?' + allblocks + '[^>]*>)', "\\1", content)
    content = re.sub(r'(</?' + allblocks + '[^>]*>)\s*</p>', "\\1", content)
    if br:
        def _preserve_newline(match):
            return match.group(0).replace("\n", "<WPPreserveNewline />")
        content = re.sub(r'/<(script|style).*?<\/\\1>/s', _preserve_newline, content)
        # optionally make line breaks
        content = re.sub(r'(?<!<br />)\s*\n', "<br />\n", content)
        content = content.replace("<WPPreserveNewline />", "\n")
    content = re.sub(r'(</?' + allblocks + r'[^>]*>)\s*<br />', "\\1", content)
    content = re.sub(r'<br />(\s*</?(?:p|li|div|dl|dd|dt|th|pre|td|ul|ol)[^>]*>)', '\\1', content)
    content = re.sub(r'\n</p>', "</p>", content)

    if pre_tags:
        def _multi_replace(dic, string):
            pattern = r'|'.join(map(re.escape, dic.keys()))
            return re.sub(pattern, lambda m: dic[m.group()], string)
        content = _multi_replace(pre_tags, content)

    return content

def get_items(xml):
    """Opens a wordpress xml file and returns a list of items"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        error = ('Missing dependency '
                 '"BeautifulSoup4" and "lxml" required to import Wordpress XML files.')
        sys.exit(error)
    with open(xml, encoding='utf-8') as infile:
        xmlfile = infile.read()
    soup = BeautifulSoup(xmlfile, "xml")
    items = soup.rss.channel.findAll('item')
    return items

def get_filename(filename, post_id):
    if filename is not None:
        return filename
    else:
        return post_id

def wp2fields(xml, wp_custpost=False):
    """Opens a wordpress XML file, and yield Pelican fields"""

    items = get_items(xml)
    for item in items:

        if item.find('status').string == "publish":

            try:
                # Use HTMLParser due to issues with BeautifulSoup 3
                title = HTMLParser().unescape(item.title.contents[0])
            except IndexError:
                title = 'No title [%s]' % item.find('post_name').string
                logger.warning('Post "%s" is lacking a proper title' % title)

            filename = item.find('post_name').string
            post_id = item.find('post_id').string
            filename = get_filename(filename, post_id)

            content = item.find('encoded').string
            raw_date = item.find('post_date').string
            date_object = time.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
            date = time.strftime("%Y-%m-%d %H:%M", date_object)
            author = item.find('creator').string

            categories = [cat.string for cat in item.findAll('category', {'domain' : 'category'})]
            # caturl = [cat['nicename'] for cat in item.find(domain='category')]

            tags = [tag.string for tag in item.findAll('category', {'domain' : 'post_tag'})]

            kind = 'article'
            post_type = item.find('post_type').string
            if post_type == 'page':
                kind = 'page'
            elif wp_custpost:
                if post_type == 'post':
                    pass
                # Old behaviour was to name everything not a page as an article.
                # Theoretically all attachments have status == inherit so
                # no attachments should be here. But this statement is to
                # maintain existing behaviour in case that doesn't hold true.
                elif post_type == 'attachment':
                    pass
                else:
                    kind = post_type
            yield (title, content, filename, date, author, categories, tags,
                   kind, "wp-html")

def dc2fields(file):
    """Opens a Dotclear export file, and yield pelican fields"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        error = ('Missing dependency '
                 '"BeautifulSoup4" and "lxml" required to import Dotclear files.')
        sys.exit(error)


    in_cat = False
    in_post = False
    category_list = {}
    posts = []

    with open(file, 'r', encoding='utf-8') as f:

        for line in f:
            # remove final \n
            line = line[:-1]

            if line.startswith('[category'):
                in_cat = True
            elif line.startswith('[post'):
                in_post = True
            elif in_cat:
                fields = line.split('","')
                if not line:
                    in_cat = False
                else:
                    # remove 1st and last ""
                    fields[0] = fields[0][1:]
                    # fields[-1] = fields[-1][:-1]
                    category_list[fields[0]]=fields[2]
            elif in_post:
                if not line:
                    in_post = False
                    break
                else:
                    posts.append(line)

    print("%i posts read." % len(posts))

    for post in posts:
        fields = post.split('","')

        # post_id = fields[0][1:]
        # blog_id = fields[1]
        # user_id = fields[2]
        cat_id = fields[3]
        # post_dt = fields[4]
        # post_tz = fields[5]
        post_creadt = fields[6]
        # post_upddt = fields[7]
        # post_password = fields[8]
        # post_type = fields[9]
        post_format = fields[10]
        # post_url = fields[11]
        # post_lang = fields[12]
        post_title = fields[13]
        post_excerpt = fields[14]
        post_excerpt_xhtml = fields[15]
        post_content = fields[16]
        post_content_xhtml = fields[17]
        # post_notes = fields[18]
        # post_words = fields[19]
        # post_status = fields[20]
        # post_selected = fields[21]
        # post_position = fields[22]
        # post_open_comment = fields[23]
        # post_open_tb = fields[24]
        # nb_comment = fields[25]
        # nb_trackback = fields[26]
        post_meta = fields[27]
        # redirect_url = fields[28][:-1]

        # remove seconds
        post_creadt = ':'.join(post_creadt.split(':')[0:2])

        author = ""
        categories = []
        tags = []

        if cat_id:
            categories = [category_list[id].strip() for id in cat_id.split(',')]

        # Get tags related to a post
        tag = post_meta.replace('{', '').replace('}', '').replace('a:1:s:3:\\"tag\\";a:', '').replace('a:0:', '')
        if len(tag) > 1:
            if int(tag[:1]) == 1:
                newtag = tag.split('"')[1]
                tags.append(
                    BeautifulSoup(
                        newtag
                        , "xml"
                    )
                    # bs4 always outputs UTF-8
                    .decode('utf-8')
                )
            else:
                i=1
                j=1
                while(i <= int(tag[:1])):
                    newtag = tag.split('"')[j].replace('\\','')
                    tags.append(
                        BeautifulSoup(
                            newtag
                            , "xml"
                        )
                        # bs4 always outputs UTF-8
                        .decode('utf-8')
                    )
                    i=i+1
                    if j < int(tag[:1])*2:
                        j=j+2

        """
        dotclear2 does not use markdown by default unless you use the markdown plugin
        Ref: http://plugins.dotaddict.org/dc2/details/formatting-markdown
        """
        if post_format == "markdown":
            content = post_excerpt + post_content
        else:
            content = post_excerpt_xhtml + post_content_xhtml
            content = content.replace('\\n', '')
            post_format = "html"

        kind = 'article'  # TODO: Recognise pages

        yield (post_title, content, slugify(post_title), post_creadt, author,
               categories, tags, kind, post_format)


def posterous2fields(api_token, email, password):
    """Imports posterous posts"""
    import base64
    from datetime import datetime, timedelta
    try:
        # py3k import
        import json
    except ImportError:
        # py2 import
        import simplejson as json

    try:
        # py3k import
        import urllib.request as urllib_request
    except ImportError:
        # py2 import
        import urllib2 as urllib_request


    def get_posterous_posts(api_token, email, password, page = 1):
        base64string = base64.encodestring(("%s:%s" % (email, password)).encode('utf-8')).replace(b'\n', b'')
        url = "http://posterous.com/api/v2/users/me/sites/primary/posts?api_token=%s&page=%d" % (api_token, page)
        request = urllib_request.Request(url)
        request.add_header("Authorization", "Basic %s" % base64string.decode())
        handle = urllib_request.urlopen(request)
        posts = json.loads(handle.read().decode('utf-8'))
        return posts

    page = 1
    posts = get_posterous_posts(api_token, email, password, page)
    while len(posts) > 0:
        posts = get_posterous_posts(api_token, email, password, page)
        page += 1

        for post in posts:
            slug = post.get('slug')
            if not slug:
                slug = slugify(post.get('title'))
            tags = [tag.get('name') for tag in post.get('tags')]
            raw_date = post.get('display_date')
            date_object = datetime.strptime(raw_date[:-6], "%Y/%m/%d %H:%M:%S")
            offset = int(raw_date[-5:])
            delta = timedelta(hours = offset / 100)
            date_object -= delta
            date = date_object.strftime("%Y-%m-%d %H:%M")
            kind = 'article'  # TODO: Recognise pages

            yield (post.get('title'), post.get('body_cleaned'), slug, date,
                post.get('user').get('display_name'), [], tags, kind, "html")


def tumblr2fields(api_key, blogname):
    """ Imports Tumblr posts (API v2)"""
    from time import strftime, localtime
    try:
        # py3k import
        import json
    except ImportError:
        # py2 import
        import simplejson as json

    try:
        # py3k import
        import urllib.request as urllib_request
    except ImportError:
        # py2 import
        import urllib2 as urllib_request

    def get_tumblr_posts(api_key, blogname, offset=0):
        url = "http://api.tumblr.com/v2/blog/%s.tumblr.com/posts?api_key=%s&offset=%d&filter=raw" % (blogname, api_key, offset)
        request = urllib_request.Request(url)
        handle = urllib_request.urlopen(request)
        posts = json.loads(handle.read().decode('utf-8'))
        return posts.get('response').get('posts')

    offset = 0
    posts = get_tumblr_posts(api_key, blogname, offset)
    while len(posts) > 0:
        for post in posts:
            title = post.get('title') or post.get('source_title') or post.get('type').capitalize()
            slug = post.get('slug') or slugify(title)
            tags = post.get('tags')
            timestamp = post.get('timestamp')
            date = strftime("%Y-%m-%d %H:%M:%S", localtime(int(timestamp)))
            slug = strftime("%Y-%m-%d-", localtime(int(timestamp))) + slug
            format = post.get('format')
            content = post.get('body')
            type = post.get('type')
            if type == 'photo':
                if format == 'markdown':
                    fmtstr = '![%s](%s)'
                else:
                    fmtstr = '<img alt="%s" src="%s" />'
                content = '\n'.join(fmtstr % (photo.get('caption'), photo.get('original_size').get('url')) for photo in post.get('photos'))
                content += '\n\n' + post.get('caption')
            elif type == 'quote':
                if format == 'markdown':
                    fmtstr = '\n\n&mdash; %s'
                else:
                    fmtstr = '<p>&mdash; %s</p>'
                content = post.get('text') + fmtstr % post.get('source')
            elif type == 'link':
                if format == 'markdown':
                    fmtstr = '[via](%s)\n\n'
                else:
                    fmtstr = '<p><a href="%s">via</a></p>\n'
                content = fmtstr % post.get('url') + post.get('description')
            elif type == 'audio':
                if format == 'markdown':
                    fmtstr = '[via](%s)\n\n'
                else:
                    fmtstr = '<p><a href="%s">via</a></p>\n'
                content = fmtstr % post.get('source_url') + post.get('caption') + post.get('player')
            elif type == 'video':
                if format == 'markdown':
                    fmtstr = '[via](%s)\n\n'
                else:
                    fmtstr = '<p><a href="%s">via</a></p>\n'
                content = fmtstr % post.get('source_url') + post.get('caption') + '\n'.join(player.get('embed_code') for player in post.get('player'))
            elif type == 'answer':
                title = post.get('question')
                content = '<p><a href="%s" rel="external nofollow">%s</a>: %s</p>\n%s' % (post.get('asking_name'), post.get('asking_url'), post.get('question'), post.get('answer'))

            content = content.rstrip() + '\n'
            kind = 'article'
            yield (title, content, slug, date, post.get('blog_name'), [type],
                   tags, kind, format)

        offset += len(posts)
        posts = get_tumblr_posts(api_key, blogname, offset)

def feed2fields(file):
    """Read a feed and yield pelican fields"""
    import feedparser
    d = feedparser.parse(file)
    for entry in d.entries:
        date = (time.strftime("%Y-%m-%d %H:%M", entry.updated_parsed)
            if hasattr(entry, "updated_parsed") else None)
        author = entry.author if hasattr(entry, "author") else None
        tags = [e['term'] for e in entry.tags] if hasattr(entry, "tags") else None

        slug = slugify(entry.title)
        kind = 'article'
        yield (entry.title, entry.description, slug, date, author, [], tags,
               kind, "html")

def build_header(title, date, author, categories, tags, slug, attachments=None):
    from docutils.utils import column_width

    """Build a header from a list of fields"""
    header = '%s\n%s\n' % (title, '#' * column_width(title))
    if date:
        header += ':date: %s\n' % date
    if author:
        header += ':author: %s\n' % author
    if categories:
        header += ':category: %s\n' % ', '.join(categories)
    if tags:
        header += ':tags: %s\n' % ', '.join(tags)
    if slug:
        header += ':slug: %s\n' % slug
    if attachments:
        header += ':attachments: %s\n' % ', '.join(attachments)
    header += '\n'
    return header

def build_markdown_header(title, date, author, categories, tags, slug,
        attachments=None):
    """Build a header from a list of fields"""
    header = 'Title: %s\n' % title
    if date:
        header += 'Date: %s\n' % date
    if author:
        header += 'Author: %s\n' % author
    if categories:
        header += 'Category: %s\n' % ', '.join(categories)
    if tags:
        header += 'Tags: %s\n' % ', '.join(tags)
    if slug:
        header += 'Slug: %s\n' % slug
    if attachments:
        header += 'Attachments: %s\n' % ', '.join(attachments)
    header += '\n'
    return header

def get_ext(out_markup, in_markup='html'):
    if in_markup == 'markdown' or out_markup == 'markdown':
        ext = '.md'
    else:
        ext = '.rst'
    return ext

def get_out_filename(output_path, filename, ext, kind,
        dirpage, dircat, categories, wp_custpost):
    filename = os.path.basename(filename)

    # Enforce filename restrictions for various filesystems at once; see
    # http://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words
    # we do not need to filter words because an extension will be appended
    filename = re.sub(r'[<>:"/\\|?*^% ]', '-', filename) # invalid chars
    filename = filename.lstrip('.') # should not start with a dot
    if not filename:
        filename = '_'
    filename = filename[:249] # allow for 5 extra characters

    out_filename = os.path.join(output_path, filename+ext)
    # option to put page posts in pages/ subdirectory
    if dirpage and kind == 'page':
        pages_dir = os.path.join(output_path, 'pages')
        if not os.path.isdir(pages_dir):
            os.mkdir(pages_dir)
        out_filename = os.path.join(pages_dir, filename+ext)
    elif not dirpage and kind == 'page':
        pass
    # option to put wp custom post types in directories with post type
    # names. Custom post types can also have categories so option to
    # create subdirectories with category names
    elif kind != 'article':
        if wp_custpost:
            typename = slugify(kind)
        else:
            typename = ''
            kind = 'article'
        if dircat and (len(categories) > 0):
            catname = slugify(categories[0])
        else:
            catname = ''
        out_filename = os.path.join(output_path, typename,
            catname, filename+ext)
        if not os.path.isdir(os.path.join(output_path, typename, catname)):
            os.makedirs(os.path.join(output_path, typename, catname))
    # option to put files in directories with categories names
    elif dircat and (len(categories) > 0):
        catname = slugify(categories[0])
        out_filename = os.path.join(output_path, catname, filename+ext)
        if not os.path.isdir(os.path.join(output_path, catname)):
            os.mkdir(os.path.join(output_path, catname))

    return out_filename

def get_attachments(xml):
    """returns a dictionary of posts that have attachments with a list
    of the attachment_urls
    """
    items = get_items(xml)
    names = {}
    attachments = []

    for item in items:
        kind = item.find('post_type').string
        filename = item.find('post_name').string
        post_id = item.find('post_id').string

        if kind == 'attachment':
            attachments.append((item.find('post_parent').string,
                item.find('attachment_url').string))
        else:
            filename = get_filename(filename, post_id)
            names[post_id] = filename
    attachedposts = {}
    for parent, url in attachments:
        try:
            parent_name = names[parent]
        except KeyError:
            #attachment's parent is not a valid post
            parent_name = None

        try:
            attachedposts[parent_name].append(url)
        except KeyError:
            attachedposts[parent_name] = []
            attachedposts[parent_name].append(url)
    return attachedposts

def download_attachments(output_path, urls):
    """Downloads wordpress attachments and returns a list of paths to
    attachments that can be associated with a post (relative path to output
    directory). Files that fail to download, will not be added to posts"""
    locations = []
    for url in urls:
        path = urlparse(url).path
        #teardown path and rebuild to negate any errors with
        #os.path.join and leading /'s
        path = path.split('/')
        filename = path.pop(-1)
        localpath = ''
        for item in path:
            localpath = os.path.join(localpath, item)
        full_path = os.path.join(output_path, localpath)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        print('downloading {}'.format(filename))
        try:
            urlretrieve(url, os.path.join(full_path, filename))
            locations.append(os.path.join(localpath, filename))
        except URLError as e:
            error = ("No file could be downloaded from {}; Error {}"
                    .format(url, e))
            logger.warning(error)
        except IOError as e: #Python 2.7 throws an IOError rather Than URLError
            # For japanese, the error might look kind of like this:
            # e = IOError( 'socket error', socket.error(111, u'\u63a5\u7d9a\u3092\u62d2\u5426\u3055\u308c\u307e\u3057\u305f') )
            # and not be suitable to use in "{}".format(e) , raising UnicodeDecodeError
            # (This is at least the case on my Fedora running Python 2.7.5 
            # (default, Feb 19 2014, 13:47:28) [GCC 4.8.2 20131212 (Red Hat 4.8.2-7)] on linux2
            try:
                error = ("No file could be downloaded from {}; Error {}"
                        .format(url, e))
            except UnicodeDecodeError:
                # For lack of a better log message because we could not decode e, let's use repr(e)
                error = ("No file could be downloaded from {}; Error {}"
                        .format(url, repr(e)))
            logger.warning(error)
    return locations


def fields2pelican(fields, out_markup, output_path,
        dircat=False, strip_raw=False, disable_slugs=False,
        dirpage=False, filename_template=None, filter_author=None,
        wp_custpost=False, wp_attach=False, attachments=None):
    for (title, content, filename, date, author, categories, tags,
            kind, in_markup) in fields:
        if filter_author and filter_author != author:
            continue
        slug = not disable_slugs and filename or None

        if wp_attach and attachments:
            try:
                urls = attachments[filename]
                attached_files = download_attachments(output_path, urls)
            except KeyError:
                attached_files = None
        else:
            attached_files = None

        ext = get_ext(out_markup, in_markup)
        if ext == '.md':
            header = build_markdown_header(title, date, author, categories,
                    tags, slug, attached_files)
        else:
            out_markup = "rst"
            header = build_header(title, date, author, categories,
                    tags, slug, attached_files)

        out_filename = get_out_filename(output_path, filename, ext,
                kind, dirpage, dircat, categories, wp_custpost)
        print(out_filename)

        if in_markup in ("html", "wp-html"):
            html_filename = os.path.join(output_path, filename+'.html')

            with open(html_filename, 'w', encoding='utf-8') as fp:
                # Replace newlines with paragraphs wrapped with <p> so
                # HTML is valid before conversion
                if in_markup == "wp-html":
                    new_content = decode_wp_content(content)
                else:
                    paragraphs = content.splitlines()
                    paragraphs = ['<p>{0}</p>'.format(p) for p in paragraphs]
                    new_content = ''.join(paragraphs)

                fp.write(new_content)


            parse_raw = '--parse-raw' if not strip_raw else ''
            cmd = ('pandoc --normalize {0} --from=html'
                   ' --to={1} -o "{2}" "{3}"').format(
                    parse_raw, out_markup, out_filename, html_filename)

            try:
                rc = subprocess.call(cmd, shell=True)
                if rc < 0:
                    error = "Child was terminated by signal %d" % -rc
                    exit(error)

                elif rc > 0:
                    error = "Please, check your Pandoc installation."
                    exit(error)
            except OSError as e:
                error = "Pandoc execution failed: %s" % e
                exit(error)

            os.remove(html_filename)

            with open(out_filename, 'r', encoding='utf-8') as fs:
                content = fs.read()
                if out_markup == "markdown":
                    # In markdown, to insert a <br />, end a line with two or more spaces & then a end-of-line
                    content = content.replace("\\\n ", "  \n")
                    content = content.replace("\\\n", "  \n")

        with open(out_filename, 'w', encoding='utf-8') as fs:
            fs.write(header + content)
    if wp_attach and attachments and None in attachments:
        print("downloading attachments that don't have a parent post")
        urls = attachments[None]
        orphan_galleries = download_attachments(output_path, urls)

def main():
    parser = argparse.ArgumentParser(
        description="Transform feed, WordPress, Tumblr, Dotclear, or Posterous "
                    "files into reST (rst) or Markdown (md) files. Be sure to "
                    "have pandoc installed.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(dest='input', help='The input file to read')
    parser.add_argument('--wpfile', action='store_true', dest='wpfile',
        help='Wordpress XML export')
    parser.add_argument('--dotclear', action='store_true', dest='dotclear',
        help='Dotclear export')
    parser.add_argument('--posterous', action='store_true', dest='posterous',
        help='Posterous export')
    parser.add_argument('--tumblr', action='store_true', dest='tumblr',
        help='Tumblr export')
    parser.add_argument('--feed', action='store_true', dest='feed',
        help='Feed to parse')
    parser.add_argument('-o', '--output', dest='output', default='output',
        help='Output path')
    parser.add_argument('-m', '--markup', dest='markup', default='rst',
        help='Output markup format (supports rst & markdown)')
    parser.add_argument('--dir-cat', action='store_true', dest='dircat',
        help='Put files in directories with categories name')
    parser.add_argument('--dir-page', action='store_true', dest='dirpage',
        help=('Put files recognised as pages in "pages/" sub-directory'
              ' (wordpress import only)'))
    parser.add_argument('--filter-author', dest='author',
        help='Import only post from the specified author')
    parser.add_argument('--strip-raw', action='store_true', dest='strip_raw',
        help="Strip raw HTML code that can't be converted to "
             "markup such as flash embeds or iframes (wordpress import only)")
    parser.add_argument('--wp-custpost', action='store_true',
        dest='wp_custpost',
        help='Put wordpress custom post types in directories. If used with '
             '--dir-cat option directories will be created as '
             '/post_type/category/ (wordpress import only)')
    parser.add_argument('--wp-attach', action='store_true', dest='wp_attach',
        help='(wordpress import only) Download files uploaded to wordpress as '
             'attachments. Files will be added to posts as a list in the post '
             'header. All files will be downloaded, even if '
             "they aren't associated with a post. Files with be downloaded "
             'with their original path inside the output directory. '
             'e.g. output/wp-uploads/date/postname/file.jpg '
             '-- Requires an internet connection --')
    parser.add_argument('--disable-slugs', action='store_true',
        dest='disable_slugs',
        help='Disable storing slugs from imported posts within output. '
             'With this disabled, your Pelican URLs may not be consistent '
             'with your original posts.')
    parser.add_argument('-e', '--email', dest='email',
        help="Email address (posterous import only)")
    parser.add_argument('-p', '--password', dest='password',
        help="Password (posterous import only)")
    parser.add_argument('-b', '--blogname', dest='blogname',
        help="Blog name (Tumblr import only)")

    args = parser.parse_args()

    input_type = None
    if args.wpfile:
        input_type = 'wordpress'
    elif args.dotclear:
        input_type = 'dotclear'
    elif args.posterous:
        input_type = 'posterous'
    elif args.tumblr:
        input_type = 'tumblr'
    elif args.feed:
        input_type = 'feed'
    else:
        error = "You must provide either --wpfile, --dotclear, --posterous, --tumblr or --feed options"
        exit(error)

    if not os.path.exists(args.output):
        try:
            os.mkdir(args.output)
        except OSError:
            error = "Unable to create the output folder: " + args.output
            exit(error)

    if args.wp_attach and input_type != 'wordpress':
        error = "You must be importing a wordpress xml to use the --wp-attach option"
        exit(error)

    if input_type == 'wordpress':
        fields = wp2fields(args.input, args.wp_custpost or False)
    elif input_type == 'dotclear':
        fields = dc2fields(args.input)
    elif input_type == 'posterous':
        fields = posterous2fields(args.input, args.email, args.password)
    elif input_type == 'tumblr':
        fields = tumblr2fields(args.input, args.blogname)
    elif input_type == 'feed':
        fields = feed2fields(args.input)

    if args.wp_attach:
        attachments = get_attachments(args.input)
    else:
        attachments = None

    init() # init logging

    fields2pelican(fields, args.markup, args.output,
                   dircat=args.dircat or False,
                   dirpage=args.dirpage or False,
                   strip_raw=args.strip_raw or False,
                   disable_slugs=args.disable_slugs or False,
                   filter_author=args.author,
                   wp_custpost = args.wp_custpost or False,
                   wp_attach = args.wp_attach or False,
                   attachments = attachments or None)

########NEW FILE########
__FILENAME__ = pelican_quickstart
#!/usr/bin/env python

# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import six

import os
import string
import argparse
import sys
import codecs

from pelican import __version__

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "templates")

_GITHUB_PAGES_BRANCHES = {
    'personal': 'master',
    'project': 'gh-pages'
}

CONF = {
    'pelican': 'pelican',
    'pelicanopts': '',
    'basedir': os.curdir,
    'ftp_host': 'localhost',
    'ftp_user': 'anonymous',
    'ftp_target_dir': '/',
    'ssh_host': 'localhost',
    'ssh_port': 22,
    'ssh_user': 'root',
    'ssh_target_dir': '/var/www',
    's3_bucket': 'my_s3_bucket',
    'cloudfiles_username': 'my_rackspace_username',
    'cloudfiles_api_key': 'my_rackspace_api_key',
    'cloudfiles_container': 'my_cloudfiles_container',
    'dropbox_dir': '~/Dropbox/Public/',
    'github_pages_branch': _GITHUB_PAGES_BRANCHES['project'],
    'default_pagination': 10,
    'siteurl': '',
    'lang': 'en'
}

def _input_compat(prompt):
    if six.PY3:
        r = input(prompt)
    else:
        r = raw_input(prompt)
    return r

if six.PY3:
    str_compat = str
else:
    str_compat = unicode

def decoding_strings(f):
    def wrapper(*args, **kwargs):
        out = f(*args, **kwargs)
        if isinstance(out, six.string_types) and not six.PY3:
            # todo: make encoding configurable?
            if six.PY3:
                return out
            else:
                return out.decode(sys.stdin.encoding)
        return out
    return wrapper


def get_template(name, as_encoding='utf-8'):
    template = os.path.join(_TEMPLATES_DIR, "{0}.in".format(name))

    if not os.path.isfile(template):
        raise RuntimeError("Cannot open {0}".format(template))

    with codecs.open(template, 'r', as_encoding) as fd:
        line = fd.readline()
        while line:
            yield line
            line = fd.readline()
        fd.close()


@decoding_strings
def ask(question, answer=str_compat, default=None, l=None):
    if answer == str_compat:
        r = ''
        while True:
            if default:
                r = _input_compat('> {0} [{1}] '.format(question, default))
            else:
                r = _input_compat('> {0} '.format(question, default))

            r = r.strip()

            if len(r) <= 0:
                if default:
                    r = default
                    break
                else:
                    print('You must enter something')
            else:
                if l and len(r) != l:
                    print('You must enter a {0} letters long string'.format(l))
                else:
                    break

        return r

    elif answer == bool:
        r = None
        while True:
            if default is True:
                r = _input_compat('> {0} (Y/n) '.format(question))
            elif default is False:
                r = _input_compat('> {0} (y/N) '.format(question))
            else:
                r = _input_compat('> {0} (y/n) '.format(question))

            r = r.strip().lower()

            if r in ('y', 'yes'):
                r = True
                break
            elif r in ('n', 'no'):
                r = False
                break
            elif not r:
                r = default
                break
            else:
                print("You must answer 'yes' or 'no'")
        return r
    elif answer == int:
        r = None
        while True:
            if default:
                r = _input_compat('> {0} [{1}] '.format(question, default))
            else:
                r = _input_compat('> {0} '.format(question))

            r = r.strip()

            if not r:
                r = default
                break

            try:
                r = int(r)
                break
            except:
                print('You must enter an integer')
        return r
    else:
        raise NotImplemented('Argument `answer` must be str_compat, bool, or integer')


def main():
    parser = argparse.ArgumentParser(
        description="A kickstarter for Pelican",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--path', default=os.curdir,
            help="The path to generate the blog into")
    parser.add_argument('-t', '--title', metavar="title",
            help='Set the title of the website')
    parser.add_argument('-a', '--author', metavar="author",
            help='Set the author name of the website')
    parser.add_argument('-l', '--lang', metavar="lang",
            help='Set the default web site language')

    args = parser.parse_args()

    print('''Welcome to pelican-quickstart v{v}.

This script will help you create a new Pelican-based website.

Please answer the following questions so this script can generate the files
needed by Pelican.

    '''.format(v=__version__))

    project = os.path.join(
        os.environ.get('VIRTUAL_ENV', os.curdir), '.project')
    if os.path.isfile(project):
        CONF['basedir'] = open(project, 'r').read().rstrip("\n")
        print('Using project associated with current virtual environment.'
              'Will save to:\n%s\n' % CONF['basedir'])
    else:
        CONF['basedir'] = os.path.abspath(os.path.expanduser(
            ask('Where do you want to create your new web site?', answer=str_compat, default=args.path)))

    CONF['sitename'] = ask('What will be the title of this web site?', answer=str_compat, default=args.title)
    CONF['author'] = ask('Who will be the author of this web site?', answer=str_compat, default=args.author)
    CONF['lang'] = ask('What will be the default language of this web site?', str_compat, args.lang or CONF['lang'], 2)

    if ask('Do you want to specify a URL prefix? e.g., http://example.com  ', answer=bool, default=True):
        CONF['siteurl'] = ask('What is your URL prefix? (see above example; no trailing slash)', str_compat, CONF['siteurl'])

    CONF['with_pagination'] = ask('Do you want to enable article pagination?', bool, bool(CONF['default_pagination']))

    if CONF['with_pagination']:
        CONF['default_pagination'] = ask('How many articles per page do you want?', int, CONF['default_pagination'])
    else:
        CONF['default_pagination'] = False

    automation = ask('Do you want to generate a Fabfile/Makefile to automate generation and publishing?', bool, True)
    develop = ask('Do you want an auto-reload & simpleHTTP script to assist with theme and site development?', bool, True)

    if automation:
        if ask('Do you want to upload your website using FTP?', answer=bool, default=False):
            CONF['ftp_host'] = ask('What is the hostname of your FTP server?', str_compat, CONF['ftp_host'])
            CONF['ftp_user'] = ask('What is your username on that server?', str_compat, CONF['ftp_user'])
            CONF['ftp_target_dir'] = ask('Where do you want to put your web site on that server?', str_compat, CONF['ftp_target_dir'])
        if ask('Do you want to upload your website using SSH?', answer=bool, default=False):
            CONF['ssh_host'] = ask('What is the hostname of your SSH server?', str_compat, CONF['ssh_host'])
            CONF['ssh_port'] = ask('What is the port of your SSH server?', int, CONF['ssh_port'])
            CONF['ssh_user'] = ask('What is your username on that server?', str_compat, CONF['ssh_user'])
            CONF['ssh_target_dir'] = ask('Where do you want to put your web site on that server?', str_compat, CONF['ssh_target_dir'])
        if ask('Do you want to upload your website using Dropbox?', answer=bool, default=False):
            CONF['dropbox_dir'] = ask('Where is your Dropbox directory?', str_compat, CONF['dropbox_dir'])
        if ask('Do you want to upload your website using S3?', answer=bool, default=False):
            CONF['s3_bucket'] = ask('What is the name of your S3 bucket?', str_compat, CONF['s3_bucket'])
        if ask('Do you want to upload your website using Rackspace Cloud Files?', answer=bool, default=False):
            CONF['cloudfiles_username'] = ask('What is your Rackspace Cloud username?', str_compat, CONF['cloudfiles_username'])
            CONF['cloudfiles_api_key'] = ask('What is your Rackspace Cloud API key?', str_compat, CONF['cloudfiles_api_key'])
            CONF['cloudfiles_container'] = ask('What is the name of your Cloud Files container?', str_compat, CONF['cloudfiles_container'])
        if ask('Do you want to upload your website using GitHub Pages?', answer=bool, default=False):
            if ask('Is this your personal page (username.github.io)?', answer=bool, default=False):
                CONF['github_pages_branch'] = _GITHUB_PAGES_BRANCHES['personal']
            else:
                CONF['github_pages_branch'] = _GITHUB_PAGES_BRANCHES['project']

    try:
        os.makedirs(os.path.join(CONF['basedir'], 'content'))
    except OSError as e:
        print('Error: {0}'.format(e))

    try:
        os.makedirs(os.path.join(CONF['basedir'], 'output'))
    except OSError as e:
        print('Error: {0}'.format(e))

    try:
        with codecs.open(os.path.join(CONF['basedir'], 'pelicanconf.py'), 'w', 'utf-8') as fd:
            conf_python = dict()
            for key, value in CONF.items():
                conf_python[key] = repr(value)

            for line in get_template('pelicanconf.py'):
                template = string.Template(line)
                fd.write(template.safe_substitute(conf_python))
            fd.close()
    except OSError as e:
        print('Error: {0}'.format(e))

    try:
        with codecs.open(os.path.join(CONF['basedir'], 'publishconf.py'), 'w', 'utf-8') as fd:
            for line in get_template('publishconf.py'):
                template = string.Template(line)
                fd.write(template.safe_substitute(CONF))
            fd.close()
    except OSError as e:
        print('Error: {0}'.format(e))

    if automation:
        try:
            with codecs.open(os.path.join(CONF['basedir'], 'fabfile.py'), 'w', 'utf-8') as fd:
                for line in get_template('fabfile.py'):
                    template = string.Template(line)
                    fd.write(template.safe_substitute(CONF))
                fd.close()
        except OSError as e:
            print('Error: {0}'.format(e))
        try:
            with codecs.open(os.path.join(CONF['basedir'], 'Makefile'), 'w', 'utf-8') as fd:
                mkfile_template_name = 'Makefile'
                py_v = 'PY?=python'
                if six.PY3:
                    py_v = 'PY?=python3'
                template = string.Template(py_v)
                fd.write(template.safe_substitute(CONF))
                fd.write('\n')
                for line in get_template(mkfile_template_name):
                    template = string.Template(line)
                    fd.write(template.safe_substitute(CONF))
                fd.close()
        except OSError as e:
            print('Error: {0}'.format(e))

    if develop:
        conf_shell = dict()
        for key, value in CONF.items():
            if isinstance(value, six.string_types) and ' ' in value:
                value = '"' + value.replace('"', '\\"') + '"'
            conf_shell[key] = value
        try:
            with codecs.open(os.path.join(CONF['basedir'], 'develop_server.sh'), 'w', 'utf-8') as fd:
                lines = list(get_template('develop_server.sh'))
                py_v = 'PY=${PY:-python}\n'
                if six.PY3:
                    py_v = 'PY=${PY:-python3}\n'
                lines = lines[:4] + [py_v] + lines[4:]
                for line in lines:
                    template = string.Template(line)
                    fd.write(template.safe_substitute(conf_shell))
                fd.close()
                os.chmod((os.path.join(CONF['basedir'], 'develop_server.sh')), 493) # mode 0o755
        except OSError as e:
            print('Error: {0}'.format(e))

    print('Done. Your new project is available at %s' % CONF['basedir'])

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = pelican_themes
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import six

import argparse
import os
import shutil
import sys

try:
    import pelican
except:
    err('Cannot import pelican.\nYou must install Pelican in order to run this script.', -1)


global _THEMES_PATH
_THEMES_PATH = os.path.join(
    os.path.dirname(
        os.path.abspath(
            pelican.__file__
    )
    ),
    'themes'
)

__version__ = '0.2'
_BUILTIN_THEMES = ['simple', 'notmyidea']


def err(msg, die=None):
    """Print an error message and exits if an exit code is given"""
    sys.stderr.write(msg + '\n')
    if die:
        sys.exit((die if type(die) is int else 1))


def main():
    """Main function"""

    parser = argparse.ArgumentParser(description="""Install themes for Pelican""")

    excl= parser.add_mutually_exclusive_group()
    excl.add_argument('-l', '--list', dest='action', action="store_const", const='list',
        help="Show the themes already installed and exit")
    excl.add_argument('-p', '--path', dest='action', action="store_const", const='path',
        help="Show the themes path and exit")
    excl.add_argument('-V', '--version', action='version', version='pelican-themes v{0}'.format(__version__),
        help='Print the version of this script')


    parser.add_argument('-i', '--install', dest='to_install', nargs='+', metavar="theme path",
        help='The themes to install')
    parser.add_argument('-r', '--remove', dest='to_remove', nargs='+', metavar="theme name",
        help='The themes to remove')
    parser.add_argument('-U', '--upgrade', dest='to_upgrade', nargs='+',
            metavar="theme path", help='The themes to upgrade')
    parser.add_argument('-s', '--symlink', dest='to_symlink', nargs='+', metavar="theme path",
        help="Same as `--install', but create a symbolic link instead of copying the theme. Useful for theme development")
    parser.add_argument('-c', '--clean', dest='clean', action="store_true",
        help="Remove the broken symbolic links of the theme path")


    parser.add_argument('-v', '--verbose', dest='verbose', action="store_true",
        help="Verbose output")


    args = parser.parse_args()
    
    to_install = args.to_install or args.to_upgrade
    to_sym = args.to_symlink or args.clean


    if args.action:
        if args.action is 'list':
            list_themes(args.verbose)
        elif args.action is 'path':
            print(_THEMES_PATH)
    elif to_install or args.to_remove or to_sym:
        if args.to_remove:
            if args.verbose:
                print('Removing themes...')

            for i in args.to_remove:
                remove(i, v=args.verbose)

        if args.to_install:
            if args.verbose:
                print('Installing themes...')

            for i in args.to_install:
                install(i, v=args.verbose)

        if args.to_upgrade:
            if args.verbose:
                print('Upgrading themes...')
            
            for i in args.to_upgrade:
                install(i, v=args.verbose, u=True)

        if args.to_symlink:
            if args.verbose:
                print('Linking themes...')

            for i in args.to_symlink:
                symlink(i, v=args.verbose)

        if args.clean:
            if args.verbose:
                print('Cleaning the themes directory...')

            clean(v=args.verbose)
    else:
        print('No argument given... exiting.')


def themes():
    """Returns the list of the themes"""
    for i in os.listdir(_THEMES_PATH):
        e = os.path.join(_THEMES_PATH, i)

        if os.path.isdir(e):
            if os.path.islink(e):
                yield (e, os.readlink(e))
            else:
                yield (e, None)


def list_themes(v=False):
    """Display the list of the themes"""
    for t, l in themes():
        if not v:
            t = os.path.basename(t)
        if l:
            if v:
                print(t + (" (symbolic link to `" + l + "')"))
            else:
                print(t + '@')
        else:
            print(t)


def remove(theme_name, v=False):
    """Removes a theme"""

    theme_name = theme_name.replace('/','')
    target = os.path.join(_THEMES_PATH, theme_name)

    if theme_name in _BUILTIN_THEMES:
        err(theme_name + ' is a builtin theme.\nYou cannot remove a builtin theme with this script, remove it by hand if you want.')
    elif os.path.islink(target):
        if v:
            print('Removing link `' + target + "'")
        os.remove(target)
    elif os.path.isdir(target):
        if v:
            print('Removing directory `' + target + "'")
        shutil.rmtree(target)
    elif os.path.exists(target):
        err(target + ' : not a valid theme')
    else:
        err(target + ' : no such file or directory')


def install(path, v=False, u=False):
    """Installs a theme"""
    if not os.path.exists(path):
        err(path + ' : no such file or directory')
    elif not os.path.isdir(path):
        err(path + ' : not a directory')
    else:
        theme_name = os.path.basename(os.path.normpath(path))
        theme_path = os.path.join(_THEMES_PATH, theme_name)
        exists = os.path.exists(theme_path)
        if exists and not u:
            err(path + ' : already exists')
        elif exists and u:
            remove(theme_name, v)
            install(path, v)
        else:
            if v:
                print("Copying `{p}' to `{t}' ...".format(p=path, t=theme_path))
            try:
                shutil.copytree(path, theme_path)

                try:
                    if os.name == 'posix':
                        for root, dirs, files in os.walk(theme_path):
                            for d in dirs:
                                dname = os.path.join(root, d)
                                os.chmod(dname, 493) # 0o755
                            for f in files:
                                fname = os.path.join(root, f)
                                os.chmod(fname, 420) # 0o644
                except OSError as e:
                    err("Cannot change permissions of files or directory in `{r}':\n{e}".format(r=theme_path, e=str(e)), die=False)
            except Exception as e:
                err("Cannot copy `{p}' to `{t}':\n{e}".format(p=path, t=theme_path, e=str(e)))


def symlink(path, v=False):
    """Symbolically link a theme"""
    if not os.path.exists(path):
        err(path + ' : no such file or directory')
    elif not os.path.isdir(path):
        err(path + ' : not a directory')
    else:
        theme_name = os.path.basename(os.path.normpath(path))
        theme_path = os.path.join(_THEMES_PATH, theme_name)
        if os.path.exists(theme_path):
            err(path + ' : already exists')
        else:
            if v:
                print("Linking `{p}' to `{t}' ...".format(p=path, t=theme_path))
            try:
                os.symlink(path, theme_path)
            except Exception as e:
                err("Cannot link `{p}' to `{t}':\n{e}".format(p=path, t=theme_path, e=str(e)))


def is_broken_link(path):
    """Returns True if the path given as is a broken symlink"""
    path = os.readlink(path)
    return not os.path.exists(path)


def clean(v=False):
    """Removes the broken symbolic links"""
    c=0
    for path in os.listdir(_THEMES_PATH):
        path = os.path.join(_THEMES_PATH, path)
        if os.path.islink(path):
            if is_broken_link(path):
                if v:
                    print('Removing {0}'.format(path))
                try:
                    os.remove(path)
                except OSError as e:
                    print('Error: cannot remove {0}'.format(path))
                else:
                    c+=1

    print("\nRemoved {0} broken links".format(c))

########NEW FILE########
__FILENAME__ = urlwrappers
import os
import functools
import logging

import six

from pelican.utils import (slugify, python_2_unicode_compatible)

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
@functools.total_ordering
class URLWrapper(object):
    def __init__(self, name, settings):
        # next 2 lines are redundant with the setter of the name property
        # but are here for clarity
        self.settings = settings
        self._name = name
        self.slug = slugify(name, self.settings.get('SLUG_SUBSTITUTIONS', ()))
        self.name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self.slug = slugify(name, self.settings.get('SLUG_SUBSTITUTIONS', ()))

    def as_dict(self):
        d = self.__dict__
        d['name'] = self.name
        return d

    def __hash__(self):
        return hash(self.slug)

    def _key(self):
        return self.slug

    def _normalize_key(self, key):
        subs = self.settings.get('SLUG_SUBSTITUTIONS', ())
        return six.text_type(slugify(key, subs))

    def __eq__(self, other):
        return self._key() == self._normalize_key(other)

    def __ne__(self, other):
        return self._key() != self._normalize_key(other)

    def __lt__(self, other):
        return self._key() < self._normalize_key(other)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, str(self))

    def _from_settings(self, key, get_page_name=False):
        """Returns URL information as defined in settings.

        When get_page_name=True returns URL without anything after {slug} e.g.
        if in settings: CATEGORY_URL="cat/{slug}.html" this returns
        "cat/{slug}" Useful for pagination.

        """
        setting = "%s_%s" % (self.__class__.__name__.upper(), key)
        value = self.settings[setting]
        if not isinstance(value, six.string_types):
            logger.warning('%s is set to %s' % (setting, value))
            return value
        else:
            if get_page_name:
                return os.path.splitext(value)[0].format(**self.as_dict())
            else:
                return value.format(**self.as_dict())

    page_name = property(functools.partial(_from_settings, key='URL',
                         get_page_name=True))
    url = property(functools.partial(_from_settings, key='URL'))
    save_as = property(functools.partial(_from_settings, key='SAVE_AS'))


class Category(URLWrapper):
    pass


class Tag(URLWrapper):
    def __init__(self, name, *args, **kwargs):
        super(Tag, self).__init__(name.strip(), *args, **kwargs)


class Author(URLWrapper):
    pass

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import six

import codecs
import errno
import fnmatch
import locale
import logging
import os
import pytz
import re
import shutil
import traceback
import pickle
import hashlib

from collections import Hashable
from contextlib import contextmanager
import dateutil.parser
from functools import partial
from itertools import groupby
from jinja2 import Markup
from operator import attrgetter

logger = logging.getLogger(__name__)


def strftime(date, date_format):
    '''
    Replacement for built-in strftime

    This is necessary because of the way Py2 handles date format strings.
    Specifically, Py2 strftime takes a bytestring. In the case of text output
    (e.g. %b, %a, etc), the output is encoded with an encoding defined by
    locale.LC_TIME. Things get messy if the formatting string has chars that
    are not valid in LC_TIME defined encoding.

    This works by 'grabbing' possible format strings (those starting with %),
    formatting them with the date, (if necessary) decoding the output and
    replacing formatted output back.
    '''

    # grab candidate format options
    format_options = '%.'
    candidates = re.findall(format_options, date_format)

    # replace candidates with placeholders for later % formatting
    template = re.sub(format_options, '%s', date_format)

    # we need to convert formatted dates back to unicode in Py2
    # LC_TIME determines the encoding for built-in strftime outputs
    lang_code, enc = locale.getlocale(locale.LC_TIME)

    formatted_candidates = []
    for candidate in candidates:
        # test for valid C89 directives only
        if candidate[1] in 'aAbBcdfHIjmMpSUwWxXyYzZ%':
            formatted = date.strftime(candidate)
            # convert Py2 result to unicode
            if not six.PY3 and enc is not None:
                formatted = formatted.decode(enc)
        else:
            formatted = candidate
        formatted_candidates.append(formatted)

    # put formatted candidates back and return
    return template % tuple(formatted_candidates)


class DateFormatter(object):
    '''A date formatter object used as a jinja filter

    Uses the `strftime` implementation and makes sure jinja uses the locale
    defined in LOCALE setting
    '''

    def __init__(self):
        self.locale = locale.setlocale(locale.LC_TIME)

    def __call__(self, date, date_format):
        old_locale = locale.setlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_TIME, self.locale)

        formatted = strftime(date, date_format)

        locale.setlocale(locale.LC_TIME, old_locale)
        return formatted


def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.

    From django.utils.encoding.
    """
    if not six.PY3:
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return klass


class memoized(object):
    """Function decorator to cache return values.

    If called later with the same arguments, the cached value is returned
    (not reevaluated).

    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, obj, objtype):
        '''Support instance methods.'''
        return partial(self.__call__, obj)


def deprecated_attribute(old, new, since=None, remove=None, doc=None):
    """Attribute deprecation decorator for gentle upgrades

    For example:

        class MyClass (object):
            @deprecated_attribute(
                old='abc', new='xyz', since=(3, 2, 0), remove=(4, 1, 3))
            def abc(): return None

            def __init__(self):
                xyz = 5

    Note that the decorator needs a dummy method to attach to, but the
    content of the dummy method is ignored.
    """
    def _warn():
        version = '.'.join(six.text_type(x) for x in since)
        message = ['{} has been deprecated since {}'.format(old, version)]
        if remove:
            version = '.'.join(six.text_type(x) for x in remove)
            message.append(
                ' and will be removed by version {}'.format(version))
        message.append('.  Use {} instead.'.format(new))
        logger.warning(''.join(message))
        logger.debug(''.join(
                six.text_type(x) for x in traceback.format_stack()))

    def fget(self):
        _warn()
        return getattr(self, new)

    def fset(self, value):
        _warn()
        setattr(self, new, value)

    def decorator(dummy):
        return property(fget=fget, fset=fset, doc=doc)

    return decorator


def get_date(string):
    """Return a datetime object from a string.

    If no format matches the given date, raise a ValueError.
    """
    string = re.sub(' +', ' ', string)
    try:
        return dateutil.parser.parse(string)
    except (TypeError, ValueError):
        raise ValueError('{0!r} is not a valid date'.format(string))


@contextmanager
def pelican_open(filename):
    """Open a file and return its content"""

    with codecs.open(filename, encoding='utf-8') as infile:
        content = infile.read()
    if content[0] == codecs.BOM_UTF8.decode('utf8'):
        content = content[1:]
    yield content


def slugify(value, substitutions=()):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    Took from Django sources.
    """
    # TODO Maybe steal again from current Django 1.5dev
    value = Markup(value).striptags()
    # value must be unicode per se
    import unicodedata
    from unidecode import unidecode
    # unidecode returns str in Py2 and 3, so in Py2 we have to make
    # it unicode again
    value = unidecode(value)
    if isinstance(value, six.binary_type):
        value = value.decode('ascii')
    # still unicode
    value = unicodedata.normalize('NFKD', value).lower()
    for src, dst in substitutions:
        value = value.replace(src.lower(), dst.lower())
    value = re.sub('[^\w\s-]', '', value).strip()
    value = re.sub('[-\s]+', '-', value)
    # we want only ASCII chars
    value = value.encode('ascii', 'ignore')
    # but Pelican should generally use only unicode
    return value.decode('ascii')


def copy(source, destination):
    """Recursively copy source into destination.

    If source is a file, destination has to be a file as well.

    The function is able to copy either files or directories.

    :param source: the source file or directory
    :param destination: the destination file or directory
    """

    source_ = os.path.abspath(os.path.expanduser(source))
    destination_ = os.path.abspath(os.path.expanduser(destination))

    if not os.path.exists(destination_) and not os.path.isfile(source_):
        os.makedirs(destination_)

    def recurse(source, destination):
        for entry in os.listdir(source):
            entry_path = os.path.join(source, entry)
            if os.path.isdir(entry_path):
                entry_dest = os.path.join(destination, entry)
                if os.path.exists(entry_dest):
                    if not os.path.isdir(entry_dest):
                        raise IOError('Failed to copy {0} a directory.'
                                      .format(entry_dest))
                    recurse(entry_path, entry_dest)
                else:
                    shutil.copytree(entry_path, entry_dest)
            else:
                shutil.copy2(entry_path, destination)


    if os.path.isdir(source_):
        recurse(source_, destination_)

    elif os.path.isfile(source_):
        dest_dir = os.path.dirname(destination_)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        shutil.copy2(source_, destination_)
        logger.info('copying %s to %s' % (source_, destination_))
    else:
        logger.warning('skipped copy %s to %s' % (source_, destination_))


def clean_output_dir(path, retention):
    """Remove all files from output directory except those in retention list"""

    if not os.path.exists(path):
        logger.debug("Directory already removed: %s" % path)
        return

    if not os.path.isdir(path):
        try:
            os.remove(path)
        except Exception as e:
            logger.error("Unable to delete file %s; %s" % (path, str(e)))
        return

    # remove existing content from output folder unless in retention list
    for filename in os.listdir(path):
        file = os.path.join(path, filename)
        if any(filename == retain for retain in retention):
            logger.debug("Skipping deletion; %s is on retention list: %s" \
                         % (filename, file))
        elif os.path.isdir(file):
            try:
                shutil.rmtree(file)
                logger.debug("Deleted directory %s" % file)
            except Exception as e:
                logger.error("Unable to delete directory %s; %s" % (
                        file, str(e)))
        elif os.path.isfile(file) or os.path.islink(file):
            try:
                os.remove(file)
                logger.debug("Deleted file/link %s" % file)
            except Exception as e:
                logger.error("Unable to delete file %s; %s" % (file, str(e)))
        else:
            logger.error("Unable to delete %s, file type unknown" % file)


def get_relative_path(path):
    """Return the relative path from the given path to the root path."""
    components = split_all(path)
    if len(components) <= 1:
        return os.curdir
    else:
        parents = [os.pardir] * (len(components) - 1)
        return os.path.join(*parents)


def path_to_url(path):
    """Return the URL corresponding to a given path."""
    if os.sep == '/':
        return path
    else:
        return '/'.join(split_all(path))


def truncate_html_words(s, num, end_text='...'):
    """Truncates HTML to a certain number of words.

    (not counting tags and comments). Closes opened tags if they were correctly
    closed in the given html. Takes an optional argument of what should be used
    to notify that the string has been truncated, defaulting to ellipsis (...).

    Newlines in the HTML are preserved. (From the django framework).
    """
    length = int(num)
    if length <= 0:
        return ''
    html4_singlets = ('br', 'col', 'link', 'base', 'img', 'param', 'area',
                      'hr', 'input')

    # Set up regular expressions
    re_words = re.compile(r'&.*?;|<.*?>|(\w[\w-]*)', re.U)
    re_tag = re.compile(r'<(/)?([^ ]+?)(?: (/)| .*?)?>')
    # Count non-HTML words and keep note of open tags
    pos = 0
    end_text_pos = 0
    words = 0
    open_tags = []
    while words <= length:
        m = re_words.search(s, pos)
        if not m:
            # Checked through whole string
            break
        pos = m.end(0)
        if m.group(1):
            # It's an actual non-HTML word
            words += 1
            if words == length:
                end_text_pos = pos
            continue
        # Check for tag
        tag = re_tag.match(m.group(0))
        if not tag or end_text_pos:
            # Don't worry about non tags or tags after our truncate point
            continue
        closing_tag, tagname, self_closing = tag.groups()
        tagname = tagname.lower()  # Element names are always case-insensitive
        if self_closing or tagname in html4_singlets:
            pass
        elif closing_tag:
            # Check for match in open tags list
            try:
                i = open_tags.index(tagname)
            except ValueError:
                pass
            else:
                # SGML: An end tag closes, back to the matching start tag,
                # all unclosed intervening start tags with omitted end tags
                open_tags = open_tags[i + 1:]
        else:
            # Add it to the start of the open tags list
            open_tags.insert(0, tagname)
    if words <= length:
        # Don't try to close tags if we don't need to truncate
        return s
    out = s[:end_text_pos]
    if end_text:
        out += ' ' + end_text
    # Close any tags still open
    for tag in open_tags:
        out += '</%s>' % tag
    # Return string
    return out


def process_translations(content_list):
    """ Finds translation and returns them.

    Returns a tuple with two lists (index, translations).  Index list includes
    items in default language or items which have no variant in default
    language. Items with the `translation` metadata set to something else than
    `False` or `false` will be used as translations, unless all the items with
    the same slug have that metadata.

    For each content_list item, sets the 'translations' attribute.
    """
    content_list.sort(key=attrgetter('slug'))
    grouped_by_slugs = groupby(content_list, attrgetter('slug'))
    index = []
    translations = []

    for slug, items in grouped_by_slugs:
        items = list(items)
        # items with `translation` metadata will be used as translations…
        default_lang_items = list(filter(
                lambda i: i.metadata.get('translation', 'false').lower()
                        == 'false',
                items))
        # …unless all items with that slug are translations
        if not default_lang_items:
            default_lang_items = items

        # display warnings if several items have the same lang
        for lang, lang_items in groupby(items, attrgetter('lang')):
            lang_items = list(lang_items)
            len_ = len(lang_items)
            if len_ > 1:
                logger.warning('There are %s variants of "%s" with lang %s' \
                        % (len_, slug, lang))
                for x in lang_items:
                    logger.warning('    %s' % x.source_path)

        # find items with default language
        default_lang_items = list(filter(attrgetter('in_default_lang'),
                default_lang_items))

        # if there is no article with default language, take an other one
        if not default_lang_items:
            default_lang_items = items[:1]

        if not slug:
            logger.warning((
                    'empty slug for {!r}. '
                    'You can fix this by adding a title or a slug to your '
                    'content'
                    ).format(default_lang_items[0].source_path))
        index.extend(default_lang_items)
        translations.extend([x for x in items if x not in default_lang_items])
        for a in items:
            a.translations = [x for x in items if x != a]
    return index, translations


def folder_watcher(path, extensions, ignores=[]):
    '''Generator for monitoring a folder for modifications.

    Returns a boolean indicating if files are changed since last check.
    Returns None if there are no matching files in the folder'''

    def file_times(path):
        '''Return `mtime` for each file in path'''

        for root, dirs, files in os.walk(path):
            dirs[:] = [x for x in dirs if not x.startswith(os.curdir)]

            for f in files:
                if (f.endswith(tuple(extensions)) and
                    not any(fnmatch.fnmatch(f, ignore) for ignore in ignores)):
                    try:
                        yield os.stat(os.path.join(root, f)).st_mtime
                    except OSError as e:
                        logger.warning('Caught Exception: {}'.format(e))

    LAST_MTIME = 0
    while True:
        try:
            mtime = max(file_times(path))
            if mtime > LAST_MTIME:
                LAST_MTIME = mtime
                yield True
        except ValueError:
            yield None
        else:
            yield False


def file_watcher(path):
    '''Generator for monitoring a file for modifications'''
    LAST_MTIME = 0
    while True:
        if path:
            try:
                mtime = os.stat(path).st_mtime
            except OSError as e:
                logger.warning('Caught Exception: {}'.format(e))
                continue

            if mtime > LAST_MTIME:
                LAST_MTIME = mtime
                yield True
            else:
                yield False
        else:
            yield None


def set_date_tzinfo(d, tz_name=None):
    """Set the timezone for dates that don't have tzinfo"""
    if tz_name and not d.tzinfo:
        tz = pytz.timezone(tz_name)
        return tz.localize(d)
    return d


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(path):
            raise


def split_all(path):
    """Split a path into a list of components

    While os.path.split() splits a single component off the back of
    `path`, this function splits all components:

    >>> split_all(os.path.join('a', 'b', 'c'))
    ['a', 'b', 'c']
    """
    components = []
    path = path.lstrip('/')
    while path:
        head, tail = os.path.split(path)
        if tail:
            components.insert(0, tail)
        elif head == path:
            components.insert(0, head)
            break
        path = head
    return components


class FileDataCacher(object):
    '''Class that can cache data contained in files'''

    def __init__(self, settings, cache_name, caching_policy, load_policy):
        '''Load the specified cache within CACHE_PATH in settings

        only if *load_policy* is True,
        May use gzip if GZIP_CACHE ins settings is True.
        Sets caching policy according to *caching_policy*.
        '''
        self.settings = settings
        self._cache_path = os.path.join(self.settings['CACHE_PATH'],
                                        cache_name)
        self._cache_data_policy = caching_policy
        if self.settings['GZIP_CACHE']:
            import gzip
            self._cache_open = gzip.open
        else:
            self._cache_open = open
        if load_policy:
            try:
                with self._cache_open(self._cache_path, 'rb') as fhandle:
                    self._cache = pickle.load(fhandle)
            except (IOError, OSError) as err:
                logger.debug(('Cannot load cache {} (this is normal on first '
                    'run). Proceeding with empty cache.\n{}').format(
                        self._cache_path, err))
                self._cache = {}
            except pickle.UnpicklingError as err:
                logger.warning(('Cannot unpickle cache {}, cache may be using '
                    'an incompatible protocol (see pelican caching docs). '
                    'Proceeding with empty cache.\n{}').format(
                        self._cache_path, err))
                self._cache = {}
        else:
            self._cache = {}

    def cache_data(self, filename, data):
        '''Cache data for given file'''
        if self._cache_data_policy:
            self._cache[filename] = data

    def get_cached_data(self, filename, default=None):
        '''Get cached data for the given file

        if no data is cached, return the default object
        '''
        return self._cache.get(filename, default)

    def save_cache(self):
        '''Save the updated cache'''
        if self._cache_data_policy:
            try:
                mkdir_p(self.settings['CACHE_PATH'])
                with self._cache_open(self._cache_path, 'wb') as fhandle:
                    pickle.dump(self._cache, fhandle)
            except (IOError, OSError, pickle.PicklingError) as err:
                logger.warning('Could not save cache {}\n{}'.format(
                    self._cache_path, err))


class FileStampDataCacher(FileDataCacher):
    '''Subclass that also caches the stamp of the file'''

    def __init__(self, settings, cache_name, caching_policy, load_policy):
        '''This sublcass additionaly sets filestamp function
        and base path for filestamping operations
        '''
        super(FileStampDataCacher, self).__init__(settings, cache_name,
                                                  caching_policy,
                                                  load_policy)

        method = self.settings['CHECK_MODIFIED_METHOD']
        if method == 'mtime':
            self._filestamp_func = os.path.getmtime
        else:
            try:
                hash_func = getattr(hashlib, method)
                def filestamp_func(filename):
                    '''return hash of file contents'''
                    with open(filename, 'rb') as fhandle:
                        return hash_func(fhandle.read()).digest()
                self._filestamp_func = filestamp_func
            except AttributeError as err:
                logger.warning('Could not get hashing function\n{}'.format(
                    err))
                self._filestamp_func = None

    def cache_data(self, filename, data):
        '''Cache stamp and data for the given file'''
        stamp = self._get_file_stamp(filename)
        super(FileStampDataCacher, self).cache_data(filename, (stamp, data))

    def _get_file_stamp(self, filename):
        '''Check if the given file has been modified
        since the previous build.

        depending on CHECK_MODIFIED_METHOD
        a float may be returned for 'mtime',
        a hash for a function name in the hashlib module
        or an empty bytes string otherwise
        '''
        try:
            return self._filestamp_func(filename)
        except (IOError, OSError, TypeError) as err:
            logger.warning('Cannot get modification stamp for {}\n{}'.format(
                filename, err))
            return b''

    def get_cached_data(self, filename, default=None):
        '''Get the cached data for the given filename
        if the file has not been modified.

        If no record exists or file has been modified, return default.
        Modification is checked by comparing the cached
        and current file stamp.
        '''
        stamp, data = super(FileStampDataCacher, self).get_cached_data(
            filename, (None, default))
        if stamp != self._get_file_stamp(filename):
            return default
        return data


def is_selected_for_writing(settings, path):
    '''Check whether path is selected for writing
    according to the WRITE_SELECTED list

    If WRITE_SELECTED is an empty list (default),
    any path is selected for writing.
    '''
    if settings['WRITE_SELECTED']:
        return path in settings['WRITE_SELECTED']
    else:
        return True
        

########NEW FILE########
__FILENAME__ = writers
# -*- coding: utf-8 -*-
from __future__ import with_statement, unicode_literals, print_function
import six

import os
import locale
import logging

if not six.PY3:
    from codecs import open
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

from feedgenerator import Atom1Feed, Rss201rev2Feed
from jinja2 import Markup

from pelican.paginator import Paginator
from pelican.utils import (get_relative_path, path_to_url, set_date_tzinfo,
                           is_selected_for_writing)
from pelican import signals

logger = logging.getLogger(__name__)


class Writer(object):

    def __init__(self, output_path, settings=None):
        self.output_path = output_path
        self.reminder = dict()
        self.settings = settings or {}
        self._written_files = set()
        self._overridden_files = set()

    def _create_new_feed(self, feed_type, context):
        feed_class = Rss201rev2Feed if feed_type == 'rss' else Atom1Feed
        sitename = Markup(context['SITENAME']).striptags()
        feed = feed_class(
            title=sitename,
            link=(self.site_url + '/'),
            feed_url=self.feed_url,
            description=context.get('SITESUBTITLE', ''))
        return feed

    def _add_item_to_the_feed(self, feed, item):

        title = Markup(item.title).striptags()
        link = '%s/%s' % (self.site_url, item.url)
        feed.add_item(
            title=title,
            link=link,
            unique_id='tag:%s,%s:%s' % (urlparse(link).netloc,
                                        item.date.date(),
                                        urlparse(link).path.lstrip('/')),
            description=item.get_content(self.site_url),
            categories=item.tags if hasattr(item, 'tags') else None,
            author_name=getattr(item, 'author', ''),
            pubdate=set_date_tzinfo(
                item.modified if hasattr(item, 'modified') else item.date,
                self.settings.get('TIMEZONE', None)))

    def _open_w(self, filename, encoding, override=False):
        """Open a file to write some content to it.

        Exit if we have already written to that file, unless one (and no more
        than one) of the writes has the override parameter set to True.
        """
        if filename in self._overridden_files:
            if override:
                raise RuntimeError('File %s is set to be overridden twice'
                                   % filename)
            else:
                logger.info('skipping %s' % filename)
                filename = os.devnull
        elif filename in self._written_files:
            if override:
                logger.info('overwriting %s' % filename)
            else:
                raise RuntimeError('File %s is to be overwritten' % filename)
        if override:
            self._overridden_files.add(filename)
        self._written_files.add(filename)
        return open(filename, 'w', encoding=encoding)

    def write_feed(self, elements, context, path=None, feed_type='atom'):
        """Generate a feed with the list of articles provided

        Return the feed. If no path or output_path is specified, just
        return the feed object.

        :param elements: the articles to put on the feed.
        :param context: the context to get the feed metadata.
        :param path: the path to output.
        :param feed_type: the feed type to use (atom or rss)
        """
        if not is_selected_for_writing(self.settings, path):
            return
        old_locale = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, str('C'))
        try:
            self.site_url = context.get(
                'SITEURL', path_to_url(get_relative_path(path)))

            self.feed_domain = context.get('FEED_DOMAIN')
            self.feed_url = '{}/{}'.format(self.feed_domain, path)

            feed = self._create_new_feed(feed_type, context)

            max_items = len(elements)
            if self.settings['FEED_MAX_ITEMS']:
                max_items = min(self.settings['FEED_MAX_ITEMS'], max_items)
            for i in range(max_items):
                self._add_item_to_the_feed(feed, elements[i])

            if path:
                complete_path = os.path.join(self.output_path, path)
                try:
                    os.makedirs(os.path.dirname(complete_path))
                except Exception:
                    pass

                encoding = 'utf-8' if six.PY3 else None
                with self._open_w(complete_path, encoding) as fp:
                    feed.write(fp, 'utf-8')
                    logger.info('writing %s' % complete_path)
            return feed
        finally:
            locale.setlocale(locale.LC_ALL, old_locale)

    def write_file(self, name, template, context, relative_urls=False,
                   paginated=None, override_output=False, **kwargs):
        """Render the template and write the file.

        :param name: name of the file to output
        :param template: template to use to generate the content
        :param context: dict to pass to the templates.
        :param relative_urls: use relative urls or absolutes ones
        :param paginated: dict of article list to paginate - must have the
            same length (same list in different orders)
        :param override_output: boolean telling if we can override previous
            output with the same name (and if next files written with the same
            name should be skipped to keep that one)
        :param **kwargs: additional variables to pass to the templates
        """

        if name is False or name == "" or\
           not is_selected_for_writing(self.settings,\
               os.path.join(self.output_path, name)):
            return
        elif not name:
            # other stuff, just return for now
            return

        def _write_file(template, localcontext, output_path, name, override):
            """Render the template write the file."""
            old_locale = locale.setlocale(locale.LC_ALL)
            locale.setlocale(locale.LC_ALL, str('C'))
            try:
                output = template.render(localcontext)
            finally:
                locale.setlocale(locale.LC_ALL, old_locale)
            path = os.path.join(output_path, name)
            try:
                os.makedirs(os.path.dirname(path))
            except Exception:
                pass

            with self._open_w(path, 'utf-8', override=override) as f:
                f.write(output)
            logger.info('writing {}'.format(path))

            # Send a signal to say we're writing a file with some specific
            # local context.
            signals.content_written.send(path, context=localcontext)

        localcontext = context.copy()
        if relative_urls:
            relative_url = path_to_url(get_relative_path(name))
            context['localsiteurl'] = relative_url
            localcontext['SITEURL'] = relative_url

        localcontext['output_file'] = name
        localcontext.update(kwargs)

        # pagination
        if paginated:

            # pagination needed, init paginators
            paginators = {key: Paginator(name, val, self.settings)
                          for key, val in paginated.items()}

            # generated pages, and write
            for page_num in range(list(paginators.values())[0].num_pages):
                paginated_localcontext = localcontext.copy()
                for key in paginators.keys():
                    paginator = paginators[key]
                    previous_page = paginator.page(page_num) \
                        if page_num > 0 else None
                    page = paginator.page(page_num + 1)
                    next_page = paginator.page(page_num + 2) \
                        if page_num + 1 < paginator.num_pages else None
                    paginated_localcontext.update(
                        {'%s_paginator' % key: paginator,
                         '%s_page' % key: page,
                         '%s_previous_page' % key: previous_page,
                         '%s_next_page' % key: next_page})

                _write_file(template, paginated_localcontext, self.output_path,
                            page.save_as, override_output)
        else:
            # no pagination
            _write_file(template, localcontext, self.output_path, name,
                        override_output)

########NEW FILE########
__FILENAME__ = pelican.conf
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

AUTHOR = 'Alexis Métaireau'
SITENAME = "Alexis' log"
SITEURL = 'http://blog.notmyidea.org'
TIMEZONE = "Europe/Paris"

# can be useful in development, but set to False when you're ready to publish
RELATIVE_URLS = True

GITHUB_URL = 'http://github.com/ametaireau/'
DISQUS_SITENAME = "blog-notmyidea"
PDF_GENERATOR = False
REVERSE_CATEGORY_ORDER = True
LOCALE = "C"
DEFAULT_PAGINATION = 4
DEFAULT_DATE = (2012, 3, 2, 14, 1, 1)

FEED_ALL_RSS = 'feeds/all.rss.xml'
CATEGORY_FEED_RSS = 'feeds/%s.rss.xml'

LINKS = (('Biologeek', 'http://biologeek.org'),
         ('Filyb', "http://filyb.info/"),
         ('Libert-fr', "http://www.libert-fr.com"),
         ('N1k0', "http://prendreuncafe.com/blog/"),
         ('Tarek Ziadé', "http://ziade.org/blog"),
         ('Zubin Mithra', "http://zubin71.wordpress.com/"),)

SOCIAL = (('twitter', 'http://twitter.com/ametaireau'),
          ('lastfm', 'http://lastfm.com/user/akounet'),
          ('github', 'http://github.com/ametaireau'),)

# global metadata to all the contents
DEFAULT_METADATA = (('yeah', 'it is'),)

# path-specific metadata
EXTRA_PATH_METADATA = {
    'extra/robots.txt': {'path': 'robots.txt'},
    }

# static paths will be copied without parsing their contents
STATIC_PATHS = [
    'pictures',
    'extra/robots.txt',
    ]

# custom page generated with a jinja2 template
TEMPLATE_PAGES = {'pages/jinja2_template.html': 'jinja2_template.html'}

# code blocks with line numbers
PYGMENTS_RST_OPTIONS = {'linenos': 'table'}

# foobar will not be used, because it's not in caps. All configuration keys
# have to be in caps
foobar = "barbaz"

########NEW FILE########
