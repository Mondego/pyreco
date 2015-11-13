__FILENAME__ = admin
""" Newforms Admin configuration for Photologue

"""
from django.contrib import admin
from django.contrib.contenttypes import generic
from models import *


class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_added', 'photo_count', 'is_public')
    list_filter = ['date_added', 'is_public']
    date_hierarchy = 'date_added'
    prepopulated_fields = {'title_slug': ('title',)}
    filter_horizontal = ('photos',)

class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_taken', 'date_added', 'is_public', 'tags', 'view_count', 'admin_thumbnail')
    list_filter = ['date_added', 'is_public']
    search_fields = ['title', 'title_slug', 'caption']
    list_per_page = 10
    prepopulated_fields = {'title_slug': ('title',)}

class PhotoEffectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color', 'brightness', 'contrast', 'sharpness', 'filters', 'admin_sample')
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Adjustments', {
            'fields': ('color', 'brightness', 'contrast', 'sharpness')
        }),
        ('Filters', {
            'fields': ('filters',)
        }),
        ('Reflection', {
            'fields': ('reflection_size', 'reflection_strength', 'background_color')
        }),
        ('Transpose', {
            'fields': ('transpose_method',)
        }),
    )

class PhotoSizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'width', 'height', 'crop', 'pre_cache', 'effect', 'increment_count')
    fieldsets = (
        (None, {
            'fields': ('name', 'width', 'height', 'quality')
        }),
        ('Options', {
            'fields': ('upscale', 'crop', 'pre_cache', 'increment_count')
        }),
        ('Enhancements', {
            'fields': ('effect', 'watermark',)
        }),
    )


class WatermarkAdmin(admin.ModelAdmin):
    list_display = ('name', 'opacity', 'style')


class GalleryUploadAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return False # To remove the 'Save and continue editing' button

class ImageOverrideInline(generic.GenericTabularInline):
    model = ImageOverride

admin.site.register(Gallery, GalleryAdmin)
admin.site.register(GalleryUpload, GalleryUploadAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(PhotoEffect, PhotoEffectAdmin)
admin.site.register(PhotoSize, PhotoSizeAdmin)
admin.site.register(Watermark, WatermarkAdmin)

########NEW FILE########
__FILENAME__ = plcache
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from photologue.models import PhotoSize, ImageModel

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--reset', '-r', action='store_true', dest='reset', help='Reset photo cache before generating'),
    )

    help = ('Manages Photologue cache file for the given sizes.')
    args = '[sizes]'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return create_cache(args, options)

def create_cache(sizes, options):
    """
    Creates the cache for the given files
    """
    reset = options.get('reset', None)

    size_list = [size.strip(' ,') for size in sizes]

    if len(size_list) < 1:
        sizes = PhotoSize.objects.filter(pre_cache=True)
    else:
        sizes = PhotoSize.objects.filter(name__in=size_list)

    if not len(sizes):
        raise CommandError('No photo sizes were found.')

    print 'Caching photos, this may take a while...'

    for cls in ImageModel.__subclasses__():
        for photosize in sizes:
            print 'Cacheing %s size images' % photosize.name
            for obj in cls.objects.all():
                if reset:
                    obj.remove_size(photosize)
                obj.create_size(photosize)

########NEW FILE########
__FILENAME__ = plcreatesize
from django.core.management.base import BaseCommand, CommandError
from photologue.management.commands import create_photosize

class Command(BaseCommand):
    help = ('Creates a new Photologue photo size interactively.')
    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        create_size(args[0])

def create_size(size):
    create_photosize(size)

########NEW FILE########
__FILENAME__ = plflush
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from photologue.models import PhotoSize, ImageModel

class Command(BaseCommand):
    help = ('Clears the Photologue cache for the given sizes.')
    args = '[sizes]'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        return create_cache(args, options)

def create_cache(sizes, options):
    """
    Clears the cache for the given files
    """
    size_list = [size.strip(' ,') for size in sizes]

    if len(size_list) < 1:
        sizes = PhotoSize.objects.all()
    else:
        sizes = PhotoSize.objects.filter(name__in=size_list)

    if not len(sizes):
        raise CommandError('No photo sizes were found.')

    print 'Flushing cache...'

    for cls in ImageModel.__subclasses__():
        for photosize in sizes:
            print 'Flushing %s size images' % photosize.name
            for obj in cls.objects.all():
                obj.remove_size(photosize)

########NEW FILE########
__FILENAME__ = plinit
from django.core.management.base import BaseCommand, CommandError
from photologue.management.commands import get_response, create_photosize
from photologue.models import PhotoEffect

class Command(BaseCommand):
    help = ('Prompts the user to set up the default photo sizes required by Photologue.')
    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **kwargs):
        return init(*args, **kwargs)

def init(*args, **kwargs):
    msg = '\nPhotologue requires a specific photo size to display thumbnail previews in the Django admin application.\nWould you like to generate this size now? (yes, no):'
    if get_response(msg, lambda inp: inp == 'yes', False):
        admin_thumbnail = create_photosize('admin_thumbnail', width=100, height=75, crop=True, pre_cache=True)
        msg = 'Would you like to apply a sample enhancement effect to your admin thumbnails? (yes, no):'
        if get_response(msg, lambda inp: inp == 'yes', False):
            effect, created = PhotoEffect.objects.get_or_create(name='Enhance Thumbnail', description="Increases sharpness and contrast. Works well for smaller image sizes such as thumbnails.", contrast=1.2, sharpness=1.3)
            admin_thumbnail.effect = effect
            admin_thumbnail.save()
    msg = '\nPhotologue comes with a set of templates for setting up a complete photo gallery. These templates require you to define both a "thumbnail" and "display" size.\nWould you like to define them now? (yes, no):'
    if get_response(msg, lambda inp: inp == 'yes', False):
        thumbnail = create_photosize('thumbnail', width=100, height=75)
        display = create_photosize('display', width=400, increment_count=True)
        msg = 'Would you like to apply a sample reflection effect to your display images? (yes, no):'
        if get_response(msg, lambda inp: inp == 'yes', False):
            effect, created = PhotoEffect.objects.get_or_create(name='Display Reflection', description="Generates a reflection with a white background", reflection_size=0.4)
            display.effect = effect
            display.save()
########NEW FILE########
__FILENAME__ = models
import os
import random
import shutil
import zipfile
import utils
import unicodedata
import logging

from datetime import datetime
from inspect import isclass

from django.db import models
from django.db.models.signals import post_init
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.utils.encoding import smart_str, force_unicode
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _

# Required PIL classes may or may not be available from the root namespace
# depending on the installation method used.
try:
    import Image
    import ImageFile
    import ImageFilter
    import ImageEnhance
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageFile
        from PIL import ImageFilter
        from PIL import ImageEnhance
    except ImportError:
        raise ImportError('Photologue was unable to import the Python Imaging Library. Please confirm it`s installed and available on your current Python path.')

# attempt to load the django-tagging TagField from default location,
# otherwise we substitude a dummy TagField.
try:
    from tagging.fields import TagField
    tagfield_help_text = _('Separate tags with spaces, put quotes around multiple-word tags.')
except ImportError:
    class TagField(models.CharField):
        def __init__(self, **kwargs):
            default_kwargs = {'max_length': 255, 'blank': True}
            default_kwargs.update(kwargs)
            super(TagField, self).__init__(**default_kwargs)
        def get_internal_type(self):
            return 'CharField'
    tagfield_help_text = _('Django-tagging was not found, tags will be treated as plain text.')

from utils import EXIF
from utils.reflection import add_reflection
from utils.watermark import apply_watermark

# Default limit for gallery.latest
LATEST_LIMIT = getattr(settings, 'PHOTOLOGUE_GALLERY_LATEST_LIMIT', None)

# max_length setting for the ImageModel ImageField
IMAGE_FIELD_MAX_LENGTH = getattr(settings, 'PHOTOLOGUE_IMAGE_FIELD_MAX_LENGTH', 100)

# Path to sample image
SAMPLE_IMAGE_PATH = getattr(settings, 'SAMPLE_IMAGE_PATH', os.path.join(os.path.dirname(__file__), 'res', 'sample.jpg')) # os.path.join(settings.PROJECT_PATH, 'photologue', 'res', 'sample.jpg'

# Modify image file buffer size.
ImageFile.MAXBLOCK = getattr(settings, 'PHOTOLOGUE_MAXBLOCK', 256 * 2 ** 10)

# Photologue image path relative to media root
PHOTOLOGUE_DIR = getattr(settings, 'PHOTOLOGUE_DIR', 'photologue')

# Look for user function to define file paths
PHOTOLOGUE_PATH = getattr(settings, 'PHOTOLOGUE_PATH', None)
if PHOTOLOGUE_PATH is not None:
    if callable(PHOTOLOGUE_PATH):
        get_storage_path = PHOTOLOGUE_PATH
    else:
        parts = PHOTOLOGUE_PATH.split('.')
        module_name = '.'.join(parts[:-1])
        module = __import__(module_name)
        get_storage_path = getattr(module, parts[-1])
else:
    def get_storage_path(instance, filename):
        fn = unicodedata.normalize('NFKD', force_unicode(filename)).encode('ascii', 'ignore')
        return os.path.join(PHOTOLOGUE_DIR, 'photos', fn)

# Quality options for JPEG images
JPEG_QUALITY_CHOICES = (
    (30, _('Very Low')),
    (40, _('Low')),
    (50, _('Medium-Low')),
    (60, _('Medium')),
    (70, _('Medium-High')),
    (80, _('High')),
    (90, _('Very High')),
)

# choices for new crop_anchor field in Photo
CROP_ANCHOR_CHOICES = (
    ('top', _('Top')),
    ('right', _('Right')),
    ('bottom', _('Bottom')),
    ('left', _('Left')),
    ('center', _('Center (Default)')),
)

IMAGE_TRANSPOSE_CHOICES = (
    ('FLIP_LEFT_RIGHT', _('Flip left to right')),
    ('FLIP_TOP_BOTTOM', _('Flip top to bottom')),
    ('ROTATE_90', _('Rotate 90 degrees counter-clockwise')),
    ('ROTATE_270', _('Rotate 90 degrees clockwise')),
    ('ROTATE_180', _('Rotate 180 degrees')),
)

WATERMARK_STYLE_CHOICES = (
    ('tile', _('Tile')),
    ('scale', _('Scale')),
)

# Prepare a list of image filters
filter_names = []
for n in dir(ImageFilter):
    klass = getattr(ImageFilter, n)
    if isclass(klass) and issubclass(klass, ImageFilter.BuiltinFilter) and \
        hasattr(klass, 'name'):
            filter_names.append(klass.__name__)
IMAGE_FILTERS_HELP_TEXT = _('Chain multiple filters using the following pattern "FILTER_ONE->FILTER_TWO->FILTER_THREE". Image filters will be applied in order. The following filters are available: %s.' % (', '.join(filter_names)))

size_method_map = {}

logger = logging.getLogger(__name__)


class Gallery(models.Model):
    date_added = models.DateTimeField(_('date published'), default=datetime.now)
    title = models.CharField(_('title'), max_length=100, unique=True)
    title_slug = models.SlugField(_('title slug'), unique=True,
                                  help_text=_('A "slug" is a unique URL-friendly title for an object.'))
    description = models.TextField(_('description'), blank=True)
    is_public = models.BooleanField(_('is public'), default=True,
                                    help_text=_('Public galleries will be displayed in the default views.'))
    photos = models.ManyToManyField('Photo', related_name='galleries', verbose_name=_('photos'),
                                    null=True, blank=True)
    tags = TagField(help_text=tagfield_help_text, verbose_name=_('tags'))

    class Meta:
        ordering = ['-date_added']
        get_latest_by = 'date_added'
        verbose_name = _('gallery')
        verbose_name_plural = _('galleries')

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.__unicode__()

    def get_absolute_url(self):
        return reverse('pl-gallery', args=[self.title_slug])

    def latest(self, limit=LATEST_LIMIT, public=True):
        if not limit:
            limit = self.photo_count()
        if public:
            return self.public()[:limit]
        else:
            return self.photos.all()[:limit]

    def sample(self, count=0, public=True):
        if count == 0 or count > self.photo_count():
            count = self.photo_count()
        if public:
            photo_set = self.public()
        else:
            photo_set = self.photos.all()
        return random.sample(photo_set, count)

    def photo_count(self, public=True):
        if public:
            return self.public().count()
        else:
            return self.photos.all().count()
    photo_count.short_description = _('count')

    def public(self):
        return self.photos.filter(is_public=True)


class GalleryUpload(models.Model):
    zip_file = models.FileField(_('images file (.zip)'), upload_to=PHOTOLOGUE_DIR+"/temp",
                                help_text=_('Select a .zip file of images to upload into a new Gallery.'))
    gallery = models.ForeignKey(Gallery, null=True, blank=True, help_text=_('Select a gallery to add these images to. leave this empty to create a new gallery from the supplied title.'))
    title = models.CharField(_('title'), max_length=75, help_text=_('All photos in the gallery will be given a title made up of the gallery title + a sequential number.'))
    caption = models.TextField(_('caption'), blank=True, help_text=_('Caption will be added to all photos.'))
    description = models.TextField(_('description'), blank=True, help_text=_('A description of this Gallery.'))
    is_public = models.BooleanField(_('is public'), default=True, help_text=_('Uncheck this to make the uploaded gallery and included photographs private.'))
    tags = models.CharField(max_length=255, blank=True, help_text=tagfield_help_text, verbose_name=_('tags'))

    class Meta:
        verbose_name = _('gallery upload')
        verbose_name_plural = _('gallery uploads')

    def save(self, *args, **kwargs):
        super(GalleryUpload, self).save(*args, **kwargs)
        gallery = self.process_zipfile()
        super(GalleryUpload, self).delete()
        return gallery

    def process_zipfile(self):
        if os.path.isfile(self.zip_file.path):
            # TODO: implement try-except here
            zip = zipfile.ZipFile(self.zip_file.path)
            bad_file = zip.testzip()
            if bad_file:
                raise Exception('"%s" in the .zip archive is corrupt.' % bad_file)
            count = 1
            if self.gallery:
                gallery = self.gallery
            else:
                gallery = Gallery.objects.create(title=self.title,
                                                 title_slug=slugify(self.title),
                                                 description=self.description,
                                                 is_public=self.is_public,
                                                 tags=self.tags)
            from cStringIO import StringIO
            for filename in sorted(zip.namelist()):
                if filename.startswith('__'): # do not process meta files
                    continue
                data = zip.read(filename)
                if len(data):
                    try:
                        # the following is taken from django.newforms.fields.ImageField:
                        #  load() is the only method that can spot a truncated JPEG,
                        #  but it cannot be called sanely after verify()
                        trial_image = Image.open(StringIO(data))
                        trial_image.load()
                        # verify() is the only method that can spot a corrupt PNG,
                        #  but it must be called immediately after the constructor
                        trial_image = Image.open(StringIO(data))
                        trial_image.verify()
                    except Exception:
                        # if a "bad" file is found we just skip it.
                        continue
                    while 1:
                        title = ' '.join([self.title, str(count)])
                        slug = slugify(title)
                        try:
                            p = Photo.objects.get(title_slug=slug)
                        except Photo.DoesNotExist:
                            photo = Photo(title=title,
                                          title_slug=slug,
                                          caption=self.caption,
                                          is_public=self.is_public,
                                          tags=self.tags)
                            photo.image.save(filename, ContentFile(data))
                            gallery.photos.add(photo)
                            count = count + 1
                            break
                        count = count + 1
            zip.close()
            return gallery


class ImageModel(models.Model):
    image = models.ImageField(_('image'), max_length=IMAGE_FIELD_MAX_LENGTH,
                              upload_to=get_storage_path, blank=True)
    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True, editable=False)
    view_count = models.PositiveIntegerField(default=0, editable=False)
    crop_from = models.CharField(_('crop from'), blank=True, max_length=10, default='center', choices=CROP_ANCHOR_CHOICES)
    effect = models.ForeignKey('PhotoEffect', null=True, blank=True, related_name="%(class)s_related", verbose_name=_('effect'))

    class Meta:
        abstract = True

    @property
    def EXIF(self):
        try:
            return EXIF.process_file(open(self.image.path, 'rb'))
        except:
            try:
                return EXIF.process_file(open(self.image.path, 'rb'), details=False)
            except:
                return {}

    def admin_thumbnail(self):
        func = getattr(self, 'get_admin_thumbnail_url', None)
        if func is None:
            return _('An "admin_thumbnail" photo size has not been defined.')
        else:
            if hasattr(self, 'get_absolute_url'):
                return u'<a href="%s"><img src="%s"></a>' % \
                    (self.get_absolute_url(), func())
            else:
                return u'<a href="%s"><img src="%s"></a>' % \
                    (self.image.url, func()) if self.image else ''
    admin_thumbnail.short_description = _('Thumbnail')
    admin_thumbnail.allow_tags = True

    def cache_path(self):
        try:
            return os.path.join(os.path.dirname(self.image.path), "cache")
        except ValueError:
            ""

    def cache_url(self):
        return '/'.join([os.path.dirname(self.image.url), "cache"])

    def image_filename(self):
        return os.path.basename(force_unicode(self.image.path))

    def _get_filename_for_size(self, size):
        size = getattr(size, 'name', size)
        base, ext = os.path.splitext(self.image_filename())
        return ''.join([base, '_', size, ext])

    def _get_SIZE_photosize(self, size):
        return PhotoSizeCache().sizes.get(size)

    def _get_SIZE_size(self, size):
        photosize = PhotoSizeCache().sizes.get(size)
        if not self.size_exists(photosize):
            self.create_size(photosize)
        return Image.open(self._get_SIZE_filename(size)).size

    def _get_SIZE_url(self, size):
        photosize = PhotoSizeCache().sizes.get(size)
        if not self.size_exists(photosize):
            self.create_size(photosize)
        if photosize.increment_count:
            self.increment_count()
        if not self.image:
            return
        return '/'.join([self.cache_url(), self._get_filename_for_size(photosize.name)])

    def _get_SIZE_filename(self, size):
        photosize = PhotoSizeCache().sizes.get(size)
        return smart_str(os.path.join(self.cache_path(),
                            self._get_filename_for_size(photosize.name)))

    def increment_count(self):
        self.view_count += 1
        models.Model.save(self)

    def add_accessor_methods(self, *args, **kwargs):
        for size in PhotoSizeCache().sizes.keys():
            setattr(self, 'get_%s_size' % size,
                    curry(self._get_SIZE_size, size=size))
            setattr(self, 'get_%s_photosize' % size,
                    curry(self._get_SIZE_photosize, size=size))
            setattr(self, 'get_%s_url' % size,
                    curry(self._get_SIZE_url, size=size))
            setattr(self, 'get_%s_filename' % size,
                    curry(self._get_SIZE_filename, size=size))

    def __getattr__(self, name):
        global size_method_map
        if not size_method_map:
            init_size_method_map()
        di = size_method_map.get(name, None)
        if di is not None:
            result = curry(getattr(self, di['base_name']), di['size'])
            setattr(self, name, result)
            return result
        else:
            raise AttributeError

    def size_exists(self, photosize):
        func = getattr(self, "get_%s_filename" % photosize.name, None)
        if func is not None:
            try:
                if os.path.isfile(func()):
                    return True
            except ValueError:
                return False
        return False

    def resize_image(self, im, photosize):
        cur_width, cur_height = im.size
        new_width, new_height = photosize.size
        if photosize.crop:
            ratio = max(float(new_width)/cur_width,float(new_height)/cur_height)
            x = (cur_width * ratio)
            y = (cur_height * ratio)
            xd = abs(new_width - x)
            yd = abs(new_height - y)
            x_diff = int(xd / 2)
            y_diff = int(yd / 2)
            if self.crop_from == 'top':
                box = (int(x_diff), 0, int(x_diff+new_width), new_height)
            elif self.crop_from == 'left':
                box = (0, int(y_diff), new_width, int(y_diff+new_height))
            elif self.crop_from == 'bottom':
                box = (int(x_diff), int(yd), int(x_diff+new_width), int(y)) # y - yd = new_height
            elif self.crop_from == 'right':
                box = (int(xd), int(y_diff), int(x), int(y_diff+new_height)) # x - xd = new_width
            else:
                box = (int(x_diff), int(y_diff), int(x_diff+new_width), int(y_diff+new_height))
            im = im.resize((int(x), int(y)), Image.ANTIALIAS).crop(box)
        else:
            if not new_width == 0 and not new_height == 0:
                ratio = min(float(new_width)/cur_width,
                            float(new_height)/cur_height)
            else:
                if new_width == 0:
                    ratio = float(new_height)/cur_height
                else:
                    ratio = float(new_width)/cur_width
            new_dimensions = (int(round(cur_width*ratio)),
                              int(round(cur_height*ratio)))
            if new_dimensions[0] > cur_width or \
               new_dimensions[1] > cur_height:
                if not photosize.upscale:
                    return im
            im = im.resize(new_dimensions, Image.ANTIALIAS)
        return im

    def get_override(self, photosize):
        """
        Returns the first ImageOverride object found for this object and photosize.
        """
        content_type = ContentType.objects.get_for_model(self)
        overrides = ImageOverride.objects.filter(object_id=self.id, content_type=content_type, photosize=photosize)
        if overrides:
            return overrides[0]
        else:
            return None

    def create_size(self, photosize):
        # Fail gracefully if we don't have an image.
        if not self.image:
            return

        if self.size_exists(photosize):
            return
        if not os.path.isdir(self.cache_path()):
            os.makedirs(self.cache_path())

        # check if we have overrides and use that instead
        override = self.get_override(photosize)
        image_model_obj = override if override else self

        try:
            im = Image.open(image_model_obj.image.path)
        except IOError:
            return
        # Correct colorspace
        im = utils.colorspace(im)
        # Save the original format
        im_format = im.format
        # Apply effect if found
        if image_model_obj.effect is not None:
            im = image_model_obj.effect.pre_process(im)
        elif photosize.effect is not None:
            im = photosize.effect.pre_process(im)
        # Resize/crop image
        if im.size != photosize.size and photosize.size != (0, 0):
            im = image_model_obj.resize_image(im, photosize)
        # Apply watermark if found
        if photosize.watermark is not None:
            im = photosize.watermark.post_process(im)
        # Apply effect if found
        if image_model_obj.effect is not None:
            im = image_model_obj.effect.post_process(im)
        elif photosize.effect is not None:
            im = photosize.effect.post_process(im)
        # Save file
        im_filename = getattr(self, "get_%s_filename" % photosize.name)()
        try:
            if im_format != 'JPEG':
                try:
                    im.save(im_filename)
                    return
                except KeyError:
                    pass
            im.save(im_filename, 'JPEG', quality=int(photosize.quality), optimize=True)
        except IOError, e:
            # Attempt to clean up.
            if os.path.isfile(im_filename):
                try:
                    os.unlink(im_filename)
                except OSError:
                    pass
            # Log the error but don't raise it
            logger.error("Cannot create size %s for %s" \
                % (photosize.name, image_model_obj.image.path)
            )


    def remove_size(self, photosize, remove_dirs=True):
        if not self.size_exists(photosize):
            return
        filename = getattr(self, "get_%s_filename" % photosize.name)()
        if os.path.isfile(filename):
            os.remove(filename)
        if remove_dirs:
            self.remove_cache_dirs()

    def clear_cache(self):
        cache = PhotoSizeCache()
        for photosize in cache.sizes.values():
            self.remove_size(photosize, False)
        self.remove_cache_dirs()

    def pre_cache(self):
        cache = PhotoSizeCache()
        for photosize in cache.sizes.values():
            if photosize.pre_cache:
                self.create_size(photosize)

    def remove_cache_dirs(self):
        try:
            os.removedirs(self.cache_path())
        except:
            pass

    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.EXIF.get('EXIF DateTimeOriginal', None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    self.date_taken = datetime(int(year), int(month), int(day),
                                               int(hour), int(minute), int(second))
            except:
                pass
        if self.date_taken is None:
            self.date_taken = datetime.now()
        if self._get_pk_val():
            self.clear_cache()
        super(ImageModel, self).save(*args, **kwargs)
        self.pre_cache()

    def delete(self):
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)
        self.clear_cache()
        os.remove(self.image.path)
        super(ImageModel, self).delete()


from django.contrib.contenttypes import generic

class ImageOverride(ImageModel):
    content_type = models.ForeignKey('contenttypes.ContentType')
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey("content_type", "object_id")
    photosize = models.ForeignKey('photologue.PhotoSize')

    class Meta():
        verbose_name = "image override"
        verbose_name_plural = "image overrides"

class Photo(ImageModel):
    title = models.CharField(_('title'), max_length=100, unique=True)
    title_slug = models.SlugField(_('slug'), unique=True,
                                  help_text=('A "slug" is a unique URL-friendly title for an object.'))
    caption = models.TextField(_('caption'), blank=True)
    date_added = models.DateTimeField(_('date added'), default=datetime.now, editable=False)
    is_public = models.BooleanField(_('is public'), default=True, help_text=_('Public photographs will be displayed in the default views.'))
    tags = TagField(help_text=tagfield_help_text, verbose_name=_('tags'))

    class Meta:
        ordering = ['-date_added']
        get_latest_by = 'date_added'
        verbose_name = _("photo")
        verbose_name_plural = _("photos")

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.__unicode__()

    def save(self, *args, **kwargs):
        if self.title_slug is None:
            self.title_slug = slugify(self.title)
        super(Photo, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('pl-photo', args=[self.title_slug])

    def public_galleries(self):
        """Return the public galleries to which this photo belongs."""
        return self.galleries.filter(is_public=True)

    def get_previous_in_gallery(self, gallery):
        try:
            return self.get_previous_by_date_added(galleries__exact=gallery,
                                                   is_public=True)
        except Photo.DoesNotExist:
            return None

    def get_next_in_gallery(self, gallery):
        try:
            return self.get_next_by_date_added(galleries__exact=gallery,
                                               is_public=True)
        except Photo.DoesNotExist:
            return None


class BaseEffect(models.Model):
    name = models.CharField(_('name'), max_length=30, unique=True)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        abstract = True

    def sample_dir(self):
        return os.path.join(settings.MEDIA_ROOT, PHOTOLOGUE_DIR, 'samples')

    def sample_url(self):
        return settings.MEDIA_URL + '/'.join([PHOTOLOGUE_DIR, 'samples', '%s %s.jpg' % (self.name.lower(), 'sample')])

    def sample_filename(self):
        return os.path.join(self.sample_dir(), '%s %s.jpg' % (self.name.lower(), 'sample'))

    def create_sample(self):
        if not os.path.isdir(self.sample_dir()):
            os.makedirs(self.sample_dir())
        try:
            im = Image.open(SAMPLE_IMAGE_PATH)
        except IOError:
            raise IOError('Photologue was unable to open the sample image: %s.' % SAMPLE_IMAGE_PATH)
        im = self.process(im)
        im.save(self.sample_filename(), 'JPEG', quality=90, optimize=True)

    def admin_sample(self):
        return u'<img src="%s">' % self.sample_url()
    admin_sample.short_description = 'Sample'
    admin_sample.allow_tags = True

    def pre_process(self, im):
        return im

    def post_process(self, im):
        return im

    def process(self, im):
        im = self.pre_process(im)
        im = self.post_process(im)
        return im

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__()

    def save(self, *args, **kwargs):
        try:
            os.remove(self.sample_filename())
        except:
            pass
        models.Model.save(self, *args, **kwargs)
        self.create_sample()
        for size in self.photo_sizes.all():
            size.clear_cache()
        # try to clear all related subclasses of ImageModel
        for prop in [prop for prop in dir(self) if prop[-8:] == '_related']:
            for obj in getattr(self, prop).all():
                obj.clear_cache()
                obj.pre_cache()

    def delete(self):
        try:
            os.remove(self.sample_filename())
        except:
            pass
        models.Model.delete(self)


class PhotoEffect(BaseEffect):
    """ A pre-defined effect to apply to photos """
    transpose_method = models.CharField(_('rotate or flip'), max_length=15, blank=True, choices=IMAGE_TRANSPOSE_CHOICES)
    color = models.FloatField(_('color'), default=1.0, help_text=_("A factor of 0.0 gives a black and white image, a factor of 1.0 gives the original image."))
    brightness = models.FloatField(_('brightness'), default=1.0, help_text=_("A factor of 0.0 gives a black image, a factor of 1.0 gives the original image."))
    contrast = models.FloatField(_('contrast'), default=1.0, help_text=_("A factor of 0.0 gives a solid grey image, a factor of 1.0 gives the original image."))
    sharpness = models.FloatField(_('sharpness'), default=1.0, help_text=_("A factor of 0.0 gives a blurred image, a factor of 1.0 gives the original image."))
    filters = models.CharField(_('filters'), max_length=200, blank=True, help_text=_(IMAGE_FILTERS_HELP_TEXT))
    reflection_size = models.FloatField(_('size'), default=0, help_text=_("The height of the reflection as a percentage of the orignal image. A factor of 0.0 adds no reflection, a factor of 1.0 adds a reflection equal to the height of the orignal image."))
    reflection_strength = models.FloatField(_('strength'), default=0.6, help_text=_("The initial opacity of the reflection gradient."))
    background_color = models.CharField(_('color'), max_length=7, default="#FFFFFF", help_text=_("The background color of the reflection gradient. Set this to match the background color of your page."))

    class Meta:
        verbose_name = _("photo effect")
        verbose_name_plural = _("photo effects")

    def pre_process(self, im):
        if self.transpose_method != '':
            method = getattr(Image, self.transpose_method)
            im = im.transpose(method)
        if im.mode != 'RGB' and im.mode != 'RGBA':
            return im
        for name in ['Color', 'Brightness', 'Contrast', 'Sharpness']:
            factor = getattr(self, name.lower())
            if factor != 1.0:
                im = getattr(ImageEnhance, name)(im).enhance(factor)
        for name in self.filters.split('->'):
            image_filter = getattr(ImageFilter, name.upper(), None)
            if image_filter is not None:
                try:
                    im = im.filter(image_filter)
                except ValueError:
                    pass
        return im

    def post_process(self, im):
        if self.reflection_size != 0.0:
            im = add_reflection(im, bgcolor=self.background_color, amount=self.reflection_size, opacity=self.reflection_strength)
        return im


class Watermark(BaseEffect):
    image = models.ImageField(_('image'), upload_to=PHOTOLOGUE_DIR+"/watermarks")
    style = models.CharField(_('style'), max_length=5, choices=WATERMARK_STYLE_CHOICES, default='scale')
    opacity = models.FloatField(_('opacity'), default=1, help_text=_("The opacity of the overlay."))

    class Meta:
        verbose_name = _('watermark')
        verbose_name_plural = _('watermarks')

    def post_process(self, im):
        mark = Image.open(self.image.path)
        return apply_watermark(im, mark, self.style, self.opacity)


class PhotoSize(models.Model):
    name = models.CharField(_('name'), max_length=64, unique=True, help_text=_('Photo size name should contain only letters, numbers and underscores. Examples: "thumbnail", "display", "small", "main_page_widget".'))
    width = models.PositiveIntegerField(_('width'), default=0, help_text=_('If width is set to "0" the image will be scaled to the supplied height.'))
    height = models.PositiveIntegerField(_('height'), default=0, help_text=_('If height is set to "0" the image will be scaled to the supplied width'))
    quality = models.PositiveIntegerField(_('quality'), choices=JPEG_QUALITY_CHOICES, default=70, help_text=_('JPEG image quality.'))
    upscale = models.BooleanField(_('upscale images?'), default=False, help_text=_('If selected the image will be scaled up if necessary to fit the supplied dimensions. Cropped sizes will be upscaled regardless of this setting.'))
    crop = models.BooleanField(_('crop to fit?'), default=False, help_text=_('If selected the image will be scaled and cropped to fit the supplied dimensions.'))
    pre_cache = models.BooleanField(_('pre-cache?'), default=False, help_text=_('If selected this photo size will be pre-cached as photos are added.'))
    increment_count = models.BooleanField(_('increment view count?'), default=False, help_text=_('If selected the image\'s "view_count" will be incremented when this photo size is displayed.'))
    effect = models.ForeignKey('PhotoEffect', null=True, blank=True, related_name='photo_sizes', verbose_name=_('photo effect'))
    watermark = models.ForeignKey('Watermark', null=True, blank=True, related_name='photo_sizes', verbose_name=_('watermark image'))

    class Meta:
        ordering = ['width', 'height']
        verbose_name = _('photo size')
        verbose_name_plural = _('photo sizes')

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__()

    def clear_cache(self):
        for cls in ImageModel.__subclasses__():
            if not cls._meta.abstract:
                for obj in cls.objects.all():
                    obj.remove_size(self)
                    if self.pre_cache:
                        obj.create_size(self)
        PhotoSizeCache().reset()

    def save(self, *args, **kwargs):
        if self.crop is True:
            if self.width == 0 or self.height == 0:
                raise ValueError("PhotoSize width and/or height can not be zero if crop=True.")
        super(PhotoSize, self).save(*args, **kwargs)
        PhotoSizeCache().reset()
        self.clear_cache()

    def delete(self):
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)
        self.clear_cache()
        super(PhotoSize, self).delete()

    def _get_size(self):
        return (self.width, self.height)
    def _set_size(self, value):
        self.width, self.height = value
    size = property(_get_size, _set_size)


class PhotoSizeCache(object):
    __state = {"sizes": {}}

    def __init__(self):
        self.__dict__ = self.__state
        if not len(self.sizes):
            sizes = PhotoSize.objects.all()
            for size in sizes:
                self.sizes[size.name] = size

    def reset(self):
        global size_method_map
        size_method_map = {}
        self.sizes = {}


def init_size_method_map():
    global size_method_map
    for size in PhotoSizeCache().sizes.keys():
        size_method_map['get_%s_size' % size] = {'base_name': '_get_SIZE_size', 'size': size}
        size_method_map['get_%s_photosize' % size] = {'base_name': '_get_SIZE_photosize', 'size': size}
        size_method_map['get_%s_url' % size] = {'base_name': '_get_SIZE_url', 'size': size}
        size_method_map['get_%s_filename' % size] = {'base_name': '_get_SIZE_filename', 'size': size}

########NEW FILE########
__FILENAME__ = photologue_tags
from django import template

register = template.Library()

@register.inclusion_tag('photologue/tags/next_in_gallery.html')
def next_in_gallery(photo, gallery):
    return {'photo': photo.get_next_in_gallery(gallery)}

@register.inclusion_tag('photologue/tags/prev_in_gallery.html')
def previous_in_gallery(photo, gallery):
    return {'photo': photo.get_previous_in_gallery(gallery)}

########NEW FILE########
__FILENAME__ = tests
# coding=utf-8

import os
import unittest
from django.conf import settings
from django.core.files.base import ContentFile, File
from django.test import TestCase

from photologue.models import *

# Path to sample image
RES_DIR = os.path.join(os.path.dirname(__file__), 'res')
LANDSCAPE_IMAGE_PATH = os.path.join(RES_DIR, 'test_landscape.jpg')
PORTRAIT_IMAGE_PATH = os.path.join(RES_DIR, 'test_portrait.jpg')
SQUARE_IMAGE_PATH = os.path.join(RES_DIR, 'test_square.jpg')
UNICODE_IMAGE_PATH = os.path.join(RES_DIR, 'test_unicode_®.jpg')
NONSENSE_IMAGE_PATH = os.path.join(RES_DIR, 'test_nonsense.jpg')


class TestPhoto(ImageModel):
    """ Minimal ImageModel class for testing """
    name = models.CharField(max_length=30)


class PLTest(TestCase):
    """ Base TestCase class """
    def setUp(self):
        self.s = PhotoSize(name='test', width=100, height=100)
        self.s.save()
        self.pl = TestPhoto(name='landscape')
        self.pl.image.save(os.path.basename(LANDSCAPE_IMAGE_PATH),
                           ContentFile(open(LANDSCAPE_IMAGE_PATH, 'rb').read()))
        self.pl.save()

    def tearDown(self):
        path = self.pl.image.path
        self.pl.delete()
        self.failIf(os.path.isfile(path))
        self.s.delete()


class PhotoTest(PLTest):
    def test_new_photo(self):
        self.assertEqual(TestPhoto.objects.count(), 1)
        self.failUnless(os.path.isfile(self.pl.image.path))
        self.assertEqual(os.path.getsize(self.pl.image.path),
                         os.path.getsize(LANDSCAPE_IMAGE_PATH))

    #def test_exif(self):
    #    self.assert_(len(self.pl.EXIF.keys()) > 0)

    def test_paths(self):
        self.assertEqual(os.path.normpath(str(self.pl.cache_path())).lower(),
                         os.path.normpath(os.path.join(settings.MEDIA_ROOT,
                                      PHOTOLOGUE_DIR,
                                      'photos',
                                      'cache')).lower())
        self.assertEqual(self.pl.cache_url(),
                         settings.MEDIA_URL + PHOTOLOGUE_DIR + '/photos/cache')

    def test_count(self):
        for i in range(5):
            self.pl.get_test_url()
        self.assertEquals(self.pl.view_count, 0)
        self.s.increment_count = True
        self.s.save()
        for i in range(5):
            self.pl.get_test_url()
        self.assertEquals(self.pl.view_count, 5)

    def test_precache(self):
        # set the thumbnail photo size to pre-cache
        self.s.pre_cache = True
        self.s.save()
        # make sure it created the file
        self.failUnless(os.path.isfile(self.pl.get_test_filename()))
        self.s.pre_cache = False
        self.s.save()
        # clear the cache and make sure the file's deleted
        self.pl.clear_cache()
        self.failIf(os.path.isfile(self.pl.get_test_filename()))

    def test_accessor_methods(self):
        self.assertEquals(self.pl.get_test_photosize(), self.s)
        self.assertEquals(self.pl.get_test_size(),
                          Image.open(self.pl.get_test_filename()).size)
        self.assertEquals(self.pl.get_test_url(),
                          self.pl.cache_url() + '/' + \
                          self.pl._get_filename_for_size(self.s))
        self.assertEquals(self.pl.get_test_filename(),
                          os.path.join(self.pl.cache_path(),
                          self.pl._get_filename_for_size(self.s)))


class ImageResizeTest(PLTest):
    def setUp(self):
        super(ImageResizeTest, self).setUp()
        self.pp = TestPhoto(name='portrait')
        self.pp.image.save(os.path.basename(PORTRAIT_IMAGE_PATH),
                           ContentFile(open(PORTRAIT_IMAGE_PATH, 'rb').read()))
        self.pp.save()
        self.ps = TestPhoto(name='square')
        self.ps.image.save(os.path.basename(SQUARE_IMAGE_PATH),
                           ContentFile(open(SQUARE_IMAGE_PATH, 'rb').read()))
        self.ps.save()

    def tearDown(self):
        super(ImageResizeTest, self).tearDown()
        self.pp.delete()
        self.ps.delete()

    def test_resize_to_fit(self):
        self.assertEquals(self.pl.get_test_size(), (100, 75))
        self.assertEquals(self.pp.get_test_size(), (75, 100))
        self.assertEquals(self.ps.get_test_size(), (100, 100))

    def test_resize_to_fit_width(self):
        self.s.size = (100, 0)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (100, 75))
        self.assertEquals(self.pp.get_test_size(), (100, 133))
        self.assertEquals(self.ps.get_test_size(), (100, 100))

    def test_resize_to_fit_width_enlarge(self):
        self.s.size = (400, 0)
        self.s.upscale = True
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (400, 300))
        self.assertEquals(self.pp.get_test_size(), (400, 533))
        self.assertEquals(self.ps.get_test_size(), (400, 400))

    def test_resize_to_fit_height(self):
        self.s.size = (0, 100)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (133, 100))
        self.assertEquals(self.pp.get_test_size(), (75, 100))
        self.assertEquals(self.ps.get_test_size(), (100, 100))

    def test_resize_to_fit_height_enlarge(self):
        self.s.size = (0, 400)
        self.s.upscale = True
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (533, 400))
        self.assertEquals(self.pp.get_test_size(), (300, 400))
        self.assertEquals(self.ps.get_test_size(), (400, 400))

    def test_resize_and_crop(self):
        self.s.crop = True
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), self.s.size)
        self.assertEquals(self.pp.get_test_size(), self.s.size)
        self.assertEquals(self.ps.get_test_size(), self.s.size)

    def test_resize_rounding_to_fit(self):
        self.s.size = (113, 113)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (113, 85))
        self.assertEquals(self.pp.get_test_size(), (85, 113))
        self.assertEquals(self.ps.get_test_size(), (113, 113))

    def test_resize_rounding_cropped(self):
        self.s.size = (113, 113)
        self.s.crop = True
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), self.s.size)
        self.assertEquals(self.pp.get_test_size(), self.s.size)
        self.assertEquals(self.ps.get_test_size(), self.s.size)

    def test_resize_one_dimension_width(self):
        self.s.size = (100, 150)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (100, 75))

    def test_resize_one_dimension_height(self):
        self.s.size = (200, 75)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (100, 75))

    def test_resize_no_upscale(self):
        self.s.size = (1000, 1000)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (200, 150))

    def test_resize_no_upscale_mixed_height(self):
        self.s.size = (400, 75)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (100, 75))

    def test_resize_no_upscale_mixed_width(self):
        self.s.size = (100, 300)
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (100, 75))

    def test_resize_no_upscale_crop(self):
        self.s.size = (1000, 1000)
        self.s.crop = True
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (1000, 1000))

    def test_resize_upscale(self):
        self.s.size = (1000, 1000)
        self.s.upscale = True
        self.s.save()
        self.assertEquals(self.pl.get_test_size(), (1000, 750))
        self.assertEquals(self.pp.get_test_size(), (750, 1000))
        self.assertEquals(self.ps.get_test_size(), (1000, 1000))


class PhotoEffectTest(PLTest):
    def test(self):
        effect = PhotoEffect(name='test')
        im = Image.open(self.pl.image.path)
        self.assert_(isinstance(effect.pre_process(im), Image.Image))
        self.assert_(isinstance(effect.post_process(im), Image.Image))
        self.assert_(isinstance(effect.process(im), Image.Image))


class PhotoSizeCacheTest(PLTest):
    def test(self):
        cache = PhotoSizeCache()
        self.assertEqual(cache.sizes['test'], self.s)


class ImageModelTest(PLTest):

    def setUp(self):
        super(ImageModelTest, self).setUp()

        # Unicode image has unicode in the path
        self.pu = TestPhoto(name='portrait')
        self.pu.image.save(os.path.basename(UNICODE_IMAGE_PATH),
                           ContentFile(open(UNICODE_IMAGE_PATH, 'rb').read()))

        # Nonsense image contains nonsense
        self.pn = TestPhoto(name='portrait')
        self.pn.image.save(os.path.basename(NONSENSE_IMAGE_PATH),
                           ContentFile(open(NONSENSE_IMAGE_PATH, 'rb').read()))

    def tearDown(self):
        super(ImageModelTest, self).tearDown()
        self.pu.delete()
        self.pn.delete()

    def test_create_size(self):
        """Nonsense image must not break scaling"""
        self.pn.create_size(self.s)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from models import *

# Number of random images from the gallery to display.
SAMPLE_SIZE = ":%s" % getattr(settings, 'GALLERY_SAMPLE_SIZE', 5)

# galleries
gallery_args = {'date_field': 'date_added', 'allow_empty': True, 'queryset': Gallery.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}
urlpatterns = patterns('django.views.generic.date_based',
    url(r'^gallery/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'date_field': 'date_added', 'slug_field': 'title_slug', 'queryset': Gallery.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}, name='pl-gallery-detail'),
    url(r'^gallery/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 'archive_day', gallery_args, name='pl-gallery-archive-day'),
    url(r'^gallery/(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'archive_month', gallery_args, name='pl-gallery-archive-month'),
    url(r'^gallery/(?P<year>\d{4})/$', 'archive_year', gallery_args, name='pl-gallery-archive-year'),
    url(r'^gallery/?$', 'archive_index', gallery_args, name='pl-gallery-archive'),
)
urlpatterns += patterns('django.views.generic.list_detail',
    url(r'^gallery/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'slug_field': 'title_slug', 'queryset': Gallery.objects.filter(is_public=True), 'extra_context':{'sample_size':SAMPLE_SIZE}}, name='pl-gallery'),
    url(r'^gallery/page/(?P<page>[0-9]+)/$', 'object_list', {'queryset': Gallery.objects.filter(is_public=True), 'allow_empty': True, 'paginate_by': 5, 'extra_context':{'sample_size':SAMPLE_SIZE}}, name='pl-gallery-list'),
)

# photographs
photo_args = {'date_field': 'date_added', 'allow_empty': True, 'queryset': Photo.objects.filter(is_public=True)}
urlpatterns += patterns('django.views.generic.date_based',
    url(r'^photo/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'date_field': 'date_added', 'slug_field': 'title_slug', 'queryset': Photo.objects.filter(is_public=True)}, name='pl-photo-detail'),
    url(r'^photo/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 'archive_day', photo_args, name='pl-photo-archive-day'),
    url(r'^photo/(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'archive_month', photo_args, name='pl-photo-archive-month'),
    url(r'^photo/(?P<year>\d{4})/$', 'archive_year', photo_args, name='pl-photo-archive-year'),
    url(r'^photo/$', 'archive_index', photo_args, name='pl-photo-archive'),
)
urlpatterns += patterns('django.views.generic.list_detail',
    url(r'^photo/(?P<slug>[\-\d\w]+)/$', 'object_detail', {'slug_field': 'title_slug', 'queryset': Photo.objects.filter(is_public=True)}, name='pl-photo'),
    url(r'^photo/page/(?P<page>[0-9]+)/$', 'object_list', {'queryset': Photo.objects.filter(is_public=True), 'allow_empty': True, 'paginate_by': 20}, name='pl-photo-list'),
)



########NEW FILE########
__FILENAME__ = EXIF
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Library to extract EXIF information from digital camera image files
# http://sourceforge.net/projects/exif-py/
#
# VERSION 1.1.0
#
# To use this library call with:
#    f = open(path_name, 'rb')
#    tags = EXIF.process_file(f)
#
# To ignore MakerNote tags, pass the -q or --quick
# command line arguments, or as
#    tags = EXIF.process_file(f, details=False)
#
# To stop processing after a certain tag is retrieved,
# pass the -t TAG or --stop-tag TAG argument, or as
#    tags = EXIF.process_file(f, stop_tag='TAG')
#
# where TAG is a valid tag name, ex 'DateTimeOriginal'
#
# These 2 are useful when you are retrieving a large list of images
#
#
# To return an error on invalid tags,
# pass the -s or --strict argument, or as
#    tags = EXIF.process_file(f, strict=True)
#
# Otherwise these tags will be ignored
#
# Returned tags will be a dictionary mapping names of EXIF tags to their
# values in the file named by path_name.  You can process the tags
# as you wish.  In particular, you can iterate through all the tags with:
#     for tag in tags.keys():
#         if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename',
#                        'EXIF MakerNote'):
#             print "Key: %s, value %s" % (tag, tags[tag])
# (This code uses the if statement to avoid printing out a few of the
# tags that tend to be long or boring.)
#
# The tags dictionary will include keys for all of the usual EXIF
# tags, and will also include keys for Makernotes used by some
# cameras, for which we have a good specification.
#
# Note that the dictionary keys are the IFD name followed by the
# tag name. For example:
# 'EXIF DateTimeOriginal', 'Image Orientation', 'MakerNote FocusMode'
#
# Copyright (c) 2002-2007 Gene Cash All rights reserved
# Copyright (c) 2007-2008 Ianaré Sévi All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#
#  3. Neither the name of the authors nor the names of its contributors
#     may be used to endorse or promote products derived from this
#     software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
# ----- See 'changes.txt' file for all contributors and changes ----- #
#


# Don't throw an exception when given an out of range character.
def make_string(seq):
    str = ''
    for c in seq:
        # Screen out non-printing characters
        if 32 <= c and c < 256:
            str += chr(c)
    # If no printing chars
    if not str:
        return seq
    return str

# Special version to deal with the code in the first 8 bytes of a user comment.
# First 8 bytes gives coding system e.g. ASCII vs. JIS vs Unicode
def make_string_uc(seq):
    code = seq[0:8]
    seq = seq[8:]
    # Of course, this is only correct if ASCII, and the standard explicitly
    # allows JIS and Unicode.
    return make_string(seq)

# field type descriptions as (length, abbreviation, full name) tuples
FIELD_TYPES = (
    (0, 'X', 'Proprietary'), # no such type
    (1, 'B', 'Byte'),
    (1, 'A', 'ASCII'),
    (2, 'S', 'Short'),
    (4, 'L', 'Long'),
    (8, 'R', 'Ratio'),
    (1, 'SB', 'Signed Byte'),
    (1, 'U', 'Undefined'),
    (2, 'SS', 'Signed Short'),
    (4, 'SL', 'Signed Long'),
    (8, 'SR', 'Signed Ratio'),
    )

# dictionary of main EXIF tag names
# first element of tuple is tag name, optional second element is
# another dictionary giving names to values
EXIF_TAGS = {
    0x0100: ('ImageWidth', ),
    0x0101: ('ImageLength', ),
    0x0102: ('BitsPerSample', ),
    0x0103: ('Compression',
             {1: 'Uncompressed',
              2: 'CCITT 1D',
              3: 'T4/Group 3 Fax',
              4: 'T6/Group 4 Fax',
              5: 'LZW',
              6: 'JPEG (old-style)',
              7: 'JPEG',
              8: 'Adobe Deflate',
              9: 'JBIG B&W',
              10: 'JBIG Color',
              32766: 'Next',
              32769: 'Epson ERF Compressed',
              32771: 'CCIRLEW',
              32773: 'PackBits',
              32809: 'Thunderscan',
              32895: 'IT8CTPAD',
              32896: 'IT8LW',
              32897: 'IT8MP',
              32898: 'IT8BL',
              32908: 'PixarFilm',
              32909: 'PixarLog',
              32946: 'Deflate',
              32947: 'DCS',
              34661: 'JBIG',
              34676: 'SGILog',
              34677: 'SGILog24',
              34712: 'JPEG 2000',
              34713: 'Nikon NEF Compressed',
              65000: 'Kodak DCR Compressed',
              65535: 'Pentax PEF Compressed'}),
    0x0106: ('PhotometricInterpretation', ),
    0x0107: ('Thresholding', ),
    0x010A: ('FillOrder', ),
    0x010D: ('DocumentName', ),
    0x010E: ('ImageDescription', ),
    0x010F: ('Make', ),
    0x0110: ('Model', ),
    0x0111: ('StripOffsets', ),
    0x0112: ('Orientation',
             {1: 'Horizontal (normal)',
              2: 'Mirrored horizontal',
              3: 'Rotated 180',
              4: 'Mirrored vertical',
              5: 'Mirrored horizontal then rotated 90 CCW',
              6: 'Rotated 90 CW',
              7: 'Mirrored horizontal then rotated 90 CW',
              8: 'Rotated 90 CCW'}),
    0x0115: ('SamplesPerPixel', ),
    0x0116: ('RowsPerStrip', ),
    0x0117: ('StripByteCounts', ),
    0x011A: ('XResolution', ),
    0x011B: ('YResolution', ),
    0x011C: ('PlanarConfiguration', ),
    0x011D: ('PageName', make_string),
    0x0128: ('ResolutionUnit',
             {1: 'Not Absolute',
              2: 'Pixels/Inch',
              3: 'Pixels/Centimeter'}),
    0x012D: ('TransferFunction', ),
    0x0131: ('Software', ),
    0x0132: ('DateTime', ),
    0x013B: ('Artist', ),
    0x013E: ('WhitePoint', ),
    0x013F: ('PrimaryChromaticities', ),
    0x0156: ('TransferRange', ),
    0x0200: ('JPEGProc', ),
    0x0201: ('JPEGInterchangeFormat', ),
    0x0202: ('JPEGInterchangeFormatLength', ),
    0x0211: ('YCbCrCoefficients', ),
    0x0212: ('YCbCrSubSampling', ),
    0x0213: ('YCbCrPositioning',
             {1: 'Centered',
              2: 'Co-sited'}),
    0x0214: ('ReferenceBlackWhite', ),
    
    0x4746: ('Rating', ),
    
    0x828D: ('CFARepeatPatternDim', ),
    0x828E: ('CFAPattern', ),
    0x828F: ('BatteryLevel', ),
    0x8298: ('Copyright', ),
    0x829A: ('ExposureTime', ),
    0x829D: ('FNumber', ),
    0x83BB: ('IPTC/NAA', ),
    0x8769: ('ExifOffset', ),
    0x8773: ('InterColorProfile', ),
    0x8822: ('ExposureProgram',
             {0: 'Unidentified',
              1: 'Manual',
              2: 'Program Normal',
              3: 'Aperture Priority',
              4: 'Shutter Priority',
              5: 'Program Creative',
              6: 'Program Action',
              7: 'Portrait Mode',
              8: 'Landscape Mode'}),
    0x8824: ('SpectralSensitivity', ),
    0x8825: ('GPSInfo', ),
    0x8827: ('ISOSpeedRatings', ),
    0x8828: ('OECF', ),
    0x9000: ('ExifVersion', make_string),
    0x9003: ('DateTimeOriginal', ),
    0x9004: ('DateTimeDigitized', ),
    0x9101: ('ComponentsConfiguration',
             {0: '',
              1: 'Y',
              2: 'Cb',
              3: 'Cr',
              4: 'Red',
              5: 'Green',
              6: 'Blue'}),
    0x9102: ('CompressedBitsPerPixel', ),
    0x9201: ('ShutterSpeedValue', ),
    0x9202: ('ApertureValue', ),
    0x9203: ('BrightnessValue', ),
    0x9204: ('ExposureBiasValue', ),
    0x9205: ('MaxApertureValue', ),
    0x9206: ('SubjectDistance', ),
    0x9207: ('MeteringMode',
             {0: 'Unidentified',
              1: 'Average',
              2: 'CenterWeightedAverage',
              3: 'Spot',
              4: 'MultiSpot',
              5: 'Pattern'}),
    0x9208: ('LightSource',
             {0: 'Unknown',
              1: 'Daylight',
              2: 'Fluorescent',
              3: 'Tungsten',
              9: 'Fine Weather',
              10: 'Flash',
              11: 'Shade',
              12: 'Daylight Fluorescent',
              13: 'Day White Fluorescent',
              14: 'Cool White Fluorescent',
              15: 'White Fluorescent',
              17: 'Standard Light A',
              18: 'Standard Light B',
              19: 'Standard Light C',
              20: 'D55',
              21: 'D65',
              22: 'D75',
              255: 'Other'}),
    0x9209: ('Flash',
             {0: 'No',
              1: 'Fired',
              5: 'Fired (?)', # no return sensed
              7: 'Fired (!)', # return sensed
              9: 'Fill Fired',
              13: 'Fill Fired (?)',
              15: 'Fill Fired (!)',
              16: 'Off',
              24: 'Auto Off',
              25: 'Auto Fired',
              29: 'Auto Fired (?)',
              31: 'Auto Fired (!)',
              32: 'Not Available'}),
    0x920A: ('FocalLength', ),
    0x9214: ('SubjectArea', ),
    0x927C: ('MakerNote', ),
    0x9286: ('UserComment', make_string_uc),
    0x9290: ('SubSecTime', ),
    0x9291: ('SubSecTimeOriginal', ),
    0x9292: ('SubSecTimeDigitized', ),
    
    # used by Windows Explorer
    0x9C9B: ('XPTitle', ),
    0x9C9C: ('XPComment', ),
    0x9C9D: ('XPAuthor', ), #(ignored by Windows Explorer if Artist exists)
    0x9C9E: ('XPKeywords', ),
    0x9C9F: ('XPSubject', ),

    0xA000: ('FlashPixVersion', make_string),
    0xA001: ('ColorSpace',
             {1: 'sRGB',
              2: 'Adobe RGB',
              65535: 'Uncalibrated'}),
    0xA002: ('ExifImageWidth', ),
    0xA003: ('ExifImageLength', ),
    0xA005: ('InteroperabilityOffset', ),
    0xA20B: ('FlashEnergy', ),               # 0x920B in TIFF/EP
    0xA20C: ('SpatialFrequencyResponse', ),  # 0x920C
    0xA20E: ('FocalPlaneXResolution', ),     # 0x920E
    0xA20F: ('FocalPlaneYResolution', ),     # 0x920F
    0xA210: ('FocalPlaneResolutionUnit', ),  # 0x9210
    0xA214: ('SubjectLocation', ),           # 0x9214
    0xA215: ('ExposureIndex', ),             # 0x9215
    0xA217: ('SensingMethod',                # 0x9217
             {1: 'Not defined',
              2: 'One-chip color area',
              3: 'Two-chip color area',
              4: 'Three-chip color area',
              5: 'Color sequential area',
              7: 'Trilinear',
              8: 'Color sequential linear'}),             
    0xA300: ('FileSource',
             {1: 'Film Scanner',
              2: 'Reflection Print Scanner',
              3: 'Digital Camera'}),
    0xA301: ('SceneType',
             {1: 'Directly Photographed'}),
    0xA302: ('CVAPattern', ),
    0xA401: ('CustomRendered',
             {0: 'Normal',
              1: 'Custom'}),
    0xA402: ('ExposureMode',
             {0: 'Auto Exposure',
              1: 'Manual Exposure',
              2: 'Auto Bracket'}),
    0xA403: ('WhiteBalance',
             {0: 'Auto',
              1: 'Manual'}),
    0xA404: ('DigitalZoomRatio', ),
    0xA405: ('FocalLengthIn35mmFilm', ),
    0xA406: ('SceneCaptureType',
             {0: 'Standard',
              1: 'Landscape',
              2: 'Portrait',
              3: 'Night)'}),
    0xA407: ('GainControl',
             {0: 'None',
              1: 'Low gain up',
              2: 'High gain up',
              3: 'Low gain down',
              4: 'High gain down'}),
    0xA408: ('Contrast',
             {0: 'Normal',
              1: 'Soft',
              2: 'Hard'}),
    0xA409: ('Saturation',
             {0: 'Normal',
              1: 'Soft',
              2: 'Hard'}),
    0xA40A: ('Sharpness',
             {0: 'Normal',
              1: 'Soft',
              2: 'Hard'}),
    0xA40B: ('DeviceSettingDescription', ),
    0xA40C: ('SubjectDistanceRange', ),
    0xA500: ('Gamma', ),
    0xC4A5: ('PrintIM', ),
    0xEA1C:	('Padding', ),
    }

# interoperability tags
INTR_TAGS = {
    0x0001: ('InteroperabilityIndex', ),
    0x0002: ('InteroperabilityVersion', ),
    0x1000: ('RelatedImageFileFormat', ),
    0x1001: ('RelatedImageWidth', ),
    0x1002: ('RelatedImageLength', ),
    }

# GPS tags (not used yet, haven't seen camera with GPS)
GPS_TAGS = {
    0x0000: ('GPSVersionID', ),
    0x0001: ('GPSLatitudeRef', ),
    0x0002: ('GPSLatitude', ),
    0x0003: ('GPSLongitudeRef', ),
    0x0004: ('GPSLongitude', ),
    0x0005: ('GPSAltitudeRef', ),
    0x0006: ('GPSAltitude', ),
    0x0007: ('GPSTimeStamp', ),
    0x0008: ('GPSSatellites', ),
    0x0009: ('GPSStatus', ),
    0x000A: ('GPSMeasureMode', ),
    0x000B: ('GPSDOP', ),
    0x000C: ('GPSSpeedRef', ),
    0x000D: ('GPSSpeed', ),
    0x000E: ('GPSTrackRef', ),
    0x000F: ('GPSTrack', ),
    0x0010: ('GPSImgDirectionRef', ),
    0x0011: ('GPSImgDirection', ),
    0x0012: ('GPSMapDatum', ),
    0x0013: ('GPSDestLatitudeRef', ),
    0x0014: ('GPSDestLatitude', ),
    0x0015: ('GPSDestLongitudeRef', ),
    0x0016: ('GPSDestLongitude', ),
    0x0017: ('GPSDestBearingRef', ),
    0x0018: ('GPSDestBearing', ),
    0x0019: ('GPSDestDistanceRef', ),
    0x001A: ('GPSDestDistance', ),
    0x001D: ('GPSDate', ),
    }

# Ignore these tags when quick processing
# 0x927C is MakerNote Tags
# 0x9286 is user comment
IGNORE_TAGS=(0x9286, 0x927C)

# http://tomtia.plala.jp/DigitalCamera/MakerNote/index.asp
def nikon_ev_bias(seq):
    # First digit seems to be in steps of 1/6 EV.
    # Does the third value mean the step size?  It is usually 6,
    # but it is 12 for the ExposureDifference.
    #
    # Check for an error condition that could cause a crash.
    # This only happens if something has gone really wrong in
    # reading the Nikon MakerNote.
    if len( seq ) < 4 : return ""
    #
    if seq == [252, 1, 6, 0]:
        return "-2/3 EV"
    if seq == [253, 1, 6, 0]:
        return "-1/2 EV"
    if seq == [254, 1, 6, 0]:
        return "-1/3 EV"
    if seq == [0, 1, 6, 0]:
        return "0 EV"
    if seq == [2, 1, 6, 0]:
        return "+1/3 EV"
    if seq == [3, 1, 6, 0]:
        return "+1/2 EV"
    if seq == [4, 1, 6, 0]:
        return "+2/3 EV"
    # Handle combinations not in the table.
    a = seq[0]
    # Causes headaches for the +/- logic, so special case it.
    if a == 0:
        return "0 EV"
    if a > 127:
        a = 256 - a
        ret_str = "-"
    else:
        ret_str = "+"
    b = seq[2]	# Assume third value means the step size
    whole = a / b
    a = a % b
    if whole != 0:
        ret_str = ret_str + str(whole) + " "
    if a == 0:
        ret_str = ret_str + "EV"
    else:
        r = Ratio(a, b)
        ret_str = ret_str + r.__repr__() + " EV"
    return ret_str

# Nikon E99x MakerNote Tags
MAKERNOTE_NIKON_NEWER_TAGS={
    0x0001: ('MakernoteVersion', make_string),	# Sometimes binary
    0x0002: ('ISOSetting', make_string),
    0x0003: ('ColorMode', ),
    0x0004: ('Quality', ),
    0x0005: ('Whitebalance', ),
    0x0006: ('ImageSharpening', ),
    0x0007: ('FocusMode', ),
    0x0008: ('FlashSetting', ),
    0x0009: ('AutoFlashMode', ),
    0x000B: ('WhiteBalanceBias', ),
    0x000C: ('WhiteBalanceRBCoeff', ),
    0x000D: ('ProgramShift', nikon_ev_bias),
    # Nearly the same as the other EV vals, but step size is 1/12 EV (?)
    0x000E: ('ExposureDifference', nikon_ev_bias),
    0x000F: ('ISOSelection', ),
    0x0011: ('NikonPreview', ),
    0x0012: ('FlashCompensation', nikon_ev_bias),
    0x0013: ('ISOSpeedRequested', ),
    0x0016: ('PhotoCornerCoordinates', ),
    # 0x0017: Unknown, but most likely an EV value
    0x0018: ('FlashBracketCompensationApplied', nikon_ev_bias),
    0x0019: ('AEBracketCompensationApplied', ),
    0x001A: ('ImageProcessing', ),
    0x001B: ('CropHiSpeed', ),
    0x001D: ('SerialNumber', ),	# Conflict with 0x00A0 ?
    0x001E: ('ColorSpace', ),
    0x001F: ('VRInfo', ),
    0x0020: ('ImageAuthentication', ),
    0x0022: ('ActiveDLighting', ),
    0x0023: ('PictureControl', ),
    0x0024: ('WorldTime', ),
    0x0025: ('ISOInfo', ),
    0x0080: ('ImageAdjustment', ),
    0x0081: ('ToneCompensation', ),
    0x0082: ('AuxiliaryLens', ),
    0x0083: ('LensType', ),
    0x0084: ('LensMinMaxFocalMaxAperture', ),
    0x0085: ('ManualFocusDistance', ),
    0x0086: ('DigitalZoomFactor', ),
    0x0087: ('FlashMode',
             {0x00: 'Did Not Fire',
              0x01: 'Fired, Manual',
              0x07: 'Fired, External',
              0x08: 'Fired, Commander Mode ',
              0x09: 'Fired, TTL Mode'}),
    0x0088: ('AFFocusPosition',
             {0x0000: 'Center',
              0x0100: 'Top',
              0x0200: 'Bottom',
              0x0300: 'Left',
              0x0400: 'Right'}),
    0x0089: ('BracketingMode',
             {0x00: 'Single frame, no bracketing',
              0x01: 'Continuous, no bracketing',
              0x02: 'Timer, no bracketing',
              0x10: 'Single frame, exposure bracketing',
              0x11: 'Continuous, exposure bracketing',
              0x12: 'Timer, exposure bracketing',
              0x40: 'Single frame, white balance bracketing',
              0x41: 'Continuous, white balance bracketing',
              0x42: 'Timer, white balance bracketing'}),
    0x008A: ('AutoBracketRelease', ),
    0x008B: ('LensFStops', ),
    0x008C: ('NEFCurve1', ),	# ExifTool calls this 'ContrastCurve'
    0x008D: ('ColorMode', ),
    0x008F: ('SceneMode', ),
    0x0090: ('LightingType', ),
    0x0091: ('ShotInfo', ),	# First 4 bytes are a version number in ASCII
    0x0092: ('HueAdjustment', ),
    # ExifTool calls this 'NEFCompression', should be 1-4
    0x0093: ('Compression', ),
    0x0094: ('Saturation',
             {-3: 'B&W',
              -2: '-2',
              -1: '-1',
              0: '0',
              1: '1',
              2: '2'}),
    0x0095: ('NoiseReduction', ),
    0x0096: ('NEFCurve2', ),	# ExifTool calls this 'LinearizationTable'
    0x0097: ('ColorBalance', ),	# First 4 bytes are a version number in ASCII
    0x0098: ('LensData', ),	# First 4 bytes are a version number in ASCII
    0x0099: ('RawImageCenter', ),
    0x009A: ('SensorPixelSize', ),
    0x009C: ('Scene Assist', ),
    0x009E: ('RetouchHistory', ),
    0x00A0: ('SerialNumber', ),
    0x00A2: ('ImageDataSize', ),
    # 00A3: unknown - a single byte 0
    # 00A4: In NEF, looks like a 4 byte ASCII version number ('0200')
    0x00A5: ('ImageCount', ),
    0x00A6: ('DeletedImageCount', ),
    0x00A7: ('TotalShutterReleases', ),
    # First 4 bytes are a version number in ASCII, with version specific
    # info to follow.  Its hard to treat it as a string due to embedded nulls.
    0x00A8: ('FlashInfo', ),
    0x00A9: ('ImageOptimization', ),
    0x00AA: ('Saturation', ),
    0x00AB: ('DigitalVariProgram', ),
    0x00AC: ('ImageStabilization', ),
    0x00AD: ('Responsive AF', ),	# 'AFResponse'
    0x00B0: ('MultiExposure', ),
    0x00B1: ('HighISONoiseReduction', ),
    0x00B7: ('AFInfo', ),
    0x00B8: ('FileInfo', ),
    # 00B9: unknown
    0x0100: ('DigitalICE', ),
    0x0103: ('PreviewCompression',
             {1: 'Uncompressed',
              2: 'CCITT 1D',
              3: 'T4/Group 3 Fax',
              4: 'T6/Group 4 Fax',
              5: 'LZW',
              6: 'JPEG (old-style)',
              7: 'JPEG',
              8: 'Adobe Deflate',
              9: 'JBIG B&W',
              10: 'JBIG Color',
              32766: 'Next',
              32769: 'Epson ERF Compressed',
              32771: 'CCIRLEW',
              32773: 'PackBits',
              32809: 'Thunderscan',
              32895: 'IT8CTPAD',
              32896: 'IT8LW',
              32897: 'IT8MP',
              32898: 'IT8BL',
              32908: 'PixarFilm',
              32909: 'PixarLog',
              32946: 'Deflate',
              32947: 'DCS',
              34661: 'JBIG',
              34676: 'SGILog',
              34677: 'SGILog24',
              34712: 'JPEG 2000',
              34713: 'Nikon NEF Compressed',
              65000: 'Kodak DCR Compressed',
              65535: 'Pentax PEF Compressed',}),
    0x0201: ('PreviewImageStart', ),
    0x0202: ('PreviewImageLength', ),
    0x0213: ('PreviewYCbCrPositioning',
             {1: 'Centered',
              2: 'Co-sited'}), 
    0x0010: ('DataDump', ),
    }

MAKERNOTE_NIKON_OLDER_TAGS = {
    0x0003: ('Quality',
             {1: 'VGA Basic',
              2: 'VGA Normal',
              3: 'VGA Fine',
              4: 'SXGA Basic',
              5: 'SXGA Normal',
              6: 'SXGA Fine'}),
    0x0004: ('ColorMode',
             {1: 'Color',
              2: 'Monochrome'}),
    0x0005: ('ImageAdjustment',
             {0: 'Normal',
              1: 'Bright+',
              2: 'Bright-',
              3: 'Contrast+',
              4: 'Contrast-'}),
    0x0006: ('CCDSpeed',
             {0: 'ISO 80',
              2: 'ISO 160',
              4: 'ISO 320',
              5: 'ISO 100'}),
    0x0007: ('WhiteBalance',
             {0: 'Auto',
              1: 'Preset',
              2: 'Daylight',
              3: 'Incandescent',
              4: 'Fluorescent',
              5: 'Cloudy',
              6: 'Speed Light'}),
    }

# decode Olympus SpecialMode tag in MakerNote
def olympus_special_mode(v):
    a={
        0: 'Normal',
        1: 'Unknown',
        2: 'Fast',
        3: 'Panorama'}
    b={
        0: 'Non-panoramic',
        1: 'Left to right',
        2: 'Right to left',
        3: 'Bottom to top',
        4: 'Top to bottom'}
    if v[0] not in a or v[2] not in b:
        return v
    return '%s - sequence %d - %s' % (a[v[0]], v[1], b[v[2]])

MAKERNOTE_OLYMPUS_TAGS={
    # ah HAH! those sneeeeeaky bastids! this is how they get past the fact
    # that a JPEG thumbnail is not allowed in an uncompressed TIFF file
    0x0100: ('JPEGThumbnail', ),
    0x0200: ('SpecialMode', olympus_special_mode),
    0x0201: ('JPEGQual',
             {1: 'SQ',
              2: 'HQ',
              3: 'SHQ'}),
    0x0202: ('Macro',
             {0: 'Normal',
             1: 'Macro',
             2: 'SuperMacro'}),
    0x0203: ('BWMode',
             {0: 'Off',
             1: 'On'}),
    0x0204: ('DigitalZoom', ),
    0x0205: ('FocalPlaneDiagonal', ),
    0x0206: ('LensDistortionParams', ),
    0x0207: ('SoftwareRelease', ),
    0x0208: ('PictureInfo', ),
    0x0209: ('CameraID', make_string), # print as string
    0x0F00: ('DataDump', ),
    0x0300: ('PreCaptureFrames', ),
    0x0404: ('SerialNumber', ),
    0x1000: ('ShutterSpeedValue', ),
    0x1001: ('ISOValue', ),
    0x1002: ('ApertureValue', ),
    0x1003: ('BrightnessValue', ),
    0x1004: ('FlashMode', ),
    0x1004: ('FlashMode',
       {2: 'On',
        3: 'Off'}),
    0x1005: ('FlashDevice',
       {0: 'None',
        1: 'Internal',
        4: 'External',
        5: 'Internal + External'}),
    0x1006: ('ExposureCompensation', ),
    0x1007: ('SensorTemperature', ),
    0x1008: ('LensTemperature', ),
    0x100b: ('FocusMode',
       {0: 'Auto',
        1: 'Manual'}),
    0x1017: ('RedBalance', ),
    0x1018: ('BlueBalance', ),
    0x101a: ('SerialNumber', ),
    0x1023: ('FlashExposureComp', ),
    0x1026: ('ExternalFlashBounce',
       {0: 'No',
        1: 'Yes'}),
    0x1027: ('ExternalFlashZoom', ),
    0x1028: ('ExternalFlashMode', ),
    0x1029: ('Contrast 	int16u',
       {0: 'High',
        1: 'Normal',
        2: 'Low'}),
    0x102a: ('SharpnessFactor', ),
    0x102b: ('ColorControl', ),
    0x102c: ('ValidBits', ),
    0x102d: ('CoringFilter', ),
    0x102e: ('OlympusImageWidth', ),
    0x102f: ('OlympusImageHeight', ),
    0x1034: ('CompressionRatio', ),
    0x1035: ('PreviewImageValid',
       {0: 'No',
        1: 'Yes'}),
    0x1036: ('PreviewImageStart', ),
    0x1037: ('PreviewImageLength', ),
    0x1039: ('CCDScanMode',
       {0: 'Interlaced',
        1: 'Progressive'}),
    0x103a: ('NoiseReduction',
       {0: 'Off',
        1: 'On'}),
    0x103b: ('InfinityLensStep', ),
    0x103c: ('NearLensStep', ),

    # TODO - these need extra definitions
    # http://search.cpan.org/src/EXIFTOOL/Image-ExifTool-6.90/html/TagNames/Olympus.html
    0x2010: ('Equipment', ),
    0x2020: ('CameraSettings', ),
    0x2030: ('RawDevelopment', ),
    0x2040: ('ImageProcessing', ),
    0x2050: ('FocusInfo', ),
    0x3000: ('RawInfo ', ),
    }

# 0x2020 CameraSettings
MAKERNOTE_OLYMPUS_TAG_0x2020={
    0x0100: ('PreviewImageValid',
             {0: 'No',
              1: 'Yes'}),
    0x0101: ('PreviewImageStart', ),
    0x0102: ('PreviewImageLength', ),
    0x0200: ('ExposureMode',
             {1: 'Manual',
              2: 'Program',
              3: 'Aperture-priority AE',
              4: 'Shutter speed priority AE',
              5: 'Program-shift'}),
    0x0201: ('AELock',
             {0: 'Off',
              1: 'On'}),
    0x0202: ('MeteringMode',
             {2: 'Center Weighted',
              3: 'Spot',
              5: 'ESP',
              261: 'Pattern+AF',
              515: 'Spot+Highlight control',
              1027: 'Spot+Shadow control'}),
    0x0300: ('MacroMode',
             {0: 'Off',
              1: 'On'}),
    0x0301: ('FocusMode',
             {0: 'Single AF',
              1: 'Sequential shooting AF',
              2: 'Continuous AF',
              3: 'Multi AF',
              10: 'MF'}),
    0x0302: ('FocusProcess',
             {0: 'AF Not Used',
              1: 'AF Used'}),
    0x0303: ('AFSearch',
             {0: 'Not Ready',
              1: 'Ready'}),
    0x0304: ('AFAreas', ),
    0x0401: ('FlashExposureCompensation', ),
    0x0500: ('WhiteBalance2',
             {0: 'Auto',
             16: '7500K (Fine Weather with Shade)',
             17: '6000K (Cloudy)',
             18: '5300K (Fine Weather)',
             20: '3000K (Tungsten light)',
             21: '3600K (Tungsten light-like)',
             33: '6600K (Daylight fluorescent)',
             34: '4500K (Neutral white fluorescent)',
             35: '4000K (Cool white fluorescent)',
             48: '3600K (Tungsten light-like)',
             256: 'Custom WB 1',
             257: 'Custom WB 2',
             258: 'Custom WB 3',
             259: 'Custom WB 4',
             512: 'Custom WB 5400K',
             513: 'Custom WB 2900K',
             514: 'Custom WB 8000K', }),
    0x0501: ('WhiteBalanceTemperature', ),
    0x0502: ('WhiteBalanceBracket', ),
    0x0503: ('CustomSaturation', ), # (3 numbers: 1. CS Value, 2. Min, 3. Max)
    0x0504: ('ModifiedSaturation',
             {0: 'Off',
              1: 'CM1 (Red Enhance)',
              2: 'CM2 (Green Enhance)',
              3: 'CM3 (Blue Enhance)',
              4: 'CM4 (Skin Tones)'}),
    0x0505: ('ContrastSetting', ), # (3 numbers: 1. Contrast, 2. Min, 3. Max)
    0x0506: ('SharpnessSetting', ), # (3 numbers: 1. Sharpness, 2. Min, 3. Max)
    0x0507: ('ColorSpace',
             {0: 'sRGB',
              1: 'Adobe RGB',
              2: 'Pro Photo RGB'}),
    0x0509: ('SceneMode',
             {0: 'Standard',
              6: 'Auto',
              7: 'Sport',
              8: 'Portrait',
              9: 'Landscape+Portrait',
             10: 'Landscape',
             11: 'Night scene',
             13: 'Panorama',
             16: 'Landscape+Portrait',
             17: 'Night+Portrait',
             19: 'Fireworks',
             20: 'Sunset',
             22: 'Macro',
             25: 'Documents',
             26: 'Museum',
             28: 'Beach&Snow',
             30: 'Candle',
             35: 'Underwater Wide1',
             36: 'Underwater Macro',
             39: 'High Key',
             40: 'Digital Image Stabilization',
             44: 'Underwater Wide2',
             45: 'Low Key',
             46: 'Children',
             48: 'Nature Macro'}),
    0x050a: ('NoiseReduction',
             {0: 'Off',
              1: 'Noise Reduction',
              2: 'Noise Filter',
              3: 'Noise Reduction + Noise Filter',
              4: 'Noise Filter (ISO Boost)',
              5: 'Noise Reduction + Noise Filter (ISO Boost)'}),
    0x050b: ('DistortionCorrection',
             {0: 'Off',
              1: 'On'}),
    0x050c: ('ShadingCompensation',
             {0: 'Off',
              1: 'On'}),
    0x050d: ('CompressionFactor', ),
    0x050f: ('Gradation',
             {'-1 -1 1': 'Low Key',
              '0 -1 1': 'Normal',
              '1 -1 1': 'High Key'}),
    0x0520: ('PictureMode',
             {1: 'Vivid',
              2: 'Natural',
              3: 'Muted',
              256: 'Monotone',
              512: 'Sepia'}),
    0x0521: ('PictureModeSaturation', ),
    0x0522: ('PictureModeHue?', ),
    0x0523: ('PictureModeContrast', ),
    0x0524: ('PictureModeSharpness', ),
    0x0525: ('PictureModeBWFilter',
             {0: 'n/a',
              1: 'Neutral',
              2: 'Yellow',
              3: 'Orange',
              4: 'Red',
              5: 'Green'}),
    0x0526: ('PictureModeTone',
             {0: 'n/a',
              1: 'Neutral',
              2: 'Sepia',
              3: 'Blue',
              4: 'Purple',
              5: 'Green'}),
    0x0600: ('Sequence', ), # 2 or 3 numbers: 1. Mode, 2. Shot number, 3. Mode bits
    0x0601: ('PanoramaMode', ), # (2 numbers: 1. Mode, 2. Shot number)
    0x0603: ('ImageQuality2',
             {1: 'SQ',
              2: 'HQ',
              3: 'SHQ',
              4: 'RAW'}),
    0x0901: ('ManometerReading', ),
    }


MAKERNOTE_CASIO_TAGS={
    0x0001: ('RecordingMode',
             {1: 'Single Shutter',
              2: 'Panorama',
              3: 'Night Scene',
              4: 'Portrait',
              5: 'Landscape'}),
    0x0002: ('Quality',
             {1: 'Economy',
              2: 'Normal',
              3: 'Fine'}),
    0x0003: ('FocusingMode',
             {2: 'Macro',
              3: 'Auto Focus',
              4: 'Manual Focus',
              5: 'Infinity'}),
    0x0004: ('FlashMode',
             {1: 'Auto',
              2: 'On',
              3: 'Off',
              4: 'Red Eye Reduction'}),
    0x0005: ('FlashIntensity',
             {11: 'Weak',
              13: 'Normal',
              15: 'Strong'}),
    0x0006: ('Object Distance', ),
    0x0007: ('WhiteBalance',
             {1: 'Auto',
              2: 'Tungsten',
              3: 'Daylight',
              4: 'Fluorescent',
              5: 'Shade',
              129: 'Manual'}),
    0x000B: ('Sharpness',
             {0: 'Normal',
              1: 'Soft',
              2: 'Hard'}),
    0x000C: ('Contrast',
             {0: 'Normal',
              1: 'Low',
              2: 'High'}),
    0x000D: ('Saturation',
             {0: 'Normal',
              1: 'Low',
              2: 'High'}),
    0x0014: ('CCDSpeed',
             {64: 'Normal',
              80: 'Normal',
              100: 'High',
              125: '+1.0',
              244: '+3.0',
              250: '+2.0'}),
    }

MAKERNOTE_FUJIFILM_TAGS={
    0x0000: ('NoteVersion', make_string),
    0x1000: ('Quality', ),
    0x1001: ('Sharpness',
             {1: 'Soft',
              2: 'Soft',
              3: 'Normal',
              4: 'Hard',
              5: 'Hard'}),
    0x1002: ('WhiteBalance',
             {0: 'Auto',
              256: 'Daylight',
              512: 'Cloudy',
              768: 'DaylightColor-Fluorescent',
              769: 'DaywhiteColor-Fluorescent',
              770: 'White-Fluorescent',
              1024: 'Incandescent',
              3840: 'Custom'}),
    0x1003: ('Color',
             {0: 'Normal',
              256: 'High',
              512: 'Low'}),
    0x1004: ('Tone',
             {0: 'Normal',
              256: 'High',
              512: 'Low'}),
    0x1010: ('FlashMode',
             {0: 'Auto',
              1: 'On',
              2: 'Off',
              3: 'Red Eye Reduction'}),
    0x1011: ('FlashStrength', ),
    0x1020: ('Macro',
             {0: 'Off',
              1: 'On'}),
    0x1021: ('FocusMode',
             {0: 'Auto',
              1: 'Manual'}),
    0x1030: ('SlowSync',
             {0: 'Off',
              1: 'On'}),
    0x1031: ('PictureMode',
             {0: 'Auto',
              1: 'Portrait',
              2: 'Landscape',
              4: 'Sports',
              5: 'Night',
              6: 'Program AE',
              256: 'Aperture Priority AE',
              512: 'Shutter Priority AE',
              768: 'Manual Exposure'}),
    0x1100: ('MotorOrBracket',
             {0: 'Off',
              1: 'On'}),
    0x1300: ('BlurWarning',
             {0: 'Off',
              1: 'On'}),
    0x1301: ('FocusWarning',
             {0: 'Off',
              1: 'On'}),
    0x1302: ('AEWarning',
             {0: 'Off',
              1: 'On'}),
    }

MAKERNOTE_CANON_TAGS = {
    0x0006: ('ImageType', ),
    0x0007: ('FirmwareVersion', ),
    0x0008: ('ImageNumber', ),
    0x0009: ('OwnerName', ),
    }

# this is in element offset, name, optional value dictionary format
MAKERNOTE_CANON_TAG_0x001 = {
    1: ('Macromode',
        {1: 'Macro',
         2: 'Normal'}),
    2: ('SelfTimer', ),
    3: ('Quality',
        {2: 'Normal',
         3: 'Fine',
         5: 'Superfine'}),
    4: ('FlashMode',
        {0: 'Flash Not Fired',
         1: 'Auto',
         2: 'On',
         3: 'Red-Eye Reduction',
         4: 'Slow Synchro',
         5: 'Auto + Red-Eye Reduction',
         6: 'On + Red-Eye Reduction',
         16: 'external flash'}),
    5: ('ContinuousDriveMode',
        {0: 'Single Or Timer',
         1: 'Continuous'}),
    7: ('FocusMode',
        {0: 'One-Shot',
         1: 'AI Servo',
         2: 'AI Focus',
         3: 'MF',
         4: 'Single',
         5: 'Continuous',
         6: 'MF'}),
    10: ('ImageSize',
         {0: 'Large',
          1: 'Medium',
          2: 'Small'}),
    11: ('EasyShootingMode',
         {0: 'Full Auto',
          1: 'Manual',
          2: 'Landscape',
          3: 'Fast Shutter',
          4: 'Slow Shutter',
          5: 'Night',
          6: 'B&W',
          7: 'Sepia',
          8: 'Portrait',
          9: 'Sports',
          10: 'Macro/Close-Up',
          11: 'Pan Focus'}),
    12: ('DigitalZoom',
         {0: 'None',
          1: '2x',
          2: '4x'}),
    13: ('Contrast',
         {0xFFFF: 'Low',
          0: 'Normal',
          1: 'High'}),
    14: ('Saturation',
         {0xFFFF: 'Low',
          0: 'Normal',
          1: 'High'}),
    15: ('Sharpness',
         {0xFFFF: 'Low',
          0: 'Normal',
          1: 'High'}),
    16: ('ISO',
         {0: 'See ISOSpeedRatings Tag',
          15: 'Auto',
          16: '50',
          17: '100',
          18: '200',
          19: '400'}),
    17: ('MeteringMode',
         {3: 'Evaluative',
          4: 'Partial',
          5: 'Center-weighted'}),
    18: ('FocusType',
         {0: 'Manual',
          1: 'Auto',
          3: 'Close-Up (Macro)',
          8: 'Locked (Pan Mode)'}),
    19: ('AFPointSelected',
         {0x3000: 'None (MF)',
          0x3001: 'Auto-Selected',
          0x3002: 'Right',
          0x3003: 'Center',
          0x3004: 'Left'}),
    20: ('ExposureMode',
         {0: 'Easy Shooting',
          1: 'Program',
          2: 'Tv-priority',
          3: 'Av-priority',
          4: 'Manual',
          5: 'A-DEP'}),
    23: ('LongFocalLengthOfLensInFocalUnits', ),
    24: ('ShortFocalLengthOfLensInFocalUnits', ),
    25: ('FocalUnitsPerMM', ),
    28: ('FlashActivity',
         {0: 'Did Not Fire',
          1: 'Fired'}),
    29: ('FlashDetails',
         {14: 'External E-TTL',
          13: 'Internal Flash',
          11: 'FP Sync Used',
          7: '2nd("Rear")-Curtain Sync Used',
          4: 'FP Sync Enabled'}),
    32: ('FocusMode',
         {0: 'Single',
          1: 'Continuous'}),
    }

MAKERNOTE_CANON_TAG_0x004 = {
    7: ('WhiteBalance',
        {0: 'Auto',
         1: 'Sunny',
         2: 'Cloudy',
         3: 'Tungsten',
         4: 'Fluorescent',
         5: 'Flash',
         6: 'Custom'}),
    9: ('SequenceNumber', ),
    14: ('AFPointUsed', ),
    15: ('FlashBias',
         {0xFFC0: '-2 EV',
          0xFFCC: '-1.67 EV',
          0xFFD0: '-1.50 EV',
          0xFFD4: '-1.33 EV',
          0xFFE0: '-1 EV',
          0xFFEC: '-0.67 EV',
          0xFFF0: '-0.50 EV',
          0xFFF4: '-0.33 EV',
          0x0000: '0 EV',
          0x000C: '0.33 EV',
          0x0010: '0.50 EV',
          0x0014: '0.67 EV',
          0x0020: '1 EV',
          0x002C: '1.33 EV',
          0x0030: '1.50 EV',
          0x0034: '1.67 EV',
          0x0040: '2 EV'}),
    19: ('SubjectDistance', ),
    }

# extract multibyte integer in Motorola format (little endian)
def s2n_motorola(str):
    x = 0
    for c in str:
        x = (x << 8) | ord(c)
    return x

# extract multibyte integer in Intel format (big endian)
def s2n_intel(str):
    x = 0
    y = 0L
    for c in str:
        x = x | (ord(c) << y)
        y = y + 8
    return x

# ratio object that eventually will be able to reduce itself to lowest
# common denominator for printing
def gcd(a, b):
    if b == 0:
        return a
    else:
        return gcd(b, a % b)

class Ratio:
    def __init__(self, num, den):
        self.num = num
        self.den = den

    def __repr__(self):
        self.reduce()
        if self.den == 1:
            return str(self.num)
        return '%d/%d' % (self.num, self.den)

    def reduce(self):
        div = gcd(self.num, self.den)
        if div > 1:
            self.num = self.num / div
            self.den = self.den / div

# for ease of dealing with tags
class IFD_Tag:
    def __init__(self, printable, tag, field_type, values, field_offset,
                 field_length):
        # printable version of data
        self.printable = printable
        # tag ID number
        self.tag = tag
        # field type as index into FIELD_TYPES
        self.field_type = field_type
        # offset of start of field in bytes from beginning of IFD
        self.field_offset = field_offset
        # length of data field in bytes
        self.field_length = field_length
        # either a string or array of data items
        self.values = values

    def __str__(self):
        return self.printable

    def __repr__(self):
        return '(0x%04X) %s=%s @ %d' % (self.tag,
                                        FIELD_TYPES[self.field_type][2],
                                        self.printable,
                                        self.field_offset)

# class that handles an EXIF header
class EXIF_header:
    def __init__(self, file, endian, offset, fake_exif, strict, debug=0):
        self.file = file
        self.endian = endian
        self.offset = offset
        self.fake_exif = fake_exif
        self.strict = strict
        self.debug = debug
        self.tags = {}

    # convert slice to integer, based on sign and endian flags
    # usually this offset is assumed to be relative to the beginning of the
    # start of the EXIF information.  For some cameras that use relative tags,
    # this offset may be relative to some other starting point.
    def s2n(self, offset, length, signed=0):
        self.file.seek(self.offset+offset)
        slice=self.file.read(length)
        if self.endian == 'I':
            val=s2n_intel(slice)
        else:
            val=s2n_motorola(slice)
        # Sign extension ?
        if signed:
            msb=1L << (8*length-1)
            if val & msb:
                val=val-(msb << 1)
        return val

    # convert offset to string
    def n2s(self, offset, length):
        s = ''
        for dummy in range(length):
            if self.endian == 'I':
                s = s + chr(offset & 0xFF)
            else:
                s = chr(offset & 0xFF) + s
            offset = offset >> 8
        return s

    # return first IFD
    def first_IFD(self):
        return self.s2n(4, 4)

    # return pointer to next IFD
    def next_IFD(self, ifd):
        entries=self.s2n(ifd, 2)
        return self.s2n(ifd+2+12*entries, 4)

    # return list of IFDs in header
    def list_IFDs(self):
        i=self.first_IFD()
        a=[]
        while i:
            a.append(i)
            i=self.next_IFD(i)
        return a

    # return list of entries in this IFD
    def dump_IFD(self, ifd, ifd_name, dict=EXIF_TAGS, relative=0, stop_tag='UNDEF'):
        entries=self.s2n(ifd, 2)
        for i in range(entries):
            # entry is index of start of this IFD in the file
            entry = ifd + 2 + 12 * i
            tag = self.s2n(entry, 2)

            # get tag name early to avoid errors, help debug
            tag_entry = dict.get(tag)
            if tag_entry:
                tag_name = tag_entry[0]
            else:
                tag_name = 'Tag 0x%04X' % tag

            # ignore certain tags for faster processing
            if not (not detailed and tag in IGNORE_TAGS):
                field_type = self.s2n(entry + 2, 2)
                
                # unknown field type
                if not 0 < field_type < len(FIELD_TYPES):
                    if not self.strict:
                        continue
                    else:
                        raise ValueError('unknown type %d in tag 0x%04X' % (field_type, tag))

                typelen = FIELD_TYPES[field_type][0]
                count = self.s2n(entry + 4, 4)
                # Adjust for tag id/type/count (2+2+4 bytes)
                # Now we point at either the data or the 2nd level offset
                offset = entry + 8

                # If the value fits in 4 bytes, it is inlined, else we
                # need to jump ahead again.
                if count * typelen > 4:
                    # offset is not the value; it's a pointer to the value
                    # if relative we set things up so s2n will seek to the right
                    # place when it adds self.offset.  Note that this 'relative'
                    # is for the Nikon type 3 makernote.  Other cameras may use
                    # other relative offsets, which would have to be computed here
                    # slightly differently.
                    if relative:
                        tmp_offset = self.s2n(offset, 4)
                        offset = tmp_offset + ifd - 8
                        if self.fake_exif:
                            offset = offset + 18
                    else:
                        offset = self.s2n(offset, 4)

                field_offset = offset
                if field_type == 2:
                    # special case: null-terminated ASCII string
                    # XXX investigate
                    # sometimes gets too big to fit in int value
                    if count != 0 and count < (2**31):
                        self.file.seek(self.offset + offset)
                        values = self.file.read(count)
                        #print values
                        # Drop any garbage after a null.
                        values = values.split('\x00', 1)[0]
                    else:
                        values = ''
                else:
                    values = []
                    signed = (field_type in [6, 8, 9, 10])
                    
                    # XXX investigate
                    # some entries get too big to handle could be malformed
                    # file or problem with self.s2n
                    if count < 1000:
                        for dummy in range(count):
                            if field_type in (5, 10):
                                # a ratio
                                value = Ratio(self.s2n(offset, 4, signed),
                                              self.s2n(offset + 4, 4, signed))
                            else:
                                value = self.s2n(offset, typelen, signed)
                            values.append(value)
                            offset = offset + typelen
                    # The test above causes problems with tags that are 
                    # supposed to have long values!  Fix up one important case.
                    elif tag_name == 'MakerNote' :
                        for dummy in range(count):
                            value = self.s2n(offset, typelen, signed)
                            values.append(value)
                            offset = offset + typelen
                    #else :
                    #    print "Warning: dropping large tag:", tag, tag_name
                
                # now 'values' is either a string or an array
                if count == 1 and field_type != 2:
                    printable=str(values[0])
                elif count > 50 and len(values) > 20 :
                    printable=str( values[0:20] )[0:-1] + ", ... ]"
                else:
                    printable=str(values)

                # compute printable version of values
                if tag_entry:
                    if len(tag_entry) != 1:
                        # optional 2nd tag element is present
                        if callable(tag_entry[1]):
                            # call mapping function
                            printable = tag_entry[1](values)
                        else:
                            printable = ''
                            for i in values:
                                # use lookup table for this tag
                                printable += tag_entry[1].get(i, repr(i))

                self.tags[ifd_name + ' ' + tag_name] = IFD_Tag(printable, tag,
                                                          field_type,
                                                          values, field_offset,
                                                          count * typelen)
                if self.debug:
                    print ' debug:   %s: %s' % (tag_name,
                                                repr(self.tags[ifd_name + ' ' + tag_name]))

            if tag_name == stop_tag:
                break

    # extract uncompressed TIFF thumbnail (like pulling teeth)
    # we take advantage of the pre-existing layout in the thumbnail IFD as
    # much as possible
    def extract_TIFF_thumbnail(self, thumb_ifd):
        entries = self.s2n(thumb_ifd, 2)
        # this is header plus offset to IFD ...
        if self.endian == 'M':
            tiff = 'MM\x00*\x00\x00\x00\x08'
        else:
            tiff = 'II*\x00\x08\x00\x00\x00'
        # ... plus thumbnail IFD data plus a null "next IFD" pointer
        self.file.seek(self.offset+thumb_ifd)
        tiff += self.file.read(entries*12+2)+'\x00\x00\x00\x00'

        # fix up large value offset pointers into data area
        for i in range(entries):
            entry = thumb_ifd + 2 + 12 * i
            tag = self.s2n(entry, 2)
            field_type = self.s2n(entry+2, 2)
            typelen = FIELD_TYPES[field_type][0]
            count = self.s2n(entry+4, 4)
            oldoff = self.s2n(entry+8, 4)
            # start of the 4-byte pointer area in entry
            ptr = i * 12 + 18
            # remember strip offsets location
            if tag == 0x0111:
                strip_off = ptr
                strip_len = count * typelen
            # is it in the data area?
            if count * typelen > 4:
                # update offset pointer (nasty "strings are immutable" crap)
                # should be able to say "tiff[ptr:ptr+4]=newoff"
                newoff = len(tiff)
                tiff = tiff[:ptr] + self.n2s(newoff, 4) + tiff[ptr+4:]
                # remember strip offsets location
                if tag == 0x0111:
                    strip_off = newoff
                    strip_len = 4
                # get original data and store it
                self.file.seek(self.offset + oldoff)
                tiff += self.file.read(count * typelen)

        # add pixel strips and update strip offset info
        old_offsets = self.tags['Thumbnail StripOffsets'].values
        old_counts = self.tags['Thumbnail StripByteCounts'].values
        for i in range(len(old_offsets)):
            # update offset pointer (more nasty "strings are immutable" crap)
            offset = self.n2s(len(tiff), strip_len)
            tiff = tiff[:strip_off] + offset + tiff[strip_off + strip_len:]
            strip_off += strip_len
            # add pixel strip to end
            self.file.seek(self.offset + old_offsets[i])
            tiff += self.file.read(old_counts[i])

        self.tags['TIFFThumbnail'] = tiff

    # decode all the camera-specific MakerNote formats

    # Note is the data that comprises this MakerNote.  The MakerNote will
    # likely have pointers in it that point to other parts of the file.  We'll
    # use self.offset as the starting point for most of those pointers, since
    # they are relative to the beginning of the file.
    #
    # If the MakerNote is in a newer format, it may use relative addressing
    # within the MakerNote.  In that case we'll use relative addresses for the
    # pointers.
    #
    # As an aside: it's not just to be annoying that the manufacturers use
    # relative offsets.  It's so that if the makernote has to be moved by the
    # picture software all of the offsets don't have to be adjusted.  Overall,
    # this is probably the right strategy for makernotes, though the spec is
    # ambiguous.  (The spec does not appear to imagine that makernotes would
    # follow EXIF format internally.  Once they did, it's ambiguous whether
    # the offsets should be from the header at the start of all the EXIF info,
    # or from the header at the start of the makernote.)
    def decode_maker_note(self):
        note = self.tags['EXIF MakerNote']
        
        # Some apps use MakerNote tags but do not use a format for which we
        # have a description, so just do a raw dump for these.
        #if self.tags.has_key('Image Make'):
        make = self.tags['Image Make'].printable
        #else:
        #    make = ''

        # model = self.tags['Image Model'].printable # unused

        # Nikon
        # The maker note usually starts with the word Nikon, followed by the
        # type of the makernote (1 or 2, as a short).  If the word Nikon is
        # not at the start of the makernote, it's probably type 2, since some
        # cameras work that way.
        if 'NIKON' in make:
            if note.values[0:7] == [78, 105, 107, 111, 110, 0, 1]:
                if self.debug:
                    print "Looks like a type 1 Nikon MakerNote."
                self.dump_IFD(note.field_offset+8, 'MakerNote',
                              dict=MAKERNOTE_NIKON_OLDER_TAGS)
            elif note.values[0:7] == [78, 105, 107, 111, 110, 0, 2]:
                if self.debug:
                    print "Looks like a labeled type 2 Nikon MakerNote"
                if note.values[12:14] != [0, 42] and note.values[12:14] != [42L, 0L]:
                    raise ValueError("Missing marker tag '42' in MakerNote.")
                # skip the Makernote label and the TIFF header
                self.dump_IFD(note.field_offset+10+8, 'MakerNote',
                              dict=MAKERNOTE_NIKON_NEWER_TAGS, relative=1)
            else:
                # E99x or D1
                if self.debug:
                    print "Looks like an unlabeled type 2 Nikon MakerNote"
                self.dump_IFD(note.field_offset, 'MakerNote',
                              dict=MAKERNOTE_NIKON_NEWER_TAGS)
            return

        # Olympus
        if make.startswith('OLYMPUS'):
            self.dump_IFD(note.field_offset+8, 'MakerNote',
                          dict=MAKERNOTE_OLYMPUS_TAGS)
            # XXX TODO
            #for i in (('MakerNote Tag 0x2020', MAKERNOTE_OLYMPUS_TAG_0x2020),):
            #    self.decode_olympus_tag(self.tags[i[0]].values, i[1])
            #return

        # Casio
        if 'CASIO' in make or 'Casio' in make:
            self.dump_IFD(note.field_offset, 'MakerNote',
                          dict=MAKERNOTE_CASIO_TAGS)
            return

        # Fujifilm
        if make == 'FUJIFILM':
            # bug: everything else is "Motorola" endian, but the MakerNote
            # is "Intel" endian
            endian = self.endian
            self.endian = 'I'
            # bug: IFD offsets are from beginning of MakerNote, not
            # beginning of file header
            offset = self.offset
            self.offset += note.field_offset
            # process note with bogus values (note is actually at offset 12)
            self.dump_IFD(12, 'MakerNote', dict=MAKERNOTE_FUJIFILM_TAGS)
            # reset to correct values
            self.endian = endian
            self.offset = offset
            return

        # Canon
        if make == 'Canon':
            self.dump_IFD(note.field_offset, 'MakerNote',
                          dict=MAKERNOTE_CANON_TAGS)
            for i in (('MakerNote Tag 0x0001', MAKERNOTE_CANON_TAG_0x001),
                      ('MakerNote Tag 0x0004', MAKERNOTE_CANON_TAG_0x004)):
                self.canon_decode_tag(self.tags[i[0]].values, i[1])
            return


    # XXX TODO decode Olympus MakerNote tag based on offset within tag
    def olympus_decode_tag(self, value, dict):
        pass

    # decode Canon MakerNote tag based on offset within tag
    # see http://www.burren.cx/david/canon.html by David Burren
    def canon_decode_tag(self, value, dict):
        for i in range(1, len(value)):
            x=dict.get(i, ('Unknown', ))
            if self.debug:
                print i, x
            name=x[0]
            if len(x) > 1:
                val=x[1].get(value[i], 'Unknown')
            else:
                val=value[i]
            # it's not a real IFD Tag but we fake one to make everybody
            # happy. this will have a "proprietary" type
            self.tags['MakerNote '+name]=IFD_Tag(str(val), None, 0, None,
                                                 None, None)

# process an image file (expects an open file object)
# this is the function that has to deal with all the arbitrary nasty bits
# of the EXIF standard
def process_file(f, stop_tag='UNDEF', details=True, strict=False, debug=False):
    # yah it's cheesy...
    global detailed
    detailed = details

    # by default do not fake an EXIF beginning
    fake_exif = 0

    # determine whether it's a JPEG or TIFF
    data = f.read(12)
    if data[0:4] in ['II*\x00', 'MM\x00*']:
        # it's a TIFF file
        f.seek(0)
        endian = f.read(1)
        f.read(1)
        offset = 0
    elif data[0:2] == '\xFF\xD8':
        # it's a JPEG file
        while data[2] == '\xFF' and data[6:10] in ('JFIF', 'JFXX', 'OLYM', 'Phot'):
            length = ord(data[4])*256+ord(data[5])
            f.read(length-8)
            # fake an EXIF beginning of file
            data = '\xFF\x00'+f.read(10)
            fake_exif = 1
        if data[2] == '\xFF' and data[6:10] == 'Exif':
            # detected EXIF header
            offset = f.tell()
            endian = f.read(1)
        else:
            # no EXIF information
            return {}
    else:
        # file format not recognized
        return {}

    # deal with the EXIF info we found
    if debug:
        print {'I': 'Intel', 'M': 'Motorola'}[endian], 'format'
    hdr = EXIF_header(f, endian, offset, fake_exif, strict, debug)
    ifd_list = hdr.list_IFDs()
    ctr = 0
    for i in ifd_list:
        if ctr == 0:
            IFD_name = 'Image'
        elif ctr == 1:
            IFD_name = 'Thumbnail'
            thumb_ifd = i
        else:
            IFD_name = 'IFD %d' % ctr
        if debug:
            print ' IFD %d (%s) at offset %d:' % (ctr, IFD_name, i)
        hdr.dump_IFD(i, IFD_name, stop_tag=stop_tag)
        # EXIF IFD
        exif_off = hdr.tags.get(IFD_name+' ExifOffset')
        if exif_off:
            if debug:
                print ' EXIF SubIFD at offset %d:' % exif_off.values[0]
            hdr.dump_IFD(exif_off.values[0], 'EXIF', stop_tag=stop_tag)
            # Interoperability IFD contained in EXIF IFD
            intr_off = hdr.tags.get('EXIF SubIFD InteroperabilityOffset')
            if intr_off:
                if debug:
                    print ' EXIF Interoperability SubSubIFD at offset %d:' \
                          % intr_off.values[0]
                hdr.dump_IFD(intr_off.values[0], 'EXIF Interoperability',
                             dict=INTR_TAGS, stop_tag=stop_tag)
        # GPS IFD
        gps_off = hdr.tags.get(IFD_name+' GPSInfo')
        if gps_off:
            if debug:
                print ' GPS SubIFD at offset %d:' % gps_off.values[0]
            hdr.dump_IFD(gps_off.values[0], 'GPS', dict=GPS_TAGS, stop_tag=stop_tag)
        ctr += 1

    # extract uncompressed TIFF thumbnail
    thumb = hdr.tags.get('Thumbnail Compression')
    if thumb and thumb.printable == 'Uncompressed TIFF':
        hdr.extract_TIFF_thumbnail(thumb_ifd)

    # JPEG thumbnail (thankfully the JPEG data is stored as a unit)
    thumb_off = hdr.tags.get('Thumbnail JPEGInterchangeFormat')
    if thumb_off:
        f.seek(offset+thumb_off.values[0])
        size = hdr.tags['Thumbnail JPEGInterchangeFormatLength'].values[0]
        hdr.tags['JPEGThumbnail'] = f.read(size)

    # deal with MakerNote contained in EXIF IFD
    # (Some apps use MakerNote tags but do not use a format for which we
    # have a description, do not process these).
    if 'EXIF MakerNote' in hdr.tags and 'Image Make' in hdr.tags and detailed:
        hdr.decode_maker_note()

    # Sometimes in a TIFF file, a JPEG thumbnail is hidden in the MakerNote
    # since it's not allowed in a uncompressed TIFF IFD
    if 'JPEGThumbnail' not in hdr.tags:
        thumb_off=hdr.tags.get('MakerNote JPEGThumbnail')
        if thumb_off:
            f.seek(offset+thumb_off.values[0])
            hdr.tags['JPEGThumbnail']=file.read(thumb_off.field_length)

    return hdr.tags


# show command line usage
def usage(exit_status):
    msg = 'Usage: EXIF.py [OPTIONS] file1 [file2 ...]\n'
    msg += 'Extract EXIF information from digital camera image files.\n\nOptions:\n'
    msg += '-q --quick   Do not process MakerNotes.\n'
    msg += '-t TAG --stop-tag TAG   Stop processing when this tag is retrieved.\n'
    msg += '-s --strict   Run in strict mode (stop on errors).\n'
    msg += '-d --debug   Run in debug mode (display extra info).\n'
    print msg
    sys.exit(exit_status)

# library test/debug function (dump given files)
if __name__ == '__main__':
    import sys
    import getopt

    # parse command line options/arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hqsdt:v", ["help", "quick", "strict", "debug", "stop-tag="])
    except getopt.GetoptError:
        usage(2)
    if args == []:
        usage(2)
    detailed = True
    stop_tag = 'UNDEF'
    debug = False
    strict = False
    for o, a in opts:
        if o in ("-h", "--help"):
            usage(0)
        if o in ("-q", "--quick"):
            detailed = False
        if o in ("-t", "--stop-tag"):
            stop_tag = a
        if o in ("-s", "--strict"):
            strict = True
        if o in ("-d", "--debug"):
            debug = True

    # output info for each file
    for filename in args:
        try:
            file=open(filename, 'rb')
        except:
            print "'%s' is unreadable\n"%filename
            continue
        print filename + ':'
        # get the tags
        data = process_file(file, stop_tag=stop_tag, details=detailed, strict=strict, debug=debug)
        if not data:
            print 'No EXIF information found'
            continue

        x=data.keys()
        x.sort()
        for i in x:
            if i in ('JPEGThumbnail', 'TIFFThumbnail'):
                continue
            try:
                print '   %s (%s): %s' % \
                      (i, FIELD_TYPES[data[i].field_type][2], data[i].printable)
            except:
                print 'error', i, '"', data[i], '"'
        if 'JPEGThumbnail' in data:
            print 'File has JPEG thumbnail'
        print


########NEW FILE########
__FILENAME__ = reflection
""" Function for generating web 2.0 style image reflection effects.

Copyright (c) 2007, Justin C. Driscoll
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    3. Neither the name of reflection.py nor the names of its contributors may be used
       to endorse or promote products derived from this software without
       specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

try:
    import Image
    import ImageColor
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageColor
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")


def add_reflection(im, bgcolor="#00000", amount=0.4, opacity=0.6):
    """ Returns the supplied PIL Image (im) with a reflection effect

    bgcolor  The background color of the reflection gradient
    amount   The height of the reflection as a percentage of the orignal image
    opacity  The initial opacity of the reflection gradient

    Originally written for the Photologue image management system for Django
    and Based on the original concept by Bernd Schlapsi

    """
    # convert bgcolor string to rgb value
    background_color = ImageColor.getrgb(bgcolor)

    # copy orignial image and flip the orientation
    reflection = im.copy().transpose(Image.FLIP_TOP_BOTTOM)

    # create a new image filled with the bgcolor the same size
    background = Image.new("RGB", im.size, background_color)

    # calculate our alpha mask
    start = int(255 - (255 * opacity)) # The start of our gradient
    steps = int(255 * amount) # the number of intermedite values
    increment = (255 - start) / float(steps)
    mask = Image.new('L', (1, 255))
    for y in range(255):
        if y < steps:
            val = int(y * increment + start)
        else:
            val = 255
        mask.putpixel((0, y), val)
    alpha_mask = mask.resize(im.size)

    # merge the reflection onto our background color using the alpha mask
    reflection = Image.composite(background, reflection, alpha_mask)

    # crop the reflection
    reflection_height = int(im.size[1] * amount)
    reflection = reflection.crop((0, 0, im.size[0], reflection_height))

    # create new image sized to hold both the original image and the reflection
    composite = Image.new("RGB", (im.size[0], im.size[1]+reflection_height), background_color)

    # paste the orignal image and the reflection into the composite image
    composite.paste(im, (0, 0))
    composite.paste(reflection, (0, im.size[1]))

    # return the image complete with reflection effect
    return composite

########NEW FILE########
__FILENAME__ = watermark
""" Function for applying watermarks to images.

Original found here:
http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/362879

"""

try:
    import Image
    import ImageEnhance
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageEnhance
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")

def reduce_opacity(im, opacity):
    """Returns an image with reduced opacity."""
    assert opacity >= 0 and opacity <= 1
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    else:
        im = im.copy()
    alpha = im.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    im.putalpha(alpha)
    return im

def apply_watermark(im, mark, position, opacity=1):
    """Adds a watermark to an image."""
    if opacity < 1:
        mark = reduce_opacity(mark, opacity)
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    # create a transparent layer the size of the image and draw the
    # watermark in that layer.
    layer = Image.new('RGBA', im.size, (0,0,0,0))
    if position == 'tile':
        for y in range(0, im.size[1], mark.size[1]):
            for x in range(0, im.size[0], mark.size[0]):
                layer.paste(mark, (x, y))
    elif position == 'scale':
        # scale, but preserve the aspect ratio
        ratio = min(
            float(im.size[0]) / mark.size[0], float(im.size[1]) / mark.size[1])
        w = int(mark.size[0] * ratio)
        h = int(mark.size[1] * ratio)
        mark = mark.resize((w, h))
        layer.paste(mark, ((im.size[0] - w) / 2, (im.size[1] - h) / 2))
    else:
        layer.paste(mark, position)
    # composite the watermark with the layer
    return Image.composite(layer, im, layer)

def test():
    im = Image.open('test.png')
    mark = Image.open('overlay.png')
    watermark(im, mark, 'tile', 0.5).show()
    watermark(im, mark, 'scale', 1.0).show()
    watermark(im, mark, (100, 100), 0.5).show()

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = test_settings
from tempfile import mkdtemp

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

ROOT_URLCONF = 'photologue.urls'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'photologue',
)

MEDIA_ROOT = mkdtemp()

########NEW FILE########
