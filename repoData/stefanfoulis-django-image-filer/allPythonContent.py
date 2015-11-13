__FILENAME__ = cms_plugins
from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _
from image_filer.models import ImagePublication, ImageFilerTeaser, FolderPublication

class ImagePlugin(CMSPluginBase):
    model = ImagePublication
    name = _("Image (image filer)")
    render_template = "cms/plugins/image.html"
    text_enabled = True
    raw_id_fields = ('image',)
    
    def render(self, context, instance, placeholder):
        if not instance.width:
            try:
                theme = context['theme']
                width = int(theme.split('_')[0]) * 60
                if width < 960:
                    width -= 20
            except (KeyError, IndexError):
                width = ''
        else:
            width = instance.width
        if instance.height:
            height = instance.height
        else:
            height = '1000'
        if instance.free_link:
            link = instance.free_link
        elif instance.page_link:
            link = instance.page_link.get_absolute_url()
        else:
            link = ""
        context.update({
            'picture':instance,
            'link':link, 
            'image_size': u'%sx%s' % (width, height),
            'placeholder':placeholder
        })
        return context
    def icon_src(self, instance):
        return instance.image.thumbnails['admin_tiny_icon']
plugin_pool.register_plugin(ImagePlugin)

class ImageFilerTeaserPlugin(CMSPluginBase):
    model = ImageFilerTeaser
    name = _("Teaser (image filer)")
    render_template = "cms/plugins/teaser.html"
    
    def render(self, context, instance, placeholder):
        if instance.url:
            link = instance.url
        elif instance.page_link:
            link = instance.page_link.get_absolute_url()
        else:
            link = ""
        context.update({
            'object':instance, 
            'placeholder':placeholder,
            'link':link
        })
        return context
plugin_pool.register_plugin(ImageFilerTeaserPlugin)

class ImageFolderPlugin(CMSPluginBase):
    model = FolderPublication
    name = _("Image Folder from Filer")
    render_template = "image_filer/folder.html"
    text_enabled = True
    #change_form_template = 'admin/image_filer/cms/image_plugin/change_form.html'
    raw_id_fields = ('folder',)
    
    def render(self, context, instance, placeholder):
        context.dicts.append({'image_folder_publication':instance, 'placeholder':placeholder})
        return context
    def icon_src(self, instance):
        return "(none)"
plugin_pool.register_plugin(ImageFolderPlugin)

class FolderSlideshowPlugin(ImageFolderPlugin):
    name = _("Slideshow of image folder")
    class Meta:
        proxy = True
    render_template = "image_filer/slideshow2.html"
plugin_pool.register_plugin(FolderSlideshowPlugin)

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings

def media(request):
    """
    Adds media-related context variables to the context.
    """
    # Use special variable from projects settings or fall back to the
    # general media URL.
    try:
        result = settings.IMAGE_FILER_MEDIA_URL
    except AttributeError:
        try:
            result = settings.MEDIA_URL+'image_filer/'
        except:
            result = ""
    
    return {'IMAGE_FILER_MEDIA_URL': result,
            # This would better be exported by django's context_processor.media.
            'ADMIN_MEDIA_PREFIX': settings.ADMIN_MEDIA_PREFIX}

########NEW FILE########
__FILENAME__ = fields
from django.utils.translation import ugettext as _
from django.utils.text import truncate_words
from django.utils import simplejson
from django.db import models
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
from sorl.thumbnail.base import ThumbnailException
from image_filer import context_processors

class ImageFilerImageWidget(ForeignKeyRawIdWidget):
    choices = None
    input_type = 'hidden'
    is_hidden = True
    def render(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id', 'id_image_x')
        css_id_thumbnail_img = "%s_thumbnail_img" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
        if attrs is None:
            attrs = {}
        related_url = reverse('admin:image_filer-directory_listing-root')
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript looks for this hook.
        output = []
        if obj:
            try:
                output.append(u'<img id="%s" src="%s" alt="%s" /> ' % (css_id_thumbnail_img, obj.thumbnails['admin_tiny_icon'], obj.label) )
            except ThumbnailException:
                # this means that the image is missing on the filesystem
                output.append(u'<img id="%s" src="%s" alt="%s" /> ' % (css_id_thumbnail_img, '', 'image missing!') )
            output.append(u'&nbsp;<strong id="%s">%s</strong>' % (css_id_description_txt, obj) )
        else:
            output.append(u'<img id="%s" src="" class="quiet" alt="no image selected">' % css_id_thumbnail_img)
            output.append(u'&nbsp;<strong id="%s">%s</strong>' % (css_id_description_txt, '') )
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append('<a href="%s%s" class="related-lookup" id="lookup_id_%s" onclick="return showRelatedObjectLookupPopup(this);"> ' % \
            (related_url, url, name))
        output.append('<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="%s" /></a>' % (settings.ADMIN_MEDIA_PREFIX, _('Lookup')))
        output.append('''<a href="" class="deletelink" onclick="return removeImageLink('%s');">&nbsp;</a>''' % (css_id,) )
        output.append('</br>')
        super_attrs = attrs.copy()
        output.append( super(ForeignKeyRawIdWidget, self).render(name, value, super_attrs) )
        return mark_safe(u''.join(output))
    def label_for_value(self, value):
        obj = self.obj_for_value(value)
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)
    def obj_for_value(self, value):
        try:
            key = self.rel.get_related_field().name
            obj = self.rel.to._default_manager.get(**{key: value})
        except:
            obj = None
        return obj
    
    class Media:
        js = (context_processors.media(None)['IMAGE_FILER_MEDIA_URL']+'js/image_widget_thumbnail.js',
              context_processors.media(None)['IMAGE_FILER_MEDIA_URL']+'js/popup_handling.js',)

class ImageFilerImageFormField(forms.ModelChoiceField):
    widget = ImageFilerImageWidget 
    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        other_widget = kwargs.pop('widget', None)
        forms.Field.__init__(self, widget=self.widget(rel), *args, **kwargs)

class ImageFilerModelImageField(models.ForeignKey):
    def __init__(self, **kwargs):
        from image_filer.models import Image
        return super(ImageFilerModelImageField,self).__init__(Image, **kwargs)
    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        #defaults = {'form_class': ImageFilerImageWidget}
        defaults = {
            'form_class': ImageFilerImageFormField,
            'rel': self.rel,
        }
        defaults.update(kwargs)
        return super(ImageFilerModelImageField, self).formfield(**defaults)
    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.related.ForeignKey"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

class ImageFilerFolderWidget(ForeignKeyRawIdWidget):
    choices = None
    input_type = 'hidden'
    is_hidden = True
    def render(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id')
        css_id_name = "%s_name" % css_id
        if attrs is None:
            attrs = {}
        related_url = reverse('admin:image_filer-directory_listing-root')
        params = self.url_parameters()
        params['select_folder'] = 1
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript looks for this hook.
        output = []
        if obj:
            output.append(u'Folder: <span id="%s">%s</span>' % (css_id_name,obj.name))
        else:
            output.append(u'Folder: <span id="%s">none selected</span>' % css_id_name)
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append('<a href="%s%s" class="related-lookup" id="lookup_id_%s" onclick="return showRelatedObjectLookupPopup(this);"> ' % \
            (related_url, url, name))
        output.append('<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="%s" /></a>' % (settings.ADMIN_MEDIA_PREFIX, _('Lookup')))
        output.append('</br>')
        super_attrs = attrs.copy()
        output.append( super(ForeignKeyRawIdWidget, self).render(name, value, super_attrs) )
        return mark_safe(u''.join(output))
    def label_for_value(self, value):
        obj = self.obj_for_value(value)
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)
    def obj_for_value(self, value):
        try:
            key = self.rel.get_related_field().name
            obj = self.rel.to._default_manager.get(**{key: value})
        except:
            obj = None
        return obj
    
    class Media:
        js = (context_processors.media(None)['IMAGE_FILER_MEDIA_URL']+'js/popup_handling.js',)

class ImageFilerFolderFormField(forms.ModelChoiceField):
    widget = ImageFilerFolderWidget 
    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        other_widget = kwargs.pop('widget', None)
        forms.Field.__init__(self, widget=self.widget(rel), *args, **kwargs)

class ImageFilerModelFolderField(models.ForeignKey):
    def __init__(self, **kwargs):
        from image_filer.models import Folder
        return super(ImageFilerModelFolderField,self).__init__(Folder, **kwargs)
    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        #defaults = {'form_class': ImageFilerImageWidget}
        defaults = {
            'form_class': ImageFilerFolderFormField,
            'rel': self.rel,
        }
        defaults.update(kwargs)
        return super(ImageFilerModelFolderField, self).formfield(**defaults)

########NEW FILE########
__FILENAME__ = filters
from inspect import isclass
from fnmatch import filter
try:
    import Image
    import ImageColor
    import ImageFile
    import ImageFilter
    import ImageEnhance
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageColor
        from PIL import ImageFile
        from PIL import ImageFilter
        from PIL import ImageEnhance
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")

#filters = [] #hack for compatibility
filters_by_identifier = {}

class FilterRegistry(object):
    def __init__(self):
        self.builtin_filters = {}
        self.application_filters = {}
        self.project_filters = {}
        self.db_filters = {}
        self.registry_priority = [self.db_filters, self.project_filters,
                                  self.application_filters, self.builtin_filters]
    
    def _register(self, filter, library):
        library[filter.identifier] = filter
        filters_by_identifier[filter.identifier] = filter #hack for compatibility
        
    def register_builtin_filter(self, filter):
        self._register(filter, self.builtin_filters)
    def register_application_filter(self, filter):
        self._register(filter, self.application_filters)
    def register_project_filter(self, filter):
        self._register(filter, self.project_filters)
    def register_db_filter(self, filter):
        self._register(filter, self.db_filters)
    def register(self, filter):
        self.register_project_filter(filter)
    
    def get(self, identifier):
        for reg in self.registry_priority:
            if reg.has_key(identifier):
                return reg[identifier]
        return None
        
library = FilterRegistry()


class BaseFilter(object):
    identifier = "base_filter"

class ResizeFilter(BaseFilter):
    name = "Resize to specified dimensions"
    identifier = "resize_simple"
    def render(self, im, size_x=48, size_y=48, crop=True, crop_from='top', upscale=True):
        cur_width, cur_height = im.size
        new_width, new_height = (size_x, size_y)
        if crop:
            ratio = max(float(new_width)/cur_width,float(new_height)/cur_height)
            x = (cur_width * ratio)
            y = (cur_height * ratio)
            xd = abs(new_width - x)
            yd = abs(new_height - y)
            x_diff = int(xd / 2)
            y_diff = int(yd / 2)
            if crop_from == 'top':
                box = (int(x_diff), 0, int(x_diff+new_width), new_height)
            elif crop_from == 'left':
                box = (0, int(y_diff), new_width, int(y_diff+new_height))
            elif crop_from == 'bottom':
                box = (int(x_diff), int(yd), int(x_diff+new_width), int(y)) # y - yd = new_height
            elif crop_from == 'right':
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
            print new_dimensions
            if new_dimensions[0] > cur_width or \
               new_dimensions[1] > cur_height:
                if not upscale:
                    return im
            im = im.resize(new_dimensions, Image.ANTIALIAS)
        return im
library.register_builtin_filter(ResizeFilter)

class ReflectionFilter(BaseFilter):
    name = "Sexy Web 2.0 reflection filter"
    identifier = "reflection"
    def render(self, im, bgcolor="#FFFFFF", amount=0.4, opacity=0.6):
        """ Returns the supplied PIL Image (im) with a reflection effect
    
        bgcolor  The background color of the reflection gradient
        amount   The height of the reflection as a percentage of the orignal image
        opacity  The initial opacity of the reflection gradient
    
        Originally written for the Photologue image management system for Django
        and Based on the original concept by Bernd Schlapsi
    
        """
        print "reflection filter"
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
library.register_builtin_filter(ReflectionFilter)
"""
Create image filter objects for all the built in PIL filters
"""
for n in dir(ImageFilter):
    klass = getattr(ImageFilter, n)
    if isclass(klass) and issubclass(klass, ImageFilter.BuiltinFilter) and \
            hasattr(klass, 'name'):
        class NewSubclass(BaseFilter):
            _pil_filter = klass
            name = klass.name
            identifier = klass.name.replace(' ', '').lower()
            def render(self, im):
                return im.filter(self._pil_filter)
        NewSubclass.__name__ = "%s%s" % (klass.name, "Filter")
        library.register_builtin_filter(NewSubclass)

########NEW FILE########
__FILENAME__ = forms
from django.forms.models import ModelForm
from image_filer.models import ImagePublication
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

# Not Used
class ImagePublicationForm(ModelForm):
    image = ForeignKeyRawIdWidget('Image')
    class Meta:
        model = ImagePublication
        exclude = ('page', 'position', 'placeholder', 'language', 'plugin_type')
    def __init__(self, *args, **kwargs):
        #print "test: ", ImagePublication.image.rel
        return super(ImagePublicationForm, self).__init__(*args, **kwargs)
        #self.fields['image'].widget = ForeignKeyRawIdWidget('Image')
########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from image_filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Folder'
        db.create_table('image_filer_folder', (
            ('id', orm['image_filer.Folder:id']),
            ('parent', orm['image_filer.Folder:parent']),
            ('name', orm['image_filer.Folder:name']),
            ('owner', orm['image_filer.Folder:owner']),
            ('uploaded_at', orm['image_filer.Folder:uploaded_at']),
            ('created_at', orm['image_filer.Folder:created_at']),
            ('modified_at', orm['image_filer.Folder:modified_at']),
            ('lft', orm['image_filer.Folder:lft']),
            ('rght', orm['image_filer.Folder:rght']),
            ('tree_id', orm['image_filer.Folder:tree_id']),
            ('level', orm['image_filer.Folder:level']),
        ))
        db.send_create_signal('image_filer', ['Folder'])
        
        # Adding model 'FolderPermission'
        db.create_table('image_filer_folderpermission', (
            ('id', orm['image_filer.FolderPermission:id']),
            ('folder', orm['image_filer.FolderPermission:folder']),
            ('type', orm['image_filer.FolderPermission:type']),
            ('user', orm['image_filer.FolderPermission:user']),
            ('group', orm['image_filer.FolderPermission:group']),
            ('everybody', orm['image_filer.FolderPermission:everybody']),
            ('can_edit', orm['image_filer.FolderPermission:can_edit']),
            ('can_read', orm['image_filer.FolderPermission:can_read']),
            ('can_add_children', orm['image_filer.FolderPermission:can_add_children']),
        ))
        db.send_create_signal('image_filer', ['FolderPermission'])
        
        # Adding model 'ImageManipulationProfile'
        db.create_table('image_filer_imagemanipulationprofile', (
            ('id', orm['image_filer.ImageManipulationProfile:id']),
            ('name', orm['image_filer.ImageManipulationProfile:name']),
            ('description', orm['image_filer.ImageManipulationProfile:description']),
            ('show_in_library', orm['image_filer.ImageManipulationProfile:show_in_library']),
        ))
        db.send_create_signal('image_filer', ['ImageManipulationProfile'])
        
        # Adding model 'Bucket'
        db.create_table('image_filer_bucket', (
            ('id', orm['image_filer.Bucket:id']),
            ('user', orm['image_filer.Bucket:user']),
        ))
        db.send_create_signal('image_filer', ['Bucket'])
        
        # Adding model 'BucketItem'
        db.create_table('image_filer_bucketitem', (
            ('id', orm['image_filer.BucketItem:id']),
            ('file', orm['image_filer.BucketItem:file']),
            ('bucket', orm['image_filer.BucketItem:bucket']),
            ('is_checked', orm['image_filer.BucketItem:is_checked']),
        ))
        db.send_create_signal('image_filer', ['BucketItem'])
        
        # Adding model 'ImageManipulationStep'
        db.create_table('image_filer_imagemanipulationstep', (
            ('id', orm['image_filer.ImageManipulationStep:id']),
            ('template', orm['image_filer.ImageManipulationStep:template']),
            ('filter_identifier', orm['image_filer.ImageManipulationStep:filter_identifier']),
            ('name', orm['image_filer.ImageManipulationStep:name']),
            ('description', orm['image_filer.ImageManipulationStep:description']),
            ('data', orm['image_filer.ImageManipulationStep:data']),
            ('order', orm['image_filer.ImageManipulationStep:order']),
        ))
        db.send_create_signal('image_filer', ['ImageManipulationStep'])
        
        # Adding model 'Image'
        db.create_table('image_filer_image', (
            ('id', orm['image_filer.Image:id']),
            ('original_filename', orm['image_filer.Image:original_filename']),
            ('name', orm['image_filer.Image:name']),
            ('owner', orm['image_filer.Image:owner']),
            ('uploaded_at', orm['image_filer.Image:uploaded_at']),
            ('modified_at', orm['image_filer.Image:modified_at']),
            ('file', orm['image_filer.Image:file']),
            ('_height_field', orm['image_filer.Image:_height_field']),
            ('_width_field', orm['image_filer.Image:_width_field']),
            ('date_taken', orm['image_filer.Image:date_taken']),
            ('manipulation_profile', orm['image_filer.Image:manipulation_profile']),
            ('parent', orm['image_filer.Image:parent']),
            ('folder', orm['image_filer.Image:folder']),
            ('contact', orm['image_filer.Image:contact']),
            ('default_alt_text', orm['image_filer.Image:default_alt_text']),
            ('default_caption', orm['image_filer.Image:default_caption']),
            ('author', orm['image_filer.Image:author']),
            ('must_always_publish_author_credit', orm['image_filer.Image:must_always_publish_author_credit']),
            ('must_always_publish_copyright', orm['image_filer.Image:must_always_publish_copyright']),
            ('can_use_for_web', orm['image_filer.Image:can_use_for_web']),
            ('can_use_for_print', orm['image_filer.Image:can_use_for_print']),
            ('can_use_for_teaching', orm['image_filer.Image:can_use_for_teaching']),
            ('can_use_for_research', orm['image_filer.Image:can_use_for_research']),
            ('can_use_for_private_use', orm['image_filer.Image:can_use_for_private_use']),
            ('usage_restriction_notes', orm['image_filer.Image:usage_restriction_notes']),
            ('notes', orm['image_filer.Image:notes']),
            ('has_all_mandatory_data', orm['image_filer.Image:has_all_mandatory_data']),
            ('lft', orm['image_filer.Image:lft']),
            ('rght', orm['image_filer.Image:rght']),
            ('tree_id', orm['image_filer.Image:tree_id']),
            ('level', orm['image_filer.Image:level']),
        ))
        db.send_create_signal('image_filer', ['Image'])
        
        # Adding model 'ImageManipulationTemplate'
        db.create_table('image_filer_imagemanipulationtemplate', (
            ('id', orm['image_filer.ImageManipulationTemplate:id']),
            ('identifier', orm['image_filer.ImageManipulationTemplate:identifier']),
            ('name', orm['image_filer.ImageManipulationTemplate:name']),
            ('description', orm['image_filer.ImageManipulationTemplate:description']),
            ('profile', orm['image_filer.ImageManipulationTemplate:profile']),
            ('pre_cache', orm['image_filer.ImageManipulationTemplate:pre_cache']),
        ))
        db.send_create_signal('image_filer', ['ImageManipulationTemplate'])
        
        # Adding model 'ImagePermission'
        db.create_table('image_filer_imagepermission', (
            ('id', orm['image_filer.ImagePermission:id']),
            ('image', orm['image_filer.ImagePermission:image']),
            ('type', orm['image_filer.ImagePermission:type']),
            ('user', orm['image_filer.ImagePermission:user']),
            ('group', orm['image_filer.ImagePermission:group']),
            ('everybody', orm['image_filer.ImagePermission:everybody']),
            ('can_edit', orm['image_filer.ImagePermission:can_edit']),
            ('can_read', orm['image_filer.ImagePermission:can_read']),
            ('can_add_children', orm['image_filer.ImagePermission:can_add_children']),
        ))
        db.send_create_signal('image_filer', ['ImagePermission'])
        
        # Creating unique_together for [template, order] on ImageManipulationStep.
        db.create_unique('image_filer_imagemanipulationstep', ['template_id', 'order'])
        
        # Creating unique_together for [parent, name] on Folder.
        db.create_unique('image_filer_folder', ['parent_id', 'name'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [parent, name] on Folder.
        db.delete_unique('image_filer_folder', ['parent_id', 'name'])
        
        # Deleting unique_together for [template, order] on ImageManipulationStep.
        db.delete_unique('image_filer_imagemanipulationstep', ['template_id', 'order'])
        
        # Deleting model 'Folder'
        db.delete_table('image_filer_folder')
        
        # Deleting model 'FolderPermission'
        db.delete_table('image_filer_folderpermission')
        
        # Deleting model 'ImageManipulationProfile'
        db.delete_table('image_filer_imagemanipulationprofile')
        
        # Deleting model 'Bucket'
        db.delete_table('image_filer_bucket')
        
        # Deleting model 'BucketItem'
        db.delete_table('image_filer_bucketitem')
        
        # Deleting model 'ImageManipulationStep'
        db.delete_table('image_filer_imagemanipulationstep')
        
        # Deleting model 'Image'
        db.delete_table('image_filer_image')
        
        # Deleting model 'ImageManipulationTemplate'
        db.delete_table('image_filer_imagemanipulationtemplate')
        
        # Deleting model 'ImagePermission'
        db.delete_table('image_filer_imagepermission')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'image_filer.bucket': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'buckets'", 'to': "orm['auth.User']"})
        },
        'image_filer.bucketitem': {
            'bucket': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Bucket']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'image_filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'image_filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'image_filer.image': {
            '_height_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'can_use_for_print': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_private_use': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_research': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_teaching': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_web': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contact_of_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'image_files'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'manipulation_profile': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'images'", 'null': 'True', 'to': "orm['image_filer.ImageManipulationProfile']"}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Image']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'usage_restriction_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagemanipulationprofile': {
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'show_in_library': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'image_filer.imagemanipulationstep': {
            'Meta': {'unique_together': "(('template', 'order'),)"},
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'filter_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'steps'", 'to': "orm['image_filer.ImageManipulationProfile']"})
        },
        'image_filer.imagemanipulationtemplate': {
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'pre_cache': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'templates'", 'to': "orm['image_filer.ImageManipulationProfile']"})
        },
        'image_filer.imagepermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['image_filer']

########NEW FILE########
__FILENAME__ = 0002_extend_image_publication_with_size

from south.db import db
from django.db import models
from image_filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'ImagePublication'
        db.create_table('cmsplugin_filer', (
            ('cmsplugin_ptr', orm['image_filer.imagepublication:cmsplugin_ptr']),
            ('image', orm['image_filer.imagepublication:image']),
            ('alt_text', orm['image_filer.imagepublication:alt_text']),
            ('caption', orm['image_filer.imagepublication:caption']),
            ('width', orm['image_filer.imagepublication:width']),
            ('height', orm['image_filer.imagepublication:height']),
            ('show_author', orm['image_filer.imagepublication:show_author']),
            ('show_copyright', orm['image_filer.imagepublication:show_copyright']),
        ))
        db.send_create_signal('image_filer', ['ImagePublication'])
        
        # Adding model 'ClipboardItem'
        db.create_table('image_filer_clipboarditem', (
            ('id', orm['image_filer.clipboarditem:id']),
            ('file', orm['image_filer.clipboarditem:file']),
            ('clipboard', orm['image_filer.clipboarditem:clipboard']),
            ('is_checked', orm['image_filer.clipboarditem:is_checked']),
        ))
        db.send_create_signal('image_filer', ['ClipboardItem'])
        
        # Adding model 'Clipboard'
        db.create_table('image_filer_clipboard', (
            ('id', orm['image_filer.clipboard:id']),
            ('user', orm['image_filer.clipboard:user']),
        ))
        db.send_create_signal('image_filer', ['Clipboard'])
        
        # Deleting field 'Image.tree_id'
        db.delete_column('image_filer_image', 'tree_id')
        
        # Deleting field 'Image.lft'
        db.delete_column('image_filer_image', 'lft')
        
        # Deleting field 'Image.manipulation_profile'
        db.delete_column('image_filer_image', 'manipulation_profile_id')
        
        # Deleting field 'Image.level'
        db.delete_column('image_filer_image', 'level')
        
        # Deleting field 'Image.parent'
        db.delete_column('image_filer_image', 'parent_id')
        
        # Deleting field 'Image.rght'
        db.delete_column('image_filer_image', 'rght')
        
        # Deleting model 'imagemanipulationtemplate'
        db.delete_table('image_filer_imagemanipulationtemplate')
        
        # Deleting model 'bucket'
        db.delete_table('image_filer_bucket')
        
        # Deleting model 'bucketitem'
        db.delete_table('image_filer_bucketitem')
        
        # Deleting model 'imagemanipulationstep'
        db.delete_table('image_filer_imagemanipulationstep')
        
        # Deleting model 'imagemanipulationprofile'
        db.delete_table('image_filer_imagemanipulationprofile')
        
        # Deleting model 'imagepermission'
        db.delete_table('image_filer_imagepermission')
        
        # Changing field 'FolderPermission.can_read'
        # (to signature: django.db.models.fields.BooleanField(default=True, blank=True))
        db.alter_column('image_filer_folderpermission', 'can_read', orm['image_filer.folderpermission:can_read'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'ImagePublication'
        db.delete_table('cmsplugin_filer')
        
        # Deleting model 'ClipboardItem'
        db.delete_table('image_filer_clipboarditem')
        
        # Deleting model 'Clipboard'
        db.delete_table('image_filer_clipboard')
        
        # Adding field 'Image.tree_id'
        db.add_column('image_filer_image', 'tree_id', orm['image_filer.image:tree_id'])
        
        # Adding field 'Image.lft'
        db.add_column('image_filer_image', 'lft', orm['image_filer.image:lft'])
        
        # Adding field 'Image.manipulation_profile'
        db.add_column('image_filer_image', 'manipulation_profile', orm['image_filer.image:manipulation_profile'])
        
        # Adding field 'Image.level'
        db.add_column('image_filer_image', 'level', orm['image_filer.image:level'])
        
        # Adding field 'Image.parent'
        db.add_column('image_filer_image', 'parent', orm['image_filer.image:parent'])
        
        # Adding field 'Image.rght'
        db.add_column('image_filer_image', 'rght', orm['image_filer.image:rght'])
        
        # Adding model 'imagemanipulationtemplate'
        db.create_table('image_filer_imagemanipulationtemplate', (
            ('profile', orm['image_filer.image:profile']),
            ('description', orm['image_filer.image:description']),
            ('pre_cache', orm['image_filer.image:pre_cache']),
            ('identifier', orm['image_filer.image:identifier']),
            ('id', orm['image_filer.image:id']),
            ('name', orm['image_filer.image:name']),
        ))
        db.send_create_signal('image_filer', ['imagemanipulationtemplate'])
        
        # Adding model 'bucket'
        db.create_table('image_filer_bucket', (
            ('files', orm['image_filer.image:files']),
            ('id', orm['image_filer.image:id']),
            ('user', orm['image_filer.image:user']),
        ))
        db.send_create_signal('image_filer', ['bucket'])
        
        # Adding model 'bucketitem'
        db.create_table('image_filer_bucketitem', (
            ('is_checked', orm['image_filer.image:is_checked']),
            ('bucket', orm['image_filer.image:bucket']),
            ('id', orm['image_filer.image:id']),
            ('file', orm['image_filer.image:file']),
        ))
        db.send_create_signal('image_filer', ['bucketitem'])
        
        # Adding model 'imagemanipulationstep'
        db.create_table('image_filer_imagemanipulationstep', (
            ('description', orm['image_filer.image:description']),
            ('name', orm['image_filer.image:name']),
            ('order', orm['image_filer.image:order']),
            ('data', orm['image_filer.image:data']),
            ('id', orm['image_filer.image:id']),
            ('template', orm['image_filer.image:template']),
            ('filter_identifier', orm['image_filer.image:filter_identifier']),
        ))
        db.send_create_signal('image_filer', ['imagemanipulationstep'])
        
        # Adding model 'imagemanipulationprofile'
        db.create_table('image_filer_imagemanipulationprofile', (
            ('show_in_library', orm['image_filer.image:show_in_library']),
            ('description', orm['image_filer.image:description']),
            ('name', orm['image_filer.image:name']),
            ('id', orm['image_filer.image:id']),
        ))
        db.send_create_signal('image_filer', ['imagemanipulationprofile'])
        
        # Adding model 'imagepermission'
        db.create_table('image_filer_imagepermission', (
            ('can_add_children', orm['image_filer.image:can_add_children']),
            ('can_edit', orm['image_filer.image:can_edit']),
            ('group', orm['image_filer.image:group']),
            ('user', orm['image_filer.image:user']),
            ('can_read', orm['image_filer.image:can_read']),
            ('image', orm['image_filer.image:image']),
            ('type', orm['image_filer.image:type']),
            ('id', orm['image_filer.image:id']),
            ('everybody', orm['image_filer.image:everybody']),
        ))
        db.send_create_signal('image_filer', ['imagepermission'])
        
        # Changing field 'FolderPermission.can_read'
        # (to signature: django.db.models.fields.BooleanField(default=False, blank=True))
        db.alter_column('image_filer_folderpermission', 'can_read', orm['image_filer.folderpermission:can_read'])
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'image_filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'image_filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'image_filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'image_filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'image_filer.image': {
            '_height_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'can_use_for_print': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_private_use': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_research': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_teaching': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_web': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contact_of_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'image_files'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_images'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'usage_restriction_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagepublication': {
            'Meta': {'db_table': "'cmsplugin_filer'"},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'show_author': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['image_filer']

########NEW FILE########
__FILENAME__ = 0003_subject_location_field

from south.db import db
from django.db import models
from image_filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'Image.subject_location'
        db.add_column('image_filer_image', 'subject_location', orm['image_filer.image:subject_location'])
        
        # Changing field 'Image.file'
        # (to signature: django.db.models.fields.files.ImageField(max_length=255, null=True, blank=True))
        db.alter_column('image_filer_image', 'file', orm['image_filer.image:file'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'Image.subject_location'
        db.delete_column('image_filer_image', 'subject_location')
        
        # Changing field 'Image.file'
        # (to signature: django.db.models.fields.files.ImageField(max_length=100, null=True, blank=True))
        db.alter_column('image_filer_image', 'file', orm['image_filer.image:file'])
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'image_filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'image_filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'image_filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'image_filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'image_filer.image': {
            '_height_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'can_use_for_print': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_private_use': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_research': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_teaching': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_web': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contact_of_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'image_files'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_images'", 'null': 'True', 'to': "orm['auth.User']"}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'usage_restriction_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagepublication': {
            'Meta': {'db_table': "'cmsplugin_filer'"},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'show_author': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['image_filer']

########NEW FILE########
__FILENAME__ = 0004_more_like_cms_picture_plugin

from south.db import db
from django.db import models
from image_filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'ImagePublication.longdesc'
        db.add_column('cmsplugin_filer', 'longdesc', orm['image_filer.imagepublication:longdesc'])
        
        # Adding field 'ImagePublication.free_link'
        db.add_column('cmsplugin_filer', 'free_link', orm['image_filer.imagepublication:free_link'])
        
        # Adding field 'ImagePublication.float'
        db.add_column('cmsplugin_filer', 'float', orm['image_filer.imagepublication:float'])
        
        # Adding field 'ImagePublication.page_link'
        db.add_column('cmsplugin_filer', 'page_link', orm['image_filer.imagepublication:page_link'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'ImagePublication.longdesc'
        db.delete_column('cmsplugin_filer', 'longdesc')
        
        # Deleting field 'ImagePublication.free_link'
        db.delete_column('cmsplugin_filer', 'free_link')
        
        # Deleting field 'ImagePublication.float'
        db.delete_column('cmsplugin_filer', 'float')
        
        # Deleting field 'ImagePublication.page_link'
        db.delete_column('cmsplugin_filer', 'page_link_id')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'image_filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'image_filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'image_filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'image_filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'image_filer.image': {
            '_height_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'can_use_for_print': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_private_use': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_research': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_teaching': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_web': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contact_of_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'image_files'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_images'", 'null': 'True', 'to': "orm['auth.User']"}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'usage_restriction_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagepublication': {
            'Meta': {'db_table': "'cmsplugin_filer'"},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'longdesc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'show_author': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['image_filer']

########NEW FILE########
__FILENAME__ = 0005_plugin_table_rename

from south.db import db
from django.db import models
from image_filer.models import *

class Migration:
    no_dry_run = True
    depends_on = (
        ('cms', '0023_plugin_table_naming_function_changed'),
    )
    def forwards(self, orm):
        "Write your forwards migration here"
        db.rename_table('cmsplugin_filer','cmsplugin_imagepublication')
    
    def backwards(self, orm):
        "Write your backwards migration here"
        db.rename_table('cmsplugin_imagepublication','cmsplugin_filer')
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'image_filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'image_filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'image_filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'image_filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'image_filer.image': {
            '_height_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'can_use_for_print': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_private_use': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_research': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_teaching': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_web': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contact_of_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'image_files'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_images'", 'null': 'True', 'to': "orm['auth.User']"}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'usage_restriction_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagepublication': {
            'Meta': {'db_table': "'cmsplugin_imagepublication'"},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'longdesc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'show_author': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['image_filer']

########NEW FILE########
__FILENAME__ = 0006_teaser_plugin

from south.db import db
from django.db import models
from image_filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'ImageFilerTeaser'
        db.create_table('cmsplugin_imagefilerteaser', (
            ('cmsplugin_ptr', orm['image_filer.imagefilerteaser:cmsplugin_ptr']),
            ('title', orm['image_filer.imagefilerteaser:title']),
            ('image', orm['image_filer.imagefilerteaser:image']),
            ('page_link', orm['image_filer.imagefilerteaser:page_link']),
            ('url', orm['image_filer.imagefilerteaser:url']),
            ('description', orm['image_filer.imagefilerteaser:description']),
        ))
        db.send_create_signal('image_filer', ['ImageFilerTeaser'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'ImageFilerTeaser'
        db.delete_table('cmsplugin_imagefilerteaser')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'image_filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'image_filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'image_filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'image_filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'image_filer.image': {
            '_height_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'can_use_for_print': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_private_use': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_research': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_teaching': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_web': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contact_of_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'image_files'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_images'", 'null': 'True', 'to': "orm['auth.User']"}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'usage_restriction_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagefilerteaser': {
            'Meta': {'db_table': "'cmsplugin_imagefilerteaser'"},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']", 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagepublication': {
            'Meta': {'db_table': "'cmsplugin_imagepublication'"},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'longdesc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'show_author': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['image_filer']

########NEW FILE########
__FILENAME__ = 0007_folder_publication_plugin

from south.db import db
from django.db import models
from image_filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'FolderPublication'
        db.create_table('cmsplugin_imagefolder', (
            ('cmsplugin_ptr', orm['image_filer.folderpublication:cmsplugin_ptr']),
            ('folder', orm['image_filer.folderpublication:folder']),
        ))
        db.send_create_signal('image_filer', ['FolderPublication'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'FolderPublication'
        db.delete_table('cmsplugin_imagefolder')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'image_filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'image_filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_checked': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'image_filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'image_filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'image_filer.folderpublication': {
            'Meta': {'db_table': "'cmsplugin_imagefolder'"},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'folder': ('ImageFilerModelFolderField', [], {})
        },
        'image_filer.image': {
            '_height_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width_field': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'can_use_for_print': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_private_use': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_research': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_teaching': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_use_for_web': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contact_of_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'image_files'", 'null': 'True', 'to': "orm['image_filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_images'", 'null': 'True', 'to': "orm['auth.User']"}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'usage_restriction_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagefilerteaser': {
            'Meta': {'db_table': "'cmsplugin_imagefilerteaser'"},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']", 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'image_filer.imagepublication': {
            'Meta': {'db_table': "'cmsplugin_imagepublication'"},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['image_filer.Image']"}),
            'longdesc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'show_author': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['image_filer']

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-

from django.db import models
########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models import Q
from datetime import datetime

class FolderManager(models.Manager):    
    def with_bad_metadata(self):
        return self.get_query_set().filter(has_all_mandatory_data=False)
########NEW FILE########
__FILENAME__ = safe_file_storage
from django.core.files.storage import FileSystemStorage
from django.template.defaultfilters import slugify
import os

class SafeFilenameFileSystemStorage(FileSystemStorage):
    def get_valid_name(self, name):
        """
        Returns a filename, based on the provided filename, that's suitable for
        use in the target storage system. (slugify)
        """
        s = super(SafeFilenameFileSystemStorage, self).get_valid_name(name)
        filename, ext = os.path.splitext(s)
        filename = slugify(filename)
        ext = slugify(ext)
        return u'%s.%s' % (filename, ext)
########NEW FILE########
__FILENAME__ = tools
from image_filer.models import Clipboard

def discard_clipboard(clipboard):
    clipboard.files.clear()

def delete_clipboard(clipboard):
    for file in clipboard.files.all():
        file.delete()

def get_user_clipboard(user):
    if user.is_authenticated():
        clipboard, was_clipboard_created = Clipboard.objects.get_or_create(user=user)
        return clipboard

def move_file_to_clipboard(files, clipboard):
    for file in files:
        clipboard.append_file(file)
        print file.folder
        file.folder = None
        file.save()
    return True

def clone_files_from_clipboard_to_folder(clipboard, folder):
    for file in clipboard.files.all():
        cloned_file = file.clone()
        cloned_file.folder = folder
        cloned_file.save()

def move_files_from_clipboard_to_folder(clipboard, folder):
    return move_files_to_folder(clipboard.files.all(), folder)

def move_files_to_folder(files, folder):
    for file in files:
        #print "moving %s (%s) to %s" % (file, type(file), folder)
        file.folder = folder
        file.save()
    return True
########NEW FILE########
__FILENAME__ = migrate_cms_picture_plugins
from image_filer import models as image_filer_models
from django.utils.encoding import force_unicode
from image_filer.scripts.migrate_utils import get_image_instance_for_path

def migrate_picture_plugin_to_image_filer_publication(plugin_instance):
    if not plugin_instance.plugin_type == 'PicturePlugin':
        return
    from django.db import connection
    cursor = connection.cursor()
    
    instance, plugin = plugin_instance.get_plugin_instance()
    if not instance:
        return
    picture = instance.picture
    attr_map = {
            'cmsplugin_ptr_id'  : str(plugin_instance.id),
            'alt_text'          : u"'%s'" % picture.alt,
            'caption'           : u"'%s'" % picture.longdesc,
            'float'             : u"'%s'" % picture.float,
            'show_author'       : '0',
            'show_copyright'    : '0',
    }
    if picture.page_link_id in ['',None]:
        attr_map['page_link_id'] = 'NULL'
    else:
        attr_map['page_link_id'] = str(picture.page_link_id)
    try:
        image_filer_image = get_image_instance_for_path(force_unicode(picture.image))
        attr_map.update({
            'image_id'          : str(image_filer_image.id),
            'width'             : str(image_filer_image.width),
            'height'            : str(image_filer_image.height),
        })
    except Exception, e:
        print u"missing image! %s" % e
        return
    
    data = {'table_name': image_filer_models.ImagePublication._meta.db_table,
            'keys': ",".join('`%s`'%key for key in attr_map.keys()),
            'values': u",".join(attr_map.values()),
            }
    
    QUERY = '''INSERT INTO %(table_name)s (%(keys)s) VALUES (%(values)s);''' % data
    #print QUERY
    #cursor.execute(QUERY)
    QUERY_UPD = "UPDATE cms_cmsplugin SET plugin_type='ImagePlugin' WHERE id=%s;" % plugin_instance.id
    #print QUERY_UPD
    #cursor.execute(QUERY_UPD)
    QUERY_DEL = 'DELETE FROM cmsplugin_picture WHERE cmsplugin_ptr_id=%s;' % str(plugin_instance.id)
    #print QUERY_DEL
    #cursor.execute(QUERY_DEL)
    cursor.execute(QUERY+QUERY_UPD+QUERY_DEL)

def migrate_all():
    from cms.models import CMSPlugin
    for plugin in CMSPlugin.objects.filter(plugin_type='PicturePlugin'):
        migrate_picture_plugin_to_image_filer_publication(plugin)
########NEW FILE########
__FILENAME__ = migrate_cms_teaser_plugins
from image_filer import models as image_filer_models
from django.utils.encoding import force_unicode
from image_filer.scripts.migrate_utils import get_image_instance_for_path

def migrate_teaser_plugin_to_image_filer_teaser(plugin_instance):
    if not plugin_instance.plugin_type == 'TeaserPlugin':
        return
    from django.db import connection
    cursor = connection.cursor()
    
    instance, plugin = plugin_instance.get_plugin_instance()
    if not instance:
        return
    teaser = instance.teaser
    attr_map = {
            'cmsplugin_ptr_id'  : str(plugin_instance.id),
            'title'             : u"'%s'" % teaser.title,
            'url'               : u"'%s'" % teaser.url,
            'description'       : u"'%s'" % teaser.description,
    }
    if teaser.page_link_id in ['',None]:
        attr_map['page_link_id'] = 'NULL'
    else:
        attr_map['page_link_id'] = str(teaser.page_link_id)
    try:
        image_filer_image = get_image_instance_for_path(force_unicode(teaser.image))
        attr_map.update({
            'image_id'          : str(image_filer_image.id),
            #'width'             : str(image_filer_image.width),
            #'height'            : str(image_filer_image.height),
        })
    except Exception, e:
        print u"missing image! %s" % e
        return
    
    data = {'table_name': image_filer_models.ImageFilerTeaser._meta.db_table,
            'keys': ",".join('`%s`'%key for key in attr_map.keys()),
            'values': u",".join(attr_map.values()),
            }
    #print data
    QUERY = '''INSERT INTO %(table_name)s (%(keys)s) VALUES (%(values)s);''' % data
    #print QUERY
    #cursor.execute(QUERY)
    QUERY_UPD = "UPDATE cms_cmsplugin SET plugin_type='ImageFilerTeaserPlugin' WHERE id=%s;" % plugin_instance.id
    #print QUERY_UPD
    #cursor.execute(QUERY_UPD)
    QUERY_DEL = 'DELETE FROM cmsplugin_picture WHERE cmsplugin_ptr_id=%s;' % str(plugin_instance.id)
    #print QUERY_DEL
    #cursor.execute(QUERY_DEL)
    cursor.execute(QUERY+QUERY_UPD+QUERY_DEL)

def migrate_all():
    from cms.models import CMSPlugin
    for plugin in CMSPlugin.objects.filter(plugin_type='TeaserPlugin'):
        migrate_teaser_plugin_to_image_filer_teaser(plugin)
########NEW FILE########
__FILENAME__ = migrate_utils
from image_filer import models as image_filer_models
from django.utils.encoding import force_unicode

def get_image_instance_for_path(image_path):
    print "  handling %s" % (image_path,)
    relative_file_path = image_path
    # check if this file is already under image_filer control
    image_filer_image, created = image_filer_models.Image.objects.get_or_create(file=relative_file_path)
    print "    image_filer.Image: %s create: %s" % (relative_file_path, created)
    if created:
        # create the missing folders objects if necessary
        crumbs = relative_file_path.split('/')[:-1] # all except the filename
        folders = []
        for crumb in crumbs:
            if len(folders):
                parent = folders[-1]
            else:
                parent = None
            print "      checking for Folder: %s" % crumb
            try:
                newfolder = image_filer_models.Folder.objects.get(name=crumb,parent=parent)
                created = False
            except:
                # this sucks, but we don't have mptt stuff in this context :-(
                newfolder = image_filer_models.Folder(name=crumb,parent=parent)
                created = True
            print "        Folder: %s create: %s" % (newfolder.name, created,)
            if created:
                newfolder.save()
                print u"      added folder %s" % (newfolder,)
            folders.append(newfolder)
        if len(folders):
            folder = folders[-1]
        else:
            folder = None

        # the image was not in image_file before... set the minimal mandatory fields
        image_filer_image.original_filename = relative_file_path.split('/')[-1]
        image_filer_image.folder = folder
        image_filer_image.save()
    return image_filer_image
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
__FILENAME__ = files
import os

from image_filer.utils.zip import unzip

def generic_handle_file(file, original_filename):
    """
    Handels a file, regardless if a package or a single file and returns 
    a list of files. can recursively unpack packages.
    """
    #print "entering generic_handle_file(file=%s, original_filename=%s)" % (file, original_filename)
    files = []
    filetype = os.path.splitext(original_filename)[1].lower()
    #print filetype
    if filetype=='.zip':
        unpacked_files = unzip(file)
        for ufile, ufilename in unpacked_files:
            files += generic_handle_file(ufile, ufilename)
    else:
        files.append( (file,original_filename) )
    #print "result of generic_handle_file: ", files
    return files
########NEW FILE########
__FILENAME__ = pexif
"""
pexif is a module which allows you to view and modify meta-data in
JPEG/JFIF/EXIF files.

The main way to use this is to create an instance of the JpegFile class.
This should be done using one of the static factory methods fromFile,
fromString or fromFd.

After manipulating the object you can then write it out using one of the
writeFile, writeString or writeFd methods.

The get_exif() method on JpegFile returns the ExifSegment if one exists.

Example:

jpeg = pexif.JpegFile.fromFile("foo.jpg")
exif = jpeg.get_exif()
....
jpeg.writeFile("new.jpg")

For photos that don't currently have an exef segment you can specify
an argument which will create the exef segment if it doesn't exist.

Example:

jpeg = pexif.JpegFile.fromFile("foo.jpg")
exif = jpeg.get_exif(create=True)
....
jpeg.writeFile("new.jpg")

The JpegFile class handles file that are formatted in something
approach the JPEG specification (ISO/IEC 10918-1) Annex B 'Compressed
Data Formats', and JFIF and EXIF standard.

In particular, the way a 'jpeg' file is treated by pexif is that
a JPEG file is made of a series of segments followed by the image
data. In particular it should look something like:

[ SOI | <arbitrary segments> | SOS | image data | EOI ]

So, the library expects a Start-of-Image marker, followed
by an arbitrary number of segment (assuming that a segment
has the format:

[ <0xFF> <segment-id> <size-byte0> <size-byte1> <data> ]

and that there are no gaps between segments.

The last segment must be the Start-of-Scan header, and the library
assumes that following Start-of-Scan comes the image data, finally
followed by the End-of-Image marker.

This is probably not sufficient to handle arbitrary files conforming
to the JPEG specs, but it should handle files that conform to
JFIF or EXIF, as well as files that conform to neither but
have both JFIF and EXIF application segment (which is the majority
of files in existence!). 

When writing out files all segment will be written out in the order
in which they were read. Any 'unknown' segment will be written out
as is. Note: This may or may not corrupt the data. If the segment
format relies on absolute references then this library may still
corrupt that segment!


Can have a JpegFile in two modes: Read Only and Read Write.

Read Only mode: trying to access missing elements will result in
an AttributeError.

Read Write mode: trying to access missing elements will automatically
create them.

E.g: 

img.exif.primary.<tagname>
             .geo
             .interop
             .exif.<tagname>
             .exif.makernote.<tagname>
               
        .thumbnail
img.flashpix.<...>
img.jfif.<tagname>
img.xmp

E.g: 

try:
 print img.exif.tiff.exif.FocalLength
except AttributeError:
 print "No Focal Length data"

"""

import StringIO
import sys
from struct import unpack, pack

MAX_HEADER_SIZE = 64 * 1024
DELIM = 0xff
EOI = 0xd9
SOI_MARKER = chr(DELIM) + '\xd8'
EOI_MARKER = chr(DELIM) + '\xd9'

EXIF_OFFSET = 0x8769
GPSIFD = 0x8825

TIFF_OFFSET = 6
TIFF_TAG = 0x2a

DEBUG = 0

def debug(*debug_string):
    """Used for print style debugging. Enable by setting the global
    DEBUG to 1."""
    if DEBUG:
        for each in debug_string:
            print each,
        print

class DefaultSegment:
    """DefaultSegment represents a particluar segment of a JPEG file.
    This class is instantiated by JpegFile when parsing Jpeg files
    and is not intended to be used directly by the programmer. This
    base class is used as a default which doesn't know about the internal
    structure of the segment. Other classes subclass this to provide
    extra information about a particular segment.
    """
    
    def __init__(self, marker, fd, data, mode):
        """The constructor for DefaultSegment takes the marker which
        identifies the segments, a file object which is currently positioned
        at the end of the segment. This allows any subclasses to potentially
        extract extra data from the stream. Data contains the contents of the
        segment."""
        self.marker = marker
        self.data = data
        self.mode = mode
        self.fd = fd
        assert mode in ["rw", "ro"]
        if not self.data is None:
            self.parse_data(data)

    class InvalidSegment(Exception):
        """This exception may be raised by sub-classes in cases when they
        can't correctly identify the segment."""
        pass

    def write(self, fd):
        """This method is called by JpegFile when writing out the file. It
        must write out any data in the segment. This shouldn't in general be
        overloaded by subclasses, they should instead override the get_data()
        method."""
        fd.write('\xff')
        fd.write(pack('B', self.marker))
        data = self.get_data()
        fd.write(pack('>H', len(data) + 2))
        fd.write(data)

    def get_data(self):
        """This method is called by write to generate the data for this segment.
        It should be overloaded by subclasses."""
        return self.data

    def parse_data(self, data):
        """This method is called be init to parse any data for the segment. It
        should be overloaded by subclasses rather than overloading __init__"""
        pass

    def dump(self, fd):
        """This is called by JpegFile.dump() to output a human readable
        representation of the segment. Subclasses should overload this to provide
        extra information."""
        print >> fd, " Section: [%5s] Size: %6d" % \
              (jpeg_markers[self.marker][0], len(self.data))

class StartOfScanSegment(DefaultSegment):
    """The StartOfScan segment needs to be treated specially as the actual
    image data directly follows this segment, and that data is not included
    in the size as reported in the segment header. This instances of this class
    are created by JpegFile and it should not be subclassed.
    """
    def __init__(self, marker, fd, data, mode):
        DefaultSegment.__init__(self, marker, fd, data, mode)

        # For SOS we also pull out the actual data
        img_data = fd.read()
        # -2 accounts for the EOI marker at the end of the file
        self.img_data = img_data[:-2]
        fd.seek(-2, 1)

    def write(self, fd):
        """Write segment data to a given file object"""
        DefaultSegment.write(self, fd)
        fd.write(self.img_data)

    def dump(self, fd):
        """Dump as ascii readable data to a given file object"""
        print >> fd, " Section: [  SOS] Size: %6d Image data size: %6d" % \
              (len(self.data), len(self.img_data))

class ExifType:
    """The ExifType class encapsulates the data types used
    in the Exif spec. These should really be called TIFF types
    probably. This could be replaced by named tuples in python 2.6."""
    lookup = {}

    def __init__(self, type_id, name, size):
        """Create an ExifType with a given name, size and type_id"""
        self.id = type_id
        self.name = name
        self.size = size
        ExifType.lookup[type_id] = self

BYTE = ExifType(1, "byte", 1).id
ASCII = ExifType(2, "ascii", 1).id
SHORT = ExifType(3, "short", 2).id
LONG = ExifType(4, "long", 4).id
RATIONAL = ExifType(5, "rational", 8).id
UNDEFINED = ExifType(7, "undefined", 1).id
SLONG = ExifType(9, "slong", 4).id
SRATIONAL = ExifType(10, "srational", 8).id

def exif_type_size(exif_type):
    """Return the size of a type"""
    return ExifType.lookup.get(exif_type).size

class Rational:
    """A simple fraction class. Python 2.6 could use the inbuilt Fraction class."""

    def __init__(self, num, den):
        """Create a number fraction num/den."""
        self.num = num
        self.den = den

    def __repr__(self):
        """Return a string representation of the fraction."""
        return "%s / %s" % (self.num, self.den)

    def as_tuple(self):
        """Return the fraction a numerator, denominator tuple."""
        return (self.num, self.den)

class IfdData:
    """Base class for IFD"""
    
    name = "Generic Ifd"
    tags = {}
    embedded_tags = {}

    def special_handler(self, tag, data):
        """special_handler method can be over-ridden by subclasses
        to specially handle the conversion of tags from raw format
        into Python data types."""
        pass

    def ifd_handler(self, data):
        """ifd_handler method can be over-ridden by subclasses to
        specially handle conversion of the Ifd as a whole into a
        suitable python representation."""
        pass

    def extra_ifd_data(self, offset):
        """extra_ifd_data method can be over-ridden by subclasses
        to specially handle conversion of the Python Ifd representation
        back into a byte stream."""
        return ""


    def has_key(self, key):
        return self[key] != None

    def __setattr__(self, name, value):
        for key, entry in self.tags.items():
            if entry[1] == name:
                self[key] = value
        self.__dict__[name] = value

    def __delattr__(self, name):
        for key, entry in self.tags.items():
            if entry[1] == name:
                del self[key]
        del self.__dict__[name]

    def __getattr__(self, name):
        for key, entry in self.tags.items():
            if entry[1] == name:
                x = self[key]
                if x is None:
                    raise AttributeError
                return x
        for key, entry in self.embedded_tags.items():
            if entry[0] == name:
                if self.has_key(key):
                    return self[key]
                else:
                    if self.mode == "rw":
                        new = entry[1](self.e, 0, "rw", self.exif_file)
                        self[key] = new
                        return new
                    else:
                        raise AttributeError
        raise AttributeError, "%s not found.. %s" % (name, self.embedded_tags)

    def __getitem__(self, key):
        if type(key) == type(""):
            try:
                return self.__getattr__(key)
            except AttributeError:
                return None
        for entry in self.entries:
            if key == entry[0]:
                if entry[1] == ASCII and not entry[2] is None:
                    return entry[2].strip('\0')
                else:
                    return entry[2]
        return None

    def __delitem__(self, key):
        if type(key) == type(""):
            try:
                return self.__delattr__(key)
            except AttributeError:
                return None
        for entry in self.entries:
            if key == entry[0]:
                self.entries.remove(entry)

    def __setitem__(self, key, value):
        if type(key) == type(""):
            return self.__setattr__(key, value)
        found = 0
        if len(self.tags[key]) < 3:
            raise Exception("Error: Tags aren't set up correctly, should have tag type.")
        if self.tags[key][2] == ASCII:
            if not value is None and not value.endswith('\0'):
                value = value + '\0'
        for i in range(len(self.entries)):
            if key == self.entries[i][0]:
                found = 1
                entry = list(self.entries[i])
                if value is None:
                    del self.entries[i]
                else:
                    entry[2] = value
                    self.entries[i] = tuple(entry)
                break
        if not found:
            # Find type...
            # Not quite enough yet...
            self.entries.append((key, self.tags[key][2], value))
        return

    def __init__(self, e, offset, exif_file, mode, data = None):
        self.exif_file = exif_file
        self.mode = mode
        self.e = e
        self.entries = []
        if data is None:
            return
        num_entries = unpack(e + 'H', data[offset:offset+2])[0]
        next = unpack(e + "I", data[offset+2+12*num_entries:
                                    offset+2+12*num_entries+4])[0]
        debug("OFFSET %s - %s" % (offset, next))
        
        for i in range(num_entries):
            start = (i * 12) + 2 + offset
            debug("START: ", start)
            entry = unpack(e + "HHII", data[start:start+12])
            tag, exif_type, components, the_data = entry

            debug("%s %s %s %s %s" % (hex(tag), exif_type,
                                      exif_type_size(exif_type), components,
                                      the_data))
            byte_size = exif_type_size(exif_type) * components


            if tag in self.embedded_tags:
                actual_data = self.embedded_tags[tag][1](e, the_data,
                                                         exif_file, self.mode, data)
            else:
                if byte_size > 4:
                    debug(" ...offset %s" % the_data)
                    the_data = data[the_data:the_data+byte_size]
                else:
                    the_data = data[start+8:start+8+byte_size]

                if exif_type == BYTE or exif_type == UNDEFINED:
                    actual_data = list(the_data)
                elif exif_type == ASCII:
                    if the_data[-1] != '\0':
                        actual_data = the_data + '\0'
                        #raise JpegFile.InvalidFile("ASCII tag '%s' not 
                        # NULL-terminated: %s [%s]" % (self.tags.get(tag, 
                        # (hex(tag), 0))[0], the_data, map(ord, the_data)))
                        #print "ASCII tag '%s' not NULL-terminated: 
                        # %s [%s]" % (self.tags.get(tag, (hex(tag), 0))[0], 
                        # the_data, map(ord, the_data))
                    actual_data = the_data
                elif exif_type == SHORT:
                    actual_data = list(unpack(e + ("H" * components), the_data))
                elif exif_type == LONG:
                    actual_data = list(unpack(e + ("I" * components), the_data))
                elif exif_type == SLONG:
                    actual_data = list(unpack(e + ("i" * components), the_data))
                elif exif_type == RATIONAL or exif_type == SRATIONAL:
                    if exif_type == RATIONAL: t = "II"
                    else: t = "ii"
                    actual_data = []
                    for i in range(components):
                        actual_data.append(Rational(*unpack(e + t,
                                                            the_data[i*8:
                                                                     i*8+8])))
                else:
                    raise "Can't handle this"

                if (byte_size > 4):
                    debug("%s" % actual_data)

                self.special_handler(tag, actual_data)
            entry = (tag, exif_type, actual_data)
            self.entries.append(entry)

            debug("%-40s %-10s %6d %s" % (self.tags.get(tag, (hex(tag), 0))[0],
                                          ExifType.lookup[exif_type],
                                          components, actual_data))
        self.ifd_handler(data)

    def isifd(self, other):
        """Return true if other is an IFD"""
        return issubclass(other.__class__, IfdData)

    def getdata(self, e, offset, last = 0):
        data_offset = offset+2+len(self.entries)*12+4
        output_data = ""

        out_entries = []

        # Add any specifc data for the particular type
        extra_data = self.extra_ifd_data(data_offset)
        data_offset += len(extra_data)
        output_data += extra_data

        for tag, exif_type, the_data in self.entries:
            magic_type = exif_type
            if (self.isifd(the_data)):
                debug("-> Magic..")
                sub_data, next_offset = the_data.getdata(e, data_offset, 1)
                the_data = [data_offset]
                debug("<- Magic", next_offset, data_offset, len(sub_data),
                      data_offset + len(sub_data))
                data_offset += len(sub_data)
                assert(next_offset == data_offset)
                output_data += sub_data
                magic_type = exif_type
                if exif_type != 4:
                    magic_components = len(sub_data)
                else:
                    magic_components = 1
                exif_type = 4 # LONG
                byte_size = 4
                components = 1
            else:
                magic_components = components = len(the_data)
                byte_size = exif_type_size(exif_type) * components
            
            if exif_type == BYTE or exif_type == UNDEFINED:
                actual_data = "".join(the_data)
            elif exif_type == ASCII:
                actual_data = the_data 
            elif exif_type == SHORT:
                actual_data = pack(e + ("H" * components), *the_data)
            elif exif_type == LONG:
                actual_data = pack(e + ("I" * components), *the_data)
            elif exif_type == SLONG:
                actual_data = pack(e + ("i" * components), *the_data)
            elif exif_type == RATIONAL or exif_type == SRATIONAL:
                if exif_type == RATIONAL: t = "II"
                else: t = "ii"
                actual_data = ""
                for i in range(components):
                    actual_data += pack(e + t, *the_data[i].as_tuple())
            else:
                raise "Can't handle this", exif_type
            if (byte_size) > 4:
                output_data += actual_data
                actual_data = pack(e + "I", data_offset) 
                data_offset += byte_size
            else:
                actual_data = actual_data + '\0' * (4 - len(actual_data))
            out_entries.append((tag, magic_type,
                                magic_components, actual_data))

        data = pack(e + 'H', len(self.entries))
        for entry in out_entries:
            data += pack(self.e + "HHI", *entry[:3])
            data += entry[3]

        next_offset = data_offset
        if last:
            data += pack(self.e + "I", 0)
        else:
            data += pack(self.e + "I", next_offset)
        data += output_data

        assert (next_offset == offset+len(data))

        return data, next_offset

    def dump(self, f, indent = ""):
        """Dump the IFD file"""
        print >> f, indent + "<--- %s start --->" % self.name
        for entry in self.entries:
            tag, exif_type, data = entry
            if exif_type == ASCII:
                data = data.strip('\0')
            if (self.isifd(data)):
                data.dump(f, indent + "    ")
            else:
                if data and len(data) == 1:
                    data = data[0]
                print >> f, indent + "  %-40s %s" % \
                      (self.tags.get(tag, (hex(tag), 0))[0], data)
        print >> f, indent + "<--- %s end --->" % self.name

class IfdInterop(IfdData):
    name = "Interop"
    tags = {
        # Interop stuff
        0x0001: ("Interoperability index", "InteroperabilityIndex"),
        0x0002: ("Interoperability version", "InteroperabilityVersion"),
        0x1000: ("Related image file format", "RelatedImageFileFormat"),
        0x1001: ("Related image file width", "RelatedImageFileWidth"),
        0x1002: ("Related image file length", "RelatedImageFileLength"),
        }

class CanonIFD(IfdData):
    tags = {
        0x0006: ("Image Type", "ImageType"),
        0x0007: ("Firmware Revision", "FirmwareRevision"),
        0x0008: ("Image Number", "ImageNumber"),
        0x0009: ("Owner Name", "OwnerName"),
        0x000c: ("Camera serial number", "SerialNumber"),
        0x000f: ("Customer functions", "CustomerFunctions")
        }
    name = "Canon"


class FujiIFD(IfdData):
    tags = {
        0x0000: ("Note version", "NoteVersion"),
        0x1000: ("Quality", "Quality"),
        0x1001: ("Sharpness", "Sharpness"),
        0x1002: ("White balance", "WhiteBalance"),
        0x1003: ("Color", "Color"),
        0x1004: ("Tone", "Tone"),
        0x1010: ("Flash mode", "FlashMode"),
        0x1011: ("Flash strength", "FlashStrength"),
        0x1020: ("Macro", "Macro"),
        0x1021: ("Focus mode", "FocusMode"),
        0x1030: ("Slow sync", "SlowSync"),
        0x1031: ("Picture mode", "PictureMode"),
        0x1100: ("Motor or bracket", "MotorOrBracket"),
        0x1101: ("Sequence number", "SequenceNumber"),
        0x1210: ("FinePix Color", "FinePixColor"),
        0x1300: ("Blur warning", "BlurWarning"),
        0x1301: ("Focus warning", "FocusWarning"),
        0x1302: ("AE warning", "AEWarning")
        }
    name = "FujiFilm"

    def getdata(self, e, offset, last = 0):
        pre_data = "FUJIFILM"
        pre_data += pack("<I", 12)
        data, next_offset = IfdData.getdata(self, e, 12, last)
        return pre_data + data, next_offset + offset


def ifd_maker_note(e, offset, exif_file, mode, data):
    """Factory function for creating MakeNote entries"""
    if exif_file.make == "Canon":
        # Canon maker note appears to always be in Little-Endian
        return CanonIFD('<', offset, exif_file, mode, data)
    elif exif_file.make == "FUJIFILM":
        # The FujiFILM maker note is special.
        # See http://www.ozhiker.com/electronics/pjmt/jpeg_info/fujifilm_mn.html

        # First it has an extra header
        header = data[offset:offset+8]
        # Which should be FUJIFILM
        if header != "FUJIFILM":
            raise JpegFile.InvalidFile("This is FujiFilm JPEG. " \
                                       "Expecting a makernote header "\
                                       "<FUJIFILM>. Got <%s>." % header)
        # The it has its own offset
        ifd_offset = unpack("<I", data[offset+8:offset+12])[0]
        # and it is always litte-endian
        e = "<"
        # and the data is referenced from the start the Ifd data, not the
        # TIFF file.
        ifd_data = data[offset:]
        return FujiIFD(e, ifd_offset, exif_file, mode, ifd_data)
    else:
        raise JpegFile.InvalidFile("Unknown maker: %s. Can't "\
                                   "currently handle this." % exif_file.make)
        

class IfdGPS(IfdData):
    name = "GPS"
    tags = {
        0x0: ("GPS tag version", "GPSVersionID", BYTE, 4),
        0x1: ("North or South Latitude", "GPSLatitudeRef", ASCII, 2),
        0x2: ("Latitude", "GPSLatitude", RATIONAL, 3),
        0x3: ("East or West Longitude", "GPSLongitudeRef", ASCII, 2),
        0x4: ("Longitude", "GPSLongitude", RATIONAL, 3),
        0x5: ("Altitude reference", "GPSAltitudeRef", BYTE, 1),
        0x6: ("Altitude", "GPSAltitude", RATIONAL, 1)
        }

    def __init__(self, e, offset, exif_file, mode, data = None):
        IfdData.__init__(self, e, offset, exif_file, mode, data)
        if data is None:
            self.GPSVersionID = ['\x02', '\x02', '\x00', '\x00']

class IfdExtendedEXIF(IfdData):
    tags = {
        # Exif IFD Attributes
        # A. Tags relating to version
        0x9000: ("Exif Version", "ExifVersion"),
        0xA000: ("Supported Flashpix version", "FlashpixVersion"),
        # B. Tag relating to Image Data Characteristics
        0xA001: ("Color Space Information", "ColorSpace"),
        # C. Tags relating to Image Configuration
        0x9101: ("Meaning of each component", "ComponentConfiguration"),
        0x9102: ("Image compression mode", "CompressedBitsPerPixel"),
        0xA002: ("Valid image width", "PixelXDimension"),
        0xA003: ("Valid image height", "PixelYDimension"),
        # D. Tags relatin to User informatio
        0x927c: ("Manufacturer notes", "MakerNote"),
        0x9286: ("User comments", "UserComment"),
        # E. Tag relating to related file information
        0xA004: ("Related audio file", "RelatedSoundFile"),
        # F. Tags relating to date and time
        0x9003: ("Date of original data generation", "DateTimeOriginal", ASCII),
        0x9004: ("Date of digital data generation", "DateTimeDigitized", ASCII),
        0x9290: ("DateTime subseconds", "SubSecTime"),
        0x9291: ("DateTime original subseconds", "SubSecTimeOriginal"),
        0x9292: ("DateTime digitized subseconds", "SubSecTimeDigitized"),
        # G. Tags relating to Picture taking conditions
        0x829a: ("Exposure Time", "ExposureTime"),
        0x829d: ("F Number", "FNumber"),
        0x8822: ("Exposure Program", "ExposureProgram"),    
        0x8824: ("Spectral Sensitivity", "SpectralSensitivity"),
        0x8827: ("ISO Speed Rating", "ISOSpeedRatings"),
        0x8829: ("Optoelectric conversion factor", "OECF"),
        0x9201: ("Shutter speed", "ShutterSpeedValue"),
        0x9202: ("Aperture", "ApertureValue"),
        0x9203: ("Brightness", "BrightnessValue"),
        0x9204: ("Exposure bias", "ExposureBiasValue"),
        0x9205: ("Maximum lens apeture", "MaxApertureValue"),
        0x9206: ("Subject Distance", "SubjectDistance"),
        0x9207: ("Metering mode", "MeteringMode"),
        0x9208: ("Light mode", "LightSource"),
        0x9209: ("Flash", "Flash"),
        0x920a: ("Lens focal length", "FocalLength"),
        0x9214: ("Subject area", "Subject area"),
        0xa20b: ("Flash energy", "FlashEnergy"),
        0xa20c: ("Spatial frequency results", "SpatialFrquencyResponse"),
        0xa20e: ("Focal plane X resolution", "FocalPlaneXResolution"),
        0xa20f: ("Focal plane Y resolution", "FocalPlaneYResolution"),
        0xa210: ("Focal plane resolution unit", "FocalPlaneResolutionUnit"),
        0xa214: ("Subject location", "SubjectLocation",SHORT),
        0xa215: ("Exposure index", "ExposureIndex"),
        0xa217: ("Sensing method", "SensingMethod"),
        0xa300: ("File source", "FileSource"),
        0xa301: ("Scene type", "SceneType"),
        0xa302: ("CFA pattern", "CFAPattern"),
        0xa401: ("Customer image processing", "CustomerRendered"),
        0xa402: ("Exposure mode", "ExposureMode"),
        0xa403: ("White balance", "WhiteBalance"),
        0xa404: ("Digital zoom ratio", "DigitalZoomRation"),
        0xa405: ("Focal length in 35mm film", "FocalLengthIn35mmFilm"),
        0xa406: ("Scene capture type", "SceneCaptureType"),
        0xa407: ("Gain control", "GainControl"),
        0xa40a: ("Sharpness", "Sharpness"),
        0xa40c: ("Subject distance range", "SubjectDistanceRange"),
        
        # H. Other tags
        0xa420: ("Unique image ID", "ImageUniqueID"),
        }
    embedded_tags = {
        0x927c: ("MakerNote", ifd_maker_note),
        }
    name = "Extended EXIF"

class IfdTIFF(IfdData):
    """
    """

    tags = {
        # Private Tags
        0x8769: ("Exif IFD Pointer", "ExifOffset", LONG), 
        0xA005: ("Interoparability IFD Pointer", "InteroparabilityIFD", LONG),
        0x8825: ("GPS Info IFD Pointer", "GPSIFD", LONG),
        # TIFF stuff used by EXIF

        # A. Tags relating to image data structure
        0x100: ("Image width", "ImageWidth", LONG),
        0x101: ("Image height", "ImageHeight", LONG),
        0x102: ("Number of bits per component", "BitsPerSample", SHORT),
        0x103: ("Compression Scheme", "Compression", SHORT),
        0x106: ("Pixel Composition", "PhotometricInterpretion", SHORT),
        0x112: ("Orientation of image", "Orientation", SHORT),
        0x115: ("Number of components", "SamplesPerPixel", SHORT),
        0x11c: ("Image data arrangement", "PlanarConfiguration", SHORT),
        0x212: ("Subsampling ration of Y to C", "YCbCrSubsampling", SHORT),
        0x213: ("Y and C positioning", "YCbCrCoefficients", SHORT),
        0x11a: ("X Resolution", "XResolution", RATIONAL),
        0x11b: ("Y Resolution", "YResolution", RATIONAL),
        0x128: ("Unit of X and Y resolution", "ResolutionUnit", SHORT),

        # B. Tags relating to recording offset
        0x111: ("Image data location", "StripOffsets", LONG),
        0x116: ("Number of rows per strip", "RowsPerStrip", LONG),
        0x117: ("Bytes per compressed strip", "StripByteCounts", LONG),
        0x201: ("Offset to JPEG SOI", "JPEGInterchangeFormat", LONG),
        0x202: ("Bytes of JPEG data", "JPEGInterchangeFormatLength", LONG),

        # C. Tags relating to image data characteristics

        # D. Other tags
        0x132: ("File change data and time", "DateTime", ASCII),
        0x10e: ("Image title", "ImageDescription", ASCII),
        0x10f: ("Camera Make", "Make", ASCII),
        0x110: ("Camera Model", "Model", ASCII),
        0x131: ("Camera Software", "Software", ASCII),
        0x13B: ("Artist", "Artist", ASCII),
        0x8298: ("Copyright holder", "Copyright", ASCII),
    }
    
    embedded_tags = {
        0xA005: ("Interoperability", IfdInterop), 
        EXIF_OFFSET: ("ExtendedEXIF", IfdExtendedEXIF),
        0x8825: ("GPS", IfdGPS),
        }

    name = "TIFF Ifd"

    def special_handler(self, tag, data):
        try:
            if self.tags[tag][1] == "Make":
                self.exif_file.make = data.strip('\0')
        except KeyError, e:
            pass

    def new_gps(self):
        if self.has_key(GPSIFD):
            raise ValueError, "Already have a GPS Ifd" 
        assert self.mode == "rw"
        gps = IfdGPS(self.e, 0, self.mode, self.exif_file)
        self[GPSIFD] = gps
        return gps

class IfdThumbnail(IfdTIFF):
    name = "Thumbnail"

    def ifd_handler(self, data):
        size = None
        offset = None
        for (tag, exif_type, val) in self.entries:
            if (tag == 0x201):
                offset = val[0]
            if (tag == 0x202):
                size = val[0]
        if size is None or offset is None:
            raise JpegFile.InvalidFile("Thumbnail doesn't have an offset "\
                                       "and/or size")
        self.jpeg_data = data[offset:offset+size]
        if len(self.jpeg_data) != size:
            raise JpegFile.InvalidFile("Not enough data for JPEG thumbnail."\
                                       "Wanted: %d got %d" %
                                       (size, len(self.jpeg_data)))

    def extra_ifd_data(self, offset):
        for i in range(len(self.entries)):
            entry = self.entries[i]
            if entry[0] == 0x201:
                # Print found field and updating
                new_entry = (entry[0], entry[1], [offset])
                self.entries[i] = new_entry
        return self.jpeg_data

class ExifSegment(DefaultSegment):
    """ExifSegment encapsulates the Exif data stored in a JpegFile. An
    ExifSegment contains two Image File Directories (IFDs). One is attribute
    information and the other is a thumbnail. This module doesn't provide
    any useful functions for manipulating the thumbnail, but does provide
    a get_attributes returns an AttributeIfd instances which allows you to
    manipulate the attributes in a Jpeg file."""

    def __init__(self, marker, fd, data, mode):
        self.ifds = []
        self.e = '<'
        self.tiff_endian = 'II'
        DefaultSegment.__init__(self, marker, fd, data, mode)
    
    def parse_data(self, data):
        """Overloads the DefaultSegment method to parse the data of
        this segment. Can raise InvalidFile if we don't get what we expect."""
        exif = unpack("6s", data[:6])[0]
        exif = exif.strip('\0')

        if (exif != "Exif"):
            raise self.InvalidSegment("Bad Exif Marker. Got <%s>, "\
                                       "expecting <Exif>" % exif)

        tiff_data = data[TIFF_OFFSET:]
        data = None # Don't need or want data for now on..
        
        self.tiff_endian = tiff_data[:2]
        if self.tiff_endian == "II":
            self.e = "<"
        elif self.tiff_endian == "MM":
            self.e = ">"
        else:
            raise JpegFile.InvalidFile("Bad TIFF endian header. Got <%s>, "
                                       "expecting <II> or <MM>" % 
                                       self.tiff_endian)

        tiff_tag, tiff_offset = unpack(self.e + 'HI', tiff_data[2:8])

        if (tiff_tag != TIFF_TAG):
            raise JpegFile.InvalidFile("Bad TIFF tag. Got <%x>, expecting "\
                                       "<%x>" % (tiff_tag, TIFF_TAG))

        # Ok, the header parse out OK. Now we parse the IFDs contained in
        # the APP1 header.
        
        # We use this loop, even though we can really only expect and support
        # two IFDs, the Attribute data and the Thumbnail data
        offset = tiff_offset
        count = 0

        while offset:
            count += 1
            num_entries = unpack(self.e + 'H', tiff_data[offset:offset+2])[0]
            start = 2 + offset + (num_entries*12)
            if (count == 1):
                ifd = IfdTIFF(self.e, offset, self, self.mode, tiff_data)
            elif (count == 2):
                ifd = IfdThumbnail(self.e, offset, self, self.mode, tiff_data)
            else:
                raise JpegFile.InvalidFile()
            self.ifds.append(ifd)

            # Get next offset
            offset = unpack(self.e + "I", tiff_data[start:start+4])[0]

    def dump(self, fd):
        print >> fd, " Section: [ EXIF] Size: %6d" % \
              (len(self.data))
        for ifd in self.ifds:
            ifd.dump(fd)

    def get_data(self):
        ifds_data = ""
        next_offset = 8
        for ifd in self.ifds:
            debug("OUT IFD")
            new_data, next_offset = ifd.getdata(self.e, next_offset,
                                                ifd == self.ifds[-1])
            ifds_data += new_data
            
        data = ""
        data += "Exif\0\0"
        data += self.tiff_endian
        data += pack(self.e + "HI", 42, 8)
        data += ifds_data
        
        return data

    def get_primary(self, create=False):
        """Return the attributes image file descriptor. If it doesn't
        exit return None, unless create is True in which case a new
        descriptor is created."""
        if len(self.ifds) > 0:
            return self.ifds[0]
        else:
            if create:
                assert self.mode == "rw"
                new_ifd = IfdTIFF(self.e, None, self, "rw")
                self.ifds.insert(0, new_ifd)
                return new_ifd
            else:
                return None

    def _get_property(self):
        if self.mode == "rw":
            return self.get_primary(True)
        else:
            primary = self.get_primary()
            if primary is None:
                raise AttributeError
            return primary

    primary = property(_get_property)

jpeg_markers = {
    0xc0: ("SOF0", []),
    0xc2: ("SOF2", []),
    0xc4: ("DHT", []),

    0xda: ("SOS", [StartOfScanSegment]),
    0xdb: ("DQT", []),
    0xdd: ("DRI", []),
    
    0xe0: ("APP0", []),
    0xe1: ("APP1", [ExifSegment]),
    0xe2: ("APP2", []),
    0xe3: ("APP3", []),
    0xe4: ("APP4", []),
    0xe5: ("APP5", []),
    0xe6: ("APP6", []),
    0xe7: ("APP7", []),
    0xe8: ("APP8", []),
    0xe9: ("APP9", []),
    0xea: ("APP10", []),
    0xeb: ("APP11", []),
    0xec: ("APP12", []),
    0xed: ("APP13", []),
    0xee: ("APP14", []),
    0xef: ("APP15", []),
    
    0xfe: ("COM", []),
    }

APP1 = 0xe1

class JpegFile:
    """JpegFile object. You should create this using one of the static methods
    fromFile, fromString or fromFd. The JpegFile object allows you to examine and
    modify the contents of the file. To write out the data use one of the methods
    writeFile, writeString or writeFd. To get an ASCII dump of the data in a file
    use the dump method."""
    
    def fromFile(filename, mode="rw"):
        """Return a new JpegFile object from a given filename."""
        return JpegFile(open(filename, "rb"), filename=filename, mode=mode)
    fromFile = staticmethod(fromFile)

    def fromString(str, mode="rw"):
        """Return a new JpegFile object taking data from a string."""
        return JpegFile(StringIO.StringIO(str), "from buffer", mode=mode)
    fromString = staticmethod(fromString)

    def fromFd(fd, mode="rw"):
        """Return a new JpegFile object taking data from a file object."""
        return JpegFile(fd, "fd <>", mode=mode)
    fromFd = staticmethod(fromFd)

    class InvalidFile(Exception):
        """This exception is raised if a given file is not able to be parsed."""
        pass

    class NoSection(Exception):
        """This exception is raised if a section is unable to be found."""
        pass
    
    def __init__(self, input, filename=None, mode="rw"):
        """JpegFile Constructor. input is a file object, and filename
        is a string used to name the file. (filename is used only for
        display functions).  You shouldn't use this function directly,
        but rather call one of the static methods fromFile, fromString
        or fromFd."""
        self.filename = filename
        self.mode = mode
        # input is the file descriptor
        soi_marker = input.read(len(SOI_MARKER))

        # The very first thing should be a start of image marker
        if (soi_marker != SOI_MARKER):
            raise self.InvalidFile("Error reading soi_marker. Got <%s> "\
                                   "should be <%s>" % (soi_marker, SOI_MARKER))

        # Now go through and find all the blocks of data
        segments = []
        while 1:
            head = input.read(2)
            delim, mark  =  unpack(">BB", head)
            if (delim != DELIM):
                raise self.InvalidFile("Error, expecting delmiter. "\
                                       "Got <%s> should be <%s>" %
                                       (delim, DELIM))
            if mark == EOI:
                # Hit end of image marker, game-over!
                break
            head2 = input.read(2)
            size = unpack(">H", head2)[0]
            data = input.read(size-2)
            possible_segment_classes = jpeg_markers[mark][1] + [DefaultSegment]
            # Try and find a valid segment class to handle
            # this data
            for segment_class in possible_segment_classes:
                try:
                    # Note: Segment class may modify the input file 
                    # descriptor. This is expected.
                    attempt = segment_class(mark, input, data, self.mode)
                    segments.append(attempt)
                    break
                except DefaultSegment.InvalidSegment:
                    # It wasn't this one so we try the next type.
                    # DefaultSegment will always work.
                    continue

        self._segments = segments

    def writeString(self):
        """Write the JpegFile out to a string. Returns a string."""
        f = StringIO.StringIO()
        self.writeFd(f)
        return f.getvalue()

    def writeFile(self, filename):
        """Write the JpegFile out to a file named filename."""
        output = open(filename, "wb")
        self.writeFd(output)

    def writeFd(self, output):
        """Write the JpegFile out on the file object output."""
        output.write(SOI_MARKER)
        for segment in self._segments:
            segment.write(output)
        output.write(EOI_MARKER)

    def dump(self, f = sys.stdout):
        """Write out ASCII representation of the file on a given file
        object. Output default to stdout."""
        print >> f, "<Dump of JPEG %s>" % self.filename
        for segment in self._segments:
            segment.dump(f)

    def get_exif(self, create=False):
        """get_exif returns a ExifSegment if one exists for this file.
        If the file does not have an exif segment and the create is
        false, then return None. If create is true, a new exif segment is
        added to the file and returned."""
        for segment in self._segments:
            if segment.__class__ == ExifSegment:
                return segment
        if create:
            return self.add_exif()
        else:
            return None

    def add_exif(self):
        """add_exif adds a new ExifSegment to a file, and returns
        it. When adding an EXIF segment is will add it at the start of
        the list of segments."""
        assert self.mode == "rw"
        new_segment = ExifSegment(APP1, None, None, "rw")
        self._segments.insert(0, new_segment)
        return new_segment


    def _get_exif(self):
        """Exif Attribute property"""
        if self.mode == "rw":
            return self.get_exif(True)
        else:
            exif = self.get_exif(False)
            if exif is None:
                raise AttributeError
            return exif

    exif = property(_get_exif)

    def get_geo(self):
        """Return a tuple of (latitude, longitude)."""
        def convert(x):
            (deg, min, sec) = x
            return (float(deg.num) / deg.den) +  \
                (1/60.0 * float(min.num) / min.den) + \
                (1/3600.0 * float(sec.num) / sec.den)
        if not self.exif.primary.has_key(GPSIFD):
            raise self.NoSection, "File %s doesn't have a GPS section." % \
                self.filename
            
        gps = self.exif.primary.GPS
        lat = convert(gps.GPSLatitude)
        lng = convert(gps.GPSLongitude)
        if gps.GPSLatitudeRef == "S":
            lat = -lat
        if gps.GPSLongitudeRef == "W":
            lng = -lng

        return lat, lng

    SEC_DEN = 50000000

    def _parse(val):
        sign = 1
        if val < 0:
            val  = -val
            sign = -1
            
        deg = int(val)
        other = (val - deg) * 60
        minutes = int(other)
        secs = (other - minutes) * 60
        secs = long(secs * JpegFile.SEC_DEN)
        return (sign, deg, minutes, secs)

    _parse = staticmethod(_parse)
        
    def set_geo(self, lat, lng):
        """Set the GeoLocation to a given lat and lng"""
        if self.mode != "rw":
            raise RWError

        gps = self.exif.primary.GPS

        sign, deg, min, sec = JpegFile._parse(lat)
        ref = "N"
        if sign < 0:
            ref = "S"

        gps.GPSLatitudeRef = ref
        gps.GPSLatitude = [Rational(deg, 1), Rational(min, 1),
                            Rational(sec, JpegFile.SEC_DEN)]

        sign, deg, min, sec = JpegFile._parse(lng)
        ref = "E"
        if sign < 0:
            ref = "W"
        gps.GPSLongitudeRef = ref
        gps.GPSLongitude = [Rational(deg, 1), Rational(min, 1),
                             Rational(sec, JpegFile.SEC_DEN)]


########NEW FILE########
__FILENAME__ = pil_exif
try:
    import Image
    import ExifTags
except ImportError:
    try:
        from PIL import Image
        from PIL import ExifTags
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
from image_filer.utils import pexif

def get_exif(im):
    try:
        exif_raw = im._getexif() or {}
    except:
        return {}
    ret={}
    for tag, value in exif_raw.items():
        decoded = ExifTags.TAGS.get(tag, tag)
        ret[decoded] = value
    return ret
def get_exif_for_file(file):
    im = Image.open(file,'r')
    return get_exif(im)
def get_subject_location(exif_data):
    try:
        r = ( int(exif_data['SubjectLocation'][0]), int(exif_data['SubjectLocation'][1]), )
    except:
        r = None
    return r

import StringIO
def set_exif_subject_location(xy, fd_source, out_path):
    try:
        img = pexif.JpegFile.fromFd(fd_source)
    except pexif.JpegFile.InvalidFile, e:
        im = Image.open(fd_source)
        #new_file_without_exif = StringIO.StringIO()
        new_file_without_exif = StringIO.StringIO()
        im.save(new_file_without_exif, format="JPEG")
        img = pexif.JpegFile.fromString(new_file_without_exif.getvalue())
        new_file_without_exif.close()
    img.exif.primary.ExtendedEXIF.SubjectLocation = xy
    img.writeFile(out_path)
########NEW FILE########
__FILENAME__ = sorl_filters
try:
    import Image
    import ImageColor
    import ImageFile
    import ImageFilter
    import ImageEnhance
    import ImageDraw
    import ExifTags
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageColor
        from PIL import ImageFile
        from PIL import ImageFilter
        from PIL import ImageEnhance
        from PIL import ImageDraw
        from PIL import ExifTags
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
from image_filer.utils.pil_exif import get_exif, get_subject_location
        
def scale_and_crop(im, requested_size, opts, subject_location=None):
    x, y   = [float(v) for v in im.size]
    xr, yr = [float(v) for v in requested_size]
    
    # we need to extract exif data now, because after the first transition
    # the exif info is lost:
    exif_data = get_exif(im)
    
    if 'crop' in opts or 'max' in opts:
        r = max(xr/x, yr/y)
    else:
        r = min(xr/x, yr/y)
    if r < 1.0 or (r > 1.0 and 'upscale' in opts):
        im = im.resize((int(x*r), int(y*r)), resample=Image.ANTIALIAS)
        
    if 'crop' in opts:
        if not subject_location and exif_data:
            subject_location = get_subject_location(exif_data)
        if not subject_location:
            # default crop implementation
            x, y   = [float(v) for v in im.size]
            ex, ey = (x-min(x, xr))/2, (y-min(y, yr))/2
            if ex or ey:
                im = im.crop((int(ex), int(ey), int(x-ex), int(y-ey)))
        else:
            # subject location aware cropping
            res_x, res_y   = [float(v) for v in im.size]
            subj_x = res_x/(x/float(subject_location[0]))
            subj_y = res_y/(y/float(subject_location[1]))
            ex, ey = (res_x-min(res_x, xr))/2, (res_y-min(res_y, yr))/2
            fx, fy = res_x-ex, res_y-ey
            # get the dimensions of the resulting box
            box_width, box_height = fx - ex, fy - ey
            # try putting the box in the center around the subject point
            # (this will be outside of the image in most cases"
            tex, tey = subj_x-(box_width/2), subj_y-(box_height/2)
            tfx, tfy = subj_x+(box_width/2), subj_y+(box_height/2)
            if tex < 0:
                # its out of the img to the left, move both to the right until tex is 0
                tfx = tfx-tex # tex is negative!)
                tex = 0
            elif tfx > res_x:
                # its out of the img to rhe right
                tex = tex-(tfx-res_x)
                tfx = res_x
            
            if tey < 0:
                # its out of the img to the top, move both to the bottom until tey is 0
                tfy = tfy-tey # tey is negative!)
                tey = 0
            elif tfy > res_y:
                # its out of the img to rhe bottom
                tey = tey-(tfy-res_y)
                tfy = res_y
            if ex or ey:
                crop_box = ((int(tex), int(tey), int(tfx), int(tfy)))
                # draw elipse on focal point for Debugging
                #draw = ImageDraw.Draw(im)
                #esize = 20
                #draw.ellipse( ( (subj_x-esize, subj_y-esize), (subj_x+esize, subj_y+esize)), outline="#FF0000" )
                im = im.crop(crop_box)
    return im
scale_and_crop.valid_options = ('crop', 'upscale', 'max')
########NEW FILE########
__FILENAME__ = zip
import os
#import zipfile
# zipfile.open() is only available in Python 2.6, so we use the future version
from django.core.files.uploadedfile import SimpleUploadedFile
from image_filer.utils import zipfile

def unzip(file):
    """
    Take a path to a zipfile and checks if it is a valid zip file
    and returns...
    """
    files = []
    # TODO: implement try-except here
    zip = zipfile.ZipFile(file)
    bad_file = zip.testzip()
    if bad_file:
        raise Exception('"%s" in the .zip archive is corrupt.' % bad_file)
    infolist = zip.infolist()
    print infolist
    for zipinfo in infolist:
        print "handling %s" % zipinfo.filename
        if zipinfo.filename.startswith('__'): # do not process meta files
            continue
        thefile = SimpleUploadedFile(name=zipinfo.filename, content=zip.read(zipinfo))
        files.append( (thefile, zipinfo.filename) )
    zip.close()
    return files

########NEW FILE########
__FILENAME__ = zipfile
"""
Read and write ZIP files.
"""
# hack so this file that is actually part of python 2.6 works in older versions
from __future__ import with_statement

import struct, os, time, sys, shutil
import binascii, cStringIO, stat

try:
    import zlib # We may need its compression method
    crc32 = zlib.crc32
except ImportError:
    zlib = None
    crc32 = binascii.crc32

__all__ = ["BadZipfile", "error", "ZIP_STORED", "ZIP_DEFLATED", "is_zipfile",
           "ZipInfo", "ZipFile", "PyZipFile", "LargeZipFile" ]

class BadZipfile(Exception):
    pass


class LargeZipFile(Exception):
    """
    Raised when writing a zipfile, the zipfile requires ZIP64 extensions
    and those extensions are disabled.
    """

error = BadZipfile      # The exception raised by this module

ZIP64_LIMIT = (1 << 31) - 1
ZIP_FILECOUNT_LIMIT = 1 << 16
ZIP_MAX_COMMENT = (1 << 16) - 1

# constants for Zip file compression methods
ZIP_STORED = 0
ZIP_DEFLATED = 8
# Other ZIP compression methods not supported

# Below are some formats and associated data for reading/writing headers using
# the struct module.  The names and structures of headers/records are those used
# in the PKWARE description of the ZIP file format:
#     http://www.pkware.com/documents/casestudies/APPNOTE.TXT
# (URL valid as of January 2008)

# The "end of central directory" structure, magic number, size, and indices
# (section V.I in the format document)
structEndArchive = "<4s4H2LH"
stringEndArchive = "PK\005\006"
sizeEndCentDir = struct.calcsize(structEndArchive)

_ECD_SIGNATURE = 0
_ECD_DISK_NUMBER = 1
_ECD_DISK_START = 2
_ECD_ENTRIES_THIS_DISK = 3
_ECD_ENTRIES_TOTAL = 4
_ECD_SIZE = 5
_ECD_OFFSET = 6
_ECD_COMMENT_SIZE = 7
# These last two indices are not part of the structure as defined in the
# spec, but they are used internally by this module as a convenience
_ECD_COMMENT = 8
_ECD_LOCATION = 9

# The "central directory" structure, magic number, size, and indices
# of entries in the structure (section V.F in the format document)
structCentralDir = "<4s4B4HL2L5H2L"
stringCentralDir = "PK\001\002"
sizeCentralDir = struct.calcsize(structCentralDir)

# indexes of entries in the central directory structure
_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_EXTRACT_SYSTEM = 4
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_FILE_ATTRIBUTES = 16
_CD_EXTERNAL_FILE_ATTRIBUTES = 17
_CD_LOCAL_HEADER_OFFSET = 18

# The "local file header" structure, magic number, size, and indices
# (section V.A in the format document)
structFileHeader = "<4s2B4HL2L2H"
stringFileHeader = "PK\003\004"
sizeFileHeader = struct.calcsize(structFileHeader)

_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_EXTRACT_SYSTEM = 2
_FH_GENERAL_PURPOSE_FLAG_BITS = 3
_FH_COMPRESSION_METHOD = 4
_FH_LAST_MOD_TIME = 5
_FH_LAST_MOD_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11

# The "Zip64 end of central directory locator" structure, magic number, and size
structEndArchive64Locator = "<4sLQL"
stringEndArchive64Locator = "PK\x06\x07"
sizeEndCentDir64Locator = struct.calcsize(structEndArchive64Locator)

# The "Zip64 end of central directory" record, magic number, size, and indices
# (section V.G in the format document)
structEndArchive64 = "<4sQ2H2L4Q"
stringEndArchive64 = "PK\x06\x06"
sizeEndCentDir64 = struct.calcsize(structEndArchive64)

_CD64_SIGNATURE = 0
_CD64_DIRECTORY_RECSIZE = 1
_CD64_CREATE_VERSION = 2
_CD64_EXTRACT_VERSION = 3
_CD64_DISK_NUMBER = 4
_CD64_DISK_NUMBER_START = 5
_CD64_NUMBER_ENTRIES_THIS_DISK = 6
_CD64_NUMBER_ENTRIES_TOTAL = 7
_CD64_DIRECTORY_SIZE = 8
_CD64_OFFSET_START_CENTDIR = 9

def _check_zipfile(fp):
    try:
        if _EndRecData(fp):
            return True         # file has correct magic number
    except IOError:
        pass
    return False

def is_zipfile(filename):
    """Quickly see if a file is a ZIP file by checking the magic number.

    The filename argument may be a file or file-like object too.
    """
    result = False
    try:
        if hasattr(filename, "read"):
            result = _check_zipfile(fp=filename)
        else:
            with open(filename, "rb") as fp:
                result = _check_zipfile(fp)
    except IOError:
        pass
    return result

def _EndRecData64(fpin, offset, endrec):
    """
    Read the ZIP64 end-of-archive records and use that to update endrec
    """
    fpin.seek(offset - sizeEndCentDir64Locator, 2)
    data = fpin.read(sizeEndCentDir64Locator)
    sig, diskno, reloff, disks = struct.unpack(structEndArchive64Locator, data)
    if sig != stringEndArchive64Locator:
        return endrec

    if diskno != 0 or disks != 1:
        raise BadZipfile("zipfiles that span multiple disks are not supported")

    # Assume no 'zip64 extensible data'
    fpin.seek(offset - sizeEndCentDir64Locator - sizeEndCentDir64, 2)
    data = fpin.read(sizeEndCentDir64)
    sig, sz, create_version, read_version, disk_num, disk_dir, \
            dircount, dircount2, dirsize, diroffset = \
            struct.unpack(structEndArchive64, data)
    if sig != stringEndArchive64:
        return endrec

    # Update the original endrec using data from the ZIP64 record
    endrec[_ECD_SIGNATURE] = sig
    endrec[_ECD_DISK_NUMBER] = disk_num
    endrec[_ECD_DISK_START] = disk_dir
    endrec[_ECD_ENTRIES_THIS_DISK] = dircount
    endrec[_ECD_ENTRIES_TOTAL] = dircount2
    endrec[_ECD_SIZE] = dirsize
    endrec[_ECD_OFFSET] = diroffset
    return endrec


def _EndRecData(fpin):
    """Return data from the "End of Central Directory" record, or None.

    The data is a list of the nine items in the ZIP "End of central dir"
    record followed by a tenth item, the file seek offset of this record."""

    # Determine file size
    fpin.seek(0, 2)
    filesize = fpin.tell()

    # Check to see if this is ZIP file with no archive comment (the
    # "end of central directory" structure should be the last item in the
    # file if this is the case).
    fpin.seek(-sizeEndCentDir, 2)
    data = fpin.read()
    if data[0:4] == stringEndArchive and data[-2:] == "\000\000":
        # the signature is correct and there's no comment, unpack structure
        endrec = struct.unpack(structEndArchive, data)
        endrec=list(endrec)

        # Append a blank comment and record start offset
        endrec.append("")
        endrec.append(filesize - sizeEndCentDir)

        # Try to read the "Zip64 end of central directory" structure
        return _EndRecData64(fpin, -sizeEndCentDir, endrec)

    # Either this is not a ZIP file, or it is a ZIP file with an archive
    # comment.  Search the end of the file for the "end of central directory"
    # record signature. The comment is the last item in the ZIP file and may be
    # up to 64K long.  It is assumed that the "end of central directory" magic
    # number does not appear in the comment.
    maxCommentStart = max(filesize - (1 << 16) - sizeEndCentDir, 0)
    fpin.seek(maxCommentStart, 0)
    data = fpin.read()
    start = data.rfind(stringEndArchive)
    if start >= 0:
        # found the magic number; attempt to unpack and interpret
        recData = data[start:start+sizeEndCentDir]
        endrec = list(struct.unpack(structEndArchive, recData))
        comment = data[start+sizeEndCentDir:]
        # check that comment length is correct
        if endrec[_ECD_COMMENT_SIZE] == len(comment):
            # Append the archive comment and start offset
            endrec.append(comment)
            endrec.append(maxCommentStart + start)

            # Try to read the "Zip64 end of central directory" structure
            return _EndRecData64(fpin, maxCommentStart + start - filesize,
                                 endrec)

    # Unable to find a valid end of central directory structure
    return


class ZipInfo (object):
    """Class with attributes describing each file in the ZIP archive."""

    __slots__ = (
            'orig_filename',
            'filename',
            'date_time',
            'compress_type',
            'comment',
            'extra',
            'create_system',
            'create_version',
            'extract_version',
            'reserved',
            'flag_bits',
            'volume',
            'internal_attr',
            'external_attr',
            'header_offset',
            'CRC',
            'compress_size',
            'file_size',
            '_raw_time',
        )

    def __init__(self, filename="NoName", date_time=(1980,1,1,0,0,0)):
        self.orig_filename = filename   # Original file name in archive

        # Terminate the file name at the first null byte.  Null bytes in file
        # names are used as tricks by viruses in archives.
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        # This is used to ensure paths in generated ZIP files always use
        # forward slashes as the directory separator, as required by the
        # ZIP format specification.
        if os.sep != "/" and os.sep in filename:
            filename = filename.replace(os.sep, "/")

        self.filename = filename        # Normalized file name
        self.date_time = date_time      # year, month, day, hour, min, sec
        # Standard values:
        self.compress_type = ZIP_STORED # Type of compression for the file
        self.comment = ""               # Comment for each file
        self.extra = ""                 # ZIP extra data
        if sys.platform == 'win32':
            self.create_system = 0          # System which created ZIP archive
        else:
            # Assume everything else is unix-y
            self.create_system = 3          # System which created ZIP archive
        self.create_version = 20        # Version which created ZIP archive
        self.extract_version = 20       # Version needed to extract archive
        self.reserved = 0               # Must be zero
        self.flag_bits = 0              # ZIP flag bits
        self.volume = 0                 # Volume number of file header
        self.internal_attr = 0          # Internal attributes
        self.external_attr = 0          # External file attributes
        # Other attributes are set by class ZipFile:
        # header_offset         Byte offset to the file header
        # CRC                   CRC-32 of the uncompressed file
        # compress_size         Size of the compressed file
        # file_size             Size of the uncompressed file

    def FileHeader(self):
        """Return the per-file header as a string."""
        dt = self.date_time
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
        if self.flag_bits & 0x08:
            # Set these to zero because we write them after the file data
            CRC = compress_size = file_size = 0
        else:
            CRC = self.CRC
            compress_size = self.compress_size
            file_size = self.file_size

        extra = self.extra

        if file_size > ZIP64_LIMIT or compress_size > ZIP64_LIMIT:
            # File is larger than what fits into a 4 byte integer,
            # fall back to the ZIP64 extension
            fmt = '<HHQQ'
            extra = extra + struct.pack(fmt,
                    1, struct.calcsize(fmt)-4, file_size, compress_size)
            file_size = 0xffffffff
            compress_size = 0xffffffff
            self.extract_version = max(45, self.extract_version)
            self.create_version = max(45, self.extract_version)

        filename, flag_bits = self._encodeFilenameFlags()
        header = struct.pack(structFileHeader, stringFileHeader,
                 self.extract_version, self.reserved, flag_bits,
                 self.compress_type, dostime, dosdate, CRC,
                 compress_size, file_size,
                 len(filename), len(extra))
        return header + filename + extra

    def _encodeFilenameFlags(self):
        if isinstance(self.filename, unicode):
            try:
                return self.filename.encode('ascii'), self.flag_bits
            except UnicodeEncodeError:
                return self.filename.encode('utf-8'), self.flag_bits | 0x800
        else:
            return self.filename, self.flag_bits

    def _decodeFilename(self):
        if self.flag_bits & 0x800:
            return self.filename.decode('utf-8')
        else:
            return self.filename

    def _decodeExtra(self):
        # Try to decode the extra field.
        extra = self.extra
        unpack = struct.unpack
        while extra:
            tp, ln = unpack('<HH', extra[:4])
            if tp == 1:
                if ln >= 24:
                    counts = unpack('<QQQ', extra[4:28])
                elif ln == 16:
                    counts = unpack('<QQ', extra[4:20])
                elif ln == 8:
                    counts = unpack('<Q', extra[4:12])
                elif ln == 0:
                    counts = ()
                else:
                    raise RuntimeError, "Corrupt extra field %s"%(ln,)

                idx = 0

                # ZIP64 extension (large files and/or large archives)
                if self.file_size in (0xffffffffffffffffL, 0xffffffffL):
                    self.file_size = counts[idx]
                    idx += 1

                if self.compress_size == 0xFFFFFFFFL:
                    self.compress_size = counts[idx]
                    idx += 1

                if self.header_offset == 0xffffffffL:
                    old = self.header_offset
                    self.header_offset = counts[idx]
                    idx+=1

            extra = extra[ln+4:]


class _ZipDecrypter:
    """Class to handle decryption of files stored within a ZIP archive.

    ZIP supports a password-based form of encryption. Even though known
    plaintext attacks have been found against it, it is still useful
    to be able to get data out of such a file.

    Usage:
        zd = _ZipDecrypter(mypwd)
        plain_char = zd(cypher_char)
        plain_text = map(zd, cypher_text)
    """

    def _GenerateCRCTable():
        """Generate a CRC-32 table.

        ZIP encryption uses the CRC32 one-byte primitive for scrambling some
        internal keys. We noticed that a direct implementation is faster than
        relying on binascii.crc32().
        """
        poly = 0xedb88320
        table = [0] * 256
        for i in range(256):
            crc = i
            for j in range(8):
                if crc & 1:
                    crc = ((crc >> 1) & 0x7FFFFFFF) ^ poly
                else:
                    crc = ((crc >> 1) & 0x7FFFFFFF)
            table[i] = crc
        return table
    crctable = _GenerateCRCTable()

    def _crc32(self, ch, crc):
        """Compute the CRC32 primitive on one byte."""
        return ((crc >> 8) & 0xffffff) ^ self.crctable[(crc ^ ord(ch)) & 0xff]

    def __init__(self, pwd):
        self.key0 = 305419896
        self.key1 = 591751049
        self.key2 = 878082192
        for p in pwd:
            self._UpdateKeys(p)

    def _UpdateKeys(self, c):
        self.key0 = self._crc32(c, self.key0)
        self.key1 = (self.key1 + (self.key0 & 255)) & 4294967295
        self.key1 = (self.key1 * 134775813 + 1) & 4294967295
        self.key2 = self._crc32(chr((self.key1 >> 24) & 255), self.key2)

    def __call__(self, c):
        """Decrypt a single character."""
        c = ord(c)
        k = self.key2 | 2
        c = c ^ (((k * (k^1)) >> 8) & 255)
        c = chr(c)
        self._UpdateKeys(c)
        return c

class ZipExtFile:
    """File-like object for reading an archive member.
       Is returned by ZipFile.open().
    """

    def __init__(self, fileobj, zipinfo, decrypt=None):
        self.fileobj = fileobj
        self.decrypter = decrypt
        self.bytes_read = 0L
        self.rawbuffer = ''
        self.readbuffer = ''
        self.linebuffer = ''
        self.eof = False
        self.univ_newlines = False
        self.nlSeps = ("\n", )
        self.lastdiscard = ''

        self.compress_type = zipinfo.compress_type
        self.compress_size = zipinfo.compress_size

        self.closed  = False
        self.mode    = "r"
        self.name = zipinfo.filename

        # read from compressed files in 64k blocks
        self.compreadsize = 64*1024
        if self.compress_type == ZIP_DEFLATED:
            self.dc = zlib.decompressobj(-15)

    def set_univ_newlines(self, univ_newlines):
        self.univ_newlines = univ_newlines

        # pick line separator char(s) based on universal newlines flag
        self.nlSeps = ("\n", )
        if self.univ_newlines:
            self.nlSeps = ("\r\n", "\r", "\n")

    def __iter__(self):
        return self

    def next(self):
        nextline = self.readline()
        if not nextline:
            raise StopIteration()

        return nextline

    def close(self):
        self.closed = True

    def _checkfornewline(self):
        nl, nllen = -1, -1
        if self.linebuffer:
            # ugly check for cases where half of an \r\n pair was
            # read on the last pass, and the \r was discarded.  In this
            # case we just throw away the \n at the start of the buffer.
            if (self.lastdiscard, self.linebuffer[0]) == ('\r','\n'):
                self.linebuffer = self.linebuffer[1:]

            for sep in self.nlSeps:
                nl = self.linebuffer.find(sep)
                if nl >= 0:
                    nllen = len(sep)
                    return nl, nllen

        return nl, nllen

    def readline(self, size = -1):
        """Read a line with approx. size. If size is negative,
           read a whole line.
        """
        if size < 0:
            size = sys.maxint
        elif size == 0:
            return ''

        # check for a newline already in buffer
        nl, nllen = self._checkfornewline()

        if nl >= 0:
            # the next line was already in the buffer
            nl = min(nl, size)
        else:
            # no line break in buffer - try to read more
            size -= len(self.linebuffer)
            while nl < 0 and size > 0:
                buf = self.read(min(size, 100))
                if not buf:
                    break
                self.linebuffer += buf
                size -= len(buf)

                # check for a newline in buffer
                nl, nllen = self._checkfornewline()

            # we either ran out of bytes in the file, or
            # met the specified size limit without finding a newline,
            # so return current buffer
            if nl < 0:
                s = self.linebuffer
                self.linebuffer = ''
                return s

        buf = self.linebuffer[:nl]
        self.lastdiscard = self.linebuffer[nl:nl + nllen]
        self.linebuffer = self.linebuffer[nl + nllen:]

        # line is always returned with \n as newline char (except possibly
        # for a final incomplete line in the file, which is handled above).
        return buf + "\n"

    def readlines(self, sizehint = -1):
        """Return a list with all (following) lines. The sizehint parameter
        is ignored in this implementation.
        """
        result = []
        while True:
            line = self.readline()
            if not line: break
            result.append(line)
        return result

    def read(self, size = None):
        # act like file() obj and return empty string if size is 0
        if size == 0:
            return ''

        # determine read size
        bytesToRead = self.compress_size - self.bytes_read

        # adjust read size for encrypted files since the first 12 bytes
        # are for the encryption/password information
        if self.decrypter is not None:
            bytesToRead -= 12

        if size is not None and size >= 0:
            if self.compress_type == ZIP_STORED:
                lr = len(self.readbuffer)
                bytesToRead = min(bytesToRead, size - lr)
            elif self.compress_type == ZIP_DEFLATED:
                if len(self.readbuffer) > size:
                    # the user has requested fewer bytes than we've already
                    # pulled through the decompressor; don't read any more
                    bytesToRead = 0
                else:
                    # user will use up the buffer, so read some more
                    lr = len(self.rawbuffer)
                    bytesToRead = min(bytesToRead, self.compreadsize - lr)

        # avoid reading past end of file contents
        if bytesToRead + self.bytes_read > self.compress_size:
            bytesToRead = self.compress_size - self.bytes_read

        # try to read from file (if necessary)
        if bytesToRead > 0:
            bytes = self.fileobj.read(bytesToRead)
            self.bytes_read += len(bytes)
            self.rawbuffer += bytes

            # handle contents of raw buffer
            if self.rawbuffer:
                newdata = self.rawbuffer
                self.rawbuffer = ''

                # decrypt new data if we were given an object to handle that
                if newdata and self.decrypter is not None:
                    newdata = ''.join(map(self.decrypter, newdata))

                # decompress newly read data if necessary
                if newdata and self.compress_type == ZIP_DEFLATED:
                    newdata = self.dc.decompress(newdata)
                    self.rawbuffer = self.dc.unconsumed_tail
                    if self.eof and len(self.rawbuffer) == 0:
                        # we're out of raw bytes (both from the file and
                        # the local buffer); flush just to make sure the
                        # decompressor is done
                        newdata += self.dc.flush()
                        # prevent decompressor from being used again
                        self.dc = None

                self.readbuffer += newdata


        # return what the user asked for
        if size is None or len(self.readbuffer) <= size:
            bytes = self.readbuffer
            self.readbuffer = ''
        else:
            bytes = self.readbuffer[:size]
            self.readbuffer = self.readbuffer[size:]

        return bytes


class ZipFile:
    """ Class with methods to open, read, write, close, list zip files.

    z = ZipFile(file, mode="r", compression=ZIP_STORED, allowZip64=False)

    file: Either the path to the file, or a file-like object.
          If it is a path, the file will be opened and closed by ZipFile.
    mode: The mode can be either read "r", write "w" or append "a".
    compression: ZIP_STORED (no compression) or ZIP_DEFLATED (requires zlib).
    allowZip64: if True ZipFile will create files with ZIP64 extensions when
                needed, otherwise it will raise an exception when this would
                be necessary.

    """

    fp = None                   # Set here since __del__ checks it

    def __init__(self, file, mode="r", compression=ZIP_STORED, allowZip64=False):
        """Open the ZIP file with mode read "r", write "w" or append "a"."""
        if mode not in ("r", "w", "a"):
            raise RuntimeError('ZipFile() requires mode "r", "w", or "a"')

        if compression == ZIP_STORED:
            pass
        elif compression == ZIP_DEFLATED:
            if not zlib:
                raise RuntimeError,\
                      "Compression requires the (missing) zlib module"
        else:
            raise RuntimeError, "That compression method is not supported"

        self._allowZip64 = allowZip64
        self._didModify = False
        self.debug = 0  # Level of printing: 0 through 3
        self.NameToInfo = {}    # Find file info given name
        self.filelist = []      # List of ZipInfo instances for archive
        self.compression = compression  # Method of compression
        self.mode = key = mode.replace('b', '')[0]
        self.pwd = None
        self.comment = ''

        # Check if we were passed a file-like object
        if isinstance(file, basestring):
            self._filePassed = 0
            self.filename = file
            modeDict = {'r' : 'rb', 'w': 'wb', 'a' : 'r+b'}
            try:
                self.fp = open(file, modeDict[mode])
            except IOError:
                if mode == 'a':
                    mode = key = 'w'
                    self.fp = open(file, modeDict[mode])
                else:
                    raise
        else:
            self._filePassed = 1
            self.fp = file
            self.filename = getattr(file, 'name', None)

        if key == 'r':
            self._GetContents()
        elif key == 'w':
            pass
        elif key == 'a':
            try:                        # See if file is a zip file
                self._RealGetContents()
                # seek to start of directory and overwrite
                self.fp.seek(self.start_dir, 0)
            except BadZipfile:          # file is not a zip file, just append
                self.fp.seek(0, 2)
        else:
            if not self._filePassed:
                self.fp.close()
                self.fp = None
            raise RuntimeError, 'Mode must be "r", "w" or "a"'

    def _GetContents(self):
        """Read the directory, making sure we close the file if the format
        is bad."""
        try:
            self._RealGetContents()
        except BadZipfile:
            if not self._filePassed:
                self.fp.close()
                self.fp = None
            raise

    def _RealGetContents(self):
        """Read in the table of contents for the ZIP file."""
        fp = self.fp
        endrec = _EndRecData(fp)
        if not endrec:
            raise BadZipfile, "File is not a zip file"
        if self.debug > 1:
            print endrec
        size_cd = endrec[_ECD_SIZE]             # bytes in central directory
        offset_cd = endrec[_ECD_OFFSET]         # offset of central directory
        self.comment = endrec[_ECD_COMMENT]     # archive comment

        # "concat" is zero, unless zip was concatenated to another file
        concat = endrec[_ECD_LOCATION] - size_cd - offset_cd
        if endrec[_ECD_SIGNATURE] == stringEndArchive64:
            # If Zip64 extension structures are present, account for them
            concat -= (sizeEndCentDir64 + sizeEndCentDir64Locator)

        if self.debug > 2:
            inferred = concat + offset_cd
            print "given, inferred, offset", offset_cd, inferred, concat
        # self.start_dir:  Position of start of central directory
        self.start_dir = offset_cd + concat
        fp.seek(self.start_dir, 0)
        data = fp.read(size_cd)
        fp = cStringIO.StringIO(data)
        total = 0
        while total < size_cd:
            centdir = fp.read(sizeCentralDir)
            if centdir[0:4] != stringCentralDir:
                raise BadZipfile, "Bad magic number for central directory"
            centdir = struct.unpack(structCentralDir, centdir)
            if self.debug > 2:
                print centdir
            filename = fp.read(centdir[_CD_FILENAME_LENGTH])
            # Create ZipInfo instance to store file information
            x = ZipInfo(filename)
            x.extra = fp.read(centdir[_CD_EXTRA_FIELD_LENGTH])
            x.comment = fp.read(centdir[_CD_COMMENT_LENGTH])
            x.header_offset = centdir[_CD_LOCAL_HEADER_OFFSET]
            (x.create_version, x.create_system, x.extract_version, x.reserved,
                x.flag_bits, x.compress_type, t, d,
                x.CRC, x.compress_size, x.file_size) = centdir[1:12]
            x.volume, x.internal_attr, x.external_attr = centdir[15:18]
            # Convert date/time code to (year, month, day, hour, min, sec)
            x._raw_time = t
            x.date_time = ( (d>>9)+1980, (d>>5)&0xF, d&0x1F,
                                     t>>11, (t>>5)&0x3F, (t&0x1F) * 2 )

            x._decodeExtra()
            x.header_offset = x.header_offset + concat
            x.filename = x._decodeFilename()
            self.filelist.append(x)
            self.NameToInfo[x.filename] = x

            # update total bytes read from central directory
            total = (total + sizeCentralDir + centdir[_CD_FILENAME_LENGTH]
                     + centdir[_CD_EXTRA_FIELD_LENGTH]
                     + centdir[_CD_COMMENT_LENGTH])

            if self.debug > 2:
                print "total", total


    def namelist(self):
        """Return a list of file names in the archive."""
        l = []
        for data in self.filelist:
            l.append(data.filename)
        return l

    def infolist(self):
        """Return a list of class ZipInfo instances for files in the
        archive."""
        return self.filelist

    def printdir(self):
        """Print a table of contents for the zip file."""
        print "%-46s %19s %12s" % ("File Name", "Modified    ", "Size")
        for zinfo in self.filelist:
            date = "%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time[:6]
            print "%-46s %s %12d" % (zinfo.filename, date, zinfo.file_size)

    def testzip(self):
        """Read all the files and check the CRC."""
        chunk_size = 2 ** 20
        for zinfo in self.filelist:
            try:
                # Read by chunks, to avoid an OverflowError or a
                # MemoryError with very large embedded files.
                f = self.open(zinfo.filename, "r")
                while f.read(chunk_size):     # Check CRC-32
                    pass
            except BadZipfile:
                return zinfo.filename

    def getinfo(self, name):
        """Return the instance of ZipInfo given 'name'."""
        info = self.NameToInfo.get(name)
        if info is None:
            raise KeyError(
                'There is no item named %r in the archive' % name)

        return info

    def setpassword(self, pwd):
        """Set default password for encrypted files."""
        self.pwd = pwd

    def read(self, name, pwd=None):
        """Return file bytes (as a string) for name."""
        return self.open(name, "r", pwd).read()

    def open(self, name, mode="r", pwd=None):
        """Return file-like object for 'name'."""
        if mode not in ("r", "U", "rU"):
            raise RuntimeError, 'open() requires mode "r", "U", or "rU"'
        if not self.fp:
            raise RuntimeError, \
                  "Attempt to read ZIP archive that was already closed"

        # Only open a new file for instances where we were not
        # given a file object in the constructor
        if self._filePassed:
            zef_file = self.fp
        else:
            zef_file = open(self.filename, 'rb')

        # Make sure we have an info object
        if isinstance(name, ZipInfo):
            # 'name' is already an info object
            zinfo = name
        else:
            # Get info object for name
            zinfo = self.getinfo(name)

        zef_file.seek(zinfo.header_offset, 0)

        # Skip the file header:
        fheader = zef_file.read(sizeFileHeader)
        if fheader[0:4] != stringFileHeader:
            raise BadZipfile, "Bad magic number for file header"

        fheader = struct.unpack(structFileHeader, fheader)
        fname = zef_file.read(fheader[_FH_FILENAME_LENGTH])
        if fheader[_FH_EXTRA_FIELD_LENGTH]:
            zef_file.read(fheader[_FH_EXTRA_FIELD_LENGTH])

        if fname != zinfo.orig_filename:
            raise BadZipfile, \
                      'File name in directory "%s" and header "%s" differ.' % (
                          zinfo.orig_filename, fname)

        # check for encrypted flag & handle password
        is_encrypted = zinfo.flag_bits & 0x1
        zd = None
        if is_encrypted:
            if not pwd:
                pwd = self.pwd
            if not pwd:
                raise RuntimeError, "File %s is encrypted, " \
                      "password required for extraction" % name

            zd = _ZipDecrypter(pwd)
            # The first 12 bytes in the cypher stream is an encryption header
            #  used to strengthen the algorithm. The first 11 bytes are
            #  completely random, while the 12th contains the MSB of the CRC,
            #  or the MSB of the file time depending on the header type
            #  and is used to check the correctness of the password.
            bytes = zef_file.read(12)
            h = map(zd, bytes[0:12])
            if zinfo.flag_bits & 0x8:
                # compare against the file type from extended local headers
                check_byte = (zinfo._raw_time >> 8) & 0xff
            else:
                # compare against the CRC otherwise
                check_byte = (zinfo.CRC >> 24) & 0xff
            if ord(h[11]) != check_byte:
                raise RuntimeError("Bad password for file", name)

        # build and return a ZipExtFile
        if zd is None:
            zef = ZipExtFile(zef_file, zinfo)
        else:
            zef = ZipExtFile(zef_file, zinfo, zd)

        # set universal newlines on ZipExtFile if necessary
        if "U" in mode:
            zef.set_univ_newlines(True)
        return zef

    def extract(self, member, path=None, pwd=None):
        """Extract a member from the archive to the current working directory,
           using its full name. Its file information is extracted as accurately
           as possible. `member' may be a filename or a ZipInfo object. You can
           specify a different directory using `path'.
        """
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        return self._extract_member(member, path, pwd)

    def extractall(self, path=None, members=None, pwd=None):
        """Extract all members from the archive to the current working
           directory. `path' specifies a different directory to extract to.
           `members' is optional and must be a subset of the list returned
           by namelist().
        """
        if members is None:
            members = self.namelist()

        for zipinfo in members:
            self.extract(zipinfo, path, pwd)

    def _extract_member(self, member, targetpath, pwd):
        """Extract the ZipInfo object 'member' to a physical
           file on the path targetpath.
        """
        # build the destination pathname, replacing
        # forward slashes to platform specific separators.
        if targetpath[-1:] in (os.path.sep, os.path.altsep):
            targetpath = targetpath[:-1]

        # don't include leading "/" from file name if present
        if member.filename[0] == '/':
            targetpath = os.path.join(targetpath, member.filename[1:])
        else:
            targetpath = os.path.join(targetpath, member.filename)

        targetpath = os.path.normpath(targetpath)

        # Create all upper directories if necessary.
        upperdirs = os.path.dirname(targetpath)
        if upperdirs and not os.path.exists(upperdirs):
            os.makedirs(upperdirs)

        if member.filename[-1] == '/':
            os.mkdir(targetpath)
            return targetpath

        source = self.open(member, pwd=pwd)
        target = file(targetpath, "wb")
        shutil.copyfileobj(source, target)
        source.close()
        target.close()

        return targetpath

    def _writecheck(self, zinfo):
        """Check for errors before writing a file to the archive."""
        if zinfo.filename in self.NameToInfo:
            if self.debug:      # Warning for duplicate names
                print "Duplicate name:", zinfo.filename
        if self.mode not in ("w", "a"):
            raise RuntimeError, 'write() requires mode "w" or "a"'
        if not self.fp:
            raise RuntimeError, \
                  "Attempt to write ZIP archive that was already closed"
        if zinfo.compress_type == ZIP_DEFLATED and not zlib:
            raise RuntimeError, \
                  "Compression requires the (missing) zlib module"
        if zinfo.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
            raise RuntimeError, \
                  "That compression method is not supported"
        if zinfo.file_size > ZIP64_LIMIT:
            if not self._allowZip64:
                raise LargeZipFile("Filesize would require ZIP64 extensions")
        if zinfo.header_offset > ZIP64_LIMIT:
            if not self._allowZip64:
                raise LargeZipFile("Zipfile size would require ZIP64 extensions")

    def write(self, filename, arcname=None, compress_type=None):
        """Put the bytes from filename into the archive under the name
        arcname."""
        if not self.fp:
            raise RuntimeError(
                  "Attempt to write to ZIP archive that was already closed")

        st = os.stat(filename)
        isdir = stat.S_ISDIR(st.st_mode)
        mtime = time.localtime(st.st_mtime)
        date_time = mtime[0:6]
        # Create ZipInfo instance to store file information
        if arcname is None:
            arcname = filename
        arcname = os.path.normpath(os.path.splitdrive(arcname)[1])
        while arcname[0] in (os.sep, os.altsep):
            arcname = arcname[1:]
        if isdir:
            arcname += '/'
        zinfo = ZipInfo(arcname, date_time)
        zinfo.external_attr = (st[0] & 0xFFFF) << 16L      # Unix attributes
        if compress_type is None:
            zinfo.compress_type = self.compression
        else:
            zinfo.compress_type = compress_type

        zinfo.file_size = st.st_size
        zinfo.flag_bits = 0x00
        zinfo.header_offset = self.fp.tell()    # Start of header bytes

        self._writecheck(zinfo)
        self._didModify = True

        if isdir:
            zinfo.file_size = 0
            zinfo.compress_size = 0
            zinfo.CRC = 0
            self.filelist.append(zinfo)
            self.NameToInfo[zinfo.filename] = zinfo
            self.fp.write(zinfo.FileHeader())
            return

        fp = open(filename, "rb")
        # Must overwrite CRC and sizes with correct data later
        zinfo.CRC = CRC = 0
        zinfo.compress_size = compress_size = 0
        zinfo.file_size = file_size = 0
        self.fp.write(zinfo.FileHeader())
        if zinfo.compress_type == ZIP_DEFLATED:
            cmpr = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                 zlib.DEFLATED, -15)
        else:
            cmpr = None
        while 1:
            buf = fp.read(1024 * 8)
            if not buf:
                break
            file_size = file_size + len(buf)
            CRC = crc32(buf, CRC) & 0xffffffff
            if cmpr:
                buf = cmpr.compress(buf)
                compress_size = compress_size + len(buf)
            self.fp.write(buf)
        fp.close()
        if cmpr:
            buf = cmpr.flush()
            compress_size = compress_size + len(buf)
            self.fp.write(buf)
            zinfo.compress_size = compress_size
        else:
            zinfo.compress_size = file_size
        zinfo.CRC = CRC
        zinfo.file_size = file_size
        # Seek backwards and write CRC and file sizes
        position = self.fp.tell()       # Preserve current position in file
        self.fp.seek(zinfo.header_offset + 14, 0)
        self.fp.write(struct.pack("<LLL", zinfo.CRC, zinfo.compress_size,
              zinfo.file_size))
        self.fp.seek(position, 0)
        self.filelist.append(zinfo)
        self.NameToInfo[zinfo.filename] = zinfo

    def writestr(self, zinfo_or_arcname, bytes):
        """Write a file into the archive.  The contents is the string
        'bytes'.  'zinfo_or_arcname' is either a ZipInfo instance or
        the name of the file in the archive."""
        if not isinstance(zinfo_or_arcname, ZipInfo):
            zinfo = ZipInfo(filename=zinfo_or_arcname,
                            date_time=time.localtime(time.time())[:6])
            zinfo.compress_type = self.compression
            zinfo.external_attr = 0600 << 16
        else:
            zinfo = zinfo_or_arcname

        if not self.fp:
            raise RuntimeError(
                  "Attempt to write to ZIP archive that was already closed")

        zinfo.file_size = len(bytes)            # Uncompressed size
        zinfo.header_offset = self.fp.tell()    # Start of header bytes
        self._writecheck(zinfo)
        self._didModify = True
        zinfo.CRC = crc32(bytes) & 0xffffffff       # CRC-32 checksum
        if zinfo.compress_type == ZIP_DEFLATED:
            co = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                 zlib.DEFLATED, -15)
            bytes = co.compress(bytes) + co.flush()
            zinfo.compress_size = len(bytes)    # Compressed size
        else:
            zinfo.compress_size = zinfo.file_size
        zinfo.header_offset = self.fp.tell()    # Start of header bytes
        self.fp.write(zinfo.FileHeader())
        self.fp.write(bytes)
        self.fp.flush()
        if zinfo.flag_bits & 0x08:
            # Write CRC and file sizes after the file data
            self.fp.write(struct.pack("<lLL", zinfo.CRC, zinfo.compress_size,
                  zinfo.file_size))
        self.filelist.append(zinfo)
        self.NameToInfo[zinfo.filename] = zinfo

    def __del__(self):
        """Call the "close()" method in case the user forgot."""
        self.close()

    def close(self):
        """Close the file, and for mode "w" and "a" write the ending
        records."""
        if self.fp is None:
            return

        if self.mode in ("w", "a") and self._didModify: # write ending records
            count = 0
            pos1 = self.fp.tell()
            for zinfo in self.filelist:         # write central directory
                count = count + 1
                dt = zinfo.date_time
                dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
                dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
                extra = []
                if zinfo.file_size > ZIP64_LIMIT \
                        or zinfo.compress_size > ZIP64_LIMIT:
                    extra.append(zinfo.file_size)
                    extra.append(zinfo.compress_size)
                    file_size = 0xffffffff
                    compress_size = 0xffffffff
                else:
                    file_size = zinfo.file_size
                    compress_size = zinfo.compress_size

                if zinfo.header_offset > ZIP64_LIMIT:
                    extra.append(zinfo.header_offset)
                    header_offset = 0xffffffffL
                else:
                    header_offset = zinfo.header_offset

                extra_data = zinfo.extra
                if extra:
                    # Append a ZIP64 field to the extra's
                    extra_data = struct.pack(
                            '<HH' + 'Q'*len(extra),
                            1, 8*len(extra), *extra) + extra_data

                    extract_version = max(45, zinfo.extract_version)
                    create_version = max(45, zinfo.create_version)
                else:
                    extract_version = zinfo.extract_version
                    create_version = zinfo.create_version

                try:
                    filename, flag_bits = zinfo._encodeFilenameFlags()
                    centdir = struct.pack(structCentralDir,
                     stringCentralDir, create_version,
                     zinfo.create_system, extract_version, zinfo.reserved,
                     flag_bits, zinfo.compress_type, dostime, dosdate,
                     zinfo.CRC, compress_size, file_size,
                     len(filename), len(extra_data), len(zinfo.comment),
                     0, zinfo.internal_attr, zinfo.external_attr,
                     header_offset)
                except DeprecationWarning:
                    print >>sys.stderr, (structCentralDir,
                     stringCentralDir, create_version,
                     zinfo.create_system, extract_version, zinfo.reserved,
                     zinfo.flag_bits, zinfo.compress_type, dostime, dosdate,
                     zinfo.CRC, compress_size, file_size,
                     len(zinfo.filename), len(extra_data), len(zinfo.comment),
                     0, zinfo.internal_attr, zinfo.external_attr,
                     header_offset)
                    raise
                self.fp.write(centdir)
                self.fp.write(filename)
                self.fp.write(extra_data)
                self.fp.write(zinfo.comment)

            pos2 = self.fp.tell()
            # Write end-of-zip-archive record
            centDirCount = count
            centDirSize = pos2 - pos1
            centDirOffset = pos1
            if (centDirCount >= ZIP_FILECOUNT_LIMIT or
                centDirOffset > ZIP64_LIMIT or
                centDirSize > ZIP64_LIMIT):
                # Need to write the ZIP64 end-of-archive records
                zip64endrec = struct.pack(
                        structEndArchive64, stringEndArchive64,
                        44, 45, 45, 0, 0, centDirCount, centDirCount,
                        centDirSize, centDirOffset)
                self.fp.write(zip64endrec)

                zip64locrec = struct.pack(
                        structEndArchive64Locator,
                        stringEndArchive64Locator, 0, pos2, 1)
                self.fp.write(zip64locrec)
                centDirCount = min(centDirCount, 0xFFFF)
                centDirSize = min(centDirSize, 0xFFFFFFFF)
                centDirOffset = min(centDirOffset, 0xFFFFFFFF)

            # check for valid comment length
            if len(self.comment) >= ZIP_MAX_COMMENT:
                if self.debug > 0:
                    msg = 'Archive comment is too long; truncating to %d bytes' \
                          % ZIP_MAX_COMMENT
                self.comment = self.comment[:ZIP_MAX_COMMENT]

            endrec = struct.pack(structEndArchive, stringEndArchive,
                                 0, 0, centDirCount, centDirCount,
                                 centDirSize, centDirOffset, len(self.comment))
            self.fp.write(endrec)
            self.fp.write(self.comment)
            self.fp.flush()

        if not self._filePassed:
            self.fp.close()
        self.fp = None


class PyZipFile(ZipFile):
    """Class to create ZIP archives with Python library files and packages."""

    def writepy(self, pathname, basename = ""):
        """Add all files from "pathname" to the ZIP archive.

        If pathname is a package directory, search the directory and
        all package subdirectories recursively for all *.py and enter
        the modules into the archive.  If pathname is a plain
        directory, listdir *.py and enter all modules.  Else, pathname
        must be a Python *.py file and the module will be put into the
        archive.  Added modules are always module.pyo or module.pyc.
        This method will compile the module.py into module.pyc if
        necessary.
        """
        dir, name = os.path.split(pathname)
        if os.path.isdir(pathname):
            initname = os.path.join(pathname, "__init__.py")
            if os.path.isfile(initname):
                # This is a package directory, add it
                if basename:
                    basename = "%s/%s" % (basename, name)
                else:
                    basename = name
                if self.debug:
                    print "Adding package in", pathname, "as", basename
                fname, arcname = self._get_codename(initname[0:-3], basename)
                if self.debug:
                    print "Adding", arcname
                self.write(fname, arcname)
                dirlist = os.listdir(pathname)
                dirlist.remove("__init__.py")
                # Add all *.py files and package subdirectories
                for filename in dirlist:
                    path = os.path.join(pathname, filename)
                    root, ext = os.path.splitext(filename)
                    if os.path.isdir(path):
                        if os.path.isfile(os.path.join(path, "__init__.py")):
                            # This is a package directory, add it
                            self.writepy(path, basename)  # Recursive call
                    elif ext == ".py":
                        fname, arcname = self._get_codename(path[0:-3],
                                         basename)
                        if self.debug:
                            print "Adding", arcname
                        self.write(fname, arcname)
            else:
                # This is NOT a package directory, add its files at top level
                if self.debug:
                    print "Adding files from directory", pathname
                for filename in os.listdir(pathname):
                    path = os.path.join(pathname, filename)
                    root, ext = os.path.splitext(filename)
                    if ext == ".py":
                        fname, arcname = self._get_codename(path[0:-3],
                                         basename)
                        if self.debug:
                            print "Adding", arcname
                        self.write(fname, arcname)
        else:
            if pathname[-3:] != ".py":
                raise RuntimeError, \
                      'Files added with writepy() must end with ".py"'
            fname, arcname = self._get_codename(pathname[0:-3], basename)
            if self.debug:
                print "Adding file", arcname
            self.write(fname, arcname)

    def _get_codename(self, pathname, basename):
        """Return (filename, archivename) for the path.

        Given a module name path, return the correct file path and
        archive name, compiling if necessary.  For example, given
        /python/lib/string, return (/python/lib/string.pyc, string).
        """
        file_py  = pathname + ".py"
        file_pyc = pathname + ".pyc"
        file_pyo = pathname + ".pyo"
        if os.path.isfile(file_pyo) and \
                            os.stat(file_pyo).st_mtime >= os.stat(file_py).st_mtime:
            fname = file_pyo    # Use .pyo file
        elif not os.path.isfile(file_pyc) or \
             os.stat(file_pyc).st_mtime < os.stat(file_py).st_mtime:
            import py_compile
            if self.debug:
                print "Compiling", file_py
            try:
                py_compile.compile(file_py, file_pyc, None, True)
            except py_compile.PyCompileError,err:
                print err.msg
            fname = file_pyc
        else:
            fname = file_pyc
        archivename = os.path.split(fname)[1]
        if basename:
            archivename = "%s/%s" % (basename, archivename)
        return (fname, archivename)


def main(args = None):
    import textwrap
    USAGE=textwrap.dedent("""\
        Usage:
            zipfile.py -l zipfile.zip        # Show listing of a zipfile
            zipfile.py -t zipfile.zip        # Test if a zipfile is valid
            zipfile.py -e zipfile.zip target # Extract zipfile into target dir
            zipfile.py -c zipfile.zip src ... # Create zipfile from sources
        """)
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] not in ('-l', '-c', '-e', '-t'):
        print USAGE
        sys.exit(1)

    if args[0] == '-l':
        if len(args) != 2:
            print USAGE
            sys.exit(1)
        zf = ZipFile(args[1], 'r')
        zf.printdir()
        zf.close()

    elif args[0] == '-t':
        if len(args) != 2:
            print USAGE
            sys.exit(1)
        zf = ZipFile(args[1], 'r')
        zf.testzip()
        print "Done testing"

    elif args[0] == '-e':
        if len(args) != 3:
            print USAGE
            sys.exit(1)

        zf = ZipFile(args[1], 'r')
        out = args[2]
        for path in zf.namelist():
            if path.startswith('./'):
                tgt = os.path.join(out, path[2:])
            else:
                tgt = os.path.join(out, path)

            tgtdir = os.path.dirname(tgt)
            if not os.path.exists(tgtdir):
                os.makedirs(tgtdir)
            fp = open(tgt, 'wb')
            fp.write(zf.read(path))
            fp.close()
        zf.close()

    elif args[0] == '-c':
        if len(args) < 3:
            print USAGE
            sys.exit(1)

        def addToZip(zf, path, zippath):
            if os.path.isfile(path):
                zf.write(path, zippath, ZIP_DEFLATED)
            elif os.path.isdir(path):
                for nm in os.listdir(path):
                    addToZip(zf,
                            os.path.join(path, nm), os.path.join(zippath, nm))
            # else: ignore

        zf = ZipFile(args[1], 'w', allowZip64=True)
        for src in args[2:]:
            addToZip(zf, src, os.path.basename(src))

        zf.close()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = views
import os
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.sessions.models import Session
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from models import Folder, Image, Clipboard, ClipboardItem
from models import tools
from models import FolderRoot, UnfiledImages, ImagesWithMissingData
from django.contrib.auth.models import User

from django import forms

from django.contrib import admin

class NewFolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('name', )

def popup_status(request):
    return request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop')
def selectfolder_status(request):
    return request.REQUEST.has_key('select_folder')
def popup_param(request):
    if popup_status(request):
        return "?_popup=1"
    else:
        return ""
def _userperms(item, request):
    r = []
    ps = ['read', 'edit', 'add_children']
    for p in ps:
        attr = "has_%s_permission" % p
        if hasattr(item, attr):
            x = getattr(item, attr)(request)
            if x:
                r.append( p )
    return r
    
@login_required
def directory_listing(request, folder_id=None, viewtype=None):
    clipboard = tools.get_user_clipboard(request.user)
    if viewtype=='images_with_missing_data':
        folder = ImagesWithMissingData()
    elif viewtype=='unfiled_images':
        folder = UnfiledImages()
    elif folder_id == None:
        folder = FolderRoot()
    else:
        folder = Folder.objects.get(id=folder_id)
        
    # search
    def filter_folder(qs, terms=[]):
        for term in terms:
            qs = qs.filter(Q(name__icontains=term) | Q(owner__username__icontains=term) | Q(owner__first_name__icontains=term) | Q(owner__last_name__icontains=term)  )  
        return qs
    def filter_image(qs, terms=[]):
        for term in terms:
            qs = qs.filter( Q(name__icontains=term) | Q(original_filename__icontains=term ) | Q(owner__username__icontains=term) | Q(owner__first_name__icontains=term) | Q(owner__last_name__icontains=term) )
        return qs
    q = request.GET.get('q', None)
    if q:
        search_terms = q.split(" ")
    else:
        search_terms = []
    limit_search_to_folder = request.GET.get('limit_search_to_folder', False) in (True, 'on')

    if len(search_terms)>0:
        if folder and limit_search_to_folder and not folder.is_root:
            folder_qs = folder.get_descendants()
            # TODO: check how folder__in=folder.get_descendats() performs in large trees
            image_qs = Image.objects.filter(folder__in=folder.get_descendants())
        else:
            folder_qs = Folder.objects.all()
            image_qs = Image.objects.all()
        folder_qs = filter_folder(folder_qs, search_terms)
        image_qs = filter_image(image_qs, search_terms)
            
        show_result_count = True
    else:
        folder_qs = folder.children.all()
        image_qs = folder.image_files.all()
        show_result_count = False
    
    folder_qs = folder_qs.order_by('name')
    image_qs = image_qs.order_by('name')
    
    folder_children = []
    folder_files = []
    for f in folder_qs:
        f.perms = _userperms(f, request)
        if hasattr(f, 'has_read_permission'):
            if f.has_read_permission(request):
                #print "%s has read permission for %s" % (request.user, f)
                folder_children.append(f)
            else:
                pass#print "%s has NO read permission for %s" % (request.user, f)
        else:
            folder_children.append(f) 
    for f in image_qs:
        f.perms = _userperms(f, request)
        if hasattr(f, 'has_read_permission'):
            if f.has_read_permission(request):
                #print "%s has read permission for %s" % (request.user, f)
                folder_files.append(f)
            else:
                pass#print "%s has NO read permission for %s" % (request.user, f)
        else:
            folder_files.append(f)
    try:
        permissions = {
            'has_edit_permission': folder.has_edit_permission(request),
            'has_read_permission': folder.has_read_permission(request),
            'has_add_children_permission': folder.has_add_children_permission(request),
        }
    except:
        permissions = {}
    #print admin.site.root_path
    return render_to_response('image_filer/directory_listing.html', {
            'folder':folder,
            'folder_children':folder_children,
            'folder_files':folder_files,
            'permissions': permissions,
            'permstest': _userperms(folder, request),
            'current_url': request.path,
            'title': u'Directory listing for %s' % folder.name,
            'search_string': ' '.join(search_terms),
            'show_result_count': show_result_count,
            'limit_search_to_folder': limit_search_to_folder,
            'is_popup': popup_status(request),
            'select_folder': selectfolder_status(request),
            'root_path': "/%s" % admin.site.root_path, # needed in the admin/base.html template for logout links and stuff 
        }, context_instance=RequestContext(request))

@login_required
def edit_folder(request, folder_id):
    # TODO: implement edit_folder view
    folder=None
    return render_to_response('image_filer/folder_edit.html', {
            'folder':folder,
            'is_popup': request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop'),
        }, context_instance=RequestContext(request))

@login_required
def edit_image(request, folder_id):
    # TODO: implement edit_image view
    folder=None
    return render_to_response('image_filer/image_edit.html', {
            'folder':folder,
            'is_popup': request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop'),
        }, context_instance=RequestContext(request))

@login_required
def make_folder(request, folder_id=None):
    if not folder_id:
        folder_id = request.REQUEST.get('parent_id', None)
    if folder_id:
        folder = Folder.objects.get(id=folder_id)
    else:
        folder = None
        
    if request.user.is_superuser:
        pass
    elif folder == None:
        # regular users may not add root folders
        raise PermissionDenied
    elif not folder.has_add_children_permission(request):
        # the user does not have the permission to add subfolders
        raise PermissionDenied
    
    if request.method == 'POST':
        new_folder_form = NewFolderForm(request.POST)
        if new_folder_form.is_valid():
            new_folder = new_folder_form.save(commit=False)
            new_folder.parent = folder
            new_folder.owner = request.user
            new_folder.save()
            #print u"Saving folder %s as child of %s" % (new_folder, folder)
            return HttpResponse('<script type="text/javascript">opener.dismissPopupAndReload(window);</script>')
    else:
        #print u"New Folder GET, parent %s" % folder
        new_folder_form = NewFolderForm()
    return render_to_response('image_filer/include/new_folder_form.html', {
            'new_folder_form': new_folder_form,
            'is_popup': request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop'),
    }, context_instance=RequestContext(request))

class UploadFileForm(forms.ModelForm):
    class Meta:
        model=Image
        #fields = ('file',)
        
from image_filer.utils.files import generic_handle_file

@login_required
def upload(request):
    return render_to_response('image_filer/upload.html', {
                    'title': u'Upload files',
                    'is_popup': popup_status(request),
                    }, context_instance=RequestContext(request))

def ajax_upload(request, folder_id=None):
    """
    receives an upload from the flash uploader and fixes the session
    because of the missing cookie. Receives only one file at the time, 
    althow it may be a zip file, that will be unpacked.
    """
    #print request.POST
    # flashcookie-hack (flash does not submit the cookie, so we send the
    # django sessionid over regular post
    try:
        engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
        #session_key = request.POST.get('jsessionid')
        session_key = request.POST.get('jsessionid')
        request.session = engine.SessionStore(session_key)
        request.user = User.objects.get(id=request.session['_auth_user_id'])
        #print request.session['_auth_user_id']
        #print session_key
        #print engine
        #print request.user
        #print request.session
        # upload and save the file
        if not request.method == 'POST':
            return HttpResponse("must be POST")
        original_filename = request.POST.get('Filename')
        file = request.FILES.get('Filedata')
        #print request.FILES
        #print original_filename, file
        clipboard, was_clipboard_created = Clipboard.objects.get_or_create(user=request.user)
        files = generic_handle_file(file, original_filename)
        file_items = []
        for ifile, iname in files:
            try:
                iext = os.path.splitext(iname)[1].lower()
            except:
                iext = ''
            #print "extension: ", iext
            if iext in ['.jpg','.jpeg','.png','.gif']:
                imageform = UploadFileForm({'original_filename':iname,'owner': request.user.pk}, {'file':ifile})
                if imageform.is_valid():
                    #print 'imageform is valid'
                    try:
                        image = imageform.save(commit=False)
                        image.save()
                        file_items.append(image)
                    except Exception, e:
                        print e
                    #print "save %s" % image
                    bi = ClipboardItem(clipboard=clipboard, file=image)
                    bi.save()
                    #sprint image
                else:
                    pass#print imageform.errors
    except Exception, e:
        print e
        raise e
    return render_to_response('image_filer/include/clipboard_item_rows.html', {'items': file_items }, context_instance=RequestContext(request))

@login_required
def paste_clipboard_to_folder(request):
    if request.method=='POST':
        folder = Folder.objects.get( id=request.POST.get('folder_id') )
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        if folder.has_add_children_permission(request):
            tools.move_files_from_clipboard_to_folder(clipboard, folder)
            tools.discard_clipboard(clipboard)
        else:
            raise PermissionDenied
    return HttpResponseRedirect( '%s%s' % (request.REQUEST.get('redirect_to', ''), popup_param(request) ) )

@login_required
def discard_clipboard(request):
    if request.method=='POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        tools.discard_clipboard(clipboard)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )

@login_required
def delete_clipboard(request):
    if request.method=='POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        tools.delete_clipboard(clipboard)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )


@login_required
def move_file_to_clipboard(request):
    print "move file"
    if request.method=='POST':
        file_id = request.POST.get("file_id", None)
        clipboard = tools.get_user_clipboard(request.user)
        if file_id:
            file = Image.objects.get(id=file_id)
            if file.has_edit_permission(request):
                tools.move_file_to_clipboard([file], clipboard)
            else:
                raise PermissionDenied
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )

@login_required
def clone_files_from_clipboard_to_folder(request):
    if request.method=='POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        folder = Folder.objects.get( id=request.POST.get('folder_id') )
        tools.clone_files_from_clipboard_to_folder(clipboard, folder)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )

class ImageExportForm(forms.Form):
    FORMAT_CHOICES = (
        ('jpg', 'jpg'),
        ('png', 'png'),
        ('gif', 'gif'),
        #('tif', 'tif'),
    )
    format = forms.ChoiceField(choices=FORMAT_CHOICES)
    
    crop = forms.BooleanField(required=False)
    upscale = forms.BooleanField(required=False)
    
    width = forms.IntegerField()
    height = forms.IntegerField()
    
    
import filters
@login_required
def export_image(request, image_id):
    image = Image.objects.get(id=image_id)
    
    if request.method=='POST':
        form = ImageExportForm(request.POST)
        if form.is_valid():
            resize_filter = filters.ResizeFilter()
            im = filters.Image.open(image.file.path)
            format = form.cleaned_data['format']
            if format=='png':
                mimetype='image/jpg'
                pil_format = 'PNG'
            #elif format=='tif':
            #    mimetype='image/tiff'
            #    pil_format = 'TIFF'
            elif format=='gif':
                mimetype='image/gif'
                pil_format = 'GIF'
            else:
                mimetype='image/jpg'
                pil_format = 'JPEG'
            im = resize_filter.render(im,
                    size_x=int(form.cleaned_data['width']), 
                    size_y=int(form.cleaned_data['height']), 
                    crop=form.cleaned_data['crop'],
                    upscale=form.cleaned_data['upscale']
            )
            response = HttpResponse(mimetype='%s' % mimetype)
            response['Content-Disposition'] = 'attachment; filename=exported_image.%s' % format
            im.save(response, pil_format)
            return response
    else:
        form = ImageExportForm(initial={'crop': True, 'width': image.file.width, 'height':image.file.height})
    return render_to_response('image_filer/image_export_form.html', {
            'form': form,
            'image': image
    }, context_instance=RequestContext(request)) 

########NEW FILE########
