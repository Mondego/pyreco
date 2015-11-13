__FILENAME__ = s3boto
"""
Incorporated from django-storages, copyright all of those listed in:
http://code.welldev.org/django-storages/src/tip/AUTHORS
"""
import urllib
import os
import mimetypes
import re

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.exceptions import ImproperlyConfigured

try:
    from boto.s3.connection import S3Connection
    from boto.exception import S3ResponseError
    from boto.s3.key import Key
except ImportError:
    raise ImproperlyConfigured(
        "Could not load boto's S3 bindings. Please install boto."
    )

AWS_REGIONS = [
    'eu-west-1',
    'us-east-1',
    'us-west-1',
    'us-west-2',
    'sa-east-1',
    'ap-northeast-1',
    'ap-southeast-1',
]

REGION_RE = re.compile(r's3-(.+).amazonaws.com')

ACCESS_KEY_NAME = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
SECRET_KEY_NAME = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
HEADERS = getattr(settings, 'AWS_HEADERS', {})
STORAGE_BUCKET_NAME = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
STORAGE_BUCKET_CNAME = getattr(settings, 'AWS_STORAGE_BUCKET_CNAME', None)
AWS_REGION = getattr(settings, 'AWS_REGION', 'us-east-1')
AUTO_CREATE_BUCKET = getattr(settings, 'AWS_AUTO_CREATE_BUCKET', True)
DEFAULT_ACL = getattr(settings, 'AWS_DEFAULT_ACL', 'public-read')
QUERYSTRING_AUTH = getattr(settings, 'AWS_QUERYSTRING_AUTH', True)
QUERYSTRING_EXPIRE = getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 3600)
IS_GZIPPED = getattr(settings, 'AWS_IS_GZIPPED', False)
GZIP_CONTENT_TYPES = getattr(settings, 'GZIP_CONTENT_TYPES', (
    'text/css',
    'application/javascript',
    'application/x-javascript'
))

if IS_GZIPPED:
    from gzip import GzipFile


class S3BotoStorage(Storage):
    """Amazon Simple Storage Service using Boto"""

    def __init__(self, bucket=STORAGE_BUCKET_NAME,
                       bucket_cname=STORAGE_BUCKET_CNAME,
                       region=AWS_REGION, access_key=None,
                       secret_key=None, acl=DEFAULT_ACL,
                       headers=HEADERS, gzip=IS_GZIPPED,
                       gzip_content_types=GZIP_CONTENT_TYPES,
                       querystring_auth=QUERYSTRING_AUTH,
                       force_no_ssl=False):
        self.bucket_name = bucket
        self.bucket_cname = bucket_cname
        self.host = self._get_host(region)
        self.acl = acl
        self.headers = headers
        self.gzip = gzip
        self.gzip_content_types = gzip_content_types
        self.querystring_auth = querystring_auth
        self.force_no_ssl = force_no_ssl
        # This is called as chunks are uploaded to S3. Useful for getting
        # around limitations in eventlet for things like gunicorn.
        self.s3_callback_during_upload = None

        if not access_key and not secret_key:
            access_key, secret_key = self._get_access_keys()

        self.connection = S3Connection(
            access_key, secret_key, host=self.host,
        )

    @property
    def bucket(self):
        if not hasattr(self, '_bucket'):
            self._bucket = self._get_or_create_bucket(self.bucket_name)
        return self._bucket

    def _get_access_keys(self):
        access_key = ACCESS_KEY_NAME
        secret_key = SECRET_KEY_NAME
        if (access_key or secret_key) and (not access_key or not secret_key):
            access_key = os.environ.get(ACCESS_KEY_NAME)
            secret_key = os.environ.get(SECRET_KEY_NAME)

        if access_key and secret_key:
            # Both were provided, so use them
            return access_key, secret_key

        return None, None

    def _get_host(self, region):
        """
        Returns correctly formatted host. Accepted formats:

            * simple region name, eg 'us-west-1' (see list in AWS_REGIONS)
            * full host name, eg 's3-us-west-1.amazonaws.com'.
        """
        if 'us-east-1' in region:
            return 's3.amazonaws.com'
        elif region in AWS_REGIONS:
            return 's3-%s.amazonaws.com' % region
        elif region and not REGION_RE.findall(region):
            raise ImproperlyConfigured('AWS_REGION improperly configured!')
        # can be full host or empty string, default region
        return  region

    def _get_or_create_bucket(self, name):
        """Retrieves a bucket if it exists, otherwise creates it."""
        try:
            return self.connection.get_bucket(name)
        except S3ResponseError, e:
            if AUTO_CREATE_BUCKET:
                return self.connection.create_bucket(name)
            raise ImproperlyConfigured, ("Bucket specified by "
            "AWS_STORAGE_BUCKET_NAME does not exist. Buckets can be "
            "automatically created by setting AWS_AUTO_CREATE_BUCKET=True")

    def _clean_name(self, name):
        # Useful for windows' paths
        return os.path.normpath(name).replace('\\', '/')

    def _compress_content(self, content):
        """Gzip a given string."""
        zbuf = StringIO()
        zfile = GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
        zfile.write(content.read())
        zfile.close()
        content.file = zbuf
        return content

    def _open(self, name, mode='rb'):
        name = self._clean_name(name)
        return S3BotoStorageFile(name, mode, self)

    def _save(self, name, content):
        name = self._clean_name(name)

        if callable(self.headers):
            headers = self.headers(name, content)
        else:
            headers = self.headers

        if hasattr(content.file, 'content_type'):
            content_type = content.file.content_type
        else:
            content_type = mimetypes.guess_type(name)[0] or "application/x-octet-stream"

        if self.gzip and content_type in self.gzip_content_types:
            content = self._compress_content(content)
            headers.update({'Content-Encoding': 'gzip'})

        headers.update({
            'Content-Type': content_type,
            'Content-Length' : len(content),
        })

        content.name = name
        k = self.bucket.get_key(name)
        if not k:
            k = self.bucket.new_key(name)
        # The callback seen here is particularly important for async WSGI
        # servers. This allows us to call back to eventlet or whatever
        # async support library we're using periodically to prevent timeouts.
        k.set_contents_from_file(content, headers=headers, policy=self.acl,
                                 cb=self.s3_callback_during_upload,
                                 num_cb=-1)
        return name

    def delete(self, name):
        name = self._clean_name(name)
        self.bucket.delete_key(name)

    def exists(self, name):
        name = self._clean_name(name)
        k = Key(self.bucket, name)
        return k.exists()

    def listdir(self, name):
        name = self._clean_name(name)
        return [l.name for l in self.bucket.list() if not len(name) or l.name[:len(name)] == name]

    def size(self, name):
        name = self._clean_name(name)
        return self.bucket.get_key(name).size

    def url(self, name):
        name = self._clean_name(name)
        if self.bucket.get_key(name) is None:
            return ''
        return self.bucket.get_key(name).generate_url(QUERYSTRING_EXPIRE,
                                                      method='GET',
                                                      query_auth=self.querystring_auth,
                                                      force_http=self.force_no_ssl)

    def url_as_attachment(self, name, filename=None):
        name = self._clean_name(name)

        if filename:
            disposition = 'attachment; filename="%s"' % filename
        else:
            disposition = 'attachment;'

        response_headers = {
            'response-content-disposition': disposition,
        }

        return self.connection.generate_url(QUERYSTRING_EXPIRE, 'GET',
                                            bucket=self.bucket.name, key=name,
                                            query_auth=True,
                                            force_http=self.force_no_ssl,
                                            response_headers=response_headers)

    def get_available_name(self, name):
        """ Overwrite existing file with the same name. """
        name = self._clean_name(name)
        return name


class S3BotoStorage_AllPublic(S3BotoStorage):
    """
    Same as S3BotoStorage, but defaults to uploading everything with a
    public acl. This has two primary beenfits:

    1) Non-encrypted requests just make a lot better sense for certain things
       like profile images. Much faster, no need to generate S3 auth keys.
    2) Since we don't have to hit S3 for auth keys, this backend is much
       faster than S3BotoStorage, as it makes no attempt to validate whether
       keys exist.

    WARNING: This backend makes absolutely no attempt to verify whether the
    given key exists on self.url(). This is much faster, but be aware.
    """
    def __init__(self, *args, **kwargs):
        super(S3BotoStorage_AllPublic, self).__init__(acl='public-read',
                                                      querystring_auth=False,
                                                      force_no_ssl=True,
                                                      *args, **kwargs)

    def url(self, name):
        """
        Since we assume all public storage with no authorization keys, we can
        just simply dump out a URL rather than having to query S3 for new keys.
        """
        name = urllib.quote_plus(self._clean_name(name), safe='/')

        if self.bucket_cname:
            return "http://%s/%s" % (self.bucket_cname, name)
        elif self.host:
            return "http://%s/%s/%s" % (self.host, self.bucket_name, name)
        # No host ? Then it's the default region
        return "http://s3.amazonaws.com/%s/%s" % (self.bucket_name, name)


class S3BotoStorageFile(File):
    def __init__(self, name, mode, storage):
        self._storage = storage
        self.name = name
        self._mode = mode
        self.key = storage.bucket.get_key(name)
        self._is_dirty = False
        self.file = StringIO()

    @property
    def size(self):
        if not self.key:
            raise IOError('No such S3 key: %s' % self.name)
        return self.key.size

    def read(self, *args, **kwargs):
        self.file = StringIO()
        self._is_dirty = False
        if not self.key:
            raise IOError('No such S3 key: %s' % self.name)
        self.key.get_contents_to_file(self.file)
        return self.file.getvalue()

    def write(self, content):
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True

    def close(self):
        if self._is_dirty:
            if not self.key:
                self.key = self._storage.bucket.new_key(key_name=self.name)
            self.key.set_contents_from_string(self.file.getvalue(), headers=self._storage.headers, policy=self.storage.acl)
        self.key.close()

########NEW FILE########
__FILENAME__ = s3boto_gunicorn_eventlet
"""
File backends with small tweaks to work with gunicorn + eventlet async
workers. These should eventually becom unecessary as the supporting libraries
continue to improve.
"""
import eventlet
from athumb.backends.s3boto import S3BotoStorage, S3BotoStorage_AllPublic

def eventlet_workaround(bytes_transmitted, bytes_remaining):
    """
    Stinks we have to do this, but calling this at intervals keeps gunicorn
    eventlet async workers from hanging and expiring.
    """
    eventlet.sleep(0)

class EventletS3BotoStorage(S3BotoStorage):
    """
    Modified standard S3BotoStorage class to play nicely with large file
    uploads and eventlet gunicorn workers.
    """
    def __init__(self, *args, **kwargs):
        super(EventletS3BotoStorage, self).__init__(*args, **kwargs)
        # Use the workaround as Boto's set_contents_from_file() callback.
        self.s3_callback_during_upload = eventlet_workaround
        
class EventletS3BotoStorage_AllPublic(S3BotoStorage_AllPublic):
    """
    Modified standard S3BotoStorage_AllPublic class to play nicely with large 
    file uploads and eventlet gunicorn workers.
    """
    def __init__(self, *args, **kwargs):
        super(EventletS3BotoStorage_AllPublic, self).__init__(*args, **kwargs)
        # Use the workaround as Boto's set_contents_from_file() callback.
        self.s3_callback_during_upload = eventlet_workaround
########NEW FILE########
__FILENAME__ = standard_gunicorn_eventlet
"""
File backends with small tweaks to work with gunicorn + eventlet async
workers. These should eventually becom unecessary as the supporting libraries
continue to improve.
"""
import os
import eventlet
from django.conf import settings
from django.core.files import locks
from django.core.files.move import file_move_safe
from django.utils.text import get_valid_filename
from django.core.files.storage import FileSystemStorage

class EventletFileSystemStorage(FileSystemStorage):
    """
    Modified standard FileSystemStorage class to play nicely with large file
    uploads and eventlet gunicorn workers.
    """
    def _save(self, name, content):
        full_path = self.path(name)

        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        elif not os.path.isdir(directory):
            raise IOError("%s exists and is not a directory." % directory)

        # There's a potential race condition between get_available_name and
        # saving the file; it's possible that two threads might return the
        # same name, at which point all sorts of fun happens. So we need to
        # try to create the file, but if it already exists we have to go back
        # to get_available_name() and try again.

        while True:
            try:
                # This file has a file path that we can move.
                if hasattr(content, 'temporary_file_path'):
                    file_move_safe(content.temporary_file_path(), full_path)
                    content.close()

                # This is a normal uploadedfile that we can stream.
                else:
                    # This fun binary flag incantation makes os.open throw an
                    # OSError if the file already exists before we open it.
                    fd = os.open(full_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0))
                    try:
                        locks.lock(fd, locks.LOCK_EX)
                        for chunk in content.chunks():
                            os.write(fd, chunk)
                            # CHANGED: This un-hangs us long enough to keep things rolling.
                            eventlet.sleep(0)
                    finally:
                        locks.unlock(fd)
                        os.close(fd)
            except OSError, e:
                if e.errno == errno.EEXIST:
                    # Ooops, the file exists. We need a new file name.
                    name = self.get_available_name(name)
                    full_path = self.path(name)
                else:
                    raise
            else:
                # OK, the file save worked. Break out of the loop.
                break

        if settings.FILE_UPLOAD_PERMISSIONS is not None:
            os.chmod(full_path, settings.FILE_UPLOAD_PERMISSIONS)

        return name

########NEW FILE########
__FILENAME__ = exceptions
"""
Some top-level exceptions that are generally useful.
"""
class UploadedImageIsUnreadableError(Exception):
    """
    Raise this when the image generation backend can't read the image being
    uploaded. This doesn't necessarily mean that the image is definitely
    mal-formed or corrupt, but the imaging library (as it is compiled) can't
    read it.
    """
    pass
########NEW FILE########
__FILENAME__ = fields
# -*- encoding: utf-8 -*-
"""
Fields, FieldFiles, and Validators.
"""
import os
import cStringIO

from PIL import Image
from django.db.models import ImageField
from django.db.models.fields.files import ImageFieldFile
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from athumb.exceptions import UploadedImageIsUnreadableError
from athumb.pial.engines.pil_engine import PILEngine

from validators import ImageUploadExtensionValidator

try:
    #noinspection PyUnresolvedReferences
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^athumb\.fields\.ImageWithThumbsField"])
except ImportError:
    # Not using South, no big deal.
    pass

# Thumbnailing is done through here. Eventually we can support image libraries
# other than PIL.
THUMBNAIL_ENGINE = PILEngine()

# Cache URLs for thumbnails so we don't have to keep re-generating them.
THUMBNAIL_URL_CACHE_TIME = getattr(settings, 'THUMBNAIL_URL_CACHE_TIME', 3600 * 24)
# Optional cache-buster string to append to end of thumbnail URLs.
MEDIA_CACHE_BUSTER = getattr(settings, 'MEDIA_CACHE_BUSTER', '')

# Models want this instantiated ahead of time.
IMAGE_EXTENSION_VALIDATOR = ImageUploadExtensionValidator()

class ImageWithThumbsFieldFile(ImageFieldFile):
    """
    Serves as the file-level storage object for thumbnails.
    """
    def generate_url(self, thumb_name, ssl_mode=False, check_cache=True, cache_bust=True):
        # This is tacked on to the end of the cache key to make sure SSL
        # URLs are stored separate from plain http.
        ssl_postfix = '_ssl' if ssl_mode else ''

        # Try to see if we can hit the cache instead of asking the storage
        # backend for the URL. This is particularly important for S3 backends.

        cache_key = None

        if check_cache:
            cache_key = "Thumbcache_%s_%s%s" % (self.url,
                                                   thumb_name,
                                                   ssl_postfix)
            cache_key = cache_key.strip()

            cached_val = cache.get(cache_key)
            if cached_val:
                return cached_val

        # Determine what the filename would be for a thumb with these
        # dimensions, regardless of whether it actually exists.
        new_filename = self._calc_thumb_filename(thumb_name)

        # Split URL from GET attribs.
        url_get_split = self.url.rsplit('?', 1)
        # Just the URL string (no GET attribs).
        url_str = url_get_split[0]
        # Get the URL string without the original's filename at the end.
        url_minus_filename = url_str.rsplit('/', 1)[0]

        # Slap the new thumbnail filename on the end of the old URL, in place
        # of the orignal image's filename.
        new_url = "%s/%s" % (url_minus_filename,
                                      os.path.basename(new_filename))

        # Cache busters are a cheezy way to force some browsers to retrieve
        # an updated image, circumventing any long-term or infinite caching
        # you may have set when uploading to S3. This are entirely optional.
        if cache_bust and MEDIA_CACHE_BUSTER:
            new_url = "%s?cbust=%s" % (new_url, MEDIA_CACHE_BUSTER)

        if ssl_mode:
            new_url = new_url.replace('http://', 'https://')

        if cache_key:
            # Cache this so we don't have to hit the storage backend for a while.
            cache.set(cache_key, new_url, THUMBNAIL_URL_CACHE_TIME)

        return new_url

    def get_thumbnail_format(self):
        """
        Determines the target thumbnail type either by looking for a format
        override specified at the model level, or by using the format the
        user uploaded.
        """
        if self.field.thumbnail_format:
            # Over-ride was given, use that instead.
            return self.field.thumbnail_format.lower()
        else:
            # Use the existing extension from the file.
            filename_split = self.name.rsplit('.', 1)
            return filename_split[-1]

    def save(self, name, content, save=True):
        """
        Handles some extra logic to generate the thumbnails when the original
        file is uploaded.
        """
        super(ImageWithThumbsFieldFile, self).save(name, content, save)
        try:
            self.generate_thumbs(name, content)
        except IOError, exc:
            if 'cannot identify' in exc.message or \
               'bad EPS header' in exc.message:
                raise UploadedImageIsUnreadableError(
                    "We were unable to read the uploaded image. "
                    "Please make sure you are uploading a valid image file."
                )
            else:
                raise

    def generate_thumbs(self, name, content):
        # see http://code.djangoproject.com/ticket/8222 for details
        content.seek(0)
        image = Image.open(content)

        # Convert to RGBA (alpha) if necessary
        if image.mode not in ('L', 'RGB', 'RGBA'):
            image = image.convert('RGBA')

        for thumb in self.field.thumbs:
            thumb_name, thumb_options = thumb
            # Pre-create all of the thumbnail sizes.
            self.create_and_store_thumb(image, thumb_name, thumb_options)

    def _calc_thumb_filename(self, thumb_name):
        """
        Calculates the correct filename for a would-be (or potentially
        existing) thumbnail of the given size.
        
        NOTE: This includes the path leading up to the thumbnail. IE:
        uploads/cbid_images/photo.png
        
        size: (tuple) In the format of (width, height)
        
        Returns a string filename.
        """
        filename_split = self.name.rsplit('.', 1)
        file_name = filename_split[0]
        file_extension = self.get_thumbnail_format()

        return '%s_%s.%s' % (file_name, thumb_name, file_extension)

    def create_and_store_thumb(self, image, thumb_name, thumb_options):
        """
        Given that 'image' is a PIL Image object, create a thumbnail for the
        given size tuple and store it via the storage backend.
        
        image: (Image) PIL Image object.
        size: (tuple) Tuple in form of (width, height). Image will be
            thumbnailed to this size.
        """
        size = thumb_options['size']
        upscale = thumb_options.get('upscale', True)
        crop = thumb_options.get('crop')
        if crop is True:
            # We'll just make an assumption here. Center cropping is the
            # typical default.
            crop = 'center'

        thumb_filename = self._calc_thumb_filename(thumb_name)
        file_extension = self.get_thumbnail_format()

        # The work starts here.
        thumbed_image = THUMBNAIL_ENGINE.create_thumbnail(
            image,
            size,
            crop=crop,
            upscale=upscale
        )

        # TODO: Avoiding hitting the disk here, but perhaps we should use temp
        # files down the road? Big images might choke us as we do part in
        # RAM then hit swap.
        img_fobj = cStringIO.StringIO()
        # This writes the thumbnailed PIL.Image to the file-like object.
        THUMBNAIL_ENGINE.write(thumbed_image, img_fobj, format=file_extension)
        # Save the result to the storage backend.
        thumb_content = ContentFile(img_fobj.getvalue())
        self.storage.save(thumb_filename, thumb_content)
        img_fobj.close()

    def delete(self, save=True):
        """
        Deletes the original, plus any thumbnails. Fails silently if there
        are errors deleting the thumbnails.
        """
        for thumb in self.field.thumbs:
            thumb_name, thumb_options = thumb
            thumb_filename = self._calc_thumb_filename(thumb_name)
            self.storage.delete(thumb_filename)

        super(ImageWithThumbsFieldFile, self).delete(save)

class ImageWithThumbsField(ImageField):
    """
    Usage example:
    ==============
    photo = ImageWithThumbsField(upload_to='images', thumbs=((125,125),(300,200),)
        
    Note: The 'thumbs' attribute is not required. If you don't provide it, 
    ImageWithThumbsField will act as a normal ImageField
    """
    attr_class = ImageWithThumbsFieldFile

    def __init__(self, *args, **kwargs):
        self.thumbs = kwargs.pop('thumbs', ())
        self.thumbnail_format = kwargs.pop('thumbnail_format', None)

        if not kwargs.has_key('validators'):
            kwargs['validators'] = [IMAGE_EXTENSION_VALIDATOR]

        if not kwargs.has_key('max_length'):
            kwargs['max_length'] = 255

        super(ImageWithThumbsField, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = athumb_regen_field
import os
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from django.db.models.loading import get_model

class Command(BaseCommand):
    args = '<app.model> <field>'
    help = 'Re-generates thumbnails for all instances of the given model, for the given field.'

    def handle(self, *args, **options):
        self.args = args
        self.options = options

        self.validate_input()
        self.parse_input()
        self.regenerate_thumbs()

    def validate_input(self):
        num_args = len(self.args)

        if num_args < 2:
            raise CommandError("Please pass the app.model and the field to generate thumbnails for.")
        if num_args > 2:
            raise CommandError("Too many arguments provided.")

        if '.' not in self.args[0]:
            raise CommandError("The first argument must be in the format of: app.model")

    def parse_input(self):
        """
        Go through the user input, get/validate some important values.
        """
        app_split = self.args[0].split('.')
        app = app_split[0]
        model_name = app_split[1].lower()
        
        self.model = get_model(app, model_name)

        # String field name to re-generate.
        self.field = self.args[1]

    def regenerate_thumbs(self):
        """
        Handle re-generating the thumbnails. All this involves is reading the
        original file, then saving the same exact thing. Kind of annoying, but
        it's simple.
        """
        Model = self.model
        instances = Model.objects.all()
        num_instances = instances.count()
        # Filenames are keys in here, to help avoid re-genning something that
        # we have already done.
        regen_tracker = {}

        counter = 1
        for instance in instances:
            file = getattr(instance, self.field)
            if not file:
                print "(%d/%d) ID: %d -- Skipped -- No file" % (counter,
                                                                num_instances,
                                                                instance.id)
                counter += 1
                continue

            file_name = os.path.basename(file.name)

            if regen_tracker.has_key(file_name):
                print "(%d/%d) ID: %d -- Skipped -- Already re-genned %s" % (
                                                    counter,
                                                    num_instances,
                                                    instance.id,
                                                    file_name)
                counter += 1
                continue

            # Keep them informed on the progress.
            print "(%d/%d) ID: %d -- %s" % (counter, num_instances,
                                            instance.id, file_name)

            try:
                fdat = file.read()
                file.close()
                del file.file
            except IOError:
                # Key didn't exist.
                print "(%d/%d) ID %d -- Error -- File missing on S3" % (
                                                              counter,
                                                              num_instances,
                                                              instance.id)
                counter += 1
                continue

            try:
                file_contents = ContentFile(fdat)
            except ValueError:
                # This field has no file associated with it, skip it.
                print "(%d/%d) ID %d --  Skipped -- No file on field)" % (
                                                              counter,
                                                              num_instances,
                                                              instance.id)
                counter += 1
                continue

            # Saving pumps it back through the thumbnailer, if this is a
            # ThumbnailField. If not, it's still pretty harmless.

            try:
                file.generate_thumbs(file_name, file_contents)
            except IOError, e:
                print "(%d/%d) ID %d --  Error -- Image may be corrupt)" % (
                    counter,
                    num_instances,
                    instance.id)
                counter += 1
                continue

            regen_tracker[file_name] = True
            counter += 1

########NEW FILE########
__FILENAME__ = models
# Just kidding!
########NEW FILE########
__FILENAME__ = base
#coding=utf-8
from athumb.pial.helpers import toint
from athumb.pial.parsers import parse_crop

class EngineBase(object):
    """
    A base class whose public methods define the public-facing API for all
    EngineBase sub-classes. Do not use this class directly, but instantiate
    and use one of the sub-classes.

    If you're writing a new backend, implement all of the methods seen after
    the comment header 'Methods which engines need to implement'.

    .. note:: Do not instantiate and use this class directly, use one of the
        sub-classes.
    """
    def create_thumbnail(self, image, geometry,
                         upscale=True, crop=None, colorspace='RGB'):
        """
        This serves as a really basic example of a thumbnailing method. You
        may want to implement your own logic, but this will work for
        simple cases.

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param tuple geometry: Geometry of the image in the format of (x,y).
        :keyword str crop: A cropping offset string. This is either one or two
            space-separated values. If only one value is specified, the cropping
            amount (pixels or percentage) for both X and Y dimensions is the
            amount given. If two values are specified, X and Y dimension cropping
            may be set independently. Some examples: '50% 50%', '50px 20px',
            '50%', '50px'.
        :keyword str colorspace: The colorspace to set/convert the image to.
            This is typically 'RGB' or 'GRAY'.
        :returns: The thumbnailed image. The returned type depends on your
            choice of Engine.
        """
        image = self.colorspace(image, colorspace)
        image = self.scale(image, geometry, upscale, crop)
        image = self.crop(image, geometry, crop)

        return image

    def colorspace(self, image, colorspace):
        """
        Sets the image's colorspace. This is typical 'RGB' or 'GRAY', but
        may be other things, depending on your choice of Engine.

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param str colorspace: The colorspace to set/convert the image to.
            This is typically 'RGB' or 'GRAY'.
        :returns: The colorspace-adjusted image. The returned type depends on
            your choice of Engine.
        """
        return self._colorspace(image, colorspace)

    def scale(self, image, geometry, upscale, crop):
        """
        Given an image, scales the image down (or up, if ``upscale`` equates
        to a boolean ``True``).

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param tuple geometry: Geometry of the image in the format of (x,y).
        :returns: The scaled image. The returned type depends on your
            choice of Engine.
        """
        x_image, y_image = map(float, self.get_image_size(image))

        # Calculate scaling factor.
        factors = (geometry[0] / x_image, geometry[1] / y_image)
        factor = max(factors) if crop else min(factors)
        if factor < 1 or upscale:
            width = toint(x_image * factor)
            height = toint(y_image * factor)
            image = self._scale(image, width, height)

        return image

    def crop(self, image, geometry, crop):
        """
        Crops the given ``image``, with dimensions specified in ``geometry``,
        according to the value(s) in ``crop``. Returns the cropped image.

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param tuple geometry: Geometry of the image in the format of (x,y).
        :param str crop: A cropping offset string. This is either one or two
            space-separated values. If only one value is specified, the cropping
            amount (pixels or percentage) for both X and Y dimensions is the
            amount given. If two values are specified, X and Y dimension cropping
            may be set independently. Some examples: '50% 50%', '50px 20px',
            '50%', '50px'.
        :returns: The cropped image. The returned type depends on your
            choice of Engine.
        """
        if not crop:
            return image

        x_image, y_image = self.get_image_size(image)
        x_offset, y_offset = parse_crop(crop, (x_image, y_image), geometry)

        return self._crop(image, geometry[0], geometry[1], x_offset, y_offset)

    def write(self, image, dest_fobj, quality=95, format=None):
        """
        Wrapper for ``_write``

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :keyword int quality: A quality level as a percent. The lower, the
            higher the compression, the worse the artifacts.
        :keyword str format: The format to save to. If omitted, guess based
            on the extension. We recommend specifying this. Typical values
            are 'JPEG', 'GIF', 'PNG'. Other formats largely depend on your
            choice of Engine.
        """
        if isinstance(format, basestring) and format.lower() == 'jpg':
            # This mistake is made all the time. Let's just effectively alias
            # this, since it's commonly used.
            format = 'JPEG'

        raw_data = self._get_raw_data(image, format, quality)
        dest_fobj.write(raw_data)

    def get_image_ratio(self, image):
        """
        Calculates the image ratio (X to Y).

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :rtype: float
        :returns: The X to Y ratio of your image's dimensions.
        """
        x, y = self.get_image_size(image)
        return float(x) / y

    #
    # Methods which engines need to implement
    # The ``image`` argument refers to a backend image object
    #
    def get_image(self, source):
        """
        Given a file-like object, loads it up into the Engine's choice of
        native object and returns it.

        :param file source: A file-like object to load the image from.
        :returns: Your Engine's representation of an Image file.
        """
        raise NotImplemented()

    def get_image_size(self, image):
        """
        Returns the image width and height as a tuple.

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :rtype: tuple
        :returns: Dimensions in the form of (x,y).
        """
        raise NotImplemented()

    def is_valid_image(self, raw_data):
        """
        Checks if the supplied raw data is valid image data.

        :param str raw_data: A string representation of the image data.
        :rtype: bool
        :returns: ``True`` if ``raw_data`` is valid, ``False`` if not.
        """
        raise NotImplemented()

    def _scale(self, image, width, height):
        """
        Given an image, scales the image to the given ``width`` and ``height``.

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param int width: The width of the scaled image.
        :param int height: The height of the scaled image.
        :returns: The scaled image. The returned type depends on your
            choice of Engine.
        """
        raise NotImplemented()

    def _crop(self, image, width, height, x_offset, y_offset):
        """
        Crops the ``image``, starting at ``width`` and ``height``, adding the
        ``x_offset`` and ``y_offset`` to make the crop window.

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param int width: The X plane's start of the crop window.
        :param int height: The Y plane's start of the crop window.
        :param int x_offset: The 'width' of the crop window.
        :param int y_offset: The 'height' of the crop window.
        :returns: The cropped image. The returned type depends on your
            choice of Engine.
        """
        raise NotImplemented()

    def _get_raw_data(self, image, format, quality):
        """
        Gets raw data given the image, format and quality. This method is
        called from :meth:`write`

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param str format: The format to dump the image in. Typical values
            are 'JPEG', 'GIF', and 'PNG', but are dependent upon the Engine.
        :rtype: str
        :returns: The string representation of the image.
        """
        raise NotImplemented()

    def _colorspace(self, image, colorspace):
        """
        Sets the image's colorspace. This is typical 'RGB' or 'GRAY', but
        may be other things, depending on your choice of Engine.

        :param Image image: This is your engine's ``Image`` object. For
            PIL it's PIL.Image.
        :param str colorspace: The colorspace to set/convert the image to.
            This is typically 'RGB' or 'GRAY'.
        :returns: The colorspace-adjusted image. The returned type depends on
            your choice of Engine.
        """
        raise NotImplemented()
########NEW FILE########
__FILENAME__ = pil_engine
from cStringIO import StringIO
from athumb.pial.engines.base import EngineBase

try:
    from PIL import Image, ImageFile, ImageDraw
except ImportError:
    import Image, ImageFile, ImageDraw

class PILEngine(EngineBase):
    """
    Python Imaging Library Engine. This implements members of EngineBase.
    """
    def get_image(self, source):
        """
        Given a file-like object, loads it up into a PIL.Image object
        and returns it.

        :param file source: A file-like object to load the image from.
        :rtype: PIL.Image
        :returns: The loaded image.
        """
        buf = StringIO(source.read())
        return Image.open(buf)

    def get_image_size(self, image):
        """
        Returns the image width and height as a tuple.

        :param PIL.Image image: An image whose dimensions to get.
        :rtype: tuple
        :returns: Dimensions in the form of (x,y).
        """
        return image.size

    def is_valid_image(self, raw_data):
        """
        Checks if the supplied raw data is valid image data.

        :param str raw_data: A string representation of the image data.
        :rtype: bool
        :returns: ``True`` if ``raw_data`` is valid, ``False`` if not.
        """
        buf = StringIO(raw_data)
        try:
            trial_image = Image.open(buf)
            trial_image.verify()
        except Exception:
            # TODO: Get more specific with this exception handling.
            return False
        return True

    def _colorspace(self, image, colorspace):
        """
        Sets the image's colorspace. This is typical 'RGB' or 'GRAY', but
        may be other things, depending on your choice of Engine.

        :param PIL.Image image: The image whose colorspace to adjust.
        :param str colorspace: One of either 'RGB' or 'GRAY'.
        :rtype: PIL.Image
        :returns: The colorspace-adjusted image.
        """
        if colorspace == 'RGB':
            if image.mode == 'RGBA':
                # RGBA is just RGB + Alpha
                return image
            if image.mode == 'P' and 'transparency' in image.info:
                return image.convert('RGBA')
            return image.convert('RGB')
        if colorspace == 'GRAY':
            return image.convert('L')
        return image

    def _scale(self, image, width, height):
        """
        Given an image, scales the image to the given ``width`` and ``height``.

        :param PIL.Image image: The image to scale.
        :param int width: The width of the scaled image.
        :param int height: The height of the scaled image.
        :rtype: PIL.Image
        :returns: The scaled image. 
        """
        return image.resize((width, height), resample=Image.ANTIALIAS)

    def _crop(self, image, width, height, x_offset, y_offset):
        """
        Crops the ``image``, starting at ``width`` and ``height``, adding the
        ``x_offset`` and ``y_offset`` to make the crop window.

        :param PIL.Image image: The image to crop.
        :param int width: The X plane's start of the crop window.
        :param int height: The Y plane's start of the crop window.
        :param int x_offset: The 'width' of the crop window.
        :param int y_offset: The 'height' of the crop window.
        :rtype: PIL.Image
        :returns: The cropped image.
        """
        return image.crop((x_offset, y_offset,
                           width + x_offset, height + y_offset))

    def _get_raw_data(self, image, format, quality):
        """
        Returns the raw data from the Image, which can be directly written
        to a something, be it a file-like object or a database.

        :param PIL.Image image: The image to get the raw data for.
        :param str format: The format to save to. If this value is ``None``,
            PIL will attempt to guess. You're almost always better off
            providing this yourself. For a full list of formats, see the PIL
            handbook at:
            http://www.pythonware.com/library/pil/handbook/index.htm
            The *Appendixes* section at the bottom, in particular.
        :param int quality: A quality level as a percent. The lower, the
            higher the compression, the worse the artifacts. Check the
            format's handbook page for what the different values for this mean.
            For example, JPEG's max quality level is 95, with 100 completely
            disabling JPEG quantization.
        :rtype: str
        :returns: A string representation of the image.
        """
        ImageFile.MAXBLOCK = 1024 * 1024
        buf = StringIO()

        try:
            # ptimize makes the encoder do a second pass over the image, if
            # the format supports it.
            image.save(buf, format=format, quality=quality, optimize=1)
        except IOError:
            # optimize is a no-go, omit it this attempt.
            image.save(buf, format=format, quality=quality)

        raw_data = buf.getvalue()
        buf.close()
        return raw_data


########NEW FILE########
__FILENAME__ = helpers

class ThumbnailError(Exception):
    pass


def toint(number):
    """
    Helper to return rounded int for a float or just the int it self.
    """
    if isinstance(number, float):
        number = round(number, 0)
    return int(number)




########NEW FILE########
__FILENAME__ = parsers
#coding=utf-8
"""
Various functions for parsing user (developer) input. For example, parsing
a cropping a string value of '50% 50%' into cropping offsets.
"""
import re
from athumb.pial.helpers import ThumbnailError

class ThumbnailParseError(ThumbnailError):
    pass

_CROP_PERCENT_PATTERN = re.compile(r'^(?P<value>\d+)(?P<unit>%|px)$')

# The following two alias dicts put percentage values on some common
# X, Y cropping names. For example, center cropping is 50%.
_X_ALIAS_PERCENT = {
    'left': '0%',
    'center': '50%',
    'right': '100%',
}
_Y_ALIAS_PERCENT = {
    'top': '0%',
    'center': '50%',
    'bottom': '100%',
}

def get_cropping_offset(crop, epsilon):
    """
    Calculates the cropping offset for the cropped image. This only calculates
    the offset for one dimension (X or Y). This should be called twice to get
    the offsets for the X and Y dimensions.

    :param str crop: A percentage cropping value for the plane. This is in the
        form of something like '50%'.
    :param float epsilon: The difference between the original image's dimension
        (X or Y) and the desired crop window.
    :rtype: int
    :returns: The cropping offset for the given dimension.
    """
    m = _CROP_PERCENT_PATTERN.match(crop)
    if not m:
        raise ThumbnailParseError('Unrecognized crop option: %s' % crop)
    value = int(m.group('value')) # we only take ints in the regexp
    unit = m.group('unit')
    if unit == '%':
        value = epsilon * value / 100.0
        # return ∈ [0, epsilon]
    return int(max(0, min(value, epsilon)))

def parse_crop(crop, xy_image, xy_window):
    """
    Returns x, y offsets for cropping. The window area should fit inside
    image but it works out anyway

    :param str crop: A cropping offset string. This is either one or two
        space-separated values. If only one value is specified, the cropping
        amount (pixels or percentage) for both X and Y dimensions is the
        amount given. If two values are specified, X and Y dimension cropping
        may be set independently. Some examples: '50% 50%', '50px 20px',
        '50%', '50px'.
    :param tuple xy_image: The (x,y) dimensions of the image.
    :param tuple xy_window: The desired dimensions (x,y) of the cropped image.
    :raises: ThumbnailParseError in the event of invalid input.
    :rtype: tuple of ints
    :returns: A tuple of of offsets for cropping, in (x,y) format.
    """
    # Cropping percentages are space-separated by axis. For example:
    # '50% 75%' would be a 50% cropping ratio for X, and 75% for Y.
    xy_crop = crop.split(' ')
    if len(xy_crop) == 1:
        # Only one dimension was specified, use the same for both planes.
        if crop in _X_ALIAS_PERCENT:
            x_crop = _X_ALIAS_PERCENT[crop]
            y_crop = '50%'
        elif crop in _Y_ALIAS_PERCENT:
            y_crop = _Y_ALIAS_PERCENT[crop]
            x_crop = '50%'
        else:
            x_crop, y_crop = crop, crop
    elif len(xy_crop) == 2:
        # Separate X and Y cropping percentages specified.
        x_crop, y_crop = xy_crop
        x_crop = _X_ALIAS_PERCENT.get(x_crop, x_crop)
        y_crop = _Y_ALIAS_PERCENT.get(y_crop, y_crop)
    else:
        raise ThumbnailParseError('Unrecognized crop option: %s' % crop)

    # We now have cropping percentages for the X and Y planes.
    # Calculate the cropping offsets (in pixels) for each plane.
    offset_x = get_cropping_offset(x_crop, xy_image[0] - xy_window[0])
    offset_y = get_cropping_offset(y_crop, xy_image[1] - xy_window[1])
    return offset_x, offset_y

########NEW FILE########
__FILENAME__ = athumb
from django.template import Library
from thumbnail import thumbnail

register = Library()

register.tag(thumbnail)

########NEW FILE########
__FILENAME__ = thumbnail
"""
Much of this module was taken/inspired from sorl-thumbnails, by mikko and
smileychris. In simple cases, we retain compatibility with sorl-thumbnails, but
we don't generate thumbs on the fly (they are generated at the time of upload,
and only the specified sizes).

Sources from sorl-thumbnails in this module are Copyright (c) 2007, 
Mikko Hellsing, Chris Beaven.

Modifications and new ideas, Copyright (c) 2010, DUO Interactive, LLC.
"""
import re
import math
from django.template import Library, Node, Variable, VariableDoesNotExist, TemplateSyntaxError
from django.conf import settings
from django.utils.encoding import force_unicode

register = Library()

# Various regular expressions compiled here to avoid having to compile them
# repeatedly.
REGEXP_THUMB_SIZES = re.compile(r'(\d+)x(\d+)$')
REGEXP_ARGS = re.compile('(?<!quality)=')

# List of valid keys for key=value tag arguments.
TAG_SETTINGS = ['force_ssl']

def split_args(args):
    """
    Split a list of argument strings into a dictionary where each key is an
    argument name.

    An argument looks like ``force_ssl=True``.
    """
    if not args:
        return {}

    # Handle the old comma separated argument format.
    if len(args) == 1 and not REGEXP_ARGS.search(args[0]):
        args = args[0].split(',')

    # Separate out the key and value for each argument.
    args_dict = {}
    for arg in args:
        split_arg = arg.split('=', 1)
        value = len(split_arg) > 1 and split_arg[1] or None
        args_dict[split_arg[0]] = value

    return args_dict

class ThumbnailNode(Node):
    """
    Handles the rendering of a thumbnail URL, based on the input gathered
    from the thumbnail() tag function.
    """
    def __init__(self, source_var, thumb_name_var, opts=None,
                 context_name=None, **kwargs):
        # Name of the object/attribute pair, ie: some_obj.image
        self.source_var = source_var
        # Typically a string, '85x85'.
        self.thumb_name_var = thumb_name_var

        # If an 'as some_var' is given, this is the context variable name
        # to store the URL in instead of returning it for rendering.
        self.context_name = context_name
        # Storage for optional keyword args processed by the tag parser.
        self.kwargs = kwargs

    def render(self, context):
        try:
            # This evaluates to a ImageWithThumbsField, as long as the
            # user specified a valid model field.
            relative_source = Variable(self.source_var).resolve(context)
        except VariableDoesNotExist:
            if settings.TEMPLATE_DEBUG:
                raise VariableDoesNotExist("Variable '%s' does not exist." %
                        self.source_var)
            else:
                relative_source = None

        try:
            requested_name = Variable(self.thumb_name_var).resolve(context)
        except VariableDoesNotExist:
            if settings.TEMPLATE_DEBUG:
                raise TemplateSyntaxError("Name argument '%s' is not a valid thumbnail." % self.thumb_name_var)
            else:
                requested_name = None

        if relative_source is None or requested_name is None:
            # Couldn't resolve the given template variable. Fail silently.
            thumbnail = ''
        else:
            # Spaces at the end of sizes is just not OK.
            requested_name = requested_name.strip()
            # This is typically a athumb.fields.ImageWithThumbsFieldFile object.
            try:
                # Allow the user to override the protocol in the tag.
                force_ssl = self.kwargs.get('force_ssl', False)
                # Try to detect SSL mode in the request context. Front-facing
                # server or proxy must be passing the correct headers for
                # this to work. Also, factor in force_ssl.
                ssl_mode = self.is_secure(context) or force_ssl
                # Get the URL for the thumbnail from the
                # ImageWithThumbsFieldFile object.
                try:
                    thumbnail = relative_source.generate_url(requested_name,
                                                             ssl_mode=ssl_mode)
                except:
                    #import traceback
                    #traceback.print_stack()
                    print "ERROR: Using {% thumbnail %} tag with "\
                          "a regular ImageField instead of ImageWithThumbsField:", self.source_var
                    return ''
            except ValueError:
                # This file object doesn't actually have a file. Probably
                # model field with a None value.
                thumbnail = ''

        # Return the thumbnail class, or put it on the context
        if self.context_name is None:
            return thumbnail

        # We need to get here so we don't have old values in the context
        # variable.
        context[self.context_name] = thumbnail

        return ''

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


def thumbnail(parser, token):
    """
    Creates a thumbnail of for an ImageField.

    To just output the absolute url to the thumbnail::

        {% thumbnail image 80x80 %}

    After the image path and dimensions, you can put any options::

        {% thumbnail image 80x80 force_ssl=True %}

    To put the thumbnail URL on the context instead of just rendering
    it, finish the tag with ``as [context_var_name]``::

        {% thumbnail image 80x80 as thumb %}
        <img src="{{thumb}}" />
    """
    args = token.split_contents()
    tag = args[0]
    # Check to see if we're setting to a context variable.
    if len(args) > 4 and args[-2] == 'as':
        context_name = args[-1]
        args = args[:-2]
    else:
        context_name = None

    if len(args) < 3:
        raise TemplateSyntaxError("Invalid syntax. Expected "
            "'{%% %s source size [option1 option2 ...] %%}' or "
            "'{%% %s source size [option1 option2 ...] as variable %%}'" %
            (tag, tag))

    # Get the source image path and requested size.

    source_var = args[1]
    # If the size argument was a correct static format, wrap it in quotes so
    # that it is compiled correctly.
    m = REGEXP_THUMB_SIZES.match(args[2])
    if m:
        args[2] = '"%s"' % args[2]
    size_var = args[2]

    # Get the options.
    args_list = split_args(args[3:]).items()

    # Check the options.
    opts = {}
    kwargs = {} # key,values here override settings and defaults

    for arg, value in args_list:
        value = value and parser.compile_filter(value)
        if arg in TAG_SETTINGS and value is not None:
            kwargs[str(arg)] = value
            continue
        else:
            raise TemplateSyntaxError("'%s' tag received a bad argument: "
                                      "'%s'" % (tag, arg))
    return ThumbnailNode(source_var, size_var, opts=opts,
                         context_name=context_name, **kwargs)

register.tag(thumbnail)

########NEW FILE########
__FILENAME__ = gunicorn_eventlet
"""
Upload handlers with small tweaks to work with gunicorn + eventlet async
workers. These should eventually become unnecessary as the supporting libraries
continue to improve.
"""
from django.core.files.uploadhandler import TemporaryFileUploadHandler
import eventlet

class EventletTmpFileUploadHandler(TemporaryFileUploadHandler):
    """
    Uploading large files can cause a worker thread to hang long enough to
    hit the timeout before the upload can be completed. Sleep long enough
    to hand things back to the other threads to avoid a timeout.
    """
    def receive_data_chunk(self, raw_data, start):
        """
        Over-ridden method to circumvent the worker timeouts on large uploads.
        """
        self.file.write(raw_data)
        # CHANGED: This un-hangs us long enough to keep things rolling.
        eventlet.sleep(0)
########NEW FILE########
__FILENAME__ = validators
from django.conf import settings
from django.core.validators import ValidationError

# A list of allowable thumbnail file extensions.
ALLOWABLE_THUMBNAIL_EXTENSIONS = getattr(
    settings, 'ALLOWABLE_THUMBNAIL_EXTENSIONS', ['png', 'jpg', 'jpeg', 'gif'])

class ImageUploadExtensionValidator(object):
    """
    Perform some basic image uploading extension validation.
    """
    compare = lambda self, a, b: a is not b
    clean   = lambda self, x: x

    def __call__(self, value):
        filename = value.name
        filename_split = filename.split('.')
        extension = filename_split[-1]
        
        # Decided to require file extensions.
        if len(filename_split) < 2:
            raise ValidationError(
                "Your file lacks an extension such as .jpg or .png. "
                "Please re-name it on your computer and re-upload it.",
                code='no_extension'
            )

        # Restrict allowable extensions.
        if extension.lower() not in ALLOWABLE_THUMBNAIL_EXTENSIONS:
            # Format for your viewing pleasure.
            allowable_str = ' '.join(ALLOWABLE_THUMBNAIL_EXTENSIONS)
            raise ValidationError(
                "Your file is not one of the allowable types: %s" % allowable_str,
                code='extension_not_allowed'
            )
########NEW FILE########
