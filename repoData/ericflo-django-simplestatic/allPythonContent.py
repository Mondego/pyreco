__FILENAME__ = compress
import hashlib
import os
import subprocess

from StringIO import StringIO

from django.core.urlresolvers import reverse
from django.core.cache.backends.locmem import LocMemCache

from simplestatic import conf


CACHE = LocMemCache('simplestatic', {})
CHUNK_SIZE = 8192


def uncached_hash_for_paths(paths):
    hsh = hashlib.md5()

    for path in paths:
        full_path = os.path.join(conf.SIMPLESTATIC_DIR, path)
        if not os.path.exists(full_path):
            # TODO: Log some kind of warning here
            continue

        with open(full_path, 'r') as f:
            while 1:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                hsh.update(data)

    return hsh.hexdigest()


def cached_hash_for_paths(paths):
    cache_key = hashlib.md5('!'.join(sorted(paths))).hexdigest()
    hsh = CACHE.get(cache_key)
    if hsh is not None:
        return hsh
    hsh = uncached_hash_for_paths(paths)
    CACHE.set(cache_key, hsh, 3600)
    return hsh


hash_for_paths = (uncached_hash_for_paths if conf.SIMPLESTATIC_DEBUG else
    cached_hash_for_paths)


def debug_url(path):
    hsh = hash_for_paths([path])
    url = reverse('django.views.static.serve', kwargs={'path': path})
    return '%s?devcachebuster=%s' % (url, hsh)


def prod_url(paths, ext=None):
    if ext is None:
        ext = paths[0].rpartition('.')[-1]
    hsh = hash_for_paths(paths)
    return '//%s/%s/%s.%s' % (
        conf.SIMPLESTATIC_CUSTOM_DOMAIN,
        conf.SIMPLESTATIC_COMPRESSED_DIR,
        hsh,
        ext,
    )


def url(path):
    if conf.SIMPLESTATIC_DEBUG:
        return debug_url(path)
    return '//%s/%s/%s' % (
        conf.SIMPLESTATIC_CUSTOM_DOMAIN,
        conf.SIMPLESTATIC_COMPRESSED_DIR,
        path,
    )


def css_url(paths):
    return prod_url(paths, 'css')


def js_url(paths):
    return prod_url(paths, 'js')


def compress_css(paths):
    output = StringIO()
    for path in paths:
        with open(path, 'r') as in_file:
            while 1:
                data = in_file.read(CHUNK_SIZE)
                if not data:
                    break
                output.write(data)
        output.write('\n')
    return output.getvalue()


def compress_js(paths):
    cmd = '%s --compilation_level %s %s' % (
        conf.CLOSURE_COMPILER_COMMAND,
        conf.CLOSURE_COMPILATION_LEVEL,
        ' '.join(['--js %s' % (path,) for path in paths]),
    )
    output = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE
    ).communicate()[0]
    return output

########NEW FILE########
__FILENAME__ = conf
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

SIMPLESTATIC_DIR = getattr(settings, 'SIMPLESTATIC_DIR', None)
if not SIMPLESTATIC_DIR:
    raise ImproperlyConfigured('You must set SIMPLESTATIC_DIR in settings.')

SIMPLESTATIC_DEBUG = getattr(settings, 'SIMPLESTATIC_DEBUG',
    settings.DEBUG)

SIMPLESTATIC_DEBUG_PATH = getattr(settings, 'SIMPLESTATIC_DEBUG_PATH',
    'static/')

SIMPLESTATIC_COMPRESSED_DIR = getattr(settings,
    'SIMPLESTATIC_COMPRESSED_DIR', 'compressed')

AWS_ACCESS_KEY_ID = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
if not AWS_ACCESS_KEY_ID:
    raise ImproperlyConfigured('You must set AWS_ACCESS_KEY_ID in settings.')

AWS_SECRET_ACCESS_KEY = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
if not AWS_SECRET_ACCESS_KEY:
    raise ImproperlyConfigured(
        'You must set AWS_SECRET_ACCESS_KEY in settings.')

AWS_STORAGE_BUCKET_NAME = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
if not AWS_STORAGE_BUCKET_NAME:
    raise ImproperlyConfigured(
        'You must set AWS_STORAGE_BUCKET_NAME in settings.')

SIMPLESTATIC_CUSTOM_DOMAIN = getattr(settings, 'SIMPLESTATIC_CUSTOM_DOMAIN',
    '%s.s3.amazonaws.com' % (AWS_STORAGE_BUCKET_NAME,))

CLOSURE_COMPILER_JAR = getattr(settings, 'CLOSURE_COMPILER_JAR', None)
if not CLOSURE_COMPILER_JAR:
    CLOSURE_COMPILER_JAR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'compiler.jar')
    )

CLOSURE_COMPILATION_LEVEL = getattr(settings, 'CLOSURE_COMPILATION_LEVEL',
    'SIMPLE_OPTIMIZATIONS')

CLOSURE_COMPILER_COMMAND = getattr(settings, 'CLOSURE_COMPILER_COMMAND', None)
if not CLOSURE_COMPILER_COMMAND:
    CLOSURE_COMPILER_COMMAND = 'java -jar %s' % (CLOSURE_COMPILER_JAR,)

########NEW FILE########
__FILENAME__ = static_sync
import mimetypes
import os

from threading import local, RLock

from multiprocessing.pool import ThreadPool

from boto.s3.connection import S3Connection

from django.template import Template, Context
from django.core.management.base import NoArgsCommand
from django.conf import settings

from simplestatic.compress import compress_css, compress_js, hash_for_paths
from simplestatic import conf
from simplestatic.templatetags.simplestatic_tags import SimpleStaticNode


def s3_bucket(local=local()):
    bucket = getattr(local, 'bucket', None)
    if bucket is not None:
        return bucket
    conn = S3Connection(
        conf.AWS_ACCESS_KEY_ID,
        conf.AWS_SECRET_ACCESS_KEY
    )
    local.bucket = conn.get_bucket(conf.AWS_STORAGE_BUCKET_NAME)
    return local.bucket


def locked_print(s, lock=RLock()):
    with lock:
        print s


def set_content_type(key):
    _, ext = os.path.splitext(key.name)
    if ext:
        content_type = mimetypes.types_map.get(ext)
        if content_type:
            key.content_type = content_type


class Command(NoArgsCommand):
    help = ('Syncs the contents of your SIMPLESTATIC_DIR to S3, compressing '
        + 'any assets as needed')

    def compress_and_upload(self, template, paths, compress, ext):
        bucket = s3_bucket()
        name = '%s/%s.%s' % (
            conf.SIMPLESTATIC_COMPRESSED_DIR,
            hash_for_paths(paths),
            ext,
        )
        key = bucket.get_key(name)
        if key is None:
            locked_print('Compressing %s from %s' % (ext, template))
            compressed = compress(paths)
            locked_print('Uploading %s from %s' % (name, template))
            key = bucket.new_key(name)
            set_content_type(key)
            key.set_contents_from_string(compressed, policy='public-read',
                replace=True)

    def sync_file(self, base, filename):
        name = filename[len(base) + 1:]
        bucket = s3_bucket()
        key = bucket.get_key(name)
        if key:
            etag = key.etag.lstrip('"').rstrip('"')
            with open(filename) as f:
                md5 = key.compute_md5(f)[0]
            if etag != md5:
                locked_print('Syncing %s' % (name,))
                set_content_type(key)
                key.set_contents_from_filename(filename, policy='public-read',
                    md5=md5, replace=True)
        else:
            locked_print('Syncing %s' % (name,))
            key = bucket.new_key(name)
            set_content_type(key)
            key.set_contents_from_filename(filename, policy='public-read',
                replace=True)

    def handle_template(self, base, filename):
        with open(filename, 'r') as f:
            tmpl = Template(f.read())
        template = filename[len(base) + 1:]
        nodes = tmpl.nodelist.get_nodes_by_type(SimpleStaticNode)
        for node in nodes:
            css, js = node.get_css_js_paths(Context())
            if css:
                self.compress_and_upload(template, css, compress_css, 'css')
            if js:
                self.compress_and_upload(template, js, compress_js, 'js')

    def walk_tree(self, paths, func):
        while len(paths):
            popped = paths.pop()
            try:
                base, current_path = popped
            except (ValueError, TypeError):
                base = current_path = popped

            for root, dirs, files in os.walk(current_path):
                for d in dirs:
                    normdir = os.path.join(root, d)
                    if os.path.islink(normdir):
                        paths.append((base, normdir))
                for fn in files:
                    if fn.startswith('.'):
                        continue
                    func(base, os.path.join(root, fn))

    def handle_noargs(self, **options):
        mimetypes.init()

        locked_print('===> Syncing static directory')
        pool = ThreadPool(20)

        # Sync every file in the static media dir with S3
        def pooled_sync_file(base, filename):
            pool.apply_async(self.sync_file, args=[base, filename])

        self.walk_tree([conf.SIMPLESTATIC_DIR], pooled_sync_file)
        pool.close()
        pool.join()
        locked_print('===> Static directory syncing complete')

        locked_print('===> Compressing and uploading CSS and JS')
        pool = ThreadPool(20)

        # Iterate over every template, looking for SimpleStaticNode
        def pooled_handle_template(base, filename):
            pool.apply_async(self.handle_template, args=[base, filename])

        self.walk_tree(list(settings.TEMPLATE_DIRS), pooled_handle_template)
        pool.close()
        pool.join()
        locked_print('===> Finished compressing and uploading CSS and JS')

########NEW FILE########
__FILENAME__ = simplestatic_tags
import os

from django import template

from simplestatic import conf
from simplestatic.compress import debug_url, css_url, js_url, url

register = template.Library()

CSS_TMPL = '<link rel="stylesheet" href="%s" type="text/css" charset="utf-8">'
JS_TMPL = '<script src="%s" type="text/javascript" charset="utf-8"></script>'


class MediaNode(template.Node):
    def __init__(self, path):
        self.path = template.Variable(path)

    def resolve(self, context):
        return self.path.resolve(context)

    def render(self, context):
        return self.TMPL % (debug_url(self.path.resolve(context)),)


class CSSNode(MediaNode):
    TMPL = CSS_TMPL


class JSNode(MediaNode):
    TMPL = JS_TMPL


class URLNode(template.Node):
    def __init__(self, path):
        self.path = template.Variable(path)

    def render(self, context):
        return url(self.path.resolve(context))


class SimpleStaticNode(template.Node):
    def __init__(self, nodes):
        self.nodes = nodes

    def render(self, context):
        if conf.SIMPLESTATIC_DEBUG:
            return self.render_debug(context)
        else:
            return self.render_prod(context)

    def render_debug(self, context):
        return '\n'.join((n.render(context) for n in self.nodes))

    def render_prod(self, context):
        css, js = self.get_css_js_paths(context)

        resp = []
        if css:
            resp.append(CSS_TMPL % (css_url(css),))
        if js:
            resp.append(JS_TMPL % (js_url(js),))

        return '\n'.join(resp)

    def get_css_js_paths(self, context):
        pre = conf.SIMPLESTATIC_DIR
        css, js = [], []
        for node in self.nodes:
            if isinstance(node, CSSNode):
                css.append(os.path.join(pre, node.resolve(context)))
            elif isinstance(node, JSNode):
                js.append(os.path.join(pre, node.resolve(context)))
        return css, js


@register.tag
def simplestatic(parser, token):
    tag_name = token.split_contents()[0]
    nodes = parser.parse('end%s' % (tag_name,))
    parser.delete_first_token()
    return SimpleStaticNode(nodes)


@register.tag
def compress_css(parser, token):
    path = token.split_contents()[1]
    return CSSNode(path)


@register.tag
def compress_js(parser, token):
    path = token.split_contents()[1]
    return JSNode(path)


@register.tag
def simplestatic_url(parser, token):
    path = token.split_contents()[1]
    return URLNode(path)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from simplestatic import conf


def simplestatic_debug_urls():
    if not conf.SIMPLESTATIC_DEBUG:
        return patterns('')

    return patterns('', url(
        r'^%s(?P<path>.*)$' % conf.SIMPLESTATIC_DEBUG_PATH,
        'django.views.static.serve',
        {'show_indexes': True, 'document_root': conf.SIMPLESTATIC_DIR},
    ))

########NEW FILE########
