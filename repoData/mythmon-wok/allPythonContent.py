__FILENAME__ = __hooks__
from wok.contrib.hooks import HeadingAnchors

hooks = {
    'page.template.post': [ HeadingAnchors() ],
}

########NEW FILE########
__FILENAME__ = __hooks__
import logging

hook_count = 0
def make_hook(name):
    def logging_hook(*args):
        global hook_count
        logging.info('logging_hook: {0}: {1}'.format(name, hook_count))
        hook_count += 1
    return [logging_hook]

hooks = {
    'site.start': make_hook('site.start'),
    'site.output.pre': make_hook('site.output.pre'),
    'site.output.post': make_hook('site.output.post'),
    'site.content.gather.pre': make_hook('site.content.gather.pre'),
    'site.content.gather.post': make_hook('site.content.gather.post'),
    'page.meta.pre': make_hook('page.template.pre'),
    'page.meta.post': make_hook('page.template.post'),
    'page.render.pre': make_hook('page.template.pre'),
    'page.render.post': make_hook('page.template.post'),
    'page.template.pre': make_hook('page.template.pre'),
    'page.template.post': make_hook('page.template.post'),
    'site.stop': make_hook('site.stop'),
}

logging.info('loaded hooks.')

########NEW FILE########
__FILENAME__ = hooks
# vim: set fileencoding=utf8 :
"""Some hooks that might be useful."""

import os
import subprocess
from StringIO import StringIO
import logging

from slugify import slugify

from wok.exceptions import DependencyException

try:
    from lxml import etree
except ImportError:
    etree = None


class HeadingAnchors(object):
    """
    Put some paragraph heading anchors.

    Serves as a 'page.template.post' wok hook.
    """

    def __init__(self, max_heading=3):
        if not etree:
            logging.warning('To use the HeadingAnchors hook, you must install '
                'the library lxml.')
            return
        self.max_heading = max_heading
        logging.info('Loaded hook HeadingAnchors')

    def __call__(self, config, page):
        if not etree:
            return
        logging.debug('Called hook HeadingAnchors on {0}'.format(page))
        parser = etree.HTMLParser()
        sio_source = StringIO(page.rendered)
        tree = etree.parse(sio_source, parser)

        for lvl in range(1, self.max_heading+1):
            headings = tree.iterfind('//h{0}'.format(lvl))
            for heading in headings:
                if not heading.text:
                    continue
                logging.debug('[HeadingAnchors] {0} {1}'
                        .format(heading, heading.text))

                name = 'heading-{0}'.format(slugify(heading.text))
                anchor = etree.Element('a')
                anchor.set('class', 'heading_anchor')
                anchor.set('href', '#' + name)
                anchor.set('title', 'Permalink to this section.')
                anchor.text = u'¶'
                heading.append(anchor)

                heading.set('id', name)

        sio_destination = StringIO()

	# Use the extension of the template to determine the type of document 
	if page.template.filename.endswith(".html") or page.filename.endswith(".htm"):
        	logging.debug('[HeadingAnchors] outputting {0} as HTML'.format(page))
	        tree.write(sio_destination, method='html')
	else:
        	logging.debug('[HeadingAnchors] outputting {0} as XML'.format(page))
	        tree.write(sio_destination)
        page.rendered = sio_destination.getvalue()


def compile_sass(config, output_dir):
    '''
    Compile Sass files -> CSS in the output directory.

    Any .scss or .sass files found in the output directory will be compiled
    to CSS using Sass. The compiled version of the file will be created in the
    same directory as the Sass file with the same name and an extension of
    .css. For example, foo.scss -> foo.css.

    Serves as a 'site.output.post' wok hook, e.g., your __hooks__.py file might
    look like this:

        from wok.contrib.hooks import compile_sass

        hooks = {
            'site.output.post':[compile_sass]
        }

    Dependencies:

        - Ruby
        - Sass (http://sass-lang.com)
    '''
    logging.info('Running hook compile_sass on {0}.'.format(output_dir))
    for root, dirs, files in os.walk(output_dir):
        for f in files:
            fname, fext = os.path.splitext(f)
            if fext == ".scss" or fext == ".sass":
                abspath = os.path.abspath(root)
                sass_src = "%s/%s"%(abspath, f)
                sass_dest = "%s/%s.css"%(abspath, fname)
                sass_arg = "%s:%s"%(sass_src, sass_dest)
                logging.debug('[hook/sass] sass {0}'.format(sass_arg))
                try:
                    subprocess.call(['sass', sass_arg])
                except OSError:
                    logging.warning('[hook/compile_sass] Could not run SASS ' +
                                    'hook. (Is SASS installed?)')

########NEW FILE########
__FILENAME__ = dev_server
''' Really simple HTTP *development* server

Do *NOT* attempt to use this as anything resembling a production server. It is
meant to be used as a development test server only.

You might ask, "Why do I need a development server for static pages?" One
hyphenated modifier: "root-relative." Since wok dumps all of the media files
in the root output directory, pages that reside inside subdirectories still
need to access these media files in a unified way.

E.g., if you include `base.css` in your `base.html` template, `base.css` should
be accessable to any page that uses `base.html`, even if it's a categorized
page, and thus, goes into a subdirectory. This way, your CSS include tag could
read `<link type='text/css' href='/base.css' />` (note the '/' in the `href`
property) and `base.css` can be accessed from anywhere.
'''

import sys
import os
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

class dev_server:

    def __init__(self, serv_dir=None, host='', port=8000, dir_mon=False,
            watch_dirs=[], change_handler=None):
        '''
        Initialize a new development server on `host`:`port`, and serve the
        files in `serv_dir`. If `serv_dir` is not provided, it will use the
        current working directory.

        If `dir_mon` is set, the server will check for changes before handling
        every request. If a change is detected, then wok will regenerate the
        site.
        '''
        self.serv_dir = os.path.abspath(serv_dir)
        self.host = host
        self.port = port
        self.dir_mon = dir_mon
        self.watch_dirs = [os.path.abspath(d) for d in watch_dirs]
        self.change_handler = change_handler

    def run(self):
        if self.serv_dir:
            os.chdir(self.serv_dir)

        if self.dir_mon:
            wrap = RebuildHandlerWrapper(self.change_handler, self.watch_dirs)
            req_handler = wrap.request_handler
        else:
            req_handler = SimpleHTTPRequestHandler

        httpd = HTTPServer((self.host, self.port), req_handler)
        socket_info = httpd.socket.getsockname()

        print("Starting dev server on http://%s:%s... (Ctrl-C to stop)"
                %(socket_info[0], socket_info[1]))
        print "Serving files from", self.serv_dir

        if self.dir_mon:
            print "Monitoring the following directories for changes: "
            for d in self.watch_dirs:
                print "\t", d
        else:
            print "Directory monitoring is OFF"

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print "\nStopping development server..."


class RebuildHandlerWrapper(object):

    def __init__(wrap_self, rebuild, watch_dirs):
        """
        We can't pass arugments to HTTPRequestHandlers, because HTTPServer
        calls __init__. So make a closure.
        """
        wrap_self.rebuild = rebuild
        wrap_self.watch_dirs = watch_dirs

        wrap_self._modtime_sum = None
        wrap_self.changed()

        class RebuildHandler(SimpleHTTPRequestHandler):
            """Rebuild if something has changed."""

            def handle(self):
                """
                Handle a request and, if anything has changed, rebuild the
                site before responding.
                """
                if wrap_self.changed():
                    wrap_self.rebuild()

                SimpleHTTPRequestHandler.handle(self)

        wrap_self.request_handler = RebuildHandler

    def changed(self):
        """
        Returns if the contents of the monitored directories have changed since
        the last call. It will return always return false on first run. 
        """
        last_modtime_sum = self._modtime_sum

        # calculate simple sum of file modification times
        self._modtime_sum = 0
        for d in self.watch_dirs:
            for root, dirs, files in os.walk(d):
                for f in files:
                    abspath = os.path.join(root, f)
                    self._modtime_sum += os.stat(abspath).st_mtime

        if last_modtime_sum is None:
            # always return false on first run
            return False
        else:
            # otherwise return if file modification sums changed since last run
            return (last_modtime_sum != self._modtime_sum)

########NEW FILE########
__FILENAME__ = engine
#!/usr/bin/python2
import os
import sys
import shutil
from datetime import datetime
from optparse import OptionParser, OptionGroup
import logging

import yaml

import wok
from wok.page import Page, Author
from wok import renderers
from wok import util
from wok.dev_server import dev_server

import locale

class Engine(object):
    """
    The main engine of wok. Upon initialization, it generates a site from the
    source files.
    """
    default_options = {
        'content_dir': 'content',
        'template_dir': 'templates',
        'output_dir': 'output',
        'media_dir': 'media',
        'site_title': 'Some random Wok site',
        'url_pattern': '/{category}/{slug}{page}.{ext}',
        'url_include_index': True,
        'relative_urls': False,
        'locale': None,
        'markdown_extra_plugins': [],
    }
    SITE_ROOT = os.getcwd()

    def __init__(self, output_lvl=1):
        """
        Set up CLI options, logging levels, and start everything off.
        Afterwards, run a dev server if asked to.
        """

        # CLI options
        # -----------
        parser = OptionParser(version='%prog v{0}'.format(wok.version))

        # Add option to to run the development server after generating pages
        devserver_grp = OptionGroup(parser, "Development server",
                "Runs a small development server after site generation. "
                "--address and --port will be ignored if --server is absent.")
        devserver_grp.add_option('--server', action='store_true',
                dest='runserver',
                help="run a development server after generating the site")
        devserver_grp.add_option('--address', action='store', dest='address',
                help="specify ADDRESS on which to run development server")
        devserver_grp.add_option('--port', action='store', dest='port',
                type='int',
                help="specify PORT on which to run development server")
        parser.add_option_group(devserver_grp)

        # Options for noisiness level and logging
        logging_grp = OptionGroup(parser, "Logging",
                "By default, log messages will be sent to standard out, "
                "and report only errors and warnings.")
        parser.set_defaults(loglevel=logging.WARNING)
        logging_grp.add_option('-q', '--quiet', action='store_const',
                const=logging.ERROR, dest='loglevel',
                help="be completely quiet, log nothing")
        logging_grp.add_option('--warnings', action='store_const',
                const=logging.WARNING, dest='loglevel',
                help="log warnings in addition to errors")
        logging_grp.add_option('-v', '--verbose', action='store_const',
                const=logging.INFO, dest='loglevel',
                help="log ALL the things!")
        logging_grp.add_option('--debug', action='store_const',
                const=logging.DEBUG, dest='loglevel',
                help="log debugging info in addition to warnings and errors")
        logging_grp.add_option('--log', '-l', dest='logfile',
                help="log to the specified LOGFILE instead of standard out")
        parser.add_option_group(logging_grp)

        cli_options, args = parser.parse_args()

        # Set up logging
        # --------------
        logging_options = {
            'format': '%(levelname)s: %(message)s',
            'level': cli_options.loglevel,
        }
        if cli_options.logfile:
            logging_options['filename'] = cli_options.logfile
        else:
            logging_options['stream'] = sys.stdout

        logging.basicConfig(**logging_options)

        # Action!
        # -------
        self.generate_site()

        # Dev server
        # ----------
        if cli_options.runserver:
            ''' Run the dev server if the user said to, and watch the specified
            directories for changes. The server will regenerate the entire wok
            site if changes are found after every request.
            '''
            output_dir = os.path.join(self.options['server_root'])
            host = '' if cli_options.address is None else cli_options.address
            port = 8000 if cli_options.port is None else cli_options.port
            server = dev_server(serv_dir=output_dir, host=host, port=port,
                dir_mon=True,
                watch_dirs=[
                    self.options['media_dir'],
                    self.options['template_dir'],
                    self.options['content_dir']
                ],
                change_handler=self.generate_site)
            server.run()

    def generate_site(self):
        ''' Generate the wok site '''
        orig_dir = os.getcwd()
        os.chdir(self.SITE_ROOT)

        self.all_pages = []

        self.read_options()
        self.sanity_check()
        self.load_hooks()
        self.renderer_options()

        self.run_hook('site.start')

        self.prepare_output()
        self.load_pages()
        self.make_tree()
        self.render_site()

        self.run_hook('site.done')

        os.chdir(orig_dir)

    def read_options(self):
        """Load options from the config file."""
        self.options = Engine.default_options.copy()

        if os.path.isfile('config'):
            with open('config') as f:
                yaml_config = yaml.load(f)

            if yaml_config:
                self.options.update(yaml_config)

        # Make authors a list, even only a single author was specified.
        authors = self.options.get('authors', self.options.get('author', None))
        if isinstance(authors, list):
            self.options['authors'] = [Author.parse(a) for a in authors]
        elif isinstance(authors, str):
            csv = authors.split(',')
            self.options['authors'] = [Author.parse(a) for a in csv]
            if len(self.options['authors']) > 1:
                logging.warn('Deprecation Warning: Use YAML lists instead of '
                        'CSV for multiple authors. i.e. ["John Doe", "Jane '
                        'Smith"] instead of "John Doe, Jane Smith". In config '
                        'file.')

        if '{type}' in self.options['url_pattern']:
            logging.warn('Deprecation Warning: You should use {ext} instead '
                    'of {type} in the url pattern specified in the config '
                    'file.')

        # Set locale if needed
        wanted_locale = self.options.get('locale')
        if wanted_locale is not None:
            try:
                locale.setlocale(locale.LC_TIME, wanted_locale)
            except locale.Error as err:
                logging.warn('Unable to set locale to `%s`: %s',
                    wanted_locale, err
                )

        # add a subdir prefix to the output_dir, if present in the config
        self.options['server_root'] = self.options['output_dir']
        self.options['output_dir'] = os.path.join(self.options['output_dir'], self.options.get('url_subdir', ''))

    def renderer_options(self):
        """Monkeypatches renderer options as in `config` file."""
        # Markdown extra plugins
        markdown_extra_plugins = \
            self.options.get('markdown_extra_plugins', [])
        if hasattr(renderers, 'Markdown'):
            renderers.Markdown.plugins.extend(markdown_extra_plugins)
        if hasattr(renderers, 'Markdown2'):
            renderers.Markdown2.extras.extend(markdown_extra_plugins)

    def sanity_check(self):
        """Basic sanity checks."""
        # Make sure that this is (probabably) a wok source directory.
        if not (os.path.isdir('templates') or os.path.isdir('content')):
            logging.critical("This doesn't look like a wok site. Aborting.")
            sys.exit(1)

    def load_hooks(self):
        try:
            sys.path.append('hooks')
            import __hooks__
            self.hooks = __hooks__.hooks
            logging.info('Loaded {0} hooks: {0}'.format(self.hooks))
        except ImportError as e:
            if "__hooks__" in str(e):
                logging.info('No hooks module found.')
            else:
                # don't catch import errors raised within a hook
                logging.info('Import error within hooks.')
                raise

    def run_hook(self, hook_name, *args):
        """ Run specified hooks if they exist """
        logging.debug('Running hook {0}'.format(hook_name))
        returns = []
        try:
            for hook in self.hooks.get(hook_name, []):
                returns.append(hook(self.options, *args))
        except AttributeError:
            logging.info('Hook {0} not defined'.format(hook_name))
        return returns

    def prepare_output(self):
        """
        Prepare the output directory. Remove any contents there already, and
        then copy over the media files, if they exist.
        """
        if os.path.isdir(self.options['output_dir']):
            for name in os.listdir(self.options['output_dir']):
                # Don't remove dotfiles
                if name[0] == ".":
                    continue
                path = os.path.join(self.options['output_dir'], name)
                if os.path.isfile(path):
                    os.unlink(path)
                else:
                    shutil.rmtree(path)
        else:
            os.makedirs(self.options['output_dir'])

        self.run_hook('site.output.pre', self.options['output_dir'])

        # Copy the media directory to the output folder
        if os.path.isdir(self.options['media_dir']):
            try:
                for name in os.listdir(self.options['media_dir']):
                    path = os.path.join(self.options['media_dir'], name)
                    if os.path.isdir(path):
                        shutil.copytree(
                                path,
                                os.path.join(self.options['output_dir'], name),
                                symlinks=True
                        )
                    else:
                        shutil.copy(path, self.options['output_dir'])


            # Do nothing if the media directory doesn't exist
            except OSError:
                logging.warning('There was a problem copying the media files '
                                'to the output directory.')

            self.run_hook('site.output.post', self.options['output_dir'])

    def load_pages(self):
        """Load all the content files."""
        # Load pages from hooks (pre)
        for pages in self.run_hook('site.content.gather.pre'):
            if pages:
                self.all_pages.extend(pages)

        # Load files
        for root, dirs, files in os.walk(self.options['content_dir']):
            # Grab all the parsable files
            for f in files:
                # Don't parse hidden files.
                if f.startswith('.'):
                    continue

                ext = f.split('.')[-1]
                renderer = renderers.Plain

                for r in renderers.all:
                    if ext in r.extensions:
                        renderer = r
                        break
                else:
                    logging.warning('No parser found '
                            'for {0}. Using default renderer.'.format(f))
                    renderer = renderers.Renderer

                p = Page.from_file(os.path.join(root, f), self.options, self, renderer)
                if p and p.meta['published']:
                    self.all_pages.append(p)

        # Load pages from hooks (post)
        for pages in self.run_hook('site.content.gather.post', self.all_pages):
            if pages:
                self.all_pages.extend(pages)

    def make_tree(self):
        """
        Make the category pseudo-tree.

        In this structure, each node is a page. Pages with sub pages are
        interior nodes, and leaf nodes have no sub pages. It is not truly a
        tree, because the root node doesn't exist.
        """
        self.categories = {}
        site_tree = []
        # We want to parse these in a approximately breadth first order
        self.all_pages.sort(key=lambda p: len(p.meta['category']))

        # For every page
        for p in self.all_pages:
            # If it has a category (ie: is not at top level)
            if len(p.meta['category']) > 0:
                top_cat = p.meta['category'][0]
                if not top_cat in self.categories:
                    self.categories[top_cat] = []

                self.categories[top_cat].append(p.meta)

            try:
                # Put this page's meta in the right place in site_tree.
                siblings = site_tree
                for cat in p.meta['category']:
                    # This line will fail if the page is an orphan
                    parent = [subpage for subpage in siblings
                                 if subpage['slug'] == cat][0]
                    siblings = parent['subpages']
                siblings.append(p.meta)
            except IndexError:
                logging.error('It looks like the page "{0}" is an orphan! '
                        'This will probably cause problems.'.format(p.path))

    def render_site(self):
        """Render every page and write the output files."""
        # Gather tags
        tag_set = set()
        for p in self.all_pages:
            tag_set = tag_set.union(p.meta['tags'])
        tag_dict = dict()
        for tag in tag_set:
            # Add all pages with the current tag to the tag dict
            tag_dict[tag] = [p.meta for p in self.all_pages
                                if tag in p.meta['tags']]

        # Gather slugs
        slug_dict = dict((p.meta['slug'], p.meta) for p in self.all_pages)

        for p in self.all_pages:
            # Construct this every time, to avoid sharing one instance
            # between page objects.
            templ_vars = {
                'site': {
                    'title': self.options.get('site_title', 'Untitled'),
                    'datetime': datetime.now(),
                    'date': datetime.now().date(),
                    'time': datetime.now().time(),
                    'tags': tag_dict,
                    'pages': self.all_pages[:],
                    'categories': self.categories,
                    'slugs': slug_dict,
                },
            }

            for k, v in self.options.iteritems():
                if k not in ('site_title', 'output_dir', 'content_dir',
                        'templates_dir', 'media_dir', 'url_pattern'):

                    templ_vars['site'][k] = v

            if 'author' in self.options:
                templ_vars['site']['author'] = self.options['author']

            # Rendering the page might give us back more pages to render.
            new_pages = p.render(templ_vars)

            if p.meta['make_file']:
                p.write()

            if new_pages:
                logging.debug('found new_pages')
                self.all_pages += new_pages

if __name__ == '__main__':
    Engine()
    exit(0)

########NEW FILE########
__FILENAME__ = exceptions
class DependencyException(Exception):
    pass

########NEW FILE########
__FILENAME__ = jinja
import glob
import os

from jinja2.loaders import FileSystemLoader, TemplateNotFound
from jinja2.loaders import split_template_path

class AmbiguousTemplate(Exception):
    pass

class GlobFileLoader(FileSystemLoader):
    """
    As ``jinja2.loaders.FileSystemLoader`` except allow support for globbing.

    The loader takes the path to the templates as string, or if multiple
    locations are wanted a list of them which is then looked up in the
    given order:

    >>> loader = GlobFileLoader('/path/to/templates')
    >>> loader = GlobFileLoader(['/path/to/templates', '/other/path'])

    Per default the template encoding is ``'utf-8'`` which can be changed
    by setting the `encoding` parameter to something else.
    """

    def get_source(self, environment, template):
        pieces = split_template_path(template)
        for searchpath in self.searchpath:
            globbed_filename = os.path.join(searchpath, *pieces)
            filenames = glob.glob(globbed_filename)
            if len(filenames) > 1:
                raise AmbiguousTemplate(template)
            elif len(filenames) < 1:
                continue
            filename = filenames[0]

            with open(filename) as f:
                contents = f.read().decode(self.encoding)

            mtime = os.path.getmtime(filename)
            def uptodate():
                try:
                    return os.path.getmtime(filename) == mtime
                except OSError:
                    return False
            return contents, filename, uptodate
        else:
            raise TemplateNotFound(template)

########NEW FILE########
__FILENAME__ = page
# System
import os
import sys
from collections import namedtuple
from datetime import datetime, date, time
import logging
import copy

# Libraries
import jinja2
import yaml
import re
from slugify import slugify

# Wok
from wok import util
from wok import renderers
from wok.jinja import GlobFileLoader, AmbiguousTemplate

class Page(object):
    """
    A single page on the website in all it's form (raw, rendered, templated) ,
    as well as it's associated metadata.
    """

    tmpl_env = None

    @classmethod
    def create_tmpl_env(cls, options):
        cls.tmpl_env = jinja2.Environment(
                loader=GlobFileLoader(
                        options.get('template_dir', 'templates')),
                extensions=options.get('jinja2_extensions', []))

    def __init__(self, options, engine):
        self.options = options
        self.filename = None
        self.meta = {}
        self.engine = engine

    @classmethod
    def from_meta(cls, meta, options, engine, renderer=renderers.Plain):
        """
        Build a page object from a meta dictionary.

        Note that you still need to call `render` and `write` to do anything
        interesting.
        """
        page = cls(options, engine)
        page.meta = meta
        page.options = options
        page.renderer = renderer

        if 'pagination' in meta:
            logging.debug('from_meta: current page %d' %
                    meta['pagination']['cur_page'])

        # Make a template environment. Hopefully no one expects this to ever
        # change after it is instantiated.
        if cls.tmpl_env is None:
            cls.create_tmpl_env(page.options)

        page.build_meta()
        return page

    @classmethod
    def from_file(cls, path, options, engine, renderer=renderers.Plain):
        """
        Load a file from disk, and parse the metadata from it.

        Note that you still need to call `render` and `write` to do anything
        interesting.
        """
        page = cls(options, engine)
        page.original = None
        page.options = options
        page.renderer = renderer

        logging.info('Loading {0}'.format(os.path.basename(path)))

        if cls.tmpl_env is None:
            cls.create_tmpl_env(page.options)

        page.path = path
        page.filename = os.path.basename(path)

        with open(path, 'rU') as f:
            page.original = f.read().decode('utf-8')
            splits = page.original.split('\n---\n')

            if len(splits) > 3:
                logging.warning('Found more --- delimited sections in {0} '
                                'than expected. Squashing the extra together.'
                                .format(page.path))

            # Handle the case where no meta data was provided
            if len(splits) == 1:
                page.original = splits[0]
                page.meta = {}
                page.original_preview = ''

            elif len(splits) == 2:
                header = splits[0]
                page.meta = yaml.load(header)
                page.original = splits[1]
                page.original_preview = page.meta.get('preview', '')

            elif len(splits) >= 3:
                header = splits[0]
                page.meta = {}
                page.original = '\n'.join(splits[1:])
                page.original_preview = splits[1]
                page.meta.update(yaml.load(header))
                logging.debug('Got preview')

        page.build_meta()

        page.engine.run_hook('page.render.pre', page)
        page.meta['content'] = page.renderer.render(page.original)
        page.meta['preview'] = page.renderer.render(page.original_preview)
        page.engine.run_hook('page.render.post', page)

        return page

    def build_meta(self):
        """
        Ensures the guarantees about metadata for documents are valid.

        `page.title` - Will be a string.
        `page.slug` - Will be a string.
        `page.author` - Will have fields `name` and `email`.
        `page.authors` - Will be a list of Authors.
        `page.category` - Will be a list.
        `page.published` - Will exist.
        `page.datetime` - Will be a datetime, or None.
        `page.date` - Will be a date, or None.
        `page.time` - Will be a time, or None.
        `page.tags` - Will be a list.
        `page.url` - Will be the url of the page, relative to the web root.
        `page.subpages` - Will be a list containing every sub page of this page
        """

        self.engine.run_hook('page.meta.pre', self)

        if not self.meta:
            self.meta = {}

        # title
        if not 'title' in self.meta:
            if self.filename:
                # Take off the last file extension.
                self.meta['title'] = '.'.join(self.filename.split('.')[:-1])
                if (self.meta['title'] == ''):
                    self.meta['title'] = self.filename

                logging.warning("You didn't specify a title in {0}. Using the "
                                "file name as a title.".format(self.path))
            elif 'slug' in self.meta:
                self.meta['title'] = self.meta['slug']
                logging.warning("You didn't specify a title in {0}, which was "
                        "not generated from a file. Using the slug as a title."
                        .format(self.meta['slug']))
            else:
                logging.error("A page was generated that is not from a file, "
                        "has no title, and no slug. I don't know what to do. "
                        "Not using this page.")
                logging.info("Bad Meta's keys: {0}".format(self.meta.keys()))
                logging.debug("Bad Meta: {0}".format(self.meta))
                raise BadMetaException()

        # slug
        if not 'slug' in self.meta:
            if self.filename:
                filename_no_ext = '.'.join(self.filename.split('.')[:-1])
                if filename_no_ext == '':
                    filename_no_ext = self.filename
                self.meta['slug'] = slugify(filename_no_ext)
                logging.info("You didn't specify a slug, generating it from the "
                             "filename.")
            else:
                self.meta['slug'] = slugify(self.meta['title'])
                logging.info("You didn't specify a slug, and no filename "
                             "exists. Generating the slug from the title.")

        elif self.meta['slug'] != slugify(self.meta['slug']):
            logging.warning('Your slug should probably be all lower case, and '
                            'match "[a-z0-9-]*"')

        # authors and author
        authors = self.meta.get('authors', self.meta.get('author', None))
        if isinstance(authors, list):
            self.meta['authors'] = [Author.parse(a) for a in authors]
        elif isinstance(authors, str):
            self.meta['authors'] = [Author.parse(a) for a in authors.split(',')]
            if len(self.meta['authors']) > 1:
                logging.warn('Deprecation Warning: Use YAML lists instead of '
                        'CSV for multiple authors. i.e. ["John Doe", "Jane '
                        'Smith"] instead of "John Doe, Jane Smith". In '
                        '{0}.'.format(self.path))

        elif authors is None:
            self.meta['authors'] = self.options.get('authors', [])
        else:
            # wait, what? Authors is of wrong type.
            self.meta['authors'] = []
            logging.error(('Authors in {0} is an unknown type. Valid types '
                           'are string or list. Instead it is a {1}')
                           .format(self.meta['slug']), authors.type)

        if self.meta['authors']:
            self.meta['author'] = self.meta['authors'][0]
        else:
            self.meta['author'] = Author()

        # category
        if 'category' in self.meta:
            if isinstance(self.meta['category'], str):
                self.meta['category'] = self.meta['category'].split('/')
            elif isinstance(self.meta['category'], list):
                pass
            else:
                # category is of wrong type.
                logging.error('Category in {0} is an unknown type. Valid '
                              'types are string or list. Instead it is a {1}'
                              .format(self.meta['slug'], type(self.meta['category'])))
                self.meta['category'] = []
        else:
            self.meta['category'] = []
        if self.meta['category'] == None:
            self.meta = []

        # published
        if not 'published' in self.meta:
            self.meta['published'] = True

        # make_file
        if not 'make_file' in self.meta:
            self.meta['make_file'] = True

        # datetime, date, time
        util.date_and_times(self.meta)

        # tags
        if 'tags' in self.meta:
            if isinstance(self.meta['tags'], list):
                # good
                pass
            elif isinstance(self.meta['tags'], str):
                self.meta['tags'] = [t.strip() for t in
                    self.meta['tags'].split(',')]
                if len(self.meta['tags']) > 1:
                    logging.warn('Deprecation Warning: Use YAML lists instead '
                            'of CSV for multiple tags. i.e. tags: [guide, '
                            'howto] instead of tags: guide, howto. In {0}.'
                            .format(self.path))
        else:
            self.meta['tags'] = []

        logging.debug('Tags for {0}: {1}'.
                format(self.meta['slug'], self.meta['tags']))

        # pagination
        if 'pagination' not in self.meta:
            self.meta['pagination'] = {}

        if 'cur_page' not in self.meta['pagination']:
            self.meta['pagination']['cur_page'] = 1
        if 'num_pages' not in self.meta['pagination']:
            self.meta['pagination']['num_pages'] = 1

        # template
        try:
            template_type = str(self.meta.get('type', 'default'))
            self.template = self.tmpl_env.get_template(template_type + '.*')
        except jinja2.loaders.TemplateNotFound:
            logging.error('No template "{0}.*" found in template directory. Aborting.'
                    .format(template_type))
            sys.exit()
        except AmbiguousTemplate:
            logging.error(('Ambiguous template found. There are two files that '
                          'match "{0}.*". Aborting.').format(template_type))
            sys.exit()

        # url
        parts = {
            'slug': self.meta['slug'],
            'category': '/'.join(self.meta['category']),
            'page': self.meta['pagination']['cur_page'],
            'date': self.meta['date'],
            'datetime': self.meta['datetime'],
            'time': self.meta['time'],
        }
        logging.debug('current page: ' + repr(parts['page']))

        # Pull extensions from the template's real file name.
        parts['ext'] = os.path.splitext(self.template.filename)[1]
        if parts['ext']:
            parts['ext'] = parts['ext'][1:] # remove leading dot
        # Deprecated
        parts['type'] = parts['ext']
        self.meta['ext'] = parts['ext']

        if parts['page'] == 1:
            parts['page'] = ''

        if 'url' in self.meta:
            logging.debug('Using page url pattern')
            self.url_pattern = self.meta['url']
        else:
            logging.debug('Using global url pattern')
            self.url_pattern = self.options['url_pattern']

        self.meta['url'] = self.url_pattern.format(**parts)

        logging.info('URL pattern is: {0}'.format(self.url_pattern))
        logging.info('URL parts are: {0}'.format(parts))

        # Get rid of extra slashes
        self.meta['url'] = re.sub(r'//+', '/', self.meta['url'])

        # If we have been asked to, rip out any plain "index.html"s
        if not self.options['url_include_index']:
            self.meta['url'] = re.sub(r'/index\.html$', '/', self.meta['url'])

        # To be used for writing page content
        self.meta['path'] = self.meta['url']
        # If site is going to be in a subdirectory
        if self.options.get('url_subdir'):
            self.meta['url'] = self.options['url_subdir'] + self.meta['url']

        # Some urls should start with /, some should not.
        if self.options['relative_urls'] and self.meta['url'][0] == '/':
            self.meta['url'] = self.meta['url'][1:]
        if not self.options['relative_urls'] and self.meta['url'][0] != '/':
            self.meta['url'] = '/' + self.meta['url']

        logging.debug('url is: ' + self.meta['url'])

        # subpages
        self.meta['subpages'] = []

        self.engine.run_hook('page.meta.post', self)

    def render(self, templ_vars=None):
        """
        Renders the page with the template engine.
        """
        logging.debug('Rendering ' + self.meta['slug'])
        if not templ_vars:
            templ_vars = {}

        # Handle pagination if we needed.
        if 'pagination' in self.meta and 'list' in self.meta['pagination']:
            extra_pages = self.paginate(templ_vars)
        else:
            extra_pages = []

        # Don't clobber possible values in the template variables.
        if 'page' in templ_vars:
            logging.debug('Found defaulted page data.')
            templ_vars['page'].update(self.meta)
        else:
            templ_vars['page'] = self.meta

        # Don't clobber pagination either.
        if 'pagination' in templ_vars:
            templ_vars['pagination'].update(self.meta['pagination'])
        else:
            templ_vars['pagination'] = self.meta['pagination']

        # ... and actions! (and logging, and hooking)
        self.engine.run_hook('page.template.pre', self, templ_vars)
        logging.debug('templ_vars.keys(): ' + repr(templ_vars.keys()))
        self.rendered = self.template.render(templ_vars)
        logging.debug('extra pages is: ' + repr(extra_pages))
        self.engine.run_hook('page.template.post', self)

        return extra_pages

    def paginate(self, templ_vars):
        extra_pages = []
        logging.debug('called pagination for {0}'.format(self.meta['slug']))
        if 'page_items' not in self.meta['pagination']:
            logging.debug('doing pagination for {0}'.format(self.meta['slug']))
            # This is the first page of a set of pages. Set up the rest. Other
            # wise don't do anything.

            source_spec = self.meta['pagination']['list'].split('.')
            logging.debug('pagination source is: ' + repr(source_spec))

            if source_spec[0] == 'page':
                source = self.meta
                source_spec.pop(0)
            elif source_spec[0] == 'site':
                source = templ_vars['site']
                source_spec.pop(0)
            else:
                logging.error('Unknown pagination source! Not paginating')
                return

            for k in source_spec:
                source = source[k]

            sort_key = self.meta['pagination'].get('sort_key', None)
            sort_reverse = self.meta['pagination'].get('sort_reverse', False)

            logging.debug('sort_key: {0}, sort_reverse: {1}'.format(
                sort_key, sort_reverse))

            if not source:
                return extra_pages
            if isinstance(source[0], Page):
                source = [p.meta for p in source]

            if sort_key is not None:
                if isinstance(source[0], dict):
                    source.sort(key=lambda x: x[sort_key],
                            reverse=sort_reverse)
                else:
                    source.sort(key=lambda x: x.__getattribute__(sort_key),
                            reverse=sort_reverse)

            chunks = list(util.chunk(source, self.meta['pagination']['limit']))
            if not chunks:
                return extra_pages

            # Make a page for each chunk
            for idx, chunk in enumerate(chunks[1:], 2):
                new_meta = copy.deepcopy(self.meta)
                new_meta.update({
                    'url': self.url_pattern,
                    'pagination': {
                        'page_items': chunk,
                        'num_pages': len(chunks),
                        'cur_page': idx,
                    }
                })
                new_page = self.from_meta(new_meta, self.options, self.engine,
                    renderer=self.renderer)
                logging.debug('page {0} is {1}'.format(idx, new_page))
                if new_page:
                    extra_pages.append(new_page)

            # Set up the next/previous page links
            for idx, page in enumerate(extra_pages):
                if idx == 0:
                    page.meta['pagination']['prev_page'] = self.meta
                else:
                    page.meta['pagination']['prev_page'] = extra_pages[idx-1].meta

                if idx < len(extra_pages) - 1:
                    page.meta['pagination']['next_page'] = extra_pages[idx+1].meta
                else:
                    page.meta['pagination']['next_page'] = None

            # Pagination date for this page
            self.meta['pagination'].update({
                'page_items': chunks[0],
                'num_pages': len(chunks),
                'cur_page': 1,
            })
            # Extra pages doesn't include the first page, so if there is at
            # least one, then make a link to the next page.
            if len(extra_pages) > 0:
                self.meta['pagination']['next_page'] = extra_pages[0].meta

        return extra_pages

    def write(self):
        """Write the page to a rendered file on disk."""

        # Use what we are passed, or the default given, or the current dir
        base_path = self.options.get('output_dir', '.')
        path = self.meta['path']
        if path and path[0] == '/':
            path = path[1:]
        base_path = os.path.join(base_path, path)
        if base_path.endswith('/'):
            base_path += 'index.' + self.meta['ext']

        try:
            os.makedirs(os.path.dirname(base_path))
        except OSError as e:
            logging.debug('makedirs failed for {0}'.format(
                os.path.basename(base_path)))
            # Probably that the dir already exists, so thats ok.
            # TODO: double check this. Permission errors are something to worry
            # about
        logging.info('writing to {0}'.format(base_path))

        logging.debug('Writing {0} to {1}'.format(self.meta['slug'], base_path))
        f = open(base_path, 'w')
        f.write(self.rendered.encode('utf-8'))
        f.close()

    def __repr__(self):
        return "&lt;wok.page.Page '{0}'&gt;".format(self.meta['slug'])


class Author(object):
    """Smartly manages a author with name and email"""
    parse_author_regex = re.compile(r'^([^<>]*) *(<(.*@.*)>)?$')

    def __init__(self, raw='', name=None, email=None):
        self.raw = raw.strip()
        self.name = name
        self.email = email

    @classmethod
    def parse(cls, raw):
        if isinstance(raw, cls):
            return raw

        a = cls(raw)
        a.name, _, a.email = cls.parse_author_regex.match(raw).groups()
        if a.name:
            a.name = a.name.strip()
        if a.email:
            a.email = a.email.strip()
        return a

    def __str__(self):
        if not self.name:
            return self.raw
        if not self.email:
            return self.name

        return "{0} <{1}>".format(self.name, self.email)

    def __repr__(self):
        return '<wok.page.Author "{0} <{1}>">'.format(self.name, self.email)

    def __unicode__(self):
        s = self.__str__()
        return s.replace('<', '&lt;').replace('>', '&gt;')

class BadMetaException(Exception):
    pass

########NEW FILE########
__FILENAME__ = renderers
import logging
from wok import util

# Check for pygments
try:
    import pygments
    have_pygments = True
except ImportError:
    logging.warn('Pygments not enabled.')
    have_pygments = False

# List of available renderers
all = []

class Renderer(object):
    extensions = []

    @classmethod
    def render(cls, plain):
        return plain
all.append(Renderer)

class Plain(Renderer):
    """Plain text renderer. Replaces new lines with html </br>s"""
    extensions = ['txt']

    @classmethod
    def render(cls, plain):
        return plain.replace('\n', '<br>')
all.append(Plain)

# Include markdown, if it is available.
try:
    from markdown import markdown

    class Markdown(Renderer):
        """Markdown renderer."""
        extensions = ['markdown', 'mkd', 'md']

        plugins = ['def_list', 'footnotes']
        if have_pygments:
            plugins.extend(['codehilite(css_class=codehilite)', 'fenced_code'])

        @classmethod
        def render(cls, plain):
            return markdown(plain, cls.plugins)

    all.append(Markdown)

except ImportError:
    logging.warn("markdown isn't available, trying markdown2")
    markdown = None

# Try Markdown2
if markdown is None:
    try:
        import markdown2
        class Markdown2(Renderer):
            """Markdown2 renderer."""
            extensions = ['markdown', 'mkd', 'md']

            extras = ['def_list', 'footnotes']
            if have_pygments:
                extras.append('fenced-code-blocks')

            @classmethod
            def render(cls, plain):
                return markdown2.markdown(plain, extras=cls.extras)

        all.append(Markdown2)
    except ImportError:
        logging.warn('Markdown not enabled.')


# Include ReStructuredText Parser, if we have docutils
try:
    import docutils.core
    from docutils.writers.html4css1 import Writer as rst_html_writer
    from docutils.parsers.rst import directives

    if have_pygments:
        from wok.rst_pygments import Pygments as RST_Pygments
        directives.register_directive('Pygments', RST_Pygments)

    class ReStructuredText(Renderer):
        """reStructuredText renderer."""
        extensions = ['rst']

        @classmethod
        def render(cls, plain):
            w = rst_html_writer()
            return docutils.core.publish_parts(plain, writer=w)['body']

    all.append(ReStructuredText)
except ImportError:
    logging.warn('reStructuredText not enabled.')


# Try Textile
try:
    import textile
    class Textile(Renderer):
        """Textile renderer."""
        extensions = ['textile']

        @classmethod
        def render(cls, plain):
            return textile.textile(plain)

    all.append(Textile)
except ImportError:
    logging.warn('Textile not enabled.')


if len(all) <= 2:
    logging.error("You probably want to install either a Markdown library (one of "
          "'Markdown', or 'markdown2'), 'docutils' (for reStructuredText), or "
          "'textile'. Otherwise only plain text input will be supported.  You "
          "can install any of these with 'sudo pip install PACKAGE'.")

########NEW FILE########
__FILENAME__ = rst_pygments
# -*- coding: utf-8 -*-
"""
    The Pygments reStructuredText directive
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This fragment is a Docutils_ 0.5 directive that renders source code
    (to HTML only, currently) via Pygments.

    To use it, adjust the options below and copy the code into a module
    that you import on initialization.  The code then automatically
    registers a ``sourcecode`` directive that you can use instead of
    normal code blocks like this::

        .. sourcecode:: python

            My code goes here.

    If you want to have different code styles, e.g. one with line numbers
    and one without, add formatters with their names in the VARIANTS dict
    below.  You can invoke them instead of the DEFAULT one by using a
    directive option::

        .. sourcecode:: python
            :linenos:

            My code goes here.

    Look at the `directive documentation`_ to get all the gory details.

    .. _Docutils: http://docutils.sf.net/
    .. _directive documentation:
       http://docutils.sourceforge.net/docs/howto/rst-directives.html

    :copyright: Copyright 2006-2010 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Options
# ~~~~~~~

# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False

from pygments.formatters import HtmlFormatter

# The default formatter
DEFAULT = HtmlFormatter(noclasses=INLINESTYLES)

# Add name -> formatter pairs for every variant you want to use
VARIANTS = {
    'linenos': HtmlFormatter(noclasses=INLINESTYLES, linenos=True),
}


from docutils import nodes
from docutils.parsers.rst import directives, Directive

from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer

class Pygments(Directive):
    """ Source code syntax hightlighting.
    """
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = dict([(key, directives.flag) for key in VARIANTS])
    has_content = True

    def run(self):
        self.assert_has_content()
        try:
            lexer = get_lexer_by_name(self.arguments[0])
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()
        # take an arbitrary option if more than one is given
        formatter = self.options and VARIANTS[self.options.keys()[0]] or DEFAULT
        parsed = highlight(u'\n'.join(self.content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]

directives.register_directive('sourcecode', Pygments)


########NEW FILE########
__FILENAME__ = test_page
try:
    from twisted.trial.unittest import TestCase
except ImportError:
    from unittest import TestCase

from wok.page import Author

class TestAuthor(TestCase):

    def test_author(self):
        a = Author.parse('Bob Smith')
        self.assertEqual(a.raw, 'Bob Smith')
        self.assertEqual(a.name, 'Bob Smith')

        a = Author.parse('Bob Smith <bob@here.com>')
        self.assertEqual(a.raw, 'Bob Smith <bob@here.com>')
        self.assertEqual(a.name, 'Bob Smith')
        self.assertEqual(a.email, 'bob@here.com')

        a = Author.parse('<bob@here.com>')
        self.assertEqual(a.raw, '<bob@here.com>')
        self.assertEqual(a.email, 'bob@here.com')

########NEW FILE########
__FILENAME__ = test_util
try:
    from twisted.trial.unittest import TestCase
except ImportError:
    from unittest import TestCase

from datetime import date, time, datetime, tzinfo

from wok import util

class TestDatetimes(TestCase):

    def setUp(self):
        """
        The date used is February 3rd, 2011 at 00:23 in the morning.

        The datetime is the first commit of wok.
        The date is the day this test was first written.
        The time is pi second.
        """
        self.datetime = datetime(2011, 2, 3, 0, 23, 0, 0)
        self.date = date(2011, 10, 12)
        self.time = time(3, 14, 15, 0)

    def test_blanks(self):
        inp = {}
        out = {
            'datetime': None,
            'date': None,
            'time': None,
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_just_date(self):
        inp = {'date': self.date}
        out = {
            'datetime': datetime(2011, 10, 12, 0, 0, 0, 0),
            'date': self.date,
            'time': None,
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_just_time(self):
        t = self.time # otherwise the datetime line gets awful
        inp = {'time': t}
        out = {
            'datetime': None,
            'date': None,
            'time': t,
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_date_and_times(self):
        inp = {'date': self.date, 'time': self.time}
        out = {
            'datetime': datetime(2011, 10, 12, 3, 14, 15, 0),
            'date': self.date,
            'time': self.time,
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_just_datetime(self):
        inp = {'datetime': self.datetime}
        out = {
            'datetime': self.datetime,
            'date': self.datetime.date(),
            'time': self.datetime.time(),
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_datetime_and_date(self):
        inp = {'datetime': self.datetime, 'date': self.date}
        out = {
           'datetime': datetime(2011, 10, 12, 0, 23, 0, 0),
           'date': self.date,
           'time': self.datetime.time(),
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_datetime_and_time(self):
        inp = {'datetime': self.datetime, 'time': self.time}
        out = {
            'datetime': datetime(2011, 2, 3, 3, 14, 15, 0),
            'date': self.datetime.date(),
            'time': self.time,
         }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_all(self):
        inp = {'datetime': self.datetime, 'date': self.date, 'time': self.time}
        out = {
            'datetime': datetime(2011, 10, 12, 3, 14, 15, 0),
            'date': self.date,
            'time': self.time,
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

    def test_types(self):
        """
        YAML doesn't always give us the types we want. Handle that correctly.
        """
        # Yaml will only make something a datetime if it also includes a time.
        inp = {'datetime': date(2011, 12, 25)}
        out = {
            'datetime': datetime(2011, 12, 25),
            'date': date(2011, 12, 25),
            'time': None,
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

        # Yaml likes to give times as the number of seconds.
        inp = {'date': self.date, 'time': 43200}
        out = {
            'datetime': datetime(2011, 10, 12, 12, 0, 0),
            'date': self.date,
            'time': time(12, 0, 0),
        }

        util.date_and_times(inp)
        self.assertEquals(inp, out)

########NEW FILE########
__FILENAME__ = util
import re
from unicodedata import normalize
from datetime import date, time, datetime, timedelta

def chunk(li, n):
    """Yield succesive n-size chunks from l."""
    for i in xrange(0, len(li), n):
        yield li[i:i+n]

def date_and_times(meta):

    date_part = None
    time_part = None

    if 'date' in meta:
        date_part = meta['date']

    if 'time' in meta:
        time_part = meta['time']

    if 'datetime' in meta:
        if date_part is None:
            if isinstance(meta['datetime'], datetime):
                date_part = meta['datetime'].date()
            elif isinstance(meta['datetime'], date):
                date_part = meta['datetime']

        if time_part is None and isinstance(meta['datetime'], datetime):
            time_part = meta['datetime'].time()

    if isinstance(time_part, int):
        seconds = time_part % 60
        minutes = (time_part / 60) % 60
        hours = (time_part / 3600)

        time_part = time(hours, minutes, seconds)

    meta['date'] = date_part
    meta['time'] = time_part

    if date_part is not None and time_part is not None:
        meta['datetime'] = datetime(date_part.year, date_part.month,
                date_part.day, time_part.hour, time_part.minute,
                time_part.second, time_part.microsecond, time_part.tzinfo)
    elif date_part is not None:
        meta['datetime'] = datetime(date_part.year, date_part.month, date_part.day)
    else:
        meta['datetime'] = None

########NEW FILE########
