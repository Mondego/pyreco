__FILENAME__ = admin
import appsettings
from django.contrib import admin
from appsettings.models import Setting

if appsettings.SHOW_ADMIN:
    admin.site.register(Setting)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = app
import settingsobj

settings = settingsobj.Settings()
if not settingsobj.Settings.discovered:
    from appsettings import autodiscover
    autodiscover()

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = fields
from django.forms import widgets
from django import forms
from django.utils import simplejson
#from django.core import validators

class ListWidget(widgets.Input):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        value = ', '.join(value)
        return super(ListWidget, self).render(name, value, attrs)

class ListField(forms.Field):
    widget = ListWidget
    default_error_messages = {}

    def to_python(self, value):
        """Validates the value and converts to python"""
        if value is None:
            return ()
        elif type(value) in (tuple, list):
            return tuple(value)
        elif type(value) in (str, unicode):
            return tuple(a.strip() for a in value.split(','))
        raise forms.ValidationError, 'invalid?'

class DictWidget(widgets.Input):
    input_type = 'text'
    def render(self, name, value, attrs=None):
        value = simplejson.dumps(value)
        return super(DictWidget, self).render(name, value, attrs)

class DictField(forms.Field):
    widget = DictWidget
    default_error_messages = {}

    def to_python(self, value):
        """Validates the value and converts to python"""
        if value is None:
            return {}
        elif type(value) is dict:
            return value
        elif type(value) in (str, unicode):
            value = json.loads(value)
            if type(value) is dict:
                return value
        raise forms.ValidationError, 'invalid input. requires a dictionary'




# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = forms
from django import forms
from settingsobj import Settings
settings = Settings()

_form = None

class Fieldset(object):
    def __init__(self, form, fields, name, verbose_name):
        self.form = form
        self.fields = fields
        self.name = name
        self.verbose_name = verbose_name
        
    def __iter__(self):
        for name in self.fields:
            yield self.form[name]

    def __getitem__(self, name):
        "Returns a BoundField with the given name."
        try:
            return self.form[name]
        except KeyError:
            raise KeyError('Key %r not found in Form' % name)

class FieldsetForm(forms.BaseForm):
    def __init__(self, *args, **kwargs):
        super(FieldsetForm, self).__init__(*args, **kwargs)
        self.fieldsets = []
        for name, verbose_name, fields in self.base_fieldsets:
            self.fieldsets.append(Fieldset(self, fields, name, verbose_name))


def settings_form():
    global _form
    if not _form:
        fields = {}
        fieldsets = []
        for app_name in sorted(vars(settings).keys()):
            app = getattr(settings, app_name)
            for group_name, group in app._vals.iteritems():
                if group._readonly:continue
                fieldset_fields = []
                for key, value in group._vals.iteritems():
                    field_name = '%s-%s-%s' % (app_name, group_name, key)
                    fields[field_name] = value
                    fieldset_fields.append(field_name)
                fieldsets.append((group_name, group._verbose_name, fieldset_fields,))
        _form = type('SettingsForm', (FieldsetForm,),
                     {'base_fieldsets': fieldsets, 'base_fields':fields})
    return _form

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.http import HttpResponseRedirect
from appsettings.settingsobj import has_db
from settingsobj import Settings
settingsinst = Settings()

Settings.using_middleware = True



class SettingsMiddleware(object):
    """
    Load the settings from the database for each request (thread), do not use with caching.
    """
    def process_request(self, request):
        settingsinst.update_from_db()


########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.sites.models import Site

class Setting(models.Model):
    site = models.ForeignKey(Site)
    app = models.CharField(max_length=255)
    class_name = models.CharField(max_length=255, blank=True)
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True)

    def __setattr__(self, name, value):
        if name != 'value':
            try:
                current = getattr(self, name, None)
            except:
                current = None
            if current is not None and current is not '':
                return
        super(Setting, self).__setattr__(name, value)

    class Meta:
        db_table = 'appsettings_setting'


########NEW FILE########
__FILENAME__ = settingsobj
try:
    from django import db
    from django.db.backends.dummy import base
    from models import Setting
    has_db = not isinstance(db.connection, base.DatabaseWrapper)
    numsettings = Setting.objects.all().count()
except:
    has_db = False

import inspect
from models import Setting
from django.contrib.sites.models import Site
from django.utils.encoding import force_unicode
from django import forms
from django.core.cache import cache


from appsettings import user
import appsettings

class SettingsException(Exception):pass
class MultipleSettingsException(Exception):pass


class Settings(object):
    discovered = False
    using_middleware = False
    _state = { }
    # see http://code.activestate.com/recipes/66531/
    def __new__(cls, *p, **k):
        self = object.__new__(cls, *p, **k)
        self.__dict__ = cls._state
        return self

    @classmethod
    def _reset(cls):
        """Reset all `Settings` object to the initial empty condition."""
        cls._state = { }

    def _register(self, appname, classobj, readonly=False, main=False):
        if not hasattr(self, appname):
            setattr(self, appname, App(appname))
        getattr(self, appname)._add(classobj, readonly, main, getattr(user.settings, appname)._dct)

    def update_from_db(self):
        if has_db:
            settings = Setting.objects.all()
            for setting in settings:
                app = getattr(self, setting.app)
                if app._vals.has_key(setting.class_name):
                    group = app._vals[setting.class_name]
                    if group._vals.has_key(setting.key):
                        group._vals[setting.key].initial = group._vals[setting.key].clean(setting.value)
                    else:
                        ## the app removed the setting... shouldn't happen
                        ## in production. maybe error? or del it?
                        pass


class App(object):
    def __init__(self, app):
        self._name = app
        self._vals = {}
        self._main = None

    def _add(self, classobj, readonly, main, preset):
        name = classobj.__name__.lower()
        if name in self._vals or (self._main is not None and name in self._vals[self._main]):
            raise SettingsException, 'duplicate declaration of settings group %s.%s' % (self._name, name)
        if name in ('_vals','_add','_name'):
            raise SettingsException, 'invalid group name: %s' % name

        if not main:
            preset = preset.get(name, {})
        self._vals[name] = Group(self._name, name, classobj, preset, main)
        if readonly:
            self._vals[name]._readonly = readonly
        if main:
            if self._main is not None:
                raise SettingsException, 'multiple "main" groups defined for app %s' % self._name
            self._main = name

    def __getattr__(self, name):
        if name not in ('_vals', '_name', '_add', '_main'):
            if name not in self._vals and self._main:
                if name in self._vals[self._main]._vals:
                    return getattr(self._vals[self._main], name)
                raise SettingsException, 'group not found: %s' % name
            return self._vals[name]
        return super(App, self).__getattribute__(name)

    def __setattr__(self, name, val):
        if name not in ('_vals', '_name', '_add', '_main') and self._main:
            if name in self._vals[self._name]._vals:
                return setattr(self._vals[self._name], name, val)
            raise SettingsException, 'groups are immutable'
        super(App, self).__setattr__(name, val)

class Group(object):
    def __init__(self, appname, name, classobj, preset, main=False):
        self._appname = appname
        self._name = name
        self._verbose_name = name
        self._vals = {}
        self._readonly = False
        self._cache_prefix = 'appsetting-%s-%s-%s-' % (Site.objects.get_current().pk, self._appname, self._name)

        for attr in inspect.classify_class_attrs(classobj):
            # for Python 2.5 compatiblity, we use tuple indexes
            # instead of the attribute names (which are only available
            # from Python 2.6 onwards).  Here's the mapping:
            #   attr[0]  attr.name   Attribute name
            #   attr[1]  attr.kind   class/static method, property, data
            #   attr[2]  attr.defining_class  The `class` object that created this attr
            #   attr[3]  attr.object Attribute value
            #
            if attr[2] != classobj or attr[1] != 'data':
                continue
            if attr[0].startswith('_'):
                continue
            if attr[0] == 'verbose_name':
                self._verbose_name = attr[3]
                continue
            val = attr[3]
            key = attr[0]
            if type(val) == int:
                val = forms.IntegerField(label=key.title(), initial=val)
            elif type(val) == float:
                val = forms.FloatField(label=key.title(), initial=val)
            elif type(val) == str:
                val = forms.CharField(label=key.title(), initial=val)
            elif val in (True, False):
                val = forms.BooleanField(label=key.title(), initial=val)
            elif not isinstance(val, forms.Field):
                raise SettingsException, 'settings must be of a valid form field type'
            if preset.has_key(key):
                val.initial = preset[key]
            try:
                val.initial = val.clean(val.initial)
            except forms.ValidationError:
                if main:
                    raise SettingsException, 'setting %s.%s not set. Please set it in your settings.py' % (appname, key)
                raise SettingsException, 'setting %s.%s.%s not set. Please set it in your settings.py' % (appname, name, key)
            val._parent = self
            self._vals[key] = val

        if has_db:
            settings = Setting.objects.all().filter(app=self._appname,
                    class_name=self._name)
            for setting in settings:
                if self._vals.has_key(setting.key):
                    self._vals[setting.key].initial = self._vals[setting.key].clean(setting.value)
                else:
                    ## the app removed the setting... shouldn't happen
                    ## in production. maybe error? or del it?
                    pass

    def __getattr__(self, name):
        if name not in ('_vals', '_name', '_appname', '_verbose_name', '_readonly', '_cache_prefix'):
            if name not in self._vals:
                raise AttributeError, 'setting "%s" not found'%name
            if has_db:
                if appsettings.USE_CACHE and cache.has_key(self._cache_prefix+name):
                    return cache.get(self._cache_prefix+name)
                if not Settings.using_middleware:
                    try:
                        setting = Setting.objects.get(app=self._appname, class_name=self._name, key=name)
                    except Setting.DoesNotExist:
                        pass
                    else:
                        return self._vals[setting.key].clean(setting.value)
            return self._vals[name].initial
        return super(Group, self).__getattribute__(name)

    def __setattr__(self, name, value):
        if name in ('_vals', '_name', '_appname', '_verbose_name', '_readonly', '_cache_prefix'):
            return object.__setattr__(self, name, value)
        if self._readonly:
            raise AttributeError, 'settings group %s is read-only' % self._name
        if not name in self._vals:
            raise AttributeError, 'setting "%s" not found'%name
        if not has_db:
            raise SettingsException, "no database -- settings are immutable"
        self._vals[name].initial = self._vals[name].clean(value)
        try:
            setting = Setting.objects.get(app = self._appname,
                    site = Site.objects.get_current(), 
                    class_name = self._name,
                    key = name)
        except Setting.DoesNotExist:
            setting = Setting(site = Site.objects.get_current(), 
                    app = self._appname, 
                    class_name = self._name, 
                    key = name)
        serialized = value
        if hasattr(self._vals[name].widget, '_format_value'):
            serialized = self._vals[name].widget._format_value(value)
        serialized = force_unicode(serialized)
        setting.value = serialized
        setting.save()
        if appsettings.USE_CACHE:
            cache.set(self._cache_prefix+name, value)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django import forms
import settingsobj
import appsettings

CHEESES = ('american','ricotta','fetta')
CHEESES = tuple((a,a) for a in CHEESES)

class Cheese:
    color = 'white'
    age = 5
    type = forms.ChoiceField(choices = CHEESES, initial='ricotta')

class RDOnly:
    version = 4

class Globals:
    spam = 'spamspamspam'

class SimpleTest(TestCase):
    def setUp(self):
        settingsobj.Settings._reset()
        self.settings = settingsobj.Settings()
        register = appsettings.register('test')
        register(Cheese)
        register(readonly=True)(RDOnly)
        register(Globals, main=True)

    def tearDown(self):
        settingsobj.Settings._reset()
        self.settings = None

    def testGroup(self):
        self.assert_(hasattr(self.settings, 'test'))

    def testHasSettings(self):
        settings = self.settings.test
        self.assert_(hasattr(settings, 'cheese'))
        self.assert_(hasattr(settings.cheese, 'color'))
        self.assert_(hasattr(settings.cheese, 'age'))
        self.assert_(hasattr(settings.cheese, 'type'))

    def testAutoMagic(self):
        settings = self.settings.test
        self.assert_(isinstance(settings.cheese._vals['color'], forms.CharField))
        self.assert_(isinstance(settings.cheese._vals['age'], forms.IntegerField))
        self.assert_(isinstance(settings.cheese._vals['type'], forms.ChoiceField))

    def testSetGet(self):
        settings = self.settings.test
        settings.cheese.color = 'blue'
        self.assertEquals(settings.cheese.color, 'blue')
        self.assertRaises(forms.ValidationError, settings.cheese.__setattr__, 'age', 'red')
        self.assertRaises(forms.ValidationError, settings.cheese.__setattr__, 'type', 4)
        self.assertRaises(forms.ValidationError, settings.cheese.__setattr__, 'type', 'blue')
        settings.cheese.type = 'american'
        self.assertEquals(settings.cheese.type, 'american')

    def testReadOnly(self):
        settings = self.settings.test
        self.assertRaises(AttributeError, settings.rdonly.__setattr__, 'version', 17)
        self.assertEquals(settings.rdonly.version, 4)

    def testNoGroup(self):
        settings = self.settings.test
        self.assertEquals(settings.spam, 'spamspamspam')
        self.assertEquals(settings.globals.spam, 'spamspamspam')


__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

import views

urlpatterns = patterns('',
        url(r'^$', views.app_index, name='index'),
        url(r'^(?P<app_name>[^/]+)/$', views.app_settings, name='app_settings'),
    )

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = user

class ProxyDict(object):
    def __init__(self, name, dct):
        self._name = name
        self._dct = dct[name] = {}
        self._proxies = {}
    def __getattr__(self, name):
        if name in ('_name', '_dct', '_proxies'):
            return super(ProxyDict, self).__getattr__(name)
        if not self._proxies.has_key(name):
            if name in self._dct:
                return self._dct[name]
            self._proxies[name] = ProxyDict(name, self._dct)
        return self._proxies[name]
    def __setattr__(self, name, val):
        if name in ('_name', '_dct', '_proxies'):
            return super(ProxyDict, self).__setattr__(name, val)
        self._dct[name] = val

settings = ProxyDict('main', {})

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.admin.views.decorators import staff_member_required
from settingsobj import Settings
settingsinst = Settings()
from models import Setting
import forms

@staff_member_required
def app_index(request, template = 'appsettings/index.html', base_template = 'index.html'):
    apps = sorted(vars(settingsinst).keys())
    return render_to_response(template, 
            {'apps':apps, 'base_template':base_template},
            RequestContext(request))

@staff_member_required
def app_settings(request, app_name=None, template = 'appsettings/settings.html', base_template = 'index.html'):
    editor = forms.settings_form()
    if request.POST:
        form = editor(request.POST)
        if form.is_valid():
            for key, value in form.fields.iteritems():
                app, group, name = key.split('-')
                val = form.cleaned_data[key]
                if val != getattr(settingsinst, app)._vals[group]._vals[name].initial:
                    setattr(getattr(settingsinst, app)._vals[group], name, val)
    else:
        initial = {}
        for app_name in sorted(vars(settingsinst).keys()):
            app = getattr(settingsinst, app_name)
            for group_name, group in app._vals.iteritems():
                if group._readonly:continue
                for key, value in group._vals.iteritems():
                    field_name = u'%s-%s-%s' % (app_name, group_name, key)
                    initial[field_name] = getattr(group, key)
        form = editor(initial)
    return render_to_response(template, 
                              {'app':app_name,'form':form, 'base_template':base_template},
                              context_instance=RequestContext(request))

########NEW FILE########
