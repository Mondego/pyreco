__FILENAME__ = cloudfiles
import cloudfiles

from django.core.exceptions import ImproperlyConfigured

from mediasync.backends import BaseClient
from mediasync.conf import msettings


class Client(BaseClient):

    def __init__(self, *args, **kwargs):
        "Set up the CloudFiles connection and grab the container."
        super(Client, self).__init__(*args, **kwargs)

        container_name = msettings['CLOUDFILES_CONTAINER']
        username = msettings['CLOUDFILES_USERNAME']
        key = msettings['CLOUDFILES_API_KEY']

        if not container_name:
            raise ImproperlyConfigured("CLOUDFILES_CONTAINER is a required setting.")

        if not username:
            raise ImproperlyConfigured("CLOUDFILES_USERNAME is a required setting.")

        if not key:
            raise ImproperlyConfigured("CLOUDFILES_API_KEY is a required setting.")

        self.conn = cloudfiles.get_connection(username, key)
        self.container = self.conn.create_container(container_name)

        if not self.container.is_public():
            self.container.make_public()

    def remote_media_url(self, with_ssl=False):
        "Grab the remote URL for the contianer."
        if with_ssl:
            raise UserWarning("""Rackspace CloudFiles does not yet support SSL.
                    See http://bit.ly/hYV502 for more info.""")
        return self.container.public_uri()

    def put(self, filedata, content_type, remote_path, force=False):

        obj = self.container.create_object(remote_path)
        obj.content_type = content_type
        obj.write(filedata)

        return True

########NEW FILE########
__FILENAME__ = dummy
from mediasync.backends import BaseClient

class Client(BaseClient):
    
    remote_media_url_callback = lambda x: "dummy://"
    put_callback = lambda x: None
    
    def remote_media_url(self, with_ssl=False):
        return self.remote_media_url_callback()
    
    def put(self, *args, **kwargs):
        self.put_callback(*args)
########NEW FILE########
__FILENAME__ = s3
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.core.exceptions import ImproperlyConfigured
from mediasync import TYPES_TO_COMPRESS
from mediasync.backends import BaseClient
from mediasync.conf import msettings
import mediasync
import datetime

class Client(BaseClient):

    def __init__(self, *args, **kwargs):
        super(Client, self).__init__(*args, **kwargs)
        
        self.aws_bucket = msettings['AWS_BUCKET']
        self.aws_prefix = msettings.get('AWS_PREFIX', '').strip('/')
        self.aws_bucket_cname =  msettings.get('AWS_BUCKET_CNAME', False)
        
        assert self.aws_bucket
    
    def supports_gzip(self):
        return msettings.get('AWS_GZIP', True)
    
    def get_connection(self):
        return self._conn
    
    def open(self):    
        
        key = msettings['AWS_KEY']
        secret = msettings['AWS_SECRET']
        
        try:
            self._conn = S3Connection(key, secret)
        except AttributeError:
            raise ImproperlyConfigured("S3 keys not set and no boto config found.")
                
        self._bucket = self._conn.create_bucket(self.aws_bucket)
    
    def close(self):
        self._bucket = None
        self._conn = None
    
    def remote_media_url(self, with_ssl=False):
        """
        Returns the base remote media URL. In this case, we can safely make
        some assumptions on the URL string based on bucket names, and having
        public ACL on.
        
        args:
          with_ssl: (bool) If True, return an HTTPS url.
        """
        protocol = 'http' if with_ssl is False else 'https'
        url = (self.aws_bucket_cname and "%s://%s" or "%s://s3.amazonaws.com/%s") % (protocol, self.aws_bucket)
        if self.aws_prefix:
            url = "%s/%s" % (url, self.aws_prefix)
        return url

    def put(self, filedata, content_type, remote_path, force=False):

        now = datetime.datetime.utcnow()
        then = now + datetime.timedelta(self.expiration_days)
        expires = then.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        if self.aws_prefix:
            remote_path = "%s/%s" % (self.aws_prefix, remote_path)
            
        (hexdigest, b64digest) = mediasync.checksum(filedata)
        raw_b64digest = b64digest # store raw b64digest to add as file metadata

        # create initial set of headers
        headers = {
            "x-amz-acl": "public-read",
            "Content-Type": content_type,
            "Expires": expires,
            "Cache-Control": 'max-age=%d, public' % (self.expiration_days * 24 * 3600),
        }
        
        key = self._bucket.get_key(remote_path)
        
        if key is None:
            key = Key(self._bucket, remote_path)
        
        key_meta = key.get_metadata('mediasync-checksum') or ''
        s3_checksum = key_meta.replace(' ', '+')
        if force or s3_checksum != raw_b64digest:
            
            key.set_metadata('mediasync-checksum', raw_b64digest)
            key.set_contents_from_string(filedata, headers=headers, md5=(hexdigest, b64digest))
        
            # check to see if file should be gzipped based on content_type
            # also check to see if filesize is greater than 1kb
            if content_type in TYPES_TO_COMPRESS:
                # Use a .gzt extension to avoid issues with Safari on OSX
                key = Key(self._bucket, "%s.gzt" % remote_path)
                
                filedata = mediasync.compress(filedata)
                (hexdigest, b64digest) = mediasync.checksum(filedata) # update checksum with compressed data
                headers["Content-Disposition"] = 'inline; filename="%sgzt"' % remote_path.split('/')[-1]
                headers["Content-Encoding"] = 'gzip'
                
                key.set_metadata('mediasync-checksum', raw_b64digest)
                key.set_contents_from_string(filedata, headers=headers, md5=(hexdigest, b64digest))
            
            return True

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings
from mediasync.processors import slim

_settings = {
    'CSS_PATH': '',
    'DEFAULT_MIMETYPE': 'application/octet-stream',
    'DOCTYPE': 'html5',
    'EMULATE_COMBO': False,
    'EXPIRATION_DAYS': 365,
    'JOINED': {},
    'JS_PATH': '',
    'STATIC_ROOT': getattr(settings, 'STATIC_ROOT', None) or
                   getattr(settings, 'MEDIA_ROOT', None),
    'STATIC_URL': getattr(settings, 'STATIC_URL', None) or
                  getattr(settings, 'MEDIA_URL', None),
    'PROCESSORS': (slim.css_minifier, slim.js_minifier),
    'SERVE_REMOTE': not settings.DEBUG,
    'URL_PROCESSOR': lambda x: x,
}

class Settings(object):
    
    def __init__(self, conf):
        for k, v in conf.iteritems():
            self[k] = v
    
    def __delitem__(self, name):
        del _settings[name]
    
    def __getitem__(self, name):
        return self.get(name)
    
    def __setitem__(self, name, val):
        _settings[name] = val
        
    def __str__(self):
        return repr(_settings)
    
    def get(self, name, default=None):
        return _settings.get(name, default)

msettings = Settings(settings.MEDIASYNC)

########NEW FILE########
__FILENAME__ = syncmedia
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from mediasync.conf import msettings
import mediasync

class Command(BaseCommand):
    
    help = "Sync local media with remote client"
    args = '[options]'
    
    requires_model_validation = False
    
    option_list = BaseCommand.option_list + (
        make_option("-F", "--force", dest="force", help="force files to sync", action="store_true"),
    )
    
    def handle(self, *args, **options):
        
        msettings['SERVE_REMOTE'] = True
        
        force = options.get('force') or False
        
        try:
            mediasync.sync(force=force)
        except ValueError, ve:
            raise CommandError('%s\nUsage is mediasync %s' % (ve.message, self.args))
########NEW FILE########
__FILENAME__ = models
# no models!
########NEW FILE########
__FILENAME__ = closurecompiler
from mediasync import JS_MIMETYPES
from urllib import urlencode
import httplib

HEADERS = {"content-type": "application/x-www-form-urlencoded"}

def compile(filedata, content_type, remote_path, is_active):
    
    is_js = (content_type in JS_MIMETYPES or remote_path.lower().endswith('.js'))
    
    if is_js:
        
        params = urlencode({
            'js_code': filedata,
            'compilation_level': 'SIMPLE_OPTIMIZATIONS',
            'output_info': 'compiled_code',
            'output_format': 'text',
        })

        conn = httplib.HTTPConnection('closure-compiler.appspot.com')
        conn.request('POST', '/compile', params, HEADERS)
        response = conn.getresponse()
        data = response.read()
        conn.close
        
        return data
########NEW FILE########
__FILENAME__ = slim
try:
    import slimmer
    SLIMMER_INSTALLED = True
except ImportError:
    SLIMMER_INSTALLED = False

def css_minifier(filedata, content_type, remote_path, is_active):
    is_css = content_type == 'text/css' or remote_path.lower().endswith('.css')
    if SLIMMER_INSTALLED and is_active and is_css:
        return slimmer.css_slimmer(filedata)

def js_minifier(filedata, content_type, remote_path, is_active):
    is_js = content_type == 'text/javascript' or remote_path.lower().endswith('.js')
    if SLIMMER_INSTALLED and is_active and is_js:
        return slimmer.css_slimmer(filedata)

########NEW FILE########
__FILENAME__ = yuicompressor
from django.conf import settings
from mediasync import CSS_MIMETYPES, JS_MIMETYPES
import os
from subprocess import Popen, PIPE

def _yui_path(settings):
    if not hasattr(settings, 'MEDIASYNC'):
        return None
    path = settings.MEDIASYNC.get('YUI_COMPRESSOR_PATH', None)
    if path:
        path = os.path.realpath(os.path.expanduser(path))
    return path

def css_minifier(filedata, content_type, remote_path, is_active):
    is_css = (content_type in CSS_MIMETYPES or remote_path.lower().endswith('.css'))
    yui_path = _yui_path(settings)
    if is_css and yui_path and is_active:
        proc = Popen(['java', '-jar', yui_path, '--type', 'css'], stdout=PIPE,
                     stderr=PIPE, stdin=PIPE)
        stdout, stderr = proc.communicate(input=filedata)
        return str(stdout)

def js_minifier(filedata, content_type, remote_path, is_active):
    is_js = (content_type in JS_MIMETYPES or remote_path.lower().endswith('.js'))
    yui_path = _yui_path(settings)
    if is_js and yui_path and is_active:
        proc = Popen(['java', '-jar', yui_path, '--type', 'js'], stdout=PIPE,
                     stderr=PIPE, stdin=PIPE)
        stdout, stderr = proc.communicate(input=filedata)
        return str(stdout)

########NEW FILE########
__FILENAME__ = signals
from django.core import management
from django.core.management.base import CommandError
from django.dispatch import Signal
from mediasync import SyncException, listdir_recursive
from mediasync.conf import msettings
import os
import subprocess

pre_sync = Signal()
post_sync = Signal()

def collectstatic_receiver(sender, **kwargs):
    try:
        management.call_command('collectstatic')
    except CommandError:
        raise SyncException("collectstatic management command not found")

def sass_receiver(sender, **kwargs):
    
    sass_cmd = msettings.get("SASS_COMMAND", "sass")
    
    root = msettings['STATIC_ROOT']
    
    for filename in listdir_recursive(root):
        
        if filename.endswith('.sass') or filename.endswith('.scss'):
            
            sass_path = os.path.join(root, filename)
            css_path = sass_path[:-4] + "css"
            
            cmd = "%s %s %s" % (sass_cmd, sass_path, css_path)
            subprocess.call(cmd.split(' '))
########NEW FILE########
__FILENAME__ = media
from django import template
from mediasync import backends
from mediasync.conf import msettings
import mediasync
import mimetypes

# Instance of the backend you configured in settings.py.
client = backends.client()

register = template.Library()

class BaseTagNode(template.Node):
    """
    Base class for all mediasync nodes.
    """
    def __init__(self, path):
        super(BaseTagNode, self).__init__()
        # This is the filename or path+filename supplied by the template call.
        self.path = path

    def is_secure(self, context):
        """
        Looks at the RequestContext object and determines if this page is
        secured with SSL. Linking unencrypted media on an encrypted page will
        show a warning icon on some browsers. We need to be able to serve from
        an encrypted source for encrypted pages, if our backend supports it.
        'django.core.context_processors.request' must be added to
        TEMPLATE_CONTEXT_PROCESSORS in settings.py.
        """
        return 'request' in context and context['request'].is_secure()
    
    def supports_gzip(self, context):
        """
        Looks at the RequestContext object and determines if the client
        supports gzip encoded content. If the client does, we will send them
        to the gzipped version of files that are allowed to be compressed.
        Clients without gzip support will be served the original media.
        """
        if 'request' in context and client.supports_gzip():
            enc = context['request'].META.get('HTTP_ACCEPT_ENCODING', '')
            return 'gzip' in enc and msettings['SERVE_REMOTE']
        return False

    def get_media_url(self, context):
        """
        Checks to see whether to use the normal or the secure media source,
        depending on whether the current page view is being sent over SSL.
        The USE_SSL setting can be used to force HTTPS (True) or HTTP (False).
        
        NOTE: Not all backends implement SSL media. In this case, they'll just
        return an unencrypted URL.
        """
        use_ssl = msettings['USE_SSL']
        is_secure = use_ssl if use_ssl is not None else self.is_secure(context)
        return client.media_url(with_ssl=True) if is_secure else client.media_url()

    def mkpath(self, url, path, filename=None, gzip=False):
        """
        Assembles various components to form a complete resource URL.
        
        args:
          url: (str) A base media URL.
          path: (str) The path on the host (specified in 'url') leading up
                      to the file.
          filename: (str) The file name to serve.
          gzip: (bool) True if client should receive *.gzt version of file.
        """
        if path:
            url = "%s/%s" % (url.rstrip('/'), path.strip('/'))

        if filename:
            url = "%s/%s" % (url, filename.lstrip('/'))
        
        content_type = mimetypes.guess_type(url)[0]
        if gzip and content_type in mediasync.TYPES_TO_COMPRESS:
            url = "%s.gzt" % url

        cb = msettings['CACHE_BUSTER']
        if cb:
            # Cache busters help tell the client to re-download the file after
            # a change. This can either be a callable or a constant defined
            # in settings.py.
            cb_val = cb(url) if callable(cb) else cb
            url = "%s?%s" % (url, cb_val)

        return msettings['URL_PROCESSOR'](url)
    
    def resolve_path(self, context):
        if self.path:
            try:
                path = template.Variable(self.path).resolve(context)
            except template.VariableDoesNotExist:
                path = self.path
            return path

def get_path_from_tokens(token):
    """
    Just yanks the path out of a list of template tokens. Ignores any
    additional arguments.
    """
    tokens = token.split_contents()

    if len(tokens) > 1:
        # At least one argument. Only interested in the path, though.
        return tokens[1].strip("\"'")
    else:
        # No path provided in the tag call.
        return None

def media_url_tag(parser, token):
    """
    If msettings['SERVE_REMOTE'] == False, returns your STATIC_URL. 
    When msettings['SERVE_REMOTE'] == True, returns your storage 
    backend's remote URL (IE: S3 URL). 
    
    If an argument is provided with the tag, it will be appended on the end
    of your media URL.
    
    *NOTE:* This tag returns a URL, not any kind of HTML tag.
    
    Usage:: 
    
        {% media_url ["path/and/file.ext"] %}
    
    Examples::
    
        {% media_url %}
        {% media_url "images/bunny.gif" %}
        {% media_url %}/themes/{{ theme_variable }}/style.css
    """
    return MediaUrlTagNode(get_path_from_tokens(token))
register.tag('media_url', media_url_tag)

class MediaUrlTagNode(BaseTagNode):
    """
    Node for the {% media_url %} tag. See the media_url_tag method above for
    documentation and examples.
    """
    def render(self, context):
        path = self.resolve_path(context)
        media_url = self.get_media_url(context)

        if not path:
            # No path provided, just return the base media URL.
            return media_url
        else:
            # File/path provided, return the assembled URL.
            return self.mkpath(media_url, path, gzip=self.supports_gzip(context))

"""
# CSS related tags
"""

def css_tag(parser, token):
    """
    Renders a tag to include the stylesheet. It takes an optional second 
    parameter for the media attribute; the default media is "screen, projector".
    
    Usage::

        {% css "<somefile>.css" ["<projection type(s)>"] %}

    Examples::

        {% css "myfile.css" %}
        {% css "myfile.css" "screen, projection"%}
    """
    path = get_path_from_tokens(token)

    tokens = token.split_contents()
    if len(tokens) > 2:
        # Get the media types from the tag call provided by the user.
        media_type = tokens[2][1:-1]
    else:
        # Default values.
        media_type = "screen, projection"

    return CssTagNode(path, media_type=media_type)
register.tag('css', css_tag)

def css_print_tag(parser, token):
    """
    Shortcut to render CSS as a print stylesheet.
    
    Usage::
    
        {% css_print "myfile.css" %}
        
    Which is equivalent to
    
        {% css "myfile.css" "print" %}
    """
    path = get_path_from_tokens(token)
    # Hard wired media type, since this is for media type of 'print'.
    media_type = "print"

    return CssTagNode(path, media_type=media_type)
register.tag('css_print', css_print_tag)

class CssTagNode(BaseTagNode):
    """
    Node for the {% css %} tag. See the css_tag method above for
    documentation and examples.
    """
    def __init__(self, *args, **kwargs):
        super(CssTagNode, self).__init__(*args)
        self.media_type = kwargs.get('media_type', "screen, projection")

    def render(self, context):
        path = self.resolve_path(context)
        media_url = self.get_media_url(context)
        css_path = msettings['CSS_PATH']
        joined = msettings['JOINED']
        
        if msettings['SERVE_REMOTE'] and path in joined:
            # Serving from S3/Cloud Files.
            return self.linktag(media_url, css_path, path, self.media_type, context)
        elif not msettings['SERVE_REMOTE'] and msettings['EMULATE_COMBO']:
            # Don't split the combo file into its component files. Emulate
            # the combo behavior, but generate/serve it locally. Useful for
            # testing combo CSS before deploying.
            return self.linktag(media_url, css_path, path, self.media_type, context)
        else:
            # If this is a combo file seen in the JOINED key on the
            # MEDIASYNC dict, break it apart into its component files and
            # write separate <link> tags for each.
            filenames = joined.get(path, (path,))
            return ' '.join((self.linktag(media_url, css_path, fn, self.media_type, context) for fn in filenames))

    def linktag(self, url, path, filename, media, context):
        """
        Renders a <link> tag for the stylesheet(s).
        """
        if msettings['DOCTYPE'] == 'xhtml':
            markup = """<link rel="stylesheet" href="%s" type="text/css" media="%s" />"""
        elif msettings['DOCTYPE'] == 'html5':
            markup = """<link rel="stylesheet" href="%s" media="%s">"""
        else:
            markup = """<link rel="stylesheet" href="%s" type="text/css" media="%s">"""
        return markup % (self.mkpath(url, path, filename, gzip=self.supports_gzip(context)), media)

"""
# JavaScript related tags
"""

def js_tag(parser, token):
    """
    Renders a tag to include a JavaScript file.
    
    Usage::
    
        {% js "somefile.js" %}
        
    """
    return JsTagNode(get_path_from_tokens(token))
register.tag('js', js_tag)

class JsTagNode(BaseTagNode):
    """
    Node for the {% js %} tag. See the js_tag method above for
    documentation and examples.
    """
    def render(self, context):
        path = self.resolve_path(context)
        media_url = self.get_media_url(context)
        js_path = msettings['JS_PATH']
        joined = msettings['JOINED']

        if msettings['SERVE_REMOTE'] and path in joined:
            # Serving from S3/Cloud Files.
            return self.scripttag(media_url, js_path, path, context)
        elif not msettings['SERVE_REMOTE'] and msettings['EMULATE_COMBO']:
            # Don't split the combo file into its component files. Emulate
            # the combo behavior, but generate/serve it locally. Useful for
            # testing combo JS before deploying.
            return self.scripttag(media_url, js_path, path, context)
        else:
            # If this is a combo file seen in the JOINED key on the
            # MEDIASYNC dict, break it apart into its component files and
            # write separate <link> tags for each.
            filenames = joined.get(path, (path,))
            return ' '.join((self.scripttag(media_url, js_path, fn, context) for fn in filenames))

    def scripttag(self, url, path, filename, context):
        """
        Renders a <script> tag for the JS file(s).
        """
        if msettings['DOCTYPE'] == 'html5':
            markup = """<script src="%s"></script>"""
        else:
            markup = """<script type="text/javascript" charset="utf-8" src="%s"></script>"""
        return markup % self.mkpath(url, path, filename, gzip=self.supports_gzip(context))

########NEW FILE########
__FILENAME__ = models
# no models, but needed for tests.py
########NEW FILE########
__FILENAME__ = settings
import os
TEST_ROOT = os.path.abspath(os.path.dirname(__file__))

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'mediasynctest.db'

STATIC_ROOT = os.path.join(TEST_ROOT, 'media')
STATIC_URL = '/media/'

MEDIASYNC = {
    'BACKEND': 'mediasync.backends.dummy',
}

INSTALLED_APPS = ('mediasync','mediasync.tests',)

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver
from django.template import Context, Template
from hashlib import md5
import glob
import httplib
import itertools
import os
import re
import time
import unittest

from mediasync import backends, JS_MIMETYPES, listdir_recursive
from mediasync.backends import BaseClient
from mediasync.conf import msettings
from mediasync.signals import pre_sync, post_sync, sass_receiver
import mediasync
import mimetypes

PWD = os.path.abspath(os.path.dirname(__file__))

EXPIRES_RE = re.compile(r'^\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2} GMT$')

def readfile(path):
    f = open(path, 'r')
    content = f.read()
    f.close()
    return content

class Client(BaseClient):
    
    def __init__(self, *args, **kwargs):
        super(Client, self).__init__(*args, **kwargs)
    
    def put(self, filedata, content_type, remote_path, force=False):
        if hasattr(self, 'put_callback'):
            return self.put_callback(filedata, content_type, remote_path, force)
        else:
            return True
        
    def remote_media_url(self, with_ssl=False):
        return ('https' if with_ssl else 'http') + "://localhost"

#
# tests
#

class BackendTestCase(unittest.TestCase):
    
    def setUp(self):
        msettings['BACKEND'] = 'not.a.backend'
        
    def tearDown(self):
        msettings['BACKEND'] = 'mediasync.backends.dummy'

    def testInvalidBackend(self):
        self.assertRaises(ImproperlyConfigured, backends.client)

class MockClientTestCase(unittest.TestCase):
    
    def setUp(self):
        msettings['BACKEND'] = 'mediasync.tests.tests'
        msettings['PROCESSORS'] = []
        msettings['SERVE_REMOTE'] = True
        msettings['JOINED'] = {
            'css/joined.css': ('css/1.css', 'css/2.css'),
            'js/joined.js': ('js/1.js', 'js/2.js'),
        }
        self.client = backends.client()
    
    def tearDown(self):
        msettings['JOINED'] = {}
    
    def testLocalMediaURL(self):
        self.assertEqual(self.client.get_local_media_url(), "/media/")
    
    def testMediaRoot(self):
        root = getattr(settings, 'STATIC_ROOT', None)
        if root is None:
            root = getattr(settings, 'MEDIA_ROOT', None)
        self.assertEqual(self.client.get_media_root(), root)
    
    def testMediaURL(self):
        self.assertEqual(self.client.media_url(with_ssl=False), "http://localhost")
        self.assertEqual(self.client.media_url(with_ssl=True), "https://localhost")
    
    def testSyncableDir(self):
        # not syncable
        self.assertFalse(mediasync.is_syncable_dir(".test"))
        self.assertFalse(mediasync.is_syncable_dir("_test"))
        # syncable
        self.assertTrue(mediasync.is_syncable_dir("test"))
        self.assertTrue(mediasync.is_syncable_dir("1234"))
    
    def testSyncableFile(self):
        # not syncable
        self.assertFalse(mediasync.is_syncable_file(".test"))
        self.assertFalse(mediasync.is_syncable_file("_test"))
        # syncable
        self.assertTrue(mediasync.is_syncable_file("test"))
        self.assertTrue(mediasync.is_syncable_file("1234"))
    
    def testDirectoryListing(self):
        allowed_files = [
            'css/1.css',
            'css/2.css',
            'css/3.scss',
            'img/black.png',
            'js/1.js',
            'js/2.js',
        ]
        media_dir = os.path.join(PWD, 'media')
        listed_files = list(mediasync.listdir_recursive(media_dir))
        self.assertListEqual(allowed_files, listed_files)
    
    def testSync(self):
        
        to_sync = {
            'css/1.css': 'text/css',
            'css/2.css': 'text/css',
            'css/3.scss': msettings['DEFAULT_MIMETYPE'],
            'css/joined.css': 'text/css',
            'img/black.png': 'image/png',
            'js/1.js': 'application/javascript',
            'js/2.js': 'application/javascript',
            'js/joined.js': 'application/javascript',
        }
        
        def generate_callback(is_forced):
            def myput(filedata, content_type, remote_path, force=is_forced):
                
                self.assertEqual(content_type, to_sync[remote_path])
                self.assertEqual(force, is_forced)
                
                if remote_path in msettings['JOINED']:
                    original = readfile(os.path.join(PWD, 'media', '_test', remote_path.split('/')[1]))
                else:
                    args = [PWD, 'media'] + remote_path.split('/')
                    original = readfile(os.path.join(*args))
                
                self.assertEqual(filedata, original)
                    
            return myput
        
        # normal sync
        self.client.put_callback = generate_callback(is_forced=False)
        mediasync.sync(self.client, force=False, verbose=False)
        
        # forced sync
        self.client.put_callback = generate_callback(is_forced=True)
        mediasync.sync(self.client, force=True, verbose=False)
        
class S3ClientTestCase(unittest.TestCase):

    def setUp(self):
        
        bucket_hash = md5("%i-%s" % (int(time.time()), os.environ['USER'])).hexdigest()
        self.bucket_name = 'mediasync_test_' + bucket_hash
        
        msettings['BACKEND'] = 'mediasync.backends.s3'
        msettings['AWS_BUCKET'] = self.bucket_name
        msettings['AWS_KEY'] = os.environ['AWS_KEY'] or None
        msettings['AWS_SECRET'] = os.environ['AWS_SECRET'] or None
        msettings['PROCESSORS'] = []
        msettings['SERVE_REMOTE'] = True
        msettings['JOINED'] = {
            'css/joined.css': ('css/1.css', 'css/2.css'),
            'js/joined.js': ('js/1.js', 'js/2.js'),
        }
        
        self.client = backends.client()
    
    def testServeRemote(self):
        
        msettings['SERVE_REMOTE'] = False
        self.assertEqual(backends.client().media_url(), '/media')

        msettings['SERVE_REMOTE'] = True
        self.assertEqual(backends.client().media_url(), 'http://s3.amazonaws.com/%s' % self.bucket_name)
    
    def testSync(self):
        
        # calculate cache control
        cc = "max-age=%i, public" % (self.client.expiration_days * 24 * 3600)
        
        # do a sync then reopen client
        mediasync.sync(self.client, force=True, verbose=False)
        self.client.open()
        conn = self.client.get_connection()
        
        # setup http connection
        http_conn = httplib.HTTPSConnection('s3.amazonaws.com')
        
        # test synced files then delete them
        bucket = conn.get_bucket(self.bucket_name)
        
        static_paths = mediasync.listdir_recursive(os.path.join(PWD, 'media'))
        joined_paths = msettings['JOINED'].iterkeys()
        
        for path in itertools.chain(static_paths, joined_paths):
            
            key = bucket.get_key(path)
            
            if path in msettings['JOINED']:
                args = [PWD, 'media', '_test', path.split('/')[1]]
            else:
                args = [PWD, 'media'] + path.split('/')
            local_content = readfile(os.path.join(*args))

            # compare file content
            self.assertEqual(key.read(), local_content)
            
            # verify checksum
            key_meta = key.get_metadata('mediasync-checksum') or ''
            s3_checksum = key_meta.replace(' ', '+')
            (hexdigest, b64digest) = mediasync.checksum(local_content)
            self.assertEqual(s3_checksum, b64digest)
            
            # do a HEAD request on the file
            http_conn.request('HEAD', "/%s/%s" % (self.bucket_name, path))
            response = http_conn.getresponse()
            response.read()
            
            # verify valid content type
            content_type = mimetypes.guess_type(path)[0] or msettings['DEFAULT_MIMETYPE']
            self.assertEqual(response.getheader("Content-Type", None), content_type)
            
            # check for valid expires headers
            expires = response.getheader("Expires", None)
            self.assertRegexpMatches(expires, EXPIRES_RE)
            
            # check for valid cache control header
            cc_header = response.getheader("Cache-Control", None)
            self.assertEqual(cc_header, cc)
            
            # done with the file, delete it from S3
            key.delete()
            
            if content_type in mediasync.TYPES_TO_COMPRESS:
                
                key = bucket.get_key("%s.gzt" % path)
                
                # do a HEAD request on the file
                http_conn.request('HEAD', "/%s/%s.gzt" % (self.bucket_name, path))
                response = http_conn.getresponse()
                response.read()
                
                key_meta = key.get_metadata('mediasync-checksum') or ''
                s3_checksum = key_meta.replace(' ', '+')
                self.assertEqual(s3_checksum, b64digest)
                
                key.delete()
        
        http_conn.close()
        
        # wait a moment then delete temporary bucket
        time.sleep(2)
        conn.delete_bucket(self.bucket_name)
        
        # close client
        self.client.close()
    
    def testMissingBucket(self):
        del msettings['AWS_BUCKET']
        self.assertRaises(AssertionError, backends.client)

class ProcessorTestCase(unittest.TestCase):

    def setUp(self):
        msettings['SERVE_REMOTE'] = True
        msettings['BACKEND'] = 'mediasync.tests.tests'
        msettings['PROCESSORS'] = (
            'mediasync.processors.slim.css_minifier',
            'mediasync.processors.slim.js_minifier',
            lambda fd, ct, rp, r: fd.upper(),
        )
        self.client = backends.client()
    
    def testJSProcessor(self):
        
        try:
            import slimmer
        except ImportError:
            self.skipTest("slimmer not installed, skipping test")
        
        content = """var foo = function() {
            alert(1);
        };"""
        
        ct = 'text/javascript'
        procd = self.client.process(content, ct, 'test.js')
        self.assertEqual(procd, 'VAR FOO = FUNCTION(){ALERT(1)};')
    
    def testCSSProcessor(self):
        
        try:
            import slimmer
        except ImportError:
            self.skipTest("slimmer not installed, skipping test")
        
        content = """html {
            border: 1px solid #000000;
            font-family: "Helvetica", "Arial", sans-serif;
        }"""

        ct = 'text/css'
        procd = self.client.process(content, ct, 'test.css')
        self.assertEqual(procd, 'HTML{BORDER:1PX SOLID #000;FONT-FAMILY:"HELVETICA","ARIAL",SANS-SERIF}')
    
    def testCustomProcessor(self):
        procd = self.client.process('asdf', 'text/plain', 'asdf.txt')
        self.assertEqual(procd, "ASDF")

class ClosureCompilerTestCase(unittest.TestCase):
    
    def setUp(self):
        msettings['SERVE_REMOTE'] = True
        msettings['BACKEND'] = 'mediasync.tests.tests'
        msettings['PROCESSORS'] = (
            'mediasync.processors.closurecompiler.compile',
        )
        self.client = backends.client()
    
    def testCompiler(self):
        
        content = """var foo = function() {
            alert(1);
        };"""
        
        for ct in JS_MIMETYPES:
            procd = self.client.process(content, ct, 'test.js')
            self.assertEqual(procd, 'var foo=function(){alert(1)};\n')
    
    def testNotJavascript(self):
        
        content = """html {
            border: 1px solid #000000;
            font-family: "Helvetica", "Arial", sans-serif;
        }"""
        
        procd = self.client.process(content, 'text/css', 'test.css')
        self.assertEqual(procd, content)

class SignalTestCase(unittest.TestCase):
    
    def setUp(self):
        msettings['BACKEND'] = 'mediasync.tests.tests'
        self.client = backends.client()
    
    def tearDown(self):
        root = msettings['STATIC_ROOT']
        for filename in glob.glob(os.path.join(root, "*/*.s[ac]ss")):
            path = filename[:-4] + "css"
            if os.path.exists(path):
                os.unlink(path)
    
    def testSyncSignals(self):
        
        self.client.called_presync = False
        self.client.called_postsync = False
        
        @receiver(pre_sync, weak=False)
        def presync_receiver(sender, **kwargs):
            self.assertEqual(self.client, sender)
            sender.called_presync = True
        
        @receiver(post_sync, weak=False)
        def postsync_receiver(sender, **kwargs):
            self.assertEqual(self.client, sender)
            sender.called_postsync = True
            
        mediasync.sync(self.client, force=True, verbose=False)
        
        self.assertTrue(self.client.called_presync)
        self.assertTrue(self.client.called_postsync)
    
    def testSassReceiver(self):
        
        pre_sync.connect(sass_receiver)
        
        mediasync.sync(self.client, force=True, verbose=False)
        
        root = msettings['STATIC_ROOT']
        
        for sass_path in glob.glob(os.path.join(root, "*/*.s[ac]ss")):
            css_path = sass_path[:-4] + "css"
            self.assertTrue(os.path.exists(css_path))

class TemplateTagTestCase(unittest.TestCase):
    
    def setUp(self):
        msettings['BACKEND'] = 'mediasync.tests.tests'
        msettings['DOCTYPE'] = 'html5'
        self.client = backends.client()
    
    def testMediaURLTag(self):
        
        pathvar = 'images/logo.png'
        c = Context({'pathvar': pathvar})
        
        # base media url
        t = Template('{% load media %}{% media_url %}')
        self.assertEqual(t.render(c), "http://localhost")
        
        # media url with string argument
        t = Template('{%% load media %%}{%% media_url "%s" %%}' % pathvar)
        self.assertEqual(t.render(c), "http://localhost/images/logo.png")
        
        # media url with variable argument
        t = Template('{% load media %}{% media_url pathvar %}')
        self.assertEqual(t.render(c), "http://localhost/images/logo.png")
    
    def testCSSTag(self):
        
        pathvar = 'styles/reset.css'
        c = Context({'pathvar': pathvar})
        
        # css tag with string argument
        t = Template('{%% load media %%}{%% css "%s" %%}' % pathvar)
        self.assertEqual(
            t.render(c),
            '<link rel="stylesheet" href="http://localhost/%s" media="screen, projection">' % pathvar)

        # css tag with string argument and explicit media type
        t = Template('{%% load media %%}{%% css "%s" "tv" %%}' % pathvar)
        self.assertEqual(
            t.render(c),
            '<link rel="stylesheet" href="http://localhost/%s" media="tv">' % pathvar)
        
        # css tag with variable argument
        t = Template('{% load media %}{% css pathvar %}')
        self.assertEqual(
            t.render(c),
            '<link rel="stylesheet" href="http://localhost/%s" media="screen, projection">' % pathvar)

        # css tag with variable argument and explicit media type
        t = Template('{% load media %}{% css pathvar "tv" %}')
        self.assertEqual(
            t.render(c),
            '<link rel="stylesheet" href="http://localhost/%s" media="tv">' % pathvar)
    
    def testJSTag(self):

        pathvar = 'scripts/jquery.js'
        c = Context({'pathvar': pathvar})
        
        # js tag with string argument
        t = Template('{%% load media %%}{%% js "%s" %%}' % pathvar)
        self.assertEqual(
            t.render(c),
            '<script src="http://localhost/%s"></script>' % pathvar)
        
        # js tag with variable argument
        t = Template('{% load media %}{% js pathvar %}')
        self.assertEqual(
            t.render(c),
            '<script src="http://localhost/%s"></script>' % pathvar)
    
    def testMultipleTags(self):
        
        paths = ('scripts/1.js','scripts/2.js')
        c = Context({'paths': paths})
        
        t = Template('{% load media %}{% for path in paths %}{% media_url path %}{% endfor %}')
        self.assertEqual(
            t.render(c),
            'http://localhost/scripts/1.jshttp://localhost/scripts/2.js')
        
########NEW FILE########
__FILENAME__ = urls
"""
Mediasync can serve media locally when MEDIASYNC['SERVE_REMOTE'] == False.
The following urlpatterns are shimmed in, in that case.
"""
from django.conf.urls import *
from mediasync import backends

client = backends.client()
local_media_url = client.local_media_url.strip('/')

urlpatterns = patterns('mediasync.views',
    url(r'^%s/(?P<path>.*)$' % local_media_url, 'static_serve',
        {'client': client}),
)

########NEW FILE########
__FILENAME__ = views
"""
This module contains views used to serve static media if 
msettings['SERVE_REMOTE'] == False. See mediasync.urls to see how
these are shimmed in.

The static_serve() function is where the party starts.
"""
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.static import serve
from mediasync import combine_files
from mediasync.conf import msettings

def combo_serve(request, path, client):
    """
    Handles generating a 'combo' file for the given path. This is similar to
    what happens when we upload to S3. Processors are applied, and we get
    the value that we would if we were serving from S3. This is a good way
    to make sure combo files work as intended before rolling out
    to production.
    """
    joinfile = path
    sourcefiles = msettings['JOINED'][path]
    # Generate the combo file as a string.
    combo_data, dirname = combine_files(joinfile, sourcefiles, client)
    
    if path.endswith('.css'):
        mime_type = 'text/css'
    elif joinfile.endswith('.js'):
        mime_type = 'application/javascript'

    return HttpResponse(combo_data, mimetype=mime_type)

def _form_key_str(path):
    """
    Given a URL path, massage it into a key we can perform a lookup on the
    MEDIASYNC['JOINED'] dict with.
    
    This mostly involves figuring into account the CSS_PATH and JS_PATH
    settings, if they have been set.
    """
    if path.endswith('.css'):
        media_path_prefix = msettings['CSS_PATH']
    elif path.endswith('.js'):
        media_path_prefix = msettings['JS_PATH']
    else:
        # This isn't a CSS/JS file, no combo for you.
        return None

    if media_path_prefix:
        # CS/JSS path prefix has been set. Factor that into the key lookup.
        if not media_path_prefix.endswith('/'):
            # We need to add this slash so we can lop it off the 'path'
            # variable, to match the value in the JOINED dict.
            media_path_prefix += '/'

        if path.startswith(media_path_prefix):
            # Given path starts with the CSS/JS media prefix. Lop this off
            # so we can perform a lookup in the JOINED dict.
            return path[len(media_path_prefix):]
        else:
            # Path is in a root dir, send along as-is.
            return path

    # No CSS/JS path prefix set. Keep it raw.
    return path

def _find_combo_match(path):
    """
    Calculate the key to check the MEDIASYNC['JOINED'] dict for, perform the
    lookup, and return the matching key string if a match is found. If no
    match is found, return None instead.
    """
    key_str = _form_key_str(path)
    if not key_str:
        # _form_key_str() says this isn't even a CSS/JS file.
        return None

    if not msettings['JOINED'].has_key(key_str):
        # No combo file match found. Must be an single file.
        return None
    else:
        # Combo match found, return the JOINED key.
        return key_str

def static_serve(request, path, client):
    """
    Given a request for a media asset, this view does the necessary wrangling
    to get the correct thing delivered to the user. This can also emulate the
    combo behavior seen when SERVE_REMOTE == False and EMULATE_COMBO == True.
    """
    
    if msettings['SERVE_REMOTE']:
        # We're serving from S3, redirect there.
        url = client.remote_media_url().strip('/') + '/%(path)s'
        return redirect(url, permanent=True)

    if not msettings['SERVE_REMOTE'] and msettings['EMULATE_COMBO']:
        # Combo emulation is on and we're serving media locally. Try to see if
        # the given path matches a combo file defined in the JOINED dict in
        # the MEDIASYNC settings dict.
        combo_match = _find_combo_match(path)
        if combo_match:
            # We found a combo file match. Combine it and serve the result.
            return combo_serve(request, combo_match, client)

    # No combo file, but we're serving locally. Use the standard (inefficient)
    # Django static serve view.
    
    resp = serve(request, path, document_root=client.media_root, show_indexes=True)
    try:
        resp.content = client.process(resp.content, resp['Content-Type'], path)
    except KeyError:
        # HTTPNotModifiedResponse lacks the "Content-Type" key.
        pass
    return resp

########NEW FILE########
