__FILENAME__ = decorators
from django.conf import settings
from django.utils.encoding import smart_str

import pytz



default_tz = pytz.timezone(getattr(settings, "TIME_ZONE", "UTC"))



def localdatetime(field_name):
    def get_datetime(instance):
        return getattr(instance, field_name)
    def set_datetime(instance, value):
        return setattr(instance, field_name, value)
    def make_local_property(get_tz):
        def get_local(instance):
            tz = get_tz(instance)
            if not hasattr(tz, "localize"):
                tz = pytz.timezone(smart_str(tz))
            dt = get_datetime(instance)
            if dt.tzinfo is None:
                dt = default_tz.localize(dt)
            return dt.astimezone(tz)
        def set_local(instance, dt):
            if dt.tzinfo is None:
                tz = get_tz(instance)
                if not hasattr(tz, "localize"):
                    tz = pytz.timezone(smart_str(tz))
                dt = tz.localize(dt)
            dt = dt.astimezone(default_tz)
            return set_datetime(instance, dt)
        return property(get_local, set_local)
    return make_local_property

########NEW FILE########
__FILENAME__ = fields
from django.conf import settings
from django.db import models
from django.db.models import signals
from django.utils.encoding import smart_unicode, smart_str

import pytz

from timezones import forms, zones
from timezones.utils import coerce_timezone_value, validate_timezone_max_length



MAX_TIMEZONE_LENGTH = getattr(settings, "MAX_TIMEZONE_LENGTH", 100)
default_tz = pytz.timezone(getattr(settings, "TIME_ZONE", "UTC"))


class TimeZoneField(models.CharField):
    
    __metaclass__ = models.SubfieldBase
    
    def __init__(self, *args, **kwargs):
        validate_timezone_max_length(MAX_TIMEZONE_LENGTH, zones.ALL_TIMEZONE_CHOICES)
        defaults = {
            "max_length": MAX_TIMEZONE_LENGTH,
            "default": settings.TIME_ZONE,
            "choices": zones.PRETTY_TIMEZONE_CHOICES
        }
        defaults.update(kwargs)
        return super(TimeZoneField, self).__init__(*args, **defaults)
    
    def validate(self, value, model_instance):
        # coerce value back to a string to validate correctly
        return super(TimeZoneField, self).validate(smart_str(value), model_instance)
    
    def run_validators(self, value):
        # coerce value back to a string to validate correctly
        return super(TimeZoneField, self).run_validators(smart_str(value))
    
    def to_python(self, value):
        value = super(TimeZoneField, self).to_python(value)
        if value is None:
            return None # null=True
        return coerce_timezone_value(value)
    
    def get_prep_value(self, value):
        if value is not None:
            return smart_unicode(value)
        return value
    
    def get_db_prep_save(self, value, connection=None):
        """
        Prepares the given value for insertion into the database.
        """
        return self.get_prep_value(value)
    
    def flatten_data(self, follow, obj=None):
        value = self._get_val_from_obj(obj)
        if value is None:
            value = ""
        return {self.attname: smart_unicode(value)}


class LocalizedDateTimeField(models.DateTimeField):
    """
    A model field that provides automatic localized timezone support.
    timezone can be a timezone string, a callable (returning a timezone string),
    or a queryset keyword relation for the model, or a pytz.timezone()
    result.
    """
    def __init__(self, verbose_name=None, name=None, timezone=None, **kwargs):
        if isinstance(timezone, basestring):
            timezone = smart_str(timezone)
        if timezone in pytz.all_timezones_set:
            self.timezone = pytz.timezone(timezone)
        else:
            self.timezone = timezone
        super(LocalizedDateTimeField, self).__init__(verbose_name, name, **kwargs)
    
    def formfield(self, **kwargs):
        defaults = {"form_class": forms.LocalizedDateTimeField}
        if (not isinstance(self.timezone, basestring) and str(self.timezone) in pytz.all_timezones_set):
            defaults["timezone"] = str(self.timezone)
        defaults.update(kwargs)
        return super(LocalizedDateTimeField, self).formfield(**defaults)
    
    def get_db_prep_save(self, value, connection=None):
        """
        Returns field's value prepared for saving into a database.
        """
        ## convert to settings.TIME_ZONE
        if value is not None:
            if value.tzinfo is None:
                value = default_tz.localize(value)
            else:
                value = value.astimezone(default_tz)
        return super(LocalizedDateTimeField, self).get_db_prep_save(value, connection=connection)
    
    def get_db_prep_lookup(self, lookup_type, value, connection=None, prepared=None):
        """
        Returns field's value prepared for database lookup.
        """
        ## convert to settings.TIME_ZONE
        if value.tzinfo is None:
            value = default_tz.localize(value)
        else:
            value = value.astimezone(default_tz)
        return super(LocalizedDateTimeField, self).get_db_prep_lookup(lookup_type, value, connection=connection, prepared=prepared)


def prep_localized_datetime(sender, **kwargs):
    for field in sender._meta.fields:
        if not isinstance(field, LocalizedDateTimeField) or field.timezone is None:
            continue
        dt_field_name = "_datetimezone_%s" % field.attname
        def get_dtz_field(instance):
            return getattr(instance, dt_field_name)
        def set_dtz_field(instance, dt):
            if dt.tzinfo is None:
                dt = default_tz.localize(dt)
            time_zone = field.timezone
            if isinstance(field.timezone, basestring):
                tz_name = instance._default_manager.filter(
                    pk=model_instance._get_pk_val()
                ).values_list(field.timezone)[0][0]
                try:
                    time_zone = pytz.timezone(tz_name)
                except:
                    time_zone = default_tz
                if time_zone is None:
                    # lookup failed
                    time_zone = default_tz
                    #raise pytz.UnknownTimeZoneError(
                    #    "Time zone %r from relation %r was not found"
                    #    % (tz_name, field.timezone)
                    #)
            elif callable(time_zone):
                tz_name = time_zone()
                if isinstance(tz_name, basestring):
                    try:
                        time_zone = pytz.timezone(tz_name)
                    except:
                        time_zone = default_tz
                else:
                    time_zone = tz_name
                if time_zone is None:
                    # lookup failed
                    time_zone = default_tz
                    #raise pytz.UnknownTimeZoneError(
                    #    "Time zone %r from callable %r was not found"
                    #    % (tz_name, field.timezone)
                    #)
            setattr(instance, dt_field_name, dt.astimezone(time_zone))
        setattr(sender, field.attname, property(get_dtz_field, set_dtz_field))

## RED_FLAG: need to add a check at manage.py validation time that
##           time_zone value is a valid query keyword (if it is one)
signals.class_prepared.connect(prep_localized_datetime)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings

import pytz

from timezones import zones
from timezones.utils import adjust_datetime_to_timezone, coerce_timezone_value



class TimeZoneField(forms.TypedChoiceField):
    def __init__(self, *args, **kwargs):
        if not "choices" in kwargs:
            kwargs["choices"] = zones.PRETTY_TIMEZONE_CHOICES
        kwargs["coerce"] = coerce_timezone_value
        super(TimeZoneField, self).__init__(*args, **kwargs)


class LocalizedDateTimeField(forms.DateTimeField):
    """
    Converts the datetime from the user timezone to settings.TIME_ZONE.
    """
    def __init__(self, timezone=None, *args, **kwargs):
        super(LocalizedDateTimeField, self).__init__(*args, **kwargs)
        self.timezone = timezone or settings.TIME_ZONE
        
    def clean(self, value):
        value = super(LocalizedDateTimeField, self).clean(value)
        if value is None: # field was likely not required
            return None
        return adjust_datetime_to_timezone(value, from_tz=self.timezone)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = timezone_filters

from django.template import Node
from django.template import Library

from timezones.utils import localtime_for_timezone

register = Library()

def localtime(value, timezone):
    return localtime_for_timezone(value, timezone)
register.filter("localtime", localtime)


########NEW FILE########
__FILENAME__ = models
from django.db import models

from timezones.fields import TimeZoneField



class Profile(models.Model):
    name = models.CharField(max_length=100)
    timezone = TimeZoneField()

########NEW FILE########
__FILENAME__ = tests
import re

from datetime import datetime

import pytz

from django import forms
from django.conf import settings
from django.test import TestCase

import timezones.forms
import timezones.timezones_tests.models as test_models

from timezones.utils import localtime_for_timezone, adjust_datetime_to_timezone



class TimeZoneTestCase(TestCase):
    
    def setUp(self):
        # ensure UTC
        self.ORIGINAL_TIME_ZONE = settings.TIME_ZONE
        settings.TIME_ZONE = "UTC"
    
    def tearDown(self):
        settings.TIME_ZONE = self.ORIGINAL_TIME_ZONE
    
    # little helpers
    
    def assertFormIsValid(self, form):
        is_valid = form.is_valid()
        self.assert_(is_valid,
            "Form did not validate (errors=%r, form=%r)" % (form._errors, form)
        )


class UtilsTestCase(TimeZoneTestCase):
    
    def test_localtime_for_timezone(self):
        self.assertEqual(
            localtime_for_timezone(
                datetime(2008, 6, 25, 18, 0, 0), "America/Denver"
            ).strftime("%m/%d/%Y %H:%M:%S"),
            "06/25/2008 12:00:00"
        )
    
    def test_adjust_datetime_to_timezone(self):
        self.assertEqual(
            adjust_datetime_to_timezone(
                datetime(2008, 6, 25, 18, 0, 0), "UTC"
            ).strftime("%m/%d/%Y %H:%M:%S"),
            "06/25/2008 18:00:00"
        )


class TimeZoneFieldTestCase(TimeZoneTestCase):
    
    def test_forms_clean_required(self):
        f = timezones.forms.TimeZoneField()
        self.assertEqual(
            repr(f.clean("US/Eastern")),
            "<DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>"
        )
        self.assertRaises(forms.ValidationError, f.clean, "")
    
    def test_forms_clean_not_required(self):
        f = timezones.forms.TimeZoneField(required=False)
        self.assertEqual(
            repr(f.clean("US/Eastern")),
            "<DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>"
        )
        self.assertEqual(f.clean(""), "")
    
    def test_forms_clean_bad_value(self):
        f = timezones.forms.TimeZoneField()
        try:
            f.clean("BAD VALUE")
        except forms.ValidationError, e:
            self.assertEqual(e.messages, ["Select a valid choice. BAD VALUE is not one of the available choices."])
    
    def test_models_as_a_form(self):
        class ProfileForm(forms.ModelForm):
            class Meta:
                model = test_models.Profile
        form = ProfileForm()
        rendered = form.as_p()
        self.assert_(
            bool(re.search(r'<option value="[\w/]+">\([A-Z]+(?:\+|\-)\d{4}\)\s[\w/]+</option>', rendered)),
            "Did not find pattern in rendered form"
        )
    
    def test_models_modelform_validation(self):
        class ProfileForm(forms.ModelForm):
            class Meta:
                model = test_models.Profile
        form = ProfileForm({"name": "Brian Rosner", "timezone": "America/Denver"})
        self.assertFormIsValid(form)
    
    def test_models_modelform_save(self):
        class ProfileForm(forms.ModelForm):
            class Meta:
                model = test_models.Profile
        form = ProfileForm({"name": "Brian Rosner", "timezone": "America/Denver"})
        self.assertFormIsValid(form)
        p = form.save()
    
    def test_models_string_value(self):
        p = test_models.Profile(name="Brian Rosner", timezone="America/Denver")
        p.save()
        p = test_models.Profile.objects.get(pk=p.pk)
        self.assertEqual(p.timezone, pytz.timezone("America/Denver"))
    
    def test_models_string_value_lookup(self):
        test_models.Profile(name="Brian Rosner", timezone="America/Denver").save()
        qs = test_models.Profile.objects.filter(timezone="America/Denver")
        self.assertEqual(qs.count(), 1)
    
    def test_models_tz_value(self):
        tz = pytz.timezone("America/Denver")
        p = test_models.Profile(name="Brian Rosner", timezone=tz)
        p.save()
        p = test_models.Profile.objects.get(pk=p.pk)
        self.assertEqual(p.timezone, tz)
    
    def test_models_tz_value_lookup(self):
        test_models.Profile(name="Brian Rosner", timezone="America/Denver").save()
        qs = test_models.Profile.objects.filter(timezone=pytz.timezone("America/Denver"))
        self.assertEqual(qs.count(), 1)


class LocalizedDateTimeFieldTestCase(TimeZoneTestCase):
    
    def test_forms_clean_required(self):
        # the default case where no timezone is given explicitly. uses settings.TIME_ZONE.
        f = timezones.forms.LocalizedDateTimeField()
        self.assertEqual(
            repr(f.clean("2008-05-30 14:30:00")),
            "datetime.datetime(2008, 5, 30, 14, 30, tzinfo=<UTC>)"
        )
        self.assertRaises(forms.ValidationError, f.clean, "")
    
    def test_forms_clean_required(self):
        # the default case where no timezone is given explicitly. uses settings.TIME_ZONE.
        f = timezones.forms.LocalizedDateTimeField(required=False)
        self.assertEqual(
            repr(f.clean("2008-05-30 14:30:00")),
            "datetime.datetime(2008, 5, 30, 14, 30, tzinfo=<UTC>)"
        )
        self.assertEqual(f.clean(""), None)


# @@@ old doctests that have not been finished (largely due to needing to
# better understand how these bits were created and use-cases)
NOT_USED = {"API_TESTS": r"""
>>> class Foo(object):
...     datetime = datetime(2008, 6, 20, 23, 58, 17)
...     @decorators.localdatetime('datetime')
...     def localdatetime(self):
...         return 'Australia/Lindeman'
...
>>> foo = Foo()
>>> foo.datetime
datetime.datetime(2008, 6, 20, 23, 58, 17)
>>> foo.localdatetime
datetime.datetime(2008, 6, 21, 9, 58, 17, tzinfo=<DstTzInfo 'Australia/Lindeman' EST+10:00:00 STD>)
>>> foo.localdatetime = datetime(2008, 6, 12, 23, 50, 0)
>>> foo.datetime
datetime.datetime(2008, 6, 12, 13, 50, tzinfo=<UTC>)
>>> foo.localdatetime
datetime.datetime(2008, 6, 12, 23, 50, tzinfo=<DstTzInfo 'Australia/Lindeman' EST+10:00:00 STD>)
"""}
########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_str

import pytz


def localtime_for_timezone(value, timezone):
    """
    Given a ``datetime.datetime`` object in UTC and a timezone represented as
    a string, return the localized time for the timezone.
    """
    return adjust_datetime_to_timezone(value, settings.TIME_ZONE, timezone)


def adjust_datetime_to_timezone(value, from_tz, to_tz=None):
    """
    Given a ``datetime`` object adjust it according to the from_tz timezone
    string into the to_tz timezone string.
    """
    if to_tz is None:
        to_tz = settings.TIME_ZONE
    if value.tzinfo is None:
        if not hasattr(from_tz, "localize"):
            from_tz = pytz.timezone(smart_str(from_tz))
        value = from_tz.localize(value)
    return value.astimezone(pytz.timezone(smart_str(to_tz)))


def coerce_timezone_value(value):
    try:
        return pytz.timezone(value)
    except pytz.UnknownTimeZoneError:
        raise ValidationError("Unknown timezone")


def validate_timezone_max_length(max_length, zones):
    def reducer(x, y):
        return x and (len(y) <= max_length)
    if not reduce(reducer, zones, True):
        raise Exception("timezones.fields.TimeZoneField MAX_TIMEZONE_LENGTH is too small")

########NEW FILE########
__FILENAME__ = zones
from datetime import datetime

import pytz



ALL_TIMEZONE_CHOICES = tuple(zip(pytz.all_timezones, pytz.all_timezones))
COMMON_TIMEZONE_CHOICES = tuple(zip(pytz.common_timezones, pytz.common_timezones))
PRETTY_TIMEZONE_CHOICES = []

for tz in pytz.common_timezones:
    now = datetime.now(pytz.timezone(tz))
    ofs = now.strftime("%z")
    PRETTY_TIMEZONE_CHOICES.append((int(ofs), tz, "(GMT%s) %s" % (ofs, tz)))
PRETTY_TIMEZONE_CHOICES.sort()
for i in xrange(len(PRETTY_TIMEZONE_CHOICES)):
    PRETTY_TIMEZONE_CHOICES[i] = PRETTY_TIMEZONE_CHOICES[i][1:]

########NEW FILE########
