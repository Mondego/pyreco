__FILENAME__ = command
"""\
grip.command
~~~~~~~~~~~~

Implements the command-line interface for Grip.


Usage:
  grip [options] [<path>] [<address>]
  grip -h | --help
  grip --version

Where:
  <path> is a file to render or a directory containing a README.md file
  <address> is what to listen on, of the form <host>[:<port>], or just <port>

Options:
  --gfm             Use GitHub-Flavored Markdown, e.g. comments or issues
  --context=<repo>  The repository context, only taken into account with --gfm
  --user=<username> A GitHub username for API authentication
  --pass=<password> A GitHub password for API authentication
  --export          Exports to <path>.html or README.md instead of serving
"""

import sys
from path_and_address import resolve, split_address
from docopt import docopt
from .server import serve
from .exporter import export
from . import __version__


usage = '\n\n\n'.join(__doc__.split('\n\n\n')[1:])


def main(argv=None):
    """The entry point of the application."""
    if argv is None:
        argv = sys.argv[1:]
    version = 'Grip ' + __version__

    # Parse options
    args = docopt(usage, argv=argv, version=version)

    # Parse arguments
    path, address = resolve(args['<path>'], args['<address>'])
    host, port = split_address(address)

    # Export to a file instead of running a server
    if args['--export']:
        try:
            export(path, args['--gfm'], args['--context'],
                  args['--user'], args['--pass'], False)
            return 0
        except ValueError as ex:
            print('Error:', ex)
            return 1

    # Validate address
    if address and not host and not port:
        print('Error: Invalid address', repr(address))

    # Run server
    try:
        serve(path, host, port, args['--gfm'], args['--context'],
              args['--user'], args['--pass'], False)
        return 0
    except ValueError as ex:
        print('Error:', ex)
        return 1

########NEW FILE########
__FILENAME__ = exporter
import io
import os
from .server import create_app
from .renderer import render_app


def export(path=None, gfm=False, context=None, username=None, password=None,
           render_offline=False, out_filename=None):
    """Exports the rendered HTML to a file."""
    app = create_app(path, gfm, context, username, password, render_offline,
                     render_inline=True)

    if out_filename is None:
        out_filename = os.path.splitext(app.config['GRIP_FILE'])[0] + '.html'
    print('Exporting to', out_filename)

    content = render_app(app)
    with io.open(out_filename, 'w', encoding='utf-8') as f:
        f.write(content)

########NEW FILE########
__FILENAME__ = github_renderer
from flask import abort, json
import requests


def render_content(text, gfm=False, context=None, username=None, password=None):
    """Renders the specified markup using the GitHub API."""
    if gfm:
        url = 'https://api.github.com/markdown'
        data = {'text': text, 'mode': 'gfm', 'context': context}
        if context:
            data['context'] = context
        data = json.dumps(data)
    else:
        url = 'https://api.github.com/markdown/raw'
        data = text
    headers = {'content-type': 'text/plain'}
    auth = (username, password) if username else None

    r = requests.post(url, headers=headers, data=data, auth=auth)

    # Relay HTTP errors
    if r.status_code != 200:
        try:
            message = r.json()['message']
        except:
            message = r.text
        abort(r.status_code, message)

    return r.text

########NEW FILE########
__FILENAME__ = mdx_urlize
"""A more liberal autolinker

Inspired by Django's urlize function.

Positive examples:

>>> import markdown
>>> md = markdown.Markdown(extensions=['urlize'])

>>> md.convert('http://example.com/')
u'<p><a href="http://example.com/">http://example.com/</a></p>'

>>> md.convert('go to http://example.com')
u'<p>go to <a href="http://example.com">http://example.com</a></p>'

>>> md.convert('example.com')
u'<p><a href="http://example.com">example.com</a></p>'

>>> md.convert('example.net')
u'<p><a href="http://example.net">example.net</a></p>'

>>> md.convert('www.example.us')
u'<p><a href="http://www.example.us">www.example.us</a></p>'

>>> md.convert('(www.example.us/path/?name=val)')
u'<p>(<a href="http://www.example.us/path/?name=val">www.example.us/path/?name=val</a>)</p>'

>>> md.convert('go to <http://example.com> now!')
u'<p>go to <a href="http://example.com">http://example.com</a> now!</p>'

Negative examples:

>>> md.convert('del.icio.us')
u'<p>del.icio.us</p>'

"""

import markdown

# Global Vars
URLIZE_RE = '(%s)' % '|'.join([
    r'<(?:f|ht)tps?://[^>]*>',
    r'\b(?:f|ht)tps?://[^)<>\s]+[^.,)<>\s]',
    r'\bwww\.[^)<>\s]+[^.,)<>\s]',
    r'[^(<\s]+\.(?:com|net|org)\b',
])

class UrlizePattern(markdown.inlinepatterns.Pattern):
    """ Return a link Element given an autolink (`http://example/com`). """
    def handleMatch(self, m):
        url = m.group(2)
        
        if url.startswith('<'):
            url = url[1:-1]
            
        text = url
        
        if not url.split('://')[0] in ('http','https','ftp'):
            if '@' in url and not '/' in url:
                url = 'mailto:' + url
            else:
                url = 'http://' + url
    
        el = markdown.util.etree.Element("a")
        el.set('href', url)
        el.text = markdown.util.AtomicString(text)
        return el

class UrlizeExtension(markdown.Extension):
    """ Urlize Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Replace autolink with UrlizePattern """
        md.inlinePatterns['autolink'] = UrlizePattern(URLIZE_RE, md)

def makeExtension(configs=None):
    return UrlizeExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = offline_renderer
import markdown
from .mdx_urlize import UrlizeExtension


def render_content(text, gfm=False, context=None):
    """Renders the specified markup locally."""
    return markdown.markdown(text, extensions=[
        'fenced_code', 
        'codehilite(css_class=highlight)',
        UrlizeExtension(),
    ])

########NEW FILE########
__FILENAME__ = renderer
from jinja2 import Environment, PackageLoader
from flask import make_response
from .github_renderer import render_content as github_render
from .offline_renderer import render_content as offline_render


# Get jinja templates
env = Environment(loader=PackageLoader('grip', 'templates'))
index_template = env.get_template('index.html')


def render_app(app, route='/'):
    """Renders the markup at the specified app route."""
    with app.test_client() as c:
        response = c.get('/')
        encoding = response.charset
        return response.data.decode(encoding)


def render_content(text, gfm=False, context=None,
                   username=None, password=None, render_offline=False):
    """Renders the specified markup and returns the result."""
    if render_offline:
        return offline_render(text, gfm, context)
    return github_render(text, gfm, context, username, password)


def render_page(text, filename=None, gfm=False, context=None,
                username=None, password=None, render_offline=False,
                style_urls=[], styles=[]):
    """Renders the specified markup text to an HTML page."""
    content = render_content(text, gfm, context, username, password, render_offline)
    return index_template.render(content=content, filename=filename,
                                 style_urls=style_urls, styles=styles)


def render_image(image_data, content_type):
    """Renders the specified image data with the given Content-Type."""
    response = make_response(image_data)
    response.headers['Content-Type'] = content_type
    return response

########NEW FILE########
__FILENAME__ = server
import os
import re
import errno
import mimetypes
import requests
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
from traceback import format_exc
from flask import Flask, safe_join, abort, url_for, send_from_directory
from .renderer import render_page, render_image


default_filenames = ['README.md', 'README.markdown']


def create_app(path=None, gfm=False, context=None, username=None, password=None,
               render_offline=False, render_inline=False):
    """Starts a server to render the specified file or directory containing a README."""
    if not path or os.path.isdir(path):
        path = _find_file(path)

    if not os.path.exists(path):
        raise ValueError('File not found: ' + path)

    # Flask application
    app = Flask(__name__)
    app.config.from_pyfile('settings.py')
    app.config.from_pyfile('settings_local.py', silent=True)
    app.config['GRIP_FILE'] = os.path.normpath(path)

    # Setup style cache
    if app.config['STYLE_CACHE_DIRECTORY']:
        style_cache_path = os.path.join(app.instance_path, app.config['STYLE_CACHE_DIRECTORY'])
        if not os.path.exists(style_cache_path):
            os.makedirs(style_cache_path)
    else:
        style_cache_path = None

    # Get initial styles
    style_urls = list(app.config['STYLE_URLS'] or [])
    styles = []

    # Get styles from style source
    @app.before_first_request
    def retrieve_styles():
        """Retrieves the style URLs from the source and caches them, if requested."""
        if not app.config['STYLE_URLS_SOURCE'] or not app.config['STYLE_URLS_RE']:
            return

        # Get style URLs from the source HTML page
        retrieved_urls = _get_style_urls(app.config['STYLE_URLS_SOURCE'],
                                         app.config['STYLE_URLS_RE'],
                                         style_cache_path,
                                         app.config['DEBUG_GRIP'])
        style_urls.extend(retrieved_urls)

        if render_inline:
            styles.extend(_get_styles(app, style_urls))
            style_urls[:] = []

    # Views
    @app.route('/')
    @app.route('/<path:filename>')
    def render(filename=None):
        if filename is not None:
            filename = safe_join(os.path.dirname(app.config['GRIP_FILE']), filename)
            if os.path.isdir(filename):
                try:
                    filename = _find_file(filename)
                except ValueError:
                    abort(404)

            # if we think this file is an image, we need to read it in
            # binary mode and serve it as such
            mimetype, _ = mimetypes.guess_type(filename)
            is_image = mimetype.startswith('image/') if mimetype else False

            try:
                text = _read_file(filename, is_image)
            except IOError as ex:
                if ex.errno != errno.ENOENT:
                    raise
                return abort(404)

            if is_image:
                return render_image(text, mimetype)
        else:
            filename = app.config['GRIP_FILE']
            text = _read_file(app.config['GRIP_FILE'])
        return render_page(text, filename, gfm, context,
                           username, password, render_offline, style_urls, styles)

    @app.route('/cache/<path:filename>')
    def render_cache(filename=None):
        return send_from_directory(style_cache_path, filename)

    return app


def serve(path=None, host=None, port=None, gfm=False, context=None,
          username=None, password=None, render_offline=False):
    """Starts a server to render the specified file or directory containing a README."""
    app = create_app(path, gfm, context, username, password, render_offline)

    # Set overridden config values
    if host is not None:
        app.config['HOST'] = host
    if port is not None:
        app.config['PORT'] = port

    # Run local server
    app.run(app.config['HOST'], app.config['PORT'], debug=app.debug,
        use_reloader=app.config['DEBUG_GRIP'])


def _get_style_urls(source_url, pattern, style_cache_path, debug=False):
    """Gets the specified resource and parses all style URLs in the form of the specified pattern."""
    try:
        # TODO: Add option to clear the cached styles
        # Skip fetching styles if there's any already cached
        if style_cache_path:
            cached = _get_cached_style_urls(style_cache_path)
            if cached:
                return cached

        # Find style URLs
        r = requests.get(source_url)
        if not 200 <= r.status_code < 300:
            print(' * Warning: retrieving styles gave status code', r.status_code)
        urls = re.findall(pattern, r.text)

        # Cache the styles
        if style_cache_path:
            _cache_contents(urls, style_cache_path)
            urls = _get_cached_style_urls(style_cache_path)

        return urls
    except Exception as ex:
        if debug:
            print(format_exc())
        else:
            print(' * Error: could not retrieve styles:', str(ex))
        return []


def _get_styles(app, style_urls):
    """Gets the content of the given list of style URLs."""
    styles = []
    for style_url in style_urls:
        if not urlparse(style_urls[0]).netloc:
            with app.test_client() as c:
                response = c.get(style_url)
                encoding = response.charset
                content = response.data.decode(encoding)
        else:
            content = requests.get(style_url).text
        styles.append(content)
    return styles


def _get_cached_style_urls(style_cache_path):
    """Gets the URLs of the cached styles."""
    cached_styles = os.listdir(style_cache_path)
    return [url_for('render_cache', filename=style) for style in cached_styles]


def _find_file(path):
    """Gets the full path and extension of the specified."""
    if path is None:
        path = '.'
    for filename in default_filenames:
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            return full_path
    raise ValueError('No README found at ' + path)


def _read_file(filename, read_as_binary=False):
    """Reads the contents of the specified file."""
    mode = "rb" if read_as_binary else "r"
    with open(filename, mode) as f:
        return f.read()


def _write_file(filename, contents):
    """Creates the specified file and writes the given contents to it."""
    with open(filename, 'wb') as f:
        f.write(contents.encode('utf-8'))


def _cache_contents(urls, style_cache_path):
    """Fetches the given URLs and caches their contents in the given directory."""
    for url in urls:
        basename = url.rsplit('/', 1)[-1]
        filename = os.path.join(style_cache_path, basename)
        contents = requests.get(url).text
        _write_file(filename, contents)
        print(' * Downloaded', url)

########NEW FILE########
__FILENAME__ = settings
"""\
Default Configuration

Do NOT change the values here for risk of accidentally committing them.
Override them using command-line arguments or with a settings_local.py instead.
"""

HOST = 'localhost'
PORT = 5000
DEBUG = True


DEBUG_GRIP = False
STYLE_URLS = []
STYLE_URLS_SOURCE = 'https://github.com/joeyespo/grip'
STYLE_URLS_RE = '<link.+href=[\'"]?([^\'" >]+)[\'"]?.+media=[\'"]?(?:screen|all)[\'"]?.+rel=[\'"]?stylesheet[\'"]?.+/>'
STYLE_CACHE_DIRECTORY = 'style-cache'

########NEW FILE########
