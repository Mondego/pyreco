__FILENAME__ = letterpress
#! /usr/bin/env python3
# -*- coding: utf-8 -*-

__version_info__ = (0, 0, 2)
__version__ = '.'.join(map(str, __version_info__))
__author__ = "Ling Wang"

import sys

argparse = None

if sys.version_info.minor < 2:
    import optparse
else:
    import argparse

import re
import markdown2
import logging
import logging.handlers
import codecs
import datetime
import os.path
import urllib.parse
import shutil
import itertools
import pyinotify

#--- globals ---
logger = logging.getLogger('Letterpress')


_meta_data_re = re.compile(r"""(?:\s*\n)*((?:\w+:.*\n)+)(?:\s*\n)+""", re.U)


def extract_meta_data(text):
    meta_data = {}

    m = _meta_data_re.match(text)
    if not m:
        logger.error('No meta data')
        return meta_data, text

    lines = m.group(1).splitlines()
    for line in lines:
        k, v = line.split(':', 1)
        v = v.strip()
        if v:
            meta_data[k] = v

    return meta_data, text[m.end():]


_template_re = re.compile(r'{{([^{}]+)}}')


def format(template, **kwargs):
    return _template_re.sub(lambda m: kwargs[m.group(1)], template)

pygments_options = {'cssclass': 'code', 'classprefix': 'code-'}


class Post(object):
    def __new__(cls, file_path, base_url, templates_dir, date_format, math_delimiter):
        file_name = os.path.basename(file_path)
        logger.debug('Post: %s', file_name)
        text = ""
        with codecs.open(file_path, 'r', 'utf-8') as f:
            text = f.read()
        meta_data, rest_text = extract_meta_data(text)
        logger.debug('Meta: %s', meta_data)
        if not meta_data.get('title'):
            logger.error('Missing title')
            return None
        if not meta_data.get('date'):
            logger.error('Missing date')
            return None
        self = super(Post, cls).__new__(cls)
        self.meta_data = meta_data
        self.rest_text = rest_text
        return self

    def __init__(self, file_path, base_url, templates_dir, date_format, math_delimiter):
        meta_data = self.meta_data
        del self.meta_data
        rest_text = self.rest_text
        del self.rest_text
        self.file_path = file_path
        self.title = meta_data['title']
        self.title = self.title.replace('"', '&quot;')
        self.title = self.title.replace("'", "&#39;")
        self.date = datetime.datetime.strptime(meta_data['date'], date_format)
        self.pretty_date = self.date.strftime('%B %d, %Y')
        self.excerpt = meta_data.get('excerpt')
        if not self.excerpt:
            if (len(rest_text) > 140):
                self.excerpt = rest_text[:140] + '…'
            else:
                self.excerpt = rest_text
        self.excerpt = self.excerpt.replace('"', '&quot;')
        self.excerpt = self.excerpt.replace("'", "&#39;")
        self.tags = []
        is_math = False
        for tag_name in meta_data.get('tags', '').split(','):
            tag_name = tag_name.strip()
            if tag_name:
                self.tags.append(tag_name)
                if tag_name.lower() == 'math':
                    is_math = True
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        self.path = '{year:04}/{month:02}/{base_name}.html'.format(year=self.date.year, month=self.date.month, base_name=base_name.lower().replace(' ', '-'))
        self.permalink = os.path.join(base_url, self.path)
        with codecs.open(os.path.join(templates_dir, "post.html"), 'r', 'utf-8') as f:
            template = f.read()
        content = markdown2.markdown(rest_text, extras={'code-friendly': True, 'fenced-code-blocks': pygments_options, 'footnotes': True, 'math_delimiter': math_delimiter if is_math else None})
        # Process <code lang="programming-lang"></code> blocks or spans.
        content = self._format_code_lang(content)
        self.html = format(template, title=self.title, date=self.date.strftime('%Y-%m-%d'), monthly_archive_url=os.path.dirname(self.permalink) + '/', year=self.date.strftime('%Y'), month=self.date.strftime('%B'), day=self.date.strftime('%d'), tags=', '.join('<a href="/tags/{tag}">{tag}</a>'.format(tag=tag) for tag in self.tags), permalink=self.permalink, excerpt=self.excerpt, content=content)
        # Load MathJax for post with math tag.
        if is_math:
            self.html = self.html.replace('</head>', '''
<script type="text/x-mathjax-config">
MathJax.Hub.Config({
  asciimath2jax: {
    delimiters: [['%s','%s']]
  }
});
</script>
<script type="text/javascript" src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-MML-AM_HTMLorMML"></script>
</head>''' % (math_delimiter, math_delimiter))

    def __str__(self):
        return '{title}({date})'.format(title=self.title, date=self.pretty_date)

    def __repr__(self):
        return str(self)

    def __gt__(self, other):
        return self.date > other.date

    def __lt__(self, other):
        return self.date < other.date

    def __ge__(self, other):
        return self.date >= other.date

    def __le__(self, other):
        return self.date <= other.date

    _code_span_re = re.compile(r"""
        <code               # start tag
        \s+                 # word break
        lang=(['"])(\w+)\1  # lang \2
        \s*?>               # closing tag
        (.*?)               # code, minimally matching \3
        </code>             # the matching end tag
    """,
    re.X | re.M)

    def _code_span_sub(self, match):
        lang = match.group(2)
        code = match.group(3)
        lexer = self._get_pygments_lexer(lang)
        if lexer:
            return self._color_with_pygments(code, lexer)
        else:
            return match.group(0)

    def _format_code_lang(self, text):
        return self._code_span_re.sub(self._code_span_sub, text)

    def _get_pygments_lexer(self, lexer_name):
        try:
            from pygments import lexers, util
        except ImportError:
            return None
        try:
            return lexers.get_lexer_by_name(lexer_name)
        except util.ClassNotFound:
            return None

    def _color_with_pygments(self, code, lexer):
        import pygments
        import pygments.formatters

        class HtmlCodeFormatter(pygments.formatters.HtmlFormatter):
            def _wrap_code(self, inner):
                """A function for use in a Pygments Formatter which
                wraps in <code> tags.
                """
                yield 0, "<code>"
                for tup in inner:
                    yield tup[0], tup[1].strip()
                yield 0, "</code>"

            def wrap(self, source, outfile):
                """Return the source with a code."""
                return self._wrap_code(source)

        formatter = HtmlCodeFormatter(**pygments_options)
        return pygments.highlight(code, lexer, formatter)


class Tag(object):
    def __init__(self, name, posts):
        self.name = name
        self.posts = posts
        self.path = ('tags/' + name + '/')
        url_comps = urllib.parse.urlparse(posts[0].permalink)
        self.permalink = urllib.parse.urlunparse(url_comps[:2] + (self.path,) + (None,) * 3)

    def build_index(self, templates_dir):
        with codecs.open(os.path.join(templates_dir, "tag_archive.html"), 'r', 'utf-8') as f:
            template = f.read()
        posts_match = _posts_re.search(template)
        post_template = posts_match.group(1)
        header_template = template[:posts_match.start()]
        header = format(header_template, archive_title=self.name)
        post_list = []
        for post in sorted(self.posts, reverse=True):
            if not post:
                break
            post_list.append(format(post_template, title=post.title, date=post.date.strftime('%Y-%m-%d'), pretty_date=post.pretty_date, permalink=post.permalink, excerpt=post.excerpt))
        index = header + ''.join(post_list) + template[posts_match.end():]
        return index

    def __str__(self):
        return '{name}\n{posts}'.format(name=self.name, posts=self.posts)

    def __repr__(self):
        return str(self)

    def __gt__(self, other):
        return self.name.lower() > other.name.lower()

    def __lt__(self, other):
        return self.name.lower() < other.name.lower()

    def __ge__(self, other):
        return self.name.lower() >= other.name.lower()

    def __le__(self, other):
        return self.name.lower() <= other.name.lower()


class MonthlyArchive(object):
    def __init__(self, month, posts):
        self.month = month
        self.posts = posts
        self.path = os.path.dirname(posts[0].path) + '/'
        self.permalink = os.path.dirname(posts[0].permalink) + '/'

    def build_index(self, templates_dir, prev_archive=None, next_archive=None):
        with codecs.open(os.path.join(templates_dir, "monthly_archive.html"), 'r', 'utf-8') as f:
            template = f.read()
        posts_match = _posts_re.search(template)
        header_template = template[:posts_match.start()]
        prev_archive_title = ''
        prev_archive_url = ''
        if prev_archive:
            prev_archive_title = '<'
            prev_archive_url = prev_archive.permalink
        next_archive_title = ''
        next_archive_url = ''
        if next_archive:
            next_archive_title = '>'
            next_archive_url = next_archive.permalink
        header = format(header_template, archive_title=self.month.strftime('%B, %Y'), prev_archive_title=prev_archive_title, prev_archive_url=prev_archive_url, next_archive_title=next_archive_title, next_archive_url=next_archive_url, month=self.month.strftime('%B'), year=self.month.strftime('%Y'), yearly_archive_url=os.path.dirname(self.permalink[:-1]) + '/')
        post_template = posts_match.group(1)
        post_list = []
        for post in self.posts:
            post_list.append(format(post_template, title=post.title, date=post.date.strftime('%Y-%m-%d'), pretty_date=post.pretty_date, permalink=post.permalink, excerpt=post.excerpt))
        index = header + ''.join(post_list) + template[posts_match.end():]
        return index

    def __str__(self):
        return '{month}\n{posts}'.format(month=self.month.strftime('%Y-%m'), posts=self.posts)

    def __repr__(self):
        return str(self)

    def __gt__(self, other):
        return self.month > other.month

    def __lt__(self, other):
        return self.month < other.month

    def __ge__(self, other):
        return self.month >= other.month

    def __le__(self, other):
        return self.month <= other.month


class YearlyArchive(object):
    def __init__(self, year, monthly_archives):
        self.year = year
        self.monthly_archives = monthly_archives
        self.path = os.path.dirname(monthly_archives[0].path[:-1]) + '/'
        self.permalink = os.path.dirname(monthly_archives[0].permalink[:-1]) + '/'

    def build_index(self, templates_dir, prev_archive=None, next_archive=None):
        with codecs.open(os.path.join(templates_dir, "yearly_archive.html"), 'r', 'utf-8') as f:
            template = f.read()
        monthly_archives_match = _monthly_archives_re.search(template)
        header_template = template[:monthly_archives_match.start()]
        prev_archive_title = ''
        prev_archive_url = ''
        if prev_archive:
            prev_archive_title = '<'
            prev_archive_url = prev_archive.permalink
        next_archive_title = ''
        next_archive_url = ''
        if next_archive:
            next_archive_title = '>'
            next_archive_url = next_archive.permalink
        header = format(header_template, archive_title=self.year.strftime('%Y'), prev_archive_title=prev_archive_title, prev_archive_url=prev_archive_url, next_archive_title=next_archive_title, next_archive_url=next_archive_url)
        monthly_archive_template = monthly_archives_match.group(1)
        posts_match = _posts_re.search(monthly_archive_template)
        monthly_archive_header = monthly_archive_template[:posts_match.start()]
        post_template = posts_match.group(1)
        monthly_archive_footer = monthly_archive_template[posts_match.end():]
        monthly_archive_list = []
        for monthly_archive in self.monthly_archives:
            post_list = []
            for post in monthly_archive.posts:
                post_list.append(format(post_template, title=post.title, date=post.date.strftime('%Y-%m-%d'), pretty_date=post.pretty_date, permalink=post.permalink, excerpt=post.excerpt))
            monthly_archive_list.append(format(monthly_archive_header, monthly_archive_title=monthly_archive.month.strftime('%B'), monthly_archive_url=monthly_archive.permalink) + ''.join(post_list) + monthly_archive_footer)
        index = header + ''.join(monthly_archive_list) + template[monthly_archives_match.end():]
        return index

    def __str__(self):
        return '{year}\n{monthly_archives}'.format(year=self.year.strftime('%Y'), monthly_archives=self.monthly_archives)

    def __repr__(self):
        return str(self)

    def __gt__(self, other):
        return self.year > other.year

    def __lt__(self, other):
        return self.year < other.year

    def __ge__(self, other):
        return self.year >= other.year

    def __le__(self, other):
        return self.year <= other.year


class TimelineArchive(object):
    def __init__(self, index, posts):
        self.index = index
        self.posts = posts
        self.path = ('archive/' + str(index) + '/') if index > 0 else ''
        url_comps = urllib.parse.urlparse(posts[0].permalink)
        self.permalink = urllib.parse.urlunparse(url_comps[:2] + (self.path,) + (None,) * 3)

    def build_index(self, templates_dir, prev_archive=None, next_archive=None):
        with codecs.open(os.path.join(templates_dir, "index.html"), 'r', 'utf-8') as f:
            template = f.read()
        posts_match = _posts_re.search(template)
        footer_template = template[posts_match.end():]
        prev_archive_title = ''
        prev_archive_url = ''
        if prev_archive:
            prev_archive_title = '<'
            prev_archive_url = prev_archive.permalink
        next_archive_title = ''
        next_archive_url = ''
        if next_archive:
            next_archive_title = '>'
            next_archive_url = next_archive.permalink
        footer = format(footer_template, prev_archive_title=prev_archive_title, prev_archive_url=prev_archive_url, next_archive_title=next_archive_title, next_archive_url=next_archive_url)
        post_template = posts_match.group(1)
        post_list = []
        for post in self.posts:
            if not post:
                break
            post_list.append(format(post_template, title=post.title, date=post.date.strftime('%Y-%m-%d'), pretty_date=post.pretty_date, permalink=post.permalink, excerpt=post.excerpt))
        index = template[:posts_match.start()] + ''.join(post_list) + footer
        return index

    def __str__(self):
        return '{index}\n{posts}'.format(index=self.index, posts=self.posts)

    def __repr__(self):
        return str(self)

    def __gt__(self, other):
        return self.index > other.index

    def __lt__(self, other):

        return self.index < other.index

    def __ge__(self, other):
        return self.index >= other.index

    def __le__(self, other):
        return self.index <= other.index


class Struct(object):
    '''http://docs.python.org/3/tutorial/classes.html#odds-and-ends'''
    pass


_posts_re = re.compile(r'{{#posts}}(.*){{/posts}}', re.S)
_tags_re = re.compile(r'{{#tags}}(.*){{/tags}}', re.S)
_monthly_archives_re = re.compile(r'{{#monthly_archives}}(.*){{/monthly_archives}}', re.S)


def triplepwise(iterable):
    "s -> (s0,s1,s2, (s1,s2,s3), (s2,s3,s4), ..."
    a, b, c = itertools.tee(iterable, 3)
    next(b, None)
    next(c, None)
    next(c, None)
    return zip(a, b, c)


def grouper(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


posts = {}
timeline_archives = []
monthly_archives = {}
yearly_archives = {}
tags = {}


def main():
    # Command line arguments parsing
    cmdln_desc = 'A markdown based blog system.'
    if argparse:
        usage = " %(prog)s PUBLISHED_DIR"
        version = "%(prog)s " + __version__
        parser = argparse.ArgumentParser(prog="letterpress", description=cmdln_desc, formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("published_dir", metavar="PUBLISHED_DIR")
        parser.add_argument("-v", "--verbose", dest="log_level",
                                  action="store_const", const=logging.DEBUG,
                                  help="more verbose output")
        parser.add_argument("--version", action="version", version=version)
        parser.set_defaults(log_level=logging.INFO)
        options = parser.parse_args()
        published_dir = options.published_dir
    else:
        usage = " %prog PUBLISHED_DIR"
        version = "%prog " + __version__
        parser = optparse.OptionParser(prog="letterpress", usage=usage,
                                                 version=version, description=cmdln_desc)
        parser.add_option("-v", "--verbose", dest="log_level",
                                action="store_const", const=logging.DEBUG,
                                help="more verbose output")
        parser.set_defaults(log_level=logging.INFO)
        options, args = parser.parse_args()
        if len(args) != 1:
            parser.print_help()
            return
        published_dir = args[0]
    published_dir = os.path.normpath(published_dir)
    templates_dir = os.path.join(published_dir, 'templates')
    logger.setLevel(options.log_level)

    # Logging.
    logging_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging_formatter)
    log_file = 'letterpress.log'
    # file_handler = logging.handlers.TimedRotatingFileHandler(os.path.join(published_dir, 'letterpress.log'), when='D', interval=1, backupCount=7, utc=True)
    file_handler = logging.handlers.RotatingFileHandler(os.path.join(published_dir, log_file), maxBytes=64 * 1024, backupCount=3)
    file_handler.setFormatter(logging_formatter)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    # Letterpress config file parsing.
    config = {'markdown_ext': '.md'}
    with codecs.open(os.path.join(published_dir, 'letterpress.config'), 'r', 'utf-8') as config_file:
        for line in config_file.readlines():
            line = line.strip()
            if len(line) == 0 or line.startswith('#'):
                continue
            key, value = line.split(':', 1)
            config[key.strip()] = value.strip()
    logger.info('Site configure: %s', config)

    site_dir = config['site_dir']
    if not os.path.isabs(site_dir):
        site_dir = os.path.join(published_dir, os.path.expanduser(site_dir))
    site_dir = os.path.normpath(site_dir)

    # Clean up old files.
    for rel_path in os.listdir(site_dir):
        path = os.path.join(site_dir, rel_path)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.remove(path)
            except:
                logger.exception('Can not delete %s', path)

    # Initial complete site building.
    def create_post(file_path):
        post = Post(file_path, base_url=config['base_url'], templates_dir=templates_dir, date_format=config['date_format'], math_delimiter=config.get('math_delimiter', '$'))
        if not post:
            return None
        output_file_path = os.path.join(site_dir, post.path)
        output_dir = os.path.dirname(output_file_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with codecs.open(output_file_path, 'w', 'utf-8') as output_file:
            output_file.write(post.html)
        # html will never be used again. So let's get rid off it to spare some memory.
        del post.html
        return post

    def create_tags(posts):
        global tags
        tags.clear()
        posts_of_tags = {}
        sorted_posts = sorted(posts.values())
        for post in sorted_posts:
            for tag_name in post.tags:
                posts_of_tag = posts_of_tags.get(tag_name)
                if posts_of_tag:
                    posts_of_tag.append(post)
                else:
                    posts_of_tags[tag_name] = [post]
        for tag_name, tag_posts in posts_of_tags.items():
            tag = Tag(tag_name, tag_posts)
            tags[tag_name] = tag
            create_tag_index(tag)

        with codecs.open(os.path.join(templates_dir, "tags.html"), 'r', 'utf-8') as f:
            template = f.read()
        tags_match = _tags_re.search(template)
        tags_template = tags_match.group(1)
        tag_list = []
        for tag in sorted(tags.values()):
            post_count = len(tag.posts)
            tag_list.append(format(tags_template, tag_title=tag.name, tag_url=tag.permalink, tag_size=str(len(tag.posts)) + ' ' + ('Articles' if post_count > 1 else 'Article')))
        index = template[:tags_match.start()] + ''.join(tag_list) + template[tags_match.end():]
        output_dir = os.path.join(site_dir, 'tags')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file_path = os.path.join(output_dir, 'index.html')
        with codecs.open(output_file_path, 'w', 'utf-8') as output_file:
            output_file.write(index)

    def create_tag_index(tag):
        index = tag.build_index(templates_dir)
        output_dir = os.path.join(site_dir, tag.path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file_path = os.path.join(output_dir, 'index.html')
        with codecs.open(output_file_path, 'w', 'utf-8') as output_file:
            output_file.write(index)

    def create_timeline_archives(posts):
        global timeline_archives
        del timeline_archives[:]
        sorted_posts = sorted(posts.values(), reverse=True)
        archive_list = [None]
        for index, post_group in enumerate(grouper(5, sorted_posts)):
            archive = TimelineArchive(index, post_group)
            timeline_archives.append(archive)
            archive_list.append(archive)
        archive_list.append(None)
        for next_archive, archive, prev_archive in triplepwise(archive_list):
            create_timeline_index(archive, prev_archive, next_archive)

    def create_timeline_index(archive, prev_archive, next_archive):
        index = archive.build_index(templates_dir, prev_archive, next_archive)
        output_dir = os.path.join(site_dir, archive.path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file_path = os.path.join(output_dir, 'index.html')
        with codecs.open(output_file_path, 'w', 'utf-8') as output_file:
            output_file.write(index)

    def create_monthly_archives(posts):
        global monthly_archives
        monthly_archives.clear()
        archive_list = [None]
        month = datetime.date.min
        posts_of_month = []
        # Append a sentry to the end to make code below simpler.
        sentry = Struct()
        sentry.date = datetime.date.max
        sorted_posts = itertools.chain(sorted(posts.values()), [sentry])
        for post in sorted_posts:
            date_of_post = post.date
            month_of_post = datetime.date(date_of_post.year, date_of_post.month, 1)
            if month_of_post > month:
                if posts_of_month:
                    archive = MonthlyArchive(month, posts_of_month)
                    monthly_archives[month] = archive
                    archive_list.append(archive)
                month = month_of_post
                posts_of_month = [post]
            else:
                posts_of_month.append(post)
        archive_list.append(None)
        for prev_archive, archive, next_archive in triplepwise(archive_list):
            create_monthly_index(archive, prev_archive, next_archive)

    def create_monthly_index(archive, prev_archive, next_archive):
        index = archive.build_index(templates_dir, prev_archive, next_archive)
        output_dir = os.path.join(site_dir, archive.path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file_path = os.path.join(output_dir, 'index.html')
        with codecs.open(output_file_path, 'w', 'utf-8') as output_file:
            output_file.write(index)

    def create_yearly_archives(monthly_archives):
        global yearly_archives
        yearly_archives.clear()
        archive_list = [None]
        year = datetime.date.min
        archives_of_year = []
        # Append a sentry to the end to make code below simpler.
        sentry = Struct()
        sentry.month = datetime.date.max
        sorted_monthly_archives = itertools.chain(sorted(monthly_archives.values()), [sentry])
        for monthly_archive in sorted_monthly_archives:
            month_of_archive = monthly_archive.month
            year_of_archive = datetime.date(month_of_archive.year, 1, 1)
            if year_of_archive > year:
                if archives_of_year:
                    archive = YearlyArchive(year, archives_of_year)
                    yearly_archives[year] = archive
                    archive_list.append(archive)
                year = year_of_archive
                archives_of_year = [monthly_archive]
            else:
                archives_of_year.append(monthly_archive)
        archive_list.append(None)
        for prev_archive, archive, next_archive in triplepwise(archive_list):
            create_yearly_index(archive, prev_archive, next_archive)

    def create_yearly_index(archive, prev_archive, next_archive):
        index = archive.build_index(templates_dir, prev_archive, next_archive)
        output_dir = os.path.join(site_dir, archive.path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file_path = os.path.join(output_dir, 'index.html')
        with codecs.open(output_file_path, 'w', 'utf-8') as output_file:
            output_file.write(index)

    def create_complete_archive(monthly_archives):
        with codecs.open(os.path.join(templates_dir, "archive.html"), 'r', 'utf-8') as f:
            template = f.read()
        monthly_archives_match = _monthly_archives_re.search(template)
        monthly_archive_template = monthly_archives_match.group(1)
        posts_match = _posts_re.search(monthly_archive_template)
        monthly_archive_header = monthly_archive_template[:posts_match.start()]
        post_template = posts_match.group(1)
        monthly_archive_footer = monthly_archive_template[posts_match.end():]
        monthly_archive_list = []
        for monthly_archive in sorted(monthly_archives.values(), reverse=True):
            post_list = []
            for post in reversed(monthly_archive.posts):
                post_list.append(format(post_template, title=post.title, date=post.date.strftime('%Y-%m-%d'), pretty_date=post.pretty_date, permalink=post.permalink, excerpt=post.excerpt))
            monthly_archive_list.append(format(monthly_archive_header, monthly_archive_title=monthly_archive.month.strftime('%B, %Y'), monthly_archive_url=monthly_archive.permalink) + ''.join(post_list) + monthly_archive_footer)
        index = template[:monthly_archives_match.start()] + ''.join(monthly_archive_list) + template[monthly_archives_match.end():]
        output_dir = os.path.join(site_dir, 'archive')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file_path = os.path.join(output_dir, 'index.html')
        with codecs.open(output_file_path, 'w', 'utf-8') as output_file:
            output_file.write(index)

    def build_site():
        logger.info('Build site')
        global posts
        posts.clear()
        for rel_path in os.listdir(published_dir):
            path = os.path.join(published_dir, rel_path)
            basename = os.path.basename(path)
            if os.path.splitext(basename)[1] == config['markdown_ext']:
                # Post.
                post = create_post(path)
                if post:
                    posts[post.file_path] = post
            elif basename == 'letterpress.config':
                pass
            elif os.path.normpath(path) == templates_dir:
                pass
            elif basename.startswith(log_file) or basename.startswith('.'):
                pass
            else:
                # Resource.
                if site_dir == published_dir:
                    continue
                dst = os.path.join(site_dir, basename)
                if os.path.isdir(path):
                    if os.path.exists(dst):
                        shutil.rmtree(dst, ignore_errors=True)
                    try:
                        shutil.copytree(path, dst)
                    except Exception as e:
                        logger.error(e)
                else:
                    try:
                        shutil.copyfile(path, dst)
                    except Exception as e:
                        logger.error(e)
        create_tags(posts)
        create_timeline_archives(posts)
        create_monthly_archives(posts)
        create_yearly_archives(monthly_archives)
        create_complete_archive(monthly_archives)

    build_site()

    # Continuous posts monitoring and site building.
    class ResourceChangeHandler(pyinotify.PrintAllEvents):
        def process_default(self, event):
            if event.name.startswith(log_file):
                return
            # super(ResourceChangeHandler, self).process_default(event)
            file_create_mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO
            dir_create_mask = pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO
            delete_mask = pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM
            path = os.path.normpath(event.path)
            if path == published_dir:
                if not event.dir:
                    if os.path.basename(event.pathname) == 'letterpress.config':
                        # Configure file changed. Rebuild the whole site.
                        if event.mask & file_create_mask:
                            logger.info('New site configure')
                            build_site()
                        return
                    elif os.path.splitext(event.pathname)[1] == config['markdown_ext']:
                        if event.mask & file_create_mask:
                            # New post or post changed.
                            post = create_post(event.pathname)
                            if not post:
                                return
                            if post.file_path in posts:
                                logger.info('Update post: %s', os.path.basename(event.pathname))
                            else:
                                logger.info('New post: %s', os.path.basename(event.pathname))
                            posts[post.file_path] = post
                            create_tags(posts)
                            create_timeline_archives(posts)
                            create_monthly_archives(posts)
                            create_yearly_archives(monthly_archives)
                            create_complete_archive(monthly_archives)
                        elif event.mask & delete_mask:
                            # Delete post.
                            logger.info('Delete post: %s', os.path.basename(event.pathname))
                            post = posts.pop(event.pathname, None)
                            if post:
                                dst = os.path.join(site_dir, post.path)
                                if os.path.exists(dst):
                                    try:
                                        os.remove(dst)
                                    except:
                                        logger.exception('Can not delete %s', dst)
                                for tag_name in post.tags:
                                    tag = tags.get(tag_name)
                                    if tag:
                                        try:
                                            tag.posts.remove(post)
                                        except:
                                            pass
                                        if not tag.posts:
                                            # The tag is empty now. Remove it.
                                            tags.pop(tag_name, None)
                                            dst = os.path.join(site_dir, tag.path)
                                            if os.path.exists(dst):
                                                shutil.rmtree(dst, ignore_errors=True)
                                if len(posts) % 5 == 0 and len(timeline_archives) > 1:
                                    # Last timeline archive is empty. Remove it.
                                    last_timeline_archive = timeline_archives.pop()
                                    dst = os.path.join(site_dir, last_timeline_archive.path)
                                    if os.path.exists(dst):
                                        shutil.rmtree(dst, ignore_errors=True)

                                monthly_archive = monthly_archives.get(datetime.date(post.date.year, post.date.month, 1))
                                if monthly_archive:
                                    try:
                                        monthly_archive.posts.remove(post)
                                    except:
                                        pass
                                    if not monthly_archive.posts:
                                        # The month is empty now. Remove it.
                                        monthly_archives.pop(monthly_archive.month, None)
                                        dst = os.path.join(site_dir, monthly_archive.path)
                                        if os.path.exists(dst):
                                            shutil.rmtree(dst, ignore_errors=True)
                                        yearly_archive = yearly_archives.get(datetime.date(monthly_archive.month.year, 1, 1))
                                        if yearly_archive:
                                            try:
                                                yearly_archive.monthly_archives.remove(monthly_archive)
                                            except:
                                                pass
                                            if not yearly_archive.monthly_archives:
                                                # The year is empty now. Remove it.
                                                yearly_archives.pop(yearly_archive.year, None)
                                                dst = os.path.join(site_dir, yearly_archive.path)
                                                if os.path.exists(dst):
                                                    shutil.rmtree(dst, ignore_errors=True)

                                create_tags(posts)
                                create_timeline_archives(posts)
                                create_monthly_archives(posts)
                                create_yearly_archives(monthly_archives)
                                create_complete_archive(monthly_archives)
                        return
            elif path == templates_dir:
                # Template changed. Rebuild the whole site.
                if event.mask & file_create_mask and os.path.splitext(event.pathname)[1] == '.html':
                    logger.info('Update template: %s', os.path.basename(event.pathname))
                    build_site()
                return
            # Map other resource changes into site dir.
            if site_dir == published_dir:
                return
            if os.path.basename(event.pathname).startswith('.'):
                # Ignore hidden/temp files
                return
            rel_path = os.path.relpath(event.pathname, published_dir)
            dst = os.path.join(site_dir, rel_path)
            if event.dir:
                if event.mask & dir_create_mask:
                    logger.info('New resource dir: %s', rel_path)
                    if os.path.exists(dst):
                        shutil.rmtree(dst, ignore_errors=True)
                    try:
                        shutil.copytree(event.pathname, dst)
                    except Exception as e:
                        logger.error(e)
                elif event.mask & delete_mask:
                    logger.info('Delete resource dir: %s', rel_path)
                    if os.path.exists(dst):
                        shutil.rmtree(dst, ignore_errors=True)
            else:
                if event.mask & file_create_mask:
                    logger.info('New resource file: %s', rel_path)
                    try:
                        shutil.copyfile(event.pathname, dst)
                    except Exception as e:
                        logger.error(e)
                elif event.mask & delete_mask:
                    logger.info('Delete resource file: %s', rel_path)
                    if os.path.exists(dst):
                        try:
                            os.remove(dst)
                        except:
                            logger.exception('Can not delete %s', dst)

    wm = pyinotify.WatchManager()
    mask = pyinotify.ALL_EVENTS
    notifier = pyinotify.Notifier(wm)
    wm.add_watch(published_dir, mask, proc_fun=ResourceChangeHandler(), rec=True, auto_add=True)
    notifier.loop()


if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = markdown2
#!/usr/bin/env python
# Copyright (c) 2012 Trent Mick.
# Copyright (c) 2007-2008 ActiveState Corp.
# License: MIT (http://www.opensource.org/licenses/mit-license.php)

from __future__ import generators

r"""A fast and complete Python implementation of Markdown.

[from http://daringfireball.net/projects/markdown/]
> Markdown is a text-to-HTML filter; it translates an easy-to-read /
> easy-to-write structured text format into HTML.  Markdown's text
> format is most similar to that of plain text email, and supports
> features such as headers, *emphasis*, code blocks, blockquotes, and
> links.
>
> Markdown's syntax is designed not as a generic markup language, but
> specifically to serve as a front-end to (X)HTML. You can use span-level
> HTML tags anywhere in a Markdown document, and you can use block level
> HTML tags (like <div> and <table> as well).

Module usage:

    >>> import markdown2
    >>> markdown2.markdown("*boo!*")  # or use `html = markdown_path(PATH)`
    u'<p><em>boo!</em></p>\n'

    >>> markdowner = Markdown()
    >>> markdowner.convert("*boo!*")
    u'<p><em>boo!</em></p>\n'
    >>> markdowner.convert("**boom!**")
    u'<p><strong>boom!</strong></p>\n'

This implementation of Markdown implements the full "core" syntax plus a
number of extras (e.g., code syntax coloring, footnotes) as described on
<https://github.com/trentm/python-markdown2/wiki/Extras>.
"""

cmdln_desc = """A fast and complete Python implementation of Markdown, a
text-to-HTML conversion tool for web writers.

Supported extra syntax options (see -x|--extras option below and
see <https://github.com/trentm/python-markdown2/wiki/Extras> for details):

* code-friendly: Disable _ and __ for em and strong.
* cuddled-lists: Allow lists to be cuddled to the preceding paragraph.
* fenced-code-blocks: Allows a code block to not have to be indented
  by fencing it with '```' on a line before and after. Based on
  <http://github.github.com/github-flavored-markdown/> with support for
  syntax highlighting.
* footnotes: Support footnotes as in use on daringfireball.net and
  implemented in other Markdown processors (tho not in Markdown.pl v1.0.1).
* header-ids: Adds "id" attributes to headers. The id value is a slug of
  the header text.
* html-classes: Takes a dict mapping html tag names (lowercase) to a
  string to use for a "class" tag attribute. Currently only supports
  "pre" and "code" tags. Add an issue if you require this for other tags.
* markdown-in-html: Allow the use of `markdown="1"` in a block HTML tag to
  have markdown processing be done on its contents. Similar to
  <http://michelf.com/projects/php-markdown/extra/#markdown-attr> but with
  some limitations.
* metadata: Extract metadata from a leading '---'-fenced block.
  See <https://github.com/trentm/python-markdown2/issues/77> for details.
* nofollow: Add `rel="nofollow"` to add `<a>` tags with an href. See
  <http://en.wikipedia.org/wiki/Nofollow>.
* pyshell: Treats unindented Python interactive shell sessions as <code>
  blocks.
* link-patterns: Auto-link given regex patterns in text (e.g. bug number
  references, revision number references).
* smarty-pants: Replaces ' and " with curly quotation marks or curly
  apostrophes.  Replaces --, ---, ..., and . . . with en dashes, em dashes,
  and ellipses.
* toc: The returned HTML string gets a new "toc_html" attribute which is
  a Table of Contents for the document. (experimental)
* xml: Passes one-liner processing instructions and namespaced XML tags.
* wiki-tables: Google Code Wiki-style tables. See
  <http://code.google.com/p/support/wiki/WikiSyntax#Tables>.
"""

# Dev Notes:
# - Python's regex syntax doesn't have '\z', so I'm using '\Z'. I'm
#   not yet sure if there implications with this. Compare 'pydoc sre'
#   and 'perldoc perlre'.

__version_info__ = (2, 1, 1)
__version__ = '.'.join(map(str, __version_info__))
__author__ = "Trent Mick"

import os
import sys
from pprint import pprint
import re
import logging
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import optparse
from random import random, randint
import codecs


#---- Python version compat

try:
    from urllib.parse import quote # python3
except ImportError:
    from urllib import quote # python2

if sys.version_info[:2] < (2,4):
    from sets import Set as set
    def reversed(sequence):
        for i in sequence[::-1]:
            yield i

# Use `bytes` for byte strings and `unicode` for unicode strings (str in Py3).
if sys.version_info[0] <= 2:
    py3 = False
    try:
        bytes
    except NameError:
        bytes = str
    base_string_type = basestring
elif sys.version_info[0] >= 3:
    py3 = True
    unicode = str
    base_string_type = str



#---- globals

DEBUG = False
log = logging.getLogger("markdown")

DEFAULT_TAB_WIDTH = 4


SECRET_SALT = bytes(randint(0, 1000000))
def _hash_text(s):
    return 'md5-' + md5(SECRET_SALT + s.encode("utf-8")).hexdigest()

# Table of hash values for escaped characters:
g_escape_table = dict([(ch, _hash_text(ch))
    for ch in '\\`*_{}[]()>#+-.!'])



#---- exceptions

class MarkdownError(Exception):
    pass



#---- public api

def markdown_path(path, encoding="utf-8",
                  html4tags=False, tab_width=DEFAULT_TAB_WIDTH,
                  safe_mode=None, extras=None, link_patterns=None,
                  use_file_vars=False):
    fp = codecs.open(path, 'r', encoding)
    text = fp.read()
    fp.close()
    return Markdown(html4tags=html4tags, tab_width=tab_width,
                    safe_mode=safe_mode, extras=extras,
                    link_patterns=link_patterns,
                    use_file_vars=use_file_vars).convert(text)

def markdown(text, html4tags=False, tab_width=DEFAULT_TAB_WIDTH,
             safe_mode=None, extras=None, link_patterns=None,
             use_file_vars=False):
    return Markdown(html4tags=html4tags, tab_width=tab_width,
                    safe_mode=safe_mode, extras=extras,
                    link_patterns=link_patterns,
                    use_file_vars=use_file_vars).convert(text)

class Markdown(object):
    # The dict of "extras" to enable in processing -- a mapping of
    # extra name to argument for the extra. Most extras do not have an
    # argument, in which case the value is None.
    #
    # This can be set via (a) subclassing and (b) the constructor
    # "extras" argument.
    extras = None

    urls = None
    titles = None
    html_blocks = None
    html_spans = None
    math_spans = None
    html_removed_text = "[HTML_REMOVED]"  # for compat with markdown.py

    # Used to track when we're inside an ordered or unordered list
    # (see _ProcessListItems() for details):
    list_level = 0

    _ws_only_line_re = re.compile(r"^[ \t]+$", re.M)

    def __init__(self, html4tags=False, tab_width=4, safe_mode=None,
                 extras=None, link_patterns=None, use_file_vars=False):
        if html4tags:
            self.empty_element_suffix = ">"
        else:
            self.empty_element_suffix = " />"
        self.tab_width = tab_width

        # For compatibility with earlier markdown2.py and with
        # markdown.py's safe_mode being a boolean,
        #   safe_mode == True -> "replace"
        if safe_mode is True:
            self.safe_mode = "replace"
        else:
            self.safe_mode = safe_mode

        # Massaging and building the "extras" info.
        if self.extras is None:
            self.extras = {}
        elif not isinstance(self.extras, dict):
            self.extras = dict([(e, None) for e in self.extras])
        if extras:
            if not isinstance(extras, dict):
                extras = dict([(e, None) for e in extras])
            self.extras.update(extras)
        assert isinstance(self.extras, dict)
        if "toc" in self.extras and not "header-ids" in self.extras:
            self.extras["header-ids"] = None   # "toc" implies "header-ids"
        self._instance_extras = self.extras.copy()

        self.link_patterns = link_patterns
        self.use_file_vars = use_file_vars
        self._outdent_re = re.compile(r'^(\t|[ ]{1,%d})' % tab_width, re.M)

        self._escape_table = g_escape_table.copy()
        if "smarty-pants" in self.extras:
            self._escape_table['"'] = _hash_text('"')
            self._escape_table["'"] = _hash_text("'")

    def reset(self):
        self.urls = {}
        self.titles = {}
        self.html_blocks = {}
        self.html_spans = {}
        self.math_spans = {}
        self.list_level = 0
        self.extras = self._instance_extras.copy()
        if "footnotes" in self.extras:
            self.footnotes = {}
            self.footnote_ids = []
            self.inline_footnote_id = 0
        if "header-ids" in self.extras:
            self._count_from_header_id = {} # no `defaultdict` in Python 2.4
        if "metadata" in self.extras:
            self.metadata = {}

    # Per <https://developer.mozilla.org/en-US/docs/HTML/Element/a> "rel"
    # should only be used in <a> tags with an "href" attribute.
    _a_nofollow = re.compile(r"<(a)([^>]*href=)", re.IGNORECASE)

    def convert(self, text):
        """Convert the given text."""
        # Main function. The order in which other subs are called here is
        # essential. Link and image substitutions need to happen before
        # _EscapeSpecialChars(), so that any *'s or _'s in the <a>
        # and <img> tags get encoded.

        # Clear the global hashes. If we don't clear these, you get conflicts
        # from other articles when generating a page which contains more than
        # one article (e.g. an index page that shows the N most recent
        # articles):
        self.reset()

        if not isinstance(text, unicode):
            #TODO: perhaps shouldn't presume UTF-8 for string input?
            text = unicode(text, 'utf-8')

        if self.use_file_vars:
            # Look for emacs-style file variable hints.
            emacs_vars = self._get_emacs_vars(text)
            if "markdown-extras" in emacs_vars:
                splitter = re.compile("[ ,]+")
                for e in splitter.split(emacs_vars["markdown-extras"]):
                    if '=' in e:
                        ename, earg = e.split('=', 1)
                        try:
                            earg = int(earg)
                        except ValueError:
                            pass
                    else:
                        ename, earg = e, None
                    self.extras[ename] = earg

        # Standardize line endings:
        text = re.sub("\r\n|\r", "\n", text)

        # Make sure $text ends with a couple of newlines:
        text += "\n\n"

        # Convert all tabs to spaces.
        text = self._detab(text)

        # Strip any lines consisting only of spaces and tabs.
        # This makes subsequent regexen easier to write, because we can
        # match consecutive blank lines with /\n+/ instead of something
        # contorted like /[ \t]*\n+/ .
        text = self._ws_only_line_re.sub("", text)

        # strip metadata from head and extract
        if "metadata" in self.extras:
            text = self._extract_metadata(text)

        text = self.preprocess(text)

        if self.extras.get("math_delimiter"):
            text = self._hash_math_spans(text)
        
        if self.safe_mode:
            text = self._hash_html_spans(text)

        # Turn block-level HTML blocks into hash entries
        text = self._hash_html_blocks(text, raw=True)

        if "fenced-code-blocks" in self.extras:
            text = self._do_fenced_code_blocks(text)
            text = self._hash_html_blocks(text)

        # Strip link definitions, store in hashes.
        if "footnotes" in self.extras:
            # Must do footnotes first because an unlucky footnote defn
            # looks like a link defn:
            #   [^4]: this "looks like a link defn"
            text = self._strip_footnote_definitions(text)
            text = self._strip_inline_footnotes(text)
        text = self._strip_link_definitions(text)

        text = self._run_block_gamut(text)

        if "footnotes" in self.extras:
            text = self._sort_footnotes(text)
            text = self._add_footnotes(text)

        text = self.postprocess(text)

        text = self._unescape_special_chars(text)

        if self.safe_mode:
            text = self._unhash_html_spans(text)

        if self.extras.get("math_delimiter"):
            text = self._unhash_math_spans(text)

        if "nofollow" in self.extras:
            text = self._a_nofollow.sub(r'<\1 rel="nofollow"\2', text)

        text += "\n"

        rv = UnicodeWithAttrs(text)
        if "toc" in self.extras:
            rv._toc = self._toc
        if "metadata" in self.extras:
            rv.metadata = self.metadata
        return rv

    def postprocess(self, text):
        """A hook for subclasses to do some postprocessing of the html, if
        desired. This is called before unescaping of special chars and
        unhashing of raw HTML spans.
        """
        return text

    def preprocess(self, text):
        """A hook for subclasses to do some preprocessing of the Markdown, if
        desired. This is called after basic formatting of the text, but prior
        to any extras, safe mode, etc. processing.
        """
        return text

    # Is metadata if the content starts with '---'-fenced `key: value`
    # pairs. E.g. (indented for presentation):
    #   ---
    #   foo: bar
    #   another-var: blah blah
    #   ---
    _metadata_pat = re.compile("""^---[ \t]*\n((?:[ \t]*[^ \t:]+[ \t]*:[^\n]*\n)+)---[ \t]*\n""")

    def _extract_metadata(self, text):
        # fast test
        if not text.startswith("---"):
            return text
        match = self._metadata_pat.match(text)
        if not match:
            return text

        tail = text[len(match.group(0)):]
        metadata_str = match.group(1).strip()
        for line in metadata_str.split('\n'):
            key, value = line.split(':', 1)
            self.metadata[key.strip()] = value.strip()

        return tail


    _emacs_oneliner_vars_pat = re.compile(r"-\*-\s*([^\r\n]*?)\s*-\*-", re.UNICODE)
    # This regular expression is intended to match blocks like this:
    #    PREFIX Local Variables: SUFFIX
    #    PREFIX mode: Tcl SUFFIX
    #    PREFIX End: SUFFIX
    # Some notes:
    # - "[ \t]" is used instead of "\s" to specifically exclude newlines
    # - "(\r\n|\n|\r)" is used instead of "$" because the sre engine does
    #   not like anything other than Unix-style line terminators.
    _emacs_local_vars_pat = re.compile(r"""^
        (?P<prefix>(?:[^\r\n|\n|\r])*?)
        [\ \t]*Local\ Variables:[\ \t]*
        (?P<suffix>.*?)(?:\r\n|\n|\r)
        (?P<content>.*?\1End:)
        """, re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)

    def _get_emacs_vars(self, text):
        """Return a dictionary of emacs-style local variables.

        Parsing is done loosely according to this spec (and according to
        some in-practice deviations from this):
        http://www.gnu.org/software/emacs/manual/html_node/emacs/Specifying-File-Variables.html#Specifying-File-Variables
        """
        emacs_vars = {}
        SIZE = pow(2, 13) # 8kB

        # Search near the start for a '-*-'-style one-liner of variables.
        head = text[:SIZE]
        if "-*-" in head:
            match = self._emacs_oneliner_vars_pat.search(head)
            if match:
                emacs_vars_str = match.group(1)
                assert '\n' not in emacs_vars_str
                emacs_var_strs = [s.strip() for s in emacs_vars_str.split(';')
                                  if s.strip()]
                if len(emacs_var_strs) == 1 and ':' not in emacs_var_strs[0]:
                    # While not in the spec, this form is allowed by emacs:
                    #   -*- Tcl -*-
                    # where the implied "variable" is "mode". This form
                    # is only allowed if there are no other variables.
                    emacs_vars["mode"] = emacs_var_strs[0].strip()
                else:
                    for emacs_var_str in emacs_var_strs:
                        try:
                            variable, value = emacs_var_str.strip().split(':', 1)
                        except ValueError:
                            log.debug("emacs variables error: malformed -*- "
                                      "line: %r", emacs_var_str)
                            continue
                        # Lowercase the variable name because Emacs allows "Mode"
                        # or "mode" or "MoDe", etc.
                        emacs_vars[variable.lower()] = value.strip()

        tail = text[-SIZE:]
        if "Local Variables" in tail:
            match = self._emacs_local_vars_pat.search(tail)
            if match:
                prefix = match.group("prefix")
                suffix = match.group("suffix")
                lines = match.group("content").splitlines(0)
                #print "prefix=%r, suffix=%r, content=%r, lines: %s"\
                #      % (prefix, suffix, match.group("content"), lines)

                # Validate the Local Variables block: proper prefix and suffix
                # usage.
                for i, line in enumerate(lines):
                    if not line.startswith(prefix):
                        log.debug("emacs variables error: line '%s' "
                                  "does not use proper prefix '%s'"
                                  % (line, prefix))
                        return {}
                    # Don't validate suffix on last line. Emacs doesn't care,
                    # neither should we.
                    if i != len(lines)-1 and not line.endswith(suffix):
                        log.debug("emacs variables error: line '%s' "
                                  "does not use proper suffix '%s'"
                                  % (line, suffix))
                        return {}

                # Parse out one emacs var per line.
                continued_for = None
                for line in lines[:-1]: # no var on the last line ("PREFIX End:")
                    if prefix: line = line[len(prefix):] # strip prefix
                    if suffix: line = line[:-len(suffix)] # strip suffix
                    line = line.strip()
                    if continued_for:
                        variable = continued_for
                        if line.endswith('\\'):
                            line = line[:-1].rstrip()
                        else:
                            continued_for = None
                        emacs_vars[variable] += ' ' + line
                    else:
                        try:
                            variable, value = line.split(':', 1)
                        except ValueError:
                            log.debug("local variables error: missing colon "
                                      "in local variables entry: '%s'" % line)
                            continue
                        # Do NOT lowercase the variable name, because Emacs only
                        # allows "mode" (and not "Mode", "MoDe", etc.) in this block.
                        value = value.strip()
                        if value.endswith('\\'):
                            value = value[:-1].rstrip()
                            continued_for = variable
                        else:
                            continued_for = None
                        emacs_vars[variable] = value

        # Unquote values.
        for var, val in list(emacs_vars.items()):
            if len(val) > 1 and (val.startswith('"') and val.endswith('"')
               or val.startswith('"') and val.endswith('"')):
                emacs_vars[var] = val[1:-1]

        return emacs_vars

    # Cribbed from a post by Bart Lateur:
    # <http://www.nntp.perl.org/group/perl.macperl.anyperl/154>
    _detab_re = re.compile(r'(.*?)\t', re.M)
    def _detab_sub(self, match):
        g1 = match.group(1)
        return g1 + (' ' * (self.tab_width - len(g1) % self.tab_width))
    def _detab(self, text):
        r"""Remove (leading?) tabs from a file.

            >>> m = Markdown()
            >>> m._detab("\tfoo")
            '    foo'
            >>> m._detab("  \tfoo")
            '    foo'
            >>> m._detab("\t  foo")
            '      foo'
            >>> m._detab("  foo")
            '  foo'
            >>> m._detab("  foo\n\tbar\tblam")
            '  foo\n    bar blam'
        """
        if '\t' not in text:
            return text
        return self._detab_re.subn(self._detab_sub, text)[0]

    # I broke out the html5 tags here and add them to _block_tags_a and
    # _block_tags_b.  This way html5 tags are easy to keep track of.
    _html5tags = '|article|aside|header|hgroup|footer|nav|section|figure|figcaption'

    _block_tags_a = 'p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math|ins|del'
    _block_tags_a += _html5tags

    _strict_tag_block_re = re.compile(r"""
        (                       # save in \1
            ^                   # start of line  (with re.M)
            <(%s)               # start tag = \2
            \b                  # word break
            (.*\n)*?            # any number of lines, minimally matching
            </\2>               # the matching end tag
            [ \t]*              # trailing spaces/tabs
            (?=\n+|\Z)          # followed by a newline or end of document
        )
        """ % _block_tags_a,
        re.X | re.M)

    _block_tags_b = 'p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math'
    _block_tags_b += _html5tags

    _liberal_tag_block_re = re.compile(r"""
        (                       # save in \1
            ^                   # start of line  (with re.M)
            <(%s)               # start tag = \2
            \b                  # word break
            (.*\n)*?            # any number of lines, minimally matching
            .*</\2>             # the matching end tag
            [ \t]*              # trailing spaces/tabs
            (?=\n+|\Z)          # followed by a newline or end of document
        )
        """ % _block_tags_b,
        re.X | re.M)

    _html_markdown_attr_re = re.compile(
        r'''\s+markdown=("1"|'1')''')
    def _hash_html_block_sub(self, match, raw=False):
        html = match.group(1)
        if raw and self.safe_mode:
            html = self._sanitize_html(html)
        elif 'markdown-in-html' in self.extras and 'markdown=' in html:
            first_line = html.split('\n', 1)[0]
            m = self._html_markdown_attr_re.search(first_line)
            if m:
                lines = html.split('\n')
                middle = '\n'.join(lines[1:-1])
                last_line = lines[-1]
                first_line = first_line[:m.start()] + first_line[m.end():]
                f_key = _hash_text(first_line)
                self.html_blocks[f_key] = first_line
                l_key = _hash_text(last_line)
                self.html_blocks[l_key] = last_line
                return ''.join(["\n\n", f_key,
                    "\n\n", middle, "\n\n",
                    l_key, "\n\n"])
        key = _hash_text(html)
        self.html_blocks[key] = html
        return "\n\n" + key + "\n\n"

    def _hash_html_blocks(self, text, raw=False):
        """Hashify HTML blocks

        We only want to do this for block-level HTML tags, such as headers,
        lists, and tables. That's because we still want to wrap <p>s around
        "paragraphs" that are wrapped in non-block-level tags, such as anchors,
        phrase emphasis, and spans. The list of tags we're looking for is
        hard-coded.

        @param raw {boolean} indicates if these are raw HTML blocks in
            the original source. It makes a difference in "safe" mode.
        """
        if '<' not in text:
            return text

        # Pass `raw` value into our calls to self._hash_html_block_sub.
        hash_html_block_sub = _curry(self._hash_html_block_sub, raw=raw)

        # First, look for nested blocks, e.g.:
        #   <div>
        #       <div>
        #       tags for inner block must be indented.
        #       </div>
        #   </div>
        #
        # The outermost tags must start at the left margin for this to match, and
        # the inner nested divs must be indented.
        # We need to do this before the next, more liberal match, because the next
        # match will start at the first `<div>` and stop at the first `</div>`.
        text = self._strict_tag_block_re.sub(hash_html_block_sub, text)

        # Now match more liberally, simply from `\n<tag>` to `</tag>\n`
        text = self._liberal_tag_block_re.sub(hash_html_block_sub, text)

        # Special case just for <hr />. It was easier to make a special
        # case than to make the other regex more complicated.
        if "<hr" in text:
            _hr_tag_re = _hr_tag_re_from_tab_width(self.tab_width)
            text = _hr_tag_re.sub(hash_html_block_sub, text)

        # Special case for standalone HTML comments:
        if "<!--" in text:
            start = 0
            while True:
                # Delimiters for next comment block.
                try:
                    start_idx = text.index("<!--", start)
                except ValueError:
                    break
                try:
                    end_idx = text.index("-->", start_idx) + 3
                except ValueError:
                    break

                # Start position for next comment block search.
                start = end_idx

                # Validate whitespace before comment.
                if start_idx:
                    # - Up to `tab_width - 1` spaces before start_idx.
                    for i in range(self.tab_width - 1):
                        if text[start_idx - 1] != ' ':
                            break
                        start_idx -= 1
                        if start_idx == 0:
                            break
                    # - Must be preceded by 2 newlines or hit the start of
                    #   the document.
                    if start_idx == 0:
                        pass
                    elif start_idx == 1 and text[0] == '\n':
                        start_idx = 0  # to match minute detail of Markdown.pl regex
                    elif text[start_idx-2:start_idx] == '\n\n':
                        pass
                    else:
                        break

                # Validate whitespace after comment.
                # - Any number of spaces and tabs.
                while end_idx < len(text):
                    if text[end_idx] not in ' \t':
                        break
                    end_idx += 1
                # - Must be following by 2 newlines or hit end of text.
                if text[end_idx:end_idx+2] not in ('', '\n', '\n\n'):
                    continue

                # Escape and hash (must match `_hash_html_block_sub`).
                html = text[start_idx:end_idx]
                if raw and self.safe_mode:
                    html = self._sanitize_html(html)
                key = _hash_text(html)
                self.html_blocks[key] = html
                text = text[:start_idx] + "\n\n" + key + "\n\n" + text[end_idx:]

        if "xml" in self.extras:
            # Treat XML processing instructions and namespaced one-liner
            # tags as if they were block HTML tags. E.g., if standalone
            # (i.e. are their own paragraph), the following do not get
            # wrapped in a <p> tag:
            #    <?foo bar?>
            #
            #    <xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="chapter_1.md"/>
            _xml_oneliner_re = _xml_oneliner_re_from_tab_width(self.tab_width)
            text = _xml_oneliner_re.sub(hash_html_block_sub, text)

        return text

    def _strip_link_definitions(self, text):
        # Strips link definitions from text, stores the URLs and titles in
        # hash references.
        less_than_tab = self.tab_width - 1

        # Link defs are in the form:
        #   [id]: url "optional title"
        _link_def_re = re.compile(r"""
            ^[ ]{0,%d}\[(.+)\]: # id = \1
              [ \t]*
              \n?               # maybe *one* newline
              [ \t]*
            <?(.+?)>?           # url = \2
              [ \t]*
            (?:
                \n?             # maybe one newline
                [ \t]*
                (?<=\s)         # lookbehind for whitespace
                ['"(]
                ([^\n]*)        # title = \3
                ['")]
                [ \t]*
            )?  # title is optional
            (?:\n+|\Z)
            """ % less_than_tab, re.X | re.M | re.U)
        return _link_def_re.sub(self._extract_link_def_sub, text)

    def _extract_link_def_sub(self, match):
        id, url, title = match.groups()
        key = id.lower()    # Link IDs are case-insensitive
        self.urls[key] = self._encode_amps_and_angles(url)
        if title:
            self.titles[key] = title
        return ""

    def _extract_footnote_def_sub(self, match):
        id, text = match.groups()
        text = _dedent(text, skip_first_line=not text.startswith('\n')).strip()
        normed_id = re.sub(r'\W', '-', id)
        # Ensure footnote text ends with a couple newlines (for some
        # block gamut matches).
        self.footnotes[normed_id] = text + "\n\n"
        return ""

    def _strip_footnote_definitions(self, text):
        """A footnote definition looks like this:

            [^note-id]: Text of the note.

                May include one or more indented paragraphs.

        Where,
        - The 'note-id' can be pretty much anything, though typically it
          is the number of the footnote.
        - The first paragraph may start on the next line, like so:

            [^note-id]:
                Text of the note.
        """
        less_than_tab = self.tab_width - 1
        footnote_def_re = re.compile(r'''
            ^[ ]{0,%d}\[\^(.+)\]:   # id = \1
            [ \t]*
            (                       # footnote text = \2
              # First line need not start with the spaces.
              (?:\s*.*\n+)
              (?:
                (?:[ ]{%d} | \t)  # Subsequent lines must be indented.
                .*\n+
              )*
            )
            # Lookahead for non-space at line-start, or end of doc.
            (?:(?=^[ ]{0,%d}\S)|\Z)
            ''' % (less_than_tab, self.tab_width, self.tab_width),
            re.X | re.M)
        return footnote_def_re.sub(self._extract_footnote_def_sub, text)

    def _extract_inline_footnote_sub(self, match):
        text = match.group(1).strip()
        self.inline_footnote_id += 1
        # Ensure footnote text ends with a couple newlines (for some
        # block gamut matches).
        self.footnotes[str(self.inline_footnote_id)] = text + "\n\n"
        # Transform it into [^id] so that it can be processed as markdown footnote.
        return '[^%d]' % self.inline_footnote_id

    def _strip_inline_footnotes(self, text):
        """An inline footnote looks like this:

            main text(^inline footnote)
        """
        _inline_footnote_re = re.compile(r'\(\^(.+?)\)')
        return _inline_footnote_re.sub(self._extract_inline_footnote_sub, text)

    _hr_data = [
        ('*', re.compile(r"^[ ]{0,3}\*(.*?)$", re.M)),
        ('-', re.compile(r"^[ ]{0,3}\-(.*?)$", re.M)),
        ('_', re.compile(r"^[ ]{0,3}\_(.*?)$", re.M)),
    ]

    def _run_block_gamut(self, text):
        # These are all the transformations that form block-level
        # tags like paragraphs, headers, and list items.
        text = self._do_headers(text)

        # Do Horizontal Rules:
        # On the number of spaces in horizontal rules: The spec is fuzzy: "If
        # you wish, you may use spaces between the hyphens or asterisks."
        # Markdown.pl 1.0.1's hr regexes limit the number of spaces between the
        # hr chars to one or two. We'll reproduce that limit here.
        hr = "\n<hr"+self.empty_element_suffix+"\n"
        for ch, regex in self._hr_data:
            if ch in text:
                for m in reversed(list(regex.finditer(text))):
                    tail = m.group(1).rstrip()
                    if not tail.strip(ch + ' ') and tail.count("   ") == 0:
                        start, end = m.span()
                        text = text[:start] + hr + text[end:]

        text = self._do_lists(text)

        if "pyshell" in self.extras:
            text = self._prepare_pyshell_blocks(text)
        if "wiki-tables" in self.extras:
            text = self._do_wiki_tables(text)

        text = self._do_code_blocks(text)

        text = self._do_block_quotes(text)

        # We already ran _hash_html_blocks() before, in Markdown(), but that
        # was to escape raw HTML in the original Markdown source. This time,
        # we're escaping the markup we've just created, so that we don't wrap
        # <p> tags around block-level tags.
        text = self._hash_html_blocks(text)

        text = self._form_paragraphs(text)

        return text

    def _pyshell_block_sub(self, match):
        lines = match.group(0).splitlines(0)
        _dedentlines(lines)
        indent = ' ' * self.tab_width
        s = ('\n' # separate from possible cuddled paragraph
             + indent + ('\n'+indent).join(lines)
             + '\n\n')
        return s

    def _prepare_pyshell_blocks(self, text):
        """Ensure that Python interactive shell sessions are put in
        code blocks -- even if not properly indented.
        """
        if ">>>" not in text:
            return text

        less_than_tab = self.tab_width - 1
        _pyshell_block_re = re.compile(r"""
            ^([ ]{0,%d})>>>[ ].*\n   # first line
            ^(\1.*\S+.*\n)*         # any number of subsequent lines
            ^\n                     # ends with a blank line
            """ % less_than_tab, re.M | re.X)

        return _pyshell_block_re.sub(self._pyshell_block_sub, text)

    def _wiki_table_sub(self, match):
        ttext = match.group(0).strip()
        #print 'wiki table: %r' % match.group(0)
        rows = []
        for line in ttext.splitlines(0):
            line = line.strip()[2:-2].strip()
            row = [c.strip() for c in re.split(r'(?<!\\)\|\|', line)]
            rows.append(row)
        #pprint(rows)
        hlines = ['<table>', '<tbody>']
        for row in rows:
            hrow = ['<tr>']
            for cell in row:
                hrow.append('<td>')
                hrow.append(self._run_span_gamut(cell))
                hrow.append('</td>')
            hrow.append('</tr>')
            hlines.append(''.join(hrow))
        hlines += ['</tbody>', '</table>']
        return '\n'.join(hlines) + '\n'

    def _do_wiki_tables(self, text):
        # Optimization.
        if "||" not in text:
            return text

        less_than_tab = self.tab_width - 1
        wiki_table_re = re.compile(r'''
            (?:(?<=\n\n)|\A\n?)            # leading blank line
            ^([ ]{0,%d})\|\|.+?\|\|[ ]*\n  # first line
            (^\1\|\|.+?\|\|\n)*        # any number of subsequent lines
            ''' % less_than_tab, re.M | re.X)
        return wiki_table_re.sub(self._wiki_table_sub, text)

    def _run_span_gamut(self, text):
        # These are all the transformations that occur *within* block-level
        # tags like paragraphs, headers, and list items.

        text = self._do_code_spans(text)

        text = self._escape_special_chars(text)

        # Process anchor and image tags.
        text = self._do_links(text)

        # Make links out of things like `<http://example.com/>`
        # Must come after _do_links(), because you can use < and >
        # delimiters in inline links like [this](<url>).
        text = self._do_auto_links(text)

        if "link-patterns" in self.extras:
            text = self._do_link_patterns(text)

        text = self._encode_amps_and_angles(text)

        text = self._do_italics_and_bold(text)

        if "smarty-pants" in self.extras:
            text = self._do_smart_punctuation(text)

        # Do hard breaks:
        text = re.sub(r" {2,}\n", " <br%s\n" % self.empty_element_suffix, text)

        return text

    # "Sorta" because auto-links are identified as "tag" tokens.
    _sorta_html_tokenize_re = re.compile(r"""
        (
            # tag
            </?
            (?:\w+)                                     # tag name
            (?:\s+(?:[\w-]+:)?[\w-]+=(?:".*?"|'.*?'))*  # attributes
            \s*/?>
            |
            # auto-link (e.g., <http://www.activestate.com/>)
            <\w+[^>]*>
            |
            <!--.*?-->      # comment
            |
            <\?.*?\?>       # processing instruction
        )
        """, re.X)

    def _escape_special_chars(self, text):
        # Python markdown note: the HTML tokenization here differs from
        # that in Markdown.pl, hence the behaviour for subtle cases can
        # differ (I believe the tokenizer here does a better job because
        # it isn't susceptible to unmatched '<' and '>' in HTML tags).
        # Note, however, that '>' is not allowed in an auto-link URL
        # here.
        escaped = []
        is_html_markup = False
        for token in self._sorta_html_tokenize_re.split(text):
            if is_html_markup:
                # Within tags/HTML-comments/auto-links, encode * and _
                # so they don't conflict with their use in Markdown for
                # italics and strong.  We're replacing each such
                # character with its corresponding MD5 checksum value;
                # this is likely overkill, but it should prevent us from
                # colliding with the escape values by accident.
                escaped.append(token.replace('*', self._escape_table['*'])
                                    .replace('_', self._escape_table['_']))
            else:
                escaped.append(self._encode_backslash_escapes(token))
            is_html_markup = not is_html_markup
        return ''.join(escaped)

    def _hash_html_spans(self, text):
        # Used for safe_mode.

        def _is_auto_link(s):
            if ':' in s and self._auto_link_re.match(s):
                return True
            elif '@' in s and self._auto_email_link_re.match(s):
                return True
            return False

        tokens = []
        is_html_markup = False
        for token in self._sorta_html_tokenize_re.split(text):
            if is_html_markup and not _is_auto_link(token):
                sanitized = self._sanitize_html(token)
                key = _hash_text(sanitized)
                self.html_spans[key] = sanitized
                tokens.append(key)
            else:
                tokens.append(token)
            is_html_markup = not is_html_markup
        return ''.join(tokens)

    def _unhash_html_spans(self, text):
        for key, sanitized in list(self.html_spans.items()):
            text = text.replace(key, sanitized)
        return text
    
    def _math_span_sub(self, match):
        m = match.string[match.start():match.start(2)] + self._encode_code(match.group(2)) + match.string[match.end(2):match.end()]
        key = _hash_text(m)
        self.math_spans[key] = m
        return key

    def _hash_math_spans(self, text):
        _math_span_re = re.compile(r'''
                (?<!\\)
                (%s)    # \1 = Opening delimiter
                (.+?)   # \2 = The math span
                \1      # Matching closer
            ''' % re.escape(self.extras['math_delimiter']), re.X)
        return _math_span_re.sub(self._math_span_sub, text)

    def _unhash_math_spans(self, text):
        for key, sanitized in list(self.math_spans.items()):
            text = text.replace(key, sanitized)
        return text

    def _sanitize_html(self, s):
        if self.safe_mode == "replace":
            return self.html_removed_text
        elif self.safe_mode == "escape":
            replacements = [
                ('&', '&amp;'),
                ('<', '&lt;'),
                ('>', '&gt;'),
            ]
            for before, after in replacements:
                s = s.replace(before, after)
            return s
        else:
            raise MarkdownError("invalid value for 'safe_mode': %r (must be "
                                "'escape' or 'replace')" % self.safe_mode)

    _tail_of_inline_link_re = re.compile(r'''
          # Match tail of: [text](/url/) or [text](/url/ "title")
          \(            # literal paren
            [ \t]*
            (?P<url>            # \1
                <.*?>
                |
                .*?
            )
            [ \t]*
            (                   # \2
              (['"])            # quote char = \3
              (?P<title>.*?)
              \3                # matching quote
            )?                  # title is optional
          \)
        ''', re.X | re.S)
    _tail_of_reference_link_re = re.compile(r'''
          # Match tail of: [text][id]
          [ ]?          # one optional space
          (?:\n[ ]*)?   # one optional newline followed by spaces
          \[
            (?P<id>.*?)
          \]
        ''', re.X | re.S)

    def _do_links(self, text):
        """Turn Markdown link shortcuts into XHTML <a> and <img> tags.

        This is a combination of Markdown.pl's _DoAnchors() and
        _DoImages(). They are done together because that simplified the
        approach. It was necessary to use a different approach than
        Markdown.pl because of the lack of atomic matching support in
        Python's regex engine used in $g_nested_brackets.
        """
        MAX_LINK_TEXT_SENTINEL = 3000  # markdown2 issue 24

        # `anchor_allowed_pos` is used to support img links inside
        # anchors, but not anchors inside anchors. An anchor's start
        # pos must be `>= anchor_allowed_pos`.
        anchor_allowed_pos = 0

        curr_pos = 0
        while True: # Handle the next link.
            # The next '[' is the start of:
            # - an inline anchor:   [text](url "title")
            # - a reference anchor: [text][id]
            # - an inline img:      ![text](url "title")
            # - a reference img:    ![text][id]
            # - a footnote ref:     [^id]
            #   (Only if 'footnotes' extra enabled)
            # - a footnote defn:    [^id]: ...
            #   (Only if 'footnotes' extra enabled) These have already
            #   been stripped in _strip_footnote_definitions() so no
            #   need to watch for them.
            # - a link definition:  [id]: url "title"
            #   These have already been stripped in
            #   _strip_link_definitions() so no need to watch for them.
            # - not markup:         [...anything else...
            try:
                start_idx = text.index('[', curr_pos)
            except ValueError:
                break
            text_length = len(text)

            # Find the matching closing ']'.
            # Markdown.pl allows *matching* brackets in link text so we
            # will here too. Markdown.pl *doesn't* currently allow
            # matching brackets in img alt text -- we'll differ in that
            # regard.
            bracket_depth = 0
            for p in range(start_idx+1, min(start_idx+MAX_LINK_TEXT_SENTINEL,
                                            text_length)):
                ch = text[p]
                if ch == ']':
                    bracket_depth -= 1
                    if bracket_depth < 0:
                        break
                elif ch == '[':
                    bracket_depth += 1
            else:
                # Closing bracket not found within sentinel length.
                # This isn't markup.
                curr_pos = start_idx + 1
                continue
            link_text = text[start_idx+1:p]

            # Possibly a footnote ref?
            if "footnotes" in self.extras and link_text.startswith("^"):
                normed_id = re.sub(r'\W', '-', link_text[1:])
                if normed_id in self.footnotes:
                    self.footnote_ids.append(normed_id)
                    result = '<sup class="footnote-ref" id="fnref-%s">' \
                             '<a href="#fn-%s">%s</a></sup>' \
                             % (normed_id, normed_id, len(self.footnote_ids))
                    text = text[:start_idx] + result + text[p+1:]
                else:
                    # This id isn't defined, leave the markup alone.
                    curr_pos = p+1
                continue

            # Now determine what this is by the remainder.
            p += 1
            if p == text_length:
                return text

            # Inline anchor or img?
            if text[p] == '(': # attempt at perf improvement
                match = self._tail_of_inline_link_re.match(text, p)
                if match:
                    # Handle an inline anchor or img.
                    is_img = start_idx > 0 and text[start_idx-1] == "!"
                    if is_img:
                        start_idx -= 1

                    url, title = match.group("url"), match.group("title")
                    if url and url[0] == '<':
                        url = url[1:-1]  # '<url>' -> 'url'
                    # We've got to encode these to avoid conflicting
                    # with italics/bold.
                    url = url.replace('*', self._escape_table['*']) \
                             .replace('_', self._escape_table['_'])
                    if title:
                        title_str = ' title="%s"' % (
                            _xml_escape_attr(title)
                                .replace('*', self._escape_table['*'])
                                .replace('_', self._escape_table['_']))
                    else:
                        title_str = ''
                    if is_img:
                        result = '<img src="%s" alt="%s"%s%s' \
                            % (url.replace('"', '&quot;'),
                               _xml_escape_attr(link_text),
                               title_str, self.empty_element_suffix)
                        if "smarty-pants" in self.extras:
                            result = result.replace('"', self._escape_table['"'])
                        curr_pos = start_idx + len(result)
                        text = text[:start_idx] + result + text[match.end():]
                    elif start_idx >= anchor_allowed_pos:
                        result_head = '<a href="%s"%s>' % (url, title_str)
                        result = '%s%s</a>' % (result_head, link_text)
                        if "smarty-pants" in self.extras:
                            result = result.replace('"', self._escape_table['"'])
                        # <img> allowed from curr_pos on, <a> from
                        # anchor_allowed_pos on.
                        curr_pos = start_idx + len(result_head)
                        anchor_allowed_pos = start_idx + len(result)
                        text = text[:start_idx] + result + text[match.end():]
                    else:
                        # Anchor not allowed here.
                        curr_pos = start_idx + 1
                    continue

            # Reference anchor or img?
            else:
                match = self._tail_of_reference_link_re.match(text, p)
                if match:
                    # Handle a reference-style anchor or img.
                    is_img = start_idx > 0 and text[start_idx-1] == "!"
                    if is_img:
                        start_idx -= 1
                    link_id = match.group("id").lower()
                    if not link_id:
                        link_id = link_text.lower()  # for links like [this][]
                    if link_id in self.urls:
                        url = self.urls[link_id]
                        # We've got to encode these to avoid conflicting
                        # with italics/bold.
                        url = url.replace('*', self._escape_table['*']) \
                                 .replace('_', self._escape_table['_'])
                        title = self.titles.get(link_id)
                        if title:
                            before = title
                            title = _xml_escape_attr(title) \
                                .replace('*', self._escape_table['*']) \
                                .replace('_', self._escape_table['_'])
                            title_str = ' title="%s"' % title
                        else:
                            title_str = ''
                        if is_img:
                            result = '<img src="%s" alt="%s"%s%s' \
                                % (url.replace('"', '&quot;'),
                                   link_text.replace('"', '&quot;'),
                                   title_str, self.empty_element_suffix)
                            if "smarty-pants" in self.extras:
                                result = result.replace('"', self._escape_table['"'])
                            curr_pos = start_idx + len(result)
                            text = text[:start_idx] + result + text[match.end():]
                        elif start_idx >= anchor_allowed_pos:
                            result = '<a href="%s"%s>%s</a>' \
                                % (url, title_str, link_text)
                            result_head = '<a href="%s"%s>' % (url, title_str)
                            result = '%s%s</a>' % (result_head, link_text)
                            if "smarty-pants" in self.extras:
                                result = result.replace('"', self._escape_table['"'])
                            # <img> allowed from curr_pos on, <a> from
                            # anchor_allowed_pos on.
                            curr_pos = start_idx + len(result_head)
                            anchor_allowed_pos = start_idx + len(result)
                            text = text[:start_idx] + result + text[match.end():]
                        else:
                            # Anchor not allowed here.
                            curr_pos = start_idx + 1
                    else:
                        # This id isn't defined, leave the markup alone.
                        curr_pos = match.end()
                    continue

            # Otherwise, it isn't markup.
            curr_pos = start_idx + 1

        return text

    def header_id_from_text(self, text, prefix, n):
        """Generate a header id attribute value from the given header
        HTML content.

        This is only called if the "header-ids" extra is enabled.
        Subclasses may override this for different header ids.

        @param text {str} The text of the header tag
        @param prefix {str} The requested prefix for header ids. This is the
            value of the "header-ids" extra key, if any. Otherwise, None.
        @param n {int} The <hN> tag number, i.e. `1` for an <h1> tag.
        @returns {str} The value for the header tag's "id" attribute. Return
            None to not have an id attribute and to exclude this header from
            the TOC (if the "toc" extra is specified).
        """
        header_id = _slugify(text)
        if prefix and isinstance(prefix, base_string_type):
            header_id = prefix + '-' + header_id
        if header_id in self._count_from_header_id:
            self._count_from_header_id[header_id] += 1
            header_id += '-%s' % self._count_from_header_id[header_id]
        else:
            self._count_from_header_id[header_id] = 1
        return header_id

    _toc = None
    def _toc_add_entry(self, level, id, name):
        if self._toc is None:
            self._toc = []
        self._toc.append((level, id, self._unescape_special_chars(name)))

    _setext_h_re = re.compile(r'^(.+)[ \t]*\n(=+|-+)[ \t]*\n+', re.M)
    def _setext_h_sub(self, match):
        n = {"=": 1, "-": 2}[match.group(2)[0]]
        demote_headers = self.extras.get("demote-headers")
        if demote_headers:
            n = min(n + demote_headers, 6)
        header_id_attr = ""
        if "header-ids" in self.extras:
            header_id = self.header_id_from_text(match.group(1),
                self.extras["header-ids"], n)
            if header_id:
                header_id_attr = ' id="%s"' % header_id
        html = self._run_span_gamut(match.group(1))
        if "toc" in self.extras and header_id:
            self._toc_add_entry(n, header_id, html)
        return "<h%d%s>%s</h%d>\n\n" % (n, header_id_attr, html, n)

    _atx_h_re = re.compile(r'''
        ^(\#{1,6})  # \1 = string of #'s
        [ \t]+
        (.+?)       # \2 = Header text
        [ \t]*
        (?<!\\)     # ensure not an escaped trailing '#'
        \#*         # optional closing #'s (not counted)
        \n+
        ''', re.X | re.M)
    def _atx_h_sub(self, match):
        n = len(match.group(1))
        demote_headers = self.extras.get("demote-headers")
        if demote_headers:
            n = min(n + demote_headers, 6)
        header_id_attr = ""
        if "header-ids" in self.extras:
            header_id = self.header_id_from_text(match.group(2),
                self.extras["header-ids"], n)
            if header_id:
                header_id_attr = ' id="%s"' % header_id
        html = self._run_span_gamut(match.group(2))
        if "toc" in self.extras and header_id:
            self._toc_add_entry(n, header_id, html)
        return "<h%d%s>%s</h%d>\n\n" % (n, header_id_attr, html, n)

    def _do_headers(self, text):
        # Setext-style headers:
        #     Header 1
        #     ========
        #
        #     Header 2
        #     --------
        text = self._setext_h_re.sub(self._setext_h_sub, text)

        # atx-style headers:
        #   # Header 1
        #   ## Header 2
        #   ## Header 2 with closing hashes ##
        #   ...
        #   ###### Header 6
        text = self._atx_h_re.sub(self._atx_h_sub, text)

        return text


    _marker_ul_chars  = '*+-'
    _marker_any = r'(?:[%s]|\d+\.)' % _marker_ul_chars
    _marker_ul = '(?:[%s])' % _marker_ul_chars
    _marker_ol = r'(?:\d+\.)'

    def _list_sub(self, match):
        lst = match.group(1)
        lst_type = match.group(3) in self._marker_ul_chars and "ul" or "ol"
        result = self._process_list_items(lst)
        if self.list_level:
            return "<%s>\n%s</%s>\n" % (lst_type, result, lst_type)
        else:
            return "<%s>\n%s</%s>\n\n" % (lst_type, result, lst_type)

    def _do_lists(self, text):
        # Form HTML ordered (numbered) and unordered (bulleted) lists.

        # Iterate over each *non-overlapping* list match.
        pos = 0
        while True:
            # Find the *first* hit for either list style (ul or ol). We
            # match ul and ol separately to avoid adjacent lists of different
            # types running into each other (see issue #16).
            hits = []
            for marker_pat in (self._marker_ul, self._marker_ol):
                less_than_tab = self.tab_width - 1
                whole_list = r'''
                    (                   # \1 = whole list
                      (                 # \2
                        [ ]{0,%d}
                        (%s)            # \3 = first list item marker
                        [ \t]+
                        (?!\ *\3\ )     # '- - - ...' isn't a list. See 'not_quite_a_list' test case.
                      )
                      (?:.+?)
                      (                 # \4
                          \Z
                        |
                          \n{2,}
                          (?=\S)
                          (?!           # Negative lookahead for another list item marker
                            [ \t]*
                            %s[ \t]+
                          )
                      )
                    )
                ''' % (less_than_tab, marker_pat, marker_pat)
                if self.list_level:  # sub-list
                    list_re = re.compile("^"+whole_list, re.X | re.M | re.S)
                else:
                    list_re = re.compile(r"(?:(?<=\n\n)|\A\n?)"+whole_list,
                                         re.X | re.M | re.S)
                match = list_re.search(text, pos)
                if match:
                    hits.append((match.start(), match))
            if not hits:
                break
            hits.sort()
            match = hits[0][1]
            start, end = match.span()
            text = text[:start] + self._list_sub(match) + text[end:]
            pos = end

        return text

    _list_item_re = re.compile(r'''
        (\n)?                   # leading line = \1
        (^[ \t]*)               # leading whitespace = \2
        (?P<marker>%s) [ \t]+   # list marker = \3
        ((?:.+?)                # list item text = \4
         (\n{1,2}))             # eols = \5
        (?= \n* (\Z | \2 (?P<next_marker>%s) [ \t]+))
        ''' % (_marker_any, _marker_any),
        re.M | re.X | re.S)

    _last_li_endswith_two_eols = False
    def _list_item_sub(self, match):
        item = match.group(4)
        leading_line = match.group(1)
        leading_space = match.group(2)
        if leading_line or "\n\n" in item or self._last_li_endswith_two_eols:
            item = self._run_block_gamut(self._outdent(item))
        else:
            # Recursion for sub-lists:
            item = self._do_lists(self._outdent(item))
            if item.endswith('\n'):
                item = item[:-1]
            item = self._run_span_gamut(item)
        self._last_li_endswith_two_eols = (len(match.group(5)) == 2)
        return "<li>%s</li>\n" % item

    def _process_list_items(self, list_str):
        # Process the contents of a single ordered or unordered list,
        # splitting it into individual list items.

        # The $g_list_level global keeps track of when we're inside a list.
        # Each time we enter a list, we increment it; when we leave a list,
        # we decrement. If it's zero, we're not in a list anymore.
        #
        # We do this because when we're not inside a list, we want to treat
        # something like this:
        #
        #       I recommend upgrading to version
        #       8. Oops, now this line is treated
        #       as a sub-list.
        #
        # As a single paragraph, despite the fact that the second line starts
        # with a digit-period-space sequence.
        #
        # Whereas when we're inside a list (or sub-list), that line will be
        # treated as the start of a sub-list. What a kludge, huh? This is
        # an aspect of Markdown's syntax that's hard to parse perfectly
        # without resorting to mind-reading. Perhaps the solution is to
        # change the syntax rules such that sub-lists must start with a
        # starting cardinal number; e.g. "1." or "a.".
        self.list_level += 1
        self._last_li_endswith_two_eols = False
        list_str = list_str.rstrip('\n') + '\n'
        list_str = self._list_item_re.sub(self._list_item_sub, list_str)
        self.list_level -= 1
        return list_str

    def _get_pygments_lexer(self, lexer_name):
        try:
            from pygments import lexers, util
        except ImportError:
            return None
        try:
            return lexers.get_lexer_by_name(lexer_name)
        except util.ClassNotFound:
            return None

    def _color_with_pygments(self, codeblock, lexer, **formatter_opts):
        import pygments
        import pygments.formatters

        class HtmlCodeFormatter(pygments.formatters.HtmlFormatter):
            def _wrap_code(self, inner):
                """A function for use in a Pygments Formatter which
                wraps in <code> tags.
                """
                yield 0, "<code>"
                for tup in inner:
                    yield tup
                yield 0, "</code>"

            def wrap(self, source, outfile):
                """Return the source with a code, pre, and div."""
                return self._wrap_div(self._wrap_pre(self._wrap_code(source)))

        formatter_opts.setdefault("cssclass", "codehilite")
        formatter = HtmlCodeFormatter(**formatter_opts)
        return pygments.highlight(codeblock, lexer, formatter)

    def _code_block_sub(self, match, is_fenced_code_block=False):
        lexer_name = None
        if is_fenced_code_block:
            lexer_name = match.group(1)
            if lexer_name:
                formatter_opts = self.extras['fenced-code-blocks'] or {}
            codeblock = match.group(2)
            codeblock = codeblock[:-1]  # drop one trailing newline
        else:
            codeblock = match.group(1)
            codeblock = self._outdent(codeblock)
            codeblock = self._detab(codeblock)
            codeblock = codeblock.lstrip('\n')  # trim leading newlines
            codeblock = codeblock.rstrip()      # trim trailing whitespace

            # Note: "code-color" extra is DEPRECATED.
            if "code-color" in self.extras and codeblock.startswith(":::"):
                lexer_name, rest = codeblock.split('\n', 1)
                lexer_name = lexer_name[3:].strip()
                codeblock = rest.lstrip("\n")   # Remove lexer declaration line.
                formatter_opts = self.extras['code-color'] or {}

        if lexer_name:
            lexer = self._get_pygments_lexer(lexer_name)
            if lexer:
                colored = self._color_with_pygments(codeblock, lexer,
                                                    **formatter_opts)
                return "\n\n%s\n\n" % colored

        codeblock = self._encode_code(codeblock)
        pre_class_str = self._html_class_str_from_tag("pre")
        code_class_str = self._html_class_str_from_tag("code")
        return "\n\n<pre%s><code%s>%s\n</code></pre>\n\n" % (
            pre_class_str, code_class_str, codeblock)

    def _html_class_str_from_tag(self, tag):
        """Get the appropriate ' class="..."' string (note the leading
        space), if any, for the given tag.
        """
        if "html-classes" not in self.extras:
            return ""
        try:
            html_classes_from_tag = self.extras["html-classes"]
        except TypeError:
            return ""
        else:
            if tag in html_classes_from_tag:
                return ' class="%s"' % html_classes_from_tag[tag]
        return ""

    def _do_code_blocks(self, text):
        """Process Markdown `<pre><code>` blocks."""
        code_block_re = re.compile(r'''
            (?:\n\n|\A\n?)
            (               # $1 = the code block -- one or more lines, starting with a space/tab
              (?:
                (?:[ ]{%d} | \t)  # Lines must start with a tab or a tab-width of spaces
                .*\n+
              )+
            )
            ((?=^[ ]{0,%d}\S)|\Z)   # Lookahead for non-space at line-start, or end of doc
            ''' % (self.tab_width, self.tab_width),
            re.M | re.X)
        return code_block_re.sub(self._code_block_sub, text)

    _fenced_code_block_re = re.compile(r'''
        (?:\n\n|\A\n?)
        ^```([\w+-]+)?[ \t]*\n      # opening fence, $1 = optional lang
        (.*?)                       # $2 = code block content
        ^```[ \t]*\n                # closing fence
        ''', re.M | re.X | re.S)

    def _fenced_code_block_sub(self, match):
        return self._code_block_sub(match, is_fenced_code_block=True);

    def _do_fenced_code_blocks(self, text):
        """Process ```-fenced unindented code blocks ('fenced-code-blocks' extra)."""
        return self._fenced_code_block_re.sub(self._fenced_code_block_sub, text)

    # Rules for a code span:
    # - backslash escapes are not interpreted in a code span
    # - to include a run of more backticks the delimiters must
    #   be a longer run of backticks
    # - cannot start or end a code span with a backtick; pad with a
    #   space and that space will be removed in the emitted HTML
    # See `test/tm-cases/escapes.text` for a number of edge-case
    # examples.
    _code_span_re = re.compile(r'''
            (?<!\\)
            (`+)        # \1 = Opening run of `
            (?!`)       # See Note A test/tm-cases/escapes.text
            (.+?)       # \2 = The code block
            (?<!`)
            \1          # Matching closer
            (?!`)
        ''', re.X | re.S)

    def _code_span_sub(self, match):
        c = match.group(2).strip(" \t")
        c = self._encode_code(c)
        return "<code>%s</code>" % c

    def _do_code_spans(self, text):
        #   *   Backtick quotes are used for <code></code> spans.
        #
        #   *   You can use multiple backticks as the delimiters if you want to
        #       include literal backticks in the code span. So, this input:
        #
        #         Just type ``foo `bar` baz`` at the prompt.
        #
        #       Will translate to:
        #
        #         <p>Just type <code>foo `bar` baz</code> at the prompt.</p>
        #
        #       There's no arbitrary limit to the number of backticks you
        #       can use as delimters. If you need three consecutive backticks
        #       in your code, use four for delimiters, etc.
        #
        #   *   You can use spaces to get literal backticks at the edges:
        #
        #         ... type `` `bar` `` ...
        #
        #       Turns to:
        #
        #         ... type <code>`bar`</code> ...
        return self._code_span_re.sub(self._code_span_sub, text)

    def _encode_code(self, text):
        """Encode/escape certain characters inside Markdown code runs.
        The point is that in code, these characters are literals,
        and lose their special Markdown meanings.
        """
        replacements = [
            # Encode all ampersands; HTML entities are not
            # entities within a Markdown code span.
            ('&', '&amp;'),
            # Do the angle bracket song and dance:
            ('<', '&lt;'),
            ('>', '&gt;'),
        ]
        for before, after in replacements:
            text = text.replace(before, after)
        return text

    _strong_re = re.compile(r"(\*\*|__)(?=\S)(.+?[*_]*)(?<=\S)\1", re.S)
    _em_re = re.compile(r"(\*|_)(?=\S)(.+?)(?<=\S)\1", re.S)
    _code_friendly_strong_re = re.compile(r"\*\*(?=\S)(.+?[*_]*)(?<=\S)\*\*", re.S)
    _code_friendly_em_re = re.compile(r"\*(?=\S)(.+?)(?<=\S)\*", re.S)
    def _do_italics_and_bold(self, text):
        # <strong> must go first:
        if "code-friendly" in self.extras:
            text = self._code_friendly_strong_re.sub(r"<strong>\1</strong>", text)
            text = self._code_friendly_em_re.sub(r"<em>\1</em>", text)
        else:
            text = self._strong_re.sub(r"<strong>\2</strong>", text)
            text = self._em_re.sub(r"<em>\2</em>", text)
        return text

    # "smarty-pants" extra: Very liberal in interpreting a single prime as an
    # apostrophe; e.g. ignores the fact that "round", "bout", "twer", and
    # "twixt" can be written without an initial apostrophe. This is fine because
    # using scare quotes (single quotation marks) is rare.
    _apostrophe_year_re = re.compile(r"'(\d\d)(?=(\s|,|;|\.|\?|!|$))")
    _contractions = ["tis", "twas", "twer", "neath", "o", "n",
        "round", "bout", "twixt", "nuff", "fraid", "sup"]
    def _do_smart_contractions(self, text):
        text = self._apostrophe_year_re.sub(r"&#8217;\1", text)
        for c in self._contractions:
            text = text.replace("'%s" % c, "&#8217;%s" % c)
            text = text.replace("'%s" % c.capitalize(),
                "&#8217;%s" % c.capitalize())
        return text

    # Substitute double-quotes before single-quotes.
    _opening_single_quote_re = re.compile(r"(?<!\S)'(?=\S)")
    _opening_double_quote_re = re.compile(r'(?<!\S)"(?=\S)')
    _closing_single_quote_re = re.compile(r"(?<=\S)'")
    _closing_double_quote_re = re.compile(r'(?<=\S)"(?=(\s|,|;|\.|\?|!|$))')
    def _do_smart_punctuation(self, text):
        """Fancifies 'single quotes', "double quotes", and apostrophes.
        Converts --, ---, and ... into en dashes, em dashes, and ellipses.

        Inspiration is: <http://daringfireball.net/projects/smartypants/>
        See "test/tm-cases/smarty_pants.text" for a full discussion of the
        support here and
        <http://code.google.com/p/python-markdown2/issues/detail?id=42> for a
        discussion of some diversion from the original SmartyPants.
        """
        if "'" in text: # guard for perf
            text = self._do_smart_contractions(text)
            text = self._opening_single_quote_re.sub("&#8216;", text)
            text = self._closing_single_quote_re.sub("&#8217;", text)

        if '"' in text: # guard for perf
            text = self._opening_double_quote_re.sub("&#8220;", text)
            text = self._closing_double_quote_re.sub("&#8221;", text)

        text = text.replace("---", "&#8212;")
        text = text.replace("--", "&#8211;")
        text = text.replace("...", "&#8230;")
        text = text.replace(" . . . ", "&#8230;")
        text = text.replace(". . .", "&#8230;")
        return text

    _block_quote_re = re.compile(r'''
        (                           # Wrap whole match in \1
          (
            ^[ \t]*>[ \t]?          # '>' at the start of a line
              .+\n                  # rest of the first line
            (.+\n)*                 # subsequent consecutive lines
            \n*                     # blanks
          )+
        )
        ''', re.M | re.X)
    _bq_one_level_re = re.compile('^[ \t]*>[ \t]?', re.M);

    _html_pre_block_re = re.compile(r'(\s*<pre>.+?</pre>)', re.S)
    def _dedent_two_spaces_sub(self, match):
        return re.sub(r'(?m)^  ', '', match.group(1))

    def _block_quote_sub(self, match):
        bq = match.group(1)
        bq = self._bq_one_level_re.sub('', bq)  # trim one level of quoting
        bq = self._ws_only_line_re.sub('', bq)  # trim whitespace-only lines
        bq = self._run_block_gamut(bq)          # recurse

        bq = re.sub('(?m)^', '  ', bq)
        # These leading spaces screw with <pre> content, so we need to fix that:
        bq = self._html_pre_block_re.sub(self._dedent_two_spaces_sub, bq)

        return "<blockquote>\n%s\n</blockquote>\n\n" % bq

    def _do_block_quotes(self, text):
        if '>' not in text:
            return text
        return self._block_quote_re.sub(self._block_quote_sub, text)

    def _form_paragraphs(self, text):
        # Strip leading and trailing lines:
        text = text.strip('\n')

        # Wrap <p> tags.
        grafs = []
        for i, graf in enumerate(re.split(r"\n{2,}", text)):
            if graf in self.html_blocks:
                # Unhashify HTML blocks
                grafs.append(self.html_blocks[graf])
            else:
                cuddled_list = None
                if "cuddled-lists" in self.extras:
                    # Need to put back trailing '\n' for `_list_item_re`
                    # match at the end of the paragraph.
                    li = self._list_item_re.search(graf + '\n')
                    # Two of the same list marker in this paragraph: a likely
                    # candidate for a list cuddled to preceding paragraph
                    # text (issue 33). Note the `[-1]` is a quick way to
                    # consider numeric bullets (e.g. "1." and "2.") to be
                    # equal.
                    if (li and len(li.group(2)) <= 3 and li.group("next_marker")
                        and li.group("marker")[-1] == li.group("next_marker")[-1]):
                        start = li.start()
                        cuddled_list = self._do_lists(graf[start:]).rstrip("\n")
                        assert cuddled_list.startswith("<ul>") or cuddled_list.startswith("<ol>")
                        graf = graf[:start]

                # Wrap <p> tags.
                graf = self._run_span_gamut(graf)
                grafs.append("<p>" + graf.lstrip(" \t") + "</p>")

                if cuddled_list:
                    grafs.append(cuddled_list)

        return "\n\n".join(grafs)

    def _sort_footnotes(self, text):
        """Because _do_links is not applied to the text in text flow order, footnotes are not generated in proper order, we have to sort them before _add_footnotes.
        """
        _footnote_tag_re = re.compile(r'''<sup class="footnote-ref" id="fnref-(.+)"><a href="#fn-\1">(\d+)</a></sup>''')
        self.footnote_ids = []
        def _repl(match):
            id = match.group(1)
            num = match.group(2)
            if id in self.footnotes:
                self.footnote_ids.append(id)
                return match.string[match.start(0):match.start(2)] + str(len(self.footnote_ids)) + match.string[match.end(2):match.end(0)]
            else:
                return match.string[match.start():match.end()]
        return _footnote_tag_re.sub(_repl, text)        
    
    def _add_footnotes(self, text):
        if self.footnotes:
            footer = [
                '<div class="footnotes">',
                '<hr' + self.empty_element_suffix,
                '<ol>',
            ]
            for i, id in enumerate(self.footnote_ids):
                if i != 0:
                    footer.append('')
                footer.append('<li id="fn-%s">' % id)
                footer.append(self._run_block_gamut(self.footnotes[id]))
                backlink = ('<a href="#fnref-%s" '
                    'class="footnoteBackLink" '
                    'title="Jump back to footnote %d in the text.">'
                    '&#8617;</a>' % (id, i+1))
                if footer[-1].endswith("</p>"):
                    footer[-1] = footer[-1][:-len("</p>")] \
                        + '&nbsp;' + backlink + "</p>"
                else:
                    footer.append("\n<p>%s</p>" % backlink)
                footer.append('</li>')
            footer.append('</ol>')
            footer.append('</div>')
            return text + '\n\n' + '\n'.join(footer)
        else:
            return text

    # Ampersand-encoding based entirely on Nat Irons's Amputator MT plugin:
    #   http://bumppo.net/projects/amputator/
    _ampersand_re = re.compile(r'&(?!#?[xX]?(?:[0-9a-fA-F]+|\w+);)')
    _naked_lt_re = re.compile(r'<(?![a-z/?\$!])', re.I)
    _naked_gt_re = re.compile(r'''(?<![a-z0-9?!/'"-])>''', re.I)

    def _encode_amps_and_angles(self, text):
        # Smart processing for ampersands and angle brackets that need
        # to be encoded.
        text = self._ampersand_re.sub('&amp;', text)

        # Encode naked <'s
        text = self._naked_lt_re.sub('&lt;', text)

        # Encode naked >'s
        # Note: Other markdown implementations (e.g. Markdown.pl, PHP
        # Markdown) don't do this.
        text = self._naked_gt_re.sub('&gt;', text)
        return text

    def _encode_backslash_escapes(self, text):
        for ch, escape in list(self._escape_table.items()):
            text = text.replace("\\"+ch, escape)
        return text

    _auto_link_re = re.compile(r'<((https?|ftp):[^\'">\s]+)>', re.I)
    def _auto_link_sub(self, match):
        g1 = match.group(1)
        return '<a href="%s">%s</a>' % (g1, g1)

    _auto_email_link_re = re.compile(r"""
          <
           (?:mailto:)?
          (
              [-.\w]+
              \@
              [-\w]+(\.[-\w]+)*\.[a-z]+
          )
          >
        """, re.I | re.X | re.U)
    def _auto_email_link_sub(self, match):
        return self._encode_email_address(
            self._unescape_special_chars(match.group(1)))

    def _do_auto_links(self, text):
        text = self._auto_link_re.sub(self._auto_link_sub, text)
        text = self._auto_email_link_re.sub(self._auto_email_link_sub, text)
        return text

    def _encode_email_address(self, addr):
        #  Input: an email address, e.g. "foo@example.com"
        #
        #  Output: the email address as a mailto link, with each character
        #      of the address encoded as either a decimal or hex entity, in
        #      the hopes of foiling most address harvesting spam bots. E.g.:
        #
        #    <a href="&#x6D;&#97;&#105;&#108;&#x74;&#111;:&#102;&#111;&#111;&#64;&#101;
        #       x&#x61;&#109;&#x70;&#108;&#x65;&#x2E;&#99;&#111;&#109;">&#102;&#111;&#111;
        #       &#64;&#101;x&#x61;&#109;&#x70;&#108;&#x65;&#x2E;&#99;&#111;&#109;</a>
        #
        #  Based on a filter by Matthew Wickline, posted to the BBEdit-Talk
        #  mailing list: <http://tinyurl.com/yu7ue>
        chars = [_xml_encode_email_char_at_random(ch)
                 for ch in "mailto:" + addr]
        # Strip the mailto: from the visible part.
        addr = '<a href="%s">%s</a>' \
               % (''.join(chars), ''.join(chars[7:]))
        return addr

    def _do_link_patterns(self, text):
        """Caveat emptor: there isn't much guarding against link
        patterns being formed inside other standard Markdown links, e.g.
        inside a [link def][like this].

        Dev Notes: *Could* consider prefixing regexes with a negative
        lookbehind assertion to attempt to guard against this.
        """
        link_from_hash = {}
        for regex, repl in self.link_patterns:
            replacements = []
            for match in regex.finditer(text):
                if hasattr(repl, "__call__"):
                    href = repl(match)
                else:
                    href = match.expand(repl)
                replacements.append((match.span(), href))
            for (start, end), href in reversed(replacements):
                escaped_href = (
                    href.replace('"', '&quot;')  # b/c of attr quote
                        # To avoid markdown <em> and <strong>:
                        .replace('*', self._escape_table['*'])
                        .replace('_', self._escape_table['_']))
                link = '<a href="%s">%s</a>' % (escaped_href, text[start:end])
                hash = _hash_text(link)
                link_from_hash[hash] = link
                text = text[:start] + hash + text[end:]
        for hash, link in list(link_from_hash.items()):
            text = text.replace(hash, link)
        return text

    def _unescape_special_chars(self, text):
        # Swap back in all the special characters we've hidden.
        for ch, hash in list(self._escape_table.items()):
            text = text.replace(hash, ch)
        return text

    def _outdent(self, text):
        # Remove one level of line-leading tabs or spaces
        return self._outdent_re.sub('', text)


class MarkdownWithExtras(Markdown):
    """A markdowner class that enables most extras:

    - footnotes
    - code-color (only has effect if 'pygments' Python module on path)

    These are not included:
    - pyshell (specific to Python-related documenting)
    - code-friendly (because it *disables* part of the syntax)
    - link-patterns (because you need to specify some actual
      link-patterns anyway)
    """
    extras = ["footnotes", "code-color"]


#---- internal support functions

class UnicodeWithAttrs(unicode):
    """A subclass of unicode used for the return value of conversion to
    possibly attach some attributes. E.g. the "toc_html" attribute when
    the "toc" extra is used.
    """
    metadata = None
    _toc = None
    def toc_html(self):
        """Return the HTML for the current TOC.

        This expects the `_toc` attribute to have been set on this instance.
        """
        if self._toc is None:
            return None

        def indent():
            return '  ' * (len(h_stack) - 1)
        lines = []
        h_stack = [0]   # stack of header-level numbers
        for level, id, name in self._toc:
            if level > h_stack[-1]:
                lines.append("%s<ul>" % indent())
                h_stack.append(level)
            elif level == h_stack[-1]:
                lines[-1] += "</li>"
            else:
                while level < h_stack[-1]:
                    h_stack.pop()
                    if not lines[-1].endswith("</li>"):
                        lines[-1] += "</li>"
                    lines.append("%s</ul></li>" % indent())
            lines.append('%s<li><a href="#%s">%s</a>' % (
                indent(), id, name))
        while len(h_stack) > 1:
            h_stack.pop()
            if not lines[-1].endswith("</li>"):
                lines[-1] += "</li>"
            lines.append("%s</ul>" % indent())
        return '\n'.join(lines) + '\n'
    toc_html = property(toc_html)

## {{{ http://code.activestate.com/recipes/577257/ (r1)
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')
def _slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    import unicodedata
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    value = _slugify_strip_re.sub('', value).strip().lower()
    return _slugify_hyphenate_re.sub('-', value)
## end of http://code.activestate.com/recipes/577257/ }}}


# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52549
def _curry(*args, **kwargs):
    function, args = args[0], args[1:]
    def result(*rest, **kwrest):
        combined = kwargs.copy()
        combined.update(kwrest)
        return function(*args + rest, **combined)
    return result

# Recipe: regex_from_encoded_pattern (1.0)
def _regex_from_encoded_pattern(s):
    """'foo'    -> re.compile(re.escape('foo'))
       '/foo/'  -> re.compile('foo')
       '/foo/i' -> re.compile('foo', re.I)
    """
    if s.startswith('/') and s.rfind('/') != 0:
        # Parse it: /PATTERN/FLAGS
        idx = s.rfind('/')
        pattern, flags_str = s[1:idx], s[idx+1:]
        flag_from_char = {
            "i": re.IGNORECASE,
            "l": re.LOCALE,
            "s": re.DOTALL,
            "m": re.MULTILINE,
            "u": re.UNICODE,
        }
        flags = 0
        for char in flags_str:
            try:
                flags |= flag_from_char[char]
            except KeyError:
                raise ValueError("unsupported regex flag: '%s' in '%s' "
                                 "(must be one of '%s')"
                                 % (char, s, ''.join(list(flag_from_char.keys()))))
        return re.compile(s[1:idx], flags)
    else: # not an encoded regex
        return re.compile(re.escape(s))

# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines

        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG:
        print("dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line))
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print("dedent: indent=%d: %r" % (indent, line))
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print("dedent: margin=%r" % margin)

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print("dedent: %r: EOL -> strip up to EOL" % line)
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print("dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin))
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)


class _memoized(object):
   """Decorator that caches a function's return value each time it is called.
   If called later with the same arguments, the cached value is returned, and
   not re-evaluated.

   http://wiki.python.org/moin/PythonDecoratorLibrary
   """
   def __init__(self, func):
      self.func = func
      self.cache = {}
   def __call__(self, *args):
      try:
         return self.cache[args]
      except KeyError:
         self.cache[args] = value = self.func(*args)
         return value
      except TypeError:
         # uncachable -- for instance, passing a list as an argument.
         # Better to not cache than to blow up entirely.
         return self.func(*args)
   def __repr__(self):
      """Return the function's docstring."""
      return self.func.__doc__


def _xml_oneliner_re_from_tab_width(tab_width):
    """Standalone XML processing instruction regex."""
    return re.compile(r"""
        (?:
            (?<=\n\n)       # Starting after a blank line
            |               # or
            \A\n?           # the beginning of the doc
        )
        (                           # save in $1
            [ ]{0,%d}
            (?:
                <\?\w+\b\s+.*?\?>   # XML processing instruction
                |
                <\w+:\w+\b\s+.*?/>  # namespaced single tag
            )
            [ \t]*
            (?=\n{2,}|\Z)       # followed by a blank line or end of document
        )
        """ % (tab_width - 1), re.X)
_xml_oneliner_re_from_tab_width = _memoized(_xml_oneliner_re_from_tab_width)

def _hr_tag_re_from_tab_width(tab_width):
     return re.compile(r"""
        (?:
            (?<=\n\n)       # Starting after a blank line
            |               # or
            \A\n?           # the beginning of the doc
        )
        (                       # save in \1
            [ ]{0,%d}
            <(hr)               # start tag = \2
            \b                  # word break
            ([^<>])*?           #
            /?>                 # the matching end tag
            [ \t]*
            (?=\n{2,}|\Z)       # followed by a blank line or end of document
        )
        """ % (tab_width - 1), re.X)
_hr_tag_re_from_tab_width = _memoized(_hr_tag_re_from_tab_width)


def _xml_escape_attr(attr, skip_single_quote=True):
    """Escape the given string for use in an HTML/XML tag attribute.

    By default this doesn't bother with escaping `'` to `&#39;`, presuming that
    the tag attribute is surrounded by double quotes.
    """
    escaped = (attr
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;'))
    if not skip_single_quote:
        escaped = escaped.replace("'", "&#39;")
    return escaped


def _xml_encode_email_char_at_random(ch):
    r = random()
    # Roughly 10% raw, 45% hex, 45% dec.
    # '@' *must* be encoded. I [John Gruber] insist.
    # Issue 26: '_' must be encoded.
    if r > 0.9 and ch not in "@_":
        return ch
    elif r < 0.45:
        # The [1:] is to drop leading '0': 0x63 -> x63
        return '&#%s;' % hex(ord(ch))[1:]
    else:
        return '&#%s;' % ord(ch)



#---- mainline

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def _test():
    import doctest
    doctest.testmod()

def main(argv=None):
    if argv is None:
        argv = sys.argv
    if not logging.root.handlers:
        logging.basicConfig()

    usage = "usage: %prog [PATHS...]"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="markdown2", usage=usage,
        version=version, description=cmdln_desc,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("--encoding",
                      help="specify encoding of text content")
    parser.add_option("--html4tags", action="store_true", default=False,
                      help="use HTML 4 style for empty element tags")
    parser.add_option("-s", "--safe", metavar="MODE", dest="safe_mode",
                      help="sanitize literal HTML: 'escape' escapes "
                           "HTML meta chars, 'replace' replaces with an "
                           "[HTML_REMOVED] note")
    parser.add_option("-x", "--extras", action="append",
                      help="Turn on specific extra features (not part of "
                           "the core Markdown spec). See above.")
    parser.add_option("--use-file-vars",
                      help="Look for and use Emacs-style 'markdown-extras' "
                           "file var to turn on extras. See "
                           "<https://github.com/trentm/python-markdown2/wiki/Extras>")
    parser.add_option("--link-patterns-file",
                      help="path to a link pattern file")
    parser.add_option("--self-test", action="store_true",
                      help="run internal self-tests (some doctests)")
    parser.add_option("--compare", action="store_true",
                      help="run against Markdown.pl as well (for testing)")
    parser.set_defaults(log_level=logging.INFO, compare=False,
                        encoding="utf-8", safe_mode=None, use_file_vars=False)
    opts, paths = parser.parse_args()
    log.setLevel(opts.log_level)

    if opts.self_test:
        return _test()

    if opts.extras:
        extras = {}
        for s in opts.extras:
            splitter = re.compile("[,;: ]+")
            for e in splitter.split(s):
                if '=' in e:
                    ename, earg = e.split('=', 1)
                    try:
                        earg = int(earg)
                    except ValueError:
                        pass
                else:
                    ename, earg = e, None
                extras[ename] = earg
    else:
        extras = None

    if opts.link_patterns_file:
        link_patterns = []
        f = open(opts.link_patterns_file)
        try:
            for i, line in enumerate(f.readlines()):
                if not line.strip(): continue
                if line.lstrip().startswith("#"): continue
                try:
                    pat, href = line.rstrip().rsplit(None, 1)
                except ValueError:
                    raise MarkdownError("%s:%d: invalid link pattern line: %r"
                                        % (opts.link_patterns_file, i+1, line))
                link_patterns.append(
                    (_regex_from_encoded_pattern(pat), href))
        finally:
            f.close()
    else:
        link_patterns = None

    from os.path import join, dirname, abspath, exists
    markdown_pl = join(dirname(dirname(abspath(__file__))), "test",
                       "Markdown.pl")
    if not paths:
        paths = ['-']
    for path in paths:
        if path == '-':
            text = sys.stdin.read()
        else:
            fp = codecs.open(path, 'r', opts.encoding)
            text = fp.read()
            fp.close()
        if opts.compare:
            from subprocess import Popen, PIPE
            print("==== Markdown.pl ====")
            p = Popen('perl %s' % markdown_pl, shell=True, stdin=PIPE, stdout=PIPE, close_fds=True)
            p.stdin.write(text.encode('utf-8'))
            p.stdin.close()
            perl_html = p.stdout.read().decode('utf-8')
            if py3:
                sys.stdout.write(perl_html)
            else:
                sys.stdout.write(perl_html.encode(
                    sys.stdout.encoding or "utf-8", 'xmlcharrefreplace'))
            print("==== markdown2.py ====")
        html = markdown(text,
            html4tags=opts.html4tags,
            safe_mode=opts.safe_mode,
            extras=extras, link_patterns=link_patterns,
            use_file_vars=opts.use_file_vars)
        if py3:
            sys.stdout.write(html)
        else:
            sys.stdout.write(html.encode(
                sys.stdout.encoding or "utf-8", 'xmlcharrefreplace'))
        if extras and "toc" in extras:
            log.debug("toc_html: " +
                html.toc_html.encode(sys.stdout.encoding or "utf-8", 'xmlcharrefreplace'))
        if opts.compare:
            test_dir = join(dirname(dirname(abspath(__file__))), "test")
            if exists(join(test_dir, "test_markdown2.py")):
                sys.path.insert(0, test_dir)
                from test_markdown2 import norm_html_from_html
                norm_html = norm_html_from_html(html)
                norm_perl_html = norm_html_from_html(perl_html)
            else:
                norm_html = html
                norm_perl_html = perl_html
            print("==== match? %r ====" % (norm_perl_html == norm_html))


if __name__ == "__main__":
    sys.exit( main(sys.argv) )

########NEW FILE########
__FILENAME__ = gen_perf_cases
#!/usr/bin/env python2.5

import os
from os.path import *
import sys
import re
import datetime
from glob import glob
import operator
import shutil
import codecs


TMP = "tmp-"

def gen_aspn_cases(limit=0):
    base_dir = TMP+'aspn-cases'
    if exists(base_dir):
        print "'%s' exists, skipping" % base_dir
        return 
    os.makedirs(base_dir)
    sys.stdout.write("generate %s" % base_dir); sys.stdout.flush()
    recipes_path = expanduser("~/as/code.as.com/db/aspn/recipes.pprint")
    recipe_dicts = eval(open(recipes_path).read())
    for i, r in enumerate(recipe_dicts):
        sys.stdout.write('.'); sys.stdout.flush()
        f = codecs.open(join(base_dir, "r%04d.text" % i), "w", "utf-8")
        f.write(r["desc"])
        f.close()

        for j, c in enumerate(sorted(r["comments"],
                        key=operator.itemgetter("pub_date"))):
            text = _markdown_from_aspn_html(c["comment"])
            headline = c["title"].strip()
            if headline:
                if headline[-1] not in ".!?,:;'\"":
                    headline += '.'
                headline = _markdown_from_aspn_html(headline).strip()
                text = "**" + headline + "**  " + text
            f = codecs.open(join(base_dir, "r%04dc%02d.text" % (i, j)),
                            'w', "utf-8")
            f.write(text)
            f.close()

        if limit and i >= limit:
            break
    sys.stdout.write('\n')

def gen_test_cases():
    base_dir = TMP+"test-cases"
    if exists(base_dir):
        print "'%s' exists, skipping" % base_dir
        return 
    os.makedirs(base_dir)
    print "generate %s" % base_dir
    for test_cases_dir in glob(join("..", "test", "*-cases")):
        for text_file in glob(join(test_cases_dir, "*.text")):
            shutil.copy(text_file, join(base_dir, basename(text_file)))


#---- internal support stuff

br_pat = re.compile(r"</?br ?/?>", re.I)
br_eol_pat = re.compile(r"</?br ?/?>$", re.I | re.MULTILINE)
pre_pat = re.compile(r"<pre>(.*?)</pre>", re.I | re.DOTALL)
single_line_code_pat = re.compile(r"<(tt|code)>(.*?)</\1>", re.I)
a_pat = re.compile(r'''<a(\s+[\w:-]+=["'].*?["'])*>(.*?)</a>''', re.I | re.S | re.U)
href_attr_pat = re.compile(r'''href=(["'])(.*?)\1''', re.I)
title_attr_pat = re.compile(r'''title=(["'])(.*?)\1''', re.I)
i_pat = re.compile(r"<(i)>(.*?)</\1>", re.I)

def _markdown_from_aspn_html(html):
    from cgi import escape

    markdown = html

    markdown = br_eol_pat.sub('\n', markdown)  # <br>EOL
    markdown = br_pat.sub('\n', markdown)  # <br>

    while True: # <code>, <tt> on a single line
        match = single_line_code_pat.search(markdown)
        if not match:
            break
        markdown = single_line_code_pat.sub(r"`\2`", markdown)

    while True: # <i> on a single line
        match = i_pat.search(markdown)
        if not match:
            break
        markdown = i_pat.sub(r"*\2*", markdown)

    while True: # <a>
        match = a_pat.search(markdown)
        if not match:
            break
        start, end = match.span()
        attrs, content = match.group(1), match.group(2)
        href_match = href_attr_pat.search(attrs)
        if href_match:
            href = href_match.group(2)
        else:
            href = None
        title_match = title_attr_pat.search(attrs)
        if title_match:
            title = title_match.group(2)
        else:
            title = None
        escaped_href = href.replace('(', '\\(').replace(')', '\\)')
        if title is None:
            replacement = '[%s](%s)' % (content, escaped_href)
        else:
            replacement = '[%s](%s "%s")' % (content, escaped_href, 
                                             title.replace('"', "'"))
        markdown = markdown[:start] + replacement + markdown[end:]
        
    markdown = markdown.replace("&nbsp;", ' ')

    # <pre> part 1: Pull out <pre>-blocks and put in placeholders
    pre_marker = "THIS_IS_MY_PRE_MARKER_BLAH"
    pre_blocks = []
    while True: # <pre>
        match = pre_pat.search(markdown)
        if not match:
            break
        start, end = match.span()
        lines = match.group(1).splitlines(0)
        if lines and not lines[0].strip():
            del lines[0]
        _dedentlines(lines)
        pre_blocks.append(lines)
        marker = pre_marker + str(len(pre_blocks) - 1)
        markdown = markdown[:start].rstrip() + marker + markdown[end:].lstrip()

    # <pre> part 2: Put <pre>-blocks back in.
    for i, pre_block in enumerate(pre_blocks):
        marker = pre_marker + str(i)
        try:
            idx = markdown.index(marker)
        except ValueError:
            print "marker: %r" % marker
            raise
        if not markdown[:idx].strip():
            #TODO: Correct this false diagnosis. Problem is not limited
            #      to <h1>
            #TODO: problem with 1203#c6 "Frozen dictionaries": comment title
            #      insertion onto start of an indented-pre/code block
            #
            # There is a bug in python-markdown with an indented block
            # at the start of a buffer: the first line can get rendered
            # as a <h1>. Workaround that by adding a '.' paragraph
            # before.
            # At the time of this writing those comments affected are:
            #    16#c9, 31#c3, 155#c1, 203#c20, 230#c3, 356#c2, 490#c1,
            #    504#c2, 1127#c12
            #log.warn("adding '.'-para Python Markdown hack")
            prefix = ['.']
        else:
            prefix = []
        lines = prefix + ['', ''] + ['    '+ln for ln in lines] + ['', '']
        replacement = '\n'.join(lines)
        markdown = markdown.replace(marker, replacement, 1)

    lines = markdown.splitlines(0)

    # Removing empty lines at start and end.
    while lines and not lines[0].strip():
        del lines[0]
    while lines and not lines[-1].strip():
        del lines[-1]

    # Strip trailing whitespace because don't want auto-<br>'s.
    for i in range(len(lines)):
        lines[i] = lines[i].rstrip()

    markdown = '\n'.join(lines) + '\n'

    #TODO: manual fixes:
    # - comment 1, recipe 7

    return markdown

# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines
    
        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG: 
        print "dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line)
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print "dedent: indent=%d: %r" % (indent, line)
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print "dedent: margin=%r" % margin

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print "dedent: %r: EOL -> strip up to EOL" % line
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print "dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin)
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)


#---- mainline

if __name__ == "__main__":
    try:
        limit = int(sys.argv[1])
    except:
        limit = 0
    gen_aspn_cases(limit)
    gen_test_cases()


########NEW FILE########
__FILENAME__ = perf
#!/usr/bin/env python

"""Run some performance numbers.  <cases-dir> is a directory with a
number of "*.text" files to process.

Example:
    python gen_perf_cases.py    # generate a couple cases dirs
    python perf.py tmp-test-cases
"""

import os
import sys
import timeit
import time
from os.path import *
from glob import glob
import optparse

from util import hotshotit


clock = sys.platform == "win32" and time.clock or time.time


@hotshotit
def hotshot_markdown_py(cases_dir, repeat):
    time_markdown_py(cases_dir, repeat)

def time_markdown_py(cases_dir, repeat):
    sys.path.insert(0, join("..", "test"))
    import markdown
    del sys.path[0]
    markdowner = markdown.Markdown()
    times = []
    for i in range(repeat):
        start = clock()
        for path in glob(join(cases_dir, "*.text")):
            f = open(path, 'r')
            content = f.read()
            f.close()
            try:
                markdowner.convert(content)
                markdowner.reset()
            except UnicodeError:
                pass
        end = clock()
        times.append(end - start)
    print "  markdown.py: best of %d: %.3fs" % (repeat, min(times))

@hotshotit
def hotshot_markdown2_py(cases_dir, repeat):
    time_markdown2_py(cases_dir, repeat)

def time_markdown2_py(cases_dir, repeat):
    sys.path.insert(0, "../lib")
    import markdown2
    del sys.path[0]
    markdowner = markdown2.Markdown()
    times = []
    for i in range(repeat):
        start = clock()
        for path in glob(join(cases_dir, "*.text")):
            f = open(path, 'r')
            content = f.read()
            f.close()
            markdowner.convert(content)
        end = clock()
        times.append(end - start)
    print "  markdown2.py: best of %d: %.3fs" % (repeat, min(times))

def time_markdown_pl(cases_dir, repeat):
    times = []
    for i in range(repeat):
        start = clock()
        os.system('perl time_markdown_pl.pl "%s"' % cases_dir)
        end = clock()
        times.append(end - start)
    print "  Markdown.pl: best of %d: %.3fs" % (repeat, min(times))

def time_all(cases_dir, repeat):
    time_markdown_pl(cases_dir, repeat=repeat)
    time_markdown_py(cases_dir, repeat=repeat)
    time_markdown2_py(cases_dir, repeat=repeat)

def time_not_markdown_py(cases_dir, repeat):
    time_markdown_pl(cases_dir, repeat=repeat)
    time_markdown2_py(cases_dir, repeat=repeat)


#---- mainline

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def main(args=sys.argv):
    usage = "python perf.py [-i all|markdown.py|markdown2.py|Markdown.pl] [cases-dir]"
    parser = optparse.OptionParser(prog="perf", usage=usage,
        description=__doc__, formatter=_NoReflowFormatter())
    parser.add_option("-r", "--repeat", type="int",
        help="number of times to repeat timing cycle (default 3 if timing, "
             "1 if profiling)")
    parser.add_option("-i", "--implementation",
        help="Markdown implementation(s) to run: all (default), "
             "markdown.py, markdown2.py, Markdown.pl, not-markdown.py")
    parser.add_option("--hotshot", "--profile", dest="hotshot",
        action="store_true",
        help="profile and dump stats about a single run (not supported "
             "for Markdown.pl)")
    parser.set_defaults(implementation="all", hotshot=False, repeat=None)
    opts, args = parser.parse_args()
 
    if len(args) != 1:
        sys.stderr.write("error: incorrect number of args\n")
        sys.stderr.write(__doc__)
        return 1
    cases_dir = args[0]
    if not exists(cases_dir):
        raise OSError("cases dir `%s' does not exist: use "
                      "gen_perf_cases.py to generate some cases dirs" 
                      % cases_dir)
    if opts.repeat is None:
        opts.repeat = opts.hotshot and 1 or 3

    if opts.hotshot:
        assert opts.implementation in ("markdown.py", "markdown2.py")
        timer_name = "hotshot_%s" \
            % opts.implementation.lower().replace('.', '_').replace('-', '_')
        d = sys.modules[__name__].__dict__
        if timer_name not in d:
            raise ValueError("no '%s' timer function" % timer_name)
        timer = d[timer_name]
        print "Profile conversion of %s (plat=%s):" \
              % (os.path.join(cases_dir, "*.text"), sys.platform)
        timer(cases_dir, repeat=opts.repeat)
        print
        os.system("python show_stats.py %s.prof" % timer_name)

    else:
        timer_name = "time_%s" \
            % opts.implementation.lower().replace('.', '_').replace('-', '_')

        d = sys.modules[__name__].__dict__
        if timer_name not in d:
            raise ValueError("no '%s' timer function" % timer_name)
        timer = d[timer_name]
        print "Time conversion of %s (plat=%s):" \
              % (os.path.join(cases_dir, "*.text"), sys.platform)
        timer(cases_dir, repeat=opts.repeat)
    
if __name__ == "__main__":
    sys.exit( main(sys.argv) )



########NEW FILE########
__FILENAME__ = show_stats
"""
show_stats.py

Display results from profiling with hotshot.

Usage:
In module M.py, replace a call to function f with this code:

    import hotshot
    profiler = hotshot.Profile("%s.prof" % (__file__))
    profiler.runcall(f, *args)

and run from the command-line as
% python .../whatever.py args

To get the results, run this file:

% python .../show_stats.py .../whatever.py.prof
"""

import sys

import hotshot, hotshot.stats
stats = hotshot.stats.load(sys.argv[1])
stats.strip_dirs()
stats.sort_stats('time', 'calls')
stats.print_stats(20)

########NEW FILE########
__FILENAME__ = strip_cookbook_data

from os.path import *
from pprint import pprint, pformat
import datetime

def doit():
    recipes_path = expanduser("recipes.pprint")
    recipe_dicts = eval(open(recipes_path).read())
    for r in recipe_dicts:
        for key in r.keys():
            if key not in ('desc', 'comments'):
                del r[key]
        for c in r['comments']:
            for key in c.keys():
                if key not in ('comment', 'title'):
                    del c[key]
    
    f = open("stripped.pprint", 'w')
    f.write(pformat(recipe_dicts))
    f.close()


doit()


########NEW FILE########
__FILENAME__ = util
#!python
# Copyright (c) 2004-2006 ActiveState Software Inc.

"""Perf utility functions"""

import os
from os.path import basename
import sys
import md5
import re
import stat
import textwrap
import types
from pprint import pprint, pformat


# Global dict for holding specific hotshot profilers
hotshotProfilers = {}


# Decorators useful for timing and profiling specific functions.
#
# timeit usage:
#   Decorate the desired function and you'll get a print for how long
#   each call to the function took.
#
# hotspotit usage:
#   1. decorate the desired function
#   2. run your code
#   3. run:
#       python show_stats.py <funcname>.prof
#
def timeit(func):
    clock = (sys.platform == "win32" and time.clock or time.time)
    def wrapper(*args, **kw):
        start_time = clock()
        try:
            return func(*args, **kw)
        finally:
            total_time = clock() - start_time
            print "%s took %.3fs" % (func.func_name, total_time)
    return wrapper

def hotshotit(func):
    def wrapper(*args, **kw):
        import hotshot
        global hotshotProfilers
        prof_name = func.func_name+".prof"
        profiler = hotshotProfilers.get(prof_name)
        if profiler is None:
            profiler = hotshot.Profile(prof_name)
            hotshotProfilers[prof_name] = profiler
        return profiler.runcall(func, *args, **kw)
    return wrapper



########NEW FILE########
__FILENAME__ = wiki

import sys
import re
from os.path import *

sys.path.insert(0, dirname(dirname(abspath(__file__))))
import markdown2

wiki_page = """
# This is my WikiPage!

This is AnotherPage and YetAnotherPage.
"""

link_patterns = [
    # Match a wiki page link LikeThis.
    (re.compile(r"(\b[A-Z][a-z]+[A-Z]\w+\b)"), r"/\1")
]
processor = markdown2.Markdown(extras=["link-patterns"],
                               link_patterns=link_patterns)
print processor.convert(wiki_page)

########NEW FILE########
__FILENAME__ = markdown
#!/usr/bin/env python

version = "1.6b"
version_info = (1,6,2,"rc-2")
__revision__ = "$Rev$"

"""
Python-Markdown
===============

Converts Markdown to HTML.  Basic usage as a module:

    import markdown
    md = Markdown()
    html = markdown.convert(your_text_string)

See http://www.freewisdom.org/projects/python-markdown/ for more
information and instructions on how to extend the functionality of the
script.  (You might want to read that before you try modifying this
file.)

Started by [Manfred Stienstra](http://www.dwerg.net/).  Continued and
maintained  by [Yuri Takhteyev](http://www.freewisdom.org).

Contact: yuri [at] freewisdom.org

License: GPL 2 (http://www.gnu.org/copyleft/gpl.html) or BSD

"""


import re, sys, os, random, codecs

# Set debug level: 3 none, 2 critical, 1 informative, 0 all
(VERBOSE, INFO, CRITICAL, NONE) = range(4)

MESSAGE_THRESHOLD = CRITICAL

def message(level, text) :
    if level >= MESSAGE_THRESHOLD :
        print text


# --------------- CONSTANTS YOU MIGHT WANT TO MODIFY -----------------

TAB_LENGTH = 4            # expand tabs to this many spaces
ENABLE_ATTRIBUTES = True  # @id = xyz -> <... id="xyz">
SMART_EMPHASIS = 1        # this_or_that does not become this<i>or</i>that
HTML_REMOVED_TEXT = "[HTML_REMOVED]" # text used instead of HTML in safe mode

RTL_BIDI_RANGES = ( (u'\u0590', u'\u07FF'),
                    # from Hebrew to Nko (includes Arabic, Syriac and Thaana)
                    (u'\u2D30', u'\u2D7F'),
                    # Tifinagh
                    )

# Unicode Reference Table:
# 0590-05FF - Hebrew
# 0600-06FF - Arabic
# 0700-074F - Syriac
# 0750-077F - Arabic Supplement
# 0780-07BF - Thaana
# 07C0-07FF - Nko

BOMS = { 'utf-8' : (unicode(codecs.BOM_UTF8, "utf-8"), ),
         'utf-16' : (unicode(codecs.BOM_UTF16_LE, "utf-16"),
                     unicode(codecs.BOM_UTF16_BE, "utf-16")),
         #'utf-32' : (unicode(codecs.BOM_UTF32_LE, "utf-32"),
         #            unicode(codecs.BOM_UTF32_BE, "utf-32")),
         }

def removeBOM(text, encoding):
    for bom in BOMS[encoding]:
        if text.startswith(bom):
            return text.lstrip(bom)
    return text

# The following constant specifies the name used in the usage
# statement displayed for python versions lower than 2.3.  (With
# python2.3 and higher the usage statement is generated by optparse
# and uses the actual name of the executable called.)

EXECUTABLE_NAME_FOR_USAGE = "python markdown.py"
                    

# --------------- CONSTANTS YOU _SHOULD NOT_ HAVE TO CHANGE ----------

# a template for html placeholders
HTML_PLACEHOLDER_PREFIX = "qaodmasdkwaspemas"
HTML_PLACEHOLDER = HTML_PLACEHOLDER_PREFIX + "%dajkqlsmdqpakldnzsdfls"

BLOCK_LEVEL_ELEMENTS = ['p', 'div', 'blockquote', 'pre', 'table',
                        'dl', 'ol', 'ul', 'script', 'noscript',
                        'form', 'fieldset', 'iframe', 'math', 'ins',
                        'del', 'hr', 'hr/', 'style']

def is_block_level (tag) :
    return ( (tag in BLOCK_LEVEL_ELEMENTS) or
             (tag[0] == 'h' and tag[1] in "0123456789") )

"""
======================================================================
========================== NANODOM ===================================
======================================================================

The three classes below implement some of the most basic DOM
methods.  I use this instead of minidom because I need a simpler
functionality and do not want to require additional libraries.

Importantly, NanoDom does not do normalization, which is what we
want. It also adds extra white space when converting DOM to string
"""

ENTITY_NORMALIZATION_EXPRESSIONS = [ (re.compile("&"), "&amp;"),
                                     (re.compile("<"), "&lt;"),
                                     (re.compile(">"), "&gt;"),
                                     (re.compile("\""), "&quot;")]

ENTITY_NORMALIZATION_EXPRESSIONS_SOFT = [ (re.compile("&(?!\#)"), "&amp;"),
                                     (re.compile("<"), "&lt;"),
                                     (re.compile(">"), "&gt;"),
                                     (re.compile("\""), "&quot;")]


def getBidiType(text) :

    if not text : return None

    ch = text[0]

    if not isinstance(ch, unicode) or not ch.isalpha():
        return None

    else :

        for min, max in RTL_BIDI_RANGES :
            if ( ch >= min and ch <= max ) :
                return "rtl"
        else :
            return "ltr"


class Document :

    def __init__ (self) :
        self.bidi = "ltr"

    def appendChild(self, child) :
        self.documentElement = child
        child.isDocumentElement = True
        child.parent = self
        self.entities = {}

    def setBidi(self, bidi) :
        if bidi :
            self.bidi = bidi

    def createElement(self, tag, textNode=None) :
        el = Element(tag)
        el.doc = self
        if textNode :
            el.appendChild(self.createTextNode(textNode))
        return el

    def createTextNode(self, text) :
        node = TextNode(text)
        node.doc = self
        return node

    def createEntityReference(self, entity):
        if entity not in self.entities:
            self.entities[entity] = EntityReference(entity)
        return self.entities[entity]

    def createCDATA(self, text) :
        node = CDATA(text)
        node.doc = self
        return node

    def toxml (self) :
        return self.documentElement.toxml()

    def normalizeEntities(self, text, avoidDoubleNormalizing=False) :

        if avoidDoubleNormalizing :
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS_SOFT
        else :
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS

        for regexp, substitution in regexps :
            text = regexp.sub(substitution, text)
        return text

    def find(self, test) :
        return self.documentElement.find(test)

    def unlink(self) :
        self.documentElement.unlink()
        self.documentElement = None


class CDATA :

    type = "cdata"

    def __init__ (self, text) :
        self.text = text

    def handleAttributes(self) :
        pass

    def toxml (self) :
        return "<![CDATA[" + self.text + "]]>"

class Element :

    type = "element"

    def __init__ (self, tag) :

        self.nodeName = tag
        self.attributes = []
        self.attribute_values = {}
        self.childNodes = []
        self.bidi = None
        self.isDocumentElement = False

    def setBidi(self, bidi) :

        if bidi :

            orig_bidi = self.bidi

            if not self.bidi or self.isDocumentElement:
                # Once the bidi is set don't change it (except for doc element)
                self.bidi = bidi
                self.parent.setBidi(bidi)


    def unlink(self) :
        for child in self.childNodes :
            if child.type == "element" :
                child.unlink()
        self.childNodes = None

    def setAttribute(self, attr, value) :
        if not attr in self.attributes :
            self.attributes.append(attr)

        self.attribute_values[attr] = value

    def insertChild(self, position, child) :
        self.childNodes.insert(position, child)
        child.parent = self

    def removeChild(self, child) :
        self.childNodes.remove(child)

    def replaceChild(self, oldChild, newChild) :
        position = self.childNodes.index(oldChild)
        self.removeChild(oldChild)
        self.insertChild(position, newChild)

    def appendChild(self, child) :
        self.childNodes.append(child)
        child.parent = self

    def handleAttributes(self) :
        pass

    def find(self, test, depth=0) :
        """ Returns a list of descendants that pass the test function """
        matched_nodes = []
        for child in self.childNodes :
            if test(child) :
                matched_nodes.append(child)
            if child.type == "element" :
                matched_nodes += child.find(test, depth+1)
        return matched_nodes

    def toxml(self):
        if ENABLE_ATTRIBUTES :
            for child in self.childNodes:
                child.handleAttributes()

        buffer = ""
        if self.nodeName in ['h1', 'h2', 'h3', 'h4'] :
            buffer += "\n"
        elif self.nodeName in ['li'] :
            buffer += "\n "

        # Process children FIRST, then do the attributes

        childBuffer = ""

        if self.childNodes or self.nodeName in ['blockquote']:
            childBuffer += ">"
            for child in self.childNodes :
                childBuffer += child.toxml()
            if self.nodeName == 'p' :
                childBuffer += "\n"
            elif self.nodeName == 'li' :
                childBuffer += "\n "
            childBuffer += "</%s>" % self.nodeName
        else :
            childBuffer += "/>"


            
        buffer += "<" + self.nodeName

        if self.nodeName in ['p', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4', 'h5', 'h6'] :

            if not self.attribute_values.has_key("dir"):
                if self.bidi :
                    bidi = self.bidi
                else :
                    bidi = self.doc.bidi
                    
                if bidi=="rtl" :
                    self.setAttribute("dir", "rtl")
        
        for attr in self.attributes :
            value = self.attribute_values[attr]
            value = self.doc.normalizeEntities(value,
                                               avoidDoubleNormalizing=True)
            buffer += ' %s="%s"' % (attr, value)


        # Now let's actually append the children

        buffer += childBuffer

        if self.nodeName in ['p', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4'] :
            buffer += "\n"

        return buffer


class TextNode :

    type = "text"
    attrRegExp = re.compile(r'\{@([^\}]*)=([^\}]*)}') # {@id=123}

    def __init__ (self, text) :
        self.value = text        

    def attributeCallback(self, match) :

        self.parent.setAttribute(match.group(1), match.group(2))

    def handleAttributes(self) :
        self.value = self.attrRegExp.sub(self.attributeCallback, self.value)

    def toxml(self) :

        text = self.value

        self.parent.setBidi(getBidiType(text))
        
        if not text.startswith(HTML_PLACEHOLDER_PREFIX):
            if self.parent.nodeName == "p" :
                text = text.replace("\n", "\n   ")
            elif (self.parent.nodeName == "li"
                  and self.parent.childNodes[0]==self):
                text = "\n     " + text.replace("\n", "\n     ")
        text = self.doc.normalizeEntities(text)
        return text


class EntityReference:

    type = "entity_ref"

    def __init__(self, entity):
        self.entity = entity

    def handleAttributes(self):
        pass

    def toxml(self):
        return "&" + self.entity + ";"


"""
======================================================================
========================== PRE-PROCESSORS ============================
======================================================================

Preprocessors munge source text before we start doing anything too
complicated.

Each preprocessor implements a "run" method that takes a pointer to a
list of lines of the document, modifies it as necessary and returns
either the same pointer or a pointer to a new list.  Preprocessors
must extend markdown.Preprocessor.

"""


class Preprocessor :
    pass


class HeaderPreprocessor (Preprocessor):

    """
       Replaces underlined headers with hashed headers to avoid
       the nead for lookahead later.
    """

    def run (self, lines) :

        i = -1
        while i+1 < len(lines) :
            i = i+1
            if not lines[i].strip() :
                continue

            if lines[i].startswith("#") :
                lines.insert(i+1, "\n")

            if (i+1 <= len(lines)
                  and lines[i+1]
                  and lines[i+1][0] in ['-', '=']) :

                underline = lines[i+1].strip()

                if underline == "="*len(underline) :
                    lines[i] = "# " + lines[i].strip()
                    lines[i+1] = ""
                elif underline == "-"*len(underline) :
                    lines[i] = "## " + lines[i].strip()
                    lines[i+1] = ""

        return lines

HEADER_PREPROCESSOR = HeaderPreprocessor()

class LinePreprocessor (Preprocessor):
    """Deals with HR lines (needs to be done before processing lists)"""

    def run (self, lines) :
        for i in range(len(lines)) :
            if self._isLine(lines[i]) :
                lines[i] = "<hr />"
        return lines

    def _isLine(self, block) :
        """Determines if a block should be replaced with an <HR>"""
        if block.startswith("    ") : return 0  # a code block
        text = "".join([x for x in block if not x.isspace()])
        if len(text) <= 2 :
            return 0
        for pattern in ['isline1', 'isline2', 'isline3'] :
            m = RE.regExp[pattern].match(text)
            if (m and m.group(1)) :
                return 1
        else:
            return 0

LINE_PREPROCESSOR = LinePreprocessor()


class LineBreaksPreprocessor (Preprocessor):
    """Replaces double spaces at the end of the lines with <br/ >."""

    def run (self, lines) :
        for i in range(len(lines)) :
            if (lines[i].endswith("  ")
                and not RE.regExp['tabbed'].match(lines[i]) ):
                lines[i] += "<br />"
        return lines

LINE_BREAKS_PREPROCESSOR = LineBreaksPreprocessor()


class HtmlBlockPreprocessor (Preprocessor):
    """Removes html blocks from self.lines"""
    
    def _get_left_tag(self, block):
        return block[1:].replace(">", " ", 1).split()[0].lower()


    def _get_right_tag(self, left_tag, block):
        return block.rstrip()[-len(left_tag)-2:-1].lower()

    def _equal_tags(self, left_tag, right_tag):
        
        if left_tag in ['?', '?php', 'div'] : # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--") :
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] != "<":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    
    def run (self, lines) :

        new_blocks = []
        text = "\n".join(lines)
        text = text.split("\n\n")
        
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag
        
        for block in text:
            if block.startswith("\n") :
                block = block[1:]

            if not in_tag:

                if block.startswith("<"):
                    
                    left_tag = self._get_left_tag(block)
                    right_tag = self._get_right_tag(left_tag, block)

                    if not (is_block_level(left_tag) \
                        or block[1] in ["!", "?", "@", "%"]):
                        new_blocks.append(block)
                        continue

                    if self._is_oneliner(left_tag):
                        new_blocks.append(block.strip())
                        continue
                        
                    if block[1] == "!":
                        # is a comment block
                        left_tag = "--"
                        right_tag = self._get_right_tag(left_tag, block)
                        # keep checking conditions below and maybe just append
                        
                    if block.rstrip().endswith(">") \
                        and self._equal_tags(left_tag, right_tag):
                        new_blocks.append(
                            self.stash.store(block.strip()))
                        continue
                    else: #if not block[1] == "!":
                        # if is block level tag and is not complete
                        items.append(block.strip())
                        in_tag = True
                        continue

                new_blocks.append(block)

            else:
                items.append(block.strip())
                
                right_tag = self._get_right_tag(left_tag, block)
                
                if self._equal_tags(left_tag, right_tag):
                    # if find closing tag
                    in_tag = False
                    new_blocks.append(
                        self.stash.store('\n\n'.join(items)))
                    items = []

        if items :
            new_blocks.append(self.stash.store('\n\n'.join(items)))
            new_blocks.append('\n')
            
        return "\n\n".join(new_blocks).split("\n")

HTML_BLOCK_PREPROCESSOR = HtmlBlockPreprocessor()


class ReferencePreprocessor (Preprocessor):

    def run (self, lines) :

        new_text = [];
        for line in lines:
            m = RE.regExp['reference-def'].match(line)
            if m:
                id = m.group(2).strip().lower()
                t = m.group(4).strip()  # potential title
                if not t :
                    self.references[id] = (m.group(3), t)
                elif (len(t) >= 2
                      and (t[0] == t[-1] == "\""
                           or t[0] == t[-1] == "\'"
                           or (t[0] == "(" and t[-1] == ")") ) ) :
                    self.references[id] = (m.group(3), t[1:-1])
                else :
                    new_text.append(line)
            else:
                new_text.append(line)

        return new_text #+ "\n"

REFERENCE_PREPROCESSOR = ReferencePreprocessor()

"""
======================================================================
========================== INLINE PATTERNS ===========================
======================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

  pattern.getCompiledRegExp() - returns a regular expression

  pattern.handleMatch(m, doc) - takes a match object and returns
                                a NanoDom node (as a part of the provided
                                doc) or None

All of python markdown's built-in patterns subclass from Patter,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

       * escape and backticks have to go before everything else, so
         that we can preempt any markdown patterns by escaping them.

       * then we handle auto-links (must be done before inline html)

       * then we handle inline HTML.  At this point we will simply
         replace all inline HTML strings with a placeholder and add
         the actual HTML to a hash.

       * then inline images (must be done before links)

       * then bracketed links, first regular then reference-style

       * finally we apply strong and emphasis
"""

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[('
        + (NOBRACKET + r'(\['+NOBRACKET)*6
        + (NOBRACKET+ r'\])*'+NOBRACKET)*6
        + NOBRACKET + r')\]' )

BACKTICK_RE = r'\`([^\`]*)\`'                    # `e= m*c^2`
DOUBLE_BACKTICK_RE =  r'\`\`(.*)\`\`'            # ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'\*([^\*]*)\*'                    # *emphasis*
STRONG_RE = r'\*\*(.*)\*\*'                      # **strong**
STRONG_EM_RE = r'\*\*\*([^_]*)\*\*\*'            # ***strong***

if SMART_EMPHASIS:
    EMPHASIS_2_RE = r'(?<!\S)_(\S[^_]*)_'        # _emphasis_
else :
    EMPHASIS_2_RE = r'_([^_]*)_'                 # _emphasis_

STRONG_2_RE = r'__([^_]*)__'                     # __strong__
STRONG_EM_2_RE = r'___([^_]*)___'                # ___strong___

LINK_RE = BRK + r'\s*\(([^\)]*)\)'               # [text](url)
LINK_ANGLED_RE = BRK + r'\s*\(<([^\)]*)>\)'      # [text](<url>)
IMAGE_LINK_RE = r'\!' + BRK + r'\s*\(([^\)]*)\)' # ![alttxt](http://x.com/)
REFERENCE_RE = BRK+ r'\s*\[([^\]]*)\]'           # [Google][3]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s*\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'( \* )'                        # stand-alone * or _
AUTOLINK_RE = r'<(http://[^>]*)>'                # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>
#HTML_RE = r'(\<[^\>]*\>)'                        # <...>
HTML_RE = r'(\<[a-zA-Z/][^\>]*\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'                # &amp;

class Pattern:

    def __init__ (self, pattern) :
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*)%s(.*)$" % pattern, re.DOTALL)

    def getCompiledRegExp (self) :
        return self.compiled_re

BasePattern = Pattern # for backward compatibility

class SimpleTextPattern (Pattern) :

    def handleMatch(self, m, doc) :
        return doc.createTextNode(m.group(2))

class SimpleTagPattern (Pattern):

    def __init__ (self, pattern, tag) :
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m, doc) :
        el = doc.createElement(self.tag)
        el.appendChild(doc.createTextNode(m.group(2)))
        return el

class BacktickPattern (Pattern):

    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m, doc) :
        el = doc.createElement(self.tag)
        text = m.group(2).strip()
        #text = text.replace("&", "&amp;")
        el.appendChild(doc.createTextNode(text))
        return el


class DoubleTagPattern (SimpleTagPattern) :

    def handleMatch(self, m, doc) :
        tag1, tag2 = self.tag.split(",")
        el1 = doc.createElement(tag1)
        el2 = doc.createElement(tag2)
        el1.appendChild(el2)
        el2.appendChild(doc.createTextNode(m.group(2)))
        return el1


class HtmlPattern (Pattern):

    def handleMatch (self, m, doc) :
        place_holder = self.stash.store(m.group(2))
        return doc.createTextNode(place_holder)


class LinkPattern (Pattern):

    def handleMatch(self, m, doc) :
        el = doc.createElement('a')
        el.appendChild(doc.createTextNode(m.group(2)))
        parts = m.group(9).split('"')
        # We should now have [], [href], or [href, title]
        if parts :
            el.setAttribute('href', parts[0].strip())
        else :
            el.setAttribute('href', "")
        if len(parts) > 1 :
            # we also got a title
            title = '"' + '"'.join(parts[1:]).strip()
            title = dequote(title) #.replace('"', "&quot;")
            el.setAttribute('title', title)
        return el


class ImagePattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('img')
        src_parts = m.group(9).split()
        el.setAttribute('src', src_parts[0])
        if len(src_parts) > 1 :
            el.setAttribute('title', dequote(" ".join(src_parts[1:])))
        if ENABLE_ATTRIBUTES :
            text = doc.createTextNode(m.group(2))
            el.appendChild(text)
            text.handleAttributes()
            truealt = text.value
            el.childNodes.remove(text)
        else:
            truealt = m.group(2)
        el.setAttribute('alt', truealt)
        return el

class ReferencePattern (Pattern):

    def handleMatch(self, m, doc):

        if m.group(9) :
            id = m.group(9).lower()
        else :
            # if we got something like "[Google][]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        if not self.references.has_key(id) : # ignore undefined refs
            return None
        href, title = self.references[id]
        text = m.group(2)
        return self.makeTag(href, title, text, doc)

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('a')
        el.setAttribute('href', href)
        if title :
            el.setAttribute('title', title)
        el.appendChild(doc.createTextNode(text))
        return el


class ImageReferencePattern (ReferencePattern):

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('img')
        el.setAttribute('src', href)
        if title :
            el.setAttribute('title', title)
        el.setAttribute('alt', text)
        return el


class AutolinkPattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('a')
        el.setAttribute('href', m.group(2))
        el.appendChild(doc.createTextNode(m.group(2)))
        return el

class AutomailPattern (Pattern):

    def handleMatch(self, m, doc) :
        el = doc.createElement('a')
        email = m.group(2)
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]
        for letter in email:
            entity = doc.createEntityReference("#%d" % ord(letter))
            el.appendChild(entity)
        mailto = "mailto:" + email
        mailto = "".join(['&#%d;' % ord(letter) for letter in mailto])
        el.setAttribute('href', mailto)
        return el

ESCAPE_PATTERN          = SimpleTextPattern(ESCAPE_RE)
NOT_STRONG_PATTERN      = SimpleTextPattern(NOT_STRONG_RE)

BACKTICK_PATTERN        = BacktickPattern(BACKTICK_RE)
DOUBLE_BACKTICK_PATTERN = BacktickPattern(DOUBLE_BACKTICK_RE)
STRONG_PATTERN          = SimpleTagPattern(STRONG_RE, 'strong')
STRONG_PATTERN_2        = SimpleTagPattern(STRONG_2_RE, 'strong')
EMPHASIS_PATTERN        = SimpleTagPattern(EMPHASIS_RE, 'em')
EMPHASIS_PATTERN_2      = SimpleTagPattern(EMPHASIS_2_RE, 'em')

STRONG_EM_PATTERN       = DoubleTagPattern(STRONG_EM_RE, 'strong,em')
STRONG_EM_PATTERN_2     = DoubleTagPattern(STRONG_EM_2_RE, 'strong,em')

LINK_PATTERN            = LinkPattern(LINK_RE)
LINK_ANGLED_PATTERN     = LinkPattern(LINK_ANGLED_RE)
IMAGE_LINK_PATTERN      = ImagePattern(IMAGE_LINK_RE)
IMAGE_REFERENCE_PATTERN = ImageReferencePattern(IMAGE_REFERENCE_RE)
REFERENCE_PATTERN       = ReferencePattern(REFERENCE_RE)

HTML_PATTERN            = HtmlPattern(HTML_RE)
ENTITY_PATTERN          = HtmlPattern(ENTITY_RE)

AUTOLINK_PATTERN        = AutolinkPattern(AUTOLINK_RE)
AUTOMAIL_PATTERN        = AutomailPattern(AUTOMAIL_RE)


"""
======================================================================
========================== POST-PROCESSORS ===========================
======================================================================

Markdown also allows post-processors, which are similar to
preprocessors in that they need to implement a "run" method.  Unlike
pre-processors, they take a NanoDom document as a parameter and work
with that.

Post-Processor should extend markdown.Postprocessor.

There are currently no standard post-processors, but the footnote
extension below uses one.
"""

class Postprocessor :
    pass


"""
======================================================================
========================== MISC AUXILIARY CLASSES ====================
======================================================================
"""

class HtmlStash :
    """This class is used for stashing HTML objects that we extract
        in the beginning and replace with place-holders."""

    def __init__ (self) :
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

    def store(self, html) :
        """Saves an HTML segment for later reinsertion.  Returns a
           placeholder string that needs to be inserted into the
           document.

           @param html: an html segment
           @returns : a placeholder string """
        self.rawHtmlBlocks.append(html)
        placeholder = HTML_PLACEHOLDER % self.html_counter
        self.html_counter += 1
        return placeholder


class BlockGuru :

    def _findHead(self, lines, fn, allowBlank=0) :

        """Functional magic to help determine boundaries of indented
           blocks.

           @param lines: an array of strings
           @param fn: a function that returns a substring of a string
                      if the string matches the necessary criteria
           @param allowBlank: specifies whether it's ok to have blank
                      lines between matching functions
           @returns: a list of post processes items and the unused
                      remainder of the original list"""

        items = []
        item = -1

        i = 0 # to keep track of where we are

        for line in lines :

            if not line.strip() and not allowBlank:
                return items, lines[i:]

            if not line.strip() and allowBlank:
                # If we see a blank line, this _might_ be the end
                i += 1

                # Find the next non-blank line
                for j in range(i, len(lines)) :
                    if lines[j].strip() :
                        next = lines[j]
                        break
                else :
                    # There is no more text => this is the end
                    break

                # Check if the next non-blank line is still a part of the list

                part = fn(next)

                if part :
                    items.append("")
                    continue
                else :
                    break # found end of the list

            part = fn(line)

            if part :
                items.append(part)
                i += 1
                continue
            else :
                return items, lines[i:]
        else :
            i += 1

        return items, lines[i:]


    def detabbed_fn(self, line) :
        """ An auxiliary method to be passed to _findHead """
        m = RE.regExp['tabbed'].match(line)
        if m:
            return m.group(4)
        else :
            return None


    def detectTabbed(self, lines) :

        return self._findHead(lines, self.detabbed_fn,
                              allowBlank = 1)


def print_error(string):
    """Print an error string to stderr"""
    sys.stderr.write(string +'\n')


def dequote(string) :
    """ Removes quotes from around a string """
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ) :
        return string[1:-1]
    else :
        return string

"""
======================================================================
========================== CORE MARKDOWN =============================
======================================================================

This stuff is ugly, so if you are thinking of extending the syntax,
see first if you can do it via pre-processors, post-processors,
inline patterns or a combination of the three.
"""

class CorePatterns :
    """This class is scheduled for removal as part of a refactoring
        effort."""

    patterns = {
        'header':          r'(#*)([^#]*)(#*)', # # A title
        'reference-def' :  r'(\ ?\ ?\ ?)\[([^\]]*)\]:\s*([^ ]*)(.*)',
                           # [Google]: http://www.google.com/
        'containsline':    r'([-]*)$|^([=]*)', # -----, =====, etc.
        'ol':              r'[ ]{0,3}[\d]*\.\s+(.*)', # 1. text
        'ul':              r'[ ]{0,3}[*+-]\s+(.*)', # "* text"
        'isline1':         r'(\**)', # ***
        'isline2':         r'(\-*)', # ---
        'isline3':         r'(\_*)', # ___
        'tabbed':          r'((\t)|(    ))(.*)', # an indented line
        'quoted' :         r'> ?(.*)', # a quoted block ("> ...")
    }

    def __init__ (self) :

        self.regExp = {}
        for key in self.patterns.keys() :
            self.regExp[key] = re.compile("^%s$" % self.patterns[key],
                                          re.DOTALL)

        self.regExp['containsline'] = re.compile(r'^([-]*)$|^([=]*)$', re.M)

RE = CorePatterns()


class Markdown:
    """ Markdown formatter class for creating an html document from
        Markdown text """


    def __init__(self, source=None,  # deprecated
                 extensions=[],
                 extension_configs=None,
                 encoding="utf-8",
                 safe_mode = False):
        """Creates a new Markdown instance.

           @param source: The text in Markdown format.
           @param encoding: The character encoding of <text>. """

        self.safeMode = safe_mode
        self.encoding = encoding
        self.source = source
        self.blockGuru = BlockGuru()
        self.registeredExtensions = []
        self.stripTopLevelTags = 1
        self.docType = ""

        self.preprocessors = [ HTML_BLOCK_PREPROCESSOR,
                               HEADER_PREPROCESSOR,
                               LINE_PREPROCESSOR,
                               LINE_BREAKS_PREPROCESSOR,
                               # A footnote preprocessor will
                               # get inserted here
                               REFERENCE_PREPROCESSOR ]


        self.postprocessors = [] # a footnote postprocessor will get
                                 # inserted later

        self.textPostprocessors = [] # a footnote postprocessor will get
                                     # inserted later                                 

        self.prePatterns = []
        

        self.inlinePatterns = [ DOUBLE_BACKTICK_PATTERN,
                                BACKTICK_PATTERN,
                                ESCAPE_PATTERN,
                                IMAGE_LINK_PATTERN,
                                IMAGE_REFERENCE_PATTERN,
                                REFERENCE_PATTERN,
                                LINK_ANGLED_PATTERN,
                                LINK_PATTERN,
                                AUTOLINK_PATTERN,
                                AUTOMAIL_PATTERN,
                                HTML_PATTERN,
                                ENTITY_PATTERN,
                                NOT_STRONG_PATTERN,
                                STRONG_EM_PATTERN,
                                STRONG_EM_PATTERN_2,
                                STRONG_PATTERN,
                                STRONG_PATTERN_2,
                                EMPHASIS_PATTERN,
                                EMPHASIS_PATTERN_2
                                # The order of the handlers matters!!!
                                ]

        self.registerExtensions(extensions = extensions,
                                configs = extension_configs)

        self.reset()


    def registerExtensions(self, extensions, configs) :

        if not configs :
            configs = {}

        for ext in extensions :

            extension_module_name = "mdx_" + ext

            try :
                module = __import__(extension_module_name)

            except :
                message(CRITICAL,
                        "couldn't load extension %s (looking for %s module)"
                        % (ext, extension_module_name) )
            else :

                if configs.has_key(ext) :
                    configs_for_ext = configs[ext]
                else :
                    configs_for_ext = []
                extension = module.makeExtension(configs_for_ext)    
                extension.extendMarkdown(self, globals())




    def registerExtension(self, extension) :
        """ This gets called by the extension """
        self.registeredExtensions.append(extension)

    def reset(self) :
        """Resets all state variables so that we can start
            with a new text."""
        self.references={}
        self.htmlStash = HtmlStash()

        HTML_BLOCK_PREPROCESSOR.stash = self.htmlStash
        REFERENCE_PREPROCESSOR.references = self.references
        HTML_PATTERN.stash = self.htmlStash
        ENTITY_PATTERN.stash = self.htmlStash
        REFERENCE_PATTERN.references = self.references
        IMAGE_REFERENCE_PATTERN.references = self.references

        for extension in self.registeredExtensions :
            extension.reset()


    def _transform(self):
        """Transforms the Markdown text into a XHTML body document

           @returns: A NanoDom Document """

        # Setup the document

        self.doc = Document()
        self.top_element = self.doc.createElement("span")
        self.top_element.appendChild(self.doc.createTextNode('\n'))
        self.top_element.setAttribute('class', 'markdown')
        self.doc.appendChild(self.top_element)

        # Fixup the source text
        text = self.source.strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text += "\n\n"
        text = text.expandtabs(TAB_LENGTH)

        # Split into lines and run the preprocessors that will work with
        # self.lines

        self.lines = text.split("\n")

        # Run the pre-processors on the lines
        for prep in self.preprocessors :
            self.lines = prep.run(self.lines)

        # Create a NanoDom tree from the lines and attach it to Document


        buffer = []
        for line in self.lines :
            if line.startswith("#") :
                self._processSection(self.top_element, buffer)
                buffer = [line]
            else :
                buffer.append(line)
        self._processSection(self.top_element, buffer)
        
        #self._processSection(self.top_element, self.lines)

        # Not sure why I put this in but let's leave it for now.
        self.top_element.appendChild(self.doc.createTextNode('\n'))

        # Run the post-processors
        for postprocessor in self.postprocessors :
            postprocessor.run(self.doc)

        return self.doc


    def _processSection(self, parent_elem, lines,
                        inList = 0, looseList = 0) :

        """Process a section of a source document, looking for high
           level structural elements like lists, block quotes, code
           segments, html blocks, etc.  Some those then get stripped
           of their high level markup (e.g. get unindented) and the
           lower-level markup is processed recursively.

           @param parent_elem: A NanoDom element to which the content
                               will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        if not lines :
            return

        # Check if this section starts with a list, a blockquote or
        # a code block

        processFn = { 'ul' :     self._processUList,
                      'ol' :     self._processOList,
                      'quoted' : self._processQuote,
                      'tabbed' : self._processCodeBlock }

        for regexp in ['ul', 'ol', 'quoted', 'tabbed'] :
            m = RE.regExp[regexp].match(lines[0])
            if m :
                processFn[regexp](parent_elem, lines, inList)
                return

        # We are NOT looking at one of the high-level structures like
        # lists or blockquotes.  So, it's just a regular paragraph
        # (though perhaps nested inside a list or something else).  If
        # we are NOT inside a list, we just need to look for a blank
        # line to find the end of the block.  If we ARE inside a
        # list, however, we need to consider that a sublist does not
        # need to be separated by a blank line.  Rather, the following
        # markup is legal:
        #
        # * The top level list item
        #
        #     Another paragraph of the list.  This is where we are now.
        #     * Underneath we might have a sublist.
        #

        if inList :

            start, theRest = self._linesUntil(lines, (lambda line:
                             RE.regExp['ul'].match(line)
                             or RE.regExp['ol'].match(line)
                                              or not line.strip()))

            self._processSection(parent_elem, start,
                                 inList - 1, looseList = looseList)
            self._processSection(parent_elem, theRest,
                                 inList - 1, looseList = looseList)


        else : # Ok, so it's just a simple block

            paragraph, theRest = self._linesUntil(lines, lambda line:
                                                 not line.strip())

            if len(paragraph) and paragraph[0].startswith('#') :
                m = RE.regExp['header'].match(paragraph[0])
                if m :
                    level = len(m.group(1))
                    h = self.doc.createElement("h%d" % level)
                    parent_elem.appendChild(h)
                    for item in self._handleInlineWrapper(m.group(2).strip()) :
                        h.appendChild(item)
                else :
                    message(CRITICAL, "We've got a problem header!")

            elif paragraph :

                list = self._handleInlineWrapper("\n".join(paragraph))

                if ( parent_elem.nodeName == 'li'
                     and not (looseList or parent_elem.childNodes)):

                    #and not parent_elem.childNodes) :
                    # If this is the first paragraph inside "li", don't
                    # put <p> around it - append the paragraph bits directly
                    # onto parent_elem
                    el = parent_elem
                else :
                    # Otherwise make a "p" element
                    el = self.doc.createElement("p")
                    parent_elem.appendChild(el)

                for item in list :
                    el.appendChild(item)

            if theRest :
                theRest = theRest[1:]  # skip the first (blank) line

            self._processSection(parent_elem, theRest, inList)



    def _processUList(self, parent_elem, lines, inList) :
        self._processList(parent_elem, lines, inList,
                         listexpr='ul', tag = 'ul')

    def _processOList(self, parent_elem, lines, inList) :
        self._processList(parent_elem, lines, inList,
                         listexpr='ol', tag = 'ol')


    def _processList(self, parent_elem, lines, inList, listexpr, tag) :
        """Given a list of document lines starting with a list item,
           finds the end of the list, breaks it up, and recursively
           processes each list item and the remainder of the text file.

           @param parent_elem: A dom element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        ul = self.doc.createElement(tag)  # ul might actually be '<ol>'
        parent_elem.appendChild(ul)

        looseList = 0

        # Make a list of list items
        items = []
        item = -1

        i = 0  # a counter to keep track of where we are

        for line in lines :

            loose = 0
            if not line.strip() :
                # If we see a blank line, this _might_ be the end of the list
                i += 1
                loose = 1

                # Find the next non-blank line
                for j in range(i, len(lines)) :
                    if lines[j].strip() :
                        next = lines[j]
                        break
                else :
                    # There is no more text => end of the list
                    break

                # Check if the next non-blank line is still a part of the list
                if ( RE.regExp['ul'].match(next) or
                     RE.regExp['ol'].match(next) or 
                     RE.regExp['tabbed'].match(next) ):
                    # get rid of any white space in the line
                    items[item].append(line.strip())
                    looseList = loose or looseList
                    continue
                else :
                    break # found end of the list

            # Now we need to detect list items (at the current level)
            # while also detabing child elements if necessary

            for expr in ['ul', 'ol', 'tabbed']:

                m = RE.regExp[expr].match(line)
                if m :
                    if expr in ['ul', 'ol'] :  # We are looking at a new item
                        #if m.group(1) :
                        # Removed the check to allow for a blank line
                        # at the beginning of the list item
                        items.append([m.group(1)])
                        item += 1
                    elif expr == 'tabbed' :  # This line needs to be detabbed
                        items[item].append(m.group(4)) #after the 'tab'

                    i += 1
                    break
            else :
                items[item].append(line)  # Just regular continuation
                i += 1 # added on 2006.02.25
        else :
            i += 1

        # Add the dom elements
        for item in items :
            li = self.doc.createElement("li")
            ul.appendChild(li)

            self._processSection(li, item, inList + 1, looseList = looseList)

        # Process the remaining part of the section

        self._processSection(parent_elem, lines[i:], inList)


    def _linesUntil(self, lines, condition) :
        """ A utility function to break a list of lines upon the
            first line that satisfied a condition.  The condition
            argument should be a predicate function.
            """

        i = -1
        for line in lines :
            i += 1
            if condition(line) : break
        else :
            i += 1
        return lines[:i], lines[i:]

    def _processQuote(self, parent_elem, lines, inList) :
        """Given a list of document lines starting with a quote finds
           the end of the quote, unindents it and recursively
           processes the body of the quote and the remainder of the
           text file.

           @param parent_elem: DOM element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None """

        dequoted = []
        i = 0
        for line in lines :
            m = RE.regExp['quoted'].match(line)
            if m :
                dequoted.append(m.group(1))
                i += 1
            else :
                break
        else :
            i += 1

        blockquote = self.doc.createElement('blockquote')
        parent_elem.appendChild(blockquote)

        self._processSection(blockquote, dequoted, inList)
        self._processSection(parent_elem, lines[i:], inList)




    def _processCodeBlock(self, parent_elem, lines, inList) :
        """Given a list of document lines starting with a code block
           finds the end of the block, puts it into the dom verbatim
           wrapped in ("<pre><code>") and recursively processes the
           the remainder of the text file.

           @param parent_elem: DOM element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        detabbed, theRest = self.blockGuru.detectTabbed(lines)

        pre = self.doc.createElement('pre')
        code = self.doc.createElement('code')
        parent_elem.appendChild(pre)
        pre.appendChild(code)
        text = "\n".join(detabbed).rstrip()+"\n"
        #text = text.replace("&", "&amp;")
        code.appendChild(self.doc.createTextNode(text))
        self._processSection(parent_elem, theRest, inList)



    def _handleInlineWrapper (self, line) :

        parts = [line]

        for pattern in self.inlinePatterns :

            i = 0

            while i < len(parts) :
                
                x = parts[i]

                if isinstance(x, (str, unicode)) :
                    result = self._applyPattern(x, pattern)

                    if result :
                        i -= 1
                        parts.remove(x)
                        for y in result :
                            parts.insert(i+1,y)

                i += 1

        for i in range(len(parts)) :
            x = parts[i]
            if isinstance(x, (str, unicode)) :
                parts[i] = self.doc.createTextNode(x)

        return parts
        

    def _handleInline(self,  line):
        """Transform a Markdown line with inline elements to an XHTML
        fragment.

        This function uses auxiliary objects called inline patterns.
        See notes on inline patterns above.

        @param item: A block of Markdown text
        @return: A list of NanoDom nodes """

        if not(line):
            return [self.doc.createTextNode(' ')]

        for pattern in self.inlinePatterns :
            list = self._applyPattern( line, pattern)
            if list: return list

        return [self.doc.createTextNode(line)]

    def _applyPattern(self, line, pattern) :

        """ Given a pattern name, this function checks if the line
        fits the pattern, creates the necessary elements, and returns
        back a list consisting of NanoDom elements and/or strings.
        
        @param line: the text to be processed
        @param pattern: the pattern to be checked

        @returns: the appropriate newly created NanoDom element if the
                  pattern matches, None otherwise.
        """

        # match the line to pattern's pre-compiled reg exp.
        # if no match, move on.



        m = pattern.getCompiledRegExp().match(line)
        if not m :
            return None

        # if we got a match let the pattern make us a NanoDom node
        # if it doesn't, move on
        node = pattern.handleMatch(m, self.doc)

        # check if any of this nodes have children that need processing

        if isinstance(node, Element):

            if not node.nodeName in ["code", "pre"] :
                for child in node.childNodes :
                    if isinstance(child, TextNode):
                        
                        result = self._handleInlineWrapper(child.value)
                        
                        if result:

                            if result == [child] :
                                continue
                                
                            result.reverse()
                            #to make insertion easier

                            position = node.childNodes.index(child)
                            
                            node.removeChild(child)

                            for item in result:

                                if isinstance(item, (str, unicode)):
                                    if len(item) > 0:
                                        node.insertChild(position,
                                             self.doc.createTextNode(item))
                                else:
                                    node.insertChild(position, item)
                



        if node :
            # Those are in the reverse order!
            return ( m.groups()[-1], # the string to the left
                     node,           # the new node
                     m.group(1))     # the string to the right of the match

        else :
            return None

    def convert (self, source = None):
        """Return the document in XHTML format.

        @returns: A serialized XHTML body."""
        #try :

        if source is not None :
            self.source = source

        if not self.source :
            return ""

        self.source = removeBOM(self.source, self.encoding)

        
        doc = self._transform()
        xml = doc.toxml()

        #finally:
        #    doc.unlink()

        # Let's stick in all the raw html pieces

        for i in range(self.htmlStash.html_counter) :
            html = self.htmlStash.rawHtmlBlocks[i]
            if self.safeMode :
                html = HTML_REMOVED_TEXT
                
            xml = xml.replace("<p>%s\n</p>" % (HTML_PLACEHOLDER % i),
                              html + "\n")
            xml = xml.replace(HTML_PLACEHOLDER % i,
                              html)

        # And return everything but the top level tag

        if self.stripTopLevelTags :
            xml = xml.strip()[23:-7] + "\n"

        for pp in self.textPostprocessors :
            xml = pp.run(xml)

        return self.docType + xml


    __str__ = convert   # deprecated - will be changed in 1.7 to report
                        # information about the MD instance
    
    toString = __str__  # toString() method is deprecated


    def __unicode__(self):
        """Return the document in XHTML format as a Unicode object.
        """
        return str(self)#.decode(self.encoding)


    toUnicode = __unicode__  # deprecated - will be removed in 1.7




# ====================================================================

def markdownFromFile(input = None,
                     output = None,
                     extensions = [],
                     encoding = None,
                     message_threshold = CRITICAL,
                     safe = False) :

    global MESSAGE_THRESHOLD
    MESSAGE_THRESHOLD = message_threshold

    message(VERBOSE, "input file: %s" % input)


    if not encoding :
        encoding = "utf-8"

    input_file = codecs.open(input, mode="r", encoding=encoding)
    text = input_file.read()
    input_file.close()

    new_text = markdown(text, extensions, encoding, safe_mode = safe)

    if output :
        output_file = codecs.open(output, "w", encoding=encoding)
        output_file.write(new_text)
        output_file.close()

    else :
        sys.stdout.write(new_text.encode(encoding))

def markdown(text,
             extensions = [],
             encoding = None,
             safe_mode = False) :
    
    message(VERBOSE, "in markdown.markdown(), received text:\n%s" % text)

    extension_names = []
    extension_configs = {}
    
    for ext in extensions :
        pos = ext.find("(") 
        if pos == -1 :
            extension_names.append(ext)
        else :
            name = ext[:pos]
            extension_names.append(name)
            pairs = [x.split("=") for x in ext[pos+1:-1].split(",")]
            configs = [(x.strip(), y.strip()) for (x, y) in pairs]
            extension_configs[name] = configs

    md = Markdown(extensions=extension_names,
                  extension_configs=extension_configs,
                  safe_mode = safe_mode)

    return md.convert(text)
        

class Extension :

    def __init__(self, configs = {}) :
        self.config = configs

    def getConfig(self, key) :
        if self.config.has_key(key) :
            return self.config[key][0]
        else :
            return ""

    def getConfigInfo(self) :
        return [(key, self.config[key][1]) for key in self.config.keys()]

    def setConfig(self, key, value) :
        self.config[key][0] = value


OPTPARSE_WARNING = """
Python 2.3 or higher required for advanced command line options.
For lower versions of Python use:

      %s INPUT_FILE > OUTPUT_FILE
    
""" % EXECUTABLE_NAME_FOR_USAGE

def parse_options() :

    try :
        optparse = __import__("optparse")
    except :
        if len(sys.argv) == 2 :
            return {'input' : sys.argv[1],
                    'output' : None,
                    'message_threshold' : CRITICAL,
                    'safe' : False,
                    'extensions' : [],
                    'encoding' : None }

        else :
            print OPTPARSE_WARNING
            return None

    parser = optparse.OptionParser(usage="%prog INPUTFILE [options]")

    parser.add_option("-f", "--file", dest="filename",
                      help="write output to OUTPUT_FILE",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="encoding for input and output files",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=NONE, dest="verbose",
                      help="suppress all messages")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="print info messages")
    parser.add_option("-s", "--safe",
                      action="store_const", const=True, dest="safe",
                      help="same mode (strip user's HTML tag)")
    
    parser.add_option("--noisy",
                      action="store_const", const=VERBOSE, dest="verbose",
                      help="print debug messages")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "load extension EXTENSION", metavar="EXTENSION")

    (options, args) = parser.parse_args()

    if not len(args) == 1 :
        parser.print_help()
        return None
    else :
        input_file = args[0]

    if not options.extensions :
        options.extensions = []

    return {'input' : input_file,
            'output' : options.filename,
            'message_threshold' : options.verbose,
            'safe' : options.safe,
            'extensions' : options.extensions,
            'encoding' : options.encoding }

if __name__ == '__main__':
    """ Run Markdown from the command line. """

    options = parse_options()

    #if os.access(inFile, os.R_OK):

    if not options :
        sys.exit(0)
    
    markdownFromFile(**options)











########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# Copyright (c) 2007-2008 ActiveState Software Inc.
# License: MIT (http://www.opensource.org/licenses/mit-license.php)

"""The markdown2 test suite entry point."""

import os
from os.path import exists, join, abspath, dirname, normpath
import sys
import logging

import testlib

log = logging.getLogger("test")
testdir_from_ns = {
    None: os.curdir,
}

def setup():
    top_dir = dirname(dirname(abspath(__file__)))
    lib_dir = join(top_dir, "lib")
    sys.path.insert(0, lib_dir)

    # Attempt to get 'pygments' on the import path.
    try:
        # If already have it, use that one.
        import pygments
    except ImportError:
        pygments_dir = join(top_dir, "deps", "pygments")
        if sys.version_info[0] <= 2:
            sys.path.insert(0, pygments_dir)
        else:
            sys.path.insert(0, pygments_dir + "3")

if __name__ == "__main__":
    logging.basicConfig()

    setup()
    default_tags = []
    try:
        import pygments
    except ImportError:
        log.warn("skipping pygments tests ('pygments' module not found)")
        default_tags.append("-pygments")

    retval = testlib.harness(testdir_from_ns=testdir_from_ns,
                             default_tags=default_tags)
    sys.exit(retval)

########NEW FILE########
__FILENAME__ = testall
#!/usr/bin/env python
#
# Run the test suite against all the Python versions we can find.
#

import sys
import os
from os.path import dirname, abspath, join
import re


TOP = dirname(dirname(abspath(__file__)))
sys.path.insert(0, join(TOP, "tools"))
import which


def _python_ver_from_python(python):
    assert ' ' not in python
    o = os.popen('''%s -c "import sys; print(sys.version)"''' % python)
    ver_str = o.read().strip()
    ver_bits = re.split("\.|[^\d]", ver_str, 2)[:2]
    ver = tuple(map(int, ver_bits))
    return ver

def _gen_python_names():
    yield "python"
    for ver in [(2,2), (2,3), (2,4), (2,5), (2,6), (2,7), (3,0), (3,1),
                (3,2), (3,3)]:
        yield "python%d.%d" % ver
        if sys.platform == "win32":
            yield "python%d%d" % ver

def _gen_pythons():
    python_from_ver = {}
    for name in _gen_python_names():
        for python in which.whichall(name):
            ver = _python_ver_from_python(python)
            if ver not in python_from_ver:
                python_from_ver[ver] = python
    for ver, python in sorted(python_from_ver.items()):
        yield ver, python

def testall():
    for ver, python in _gen_pythons():
        if ver < (2,3):
            # Don't support Python < 2.3.
            continue
        ver_str = "%s.%s" % ver
        print "-- test with Python %s (%s)" % (ver_str, python)
        assert ' ' not in python
        rv = os.system("%s test.py -- -knownfailure" % python)
        if rv:
            sys.exit(os.WEXITSTATUS(rv))

testall()

########NEW FILE########
__FILENAME__ = testlib
#!python
# Copyright (c) 2000-2008 ActiveState Software Inc.
# License: MIT License (http://www.opensource.org/licenses/mit-license.php)

"""
    test suite harness

    Usage:

        test --list [<tags>...]  # list available tests modules
        test [<tags>...]         # run test modules

    Options:
        -v, --verbose   more verbose output
        -q, --quiet     don't print anything except if a test fails
        -d, --debug     log debug information        
        -h, --help      print this text and exit
        -l, --list      Just list the available test modules. You can also
                        specify tags to play with module filtering.
        -n, --no-default-tags   Ignore default tags
        -L <directive>  Specify a logging level via
                            <logname>:<levelname>
                        For example:
                            codeintel.db:DEBUG
                        This option can be used multiple times.

    By default this will run all tests in all available "test_*" modules.
    Tags can be specified to control which tests are run. For example:
    
        test python         # run tests with the 'python' tag
        test python cpln    # run tests with both 'python' and 'cpln' tags
        test -- -python     # exclude tests with the 'python' tag
                            # (the '--' is necessary to end the option list)
    
    The full name and base name of a test module are implicit tags for that
    module, e.g. module "test_xdebug.py" has tags "test_xdebug" and "xdebug".
    A TestCase's class name (with and without "TestCase") is an implicit
    tag for an test_* methods. A "test_foo" method also has "test_foo"
    and "foo" implicit tags.

    Tags can be added explicitly added:
    - to modules via a __tags__ global list; and
    - to individual test_* methods via a "tags" attribute list (you can
      use the testlib.tag() decorator for this).
"""
#TODO:
# - Document how tests are found (note the special "test_cases()" and
#   "test_suite_class" hooks).
# - See the optparse "TODO" below.
# - Make the quiet option actually quiet.

__version_info__ = (0, 6, 6)
__version__ = '.'.join(map(str, __version_info__))


import os
from os.path import join, basename, dirname, abspath, splitext, \
                    isfile, isdir, normpath, exists
import sys
import getopt
import glob
import time
import types
import tempfile
import unittest
from pprint import pprint
import imp
import optparse
import logging
import textwrap
import traceback



#---- globals and exceptions

log = logging.getLogger("test")



#---- exports generally useful to test cases

class TestError(Exception):
    pass

class TestSkipped(Exception):
    """Raise this to indicate that a test is being skipped.

    ConsoleTestRunner knows to interpret these at NOT failures.
    """
    pass

class TestFailed(Exception):
    pass

def tag(*tags):
    """Decorator to add tags to test_* functions.
    
    Example:
        class MyTestCase(unittest.TestCase):
            @testlib.tag("knownfailure")
            def test_foo(self):
                #...
    """
    def decorate(f):
        if not hasattr(f, "tags"):
            f.tags = []
        f.tags += tags
        return f
    return decorate


#---- timedtest decorator
# Use this to assert that a test completes in a given amount of time.
# This is from http://www.artima.com/forums/flat.jsp?forum=122&thread=129497
# Including here, becase it might be useful.
# NOTE: Untested and I suspect some breakage.

TOLERANCE = 0.05

class DurationError(AssertionError): pass

def timedtest(max_time, tolerance=TOLERANCE):
    """ timedtest decorator
    decorates the test method with a timer
    when the time spent by the test exceeds
    max_time in seconds, an Assertion error is thrown.
    """
    def _timedtest(function):
        def wrapper(*args, **kw):
            start_time = time.time()
            try:
                function(*args, **kw)
            finally:
                total_time = time.time() - start_time
                if total_time > max_time + tolerance:
                    raise DurationError(('Test was too long (%.2f s)'
                                           % total_time))
        return wrapper

    return _timedtest



#---- module api

class Test(object):
    def __init__(self, ns, testmod, testcase, testfn_name,
                 testsuite_class=None):
        self.ns = ns
        self.testmod = testmod
        self.testcase = testcase
        self.testfn_name = testfn_name
        self.testsuite_class = testsuite_class
        # Give each testcase some extra testlib attributes for useful
        # introspection on TestCase instances later on.
        self.testcase._testlib_shortname_ = self.shortname()
        self.testcase._testlib_explicit_tags_ = self.explicit_tags()
        self.testcase._testlib_implicit_tags_ = self.implicit_tags()
    def __str__(self):
        return self.shortname()
    def __repr__(self):
        return "<Test %s>" % self.shortname()
    def shortname(self):
        bits = [self._normname(self.testmod.__name__),
                self._normname(self.testcase.__class__.__name__),
                self._normname(self.testfn_name)]
        if self.ns:
            bits.insert(0, self.ns)
        return '/'.join(bits)
    def _flatten_tags(self, tags):
        """Split tags with '/' in them into multiple tags.
        
        '/' is the reserved tag separator and allowing tags with
        embedded '/' results in one being unable to select those via
        filtering. As long as tag order is stable then presentation of
        these subsplit tags should be fine.
        """
        flattened = []
        for t in tags:
            flattened += t.split('/')
        return flattened
    def explicit_tags(self):
        tags = []
        if hasattr(self.testmod, "__tags__"):
            tags += self.testmod.__tags__
        if hasattr(self.testcase, "__tags__"):
            tags += self.testcase.__tags__
        testfn = getattr(self.testcase, self.testfn_name)
        if hasattr(testfn, "tags"):
            tags += testfn.tags
        return self._flatten_tags(tags)
    def implicit_tags(self):
        tags = [
            self.testmod.__name__.lower(),
            self._normname(self.testmod.__name__),
            self.testcase.__class__.__name__.lower(),
            self._normname(self.testcase.__class__.__name__),
            self.testfn_name,
            self._normname(self.testfn_name),
        ]
        if self.ns:
            tags.insert(0, self.ns)
        return self._flatten_tags(tags)
    def tags(self):
        return self.explicit_tags() + self.implicit_tags()
    def doc(self):
        testfn = getattr(self.testcase, self.testfn_name)
        return testfn.__doc__ or ""
    def _normname(self, name):
        if name.startswith("test_"):
            return name[5:].lower()
        elif name.startswith("test"):
            return name[4:].lower()
        elif name.endswith("TestCase"):
            return name[:-8].lower()
        else:
            return name


def testmod_paths_from_testdir(testdir):
    """Generate test module paths in the given dir."""
    for path in glob.glob(join(testdir, "test_*.py")):
        yield path

    for path in glob.glob(join(testdir, "test_*")):
        if not isdir(path): continue
        if not isfile(join(path, "__init__.py")): continue
        yield path

def testmods_from_testdir(testdir):
    """Generate test modules in the given test dir.
    
    Modules are imported with 'testdir' first on sys.path.
    """
    testdir = normpath(testdir)
    for testmod_path in testmod_paths_from_testdir(testdir):
        testmod_name = splitext(basename(testmod_path))[0]
        log.debug("import test module '%s'", testmod_path)
        try:
            iinfo = imp.find_module(testmod_name, [dirname(testmod_path)])
            testabsdir = abspath(testdir)
            sys.path.insert(0, testabsdir)
            old_dir = os.getcwd()
            os.chdir(testdir)
            try:
                testmod = imp.load_module(testmod_name, *iinfo)
            finally:
                os.chdir(old_dir)
                sys.path.remove(testabsdir)
        except TestSkipped:
            _, ex, _ = sys.exc_info()
            log.warn("'%s' module skipped: %s", testmod_name, ex)
        except Exception:
            _, ex, _ = sys.exc_info()
            log.warn("could not import test module '%s': %s (skipping, "
                     "run with '-d' for full traceback)",
                     testmod_path, ex)
            if log.isEnabledFor(logging.DEBUG):
                traceback.print_exc()
        else:
            yield testmod

def testcases_from_testmod(testmod):
    """Gather tests from a 'test_*' module.
    
    Returns a list of TestCase-subclass instances. One instance for each
    found test function.
    
    In general the normal unittest TestLoader.loadTests*() semantics are
    used for loading tests with some differences:
    - TestCase subclasses beginning with '_' are skipped (presumed to be
      internal).
    - If the module has a top-level "test_cases", it is called for a list of
      TestCase subclasses from which to load tests (can be a generator). This
      allows for run-time setup of test cases.
    - If the module has a top-level "test_suite_class", it is used to group
      all test cases from that module into an instance of that TestSuite
      subclass. This allows for overriding of test running behaviour.
    """
    class TestListLoader(unittest.TestLoader):
        suiteClass = list

    loader = TestListLoader()
    if hasattr(testmod, "test_cases"):
        try:
            for testcase_class in testmod.test_cases():
                if testcase_class.__name__.startswith("_"):
                    log.debug("skip private TestCase class '%s'",
                              testcase_class.__name__)
                    continue
                for testcase in loader.loadTestsFromTestCase(testcase_class):
                    yield testcase
        except Exception:
            _, ex, _ = sys.exc_info()
            testmod_path = testmod.__file__
            if testmod_path.endswith(".pyc"):
                testmod_path = testmod_path[:-1]
            log.warn("error running test_cases() in '%s': %s (skipping, "
                     "run with '-d' for full traceback)",
                     testmod_path, ex)
            if log.isEnabledFor(logging.DEBUG):
                traceback.print_exc()
    else:
        class_names_skipped = []
        for testcases in loader.loadTestsFromModule(testmod):
            for testcase in testcases:
                class_name = testcase.__class__.__name__
                if class_name in class_names_skipped:
                    pass
                elif class_name.startswith("_"):
                    log.debug("skip private TestCase class '%s'", class_name)
                    class_names_skipped.append(class_name)
                else:
                    yield testcase


def tests_from_manifest(testdir_from_ns):
    """Return a list of `testlib.Test` instances for each test found in
    the manifest.
    
    There will be a test for
    (a) each "test*" function of
    (b) each TestCase-subclass in
    (c) each "test_*" Python module in
    (d) each test dir in the manifest.
    
    If a "test_*" module has a top-level "test_suite_class", it will later
    be used to group all test cases from that module into an instance of that
    TestSuite subclass. This allows for overriding of test running behaviour.
    """
    for ns, testdir in testdir_from_ns.items():
        for testmod in testmods_from_testdir(testdir):
            if hasattr(testmod, "test_suite_class"):
                testsuite_class = testmod.test_suite_class
                if not issubclass(testsuite_class, unittest.TestSuite):
                    testmod_path = testmod.__file__
                    if testmod_path.endswith(".pyc"):
                        testmod_path = testmod_path[:-1]
                    log.warn("'test_suite_class' of '%s' module is not a "
                             "subclass of 'unittest.TestSuite': ignoring",
                             testmod_path)
            else:
                testsuite_class = None
            for testcase in testcases_from_testmod(testmod):
                try:
                    yield Test(ns, testmod, testcase,
                               testcase._testMethodName,
                               testsuite_class)
                except AttributeError:
                    # Python 2.4 and older:
                    yield Test(ns, testmod, testcase,
                               testcase._TestCase__testMethodName,
                               testsuite_class)

def tests_from_manifest_and_tags(testdir_from_ns, tags):
    include_tags = [tag.lower() for tag in tags if not tag.startswith('-')]
    exclude_tags = [tag[1:].lower() for tag in tags if tag.startswith('-')]

    for test in tests_from_manifest(testdir_from_ns):
        test_tags = [t.lower() for t in test.tags()]

        matching_exclude_tags = [t for t in exclude_tags if t in test_tags]
        if matching_exclude_tags:
            #log.debug("test '%s' matches exclude tag(s) '%s': skipping",
            #          test.shortname(), "', '".join(matching_exclude_tags))
            continue

        if not include_tags:
            yield test
        else:
            for tag in include_tags:
                if tag not in test_tags:
                    #log.debug("test '%s' does not match tag '%s': skipping",
                    #          test.shortname(), tag)
                    break
            else:
                #log.debug("test '%s' matches tags: %s", test.shortname(),
                #          ' '.join(tags))
                yield test
                
def test(testdir_from_ns, tags=[], setup_func=None):
    log.debug("test(testdir_from_ns=%r, tags=%r, ...)",
              testdir_from_ns, tags)
    if setup_func is not None:
        setup_func()
    tests = list(tests_from_manifest_and_tags(testdir_from_ns, tags))
    if not tests:
        return None
    
    # Groups test cases into a test suite class given by their test module's
    # "test_suite_class" hook, if any.
    suite = unittest.TestSuite()
    suite_for_testmod = None
    testmod = None
    for test in tests:
        if test.testmod != testmod:
            if suite_for_testmod is not None:
                suite.addTest(suite_for_testmod)
            suite_for_testmod = (test.testsuite_class or unittest.TestSuite)()
            testmod = test.testmod
        suite_for_testmod.addTest(test.testcase)
    if suite_for_testmod is not None:
        suite.addTest(suite_for_testmod)
    
    runner = ConsoleTestRunner(sys.stdout)
    result = runner.run(suite)
    return result

def list_tests(testdir_from_ns, tags):
    # Say I have two test_* modules:
    #   test_python.py:
    #       __tags__ = ["guido"]
    #       class BasicTestCase(unittest.TestCase):
    #           def test_def(self):
    #           def test_class(self):
    #       class ComplexTestCase(unittest.TestCase):
    #           def test_foo(self):
    #           def test_bar(self):
    #   test_perl/__init__.py:
    #       __tags__ = ["larry", "wall"]
    #       class BasicTestCase(unittest.TestCase):
    #           def test_sub(self):
    #           def test_package(self):
    #       class EclecticTestCase(unittest.TestCase):
    #           def test_foo(self):
    #           def test_bar(self):
    # The short-form list output for this should look like:
    #   python/basic/def [guido]
    #   python/basic/class [guido]
    #   python/complex/foo [guido]
    #   python/complex/bar [guido]
    #   perl/basic/sub [larry, wall]
    #   perl/basic/package [larry, wall]
    #   perl/eclectic/foo [larry, wall]
    #   perl/eclectic/bar [larry, wall]
    log.debug("list_tests(testdir_from_ns=%r, tags=%r)",
              testdir_from_ns, tags)

    tests = list(tests_from_manifest_and_tags(testdir_from_ns, tags))
    if not tests:
        return

    WIDTH = 78
    if log.isEnabledFor(logging.INFO): # long-form
        for i, t in enumerate(tests):
            if i:
                print()
            testfile = t.testmod.__file__
            if testfile.endswith(".pyc"):
                testfile = testfile[:-1]
            print("%s:" % t.shortname())
            print("  from: %s#%s.%s" % (testfile,
                t.testcase.__class__.__name__, t.testfn_name))
            wrapped = textwrap.fill(' '.join(t.tags()), WIDTH-10)
            print("  tags: %s" % _indent(wrapped, 8, True))
            if t.doc():
                print(_indent(t.doc(), width=2))
    else:
        for t in tests:
            line = t.shortname() + ' '
            if t.explicit_tags():
                line += '[%s]' % ' '.join(t.explicit_tags())
            print(line)


#---- text test runner that can handle TestSkipped reasonably

class ConsoleTestResult(unittest.TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by ConsoleTestRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream):
        unittest.TestResult.__init__(self)
        self.skips = []
        self.stream = stream

    def getDescription(self, test):
        if test._testlib_explicit_tags_:
            return "%s [%s]" % (test._testlib_shortname_,
                                ', '.join(test._testlib_explicit_tags_))
        else:
            return test._testlib_shortname_

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        self.stream.write(self.getDescription(test))
        self.stream.write(" ... ")

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        self.stream.write("ok\n")

    def addSkip(self, test, err):
        why = str(err[1])
        self.skips.append((test, why))
        self.stream.write("skipped (%s)\n" % why)

    def addError(self, test, err):
        if isinstance(err[1], TestSkipped):
            self.addSkip(test, err)
        else:
            unittest.TestResult.addError(self, test, err)
            self.stream.write("ERROR\n")

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self.stream.write("FAIL\n")

    def printSummary(self):
        self.stream.write('\n')
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.write(self.separator1 + '\n')
            self.stream.write("%s: %s\n"
                              % (flavour, self.getDescription(test)))
            self.stream.write(self.separator2 + '\n')
            self.stream.write("%s\n" % err)


class ConsoleTestRunner(object):
    """A test runner class that displays results on the console.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    
    Differences with unittest.TextTestRunner:
    - adds support for *skipped* tests (those that raise TestSkipped)
    - no verbosity option (only have equiv of verbosity=2)
    - test "short desc" is it 3-level tag name (e.g. 'foo/bar/baz' where
      that identifies: 'test_foo.py::BarTestCase.test_baz'.
    """
    def __init__(self, stream=sys.stderr):
        self.stream = stream

    def run(self, test_or_suite, test_result_class=ConsoleTestResult):
        """Run the given test case or test suite."""
        result = test_result_class(self.stream)
        start_time = time.time()
        test_or_suite.run(result)
        time_taken = time.time() - start_time

        result.printSummary()
        self.stream.write(result.separator2 + '\n')
        self.stream.write("Ran %d test%s in %.3fs\n\n"
            % (result.testsRun, result.testsRun != 1 and "s" or "",
               time_taken))
        details = []
        num_skips = len(result.skips)
        if num_skips:
            details.append("%d skip%s"
                % (num_skips, (num_skips != 1 and "s" or "")))
        if not result.wasSuccessful():
            num_failures = len(result.failures)
            if num_failures:
                details.append("%d failure%s"
                    % (num_failures, (num_failures != 1 and "s" or "")))
            num_errors = len(result.errors)
            if num_errors:
                details.append("%d error%s"
                    % (num_errors, (num_errors != 1 and "s" or "")))
            self.stream.write("FAILED (%s)\n" % ', '.join(details))
        elif details:
            self.stream.write("OK (%s)\n" % ', '.join(details))
        else:
            self.stream.write("OK\n")
        return result



#---- internal support stuff

# Recipe: indent (0.2.1)
def _indent(s, width=4, skip_first_line=False):
    """_indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)





#---- mainline

#TODO: pass in add_help_option=False and add it ourself here.
## Optparse's handling of the doc passed in for -h|--help handling is
## abysmal. Hence we'll stick with getopt.
#def _parse_opts(args):
#    """_parse_opts(args) -> (options, tags)"""
#    usage = "usage: %prog [OPTIONS...] [TAGS...]"
#    parser = optparse.OptionParser(prog="test", usage=usage,
#                                   description=__doc__)
#    parser.add_option("-v", "--verbose", dest="log_level",
#                      action="store_const", const=logging.DEBUG,
#                      help="more verbose output")
#    parser.add_option("-q", "--quiet", dest="log_level",
#                      action="store_const", const=logging.WARNING,
#                      help="quieter output")
#    parser.add_option("-l", "--list", dest="action",
#                      action="store_const", const="list",
#                      help="list available tests")
#    parser.set_defaults(log_level=logging.INFO, action="test")
#    opts, raw_tags = parser.parse_args()
#
#    # Trim '.py' from user-supplied tags. They might have gotten there
#    # via shell expansion.
#    ...
#
#    return opts, raw_tags

def _parse_opts(args, default_tags):
    """_parse_opts(args) -> (log_level, action, tags)"""
    opts, raw_tags = getopt.getopt(args, "hvqdlL:n",
        ["help", "verbose", "quiet", "debug", "list", "no-default-tags"])
    log_level = logging.WARN
    action = "test"
    no_default_tags = False
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            action = "help"
        elif opt in ("-v", "--verbose"):
            log_level = logging.INFO
        elif opt in ("-q", "--quiet"):
            log_level = logging.ERROR
        elif opt in ("-d", "--debug"):
            log_level = logging.DEBUG
        elif opt in ("-l", "--list"):
            action = "list"
        elif opt in ("-n", "--no-default-tags"):
            no_default_tags = True
        elif opt == "-L":
            # Optarg is of the form '<logname>:<levelname>', e.g.
            # "codeintel:DEBUG", "codeintel.db:INFO".
            lname, llevelname = optarg.split(':', 1)
            llevel = getattr(logging, llevelname)
            logging.getLogger(lname).setLevel(llevel)

    # Clean up the given tags.
    if no_default_tags:
        tags = []
    else:
        tags = default_tags
    for raw_tag in raw_tags:
        if splitext(raw_tag)[1] in (".py", ".pyc", ".pyo", ".pyw") \
           and exists(raw_tag):
            # Trim '.py' from user-supplied tags if it looks to be from
            # shell expansion.
            tags.append(splitext(raw_tag)[0])
        elif '/' in raw_tag:
            # Split one '/' to allow the shortname from the test listing
            # to be used as a filter.
            tags += raw_tag.split('/')
        else:
            tags.append(raw_tag)

    return log_level, action, tags


def harness(testdir_from_ns={None: os.curdir}, argv=sys.argv,
            setup_func=None, default_tags=None):
    """Convenience mainline for a test harness "test.py" script.

        "testdir_from_ns" (optional) is basically a set of directories in
            which to look for test cases. It is a dict with:
                <namespace>: <testdir>
            where <namespace> is a (short) string that becomes part of the
            included test names and an implicit tag for filtering those
            tests. By default the current dir is use with an empty namespace:
                {None: os.curdir}
        "setup_func" (optional) is a callable that will be called once
            before any tests are run to prepare for the test suite. It
            is not called if no tests will be run.
        "default_tags" (optional)
    
    Typically, if you have a number of test_*.py modules you can create
    a test harness, "test.py", for them that looks like this:

        #!/usr/bin/env python
        if __name__ == "__main__":
            retval = testlib.harness()
            sys.exit(retval)
    """
    if not logging.root.handlers:
        logging.basicConfig()
    try:
        log_level, action, tags = _parse_opts(argv[1:], default_tags or [])
    except getopt.error:
        _, ex, _ = sys.exc_info()
        log.error(str(ex) + " (did you need a '--' before a '-TAG' argument?)")
        return 1
    log.setLevel(log_level)

    if action == "help":
        print(__doc__)
        return 0
    if action == "list":
        return list_tests(testdir_from_ns, tags)
    elif action == "test":
        result = test(testdir_from_ns, tags, setup_func=setup_func)
        if result is None:
            return None
        return len(result.errors) + len(result.failures)
    else:
        raise TestError("unexpected action/mode: '%s'" % action)



########NEW FILE########
__FILENAME__ = test_markdown2
#!/usr/bin/env python
# Copyright (c) 2007-2008 ActiveState Software Inc.
# License: MIT (http://www.opensource.org/licenses/mit-license.php)

"""Test the Python markdown2.py."""

import os
import sys
from os.path import join, dirname, abspath, exists, splitext, basename
import re
from glob import glob
from pprint import pprint
import unittest
import codecs
import difflib
import doctest
try:
    from json import loads as json_loads
except ImportError:
    def json_loads(s):
        # Total hack to get support for 2.4. "simplejson" only supports back
        # to 2.5 now and `json` is only in the Python stdlib >=2.6.
        return eval(s, {}, {})

from testlib import TestError, TestSkipped, tag

sys.path.insert(0, join(dirname(dirname(abspath(__file__)))))
try:
    import markdown2
finally:
    del sys.path[0]



#---- Python version compat

# Use `bytes` for byte strings and `unicode` for unicode strings (str in Py3).
if sys.version_info[0] <= 2:
    py3 = False
    try:
        bytes
    except NameError:
        bytes = str
    base_string_type = basestring
elif sys.version_info[0] >= 3:
    py3 = True
    unicode = str
    base_string_type = str
    unichr = chr



#---- Test cases

class _MarkdownTestCase(unittest.TestCase):
    """Helper class for Markdown tests."""

    maxDiff = None

    def _assertMarkdownParity(self, text):
        """Assert that markdown2.py produces same output as Markdown.pl."""
        #TODO add normalization
        python_html = markdown2.markdown(text)
        perl_html = _markdown_with_perl(text)

        close_though = ""
        if python_html != perl_html \
           and (python_html.replace('\n', '')
                == perl_html.replace('\n', '')):
            close_though = " (close though -- all but EOLs match)"

        self.assertEqual(python_html, perl_html, _dedent("""\
            markdown2.py didn't produce the same output as Markdown.pl%s:
              ---- text ----
            %s  ---- Python markdown2.py HTML ----
            %s  ---- Perl Markdown.pl HTML ----
            %s""") % (close_though, _display(text),
                      _display(python_html), _display(perl_html)))

    def _assertMarkdownPath(self, text_path, encoding="utf-8", opts=None,
            toc_html_path=None, metadata_path=None):
        text = codecs.open(text_path, 'r', encoding=encoding).read()
        html_path = splitext(text_path)[0] + ".html"
        html = codecs.open(html_path, 'r', encoding=encoding).read()
        extra = {}
        if toc_html_path:
            extra["toc_html"] = codecs.open(toc_html_path, 'r', encoding=encoding).read()
            extra["toc_html_path"] = toc_html_path
        if metadata_path:
            extra["metadata"] = json_loads(
                codecs.open(metadata_path, 'r', encoding=encoding).read())
            extra["metadata_path"] = metadata_path
        self._assertMarkdown(text, html, text_path, html_path, opts=opts,
            **extra)

    def _assertMarkdown(self, text, html, text_path=None, html_path=None,
            opts=None, toc_html=None, toc_html_path=None, metadata=None,
            metadata_path=None):
        """Assert that markdown2.py produces the expected HTML."""
        if text_path is None: text_path = "<text content>"
        if html_path is None: html_path = "<html content>"
        if opts is None:
            opts = {}

        norm_html = norm_html_from_html(html)
        python_html = markdown2.markdown(text, **opts)
        python_norm_html = norm_html_from_html(python_html)

        close_though = ""
        if python_norm_html != norm_html \
           and (python_norm_html.replace('\n', '')
                == norm_html.replace('\n', '')):
            close_though = " (close though -- all but EOLs match)"

        diff = ''
        if python_norm_html != norm_html:
            diff = difflib.unified_diff(
                    norm_html.splitlines(1),
                    python_norm_html.splitlines(1),
                    html_path,
                    "markdown2 "+text_path)
            diff = ''.join(diff)
        errmsg = _dedent("""\
            markdown2.py didn't produce the expected HTML%s:
              ---- text (escaping: .=space, \\n=newline) ----
            %s  ---- Python markdown2.py HTML (escaping: .=space, \\n=newline) ----
            %s  ---- expected HTML (escaping: .=space, \\n=newline) ----
            %s  ---- diff ----
            %s""") % (close_though, _display(text),
                      _display(python_html), _display(html),
                      _indent(diff))

        def charreprreplace(exc):
            if not isinstance(exc, UnicodeEncodeError):
                raise TypeError("don't know how to handle %r" % exc)
            if py3:
                obj_repr = repr(exc.object[exc.start:exc.end])[1:-1]
            else:
                # repr -> remote "u'" and "'"
                obj_repr = repr(exc.object[exc.start:exc.end])[2:-1]
            return (unicode(obj_repr), exc.end)
        codecs.register_error("charreprreplace", charreprreplace)

        self.assertEqual(python_norm_html, norm_html, errmsg)

        if toc_html:
            python_toc_html = python_html.toc_html
            python_norm_toc_html = norm_html_from_html(python_toc_html)
            norm_toc_html = norm_html_from_html(toc_html)

            diff = ''
            if python_norm_toc_html != norm_toc_html:
                diff = difflib.unified_diff(
                        norm_toc_html.splitlines(1),
                        python_norm_toc_html.splitlines(1),
                        toc_html_path,
                        "`markdown2 %s`.toc_html" % text_path)
                diff = ''.join(diff)
            errmsg = _dedent("""\
                markdown2.py didn't produce the expected TOC HTML%s:
                  ---- text (escaping: .=space, \\n=newline) ----
                %s  ---- Python markdown2.py TOC HTML (escaping: .=space, \\n=newline) ----
                %s  ---- expected TOC HTML (escaping: .=space, \\n=newline) ----
                %s  ---- diff ----
                %s""") % (close_though, _display(text),
                          _display(python_toc_html), _display(toc_html),
                          _indent(diff))
            self.assertEqual(python_norm_toc_html, norm_toc_html,
                errmsg.encode('ascii', 'charreprreplace'))

        if metadata:
            self.assertEqual(python_html.metadata, metadata)

    def generate_tests(cls):
        """Add test methods to this class for each test file in
        `cls.cases_dir'.
        """
        cases_pat = join(dirname(__file__), cls.cases_dir, "*.text")
        for text_path in glob(cases_pat):
            # Load an options (`*.opts` file, if any).
            # It must be a Python dictionary. It will be passed as
            # kwargs to the markdown function.
            opts = {}
            opts_path = splitext(text_path)[0] + ".opts"
            if exists(opts_path):
                try:
                    opts = eval(open(opts_path, 'r').read())
                except Exception:
                    _, ex, _ = sys.exc_info()
                    print("WARNING: couldn't load `%s' opts file: %s" \
                          % (opts_path, ex))

            toc_html_path = splitext(text_path)[0] + ".toc_html"
            if not exists(toc_html_path):
                toc_html_path = None
            metadata_path = splitext(text_path)[0] + ".metadata"
            if not exists(metadata_path):
                metadata_path = None

            test_func = lambda self, t=text_path, o=opts, c=toc_html_path, m=metadata_path: \
                self._assertMarkdownPath(t, opts=o, toc_html_path=c,
                                         metadata_path=m)

            tags_path = splitext(text_path)[0] + ".tags"
            if exists(tags_path):
                tags = []
                for line in open(tags_path):
                    if '#' in line: # allow comments in .tags files
                        line = line[:line.index('#')]
                    tags += line.split()
                test_func.tags = tags

            name = splitext(basename(text_path))[0]
            name = name.replace(' - ', '_')
            name = name.replace(' ', '_')
            name = re.sub("[(),]", "", name)
            test_name = "test_%s" % name
            setattr(cls, test_name, test_func)
    generate_tests = classmethod(generate_tests)

class TMTestCase(_MarkdownTestCase):
    cases_dir = "tm-cases"

class MarkdownTestTestCase(_MarkdownTestCase):
    """Test cases from MarkdownTest-1.0."""
    cases_dir = "markdowntest-cases"

class PHPMarkdownTestCase(_MarkdownTestCase):
    """Test cases from MDTest."""
    cases_dir = "php-markdown-cases"

class PHPMarkdownExtraTestCase(_MarkdownTestCase):
    """Test cases from MDTest.

    These are all knownfailures because these test non-standard Markdown
    syntax no implemented in markdown2.py.  See
    <http://www.michelf.com/projects/php-markdown/extra/> for details.
    """
    __tags__ = ["knownfailure"]
    cases_dir = "php-markdown-extra-cases"


class DirectTestCase(_MarkdownTestCase):
    """These are specific test that I found were broken in
    Python-markdown (markdown.py).
    """

    def test_slow_hr(self):
        import time
        text = """\
* * *

This on *almost* looks like an hr, except for the trailing '+'. In older
versions of markdown2.py this was pathologically slow:

- - - - - - - - - - - - - - - - - - - - - - - - - +
"""
        html = """\
<hr />

<p>This on <em>almost</em> looks like an hr, except for the trailing '+'. In older
versions of markdown2.py this was pathologically slow:</p>

<p>- - - - - - - - - - - - - - - - - - - - - - - - - +</p>
"""
        start = time.time()
        self._assertMarkdown(text, html)
        end = time.time()
        delta = end - start
        self.assertTrue(delta < 1.0, "It took more than 1s to process "
            "'slow-hr'. It took %.2fs. Too slow!" % delta)
    test_slow_hr.tags = ["perf"]

    def test_code_in_strong(self):
        self._assertMarkdown(
            '**look at `this code` call**',
            '<p><strong>look at <code>this code</code> call</strong></p>\n')
    test_code_in_strong.tags = ["code", "strong"]

    def test_starter_pre(self):
        self._assertMarkdown(
            _indent('#!/usr/bin/python\nprint "hi"'),
            '<pre><code>#!/usr/bin/python\nprint "hi"\n</code></pre>\n')
    test_starter_pre.tags = ["pre", "recipes"]

    def test_pre(self):
        self._assertMarkdown(_dedent('''\
            some starter text

                #!/usr/bin/python
                print "hi"'''),
            '<p>some starter text</p>\n\n<pre><code>#!/usr/bin/python\nprint "hi"\n</code></pre>\n')

    def test_russian(self):
        ko = '\u043b\u0449' # 'ko' on russian keyboard
        self._assertMarkdown("## %s" % ko,
            '<h2>%s</h2>\n' % ko)
    test_russian.tags = ["unicode", "issue3"]


class DocTestsTestCase(unittest.TestCase):
    def test_api(self):
        if sys.version_info[:2] < (2,4):
            raise TestSkipped("no DocFileTest in Python <=2.3")
        test = doctest.DocFileTest("api.doctests")
        test.runTest()

    # Don't bother on Python 3 because (a) there aren't many inline doctests,
    # and (b) they are more to be didactic than comprehensive test suites.
    if not py3:
        def test_internal(self):
            doctest.testmod(markdown2)



#---- internal support stuff

_xml_escape_re = re.compile(r'&#(x[0-9A-Fa-f]{2,3}|[0-9]{2,3});')
def _xml_escape_sub(match):
    escape = match.group(1)
    if escape[0] == 'x':
        return unichr(int('0'+escape, base=16))
    else:
        return unichr(int(escape))

_markdown_email_link_re = re.compile(r'<a href="(.*?&#.*?)">(.*?)</a>', re.U)
def _markdown_email_link_sub(match):
    href, text = match.groups()
    href = _xml_escape_re.sub(_xml_escape_sub, href)
    text = _xml_escape_re.sub(_xml_escape_sub, text)
    return '<a href="%s">%s</a>' % (href, text)

def norm_html_from_html(html):
    """Normalize (somewhat) Markdown'd HTML.

    Part of Markdown'ing involves obfuscating email links with
    randomize encoding. Undo that obfuscation.

    Also normalize EOLs.
    """
    if not isinstance(html, unicode):
        html = html.decode('utf-8')
    html = _markdown_email_link_re.sub(
        _markdown_email_link_sub, html)
    if sys.platform == "win32":
        html = html.replace('\r\n', '\n')
    return html


def _display(s):
    """Markup the given string for useful display."""
    if not isinstance(s, unicode):
        s = s.decode("utf-8")
    s = _indent(_escaped_text_from_text(s, "whitespace"), 4)
    if not s.endswith('\n'):
        s += '\n'
    return s

def _markdown_with_perl(text):
    markdown_pl = join(dirname(__file__), "Markdown.pl")
    if not exists(markdown_pl):
        raise OSError("`%s' does not exist: get it from "
                      "http://daringfireball.net/projects/markdown/"
                      % markdown_pl)

    i, o = os.popen2("perl %s" % markdown_pl)
    i.write(text)
    i.close()
    html = o.read()
    o.close()
    return html


# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines

        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG:
        print("dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line))
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print("dedent: indent=%d: %r" % (indent, line))
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print("dedent: margin=%r" % margin)

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print("dedent: %r: EOL -> strip up to EOL" % line)
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print("dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin))
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.

    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)

# Recipe: indent (0.2.1)
def _indent(s, width=4, skip_first_line=False):
    """_indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)


# Recipe: text_escape (0.1)
def _escaped_text_from_text(text, escapes="eol"):
    r"""Return escaped version of text.

        "escapes" is either a mapping of chars in the source text to
            replacement text for each such char or one of a set of
            strings identifying a particular escape style:
                eol
                    replace EOL chars with '\r' and '\n', maintain the actual
                    EOLs though too
                whitespace
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
                eol-one-line
                    replace EOL chars with '\r' and '\n'
                whitespace-one-line
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
    """
    #TODO:
    # - Add 'c-string' style.
    # - Add _escaped_html_from_text() with a similar call sig.
    import re

    if isinstance(escapes, base_string_type):
        if escapes == "eol":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r"}
        elif escapes == "whitespace":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r",
                       '\t': "\\t", ' ': "."}
        elif escapes == "eol-one-line":
            escapes = {'\n': "\\n", '\r': "\\r"}
        elif escapes == "whitespace-one-line":
            escapes = {'\n': "\\n", '\r': "\\r", '\t': "\\t", ' ': '.'}
        else:
            raise ValueError("unknown text escape style: %r" % escapes)

    # Sort longer replacements first to allow, e.g. '\r\n' to beat '\r' and
    # '\n'.
    escapes_keys = list(escapes.keys())
    try:
        escapes_keys.sort(key=lambda a: len(a), reverse=True)
    except TypeError:
        # Python 2.3 support: sort() takes no keyword arguments
        escapes_keys.sort(lambda a,b: cmp(len(a), len(b)))
        escapes_keys.reverse()
    def repl(match):
        val = escapes[match.group(0)]
        return val
    escaped = re.sub("(%s)" % '|'.join([re.escape(k) for k in escapes_keys]),
                     repl,
                     text)

    return escaped

def _one_line_summary_from_text(text, length=78,
        escapes={'\n':"\\n", '\r':"\\r", '\t':"\\t"}):
    r"""Summarize the given text with one line of the given length.

        "text" is the text to summarize
        "length" (default 78) is the max length for the summary
        "escapes" is a mapping of chars in the source text to
            replacement text for each such char. By default '\r', '\n'
            and '\t' are escaped with their '\'-escaped repr.
    """
    if len(text) > length:
        head = text[:length-3]
    else:
        head = text
    escaped = _escaped_text_from_text(head, escapes)
    if len(text) > length:
        summary = escaped[:length-3] + "..."
    else:
        summary = escaped
    return summary


#---- hook for testlib

def test_cases():
    """This is called by test.py to build up the test cases."""
    TMTestCase.generate_tests()
    yield TMTestCase
    MarkdownTestTestCase.generate_tests()
    yield MarkdownTestTestCase
    PHPMarkdownTestCase.generate_tests()
    yield PHPMarkdownTestCase
    PHPMarkdownExtraTestCase.generate_tests()
    yield PHPMarkdownExtraTestCase
    yield DirectTestCase
    yield DocTestsTestCase

########NEW FILE########
__FILENAME__ = cutarelease
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009-2012 Trent Mick

"""cutarelease -- Cut a release of your project.

A script that will help cut a release for a git-based project that follows
a few conventions. It'll update your changelog (CHANGES.md), add a git
tag, push those changes, update your version to the next patch level release
and create a new changelog section for that new version.

Conventions:
- XXX
"""

__version_info__ = (1, 0, 7)
__version__ = '.'.join(map(str, __version_info__))

import sys
import os
from os.path import join, dirname, normpath, abspath, exists, basename, splitext
from glob import glob
from pprint import pprint
import re
import codecs
import logging
import optparse
import json



#---- globals and config

log = logging.getLogger("cutarelease")

class Error(Exception):
    pass



#---- main functionality

def cutarelease(project_name, version_files, dry_run=False):
    """Cut a release.

    @param project_name {str}
    @param version_files {list} List of paths to files holding the version
        info for this project.

        If none are given it attempts to guess the version file:
        package.json or VERSION.txt or VERSION or $project_name.py
        or lib/$project_name.py or $project_name.js or lib/$project_name.js.

        The version file can be in one of the following forms:

        - A .py file, in which case the file is expect to have a top-level
          global called "__version_info__" as follows. [1]

            __version_info__ = (0, 7, 6)

          Note that I typically follow that with the following to get a
          string version attribute on my modules:

            __version__ = '.'.join(map(str, __version_info__))

        - A .js file, in which case the file is expected to have a top-level
          global called "VERSION" as follows:

            ver VERSION = "1.2.3";

        - A "package.json" file, typical of a node.js npm-using project.
          The package.json file must have a "version" field.

        - TODO: A simple version file whose only content is a "1.2.3"-style version
          string.

    [1]: This is a convention I tend to follow in my projects.
        Granted it might not be your cup of tea. I should add support for
        just `__version__ = "1.2.3"`. I'm open to other suggestions too.
    """
    dry_run_str = dry_run and " (dry-run)" or ""

    if not version_files:
        log.info("guessing version file")
        candidates = [
            "package.json",
            "VERSION.txt",
            "VERSION",
            "%s.py" % project_name,
            "lib/%s.py" % project_name,
            "%s.js" % project_name,
            "lib/%s.js" % project_name,
        ]
        for candidate in candidates:
            if exists(candidate):
                version_files = [candidate]
                break
        else:
            raise Error("could not find a version file: specify its path or "
                "add one of the following to your project: '%s'"
                % "', '".join(candidates))
        log.info("using '%s' as version file", version_files[0])

    parsed_version_files = [_parse_version_file(f) for f in version_files]
    version_file_type, version_info = parsed_version_files[0]
    version = _version_from_version_info(version_info)

    # Confirm
    if not dry_run:
        answer = query_yes_no("* * *\n"
            "Are you sure you want cut a %s release?\n"
            "This will involved commits and a push." % version,
            default="no")
        print "* * *"
        if answer != "yes":
            log.info("user abort")
            return
    log.info("cutting a %s release%s", version, dry_run_str)

    # Checks: Ensure there is a section in changes for this version.



    changes_path = "CHANGES.md"
    changes_txt, changes, nyr = parse_changelog(changes_path)
    #pprint(changes)
    top_ver = changes[0]["version"]
    if top_ver != version:
        raise Error("changelog '%s' top section says "
            "version %r, expected version %r: aborting"
            % (changes_path, top_ver, version))
    top_verline = changes[0]["verline"]
    if not top_verline.endswith(nyr):
        answer = query_yes_no("\n* * *\n"
            "The changelog '%s' top section doesn't have the expected\n"
            "'%s' marker. Has this been released already?"
            % (changes_path, nyr), default="yes")
        print "* * *"
        if answer != "no":
            log.info("abort")
            return
    top_body = changes[0]["body"]
    if top_body.strip() == "(nothing yet)":
        raise Error("top section body is `(nothing yet)': it looks like "
            "nothing has been added to this release")

    # Commits to prepare release.
    changes_txt_before = changes_txt
    changes_txt = changes_txt.replace(" (not yet released)", "", 1)
    if not dry_run and changes_txt != changes_txt_before:
        log.info("prepare `%s' for release", changes_path)
        f = codecs.open(changes_path, 'w', 'utf-8')
        f.write(changes_txt)
        f.close()
        run('git commit %s -m "prepare for %s release"'
            % (changes_path, version))

    # Tag version and push.
    curr_tags = set(t for t in _capture_stdout(["git", "tag", "-l"]).split('\n') if t)
    if not dry_run and version not in curr_tags:
        log.info("tag the release")
        run('git tag -a "%s" -m "version %s"' % (version, version))
        run('git push --tags')

    # Optionally release.
    if exists("package.json"):
        answer = query_yes_no("\n* * *\nPublish to npm?", default="yes")
        print "* * *"
        if answer == "yes":
            if dry_run:
                log.info("skipping npm publish (dry-run)")
            else:
                run('npm publish')
    elif exists("setup.py"):
        answer = query_yes_no("\n* * *\nPublish to pypi?", default="yes")
        print "* * *"
        if answer == "yes":
            if dry_run:
                log.info("skipping pypi publish (dry-run)")
            else:
                run("%spython setup.py sdist --formats zip upload"
                    % _setup_command_prefix())

    # Commits to prepare for future dev and push.
    # - update changelog file
    next_version_info = _get_next_version_info(version_info)
    next_version = _version_from_version_info(next_version_info)
    log.info("prepare for future dev (version %s)", next_version)
    marker = "## " + changes[0]["verline"]
    if marker.endswith(nyr):
        marker = marker[0:-len(nyr)]
    if marker not in changes_txt:
        raise Error("couldn't find `%s' marker in `%s' "
            "content: can't prep for subsequent dev" % (marker, changes_path))
    next_verline = "%s %s%s" % (marker.rsplit(None, 1)[0], next_version, nyr)
    changes_txt = changes_txt.replace(marker + '\n',
        "%s\n\n(nothing yet)\n\n\n%s\n" % (next_verline, marker))
    if not dry_run:
        f = codecs.open(changes_path, 'w', 'utf-8')
        f.write(changes_txt)
        f.close()

    # - update version file
    next_version_tuple = _tuple_from_version(next_version)
    for i, ver_file in enumerate(version_files):
        ver_content = codecs.open(ver_file, 'r', 'utf-8').read()
        ver_file_type, ver_info = parsed_version_files[i]
        if ver_file_type == "json":
            marker = '"version": "%s"' % version
            if marker not in ver_content:
                raise Error("couldn't find `%s' version marker in `%s' "
                    "content: can't prep for subsequent dev" % (marker, ver_file))
            ver_content = ver_content.replace(marker,
                '"version": "%s"' % next_version)
        elif ver_file_type == "javascript":
            marker = 'var VERSION = "%s";' % version
            if marker not in ver_content:
                raise Error("couldn't find `%s' version marker in `%s' "
                    "content: can't prep for subsequent dev" % (marker, ver_file))
            ver_content = ver_content.replace(marker,
                'var VERSION = "%s";' % next_version)
        elif ver_file_type == "python":
            marker = "__version_info__ = %r" % (version_info,)
            if marker not in ver_content:
                raise Error("couldn't find `%s' version marker in `%s' "
                    "content: can't prep for subsequent dev" % (marker, ver_file))
            ver_content = ver_content.replace(marker,
                "__version_info__ = %r" % (next_version_tuple,))
        elif ver_file_type == "version":
            ver_content = next_version
        else:
            raise Error("unknown ver_file_type: %r" % ver_file_type)
        if not dry_run:
            log.info("update version to '%s' in '%s'", next_version, ver_file)
            f = codecs.open(ver_file, 'w', 'utf-8')
            f.write(ver_content)
            f.close()

    if not dry_run:
        run('git commit %s %s -m "prep for future dev"' % (
            changes_path, ' '.join(version_files)))
        run('git push')



#---- internal support routines

def _indent(s, indent='    '):
    return indent + indent.join(s.splitlines(True))

def _tuple_from_version(version):
    def _intify(s):
        try:
            return int(s)
        except ValueError:
            return s
    return tuple(_intify(b) for b in version.split('.'))

def _get_next_version_info(version_info):
    next = list(version_info[:])
    next[-1] += 1
    return tuple(next)

def _version_from_version_info(version_info):
    v = str(version_info[0])
    state_dot_join = True
    for i in version_info[1:]:
        if state_dot_join:
            try:
                int(i)
            except ValueError:
                state_dot_join = False
            else:
                pass
        if state_dot_join:
            v += "." + str(i)
        else:
            v += str(i)
    return v

_version_re = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+)([abc](\d+)?)?)?$")
def _version_info_from_version(version):
    m = _version_re.match(version)
    if not m:
        raise Error("could not convert '%s' version to version info" % version)
    version_info = []
    for g in m.groups():
        if g is None:
            break
        try:
            version_info.append(int(g))
        except ValueError:
            version_info.append(g)
    return tuple(version_info)

def _parse_version_file(version_file):
    """Get version info from the given file. It can be any of:

    Supported version file types (i.e. types of files from which we know
    how to parse the version string/number -- often by some convention):
    - json: use the "version" key
    - javascript: look for a `var VERSION = "1.2.3";`
    - python: Python script/module with `__version_info__ = (1, 2, 3)`
    - version: a VERSION.txt or VERSION file where the whole contents are
      the version string

    @param version_file {str} Can be a path or "type:path", where "type"
        is one of the supported types.
    """
    # Get version file *type*.
    version_file_type = None
    match = re.compile("^([a-z]+):(.*)$").search(version_file)
    if match:
        version_file = match.group(2)
        version_file_type = match.group(1)
        aliases = {
            "js": "javascript"
        }
        if version_file_type in aliases:
            version_file_type = aliases[version_file_type]

    f = codecs.open(version_file, 'r', 'utf-8')
    content = f.read()
    f.close()

    if not version_file_type:
        # Guess the type.
        base = basename(version_file)
        ext = splitext(base)[1]
        if ext == ".json":
            version_file_type = "json"
        elif ext == ".py":
            version_file_type = "python"
        elif ext == ".js":
            version_file_type = "javascript"
        elif content.startswith("#!"):
            shebang = content.splitlines(False)[0]
            shebang_bits = re.split(r'[/ \t]', shebang)
            for name, typ in {"python": "python", "node": "javascript"}.items():
                if name in shebang_bits:
                    version_file_type = typ
                    break
        elif base in ("VERSION", "VERSION.txt"):
            version_file_type = "version"
    if not version_file_type:
        raise RuntimeError("can't extract version from '%s': no idea "
            "what type of file it it" % version_file)

    if version_file_type == "json":
        obj = json.loads(content)
        version_info = _version_info_from_version(obj["version"])
    elif version_file_type == "python":
        m = re.search(r'^__version_info__ = (.*?)$', content, re.M)
        version_info = eval(m.group(1))
    elif version_file_type == "javascript":
        m = re.search(r'^var VERSION = "(.*?)";$', content, re.M)
        version_info = _version_info_from_version(m.group(1))
    elif version_file_type == "version":
        version_info = _version_info_from_version(content.strip())
    else:
        raise RuntimeError("unexpected version_file_type: %r"
            % version_file_type)
    return version_file_type, version_info


def parse_changelog(changes_path):
    """Parse the given changelog path and return `(content, parsed, nyr)`
    where `nyr` is the ' (not yet released)' marker and `parsed` looks like:

        [{'body': u'\n(nothing yet)\n\n',
          'verline': u'restify 1.0.1 (not yet released)',
          'version': u'1.0.1'},    # version is parsed out for top section only
         {'body': u'...',
          'verline': u'1.0.0'},
         {'body': u'...',
          'verline': u'1.0.0-rc2'},
         {'body': u'...',
          'verline': u'1.0.0-rc1'}]

    A changelog (CHANGES.md) is expected to look like this:

        # $project Changelog

        ## $next_version (not yet released)

        ...

        ## $version1

        ...

        ## $version2

        ... and so on

    The version lines are enforced as follows:

    - The top entry should have a " (not yet released)" suffix. "Should"
      because recovery from half-cutarelease failures is supported.
    - A version string must be extractable from there, but it tries to
      be loose (though strict "X.Y.Z" versioning is preferred). Allowed

            ## 1.0.0
            ## my project 1.0.1
            ## foo 1.2.3-rc2

      Basically, (a) the " (not yet released)" is stripped, (b) the
      last token is the version, and (c) that version must start with
      a digit (sanity check).
    """
    if not exists(changes_path):
        raise Error("changelog file '%s' not found" % changes_path)
    content = codecs.open(changes_path, 'r', 'utf-8').read()

    parser = re.compile(
        r'^##\s*(?P<verline>[^\n]*?)\s*$(?P<body>.*?)(?=^##|\Z)',
        re.M | re.S)
    sections = parser.findall(content)

    # Sanity checks on changelog format.
    if not sections:
        template = "## 1.0.0 (not yet released)\n\n(nothing yet)\n"
        raise Error("changelog '%s' must have at least one section, "
            "suggestion:\n\n%s" % (changes_path, _indent(template)))
    first_section_verline = sections[0][0]
    nyr = ' (not yet released)'
    #if not first_section_verline.endswith(nyr):
    #    eg = "## %s%s" % (first_section_verline, nyr)
    #    raise Error("changelog '%s' top section must end with %r, "
    #        "naive e.g.: '%s'" % (changes_path, nyr, eg))

    items = []
    for i, section in enumerate(sections):
        item = {
            "verline": section[0],
            "body": section[1]
        }
        if i == 0:
            # We only bother to pull out 'version' for the top section.
            verline = section[0]
            if verline.endswith(nyr):
                verline = verline[0:-len(nyr)]
            version = verline.split()[-1]
            try:
                int(version[0])
            except ValueError:
                msg = ''
                if version.endswith(')'):
                    msg = " (cutarelease is picky about the trailing %r " \
                        "on the top version line. Perhaps you misspelled " \
                        "that?)" % nyr
                raise Error("changelog '%s' top section version '%s' is "
                    "invalid: first char isn't a number%s"
                    % (changes_path, version, msg))
            item["version"] = version
        items.append(item)

    return content, items, nyr

## {{{ http://code.activestate.com/recipes/577058/ (r2)
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")
## end of http://code.activestate.com/recipes/577058/ }}}

def _capture_stdout(argv):
    import subprocess
    p = subprocess.Popen(argv, stdout=subprocess.PIPE)
    return p.communicate()[0]

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def run(cmd):
    """Run the given command.

    Raises OSError is the command returns a non-zero exit status.
    """
    log.debug("running '%s'", cmd)
    fixed_cmd = cmd
    if sys.platform == "win32" and cmd.count('"') > 2:
        fixed_cmd = '"' + cmd + '"'
    retval = os.system(fixed_cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        raise OSError(status, "error running '%s'" % cmd)

def _setup_command_prefix():
    prefix = ""
    if sys.platform == "darwin":
        # http://forums.macosxhints.com/archive/index.php/t-43243.html
        # This is an Apple customization to `tar` to avoid creating
        # '._foo' files for extended-attributes for archived files.
        prefix = "COPY_EXTENDED_ATTRIBUTES_DISABLE=1 "
    return prefix


#---- mainline

def main(argv):
    logging.basicConfig(format="%(name)s: %(levelname)s: %(message)s")
    log.setLevel(logging.INFO)

    # Parse options.
    parser = optparse.OptionParser(prog="cutarelease", usage='',
        version="%prog " + __version__, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
        action="store_const", const=logging.DEBUG,
        help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
        action="store_const", const=logging.WARNING,
        help="quieter output (just warnings and errors)")
    parser.set_default("log_level", logging.INFO)
    parser.add_option("--test", action="store_true",
        help="run self-test and exit (use 'eol.py -v --test' for verbose test output)")
    parser.add_option("-p", "--project-name", metavar="NAME",
        help='the name of this project (default is the base dir name)',
        default=basename(os.getcwd()))
    parser.add_option("-f", "--version-file", metavar="[TYPE:]PATH",
        action='append', dest="version_files",
        help='The path to the project file holding the version info. Can be '
             'specified multiple times if more than one file should be updated '
             'with new version info. If excluded, it will be guessed.')
    parser.add_option("-n", "--dry-run", action="store_true",
        help='Do a dry-run', default=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    cutarelease(opts.project_name, opts.version_files, dry_run=opts.dry_run)


## {{{ http://code.activestate.com/recipes/577258/ (r5+)
if __name__ == "__main__":
    try:
        retval = main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
    except:
        import traceback, logging
        if not log.handlers and not logging.root.handlers:
            logging.basicConfig()
        skip_it = False
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            if isinstance(exc, IOError) and exc.args[0] == 32:
                # Skip 'IOError: [Errno 32] Broken pipe': often a cancelling of `less`.
                skip_it = True
            if not skip_it:
                tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                log.error("%s (%s:%s in %s)", exc_info[1], tb_path,
                    tb_lineno, tb_func)
        else:  # string exception
            log.error(exc_info[0])
        if not skip_it:
            if log.isEnabledFor(logging.DEBUG):
                traceback.print_exception(*exc_info)
            sys.exit(1)
    else:
        sys.exit(retval)
## end of http://code.activestate.com/recipes/577258/ }}}

########NEW FILE########
__FILENAME__ = which
#!/usr/bin/env python
# Copyright (c) 2002-2007 ActiveState Software Inc.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/which/

r"""Find the full path to commands.

which(command, path=None, verbose=0, exts=None)
    Return the full path to the first match of the given command on the
    path.

whichall(command, path=None, verbose=0, exts=None)
    Return a list of full paths to all matches of the given command on
    the path.

whichgen(command, path=None, verbose=0, exts=None)
    Return a generator which will yield full paths to all matches of the
    given command on the path.
    
By default the PATH environment variable is searched (as well as, on
Windows, the AppPaths key in the registry), but a specific 'path' list
to search may be specified as well.  On Windows, the PATHEXT environment
variable is applied as appropriate.

If "verbose" is true then a tuple of the form
    (<fullpath>, <matched-where-description>)
is returned for each match. The latter element is a textual description
of where the match was found. For example:
    from PATH element 0
    from HKLM\SOFTWARE\...\perl.exe
"""

_cmdlnUsage = """
    Show the full path of commands.

    Usage:
        which [<options>...] [<command-name>...]

    Options:
        -h, --help      Print this help and exit.
        -V, --version   Print the version info and exit.

        -a, --all       Print *all* matching paths.
        -v, --verbose   Print out how matches were located and
                        show near misses on stderr.
        -q, --quiet     Just print out matches. I.e., do not print out
                        near misses.

        -p <altpath>, --path=<altpath>
                        An alternative path (list of directories) may
                        be specified for searching.
        -e <exts>, --exts=<exts>
                        Specify a list of extensions to consider instead
                        of the usual list (';'-separate list, Windows
                        only).

    Show the full path to the program that would be run for each given
    command name, if any. Which, like GNU's which, returns the number of
    failed arguments, or -1 when no <command-name> was given.

    Near misses include duplicates, non-regular files and (on Un*x)
    files without executable access.
"""

__revision__ = "$Id$"
__version_info__ = (1, 1, 3)
__version__ = '.'.join(map(str, __version_info__))
__all__ = ["which", "whichall", "whichgen", "WhichError"]

import os
import sys
import getopt
import stat


#---- exceptions

class WhichError(Exception):
    pass



#---- internal support stuff

def _getRegisteredExecutable(exeName):
    """Windows allow application paths to be registered in the registry."""
    registered = None
    if sys.platform.startswith('win'):
        if os.path.splitext(exeName)[1].lower() != '.exe':
            exeName += '.exe'
        import _winreg
        try:
            key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\" +\
                  exeName
            value = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE, key)
            registered = (value, "from HKLM\\"+key)
        except _winreg.error:
            pass
        if registered and not os.path.exists(registered[0]):
            registered = None
    return registered

def _samefile(fname1, fname2):
    if sys.platform.startswith('win'):
        return ( os.path.normpath(os.path.normcase(fname1)) ==\
            os.path.normpath(os.path.normcase(fname2)) )
    else:
        return os.path.samefile(fname1, fname2)

def _cull(potential, matches, verbose=0):
    """Cull inappropriate matches. Possible reasons:
        - a duplicate of a previous match
        - not a disk file
        - not executable (non-Windows)
    If 'potential' is approved it is returned and added to 'matches'.
    Otherwise, None is returned.
    """
    for match in matches:  # don't yield duplicates
        if _samefile(potential[0], match[0]):
            if verbose:
                sys.stderr.write("duplicate: %s (%s)\n" % potential)
            return None
    else:
        if not stat.S_ISREG(os.stat(potential[0]).st_mode):
            if verbose:
                sys.stderr.write("not a regular file: %s (%s)\n" % potential)
        elif sys.platform != "win32" \
             and not os.access(potential[0], os.X_OK):
            if verbose:
                sys.stderr.write("no executable access: %s (%s)\n"\
                                 % potential)
        else:
            matches.append(potential)
            return potential

        
#---- module API

def whichgen(command, path=None, verbose=0, exts=None):
    """Return a generator of full paths to the given command.
    
    "command" is a the name of the executable to search for.
    "path" is an optional alternate path list to search. The default it
        to use the PATH environment variable.
    "verbose", if true, will cause a 2-tuple to be returned for each
        match. The second element is a textual description of where the
        match was found.
    "exts" optionally allows one to specify a list of extensions to use
        instead of the standard list for this system. This can
        effectively be used as an optimization to, for example, avoid
        stat's of "foo.vbs" when searching for "foo" and you know it is
        not a VisualBasic script but ".vbs" is on PATHEXT. This option
        is only supported on Windows.

    This method returns a generator which yields either full paths to
    the given command or, if verbose, tuples of the form (<path to
    command>, <where path found>).
    """
    matches = []
    if path is None:
        usingGivenPath = 0
        path = os.environ.get("PATH", "").split(os.pathsep)
        if sys.platform.startswith("win"):
            path.insert(0, os.curdir)  # implied by Windows shell
    else:
        usingGivenPath = 1

    # Windows has the concept of a list of extensions (PATHEXT env var).
    if sys.platform.startswith("win"):
        if exts is None:
            exts = os.environ.get("PATHEXT", "").split(os.pathsep)
            # If '.exe' is not in exts then obviously this is Win9x and
            # or a bogus PATHEXT, then use a reasonable default.
            for ext in exts:
                if ext.lower() == ".exe":
                    break
            else:
                exts = ['.COM', '.EXE', '.BAT']
        elif not isinstance(exts, list):
            raise TypeError("'exts' argument must be a list or None")
    else:
        if exts is not None:
            raise WhichError("'exts' argument is not supported on "\
                             "platform '%s'" % sys.platform)
        exts = []

    # File name cannot have path separators because PATH lookup does not
    # work that way.
    if os.sep in command or os.altsep and os.altsep in command:
        if os.path.exists(command):
            match = _cull((command, "explicit path given"), matches, verbose)
            if verbose:
                yield match
            else:
                yield match[0]
    else:
        for i in range(len(path)):
            dirName = path[i]
            # On windows the dirName *could* be quoted, drop the quotes
            if sys.platform.startswith("win") and len(dirName) >= 2\
               and dirName[0] == '"' and dirName[-1] == '"':
                dirName = dirName[1:-1]
            for ext in ['']+exts:
                absName = os.path.abspath(
                    os.path.normpath(os.path.join(dirName, command+ext)))
                if os.path.isfile(absName):
                    if usingGivenPath:
                        fromWhere = "from given path element %d" % i
                    elif not sys.platform.startswith("win"):
                        fromWhere = "from PATH element %d" % i
                    elif i == 0:
                        fromWhere = "from current directory"
                    else:
                        fromWhere = "from PATH element %d" % (i-1)
                    match = _cull((absName, fromWhere), matches, verbose)
                    if match:
                        if verbose:
                            yield match
                        else:
                            yield match[0]
        match = _getRegisteredExecutable(command)
        if match is not None:
            match = _cull(match, matches, verbose)
            if match:
                if verbose:
                    yield match
                else:
                    yield match[0]


def which(command, path=None, verbose=0, exts=None):
    """Return the full path to the first match of the given command on
    the path.
    
    "command" is a the name of the executable to search for.
    "path" is an optional alternate path list to search. The default it
        to use the PATH environment variable.
    "verbose", if true, will cause a 2-tuple to be returned. The second
        element is a textual description of where the match was found.
    "exts" optionally allows one to specify a list of extensions to use
        instead of the standard list for this system. This can
        effectively be used as an optimization to, for example, avoid
        stat's of "foo.vbs" when searching for "foo" and you know it is
        not a VisualBasic script but ".vbs" is on PATHEXT. This option
        is only supported on Windows.

    If no match is found for the command, a WhichError is raised.
    """
    try:
        match = whichgen(command, path, verbose, exts).next()
    except StopIteration:
        raise WhichError("Could not find '%s' on the path." % command)
    return match


def whichall(command, path=None, verbose=0, exts=None):
    """Return a list of full paths to all matches of the given command
    on the path.  

    "command" is a the name of the executable to search for.
    "path" is an optional alternate path list to search. The default it
        to use the PATH environment variable.
    "verbose", if true, will cause a 2-tuple to be returned for each
        match. The second element is a textual description of where the
        match was found.
    "exts" optionally allows one to specify a list of extensions to use
        instead of the standard list for this system. This can
        effectively be used as an optimization to, for example, avoid
        stat's of "foo.vbs" when searching for "foo" and you know it is
        not a VisualBasic script but ".vbs" is on PATHEXT. This option
        is only supported on Windows.
    """
    return list( whichgen(command, path, verbose, exts) )



#---- mainline

def main(argv):
    all = 0
    verbose = 0
    altpath = None
    exts = None
    try:
        optlist, args = getopt.getopt(argv[1:], 'haVvqp:e:',
            ['help', 'all', 'version', 'verbose', 'quiet', 'path=', 'exts='])
    except getopt.GetoptError, msg:
        sys.stderr.write("which: error: %s. Your invocation was: %s\n"\
                         % (msg, argv))
        sys.stderr.write("Try 'which --help'.\n")
        return 1
    for opt, optarg in optlist:
        if opt in ('-h', '--help'):
            print _cmdlnUsage
            return 0
        elif opt in ('-V', '--version'):
            print "which %s" % __version__
            return 0
        elif opt in ('-a', '--all'):
            all = 1
        elif opt in ('-v', '--verbose'):
            verbose = 1
        elif opt in ('-q', '--quiet'):
            verbose = 0
        elif opt in ('-p', '--path'):
            if optarg:
                altpath = optarg.split(os.pathsep)
            else:
                altpath = []
        elif opt in ('-e', '--exts'):
            if optarg:
                exts = optarg.split(os.pathsep)
            else:
                exts = []

    if len(args) == 0:
        return -1

    failures = 0
    for arg in args:
        #print "debug: search for %r" % arg
        nmatches = 0
        for match in whichgen(arg, path=altpath, verbose=verbose, exts=exts):
            if verbose:
                print "%s (%s)" % match
            else:
                print match
            nmatches += 1
            if not all:
                break
        if not nmatches:
            failures += 1
    return failures


if __name__ == "__main__":
    sys.exit( main(sys.argv) )



########NEW FILE########
