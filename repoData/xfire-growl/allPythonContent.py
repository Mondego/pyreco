__FILENAME__ = growl
#!/usr/bin/env python
#
# vim:syntax=python:sw=4:ts=4:expandtab
#
# Copyright (C) 2012 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#

__author__ = 'Rico Schiekel <fire@downgra.de>'
__copyright__ = 'Copyright (C) 2012 Rico Schiekel'
__license__ = 'GPLv2'
__version__ = '0.3'


import os
import sys
import re
import shutil
import datetime
import time
import collections
import itertools
import functools
import inspect
from optparse import OptionParser

import yaml


def renderTemplate(template, context):
    raise NotImplementedError('no template engine configured!')


try:
    import jinja2

    jinja2_env = jinja2.Environment()

    def renderTemplate(template, context):
        template = template.decode("utf8")
        return jinja2_env.from_string(template).render(context)

    def templateFilter(func):
        """ decorator to easily create jinja2 filters
        """
        jinja2_env.filters[func.__name__] = func
except ImportError:
    pass


def wrap(orig_func):
    """ decorator to wrap an existing method of a class.
        e.g.

        @wrap(Post.write)
        def verbose_write(forig, self):
            print 'generating post: %s (from: %s)' % (self.title,
                                                      self.filename)
            return forig(self)

        the first parameter of the new function is the the original,
        overwritten function ('forig').
    """

    # har, some funky python magic NOW!

    def outer(new_func):

        @functools.wraps(orig_func)
        def wrapper(*args, **kwargs):
            return new_func(orig_func, *args, **kwargs)

        if inspect.ismethod(orig_func):
            setattr(orig_func.im_class, orig_func.__name__, wrapper)
        return wrapper
    return outer


class AttrDict(dict):
    """ dictionary which provides its items as attributes.
    """

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def copy(self):
        return AttrDict(super(AttrDict, self).copy())


class Config(object):
    """ base class providing some static configuration values.
    """

    LIB_DIR = HOOK_DIR = ''

    @classmethod
    def updateconfig(cls, base, deploy):
        cls.transformers = {}
        cls.BASE_DIR = base
        cls.DEPLOY_DIR = deploy
        cls.LAYOUT_DIR = os.path.join(base, '_layout')
        cls.HOOK_DIR = os.path.join(base, '_hooks')
        cls.LIB_DIR = os.path.join(base, '_libs')
        cls.POST_FILE_EXT = '.html'
        cls.ARTICLE_FILE_EXT = '.html'


class Template(Config):
    """ abstract template base class providing support for an
        yaml header, transforming based on file extension,
        rendering (only using current layout if defined) and
        layouting (applying all layouts).
    """

    RE_YAML = re.compile(r'(^---\s*$(?P<yaml>.*?)^---\s*$)?(?P<content>.*)',
                         re.M | re.S)

    def __init__(self, filename, layouts, context):
        super(Template, self).__init__()
        self.filename = filename
        self.layouts = layouts
        self.context = context.copy()
        self.context.layout = None
        self.read_yaml()

    def read_yaml(self):
        """ read yaml header and remove the header from content
        """
        self._content = file(self.filename, 'r').read()

        mo = self.RE_YAML.match(self._content)
        if mo and mo.groupdict().get('yaml'):
            self.context.update(yaml.load(mo.groupdict().get('yaml')))
            self._content = mo.groupdict().get('content')

    def transform(self):
        """ do transformation based on filename extension.
            e.g. do markdown or textile transformations
        """
        ext = os.path.splitext(self.filename)[-1][1:]
        t = self.transformers.get(ext, lambda x: x)
        return t(self._content)

    def render(self):
        """ render content, so transforming and then
            apply current layout.
        """
        ctx = self.context.copy()
        ctx.content = renderTemplate(self.transform(), ctx)
        layout = self.layouts.get(ctx.layout)
        if layout:
            return renderTemplate(layout.content, ctx)
        else:
            return ctx.content

    def layout(self):
        """ layout content, so transforming and then applying
            all layouts.
        """
        ctx = self.context.copy()
        ctx.content = self.render()
        layout = self.layouts.get(ctx.layout)
        if layout:
            layout = self.layouts.get(layout.layout)

        while layout != None:
            ctx.content = renderTemplate(layout.content, ctx)
            layout = self.layouts.get(layout.layout)

        return ctx.content

    def write(self, path, content):
        """ write content to path in deploy directory.
        """
        fname = os.path.join(self.DEPLOY_DIR, path)
        dirname = os.path.dirname(fname)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        f = file(fname, 'w')
        f.write(content.encode("utf8"))
        f.close()

    def __getattr__(self, name):
        if not name in self.context:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                    (self.__class__.__name__, name))
        return self.context[name]

    @property
    def transformed(self):
        return self.transform()


class Layout(Template):
    """ a layout template from _layouts/ directory.
    """

    def __init__(self, filename, context):
        super(Layout, self).__init__(filename, {}, context)

        base = os.path.basename(filename)
        ext = os.path.splitext(base)
        self.name = ext[0]

    @property
    def layout(self):
        return self.context.get('layout')

    @property
    def content(self):
        return self.transform()


class Page(Template):
    """ a page template which should be transformed. e.g. files which
        filename ends with an '_' or an transformer file extension.
    """

    TRANSFORM = ('_', )

    def __init__(self, filename, layout, context):
        super(Page, self).__init__(filename, layout, context)

        self.context.page = self

    @property
    def url(self):
        return self.path.replace(os.path.sep, '/')

    @property
    def urlparts(self):
        return self.url.split("/")

    @property
    def root(self):
        return "../" * self.url.count("/")

    @property
    def path(self):
        path = os.path.abspath(self.filename)
        npath, ext = os.path.splitext(path)
        if self.filename[-1] in Page.TRANSFORM:
            path = path[:-1]
        elif ext and ext[1:] in self.transformers:
            path = npath
        path = path.replace(os.path.abspath(self.BASE_DIR), '', 1)
        return path.lstrip(os.path.sep)

    @property
    def content(self):
        return self.render()

    def write(self):
        return super(Page, self).write(self.path, self.layout())

    @staticmethod
    def transformable(filename):
        """ return true, if the file is transformable. that means the
            filename ends with a character from self.TRANSFORM or
            self.transformers.
        """
        ext = os.path.splitext(filename)[-1]
        return ((filename[-1] in Page.TRANSFORM) or
                (ext and ext[1:] in Page.transformers))


class Site(Config):
    """ controls the site and holds the global context object. the context
        object contains all layouts, all posts and categories.
        hooks can be used to configure the context.
    """

    CONTEXT = AttrDict()
    IGNORE = ('_', '.')

    def __init__(self):
        super(Site, self).__init__()

        if not self.LIB_DIR in sys.path and os.path.isdir(self.LIB_DIR):
            sys.path.append(self.LIB_DIR)

        self.layouts = {}

        self.hooks()

        self.context = Site.CONTEXT.copy()
        if not 'site' in self.context:
            self.context.site = AttrDict()

        self.context.site.now = datetime.datetime.now()

    def hooks(self):
        """ load all available hooks from the _hooks/ directory.
        """
        if os.path.isdir(self.HOOK_DIR):
            for f in sorted(self.ignoreFilter(os.listdir(self.HOOK_DIR))):
                if f.endswith('.py'):
                    execfile(os.path.join(self.HOOK_DIR, f), globals())

    def prepare(self):
        """ read all layouts
        """
        self.read_layouts()

    def run(self):
        """ generate the site content to the deploy directory.
        """
        self.write_site_content()

        if options.serve != None:
            try:
                options.serve = (options.serve).strip('-')
                port = int(options.serve)
                site.serve(port)
            except ValueError:
                print 'Invalid Port: %s' % options.serve

    def read_layouts(self):
        if os.path.isdir(self.LAYOUT_DIR):
            self.layouts = [Layout(os.path.join(self.LAYOUT_DIR, f),
                                   self.context)
                                for f in self.ignoreFilter(os.listdir(
                                                            self.LAYOUT_DIR))]
            self.layouts = dict((l.name, l) for l in self.layouts)

    def write_site_content(self):
        """ copy site content to deploy directory.

            ignoring all files and directories, if their filename
            begins with a token defined in IGNORE.

            files with and filename ending with an token defined in
            TRANSFORM are transformed via the Page class. all other
            files are simple copied.
        """

        for root, dirs, files in os.walk(self.BASE_DIR):
            base = root.replace(self.BASE_DIR, '')
            base = base.lstrip(os.path.sep)

            for d in self.ignoreFilter(dirs):
                nd = os.path.join(self.DEPLOY_DIR, base, d)
                if not os.path.isdir(nd):
                    os.makedirs(nd)
            dirs[:] = self.ignoreFilter(dirs)

            for f in self.ignoreFilter(files):
                if Page.transformable(f):
                    Page(os.path.join(root, f),
                         self.layouts,
                         self.context).write()
                else:
                    path = os.path.abspath(root)
                    path = path.replace(os.path.abspath(self.BASE_DIR), '', 1)
                    path = path.lstrip(os.path.sep)
                    path = os.path.join(self.DEPLOY_DIR, path)
                    if not os.path.isdir(path):
                        os.makedirs(path)
                    shutil.copy(os.path.join(root, f), os.path.join(path, f))

    def serve(self, port):
        """ serve the deploy directory with a very simple, cgi
            capable web server on 0.0.0.0:<port>.
        """
        from BaseHTTPServer import HTTPServer
        from CGIHTTPServer import CGIHTTPRequestHandler
        os.chdir(self.DEPLOY_DIR)
        httpd = HTTPServer(('', int(port)), CGIHTTPRequestHandler)
        sa = httpd.socket.getsockname()
        print "Serving HTTP on", sa[0], "port", sa[1], "..."
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

    def ignoreFilter(self, seq):
        """ filter out files starting with self.IGNORE tokens
        """

        def ignore_filter(item):
            for ign in self.IGNORE:
                if item.startswith(ign):
                    return False
            return True
        return itertools.ifilter(ignore_filter, seq)

    def files_changed(self, path, extensions):
        """ return true if the files have changed since the last check
        """
        def file_times(path):
            """ return the last time files have been modified
            """
            for root, dirs, files in os.walk(path):
                dirs[:] = [x for x in dirs if x[0] != '.' and x != '_deploy']
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        try:
                            yield os.stat(os.path.join(root, file)).st_mtime
                        except:
                            yield None

        global LAST_MTIME
        mtime = max(file_times(path))
        if mtime > LAST_MTIME:
            LAST_MTIME = mtime
            return True
        return False

    def get_extensions(self, path):
        """ get all filename extensions and ignore the `_deploy` directory
        """
        exts = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [x for x in dirs if x[0] != '.' and x != '_deploy']
            for file in files:
                ext = os.path.splitext(file)[-1][1:]
                exts.append(ext)
        return set(exts)

    def setupOptions(self, parser):
        parser.add_option('--serve',
                          action = 'store', dest = 'serve',
                          metavar = 'PORT',
                          help = 'Start web server')

        parser.set_defaults(version = False)
        parser.add_option('-v', '--version',
                          action = 'store_true', dest = 'version',
                          help = 'Output version information and exit')
        parser.add_option('-r', '--autoreload',
                          action = 'store_true', dest = 'autoreload',
                          help = 'Relaunch Growl each time a modification'
                                 ' occurs on the content files.')


if __name__ == '__main__':
    DEFAULT_PORT = 8080
    LAST_MTIME = 0
    parser = OptionParser(usage = 'syntax: %prog [options] <from> [to]')

    base = deploy_path = None
    args = sys.argv[1:]

    for arg in sys.argv[:0:-1]:
        if not arg.startswith('-'):
            if not deploy_path:
                deploy_path = arg
            elif not base:
                base = arg
        elif arg == '--':
            break

    if not base and deploy_path:
        base = deploy_path
        deploy_path = os.path.join(base, '_deploy')

    if base and os.path.isdir(base):
        Config.updateconfig(base, deploy_path)

    site = Site()

    site.setupOptions(parser)
    (options, args) = parser.parse_args(args)

    if options.version:
        print 'growl version %s - %s (%s)' % (__version__,
                                              __copyright__,
                                              __license__)
        sys.exit(0)

    if not base:
        parser.error('"from" parameter missing!')

    if not os.path.isdir(base):
        print 'error: invalid directory: %s' % base
        sys.exit(2)

    try:
        import markdown
        Config.transformers.setdefault('markdown', markdown.markdown)
    except ImportError:
        pass

    try:
        import textile
        Config.transformers.setdefault('textile', textile.textile)
    except ImportError:
        pass

    try:
        # set jinja2 loader to enable template inheritance
        jinja2_env.loader = jinja2.FileSystemLoader(site.LAYOUT_DIR)
    except NameError:
        pass

    site.options = options

    extensions = site.get_extensions(base)

    if options.autoreload:
        while True:
            try:
                if site.files_changed(base, extensions):
                    site.prepare()
                    site.run()
                time.sleep(1)
            except KeyboardInterrupt:
                break
    else:
        site.prepare()
        site.run()

########NEW FILE########
__FILENAME__ = deploy_rsync
# vim:syntax=python:sw=4:ts=4:expandtab
#
# Copyright (C) 2009 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#

import subprocess

REMOTE_PATH = 'user@host:/path/'

@wrap(Site.setupOptions)
def setupOptions(forig, self, parser):
    forig(self, parser)
    parser.set_defaults(deploy = False)
    parser.add_option('--deploy',
                      action = 'store_true', dest = 'deploy',
                      help = 'deploy site')


@wrap(Site.run)
def run_rsync(forig, self):
    # first run 'default' actions and maybe other run hooks
    forig(self)

    if self.options.deploy:

        cmd = 'rsync -ahz --delete %s/* %s\n' % (self.DEPLOY_DIR, REMOTE_PATH)
        sys.stderr.write('deploy to >>> %s\n' % REMOTE_PATH)
        ret = subprocess.call(cmd, shell=True)
        if ret == 0:
            sys.stderr.write('<<< finished\n')
        else:
            sys.stderr.write('<<< failed! (return code: %d)\n' % ret)

########NEW FILE########
__FILENAME__ = markdown2
# vim:syntax=python:sw=4:ts=4:expandtab
#
# Copyright (C) 2009 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#

"""
copy 'markdown2.py' from http://code.google.com/p/python-markdown2/
to _libs directory.
"""

import markdown2
import functools

Config.transformers['markdown2'] = functools.partial(
            markdown2.markdown,
            extras={'code-color': {"classes": True}})

Config.transformers['md2'] = Config.transformers['markdown2']

########NEW FILE########
__FILENAME__ = posts
# vim:syntax=python:sw=4:ts=4:expandtab
#
# Copyright (C) 2009 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#

import os
import datetime


class Post(Page):
    """ a post template mapping a single post from the _posts/
        directory.
    """

    def __init__(self, filename, layout, context):
        super(Post, self).__init__(filename, layout, context)

        base = os.path.basename(filename)
        ext = os.path.splitext(base)

        self.year, self.month, self.day, self.slug = ext[0].split('-', 3)

        self.context.post = self

        cats = ','.join((self.context.get('category', ''),
                         self.context.get('categories', '')))
        if 'category' in self.context:
            del self.context['category']
        if 'categories' in self.context:
            del self.context['categories']
        self.categories = [c.strip() for c in cats.split(',') if c]

    @property
    def date(self):
        return datetime.datetime(int(self.year),
                                 int(self.month),
                                 int(self.day))

    @property
    def url(self):
        return os.path.join(self.year, self.month, self.day, self.slug)

    @property
    def path(self):
        return os.path.join(self.url, 'index' + self.POST_FILE_EXT)

    @property
    def content(self):
        return self.render()

    @property
    def publish(self):
        return self.context.get('publish', True)

    def __cmp__(self, other):
        return cmp(self.date, other.date)

    @staticmethod
    def setup(clazz):
        clazz.POST_DIR = os.path.join(clazz.BASE_DIR, '_posts')

        def read_posts(self):
            self.posts = []
            if os.path.isdir(self.POST_DIR):
                self.posts = [Post(os.path.join(self.POST_DIR, f),
                                   self.layouts,
                                   self.context)
                              for f in self.ignoreFilter(os.listdir(
                                                         self.POST_DIR))]
                self.context.site.posts = sorted(p for p in self.posts
                                                    if p.publish)
                self.context.site.unpublished_posts = sorted(p for
                                                             p in self.posts
                                                             if not p.publish)

        def calc_categories(self):
            self.categories = AttrDict()
            for post in self.posts:
                if post.publish:
                    for cat in post.categories:
                        self.categories.setdefault(cat, []).append(post)
                    if not post.categories:
                        self.categories.setdefault(None, []).append(post)
            self.context.site.categories = self.categories

        def write_posts(self):
            for p in self.posts:
                p.write()

        @wrap(clazz.prepare)
        def site_prepare(forig, self):
            """ read all posts and calculate the categories.
            """
            forig(self)
            read_posts(self)
            calc_categories(self)

        @wrap(clazz.run)
        def site_run(forig, self):
            """ write all posts to the deploy directory.
            """
            write_posts(self)
            forig(self)

Post.setup(Site) # whooha!

########NEW FILE########
__FILENAME__ = posts_ui
# vim:syntax=python:sw=4:ts=4:expandtab
#
# Copyright (C) 2009 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#

import os
import time
import datetime
import tempfile
import textwrap
import readline
import urllib
import hashlib


def setup_posts_ui():

    def get_editor():
        editor = os.environ.get('GROWL_EDITOR')
        if not editor:
            editor = os.environ.get('EDITOR')
        if not editor:
            editor = 'vi'
        return editor

    def launch_editor(content = ''):
        fn = None
        try:
            fid, fn = tempfile.mkstemp('.post', 'growl_', None, True)
            f = open(fn, 'w')
            f.write(content)
            f.close()

            mod_time_start = os.stat(fn).st_mtime
            rcode = subprocess.call([get_editor(), fn])
            mod_time_end = os.stat(fn).st_mtime

            hash_org = hashlib.sha256(content).digest()
            f = open(fn, 'r')
            content = f.read()
            f.close()
            hash_new = hashlib.sha256(content).digest()

            if (rcode != 0 or
                    mod_time_end == mod_time_start or
                    hash_org == hash_new):
                return None

            # only delete temp file if anything went ok
            return content
        finally:
            if fn:
                os.unlink(fn)

    def raw_input_default(prompt, value = None):
        if value:
            readline.set_startup_hook(lambda: readline.insert_text(value))
        try:
            return raw_input(prompt)
        finally:
            if value:
                readline.set_startup_hook(None)

    def mangle_url(url):
        ou = url
        url = url.lower()
        url = ''.join(c for c in url if c not in mangle_url.SP)
        url = url.replace('&', ' and ')
        url = url.replace('.', ' dot ')
        url = url.strip()
        url = url.replace(' ', '_')
        return urllib.quote(url)
    mangle_url.SP = '`~!@#$%^*()+={}[]|\\;:\'",<>/?'

    def create_new_post(self):
        TEMPLATE = textwrap.dedent("""
        ---
        layout: post
        title: ???
        categories: ???
        ---
        """).strip()
        try:
            content = launch_editor(TEMPLATE)
            if content:
                # load yaml header
                mo = Template.RE_YAML.match(content)
                if mo and mo.groupdict().get('yaml'):
                    meta = yaml.load(mo.groupdict().get('yaml'))
                    title = meta.get('title')

                if title:
                    title = mangle_url(title)

                    tnow = datetime.datetime.now().timetuple()
                    filename = time.strftime('%Y-%m-%d-', tnow)
                    filename += title

                    try:
                        filename = raw_input_default('filename: ', filename)
                        filename = os.path.join(self.POST_DIR, filename)
                        f = open(filename, 'w')
                        f.write(content)
                        f.close()
                        print 'created post: %s' % filename
                    except KeyboardInterrupt:
                        # save backup to temp file
                        print '\nabort...'
                        fid, fn = tempfile.mkstemp('.post', 'growl_',
                                                   None, True)
                        f = open(fn, 'w')
                        f.write(content)
                        f.close()
                else:
                    print 'abort... (no title)'
            else:
                print 'abort...'
        except Exception, e:
            print 'can\'t create new post: %s' % e
            raise

    @wrap(Site.setupOptions)
    def setupOptions(forig, self, parser):
        forig(self, parser)
        parser.add_option('-n', '--newpost',
                          action = 'store_true', dest = 'new_post',
                          help = 'create new post')

    @wrap(Site.run)
    def site_run(forig, self):
        """ write all posts to the deploy directory.
        """
        if self.options.new_post:
            create_new_post(self)
        else:
            forig(self)

setup_posts_ui()

########NEW FILE########
__FILENAME__ = status
# vim:syntax=python:sw=4:ts=4:expandtab
#
# Copyright (C) 2009 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#

import sys


@wrap(Post.write)
def verbose_post_write(forig, self):
    sys.stderr.write('post: %s - %s\n' %
                     (self.date.strftime('%Y-%m-%d'), self.title))
    return forig(self)


@wrap(Page.write)
def verbose_page_write(forig, self):
    sys.stderr.write('page: %s\n' % self.path)
    return forig(self)

########NEW FILE########
__FILENAME__ = template_filters
# vim:syntax=python:sw=4:ts=4:expandtab
#
# Copyright (C) 2009 Rico Schiekel (fire at downgra dot de)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#


@templateFilter
def dateFormat(dt, format='%Y-%m-%d'):
    return dt.strftime(format)


@templateFilter
def xmldatetime(dt):
    """ shameless stolen from http://github.com/lakshmivyas/hyde
        thanks alot
    """
    zprefix = "Z"
    tz = dt.strftime("%z")
    if tz:
        zprefix = tz[:3] + ":" + tz[3:]
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + zprefix


@templateFilter
def xtruncate(s, length=255, end='...'):
    import tidy

    options = dict(output_xhtml=1,
                   add_xml_decl=1,
                   indent=1,
                   show_body_only=1,
                   tidy_mark=0)
    return str(tidy.parseString(str(s[:length]) + end, **options))

########NEW FILE########
