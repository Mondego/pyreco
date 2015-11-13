__FILENAME__ = fields
"""Pickle field implementation for Django."""

from copy import deepcopy
from base64 import b64encode, b64decode
from zlib import compress, decompress
try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps

from django.db import models
from django.utils.encoding import force_unicode

from picklefield import DEFAULT_PROTOCOL

class PickledObject(str):
    """
    A subclass of string so it can be told whether a string is a pickled
    object or not (if the object is an instance of this class then it must
    [well, should] be a pickled one).

    Only really useful for passing pre-encoded values to ``default``
    with ``dbsafe_encode``, not that doing so is necessary. If you
    remove PickledObject and its references, you won't be able to pass
    in pre-encoded values anymore, but you can always just pass in the
    python objects themselves.

    """


def dbsafe_encode(value, compress_object=False, pickle_protocol=DEFAULT_PROTOCOL):
    # We use deepcopy() here to avoid a problem with cPickle, where dumps
    # can generate different character streams for same lookup value if
    # they are referenced differently.
    # The reason this is important is because we do all of our lookups as
    # simple string matches, thus the character streams must be the same
    # for the lookups to work properly. See tests.py for more information.
    if not compress_object:
        value = b64encode(dumps(deepcopy(value), pickle_protocol))
    else:
        value = b64encode(compress(dumps(deepcopy(value), pickle_protocol)))
    return PickledObject(value)


def dbsafe_decode(value, compress_object=False):
    if not compress_object:
        value = loads(b64decode(value))
    else:
        value = loads(decompress(b64decode(value)))
    return value


class PickledObjectField(models.Field):
    """
    A field that will accept *any* python object and store it in the
    database. PickledObjectField will optionally compress its values if
    declared with the keyword argument ``compress=True``.

    Does not actually encode and compress ``None`` objects (although you
    can still do lookups using None). This way, it is still possible to
    use the ``isnull`` lookup type correctly.
    """

    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.compress = kwargs.pop('compress', False)
        self.protocol = kwargs.pop('protocol', DEFAULT_PROTOCOL)
        kwargs.setdefault('editable', False)
        super(PickledObjectField, self).__init__(*args, **kwargs)

    def get_default(self):
        """
        Returns the default value for this field.

        The default implementation on models.Field calls force_unicode
        on the default, which means you can't set arbitrary Python
        objects as the default. To fix this, we just return the value
        without calling force_unicode on it. Note that if you set a
        callable as a default, the field will still call it. It will
        *not* try to pickle and encode it.

        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        # If the field doesn't have a default, then we punt to models.Field.
        return super(PickledObjectField, self).get_default()

    def to_python(self, value):
        """
        B64decode and unpickle the object, optionally decompressing it.

        If an error is raised in de-pickling and we're sure the value is
        a definite pickle, the error is allowed to propogate. If we
        aren't sure if the value is a pickle or not, then we catch the
        error and return the original value instead.

        """
        if value is not None:
            try:
                value = dbsafe_decode(value, self.compress)
            except:
                # If the value is a definite pickle; and an error is raised in
                # de-pickling it should be allowed to propogate.
                if isinstance(value, PickledObject):
                    raise
        return value

    def get_db_prep_value(self, value):
        """
        Pickle and b64encode the object, optionally compressing it.

        The pickling protocol is specified explicitly (by default 2),
        rather than as -1 or HIGHEST_PROTOCOL, because we don't want the
        protocol to change over time. If it did, ``exact`` and ``in``
        lookups would likely fail, since pickle would now be generating
        a different string.

        """
        if value is not None and not isinstance(value, PickledObject):
            # We call force_unicode here explicitly, so that the encoded string
            # isn't rejected by the postgresql_psycopg2 backend. Alternatively,
            # we could have just registered PickledObject with the psycopg
            # marshaller (telling it to store it like it would a string), but
            # since both of these methods result in the same value being stored,
            # doing things this way is much easier.
            value = force_unicode(dbsafe_encode(value, self.compress, self.protocol))
        return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def get_internal_type(self):
        return 'TextField'

    def get_db_prep_lookup(self, lookup_type, value, connection=None, prepared=False):
        if lookup_type not in ['exact', 'in', 'isnull']:
            raise TypeError('Lookup type %s is not supported.' % lookup_type)
        # The Field model already calls get_db_prep_value before doing the
        # actual lookup, so all we need to do is limit the lookup types.
        try:
            return super(PickledObjectField, self).get_db_prep_lookup(
                lookup_type, value, connection=connection, prepared=prepared)
        except TypeError:
            # Try not to break on older versions of Django, where the
            # `connection` and `prepared` parameters are not available.
            return super(PickledObjectField, self).get_db_prep_lookup(
                lookup_type, value)


# South support; see http://south.aeracode.org/docs/tutorial/part4.html#simple-inheritance
try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([], [r"^picklefield\.fields\.PickledObjectField"])

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
"""Unit tests for django-picklefield."""

from django.test import TestCase
from django.db import models
from django.core import serializers
from picklefield.fields import PickledObjectField

class TestingModel(models.Model):
    pickle_field = PickledObjectField()
    compressed_pickle_field = PickledObjectField(compress=True)
    default_pickle_field = PickledObjectField(default=({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5]))

class MinimalTestingModel(models.Model):
    pickle_field = PickledObjectField()

class TestCustomDataType(str):
    pass

class PickledObjectFieldTests(TestCase):
    def setUp(self):
        self.testing_data = (
            {1:2, 2:4, 3:6, 4:8, 5:10},
            'Hello World',
            (1, 2, 3, 4, 5),
            [1, 2, 3, 4, 5],
            TestCustomDataType('Hello World'),
        )
        return super(PickledObjectFieldTests, self).setUp()

    def testDataIntegriry(self):
        """
        Tests that data remains the same when saved to and fetched from
        the database, whether compression is enabled or not.

        """
        for value in self.testing_data:
            model_test = TestingModel(pickle_field=value, compressed_pickle_field=value)
            model_test.save()
            model_test = TestingModel.objects.get(id__exact=model_test.id)
            # Make sure that both the compressed and uncompressed fields return
            # the same data, even thought it's stored differently in the DB.
            self.assertEquals(value, model_test.pickle_field)
            self.assertEquals(value, model_test.compressed_pickle_field)
            model_test.delete()

        # Make sure the default value for default_pickled_field gets stored
        # correctly and that it isn't converted to a string.
        model_test = TestingModel()
        model_test.save()
        model_test = TestingModel.objects.get(id__exact=model_test.id)
        self.assertEquals(({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5]), model_test.default_pickle_field)

    def testLookups(self):
        """
        Tests that lookups can be performed on data once stored in the
        database, whether compression is enabled or not.

        One problem with cPickle is that it will sometimes output
        different streams for the same object, depending on how they are
        referenced. It should be noted though, that this does not happen
        for every object, but usually only with more complex ones.

        >>> from pickle import dumps
        >>> t = ({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, \
        ... 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5])
        >>> dumps(({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, \
        ... 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5]))
        "((dp0\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\np1\n(I1\nI2\nI3\nI4\nI5\ntp2\n(lp3\nI1\naI2\naI3\naI4\naI5\natp4\n."
        >>> dumps(t)
        "((dp0\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\np1\n(I1\nI2\nI3\nI4\nI5\ntp2\n(lp3\nI1\naI2\naI3\naI4\naI5\natp4\n."
        >>> # Both dumps() are the same using pickle.

        >>> from cPickle import dumps
        >>> t = ({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5])
        >>> dumps(({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5]))
        "((dp1\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\np2\n(I1\nI2\nI3\nI4\nI5\ntp3\n(lp4\nI1\naI2\naI3\naI4\naI5\nat."
        >>> dumps(t)
        "((dp1\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\n(I1\nI2\nI3\nI4\nI5\nt(lp2\nI1\naI2\naI3\naI4\naI5\natp3\n."
        >>> # But with cPickle the two dumps() are not the same!
        >>> # Both will generate the same object when loads() is called though.

        We can solve this by calling deepcopy() on the value before
        pickling it, as this copies everything to a brand new data
        structure.

        >>> from cPickle import dumps
        >>> from copy import deepcopy
        >>> t = ({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5])
        >>> dumps(deepcopy(({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5])))
        "((dp1\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\np2\n(I1\nI2\nI3\nI4\nI5\ntp3\n(lp4\nI1\naI2\naI3\naI4\naI5\nat."
        >>> dumps(deepcopy(t))
        "((dp1\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\np2\n(I1\nI2\nI3\nI4\nI5\ntp3\n(lp4\nI1\naI2\naI3\naI4\naI5\nat."
        >>> # Using deepcopy() beforehand means that now both dumps() are idential.
        >>> # It may not be necessary, but deepcopy() ensures that lookups will always work.

        Unfortunately calling copy() alone doesn't seem to fix the
        problem as it lies primarily with complex data types.

        >>> from cPickle import dumps
        >>> from copy import copy
        >>> t = ({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5])
        >>> dumps(copy(({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5])))
        "((dp1\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\np2\n(I1\nI2\nI3\nI4\nI5\ntp3\n(lp4\nI1\naI2\naI3\naI4\naI5\nat."
        >>> dumps(copy(t))
        "((dp1\nI1\nI1\nsI2\nI4\nsI3\nI6\nsI4\nI8\nsI5\nI10\nsS'Hello World'\n(I1\nI2\nI3\nI4\nI5\nt(lp2\nI1\naI2\naI3\naI4\naI5\natp3\n."

        """
        for value in self.testing_data:
            model_test = TestingModel(pickle_field=value, compressed_pickle_field=value)
            model_test.save()
            # Make sure that we can do an ``exact`` lookup by both the
            # pickle_field and the compressed_pickle_field.
            model_test = TestingModel.objects.get(pickle_field__exact=value, compressed_pickle_field__exact=value)
            self.assertEquals(value, model_test.pickle_field)
            self.assertEquals(value, model_test.compressed_pickle_field)
            # Make sure that ``in`` lookups also work correctly.
            model_test = TestingModel.objects.get(pickle_field__in=[value], compressed_pickle_field__in=[value])
            self.assertEquals(value, model_test.pickle_field)
            self.assertEquals(value, model_test.compressed_pickle_field)
            # Make sure that ``is_null`` lookups are working.
            self.assertEquals(1, TestingModel.objects.filter(pickle_field__isnull=False).count())
            self.assertEquals(0, TestingModel.objects.filter(pickle_field__isnull=True).count())
            model_test.delete()

        # Make sure that lookups of the same value work, even when referenced
        # differently. See the above docstring for more info on the issue.
        value = ({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5])
        model_test = TestingModel(pickle_field=value, compressed_pickle_field=value)
        model_test.save()
        # Test lookup using an assigned variable.
        model_test = TestingModel.objects.get(pickle_field__exact=value)
        self.assertEquals(value, model_test.pickle_field)
        # Test lookup using direct input of a matching value.
        model_test = TestingModel.objects.get(
            pickle_field__exact = ({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5]),
            compressed_pickle_field__exact = ({1: 1, 2: 4, 3: 6, 4: 8, 5: 10}, 'Hello World', (1, 2, 3, 4, 5), [1, 2, 3, 4, 5]),
        )
        self.assertEquals(value, model_test.pickle_field)
        model_test.delete()

    def testSerialization(self):
        model_test = MinimalTestingModel(pickle_field={'foo': 'bar'})
        json_test = serializers.serialize('json', [model_test])
        self.assertEquals(json_test,
                          '[{"pk": null,'
                          ' "model": "picklefield.minimaltestingmodel",'
                          ' "fields": {"pickle_field": "gAJ9cQFVA2Zvb3ECVQNiYXJxA3Mu"}}]')
        for deserialized_test in serializers.deserialize('json', json_test):
            self.assertEquals(deserialized_test.object,
                              model_test)

########NEW FILE########
