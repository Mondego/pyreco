__FILENAME__ = fields
# -*- coding: UTF-8 -*-
from django.db import models
from django.db.models.signals import post_init
from django.db.models.fields import FieldDoesNotExist

from image.video_field import VideoField
from image.forms import ImageCenterFormField


class ImageCenter(object):
    def __init__(self, image_field, x=None, y=None, xy=None):
        self.image_field = image_field
        if (not x is None and y is None) or (x is None and not y is None):
            raise ValueError("If x or y are provided, both have to be provided: x=" + str(x) + ", y=" + str(y))
        if not x is None and not y is None:
            if x < 0 or x > 1 or y < 0 or y > 1:
                raise ValueError("Valid values for x and y go from 0 to 1: x=" + str(x) + ", y=" + str(y))
            self.x = float(x)
            self.y = float(y)
        else:
            if xy is None:
                self.x = .5
                self.y = .5
            else:
                try:
                    x, y = xy.split(",")
                except ValueError:
                    x = .5
                    y = .5
                self.x = float(x)
                self.y = float(y)

    def __unicode__(self):
        return str(self.x) + "," + str(self.y)


class ImageCenterField(models.Field):

    attr_class = ImageCenter

    description = "A field that stores the center of attention for an image."

    __metaclass__ = models.SubfieldBase

    def __init__(self, image_field=None, *args, **kwargs):
        if image_field is not None:
            if not isinstance(image_field, models.ImageField) and  not isinstance(image_field, VideoField):
                raise ValueError("image_field value must be an ImageField or VideoField instance")
        kwargs["default"] = ".5,.5"
        self.image_field = image_field
        super(ImageCenterField, self).__init__(*args, **kwargs)

    def set_instance(self, instance):
        self.instance = instance

    def formfield(self, **kwargs):
        defaults = {'form_class': ImageCenterFormField}
        defaults.update(kwargs)
        return super(ImageCenterField, self).formfield(**defaults)

    def db_type(self, connection):
        return "char(100)"

    # Esta función es llamada al leer un valor de la base de datos
    def to_python(self, value):
        if isinstance(value, ImageCenter):
            return value
        return ImageCenter(self.image_field, xy=value)

    # Esta función es llamada al escribir un valor en la base de datos
    def get_db_prep_value(self, value, connection=None, prepared=False):
        try:
            return str(value.x) + "," + str(value.y)
        except AttributeError:
            return str(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def query_string(self):
        return "center=" + str(self.x) + "," + str(self.y)


def post_init_capture(sender, instance, *args, **kwargs):
    fields = instance.__class__._meta.get_all_field_names()
    for field_name in fields:
        try:
            field = instance.__class__._meta.get_field(field_name)
            if isinstance(field, ImageCenterField):
                image_field = instance.__class__._meta.get_field(field.image_field.name)
                image_instance = instance.__getattribute__(image_field.name)
                image_center_instance = instance.__getattribute__(field.name)
                image_instance.__image_center_instance__ = image_center_instance
                image_center_instance.image_path = unicode(image_instance)
        except FieldDoesNotExist:
            pass

post_init.connect(post_init_capture)

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^image\.fields\.ImageCenterField$"])
    add_introspection_rules([], ["^image\.video_field\.VideoField$"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = forms
# -*- coding: UTF-8 -*-
from django import forms
from django.utils.safestring import mark_safe
from django.forms.util import flatatt
from django.utils.encoding import force_unicode
from django.core.urlresolvers import reverse
import threading

from image.video_field import VideoField


COUNTER = 0


class ImageCenterFormWidget(forms.Widget):

    #def __init__(self, attrs=None):
    #    super(ImageCenterFormWidget, self).__init__(attrs)

    def _format_value(self, value):
        return unicode(value)

    def render(self, name, value, attrs=None):

        global COUNTER

        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))

        resp = ''
        if getattr(value, 'image_path', None):
            try:
                extra_parms = ""
                if isinstance(value.image_field, VideoField):
                    extra_parms += "&video=true"

                extra_parms += "&is_admin=true"

                resp = '<div style="display:inline-block; position:relative; border:1px solid black;">'
                resp += '<img id="image_center-' + str(COUNTER) + '" src="' + reverse('image.views.image', args=(value.image_path, 'format=png&width=150&height=150&mode=scale' + extra_parms)) + '" onclick=""/>'
                resp += '<img id="image_center_crosshair-' + str(COUNTER) + '" src="' + reverse('image.views.crosshair') + '" style="position:absolute; left:0; top:0;" />'
                resp += '</div>'
                resp += '<script>'
                resp += '(function($) {'
                resp += '    $(window).load(function(){'
                resp += '        var crosshair = document.getElementById("image_center_crosshair-' + str(COUNTER) + '");'
                resp += '        var image = document.getElementById("image_center-' + str(COUNTER) + '");'
                resp += '        var iw = $(image).width();'
                resp += '        var ih = $(image).height();'
                resp += '        $(crosshair).css( { left : (iw*' + str(value.x) + ' - 7)+"px", top : (ih*' + str(value.y) + ' - 7)+"px" } );'
                resp += '        $(image).parent().parent().find("input").hide();'
                resp += '        $(image).parent().click(function(e){'
                resp += '            var nx = e.pageX - $(image).offset().left;'
                resp += '            var ny = e.pageY - $(image).offset().top;'
                resp += '            crosshair.style.left=(nx - 7)+"px";'
                resp += '            crosshair.style.top=(ny - 7)+"px";'
                resp += '            $(image).parent().parent().find("input").val( (nx/iw)+","+(ny/ih) );'
                resp += '        });'
                resp += '});'
                resp += '})(django.jQuery);'
                resp += '</script>'
                resp += u'<input%s />' % flatatt(final_attrs)

                lock = threading.Lock()
                with lock:
                    COUNTER += 1
                    if COUNTER > 4000000000:
                        COUNTER = 0
            except AttributeError:
                resp = 'Only available once the image has been saved'

        return mark_safe(resp)


class ImageCenterFormField(forms.Field):

    widget = ImageCenterFormWidget

    def __init__(self, **kwargs):
        kwargs['required'] = False
        super(ImageCenterFormField, self).__init__(kwargs)

    def clean(self, value):
        value = self.to_python(value)
        return value

########NEW FILE########
__FILENAME__ = misc
#-*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse

from image.views import image as image_view
from image.utils import image_create_token


def get_image_url(image, parameters):
    if 'autogen=true' in parameters:
        image_view(None, str(image), parameters, True)
    
    return reverse(
        'image.views.image',
        args=(
            unicode(image),
            image_create_token(parameters)
        )
    )



########NEW FILE########
__FILENAME__ = models
from django.core.files.storage import FileSystemStorage
import os
from django.db.models.signals import post_save, post_delete, pre_save
from django.db.models.fields.files import FileField
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from django.conf import settings as django_settings
from image.storage import IMAGE_CACHE_STORAGE


def safe_delete(path):
    if isinstance(IMAGE_CACHE_STORAGE, FileSystemStorage):
        full_path = os.path.join(IMAGE_CACHE_STORAGE.location, path)
        if os.path.isdir(full_path):
            os.rmdir(full_path)
            return
    IMAGE_CACHE_STORAGE.delete(path)


def remove_directory(dir_path):
    try:
        # Since no all storages support exists for directories, we check for OSError
        contents = IMAGE_CACHE_STORAGE.listdir(dir_path)
    except OSError:
        pass
    else:
        for directory in contents[0]:
            safe_delete(os.path.join(dir_path, directory))
        for filename in contents[1]:
            safe_delete(os.path.join(dir_path, filename))

    if IMAGE_CACHE_STORAGE.exists(dir_path):
        # In some storages like amazon S3 there are no directories
        safe_delete(dir_path)


def remove_cache(image_path):
    if image_path:
        remove_directory(image_path)


def prepare_image_cache_cleanup(sender, instance=None, **kwargs):
    if instance is None:
        return
    instance.old_image_fields = {}

    old_instance = None

    for field in instance._meta.fields:
        if isinstance(field, FileField):
            if not old_instance:
                try:
                    old_instance = sender.objects.get(pk=instance.pk)
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    return

            instance.old_image_fields[field.attname] = field.value_to_string(old_instance)


def clear_prepared_image_cache_cleanup(sender, instance=None, created=False, **kwargs):
    if created:
        return
    if instance is None:
        return
    for field in instance._meta.fields:
        if isinstance(field, FileField):
            if instance.old_image_fields[field.attname] != field.value_to_string(instance):
                remove_cache(instance.old_image_fields[field.attname])


def clear_image_cache(sender, instance, **kwargs):
    for field in instance._meta.fields:
        if isinstance(field, FileField):
            remove_cache(field.value_to_string(instance))


pre_save.connect(prepare_image_cache_cleanup)
post_save.connect(clear_prepared_image_cache_cleanup)
post_delete.connect(clear_image_cache)

#reversion compatibility
if 'reversion' in django_settings.INSTALLED_APPS:
    try:
        from reversion.models import pre_revision_commit, post_revision_commit

        pre_revision_commit.connect(prepare_image_cache_cleanup)
        post_revision_commit.connect(clear_prepared_image_cache_cleanup)
    except ImportError:
        pass

# http://bakery-app01-static.s3.amazonaws.com/image/actuality/file0001116000079.jpg/image_token_73ff82d8ce1577a8a22f5a7d29a772a3ffc6e76c

remove_directory('actuality/file0001116000079.jpg')
########NEW FILE########
__FILENAME__ = settings
# coding=UTF-8
from django.conf import global_settings

__author__ = 'franki'

from django.conf import settings


def get(key, default):
    return getattr(settings, key, default)

IMAGE_DEFAULT_FORMAT = get('IMAGE_DEFAULT_FORMAT', 'JPEG')
IMAGE_DEFAULT_QUALITY = get('IMAGE_DEFAULT_QUALITY', 85)

IMAGE_CACHE_STORAGE = get('IMAGE_CACHE_STORAGE', 'image.storage.ImageCacheStorage')
IMAGE_CACHE_ROOT = get('IMAGE_CACHE_ROOT', None)

# If IMAGE_CACHE_URL differs from the url of the image view then you must always use autogen or have proper rewrite rules on your server
IMAGE_CACHE_URL = get('IMAGE_CACHE_URL', '/image/')


IMAGE_CACHE_HTTP_EXPIRATION = get('IMAGE_CACHE_HTTP_EXPIRATION', 3600 * 24 * 30)

FILE_UPLOAD_TEMP_DIR = get('FILE_UPLOAD_TEMP_DIR', global_settings.FILE_UPLOAD_TEMP_DIR)
STATICFILES_STORAGE = get('STATICFILES_STORAGE', global_settings.STATICFILES_STORAGE)

########NEW FILE########
__FILENAME__ = storage
# coding=UTF-8
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import get_storage_class, FileSystemStorage

from image import settings
from image.settings import IMAGE_CACHE_STORAGE, STATICFILES_STORAGE


__author__ = 'franki'

STORAGE = None


class ImageCacheStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.IMAGE_CACHE_ROOT
        if base_url is None:
            base_url = settings.IMAGE_CACHE_URL
        if not location:
            raise ImproperlyConfigured("IMAGE_CACHE_ROOT not defined.")
        super(ImageCacheStorage, self).__init__(location, base_url, *args, **kwargs)

    def path(self, name):
        if not self.location:
            raise ImproperlyConfigured("IMAGE_CACHE_ROOT not defined.")
        return super(ImageCacheStorage, self).path(name)


def get_storage():
    global STORAGE
    if STORAGE:
        return STORAGE
    if IMAGE_CACHE_STORAGE:
        storage_class = get_storage_class(IMAGE_CACHE_STORAGE)
    else:
        storage_class = get_storage_class()
    STORAGE = storage_class()
    return STORAGE


IMAGE_CACHE_STORAGE = get_storage()
MEDIA_STORAGE = get_storage_class()()
STATIC_STORAGE = get_storage_class(STATICFILES_STORAGE)()



########NEW FILE########
__FILENAME__ = img
# -*- coding: UTF-8 -*-

from django import template
from django.template.defaulttags import register
from django.core.urlresolvers import reverse
from django.db.models.fields.files import ImageFieldFile
import os
from image.storage import IMAGE_CACHE_STORAGE
from image.video_field import VideoFieldFile
from image import views as image_views
from image.utils import image_create_token


def image_tokenize(session, parameters):
    if session:
        token = None
        for k, v in session.items():
            if v == parameters:
                token = k
                break
        if token is None:
            token = image_create_token(parameters)
            session[token] = parameters
    else:
        token = image_create_token(parameters)
    return token


class ImageNode(template.Node):
    def __init__(self, image_field, parameters):
        self.image_field = template.Variable(image_field)
        self.parameters = template.Variable(parameters)

    def render(self, context):
        try:
            request = context['request']
            session = request.session
        except KeyError:
            session = None

        image_field = self.image_field.resolve(context)
        try:
            parameters = self.parameters.resolve(context)
        except template.VariableDoesNotExist:
            parameters = self.parameters

        if isinstance(image_field, VideoFieldFile):
            parameters += "&video=true"

        if isinstance(image_field, ImageFieldFile) or isinstance(image_field, VideoFieldFile):
            try:
                parameters = parameters + "&center=" + image_field.__image_center_instance__.__unicode__()
            except AttributeError:
                pass

        if "autogen=true" in parameters:
            # We want the image to be generated immediately
            image_views.image(None, str(image_field), parameters, True)

        return IMAGE_CACHE_STORAGE.url(os.path.join(unicode(image_field), image_tokenize(session, parameters)))

        # return reverse(
        #     'image.views.image',
        #     args=(
        #         str(image_field),
        #         image_tokenize(session, parameters)
        #     )
        # )


@register.tag(name="image")
def image(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, image_field, parameters = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires 2 arguments " % token.contents.split()[0]

    return ImageNode(image_field, parameters)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: UTF-8 -*-
from django.conf.urls import patterns

urlpatterns = patterns('image.views',
    (r'^crosshair$', 'crosshair'),
    (r'^(?P<path>.*)/((?P<token>.*))$', 'image'),
)

########NEW FILE########
__FILENAME__ = utils
from PIL import Image as pil
from cStringIO import StringIO
import hashlib

from image import settings
from image.settings import IMAGE_DEFAULT_QUALITY, IMAGE_DEFAULT_FORMAT
from image.storage import MEDIA_STORAGE, STATIC_STORAGE


INTERNAL_CACHE_ROOT = "%s/_internal/" % settings.IMAGE_CACHE_ROOT


def power_to_rgb(value):
    if value <= 0.0031308:
        value *= 12.92
    else:
        value = 1.055 * pow(value, 0.416666666667) - 0.055
    return round(value * 255.0)


def rgb_to_power(value):
    value = float(value) / 255.0
    if value <= 0.04045:
        value /= 12.92
    else:
        value = pow( (value + 0.055) / 1.055  , 2.4)
    return value


def add_rgba_to_pixel(pixel, rgba, x_ammount, x_displacement):
    a = rgba[3]
    pa = pixel[3]
    if a == 1.0 and pa == 1.0:
        total_ammount = x_ammount + x_displacement
        rgba_ammount = x_ammount / total_ammount
        pixel_ammount = x_displacement / total_ammount
        return (
                pixel[0] * pixel_ammount + rgba[0] * rgba_ammount,
                pixel[1] * pixel_ammount + rgba[1] * rgba_ammount,
                pixel[2] * pixel_ammount + rgba[2] * rgba_ammount,
                pa * pixel_ammount + a * rgba_ammount,
                )
    else:
        total_ammount = x_ammount + x_displacement
        rgba_ammount = x_ammount / total_ammount
        #rgba_ammount_alpha = rgba_ammount * a
        pixel_ammount = x_displacement / total_ammount
        #pixel_ammount_alpha = pixel_ammount * pa
        return (
                pixel[0] * pixel_ammount + rgba[0] * rgba_ammount,
                pixel[1] * pixel_ammount + rgba[1] * rgba_ammount,
                pixel[2] * pixel_ammount + rgba[2] * rgba_ammount,
                pa * pixel_ammount + a * rgba_ammount,
                )


def image_create_token(parameters):
    return "image_token_%s" % hashlib.sha1(parameters).hexdigest()


def resizeScale(img, width, height, filepath):
    """
    # Esto no hace nada perceptible
    RATIO = 2
    while img.size[0] / RATIO > width or img.size[1] / RATIO > height:
        img = img.resize((int(img.size[0]/RATIO), int(img.size[1]/RATIO)), pil.ANTIALIAS)
    """

    max_width = width
    max_height = height
    
    src_width, src_height = img.size
    src_ratio = float(src_width) / float(src_height)
    dst_width = max_width
    dst_height = dst_width / src_ratio

    if dst_height > max_height:
        dst_height = max_height
        dst_width = dst_height * src_ratio
    
    img_width, img_height = img.size
    img = img.resize((int(dst_width), int(dst_height)), pil.ANTIALIAS)
    
    return img


def resizeCrop(img, width, height, center, force):
    """
    # Esto no hace nada perceptible
    RATIO = 2
    while img.size[0] / RATIO > width or img.size[1] / RATIO > height:
        img = img.resize((int(img.size[0]/RATIO), int(img.size[1]/RATIO)), pil.ANTIALIAS)
    """

    max_width = width
    max_height = height

    if not force:
        img.thumbnail((max_width, max_height), pil.ANTIALIAS)
    else:
        src_width, src_height = img.size
        src_ratio = float(src_width) / float(src_height)
        dst_width, dst_height = max_width, max_height
        dst_ratio = float(dst_width) / float(dst_height)

        if dst_ratio < src_ratio:
            crop_height = src_height
            crop_width = crop_height * dst_ratio
            x_offset = float(src_width - crop_width) / 2
            y_offset = 0
        else:
            crop_width = src_width
            crop_height = crop_width / dst_ratio
            x_offset = 0
            y_offset = float(src_height - crop_height) / 2

        center_x, center_y = center.split(',')
        center_x = float(center_x)
        center_y = float(center_y)

        x_offset = min(
            max(0, center_x * src_width - crop_width / 2),
            src_width - crop_width
        )
        y_offset = min(
            max(0, center_y * src_height - crop_height / 2),
            src_height - crop_height
        )

        img = img.crop((int(x_offset), int(y_offset), int(x_offset) + int(crop_width), int(y_offset) + int(crop_height)))
        img = img.resize((int(dst_width), int(dst_height)), pil.ANTIALIAS)
    
    return img


def do_tint(img, tint):
    
    if tint is None or tint is 'None':
        return
    
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    try:
        tint_red = float(int("0x%s" % tint[0:2], 16)) / 255.0
    except ValueError:
        tint_red = 1.0
     
    try:
        tint_green = float(int("0x%s" % tint[2:4], 16)) / 255.0
    except ValueError:
        tint_green = 1.0
     
    try:
        tint_blue = float(int("0x%s" % tint[4:6], 16)) / 255.0
    except ValueError:
        tint_blue = 1.0
     
    try:
        tint_alpha = float(int("0x%s" % tint[6:8], 16)) / 255.0
    except ValueError:
        tint_alpha = 1.0
 
    try:
        intensity = float(int("0x%s" % tint[8:10], 16))
    except ValueError:
        intensity = 255.0
        
    if intensity > 0.0 and (tint_red != 1.0 or tint_green != 1.0 or tint_blue != 1.0 or tint_alpha != 1.0):
        # Only tint if the color provided is not ffffffff, because that equals no tint
        
        pixels = img.load()
        if intensity == 255.0:
            for y in xrange(img.size[1]):
                for x in xrange(img.size[0]):
                    data = pixels[x, y]
                    pixels[x, y] = (
                        int(float(data[0]) * tint_red),
                        int(float(data[1]) * tint_green),
                        int(float(data[2]) * tint_blue),
                        int(float(data[3]) * tint_alpha),
                    )
        else:
            intensity = intensity / 255.0
            intensity_inv = 1 - intensity
            tint_red *= intensity
            tint_green *= intensity
            tint_blue *= intensity
            tint_alpha *= intensity
            for y in xrange(img.size[1]):
                for x in xrange(img.size[0]):
                    data = pixels[x, y]
                    pixels[x, y] = (
                        int(float(data[0]) * intensity_inv + float(data[0]) * tint_red),
                        int(float(data[1]) * intensity_inv + float(data[1]) * tint_green),
                        int(float(data[2]) * intensity_inv + float(data[2]) * tint_blue),
                        int(float(data[3]) * intensity_inv + float(data[3]) * tint_alpha),
                    )


def do_paste(img, overlay, position):
    overlay_pixels = overlay.load()
    img_pixels = img.load()
    overlay_width, overlay_height = overlay.size
    x_offset, y_offset = position
    
    for y in xrange(min(overlay_height, img.size[1] - y_offset)):
        for x in xrange(min(overlay_width, img.size[0] - x_offset)):
            img_pixel = img_pixels[x + x_offset, y + y_offset]
            overlay_pixel = overlay_pixels[x, y]
            ia = img_pixel[3]
            oa = overlay_pixel[3]
            if oa == 0:
                # overlay is transparent, nothing to do
                continue
            elif oa == 255:
                # overlay is opaque, ignore img pixel
                new_pixel = overlay_pixel
            elif ia == 0:
                # image pixel is 100% transparent, only overlay matters 
                new_pixel = overlay_pixel
            elif ia == 255:
                # simpler math
                oa = float(oa) / 255.0
                oa1 = 1.0 - oa
                new_pixel = (
                             int(power_to_rgb( rgb_to_power(img_pixel[0]) * oa1 + rgb_to_power(overlay_pixel[0]) * oa  )),
                             int(power_to_rgb( rgb_to_power(img_pixel[1]) * oa1 + rgb_to_power(overlay_pixel[1]) * oa  )),
                             int(power_to_rgb( rgb_to_power(img_pixel[2]) * oa1 + rgb_to_power(overlay_pixel[2]) * oa  )),
                             255,
                             )
            else:
                # complex math
                oa = float(oa) / 255.0
                ia = float(ia) / 255.0
                oa1 = 1 - oa
                #total_alpha_percent = oa + ia
                overlay_percent = oa
                image_percent = ia * oa1
                
                new_pixel = (
                             int(power_to_rgb( rgb_to_power(img_pixel[0]) * image_percent + rgb_to_power(overlay_pixel[0]) * overlay_percent  )),
                             int(power_to_rgb( rgb_to_power(img_pixel[1]) * image_percent + rgb_to_power(overlay_pixel[1]) * overlay_percent  )),
                             int(power_to_rgb( rgb_to_power(img_pixel[2]) * image_percent + rgb_to_power(overlay_pixel[2]) * overlay_percent  )),
                             int((oa + ia * oa1) * 255.0),
                             )
            
            img_pixels[x + x_offset, y + y_offset] = new_pixel


def do_overlay(img, overlay_path, overlay_source=None, overlay_tint=None, overlay_size=None, overlay_position=None):
    if overlay_path is None:
        return img

    if overlay_source == 'media':
        overlay = pil.open(MEDIA_STORAGE.open(overlay_path))
    else:
        overlay = pil.open(STATIC_STORAGE.open(overlay_path))

    # We want the overlay to fit in the image
    iw, ih = img.size
    ow, oh = overlay.size
    overlay_ratio = float(ow) / float(oh)
    
    if overlay_size:
        tw, th = overlay_size.split(',')
        ow = int(round(float(tw.strip()) * iw))
        oh = int(round(float(th.strip()) * ih))
        if ow < 0:
            ow = oh * overlay_ratio
        elif oh < 0:
            oh = ow / overlay_ratio
        
        overlay = resizeScale(overlay, ow, oh, overlay_source + "/" + overlay_path)
        ow, oh = overlay.size
    else:
        have_to_scale = False
        if ow > iw:
            ow = iw
            oh = int(float(iw) / overlay_ratio)
            have_to_scale = True
        if oh > ih:
            ow = int(float(ih) * overlay_ratio)
            oh = ih
            have_to_scale = True

        if have_to_scale:
            overlay = resizeScale(overlay, ow, oh, overlay_source + "/" + overlay_path)
            ow, oh = overlay.size

    if overlay_tint:
        do_tint(overlay, overlay_tint)
    
    if not overlay_position:
        target_x = int((iw - ow) / 2)
        target_y = int((ih - oh) / 2)
    else:
        tx, ty = overlay_position.split(',')
        if tx == "":
            target_x = int((iw - ow) / 2)
        else:
            target_x  = int(round(float(tx.strip()) * iw))
        if ty == "":
            target_y = int((ih - oh) / 2)
        else:
            target_y  = int(round(float(ty.strip()) * ih))
        
    """
    TODO: paste seems to be buggy, because pasting over opaque background returns a non opaque image
    (the parts that are not 100% opaque or 100% transparent become partially transparent. 
    the putalpha workareound doesn't seem to look nice enough
    """ 
    #r, g, b, a = img.split()
    #img.paste(overlay, (int((iw - ow) / 2), int((ih - oh) / 2)), overlay)
    #img.putalpha(a)
    do_paste(img, overlay, (target_x, target_y))
    
    return img


def do_overlays(img, overlays, overlay_tints, overlay_sources, overlay_sizes, overlay_positions):
    overlay_index = 0
    
    for overlay in overlays:
        
        try:
            overlay_tint = overlay_tints[overlay_index]
        except (IndexError, TypeError):
            overlay_tint = None
        
        if overlay_tint == "None":
            overlay_tint = None
            
        try:
            overlay_source = overlay_sources[overlay_index]
        except (IndexError, TypeError):
            overlay_source = 'static'
            
        try:
            overlay_size = overlay_sizes[overlay_index]
        except (IndexError, TypeError):
            overlay_size = None
            
        if overlay_size == "None":
            overlay_size = None
            
        try:
            overlay_position = overlay_positions[overlay_index]
        except (IndexError, TypeError):
            overlay_position = None
            
        if overlay_position == "None":
            overlay_position = None
            
        do_overlay(img, overlay, overlay_source, overlay_tint, overlay_size, overlay_position)
        overlay_index += 1


def do_mask(img, mask_path, mask_source, mask_mode=None):
    if mask_path is None:
        return img

    if mask_source == 'media':
        mask = pil.open(MEDIA_STORAGE.open(mask_path)).convert("RGBA")
    else:
        mask = pil.open(STATIC_STORAGE.open(mask_path)).convert("RGBA")

    # We want the mask to have the same size than the image
    if mask_mode == 'distort':
        iw, ih = img.size
        mw, mh = mask.size
        if mw != iw or mh != ih:
            mask = mask.resize((iw, ih), pil.ANTIALIAS)
    
    else:
        # We want the overlay to fit in the image
        iw, ih = img.size
        ow, oh = mask.size
        overlay_ratio = float(ow) / float(oh)
        have_to_scale = False
        if ow > iw:
            ow = iw
            oh = int(float(iw) / overlay_ratio)
        if oh > ih:
            ow = int(float(ih) * overlay_ratio)
            oh = ih
            
        if ow != iw or oh != ih:
            have_to_scale = True
    
        if have_to_scale:
            nmask = mask.resize((ow, oh), pil.ANTIALIAS)
            mask = pil.new('RGBA', (iw, ih))
            #mask.paste(nmask, (int((iw - ow) / 2), int((ih - oh) / 2)), nmask)
            do_paste(mask, nmask, (int((iw - ow) / 2), int((ih - oh) / 2)))
            ow, oh = mask.size

    r, g, b, a = mask.split()
    img.putalpha(a)


def do_fill(img, fill, width, height):
    if fill is None:
        return img

    overlay = img
    
    fill_color = (
        int("0x%s" % fill[0:2], 16),
        int("0x%s" % fill[2:4], 16),
        int("0x%s" % fill[4:6], 16),
        int("0x%s" % fill[6:8], 16),
    )
    img = pil.new("RGBA", (width,height), fill_color)

    iw, ih = img.size
    ow, oh = overlay.size

    #img.paste(overlay, (int((iw - ow) / 2), int((ih - oh) / 2)), overlay)
    do_paste(img, overlay, (int((iw - ow) / 2), int((ih - oh) / 2)))

    return img


def do_padding(img, padding):
    if not padding:
        return img
    try:
        padding = float(padding)*2.0
        if padding > .9:
            padding = .9
        if padding <= 0.0:
            return img
    except ValueError:
        return
    
    iw, ih = img.size
    
    img.thumbnail(
        (
            int( round( float(img.size[0]) * (1.0 - padding) ) ),
            int( round( float(img.size[1]) * (1.0 - padding) ) )
        ),
        pil.ANTIALIAS
        )
    
    img = do_fill(img, "ffffff00", iw, ih)
    
    return img


def do_background(img, background):
    if background is None:
        return img

    overlay = img
    
    fill_color = (
        int("0x%s" % background[0:2], 16),
        int("0x%s" % background[2:4], 16),
        int("0x%s" % background[4:6], 16),
        int("0x%s" % background[6:8], 16),
    )
    img = pil.new("RGBA", overlay.size, fill_color)

    iw, ih = img.size
    ow, oh = overlay.size

    #img.paste(overlay, (int((iw - ow) / 2), int((ih - oh) / 2)), overlay)
    do_paste(img, overlay, (int((iw - ow) / 2), int((ih - oh) / 2)))

    return img


def scaleAndCrop(data, width, height, filepath, force=True, padding=None, overlays=(), overlay_sources=(), overlay_tints=(), overlay_sizes=None, overlay_positions=None, mask=None, mask_source=None, center=".5,.5", format=IMAGE_DEFAULT_FORMAT, quality=IMAGE_DEFAULT_QUALITY, fill=None, background=None, tint=None):
    """Rescale the given image, optionally cropping it to make sure the result image has the specified width and height."""

    input_file = StringIO(data)
    img = pil.open(input_file)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    img = resizeCrop(img, width, height, center, force)

    do_tint(img, tint)
    img = do_fill(img, fill, width, height)
    img = do_background(img, background)
    do_mask(img, mask, mask_source)
    do_overlays(img, overlays, overlay_tints, overlay_sources, overlay_sizes, overlay_positions)
    img = do_padding(img, padding)

    tmp = StringIO()
    img.save(tmp, format, quality=quality)
    tmp.seek(0)
    output_data = tmp.getvalue()
    input_file.close()
    tmp.close()

    return output_data


def scale(data, width, height, filepath, padding=None, overlays=(), overlay_sources=(), overlay_tints=(), overlay_sizes=None, overlay_positions=None, mask=None, mask_source=None, format=IMAGE_DEFAULT_FORMAT, quality=IMAGE_DEFAULT_QUALITY, fill=None, background=None, tint=None):
    """Rescale the given image, optionally cropping it to make sure the result image has the specified width and height."""


    input_file = StringIO(data)
    img = pil.open(input_file)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    img = resizeScale(img, width, height, filepath)

    do_tint(img, tint)
    img = do_fill(img, fill, width, height)
    img = do_background(img, background)
    do_mask(img, mask, mask_source)
    do_overlays(img, overlays, overlay_tints, overlay_sources, overlay_sizes, overlay_positions)
    img = do_padding(img, padding)

    tmp = StringIO()
    img.save(tmp, format, quality=quality)
    tmp.seek(0)
    output_data = tmp.getvalue()
    input_file.close()
    tmp.close()

    return output_data

########NEW FILE########
__FILENAME__ = videothumbs
# -*- encoding: utf-8 -*-
"""
django-videothumbs
"""

import cStringIO
from django.conf.global_settings import FILE_UPLOAD_TEMP_DIR
import math
import os
import time
from PIL import Image

def generate_thumb(storage, video_path, thumb_size=None, format='jpg', frames=100, width=100, height=100):
    histogram = []

    http_status = 200
    
    name = video_path
    path = video_path

    if not storage.exists(video_path):
        return "", '404'

    framemask = "%s%s%s%s" % (FILE_UPLOAD_TEMP_DIR,
                              name.split('/')[-1].split('.')[0] + str(time.time()),
                              '.%d.',
                              format)
    # ffmpeg command for grabbing N number of frames
    cmd = "/usr/bin/ffmpeg -y -t 00:00:05 -i '%s' '%s'" % (path, framemask)

    # make sure that this command worked or return.
    if os.system(cmd) != 0:
        return "", '500'

    # loop through the generated images, open, and generate the image histogram.
    for i in range(1, frames + 1):
        fname = framemask % i

        if not storage.exists(fname):
            break

        image = Image.open(fname)

        # Convert to RGB if necessary
        if image.mode not in ('L', 'RGB'):
            image = image.convert('RGB')

        # The list of image historgrams
        histogram.append(image.histogram())

    n = len(histogram)
    avg = []

    # Get the image average of the first image
    for c in range(len(histogram[0])):
        ac = 0.0
        for i in range(n):
            ac = ac + (float(histogram[i][c]) / n)
        avg.append(ac)

    minn = -1
    minRMSE = -1

    # Compute the mean squared error
    for i in range(1, n + 1):
        results = 0.0
        num = len(avg)

        for j in range(num):
            median_error = avg[j] - float(histogram[i - 1][j])
            results += (median_error * median_error) / num
        rmse = math.sqrt(results)

        if minn == -1 or rmse < minRMSE:
            minn = i
            minRMSE = rmse

    file_location = framemask % (minn)
    image = Image.open(file_location)

    # If you want to generate a square thumbnail
    if not thumb_size is None:
        thumb_w, thumb_h = thumb_size

        if thumb_w == thumb_h:
            # quad
            xsize, ysize = image.size
            # get minimum size
            minsize = min(xsize, ysize)
            # largest square possible in the image
            xnewsize = (xsize - minsize) / 2
            ynewsize = (ysize - minsize) / 2
            # crop it
            image2 = image.crop((xnewsize, ynewsize, xsize - xnewsize, ysize - ynewsize))
            # load is necessary after crop
            image2.load()
            # thumbnail of the cropped image (with ANTIALIAS to make it look better)
            image2.thumbnail(thumb_size, Image.ANTIALIAS)
        else:
            # not quad
            image2 = image
            image2.thumbnail(thumb_size, Image.ANTIALIAS)
    else:
        image2 = image

    io = cStringIO.StringIO()

    # PNG and GIF are the same, JPG is JPEG
    if format.upper() == 'JPG':
        format = 'JPEG'

    image2.save(io, format)

    # We don't know how many frames we capture. We just captured the first 5 seconds, so keep removing until not found
    for i in range(1, 9999):
        fname = framemask % i
        try:
            os.unlink(fname)
        except OSError:
            break

    return io.getvalue(), http_status

########NEW FILE########
__FILENAME__ = video_field
from django.db import models
from django.db.models.fields.files import FieldFile


# A video field is exactly a file field with a different signature
class VideoFieldFile(FieldFile):
    pass


class VideoField(models.FileField):
    attr_class = VideoFieldFile

########NEW FILE########
__FILENAME__ = views
# -*- coding: UTF-8 -*-
from django.core.files.base import ContentFile
from encodings.base64_codec import base64_decode
import os
import urllib
import traceback

from django.http import HttpResponse, QueryDict
from django.http.response import Http404
from django.utils import timezone
from django.utils.encoding import smart_unicode

from image.settings import IMAGE_CACHE_HTTP_EXPIRATION, IMAGE_CACHE_ROOT
from image.storage import IMAGE_CACHE_STORAGE, MEDIA_STORAGE, STATIC_STORAGE
from image.utils import scale, scaleAndCrop, IMAGE_DEFAULT_FORMAT, IMAGE_DEFAULT_QUALITY,\
    image_create_token
from image.videothumbs import generate_thumb


def image(request, path, token, autogen=False):

    is_admin = False
    if ("is_admin=true" in token and request and request.user.has_perm('admin')) or autogen:
        parameters = token
        is_admin = True
        if autogen:
            token = image_create_token(parameters)
    else:
        parameters = request.session.get(token, token)

    cached_image_file = os.path.join(path, token)

    now = timezone.now()
    expire_offset = timezone.timedelta(seconds=IMAGE_CACHE_HTTP_EXPIRATION)

    response = HttpResponse()
    response['Content-type'] = 'image/jpeg'
    response['Expires'] = (now + expire_offset).strftime("%a, %d %b %Y %T GMT")
    response['Last-Modified'] = now.strftime("%a, %d %b %Y %T GMT")
    response['Cache-Control'] = 'max-age=3600, must-revalidate'
    response.status_code = 200

    # If we already have the cache we send it instead of recreating it
    if IMAGE_CACHE_STORAGE.exists(cached_image_file):
        
        if autogen:
            return 'Already generated'
        
        try:
            f = IMAGE_CACHE_STORAGE.open(cached_image_file, "r")
        except IOError:
            raise Http404()
        response.write(f.read())
        f.close()

        response['Last-Modified'] = IMAGE_CACHE_STORAGE.modified_time(cached_image_file).strftime("%a, %d %b %Y %T GMT")
        return response
    
    if parameters == token and not is_admin:
        return HttpResponse("Forbidden", status=403)

    qs = QueryDict(parameters)

    file_storage = MEDIA_STORAGE
    if qs.get('static', '') == "true":
        file_storage = STATIC_STORAGE

    format = qs.get('format', IMAGE_DEFAULT_FORMAT)
    quality = int(qs.get('quality', IMAGE_DEFAULT_QUALITY))
    mask = qs.get('mask', None)
    mask_source = qs.get('mask_source', None)

    if mask is not None:
        format = "PNG"

    fill = qs.get('fill', None)
    background = qs.get('background', None)
    tint = qs.get('tint', None)

    center = qs.get('center', ".5,.5")
    mode = qs.get('mode', "crop")
        
    overlays = qs.getlist('overlay')
    overlay_sources = qs.getlist('overlay_source')
    overlay_tints = qs.getlist('overlay_tint')
    overlay_sizes = qs.getlist('overlay_size')
    overlay_positions = qs.getlist('overlay_position')

    width = int(qs.get('width', None))
    height = int(qs.get('height', None))
    try:
        padding = float(qs.get('padding',None))
    except TypeError:
        padding = 0.0

    if "video" in qs:
        data, http_response = generate_thumb(file_storage, smart_unicode(path), width=width, height=height)
        response.status_code = http_response
    else:
        try:
            try:
                f = urllib.urlopen(qs['url'])
                data = f.read()
                f.close()
            except KeyError:
                f = file_storage.open(path)
                data = f.read()
                f.close()
        except IOError:
            response.status_code = 404
            data = ""

    if data:
        try:
            if mode == "scale":
                output_data = scale(data, width, height, path, padding=padding, overlays=overlays, overlay_sources=overlay_sources, overlay_tints=overlay_tints, overlay_positions=overlay_positions, overlay_sizes=overlay_sizes, mask=mask, mask_source=mask_source, format=format, quality=quality, fill=fill, background=background, tint=tint)
            else:
                output_data = scaleAndCrop(data, width, height, path, True, padding=padding, overlays=overlays, overlay_sources=overlay_sources, overlay_tints=overlay_tints, overlay_positions=overlay_positions, overlay_sizes=overlay_sizes, mask=mask, mask_source=mask_source, center=center, format=format, quality=quality, fill=fill, background=background, tint=tint)
        except IOError:
            traceback.print_exc()
            response.status_code = 500
            output_data = ""
    else:
        output_data = data

    if response.status_code == 200:
        IMAGE_CACHE_STORAGE.save(cached_image_file,  ContentFile(output_data))
        if autogen:
            return 'Generated ' + str(response.status_code)
    else:
        if autogen:
            return 'Failed ' + cached_image_file
    
    response.write(output_data)

    return response


def crosshair(request):

    response = HttpResponse()
    response['Content-type'] = 'image/png'
    response['Expires'] = 'Fri, 09 Dec 2327 08:34:31 GMT'
    response['Last-Modified'] = 'Fri, 24 Sep 2010 11:36:29 GMT'
    output, length = base64_decode('iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAAwElEQVQoz6WTwY0CMQxFX7DEVjCShUQnc6YCdzCH1EYDboICphb28veA2UULSBHzLpEif9vfcRr/kHQF9jzz3Vr74hWSLpKUmYoIubvMTO6uiFBmqri8FPbeBazAAhwBq3MB1t77c4IH4flNy9T9+Z7g12Nm3iu+Ez4mWMvCFUmKCFVrIywRcasuSe6u8jbC0d3/xGamGs4IZmaSpB3ANE0Ah0HxoeLZAczzDHAaFJ8qfuO0N73z5g37dLfbll/1A+4O0Wm4+ZiPAAAAAElFTkSuQmCC')
    response.write(output)
    return response

########NEW FILE########
