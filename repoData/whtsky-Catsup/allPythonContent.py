__FILENAME__ = cli
import sys
import os

major = sys.version_info[0]
if major < 3:
    reload(sys)
    sys.setdefaultencoding('utf-8')

from catsup.options import g
from catsup.logger import logger, enable_pretty_logging

enable_pretty_logging()

import catsup

doc = """Catsup v%s

Usage:
    catsup init [<path>]
    catsup build [-s <file>|--settings=<file>]
    catsup deploy [-s <file>|--settings=<file>]
    catsup git [-s <file>|--settings=<file>]
    catsup rsync [-s <file>|--settings=<file>]
    catsup server [-s <file>|--settings=<file>] [-p <port>|--port=<port>]
    catsup webhook [-s <file>|--settings=<file>] [-p <port>|--port=<port>]
    catsup watch [-s <file>|--settings=<file>]
    catsup clean [-s <file>|--settings=<file>]
    catsup themes
    catsup install <theme>
    catsup -h | --help
    catsup --version

Options:
    -h --help               Show this screen and exit.
    -s --settings=<file>    specify a config file. [default: config.json]
    -f --file=<file>        specify a wordpress output file.
    -o --output=<dir>       specify a output folder. [default: .]
    -p --port=<port>        specify the server port. [default: 8888]
    -g --global             install theme to global theme folder.
""" % catsup.__version__

from parguments import Parguments

parguments = Parguments(doc, version=catsup.__version__)


@parguments.command
def init(path):
    """
    Usage:
        catsup init [<path>]

    Options:
        -h --help               Show this screen and exit.
    """
    from catsup.parser.utils import create_config_file
    create_config_file(path)


@parguments.command
def build(settings):
    """
    Usage:
        catsup build [-s <file>|--settings=<file>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
    """
    from catsup.generator import Generator
    generator = Generator(settings)
    generator.generate()


@parguments.command
def deploy(settings):
    """
    Usage:
        catsup deploy [-s <file>|--settings=<file>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
    """
    import catsup.parser
    import catsup.deploy
    config = catsup.parser.config(settings)
    if config.deploy.default == 'git':
        catsup.deploy.git(config)
    elif config.deploy.default == 'rsync':
        catsup.deploy.rsync(config)
    else:
        logger.error("Unknown deploy: %s" % config.deploy.default)


@parguments.command
def git(settings):
    """
    Usage:
        catsup git [-s <file>|--settings=<file>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
    """
    import catsup.parser.config
    import catsup.deploy
    config = catsup.parser.config(settings)
    catsup.deploy.git(config)


@parguments.command
def rsync(settings):
    """
    Usage:
        catsup rsync [-s <file>|--settings=<file>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
    """
    import catsup.parser.config
    import catsup.deploy
    config = catsup.parser.config(settings)
    catsup.deploy.rsync(config)


@parguments.command
def server(settings, port):
    """
    Usage:
        catsup server [-s <file>|--settings=<file>] [-p <port>|--port=<port>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
        -p --port=<port>        specify the server port. [default: 8888]
    """
    import catsup.server
    preview_server = catsup.server.PreviewServer(settings, port)
    preview_server.run()


@parguments.command
def webhook(settings, port):
    """
    Usage:
        catsup webhook [-s <file>|--settings=<file>] [-p <port>|--port=<port>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
        -p --port=<port>        specify the server port. [default: 8888]
    """
    import catsup.server
    server = catsup.server.WebhookServer(settings, port)
    server.run()


@parguments.command
def watch(settings):
    """
    Usage:
        catsup watch [-s <file>|--settings=<file>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
    """
    from catsup.generator import Generator
    from catsup.server import CatsupEventHandler
    from watchdog.observers import Observer

    generator = Generator(settings)
    generator.generate()
    event_handler = CatsupEventHandler(generator)
    observer = Observer()
    for path in [generator.config.config.source, g.theme.path]:
        path = os.path.abspath(path)
        observer.schedule(event_handler, path=path, recursive=True)
    observer.start()
    while True:
        pass


@parguments.command
def clean(settings):
    """
    Usage:
        catsup clean [-s <file>|--settings=<file>]

    Options:
        -h --help               Show this screen and exit.
        -s --settings=<file>    specify a setting file. [default: config.json]
    """
    import shutil
    import catsup.parser.config
    config = catsup.parser.config(settings)

    for path in [config.config.static_output, config.config.output]:
        if os.path.exists(path):
            shutil.rmtree(path)


@parguments.command
def themes():
    """
    Usage:
        catsup themes

    Options:
        -h --help               Show this screen and exit.
    """
    from catsup.parser.themes import list_themes
    list_themes()


@parguments.command
def install(name):
    """
    Usage:
        catsup install <name>

    Options:
        -h --help               Show this screen and exit.
    """
    from catsup.themes.install import install_theme
    install_theme(name=name)


def main():
    parguments.run()

########NEW FILE########
__FILENAME__ = deploy
import os
import datetime
import shutil

from catsup.logger import logger
from catsup.utils import call


RSYNC_COMMAND = "rsync -avze 'ssh -p {ssh_port}' {args}" \
                " {deploy_dir}/ {ssh_user}@{ssh_host}:{document_root}"


def git(config):
    logger.info("Deploying your site via git")

    cwd = os.path.abspath(config.config.output)

    def _call(*args, **kwargs):
        return call(*args, cwd=cwd, **kwargs)

    dot_git_path = os.path.join(cwd, '.git')

    if os.path.exists(dot_git_path) and \
            _call('git remote -v | grep %s' % config.deploy.git.repo) == 0:
        if os.path.exists(dot_git_path):
            shutil.rmtree(dot_git_path)
        _call('git init', silence=True)
        _call('git remote add origin %s' % config.deploy.git.repo)
        if config.deploy.git.branch != 'master':
            _call('git branch -m %s' % config.deploy.git.branch, silence=True)
        _call('git pull origin %s' % config.deploy.git.branch)
        _call('rm -rf *')

        from catsup.generator import Generator

        generator = Generator(config.path)
        generator.generate()

    _call('git add .', silence=True)
    _call('git commit -m "Update at %s"' % str(datetime.datetime.utcnow()),
          silence=True)
    _call('git push origin %s' % config.deploy.git.branch)


def rsync(config):
    logger.info("Deploying your site via rsync")
    if config.deploy.rsync.delete:
        args = "--delete"
    else:
        args = ""
    cmd = RSYNC_COMMAND.format(
        ssh_port=config.deploy.rsync.ssh_port,
        args=args,
        deploy_dir=config.config.output,
        ssh_user=config.deploy.rsync.ssh_user,
        ssh_host=config.deploy.rsync.ssh_host,
        document_root=config.deploy.rsync.document_root
    )
    call(cmd)

########NEW FILE########
__FILENAME__ = renderer
import os

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from catsup.options import g
from catsup.utils import mkdir, static_url, url_for, urljoin


class Renderer(object):
    def __init__(self, templates_path, generator):
        self.env = Environment(
            loader=FileSystemLoader(templates_path),
            autoescape=False
        )
        config = generator.config

        self.env.globals.update(
            generator=generator,
            site=config.site,
            config=config.config,
            author=config.author,
            comment=config.comment,
            theme=config.theme.vars,
            g=g,
            pages=generator.pages,
            static_url=static_url,
            url_for=url_for
        )

        catsup_filter_path = os.path.join(
            g.catsup_path, "templates", 'filters.py'
        )
        theme_filter_path = os.path.join(g.theme.path, 'filters.py')
        self.load_filters_from_pyfile(catsup_filter_path)
        self.load_filters_from_pyfile(theme_filter_path)
        self.rendered_permalinks = []

    def load_filters_from_pyfile(self, path):
        if not os.path.exists(path):
            return
        filters = {}
        exec(open(path).read(), {}, filters)
        self.env.filters.update(filters)

    def render(self, template, **kwargs):
        try:
            return self.env.get_template(template).render(**kwargs)
        except TemplateNotFound:
            # logger.warning("Template not found: %s" % template)
            pass

    def render_to(self, template, permalink, **kwargs):
        html = self.render(template, **kwargs)
        if not html:
            return
        permalink, output_name = urljoin(
            g.base_url,
            permalink
        ), permalink
        kwargs.setdefault("permalink", permalink)
        self.rendered_permalinks.append(permalink)
        if output_name.endswith("/") or "." not in output_name:
            output_name = output_name.rstrip("/")
            output_name += '/index.html'
        output_path = os.path.join(g.output, output_name.lstrip("/"))
        mkdir(os.path.dirname(output_path))
        with open(output_path, "w") as f:
            f.write(html)

    def render_sitemap(self):
        with open(os.path.join(g.output, "sitemap.txt"), "w") as f:
            f.write("\n".join(self.rendered_permalinks))

########NEW FILE########
__FILENAME__ = utils

########NEW FILE########
__FILENAME__ = logger
import sys
import time
import logging

try:
    import curses
    assert curses
except ImportError:
    curses = None

from catsup.utils import py3k

if py3k:
    unicode = str

logger = logging.getLogger()


def enable_pretty_logging(level='info'):
    """Turns on formatted logging output as configured.

    This is called automatically by `parse_command_line`.
    """
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        # Set up color if we are in a tty and curses is installed
        color = False
        if curses and sys.stderr.isatty():
            try:
                curses.setupterm()
                if curses.tigetnum("colors") > 0:
                    color = True
            except Exception:
                pass
        channel = logging.StreamHandler()
        channel.setFormatter(_LogFormatter(color=color))
        logger.addHandler(channel)


class _LogFormatter(logging.Formatter):
    def __init__(self, color, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self._color = color
        if color:
            # The curses module has some str/bytes confusion in
            # python3.  Until version 3.2.3, most methods return
            # bytes, but only accept strings.  In addition, we want to
            # output these strings with the logging module, which
            # works with unicode strings.  The explicit calls to
            # unicode() below are harmless in python2 but will do the
            # right conversion in python 3.
            fg_color = (curses.tigetstr("setaf") or
                        curses.tigetstr("setf") or "")
            if (3, 0) < sys.version_info < (3, 2, 3):
                fg_color = unicode(fg_color, "ascii")
            self._colors = {
                logging.DEBUG: unicode(curses.tparm(fg_color, 4),
                                       "ascii"),  # Blue
                logging.INFO: unicode(curses.tparm(fg_color, 2),
                                      "ascii"),  # Green
                logging.WARNING: unicode(curses.tparm(fg_color, 3),
                                         "ascii"),  # Yellow
                logging.ERROR: unicode(curses.tparm(fg_color, 1),
                                       "ascii"),  # Red
            }
            self._normal = unicode(curses.tigetstr("sgr0"), "ascii")

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)
        record.asctime = time.strftime(
            "%y%m%d %H:%M:%S", self.converter(record.created))
        prefix = '[%(levelname)1.1s %(asctime)s]' % \
                 record.__dict__
        if self._color:
            prefix = (self._colors.get(record.levelno, self._normal) +
                      prefix + self._normal)
        formatted = prefix + " " + record.message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + record.exc_text
        return formatted.replace("\n", "\n    ")

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

import os
import re

from datetime import datetime

from catsup.options import g
from catsup.utils import html_to_raw_text
from .utils import Pagination


class CatsupPage(object):
    @property
    def class_name(self):
        return self.__class__.__name__.lower()

    def get_permalink_args(self):
        return {}

    @property
    def permalink(self):
        kwargs = self.__dict__.copy()
        kwargs.update(self.get_permalink_args())
        return g.permalink[self.class_name].format(**kwargs).replace(" ", "-")

    def render(self, renderer, **kwargs):
        if hasattr(self, "template_name"):
            template_name = self.template_name
        else:
            template_name = self.class_name + ".html"
        kwargs[self.class_name] = self
        kwargs.update(self.__dict__)
        renderer.render_to(template_name, self.permalink, **kwargs)


class Tag(CatsupPage):
    def __init__(self, name):
        self.name = name
        self.posts = []

    def add_post(self, post):
        self.posts.append(post)

    @property
    def count(self):
        return len(self.posts)

    def __iter__(self):
        for post in self.posts:
            yield post


class Tags(CatsupPage):
    def __init__(self, tags=None):
        if tags is None:
            tags = {}
        self.tags_dict = tags

    def get(self, name):
        return self.tags_dict.setdefault(
            name,
            Tag(name)
        )

    def render(self, renderer, **kwargs):
        for tag in self.tags:
            tag.render(renderer)
        super(Tags, self).render(renderer, **kwargs)

    @property
    def tags(self):
        if not hasattr(self, "_tags"):
            self._tags = list(self.tags_dict.values())
            self._tags.sort(
                key=lambda x: x.count,
                reverse=True
            )
        return self._tags

    def __iter__(self):
        for tag in self.tags:
            yield tag


class Archive(CatsupPage):
    def __init__(self, year):
        self.year = int(year)
        self.posts = []

    def add_post(self, post):
        self.posts.append(post)

    @property
    def count(self):
        return len(self.posts)

    def __iter__(self):
        for post in self.posts:
            yield post


class Archives(CatsupPage):
    def __init__(self, archives=None):
        if archives is None:
            archives = {}
        self.archives_dict = archives

    def get(self, year):
        return self.archives_dict.setdefault(
            year,
            Archive(year)
        )

    def render(self, renderer, **kwargs):
        for tag in self.archives:
            tag.render(renderer)
        super(Archives, self).render(renderer, **kwargs)

    @property
    def archives(self):
        if not hasattr(self, "_archives"):
            self._archives = list(self.archives_dict.values())
            self._archives.sort(
                key=lambda x: x.year,
                reverse=True
            )
        return self._archives

    def __iter__(self):
        for archive in self.archives:
            yield archive


class Post(CatsupPage):
    DATE_RE = re.compile('\d{4}\-\d{2}\-\d{2}')

    def __init__(self, path, meta, content):
        self.path = path
        self.filename, _ = os.path.splitext(os.path.basename(path))
        self.meta = meta
        self.content = content
        self.tags = []
        self.date = self.datetime.strftime("%Y-%m-%d")

        filename, _ = os.path.splitext(os.path.basename(path))
        if self.DATE_RE.match(filename[:10]):
            self.meta.setdefault("date", filename[:10])
            self.filename = filename[11:]
        else:
            self.filename = filename

        if "date" in self.meta:
            self.date = self.meta.date
        else:
            self.date = self.datetime.strftime("%Y-%m-%d")

    def add_archive_and_tags(self):
        year = self.datetime.strftime("%Y")
        g.archives.get(year).add_post(self)

        for tag in self.meta.pop("tags", "").split(","):
            tag = tag.strip()
            tag = g.tags.get(tag)
            tag.add_post(self)
            self.tags.append(tag)

    @property
    def permalink(self):
        if "permalink" in self.meta:
            return self.meta.permalink
        return super(Post, self).permalink

    def get_permalink_args(self):
        args = self.meta.copy()
        args.update(
            title=self.title,
            datetime=self.datetime
        )
        return args

    @property
    def datetime(self):
        import os
        if "time" in self.meta:
            return datetime.strptime(
                self.meta.time, "%Y-%m-%d %H:%M"
            )
        elif "date" in self.meta:
            return datetime.strptime(
                self.meta.date, "%Y-%m-%d"
            )
        st_ctime = os.stat(self.path).st_ctime
        return datetime.fromtimestamp(st_ctime)

    @property
    def description(self):
        if "description" not in self.meta:
            description = self.meta.get(
                "description",
                self.content
            ).replace("\n", "")
            description = html_to_raw_text(description)
            if "<br" in description:
                description = description.split("<br")[0]
            elif "</p" in description:
                description = description.split("</p")[0]
            if len(description) > 150:
                description = description[:150]
            self.meta.description = description.strip()
        return self.meta.description

    @property
    def allow_comment(self):
        if self.meta.get("comment", None) == "disabled":
            return False
        else:
            return g.config.comment.allow

    @property
    def title(self):
        return self.meta.get("title", self.filename)

    @property
    def type(self):
        return self.meta.type


class Page(CatsupPage):
    def __init__(self, posts):
        self.posts = posts
        self.per_page = g.theme.post_per_page

    @staticmethod
    def get_permalink(page):
        if page == 1:
            return "/"
        return g.permalink["page"].format(page=page)

    @property
    def permalink(self):
        return Page.get_permalink(self.page)

    def render_all(self, renderer):
        count = int((len(self.posts) - 1) / self.per_page) + 1
        for i in range(count):
            page = i + 1
            if page == 1:
                self._permalink = "/"
            self.page = page
            pagination = Pagination(
                page=page,
                posts=self.posts,
                per_page=self.per_page,
                get_permalink=self.get_permalink
            )
            self.render(renderer=renderer, pagination=pagination)


class Feed(CatsupPage):
    def __init__(self, posts):
        self.posts = posts
        self.template_name = "feed.xml"


class NotFound(CatsupPage):
    def __init__(self):
        self.template_name = "404.html"

    @property
    def permalink(self):
        return "/404.html"

########NEW FILE########
__FILENAME__ = options
import os

from catsup.utils import ObjectDict

g = ObjectDict()

g.catsup_path = os.path.abspath(os.path.dirname(__file__))
g.public_templates_path = os.path.join(g.catsup_path, 'templates')
g.cwdpath = os.path.abspath('.')

########NEW FILE########
__FILENAME__ = config
import os
import ujson

from catsup.logger import logger
from catsup.options import g
from catsup.utils import update_nested_dict, urljoin, ObjectDict
from catsup.parser.themes import find_theme

from .utils import add_slash


def parse(path):
    """
    Parser json configuration file
    """
    try:
        f = open(path, 'r')
    except IOError:
        logger.error("Can't find config file."
                     "Run `catsup init` to generate a new config file.")
        exit(1)
    return update_nested_dict(ObjectDict(), ujson.load(f))


def load(path=None, local=False, base_url=None):
    # Read default configuration file first.
    # So catsup can use the default value when user's conf is missing.
    # And user does't have to change conf file everytime he updates catsup.
    default_config = os.path.join(g.public_templates_path, 'config.json')
    config = parse(default_config)

    if path:
        user_config = parse(path)
        config = update_nested_dict(config, user_config)
        os.chdir(os.path.abspath(os.path.dirname(path)))
    g.theme = find_theme(config)
    g.source = config.config.source
    g.output = config.config.output
    g.permalink = config.permalink
    if base_url:
        g.base_url = add_slash(base_url)
    else:
        g.base_url = add_slash(config.site.url)
    config.site.url = g.base_url
    if local:
        import tempfile
        config.config.static_prefix = "/static/"
        config.config.output = tempfile.mkdtemp()

    g.static_prefix = urljoin(
        g.base_url,
        add_slash(config.config.static_prefix)
    )

    g.theme.vars = update_nested_dict(g.theme.vars, config.theme.vars)
    config.theme.vars = g.theme.vars
    config.path = path
    return config

########NEW FILE########
__FILENAME__ = themes
# coding=utf-8
from __future__ import with_statement

import sys
import os

from catsup.logger import logger
from catsup.options import g
from catsup.utils import call, ObjectDict


def read_theme(path):
    """
    :param path: path for the theme.
    :return: Theme theme read in path.
    """
    if not os.path.exists(path):
        return
    theme_file = os.path.join(path, 'theme.py')
    if not os.path.exists(theme_file):
        logger.warn("%s is not a catsup theme." % path)
        return
    theme = ObjectDict(
        name='',
        author='',
        homepage='',
        path=path,
        post_per_page=5,
        vars={},
    )
    exec(open(theme_file).read(), {}, theme)
    theme.name = theme.name.lower()
    return theme


def find_theme(config=None, theme_name='', silence=False):
    if not theme_name:
        theme_name = config.theme.name
    theme_name = theme_name.lower()
    theme_gallery = [
        os.path.join(os.path.abspath('themes'), theme_name),
        os.path.join(g.catsup_path, 'themes', theme_name),
    ]
    for path in theme_gallery:
        theme = read_theme(path)
        if theme:
            return theme

    if not silence:
        logger.error("Can't find theme: {name}".format(name=theme_name))
        exit(1)


def list_themes():
    theme_gallery = [
        os.path.abspath('themes'),
        os.path.join(g.catsup_path, 'themes'),
    ]
    themes = ()
    for path in theme_gallery:
        if not os.path.exists(path):
            continue
        names = os.listdir(path)
        for name in names:
            theme_path = os.path.join(path, name)
            if os.path.isdir(theme_path):
                themes.add(name)
    print('Available themes: \n')
    themes_text = []
    for name in themes:
        theme = find(theme_name=name)
        themes_text.append("\n".join([
            'Name: %s' % theme.name,
            'Author: %s' % theme.author,
            'HomePage: %s' % theme.homepage
        ]))
    print("\n--------\n".join(themes_text))

########NEW FILE########
__FILENAME__ = utils
import os

from catsup.options import g
from catsup.utils import mkdir


def add_slash(url):
    if '//' in url:
        return url.rstrip('/') + '/'
    return '/%s/' % url.strip('/')


def get_template():
    default_config_path = os.path.join(g.public_templates_path, 'config.json')
    return open(default_config_path, 'r').read()


def create_config_file(path=None):
    if path:
        os.chdir(path)

    current_dir = os.getcwd()
    config_path = os.path.join(current_dir, 'config.json')

    if os.path.exists(config_path):
        from catsup.logger import logger
        logger.warning("Config file already exist.")
        exit(1)

    mkdir("posts")
    mkdir("static")

    template = get_template()

    with open(config_path, 'w') as f:
        f.write(template)

    print('Created a new config file.'
          'Please configure your blog by editing config.json')

########NEW FILE########
__FILENAME__ = html


from catsup.models import Post
from catsup.utils import to_unicode, ObjectDict
from catsup.reader.meta import parse_yaml_meta
from catsup.reader.utils import split_content


def html_reader(path):
    meta, content = split_content(path)
    if not meta:
        meta = ObjectDict()
    else:
        meta = parse_yaml_meta(meta, path)
    return Post(
        path=path,
        meta=meta,
        content=to_unicode(content)
    )

########NEW FILE########
__FILENAME__ = markdown
import misaka as m

from houdini import escape_html

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from catsup.models import Post
from catsup.utils import ObjectDict
from catsup.reader.meta import parse_meta
from catsup.reader.utils import split_content


class CatsupRender(m.HtmlRenderer, m.SmartyPants):
    def block_code(self, text, lang):
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except ClassNotFound:
            text = escape_html(text.strip())
            return '\n<pre><code>%s</code></pre>\n' % text
        else:
            formatter = HtmlFormatter()
            return highlight(text, lexer, formatter)

    def autolink(self, link, is_email):
        if is_email:
            s = '<a href="mailto:{link}">{link}</a>'
        elif link.endswith(('.jpg', '.png', '.git', '.jpeg')):
            s = '<a href="{link}"><img src="{link}" /></a>'
        else:
            s = '<a href="{link}">{link}</a>'
        return s.format(link=link)

md = m.Markdown(CatsupRender(flags=m.HTML_USE_XHTML),
                extensions=m.EXT_FENCED_CODE |
                m.EXT_NO_INTRA_EMPHASIS |
                m.EXT_AUTOLINK |
                m.EXT_STRIKETHROUGH |
                m.EXT_SUPERSCRIPT)


def markdown_reader(path):
    meta, content = split_content(path)
    content = content.replace("\n", "  \n")
    if not meta:
        meta = ObjectDict()
    else:
        meta = parse_meta(meta, path)
    return Post(
        path=path,
        meta=meta,
        content=md.render(content)
    )

########NEW FILE########
__FILENAME__ = meta
# -*- coding:utf-8 -*-

import yaml

from houdini import escape_html
from catsup.reader.utils import not_valid
from catsup.utils import update_nested_dict, ObjectDict


def read_base_meta(path):
    meta = ObjectDict(
        type="post"
    )
    if path:
        pass
    return meta


def parse_meta(lines, path=None):
    lines = [l.strip() for l in lines if l]
    if lines[0].startswith("#"):
        return parse_catsup_meta(lines, path)
    elif lines[0].startswith("---"):
        return parse_yaml_meta(lines, path)
    else:
        not_valid(path)


def parse_yaml_meta(lines, path=None):
    title_line = lines.pop(0)
    if not title_line.startswith("---"):
        not_valid(path)
    meta = read_base_meta(path)
    meta.update(yaml.load("\n".join(lines)))
    return update_nested_dict(ObjectDict(), meta)


def parse_catsup_meta(lines, path=None):
    meta = read_base_meta(path)
    if lines[0][0] == "#":
        meta.title = escape_html(lines.pop(0)[1:].strip())
    for line in lines:
        if not line:
            continue
        if ":" not in line:
            not_valid(path)
        name, value = line.split(':', 1)
        name = name.strip().lstrip('-').strip().lower()
        meta[name] = value.strip()
    return meta

########NEW FILE########
__FILENAME__ = txt
#coding: utf-8

from houdini import escape_html

from catsup.utils import to_unicode
from catsup.reader.html import html_reader


def txt_reader(path):
    post = html_reader(path)
    content = post.content.encode("utf-8")
    content = escape_html(content)
    content = content.replace(
        "\n",
        "<br />"
    )
    post.content = to_unicode(content)
    return post

########NEW FILE########
__FILENAME__ = utils
# -*- coding:utf-8 -*-

import codecs

from catsup.logger import logger
from catsup.utils import to_unicode


def open_file(path):
    try:
        return codecs.open(path, "r", encoding="utf-8")
    except IOError:
        logger.error("Can't open file %s" % path)
        exit(1)


def not_valid(path):
    logger.error("%s is not a valid post." % path)
    exit(1)


def split_content(path):
    file = open_file(path)

    lines = [file.readline().strip()]
    no_meta = False

    for l in file:
        l = l.strip()
        if l.startswith("---"):
            break
        elif l:
            lines.append(l)
    else:
        no_meta = True
    if no_meta:
        return [], to_unicode("\n".join(lines))
    else:
        return lines, to_unicode("".join(file))

########NEW FILE########
__FILENAME__ = server
import os
import catsup
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.autoreload

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from catsup.generator import Generator
from catsup.logger import logger
from catsup.options import g
from catsup.utils import call


class CatsupEventHandler(FileSystemEventHandler):
    def __init__(self, generator):
        self.generator = generator

    def on_any_event(self, event):
        logger.info("Captured a file change. Regenerate..")
        try:
            self.generator.generate()
        except:
            logger.error("Error when generating:", exc_info=True)


class CatsupHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Server", "Catsup/%s" % catsup.__version__)

    def log_exception(self, typ, value, tb):
        pass


class WebhookHandler(CatsupHandler):
    def initialize(self, path, generate):
        self.path = path
        self.generate = generate

    def get(self):
        call("git pull", cwd=self.path)
        self.generate()
        self.write("success.")

    def post(self):
        self.get()


class StaticFileHandler(CatsupHandler, tornado.web.StaticFileHandler):
    pass


class CatsupServer(object):
    def __init__(self, settings, port):
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.generator = Generator(settings)
        self.port = port

    @property
    def application(self):
        raise NotImplementedError()

    def prepare(self):
        pass

    def generate(self):
        self.generator.generate()

    def run(self):
        self.generate()
        self.prepare()
        application = self.application
        application.settings["log_function"] = lambda x: None
        application.settings["static_handler_class"] = StaticFileHandler
        http_server = tornado.httpserver.HTTPServer(application,
                                                    io_loop=self.ioloop)
        http_server.listen(self.port)
        logger.info("Start server at port %s" % self.port)
        self.ioloop.start()


class PreviewServer(CatsupServer):
    def __init__(self, settings, port):
        super(PreviewServer, self).__init__(settings, port)
        self.generator = Generator(
            settings,
            local=True,
            base_url="http://127.0.0.1:%s/" % port
        )

    @property
    def application(self):
        params = {
            "path": g.output,
            "default_filename": "index.html"
        }
        return tornado.web.Application([
            (r"/(.*)", StaticFileHandler, params),
        ])

    def prepare(self):
        # Reload server when catsup modified.
        tornado.autoreload.start(self.ioloop)
        tornado.autoreload.add_reload_hook(self.generate)

        event_handler = CatsupEventHandler(self.generator)
        observer = Observer()
        for path in [self.generator.config.config.source, g.theme.path]:
            path = os.path.abspath(path)
            observer.schedule(event_handler, path=path, recursive=True)
        observer.start()


class WebhookServer(CatsupServer):
    @property
    def application(self):
        git_path = ""
        for path in ["", self.generator.config.config.source]:
            path = os.path.abspath(os.path.join(
                g.cwdpath,
                path
            ))
            if os.path.exists(os.path.join(path, ".git")):
                git_path = path
                break
        if not git_path:
            logger.error("Can't find git repository.")
            exit(1)
        params = {
            "path": git_path,
            "generate": self.generate
        }
        return tornado.web.Application([
            (r"/.*?", WebhookHandler, params),
        ])

########NEW FILE########
__FILENAME__ = filters
def xmldatetime(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')

########NEW FILE########
__FILENAME__ = install
import os
import shutil
import tempfile

from catsup.logger import logger
from catsup.parser.themes import find_theme, read_theme
from catsup.utils import call, mkdir
from catsup.themes.utils import search_github

THEMES_PATH = os.path.abspath("themes")


def install_from_git(clone_url):
    mkdir(THEMES_PATH)
    os.chdir(THEMES_PATH)
    tmp_dir = tempfile.mkdtemp()
    os.system('git clone {clone_url} {tmp_dir}'.format(
        clone_url=clone_url,
        tmp_dir=tmp_dir
    ))
    theme = read_theme(tmp_dir)
    if not theme:
        logger.error("{clone_url} is not a Catsup theme repo.".format(
            clone_url=clone_url
        ))
        shutil.rmtree(tmp_dir)
    if os.path.exists(theme.name):
        shutil.rmtree(theme.name)

    shutil.move(tmp_dir, theme.name)
    logger.info("Installed theme {name}".format(name=theme.name))


def search_and_install(name):
    logger.info("Searching theme {name} on GitHub..".format(name=name))
    item = search_github(name=name)
    if not item:
        logger.error("Can't find theme {name}.".format(name=name))
        exit(1)

    logger.info("Fount {name} on GitHub.".format(name=item["name"]))
    install_from_git(item["clone_url"])


def install_theme(name):
    theme = find_theme(theme_name=name, silence=True)
    if theme:
        # Update theme
        if not os.path.exists(os.path.join(theme.path, '.git')):
            logger.warn("%s is not installed via git."
                        "Can't update it." % theme.name)
        else:
            logger.info("Updating theme %s" % theme.name)
            call("git pull", cwd=theme.path)
        exit(0)
    if ".git" in name or "//" in name:
        install_from_git(name)
    else:
        item = search_github(name)
        if not item:
            logger.error("Can't find {} on GitHub.".format(name))
            exit(1)
        install_from_git(item["clone_url"])

########NEW FILE########
__FILENAME__ = utils
import urllib2
import ujson

from catsup.logger import logger


def search_github(name):
    repo_name = "catsup-theme-{name}".format(name=name)
    url = "https://api.github.com/search/repositories?q=" + repo_name
    request = urllib2.Request(url)
    request.add_header("User-Agent", "Catsup Theme Finder")
    try:
        response = urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        logger.warning("Error when connecting to GitHub: {}".format(e.msg))
        return None
    content = response.read()
    json = ujson.loads(content)
    if json["total_count"] == 0:
        return None
    for item in json["items"]:
        if item["name"] == repo_name:
            return {
                "name": item["name"],
                "clone_url": item["clone_url"]
            }

########NEW FILE########
__FILENAME__ = utils
import os
import re
import sys
import subprocess

try:
    from urllib.parse import urljoin
    assert urljoin
except ImportError:
    from urlparse import urljoin

from tornado.util import ObjectDict

py = sys.version_info
py3k = py >= (3, 0, 0)

if py3k:
    basestring = str
    unicode = str


HTML_TAG_RE = re.compile("<.*?>")


def html_to_raw_text(html):
    return "".join(HTML_TAG_RE.split(html))


def static_url(f):
    from catsup.options import g
    caches_class = g.generator.caches["static_url"]
    if f not in caches_class:
        import os
        import hashlib

        from catsup.logger import logger

        def get_hash(path):
            path = os.path.join(g.theme.path, 'static', path)
            if not os.path.exists(path):
                logger.warn("%s does not exist." % path)
                return

            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()

        hsh = get_hash(f)
        url = urljoin(
            g.static_prefix,
            '%s?v=%s' % (f, hsh)
        )
        caches_class[f] = url
    return caches_class[f]


def url_for(obj):
    from catsup.options import g
    caches_class = g.generator.caches["url_for"]
    key = id(obj)
    if key not in caches_class:
        from catsup.models import CatsupPage

        url = ''
        if obj == 'index':
            url = g.base_url
        elif isinstance(obj, CatsupPage):
            url = obj.permalink
        elif isinstance(obj, str):
            url = g.permalink[obj]
        caches_class[key] = urljoin(
            g.base_url,
            url
        )
    return caches_class[key]


def to_unicode(value):
    if isinstance(value, unicode):
        return value
    if isinstance(value, basestring):
        return value.decode('utf-8')
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return value


def update_nested_dict(a, b):
    for k, v in b.items():
        if isinstance(v, dict):
            d = a.setdefault(k, ObjectDict())
            update_nested_dict(d, v)
        else:
            a[k] = v
    return a


def call(cmd, silence=True, **kwargs):
    from catsup.options import g
    kwargs.setdefault("cwd", g.cwdpath)
    if silence:
        kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("shell", True)
    return subprocess.call(cmd, **kwargs)


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def smart_copy(source, target):
    if not os.path.exists(source):
        return

    def copy_file(source, target):
        if os.path.exists(target):
            if os.path.getsize(source) == os.path.getsize(target):
                return
        mkdir(os.path.dirname(target))
        open(target, "wb").write(open(source, "rb").read())

    if os.path.isfile(source):
        return copy_file(source, target)

    for f in os.listdir(source):
        sourcefile = os.path.join(source, f)
        targetfile = os.path.join(target, f)
        if os.path.isfile(sourcefile):
            copy_file(sourcefile, targetfile)
        else:
            smart_copy(sourcefile, targetfile)


class Pagination(object):
    def __init__(self, page, posts, per_page, get_permalink):
        self.total_items = posts
        self.page = page
        self.per_page = per_page
        self.get_permalink = get_permalink

    def iter_pages(self, edge=4):
        if self.page <= edge:
            return range(1, min(self.pages, 2 * edge + 1) + 1)
        if self.page + edge > self.pages:
            return range(max(self.pages - 2 * edge, 1), self.pages + 1)
        return range(self.page - edge, min(self.pages, self.page + edge) + 1)

    @property
    def pages(self):
        return int((self.total - 1) / self.per_page) + 1

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def prev_permalink(self):
        return self.get_permalink(self.prev_num)

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def next_permalink(self):
        return self.get_permalink(self.next_num)

    @property
    def next_num(self):
        return self.page + 1

    @property
    def total(self):
        return len(self.total_items)

    @property
    def items(self):
        start = (self.page - 1) * self.per_page
        end = self.page * self.per_page
        return self.total_items[start:end]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# catsup documentation build configuration file, created by
# sphinx-quickstart on Fri Feb  8 17:06:00 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os
import time

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('_themes'))
sys.path.insert(0, os.path.abspath('..'))

import catsup

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Catsup'
copyright = (u'2012-%s, <a href="http://whouz.com">whtsky</a> and'
             u' <a href="https://github.com/whtsky/catsup/graphs/contributors">Other Crontributors</a>'
             % time.strftime('%Y'))

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = catsup.__version__
# The full version, including alpha/beta/rc tags.
release = catsup.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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
pygments_style = 'flask_theme_support.FlaskyStyle'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'flask'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
html_sidebars = {
    'index': ['sourcelink.html', 'sidebarintro.html', 'searchbox.html'],
    '**': ['localtoc.html', 'relations.html', 'sidebarintro.html',
           'searchbox.html']
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'catsupdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'catsup.tex', u'catsup Documentation',
   u'whtsky', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'catsup', u'Catsup Documentation',
     [u'whtsky'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'catsup', u'Catsup Documentation',
   u'whtsky', 'catsup', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = theme
name = 'test'
author = 'whtsky'
homepage = 'https://github.com/whtsky/catsup'
post_per_page = 2
vars = {}

########NEW FILE########
__FILENAME__ = test_meta_parser
from nose.tools import raises
from catsup.reader.meta import parse_meta, parse_catsup_meta, parse_yaml_meta


def test_catsup_meta_parser():
    meta_txt = """
    # Hello, world!

    - tags: hello, world
    """
    lines = [l.strip() for l in meta_txt.splitlines() if l]
    meta = parse_catsup_meta(lines)
    assert meta.title == "Hello, world!"
    assert meta.tags == "hello, world"


@raises(SystemExit)
def test_catsup_meta_parser_error_1():
    parse_catsup_meta(["fsdaf-,-,-,-", "fdsa- 0,"])


@raises(SystemExit)
def test_catsup_meta_parser_error_2():
    parse_catsup_meta(["#fsdaf-,-,-,-", "fdsa- 0,"])


def test_base_meta():
    pass


def test_meta_parser():
    meta_txt = """
    # Hello, world!

    - tags: hello, world
    """

    lines = [l.strip() for l in meta_txt.splitlines() if l]
    meta = parse_meta(lines)
    assert meta.title == "Hello, world!"
    assert meta.tags == "hello, world"


@raises(SystemExit)
def test_parse_unknown_meta():
    parse_meta(["fdsjaklfdsjaklfdsjaklfjdsklfjsa"])

########NEW FILE########
__FILENAME__ = test_parser
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

from nose.tools import raises


def test_config_parser():
    from catsup.parser.config import parse
    from catsup.utils import ObjectDict
    config = parse(os.path.join(BASE_DIR, "config.json"))
    assert config == ObjectDict({u'site': {u'url': u'http://blog.com/', u'name': u'blogname', u'description': u'Just another catsup blog'}, u'author': {u'twitter': u'twitter', u'name': u'nickname', u'email': u'name@exmaple.com'}})


@raises(SystemExit)
def test_parser_non_exist_file():
    from catsup.parser.config import parse
    parse("fd")

########NEW FILE########
__FILENAME__ = test_permalink
# -*- coding:utf-8 -*-

import os
import catsup.parser

from catsup.options import g
from catsup.reader import txt_reader

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def test_post_permalink():
    post_path = os.path.join(BASE_DIR, "post.txt")
    post = txt_reader(post_path)
    g.config = catsup.parser.config(os.path.join(BASE_DIR, "config.json"))
    g.config.permalink.post = "/{title}/"
    assert post.permalink == "/Hello,-World!/"
    g.config.permalink.post = "/{filename}/"
    assert post.permalink == "/post/"
    g.config.permalink.post = "/{date}/{title}/"
    assert post.permalink == "/2014-01-04/Hello,-World!/"
    g.config.permalink.post = "/{datetime.year}/{filename}/"
    assert post.permalink == "/2014/post/"
########NEW FILE########
__FILENAME__ = test_reader
#coding: utf-8

import os

from nose.tools import raises
from catsup.utils import to_unicode

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def test_reader_choser():
    from catsup.reader import get_reader, markdown_reader, txt_reader
    assert get_reader("md") == markdown_reader
    assert get_reader("markdown") == markdown_reader
    assert get_reader("txt") == txt_reader


@raises(SystemExit)
def test_open_unexist_file():
    from catsup.reader.utils import open_file
    open_file(">_<")


def test_txt_reader():
    import datetime
    from catsup.reader import txt_reader
    post_path = os.path.join(BASE_DIR, "post.txt")
    post = txt_reader(post_path)
    assert post.path == post_path
    assert post.date == post.datetime.strftime("%Y-%m-%d") == "2014-01-04"
    assert post.datetime == datetime.datetime(2014, 1, 4, 20, 56)
    assert post.title == "Hello, World!"
    assert post.content == to_unicode("<br />Hi!<br />I&#39;m happy to use Catsup!<br />中文测试<br />")


def test_read_txt_without_meta():
    from catsup.reader import txt_reader
    post_path = os.path.join(BASE_DIR, "no_meta.txt")
    post = txt_reader(post_path)
    assert post.title == "no_meta", post.title


def test_md_reader():
    from catsup.reader import markdown_reader
    post_path = os.path.join(BASE_DIR, "2013-02-11-test.md")
    post = markdown_reader(post_path)
    assert post.path == post_path
    assert post.date == post.datetime.strftime("%Y-%m-%d") == "2013-02-11"

########NEW FILE########
__FILENAME__ = test_theme_utils
from catsup.themes.utils import search_github


def test_search_github():
    theme = search_github("clean")
    assert theme["name"] == "catsup-theme-clean"
    assert theme["clone_url"] == "https://github.com/whtsky/catsup-theme-clean.git"

########NEW FILE########
__FILENAME__ = test_with_cli
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SITE_DIR = os.path.join(BASE_DIR, "site")

os.chdir(SITE_DIR)

from nose.tools import raises
from catsup.options import g
g.cwdpath = SITE_DIR


def output_exist(path):
    return os.path.exists(os.path.join(
        SITE_DIR,
        "deploy",
        path
    ))


def test_build():
    from catsup.cli import clean, build
    clean(settings="config.json")
    build(settings="config.json")
    assert output_exist("feed.xml")
    assert output_exist("index.html")
    assert output_exist("page.html")
    assert output_exist("sitemap.txt")
    assert output_exist("should-exist")
    assert not output_exist(".should-not-exist")


def test_init():
    from catsup.cli import init
    os.remove("config.json")
    init("./")


@raises(SystemExit)
def test_reinit():
    from catsup.cli import init
    init("./")


def test_generate_without_post():
    from catsup.cli import clean, build
    clean(settings="config2.json")
    build(settings="config2.json")
    assert not output_exist("page.html")

########NEW FILE########
