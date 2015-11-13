__FILENAME__ = helpers
# -*- coding: utf-8 -*-
from datetime import datetime
import errno
from fnmatch import fnmatch
import io
import os
import shutil
import unicodedata


def to_unicode(txt, encoding='utf8'):
    if not isinstance(txt, basestring):
        txt = str(txt)
    if isinstance(txt, unicode):
        return txt
    return unicode(txt, encoding)


def unormalize(text, form='NFD'):
    return unicodedata.normalize(form, text)


def fullmatch(path, pattern):
    path = unormalize(path)
    name = os.path.basename(path)
    return fnmatch(name, pattern) or fnmatch(path, pattern)


def make_dirs(*lpath):
    path = os.path.join(*lpath)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return path


def create_file(path, content, encoding='utf8'):
    if not isinstance(content, unicode):
        content = unicode(content, encoding)
    with io.open(path, 'w+t', encoding=encoding) as f:
        f.write(content)


def copy_if_updated(path_in, path_out):
    if os.path.exists(path_out):
        newt = os.path.getmtime(path_in)
        currt = os.path.getmtime(path_out)
        if currt >= newt:
            return
    shutil.copy2(path_in, path_out)


def get_updated_datetime(path):
    ut = os.path.getmtime(path)
    return datetime.fromtimestamp(ut)


def sort_paths_dirs_last(paths):
    def dirs_last(a, b):
        return cmp(a[0].count('/'), b[0].count('/')) or cmp(a[0], b[0])

    return sorted(paths, cmp=dirs_last)

########NEW FILE########
__FILENAME__ = jinja_includewith
# -*- coding: utf-8 -*-
import re
from jinja2.ext import Extension


class IncludeWith(Extension):
    """A Jinja2 preprocessor extension that let you update the `include`
    context like this:

        {% include "something.html" with foo=bar %}
        {% include "something.html" with a=3, b=2+2, c='yes' %}

    You **must** also include 'jinja2.ext.with_' in the extensions list.
    """

    rx = re.compile(r'\{\%-?[\s\n]*include[\s\n]+(?P<tmpl>[^\s\n]+)[\s\n]+with[\s\n]+'
                    '(?P<context>.*?)[\s\n]*-?\%\}', re.IGNORECASE)

    def preprocess(self, source, name, filename=None):
        lastpos = 0
        while 1:
            m = self.rx.search(source, lastpos)
            if not m:
                break

            lastpos = m.end()
            d = m.groupdict()
            context = d['context'].strip()
            if context == 'context':
                continue

            source = ''.join([
                source[:m.start()],
                '{% with ', context, ' %}',
                '{% include ', d['tmpl'].strip(), ' %}',
                '{% endwith %}',
                source[m.end():]
            ])

        return source

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
from __future__ import print_function

import imp
import mimetypes
import os
from os.path import (
    isfile, isdir, dirname, join, splitext, basename, exists, relpath, sep)
import re

from jinja2.exceptions import TemplateNotFound

from .helpers import (
    to_unicode, unormalize, fullmatch, make_dirs, create_file,
    copy_if_updated, get_updated_datetime, sort_paths_dirs_last)
from .server import Server, DEFAULT_HOST, DEFAULT_PORT
from .static import serve_file
from .wsgiapp import WSGIApplication
from functools import reduce


SOURCE_DIRNAME = 'source'
BUILD_DIRNAME = 'build'
THUMBS_URL = '/_thumbs:'
TMPL_EXTS = ('.html', '.tmpl', '.md')
RX_MD = re.compile(r'\.md$')
RX_TMPL = re.compile(r'\.tmpl$')

DEFAULT_INCLUDE = []
DEFAULT_FILTER = ['.*']

HTTP_NOT_FOUND = 404

SOURCE_NOT_FOUND = u"""We couldn't found a "%s" dir.
Check if you're in the correct folder""" % SOURCE_DIRNAME

rx_abs_url = re.compile(
    r'\s(src|href|data-[a-z0-9_-]+)\s*=\s*[\'"](\/(?:[a-z0-9_-][^\'"]*)?)[\'"]',
    re.UNICODE | re.IGNORECASE)


class Clay(object):

    _cached_pages_list = None

    def __init__(self, root, settings=None):
        if isfile(root):
            root = dirname(root)
        settings = settings or {}
        self.settings = settings
        self.settings_path = join(root, 'settings.py')
        self.load_settings_from_file()
        self.source_dir = to_unicode(join(root, SOURCE_DIRNAME))
        self.build_dir = to_unicode(join(root, BUILD_DIRNAME))
        self.app = self.make_app()
        self.server = Server(self)

    def make_app(self):
        app = WSGIApplication(self.source_dir, self.build_dir, THUMBS_URL)
        self.set_urls(app)
        return app

    def set_urls(self, app):
        app.add_url_rule('/', 'page', self.render_page)
        app.add_url_rule('/<path:path>', 'page', self.render_page)
        app.add_url_rule('/_index.html', 'index', self.show__index)
        app.add_url_rule('/_index.txt', 'index_txt', self.show__index_txt)
        app.add_url_rule(THUMBS_URL + '/<path:path>', 'thumb', self.show_thumb)

    def load_settings_from_file(self):
        if isfile(self.settings_path):
            settings = imp.load_source('settings', self.settings_path)
            self.settings.update(settings.__dict__)

    def render(self, path, context):
        host = self.settings.get('HOST', DEFAULT_HOST)
        port = self.settings.get('PORT', DEFAULT_PORT)
        return self.app.render_template(path, context, host, port)

    def get_full_source_path(self, path):
        return join(self.source_dir, path)

    def get_full_build_path(self, path):
        return join(self.build_dir, path)

    def get_real_fn(self, path):
        if path.endswith('.md'):
            return RX_MD.sub('.html', path)
        filename = basename(path)
        fn, ext = splitext(filename)
        fn2, ext2 = splitext(fn)
        if ext2:
            return fn
        return filename

    def guess_mimetype(self, fn):
        return mimetypes.guess_type(fn)[0] or 'text/plain'

    def normalize_path(self, path):
        path = path or 'index.html'
        if isdir(self.get_full_source_path(path)):
            path = '/'.join([path, 'index.html'])
        return path

    def get_relpath(self, fullpath):
        rel = relpath(fullpath, self.source_dir)
        return rel.lstrip('.').lstrip(sep)

    def remove_template_ext(self, path):
        path = RX_MD.sub('.html', path)
        return RX_TMPL.sub('', path)

    def get_relative_url(self, relpath, currurl):
        depth = relpath.count('/')
        url = (r'../' * depth) + currurl.lstrip('/')
        if not url:
            return 'index.html'
        path = self.get_full_source_path(url)
        if isdir(path) or url.endswith('/'):
            return url.rstrip('/') + '/index.html'
        return url

    def make_absolute_urls_relative(self, content, relpath):
        for attr, url in rx_abs_url.findall(content):
            newurl = self.get_relative_url(relpath, url)
            repl = r' %s="%s"' % (attr, newurl)
            content = re.sub(rx_abs_url, repl, content, count=1)
        return content

    def is_html_fragment(self, content):
        head = content[:500].strip().lower()
        return not (head.startswith('<!doctype ') or head.startswith('<html'))

    def must_be_included(self, path):
        patterns = (self.settings.get('INCLUDE', DEFAULT_INCLUDE)
                    or DEFAULT_INCLUDE)
        patterns = [unormalize(to_unicode(p)) for p in patterns]
        return reduce(lambda r, pattern: r or
                      fullmatch(path, pattern), patterns, False)

    def must_be_filtered(self, path):
        patterns = (self.settings.get('FILTER', DEFAULT_FILTER)
                    or DEFAULT_FILTER)
        patterns = [unormalize(to_unicode(p)) for p in patterns]
        return reduce(lambda r, pattern: r or
                      fullmatch(path, pattern), patterns, False)

    def must_filter_fragment(self, content):
        return (bool(self.settings.get('FILTER_PARTIALS', True))
                and self.is_html_fragment(content))

    def get_pages_list(self, pattern=None):
        if self._cached_pages_list:
            return self._cached_pages_list
        if pattern:
            pattern = unormalize(to_unicode(pattern))
        pages = []
        for folder, subs, files in os.walk(self.source_dir):
            rel = self.get_relpath(folder)
            for filename in files:
                path = join(rel, filename)
                if not pattern or fullmatch(path, pattern):
                    pages.append(path)
        self._cached_pages_list = pages
        return pages

    def get_pages_index(self):
        index = []
        pages = self.get_pages_list()
        for path in pages:
            if not path.endswith(TMPL_EXTS):
                continue

            if not self.must_be_included(path):
                if self.must_be_filtered(path):
                    continue
                content = self.render(path, self.settings)
                if self.must_filter_fragment(content):
                    continue

            fullpath = self.get_full_source_path(path)
            updated_at = get_updated_datetime(fullpath)
            index.append((path, updated_at))
        return sort_paths_dirs_last(index)

    def serve_file(self, fullpath):
        try:
            body, headers, status_code = serve_file(fullpath)
            rsp = self.app.response_class(
                body,
                headers=headers,
                mimetype=headers.get('Content-Type', 'text/plain'),
                direct_passthrough=True
            )
            rsp.status_code = status_code
            return rsp
        except (IOError, OSError):
            path = self.get_relpath(fullpath)
            return self.show_notfound(path)

    def render_page(self, path=None):
        path = self.normalize_path(path)

        if not path.endswith(TMPL_EXTS):
            fullpath = self.get_full_source_path(path)
            return self.serve_file(fullpath)

        try:
            content = None
            fn, ext = splitext(path)
            if ext == '.html':
                mdpath = join(self.source_dir, fn + '.md')
                if isfile(mdpath):
                    content = self.render(mdpath, self.settings)

            if content is None:
                content = self.render(path, self.settings)

        except TemplateNotFound as e:
            return self.show_notfound(e)

        mimetype = self.guess_mimetype(self.get_real_fn(path))
        return self.app.response(content, mimetype=mimetype)

    def _make__index(self, path):
        index = self.get_pages_index()
        context = self.settings.copy()
        context['index'] = index
        return self.render(path, context)

    def show__index_txt(self):
        path = '_index.txt'
        content = self._make__index(path)
        return self.app.response(content, mimetype='text/plain')

    def show_thumb(self, path):
        fullpath = self.app.get_thumb_fullpath(path)
        return self.serve_file(fullpath)

    def build__index_txt(self):
        path = '_index.txt'
        self.print_build_message(path)
        content = self._make__index(path)
        bp = self.get_full_build_path(path)
        create_file(bp, content)

    def show__index(self):
        path = '_index.html'
        content = self._make__index(path)
        return self.app.response(content, mimetype='text/html')

    def build__index(self):
        path = '_index.html'
        self.print_build_message(path)
        content = self._make__index(path)
        bp = self.get_full_build_path(path)
        create_file(bp, content)

    def print_build_message(self, path):
        print(' ', to_unicode(self.remove_template_ext(path)))

    def build_page(self, path):
        path = to_unicode(path)
        sp = self.get_full_source_path(path)
        bp = self.get_full_build_path(path)
        make_dirs(dirname(bp))
        if not path.endswith(TMPL_EXTS):
            if self.must_be_filtered(path):
                return
            self.print_build_message(path)
            return copy_if_updated(sp, bp)

        must_be_included = self.must_be_included(path)
        if self.must_be_filtered(path) and not must_be_included:
            return

        self.settings['BUILD'] = True
        content = self.render(path, self.settings)
        if self.must_filter_fragment(content) and not must_be_included:
            return

        self.print_build_message(path)
        bp = self.remove_template_ext(bp)
        if bp.endswith('.html'):
            content = self.make_absolute_urls_relative(content, path)
        create_file(bp, content)

    def run(self, host=None, port=None):
        if not exists(self.source_dir):
            print(SOURCE_NOT_FOUND)
            return None, None
        return self.server.run(host, port)

    def build(self, pattern=None):
        self._cached_pages_list = None
        pages = self.get_pages_list(pattern)
        print('Building...\n')
        for path in pages:
            self.build_page(path)
        self.build__index()
        self.build__index_txt()
        print('\nDone.')

    def show_notfound(self, path):
        context = self.settings.copy()
        context['path'] = path
        res = self.render('_notfound.html', context)
        return self.app.response(res, status=HTTP_NOT_FOUND, mimetype='text/html')

    def get_test_client(self):
        host = self.settings.get('HOST', DEFAULT_HOST)
        port = self.settings.get('PORT', DEFAULT_PORT)
        return self.app.get_test_client(host, port)

########NEW FILE########
__FILENAME__ = manage
# -*- coding: utf-8 -*-
from __future__ import print_function

from os.path import sep, abspath

import baker
from voodoo import render_skeleton

from .main import Clay, DEFAULT_HOST, DEFAULT_PORT


DEFAULT_TEMPLATE_URL = 'git@github.com:lucuma/clay-template.git'

HELP_MSG = """
    Done!
    Now go to %s, and do `clay run` to start the server.
"""


manager = baker.Baker()


@manager.command
def new(path='.', template=None):
    """Creates a new project
    """
    path = abspath(path.rstrip(sep))
    template = template or DEFAULT_TEMPLATE_URL
    render_skeleton(template, path, include_this=['.gitignore'])
    print(HELP_MSG % (path,))


@manager.command
def run(host=DEFAULT_HOST, port=DEFAULT_PORT, path='.'):
    """Run the development server
    """
    path = abspath(path)
    c = Clay(path)
    c.run(host=host, port=port)


# @manager.command
# def debug(host=DEFAULT_HOST, port=DEFAULT_PORT, path='.'):
#     """Like 'Run' but starting pudb on error
#     """
#     import sys
#     def on_error(type, value, tb):
#         import pudb
#         if sys.stderr.isatty() or sys.stdin.isatty():
#             return
#         pudb.pm()

#     sys.excepthook = on_error
#     run(host, port, path)


@manager.command
def build(pattern=None, path='.'):
    """Generates a static copy of the sources
    """
    path = abspath(path)
    c = Clay(path)
    c.build(pattern)


@manager.command
def version():
    """Returns the current Clay version
    """
    from clay import __version__
    print(__version__)


def main():
    manager.run()

########NEW FILE########
__FILENAME__ = jinja
# -*- coding: utf-8 -*-
import os

import jinja2
import jinja2.ext

from .render import md_to_jinja


MARKDOWN_EXTENSION = '.md'


class MarkdownExtension(jinja2.ext.Extension):

    def preprocess(self, source, name, filename=None):
        if name is None or os.path.splitext(name)[1] != MARKDOWN_EXTENSION:
            return source
        return md_to_jinja(source)

    def _from_string(self, source, globals=None, template_class=None):
        env = self.environment
        globals = env.make_globals(globals)
        cls = template_class or env.template_class
        template_name = 'markdown_from_string.md'
        return cls.from_code(env, env.compile(source, template_name), globals, None)

########NEW FILE########
__FILENAME__ = md_admonition
# -*- coding: utf-8 -*-
"""
Admonition extension for Python-Markdown
=========================================

The syntax is as following:

    !!! [optional css classes]
        content here

A simple example:

    !!! note big
        This is the first line inside the box.

Outputs:

    <div class="admonition note big">
    <p>This is the first line inside the box.</p>
    </div>

"""
from markdown import Extension
from markdown.blockprocessors import BlockProcessor
from markdown.util import etree

import re


CLASSNAME = 'admonition'
RX = re.compile(r'(?:^|\n)!!!\ ?([^\n]+)')


class AdmonitionProcessor(BlockProcessor):

    def test(self, parent, block):
        sibling = self.lastChild(parent)
        return RX.search(block) or \
            (block.startswith(' ' * self.tab_length) and sibling and \
                sibling.get('class', '').find(CLASSNAME) != -1)

    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        m = RX.search(block)
        if m:
            block = block[m.end() + 1:]  # removes the first line
        block, theRest = self.detab(block)
        if m:
            klass = m.group(1)
            div = etree.SubElement(parent, 'div')
            div.set('class', '%s %s' % (CLASSNAME, klass))
        else:
            div = sibling
        self.parser.parseChunk(div, block)

        if theRest:
            # This block contained unindented line(s) after the first indented
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)


class AdmonitionExtension(Extension):
    """ Admonition extension for Python-Markdown.
    """

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.parser.blockprocessors.add(
            'admonition',
            AdmonitionProcessor(md.parser),
            '_begin'
        )

########NEW FILE########
__FILENAME__ = md_delinsmark
# -*- coding: utf-8 -*-
"""
Del/Ins/Mark Extension for Markdown
====================================

Wraps the inline content with ins/del tags.

Example:

>>> import markdown
>>> md = markdown.Markdown(extensions=[DelInsMarkExtension()])

>>> md.convert('This is ++added content++, this is ~~deleted content~~ and this is ==marked==.')
u'<p>This is <ins>added content</ins>, this is <del>deleted content</del> and this is <mark>marked</mark>.</p>'

"""
import markdown
from markdown.inlinepatterns import SimpleTagPattern


DEL_RE = r"(\~\~)(.+?)(\~\~)"
INS_RE = r"(\+\+)(.+?)(\+\+)"
MARK_RE = r"(\=\=)(.+?)(\=\=)"


class DelInsMarkExtension(markdown.extensions.Extension):
    """Adds del_ins extension to Markdown class.
    """

    def extendMarkdown(self, md, md_globals):
        """Modifies inline patterns."""
        md.inlinePatterns.add('del', SimpleTagPattern(DEL_RE, 'del'), '<not_strong')
        md.inlinePatterns.add('ins', SimpleTagPattern(INS_RE, 'ins'), '<not_strong')
        md.inlinePatterns.add('mark', SimpleTagPattern(MARK_RE, 'mark'), '<not_strong')


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = md_fencedcode
# -*- coding: utf-8 -*-
"""
Fenced Code Extension for Markdown
===================================

    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ...
    ... ```
    ... Fenced code block
    ... ```
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> print html
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Language tags:

    >>> text = '''
    ... ```python
    ... # Some python code
    ... ```'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code class="language-python"># Some python code
    </code></pre>

Optionally tildes instead of  backticks:

    >>> text = '''
    ... ~~~
    ... # Arbitrary code
    ... ``` # these backticks will not close the block
    ... ~~~
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code># Arbitrary code
    ``` # these backticks will not close the block
    </code></pre>


Adapted under the BSD License from the `fenced_code` and `codehilite`
extensions (Copyright 2007-2008 Waylan Limberg http://achinghead.com/).

"""
import re

from markdown import Extension
from markdown.preprocessors import Preprocessor
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter


FENCED_BLOCK_RE = re.compile(
    (r'(?P<fence>^(?:~{3,}|`{3,}))[ ]*'
     r'(?P<lang>[a-z0-9_+-]*)(?P<linenums>#)?[ ]*\n'
     r'(?P<code>.*?)'
     r'(?<=\n)(?P=fence)[ ]*$'
    ), re.MULTILINE|re.DOTALL|re.IGNORECASE
)
OPEN_CODE = u'<pre><code%s>{%% raw %%}'
LANG_TAG = u' class="language-%s"'
CLOSE_CODE = '{% endraw %}</code></pre>'
TAB_LENGTH = 4


def highlight_syntax(src, lang, linenums=False):
    """Pass code to the [Pygments](http://pygments.pocoo.org/) highliter
    with optional line numbers. The output should then be styled with CSS
    to  your liking. No styles are applied by default - only styling hooks
    (i.e.: <span class="k">).
    """
    src = src.strip('\n')
    if not lang:
        lexer = TextLexer()
    else:
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except ValueError:
            lexer = TextLexer()
    formatter = HtmlFormatter(linenos=linenums, tab_length=TAB_LENGTH)
    html = highlight(src, lexer, formatter)

    if lang:
        open_code = OPEN_CODE % (LANG_TAG % (lang, ), )
    else:
        open_code = OPEN_CODE % u''
    html = html.replace('<div class="highlight"><pre>', open_code, 1)
    html = html.replace('</pre></div>', CLOSE_CODE)
    return html


class FencedBlockPreprocessor(Preprocessor):

    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash.
        """
        text = "\n".join(lines)
        while 1:
            m = FENCED_BLOCK_RE.search(text)
            if not m:
                break
            lang = m.group('lang')
            linenums = bool(m.group('linenums'))
            html = highlight_syntax(m.group('code'), lang, linenums=linenums)
            placeholder = self.markdown.htmlStash.store(html, safe=True)
            text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])

        return text.split("\n")


class FencedCodeExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.preprocessors.add(
            'fenced_code_block',
            FencedBlockPreprocessor(md),
            ">normalize_whitespace"
        )

########NEW FILE########
__FILENAME__ = md_superscript
# -*- coding: utf-8 -*-
"""
Superscipt extension for Markdown
==================================

Examples:

>>> import markdown
>>> md = markdown.Markdown(extensions=[SuperscriptExtension()])

>>> md.convert('lorem ipsum^1 sit.')
u'<p>lorem ipsum<sup>1</sup> sit.</p>'

>>> md.convert('6.02 x 10^23')
u'<p>6.02 x 10<sup>23</sup></p>'

>>> md.convert('10^(2x + 3).')
u'<p>10<sup>2x + 3</sup>.</p>'

"""
import markdown
from markdown.inlinepatterns import Pattern
from markdown.util import etree, AtomicString


SUPER_RE = r'\^(?:([^\(\s]+)|\(([^\n\)]+)\))'


class SuperscriptPattern(Pattern):
    """ Return a superscript Element (`word^2^`). """
    def handleMatch(self, m):
        supr = m.group(2) or m.group(3)
        text = supr
        el = etree.Element("sup")
        el.text = AtomicString(text)
        return el


class SuperscriptExtension(markdown.Extension):
    """ Superscript Extension for Python-Markdown.
    """

    def extendMarkdown(self, md, md_globals):
        """ Replace superscript with SuperscriptPattern """
        md.inlinePatterns['superscript'] = SuperscriptPattern(SUPER_RE, md)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = render
# -*- coding: utf-8 -*-
import markdown as m
import re

from .md_admonition import AdmonitionExtension
from .md_delinsmark import DelInsMarkExtension
from .md_fencedcode import FencedCodeExtension
from .md_superscript import SuperscriptExtension


TMPL_LAYOUT = u'{%% extends "%s" %%}'
TMPL_BLOCK = u'{%% block %s %%}%s{%% endblock %%}'


md = m.Markdown(
    extensions=['meta',
        AdmonitionExtension(), FencedCodeExtension(),
        DelInsMarkExtension(), SuperscriptExtension(),
        'abbr', 'attr_list', 'def_list', 'footnotes', 'smart_strong',
        'tables', 'headerid', 'nl2br', 'sane_lists',
    ],
    output_format='html5',
    smart_emphasis=True,
    lazy_ol=True
)


# match all the urls
# this returns a tuple with two groups
# if the url is part of an existing link, the second element
# in the tuple will be "> or </a>
# if not, the second element will be an empty string
URL_RE = re.compile(
    r'\(?' +
    '(%s)' % '|'.join([
        r'\b[a-zA-Z]{3,7}://[^)<>\s]+[^.,)<>\s]',
        r'\b(?:www|WWW)\.[^)<>\s]+[^.,)<>\s]',
    ])
    + r'(">|</a>)?'
)

def autolink(html):
    urls = URL_RE.findall(html)
    for m_url in urls:
        # ignore urls that are part of a link already
        if m_url[1]:
            continue
        url = m_url[0]
        text = url

        # ignore parens if they enclose the entire url
        if url[0] == '(' and url[-1] == ')':
            url = url[1:-1]

        protocol = url.split('://')[0]
        if not protocol or protocol == url:
            url = 'http://' + url

        # substitute only where the url is not already part of a
        # link element.
        html = re.sub('(?<!(="|">))' + re.escape(text),
                      '<a href="' + url + '">' + text + '</a>',
                      html)
    return html


BLOCK_OPEN_RE = re.compile(r'({[{%])(%20)+')
BLOCK_CLOSE_RE = re.compile(r'(%20)+([%}]})')


def md_to_jinja(source):
    md.reset()
    tmpl = []
    html = md.convert(source)
    html = re.sub(BLOCK_OPEN_RE, '\g<1> ', html)
    html = re.sub(BLOCK_CLOSE_RE, ' \g<2>', html)
    html = autolink(html)
    layout = md.Meta.pop('layout', None)
    if layout:
        tmpl.append(TMPL_LAYOUT % (layout[0], ))

    for name, value in md.Meta.items():
        tmpl.append(TMPL_BLOCK % (name, value[0]))

    tmpl.append(TMPL_BLOCK % (u'content', html))
    return '\n'.join(tmpl)

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
from __future__ import print_function

from datetime import datetime
import socket
import sys

import cherrypy
from cherrypy import wsgiserver


ALL_HOSTS = '0.0.0.0'
DEFAULT_HOST = ALL_HOSTS
DEFAULT_PORT = 8080
MAX_PORT_DELTA = 10

WELCOME = u' # Clay (by Lucuma labs)\n'
ADDRINUSE = u' ---- Address already in use. Trying another port...'
RUNNING_ON = u' * Running on http://%s:%s'
HOW_TO_QUIT = u' -- Quit the server with Ctrl+C --\n'

HTTPMSG = '500 Internal Error'


class Server(object):

    def __init__(self, clay):
        self.clay = clay
        app = RequestLogger(clay.app)
        self.dispatcher = wsgiserver.WSGIPathInfoDispatcher({'/': app})

    def run(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        port = port or self.clay.settings.get('port', DEFAULT_PORT)
        host = host or self.clay.settings.get('host', DEFAULT_HOST)
        max_port = port + MAX_PORT_DELTA
        print(WELCOME)
        return self._testrun(host, port, max_port)

    def _testrun(self, host, current_port, max_port):
        self.print_help_msg(host, current_port)
        try:
            self._run_wsgi_server(host, current_port)
        except socket.error:
            current_port += 1
            if current_port > max_port:
                return
            print(ADDRINUSE)
            self._testrun(host, current_port, max_port)
        except KeyboardInterrupt:
            self.stop()
        return host, current_port

    def _run_wsgi_server(self, host, port):
        self.server = self._get_wsgi_server(host, port)
        self.start()

    def _get_wsgi_server(self, host, port):
        return wsgiserver.CherryPyWSGIServer(
            (host, port),
            wsgi_app=self.dispatcher
        )

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()

    def print_help_msg(self, host, port):
        if host == ALL_HOSTS:
            print(RUNNING_ON % ('localhost', port))
            local_ip = get_local_ip()
            if local_ip:
                print(RUNNING_ON % (local_ip, port))
        print(HOW_TO_QUIT)



class RequestLogger(object):

    def __init__(self, application, **kw):
        self.application = application

    def log_request(self, environ, now=None):
        now = now or datetime.now()
        msg = [
            ' ',
            now.strftime('%H:%M:%S'), ' | ',
            environ.get('REMOTE_ADDR', '?'), '  ',
            environ.get('REQUEST_URI', ''), '  ',
            '(', environ.get('REQUEST_METHOD', ''), ')',
        ]
        msg = ''.join(msg)
        print(msg)

    def __call__(self, environ, start_response):
        self.log_request(environ)
        try:
            return self.application(environ, start_response)
        except Exception:
            start_response(HTTPMSG, [('Content-type', 'text/plain')], sys.exc_info())
            raise


def get_local_ip():
    try:
        interfaces = socket.gethostbyname_ex(socket.gethostname())[-1]
    except socket.gaierror:
        return
    for ip in interfaces:
        if ip.startswith('192.'):
            return ip

########NEW FILE########
__FILENAME__ = static
# -*- coding: utf-8 -*-
from __future__ import print_function
import mimetypes
mimetypes.init()

NEW_MIMETYPES = {
    '.dwg': 'image/x-dwg',
    '.ico': 'image/x-icon',
    '.bz2': 'application/x-bzip2',
    '.gz': 'application/x-gzip',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xltx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
    '.potx': 'application/vnd.openxmlformats-officedocument.presentationml.template',
    '.ppsx': 'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.sldx': 'application/vnd.openxmlformats-officedocument.presentationml.slide',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.dotx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
    '.xlam': 'application/vnd.ms-excel.addin.macroEnabled.12',
    '.xlsb': 'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
}
for name, value in NEW_MIMETYPES.items():
    mimetypes.types_map[name] = value

import os
from zlib import adler32

from cherrypy.lib import httputil, file_generator_limited
from werkzeug.http import quote_etag
from werkzeug.exceptions import RequestedRangeNotSatisfiable

from .helpers import to_unicode


def serve_file(path):
    headers = {}

    st = os.stat(path)

    etag = 'clay-{0}-{1}-{2}'.format(
        os.path.getmtime(path),
        os.path.getsize(path),
        adler32(path.encode('utf-8')) & 0xffffffff
    )
    headers['ETag'] = quote_etag(etag)

    # Set the Last-Modified response header, so that
    # modified-since validation code can work.
    headers['Last-Modified'] = httputil.HTTPDate(st.st_mtime)

    _, ext = os.path.splitext(path)
    content_type = mimetypes.types_map.get(ext, None)
    headers['Content-Type'] = content_type or 'text/plain'

    fileobj = open(path, 'rb')
    return serve_fileobj(fileobj, headers, st.st_size)


def serve_fileobj(fileobj, headers, content_length):
    status_code = 200
    headers["Accept-Ranges"] = "bytes"

    r = httputil.get_ranges(headers.get('Range'), content_length)

    if r == []:
        headers['Content-Range'] = "bytes */{0}".format(content_length)
        message = "Invalid Range (first-byte-pos greater than Content-Length)"
        raise RequestedRangeNotSatisfiable(message)

    if not r:
        headers['Content-Length'] = content_length
        return fileobj, headers, status_code

    # Return a multipart/byteranges response.
    status_code = 206

    if len(r) == 1:
        # Return a single-part response.
        start, stop = r[0]
        if stop > content_length:
            stop = content_length
        r_len = stop - start

        headers['Content-Range'] = "bytes {0}-{1}/{2}".format(
            start, stop - 1, content_length
        )
        headers['Content-Length'] = r_len
        fileobj.seek(start)
        body = file_generator_limited(fileobj, r_len)
        return body, headers, status_code

    try:
        # Python 3
        from email.generator import _make_boundary as make_boundary
    except ImportError:
        # Python 2
        from mimetools import choose_boundary as make_boundary

    boundary = make_boundary()
    content_type = "multipart/byteranges; boundary={0}".format(boundary)
    headers['Content-Type'] = content_type
    if "Content-Length" in headers:
        del headers["Content-Length"]

    def file_ranges():
        for start, stop in r:
            yield to_unicode("--" + boundary)
            yield to_unicode("\r\nContent-type: {0}".format(content_type))
            yield to_unicode(
                "\r\nContent-range: bytes {0}-{1}/{2}\r\n\r\n".format(
                    start, stop - 1, content_length
                )
            )
            fileobj.seek(start)

            gen = file_generator_limited(fileobj, stop - start)
            for chunk in gen:
                yield chunk
            yield to_unicode("\r\n")

        yield to_unicode("--" + boundary + "--")

    body = file_ranges()
    return body, headers, status_code

########NEW FILE########
__FILENAME__ = tglobals
# -*- coding: utf-8 -*-
from fnmatch import fnmatch
from os.path import dirname
import re

from flask import request


def norm_url(url):
    url = url.strip().rstrip('/')
    url = re.sub('index.html$', '', url).rstrip('/')
    if url.startswith('/'):
        return url
    baseurl = dirname(request.path.strip('/'))
    if baseurl:
        return '/' + '/'.join([baseurl, url])
    return '/' + url


def active(*url_patterns, **kwargs):
    partial = kwargs.get('partial')

    path = norm_url(request.path)

    # Accept single patterns also
    if len(url_patterns) == 1 and isinstance(url_patterns[0], (list, tuple)):
        url_patterns = url_patterns[0]

    for urlp in url_patterns:
        urlp = norm_url(urlp)
        if fnmatch(path, urlp) or (partial and path.startswith(urlp)):
            return 'active'
    return u''

########NEW FILE########
__FILENAME__ = wsgiapp
# -*- coding: utf-8 -*-
from datetime import datetime
from os.path import basename, join
import tempfile

from flask import (Flask, request, has_request_context, render_template,
                   make_response)
from jinja2 import ChoiceLoader, FileSystemLoader, PackageLoader
from moar import FileStorage, Thumbnailer

from .jinja_includewith import IncludeWith
from .markdown_ext import MarkdownExtension
from .tglobals import active


APP_NAME = 'clay'

TEMPLATE_GLOBALS = {
    'CLAY_URL': 'http://lucuma.github.com/Clay',
    'active': active,
    'now': datetime.utcnow(),
    'dir': dir,
    'enumerate': enumerate,
    'map': map,
    'zip': zip,
}


class WSGIApplication(Flask):

    def __init__(self, source_dir, build_dir, thumbs_url):
        super(WSGIApplication, self).__init__(
            APP_NAME, template_folder=source_dir, static_folder=None)
        self.jinja_loader = get_jinja_loader(source_dir)
        self.jinja_options = get_jinja_options()

        tempdir = tempfile.gettempdir()
        self.tempdir = tempdir
        storage = FileStorage(tempdir, base_url=thumbs_url)
        self.thumbnailer = Thumbnailer(source_dir, storage=storage)
        TEMPLATE_GLOBALS['thumbnail'] = self.thumbnailer
        self.build_dir = build_dir

        self.context_processor(lambda: TEMPLATE_GLOBALS)
        self.debug = True

    def get_test_client(self, host, port):
        self.testing = True
        self.config['SERVER_NAME'] = '%s:%s' % (host, port)
        return self.test_client()

    def render_template(self, path, context, host, port):
        if has_request_context():
            context.update(request.values.to_dict())
            return render_template(path, **context)

        self.thumbnailer.echo = not path.startswith('_index')
        self.thumbnailer.storage.base_url = '/'
        self.thumbnailer.storage.out_path = self.build_dir
        with self.test_request_context(
                '/' + path, method='GET',
                base_url='http://%s:%s' % (host, port)):
            return render_template(path, **context)

    def get_thumb_fullpath(self, thumbpath):
        return join(self.thumbnailer.storage.out_path, thumbpath)

    def response(self, content, status=200, mimetype='text/plain'):
        resp = make_response(content, status)
        resp.mimetype = mimetype
        return resp


def get_jinja_loader(source_dir):
    return ChoiceLoader([
        FileSystemLoader(source_dir),
        PackageLoader('clay', basename(source_dir)),
    ])


def get_jinja_options():
    return {
        'autoescape': True,
        'extensions': [MarkdownExtension, 'jinja2.ext.with_', IncludeWith],
    }

########NEW FILE########
__FILENAME__ = conftest
# -*- coding: utf-8 -*-
"""
Directory-specific fixtures, hooks, etc. for py.test
"""
from clay import Clay
import pytest

from .helpers import TESTS


@pytest.fixture()
def c():
    return Clay(TESTS, {'foo': 'bar'})


@pytest.fixture()
def t(c):
    return c.get_test_client()

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
import io
import os
from os.path import dirname, join, isdir, exists
import shutil
from StringIO import StringIO
import sys
from tempfile import mkdtemp

from clay.helpers import make_dirs, create_file


HTML = u'<!DOCTYPE html><html><head><title></title></head><body></body></html>'
HTTP_OK = 200
HTTP_NOT_FOUND = 404
TESTS = mkdtemp()
SOURCE_DIR = join(TESTS, 'source')
BUILD_DIR = join(TESTS, 'build')


def get_source_path(path):
    return join(SOURCE_DIR, path)


def get_build_path(path):
    return join(BUILD_DIR, path)


def create_page(name, content, encoding='utf8'):
    sp = get_source_path(name)
    make_dirs(dirname(sp))
    content = content.encode(encoding)
    create_file(sp, content, encoding=encoding)


def read_content(path, encoding='utf8'):
    with io.open(path, 'r', encoding=encoding) as f:
        return f.read().encode(encoding)


def remove_file(path):
    if exists(path):
        os.remove(path)


def remove_dir(path):
    if isdir(path):
        shutil.rmtree(path, ignore_errors=True)


def execute_and_read_stdout(f):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    f()
    sys.stdout = old_stdout
    mystdout.seek(0)
    return mystdout.read()


def setup_function(f=None):
    make_dirs(SOURCE_DIR)
    make_dirs(BUILD_DIR)


def teardown_function(f=None):
    remove_dir(SOURCE_DIR)
    remove_dir(BUILD_DIR)
    remove_file(join(TESTS, 'settings.yml'))

########NEW FILE########
__FILENAME__ = test_build
# -*- coding: utf-8 -*-
import os

from clay import Clay

from .helpers import *


def get_file_paths(name):
    sp = get_source_path(name)
    bp = get_build_path(name)
    return sp, bp


def create_test_file(name):
    sp, bp = get_file_paths(name)
    create_file(sp, 'source')
    create_file(bp, 'build')
    return sp, bp


def test_build_dir_is_made(c):
    name = 'test.html'
    sp, bp = get_file_paths(name)
    create_file(sp, u'')
    remove_dir(BUILD_DIR)
    c.build_page(name)
    assert isdir(BUILD_DIR)


def test_build_page(c):
    c.settings['FILTER_PARTIALS'] = False

    name = 'foo.html'
    sp1, bp1 = get_file_paths(name)
    sp2, bp2 = get_file_paths('bar.html')

    create_file(sp1, u'foo{% include "bar.html" %}')
    create_file(sp2, u'bar')
    c.build_page(name)
    result = read_content(bp1)
    assert result.strip() == 'foobar'


def test_build_file_without_process(c):
    name = 'main.css'
    sp, bp = get_file_paths(name)
    content = "/* {% foobar %} */"
    create_file(sp, content)
    c.build_page(name)
    result = read_content(bp)
    assert result.strip() == content.strip()


def test_do_not_copy_if_build_is_newer(c):
    name = 'test.txt'
    sp, bp = create_test_file(name)
    t = os.path.getmtime(sp)
    os.utime(bp, (-1, t + 1))
    c.build_page(name)
    assert read_content(bp) == 'build'


def test_copy_if_source_is_newer(c):
    name = 'test.txt'
    sp, bp = create_test_file(name)
    t = os.path.getmtime(bp)
    os.utime(sp, (-1, t + 1))
    c.build_page(name)
    assert read_content(bp) == 'source'


def test_rename_tmpl_file(c):
    c.settings['FILTER_PARTIALS'] = False

    name = 'test.txt.tmpl'
    sp, bp = get_file_paths(name)
    create_file(sp, u'lalala')
    bpreal = get_build_path('test.txt')

    c.build_page(name)
    assert os.path.exists(bpreal)
    assert not os.path.exists(bp)


def test_settings_as_template_build_context():
    c = Clay(TESTS, {'who': u'world', 'FILTER_PARTIALS': False})
    name = 'test.txt.tmpl'
    sp = get_source_path(name)
    bp = get_build_path('test.txt')
    create_file(sp, u'Hello {{ who }}!')

    c.build_page(name)
    assert read_content(bp) == u'Hello world!'


def test_build_all(c):
    c.settings['FILTER_PARTIALS'] = False
    make_dirs(SOURCE_DIR, 'sub')

    sp1, bp1 = get_file_paths('a.txt')
    sp2 = get_source_path('b.txt.tmpl')
    bp2 = get_build_path('b.txt')
    sp3, bp3 = get_file_paths('sub/c.txt')

    create_file(sp1, u'foo')
    create_file(sp2, u'bar')
    create_file(sp3, u'mwahaha')

    c.build()
    assert os.path.exists(bp1)
    assert os.path.exists(bp2)
    assert os.path.exists(bp3)


def test_build_pattern(c):
    c.settings['FILTER_PARTIALS'] = False
    make_dirs(SOURCE_DIR, 'sub')

    sp1, bp1 = get_file_paths(u'a.txt')
    sp2 = get_source_path(u'ñ.txt.tmpl')
    bp2 = get_build_path(u'ñ.txt')
    sp3, bp3 = get_file_paths(u'sub/c.txt')
    sp4, bp4 = get_file_paths(u'ñ.html')

    create_file(sp1, u'foo')
    create_file(sp2, u'bar')
    create_file(sp3, u'mwahaha')
    create_file(sp4, HTML)

    c.build(u'ñ.*')
    assert not os.path.exists(bp1)
    assert os.path.exists(bp2)
    assert not os.path.exists(bp3)
    assert os.path.exists(bp4)
    assert read_content(bp4) == HTML


def test_translate_absolute_to_relative(c):
    make_dirs(SOURCE_DIR, 'foo')

    sp1, bp1 = get_file_paths('wtf.html')
    sp2, bp2 = get_file_paths('foo/wtf.html')
    content = u"""<!DOCTYPE html><html><head><title>%s</title>
    <link href="/styles/reset.css">
    <link href="/styles/test.css">
    <script src="/scripts/main.js"></script>
    <img src="/static/img.jpg" data-src="/static/imgBig.jpg">
    </head><body></body></html>"""
    create_file(sp1, content % 'wtf')
    create_file(sp2, content % 'foo/wtf')

    c.build()

    page = read_content(bp1)
    assert '<link href="styles/reset.css">' in page
    assert '<link href="styles/test.css">' in page
    assert '<script src="scripts/main.js">' in page
    assert '<img src="static/img.jpg" data-src="static/imgBig.jpg">' in page
    page = read_content(bp2)
    assert '<link href="../styles/reset.css">' in page
    assert '<link href="../styles/test.css">' in page
    assert '<script src="../scripts/main.js">' in page
    assert '<img src="../static/img.jpg" data-src="../static/imgBig.jpg">' in page


def test_translate_absolute_to_relative_index(c):
    make_dirs(SOURCE_DIR, 'bar')

    sp1, bp1 = get_file_paths('index.html')
    sp2, bp2 = get_file_paths('bar/index.html')
    content = u"""<!DOCTYPE html><html><head><title>%s</title></head>
    <body><a href="/">Home</a></body></html>"""
    create_file(sp1, content % 'index')
    create_file(sp2, content % 'bar/index')

    c.build()

    page = read_content(bp1)
    assert '<a href="index.html">Home</a>' in page
    page = read_content(bp2)
    assert '<a href="../index.html">Home</a>' in page


def test_translate_ignore_external_urls(c):
    sp1, bp1 = get_file_paths('t1.html')
    sp2, bp2 = get_file_paths('t2.html')
    sp3, bp3 = get_file_paths('t3.html')
    c1 = (u'<!DOCTYPE html><html><head><title></title></head><body>'
        '<a href="//google.com"></a></body></html>')
    c2 = (u'<!DOCTYPE html><html><head><title></title></head><body>'
        '<a href="http://example.net/foo/bar"></a></body></html>')
    c3 = (u'<!DOCTYPE html><html><head><title></title></head><body>'
        '<a href="mailto:bob@example.com"></a></body></html>')
    create_file(sp1, c1)
    create_file(sp2, c2)
    create_file(sp3, c3)

    c.build()
    assert read_content(bp1) == c1
    assert read_content(bp2) == c2
    assert read_content(bp3) == c3


def test_filter_hidden_files(c):
    sp, bp = get_file_paths('.DS_Store')
    create_file(sp, u'lorem ipsum')
    c.build()
    assert not exists(bp)


def test_setting_filter_fragments(c):
    sp, bp = get_file_paths('fragment.html')
    create_file(sp, u"lalala")

    c.settings['FILTER_PARTIALS'] = True
    c.build()
    assert not exists(bp)

    c.settings['FILTER_PARTIALS'] = False
    c.build()
    assert exists(bp)


def test_setting_force_fragment_inclusion(c):
    name = 'fragment.html'
    sp, bp = get_file_paths(name)
    create_file(sp, u"lalala")

    c.settings['FILTER_PARTIALS'] = True
    c.settings['INCLUDE'] = [name,]
    c.build()
    assert exists(bp)


def test_setting_force_ignore(c):
    name = 'fullpage.html'
    sp, bp = get_file_paths(name)
    content = HTML
    create_file(sp, content)

    c.settings['FILTER'] = [name,]
    c.build()
    assert not exists(bp)


def test_build__index(c):
    make_dirs(SOURCE_DIR, 'bbb')

    sp1, bp1 = get_file_paths('aaa.html')
    sp2, bp2 = get_file_paths('bbb/ccc.html')
    sp3, bp3 = get_file_paths('ddd.html')
    create_file(sp1, HTML)
    create_file(sp2, HTML)
    create_file(sp3, HTML)

    c.build()

    bpindex = get_build_path('_index.html')
    page = read_content(bpindex)
    assert 'href="aaa.html"' in page
    assert 'href="bbb/ccc.html"' in page
    assert 'href="ddd.html"' in page


def test_build__index_txt(c):
    make_dirs(SOURCE_DIR, 'bbb')

    sp1, bp1 = get_file_paths('aaa.html')
    sp2, bp2 = get_file_paths('eee.html')
    sp3, bp3 = get_file_paths('bbb/aa.html')
    sp4, bp4 = get_file_paths('bbb/zz.html')
    sp5, bp5 = get_file_paths('bbb/ccc.html')
    sp6, bp6 = get_file_paths('ddd.html')
    sp7, bp7 = get_file_paths('bbb/bb.html')
    create_file(sp1, HTML)
    create_file(sp2, HTML)
    create_file(sp3, HTML)
    create_file(sp4, HTML)
    create_file(sp5, HTML)
    create_file(sp6, HTML)
    create_file(sp7, HTML)
    c.build()

    bpindex = get_build_path('_index.txt')
    page = read_content(bpindex)
    assert page.find('http://0.0.0.0:8080/aaa.html') \
        < page.find('http://0.0.0.0:8080/ddd.html')
    assert page.find('http://0.0.0.0:8080/ddd.html') \
        < page.find('http://0.0.0.0:8080/eee.html')
    assert page.find('http://0.0.0.0:8080/eee.html') \
        < page.find('http://0.0.0.0:8080/bbb/aa.html')
    assert page.find('http://0.0.0.0:8080/bbb/aa.html') \
        < page.find('http://0.0.0.0:8080/bbb/bb.html')
    assert page.find('http://0.0.0.0:8080/bbb/bb.html') \
        < page.find('http://0.0.0.0:8080/bbb/ccc.html')
    assert page.find('http://0.0.0.0:8080/bbb/ccc.html') \
        < page.find('http://0.0.0.0:8080/bbb/zz.html')


def test_do_not_include_non_template_files_in__index(c):
    bpindex = get_build_path('_index.html')

    sp = get_source_path('main.js')
    create_file(sp, "/* {% foobar %} */")
    c.build()
    page = read_content(bpindex)
    assert 'href="main.js"' not in page


def test_setting_filter_fragments_in__index(c):
    bpindex = get_build_path('_index.html')

    create_file(get_source_path('bbb.html'), u'lalala')

    c.settings['FILTER_PARTIALS'] = True
    c.build()
    page = read_content(bpindex)
    assert 'href="bbb.html"' not in page

    c.settings['FILTER_PARTIALS'] = False
    c.build()
    page = read_content(bpindex)
    assert 'href="bbb.html"' in page


def test_setting_force_fragment_inclusion_in__index(c):
    bpindex = get_build_path('_index.html')

    name = 'fragment.html'
    create_file(get_source_path(name), u'lalala')

    c.settings['FILTER_PARTIALS'] = True
    c.settings['INCLUDE'] = [name,]
    c.build()
    page = read_content(bpindex)
    assert 'href="%s"' % name in page


def test_setting_force_ignore_in__index(c):
    bpindex = get_build_path('_index.html')

    name = 'fullpage.html'
    create_file(get_source_path(name), HTML)

    c.settings['FILTER_PARTIALS'] = True
    c.settings['FILTER'] = [name,]
    c.build()
    page = read_content(bpindex)
    assert 'href="%s"' % name not in page


def test_setting_force_ignore_in__index_with_patterns(c):
    make_dirs(SOURCE_DIR, 'b')

    sp1, bp1 = get_file_paths('a.html')
    sp2, bp2 = get_file_paths('b/aa.html')
    sp3, bp3 = get_file_paths('b/z.html')
    sp4, bp4 = get_file_paths('b/ab.html')
    create_file(sp1, HTML)
    create_file(sp2, HTML)
    create_file(sp3, HTML)
    create_file(sp4, HTML)
    c.settings['FILTER'] = ['b/a*']
    c.build()

    bpindex = get_build_path('_index.html')
    page = read_content(bpindex)
    assert page.find('href="a.html"') != -1
    assert page.find('href="b/z.html"') != -1
    assert page.find('href="b/aa.html"') == -1
    assert page.find('href="b/ab.html"') == -1


def test_setting_force_inclusion_in__index_with_patterns(c):
    make_dirs(SOURCE_DIR, 'b')

    sp1, bp1 = get_file_paths('aaa.html')
    sp2, bp2 = get_file_paths('aab.html')
    sp3, bp3 = get_file_paths('abc.html')
    sp4, bp4 = get_file_paths('add.html')

    sp5, bp5 = get_file_paths('zoo.html')
    sp6, bp6 = get_file_paths('foo.html')
    sp7, bp7 = get_file_paths('b/loremipsum-oo.html')

    create_file(sp1, HTML)
    create_file(sp2, HTML)
    create_file(sp3, HTML)
    create_file(sp4, HTML)
    create_file(sp5, HTML)
    create_file(sp6, HTML)
    create_file(sp7, HTML)

    c.settings['FILTER'] = ['a*', '*oo.html']
    c.settings['INCLUDE'] = ['aa*', 'b/loremipsum*']
    c.build()

    bpindex = get_build_path('_index.html')
    page = read_content(bpindex)
    assert page.find('href="aaa.html"') != -1
    assert page.find('href="aab.html"') != -1
    assert page.find('href="b/loremipsum-oo.html"') != -1
    assert page.find('href="abc.html"') == -1
    assert page.find('href="add.html"') == -1

    for path in (bp1, bp2, bp7):
        assert read_content(path) == HTML


def test_feedback_message(c):
    n1 = 'aa.html'
    n2 = 'bb.html'
    n3 = 'cc.txt'
    n4 = 'dd.txt.tmpl'
    create_file(get_source_path(n1), HTML)
    create_file(get_source_path(n2), HTML)
    create_file(get_source_path(n3), u'lalala')
    create_file(get_source_path(n4), u'lalala')
    c.settings['FILTER_PARTIALS'] = True

    msg = execute_and_read_stdout(c.build)

    assert n1 in msg
    assert n2 in msg
    assert n3 in msg
    assert n4 not in msg


def test_build_variable(c):
    name = 'test.html'
    sp, bp = get_file_paths(name)
    create_file(sp, u'foo{% if BUILD %}bar{% endif %}')
    c.settings['FILTER_PARTIALS'] = False
    c.build_page(name)
    result = read_content(bp)
    assert result.strip() == 'foobar'

########NEW FILE########
__FILENAME__ = test_exceptions
# -*- coding: utf-8 -*-
from clay import Clay
from clay.main import SOURCE_NOT_FOUND
import pytest

from .helpers import *


def test_friendly_notfound_of_templates(t):
    create_file(get_source_path('foo.html'), u'foo{% include "bar.html" %}')

    resp = t.get('/hello.html')
    assert resp.status_code == HTTP_NOT_FOUND
    assert 'hello.html' in resp.data
    assert 'jinja2.exceptions' not in resp.data

    resp = t.get('/foo.html')
    assert resp.status_code == HTTP_NOT_FOUND
    assert 'bar.html' in resp.data
    assert 'jinja2.exceptions' not in resp.data


def test_friendly_notfound_of_files(t):
    resp = t.get('/foobar')
    assert resp.status_code == HTTP_NOT_FOUND
    assert 'foobar' in resp.data
    assert 'jinja2.exceptions' not in resp.data


def test_fail_if_source_dir_dont_exists(c):
    remove_dir(SOURCE_DIR)

    def fake_run(**kwargs):
        return kwargs

    _run = c.app.run
    c.app.run = fake_run
    out = execute_and_read_stdout(c.run)

    c.app.run = _run
    make_dirs(SOURCE_DIR)

    assert SOURCE_NOT_FOUND in out


def test_make_dirs_wrong():
    with pytest.raises(OSError):
        make_dirs('/etc/bla')


def test_fix_settings():
    bad_settings = dict(
        FILTER_PARTIALS = None,
        FILTER = None,
        INCLUDE = None,
        HOST = None,
        PORT = None,
    )
    c = Clay(TESTS, bad_settings)
    create_page('test.html', HTML)
    c.get_pages_index()


########NEW FILE########
__FILENAME__ = test_main
# -*- coding: utf-8 -*-
from __future__ import print_function

from clay import Clay

from .helpers import *


TEXT = u'''Je suis belle, ô mortels! comme un rêve de pierre,
Et mon sein, où chacun s'est meurtri tour à tour,
Est fait pour inspirer au poète un amour'''


def assert_page(t, name, content=HTML, url=None, encoding='utf8'):
    create_page(name, content, encoding)
    url = url or '/' + name
    resp = t.get(url)
    assert resp.status_code == HTTP_OK
    assert content.encode(encoding) == resp.data


def test_setup_with_filename_as_root():
    assert Clay(__file__)


def test_setup_with_settings():
    c = Clay(TESTS, {'foo': 'bar'})
    assert 'foo' in c.settings


def test_get_real_fn(c):
    assert c.get_real_fn('foo/bar/test.html') == 'test.html'
    assert c.get_real_fn('foo/bar/test.txt') == 'test.txt'
    assert c.get_real_fn('foo/bar/test.txt.tmpl') == 'test.txt'


def test_guess_mimetype(c):
    assert c.guess_mimetype('lalala.html') == 'text/html'
    assert c.guess_mimetype('lalala.txt') == 'text/plain'
    assert c.guess_mimetype('whatever') == 'text/plain'


def test_load_settings_from_file():
    c = Clay(TESTS)
    assert 'foo' not in c.settings

    stpath = join(TESTS, 'settings.py')
    create_file(stpath, "\nfoo='bar'\n")
    c = Clay(TESTS)
    remove_file(stpath)
    assert 'foo' in c.settings


def test_render_page(t):
    assert_page(t, 'index.html')


def test_index_page(t):
    assert_page(t, 'index.html', url='/')


def test_render_sub_page(t):
    assert_page(t, 'sub/index.html')


def test_render_sub_index_page(t):
    assert_page(t, 'sub/index.html', url='sub')


def test_ignore_non_template_files(t):
    assert_page(t, 'main.js', "/* {% foobar %} */")


def test_i18n_filename(t):
    assert_page(t, 'mañana.txt', TEXT)


def test_weird_encoding_of_content(t):
    assert_page(t, 'iso-8859-1.txt', TEXT, encoding='iso-8859-1')


def test_static_filename(t):
    assert_page(t, 'static/css/index.css', u'')


def test_process_template_files(t):
    content = """
    {% for i in range(1,5) -%}
    .icon{{ i }} { background-image: url('img/icon{{ i }}.png'); }
    {% endfor -%}
    """
    expected = """
    .icon1 { background-image: url('img/icon1.png'); }
    .icon2 { background-image: url('img/icon2.png'); }
    .icon3 { background-image: url('img/icon3.png'); }
    .icon4 { background-image: url('img/icon4.png'); }
    """
    path = get_source_path('main.css.tmpl')
    create_file(path, content)
    resp = t.get('/main.css.tmpl')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/css'
    assert resp.data.strip() == expected.strip()


def test_page_with_includes(t):
    create_file(get_source_path('foo.html'), u'foo{% include "bar.html" %}')
    create_file(get_source_path('bar.html'), u'bar')
    resp = t.get('/foo.html')
    assert resp.status_code == HTTP_OK
    assert resp.data == 'foobar'
    assert resp.mimetype == 'text/html'


def test_settings_as_template_context():

    c = Clay(TESTS, {'who': u'world'})
    t = c.get_test_client()
    create_file(get_source_path('hello.html'), u'Hello {{ who }}!')
    resp = t.get('/hello.html')
    assert resp.status_code == HTTP_OK
    assert resp.data == 'Hello world!'
    assert resp.mimetype == 'text/html'


def test_values_as_template_context():
    c = Clay(TESTS)
    t = c.get_test_client()
    create_file(get_source_path('hello.html'), u'Hello {{ who }}!')
    resp = t.get('/hello.html?who=world')
    assert resp.status_code == HTTP_OK
    assert resp.data == 'Hello world!'
    assert resp.mimetype == 'text/html'


def test_get_pages_list(c):
    make_dirs(SOURCE_DIR, 'bbb')

    create_file(get_source_path('aaa.html'), HTML)
    create_file(get_source_path('bbb/ccc.html'), HTML)
    create_file(get_source_path('lalala.txt'), u'')

    expected = ['aaa.html', 'bbb/ccc.html', 'lalala.txt']
    expected.sort()
    result = c.get_pages_list()
    result.sort()
    print(result)
    assert expected == result


def test_show__index_txt(t):
    make_dirs(SOURCE_DIR, 'bbb')

    create_file(get_source_path('aaa.html'), HTML)
    create_file(get_source_path('bbb/ccc.html'), HTML)
    create_file(get_source_path('lalala.txt'), u'')

    resp = t.get('/_index.txt')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/plain'

    page = resp.data
    assert 'http://0.0.0.0:8080/aaa.html' in page
    assert 'http://0.0.0.0:8080/bbb/ccc.html' in page
    assert 'href="aaa.html"' not in page
    assert 'lalala.txt' not in page


def test_show__index(t):
    make_dirs(SOURCE_DIR, 'bbb')

    create_file(get_source_path('aaa.html'), HTML)
    create_file(get_source_path('bbb/ccc.html'), HTML)
    create_file(get_source_path('ddd.html'), HTML)

    resp = t.get('/_index.html')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'

    page = resp.data
    assert 'href="aaa.html"' in page
    assert 'href="bbb/ccc.html"' in page
    assert 'href="ddd.html"' in page


def test__index_is_sorted(t):
    make_dirs(SOURCE_DIR, 'bbb')

    create_file(get_source_path('bbb.html'), HTML)
    create_file(get_source_path('bbb/aa.html'), HTML)
    create_file(get_source_path('bbb/ccc.html'), HTML)
    create_file(get_source_path('aaa.html'), HTML)
    create_file(get_source_path('ddd.html'), HTML)

    resp = t.get('/_index.html')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'

    page = resp.data
    assert page.find('href="aaa.html"') < page.find('href="bbb.html"')
    assert page.find('href="bbb.html"') < page.find('href="ddd.html"')
    assert page.find('href="ddd.html"') < page.find('href="bbb/aa.html"')
    assert page.find('href="bbb/aa.html"') < page.find('href="bbb/ccc.html"')


def test_do_not_include_non_template_files_in__index(t):
    create_file(get_source_path('main.js'), "/* {% foobar %} */")
    resp = t.get('/_index.html')
    assert 'href="main.js"' not in resp.data


def test_setting_filter_fragments_in__index(c):
    t = c.get_test_client()

    create_file(get_source_path('aaa.html'), HTML)
    create_file(get_source_path('bbb.html'), u'lalala')

    c.settings['FILTER_PARTIALS'] = True
    resp = t.get('/_index.html')
    page = resp.data
    assert 'href="aaa.html"' in page
    assert 'href="bbb.html"' not in page

    c.settings['FILTER_PARTIALS'] = False
    resp = t.get('/_index.html')
    page = resp.data
    assert 'href="aaa.html"' in page
    assert 'href="bbb.html"' in page


def test_setting_filter_fragments_in__indexs_after_rendering(c):
    t = c.get_test_client()

    create_file(get_source_path('base.html'),
        u'<!DOCTYPE html><html><body>{% block content %}{% endblock %}</body></html>')
    create_file(get_source_path('xxx.html'),
        u'{% extends "base.html" %}{% block content %}Hi!{% endblock %}')

    c.settings['FILTER_PARTIALS'] = True
    resp = t.get('/_index.html')
    page = resp.data
    assert 'href="base.html"' in page
    assert 'href="xxx.html"' in page


def test_setting_force_fragment_inclusion_in__index(c):
    t = c.get_test_client()

    name = 'fragment.html'
    create_file(get_source_path(name), u'lalala')

    c.settings['FILTER_PARTIALS'] = True
    c.settings['INCLUDE'] = [name, ]
    resp = t.get('/_index.html')
    assert 'href="%s"' % name in resp.data


def test_setting_force_ignore_in__index(c):
    t = c.get_test_client()

    name = 'fullpage.html'
    create_file(get_source_path(name), HTML)

    c.settings['FILTER_PARTIALS'] = True
    c.settings['FILTER'] = [name, ]
    resp = t.get('/_index.html')
    assert not 'href="%s"' % name in resp.data


def test_setting_force_ignore_in__index_with_patterns(c):
    make_dirs(SOURCE_DIR, 'b')

    create_file(get_source_path('a.html'), HTML)
    create_file(get_source_path('b.html'), HTML)

    create_file(get_source_path('b/c.html'), HTML)
    create_file(get_source_path('b/ab.html'), HTML)
    create_file(get_source_path('b/a-a.html'), HTML)

    create_file(get_source_path('zoo.html'), HTML)
    create_file(get_source_path('foo.html'), HTML)
    create_file(get_source_path('b/loremipsum-oo.html'), HTML)

    t = c.get_test_client()
    c.settings['FILTER'] = ['b/a*', '*oo.html']
    resp = t.get('/_index.html')

    assert 'href="a.html"' in resp.data
    assert 'href="b.html"' in resp.data
    assert 'href="b/aa.html"' not in resp.data
    assert 'href="b/c.html"' in resp.data
    assert 'href="b/ab.html"' not in resp.data

    assert 'href="zoo.html"' not in resp.data
    assert 'href="foo.html"' not in resp.data
    assert 'href="b/loremipsum-oo.html"' not in resp.data


def test_setting_force_inclusion_in__index_with_patterns(c):
    make_dirs(SOURCE_DIR, 'b')

    create_file(get_source_path('aaa.html'), HTML)
    create_file(get_source_path('aab.html'), HTML)
    create_file(get_source_path('abc.html'), HTML)
    create_file(get_source_path('add.html'), HTML)

    create_file(get_source_path('zoo.html'), HTML)
    create_file(get_source_path('foo.html'), HTML)
    create_file(get_source_path('b/loremipsum-oo.html'), HTML)

    t = c.get_test_client()
    c.settings['FILTER'] = ['a*', '*oo.html']
    c.settings['INCLUDE'] = ['aa*', 'b/loremipsum*']
    resp = t.get('/_index.html')

    assert 'href="aaa.html"' in resp.data
    assert 'href="aab.html"' in resp.data
    assert 'href="abc.html"' not in resp.data
    assert 'href="add.html"' not in resp.data

    assert 'href="zoo.html"' not in resp.data
    assert 'href="foo.html"' not in resp.data
    assert 'href="b/loremipsum-oo.html"' in resp.data


def test_no_build_variable(t):
    name = u'build-test.html'
    content = u'foo{% if BUILD %}bar{% endif %}'
    create_page(name, content, 'utf8')
    url = '/' + name
    resp = t.get(url)
    assert resp.data == u'foo'

########NEW FILE########
__FILENAME__ = test_manage
# -*- coding: utf-8 -*-
import os
import sys
from tempfile import mkdtemp

import clay
from clay.manage import manager
from flask import Flask

from .helpers import *


def test_create_skeleton():
    test_dir = mkdtemp()
    sys.argv = [sys.argv[0], 'new', test_dir]
    manager.run()
    assert os.path.isdir(join(test_dir, 'source'))
    remove_dir(test_dir)


def test_get_version():
    sys.argv = [sys.argv[0], 'version']
    o = execute_and_read_stdout(manager.run)
    assert o.strip() == clay.__version__


def test_can_run(c, monkeypatch):
    def fake_run(self, **config):
        assert config['use_debugger']
        assert not config['use_reloader']

    monkeypatch.setattr(Flask, 'run', fake_run)
    sys.argv = [sys.argv[0], 'run']
    manager.run()


def test_run_with_custom_host_and_port(c, monkeypatch):
    host = 'localhost'
    port = 9000

    def fake_run(self, **config):
        assert host == config['host']
        assert port == config['port']

    monkeypatch.setattr(Flask, 'run', fake_run)
    sys.argv = [sys.argv[0], 'run', mkdtemp(), str(host), str(port)]
    manager.run()


def test_can_build(c):
    test_dir = mkdtemp()
    make_dirs(test_dir, 'source')
    sp = join(test_dir, 'source', 'foo.txt')
    bp = join(test_dir, 'build', 'foo.txt')
    create_file(sp, u'bar')

    sys.argv = [sys.argv[0], 'build', '--path', test_dir]
    manager.run()
    assert os.path.exists(bp)
    remove_dir(test_dir)


def test_can_build_pattern(c):
    test_dir = mkdtemp()
    make_dirs(test_dir, 'source')
    sp1 = join(test_dir, 'source', 'foo.txt')
    bp1 = join(test_dir, 'build', 'foo.txt')
    create_file(sp1, u'bar')

    sp2 = join(test_dir, 'source', 'bar.txt')
    bp2 = join(test_dir, 'build', 'bar.txt')
    create_file(sp2, u'bar')

    sys.argv = [sys.argv[0], 'build', 'bar.txt', '--path', test_dir]
    manager.run()
    assert not os.path.exists(bp1)
    assert os.path.exists(bp2)
    assert read_content(bp2) == u'bar'
    remove_dir(test_dir)

########NEW FILE########
__FILENAME__ = test_render_includewith
# -*- coding: utf-8 -*-
from jinja2 import Environment, DictLoader

from clay.jinja_includewith import IncludeWith


env = Environment(
    loader=DictLoader({
        'hello': 'Hello {{ what }}!',
        'sum': '{{ a }} + {{ b }} makes {{ c }}',
        'foo/bar.html': '{{ num }}. Hello {{ what }}!',
    }),
    extensions=['jinja2.ext.with_', IncludeWith]
)


def test_set_context():
    tmpl = env.from_string('''{% include "hello" with what='world' %} {% include "hello" with what='world' %}''')
    expected = '''Hello world! Hello world!'''
    result = tmpl.render()
    assert result == expected


def test_set_context_linebreak():
    tmpl = env.from_string('''{% include "hello"
        with
        what='world' -%}''')
    expected = '''Hello world!'''
    result = tmpl.render()
    assert result == expected


def test_overwrite_context():
    tmpl = env.from_string('''
        {% include "foo/bar.html" with what="world", num="1" %}
        {% include "foo/bar.html" with what="world", num="2" %}
        {% include "foo/bar.html" with what="world", num="3" %}
        {% include "foo/bar.html" with what="world", num="4" %}
    ''')
    expected = '''
        1. Hello world!
        2. Hello world!
        3. Hello world!
        4. Hello world!
    '''
    result = tmpl.render(what='you')
    assert result == expected


def test_multiple_values():
    tmpl = env.from_string('''
        {% include "sum" with a=3, b=2, c=3+2 %}
        {% include "sum" with a=3, b=2, c=3+2 %}
    ''')
    expected = '''
        3 + 2 makes 5
        3 + 2 makes 5
    '''
    result = tmpl.render()
    assert result == expected


def test_careless_formatting():
    tmpl = env.from_string('''
        {% include "sum" with a = 'Antartica', b=42,c='no sense' %}
        {% include "sum" with a='Antartica',b=42 ,c='no sense' %}
    ''')
    expected = '''
        Antartica + 42 makes no sense
        Antartica + 42 makes no sense
    '''
    result = tmpl.render()
    assert result == expected


def test_text():
    tmpl = env.from_string('''{% include "hello" with what='5%, er }} lalala' %} {% include "hello" with what='world' %}''')
    expected = '''Hello 5%, er }} lalala! Hello world!'''
    result = tmpl.render()
    assert result == expected


def test_include_current_context():
    tmpl = env.from_string('''
        {% set a = 2 %}{% include "sum" with c=4 %}
        {% include "sum" with c=4 %}
    ''')
    expected = '''
        2 + 2 makes 4
        2 + 2 makes 4
    '''
    result = tmpl.render(b=2)
    assert result == expected


def test_unobstrusiveness():
    tmpl = env.from_string('''{% include "hello" %}''')
    r1 = tmpl.render(what='you')
    tmpl = env.from_string('''{% include "hello" with context %}''')
    r2 = tmpl.render(what='you')
    assert r1 == r2 == 'Hello you!'


########NEW FILE########
__FILENAME__ = test_render_markdown
# -*- coding: utf-8 -*-
from __future__ import print_function

from .helpers import *


def test_basic_md(t):
    content = '''
Roses are red;
Violets are blue.

Hello world!
'''
    expected = '''
<p>Roses are red;<br>
Violets are blue.</p>
<p>Hello world!</p>
'''
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_jinja_variables(t):
    content = 'Hello {{ foo }}!'
    expected = '<p>Hello bar!</p>'
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_layout(t):
    base = '''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{% block title %}{% endblock %}</title>
</head>
<body>{% block content %}{% endblock %}</body>
</html>
'''

    content = '''layout: base.html
title: Hello world

# Hi
'''

    expected = '''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Hello world</title>
</head>
<body><h1 id="hi">Hi</h1></body>
</html>
'''

    create_file(get_source_path('base.html'), base)
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_fenced_code(t):
    content = '''
Plain:

```
pip install clay
```

Highlighted:

```python
print('hi')
```
'''
    expected = '''
<p>Plain:</p>
<pre><code>pip install clay
</code></pre>


<p>Highlighted:</p>
<pre><code class="language-python"><span class="k">print</span><span class="p">(</span><span class="s">&#39;hi&#39;</span><span class="p">)</span>
</code></pre>
'''
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_protect_jinja_code(t):
    content = '''
```jinja
{{ protect_me }}
```
'''
    expected = '''
<pre><code class="language-jinja"><span class="cp">{{</span> <span class="nv">protect_me</span> <span class="cp">}}</span><span class="x"></span>
</code></pre>
'''
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_admonition(t):
    content = '''
!!! note clear
    This is the first line inside the box.
    This is [an example](http://example.com/) inline link.

    Another paragraph
'''
    expected = '''
<div class="admonition note clear">
<p>This is the first line inside the box.<br>
This is <a href="http://example.com/">an example</a> inline link.</p>
<p>Another paragraph</p>
</div>
'''
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_superscript(t):
    content = '''
lorem ipsum^1 sit.

6.02 x 10^23

10^(2x + 3).
'''
    expected = '''
<p>lorem ipsum<sup>1</sup> sit.</p>
<p>6.02 x 10<sup>23</sup></p>
<p>10<sup>2x + 3</sup>.</p>
'''
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_delinsmark(t):
    content = '''
This is ++added content++, this is ~~deleted content~~ and this is ==marked==.
'''
    expected = '''
<p>This is <ins>added content</ins>, this is <del>deleted content</del> and this is <mark>marked</mark>.</p>
'''
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()


def test_autolink(t):
    content = '''
http://example.com/

go to http://example.com. Now!

ftp://example.com

www.example.com

WWW.EXAMPLE.COM

www.example.pe

(www.example.us/path/?name=val)

----------

like something.com or whatever

punto.pe

<a href="http://example.com/">http://example.com/</a>

<a href="www.example.org/" title="www.example.net" class="blue">http://example.org/</a>

info@example.com

<a href="mailto:info@example.com">write us</a>
'''
    expected = '''
<p><a href="http://example.com/">http://example.com/</a></p>
<p>go to <a href="http://example.com">http://example.com</a>. Now!</p>
<p><a href="ftp://example.com">ftp://example.com</a></p>
<p><a href="http://www.example.com">www.example.com</a></p>
<p><a href="http://WWW.EXAMPLE.COM">WWW.EXAMPLE.COM</a></p>
<p><a href="http://www.example.pe">www.example.pe</a></p>
<p>(<a href="http://www.example.us/path/?name=val">www.example.us/path/?name=val</a>)</p>
<hr>
<p>like something.com or whatever</p>
<p>punto.pe</p>
<p><a href="http://example.com/">http://example.com/</a></p>
<p><a href="www.example.org/" title="www.example.net" class="blue">http://example.org/</a></p>
<p>info@example.com</p>
<p><a href="mailto:info@example.com">write us</a></p>
'''
    path = get_source_path('test.md')
    create_file(path, content)
    resp = t.get('/test.md')
    assert resp.status_code == HTTP_OK
    assert resp.mimetype == 'text/html'
    print(resp.data)
    assert resp.data.strip() == expected.strip()

########NEW FILE########
__FILENAME__ = test_server
# -*- coding: utf-8 -*-
from datetime import datetime

from clay.server import RequestLogger
import pytest
import socket

from .helpers import *


def test_run_with_custom_host_and_port(c):
    class FakeServer(object):
        def __init__(self, hp, **kwargs):
            self.hp = hp

        def start(self):
            return self.hp

        def stop(self):
            pass

    def get_fake_server(host, port):
        return FakeServer((host, port))

    _get_wsgi_server = c.server._get_wsgi_server
    c.server._get_wsgi_server = get_fake_server
    host = 'localhost'
    port = 9000
    h, p = c.run(host=host, port=port)
    c.server._get_wsgi_server = _get_wsgi_server
    assert host == h
    assert port == p


def test_run_port_is_already_in_use(c):
    ports = []

    class FakeServer(object):
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            raise socket.error()

        def stop(self):
            pass

    def get_fake_server(host, port):
        ports.append(port)
        return FakeServer()

    _get_wsgi_server = c.server._get_wsgi_server
    c.server._get_wsgi_server = get_fake_server
    host = 'localhost'
    port = 9000
    c.run(host=host, port=port)
    c.server._get_wsgi_server = _get_wsgi_server

    expected = [p for p in range(port, port + 11)]
    assert ports == expected


def test_server_stop(c):
    log = []

    class FakeServer(object):
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            log.append('start')
            raise KeyboardInterrupt

        def stop(self):
            log.append('stop')

    def get_fake_server(host, port):
        return FakeServer()

    _get_wsgi_server = c.server._get_wsgi_server
    c.server._get_wsgi_server = get_fake_server
    c.run()
    c.server._get_wsgi_server = _get_wsgi_server

    assert log == ['start', 'stop']


def test_run_with_invalid_port(c):
    with pytest.raises(Exception):
        c.run(port=-80)


def test_request_logger():
    def app(*args, **kwargs):
        pass

    l = RequestLogger(app)
    environ = {
        'REMOTE_ADDR': '192.168.0.25',
        'REQUEST_URI': '/lalala',
        'REQUEST_METHOD': 'HEAD',
    }
    now = datetime.now()
    out = execute_and_read_stdout(lambda: l.log_request(environ, now))
    expected = ' %s | 192.168.0.25  /lalala  (HEAD)\n' % now.strftime('%H:%M:%S')
    assert out == expected


def test_request_logger_as_middleware():
    called = []

    def app(*args, **kwargs):
        pass

    def start_response(*args, **kwargs):
        called.append(True)

    l = RequestLogger(app)
    l({}, start_response)
    assert not called


def test_request_logger_as_middleware_fail():
    called = []

    def app(*args, **kwargs):
        raise ValueError

    def start_response(*args, **kwargs):
        called.append(True)

    l = RequestLogger(app)
    with pytest.raises(ValueError):
        l({}, start_response)
    assert called



########NEW FILE########
__FILENAME__ = test_tg_active
# -*- coding: utf-8 -*-
from clay.tglobals import active

from .helpers import *


ACTIVE_PATH = '/foo/bar.html'


def _test_active():
    assert not active('/hello/')
    assert active(ACTIVE_PATH) == 'active'
    assert active('/hello/', ACTIVE_PATH[:5], partial=True) == 'active'
    assert active('/hello/', ACTIVE_PATH) == 'active'
    assert not active('/hello/', '/world/')


def _test_active_relative():
    assert not active('meh')
    assert active('bar.html') == 'active'
    assert active('b', partial=True) == 'active'


def _test_active_patterns():
    assert active('/*/bar.html') == 'active'
    assert active('/fo?/bar.html') == 'active'
    assert active('/f*') == 'active'


def _test_active_backward_compatibilty():
    assert active(['/hello/', ACTIVE_PATH, ]) == 'active'
    assert not active(['/hello/', '/world/', ])
    assert active([ACTIVE_PATH[:5], ], partial=True) == 'active'


def test_active(c):
    with c.app.test_request_context(ACTIVE_PATH, method='GET'):
        _test_active()


def test_active_index(c):
    with c.app.test_request_context('/index.html', method='GET'):
        assert active('/') == 'active'
        assert active('/index.html') == 'active'
        assert active('') == 'active'

    with c.app.test_request_context('/foo/bar/index.html', method='GET'):
        assert active('/foo/bar') == 'active'
        assert active('/foo/bar/') == 'active'
        assert active('/foo/bar/index.html') == 'active'

    with c.app.test_request_context('/', method='GET'):
        assert active('/') == 'active'
        assert active('/index.html') == 'active'
        assert active('') == 'active'


def test_active_relative(c):
    with c.app.test_request_context(ACTIVE_PATH, method='GET'):
        _test_active_relative()


def test_active_patterns(c):
    with c.app.test_request_context(ACTIVE_PATH, method='GET'):
        _test_active_patterns()


def test_active_backward_compatibilty(c):
    with c.app.test_request_context(ACTIVE_PATH, method='GET'):
        _test_active_backward_compatibilty()


def test_active_in_templates(t):
    path = 'bbbb.html'
    content = u'''class="{{ active('%s') }}"''' % path
    create_file(get_source_path(path), content)

    expected = u'class="active"'
    resp = t.get('/' + path)
    assert resp.data == expected

########NEW FILE########
