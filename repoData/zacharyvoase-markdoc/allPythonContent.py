__FILENAME__ = builder
# -*- coding: utf-8 -*-

import os
import os.path as p
import operator
import re

from markdoc.cache import DocumentCache, RenderCache, read_from
from markdoc.config import Config
from markdoc.render import make_relative


Config.register_default('listing-filename', '_list.html')


class Builder(object):
    
    """An object to handle all the parts of the wiki building process."""
    
    def __init__(self, config):
        self.config = config
        
        self.doc_cache = DocumentCache(base=self.config.wiki_dir)
        
        def render_func(path, doc):
            level = len(path.lstrip('/').split('/')) - 1
            return self.config.markdown(curr_path=path).convert(doc)
        self.render_cache = RenderCache(render_func, self.doc_cache)
        
        render_doc_func = lambda path, doc: self.render_document(path, cache=False)
        self.document_render_cache = RenderCache(render_doc_func, self.render_cache)
    
    def crumbs(self, path):
        
        """
        Produce a breadcrumbs list for the given filename.
        
        The crumbs are calculated based on the wiki root and the absolute path
        to the current file.
        
        Examples
        --------
        
        Assuming a wiki root of `/a/b/c`:
        
        * `a/b/c/wiki/index.md` => `[('index', None)]`
        
        * `a/b/c/wiki/subdir/index.md` =>
          `[('index', '/'), ('subdir', None)]`
        
        * `a/b/c/wiki/subdir/file.md` =>
          `[('index', '/'), ('subdir', '/subdir/'), ('file', None)]
        
        """
        
        if p.isabs(path):
            path = self.doc_cache.relative(path)
        
        rel_components = path.split(p.sep)
        terminus = p.splitext(rel_components.pop())[0]
        
        if not rel_components:
            if terminus == 'index':
                return [('index', None)]
            return [('index', '/'), (terminus, None)]
        elif terminus == 'index':
            terminus = p.splitext(rel_components.pop())[0]
        
        crumbs = [('index', '/')]
        for component in rel_components:
            path = '%s%s/' % (crumbs[-1][1], component)
            crumbs.append((component, path))
        
        crumbs.append((terminus, None))
        return crumbs
    
    def walk(self):
        
        """
        Walk through the wiki, yielding info for each document.
        
        For each document encountered, a `(filename, crumbs)` tuple will be
        yielded.
        """
        
        if not self.config['document-extensions']:
            self.config['document-extensions'].append('')
        
        def valid_extension(filename):
            return any(filename.endswith(valid_ext)
                       for valid_ext in self.config['document-extensions'])
        
        for dirpath, subdirs, files in os.walk(self.config.wiki_dir):
            remove_hidden(subdirs); subdirs.sort()
            remove_hidden(files); files.sort()
            
            for filename in filter(valid_extension, files):
                full_filename = p.join(dirpath, filename)
                yield p.relpath(full_filename, start=self.config.wiki_dir)
    
    def listing_context(self, directory):
        
        """
        Generate the template context for a directory listing.
        
        This method accepts a relative path, with the base assumed to be the
        HTML root. This means listings must be generated after the wiki is
        built, allowing them to list static media too. 
        
        Directories should always be '/'-delimited when specified, since it is
        assumed that they are URL paths, not filesystem paths.
        
        For information on what the produced context will look like, consult the
        `listing` doctest.
        """
        
        # Ensure the directory name ends with '/'. 
        directory = directory.strip('/')
        
        # Resolve to filesystem paths.
        fs_rel_dir = p.sep.join(directory.split('/'))
        fs_abs_dir = p.join(self.config.html_dir, fs_rel_dir)
        skip_files = set([self.config['listing-filename'], 'index.html'])
        
        sub_directories, pages, files = [], [], []
        for basename in os.listdir(fs_abs_dir):
            fs_abs_path = p.join(fs_abs_dir, basename)
            file_dict = {
                'basename': basename,
                'href': directory + '/' + basename}
            if not file_dict['href'].startswith('/'):
                file_dict['href'] = '/' + file_dict['href']
            
            if p.isdir(fs_abs_path):
                file_dict['href'] += '/'
                sub_directories.append(file_dict)
            
            else:
                if (basename in skip_files or basename.startswith('.') or
                    basename.startswith('_')):
                    continue
                
                file_dict['slug'] = p.splitext(basename)[0]
                file_dict['size'] = p.getsize(fs_abs_path)
                file_dict['humansize'] = humansize(file_dict['size'])
                
                if p.splitext(basename)[1] == (p.extsep + 'html'):
                    # Get the title from the file.
                    contents = read_from(fs_abs_path)
                    file_dict['title'] = get_title(file_dict['slug'], contents)
                    # Remove .html from the end of the href.
                    file_dict['href'] = p.splitext(file_dict['href'])[0]
                    pages.append(file_dict)
                else:
                    files.append(file_dict)
        
        sub_directories.sort(key=lambda directory: directory['basename'])
        pages.sort(key=lambda page: page['title'])
        files.sort(key=lambda file_: file_['basename'])
        
        return {
            'directory': directory,
            'sub_directories': sub_directories,
            'pages': pages,
            'files': files,
            'make_relative': lambda href: make_relative(directory, href),
        }
    
    def render(self, path, cache=True):
        return self.render_cache.render(path, cache=cache)
    
    def title(self, path, cache=True):
        return get_title(path, self.render(path, cache=cache))
    
    def render_document(self, path, cache=True):
        if cache:
            return self.document_render_cache.render(path)
        
        context = {}
        context['content'] = self.render(path)
        context['title'] = self.title(path)
        context['crumbs'] = self.crumbs(path)
        context['make_relative'] = lambda href: make_relative(path, href)
        
        template = self.config.template_env.get_template('document.html')
        return template.render(context)
    
    def render_listing(self, path):
        import jinja2
        
        context = self.listing_context(path)
        
        crumbs = [('index', '/')]
        if path not in ['', '/']:
            current_dir = ''
            for component in path.strip('/').split('/'):
                crumbs.append((component, '%s/%s/' % (current_dir, component)))
                current_dir += '/' + component
        crumbs.append((jinja2.Markup('<span class="list-crumb">list</span>'), None))
        
        context['crumbs'] = crumbs
        context['make_relative'] = lambda href: make_relative(path + '/', href)
        
        template = self.config.template_env.get_template('listing.html')
        return template.render(context)


def remove_hidden(names):
    """Remove (in-place) all strings starting with a '.' in the given list."""
    
    i = 0
    while i < len(names):
        if names[i].startswith('.'):
            names.pop(i)
        else:
            i += 1
    return names


def get_title(filename, data):
    """Try to retrieve a title from a filename and its contents."""
    
    match = re.search(r'<!-- ?title:(.+)-->', data, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    match = re.search(r'<h1[^>]*>([^<]+)</h1>', data, re.IGNORECASE)
    if match:
        return match.group(1)
    
    name, extension = p.splitext(p.basename(filename))
    return re.sub(r'[-_]+', ' ', name).title()


def humansize(size, base=1024):
    import decimal
    import math
    
    if size == 0:
        return '0B'
    
    i = int(math.log(size, base))
    prefix = 'BKMGTPEZY'[i]
    number = decimal.Decimal(size) / (base ** i)
    return str(number.to_integral()) + prefix

########NEW FILE########
__FILENAME__ = cache
# -*- coding: utf-8 -*-

import codecs
from functools import wraps
import os
import os.path as p
import time


class DocumentCache(object):
    
    """
    A high-level document cache for caching the content of files.
    
    This is a read-only cache which uses the OS-reported modification timestamps
    for files (via `os.stat()`) to determine cache dirtiness, and then refreshes
    its cache behind the scenes when files are requested.
    
    You can access values via `.get()` (which supports several options) or via
    simple subscription syntax (i.e. `cache[path]`). The cache is configured
    with a 'root' on instantiation, by which all relative paths are resolved.
    """
    
    def __init__(self, base=None, cache=None, encoding='utf-8'):
        if cache is None:
            cache = {}
        self.cache = cache
        
        if base is None:
            base = os.getcwd()
        self.base = base
        
        self.encoding = encoding
    
    absolute = lambda self, relpath: p.join(self.base, relpath)
    relative = lambda self, abspath: p.relpath(abspath, start=self.base)
    
    def has_latest_version(self, path):
        """Determine whether the cache for a path is up to date."""
        
        # No-op for already-absolute paths.
        path = self.absolute(path)
        if path not in self.cache:
            return False
        cached_mtime = self.cache[path][0]
        return os.stat(path).st_mtime <= cached_mtime
    
    def refresh_cache(self, path, encoding=None):
        """Refresh the cache, no matter what, with an optional encoding."""
        
        path = self.absolute(path)
        encoding = encoding or self.encoding
        data = read_from(path, encoding=encoding)
        mtime = os.stat(path).st_mtime
        self.cache[path] = (mtime, data)
    
    def update_to_latest_version(self, path):
        """If necessary, refresh the cache's copy of a file."""
        
        if not self.has_latest_version(path):
            self.refresh_cache(path)
    
    def get(self, path, cache=True, encoding=None):
        """Retrieve the data for a given path, optionally using the cache."""
        
        path = self.absolute(path)
        
        if cache:
            self.update_to_latest_version(path)
            return self.cache[path][1] # (mtime, data)[1]
        
        if not p.isfile(path):
            return None
        
        if encoding is None:
            encoding = self.encoding
        return read_from(path, encoding=encoding)
    
    def __getitem__(self, path):
        result = self.get(path)
        if result is None:
            raise KeyError(path)
        return result


class RenderCache(object):
    
    def __init__(self, render_func, document_cache):
        self.render_func = render_func
        self.doc_cache = document_cache
        # The two-cache structure allows us to garbage collect rendered results
        # for old versions of documents.
        # pathname => document hash
        self.hash_cache = {}
        # document hash => rendered results
        self.result_cache = {}
    
    def render(self, path, cache=True):
        """Render the contents of a filename, optionally using the cache."""
        
        document = self.doc_cache.get(path, cache=cache)
        
        if cache:
            doc_hash = (hash(path), hash(document))
            if path in self.hash_cache and self.hash_cache[path] != doc_hash:
                self.result_cache.pop(self.hash_cache[path], None)
                self.hash_cache[path] = doc_hash
            
            if doc_hash not in self.result_cache:
                self.result_cache[doc_hash] = self.render_func(path, document)
            return self.result_cache[doc_hash]
        else:
            return self.render_func(document)
    
    get = render # For compatibility with the document cache.


def read_from(filename, encoding='utf-8'):
    """Read data from a filename, optionally with an encoding."""
    
    if encoding is None:
        fp = open(filename)
    else:
        fp = codecs.open(filename, encoding=encoding)
    
    try:
        return fp.read()
    finally:
        fp.close()

########NEW FILE########
__FILENAME__ = commands
# -*- coding: utf-8 -*-

import codecs
from functools import wraps
import logging
import os
import os.path as p
import pprint
import re
import shutil
import subprocess
import sys

import markdoc
from markdoc.builder import Builder
from markdoc.cli.parser import subparsers


def command(function):
    """Decorator/wrapper to declare a function as a Markdoc CLI task."""
    
    cmd_name = function.__name__.replace('_', '-')
    help = (function.__doc__ or '').rstrip('.') or None
    parser = subparsers.add_parser(cmd_name, help=help)
    
    @wraps(function)
    def wrapper(config, args):
        logging.getLogger('markdoc').debug('Running markdoc.%s' % cmd_name)
        return function(config, args)
    wrapper.parser = parser
    
    return wrapper


## Utilities

@command
def show_config(config, args):
    """Pretty-print the current Markdoc configuration."""
    
    pprint.pprint(config)


@command
def init(_, args):
    """Initialize a new Markdoc repository."""
    
    log = logging.getLogger('markdoc.init')
    
    if not args.destination:
        log.info('No destination specified; using current directory')
        destination = os.getcwd()
    else:
        destination = p.abspath(args.destination)
    
    if p.exists(destination) and os.listdir(destination):
        init.parser.error("destination isn't empty")
    elif not p.exists(destination):
        log.debug('makedirs %s' % destination)
        os.makedirs(destination)
    elif not p.isdir(destination):
        init.parser.error("destination isn't a directory")
    
    log.debug('mkdir %s/.templates/' % destination)
    os.makedirs(p.join(destination, '.templates'))
    log.debug('mkdir %s/static/' % destination)
    os.makedirs(p.join(destination, 'static'))
    log.debug('mkdir %s/wiki/' % destination)
    os.makedirs(p.join(destination, 'wiki'))
    
    log.debug('Creating markdoc.yaml file')
    config_filename = p.join(destination, 'markdoc.yaml')
    fp = open(config_filename, 'w')
    try:
        fp.write('{}\n')
    finally:
        fp.close()
    
    if args.vcs_ignore:
        config = markdoc.config.Config.for_directory(destination)
        args = vcs_ignore.parser.parse_args([args.vcs_ignore])
        vcs_ignore(config, args)
    
    log.info('Wiki initialization complete')
    log.info('Your new wiki is at: %s' % destination)

init.parser.add_argument('destination', default=None,
    help="Create wiki here (if omitted, defaults to current directory)")
init.parser.add_argument('--vcs-ignore', choices=['hg', 'git', 'cvs', 'bzr'],
    help="Create an ignore file for the specified VCS.")


@command
def vcs_ignore(config, args):
    """Create a VCS ignore file for a wiki."""
    
    log = logging.getLogger('markdoc.vcs-ignore')
    log.debug('Creating ignore file for %s' % args.vcs)
    wiki_root = config['meta.root'] # shorter local alias.
    
    ignore_file_lines = []
    ignore_file_lines.append(p.relpath(config.html_dir, start=wiki_root))
    ignore_file_lines.append(p.relpath(config.temp_dir, start=wiki_root))
    if args.vcs == 'hg':
        ignore_file_lines.insert(0, 'syntax: glob')
        ignore_file_lines.insert(1, '')
    
    if args.output == '-':
        log.debug('Writing ignore file to stdout')
        fp = sys.stdout
    else:
        if not args.output:
            filename = p.join(wiki_root, '.%signore' % args.vcs)
        else:
            filename = p.join(wiki_root, args.output)
        log.info('Writing ignore file to %s' % p.relpath(filename, start=wiki_root))
        fp = open(filename, 'w')
    
    try:
        fp.write('\n'.join(ignore_file_lines) + '\n')
    finally:
        if fp is not sys.stdout:
            fp.close()
    
    log.debug('Ignore file written.')

vcs_ignore.parser.add_argument('vcs', default='hg', nargs='?',
    choices=['hg', 'git', 'cvs', 'bzr'],
    help="Create ignore file for specified VCS (default 'hg')")
vcs_ignore.parser.add_argument('-o', '--output', default=None, metavar='FILENAME',
    help="Write output to the specified filename, relative to the wiki root. "
         "Default is to generate the filename from the VCS. "
         "'-' will write to stdout.")


## Cleanup

@command
def clean_html(config, args):
    """Clean built HTML from the HTML root."""
    
    log = logging.getLogger('markdoc.clean-html')
    
    if p.exists(config.html_dir):
        log.debug('rm -Rf %s' % config.html_dir)
        shutil.rmtree(config.html_dir)
    
    log.debug('makedirs %s' % config.html_dir)
    os.makedirs(config.html_dir)


@command
def clean_temp(config, args):
    """Clean built HTML from the temporary directory."""
    
    log = logging.getLogger('markdoc.clean-temp')
    
    if p.exists(config.temp_dir):
        log.debug('rm -Rf %s' % config.temp_dir)
        shutil.rmtree(config.temp_dir)
    
    log.debug('makedirs %s' % config.temp_dir)
    os.makedirs(config.temp_dir)


## Synchronization

@command
def sync_static(config, args):
    """Sync static files into the HTML root."""
    
    log = logging.getLogger('markdoc.sync-static')
    
    if not p.exists(config.html_dir):
        log.debug('makedirs %s' % config.html_dir)
        os.makedirs(config.html_dir)
    
    command = ('rsync -vaxq --cvs-exclude --ignore-errors --include=.htaccess --exclude=.* --exclude=_*').split()
    display_cmd = command[:]
    
    if config['use-default-static']:
        # rsync needs the paths to have trailing slashes to work correctly.
        command.append(p.join(markdoc.default_static_dir, ''))
        display_cmd.append(p.basename(markdoc.default_static_dir) + '/')
    
    if not config['cvs-exclude']:
        command.remove('--cvs-exclude')
        display_cmd.remove('--cvs-exclude')
    
    if p.isdir(config.static_dir):
        command.append(p.join(config.static_dir, ''))
        display_cmd.append(p.basename(config.static_dir) + '/')
    
    command.append(p.join(config.html_dir, ''))
    display_cmd.append(p.basename(config.html_dir) + '/')
    
    log.debug(subprocess.list2cmdline(display_cmd))
    
    subprocess.check_call(command)
    
    log.debug('rsync completed')


@command
def sync_html(config, args):
    """Sync built HTML and static media into the HTML root."""
    
    log = logging.getLogger('markdoc.sync-html')
    
    if not p.exists(config.html_dir):
        log.debug('makedirs %s' % config.html_dir)
        os.makedirs(config.html_dir)
    
    command = ('rsync -vaxq --cvs-exclude --delete --ignore-errors --include=.htaccess --exclude=.* --exclude=_*').split()
    display_cmd = command[:]
    
    # rsync needs the paths to have trailing slashes to work correctly.
    command.append(p.join(config.temp_dir, ''))
    display_cmd.append(p.basename(config.temp_dir) + '/')
    
    if config['use-default-static']:
        command.append(p.join(markdoc.default_static_dir, ''))
        display_cmd.append(p.basename(markdoc.default_static_dir) + '/')
    
    if not config['cvs-exclude']:
        command.remove('--cvs-exclude')
        display_cmd.remove('--cvs-exclude')
    
    if p.isdir(config.static_dir):
        command.append(p.join(config.static_dir, ''))
        display_cmd.append(p.basename(config.static_dir) + '/')
    
    command.append(p.join(config.html_dir, ''))
    display_cmd.append(p.basename(config.html_dir) + '/')
    
    log.debug(subprocess.list2cmdline(display_cmd))
    
    subprocess.check_call(command)
    
    log.debug('rsync completed')


## Building

@command
def build(config, args):
    """Compile wiki to HTML and sync to the HTML root."""
    
    log = logging.getLogger('markdoc.build')
    
    clean_temp(config, args)
    
    builder = Builder(config)
    for rel_filename in builder.walk():
        html = builder.render_document(rel_filename)
        out_filename = p.join(config.temp_dir,
            p.splitext(rel_filename)[0] + p.extsep + 'html')
        
        if not p.exists(p.dirname(out_filename)):
            log.debug('makedirs %s' % p.dirname(out_filename))
            os.makedirs(p.dirname(out_filename))
        
        log.debug('Creating %s' % p.relpath(out_filename, start=config.temp_dir))
        fp = codecs.open(out_filename, 'w', encoding='utf-8')
        try:
            fp.write(html)
        finally:
            fp.close()
    
    sync_html(config, args)
    build_listing(config, args)


@command
def build_listing(config, args):
    """Create listings for all directories in the HTML root (post-build)."""
    
    log = logging.getLogger('markdoc.build-listing')
    
    list_basename = config['listing-filename']
    builder = Builder(config)
    generate_listing = config.get('generate-listing', 'always').lower()
    always_list = True
    if generate_listing == 'never':
        log.debug("No listing generated (generate-listing == never)")
        return # No need to continue.
    
    for fs_dir, _, _ in os.walk(config.html_dir):
        index_file_exists = any([
            p.exists(p.join(fs_dir, 'index.html')),
            p.exists(p.join(fs_dir, 'index'))])
        
        directory = '/' + '/'.join(p.relpath(fs_dir, start=config.html_dir).split(p.sep))
        if directory == '/' + p.curdir:
            directory = '/'
        
        if (generate_listing == 'sometimes') and index_file_exists:
            log.debug("No listing generated for %s" % directory)
            continue
        
        log.debug("Generating listing for %s" % directory)
        listing = builder.render_listing(directory)
        list_filename = p.join(fs_dir, list_basename)
        
        fp = codecs.open(list_filename, 'w', encoding='utf-8')
        try:
            fp.write(listing)
        finally:
            fp.close()
        
        if not index_file_exists:
            log.debug("cp %s/%s %s/%s" % (directory, list_basename, directory, 'index.html'))
            shutil.copyfile(list_filename, p.join(fs_dir, 'index.html'))


## Serving

IPV4_RE = re.compile(r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}$')

@command
def serve(config, args):
    """Serve the built HTML from the HTML root."""
    
    # This should be a lazy import, otherwise it'll slow down the whole CLI.
    from markdoc.wsgi import MarkdocWSGIApplication
    
    log = logging.getLogger('markdoc.serve')
    app = MarkdocWSGIApplication(config)
    
    config['server.port'] = args.port
    config['server.num-threads'] = args.num_threads
    if args.server_name:
        config['server.name'] = args.server_name
    config['server.request-queue-size'] = args.queue_size
    config['server.timeout'] = args.timeout
    if args.interface:
        if not IPV4_RE.match(args.interface):
            serve.parser.error('invalid interface specifier: %r' % args.interface)
        config['server.bind'] = args.interface
    
    server = config.server_maker()(app)
    
    try:
        log.info('Serving on http://%s:%d' % server.bind_addr)
        server.start()
    except KeyboardInterrupt:
        log.debug('Interrupted')
    finally:
        log.info('Shutting down gracefully')
        server.stop()

serve.parser.add_argument('-p', '--port', type=int, default=8008,
    help="Listen on specified port (default is 8008)")
serve.parser.add_argument('-i', '--interface', default=None,
    help="Bind to specified interface (defaults to loopback only)")
serve.parser.add_argument('-t', '--num-threads', type=int, default=10, metavar='N',
    help="Use N threads to handle requests (default is 10)")
serve.parser.add_argument('-n', '--server-name', default=None, metavar='NAME',
    help="Use an explicit server name (default to an autodetected value)")
serve.parser.add_argument('-q', '--queue-size', type=int, default=5, metavar='SIZE',
    help="Set request queue size (default is 5)")
serve.parser.add_argument('--timeout', type=int, default=10,
    help="Set the socket timeout for connections (default is 10)")


########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

import logging
import os
import argparse

from markdoc.cli import commands
from markdoc.cli.parser import parser
from markdoc.config import Config, ConfigNotFound


def main(cmd_args=None):
    """The main entry point for running the Markdoc CLI."""
    
    if cmd_args is not None:
        args = parser.parse_args(cmd_args)
    else:
        args = parser.parse_args()
    
    if args.command != 'init':
        try:
            args.config = os.path.abspath(args.config)
            
            if os.path.isdir(args.config):
                config = Config.for_directory(args.config)
            elif os.path.isfile(args.config):
                config = Config.for_file(args.config)
            else:
                raise ConfigNotFound("Couldn't locate Markdoc config.")
        except ConfigNotFound, exc:
            parser.error(str(exc))
    else:
        config = None
    
    logging.getLogger('markdoc').setLevel(getattr(logging, args.log_level))
    
    command = getattr(commands, args.command.replace('-', '_'))
    return command(config, args)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-

import os

import argparse

import markdoc
from markdoc.config import Config


parser = argparse.ArgumentParser(**{
    'prog': 'markdoc',
    'description': 'A lightweight Markdown-based wiki build tool.',
})

parser.add_argument('-v', '--version', action='version',
    version=markdoc.__version__)

config = parser.add_argument('--config', '-c', default=os.getcwd(),
    help="Use the specified Markdoc config (a YAML file or a directory "
         "containing markdoc.yaml)")

log_level = parser.add_argument('--log-level', '-l', metavar='LEVEL',
    default='INFO', choices='DEBUG INFO WARN ERROR'.split(),
    help="Choose a log level from DEBUG, INFO (default), WARN or ERROR")

quiet = parser.add_argument('--quiet', '-q',
    action='store_const', dest='log_level', const='ERROR',
    help="Alias for --log-level ERROR")

verbose = parser.add_argument('--verbose',
    action='store_const', dest='log_level', const='DEBUG',
    help="Alias for --log-level DEBUG")

subparsers = parser.add_subparsers(dest='command', title='commands', metavar='COMMAND')

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-

"""Utilities for working with Markdoc configurations."""

import copy
import os
import os.path as p

import markdown
import yaml

import markdoc.exc


class ConfigNotFound(markdoc.exc.AbortError):
    """The configuration file was not found."""
    pass


class ConfigMeta(type):
    
    def __new__(mcls, name, bases, attrs):
        cls = type.__new__(mcls, name, bases, attrs)
        cls._defaults = {}
        cls._func_defaults = {}
        return cls
    
    def register_default(cls, key, default_value):
        """Register a default value for a given key."""
        
        cls._defaults[key] = default_value
    
    def register_func_default(cls, key, function):
        """Register a callable as a functional default for a key."""
        
        cls._func_defaults[key] = function
    
    def func_default_for(cls, key):
        """Decorator to define a functional default for a given key."""
        
        return lambda function: [cls.register_func_default(key, function),
                                 function][1]


class Config(dict):
    
    """
    A dictionary which represents a single wiki's Markdoc configuration.
    
    When instantiating this dictionary, if you aren't using an actual
    configuration file, just remember to set `config['meta.root']` to the
    wiki root; you can use `None` as the value for config_file. For example:
        
        # With a filename:
        config = Config('filename.yaml', {...})
        
        # Without a filename:
        config = Config(None, {'meta': {'root': '/path/to/wiki/root/'}, ...})
    
    """
    
    __metaclass__ = ConfigMeta
    
    def __init__(self, config_file, config):
        super(Config, self).__init__(flatten(config))
        
        self['meta.config-file'] = config_file
        self['meta.root'] = p.dirname(config_file)
    
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if key in self._defaults:
                self[key] = copy.copy(self._defaults[key])
            elif key in self._func_defaults:
                self[key] = self._func_defaults[key](self, key)
            else:
                raise
            return dict.__getitem__(self, key)
    
    def __delitem__(self, key):
        if (key not in self):
            return # fail silently.
        return dict.__delitem__(self, key)
    
    @classmethod
    def for_directory(cls, directory=None):
        
        """
        Get the configuration from the 'markdoc.yaml' file in a directory.
        
        If you do not specify a directory, this method will use the current
        working directory.
        """
        
        if directory is None:
            directory = os.getcwd()
        
        if p.exists(p.join(directory, 'markdoc.yaml')):
            return cls.for_file(p.join(directory, 'markdoc.yaml'))
        elif p.exists(p.join(directory, '.markdoc.yaml')):
            return cls.for_file(p.join(directory, '.markdoc.yaml'))
        raise ConfigNotFound("A markdoc configuration could not be found.")
    
    @classmethod
    def for_file(cls, filename):
        """Get the configuration from a given YAML file."""
        
        if not p.exists(filename):
            relpath = p.relpath(p.dirname(filename), start=os.getcwd())
            basename = p.basename(filename)
            if relpath == '.':
                raise ConfigNotFound("%s was not found in the current directory" % basename)
            raise ConfigNotFound("%s was not found in %s" % (basename, relpath))
        
        fp = open(filename)
        try:
            config = yaml.load(fp) or {}
        finally:
            fp.close()
        
        return cls(filename, config)


def flatten(dictionary, prefix=''):
    
    """
    Flatten nested dictionaries into dotted keys.
    
        >>> d = {
        ...     'a': {
        ...           'b': 1,
        ...           'c': {
        ...                 'd': 2,
        ...                 'e': {
        ...                       'f': 3
        ...                 }
        ...           }
        ...      },
        ...      'g': 4,
        ... }
    
        >>> sorted(flatten(d).items())
        [('a.b', 1), ('a.c.d', 2), ('a.c.e.f', 3), ('g', 4)]
    """
    
    for key in dictionary.keys():
        value = dictionary.pop(key)
        if not isinstance(value, dict):
            dictionary[prefix + key] = value
        else:
            for key2 in value.keys():
                value2 = value.pop(key2)
                if not isinstance(value2, dict):
                    dictionary[prefix + key + '.' + key2] = value2
                else:
                    dictionary.update(flatten(value2,
                        prefix=(prefix + key + '.' + key2 + '.')))
    return dictionary

########NEW FILE########
__FILENAME__ = directories
# -*- coding: utf-8 -*-

import os.path as p

from markdoc.config import Config


def html_dir(config):
    return p.abspath(p.join(config['meta.root'],
        config.get('html-dir', config['hide-prefix'] + 'html')))


def static_dir(config):
    return p.abspath(p.join(config['meta.root'], config.get('static-dir', 'static')))


def wiki_dir(config):
    return p.abspath(p.join(config['meta.root'], config.get('wiki-dir', 'wiki')))


def temp_dir(config):
    return p.abspath(p.join(config['meta.root'],
        config.get('temp-dir', config['hide-prefix'] + 'tmp')))


def template_dir(config):
    return p.abspath(p.join(config['meta.root'],
        config.get('template-dir', config['hide-prefix'] + 'templates')))


Config.register_default('hide-prefix', '.')
Config.register_default('use-default-static', True)
Config.register_default('cvs-exclude', True)
Config.register_func_default('html-dir', lambda cfg, key: html_dir(cfg))
Config.register_func_default('static-dir', lambda cfg, key: static_dir(cfg))
Config.register_func_default('wiki-dir', lambda cfg, key: wiki_dir(cfg))
Config.register_func_default('temp-dir', lambda cfg, key: temp_dir(cfg))
Config.register_func_default('template-dir', lambda cfg, key: template_dir(cfg))

Config.html_dir = property(html_dir)
Config.static_dir = property(static_dir)
Config.wiki_dir = property(wiki_dir)
Config.temp_dir = property(temp_dir)
Config.template_dir = property(template_dir)

########NEW FILE########
__FILENAME__ = exc
# -*- coding: utf-8 -*-


class MarkdocError(Exception):
    """An error occurred whilst running the markdoc utility."""
    pass


class AbortError(MarkdocError):
    """An exception occurred which should cause Markdoc to abort."""
    pass


########NEW FILE########
__FILENAME__ = render
# -*- coding: utf-8 -*-

import os.path as p

from markdoc.config import Config
import markdown


Config.register_default('markdown.extensions', ())
Config.register_func_default('markdown.extension-configs', lambda cfg, key: {})
Config.register_default('markdown.safe-mode', False)
Config.register_default('markdown.output-format', 'xhtml1')
Config.register_default('document-extensions',
    frozenset(['.md', '.mdown', '.markdown', '.wiki', '.text']))


class RelativeLinksTreeProcessor(markdown.treeprocessors.Treeprocessor):
    
    """A Markdown tree processor to relativize wiki links."""
    
    def __init__(self, curr_path='/'):
        self.curr_path = curr_path
    
    def make_relative(self, href):
        return make_relative(self.curr_path, href)
    
    def run(self, tree):
        links = tree.getiterator('a')
        for link in links:
            if link.attrib['href'].startswith('/'):
                link.attrib['href'] = self.make_relative(link.attrib['href'])
        return tree


def make_relative(curr_path, href):
    """Given a current path and a href, return an equivalent relative path."""
    
    curr_list = curr_path.lstrip('/').split('/')
    href_list = href.lstrip('/').split('/')
    
    # How many path components are shared between the two paths?
    i = len(p.commonprefix([curr_list, href_list]))
    
    rel_list = (['..'] * (len(curr_list) - i - 1)) + href_list[i:]
    if not rel_list or rel_list == ['']:
        return './'
    return '/'.join(rel_list)


def unflatten_extension_configs(config):
    """Unflatten the markdown extension configs from the config dictionary."""
    
    configs = config['markdown.extension-configs']
    
    for key, value in config.iteritems():
        if not key.startswith('markdown.extension-configs.'):
            continue
        
        parts = key[len('markdown.extension-configs.'):].split('.')
        extension_config = configs
        for part in parts[:-1]:
            extension_config = extension_config.setdefault(part, {})
        extension_config[parts[-1]] = value
    
    return configs


def get_markdown_instance(config, curr_path='/', **extra_config):
    """Return a `markdown.Markdown` instance for a given configuration."""
    
    mdconfig = dict(
        extensions=config['markdown.extensions'],
        extension_configs=unflatten_extension_configs(config),
        safe_mode=config['markdown.safe-mode'],
        output_format=config['markdown.output-format'])
    
    mdconfig.update(extra_config) # Include any extra kwargs.
    
    md_instance = markdown.Markdown(**mdconfig)
    md_instance.treeprocessors['relative_links'] = RelativeLinksTreeProcessor(curr_path=curr_path)
    return md_instance

# Add it as a method to `markdoc.config.Config`.
Config.markdown = get_markdown_instance

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-

from markdoc.config import Config


Config.register_default('server.bind', '127.0.0.1')
Config.register_default('server.port', 8008)
Config.register_default('server.num-threads', 10)
Config.register_default('server.name', None)
Config.register_default('server.request-queue-size', 5)
Config.register_default('server.timeout', 10)


def server_maker(config, **extra_config):
    
    """
    Return a server-making callable to create a CherryPy WSGI server.
    
    The server-making callable should be passed a WSGI application, and it
    will return an instance of `cherrypy.wsgiserver.CherryPyWSGIServer`.
    
    You can optionally override any of the hardwired configuration
    parameters by passing in keyword arguments which will be passed along to
    the `CherryPyWSGIServer` constructor.
    """
    
    from cherrypy.wsgiserver import CherryPyWSGIServer
    
    bind_addr = (config['server.bind'], config['server.port'])
    kwargs = dict(
        numthreads=config['server.num-threads'],
        server_name=config['server.name'],
        request_queue_size=config['server.request-queue-size'],
        timeout=config['server.timeout'])
    kwargs.update(extra_config)
    
    return lambda wsgi_app: CherryPyWSGIServer(bind_addr, wsgi_app, **kwargs)

Config.server_maker = server_maker

########NEW FILE########
__FILENAME__ = templates
# -*- coding: utf-8 -*-

import os.path as p

import jinja2
import markdoc
from markdoc.config import Config


Config.register_default('use-default-templates', True)


def build_template_env(config):
    """Build a Jinja2 template environment for a given config."""
    
    load_path = []
    
    if p.isdir(config.template_dir):
        load_path.append(config.template_dir)
    
    if config['use-default-templates']:
        load_path.append(markdoc.default_template_dir)
    
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(load_path))
    environment.globals['config'] = config
    return environment


def template_env(config):
    if not getattr(config, '_template_env', None):
        config._template_env = build_template_env(config)
    return config._template_env

Config.template_env = property(template_env)

########NEW FILE########
__FILENAME__ = wsgi
# -*- coding: utf-8 -*-

import logging
import mimetypes
import os.path as p

import webob

from markdoc.render import make_relative


if not mimetypes.inited:
    mimetypes.init()
# Assume all HTML files are XHTML.
mimetypes.types_map['.html'] = mimetypes.types_map['.xhtml']


class MarkdocWSGIApplication(object):
    
    """
    A WSGI application which will serve up a Markdoc wiki.
    
    Note that this application is not specifically reserved for Markdoc wikis,
    but was designed especially for them. The handling of requests is simple,
    and is based on the request path:
    
        /[a/b/.../c/]filename
        * If the file exists relative to the docroot, serve it; else
        * If the filename with the extension 'html' exists relative to the
          docroot, serve it; else
        * If a directory exists with that name, return a redirect to it (with a
          trailing slash); else
        * Return a HTTP 404 ‘Not Found’.
        
        /[a/b/.../c/]directory/ (including the index, '/')
        * If the directory exists, look for an 'index.html' file inside it, and
          serve it if it exists; else
        * If a file of the same name exists in the parent directory, return a
          redirect to it (without the trailing slash); else
        * Return a HTTP 404 ‘Not Found’.
    
    In the context of Markdoc, if a directory does not contain an 'index.md'
    file, a listing will be generated and saved as the 'index.html' file for
    that directory.
    """
    
    def __init__(self, config):
        self.config = config
        self.log = logging.getLogger('markdoc.wsgi')
    
    def __call__(self, environ, start_response):
        request = webob.Request(environ)
        response = self.get_response(request)
        self.log.info('%s %s - %d' % (request.method, request.path_info, response.status_int))
        return response(environ, start_response)
    
    def is_safe(self, directory):
        """Make sure the given absolute path does not point above the htroot."""
        
        return p.pardir not in p.relpath(directory, start=self.config.html_dir).split(p.sep)
    
    def get_response(self, request):
        if request.path_info.endswith('/'):
            return self.directory(request)
        return self.file(request)
    
    def directory(self, request):
        
        """
        Serve a request which points to a directory.
        
        * If the directory exists, look for an 'index.html' file inside it, and
          serve it if it exists; else
        * If a file of the same name exists in the parent directory, return a
          redirect to it (without the trailing slash); else
        * If a file of the same name with a 'html' extension exists in the
          parent directory, redirect to it (without the trailing slash); else
        * Return a HTTP 404 ‘Not Found’.
        """
        
        path_parts = request.path_info.strip('/').split('/')
        index_filename = p.join(self.config.html_dir, *(path_parts + ['index.html']))
        if p.exists(index_filename) and self.is_safe(index_filename):
            return serve_file(index_filename)
        
        directory_filename = p.join(self.config.html_dir, *path_parts)
        if p.isfile(directory_filename) or p.isfile(directory_filename + p.extsep + 'html'):
            return temp_redirect(request.path_info.rstrip('/'))
        
        return self.not_found(request)
    
    def file(self, request):
        
        """
        Serve a request which points to a file.
        
        * If the file exists relative to the docroot, serve it; else
        * If the filename with the extension 'html' exists relative to the
          docroot, serve it; else
        * If a directory exists with that name, return a redirect to it (with a
          trailing slash); else
        * Return a HTTP 404 ‘Not Found’.
        """
        
        path_parts = request.path_info.strip('/').split('/')
        filename = p.abspath(p.join(self.config.html_dir, *path_parts))
        if not self.is_safe(filename):
            return self.forbidden(request)
        
        if p.isfile(filename):
            pass
        elif p.isfile(filename + p.extsep + 'html'):
            filename = filename + p.extsep + 'html'
        else:
            if p.isdir(filename):
                return temp_redirect(request.path_info + '/')
            return self.not_found(request)
        
        return serve_file(filename)
    
    def error(self, request, status):
        
        """
        Serve a page for a given HTTP error.
        
        This works by rendering a template based on the HTTP error code; so an
        error of '404 Not Found' will render the '404.html' template. The
        context passed to the template is as follows:
        
        `request`
        : The `webob.Request` object for this HTTP request.
        
        `is_index`
        : A boolean indicating whether or not this is the index page. This may
        be useful in error pages where you want to link back to the home page;
        such a link will be useless in the index.
        
        `status`
        : An integer representing the HTTP status code of this error.
        
        `reason`
        : A string of the HTTP status 'reason', such as 'Not Found' for 404.
        
        The template is assumed to be valid XHTML.
        
        Note that the templating machinery is only invoked when the browser is
        expecting HTML. This is determined by calling
        `request.accept.accept_html()`. If not, an empty response (i.e. one
        without a content body) is returned.
        """
        
        response = webob.Response()
        response.status = status
        
        if request.accept.accept_html():
            context = {}
            context['request'] = request
            context['is_index'] = request.path_info in ['/', '/index.html']
            context['make_relative'] = lambda href: make_relative(request.path_info, href)
            context['status'] = status
            context['reason'] = webob.util.status_reasons[status]
            
            template = self.config.template_env.get_template('%d.html' % status)
            response.unicode_body = template.render(context)
            response.content_type = mimetypes.types_map['.xhtml']
        else:
            del response.content_length
            del response.content_type
        
        return response
    
    forbidden = lambda self, request: self.error(request, 403)
    not_found = lambda self, request: self.error(request, 404)


def redirect(location, permanent=False):
    """Issue an optionally-permanent redirect to another location."""
    
    response = webob.Response()
    response.status = 301 if permanent else 302
    response.location = location
    
    del response.content_type
    del response.content_length
    
    return response

temp_redirect = lambda location: redirect(location, permanent=False)
perm_redirect = lambda location: redirect(location, permanent=True)


def serve_file(filename, content_type=None, chunk_size=4096):
    
    """
    Serve the specified file as a chunked response.
    
    Return a `webob.Response` instance which will serve up the file in chunks,
    as specified by the `chunk_size` parameter (default 4KB).
    
    You can also specify a content type with the `content_type` keyword
    argument. If you do not, the content type will be inferred from the
    filename; so 'index.html' will be interpreted as 'application/xhtml+xml',
    'file.mp3' as 'audio/mpeg', et cetera. If none can be guessed, the content
    type will be reported as 'application/octet-stream'.
    """
    
    if content_type is None:
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
    if content_type.startswith('text/html'):
        content_type = content_type.replace('text/html', 'application/xhtml+xml')
    
    def chunked_read(chunk_size=4096):
        fp = open(filename, 'rb')
        try:
            data = fp.read(chunk_size)
            while data:
                yield data
                data = fp.read(chunk_size)
        finally:
            fp.close()
    
    response = webob.Response(content_type=content_type)
    response.app_iter = chunked_read()
    response.content_length = p.getsize(filename)
    return response

########NEW FILE########
__FILENAME__ = builder_fixture
# -*- coding: utf-8 -*-

import os.path as p

from common import get_temporary_config, clean_temporary_config


def setup_test(test):
    test.globs['CONFIG'] = get_temporary_config()
    test.globs['WIKI_ROOT'] = p.join(test.globs['CONFIG']['meta.root'], '')


def teardown_test(test):
    clean_temporary_config(test.globs['CONFIG'])

########NEW FILE########
__FILENAME__ = cache_fixture
# -*- coding: utf-8 -*-

from builder_fixture import setup_test, teardown_test

########NEW FILE########
__FILENAME__ = cli_fixture
# -*- coding: utf-8 -*-

from builder_fixture import setup_test, teardown_test

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

import os.path as p
import shutil
import tempfile

from markdoc.config import Config


def get_temporary_config():
    
    """
    Return a temporary Markdoc configuration.
    
    The contents of the wiki will be copied from the example Markdoc wiki. After
    you're done with this, you should call `clean_temporary_config()` on the
    config object.
    """
    
    own_config_dir = p.join(p.dirname(p.abspath(__file__)), 'example') + p.sep
    temp_config_dir = p.join(tempfile.mkdtemp(), 'example')
    shutil.copytree(own_config_dir, temp_config_dir)
    return Config.for_directory(temp_config_dir)


def clean_temporary_config(config):
    """Delete a temporary configuration's wiki root."""
    
    shutil.rmtree(p.dirname(config['meta.root']))

########NEW FILE########
__FILENAME__ = config_fixture
# -*- coding: utf-8 -*-

import os.path as p


def setup_test(test):
    test.globs['WIKI_ROOT'] = p.join(p.dirname(p.abspath(__file__)), 'example')

########NEW FILE########
__FILENAME__ = listing_fixture
# -*- coding: utf-8 -*-

from builder_fixture import setup_test, teardown_test

########NEW FILE########
