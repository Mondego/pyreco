__FILENAME__ = manager
from django.db.models import signals
from django.db.models.manager import Manager

from indexer.utils import Proxy

COLUMN_SEPARATOR = '__'

class LazyIndexLookup(Proxy):
    __slots__ = ('__data__', '__instance__')

    def __init__(self, model, model_class, queryset=None, **pairs):
        object.__setattr__(self, '__data__', (model, model_class, queryset, pairs))
        object.__setattr__(self, '__instance__', None)

    def _get_current_object(self):
        """
        Return the current object.  This is useful if you want the real object
        behind the proxy at a time for performance reasons or because you want
        to pass the object into a different context.
        """
        inst = self.__instance__
        if inst is not None:
            return inst
        model, model_class, qs, pairs = self.__data__
        
        app_label = model_class._meta.app_label
        module_name = model_class._meta.module_name

        if qs is None:
            qs = model_class.objects.all()

        tbl = model._meta.db_table
        main = model_class._meta.db_table
        pk = model_class._meta.pk.column
        for column, value in pairs.iteritems():
            #cid = '_i%d' % abs(hash(column))
            # print self.model.objects.filter(module_name=module_name, app_label=app_label, column=column, value=value).values_list('object_id')
            # qs = qs.filter(pk__in=self.model.objects.filter(module_name=module_name, app_label=app_label, column=column, value=value).values_list('object_id'))
            cid = tbl
            qs = qs.extra(
                # tables=['%s as %s' % (tbl, cid)],
                tables=[tbl],
                where=['%(cid)s.module_name = %%s and %(cid)s.app_label = %%s and %(cid)s.column = %%s and %(cid)s.value = %%s and %(cid)s.object_id = %(main)s.%(pk)s' % dict(
                    cid=cid,
                    pk=pk,
                    main=main,
                )],
                params=[
                    module_name,
                    app_label,
                    column,
                    value,
                ],
            )

        object.__setattr__(self, '__instance__', qs)
        return qs
    _current_object = property(_get_current_object)

class BaseLazyIndexLookup(LazyIndexLookup):
    def _get_current_object(self):
        """
        Return the current object.  This is useful if you want the real object
        behind the proxy at a time for performance reasons or because you want
        to pass the object into a different context.
        """
        inst = self.__instance__
        if inst is not None:
            return inst
        model, model_class, qs, pairs = self.__data__
        
        if qs is None:
            qs = model_class.objects.all()

        tbl = model._meta.db_table
        main = model_class._meta.db_table
        pk = model_class._meta.pk.column
        for column, value in pairs.iteritems():
            cid = tbl
            qs = qs.extra(
                tables=[tbl],
                where=['%(cid)s.column = %%s and %(cid)s.value = %%s and %(cid)s.object_id = %(main)s.%(pk)s' % dict(
                    cid=cid,
                    pk=pk,
                    main=main,
                )],
                params=[
                    column,
                    value,
                ],
            )

        object.__setattr__(self, '__instance__', qs)
        return qs
    _current_object = property(_get_current_object)

class IndexManager(Manager):
    def get_for_model(self, model_class, **kwargs):
        if len(kwargs) < 1:
            raise ValueError
        
        return LazyIndexLookup(self.model, model_class, None, **kwargs)
    
    def get_for_queryset(self, queryset, **kwargs):
        if len(kwargs) < 1:
            raise ValueError
        
        return LazyIndexLookup(self.model, queryset.model, queryset, **kwargs)
    
    def register_model(self, model_class, column, index_to=None):
        """Registers a model and an index for it."""
        if model_class not in self.model.indexes:
            self.model.indexes[model_class] = set([(column, index_to)])
        else:
            self.model.indexes[model_class].add((column, index_to))
        signals.post_save.connect(self.model.handle_save, sender=model_class)
        signals.pre_delete.connect(self.model.handle_delete, sender=model_class)
    
    def remove_from_index(self, instance):
        app_label = instance._meta.app_label
        module_name = instance._meta.module_name
        tbl = self.model._meta.db_table
        self.filter(app_label=app_label, module_name=module_name, object_id=instance.pk).delete()
    
    def save_in_index(self, instance, column, index_to=None):
        """Updates an index for an instance.
        
        You may pass column as base__sub to access
        values stored deeper in the hierarchy."""
        if index_to:
            index_to = instance._meta.get_field_by_name(index_to)[0]

        if not index_to:
            app_label = instance._meta.app_label
            module_name = instance._meta.module_name
            object_id = instance.pk
        else:
            app_label = index_to.rel.to._meta.app_label
            module_name = index_to.rel.to._meta.module_name
            object_id = getattr(instance, index_to.column)

        value = instance
        first = True
        for bit in column.split(COLUMN_SEPARATOR):
            if first:
                value = getattr(value, bit)
                first = False
            elif value is not None:
                value = value.get(bit)
        if not value:
            self.filter(app_label=app_label, module_name=module_name, object_id=object_id, column=column).delete()
        else:
            # TODO: in mysql this can be a single operation
            qs = self.filter(app_label=app_label, module_name=module_name, object_id=object_id, column=column)
            if qs.exists():
                qs.update(value=value)
            else:
                self.create(app_label=app_label, module_name=module_name, object_id=object_id, column=column, value=value)

    def create_index(self, model_class, column, index_to=None):
        """Creates and prepopulates an index.
        
        You may pass column as base__sub to access
        values stored deeper in the hierarchy."""
        
        # make sure the index exists
        if index_to:
            index_to = model_class._meta.get_field_by_name(index_to)[0]

        # must pull from original data
        qs = model_class.objects.all()
        column_bits = column.split(COLUMN_SEPARATOR)

        if not index_to:
            app_label = model_class._meta.app_label
            module_name = model_class._meta.module_name
        else:
            app_label = index_to.rel.to._meta.app_label
            module_name = index_to.rel.to._meta.module_name

        for m in qs:
            if not index_to:
                object_id = m.pk
            else:
                object_id = getattr(m, index_to.column)

            value = m
            first = True
            for bit in column.split(COLUMN_SEPARATOR):
                if first:
                    value = getattr(value, bit)
                    first = False
                else:
                    value = value.get(bit)
            if not value:
                continue
            self.create(app_label=app_label, module_name=module_name, object_id=object_id, column=column, value=value)
        self.register_model(model_class, column)

class BaseIndexManager(Manager):
    def get_for_index(self, **kwargs):
        if len(kwargs) < 1:
            raise ValueError
        
        return BaseLazyIndexLookup(self.model, self.model.get_model(), **kwargs)
    
    def get_for_queryset(self, queryset, **kwargs):
        if len(kwargs) < 1:
            raise ValueError
        
        return BaseLazyIndexLookup(self.model, queryset.model, queryset, **kwargs)
    
    def register_index(self, column, index_to=None):
        """Registers a model and an index for it."""
        self.model._indexes.add((column, index_to))
        model_class = self.model.get_model()
        signals.post_save.connect(self.model.handle_save, sender=model_class)
        signals.pre_delete.connect(self.model.handle_delete, sender=model_class)
    
    def remove_from_index(self, instance):
        tbl = self.model._meta.db_table
        self.filter(object_id=instance.pk).delete()
    
    def save_in_index(self, instance, column, index_to=None):
        """Updates an index for an instance.
        
        You may pass column as base__sub to access
        values stored deeper in the hierarchy."""
        if index_to:
            index_to = instance._meta.get_field_by_name(index_to)[0]

        if not index_to:
            object_id = instance.pk
        else:
            object_id = getattr(instance, index_to.column)

        value = instance
        first = True
        for bit in column.split(COLUMN_SEPARATOR):
            if first:
                value = getattr(value, bit)
                first = False
            elif value is not None:
                value = value.get(bit)
        if not value:
            self.filter(object_id=object_id, column=column).delete()
        else:
            # TODO: in mysql this can be a single operation
            qs = self.filter(object_id=object_id, column=column)
            if qs.exists():
                qs.update(value=value)
            else:
                self.create(object_id=object_id, column=column, value=value)

    def create_index(self, column, index_to=None):
        """Creates and prepopulates an index.
        
        You may pass column as base__sub to access
        values stored deeper in the hierarchy."""
        
        # make sure the index exists
        model_class = self.model.get_model()
        
        if index_to:
            index_to = model_class._meta.get_field_by_name(index_to)[0]

        # must pull from original data
        qs = model_class.objects.all()
        column_bits = column.split(COLUMN_SEPARATOR)

        for m in qs:
            if not index_to:
                object_id = m.pk
            else:
                object_id = getattr(m, index_to.column)

            value = m
            first = True
            for bit in column.split(COLUMN_SEPARATOR):
                if first:
                    value = getattr(value, bit)
                    first = False
                else:
                    value = value.get(bit)
            if not value:
                continue
            self.create(object_id=object_id, column=column, value=value)
        self.register_index(column)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Index'
        db.create_table('indexer_index', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app_label', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('module_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('column', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('indexer', ['Index'])

        # Adding unique constraint on 'Index', fields ['app_label', 'module_name', 'column', 'value', 'object_id']
        db.create_unique('indexer_index', ['app_label', 'module_name', 'column', 'value', 'object_id'])


    def backwards(self, orm):
        
        # Deleting model 'Index'
        db.delete_table('indexer_index')

        # Removing unique constraint on 'Index', fields ['app_label', 'module_name', 'column', 'value', 'object_id']
        db.delete_unique('indexer_index', ['app_label', 'module_name', 'column', 'value', 'object_id'])


    models = {
        'indexer.index': {
            'Meta': {'unique_together': "(('app_label', 'module_name', 'column', 'value', 'object_id'),)", 'object_name': 'Index'},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'column': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['indexer']

########NEW FILE########
__FILENAME__ = models
from django.db import models

from indexer.manager import IndexManager, BaseIndexManager

__all__ = ('BaseIndex', 'Index')

class BaseIndex(models.Model):
    object_id   = models.PositiveIntegerField()
    column      = models.CharField(max_length=32)
    value       = models.CharField(max_length=128)
    
    objects     = BaseIndexManager()
    
    _indexes     = set()
    model       = None
    
    class Meta:
        abstract = True
        unique_together = (('column', 'value', 'object_id'),)

    def __unicode__(self):
        return "%s=%s where pk is %s" % (self.column, self.value, self.object_id)

    @classmethod
    def get_model(cls):
        return cls.model

    @classmethod
    def handle_save(cls, sender, instance, created, **kwargs):
        """Handles updating this model's indexes."""
        for column, index_to in cls._indexes:
            cls.objects.save_in_index(instance, column, index_to)

    @classmethod
    def handle_delete(cls, sender, instance, **kwargs):
        """Handles updating this model's indexes."""
        cls.objects.remove_from_index(instance)

class Index(models.Model):
    app_label   = models.CharField(max_length=32)
    module_name = models.CharField(max_length=32)
    column      = models.CharField(max_length=32)
    value       = models.CharField(max_length=128)
    object_id   = models.PositiveIntegerField()
    
    objects     = IndexManager()
    
    indexes = {}
    
    class Meta:
        unique_together = (('app_label', 'module_name', 'column', 'value', 'object_id'),)

    def __unicode__(self):
        return "%s=%s in %s_%s where pk is %s" % (self.column, self.value, self.app_label, self.module_name, self.object_id)

    @classmethod
    def handle_save(cls, sender, instance, created, **kwargs):
        """Handles updating this model's indexes."""
        for column, index_to in Index.indexes[sender]:
            cls.objects.save_in_index(instance, column, index_to)

    @classmethod
    def handle_delete(cls, sender, instance, **kwargs):
        """Handles updating this model's indexes."""
        cls.objects.remove_from_index(instance)
########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',

            'south',

            'indexer',
            'indexer.tests',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
        SITE_ID=1,
        TEMPLATE_DEBUG=True,
    )
    import djcelery
    djcelery.setup_loader()

from django.test.simple import run_tests

def runtests(*test_args):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['indexer']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
########NEW FILE########
__FILENAME__ = models
from django.db import models

from indexer.models import BaseIndex

class IndexerObject(models.Model):
    name = models.CharField(max_length=32)

class TestIndex(BaseIndex):
    model = IndexerObject

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from indexer.tests.models import IndexerObject, TestIndex

class BaseIndexTestCase(TestCase):
    def setUp(self):
        # XXX: gotta ensure indexes are taken down
        TestIndex._indexes = set()
        TestIndex.objects.all().delete()
    
    def test_index_registration(self):
        TestIndex.objects.register_index('name')
        
        self.assertEquals(len(TestIndex._indexes), 1)
        self.assertEquals(list(TestIndex._indexes)[0], ('name', None))

    def test_index_signals(self):
        obj1 = IndexerObject.objects.create(name='foo')
        
        TestIndex.objects.register_index('name')
        
        self.assertEquals(TestIndex.objects.count(), 0)

        results = list(TestIndex.objects.get_for_index(name='foo'))
        
        self.assertEquals(len(results), 0)

        # Force backfill
        TestIndex.objects.create_index('name')

        self.assertEquals(TestIndex.objects.count(), 1)
        
        results = list(TestIndex.objects.get_for_index(name='foo'))
        
        self.assertEquals(len(results), 1)
        self.assertEquals(results[0], obj1)
    
        obj1.delete()
        
        self.assertEquals(TestIndex.objects.count(), 0)

        results = list(TestIndex.objects.get_for_index(name='foo'))
        
        self.assertEquals(len(results), 0)
        
########NEW FILE########
__FILENAME__ = utils
class Proxy(object):
    __slots__ = ('__dict__',)

    def __init__(self, instance):
        object.__setattr__(self, '__instance__', instance)

    def _get_current_object(self):
        """
        Return the current object.  This is useful if you want the real object
        behind the proxy at a time for performance reasons or because you want
        to pass the object into a different context.
        """
        return self.__instance__
    _current_object = property(_get_current_object)

    def __dict__(self):
        try:
            return self._current_object.__dict__
        except RuntimeError:
            return AttributeError('__dict__')
    __dict__ = property(__dict__)

    def __repr__(self):
        try:
            obj = self._current_object
        except RuntimeError:
            return '<%s unbound>' % self.__class__.__name__
        return repr(obj)

    def __nonzero__(self):
        try:
            return bool(self._current_object)
        except RuntimeError:
            return False

    def __unicode__(self):
        try:
            return unicode(self.__current_oject)
        except RuntimeError:
            return repr(self)

    def __dir__(self):
        try:
            return dir(self._current_object)
        except RuntimeError:
            return []

    __getattr__ = lambda x, i, j=None: getattr(x._current_object, i, j)
    __setattr__ = lambda x, i, j: setattr(x._current_object, i, j)

    def __setitem__(self, key, value):
        self._current_object[key] = value

    def __delitem__(self, key):
        del self._current_object[key]

    def __setslice__(self, i, j, seq):
        self._current_object[i:j] = seq

    def __delslice__(self, i, j):
        del self._current_object[i:j]

    __delattr__ = lambda x, n: delattr(x._current_object, n)
    __str__ = lambda x: str(x._current_object)
    __unicode__ = lambda x: unicode(x._current_object)
    __lt__ = lambda x, o: x._current_object < o
    __le__ = lambda x, o: x._current_object <= o
    __eq__ = lambda x, o: x._current_object == o
    __ne__ = lambda x, o: x._current_object != o
    __gt__ = lambda x, o: x._current_object > o
    __ge__ = lambda x, o: x._current_object >= o
    __cmp__ = lambda x, o: cmp(x._current_object, o)
    __hash__ = lambda x: hash(x._current_object)
    # attributes are currently not callable
    # __call__ = lambda x, *a, **kw: x._current_object(*a, **kw)
    __len__ = lambda x: len(x._current_object)
    __getitem__ = lambda x, i: x._current_object[i]
    __iter__ = lambda x: iter(x._current_object)
    __contains__ = lambda x, i: i in x._current_object
    __getslice__ = lambda x, i, j: x._current_object[i:j]
    __add__ = lambda x, o: x._current_object + o
    __sub__ = lambda x, o: x._current_object - o
    __mul__ = lambda x, o: x._current_object * o
    __floordiv__ = lambda x, o: x._current_object // o
    __mod__ = lambda x, o: x._current_object % o
    __divmod__ = lambda x, o: x._current_object.__divmod__(o)
    __pow__ = lambda x, o: x._current_object ** o
    __lshift__ = lambda x, o: x._current_object << o
    __rshift__ = lambda x, o: x._current_object >> o
    __and__ = lambda x, o: x._current_object & o
    __xor__ = lambda x, o: x._current_object ^ o
    __or__ = lambda x, o: x._current_object | o
    __div__ = lambda x, o: x._current_object.__div__(o)
    __truediv__ = lambda x, o: x._current_object.__truediv__(o)
    __neg__ = lambda x: -(x._current_object)
    __pos__ = lambda x: +(x._current_object)
    __abs__ = lambda x: abs(x._current_object)
    __invert__ = lambda x: ~(x._current_object)
    __complex__ = lambda x: complex(x._current_object)
    __int__ = lambda x: int(x._current_object)
    __long__ = lambda x: long(x._current_object)
    __float__ = lambda x: float(x._current_object)
    __oct__ = lambda x: oct(x._current_object)
    __hex__ = lambda x: hex(x._current_object)
    __index__ = lambda x: x._current_object.__index__()
    __coerce__ = lambda x, o: x.__coerce__(x, o)
    __enter__ = lambda x: x.__enter__()
    __exit__ = lambda x, *a, **kw: x.__exit__(*a, **kw)
########NEW FILE########
