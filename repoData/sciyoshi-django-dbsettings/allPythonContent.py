__FILENAME__ = forms
import re

from django.db.models import get_model
from django import forms
from django.utils.datastructures import SortedDict
from django.utils.text import capfirst

from dbsettings.loading import get_setting_storage


RE_FIELD_NAME = re.compile(r'^(.+)__(.*)__(.+)$')


class SettingsEditor(forms.BaseForm):
    "Base editor, from which customized forms are created"

    def __iter__(self):
        for field in super(SettingsEditor, self).__iter__():
            yield self.specialize(field)

    def __getitem__(self, name):
        field = super(SettingsEditor, self).__getitem__(name)
        return self.specialize(field)

    def specialize(self, field):
        "Wrapper to add module_name and class_name for regrouping"
        field.label = capfirst(field.label)
        module_name, class_name, _ = RE_FIELD_NAME.match(field.name).groups()

        app_label = module_name.split('.')[-2]
        field.module_name = app_label

        if class_name:
            model = get_model(app_label, class_name)
            if model:
                class_name = model._meta.verbose_name
        field.class_name = class_name
        field.verbose_name = self.verbose_names[field.name]

        return field


def customized_editor(user, settings):
    "Customize the setting editor based on the current user and setting list"
    base_fields = SortedDict()
    verbose_names = {}
    for setting in settings:
        perm = '%s.can_edit_%s_settings' % (
            setting.module_name.split('.')[-2],
            setting.class_name.lower()
        )
        if user.has_perm(perm):
            # Add the field to the customized field list
            storage = get_setting_storage(*setting.key)
            kwargs = {
                'label': setting.description,
                'help_text': setting.help_text,
                # Provide current setting values for initializing the form
                'initial': setting.to_editor(storage.value),
                'required': setting.required,
                'widget': setting.widget,
            }
            if setting.choices:
                field = forms.ChoiceField(choices=setting.choices, **kwargs)
            else:
                field = setting.field(**kwargs)
            key = '%s__%s__%s' % setting.key
            base_fields[key] = field
            verbose_names[key] = setting.verbose_name
    attrs = {'base_fields': base_fields, 'verbose_names': verbose_names}
    return type('SettingsEditor', (SettingsEditor,), attrs)

########NEW FILE########
__FILENAME__ = group
import sys

from dbsettings.values import Value
from dbsettings.loading import register_setting, unregister_setting

__all__ = ['Group']


class GroupBase(type):
    def __init__(mcs, name, bases, attrs):
        if not bases or bases == (object,):
            return
        attrs.pop('__module__', None)
        attrs.pop('__doc__', None)
        for attribute_name, attr in attrs.items():
            if not isinstance(attr, Value):
                raise TypeError('The type of %s (%s) is not a valid Value.' %
                                (attribute_name, attr.__class__.__name__))
            mcs.add_to_class(attribute_name, attr)
        super(GroupBase, mcs).__init__(name, bases, attrs)


def install_permission(cls, permission):
    if permission not in cls._meta.permissions:
        # Add a permission for the setting editor
        try:
            cls._meta.permissions.append(permission)
        except AttributeError:
            # Permissions were supplied as a tuple, so preserve that
            cls._meta.permissions = tuple(cls._meta.permissions + (permission,))


class GroupDescriptor(object):
    def __init__(self, group, attribute_name):
        self.group = group
        self.attribute_name = attribute_name

    def __get__(self, instance=None, cls=None):
        if instance is not None:
            raise AttributeError("%r is not accessible from %s instances." %
                                 (self.attribute_name, cls.__name__))
        return self.group


class Group(object):
    __metaclass__ = GroupBase

    def __new__(cls, verbose_name=None, copy=True):
        # If not otherwise provided, set the module to where it was executed
        if '__module__' in cls.__dict__:
            module_name = cls.__dict__['__module__']
        else:
            module_name = sys._getframe(1).f_globals['__name__']

        attrs = [(k, v) for (k, v) in cls.__dict__.items() if isinstance(v, Value)]
        if copy:
            attrs = [(k, v.copy()) for (k, v) in attrs]
        attrs.sort(lambda a, b: cmp(a[1], b[1]))

        for _, attr in attrs:
            attr.creation_counter = Value.creation_counter
            Value.creation_counter += 1
            if not hasattr(attr, 'verbose_name'):
                attr.verbose_name = verbose_name
            register_setting(attr)

        attr_dict = dict(attrs + [('__module__', module_name)])

        # A new class is created so descriptors work properly
        # object.__new__ is necessary here to avoid recursion
        group = object.__new__(type('Group', (cls,), attr_dict))
        group._settings = attrs

        return group

    def contribute_to_class(self, cls, name):
        # Override module_name and class_name of all registered settings
        for attr in self.__class__.__dict__.values():
            if isinstance(attr, Value):
                unregister_setting(attr)
                attr.module_name = cls.__module__
                attr.class_name = cls.__name__
                register_setting(attr)

        # Create permission for editing settings on the model
        permission = (
            'can_edit_%s_settings' % cls.__name__.lower(),
            'Can edit %s settings' % cls._meta.verbose_name_raw,
        )
        if permission not in cls._meta.permissions:
            # Add a permission for the setting editor
            try:
                cls._meta.permissions.append(permission)
            except AttributeError:
                # Permissions were supplied as a tuple, so preserve that
                cls._meta.permissions = tuple(cls._meta.permissions + (permission,))

        # Finally, place the attribute on the class
        setattr(cls, name, GroupDescriptor(self, name))

    @classmethod
    def add_to_class(cls, attribute_name, value):
        value.contribute_to_class(cls, attribute_name)

    def __add__(self, other):
        if not isinstance(other, Group):
            raise NotImplementedError('Groups may only be added to other groups.')

        attrs = dict(self._settings + other._settings)
        attrs['__module__'] = sys._getframe(1).f_globals['__name__']
        return type('Group', (Group,), attrs)(copy=False)

    def __iter__(self):
        for attribute_name, _ in self._settings:
            yield attribute_name, getattr(self, attribute_name)

    def keys(self):
        return [k for (k, _) in self]

    def values(self):
        return [v for (_, v) in self]

########NEW FILE########
__FILENAME__ = loading
from bisect import bisect

from django.utils.datastructures import SortedDict
from django.core.cache import cache

from dbsettings.models import Setting

__all__ = ['get_all_settings', 'get_setting', 'get_setting_storage',
           'register_setting', 'unregister_setting', 'set_setting_value']


class SettingDict(SortedDict):
    "Sorted dict that has a bit more list-type functionality"

    def __iter__(self):
        return self.itervalues()

_settings = SettingDict()


def _get_cache_key(module_name, class_name, attribute_name):
    return '.'.join(['dbsettings', module_name, class_name, attribute_name])


def get_all_settings():
    return list(_settings)


def get_app_settings(app_label):
    return [p for p in _settings if app_label == p.module_name.split('.')[-2]]


def get_setting(module_name, class_name, attribute_name):
    return _settings[module_name, class_name, attribute_name]


def get_setting_storage(module_name, class_name, attribute_name):
    key = _get_cache_key(module_name, class_name, attribute_name)
    storage = cache.get(key)
    if storage is None:
        try:
            storage = Setting.objects.get(
                module_name=module_name,
                class_name=class_name,
                attribute_name=attribute_name,
            )
        except Setting.DoesNotExist:
            setting_object = get_setting(module_name, class_name, attribute_name)
            storage = Setting(
                module_name=module_name,
                class_name=class_name,
                attribute_name=attribute_name,
                value=setting_object.default,
            )
        cache.set(key, storage)
    return storage


def register_setting(setting):
    if setting.key not in _settings:
        _settings.insert(bisect(list(_settings), setting), setting.key, setting)


def unregister_setting(setting):
    if setting.key in _settings and _settings[setting.key] is setting:
        del _settings[setting.key]


def set_setting_value(module_name, class_name, attribute_name, value):
    setting = get_setting(module_name, class_name, attribute_name)
    storage = get_setting_storage(module_name, class_name, attribute_name)
    storage.value = setting.get_db_prep_save(value)
    storage.save()
    key = _get_cache_key(module_name, class_name, attribute_name)
    cache.delete(key)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.sites.models import Site


class SettingManager(models.Manager):
    def get_query_set(self):
        all = super(SettingManager, self).get_query_set()
        return all.filter(site=Site.objects.get_current())


class Setting(models.Model):
    site = models.ForeignKey(Site)
    module_name = models.CharField(max_length=255)
    class_name = models.CharField(max_length=255, blank=True)
    attribute_name = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True)

    objects = SettingManager()

    def __nonzero__(self):
        return self.pk is not None

    def save(self, *args, **kwargs):
        self.site = Site.objects.get_current()
        return super(Setting, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import *
from django.contrib import admin

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^settings/', include('dbsettings.urls')),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('dbsettings.views',
    url(r'^$', 'site_settings', name='site_settings'),
    url(r'^(?P<app_label>[^/]+)/$', 'app_settings', name='app_settings'),
)

########NEW FILE########
__FILENAME__ = utils
def set_defaults(app, *defaults):
    "Installs a set of default values during syncdb processing"
    from django.core.exceptions import ImproperlyConfigured
    from django.db.models import signals
    from dbsettings.loading import get_setting_storage, set_setting_value

    if not defaults:
        raise ImproperlyConfigured("No defaults were supplied to set_defaults.")
    app_label = app.__name__.split('.')[-2]

    def install_settings(app, created_models, verbosity=2, **kwargs):
        printed = False

        for class_name, attribute_name, value in defaults:
            if not get_setting_storage(app.__name__, class_name, attribute_name):
                if verbosity >= 2 and not printed:
                    # Print this message only once, and only if applicable
                    print "Installing default settings for %s" % app_label
                    printed = True
                try:
                    set_setting_value(app.__name__, class_name, attribute_name, value)
                except:
                    raise ImproperlyConfigured("%s requires dbsettings." % app_label)

    signals.post_syncdb.connect(install_settings, sender=app, weak=False)

########NEW FILE########
__FILENAME__ = values
import datetime
from decimal import Decimal
from hashlib import md5
from os.path import join as pjoin
import time
from PIL import Image

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import formats
from django.utils.safestring import mark_safe

from dbsettings.loading import get_setting_storage, set_setting_value

__all__ = ['Value', 'BooleanValue', 'DecimalValue', 'EmailValue',
           'DurationValue', 'FloatValue', 'IntegerValue', 'PercentValue',
           'PositiveIntegerValue', 'StringValue', 'TextValue',
           'MultiSeparatorValue', 'ImageValue',
           'DateTimeValue', 'DateValue', 'TimeValue']


class Value(object):

    creation_counter = 0
    unitialized_value = None

    def __init__(self, description=None, help_text=None, choices=None, required=True, default=None, widget=None):
        self.description = description
        self.help_text = help_text
        self.choices = choices or []
        self.required = required
        self.widget = widget
        if default is None:
            self.default = self.unitialized_value
        else:
            self.default = default

        self.creation_counter = Value.creation_counter
        Value.creation_counter += 1

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        return cmp(self.creation_counter, other.creation_counter)

    def copy(self):
        new_value = self.__class__()
        new_value.__dict__ = self.__dict__.copy()
        return new_value

    @property
    def key(self):
        return self.module_name, self.class_name, self.attribute_name

    def contribute_to_class(self, cls, attribute_name):
        self.module_name = cls.__module__
        self.class_name = ''
        self.attribute_name = attribute_name
        self.description = self.description or attribute_name.replace('_', ' ')

        setattr(cls, self.attribute_name, self)

    def __get__(self, instance=None, cls=None):
        if instance is None:
            raise AttributeError("%r is only accessible from %s instances." %
                                 (self.attribute_name, cls.__name__))
        try:
            storage = get_setting_storage(*self.key)
            return self.to_python(storage.value)
        except:
            return None

    def __set__(self, instance, value):
        current_value = self.__get__(instance)
        python_value = value if value is None else self.to_python(value)
        if python_value != current_value:
            set_setting_value(*(self.key + (value,)))

    # Subclasses should override the following methods where applicable

    def to_python(self, value):
        "Returns a native Python object suitable for immediate use"
        return value

    def get_db_prep_save(self, value):
        "Returns a value suitable for storage into a CharField"
        return unicode(value)

    def to_editor(self, value):
        "Returns a value suitable for display in a form widget"
        return unicode(value)

###############
# VALUE TYPES #
###############


class BooleanValue(Value):
    unitialized_value = False

    class field(forms.BooleanField):

        def __init__(self, *args, **kwargs):
            kwargs['required'] = False
            forms.BooleanField.__init__(self, *args, **kwargs)

    def to_python(self, value):
        if value in (True, 't', 'True'):
            return True
        return False

    to_editor = to_python


class DecimalValue(Value):
    field = forms.DecimalField

    def to_python(self, value):
        return Decimal(value)


# DurationValue has a lot of duplication and ugliness because of issue #2443
# Until DurationField is sorted out, this has to do some extra work
class DurationValue(Value):

    class field(forms.CharField):
        def clean(self, value):
            try:
                return datetime.timedelta(seconds=float(value))
            except (ValueError, TypeError):
                raise forms.ValidationError('This value must be a real number.')
            except OverflowError:
                raise forms.ValidationError('The maximum allowed value is %s' %
                                            datetime.timedelta.max)

    def to_python(self, value):
        if isinstance(value, datetime.timedelta):
            return value
        try:
            return datetime.timedelta(seconds=float(value))
        except (ValueError, TypeError):
            raise forms.ValidationError('This value must be a real number.')
        except OverflowError:
            raise forms.ValidationError('The maximum allowed value is %s' % datetime.timedelta.max)

    def get_db_prep_save(self, value):
        return unicode(value.days * 24 * 3600 + value.seconds + float(value.microseconds) / 1000000)


class FloatValue(Value):
    field = forms.FloatField

    def to_python(self, value):
        return float(value)


class IntegerValue(Value):
    field = forms.IntegerField

    def to_python(self, value):
        return int(value)


class PercentValue(Value):

    class field(forms.DecimalField):

        def __init__(self, *args, **kwargs):
            forms.DecimalField.__init__(self, 100, 0, 5, 2, *args, **kwargs)

        class widget(forms.TextInput):
            def render(self, *args, **kwargs):
                # Place a percent sign after a smaller text field
                attrs = kwargs.pop('attrs', {})
                attrs['size'] = attrs['max_length'] = 6
                return mark_safe(
                    forms.TextInput.render(self, attrs=attrs, *args, **kwargs) +
                    '<span style="vertical-align: middle;">&nbsp;%</span>')

    def to_python(self, value):
        return Decimal(value) / 100


class PositiveIntegerValue(IntegerValue):

    class field(forms.IntegerField):

        def __init__(self, *args, **kwargs):
            kwargs['min_value'] = 0
            forms.IntegerField.__init__(self, *args, **kwargs)


class StringValue(Value):
    unitialized_value = ''
    field = forms.CharField


class TextValue(Value):
    unitialized_value = ''
    field = forms.CharField

    def to_python(self, value):
        return unicode(value)


class EmailValue(Value):
    unitialized_value = ''
    field = forms.EmailField

    def to_python(self, value):
        return unicode(value)


class MultiSeparatorValue(TextValue):
    """Provides a way to store list-like string settings.
    e.g 'mail@test.com;*@blah.com' would be returned as
        [u'mail@test.com', u'*@blah.com']. What the method
        uses to split on can be defined by passing in a
        separator string (default is semi-colon as above).
    """

    def __init__(self, description=None, help_text=None, separator=';', required=True,
                 default=None):
        self.separator = separator
        if default is not None:
            # convert from list to string
            default = separator.join(default)
        super(MultiSeparatorValue, self).__init__(description=description,
                                                  help_text=help_text,
                                                  required=required,
                                                  default=default)

    class field(forms.CharField):

        class widget(forms.Textarea):
            pass

    def to_python(self, value):
        if value:
            value = unicode(value)
            value = value.split(self.separator)
            value = filter(None, (x.strip() for x in value))
        else:
            value = []
        return value


class ImageValue(Value):
    def __init__(self, *args, **kwargs):
        if 'upload_to' in kwargs:
            self._upload_to = kwargs.pop('upload_to', '')
        super(ImageValue, self).__init__(*args, **kwargs)

    class field(forms.ImageField):
        class widget(forms.FileInput):
            "Widget with preview"

            def render(self, name, value, attrs=None):
                output = []

                try:
                    if not value:
                        raise IOError('No value')

                    Image.open(value.file)
                    file_name = pjoin(settings.MEDIA_URL, value.name).replace("\\", "/")
                    params = {"file_name": file_name}
                    output.append(u'<p><img src="%(file_name)s" width="100" /></p>' % params)
                except IOError:
                    pass

                output.append(forms.FileInput.render(self, name, value, attrs))
                return mark_safe(''.join(output))

    def to_python(self, value):
        "Returns a native Python object suitable for immediate use"
        return unicode(value)

    def get_db_prep_save(self, value):
        "Returns a value suitable for storage into a CharField"
        if not value:
            return None

        hashed_name = md5(unicode(time.time())).hexdigest() + value.name[-4:]
        image_path = pjoin(self._upload_to, hashed_name)
        dest_name = pjoin(settings.MEDIA_ROOT, image_path)

        with open(dest_name, 'wb+') as dest_file:
            for chunk in value.chunks():
                dest_file.write(chunk)

        return unicode(image_path)

    def to_editor(self, value):
        "Returns a value suitable for display in a form widget"
        if not value:
            return None

        file_name = pjoin(settings.MEDIA_ROOT, value)
        try:
            with open(file_name, 'rb') as f:
                uploaded_file = SimpleUploadedFile(value, f.read(), 'image')

                # hack to retrieve path from `name` attribute
                uploaded_file.__dict__['_name'] = value
                return uploaded_file
        except IOError:
            return None


class DateTimeValue(Value):
    field = forms.DateTimeField
    formats_source = 'DATETIME_INPUT_FORMATS'

    @property
    def _formats(self):
        return formats.get_format(self.formats_source)

    def _parse_format(self, value):
        for format in self._formats:
            try:
                return datetime.datetime.strptime(value, format)
            except ValueError:
                continue
        return None

    def get_db_prep_save(self, value):
        if isinstance(value, basestring):
            return value
        return value.strftime(self._formats[0])

    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value
        return self._parse_format(value)


class DateValue(DateTimeValue):
    field = forms.DateField
    formats_source = 'DATE_INPUT_FORMATS'

    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value.date()
        elif isinstance(value, datetime.date):
            return value
        res = self._parse_format(value)
        if res is not None:
            return res.date()
        return res


class TimeValue(DateTimeValue):
    field = forms.TimeField
    formats_source = 'TIME_INPUT_FORMATS'

    def to_python(self, value):
        if isinstance(value, datetime.datetime):
            return value.time()
        elif isinstance(value, datetime.time):
            return value
        res = self._parse_format(value)
        if res is not None:
            return res.time()
        return res

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages

from dbsettings import loading, forms


@staff_member_required
def app_settings(request, app_label, template='dbsettings/app_settings.html'):
    # Determine what set of settings this editor is used for
    if app_label is None:
        settings = loading.get_all_settings()
        title = _('Site settings')
    else:
        settings = loading.get_app_settings(app_label)
        title = _('%(app)s settings') % {'app': capfirst(app_label)}

    # Create an editor customized for the current user
    editor = forms.customized_editor(request.user, settings)

    if request.method == 'POST':
        # Populate the form with user-submitted data
        form = editor(request.POST.copy(), request.FILES)
        if form.is_valid():
            form.full_clean()

            for name, value in form.cleaned_data.items():
                key = forms.RE_FIELD_NAME.match(name).groups()
                setting = loading.get_setting(*key)
                try:
                    storage = loading.get_setting_storage(*key)
                    current_value = setting.to_python(storage.value)
                except:
                    current_value = None

                if current_value != setting.to_python(value):
                    args = key + (value,)
                    loading.set_setting_value(*args)

                    # Give user feedback as to which settings were changed
                    if setting.class_name:
                        location = setting.class_name
                    else:
                        location = setting.module_name
                    update_msg = (_(u'Updated %(desc)s on %(location)s') %
                                  {'desc': unicode(setting.description), 'location': location})
                    messages.add_message(request, messages.INFO, update_msg)

            return HttpResponseRedirect(request.path)
    else:
        # Leave the form populated with current setting values
        form = editor()

    return render_to_response(template, {
        'title': title,
        'form': form,
    }, context_instance=RequestContext(request))


# Site-wide setting editor is identical, but without an app_label
def site_settings(request):
    return app_settings(request, app_label=None, template='dbsettings/site_settings.html')
# staff_member_required is implied, since it calls app_settings

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.core.management import call_command


INSTALLED_APPS = (
    # Required contrib apps.
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    # Our app and it's test app.
    'dbsettings',
)

SETTINGS = {
    'INSTALLED_APPS': INSTALLED_APPS,
    'SITE_ID': 1,
    'ROOT_URLCONF': 'dbsettings.tests.test_urls',
}

if DJANGO_VERSION > (1, 2):
    # Post multi-db settings.
    SETTINGS['DATABASES'] = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    # Pre multi-db settings.
    SETTINGS['DATABASE_ENGINE'] = 'sqlite3'
    SETTINGS['DATABASE_NAME'] = ':memory:'

if not settings.configured:
    settings.configure(**SETTINGS)

call_command('test', 'dbsettings')

########NEW FILE########
