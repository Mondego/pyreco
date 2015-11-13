__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser()
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=False,
                   help="Use Disribute rather than Setuptools.")

parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse(requirement)).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse(requirement)).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = builder
# -*- coding: utf-8 -*-
"""
    rstblog.builder
    ~~~~~~~~~~~~~~~

    The building components.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import re
import os
import posixpath
from fnmatch import fnmatch
from urlparse import urlparse

from docutils.core import publish_parts

from jinja2 import Environment, FileSystemLoader, Markup

from babel import Locale, dates

from werkzeug.routing import Map, Rule
from werkzeug import url_unquote

from rstblog.signals import before_file_processed, \
     before_template_rendered, before_build_finished, \
     before_file_built, after_file_prepared, \
     after_file_published
from rstblog.modules import find_module
from rstblog.programs import RSTProgram, CopyProgram


OUTPUT_FOLDER = '_build'
builtin_programs = {
    'rst':      RSTProgram,
    'copy':     CopyProgram
}
builtin_templates = os.path.join(os.path.dirname(__file__), 'templates')
url_parts_re = re.compile(r'\$(\w+|{[^}]+})')


class Context(object):
    """Per rendering information"""

    def __init__(self, builder, config, source_filename, prepare=False):
        self.builder = builder
        self.config = config
        self.title = 'Untitled'
        self.summary = None
        self.pub_date = None
        self.source_filename = source_filename
        self.links = []
        self.program_name = self.config.get('program')
        if self.program_name is None:
            self.program_name = self.builder.guess_program(
                config, source_filename)
        self.program = self.builder.programs[self.program_name](self)
        self.destination_filename = os.path.join(
            self.builder.prefix_path.lstrip('/'),
            self.program.get_desired_filename())
        if prepare:
            self.program.prepare()
            after_file_prepared.send(self)
            if self.public:
                after_file_published.send(self)

    @property
    def is_new(self):
        return not os.path.exists(self.full_destination_filename)

    @property
    def public(self):
        return self.config.get('public', True)

    @property
    def slug(self):
        directory, filename = os.path.split(self.source_filename)
        basename, ext = os.path.splitext(filename)
        if basename == 'index':
            return posixpath.join(directory, basename).rstrip('/').replace('\\', '/')
        return posixpath.join(directory, basename).replace('\\', '/')

    def make_destination_folder(self):
        folder = self.destination_folder
        if not os.path.isdir(folder):
            os.makedirs(folder)

    def open_source_file(self, mode='r'):
        return open(self.full_source_filename, mode)

    def open_destination_file(self, mode='w'):
        self.make_destination_folder()
        return open(self.full_destination_filename, mode)

    @property
    def destination_folder(self):
        return os.path.dirname(self.full_destination_filename)

    @property
    def full_destination_filename(self):
        return os.path.join(self.builder.project_folder,
                            self.config.get('output_folder') or OUTPUT_FOLDER,
                            self.destination_filename)

    @property
    def full_source_filename(self):
        return os.path.join(self.builder.project_folder, self.source_filename)

    @property
    def needs_build(self):
        if self.is_new:
            return True
        src = self.full_source_filename
        dst = self.full_destination_filename
        return os.path.getmtime(dst) < os.path.getmtime(src)

    def get_default_template_context(self):
        return {
            'source_filename':  self.source_filename,
            'program_name':     self.program_name,
            'links':            self.links,
            'ctx':              self,
            'config':           self.config
        }

    def render_template(self, template_name, context=None):
        real_context = self.get_default_template_context()
        if context:
            real_context.update(context)
        return self.builder.render_template(template_name, real_context)

    def render_rst(self, contents):
        settings = {
            'initial_header_level': self.config.get('rst_header_level', 2),
            'rstblog_context':      self
        }
        parts = publish_parts(source=contents,
                              writer_name='html4css1',
                              settings_overrides=settings)
        return {
            'title':        Markup(parts['title']).striptags(),
            'html_title':   Markup(parts['html_title']),
            'fragment':     Markup(parts['fragment'])
        }

    def render_contents(self):
        return self.program.render_contents()

    def render_summary(self):
        if not self.summary:
            return u''
        return self.render_rst(self.summary)['fragment']

    def add_stylesheet(self, href, type=None, media=None):
        if type is None:
            type = 'text/css'
        self.links.append({
            'href':     self.builder.get_static_url(href),
            'type':     type,
            'media':    media,
            'rel':      'stylesheet'
        })

    def run(self):
        before_file_processed.send(self)
        if self.needs_build:
            self.build()

    def build(self):
        before_file_built.send(self)
        self.program.run()


class BuildError(ValueError):
    pass


class Builder(object):
    default_ignores = ('.*', '_*', 'config.yml', 'Makefile', 'README', '*.conf', )
    default_programs = {
        '*.rst':    'rst'
    }
    default_template_path = '_templates'
    default_static_folder = 'static'

    def __init__(self, project_folder, config):
        self.project_folder = os.path.abspath(project_folder)
        self.config = config
        self.programs = builtin_programs.copy()
        self.modules = []
        self.storage = {}
        self.url_map = Map()
        parsed = urlparse(self.config.root_get('canonical_url'))
        self.prefix_path = parsed.path
        self.url_adapter = self.url_map.bind('dummy.invalid',
            script_name=self.prefix_path)
        self.register_url('page', '/<path:slug>')

        template_path = os.path.join(self.project_folder,
            self.config.root_get('template_path') or
                self.default_template_path)
        self.locale = Locale(self.config.root_get('locale') or 'en')
        self.jinja_env = Environment(
            loader=FileSystemLoader([template_path, builtin_templates]),
            autoescape=self.config.root_get('template_autoescape', True),
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_'],
        )
        self.jinja_env.globals.update(
            link_to=self.link_to,
            format_datetime=self.format_datetime,
            format_date=self.format_date,
            format_time=self.format_time
        )

        self.static_folder = self.config.root_get('static_folder') or \
                             self.default_static_folder

        for module in self.config.root_get('active_modules') or []:
            mod = find_module(module)
            mod.setup(self)
            self.modules.append(mod)

    @property
    def default_output_folder(self):
        return os.path.join(self.project_folder,
                            self.config.root_get('output_folder')
                            or OUTPUT_FOLDER)

    def link_to(self, _key, **values):
        return self.url_adapter.build(_key, values)

    def get_link_filename(self, _key, **values):
        link = url_unquote(self.link_to(_key, **values).lstrip('/')).encode('utf-8')
        if not link or link.endswith('/'):
            link += 'index.html'
        return os.path.join(self.default_output_folder, link)

    def open_link_file(self, _key, mode='w', **values):
        filename = self.get_link_filename(_key, **values)
        folder = os.path.dirname(filename)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return open(filename, mode)

    def register_url(self, key, rule=None, config_key=None,
                     config_default=None, **extra):
        if config_key is not None:
            rule = self.config.root_get(config_key, config_default)
        self.url_map.add(Rule(rule, endpoint=key, **extra))

    def get_full_static_filename(self, filename):
        return os.path.join(self.default_output_folder,
                            self.static_folder, filename)

    def get_static_url(self, filename):
        return '/' + posixpath.join(self.static_folder, filename)

    def open_static_file(self, filename, mode='w'):
        full_filename = self.get_full_static_filename(filename)
        folder = os.path.dirname(full_filename)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return open(full_filename, mode)

    def get_storage(self, module):
        return self.storage.setdefault(module, {})

    def filter_files(self, files, config):
        patterns = config.merged_get('ignore_files')
        if patterns is None:
            patterns = self.default_ignores

        result = []
        for filename in files:
            for pattern in patterns:
                if fnmatch(filename, pattern):
                    break
            else:
                result.append(filename)
        return result

    def guess_program(self, config, filename):
        mapping = config.list_entries('programs') or self.default_programs
        for pattern, program_name in mapping.iteritems():
            if fnmatch(filename, pattern):
                return program_name
        return 'copy'

    def render_template(self, template_name, context=None):
        if context is None:
            context = {}
        context['builder'] = self
        context.setdefault('config', self.config)
        tmpl = self.jinja_env.get_template(template_name)
        before_template_rendered.send(tmpl, context=context)
        return tmpl.render(context)

    def format_datetime(self, datetime=None, format='medium'):
        return dates.format_datetime(datetime, format, locale=self.locale)

    def format_time(self, time=None, format='medium'):
        return dates.format_time(time, format, locale=self.locale)

    def format_date(self, date=None, format='medium'):
        return dates.format_date(date, format, locale=self.locale)

    def iter_contexts(self, prepare=True):
        last_config = self.config
        cutoff = len(self.project_folder) + 1
        for dirpath, dirnames, filenames in os.walk(self.project_folder):
            local_config = last_config
            local_config_filename = os.path.join(dirpath, 'config.yml')
            if os.path.isfile(local_config_filename):
                with open(local_config_filename) as f:
                    local_config = last_config.add_from_file(f)

            dirnames[:] = self.filter_files(dirnames, local_config)
            filenames = self.filter_files(filenames, local_config)

            for filename in filenames:
                yield Context(self, local_config, os.path.join(
                    dirpath[cutoff:], filename), prepare)

    def anything_needs_build(self):
        for context in self.iter_contexts(prepare=False):
            if context.needs_build:
                return True
        return False

    def run(self):
        self.storage.clear()
        contexts = list(self.iter_contexts())

        for context in contexts:
            if context.needs_build:
                key = context.is_new and 'A' or 'U'
                context.run()
                print key, context.source_filename

        before_build_finished.send(self)

    def debug_serve(self, host='127.0.0.1', port=5000):
        from rstblog.server import Server
        print 'Serving on http://%s:%d/' % (host, port)
        try:
            Server(host, port, self).serve_forever()
        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = cli
# -*- coding: utf-8 -*-
"""
    rstblog.cli
    ~~~~~~~~~~~

    The command line interface

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
import sys
import os
from rstblog.config import Config
from rstblog.builder import Builder


def get_builder(project_folder):
    """Runs the builder for the given project folder."""
    config_filename = os.path.join(project_folder, 'config.yml')
    config = Config()
    if not os.path.isfile(config_filename):
        raise ValueError('root config file "%s" is required' % config_filename)
    with open(config_filename) as f:
        config = config.add_from_file(f)
    return Builder(project_folder, config)


def main():
    """Entrypoint for the console script."""
    if len(sys.argv) not in (1, 2, 3):
        print >> sys.stderr, 'usage: rstblog <action> <folder>'
    if len(sys.argv) >= 2:
        action = sys.argv[1]
    else:
        action = 'build'
    if len(sys.argv) >= 3:
        folder = sys.argv[2]
    else:
        folder = os.getcwd()
    if action not in ('build', 'serve'):
        print >> sys.stderr, 'unknown action', action
    builder = get_builder(folder)

    if action == 'build':
        builder.run()
    else:
        builder.debug_serve()

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""
    rstblog.config
    ~~~~~~~~~~~~~~

    Holds the configuration and can read it from another file.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import yaml


missing = object()


class Config(object):
    """A stacked config."""

    def __init__(self):
        self.stack = []

    def __getitem__(self, key):
        for layer in reversed(self.stack):
            rv = layer.get(key, missing)
            if rv is not missing:
                return rv
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def list_entries(self, key):
        rv = {}
        prefix = key + '.'
        for layer in self.stack:
            for key, value in layer.iteritems():
                if key.startswith(prefix):
                    rv[key] = value
        return rv

    def merged_get(self, key):
        result = None
        for layer in reversed(self.stack):
            rv = layer.get(key, missing)
            if rv is not missing:
                if result is None:
                    result = rv
                else:
                    if isinstance(result, list):
                        result.extend(rv)
                    elif isinstance(result, dict):
                        result.update(rv)
                    else:
                        raise ValueError('expected list or dict')
        return result

    def root_get(self, key, default=None):
        return self.stack[0].get(key, default)

    def add_from_dict(self, d):
        """Returns a new config from this config with another layer added
        from a given dictionary.
        """
        layer = {}
        rv = Config()
        rv.stack = self.stack + [layer]
        def _walk(d, prefix):
            for key, value in d.iteritems():
                if isinstance(value, dict):
                    _walk(value, prefix + key + '.')
                else:
                    layer[prefix + key] = value
        _walk(d, '')
        return rv

    def add_from_file(self, fd):
        """Returns a new config from this config with another layer added
        from a given config file.
        """
        d = yaml.load(fd)
        if not d:
            return
        if not isinstance(d, dict):
            raise ValueError('Configuration has to contain a dict')
        return self.add_from_dict(d)

    def pop(self):
        self.stack.pop()

########NEW FILE########
__FILENAME__ = blog
# -*- coding: utf-8 -*-
"""
    rstblog.modules.blog
    ~~~~~~~~~~~~~~~~~~~~

    The blog component.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

from datetime import datetime, date
from urlparse import urljoin

from jinja2 import contextfunction

from werkzeug.routing import Rule, Map, NotFound
from werkzeug.contrib.atom import AtomFeed

from rstblog.signals import after_file_published, \
     before_build_finished
from rstblog.utils import Pagination


class MonthArchive(object):

    def __init__(self, builder, year, month, entries):
        self.builder = builder
        self.year = year
        self.month = month
        self.entries = entries
        entries.sort(key=lambda x: x.pub_date, reverse=True)

    @property
    def month_name(self):
        return self.builder.format_date(date(int(self.year),
                                        int(self.month), 1),
                                        format='MMMM')

    @property
    def count(self):
        return len(self.entries)


class YearArchive(object):

    def __init__(self, builder, year, months):
        self.year = year
        self.months = [MonthArchive(builder, year, month, entries)
                       for month, entries in months.iteritems()]
        self.months.sort(key=lambda x: -int(x.month))
        self.count = sum(len(x.entries) for x in self.months)


def test_pattern(path, pattern):
    pattern = '/' + pattern.strip('/') + '/<path:extra>'
    adapter = Map([Rule(pattern)]).bind('dummy.invalid')
    try:
        endpoint, values = adapter.match(path.strip('/'))
    except NotFound:
        return
    return values['year'], values['month'], values['day']


def process_blog_entry(context):
    if context.pub_date is None:
        pattern = context.config.get('modules.blog.pub_date_match',
                                     '/<int:year>/<int:month>/<int:day>/')
        if pattern is not None:
            rv = test_pattern(context.slug, pattern)
            if rv is not None:
                context.pub_date = datetime(*rv)

    if context.pub_date is not None:
        context.builder.get_storage('blog') \
            .setdefault(context.pub_date.year, {}) \
            .setdefault(('0%d' % context.pub_date.month)[-2:], []) \
            .append(context)


def get_all_entries(builder):
    """Returns all blog entries in reverse order"""
    result = []
    storage = builder.get_storage('blog')
    years = storage.items()
    for year, months in years:
        for month, contexts in months.iteritems():
            result.extend(contexts)
    result.sort(key=lambda x: (x.pub_date, x.config.get('day-order', 0)),
                reverse=True)
    return result


def get_archive_summary(builder):
    """Returns a summary of the stuff in the archives."""
    storage = builder.get_storage('blog')
    years = storage.items()
    years.sort(key=lambda x: -x[0])
    return [YearArchive(builder, year, months) for year, months in years]


@contextfunction
def get_recent_blog_entries(context, limit=10):
    return get_all_entries(context['builder'])[:limit]


def write_index_page(builder):
    use_pagination = builder.config.root_get('modules.blog.use_pagination', True)
    per_page = builder.config.root_get('modules.blog.per_page', 10)
    entries = get_all_entries(builder)
    pagination = Pagination(builder, entries, 1, per_page, 'blog_index')
    while 1:
        with builder.open_link_file('blog_index', page=pagination.page) as f:
            rv = builder.render_template('blog/index.html', {
                'pagination':       pagination,
                'show_pagination':  use_pagination
            })
            f.write(rv.encode('utf-8') + '\n')
            if not use_pagination or not pagination.has_next:
                break
            pagination = pagination.get_next()


def write_archive_pages(builder):
    archive = get_archive_summary(builder)
    with builder.open_link_file('blog_archive') as f:
        rv = builder.render_template('blog/archive.html', {
            'archive':      archive
        })
        f.write(rv.encode('utf-8') + '\n')

    for entry in archive:
        with builder.open_link_file('blog_archive', year=entry.year) as f:
            rv = builder.render_template('blog/year_archive.html', {
                'entry':    entry
            })
            f.write(rv.encode('utf-8') + '\n')
        for subentry in entry.months:
            with builder.open_link_file('blog_archive', year=entry.year,
                                        month=subentry.month) as f:
                rv = builder.render_template('blog/month_archive.html', {
                    'entry':    subentry
                })
                f.write(rv.encode('utf-8') + '\n')


def write_feed(builder):
    blog_author = builder.config.root_get('author')
    url = builder.config.root_get('canonical_url') or 'http://localhost/'
    name = builder.config.get('feed.name') or u'Recent Blog Posts'
    subtitle = builder.config.get('feed.subtitle') or u'Recent blog posts'
    feed = AtomFeed(name,
                    subtitle=subtitle,
                    feed_url=urljoin(url, builder.link_to('blog_feed')),
                    url=url)
    for entry in get_all_entries(builder)[:10]:
        feed.add(entry.title, unicode(entry.render_contents()),
                 content_type='html', author=blog_author,
                 url=urljoin(url, entry.slug),
                 updated=entry.pub_date)
    with builder.open_link_file('blog_feed') as f:
        f.write(feed.to_string().encode('utf-8') + '\n')


def write_blog_files(builder):
    write_index_page(builder)
    write_archive_pages(builder)
    write_feed(builder)


def setup(builder):
    after_file_published.connect(process_blog_entry)
    before_build_finished.connect(write_blog_files)
    builder.register_url('blog_index', config_key='modules.blog.index_url',
                         config_default='/', defaults={'page': 1})
    builder.register_url('blog_index', config_key='modules.blog.paged_index_url',
                         config_default='/page/<page>/')
    builder.register_url('blog_archive', config_key='modules.blog.archive_url',
                         config_default='/archive/')
    builder.register_url('blog_archive',
                         config_key='modules.blog.year_archive_url',
                         config_default='/<year>/')
    builder.register_url('blog_archive',
                         config_key='modules.blog.month_archive_url',
                         config_default='/<year>/<month>/')
    builder.register_url('blog_feed', config_key='modules.blog.feed_url',
                         config_default='/feed.atom')
    builder.jinja_env.globals.update(
        get_recent_blog_entries=get_recent_blog_entries
    )

########NEW FILE########
__FILENAME__ = disqus
# -*- coding: utf-8 -*-
"""
    rstblog.modules.disqus
    ~~~~~~~~~~~~~~~~~~~~~~

    Implements disqus element if asked for.
    
    To use this, include ``disqus`` in the list of modules in your ``config.yml`` file,
    and add a configuration variable to match your settings : ``disqus.shortname`` 
    
    To set developer mode on the site, set ``disqus.developer=1`` in your ``config.yml`` file.
    
    To prevent comments on a particular page, set ``disqus = no`` in the page's YAML preamble.

    :copyright: (c) 2012 by Martin Andrews.
    :license: BSD, see LICENSE for more details.
"""
import jinja2

@jinja2.contextfunction
def get_disqus(context):
    var_shortname=context['builder'].config.root_get('modules.disqus.shortname', 'YOUR-DISQUS-SHORTNAME')

    var_developer=''
    if context['builder'].config.root_get('modules.disqus.developer', False):
        var_developer='var disqus_developer = 1;'
    
    disqus_txt="""
<div id="disqus_thread"></div>
<script type="text/javascript">
    var disqus_shortname = '%s'; // required: replace example with your forum shortname
    %s
    
    /* * * DON'T EDIT BELOW THIS LINE * * */
    (function() {
        var dsq = document.createElement('script'); dsq.type = 'text/javascript'; dsq.async = true;
        dsq.src = 'http://' + disqus_shortname + '.disqus.com/embed.js';
        (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(dsq);
    })();
</script>
<noscript>Please enable JavaScript to view the <a href="http://disqus.com/?ref_noscript">comments powered by Disqus.</a></noscript>
<a href="http://disqus.com" class="dsq-brlink">blog comments powered by <span class="logo-disqus">Disqus</span></a>
""" % ( var_shortname, var_developer, )

    if not context['config'].get('disqus', True):
        disqus_txt='' # "<h1>DISQUS DEFEATED</h1>"
        
    return jinja2.Markup(disqus_txt.encode('utf-8'))


def setup(builder):
    builder.jinja_env.globals['get_disqus'] = get_disqus

########NEW FILE########
__FILENAME__ = latex
# -*- coding: utf-8 -*-
"""
    rstblog.modules.latex
    ~~~~~~~~~~~~~~~~~~~~~

    Simple latex support for formulas.

    :copyright: (c) 2010 by Armin Ronacher, Georg Brandl.
    :license: BSD, see LICENSE for more details.
"""
import os
import re
import tempfile
import shutil
from hashlib import sha1
from os import path, getcwd, chdir
from subprocess import Popen, PIPE
from werkzeug import escape

from docutils import nodes, utils
from docutils.parsers.rst import Directive, directives, roles

DOC_WRAPPER = r'''
\documentclass[12pt]{article}
\usepackage[utf8x]{inputenc}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage{amsfonts}
%%\usepackage{mathpazo}
\usepackage{bm}
\usepackage[active]{preview}
\pagestyle{empty}
\begin{document}
\begin{preview}
%s
\end{preview}
\end{document}
'''

_depth_re = re.compile(r'\[\d+ depth=(-?\d+)\]')


def wrap_displaymath(math):
    ret = []
    for part in math.split('\n\n'):
        ret.append('\\begin{split}%s\\end{split}\\notag' % part)
    return '\\begin{gather}\n' + '\\\\'.join(ret) + '\n\\end{gather}'


def find_depth(stdout):
    for line in stdout.splitlines():
        m = _depth_re.match(line)
        if m:
            return int(m.group(1))


def render_math(context, math):
    relname = '_math/%s.png' % sha1(math.encode('utf-8')).hexdigest()
    full_filename = context.builder.get_full_static_filename(relname)
    url = context.builder.get_static_url(relname)

    # if we rebuild the document, we also want to rebuild the math
    # for it.
    if os.path.isfile(full_filename):
        os.remove(full_filename)

    latex = DOC_WRAPPER % wrap_displaymath(math)

    depth = None
    tempdir = tempfile.mkdtemp()
    try:
        tf = open(path.join(tempdir, 'math.tex'), 'w')
        tf.write(latex.encode('utf-8'))
        tf.close()

        # build latex command; old versions of latex don't have the
        # --output-directory option, so we have to manually chdir to the
        # temp dir to run it.
        ltx_args = ['latex', '--interaction=nonstopmode', 'math.tex']

        curdir = getcwd()
        chdir(tempdir)

        try:
            p = Popen(ltx_args, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
        finally:
            chdir(curdir)

        if p.returncode != 0:
            raise Exception('latex exited with error:\n[stderr]\n%s\n'
                            '[stdout]\n%s' % (stderr, stdout))

        directory = os.path.dirname(full_filename)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        dvipng_args = ['dvipng', '-o', full_filename, '-T', 'tight', '-z9',
                       '-D', str(int(context.builder.config.root_get(
                            'modules.latex.font_size', 16) * 72.27 / 10)),
                       '-bg', 'Transparent',
                       '--depth', os.path.join(tempdir, 'math.dvi')]
        p = Popen(dvipng_args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise Exception('dvipng exited with error:\n[stderr]\n%s\n'
                            '[stdout]\n%s' % (stderr, stdout))
        depth = find_depth(stdout)
    finally:
        try:
            shutil.rmtree(tempdir)
        except (IOError, OSError):
            # might happen? unsure
            pass

    return url, depth


def make_imgtag(url, depth, latex):
    bits = ['<img src="%s" alt="%s"' % (escape(url), escape(latex))]
    if depth is not None:
        bits.append(' style="vertical-align: %dpx"' % -depth)
    bits.append('>')
    return ''.join(bits)


class MathDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        'label': directives.unchanged,
        'nowrap': directives.flag
    }

    def run(self):
        latex = '\n'.join(self.content)
        if self.arguments and self.arguments[0]:
            latex = self.arguments[0] + '\n\n' + latex
        url, _ = render_math(self.state.document.settings.rstblog_context,
                             latex)
        return [nodes.raw('', u'<blockquote class="math">%s</blockquote>'
                          % make_imgtag(url, None, latex), format='html')]


def math_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    latex = utils.unescape(text, restore_backslashes=True)
    url, depth = render_math(inliner.document.settings.rstblog_context, latex)
    return [nodes.raw('', u'<span class="math">%s</span>' %
                      make_imgtag(url, depth, latex), format='html')], []


def setup(builder):
    directives.register_directive('math', MathDirective)
    roles.register_local_role('math', math_role)

########NEW FILE########
__FILENAME__ = pygments
# -*- coding: utf-8 -*-
"""
    rstblog.modules.pygments
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Adds support for pygments.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import
from rstblog.signals import before_file_processed, \
     before_build_finished

from docutils import nodes
from docutils.parsers.rst import Directive, directives

from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name


html_formatter = None


class CodeBlock(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self):
        try:
            lexer = get_lexer_by_name(self.arguments[0])
        except ValueError:
            lexer = TextLexer()
        code = u'\n'.join(self.content)
        formatted = highlight(code, lexer, html_formatter)
        return [nodes.raw('', formatted, format='html')]


def inject_stylesheet(context, **kwargs):
    context.add_stylesheet('_pygments.css')


def write_stylesheet(builder, **kwargs):
    with builder.open_static_file('_pygments.css', 'w') as f:
        f.write(html_formatter.get_style_defs())


def setup(builder):
    global html_formatter
    style = get_style_by_name(builder.config.root_get('modules.pygments.style'))
    html_formatter = HtmlFormatter(style=style)
    directives.register_directive('code-block', CodeBlock)
    directives.register_directive('sourcecode', CodeBlock)
    before_file_processed.connect(inject_stylesheet)
    before_build_finished.connect(write_stylesheet)

########NEW FILE########
__FILENAME__ = tags
# -*- coding: utf-8 -*-
"""
    rstblog.modules.tags
    ~~~~~~~~~~~~~~~~~~~~

    Implements tagging.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from math import log
from urlparse import urljoin

from jinja2 import contextfunction

from werkzeug.contrib.atom import AtomFeed

from rstblog.signals import after_file_published, \
     before_build_finished


class Tag(object):

    def __init__(self, name, count):
        self.name = name
        self.count = count
        self.size = 100 + log(count or 1) * 20


@contextfunction
def get_tags(context, limit=50):
    tags = get_tag_summary(context['builder'])
    if limit:
        tags.sort(key=lambda x: -x.count)
        tags = tags[:limit]
    tags.sort(key=lambda x: x.name.lower())
    return tags


def get_tag_summary(builder):
    storage = builder.get_storage('tags')
    by_tag = storage.get('by_tag', {})
    result = []
    for tag, tagged in by_tag.iteritems():
        result.append(Tag(tag, len(tagged)))
    result.sort(key=lambda x: x.count)
    return result


def get_tagged_entries(builder, tag):
    if isinstance(tag, Tag):
        tag = tag.name
    storage = builder.get_storage('tags')
    by_tag = storage.get('by_tag', {})
    return by_tag.get(tag) or []


def remember_tags(context):
    tags = context.config.merged_get('tags') or []
    storage = context.builder.get_storage('tags')
    by_file = storage.setdefault('by_file', {})
    by_file[context.source_filename] = tags
    by_tag = storage.setdefault('by_tag', {})
    for tag in tags:
        by_tag.setdefault(tag, []).append(context)
    context.tags = frozenset(tags)


def write_tagcloud_page(builder):
    with builder.open_link_file('tagcloud') as f:
        rv = builder.render_template('tagcloud.html')
        f.write(rv.encode('utf-8') + '\n')


def write_tag_feed(builder, tag):
    blog_author = builder.config.root_get('author')
    url = builder.config.root_get('canonical_url') or 'http://localhost/'
    name = builder.config.get('feed.name') or u'Recent Blog Posts'
    subtitle = builder.config.get('feed.subtitle') or u'Recent blog posts'
    feed = AtomFeed(name,
                    subtitle=subtitle,
                    feed_url=urljoin(url, builder.link_to('blog_feed')),
                    url=url)
    for entry in get_tagged_entries(builder, tag)[:10]:
        feed.add(entry.title, unicode(entry.render_contents()),
                 content_type='html', author=blog_author,
                 url=urljoin(url, entry.slug),
                 updated=entry.pub_date)
    with builder.open_link_file('tagfeed', tag=tag.name) as f:
        f.write(feed.to_string().encode('utf-8') + '\n')


def write_tag_page(builder, tag):
    entries = get_tagged_entries(builder, tag)
    entries.sort(key=lambda x: (x.title or '').lower())
    with builder.open_link_file('tag', tag=tag.name) as f:
        rv = builder.render_template('tag.html', {
            'tag':      tag,
            'entries':  entries
        })
        f.write(rv.encode('utf-8') + '\n')


def write_tag_files(builder):
    write_tagcloud_page(builder)
    for tag in get_tag_summary(builder):
        write_tag_page(builder, tag)
        write_tag_feed(builder, tag)


def setup(builder):
    after_file_published.connect(remember_tags)
    before_build_finished.connect(write_tag_files)
    builder.register_url('tag', config_key='modules.tags.tag_url',
                         config_default='/tags/<tag>/')
    builder.register_url('tagfeed', config_key='modules.tags.tag_feed_url',
                         config_default='/tags/<tag>/feed.atom')
    builder.register_url('tagcloud', config_key='modules.tags.cloud_url',
                         config_default='/tags/')
    builder.jinja_env.globals['get_tags'] = get_tags

########NEW FILE########
__FILENAME__ = programs
# -*- coding: utf-8 -*-
"""
    rstblog.programs
    ~~~~~~~~~~~~~~~~

    Builtin build programs.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
import os
import yaml
import shutil
from datetime import datetime
from StringIO import StringIO
from weakref import ref


class Program(object):

    def __init__(self, context):
        self._context = ref(context)

    @property
    def context(self):
        rv = self._context()
        if rv is None:
            raise RuntimeError('context went away, program is invalid')
        return rv

    def get_desired_filename(self):
        folder, basename = os.path.split(self.context.source_filename)
        simple_name = os.path.splitext(basename)[0]
        if simple_name == 'index':
            suffix = 'index.html'
        else:
            suffix = os.path.join(simple_name, 'index.html')
        return os.path.join(folder, suffix)

    def prepare(self):
        pass

    def render_contents(self):
        return u''

    def run(self):
        raise NotImplementedError()


class CopyProgram(Program):
    """A program that copies a file over unchanged"""

    def run(self):
        self.context.make_destination_folder()
        shutil.copy(self.context.full_source_filename,
                    self.context.full_destination_filename)

    def get_desired_filename(self):
        return self.context.source_filename


class TemplatedProgram(Program):
    default_template = None

    def get_template_context(self):
        return {}

    def run(self):
        template_name = self.context.config.get('template') \
            or self.default_template
        context = self.get_template_context()
        rv = self.context.render_template(template_name, context)
        with self.context.open_destination_file() as f:
            f.write(rv.encode('utf-8') + '\n')


class RSTProgram(TemplatedProgram):
    """A program that renders an rst file into a template"""
    default_template = 'rst_display.html'
    _fragment_cache = None

    def prepare(self):
        headers = ['---']
        with self.context.open_source_file() as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    break
                headers.append(line)
            title = self.parse_text_title(f)

        cfg = yaml.load(StringIO('\n'.join(headers)))
        if cfg:
            if not isinstance(cfg, dict):
                raise ValueError('expected dict config in file "%s", got: %.40r' \
                    % (self.context.source_filename, cfg))
            self.context.config = self.context.config.add_from_dict(cfg)
            self.context.destination_filename = cfg.get(
                'destination_filename',
                self.context.destination_filename)

            title_override = cfg.get('title')
            if title_override is not None:
                title = title_override

            pub_date_override = cfg.get('pub_date')
            if pub_date_override is not None:
                if not isinstance(pub_date_override, datetime):
                    pub_date_override = datetime(pub_date_override.year,
                                                 pub_date_override.month,
                                                 pub_date_override.day)
                self.context.pub_date = pub_date_override

            summary_override = cfg.get('summary')
            if summary_override is not None:
                self.context.summary = summary_override

        if title is not None:
            self.context.title = title

    def parse_text_title(self, f):
        buffer = []
        for line in f:
            line = line.rstrip()
            if not line:
                break
            buffer.append(line)
        return self.context.render_rst('\n'.join(buffer).decode('utf-8')).get('title')

    def get_fragments(self):
        if self._fragment_cache is not None:
            return self._fragment_cache
        with self.context.open_source_file() as f:
            while f.readline().strip():
                pass
            rv = self.context.render_rst(f.read().decode('utf-8'))
        self._fragment_cache = rv
        return rv

    def render_contents(self):
        return self.get_fragments()['fragment']

    def get_template_context(self):
        ctx = TemplatedProgram.get_template_context(self)
        ctx['rst'] = self.get_fragments()
        return ctx

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
"""
    rstblog.server
    ~~~~~~~~~~~~~~

    Development server that rebuilds automatically

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import urllib
import posixpath
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler


class SimpleRequestHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.server.builder.anything_needs_build():
            print >> sys.stderr, 'Detected change, building'
            self.server.builder.run()
        SimpleHTTPRequestHandler.do_GET(self)

    def translate_path(self, path):
        path = path.split('?', 1)[0].split('#', 1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = self.server.builder.default_output_folder
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path

    def log_request(self, code='-', size='-'):
        pass

    def log_error(self, *args):
        pass

    def log_message(self, format, *args):
        pass


class Server(HTTPServer):

    def __init__(self, host, port, builder):
        HTTPServer.__init__(self, (host, int(port)), SimpleRequestHandler)
        self.builder = builder

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
"""
    rstblog.signals
    ~~~~~~~~~~~~~~~

    Blinker signals for the modules and other hooks.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from blinker import Namespace


signals = Namespace()

#: before the file is processed.  The context is already prepared and if
#: the given program was able to extract configuration from the file, it
#: will already be stored on the context.
before_file_processed = signals.signal('before_file_processed')

#: after the file was prepared
after_file_prepared = signals.signal('after_file_prepared')

#: after the file was published (public: yes)
after_file_published = signals.signal('after_file_published')

#: fired the moment before a template is rendered with the context object
#: that is about to be passed to the template.
before_template_rendered = signals.signal('before_template_rendered')

#: fired right before the build finished.  This is the perfect place to
#: write some more files to the build folder.
before_build_finished = signals.signal('before_build_finished')

#: emitted right before a file is actually built.
before_file_built = signals.signal('before_file_built')

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    rstblog.utils
    ~~~~~~~~~~~~~

    Various utilities.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from math import ceil

from jinja2 import Markup


class Pagination(object):
    """Internal helper class for paginations"""

    def __init__(self, builder, entries, page, per_page, url_key):
        self.builder = builder
        self.entries = entries
        self.page = page
        self.per_page = per_page
        self.url_key = url_key

    @property
    def total(self):
        return len(self.entries)

    @property
    def pages(self):
        return int(ceil(self.total / float(self.per_page)))

    def get_prev(self):
        return Pagination(self.builder, self.entries, self.page - 1,
                          self.per_page, self.url_key)

    @property
    def prev_num(self):
        """Number of the previous page."""
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def get_next(self):
        return Pagination(self.builder, self.entries, self.page + 1,
                          self.per_page, self.url_key)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        return self.page + 1

    def get_slice(self):
        return self.entries[(self.page - 1) * self.per_page:
                            self.page * self.per_page]

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        """
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.builder.render_template('_pagination.html', {
            'pagination':   self
        })

    def __html__(self):
        return Markup(unicode(self))

########NEW FILE########
