__FILENAME__ = staticsitegen
from django.core.management.base import BaseCommand
from django_medusa.renderers import StaticSiteRenderer
from django_medusa.utils import get_static_renderers


class Command(BaseCommand):
    can_import_settings = True

    help = 'Looks for \'renderers.py\' in each INSTALLED_APP, which defines '\
           'a class for processing one or more URL paths into static files.'

    def handle(self, *args, **options):
        StaticSiteRenderer.initialize_output()

        for Renderer in get_static_renderers():
            r = Renderer()
            r.generate()

        StaticSiteRenderer.finalize_output()

########NEW FILE########
__FILENAME__ = appengine
from django.conf import settings
from django.test.client import Client
from .base import BaseStaticSiteRenderer
import os

__all__ = ('GAEStaticSiteRenderer', )

STANDARD_EXTENSIONS = (
    'htm', 'html', 'css', 'xml', 'json', 'js', 'yaml', 'txt'
)


# Unfortunately split out from the class at the moment to allow rendering with
# several processes via `multiprocessing`.
# TODO: re-implement within the class if possible?
def _gae_render_path(args):
    client, path, view = args
    if not client:
        client = Client()
    if path:
        DEPLOY_DIR = settings.MEDUSA_DEPLOY_DIR
        realpath = path
        if path.startswith("/"):
            realpath = realpath[1:]

        if path.endswith("/"):
            needs_ext = True
        else:
            needs_ext = False

        output_dir = os.path.abspath(os.path.join(
            DEPLOY_DIR,
            "deploy",
            os.path.dirname(realpath)
        ))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        outpath = os.path.join(DEPLOY_DIR, "deploy", realpath)

        resp = client.get(path)
        if resp.status_code != 200:
            raise Exception

        mimetype = resp['Content-Type'].split(";", 1)[0]

        if needs_ext:
            outpath += "index.html"

        print outpath
        with open(outpath, 'w') as f:
            f.write(resp.content)

        rel_outpath = outpath.replace(
            os.path.abspath(DEPLOY_DIR) + "/",
            ""
        )
        if ((not needs_ext) and path.endswith(STANDARD_EXTENSIONS))\
        or (mimetype == "text/html"):
            # Either has obvious extension OR it's a regular HTML file.
            return None
        return "# req since this url does not end in an extension and also\n"\
               "# has non-html mime: %s\n"\
               "- url: %s\n"\
               "  static_files: %s\n"\
               "  upload: %s\n"\
               "  mime_type: %s\n\n" % (
                    mimetype, path, rel_outpath, rel_outpath, mimetype
               )


class GAEStaticSiteRenderer(BaseStaticSiteRenderer):
    """
    A variation of BaseStaticSiteRenderer that deploys directly to S3
    rather than to the local filesystem.

    Settings:
      * GAE_APP_ID
      * MEDUSA_DEPLOY_DIR
    """
    def render_path(self, path=None, view=None):
        return _gae_render_path((self.client, path, view))

    @classmethod
    def initialize_output(cls):
        print "Initializing output directory with `app.yaml`."
        print

        # Initialize the MEDUSA_DEPLOY_DIR with an `app.yaml` and `deploy`
        # directory which stores the static files on disk.
        DEPLOY_DIR = settings.MEDUSA_DEPLOY_DIR
        static_output_dir = os.path.abspath(os.path.join(
            DEPLOY_DIR,
            "deploy"
        ))
        app_yaml = os.path.abspath(os.path.join(
            DEPLOY_DIR,
            "app.yaml"
        ))
        if not os.path.exists(static_output_dir):
            os.makedirs(static_output_dir)

        # Initialize the app.yaml file
        app_yaml_f = open(app_yaml, 'w')
        app_yaml_f.write(
            "application: %s\n"\
            "version: 1\n"\
            "runtime: python\n"\
            "api_version: 1\n"\
            "threadsafe: true\n\n"\
            "handlers:\n\n" % settings.GAE_APP_ID
        )
        app_yaml_f.close()

    @classmethod
    def finalize_output(cls):
        print
        print "Finalizing `app.yaml`."
        print

        DEPLOY_DIR = settings.MEDUSA_DEPLOY_DIR
        app_yaml = os.path.abspath(os.path.join(
            DEPLOY_DIR,
            "app.yaml"
        ))

        app_yaml_f = open(app_yaml, 'a')

        # Handle "root" index.html pages up to 10 paths deep.
        # This is pretty awful, but it's an easy way to handle arbitrary
        # paths and a) ensure GAE uploads all the files we want and b)
        # we don't encounter the 100 URL definition limit for app.yaml.
        app_yaml_f.write(
            "####################\n"\
            "# map index.html files to their root (up to 10 deep)\n"\
            "####################\n\n"
        )

        for num_bits in xrange(10):
            path_parts = "(.*)/" * num_bits
            counter_part = ""
            for c in xrange(0, num_bits):
                counter_part += "\\%s/" % (c + 1)

            app_yaml_f.write(
                "- url: /%s\n"\
                "  static_files: deploy/%sindex.html\n"\
                "  upload: deploy/%sindex.html\n\n" % (
                path_parts, counter_part, path_parts
            ))

        # Anything else not matched should just be uploaded as-is.
        app_yaml_f.write(
            "####################\n"\
            "# everything else\n"\
            "####################\n\n"\
            "- url: /\n"\
            "  static_dir: deploy"
        )
        app_yaml_f.close()

        print "You should now be able to deploy this to Google App Engine"
        print "by performing the following command:"
        print "appcfg.py update %s" % os.path.abspath(DEPLOY_DIR)
        print

    def generate(self):
        DEPLOY_DIR = settings.MEDUSA_DEPLOY_DIR

        # Generate the site
        if getattr(settings, "MEDUSA_MULTITHREAD", False):
            # Upload up to ten items at once via `multiprocessing`.
            from multiprocessing import Pool

            print "Uploading with up to 10 upload processes..."
            pool = Pool(10)

            handlers = pool.map(
                _gae_render_path,
                ((None, path, None) for path in self.paths),
                chunksize=5
            )
            pool.close()
            pool.join()
        else:
            # Use standard, serial upload.
            self.client = Client()
            handlers = []
            for path in self.paths:
                handlers.append(self.render_path(path=path))

        DEPLOY_DIR = settings.MEDUSA_DEPLOY_DIR
        app_yaml = os.path.abspath(os.path.join(
            DEPLOY_DIR,
            "app.yaml"
        ))
        app_yaml_f = open(app_yaml, 'a')
        for handler_def in handlers:
            if handler_def is not None:
                app_yaml_f.write(handler_def)
        app_yaml_f.close()

########NEW FILE########
__FILENAME__ = base
__all__ = ['COMMON_MIME_MAPS', 'BaseStaticSiteRenderer']


# Since mimetypes.get_extension() gets the "first known" (alphabetically),
# we get supid behavior like "text/plain" mapping to ".bat". This list
# overrides some file types we will surely use, to eliminate a call to
# mimetypes.get_extension() except in unusual cases.
COMMON_MIME_MAPS = {
    "text/plain": ".txt",
    "text/html": ".html",
    "text/javascript": ".js",
    "application/javascript": ".js",
    "text/json": ".json",
    "application/json": ".json",
    "text/css": ".css",
}


class BaseStaticSiteRenderer(object):
    """
    This default renderer writes the given URLs (defined in get_paths())
    into static files on the filesystem by getting the view's response
    through the Django testclient.
    """

    @classmethod
    def initialize_output(cls):
        """
        Things that should be done only once to the output directory BEFORE
        rendering occurs (i.e. setting up a config file, creating dirs,
        creating an external resource, starting an atomic deploy, etc.)

        Management command calls this once before iterating over all
        renderer instances.
        """
        pass

    @classmethod
    def finalize_output(cls):
        """
        Things that should be done only once to the output directory AFTER
        rendering occurs (i.e. writing end of config file, setting up
        permissions, calling an external "deploy" method, finalizing an
        atomic deploy, etc.)

        Management command calls this once after iterating over all
        renderer instances.
        """
        pass

    def get_paths(self):
        """ Override this in a subclass to define the URLs to process """
        raise NotImplementedError

    @property
    def paths(self):
        """ Property that memoizes get_paths. """
        p = getattr(self, "_paths", None)
        if not p:
            p = self.get_paths()
            self._paths = p
        return p

    def render_path(self, path=None, view=None):
        raise NotImplementedError

    def generate(self):
        for path in self.paths:
            self.render_path(path)

########NEW FILE########
__FILENAME__ = disk
from django.conf import settings
from django.test.client import Client
import mimetypes
import os
from .base import COMMON_MIME_MAPS, BaseStaticSiteRenderer

__all__ = ('DiskStaticSiteRenderer', )


# Unfortunately split out from the class at the moment to allow rendering with
# several processes via `multiprocessing`.
# TODO: re-implement within the class if possible?
def _disk_render_path(args):
    client, path, view = args
    if not client:
        client = Client()
    if path:
        DEPLOY_DIR = settings.MEDUSA_DEPLOY_DIR
        realpath = path
        if path.startswith("/"):
            realpath = realpath[1:]

        if path.endswith("/"):
            needs_ext = True
        else:
            needs_ext = False

        output_dir = os.path.abspath(os.path.join(
            DEPLOY_DIR,
            os.path.dirname(realpath)
        ))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        outpath = os.path.join(DEPLOY_DIR, realpath)

        resp = client.get(path)
        if resp.status_code != 200:
            raise Exception
        if needs_ext:
            mime = resp['Content-Type']
            mime = mime.split(';', 1)[0]

            # Check our override list above first.
            ext = COMMON_MIME_MAPS.get(
                mime,
                mimetypes.guess_extension(mime)
            )
            if ext:
                outpath += "index" + ext
            else:
                # Default to ".html"
                outpath += "index.html"
        print outpath
        with open(outpath, 'w') as f:
            f.write(resp.content)


class DiskStaticSiteRenderer(BaseStaticSiteRenderer):

    def render_path(self, path=None, view=None):
        _disk_render_path((self.client, path, view))

    def generate(self):
        if getattr(settings, "MEDUSA_MULTITHREAD", False):
            # Upload up to ten items at once via `multiprocessing`.
            from multiprocessing import Pool, cpu_count

            print "Generating with up to %d processes..." % cpu_count()
            pool = Pool(cpu_count())

            pool.map_async(
                _disk_render_path,
                ((None, path, None) for path in self.paths),
                chunksize=5
            )
            pool.close()
            pool.join()
        else:
            # Use standard, serial upload.
            self.client = Client()
            for path in self.paths:
                self.render_path(path=path)

########NEW FILE########
__FILENAME__ = s3
import cStringIO

from datetime import timedelta, datetime
from django.conf import settings
from django.test.client import Client
from .base import BaseStaticSiteRenderer

__all__ = ('S3StaticSiteRenderer', )


def _get_cf():
    from boto.cloudfront import CloudFrontConnection
    return CloudFrontConnection(
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )


def _get_distribution():
    if not getattr(settings, "AWS_DISTRIBUTION_ID", None):
        return None

    conn = _get_cf()
    try:
        return conn.get_distribution_info(settings.AWS_DISTRIBUTION_ID)
    except:
        return None


def _get_bucket():
    from boto.s3.connection import S3Connection
    conn = S3Connection(
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    bucket = (settings.MEDUSA_AWS_STORAGE_BUCKET_NAME if settings.MEDUSA_AWS_STORAGE_BUCKET_NAME else settings.AWS_STORAGE_BUCKET_NAME)
    return conn.get_bucket(bucket)


def _upload_to_s3(key, file):
    key.set_contents_from_file(file, policy="public-read")

    cache_time = 0
    now = datetime.now()
    expire_dt = now + timedelta(seconds=cache_time * 1.5)
    if cache_time != 0:
        key.set_metadata('Cache-Control',
            'max-age=%d, must-revalidate' % int(cache_time))
        key.set_metadata('Expires',
            expire_dt.strftime("%a, %d %b %Y %H:%M:%S GMT"))
    key.make_public()


# Unfortunately split out from the class at the moment to allow rendering with
# several processes via `multiprocessing`.
# TODO: re-implement within the class if possible?
def _s3_render_path(args):
    client, bucket, path, view = args
    if not client:
        client = Client()

    if not bucket:
        bucket = _get_bucket()

    # Render the view
    resp = client.get(path)
    if resp.status_code != 200:
        raise Exception

    # Default to "index.html" as the upload path if we're in a dir listing.
    outpath = path
    if path.endswith("/"):
        outpath += "index.html"

    key = bucket.get_key(outpath) or bucket.new_key(outpath)
    key.content_type = resp['Content-Type']

    temp_file = cStringIO.StringIO(resp.content)
    md5 = key.compute_md5(temp_file)

    # If key is new, there's no etag yet
    if not key.etag:
        _upload_to_s3(key, temp_file)
        message = "Creating"

    else:
        etag = key.etag or ''
        # for some weird reason, etags are quoted, strip them
        etag = etag.strip('"').strip("'")
        if etag not in md5:
            _upload_to_s3(key, temp_file)
            message = "Updating"
        else:
            message = "Skipping"

    print "%s http://%s%s" % (
        message,
        bucket.get_website_endpoint(),
        path
    )
    temp_file.close()
    return [path, outpath]


class S3StaticSiteRenderer(BaseStaticSiteRenderer):
    """
    A variation of BaseStaticSiteRenderer that deploys directly to S3
    rather than to the local filesystem.

    Requires `boto`.

    Uses some of the same settings as `django-storages`:
      * AWS_ACCESS_KEY
      * AWS_SECRET_ACCESS_KEY
      * AWS_STORAGE_BUCKET_NAME
    """
    @classmethod
    def initialize_output(cls):
        cls.all_generated_paths = []

    def render_path(self, path=None, view=None):
        return _s3_render_path((self.client, self.bucket, path, view))

    def generate(self):
        from boto.s3.connection import S3Connection

        self.conn = S3Connection(
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket = (self.conn.get_bucket(settings.MEDUSA_AWS_STORAGE_BUCKET_NAME) if settings.MEDUSA_AWS_STORAGE_BUCKET_NAME else self.conn.get_bucket(settings.AWS_STORAGE_BUCKET_NAME))
        self.bucket.configure_website("index.html", "500.html")
        self.server_root_path = self.bucket.get_website_endpoint()

        self.generated_paths = []
        if getattr(settings, "MEDUSA_MULTITHREAD", False):
            # Upload up to ten items at once via `multiprocessing`.
            from multiprocessing import Pool
            import itertools

            print "Uploading with up to 10 upload processes..."
            pool = Pool(10)

            path_tuples = pool.map(
                _s3_render_path,
                ((None, None, path, None) for path in self.paths),
                chunksize=5
            )
            pool.close()
            pool.join()

            self.generated_paths = list(itertools.chain(*path_tuples))
        else:
            # Use standard, serial upload.
            self.client = Client()
            for path in self.paths:
                self.generated_paths += self.render_path(path=path)

        type(self).all_generated_paths += self.generated_paths

    @classmethod
    def finalize_output(cls):
        dist = _get_distribution()
        if dist and dist.in_progress_invalidation_batches < 3:
            cf = _get_cf()
            req = cf.create_invalidation_request(
                settings.AWS_DISTRIBUTION_ID,
                cls.all_generated_paths
            )
            print req.id
            #import time
            #while True:
            #    status = cf.invalidation_request_status(
            #        settings.AWS_DISTRIBUTION_ID,
            #        req.id
            #    ).status
            #    if status != "InProgress":
            #        print
            #        print "Complete:"
            #        if dist.config.cnames:
            #            print "Site deployed to http://%s/" % dist.config.cnames[0]
            #        else:
            #            print "Site deployed to http://%s/" % dist.domain_name
            #        print
            #        break
            #    else:
            #        print "In progress..."
            #    time.sleep(5)

########NEW FILE########
__FILENAME__ = utils
import imp
from django.conf import settings
from importlib import import_module
import sys


def get_static_renderers():
    module_name = 'renderers'
    renderers = []

    modules_to_check = []

    # Hackish: do this in case we have some project top-level
    # (homepage, etc) urls defined project-level instead of app-level.
    settings_module = settings.SETTINGS_MODULE
    if settings_module:
        if "." in settings_module:
            # strip off '.settings" from end of module
            # (want project module, if possible)
            settings_module = settings_module.split(".", 1)[0]
        modules_to_check += [settings_module, ]

    # INSTALLED_APPS that aren't the project itself (also ignoring this
    # django_medusa module)
    modules_to_check += filter(
        lambda x: (x != "django_medusa") and (x != settings_module),
        settings.INSTALLED_APPS
    )

    for app in modules_to_check:
        try:
            import_module(app)
            app_path = sys.modules[app].__path__
        except AttributeError:
            print "Skipping app '%s'... (Not found)" % app
            continue
        try:
            imp.find_module(module_name, app_path)
        except ImportError:
            print "Skipping app '%s'... (No 'renderers.py')" % app
            continue
        try:
            app_render_module = import_module('%s.%s' % (app, module_name))
            if hasattr(app_render_module, "renderers"):
                renderers += getattr(app_render_module, module_name)
            else:
                print "Skipping app '%s'... ('%s.renderers' does not contain "\
                      "'renderers' var (list of render classes)" % (app, app)
        except AttributeError:
            print "Skipping app '%s'... (Error importing '%s.renderers')" % (
                app, app
            )
            continue
        print "Found renderers for '%s'..." % app
    print
    return tuple(renderers)

########NEW FILE########
