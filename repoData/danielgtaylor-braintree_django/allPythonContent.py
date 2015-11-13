__FILENAME__ = forms
import datetime
from copy import deepcopy

from django import forms
from django.forms.util import ErrorList
from django.forms import widgets

import braintree

from .odict import OrderedDict

class BraintreeForm(forms.Form):
    """
        A base Braintree form that defines common behaviors for all the
        various forms in this file for implementing Braintree transparent
        redirects.

        When creating a new instance of a Braintree form you MUST pass in a 
        result object as returned by BraintreeForm.get_result(...). You SHOULD
        also pass in a redirect_url keyword parameter.

            >>> result = MyForm.get_result(request)
            >>> form = MyForm(result, redirect_url="http://mysite.com/foo")

        Note that result may be None.

        Each BraintreeForm subclass must define a set of fields and its type,
        and can optionally define a set of labels and protected data. This is
        all dependent on the type of transparent redirect, which is documented
        here:

           http://www.braintreepaymentsolutions.com/gateway/transparent-redirect

        You can set any protected data easily:

            >>> form.tr_protected["options"]["submit_for_settlement"] = True

        Before rendering the form you MUST always generate the signed, hidden
        special data via:

            >>> form.generate_tr_data()

        To get the location to post data to you can use the action property in
        your templates:

            <form action="{{ form.action }}" method="POST">
                {{ form.as_table }}
                <button type="submit">Submit order</button>
            </form>
        
    """
    tr_type = ""
    
    # Order of fields matters so we used an ordered dictionary
    tr_fields = OrderedDict()
    tr_labels = {}
    tr_help = {}
    tr_protected = {}

    # A list of fields that should be boolean (checkbox) options
    tr_boolean_fields = []
    
    @classmethod
    def get_result(cls, request):
        """
            Get the result (or None) of a transparent redirect given a Django
            Request object.

                >>> result = MyForm.get_result(request)
                >>> if result.is_success:
                        take_some_action()

            This method uses the request.META["QUERY_STRING"] parameter to get
            the HTTP query string.
        """
        try:
            result = braintree.TransparentRedirect.confirm(request.META["QUERY_STRING"])
        except (KeyError, braintree.exceptions.not_found_error.NotFoundError):
            result = None

        return result

    def __init__(self, result, *args, **kwargs):
        self.redirect_url = kwargs.pop("redirect_url", "")
        self.update_id = kwargs.pop("update_id", None)

        # Create the form instance, with initial data if it was given
        if result:
            self.result = result
            data = self._flatten_dictionary(result.params)

            super(BraintreeForm, self).__init__(data, *args, **kwargs)

            # Are there any errors we should display?
            errors = self._flatten_errors(result.errors.errors.data)
            self.errors.update(errors)

        else:
            super(BraintreeForm, self).__init__(*args, **kwargs)

        # Dynamically setup all the required form fields
        # This is required because of the strange naming scheme that uses
        # characters not supported in Python variable names.
        labels = self._flatten_dictionary(self.tr_labels)
        helptext = self._flatten_dictionary(self.tr_help)
        for key in self._flatten_dictionary(self.tr_fields).keys():
            if key in labels:
                label = labels[key]
            else:
                label = key.split("[")[-1].strip("]").replace("_", " ").title()
            
            #override for default field
            if isinstance(self._flatten_dictionary(self.tr_fields)[key], forms.Field): 
                self.fields[key] = self._flatten_dictionary(self.tr_fields)[key]
                self.fields[key].label = label
                continue
            
            if key in self.tr_boolean_fields:
                # A checkbox MUST set value="true" for Braintree to pick
                # it up properly, refer to Braintree ticket #26438
                field = forms.BooleanField(label=label, required=False, widget=widgets.CheckboxInput(attrs={"checked": True, "value": "true", "class": "checkbox"}))
            elif key.endswith("[expiration_month]"):
                # Month selection should be a simple dropdown
                field = forms.ChoiceField(choices=[(x,x) for x in range(1, 13)], required=False, label=label)
            elif key.endswith("[expiration_year]"):
                # Year selection should be a simple dropdown
                year = datetime.date.today().year
                field = forms.ChoiceField(choices=[(x,x) for x in range(year, year + 16)], required=False, label=label)
            else:
                field = forms.CharField(label=label, required=False)

            if key in helptext:
                field.help_text = helptext[key]
                
            self.fields[key] = field

    def _flatten_dictionary(self, params, parent=None):
        """
            Flatten a hierarchical dictionary into a simple dictionary.

                >>> self._flatten_dictionary({
                    "test": {
                        "foo": 12,
                        "bar": "hello",
                    },
                    "baz": False
                })
                {
                    "test[foo]": 12,
                    "test[bar]": hello,
                    "baz": False
                }
                
        """
        data = OrderedDict()
        for key, val in params.items():
            full_key = parent + "[" + key + "]" if parent else key
            if isinstance(val, dict):
                data.update(self._flatten_dictionary(val, full_key))
            else:
                data[full_key] = val
        return data

    def _flatten_errors(self, params, parent=None):
        """
            A modified version of the flatten_dictionary method above used
            to coerce the structure holding errors returned by Braintree into
            a flattened dictionary where the keys are the names of the fields
            and the values the error messages, which can be directly used to
            set the field errors on the Django form object for display in
            templates.
        """
        data = OrderedDict()
        for key, val in params.items():
            full_key = parent + "[" + key + "]" if parent else key
            if full_key.endswith("[errors]"):
                full_key = full_key[:-len("[errors]")]
            if isinstance(val, dict):
                data.update(self._flatten_errors(val, full_key))
            elif key == "errors":
                for error in val:
                    data[full_key + "[" + error["attribute"] + "]"] = [error["message"]]
            else:
                data[full_key] = [val]
        return data

    def _remove_none(self, data):
        """
            Remove all items from a nested dictionary whose value is None.
        """
        for key, value in data.items():
            if value is None or isinstance(value, forms.Field):
                del data[key]
            if isinstance(value, dict):
                self._remove_none(data[key])

    def generate_tr_data(self):
        """
            Generate the special signed tr_data field required to properly
            render and submit the form to Braintree. This MUST be called
            prior to rendering the form!
        """
        tr_data = deepcopy(self.tr_fields)
        
        if self._errors:
            tr_data.update(self.tr_protected)
        else:
            tr_data.recursive_update(self.tr_protected)
            
        self._remove_none(tr_data)

        if self.update_id:
            tr_data.update({self.update_key:self.update_id})
            signed = getattr(braintree, self.tr_type).tr_data_for_update(tr_data, self.redirect_url)
        
        elif hasattr(getattr(braintree, self.tr_type), "tr_data_for_sale"):
            signed = getattr(braintree, self.tr_type).tr_data_for_sale(tr_data, self.redirect_url)
        
        else:
            signed = getattr(braintree, self.tr_type).tr_data_for_create(tr_data, self.redirect_url)
        
        self.fields["tr_data"] = forms.CharField(widget=widgets.HiddenInput({'value': signed}))

    def remove_section(self, section):
        """
            Remove a section of fields from the form, e.g. allowing you to
            hide all shipping address information in one quick call if you
            don't care about it.
        """
        for key in self.fields.keys():
            if key.startswith(section):
                del self.fields[key]

    def clean(self):
        if isinstance(self.result, braintree.error_result.ErrorResult) and self.result.transaction:
            raise forms.ValidationError(u"Error Processing Credit Card: %s" % self.result.transaction.processor_response_text)

    @property
    def action(self):
        """
            Get the location to post data to. Use this property in your
            templates, e.g. <form action="{{ form.action }}" method="post">.
        """
        return braintree.TransparentRedirect.url()

class TransactionForm(BraintreeForm):
    """
        A form to enter transaction details.
    """
    tr_type = "Transaction"
    tr_fields = OrderedDict([
        ("transaction", OrderedDict([
            ("amount", None),
            ("customer", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("email", None),
                ("phone", None),
                ("fax", None),
                ("website", None)]),
            ),
            ("credit_card", OrderedDict([
                ("cardholder_name", None),
                ("number", None),
                ("expiration_month", None),
                ("expiration_year", None),
                ("cvv", None)]),
            ),
            ("billing", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("street_address", None),
                ("extended_address", None),
                ("locality", None),
                ("region", None),
                ("postal_code", None),
                ("country_name", None)]),
            ),
            ("shipping", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("street_address", None),
                ("extended_address", None),
                ("locality", None),
                ("region", None),
                ("postal_code", None),
                ("country_name", None)]),
            ),
            ("options", OrderedDict([
                ("store_in_vault", None),
                ("add_billing_address_to_payment_method", None),
                ("store_shipping_address_in_vault", None)]),
            ),
        ])),
    ])
    tr_labels = {
        "transaction": {
            "credit_card": {
                "cvv": "CVV",
                "expiration_month": "Expiration Month",
                "expiration_year": "Expiration Year",
            },
            "options": {
                "store_in_vault": "Save credit card",
                "add_billing_address_to_payment_method": "Save billing address",
                "store_shipping_address_in_vault": "Save shipping address",
            },
        },
    }
    tr_protected = {
        "transaction": {
            "type": None,
            "order_id": None,
            "customer_id": None,
            "payment_method_token": None,
            "customer": {
                "id": None,
            },
            "credit_card": {
                "token": None,
            },
            "options": {
                "submit_for_settlement": None,
            },
        },
    }
    tr_boolean_fields = [
        "transaction[options][store_in_vault]",
        "transaction[options][add_billing_address_to_payment_method]",
        "transaction[options][store_shipping_address_in_vault]",
    ]

class CustomerForm(BraintreeForm):
    """
        A form to enter a new customer.
    """
    tr_type = "Customer"
    tr_fields = OrderedDict([
        ("customer", OrderedDict([
            ("first_name", None),
            ("last_name", None),
            ("company", None),
            ("email", None),
            ("phone", None),
            ("fax", None),
            ("website", None),
            ("credit_card", OrderedDict([
                ("cardholder_name", None),
                ("number", None),
                ("expiration_month", None),
                ("expiration_year", None),
                ("cvv", None),
                ("billing_address", OrderedDict([
                    ("first_name", None),
                    ("last_name", None),
                    ("company", None),
                    ("street_address", None),
                    ("extended_address", None),
                    ("locality", None),
                    ("region", None),
                    ("postal_code", None),
                    ("country_name", None)]),
                )]),
            )]),
        ),
    ])
    tr_labels = {
        "customer": {
            "credit_card": {
                "cvv": "CVV",
            },
        },
    }
    tr_protected = {
        "customer": {
            "id": None,
            "credit_card": {
                "token": None,
                "options": {
                    "verify_card": None,
                },
            },
        },
    }

class CreditCardForm(BraintreeForm):
    """
        A form to enter a new credit card.
    """
    tr_type = "CreditCard"
    tr_fields = OrderedDict([
        ("credit_card", OrderedDict([
            ("cardholder_name", None),
            ("number", None),
            ("expiration_month", None),
            ("expiration_year", None),
            ("cvv", None),
            ("billing_address", OrderedDict([
                ("first_name", None),
                ("last_name", None),
                ("company", None),
                ("street_address", None),
                ("extended_address", None),
                ("locality", None),
                ("region", None),
                ("postal_code", None),
                ("country_name", None)]),
            )]),
        ),
    ])
    tr_labels = {
        "credit_card": {
            "cvv": "CVV",
        },
    }
    tr_protected = {
        "credit_card": {
            "customer_id": None,
            "token": None,
            "options": {
                "verify_card": None,
            },
        },
    }



########NEW FILE########
__FILENAME__ = odict
# -*- coding: utf-8 -*-
"""
    odict
    ~~~~~

    This module is an example implementation of an ordered dict for the
    collections module.  It's not written for performance (it actually
    performs pretty bad) but to show how the API works.


    Questions and Answers
    =====================

    Why would anyone need ordered dicts?

        Dicts in python are unordered which means that the order of items when
        iterating over dicts is undefined.  As a matter of fact it is most of
        the time useless and differs from implementation to implementation.

        Many developers stumble upon that problem sooner or later when
        comparing the output of doctests which often does not match the order
        the developer thought it would.

        Also XML systems such as Genshi have their problems with unordered
        dicts as the input and output ordering of tag attributes is often
        mixed up because the ordering is lost when converting the data into
        a dict.  Switching to lists is often not possible because the
        complexity of a lookup is too high.

        Another very common case is metaprogramming.  The default namespace
        of a class in python is a dict.  With Python 3 it becomes possible
        to replace it with a different object which could be an ordered dict.
        Django is already doing something similar with a hack that assigns
        numbers to some descriptors initialized in the class body of a
        specific subclass to restore the ordering after class creation.

        When porting code from programming languages such as PHP and Ruby
        where the item-order in a dict is guaranteed it's also a great help
        to have an equivalent data structure in Python to ease the transition.

    Where are new keys added?

        At the end.  This behavior is consistent with Ruby 1.9 Hashmaps
        and PHP Arrays.  It also matches what common ordered dict
        implementations do currently.

    What happens if an existing key is reassigned?

        The key is *not* moved.  This is consitent with existing
        implementations and can be changed by a subclass very easily::

            class movingodict(odict):
                def __setitem__(self, key, value):
                    self.pop(key, None)
                    odict.__setitem__(self, key, value)

        Moving keys to the end of a ordered dict on reassignment is not
        very useful for most applications.

    Does it mean the dict keys are sorted by a sort expression?

        That's not the case.  The odict only guarantees that there is an order
        and that newly inserted keys are inserted at the end of the dict.  If
        you want to sort it you can do so, but newly added keys are again added
        at the end of the dict.

    I initializes the odict with a dict literal but the keys are not
    ordered like they should!

        Dict literals in Python generate dict objects and as such the order of
        their items is not guaranteed.  Before they are passed to the odict
        constructor they are already unordered.

    What happens if keys appear multiple times in the list passed to the
    constructor?

        The same as for the dict.  The latter item overrides the former.  This
        has the side-effect that the position of the first key is used because
        the key is actually overwritten:

        >>> odict([('a', 1), ('b', 2), ('a', 3)])
        odict.odict([('a', 3), ('b', 2)])

        This behavor is consistent with existing implementation in Python
        and the PHP array and the hashmap in Ruby 1.9.

    This odict doesn't scale!

        Yes it doesn't.  The delitem operation is O(n).  This is file is a
        mockup of a real odict that could be implemented for collections
        based on an linked list.

    Why is there no .insert()?

        There are few situations where you really want to insert a key at
        an specified index.  To now make the API too complex the proposed
        solution for this situation is creating a list of items, manipulating
        that and converting it back into an odict:

        >>> d = odict([('a', 42), ('b', 23), ('c', 19)])
        >>> l = d.items()
        >>> l.insert(1, ('x', 0))
        >>> odict(l)
        odict.odict([('a', 42), ('x', 0), ('b', 23), ('c', 19)])

    :copyright: (c) 2008 by Armin Ronacher and PEP 273 authors.
    :license: modified BSD license.
"""
from itertools import izip, imap
from copy import deepcopy

missing = object()


class OrderedDict(dict):
    """
    Ordered dict example implementation.

    This is the proposed interface for a an ordered dict as proposed on the
    Python mailinglist (proposal_).

    It's a dict subclass and provides some list functions.  The implementation
    of this class is inspired by the implementation of Babel but incorporates
    some ideas from the `ordereddict`_ and Django's ordered dict.

    The constructor and `update()` both accept iterables of tuples as well as
    mappings:

    >>> d = odict([('a', 'b'), ('c', 'd')])
    >>> d.update({'foo': 'bar'})
    >>> d
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    
    Keep in mind that when updating from dict-literals the order is not
    preserved as these dicts are unsorted!

    You can copy an odict like a dict by using the constructor, `copy.copy`
    or the `copy` method and make deep copies with `copy.deepcopy`:

    >>> from copy import copy, deepcopy
    >>> copy(d)
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> d.copy()
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> odict(d)
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> d['spam'] = []
    >>> d2 = deepcopy(d)
    >>> d2['spam'].append('eggs')
    >>> d
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])])
    >>> d2
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', ['eggs'])])

    All iteration methods as well as `keys`, `values` and `items` return
    the values ordered by the the time the key-value pair is inserted:

    >>> d.keys()
    ['a', 'c', 'foo', 'spam']
    >>> d.values()
    ['b', 'd', 'bar', []]
    >>> d.items()
    [('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])]
    >>> list(d.iterkeys())
    ['a', 'c', 'foo', 'spam']
    >>> list(d.itervalues())
    ['b', 'd', 'bar', []]
    >>> list(d.iteritems())
    [('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])]

    Index based lookup is supported too by `byindex` which returns the
    key/value pair for an index:

    >>> d.byindex(2)
    ('foo', 'bar')

    You can reverse the odict as well:

    >>> d.reverse()
    >>> d
    odict.odict([('spam', []), ('foo', 'bar'), ('c', 'd'), ('a', 'b')])
    
    And sort it like a list:

    >>> d.sort(key=lambda x: x[0].lower())
    >>> d
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])])

    .. _proposal: http://thread.gmane.org/gmane.comp.python.devel/95316
    .. _ordereddict: http://www.xs4all.nl/~anthon/Python/ordereddict/
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self._keys = []
        self.update(*args, **kwargs)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        if key not in self:
            self._keys.append(key)
        dict.__setitem__(self, key, item)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        d = memo.get(id(self), missing)
        if d is not missing:
            return d
        memo[id(self)] = d = self.__class__()
        dict.__init__(d, deepcopy(self.items(), memo))
        d._keys = self._keys[:]
        return d

    def __getstate__(self):
        return {'items': dict(self), 'keys': self._keys}

    def __setstate__(self, d):
        self._keys = d['keys']
        dict.update(d['items'])

    def __reversed__(self):
        return reversed(self._keys)

    def __eq__(self, other):
        if isinstance(other, odict):
            if not dict.__eq__(self, other):
                return False
            return self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __cmp__(self, other):
        if isinstance(other, odict):
            return cmp(self.items(), other.items())
        elif isinstance(other, dict):
            return dict.__cmp__(self, other)
        return NotImplemented

    @classmethod
    def fromkeys(cls, iterable, default=None):
        return cls((key, default) for key in iterable)

    def clear(self):
        del self._keys[:]
        dict.clear(self)

    def copy(self):
        return self.__class__(self)

    def items(self):
        return zip(self._keys, self.values())

    def iteritems(self):
        return izip(self._keys, self.itervalues())

    def keys(self):
        return self._keys[:]

    def iterkeys(self):
        return iter(self._keys)

    def pop(self, key, default=missing):
        if default is missing:
            return dict.pop(self, key)
        elif key not in self:
            return default
        self._keys.remove(key)
        return dict.pop(self, key, default)

    def popitem(self, key):
        self._keys.remove(key)
        return dict.popitem(key)

    def setdefault(self, key, default=None):
        if key not in self:
            self._keys.append(key)
        dict.setdefault(self, key, default)

    def _update(self, *args, **kwargs):
        recursive = kwargs.get('recursive', False)
        kwargs = kwargs.get('kwargs', {})
        
        sources = []
        if len(args) == 1:
            if hasattr(args[0], 'iteritems'):
                sources.append(args[0].iteritems())
            else:
                sources.append(iter(args[0]))
        elif args:
            raise TypeError('expected at most one positional argument')
        if kwargs:
            sources.append(kwargs.iteritems())
        for iterable in sources:
            for key, val in iterable:
                if (self.has_key(key) and recursive 
                        and isinstance(val, dict) 
                        and isinstance(self[key], dict)):
                    if hasattr(self[key], "recursive_update"):
                        self[key].recursive_update(val)
                    else:
                        self[key].update(val)
                else:
                    self[key] = val

    def update(self, *args, **kwargs):
        return self._update(kwargs=kwargs, *args)
    
    def recursive_update(self, *args, **kwargs):
        return self._update(kwargs=kwargs, recursive=True, *args)

    def values(self):
        return map(self.get, self._keys)

    def itervalues(self):
        return imap(self.get, self._keys)

    def index(self, item):
        return self._keys.index(item)

    def byindex(self, item):
        key = self._keys[item]
        return (key, dict.__getitem__(self, key))

    def reverse(self):
        self._keys.reverse()

    def sort(self, *args, **kwargs):
        self._keys.sort(*args, **kwargs)

    def __repr__(self):
        return 'odict.odict(%r)' % self.items()

    __copy__ = copy
    __iter__ = iterkeys


if __name__ == '__main__':
    import doctest
    doctest.testmod()


########NEW FILE########
