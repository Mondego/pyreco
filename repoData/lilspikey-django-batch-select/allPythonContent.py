__FILENAME__ = models
from django.db.models.query import QuerySet
from django.db import models, connection
from django.db.models.fields import FieldDoesNotExist

from django.conf import settings

from replay import Replay

def _not_exists(fieldname):
    raise FieldDoesNotExist('"%s" is not a ManyToManyField or a reverse ForeignKey relationship' % fieldname)

def _check_field_exists(model, fieldname):
    try:
        field_object, model, direct, m2m = model._meta.get_field_by_name(fieldname)
    except FieldDoesNotExist:
        # might be after reverse foreign key
        # which by default don't have the name we expect
        if fieldname.endswith('_set'):
            return _check_field_exists(model, fieldname[:-len('_set')])
        else:
            raise
    if not m2m:
        if direct: # reverse foreign key relationship
            _not_exists(fieldname)
    return fieldname

def _id_attr(id_column):
    # mangle the id column name, so we can make sure
    # the postgres doesn't complain about not quoting
    # field names (this helps make sure we don't clash
    # with the regular id column)
    return '__%s' % id_column.lower()

def _select_related_instances(related_model, related_name, ids, db_table, id_column):
    id__in_filter={ ('%s__pk__in' % related_name): ids }
    qn = connection.ops.quote_name
    select = { _id_attr(id_column): '%s.%s' % (qn(db_table), qn(id_column)) }
    related_instances = related_model._default_manager \
                            .filter(**id__in_filter) \
                            .extra(select=select)
    return related_instances

def batch_select(model, instances, target_field_name, fieldname, filter=None):
    '''
    basically do an extra-query to select the many-to-many
    field values into the instances given. e.g. so we can get all
    Entries and their Tags in two queries rather than n+1
    
    returns a list of the instances with the newly attached fields
    
    batch_select(Entry, Entry.objects.all(), 'tags_all', 'tags')
    
    would return a list of Entry objects with 'tags_all' fields
    containing the tags for that Entry
    
    filter is a function that can be used alter the extra-query - it 
    takes a queryset and returns a filtered version of the queryset
    
    NB: this is a semi-private API at the moment, but may be useful if you
    dont want to change your model/manager.
    '''
    
    fieldname = _check_field_exists(model, fieldname)
    
    instances = list(instances)
    ids = [instance.pk for instance in instances]
    
    field_object, model, direct, m2m = model._meta.get_field_by_name(fieldname)
    if m2m:
        if not direct:
            m2m_field = field_object.field
            related_model = field_object.model
            related_name = m2m_field.name
            id_column = m2m_field.m2m_reverse_name()
            db_table = m2m_field.m2m_db_table()
        else:
            m2m_field = field_object
            related_model = m2m_field.rel.to # model on other end of relationship
            related_name = m2m_field.related_query_name()
            id_column = m2m_field.m2m_column_name()
            db_table  = m2m_field.m2m_db_table()
    elif not direct:
        # handle reverse foreign key relationships
        fk_field = field_object.field
        related_model = field_object.model
        related_name  = fk_field.name
        id_column = fk_field.column
        db_table = related_model._meta.db_table
    
    related_instances = _select_related_instances(related_model, related_name, 
                                                  ids, db_table, id_column)
    
    if filter:
        related_instances = filter(related_instances)
    
    grouped = {}
    id_attr = _id_attr(id_column)
    for related_instance in related_instances:
        instance_id = getattr(related_instance, id_attr)
        group = grouped.get(instance_id, [])
        group.append(related_instance)
        grouped[instance_id] = group
    
    for instance in instances:
        setattr(instance, target_field_name, grouped.get(instance.pk, []))
    
    return instances

class Batch(Replay):
    # functions on QuerySet that we can invoke via this batch object
    __replayable__ = ('filter', 'exclude', 'annotate', 
                      'order_by', 'reverse', 'select_related',
                      'extra', 'defer', 'only', 'batch_select')
    
    def __init__(self, m2m_fieldname, **filter):
        super(Batch,self).__init__()
        self.m2m_fieldname = m2m_fieldname
        self.target_field_name = '%s_all' % m2m_fieldname
        if filter: # add a filter replay method
            self._add_replay('filter', *(), **filter)
    
    def clone(self):
        cloned = super(Batch, self).clone(self.m2m_fieldname)
        cloned.target_field_name = self.target_field_name
        return cloned

class BatchQuerySet(QuerySet):
    
    def _clone(self, *args, **kwargs):
        query = super(BatchQuerySet, self)._clone(*args, **kwargs)
        batches = getattr(self, '_batches', None)
        if batches:
            query._batches = set(batches)
        return query
    
    def _create_batch(self, batch_or_str, target_field_name=None):
        batch = batch_or_str
        if isinstance(batch_or_str, basestring):
            batch = Batch(batch_or_str)
        if target_field_name:
            batch.target_field_name = target_field_name
        
        _check_field_exists(self.model, batch.m2m_fieldname)
        return batch
    
    def batch_select(self, *batches, **named_batches):
        batches = getattr(self, '_batches', set()) | \
                  set(self._create_batch(batch) for batch in batches) | \
                  set(self._create_batch(batch, target_field_name) \
                        for target_field_name, batch in named_batches.items())
        
        query = self._clone()
        query._batches = batches
        return query
    
    def iterator(self):
        result_iter = super(BatchQuerySet, self).iterator()
        batches = getattr(self, '_batches', None)
        if batches:
            results = list(result_iter)
            for batch in batches:
                results = batch_select(self.model, results,
                                       batch.target_field_name,
                                       batch.m2m_fieldname,
                                       batch.replay)
            return iter(results)
        return result_iter

class BatchManager(models.Manager):
    use_for_related_fields = True
    
    def get_query_set(self):
        return BatchQuerySet(self.model)
    
    def batch_select(self, *batches, **named_batches):
        return self.all().batch_select(*batches, **named_batches)

if getattr(settings, 'TESTING_BATCH_SELECT', False):
    class Tag(models.Model):
        name = models.CharField(max_length=32)
        
        objects = BatchManager()
    
    class Section(models.Model):
        name = models.CharField(max_length=32)
        
        objects = BatchManager()
    
    class Location(models.Model):
        name = models.CharField(max_length=32)
    
    class Entry(models.Model):
        title = models.CharField(max_length=255)
        section  = models.ForeignKey(Section, blank=True, null=True)
        location = models.ForeignKey(Location, blank=True, null=True)
        tags = models.ManyToManyField(Tag)
        
        objects = BatchManager()
    
    class Country(models.Model):
        # non id pk
        name = models.CharField(primary_key=True, max_length=100)
        locations = models.ManyToManyField(Location)
        
        objects = BatchManager()


########NEW FILE########
__FILENAME__ = replay
'''
Class that we can use to chain together several methods calls (in
the same fashion as we would with a QuerySet) and then "replay" them
later on a different object.
'''

def create_replay_method(name):
    def _replay_method(self, *args, **kwargs):
        cloned = self.clone()
        cloned._add_replay(name, *args, **kwargs)
        return cloned
    _replay_method.__name__ = name
    _replay_method.__doc__ = 'replay %s method on target object' % name
    return _replay_method

class ReplayMetaClass(type):
    def __new__(meta, classname, bases, class_dict):
        replay_methods = class_dict.get('__replayable__', [])
        for name in replay_methods:
            class_dict[name] = create_replay_method(name)
        return type.__new__(meta, classname, bases, class_dict)

class Replay(object):
    __metaclass__ = ReplayMetaClass
    
    def __init__(self):
        self._replays=[]
    
    def _add_replay(self, method_name, *args, **kwargs):
        self._replays.append((method_name, args, kwargs))
    
    def clone(self, *args, **kwargs):
        klass = self.__class__
        cloned = klass(*args, **kwargs)
        cloned._replays=self._replays[:]
        return cloned
    
    def replay(self, target):
        result = target
        for method_name, args, kwargs in self._replays:
            method = getattr(result, method_name)
            result = method(*args, **kwargs)
        return result

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings

if getattr(settings, 'TESTING_BATCH_SELECT', False):
    from django.test import TransactionTestCase
    from django.db.models.fields import FieldDoesNotExist
    from batch_select.models import Tag, Entry, Section, Batch, Location,\
                                    _select_related_instances, Country,\
                                    _check_field_exists
    from batch_select.replay import Replay
    from django import db
    from django.db.models import Count
    import unittest
    
    def with_debug_queries(fn):
        def _decorated(*arg, **kw):
            db.reset_queries()
            old_debug, settings.DEBUG = settings.DEBUG, True
            result = fn(*arg, **kw)
            settings.DEBUG = old_debug
            return result
        return _decorated
    
    def _create_tags(*names):
        return [Tag.objects.create(name=name) for name in names]
    
    def _create_entries(count):
        return [Entry.objects.create() for _ in xrange(count)]
    
    class TestBatchSelect(TransactionTestCase):
        
        def test_batch_select_empty(self):
            entries = Entry.objects.batch_select('tags')
            self.failUnlessEqual([], list(entries))
        
        def test_batch_select_no_tags(self):
            entry = Entry.objects.create()
            entries = Entry.objects.batch_select('tags')
            self.failUnlessEqual([entry], list(entries))
        
        def test_batch_select_default_name(self):
            entry = _create_entries(1)[0]
            tag1, tag2 = _create_tags('tag1', 'tag2')
            
            entry.tags.add(tag1, tag2)
            
            entry = Entry.objects.batch_select('tags')[0]
            
            self.failIf( getattr(entry, 'tags_all', None) is None )
            self.failUnlessEqual( set([tag1, tag2]), set(entry.tags_all) )
        
        def test_batch_select_non_default_name(self):
            entry = _create_entries(1)[0]
            tag1, tag2 = _create_tags('tag1', 'tag2')
            
            entry.tags.add(tag1, tag2)
            
            entry = Entry.objects.batch_select(batch_tags='tags')[0]
            
            self.failIf( getattr(entry, 'batch_tags', None) is None )
            self.failUnlessEqual( set([tag1, tag2]), set(entry.batch_tags) )
        
        def test_batch_select_with_tags(self):
            entry1, entry2, entry3, entry4 = _create_entries(4)
            tag1, tag2, tag3 = _create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            
            entry2.tags.add(tag2)
            
            entry3.tags.add(tag2, tag3)
            
            entries = Entry.objects.batch_select('tags').order_by('id')
            entries = list(entries)
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], entries)
            
            entry1, entry2, entry3, entry4 = entries
            
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
            self.failUnlessEqual(set([tag2]),             set(entry2.tags_all))
            self.failUnlessEqual(set([tag2, tag3]),       set(entry3.tags_all))
            self.failUnlessEqual(set([]),                 set(entry4.tags_all))
        
        def test_batch_select_get(self):
            entry = Entry.objects.create()
            tag1, tag2, tag3 = _create_tags('tag1', 'tag2', 'tag3')
            
            entry.tags.add(tag1, tag2, tag3)
            
            entry = Entry.objects.batch_select('tags').get()
            
            self.failIf( getattr(entry, 'tags_all', None) is None )
            self.failUnlessEqual( set([tag1, tag2, tag3]), set(entry.tags_all) )
        
        def test_batch_select_caching_works(self):
            # make sure that query set caching still
            # works and doesn't alter the added fields
            entry1, entry2, entry3, entry4 = _create_entries(4)
            tag1, tag2, tag3 = _create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            
            entry2.tags.add(tag2)
            
            entry3.tags.add(tag2, tag3)
            
            qs = Entry.objects.batch_select(Batch('tags')).order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            
            entry1, entry2, entry3, entry4 = list(qs)
            
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
            self.failUnlessEqual(set([tag2]),             set(entry2.tags_all))
            self.failUnlessEqual(set([tag2, tag3]),       set(entry3.tags_all))
            self.failUnlessEqual(set([]),                 set(entry4.tags_all))
            
        def test_no_batch_select(self):
            # make sure things still work when we don't do a batch select
            entry1, entry2, entry3, entry4 = _create_entries(4)
            
            qs = Entry.objects.all().order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
        
        def test_batch_select_after_new_query(self):
            entry1, entry2, entry3, entry4 = _create_entries(4)
            tag1, tag2, tag3 = _create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            
            entry2.tags.add(tag2)
            
            entry3.tags.add(tag2, tag3)
            
            qs = Entry.objects.batch_select(Batch('tags')).order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            
            entry1, entry2, entry3, entry4 = list(qs)
            
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
            self.failUnlessEqual(set([tag2]),             set(entry2.tags_all))
            self.failUnlessEqual(set([tag2, tag3]),       set(entry3.tags_all))
            self.failUnlessEqual(set([]),                 set(entry4.tags_all))
            
            new_qs = qs.filter(id=entry1.id)
            
            self.failUnlessEqual([entry1], list(new_qs))
            
            entry1 = list(new_qs)[0]
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
        
        @with_debug_queries
        def test_batch_select_minimal_queries(self):
            # make sure we are only doing the number of sql queries we intend to
            entry1, entry2, entry3, entry4 = _create_entries(4)
            tag1, tag2, tag3 = _create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            entry2.tags.add(tag2)
            entry3.tags.add(tag2, tag3)
            
            db.reset_queries()
            
            qs = Entry.objects.batch_select(Batch('tags')).order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            
            # this should have resulted in only two queries
            self.failUnlessEqual(2, len(db.connection.queries))
            
            # double-check result is cached, and doesn't trigger more queries
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            self.failUnlessEqual(2, len(db.connection.queries))
        
        @with_debug_queries
        def test_no_batch_select_minimal_queries(self):
            # check we haven't altered the original querying behaviour
            entry1, entry2, entry3 = _create_entries(3)
            
            db.reset_queries()

            qs = Entry.objects.order_by('id')

            self.failUnlessEqual([entry1, entry2, entry3], list(qs))

            # this should have resulted in only two queries
            self.failUnlessEqual(1, len(db.connection.queries))
            
            # check caching still works
            self.failUnlessEqual([entry1, entry2, entry3], list(qs))
            self.failUnlessEqual(1, len(db.connection.queries))
        
        def test_batch_select_non_existant_field(self):
            try:
                qs = Entry.objects.batch_select(Batch('qwerty')).order_by('id')
                self.fail('selected field that does not exist')
            except FieldDoesNotExist:
                pass
        
        def test_batch_select_non_m2m_field(self):
            try:
                qs = Entry.objects.batch_select(Batch('title')).order_by('id')
                self.fail('selected field that is not m2m field')
            except FieldDoesNotExist:
                pass
        
        def test_batch_select_empty_one_to_many(self):
            sections = Section.objects.batch_select('entry')
            self.failUnlessEqual([], list(sections))
        
        def test_batch_select_one_to_many_no_children(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            
            sections = Section.objects.batch_select('entry').order_by('id')
            self.failUnlessEqual([section1, section2], list(sections))
        
        def test_batch_select_one_to_many_with_children(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            section3 = Section.objects.create(name='s3')
            
            entry1 = Entry.objects.create(section=section1)
            entry2 = Entry.objects.create(section=section1)
            entry3 = Entry.objects.create(section=section3)
            
            sections = Section.objects.batch_select('entry').order_by('id')
            self.failUnlessEqual([section1, section2, section3], list(sections))
            
            section1, section2, section3 = list(sections)
            
            self.failUnlessEqual(set([entry1, entry2]), set(section1.entry_all))
            self.failUnlessEqual(set([]),               set(section2.entry_all))
            self.failUnlessEqual(set([entry3]),         set(section3.entry_all))
        
        def test___check_field_exists_full_field_name(self):
            # make sure we can retrieve the "real" fieldname
            # given the full fieldname for a reverse foreign key
            # relationship
            # e.g. give "entry_set" we should get "entry"
            self.failUnlessEqual("entry", _check_field_exists(Section, "entry_set"))
        
        def test___check_field_exists_full_field_name_non_existant_field(self):
            try:
                _check_field_exists(Section, "qwerty_set")
                self.fail('selected field that does not exist')
            except FieldDoesNotExist:
                pass
        
        def test_batch_select_one_to_many_with_children_full_field_name(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            section3 = Section.objects.create(name='s3')

            entry1 = Entry.objects.create(section=section1)
            entry2 = Entry.objects.create(section=section1)
            entry3 = Entry.objects.create(section=section3)

            sections = Section.objects.batch_select('entry_set').order_by('id')
            self.failUnlessEqual([section1, section2, section3], list(sections))

            section1, section2, section3 = list(sections)

            self.failUnlessEqual(set([entry1, entry2]), set(section1.entry_set_all))
            self.failUnlessEqual(set([]),               set(section2.entry_set_all))
            self.failUnlessEqual(set([entry3]),         set(section3.entry_set_all))
        
        @with_debug_queries
        def test_batch_select_one_to_many_with_children_minimal_queries(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            section3 = Section.objects.create(name='s3')
            
            entry1 = Entry.objects.create(section=section1)
            entry2 = Entry.objects.create(section=section2)
            entry3 = Entry.objects.create(section=section3)
            
            db.reset_queries()
            
            sections = Section.objects.batch_select('entry').order_by('id')
            self.failUnlessEqual([section1, section2, section3], list(sections))
            
            # this should have resulted in only two queries
            self.failUnlessEqual(2, len(db.connection.queries))
            
            section1, section2, section3 = list(sections)
            
            self.failUnlessEqual(set([entry1]), set(section1.entry_all))
            self.failUnlessEqual(set([entry2]), set(section2.entry_all))
            self.failUnlessEqual(set([entry3]), set(section3.entry_all))
    
    class TestBatchSelectQuerySetMethods(TransactionTestCase):
        
        def setUp(self):
            super(TransactionTestCase, self).setUp()
            self.entry1, self.entry2, self.entry3, self.entry4 = _create_entries(4)
            # put tags names in different order to id
            self.tag2, self.tag1, self.tag3 = _create_tags('tag2', 'tag1', 'tag3')
            
            self.entry1.tags.add(self.tag1, self.tag2, self.tag3)
            self.entry2.tags.add(self.tag2)
            self.entry3.tags.add(self.tag2, self.tag3)            
        
        def test_batch_select_filtering_name_params(self):
            entries = Entry.objects.batch_select(Batch('tags', name='tag1')).order_by('id')
            entries = list(entries)
            
            self.failUnlessEqual([self.entry1, self.entry2, self.entry3, self.entry4],
                                  entries)
            
            entry1, entry2, entry3, entry4 = entries

            self.failUnlessEqual(set([self.tag1]), set(entry1.tags_all))
            self.failUnlessEqual(set([]),     set(entry2.tags_all))
            self.failUnlessEqual(set([]),     set(entry3.tags_all))
            self.failUnlessEqual(set([]),     set(entry4.tags_all))
        
        def test_batch_select_filter(self):
            entries = Entry.objects.batch_select(Batch('tags').filter(name='tag2')).order_by('id')
            entries = list(entries)

            self.failUnlessEqual([self.entry1, self.entry2, self.entry3, self.entry4],
                                 entries)

            entry1, entry2, entry3, entry4 = entries

            self.failUnlessEqual(set([self.tag2]), set(entry1.tags_all))
            self.failUnlessEqual(set([self.tag2]), set(entry2.tags_all))
            self.failUnlessEqual(set([self.tag2]), set(entry3.tags_all))
            self.failUnlessEqual(set([]),     set(entry4.tags_all))
        
        def test_batch_select_exclude(self):
            entries = Entry.objects.batch_select(Batch('tags').exclude(name='tag2')).order_by('id')
            entries = list(entries)

            self.failUnlessEqual([self.entry1, self.entry2, self.entry3, self.entry4],
                                  entries)

            entry1, entry2, entry3, entry4 = entries

            self.failUnlessEqual(set([self.tag1, self.tag3]), set(entry1.tags_all))
            self.failUnlessEqual(set([]),                     set(entry2.tags_all))
            self.failUnlessEqual(set([self.tag3]),            set(entry3.tags_all))
            self.failUnlessEqual(set([]),                     set(entry4.tags_all))
        
        def test_batch_order_by_name(self):
            entries = Entry.objects.batch_select(Batch('tags').order_by('name')).order_by('id')
            entries = list(entries)

            self.failUnlessEqual([self.entry1, self.entry2, self.entry3, self.entry4],
                                  entries)

            entry1, entry2, entry3, entry4 = entries

            self.failUnlessEqual([self.tag1, self.tag2, self.tag3], entry1.tags_all)
            self.failUnlessEqual([self.tag2],                       entry2.tags_all)
            self.failUnlessEqual([self.tag2, self.tag3],            entry3.tags_all)
            self.failUnlessEqual([],                                entry4.tags_all)
    
        def test_batch_order_by_id(self):
            entries = Entry.objects.batch_select(Batch('tags').order_by('id')).order_by('id')
            entries = list(entries)

            self.failUnlessEqual([self.entry1, self.entry2, self.entry3, self.entry4],
                                  entries)

            entry1, entry2, entry3, entry4 = entries

            self.failUnlessEqual([self.tag2, self.tag1, self.tag3], entry1.tags_all)
            self.failUnlessEqual([self.tag2],                       entry2.tags_all)
            self.failUnlessEqual([self.tag2, self.tag3],            entry3.tags_all)
            self.failUnlessEqual([],                                entry4.tags_all)
        
        def test_batch_reverse(self):
            entries = Entry.objects.batch_select(Batch('tags').order_by('name').reverse()).order_by('id')
            entries = list(entries)

            self.failUnlessEqual([self.entry1, self.entry2, self.entry3, self.entry4],
                                  entries)

            entry1, entry2, entry3, entry4 = entries

            self.failUnlessEqual([self.tag3, self.tag2, self.tag1], entry1.tags_all)
            self.failUnlessEqual([self.tag2],                       entry2.tags_all)
            self.failUnlessEqual([self.tag3, self.tag2],            entry3.tags_all)
            self.failUnlessEqual([],                                entry4.tags_all)
        
        def test_batch_annotate(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            section3 = Section.objects.create(name='s3')
            
            entry1 = Entry.objects.create(section=section1)
            entry2 = Entry.objects.create(section=section1)
            entry3 = Entry.objects.create(section=section3)
            
            entry1.tags.add(self.tag2, self.tag3, self.tag1)
            entry3.tags.add(self.tag2, self.tag3)
            
            batch = Batch('entry').order_by('id').annotate(Count('tags'))
            sections = Section.objects.batch_select(batch).order_by('id')
            sections = list(sections)
            self.failUnlessEqual([section1, section2, section3], sections)
            
            section1, section2, section3 = sections
            
            self.failUnlessEqual([entry1, entry2], section1.entry_all)
            self.failUnlessEqual([],               section2.entry_all)
            self.failUnlessEqual([entry3],         section3.entry_all)
            
            self.failUnlessEqual(3, section1.entry_all[0].tags__count)
            self.failUnlessEqual(0, section1.entry_all[1].tags__count)
            self.failUnlessEqual(2, section3.entry_all[0].tags__count)
        
        @with_debug_queries
        def test_batch_select_related(self):
            # verify using select related doesn't tigger more queries
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            section3 = Section.objects.create(name='s3')
            
            location = Location.objects.create(name='home')
            
            entry1 = Entry.objects.create(section=section1, location=location)
            entry2 = Entry.objects.create(section=section1)
            entry3 = Entry.objects.create(section=section3)

            entry1.tags.add(self.tag2, self.tag3, self.tag1)
            entry3.tags.add(self.tag2, self.tag3)

            db.reset_queries()
            
            batch = Batch('entry').order_by('id').select_related('location')
            sections = Section.objects.batch_select(batch).order_by('id')
            sections = list(sections)
            self.failUnlessEqual([section1, section2, section3], sections)

            section1, section2, section3 = sections

            self.failUnlessEqual([entry1, entry2], section1.entry_all)
            self.failUnlessEqual([],               section2.entry_all)
            self.failUnlessEqual([entry3],         section3.entry_all)
            
            self.failUnlessEqual(2, len(db.connection.queries))
            db.reset_queries()
            
            entry1, entry2 = section1.entry_all
            
            self.failUnlessEqual(0, len(db.connection.queries))
            self.failUnlessEqual(location, entry1.location)
            self.failUnlessEqual(0, len(db.connection.queries))
            self.failUnless( entry2.location is None )
            self.failUnlessEqual(0, len(db.connection.queries))
        
        def _check_name_deferred(self, batch):
            entries = Entry.objects.batch_select(batch).order_by('id')
            entries = list(entries)
            
            self.failUnlessEqual([self.entry1, self.entry2, self.entry3, self.entry4],
                                  entries)
            
            self.failUnlessEqual(2, len(db.connection.queries))
            db.reset_queries()
            
            entry1, entry2, entry3, entry4 = entries
            
            self.failUnlessEqual(3, len(entry1.tags_all))
            self.failUnlessEqual(1, len(entry2.tags_all))
            self.failUnlessEqual(2, len(entry3.tags_all))
            self.failUnlessEqual(0, len(entry4.tags_all))
            
            self.failUnlessEqual(0, len(db.connection.queries))
            
            # as name has been defered it should trigger a query when we
            # try to access it
            self.failUnlessEqual( self.tag2.name, entry1.tags_all[0].name )
            self.failUnlessEqual(1, len(db.connection.queries))
            self.failUnlessEqual( self.tag1.name, entry1.tags_all[1].name )
            self.failUnlessEqual(2, len(db.connection.queries))
            self.failUnlessEqual( self.tag3.name, entry1.tags_all[2].name )
            self.failUnlessEqual(3, len(db.connection.queries))
        
        @with_debug_queries
        def test_batch_defer(self):
            batch = Batch('tags').order_by('id').defer('name')
            self._check_name_deferred(batch)

        @with_debug_queries
        def test_batch_only(self):
            batch = Batch('tags').order_by('id').only('id')
            self._check_name_deferred(batch)
        
        def test_batch_select_reverse_m2m(self):
            entry1, entry2, entry3, entry4 = _create_entries(4)
            tag1, tag2, tag3 = _create_tags('tag1', 'tag2', 'tag3')

            entry1.tags.add(tag1, tag2, tag3)

            entry2.tags.add(tag2)

            entry3.tags.add(tag2, tag3)

            tags = Tag.objects.batch_select('entry')\
                              .filter(id__in=[tag1.id, tag2.id, tag3.id])\
                              .order_by('id')
            tags = list(tags)

            self.failUnlessEqual([tag1, tag2, tag3], tags)

            tag1, tag2, tag3 = tags

            self.failUnlessEqual(set([entry1]), set(tag1.entry_all))
            self.failUnlessEqual(set([entry1, entry2, entry3]),
                                 set(tag2.entry_all))
            self.failUnlessEqual(set([entry1, entry3]), set(tag3.entry_all))

        def test_non_id_primary_key(self):
            uk = Country.objects.create(name='United Kingdom')
            brighton = Location.objects.create(name='Brighton')
            hove = Location.objects.create(name='Hove')

            uk.locations.add(brighton, hove)

            countries = Country.objects.batch_select('locations')
            countries = list(countries)

            self.failUnlessEqual([uk], countries)

            uk = countries[0]
            self.failUnlessEqual(set([brighton, hove]), set(uk.locations_all))

        @with_debug_queries
        def test_batch_nested(self):
            section1 = Section.objects.create(name='s1')

            entry1 = Entry.objects.create(section=section1)
            entry2 = Entry.objects.create(section=section1)

            tag1, tag2, tag3 = _create_tags('tag1', 'tag2', 'tag3')

            entry1.tags.add(tag1, tag3)
            entry2.tags.add(tag2)

            db.reset_queries()

            entry_batch = Batch('entry_set').batch_select('tags')
            sections = Section.objects.batch_select(entries=entry_batch)
            sections = list(sections)
            section1 = sections[0]
            section1_tags = [tag for entry in section1.entries
                             for tag in entry.tags_all]

            self.failUnlessEqual(set([tag1, tag2, tag3]), set(section1_tags))
            self.failUnlessEqual(3, len(db.connection.queries))


    class ReplayTestCase(unittest.TestCase):
        
        def setUp(self):
            class ReplayTest(Replay):
                __replayable__ = ('lower', 'upper', 'replace')
            self.klass = ReplayTest
            self.instance = ReplayTest()
        
        def test_replayable_methods_present_on_class(self):
            self.failIf( getattr(self.klass, 'lower', None) is None )
            self.failIf( getattr(self.klass, 'upper', None) is None )
            self.failIf( getattr(self.klass, 'replace', None) is None )
        
        def test_replayable_methods_present_on_instance(self):
            self.failIf( getattr(self.instance, 'lower', None) is None )
            self.failIf( getattr(self.instance, 'upper', None) is None )
            self.failIf( getattr(self.instance, 'replace', None) is None )
        
        def test_replay_methods_recorded(self):
            r = self.instance
            self.failUnlessEqual([], r._replays)
            
            self.failIf(r == r.upper())
            
            self.failUnlessEqual([('upper', (), {})], r.upper()._replays)
            self.failUnlessEqual([('lower', (), {})], r.lower()._replays)
            self.failUnlessEqual([('replace', (), {})], r.replace()._replays)
            
            self.failUnlessEqual([('upper', (1,), {})], r.upper(1)._replays)
            self.failUnlessEqual([('upper', (1,), {'param': 's'})], r.upper(1, param='s')._replays)
            
            self.failUnlessEqual([('upper', (), {'name__contains': 'test'}),
                                  ('replace', ('id',), {})],
                                 r.upper(name__contains='test').replace('id')._replays)
        
        def test_replay_no_replay(self):
            r = self.instance
            s = 'gfjhGF&'
            self.failUnlessEqual(s, r.replay(s))
        
        def test_replay_single_call(self):
            r = self.instance.upper()
            self.failUnlessEqual('MYWORD', r.replay('MyWord'))
            
            r = self.instance.lower()
            self.failUnlessEqual('myword', r.replay('MyWord'))
            
            r = self.instance.replace('a', 'b')
            self.failUnlessEqual('bbb', r.replay('aaa'))
            
            r = self.instance.replace('a', 'b', 1)
            self.failUnlessEqual('baa', r.replay('aaa'))

    class QuotingTestCase(TransactionTestCase):
        """Ensure correct quoting of table and field names in queries"""

        @with_debug_queries
        def test_uses_backend_specific_quoting(self):
            """Backend-specific quotes should be used

            Table and field names should be quoted with the quote_name
            function provided by the database backend.  The test here
            is a bit trivial since a real-life test case with
            PostgreSQL schema tricks or other table/field name munging
            would be difficult.
            """
            qn = db.connection.ops.quote_name
            qs = _select_related_instances(Entry, 'section', [1],
                                           'batch_select_entry', 'section_id')
            db.reset_queries()
            list(qs)
            sql = db.connection.queries[-1]['sql']
            self.failUnless(sql.startswith('SELECT (%s.%s) AS ' %(
                        qn('batch_select_entry'), qn('section_id'))))

        @with_debug_queries
        def test_batch_select_related_quoted_section_id(self):
            """Field names should be quoted in the WHERE clause

            PostgreSQL is particularly picky about quoting when table
            or field names contain mixed case
            """
            section = Section.objects.create(name='s1')
            entry = Entry.objects.create(section=section)

            db.reset_queries()
            sections = Section.objects.batch_select('entry').all()
            sections[0]
            sql = db.connection.queries[-1]['sql']
            correct_where = ' WHERE "batch_select_entry"."section_id" IN (1)'
            self.failUnless(sql.endswith(correct_where),
                            '"section_id" is not correctly quoted in the WHERE '
                            'clause of %r' % sql)

########NEW FILE########
__FILENAME__ = test_settings

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Django 1.2 and less
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'
# Django 1.3 and above
DATABASES = {
    'default': {
        'NAME': DATABASE_NAME,
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

INSTALLED_APPS = ( 'batch_select', )


TESTING_BATCH_SELECT=True

# enable this for coverage (using django test coverage 
# http://pypi.python.org/pypi/django-test-coverage )
#TEST_RUNNER = 'django-test-coverage.runner.run_tests'
#COVERAGE_MODULES = ('batch_select.models', 'batch_select.replay')
########NEW FILE########
