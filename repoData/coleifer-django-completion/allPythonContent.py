__FILENAME__ = base
class BaseBackend(object):
    """
    Specify the interface for Autocomplete providers
    """
    def flush(self):
        raise NotImplementedError
    
    def store_object(self, obj, data):
        raise NotImplementedError
    
    def remove_object(self, obj, data):
        raise NotImplementedError
    
    def suggest(self, phrase, limit, models):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = db_backend
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from completion.backends.base import BaseBackend
from completion.models import AutocompleteObject
from completion.utils import clean_phrase, create_key, partial_complete


class DatabaseAutocomplete(BaseBackend):
    def flush(self):
        AutocompleteObject.objects.all().delete()
    
    def store_object(self, obj, data):
        """
        Given a title & some data that needs to be stored, make it available
        for autocomplete via the suggest() method
        """
        self.remove_object(obj, data)
        
        title = data['title']
        for partial_title in partial_complete(title):
            key = create_key(partial_title)
            autocomplete_obj = AutocompleteObject(
                title=key,
                object_id=obj.pk,
                content_type=ContentType.objects.get_for_model(obj),
                pub_date=data['pub_date'],
                data=data['data']
            )
            autocomplete_obj.save()
            autocomplete_obj.sites = data['sites']
    
    def remove_object(self, obj, data):
        AutocompleteObject.objects.for_object(obj).delete()
    
    def suggest(self, phrase, limit, models):
        phrase = create_key(phrase)
        if not phrase:
            return []
        
        query = dict(
            title__startswith=phrase,
            sites__pk__exact=settings.SITE_ID,
        )
        
        if models is not None:
            query.update(content_type__in=[
                ContentType.objects.get_for_model(model_class) \
                    for model_class in models
            ])
        
        qs = AutocompleteObject.objects.filter(
            **query
        ).values_list('data', flat=True).distinct()
        
        if limit is not None:
            qs = qs[:limit]
        
        return qs

########NEW FILE########
__FILENAME__ = redis_backend
import re

from django.conf import settings

from completion.backends.base import BaseBackend
from completion.constants import MIN_LENGTH, REDIS_CONNECTION
from completion.utils import clean_phrase, create_key, partial_complete

from redis import Redis


class RedisAutocomplete(BaseBackend):
    """
    Pretty proof-of-concept-y -- autocomplete across partial matches of a title
    string.  Does not handle siteification, pub_date filtering.
    
    Check out:
    http://antirez.com/post/autocomplete-with-redis.html
    http://stackoverflow.com/questions/1958005/redis-autocomplete/1966188#1966188
    """
    def __init__(self, connection=REDIS_CONNECTION, prefix='autocomplete:',
                 terminator='^'):
        host, port, db = connection.split(':') # host:port:db
        self.host = host
        self.port = int(port)
        self.db = int(db)
        
        self.prefix = prefix
        self.terminator = terminator
        
        self.client = self.get_connection()
    
    def get_connection(self):
        return Redis(host=self.host, port=self.port, db=self.db)
    
    def flush(self):
        self.client.flushdb()
    
    def get_object_data(self, obj):
        return '%s:%s' % (str(obj._meta), obj.pk)
    
    def autocomplete_keys(self, title):
        key = create_key(title)
        
        current_key = key[:MIN_LENGTH]
        for char in key[MIN_LENGTH:]:
            yield (current_key, char, ord(char))
            current_key += char
        
        yield (current_key, self.terminator, 0)
    
    def store_object(self, obj, data):
        """
        Given a title & some data that needs to be stored, make it available
        for autocomplete via the suggest() method
        """
        title = data['title']
        
        # store actual object data
        obj_data = self.get_object_data(obj)
        self.client.set('objdata:%s' % obj_data, data['data'])
        
        # create tries using sorted sets and add obj_data to the lookup set
        for partial_title in partial_complete(title):
            # store a reference to our object in the lookup set
            self.client.sadd(create_key(partial_title), obj_data)
            
            for (key, value, score) in self.autocomplete_keys(partial_title):
                self.client.zadd('%s%s' % (self.prefix, key), value, score)
    
    def remove_object(self, obj, data):
        title = data['title']
        keys = []

        obj_data = self.get_object_data(obj)
        
        #...how to figure out if its the final item...
        for partial_title in partial_complete(title):
            # get a list of all the keys that would have been set for the tries
            autocomplete_keys = list(self.autocomplete_keys(partial_title))
            
            # flag for whether ours is the last object at this lookup
            is_last = False
            
            # grab all the members of this lookup set
            partial_key = create_key(partial_title)
            objects_at_key = self.client.smembers(partial_key)
            
            # check the data at this lookup set to see if ours was the only obj
            # referenced at this point
            if obj_data not in objects_at_key:
                # something weird happened and our data isn't even here
                continue
            elif len(objects_at_key) == 1:
                # only one object stored here, remove the terminal flag
                zset_key = '%s%s' % (self.prefix, partial_key)
                self.client.zrem(zset_key, '^')
                
                # see if there are any other references to keys here
                is_last = self.client.zcard(zset_key) == 0
            
            if is_last:
                for (key, value, score) in reversed(autocomplete_keys):
                    key = '%s%s' % (self.prefix, key)
                    
                    # another lookup ends here, so bail
                    if '^' in self.client.zrange(key, 0, -1):
                        self.client.zrem(key, value)
                        break
                    else:
                        self.client.delete(key)
                
                # we can just blow away the lookup key
                self.client.delete(partial_key)
            else:
                # remove only our object's data
                self.client.srem(partial_key, obj_data)
        
        # finally, remove the data from the data key
        self.client.delete('objdata:%s' % obj_data)
    
    def suggest(self, phrase, limit, models):
        """
        Wrap our search & results with prefixing
        """
        phrase = create_key(phrase)
        
        # perform the depth-first search over the sorted sets
        results = self._suggest('%s%s' % (self.prefix, phrase), limit)
        
        # strip the prefix off the keys that indicated they matched a lookup
        prefix_len = len(self.prefix)
        cleaned_keys = map(lambda x: x[prefix_len:], results)
        
        # lookup the data references for each lookup set
        obj_data_lookups = []
        for key in cleaned_keys:
            obj_data_lookups.extend(self.client.smembers(key))
        
        seen = set()
        data = []
        
        if models:
            valid_models = set([str(model_class._meta) for model_class in models])
        
        # grab the data for each object
        for lookup in obj_data_lookups:
            if lookup in seen:
                continue
            
            seen.add(lookup)
            
            if models:
                model_class, obj_pk = lookup.split(':')
                if model_class not in valid_models:
                    continue
            
            data.append(self.client.get('objdata:%s' % lookup))
        
        return data
    
    def _suggest(self, text, limit):
        """
        At the expense of key memory, depth-first search all results
        """
        w = []
        
        for char in self.client.zrange(text, 0, -1):
            if char == self.terminator:
                w.append(text)
            else:
                w.extend(self._suggest(text + char, limit))
            
            if limit and len(w) >= limit:
                return w[:limit]
        
        return w

########NEW FILE########
__FILENAME__ = solr_backend
from django.conf import settings

from completion import constants
from completion.backends.base import BaseBackend

from pysolr import Solr, Results


class SolrAutocomplete(BaseBackend):
    def __init__(self, connection_string=constants.SOLR_CONNECTION):
        self.connection_string = connection_string
        self.client = self.get_connection()
    
    def flush(self):
        self.client.delete(q='*:*', commit=True)
        self.client.optimize()
    
    def get_connection(self):
        return Solr(self.connection_string)
    
    def generate_unique_id(self, obj):
        return '%s:%s' % (str(obj._meta), obj.pk)
    
    def store_object(self, obj, data):
        data.update(
            id=self.generate_unique_id(obj),
            django_ct=str(obj._meta),
            django_id=obj.pk
        )
        self.client.add([data], commit=True)
    
    def remove_object(self, obj, data):
        self.client.delete(id=self.generate_unique_id(obj), commit=True)
    
    def phrase_to_query(self, phrase, models):
        base_query = 'title_ngram:%s sites:%s' % (phrase, settings.SITE_ID)
        
        if models:
            additional_query = 'django_ct:(%s)' % ' OR '.join([
                str(model_class._meta) for model_class in models
            ])
            query = '%s %s' % (base_query, additional_query)
        else:
            query = base_query
            
        return query
    
    def suggest(self, phrase, limit, models):
        if not phrase:
            return []
        
        results = self.client.search(
            self.phrase_to_query(phrase, models),
            rows=limit or constants.DEFAULT_RESULTS
        )
        
        return map(lambda r: r['data'], results)

########NEW FILE########
__FILENAME__ = base
from django.test import TestCase

from completion.completion_tests.models import Blog, Note1, Note2, Note3


class AutocompleteTestCase(TestCase):
    fixtures = ['completion_testdata.json']
    
    def setUp(self):
        self.blog_tp = Blog.objects.get(pk=1)
        self.blog_tpc = Blog.objects.get(pk=2)
        self.blog_wtp = Blog.objects.get(pk=3)
        self.blog_utp = Blog.objects.get(pk=4)
        self.blog_unpub = Blog.objects.get(pk=5)
    
    def create_notes(self):
        notes = []
        for i in range(3):
            for klass in [Note1, Note2, Note3]:
                title = 'note class-%s number-%s' % (klass._meta.module_name, i)
                notes.append(klass.objects.create(title=title))
        return notes


class AutocompleteBackendTestCase(object):
    def test_suggest(self):
        test_site = self.test_site
        
        test_site.store_providers()
        
        results = test_site.suggest('testing python')
        self.assertEqual(sorted(results), [
            {'stored_title': 'testing python'},
            {'stored_title': 'testing python code'},
            {'stored_title': 'web testing python code'},
        ])
        
        results = test_site.suggest('test')
        self.assertEqual(sorted(results), [
            {'stored_title': 'testing python'},
            {'stored_title': 'testing python code'},
            {'stored_title': 'unit tests with python'},
            {'stored_title': 'web testing python code'},
        ])
        
        results = test_site.suggest('unit')
        self.assertEqual(results, [{'stored_title': 'unit tests with python'}])
        
        results = test_site.suggest('')
        self.assertEqual(results, [])
        
        results = test_site.suggest('another')
        self.assertEqual(results, [])
    
    def test_removing_objects(self):
        test_site = self.test_site
        
        test_site.store_providers()
        
        test_site.remove_object(self.blog_tp)
        
        results = test_site.suggest('testing')
        self.assertEqual(sorted(results), [
            {'stored_title': 'testing python code'}, 
            {'stored_title': 'web testing python code'},
        ])
        
        test_site.store_object(self.blog_tp)
        test_site.remove_object(self.blog_tpc)
        
        results = test_site.suggest('testing')
        self.assertEqual(sorted(results), [
            {'stored_title': 'testing python'}, 
            {'stored_title': 'web testing python code'},
        ])
    
    def test_filtering_by_type(self):
        test_site = self.test_site
        
        for note in self.create_notes():
            test_site.store_object(note)
        
        # first check that our results are as expected
        results = test_site.suggest('note')
        self.assertEqual(sorted(results), [
            {u'stored_title': u'note class-note1 number-0'},
            {u'stored_title': u'note class-note1 number-1'},
            {u'stored_title': u'note class-note1 number-2'},
            {u'stored_title': u'note class-note2 number-0'}, 
            {u'stored_title': u'note class-note2 number-1'}, 
            {u'stored_title': u'note class-note2 number-2'}, 
            {u'stored_title': u'note class-note3 number-0'}, 
            {u'stored_title': u'note class-note3 number-1'}, 
            {u'stored_title': u'note class-note3 number-2'}
        ])
        
        results = test_site.suggest('note', models=[Note1])
        self.assertEqual(sorted(results), [
            {u'stored_title': u'note class-note1 number-0'},
            {u'stored_title': u'note class-note1 number-1'},
            {u'stored_title': u'note class-note1 number-2'},
        ])
        
        results = test_site.suggest('note', models=[Note1, Note3])
        self.assertEqual(sorted(results), [
            {u'stored_title': u'note class-note1 number-0'},
            {u'stored_title': u'note class-note1 number-1'},
            {u'stored_title': u'note class-note1 number-2'},
            {u'stored_title': u'note class-note3 number-0'}, 
            {u'stored_title': u'note class-note3 number-1'}, 
            {u'stored_title': u'note class-note3 number-2'}
        ])

########NEW FILE########
__FILENAME__ = db_backend
from completion.backends.db_backend import DatabaseAutocomplete
from completion.completion_tests.base import AutocompleteTestCase, AutocompleteBackendTestCase
from completion.completion_tests.models import Blog, Note1, Note2, Note3, BlogProvider, NoteProvider
from completion.models import AutocompleteObject
from completion.sites import AutocompleteSite


test_site = AutocompleteSite(DatabaseAutocomplete())
test_site.register(Blog, BlogProvider)
test_site.register(Note1, NoteProvider)
test_site.register(Note2, NoteProvider)
test_site.register(Note3, NoteProvider)


class DatabaseBackendTestCase(AutocompleteTestCase, AutocompleteBackendTestCase):
    def setUp(self):
        self.test_site = test_site
        AutocompleteTestCase.setUp(self)
        test_site.flush()
    
    def test_storing_providers(self):
        self.assertEqual(AutocompleteObject.objects.count(), 0)
        
        test_site.store_providers()
        self.assertEqual(AutocompleteObject.objects.count(), 14)
        
        titles = AutocompleteObject.objects.values_list('title', flat=True)
        self.assertEqual(sorted(titles), [
            'pythoncode',
            'pythoncode',
            'testingpython',
            'testingpython',
            'testingpython',
            'testingpythoncode',
            'testingpythoncode',
            'testswith',
            'testswithpython',
            'unittests',
            'unittestswith',
            'webtesting',
            'webtestingpython',
            'withpython'
        ])
    
    def test_storing_objects_db(self):
        test_site.store_object(self.blog_tp)
        self.assertEqual(AutocompleteObject.objects.count(), 1)
        
        test_site.store_object(self.blog_tpc)
        self.assertEqual(AutocompleteObject.objects.count(), 4)
        
        test_site.store_object(self.blog_tp) # storing again does not produce dupe
        self.assertEqual(AutocompleteObject.objects.count(), 4)
        
        test_site.store_object(self.blog_wtp)
        # web testing, testing python, python code, web testing python, testing python code
        self.assertEqual(AutocompleteObject.objects.count(), 9)
    
    def test_removing_objects_db(self):
        test_site.store_providers()
        self.assertEqual(AutocompleteObject.objects.count(), 14)
        
        test_site.remove_object(self.blog_tp)
        # testing python
        self.assertEqual(AutocompleteObject.objects.count(), 13)
        
        test_site.remove_object(self.blog_tp)
        self.assertEqual(AutocompleteObject.objects.count(), 13)
        
        test_site.remove_object(self.blog_tpc)
        # testing python, python code, testing python code
        self.assertEqual(AutocompleteObject.objects.count(), 10)

########NEW FILE########
__FILENAME__ = models
import datetime

from django.db import models

from completion.sites import AutocompleteProvider, DjangoModelProvider


class Blog(models.Model):
    title = models.CharField(max_length=255)
    pub_date = models.DateTimeField()
    content = models.TextField()
    published = models.BooleanField(default=True)


class BlogProvider(AutocompleteProvider):
    def get_title(self, obj):
        return obj.title
    
    def get_pub_date(self, obj):
        return datetime.datetime(2010, 1, 1)
    
    def get_data(self, obj):
        return {'stored_title': obj.title}
    
    def get_queryset(self):
        return self.model._default_manager.filter(published=True)


class BaseNote(models.Model):
    title = models.CharField(max_length=255)
    pub_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True

class Note1(BaseNote):
    pass

class Note2(BaseNote):
    pass

class Note3(BaseNote):
    pass


class NoteProvider(AutocompleteProvider):
    def get_title(self, obj):
        return obj.title
    
    def get_pub_date(self, obj):
        return obj.pub_date
    
    def get_data(self, obj):
        return {'stored_title': obj.title}


class DjNoteProvider(DjangoModelProvider, NoteProvider):
    pass

########NEW FILE########
__FILENAME__ = redis_backend
from django.contrib.auth.models import User

from completion.backends.redis_backend import RedisAutocomplete
from completion.completion_tests.base import AutocompleteTestCase, AutocompleteBackendTestCase
from completion.completion_tests.models import Blog, Note1, Note2, Note3, BlogProvider, NoteProvider
from completion.sites import AutocompleteSite


test_site = AutocompleteSite(RedisAutocomplete(prefix='test:ac:'))
test_site.register(Blog, BlogProvider)
test_site.register(Note1, NoteProvider)
test_site.register(Note2, NoteProvider)
test_site.register(Note3, NoteProvider)


class RedisBackendTestCase(AutocompleteTestCase, AutocompleteBackendTestCase):
    def setUp(self):
        self.test_site = test_site
        AutocompleteTestCase.setUp(self)
        test_site.flush()
    
    def test_removing_objects_in_depth(self):
        # want to ensure that redis is cleaned up and does not become polluted
        # with spurious keys when objects are removed
        backend = test_site.backend
        redis_client = backend.client
        prefix = backend.prefix
        
        # store the blog "testing python"
        test_site.store_object(self.blog_tp)
        
        # see how many keys we have in the db - check again in a bit
        key_len = len(redis_client.keys())
        
        # make sure that the final item in our sorted set indicates such
        values = redis_client.zrange('%stestingpython' % prefix, 0, -1)
        self.assertEqual(values, [backend.terminator])

        test_site.store_object(self.blog_tpc)
        key_len2 = len(redis_client.keys())
        
        self.assertTrue(key_len != key_len2)
        
        # check to see that the final item in the sorted set from earlier now
        # includes a reference to 'c'
        values = redis_client.zrange('%stestingpython' % prefix, 0, -1)
        self.assertEqual(values, [backend.terminator, 'c'])
        
        test_site.remove_object(self.blog_tpc)
        
        # see that the reference to 'c' is removed so that we aren't following
        # a path that no longer exists
        values = redis_client.zrange('%stestingpython' % prefix, 0, -1)
        self.assertEqual(values, [backend.terminator])
        
        # back to the original amount of keys
        self.assertEqual(len(redis_client.keys()), key_len)

########NEW FILE########
__FILENAME__ = site
import datetime

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType

from completion import listeners
from completion.backends.base import BaseBackend
from completion.completion_tests.base import AutocompleteTestCase
from completion.completion_tests.models import Blog, Note1, Note2, Note3, BlogProvider, DjNoteProvider
from completion.listeners import start_listening, stop_listening
from completion.models import AutocompleteObject
from completion.sites import AutocompleteProvider, AutocompleteSite, UnknownObjectException
from completion.utils import clean_phrase, partial_complete, create_key


class DummyBackend(BaseBackend):
    """
    A test-only backend, titles are not broken up into bits to be searched for
    partial matches.  Just an in-memory dictionary of {title: provider data}
    """
    def __init__(self):
        self._index = {}
    
    def store_object(self, obj, data):
        self._index[data['title']] = data
    
    def remove_object(self, obj, data):
        if data['title'] in self._index:
            del(self._index[data['title']])
    
    def suggest(self, phrase, limit, models):
        if phrase in self._index:
            return [self._index[phrase]['data']]
        return []
    
    def flush(self):
        self._index = {}


test_site = AutocompleteSite(DummyBackend())
test_site.register(Blog, BlogProvider)
test_site.register(Note1, DjNoteProvider)
test_site.register(Note2, DjNoteProvider)
test_site.register(Note3, DjNoteProvider)


class SiteTestCase(AutocompleteTestCase):
    def test_registration(self):
        # make sure our registry is populated with the test provider
        self.assertEqual(len(test_site._providers), 4)
        self.assertTrue(Blog in test_site._providers)
        self.assertTrue(isinstance(test_site._providers[Blog], BlogProvider))
    
        # make sure removing works
        test_site.unregister(Blog)
        self.assertEqual(len(test_site._providers), 3)
        
        # should no-op
        test_site.unregister(Blog)
        
        # register & then double-register -> dictionary so just reg'd once
        test_site.register(Blog, BlogProvider)
        test_site.register(Blog, BlogProvider)
        self.assertEqual(len(test_site._providers), 4)
    
    def test_get_provider(self):
        provider = test_site.get_provider(self.blog_tp)
        self.assertTrue(isinstance(provider, BlogProvider))
        
        self.assertRaises(UnknownObjectException, test_site.get_provider, Group)
    
    def test_storing_objects(self):
        test_site.flush()
        self.assertEqual(test_site.backend._index, {})
        
        test_site.store_object(self.blog_tp)
        self.assertEqual(test_site.backend._index, {
            'testing python': {
                'data': '{"stored_title": "testing python"}',
                'pub_date': datetime.datetime(2010, 1, 1),
                'sites': [1], 
                'title': 'testing python'
            }
        })
    
    def test_removing_objects(self):
        test_site.flush()
        test_site.store_providers()
        
        test_site.remove_object(self.blog_tp)
        test_site.remove_object(self.blog_tpc)
        test_site.remove_object(self.blog_wtp)
        
        self.assertEqual(test_site.backend._index, {
            'unit tests with python': {
                'data': '{"stored_title": "unit tests with python"}', 
                'pub_date': datetime.datetime(2010, 1, 1), 
                'sites': [1], 
                'title': 'unit tests with python'
            }
        })
    
    def test_storing_providers(self):
        test_site.store_providers()
        
        self.assertEqual(test_site.backend._index, {
            'testing python': {
                'data': '{"stored_title": "testing python"}',
                'pub_date': datetime.datetime(2010, 1, 1, 0, 0),
                'sites': [1],
                'title': 'testing python'
            },
            'testing python code': {
                'data': '{"stored_title": "testing python code"}',
                'pub_date': datetime.datetime(2010, 1, 1, 0, 0),
                'sites': [1],
                'title': 'testing python code'
            },
            'unit tests with python': {
                'data': '{"stored_title": "unit tests with python"}',
                'pub_date': datetime.datetime(2010, 1, 1, 0, 0),
                'sites': [1],
                'title': 'unit tests with python'
            },
            'web testing python code': {
                'data': '{"stored_title": "web testing python code"}',
                'pub_date': datetime.datetime(2010, 1, 1, 0, 0),
                'sites': [1],
                'title': 'web testing python code'
            }
        })
    
    def test_suggest(self):
        test_site.flush()
        test_site.store_providers()
        
        results = test_site.suggest('web testing python code')
        self.assertEqual(results, [{'stored_title': 'web testing python code'}])
        
        results = test_site.suggest('testing python', 2)
        self.assertEqual(results, [{'stored_title': 'testing python'}])
        
        results = test_site.suggest('testing python', 0)
        self.assertEqual(results, [])
        
        results = test_site.suggest('another unpublished')
        self.assertEqual(results, [])
    
    def test_dj_provider(self):
        test_site.flush()
        
        n1 = Note1.objects.create(title='n1')
        n2 = Note2.objects.create(title='n2')
        n3 = Note3.objects.create(title='n3')
        
        test_site.store_object(n1)
        test_site.store_object(n2)
        test_site.store_object(n3)
        
        results = test_site.suggest('n1')
        self.assertEqual(results, [{
            'stored_title': 'n1',
            'django_ct': ContentType.objects.get_for_model(Note1).id,
            'object_id': n1.pk,
        }])
        
        results = test_site.suggest('n2')
        self.assertEqual(results, [{
            'stored_title': 'n2',
            'django_ct': ContentType.objects.get_for_model(Note2).id,
            'object_id': n2.pk,
        }])


class SignalHandlerTestCase(AutocompleteTestCase):
    def setUp(self):
        self._orig_site = listeners.site
        listeners.site = test_site
        AutocompleteTestCase.setUp(self)
    
    def tearDown(self):
        listeners.site = self._orig_site
        AutocompleteTestCase.tearDown(self)
    
    def test_signal_handlers(self):
        test_site.flush()
        
        n1 = Note1.objects.create(title='n1')
        self.assertEqual(len(test_site.backend._index), 0)
        
        start_listening()
        
        n1.save()
        self.assertEqual(len(test_site.backend._index), 1)
        
        n1.save()
        self.assertEqual(len(test_site.backend._index), 1)
        
        n2 = Note2.objects.create(title='n2')
        self.assertEqual(len(test_site.backend._index), 2)
        
        n1.delete()
        self.assertEqual(len(test_site.backend._index), 1)
        
        stop_listening()
        
        n2.delete()
        self.assertEqual(len(test_site.backend._index), 1)

########NEW FILE########
__FILENAME__ = solr_backend
from django.contrib.auth.models import User

from completion.backends.solr_backend import SolrAutocomplete
from completion.completion_tests.base import AutocompleteTestCase, AutocompleteBackendTestCase
from completion.completion_tests.models import Blog, Note1, Note2, Note3, BlogProvider, NoteProvider
from completion.sites import AutocompleteSite


test_site = AutocompleteSite(SolrAutocomplete())
test_site.register(Blog, BlogProvider)
test_site.register(Note1, NoteProvider)
test_site.register(Note2, NoteProvider)
test_site.register(Note3, NoteProvider)


class SolrBackendTestCase(AutocompleteTestCase, AutocompleteBackendTestCase):
    def setUp(self):
        self.test_site = test_site
        AutocompleteTestCase.setUp(self)

########NEW FILE########
__FILENAME__ = tests
import warnings

from django.conf import settings

from completion import constants
from completion.completion_tests.site import *
from completion.completion_tests.utils import *
from completion.completion_tests.db_backend import *

try:
    import redis
except ImportError:
    warnings.warn('Skipping redis backend tests, redis-py not installed')
else:
    if not constants.REDIS_CONNECTION:
        warnings.warn('Skipping redis backend tests, no connection configured')
    else:
        from completion.completion_tests.redis_backend import *

try:
    import pysolr
except ImportError:
    warnings.warn('Skipping solr backend tests, pysolr not installed')
else:
    if not constants.SOLR_CONNECTION:
        warnings.warn('Skipping solr backend tests, no connection configured')
    else:
        from completion.completion_tests.solr_backend import *

########NEW FILE########
__FILENAME__ = utils
from completion.completion_tests.base import AutocompleteTestCase
from completion.utils import clean_phrase, partial_complete, create_key


class UtilsTestCase(AutocompleteTestCase):
    def setUp(self):
        pass
    
    def test_clean_phrase(self):
        self.assertEqual(clean_phrase('abc def ghi'), ['abc', 'def', 'ghi'])
        
        self.assertEqual(clean_phrase('a A tHe an a'), [])
        self.assertEqual(clean_phrase(''), [])
        
        self.assertEqual(
            clean_phrase('The Best of times, the blurst of times'),
            ['best', 'times,', 'blurst', 'times'])
    
    def test_partial_complete(self):
        self.assertEqual(list(partial_complete('1')), ['1'])
        self.assertEqual(list(partial_complete('1 2')), ['1 2'])
        self.assertEqual(list(partial_complete('1 2 3')), ['1 2', '2 3', '1 2 3'])
        self.assertEqual(list(partial_complete('1 2 3 4')), ['1 2', '2 3', '3 4', '1 2 3', '2 3 4'])
        self.assertEqual(list(partial_complete('1 2 3 4 5')), ['1 2', '2 3', '3 4', '4 5', '1 2 3', '2 3 4', '3 4 5'])
        
        self.assertEqual(
            list(partial_complete('The Best of times, the blurst of times')),
            ['best times,', 'times, blurst', 'blurst times', 'best times, blurst', 'times, blurst times']
        )
        
        self.assertEqual(list(partial_complete('a the An')), [''])
        self.assertEqual(list(partial_complete('a')), [''])
    
    def test_create_key(self):
        self.assertEqual(
            create_key('the best of times, the blurst of Times'),
            'besttimesblurst'
        )
        
        self.assertEqual(create_key('<?php $bling; $bling; ?>'),
            'phpblingbling')
        
        self.assertEqual(create_key(''), '')
        
        self.assertEqual(create_key('the a an'), '')
        self.assertEqual(create_key('a'), '')

########NEW FILE########
__FILENAME__ = constants
from django.conf import settings


def def_to(setting, default):
    return getattr(settings, setting, default)


# articles to strip when handling a phrase for autocomplete
AUTOCOMPLETE_ARTICLES = def_to('AUTOCOMPLETE_ARTICLES', ['a', 'an', 'the', 'of'])

# min/max number of words to generate keys on (Redis & Postgres)
MIN_WORDS = def_to('AUTOCOMPLETE_MIN_WORDS', 2)
MAX_WORDS = def_to('AUTOCOMPLETE_MAX_WORDS', 3)

# minimum length of phrase for autocompletion
MIN_LENGTH = def_to('AUTOCOMPLETE_MIN_LENGTH', 3)

# default results to return
DEFAULT_RESULTS = def_to('AUTOCOMPLETE_DEFAULT_RESULTS', 10)


# connection settings

# host:port:db, i.e. localhost:6379:0
REDIS_CONNECTION = def_to('AUTOCOMPLETE_REDIS_CONNECTION', None)

# url, i.e. http://localhost:8080/solr/autocomplete-core/
SOLR_CONNECTION = def_to('AUTOCOMPLETE_SOLR_CONNECTION', None)

# test-only settings
SOLR_TEST_CONNECTION = def_to('AUTOCOMPLETE_SOLR_TEST_CONNECTION', None)

########NEW FILE########
__FILENAME__ = listeners
from django.db.models.signals import post_save, post_delete

from completion import site, UnknownObjectException


def update_obj(sender, instance, created, **kwargs):
    try:
        site.get_provider(instance)
        site.remove_object(instance)
        site.store_object(instance)
    except UnknownObjectException:
        pass

def remove_obj(sender, instance, **kwargs):
    try:
        site.get_provider(instance)
        site.remove_object(instance)
    except UnknownObjectException:
        pass


def start_listening():
    post_save.connect(update_obj, dispatch_uid='completion.listeners.update_obj')
    post_delete.connect(remove_obj, dispatch_uid='completion.listeners.remove_obj')

def stop_listening():
    post_save.disconnect(dispatch_uid='completion.listeners.update_obj')
    post_delete.disconnect(dispatch_uid='completion.listeners.remove_obj')

########NEW FILE########
__FILENAME__ = autocomplete_schema
import os
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.template import loader


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--dir', '-d', dest='directory',
            help='Directory to write files to, defaults to current dir'),
    )
    help = 'Generate a schema useful for autocomplete'
    
    def write_template(self, template_dir, template_name):
        filename = template_name.replace('.conf', '')
        fh = open(filename, 'w')
        fh.write(loader.render_to_string(template_dir + '/' + template_name, {}))
        fh.close()
        print 'Successfully wrote [%s]' % filename

    def handle(self, **options):
        directory = options.get('directory') or '.'
        try:
            os.chdir(directory)
        except OSError:
            raise CommandError('Error changing directory to %s' % directory)

        self.write_template('completion', 'schema.xml.conf')

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'AutocompleteObject'
        db.create_table('completion_autocompleteobject', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('object_id', self.gf('django.db.models.fields.IntegerField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('pub_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('data', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('completion', ['AutocompleteObject'])

        # Adding M2M table for field sites on 'AutocompleteObject'
        db.create_table('completion_autocompleteobject_sites', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('autocompleteobject', models.ForeignKey(orm['completion.autocompleteobject'], null=False)),
            ('site', models.ForeignKey(orm['sites.site'], null=False))
        ))
        db.create_unique('completion_autocompleteobject_sites', ['autocompleteobject_id', 'site_id'])


    def backwards(self, orm):
        
        # Deleting model 'AutocompleteObject'
        db.delete_table('completion_autocompleteobject')

        # Removing M2M table for field sites on 'AutocompleteObject'
        db.delete_table('completion_autocompleteobject_sites')


    models = {
        'completion.autocompleteobject': {
            'Meta': {'object_name': 'AutocompleteObject'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'pub_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['completion']

########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models


class AutocompleteObjectManager(models.Manager):
    def for_object(self, obj):
        return self.filter(
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.pk
        )


class AutocompleteObject(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    object_id = models.IntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = GenericForeignKey()
    sites = models.ManyToManyField(Site, blank=True)
    pub_date = models.DateTimeField(blank=True, null=True)
    data = models.TextField(blank=True)
    
    objects = AutocompleteObjectManager()
    
    class Meta:
        ordering = ('-pub_date',)
    
    def __unicode__(self):
        return '%s: %s' % (self.content_object, self.title)

########NEW FILE########
__FILENAME__ = sites
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models.query import QuerySet
from django.utils import simplejson as json

from completion.utils import get_backend


class AutocompleteProvider(object):
    def __init__(self, model):
        self.model = model
    
    def get_title(self, obj):
        """
        The title of the object, which will support autocompletion
        """
        raise NotImplementedError
    
    def get_sites(self, obj):
        """
        Ideally, return a list of primary keys, however a list or queryset of
        Site objects will be converted automatically
        """
        return [settings.SITE_ID]
    
    def get_pub_date(self, obj):
        """
        Used for ordering
        """
        raise NotImplementedError
    
    def get_data(self, obj):
        """
        Any arbitrary data to go along with this object, i.e. the object's
        absolute URL, which can be stored to avoid a db hit
        """
        return {}
    
    def get_queryset(self):
        return self.model._default_manager.all()
    
    def object_to_dictionary(self, obj):
        sites = self.get_sites(obj)
        if isinstance(sites, QuerySet):
            sites = list(sites.values_list('pk', flat=True))
        elif isinstance(sites, (list, tuple)) and len(sites):
            if isinstance(sites[0], Site):
                sites = [site.pk for site in sites]
        
        return {
            'title': self.get_title(obj),
            'sites': sites,
            'pub_date': self.get_pub_date(obj),
            'data': self.get_data(obj)
        }


class DjangoModelProvider(AutocompleteProvider):
    def object_to_dictionary(self, obj):
        obj_dict = super(DjangoModelProvider, self).object_to_dictionary(obj)
        obj_dict['data'].update(
            django_ct=ContentType.objects.get_for_model(obj).pk,
            object_id=obj.pk,
        )
        return obj_dict


class UnknownObjectException(Exception):
    pass


class AutocompleteSite(object):
    def __init__(self, backend):
        self._providers = {}
        self.backend = backend
    
    def register(self, model_class, provider):
        self._providers[model_class] = provider(model_class)
    
    def unregister(self, model_class):
        if model_class in self._providers:
            del(self._providers[model_class])
    
    def get_provider(self, obj):
        try:
            return self._providers[type(obj)]
        except KeyError:
            raise UnknownObjectException("Don't know what do with %s" % obj)
    
    def flush(self):
        self.backend.flush()
    
    def prepare_object(self, provider, obj):
        obj_dict = provider.object_to_dictionary(obj)
        obj_dict['data'] = self.serialize_data(obj_dict['data'])
        return obj_dict
    
    def _store(self, provider, obj):
        obj_dict = self.prepare_object(provider, obj)
        self.backend.store_object(obj, obj_dict)
    
    def store_providers(self):
        self.flush()
        for provider in self._providers.values():
            self.store_provider_queryset(provider)
    
    def store_provider_queryset(self, provider):
        for obj in provider.get_queryset().iterator():
            self._store(provider, obj)
    
    def store_object(self, obj):
        provider = self.get_provider(obj)
        self._store(provider, obj)
    
    def remove_object(self, obj):
        provider = self.get_provider(obj)
        obj_dict = self.prepare_object(provider, obj)
        self.backend.remove_object(obj, obj_dict)
    
    def suggest(self, text, limit=None, models=None, **kwargs):
        # pass limit to the backend in case it can optimize
        result_set = self.backend.suggest(text, limit, models, **kwargs)
        if limit is not None:
            result_set = result_set[:limit]
        return map(self.deserialize_data, result_set)
    
    def serialize_data(self, data_dict):
        return json.dumps(data_dict)
    
    def deserialize_data(self, raw):
        return json.loads(raw)


backend_class = get_backend()
backend = backend_class()
site = AutocompleteSite(backend)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('completion.views',
    url(r'^$', 'autocomplete', name='autocomplete'),
)

########NEW FILE########
__FILENAME__ = utils
import re

from django.conf import settings
from django.utils.importlib import import_module

from completion.constants import *


def clean_phrase(phrase):
    """
    Lower-case and strip articles from a phrase
    """
    phrase = phrase.lower()
    return [w for w in phrase.split() if w not in AUTOCOMPLETE_ARTICLES]

def partial_complete(phrase):
    """
    Break apart a phrase into several chunks using max_words as a guide
    
    The quick brown fox jumped --> quick brown fox, brown fox jumped
    """
    words = clean_phrase(phrase)
    
    max_words = max(
        min(len(words), MAX_WORDS), MIN_WORDS
    )
    
    for num_words in range(MIN_WORDS, max_words + 1):
        chunks = len(words) - num_words + 1
        chunks = chunks < 1 and 1 or chunks
        
        for i in range(chunks):
            yield ' '.join(words[i:i + num_words])

def create_key(phrase):
    """
    Clean up a phrase making it suitable for use as a key
    
    The quick brown fox jumped --> quickbrownfox
    """
    key = ' '.join(clean_phrase(phrase)[:MAX_WORDS])
    return re.sub('[^a-z0-9_-]', '', key)

def get_backend():
    mod, klass = settings.AUTOCOMPLETE_BACKEND.rsplit('.', 1)
    module = import_module(mod)
    return getattr(module, klass)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.utils import simplejson as json

from completion import constants, site


def autocomplete(request, num_results=constants.DEFAULT_RESULTS):
    q = request.GET.get('q')
    results = []
    if q:
        results = site.suggest(q, num_results)
    return HttpResponse(json.dumps(results), mimetype='application/json')

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        SITE_ID=1,
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'completion.completion_tests',
            'completion',
        ],
        AUTOCOMPLETE_BACKEND='completion.backends.db_backend.DatabaseAutocomplete',
        AUTOCOMPLETE_REDIS_CONNECTION='localhost:6379:0',
        AUTOCOMPLETE_SOLR_CONNECTION='http://localhost:8999/solr/autocomplete-test/',
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if not test_args:
        test_args = ['completion_tests']
    ac_dir = os.path.join(os.path.dirname(__file__), 'completion')
    sys.path.insert(0, ac_dir)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
