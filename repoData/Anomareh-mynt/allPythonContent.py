__FILENAME__ = base
# -*- coding: utf-8 -*-

from __future__ import unicode_literals


class Parser(object):
    accepts = ()
    
    
    def __init__(self, options = None):
        self.options = options if options is not None else {}
        
        self.setup()
    
    
    def parse(self, content):
        raise NotImplementedError('A parser must implement parse.')
    
    def setup(self):
        pass

class Renderer(object):
    def __init__(self, path, options = None, globals_ = None):
        self.path = path
        self.options = options if options is not None else {}
        self.globals = globals_ if globals_ is not None else {}
        
        self.setup()
    
    
    def from_string(self, string, data = None):
        raise NotImplementedError('A renderer must implement from_string.')
    
    def register(self, key, value):
        raise NotImplementedError('A renderer must implement register.')
    
    def render(self, template, data = None):
        raise NotImplementedError('A renderer must implement render.')
    
    def setup(self):
        pass

########NEW FILE########
__FILENAME__ = containers
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from collections import OrderedDict
from datetime import datetime

import yaml

from mynt.exceptions import ConfigException
from mynt.fs import Directory
from mynt.utils import absurl, Data, format_url, get_logger, normpath, slugify


yaml.add_constructor('tag:yaml.org,2002:str', lambda loader, node: loader.construct_scalar(node))

logger = get_logger('mynt')


class Config(dict):
    def __init__(self, string):
        super(Config, self).__init__()
        
        try:
            self.update(yaml.load(string))
        except yaml.YAMLError:
            raise ConfigException('Config contains unsupported YAML.')
        except:
            logger.debug('..  config file is empty')
            
            pass


class Container(object):
    def __init__(self, name, src, config):
        self._pages = None
        
        self.name = name
        self.src = src
        self.path = Directory(normpath(self.src.path, '_containers', self.name))
        self.config = config
        self.data = Data([], OrderedDict(), OrderedDict())
    
    
    def _archive(self, container, archive):
        for item in container:
            year, month = datetime.utcfromtimestamp(item['timestamp']).strftime('%Y %B').decode('utf-8').split()
            
            if year not in archive:
                archive[year] = {
                    'months': OrderedDict({month: [item]}),
                    'url': self._get_page_url(self.config['archives_url'], year),
                    'year': year
                }
            elif month not in archive[year]['months']:
                archive[year]['months'][month] = [item]
            else:
                archive[year]['months'][month].append(item)
    
    def _get_page_url(self, url, text):
        slug = slugify(text)
        
        return format_url(absurl(url, slug), url.endswith('/'))
    
    def _get_pages(self):
        pages = []
        
        for item in self.container:
            pages.append((item['layout'], {'item': item}, item['url']))
        
        if self.config['archive_layout'] and self.archives:
            for archive in self.archives.itervalues():
                pages.append((
                    self.config['archive_layout'],
                    {'archive': archive},
                    archive['url']
                ))
        
        if self.config['tag_layout'] and self.tags:
            for tag in self.tags.itervalues():
                pages.append((
                    self.config['tag_layout'],
                    {'tag': tag},
                    tag['url']
                ))
        
        return pages
    
    def _relate(self):
        for index, item in enumerate(self.container):
            if index:
                item['prev'] = self.container[index - 1]
            else:
                item['prev'] = None
            
            try:
                item['next'] = self.container[index + 1]
            except IndexError:
                item['next'] = None
    
    def _sort(self, container, key, reverse = False):
        def sort(item):
            attribute = item.get(key, item)
            
            if isinstance(attribute, basestring):
                return attribute.lower()
            
            return attribute
        
        container.sort(key = sort, reverse = reverse)
    
    
    def add(self, item):
        self.container.append(item)
    
    def archive(self):
        self._archive(self.container, self.archives)
        
        for tag in self.tags.itervalues():
            self._archive(tag['container'], tag['archives'])
    
    def sort(self):
        self._sort(self.container, self.config['sort'], self.config['reverse'])
        self._relate()
    
    def tag(self):
        tags = []
        
        for item in self.container:
            item['tags'].sort(key = unicode.lower)
            
            for tag in item['tags']:
                if tag not in self.tags:
                    self.tags[tag] = []
                
                self.tags[tag].append(item)
        
        for name, container in self.tags.iteritems():
            tags.append({
                'archives': OrderedDict(),
                'count': len(container),
                'name': name,
                'container': container,
                'url': self._get_page_url(self.config['tags_url'], name)
            })
        
        self._sort(tags, 'name')
        self._sort(tags, 'count', True)
        
        self.tags.clear()
        
        for tag in tags:
            self.tags[tag['name']] = tag
    
    
    @property
    def archives(self):
        return self.data.archives
    
    @property
    def container(self):
        return self.data.container
    
    @property
    def pages(self):
        if self._pages is None:
            self._pages = self._get_pages()
        
        return self._pages
    
    @property
    def tags(self):
        return self.data.tags


class Posts(Container):
    def __init__(self, src, config):
        super(Posts, self).__init__('posts', src, config)
        
        self.path = Directory(normpath(self.src.path, '_posts'))
        
        self._update_config()
    
    
    def _update_config(self):
        config = {
            'archives_url': 'archives_url',
            'archive_layout': 'archive_layout',
            'reverse': True,
            'sort': 'timestamp',
            'tags_url': 'tags_url',
            'tag_layout': 'tag_layout',
            'url': 'posts_url'
        }
        
        for k, v in config.iteritems():
            config[k] = self.config.get(v, v)
        
        self.config = config

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from argparse import ArgumentParser
from copy import deepcopy
from glob import iglob
import locale
import logging
from os import chdir, getcwd, path as op
import re
from time import sleep

from pkg_resources import resource_filename
from watchdog.observers import Observer

from mynt import __version__
from mynt.containers import Config
from mynt.exceptions import ConfigException, OptionException
from mynt.fs import Directory, EventHandler, File
from mynt.processors import Reader, Writer
from mynt.server import RequestHandler, Server
from mynt.utils import absurl, get_logger, normpath, Timer


logger = get_logger('mynt')


class Mynt(object):
    defaults = {
        'archive_layout': None,
        'archives_url': '/',
        'assets_url': '/assets/',
        'base_url': '/',
        'containers': {},
        'date_format': '%A, %B %d, %Y',
        'domain': None,
        'include': [],
        'locale': None,
        'posts_url': '/<year>/<month>/<day>/<slug>/',
        'pygmentize': True,
        'renderer': 'jinja',
        'tag_layout': None,
        'tags_url': '/',
        'version': __version__
    }
    
    container_defaults = {
        'archive_layout': None,
        'archives_url': '/',
        'reverse': False,
        'sort': 'title',
        'tag_layout': None,
        'tags_url': '/'
    }
    
    
    def __init__(self, args = None):
        self._reader = None
        self._writer = None
        
        self.config = {}
        self.posts = None
        self.containers = {}
        self.data = {}
        self.pages = []
        
        self.opts = self._get_opts(args)
        
        logger.setLevel(getattr(logging, self.opts['level'], logging.INFO))
        
        self.opts['func']()
    
    
    def _get_opts(self, args):
        opts = {}
        
        parser = ArgumentParser(description = 'A static blog generator.')
        sub = parser.add_subparsers()
        
        level = parser.add_mutually_exclusive_group()
        
        level.add_argument('-l', '--level',
            default = b'INFO', type = str.upper, choices = [b'DEBUG', b'INFO', b'WARNING', b'ERROR'],
            help = 'Sets %(prog)s\'s log level.')
        level.add_argument('-q', '--quiet',
            action = 'store_const', const = 'ERROR', dest = 'level',
            help = 'Sets %(prog)s\'s log level to ERROR.')
        level.add_argument('-v', '--verbose',
            action = 'store_const', const = 'DEBUG', dest = 'level',
            help = 'Sets %(prog)s\'s log level to DEBUG.')
        
        parser.add_argument('-V', '--version',
            action = 'version', version = '%(prog)s v{0}'.format(__version__),
            help = 'Prints %(prog)s\'s version and exits.')
        
        gen = sub.add_parser('gen')
        
        gen.add_argument('src',
            nargs = '?', default = '.', metavar = 'source',
            help = 'The directory %(prog)s looks in for source files.')
        gen.add_argument('dest',
            metavar = 'destination',
            help = 'The directory %(prog)s outputs to.')
        
        gen.add_argument('--base-url',
            help = 'Sets the site\'s base URL overriding the config setting.')
        gen.add_argument('--locale',
            help = 'Sets the locale used by the renderer.')
        
        force = gen.add_mutually_exclusive_group()
        
        force.add_argument('-c', '--clean',
            action = 'store_true',
            help = 'Forces generation by deleting the destination if it exists.')
        force.add_argument('-f', '--force',
            action = 'store_true',
            help = 'Forces generation by emptying the destination if it exists.')
        
        gen.set_defaults(func = self.generate)
        
        init = sub.add_parser('init')
        
        init.add_argument('dest',
            metavar = 'destination',
            help = 'The directory %(prog)s outputs to.')
        
        init.add_argument('--bare',
            action = 'store_true',
            help = 'Initializes a new site without using a theme.')
        init.add_argument('-f', '--force',
            action = 'store_true',
            help = 'Forces initialization by deleting the destination if it exists.')
        init.add_argument('-t', '--theme',
            default = 'dark',
            help = 'Sets which theme will be used.')
        
        init.set_defaults(func = self.init)
        
        serve = sub.add_parser('serve')
        
        serve.add_argument('src',
            nargs = '?', default = '.', metavar = 'source',
            help = 'The directory %(prog)s will serve.')
        
        serve.add_argument('--base-url',
            default = '/',
            help = 'Sets the site\'s base URL overriding the config setting.')
        serve.add_argument('-p', '--port',
            default = 8080, type = int,
            help = 'Sets the port used by the server.')
        
        serve.set_defaults(func = self.serve)
        
        watch = sub.add_parser('watch')
        
        watch.add_argument('src',
            nargs = '?', default = '.', metavar = 'source',
            help = 'The directory %(prog)s looks in for source files.')
        watch.add_argument('dest',
            metavar = 'destination',
            help = 'The directory %(prog)s outputs to.')
        
        watch.add_argument('--base-url',
            help = 'Sets the site\'s base URL overriding the config setting.')
        watch.add_argument('-f', '--force',
            action = 'store_true',
            help = 'Forces watching by emptying the destination every time a change is made if it exists.')
        watch.add_argument('--locale',
            help = 'Sets the locale used by the renderer.')
        
        watch.set_defaults(func = self.watch)
        
        for option, value in vars(parser.parse_args(args)).iteritems():
            if value is not None:
                if isinstance(option, str):
                    option = option.decode('utf-8')
                
                if isinstance(value, str):
                    value = value.decode('utf-8')
                
                opts[option] = value
        
        return opts
    
    def _get_theme(self, theme):
        return resource_filename(__name__, 'themes/{0}'.format(theme))
    
    def _update_config(self):
        self.config = deepcopy(self.defaults)
        
        logger.debug('>> Searching for config')
        
        for ext in ('.yml', '.yaml'):
            f = File(normpath(self.src.path, 'config' + ext))
            
            if f.exists:
                logger.debug('..  found: %s', f.path)
                
                try:
                    self.config.update(Config(f.content))
                except ConfigException as e:
                    raise ConfigException(e.message, 'src: {0}'.format(f.path))
                
                self.config['locale'] = self.opts.get('locale', self.config['locale'])
                
                self.config['assets_url'] = absurl(self.config['assets_url'], '')
                self.config['base_url'] = absurl(self.opts.get('base_url', self.config['base_url']), '')
                
                for setting in ('archives_url', 'posts_url', 'tags_url'):
                    self.config[setting] = absurl(self.config[setting])
                
                for setting in ('archives_url', 'assets_url', 'base_url', 'posts_url', 'tags_url'):
                    if re.search(r'(?:^\.{2}/|/\.{2}$|/\.{2}/)', self.config[setting]):
                        raise ConfigException('Invalid config setting.',
                            'setting: {0}'.format(setting),
                            'path traversal is not allowed')
                
                for name, config in self.config['containers'].iteritems():
                    try:
                        url = absurl(config['url'])
                    except KeyError:
                        raise ConfigException('Invalid config setting.',
                            'setting: containers:{0}'.format(name),
                            'url must be set for all containers')
                    
                    if re.search(r'(?:^\.{2}/|/\.{2}$|/\.{2}/)', url):
                        raise ConfigException('Invalid config setting.',
                            'setting: containers:{0}:url'.format(name),
                            'path traversal is not allowed')
                    
                    config.update((k, v) for k, v in self.container_defaults.iteritems() if k not in config)
                    config['url'] = url
                
                for pattern in self.config['include']:
                    if op.commonprefix((self.src.path, normpath(self.src.path, pattern))) != self.src.path:
                        raise ConfigException('Invalid include path.',
                            'path: {0}'.format(pattern),
                            'path traversal is not allowed')
                
                break
        else:
            logger.debug('..  no config file found')
    
    
    def _parse(self):
        logger.info('>> Parsing')
        
        self.posts, containers, pages = self.reader.parse()
        
        self.containers.update(containers)
        self.pages.extend(pages)
        
        self.data['posts'] = self.posts.data
        self.data['containers'] = {}
        
        for name, container in self.containers.iteritems():
            self.data['containers'][name] = container.data
    
    def _render(self):
        self._parse()
        
        logger.info('>> Rendering')
        
        self.writer.register(self.data)
        
        for i, page in enumerate(self.pages):
            self.pages[i] = self.writer.render(*page)
    
    def _generate(self):
        logger.debug('>> Initializing\n..  src:  %s\n..  dest: %s', self.src.path, self.dest.path)
        
        self._update_config()
        
        if self.config['locale']:
            try:
                locale.setlocale(locale.LC_ALL, (self.config['locale'], 'utf-8'))
            except locale.Error:
                raise ConfigException('Locale not available.',
                    'run `locale -a` to see available locales')
        
        self.writer.register({'site': self.config})
        
        self._render()
        
        logger.info('>> Generating')
        
        assets_src = Directory(normpath(self.src.path, '_assets'))
        assets_dest = Directory(normpath(self.dest.path, *self.config['assets_url'].split('/')))
        
        if self.dest.exists:
            if self.opts['force']:
                self.dest.empty()
            else:
                self.dest.rm()
        else:
            self.dest.mk()
        
        for page in self.pages:
            page.mk()
        
        assets_src.cp(assets_dest.path)
        
        for pattern in self.config['include']:
            for path in iglob(normpath(self.src.path, pattern)):
                dest = path.replace(self.src.path, self.dest.path)
                
                if op.isdir(path):
                    Directory(path).cp(dest, False)
                elif op.isfile(path):
                    File(path).cp(dest)
    
    def _regenerate(self):
        self._reader = None
        self._writer = None
        
        self.posts = None
        
        self.config.clear()
        self.containers.clear()
        self.data.clear()
        
        del self.pages[:]
        
        self._generate()
    
    
    def generate(self):
        Timer.start()
        
        self.src = Directory(self.opts['src'])
        self.dest = Directory(self.opts['dest'])
        
        if not self.src.exists:
            raise OptionException('Source must exist.')
        elif self.src == self.dest:
            raise OptionException('Source and destination must differ.')
        elif self.dest.exists and not (self.opts['force'] or self.opts['clean']):
            raise OptionException('Destination already exists.',
                'the -c or -f flag must be passed to force generation by deleting or emptying the destination')
        
        self._generate()
        
        logger.info('Completed in %.3fs', Timer.stop())
    
    def init(self):
        Timer.start()
        
        self.src = Directory(self._get_theme(self.opts['theme']))
        self.dest = Directory(self.opts['dest'])
        
        if not self.src.exists:
            raise OptionException('Theme not found.')
        elif self.dest.exists and not self.opts['force']:
            raise OptionException('Destination already exists.',
                'the -f flag must be passed to force initialization by deleting the destination')
        
        logger.info('>> Initializing')
        
        if self.opts['bare']:
            self.dest.rm()
            
            for d in ('_assets/css', '_assets/images', '_assets/js', '_templates', '_posts'):
                Directory(normpath(self.dest.path, d)).mk()
            
            File(normpath(self.dest.path, 'config.yml')).mk()
        else:
            self.src.cp(self.dest.path, False)
        
        logger.info('Completed in %.3fs', Timer.stop())
    
    def serve(self):
        self.src = Directory(self.opts['src'])
        base_url = absurl(self.opts['base_url'], '')
        
        if not self.src.exists:
            raise OptionException('Source must exist.')
        
        logger.info('>> Serving at 127.0.0.1:%s', self.opts['port'])
        logger.info('Press ctrl+c to stop.')
        
        cwd = getcwd()
        self.server = Server(('', self.opts['port']), base_url, RequestHandler)
        
        chdir(self.src.path)
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.shutdown()
            chdir(cwd)
            
            print('')
    
    def watch(self):
        self.src = Directory(self.opts['src'])
        self.dest = Directory(self.opts['dest'])
        
        if not self.src.exists:
            raise OptionException('Source must exist.')
        elif self.src == self.dest:
            raise OptionException('Source and destination must differ.')
        elif self.dest.exists and not self.opts['force']:
            raise OptionException('Destination already exists.',
                'the -f flag must be passed to force watching by emptying the destination every time a change is made')
        
        logger.info('>> Watching')
        logger.info('Press ctrl+c to stop.')
        
        self.observer = Observer()
        
        self.observer.schedule(EventHandler(self.src.path, self._regenerate), self.src.path, True)
        self.observer.start()
        
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            
            print('')
        
        self.observer.join()
    
    
    @property
    def reader(self):
        if self._reader is None:
            self._reader = Reader(self.src, self.dest, self.config, self.writer)
        
        return self._reader
    
    @property
    def writer(self):
        if self._writer is None:
            self._writer = Writer(self.src, self.dest, self.config)
        
        return self._writer

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

from __future__ import unicode_literals


class MyntException(Exception):
    code = 1
    
    
    def __init__(self, message, *args):
        self.message = message
        self.debug = args
    
    
    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        message = '!! {0}'.format(self.message)
        
        for d in self.debug:
            message += '\n..  {0}'.format(d)
        
        return message


class ConfigException(MyntException):
    pass

class ContentException(MyntException):
    pass

class FileSystemException(MyntException):
    pass

class OptionException(MyntException):
    code = 2

class ParserException(MyntException):
    pass

class RendererException(MyntException):
    pass

########NEW FILE########
__FILENAME__ = fs
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from codecs import open
from datetime import datetime
from os import makedirs, path as op, remove, walk
from re import search
import shutil
from sys import exc_info
import traceback

from watchdog.events import FileSystemEventHandler

from mynt.exceptions import FileSystemException
from mynt.utils import abspath, get_logger, normpath, Timer


logger = get_logger('mynt')


class Directory(object):
    def __init__(self, path):
        self.path = abspath(path)
        
        if self.is_root:
            raise FileSystemException('Root is not an acceptible directory.')
    
    
    def _ignored(self, path, names):
        return [name for name in names if name.startswith(('.', '_'))]
    
    
    def cp(self, dest, ignore = True):
        if self.exists:
            dest = Directory(dest)
            ignore = self._ignored if ignore else None
            
            if dest.exists:
                dest.rm()
            
            logger.debug('..  cp: %s\n..      dest: %s', self.path, dest.path)
            
            shutil.copytree(self.path, dest.path, ignore = ignore)
    
    def empty(self):
        if self.exists:
            for root, dirs, files in walk(self.path):
                for d in dirs[:]:
                    if not d.startswith(('.', '_')):
                        Directory(abspath(root, d)).rm()
                    
                    dirs.remove(d)
                
                for f in files:
                    if not f.startswith(('.', '_')):
                        File(abspath(root, f)).rm()
    
    def mk(self):
        if not self.exists:
            logger.debug('..  mk: %s', self.path)
            
            makedirs(self.path)
    
    def rm(self):
        if self.exists:
            logger.debug('..  rm: %s', self.path)
            
            shutil.rmtree(self.path)
    
    
    @property
    def exists(self):
        return op.isdir(self.path)
    
    @property
    def is_root(self):
        return op.dirname(self.path) == self.path
    
    
    def __eq__(self, other):
        return self.path == other
    
    def __iter__(self):
        for root, dirs, files in walk(self.path):
            for d in dirs[:]:
                if d.startswith(('.', '_')):
                    dirs.remove(d)
            
            for f in files:
                if f.startswith(('.', '_')):
                    continue
                
                yield File(normpath(root, f))
    
    def __ne__(self, other):
        return self.path != other
    
    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return self.path

class EventHandler(FileSystemEventHandler):
    def __init__(self, src, callback):
        self._src = src
        self._callback = callback
    
    
    def _regenerate(self, path):
        path = path.replace(self._src, '')
        
        if search(r'/[._](?!assets|containers|posts|templates)', path):
            logger.debug('>> Skipping: %s', path)
        else:
            logger.info('>> Change detected in: %s', path)
            
            try:
                Timer.start()
                
                self._callback()
                
                logger.info('Regenerated in %.3fs', Timer.stop())
            except:
                t, v, tb = exc_info()
                lc = traceback.extract_tb(tb)[-1:][0]
                
                logger.error('!! %s\n..  file: %s\n..  line: %s\n..    in: %s\n..    at: %s', v, *lc)
                
                pass
    
    
    def on_any_event(self, event):
        if event.event_type != 'moved':
            self._regenerate(event.src_path)
    
    def on_moved(self, event):
        self._regenerate(event.dest_path)

class File(object):
    def __init__(self, path, content = None):
        self.path = abspath(path)
        self.root = Directory(op.dirname(self.path))
        self.name, self.extension = op.splitext(op.basename(self.path))
        self.content = content
    
    
    def cp(self, dest):
        if self.exists:
            dest = File(dest)
            
            if self.path != dest.path:
                if not dest.root.exists:
                    dest.root.mk()
                
                logger.debug('..  cp: %s%s\n..      src:  %s\n..      dest: %s', self.name, self.extension, self.root, dest.root)
                
                shutil.copyfile(self.path, dest.path)
    
    def mk(self):
        if not self.exists:
            if not self.root.exists:
                self.root.mk()
            
            logger.debug('..  mk: %s', self.path)
            
            with open(self.path, 'w', encoding = 'utf-8') as f:
                if self.content is None:
                    self.content = ''
                
                f.write(self.content)
    
    def rm(self):
        if self.exists:
            logger.debug('..  rm: %s', self.path)
            
            remove(self.path)
    
    
    @property
    def content(self):
        if self._content is None and self.exists:
            with open(self.path, 'r', encoding = 'utf-8') as f:
                self._content = f.read()
        
        return self._content
    
    @content.setter
    def content(self, content):
        self._content = content
    
    @property
    def exists(self):
        return op.isfile(self.path)
    
    @property
    def mtime(self):
        if self.exists:
            return datetime.utcfromtimestamp(op.getmtime(self.path))
    
    
    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return self.path

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import sys

from mynt.core import Mynt
from mynt.exceptions import MyntException


def main():
    try:
        Mynt()
    except MyntException as e:
        print(e)
        
        return e.code
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = docutils
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from copy import deepcopy

from docutils import nodes, utils
from docutils.core import publish_parts
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.body import CodeBlock
from docutils.parsers.rst.roles import register_canonical_role, set_classes
from docutils.utils.code_analyzer import Lexer, LexerError
from docutils.writers.html4css1 import HTMLTranslator, Writer

from mynt.base import Parser as _Parser


def code_role(role, rawtext, text, lineno, inliner, options = {}, content = []):
    set_classes(options)
    language = options.get('language', '')
    classes = []
    
    if 'classes' in options:
        classes.extend(options['classes'])
    
    if language and language not in classes:
        classes.append(language)
    
    try:
        tokens = Lexer(utils.unescape(text, 1), language, inliner.document.settings.syntax_highlight)
    except LexerError, error:
        msg = inliner.reporter.warning(error)
        prb = inliner.problematic(rawtext, rawtext, msg)
        
        return [prb], [msg]

    node = nodes.literal(rawtext, '', classes = classes)

    for classes, value in tokens:
        if classes:
            node += nodes.inline(value, value, classes = classes)
        else:
            node += nodes.Text(value, value)

    return [node], []

code_role.options = {
    'class': directives.class_option,
    'language': directives.unchanged
}

register_canonical_role('code', code_role)


class _CodeBlock(CodeBlock):
    optional_arguments = 1
    option_spec = {
        'class': directives.class_option,
        'name': directives.unchanged,
        'number-lines': directives.unchanged
    }
    has_content = True
    
    def run(self):
        self.assert_has_content()
        
        if self.arguments:
            language = self.arguments[0]
        else:
            language = 'text'
        
        set_classes(self.options)
        classes = []
        
        if 'classes' in self.options:
            classes.extend(self.options['classes'])
        
        try:
            tokens = Lexer(u'\n'.join(self.content), language, self.state.document.settings.syntax_highlight)
        except LexerError, error:
            raise self.warning(error)
        
        pre = nodes.literal_block(classes = classes)
        code = nodes.literal(classes = classes)
        code.attributes['data-lang'] = language
        self.add_name(pre)
        self.add_name(code)
        
        for classes, value in tokens:
            if classes:
                code += nodes.inline(value, value, classes = classes)
            else:
                code += nodes.Text(value, value)
        
        pre += code
        
        return [pre]

directives.register_directive('code', _CodeBlock)


class _Translator(HTMLTranslator):
    def set_first_last(self, node):
        pass
    
    def visit_bullet_list(self, node):
        atts = {}
        self.context.append((self.compact_simple, self.compact_p))
        self.compact_p = None
        self.compact_simple = self.is_compactable(node)
        self.body.append(self.starttag(node, 'ul', '', **atts))
    
    def visit_definition(self, node):
        self.body.append('</dt>')
        self.body.append(self.starttag(node, 'dd', ''))
        self.set_first_last(node)

    def depart_definition(self, node):
        self.body.append('</dd>')

    def visit_definition_list(self, node):
        self.body.append(self.starttag(node, 'dl', ''))

    def depart_definition_list(self, node):
        self.body.append('</dl>')
    
    def visit_entry(self, node):
        atts = {}
        
        if isinstance(node.parent.parent, nodes.thead):
            tagname = 'th'
        else:
            tagname = 'td'
        
        node.parent.column += 1
        
        if 'morerows' in node:
            atts['rowspan'] = node['morerows'] + 1
        
        if 'morecols' in node:
            atts['colspan'] = node['morecols'] + 1
            node.parent.column += node['morecols']
        
        self.body.append(self.starttag(node, tagname, '', **atts))
        self.context.append('</%s>' % tagname.lower())
        
        if len(node) == 0:
            self.body.append('&nbsp;')
        
        self.set_first_last(node)
    
    def visit_enumerated_list(self, node):
        atts = {}
        
        if 'start' in node:
            atts['start'] = node['start']
        
        self.context.append((self.compact_simple, self.compact_p))
        self.compact_p = None
        self.compact_simple = self.is_compactable(node)
        self.body.append(self.starttag(node, 'ol', '', **atts))
    
    def visit_list_item(self, node):
        self.body.append(self.starttag(node, 'li', ''))
    
    def depart_list_item(self, node):
        self.body.append('</li>')
    
    def visit_literal(self, node):
        atts = {}
        
        if 'data-lang' in node.attributes:
            atts['data-lang'] = node.attributes['data-lang']
        
        self.body.append(self.starttag(node, 'code', '', **atts))
    
    def visit_literal_block(self, node):
        self.body.append(self.starttag(node, 'pre', ''))
    
    def depart_literal_block(self, node):
        self.body.append('</pre>')
    
    def visit_paragraph(self, node):
        if self.should_be_compact_paragraph(node):
            self.context.append('')
        else:
            self.body.append(self.starttag(node, 'p', ''))
            self.context.append('</p>')
    
    def visit_reference(self, node):
        atts = {}
        
        if 'refuri' in node:
            atts['href'] = node['refuri']
            
            if (self.settings.cloak_email_addresses and atts['href'].startswith('mailto:')):
                atts['href'] = self.cloak_mailto(atts['href'])
                self.in_mailto = True
        else:
            assert 'refid' in node, 'References must have "refuri" or "refid" attribute.'
            
            atts['href'] = '#' + node['refid']
        
        if not isinstance(node.parent, nodes.TextElement):
            assert len(node) == 1 and isinstance(node[0], nodes.image)
        
        self.body.append(self.starttag(node, 'a', '', **atts))
    
    def depart_row(self, node):
        self.body.append('</tr>')
    
    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1
    
    def visit_table(self, node):
        self.body.append(self.starttag(node, 'table', ''))
    
    def depart_table(self, node):
        self.body.append('</table>')
    
    def visit_tbody(self, node):
        self.body.append(self.starttag(node, 'tbody', ''))
    
    def depart_tbody(self, node):
        self.body.append('</tbody>')
    
    def visit_tgroup(self, node):
        node.stubs = []
    
    def visit_thead(self, node):
        self.body.append(self.starttag(node, 'thead', ''))
    
    def depart_thead(self, node):
        self.body.append('</thead>')
    
    def visit_title(self, node):
        close_tag = '</p>'
        
        if isinstance(node.parent, nodes.topic):
            self.body.append(self.starttag(node, 'p', ''))
        elif isinstance(node.parent, nodes.sidebar):
            self.body.append(self.starttag(node, 'p', ''))
        elif isinstance(node.parent, nodes.Admonition):
            self.body.append(self.starttag(node, 'p', ''))
        elif isinstance(node.parent, nodes.table):
            self.body.append(self.starttag(node, 'caption', ''))
            close_tag = '</caption>'
        elif isinstance(node.parent, nodes.document):
            self.body.append(self.starttag(node, 'h1', ''))
            close_tag = '</h1>'
            self.in_document_title = len(self.body)
        else:
            assert isinstance(node.parent, nodes.section)
            
            h_level = self.section_level + self.initial_header_level - 1
            
            self.body.append(self.starttag(node, 'h%s' % h_level, ''))
            
            atts = {}
            
            if node.hasattr('refid'):
                atts['href'] = '#' + node['refid']
            
            if atts:
                self.body.append(self.starttag({}, 'a', '', **atts))
                close_tag = '</a></h%s>' % (h_level)
            else:
                close_tag = '</h%s>' % (h_level)
        
        self.context.append(close_tag)

class _Writer(Writer):
    def __init__(self):
        Writer.__init__(self)
        
        self.translator_class = _Translator


class Parser(_Parser):
    accepts = (u'.rst',)
    
    
    defaults = {
        'doctitle_xform': 0,
        'input_encoding': 'utf-8',
        'output_encoding': 'utf-8',
        'report_level': 4,
        'smart_quotes': 1,
        'syntax_highlight': 'none'
    }
    
    
    def parse(self, restructuredtext):
        return publish_parts(
            restructuredtext,
            settings_overrides = self.config,
            writer = self._writer
        )['fragment']
    
    def setup(self):
        self.config = deepcopy(self.defaults)
        self.config.update(self.options)
        self.config['file_insertion_enabled'] = 0
        
        self._writer = _Writer()

########NEW FILE########
__FILENAME__ = hoep
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from copy import deepcopy
from operator import or_
import re

import hoep as h

from mynt.base import Parser as _Parser
from mynt.utils import escape


class _Renderer(h.Hoep):
    def __init__(self, extensions = 0, render_flags = 0):
        super(_Renderer, self).__init__(extensions, render_flags)
        
        self._toc_ids = {}
        self._toc_patterns = (
            (r'<[^<]+?>', ''),
            (r'[^a-z0-9_.\s-]', ''),
            (r'\s+', '-'),
            (r'^[^a-z]+', ''),
            (r'^$', 'section')
        )
    
    
    def block_code(self, text, language):
        text = escape(text)
        language = ' data-lang="{0}"'.format(language) if language else ''
        
        return '<pre><code{0}>{1}</code></pre>'.format(language, text)
    
    def header(self, text, level):
        if self.render_flags & h.HTML_TOC:
            identifier = text.lower()
            
            for pattern, replace in self._toc_patterns:
                identifier = re.sub(pattern, replace, identifier)
            
            if identifier in self._toc_ids:
                self._toc_ids[identifier] += 1
                identifier = '{0}-{1}'.format(identifier, self._toc_ids[identifier])
            else:
                self._toc_ids[identifier] = 1
            
            return '<h{0} id="{1}">{2}</h{0}>'.format(level, identifier, text)
        else:
            return '<h{0}>{1}</h{0}>'.format(level, text)
    
    
    def preprocess(self, markdown):
        self._toc_ids.clear()
        
        return markdown


class Parser(_Parser):
    accepts = ('.md',)
    
    
    lookup = {
        'extensions': {
            'autolink': h.EXT_AUTOLINK,
            'disable_indented_code': h.EXT_DISABLE_INDENTED_CODE,
            'fenced_code': h.EXT_FENCED_CODE,
            'footnotes': h.EXT_FOOTNOTES,
            'highlight': h.EXT_HIGHLIGHT,
            'lax_spacing': h.EXT_LAX_SPACING,
            'no_intra_emphasis': h.EXT_NO_INTRA_EMPHASIS,
            'quote': h.EXT_QUOTE,
            'space_headers': h.EXT_SPACE_HEADERS,
            'strikethrough': h.EXT_STRIKETHROUGH,
            'superscript': h.EXT_SUPERSCRIPT,
            'tables': h.EXT_TABLES,
            'underline': h.EXT_UNDERLINE
        },
        'render_flags': {
            'escape': h.HTML_ESCAPE,
            'expand_tabs': h.HTML_EXPAND_TABS,
            'hard_wrap': h.HTML_HARD_WRAP,
            'safelink': h.HTML_SAFELINK,
            'skip_html': h.HTML_SKIP_HTML,
            'skip_images': h.HTML_SKIP_IMAGES,
            'skip_links': h.HTML_SKIP_LINKS,
            'skip_style': h.HTML_SKIP_STYLE,
            'smartypants': h.HTML_SMARTYPANTS,
            'toc': h.HTML_TOC,
            'use_xhtml': h.HTML_USE_XHTML
        }
    }
    
    defaults = {
        'extensions': {
            'autolink': True,
            'fenced_code': True,
            'footnotes': True,
            'no_intra_emphasis': True,
            'strikethrough': True,
            'tables': True
        },
        'render_flags': {
            'smartypants': True
        }
    }
    
    
    def parse(self, markdown):
        return self._md.render(markdown)
    
    def setup(self):
        self.flags = {}
        self.config = deepcopy(self.defaults)
        
        for k, v in self.options.iteritems():
            self.config[k].update(v)
        
        for group, options in self.config.iteritems():
            flags = [self.lookup[group][k] for k, v in options.iteritems() if v]
            
            self.flags[group] = reduce(or_, flags, 0)
        
        self._md = _Renderer(**self.flags)

########NEW FILE########
__FILENAME__ = processors
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from calendar import timegm
from datetime import datetime
from importlib import import_module
from os import path as op
import re

from pkg_resources import DistributionNotFound, iter_entry_points, load_entry_point
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from mynt.containers import Config, Container, Posts
from mynt.exceptions import ConfigException, ContentException, ParserException, RendererException
from mynt.fs import File
from mynt.utils import format_url, get_logger, Item, normpath, slugify, Timer, unescape


logger = get_logger('mynt')


class Reader(object):
    def __init__(self, src, dest, site, writer):
        self._writer = writer
        
        self._parsers = {}
        self._extensions = {}
        self._cache = {}
        
        self.src = src
        self.dest = dest
        self.site = site
        
        self._find_parsers()
    
    
    def _find_parsers(self):
        for parser in iter_entry_points('mynt.parsers'):
            name = parser.name.decode('utf-8')
            
            try:
                Parser = parser.load()
            except DistributionNotFound as e:
                logger.debug('@@ The %s parser could not be loaded due to a missing requirement: %s.', name, unicode(e))
                
                continue
            
            for extension in Parser.accepts:
                if extension in self._extensions:
                    self._extensions[extension].append(name)
                else:
                    self._extensions[extension] = [name]
            
            self._parsers[name] = Parser
        
        for parsers in self._extensions.itervalues():
            parsers.sort(key = unicode.lower)
    
    def _get_content_url(self, url, slug, date, frontmatter):
        subs = {
            '<year>': '%Y',
            '<month>': '%m',
            '<day>': '%d',
            '<i_month>': unicode(date.month),
            '<i_day>': unicode(date.day),
            '<slug>': slug
        }
        
        url = url.replace('%', '%%')
        
        for match, replace in subs.iteritems():
            url = url.replace(match, replace)
        
        for attribute, value in frontmatter.iteritems():
            if isinstance(value, basestring):
                url = url.replace('<{0}>'.format(attribute), slugify(value))
        
        url = date.strftime(url).decode('utf-8')
        
        return format_url(url, url.endswith('/'))
    
    def _get_date(self, mtime, date):
        if not date:
            return mtime
        
        d = [None, None, None, 0, 0]
        
        for i, v in enumerate(date.split('-')):
            d[i] = v
        
        if not d[3]:
            d[3], d[4] = mtime.strftime('%H %M').decode('utf-8').split()
        elif not d[4]:
            d[4] = '{0:02d}'.format(d[4])
        
        return datetime.strptime('-'.join(d), '%Y-%m-%d-%H-%M')
    
    def _get_parser(self, f, parser = None):
        if not parser:
            try:
                parser = self._extensions[f.extension][0]
            except KeyError:
                raise ParserException('No parser found that accepts \'{0}\' files.'.format(f.extension),
                    'src: {0}'.format(f.path))
        
        if parser in self._cache:
            return self._cache[parser]
        
        options = self.site.get(parser, None)
        
        if parser in self._parsers:
            Parser = self._parsers[parser](options)
        else:
            try:
                Parser = import_module('mynt.parsers.{0}'.format(parser)).Parser(options)
            except ImportError:
                raise ParserException('The {0} parser could not be found.'.format(parser))
        
        self._cache[parser] = Parser
        
        return Parser
    
    def _parse_filename(self, f):
        date, slug = re.match(r'(?:(\d{4}(?:-\d{2}-\d{2}){1,2})-)?(.+)', f.name).groups()
        
        return (
            slugify(slug),
            self._get_date(f.mtime, date)
        )
    
    
    def _parse(self, container):
        for f in container.path:
            Timer.start()
            
            item = Item(f.path)
            
            try:
                frontmatter, bodymatter = re.search(r'\A---\s+^(.+?)$\s+---\s*(.*)\Z', f.content, re.M | re.S).groups()
                frontmatter = Config(frontmatter)
            except AttributeError:
                raise ContentException('Invalid frontmatter.',
                    'src: {0}'.format(f.path),
                    'frontmatter must not be empty')
            except ConfigException:
                raise ConfigException('Invalid frontmatter.',
                    'src: {0}'.format(f.path),
                    'fontmatter contains invalid YAML')
            
            if 'layout' not in frontmatter:
                raise ContentException('Invalid frontmatter.',
                    'src: {0}'.format(f.path),
                    'layout must be set')
            
            parser = self._get_parser(f, frontmatter.get('parser', container.config.get('parser', None)))
            
            slug, date = self._parse_filename(f)
            content = parser.parse(self._writer.from_string(bodymatter, frontmatter))
            
            item['content'] = content
            item['date'] = date.strftime(self.site['date_format']).decode('utf-8')
            item['excerpt'] = re.search(r'\A.*?(?:<p>(.+?)</p>)?', content, re.M | re.S).group(1)
            item['tags'] = []
            item['timestamp'] = timegm(date.utctimetuple())
            
            item.update(frontmatter)
            
            item['url'] = self._get_content_url(container.config['url'], slug, date, frontmatter)
            
            container.add(item)
            
            logger.debug('..  (%.3fs) %s', Timer.stop(), f.path.replace(self.src.path, ''))
        
        container.sort()
        container.tag()
        container.archive()
        
        return container
    
    
    def parse(self):
        posts = self._parse(Posts(self.src, self.site))
        containers = {}
        pages = posts.pages
        
        for name, config in self.site['containers'].iteritems():
            container = self._parse(Container(name, self.src, config))
            
            containers[name] = container
            pages.extend(container.pages)
        
        for f in self.src:
            if f.extension in ('.html', '.htm', '.xml'):
                pages.append((f.path.replace(self.src.path, ''), None, None))
        
        return (posts, containers, pages)

class Writer(object):
    def __init__(self, src, dest, site):
        self.src = src
        self.dest = dest
        self.site = site
        
        self._renderer = self._get_renderer()
    
    
    def _get_path(self, url):
        parts = [self.dest.path] + url.split('/')
        
        if url.endswith('/'):
            parts.append('index.html')
        
        path = normpath(*parts)
        
        if op.commonprefix((self.dest.path, path)) != self.dest.path:
            raise ConfigException('Invalid URL.',
                'url: {0}'.format(url),
                'path traversal is not allowed')
        
        return path
    
    def _get_renderer(self):
        renderer = self.site['renderer']
        options = self.site.get(renderer, None)
        
        try:
            Renderer = load_entry_point('mynt', 'mynt.renderers', renderer)
        except DistributionNotFound as e:
            raise RendererException('The {0} renderer requires {1}.'.format(renderer, unicode(e)))
        except ImportError:
            try:
                Renderer = import_module('mynt.renderers.{0}'.format(renderer)).Renderer
            except ImportError:
                raise RendererException('The {0} renderer could not be found.'.format(renderer))
        
        return Renderer(self.src.path, options)
    
    def _highlight(self, match):
        language, code = match.groups()
        formatter = HtmlFormatter(linenos = 'table')
        code = unescape(code)
        
        try:
            code = highlight(code, get_lexer_by_name(language), formatter)
        except ClassNotFound:
            code = highlight(code, get_lexer_by_name('text'), formatter)
        
        return '<div class="code"><div>{0}</div></div>'.format(code)
    
    def _pygmentize(self, html):
        return re.sub(r'<pre><code[^>]+data-lang="([^>]+)"[^>]*>(.+?)</code></pre>', self._highlight, html, flags = re.S)
    
    
    def from_string(self, string, data = None):
        return self._renderer.from_string(string, data)
    
    def register(self, data):
        self._renderer.register(data)
    
    def render(self, template, data = None, url = None):
        url = url if url is not None else template
        path = self._get_path(url)
        
        try:
            Timer.start()
            
            content = self._renderer.render(template, data)
            
            if self.site['pygmentize']:
                content = self._pygmentize(content)
            
            logger.debug('..  (%.3fs) %s', Timer.stop(), path.replace(self.dest.path, ''))
        except RendererException as e:
            raise RendererException(e.message,
                '{0} in container item {1}'.format(template, data.get('item', url)))
        
        return File(path, content)

########NEW FILE########
__FILENAME__ = jinja
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from collections import OrderedDict
from datetime import datetime
import gettext
import locale
from os import path as op
from re import sub

from jinja2 import Environment, FileSystemLoader, PrefixLoader
from jinja2.exceptions import TemplateNotFound

from mynt.base import Renderer as _Renderer
from mynt.exceptions import RendererException
from mynt.utils import absurl, normpath


class _PrefixLoader(PrefixLoader):
    def get_loader(self, template):
        try:
            if not self.delimiter:
                for prefix in self.mapping:
                    if template.startswith(prefix):
                        name = template.replace(prefix, '', 1)
                        loader = self.mapping[prefix]
                        
                        break
                else:
                    raise TemplateNotFound(template)
            else:
                prefix, name = template.split(self.delimiter, 1)
                loader = self.mapping[prefix]
        except (KeyError, ValueError):
            raise TemplateNotFound(template)
        
        # Gross hack to appease Jinja when handling Windows paths.
        if op.sep != '/':
            name = name.replace(op.sep, '/')
        
        return loader, name


class Renderer(_Renderer):
    config = {}
    
    
    def _absolutize(self, html):
        def _replace(match):
            return self._get_url(match.group(1).replace(self.globals['site']['base_url'], '', 1), True)
        
        return sub(r'(?<==")({0}[^"]*)'.format(self.globals['site']['base_url']), _replace, html)
    
    def _date(self, ts, format = '%A, %B %d, %Y'):
        if ts is None:
            return datetime.utcnow().strftime(format).decode('utf-8')
        
        return datetime.utcfromtimestamp(ts).strftime(format).decode('utf-8')
    
    def _get_asset(self, asset):
        return absurl(self.globals['site']['base_url'], self.globals['site']['assets_url'], asset)
    
    def _get_url(self, url = '', absolute = False):
        parts = [self.globals['site']['base_url'], url]
        domain = self.globals['site']['domain']
        
        if absolute and domain:
            if not domain.startswith(('http://', 'https://')):
                domain = 'http://' + domain
            
            parts.insert(0, domain)
        
        return absurl(*parts)
    
    def _items(self, dict_):
        return dict_.iteritems()
    
    def _values(self, dict_):
        return dict_.itervalues()
    
    
    def from_string(self, string, data = None):
        if data is None:
            data = {}
        
        template = self.environment.from_string(string)
        
        return template.render(**data)
    
    def register(self, data):
        self.globals.update(data)
        self.environment.globals.update(data)
    
    def render(self, template, data = None):
        if data is None:
            data = {}
        
        try:
            template = self.environment.get_template(template)
        except TemplateNotFound:
            raise RendererException('Template not found.')
        
        return template.render(**data)
    
    def setup(self):
        self.config.update(self.options)
        self.config['loader'] = _PrefixLoader(OrderedDict([
            (op.sep, FileSystemLoader(self.path)),
            ('', FileSystemLoader(normpath(self.path, '_templates')))
        ]), None)
        
        self.environment = Environment(**self.config)
        
        self.environment.filters['absolutize'] = self._absolutize
        self.environment.filters['date'] = self._date
        self.environment.filters['items'] = self._items
        self.environment.filters['values'] = self._values
        
        self.environment.globals.update(self.globals)
        self.environment.globals['get_asset'] = self._get_asset
        self.environment.globals['get_url'] = self._get_url
        
        if 'extensions' in self.config and 'jinja2.ext.i18n' in self.config['extensions']:
            try:
                langs = [locale.getlocale(locale.LC_MESSAGES)[0].decode('utf-8')]
            except AttributeError:
                langs = None
            
            self.environment.install_gettext_translations(gettext.translation(gettext.textdomain(), normpath(self.path, '_locales'), langs, fallback = True))

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import TCPServer

from mynt.utils import get_logger


logger = get_logger('mynt')


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, base_url, server):
        self.base_url = base_url
        
        SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
    
    def do_GET(self):
        self.path = self.path.replace(self.base_url, b'/')
        
        SimpleHTTPRequestHandler.do_GET(self)
    
    def log_message(self, format, *args):
        # A little bit of me died inside having had to commit this.
        args = list(args)
        
        for i, v in enumerate(args):
            if not isinstance(v, basestring):
                args[i] = str(v).decode('utf-8')
            elif isinstance(v, str):
                args[i] = v.decode('utf-8')
        
        logger.debug('>> [%s] %s: %s', self.log_date_time_string(), self.address_string(), ' '.join(args))

class Server(TCPServer):
    allow_reuse_address = True
    
    def __init__(self, server_address, base_url, RequestHandlerClass, bind_and_activate = True):
        TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        
        self.base_url = base_url.encode('utf-8')
    
    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self.base_url, self)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
from os import path as op
import re
from time import time


_ENTITIES = [
    ('&', ['&amp;', '&#x26;', '&#38;']),
    ('<', ['&lt;', '&#x3C;', '&#60;']),
    ('>', ['&gt;', '&#x3E;', '&#62;']),
    ('"', ['&quot;', '&#x22;', '&#34;']),
    ('\'', ['&#x27;', '&#39;']),
    ('/', ['&#x2F;', '&#47;']),
]


def _cleanpath(*args):
    parts = [args[0].strip()]
    
    for arg in args[1:]:
        parts.append(arg.strip(' \t\n\r\v\f' + op.sep))
    
    return parts


def abspath(*args):
    return op.realpath(
        op.expanduser(
            op.join(
                *_cleanpath(*args)
            )
        )
    )

def absurl(*args):
    url = '/'.join(args)
    
    if not re.match(r'[^/]+://', url):
        url = '/' + url
    
    return re.sub(r'(?<!:)//+', '/', url)

def escape(html):
    for match, replacements in _ENTITIES:
        html = html.replace(match, replacements[0])
    
    return html

def get_logger(name):
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        
        logger.addHandler(handler)
    
    return logger

def normpath(*args):
    return op.normpath(
        op.join(
            *_cleanpath(*args)
        )
    )

def slugify(string):
    slug = re.sub(r'\s+', '-', string.strip())
    slug = re.sub(r'[^a-z0-9\-_.]', '', slug, flags = re.I)
    
    return slug

def unescape(html):
    for replace, matches in _ENTITIES:
        for match in matches:
            html = html.replace(match, replace)
    
    return html


def format_url(url, clean):
    if clean:
        return absurl(url, '')
    
    return '{0}.html'.format(url)


class Data(object):
    def __init__(self, container, archives, tags):
        self.container = container
        self.archives = archives
        self.tags = tags
    
    
    def __iter__(self):
        return self.container.__iter__()

class Item(dict):
    def __init__(self, src, *args, **kwargs):
        super(Item, self).__init__(*args, **kwargs)
        
        self.__src = src
    
    
    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return self.__src

class Timer(object):
    _start = []
    
    
    @classmethod
    def start(cls):
        cls._start.append(time())
    
    @classmethod
    def stop(cls):
        return time() - cls._start.pop()

########NEW FILE########
