__FILENAME__ = fields
from __future__ import unicode_literals
from warnings import warn

from django.forms import MultiValueField, DecimalField, ChoiceField
from moneyed.classes import Money

from .widgets import MoneyWidget, CURRENCY_CHOICES


__all__ = ('MoneyField',)


class MoneyField(MultiValueField):
    def __init__(self, currency_widget=None, currency_choices=CURRENCY_CHOICES, choices=CURRENCY_CHOICES,
                 max_value=None, min_value=None,
                 max_digits=None, decimal_places=None, *args, **kwargs):
        if currency_choices != CURRENCY_CHOICES:
            warn('currency_choices will be deprecated in favor of choices', PendingDeprecationWarning)
            choices = currency_choices
        decimal_field = DecimalField(max_value, min_value, max_digits, decimal_places, *args, **kwargs)
        choice_field = ChoiceField(choices=currency_choices)
        self.widget = currency_widget if currency_widget else MoneyWidget(amount_widget=decimal_field.widget,
                                                                          currency_widget=choice_field.widget)
        fields = (decimal_field, choice_field)
        super(MoneyField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        return Money(*data_list[:2])
########NEW FILE########
__FILENAME__ = widgets
import operator

from django.conf import settings
from django.forms import TextInput, Select, MultiWidget
from moneyed import CURRENCIES, DEFAULT_CURRENCY_CODE

__all__ = ('MoneyWidget', )

PROJECT_CURRENCIES = getattr(settings, 'CURRENCIES', None)

if PROJECT_CURRENCIES:
    CURRENCY_CHOICES = [(code, CURRENCIES[code].name) for code in
                        PROJECT_CURRENCIES]
else:
    CURRENCY_CHOICES = [(c.code, c.name) for i, c in CURRENCIES.items() if
                        c.code != DEFAULT_CURRENCY_CODE]

CURRENCY_CHOICES.sort(key=operator.itemgetter(1))


class MoneyWidget(MultiWidget):
    def __init__(self, choices=CURRENCY_CHOICES, amount_widget=None, currency_widget=None, *args, **kwargs):
        if not amount_widget:
            amount_widget = TextInput
        if not currency_widget:
            currency_widget = Select(choices)
        widgets = (amount_widget, currency_widget)
        super(MoneyWidget, self).__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if value:
            return [value.amount, value.currency]
        return [None, None]
########NEW FILE########
__FILENAME__ = fields
from __future__ import division
from django.db import models
from django.conf import settings
from django.db.models.sql.expressions import SQLEvaluator
try:
    from django.utils.encoding import smart_unicode
except ImportError:
    # Python 3
    from django.utils.encoding import smart_text as smart_unicode
from django.utils import translation
from django.db.models.signals import class_prepared
from moneyed import Money, Currency, DEFAULT_CURRENCY
from moneyed.localization import _FORMATTER, format_money
from djmoney import forms
from djmoney.forms.widgets import CURRENCY_CHOICES
from djmoney.utils import get_currency_field_name
from django.db.models.expressions import ExpressionNode

from decimal import Decimal, ROUND_DOWN
import inspect

try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, in Python 3
    basestring = (str, bytes)

__all__ = ('MoneyField', 'NotSupportedLookup')

SUPPORTED_LOOKUPS = ('exact', 'isnull', 'lt', 'gt', 'lte', 'gte')


class NotSupportedLookup(Exception):
    def __init__(self, lookup):
        self.lookup = lookup

    def __str__(self):
        return "Lookup '%s' is not supported for MoneyField" % self.lookup


class MoneyPatched(Money):

    # Set to True or False has a higher priority
    # than USE_L10N == True in the django settings file.
    # The variable "self.use_l10n" has three states:
    use_l10n = None

    def __float__(self):
        return float(self.amount)

    @classmethod
    def _patch_to_current_class(cls, money):
        """
        Converts object of type MoneyPatched on the object of type Money.
        """
        return cls(money.amount, money.currency)

    def __pos__(self):
        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__pos__())

    def __neg__(self):
        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__neg__())

    def __add__(self, other):

        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__add__(other))

    def __sub__(self, other):

        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__sub__(other))

    def __mul__(self, other):

        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__mul__(other))

    def __truediv__(self, other):

        if isinstance(other, Money):
            return super(MoneyPatched, self).__truediv__(other)
        else:
            return self._patch_to_current_class(
                super(MoneyPatched, self).__truediv__(other))

    def __rmod__(self, other):

        return MoneyPatched._patch_to_current_class(
            super(MoneyPatched, self).__rmod__(other))

    def __get_current_locale(self):
        locale = translation.to_locale(translation.get_language())

        if _FORMATTER.get_formatting_definition(locale):
            return locale

        if _FORMATTER.get_formatting_definition('%s_%s' % (locale, locale)):
            return '%s_%s' % (locale, locale)

        return ''

    def __use_l10n(self):
        """
        Return boolean.
        """
        if self.use_l10n is None:
            return settings.USE_L10N
        return self.use_l10n

    def __unicode__(self):

        if self.__use_l10n():
            locale = self.__get_current_locale()
            if locale:
                return format_money(self, locale=locale)

        return format_money(self)

    def __str__(self):

        if self.__use_l10n():
            locale = self.__get_current_locale()
            if locale:
                return format_money(self, locale=locale)

        return format_money(self)

    def __repr__(self):
        # small fix for tests
        return "%s %s" % (self.amount.to_integral_value(ROUND_DOWN),
                          self.currency)


class MoneyFieldProxy(object):
    def __init__(self, field):
        self.field = field
        self.currency_field_name = get_currency_field_name(self.field.name)

    def _money_from_obj(self, obj):
        amount = obj.__dict__[self.field.name]
        currency = obj.__dict__[self.currency_field_name]
        if amount is None:
            return None
        return MoneyPatched(amount=amount, currency=currency)

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')
        if isinstance(obj.__dict__[self.field.name], ExpressionNode):
            return obj.__dict__[self.field.name]
        if not isinstance(obj.__dict__[self.field.name], Money):
            obj.__dict__[self.field.name] = self._money_from_obj(obj)
        return obj.__dict__[self.field.name]

    def __set__(self, obj, value):
        if isinstance(value, tuple):
            value = Money(amount=value[0], currency=value[1])
        if isinstance(value, Money):
            obj.__dict__[self.field.name] = value.amount
            setattr(obj, self.currency_field_name,
                    smart_unicode(value.currency))
        elif isinstance(value, ExpressionNode):
            if isinstance(value.children[1], Money):
                value.children[1] = value.children[1].amount
            obj.__dict__[self.field.name] = value
        else:
            if value:
                value = str(value)
            obj.__dict__[self.field.name] = self.field.to_python(value)


class CurrencyField(models.CharField):
    description = "A field which stores currency."

    def __init__(self, price_field=None, verbose_name=None, name=None,
                 default=DEFAULT_CURRENCY, **kwargs):
        if isinstance(default, Currency):
            default = default.code
        kwargs['max_length'] = 3
        self.price_field = price_field
        self.frozen_by_south = kwargs.pop('frozen_by_south', False)
        super(CurrencyField, self).__init__(verbose_name, name, default=default,
                                            **kwargs)

    def get_internal_type(self):
        return "CharField"

    def contribute_to_class(self, cls, name):
        if not self.frozen_by_south and not name in [f.name for f in cls._meta.fields]:
            super(CurrencyField, self).contribute_to_class(cls, name)


class MoneyField(models.DecimalField):
    description = "A field which stores both the currency and amount of money."

    def __init__(self, verbose_name=None, name=None,
                 max_digits=None, decimal_places=None,
                 default=0.0,
                 default_currency=DEFAULT_CURRENCY,
                 currency_choices=CURRENCY_CHOICES, **kwargs):

        if isinstance(default, basestring):
            try:
                # handle scenario where default is formatted like:
                # 'amount currency-code'
                amount, currency = default.split(" ")
            except ValueError:
                # value error would be risen if the default is
                # without the currency part, i.e
                # 'amount'
                amount = default
                currency = default_currency
            default = Money(float(amount), Currency(code=currency))
        elif isinstance(default, (float, Decimal, int)):
            default = Money(default, default_currency)

        if not isinstance(default, Money):
            raise Exception(
                "default value must be an instance of Money, is: %s" % str(
                    default))

        # Avoid giving the user hard-to-debug errors if they miss required attributes
        if max_digits is None:
            raise Exception(
                "You have to provide a max_digits attribute to Money fields.")

        if decimal_places is None:
            raise Exception(
                "You have to provide a decimal_places attribute to Money fields.")

        if not default_currency:
            default_currency = default.currency

        self.default_currency = default_currency
        self.currency_choices = currency_choices
        self.frozen_by_south = kwargs.pop('frozen_by_south', False)

        super(MoneyField, self).__init__(verbose_name, name, max_digits,
                                         decimal_places, default=default,
                                         **kwargs)

    def to_python(self, value):
        if isinstance(value, SQLEvaluator):
            return value
        if isinstance(value, Money):
            value = value.amount
        if isinstance(value, tuple):
            value = value[0]
        return super(MoneyField, self).to_python(value)

    def get_internal_type(self):
        return "DecimalField"

    def contribute_to_class(self, cls, name):

        cls._meta.has_money_field = True

        # Don't run on abstract classes
        # Removed, see https://github.com/jakewins/django-money/issues/42
        #if cls._meta.abstract:
        #    return

        if not self.frozen_by_south:
            c_field_name = get_currency_field_name(name)
            # Do not change default=self.default_currency.code, needed
            # for south compat.
            c_field = CurrencyField(
                max_length=3, price_field=self,
                default=self.default_currency, editable=False,
                choices=self.currency_choices
            )
            c_field.creation_counter = self.creation_counter
            cls.add_to_class(c_field_name, c_field)

        super(MoneyField, self).contribute_to_class(cls, name)

        setattr(cls, self.name, MoneyFieldProxy(self))

    def get_db_prep_save(self, value, connection):
        if isinstance(value, SQLEvaluator):
            return value
        if isinstance(value, Money):
            value = value.amount
            return value
        return super(MoneyField, self).get_db_prep_save(value, connection)

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        if not lookup_type in SUPPORTED_LOOKUPS:
            raise NotSupportedLookup(lookup_type)
        value = self.get_db_prep_save(value, connection)
        return super(MoneyField, self).get_db_prep_lookup(lookup_type, value,
                                                          connection, prepared)

    def get_default(self):
        if isinstance(self.default, Money):
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])
            # We need to return the numerical value if this is called by south
            if mod.__name__ == "south.db.generic":
                return float(self.default.amount)
            return self.default
        else:
            return super(MoneyField, self).get_default()

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.MoneyField}
        defaults.update(kwargs)
        defaults['currency_choices'] = self.currency_choices
        return super(MoneyField, self).formfield(**defaults)

    def get_south_default(self):
        return '%s' % str(self.default)

    def get_south_default_currency(self):
        return '"%s"' % str(self.default_currency.code)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

    ## South support
    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # Note: This method gets automatically with schemamigration time.
        from south.modelsinspector import introspector
        field_class = self.__class__.__module__ + "." + self.__class__.__name__
        args, kwargs = introspector(self)
        # We need to
        # 1. Delete the default, 'cause it's not automatically supported.
        kwargs.pop('default')
        # 2. add the default currency, because it's not picked up from the inspector automatically.
        kwargs['default_currency'] = "'%s'" % self.default_currency
        return field_class, args, kwargs


try:
    from south.modelsinspector import add_introspection_rules
    rules = [
        # MoneyField has its own method.
        ((CurrencyField,),
         [],  # No positional args
         {'default': ('default', {'default': DEFAULT_CURRENCY.code}),
          'max_length': ('max_length', {'default': 3})}),
    ]

    # MoneyField implement the serialization in south_field_triple method
    add_introspection_rules(rules, ["^djmoney\.models\.fields\.CurrencyField"])
except ImportError:
    pass


def patch_managers(sender, **kwargs):
    """
    Patches models managers
    """
    from .managers import money_manager

    if hasattr(sender._meta, 'has_money_field'):
        for _id, name, manager in sender._meta.concrete_managers:
            setattr(sender, name, money_manager(manager))


class_prepared.connect(patch_managers)

########NEW FILE########
__FILENAME__ = managers
from django.db.models.expressions import ExpressionNode, F

try:
    from django.utils.encoding import smart_unicode
except ImportError:
    # Python 3
    from django.utils.encoding import smart_text as smart_unicode

from djmoney.utils import get_currency_field_name


def _expand_money_params(kwargs):
    def get_clean_name(name):
        # Get rid of __lt, __gt etc for the currency lookup
        path = name.split(LOOKUP_SEP)
        if path[-1] in QUERY_TERMS:
            return LOOKUP_SEP.join(path[:-1])
        else:
            return name

    from moneyed import Money
    try:
        from django.db.models.constants import LOOKUP_SEP
    except ImportError:
        # Django < 1.5
        LOOKUP_SEP = '__'
    from django.db.models.sql.constants import QUERY_TERMS

    to_append = {}
    for name, value in kwargs.items():
        if isinstance(value, Money):
            clean_name = get_clean_name(name)
            to_append[name] = value.amount
            to_append[get_currency_field_name(clean_name)] = smart_unicode(
                value.currency)
        if isinstance(value, ExpressionNode):
            clean_name = get_clean_name(name)
            to_append['_'.join([clean_name, 'currency'])] = F('_'.join([value.name, 'currency']))

    kwargs.update(to_append)
    return kwargs


def understands_money(func):
    """
    Used to wrap a queryset method with logic to expand
    a query from something like:

    mymodel.objects.filter(money=Money(100,"USD"))

    To something equivalent to:

    mymodel.objects.filter(money=Decimal("100.0), money_currency="USD")
    """

    def decorator(*args, **kwargs):
        kwargs = _expand_money_params(kwargs)
        return func(*args, **kwargs)

    return decorator


RELEVANT_QUERYSET_METHODS = ['dates', 'distinct', 'extra', 'get',
                             'get_or_create', 'filter', 'complex_filter',
                             'exclude', 'in_bulk', 'iterator', 'latest',
                             'order_by', 'select_related', 'values']


def add_money_comprehension_to_queryset(qs):
    # Decorate each relevant method with understand_money in the queryset given
    list(map(lambda attr: setattr(qs, attr, understands_money(getattr(qs, attr))),
        RELEVANT_QUERYSET_METHODS))
    return qs


def money_manager(manager):
    """
    Wraps a model managers get_query_set method so that each query set it returns
    is able to work on money fields.

    We use this instead of a real model manager, in order to allow users of django-money to
    use other managers special managers while still doing money queries.
    """
    old_get_query_set = manager.get_query_set

    def get_query_set(*args, **kwargs):
        return add_money_comprehension_to_queryset(old_get_query_set(*args, **kwargs))

    manager.get_query_set = get_query_set

    if hasattr(manager, 'get_queryset'):
        # Django 1.6
        manager.get_queryset = get_query_set

    return manager

########NEW FILE########
__FILENAME__ = serializers
# coding=utf-8
import json

from django.core.serializers.python import Deserializer as PythonDeserializer
from django.core.serializers.json import Serializer as JSONSerializer
from django.core.serializers.python import _get_model
from django.utils import six

from djmoney.models.fields import MoneyField
from djmoney.utils import get_currency_field_name
from moneyed import Money

Serializer = JSONSerializer


def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of JSON data.
    """
    if not isinstance(stream_or_string, (bytes, six.string_types)):
        stream_or_string = stream_or_string.read()
    if isinstance(stream_or_string, bytes):
        stream_or_string = stream_or_string.decode('utf-8')
    try:
        for obj in json.loads(stream_or_string):
            money_fields = {}
            fields = {}
            Model = _get_model(obj["model"])
            for (field_name, field_value) in six.iteritems(obj['fields']):
                field = Model._meta.get_field(field_name)
                if isinstance(field, MoneyField) and field_value is not None:
                    money_fields[field_name] = Money(field_value, obj['fields'][get_currency_field_name(field_name)])
                else:
                    fields[field_name] = field_value
            obj['fields'] = fields

            for obj in PythonDeserializer([obj], **options):
                for field, value in money_fields.items():
                    setattr(obj.object, field, value)
                yield obj
    except GeneratorExit:
        raise

########NEW FILE########
__FILENAME__ = djmoney
from django import template
from django.template import TemplateSyntaxError
from moneyed import Money

from ..models.fields import MoneyPatched

register = template.Library()


class MoneyLocalizeNode(template.Node):

    def __repr__(self):
        return "<MoneyLocalizeNode %r>" % self.money

    def __init__(self, money=None, amount=None, currency=None, use_l10n=None,
                 var_name=None):

        if money and (amount or currency):
            raise Exception('You can define either "money" or the'
                            ' "amount" and "currency".')

        self.money = money
        self.amount = amount
        self.currency = currency
        self.use_l10n = use_l10n
        self.var_name = var_name

    @classmethod
    def handle_token(cls, parser, token):

        tokens = token.contents.split()

        # default value
        var_name = None
        use_l10n = True

        # GET variable var_name
        if len(tokens) > 3:
            if tokens[-2] == 'as':
                var_name = parser.compile_filter(tokens[-1])
                # remove the already used data
                tokens = tokens[0:-2]

        # GET variable use_l10n
        if tokens[-1].lower() in ('on', 'off'):

            if tokens[-1].lower() == 'on':
                use_l10n = True
            else:
                use_l10n = False
            # remove the already used data
            tokens.pop(-1)

        # GET variable money
        if len(tokens) == 2:
            return cls(money=parser.compile_filter(tokens[1]),
                       var_name=var_name, use_l10n=use_l10n)

        # GET variable amount and currency
        if len(tokens) == 3:
            return cls(amount=parser.compile_filter(tokens[1]),
                       currency=parser.compile_filter(tokens[2]),
                       var_name=var_name, use_l10n=use_l10n)

        raise TemplateSyntaxError('Wrong number of input data to the tag.')

    def render(self, context):

        money = self.money.resolve(context) if self.money else None
        amount = self.amount.resolve(context) if self.amount else None
        currency = self.currency.resolve(context) if self.currency else None

        if money is not None:
            if isinstance(money, Money):
                money = MoneyPatched._patch_to_current_class(money)
            else:
                raise TemplateSyntaxError('The variable "money" must be an '
                                          'instance of Money.')

        elif amount is not None and currency is not None:
            money = MoneyPatched(float(amount), str(currency))
        else:
            raise TemplateSyntaxError('You must define both variables: '
                                      'amount and currency.')

        money.use_l10n = self.use_l10n

        if self.var_name is None:
            return money

        # as <var_name>
        context[self.var_name.token] = money
        return ''


@register.tag
def money_localize(parser, token):
    """
    Usage::

        {% money_localize <money_object> [ on(default) | off ] [as var_name] %}
        {% money_localize <amount> <currency> [ on(default) | off ] [as var_name] %}

    Example:

        The same effect:
        {% money_localize money_object %}
        {% money_localize money_object on %}

        Assignment to a variable:
        {% money_localize money_object on as NEW_MONEY_OBJECT %}

        Formatting the number with currency:
        {% money_localize '4.5' 'USD' %}

    Return::

        MoneyPatched object

    """
    return MoneyLocalizeNode.handle_token(parser, token)

########NEW FILE########
__FILENAME__ = form_tests
'''
Created on May 7, 2011

@author: jake
'''
from decimal import Decimal
from warnings import warn

import moneyed
from django.test import TestCase
from moneyed import Money

from .testapp.forms import MoneyForm, MoneyModelForm
from .testapp.models import ModelWithVanillaMoneyField


class MoneyFormTestCase(TestCase):
    def testRender(self):
        warn('Rendering depends on localization.', DeprecationWarning)

    def testValidate(self):
        m = Money(Decimal(10), moneyed.SEK)

        form = MoneyForm({"money_0": m.amount, "money_1": m.currency})

        self.assertTrue(form.is_valid())

        result = form.cleaned_data['money']
        self.assertTrue(isinstance(result, Money))

        self.assertEquals(result.amount, Decimal("10"))
        self.assertEquals(result.currency, moneyed.SEK)
        self.assertEquals(result, m)

    def testAmountIsNotANumber(self):
        form = MoneyForm({"money_0": "xyz*|\\", "money_1": moneyed.SEK})
        self.assertFalse(form.is_valid())

    def testAmountExceedsMaxValue(self):
        form = MoneyForm({"money_0": 10000, "money_1": moneyed.SEK})
        self.assertFalse(form.is_valid())

    def testAmountExceedsMinValue(self):
        form = MoneyForm({"money_0": 1, "money_1": moneyed.SEK})
        self.assertFalse(form.is_valid())

    def testNonExistentCurrency(self):
        m = Money(Decimal(10), moneyed.EUR)
        form = MoneyForm({"money_0": m.amount, "money_1": m.currency})
        self.assertFalse(form.is_valid())


class MoneyModelFormTestCase(TestCase):
    def testSave(self):
        m = Money(Decimal("10"), moneyed.SEK)
        form = MoneyModelForm({"money_0": m.amount, "money_1": m.currency})

        self.assertTrue(form.is_valid())
        model = form.save()

        retrieved = ModelWithVanillaMoneyField.objects.get(pk=model.pk)
        self.assertEqual(m, retrieved.money)

########NEW FILE########
__FILENAME__ = model_tests
'''
Created on May 7, 2011

@author: jake
'''
from django.test import TestCase
from django.db.models import F
from moneyed import Money
from .testapp.models import (ModelWithVanillaMoneyField,
    ModelRelatedToModelWithMoney, ModelWithChoicesMoneyField, BaseModel, InheritedModel, InheritorModel,
    SimpleModel, NullMoneyFieldModel, ModelWithDefaultAsDecimal, ModelWithDefaultAsFloat, ModelWithDefaultAsInt,
    ModelWithDefaultAsString, ModelWithDefaultAsStringWithCurrency, ModelWithDefaultAsMoney, ModelWithTwoMoneyFields)
import moneyed


class VanillaMoneyFieldTestCase(TestCase):

    def testSaving(self):

        somemoney = Money("100.0")

        model = ModelWithVanillaMoneyField(money=somemoney)
        model.save()

        retrieved = ModelWithVanillaMoneyField.objects.get(pk=model.pk)

        self.assertEquals(somemoney.currency, retrieved.money.currency)
        self.assertEquals(somemoney, retrieved.money)

        # Try setting the value directly
        retrieved.money = Money(1, moneyed.DKK)
        retrieved.save()
        retrieved = ModelWithVanillaMoneyField.objects.get(pk=model.pk)

        self.assertEquals(Money(1, moneyed.DKK), retrieved.money)

        object = BaseModel.objects.create()
        self.assertEquals(Money(0, 'USD'), object.first_field)
        object = BaseModel.objects.create(first_field='111.2')
        self.assertEquals(Money('111.2', 'USD'), object.first_field)
        object = BaseModel.objects.create(first_field=Money('123', 'PLN'))
        self.assertEquals(Money('123', 'PLN'), object.first_field)

        object = ModelWithDefaultAsDecimal.objects.create()
        self.assertEquals(Money('0.01', 'CHF'), object.money)
        object = ModelWithDefaultAsInt.objects.create()
        self.assertEquals(Money('123', 'GHS'), object.money)
        object = ModelWithDefaultAsString.objects.create()
        self.assertEquals(Money('123', 'PLN'), object.money)
        object = ModelWithDefaultAsStringWithCurrency.objects.create()
        self.assertEquals(Money('123', 'USD'), object.money)
        object = ModelWithDefaultAsFloat.objects.create()
        self.assertEquals(Money('12.05', 'PLN'), object.money)
        object = ModelWithDefaultAsMoney.objects.create()
        self.assertEquals(Money('0.01', 'RUB'), object.money)

    def testRelativeAddition(self):
        # test relative value adding
        somemoney = Money(100, 'USD')
        mymodel = ModelWithVanillaMoneyField.objects.create(money=somemoney)
        # duplicate money
        mymodel.money = F('money') + somemoney
        mymodel.save()
        mymodel = ModelWithVanillaMoneyField.objects.get(pk=mymodel.pk)
        self.assertEquals(mymodel.money, 2 * somemoney)
        # subtract everything.
        mymodel.money = F('money') - (2 * somemoney)
        mymodel.save()
        mymodel = ModelWithVanillaMoneyField.objects.get(pk=mymodel.pk)
        self.assertEquals(Money(0, 'USD'), mymodel.money)

    def testComparisonLookup(self):
        ModelWithTwoMoneyFields.objects.create(amount1=Money(1, 'USD'), amount2=Money(2, 'USD'))
        ModelWithTwoMoneyFields.objects.create(amount1=Money(2, 'USD'), amount2=Money(0, 'USD'))
        ModelWithTwoMoneyFields.objects.create(amount1=Money(3, 'USD'), amount2=Money(0, 'USD'))
        ModelWithTwoMoneyFields.objects.create(amount1=Money(4, 'USD'), amount2=Money(0, 'GHS'))

        qs = ModelWithTwoMoneyFields.objects.filter(amount1__gt=F('amount2'))
        self.assertEquals(2, qs.count())

    def testExactMatch(self):

        somemoney = Money("100.0")

        model = ModelWithVanillaMoneyField()
        model.money = somemoney

        model.save()

        retrieved = ModelWithVanillaMoneyField.objects.get(money=somemoney)

        self.assertEquals(model.pk, retrieved.pk)

    def testRangeSearch(self):

        minMoney = Money("3")

        model = ModelWithVanillaMoneyField(money=Money("100.0"))

        model.save()

        retrieved = ModelWithVanillaMoneyField.objects.get(money__gt=minMoney)
        self.assertEquals(model.pk, retrieved.pk)

        shouldBeEmpty = ModelWithVanillaMoneyField.objects.filter(money__lt=minMoney)
        self.assertEquals(shouldBeEmpty.count(), 0)

    def testCurrencySearch(self):

        otherMoney = Money("1000", moneyed.USD)
        correctMoney = Money("1000", moneyed.ZWN)

        model = ModelWithVanillaMoneyField(money=Money("100.0", moneyed.ZWN))
        model.save()

        shouldBeEmpty = ModelWithVanillaMoneyField.objects.filter(money__lt=otherMoney)
        self.assertEquals(shouldBeEmpty.count(), 0)

        shouldBeOne = ModelWithVanillaMoneyField.objects.filter(money__lt=correctMoney)
        self.assertEquals(shouldBeOne.count(), 1)

    def testCurrencyChoices(self):

        otherMoney = Money("1000", moneyed.USD)
        correctMoney = Money("1000", moneyed.ZWN)

        model = ModelWithChoicesMoneyField(
            money=Money("100.0", moneyed.ZWN)
        )
        model.save()

        shouldBeEmpty = ModelWithChoicesMoneyField.objects.filter(money__lt=otherMoney)
        self.assertEquals(shouldBeEmpty.count(), 0)

        shouldBeOne = ModelWithChoicesMoneyField.objects.filter(money__lt=correctMoney)
        self.assertEquals(shouldBeOne.count(), 1)

        model = ModelWithChoicesMoneyField(
            money=Money("100.0", moneyed.USD)
        )
        model.save()

    def testIsNullLookup(self):

        null_instance = NullMoneyFieldModel.objects.create(field=None)
        null_instance.save()

        normal_instance = NullMoneyFieldModel.objects.create(field=Money(100, 'USD'))
        normal_instance.save()

        shouldBeOne = NullMoneyFieldModel.objects.filter(field=None)
        self.assertEquals(shouldBeOne.count(), 1)


class RelatedModelsTestCase(TestCase):

    def testFindModelsRelatedToMoneyModels(self):

        moneyModel = ModelWithVanillaMoneyField(money=Money("100.0", moneyed.ZWN))
        moneyModel.save()

        relatedModel = ModelRelatedToModelWithMoney(moneyModel=moneyModel)
        relatedModel.save()

        ModelRelatedToModelWithMoney.objects.get(moneyModel__money=Money("100.0", moneyed.ZWN))
        ModelRelatedToModelWithMoney.objects.get(moneyModel__money__lt=Money("1000.0", moneyed.ZWN))


class InheritedModelTestCase(TestCase):
    """Test inheritence from a concrete model"""

    def testBaseModel(self):
        self.assertEqual(BaseModel.objects.model, BaseModel)

    def testInheritedModel(self):
        self.assertEqual(InheritedModel.objects.model, InheritedModel)
        moneyModel = InheritedModel(
            first_field=Money("100.0", moneyed.ZWN),
            second_field=Money("200.0", moneyed.USD),
        )
        moneyModel.save()
        self.assertEqual(moneyModel.first_field, Money(100.0, moneyed.ZWN))
        self.assertEqual(moneyModel.second_field, Money(200.0, moneyed.USD))


class InheritorModelTestCase(TestCase):
    """Test inheritence from an ABSTRACT model"""

    def testInheritorModel(self):
        self.assertEqual(InheritorModel.objects.model, InheritorModel)
        moneyModel = InheritorModel(
            price1=Money("100.0", moneyed.ZWN),
            price2=Money("200.0", moneyed.USD),
        )
        moneyModel.save()
        self.assertEqual(moneyModel.price1, Money(100.0, moneyed.ZWN))
        self.assertEqual(moneyModel.price2, Money(200.0, moneyed.USD))


class ManagerTest(TestCase):

    def test_manager(self):
        self.assertTrue(hasattr(SimpleModel, 'objects'))

    def test_objects_creation(self):
        SimpleModel.objects.create(money=Money("100.0", 'USD'))
        self.assertEqual(SimpleModel.objects.count(), 1)

########NEW FILE########
__FILENAME__ = money_patched
# -*- encoding: utf-8
from moneyed import test_moneyed_classes
from djmoney.models.fields import MoneyPatched

# replace class "Money" a class "MoneyPath"
test_moneyed_classes.Money = MoneyPatched

TestCurrency = test_moneyed_classes.TestCurrency

TestMoney = test_moneyed_classes.TestMoney

########NEW FILE########
__FILENAME__ = reversion_tests
from django.test import TestCase
from testapp.models import RevisionedModel
from moneyed import Money
import reversion


class ReversionTestCase(TestCase):
    def test_that_can_safely_restore_deleted_object(self):
        model = None
        amount = Money(100, 'GHS')
        with reversion.create_revision():
            model = RevisionedModel.objects.create(amount=amount)
            model.save()
        model.delete()
        version = reversion.get_deleted(RevisionedModel)[0]
        version.revision.revert()
        model = RevisionedModel.objects.get(pk=1)
        self.assertEquals(model.amount, amount)

########NEW FILE########
__FILENAME__ = runtests
'''
Created on May 7, 2011

@author: jake
'''
import sys
import os
import unittest
import django.conf


def setup():
    test_folder = os.path.abspath(os.path.dirname(__file__))
    src_folder = os.path.abspath(test_folder + "/../")
    sys.path.insert(0, test_folder)
    sys.path.insert(0, src_folder)

    os.environ[django.conf.ENVIRONMENT_VARIABLE] = "settings"

    from django.test.utils import setup_test_environment
    setup_test_environment()

    from django.db import connection
    connection.creation.create_test_db()


def tear_down():
    from django.db import connection
    connection.creation.destroy_test_db("not_needed")

    from django.test.utils import teardown_test_environment
    teardown_test_environment()

if __name__ == "__main__":

    setup()

    import tests
    unittest.main(module=tests)

    tear_down()

########NEW FILE########
__FILENAME__ = settings
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import warnings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

warnings.simplefilter('ignore', Warning)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'djmoney',
    'testapp'
)

SITE_ID = 1
ROOT_URLCONF = 'core.urls'

SECRET_KEY = 'foobar'

USE_L10N = True

import moneyed
from moneyed.localization import _FORMATTER, DEFAULT
from decimal import ROUND_HALF_EVEN

_FORMATTER.add_sign_definition('pl_PL', moneyed.PLN, suffix=' zł')
_FORMATTER.add_sign_definition(DEFAULT, moneyed.PLN, suffix=' zł')
_FORMATTER.add_formatting_definition(
    "pl_PL", group_size=3, group_separator=" ", decimal_point=",",
    positive_sign="", trailing_positive_sign="",
    negative_sign="-", trailing_negative_sign="",
    rounding_method=ROUND_HALF_EVEN)

########NEW FILE########
__FILENAME__ = tags_tests
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from django.test import TestCase
from django import template
from django.utils import translation

from ..models.fields import MoneyPatched
from moneyed import Money


class MoneyLocalizeTestCase(TestCase):

    def setUp(self):
        self.default_language = translation.get_language()
        translation.activate('pl')
        super(TestCase, self).setUp()

    def tearDown(self):
        translation.activate(self.default_language)
        super(TestCase, self).tearDown()

    def assertTemplate(self, template_string, result, context={}):
        c = template.Context(context)
        t = template.Template(template_string)
        self.assertEqual(t.render(c), result)

    def testOnOff(self):

        # with a tag template "money_localize"
        self.assertTemplate(
            '{% load djmoney %}{% money_localize money %}',
            '2,30 zł',
            context={'money': Money(2.3, 'PLN')})

        # without a tag template "money_localize"
        self.assertTemplate(
            '{{ money }}',
            '2,30 zł',
            context={'money': MoneyPatched(2.3, 'PLN')})

        with self.settings(USE_L10N=False):
            # money_localize has a default setting USE_L10N = True
            self.assertTemplate(
                '{% load djmoney %}{% money_localize money %}',
                '2,30 zł',
                context={'money': Money(2.3, 'PLN')})

            # without a tag template "money_localize"
            self.assertTemplate(
                '{{ money }}',
                '2.30 zł',
                context={'money': MoneyPatched(2.3, 'PLN')})
            mp = MoneyPatched(2.3, 'PLN')
            mp.use_l10n = True
            self.assertTemplate(
                '{{ money }}',
                '2,30 zł',
                context={'money': mp})

        self.assertTemplate(
            '{% load djmoney %}{% money_localize money on %}',
            '2,30 zł',
            context={'money': Money(2.3, 'PLN')})

        with self.settings(USE_L10N=False):
            self.assertTemplate(
                '{% load djmoney %}{% money_localize money on %}',
                '2,30 zł',
                context={'money': Money(2.3, 'PLN')})

        self.assertTemplate(
            '{% load djmoney %}{% money_localize money off %}',
            '2.30 zł',
            context={'money': Money(2.3, 'PLN')})

    def testAsVar(self):

        self.assertTemplate(
            '{% load djmoney %}{% money_localize money as NEW_M %}{{NEW_M}}',
            '2,30 zł',
            context={'money': Money(2.3, 'PLN')})

        self.assertTemplate(
            '{% load djmoney %}{% money_localize money off as NEW_M %}{{NEW_M}}',
            '2.30 zł',
            context={'money': Money(2.3, 'PLN')})

        # test zero amount of money
        self.assertTemplate(
            '{% load djmoney %}{% money_localize money off as NEW_M %}{{NEW_M}}',
            '0.00 zł',
            context={'money': Money(0, 'PLN')})

    def testConvert(self):

        self.assertTemplate(
            '{% load djmoney %}{% money_localize "2.5" "PLN" as NEW_M %}{{NEW_M}}',
            '2,50 zł',
            context={})

        self.assertTemplate(
            '{% load djmoney %}{% money_localize "2.5" "PLN" %}',
            '2,50 zł',
            context={})

        self.assertTemplate(
            '{% load djmoney %}{% money_localize amount currency %}',
            '2,60 zł',
            context={'amount': 2.6, 'currency': 'PLN'})

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

import models

class InheritedModelAdmin(admin.ModelAdmin):
     readonly_fields = ('second_field',)

admin.site.register(models.InheritedModel, InheritedModelAdmin)

########NEW FILE########
__FILENAME__ = forms
'''
Created on May 15, 2011

@author: jake
'''

from django import forms
from djmoney.forms import MoneyField
from .models import ModelWithVanillaMoneyField


class MoneyForm(forms.Form):

    money = MoneyField(currency_choices=[(u'SEK', u'Swedish Krona')], max_value=1000, min_value=2)


class MoneyModelForm(forms.ModelForm):

    class Meta:
        model = ModelWithVanillaMoneyField

########NEW FILE########
__FILENAME__ = models
'''
Created on May 7, 2011

@author: jake
'''

from djmoney.models.fields import MoneyField
from django.db import models

import moneyed
from decimal import Decimal


class ModelWithVanillaMoneyField(models.Model):
    money = MoneyField(max_digits=10, decimal_places=2)

class ModelWithDefaultAsInt(models.Model):
    money = MoneyField(default=123, max_digits=10, decimal_places=2, default_currency='GHS')

class ModelWithDefaultAsStringWithCurrency(models.Model):
    money = MoneyField(default='123 USD', max_digits=10, decimal_places=2)

class ModelWithDefaultAsString(models.Model):
    money = MoneyField(default='123', max_digits=10, decimal_places=2, default_currency='PLN')

class ModelWithDefaultAsFloat(models.Model):
    money = MoneyField(default=12.05, max_digits=10, decimal_places=2, default_currency='PLN')

class ModelWithDefaultAsDecimal(models.Model):
    money = MoneyField(default=Decimal('0.01'), max_digits=10, decimal_places=2, default_currency='CHF')

class ModelWithDefaultAsMoney(models.Model):
    money = MoneyField(default=moneyed.Money('0.01', 'RUB'), max_digits=10, decimal_places=2)

class ModelWithTwoMoneyFields(models.Model):
    amount1 = MoneyField(max_digits=10, decimal_places=2)
    amount2 = MoneyField(max_digits=10, decimal_places=3)

class ModelRelatedToModelWithMoney(models.Model):
    moneyModel = models.ForeignKey(ModelWithVanillaMoneyField)


class ModelWithChoicesMoneyField(models.Model):
    money = MoneyField(
        max_digits=10,
        decimal_places=2,
        currency_choices=[
            (moneyed.USD, 'US Dollars'),
            (moneyed.ZWN, 'Zimbabwian')
        ],
    )


class AbstractModel(models.Model):
    price1 = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')

    class Meta:
        abstract = True


class InheritorModel(AbstractModel):
    price2 = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')


class RevisionedModel(models.Model):
    amount = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')

import reversion
reversion.register(RevisionedModel)


class BaseModel(models.Model):
    first_field = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')


class InheritedModel(BaseModel):
    second_field = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')


class SimpleModel(models.Model):
    money = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')


class NullMoneyFieldModel(models.Model):
    field = MoneyField(max_digits=10, decimal_places=2, null=True)

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8

get_currency_field_name = lambda name: "%s_currency" % name

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import sys
from django.conf import settings

settings.configure(
    DEBUG=True,
#    AUTH_USER_MODEL='testdata.CustomUser',
    DATABASES={
         'default': {
             'ENGINE': 'django.db.backends.sqlite3',
         }
    },
    SITE_ID=1,
    ROOT_URLCONF=None,
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'djmoney',
        'djmoney.tests.testapp',
        'south',
        'reversion',
    ),
    USE_TZ=True,
    USE_L10N=True,
    SOUTH_TESTS_MIGRATE=True,
)

import moneyed
from moneyed.localization import _FORMATTER, DEFAULT
from decimal import ROUND_HALF_EVEN

_FORMATTER.add_sign_definition('pl_PL', moneyed.PLN, suffix=' zł')
_FORMATTER.add_sign_definition(DEFAULT, moneyed.PLN, suffix=' zł')
_FORMATTER.add_formatting_definition(
     "pl_PL", group_size=3, group_separator=" ", decimal_point=",",
     positive_sign="", trailing_positive_sign="",
     negative_sign="-", trailing_negative_sign="",
     rounding_method=ROUND_HALF_EVEN)


from django.test.simple import DjangoTestSuiteRunner
test_runner = DjangoTestSuiteRunner(verbosity=1)

# If you use South for migrations, uncomment this to monkeypatch
# syncdb to get migrations to run.
from south.management.commands import patch_for_test_db_setup
patch_for_test_db_setup()

failures = test_runner.run_tests(['djmoney', ])
if failures:
    sys.exit(failures)


## Run py.tests
# Compatibility testing patches on the py-moneyed
import pytest
pytest.main()

########NEW FILE########
