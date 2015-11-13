__FILENAME__ = assets
# -*- coding: utf-8 -*-
"""
Asset management plugin for Pelican
===================================

This plugin allows you to use the `webassets`_ module to manage assets such as
CSS and JS files.

The ASSET_URL is set to a relative url to honor Pelican's RELATIVE_URLS
setting. This requires the use of SITEURL in the templates::

    <link rel="stylesheet" href="{{ SITEURL }}/{{ ASSET_URL }}">

.. _webassets: https://webassets.readthedocs.org/

"""
from __future__ import unicode_literals

import os
import logging

from pelican import signals
logger = logging.getLogger(__name__)

try:
    import webassets
    from webassets import Environment
    from webassets.ext.jinja2 import AssetsExtension
except ImportError:
    webassets = None

def add_jinja2_ext(pelican):
    """Add Webassets to Jinja2 extensions in Pelican settings."""

    pelican.settings['JINJA_EXTENSIONS'].append(AssetsExtension)


def create_assets_env(generator):
    """Define the assets environment and pass it to the generator."""

    theme_static_dir = generator.settings['THEME_STATIC_DIR']
    assets_src = os.path.join(generator.output_path, theme_static_dir)
    generator.env.assets_environment = Environment(
        assets_src, theme_static_dir)

    if 'ASSET_CONFIG' in generator.settings:
        for item in generator.settings['ASSET_CONFIG']:
            generator.env.assets_environment.config[item[0]] = item[1]

    if 'ASSET_BUNDLES' in generator.settings:
        for name, args, kwargs in generator.settings['ASSET_BUNDLES']:
            generator.env.assets_environment.register(name, *args, **kwargs)

    if logging.getLevelName(logger.getEffectiveLevel()) == "DEBUG":
        generator.env.assets_environment.debug = True

    if 'ASSET_SOURCE_PATHS' in generator.settings:
        # the default load path gets overridden if additional paths are
        # specified, add it back
        generator.env.assets_environment.append_path(assets_src)
        for path in generator.settings['ASSET_SOURCE_PATHS']:
            full_path = os.path.join(generator.theme, path)
            generator.env.assets_environment.append_path(full_path)


def register():
    """Plugin registration."""
    if webassets:
        signals.initialized.connect(add_jinja2_ext)
        signals.generator_init.connect(create_assets_env)
    else:
        logger.warning('`assets` failed to load dependency `webassets`.'
                       '`assets` plugin not loaded.')

########NEW FILE########
__FILENAME__ = test_assets
# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

import hashlib
import locale
import os
from codecs import open
from tempfile import mkdtemp
from shutil import rmtree
import unittest
import subprocess

from pelican import Pelican
from pelican.settings import read_settings

CUR_DIR = os.path.dirname(__file__)
THEME_DIR = os.path.join(CUR_DIR, 'test_data')
CSS_REF = open(os.path.join(THEME_DIR, 'static', 'css',
                            'style.min.css')).read()
CSS_HASH = hashlib.md5(CSS_REF).hexdigest()[0:8]


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



@unittest.skipUnless(module_exists('webassets'), "webassets isn't installed")
@skipIfNoExecutable(['scss', '-v'])
@skipIfNoExecutable(['cssmin', '--version'])
class TestWebAssets(unittest.TestCase):
    """Base class for testing webassets."""

    def setUp(self, override=None):
        import assets
        self.temp_path = mkdtemp(prefix='pelicantests.')
        settings = {
            'PATH': os.path.join(os.path.dirname(CUR_DIR), 'test_data', 'content'),
            'OUTPUT_PATH': self.temp_path,
            'PLUGINS': [assets],
            'THEME': THEME_DIR,
            'LOCALE': locale.normalize('en_US'),
        }
        if override:
            settings.update(override)

        self.settings = read_settings(override=settings)
        pelican = Pelican(settings=self.settings)
        pelican.run()

    def tearDown(self):
        rmtree(self.temp_path)

    def check_link_tag(self, css_file, html_file):
        """Check the presence of `css_file` in `html_file`."""

        link_tag = ('<link rel="stylesheet" href="{css_file}">'
                    .format(css_file=css_file))
        html = open(html_file).read()
        self.assertRegexpMatches(html, link_tag)


class TestWebAssetsRelativeURLS(TestWebAssets):
    """Test pelican with relative urls."""


    def setUp(self):
        TestWebAssets.setUp(self, override={'RELATIVE_URLS': True})

    def test_jinja2_ext(self):
        # Test that the Jinja2 extension was correctly added.

        from webassets.ext.jinja2 import AssetsExtension
        self.assertIn(AssetsExtension, self.settings['JINJA_EXTENSIONS'])

    def test_compilation(self):
        # Compare the compiled css with the reference.

        gen_file = os.path.join(self.temp_path, 'theme', 'gen',
                                'style.{0}.min.css'.format(CSS_HASH))
        self.assertTrue(os.path.isfile(gen_file))

        css_new = open(gen_file).read()
        self.assertEqual(css_new, CSS_REF)

    def test_template(self):
        # Look in the output files for the link tag.

        css_file = './theme/gen/style.{0}.min.css'.format(CSS_HASH)
        html_files = ['index.html', 'archives.html',
                      'this-is-a-super-article.html']
        for f in html_files:
            self.check_link_tag(css_file, os.path.join(self.temp_path, f))

        self.check_link_tag(
            '../theme/gen/style.{0}.min.css'.format(CSS_HASH),
            os.path.join(self.temp_path, 'category/yeah.html'))


class TestWebAssetsAbsoluteURLS(TestWebAssets):
    """Test pelican with absolute urls."""

    def setUp(self):
        TestWebAssets.setUp(self, override={'RELATIVE_URLS': False,
                                            'SITEURL': 'http://localhost'})

    def test_absolute_url(self):
        # Look in the output files for the link tag with absolute url.

        css_file = ('http://localhost/theme/gen/style.{0}.min.css'
                    .format(CSS_HASH))
        html_files = ['index.html', 'archives.html',
                      'this-is-a-super-article.html']
        for f in html_files:
            self.check_link_tag(css_file, os.path.join(self.temp_path, f))

########NEW FILE########
__FILENAME__ = better_figures_and_images
"""
Better Figures & Images
------------------------

This plugin:

- Adds a style="width: ???px; height: auto;" to each image in the content
- Also adds the width of the contained image to any parent div.figures.
    - If RESPONSIVE_IMAGES == True, also adds style="max-width: 100%;"
- Corrects alt text: if alt == image filename, set alt = ''

TODO: Need to add a test.py for this plugin.

"""

from os import path, access, R_OK

from pelican import signals

from bs4 import BeautifulSoup
from PIL import Image

import logging
logger = logging.getLogger(__name__)

def content_object_init(instance):

    if instance._content is not None:
        content = instance._content
        soup = BeautifulSoup(content)

        if 'img' in content:
            for img in soup('img'):
                logger.debug('Better Fig. PATH: %s', instance.settings['PATH'])
                logger.debug('Better Fig. img.src: %s', img['src'])

                img_path, img_filename = path.split(img['src'])

                logger.debug('Better Fig. img_path: %s', img_path)
                logger.debug('Better Fig. img_fname: %s', img_filename)

                # Strip off {filename}, |filename| or /static
                if img_path.startswith(('{filename}', '|filename|')):
                    img_path = img_path[10:]
                elif img_path.startswith('/static'):
                    img_path = img_path[7:]
                else:
                    logger.warning('Better Fig. Error: img_path should start with either {filename}, |filename| or /static')

                # Build the source image filename
                src = instance.settings['PATH'] + img_path + '/' + img_filename

                logger.debug('Better Fig. src: %s', src)
                if not (path.isfile(src) and access(src, R_OK)):
                    logger.error('Better Fig. Error: image not found: {}'.format(src))

                # Open the source image and query dimensions; build style string
                im = Image.open(src)
                extra_style = 'width: {}px; height: auto;'.format(im.size[0])

                if instance.settings['RESPONSIVE_IMAGES']:
                    extra_style += ' max-width: 100%;'

                if img.get('style'):
                    img['style'] += extra_style
                else:
                    img['style'] = extra_style

                if img['alt'] == img['src']:
                    img['alt'] = ''

                fig = img.find_parent('div', 'figure')
                if fig:
                    if fig.get('style'):
                        fig['style'] += extra_style
                    else:
                        fig['style'] = extra_style

        instance._content = soup.decode()


def register():
    signals.content_object_init.connect(content_object_init)

########NEW FILE########
__FILENAME__ = clean_summary
"""
Clean Summary
-------------

adds option to specify maximum number of images to appear in article summary
also adds option to include an image by default if one exists in your article
"""

from pelican import signals
from pelican.contents import Content, Article
from bs4 import BeautifulSoup
from six import text_type

def clean_summary(instance):
    if "CLEAN_SUMMARY_MAXIMUM" in instance.settings:
        maximum_images = instance.settings["CLEAN_SUMMARY_MAXIMUM"]
    else:
        maximum_images = 0
    if "CLEAN_SUMMARY_MINIMUM_ONE" in instance.settings:
        minimum_one = instance.settings['CLEAN_SUMMARY_MINIMUM_ONE']
    else:
        minimum_one = False
    if type(instance) == Article:
        summary = instance.summary
        summary = BeautifulSoup(instance.summary, 'html.parser')
        images = summary.findAll('img')
        if (len(images) > maximum_images):
            for image in images[maximum_images:]:
                image.extract()
        if len(images) < 1 and minimum_one: #try to find one
            content = BeautifulSoup(instance.content, 'html.parser')
            first_image = content.find('img')
            if first_image:
                summary.insert(0, first_image)
        instance._summary = text_type(summary)

def register():
    signals.content_object_init.connect(clean_summary)

########NEW FILE########
__FILENAME__ = code_include
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os.path

from docutils import io, nodes, statemachine, utils
from docutils.utils.error_reporting import SafeString, ErrorString
from docutils.parsers.rst import directives, Directive

from pelican.rstdirectives import Pygments


class CodeInclude(Directive):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'lexer': directives.unchanged,
                   'encoding': directives.encoding,
                   'tab-width': int,
                   'start-line': int,
                   'end-line': int}

    def run(self):
        """Include a file as part of the content of this reST file."""
        if not self.state.document.settings.file_insertion_enabled:
            raise self.warning('"%s" directive disabled.' % self.name)
        source = self.state_machine.input_lines.source(
            self.lineno - self.state_machine.input_offset - 1)
        source_dir = os.path.dirname(os.path.abspath(source))

        path = directives.path(self.arguments[0])
        path = os.path.normpath(os.path.join(source_dir, path))
        path = utils.relative_path(None, path)
        path = nodes.reprunicode(path)

        encoding = self.options.get(
            'encoding', self.state.document.settings.input_encoding)
        e_handler = self.state.document.settings.input_encoding_error_handler
        tab_width = self.options.get(
            'tab-width', self.state.document.settings.tab_width)

        try:
            self.state.document.settings.record_dependencies.add(path)
            include_file = io.FileInput(source_path=path,
                                        encoding=encoding,
                                        error_handler=e_handler)
        except UnicodeEncodeError as error:
            raise self.severe('Problems with "%s" directive path:\n'
                              'Cannot encode input file path "%s" '
                              '(wrong locale?).' %
                              (self.name, SafeString(path)))
        except IOError as error:
            raise self.severe('Problems with "%s" directive path:\n%s.' %
                              (self.name, ErrorString(error)))
        startline = self.options.get('start-line', None)
        endline = self.options.get('end-line', None)
        try:
            if startline or (endline is not None):
                lines = include_file.readlines()
                rawtext = ''.join(lines[startline:endline])
            else:
                rawtext = include_file.read()
        except UnicodeError as error:
            raise self.severe('Problem with "%s" directive:\n%s' %
                              (self.name, ErrorString(error)))

        include_lines = statemachine.string2lines(rawtext, tab_width,
                                                  convert_whitespace=True)

        # default lexer to 'text'
        lexer = self.options.get('lexer', 'text')

        self.options['source'] = path
        codeblock = Pygments(self.name,
                             [lexer],  # arguments
                             {},  # no options for this directive
                             include_lines,  # content
                             self.lineno,
                             self.content_offset,
                             self.block_text,
                             self.state,
                             self.state_machine)
        return codeblock.run()


def register():
    directives.register_directive('code-include', CodeInclude)

########NEW FILE########
__FILENAME__ = creole_reader
#-*- conding: utf-8 -*-

'''
Creole Reader
-------------

This plugins allows you to write your posts using the wikicreole syntax. Give to
these files the creole extension.
For the syntax, look at: http://www.wikicreole.org/
'''

from pelican import readers
from pelican import signals
from pelican import settings

from pelican.utils import pelican_open

try:
    from creole import creole2html
    creole = True
except ImportError:
    creole = False

try:
    from pygments import lexers
    from pygments.formatters import HtmlFormatter
    from pygments import highlight
    PYGMENTS = True
except:
    PYGMENTS = False

class CreoleReader(readers.BaseReader):
    enabled = creole

    file_extensions = ['creole']

    def __init__(self, settings):
        super(CreoleReader, self).__init__(settings)

    def _parse_header_macro(self, text):
        for line in text.split('\n'):
            name, value = line.split(':')
            name, value = name.strip(), value.strip()
            if name == 'title':
                self._metadata[name] = value
            else:
                self._metadata[name] = self.process_metadata(name, value)
        return u''

    def _no_highlight(self, text):
        html = u'\n<pre><code>{}</code></pre>\n'.format(text)
        return html

    def _get_lexer(self, source_type, code):
        try:
            return lexers.get_lexer_by_name(source_type)
        except:
            return lexers.guess_lexer(code)

    def _get_formatter(self):
        formatter = HtmlFormatter(lineos = True, encoding='utf-8',
                                  style='colorful', outencoding='utf-8',
                                  cssclass='pygments')
        return formatter

    def _parse_code_macro(self, ext, text):
        if not PYGMENTS:
            return self._no_highlight(text)

        try:
            source_type = ''
            if '.' in ext:
                source_type = ext.strip().split('.')[1]
            else:
                source_type = ext.strip()
        except IndexError:
            source_type = ''
        lexer = self._get_lexer(source_type, text)
        formatter = self._get_formatter()

        try:
            return highlight(text, lexer, formatter).decode('utf-8')
        except:
            return self._no_highlight(text)

    # You need to have a read method, which takes a filename and returns
    # some content and the associated metadata.
    def read(self, source_path):
        """Parse content and metadata of creole files"""

        self._metadata = {}
        with pelican_open(source_path) as text:
            content = creole2html(text, macros={'header': self._parse_header_macro,
                                            'code': self._parse_code_macro})
        return content, self._metadata

def add_reader(readers):
    readers.reader_classes['creole'] = CreoleReader

def register():
    signals.readers_init.connect(add_reader)

########NEW FILE########
__FILENAME__ = custom_article_urls
# -*- coding: utf-8 -*-
"""
@Author: Alistair Magee

Adds ability to specify custom urls for different categories 
(or subcategories if using subcategory plugin) of article
using a dictionary stored in pelican settings file as
{category: {article_url_structure: stirng, article_save_as: string}}
"""
from pelican import signals
from pelican.contents import Content, Category
from six import text_type

def custom_url(generator, metadata):
    if 'CUSTOM_ARTICLE_URLS' in generator.settings:
        custom_urls = generator.settings['CUSTOM_ARTICLE_URLS']
        category = text_type(metadata['category'])
        pattern_matched = {}
        
        if category in custom_urls:
            pattern_matched = custom_urls[category]

        if 'subcategories' in metadata: #using subcategory plugin
            for subcategory in metadata['subcategories']:
                if subcategory in custom_urls:
                    pattern_matched = custom_urls[subcategory]

        if pattern_matched:
            #only alter url if hasn't been set in the metdata
            if ('url', 'save_as') in metadata:
                """ if both url and save_as are set in the metadata already
                then there is already a custom url set, skip this one
                """
                pass
            else:
                temp_article = Content(None, metadata=metadata)
                url_format = pattern_matched['URL']
                save_as_format = pattern_matched['SAVE_AS']
                url = url_format.format(**temp_article.url_format)
                save_as = save_as_format.format(**temp_article.url_format)
                metadata.update({'url': url, 'save_as': save_as})

        
def register():
    signals.article_generator_context.connect(custom_url)

########NEW FILE########
__FILENAME__ = disqus_static
# -*- coding: utf-8 -*-
"""
Disqus static comment plugin for Pelican
====================================
This plugin adds a disqus_comments property to all articles.          
Comments are fetched at generation time using disqus API.
"""

from disqusapi import DisqusAPI, Paginator
from pelican import signals

def initialized(pelican):
    from pelican.settings import DEFAULT_CONFIG
    DEFAULT_CONFIG.setdefault('DISQUS_SECRET_KEY', '')
    DEFAULT_CONFIG.setdefault('DISQUS_PUBLIC_KEY', '')
    if pelican:
        pelican.settings.setdefault('DISQUS_SECRET_KEY', '')
        pelican.settings.setdefault('DISQUS_PUBLIC_KEY', '')

def disqus_static(generator):
    disqus = DisqusAPI(generator.settings['DISQUS_SECRET_KEY'], 
                       generator.settings['DISQUS_PUBLIC_KEY'])
    # first retrieve the threads
    threads = Paginator(disqus.threads.list, 
                        forum=generator.settings['DISQUS_SITENAME'])
    # build a {thread_id: title} dict
    thread_dict = {}
    for thread in threads:
        thread_dict[thread['id']] = thread['title']

    # now retrieve the posts
    posts = Paginator(disqus.posts.list, 
                      forum=generator.settings['DISQUS_SITENAME'])

    # build a {post_id: [child_post1, child_post2, ...]} dict
    child_dict = {}
    for post in posts:
        if post['id'] not in child_dict.keys():
            child_dict[post['id']] = []
        if post['parent'] is not None:
            if str(post['parent']) not in child_dict.keys():
                child_dict[str(post['parent'])] = []
            child_dict[str(post['parent'])].append(post)

    # build a {title: [post1, post2, ...]} dict
    post_dict = {}
    for post in posts:
        build_post_dict(post_dict, child_dict, thread_dict, post)

    for article in generator.articles:
        if article.title in post_dict:
            article.disqus_comments = post_dict[article.title]
            article.disqus_comment_count = sum([
                postcounter(post) for post in post_dict[article.title]])

def postcounter(node):
    return 1 + sum([postcounter(n) for n in node['children']])

def build_post_dict(post_dict, child_dict, thread_dict, post):
    if post['thread'] not in thread_dict.keys():
        return # invalid thread, should never happen

    build_child_dict(child_dict, post)

    if post['parent'] is not None:
        return # this is a child post, don't want to display it here

    if thread_dict[post['thread']] not in post_dict.keys():
        post_dict[thread_dict[post['thread']]] = []
    post_dict[thread_dict[post['thread']]].append(post)

def build_child_dict(child_dict, post):
    post['children'] = child_dict[post['id']]
    for child in child_dict[post['id']]:
        build_child_dict(child_dict, child)

def register():
    signals.initialized.connect(initialized)
    signals.article_generator_finalized.connect(disqus_static)

########NEW FILE########
__FILENAME__ = extract_toc
"""
Extract Table of Content
========================

This plugin allows you to extract table of contents (ToC) from article.content
and place it in its own article.toc variable.
"""

from os import path
from bs4 import BeautifulSoup
from pelican import signals, readers, contents


def extract_toc(content):
    if isinstance(content, contents.Static):
        return
    soup = BeautifulSoup(content._content,'html.parser')
    filename = content.source_path
    extension = path.splitext(filename)[1][1:]
    toc = ''
    # if it is a Markdown file
    if extension in readers.MarkdownReader.file_extensions:
        toc = soup.find('div', class_='toc')
    # else if it is a reST file
    elif extension in readers.RstReader.file_extensions:
        toc = soup.find('div', class_='contents topic')
    if toc:
        toc.extract()
        content._content = soup.decode()
        content.toc = toc.decode()


def register():
    signals.content_object_init.connect(extract_toc)

########NEW FILE########
__FILENAME__ = feed_summary
# -*- coding: utf-8 -*-
"""
Feed Summary
============

This plugin allows summaries to be used in feeds instead of the full length article.
"""

from __future__ import unicode_literals

from jinja2 import Markup

import six
if not six.PY3:
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

from pelican import signals
from pelican.writers import Writer
from pelican.utils import set_date_tzinfo

from .magic_set import magic_set

class FeedSummaryWriter(Writer):
    def _add_item_to_the_feed(self, feed, item):
        if self.settings['FEED_USE_SUMMARY']:
            title = Markup(item.title).striptags()
            link = '%s/%s' % (self.site_url, item.url)
            feed.add_item(
                title=title,
                link=link,
                unique_id='tag:%s,%s:%s' % (urlparse(link).netloc,
                                            item.date.date(),
                                            urlparse(link).path.lstrip('/')),
                description=item.summary if hasattr(item, 'summary') else item.get_content(self.site_url),
                categories=item.tags if hasattr(item, 'tags') else None,
                author_name=getattr(item, 'author', ''),
                pubdate=set_date_tzinfo(item.modified if hasattr(item, 'modified') else item.date,
                    self.settings.get('TIMEZONE', None)))
        else:
            super(FeedSummaryWriter, self)._add_item_to_the_feed(feed, item)

def set_feed_use_summary_default(pelican_object):
    # modifying DEFAULT_CONFIG doesn't have any effect at this point in pelican setup
    # everybody who uses DEFAULT_CONFIG is already used/copied it or uses the pelican_object.settings copy.

    pelican_object.settings.setdefault('FEED_USE_SUMMARY', False)

def patch_pelican_writer(pelican_object):
    @magic_set(pelican_object)
    def get_writer(self):
        return FeedSummaryWriter(self.output_path,settings=self.settings)

def register():
    signals.initialized.connect(set_feed_use_summary_default)
    signals.initialized.connect(patch_pelican_writer)

########NEW FILE########
__FILENAME__ = magic_set
import types
import inspect

# Modifies class methods (or instances of them) on the fly
# http://blog.ianbicking.org/2007/08/08/opening-python-classes/
# http://svn.colorstudy.com/home/ianb/recipes/magicset.py

def magic_set(obj):
    """
Adds a function/method to an object. Uses the name of the first
argument as a hint about whether it is a method (``self``), class
method (``cls`` or ``klass``), or static method (anything else).
Works on both instances and classes.

>>> class color:
... def __init__(self, r, g, b):
... self.r, self.g, self.b = r, g, b
>>> c = color(0, 1, 0)
>>> c # doctest: +ELLIPSIS
<__main__.color instance at ...>
>>> @magic_set(color)
... def __repr__(self):
... return '<color %s %s %s>' % (self.r, self.g, self.b)
>>> c
<color 0 1 0>
>>> @magic_set(color)
... def red(cls):
... return cls(1, 0, 0)
>>> color.red()
<color 1 0 0>
>>> c.red()
<color 1 0 0>
>>> @magic_set(color)
... def name():
... return 'color'
>>> color.name()
'color'
>>> @magic_set(c)
... def name(self):
... return 'red'
>>> c.name()
'red'
>>> @magic_set(c)
... def name(cls):
... return cls.__name__
>>> c.name()
'color'
>>> @magic_set(c)
... def pr(obj):
... print obj
>>> c.pr(1)
1
"""
    def decorator(func):
        is_class = (isinstance(obj, type)
                    or isinstance(obj, types.ClassType))
        args, varargs, varkw, defaults = inspect.getargspec(func)
        if not args or args[0] not in ('self', 'cls', 'klass'):
            # Static function/method
            if is_class:
                replacement = staticmethod(func)
            else:
                replacement = func
        elif args[0] == 'self':
            if is_class:
                replacement = func
            else:
                def replacement(*args, **kw):
                    return func(obj, *args, **kw)
                try:
                    replacement.func_name = func.func_name
                except:
                    pass
        else:
            if is_class:
                replacement = classmethod(func)
            else:
                def replacement(*args, **kw):
                    return func(obj.__class__, *args, **kw)
                try:
                    replacement.func_name = func.func_name
                except:
                    pass
        setattr(obj, func.func_name, replacement)
        return replacement
    return decorator
        
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    


########NEW FILE########
__FILENAME__ = gallery
import os
from pelican import signals


def add_gallery_post(generator):

    contentpath = generator.settings.get('PATH')
    gallerycontentpath = os.path.join(contentpath,'images/gallery')

    for article in generator.articles:
        if 'gallery' in article.metadata.keys():
            album = article.metadata.get('gallery')
            galleryimages = []

            articlegallerypath=os.path.join(gallerycontentpath, album)

            if(os.path.isdir(articlegallerypath)):
                for i in os.listdir(articlegallerypath):
                    if os.path.isfile(os.path.join(os.path.join(gallerycontentpath, album), i)):
                        galleryimages.append(i)

            article.album = album
            article.galleryimages = sorted(galleryimages)


def generate_gallery_page(generator):

    contentpath = generator.settings.get('PATH')
    gallerycontentpath = os.path.join(contentpath,'images/gallery')

    for page in generator.pages:
        if page.metadata.get('template') == 'gallery':
            gallery = dict()

            for a in os.listdir(gallerycontentpath):
                if os.path.isdir(os.path.join(gallerycontentpath, a)):

                    for i in os.listdir(os.path.join(gallerycontentpath, a)):
                        if os.path.isfile(os.path.join(os.path.join(gallerycontentpath, a), i)):
                            gallery.setdefault(a, []).append(i)
                    gallery[a].sort()

            page.gallery=gallery


def register():
    signals.article_generator_finalized.connect(add_gallery_post)
    signals.page_generator_finalized.connect(generate_gallery_page)

########NEW FILE########
__FILENAME__ = github_activity
# -*- coding: utf-8 -*-

# NEEDS WORK
"""
Copyright (c) Marco Milanesi <kpanic@gnufunk.org>

Github Activity
---------------
A plugin to list your Github Activity
"""

from __future__ import unicode_literals, print_function

import logging
logger = logging.getLogger(__name__)

from pelican import signals


class GitHubActivity():
    """
        A class created to fetch github activity with feedparser
    """
    def __init__(self, generator):
        import feedparser
        self.activities = feedparser.parse(
            generator.settings['GITHUB_ACTIVITY_FEED'])
        self.max_entries = generator.settings['GITHUB_ACTIVITY_MAX_ENTRIES'] 

    def fetch(self):
        """
            returns a list of html snippets fetched from github actitivy feed
        """

        entries = []
        for activity in self.activities['entries']:
            entries.append(
                    [element for element in [activity['title'],
                        activity['content'][0]['value']]])

        return entries[0:self.max_entries]


def fetch_github_activity(gen, metadata):
    """
        registered handler for the github activity plugin
        it puts in generator.context the html needed to be displayed on a
        template
    """

    if 'GITHUB_ACTIVITY_FEED' in gen.settings.keys():
        gen.context['github_activity'] = gen.plugin_instance.fetch()


def feed_parser_initialization(generator):
    """
        Initialization of feed parser
    """

    generator.plugin_instance = GitHubActivity(generator)


def register():
    """
        Plugin registration
    """
    try:
        signals.article_generator_init.connect(feed_parser_initialization)
        signals.article_generator_context.connect(fetch_github_activity)
    except ImportError:
        logger.warning('`github_activity` failed to load dependency `feedparser`.'
                       '`github_activity` plugin not loaded.')

########NEW FILE########
__FILENAME__ = global_license
"""
License plugin for Pelican
==========================

This plugin allows you to define a LICENSE setting and adds the contents of that
license variable to the article's context, making that variable available to use
from within your theme's templates.
"""

from pelican import signals

def add_license(generator, metadata):
    if 'license' not in metadata.keys()\
        and 'LICENSE' in generator.settings.keys():
            metadata['license'] = generator.settings['LICENSE']

def register():
    signals.article_generator_context.connect(add_license)

########NEW FILE########
__FILENAME__ = goodreads_activity
# -*- coding: utf-8 -*-
"""
Goodreads Activity
==================

A Pelican plugin to lists books from your Goodreads shelves.

Copyright (c) Talha Mansoor
"""

from __future__ import unicode_literals

import logging
logger = logging.getLogger(__name__)

from pelican import signals


class GoodreadsActivity():
    def __init__(self, generator):
        import feedparser
        self.activities = feedparser.parse(
            generator.settings['GOODREADS_ACTIVITY_FEED'])

    def fetch(self):
        goodreads_activity = {
            'shelf_title': self.activities.feed.title,
            'books': []
        }
        for entry in self.activities['entries']:
            book = {
                'title': entry.title,
                'author': entry.author_name,
                'link': entry.link,
                'l_cover': entry.book_large_image_url,
                'm_cover': entry.book_medium_image_url,
                's_cover': entry.book_small_image_url,
                'description': entry.book_description,
                'rating': entry.user_rating,
                'review': entry.user_review,
                'tags': entry.user_shelves
            }
            goodreads_activity['books'].append(book)

        return goodreads_activity


def fetch_goodreads_activity(gen, metadata):
    if 'GOODREADS_ACTIVITY_FEED' in gen.settings:
        gen.context['goodreads_activity'] = gen.goodreads.fetch()


def initialize_feedparser(generator):
    generator.goodreads = GoodreadsActivity(generator)


def register():
    try:
        signals.article_generator_init.connect(initialize_feedparser)
        signals.article_generator_context.connect(fetch_goodreads_activity)
    except ImportError:
        logger.warning('`goodreads_activity` failed to load dependency `feedparser`.'
                       '`goodreads_activity` plugin not loaded.')

########NEW FILE########
__FILENAME__ = googleplus_comments
# -*- coding: utf-8 -*-
"""
Google Comments Plugin For Pelican
==================================

Adds Google comments to Pelican
"""

from pelican import signals

googleplus_comments_snippet = """
    <script src="https://apis.google.com/js/plusone.js"></script>
    <script>
        $(document).ready(function () {
            gapi.comments.render('comments', {
                href: window.location,
                width: '600',
                first_party_property: 'BLOGGER',
                view_type: 'FILTERED_POSTMOD'
            });
    });
    </script>
"""

def add_googleplus_comments(generator, metadata):
    metadata["googleplus_comments"] = googleplus_comments_snippet

def register():
    signals.article_generator_context.connect(add_googleplus_comments)

########NEW FILE########
__FILENAME__ = gravatar
"""
Gravatar plugin for Pelican
===========================

This plugin assigns the ``author_gravatar`` variable to the Gravatar URL and
makes the variable available within the article's context.
"""

import hashlib
import six

from pelican import signals


def add_gravatar(generator, metadata):

    #first check email
    if 'email' not in metadata.keys()\
        and 'AUTHOR_EMAIL' in generator.settings.keys():
            metadata['email'] = generator.settings['AUTHOR_EMAIL']

    #then add gravatar url
    if 'email' in metadata.keys():
        email_bytes = six.b(metadata['email']).lower()
        gravatar_url = "http://www.gravatar.com/avatar/" + \
                        hashlib.md5(email_bytes).hexdigest()
        metadata["author_gravatar"] = gravatar_url


def register():
    signals.article_generator_context.connect(add_gravatar)

########NEW FILE########
__FILENAME__ = gzip_cache
'''
Copyright (c) 2012 Matt Layman

Gzip cache
----------

A plugin to create .gz cache files for optimization.
'''

import gzip
import logging
import os

from pelican import signals

logger = logging.getLogger(__name__)

# A list of file types to exclude from possible compression
EXCLUDE_TYPES = [
    # Compressed types
    '.bz2',
    '.gz',

    # Audio types
    '.aac',
    '.flac',
    '.mp3',
    '.wma',

    # Image types
    '.gif',
    '.jpg',
    '.jpeg',
    '.png',

    # Video types
    '.avi',
    '.mov',
    '.mp4',
]

def create_gzip_cache(pelican):
    '''Create a gzip cache file for every file that a webserver would
    reasonably want to cache (e.g., text type files).

    :param pelican: The Pelican instance
    '''
    for dirpath, _, filenames in os.walk(pelican.settings['OUTPUT_PATH']):
        for name in filenames:
            if should_compress(name):
                filepath = os.path.join(dirpath, name)
                create_gzip_file(filepath)

def should_compress(filename):
    '''Check if the filename is a type of file that should be compressed.

    :param filename: A file name to check against
    '''
    for extension in EXCLUDE_TYPES:
        if filename.endswith(extension):
            return False

    return True

def create_gzip_file(filepath):
    '''Create a gzipped file in the same directory with a filepath.gz name.

    :param filepath: A file to compress
    '''
    compressed_path = filepath + '.gz'

    with open(filepath, 'rb') as uncompressed:
        try:
            logger.debug('Compressing: %s' % filepath)
            compressed = gzip.open(compressed_path, 'wb')
            compressed.writelines(uncompressed)
        except Exception as ex:
            logger.critical('Gzip compression failed: %s' % ex)
        finally:
            compressed.close()

def register():
    signals.finalized.connect(create_gzip_cache)


########NEW FILE########
__FILENAME__ = test_gzip_cache
# -*- coding: utf-8 -*-
'''Core plugins unit tests'''

import os
import tempfile
import unittest

from contextlib import contextmanager
from tempfile import mkdtemp
from shutil import rmtree

import gzip_cache

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


class TestGzipCache(unittest.TestCase):

    def test_should_compress(self):
        # Some filetypes should compress and others shouldn't.
        self.assertTrue(gzip_cache.should_compress('foo.html'))
        self.assertTrue(gzip_cache.should_compress('bar.css'))
        self.assertTrue(gzip_cache.should_compress('baz.js'))
        self.assertTrue(gzip_cache.should_compress('foo.txt'))

        self.assertFalse(gzip_cache.should_compress('foo.gz'))
        self.assertFalse(gzip_cache.should_compress('bar.png'))
        self.assertFalse(gzip_cache.should_compress('baz.mp3'))
        self.assertFalse(gzip_cache.should_compress('foo.mov'))

    def test_creates_gzip_file(self):
        # A file matching the input filename with a .gz extension is created.

        # The plugin walks over the output content after the finalized signal
        # so it is safe to assume that the file exists (otherwise walk would
        # not report it). Therefore, create a dummy file to use.
        with temporary_folder() as tempdir:
            _, a_html_filename = tempfile.mkstemp(suffix='.html', dir=tempdir)
            gzip_cache.create_gzip_file(a_html_filename)
            self.assertTrue(os.path.exists(a_html_filename + '.gz'))


########NEW FILE########
__FILENAME__ = html_entity
"""
HTML Entities for reStructured Text
===================================

Allows user to use HTML entities (&copy;, &#149;, etc.) in RST documents.

Usage:
:html_entity:`copy`
:html_entity:`149`
:html_entity:`#149`
"""
from __future__ import unicode_literals
from docutils import nodes, utils
from docutils.parsers.rst import roles
from pelican.readers import PelicanHTMLTranslator
import six


class html_entity(nodes.Inline, nodes.Node):
    # Subclassing Node directly since TextElement automatically appends the escaped element
    def __init__(self, rawsource, text):
        self.rawsource = rawsource
        self.text = text
        self.children = []
        self.attributes = {}

    def astext(self):
        return self.text


def entity_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    entity_code = text
    try:
        entity_code = "#{}".format(six.u(int(entity_code)))
    except ValueError:
        pass
    entity_code = "&{};".format(entity_code)
    return [html_entity(text, entity_code)], []


def register():
    roles.register_local_role('html_entity', entity_role)

PelicanHTMLTranslator.visit_html_entity = lambda self, node: self.body.append(node.astext())
PelicanHTMLTranslator.depart_html_entity = lambda self, node: None

########NEW FILE########
__FILENAME__ = html_rst_directive
# -*- coding: utf-8 -*-
"""
HTML tags for reStructuredText
==============================

This plugin allows you to use HTML tags from within reST documents. 

"""

from __future__ import unicode_literals
from docutils import nodes
from docutils.parsers.rst import directives, Directive


class RawHtml(Directive):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True

    def run(self):
        html = ' '.join(self.content)
        node = nodes.raw('', html, format='html')
        return [node]



def register():
    directives.register_directive('html', RawHtml)


########NEW FILE########
__FILENAME__ = i18n_subsites
"""i18n_subsites plugin creates i18n-ized subsites of the default site"""



import os
import six
import logging
from itertools import chain
from collections import defaultdict, OrderedDict

import gettext

from pelican import signals
from pelican.contents import Page, Article
from pelican.settings import configure_settings

from ._regenerate_context_helpers import regenerate_context_articles



# Global vars
_main_site_generated = False
_main_site_lang = "en"
_main_siteurl = ''
_lang_siteurls = None
logger = logging.getLogger(__name__)



def disable_lang_vars(pelican_obj):
    """Set lang specific url and save_as vars to the non-lang defaults

    e.g. ARTICLE_LANG_URL = ARTICLE_URL
    They would conflict with this plugin otherwise
    """
    global _main_site_lang, _main_siteurl, _lang_siteurls
    s = pelican_obj.settings
    for content in ['ARTICLE', 'PAGE']:
        for meta in ['_URL', '_SAVE_AS']:
            s[content + '_LANG' + meta] = s[content + meta]
    if not _main_site_generated:
        _main_site_lang = s['DEFAULT_LANG']
        _main_siteurl = s['SITEURL']
        _lang_siteurls = [(lang, _main_siteurl + '/' + lang) for lang in s.get('I18N_SUBSITES', {}).keys()]
        # To be able to use url for main site root when SITEURL == '' (e.g. when developing)
        _lang_siteurls = [(_main_site_lang, ('/' if _main_siteurl == '' else _main_siteurl))] + _lang_siteurls
        _lang_siteurls = OrderedDict(_lang_siteurls)
        

    
def create_lang_subsites(pelican_obj):
    """For each language create a subsite using the lang-specific config

    for each generated lang append language subpath to SITEURL and OUTPUT_PATH
    and set DEFAULT_LANG to the language code to change perception of what is translated
    and set DELETE_OUTPUT_DIRECTORY to False to prevent deleting output from previous runs
    Then generate the subsite using a PELICAN_CLASS instance and its run method.
    """
    global _main_site_generated
    if _main_site_generated:      # make sure this is only called once
        return
    else:
        _main_site_generated = True

    orig_settings = pelican_obj.settings
    for lang, overrides in orig_settings.get('I18N_SUBSITES', {}).items():
        settings = orig_settings.copy()
        settings.update(overrides)
        settings['SITEURL'] = _lang_siteurls[lang]
        settings['OUTPUT_PATH'] = os.path.join(orig_settings['OUTPUT_PATH'], lang, '')
        settings['DEFAULT_LANG'] = lang   # to change what is perceived as translations
        settings['DELETE_OUTPUT_DIRECTORY'] = False  # prevent deletion of previous runs
        settings = configure_settings(settings)      # to set LOCALE, etc.

        cls = settings['PELICAN_CLASS']
        if isinstance(cls, six.string_types):
            module, cls_name = cls.rsplit('.', 1)
            module = __import__(module)
            cls = getattr(module, cls_name)

        pelican_obj = cls(settings)
        logger.debug("Generating i18n subsite for lang '{}' using class '{}'".format(lang, str(cls)))
        pelican_obj.run()
    _main_site_generated = False          # for autoreload mode



def move_translations_links(content_object):
    """This function points translations links to the sub-sites

    by prepending their location with the language code
    or directs an original DEFAULT_LANG translation back to top level site
    """
    for translation in content_object.translations:
        if translation.lang == _main_site_lang:
        # cannot prepend, must take to top level
            lang_prepend = '../'
        else:
            lang_prepend = translation.lang + '/'
        translation.override_url =  lang_prepend + translation.url



def update_generator_contents(generator, *args):
    """Update the contents lists of a generator

    Empty the (hidden_)translation attribute of article and pages generators
    to prevent generating the translations as they will be generated in the lang sub-site
    and point the content translations links to the sub-sites

    Hide content without a translation for current DEFAULT_LANG
    if HIDE_UNTRANSLATED_CONTENT is True
    """
    generator.translations = []
    is_pages_gen = hasattr(generator, 'pages')
    if is_pages_gen:
        generator.hidden_translations = []
        for page in chain(generator.pages, generator.hidden_pages):
            move_translations_links(page)
    else:                                    # is an article generator
        for article in chain(generator.articles, generator.drafts):
            move_translations_links(article)

    if not generator.settings.get('HIDE_UNTRANSLATED_CONTENT', True):
        return
    contents = generator.pages if is_pages_gen else generator.articles
    hidden_contents = generator.hidden_pages if is_pages_gen else generator.drafts
    default_lang = generator.settings['DEFAULT_LANG']
    for content_object in contents[:]:   # loop over copy for removing
        if content_object.lang != default_lang:
            if isinstance(content_object, Article):
                content_object.status = 'draft'
            elif isinstance(content_object, Page):
                content_object.status = 'hidden'
            contents.remove(content_object)
            hidden_contents.append(content_object)
    if not is_pages_gen: # regenerate categories, tags, etc. for articles
        if hasattr(generator, '_generate_context_aggregate'):                  # if implemented
            # Simulate __init__ for fields that need it
            generator.dates = {}
            generator.tags = defaultdict(list)
            generator.categories = defaultdict(list)
            generator.authors = defaultdict(list)
            generator._generate_context_aggregate()
        else:                             # fallback for Pelican 3.3.0
            regenerate_context_articles(generator)



def install_templates_translations(generator):
    """Install gettext translations for current DEFAULT_LANG in the jinja2.Environment

    if the 'jinja2.ext.i18n' jinja2 extension is enabled
    adds some useful variables into the template context
    """
    generator.context['main_siteurl'] = _main_siteurl
    generator.context['main_lang'] = _main_site_lang
    generator.context['lang_siteurls'] = _lang_siteurls
    current_def_lang = generator.settings['DEFAULT_LANG']
    extra_siteurls = _lang_siteurls.copy()
    extra_siteurls.pop(current_def_lang)
    generator.context['extra_siteurls'] = extra_siteurls
    
    if 'jinja2.ext.i18n' not in generator.settings['JINJA_EXTENSIONS']:
        return
    domain = generator.settings.get('I18N_GETTEXT_DOMAIN', 'messages')
    localedir = generator.settings.get('I18N_GETTEXT_LOCALEDIR')
    if localedir is None:
        localedir = os.path.join(generator.theme, 'translations')
    if current_def_lang == generator.settings.get('I18N_TEMPLATES_LANG', _main_site_lang):
        translations = gettext.NullTranslations()
    else:
        languages = [current_def_lang]
        try:
            translations = gettext.translation(domain, localedir, languages)
        except (IOError, OSError):
            logger.error("Cannot find translations for language '{}' in '{}' with domain '{}'. Installing NullTranslations.".format(languages[0], localedir, domain))
            translations = gettext.NullTranslations()
    newstyle = generator.settings.get('I18N_GETTEXT_NEWSTYLE', True)
    generator.env.install_gettext_translations(translations, newstyle)    



def register():
    signals.initialized.connect(disable_lang_vars)
    signals.generator_init.connect(install_templates_translations)
    signals.article_generator_finalized.connect(update_generator_contents)
    signals.page_generator_finalized.connect(update_generator_contents)
    signals.finalized.connect(create_lang_subsites)

########NEW FILE########
__FILENAME__ = _regenerate_context_helpers

import math
import random
from collections import defaultdict
from operator import attrgetter, itemgetter


def regenerate_context_articles(generator):
    """Helper to regenerate context after modifying articles draft state

    essentially just a copy from pelican.generators.ArticlesGenerator.generate_context
    after process_translations up to signal sending

    This has to be kept in sync untill a better solution is found
    This is for Pelican version 3.3.0
    """
    # Simulate __init__ for fields that need it
    generator.dates = {}
    generator.tags = defaultdict(list)
    generator.categories = defaultdict(list)
    generator.authors = defaultdict(list)
    

    # Simulate ArticlesGenerator.generate_context 
    for article in generator.articles:
        # only main articles are listed in categories and tags
        # not translations
        generator.categories[article.category].append(article)
        if hasattr(article, 'tags'):
            for tag in article.tags:
                generator.tags[tag].append(article)
        # ignore blank authors as well as undefined
        if hasattr(article, 'author') and article.author.name != '':
            generator.authors[article.author].append(article)


    # sort the articles by date
    generator.articles.sort(key=attrgetter('date'), reverse=True)
    generator.dates = list(generator.articles)
    generator.dates.sort(key=attrgetter('date'),
            reverse=generator.context['NEWEST_FIRST_ARCHIVES'])

    # create tag cloud
    tag_cloud = defaultdict(int)
    for article in generator.articles:
        for tag in getattr(article, 'tags', []):
            tag_cloud[tag] += 1

    tag_cloud = sorted(tag_cloud.items(), key=itemgetter(1), reverse=True)
    tag_cloud = tag_cloud[:generator.settings.get('TAG_CLOUD_MAX_ITEMS')]

    tags = list(map(itemgetter(1), tag_cloud))
    if tags:
        max_count = max(tags)
    steps = generator.settings.get('TAG_CLOUD_STEPS')

    # calculate word sizes
    generator.tag_cloud = [
        (
            tag,
            int(math.floor(steps - (steps - 1) * math.log(count)
                / (math.log(max_count)or 1)))
        )
        for tag, count in tag_cloud
    ]
    # put words in chaos
    random.shuffle(generator.tag_cloud)

    # and generate the output :)

    # order the categories per name
    generator.categories = list(generator.categories.items())
    generator.categories.sort(
            reverse=generator.settings['REVERSE_CATEGORY_ORDER'])

    generator.authors = list(generator.authors.items())
    generator.authors.sort()

    generator._update_context(('articles', 'dates', 'tags', 'categories',
                          'tag_cloud', 'authors', 'related_posts'))
    

########NEW FILE########
__FILENAME__ = ical
# -*- coding: utf-8 -*-
"""
ical plugin for Pelican
=======================

This plugin looks for and parses an .ics file if it is defined in a given
page's :calendar: metadata. One calendar can be defined per page.

"""

from icalendar import Calendar, Event
from pelican import signals , utils
import pytz
import datetime
import os.path

def init_cal(generator):
    # initialisation of the calendar dictionary
    # you can add one calendar per page
    calDict = {}
    generator.context['events'] = calDict

def add_ical(generator, metadata):
    # check if a calendar is here
    if 'calendar' in metadata.keys():
        summ = []
        path = metadata['calendar']
        if not os.path.isabs(path):
            path = os.path.abspath(metadata['calendar'])
        cal = Calendar.from_ical(open(path,'rb').read())
        for element in cal.walk():
            eventdict = {}
            if element.name == "VEVENT":
                if element.get('summary') != None:
                    eventdict['summary'] = element.get('summary')
                if element.get('description') != None:
                    eventdict['description'] = element.get('description')
                if element.get('url') != None:
                    eventdict['url'] = element.get('url')
                if element.get('dtstart') != None:
                    eventdict['dtstart'] = element.get('dtstart').dt
                if element.get('dtend') != None:
                    eventdict['dtend'] = element.get('dtend').dt
                summ.append(eventdict)
        # the id of the calendar is the slugified name of the page
        calId = utils.slugify(metadata['title'])
        generator.context['events'][calId] = summ


def register():
    signals.page_generator_init.connect(init_cal)
    signals.page_generator_context.connect(add_ical)

########NEW FILE########
__FILENAME__ = interlinks
﻿# -*- coding: utf-8 -*-

"""
Interlinks
=========================

This plugin allows you to include "interwiki" or shortcuts links into the blog, as keyword>rest_of_url

"""

from bs4 import BeautifulSoup
from pelican import signals
import re

interlinks = {}

def getSettings (generator):

	global interlinks

	interlinks = {'this': generator.settings['SITEURL']+"/"}
	if 'INTERLINKS' in generator.settings:
		for key, value in generator.settings['INTERLINKS'].items():
			interlinks[key] = value

def content_object_init(instance):

	if instance._content is not None:
		content = instance._content
		# use Python's built-in parser so no duplicated html & body tags appear, or use tag.unwrap()
		text = BeautifulSoup(content, "html.parser")
		
		if 'a' in content:
			for link in text.find_all(href=re.compile("(.+?)>")):
				url = link.get('href')
				m = re.search(r"(.+?)>", url).groups()
				name = m[0]
				if name in interlinks:
					hi = url.replace(name+">",interlinks[name])
					link['href'] = hi

		instance._content = text.decode()

def register():
	signals.generator_init.connect(getSettings)
	signals.content_object_init.connect(content_object_init)
########NEW FILE########
__FILENAME__ = img
"""
Image Tag
---------
This implements a Liquid-style image tag for Pelican,
based on the octopress image tag [1]_

Syntax
------
{% img [class name(s)] [http[s]:/]/path/to/image [width [height]] [title text | "title text" ["alt text"]] %}

Examples
--------
{% img /images/ninja.png Ninja Attack! %}
{% img left half http://site.com/images/ninja.png Ninja Attack! %}
{% img left half http://site.com/images/ninja.png 150 150 "Ninja Attack!" "Ninja in attack posture" %}

Output
------
<img src="/images/ninja.png">
<img class="left half" src="http://site.com/images/ninja.png" title="Ninja Attack!" alt="Ninja Attack!">
<img class="left half" src="http://site.com/images/ninja.png" width="150" height="150" title="Ninja Attack!" alt="Ninja in attack posture">

[1] https://github.com/imathis/octopress/blob/master/plugins/image_tag.rb
"""
import re
from .mdx_liquid_tags import LiquidTags

SYNTAX = '{% img [class name(s)] [http[s]:/]/path/to/image [width [height]] [title text | "title text" ["alt text"]] %}'

# Regular expression to match the entire syntax
ReImg = re.compile("""(?P<class>\S.*\s+)?(?P<src>(?:https?:\/\/|\/|\S+\/)\S+)(?:\s+(?P<width>\d+))?(?:\s+(?P<height>\d+))?(?P<title>\s+.+)?""")

# Regular expression to split the title and alt text
ReTitleAlt = re.compile("""(?:"|')(?P<title>[^"']+)?(?:"|')\s+(?:"|')(?P<alt>[^"']+)?(?:"|')""")


@LiquidTags.register('img')
def img(preprocessor, tag, markup):
    attrs = None

    # Parse the markup string
    match = ReImg.search(markup)
    if match:
        attrs = dict([(key, val.strip())
                      for (key, val) in match.groupdict().iteritems() if val])
    else:
        raise ValueError('Error processing input. '
                         'Expected syntax: {0}'.format(SYNTAX))

    # Check if alt text is present -- if so, split it from title
    if 'title' in attrs:
        match = ReTitleAlt.search(attrs['title'])
        if match:
            attrs.update(match.groupdict())
        if not attrs.get('alt'):
            attrs['alt'] = attrs['title']

    # Return the formatted text
    return "<img {0}>".format(' '.join('{0}="{1}"'.format(key, val)
                                       for (key, val) in attrs.iteritems()))

#----------------------------------------------------------------------
# This import allows image tag to be a Pelican plugin
from liquid_tags import register


########NEW FILE########
__FILENAME__ = include_code
"""
Include Code Tag
----------------
This implements a Liquid-style video tag for Pelican,
based on the octopress video tag [1]_

Syntax
------
{% include_code path/to/code [lang:python] [Title text] %}

The "path to code" is specified relative to the ``code`` subdirectory of
the content directory  Optionally, this subdirectory can be specified in the
config file:

    CODE_DIR = 'code'

Example
-------
{% include_code myscript.py %}

This will import myscript.py from content/code/myscript.py
and output the contents in a syntax highlighted code block inside a figure,
with a figcaption listing the file name and download link.

The file link will be valid only if the 'code' directory is listed
in the STATIC_PATHS setting, e.g.:

    STATIC_PATHS = ['images', 'code']

[1] https://github.com/imathis/octopress/blob/master/plugins/include_code.rb
"""
import re
import os
from .mdx_liquid_tags import LiquidTags


SYNTAX = "{% include_code /path/to/code.py [lang:python] [lines:X-Y] [:hidefilename:] [title] %}"
FORMAT = re.compile(r"""
^(?:\s+)?                          # Allow whitespace at beginning
(?P<src>\S+)                       # Find the path
(?:\s+)?                           # Whitespace
(?:(?:lang:)(?P<lang>\S+))?        # Optional language
(?:\s+)?                           # Whitespace
(?:(?:lines:)(?P<lines>\d+-\d+))?  # Optional lines
(?:\s+)?                           # Whitespace
(?P<hidefilename>:hidefilename:)?  # Hidefilename flag
(?:\s+)?                           # Whitespace
(?P<title>.+)?$                    # Optional title
""", re.VERBOSE)


@LiquidTags.register('include_code')
def include_code(preprocessor, tag, markup):

    title = None
    lang = None
    src = None

    match = FORMAT.search(markup)
    if match:
        argdict = match.groupdict()
        title = argdict['title'] or ""
        lang = argdict['lang']
        lines = argdict['lines']
        hide_filename = bool(argdict['hidefilename'])
        if lines:
            first_line, last_line = map(int, lines.split("-"))
        src = argdict['src']

    if not src:
        raise ValueError("Error processing input, "
                         "expected syntax: {0}".format(SYNTAX))

    settings = preprocessor.configs.config['settings']
    code_dir = settings.get('CODE_DIR', 'code')
    code_path = os.path.join('content', code_dir, src)

    if not os.path.exists(code_path):
        raise ValueError("File {0} could not be found".format(code_path))

    with open(code_path) as fh:
        if lines:
            code = fh.readlines()[first_line - 1: last_line]
            code[-1] = code[-1].rstrip()
            code = "".join(code)
        else:
            code = fh.read()

    if not title and hide_filename:
        raise ValueError("Either title must be specified or filename must "
                         "be available")

    if not hide_filename:
        title += " %s" % os.path.basename(src)
    if lines:
        title += " [Lines %s]" % lines
    title = title.strip()

    url = '/{0}/{1}'.format(code_dir, src)
    url = re.sub('/+', '/', url)

    open_tag = ("<figure class='code'>\n<figcaption><span>{title}</span> "
                "<a href='{url}'>download</a></figcaption>".format(title=title,
                                                                   url=url))
    close_tag = "</figure>"

    # store HTML tags in the stash.  This prevents them from being
    # modified by markdown.
    open_tag = preprocessor.configs.htmlStash.store(open_tag, safe=True)
    close_tag = preprocessor.configs.htmlStash.store(close_tag, safe=True)

    if lang:
        lang_include = ':::' + lang + '\n    '
    else:
        lang_include = ''

    source = (open_tag
              + '\n\n    '
              + lang_include
              + '\n    '.join(code.split('\n')) + '\n\n'
              + close_tag + '\n')

    return source


#----------------------------------------------------------------------
# This import allows image tag to be a Pelican plugin
from liquid_tags import register

########NEW FILE########
__FILENAME__ = liquid_tags
from pelican import signals
from .mdx_liquid_tags import LiquidTags


def addLiquidTags(gen):
    if not gen.settings.get('MD_EXTENSIONS'):
        from pelican.settings import DEFAULT_CONFIG
        gen.settings['MD_EXTENSIONS'] = DEFAULT_CONFIG['MD_EXTENSIONS']

    if LiquidTags not in gen.settings['MD_EXTENSIONS']:
        configs = dict(settings=gen.settings)
        gen.settings['MD_EXTENSIONS'].append(LiquidTags(configs))


def register():
    signals.initialized.connect(addLiquidTags)

########NEW FILE########
__FILENAME__ = literal
"""
Literal Tag
-----------
This implements a tag that allows explicitly showing commands which would
otherwise be interpreted as a liquid tag.

For example, the line

    {% literal video arg1 arg2 %}

would result in the following line:

    {% video arg1 arg2 %}

This is useful when the resulting line would be interpreted as another
liquid-style tag.
"""
from .mdx_liquid_tags import LiquidTags

@LiquidTags.register('literal')
def literal(preprocessor, tag, markup):
    return '{%% %s %%}' % markup

#----------------------------------------------------------------------
# This import allows image tag to be a Pelican plugin
from liquid_tags import register


########NEW FILE########
__FILENAME__ = mdx_liquid_tags
"""
Markdown Extension for Liquid-style Tags
----------------------------------------
A markdown extension to allow user-defined tags of the form::

    {% tag arg1 arg2 ... argn %}

Where "tag" is associated with some user-defined extension.
These result in a preprocess step within markdown that produces
either markdown or html.
"""
import warnings
import markdown
import itertools
import re
import os
from functools import wraps

# Define some regular expressions
LIQUID_TAG = re.compile(r'\{%.*?%\}')
EXTRACT_TAG = re.compile(r'(?:\s*)(\S+)(?:\s*)')


class _LiquidTagsPreprocessor(markdown.preprocessors.Preprocessor):
    _tags = {}
    def __init__(self, configs):
        self.configs = configs

    def run(self, lines):
        page = '\n'.join(lines)
        liquid_tags = LIQUID_TAG.findall(page)

        for i, markup in enumerate(liquid_tags):
            # remove {% %}
            markup = markup[2:-2]
            tag = EXTRACT_TAG.match(markup).groups()[0]
            markup = EXTRACT_TAG.sub('', markup, 1)
            if tag in self._tags:
                liquid_tags[i] = self._tags[tag](self, tag, markup.strip())
                
        # add an empty string to liquid_tags so that chaining works
        liquid_tags.append('')
 
        # reconstruct string
        page = ''.join(itertools.chain(*zip(LIQUID_TAG.split(page),
                                            liquid_tags)))

        # resplit the lines
        return page.split("\n")


class LiquidTags(markdown.Extension):
    """Wrapper for MDPreprocessor"""
    @classmethod
    def register(cls, tag):
        """Decorator to register a new include tag"""
        def dec(func):
            if tag in _LiquidTagsPreprocessor._tags:
                warnings.warn("Enhanced Markdown: overriding tag '%s'" % tag)
            _LiquidTagsPreprocessor._tags[tag] = func
            return func
        return dec

    def extendMarkdown(self, md, md_globals):
        self.htmlStash = md.htmlStash
        md.registerExtension(self)
        # for the include_code preprocessor, we need to re-run the
        # fenced code block preprocessor after substituting the code.
        # Because the fenced code processor is run before, {% %} tags
        # within equations will not be parsed as an include.
        md.preprocessors.add('mdincludes',
                             _LiquidTagsPreprocessor(self), ">html_block")


def makeExtension(configs=None):
    """Wrapper for a MarkDown extension"""
    return LiquidTags(configs=configs)

########NEW FILE########
__FILENAME__ = notebook
"""
Notebook Tag
------------
This is a liquid-style tag to include a static html rendering of an IPython
notebook in a blog post.

Syntax
------
{% notebook filename.ipynb [ cells[start:end] ]%}

The file should be specified relative to the ``notebooks`` subdirectory of the
content directory.  Optionally, this subdirectory can be specified in the
config file:

    NOTEBOOK_DIR = 'notebooks'

The cells[start:end] statement is optional, and can be used to specify which
block of cells from the notebook to include.

Requirements
------------
- The plugin requires IPython version 1.0 or above.  It no longer supports the
  standalone nbconvert package, which has been deprecated.

Details
-------
Because the notebook relies on some rather extensive custom CSS, the use of
this plugin requires additional CSS to be inserted into the blog theme.
After typing "make html" when using the notebook tag, a file called
``_nb_header.html`` will be produced in the main directory.  The content
of the file should be included in the header of the theme.  An easy way
to accomplish this is to add the following lines within the header template
of the theme you use:

    {% if EXTRA_HEADER %}
      {{ EXTRA_HEADER }}
    {% endif %}

and in your ``pelicanconf.py`` file, include the line:

    EXTRA_HEADER = open('_nb_header.html').read().decode('utf-8')

this will insert the appropriate CSS.  All efforts have been made to ensure
that this CSS will not override formats within the blog theme, but there may
still be some conflicts.
"""
import re
import os
from .mdx_liquid_tags import LiquidTags

from distutils.version import LooseVersion
import IPython
if not LooseVersion(IPython.__version__) >= '1.0':
    raise ValueError("IPython version 1.0+ required for notebook tag")

from IPython import nbconvert

try:
    from IPython.nbconvert.filters.highlight import _pygments_highlight
except ImportError:
    # IPython < 2.0
    from IPython.nbconvert.filters.highlight import _pygment_highlight as _pygments_highlight

from pygments.formatters import HtmlFormatter

from IPython.nbconvert.exporters import HTMLExporter
from IPython.config import Config

from IPython.nbformat import current as nbformat

try:
    from IPython.nbconvert.preprocessors import Preprocessor
except ImportError:
    # IPython < 2.0
    from IPython.nbconvert.transformers import Transformer as Preprocessor

from IPython.utils.traitlets import Integer
from copy import deepcopy

from jinja2 import DictLoader


#----------------------------------------------------------------------
# Some code that will be added to the header:
#  Some of the following javascript/css include is adapted from
#  IPython/nbconvert/templates/fullhtml.tpl, while some are custom tags
#  specifically designed to make the results look good within the
#  pelican-octopress theme.
JS_INCLUDE = r"""
<style type="text/css">
/* Overrides of notebook CSS for static HTML export */
div.entry-content {
  overflow: visible;
  padding: 8px;
}
.input_area {
  padding: 0.2em;
}

a.heading-anchor {
 white-space: normal;
}

.rendered_html
code {
 font-size: .8em;
}

pre.ipynb {
  color: black;
  background: #f7f7f7;
  border: none;
  box-shadow: none;
  margin-bottom: 0;
  padding: 0;
  margin: 0px;
  font-size: 13px;
}

/* remove the prompt div from text cells */
div.text_cell .prompt {
    display: none;
}

/* remove horizontal padding from text cells, */
/* so it aligns with outer body text */
div.text_cell_render {
    padding: 0.5em 0em;
}

img.anim_icon{padding:0; border:0; vertical-align:middle; -webkit-box-shadow:none; -box-shadow:none}

div.collapseheader {
    width=100%;
    background-color:#d3d3d3;
    padding: 2px;
    cursor: pointer;
    font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;
}
</style>

<script src="https://c328740.ssl.cf1.rackcdn.com/mathjax/latest/MathJax.js?config=TeX-AMS_HTML" type="text/javascript"></script>
<script type="text/javascript">
init_mathjax = function() {
    if (window.MathJax) {
        // MathJax loaded
        MathJax.Hub.Config({
            tex2jax: {
                inlineMath: [ ['$','$'], ["\\(","\\)"] ],
                displayMath: [ ['$$','$$'], ["\\[","\\]"] ]
            },
            displayAlign: 'left', // Change this to 'center' to center equations.
            "HTML-CSS": {
                styles: {'.MathJax_Display': {"margin": 0}}
            }
        });
        MathJax.Hub.Queue(["Typeset",MathJax.Hub]);
    }
}
init_mathjax();
</script>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>

<script type="text/javascript">
jQuery(document).ready(function($) {
    $("div.collapseheader").click(function () {
    $header = $(this).children("span").first();
    $codearea = $(this).children(".input_area");
    console.log($(this).children());
    $codearea.slideToggle(500, function () {
        $header.text(function () {
            return $codearea.is(":visible") ? "Collapse Code" : "Expand Code";
        });
    });
});
});
</script>

"""

CSS_WRAPPER = """
<style type="text/css">
{0}
</style>
"""


#----------------------------------------------------------------------
# Create a custom preprocessor
class SliceIndex(Integer):
    """An integer trait that accepts None"""
    default_value = None

    def validate(self, obj, value):
        if value is None:
            return value
        else:
            return super(SliceIndex, self).validate(obj, value)


class SubCell(Preprocessor):
    """A transformer to select a slice of the cells of a notebook"""
    start = SliceIndex(0, config=True,
                       help="first cell of notebook to be converted")
    end = SliceIndex(None, config=True,
                     help="last cell of notebook to be converted")

    def preprocess(self, nb, resources):
        nbc = deepcopy(nb)
        for worksheet in nbc.worksheets:
            cells = worksheet.cells[:]
            worksheet.cells = cells[self.start:self.end]
        return nbc, resources

    call = preprocess # IPython < 2.0



#----------------------------------------------------------------------
# Custom highlighter:
#  instead of using class='highlight', use class='highlight-ipynb'
def custom_highlighter(source, language='ipython', metadata=None):
    formatter = HtmlFormatter(cssclass='highlight-ipynb')
    if not language:
        language = 'ipython'
    output = _pygments_highlight(source, formatter, language)
    return output.replace('<pre>', '<pre class="ipynb">')


#----------------------------------------------------------------------
# Below is the pelican plugin code.
#
SYNTAX = "{% notebook /path/to/notebook.ipynb [ cells[start:end] ] %}"
FORMAT = re.compile(r"""^(\s+)?(?P<src>\S+)(\s+)?((cells\[)(?P<start>-?[0-9]*):(?P<end>-?[0-9]*)(\]))?(\s+)?$""")


@LiquidTags.register('notebook')
def notebook(preprocessor, tag, markup):
    match = FORMAT.search(markup)
    if match:
        argdict = match.groupdict()
        src = argdict['src']
        start = argdict['start']
        end = argdict['end']
    else:
        raise ValueError("Error processing input, "
                         "expected syntax: {0}".format(SYNTAX))

    if start:
        start = int(start)
    else:
        start = 0

    if end:
        end = int(end)
    else:
        end = None

    settings = preprocessor.configs.config['settings']
    nb_dir =  settings.get('NOTEBOOK_DIR', 'notebooks')
    nb_path = os.path.join('content', nb_dir, src)

    if not os.path.exists(nb_path):
        raise ValueError("File {0} could not be found".format(nb_path))

    # Create the custom notebook converter
    c = Config({'CSSHTMLHeaderTransformer':
                    {'enabled':True, 'highlight_class':'.highlight-ipynb'},
                'SubCell':
                    {'enabled':True, 'start':start, 'end':end}})

    template_file = 'basic'
    if LooseVersion(IPython.__version__) >= '2.0':
        if os.path.exists('pelicanhtml_2.tpl'):
            template_file = 'pelicanhtml_2'
    else:
        if os.path.exists('pelicanhtml_1.tpl'):
            template_file = 'pelicanhtml_1'

    if LooseVersion(IPython.__version__) >= '2.0':
        subcell_kwarg = dict(preprocessors=[SubCell])
    else:
        subcell_kwarg = dict(transformers=[SubCell])
    
    exporter = HTMLExporter(config=c,
                            template_file=template_file,
                            filters={'highlight2html': custom_highlighter},
                            **subcell_kwarg)

    # read and parse the notebook
    with open(nb_path) as f:
        nb_text = f.read()
    nb_json = nbformat.reads_json(nb_text)
    (body, resources) = exporter.from_notebook_node(nb_json)

    # if we haven't already saved the header, save it here.
    if not notebook.header_saved:
        print ("\n ** Writing styles to _nb_header.html: "
               "this should be included in the theme. **\n")

        header = '\n'.join(CSS_WRAPPER.format(css_line)
                           for css_line in resources['inlining']['css'])
        header += JS_INCLUDE

        with open('_nb_header.html', 'w') as f:
            f.write(header)
        notebook.header_saved = True

    # this will stash special characters so that they won't be transformed
    # by subsequent processes.
    body = preprocessor.configs.htmlStash.store(body, safe=True)
    return body

notebook.header_saved = False


#----------------------------------------------------------------------
# This import allows notebook to be a Pelican plugin
from liquid_tags import register

########NEW FILE########
__FILENAME__ = video
"""
Video Tag
---------
This implements a Liquid-style video tag for Pelican,
based on the octopress video tag [1]_

Syntax
------
{% video url/to/video [width height] [url/to/poster] %}

Example
-------
{% video http://site.com/video.mp4 720 480 http://site.com/poster-frame.jpg %}

Output
------
<video width='720' height='480' preload='none' controls poster='http://site.com/poster-frame.jpg'>
   <source src='http://site.com/video.mp4' type='video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\"'/>
</video>

[1] https://github.com/imathis/octopress/blob/master/plugins/video_tag.rb
"""
import os
import re
from .mdx_liquid_tags import LiquidTags

SYNTAX = "{% video url/to/video [url/to/video] [url/to/video] [width height] [url/to/poster] %}"

VIDEO = re.compile(r'(/\S+|https?:\S+)(\s+(/\S+|https?:\S+))?(\s+(/\S+|https?:\S+))?(\s+(\d+)\s(\d+))?(\s+(/\S+|https?:\S+))?')

VID_TYPEDICT = {'.mp4':"type='video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\"'",
                '.ogv':"type='video/ogg; codecs=theora, vorbis'",
                '.webm':"type='video/webm; codecs=vp8, vorbis'"}


@LiquidTags.register('video')
def video(preprocessor, tag, markup):
    videos = []
    width = None
    height = None
    poster = None

    match = VIDEO.search(markup)
    if match:
        groups = match.groups()
        videos = [g for g in groups[0:6:2] if g]
        width = groups[6]
        height = groups[7]
        poster = groups[9]

    if any(videos):
        video_out =  "<video width='{width}' height='{height}' preload='none' controls poster='{poster}'>".format(width=width, height=height, poster=poster)
        for vid in videos:
            base, ext = os.path.splitext(vid)
            if ext not in VID_TYPEDICT:
                raise ValueError("Unrecognized video extension: "
                                 "{0}".format(ext))
            video_out += ("<source src='{0}' "
                          "{1}>".format(vid, VID_TYPEDICT[ext]))
        video_out += "</video>"
    else:
        raise ValueError("Error processing input, "
                         "expected syntax: {0}".format(SYNTAX))

    return video_out


#----------------------------------------------------------------------
# This import allows image tag to be a Pelican plugin
from liquid_tags import register

########NEW FILE########
__FILENAME__ = vimeo
"""
Vimeo Tag
---------
This implements a Liquid-style vimeo tag for Pelican,
based on the youtube tag which is in turn based on
the jekyll / octopress youtube tag [1]_

Syntax
------
{% vimeo id [width height] %}

Example
-------
{% vimeo 10739054 640 480 %}

Output
------
<div style="width:640px; height:480px;"><iframe src="//player.vimeo.com/video/10739054?title=0&amp;byline=0&amp;portrait=0" width="640" height="480" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe></div>

[1] https://gist.github.com/jamieowen/2063748
"""
import re
from .mdx_liquid_tags import LiquidTags

SYNTAX = "{% vimeo id [width height] %}"

VIMEO = re.compile(r'(\w+)(\s+(\d+)\s(\d+))?')


@LiquidTags.register('vimeo')
def vimeo(preprocessor, tag, markup):
    width = 640
    height = 390
    vimeo_id = None

    match = VIMEO.search(markup)
    if match:
        groups = match.groups()
        vimeo_id = groups[0]
        width = groups[2] or width
        height = groups[3] or height

    if vimeo_id:
        vimeo_out = '<div style="width:{width}px; height:{height}px;"><iframe src="//player.vimeo.com/video/{vimeo_id}?title=0&amp;byline=0&amp;portrait=0" width="{width}" height="{height}" frameborder="0" webkitAllowFullScreen mozallowfullscreen allowFullScreen></iframe></div>'.format(width=width, height=height, vimeo_id=vimeo_id)
    else:
        raise ValueError("Error processing input, "
                         "expected syntax: {0}".format(SYNTAX))

    return vimeo_out


#----------------------------------------------------------------------
# This import allows vimeo tag to be a Pelican plugin
from liquid_tags import register

########NEW FILE########
__FILENAME__ = youtube
"""
Youtube Tag
---------
This implements a Liquid-style youtube tag for Pelican,
based on the jekyll / octopress youtube tag [1]_

Syntax
------
{% youtube id [width height] %}

Example
-------
{% youtube dQw4w9WgXcQ 640 480 %}

Output
------
<iframe width="640" height="480" src="http://www.youtube.com/embed/dQw4w9WgXcQ" frameborder="0" webkitAllowFullScreen mozallowfullscreen allowFullScreen></iframe>

[1] https://gist.github.com/jamieowen/2063748
"""
import os
import re
from .mdx_liquid_tags import LiquidTags

SYNTAX = "{% youtube id [width height] %}"

YOUTUBE = re.compile(r'(\w+)(\s+(\d+)\s(\d+))?')

@LiquidTags.register('youtube')
def youtube(preprocessor, tag, markup):
    width = 640
    height = 390
    youtube_id = None

    match = YOUTUBE.search(markup)
    if match:
        groups = match.groups()
        youtube_id = groups[0]
        width = groups[2] or width
        height = groups[3] or height

    if youtube_id:
        youtube_out = "<iframe width='{width}' height='{height}' src='http://www.youtube.com/embed/{youtube_id}' frameborder='0' webkitAllowFullScreen mozallowfullscreen allowFullScreen></iframe>".format(width=width, height=height, youtube_id=youtube_id)
    else:
        raise ValueError("Error processing input, "
                         "expected syntax: {0}".format(SYNTAX))

    return youtube_out


#----------------------------------------------------------------------
# This import allows image tag to be a Pelican plugin
from liquid_tags import register

########NEW FILE########
__FILENAME__ = multi_part
# -*- coding: utf-8 -*-
"""
Copyright (c) FELD Boris <lothiraldan@gmail.com>

Multiple part support
=====================

Create a navigation menu for multi-part related_posts
"""

from collections import defaultdict

from pelican import signals


def aggregate_multi_part(generator):
        multi_part = defaultdict(list)

        for article in generator.articles:
            if 'parts' in article.metadata:
                multi_part[article.metadata['parts']].append(article)

        for part_id in multi_part:
            parts = multi_part[part_id]

            # Sort by date
            parts.sort(key=lambda x: x.metadata['date'])

            for article in parts:
                article.metadata['parts_articles'] = parts


def register():
    signals.article_generator_finalized.connect(aggregate_multi_part)

########NEW FILE########
__FILENAME__ = neighbors
# -*- coding: utf-8 -*-
"""
Neighbor Articles Plugin for Pelican
====================================

This plugin adds ``next_article`` (newer) and ``prev_article`` (older) 
variables to the article's context
"""
from pelican import signals

def iter3(seq):
    it = iter(seq)
    nxt = None
    cur = next(it)
    for prv in it:
        yield nxt, cur, prv
        nxt, cur = cur, prv
    yield nxt, cur, None

def get_translation(article, prefered_language):
    if not article:
        return None
    for translation in article.translations:
        if translation.lang == prefered_language:
            return translation
    return article

def set_neighbors(articles, next_name, prev_name):
    for nxt, cur, prv in iter3(articles):
        exec("cur.{} = nxt".format(next_name))
        exec("cur.{} = prv".format(prev_name))

        for translation in cur.translations:
            exec(
            "translation.{} = get_translation(nxt, translation.lang)".format(
                next_name))
            exec(
            "translation.{} = get_translation(prv, translation.lang)".format(
                prev_name))
      
def neighbors(generator):
    set_neighbors(generator.articles, 'next_article', 'prev_article')
    
    for category, articles in generator.categories:
        articles.sort(key=(lambda x: x.date), reverse=(True))
        set_neighbors(
            articles, 'next_article_in_category', 'prev_article_in_category')

    if hasattr(generator, 'subcategories'):
        for subcategory, articles in generator.subcategories:
            articles.sort(key=(lambda x: x.date), reverse=(True))
            index = subcategory.name.count('/')
            next_name = 'next_article_in_subcategory{}'.format(index)
            prev_name = 'prev_article_in_subcategory{}'.format(index)
            set_neighbors(articles, next_name, prev_name)

def register():
    signals.article_generator_finalized.connect(neighbors)

########NEW FILE########
__FILENAME__ = optimize_images
# -*- coding: utf-8 -*-

"""
Optimized images (jpg and png)
Assumes that jpegtran and optipng are isntalled on path.
http://jpegclub.org/jpegtran/
http://optipng.sourceforge.net/
Copyright (c) 2012 Irfan Ahmad (http://i.com.pk)
"""

import logging
import os
from subprocess import call

from pelican import signals

logger = logging.getLogger(__name__)

# Display command output on DEBUG and TRACE
SHOW_OUTPUT = logger.getEffectiveLevel() <= logging.DEBUG

# A list of file types with their respective commands
COMMANDS = {
    # '.ext': ('command {flags} {filename', 'silent_flag', 'verbose_flag')
    '.jpg': ('jpegtran {flags} -copy none -optimize -outfile "{filename}" "{filename}"', '', '-v'),
    '.png': ('optipng {flags} "{filename}"', '--quiet', ''),
}


def optimize_images(pelican):
    """
    Optimized jpg and png images

    :param pelican: The Pelican instance
    """
    for dirpath, _, filenames in os.walk(pelican.settings['OUTPUT_PATH']):
        for name in filenames:
            if os.path.splitext(name)[1] in COMMANDS.keys():
                optimize(dirpath, name)

def optimize(dirpath, filename):
    """
    Check if the name is a type of file that should be optimized.
    And optimizes it if required.

    :param dirpath: Path of the file to be optimzed
    :param name: A file name to be optimized
    """
    filepath = os.path.join(dirpath, filename)
    logger.info('optimizing %s', filepath)

    ext = os.path.splitext(filename)[1]
    command, silent, verbose = COMMANDS[ext]
    flags = verbose if SHOW_OUTPUT else silent
    command = command.format(filename=filepath, flags=flags)
    call(command, shell=True)


def register():
    signals.finalized.connect(optimize_images)

########NEW FILE########
__FILENAME__ = pdf
# -*- coding: utf-8 -*-
'''
PDF Generator
-------

The pdf plugin generates PDF files from RST sources.
'''

from __future__ import unicode_literals, print_function

from pelican import signals
from pelican.generators import Generator
from rst2pdf.createpdf import RstToPdf

import os
import logging

logger = logging.getLogger(__name__)


class PdfGenerator(Generator):
    """Generate PDFs on the output dir, for all articles and pages coming from
    rst"""
    def __init__(self, *args, **kwargs):
        super(PdfGenerator, self).__init__(*args, **kwargs)
        
        pdf_style_path = os.path.join(self.settings['PDF_STYLE_PATH'])
        pdf_style = self.settings['PDF_STYLE']
        self.pdfcreator = RstToPdf(breakside=0,
                                   stylesheets=[pdf_style],
                                   style_path=[pdf_style_path])

    def _create_pdf(self, obj, output_path):
        if obj.source_path.endswith('.rst'):
            filename = obj.slug + ".pdf"
            output_pdf = os.path.join(output_path, filename)
            # print('Generating pdf for', obj.source_path, 'in', output_pdf)
            with open(obj.source_path) as f:
                self.pdfcreator.createPdf(text=f.read(), output=output_pdf)
            logger.info(' [ok] writing %s' % output_pdf)

    def generate_context(self):
        pass

    def generate_output(self, writer=None):
        # we don't use the writer passed as argument here
        # since we write our own files
        logger.info(' Generating PDF files...')
        pdf_path = os.path.join(self.output_path, 'pdf')
        if not os.path.exists(pdf_path):
            try:
                os.mkdir(pdf_path)
            except OSError:
                logger.error("Couldn't create the pdf output folder in " +
                             pdf_path)

        for article in self.context['articles']:
            self._create_pdf(article, pdf_path)

        for page in self.context['pages']:
            self._create_pdf(page, pdf_path)


def get_generators(generators):
    return PdfGenerator


def register():
    signals.get_generators.connect(get_generators)

########NEW FILE########
__FILENAME__ = test_pdf
import unittest
import os
import locale
import logging
import pdf

from tempfile import mkdtemp
from pelican import Pelican
from pelican.settings import read_settings
from shutil import rmtree

CUR_DIR = os.path.dirname(__file__)

class TestPdfGeneration(unittest.TestCase):
    def setUp(self, override=None):
        import pdf
        self.temp_path = mkdtemp(prefix='pelicantests.')
        settings = {
            'PATH': os.path.join(os.path.dirname(CUR_DIR), '..', 'test_data', 'content'),
            'OUTPUT_PATH': self.temp_path,
            'PLUGINS': [pdf],
            'LOCALE': locale.normalize('en_US'),
        }
        if override:
            settings.update(override)

        self.settings = read_settings(override=settings)
        pelican = Pelican(settings=self.settings)

        try:
            pelican.run()
        except ValueError:
            logging.warn('Relative links in the form of |filename|images/test.png are not yet handled by the pdf generator')
            pass


    def tearDown(self):
        rmtree(self.temp_path)

    def test_existence(self):
        assert os.path.exists(os.path.join(self.temp_path, 'pdf', 'this-is-a-super-article.pdf'))

########NEW FILE########
__FILENAME__ = avatars
# -*- coding: utf-8 -*-
"""

"""

from __future__ import unicode_literals

import logging
import os

import hashlib


logger = logging.getLogger(__name__)
_log = "pelican_comment_system: avatars: "
try:
	from . identicon import identicon
	_identiconImported = True
except ImportError as e:
	logger.warning(_log + "identicon deactivated: " + str(e))
	_identiconImported = False

# Global Variables
_identicon_save_path = None
_identicon_output_path = None
_identicon_data = None
_identicon_size = None
_initialized = False
_authors = None
_missingAvatars = []

def _ready():
	if not _initialized:
		logger.warning(_log + "Module not initialized. use init")
	if not _identicon_data:
		logger.debug(_log + "No identicon data set")
	return _identiconImported and _initialized and _identicon_data


def init(pelican_output_path, identicon_output_path, identicon_data, identicon_size, authors):
	global _identicon_save_path
	global _identicon_output_path
	global _identicon_data
	global _identicon_size
	global _initialized
	global _authors
	_identicon_save_path = os.path.join(pelican_output_path, identicon_output_path)
	_identicon_output_path = identicon_output_path
	_identicon_data = identicon_data
	_identicon_size = identicon_size
	_authors = authors
	_initialized = True

def _createIdenticonOutputFolder():
	if not _ready():
		return

	if not os.path.exists(_identicon_save_path):
		os.makedirs(_identicon_save_path)


def getAvatarPath(comment_id, metadata):
	if not _ready():
		return ''

	md5 = hashlib.md5()
	author = tuple()
	for data in _identicon_data:
		if data in metadata:
			string = str(metadata[data])
			md5.update(string.encode('utf-8'))
			author += tuple([string])
		else:
			logger.warning(_log + data + " is missing in comment: " + comment_id)

	if author in _authors:
		return _authors[author]

	global _missingAvatars

	code = md5.hexdigest()

	if not code in _missingAvatars:
		_missingAvatars.append(code)

	return os.path.join(_identicon_output_path, '%s.png' % code)

def generateAndSaveMissingAvatars():
	_createIdenticonOutputFolder()
	for code in _missingAvatars:
		avatar_path = '%s.png' % code
		avatar = identicon.render_identicon(int(code, 16), _identicon_size)
		avatar_save_path = os.path.join(_identicon_save_path, avatar_path)
		avatar.save(avatar_save_path, 'PNG')

########NEW FILE########
__FILENAME__ = comment
# -*- coding: utf-8 -*-
"""

"""
from __future__ import unicode_literals
from pelican import contents
from pelican.contents import Content

class Comment(Content):
	mandatory_properties = ('author', 'date')
	default_template = 'None'

	def __init__(self, id, avatar, content, metadata, settings, source_path, context):
		super(Comment,self).__init__( content, metadata, settings, source_path, context )
		self.id = id
		self.replies = []
		self.avatar = avatar
		self.title = "Posted by:  " + str(metadata['author'])

	def addReply(self, comment):
		self.replies.append(comment)

	def getReply(self, id):
		for reply in self.replies:
			if reply.id == id:
				return reply
			else:
				deepReply = reply.getReply(id)
				if deepReply != None:
					return deepReply
		return None

	def __lt__(self, other):
		return self.metadata['date'] < other.metadata['date']

	def sortReplies(self):
		for r in self.replies:
			r.sortReplies()
		self.replies = sorted(self.replies)

	def countReplies(self):
		amount = 0
		for r in self.replies:
			amount += r.countReplies()
		return amount + len(self.replies)

########NEW FILE########
__FILENAME__ = identicon
#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
identicon.py
identicon python implementation.
by Shin Adachi <shn@glucose.jp>

= usage =

== commandline ==
>>> python identicon.py [code]

== python ==
>>> import identicon
>>> identicon.render_identicon(code, size)

Return a PIL Image class instance which have generated identicon image.
```size``` specifies `patch size`. Generated image size is 3 * ```size```.
"""
# g
# PIL Modules
from PIL import Image, ImageDraw, ImagePath, ImageColor


__all__ = ['render_identicon', 'IdenticonRendererBase']


class Matrix2D(list):
    """Matrix for Patch rotation"""
    def __init__(self, initial=[0.] * 9):
        assert isinstance(initial, list) and len(initial) == 9
        list.__init__(self, initial)

    def clear(self):
        for i in xrange(9):
            self[i] = 0.

    def set_identity(self):
        self.clear()
        for i in xrange(3):
            self[i] = 1.

    def __str__(self):
        return '[%s]' % ', '.join('%3.2f' % v for v in self)

    def __mul__(self, other):
        r = []
        if isinstance(other, Matrix2D):
            for y in range(3):
                for x in range(3):
                    v = 0.0
                    for i in range(3):
                        v += (self[i * 3 + x] * other[y * 3 + i])
                    r.append(v)
        else:
            raise NotImplementedError
        return Matrix2D(r)

    def for_PIL(self):
        return self[0:6]

    @classmethod
    def translate(kls, x, y):
        return kls([1.0, 0.0, float(x),
                    0.0, 1.0, float(y),
                    0.0, 0.0, 1.0])

    @classmethod
    def scale(kls, x, y):
        return kls([float(x), 0.0, 0.0,
                    0.0, float(y), 0.0,
                    0.0, 0.0, 1.0])

    """
    # need `import math`
    @classmethod
    def rotate(kls, theta, pivot=None):
        c = math.cos(theta)
        s = math.sin(theta)

        matR = kls([c, -s, 0., s, c, 0., 0., 0., 1.])
        if not pivot:
            return matR
        return kls.translate(-pivot[0], -pivot[1]) * matR *
            kls.translate(*pivot)
    """
    
    @classmethod
    def rotateSquare(kls, theta, pivot=None):
        theta = theta % 4
        c = [1., 0., -1., 0.][theta]
        s = [0., 1., 0., -1.][theta]

        matR = kls([c, -s, 0., s, c, 0., 0., 0., 1.])
        if not pivot:
            return matR
        return kls.translate(-pivot[0], -pivot[1]) * matR * \
            kls.translate(*pivot)


class IdenticonRendererBase(object):
    PATH_SET = []
    
    def __init__(self, code):
        """
        @param code code for icon
        """
        if not isinstance(code, int):
            code = int(code)
        self.code = code
    
    def render(self, size):
        """
        render identicon to PIL.Image
        
        @param size identicon patchsize. (image size is 3 * [size])
        @return PIL.Image
        """
        
        # decode the code
        middle, corner, side, foreColor, backColor = self.decode(self.code)
        size = int(size)
        # make image        
        image = Image.new("RGB", (size * 3, size * 3))
        draw = ImageDraw.Draw(image)
        
        # fill background
        draw.rectangle((0, 0, image.size[0], image.size[1]), fill=0)
        
        kwds = {
            'draw': draw,
            'size': size,
            'foreColor': foreColor,
            'backColor': backColor}
        # middle patch
        self.drawPatch((1, 1), middle[2], middle[1], middle[0], **kwds)

        # side patch
        kwds['type'] = side[0]
        for i in range(4):
            pos = [(1, 0), (2, 1), (1, 2), (0, 1)][i]
            self.drawPatch(pos, side[2] + 1 + i, side[1], **kwds)
        
        # corner patch
        kwds['type'] = corner[0]
        for i in range(4):
            pos = [(0, 0), (2, 0), (2, 2), (0, 2)][i]
            self.drawPatch(pos, corner[2] + 1 + i, corner[1], **kwds)
        
        return image
                
    def drawPatch(self, pos, turn, invert, type, draw, size, foreColor,
            backColor):
        """
        @param size patch size
        """
        path = self.PATH_SET[type]
        if not path:
            # blank patch
            invert = not invert
            path = [(0., 0.), (1., 0.), (1., 1.), (0., 1.), (0., 0.)]
        patch = ImagePath.Path(path)
        if invert:
            foreColor, backColor = backColor, foreColor
        
        mat = Matrix2D.rotateSquare(turn, pivot=(0.5, 0.5)) *\
              Matrix2D.translate(*pos) *\
              Matrix2D.scale(size, size)
        
        patch.transform(mat.for_PIL())
        draw.rectangle((pos[0] * size, pos[1] * size, (pos[0] + 1) * size,
            (pos[1] + 1) * size), fill=backColor)
        draw.polygon(patch, fill=foreColor, outline=foreColor)

    ### virtual functions
    def decode(self, code):
        raise NotImplementedError


class DonRenderer(IdenticonRendererBase):
    """
    Don Park's implementation of identicon
    see : http://www.docuverse.com/blog/donpark/2007/01/19/identicon-updated-and-source-released
    """
    
    PATH_SET = [
        [(0, 0), (4, 0), (4, 4), (0, 4)],   # 0
        [(0, 0), (4, 0), (0, 4)],
        [(2, 0), (4, 4), (0, 4)],
        [(0, 0), (2, 0), (2, 4), (0, 4)],
        [(2, 0), (4, 2), (2, 4), (0, 2)],   # 4
        [(0, 0), (4, 2), (4, 4), (2, 4)],
        [(2, 0), (4, 4), (2, 4), (3, 2), (1, 2), (2, 4), (0, 4)],
        [(0, 0), (4, 2), (2, 4)],
        [(1, 1), (3, 1), (3, 3), (1, 3)],   # 8   
        [(2, 0), (4, 0), (0, 4), (0, 2), (2, 2)],
        [(0, 0), (2, 0), (2, 2), (0, 2)],
        [(0, 2), (4, 2), (2, 4)],
        [(2, 2), (4, 4), (0, 4)],
        [(2, 0), (2, 2), (0, 2)],
        [(0, 0), (2, 0), (0, 2)],
        []]                                 # 15
    MIDDLE_PATCH_SET = [0, 4, 8, 15]
    
    # modify path set
    for idx in range(len(PATH_SET)):
        if PATH_SET[idx]:
            p = map(lambda vec: (vec[0] / 4.0, vec[1] / 4.0), PATH_SET[idx])
            p = list(p)
            PATH_SET[idx] = p + p[:1]
    
    def decode(self, code):
        # decode the code        
        middleType  = self.MIDDLE_PATCH_SET[code & 0x03]
        middleInvert= (code >> 2) & 0x01
        cornerType  = (code >> 3) & 0x0F
        cornerInvert= (code >> 7) & 0x01
        cornerTurn  = (code >> 8) & 0x03
        sideType    = (code >> 10) & 0x0F
        sideInvert  = (code >> 14) & 0x01
        sideTurn    = (code >> 15) & 0x03
        blue        = (code >> 16) & 0x1F
        green       = (code >> 21) & 0x1F
        red         = (code >> 27) & 0x1F
        
        foreColor = (red << 3, green << 3, blue << 3)
        
        return (middleType, middleInvert, 0),\
               (cornerType, cornerInvert, cornerTurn),\
               (sideType, sideInvert, sideTurn),\
               foreColor, ImageColor.getrgb('white')


def render_identicon(code, size, renderer=None):
    if not renderer:
        renderer = DonRenderer
    return renderer(code).render(size)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print('usage: python identicon.py [CODE]....')
        raise SystemExit
    
    for code in sys.argv[1:]:
        if code.startswith('0x') or code.startswith('0X'):
            code = int(code[2:], 16)
        elif code.startswith('0'):
            code = int(code[1:], 8)
        else:
            code = int(code)
        
        icon = render_identicon(code, 24)
        icon.save('%08x.png' % code, 'PNG')

########NEW FILE########
__FILENAME__ = pelican_comment_system
# -*- coding: utf-8 -*-
"""
Pelican Comment System
======================

A Pelican plugin, which allows you to add comments to your articles.

Author: Bernhard Scheirle
"""
from __future__ import unicode_literals
import logging
import os
import copy

logger = logging.getLogger(__name__)

from itertools import chain
from pelican import signals
from pelican.readers import MarkdownReader
from pelican.writers import Writer

from . comment import Comment
from . import avatars


def pelican_initialized(pelican):
	from pelican.settings import DEFAULT_CONFIG
	DEFAULT_CONFIG.setdefault('PELICAN_COMMENT_SYSTEM', False)
	DEFAULT_CONFIG.setdefault('PELICAN_COMMENT_SYSTEM_DIR' 'comments')
	DEFAULT_CONFIG.setdefault('PELICAN_COMMENT_SYSTEM_IDENTICON_OUTPUT_PATH' 'images/identicon')
	DEFAULT_CONFIG.setdefault('PELICAN_COMMENT_SYSTEM_IDENTICON_DATA', ())
	DEFAULT_CONFIG.setdefault('PELICAN_COMMENT_SYSTEM_IDENTICON_SIZE', 72)
	DEFAULT_CONFIG.setdefault('PELICAN_COMMENT_SYSTEM_AUTHORS', {})
	DEFAULT_CONFIG.setdefault('PELICAN_COMMENT_SYSTEM_FEED', os.path.join('feeds', 'comment.%s.atom.xml'))
	DEFAULT_CONFIG.setdefault('COMMENT_URL', '#comment-{path}')
	if pelican:
		pelican.settings.setdefault('PELICAN_COMMENT_SYSTEM', False)
		pelican.settings.setdefault('PELICAN_COMMENT_SYSTEM_DIR', 'comments')
		pelican.settings.setdefault('PELICAN_COMMENT_SYSTEM_IDENTICON_OUTPUT_PATH', 'images/identicon')
		pelican.settings.setdefault('PELICAN_COMMENT_SYSTEM_IDENTICON_DATA', ())
		pelican.settings.setdefault('PELICAN_COMMENT_SYSTEM_IDENTICON_SIZE', 72)
		pelican.settings.setdefault('PELICAN_COMMENT_SYSTEM_AUTHORS', {})
		pelican.settings.setdefault('PELICAN_COMMENT_SYSTEM_FEED', os.path.join('feeds', 'comment.%s.atom.xml'))
		pelican.settings.setdefault('COMMENT_URL', '#comment-{path}')


def initialize(article_generator):
	avatars.init(
		article_generator.settings['OUTPUT_PATH'],
		article_generator.settings['PELICAN_COMMENT_SYSTEM_IDENTICON_OUTPUT_PATH'],
		article_generator.settings['PELICAN_COMMENT_SYSTEM_IDENTICON_DATA'],
		article_generator.settings['PELICAN_COMMENT_SYSTEM_IDENTICON_SIZE']/3,
		article_generator.settings['PELICAN_COMMENT_SYSTEM_AUTHORS'],
		)

def add_static_comments(gen, content):
	if gen.settings['PELICAN_COMMENT_SYSTEM'] != True:
		return

	content.comments_count = 0
	content.comments = []

	#Modify the local context, so we get proper values for the feed
	context = copy.copy(gen.context)
	context['SITEURL'] += "/" + content.url
	context['SITENAME'] = "Comments for: " + content.title
	context['SITESUBTITLE'] = ""
	path = gen.settings['PELICAN_COMMENT_SYSTEM_FEED'] % content.slug
	writer = Writer(gen.output_path, settings=gen.settings)

	folder = os.path.join(gen.settings['PELICAN_COMMENT_SYSTEM_DIR'], content.slug)

	if not os.path.isdir(folder):
		logger.debug("No comments found for: " + content.slug)
		writer.write_feed( [], context, path)
		return

	reader = MarkdownReader(gen.settings)
	comments = []
	replies = []

	for file in os.listdir(folder):
		name, extension = os.path.splitext(file)
		if extension[1:].lower() in reader.file_extensions:
			com_content, meta = reader.read(os.path.join(folder, file))
			
			avatar_path = avatars.getAvatarPath(name, meta)

			com = Comment(file, avatar_path, com_content, meta, gen.settings, file, context)

			if 'replyto' in meta:
				replies.append( com )
			else:
				comments.append( com )

	writer.write_feed( comments + replies, context, path)

	#TODO: Fix this O(n²) loop
	for reply in replies:
		for comment in chain(comments, replies):
			if comment.id == reply.metadata['replyto']:
				comment.addReply(reply)

	count = 0
	for comment in comments:
		comment.sortReplies()
		count += comment.countReplies()

	comments = sorted(comments)

	content.comments_count = len(comments) + count
	content.comments = comments

def writeIdenticonsToDisk(gen, writer):
	avatars.generateAndSaveMissingAvatars()

def register():
	signals.initialized.connect(pelican_initialized)
	signals.article_generator_init.connect(initialize)
	signals.article_generator_write_article.connect(add_static_comments)
	signals.article_writer_finalized.connect(writeIdenticonsToDisk)

########NEW FILE########
__FILENAME__ = post_stats
# -*- coding: utf-8 -*-
"""
Post Statistics
========================

This plugin calculates various statistics about a post and stores them in an article.stats dictionary:

wc: how many words
read_mins: how many minutes to read this article, based on 250 wpm (http://en.wikipedia.org/wiki/Words_per_minute#Reading_and_comprehension)
word_counts: frquency count of all the words in the article; can be used for tag/word clouds/
fi: Flesch-kincaid Index/ Reading Ease
fk: Flesch-kincaid Grade Level

"""

from pelican import signals
from bs4 import BeautifulSoup
import re
from collections import Counter

from .readability import *


def calculate_stats(instance):

    if instance._content is not None:
        stats = {}
        content = instance._content

        # How fast do average people read?
        WPM = 250

        # Use BeautifulSoup to get readable/visible text
        raw_text = BeautifulSoup(content).getText()

        # Process the text to remove entities
        entities = r'\&\#?.+?;'
        raw_text = raw_text.replace('&nbsp;', ' ')
        raw_text = re.sub(entities, '', raw_text)

        # Flesch-kincaid readbility stats counts sentances,
        # so save before removing punctuation
        tmp = raw_text

        # Process the text to remove punctuation
        drop = u'.,?!@#$%^&*()_+-=\|/[]{}`~:;\'\"‘’—…“”'
        raw_text = raw_text.translate(dict((ord(c), u'') for c in drop))

        # Count the words in the text
        words = raw_text.lower().split()
        word_count = Counter(words)

        # Return the stats
        stats['word_counts'] = word_count
        stats['wc'] = sum(word_count.values())

        # Calulate how long it'll take to read, rounding up
        stats['read_mins'] = (stats['wc'] + WPM - 1) // WPM
        if stats['read_mins'] == 0:
            stats['read_mins'] = 1

        # Calculate Flesch-kincaid readbility stats
        readability_stats = stcs, words, sbls = text_stats(tmp, stats['wc'])
        stats['fi'] = "{:.2f}".format(flesch_index(readability_stats))
        stats['fk'] = "{:.2f}".format(flesch_kincaid_level(readability_stats))

        instance.stats = stats


def register():
    signals.content_object_init.connect(calculate_stats)

########NEW FILE########
__FILENAME__ = readability
# -*- coding: utf-8 -*-

# Adadpted from here: http://acdx.net/calculating-the-flesch-kincaid-level-in-python/
# See here for details: http://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_test

from __future__ import division
import re


def mean(seq):
    return sum(seq) / len(seq)


def syllables(word):
    if len(word) <= 3:
        return 1

    word = re.sub(r"(es|ed|(?<!l)e)$", "", word)
    return len(re.findall(r"[aeiouy]+", word))


def normalize(text):
    terminators = ".!?:;"
    term = re.escape(terminators)
    text = re.sub(r"[^%s\sA-Za-z]+" % term, "", text)
    text = re.sub(r"\s*([%s]+\s*)+" % term, ". ", text)
    return re.sub(r"\s+", " ", text)


def text_stats(text, wc):
    text = normalize(text)
    stcs = [s.split(" ") for s in text.split(". ")]
    stcs = filter(lambda s: len(s) >= 2, stcs)

    if wc:
        words = wc
    else:
        words = sum(len(s) for s in stcs)

    sbls = sum(syllables(w) for s in stcs for w in s)

    return len(stcs), words, sbls


def flesch_index(stats):
    stcs, words, sbls = stats
    if stcs == 0 or words == 0:
        return 0
    return 206.835 - 1.015 * (words / stcs) - 84.6 * (sbls / words)


def flesch_kincaid_level(stats):
    stcs, words, sbls = stats
    if stcs == 0 or words == 0:
        return 0
    return 0.39 * (words / stcs) + 11.8 * (sbls / words) - 15.59

########NEW FILE########
__FILENAME__ = random_article
# -*- coding: utf-8 -*-
"""
Random Article Plugin For Pelican
========================

This plugin generates a html file which redirect to a random article
using javascript's window.location. The generated html file is 
saved at SITEURL.
"""

from __future__ import unicode_literals

import os.path

from logging import info
from codecs import open

from pelican import signals

HTML_TOP = """
<!DOCTYPE html>
<head>
    <title>random</title>
    <script type="text/javascript">
        function redirect(){
            var urls = [
"""

HTML_BOTTOM = """
        ""];

        var index = Math.floor(Math.random() * (urls.length-1));
        window.location = urls[index];
    }
</script>
<body onload="redirect()">
</body>
</html>
"""

ARTICLE_URL = """ "{0}/{1}",
"""


class RandomArticleGenerator(object):
    """
        The structure is derived from sitemap plugin
    """

    def __init__(self, context, settings, path, theme, output_path, *null):

        self.output_path = output_path
        self.context = context
        self.siteurl = settings.get('SITEURL')
        self.randomurl = settings.get('RANDOM')

    def write_url(self, article, fd):
        if getattr(article, 'status', 'published') != 'published':
            return

        page_path = os.path.join(self.output_path, article.url)
        if not os.path.exists(page_path):
            return

        fd.write(ARTICLE_URL.format(self.siteurl, article.url))


    def generate_output(self, writer):
        path = os.path.join(self.output_path, self.randomurl)
        articles = self.context['articles']
        info('writing {0}'.format(path))

        if len(articles) == 0:
            return

        with open(path, 'w', encoding='utf-8') as fd:
            fd.write(HTML_TOP)

            for art in articles:
                self.write_url(art, fd)

            fd.write(HTML_BOTTOM)

def get_generators(generators):
    return RandomArticleGenerator


def register():
    signals.get_generators.connect(get_generators)

########NEW FILE########
__FILENAME__ = read_more_link
# -*- coding: utf-8 -*-
"""
Read More Link
===========================

This plugin inserts an inline "read more" or "continue" link into the last html element of the object summary.

For more information, please visit: http://vuongnguyen.com/creating-inline-read-more-link-python-pelican-lxml.html

"""

from pelican import signals, contents
from pelican.utils import truncate_html_words

try:
    from lxml.html import fragment_fromstring, fragments_fromstring, tostring
    from lxml.etree import ParserError
except ImportError:
    raise Exception("Unable to find lxml. To use READ_MORE_LINK, you need lxml")


def insert_into_last_element(html, element):
    """
    function to insert an html element into another html fragment
    example:
        html = '<p>paragraph1</p><p>paragraph2...</p>'
        element = '<a href="/read-more/">read more</a>'
        ---> '<p>paragraph1</p><p>paragraph2...<a href="/read-more/">read more</a></p>'
    """
    try:
        item = fragment_fromstring(element)
    except ParserError, TypeError:
        item = fragment_fromstring('<span></span>')

    try:
        doc = fragments_fromstring(html)
        doc[-1].append(item)

        return ''.join(tostring(e) for e in doc)
    except ParserError, TypeError:
        return ''

def insert_read_more_link(instance):
    """
    Insert an inline "read more" link into the last element of the summary
    :param instance:
    :return:
    """

    # only deals with Article type
    if type(instance) != contents.Article: return


    SUMMARY_MAX_LENGTH = instance.settings.get('SUMMARY_MAX_LENGTH')
    READ_MORE_LINK = instance.settings.get('READ_MORE_LINK', None)
    READ_MORE_LINK_FORMAT = instance.settings.get('READ_MORE_LINK_FORMAT',
                                                  '<a class="read-more" href="/{url}">{text}</a>')

    if not (SUMMARY_MAX_LENGTH and READ_MORE_LINK and READ_MORE_LINK_FORMAT): return

    if hasattr(instance, '_summary') and instance._summary:
        summary = instance._summary
    else:
        summary = truncate_html_words(instance.content, SUMMARY_MAX_LENGTH)

    if summary<instance.content:
        read_more_link = READ_MORE_LINK_FORMAT.format(url=instance.url, text=READ_MORE_LINK)
        instance._summary = insert_into_last_element(summary, read_more_link)

def register():
    signals.content_object_init.connect(insert_read_more_link)
########NEW FILE########
__FILENAME__ = related_posts
"""
Related posts plugin for Pelican
================================

Adds related_posts variable to article's context
"""

from pelican import signals
from collections import Counter


def add_related_posts(generator):
    # get the max number of entries from settings
    # or fall back to default (5)
    numentries = generator.settings.get('RELATED_POSTS_MAX', 5)
    for article in generator.articles:
        # set priority in case of forced related posts
        if hasattr(article,'related_posts'):
            # split slugs 
            related_posts = article.related_posts.split(',')
            posts = [] 
            # get related articles
            for slug in related_posts:
                i = 0
                for a in generator.articles:
                    if i >= numentries: # break in case there are max related psots
                        break
                    if a.slug == slug:
                        posts.append(a)
                        i += 1

            article.related_posts = posts
        else:
            # no tag, no relation
            if not hasattr(article, 'tags'):
                continue

            # score = number of common tags
            scores = Counter()
            for tag in article.tags:
                scores += Counter(generator.tags[tag])

            # remove itself
            scores.pop(article)

            article.related_posts = [other for other, count 
                in scores.most_common(numentries)]

def register():
    signals.article_generator_finalized.connect(add_related_posts)
########NEW FILE########
__FILENAME__ = math
# -*- coding: utf-8 -*-
"""
Math Render Plugin for Pelican
==============================
This plugin allows your site to render Math. It supports both LaTeX and MathML
using the MathJax JavaScript engine.

Typogrify Compatibility
-----------------------
This plugin now plays nicely with Typogrify, but it requires
Typogrify version 2.04 or above.

User Settings
-------------
Users are also able to pass a dictionary of settings in the settings file which
will control how the MathJax library renders things. This could be very useful
for template builders that want to adjust the look and feel of the math.
See README for more details.
"""

import os
import re

from pelican import signals
from pelican import contents


# Global Variables
_TYPOGRIFY = None  # if Typogrify is enabled, this is set to the typogrify.filter function
_WRAP_LATEX = None  # the tag to wrap LaTeX math in (needed to play nicely with Typogrify or for template designers)
_MATH_REGEX = re.compile(r'(\$\$|\$|\\begin\{(.+?)\}|<(math)(?:\s.*?)?>).*?(\1|\\end\{\2\}|</\3>)', re.DOTALL | re.IGNORECASE)  # used to detect math
_MATH_SUMMARY_REGEX = None  # used to match math in summary
_MATH_INCOMPLETE_TAG_REGEX = None  # used to match math that has been cut off in summary
_MATHJAX_SETTINGS = {}  # settings that can be specified by the user, used to control mathjax script settings
with open (os.path.dirname(os.path.realpath(__file__))+'/mathjax_script.txt', 'r') as mathjax_script:  # Read the mathjax javascript from file
    _MATHJAX_SCRIPT=mathjax_script.read()


# Python standard library for binary search, namely bisect is cool but I need
# specific business logic to evaluate my search predicate, so I am using my
# own version
def binary_search(match_tuple, ignore_within):
    """Determines if t is within tupleList. Using the fact that tupleList is
    ordered, binary search can be performed which is O(logn)
    """

    ignore = False
    if ignore_within == []:
        return False

    lo = 0
    hi = len(ignore_within)-1

    # Find first value in array where predicate is False
    # predicate function: tupleList[mid][0] < t[index]
    while lo < hi:
        mid = lo + (hi-lo+1)//2
        if ignore_within[mid][0] < match_tuple[0]:
            lo = mid
        else:
            hi = mid-1

    if lo >= 0 and lo <= len(ignore_within)-1:
        ignore = (ignore_within[lo][0] <= match_tuple[0] and ignore_within[lo][1] >= match_tuple[1])

    return ignore


def ignore_content(content):
    """Creates a list of match span tuples for which content should be ignored
    e.g. <pre> and <code> tags
    """
    ignore_within = []

    # used to detect all <pre> and <code> tags. NOTE: Alter this regex should
    # additional tags need to be ignored
    ignore_regex = re.compile(r'<(pre|code)(?:\s.*?)?>.*?</(\1)>', re.DOTALL | re.IGNORECASE)

    for match in ignore_regex.finditer(content):
        ignore_within.append(match.span())

    return ignore_within


def wrap_math(content, ignore_within):
    """Wraps math in user specified tags.

    This is needed for Typogrify to play nicely with math but it can also be
    styled by template providers
    """

    wrap_math.found_math = False

    def math_tag_wrap(match):
        """function for use in re.sub"""

        # determine if the tags are within <pre> and <code> blocks
        ignore = binary_search(match.span(1), ignore_within) or binary_search(match.span(4), ignore_within)

        if ignore or match.group(3) == 'math':
            if match.group(3) == 'math':
                # Will detect mml, but not wrap anything around it
                wrap_math.found_math = True

            return match.group(0)
        else:
            wrap_math.found_math = True
            return '<%s>%s</%s>' % (_WRAP_LATEX, match.group(0), _WRAP_LATEX)

    return (_MATH_REGEX.sub(math_tag_wrap, content), wrap_math.found_math)


def process_summary(instance, ignore_within):
    """Summaries need special care. If Latex is cut off, it must be restored.

    In addition, the mathjax script must be included if necessary thereby
    making it independent to the template
    """

    process_summary.altered_summary = False
    insert_mathjax = False
    end_tag = '</%s>' % _WRAP_LATEX if _WRAP_LATEX is not None else ''

    # use content's _get_summary method to obtain summary
    summary = instance._get_summary()

    # Determine if there is any math in the summary which are not within the
    # ignore_within tags
    math_item = None
    for math_item in _MATH_SUMMARY_REGEX.finditer(summary):
        ignore = binary_search(math_item.span(2), ignore_within)
        if '...' not in math_item.group(5):
            ignore = ignore or binary_search(math_item.span(5), ignore_within)
        else:
            ignore = ignore or binary_search(math_item.span(6), ignore_within)

        if ignore:
            math_item = None # In <code> or <pre> tags, so ignore
        else:
            insert_mathjax = True

    # Repair the math if it was cut off math_item will be the final math
    # code  matched that is not within <pre> or <code> tags
    if math_item and '...' in math_item.group(5):
        if math_item.group(3) is not None:
            end = r'\end{%s}' % math_item.group(3)
        elif math_item.group(4) is not None:
            end = r'</math>'
        elif math_item.group(2) is not None:
            end = math_item.group(2)

        search_regex = r'%s(%s.*?%s)' % (re.escape(instance._content[0:math_item.start(1)]), re.escape(math_item.group(1)), re.escape(end))
        math_match = re.search(search_regex, instance._content, re.DOTALL | re.IGNORECASE)

        if math_match:
            new_summary = summary.replace(math_item.group(0), math_match.group(1)+'%s ...' % end_tag)

            if new_summary != summary:
                if _MATHJAX_SETTINGS['auto_insert']:
                    return new_summary+_MATHJAX_SCRIPT.format(**_MATHJAX_SETTINGS)
                else:
                    instance.mathjax = True
                    return new_summary

    def incomplete_end_latex_tag(match):
        """function for use in re.sub"""
        if binary_search(match.span(3), ignore_within):
            return match.group(0)

        process_summary.altered_summary = True
        return match.group(1) + match.group(4)

    # check for partial math tags at end. These must be removed
    summary = _MATH_INCOMPLETE_TAG_REGEX.sub(incomplete_end_latex_tag, summary)

    if process_summary.altered_summary or insert_mathjax:
        if insert_mathjax:
            if _MATHJAX_SETTINGS['auto_insert']:
                summary+= _MATHJAX_SCRIPT.format(**_MATHJAX_SETTINGS)
            else:
                instance.mathjax = True

        return summary

    return None  # Making it explicit that summary was not altered


def process_settings(settings):
    """Sets user specified MathJax settings (see README for more details)"""

    global _MATHJAX_SETTINGS

    # NOTE TO FUTURE DEVELOPERS: Look at the README and what is happening in
    # this function if any additional changes to the mathjax settings need to
    # be incorporated. Also, please inline comment what the variables
    # will be used for

    # Default settings
    _MATHJAX_SETTINGS['align'] = 'center'  # controls alignment of of displayed equations (values can be: left, right, center)
    _MATHJAX_SETTINGS['indent'] = '0em'  # if above is not set to 'center', then this setting acts as an indent
    _MATHJAX_SETTINGS['show_menu'] = 'true'  # controls whether to attach mathjax contextual menu
    _MATHJAX_SETTINGS['process_escapes'] = 'true'  # controls whether escapes are processed
    _MATHJAX_SETTINGS['latex_preview'] = 'TeX'  # controls what user sees while waiting for LaTex to render
    _MATHJAX_SETTINGS['color'] = 'black'  # controls color math is rendered in

    # Source for MathJax: default (below) is to automatically determine what protocol to use
    _MATHJAX_SETTINGS['source'] = """'https:' == document.location.protocol
                ? 'https://c328740.ssl.cf1.rackcdn.com/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML'
                : 'http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML'"""

    # This next setting controls whether the mathjax script should be automatically
    # inserted into the content. The mathjax script will not be inserted into
    # the content if no math is detected. For summaries that are present in the
    # index listings, mathjax script will also be automatically inserted.
    # Setting this value to false means the template must be altered if this
    # plugin is to work, and so it is only recommended for the template
    # designer who wants maximum control.
    _MATHJAX_SETTINGS['auto_insert'] = True  # controls whether mathjax script is automatically inserted into the content

    if not isinstance(settings, dict):
        return

    # The following mathjax settings can be set via the settings dictionary
    # Iterate over dictionary in a way that is compatible with both version 2
    # and 3 of python
    for key, value in ((key, settings[key]) for key in settings):
        if key == 'auto_insert' and isinstance(value, bool):
            _MATHJAX_SETTINGS[key] = value

        if key == 'align' and isinstance(value, str):
            if value == 'left' or value == 'right' or value == 'center':
                _MATHJAX_SETTINGS[key] = value
            else:
                _MATHJAX_SETTINGS[key] = 'center'

        if key == 'indent':
            _MATHJAX_SETTINGS[key] = value

        if key == 'show_menu' and isinstance(value, bool):
            _MATHJAX_SETTINGS[key] = 'true' if value else 'false'

        if key == 'process_escapes' and isinstance(value, bool):
            _MATHJAX_SETTINGS[key] = 'true' if value else 'false'

        if key == 'latex_preview' and isinstance(value, str):
            _MATHJAX_SETTINGS[key] = value

        if key == 'color' and isinstance(value, str):
            _MATHJAX_SETTINGS[key] = value

        if key == 'ssl' and isinstance(value, str):
            if value == 'off':
                _MATHJAX_SETTINGS['source'] = "'http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML'"

            if value == 'force':
                _MATHJAX_SETTINGS['source'] = "'https://c328740.ssl.cf1.rackcdn.com/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML'"


def process_content(instance):
    """Processes content, with logic to ensure that Typogrify does not clash
    with math.

    In addition, mathjax script is inserted at the end of the content thereby
    making it independent of the template
    """

    if not instance._content:
        return

    ignore_within = ignore_content(instance._content)

    if _WRAP_LATEX:
        instance._content, math = wrap_math(instance._content, ignore_within)
    else:
        math = True if _MATH_REGEX.search(instance._content) else False

    # The user initially set Typogrify to be True, but since it would clash
    # with math, we set it to False. This means that the default reader will
    # not call Typogrify, so it is called here, where we are able to control
    # logic for it ignore math if necessary
    if _TYPOGRIFY:
        # Tell Typogrify to ignore the tags that math has been wrapped in
        # also, Typogrify must always ignore mml (math) tags
        ignore_tags = [_WRAP_LATEX,'math'] if _WRAP_LATEX else ['math']

        # Exact copy of the logic as found in the default reader
        instance._content = _TYPOGRIFY(instance._content, ignore_tags)
        instance.metadata['title'] = _TYPOGRIFY(instance.metadata['title'], ignore_tags)

    if math:
        if _MATHJAX_SETTINGS['auto_insert']:
            # Mathjax script added to content automatically. Now it
            # does not need to be explicitly added to the template
            instance._content += _MATHJAX_SCRIPT.format(**_MATHJAX_SETTINGS)
        else:
            # Place the burden on ensuring mathjax script is available to
            # browser on the template designer (see README for more details)
            instance.mathjax = True

        # The summary needs special care because math math cannot just be cut
        # off
        summary = process_summary(instance, ignore_within)
        if summary is not None:
            instance._summary = summary


def pelican_init(pelicanobj):
    """Intialializes certain global variables and sets typogogrify setting to
    False should it be set to True.
    """

    global _TYPOGRIFY
    global _WRAP_LATEX
    global _MATH_SUMMARY_REGEX
    global _MATH_INCOMPLETE_TAG_REGEX

    try:
        settings = pelicanobj.settings['MATH']
    except:
        settings = None

    process_settings(settings)

    # Allows MathJax script to be accessed from template should it be needed
    pelicanobj.settings['MATHJAXSCRIPT'] = _MATHJAX_SCRIPT.format(**_MATHJAX_SETTINGS)

    # If Typogrify set to True, then we need to handle it manually so it does
    # not conflict with LaTeX
    try:
        if pelicanobj.settings['TYPOGRIFY'] is True:
            pelicanobj.settings['TYPOGRIFY'] = False
            try:
                from typogrify.filters import typogrify

                # Determine if this is the correct version of Typogrify to use
                import inspect
                typogrify_args = inspect.getargspec(typogrify).args
                if len(typogrify_args) < 2 or 'ignore_tags' not in typogrify_args:
                    raise TypeError('Incorrect version of Typogrify')

                # At this point, we are happy to use Typogrify, meaning
                # it is installed and it is a recent enough version
                # that can be used to ignore all math
                _TYPOGRIFY = typogrify
                _WRAP_LATEX = 'mathjax' # default to wrap mathjax content inside of
            except ImportError:
                print("\nTypogrify is not installed, so it is being ignored.\nIf you want to use it, please install via: pip install typogrify\n")
            except TypeError:
                print("\nA more recent version of Typogrify is needed for the render_math module.\nPlease upgrade Typogrify to the latest version (anything above version 2.04 is okay).\nTypogrify will be turned off due to this reason.\n")
    except KeyError:
        pass

    # Set _WRAP_LATEX to the settings tag if defined. The idea behind this is
    # to give template designers control over how math would be rendered
    try:
        if pelicanobj.settings['MATH']['wrap_latex']:
            _WRAP_LATEX = pelicanobj.settings['MATH']['wrap_latex']
    except (KeyError, TypeError):
        pass

    # regular expressions that depend on _WRAP_LATEX are set here
    tag_start= r'<%s>' % _WRAP_LATEX if not _WRAP_LATEX is None else ''
    tag_end = r'</%s>' % _WRAP_LATEX if not _WRAP_LATEX is None else ''
    math_summary_regex = r'((\$\$|\$|\\begin\{(.+?)\}|<(math)(?:\s.*?)?>).+?)(\2|\\end\{\3\}|</\4>|\s?\.\.\.)(%s|</\4>)?' % tag_end

    # NOTE: The logic in _get_summary will handle <math> correctly because it
    # is perceived as an html tag. Therefore we are only interested in handling
    # non mml (i.e. LaTex)
    incomplete_end_latex_tag = r'(.*)(%s)(\\\S*?|\$)\s*?(\s?\.\.\.)(%s)?$' % (tag_start, tag_end)

    _MATH_SUMMARY_REGEX = re.compile(math_summary_regex, re.DOTALL | re.IGNORECASE)
    _MATH_INCOMPLETE_TAG_REGEX = re.compile(incomplete_end_latex_tag, re.DOTALL | re.IGNORECASE)


def register():
    """Plugin registration"""

    signals.initialized.connect(pelican_init)
    signals.content_object_init.connect(process_content)

########NEW FILE########
__FILENAME__ = representative_image
from pelican import signals
from pelican.contents import Content, Article
from bs4 import BeautifulSoup

def images_extraction(instance):
    representativeImage = None
    if type(instance) == Article:
        # Process Summary:
        # If summary contains images, extract one to be the representativeImage and remove images from summary
        soup = BeautifulSoup(instance.summary, 'html.parser')
        images = soup.find_all('img')
        for i in images:
            if not representativeImage:
                representativeImage = i['src']
            i.extract()
        if len(images) > 0:
            # set _summary field which is based on metadata. summary field is only based on article's content and not settable
            instance._summary = unicode(soup)
        
        # If there are no image in summary, look for it in the content body
        if not representativeImage:
            soup = BeautifulSoup(instance.content, 'html.parser')
            imageTag = soup.find('img')
            if imageTag:
                representativeImage = imageTag['src']
        
        # Set the attribute to content instance
        instance.featured_image = representativeImage

def register():
    signals.content_object_init.connect(images_extraction)

########NEW FILE########
__FILENAME__ = test_representative_image
#!/bin/sh
import unittest

from jinja2.utils import generate_lorem_ipsum

# Generate content with image 
TEST_CONTENT_IMAGE_URL = 'https://testimage.com/test.jpg' 
TEST_CONTENT = str(generate_lorem_ipsum(n=3, html=True)) + '<img src="' + TEST_CONTENT_IMAGE_URL + '"/>'+ str(generate_lorem_ipsum(n=2,html=True))
TEST_SUMMARY_IMAGE_URL = 'https://testimage.com/summary.jpg'
TEST_SUMMARY_WITHOUTIMAGE = str(generate_lorem_ipsum(n=1, html=True))
TEST_SUMMARY_WITHIMAGE = TEST_SUMMARY_WITHOUTIMAGE + '<img src="' + TEST_SUMMARY_IMAGE_URL + '"/>'


from pelican.contents import Article
import representative_image

class TestRepresentativeImage(unittest.TestCase):

    def setUp(self):
        super(TestRepresentativeImage, self).setUp()
        representative_image.register()

    def test_extract_image_from_content(self): 
        args = {
            'content': TEST_CONTENT,
            'metadata': {
                'summary': TEST_SUMMARY_WITHOUTIMAGE,
            },
        }

        article = Article(**args)
        self.assertEqual(article.featured_image, TEST_CONTENT_IMAGE_URL)

    def test_extract_image_from_summary(self):
        args = {
            'content': TEST_CONTENT,
            'metadata': {
                'summary': TEST_SUMMARY_WITHIMAGE,
            },
        }

        article = Article(**args)
        self.assertEqual(article.featured_image, TEST_SUMMARY_IMAGE_URL)
        self.assertEqual(article.summary, TEST_SUMMARY_WITHOUTIMAGE)

if __name__ == '__main__':
    unittest.main()
        







########NEW FILE########
__FILENAME__ = share_post
"""
Share Post
==========

This plugin adds share URL to article. These links are textual which means no
online tracking of your readers.
"""

from bs4 import BeautifulSoup
try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote
from pelican import signals, contents


def article_title(content):
    main_title = BeautifulSoup(content.title, 'html.parser').prettify().strip()
    sub_title = ''
    if hasattr(content, 'subtitle'):
        sub_title = BeautifulSoup(content.subtitle, 'html.parser').prettify().strip()
    return quote(('%s %s' % (main_title, sub_title)).encode('utf-8'))


def article_url(content):
    site_url = content.settings['SITEURL']
    return quote(('%s/%s' % (site_url, content.url)).encode('utf-8'))


def article_summary(content):
    return quote(content.summary.encode('utf-8'))


def share_post(content):
    if isinstance(content, contents.Static):
        return
    title = article_title(content)
    url = article_url(content)
    summary = article_summary(content)

    tweet = '%s %s' % (title, url)
    facebook_link = 'http://www.facebook.com/sharer/sharer.php?s=100' \
                    '&p[url]=%s&p[images][0]=&p[title]=%s&p[summary]=%s' \
                    % (url, title, summary)
    gplus_link = 'https://plus.google.com/share?url=%s' % url
    twitter_link = 'http://twitter.com/home?status=%s' % tweet
    mail_link = 'mailto:?subject=%s&body=%s' % (title, url)

    share_links = {'twitter': twitter_link,
                   'facebook': facebook_link,
                   'google-plus': gplus_link,
                   'email': mail_link
                   }
    content.share_post = share_links


def register():
    signals.content_object_init.connect(share_post)

########NEW FILE########
__FILENAME__ = simple_footnotes
from pelican import signals
import re
import html5lib

RAW_FOOTNOTE_CONTAINERS = ["code"]

def getText(node, recursive = False):
    """Get all the text associated with this node.
       With recursive == True, all text from child nodes is retrieved."""
    L = ['']
    for n in node.childNodes:
        if n.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
            L.append(n.data)
        else:
            if not recursive:
                return None
        L.append(getText(n) )
    return ''.join(L)

def parse_for_footnotes(article_generator):
    for article in article_generator.articles:
        if "[ref]" in article._content and "[/ref]" in article._content:
            content = article._content.replace("[ref]", "<x-simple-footnote>").replace("[/ref]", "</x-simple-footnote>")
            parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"))
            dom = parser.parse(content)
            endnotes = []
            count = 0
            for footnote in dom.getElementsByTagName("x-simple-footnote"):
                pn = footnote
                leavealone = False
                while pn:
                    if pn.nodeName in RAW_FOOTNOTE_CONTAINERS:
                        leavealone = True
                        break
                    pn = pn.parentNode
                if leavealone:
                    continue
                count += 1
                fnid = "sf-%s-%s" % (article.slug, count)
                fnbackid = "%s-back" % (fnid,)
                endnotes.append((footnote, fnid, fnbackid))
                number = dom.createElement("sup")
                number.setAttribute("id", fnbackid)
                numbera = dom.createElement("a")
                numbera.setAttribute("href", "#%s" % fnid)
                numbera.setAttribute("class", "simple-footnote")
                numbera.appendChild(dom.createTextNode(str(count)))
                txt = getText(footnote, recursive=True).replace("\n", " ")
                numbera.setAttribute("title", txt)
                number.appendChild(numbera)
                footnote.parentNode.insertBefore(number, footnote)
            if endnotes:
                ol = dom.createElement("ol")
                ol.setAttribute("class", "simple-footnotes")
                for e, fnid, fnbackid in endnotes:
                    li = dom.createElement("li")
                    li.setAttribute("id", fnid)
                    while e.firstChild:
                        li.appendChild(e.firstChild)
                    backlink = dom.createElement("a")
                    backlink.setAttribute("href", "#%s" % fnbackid)
                    backlink.setAttribute("class", "simple-footnote-back")
                    backlink.appendChild(dom.createTextNode(u'\u21a9'))
                    li.appendChild(dom.createTextNode(" "))
                    li.appendChild(backlink)
                    ol.appendChild(li)
                    e.parentNode.removeChild(e)
                dom.getElementsByTagName("body")[0].appendChild(ol)
                s = html5lib.serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False, quote_attr_values=True)
                output_generator = s.serialize(html5lib.treewalkers.getTreeWalker("dom")(dom.getElementsByTagName("body")[0]))
                article._content =  "".join(list(output_generator)).replace(
                    "<x-simple-footnote>", "[ref]").replace("</x-simple-footnote>", "[/ref]").replace(
                    "<body>", "").replace("</body>", "")
        if False:
            count = 0
            endnotes = []
            for f in footnotes:
                count += 1
                fnstr = '<a class="simple-footnote" name="%s-%s-back" href="#%s-%s"><sup>%s</a>' % (
                    article.slug, count, article.slug, count, count)
                endstr = '<li id="%s-%s">%s <a href="#%s-%s-back">&uarr;</a></li>' % (
                    article.slug, count, f[len("[ref]"):-len("[/ref]")], article.slug, count)
                content = content.replace(f, fnstr)
                endnotes.append(endstr)
            content += '<h4>Footnotes</h4><ol class="simple-footnotes">%s</ul>' % ("\n".join(endnotes),)
            article._content = content


def register():
    signals.article_generator_finalized.connect(parse_for_footnotes)


########NEW FILE########
__FILENAME__ = test_simple_footnotes
import unittest
from simple_footnotes import parse_for_footnotes

class PseudoArticleGenerator(object):
    articles = []
class PseudoArticle(object):
    _content = ""
    slug = "article"

class TestFootnotes(unittest.TestCase):

    def _expect(self, input, expected_output):
        ag = PseudoArticleGenerator()
        art = PseudoArticle()
        art._content = input
        ag.articles = [art]
        parse_for_footnotes(ag)
        self.assertEqual(art._content, expected_output)

    def test_simple(self):
        self._expect("words[ref]footnote[/ref]end",
        ('words<sup id="sf-article-1-back"><a title="footnote" '
         'href="#sf-article-1" class="simple-footnote">1</a></sup>end'
         '<ol class="simple-footnotes">'
         u'<li id="sf-article-1">footnote <a href="#sf-article-1-back" class="simple-footnote-back">\u21a9</a></li>'
         '</ol>'))

    def test_no_footnote_inside_code(self):
        self._expect("words<code>this is code[ref]footnote[/ref] end code </code> end",
            "words<code>this is code[ref]footnote[/ref] end code </code> end")

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = sitemap
﻿# -*- coding: utf-8 -*-
'''
Sitemap
-------

The sitemap plugin generates plain-text or XML sitemaps.
'''

from __future__ import unicode_literals

import collections
import os.path

from datetime import datetime
from logging import warning, info
from codecs import open

from pelican import signals, contents
from pelican.utils import get_date

TXT_HEADER = """{0}/index.html
{0}/archives.html
{0}/tags.html
{0}/categories.html
"""

XML_HEADER = """<?xml version="1.0" encoding="utf-8"?>
<urlset xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd"
xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

XML_URL = """
<url>
<loc>{0}/{1}</loc>
<lastmod>{2}</lastmod>
<changefreq>{3}</changefreq>
<priority>{4}</priority>
</url>
"""

XML_FOOTER = """
</urlset>
"""


def format_date(date):
    if date.tzinfo:
        tz = date.strftime('%s')
        tz = tz[:-2] + ':' + tz[-2:]
    else:
        tz = "-00:00"
    return date.strftime("%Y-%m-%dT%H:%M:%S") + tz

class SitemapGenerator(object):

    def __init__(self, context, settings, path, theme, output_path, *null):

        self.output_path = output_path
        self.context = context
        self.now = datetime.now()
        self.siteurl = settings.get('SITEURL')

        self.format = 'xml'

        self.changefreqs = {
            'articles': 'monthly',
            'indexes': 'daily',
            'pages': 'monthly'
        }

        self.priorities = {
            'articles': 0.5,
            'indexes': 0.5,
            'pages': 0.5
        }

        config = settings.get('SITEMAP', {})

        if not isinstance(config, dict):
            warning("sitemap plugin: the SITEMAP setting must be a dict")
        else:
            fmt = config.get('format')
            pris = config.get('priorities')
            chfreqs = config.get('changefreqs')

            if fmt not in ('xml', 'txt'):
                warning("sitemap plugin: SITEMAP['format'] must be `txt' or `xml'")
                warning("sitemap plugin: Setting SITEMAP['format'] on `xml'")
            elif fmt == 'txt':
                self.format = fmt
                return

            valid_keys = ('articles', 'indexes', 'pages')
            valid_chfreqs = ('always', 'hourly', 'daily', 'weekly', 'monthly',
                    'yearly', 'never')

            if isinstance(pris, dict):
                # We use items for Py3k compat. .iteritems() otherwise
                for k, v in pris.items():
                    if k in valid_keys and not isinstance(v, (int, float)):
                        default = self.priorities[k]
                        warning("sitemap plugin: priorities must be numbers")
                        warning("sitemap plugin: setting SITEMAP['priorities']"
                                "['{0}'] on {1}".format(k, default))
                        pris[k] = default
                self.priorities.update(pris)
            elif pris is not None:
                warning("sitemap plugin: SITEMAP['priorities'] must be a dict")
                warning("sitemap plugin: using the default values")

            if isinstance(chfreqs, dict):
                # .items() for py3k compat.
                for k, v in chfreqs.items():
                    if k in valid_keys and v not in valid_chfreqs:
                        default = self.changefreqs[k]
                        warning("sitemap plugin: invalid changefreq `{0}'".format(v))
                        warning("sitemap plugin: setting SITEMAP['changefreqs']"
                                "['{0}'] on '{1}'".format(k, default))
                        chfreqs[k] = default
                self.changefreqs.update(chfreqs)
            elif chfreqs is not None:
                warning("sitemap plugin: SITEMAP['changefreqs'] must be a dict")
                warning("sitemap plugin: using the default values")

    def write_url(self, page, fd):

        if getattr(page, 'status', 'published') != 'published':
            return

        page_path = os.path.join(self.output_path, page.save_as)
        if not os.path.exists(page_path):
            return

        lastdate = getattr(page, 'date', self.now)
        try:
            lastdate = self.get_date_modified(page, lastdate)
        except ValueError:
            warning("sitemap plugin: " + page.save_as + " has invalid modification date,")
            warning("sitemap plugin: using date value as lastmod.")
        lastmod = format_date(lastdate)

        if isinstance(page, contents.Article):
            pri = self.priorities['articles']
            chfreq = self.changefreqs['articles']
        elif isinstance(page, contents.Page):
            pri = self.priorities['pages']
            chfreq = self.changefreqs['pages']
        else:
            pri = self.priorities['indexes']
            chfreq = self.changefreqs['indexes']


        if self.format == 'xml':
            fd.write(XML_URL.format(self.siteurl, page.url, lastmod, chfreq, pri))
        else:
            fd.write(self.siteurl + '/' + page.url + '\n')

    def get_date_modified(self, page, default):
        if hasattr(page, 'modified'):
            if isinstance(page.modified, datetime):
                return page.modified
            return get_date(page.modified)
        else:
            return default

    def set_url_wrappers_modification_date(self, wrappers):
        for (wrapper, articles) in wrappers:
            lastmod = datetime.min
            for article in articles:
                lastmod = max(lastmod, article.date)
                try:
                    modified = self.get_date_modified(article, datetime.min);
                    lastmod = max(lastmod, modified)
                except ValueError:
                    # Supressed: user will be notified.
                    pass
            setattr(wrapper, 'modified', str(lastmod))

    def generate_output(self, writer):
        path = os.path.join(self.output_path, 'sitemap.{0}'.format(self.format))

        pages = self.context['pages'] + self.context['articles'] \
                + [ c for (c, a) in self.context['categories']] \
                + [ t for (t, a) in self.context['tags']] \
                + [ a for (a, b) in self.context['authors']]

        self.set_url_wrappers_modification_date(self.context['categories'])
        self.set_url_wrappers_modification_date(self.context['tags'])
        self.set_url_wrappers_modification_date(self.context['authors'])

        for article in self.context['articles']:
            pages += article.translations

        info('writing {0}'.format(path))

        with open(path, 'w', encoding='utf-8') as fd:

            if self.format == 'xml':
                fd.write(XML_HEADER)
            else:
                fd.write(TXT_HEADER.format(self.siteurl))

            FakePage = collections.namedtuple('FakePage',
                                              ['status',
                                               'date',
                                               'url',
                                               'save_as'])

            for standard_page_url in ['index.html',
                                      'archives.html',
                                      'tags.html',
                                      'categories.html']:
                fake = FakePage(status='published',
                                date=self.now,
                                url=standard_page_url,
                                save_as=standard_page_url)
                self.write_url(fake, fd)

            for page in pages:
                self.write_url(page, fd)

            if self.format == 'xml':
                fd.write(XML_FOOTER)


def get_generators(generators):
    return SitemapGenerator


def register():
    signals.get_generators.connect(get_generators)

########NEW FILE########
__FILENAME__ = static_comments
# -*- coding: utf-8 -*-

import codecs
import logging
import markdown
import os

logger = logging.getLogger(__name__)

from pelican import signals


def initialized(pelican):
    from pelican.settings import DEFAULT_CONFIG
    DEFAULT_CONFIG.setdefault('STATIC_COMMENTS', False)
    DEFAULT_CONFIG.setdefault('STATIC_COMMENTS_DIR' 'comments')
    if pelican:
        pelican.settings.setdefault('STATIC_COMMENTS', False)
        pelican.settings.setdefault('STATIC_COMMENTS_DIR', 'comments')


def add_static_comments(gen, metadata):
    if gen.settings['STATIC_COMMENTS'] != True:
        return

    if not 'slug' in metadata:
        logger.warning("static_comments: "
                "cant't locate comments file without slug tag in the article")
        return

    fname = os.path.join(gen.settings['STATIC_COMMENTS_DIR'],
            metadata['slug'] + ".md")

    if not os.path.exists(fname):
        return

    input_file = codecs.open(fname, mode="r", encoding="utf-8")
    text = input_file.read()
    html = markdown.markdown(text)

    metadata['static_comments'] = html


def register():
    signals.initialized.connect(initialized)
    signals.article_generator_context.connect(add_static_comments)

########NEW FILE########
__FILENAME__ = subcategory
# -*- coding: utf-8 -*-
"""
@Author: Alistair Magee

Adds support for subcategories on pelican articles
"""
import os
from collections import defaultdict
from operator import attrgetter
from functools import partial

from pelican import signals
from pelican.urlwrappers import URLWrapper, Category
from pelican.utils import (slugify, python_2_unicode_compatible)

from six import text_type

class SubCategory(URLWrapper):
    def __init__(self, name, parent, settings):
        super(SubCategory, self).__init__(name, settings)
        self.parent = parent
        self.shortname = name.split('/')
        self.shortname = self.shortname.pop()
        self.slug = slugify(self.shortname, settings.get('SLUG_SUBSTITUIONS', ()))
        if isinstance(self.parent, SubCategory):
            self.savepath = os.path.join(self.parent.savepath, self.slug)
            self.fullurl = '{}/{}'.format(self.parent.fullurl, self.slug)
        else: #parent is a category
            self.savepath = os.path.join(self.parent.slug, self.slug)
            self.fullurl = '{}/{}'.format(self.parent.slug, self.slug)
        
    def as_dict(self):
        d = self.__dict__
        d['shortname'] = self.shortname
        d['savepath'] = self.savepath
        d['fullurl'] = self.fullurl
        d['parent'] = self.parent
        return d

    def __hash__(self):
        return hash(self.fullurl)

    def _key(self):
        return self.fullurl

def get_subcategories(generator, metadata):
    if 'SUBCATEGORY_SAVE_AS' not in generator.settings:
        generator.settings['SUBCATEGORY_SAVE_AS'] = os.path.join( 
                'subcategory', '{savepath}.html')
    if 'SUBCATEGORY_URL' not in generator.settings:
        generator.settings['SUBCATEGORY_URL'] = 'subcategory/{fullurl}.html'
    
    category_list = text_type(metadata.get('category')).split('/')
    category = (category_list.pop(0)).strip()
    category = Category(category, generator.settings)
    metadata['category'] = category
    #generate a list of subcategories with their parents
    sub_list = []
    parent = category.name
    for subcategory in category_list:
        subcategory.strip()
        subcategory = parent + '/' + subcategory
        sub_list.append(subcategory)
        parent = subcategory
    metadata['subcategories'] = sub_list

def create_subcategories(generator):
    generator.subcategories = []
    for article in generator.articles:
        parent = article.category
        actual_subcategories = []
        for subcategory in article.subcategories:
            #following line returns a list of items, tuples in this case
            sub_cat = [item for item in generator.subcategories 
                    if item[0].name == subcategory]
            if sub_cat:
                sub_cat[0][1].append(article)
                parent = sub_cat[0][0]
                actual_subcategories.append(parent)
            else:
                new_sub = SubCategory(subcategory, parent, generator.settings)
                generator.subcategories.append((new_sub, [article,]))
                parent = new_sub
                actual_subcategories.append(parent)
        article.subcategories = actual_subcategories

def generate_subcategories(generator, writer):
    write = partial(writer.write_file,
            relative_urls=generator.settings['RELATIVE_URLS'])
    subcategory_template = generator.get_template('subcategory')
    for subcat, articles in generator.subcategories:
        articles.sort(key=attrgetter('date'), reverse=True)
        dates = [article for article in generator.dates if article in articles]
        write(subcat.save_as, subcategory_template, generator.context, 
                subcategory=subcat, articles=articles, dates=dates, 
                paginated={'articles': articles, 'dates': dates},
                page_name=subcat.page_name, all_articles=generator.articles)

def generate_subcategory_feeds(generator, writer):
    for subcat, articles in generator.subcategories:
        articles.sort(key=attrgetter('date'), reverse=True)
        if generator.settings.get('SUBCATEGORY_FEED_ATOM'):
            writer.write_feed(articles, generator.context,
                    generator.settings['SUBCATEGORY_FEED_ATOM']
                    % subcat.fullurl)
        if generator.settings.get('SUBCATEGORY_FEED_RSS'):
            writer.write_feed(articles, generator.context,
                    generator.settings['SUBCATEGORY_FEED_RSS']
                    % subcat.fullurl, feed_type='rss')

def generate(generator, writer):
    generate_subcategory_feeds(generator, writer)
    generate_subcategories(generator, writer)

def register():
    signals.article_generator_context.connect(get_subcategories)
    signals.article_generator_finalized.connect(create_subcategories)
    signals.article_writer_finalized.connect(generate)

########NEW FILE########
__FILENAME__ = summary
"""
Summary
-------

This plugin allows easy, variable length summaries directly embedded into the 
body of your articles.
"""

import types

from pelican import signals

def initialized(pelican):
    from pelican.settings import DEFAULT_CONFIG
    DEFAULT_CONFIG.setdefault('SUMMARY_BEGIN_MARKER',
                              '<!-- PELICAN_BEGIN_SUMMARY -->')
    DEFAULT_CONFIG.setdefault('SUMMARY_END_MARKER',
                              '<!-- PELICAN_END_SUMMARY -->')
    if pelican:
        pelican.settings.setdefault('SUMMARY_BEGIN_MARKER',
                                    '<!-- PELICAN_BEGIN_SUMMARY -->')
        pelican.settings.setdefault('SUMMARY_END_MARKER',
                                    '<!-- PELICAN_END_SUMMARY -->')

def content_object_init(instance):
    # if summary is already specified, use it
    if 'summary' in instance.metadata:
        return

    def _get_content(self):
        content = self._content
        if self.settings['SUMMARY_BEGIN_MARKER']:
            content = content.replace(
                self.settings['SUMMARY_BEGIN_MARKER'], '', 1)
        if self.settings['SUMMARY_END_MARKER']:
            content = content.replace(
                self.settings['SUMMARY_END_MARKER'], '', 1)
        return content
    instance._get_content = types.MethodType(_get_content, instance)

    # extract out our summary
    if not hasattr(instance, '_summary') and instance._content is not None:
        content = instance._content
        begin_summary = -1
        end_summary = -1
        if instance.settings['SUMMARY_BEGIN_MARKER']:
            begin_summary = content.find(instance.settings['SUMMARY_BEGIN_MARKER'])
        if instance.settings['SUMMARY_END_MARKER']:
            end_summary = content.find(instance.settings['SUMMARY_END_MARKER'])
        if begin_summary != -1 or end_summary != -1:
            # the beginning position has to take into account the length
            # of the marker
            begin_summary = (begin_summary +
                            len(instance.settings['SUMMARY_BEGIN_MARKER'])
                            if begin_summary != -1 else 0)
            end_summary = end_summary if end_summary != -1 else None
            instance._summary = instance._update_content(content[begin_summary:end_summary], instance._context.get('localsiteurl', ''))

def register():
    signals.initialized.connect(initialized)
    signals.content_object_init.connect(content_object_init)

########NEW FILE########
__FILENAME__ = test_summary
# -*- coding: utf-8 -*-

import unittest

from jinja2.utils import generate_lorem_ipsum

# generate one paragraph, enclosed with <p>
TEST_CONTENT = str(generate_lorem_ipsum(n=1))
TEST_SUMMARY = generate_lorem_ipsum(n=1, html=False)


from pelican.contents import Page

import summary

class TestSummary(unittest.TestCase):
    def setUp(self):
        super(TestSummary, self).setUp()

        summary.register()
        summary.initialized(None)
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
        }

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

    def test_end_summary(self):
        page_kwargs = self._copy_page_kwargs()
        del page_kwargs['metadata']['summary']
        page_kwargs['content'] = (
            TEST_SUMMARY + '<!-- PELICAN_END_SUMMARY -->' + TEST_CONTENT)
        page = Page(**page_kwargs)
        # test both the summary and the marker removal
        self.assertEqual(page.summary, TEST_SUMMARY)
        self.assertEqual(page.content, TEST_SUMMARY + TEST_CONTENT)

    def test_begin_summary(self):
        page_kwargs = self._copy_page_kwargs()
        del page_kwargs['metadata']['summary']
        page_kwargs['content'] = (
            'FOOBAR<!-- PELICAN_BEGIN_SUMMARY -->' + TEST_CONTENT)
        page = Page(**page_kwargs)
        # test both the summary and the marker removal
        self.assertEqual(page.summary, TEST_CONTENT)
        self.assertEqual(page.content, 'FOOBAR' + TEST_CONTENT)

    def test_begin_end_summary(self):
        page_kwargs = self._copy_page_kwargs()
        del page_kwargs['metadata']['summary']
        page_kwargs['content'] = (
                'FOOBAR<!-- PELICAN_BEGIN_SUMMARY -->' + TEST_SUMMARY +
                '<!-- PELICAN_END_SUMMARY -->' + TEST_CONTENT)
        page = Page(**page_kwargs)
        # test both the summary and the marker removal
        self.assertEqual(page.summary, TEST_SUMMARY)
        self.assertEqual(page.content, 'FOOBAR' + TEST_SUMMARY + TEST_CONTENT)

########NEW FILE########
__FILENAME__ = pelican.conf
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

AUTHOR = 'Alexis Métaireau'
SITENAME = "Alexis' log"
SITEURL = 'http://blog.notmyidea.org'
TIMEZONE = "Europe/Paris"

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

# static paths will be copied under the same name
STATIC_PATHS = ["pictures", ]

# A list of files to copy from the source to the destination
FILES_TO_COPY = (('extra/robots.txt', 'robots.txt'),)

# custom page generated with a jinja2 template
TEMPLATE_PAGES = {'pages/jinja2_template.html': 'jinja2_template.html'}

# foobar will not be used, because it's not in caps. All configuration keys
# have to be in caps
foobar = "barbaz"

########NEW FILE########
__FILENAME__ = test_thumbnails
from thumbnailer import _resizer
from unittest import TestCase, main
import os.path as path
from PIL import Image, ImageChops

class ThumbnailerTests(TestCase):

    def path(self, filename):
        return path.join(self.img_path, filename)

    def setUp(self):
        self.img_path = path.join(path.dirname(__file__), "test_data")
        self.img = Image.open(self.path("sample_image.jpg"))

    def testSquare(self):
        r = _resizer('square', '100')
        output = r.resize(self.img)
        self.assertEqual((100, 100), output.size)

    def testExact(self):
        r = _resizer('exact', '250x100')
        output = r.resize(self.img)
        self.assertEqual((250, 100), output.size)

    def testWidth(self):
        r = _resizer('aspect', '250x?')
        output = r.resize(self.img)
        self.assertEqual((250, 166), output.size)

    def testHeight(self):
        r = _resizer('aspect', '?x250')
        output = r.resize(self.img)
        self.assertEqual((375, 250), output.size)

if __name__=="__main__":
    main()
########NEW FILE########
__FILENAME__ = thumbnailer
import os
import os.path as path
import re
from pelican import signals

import logging
logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
    enabled = True
except ImportError:
    logging.warning("Unable to load PIL, disabling thumbnailer")
    enabled = False

DEFAULT_IMAGE_DIR = "pictures"
DEFAULT_THUMBNAIL_DIR = "thumbnails"
DEFAULT_THUMBNAIL_SIZES = {
    'thumbnail_square': '150',
    'thumbnail_wide': '150x?',
    'thumbnail_tall': '?x150',
}
DEFAULT_TEMPLATE = """<a href="{url}" rel="shadowbox" title="{filename}"><img src="{thumbnail}" alt="{filename}"></a>"""
DEFAULT_GALLERY_THUMB = "thumbnail_square"

class _resizer(object):
    """ Resizes based on a text specification, see readme """

    REGEX = re.compile(r'(\d+|\?)x(\d+|\?)')

    def __init__(self, name, spec):
        self._name = name
        self._spec = spec

    def _null_resize(self, w, h, image):
        return image

    def _exact_resize(self, w, h, image):
        retval = ImageOps.fit(image, (w,h), Image.BICUBIC)
        return retval

    def _aspect_resize(self, w, h, image):
        retval = image.copy()
        retval.thumbnail((w, h), Image.ANTIALIAS)

        return retval

    def resize(self, image):
        resizer = self._null_resize

        # Square resize and crop
        if 'x' not in self._spec:
            resizer = self._exact_resize
            targetw = int(self._spec)
            targeth = targetw
        else:
            matches = self.REGEX.search(self._spec)
            tmpw = matches.group(1)
            tmph = matches.group(2)

            # Full Size
            if tmpw == '?' and tmph == '?':
                targetw = image.size[0]
                targeth = image.size[1]
                resizer = self._null_resize

            # Set Height Size
            if tmpw == '?':
                targetw = image.size[0]
                targeth = int(tmph)
                resizer = self._aspect_resize

            # Set Width Size
            elif tmph == '?':
                targetw = int(tmpw)
                targeth = image.size[1]
                resizer = self._aspect_resize

            # Scale and Crop
            else:
                targetw = int(tmpw)
                targeth = int(tmph)
                resizer = self._exact_resize

        logging.debug("Using resizer {0}".format(resizer.__name__))
        return resizer(targetw, targeth, image)

    def get_thumbnail_name(self, in_path):
        new_filename = path.basename(in_path)
        (basename, ext) = path.splitext(new_filename)
        basename = "{0}_{1}".format(basename, self._name)
        new_filename = "{0}{1}".format(basename, ext)
        return new_filename

    def resize_file_to(self, in_path, out_path, keep_filename=False):
        """ Given a filename, resize and save the image per the specification into out_path

        :param in_path: path to image file to save.  Must be supposed by PIL
        :param out_path: path to the directory root for the outputted thumbnails to be stored
        :return: None
        """
        if keep_filename:
            filename = path.join(out_path, path.basename(in_path))
        else:
            filename = path.join(out_path, self.get_thumbnail_name(in_path))
        if not path.exists(out_path):
            os.makedirs(out_path)
        if not path.exists(filename):
            image = Image.open(in_path)
            thumbnail = self.resize(image)
            thumbnail.save(filename)
            logger.info("Generated Thumbnail {0}".format(path.basename(filename)))


def resize_thumbnails(pelican):
    """ Resize a directory tree full of images into thumbnails

    :param pelican: The pelican instance
    :return: None
    """
    global enabled
    if not enabled:
        return

    in_path = _image_path(pelican)
    out_path = path.join(pelican.settings['OUTPUT_PATH'],
                         pelican.settings.get('THUMBNAIL_DIR', DEFAULT_THUMBNAIL_DIR))

    sizes = pelican.settings.get('THUMBNAIL_SIZES', DEFAULT_THUMBNAIL_SIZES)
    resizers = dict((k, _resizer(k, v)) for k,v in sizes.items())
    logger.debug("Thumbnailer Started")
    for dirpath, _, filenames in os.walk(in_path):
        for filename in filenames:
            for name, resizer in resizers.items():
                in_filename = path.join(dirpath, filename)
                logger.debug("Processing thumbnail {0}=>{1}".format(filename, name))
                if pelican.settings.get('THUMBNAIL_KEEP_NAME', False):
                    resizer.resize_file_to(in_filename, path.join(out_path, name), True)
                else:
                    resizer.resize_file_to(in_filename, out_path)


def _image_path(pelican):
    return path.join(pelican.settings['PATH'],
                        pelican.settings.get("IMAGE_PATH", DEFAULT_IMAGE_DIR))


def expand_gallery(generator, metadata):
    """ Expand a gallery tag to include all of the files in a specific directory under IMAGE_PATH

    :param pelican: The pelican instance
    :return: None
    """
    if "gallery" not in metadata or metadata['gallery'] is None:
        return  # If no gallery specified, we do nothing

    lines = [ ]
    base_path = _image_path(generator)
    in_path = path.join(base_path, metadata['gallery'])
    template = generator.settings.get('GALLERY_TEMPLATE', DEFAULT_TEMPLATE)
    thumbnail_name = generator.settings.get("GALLERY_THUMBNAIL", DEFAULT_GALLERY_THUMB)
    thumbnail_prefix = generator.settings.get("")
    resizer = _resizer(thumbnail_name, '?x?')
    for dirpath, _, filenames in os.walk(in_path):
        for filename in filenames:
            url = path.join(dirpath, filename).replace(base_path, "")[1:]
            url = path.join('/static', generator.settings.get('IMAGE_PATH', DEFAULT_IMAGE_DIR), url).replace('\\', '/')
            logger.debug("GALLERY: {0}".format(url))
            thumbnail = resizer.get_thumbnail_name(filename)
            thumbnail = path.join('/', generator.settings.get('THUMBNAIL_DIR', DEFAULT_THUMBNAIL_DIR), thumbnail).replace('\\', '/')
            lines.append(template.format(
                filename=filename,
                url=url,
                thumbnail=thumbnail,
            ))
    metadata['gallery_content'] = "\n".join(lines)


def register():
    signals.finalized.connect(resize_thumbnails)
    signals.article_generator_context.connect(expand_gallery)

########NEW FILE########
__FILENAME__ = tipue_search
# -*- coding: utf-8 -*-
"""
Tipue Search
============

A Pelican plugin to serialize generated HTML to JSON
that can be used by jQuery plugin - Tipue Search.

Copyright (c) Talha Mansoor
"""

from __future__ import unicode_literals

import os.path
import json
from bs4 import BeautifulSoup
from codecs import open

from pelican import signals


class Tipue_Search_JSON_Generator(object):

    def __init__(self, context, settings, path, theme, output_path, *null):

        self.output_path = output_path
        self.context = context
        self.siteurl = settings.get('SITEURL')
        self.json_nodes = []

    def create_json_node(self, page):

        if getattr(page, 'status', 'published') != 'published':
            return

        soup_title = BeautifulSoup(page.title.replace('&nbsp;', ' '))
        page_title = soup_title.get_text(' ', strip=True).replace('“', '"').replace('”', '"').replace('’', "'").replace('^', '&#94;')

        soup_text = BeautifulSoup(page.content)
        page_text = soup_text.get_text(' ', strip=True).replace('“', '"').replace('”', '"').replace('’', "'").replace('¶', ' ').replace('^', '&#94;')
        page_text = ' '.join(page_text.split())

        if getattr(page, 'category', 'None') == 'None':
            page_category = ''
        else:
            page_category = page.category.name

        page_url = self.siteurl + '/' + page.url

        node = {'title': page_title,
                'text': page_text,
                'tags': page_category,
                'loc': page_url}

        self.json_nodes.append(node)

    def generate_output(self, writer):
        path = os.path.join(self.output_path, 'tipuesearch_content.json')

        pages = self.context['pages'] + self.context['articles']

        for article in self.context['articles']:
            pages += article.translations

        for page in pages:
            self.create_json_node(page)
        root_node = {'pages': self.json_nodes}

        with open(path, 'w', encoding='utf-8') as fd:
            json.dump(root_node, fd, separators=(',', ':'))


def get_generators(generators):
    return Tipue_Search_JSON_Generator


def register():
    signals.get_generators.connect(get_generators)

########NEW FILE########
__FILENAME__ = bootstrap_rst_directives
#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
Twitter Bootstrap RST directives Plugin For Pelican
===================================================

This plugin defines rst directives for different CSS and Javascript components from
the twitter bootstrap framework.

"""

from uuid import uuid1

from cgi import escape
from docutils import nodes, utils
import docutils
from docutils.parsers import rst
from docutils.parsers.rst import directives, roles, Directive
from pelican import signals
from pelican.readers import RstReader, PelicanHTMLTranslator



class CleanHTMLTranslator(PelicanHTMLTranslator):

    """
        A custom HTML translator based on the Pelican HTML translator.
        Used to clean up some components html classes that could conflict 
        with the bootstrap CSS classes.
        Also defines new tags that are not handleed by the current implementation of 
        docutils.

        The most obvious example is the Container component
    """

    def visit_literal(self, node):
        classes = node.get('classes', node.get('class', []))
        if 'code' in classes:
            self.body.append(self.starttag(node, 'code'))
        elif 'kbd' in classes:
            self.body.append(self.starttag(node, 'kbd'))
        else:
            self.body.append(self.starttag(node, 'pre'))

    def depart_literal(self, node):
        classes = node.get('classes', node.get('class', []))
        if 'code' in classes:
            self.body.append('</code>\n')
        elif 'kbd' in classes:
            self.body.append('</kbd>\n')
        else:
            self.body.append('</pre>\n')

    def visit_container(self, node):
        self.body.append(self.starttag(node, 'div'))


class CleanRSTReader(RstReader):

    """
        A custom RST reader that behaves exactly like its parent class RstReader with
        the difference that it uses the CleanHTMLTranslator
    """

    def _get_publisher(self, source_path):
        extra_params = {'initial_header_level': '2',
                        'syntax_highlight': 'short',
                        'input_encoding': 'utf-8'}
        user_params = self.settings.get('DOCUTILS_SETTINGS')
        if user_params:
            extra_params.update(user_params)

        pub = docutils.core.Publisher(
            destination_class=docutils.io.StringOutput)
        pub.set_components('standalone', 'restructuredtext', 'html')
        pub.writer.translator_class = CleanHTMLTranslator
        pub.process_programmatic_settings(None, extra_params, None)
        pub.set_source(source_path=source_path)
        pub.publish()
        return pub


def keyboard_role(name, rawtext, text, lineno, inliner,
                  options={}, content=[]):
    """
        This function creates an inline console input block as defined in the twitter bootstrap documentation
        overrides the default behaviour of the kbd role

        *usage:*
            :kbd:`<your code>`

        *Example:*

            :kbd:`<section>`

        This code is not highlighted
    """
    new_element = nodes.literal(rawtext, text)
    new_element.set_class('kbd')

    return [new_element], []


def code_role(name, rawtext, text, lineno, inliner,
              options={}, content=[]):
    """
        This function creates an inline code block as defined in the twitter bootstrap documentation
        overrides the default behaviour of the code role

        *usage:*
            :code:`<your code>`

        *Example:*

            :code:`<section>`

        This code is not highlighted
    """
    new_element = nodes.literal(rawtext, text)
    new_element.set_class('code')

    return [new_element], []


def glyph_role(name, rawtext, text, lineno, inliner,
               options={}, content=[]):
    """
        This function defines a glyph inline role that show a glyph icon from the 
        twitter bootstrap framework

        *Usage:*

            :glyph:`<glyph_name>`

        *Example:*

            Love this music :glyph:`music` :)

        Can be subclassed to include a target

        *Example:*

            .. role:: story_time_glyph(glyph)
                :target: http://www.youtube.com/watch?v=5g8ykQLYnX0
                :class: small text-info

            Love this music :story_time_glyph:`music` :)

    """

    target = options.get('target', None)
    glyph_name = 'glyphicon-{}'.format(text)

    if target:
        target = utils.unescape(target)
        new_element = nodes.reference(rawtext, ' ', refuri=target)
    else:
        new_element = nodes.container()
    classes = options.setdefault('class', [])
    classes += ['glyphicon', glyph_name]
    for custom_class in classes:
        new_element.set_class(custom_class)
    return [new_element], []

glyph_role.options = {
    'target': rst.directives.unchanged,
}
glyph_role.content = False


class Label(rst.Directive):

    '''
        generic Label directive class definition.
        This class define a directive that shows 
        bootstrap Labels around its content

        *usage:*

            .. label-<label-type>::

                <Label content>

        *example:*

            .. label-default::

                This is a default label content

    '''

    has_content = True
    custom_class = ''

    def run(self):
        # First argument is the name of the glyph
        label_name = 'label-{}'.format(self.custom_class)
        # get the label content
        text = '\n'.join(self.content)
        # Create a new container element (div)
        new_element = nodes.container(text)
        # Update its content
        self.state.nested_parse(self.content, self.content_offset,
                                new_element)
        # Set its custom bootstrap classes
        new_element['classes'] += ['label ', label_name]
        # Return one single element
        return [new_element]


class DefaultLabel(Label):

    custom_class = 'default'


class PrimaryLabel(Label):

    custom_class = 'primary'


class SuccessLabel(Label):

    custom_class = 'success'


class InfoLabel(Label):

    custom_class = 'info'


class WarningLabel(Label):

    custom_class = 'warning'


class DangerLabel(Label):

    custom_class = 'danger'


class Panel(rst.Directive):

    """
        generic Panel directive class definition.
        This class define a directive that shows 
        bootstrap Labels around its content

        *usage:*

            .. panel-<panel-type>:: 
                :title: <title>

                <Panel content>

        *example:*

            .. panel-default:: 
                :title: panel title

                This is a default panel content

    """

    has_content = True
    option_spec = {
        'title': rst.directives.unchanged,
    }
    custom_class = ''

    def run(self):
        # First argument is the name of the glyph
        panel_name = 'panel-{}'.format(self.custom_class)
        # get the label title
        title_text = self.options.get('title', self.custom_class.title())
        # get the label content
        text = '\n'.join(self.content)
        # Create the panel element
        panel_element = nodes.container()
        panel_element['classes'] += ['panel', panel_name]
        # Create the panel headings
        heading_element = nodes.container(title_text)
        title_nodes, messages = self.state.inline_text(title_text,
                                                       self.lineno)
        title = nodes.paragraph(title_text, '', *title_nodes)
        heading_element.append(title)
        heading_element['classes'] += ['panel-heading']
        # Create a new container element (div)
        body_element = nodes.container(text)
        # Update its content
        self.state.nested_parse(self.content, self.content_offset,
                                body_element)
        # Set its custom bootstrap classes
        body_element['classes'] += ['panel-body']
        # add the heading and body to the panel
        panel_element.append(heading_element)
        panel_element.append(body_element)
        # Return the panel element
        return [panel_element]


class DefaultPanel(Panel):

    custom_class = 'default'


class PrimaryPanel(Panel):

    custom_class = 'primary'


class SuccessPanel(Panel):

    custom_class = 'success'


class InfoPanel(Panel):

    custom_class = 'info'


class WarningPanel(Panel):

    custom_class = 'warning'


class DangerPanel(Panel):

    custom_class = 'danger'


class Alert(rst.Directive):

    """
        generic Alert directive class definition.
        This class define a directive that shows 
        bootstrap Labels around its content

        *usage:*

            .. alert-<alert-type>::

                <alert content>

        *example:*

            .. alert-default::

                This is a default alert content

    """
    has_content = True
    custom_class = ''

    def run(self):
        # First argument is the name of the glyph
        alert_name = 'alert-{}'.format(self.custom_class)
        # get the label content
        text = '\n'.join(self.content)
        # Create a new container element (div)
        new_element = nodes.compound(text)
        # Update its content
        self.state.nested_parse(self.content, self.content_offset,
                                new_element)
        # Recurse inside its children and change the hyperlinks classes
        for child in new_element.traverse(include_self=False):
            if isinstance(child, nodes.reference):
                child.set_class('alert-link')
        # Set its custom bootstrap classes
        new_element['classes'] += ['alert ', alert_name]
        # Return one single element
        return [new_element]


class SuccessAlert(Alert):

    custom_class = 'success'


class InfoAlert(Alert):

    custom_class = 'info'


class WarningAlert(Alert):

    custom_class = 'warning'


class DangerAlert(Alert):

    custom_class = 'danger'


class Media(rst.Directive):

    '''
        generic Media directive class definition.
        This class define a directive that shows 
        bootstrap media image with text according
        to the media component on bootstrap

        *usage*:
            .. media:: <image_uri>
                :position: <position>
                :alt: <alt>
                :height: <height>
                :width: <width>
                :scale: <scale>
                :target: <target>

                <text content>

        *example*:
            .. media:: http://stuffkit.com/wp-content/uploads/2012/11/Worlds-Most-Beautiful-Lady-Camilla-Belle-HD-Photos-4.jpg
                :height: 750
                :width: 1000
                :scale: 20
                :target: www.google.com
                :alt: Camilla Belle
                :position: left

                This image is not mine. Credit goes to http://stuffkit.com



    '''

    has_content = True
    required_arguments = 1

    option_spec = {
        'position': str,
        'alt': rst.directives.unchanged,
        'height': rst.directives.length_or_unitless,
        'width': rst.directives.length_or_percentage_or_unitless,
        'scale': rst.directives.percentage,
        'target': rst.directives.unchanged_required,
    }

    def get_image_element(self):
        # Get the image url
        image_url = self.arguments[0]
        image_reference = rst.directives.uri(image_url)
        self.options['uri'] = image_reference

        reference_node = None
        messages = []
        if 'target' in self.options:
            block = rst.states.escape2null(
                self.options['target']).splitlines()
            block = [line for line in block]
            target_type, data = self.state.parse_target(
                block, self.block_text, self.lineno)
            if target_type == 'refuri':
                container_node = nodes.reference(refuri=data)
            elif target_type == 'refname':
                container_node = nodes.reference(
                    refname=fully_normalize_name(data),
                    name=whitespace_normalize_name(data))
                container_node.indirect_reference_name = data
                self.state.document.note_refname(container_node)
            else:                           # malformed target
                messages.append(data)       # data is a system message
            del self.options['target']
        else:
            container_node = nodes.container()

        # get image position
        position = self.options.get('position', 'left')
        position_class = 'pull-{}'.format(position)

        container_node.set_class(position_class)

        image_node = nodes.image(self.block_text, **self.options)
        image_node['classes'] += ['media-object']

        container_node.append(image_node)
        return container_node

    def run(self):
        # now we get the content
        text = '\n'.join(self.content)

        # get image alternative text
        alternative_text = self.options.get('alternative-text', '')

        # get container element
        container_element = nodes.container()
        container_element['classes'] += ['media']

        # get image element
        image_element = self.get_image_element()

        # get body element
        body_element = nodes.container(text)
        body_element['classes'] += ['media-body']
        self.state.nested_parse(self.content, self.content_offset,
                                body_element)

        container_element.append(image_element)
        container_element.append(body_element)
        return [container_element, ]


def register_directives():
    rst.directives.register_directive('label-default', DefaultLabel)
    rst.directives.register_directive('label-primary', PrimaryLabel)
    rst.directives.register_directive('label-success', SuccessLabel)
    rst.directives.register_directive('label-info', InfoLabel)
    rst.directives.register_directive('label-warning', WarningLabel)
    rst.directives.register_directive('label-danger', DangerLabel)

    rst.directives.register_directive('panel-default', DefaultPanel)
    rst.directives.register_directive('panel-primary', PrimaryPanel)
    rst.directives.register_directive('panel-success', SuccessPanel)
    rst.directives.register_directive('panel-info', InfoPanel)
    rst.directives.register_directive('panel-warning', WarningPanel)
    rst.directives.register_directive('panel-danger', DangerPanel)

    rst.directives.register_directive('alert-success', SuccessAlert)
    rst.directives.register_directive('alert-info', InfoAlert)
    rst.directives.register_directive('alert-warning', WarningAlert)
    rst.directives.register_directive('alert-danger', DangerAlert)

    rst.directives.register_directive( 'media', Media )


def register_roles():
    rst.roles.register_local_role('glyph', glyph_role)
    rst.roles.register_local_role('code', code_role)
    rst.roles.register_local_role('kbd', keyboard_role)


def add_reader(readers):
    readers.reader_classes['rst'] = CleanRSTReader


def register():
    register_directives()
    register_roles()
    signals.readers_init.connect(add_reader)

########NEW FILE########
__FILENAME__ = wc3_validate
# -*- coding: utf-8 -*-
"""
W3C HTML Validator plugin for genrated content.
"""


from pelican import signals
import logging
import os

LOG = logging.getLogger(__name__)

INCLUDE_TYPES = ['html']


def validate_files(pelican):
    """
    Validate a generated HTML file
    :param pelican: pelican object
    """
    for dirpath, _, filenames in os.walk(pelican.settings['OUTPUT_PATH']):
        for name in filenames:
            if should_validate(name):
                filepath = os.path.join(dirpath, name)
                validate(filepath)


def validate(filename):
    """
    Use W3C validator service: https://bitbucket.org/nmb10/py_w3c/ .
    :param filename: the filename to validate
    """
    import HTMLParser
    from py_w3c.validators.html.validator import HTMLValidator

    h = HTMLParser.HTMLParser()  # for unescaping WC3 messages

    vld = HTMLValidator()
    LOG.info("Validating: {0}".format(filename))

    # call w3c webservice
    vld.validate_file(filename)

    # display errors and warning
    for err in vld.errors:
        LOG.error(u'line: {0}; col: {1}; message: {2}'.
                  format(err['line'], err['col'], h.unescape(err['message']))
                  )
    for err in vld.warnings:
        LOG.warning(u'line: {0}; col: {1}; message: {2}'.
                    format(err['line'], err['col'], h.unescape(err['message']))
                    )


def should_validate(filename):
    """Check if the filename is a type of file that should be validated.
    :param filename: A file name to check against
    """
    for extension in INCLUDE_TYPES:
        if filename.endswith(extension):
            return True
    return False


def register():
    """
    Register Pelican signal for validating content after it is generated.
    """
    signals.finalized.connect(validate_files)

########NEW FILE########
