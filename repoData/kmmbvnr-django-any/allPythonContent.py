__FILENAME__ = auth
# -*- coding: utf-8 -*-
from django.contrib.auth.models import User, Permission, Group
from django_any import any_model

def any_user(password=None, permissions=[], groups=[], **kwargs):
    """
    Shortcut for creating Users

    Permissions could be a list of permission names

    If not specified, creates active, non superuser 
    and non staff user
    """

    is_active = kwargs.pop('is_active', True)
    is_superuser = kwargs.pop('is_superuser', False)
    is_staff = kwargs.pop('is_staff', False)

    user = any_model(User, is_active = is_active, is_superuser = is_superuser,
                     is_staff = is_staff, **kwargs)

    for group_name in groups :
        group = Group.objects.get(name=group_name)
        user.groups.add(group)

    for permission_name in permissions:
        app_label, codename = permission_name.split('.')
        permission = Permission.objects.get(
            content_type__app_label=app_label,
            codename=codename)
        user.user_permissions.add(permission)

    if password:
        user.set_password(password)
    
    user.save()
    return user


########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
# pylint: disable=W0613, C0103
"""
Django forms data generators

"""
import random
from datetime import date, datetime, time
from django import forms
from django.utils import formats
from django_any import xunit
from django_any.functions import valid_choices, split_model_kwargs, \
    ExtensionMethod

any_form = ExtensionMethod()
any_form_field = ExtensionMethod()


@any_form.register_default
def any_form_default(form_cls, **kwargs):
    """
    Returns tuple with form data and files
    """
    form_data = {}
    form_files = {}

    form_fields, fields_args = split_model_kwargs(kwargs)

    for name, field in form_cls.base_fields.iteritems():
        if name in form_fields:
            form_data[name] = kwargs[name]
        else:
            form_data[name] = any_form_field(field, **fields_args[name])

    return form_data, form_files


@any_form_field.decorator
def field_required_attribute(function):
    """
    Sometimes return None if field is not required

    >>> result = any_form_field(forms.BooleanField(required=False))
    >>> result in ['', 'True', 'False']
    True
    """
    def _wrapper(field, **kwargs):
        if not field.required and random.random < 0.1:
            return None
        return function(field, **kwargs)
    return _wrapper


@any_form_field.decorator
def field_choices_attibute(function):
    """
    Selection from field.choices
    """
    def _wrapper(field, **kwargs):
        if hasattr(field.widget, 'choices'):
            return random.choice(list(valid_choices(field.widget.choices)))
        return function(field, **kwargs)

    return _wrapper


@any_form_field.register(forms.BooleanField)
def boolean_field_data(field, **kwargs):
    """
    Return random value for BooleanField

    >>> result = any_form_field(forms.BooleanField())
    >>> type(result)
    <type 'str'>
    """
    return str(xunit.any_boolean())


@any_form_field.register(forms.CharField)
def char_field_data(field, **kwargs):
    """
    Return random value for CharField
    >>> result = any_form_field(forms.CharField(min_length=3, max_length=10))
    >>> type(result)
    <type 'str'>
    """
    min_length = kwargs.get('min_length', 1)
    max_length = kwargs.get('max_length', field.max_length or 255)    
    return xunit.any_string(min_length=field.min_length or min_length, 
                            max_length=field.max_length or max_length)


@any_form_field.register(forms.DecimalField)
def decimal_field_data(field, **kwargs):
    """
    Return random value for DecimalField

    >>> result = any_form_field(forms.DecimalField(max_value=100, min_value=11, max_digits=4, decimal_places = 2))
    >>> type(result)
    <type 'str'>
    >>> from decimal import Decimal
    >>> Decimal(result) >= 11, Decimal(result) <= Decimal('99.99')
    (True, True)
    """
    min_value = 0
    max_value = 10
    from django.core.validators import MinValueValidator, MaxValueValidator 
    for elem in field.validators:
        if isinstance(elem, MinValueValidator):
            min_value = elem.limit_value
        if isinstance(elem, MaxValueValidator):
            max_value = elem.limit_value
    if (field.max_digits and field.decimal_places):
        from decimal import Decimal
        max_value = min(max_value,
                        Decimal('%s.%s' % ('9'*(field.max_digits-field.decimal_places),
                                           '9'*field.decimal_places)))

    min_value = kwargs.get('min_value') or min_value
    max_value = kwargs.get('max_value') or max_value

    return str(xunit.any_decimal(min_value=min_value,
                             max_value=max_value,
                             decimal_places = field.decimal_places or 2))


@any_form_field.register(forms.EmailField)
def email_field_data(field, **kwargs):
    """
    Return random value for EmailField

    >>> result = any_form_field(forms.EmailField(min_length=10, max_length=30))
    >>> type(result)
    <type 'str'>
    >>> len(result) <= 30, len(result) >= 10
    (True, True)
    """
    max_length = 10
    if field.max_length:
        max_length = (field.max_length -5) / 2 
    min_length = 10
    if field.min_length:
        min_length = (field.min_length-4) / 2
    return "%s@%s.%s" % (
        xunit.any_string(min_length=min_length, max_length=max_length),
        xunit.any_string(min_length=min_length, max_length=max_length),
        xunit.any_string(min_length=2, max_length=3))


@any_form_field.register(forms.DateField)
def date_field_data(field, **kwargs):
    """
    Return random value for DateField

    >>> result = any_form_field(forms.DateField())
    >>> type(result)
    <type 'str'>
    """
    from_date = kwargs.get('from_date', date(1990, 1, 1))
    to_date = kwargs.get('to_date', date.today())
    
    date_format = random.choice(field.input_formats or formats.get_format('DATE_INPUT_FORMATS'))
                                
    return xunit.any_date(from_date=from_date, to_date=to_date).strftime(date_format)


@any_form_field.register(forms.DateTimeField)
def datetime_field_data(field, **kwargs):
    """
    Return random value for DateTimeField

    >>> result = any_form_field(forms.DateTimeField())
    >>> type(result)
    <type 'str'>
    """
    from_date = kwargs.get('from_date', datetime(1990, 1, 1))
    to_date = kwargs.get('to_date', datetime.today())
    date_format = random.choice(field.input_formats or formats.get_format('DATETIME_INPUT_FORMATS'))
    return xunit.any_datetime(from_date=from_date, to_date=to_date).strftime(date_format)


@any_form_field.register(forms.FloatField)
def float_field_data(field, **kwargs):
    """
    Return random value for FloatField

    >>> result = any_form_field(forms.FloatField(max_value=200, min_value=100))
    >>> type(result)
    <type 'str'>
    >>> float(result) >=100, float(result) <=200
    (True, True)
    """
    min_value = 0
    max_value = 100
    from django.core.validators import MinValueValidator, MaxValueValidator
    for elem in field.validators:
        if isinstance(elem, MinValueValidator):
            min_value = elem.limit_value
        if isinstance(elem, MaxValueValidator):
            max_value = elem.limit_value

    min_value = kwargs.get('min_value', min_value)
    max_value = kwargs.get('max_value', max_value)
    precision = kwargs.get('precision', 3)

    return str(xunit.any_float(min_value=min_value, max_value=max_value, precision=precision))


@any_form_field.register(forms.IntegerField)
def integer_field_data(field, **kwargs):
    """
    Return random value for IntegerField

    >>> result = any_form_field(forms.IntegerField(max_value=200, min_value=100))
    >>> type(result)
    <type 'str'>
    >>> int(result) >=100, int(result) <=200
    (True, True)
    """
    min_value = 0
    max_value = 100
    from django.core.validators import MinValueValidator, MaxValueValidator 
    for elem in field.validators:
        if isinstance(elem, MinValueValidator):
            min_value = elem.limit_value
        if isinstance(elem, MaxValueValidator):
            max_value = elem.limit_value

    min_value = kwargs.get('min_value', min_value)
    max_value = kwargs.get('max_value', max_value)

    return str(xunit.any_int(min_value=min_value, max_value=max_value))


@any_form_field.register(forms.IPAddressField)
def ipaddress_field_data(field, **kwargs):
    """
    Return random value for IPAddressField
    
    >>> result = any_form_field(forms.IPAddressField())
    >>> type(result)
    <type 'str'>
    >>> from django.core.validators import ipv4_re
    >>> import re
    >>> re.match(ipv4_re, result) is not None
    True
    """
    choices = kwargs.get('choices')
    if choices:
        return random.choice(choices)
    else:
        nums = [str(xunit.any_int(min_value=0, max_value=255)) for _ in xrange(0, 4)]
        return ".".join(nums)


@any_form_field.register(forms.NullBooleanField)
def null_boolean_field_data(field, **kwargs):
    """
    Return random value for NullBooleanField
    
    >>> result = any_form_field(forms.NullBooleanField())
    >>> type(result)
    <type 'unicode'>
    >>> result in [u'1', u'2', u'3']
    True
    """
    return random.choice(['None', 'True', 'False'])


@any_form_field.register(forms.SlugField)
def slug_field_data(field, **kwargs):
    """
    Return random value for SlugField
    
    >>> result = any_form_field(forms.SlugField())
    >>> type(result)
    <type 'str'>
    >>> from django.core.validators import slug_re
    >>> import re
    >>> re.match(slug_re, result) is not None
    True
    """
    min_length = kwargs.get('min_length', 1)
    max_length = kwargs.get('max_length', field.max_length or 20)    
    
    from string import ascii_letters, digits
    letters = ascii_letters + digits + '_-' 
    return xunit.any_string(letters = letters, min_length = min_length, max_length = max_length)


@any_form_field.register(forms.URLField)
def url_field_data(field, **kwargs):
    """
    Return random value for URLField
    
    >>> result = any_form_field(forms.URLField())
    >>> from django.core.validators import URLValidator
    >>> import re
    >>> re.match(URLValidator.regex, result) is not None
    True
    """
    urls = kwargs.get('choices',
                      ['http://news.yandex.ru/society.html',
                       'http://video.google.com/?hl=en&tab=wv',
                       'http://www.microsoft.com/en/us/default.aspx',
                       'http://habrahabr.ru/company/opera/',
                       'http://www.apple.com/support/hardware/',
                                        'http://localhost/',
                       'http://72.14.221.99',
                       'http://fr.wikipedia.org/wiki/France'])

    return random.choice(urls)


@any_form_field.register(forms.TimeField)
def time_field_data(field, **kwargs):
    """
    Return random value for TimeField

    >>> result = any_form_field(forms.TimeField())
    >>> type(result)
    <type 'str'>
    """
    time_format = random.choice(field.input_formats or formats.get_format('TIME_INPUT_FORMATS'))

    return time(xunit.any_int(min_value=0, max_value=23),
                xunit.any_int(min_value=0, max_value=59),
                xunit.any_int(min_value=0, max_value=59)).strftime(time_format)


@any_form_field.register(forms.TypedChoiceField)
@any_form_field.register(forms.ChoiceField)
def choice_field_data(field, **kwargs):
    """
    Return random value for ChoiceField

    >>> CHOICES = [('YNG', 'Child'), ('OLD', 'Parent')]
    >>> result = any_form_field(forms.ChoiceField(choices=CHOICES))
    >>> type(result)
    <type 'str'>
    >>> result in ['YNG', 'OLD']
    True
    >>> typed_result = any_form_field(forms.TypedChoiceField(choices=CHOICES))
    >>> typed_result in ['YNG', 'OLD']
    True
    """
    if field.choices:
        return str(random.choice(list(valid_choices(field.choices))))
    return 'None'


@any_form_field.register(forms.MultipleChoiceField)
def multiple_choice_field_data(field, **kwargs):
    """
    Return random value for MultipleChoiceField

    >>> CHOICES = [('YNG', 'Child'), ('MIDDLE', 'Parent') ,('OLD', 'GrandParent')]
    >>> result = any_form_field(forms.MultipleChoiceField(choices=CHOICES))
    >>> type(result)
    <type 'str'>
    """
    if field.choices:
        from django_any.functions import valid_choices 
        l = list(valid_choices(field.choices))
        random.shuffle(l)
        choices = []
        count = xunit.any_int(min_value=1, max_value=len(field.choices))
        for i in xrange(0, count):
            choices.append(l[i])
        return ' '.join(choices)
    return 'None'


@any_form_field.register(forms.models.ModelChoiceField)
def model_choice_field_data(field, **kwargs):
    """
    Return one of first ten items for field queryset
    """
    data = list(field.queryset[:10])
    if data:
        return random.choice(data)
    else:
        raise TypeError('No %s available in queryset' % field.queryset.model)


########NEW FILE########
__FILENAME__ = functions
#-*- coding: utf-8 -*-
"""
Additional functions for django-any
"""

def valid_choices(choices):
    """
    Return list of choices's keys
    """
    for key, value in choices:
        if isinstance(value, (list, tuple)):
            for key, _ in value:
                yield key
        else:
            yield key


def split_model_kwargs(kw):
    """
    django_any birds language parser
    """
    from collections import defaultdict
    
    model_fields = {}
    fields_agrs = defaultdict(lambda : {})
    
    for key in kw.keys():
        if '__' in key:
            field, _, subfield = key.partition('__')
            fields_agrs[field][subfield] = kw[key]
        else:
            model_fields[key] = kw[key]

    return model_fields, fields_agrs


class ExtensionMethod(object):
    """
    Works like one parameter multimethod
    """
    def __init__(self, by_instance=False):
        self.registry = {}
        self.by_instance = by_instance
        self.default = None

    def register(self, field_type, impl=None):
        """
        Register form field data function.
        
        Could be used as decorator
        """
        def _wrapper(func):
            self.registry[field_type] = func
            return func

        if impl:
            return _wrapper(impl)
        return _wrapper
    
    def register_default(self, func):
        self.default = func
        return func

    def decorator(self, impl):
        """
        Decorator for register decorators
        """
        self._create_value = impl(self._create_value)
        return impl

    def _create_value(self, *args, **kwargs):
        """
        Lowest value generator.

        Separated from __call__, because it seems that python
        cache __call__ reference on module import
        """
        if not len(args):
            raise TypeError('Object instance is not provided')

        if self.by_instance:
            field_type = args[0]
        else:
            field_type = args[0].__class__

        function = self.registry.get(field_type, self.default)

        if function is None:
            raise TypeError("no match %s" % field_type)

        return function(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self._create_value(*args, **kwargs)


########NEW FILE########
__FILENAME__ = models
#-*- coding: utf-8 -*-
# pylint: disable=E0102, W0613
"""
Values generators for common Django Fields
"""
import re, os, random
from decimal import Decimal
from datetime import date, datetime, time
from string import ascii_letters, digits
from random import choice

from django.core.exceptions import ValidationError
from django.core import validators
from django.db import models, IntegrityError
from django.db.models import Q
from django.db.models.fields.files import FieldFile
from django.contrib.webdesign.lorem_ipsum import paragraphs

from django_any import xunit
from django_any.functions import valid_choices, split_model_kwargs, \
    ExtensionMethod

any_field = ExtensionMethod()
any_model = ExtensionMethod(by_instance=True)

@any_field.decorator
def any_field_blank(function):
    """
    Sometimes return None if field could be blank
    """
    def wrapper(field, **kwargs):
        if kwargs.get('isnull', False):
            return None
    
        if field.blank and random.random < 0.1:
            return None
        return function(field, **kwargs)
    return wrapper


@any_field.decorator
def any_field_choices(function):
    """
    Selection from field.choices

    >>> CHOICES = [('YNG', 'Child'), ('OLD', 'Parent')]
    >>> result = any_field(models.CharField(max_length=3, choices=CHOICES))
    >>> result in ['YNG', 'OLD']
    True
    """
    def wrapper(field, **kwargs):
        if field.choices:
            return random.choice(list(valid_choices(field.choices)))
        return function(field, **kwargs)

    return wrapper


@any_field.register(models.BigIntegerField)
def any_biginteger_field(field, **kwargs):
    """
    Return random value for BigIntegerField

    >>> result = any_field(models.BigIntegerField())
    >>> type(result)
    <type 'long'>
    """
    min_value = kwargs.get('min_value', 1)
    max_value = kwargs.get('max_value', 10**10)
    return long(xunit.any_int(min_value=min_value, max_value=max_value))


@any_field.register(models.BooleanField)
def any_boolean_field(field, **kwargs):
    """
    Return random value for BooleanField

    >>> result = any_field(models.BooleanField())
    >>> type(result)
    <type 'bool'>
    """
    return xunit.any_boolean()


@any_field.register(models.PositiveIntegerField)
def any_positiveinteger_field(field, **kwargs):
    """
    An positive integer

    >>> result = any_field(models.PositiveIntegerField())
    >>> type(result)
    <type 'int'>
    >>> result > 0
    True
    """
    min_value = kwargs.get('min_value', 1)
    max_value = kwargs.get('max_value', 9999)
    return xunit.any_int(min_value=min_value, max_value=max_value)


@any_field.register(models.CharField)
def any_char_field(field, **kwargs):
    """
    Return random value for CharField

    >>> result = any_field(models.CharField(max_length=10))
    >>> type(result)
    <type 'str'>
    """
    min_length = kwargs.get('min_length', 1)
    max_length = kwargs.get('max_length', field.max_length)
    return xunit.any_string(min_length=min_length, max_length=max_length)


@any_field.register(models.CommaSeparatedIntegerField)
def any_commaseparatedinteger_field(field, **kwargs):
    """
    Return random value for CharField

    >>> result = any_field(models.CommaSeparatedIntegerField(max_length=10))
    >>> type(result)
    <type 'str'>
    >>> [int(num) for num in result.split(',')] and 'OK'
    'OK'
    """
    nums_count = field.max_length/2
    nums = [str(xunit.any_int(min_value=0, max_value=9)) for _ in xrange(0, nums_count)]
    return ",".join(nums)


@any_field.register(models.DateField)
def any_date_field(field, **kwargs):
    """
    Return random value for DateField,
    skips auto_now and auto_now_add fields

    >>> result = any_field(models.DateField())
    >>> type(result)
    <type 'datetime.date'>
    """
    if field.auto_now or field.auto_now_add:
        return None
    from_date = kwargs.get('from_date', date(1990, 1, 1))
    to_date = kwargs.get('to_date', date.today())
    return xunit.any_date(from_date=from_date, to_date=to_date)


@any_field.register(models.DateTimeField)
def any_datetime_field(field, **kwargs):
    """
    Return random value for DateTimeField,
    skips auto_now and auto_now_add fields

    >>> result = any_field(models.DateTimeField())
    >>> type(result)
    <type 'datetime.datetime'>
    """
    from_date = kwargs.get('from_date', datetime(1990, 1, 1))
    to_date = kwargs.get('to_date', datetime.today())
    return xunit.any_datetime(from_date=from_date, to_date=to_date)


@any_field.register(models.DecimalField)
def any_decimal_field(field, **kwargs):
    """
    Return random value for DecimalField

    >>> result = any_field(models.DecimalField(max_digits=5, decimal_places=2))
    >>> type(result)
    <class 'decimal.Decimal'>
    """
    min_value = kwargs.get('min_value', 0)
    max_value = kwargs.get('max_value',
                           Decimal('%s.%s' % ('9'*(field.max_digits-field.decimal_places),
                                              '9'*field.decimal_places)))
    decimal_places = kwargs.get('decimal_places', field.decimal_places)
    return xunit.any_decimal(min_value=min_value, max_value=max_value,
                             decimal_places = decimal_places)


@any_field.register(models.EmailField)
def any_email_field(field, **kwargs):
    """
    Return random value for EmailField

    >>> result = any_field(models.EmailField())
    >>> type(result)
    <type 'str'>
    >>> re.match(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", result, re.IGNORECASE) is not None
    True
    """
    return "%s@%s.%s" % (xunit.any_string(max_length=10),
                         xunit.any_string(max_length=10),
                         xunit.any_string(min_length=2, max_length=3))


@any_field.register(models.FloatField)
def any_float_field(field, **kwargs):
    """
    Return random value for FloatField

    >>> result = any_field(models.FloatField())
    >>> type(result)
    <type 'float'>
    """
    min_value = kwargs.get('min_value', 1)
    max_value = kwargs.get('max_value', 100)
    precision = kwargs.get('precision', 3)
    return xunit.any_float(min_value=min_value, max_value=max_value, precision=precision)


@any_field.register(models.FileField)
def any_file_field(field, **kwargs):
    """
    Lookup for nearest existing file

    """
    def get_some_file(path):
        subdirs, files = field.storage.listdir(path)

        if files:
            result_file = random.choice(files)
            instance = field.storage.open("%s/%s" % (path, result_file)).file
            return FieldFile(instance, field, result_file)

        for subdir in subdirs:
            result = get_some_file("%s/%s" % (path, subdir))
            if result:
                return result
            
    result = get_some_file(field.upload_to)

    if result is None and not field.null:
        raise TypeError("Can't found file in %s for non nullable FileField" % field.upload_to)
    return result


@any_field.register(models.FilePathField)
def any_filepath_field(field, **kwargs):
    """
    Lookup for nearest existing file

    """
    def get_some_file(path):
        subdirs, files = [], []
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            if os.path.isdir(entry_path):
                subdirs.append(entry_path)
            else:
                if not field.match or re.match(field.match,entry):
                    files.append(entry_path)

        if files:
            return random.choice(files)
        
        if field.recursive:
            for subdir in subdirs:
                result = get_some_file(subdir)
                if result:
                    return result

    result = get_some_file(field.path)
    if result is None and not field.null:
        raise TypeError("Can't found file in %s for non nullable FilePathField" % field.path)
    return result


@any_field.register(models.IPAddressField)
def any_ipaddress_field(field, **kwargs):
    """
    Return random value for IPAddressField
    >>> result = any_field(models.IPAddressField())
    >>> type(result)
    <type 'str'>
    >>> from django.core.validators import ipv4_re
    >>> re.match(ipv4_re, result) is not None
    True
    """
    nums = [str(xunit.any_int(min_value=0, max_value=255)) for _ in xrange(0, 4)]
    return ".".join(nums)


@any_field.register(models.NullBooleanField)
def any_nullboolean_field(field, **kwargs):
    """
    Return random value for NullBooleanField
    >>> result = any_field(models.NullBooleanField())
    >>> result in [None, True, False]
    True
    """
    return random.choice([None, True, False])


@any_field.register(models.PositiveSmallIntegerField)
def any_positivesmallinteger_field(field, **kwargs):
    """
    Return random value for PositiveSmallIntegerField
    >>> result = any_field(models.PositiveSmallIntegerField())
    >>> type(result)
    <type 'int'>
    >>> result < 256, result > 0
    (True, True)
    """
    min_value = kwargs.get('min_value', 1)
    max_value = kwargs.get('max_value', 255)
    return xunit.any_int(min_value=min_value, max_value=max_value)


@any_field.register(models.SlugField)
def any_slug_field(field, **kwargs):
    """
    Return random value for SlugField
    >>> result = any_field(models.SlugField())
    >>> type(result)
    <type 'str'>
    >>> from django.core.validators import slug_re
    >>> re.match(slug_re, result) is not None
    True
    """
    letters = ascii_letters + digits + '_-'
    return xunit.any_string(letters = letters, max_length = field.max_length)


@any_field.register(models.SmallIntegerField)
def any_smallinteger_field(field, **kwargs):
    """
    Return random value for SmallIntegerValue
    >>> result = any_field(models.SmallIntegerField())
    >>> type(result)
    <type 'int'>
    >>> result > -256, result < 256
    (True, True)
    """
    min_value = kwargs.get('min_value', -255)
    max_value = kwargs.get('max_value', 255)
    return xunit.any_int(min_value=min_value, max_value=max_value)


@any_field.register(models.IntegerField)
def any_integer_field(field, **kwargs):
    """
    Return random value for IntegerField
    >>> result = any_field(models.IntegerField())
    >>> type(result)
    <type 'int'>
    """
    min_value = kwargs.get('min_value', -10000)
    max_value = kwargs.get('max_value', 10000)
    return xunit.any_int(min_value=min_value, max_value=max_value)


@any_field.register(models.TextField)
def any_text_field(field, **kwargs):
    """
    Return random 'lorem ipsum' Latin text
    >>> result = any_field(models.TextField())
    >>> from django.contrib.webdesign.lorem_ipsum import COMMON_P
    >>> result[0] == COMMON_P
    True
    """
    return paragraphs(10)


@any_field.register(models.URLField)
def any_url_field(field, **kwargs):
    """
    Return random value for URLField
    >>> result = any_field(models.URLField())
    >>> from django.core.validators import URLValidator
    >>> re.match(URLValidator.regex, result) is not None
    True
    """
    url = kwargs.get('url')

    if not url:
        verified = [validator for validator in field.validators \
                    if isinstance(validator, validators.URLValidator) and \
                    validator.verify_exists == True]
        if verified:
            url = choice(['http://news.yandex.ru/society.html',
                          'http://video.google.com/?hl=en&tab=wv',
                          'http://www.microsoft.com/en/us/default.aspx',
                          'http://habrahabr.ru/company/opera/',
                          'http://www.apple.com/support/hardware/',
                          'http://ya.ru',
                          'http://google.com',
                          'http://fr.wikipedia.org/wiki/France'])
        else:
            url = "http://%s.%s/%s" % (
                xunit.any_string(max_length=10),
                xunit.any_string(min_length=2, max_length=3),
                xunit.any_string(max_length=20))

    return url


@any_field.register(models.TimeField)
def any_time_field(field, **kwargs):
    """
    Return random value for TimeField
    >>> result = any_field(models.TimeField())
    >>> type(result)
    <type 'datetime.time'>
    """
    return time(
        xunit.any_int(min_value=0, max_value=23),
        xunit.any_int(min_value=0, max_value=59),
        xunit.any_int(min_value=0, max_value=59))


@any_field.register(models.ForeignKey)
def any_foreignkey_field(field, **kwargs):
    return any_model(field.rel.to, **kwargs)


@any_field.register(models.OneToOneField)
def any_onetoone_field(field, **kwargs):
    return any_model(field.rel.to, **kwargs)


def _fill_model_fields(model, **kwargs):
    model_fields, fields_args = split_model_kwargs(kwargs)

    # fill local fields
    for field in model._meta.fields:
        if field.name in model_fields:
            if isinstance(kwargs[field.name], Q):
                """
                Lookup ForeingKey field in db
                """
                key_field = model._meta.get_field(field.name)
                value = key_field.rel.to.objects.get(kwargs[field.name])
                setattr(model, field.name, value)
            else:
                # TODO support any_model call
                setattr(model, field.name, kwargs[field.name])
        elif isinstance(field, models.OneToOneField) and field.rel.parent_link:
            """
            skip link to parent instance
            """
        elif isinstance(field, models.fields.AutoField):
            """
            skip primary key field
            """
        else:
            setattr(model, field.name, any_field(field, **fields_args[field.name]))

    # procceed reversed relations
    onetoone = [(relation.var_name, relation.field) \
                for relation in model._meta.get_all_related_objects() \
                if relation.field.unique] # TODO and not relation.field.rel.parent_link ??
    for field_name, field in onetoone:
        if field_name in model_fields:
            # TODO support any_model call
            setattr(model, field_name, kwargs[field_name])


@any_model.register_default
def any_model_default(model_cls, **kwargs):
    result = model_cls()

    attempts = 10
    while True:
        try:
            _fill_model_fields(result, **kwargs)
            result.full_clean()
            result.save()
            return result
        except (IntegrityError, ValidationError):
            attempts -= 1
            if not attempts:
                raise


########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
import time, random
from unittest import _strclass
from django import forms
from django_any import any_form
from django.test.client import Client as DjangoClient
from django_any.contrib.auth import any_user
from django.contrib.admin.helpers import AdminForm
from django_any import xunit


def _context_keys_iterator(context):
    for container_or_key in context:
        if isinstance(container_or_key, basestring):
            yield container_or_key
        else:
            for key in _context_keys_iterator(container_or_key):
                yield key


def _request_context_forms(context):
    """
    Lookup all stored in context froms instance
    """
    for key in _context_keys_iterator(context):
        inst = context[key]
        if isinstance(inst, (forms.Form, forms.ModelForm)):
            yield inst
        elif isinstance(inst,  forms.formsets.BaseFormSet):
            yield inst
        elif isinstance(inst, AdminForm):
            yield inst.form


class Client(DjangoClient):
    def login_as(self, **kwargs):
        password = xunit.any_string()
        user = any_user(password=password, **kwargs)

        if self.login(username=user.username, password=password):
            return user
        raise AssertionError('Can''t login with autogenerated user')

    def post_any_data(self, url, extra=None, context_forms=_request_context_forms, **kwargs):
        response = self.get(url)

        post_data = {}

        # extract foms instances
        if callable(context_forms):
            forms_list = context_forms(response.context)
        elif isinstance(context_forms, (list, tuple)):
            forms_list = [response.context[form_name] for form_name in context_forms]
        else:
            raise TypeError('context_forms should be callable or list or tuple, not %s' % type(context_forms).__name__)

        # generate data
        for form in forms_list:
            if isinstance(form, forms.formsets.BaseFormSet): # TODO any_form ExtensionMethod
                #TODO support formset data
                form_data = form.management_form.initial
                form_data['MAX_NUM_FORMS'] = 0
            else:
                form_data, form_files = any_form(form.__class__, **kwargs) #TODO support form instance

            if form.prefix:
                form_data = dict([('%s-%s' % (form.prefix, key), value) for key, value in form_data.items()])

            post_data.update(form_data)

        if extra:
            post_data.update(extra)

        return self.post(url, post_data)


def without_random_seed(func):
    """
    Marks that test method do not need to be started with random seed
    """
    func.__django_any_without_random_seed = True
    return func


def with_seed(seed):
    """
    Marks that test method do not need to be started with specific seed
    """
    def _wrapper(func):
        seeds = getattr(func, '__django_any_with_seed', [])
        seeds.append(seed)
        func.__django_any_with_seed = seeds
        return func
    return _wrapper


def set_seed(func, seed=None):
    """
    Set randon seed before executing function. If seed is 
    not provided current timestamp used
    """
    def _wrapper(self, seed=seed, *args, **kwargs):
        self.__django_any_seed = seed if seed else int(time.time()*1000)
        random.seed(self.__django_any_seed)
        return func(self, *args, **kwargs)
    return _wrapper


class WithTestDataSeed(type):
    """
    Metaclass for TestCases, manages random tests run
    """
    def __new__(cls, cls_name, bases, attrs):
        attrs['__django_any_seed'] = 0

        def shortDescription(self):            
            return "%s (%s) With seed %s" % (self._testMethodName,  _strclass(self.__class__), getattr(self, '__django_any_seed'))

        for name, func in attrs.items():
            if name.startswith('test') and hasattr(func, '__call__'):
                if getattr(func, '__django_any_without_random_seed', False):
                    del attrs[name]
                else:
                    attrs[name] = set_seed(func)

                for seed in getattr(func, '__django_any_with_seed', []):
                    attrs['%s_%d' % (name, seed)] = set_seed(func, seed)
                
        testcase = super(WithTestDataSeed, cls).__new__(cls, cls_name, bases, attrs)
        testcase.shortDescription = shortDescription
        return testcase
    

########NEW FILE########
__FILENAME__ = contrib_any_user
# -*- coding: utf-8; mode: django -*-
from django.db import models
from django.contrib.auth.models import User
from django.test import TestCase
from django_any import any_model
from django_any.contrib.auth import any_user


class CustomPermission(models.Model):
    name = models.CharField(max_length=5)

    class Meta:
        app_label = 'django_any'


class AnyUser(TestCase):
    def test_raw_user_creation(self):
        result = any_model(User)
        self.assertEqual(type(result), User)

    def test_create_superuser(self):
        user = any_user(is_superuser=True)
        self.assertTrue(user.is_superuser)

    def test_create_with_permissions(self):
        user = any_user(permissions= ['django_any.add_custompermission',
                                      'django_any.delete_custompermission'])

        self.assertTrue(user.has_perm('django_any.add_custompermission'))
        self.assertTrue(user.has_perm('django_any.delete_custompermission'))
        self.assertFalse(user.has_perm('django_any.change_custompermission'))


########NEW FILE########
__FILENAME__ = field_attr_choices
# -*- coding: utf-8; mode: django -*-
"""
https://docs.djangoproject.com/en/1.3/ref/models/fields/#choices
"""
from django.test import TestCase
from django.db import models
from django_any import any_field

class AttrChoices(TestCase):
    def test_one_case_selection(self):
        """
        Even there is only one choice, it should be returned always
        """
        field = models.BooleanField(choices=[
            (False, 'This sentence is wrong')])

        result = any_field(field)

        self.assertEqual(bool, type(result))
        self.assertEqual(False, result)

    def test_choices_named_groups_support(self):
        """
        Group names completely ignored
        """
        MEDIA_CHOICES = (
            ('Audio', (
                    ('vinyl', 'Vinyl'),
                    ('cd', 'CD'),
                    )),
            ('Video', (
                    ('vhs', 'VHS Tape'),
                    ('dvd', 'DVD'),
                    )),
            ('unknown', 'Unknown'))
        media = models.CharField(max_length=25, choices=MEDIA_CHOICES)

        result = any_field(media)

        self.assertTrue(result in ['vinyl', 'cd', 'vhs', 'dvd', 'unknown'])


########NEW FILE########
__FILENAME__ = model_creation_constraint
# -*- coding: utf-8; mode: django -*-
"""
Models that have custom validation checks
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django_any import any_model


class ModelWithConstraint(models.Model):
    """
    Validates that start_time is always before end_time
    """
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def clean(self):
        if self.start_time > self.end_time:
            raise ValidationError('start_time could not be after end_time')

    class Meta:
        app_label = 'django_any'


class ModelWithConstraintOnForeignKey(models.Model):
    timestamp = models.ForeignKey(ModelWithConstraint)

    class Meta:
        app_label = 'django_any'


class PassModelValidation(TestCase):
    def test_model_creation_succeed(self):
        result = any_model(ModelWithConstraint)
        self.assertTrue(result.start_time <= result.end_time)

    def test_foreignkey_constraint_succeed(self):
        result = any_model(ModelWithConstraintOnForeignKey)
        self.assertTrue(result.timestamp.start_time <= result.timestamp.end_time)


########NEW FILE########
__FILENAME__ = model_creation_simple
# -*- coding: utf-8; mode: django -*-
"""
Create models will all fields with simply to generate values
"""
from django.db import models
from django.test import TestCase
from django_any import any_model

class SimpleModel(models.Model):
    big_integer_field = models.BigIntegerField()
    char_field = models.CharField(max_length=5)
    boolean_field = models.BooleanField()
    comma_separated_field = models.CommaSeparatedIntegerField(max_length=50)
    date_field = models.DateField()
    datetime_field = models.DateTimeField()
    decimal_field = models.DecimalField(decimal_places=2, max_digits=10)
    email_field = models.EmailField()
    float_field = models.FloatField()
    integer_field = models.IntegerField()
    ip_field = models.IPAddressField()
    null_boolead_field = models.NullBooleanField()
    positive_integer_field = models.PositiveIntegerField()
    small_integer = models.PositiveSmallIntegerField()
    slig_field = models.SlugField()
    text_field = models.TextField()
    time_field = models.TimeField()
    url_field = models.URLField(verify_exists=False)

    class Meta:
        app_label = 'django_any'


class SimpleCreation(TestCase):
    def test_model_creation_succeed(self):
        result = any_model(SimpleModel)
        
        self.assertEqual(type(result), SimpleModel)

        for field in result._meta.fields:
            value = getattr(result, field.name)
        self.assertTrue(value is not None, "%s is uninitialized" % field.name)

    def _test_partial_specification(self):
        result = any_model(SimpleModel, char_field='test')
        self.assertEqual(result.char_field, 'test')

########NEW FILE########
__FILENAME__ = model_field_validatiors
# -*- coding: utf-8; mode: django -*-
"""
Test model creation with custom field validation
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django_any import any_model


def validate_even(value):
    if value % 2 != 0:
        raise ValidationError(u'%s is not an even number' % value)


class ModelWithValidatedField(models.Model):
    even_field = models.PositiveIntegerField(validators=[validate_even])

    class Meta:
        app_label = 'django_any'    


class PassFieldValidation(TestCase):
    def test_created_value_pass_validation(self):
        result = any_model(ModelWithValidatedField)
        validate_even(result.even_field)


########NEW FILE########
__FILENAME__ = model_foreign_key
# -*- coding: utf-8; mode: django -*-
"""
Auto-create foreingkey referencies
"""
from django.db import models
from django.test import TestCase
from django_any import any_model


class RelatedModel(models.Model):
    name = models.CharField(max_length=5)

    class Meta:
        app_label = 'django_any'


class BaseModel(models.Model):
    related = models.ForeignKey(RelatedModel)

    class Meta:
        app_label = 'django_any'


class ForeignKeyCreation(TestCase):
    def test_fk_relation_autocreate(self):
        result = any_model(BaseModel)

        self.assertEqual(type(result), BaseModel)

        self.assertEqual(type(result.related), RelatedModel)
        self.assertTrue(result.related.name is not None)

    def test_nested_models_specification(self):
        result = any_model(BaseModel, related__name='test')
        self.assertEqual(result.related.name, 'test')


########NEW FILE########
__FILENAME__ = model_oneto_one
# -*- coding: utf-8; mode: django -*-
"""
Shortcuts for onetoone model fields
"""
from django.db import models
from django.test import TestCase
from django_any import any_model


class OneToOneRelated(models.Model):
    name = models.CharField(max_length=5)

    class Meta:
        app_label = 'django_any'


class ModelWithOneToOneField(models.Model):
    name = models.CharField(max_length=5)
    related = models.OneToOneField(OneToOneRelated)

    class Meta:
        app_label = 'django_any'


class OneToOneCreation(TestCase):
    def test_oneto_one_autocreate(self):
        result = any_model(ModelWithOneToOneField)
        self.assertEqual(type(result), ModelWithOneToOneField)
        self.assertTrue(result.name is not None)

        self.assertEqual(type(result.related), OneToOneRelated)
        self.assertTrue(result.related.name is not None)

    def test_related_onetoone_not_created_by_default(self):
        simple_model = any_model(OneToOneRelated)
        self.assertRaises(ModelWithOneToOneField.DoesNotExist,
                          lambda : simple_model.modelwithonetoonefield)

    def test_related_specification_succeed(self):
        related = any_model(OneToOneRelated)
        result = any_model(ModelWithOneToOneField, related=related)
        self.assertEqual(related, result.related)

    def test_partial_specification_succeed(self):
        result = any_model(ModelWithOneToOneField, related__name='test')
        self.assertEqual(result.related.name, 'test')

    # TODO Create model for reverse relation
    def _test_reverse_relation_spec_succeed(self):
        related = any_model(OneToOneRelated, modelwithonetoonefield__name='test')
        self.assertEqual(related.modelwithonetoonefield.name, 'test')


########NEW FILE########
__FILENAME__ = model_qobjects_spec
# -*- coding: utf-8; mode: django -*-
"""
Allow partial specifications with q objects
"""
from django.db import models
from django.db.models import Q
from django.test import TestCase
from django_any import any_model


class QObjectRelated(models.Model):
    class Meta:
        app_label = 'django_any'


class RelatedToQObject(models.Model):
    related = models.ForeignKey(QObjectRelated)

    class Meta:
        app_label = 'django_any'
    

class QObjectsSupport(TestCase):
    def setUp(self):
        self.related = any_model(QObjectRelated)
        
    def test_qobject_specification(self):
        result = any_model(RelatedToQObject, related=Q(pk=self.related.pk))
        self.assertEqual(self.related, result.related)


########NEW FILE########
__FILENAME__ = model_redefine_creation
# -*- coding: utf-8; mode: django -*-
from django.db import models
from django.test import TestCase
from django_any import any_model


class Redefined(models.Model):
    name = models.CharField(max_length=5)

    class Meta:
        app_label = 'django_any'


class RelatedToRedefined(models.Model):
    related = models.ForeignKey(Redefined)

    class Meta:
        app_label = 'django_any'


@any_model.register(Redefined)
def any_redefined_model(model_cls, **kwargs):
    kwargs['name'] = kwargs.get('name', 'test')  
    return any_model.default(model_cls, **kwargs)


class RedefinedCreation(TestCase):
    def test_redefined_creation(self):        
        result = any_model(Redefined)
        self.assertEqual(result.name, 'test')

    def test_redefined_creation_partial_specification(self):
        result = any_model(Redefined, name="test2")
        self.assertEqual(result.name, 'test2')

    # TODO Fix model factory registration
    def _test_create_related_redefied(self):
        result = any_model(RelatedToRedefined)
        self.assertEqual(result.related.name, 'test')

########NEW FILE########
__FILENAME__ = test_client
# -*- coding: utf-8; mode: django -*-
from django.conf.urls.defaults import patterns, include
from django.contrib import admin
from django.test import TestCase
from django_any.test import Client

def view(request):
    """
    Test view that returning form
    """
    from django import forms
    from django.http import HttpResponse
    from django.shortcuts import redirect
    from django.template import Context, Template

    class TestForm(forms.Form):
        name = forms.CharField()

    if request.POST:
        form = TestForm(request.POST)
        if form.is_valid():
            return redirect('/view/')
    else:
        form = TestForm()

    template = Template("{{ form }}")
    context = Context({'form' : form})

    return HttpResponse(template.render(context))


urlpatterns = patterns('',
     (r'^admin/', include(admin.site.urls)),
     (r'^view/', view),
)


class DjangoAnyClient(TestCase):
    urls = 'django_any.tests.test_client'

    def setUp(self):
        self.client = Client()

    def test_login_as_super_user(self):
        self.assertTrue(self.client.login_as(is_superuser=True))

        response = self.client.get('/admin/')
        self.assertEquals(200, response.status_code)

    def test_post_any_data(self):
        response = self.client.post_any_data('/view/')
        self.assertRedirects(response, '/view/')


########NEW FILE########
__FILENAME__ = test_custom_seed
# -*- coding: utf-8; mode: django -*-
from django.db import models
from django.test import TestCase
from django_any import any_field
from django_any.test import WithTestDataSeed, with_seed, without_random_seed


class CustomSeed(TestCase):
    __metaclass__ = WithTestDataSeed

    @without_random_seed
    @with_seed(1)
    def test_deterministic_string(self):
        media = models.CharField(max_length=25)
        result = any_field(media)
        self.assertEqual('SNnz', result)

########NEW FILE########
__FILENAME__ = xunit
#-*- coding: utf-8 -*-
"""
The python basic types generators
"""
import random
from string import ascii_letters
from datetime import date, datetime, timedelta
from decimal import Decimal

def weighted_choice(choices):
    """
    Supposes that choices is sequence of two elements items,
    where first one is the probability and second is the
    result object or callable

    >>> result = weighted_choice([(20,'x'), (100, 'y')])
    >>> result in ['x', 'y']
    True
    """
    total = sum([weight for (weight, _) in choices])
    i = random.randint(0, total - 1)
    for weight, choice in choices:
        i -= weight
        if i < 0: 
            if callable(choice):
                return choice()
            return choice
    raise Exception('Bug')


def any_boolean():
    """
    Returns True or False
    
    >>> result = any_boolean()
    >>> type(result)
    <type 'bool'>
    """
    return random.choice([True, False])


def any_int(min_value=0, max_value=100, **kwargs):
    """
    Return random integer from the selected range

    >>> result = any_int(min_value=0, max_value=100)
    >>> type(result)
    <type 'int'>
    >>> result in range(0,101)
    True

    """
    return random.randint(min_value, max_value)


def any_float(min_value=0, max_value=100, precision=2):
    """
    Returns random float
    
    >>> result = any_float(min_value=0, max_value=100, precision=2)
    >>> type(result)
    <type 'float'>
    >>> result >=0 and result <= 100
    True

    """
    return round(random.uniform(min_value, max_value), precision)


def any_letter(letters = ascii_letters, **kwargs):
    """
    Return random letter

    >>> result = any_letter(letters = ascii_letters)
    >>> type(result)
    <type 'str'>
    >>> len(result)
    1
    >>> result in ascii_letters
    True

    """
    return random.choice(letters)


def any_string(letters = ascii_letters, min_length=3, max_length=100):
    """
    Return string with random content

    >>> result = any_string(letters = ascii_letters, min_length=3, max_length=100)
    >>> type(result)
    <type 'str'>
    >>> len(result) in range(3,101)
    True
    >>> any([c in ascii_letters for c in result])
    True
    """
    
    length = random.randint(min_length, max_length)
    letters = [any_letter(letters=letters) for _ in range(0, length)]
    return "".join(letters)


def any_date(from_date=date(1990, 1, 1), to_date=date.today()):
    """
    Return random date from the [from_date, to_date] interval

    >>> result = any_date(from_date=date(1990,1,1), to_date=date(1990,1,3))
    >>> type(result)
    <type 'datetime.date'>
    >>> result >= date(1990,1,1) and result <= date(1990,1,3)
    True
    """
    days = any_int(min_value=0, max_value=(to_date - from_date).days)

    return from_date + timedelta(days=days)


def any_datetime(from_date=datetime(1990, 1, 1), to_date=datetime.now()):
    """
    Return random datetime from the [from_date, to_date] interval

    >>> result = any_datetime(from_date=datetime(1990,1,1), to_date=datetime(1990,1,3))
    >>> type(result)
    <type 'datetime.datetime'>
    >>> result >= datetime(1990,1,1) and result <= datetime(1990,1,3)
    True
    """
    days = any_int(min_value=0, max_value=(to_date - from_date).days-1)
    time = timedelta(seconds=any_int(min_value=0, max_value=24*3600-1))

    return from_date + timedelta(days=days) + time


def any_decimal(min_value=Decimal(0), max_value=Decimal('99.99'), decimal_places=2):
    """
    Return random decimal from the [min_value, max_value] interval

    >>> result = any_decimal(min_value=0.999, max_value=3, decimal_places=3)
    >>> type(result)
    <class 'decimal.Decimal'>
    >>> result >= Decimal('0.999') and result <= Decimal(3)
    True
    """
    return Decimal(str(any_float(min_value=float(min_value),
                                 max_value=float(max_value),
                                 precision=decimal_places)))


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
from os import path
import shutil, sys, virtualenv, subprocess

PROJECT_ROOT = path.dirname(path.abspath(path.dirname(__file__)))
REQUIREMENTS = path.join(PROJECT_ROOT, 'tests', 'requirements.pip')

VE_ROOT = path.join(PROJECT_ROOT, '.ve')
VE_TIMESTAMP = path.join(VE_ROOT, 'timestamp')

envtime = path.exists(VE_ROOT) and path.getmtime(VE_ROOT) or 0
envreqs = path.exists(VE_TIMESTAMP) and path.getmtime(VE_TIMESTAMP) or 0
envspec = path.getmtime(REQUIREMENTS)

def go_to_ve():
    # going into ve
    if not sys.prefix == VE_ROOT:
        if sys.platform == 'win32':
            python = path.join(VE_ROOT, 'Scripts', 'python.exe')
        else:
            python = path.join(VE_ROOT, 'bin', 'python')
            
        retcode = subprocess.call([python, __file__] + sys.argv[1:])
        sys.exit(retcode)

update_ve = 'update_ve' in sys.argv
if update_ve or envtime < envspec or envreqs < envspec:
    if update_ve:
        # install ve
        if envtime < envspec:
            if path.exists(VE_ROOT):
                shutil.rmtree(VE_ROOT)
            virtualenv.logger = virtualenv.Logger(consumers=[])
            virtualenv.create_environment(VE_ROOT, site_packages=True)

        go_to_ve()    

        # check requirements
        if update_ve or envreqs < envspec:
            import pip
            pip.main(initial_args=['install', '-r', REQUIREMENTS])
            file(VE_TIMESTAMP, 'w').close()
        sys.exit(0)
    else:
        print "VirtualEnv need to be updated"
        print "Run ./manage.py update_ve"
        sys.exit(1)

go_to_ve()

sys.path.insert(0, PROJECT_ROOT)

# run django
from django.core.management import execute_manager
try:
    import tests.settings
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv += ['test'] + list(tests.settings.PROJECT_APPS)
    execute_manager(tests.settings)

########NEW FILE########
__FILENAME__ = settings
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

SITE_ID=1
PROJECT_APPS = ('django_any',)
INSTALLED_APPS = ( 'django.contrib.auth',
                   'django.contrib.contenttypes',
                   'django.contrib.sessions',
                   'django.contrib.sites',
                   'django.contrib.admin',
                   'django_jenkins',) + PROJECT_APPS
DATABASE_ENGINE = 'sqlite3'
TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.load_template_source',
)
ROOT_URLCONF = 'tests.test_runner'
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

if __name__ == "__main__":
    import sys, test_runner as settings
    from django.core.management import execute_manager
    if len(sys.argv) == 1:
            sys.argv += ['test'] + list(PROJECT_APPS)
    execute_manager(settings)

########NEW FILE########
